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
