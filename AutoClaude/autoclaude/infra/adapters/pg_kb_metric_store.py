"""PgKbMetricStore — IKbMetricStore PostgreSQL 後端（F-C3 / ADR-SD09-006 §2.2）。

storage.mode in ('both', 'db_only') 路由（factory.build_kb_metric_store）。
落地：`kb_metrics` 表（alembic 0016_agt_phase1_memory，append-only 快照）。

行為與 LocalKbMetricStore 對等：
  - 記憶體 buffer 累計；flush() 時每 counter/histogram 寫一列
  - 建構時讀各 counter 最新一列恢復累計值（重啟不清零）
  - 所有 DB 失敗 warning 不中斷主流程（KB 為輔助功能，與 PgMemoryStore 一致）

⚠️ 須安裝：pip install 'autoclaude[postgres]'
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("autoclaude.infra.adapters.pg_kb_metric_store")

_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import select

    from ..repositories._pg_models import KbMetricRow
    from ..repositories.pg_async_utils import _run_async
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    from ..repositories.pg_async_utils import _run_async  # type: ignore[import]

# fallback import 模式後置（與 pg_memory_store 同款結構）
from ...core.ports.kb_metric_store import MetricValue  # noqa: E402, I001

_HISTOGRAM_WINDOW = 200


def _p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    s = sorted(samples)
    n = len(s)
    if n < 20:
        return float(s[-1])
    return float(s[max(0, int(0.95 * n) - 1)])


class PgKbMetricStore:
    """PostgreSQL 後端：記憶體 buffer + kb_metrics 表快照。"""

    def __init__(self, engine: Any):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgKbMetricStore 需 sqlalchemy + asyncpg；"
                "請執行 pip install 'autoclaude[postgres]'"
            )
        self._engine = engine
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, deque] = {}
        self._window_start = datetime.now(UTC)
        self._restore_latest_counters()

    # ── IKbMetricStore Protocol ──────────────────────────────
    def record_counter(
        self, name: str, delta: int, *, tags: dict[str, str] | None = None
    ) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + delta

    def record_histogram(
        self, name: str, value: float, *, tags: dict[str, str] | None = None
    ) -> None:
        window = self._histograms.setdefault(name, deque(maxlen=_HISTOGRAM_WINDOW))
        window.append(float(value))

    def snapshot(self) -> dict[str, MetricValue]:
        now = datetime.now(UTC)
        result: dict[str, MetricValue] = {}
        for name, value in self._counters.items():
            result[name] = MetricValue(
                metric_name=name, value=value,
                window_start_at=self._window_start, window_end_at=now,
            )
        for name, window in self._histograms.items():
            result[name] = MetricValue(
                metric_name=name, value=_p95(list(window)),
                window_start_at=self._window_start, window_end_at=now,
            )
        return result

    def flush(self) -> None:
        try:
            _run_async(self._flush_async(self.snapshot()))
        except Exception as exc:
            logger.warning("PgKbMetricStore.flush 失敗（warning，繼續主流程）: %s", exc)

    def query_window(self, metric: str, since: datetime) -> list[MetricValue]:
        try:
            return _run_async(self._query_window_async(metric, since))
        except Exception as exc:
            logger.warning("PgKbMetricStore.query_window 失敗: %s", exc)
            return []

    # ── 內部 async ───────────────────────────────────────────
    async def _flush_async(self, snap: dict[str, MetricValue]) -> None:
        if not snap:
            return
        rows = [
            {
                "metric_name": mv.metric_name,
                "value": mv.value,
                "window_start_at": mv.window_start_at,
                "window_end_at": mv.window_end_at,
            }
            for mv in snap.values()
        ]
        async with self._engine.begin() as conn:
            await conn.execute(KbMetricRow.__table__.insert(), rows)

    async def _query_window_async(
        self, metric: str, since: datetime
    ) -> list[MetricValue]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                select(KbMetricRow)
                .where(
                    KbMetricRow.metric_name == metric,
                    KbMetricRow.window_end_at >= since,
                )
                .order_by(KbMetricRow.window_end_at.asc())
            )
            rows = result.all()
        return [
            MetricValue(
                metric_name=r[0].metric_name,
                value=float(r[0].value),
                window_start_at=r[0].window_start_at,
                window_end_at=r[0].window_end_at,
                run_id=str(r[0].run_id) if r[0].run_id else None,
            )
            for r in rows
        ]

    def _restore_latest_counters(self) -> None:
        """讀各 counter metric（*_total 命名）最新一列恢復累計值。"""
        try:
            self._counters = _run_async(self._restore_async())
        except Exception as exc:
            logger.warning("PgKbMetricStore 恢復失敗（以零起算）: %s", exc)
            self._counters = {}

    async def _restore_async(self) -> dict[str, float]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                select(
                    KbMetricRow.metric_name, KbMetricRow.value, KbMetricRow.window_end_at
                ).order_by(KbMetricRow.metric_name, KbMetricRow.window_end_at.desc())
            )
            rows = result.all()
        restored: dict[str, float] = {}
        for name, value, _end in rows:
            # 每 metric 只取最新一列（rows 已依 name + end DESC 排序）
            if name not in restored and name.endswith("_total"):
                restored[name] = float(value)
        return restored


__all__ = ["PgKbMetricStore"]
