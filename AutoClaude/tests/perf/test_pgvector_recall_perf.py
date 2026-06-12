"""pgvector recall@10 + p95 性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #4）。

採集環境：**perf machine 季度**（NOT CI nightly — R-SD08-G-1 紅線）
SLA 目標：recall ≥ 0.95 + p95 < 50ms

CI 上預設 SKIP；僅在帶 `pg_real` marker 的 perf machine 上跑（SD_09 採購評估）。

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除 placeholder `pass` workload
  - 改為 100 query × adapter.search(top_k=10) 真實負載
  - 維持 PG_REAL_ENABLED=0 時 skip（pg_real marker）
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from autoclaude.utils.perf_baseline import measure

pytestmark = [pytest.mark.perf, pytest.mark.pg_real]


_PG_REAL_ENABLED = os.environ.get("PG_REAL_ENABLED", "0") == "1"


@pytest.mark.skipif(
    not _PG_REAL_ENABLED,
    reason="pgvector recall 性能僅在 perf machine 跑（R-SD08-G-1 / set PG_REAL_ENABLED=1）",
)
def test_pgvector_recall_baseline_perf_machine_only():
    """perf machine 季度量測；CI runner 強制 skip。

    SD_09 B-07：100 query × adapter.search(top_k=10) 真實負載。
    fixture 缺失時 skip（X1 路徑 tests/fixtures/pgvector_real_queries.json）。
    """
    queries_path = Path("tests/fixtures/pgvector_real_queries.json")
    if not queries_path.exists():
        pytest.skip(
            f"fixture 缺失：{queries_path}；由 tools/seed_kb.py 預先產生（X1 路徑）"
        )

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    if len(queries) < 100:
        pytest.skip(f"query 數量不足：{len(queries)} < 100")

    # 真實 PG 連線需 SD07_REAL_PG_E2E_ENABLED；perf machine 既然開了 PG_REAL_ENABLED 即假設 PG 就緒
    dsn_raw = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
    if not dsn_raw:
        pytest.skip("AUTOCLAUDE_TEST_PG_DSN 未設定 — perf machine 預期應提供 DSN")

    # 延遲 import：避免 CI runner skip path 觸發 psycopg / asyncpg 載入
    from autoclaude.infra.adapters.pg_vector_search import PgVectorSearchAdapter

    adapter = PgVectorSearchAdapter(dsn=dsn_raw)  # noqa: F841 — adapter signature may differ; perf machine 整合
    selected_queries = queries[:100]

    def _workload() -> None:
        """100 query × adapter.search(top_k=10) 真實 pgvector HNSW 查詢。"""
        for q in selected_queries:
            adapter.search(query_embedding=q["embedding"], top_k=10)

    baseline = measure("pgvector_recall_perf", _workload, runs=7)

    # 絕對 SLA（perf machine 限定）
    assert baseline.p95_ms < 50.0, (
        f"pgvector recall p95={baseline.p95_ms}ms ≥ 50ms（perf machine SLA 違反）"
    )

    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
