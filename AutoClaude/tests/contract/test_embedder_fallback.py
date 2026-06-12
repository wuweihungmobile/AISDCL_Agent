"""SD_Improving_06 W3-T3-26 — 雙 adapter fallback / CircuitBreaker 契約測試（AC4-2）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-2：CircuitBreaker 3 fail → 切備援 < 60s
  - SD_Improving_06.md §11 黃線：latency > 200ms 累積觸發降級
  - DualEmbedderRouter / CircuitBreaker 行為

驗證項目（≥ 3 case + 額外）：
  T1 CircuitBreaker 連續 3 failure → open
  T2 open 超過 recovery_seconds → half_open → 成功一次 → closed
  T3 連續慢呼叫（> latency_threshold）達 slow_call_threshold → open
  T4 DualEmbedderRouter primary 失敗時自動使用 fallback 並回傳結果
  T5 DualEmbedderRouter primary breaker open 時直接走 fallback（不等失敗）
  T6 fallback 也失敗 → 拋 EmbedderUnavailableError（不可吞錯）
"""
from __future__ import annotations

from typing import Any

import pytest

from autoclaude.core.ports.embedder import EmbedderUnavailableError
from autoclaude.infra.adapters.circuit_breaker import CircuitBreaker
from autoclaude.infra.adapters.minimax_embedder import DualEmbedderRouter


class _FakeEmbedder:
    def __init__(self, *, dim: int = 1024, model_id: str = "fake", responses: list = None, breaker: CircuitBreaker = None) -> None:
        self.dimension = dim
        self.model_id = model_id
        self._responses = responses or []
        self._call = 0
        self.breaker = breaker
        self._BACKEND = model_id

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._call >= len(self._responses):
            raise EmbedderUnavailableError("exhausted")
        resp = self._responses[self._call]
        self._call += 1
        if isinstance(resp, Exception):
            if self.breaker:
                self.breaker.record_failure()
            raise resp
        return [resp for _ in texts]

    def health_check(self):
        from autoclaude.core.ports.embedder import EmbedderHealth
        return EmbedderHealth(
            healthy=self._call < len(self._responses),
            backend=self.model_id,
            dimension=self.dimension,
            latency_ms=1.0,
        )


def test_breaker_opens_after_consecutive_failures():
    """T1 連續 3 fail → open。"""
    b = CircuitBreaker(failure_threshold=3, latency_threshold_ms=200.0, slow_call_threshold=3)
    for _ in range(3):
        b.record_failure()
    assert b.state == "open"
    assert b.allow_request() is False


def test_breaker_recovery_half_open_closed():
    """T2 open → recovery_seconds → half_open → 成功 → closed（< 60s 切回）。"""
    fake_clock = {"t": 1000.0}
    b = CircuitBreaker(
        failure_threshold=2,
        latency_threshold_ms=200.0,
        slow_call_threshold=3,
        recovery_seconds=10.0,
        time_source=lambda: fake_clock["t"],
    )
    b.record_failure(); b.record_failure()
    assert b.state == "open"
    fake_clock["t"] += 11
    assert b.allow_request() is True
    assert b.state == "half_open"
    b.record_success(latency_ms=10.0)
    assert b.state == "closed"


def test_breaker_opens_on_consecutive_slow_calls():
    """T3 慢呼叫累積也觸發 open（latency > 200ms × 3 次）。"""
    b = CircuitBreaker(failure_threshold=99, latency_threshold_ms=200.0, slow_call_threshold=3)
    for _ in range(3):
        b.record_success(latency_ms=250.0)
    assert b.state == "open"


def test_dual_router_falls_back_when_primary_raises():
    """T4 primary raise → router 自動走 fallback。"""
    primary = _FakeEmbedder(responses=[EmbedderUnavailableError("down")], model_id="primary",
                            breaker=CircuitBreaker(failure_threshold=99))
    fallback = _FakeEmbedder(responses=[[0.5] * 1024], model_id="fallback")
    router = DualEmbedderRouter(primary, fallback)
    out = router.embed_one("hi")
    assert len(out) == 1024
    assert out[0] == pytest.approx(0.5)


def test_dual_router_skips_primary_when_breaker_open():
    """T5 primary breaker open → 直接走 fallback（不等 fail）。"""
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.record_failure()
    assert breaker.state == "open"
    primary = _FakeEmbedder(responses=[[9.9] * 1024], model_id="primary", breaker=breaker)
    fallback = _FakeEmbedder(responses=[[0.5] * 1024], model_id="fallback")
    router = DualEmbedderRouter(primary, fallback)
    out = router.embed_one("hi")
    # 因 breaker 是 open，會先用 fallback，回傳 0.5
    assert out[0] == pytest.approx(0.5)


def test_dual_router_raises_when_both_down():
    """T6 兩個 adapter 都掛 → 拋 EmbedderUnavailableError（不可吞錯）。"""
    primary = _FakeEmbedder(responses=[EmbedderUnavailableError("p")], model_id="p",
                            breaker=CircuitBreaker(failure_threshold=99))
    fallback = _FakeEmbedder(responses=[EmbedderUnavailableError("f")], model_id="f")
    router = DualEmbedderRouter(primary, fallback)
    with pytest.raises(EmbedderUnavailableError):
        router.embed_one("hi")


def test_breaker_recovery_under_60s():
    """T7 黃線約定：recovery_seconds 預設應 ≤ 60s（AC4-2 切備援 < 60s）。"""
    b = CircuitBreaker()
    assert b.recovery_seconds <= 60.0
