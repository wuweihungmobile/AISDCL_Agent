"""
獨立評估器：在 Claude Code 子進程之外執行驗證指令。
AI 說完成不算，由 Evaluator 親自執行並回傳結果。
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

from ..utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger("autoclaude.execution.evaluator")

# R68：POSIX 要整棵殺，子行程須先成為新 session 的 process group leader（PID 即
# pgid）。start_new_session 為 POSIX only，故平台守門。同 perception/pty_wrapper.py
# `_start_subprocess()`（本修復的對照組，已雙平台驗證）。
_NEW_SESSION_KWARGS: dict = {} if sys.platform == "win32" else {"start_new_session": True}


def kill_process_tree(proc: subprocess.Popen) -> None:
    """終結 proc 及其任意深度的孫行程（shell=True 逾時回收的 SSOT）。"""
    # R68：`subprocess.run(..., timeout=)` 逾時只 kill 直接子行程（POSIX 的 /bin/sh、
    # Windows 的 cmd.exe）；該殼再 fork 出的孫行程會變孤兒（PPID→1）續跑並寫檔，使
    # 「已判逾時失敗」的工作仍在背景產生副作用。手法比照 pty_wrapper.py `close()`
    # （已雙平台驗證）：Windows `taskkill /T /F`；POSIX `killpg` 先 SIGTERM 給緩衝、
    # 輪詢後仍活才 SIGKILL。pid 非真實整數即跳過（測試以 MagicMock 充當 proc）。
    # 🔴 待收斂（R69，ADR-SD07-001 §6.3「先收斂重複實作，最後才調 baseline」）：
    # 本函式與 perception/pty_wrapper.py `close()` 是同一套行程樹回收的兩份實作，
    # 抽到 utils/ 共用可淨減 autoclaude/ 總 LOC；本輪 total 已逼近 cap 故先記。
    pid = getattr(proc, "pid", None)
    if not isinstance(pid, int):
        return
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.killpg(pgid, 0)
            except OSError:
                return
            time.sleep(0.05)
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass


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
