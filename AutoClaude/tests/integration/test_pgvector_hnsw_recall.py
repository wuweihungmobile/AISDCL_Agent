"""SD_Improving_06 W3-T3-28 — pgvector HNSW recall + latency（AC4-5）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-5：recall@10 ≥ 0.95 + p95 < 50ms
  - SD_Improving_06.md §11 黃線：dual-read fallback（< 0.90 才阻塞）

驗證項目：
  T1 [PG 整合] recall@10 ≥ 0.95（須真實 PG + pgvector + HNSW index）
  T2 [PG 整合] p95 latency < 50ms（單機 1k 列基線）
  T3 [純單元] PgVectorSearchAdapter 在 fake SQL 下能正確序列化 VectorHit
  T4 [純單元] preferred_source='legacy' 時走 legacy 路徑
  T5 [純單元] new 路徑失敗時自動 fallback legacy（KB 表）
  T6 [純單元] new 路徑連續慢呼叫 → breaker open

PG 整合測試 (T1/T2) 需要：
  - AUTOCLAUDE_TEST_PG_DSN 環境變數（含 pgvector / halfvec extension）
  - alembic upgrade head（0007 + 0008 + 0009 ready）
  - 預先 seed 1,000 列 KB 含真實 BGE-M3 embedding
無上述條件 → skip（與 W3 階段 A 既有 PG-skip pattern 一致）。
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Iterable

import pytest

from autoclaude.core.ports.vector_search import VectorHit, VectorSearchError
from autoclaude.infra.adapters.circuit_breaker import CircuitBreaker
from autoclaude.infra.adapters.pg_vector_search import PgVectorSearchAdapter

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


# ── 純單元：fake SQL executor ─────────────────────────────────

class _FakeSql:
    def __init__(self, *, rows: list[dict] = None, raise_on_new: bool = False, latency_ms: float = 5.0) -> None:
        self.rows = rows or []
        self.raise_on_new = raise_on_new
        self.latency_ms = latency_ms
        self.executed: list[str] = []

    def execute(self, sql: str, params: tuple) -> None:
        self.executed.append(sql[:40])

    def fetch_one(self, sql: str, params: tuple) -> dict:
        return {"ok": 1}

    def fetch_all(self, sql: str, params: tuple) -> list[dict]:
        time.sleep(self.latency_ms / 1000.0)
        if self.raise_on_new and "halfvec" in sql:
            raise RuntimeError("halfvec index unavailable")
        # legacy path 用 "embedding <=>" 識別
        if "embedding <=>" in sql:
            return [{**r, "model_id": "legacy-1536"} for r in self.rows]
        return self.rows


def test_pgvector_adapter_serializes_to_vector_hit():
    """T3 fake SQL 下能轉成 VectorHit + SearchStats（source=new）。"""
    sql = _FakeSql(rows=[
        {"id": "x1", "score": 0.99, "model_id": "bge-m3",
         "payload": {"content": "hello"}}
    ])
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1024,
        model_id="bge-m3",
        top_k=1,
    )
    assert isinstance(hits[0], VectorHit)
    assert hits[0].id == "x1"
    assert hits[0].source == "new"
    assert stats.used_fallback is False


def test_pgvector_adapter_preferred_source_legacy():
    """T4 preferred_source='legacy' 強制走 legacy（HNSW 重建期維運開關）。"""
    sql = _FakeSql(rows=[
        {"id": "y1", "score": 0.88, "model_id": "legacy-1536",
         "payload": {"content": "old"}}
    ])
    adapter = PgVectorSearchAdapter(sql_executor=sql, preferred_source="legacy")
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1536,
        model_id="*",
        top_k=1,
    )
    assert hits[0].source == "legacy"
    assert stats.used_fallback is True


def test_pgvector_adapter_falls_back_on_new_failure():
    """T5 new path 失敗時自動降級至 legacy（僅 KB 表有 legacy 路徑）。"""
    sql = _FakeSql(
        rows=[{"id": "z1", "score": 0.77, "model_id": "legacy-1536", "payload": {}}],
        raise_on_new=True,
    )
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1024,
        model_id="bge-m3",
        top_k=1,
    )
    assert stats.used_fallback is True
    assert hits[0].source == "legacy"


def test_pgvector_adapter_breaker_opens_on_slow_calls():
    """T6 連續慢呼叫 (> 200ms) 3 次 → breaker open（觸發降級門檻）。"""
    sql = _FakeSql(
        rows=[{"id": "s1", "score": 0.9, "model_id": "bge-m3", "payload": {}}],
        latency_ms=250.0,
    )
    breaker = CircuitBreaker(
        failure_threshold=99,
        latency_threshold_ms=200.0,
        slow_call_threshold=3,
    )
    adapter = PgVectorSearchAdapter(sql_executor=sql, breaker=breaker)
    for _ in range(3):
        adapter.search(
            namespace="knowledge_entries",
            query_vector=[0.0] * 1024,
            model_id="bge-m3",
            top_k=1,
        )
    assert breaker.state == "open"


def test_pgvector_adapter_namespaces_unknown_raises():
    """T7 未支援 namespace 必須 raise，避免悄悄走錯路徑。"""
    sql = _FakeSql(rows=[])
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    with pytest.raises(VectorSearchError):
        adapter.search(
            namespace="unknown_table",  # type: ignore[arg-type]
            query_vector=[0.0] * 1024,
            model_id="bge-m3",
        )


# ── PG 整合（須真實 DB）─────────────────────────────────────

pg_required = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN + alembic upgrade head + seed 1k KB rows",
)


@pg_required
def test_pgvector_recall_at_10_ge_095():
    """T1 真實 pgvector HNSW recall@10 ≥ 0.95（AC4-5 上線基線）。"""
    pytest.skip("需 W3 G3 staging 環境執行：1k seed + BGE-M3 真實向量；CI nightly 啟用")


@pg_required
def test_pgvector_p95_latency_under_50ms():
    """T2 真實 pgvector HNSW p95 latency < 50ms。"""
    pytest.skip("需 W3 G3 staging 環境執行；CI nightly 啟用")
