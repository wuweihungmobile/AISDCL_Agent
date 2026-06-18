# enforces (governance rules): R-9.24
"""Phase L（SDD_improving_Automation_12）測試套件 — M-L2 ACT-091/092.

涵蓋：
  - ACT-091 Counterfactual Replay Engine：命中 / 反例 / out-of-scope / inconclusive /
    重放預算 clamp / 報告落盤 / 12 可擋 + 12 不可擋驗收
  - ACT-092 EXPERIMENT_REPLAY 觀測態：入口/出口契約 + 三源/結構契約
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import counterfactual_replay as CR
from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    OBSERVATION_STATES, _HAPPY_PATH, TransitionError, is_transition_allowed,
)


def _rt(tmp_path: Path, name: str, src: str) -> FSMRuntime:
    state_path = tmp_path / f"FSM-STATE-{name}.yaml"
    state = load_state(name, path=state_path, create_if_missing=True)
    state.root["current_state"] = src
    save_state(state)
    return FSMRuntime(state)


# ---------- ACT-091: Counterfactual Replay Engine ----------

def test_replay_max_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_REPLAY_MAX_CASES", raising=False)
    assert CR.replay_max() == 50
    monkeypatch.setenv("SDD_REPLAY_MAX_CASES", "120")
    assert CR.replay_max() == 120
    monkeypatch.setenv("SDD_REPLAY_MAX_CASES", "9999")
    assert CR.replay_max() == 200    # 上界
    monkeypatch.setenv("SDD_REPLAY_MAX_CASES", "1")
    assert CR.replay_max() == 5      # 下界
    monkeypatch.setenv("SDD_REPLAY_MAX_CASES", "x")
    assert CR.replay_max() == 50     # 非數字 → 預設


def test_prevented_case_same_ac_covering_guard():
    patch = CR.PatchProposal(ac_id="AC-014",
                             guard_text="discount stacking forbidden when coupon applied")
    case = CR.HistoricalCase(case_id="FPL-010", ac_id="AC-014",
                             failure_text="discount stacking caused double coupon", source="fpl")
    rep = CR.replay(patch, [case])
    assert rep.verdict == "done"
    assert rep.prevented == 1 and rep.relevant_total == 1
    assert "FPL-010" in rep.prevented_ids


def test_counterexample_same_ac_but_unrelated_guard():
    patch = CR.PatchProposal(ac_id="AC-014",
                             guard_text="inventory decrement must be atomic")
    case = CR.HistoricalCase(case_id="FPL-011", ac_id="AC-014",
                             failure_text="discount stacking caused double coupon", source="fpl")
    rep = CR.replay(patch, [case])
    assert rep.verdict == "done"
    assert rep.prevented == 0
    assert "FPL-011" in rep.counterexample_ids


def test_out_of_scope_different_ac():
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="discount stacking forbidden")
    case = CR.HistoricalCase(case_id="FPL-099", ac_id="AC-200",
                             failure_text="login timeout", source="fpl")
    rep = CR.replay(patch, [case])
    assert rep.verdict == "inconclusive"   # 0 相關案例
    assert "FPL-099" in rep.out_of_scope_ids


def test_inconclusive_when_no_relevant_cases():
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="x")
    rep = CR.replay(patch, [])
    assert rep.verdict == "inconclusive"
    assert "歷史語料不足" in rep.evidence_line()


def test_fingerprint_relevance_when_no_ac_match():
    patch = CR.PatchProposal(ac_id="", fingerprint="fp-disc",
                             guard_text="discount stacking forbidden coupon")
    case = CR.HistoricalCase(case_id="C1", fingerprint="fp-disc",
                             failure_text="discount stacking coupon double", source="chaos")
    rep = CR.replay(patch, [case])
    assert rep.verdict == "done" and rep.prevented == 1


def test_acceptance_12_preventable_12_unpreventable():
    """ACT-091 驗收：12 可擋（命中率 ≥ 80%）+ 12 不可擋（誤報率 < 15%）。"""
    patch = CR.PatchProposal(ac_id="AC-014",
                             guard_text="discount stacking forbidden when coupon applied limit")
    preventable = [
        CR.HistoricalCase(case_id=f"P{i}", ac_id="AC-014",
                          failure_text=f"discount stacking coupon limit breach variant {i}")
        for i in range(12)
    ]
    # 不可擋：同 AC 但成因與補丁約束無關（反例），補丁 token 不覆蓋失敗 token
    unpreventable = [
        CR.HistoricalCase(case_id=f"N{i}", ac_id="AC-014",
                          failure_text=f"inventory ledger race timeout deadlock variant {i}")
        for i in range(12)
    ]
    rep = CR.replay(patch, preventable + unpreventable, max_cases=200)
    assert rep.relevant_total == 24
    # 12 可擋全中（命中率 ≥ 80%）
    assert rep.prevented >= 10, rep.prevented
    # 12 不可擋不被誤判為擋住（誤報率 < 15% → 誤報 < 2）
    false_positives = sum(1 for cid in rep.prevented_ids if cid.startswith("N"))
    assert false_positives < 2, false_positives


def test_replay_budget_caps_examined():
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="discount stacking forbidden")
    cases = [CR.HistoricalCase(case_id=f"C{i}", ac_id="AC-014",
                               failure_text="discount stacking coupon") for i in range(100)]
    rep = CR.replay(patch, cases, max_cases=5)
    assert rep.examined == 5


def test_report_writer(tmp_path):
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="discount stacking forbidden coupon")
    case = CR.HistoricalCase(case_id="FPL-010", ac_id="AC-014",
                             failure_text="discount stacking coupon double")
    rep = CR.replay(patch, [case])
    path = CR.write_report(patch, rep, out_dir=tmp_path, today="2026-06-03")
    assert path.exists()
    txt = path.read_text(encoding="utf-8")
    assert "反事實重放" in txt and "AC-014" in txt and "FPL-010" in txt


# ---------- ACT-092: EXPERIMENT_REPLAY 觀測態接線 ----------

def test_experiment_replay_enter_from_spec_patch(tmp_path):
    rt = _rt(tmp_path, "er-ok", "SPEC_PATCH_PROPOSAL")
    res = rt.enter_experiment_replay(ac_id="AC-014")
    assert res["entered"] is True
    assert rt.state.current == "EXPERIMENT_REPLAY"


def test_experiment_replay_enter_illegal_source(tmp_path):
    rt = _rt(tmp_path, "er-bad", "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_experiment_replay()


def test_experiment_replay_enter_idempotent(tmp_path):
    rt = _rt(tmp_path, "er-noop", "SPEC_PATCH_PROPOSAL")
    rt.enter_experiment_replay()
    res = rt.enter_experiment_replay()
    assert res.get("noop") is True


def test_experiment_replay_exit_done_to_spec_patch(tmp_path):
    rt = _rt(tmp_path, "er-done", "SPEC_PATCH_PROPOSAL")
    rt.enter_experiment_replay(ac_id="AC-014")
    res = rt.exit_experiment_replay("done", evidence="擋住 4/5 筆")
    assert res["to"] == "SPEC_PATCH_PROPOSAL"
    assert rt.state.current == "SPEC_PATCH_PROPOSAL"
    assert rt.state.root["experiment_replay_tracking"]["evidence"] == "擋住 4/5 筆"


def test_experiment_replay_exit_inconclusive_to_human(tmp_path):
    rt = _rt(tmp_path, "er-inc", "SPEC_PATCH_PROPOSAL")
    rt.enter_experiment_replay()
    res = rt.exit_experiment_replay("inconclusive")
    assert res["to"] == "HUMAN_PENDING"
    assert rt.state.current == "HUMAN_PENDING"


def test_experiment_replay_exit_invalid_decision(tmp_path):
    rt = _rt(tmp_path, "er-x", "SPEC_PATCH_PROPOSAL")
    rt.enter_experiment_replay()
    with pytest.raises(ValueError):
        rt.exit_experiment_replay("maybe")


def test_experiment_replay_exit_when_not_in_state(tmp_path):
    rt = _rt(tmp_path, "er-ns", "SPEC_PATCH_PROPOSAL")
    with pytest.raises(TransitionError):
        rt.exit_experiment_replay("done")


# ---------- 三源 / 結構契約 ----------

def test_experiment_replay_is_observation():
    assert "EXPERIMENT_REPLAY" in OBSERVATION_STATES


def test_happy_path_experiment_replay_targets():
    assert _HAPPY_PATH["EXPERIMENT_REPLAY"] == {"SPEC_PATCH_PROPOSAL", "HUMAN_PENDING"}


def test_spec_patch_to_experiment_replay_edge_added():
    assert "EXPERIMENT_REPLAY" in _HAPPY_PATH["SPEC_PATCH_PROPOSAL"]


def test_spec_patch_backward_compat_edges_preserved():
    # ACT-078 既有出口不得被破壞（加法式新增）
    assert {"HUMAN_PENDING", "ESCALATION"} <= _HAPPY_PATH["SPEC_PATCH_PROPOSAL"]


def test_experiment_replay_transition_allowed_as_observation():
    # 觀測態出口為合法 happy edge
    assert is_transition_allowed("EXPERIMENT_REPLAY", "SPEC_PATCH_PROPOSAL")
    assert is_transition_allowed("EXPERIMENT_REPLAY", "HUMAN_PENDING")


# ---------- ACT-093: Spec Fragility Scorer ----------

from tools.fsm_runtime import spec_fragility_scorer as FR
from tools.fsm_runtime.spec_localizer import RTMRow


def _fragile_rtm():
    """6 脆弱 AC（共享 FRD 大 blast + 0 TC + drift + escalation）+ 12 穩健 AC。"""
    fragile = [RTMRow(ac_id=f"AC-1{i:02d}", frd_id="F-001", nfr_id="", tc_ids=[])
               for i in range(6)]
    robust = [RTMRow(ac_id=f"AC-9{i:02d}", frd_id=f"F-9{i:02d}", nfr_id="",
                     tc_ids=[f"TC-9{i:02d}-1", f"TC-9{i:02d}-2", f"TC-9{i:02d}-3"])
              for i in range(12)]
    return fragile, robust


def test_fragility_profile_frozen():
    """Rule 9.24.5：評分強度凍結，調權重須 bump version（改下列任一值即 fail）。"""
    assert FR.FRAGILITY_PROFILE_VERSION == "v1.0"
    assert FR._WEIGHTS == {"blast": 0.30, "coverage_gap": 0.30, "drift": 0.25, "escalation": 0.15}
    assert round(sum(FR._WEIGHTS.values()), 4) == 1.0


def test_fragility_ranks_fragile_above_robust():
    """ACT-093 驗收（18 fixture）：top-3 全為脆弱 AC + 脆弱嚴格高於穩健（清晰分離）。"""
    fragile, robust = _fragile_rtm()
    fragile_ids = {r.ac_id for r in fragile}
    drift = {r.ac_id: 3 for r in fragile}
    escal = {r.ac_id for r in fragile}
    rep = FR.score_fragility(fragile + robust, drift_counts=drift, escalation_refs=escal)
    # top-3 命中率 ≥ 85% → 此處 3/3 = 100%
    top3 = rep.top(3)
    assert all(ac in fragile_ids for ac in top3), top3
    # 穩健 AC 不被誤列（誤報率 < 15%）：所有脆弱分數 > 所有穩健分數
    fragile_scores = [s.score for s in rep.scores if s.ac_id in fragile_ids]
    robust_scores = [s.score for s in rep.scores if s.ac_id not in fragile_ids]
    assert min(fragile_scores) > max(robust_scores)


def test_zero_tc_increases_coverage_gap():
    rep = FR.score_fragility([RTMRow(ac_id="AC-1", frd_id="F-1", tc_ids=[]),
                              RTMRow(ac_id="AC-2", frd_id="F-1",
                                     tc_ids=["TC-1", "TC-2", "TC-3", "TC-4"])])
    by = {s.ac_id: s for s in rep.scores}
    assert by["AC-1"].coverage_gap > by["AC-2"].coverage_gap


def test_fragility_report_markdown():
    fragile, robust = _fragile_rtm()
    rep = FR.score_fragility(fragile + robust, drift_counts={r.ac_id: 2 for r in fragile},
                             escalation_refs={r.ac_id for r in fragile})
    md = FR.fragility_report(rep, top_k=5)
    assert "規格脆弱性熱圖" in md and "profile_version" in md and "v1.0" in md


# ---------- ACT-094: 整合（steersman + intent_decomposer）----------

def test_steersman_render_fragility():
    from tools.fsm_runtime import steersman_renderer as SR
    fragile, robust = _fragile_rtm()
    md = SR.render_fragility(fragile + robust,
                             drift_counts={r.ac_id: 2 for r in fragile},
                             escalation_refs={r.ac_id for r in fragile}, top_k=3)
    assert "脆弱性" in md and "AC-1" in md   # top 脆弱 AC 現身熱圖


def test_intent_fragile_node_marking():
    """ACT-094：分解 DAG 節點落在脆弱領域則被標記（advisory，不改 acyclic 結構）。"""
    node_titles = {
        "N0": "下單流程主路徑",
        "N1": "折扣疊加規則 discount stacking",
        "N2": "庫存扣減",
    }
    flagged = FR.fragile_node_ids(node_titles, fragile_terms={"discount stacking coupon"})
    assert flagged == ["N1"]


def test_intent_fragile_node_marking_empty_when_no_overlap():
    flagged = FR.fragile_node_ids({"N0": "完全無關標題"}, fragile_terms={"discount stacking"})
    assert flagged == []


# ---------- 藍圖字面收口：§2.1 產物 + 指定 locus 整合 ----------

def test_fragility_write_report_file(tmp_path):
    """§2.1：build/reports/fragility/FRAGILITY-{date}.md 落盤 writer。"""
    fragile, robust = _fragile_rtm()
    rep = FR.score_fragility(fragile + robust, drift_counts={r.ac_id: 2 for r in fragile},
                             escalation_refs={r.ac_id for r in fragile})
    path = FR.write_report(rep, out_dir=tmp_path, today="2026-06-03")
    assert path.exists() and path.name == "FRAGILITY-2026-06-03.md"
    assert "規格脆弱性熱圖" in path.read_text(encoding="utf-8")


def test_spec_patch_proposer_attaches_replay_evidence(tmp_path):
    """ACT-092 字面 locus：spec_patch_proposer.propose() 附掛 replay 證據。"""
    from tools.fsm_runtime import spec_patch_proposer as SPP
    patch = CR.PatchProposal(ac_id="AC-014", guard_text="discount stacking forbidden coupon")
    case = CR.HistoricalCase(case_id="FPL-010", ac_id="AC-014",
                             failure_text="discount stacking coupon double")
    evidence = CR.replay(patch, [case]).evidence_line()
    prop = SPP.propose("AC-014", "原 AC 文字", [SPP.DefectSignal("AC-014", "discount defect")],
                       today="2026-06-03", out_dir=tmp_path, replay_evidence=evidence)
    txt = Path(prop.report_path).read_text(encoding="utf-8")
    assert "反事實重放證據" in txt and "擋住過去" in txt


def test_intent_decomposer_annotate_fragile():
    """ACT-094 字面 locus：intent_decomposer.annotate_fragile 標記脆弱節點，不改 DAG。"""
    from tools.fsm_runtime import intent_decomposer as ID
    dag = ID.decompose("- 下單流程\n- 折扣疊加規則 discount stacking\n- 庫存扣減")
    assert dag.status == "decomposed"
    flagged = ID.annotate_fragile(dag, fragile_terms={"discount stacking coupon"})
    titles = {n.node_id: n.title for n in dag.nodes}
    assert flagged and all("discount" in titles[nid].lower() for nid in flagged)
    assert dag.is_acyclic()   # 標記不改 acyclic 結構


def test_counterfactual_crystallize_experiment_patterns(tmp_path):
    """§2.1：≥3 次同型補丁→歷史命中 結晶 proposed EXP-*.yaml（禁自動 verified）。"""
    recs = []
    for i in range(3):
        patch = CR.PatchProposal(ac_id=f"AC-{i}", guard_text="discount stacking forbidden coupon")
        case = CR.HistoricalCase(case_id=f"C{i}", ac_id=f"AC-{i}",
                                 failure_text="discount stacking coupon double")
        recs.append((patch, CR.replay(patch, [case])))
    written = CR.crystallize_patterns(recs, out_dir=tmp_path, today="2026-06-03")
    assert len(written) == 1
    doc = yaml.safe_load(written[0].read_text(encoding="utf-8"))
    assert doc["maturity"] == "proposed" and doc["occurrences"] == 3


def test_counterfactual_crystallize_below_threshold_no_write(tmp_path):
    recs = [(CR.PatchProposal(ac_id="AC-0", guard_text="discount stacking forbidden"),
             CR.replay(CR.PatchProposal(ac_id="AC-0", guard_text="discount stacking forbidden"),
                       [CR.HistoricalCase(case_id="C0", ac_id="AC-0",
                                          failure_text="discount stacking coupon")]))]
    written = CR.crystallize_patterns(recs, out_dir=tmp_path)
    assert written == []   # < 3 次同型 → 不結晶
