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
from .checkpoint_plugin import CheckpointPlugin
from .convergence_plugin import ConvergencePlugin
from .cross_step_validator_plugin import CrossStepValidatorPlugin
from .evolution_plugin import EvolutionPlugin
from .fast_path_plugin import FastPathPlugin
from .global_goal_anchor_plugin import GlobalGoalAnchorPlugin
from .goal_progress_plugin import GoalProgressPlugin
from .goal_synthesis_plugin import GoalSynthesisPlugin
from .goto_counter_plugin import CounterSnapshot, GotoCounterPlugin
from .hotkey_plugin import HotkeyPlugin
from .knowledge_base_plugin import KnowledgeBasePlugin
from .notification_plugin import NotificationPlugin
from .playbook_persistence_plugin import PlaybookPersistencePlugin
from .pre_run_validator_plugin import PreRunValidatorPlugin
from .preference_memory_plugin import PreferenceMemoryPlugin
from .sdd_governance_plugin import SddGovernancePlugin
from .token_guard_plugin import TokenGuardPlugin

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
    # Improving_012 Phase 1（F-C1 / F-C2，皆 PRIORITY=50 tie-breaker 群尾端）
    "PreferenceMemoryPlugin",
    "GoalProgressPlugin",
]
