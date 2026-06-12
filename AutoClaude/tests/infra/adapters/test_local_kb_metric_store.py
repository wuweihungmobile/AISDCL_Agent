"""LocalKbMetricStore 單元測試（F-C3）。

驗證意圖：F-C3 驗收條件「重啟後 metrics 不清零」— 持久化必須真的跨實例存活，
而非僅記憶體累計；flush 失敗不可中斷主流程（KB 為輔助功能）。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from autoclaude.core.ports.kb_metric_store import IKbMetricStore
from autoclaude.infra.adapters.local_kb_metric_store import LocalKbMetricStore


def _store(tmp_path) -> LocalKbMetricStore:
    return LocalKbMetricStore(str(tmp_path / ".kb_metrics_local.jsonl"))


class TestProtocolCompliance:
    def test_satisfies_ikbmetricstore(self, tmp_path):
        assert isinstance(_store(tmp_path), IKbMetricStore)


class TestCounterAndHistogram:
    def test_counter_accumulates(self, tmp_path):
        s = _store(tmp_path)
        s.record_counter("kb_queries_total", 1)
        s.record_counter("kb_queries_total", 2)
        assert s.snapshot()["kb_queries_total"].value == 3.0

    def test_histogram_p95_small_sample_is_max(self, tmp_path):
        s = _store(tmp_path)
        for v in (1.0, 5.0, 3.0):
            s.record_histogram("kb_query_latency_ms", v)
        assert s.snapshot()["kb_query_latency_ms"].value == 5.0


class TestPersistenceAcrossRestart:
    def test_counters_survive_restart(self, tmp_path):
        """F-C3 核心驗收：flush 後新實例（模擬重啟）counters 不清零。"""
        path = tmp_path / ".kb_metrics_local.jsonl"
        s1 = LocalKbMetricStore(str(path))
        s1.record_counter("kb_queries_total", 7)
        s1.record_counter("kb_hits_total", 3)
        s1.flush()

        s2 = LocalKbMetricStore(str(path))
        snap = s2.snapshot()
        assert snap["kb_queries_total"].value == 7.0
        assert snap["kb_hits_total"].value == 3.0

    def test_restart_then_increment_continues_from_restored(self, tmp_path):
        path = tmp_path / ".kb_metrics_local.jsonl"
        s1 = LocalKbMetricStore(str(path))
        s1.record_counter("kb_queries_total", 7)
        s1.flush()

        s2 = LocalKbMetricStore(str(path))
        s2.record_counter("kb_queries_total", 1)
        assert s2.snapshot()["kb_queries_total"].value == 8.0

    def test_histogram_window_not_restored(self, tmp_path):
        """latency 為短期窗口統計（SRD §1.3），重啟重算。"""
        path = tmp_path / ".kb_metrics_local.jsonl"
        s1 = LocalKbMetricStore(str(path))
        s1.record_histogram("kb_query_latency_ms", 10.0)
        s1.flush()

        s2 = LocalKbMetricStore(str(path))
        assert "kb_query_latency_ms" not in s2.snapshot()

    def test_corrupted_file_starts_from_zero_without_raising(self, tmp_path):
        path = tmp_path / ".kb_metrics_local.jsonl"
        path.write_text("not-json\n", encoding="utf-8")
        s = LocalKbMetricStore(str(path))
        assert s.snapshot() == {}


class TestQueryWindow:
    def test_returns_only_rows_after_since(self, tmp_path):
        path = tmp_path / ".kb_metrics_local.jsonl"
        s = LocalKbMetricStore(str(path))
        s.record_counter("kb_queries_total", 1)
        s.flush()
        s.record_counter("kb_queries_total", 1)
        s.flush()

        since_past = datetime.now(UTC) - timedelta(days=1)
        rows = s.query_window("kb_queries_total", since_past)
        assert [r.value for r in rows] == [1.0, 2.0]

        since_future = datetime.now(UTC) + timedelta(days=1)
        assert s.query_window("kb_queries_total", since_future) == []

    def test_unknown_metric_returns_empty(self, tmp_path):
        s = _store(tmp_path)
        s.flush()
        assert s.query_window("nope", datetime.now(UTC) - timedelta(days=1)) == []
