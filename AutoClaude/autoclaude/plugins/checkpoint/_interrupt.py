"""_interrupt — ESC+F12 中斷 checkpoint 持久化（W3-1c）。

從 ``autoclaude.execution._runner_internals._save_interrupt_checkpoint`` 搬移。

職責：純檔案 I/O，counter 由呼叫端（mixin `_save_interrupt_checkpoint`）從持久化
counter dict 直接傳入；無需透過 EventBus。SD_05 W6 後 PlaybookRunner 不再持有
任何 `_goto_counter_plugin` 直接參照，全走 EventBus 廣播路徑。
"""
from __future__ import annotations

import logging
from typing import Optional

from ...utils.checkpoint_manager import PlaybookCheckpoint

logger = logging.getLogger("autoclaude.plugins.checkpoint")


def save_interrupt_checkpoint_impl(
    plugin,
    playbook,
    playbook_path: str,
    task,
    step_idx: int,
    step_log: list,
    total: int,
    tracker=None,
    attempt: int = 0,
    goto_counter: Optional[dict] = None,
    inject_before_counter: Optional[dict] = None,
    skip_to_counter: Optional[dict] = None,
    completed_step_ids: Optional[list] = None,
    step_evolution_counter: Optional[dict] = None,
) -> None:
    """W3-1c：ESC+F12 中斷時持久化 checkpoint（含 5 個 counter snapshot）。"""
    cp = PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=step_idx,
        step_id=task.step_id,
        total_steps=total,
        project=playbook.project,
        completed_step_log=list(step_log),
        failure_history=tracker.to_checkpoint_records() if tracker else [],
        active_step_attempt=attempt,
        last_correction_prompt=(
            tracker.history[-1].correction_prompt_sent
            if tracker and tracker.history else ""
        ),
        goto_counter=dict(goto_counter) if goto_counter else {},
        inject_before_counter=dict(inject_before_counter) if inject_before_counter else {},
        skip_to_counter=dict(skip_to_counter) if skip_to_counter else {},
        completed_step_ids=list(completed_step_ids) if completed_step_ids else [],
        step_evolution_counter=dict(step_evolution_counter) if step_evolution_counter else {},
    )
    plugin._mgr.save(cp, playbook_path)
    logger.info(
        "ESC+F12 中斷：checkpoint 已儲存於 step %d [%s]（含 %d 筆失敗歷史，"
        "%d 個計數器，%d 個演化計數）",
        step_idx, task.step_id, len(cp.failure_history),
        len(cp.goto_counter) + len(cp.inject_before_counter) + len(cp.skip_to_counter),
        len(cp.step_evolution_counter),
    )
