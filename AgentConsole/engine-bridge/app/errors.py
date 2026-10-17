"""統一的錯誤封包 `{"code":<HTTP 狀態>,"reason":"…",…附加欄位}`（main.py 的 handler 轉成回應）。"""
from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(self, status_code: int, reason: str, **extra: Any):
        super().__init__(f"{status_code} {reason}")
        self.status_code = status_code
        self.body: dict[str, Any] = {"code": status_code, "reason": reason, **extra}


def not_found(reason: str, **extra: Any) -> ApiError:
    return ApiError(404, reason, **extra)


def invalid_state(run_id: str, status: str, action: str) -> ApiError:
    return ApiError(409, "invalid_state", run_id=run_id, status=status,
                    detail=f"狀態 {status} 不允許 {action}")


def lock_held(holder_run_id: str | None) -> ApiError:
    return ApiError(409, "advisory_lock_held", holder_run_id=holder_run_id)


def unprocessable(violations: list[dict[str, Any]],
                  reason: str = "sanitization_failed") -> ApiError:
    return ApiError(422, reason, violations=violations)


def fsm_state_conflict(current_state: Any, *, expected_state: Any = None,
                       sub_reason: str | None = None, **extra: Any) -> ApiError:
    """409 `fsm_state_conflict`（ADR-XPLAT-016 §10.2／§10.3；契約 v1.5 附錄 B.5）。

    欄位同時放兩處：頂層（契約 v1.5 的形狀：`current_state`、`expected_state`、`run_id`、
    `run_status`）與 `detail` 物件（ADR 的形狀：`detail={current_state, reason, run_id,
    run_status}`）；內容相同，消費端讀哪一種都對。`sub_reason`（如 `foreign_delegation`）只放
    `detail.reason`，因為頂層 `reason` 已是錯誤碼 `fsm_state_conflict`。"""
    fields: dict[str, Any] = {"current_state": current_state}
    if expected_state is not None:
        fields["expected_state"] = expected_state
    fields.update(extra)
    detail = dict(fields)
    if sub_reason is not None:
        detail["reason"] = sub_reason
    return ApiError(409, "fsm_state_conflict", **fields, detail=detail)


def spec_digest_changed(pair: str, *, doc: str | None = None, frozen_digest: str | None = None,
                        import_digest: str | None = None, current_digest: str | None = None,
                        expected_digest: str | None = None, message: str | None = None) -> ApiError:
    """409 `spec_digest_changed`：內容與凍結時（或核准人看到的、匯入時的）不同。

    `pair`＝`expected_vs_file`（`:freeze`）｜`frozen_vs_file`｜`import_vs_file`（批次預檢）。
    沒有的摘要鍵省略；同樣頂層與 `detail` 各放一份（理由同 `fsm_state_conflict`）。"""
    fields = {"doc": doc, "expected_digest": expected_digest, "frozen_digest": frozen_digest,
              "import_digest": import_digest, "current_digest": current_digest}
    present = {k: v for k, v in fields.items() if v is not None}
    detail: dict[str, Any] = {"pair": pair, **present}
    if message:
        detail["message"] = message
    return ApiError(409, "spec_digest_changed", pair=pair, **present, detail=detail)
