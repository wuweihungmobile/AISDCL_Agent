"""driver：起真的 `claude -p`（可 `-r <sid>`），帶 env 覆寫、牆鐘上限與 `--debug hooks` 日誌。"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .sandbox import Sandbox, kill_tree

DEFAULT_TIMEOUT_S = 240


class EnvMissing(RuntimeError):
    """環境缺件（如找不到 claude 執行檔）：runner 回 rc 2，**不得 skip 成綠**。"""


def find_claude() -> str:
    exe = shutil.which("claude")
    if not exe:
        raise EnvMissing("找不到 claude 執行檔（PATH 內無 claude）")
    return exe


@dataclass
class RunResult:
    rc: int
    stdout: str
    stderr: str
    sid: str
    debug_log: Path
    timed_out: bool
    seconds: float

    def debug_text(self) -> str:
        try:
            return self.debug_log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


def _kill_tree(proc: subprocess.Popen) -> None:
    """逾時收尾：連同子行程樹一起砍（R216 複審 P3-c）。

    WHY：`proc.kill()` 只砍 claude 本身，它派生的背景行程（如被 Stop 閘要求掛上的 keepwarm）
    活下來並握著沙盒目錄 ⇒ 清理報 RESIDUE、孤兒行程遺留。實作搬到 `sandbox.kill_tree`（R217 DEF-03：
    `Sandbox.cleanup` 也要用同一個，POSIX 另補行程群組）；本名留著給既有呼叫端與測試。"""
    kill_tree(proc)


def run_claude(
    sb: Sandbox,
    prompt: str,
    *,
    resume: bool = False,
    model: str = "haiku",
    env_extra: dict | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    extra_args: tuple[str, ...] = (),
) -> RunResult:
    """跑一次 `claude -p`。首次呼叫用 `--session-id <sb.sid>` 預知 sid；`resume=True`（或第二次起）用 `-r <sid>`。"""  # noqa: E501
    exe = find_claude()
    resume = resume or sb.used_resume
    dbg = sb.root / f"debug_{uuid.uuid4().hex[:6]}.log"
    argv = [exe, "-p", "--model", model, "--debug", "hooks", "--debug-file", str(dbg)]
    argv += ["-r", sb.sid] if resume else ["--session-id", sb.sid]
    argv += [*extra_args, prompt]
    t0 = time.monotonic()
    proc = subprocess.Popen(  # noqa: S603
        argv, cwd=str(sb.root), env=sb.env(env_extra),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        start_new_session=os.name != "nt",  # POSIX：自成行程群組，`kill_tree` 才砍得到整棵樹
    )
    sb.procs.append(proc)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        out, err = proc.communicate()
    sb.used_resume = True
    return RunResult(
        rc=-9 if timed_out else proc.returncode,
        stdout=out.decode("utf-8", errors="replace"), stderr=err.decode("utf-8", errors="replace"),
        sid=sb.sid, debug_log=dbg, timed_out=timed_out, seconds=time.monotonic() - t0,
    )
