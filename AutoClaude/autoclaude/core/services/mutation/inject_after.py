"""InjectAfterStrategy（IMutationStrategy 之一）。"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType
from ._helpers import make_task_from_mutation


class InjectAfterStrategy:
    def kind(self) -> str:
        return StepMutationType.INJECT_AFTER.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.INJECT_AFTER

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        if not mutation.new_step_id or not mutation.new_step_prompt:
            return False
        if not (0 <= current_idx < len(playbook.tasks)):
            return False
        playbook.tasks.insert(current_idx + 1, make_task_from_mutation(mutation))
        return True
