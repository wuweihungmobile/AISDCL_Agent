# enforces (governance rules): R-9.32
"""Phase T / ACT-141~146 — 轉換算子文法自我擴充（meta⁵）回歸守門.

涵蓋：
  - ACT-141 Operator Genesis Grammar：TRANSFORMS/OPS 外有界算子生成文法（可枚舉、cap budget、結構性
    全函式 + 有界步數 + 零遞迴零迴圈）、算子自指 operator_self_reference_guard 零漏放、deterministic、
    只透過注入 evaluate 取必要性（結構性無自評）、proposed-only、反 big-bang K_op=1 截斷、對抗分離
    （不 import oracle）、expanded_ops
  - ACT-142 feature-grounded 必要性 oracle：evaluate_genesis_operator（不靠算子名）、算子外真必要偵出、
    算子自我發明 Goodhart（噪音算子+冗餘算子）零漏放、necessity tier 唯一來源、隔離、OPR 凍結語料
  - ACT-143 算子 stock OperatorGenesisBounded + 可計算性 OperatorComputabilityBounded：算子基數觸頂→
    OperatorCardinalityExceeded→MFSM_ESCALATION、cost 超界/非全函式→OperatorComputabilityExceeded、
    META_FSM 不增第六軌/不增狀態變數
  - ACT-144 steersman 算子外發明 diff + 可計算性證據（advisory + 反 big-bang + 人工 gate）
  - ACT-146 chaos OPERATOR_GENESIS_GOODHART_FLAP / OPERATOR_COMPUTABILITY_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import operator_genesis as OG
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.operator_genesis import GenesisOperator
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ACT-141 — Operator Genesis Grammar（TRANSFORMS/OPS 外有界算子生成文法 + 算子自指守門 + 可計算性，meta⁵）
# ---------------------------------------------------------------------------

def test_enumerate_operators_bounded():
    """Rule 9.32.1 有界算子生成文法：枚舉節點 <= budget（OPS 外≠無界）。"""
    assert len(OG.enumerate_genesis_operators(budget=10)) == 10
    assert len(OG.enumerate_genesis_operators(budget=1)) == 1
    # 超大 budget 被文法大小截住（仍有界、有限）
    full = len(OG.enumerate_genesis_operators(budget=10000))
    assert 0 < full < 10000


def test_enumerate_operators_deterministic():
    a = OG.enumerate_genesis_operators(budget=30)
    b = OG.enumerate_genesis_operators(budget=30)
    assert [o.name for o in a] == [o.name for o in b]


def test_operator_name_cost_fingerprint():
    go = GenesisOperator.of("max", "diff", secondary="min")
    assert go.name.startswith("op::diff(max,min)@")
    assert go.cost() == 3                      # 二元：2 primitive + 1 combinator
    assert GenesisOperator.of("mean", "identity").cost() == 2  # 一元：1 primitive + 1 combinator
    fp = go.fingerprint()
    assert fp.startswith("operator-genesis:")
    assert go.fingerprint() != GenesisOperator.of("min", "diff", secondary="max").fingerprint()


def test_operator_apply_is_total_fuzz():
    """Rule 9.32.3 全函式：對極端輸入 fuzz，apply 永不拋例外、無 NaN/inf。"""
    extreme = [[], [0.0], [-5.0], [1e18, -1e18], [0.0, 0.0, 0.0], [1e-18]]
    for o in OG.enumerate_genesis_operators(budget=10000):
        assert o.is_total(), f"算子 {o.name} 非全函式"
        for vals in extreme:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(o.probe)}
            r = o.apply(feats)   # 不得拋例外
            assert r == r        # 不得 NaN


def test_all_enumerated_operators_within_step_budget():
    """Rule 9.32.3 有界步數：所有枚舉算子 cost <= 預設 step_max（結構性 <=3）。"""
    step_max = OG.op_step_max()
    assert all(o.cost() <= step_max for o in OG.enumerate_genesis_operators(budget=10000))
    assert all(o.cost() <= 3 for o in OG.enumerate_genesis_operators(budget=10000))


def test_operator_eval_path_no_while_no_recursion():
    """Rule 9.32.3 零遞迴零迴圈：算子求值路徑（_prim/_comb/apply/cost）無 while、無自呼叫。"""
    src = (ROOT / "operator_genesis.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    targets = {"_prim", "_comb", "apply", "cost"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in targets:
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), f"{node.name} 含 while（破可計算性零迴圈）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != node.name, f"{node.name} 自呼叫（破可計算性零遞迴）"


def test_operator_self_reference_guard_zero_miss():
    """Rule 9.32.2 反自利第一閘：任何 primitive/combinator/secondary/probe 自指 → 結構性丟棄。"""
    decoys = [
        GenesisOperator.of("self_score", "identity"),
        GenesisOperator.of("mean", "identity", probe=["proposer_x"]),
        GenesisOperator.of("max", "diff", secondary="necessity"),
        GenesisOperator.of("mean", "identity", probe=["oracle_score"]),
    ]
    for d in decoys:
        assert OG.is_operator_self_referential(d)
    kept = OG.operator_self_reference_guard(decoys + [GenesisOperator.of("mean", "identity")])
    assert len(kept) == 1 and not OG.is_operator_self_referential(kept[0])


def test_enumerate_excludes_self_referential():
    """生產 PRIMITIVES/COMBINATORS 無自指 token → 枚舉恆無自指算子。"""
    assert all(not OG.is_operator_self_referential(o)
               for o in OG.enumerate_genesis_operators(budget=10000))


def test_operator_genesis_only_via_injected_evaluate():
    """Rule 9.32.2 對抗分離：genesis 只呼叫注入 evaluate、結構性無自評。"""
    seen = {}
    def ev(go):
        seen[go.name] = seen.get(go.name, 0) + 1
        return 0.5 if "identity(mean)" in go.name else 0.0   # identity(mean) 為枚舉首位
    prop = OG.operator_genesis(ev, budget=30)
    assert prop.operator is not None and prop.accepted
    assert prop.nodes_searched <= 30           # Rule 9.32.1 有界
    assert seen, "genesis 必須透過注入 evaluate 取必要性"


def test_operator_genesis_isolation_from_oracle():
    """Rule 9.32.2 對抗分離：operator_genesis 結構性不 import oracle、不讀必要性語料。"""
    src = (ROOT / "operator_genesis.py").read_text(encoding="utf-8")
    assert "dimension_necessity_oracle" not in src   # 不 import 評估器（對抗分離）
    assert "load_operator_corpus" not in src         # 不讀必要性語料
    assert "held-out-corpus" not in src              # 不觸及凍結語料目錄


def test_operator_genesis_round_k_truncation():
    """Rule 9.32.4 反 big-bang：一輪至多 K_op 個，其餘順延。"""
    cands = OG.enumerate_genesis_operators(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda o: scores.get(o.name, 0.0)
    rnd = OG.operator_genesis_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].operator.name == cands[0].name   # 最高 necessity
    assert len(rnd.deferred) == 2


def test_expanded_ops():
    base = OG.expanded_ops([])
    assert "mean" in base and "max" in base
    grown = OG.expanded_ops(["op::diff(max,min)@x"])
    assert "op::diff(max,min)@x" in grown and len(grown) == len(base) + 1


def test_adopt_operator_requires_signoff():
    go = GenesisOperator.of("mean", "identity")
    with pytest.raises(OG.SignoffRequired):
        OG.adopt_genesis_operator(go, 50, human_signoff=False)


def test_adopt_operator_rejects_self_referential():
    go = GenesisOperator.of("self_score", "identity")
    with pytest.raises(OG.SelfReferentialOperator):
        OG.adopt_genesis_operator(go, 50, human_signoff=True)


# ---------------------------------------------------------------------------
# ACT-142 — feature-grounded 算子必要性 oracle（evaluate_genesis_operator，反 Goodhart）
# ---------------------------------------------------------------------------

def _true_operator_case():
    # spread/range-sensitive 算子救回 baseline 漏判的低 spread 好候選
    return DO.OperatorCase(case_id="T", candidates=[
        DO.OperatorCandidate(0.4, 2.0, {"rollback_steps": 9.0, "blast_radius": 1.0, "canary_gap": 1.0}),
        DO.OperatorCandidate(0.9, 3.0, {"rollback_steps": 4.0, "blast_radius": 4.0, "canary_gap": 4.0}),
        DO.OperatorCandidate(0.6, 5.0, {"rollback_steps": 6.0, "blast_radius": 3.0, "canary_gap": 2.0})])


def _noise_operator_case():
    return DO.OperatorCase(case_id="N", candidates=[
        DO.OperatorCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        DO.OperatorCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        DO.OperatorCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])


def _redundant_operator_case():
    # mean 在 probe 上等於 existing_cost 排序（再投影既有成本）→ concordance 高 → 冗餘
    return DO.OperatorCase(case_id="R", candidates=[
        DO.OperatorCandidate(0.6, 2.0, {"rollback_steps": 2.0, "blast_radius": 2.0, "canary_gap": 2.0}),
        DO.OperatorCandidate(0.5, 3.0, {"rollback_steps": 3.0, "blast_radius": 3.0, "canary_gap": 3.0}),
        DO.OperatorCandidate(0.4, 4.0, {"rollback_steps": 4.0, "blast_radius": 4.0, "canary_gap": 4.0})])


def test_evaluate_operator_true_necessary():
    rng = GenesisOperator.of("max", "diff", secondary="min")
    v = DO.evaluate_genesis_operator(rng, [_true_operator_case()], coverage_margin=0.1)
    assert v.incremental_coverage >= 0.1
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier > 0


def test_evaluate_operator_noise_rejected_by_coverage():
    noise = GenesisOperator.of("mean", "identity")
    v = DO.evaluate_genesis_operator(noise, [_noise_operator_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_evaluate_operator_redundant_rejected_by_redundancy():
    mean = GenesisOperator.of("mean", "identity")
    v = DO.evaluate_genesis_operator(mean, [_redundant_operator_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_operator_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘算子仍被非冗餘度獨立否決。"""
    mean = GenesisOperator.of("mean", "identity")
    v = DO.evaluate_genesis_operator(mean, [_redundant_operator_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘算子須被非冗餘度獨立否決"


def test_operator_goodhart_zero_miss():
    """安全紅線：噪音算子 + 冗餘算子攔截零漏放。"""
    noise = GenesisOperator.of("mean", "identity")
    assert not DO.evaluate_genesis_operator(noise, [_noise_operator_case()], coverage_margin=0.1).necessary
    mean = GenesisOperator.of("mean", "identity")
    assert not DO.evaluate_genesis_operator(mean, [_redundant_operator_case()], coverage_margin=0.1).necessary


def test_necessity_score_operator_zero_when_not_necessary():
    rng = GenesisOperator.of("max", "diff", secondary="min")
    assert DO.necessity_score_operator(rng, [_true_operator_case()]) > 0.0
    assert DO.necessity_score_operator(
        GenesisOperator.of("mean", "identity"), [_noise_operator_case()]) == 0.0


def test_operator_genesis_self_passes_but_oracle_rejects():
    """genesis 樸素自評視噪音算子為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise = GenesisOperator.of("mean", "identity")
    per = OG.operator_genesis(lambda o: 0.9, candidates=[noise])
    assert per.accepted, "genesis 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_genesis_operator(noise, [_noise_operator_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_operator_replay_bounded():
    corpus = [_true_operator_case() for _ in range(100)]
    v = DO.evaluate_genesis_operator(GenesisOperator.of("max", "diff", secondary="min"),
                                     corpus, max_cases=5)
    assert v.examined == 5


def test_load_operator_corpus_12_cases():
    corpus = DO.load_operator_corpus()
    assert len(corpus) >= 12, f"OPR 凍結語料應 >= 12，實得 {len(corpus)}"


def test_load_operator_corpus_makes_range_operator_necessary():
    """端到端：載入凍結 OPR 語料 → range 算子在其上必要（feature-grounded）。"""
    corpus = DO.load_operator_corpus()
    rng = GenesisOperator.of("max", "diff", secondary="min")
    v = DO.evaluate_genesis_operator(rng, corpus, coverage_margin=0.1)
    assert v.necessary and v.incremental_coverage >= 0.1


def test_operator_corpus_fingerprint_deterministic():
    corpus = DO.load_operator_corpus()
    assert DO.operator_corpus_fingerprint(corpus) == DO.operator_corpus_fingerprint(corpus)


# ---------------------------------------------------------------------------
# ACT-143 — META_FSM 不增第六軌/不增狀態變數（兩新不變量）+ 守門
# ---------------------------------------------------------------------------

def test_meta_fsm_declares_phase_t_invariants():
    """ACT-143：META_FSM.tla 定義 OperatorGenesisBounded + OperatorComputabilityBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "OperatorGenesisBounded ==" in tla
    assert "OperatorComputabilityBounded ==" in tla
    assert "OperatorGenesisBounded" in cfg
    assert "OperatorComputabilityBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.32.4：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.32.4：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_operator_leak():
    """Rule 9.32.4：operator-genesis 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "OperatorGenesis" not in sdd and "operator-genesis" not in sdd


def test_operator_genesis_namespace_isolation():
    """Rule 9.32.4：operator-genesis 與維度/詞彙/calibration 命名空間分開治理。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert ML.is_operator_genesis_fingerprint("operator-genesis:abc")
    assert not ML.is_operator_genesis_fingerprint("value-dimension:abc")
    assert not ML.is_operator_genesis_fingerprint("vocab-genesis:abc")
    assert not ML.is_calibration_fingerprint("operator-genesis:abc")
    assert not ML.is_dimension_fingerprint("operator-genesis:abc")


def test_dim_op_max_env(monkeypatch):
    monkeypatch.delenv("SDD_DIM_OP_MAX", raising=False)
    assert MM.dim_op_max() == 16
    monkeypatch.setenv("SDD_DIM_OP_MAX", "999")
    assert MM.dim_op_max() == 64
    monkeypatch.setenv("SDD_DIM_OP_MAX", "0")
    assert MM.dim_op_max() == 1


def test_dim_op_step_max_env(monkeypatch):
    monkeypatch.delenv("SDD_DIM_OP_STEP_MAX", raising=False)
    assert MM.dim_op_step_max() == 8


def test_guard_operator_computability_cost_ceiling(monkeypatch):
    """Rule 9.32.3：算子 cost 超 step_max → OperatorComputabilityExceeded。"""
    monkeypatch.setenv("SDD_DIM_OP_STEP_MAX", "1")
    go = GenesisOperator.of("max", "diff", secondary="min")   # cost=3 > 1
    with pytest.raises(MM.OperatorComputabilityExceeded):
        MM.guard_operator_computability(go)


def test_guard_operator_computability_nontotal():
    """Rule 9.32.3：非全函式算子 → OperatorComputabilityExceeded。"""
    class _Bad:
        name = "op::bad"
        def cost(self):
            return 2
        def is_total(self, *, samples=None):
            return False
    with pytest.raises(MM.OperatorComputabilityExceeded):
        MM.guard_operator_computability(_Bad())


def test_guard_operator_computability_passes_legit():
    go = GenesisOperator.of("mean", "identity")
    r = MM.guard_operator_computability(go)
    assert r.allowed and r.total and r.cost <= r.step_max


def test_guard_operator_genesis_stock_ceiling(tmp_path, monkeypatch):
    """Rule 9.32.4：算子 stock 觸頂 → OperatorCardinalityExceeded + meta_state ESCALATION。"""
    monkeypatch.setenv("SDD_DIM_OP_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    prims = ["mean", "max", "min", "sum", "range"]
    for i in range(2):
        OG.adopt_genesis_operator(GenesisOperator.of(prims[i], "identity"), 40 + i,
                                  human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    with pytest.raises(MM.OperatorCardinalityExceeded):
        OG.adopt_genesis_operator(GenesisOperator.of(prims[2], "identity"), 99,
                                  human_signoff=True, ledger_path=led)


def test_adopt_operator_happy_path(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    go = GenesisOperator.of("max", "diff", secondary="min")
    ev = OG.adopt_genesis_operator(go, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint == go.fingerprint()
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert go.fingerprint() in ML.active_operator_genesis_features(ledger_path=led)


# ---------------------------------------------------------------------------
# ACT-144 — steersman 算子外發明 diff + 可計算性證據（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_operator_round(k=1):
    cands = OG.enumerate_genesis_operators(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda o: scores.get(o.name, 0.0)
    return OG.operator_genesis_round(ev, candidates=cands, k=k)


def test_render_operator_genesis_proposal():
    from tools.fsm_runtime.steersman_renderer import render_operator_genesis_proposal
    rnd = _accepted_operator_round(k=1)
    verdict = DO.evaluate_genesis_operator(
        GenesisOperator.of("max", "diff", secondary="min"), [_true_operator_case()], coverage_margin=0.1)
    md = render_operator_genesis_proposal(rnd, verdict=verdict)
    assert "Self-Expanding Operator Grammar" in md
    assert "OPS 外" in md
    assert "K_op=1" in md
    assert "signoff" in md and "待人工" in md
    assert "全函式" in md and "cost" in md           # 可計算性證據
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].operator.name in md


def test_render_operator_genesis_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_operator_genesis_proposal
    rnd = _accepted_operator_round(k=1)
    md = render_operator_genesis_proposal(rnd)
    assert "K_op=1" in md
    assert rnd.deferred[0] in md


def test_render_operator_genesis_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_operator_genesis_proposal)
    assert "record_rule_add" not in src and "adopt_genesis_operator" not in src


def test_render_operator_genesis_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_operator_genesis_proposal
    md = render_operator_genesis_proposal(_accepted_operator_round(k=1))
    assert "OPS 外" in md and "待人工" in md


# ---------------------------------------------------------------------------
# ACT-146 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_operator_genesis_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _operator_genesis_goodhart_flap_is_bounded
    assert _operator_genesis_goodhart_flap_is_bounded()


def test_chaos_operator_computability_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _operator_computability_flap_is_bounded
    assert _operator_computability_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "OPERATOR_GENESIS_GOODHART_FLAP" in FAULT_TYPES
    assert "OPERATOR_COMPUTABILITY_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase T ownership（R-9.32 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_t_enforces_rule_9_32():
    """本檔頭 `# enforces (governance rules): R-9.32` 連結 Phase T 守門至 R-9.32。"""
    head = (ROOT / "tests" / "test_phase_t.py").read_text(encoding="utf-8").splitlines()[0]
    assert head == "# enforces (governance rules): R-9.32"
