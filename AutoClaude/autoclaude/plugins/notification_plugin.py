"""NotificationPlugin — 取代 PlaybookRunner._notify 散在 7 處的呼叫。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 7 列（priority=50）
  - SD_Improving_02.md v1.1 §2.5 W5 #1（低測試耦合度）

訂閱 phase：
  - ON_ESCALATION         → notify_escalation（含 escalation dump 路徑）
  - ON_EVOLUTION          → notify「自動演化」訊息
  - POST_RUN              → notify「Playbook 完成」訊息
  - ON_AUTO_RESUME_WAKE   → notify「自動恢復」訊息（W5 / M-9 / SA-M3：避免死碼）
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, IHook, KernelPhase, ScheduleResumeResult
from ..utils.notifier import notify, notify_escalation


class NotificationPlugin:
    """事件驅動的桌面通知 Plugin。"""

    PRIORITY = 50

    def __init__(self, enabled: bool = True, app_config: Optional[Any] = None):
        self._enabled = enabled
        self._cfg = app_config  # 可選：notify_escalation 需要 AppConfig

    def name(self) -> str:
        return "notification"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION,
            KernelPhase.POST_RUN,
            KernelPhase.ON_AUTO_RESUME_WAKE,  # W5 / M-9 / SA-M3
        ]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if not self._enabled:
            return None

        if ctx.phase == KernelPhase.ON_ESCALATION:
            self._on_escalation(ctx)
        elif ctx.phase == KernelPhase.ON_EVOLUTION:
            self._on_evolution(ctx)
        elif ctx.phase == KernelPhase.POST_RUN:
            self._on_post_run(ctx)
        elif ctx.phase == KernelPhase.ON_AUTO_RESUME_WAKE:
            return self._on_auto_resume_wake(ctx)
        return None  # 純觀察者，不回控制 Kernel

    # ──────────────────────────────────────────────
    # 內部 handler
    # ──────────────────────────────────────────────
    def _on_escalation(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        title = payload.get("title", "AutoClaude — ESCALATION")
        message = payload.get("message", f"步驟 {ctx.task.step_id if ctx.task else 'N/A'} 已升級")
        dump_path = payload.get("dump_path", "")
        if dump_path and self._cfg is not None:
            try:
                notify_escalation(title, message, dump_path, self._cfg)
            except (TypeError, AttributeError):
                # 簽章不符或缺 cfg → fallback 至一般 notify
                notify(title, message, enabled=self._enabled)
        else:
            notify(title, message, enabled=self._enabled)

    def _on_evolution(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        evo_count = payload.get("evolution_count", 1)
        path = payload.get("evolved_playbook_path", "")
        title = f"AutoClaude — 自動演化（第 {evo_count} 次）"
        message = f"演化版: {path}" if path else "Playbook 已自動演化"
        notify(title, message, enabled=self._enabled)

    def _on_post_run(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        success = payload.get("success", True)
        title = "AutoClaude — 完成" if success else "AutoClaude — 失敗"
        message = payload.get(
            "message",
            f"Playbook {ctx.playbook.project} 已結束",
        )
        notify(title, message, enabled=self._enabled)

    def _on_auto_resume_wake(self, ctx: HookContext) -> ScheduleResumeResult:
        """W5 / M-9 / SA-M3：訂閱 ON_AUTO_RESUME_WAKE 並回傳 ScheduleResumeResult。

        kind ∈ {halt, evolution, checkpoint_resume}。
        回傳 ScheduleResumeResult 符合 PHASE_RESULT_CONTRACT；
        無 plugin 訂閱即死碼的 SA-M3 風險已消除。
        """
        payload = ctx.payload or {}
        kind = payload.get("kind", "unknown")
        scheduled_at = payload.get("scheduled_at") or ""
        wait_seconds = payload.get("wait_seconds", 0.0)
        kind_zh = {
            "halt": "Token 耗盡恢復",
            "evolution": "Playbook 演化重啟",
            "checkpoint_resume": "從 checkpoint 喚醒",
        }.get(kind, kind)
        title = f"AutoClaude — 自動恢復（{kind_zh}）"
        if wait_seconds > 0:
            message = f"等待 {wait_seconds:.0f} 秒後繼續"
        else:
            message = "立即繼續執行"
        notify(title, message, enabled=self._enabled)
        return ScheduleResumeResult(
            contributor="notification", scheduled_at=scheduled_at,
        )
