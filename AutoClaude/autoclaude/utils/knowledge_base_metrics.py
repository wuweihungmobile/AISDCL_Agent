"""KnowledgeBaseMetrics — FailureKnowledgeBase 觀測指標（SD_08 W4 / ADR-SD08-004 §2.4）。

設計原則（≤ 150 LOC data tier）：
  - 4 metric（不含 cache_size，純記憶體統計無 SLO 意義）：
      hit_rate              : KB query 命中率（成功命中 / 總查詢）
      query_p95_ms          : KB query latency p95（最近 N=200 滑動窗口）
      strategy_rotation_count : 策略輪換次數（next_strategy() 觸發）
      cache_eviction_count  : 記憶體淘汰次數（_MAX_ENTRIES 1000 滿時 LRU evict）
  - snapshot() 與 AutoResumeMetrics 一致設計（pure dict，淺拷貝）
  - 純記憶體統計，不寫檔；KB 重新建構時自然重置

對應：
  - ADR-SD08-004 §2.4 KB metric 設計
  - SD_Improving_08.md §4.1 程式碼交付
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# 滑動窗口大小（最近 200 次 query latency 估算 p95）
_LATENCY_WINDOW_SIZE = 200


@dataclass
class KnowledgeBaseMetrics:
    """FailureKnowledgeBase 觀測指標。

    使用模式：
        metrics = KnowledgeBaseMetrics()
        # query 流程
        metrics.record_query(hit=True, latency_ms=12.3)
        # 策略輪換
        metrics.record_strategy_rotation()
        # cache eviction
        metrics.record_cache_eviction()
        # snapshot
        snap = metrics.snapshot()
        assert snap["hit_rate"] == 1.0

    搭配 IObservabilityPort（FailureKnowledgeBase 整合點）：
        obs.emit_counter("kb_hit_total", tags={"hit": "true"})
        obs.emit_histogram("kb_query_latency_ms", 12.3)
    """

    # 累計計數
    total_queries: int = 0
    total_hits: int = 0
    strategy_rotation_count: int = 0
    cache_eviction_count: int = 0

    # latency 滑動窗口（bounded deque 防 memory leak）
    _latency_window: deque = field(
        default_factory=lambda: deque(maxlen=_LATENCY_WINDOW_SIZE)
    )

    # ── 公開 API ──────────────────────────────────────────────
    @property
    def hit_rate(self) -> float:
        """命中率（0.0~1.0）；total_queries=0 時回 0.0。"""
        if self.total_queries == 0:
            return 0.0
        return self.total_hits / self.total_queries

    @property
    def query_p95_ms(self) -> float:
        """latency p95（最近 N=200 滑動窗口）；窗口為空回 0.0。

        近似演算法：sort + index([0.95 * N]-1)；N < 20 時退化為 max。
        """
        if not self._latency_window:
            return 0.0
        sorted_lat = sorted(self._latency_window)
        n = len(sorted_lat)
        if n < 20:
            return float(sorted_lat[-1])
        idx = max(0, int(0.95 * n) - 1)
        return float(sorted_lat[idx])

    def record_query(self, *, hit: bool, latency_ms: float) -> None:
        """記錄一次 query；hit=True 計入 hit_total；latency_ms 進滑動窗口。"""
        self.total_queries += 1
        if hit:
            self.total_hits += 1
        if latency_ms >= 0:
            self._latency_window.append(float(latency_ms))

    def record_strategy_rotation(self) -> None:
        """策略輪換 +1（next_strategy 觸發時）。"""
        self.strategy_rotation_count += 1

    def record_cache_eviction(self) -> None:
        """cache eviction +1（LRU 淘汰時）。"""
        self.cache_eviction_count += 1

    def snapshot(self) -> dict:
        """與 AutoResumeMetrics 一致的 snapshot 模式（純 dict，淺拷貝）。

        Returns:
            {
                "hit_rate": float (0.0~1.0),
                "query_p95_ms": float (>=0),
                "strategy_rotation_count": int,
                "cache_eviction_count": int,
                "total_queries": int,
                "total_hits": int,
            }
        """
        return {
            "hit_rate": self.hit_rate,
            "query_p95_ms": self.query_p95_ms,
            "strategy_rotation_count": self.strategy_rotation_count,
            "cache_eviction_count": self.cache_eviction_count,
            # 額外暴露原始計數（debug / monitoring 用）
            "total_queries": self.total_queries,
            "total_hits": self.total_hits,
        }


__all__ = ["KnowledgeBaseMetrics"]
