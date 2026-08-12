"""IKbMetricStore — KB metric 跨 session 統計儲存 Port（ADR-SD09-006 §2.1 canonical）。

Improving_012 Phase 1 F-C3（SCG-1 凍結於 SRD_AGT_Phase1_Memory.md §1.1）：
  - LocalKbMetricStore（yaml_only）落地 `.kb_metrics_local.jsonl`
  - PgKbMetricStore（both/db_only）落地 `kb_metrics` 表（alembic 0016）
  - Plugin 不可直接 import 本模組（importlinter Rule 8；經 FailureKnowledgeBase 注入路由）

設計原則（data tier ≤ 150）：純 Protocol + dataclass，零實作、零外部依賴。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class MetricValue:
    """單一 metric 視窗值（ADR-SD09-006 §2.1）。

    window_start_at / window_end_at 採 [start, end) 半開區間，聚合不重複。
    """

    metric_name: str
    value: float
    window_start_at: datetime
    window_end_at: datetime
    run_id: str | None = None
    tags: dict[str, str] | None = None


@runtime_checkable
class IKbMetricStore(Protocol):
    """KB metric 跨 session 統計儲存抽象（議題 G W0 拍板 (a)）。"""

    def record_counter(
        self, name: str, delta: int, *, tags: dict[str, str] | None = None
    ) -> None:
        """計數器累加（kb_queries_total / kb_strategy_rotation_total 等）。"""

    def record_histogram(
        self, name: str, value: float, *, tags: dict[str, str] | None = None
    ) -> None:
        """直方圖樣本（kb_query_latency_ms 等）。"""

    def snapshot(self) -> dict[str, MetricValue]:
        """當前快照（含自後端恢復之累計值；key = metric_name）。"""

    def flush(self) -> None:
        """強制寫入後端（避免 buffer in-memory 丟失）。"""

    def query_window(self, metric: str, since: datetime) -> list[MetricValue]:
        """視窗查詢（GA 30 天連續綠取證使用）。"""


# R85（訴求 2）：p95／HISTOGRAM_WINDOW 的 SSOT。此前 local_kb_metric_store 與
# pg_kb_metric_store 各持一份**逐字相同**的 `_p95` 與 `_HISTOGRAM_WINDOW`，並且
# tests/infra/adapters/test_pg_phase1_adapters.py 還特地 import 兩份、parametrize
# 跑同一組斷言來證明「兩份實作行為一致」——那支測試的存在本身就是重複的證據。
# 收斂到唯一定義後，兩個 adapter 以 `import p95 as _p95` 保留原私有名（呼叫端與該
# 測試的 import 皆不需改動），一致性由「只有一份」保證，不再靠測試去比對。
HISTOGRAM_WINDOW = 200  # 與 KnowledgeBaseMetrics latency 窗口一致


def p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    s = sorted(samples)
    n = len(s)
    if n < 20:
        return float(s[-1])
    return float(s[max(0, int(0.95 * n) - 1)])


__all__ = ["IKbMetricStore", "MetricValue", "HISTOGRAM_WINDOW", "p95"]
