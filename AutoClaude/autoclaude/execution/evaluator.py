"""
獨立評估器：在 Claude Code 子進程之外執行驗證指令。
AI 說完成不算，由 Evaluator 親自執行並回傳結果。
"""
from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

from ..utils.platform_caps import kill_process_tree, new_session_kwargs
from ..utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger("autoclaude.execution.evaluator")

# R69：行程樹回收（原 kill_process_tree）與平台守門一併收斂至
# utils/platform_caps.py —— 它與 perception/pty_wrapper.py `close()` 原本是同一套
# 邏輯的兩份複製（DEF-101-706）。此處僅 re-export 供既有呼叫端
# （mutation_applier/_conditional.py）沿用原 import 路徑。
# 常數在 import 期算一次，維持 `**_NEW_SESSION_KWARGS` 呼叫站點語意不變。
_NEW_SESSION_KWARGS: dict = new_session_kwargs()


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
            # 改 Popen + communicate（而非 subprocess.run）純為了逾時分支能拿到
            # Popen 物件呼叫 kill_process_tree()——run() 內部逾時時已自行 kill
            # 直接子行程並吞掉 handle，呼叫端無從回收孫行程。
            proc = subprocess.Popen(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                env=propagate_to_subprocess_env(dict(os.environ)),
                **_NEW_SESSION_KWARGS,
            )
            try:
                out, err = proc.communicate(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                kill_process_tree(proc)
                try:
                    proc.communicate(timeout=5)
                except Exception:
                    pass
                msg = f"評估指令逾時 ({effective_timeout}s): {command}"
                logger.error(msg)
                return EvalResult(success=False, output=msg, exit_code=-1)
            output = ((out or "") + (err or "")).strip()
            success = proc.returncode == 0
            if success:
                logger.info("評估通過 [exit=%d]", proc.returncode)
            else:
                logger.warning("評估失敗 [exit=%d]\n%s", proc.returncode, output[:800])
            return EvalResult(success=success, output=output, exit_code=proc.returncode)
        except Exception as exc:
            msg = f"評估指令異常: {exc}"
            logger.error(msg)
            return EvalResult(success=False, output=msg, exit_code=-1)
