"""_token_observer — Kernel 路徑的 token 使用率觀測器（improving_78 W-78-1 / DEF-78-001）。

職責（純觀測，零副作用）：
  - 作為 ``IExecutor.execute(..., on_event=callback)`` 的 callback，消費 ExecutionEvent
    串流，追蹤單次步驟執行期間 context 使用率（token%）的最高水位（peak）。
  - 兩種事件來源（對稱兩後端）：
      * SDK（SdkExecutorAdapter）：直接發 ``TOKEN_PCT`` 事件 payload ``{"pct": float}``。
      * PTY（PtyExecutor）：只發 ``PARTIAL_OUTPUT`` 行文字；以 ``extract_context_pct``
        （預設 regex）自行解析行內 context 百分比（鏡像已棄用 prompt_dispatcher 的作法）。

背景（DEF-78-001）：production 唯一正式路徑（Kernel）原本呼叫 executor 時不傳 on_event，
token% 事件無處可去 → token-guard 的 ≥90% halt 編排在 production 結構性死碼。本觀測器
讓 Kernel 能拿到「executor 已測得的真實 token%」，據以 emit ON_TOKEN_USAGE 觸發 halt 決策。

設計原則：
  - 純粹、無 I/O；callback 邊界錯誤由呼叫端（executor adapter）吞掉，不影響執行。
  - 無 token 事件時 peak 維持 0.0 → Kernel 不觸發 halt → 與接線前行為完全一致（零退化）。
"""
from __future__ import annotations

from .ports.executor import ExecutionEvent, ExecutionEventKind


class TokenObserver:
    """觀測單次步驟執行的 token% 峰值（ExecutionEvent callback）。"""

    def __init__(self) -> None:
        self._peak_pct: float = 0.0

    @property
    def peak_pct(self) -> float:
        """本次觀測到的 context 使用率最高水位（0.0 = 未觀測到任何 token 訊號）。"""
        return self._peak_pct

    def __call__(self, event: ExecutionEvent) -> None:
        """消費單一 ExecutionEvent，更新 peak（僅 TOKEN_PCT / PARTIAL_OUTPUT 有意義）。"""
        kind = getattr(event, "kind", None)
        payload = getattr(event, "payload", None) or {}
        if kind == ExecutionEventKind.TOKEN_PCT:
            pct = payload.get("pct")
            if pct is not None:
                self._observe(float(pct))
        elif kind == ExecutionEventKind.PARTIAL_OUTPUT:
            text = payload.get("text", "")
            if text:
                # late import 避免模組載入期 core→utils 相依（與 event_bus 既有作法一致）
                from ..utils.token_tracker import extract_context_pct
                pct = extract_context_pct(text)
                if pct is not None:
                    self._observe(pct)

    def _observe(self, pct: float) -> None:
        if pct > self._peak_pct:
            self._peak_pct = pct
