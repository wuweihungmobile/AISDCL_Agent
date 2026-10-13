"""SD_Improving_06 W3-T3-28 — pgvector HNSW recall + latency（AC4-5）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-5：recall@10 ≥ 0.95 + p95 < 50ms
  - SD_Improving_06.md §11 黃線：dual-read fallback（< 0.90 才阻塞）

驗證項目（本檔現在只剩純單元，不連任何 DB）：
  T3 [純單元] PgVectorSearchAdapter 在 fake SQL 下能正確序列化 VectorHit
  T4 [純單元] preferred_source='legacy' 時走 legacy 路徑
  T5 [純單元] new 路徑失敗時自動 fallback legacy（KB 表）
  T6 [純單元] new 路徑連續慢呼叫 → breaker open
  T7 [純單元] 未支援 namespace 必須 raise

【廢止】T1／T2 已於 2026-10-13 依 PM 層級決定廢止（DEF-101-856；主控依掌舵者授權代決——那就是
SD_06 W3 G3「保留或顯式廢止」那道 PM 門檻的書面決定）：
  T1 [PG 整合] recall@10 ≥ 0.95
  T2 [PG 整合] p95 latency < 50ms（單機 1k 列基線）
兩支要的是「≥1k 列真實 BGE-M3 向量 ＋ HNSW index」的 staging 語料。任何 CI 執行者與本機都沒有
BGE-M3 權重與該語料，repo 內也沒有任何機械取得路徑；它們的函式體第一句就是無條件 skip，
從來沒有斷言過。掌舵者 2026-08-14 曾選「保留並建自動通道」，通道建了（`run_local_nightly.ps1` 的
pg-e2e stage 獨立呼叫本檔），缺的卻一直是受測資產而不是通道，所以這次改判廢止，不再續期。
  - 同門檻、**真的會斷言**的檢查由姊妹檔 `test_pgvector_real_recall.py` 的 `TestRecallAt10`／
    `TestP95Latency` 承接（就地 seed 100 列 mock-1024 語料；`run_local_nightly.ps1` 的
    pg-e2e stage 與 `autoclaude-ci.yml`／`autoclaude-pg-e2e-on-label.yml` 的 pg-e2e job 都跑它）。
    誠實劃界：那是 100 列 mock 語料，不是 1k 列真實 BGE-M3——這個差距是被廢止的內容，
    不是被遮起來的。
  - 「Production 上線紅線」（人類 DBA 於 staging ≥ 1M 真實列重跑 ＋ 人類 PM 親簽 release
    approval；見 `AutoClaude/CLAUDE.md` 同名段，現於第 153 行）本來就不是測試套件債，維持為
    人工 release gate，不因本次廢止而改變。
  - 被廢止段落的原文（含逐輪訂正史）不另存檔，取回方式：
    `git show b3caf68a:AutoClaude/tests/integration/test_pgvector_hnsw_recall.py`。
"""
from __future__ import annotations

import time

import pytest

from autoclaude.core.ports.vector_search import VectorHit, VectorSearchError
from autoclaude.infra.adapters.circuit_breaker import CircuitBreaker
from autoclaude.infra.adapters.pg_vector_search import PgVectorSearchAdapter

# ── 純單元：fake SQL executor ─────────────────────────────────

class _FakeSql:
    def __init__(self, *, rows: list[dict] | None = None, raise_on_new: bool = False,
                 latency_ms: float = 5.0) -> None:
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
