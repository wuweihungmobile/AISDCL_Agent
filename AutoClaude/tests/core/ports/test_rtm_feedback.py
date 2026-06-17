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
