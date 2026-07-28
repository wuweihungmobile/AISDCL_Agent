"""PgMemoryStore — IMemoryStore 的 PostgreSQL 後端（Phase 6 選配）。

⚠️ 需安裝：pip install 'autoclaude[postgres]'
   pgvector 向量查詢需額外：pip install pgvector
"""
from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("autoclaude.infra.repositories.pg_memory")

_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import func, select, text

    from ._pg_models import _PGVECTOR_AVAILABLE, KnowledgeEntry
    from .pg_async_utils import _run_async
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False
    # C-A 修復：即使 sqlalchemy 未安裝，仍提供完整的 thread-safe _run_async
    from .pg_async_utils import _run_async  # type: ignore[import]


class PgMemoryStore:
    """PostgreSQL backend for IMemoryStore（knowledge_entries 表）。"""

    def __init__(self, engine: Any):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgMemoryStore 需 sqlalchemy + asyncpg；"
                "請執行：pip install 'autoclaude[postgres]'"
            )
        self._engine = engine

    # ──────────────────────────────────────────────
    # Public sync interface（相容 IMemoryStore Protocol）
    # ──────────────────────────────────────────────

    def query(self, error_signature: str) -> dict | None:
        try:
            return _run_async(self._query(error_signature))
        except Exception as exc:
            logger.warning("PgMemoryStore.query 失敗 (sig=%s): %s", error_signature[:60], exc)
            return None

    def query_semantic(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.8,
    ) -> list[dict]:
        """ANN cosine 相似度查詢；pgvector 未安裝時回傳空清單。"""
        if not _PGVECTOR_AVAILABLE:
            return []
        try:
            return _run_async(self._query_semantic(embedding, top_k, threshold))
        except ValueError as exc:
            # Dev-1：embedding 內含 inf/nan 屬於呼叫端錯誤，需明確上拋而非 silent
            logger.error("PgMemoryStore.query_semantic 拒絕無效 embedding: %s", exc)
            raise
        except Exception as exc:
            logger.warning("PgMemoryStore.query_semantic 失敗: %s", exc)
            return []

    def query_strategy_priority(self, error_class: str) -> list[str]:
        try:
            return _run_async(self._query_priority(error_class))
        except Exception as exc:
            logger.warning("PgMemoryStore.query_strategy_priority 失敗 (class=%s): %s",
                           error_class, exc)
            return []

    def record_success(
        self, error_signature: str, strategy: str,
        step_id: str, error_class: str = "unknown",
        embedding: list[float] | None = None,
    ) -> None:
        try:
            _run_async(self._record(
                error_signature, strategy, step_id, error_class,
                outcome="success", embedding=embedding,
            ))
        except Exception as exc:
            logger.warning("PgMemoryStore.record_success 失敗 (step=%s): %s", step_id, exc)

    def record_escalation(
        self, error_signature: str, tried_strategies: list[str], step_id: str,
    ) -> None:
        try:
            _run_async(self._record(
                error_signature, None, step_id, "unknown",
                outcome="escalation", tried=list(tried_strategies),
            ))
        except Exception as exc:
            logger.warning("PgMemoryStore.record_escalation 失敗 (step=%s): %s", step_id, exc)

    def stats_by_error_class(self) -> dict[str, dict]:
        try:
            return _run_async(self._stats())
        except Exception as exc:
            logger.warning("PgMemoryStore.stats_by_error_class 失敗: %s", exc)
            return {}

    # ──────────────────────────────────────────────
    # Private async implementation
    # ──────────────────────────────────────────────

    async def _query(self, sig: str) -> dict | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                select(KnowledgeEntry).where(KnowledgeEntry.error_signature == sig)
            )).first()
        if row is None:
            return None
        e = row[0]
        return {
            "error_class": e.error_class,
            "successful_strategy": e.successful_strategy,
            "step_id": e.step_id,
            "outcome": e.outcome,
        }

    async def _query_semantic(
        self, embedding: list[float], top_k: int, threshold: float
    ) -> list[dict]:
        """向量 ANN 查詢（pgvector cosine 距離 <=>）。

        僅回傳 outcome='success' 且相似度 >= threshold 的記錄，
        按相似度降序排列（距離越小越相似）。

        T4（SD_04 §3）：向量值改用 SQLAlchemy bindparams（:vec），
        徹底移除 f-string 拼接以消除 SQL 注入面（即便目前輸入為 float
        亦不應信任未來呼叫者，符合縱深防禦 Defense-in-depth 原則）。

        Dev-1：若 embedding 含 inf / nan / 非數值將拋 ValueError，
        避免被 silent except 吞掉導致 root cause 不明。
        """
        # 構造 pgvector 字面格式 "[v1,v2,...]"；浮點數安全轉字串
        # Dev-1：嚴格驗證每個元素為有限數（pgvector reject inf/nan，提前 fail-fast）
        sanitized: list[float] = []
        for i, v in enumerate(embedding):
            f = float(v)  # 非數值會拋 ValueError，由呼叫端 except 捕捉
            if not math.isfinite(f):
                raise ValueError(
                    f"embedding[{i}]={f!r} 為非有限數（inf/nan）；pgvector 不接受"
                )
            sanitized.append(f)
        # Dev-Minor-1：使用 .17g 確保 IEEE 754 雙精度浮點數無損往返序列化
        vec_literal = "[" + ",".join(format(v, '.17g') for v in sanitized) + "]"
        stmt = text(
            """
            SELECT error_class, error_signature, successful_strategy, step_id,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM knowledge_entries
            WHERE outcome = 'success'
              AND embedding IS NOT NULL
              AND 1 - (embedding <=> CAST(:vec AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
            """
        ).bindparams(vec=vec_literal, threshold=threshold, top_k=top_k)
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [
            {
                "error_class": r.error_class,
                "error_signature": r.error_signature,
                "successful_strategy": r.successful_strategy,
                "step_id": r.step_id,
                "similarity": float(r.similarity),
            }
            for r in rows
        ]

    async def _query_priority(self, error_class: str) -> list[str]:
        async with self._engine.connect() as conn:
            stmt = (
                select(KnowledgeEntry.successful_strategy, func.count().label("n"))
                .where(KnowledgeEntry.error_class == error_class)
                .where(KnowledgeEntry.outcome == "success")
                .group_by(KnowledgeEntry.successful_strategy)
                .order_by(func.count().desc())
            )
            result = await conn.execute(stmt)
        return [r[0] for r in result.all() if r[0]]

    async def _record(
        self, sig: str, strategy: str | None, step_id: str,
        error_class: str, outcome: str,
        tried: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> None:
        values: dict[str, Any] = dict(
            error_class=error_class, error_signature=sig,
            successful_strategy=strategy, step_id=step_id,
            outcome=outcome, tried_strategies=tried or [],
        )
        if embedding is not None and _PGVECTOR_AVAILABLE:
            values["embedding"] = embedding
        async with self._engine.begin() as conn:
            await conn.execute(
                KnowledgeEntry.__table__.insert().values(**values)
            )

    async def _stats(self) -> dict[str, dict]:
        async with self._engine.connect() as conn:
            stmt = (
                select(
                    KnowledgeEntry.error_class,
                    KnowledgeEntry.successful_strategy,
                    func.count().label("n"),
                )
                .where(KnowledgeEntry.outcome == "success")
                .group_by(KnowledgeEntry.error_class, KnowledgeEntry.successful_strategy)
            )
            rows = (await conn.execute(stmt)).all()
        result: dict[str, dict] = {}
        for ec, strategy, n in rows:
            d = result.setdefault(ec, {"success_count": 0, "strategies": {}})
            d["success_count"] += n
            if strategy:
                d["strategies"][strategy] = n
        return result
