"""Phase X / ACT-156~158 — 具身接地接入 META_FSM（EmbodiedGroundingBounded）回歸測試.

對應藍圖：build/planning/active/SDD_improving_Automation_25.md
對應規則：CLAUDE.md Rule 9.36 / formal/META_FSM.tla EmbodiedGroundingBounded

涵蓋：
  - ACT-156：META_FSM 補 EmbodiedGroundingBounded 不變量（不增軸、不增狀態變數）。
  - ACT-157：guard_embodied_grounding fail-closed ↔ TLA+ 100% 同構 + embodied_grounding_oracle
            具身增益判據 + 對抗分離（oracle 不 import generator）+ embodied-grounding 命名空間隔離。
  - ACT-158：chaos EMBODIED_GROUNDING_FLAP + steersman render + 治理（R-9.36 / RULES_INDEX / INIT）。
"""
from __future__ import annotations

# enforces (governance rules): R-9.36

import ast
from pathlib import Path

import pytest

from tools.fsm_runtime import embodied_grounding_oracle as EG
from tools.fsm_runtime import output_quality_scorer as OQS
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
from tools.fsm_runtime.meta_halt import meta_ledger as ML

ROOT = Path(__file__).resolve().parents[1]   # tools/fsm_runtime/


# ---------------------------------------------------------------------------
# 觀測 fixtures
# ---------------------------------------------------------------------------
def _obs_pass() -> OQS.ExecutionObservation:
    """乾淨高品質觀測（OQS=1.0 → verdict pass）。"""
    return OQS.ExecutionObservation(tests_total=10, tests_passed=10,
                                    runtime_errors=0, nonzero_exit=False)


def _obs_runtime_fail() -> OQS.ExecutionObservation:
    """runtime 失敗觀測（非零 exit + 多測試失敗 → verdict runtime_fail）。"""
    return OQS.ExecutionObservation(tests_total=10, tests_passed=3,
                                    runtime_errors=5, nonzero_exit=True)


def _obs_zero() -> OQS.ExecutionObservation:
    """零觀測（沙箱從未真正跑過/壞過 → OQS inconclusive）。"""
    return OQS.ExecutionObservation()


# ---------------------------------------------------------------------------
# ACT-157 — embodied_grounding_oracle（具身增益判據，generator 不可見）
# ---------------------------------------------------------------------------
def test_oracle_grounded_pass_when_no_regress_no_new_fail():
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass())
    assert v.grounded_verdict == EG.GROUNDED_PASS
    assert v.oqs >= v.baseline_oqs


def test_oracle_grounded_fail_on_oqs_regression():
    base = _obs_pass()                       # OQS 1.0
    cand = OQS.ExecutionObservation(tests_total=10, tests_passed=5)   # OQS 退步但仍有觀測
    v = EG.evaluate_embodied_grounding(base, cand)
    assert v.grounded_verdict == EG.GROUNDED_FAIL


def test_oracle_grounded_fail_on_new_runtime_fail():
    base = _obs_pass()
    cand = OQS.ExecutionObservation(tests_total=10, tests_passed=10,
                                    runtime_errors=2, nonzero_exit=True)  # 新增 runtime 失敗
    v = EG.evaluate_embodied_grounding(base, cand)
    assert v.grounded_verdict == EG.GROUNDED_FAIL


def test_oracle_sandbox_timeout_is_grounded_fail():
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass(), sandbox_timed_out=True)
    assert v.grounded_verdict == EG.GROUNDED_FAIL
    assert v.sandbox_timed_out is True


def test_oracle_spec_defect_routes_spec_audit():
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass(), spec_defect=True)
    assert v.grounded_verdict == EG.GROUNDED_SPEC_DEFECT
    assert v.spec_defect is True


def test_oracle_inconclusive_on_zero_observation():
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_zero())
    assert v.grounded_verdict == EG.GROUNDED_INCONCLUSIVE


def test_oracle_none_candidate_is_inconclusive():
    v = EG.evaluate_embodied_grounding(_obs_pass(), None)
    assert v.grounded_verdict == EG.GROUNDED_INCONCLUSIVE
    assert v.observation is None


