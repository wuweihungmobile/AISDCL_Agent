"""PgPreferenceStore — IPreferenceStore PostgreSQL 後端（F-C1 / ADR-AGT-003 L3）。

storage.mode in ('both', 'db_only') 路由（factory.build_preference_store）。
落地：`user_preferences` 表（alembic 0016，UPSERT by (scope, key)）。

DB 失敗 warning 不中斷主流程（偏好為輔助功能，與 PgMemoryStore 一致）。

⚠️ 須安裝：pip install 'autoclaude[postgres]'
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("autoclaude.infra.adapters.pg_preference_store")

_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import func, select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from ..repositories._pg_models import UserPreferenceRow
    from ..repositories.pg_async_utils import _run_async
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    from ..repositories.pg_async_utils import _run_async  # type: ignore[import]


class PgPreferenceStore:
    """PostgreSQL 後端：user_preferences 表 UPSERT。"""

    def __init__(self, engine: Any):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgPreferenceStore 需 sqlalchemy + asyncpg；"
                "請執行 pip install 'autoclaude[postgres]'"
            )
        self._engine = engine

    # ── IPreferenceStore Protocol ────────────────────────────
    def get(self, key: str, scope: str = "global") -> str | None:
        try:
            return _run_async(self._get(key, scope))
        except Exception as exc:
            logger.warning("PgPreferenceStore.get 失敗 (key=%s): %s", key, exc)
            return None

    def set(self, key: str, value: str, scope: str = "global") -> None:
        try:
            _run_async(self._set(key, value, scope))
        except Exception as exc:
            logger.warning("PgPreferenceStore.set 失敗 (key=%s): %s", key, exc)

    def list(self, scope: str | None = None) -> dict[str, str]:
        try:
            return _run_async(self._list(scope))
        except Exception as exc:
            logger.warning("PgPreferenceStore.list 失敗: %s", exc)
            return {}

    # ── 內部 async ───────────────────────────────────────────
    async def _get(self, key: str, scope: str) -> str | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                select(UserPreferenceRow.value).where(
                    UserPreferenceRow.scope == scope,
                    UserPreferenceRow.key == key,
                )
            )).first()
        return row[0] if row else None

    async def _set(self, key: str, value: str, scope: str) -> None:
        stmt = pg_insert(UserPreferenceRow.__table__).values(
            scope=scope, key=key, value=value,
        ).on_conflict_do_update(
            index_elements=["scope", "key"],
            # func.now() 為 SQL 函式；字串 "now()" 會被當綁定參數導致
            # PG invalid input syntax（SA·SD audit 複核發現）
            set_={"value": value, "updated_at": func.now()},
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def _list(self, scope: str | None) -> dict[str, str]:
        async with self._engine.connect() as conn:
            if scope is not None:
                rows = (await conn.execute(
                    select(UserPreferenceRow.key, UserPreferenceRow.value)
                    .where(UserPreferenceRow.scope == scope)
                )).all()
                return {k: v for k, v in rows}
            rows = (await conn.execute(
                select(UserPreferenceRow.scope, UserPreferenceRow.key,
                       UserPreferenceRow.value)
            )).all()
        # 合併視圖：global 先鋪底，playbook:* 覆寫同名鍵（與 FilePreferenceStore 對等）
        merged = {k: v for s, k, v in rows if s == "global"}
        for s, k, v in rows:
            if s != "global":
                merged[k] = v
        return merged


__all__ = ["PgPreferenceStore"]
