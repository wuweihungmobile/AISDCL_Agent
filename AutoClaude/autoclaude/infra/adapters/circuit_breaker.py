"""CircuitBreaker — 簡易閘斷器（SD_Improving_06 W3-T3-19 + T3-24）。

支援兩種觸發模式：
  - failure threshold：連續 N 次失敗 → open
  - latency threshold：連續 N 次 latency > limit → open

設計上不依賴 asyncio / threading 鎖（W3 階段 sync 場景），由呼叫端保證單執行緒。
testing 友善：時間源透過 ``time_source`` 注入。

狀態機：
  CLOSED → (連續 fail/slow) → OPEN → (recovery_seconds) → HALF_OPEN
  HALF_OPEN → (一次成功) → CLOSED ；HALF_OPEN → (一次 fail) → OPEN
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal

CircuitState = Literal["closed", "open", "half_open"]


@dataclass
class CircuitBreaker:
    """簡易閘斷器（W3 階段同步版本）。

    Args:
        failure_threshold: 連續失敗多少次後 open
        latency_threshold_ms: 連續 latency 超過幾毫秒視為「慢失敗」
        slow_call_threshold: 連續多少次「慢呼叫」即 open
        recovery_seconds: open 後等多久進入 half_open
    """

    failure_threshold: int = 3
    latency_threshold_ms: float = 200.0
    slow_call_threshold: int = 3
    recovery_seconds: float = 60.0
    state: CircuitState = "closed"
    _consecutive_failures: int = 0
    _consecutive_slow: int = 0
    _opened_at: float = 0.0
    time_source: Callable[[], float] = time.monotonic

    def allow_request(self) -> bool:
        """是否允許下一次請求；副作用：open 過了 recovery_seconds 後轉 half_open。"""
        if self.state == "closed":
            return True
        if self.state == "open":
            elapsed = self.time_source() - self._opened_at
            if elapsed >= self.recovery_seconds:
                self.state = "half_open"
                return True
            return False
        # half_open：放行一次探測
        return True

    def record_success(self, latency_ms: float = 0.0) -> None:
        if latency_ms > self.latency_threshold_ms:
            self._consecutive_slow += 1
            self._consecutive_failures = 0
            if self._consecutive_slow >= self.slow_call_threshold:
                self._trip("slow")
            return
        # 成功 + 不慢 → 全清零，half_open 轉 closed
        self._consecutive_failures = 0
        self._consecutive_slow = 0
        if self.state == "half_open":
            self.state = "closed"

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        self._consecutive_slow = 0
        if self.state == "half_open":
            self._trip("half_open_fail")
        elif self._consecutive_failures >= self.failure_threshold:
            self._trip("fail")

    def _trip(self, reason: str) -> None:  # noqa: ARG002 — reason 預留給未來 telemetry
        self.state = "open"
        self._opened_at = self.time_source()

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_slow": self._consecutive_slow,
            "opened_at": self._opened_at,
        }
