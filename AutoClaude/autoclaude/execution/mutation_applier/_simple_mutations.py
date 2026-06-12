"""_simple_mutations.py — REVISE_CURRENT / INJECT_AFTER / DELETE_STEP / SKIP_TO handlers.

對應 SD_06 W2 G2 deferred：簡單變異（不含 escalation/evolution 觸發路徑）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...models.playbook import PlaybookTask

if TYPE_CHECKING:
    from ...models.step_mutation import StepMutation
    from ..types import _MutationResult
    from ._dispatcher import MutationCtx

logger = logging.getLogger("autoclaude.execution.playbook")


def handle_revise_current(ctx: "MutationCtx", mutation: "StepMutation", result: "_MutationResult") -> None:
    ctx.task.prompt = mutation.revised_prompt
    logger.info("=== Gap-011-B | REVISE_CURRENT 步驟 %s prompt 已更新 ===", ctx.task.step_id)
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] REVISE_CURRENT: 步驟 {ctx.task.step_id} prompt 已更新"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    result.clear_goal_summary = True


def handle_inject_after(ctx: "MutationCtx", mutation: "StepMutation", result: "_MutationResult") -> None:
    new_task = PlaybookTask(
        step_id=mutation.new_step_id or f"{ctx.task.step_id}_INJECT",
        name=mutation.new_step_name or f"{ctx.task.name}（注入步驟）",
        prompt=mutation.new_step_prompt,
        expected_output_regex=mutation.new_step_expected_regex,
        evaluator_command=(
            mutation.new_step_evaluator_command or "git diff --stat HEAD | grep -c ."
        ),
        max_retries=mutation.new_step_max_retries,
    )
    ctx.playbook.tasks.insert(ctx.step_idx + 1, new_task)
    logger.info(
        "=== Gap-011-B / Gap-036 | INJECT_AFTER 插入步驟 %s 於 %s 後（evaluator=%s）===",
        new_task.step_id, ctx.task.step_id,
        new_task.evaluator_command[:60] if new_task.evaluator_command else "None",
    )
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] INJECT_AFTER: 插入步驟 {new_task.step_id} 於 {ctx.task.step_id} 後"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)


def handle_delete_step(ctx: "MutationCtx", mutation: "StepMutation", result: "_MutationResult") -> None:
    del_id = mutation.delete_step_id
    del_idx = next(
        (i for i, t in enumerate(ctx.playbook.tasks) if t.step_id == del_id), None,
    )
    if del_idx is not None and del_idx > ctx.step_idx:
        del ctx.playbook.tasks[del_idx]
        ctx.step_log.append(f"[DELETED] {del_id}（Minimax 判定為冗餘）")
        logger.info("=== Gap-012-C | DELETE_STEP 刪除步驟 %s（原 idx=%d）===", del_id, del_idx)
        ctx.mutation_log.append(f"[attempt {ctx.attempt}] DELETE_STEP: 刪除步驟 {del_id}")
        ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    else:
        logger.warning(
            "=== Gap-012-C | 刪除目標 %s 不存在或不在當前步驟之後（idx=%s），忽略 ===",
            del_id, del_idx,
        )


def handle_skip_to(ctx: "MutationCtx", mutation: "StepMutation", result: "_MutationResult") -> None:
    skip_id = mutation.skip_to_step_id
    skip_target_idx = next(
        (i for i, t in enumerate(ctx.playbook.tasks) if t.step_id == skip_id), None,
    )
    if skip_target_idx is None:
        logger.warning("=== Gap-017-C | SKIP_TO 目標步驟 %s 不存在，忽略 ===", skip_id)
        return
    if skip_target_idx <= ctx.step_idx:
        logger.warning(
            "=== Gap-017-C | 禁止 SKIP_TO 向後（target=%s idx=%d <= current=%d），忽略 ===",
            skip_id, skip_target_idx, ctx.step_idx,
        )
        return
    if ctx.skip_to_counter.get(ctx.task.step_id, 0) >= 1:
        logger.warning(
            "=== Gap-017-C | 步驟 %s 的 SKIP_TO 已執行 1 次，防護限制觸發，忽略 ===",
            ctx.task.step_id,
        )
        return
    ctx.skip_to_counter[ctx.task.step_id] = ctx.skip_to_counter.get(ctx.task.step_id, 0) + 1
    for skipped in ctx.playbook.tasks[ctx.step_idx + 1:skip_target_idx]:
        note = (
            f"[SKIPPED] {skipped.step_id}（Gap-017：Minimax 判定為已隱性完成"
            + (f"，原因：{mutation.skip_reason}" if mutation.skip_reason else "")
            + "）"
        )
        ctx.step_log.append(note)
    result.goto_target_idx = skip_target_idx
    logger.info(
        "=== Gap-017-C | SKIP_TO 跳轉至 %s（idx=%d），跳過 %d 個步驟 ===",
        skip_id, skip_target_idx, skip_target_idx - ctx.step_idx - 1,
    )
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] SKIP_TO: 跳轉至 {skip_id}，"
        f"跳過步驟 {[t.step_id for t in ctx.playbook.tasks[ctx.step_idx + 1:skip_target_idx]]}"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    result.should_break = True
