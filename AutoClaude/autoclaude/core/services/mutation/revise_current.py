"""ReviseCurrentStrategy（IMutationStrategy 之一）。"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType


class ReviseCurrentStrategy:
    def kind(self) -> str:
        return StepMutationType.REVISE_CURRENT.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.REVISE_CURRENT

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        if not mutation.revised_prompt:
            return False
        if not (0 <= current_idx < len(playbook.tasks)):
            return False
        playbook.tasks[current_idx].prompt = mutation.revised_prompt
        return True
