"""PgGoalProgressLedger — GoalProgressLedger PostgreSQL 對等（F-C2 / ADR-AGT-003 L4）。

storage.mode in ('both', 'db_only') 路由（factory.build_goal_progress_ledger）。
落地：`goal_progress` 表（alembic 0016，append-only）。

介面與 utils.goal_progress.GoalProgressLedger 對等（record / summarize），
DB 失敗 warning 不中斷主流程。

⚠️ 須安裝：pip install autoclaude[postgres]
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("autoclaude.infra.adapters.pg_goal_progress_ledger")

_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import select

    from ..repositories._pg_models import GoalProgressRow
    from ..repositories.pg_async_utils import _run_async
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    from ..repositories.pg_async_utils import _run_async  # type: ignore[import]


class PgGoalProgressLedger:
    """PostgreSQL 後端：goal_progress 表 append-only ledger。"""

    def __init__(self, engine: Any):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgGoalProgressLedger 需 sqlalchemy + asyncpg；"
                "請執行 pip install autoclaude[postgres]"
            )
        self._engine = engine

    def record(
        self,
        goal_task_id: str,
        *,
        playbook_id: str | None = None,
        run_id: str | None = None,
        completed_features: list[str] | None = None,
        progress_pct: float | None = None,
    ) -> None:
        try:
            _run_async(self._record(
                goal_task_id, playbook_id, run_id,
                completed_features or [], progress_pct,
            ))
        except Exception as exc:
            logger.warning("PgGoalProgressLedger.record 失敗 (goal=%s): %s",
                           goal_task_id, exc)

    def summarize(self, goal_task_id: str) -> dict:
        try:
            return _run_async(self._summarize(goal_task_id))
        except Exception as exc:
            logger.warning("PgGoalProgressLedger.summarize 失敗: %s", exc)
            return {
                "goal_task_id": goal_task_id, "run_count": 0,
                "completed_features": [], "progress_pct": None,
                "last_recorded_at": None,
            }

    # ── 內部 async ───────────────────────────────────────────
    async def _record(self, goal, playbook_id, run_id, features, pct) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(GoalProgressRow.__table__.insert(), [{
                "goal_task_id": goal,
                "playbook_id": playbook_id,
                "run_id": run_id,
                "completed_features": features,
                "progress_pct": pct,
            }])

    async def _summarize(self, goal: str) -> dict:
        async with self._engine.connect() as conn:
            rows = (await conn.execute(
                select(GoalProgressRow)
                .where(GoalProgressRow.goal_task_id == goal)
                .order_by(GoalProgressRow.recorded_at.asc())
            )).all()
        features: list[str] = []
        seen: set[str] = set()
        latest_pct = None
        latest_ts = None
        for r in rows:
            row = r[0]
            for feat in (row.completed_features or []):
                if feat not in seen:
                    seen.add(feat)
                    features.append(feat)
            if row.progress_pct is not None:
                latest_pct = float(row.progress_pct)
            latest_ts = row.recorded_at.isoformat() if row.recorded_at else latest_ts
        return {
            "goal_task_id": goal,
            "run_count": len(rows),
            "completed_features": features,
            "progress_pct": latest_pct,
            "last_recorded_at": latest_ts,
        }


__all__ = ["PgGoalProgressLedger"]
