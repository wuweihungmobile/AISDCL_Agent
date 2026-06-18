# enforces (governance rules): R-9.28
"""Phase P / ACT-117~122 — 全評分器一體化自校準的耦合感知有界元最佳化 回歸守門.

涵蓋：
  - ACT-117 Scorer Calibration Registry：8 評分器登記、ScorerTuner 泛化骨架、bounded 格點、
    deterministic、只透過注入 evaluate 評分（結構性無自評）、proposed-only、反 big-bang K 截斷
  - ACT-118 Joint Calibration Oracle：pipeline 級聯合 held-out 評估、跨評分器接縫 Goodhart
    零漏放、joint tier = 聯合唯一來源、per 通過但 joint 不通過以 joint 為準、tuner↔oracle 隔離
  - ACT-119 CrossScorerChurnBounded：聚合採納速率有界、耦合震盪→MFSM_ESCALATION、不增第六軌
  - ACT-120 steersman 整體價值系統 diff（advisory + 反 big-bang + 人工 gate）
  - ACT-122 chaos CROSS_SCORER_GOODHART_FLAP / JOINT_CALIBRATION_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import scorer_calibration_registry as CR
from tools.fsm_runtime.scorer_calibration_registry import CalibrationProfile, ScorerSpec

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 共用：合成 per-scorer 評估器（distance-to-target；ACT-117 自足，不依賴 oracle）
# ---------------------------------------------------------------------------

def _target_evaluator(target: dict):
    """距離 target 越近真實品質越高（clamp[0,1]）。模擬「某組權重在 held-out 上真實更好」。"""
    def ev(profile: CalibrationProfile) -> float:
        d = sum(abs(profile.weight(k) - v) for k, v in target.items())
        return round(max(0.0, 1.0 - 0.2 * d), 6)
    return ev


# ---------------------------------------------------------------------------
# ACT-117 — Scorer Calibration Registry + ScorerTuner 泛化骨架
# ---------------------------------------------------------------------------

def test_registry_registers_all_eight_scorers():
    names = {s.name for s in CR.all_specs()}
    assert names == {"objective", "adversarial", "fragility", "ambiguity",
                     "oqs", "debate", "trajectory", "comp_fragility"}


def test_registry_wired_trio_plus_objective():
    """OPEN-P.3 預設：骨架一次到位（8 登記），具體接入高耦合三器 + objective（wired）。"""
    wired = {s.name for s in CR.wired_specs()}
    assert wired == {"objective", "adversarial", "fragility", "ambiguity"}
    # 其餘 4 器登記命名空間但 staged（接入分批）
    staged = {s.name for s in CR.all_specs() if not s.wired}
    assert staged == {"oqs", "debate", "trajectory", "comp_fragility"}


def test_namespaces_all_profile_suffixed():
    """全部 calibration 命名空間以 `-profile:` 結尾（供聚合停機指紋過濾，Rule 9.28.3）。"""
    for ns in CR.namespaces():
        assert ns.endswith("-profile:")
    assert CR.is_calibration_namespace("adversarial-profile:abc123")
    assert not CR.is_calibration_namespace("some-slv-rule-token-bag")


def test_version_const_paths_reference_frozen_scorers():
    """登記項唯讀參照各評分器凍結版本常數（honesty：tuner 只讀不寫，Rule 9.28.1/9.28.5）。"""
    obj = CR.get_spec("objective")
    assert obj.version_const == "composition_objective_scorer.OBJECTIVE_PROFILE_VERSION"
    assert CR.get_spec("adversarial").version_const.endswith("ADVERSARIAL_PROFILE_VERSION")
    assert CR.get_spec("fragility").version_const.endswith("FRAGILITY_PROFILE_VERSION")
    assert CR.get_spec("ambiguity").version_const.endswith("SCORER_VERSION")


def test_profile_fingerprint_namespaced_and_stable():
    p = CalibrationProfile.of("adversarial-profile:", {"attack_strength_w": 1.5, "breadth_w": 0.5})
    assert p.fingerprint().startswith("adversarial-profile:")
    # deterministic + 與 dict 插入序無關
    q = CalibrationProfile.of("adversarial-profile:", {"breadth_w": 0.5, "attack_strength_w": 1.5})
    assert p.fingerprint() == q.fingerprint()
    r = CalibrationProfile.of("adversarial-profile:", {"attack_strength_w": 2.0, "breadth_w": 0.5})
    assert p.fingerprint() != r.fingerprint()


def test_candidate_grid_search_bounded():
    spec = CR.get_spec("adversarial")
    grid = CR.candidate_grid(spec, budget=8)
    assert len(grid) <= 8                            # SearchBounded（Rule 9.28.1）
    assert spec.incumbent() not in grid              # 排除 incumbent 自身


def test_candidate_grid_deterministic():
    spec = CR.get_spec("fragility")
    assert CR.candidate_grid(spec, budget=12) == CR.candidate_grid(spec, budget=12)


def test_candidate_grid_empty_for_staged():
    """staged（wired=False）評分器無格點（接入分批）。"""
    assert CR.candidate_grid(CR.get_spec("debate")) == []


def test_tune_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_CALIB_TUNE_BUDGET", raising=False)
    assert CR.calib_tune_budget() == 64
    monkeypatch.setenv("SDD_CALIB_TUNE_BUDGET", "9999")
    assert CR.calib_tune_budget() == 256
    monkeypatch.setenv("SDD_CALIB_TUNE_BUDGET", "1")
    assert CR.calib_tune_budget() == 8
    monkeypatch.setenv("SDD_CALIB_TUNE_BUDGET", "x")
    assert CR.calib_tune_budget() == 64


def test_bigbang_k_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_CALIB_BIGBANG_K", raising=False)
    assert CR.calib_bigbang_k() == 2
    monkeypatch.setenv("SDD_CALIB_BIGBANG_K", "99")
    assert CR.calib_bigbang_k() == 16
    monkeypatch.setenv("SDD_CALIB_BIGBANG_K", "0")
    assert CR.calib_bigbang_k() == 1


def test_propose_finds_improvement():
    """tuner 在 incumbent 次優的注入評估上找到真實改進（達 margin、送 signoff）。"""
    spec = CR.get_spec("adversarial")    # incumbent {1.0, 0.5}
    ev = _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0})
    prop = CR.propose(spec, ev)
    assert prop.accepted
    assert prop.candidate.weight("attack_strength_w") == 2.0
    assert prop.win_delta >= prop.win_margin
    assert prop.to_dict()["maturity"] == "proposed"


def test_propose_search_bounded():
    spec = CR.get_spec("ambiguity")
    ev = _target_evaluator({"block_threshold_w": 2.0, "dimension_w": 1.0})
    prop = CR.propose(spec, ev, budget=8)
    assert prop.nodes_searched <= 8


def test_propose_deterministic():
    spec = CR.get_spec("fragility")
    ev = _target_evaluator({"threshold_w": 2.0, "history_w": 0.5})
    p1 = CR.propose(spec, ev)
    p2 = CR.propose(spec, ev)
    assert p1.candidate == p2.candidate and p1.win_delta == p2.win_delta


def test_propose_no_improvement_when_incumbent_optimal():
    spec = CR.get_spec("adversarial")
    ev = _target_evaluator(spec.incumbent_weights)   # target = incumbent → 無候選更優
    prop = CR.propose(spec, ev)
    assert not prop.accepted


def test_propose_only_uses_injected_evaluate():
    seen = []

    def spy(profile):
        seen.append(profile)
        return 0.0
    CR.propose(CR.get_spec("adversarial"), spy, budget=8)
    assert len(seen) >= 1


# ---------------------------------------------------------------------------
# ACT-117 驗收 — 每 wired 評分器 4 情境 fixture（scorer × 情境 parametrize；合計 16，
# 連同上方既有 propose 系列覆蓋藍圖「約 28 fixture」要求）。
#
# 對齊藍圖 §3.1 ACT-117 驗收：「對每個新接入評分器 ≥4 fixture（incumbent 次優〔應提更優〕/
# incumbent 已最優〔應不提案〕/ Goodhart 誘餌〔自評高真實差〕/ deterministic 可重現），
# 合計約 28 fixture」。四個 wired 評分器（objective / adversarial / fragility / ambiguity）
# 各 4 情境 → 16 組；上方既有 9 條 propose/round 系列（adversarial/fragility/ambiguity 代表性）
# 補足至約 28 組覆蓋面。objective_tuner 既有 test_phase_o.py 不受影響（零回歸）。
# ---------------------------------------------------------------------------

# 每個 wired 評分器的「真實改進目標」（遠離 incumbent 的格點，注入評估器獎勵它）
_IMPROVE_TARGET = {
    "objective":   {"batch_w": 2.0, "latency_w": 0.5},
    "adversarial": {"attack_strength_w": 2.0, "breadth_w": 1.0},
    "fragility":   {"threshold_w": 2.0, "history_w": 0.5},
    "ambiguity":   {"block_threshold_w": 2.0, "dimension_w": 1.0},
}
# 每個評分器的「Goodhart 誘餌」格點：自評（naive 自評器）給高分、但注入的真實 held-out
# 品質為 0（自評高、真實差）。tuner 只看注入 evaluate（真實），結構性無法選中誘餌。
_GOODHART_DECOY = {
    "objective":   {"batch_w": 0.0, "latency_w": 0.0},
    "adversarial": {"attack_strength_w": 0.0, "breadth_w": 0.0},
    "fragility":   {"threshold_w": 0.5, "history_w": 0.0},
    "ambiguity":   {"block_threshold_w": 0.5, "dimension_w": 0.0},
}
_WIRED_SCORERS = ["objective", "adversarial", "fragility", "ambiguity"]


@pytest.mark.parametrize("scorer", _WIRED_SCORERS)
def test_scorer_fixture_incumbent_suboptimal_proposes(scorer):
    """情境①：incumbent 次優 → tuner 在注入 held-out 上找到更優候選並達 margin（送 signoff）。"""
    spec = CR.get_spec(scorer)
    ev = _target_evaluator(_IMPROVE_TARGET[scorer])
    prop = CR.propose(spec, ev)
    assert prop.accepted, f"{scorer}：incumbent 次優時應提更優候選"
    assert prop.win_delta >= prop.win_margin
    assert prop.candidate != spec.incumbent()
    assert prop.to_dict()["maturity"] == "proposed"     # 只提案、不自動 commit


@pytest.mark.parametrize("scorer", _WIRED_SCORERS)
def test_scorer_fixture_incumbent_optimal_no_proposal(scorer):
    """情境②：incumbent 已最優（target=incumbent）→ 格點內無更優 → 不提案。"""
    spec = CR.get_spec(scorer)
    ev = _target_evaluator(spec.incumbent_weights)
    prop = CR.propose(spec, ev)
    assert not prop.accepted, f"{scorer}：incumbent 已最優時不應提案"


@pytest.mark.parametrize("scorer", _WIRED_SCORERS)
def test_scorer_fixture_goodhart_decoy_not_selected(scorer):
    """情境③：Goodhart 誘餌（自評高、真實差）→ tuner 只看注入真實品質 → 結構性不選中誘餌。"""
    spec = CR.get_spec(scorer)
    decoy = CalibrationProfile.of(spec.namespace, _GOODHART_DECOY[scorer])
    assert decoy in CR.candidate_grid(spec)              # 誘餌確在搜尋格點內（有機會被誤選）
    truth = _target_evaluator(_IMPROVE_TARGET[scorer])
    # 注入「真實」評估器：誘餌真實品質 0（自評高但真實差），其餘照真實獎勵改進目標。
    def truth_ev(profile, _decoy=decoy, _truth=truth):
        return 0.0 if profile.as_dict() == _decoy.as_dict() else _truth(profile)
    prop = CR.propose(spec, truth_ev)
    assert prop.candidate.as_dict() != decoy.as_dict(), \
        f"{scorer}：tuner 不得選中自評高/真實差的 Goodhart 誘餌（反自評紀律）"


@pytest.mark.parametrize("scorer", _WIRED_SCORERS)
def test_scorer_fixture_deterministic(scorer):
    """情境④：同一注入評估器兩次 propose 完全可重現（deterministic）。"""
    spec = CR.get_spec(scorer)
    ev = _target_evaluator(_IMPROVE_TARGET[scorer])
    p1 = CR.propose(spec, ev)
    p2 = CR.propose(spec, ev)
    assert p1.candidate == p2.candidate
    assert p1.win_delta == p2.win_delta and p1.accepted == p2.accepted
    assert p1.nodes_searched == p2.nodes_searched


def test_registry_structurally_blind_to_oracle():
    """Rule 9.28.2：registry/tuner **不得 import** 任何 oracle、不得觸及 held-out 語料（對抗分離）。"""
    tree = ast.parse(inspect.getsource(CR))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {a.name for a in node.names}
    assert not any("oracle" in m.lower() for m in imported), "registry 不得 import oracle（破對抗分離）"
    assert not any("held_out" in m.lower() or "held-out" in m.lower() for m in imported)


# ---- 反 big-bang 一輪提案（Rule 9.28.4）----

def test_propose_round_respects_bigbang_k():
    """一輪至多 K 個評分器進 proposed（按 win_delta 取前 K），其餘順延（Rule 9.28.4）。"""
    evaluators = {
        "adversarial": _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0}),
        "fragility": _target_evaluator({"threshold_w": 2.0, "history_w": 0.5}),
        "ambiguity": _target_evaluator({"block_threshold_w": 2.0, "dimension_w": 1.0}),
    }
    rnd = CR.propose_round(evaluators, k=2)
    assert len(rnd.selected) == 2
    assert len(rnd.deferred) == 1
    # selected 為 win_delta 最高的兩個
    assert all(p.accepted for p in rnd.selected)


def test_propose_round_k1_defers_rest():
    evaluators = {
        "adversarial": _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0}),
        "fragility": _target_evaluator({"threshold_w": 2.0, "history_w": 0.5}),
    }
    rnd = CR.propose_round(evaluators, k=1)
    assert len(rnd.selected) == 1 and len(rnd.deferred) == 1


def test_value_vector_shape():
    evaluators = {"adversarial": _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0})}
    rnd = CR.propose_round(evaluators, k=2)
    vv = rnd.value_vector()
    assert "adversarial" in vv and isinstance(vv["adversarial"], CalibrationProfile)


def test_record_round_writes_pending_signoff(tmp_path):
    evaluators = {"adversarial": _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0})}
    rnd = CR.propose_round(evaluators, k=2)
    led = tmp_path / "scorer-calibration-ledger.yaml"
    entry = CR.record_round(rnd, ledger_path=led, ts="2026-06-03T00:00:00+00:00")
    assert led.exists()
    assert entry["signoff"] == "pending"
    assert all(p["maturity"] == "proposed" for p in entry["selected"])


# ---- 採納走既有 META_FSM（共用 churn）+ 人工 signoff（Rule 9.28.1/9.28.3）----

def test_adopt_requires_human_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    prof = CalibrationProfile.of("adversarial-profile:", {"attack_strength_w": 2.0, "breadth_w": 1.0})
    with pytest.raises(CR.SignoffRequired):
        CR.adopt_profile(prof, 90, ledger_path=led)
    assert not led.exists()


def test_adopt_goes_through_meta_guard(tmp_path):
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    led = tmp_path / "meta-loop-ledger.yaml"
    prof = CalibrationProfile.of("fragility-profile:", {"threshold_w": 2.0, "history_w": 0.5})
    ev = CR.adopt_profile(prof, 90, human_signoff=True, ledger_path=led)
    assert ev.fingerprint.startswith("fragility-profile:")
    assert ML.compute_churn(ev.fingerprint, ledger_path=led) == 0      # 首採納非 churn


# ---------------------------------------------------------------------------
# ACT-119（meta 側聚合守門）— CrossScorerChurnBounded（與 registry.adopt 串接）
# ---------------------------------------------------------------------------

def _distinct_profiles(n: int):
    """產 n 個跨多評分器命名空間的 distinct calibration profile（每個首採、per-fingerprint churn=0）。"""
    specs = ["adversarial-profile:", "fragility-profile:", "ambiguity-profile:", "obj-profile:"]
    out = []
    for i in range(n):
        ns = specs[i % len(specs)]
        out.append(CalibrationProfile.of(ns, {"w": float(i)}))
    return out


def test_cross_scorer_aggregate_rate_bounded(tmp_path, monkeypatch):
    """Rule 9.28.3：聚合採納速率觸頂 → CrossScorerChurnExceeded（per-fingerprint 各自 churn=0）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_CALIB_ADOPT_RATE_MAX", raising=False)
    monkeypatch.delenv("SDD_CALIB_ADOPT_WINDOW", raising=False)
    rate_max = MM.calib_adopt_rate_max()              # 預設 6
    led = tmp_path / "meta-loop-ledger.yaml"
    profs = _distinct_profiles(rate_max + 1)
    for p in profs[:rate_max]:                        # 前 rate_max 個成功（窗內 < max）
        CR.adopt_profile(p, 1, human_signoff=True, ledger_path=led)
    with pytest.raises(MM.CrossScorerChurnExceeded):  # 第 rate_max+1 個觸頂
        CR.adopt_profile(profs[rate_max], 1, human_signoff=True, ledger_path=led)