# ---------------------------------------------------------------------------
# ACT-157 — guard_embodied_grounding fail-closed ↔ TLA+ EmbodiedGroundingBounded 100% 同構
# ---------------------------------------------------------------------------
def test_guard_grounded_pass_allows_grow():
    """(iii) grounded_pass → allowed=True（允許 MFSM_GROW）。"""
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass())
    res = MM.guard_embodied_grounding(v)
    assert res.allowed is True
    assert res.verdict == "grounded_pass"
    assert res.grounded is True


def test_guard_fail_closed_missing_observation_escalates():
    """(i) fail-closed：observation=None → raise EmbodiedGroundingViolation（导 MFSM_ESCALATION）。"""
    v = EG.GroundedVerdict(observation=None, grounded_verdict=EG.GROUNDED_INCONCLUSIVE,
                           oqs=0.0, baseline_oqs=1.0)
    with pytest.raises(MM.EmbodiedGroundingViolation):
        MM.guard_embodied_grounding(v)


def test_guard_fail_closed_inconclusive_zero_observation_escalates():
    """(i) fail-closed：零觀測 → OQS inconclusive → raise（杜絕零觀測 false-green 納入）。"""
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_zero())
    with pytest.raises(MM.EmbodiedGroundingViolation):
        MM.guard_embodied_grounding(v)


def test_guard_sandbox_timeout_rejects_no_churn():
    """(ii) 沙箱硬 timeout → allowed=False（grounded_fail，FSM 不 wall-clock wait）。"""
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass(), sandbox_timed_out=True)
    res = MM.guard_embodied_grounding(v)
    assert res.allowed is False
    assert res.verdict == "grounded_fail"


def test_guard_runtime_fail_rejects_no_churn():
    """(iii) runtime_fail → allowed=False（REJECT，回 OBSERVE 不增 churn）。"""
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_runtime_fail())
    res = MM.guard_embodied_grounding(v)
    assert res.allowed is False
    assert res.verdict in ("grounded_fail", "spec_defect")


def test_guard_independent_of_oracle_label_not_trusting_grounded_pass():
    """guard 獨立用 OQS 重新計分驗證——即使 verdict 標籤謊稱 grounded_pass，零觀測仍 fail-closed。"""
    forged = EG.GroundedVerdict(observation=_obs_zero(), grounded_verdict=EG.GROUNDED_PASS,
                                oqs=1.0, baseline_oqs=1.0)   # 標籤造假但觀測為零
    with pytest.raises(MM.EmbodiedGroundingViolation):
        MM.guard_embodied_grounding(forged)


def test_guard_spec_defect_rejects():
    v = EG.evaluate_embodied_grounding(_obs_pass(), _obs_pass(), spec_defect=True)
    res = MM.guard_embodied_grounding(v)
    assert res.allowed is False
    assert res.verdict == "spec_defect"


# ---------------------------------------------------------------------------
# ACT-157 — 對抗分離（embodied_grounding_oracle 對 generator 不可見）+ 命名空間隔離
# ---------------------------------------------------------------------------
def _imported_module_names(py_path: Path) -> set:
    """AST 解析回傳檔案實際 import 的模組名集合（Import / ImportFrom，含函式內惰性 import）.

    用 AST 而非子字串——docstring 提及模組名（解釋「不 import」）不應誤判為 import。
    """
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[-1])
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names.add(mod.split(".")[-1])
            names.add(mod)
            for a in node.names:
                names.add(a.name)
    return names


_FORBIDDEN_GENERATOR_IMPORTS = {
    "operator_genesis", "operator_recursion_genesis", "operator_alphabet_genesis",
    "operator_depth_genesis", "dimension_semantics_synthesizer", "vocabulary_genesis",
    "dimension_necessity_oracle",
}


