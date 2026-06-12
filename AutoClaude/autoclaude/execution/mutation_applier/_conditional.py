"""_conditional.py — CONDITIONAL handler（含 shell 安全 + 遞迴 dispatch）。

對應 SD_06 W2 G2 deferred + SD_05 W4 Gap-046 安全強化。
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import TYPE_CHECKING

from ...utils.trace_context import propagate_to_subprocess_env

if TYPE_CHECKING:
    from ...models.step_mutation import StepMutation
    from ..types import _MutationResult
    from ._dispatcher import MutationCtx

logger = logging.getLogger("autoclaude.execution.playbook")

_SAFE_COND_PATTERN = re.compile(r'^[\w\s\-./=:!"\']+$')


def handle_conditional(ctx: "MutationCtx", mutation: "StepMutation", result: "_MutationResult") -> None:
    if not mutation.condition_evaluator:
        logger.warning("=== Gap-021 | CONDITIONAL 缺少 condition_evaluator，略過 ===")
        return
    if not _SAFE_COND_PATTERN.match(mutation.condition_evaluator.strip()):
        logger.warning(
            "=== Gap-046 | CONDITIONAL evaluator 包含不安全字符，略過: %s ===",
            mutation.condition_evaluator[:80],
        )
        return
    try:
        cond_proc = subprocess.run(
            mutation.condition_evaluator,
            shell=True, capture_output=True,
            timeout=ctx.runner._cfg.playbook.conditional_evaluator_timeout_seconds,
            env=propagate_to_subprocess_env(dict(os.environ)),
        )
        cond_exit = cond_proc.returncode
    except Exception as exc:
        logger.warning("=== Gap-021 | CONDITIONAL evaluator 執行失敗: %s，視為 false ===", exc)
        cond_exit = 1
    branch = mutation.true_mutation if cond_exit == 0 else mutation.false_mutation
    logger.info(
        "=== Gap-021 | CONDITIONAL exit=%d，選擇分支: %s ===",
        cond_exit, "true_mutation" if cond_exit == 0 else "false_mutation",
    )
    if branch is None:
        return
    branch_result = ctx.runner._apply_single_mutation(
        branch, ctx.playbook, ctx.playbook_path, ctx.task, ctx.step_idx,
        ctx.step_log, ctx.mutation_log, ctx.attempt,
        ctx.inject_before_counter, ctx.goto_counter, ctx.skip_to_counter,
        ctx.workflow, ctx.total, ctx.tracker, ctx.eval_output,
    )
    result.should_break = branch_result.should_break
    result.inject_before_pending = branch_result.inject_before_pending
    result.goto_target_idx = branch_result.goto_target_idx
    result.early_return = branch_result.early_return
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] CONDITIONAL: exit={cond_exit} → "
        f"{'true' if cond_exit == 0 else 'false'} branch ({branch.mutation_type})"
    )
