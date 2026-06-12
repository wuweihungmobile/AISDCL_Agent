"""_dispatcher.py — MutationCtx + apply_single_mutation_full_impl 主分發。

對應 SD_06 W2 G2 deferred：將原 mutation_applier.py 328 LOC 拆 4 子模組
（各 ≤ 200 LOC）。本模組為對外公開 API 入口。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...models.step_mutation import StepMutationType
from ..types import _MutationResult

if TYPE_CHECKING:
    from ...models.playbook import Playbook, PlaybookTask
    from ...models.step_mutation import StepMutation
    from ..playbook_runner import PlaybookRunner


@dataclass
class MutationCtx:
    """打包 mutation 套用所需的所有 runtime 上下文（避免 16 參數列表反覆傳遞）。"""
    runner: "PlaybookRunner"
    playbook: "Playbook"
    playbook_path: str
    task: "PlaybookTask"
    step_idx: int
    step_log: list
    mutation_log: list
    attempt: int
    inject_before_counter: dict
    goto_counter: dict
    skip_to_counter: dict
    workflow: object
    total: int
    tracker: object
    eval_output: str


def apply_single_mutation_full_impl(
    runner: "PlaybookRunner",
    mutation: "StepMutation",
    playbook: "Playbook",
    playbook_path: str,
    task: "PlaybookTask",
    step_idx: int,
    step_log: list,
    _mutation_log: list,
    attempt: int,
    _inject_before_counter: dict,
    _goto_counter: dict,
    _skip_to_counter: dict,
    workflow,
    total: int,
    tracker,
    eval_output: str,
) -> _MutationResult:
    """SD_06 W2-T2-4：dispatch 至 6 種 StepMutationType handler。"""
    import logging
    ctx = MutationCtx(
        runner=runner, playbook=playbook, playbook_path=playbook_path,
        task=task, step_idx=step_idx, step_log=step_log,
        mutation_log=_mutation_log, attempt=attempt,
        inject_before_counter=_inject_before_counter,
        goto_counter=_goto_counter, skip_to_counter=_skip_to_counter,
        workflow=workflow, total=total, tracker=tracker, eval_output=eval_output,
    )
    result = _MutationResult()

    if mutation.mutation_type == StepMutationType.REVISE_CURRENT and mutation.revised_prompt:
        from ._simple_mutations import handle_revise_current
        handle_revise_current(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.INJECT_AFTER and mutation.new_step_prompt:
        from ._simple_mutations import handle_inject_after
        handle_inject_after(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.DELETE_STEP and mutation.delete_step_id:
        from ._simple_mutations import handle_delete_step
        handle_delete_step(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.INJECT_BEFORE and mutation.new_step_prompt:
        from ._complex_mutations import handle_inject_before
        handle_inject_before(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.GOTO_STEP and mutation.goto_step_id:
        from ._complex_mutations import handle_goto_step
        handle_goto_step(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.SKIP_TO and mutation.skip_to_step_id:
        from ._simple_mutations import handle_skip_to
        handle_skip_to(ctx, mutation, result)
    elif mutation.mutation_type == StepMutationType.CONDITIONAL:
        from ._conditional import handle_conditional
        handle_conditional(ctx, mutation, result)
    else:
        logging.getLogger("autoclaude.execution.playbook").warning(
            "=== Gap-019-B | 突變類型 %s 不支援（破壞性突變需單獨使用），略過 ===",
            mutation.mutation_type,
        )

    return result
