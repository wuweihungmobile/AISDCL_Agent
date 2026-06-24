"""IRtmFeedbackSource port 契約測試（AutoSDD_improving_27 W1a）。

RTM AT 對應：
  - AT-27-1-1：NullRtmFeedbackSource 為 no-op（read_report→None / read_history→()）
  - AT-27-1-2：coverage_report_to_doc → coverage_report_from_doc round-trip 還原原始欄位
  - AT-27-1-3：coverage_report_from_doc 能解析既有 render_yaml 輸出（格式一致性鎖定，防 drift）
  - AT-27-1-4：畸形 doc fail-soft（缺 summary / 缺欄位不 raise，回最小 report）
"""
from __future__ import annotations

import yaml

from autoclaude.core.ports.rtm_feedback import (
    NullRtmFeedbackSource,
    coverage_report_from_doc,
    coverage_report_to_doc,
    coverage_trend,
)
from autoclaude.core.ports.rtm_sink import RtmCoverageReport
from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter


def _sample_report() -> RtmCoverageReport:
    return RtmCoverageReport(
        scenario="brownfield",
        spec_digest="sha256:abc123",
        total_at=3,
        passed_at=2,
        failed_at_ids=("AT-001-1-2",),
        ac_coverage=(("AC-001-1", 1, 2), ("AC-001-2", 1, 1)),
    )


class TestNullFeedbackSource:
    def test_read_report_is_none(self):
        """AT-27-1-1：未注入 → read_report no-op 回 None。"""
        assert NullRtmFeedbackSource().read_report("AnyProject") is None

    def test_read_history_is_empty(self):
        """AT-27-1-1：未注入 → read_history no-op 回空 tuple。"""
        assert NullRtmFeedbackSource().read_history("AnyProject", limit=5) == ()


class TestDocRoundTrip:
    def test_to_doc_from_doc_restores_fields(self):
        """AT-27-1-2：to_doc → from_doc 還原全部原始欄位 + 衍生 property 重算正確。"""
        report = _sample_report()
        doc = coverage_report_to_doc(report, saved_at="2026-06-17T10:00:00")
        restored = coverage_report_from_doc(doc)
        assert restored.scenario == report.scenario
        assert restored.spec_digest == report.spec_digest
        assert restored.total_at == report.total_at
        assert restored.passed_at == report.passed_at
        assert restored.failed_at_ids == report.failed_at_ids
        assert restored.ac_coverage == report.ac_coverage
        # 衍生 property 由 dataclass 重算，與原一致
        assert restored.coverage_pct == report.coverage_pct
        assert restored.ac_coverage_pct == report.ac_coverage_pct
        assert restored.is_fully_covered == report.is_fully_covered

    def test_saved_at_optional(self):
        """saved_at 省略時 doc 不含該鍵（不污染既有格式）。"""
        assert "saved_at" not in coverage_report_to_doc(_sample_report())

    def test_from_doc_parses_render_yaml_output(self):
        """AT-27-1-3：from_doc 能解析既有 render_yaml 輸出（格式一致性鎖定）。

        若 render_yaml 的 doc 結構與 coverage_report_to_doc 漂移，本測試立即轉紅，
        防 read_report 因格式不一致而靜默還原錯誤（DEF-05-002/07-001 drift 家族防護）。
        """
        report = _sample_report()
        yaml_text = PlaybookToRtmAdapter().render_yaml(report)
        restored = coverage_report_from_doc(yaml.safe_load(yaml_text))
        assert restored == report  # frozen dataclass 全欄位等值


def _ac_report(covered: int, total: int) -> RtmCoverageReport:
    """建一份 ac_coverage_pct = covered/total×100 的快照（其餘欄位不影響趨勢）。"""
    ac = tuple((f"AC-{i}", 1, 1) for i in range(covered)) + tuple(
        (f"AC-{covered + i}", 0, 1) for i in range(total - covered)
    )
    return RtmCoverageReport(
        scenario="brownfield", spec_digest="x",
        total_at=total, passed_at=covered, ac_coverage=ac,
    )


