"""_escalation — ESCALATION dump 持久化（W3-1d）。

從 ``autoclaude.execution._runner_internals._save_escalation_dump`` 搬移
持久化部分（dump.save 檔案 I/O）。

notify_escalation（業務動作）改由 EvolutionPlugin 訂閱
``ON_ESCALATION_DUMP_REQUEST`` phase 處理；CheckpointPlugin 僅負責檔案落地，
維持單一職責。

但 backward compat 期間（W3~W6），mixin 仍直接呼叫此方法並期望 notify
一併發出 → notify_callback 由呼叫端注入；W6 後可改為純 dump.save。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from ...models.escalation import EscalationDump

logger = logging.getLogger("autoclaude.plugins.checkpoint")


def save_escalation_dump_impl(
    plugin,
    tracker,
    task,
    playbook_path: str,
    final_eval_output: str,
    checkpoint_dir: str,
    log_dir: str,
    human_hint: str = "",
    notify_callback: Optional[Callable[..., None]] = None,
) -> EscalationDump:
    """W3-1d：組裝 EscalationDump + 持久化 + 觸發 notify。

    SD_05 W3 三方審查 Arch-C1 / SD-C1 修復：plugin._last_dump_path 記錄 dump.save()
    真實回傳路徑（可能含 timestamp + .md 副檔名），供 on_escalation_dump_request
    回傳給 EventBus 的 EscalationDumpedResult.dump_path 使用，避免手構字串失真。

    cfg 不再注入 plugin（保持 plugin 與 infra 解耦），改為 checkpoint_dir / log_dir
    參數直傳。notify_callback 接收 (title, message, dump_path) 參數。
    """
    last_attempt = max(0, len(tracker.history) - 1)
    last_log_path = str(
        Path(log_dir) / f"playbook_{task.step_id}_attempt{last_attempt}.log"
    )
    checkpoint_resume_hint = f"autoclaude {playbook_path}"
    dump = EscalationDump(
        playbook_path=playbook_path,
        step_id=task.step_id,
        step_name=task.name,
        total_attempts=len(tracker.history),
        failure_chain=tracker.to_failure_chain(),
        final_eval_output=final_eval_output,
        is_stuck=tracker.is_stuck(),
        is_diverging=tracker.is_diverging(),
        suspect_test_file=tracker.suspect_test_file_error(),
        is_oscillating=tracker.is_oscillating(),
        is_worsening=tracker.is_worsening(),
        suspect_assertion_mismatch=tracker.suspect_assertion_baseline_mismatch(),
        human_hint=human_hint,
        last_log_path=last_log_path,
        checkpoint_resume_hint=checkpoint_resume_hint,
    )
    saved_path: str = ""
    try:
        saved_path = str(dump.save(checkpoint_dir))
        logger.info("EscalationDump 已儲存: %s", saved_path)
    except Exception as exc:
        logger.warning("EscalationDump 儲存失敗: %s", exc)
        saved_path = ""

    # SD_05 W3 Arch-C1 / SD-C1 修：記錄真實 dump path 至 plugin（供 phase handler 取用）
    plugin._last_dump_path = saved_path

    if notify_callback is not None:
        # SD_05 W3 SD-M1 修：失敗時傳 dump_path=None（而非空字串）以便 UI/CLI 區分
        cb_path = saved_path if saved_path else None
        notify_callback(
            title=f"AutoClaude — ESCALATION [{task.step_id}]",
            message=human_hint or f"步驟 [{task.step_id}] {task.name} 發生 ESCALATION",
            dump_path=cb_path,
        )
    return dump
