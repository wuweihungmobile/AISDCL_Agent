"""LocalLogger — IObservabilityPort 的 stdlib logging 實作（SD_08 W4 / ADR-SD08-004）。

設計原則（adapter tier ≤ 400）：
  - 零外部相依（純 stdlib logging）
  - 結構化 log（JSON 形式）便於後續 grep / parse
  - trace_id 自動從 ContextVar 注入（無需 caller 顯式傳入）
  - span 行為：__enter__ 記錄 start，__exit__ 記錄 end + duration_ms
  - 例外語意：record_exception 寫入 ERROR；__exit__ 收到 exc 自動 record + re-raise

對應：
  - ADR-SD08-004 §2.1 LocalLogger 為 W4 唯一實作
  - ADR-SD08-004 §2.5 階段性混合策略 Phase 1
"""
from __future__ import annotations

import json
import logging
import time
from typing import Mapping, Optional

from ....core.ports.observability import IObservabilityPort, ISpan

# 內部 logger（structured event 全部統一從此 logger 發出，便於 filter）
_logger = logging.getLogger("autoclaude.observability")


def _safe_tags(tags: Optional[Mapping[str, str]]) -> dict:
    """安全轉換 tags（None → {}，過濾不可序列化值）。"""
    if not tags:
        return {}
    return {str(k): str(v) for k, v in tags.items()}


def _safe_attributes(attrs: Optional[Mapping[str, object]]) -> dict:
    """安全轉換 attributes；不可序列化值轉 str。"""
    if not attrs:
        return {}
    out: dict = {}
    for k, v in attrs.items():
        try:
            json.dumps(v)
            out[str(k)] = v
        except (TypeError, ValueError):
            out[str(k)] = repr(v)
    return out


def _current_trace_id() -> Optional[str]:
    """從 ContextVar 取得當前 trace_id（lazy import 避免 utils → core 循環）。"""
    # lazy import 避免測試夾具尚未初始化 ContextVar 時的 ImportError
    try:
        from ....utils.trace_context import get_trace_id
        return get_trace_id()
    except ImportError:
        return None


class LocalLoggerSpan:
    """LocalLogger 的 ISpan 實作；記錄 start/end + duration_ms。

    生命週期：
      - __enter__：寫 INFO log（event=span_start）+ 記錄 _start_ns
      - set_attribute / record_exception：累積屬性
      - __exit__：寫 INFO log（event=span_end + duration_ms）；
                  若收到 exc，先 record_exception 再讓例外傳播
    """

    def __init__(self, name: str, tags: Optional[Mapping[str, str]] = None):
        self._name = name
        self._tags = _safe_tags(tags)
        self._attributes: dict = {}
        self._start_ns: int = 0
        self._exception: Optional[BaseException] = None

    def __enter__(self) -> "LocalLoggerSpan":
        self._start_ns = time.monotonic_ns()
        _logger.info(
            "observability_span_start",
            extra={
                "event": "span_start",
                "span_name": self._name,  # 避免與 LogRecord.name 衝突
                "trace_id": _current_trace_id(),
                "tags": self._tags,
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        duration_ms = (time.monotonic_ns() - self._start_ns) / 1_000_000.0
        if exc_val is not None and self._exception is None:
            self.record_exception(exc_val)
        _logger.info(
            "observability_span_end",
            extra={
                "event": "span_end",
                "span_name": self._name,
                "trace_id": _current_trace_id(),
                "tags": self._tags,
                "attributes": self._attributes,
                "duration_ms": round(duration_ms, 3),
                "exception": (
                    None if self._exception is None
                    else type(self._exception).__name__
                ),
            },
        )
        return None  # 不抑制例外傳播

    def set_attribute(self, key: str, value: object) -> None:
        self._attributes[str(key)] = _safe_attributes({"_": value})["_"]

    def record_exception(self, exception: BaseException) -> None:
        self._exception = exception
        _logger.error(
            "observability_span_exception",
            extra={
                "event": "span_exception",
                "span_name": self._name,
                "trace_id": _current_trace_id(),
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )


class LocalLogger:
    """IObservabilityPort 的 stdlib logging 實作（ADR-SD08-004 W4 唯一 Adapter）。

    輸出格式（structured log via logging.extra）：
        {
            "event": "counter" | "histogram" | "record_event" | "span_*",
            "name": "<metric_name>",
            "value": <int|float>,
            "tags": {...},
            "trace_id": "<uuid>" | null,
        }

    後端遷移成本（SD_10+）：
      - OTel adapter 僅需替換 _logger.info → otel_meter.create_counter / span
      - 接受 IObservabilityPort Protocol 的呼叫方零修改
    """

    def emit_counter(
        self, name: str, value: int = 1, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        # 注意：LogRecord 保留 "name" / "message" / "asctime" 等 key，
        # 使用 "metric_name" 避免 KeyError "Attempt to overwrite 'name' in LogRecord"
        _logger.info(
            "observability_counter",
            extra={
                "event": "counter",
                "metric_name": name,
                "value": int(value),
                "tags": _safe_tags(tags),
                "trace_id": _current_trace_id(),
            },
        )

    def emit_histogram(
        self, name: str, value: float, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        _logger.info(
            "observability_histogram",
            extra={
                "event": "histogram",
                "metric_name": name,
                "value": float(value),
                "tags": _safe_tags(tags),
                "trace_id": _current_trace_id(),
            },
        )

    def start_span(
        self, name: str, tags: Optional[Mapping[str, str]] = None
    ) -> ISpan:
        return LocalLoggerSpan(name, tags)  # type: ignore[return-value]

    def record_event(
        self, name: str, attributes: Optional[Mapping[str, object]] = None
    ) -> None:
        _logger.info(
            "observability_event",
            extra={
                "event": "record_event",
                "event_name": name,
                "attributes": _safe_attributes(attributes),
                "trace_id": _current_trace_id(),
            },
        )


__all__ = ["LocalLogger", "LocalLoggerSpan"]
