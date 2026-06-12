"""IObservabilityPort — 可觀測性 Hexagonal Port（SD_Improving_08 W4 / ADR-SD08-004 §2.1）。

設計原則（contract tier ≤ 400）：
  - 純 Protocol + dataclass，零實作、零外部依賴
  - 與 IBrain / IExecutor / IEvaluator 同層級，由 wiring 建構式注入 Kernel
  - LocalLogger（W4 唯一實作）位於 `autoclaude/infra/adapters/observability/`
  - 未來 OTel adapter（SD_10+）以平行 adapter 形式並存

禁止：
  ❌ 將 OTel SDK 直接散落於 plugin / service（ADR-SD08-004 §2.1）
  ❌ Plugin 直接 import `utils.knowledge_base_metrics` / `utils.trace_context`
     （必須走 Port 注入；importlinter Rule 7 強制）
  ❌ 將本 Port 放在 `utils/` 而非 `core/ports/`（紅線 ❌18 / ADR-SD08-004 §2.1）

對應：
  - ADR-SD08-004 §2.1 邊界劃分 + §2.2 IObservabilityPort 簽名
  - SD_Improving_08.md §4.1 程式碼交付
"""
from __future__ import annotations

from typing import Mapping, Optional, Protocol, runtime_checkable


# ──────────────────────────────────────────────────────────────
# ISpan — span 生命週期管理（context manager 介面）
# ──────────────────────────────────────────────────────────────
@runtime_checkable
class ISpan(Protocol):
    """Span 生命週期 Protocol；trace_id 由 ContextVar 自動注入。

    使用模式：
        with obs.start_span("kernel.run", tags={"step_id": "T01"}) as span:
            span.set_attribute("retries", 2)
            ...
    """

    def __enter__(self) -> "ISpan":
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        ...

    def set_attribute(self, key: str, value: object) -> None:
        """設定 span 屬性（key/value）。"""

    def record_exception(self, exception: BaseException) -> None:
        """記錄 span 內部例外（不影響例外傳播）。"""


# ──────────────────────────────────────────────────────────────
# IObservabilityPort — 可觀測性 Port（與 IBrain/IExecutor 同層級）
# ──────────────────────────────────────────────────────────────
@runtime_checkable
class IObservabilityPort(Protocol):
    """可觀測性 Port — Hexagonal 介面（ADR-SD08-004 §2.2）。

    簽名穩定承諾：
      - emit_counter / emit_histogram / start_span / record_event 為穩定 API
      - 新增 metric 不需修改本 Port；Adapter 端透過 name 區分

    使用模式（plugin / service）：
        # 建構式注入（必須）
        def __init__(self, observability: Optional[IObservabilityPort] = None):
            self._obs = observability or NullObservability()  # 預設 no-op
    """

    def emit_counter(
        self, name: str, value: int = 1, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        """累計型 metric（如 kb_hit_total / autoresume_wake_total）。

        Args:
            name: metric 名稱（snake_case，建議 namespace_metric_total 結尾）
            value: 累計增量（預設 1，可傳負數做減量）
            tags: 維度標籤（如 {"kind": "halt"}）
        """

    def emit_histogram(
        self, name: str, value: float, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        """分布型 metric（如 kb_query_latency_ms / dry_run_duration_ms）。

        Args:
            name: metric 名稱（建議 _ms / _seconds / _bytes 等單位後綴）
            value: 觀測值（float）
            tags: 維度標籤
        """

    def start_span(
        self, name: str, tags: Optional[Mapping[str, str]] = None
    ) -> ISpan:
        """span 生命週期管理（context manager）；trace_id 由 ContextVar 自動注入。

        Args:
            name: span 名稱（建議 dot.notation，例：kernel.run / brain.decide_correction）
            tags: 初始屬性

        Returns:
            ISpan instance（適用於 with 區塊）
        """

    def record_event(
        self, name: str, attributes: Optional[Mapping[str, object]] = None
    ) -> None:
        """事件記錄（如 token_halt / esc_f12_interrupt）。

        Args:
            name: 事件名稱（snake_case）
            attributes: 任意 metadata（會帶 trace_id 自動注入）
        """


# ──────────────────────────────────────────────────────────────
# NullObservability — 預設 no-op Adapter（測試 / 未注入時 fallback）
# ──────────────────────────────────────────────────────────────
class _NullSpan:
    """No-op Span；測試 / 未注入 Adapter 時 fallback。"""

    def __enter__(self) -> "_NullSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        return None

    def set_attribute(self, key: str, value: object) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass


class NullObservability:
    """No-op IObservabilityPort 實作；任何呼叫皆不執行副作用。

    用途：
      - 測試夾具（不需驗證 metric 行為時）
      - 元件未注入 Adapter 時的 fallback（避免散落 None check）

    符合 IObservabilityPort Protocol（duck typing）。
    """

    def emit_counter(
        self, name: str, value: int = 1, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        pass

    def emit_histogram(
        self, name: str, value: float, tags: Optional[Mapping[str, str]] = None
    ) -> None:
        pass

    def start_span(
        self, name: str, tags: Optional[Mapping[str, str]] = None
    ) -> ISpan:
        return _NullSpan()  # type: ignore[return-value]

    def record_event(
        self, name: str, attributes: Optional[Mapping[str, object]] = None
    ) -> None:
        pass


__all__ = [
    "IObservabilityPort",
    "ISpan",
    "NullObservability",
]
