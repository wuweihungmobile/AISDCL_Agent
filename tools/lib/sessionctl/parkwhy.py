"""提前探針「量不到」的具名原因（WP-SW D-SW-3／REQ-CTL-51；DES §24.3）。

立案（暴露證據）：`autosdd_session_switch.jsonl` 第 1379、1381 行 `park_early_probe reason=unmeasured
stale=true reading=null`——量不到卻不說為什麼，根因只能靠推理。本檔把「為什麼量不到」收斂成**封閉值域**，
`reading=null` 的痕跡一律帶 `why`（違規＝缺 `why` 或不在值域）。

值域：`no_credential`｜`claim_lost`（補量名額被搶、`await_winner` 逾時）｜`http_error:<status>`｜`timeout`｜
`measure_exception:<Type>`｜`stale_cache`｜`account_unreadable`｜`stdio_none`。

取證來源：`quota_gate.MEASURE_NOTE`（`pace_state` 最近一次補量的 `{won, reason}` 旁記，行程內、不入判準）
與 `ruling_for` 拋出的例外。純函式、不呼叫網路（紅線 1 不受影響）。
"""
from __future__ import annotations

import re
import sys

WHY_VALUES = ("no_credential", "claim_lost", "http_error", "timeout", "measure_exception",
              "stale_cache", "account_unreadable", "stdio_none")
_HTTP = re.compile(r"http-(\d+)")


def _note() -> dict:
    """`quota_gate.MEASURE_NOTE` 的唯一入口（探針路徑 `parkearly` 不得自己 import 額度讀取點，鎖在
    `test_at_ctl_65_69_the_only_quota_read_is_park_pace_state`）；讀不到模組 ⇒ 空旁記。"""
    try:
        import quota_gate  # noqa: PLC0415

        return quota_gate.MEASURE_NOTE
    except Exception:  # noqa: BLE001
        return {}


def reset_note() -> None:
    _note().clear()


def last_note() -> dict:
    return dict(_note())


def valid(why) -> bool:
    """值域判準：`kind` 或 `kind:<detail>`，kind 必在 `WHY_VALUES`。"""
    head, _, detail = str(why or "").partition(":")
    return head in WHY_VALUES and (bool(detail) == (head in ("http_error", "measure_exception")))


def classify(*, state=None, exc: BaseException | None = None, note: dict | None = None,
             expected_account: str | None = None) -> str:
    """回 `why`（量得到且帳號可讀 ⇒ `""`）。`state`＝`pace_state` 的讀數；`exc`＝量測路徑拋出的例外；
    `note`＝`quota_gate.MEASURE_NOTE`；`expected_account`＝標記登記時的基準帳號。"""
    if exc is not None:
        if isinstance(exc, AttributeError) and (sys.stderr is None or sys.stdout is None):
            return "stdio_none"
        return f"measure_exception:{type(exc).__name__}"
    if state is not None and getattr(state, "axes", ()):
        return "account_unreadable" if expected_account and not getattr(state, "account_key", None) else ""
    note = note or {}
    if note.get("won") is False:
        return "claim_lost"
    reason = str(note.get("reason") or "")
    if reason.startswith("no-credentials"):
        return "no_credential"
    if reason == "meter-unreachable":
        return "timeout"
    if match := _HTTP.fullmatch(reason.removesuffix("-unmeasured")):
        return f"http_error:{match.group(1)}"
    if reason == "no-buckets":
        return "http_error:200"
    return "stale_cache"
