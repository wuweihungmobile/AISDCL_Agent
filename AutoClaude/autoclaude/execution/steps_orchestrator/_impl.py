
# ──────────────────────────────────────────────────────────────
# SD_06 W2-T2-2: _run_steps 主體下沉（從 _runner_internals.py 抽出）
# ──────────────────────────────────────────────────────────────
from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

import yaml

from ...models.playbook import Playbook, PlaybookTask
from ...models.escalation import EscalationDump
from ...models.step_mutation import StepMutation, StepMutationType
from ...utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
from ...utils.token_tracker import extract_context_pct
from ...perception.pty_wrapper import strip_ansi
from ...decision.minimax_client import _validate_correction_quality
from ...decision.prompt_builder import STRATEGY_PROMPTS
from ..workflow_detector import WorkflowType
from ..failure_tracker import FailureTracker
from ..error_classifier import ErrorClass
from ...plugins.goal_synthesis_plugin import GoalSynthesisPlugin as _GoalSynthesisPlugin
from ..pre_run_validator import PreRunValidator
from ..error_budget import ErrorBudget

from ..types import _StepOutput, PlaybookResult, _MutationResult
from ..playbook_runner import _pr

logger = logging.getLogger("autoclaude.execution.playbook")


def run_steps_impl(
    runner: "PlaybookRunner",
    playbook: Playbook,
    playbook_path: str,
    start_idx: int,
    prior_log: list[str],
    is_first_prompt: bool,
    workflow: WorkflowType,
    total: int,
    resume_checkpoint: Optional[PlaybookCheckpoint] = None,
) -> PlaybookResult:
    step_log = list(prior_log)

    # SD_06 W2 G2 階段 B：CONTEXT_NEGOTIATION 區塊抽至 _context_negotiation.py
    from ._context_negotiation import handle_context_negotiation
    is_first_prompt, _cn_early_return = handle_context_negotiation(
        runner, playbook, playbook_path, is_first_prompt, start_idx, workflow, total,
    )
    if _cn_early_return is not None:
        return _cn_early_return

    # SD_06 W2 G2 階段 B：counter restore + mutation_log + KB 預播種抽至 _loop_state.py
    from ._loop_state import initialize_loop_state
    _state = initialize_loop_state(runner, playbook, resume_checkpoint)
    _goto_counter = _state.goto_counter
    _inject_before_counter = _state.inject_before_counter
    _skip_to_counter = _state.skip_to_counter
    _step_evolution_counter = _state.step_evolution_counter
    _step_trackers: dict[str, FailureTracker] = _state.step_trackers
    _mutation_log: list[str] = _state.mutation_log
    _completed_step_ids: set[str] = _state.completed_step_ids
    _skip_completed_ids: set[str] = _state.skip_completed_ids
    _goal_synthesis_injected = _state.goal_synthesis_injected

    step_idx = start_idx
    _prev_step_idx = -1
    while step_idx < len(playbook.tasks):
        task = playbook.tasks[step_idx]

        if task.step_id in _skip_completed_ids:
            logger.info("=== Gap-041 | 跳過已完成步驟（演化後恢復）: %s ===", task.step_id)
            step_log.append(f"[RESUMED] {task.step_id}（Gap-041：演化前已完成，跳過）")
            step_idx += 1
            continue

        # SD_06 W2 G2 階段 B-1：cross_hint + tracker init + hotkey check 抽至 _step_init.py
        from ._step_init import build_cross_step_hint, init_step_tracker, check_hotkey_and_save
        _cross_hint = build_cross_step_hint(runner, playbook, task, step_idx, _prev_step_idx)
        tracker, attempt_offset, resume_checkpoint = init_step_tracker(
            task, _step_trackers, resume_checkpoint, playbook,
        )
        _hotkey_return = check_hotkey_and_save(
            runner, playbook, playbook_path, task, step_idx, step_log, total,
            tracker, attempt_offset,
            _goto_counter, _inject_before_counter, _skip_to_counter,
            _completed_step_ids, _step_evolution_counter, workflow,
        )
        if _hotkey_return is not None:
            return _hotkey_return

        max_retries = (
            task.max_retries
            if task.max_retries is not None
            else playbook.global_invariants.max_retries_per_step
        )
        correction_prompt: Optional[str] = None
        monitor = _pr().ConvergenceMonitor()
        minimax_reasoning = ""
        last_error_cls = ErrorClass.UNKNOWN
        last_strategy_used = "PINPOINT"
        _task_goal_summary: Optional[str] = None
        _inject_before_pending = False
        _goto_target_idx: Optional[int] = None

        _pre_run_hint: Optional[str] = None
        if not runner._dry_run and task.evaluator_command:
            pre_run_issues = PreRunValidator().validate_step(
                task.evaluator_command, task.prompt
            )
            block_issues = [i for i in pre_run_issues if i.severity == "block"]
            if block_issues:
                issue = block_issues[0]
                logger.warning(
                    "=== Gap-009-B | [%s] Pre-Run block 偵測: %s ===",
                    task.step_id, issue.message,
                )
                _pre_run_hint = issue.strategy_hint

        logger.info("=== STATE: EXECUTE | [%s/%d] %s ===", task.step_id, step_idx + 1, task.name)

        for attempt in range(attempt_offset, max_retries + 1):
            if runner._hotkey.triggered:
                runner._checkpoint_plugin.save_interrupt_checkpoint(
                    playbook, playbook_path, task, step_idx, step_log, total,
                    tracker=tracker, attempt=attempt,
                    goto_counter=_goto_counter,
                    inject_before_counter=_inject_before_counter,
                    skip_to_counter=_skip_to_counter,
                    completed_step_ids=list(_completed_step_ids),
                    step_evolution_counter=_step_evolution_counter,
                )
                return PlaybookResult(
                    False, len(step_log), total, "使用者 ESC+F12 中斷（已儲存中斷點）",
                    workflow, step_log,
                )

            interval = playbook.global_invariants.auto_compact_interval
            if interval > 0 and runner._step_counter > 0 and runner._step_counter % interval == 0:
                logger.info("=== STATE: CONTEXT_RESET (step_counter=%d) ===", runner._step_counter)
                if not runner._send_compact(
                    is_first_prompt, task=task, attempt=attempt,
                    global_goal=playbook.global_goal,
                ):
                    return PlaybookResult(
                        False, len(step_log), total,
                        f"Gap-008-E: compact 連續失敗 2 次，TOKEN_HALT [{task.step_id}]",
                        workflow, step_log,
                    )

            prompt_to_send = correction_prompt if correction_prompt else task.prompt
            correction_prompt = None

            if attempt == attempt_offset and _pre_run_hint:
                original_prompt_preview = task.prompt[:1000] + ("..." if len(task.prompt) > 1000 else "")
                prompt_to_send = (
                    _pre_run_hint
                    + "\n\n---\n\n完成修復後，繼續執行以下原始任務：\n"
                    + original_prompt_preview
                )
                _pre_run_hint = None
                logger.info(
                    "=== Gap-009-B | [%s] Pre-Run block，首次 Prompt 已注入約束 ===",
                    task.step_id,
                )

            if attempt == attempt_offset and _cross_hint:
                prompt_to_send = _cross_hint + "\n\n---\n\n" + prompt_to_send
                _cross_hint = None
                logger.info(
                    "=== Gap-010-C | [%s] 跨步驟污染警告已注入首次 Prompt ===",
                    task.step_id,
                )

            if attempt == attempt_offset:
                if step_idx == 0:
                    prompt_to_send = runner._prepend_global_goal(prompt_to_send, playbook.global_goal)
                else:
                    # SD_07 W4-T4-6：直接走 plugin SSOT（原 runner._prepend_global_goal_brief shim 已物理拔除）
                    prompt_to_send = runner._goal_synthesis_plugin.prepend_global_goal_brief(
                        prompt_to_send, playbook.global_goal, runner._cfg,
                    )

            if runner._dry_run:
                regex = task.expected_output_regex or ""
                keyword = re.sub(r"\\(.)", r"\1", regex) if regex else "dry-run-pass"
                step_out = _StepOutput(text=f"[dry-run] {keyword}")
            else:
                step_out = runner._execute_prompt(
                    prompt=prompt_to_send,
                    maintain_context=not is_first_prompt,
                    timeout=runner._cfg.playbook.step_timeout_seconds,
                    step_label=f"{task.step_id}_attempt{attempt}",
                )
            is_first_prompt = False
            runner._step_counter += 1

            if runner._cfg.token_guard.enabled:
                if step_out.triggered_halt:
                    return runner._handle_token_halt(
                        playbook, playbook_path, task, step_idx,
                        step_out, step_log, workflow, total,
                        tracker=tracker, attempt=attempt,
                        goto_counter=_goto_counter,
                        inject_before_counter=_inject_before_counter,
                        skip_to_counter=_skip_to_counter,
                        completed_step_ids=_completed_step_ids,
                        step_evolution_counter=_step_evolution_counter,
                    )
                if runner._should_compact_now(
                    step_out,
                    in_correction_loop=(attempt > 0),
                    correction_history_len=len(tracker.history),
                    attempt=attempt,
                    max_retries=max_retries,
                ):
                    logger.info(
                        "=== STATE: TOKEN_COMPACT | [%s] %.0f%% >=  %.0f%% ===",
                        task.step_id, step_out.peak_token_pct,
                        runner._cfg.token_guard.compact_threshold_pct,
                    )
                    runner._token_logger.record(
                        playbook.project, task.step_id,
                        step_out.peak_token_pct, "compact", "in_progress",
                    )
                    failure_summary = tracker.build_history_summary() if tracker.history else ""
                    if not runner._send_compact(
                        False, failure_summary=failure_summary,
                        task=task, attempt=attempt,
                        global_goal=playbook.global_goal,
                    ):
                        return PlaybookResult(
                            False, len(step_log), total,
                            f"Gap-008-E: compact 連續失敗 2 次，TOKEN_HALT [{task.step_id}]",
                            workflow, step_log,
                        )

            logger.info("=== STATE: EVALUATE | [%s] attempt %d ===", task.step_id, attempt + 1)
            failure_reason, eval_output, exit_code = runner._evaluate(task, step_out.text)

            if failure_reason is None:
                msg = f"[{task.step_id}] {task.name} ✓ (attempt {attempt + 1})"
                logger.info(msg)
                step_log.append(msg)
                runner._token_logger.record(
                    playbook.project, task.step_id,
                    step_out.peak_token_pct, "continue", "success",
                )
                if attempt > attempt_offset and tracker.history:
                    kb_key = f"{last_error_cls.value}:{tracker.history[-1].error_signature[:60]}"
                    runner._knowledge_base.record_success(
                        kb_key, last_strategy_used, task.step_id,
                        error_class=last_error_cls.value,
                    )
                _completed_step_ids.add(task.step_id)
                break

            logger.warning(
                "[%s] attempt %d/%d 失敗: %s",
                task.step_id, attempt + 1, max_retries + 1, failure_reason,
            )
            runner._token_logger.record(
                playbook.project, task.step_id,
                step_out.peak_token_pct, "continue", "failed",
            )

            error_cls = runner._error_classifier.classify(eval_output, exit_code)
            last_error_cls = error_cls
            tracker.record(attempt, failure_reason, eval_output, exit_code, minimax_reasoning,
                           error_class=error_cls.value)

            report = monitor.evaluate(tracker)
            if report.recommendation == "escalate":
                from ._escalation_handler import handle_convergence_escalation
                return handle_convergence_escalation(
                    runner=runner,
                    playbook=playbook,
                    playbook_path=playbook_path,
                    task=task,
                    step_idx=step_idx,
                    tracker=tracker,
                    convergence_trend=report.trend,
                    convergence_reasoning=report.reasoning,
                    eval_output=eval_output,
                    error_cls=error_cls,
                    step_log=step_log,
                    workflow=workflow,
                    total=total,
                    mutation_log=_mutation_log,
                    completed_step_ids=_completed_step_ids,
                    step_evolution_counter=_step_evolution_counter,
                )

            _budget_check = ErrorBudget()
            _eff_limit = _budget_check.effective_max_retries(max_retries, error_cls.value, attempt)
            if attempt >= _eff_limit and _eff_limit < max_retries:
                logger.warning(
                    "=== Gap-010-A | [%s] error_class=%s 語意預算耗盡（attempt=%d eff=%d）===",
                    task.step_id, error_cls.value, attempt, _eff_limit,
                )
                if tracker.history:
                    kb_key = f"{error_cls.value}:{tracker.history[-1].error_signature[:60]}"
                    runner._knowledge_base.record_escalation(
                        kb_key, list(tracker._tried_strategies), task.step_id
                    )
                _dump = runner._save_escalation_dump(
                    tracker, task, playbook_path, eval_output,
                    human_hint=f"Gap-010-A: {error_cls.value} 語意預算耗盡（{_eff_limit + 1} 次修正無效）",
                )
                runner._escalation_history.append(_dump)
                runner._notify(
                    "AutoClaude — 需要人工介入",
                    f"[{task.step_id}] {error_cls.value} 語意預算耗盡，提前 ESCALATION",
                )
                return PlaybookResult(
                    False, len(step_log), total,
                    f"[{task.step_id}] 語意預算耗盡 ({error_cls.value}): {failure_reason}",
                    workflow, step_log,
                )

            strategy_hint = ""
            if report.recommendation == "change_strategy":
                next_strat = tracker.next_strategy(
                    kb=runner._knowledge_base, current_error_class=error_cls.value
                )
                strategy_hint = STRATEGY_PROMPTS.get(next_strat, STRATEGY_PROMPTS["PINPOINT"])
                last_strategy_used = next_strat
                logger.info(
                    "=== STATE: CHANGE_STRATEGY | [%s] 策略輪換至 %s ===",
                    task.step_id, next_strat,
                )

            if attempt >= max_retries:
                from ._escalation_handler import handle_max_retries_escalation
                return handle_max_retries_escalation(
                    runner=runner,
                    playbook=playbook,
                    playbook_path=playbook_path,
                    task=task,
                    step_idx=step_idx,
                    tracker=tracker,
                    max_retries=max_retries,
                    eval_output=eval_output,
                    error_cls=error_cls,
                    failure_reason=failure_reason,
                    step_log=step_log,
                    workflow=workflow,
                    total=total,
                    mutation_log=_mutation_log,
                    completed_step_ids=_completed_step_ids,
                    step_evolution_counter=_step_evolution_counter,
                )

            if not strategy_hint and tracker.history:
                kb_key = f"{error_cls.value}:{tracker.history[-1].error_signature[:60]}"
                kb_entry = runner._knowledge_base.query(kb_key)
                if not kb_entry:
                    _fallback_key = f"{error_cls.value}:{task.step_id}:env_setup"
                    kb_entry = runner._knowledge_base.query(_fallback_key)
                    if kb_entry:
                        logger.info(
                            "=== Gap-045 | 知識庫兜底命中 [%s] key=%s ===",
                            task.step_id, _fallback_key,
                        )
                if kb_entry and kb_entry.get("successful_strategy"):
                    kb_strategy = kb_entry["successful_strategy"]
                    strategy_hint = STRATEGY_PROMPTS.get(
                        kb_strategy, STRATEGY_PROMPTS["PINPOINT"]
                    )
                    last_strategy_used = kb_strategy
                    logger.info(
                        "=== Gap-009-E | 知識庫命中 [%s]: 直接使用策略 %s ===",
                        task.step_id, kb_strategy,
                    )
                    for strat in kb_entry.get("skip_strategies", []):
                        tracker._tried_strategies.add(strat)

            if attempt == 0 and not runner._dry_run:
                fast_path = runner._fast_path_test_file_check(eval_output)
                if fast_path:
                    strategy_hint = fast_path
                    logger.warning(
                        "=== Gap-007-B | [%s] Fast-path 偵測到測試檔語法錯誤，注入硬性約束 ===",
                        task.step_id,
                    )

            _is_prerequisite_error = error_cls in (ErrorClass.IMPORT, ErrorClass.ENVIRONMENT)
            allow_mutation = (
                (_is_prerequisite_error and attempt >= 1)
                or (attempt >= 2 and report.trend in ("stuck", "oscillating", "cycling"))
            )

            _mutation_pressure = (
                sum(
                    1 for r in tracker.history
                    if r.correction_prompt_sent and not r.mutation_applied
                )
                if allow_mutation else 0
            )

            logger.info("=== STATE: CORRECTION | 諮詢 Minimax ===")
            corr_result = runner._get_correction(
                task, failure_reason, eval_output, attempt,
                history_summary=tracker.build_history_summary(),
                last_correction_prompt=(
                    tracker.history[-1].correction_prompt_sent or ""
                    if tracker.history else ""
                ),
                convergence_trend=report.trend,
                convergence_reasoning=report.reasoning,
                strategy_hint=strategy_hint,
                error_class=error_cls.value,
                task_goal_summary=_task_goal_summary,
                global_goal=playbook.global_goal,
                allow_step_mutation=allow_mutation,
                mutation_history=list(_mutation_log),
                mutation_pressure=_mutation_pressure,
            )
            if corr_result is None:
                return PlaybookResult(
                    False, len(step_log), total, "Minimax API 故障，安全停止",
                    workflow, step_log,
                )
            correction_prompt, minimax_reasoning, _new_goal_summary, _step_mutation = corr_result
            if _new_goal_summary and not _task_goal_summary:
                _task_goal_summary = _new_goal_summary

            if _step_mutation is not None:
                from ._correction_helpers import apply_step_mutations
                _apply_outcome = apply_step_mutations(
                    runner=runner,
                    step_mutation=_step_mutation,
                    playbook=playbook,
                    playbook_path=playbook_path,
                    task=task,
                    step_idx=step_idx,
                    step_log=step_log,
                    mutation_log=_mutation_log,
                    attempt=attempt,
                    inject_before_counter=_inject_before_counter,
                    goto_counter=_goto_counter,
                    skip_to_counter=_skip_to_counter,
                    workflow=workflow,
                    total=total,
                    tracker=tracker,
                    eval_output=eval_output,
                )
                if _apply_outcome.early_return is not None:
                    return _apply_outcome.early_return
                if _apply_outcome.inject_before_pending:
                    _inject_before_pending = True
                if _apply_outcome.goto_target_idx is not None:
                    _goto_target_idx = _apply_outcome.goto_target_idx
                if _apply_outcome.clear_goal_summary:
                    _task_goal_summary = None
                if _apply_outcome.should_break:
                    break

            from ._correction_helpers import validate_and_retry_correction
            correction_prompt, minimax_reasoning = validate_and_retry_correction(
                runner=runner,
                task=task,
                failure_reason=failure_reason,
                eval_output=eval_output,
                attempt=attempt,
                attempt_offset=attempt_offset,
                correction_prompt=correction_prompt,
                minimax_reasoning=minimax_reasoning,
                strategy_hint=strategy_hint,
                tracker=tracker,
                report=report,
                error_cls=error_cls,
                task_goal_summary=_task_goal_summary,
                playbook=playbook,
                mutation_log=_mutation_log,
                mutation_pressure=_mutation_pressure,
                allow_mutation=allow_mutation,
            )

            tracker.update_last_correction_prompt(correction_prompt)
            logger.info("Minimax 修正 Prompt (前 100 字): %s…", correction_prompt[:100])

        if _inject_before_pending:
            _inject_before_pending = False
            _prev_step_idx = step_idx
            continue
        if _goto_target_idx is not None:
            _prev_step_idx = step_idx
            if (
                not runner._dry_run
                and runner._cfg.token_guard.enabled
                and runner._step_counter > 0
            ):
                _goto_anchor_task = playbook.tasks[_goto_target_idx]
                logger.info(
                    "=== Gap-031 | GOTO 前置 /compact（目標步驟 %s）===",
                    _goto_anchor_task.step_id,
                )
                runner._send_compact(
                    False,
                    task=_goto_anchor_task,
                    attempt=0,
                    global_goal=playbook.global_goal,
                )
            step_idx = _goto_target_idx
            _goto_target_idx = None
            continue

        _prev_step_idx = step_idx
        step_idx += 1

        # SD_06 W2 G2 階段 B-2：GOAL_SYNTHESIS 注入抽至 _goal_synthesis.py
        from ._goal_synthesis import maybe_inject_goal_synthesis
        _goal_synthesis_injected, total = maybe_inject_goal_synthesis(
            runner, playbook, step_idx, step_log, _goal_synthesis_injected,
        )

    _final_total = len(playbook.tasks)
    logger.info("=== STATE: DONE | 所有 %d 步驟完成 ===", _final_total)
    runner._notify(
        f"AutoClaude — {playbook.project} 完成",
        f"所有 {_final_total} 步驟執行完畢！工作流程: {workflow}",
    )
    return PlaybookResult(True, _final_total, _final_total, "所有步驟完成", workflow, step_log)

