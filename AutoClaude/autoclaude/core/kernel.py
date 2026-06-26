"""PlaybookKernel — 純粹的 DAG 狀態機（SD_Improving_01.md v1.1 §3.4.3）。

設計原則：
  - 行數 ≤ 250（行數預算 CI 強制，01 v1.1 §3.13.1）
  - 任何業務邏輯變化點都透過 bus.emit() 委外
"""
from __future__ import annotations

import logging

from ..models.playbook import Playbook, PlaybookTask
from ..models.step_mutation import StepMutationType
from ._token_observer import TokenObserver
from .event_bus import EventBus
from .hookspec import HookContext, KernelPhase
from .kernel_state import KernelResult, StepAction, StepOutcome
from .ports.brain import IBrain
from .ports.evaluator import IEvaluator
from .ports.executor import IExecutor
from .ports.observability import IObservabilityPort, NullObservability
from .services.mutation.service import MutationApplyService

logger = logging.getLogger("autoclaude.core.kernel")


class PlaybookKernel:
    """純粹的 DAG 狀態機。不持有任何業務邏輯。"""

    def __init__(
        self,
        executor: IExecutor,
        evaluator: IEvaluator,
        bus: EventBus | None = None,
        brain: IBrain | None = None,
        mutation_service: MutationApplyService | None = None,
        observability: IObservabilityPort | None = None,
    ):
        self._exec = executor
        self._eval = evaluator
        self._bus = bus or EventBus()
        self._brain = brain
        self._mutation_service = mutation_service or MutationApplyService()
        # SD_08 W4 / ADR-SD08-004 §2.1：IObservabilityPort 建構式注入
        # 未注入時 fallback NullObservability，避免 None check 散落
        self._observability: IObservabilityPort = observability or NullObservability()

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def observability(self) -> IObservabilityPort:
        """SD_08 W4：對外暴露 IObservabilityPort（供 Coordinator / AutoResume 等讀取）。"""
        return self._observability

    @property
    def mutation_service(self) -> MutationApplyService:
        return self._mutation_service

    @property
    def evaluator(self) -> IEvaluator:
        """M1 shim 用：供 PlaybookRunner._evaluate 委派。"""
        return self._eval

    def execute_once(self, prompt: str) -> object:
        """供 AutoResumeService 執行單次 prompt（context_negotiation 等）。"""
        return self._exec.execute(prompt, maintain_context=False, timeout=60, label="cn")

    # ── 公開進入點 ──────────────────────────────────────────────────────────────
    def run(self, playbook: Playbook, start_idx: int = 0) -> KernelResult:
        """執行 Playbook 完整生命週期。

        Args:
            playbook: 待執行 Playbook
            start_idx: 起始步驟索引（W2-T9 / SD_04）。預設 0 維持向後相容；
                       AutoResumeService 從 checkpoint 解析後傳入以實現續跑。
                       值會被夾在 [0, len(tasks)] 區間內，避免越界。

        邊界對稱性（SD_04 W2 三方審查 Arch-W2-Min-2 補述）：
            - `start_idx < 0`：截至 0（從頭開始）
            - `0 <= start_idx < len(tasks)`：正常從該步驟開始
            - `start_idx >= len(playbook.tasks)`：截至 len，while 迴圈立即結束
              → 直接進入 POST_RUN，回傳 success=True（視為已完整恢復的 playbook，
              對應「checkpoint 顯示全部步驟已完成」的場景，例如 evolved playbook
              全部完成後 resume）
        """
        merged = self._bus.emit(HookContext(phase=KernelPhase.PRE_RUN, playbook=playbook))
        if merged.veto:
            return KernelResult.vetoed(len(playbook.tasks), merged.veto_reasons)

        # start_idx 邊界保護：負數截至 0，超過總步數截至 len（直接 POST_RUN）
        step_idx = max(0, min(start_idx, len(playbook.tasks)))
        # F-C2 resume 口徑（Phase 1 複驗 P1-1）：start_idx 語意 = 前面步驟皆已完成
        # （checkpoint resume），POST_RUN 進度摘要須含這些步驟，否則 resume run
        # 的 progress_pct 系統性低估（10 步於 idx 5 resume 完成 → 誤記 50%）
        resume_prior_ids = [t.step_id for t in playbook.tasks[:step_idx]]
        step_log: list[str] = []
        completed_ids: list[str] = []
        contributors: list[str] = []

        while step_idx < len(playbook.tasks):
            outcome = self._run_step(playbook, step_idx, step_log, completed_ids, contributors)

            if outcome.action == StepAction.ADVANCE:
                step_idx += 1
            elif outcome.action == StepAction.GOTO and outcome.goto_idx is not None:
                step_idx = max(0, min(outcome.goto_idx, len(playbook.tasks) - 1))
            elif outcome.action == StepAction.ESCALATE:
                return KernelResult.escalated_(
                    completed_steps=len(completed_ids),
                    total_steps=len(playbook.tasks),
                    step_log=step_log,
                    completed_step_ids=completed_ids,
                    reason=outcome.failure_reason or "escalated",
                )
            elif outcome.action == StepAction.HALT:
                return KernelResult.halted_(
                    completed_steps=len(completed_ids),
                    total_steps=len(playbook.tasks),
                    step_log=step_log,
                    completed_step_ids=completed_ids,
                    halt_step_idx=step_idx,
                    peak_token_pct=outcome.peak_token_pct,
                )

        # F-C2：POST_RUN 附帶 run 結果摘要（GoalProgressPlugin 記錄 L4 進度 ledger）；
        # completed_step_ids = resume 前已完成（start_idx 語意）+ 本次完成，
        # KernelResult 維持「本次 run」口徑不變（兩者語意刻意不同）
        post = self._bus.emit(HookContext(
            phase=KernelPhase.POST_RUN, playbook=playbook,
            payload={
                "completed_step_ids": resume_prior_ids + list(completed_ids),
                "total_steps": len(playbook.tasks),
            },
        ))
        contributors.extend(post.contributors)

        return KernelResult.success_(
            completed_steps=len(completed_ids),
            total_steps=len(playbook.tasks),
            step_log=step_log,
            completed_step_ids=completed_ids,
            contributors=contributors,
        )

    # ── 內部：單一步驟 attempt loop ─────────────────────────────────────────────
    def _run_step(self, playbook, step_idx, step_log, completed_ids, contributors) -> StepOutcome:
        task = playbook.tasks[step_idx]

        pre_step = self._bus.emit(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=playbook, task=task, step_idx=step_idx,
        ))
        if pre_step.veto:
            return StepOutcome(
                action=StepAction.ESCALATE, failure_reason="; ".join(pre_step.veto_reasons),
            )

        max_retries = (
            task.max_retries if task.max_retries is not None
            else playbook.global_invariants.max_retries_per_step
        )
        attempt = 0
        last_failure_reason = ""
        failure_history: list = []

        while attempt <= max_retries:
            pre_attempt = self._bus.emit(HookContext(
                phase=KernelPhase.PRE_ATTEMPT, playbook=playbook, task=task,
                step_idx=step_idx, attempt=attempt,
            ))
            if pre_attempt.veto:
                return StepOutcome(
                    action=StepAction.ESCALATE,
                    failure_reason="; ".join(pre_attempt.veto_reasons),
                    attempts_used=attempt,
                )

            full_prompt = (pre_attempt.accumulated_prefix or "") + task.prompt
            timeout = getattr(playbook.global_invariants, "step_timeout_seconds", 600)
            # improving_78 W-78-1（DEF-78-001）：token 觀測器作為 on_event callback，
            # 蒐集 executor 真實 token% 峰值（SDK TOKEN_PCT / PTY PARTIAL_OUTPUT）。
            observer = TokenObserver()
            output = self._exec.execute(
                full_prompt, maintain_context=task.maintain_context,
                timeout=timeout, label=task.step_id, on_event=observer,
            )
            # improving_78 W-78-1（DEF-78-001）：production token-guard halt 接線。
            # 僅在真有 token 訊號（peak>0）時 emit ON_TOKEN_USAGE → token_guard 決策；
            # 無訊號（dry-run / 既有 fake）→ 不 emit、行為與接線前完全一致（零退化）。
            halt_outcome = self._consult_token_guard(playbook, task, step_idx, attempt,
                                                     max_retries, observer.peak_pct)
            if halt_outcome is not None:
                return halt_outcome
            failure_reason, _eval_out, _exit = self._eval.evaluate(task, output.text)

            if failure_reason is None:
                completed_ids.append(task.step_id)
                step_log.append(f"[{task.step_id}] {task.name} ✓ (attempt {attempt + 1})")
                self._bus.emit(HookContext(phase=KernelPhase.ON_SUCCESS, playbook=playbook,
                                           task=task, step_idx=step_idx, attempt=attempt))
                self._bus.emit(HookContext(phase=KernelPhase.POST_STEP, playbook=playbook,
                                           task=task, step_idx=step_idx))
                return StepOutcome(action=StepAction.ADVANCE, attempts_used=attempt + 1)

            last_failure_reason = failure_reason
            failure_history.append({
                "attempt": attempt, "failure_reason": failure_reason,
                "eval_output": _eval_out, "exit_code": _exit,
            })

            if self._brain is not None and attempt < max_retries:
                # F-C1：PRE_CORRECTION dispatch（hookspec 既有定義，本處首次發布）。
                # PreferenceMemoryPlugin 回傳 PromptInjectionResult（## 使用者偏好），
                # 僅於非空時以 preferences_section 傳遞（fake brain 向下相容）。
                pre_correction = self._bus.emit(HookContext(
                    phase=KernelPhase.PRE_CORRECTION, playbook=playbook, task=task,
                    step_idx=step_idx, attempt=attempt,
                    payload={"failure_reason": failure_reason},
                ))
                _prefs_kwargs = (
                    {"preferences_section": pre_correction.accumulated_prefix}
                    if pre_correction.accumulated_prefix else {}
                )
                c = self._brain.decide_correction(
                    task=task, failure_reason=failure_reason, eval_output=_eval_out,
                    attempt=attempt, global_goal=playbook.global_goal,
                    **_prefs_kwargs,
                )
                if c is None:
                    return StepOutcome(action=StepAction.ESCALATE,
                                       failure_reason="Minimax API 故障，安全停止",
                                       attempts_used=attempt + 1)
                # improving_71 W-71-2：CORRECTION 可觀測標記（observability-only，零行為變更）。
                # Kernel 正式路徑原本無 correction log marker，致 pty/sdk A/B 無法計數
                # CORRECTION 次數（tools/ab_compare_backends.py 依此行計數）。
                logger.info(
                    "=== STATE: CORRECTION | step=%s attempt=%d ===",
                    task.step_id, attempt + 1,
                )
                if c.correction_prompt:
                    task.prompt = c.correction_prompt
                mut = getattr(c, "step_mutation", None)
                if mut is not None:
                    out = self._apply_mutation(playbook, task, step_idx, mut, attempt)
                    if out is not None:
                        return out

            post_attempt = self._bus.emit(HookContext(
                phase=KernelPhase.POST_ATTEMPT, playbook=playbook, task=task,
                step_idx=step_idx, attempt=attempt,
                payload={
                    "failure_reason": failure_reason, "exit_code": _exit,
                    "failure_history": failure_history, "step_id": task.step_id,
                },
            ))
            contributors.extend(post_attempt.contributors)
            if post_attempt.request_escalation:
                return StepOutcome(action=StepAction.ESCALATE,
                                   failure_reason=f"[{task.step_id}] {failure_reason}",
                                   attempts_used=attempt + 1)
            if post_attempt.request_halt:
                return StepOutcome(action=StepAction.HALT, failure_reason=failure_reason,
                                   attempts_used=attempt + 1)
            attempt += 1

        step_log.append(f"[FAIL] {task.step_id}: {last_failure_reason} (attempt {attempt})")
        self._bus.emit(HookContext(phase=KernelPhase.ON_FAILURE, playbook=playbook, task=task,
                                   step_idx=step_idx,
                                   payload={"failure_reason": last_failure_reason}))
        return StepOutcome(action=StepAction.ESCALATE,
                           failure_reason=f"max_retries_exhausted: {last_failure_reason}",
                           attempts_used=attempt)

    def _consult_token_guard(
        self, playbook, task, step_idx, attempt, max_retries, peak_pct,
    ) -> StepOutcome | None:
        """improving_78 W-78-1（DEF-78-001）：production token-guard halt 接線。

        以 executor 觀測到的真實 token% emit ON_TOKEN_USAGE；token_guard 判 ≥halt 門檻
        則回傳 HALT StepOutcome（並印真誠 TOKEN_HALT marker 供載具計數），否則 None。
        ≥compact 門檻的 request_compact 由 W-78-2 執行層處理，本輪 Kernel 不動作（純 DAG）。
        peak_pct<=0（無 token 訊號，如 dry-run / 既有 fake）直接 None、不 emit → 零退化。
        """
        if peak_pct <= 0:
            return None
        tu = self._bus.emit(HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=playbook, task=task,
            step_idx=step_idx, attempt=attempt,
            payload={"token_pct": peak_pct, "step_id": task.step_id,
                     "max_retries": max_retries},
        ))
        if tu.request_halt:
            logger.warning(
                "=== STATE: TOKEN_HALT | [%s] context %.0f%% >= halt 門檻 ===",
                task.step_id, peak_pct,
            )
            return StepOutcome(action=StepAction.HALT, attempts_used=attempt + 1,
                               peak_token_pct=peak_pct)
        return None

    def _apply_mutation(self, playbook, task, step_idx, mut, attempt) -> StepOutcome | None:
        """Brain correction step_mutation 處理；回傳 StepOutcome 表示需跳轉，None 表示繼續。"""
        mt = mut.mutation_type
        if mt == StepMutationType.GOTO_STEP and mut.goto_step_id:
            target = next(
                (i for i, t in enumerate(playbook.tasks) if t.step_id == mut.goto_step_id), None
            )
            if target is not None:
                return StepOutcome(action=StepAction.GOTO, goto_idx=target,
                                   attempts_used=attempt + 1)
        elif mt == StepMutationType.INJECT_BEFORE and mut.new_step_prompt:
            playbook.tasks.insert(step_idx, PlaybookTask(
                step_id=mut.new_step_id or f"{task.step_id}_PRE",
                name=mut.new_step_name or f"前置步驟（注入於 {task.step_id} 前）",
                prompt=mut.new_step_prompt,
                expected_output_regex=mut.new_step_expected_regex,
                max_retries=mut.new_step_max_retries,
            ))
            return StepOutcome(action=StepAction.GOTO, goto_idx=step_idx,
                               attempts_used=attempt + 1)
        elif mt == StepMutationType.INJECT_AFTER and mut.new_step_prompt:
            playbook.tasks.insert(step_idx + 1, PlaybookTask(
                step_id=mut.new_step_id or f"{task.step_id}_INJECT",
                name=mut.new_step_name or f"{task.name}（注入步驟）",
                prompt=mut.new_step_prompt,
                expected_output_regex=mut.new_step_expected_regex,
                max_retries=mut.new_step_max_retries,
            ))
        elif mt == StepMutationType.REVISE_CURRENT and mut.revised_prompt:
            task.prompt = mut.revised_prompt
        return None
