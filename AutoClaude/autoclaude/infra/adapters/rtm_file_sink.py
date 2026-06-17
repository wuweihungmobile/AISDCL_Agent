"""FileRtmSink — IRtmSink 的檔案系統實作（adapter tier ≤400 LOC）。

對應 AutoSDD_improving_24.md A 軌（W-24-1c）。把 RTM coverage/gap 報告寫到
指定基底目錄（預設 AutoClaude run 工作區 build/reports/rtm/），回傳絕對路徑。
SDD 側 / 人類可由該路徑撷取，作為 SCG-5 諮詢輸入——不直接覆寫人工 RTM。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...core.ports.observability import IObservabilityPort, NullObservability

_EXT_BY_FMT = {"yaml": ".yaml", "md": ".md"}


class FileRtmSink:
    """把 RTM 報告寫到 base_dir 下的檔案（符合 IRtmSink Protocol，duck typing）。"""

    def __init__(
        self,
        base_dir: str,
        *,
        observability: Optional[IObservabilityPort] = None,
    ) -> None:
        self._base = Path(base_dir)
        self._obs = observability or NullObservability()

    def write_report(self, report_name: str, content: str, *, fmt: str = "yaml") -> str:
        """寫出報告，回傳絕對路徑。目錄不存在時自動建立（parents=True）。"""
        ext = _EXT_BY_FMT.get(fmt, ".txt")
        safe_name = _sanitize_name(report_name)
        self._base.mkdir(parents=True, exist_ok=True)
        target = self._base / f"{safe_name}{ext}"
        target.write_text(content, encoding="utf-8")
        path = str(target.resolve())
        self._obs.record_event(
            "rtm_report_written", {"path": path, "fmt": fmt, "bytes": len(content)}
        )
        return path

    def append_report_line(self, report_name: str, line: str) -> str:
        """append 單行至 {report_name}.jsonl（improving_27 W3 跨輪趨勢）。

        以單行 JSON（呼叫端序列化）累積，每行恰一筆覆蓋快照；強制 LF 收尾，
        既有檔不存在時自動建立。回傳檔案絕對路徑。
        """
        safe_name = _sanitize_name(report_name)
        self._base.mkdir(parents=True, exist_ok=True)
        target = self._base / f"{safe_name}.jsonl"
        with target.open("a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")
        path = str(target.resolve())
        self._obs.record_event(
            "rtm_history_appended", {"path": path, "bytes": len(line)}
        )
        return path


def _sanitize_name(name: str) -> str:
    """報告基名消毒：僅保留檔名安全字元，杜絕路徑穿越（../、絕對路徑）。"""
    cleaned = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name)
    cleaned = cleaned.strip("._") or "rtm-report"
    return cleaned


__all__ = ["FileRtmSink"]
