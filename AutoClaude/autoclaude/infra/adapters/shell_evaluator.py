"""ShellEvaluator — IEvaluator 的實作（Phase 1）。

職責：
  - 對 PlaybookTask 執行雙重驗證：expected_output_regex（regex）+ evaluator_command（shell）
  - regex 比對前自動 strip ANSI（與舊 PlaybookRunner._evaluate 行為等價）
  - 此 Adapter 與 Frozen Surface `runner._evaluate` 在 Phase 1 ~ Phase 4 並存
"""
from __future__ import annotations

import re
from typing import Optional

from ...execution.evaluator import Evaluator
from ...models.playbook import PlaybookTask
from ...perception.text_utils import strip_ansi
from ...utils.config import PlaybookConfig


class ShellEvaluator:
    """雙重驗證（regex + shell command）的 Adapter。"""

    def __init__(self, playbook_cfg: PlaybookConfig):
        self._cfg = playbook_cfg
        self._inner = Evaluator(timeout=playbook_cfg.evaluator_timeout_seconds)

    def evaluate(
        self, task: PlaybookTask, output: str
    ) -> tuple[Optional[str], str, int]:
        # 1. regex 比對（先 strip ANSI）
        if task.expected_output_regex:
            if not re.search(task.expected_output_regex, strip_ansi(output)):
                reason = f"輸出未符合期望 regex: {task.expected_output_regex!r}"
                return reason, output[-2000:], 0

        # 2. evaluator_command 驗證（如有指定）
        if task.evaluator_command:
            result = self._inner.run(
                task.evaluator_command,
                timeout=task.evaluator_timeout_seconds,
            )
            if not result.success:
                reason = f"評估指令失敗 (exit={result.exit_code}): {task.evaluator_command}"
                return reason, result.output, result.exit_code

        return None, "", 0
