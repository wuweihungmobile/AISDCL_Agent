"""Phase K M-K3 / ACT-085+086 — Causal Spec Localizer 測試套件.

定位（tc/nfr/hint）、decision_trace 加成、blast-radius、RTM 解析、18-fixture 聚合
（top-1 ≥70% / top-3 ≥90%），以及整合（spec_patch_proposer / steersman_renderer）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import spec_localizer as SL
from tools.fsm_runtime.spec_localizer import RTMRow, Signal


RTM = [
    RTMRow("AC-001", "F-001", "", ["TC-001-1", "TC-001-2"]),
    RTMRow("AC-002", "F-001", "", ["TC-002-1"]),
    RTMRow("AC-014", "F-003", "", ["TC-014-1"]),
    RTMRow("AC-020", "F-004", "NFR-002", ["TC-020-1"]),
    RTMRow("AC-021", "F-004", "NFR-003", ["TC-021-1"]),
    RTMRow("AC-030", "F-005", "", ["TC-030-1", "TC-030-2"]),
    RTMRow("AC-040", "F-006", "", ["TC-shared"]),
    RTMRow("AC-041", "F-006", "", ["TC-shared"]),
]


# ---------- 基本定位 ----------

def test_localize_by_tc_top1():
    r = SL.localize_from_counterexample("TC-014-1", RTM)
    assert r.top(1) == ["AC-014"]
    assert r.suspects[0].score == 0.9


def test_localize_includes_parent_frd():
    r = SL.localize_from_counterexample("TC-014-1", RTM)
    ids = {s.node_id for s in r.suspects}
    assert "F-003" in ids
    frd = next(s for s in r.suspects if s.node_id == "F-003")
    assert frd.score == 0.5


def test_localize_by_nfr():
    r = SL.localize_from_production_drift("NFR-002", RTM)
    assert r.top(1) == ["AC-020"]


def test_localize_by_ac_hint_scores_one():
    r = SL.localize(Signal("adversarial_counterexample", ac_hint="AC-014"), rtm=RTM)
    assert r.suspects[0].node_id == "AC-014"
    assert r.suspects[0].score == 1.0


def test_no_match_returns_empty():
    r = SL.localize_from_counterexample("TC-999", RTM)
    assert r.suspects == []
    assert "無命中" in SL.localization_report(r)


# ---------- decision_trace 加成 / 排序 ----------

def test_decision_trace_boosts_score():
    trace = [{"spec_refs": ["AC-014"]}]
    r = SL.localize_from_counterexample("TC-014-1", RTM, decision_trace=trace)
    ac = next(s for s in r.suspects if s.node_id == "AC-014")
    assert ac.score == 1.0
    assert "decision_trace" in ac.evidence


def test_decision_trace_changes_ranking():
    # TC-shared 同時對應 AC-040/AC-041（同分 0.9）；trace 命中 AC-041 → 排第一
    trace = [{"spec_refs": ["AC-041"]}]
    r = SL.localize_from_counterexample("TC-shared", RTM, decision_trace=trace)
    assert r.top(1) == ["AC-041"]


# ---------- blast radius ----------

def test_blast_radius_neighborhood():
    r = SL.localize_from_counterexample("TC-001-1", RTM)
    assert r.top(1) == ["AC-001"]
    assert set(r.blast_radius) >= {"AC-001", "F-001", "AC-002", "TC-001-1", "TC-001-2"}


# ---------- 18-fixture 聚合（top-1 ≥70% / top-3 ≥90%）----------

FIXTURES = [
    (Signal("adversarial_counterexample", tc_id="TC-001-1"), "AC-001"),
    (Signal("adversarial_counterexample", tc_id="TC-001-2"), "AC-001"),
    (Signal("adversarial_counterexample", tc_id="TC-002-1"), "AC-002"),
    (Signal("adversarial_counterexample", tc_id="TC-014-1"), "AC-014"),
    (Signal("adversarial_counterexample", tc_id="TC-020-1"), "AC-020"),
    (Signal("adversarial_counterexample", tc_id="TC-021-1"), "AC-021"),
    (Signal("rtm_gap", tc_id="TC-030-1"), "AC-030"),
    (Signal("rtm_gap", tc_id="TC-030-2"), "AC-030"),
    (Signal("rtm_gap", tc_id="TC-002-1"), "AC-002"),
    (Signal("production_drift", nfr_id="NFR-002"), "AC-020"),
    (Signal("production_drift", nfr_id="NFR-003"), "AC-021"),
    (Signal("adversarial_counterexample", ac_hint="AC-014"), "AC-014"),
    (Signal("adversarial_counterexample", ac_hint="AC-001"), "AC-001"),
    (Signal("adversarial_counterexample", ac_hint="AC-030"), "AC-030"),
    (Signal("rtm_gap", tc_id="TC-001-2"), "AC-001"),
    (Signal("rtm_gap", tc_id="TC-014-1"), "AC-014"),
    (Signal("production_drift", nfr_id="NFR-002"), "AC-020"),
    (Signal("adversarial_counterexample", tc_id="TC-021-1"), "AC-021"),
]


def test_top1_accuracy_at_least_70pct():
    hits = sum(1 for sig, exp in FIXTURES if SL.localize(sig, rtm=RTM).top(1) == [exp])
    assert hits / len(FIXTURES) >= 0.70


def test_top3_accuracy_at_least_90pct():
    hits = sum(1 for sig, exp in FIXTURES if exp in SL.localize(sig, rtm=RTM).top(3))
    assert hits / len(FIXTURES) >= 0.90


# ---------- RTM markdown 解析 ----------

def test_parse_rtm_markdown():
    md = (
        "| FRD | AC | TC | NFR |\n"
        "|-----|----|----|-----|\n"
        "| F-001 | AC-001 | TC-001-1, TC-001-2 | — |\n"
        "| F-004 | AC-020 | TC-020-1 | NFR-002 |\n"
    )
    rows = SL.parse_rtm_markdown(md)
    assert len(rows) == 2
    assert rows[0].ac_id == "AC-001"
    assert rows[0].frd_id == "F-001"
    assert rows[0].tc_ids == ["TC-001-1", "TC-001-2"]
    assert rows[1].nfr_id == "NFR-002"


def test_parse_then_localize():
    md = "| F-003 | AC-014 | TC-014-1 |\n"
    rows = SL.parse_rtm_markdown(md)
    assert SL.localize_from_counterexample("TC-014-1", rows).top(1) == ["AC-014"]


# ---------- 報告 + 便捷 adapter ----------

def test_report_contains_suspect_and_advisory():
    rep = SL.localization_report(SL.localize_from_counterexample("TC-014-1", RTM))
    assert "AC-014" in rep
    assert "advisory" in rep
    assert "絕不自動改 spec" in rep


def test_adapters_set_signal_type():
    assert SL.localize_from_production_drift("NFR-002", RTM).signal.signal_type == "production_drift"
    assert SL.localize_from_rtm_gap("TC-002-1", RTM).signal.signal_type == "rtm_gap"


# ---------- ACT-086 整合：spec_patch_proposer ----------

def test_integration_spec_patch_embeds_localization(tmp_path):
    from tools.fsm_runtime.spec_patch_proposer import propose, DefectSignal
    rep = SL.localization_report(SL.localize_from_counterexample("TC-014-1", RTM))
    signals = [
        DefectSignal("AC-014", "spec_gap: metamorphic 違反", "f(2x) != 2f(x)"),
        DefectSignal("AC-014", "spec_gap: metamorphic 違反", "f(2x) != 2f(x)"),
    ]
    proposal = propose("AC-014", "原始 AC 文字", signals,
                       today="2026-06-02", out_dir=tmp_path, localization=rep)
    md = Path(proposal.report_path).read_text(encoding="utf-8")
    assert "因果定位" in md
    assert "AC-014" in md


def test_integration_spec_patch_without_localization_unchanged(tmp_path):
    from tools.fsm_runtime.spec_patch_proposer import propose, DefectSignal
    signals = [DefectSignal("AC-1", "r", "c")]
    proposal = propose("AC-1", "before", signals, today="2026-06-02", out_dir=tmp_path)
    md = Path(proposal.report_path).read_text(encoding="utf-8")
    assert "因果定位" not in md   # 預設不注入，向後相容


# ---------- ACT-086 整合：steersman_renderer ----------

def test_integration_steersman_embeds_localization():
    from tools.fsm_runtime.steersman_renderer import render_steersman
    rep = SL.localization_report(SL.localize_from_production_drift("NFR-002", RTM))
    md = render_steersman(None, localization=rep).to_markdown()
    assert "因果定位" in md
    assert "AC-020" in md


def test_integration_steersman_without_localization_unchanged():
    from tools.fsm_runtime.steersman_renderer import render_steersman
    md = render_steersman(None).to_markdown()
    assert "因果定位" not in md
