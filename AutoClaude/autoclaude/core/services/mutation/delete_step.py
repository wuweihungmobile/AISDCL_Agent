"""DeleteStepStrategy（IMutationStrategy 之一）。

禁止刪除「當前正在執行的步驟」（current_idx）以避免狀態機錯亂。
"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType


class DeleteStepStrategy:
    def kind(self) -> str:
        return StepMutationType.DELETE_STEP.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.DELETE_STEP

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        target = mutation.delete_step_id
        if not target:
            return False
        for i, t in enumerate(playbook.tasks):
            if t.step_id == target and i != current_idx:
                playbook.tasks.pop(i)
                return True
        return False
