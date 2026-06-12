"""infra/observability — 基礎設施層可觀測性 adapter（SD_08 W5 / ADR-SD08-005）。

模組職責：
  - pg_health.py : PgHealthMonitor / DefaultPgHealthMonitor（WAL lag + 連線數）

注意：
  - 與 `autoclaude/core/ports/observability.py`（IObservabilityPort）為「實作 vs 介面」分層；
    本模組為 health-check adapter，會 emit metric 給 IObservabilityPort 但不實作 Port。
  - 與 `autoclaude/infra/adapters/observability/local_logger.py`（IObservabilityPort 實作）為「資料來源 vs metric sink」分層。
"""
from __future__ import annotations

from .pg_health import (
    DefaultPgHealthMonitor,
    PgHealthMonitor,
    PgHealthSample,
    PgLagLevel,
)

__all__ = [
    "PgHealthMonitor",
    "DefaultPgHealthMonitor",
    "PgHealthSample",
    "PgLagLevel",
]