class TestCoverageTrend:
    """W-28-1：跨輪覆蓋趨勢純函式（read_history 的生產消費判定邏輯）。"""

    def test_empty_history_returns_none(self):
        """AT-28-1-1：空 history → None。"""
        assert coverage_trend(()) is None

    def test_single_round_is_single_direction(self):
        """AT-28-1-2：僅 1 輪 → direction=single、previous_pct=None（呼叫端判「無趨勢」）。"""
        t = coverage_trend((_ac_report(4, 5),))
        assert t is not None
        assert t.rounds == 1
        assert t.direction == "single"
        assert t.previous_pct is None
        assert t.latest_pct == 80.0
        assert t.consecutive_declines == 0

    def test_two_rounds_improving(self):
        """AT-28-1-3：40%→80% → improving、delta=+40、declines=0。"""
        t = coverage_trend((_ac_report(2, 5), _ac_report(4, 5)))
        assert t.direction == "improving"
        assert t.previous_pct == 40.0
        assert t.latest_pct == 80.0
        assert t.delta_pct == 40.0
        assert t.consecutive_declines == 0

    def test_two_rounds_declining(self):
        """AT-28-1-4：80%→40% → declining、delta=-40、declines=1。"""
        t = coverage_trend((_ac_report(4, 5), _ac_report(2, 5)))
        assert t.direction == "declining"
        assert t.delta_pct == -40.0
        assert t.consecutive_declines == 1

    def test_consecutive_declines_counts_trailing_drops(self):
        """AT-28-1-5：100%→80%→40% → 連續下降 2 輪。"""
        t = coverage_trend(
            (_ac_report(5, 5), _ac_report(4, 5), _ac_report(2, 5))
        )
        assert t.direction == "declining"
        assert t.consecutive_declines == 2
        assert t.previous_pct == 80.0
        assert t.latest_pct == 40.0

    def test_flat_trend(self):
        """AT-28-1-6：50%→50% → flat、delta=0、declines=0。"""
        t = coverage_trend((_ac_report(1, 2), _ac_report(1, 2)))
        assert t.direction == "flat"
        assert t.delta_pct == 0.0
        assert t.consecutive_declines == 0

    def test_recover_then_dip_only_counts_last_decline(self):
        """AT-28-1-7：40%→80%→60%（先升後降）→ declining 但連續下降僅 1 輪。"""
        t = coverage_trend(
            (_ac_report(2, 5), _ac_report(4, 5), _ac_report(3, 5))
        )
        assert t.direction == "declining"
        assert t.consecutive_declines == 1
        assert t.previous_pct == 80.0
        assert t.latest_pct == 60.0


class TestFailSoft:
    def test_missing_summary_no_raise(self):
        """AT-27-1-4：缺 summary 不 raise，回最小 report（total_at=0）。"""
        r = coverage_report_from_doc({"scenario": "x"})
        assert r.scenario == "x"
        assert r.total_at == 0
        assert r.coverage_pct == 0.0

    def test_empty_doc_no_raise(self):
        """AT-27-1-4：全空 doc fail-soft。"""
        r = coverage_report_from_doc({})
        assert r.total_at == 0
        assert r.failed_at_ids == ()
        assert r.ac_coverage == ()


class TestWeakRegexAtIdsDoc:
    """improving_61 W-61-1 / R-61-3：weak_regex_at_ids 搭 history doc 往返；
    舊紀錄無此欄 → from_doc fail-soft 回 ()（向後相容）。"""

    def test_coverage_doc_roundtrip_weak_regex(self):
        report = RtmCoverageReport(
            scenario="brownfield", spec_digest="sha256:abc",
            total_at=2, passed_at=2,
            failed_at_ids=(), ac_coverage=(("AC-001-1", 2, 2),),
            weak_regex_at_ids=("AT-001-1-1", "AT-001-1-2"),
        )
        restored = coverage_report_from_doc(coverage_report_to_doc(report))
        assert restored.weak_regex_at_ids == ("AT-001-1-1", "AT-001-1-2")

    def test_legacy_doc_missing_weak_field_defaults_empty(self):
        """improving_60 既有 history 紀錄無 weak_regex_at_ids → 讀回 ()，不 raise。"""
        legacy_doc = {
            "kind": "rtm-coverage", "scenario": "x", "spec_digest": "sha256:1",
            "summary": {"total_at": 1, "passed_at": 1},
            "ac_coverage": [{"ac_id": "AC-001-1", "passed_at": 1, "total_at": 1}],
            "failed_at_ids": [],
            # 刻意無 weak_regex_at_ids
        }
        restored = coverage_report_from_doc(legacy_doc)
        assert restored.weak_regex_at_ids == ()
