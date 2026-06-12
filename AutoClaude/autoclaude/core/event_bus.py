"""EventBus（SD_Improving_01.md v1.1 §3.4.2）。

職責：同步 dispatcher，依 priority 排序呼叫 plugin；合併 result 由 IResolutionPolicy 決定（DIP）。
PHASE_RESULT_CONTRACT 違反時 fail-fast；連續 3 次相同 phase 失敗加入 escalated_phases。

刻意設計：同步、無 async、無 threading（保持狀態機可預測）；register 順序為同 priority 的 tie-breaker。

MergedResult / DefaultResolutionPolicy 已抽至 `resolution_policy.py`（SD_05 W0 SD-C2 / Arch-C1）；
本檔自 resolution_policy re-export 以保 backward compat。
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any, Optional

from .hookspec import (
    HookContext,
    HookContractViolation,
    IHook,
    IResolutionPolicy,
    KernelPhase,
    PHASE_RESULT_CONTRACT,
)
from .resolution_policy import DefaultResolutionPolicy, MergedResult

# SD_05 W0 SD-C2：MergedResult / DefaultResolutionPolicy backward compat re-export
__all__ = ["EventBus", "MergedResult", "DefaultResolutionPolicy"]

logger = logging.getLogger("autoclaude.core.bus")


class EventBus:
    """同步 dispatcher。

    SD_Improving_05 W0 T0-4 / QA Q-M1：每次 dispatch 產生 trace_id，存於內部
    `_phase_traces`（不污染 ctx.payload，避免 SD-M5 跨 emit 取舊 trace_id）；
    連續 ≥ FAILURE_ESCALATE_THRESHOLD 次相同 phase 失敗加入 escalated_phases。
    """

    # SD_05 W0 SA-C2：QA Q-M1 escalate 門檻
    FAILURE_ESCALATE_THRESHOLD = 3

    def __init__(self, policy: Optional[IResolutionPolicy] = None):
        self._subscribers: dict[KernelPhase, list[IHook]] = defaultdict(list)
        self._policy: IResolutionPolicy = policy or DefaultResolutionPolicy()
        self._register_seq = 0
        self._phase_failure_counts: dict[KernelPhase, int] = defaultdict(int)
        self._phase_traces: dict[KernelPhase, str] = {}
        self._last_trace_id: Optional[str] = None
        self._escalated_phases: set[KernelPhase] = set()

    def register(self, hook: IHook) -> None:
        seq = self._register_seq
        self._register_seq += 1
        hook._priority = hook.priority()         # type: ignore[attr-defined]
        hook._register_idx = seq                 # type: ignore[attr-defined]
        for phase in hook.subscribed_phases():
            self._subscribers[phase].append(hook)
            logger.debug(
                "Plugin %s 訂閱 %s（priority=%d, seq=%d）",
                hook.name(), phase, hook._priority, seq,  # type: ignore[attr-defined]
            )

    def get_plugin(self, name: str) -> Optional[IHook]:
        """依 name 取得已註冊的 Plugin（供 Facade 期 backward compat 使用）。"""
        for hooks in self._subscribers.values():
            for h in hooks:
                if h.name() == name:
                    return h
        return None

    def emit(self, ctx: HookContext) -> MergedResult:
        # SD_05 W0 T0-4 / SD-M5：每次 emit 產生新 trace_id，不寫入 ctx.payload
        # SD_08 W4 / ADR-SD08-004 §2.3：trace_id 來源優先級
        #   1) ctx.payload["_trace_id"]（顯式指定，向後相容）
        #   2) utils.trace_context.get_trace_id()（ContextVar 自動注入）
        #   3) uuid.uuid4().hex[:12]（fallback 自動生成）
        # 設計原則：不污染 IBrain/IExecutor Port 簽名；trace_id 透過 ContextVar 傳輸
        explicit_trace = ctx.payload.get("_trace_id") if ctx.payload else None
        if explicit_trace:
            trace_id = explicit_trace
        else:
            # lazy import 避免 core/ → utils/ 循環風險（utils/trace_context 零依賴）
            from ..utils.trace_context import get_trace_id
            trace_id = get_trace_id() or uuid.uuid4().hex[:12]
        self._phase_traces[ctx.phase] = trace_id
        self._last_trace_id = trace_id

        results: list[Any] = []
        ordered = sorted(
            self._subscribers.get(ctx.phase, []),
            key=lambda h: (
                getattr(h, "_priority", 50),
                getattr(h, "_register_idx", 0),
            ),
        )
        dispatch_failed = False
        try:
            for hook in ordered:
                try:
                    r = hook.on_event(ctx)
                except HookContractViolation:
                    dispatch_failed = True
                    raise
                except Exception:
                    dispatch_failed = True
                    logger.exception(
                        "Plugin %s 於 phase=%s trace_id=%s 拋出例外",
                        hook.name(), ctx.phase.value, trace_id,
                    )
                    raise
                if r is None:
                    continue
                allowed = PHASE_RESULT_CONTRACT.get(ctx.phase)
                if allowed and type(r) not in allowed:
                    dispatch_failed = True
                    raise HookContractViolation(
                        f"Plugin {hook.name()} 在 {ctx.phase.value} 回傳不合法型別 {type(r).__name__}；"
                        f"允許的型別: {{{', '.join(t.__name__ for t in allowed)}}}；"
                        f"trace_id={trace_id}"
                    )
                # SD_05 W0 SD-C1：用 object.__setattr__ 繞過 frozen 限制
                try:
                    object.__setattr__(r, "_priority", getattr(hook, "_priority", 50))
                    object.__setattr__(r, "_register_idx", getattr(hook, "_register_idx", 0))
                except (AttributeError, TypeError):
                    pass
                results.append(r)
        finally:
            # SD_05 W0 SA-C2：try/finally 確保 raise 後仍正確累積失敗計數
            if dispatch_failed:
                self._phase_failure_counts[ctx.phase] += 1
                if self._phase_failure_counts[ctx.phase] >= self.FAILURE_ESCALATE_THRESHOLD:
                    self._escalated_phases.add(ctx.phase)
                    logger.error(
                        "Phase %s 已連續失敗 %d 次（threshold=%d），加入 escalated_phases；trace_id=%s",
                        ctx.phase.value, self._phase_failure_counts[ctx.phase],
                        self.FAILURE_ESCALATE_THRESHOLD, trace_id,
                    )
            else:
                self._phase_failure_counts[ctx.phase] = 0

        return self._policy.merge(ctx.phase, results)

    def get_phase_failure_count(self, phase: KernelPhase) -> int:
        """SD_05 W0 T0-4 / QA Q-M1：取得 phase 連續失敗次數。"""
        return self._phase_failure_counts.get(phase, 0)

    def is_phase_escalated(self, phase: KernelPhase) -> bool:
        """SD_05 W0 SA-C2：phase 是否已達 escalate 門檻。"""
        return phase in self._escalated_phases

    def get_phase_trace_id(self, phase: KernelPhase) -> Optional[str]:
        """SD_05 W0 SD-M5：取得指定 phase 的最近 trace_id。"""
        return self._phase_traces.get(phase)

    def last_trace_id(self) -> Optional[str]:
        """SD_05 W0 T0-4：最近一次 dispatch 的 trace_id（debug 用）。"""
        return self._last_trace_id
