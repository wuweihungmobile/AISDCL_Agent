"""_loop_state.py — 主 while loop 狀態初始化（SD_06 W2 G2 階段 B 拆出）。

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組 each ≤ 250 LOC）
  - SD06_Execution_Guide.md W2 — _impl.py 拆分計畫

從 run_steps_impl 抽出 line 87-137 區塊（51 行）— counter restore、
mutation_log 復原、skip_completed_ids 計算、KB 預播種等迴圈前置初始化。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..error_classifier import ErrorClass

if TYPE_CHECKING:
    from ...models.playbook import Playbook
    from ...utils.checkpoint_manager import PlaybookCheckpoint
    from ..failure_tracker import FailureTracker
    from ..playbook_runner import PlaybookRunner

logger = logging.getLogger("autoclaude.execution.playbook")


@dataclass
class LoopState:
    """主 while loop 起始狀態快照（live alias 至 GotoCounterPlugin 內部 dict）。"""
    goto_counter: dict
    inject_before_counter: dict
    skip_to_counter: dict
    step_evolution_counter: dict
    step_trackers: dict = field(default_factory=dict)
    mutation_log: list = field(default_factory=list)
    completed_step_ids: set = field(default_factory=set)
    skip_completed_ids: set = field(default_factory=set)
    goal_synthesis_injected: bool = False
    # F-B1/F-B2（ADR-AGT-004）：AlertLadder 階梯計數 + streak 恢復快照
    alert_ladder_state: dict = field(default_factory=dict)


def initialize_loop_state(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    resume_checkpoint: "PlaybookCheckpoint | None",
) -> LoopState:
    """SD_06 W2 G2 階段 B：counter restore + mutation_log 復原 + KB 預播種。

    SD_05 W1 Step-1 counter SSOT 遷移：4 個計數器資料儲存點完全改由
    GotoCounterPlugin 維護；local 變數為 plugin 內部 dict 的 alias（live reference）。
    """
    from ...models.counter_snapshot import CounterSnapshot

    if resume_checkpoint:
        runner._goto_counter_plugin.restore(CounterSnapshot(
            goto_counter=dict(resume_checkpoint.goto_counter),
            inject_before_counter=dict(resume_checkpoint.inject_before_counter),
            skip_to_counter=dict(resume_checkpoint.skip_to_counter),
            step_evolution_counter=dict(resume_checkpoint.step_evolution_counter),
        ))
    else:
        runner._goto_counter_plugin.restore(CounterSnapshot())

    state = LoopState(
        goto_counter=runner._goto_counter_plugin.goto_counter,
        inject_before_counter=runner._goto_counter_plugin.inject_before_counter,
        skip_to_counter=runner._goto_counter_plugin.skip_to_counter,
        step_evolution_counter=runner._goto_counter_plugin.step_evolution_counter,
    )

    if playbook.evolution_metadata and playbook.evolution_metadata.mutation_log:
        state.mutation_log = list(playbook.evolution_metadata.mutation_log)
        logger.info("Gap-024-C | 恢復演化版 mutation_log: %d 筆", len(state.mutation_log))

    if resume_checkpoint:
        # F-B1：舊 checkpoint 無 alert_ladder 屬性 → getattr 補空 dict（additive 相容）
        state.alert_ladder_state = dict(getattr(resume_checkpoint, "alert_ladder", {}) or {})
        state.skip_completed_ids = set(resume_checkpoint.completed_step_ids)
        if state.skip_completed_ids:
            logger.info(
                "Gap-041 | 演化後重啟:將跳過 %d 個已完成步驟: %s",
                len(state.skip_completed_ids), list(state.skip_completed_ids),
            )

    if playbook.evolution_metadata and playbook.evolution_metadata.escalated_step_ids:
        for esc_id in playbook.evolution_metadata.escalated_step_ids:
            pre_id = f"{esc_id}_PRE"
            kb_key = f"{ErrorClass.IMPORT.value}:{pre_id}:env_setup"
            if not runner._knowledge_base.query(kb_key):
                runner._knowledge_base.record_success(
                    kb_key, "PINPOINT", pre_id, error_class=ErrorClass.IMPORT.value,
                )
                logger.debug("Gap-045 | 為 %s 預播種 KB 記錄 (key=%s)", pre_id, kb_key)

    return state
