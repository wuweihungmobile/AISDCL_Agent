"""_token_halt — TOKEN_HALT checkpoint + 排程恢復（W3-1b）。

從 ``autoclaude.execution._runner_internals._handle_token_halt`` 搬移
checkpoint 部分（排程 + save + notify hook）。

PlaybookResult 組裝邏輯保留在 mixin（PlaybookResult 屬 _runner_compat，
plugin 不直接 import 避免分層違規），plugin 回傳 (checkpoint, scheduled_resume_at) tuple。
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from ...utils.checkpoint_manager import PlaybookCheckpoint

logger = logging.getLogger("autoclaude.plugins.checkpoint")


def handle_token_halt_impl(
    plugin,
    playbook,
    playbook_path: str,
    task,
    step_idx: int,
    peak_token_pct: float,
    step_log: list,
    total: int,
    halt_threshold_pct: float,
    resume_delay_minutes: int,
    tracker=None,
    attempt: int = 0,
    goto_counter: Optional[dict] = None,
    inject_before_counter: Optional[dict] = None,
    skip_to_counter: Optional[dict] = None,
    completed_step_ids: Optional[set] = None,
    step_evolution_counter: Optional[dict] = None,
    notify_callback: Optional[Callable[[str, str], None]] = None,
    token_logger_callback: Optional[Callable[[str, str, float, str, str], None]] = None,
) -> PlaybookCheckpoint:
    """W3-1b：TOKEN_HALT 儲存 checkpoint + 排程恢復 + notify；回傳 checkpoint。

    PlaybookResult 組裝由呼叫端（mixin）處理（plugin 不依賴 PlaybookResult）。
    """
    logger.warning(
        "=== STATE: TOKEN_HALT | [%s] context %.0f%% >=  halt 門檻 %.0f%% ===",
        task.step_id, peak_token_pct, halt_threshold_pct,
    )
    cp = PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=step_idx,
        step_id=task.step_id,
        total_steps=total,
        project=playbook.project,
        completed_step_log=list(step_log),
        peak_token_pct=peak_token_pct,
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
    if resume_delay_minutes > 0:
        plugin._mgr.schedule_resume(cp, resume_delay_minutes)
    plugin._mgr.save(cp, playbook_path)

    if tracker and tracker.history:
        logger.info(
            "Gap-007-A: TOKEN_HALT checkpoint 包含 %d 筆失敗歷史（attempt_offset=%d）",
            len(tracker.history), attempt,
        )

    if token_logger_callback is not None:
        token_logger_callback(
            playbook.project, task.step_id,
            peak_token_pct, "halt_checkpoint", "in_progress",
        )
    if notify_callback is not None:
        notify_callback(
            "AutoClaude — Context 達限，已儲存進度",
            f"[{task.step_id}] Context {peak_token_pct:.0f}%，"
            f"將於 {resume_delay_minutes} 分鐘後繼續",
        )
    return cp
