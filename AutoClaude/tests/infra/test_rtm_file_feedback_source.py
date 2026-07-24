"""FileRtmFeedbackSource 單元測試（AutoSDD_improving_27 W1b）。

RTM AT 對應：
  - AT-27-2-1：read_report 不存在 → None（fail-soft）
  - AT-27-2-2：FileRtmSink.write_report(render_yaml) → read_report 還原 report（端到端 round-trip）
  - AT-27-2-3：read_history 不存在 → ()；append 多筆 → 還原順序 + limit 取最近 N 筆
  - AT-27-2-4：fail-soft（畸形 YAML → None；畸形 JSONL 行跳過不丟整檔）
  - AT-27-2-5：project 名路徑穿越消毒（讀回路徑與 sink 寫出對稱、不越出 base_dir）
"""
from __future__ import annotations

import json

from autoclaude.core.ports.rtm_feedback import coverage_report_to_doc
from autoclaude.core.ports.rtm_sink import RtmCoverageReport
from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter
from autoclaude.infra.adapters.rtm_file_feedback_source import FileRtmFeedbackSource
from autoclaude.infra.adapters.rtm_file_sink import FileRtmSink


def _report(passed_at: int = 2) -> RtmCoverageReport:
    return RtmCoverageReport(
        scenario="brownfield",
        spec_digest="sha256:deadbeef",
        total_at=3,
        passed_at=passed_at,
        failed_at_ids=("AT-001-1-2",),
        ac_coverage=(("AC-001-1", 1, 2), ("AC-001-2", 1, 1)),
    )


class TestReadReport:
    def test_missing_returns_none(self, tmp_path):
        """AT-27-2-1：報告不存在 → None。"""
        assert FileRtmFeedbackSource(str(tmp_path)).read_report("Demo") is None

    def test_roundtrip_sink_to_source(self, tmp_path):
        """AT-27-2-2：sink 寫 render_yaml → source read_report 還原 report（端到端）。"""
        base = str(tmp_path / "rtm")
        report = _report()
        FileRtmSink(base).write_report(
            "RTM-COVERAGE-Demo", PlaybookToRtmAdapter().render_yaml(report), fmt="yaml"
        )
        restored = FileRtmFeedbackSource(base).read_report("Demo")
        assert restored == report  # frozen dataclass 全欄位等值

    def test_malformed_yaml_fail_soft(self, tmp_path):
        """AT-27-2-4：畸形 YAML → None，不 raise。"""
        base = tmp_path / "rtm"
        base.mkdir()
        (base / "RTM-COVERAGE-Bad.yaml").write_text("{ this: is: not: valid", encoding="utf-8")
        assert FileRtmFeedbackSource(str(base)).read_report("Bad") is None

    def test_non_dict_yaml_returns_none(self, tmp_path):
        """YAML 解析為非 dict（如純字串） → None。"""
        base = tmp_path / "rtm"
        base.mkdir()
        (base / "RTM-COVERAGE-Scalar.yaml").write_text("just a string", encoding="utf-8")
        assert FileRtmFeedbackSource(str(base)).read_report("Scalar") is None


class TestReadHistory:
    def test_missing_returns_empty(self, tmp_path):
        """AT-27-2-3：history 不存在 → ()。"""
        assert FileRtmFeedbackSource(str(tmp_path)).read_history("Demo") == ()

    def test_append_then_read_history_order(self, tmp_path):
        """AT-27-2-3：append 三筆（json doc）→ read_history 還原順序（最舊→最新）。"""
        base = str(tmp_path / "rtm")
        sink = FileRtmSink(base)
        for i in range(1, 4):
            line = json.dumps(coverage_report_to_doc(_report(passed_at=i)))
            sink.append_report_line("RTM-COVERAGE-HISTORY-Demo", line)
        history = FileRtmFeedbackSource(base).read_history("Demo")
        assert len(history) == 3
        assert [r.passed_at for r in history] == [1, 2, 3]

    def test_limit_takes_recent(self, tmp_path):
        """AT-27-2-3：limit>0 取最近 N 筆。"""
        base = str(tmp_path / "rtm")
        sink = FileRtmSink(base)
        for i in range(1, 6):
            sink.append_report_line(
                "RTM-COVERAGE-HISTORY-Demo",
                json.dumps(coverage_report_to_doc(_report(passed_at=i))),
            )
        history = FileRtmFeedbackSource(base).read_history("Demo", limit=2)
        assert [r.passed_at for r in history] == [4, 5]

    def test_malformed_line_skipped(self, tmp_path):
        """AT-27-2-4：畸形 JSONL 行跳過，有效行仍還原（per-line fail-soft）。"""
        base = tmp_path / "rtm"
        base.mkdir()
        good = json.dumps(coverage_report_to_doc(_report(passed_at=2)))
        (base / "RTM-COVERAGE-HISTORY-Mixed.jsonl").write_text(
            f"{good}\nNOT JSON {{\n\n{good}\n", encoding="utf-8"
        )
        history = FileRtmFeedbackSource(str(base)).read_history("Mixed")
        assert len(history) == 2  # 兩 good，畸形行與空行跳過


class TestReservedDeviceNameSanitization:
    """R42 二審回歸（DEF-101-346 追記）：`_sanitize`（本模組私有函式）的
    `.lstrip("._")` 曾把 SSOT `_sanitize_log_filename` 為保留裝置名補上的逃逸
    前導底線一併剝除，導致淨化後裸露為保留名本身，防護沒生效。

    注意：本模組公開方法（`read_report`/`read_history`）一律先固定字面前綴
    （``RTM-COVERAGE-``/``RTM-COVERAGE-HISTORY-``）再消毒，故 project 參數本身
    即使是 `"CON"`，組出的完整字串 `"RTM-COVERAGE-CON"` 也不會等於保留名——
    無法透過這兩個公開方法端到端觸發本缺陷（結構性不可達）。因此本測試直接呼叫
    私有 `_sanitize` 函式，並把結果**實際寫入磁碟檔案**驗證真實落地檔名，而非
    僅比較字串——行為級驗證仍落在真實檔案系統，而非純函式回傳值比對。"""

    def test_sanitize_reserved_name_writes_safe_real_file(self, tmp_path):
        from autoclaude.infra.adapters.rtm_file_feedback_source import _sanitize

        for reserved in ("CON", "con", "NUL", "PRN", "COM1", "LPT9"):
            safe_name = _sanitize(reserved)
            target = tmp_path / f"{safe_name}.yaml"
            target.write_text("x", encoding="utf-8")
            assert target.is_file()
            assert target.stem.upper() != reserved.upper(), (
                f"保留裝置名 {reserved!r} 消毒後仍裸露：{target.name!r}"
            )
            assert target.stem.lstrip("_").upper() == reserved.upper()


class TestPathSafety:
    def test_traversal_project_name_sanitized(self, tmp_path):
        """AT-27-2-5：惡意 project 名消毒，與 sink 寫出對稱（讀回同一安全路徑、不越界）。"""
        base = str(tmp_path / "rtm")
        report = _report()
        # sink 以同名寫出（其 _sanitize_name 消毒 "RTM-COVERAGE-../../evil"）
        FileRtmSink(base).write_report(
            "RTM-COVERAGE-../../evil", PlaybookToRtmAdapter().render_yaml(report), fmt="yaml"
        )
        # source 對 project="../../evil" 消毒後讀回同一檔 → 成功還原（路徑對稱、未越界）
        restored = FileRtmFeedbackSource(base).read_report("../../evil")
        assert restored == report
