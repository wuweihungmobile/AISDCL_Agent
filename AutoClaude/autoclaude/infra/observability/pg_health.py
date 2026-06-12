"""PgHealthMonitor — PG WAL lag + 連線數 health adapter（SD_08 W5 / ADR-SD08-005 §2.4）。

設計原則（adapter ≤ 400 LOC）：
  - 純查詢 adapter（READ-ONLY）；不涉及 DDL/DML
  - WAL lag 透過 `pg_last_xact_replay_timestamp()` 計算（SD 共識）
  - 三閾值告警（lag < 2s 正常 / 2-10s warn / ≥ 10s critical）
  - 透過 IObservabilityPort 注入發送 metric（建構式注入；NullObservability fallback）

對應：
  - ADR-SD08-005 §2.4 WAL lag adapter 設計
  - ADR-SD08-005 §2.5 風險覆蓋（WAL lag 為優先 1）
  - R-SD08-H-1 / R-SD08-PM-#4 W5 強制交付 3 項之 (i)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from ...core.ports.observability import IObservabilityPort, NullObservability

# ADR-SD08-005 §2.4 三閾值（與 SD_06 W5 dual_state reconcile drain SLA 一致）
WAL_LAG_WARN_SECONDS = 2.0
WAL_LAG_CRITICAL_SECONDS = 10.0


# ──────────────────────────────────────────────────────────────
# 告警等級 / Health sample
# ──────────────────────────────────────────────────────────────
class PgLagLevel(str, Enum):
    """WAL lag 三閾值（ADR-SD08-005 §2.4）。"""

    NORMAL = "normal"      # lag < 2s
    WARN = "warn"          # 2s ≤ lag < 10s
    CRITICAL = "critical"  # lag ≥ 10s


@dataclass(frozen=True)
class PgHealthSample:
    """單次 health 採樣結果。

    欄位：
      wal_lag_seconds   : 主從 replication lag（秒）；無 replica 時為 0.0
      active_connections: 目前 active 連線數（pg_stat_activity）
      level             : 三閾值告警等級
    """

    wal_lag_seconds: float
    active_connections: int
    level: PgLagLevel

    def is_degradable(self) -> bool:
        """是否需觸發降級至 yaml_only（ADR-SD08-005 §2.4 critical 行為）。"""
        return self.level == PgLagLevel.CRITICAL


# ──────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────
class PgHealthMonitor(Protocol):
    """PG health 查詢 Protocol（ADR-SD08-005 §2.4）。

    使用模式：
        monitor = DefaultPgHealthMonitor(observability=obs, dsn=...)
        sample = await monitor.sample()
        if sample.is_degradable():
            # 觸發降級至 yaml_only
    """

    async def get_wal_lag_seconds(self) -> float:
        """查詢主從 replication lag（秒）。"""

    async def get_active_connections(self) -> int:
        """查詢目前 active 連線數。"""

    async def sample(self) -> PgHealthSample:
        """一次性採樣，回 PgHealthSample 含告警等級。"""


def classify_lag(lag_seconds: float) -> PgLagLevel:
    """依 ADR-SD08-005 §2.4 三閾值分類。

    Args:
        lag_seconds: WAL replication lag（秒，非負）

    Returns:
        PgLagLevel
    """
    if lag_seconds < 0:
        return PgLagLevel.NORMAL  # 異常負值視為正常（pg_replay_timestamp 偶爾回未來）
    if lag_seconds < WAL_LAG_WARN_SECONDS:
        return PgLagLevel.NORMAL
    if lag_seconds < WAL_LAG_CRITICAL_SECONDS:
        return PgLagLevel.WARN
    return PgLagLevel.CRITICAL


# ──────────────────────────────────────────────────────────────
# DefaultPgHealthMonitor — 真實 PG 查詢實作（asyncpg）
# ──────────────────────────────────────────────────────────────
class DefaultPgHealthMonitor:
    """asyncpg 後端 PgHealthMonitor 實作（SD_09 啟用前置）。

    建構式注入 IObservabilityPort；sample() 觸發 emit_counter / emit_histogram。

    使用模式：
        from autoclaude.infra.adapters.observability.local_logger import LocalLogger
        obs = LocalLogger()
        monitor = DefaultPgHealthMonitor(observability=obs, dsn=os.environ["PG_DSN"])
        sample = await monitor.sample()
    """

    # WAL lag 查詢（容忍主庫無 replica 場景：pg_last_xact_replay_timestamp 回 NULL）
    _WAL_LAG_QUERY = """
        SELECT COALESCE(
            EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp())),
            0.0
        ) AS lag_seconds
    """

    _ACTIVE_CONN_QUERY = """
        SELECT count(*) FROM pg_stat_activity
        WHERE state = 'active' AND backend_type = 'client backend'
    """

    def __init__(
        self,
        *,
        observability: Optional[IObservabilityPort] = None,
        dsn: Optional[str] = None,
        connection_factory=None,
    ):
        """
        Args:
            observability: IObservabilityPort；None 時用 NullObservability fallback
            dsn: PG 連線 DSN；測試可省略並注入 connection_factory
            connection_factory: 測試夾具用；async () -> Connection（含 fetchval / fetchrow）
        """
        self._obs: IObservabilityPort = observability or NullObservability()
        self._dsn = dsn
        self._factory = connection_factory

    async def _acquire(self):
        """取得連線（測試可注入 factory；正式環境用 asyncpg）。"""
        if self._factory is not None:
            return await self._factory()
        # 正式環境 lazy import asyncpg（測試環境可能未裝）
        import asyncpg  # type: ignore[import-not-found]

        if not self._dsn:
            raise ValueError("DefaultPgHealthMonitor 需提供 dsn 或 connection_factory")
        return await asyncpg.connect(self._dsn)

    async def get_wal_lag_seconds(self) -> float:
        conn = await self._acquire()
        try:
            val = await conn.fetchval(self._WAL_LAG_QUERY)
            return float(val) if val is not None else 0.0
        finally:
            await conn.close()

    async def get_active_connections(self) -> int:
        conn = await self._acquire()
        try:
            val = await conn.fetchval(self._ACTIVE_CONN_QUERY)
            return int(val) if val is not None else 0
        finally:
            await conn.close()

    async def sample(self) -> PgHealthSample:
        """一次性採樣 + 透過 IObservabilityPort 發送 metric。

        Metric 行為（ADR-SD08-005 §2.4）：
          - 永遠 emit_histogram("pg_wal_lag_seconds", lag, tags={"level": ...})
          - warn 等級：emit_counter("pg_wal_lag_warn")
          - critical 等級：emit_counter("pg_wal_lag_critical") + record_event("pg_degrade_yaml_only")
          - 永遠 emit_histogram("pg_active_connections", conns)
        """
        lag = await self.get_wal_lag_seconds()
        conns = await self.get_active_connections()
        level = classify_lag(lag)

        # 永遠 emit lag histogram（趨勢監控）
        self._obs.emit_histogram(
            "pg_wal_lag_seconds", lag, tags={"level": level.value}
        )
        self._obs.emit_histogram("pg_active_connections", float(conns))

        # 告警 counter
        if level == PgLagLevel.WARN:
            self._obs.emit_counter("pg_wal_lag_warn", tags={"lag": f"{lag:.1f}"})
        elif level == PgLagLevel.CRITICAL:
            self._obs.emit_counter("pg_wal_lag_critical", tags={"lag": f"{lag:.1f}"})
            self._obs.record_event(
                "pg_degrade_yaml_only",
                attributes={"wal_lag_seconds": lag, "trigger": "wal_lag_critical"},
            )

        return PgHealthSample(
            wal_lag_seconds=lag,
            active_connections=conns,
            level=level,
        )


__all__ = [
    "PgHealthMonitor",
    "DefaultPgHealthMonitor",
    "PgHealthSample",
    "PgLagLevel",
    "classify_lag",
    "WAL_LAG_WARN_SECONDS",
    "WAL_LAG_CRITICAL_SECONDS",
]
