"""共用工具：從 INJECT_AFTER / INJECT_BEFORE 突變欄位建構新 PlaybookTask。"""
from __future__ import annotations

from ....models.playbook import PlaybookTask
from ....models.step_mutation import StepMutation


def make_task_from_mutation(m: StepMutation) -> PlaybookTask:
    return PlaybookTask(
        step_id=m.new_step_id or "T_INJECTED",
        name=m.new_step_name or "Injected step",
        prompt=m.new_step_prompt or "",
        expected_output_regex=m.new_step_expected_regex,
        evaluator_command=m.new_step_evaluator_command,
        max_retries=m.new_step_max_retries,
    )
