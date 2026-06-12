"""SD_Improving_08 W4 / T4-F10：FailureKnowledgeBase × IObservabilityPort 整合測試。

涵蓋：
  1. query hit → metrics.hit_total +1 + observability.emit_counter(kb_hit_total, tags={hit: true})
  2. query miss → metrics.miss + observability.emit_counter(kb_hit_total, tags={hit: false})
  3. get_strategy_priority → metrics.strategy_rotation +1 + observability.emit_counter
  4. metrics_snapshot 與 KnowledgeBaseMetrics.snapshot 一致
  5. observability=None → metrics 仍累計（不依賴 observability）
"""
from __future__ import annotations

from autoclaude.utils.knowledge_base import FailureKnowledgeBase


class _RecordingObservability:
    """測試夾具：紀錄所有 emit 呼叫供斷言。"""

    def __init__(self):
        self.counters: list[tuple[str, int, dict]] = []
        self.histograms: list[tuple[str, float, dict]] = []

    def emit_counter(self, name, value=1, tags=None):
        self.counters.append((name, value, dict(tags or {})))

    def emit_histogram(self, name, value, tags=None):
        self.histograms.append((name, value, dict(tags or {})))

    def start_span(self, name, tags=None):
        from autoclaude.core.ports.observability import NullObservability
        return NullObservability().start_span(name, tags)

    def record_event(self, name, attributes=None):
        pass


def test_query_hit_emits_kb_hit_total_true(tmp_path):
    obs = _RecordingObservability()
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"), observability=obs)
    kb.record_success("syntax:err1", "PINPOINT", "T01", error_class="syntax")

    result = kb.query("syntax:err1")

    assert result is not None
    counters = [c for c in obs.counters if c[0] == "kb_hit_total"]
    assert len(counters) == 1
    assert counters[0][2] == {"hit": "true"}
    # latency histogram 至少一筆
    assert any(h[0] == "kb_query_latency_ms" for h in obs.histograms)
    snap = kb.metrics_snapshot()
    assert snap["hit_rate"] == 1.0
    assert snap["total_queries"] == 1


def test_query_miss_emits_kb_hit_total_false(tmp_path):
    obs = _RecordingObservability()
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"), observability=obs)

    result = kb.query("nonexistent_sig")
    assert result is None
    counters = [c for c in obs.counters if c[0] == "kb_hit_total"]
    assert counters[0][2] == {"hit": "false"}
    snap = kb.metrics_snapshot()
    assert snap["hit_rate"] == 0.0


def test_strategy_priority_emits_rotation_counter(tmp_path):
    obs = _RecordingObservability()
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"), observability=obs)

    kb.get_strategy_priority("syntax")
    kb.get_strategy_priority("assertion")

    rotations = [c for c in obs.counters if c[0] == "kb_strategy_rotation_count"]
    assert len(rotations) == 2
    assert rotations[0][2] == {"error_class": "syntax"}
    assert rotations[1][2] == {"error_class": "assertion"}
    assert kb.metrics_snapshot()["strategy_rotation_count"] == 2


def test_metrics_accumulate_without_observability(tmp_path):
    """observability=None 時 metrics 仍純記憶體累計（不可依賴 observability）。"""
    kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"), observability=None)
    kb.record_success("err1", "PINPOINT", "T01", error_class="syntax")

    kb.query("err1")
    kb.query("missing")
    kb.get_strategy_priority("syntax")

    snap = kb.metrics_snapshot()
    assert snap["total_queries"] == 2
    assert snap["total_hits"] == 1
    assert snap["hit_rate"] == 0.5
    assert snap["strategy_rotation_count"] == 1
