"""NoOpStrategy（IMutationStrategy fallback）。"""
from __future__ import annotations

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation


class NoOpStrategy:
    """fallback：未識別的突變類型（如 CONDITIONAL 在解析後仍未匹配子類型時）。"""

    def kind(self) -> str:
        return "NO_OP"

    def can_handle(self, mutation: StepMutation) -> bool:
        return True

    def apply(self, mutation: StepMutation, playbook: Playbook, current_idx: int) -> bool:
        return True
