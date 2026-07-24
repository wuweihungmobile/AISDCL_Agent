"""FileRtmFeedbackSource — IRtmFeedbackSource 檔案實作（improving_27 W1b, adapter ≤400）。

與 FileRtmSink（infra/adapters/rtm_file_sink.py，同 base_dir）對稱、互為逆向：
  寫出：FileRtmSink.write_report → RTM-COVERAGE-{project}.yaml（最新快照）
        FileRtmSink.append_report_line → RTM-COVERAGE-HISTORY-{project}.jsonl（跨輪趨勢）
  讀回：FileRtmFeedbackSource.read_report ← RTM-COVERAGE-{project}.yaml
        FileRtmFeedbackSource.read_history ← RTM-COVERAGE-HISTORY-{project}.jsonl

fail-soft 紀律（讀回為輔助諮詢功能，絕不阻斷主流程）：
  檔案不存在 / YAML·JSON 畸形 / 非 dict 結構一律回 None 或空 tuple、不 raise；
  read_history 採 per-line fail-soft（畸形行跳過，不丟整檔）。

報告基名消毒與 FileRtmSink._sanitize_name 對稱，確保讀回路徑與寫出路徑一致，
並防 project 名挾帶路徑穿越（../、絕對路徑）讀到 base_dir 外的檔。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from ...core.ports.rtm_feedback import coverage_report_from_doc
from ...core.ports.rtm_sink import RtmCoverageReport
from ...utils.logger import _sanitize_log_filename

logger = logging.getLogger("autoclaude.infra.rtm_feedback")


class FileRtmFeedbackSource:
    """讀回 FileRtmSink 寫出的 coverage 報告 / history（符合 IRtmFeedbackSource Protocol）。"""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def read_report(self, project: str) -> RtmCoverageReport | None:
        """讀回 project 最近一次 coverage（RTM-COVERAGE-{project}.yaml）；fail-soft 回 None。"""
        target = self._base / f"{_sanitize(f'RTM-COVERAGE-{project}')}.yaml"
        try:
            if not target.is_file():
                return None
            doc = yaml.safe_load(target.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                return None
            return coverage_report_from_doc(doc)
        except Exception as exc:  # noqa: BLE001 — fail-soft（讀回為輔助功能）
            logger.warning("read_report fail-soft for %s: %s", project, exc)
            return None

    def read_history(
        self, project: str, *, limit: int = 0
    ) -> tuple[RtmCoverageReport, ...]:
        """讀回跨輪趨勢（RTM-COVERAGE-HISTORY-{project}.jsonl，最舊→最新）；fail-soft 回 ()。"""
        target = self._base / f"{_sanitize(f'RTM-COVERAGE-HISTORY-{project}')}.jsonl"
        try:
            if not target.is_file():
                return ()
            reports: list[RtmCoverageReport] = []
            for raw in target.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue  # per-line fail-soft：畸形行跳過，不丟整檔
                if isinstance(doc, dict):
                    reports.append(coverage_report_from_doc(doc))
            if limit > 0:
                reports = reports[-limit:]
            return tuple(reports)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("read_history fail-soft for %s: %s", project, exc)
            return ()


def _sanitize(name: str) -> str:
    """委派 SSOT `_sanitize_log_filename`（DEF-101-343，R42 收斂），與
    `FileRtmSink._sanitize_name` 對稱：報告基名消毒，防路徑穿越讀取，並補齊
    Windows 保留裝置名防護（舊版獨立實作缺漏）。

    `.lstrip("._")` 對稱 `FileRtmSink._sanitize_name`：`_sanitize_log_filename`
    只 `rstrip` 尾端空白/句點，不清前導句點/底線，須補一層維持既有「不留字面
    ``..`` 前綴」保證（與 sink 對稱讀寫路徑一致）。

    `_sanitize_log_filename` 對「淨化後整段為空」回傳 `"untitled"`；本模組既有
    對外行為為 `"rtm-report"`，委派後改寫回原字面值，維持既有可觀察行為不變。

    R42 二審修復（DEF-101-346 追記）：`.lstrip("._")` 會把 `_sanitize_log_filename`
    為保留裝置名（如 ``CON`` → ``_CON``）補上的前導底線逃逸字元一併剝除，導致
    ``CON`` 經 lstrip 後又變回裸 ``CON``——保留名防護被 wrapper 自己抵銷。故在
    lstrip 之後，對非 fallback 結果**再委派一次** `_sanitize_log_filename`，
    讓保留名偵測在 lstrip 之後重新執行、補回逃逸前綴。"""
    sanitized = _sanitize_log_filename(name)
    if sanitized == "untitled":
        return "rtm-report"
    result = sanitized.lstrip("._") or "rtm-report"
    if result == "rtm-report":
        return result
    return _sanitize_log_filename(result)


__all__ = ["FileRtmFeedbackSource"]
