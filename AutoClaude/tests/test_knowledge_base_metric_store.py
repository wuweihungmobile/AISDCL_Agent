"""F-C3 整合測試 — FailureKnowledgeBase × IKbMetricStore（持久化驗收）。

驗證意圖：凍結計畫 Phase 1 驗收條件一「重啟後 metrics 不清零」。
metrics 必須經 metric_store 跨實例存活；未注入時行為與 SD_08 W4 完全相同
（向下相容，原 2,853 基線零回歸）。
"""
from __future__ import annotations

from autoclaude.infra.adapters.local_kb_metric_store import LocalKbMetricStore
from autoclaude.infra.repositories.factory import build_kb_metric_store
from autoclaude.utils.config import StorageConfig
from autoclaude.utils.knowledge_base import FailureKnowledgeBase


def _kb(tmp_path, store=None) -> FailureKnowledgeBase:
    return FailureKnowledgeBase(
        str(tmp_path / "failure_knowledge_base.jsonl"), metric_store=store
    )


class TestMetricsPersistAcrossRestart:
    def test_counters_survive_kb_restart(self, tmp_path):
        """F-C3 核心驗收：persist 後重建 KB（模擬重啟）counters 不清零。"""
        store_path = str(tmp_path / ".kb_metrics_local.jsonl")
        kb1 = _kb(tmp_path, LocalKbMetricStore(store_path))
        kb1.query("sig-a")
        kb1.record_success("sig-a", "PINPOINT", "T01")
        kb1.query("sig-a")  # hit
        kb1.persist_metrics()

        kb2 = _kb(tmp_path, LocalKbMetricStore(store_path))
        snap = kb2.metrics_snapshot()
        assert snap["total_queries"] == 2
        assert snap["total_hits"] == 1

    def test_restored_counters_continue_accumulating(self, tmp_path):
        store_path = str(tmp_path / ".kb_metrics_local.jsonl")
        kb1 = _kb(tmp_path, LocalKbMetricStore(store_path))
        kb1.query("sig-a")
        kb1.persist_metrics()

        kb2 = _kb(tmp_path, LocalKbMetricStore(store_path))
        kb2.query("sig-b")
        assert kb2.metrics_snapshot()["total_queries"] == 2

    def test_strategy_rotation_persisted(self, tmp_path):
        store_path = str(tmp_path / ".kb_metrics_local.jsonl")
        kb1 = _kb(tmp_path, LocalKbMetricStore(store_path))
        kb1.get_strategy_priority("syntax")
        kb1.persist_metrics()

        kb2 = _kb(tmp_path, LocalKbMetricStore(store_path))
        assert kb2.metrics_snapshot()["strategy_rotation_count"] == 1


class TestBackwardCompatibility:
    def test_no_store_keeps_memory_only_behavior(self, tmp_path):
        """未注入 metric_store：原 SD_08 W4 行為（記憶體累計、重建清零）。"""
        kb1 = _kb(tmp_path)
        kb1.query("sig-a")
        kb1.persist_metrics()  # no-op，不得 raise

        kb2 = _kb(tmp_path)
        assert kb2.metrics_snapshot()["total_queries"] == 0

    def test_broken_store_does_not_break_kb(self, tmp_path):
        """metric_store 全面故障時 KB 主流程（query/record）不受影響（fail-soft）。"""

        class _Broken:
            def record_counter(self, *a, **k):
                raise RuntimeError("boom")

            def record_histogram(self, *a, **k):
                raise RuntimeError("boom")

            def snapshot(self):
                raise RuntimeError("boom")

            def flush(self):
                raise RuntimeError("boom")

            def query_window(self, *a, **k):
                raise RuntimeError("boom")

        kb = _kb(tmp_path, _Broken())
        assert kb.query("sig-a") is None
        kb.record_success("sig-a", "PINPOINT", "T01")
        kb.persist_metrics()
        assert kb.metrics_snapshot()["total_queries"] == 1


class TestFactoryRouting:
    def test_yaml_only_routes_to_local(self, tmp_path):
        store = build_kb_metric_store(str(tmp_path), StorageConfig(mode="yaml_only"))
        assert isinstance(store, LocalKbMetricStore)
