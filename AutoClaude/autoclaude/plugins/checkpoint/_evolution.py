"""_evolution — 演化後 checkpoint 持久化（W3-1a）。

從 ``autoclaude.execution._runner_internals._save_evolution_resume_checkpoint`` 搬移。

Gap-041：演化後重啟 checkpoint — 已完成步驟可跳過、step_evolution_counter
持久化以防止跨 session 重複演化（Gap-048）。
"""
from __future__ import annotations

import logging
from typing import Optional

from ...utils.checkpoint_manager import PlaybookCheckpoint

logger = logging.getLogger("autoclaude.plugins.checkpoint")


def save_evolution_resume_checkpoint_impl(
    plugin,
    evolved_path: str,
    playbook,
    step_log: list,
    completed_step_ids,
    step_evolution_counter: Optional[dict] = None,
    alert_ladder: Optional[dict] = None,
) -> bool:
    """W3-1a：Gap-041 演化後儲存 checkpoint；回傳是否成功。"""
    try:
        _first_task_id = playbook.tasks[0].step_id if playbook.tasks else "T01"
        _cp = PlaybookCheckpoint(
            playbook_path=evolved_path,
            step_idx=0,
            step_id=_first_task_id,
            total_steps=len(playbook.tasks),
            project=playbook.project,
            completed_step_log=list(step_log),
            completed_step_ids=list(completed_step_ids),
            step_evolution_counter=(
                dict(step_evolution_counter) if step_evolution_counter else {}
            ),
            alert_ladder=dict(alert_ladder) if alert_ladder else {},
        )
        plugin._mgr.save(_cp, evolved_path)
        logger.info(
            "Gap-041 | 已儲存演化後 checkpoint（%d 個已完成步驟可跳過）: %s",
            len(completed_step_ids), evolved_path,
        )
        return True
    except Exception as exc:
        logger.error(
            "Gap-041 | 演化後 checkpoint 儲存失敗（將回退 fresh=True）: %s",
            exc,
        )
        return False
