"""OrchestrationCoordinator — Layer 1.5 協調層（SD_Improving_06 W1 T1-3）。

對應：
  - ADR-SD06-001 §2 雙層架構圖（Layer 1.5 in / Layer 2 out）
  - ADR-SD06-001 §6.1 6 phase 序保證（內部狀態機強制；違反 raise PhaseOrderViolation）
  - ADR-SD06-001 §6.4 send_interrupt 走 EventBus（ON_INTERRUPT_REQUEST event）
  - PM #8（W2-T2-15 預埋）MAX_ACTIVE_RUNS_PER_GOAL=5 guard

職責：
  BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC

邊界規則（ADR R1~R5）：不可呼叫 AutoResumeService；不可訂閱 Layer 2 phase；
Brain ↔ Executor 互通必須走 EventBus。

LOC 預算：≤ 250 行
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from ..event_bus import EventBus
from ..hookspec import HookContext, KernelPhase
from ..ports.brain import BrainCapabilities, IBrain
from ..ports.executor import ExecutionEvent, ExecutionOutput, IExecutor


# ──────────────────────────────────────────────────────────────
# 例外與資料型別
# ──────────────────────────────────────────────────────────────
class PhaseOrderViolation(Exception):
    """6 phase 序錯誤（ADR §6.1 + §7.4 QA 條件 1）。"""


class MaxActiveRunsExceeded(Exception):
    """MAX_ACTIVE_RUNS_PER_GOAL guard 觸發（PM #8）。"""


@dataclass(frozen=True)
class CoordinatorResult:
    """單一 step 協調完成後的彙整。"""
    output: ExecutionOutput
    capabilities: BrainCapabilities
    event_count: int
    interrupted: bool = False
    veto_reason: Optional[str] = None
    extra: dict = field(default_factory=dict)


# 6 phase 序（不可顛倒；ADR §6.1）
_PHASE_ORDER: tuple[KernelPhase, ...] = (
    KernelPhase.BEFORE_DECIDE,
    KernelPhase.DECIDE,
    KernelPhase.BEFORE_EXEC,
    KernelPhase.EXEC,
    KernelPhase.ON_EVENT,
    KernelPhase.AFTER_EXEC,
)


