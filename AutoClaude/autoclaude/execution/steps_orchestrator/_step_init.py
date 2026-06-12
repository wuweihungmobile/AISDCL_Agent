"""_step_init.py — 單一 step 進入主迴圈前的初始化（SD_06 W2 G2 階段 B-1 拆出）。

對應 SD_06 W2 G2 階段 B：從 _impl.py 主 while loop 抽出 3 個獨立邏輯片段，
減少 _impl.py LOC + 提升可讀性。

3 個 helper：
  - build_cross_step_hint：跨步驟污染偵測 + GOTO 重訪 hint 合併
  - init_step_tracker：FailureTracker 建立（含 GOTO 熱啟動 + checkpoint 恢復）
  - check_hotkey_and_save：ESC+F12 中斷偵測 + interrupt checkpoint 儲存
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from ..failure_tracker import FailureTracker
from ..types import PlaybookResult

if TYPE_CHECKING:
    from ...models.playbook import Playbook, PlaybookTask
    from ...utils.checkpoint_manager import PlaybookCheckpoint
    from ..playbook_runner import PlaybookRunner
    from ..workflow_detector import WorkflowType

logger = logging.getLogger("autoclaude.execution.playbook")


def build_cross_step_hint(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    task: "PlaybookTask",
    step_idx: int,
    prev_step_idx: int,
) -> Optional[str]:
    """合併跨步驟污染警告 + GOTO 重訪 hint（line 82-101 抽出）。"""
    from ..playbook_runner import _pr

    cross_hint: Optional[str] = None
    if not runner._dry_run and step_idx > 0:
        prev_task = playbook.tasks[step_idx - 1]
        cross_hint = _pr().CrossStepStateValidator().validate_before_step(task, prev_task)
        if cross_hint:
            logger.warning(
                "=== Gap-010-C | [%s] 偵測到跨步驟污染,將警告注入首次 Prompt ===",
                task.step_id,
            )

    if prev_step_idx >= 0 and step_idx < prev_step_idx and not runner._dry_run:
        logger.info("=== Gap-027 | GOTO 重訪 [%s],注入 context clean hint ===", task.step_id)
        goto_revisit_hint = (
            f"⚠️ 重要提示（GOTO 重訪）:系統已判斷需要重新執行步驟 {task.step_id}。\n"
            f"請忽略此步驟之前所有失敗的修改嘗試,從當前程式碼狀態重新分析並修正。\n"
            f"優先使用 Read 工具確認當前檔案狀態,不要假設之前的修改已套用。\n\n"
        )
        cross_hint = (goto_revisit_hint + cross_hint) if cross_hint else goto_revisit_hint
    return cross_hint


def init_step_tracker(
    task: "PlaybookTask",
    step_trackers: dict,
    resume_checkpoint: Optional["PlaybookCheckpoint"],
    playbook: "Playbook",
) -> tuple[FailureTracker, int, Optional["PlaybookCheckpoint"]]:
    """FailureTracker 建立（line 103-130 抽出）。

    Returns:
        (tracker, attempt_offset, new_resume_checkpoint):
          - tracker: 新建或從 checkpoint 重建的 FailureTracker
          - attempt_offset: checkpoint 恢復後的起始 attempt 編號
          - new_resume_checkpoint: 若已套用則回 None（避免後續步驟重複套用）
    """
    if task.step_id in step_trackers:
        prev_tracker = step_trackers[task.step_id]
        tracker = FailureTracker(task.step_id)
        tracker._tried_strategies = prev_tracker._tried_strategies.copy()
        logger.info(
            "=== Gap-013-A | [%s] GOTO 重訪熱啟動,繼承 %d 個已嘗試策略 ===",
            task.step_id, len(tracker._tried_strategies),
        )
    else:
        tracker = FailureTracker(task.step_id)

    attempt_offset = 0
    if (
        resume_checkpoint is not None
        and resume_checkpoint.failure_history
        and resume_checkpoint.step_id == task.step_id
    ):
        tracker = FailureTracker.from_records(task.step_id, resume_checkpoint.failure_history)
        attempt_offset = min(
            resume_checkpoint.active_step_attempt,
            (task.max_retries if task.max_retries is not None
             else playbook.global_invariants.max_retries_per_step),
        )
        logger.info(
            "=== Gap-007-A | [%s] 從 checkpoint 重建 FailureTracker: %d 筆歷史,attempt_offset=%d ===",
            task.step_id, len(tracker.history), attempt_offset,
        )
        resume_checkpoint = None
    step_trackers[task.step_id] = tracker
    return tracker, attempt_offset, resume_checkpoint


def check_hotkey_and_save(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    playbook_path: str,
    task: "PlaybookTask",
    step_idx: int,
    step_log: list,
    total: int,
    tracker: FailureTracker,
    attempt_offset: int,
    goto_counter: dict,
    inject_before_counter: dict,
    skip_to_counter: dict,
    completed_step_ids: set,
    step_evolution_counter: dict,
    workflow: "WorkflowType",
) -> Optional[PlaybookResult]:
    """ESC+F12 中斷檢查（line 132-145 抽出）。觸發則 save_interrupt + 回 PlaybookResult。"""
    if not runner._hotkey.triggered:
        return None
    runner._checkpoint_plugin.save_interrupt_checkpoint(
        playbook, playbook_path, task, step_idx, step_log, total,
        tracker=tracker, attempt=attempt_offset,
        goto_counter=goto_counter,
        inject_before_counter=inject_before_counter,
        skip_to_counter=skip_to_counter,
        completed_step_ids=list(completed_step_ids),
        step_evolution_counter=step_evolution_counter,
    )
    return PlaybookResult(
        False, len(step_log), total, "使用者 ESC+F12 中斷（已儲存中斷點）",
        workflow, step_log,
    )
