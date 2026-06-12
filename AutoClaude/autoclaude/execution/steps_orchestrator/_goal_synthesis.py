"""_goal_synthesis.py — GOAL_SYNTHESIS 步驟注入處理（SD_06 W2 G2 階段 B-2 拆出）。

對應：
  - Gap-014-C / Gap-030：全部步驟完成後，若 global_goal 未達成則動態注入
    GOAL_SYNTHESIS 補完步驟

從 _impl.py 主 while loop 抽出 line 723-750 區塊（28 行）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...models.playbook import PlaybookTask

if TYPE_CHECKING:
    from ...models.playbook import Playbook
    from ..playbook_runner import PlaybookRunner

logger = logging.getLogger("autoclaude.execution.playbook")


def maybe_inject_goal_synthesis(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    step_idx: int,
    step_log: list,
    goal_synthesis_injected: bool,
) -> tuple[bool, int]:
    """完成所有步驟後驗證 global_goal 達成；若未達成則注入 GOAL_SYNTHESIS 步驟。

    Returns:
        (new_goal_synthesis_injected, new_total):
          - new_goal_synthesis_injected: 更新後旗標
          - new_total: 更新後 total（若注入則 += 1，否則不變）
    """
    if not (
        step_idx >= len(playbook.tasks)
        and not goal_synthesis_injected
        and playbook.global_goal
        and runner._cfg.playbook.goal_synthesis_enabled
        and not runner._dry_run
    ):
        return goal_synthesis_injected, len(playbook.tasks)

    goal_synthesis_injected = True
    logger.info("=== Gap-014-C | 全局目標驗證開始 ===")
    goal_result = runner._validate_global_goal_achievement(
        playbook, step_log, playbook.global_goal,
    )
    if goal_result is None:
        return goal_synthesis_injected, len(playbook.tasks)

    completion_prompt, suggested_evaluator = goal_result
    logger.info(
        "=== Gap-014-C / Gap-030 | 目標未完全達成,注入 GOAL_SYNTHESIS 步驟"
        "（evaluator=%s）===", suggested_evaluator,
    )
    synth_task = PlaybookTask(
        step_id="GOAL_SYNTHESIS",
        name="全局目標最終補完與驗證",
        prompt=completion_prompt,
        expected_output_regex=r"(?:目標達成|DONE|完成|verified|passed)",
        evaluator_command=suggested_evaluator,
        max_retries=2,
    )
    playbook.tasks.append(synth_task)
    return goal_synthesis_injected, len(playbook.tasks)
