"""
獨立評估器：在 Claude Code 子進程之外執行驗證指令。
AI 說完成不算，由 Evaluator 親自執行並回傳結果。
"""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

from ..utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger("autoclaude.execution.evaluator")


@dataclass
class EvalResult:
    success: bool
    output: str
    exit_code: int


class Evaluator:
    def __init__(self, timeout: int = 120):
        self._timeout = timeout

    def run(self, command: str, timeout: int | None = None) -> EvalResult:
        """執行 playbook 作者提供的 evaluator_command。

        跨平台注意：以 subprocess.run(shell=True) 執行，實際呼叫的是「作業系統原生殼」——
        Windows 為 cmd.exe，POSIX 為 /bin/sh，而非固定的 bash。因此 evaluator_command
        必須寫成可攜指令（如 `pytest ...`、`python -c "..."`），避免 POSIX 專屬語法
        （test -f、單引號字串、&&/||、grep 等 shell builtin/GNU 工具），否則在 Windows
        上會被 cmd.exe 解讀出非預期結果，而非清楚的「找不到指令」失敗。
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        logger.info("執行評估指令: %s (timeout=%ds)", command, effective_timeout)
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
                env=propagate_to_subprocess_env(dict(os.environ)),
            )
            output = (result.stdout + result.stderr).strip()
            success = result.returncode == 0
            if success:
                logger.info("評估通過 [exit=%d]", result.returncode)
            else:
                logger.warning("評估失敗 [exit=%d]\n%s", result.returncode, output[:800])
            return EvalResult(success=success, output=output, exit_code=result.returncode)
        except subprocess.TimeoutExpired:
            msg = f"評估指令逾時 ({effective_timeout}s): {command}"
            logger.error(msg)
            return EvalResult(success=False, output=msg, exit_code=-1)
        except Exception as exc:
            msg = f"評估指令異常: {exc}"
            logger.error(msg)
            return EvalResult(success=False, output=msg, exit_code=-1)
