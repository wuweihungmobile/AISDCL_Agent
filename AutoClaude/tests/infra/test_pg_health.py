"""PgHealthMonitor 單元測試（SD_08 W5 / ADR-SD08-005 §2.4）。

≥ 5 case：
  1. lag < 2s → NORMAL（無告警 counter）
  2. 2s ≤ lag < 10s → WARN（emit_counter pg_wal_lag_warn）
  3. lag ≥ 10s → CRITICAL（emit_counter pg_wal_lag_critical + record_event pg_degrade_yaml_only）
  4. active_connections 透傳 + emit_histogram
  5. classify_lag 邊界值

注意：repo 未安裝 pytest-asyncio，用 asyncio.run() 包同步測試。
"""
from __future__ import annotations

import asyncio
from typing import Optional

from autoclaude.core.ports.observability import ISpan
from autoclaude.infra.observability import (
    DefaultPgHealthMonitor,
    PgLagLevel,
)
from autoclaude.infra.observability.pg_health import classify_lag


# ──────────────────────────────────────────────────────────────
# 測試夾具
# ──────────────────────────────────────────────────────────────
class _SpyObs:
    """可記錄呼叫的 IObservabilityPort spy。"""

    def __init__(self) -> None:
        self.counters: list[tuple[str, int, dict]] = []
        self.histograms: list[tuple[str, float, dict]] = []
        self.events: list[tuple[str, dict]] = []

    def emit_counter(self, name, value=1, tags=None):
        self.counters.append((name, int(value), dict(tags or {})))

    def emit_histogram(self, name, value, tags=None):
        self.histograms.append((name, float(value), dict(tags or {})))

    def start_span(self, name, tags=None) -> ISpan:  # noqa: ARG002
        class _NS:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return None

            def set_attribute(self_inner, k, v):
                pass

            def record_exception(self_inner, e):
                pass

        return _NS()  # type: ignore[return-value]

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


class _FakeConn:
    """模擬 asyncpg.Connection 的 fetchval / close。"""

    def __init__(self, lag: float, conns: int):
        self._lag = lag
        self._conns = conns
        self.closed = False

    async def fetchval(self, query: str) -> Optional[float]:
        if "pg_last_xact_replay_timestamp" in query:
            return self._lag
        if "pg_stat_activity" in query:
            return self._conns
        return None

    async def close(self):
        self.closed = True


def _factory_for(lag: float, conns: int):
    async def _factory():
        return _FakeConn(lag, conns)

    return _factory


def _run_sample(monitor) -> object:
    """asyncio.run() 包裝；回 PgHealthSample。"""
    return asyncio.run(monitor.sample())


# ──────────────────────────────────────────────────────────────
# Case 1：lag < 2s → NORMAL
# ──────────────────────────────────────────────────────────────
def test_pg_health_lag_normal_no_alert():
    spy = _SpyObs()
    monitor = DefaultPgHealthMonitor(
        observability=spy,
        connection_factory=_factory_for(lag=0.5, conns=12),
    )

    sample = _run_sample(monitor)

    assert sample.level == PgLagLevel.NORMAL
    assert sample.wal_lag_seconds == 0.5
    assert sample.active_connections == 12
    counter_names = [c[0] for c in spy.counters]
    assert "pg_wal_lag_warn" not in counter_names
    assert "pg_wal_lag_critical" not in counter_names
    hist_names = [h[0] for h in spy.histograms]
    assert "pg_wal_lag_seconds" in hist_names
    assert "pg_active_connections" in hist_names


# ──────────────────────────────────────────────────────────────
# Case 2：2s ≤ lag < 10s → WARN
# ──────────────────────────────────────────────────────────────
def test_pg_health_lag_warn_emit_counter():
    spy = _SpyObs()
    monitor = DefaultPgHealthMonitor(
        observability=spy,
        connection_factory=_factory_for(lag=5.0, conns=20),
    )

    sample = _run_sample(monitor)

    assert sample.level == PgLagLevel.WARN
    counter_names = [c[0] for c in spy.counters]
    assert "pg_wal_lag_warn" in counter_names
    assert "pg_wal_lag_critical" not in counter_names
    event_names = [e[0] for e in spy.events]
    assert "pg_degrade_yaml_only" not in event_names


# ──────────────────────────────────────────────────────────────
# Case 3：lag ≥ 10s → CRITICAL + 降級事件
# ──────────────────────────────────────────────────────────────
def test_pg_health_lag_critical_emit_event():
    spy = _SpyObs()
    monitor = DefaultPgHealthMonitor(
        observability=spy,
        connection_factory=_factory_for(lag=15.0, conns=50),
    )

    sample = _run_sample(monitor)

    assert sample.level == PgLagLevel.CRITICAL
    assert sample.is_degradable() is True
    counter_names = [c[0] for c in spy.counters]
    assert "pg_wal_lag_critical" in counter_names
    event_names = [e[0] for e in spy.events]
    assert "pg_degrade_yaml_only" in event_names
    event_attrs = next(attrs for name, attrs in spy.events if name == "pg_degrade_yaml_only")
    assert event_attrs["wal_lag_seconds"] == 15.0


# ──────────────────────────────────────────────────────────────
# Case 4：active_connections 透傳
# ──────────────────────────────────────────────────────────────
def test_pg_health_active_connections_emit_histogram():
    spy = _SpyObs()
    monitor = DefaultPgHealthMonitor(
        observability=spy,
        connection_factory=_factory_for(lag=0.0, conns=123),
    )

    sample = _run_sample(monitor)

    assert sample.active_connections == 123
    conn_hist = next(h for h in spy.histograms if h[0] == "pg_active_connections")
    assert conn_hist[1] == 123.0


# ──────────────────────────────────────────────────────────────
# Case 5：classify_lag 邊界值
# ──────────────────────────────────────────────────────────────
def test_classify_lag_boundaries():
    assert classify_lag(-1.0) == PgLagLevel.NORMAL
    assert classify_lag(0.0) == PgLagLevel.NORMAL
    assert classify_lag(1.99) == PgLagLevel.NORMAL
    assert classify_lag(2.0) == PgLagLevel.WARN
    assert classify_lag(5.0) == PgLagLevel.WARN
    assert classify_lag(9.99) == PgLagLevel.WARN
    assert classify_lag(10.0) == PgLagLevel.CRITICAL
    assert classify_lag(60.0) == PgLagLevel.CRITICAL


# ──────────────────────────────────────────────────────────────
# Case 6（bonus）：NullObservability fallback（無注入時不爆）
# ──────────────────────────────────────────────────────────────
def test_pg_health_null_observability_fallback():
    monitor = DefaultPgHealthMonitor(
        observability=None,
        connection_factory=_factory_for(lag=15.0, conns=10),
    )

    sample = _run_sample(monitor)

    assert sample.level == PgLagLevel.CRITICAL
