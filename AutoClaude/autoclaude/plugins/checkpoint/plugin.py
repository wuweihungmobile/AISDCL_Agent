"""CheckpointPlugin 主類（SD_Improving_05 W3-2 拆 package 後 facade）。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 2 列（priority=90）
  - SD_Improving_02.md v1.1 §2.5 W8 #9（高風險）
  - W4-T17 / M-11：與 GotoCounterPlugin 解耦，改用 EventBus 廣播
  - SD_Improving_05 W3：吸收 3 條中斷路徑（TOKEN_HALT / ESC+F12 / ESCALATION dump）
    + 演化後 checkpoint；4 個公開方法；新增訂閱 ON_PERSISTENCE_REQUEST /
    ON_ESCALATION_DUMP_REQUEST。

訂閱 phase（W4-T17 5 個 + W3 2 個 = 7 個）：
  - PRE_RUN                    → 載入 checkpoint，廣播 ON_CHECKPOINT_RESTORE
  - POST_STEP                  → 暫不處理（保留以支援後續 token_halt resume）
  - ON_INTERRUPT               → ESC+F12 中斷 → 儲存 interrupt checkpoint
  - ON_TOKEN_USAGE             → request_halt=True → 儲存 token_halt checkpoint
  - ON_EVOLUTION               → 演化後 → 儲存 evolution_resume checkpoint
  - ON_PERSISTENCE_REQUEST     → W3 新增：通用持久化請求入口
  - ON_ESCALATION_DUMP_REQUEST → W3 新增：ESCALATION dump 持久化請求
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Callable, Optional

from ...core.event_bus import EventBus
from ...core.hookspec import HookContext, IHookResult, KernelPhase
from ...utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint

from ._evolution import save_evolution_resume_checkpoint_impl
from ._interrupt import save_interrupt_checkpoint_impl
from ._token_halt import handle_token_halt_impl
from ._escalation import save_escalation_dump_impl
from ._phase_handlers import (
    on_pre_run,
    save_interrupt,
    save_token_halt,
    save_evolution,
    on_persistence_request,
    on_escalation_dump_request,
)

logger = logging.getLogger("autoclaude.plugins.checkpoint")


class CheckpointPlugin:
    """跨 Session 持久化 Plugin（Gap-007-A / 041 / 042 / 048 + SD_05 W3 4 公開方法）。"""

    PRIORITY = 90

    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        checkpoint_dir: str = "checkpoints",
        event_bus: Optional[EventBus] = None,
        **deprecated_kwargs: Any,
    ):
        # SD_05 W6 三方審查 SD-M2 修：保留 deprecated alias 過渡期，避免下游 hard break。
        # SD_06 W0 將完全拔除此 deprecation 期。
        if "goto_counter_plugin" in deprecated_kwargs:
            warnings.warn(
                "CheckpointPlugin(goto_counter_plugin=...) 已於 SD_05 W6 移除，"
                "請改用 EventBus 廣播路徑：bus.register(GotoCounterPlugin()); "
                "CheckpointPlugin(event_bus=bus)。"
                "詳見 docs/08_deployment/SD05_Migration_Guide.md §3.1。",
                DeprecationWarning,
                stacklevel=2,
            )
            deprecated_kwargs.pop("goto_counter_plugin")
        if deprecated_kwargs:
            raise TypeError(
                f"CheckpointPlugin 收到未知 keyword argument(s): "
                f"{list(deprecated_kwargs.keys())}"
            )
        self._mgr = checkpoint_manager or CheckpointManager(checkpoint_dir)
        self._bus: Optional[EventBus] = event_bus
        # SD_05 W3 Arch-C1 / SD-C1：記錄最近一次 save_escalation_dump 真實路徑，
        # 供 on_escalation_dump_request 回傳 EscalationDumpedResult.dump_path 使用。
        self._last_dump_path: str = ""

    def attach_bus(self, bus: EventBus) -> None:
        self._bus = bus

    def name(self) -> str:
        return "checkpoint"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.PRE_RUN,
            KernelPhase.POST_STEP,
            KernelPhase.ON_INTERRUPT,
            KernelPhase.ON_TOKEN_USAGE,
            KernelPhase.ON_EVOLUTION,
            # SD_05 W3：新增 2 phase
            KernelPhase.ON_PERSISTENCE_REQUEST,
            KernelPhase.ON_ESCALATION_DUMP_REQUEST,
        ]

    def on_event(self, ctx: HookContext) -> Optional[IHookResult]:
        phase = ctx.phase
        if phase == KernelPhase.PRE_RUN:
            on_pre_run(self, ctx)
            return None
        if phase == KernelPhase.ON_INTERRUPT:
            return save_interrupt(self, ctx)
        if phase == KernelPhase.ON_TOKEN_USAGE:
            return save_token_halt(self, ctx)
        if phase == KernelPhase.ON_EVOLUTION:
            return save_evolution(self, ctx)
        if phase == KernelPhase.ON_PERSISTENCE_REQUEST:
            return on_persistence_request(self, ctx)
        if phase == KernelPhase.ON_ESCALATION_DUMP_REQUEST:
            return on_escalation_dump_request(self, ctx)
        return None

    # ──────────────────────────────────────────────
    # 私有 method alias（backward compat for 既有 30+ 測試 patch）
    # SD_05 W3-2 拆 package：邏輯下沉 _phase_handlers.py；W6 評估刪除
    # ──────────────────────────────────────────────
    def _on_pre_run(self, ctx: HookContext) -> None:
        on_pre_run(self, ctx)

    def _save_interrupt(self, ctx: HookContext):
        return save_interrupt(self, ctx)

    def _save_token_halt(self, ctx: HookContext):
        return save_token_halt(self, ctx)

    def _save_evolution(self, ctx: HookContext):
        return save_evolution(self, ctx)

    def _build_checkpoint(self, ctx: HookContext, payload: dict):
        from ._builder import build_checkpoint_from_ctx
        return build_checkpoint_from_ctx(self, ctx, payload)

    # ──────────────────────────────────────────────
    # 公開 API（W4-T17 既有 3 + W3 新增 4 = 7 個）
    # ──────────────────────────────────────────────
    def load_checkpoint(self, playbook_path: str) -> Optional[PlaybookCheckpoint]:
        return self._mgr.load(playbook_path)

    def clear_checkpoint(self, playbook_path: str) -> None:
        self._mgr.clear(playbook_path)

    def save_checkpoint(
        self, playbook_path: str, checkpoint: PlaybookCheckpoint,
    ) -> None:
        self._mgr.save(checkpoint, playbook_path)

    # W3-1a：演化後 checkpoint
    def save_evolution_resume_checkpoint(
        self,
        evolved_path: str,
        playbook,
        step_log: list,
        completed_step_ids,
        step_evolution_counter: Optional[dict] = None,
        alert_ladder: Optional[dict] = None,
    ) -> bool:
        return save_evolution_resume_checkpoint_impl(
            self, evolved_path, playbook, step_log,
            completed_step_ids, step_evolution_counter, alert_ladder,
        )

    # W3-1b：TOKEN_HALT checkpoint（純 plugin，PlaybookResult 由呼叫端組裝）
    def handle_token_halt(
        self,
        playbook,
        playbook_path: str,
        task,
        step_idx: int,
        peak_token_pct: float,
        step_log: list,
        total: int,
        halt_threshold_pct: float,
        resume_delay_minutes: int,
        tracker=None,
        attempt: int = 0,
        goto_counter: Optional[dict] = None,
        inject_before_counter: Optional[dict] = None,
        skip_to_counter: Optional[dict] = None,
        completed_step_ids: Optional[set] = None,
        step_evolution_counter: Optional[dict] = None,
        alert_ladder: Optional[dict] = None,
        notify_callback: Optional[Callable[[str, str], None]] = None,
        token_logger_callback: Optional[Callable[..., None]] = None,
    ) -> PlaybookCheckpoint:
        return handle_token_halt_impl(
            self, playbook, playbook_path, task, step_idx, peak_token_pct,
            step_log, total, halt_threshold_pct, resume_delay_minutes,
            tracker, attempt, goto_counter, inject_before_counter,
            skip_to_counter, completed_step_ids, step_evolution_counter,
            alert_ladder, notify_callback, token_logger_callback,
        )

    # W3-1c：ESC+F12 中斷 checkpoint
    def save_interrupt_checkpoint(
        self,
        playbook,
        playbook_path: str,
        task,
        step_idx: int,
        step_log: list,
        total: int,
        tracker=None,
        attempt: int = 0,
        goto_counter: Optional[dict] = None,
        inject_before_counter: Optional[dict] = None,
        skip_to_counter: Optional[dict] = None,
        completed_step_ids: Optional[list] = None,
        step_evolution_counter: Optional[dict] = None,
        alert_ladder: Optional[dict] = None,
    ) -> None:
        return save_interrupt_checkpoint_impl(
            self, playbook, playbook_path, task, step_idx, step_log, total,
            tracker, attempt, goto_counter, inject_before_counter,
            skip_to_counter, completed_step_ids, step_evolution_counter,
            alert_ladder,
        )

    # W3-1d：ESCALATION dump 持久化
    def save_escalation_dump(
        self,
        tracker,
        task,
        playbook_path: str,
        final_eval_output: str,
        checkpoint_dir: str,
        log_dir: str,
        human_hint: str = "",
        notify_callback: Optional[Callable[..., None]] = None,
        topology_dashboard: str = "",
    ):
        return save_escalation_dump_impl(
            self, tracker, task, playbook_path, final_eval_output,
            checkpoint_dir, log_dir, human_hint, notify_callback,
            topology_dashboard=topology_dashboard,
        )
