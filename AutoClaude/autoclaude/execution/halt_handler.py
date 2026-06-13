"""halt_handler.py — _handle_token_halt 拆解承接模組（SD_06 W2-T2-7 / T2-8）。

對應：
  - SD_Improving_06.md v1.2 §4 W2-4（halt_handler.py）
  - SD06_Execution_Guide.md W2 T2-7 / T2-8

設計原則：
  - 真正 checkpoint 邏輯由 CheckpointPlugin.handle_token_halt SSOT 承擔（SD_05 W3-1b）
  - 本模組僅負責 PlaybookResult 組裝（_runner_compat dataclass，plugin 不可依賴）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .types import PlaybookResult, _StepOutput

if TYPE_CHECKING:
    from ..models.playbook import Playbook, PlaybookTask
    from .failure_tracker import FailureTracker
    from .playbook_runner import PlaybookRunner
    from .workflow_detector import WorkflowType


def handle_token_halt_impl(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    playbook_path: str,
    task: "PlaybookTask",
    step_idx: int,
    step_out: _StepOutput,
    step_log: list[str],
    workflow: "WorkflowType",
    total: int,
    tracker: Optional["FailureTracker"] = None,
    attempt: int = 0,
    goto_counter: Optional[dict] = None,
    inject_before_counter: Optional[dict] = None,
    skip_to_counter: Optional[dict] = None,
    completed_step_ids: Optional[set] = None,
    step_evolution_counter: Optional[dict] = None,
    alert_ladder: Optional[dict] = None,
) -> PlaybookResult:
    """SD_06 W2-T2-8：_handle_token_halt 全文下沉。

    委派 checkpoint 部分至 CheckpointPlugin.handle_token_halt；PlaybookResult 組裝
    由本函式承擔（PlaybookResult 屬 _runner_compat，plugin 不依賴此資料類別）。
    """
    tg = runner._cfg.token_guard
    cp = runner._checkpoint_plugin.handle_token_halt(
        playbook=playbook,
        playbook_path=playbook_path,
        task=task,
        step_idx=step_idx,
        peak_token_pct=step_out.peak_token_pct,
        step_log=step_log,
        total=total,
        halt_threshold_pct=tg.halt_threshold_pct,
        resume_delay_minutes=tg.resume_delay_minutes,
        tracker=tracker,
        attempt=attempt,
        goto_counter=goto_counter,
        inject_before_counter=inject_before_counter,
        skip_to_counter=skip_to_counter,
        completed_step_ids=completed_step_ids,
        step_evolution_counter=step_evolution_counter,
        alert_ladder=alert_ladder,
        notify_callback=runner._notify,
        token_logger_callback=runner._token_logger.record,
    )
    return PlaybookResult(
        False, len(step_log), total,
        f"Context {step_out.peak_token_pct:.0f}% 達限，已儲存檢查點",
        workflow, step_log,
        halt_for_token=True,
        scheduled_resume_at=cp.scheduled_resume_at,
    )