# ──────────────────────────────────────────────────────────────
# OrchestrationCoordinator
# ──────────────────────────────────────────────────────────────
class OrchestrationCoordinator:
    """Layer 1.5 — 單一 step 內 Brain / Executor 協調。

    一個實例綁定一個 EventBus + Brain + Executor；每次 run_step 跑一輪 6 phase。
    """

    _DEFAULT_MAX_ACTIVE_RUNS = 5  # PM #8

    def __init__(
        self,
        *,
        bus: EventBus,
        brain: IBrain,
        executor: IExecutor,
        max_active_runs_per_goal: Optional[int] = None,
    ):
        self._bus = bus
        self._brain = brain
        self._executor = executor
        # PM #8 解析優先級：env > 建構子 > 預設
        env_val = os.environ.get("MAX_ACTIVE_RUNS_PER_GOAL")
        if env_val and env_val.isdigit():
            self._max_active_runs = int(env_val)
        elif max_active_runs_per_goal is not None:
            self._max_active_runs = max_active_runs_per_goal
        else:
            self._max_active_runs = self._DEFAULT_MAX_ACTIVE_RUNS
        self._current_phase_idx: int = -1
        self._captured_events: list[ExecutionEvent] = []

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────
    def reset(self) -> None:
        """重置狀態機（每次 run_step 開始時呼叫）。"""
        self._current_phase_idx = -1
        self._captured_events = []

    @property
    def max_active_runs_per_goal(self) -> int:
        return self._max_active_runs

    def run_step(
        self,
        *,
        playbook,
        task,
        step_idx: int,
        attempt: int = 0,
        active_runs_for_goal: int = 0,
    ) -> CoordinatorResult:
        """執行單一 step 的 6 phase 協調序。

        Raises:
            MaxActiveRunsExceeded：active_runs_for_goal >= max_active_runs（PM #8）
            PhaseOrderViolation：內部 bug；外部 caller 不應觸發
        """
        self.reset()

        # Phase 1：BEFORE_DECIDE — guard + 讀 capabilities
        self._enter_phase(KernelPhase.BEFORE_DECIDE)
        if active_runs_for_goal >= self._max_active_runs:
            raise MaxActiveRunsExceeded(
                f"active_runs_for_goal={active_runs_for_goal} >= "
                f"MAX_ACTIVE_RUNS_PER_GOAL={self._max_active_runs}"
            )
        capabilities = self._brain.capabilities()
        self._dispatch_phase(KernelPhase.BEFORE_DECIDE, playbook, task, step_idx, attempt,
                             {"capabilities_model_id": capabilities.model_id})

        # Phase 2：DECIDE — W1 預留 phase；Brain 呼叫由 W2+ 接管
        self._enter_phase(KernelPhase.DECIDE)
        self._dispatch_phase(KernelPhase.DECIDE, playbook, task, step_idx, attempt, {})

        # Phase 3：BEFORE_EXEC — Plugin Veto 機會
        self._enter_phase(KernelPhase.BEFORE_EXEC)
        merged = self._dispatch_phase(KernelPhase.BEFORE_EXEC, playbook, task,
                                      step_idx, attempt, {})
        veto_reason = self._extract_veto_reason(merged)
        if veto_reason is not None:
            self._current_phase_idx = _PHASE_ORDER.index(KernelPhase.AFTER_EXEC)
            self._dispatch_phase(KernelPhase.AFTER_EXEC, playbook, task, step_idx,
                                 attempt, {"vetoed": True, "reason": veto_reason})
            return CoordinatorResult(
                output=ExecutionOutput(text="", exit_code=0, completed=False),
                capabilities=capabilities,
                event_count=0,
                interrupted=False,
                veto_reason=veto_reason,
            )

        # Phase 4：EXEC — Executor 主導；on_event 自封 callback
        self._enter_phase(KernelPhase.EXEC)
        output = self._executor.execute(
            task.prompt,
            maintain_context=task.maintain_context,
            label=task.step_id,
            on_event=self._on_executor_event,
        )

        # Phase 5：ON_EVENT — 彙整廣播（W1 一次性；W2+ 改逐筆 emit）
        self._enter_phase(KernelPhase.ON_EVENT)
        self._dispatch_phase(KernelPhase.ON_EVENT, playbook, task, step_idx, attempt,
                             {"event_count": len(self._captured_events)})

        # Phase 6：AFTER_EXEC — 終態廣播
        self._enter_phase(KernelPhase.AFTER_EXEC)
        self._dispatch_phase(KernelPhase.AFTER_EXEC, playbook, task, step_idx, attempt,
                             {"completed": output.completed, "exit_code": output.exit_code})

        return CoordinatorResult(
            output=output,
            capabilities=capabilities,
            event_count=len(self._captured_events),
            interrupted=not output.completed,
        )

    def request_interrupt(self, reason: str = "") -> bool:
        """走 EventBus 發送 ON_INTERRUPT_REQUEST（ADR §6.4）+ 直接呼叫 executor（Phase 1 雙保險）。"""
        return self._executor.send_interrupt(reason)

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────
    def _enter_phase(self, phase: KernelPhase) -> None:
        """進入下一 phase；違反序則 raise PhaseOrderViolation。"""
        expected_idx = self._current_phase_idx + 1
        if expected_idx >= len(_PHASE_ORDER):
            raise PhaseOrderViolation(
                f"嘗試進入 {phase.value}，但 6 phase 序已完成；請先 reset()"
            )
        expected_phase = _PHASE_ORDER[expected_idx]
        if phase is not expected_phase:
            raise PhaseOrderViolation(
                f"phase 序違反：預期 {expected_phase.value}，實際 {phase.value}"
            )
        self._current_phase_idx = expected_idx

    def _dispatch_phase(
        self,
        phase: KernelPhase,
        playbook,
        task,
        step_idx: int,
        attempt: int,
        payload: dict,
    ) -> Any:
        ctx = HookContext(
            phase=phase,
            playbook=playbook,
            task=task,
            step_idx=step_idx,
            attempt=attempt,
            payload=payload,
        )
        return self._bus.emit(ctx)

    def _on_executor_event(self, event: ExecutionEvent) -> None:
        """Executor on_event callback（ADR R3：不可直接呼叫 Brain）。"""
        self._captured_events.append(event)

    @staticmethod
    def _extract_veto_reason(merged: Any) -> Optional[str]:
        """從 MergedResult 抽取 veto 原因（merged.veto: bool + veto_reasons: list[str]）。"""
        if merged is None or not getattr(merged, "veto", False):
            return None
        reasons = getattr(merged, "veto_reasons", []) or []
        return "; ".join(reasons) if reasons else "vetoed"
