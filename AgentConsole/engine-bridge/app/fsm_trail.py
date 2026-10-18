"""決策軌跡的顯示投影：把委派失敗那筆 decision_trace 的 `from` 還原成真實來源狀態
（DEF-AC-023；TCS-FsmTrail-20261018 的 R1～R9）。

SDD 的 `record_escalation` 先把 `current_state` 寫成 ESCALATION 再轉態，所以委派失敗那一筆在檔裡是
`ESCALATION → ESCALATION`（trigger＝`autoclaude_delegated_exit`）；真實來源是
`AUTOCLAUDE_DELEGATED`。這裡只在 Bridge 輸出前做投影，並以 `from_inferred: True` 標明推斷值；
FSM 狀態檔不動。

純函式：只用標準庫、無 I/O、無全域可變狀態、不 import `app.*`（葉節點）；任何輸入都不拋例外。
"""
from __future__ import annotations

from typing import Any

_ESCALATION = "ESCALATION"
_DELEGATED_EXIT_TRIGGER = "autoclaude_delegated_exit"
_DELEGATED_FAILED_SOURCE = "autoclaude_delegated_failed"
_RESTORED_FROM = "AUTOCLAUDE_DELEGATED"


def _is_delegated_failure(elem: Any) -> bool:
    return (isinstance(elem, dict)
            and elem.get("from") == _ESCALATION
            and elem.get("to") == _ESCALATION
            and elem.get("trigger") == _DELEGATED_EXIT_TRIGGER)


def restore_trail(trace: Any, provenance: Any) -> Any:
    """回傳還原後的新 list；`trace` 不是 list 時原樣回傳同一個物件。"""
    if not isinstance(trace, list):
        return trace
    gate_open = (isinstance(provenance, dict)
                 and provenance.get("source") == _DELEGATED_FAILED_SOURCE)
    result: list[Any] = []
    for elem in trace:
        if gate_open and _is_delegated_failure(elem):
            result.append({**elem, "from": _RESTORED_FROM, "from_inferred": True})
        else:
            result.append(elem)
    return result
