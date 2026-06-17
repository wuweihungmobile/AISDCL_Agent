"""FileRtmSink 單元測試（AutoSDD_improving_24 A 軌 W-24-1c）。

RTM AT 對應：
  - AT-24-1-7：寫出報告至 base_dir 並回傳絕對路徑，目錄自動建立
  - AT-24-1-8：fmt 決定副檔名（yaml/md/其他）
  - AT-24-1-9：報告基名消毒，杜絕路徑穿越
"""
from __future__ import annotations

from pathlib import Path

from autoclaude.infra.adapters.rtm_file_sink import FileRtmSink


class TestFileRtmSink:
    def test_writes_yaml_and_returns_path(self, tmp_path):
        """AT-24-1-7：寫檔成功、回傳絕對路徑、內容正確、目錄自動建立。"""
        base = tmp_path / "reports" / "rtm"  # 尚未存在
        sink = FileRtmSink(str(base))
        path = sink.write_report("RTM-COVERAGE-Demo", "kind: rtm-coverage\n", fmt="yaml")
        p = Path(path)
        assert p.is_file()
        assert p.name == "RTM-COVERAGE-Demo.yaml"
        assert p.read_text(encoding="utf-8") == "kind: rtm-coverage\n"

    def test_md_extension(self, tmp_path):
        """AT-24-1-8：fmt=md → .md。"""
        sink = FileRtmSink(str(tmp_path))
        path = sink.write_report("RTM-GAP-Demo", "# gap", fmt="md")
        assert Path(path).name == "RTM-GAP-Demo.md"

    def test_unknown_fmt_falls_back_txt(self, tmp_path):
        sink = FileRtmSink(str(tmp_path))
        path = sink.write_report("r", "x", fmt="weird")
        assert Path(path).suffix == ".txt"

    def test_path_traversal_sanitized(self, tmp_path):
        """AT-24-1-9：惡意基名（路徑穿越）被消毒，落點仍在 base_dir 內。"""
        sink = FileRtmSink(str(tmp_path))
        path = sink.write_report("../../etc/passwd", "x", fmt="yaml")
        p = Path(path)
        # 落點必須在 base_dir 之下（resolve 後仍以 tmp_path 為前綴）
        assert str(p).startswith(str(tmp_path.resolve()))
        assert ".." not in p.name

    def test_empty_name_defaults(self, tmp_path):
        sink = FileRtmSink(str(tmp_path))
        path = sink.write_report("...", "x")
        assert Path(path).stem == "rtm-report"

    def test_observability_event_emitted(self, tmp_path):
        """寫出時發 rtm_report_written 事件（審計鏈）。"""
        events = []

        class _Obs:
            def emit_counter(self, *a, **k): pass
            def emit_histogram(self, *a, **k): pass
            def start_span(self, *a, **k):
                raise AssertionError("unused")
            def record_event(self, name, attributes=None):
                events.append((name, attributes))

        sink = FileRtmSink(str(tmp_path), observability=_Obs())
        sink.write_report("R", "content", fmt="yaml")
        assert any(n == "rtm_report_written" for n, _ in events)
