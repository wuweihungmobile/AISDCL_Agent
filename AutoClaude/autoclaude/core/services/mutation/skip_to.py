"""SkipToStrategy（IMutationStrategy 之一）。

驗證 SKIP_TO 目標必須在當前步驟之後（前向跳）。
"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType


class SkipToStrategy:
    def kind(self) -> str:
        return StepMutationType.SKIP_TO.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.SKIP_TO

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        target = mutation.skip_to_step_id
        if not target:
            return False
        for i, t in enumerate(playbook.tasks):
            if t.step_id == target:
                return i > current_idx
        return False
