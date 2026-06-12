"""SD_Improving_08 W4 / T4-F13：KnowledgeBaseMetrics 測試（≥ 4 case）。

涵蓋：
  1. 4 metric 計算（hit_rate / query_p95_ms / strategy_rotation_count / cache_eviction_count）
  2. snapshot() 一致性（dict 內容與屬性同步）
  3. hit_rate 邊界 0 / 1（全 miss / 全 hit）
  4. cache_eviction_count 累計
  5. p95 滑動窗口大小限制（≤ 200）
  6. p95 小樣本退化為 max

對應 ADR-SD08-004 §2.4 / §4 T4-F13。
"""
from __future__ import annotations

import pytest

from autoclaude.utils.knowledge_base_metrics import KnowledgeBaseMetrics


# ──────────────────────────────────────────────────────────────
# 1. 4 metric 計算（含 cache_eviction_count）
# ──────────────────────────────────────────────────────────────
def test_four_metrics_basic_computation():
    m = KnowledgeBaseMetrics()
    # 10 次 query：7 hit / 3 miss
    for _ in range(7):
        m.record_query(hit=True, latency_ms=5.0)
    for _ in range(3):
        m.record_query(hit=False, latency_ms=10.0)
    # 2 次策略輪換
    m.record_strategy_rotation()
    m.record_strategy_rotation()
    # 1 次 cache eviction
    m.record_cache_eviction()

    assert m.total_queries == 10
    assert m.total_hits == 7
    assert m.hit_rate == 0.7
    assert m.strategy_rotation_count == 2
    assert m.cache_eviction_count == 1
    # query_p95_ms：10 個樣本不足 20，退化為 max
    assert m.query_p95_ms == 10.0


# ──────────────────────────────────────────────────────────────
# 2. snapshot() 與屬性一致
# ──────────────────────────────────────────────────────────────
def test_snapshot_matches_properties():
    m = KnowledgeBaseMetrics()
    m.record_query(hit=True, latency_ms=3.5)
    m.record_strategy_rotation()
    m.record_cache_eviction()

    snap = m.snapshot()
    assert snap["hit_rate"] == m.hit_rate == 1.0
    assert snap["query_p95_ms"] == m.query_p95_ms
    assert snap["strategy_rotation_count"] == 1
    assert snap["cache_eviction_count"] == 1
    assert snap["total_queries"] == 1
    assert snap["total_hits"] == 1


# ──────────────────────────────────────────────────────────────
# 3. hit_rate 邊界 0 / 1
# ──────────────────────────────────────────────────────────────
def test_hit_rate_boundary_zero_and_one():
    # 全 miss
    m1 = KnowledgeBaseMetrics()
    for _ in range(5):
        m1.record_query(hit=False, latency_ms=1.0)
    assert m1.hit_rate == 0.0

    # 全 hit
    m2 = KnowledgeBaseMetrics()
    for _ in range(5):
        m2.record_query(hit=True, latency_ms=1.0)
    assert m2.hit_rate == 1.0

    # 空：total_queries=0 → hit_rate=0.0
    m3 = KnowledgeBaseMetrics()
    assert m3.hit_rate == 0.0
    assert m3.query_p95_ms == 0.0


# ──────────────────────────────────────────────────────────────
# 4. cache_eviction_count 累計
# ──────────────────────────────────────────────────────────────
def test_cache_eviction_count_accumulates():
    m = KnowledgeBaseMetrics()
    for _ in range(100):
        m.record_cache_eviction()
    assert m.cache_eviction_count == 100
    assert m.snapshot()["cache_eviction_count"] == 100


# ──────────────────────────────────────────────────────────────
# 5. p95 滑動窗口 maxlen=200（不無限增長）
# ──────────────────────────────────────────────────────────────
def test_latency_window_bounded_at_200():
    m = KnowledgeBaseMetrics()
    for i in range(500):
        m.record_query(hit=True, latency_ms=float(i))
    assert len(m._latency_window) == 200
    # 最舊 300 筆已被擠出；最新 200 筆為 300~499
    assert min(m._latency_window) == 300.0
    assert max(m._latency_window) == 499.0


# ──────────────────────────────────────────────────────────────
# 6. p95 大樣本 (n >= 20) 採 sort + index
# ──────────────────────────────────────────────────────────────
def test_p95_large_sample_uses_percentile():
    m = KnowledgeBaseMetrics()
    # 100 個樣本：1.0 ~ 100.0
    for i in range(1, 101):
        m.record_query(hit=True, latency_ms=float(i))
    # idx = max(0, int(0.95*100)-1) = 94 → sorted[94] = 95.0
    assert m.query_p95_ms == 95.0
