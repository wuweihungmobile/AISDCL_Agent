"""CrossStepValidatorPlugin — 取代 PlaybookRunner 內 CrossStepStateValidator 的呼叫。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 10 列（priority=15）
  - SD_Improving_02.md v1.1 §2.5 W6 #4

訂閱 phase：
  - PRE_STEP    → 偵測 git 跨步驟污染，將警告快取至 self._cached_warning
  - PRE_ATTEMPT → 若 attempt=0 且有 cached warning，注入 PromptInjectionResult

注意：
  - PRE_STEP 的 PHASE_RESULT_CONTRACT 僅允許 VetoResult；本 Plugin 不 veto，僅快取警告
  - 警告改在 PRE_ATTEMPT 注入 prompt prefix（PHASE_RESULT_CONTRACT 允許）
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from ..execution.cross_step_validator import CrossStepStateValidator


class CrossStepValidatorPlugin:
    """跨步驟 git 狀態污染偵測 Plugin。"""

    PRIORITY = 15

    def __init__(
        self,
        validator: Optional[CrossStepStateValidator] = None,
        working_dir: str = ".",
        modified_threshold: int = 5,
    ):
        self._validator = validator or CrossStepStateValidator()
        self._working_dir = working_dir
        self._modified_threshold = modified_threshold
        self._cached_warning: Optional[str] = None
        self._cached_for_step_idx: Optional[int] = None

    def name(self) -> str:
        return "cross_step_validator"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_STEP, KernelPhase.PRE_ATTEMPT]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if ctx.phase == KernelPhase.PRE_STEP:
            self._on_pre_step(ctx)
            return None  # PRE_STEP 不回傳（避免 VetoResult-only contract 問題）

        if ctx.phase == KernelPhase.PRE_ATTEMPT:
            return self._on_pre_attempt(ctx)
        return None

    def _on_pre_step(self, ctx: HookContext) -> None:
        if ctx.task is None or ctx.step_idx is None:
            self._cached_warning = None
            return

        prev_step = None
        if ctx.step_idx > 0:
            prev_step = ctx.playbook.tasks[ctx.step_idx - 1]

        warning = self._validator.validate_before_step(
            current_step=ctx.task,
            prev_step=prev_step,
            working_dir=self._working_dir,
            modified_threshold=self._modified_threshold,
        )
        self._cached_warning = warning
        self._cached_for_step_idx = ctx.step_idx

    def _on_pre_attempt(self, ctx: HookContext) -> Optional[PromptInjectionResult]:
        # 僅在 attempt=0 且 step_idx 對應 cache 時注入
        if ctx.attempt is not None and ctx.attempt > 0:
            return None
        if self._cached_warning is None:
            return None
        if self._cached_for_step_idx is not None and ctx.step_idx != self._cached_for_step_idx:
            return None

        warning = self._cached_warning
        # 注入後清除 cache（避免後續步驟誤注入）
        self._cached_warning = None
        return PromptInjectionResult(
            contributor=self.name(),
            prefix=f"\n{warning}\n\n",
            position="top",
        )
