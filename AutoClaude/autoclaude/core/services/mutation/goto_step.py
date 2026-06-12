"""GotoStepStrategy（IMutationStrategy 之一）。

注意：GOTO_STEP 不修改 playbook，僅驗證目標 step_id 存在；
實際的 step_idx 跳轉由 Kernel 從 playbook 中尋找對應 task 完成。
"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType


class GotoStepStrategy:
    def kind(self) -> str:
        return StepMutationType.GOTO_STEP.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.GOTO_STEP

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        target = mutation.goto_step_id
        if not target:
            return False
        return any(t.step_id == target for t in playbook.tasks)
