"""FileRtmSink — IRtmSink 的檔案系統實作（adapter tier ≤400 LOC）。

對應 AutoSDD_improving_24.md A 軌（W-24-1c）。把 RTM coverage/gap 報告寫到
指定基底目錄（預設 AutoClaude run 工作區 build/reports/rtm/），回傳絕對路徑。
SDD 側 / 人類可由該路徑撷取，作為 SCG-5 諮詢輸入——不直接覆寫人工 RTM。
"""
from __future__ import annotations

from pathlib import Path

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...utils.logger import _sanitize_log_filename

_EXT_BY_FMT = {"yaml": ".yaml", "md": ".md"}


class FileRtmSink:
    """把 RTM 報告寫到 base_dir 下的檔案（符合 IRtmSink Protocol，duck typing）。"""

    def __init__(
        self,
        base_dir: str,
        *,
        observability: IObservabilityPort | None = None,
    ) -> None:
        self._base = Path(base_dir)
        self._obs = observability or NullObservability()

    def write_report(self, report_name: str, content: str, *, fmt: str = "yaml") -> str:
        """寫出報告，回傳絕對路徑。目錄不存在時自動建立（parents=True）。"""
        ext = _EXT_BY_FMT.get(fmt, ".txt")
        safe_name = _sanitize_name(report_name)
        self._base.mkdir(parents=True, exist_ok=True)
        target = self._base / f"{safe_name}{ext}"
        # newline="" 為必要（R68；同 DEF-101-524/534 缺陷類別）：text 模式預設
        # newline=None 會在 Windows 上把每個 "\n" 寫成 "\r\n"，使同一份報告在
        # 兩平台產出不同位元組（跨平台共用工作目錄時 diff/雜湊全部對不上）。
        target.write_text(content, encoding="utf-8", newline="")
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
        # newline=""：上方 docstring 的「強制 LF 收尾」在 Windows 上原本是假的
        # ——text 模式預設 newline=None 會把 "\n" 轉成 "\r\n"，寫出 CRLF 的
        # .jsonl。指定 newline="" 停用寫入端行尾轉換，讓承諾與實作一致（R68）。
        with target.open("a", encoding="utf-8", newline="") as f:
            f.write(line.rstrip("\n") + "\n")
        path = str(target.resolve())
        self._obs.record_event(
            "rtm_history_appended", {"path": path, "bytes": len(line)}
        )
        return path


def _sanitize_name(name: str) -> str:
    """報告基名消毒：委派 SSOT `_sanitize_log_filename`（DEF-101-343，R42 收斂第 4~6
    處獨立重寫）取得字元層淨化，杜絕路徑穿越（../、絕對路徑）並補齊 Windows
    保留裝置名（CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]）防護——舊版僅限縮字元集合，
    未檢查保留裝置名。

    `_sanitize_log_filename` 只 `rstrip` 尾端空白/句點，不清前導句點/底線；舊版
    `_sanitize_name` 額外用 `.strip("._")` 兩端一併清除（既有測試
    `test_path_traversal_sanitized`／`test_append_sanitizes_name` 鎖定「``..``
    不得以任何形式殘留於檔名」，即使已無 `/` 分隔符也不留字面 `..` 前綴）。委派
    後在此補一層 `.lstrip("._")` 保留該既有保證，不依賴猜測、已用兩測試驗證。

    `_sanitize_log_filename` 對「淨化後整段為空」回傳固定字面值 `"untitled"`；
    本模組既有對外行為（測試 `test_empty_name_defaults` 鎖定）為 `"rtm-report"`，
    委派後在此改寫回原字面值，維持既有可觀察行為不變（`lstrip` 後同樣可能變
    空，一併兜底）。

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


__all__ = ["FileRtmSink"]
