"""compact_controller.py — _send_compact 拆解承接模組（SD_06 W2-T2-7 / T2-8）。

對應：
  - SD_Improving_06.md v1.2 §4 W2-4（compact 邏輯下沉）
  - SD06_Execution_Guide.md W2 T2-7 / T2-8

設計原則：
  - prompt 組裝走 token_guard.compactor.build_compact_prompt（W2-T2-13 已拆出）
  - 失敗計數走 token_guard.compactor.CompactFailureState（SSOT）
  - 實際 PTY 執行走 mixin._execute_prompt（已下沉至 prompt_dispatcher）
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..models.playbook import PlaybookTask
    from .playbook_runner import PlaybookRunner

logger = logging.getLogger("autoclaude.execution.playbook")


def send_compact_impl(
    runner: "PlaybookRunner",
    is_first: bool,
    failure_summary: str = "",
    task: Optional["PlaybookTask"] = None,
    attempt: int = 0,
    global_goal: Optional[str] = None,
) -> bool:
    """SD_06 W2-T2-8：_send_compact 全文下沉（SD_05 W2-1d + M-2 雙寫拔除）。

    - prompt 構造 → TokenGuardPlugin.build_compact_prompt（純函式）
    - PTY 執行 → runner._execute_prompt（thin shim 至 prompt_dispatcher）
    - compact 後處理 → TokenGuardPlugin.process_compact_result（SSOT 計數器）
    """
    if is_first:
        return False
    logger.info("發送 /compact 指令節省 Token（帶結構化壓縮提示）")

    compact_prompt = runner._token_guard_plugin.build_compact_prompt(
        task=task, attempt=attempt, failure_summary=failure_summary,
        global_goal=global_goal,
        global_goal_anchor_chars=runner._cfg.playbook.global_goal_anchor_chars,
    )
    compact_out = runner._execute_prompt(
        prompt=compact_prompt,
        maintain_context=True,
        timeout=60,
        step_label="compact",
    )
    ok = runner._token_guard_plugin.process_compact_result(
        triggered_compact=compact_out.triggered_compact,
        peak_token_pct=compact_out.peak_token_pct,
    )
    if compact_out.triggered_compact:
        logger.warning(
            "/compact 後 context 仍達 %.0f%%（連續失敗 %d 次）",
            compact_out.peak_token_pct,
            runner._token_guard_plugin.compact_failure_count,
        )
        if not ok:
            logger.error(
                "=== Gap-008-E | 連續 compact 失敗 %d 次，強制 TOKEN_HALT ===",
                runner._token_guard_plugin.compact_failure_count,
            )
    return ok and not compact_out.triggered_compact
