"""PreRunValidatorPlugin — 取代 PlaybookRunner 內 PreRunValidator().validate_step(...) 的呼叫。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 9 列（priority=5）
  - SD_Improving_02.md v1.1 §2.5 W5 #3（低測試耦合度）

訂閱 phase：
  - PRE_RUN     → Playbook 啟動時的整體預驗證（目前不阻擋，預留）
  - PRE_ATTEMPT → 每次 attempt 前檢查 evaluator_command 合法性
                   發現 block 級問題 → 回傳 VetoResult 阻擋當次 attempt
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, VetoResult
from ..execution.pre_run_validator import PreRunValidator


class PreRunValidatorPlugin:
    """Playbook / 步驟啟動前的靜態驗證 Plugin。"""

    PRIORITY = 5  # 系統級 veto（最早執行）

    def __init__(self, validator: Optional[PreRunValidator] = None):
        self._validator = validator or PreRunValidator()

    def name(self) -> str:
        return "pre_run_validator"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_RUN, KernelPhase.PRE_ATTEMPT]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        # PRE_RUN：目前僅作為觀察者，未來可掃描整個 playbook
        if ctx.phase == KernelPhase.PRE_RUN:
            return None

        # PRE_ATTEMPT：對當前 task 的 evaluator_command 做靜態驗證
        if ctx.task is None:
            return None

        # 僅在 attempt=0（首次嘗試）時驗證；後續重試已修正則不再阻擋
        if ctx.attempt is not None and ctx.attempt > 0:
            return None

        issues = self._validator.validate_step(
            ctx.task.evaluator_command,
            ctx.task.prompt,
        )
        if not issues:
            return None

        block_issues = [i for i in issues if i.severity == "block"]
        if not block_issues:
            return None  # 只有 warn 級別 → 不阻擋

        # block 級問題 → veto
        first = block_issues[0]
        return VetoResult(
            contributor=self.name(),
            reason=(
                f"PreRunValidator block: {first.category} - {first.message}"
                + (f"\nstrategy_hint: {first.strategy_hint}" if first.strategy_hint else "")
            ),
        )