def test_oracle_adversarial_separation_no_generator_import():
    """Rule 9.36 對抗分離：embodied_grounding_oracle 結構性不 import 任何 generator / 必要性 oracle（AST 驗證）。"""
    imported = _imported_module_names(ROOT / "embodied_grounding_oracle.py")
    leaked = imported & _FORBIDDEN_GENERATOR_IMPORTS
    assert not leaked, f"具身 oracle 不得 import generator / 必要性 oracle（對抗分離），洩漏：{leaked}"


def test_guard_does_not_import_oracle_or_generator():
    """Rule 9.36：guard 模組不 import embodied_grounding_oracle / generator（duck-typed，避免循環+耦合；AST 驗證）。"""
    imported = _imported_module_names(ROOT / "meta_halt" / "meta_halt_monitor.py")
    assert "embodied_grounding_oracle" not in imported
    assert not (imported & _FORBIDDEN_GENERATOR_IMPORTS)


def test_embodied_grounding_namespace_isolation():
    """Rule 9.36：embodied-grounding 與維度/詞彙/算子/字母/深度/互遞迴命名空間分開治理。"""
    assert ML.is_embodied_grounding_fingerprint("embodied-grounding:abc")
    assert not ML.is_embodied_grounding_fingerprint("recursion-genesis:abc")
    assert not ML.is_embodied_grounding_fingerprint("depth-genesis:abc")
    assert not ML.is_embodied_grounding_fingerprint("value-dimension:abc")
    assert not ML.is_recursion_genesis_fingerprint("embodied-grounding:abc")


def test_guard_eval_path_no_while_no_recursion():
    """guard_embodied_grounding 求值路徑零 while / 零自呼叫（有界停機，沿 Phase W 風格守門）。"""
    src = (ROOT / "meta_halt" / "meta_halt_monitor.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "guard_embodied_grounding":
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), "guard 不得含 while（有界停機）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != "guard_embodied_grounding", "guard 不得自呼叫"


# ---------------------------------------------------------------------------
# ACT-156 — META_FSM 不增第六軌 / 不增狀態變數（EmbodiedGroundingBounded 不變量）
# ---------------------------------------------------------------------------
def test_meta_fsm_declares_phase_x_invariant():
    """META_FSM.tla 定義 EmbodiedGroundingBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "EmbodiedGroundingBounded ==" in tla
    assert "EmbodiedGroundingBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state_phase_x():
    """Rule 9.36：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track_phase_x():
    """Rule 9.36：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_embodied_grounding_leak():
    """Rule 9.36：embodied-grounding 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "EmbodiedGrounding" not in sdd and "embodied-grounding" not in sdd


# ---------------------------------------------------------------------------
# ACT-158 — chaos EMBODIED_GROUNDING_FLAP + steersman + 治理
# ---------------------------------------------------------------------------
def test_chaos_registers_embodied_grounding_flap():
    """chaos_runner 註冊 EMBODIED_GROUNDING_FLAP 故障型（具身接地閘有界停機驗收）。"""
    src = (ROOT / "chaos_runner.py").read_text(encoding="utf-8")
    assert "EMBODIED_GROUNDING_FLAP" in src


def test_steersman_renders_embodied_grounding_proposal():
    """steersman_renderer 提供 render_embodied_grounding_proposal（人類 K=1 掌舵介面）。"""
    from tools.fsm_runtime import steersman_renderer as SR
    assert hasattr(SR, "render_embodied_grounding_proposal")


def test_r936_rule_yaml_exists_and_indexed():
    """收官治理：R-9.36 yaml 落地、RULES_INDEX 列入。"""
    gov = ROOT.parent.parent / "governance"
    rule = gov / "rules" / "R-9.36-embodied-grounding-phase-x.yaml"
    assert rule.exists(), "R-9.36 規則 yaml 須落地"
    idx = (gov / "RULES_INDEX.md").read_text(encoding="utf-8")
    assert "9.36" in idx


def test_id_registry_next_free_advanced():
    """收官 ID 翻牌：next_free 已推進過 Phase X 範圍（act > 158 / rule > 9.36；durable，後續 Phase 推進不破）。"""
    from tools.fsm_runtime import id_registry
    assert id_registry.next_act() >= 159
    assert float(id_registry.next_rule()) >= 9.37