def test_cross_scorer_storm_escalates_meta_state(tmp_path, monkeypatch):
    """聚合速率觸頂使整個 META_FSM meta_state → MFSM_ESCALATION（Rule 9.28.3）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_CALIB_ADOPT_RATE_MAX", raising=False)
    rate_max = MM.calib_adopt_rate_max()
    led = tmp_path / "meta-loop-ledger.yaml"
    for p in _distinct_profiles(rate_max):            # 採滿 rate_max → 窗內 == max
        CR.adopt_profile(p, 1, human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_aggregate_guard_ignores_non_calibration(tmp_path, monkeypatch):
    """非 calibration 指紋（SLV 規則）不受聚合速率守門影響（不誤傷既有元迴圈）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    res = MM.guard_calibration_adoption("some-slv-rule-normalized-tokenbag", ledger_path=led)
    assert res.allowed and res.window_adds == 0


def test_coupling_message_flags_multi_namespace(tmp_path, monkeypatch):
    """聚合觸頂訊息標示『跨評分器耦合震盪』（≥2 命名空間）vs『單評分器抖動』。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_CALIB_ADOPT_RATE_MAX", raising=False)
    rate_max = MM.calib_adopt_rate_max()
    led = tmp_path / "meta-loop-ledger.yaml"
    for p in _distinct_profiles(rate_max):            # 跨 4 命名空間 → 耦合
        CR.adopt_profile(p, 1, human_signoff=True, ledger_path=led)
    with pytest.raises(MM.CrossScorerChurnExceeded, match="耦合震盪"):
        CR.adopt_profile(CalibrationProfile.of("obj-profile:", {"w": 999.0}), 1,
                         human_signoff=True, ledger_path=led)


# ---------------------------------------------------------------------------
# 不增第六軌（Rule 9.28.3）
# ---------------------------------------------------------------------------

def test_no_sixth_formal_track():
    """Rule 9.28.3：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_meta_fsm_states_unchanged():
    """META_FSM.tla 狀態宇宙不因 calibration 改動（仍 5 態，calibration 共用不新增狀態）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_meta_fsm_declares_cross_scorer_invariant():
    """ACT-119：META_FSM.tla 定義 CrossScorerChurnBounded，且 .cfg INVARIANT 區塊列入（TLC 會檢查）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "CrossScorerChurnBounded ==" in tla
    assert "CrossScorerChurnBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.28.3：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla


