"""IEvaluator — 步驟成功評估的 Port。

對應 SD_Improving_01.md v1.1 §3.4 / SD_Improving_02.md v1.1 §1.2。

簽章與 PlaybookRunner._evaluate 對齊（Frozen Surface #1）：
  evaluate(task, output) -> (failure_reason, eval_output, exit_code)
  - 成功：(None, "", 0)
  - 失敗：(reason: str, eval_output: str, exit_code: int)

實作（Phase 1）：
  - autoclaude.infra.adapters.shell_evaluator.ShellEvaluator
"""
from __future__ import annotations

from typing import Optional, Protocol

from ...models.playbook import PlaybookTask


class IEvaluator(Protocol):
    """步驟雙重驗證（regex + evaluator_command）的契約。"""

    def evaluate(
        self, task: PlaybookTask, output: str
    ) -> tuple[Optional[str], str, int]:
        """評估步驟輸出是否成功。

        Args:
            task: PlaybookTask（含 expected_output_regex / evaluator_command）
            output: 步驟執行的輸出文字（含 ANSI 控制碼，由實作決定是否 strip）

        Returns:
            (failure_reason, eval_output, exit_code)：
            - failure_reason 為 None 代表成功
            - eval_output 為 evaluator_command 的輸出（regex 失敗時為原 output 尾段）
            - exit_code 為 evaluator_command 的退出碼（regex 失敗時為 0）
        """
        ...
