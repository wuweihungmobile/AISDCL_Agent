"""SelfImproving 巡邏快照 `patrol.json` 的唯讀讀取（TCS-SiFlowVisibility-20261111 W-F1、C-1、C-6）。

主機端（根層巡邏器）以「寫新檔→replace」更新 `<AUTOSDD_SI_DIR>/console_report/patrol.json`；本模組
只**讀**它：每個請求恰讀一次、不快取、不寫任何檔、不啟動子行程、不 import `lib`／`tools`。

只驗形狀與大小，不解讀內容（內容由前端依契約顯示）：
  · 頂層為 JSON 物件，`schema_rev` 為整數 1（布林、浮點、字串都不收），`generated_at` 為帶 offset 的
    ISO 8601 字串；
  · 位元組數不超過 `PATROL_REPORT_MAX_BYTES`（讀端寬於根層寫端的 524288，不會誤拒合法快照）。

失敗一律 `ApiError(503, "si_unavailable", cause=…)`，`cause` 四值：
  `report_dir_unset`（未設 `BRIDGE_SI_REPORT_DIR`；零檔案系統存取）、`report_missing`（無
  `patrol.json`）、`report_unreadable`（存在但讀不了，例如是目錄或權限不足）、`report_invalid`
  （壞檔、形狀不符、過大、路徑逃出目錄）。

Windows 行為＝主機端 `os.replace` 覆寫的瞬間，讀端的 `open` 可能短暫收到 PermissionError；本模組對
「不是目錄的 PermissionError」重試數次再判不可讀，避免把正常更新誤報成 503（寫入端另有自己的重試）。
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ApiError

#: 快照檔的大小上限（位元組；Bridge 唯一定義處，C-6）。
PATROL_REPORT_MAX_BYTES = 1048576
#: 固定檔名（只讀這一個；`.tmp`、`.bak` 與其他檔名一律不讀）。
PATROL_FILE_NAME = "patrol.json"
#: 暫時性拒絕存取的重試（Windows 讀寫競態）：次數與間隔（秒）。
_TRANSIENT_RETRIES = 5
_TRANSIENT_SLEEP = 0.01


def _unavailable(cause: str, detail: str) -> ApiError:
    return ApiError(503, "si_unavailable", cause=cause, detail=detail)


def _default_resolver(path: Path) -> Path:
    return path.resolve()


def resolve_report_path(report_dir: Path,
                        resolver: Callable[[Path], Path] = _default_resolver
                        ) -> tuple[Path | None, str | None]:
    """逃逸判準（純函式；解析器可注入）：回 `(要讀的路徑, None)` 或 `(None, 問題說明)`。

    通過條件＝候選檔解析後的**父目錄**逐段等於解析後的快照目錄（比較前一律 `os.path.normcase`，
    Windows 大小寫與分隔符不影響；不比字串前綴，所以 `/si-report-evil` 不會被當成含於
    `/si-report`），且解析後路徑不含 `..` 段。快照檔本身是指向目錄外的符號連結、或解析後就是目錄
    本身，都不通過。"""
    candidate = report_dir / PATROL_FILE_NAME
    resolved_dir = resolver(report_dir)
    resolved = resolver(candidate)
    if ".." in resolved.parts:
        return None, f"解析後的路徑含 .. 段：{resolved}"
    if os.path.normcase(str(resolved.parent)) != os.path.normcase(str(resolved_dir)):
        return None, f"解析後的路徑不在快照目錄之內：{resolved}"
    if os.path.normcase(str(resolved)) == os.path.normcase(str(resolved_dir)):
        return None, "解析後的路徑就是快照目錄本身"
    return resolved, None


def _reject_constant(name: str) -> Any:
    raise ValueError(f"JSON 不允許 {name}")


def _read_limited(path: Path) -> bytes:
    """讀至多 `PATROL_REPORT_MAX_BYTES + 1` 位元組（多讀的一個位元組只用來判斷是否超限）。
    未設重試以外的容錯：`FileNotFoundError`＝缺檔；其餘 OSError＝不可讀。"""
    attempt = 0
    while True:
        try:
            with open(path, "rb") as handle:
                return handle.read(PATROL_REPORT_MAX_BYTES + 1)
        except FileNotFoundError:
            raise
        except PermissionError:
            attempt += 1
            # 目錄（Windows 對目錄 open 回 PermissionError）與持續拒絕＝不可讀，不必等
            if path.is_dir() or attempt > _TRANSIENT_RETRIES:
                raise
            time.sleep(_TRANSIENT_SLEEP)


def _shape_problem(report: Any) -> str | None:
    if not isinstance(report, dict):
        return "頂層不是 JSON 物件"
    rev = report.get("schema_rev")
    if "schema_rev" not in report or type(rev) is not int or rev != 1:
        return "schema_rev 須為整數 1"
    stamp = report.get("generated_at")
    if not isinstance(stamp, str) or not stamp:
        return "generated_at 須為非空字串"
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return "generated_at 不是 ISO 8601 時間"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return "generated_at 缺 offset"
    return None


def read_patrol(report_dir: Path | None) -> dict[str, Any]:
    """讀並驗快照，回 C-1 的 200 本文：`{schema_rev, kind, read_at, report}`（鍵序固定；`report` 為
    檔案解析後的物件，鍵序與值逐值保留）。"""
    if report_dir is None:
        raise _unavailable("report_dir_unset",
                           "BRIDGE_SI_REPORT_DIR 未設定（此部署沒有掛載巡邏回報目錄）")
    path, problem = resolve_report_path(report_dir)
    if path is None:
        raise _unavailable("report_invalid", problem or "路徑不在快照目錄之內")
    try:
        raw = _read_limited(path)
    except FileNotFoundError:
        raise _unavailable("report_missing", f"{PATROL_FILE_NAME} 不存在") from None
    except OSError as exc:
        raise _unavailable("report_unreadable",
                           f"{PATROL_FILE_NAME} 讀取失敗：{type(exc).__name__}") from None
    if len(raw) > PATROL_REPORT_MAX_BYTES:
        raise _unavailable("report_invalid",
                           f"{PATROL_FILE_NAME} 超過 {PATROL_REPORT_MAX_BYTES} 位元組")
    try:
        report = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise _unavailable("report_invalid", f"{PATROL_FILE_NAME} 不是合法的 UTF-8 JSON") from None
    bad = _shape_problem(report)
    if bad is not None:
        raise _unavailable("report_invalid", bad)
    return {"schema_rev": 1, "kind": "patrol",
            "read_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "report": report}
