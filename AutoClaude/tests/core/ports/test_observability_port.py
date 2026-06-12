"""SD_Improving_08 W4 / T4-F8：IObservabilityPort 契約測試（≥ 6 case）。

涵蓋：
  1. Protocol 合約：LocalLogger 滿足 IObservabilityPort
  2. Protocol 合約：NullObservability 滿足 IObservabilityPort
  3. LocalLogger.emit_counter 寫入 structured log（含 trace_id）
  4. LocalLogger.emit_histogram 寫入 structured log（含 value 與 tags）
  5. LocalLogger.start_span 為 context manager + 自動記錄 duration_ms
  6. LocalLogger.record_event 注入當前 trace_id
  7. ContextVar 傳遞：with_trace_id() 內 emit 帶該 trace_id
  8. NullObservability 為 no-op（不拋例外）+ span no-op

對應 ADR-SD08-004 §2.2 / §4 T4-F8。
"""
from __future__ import annotations

import logging

import pytest

from autoclaude.core.ports.observability import (
    IObservabilityPort,
    ISpan,
    NullObservability,
)
from autoclaude.infra.adapters.observability import LocalLogger, LocalLoggerSpan
from autoclaude.utils.trace_context import with_trace_id


# ──────────────────────────────────────────────────────────────
# 1~2. Protocol 合約
# ──────────────────────────────────────────────────────────────
def test_local_logger_satisfies_iobservability_port():
    """LocalLogger 必須是 IObservabilityPort 的 Protocol 合規實作。"""
    obs = LocalLogger()
    assert isinstance(obs, IObservabilityPort)


def test_null_observability_satisfies_iobservability_port():
    """NullObservability 必須符合 Protocol（供測試夾具使用）。"""
    obs = NullObservability()
    assert isinstance(obs, IObservabilityPort)


# ──────────────────────────────────────────────────────────────
# 3. emit_counter 寫入 structured log
# ──────────────────────────────────────────────────────────────
def test_local_logger_emit_counter_writes_structured_log(caplog):
    obs = LocalLogger()
    with caplog.at_level(logging.INFO, logger="autoclaude.observability"):
        obs.emit_counter("kb_hit_total", value=1, tags={"hit": "true"})
    matched = [r for r in caplog.records if getattr(r, "event", None) == "counter"]
    assert len(matched) == 1
    rec = matched[0]
    assert rec.__dict__["metric_name"] == "kb_hit_total"
    assert rec.__dict__["value"] == 1
    assert rec.__dict__["tags"] == {"hit": "true"}


# ──────────────────────────────────────────────────────────────
# 4. emit_histogram 寫入 structured log
# ──────────────────────────────────────────────────────────────
def test_local_logger_emit_histogram_records_value_and_tags(caplog):
    obs = LocalLogger()
    with caplog.at_level(logging.INFO, logger="autoclaude.observability"):
        obs.emit_histogram("kb_query_latency_ms", value=12.3, tags={"backend": "file"})
    matched = [r for r in caplog.records if getattr(r, "event", None) == "histogram"]
    assert len(matched) == 1
    rec = matched[0]
    assert rec.__dict__["metric_name"] == "kb_query_latency_ms"
    assert rec.__dict__["value"] == 12.3
    assert rec.__dict__["tags"] == {"backend": "file"}


# ──────────────────────────────────────────────────────────────
# 5. start_span 為 context manager + duration_ms
# ──────────────────────────────────────────────────────────────
def test_local_logger_start_span_is_context_manager_with_duration(caplog):
    obs = LocalLogger()
    with caplog.at_level(logging.INFO, logger="autoclaude.observability"):
        with obs.start_span("test.span", tags={"step": "T01"}) as span:
            assert isinstance(span, ISpan)
            assert isinstance(span, LocalLoggerSpan)
            span.set_attribute("retries", 2)
    # span_start + span_end 都要出現
    events = [r.__dict__.get("event") for r in caplog.records]
    assert "span_start" in events
    assert "span_end" in events
    end_record = next(r for r in caplog.records if r.__dict__.get("event") == "span_end")
    assert end_record.__dict__["duration_ms"] >= 0.0
    assert end_record.__dict__["attributes"] == {"retries": 2}
    assert end_record.__dict__["exception"] is None


# ──────────────────────────────────────────────────────────────
# 6. record_event 注入當前 trace_id
# ──────────────────────────────────────────────────────────────
def test_local_logger_record_event_injects_trace_id_from_contextvar(caplog):
    obs = LocalLogger()
    with caplog.at_level(logging.INFO, logger="autoclaude.observability"):
        with with_trace_id("fixed-trace-001") as tid:
            obs.record_event("token_halt", attributes={"pct": 95})
    matched = [r for r in caplog.records if r.__dict__.get("event") == "record_event"]
    assert len(matched) == 1
    rec = matched[0]
    assert rec.__dict__["event_name"] == "token_halt"
    assert rec.__dict__["trace_id"] == "fixed-trace-001"
    assert rec.__dict__["attributes"] == {"pct": 95}


# ──────────────────────────────────────────────────────────────
# 7. ContextVar 傳遞：with_trace_id 內 emit_counter 帶該 trace_id
# ──────────────────────────────────────────────────────────────
def test_emit_counter_inside_with_trace_id_carries_trace(caplog):
    obs = LocalLogger()
    with caplog.at_level(logging.INFO, logger="autoclaude.observability"):
        with with_trace_id("trace-xyz") as tid:
            obs.emit_counter("kb_hit_total", value=1)
        # 出 with 區塊 trace_id 應還原 None
        obs.emit_counter("outside_counter", value=1)
    counters = [r for r in caplog.records if r.__dict__.get("event") == "counter"]
    assert counters[0].__dict__["trace_id"] == "trace-xyz"
    assert counters[1].__dict__["trace_id"] is None


# ──────────────────────────────────────────────────────────────
# 8. NullObservability 為 no-op（不拋例外 + span no-op）
# ──────────────────────────────────────────────────────────────
def test_null_observability_is_pure_noop():
    obs = NullObservability()
    # 所有呼叫皆 no-op
    obs.emit_counter("x")
    obs.emit_counter("x", value=5, tags={"k": "v"})
    obs.emit_histogram("y", value=1.5)
    obs.emit_histogram("y", value=2.5, tags={"k": "v"})
    obs.record_event("z")
    obs.record_event("z", attributes={"k": 1})
    with obs.start_span("span") as span:
        span.set_attribute("k", "v")
        span.record_exception(RuntimeError("ignored"))


def test_local_logger_span_records_exception_and_propagates():
    """span 在 with 區塊內遇例外時：先 record_exception，再讓例外傳播。"""
    obs = LocalLogger()
    with pytest.raises(ValueError):
        with obs.start_span("failing_span"):
            raise ValueError("expected")
