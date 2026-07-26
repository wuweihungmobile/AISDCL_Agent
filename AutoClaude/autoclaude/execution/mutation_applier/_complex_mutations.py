"""_complex_mutations.py — INJECT_BEFORE / GOTO_STEP handlers（含 escalation/evolution）。

對應 SD_06 W2 G2 deferred：複雜變異（含 GOTO 無限迴圈防護 + 演化觸發）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...models.playbook import PlaybookTask
from ..types import PlaybookResult
from ._simple_mutations import _default_fallback_evaluator_command

if TYPE_CHECKING:
    from ...models.step_mutation import StepMutation
    from ..types import _MutationResult
    from ._dispatcher import MutationCtx

logger = logging.getLogger("autoclaude.execution.playbook")


def handle_inject_before(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    cnt = ctx.inject_before_counter.get(ctx.task.step_id, 0) + 1
    if cnt > 5:
        logger.warning(
            "=== Gap-012-A / Gap-037 | [%s] INJECT_BEFORE 已注入 %d 次，防遞迴 → 忽略 ===",
            ctx.task.step_id, cnt,
        )
        return
    ctx.inject_before_counter[ctx.task.step_id] = cnt
    proposed_id = mutation.new_step_id or f"{ctx.task.step_id}_PRE"
    existing_ids = {t.step_id for t in ctx.playbook.tasks}
    base_prefix = proposed_id.rstrip("_0123456789").rstrip("_PRE")
    similar_existing = [
        sid for sid in existing_ids
        if sid.startswith(base_prefix) and sid != ctx.task.step_id and "PRE" in sid
    ]
    if similar_existing:
        logger.warning(
            "=== Gap-028 | INJECT_BEFORE 偵測到相似前置步驟已存在 %s，"
            "修改 step_id 避免語意重疊 ===", similar_existing,
        )
        proposed_id = f"{ctx.task.step_id}_PRE_{cnt}"
    pre_task = PlaybookTask(
        step_id=proposed_id,
        name=mutation.new_step_name or f"前置步驟（注入於 {ctx.task.step_id} 前）",
        prompt=mutation.new_step_prompt,
        expected_output_regex=mutation.new_step_expected_regex,
        evaluator_command=(
            mutation.new_step_evaluator_command or _default_fallback_evaluator_command()
        ),
        max_retries=mutation.new_step_max_retries,
    )
    ctx.playbook.tasks.insert(ctx.step_idx, pre_task)
    result.inject_before_pending = True
    logger.info(
        "=== Gap-012-A / Gap-036 | INJECT_BEFORE 插入步驟 %s 於 %s 前，"
        "立即切換執行（第 %d 次，evaluator=%s）===",
        pre_task.step_id, ctx.task.step_id, cnt,
        pre_task.evaluator_command[:60] if pre_task.evaluator_command else "None",
    )
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] INJECT_BEFORE: 插入前置步驟 {pre_task.step_id} "
        f"於 {ctx.task.step_id} 前"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    result.should_break = True


def handle_goto_step(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    target_id = mutation.goto_step_id
    target_idx = next(
        (i for i, t in enumerate(ctx.playbook.tasks) if t.step_id == target_id), None,
    )
    if target_idx is None:
        logger.warning("=== Gap-012-B | GOTO 目標步驟 %s 不存在，忽略 ===", target_id)
        return
    if target_idx >= ctx.step_idx:
        logger.warning(
            "=== Gap-012-B | 禁止 GOTO 向前（target=%s idx=%d >= current=%d），忽略 ===",
            target_id, target_idx, ctx.step_idx,
        )
        return
    gc = ctx.goto_counter.get(target_id, 0) + 1
    if gc > ctx.runner._cfg.playbook.max_goto_per_step:
        _trigger_goto_escalation(ctx, target_id, gc, result)
        return
    ctx.goto_counter[target_id] = gc
    result.goto_target_idx = target_idx
    logger.info(
        "=== Gap-012-B | GOTO 跳轉至步驟 %s（idx=%d，第 %d 次）===",
        target_id, target_idx, gc,
    )
    result.should_break = True


def _trigger_goto_escalation(
    ctx: MutationCtx, target_id: str, gc: int, result: _MutationResult,
) -> None:
    """GOTO 上限觸發：dump escalation + 嘗試演化 + 設定 early_return。"""
    logger.error(
        "=== Gap-012-B / Gap-013-E | GOTO %s 已 %d 次，嘗試演化 ===", target_id, gc,
    )
    goto_dump = ctx.runner._save_escalation_dump(
        ctx.tracker, ctx.task, ctx.playbook_path, ctx.eval_output,
        human_hint=(f"GOTO 無限迴圈防護觸發（目標={target_id}，已執行 {gc} 次）"),
    )
    ctx.runner._escalation_history.append(goto_dump)
    proposal = ctx.runner._evolver.propose_evolution(
        ctx.playbook, ctx.step_idx, goto_dump, ctx.runner._escalation_history,
    )
    evolved_path: str | None = None
    if proposal:
        evolved_path = ctx.runner._evolver.apply_evolution(
            ctx.playbook, proposal, ctx.playbook_path, mutation_log=ctx.mutation_log,
        )
        if evolved_path:
            ctx.runner._notify(
                "AutoClaude — Playbook 自動演化（GOTO 迴圈）",
                f"演化版本: {evolved_path}\n原因: {proposal.reasoning}",
            )
    result.early_return = PlaybookResult(
        False, len(ctx.step_log), ctx.total,
        f"[{ctx.task.step_id}] GOTO 無限迴圈防護觸發（目標={target_id}）",
        ctx.workflow, ctx.step_log,
        evolved_playbook_path=evolved_path,
    )
    result.should_break = True
