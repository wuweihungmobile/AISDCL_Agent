"""autoclaude.plugins — Layer 3 Plugin 集合（SD_Improving_01.md v1.1 §3.5）。

Phase 3 遷移順序（SD_Improving_02.md v1.1 §2.5）：
  W5: NotificationPlugin / HotkeyPlugin / PreRunValidatorPlugin
  W6: CrossStepValidatorPlugin / KnowledgeBasePlugin / GotoCounterPlugin
  W7: GlobalGoalAnchorPlugin / TokenGuardPlugin
  W8: CheckpointPlugin
  W9: ConvergencePlugin
  W10: EvolutionPlugin
  W11: GoalSynthesisPlugin

每個 Plugin ≤ 250 行（行數預算 CI 強制，01 v1.1 §3.13.1）。
"""
from .notification_plugin import NotificationPlugin
from .hotkey_plugin import HotkeyPlugin
from .pre_run_validator_plugin import PreRunValidatorPlugin
from .cross_step_validator_plugin import CrossStepValidatorPlugin
from .knowledge_base_plugin import KnowledgeBasePlugin
from .goto_counter_plugin import GotoCounterPlugin, CounterSnapshot
from .global_goal_anchor_plugin import GlobalGoalAnchorPlugin
from .token_guard_plugin import TokenGuardPlugin
from .checkpoint_plugin import CheckpointPlugin
from .convergence_plugin import ConvergencePlugin
from .evolution_plugin import EvolutionPlugin
from .goal_synthesis_plugin import GoalSynthesisPlugin
from .fast_path_plugin import FastPathPlugin
from .playbook_persistence_plugin import PlaybookPersistencePlugin
from .sdd_governance_plugin import SddGovernancePlugin

__all__ = [
    # W5
    "NotificationPlugin",
    "HotkeyPlugin",
    "PreRunValidatorPlugin",
    # W6
    "CrossStepValidatorPlugin",
    "KnowledgeBasePlugin",
    "GotoCounterPlugin",
    "CounterSnapshot",
    # W7
    "GlobalGoalAnchorPlugin",
    "TokenGuardPlugin",
    # W8
    "CheckpointPlugin",
    # W9
    "ConvergencePlugin",
    # W10
    "EvolutionPlugin",
    # W11
    "GoalSynthesisPlugin",
    # SD_Improving_05 W4
    "FastPathPlugin",
    "PlaybookPersistencePlugin",
    # AutoSDD_improving_01 W6（PRIORITY=45）
    "SddGovernancePlugin",
]
