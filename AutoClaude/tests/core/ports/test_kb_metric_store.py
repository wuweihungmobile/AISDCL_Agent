"""IKbMetricStore Port 契約測試（F-C3 / ADR-SD09-006 §2.1）。

驗證意圖：Port 介面凍結後（SCG-3），任何符合 Protocol 的實作可被
runtime_checkable 識別；MetricValue 為不可變值物件（防 adapter 竄改快照）。
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autoclaude.core.ports.kb_metric_store import IKbMetricStore, MetricValue


def _mv(name: str = "kb_queries_total", value: float = 1.0) -> MetricValue:
    now = datetime.now(UTC)
    return MetricValue(
        metric_name=name, value=value, window_start_at=now, window_end_at=now
    )


class _CompliantStore:
    def record_counter(self, name, delta, *, tags=None):
        pass

    def record_histogram(self, name, value, *, tags=None):
        pass

    def snapshot(self):
        return {}

    def flush(self):
        pass

    def query_window(self, metric, since):
        return []


class _IncompleteStore:
    def record_counter(self, name, delta, *, tags=None):
        pass


class TestProtocolContract:
    def test_compliant_implementation_passes_isinstance(self):
        assert isinstance(_CompliantStore(), IKbMetricStore)

    def test_incomplete_implementation_fails_isinstance(self):
        assert not isinstance(_IncompleteStore(), IKbMetricStore)


class TestMetricValue:
    def test_frozen_immutable(self):
        mv = _mv()
        with pytest.raises(AttributeError):
            mv.value = 99.0  # type: ignore[misc]

    def test_optional_fields_default_none(self):
        mv = _mv()
        assert mv.run_id is None
        assert mv.tags is None
