"""PgVectorSearchAdapter — IVectorSearch 的 pgvector 實作 + HNSW dual-read fallback。

對應規格（SD_Improving_06 W3-T3-24）：
  - §6 表 0008：新欄位 embedding_v halfvec(1024) + 舊欄位 vector(1536) dual-read
  - §6.5 AC4-5：recall@10 ≥ 0.95 + p95 < 50ms
  - §11 黃線：CircuitBreaker 偵測 latency > 200ms 三次 → 切舊欄位 (legacy fallback)；
    黃線告警（不阻塞），48h Wave 內修正期

策略：
  - 預設走 ``embedding_v halfvec(1024)`` + per-model_id partial HNSW
  - breaker open → 自動降級走舊 ``embedding vector(1536)``（dim=1536，model_id 不過濾）
  - 每次 search 都記錄 latency；recover：half_open 探測一次成功即 closed
  - 提供 ``preferred_source`` 強制路徑（測試用 / 維運降級開關）
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ...core.ports.vector_search import (
    IVectorSearch,
    Namespace,
    SearchStats,
    VectorHit,
    VectorSearchError,
)
from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


_NEW_INDEX_SQL = {
    "knowledge_entries": (
        "SELECT entry_id::text AS id, "
        "       1 - (embedding_v <=> %s::halfvec) AS score, "
        "       embedding_model_id AS model_id, "
        "       jsonb_build_object('strategy', successful_strategy, "
        "                         'error_class', error_class) AS payload "
        "FROM knowledge_entries "
        "WHERE embedding_v IS NOT NULL "
        "  AND ({model_clause}) "
        "ORDER BY embedding_v <=> %s::halfvec "
        "LIMIT %s"
    ),
    "goal_tasks": (
        "SELECT goal_task_id::text AS id, "
        "       1 - (embedding_v <=> %s::halfvec) AS score, "
        "       embedding_model_id AS model_id, "
        "       jsonb_build_object('title', title, 'status', status) AS payload "
        "FROM goal_tasks "
        "WHERE embedding_v IS NOT NULL "
        "  AND ({model_clause}) "
        "ORDER BY embedding_v <=> %s::halfvec "
        "LIMIT %s"
    ),
    "execution_items": (
        "SELECT exec_id::text AS id, "
        "       1 - (embedding_v <=> %s::halfvec) AS score, "
        "       embedding_model_id AS model_id, "
        "       jsonb_build_object('action', action, 'status', status) AS payload "
        "FROM execution_items "
        "WHERE embedding_v IS NOT NULL "
        "  AND ({model_clause}) "
        "ORDER BY embedding_v <=> %s::halfvec "
        "LIMIT %s"
    ),
}

# legacy index 僅 knowledge_entries 有舊 vector(1536) 欄位（goal_tasks / execution_items 無）
_LEGACY_INDEX_SQL = {
    "knowledge_entries": (
        "SELECT entry_id::text AS id, "
        "       1 - (embedding <=> %s::vector) AS score, "
        "       'legacy-1536' AS model_id, "
        "       jsonb_build_object('strategy', successful_strategy, "
        "                         'error_class', error_class) AS payload "
        "FROM knowledge_entries "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s"
    ),
}


class PgVectorSearchAdapter:
    """pgvector HNSW 查詢 + dual-read fallback（IVectorSearch 實作）。"""

    def __init__(
        self,
        *,
        sql_executor,
        breaker: Optional[CircuitBreaker] = None,
        latency_alert_ms: float = 200.0,
        preferred_source: Optional[str] = None,
    ) -> None:
        self.sql = sql_executor
        self.breaker = breaker or CircuitBreaker(
            failure_threshold=3,
            latency_threshold_ms=latency_alert_ms,
            slow_call_threshold=3,
            recovery_seconds=60.0,
        )
        self.preferred_source = preferred_source  # "new" / "legacy" / None=auto

    @classmethod
    def from_dsn(cls, dsn: str, **kwargs) -> "PgVectorSearchAdapter":
        """整合測試便利工廠：從 psycopg2 格式 DSN 建立 adapter。

        dsn 必須是同步格式（不含 +asyncpg）。
        僅供整合測試使用；生產環境透過 wiring 注入 sql_executor。
        """
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(dsn)
        conn.autocommit = True

        def _fmt_params(params):
            # list[float] → halfvec literal string；避免 psycopg2 array 格式化開銷
            out = []
            for p in params:
                if isinstance(p, list) and p and isinstance(p[0], (int, float)):
                    out.append("[" + ",".join(f"{v:.8g}" for v in p) + "]")
                else:
                    out.append(p)
            return tuple(out)

        class _SyncExecutor:
            def execute(self, sql, params=()):
                with conn.cursor() as cur:
                    cur.execute(sql, _fmt_params(params))

            def fetch_one(self, sql, params=()):
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, _fmt_params(params))
                    return cur.fetchone()

            def fetch_all(self, sql, params=()):
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, _fmt_params(params))
                    return cur.fetchall() or []

        return cls(sql_executor=_SyncExecutor(), **kwargs)

    def search(
        self,
        *,
        namespace: Namespace,
        query_vector: list[float],
        model_id: str,
        top_k: int = 10,
        ef_search: Optional[int] = None,
        extra_filters: Optional[dict[str, Any]] = None,
    ) -> tuple[list[VectorHit], SearchStats]:
        if namespace not in _NEW_INDEX_SQL:
            raise VectorSearchError(f"unsupported namespace: {namespace}")

        # 1. 路徑決定
        source = self._decide_source(namespace)
        used_fallback = source == "legacy"

        # 2. 設定 ef_search（HNSW per session）
        if ef_search is not None:
            try:
                self.sql.execute(f"SET LOCAL hnsw.ef_search = {int(ef_search)}", ())
            except Exception:  # pragma: no cover — 部份 driver 不支援
                pass

        # 3. 執行查詢 + 量測 latency
        start = time.perf_counter()
        try:
            rows = self._execute(
                namespace=namespace,
                source=source,
                query_vector=query_vector,
                model_id=model_id,
                top_k=top_k,
            )
        except Exception as exc:
            self.breaker.record_failure()
            if source == "new" and namespace in _LEGACY_INDEX_SQL:
                logger.warning(
                    "pgvector new path failed; downgrading to legacy: %s", exc
                )
                start = time.perf_counter()
                rows = self._execute(
                    namespace=namespace,
                    source="legacy",
                    query_vector=query_vector,
                    model_id=model_id,
                    top_k=top_k,
                )
                used_fallback = True
            else:
                raise VectorSearchError(str(exc)) from exc
        latency_ms = (time.perf_counter() - start) * 1000.0
        self.breaker.record_success(latency_ms=latency_ms)

        hits = [
            VectorHit(
                id=str(r["id"]),
                score=float(r["score"]),
                model_id=str(r["model_id"]),
                payload=dict(r.get("payload") or {}),
                source="legacy" if used_fallback else "new",
            )
            for r in (rows or [])
        ]
        stats = SearchStats(
            latency_ms=latency_ms,
            used_fallback=used_fallback,
            candidate_count=len(hits),
            backend_index=(
                f"idx_{namespace}_embedding_hnsw"
                if not used_fallback
                else "idx_kb_embedding_legacy_hnsw"
            ),
        )
        return hits, stats

    def health_check(self) -> bool:
        try:
            self.sql.fetch_one("SELECT 1 AS ok", ())
            return True
        except Exception:
            return False

    def _decide_source(self, namespace: Namespace) -> str:
        if self.preferred_source in ("new", "legacy"):
            return self.preferred_source  # type: ignore[return-value]
        if self.breaker.allow_request():
            return "new"
        # breaker open；只有 KB 有 legacy 路徑
        if namespace in _LEGACY_INDEX_SQL:
            return "legacy"
        return "new"  # 沒有 legacy 路徑 → 仍嘗試 new（會觸發 record_failure）

    def _execute(
        self,
        *,
        namespace: str,
        source: str,
        query_vector: list[float],
        model_id: str,
        top_k: int,
    ) -> list[dict]:
        if source == "legacy":
            sql_tmpl = _LEGACY_INDEX_SQL[namespace]
            return self.sql.fetch_all(
                sql_tmpl,
                (query_vector, query_vector, top_k),
            ) or []
        # new path：依 model_id == "*" 決定是否做 dual-model 並讀
        if model_id == "*":
            model_clause = "embedding_model_id IS NOT NULL"
            params = (query_vector, query_vector, top_k)
        else:
            model_clause = "embedding_model_id = %s"
            params = (query_vector, model_id, query_vector, top_k)
        sql_str = _NEW_INDEX_SQL[namespace].format(model_clause=model_clause)
        # 註：params 順序對應 SQL 中 %s 出現順序：select_vec、(model)、order_vec、top_k
        if model_id == "*":
            return self.sql.fetch_all(
                sql_str.replace(
                    "WHERE embedding_v IS NOT NULL\n  AND (embedding_model_id IS NOT NULL)",
                    "WHERE embedding_v IS NOT NULL\n  AND (embedding_model_id IS NOT NULL)",
                ),
                params,
            ) or []
        return self.sql.fetch_all(sql_str, params) or []


# 靜態型別對齊（mypy 友善，運行期不執行）
if False:  # pragma: no cover
    _proto: IVectorSearch = PgVectorSearchAdapter(sql_executor=None)  # type: ignore[arg-type]
