"""
SD_07 W1: 修正循環輔助（從 _impl.py 抽出，原 L432-478 + L480-523）

職責：
1. `apply_step_mutations()` — batch / single mutation 套用（Gap-019-B / Gap-025 / Gap-034）
2. `validate_and_retry_correction()` — Gap-009-C 應用驗證警告 + Gap-008-D 品質驗證 + 策略輪換重試

設計原則（依 ADR-SD07-001 strategy tier ≤ 300 LOC）：
- 兩個函式維持 _impl.py 編排層職責清楚分離
- 完整保留原邏輯順序與 logger 訊息（行為等價）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ...decision.minimax_client import _validate_correction_quality
from ...decision.prompt_builder import STRATEGY_PROMPTS
from ..types import PlaybookResult

logger = logging.getLogger("autoclaude.execution.playbook")


@dataclass
class _MutationApplyOutcome:
    """apply_step_mutations 回傳結果"""
    early_return: Optional[PlaybookResult] = None
    inject_before_pending: bool = False
    goto_target_idx: Optional[int] = None
    clear_goal_summary: bool = False
    should_break: bool = False


def apply_step_mutations(
    *,
    runner,
    step_mutation,
    playbook,
    playbook_path: str,
    task,
    step_idx: int,
    step_log: list[str],
    mutation_log: list[str],
    attempt: int,
    inject_before_counter: dict,
    goto_counter: dict,
    skip_to_counter: dict,
    workflow,
    total: int,
    tracker,
    eval_output: str,
) -> _MutationApplyOutcome:
    """套用 batch 或 single mutation（原 _impl.py L432-478）

    Returns:
        _MutationApplyOutcome：含 early_return / inject_before_pending / goto_target_idx /
        clear_goal_summary / should_break 五旗標
    """
    outcome = _MutationApplyOutcome()

    if step_mutation is not None and step_mutation.batch_mutations:
        _batch = step_mutation.batch_mutations[:3]
        logger.info(
            "=== Gap-019-B | [%s] 批次突變 %d 個 ===", task.step_id, len(_batch)
        )
        _batch_valid, _batch_reason = runner._validate_batch_compatibility(_batch)
        if not _batch_valid:
            logger.warning(
                "=== Gap-025 | 批次突變相容性失敗（%s），降級為單一突變 ===", _batch_reason
            )
            step_mutation = _batch[0]
        else:
            for _batch_m in _batch:
                _batch_result = runner._apply_single_mutation(
                    _batch_m, playbook, playbook_path, task, step_idx,
                    step_log, mutation_log, attempt,
                    inject_before_counter, goto_counter, skip_to_counter,
                    workflow, total, tracker, eval_output,
                )
                if _batch_result.early_return is not None:
                    outcome.early_return = _batch_result.early_return
                    return outcome
                if _batch_result.inject_before_pending:
                    outcome.inject_before_pending = True
                if _batch_result.goto_target_idx is not None:
                    outcome.goto_target_idx = _batch_result.goto_target_idx
            step_mutation = None

    if step_mutation is not None:
        _mut_result = runner._apply_single_mutation(
            step_mutation, playbook, playbook_path, task, step_idx,
            step_log, mutation_log, attempt,
            inject_before_counter, goto_counter, skip_to_counter,
            workflow, total, tracker, eval_output,
        )
        if _mut_result.early_return is not None:
            outcome.early_return = _mut_result.early_return
            return outcome
        if _mut_result.inject_before_pending:
            outcome.inject_before_pending = True
        if _mut_result.goto_target_idx is not None:
            outcome.goto_target_idx = _mut_result.goto_target_idx
        if _mut_result.clear_goal_summary:
            outcome.clear_goal_summary = True
            logger.info("Gap-034 | REVISE_CURRENT：清除 _task_goal_summary 快取")
        if tracker.history:
            tracker.history[-1].mutation_applied = True
        if _mut_result.should_break:
            outcome.should_break = True

    return outcome


def validate_and_retry_correction(
    *,
    runner,
    task,
    failure_reason: str,
    eval_output: str,
    attempt: int,
    attempt_offset: int,
    correction_prompt: str,
    minimax_reasoning: str,
    strategy_hint: str,
    tracker,
    report,
    error_cls,
    task_goal_summary: Optional[str],
    playbook,
    mutation_log: list[str],
    mutation_pressure: int,
    allow_mutation: bool,
) -> tuple[str, str]:
    """Gap-009-C 應用驗證警告 + Gap-008-D 品質驗證 + 策略輪換重試（原 _impl.py L480-523）

    Returns:
        (correction_prompt, minimax_reasoning)：可能被覆寫的修正 prompt + reasoning
    """
    if attempt > attempt_offset and not runner._dry_run:
        no_change_hint = runner._verify_correction_applied(attempt)
        if no_change_hint:
            logger.warning(
                "=== Gap-009-C | [%s] attempt %d 無 git diff，注入應用驗證警告 ===",
                task.step_id, attempt,
            )
            correction_prompt = no_change_hint + "\n\n---\n\n" + correction_prompt

    if not strategy_hint:
        prev_prompts = [
            r.correction_prompt_sent for r in tracker.history
            if r.correction_prompt_sent
        ]
        is_valid, quality_reason = _validate_correction_quality(
            correction_prompt, prev_prompts
        )
        if not is_valid:
            logger.warning(
                "=== Gap-008-D | 品質驗證失敗: %s，切換策略重試 ===",
                quality_reason,
            )
            next_strat = tracker.next_strategy(
                kb=runner._knowledge_base, current_error_class=error_cls.value
            )
            retry_strategy = STRATEGY_PROMPTS.get(
                next_strat, STRATEGY_PROMPTS["PINPOINT"]
            )
            retry_result = runner._get_correction(
                task, failure_reason, eval_output, attempt,
                history_summary=tracker.build_history_summary(),
                last_correction_prompt=correction_prompt,
                convergence_trend=report.trend,
                convergence_reasoning=report.reasoning,
                strategy_hint=retry_strategy,
                error_class=error_cls.value,
                task_goal_summary=task_goal_summary,
                global_goal=playbook.global_goal,
                allow_step_mutation=allow_mutation,
                mutation_history=list(mutation_log),
                mutation_pressure=mutation_pressure,
            )
            if retry_result:
                correction_prompt, minimax_reasoning, _, _ = retry_result

    return correction_prompt, minimax_reasoning
