"""ConvergencePlugin — 取代 PlaybookRunner 內 monitor.evaluate(tracker) + ESCALATE 判定。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 4 列（priority=65）
  - SD_Improving_02.md v1.1 §2.5 W9 #10（高風險）

訂閱 phase：
  - POST_ATTEMPT  → 檢查 ctx.payload 中的 ConvergenceReport.recommendation
                    若為 "escalate" → 回傳 ResourceRequest(request_escalation=True)

設計原則：
  - 純策略決定（escalate / change_strategy / continue）
  - ConvergenceMonitor.evaluate(tracker) 仍由呼叫端執行，Plugin 從 payload 接收結果
  - Phase 4 Facade 切換時 Kernel 將內建 evaluate 呼叫
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, ResourceRequest
from ..execution.convergence_monitor import ConvergenceMonitor


class ConvergencePlugin:
    """收斂評估 Plugin（8 優先級判定 + ESCALATE 決策）。"""

    PRIORITY = 65

    def __init__(self, monitor: Optional[ConvergenceMonitor] = None):
        self._monitor = monitor or ConvergenceMonitor()

    def name(self) -> str:
        return "convergence"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_ATTEMPT]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        payload = ctx.payload or {}

        # 模式 A：呼叫端已執行 evaluate，僅注入 recommendation 字串
        recommendation = payload.get("convergence_recommendation")
        reasoning = payload.get("convergence_reasoning", "")

        # 模式 B：呼叫端傳入 FailureTracker，由 Plugin 執行評估
        if recommendation is None:
            tracker = payload.get("failure_tracker")
            if tracker is not None:
                report = self._monitor.evaluate(tracker)
                recommendation = report.recommendation
                reasoning = report.reasoning

        # 模式 C：Kernel 傳入 failure_history list of dicts，由 Plugin 重建 tracker
        if recommendation is None:
            failure_history = payload.get("failure_history")
            if failure_history is not None:
                from ..execution.failure_tracker import FailureTracker
                step_id = payload.get("step_id", "unknown")
                tracker = FailureTracker(step_id)
                for rec in failure_history:
                    tracker.record(
                        attempt=rec.get("attempt", 0),
                        failure_reason=rec.get("failure_reason", ""),
                        eval_output=rec.get("eval_output", ""),
                        exit_code=rec.get("exit_code", 0),
                    )
                report = self._monitor.evaluate(tracker)
                recommendation = report.recommendation
                reasoning = report.reasoning

        if recommendation != "escalate":
            return None

        return ResourceRequest(
            contributor=self.name(),
            request_escalation=True,
            reason=reasoning or "ConvergenceMonitor recommended escalation",
        )

    # ──────────────────────────────────────────────
    # 公開 API
    # ──────────────────────────────────────────────
    def evaluate(self, tracker) -> "ConvergenceReport":  # type: ignore[name-defined]
        """供 Kernel / 呼叫端直接執行收斂評估。"""
        return self._monitor.evaluate(tracker)
