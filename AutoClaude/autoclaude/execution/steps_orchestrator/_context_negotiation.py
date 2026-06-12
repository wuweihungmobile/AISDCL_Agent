"""_context_negotiation.py — CONTEXT_NEGOTIATION 階段處理（SD_06 W2 G2 階段 B 拆出）。

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組 each ≤ 250 LOC）
  - SD06_Execution_Guide.md W2 — _impl.py 拆分計畫

從 run_steps_impl 抽出 line 50-86 區塊（37 行）。回傳 (continue, early_return)：
  - continue=True 表示 caller 應繼續執行主 while loop
  - early_return 非 None 表示 CONTEXT_NEGOTIATION 失敗 / token halt / compact 失敗，
    caller 應立即 return 此 PlaybookResult
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from ...perception.pty_wrapper import strip_ansi
from ..types import PlaybookResult

if TYPE_CHECKING:
    from ...models.playbook import Playbook
    from ..playbook_runner import PlaybookRunner
    from ..workflow_detector import WorkflowType

logger = logging.getLogger("autoclaude.execution.playbook")


def handle_context_negotiation(
    runner: "PlaybookRunner",
    playbook: "Playbook",
    playbook_path: str,
    is_first_prompt: bool,
    start_idx: int,
    workflow: "WorkflowType",
    total: int,
) -> tuple[bool, Optional[PlaybookResult]]:
    """處理 CONTEXT_NEGOTIATION 階段。

    Returns:
        (is_first_prompt_after, early_return):
          - is_first_prompt_after: 完成後 caller 應更新的 is_first_prompt 值
          - early_return: 若非 None，caller 應立即 return；None 表示繼續主 loop
    """
    if not (playbook.context_negotiation and is_first_prompt and start_idx == 0):
        return is_first_prompt, None

    cn = playbook.context_negotiation
    logger.info("=== STATE: CONTEXT_NEGOTIATION | 送出初始 Prompt ===")
    if runner._dry_run:
        logger.debug("[dry-run] context_negotiation 略過")
        return False, None

    cn_out = runner._execute_prompt(
        prompt=runner._prepend_global_goal(cn.prompt, playbook.global_goal),
        maintain_context=False,
        timeout=runner._cfg.playbook.step_timeout_seconds,
        step_label="context_negotiation",
    )
    if cn.expected_keyword and cn.expected_keyword not in strip_ansi(cn_out.text):
        return is_first_prompt, PlaybookResult(
            False, 0, total,
            f"CONTEXT_NEGOTIATION 失敗:未找到 expected_keyword={cn.expected_keyword!r}",
            workflow, [],
        )
    logger.info("CONTEXT_NEGOTIATION 成功,expected_keyword=%r 已找到", cn.expected_keyword)

    if runner._cfg.token_guard.enabled:
        if cn_out.triggered_halt:
            logger.warning(
                "CONTEXT_NEGOTIATION 後 context 達 halt 門檻,儲存 checkpoint 並暫停"
            )
            return is_first_prompt, runner._handle_token_halt(
                playbook, playbook_path,
                playbook.tasks[0], 0,
                cn_out, [], workflow, total,
            )
        if cn_out.triggered_compact:
            logger.info("CONTEXT_NEGOTIATION 後 context 達 compact 門檻,主任務開始前壓縮")
            if not runner._send_compact(False, global_goal=playbook.global_goal):
                return is_first_prompt, PlaybookResult(
                    False, 0, total, "Gap-008-E: compact 連續失敗 2 次,TOKEN_HALT",
                    workflow, [],
                )
    return False, None
