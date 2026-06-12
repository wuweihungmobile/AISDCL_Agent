"""CounterSnapshot — 4 個跨 Session 計數器的快照 DTO（Gap-042/048/049）。

從 autoclaude.plugins.goto_counter_plugin 移出，作為共享數據模型，
避免 plugin-to-plugin 直接 import（R-3 M5 架構修正）。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CounterSnapshot:
    """4 個計數器的快照，供 CheckpointPlugin 持久化與 GotoCounterPlugin 還原。"""
    goto_counter: dict[str, int] = field(default_factory=dict)
    inject_before_counter: dict[str, int] = field(default_factory=dict)
    skip_to_counter: dict[str, int] = field(default_factory=dict)
    step_evolution_counter: dict[str, int] = field(default_factory=dict)