def test_single_track_no_calibration_leak():
    """Rule 9.28.3：calibration 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "CALIB" not in sdd and "-profile:" not in sdd


# ---------------------------------------------------------------------------
# ACT-118 — Joint Calibration Oracle（pipeline 級聯合反 Goodhart）
# ---------------------------------------------------------------------------

from tools.fsm_runtime import joint_calibration_oracle as JO   # noqa: E402


def _seam_goodhart_corpus():
    """接縫 Goodhart：incumbent 向量選 GOOD（0.9）；弱化 adversarial 後選 BAD（0.2）。"""
    return [JO.JointHeldOutCase(
        case_id="SEAM-1",
        candidates=[
            JO.JointCandidate(real_quality=0.9, features={
                "adversarial": {"attack_strength_w": 0.5, "breadth_w": 0.5},
                "fragility": {"threshold_w": 1.0, "history_w": 1.0},
                "ambiguity": {"block_threshold_w": 1.0, "dimension_w": 1.0}}),
            JO.JointCandidate(real_quality=0.2, features={
                "adversarial": {"attack_strength_w": 5.0, "breadth_w": 0.0},
                "fragility": {"threshold_w": 0.0, "history_w": 0.0},
                "ambiguity": {"block_threshold_w": 0.0, "dimension_w": 0.0}}),
        ])]


def _true_improvement_corpus():
    """真實聯合改進：objective latency 調高 → 從次優 A(0.3) 翻到真實最優 GOOD(0.9)。"""
    return [JO.JointHeldOutCase(
        case_id="TRUE-1",
        candidates=[
            JO.JointCandidate(real_quality=0.3, features={
                "objective": {"batch_w": 2.0, "latency_w": 11.0}}),   # A 早排晚、latency 高
            JO.JointCandidate(real_quality=0.9, features={
                "objective": {"batch_w": 3.0, "latency_w": 3.0}}),    # GOOD 多一批但 latency 低
        ])]


def _adv_weakened_vector():
    inc = JO.incumbent_vector()
    weak = CalibrationProfile.of("adversarial-profile:", {"attack_strength_w": 0.0, "breadth_w": 0.5})
    return JO.apply_selection(inc, {"adversarial": weak}), inc


def test_incumbent_vector_covers_wired():
    vec = JO.incumbent_vector()
    assert set(vec) == {"objective", "adversarial", "fragility", "ambiguity"}
    assert vec["objective"].weight("latency_w") == 0.1


def test_select_argmin_joint_cost():
    corpus = _seam_goodhart_corpus()
    inc = JO.incumbent_vector()
    assert corpus[0].real_quality_under(inc) == 0.9          # incumbent 選 GOOD


def test_seam_goodhart_rejected_by_joint_oracle():
    """安全紅線：弱化 adversarial → 選中整體很差的 BAD → 聯合真實品質崩 → 不達 margin（零漏放）。"""
    cand_vec, inc_vec = _adv_weakened_vector()
    v = JO.evaluate_joint(cand_vec, inc_vec, _seam_goodhart_corpus(), win_margin=0.1)
    assert v.candidate_quality == 0.2 and v.incumbent_quality == 0.9
    assert v.win_delta == pytest.approx(-0.7)
    assert not v.passes_margin                               # 接縫 Goodhart 必被攔
    assert v.changed_scorers == ["adversarial"]


def test_per_scorer_passes_but_joint_fails():
    """關鍵：adversarial 弱化在 per-scorer 樸素評估上『通過』，但 pipeline 聯合 oracle 否決 → 以 joint 為準。"""
    # (a) per-scorer 樸素視角：攻擊越弱「看起來越好」（盲於接縫）→ propose 接受弱化
    spec = CR.get_spec("adversarial")
    naive_ev = lambda p: round(1.0 - 0.2 * p.weight("attack_strength_w"), 6)
    per = CR.propose(spec, naive_ev)
    assert per.accepted and per.candidate.weight("attack_strength_w") == 0.0
    # (b) 但聯合 oracle 在 pipeline held-out 上否決同一弱化
    cand_vec, inc_vec = _adv_weakened_vector()
    joint = JO.evaluate_joint(cand_vec, inc_vec, _seam_goodhart_corpus(), win_margin=0.1)
    assert not joint.passes_margin
    # 結論：per 通過、joint 不通過 → 採納須以 joint 為準（拒絕）


def test_true_joint_improvement_passes():
    """真實聯合改進（objective latency 校準）→ 達 margin、取得 joint tier。"""
    inc = JO.incumbent_vector()
    tuned = JO.apply_selection(inc, {"objective":
                                     CalibrationProfile.of("obj-profile:", {"batch_w": 1.0, "latency_w": 0.35})})
    v = JO.evaluate_joint(tuned, inc, _true_improvement_corpus(), win_margin=0.1)
    assert v.candidate_quality == 0.9 and v.incumbent_quality == 0.3
    assert v.passes_margin and v.win_delta == pytest.approx(0.6)
    assert v.tier == 90                                      # joint tier = held-out 真實品質


def test_joint_tier_from_held_out_only():
    inc = JO.incumbent_vector()
    tuned = JO.apply_selection(inc, {"objective":
                                     CalibrationProfile.of("obj-profile:", {"batch_w": 1.0, "latency_w": 0.35})})
    v = JO.evaluate_joint(tuned, inc, _true_improvement_corpus(), win_margin=0.1)
    assert v.tier == int(round(v.candidate_quality * 100))


def test_evaluate_vector_bounded(monkeypatch):
    corpus = _seam_goodhart_corpus() * 100
    inc = JO.incumbent_vector()
    v = JO.evaluate_joint(inc, inc, corpus, win_margin=0.1, max_cases=5)
    assert v.examined == 5


def test_joint_corpus_fingerprint_tamper_and_stable():
    base = _seam_goodhart_corpus()
    assert JO.corpus_fingerprint(base) == JO.corpus_fingerprint(_seam_goodhart_corpus())
    tampered = _seam_goodhart_corpus()
    tampered[0].candidates[1].real_quality = 0.9            # 竄改 BAD 真實品質
    assert JO.corpus_fingerprint(base) != JO.corpus_fingerprint(tampered)


def test_load_joint_corpus_from_disk():
    """凍結 JOINT-001.yaml 可載入，且接縫 Goodhart 效應與 in-memory 版一致。"""
    corpus = JO.load_joint_corpus()
    assert any(c.case_id == "JOINT-001" for c in corpus)
    seam = [c for c in corpus if c.case_id == "JOINT-001"]
    cand_vec, inc_vec = _adv_weakened_vector()
    v = JO.evaluate_joint(cand_vec, inc_vec, seam, win_margin=0.1)
    assert v.incumbent_quality == 0.9 and v.candidate_quality == 0.2
    assert not v.passes_margin


def test_generator_cannot_reach_joint_corpus():
    """Rule 9.28.2 對抗分離：registry（生成器）無法觸及聯合語料載入符號/路徑。"""
    assert not hasattr(CR, "load_joint_corpus")
    assert not hasattr(CR, "JointHeldOutCase")
    # registry 原始碼不得 import joint oracle（已於 test_registry_structurally_blind_to_oracle 覆蓋；此處雙保險）
    src = inspect.getsource(CR)
    assert "joint_calibration_oracle" not in src


# ---------------------------------------------------------------------------
# ACT-118 驗收 — 18 凍結聯合語料統計性驗收（9 真優 + 9 接縫 Goodhart 假優；零漏放）
#
# 對齊藍圖 §3.1 ACT-118 驗收：「18 fixture（9 真優〔聯合勝率 ≥ margin〕+ 9 接縫 Goodhart
# 假優〔每個 per-scorer oracle 單獨通過、整套 pipeline 聯合輸〕）；真優偵出率 ≥ 85%、
# 接縫 Goodhart 假優攔截率 100%（零漏放）」。本組以 knowledge/held-out-corpus/JOINT-002~019
# 的**磁碟凍結語料**，經**真實** joint oracle（load_joint_corpus → evaluate_joint）重放，
# 非 in-memory 代表案例——確保「實作交付」對齊藍圖驗收文字。
# ---------------------------------------------------------------------------

import yaml as _yaml  # noqa: E402

_JOINT_MARGIN = 0.1
# per-scorer 樸素評估器（盲於接縫）：對「弱化/放寬」一律給高分（局部自洽），模擬
# 每個 per-scorer oracle 單獨通過——這正是接縫 Goodhart「per 通過、joint 不通過」的前提。
_SEAM_NAIVE_TUNED_DIM = {
    "objective": "latency_w", "adversarial": "attack_strength_w",
    "fragility": "threshold_w", "ambiguity": "block_threshold_w",
}


def _load_joint_yaml_meta():
    """讀 JOINT-002~019 的 meta（case_id / expect / tuned_scorer / candidate_profile）。"""
    out = []
    for p in sorted(JO.HELD_OUT_CORPUS_DIR.glob("JOINT-*.yaml")):
        doc = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if doc.get("expect") in ("true_optimum", "seam_goodhart"):
            out.append(doc)
    return out


def _verdict_for(doc):
    """以磁碟凍結語料 + 真實 oracle 算出該 case 的聯合 verdict。"""
    cid, scorer = doc["case_id"], doc["tuned_scorer"]
    cp = doc["candidate_profile"]
    cand_prof = CalibrationProfile.of(cp["namespace"],
                                      {k: float(v) for k, v in cp["weights"].items()})
    case = [c for c in JO.load_joint_corpus() if c.case_id == cid]
    assert case, f"{cid} 未能自磁碟載入"
    inc = JO.incumbent_vector()
    cand_vec = JO.apply_selection(inc, {scorer: cand_prof})
    return JO.evaluate_joint(cand_vec, inc, case, win_margin=_JOINT_MARGIN)


def test_joint_corpus_has_18_labelled_cases():
    """磁碟落地 9 真優 + 9 接縫 Goodhart 假優（共 18），對齊 ACT-118 驗收條。"""
    metas = _load_joint_yaml_meta()
    true_cases = [m for m in metas if m["expect"] == "true_optimum"]
    seam_cases = [m for m in metas if m["expect"] == "seam_goodhart"]
    assert len(true_cases) == 9, f"真優 fixture 應為 9，實得 {len(true_cases)}"
    assert len(seam_cases) == 9, f"接縫 Goodhart 假優 fixture 應為 9，實得 {len(seam_cases)}"
    # 覆蓋全部 4 個 wired 評分器（接縫不只壓在單一評分器上）
    assert {m["tuned_scorer"] for m in metas} == {"objective", "adversarial", "fragility", "ambiguity"}


@pytest.mark.parametrize("doc", [m for m in _load_joint_yaml_meta()
                                 if m["expect"] == "true_optimum"],
                         ids=lambda d: d["case_id"])
def test_joint_true_optimum_detected(doc):
    """每個真優案例：候選向量在 pipeline 級聯合重放整體真實勝率 ≥ incumbent + margin。"""
    v = _verdict_for(doc)
    assert v.candidate_quality > v.incumbent_quality
    assert v.passes_margin, f"{doc['case_id']} 真優卻未達 margin（Δ={v.win_delta}）"
    assert v.tier == int(round(v.candidate_quality * 100))   # joint tier = held-out 真實品質


@pytest.mark.parametrize("doc", [m for m in _load_joint_yaml_meta()
                                 if m["expect"] == "seam_goodhart"],
                         ids=lambda d: d["case_id"])
def test_joint_seam_goodhart_intercepted(doc):
    """每個接縫 Goodhart 假優：per-scorer 樸素視角『通過』，但 pipeline 聯合 oracle 必否決（零漏放）。"""
    # (a) per-scorer 樸素：弱化/放寬看起來『沒退步』（局部自洽）→ 若無聯合 oracle 就中招。
    # 樸素 per-scorer oracle 盲於接縫，只看「該評分器自己的尺規」——弱化 tuned 維度時，它認為
    # 候選 weak profile 不劣於（甚至優於）incumbent（這正是接縫 Goodhart「per 通過」的前提）。
    scorer = doc["tuned_scorer"]
    spec = CR.get_spec(scorer)
    tuned_dim = _SEAM_NAIVE_TUNED_DIM[scorer]
    cp = doc["candidate_profile"]
    weak = CalibrationProfile.of(cp["namespace"], {k: float(v) for k, v in cp["weights"].items()})
    naive = lambda p: round(1.0 - 0.2 * p.weight(tuned_dim), 6)   # 越弱越「好看」（盲於接縫）
    assert naive(weak) >= naive(spec.incumbent()), \
        f"{doc['case_id']} per-scorer 樸素視角應視弱化為不劣（接縫前提）"
    # (b) 但聯合 oracle 在 pipeline held-out 上否決同一弱化向量 → 以 joint 為準
    v = _verdict_for(doc)
    assert v.candidate_quality < v.incumbent_quality
    assert not v.passes_margin, f"{doc['case_id']} 接縫 Goodhart 漏放（Δ={v.win_delta}，安全紅線破！）"


def test_joint_acceptance_rates_meet_blueprint():
    """ACT-118 驗收統計：真優偵出率 ≥ 85%、接縫 Goodhart 假優攔截率 100%（零漏放）。"""
    metas = _load_joint_yaml_meta()
    true_cases = [m for m in metas if m["expect"] == "true_optimum"]
    seam_cases = [m for m in metas if m["expect"] == "seam_goodhart"]
    true_detected = sum(1 for m in true_cases if _verdict_for(m).passes_margin)
    seam_intercepted = sum(1 for m in seam_cases if not _verdict_for(m).passes_margin)
    assert true_detected / len(true_cases) >= 0.85, \
        f"真優偵出率 {true_detected}/{len(true_cases)} < 85%"
    assert seam_intercepted == len(seam_cases), \
        f"接縫 Goodhart 攔截率非 100%（{seam_intercepted}/{len(seam_cases)}，零漏放破！）"


def test_joint_corpus_tuner_isolation_preserved():
    """承 Rule 9.28.2：擴充 18 聯合語料後，生成器仍結構性看不到聯合語料（隔離不破）。"""
    src = inspect.getsource(CR)
    assert "joint_calibration_oracle" not in src
    assert "held-out-corpus" not in src and "held_out" not in src.lower()
    assert not hasattr(CR, "load_joint_corpus")


# ---------------------------------------------------------------------------
# ACT-120 — steersman 整體價值系統 diff（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_round(k=2):
    evaluators = {
        "adversarial": _target_evaluator({"attack_strength_w": 2.0, "breadth_w": 1.0}),
        "fragility": _target_evaluator({"threshold_w": 2.0, "history_w": 0.5}),
        "ambiguity": _target_evaluator({"block_threshold_w": 2.0, "dimension_w": 1.0}),
    }
    return CR.propose_round(evaluators, k=k)


def test_render_unified_calibration_proposal():
    from tools.fsm_runtime.steersman_renderer import render_unified_calibration_proposal
    rnd = _accepted_round(k=2)
    inc = JO.incumbent_vector()
    cand_vec = JO.apply_selection(inc, rnd.value_vector())
    verdict = JO.evaluate_joint(cand_vec, inc, _true_improvement_corpus(), win_margin=0.1)
    md = render_unified_calibration_proposal(rnd, joint_verdict=verdict)
    assert "整體價值系統" in md
    assert "Unified Scorer Calibration" in md
    assert "K=2" in md                                   # 反 big-bang 上限明示（Rule 9.28.4）
    assert "PROFILE_VERSION" in md                       # 人工 bump gate
    assert "待人工" in md
    assert "聯合" in md and verdict.corpus_fingerprint in md
    # 至少一個被選評分器的權重 diff 出現
    assert any(s.scorer_name in md for s in rnd.selected)


def test_render_shows_deferred_under_bigbang():
    """K=1 → 渲染明示順延的評分器（反 big-bang，Rule 9.28.4）。"""
    from tools.fsm_runtime.steersman_renderer import render_unified_calibration_proposal
    rnd = _accepted_round(k=1)
    md = render_unified_calibration_proposal(rnd)
    assert "K=1" in md
    assert rnd.deferred[0] in md                         # 順延者被列出


def test_render_unified_never_auto_commits():
    """渲染器純文字產出，不觸發任何採納/bump（無 record_rule_add / adopt_profile / bump 副作用）。"""
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_unified_calibration_proposal)
    assert "record_rule_add" not in src and "adopt_profile" not in src


def test_render_unified_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_unified_calibration_proposal
    rnd = _accepted_round(k=2)
    md = render_unified_calibration_proposal(rnd)         # 無 joint_verdict
    assert "整體價值系統" in md and "待人工" in md
