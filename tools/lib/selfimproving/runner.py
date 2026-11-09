"""SelfImproving 探針子行程出口（TCS-SelfImproving-P2 R87；PRD §9.4）：整個套件除 `git.py` 外
唯一出現行程外呼的檔（能力類別 `exec`）。

`Popen`＋`communicate(timeout)`、`shell=False`；環境白名單（不繼承 `AUTOSDD_*` 與其他機密）；
`PYTHONPATH` 只有沙盒樹根（不帶 `-I`／`-P`，否則載具自證失效）；逾時殺行程樹並回收；輸出只留
sha256、位元組數與遮蔽後的末段（≤300 位元組），原始輸出全文不入 git、不落任何檔。
"""

from __future__ import annotations

import hashlib
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL")
TAIL_BYTES = 300
_MASKS = (
    (re.compile(r"Bearer\s+\S+"), "Bearer [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}"), "[REDACTED]"),
    (re.compile(r"(?i)Authorization:[^\r\n]*"), "Authorization: [REDACTED]"),
    (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://[REDACTED]@"),
)


@dataclass
class ProbeResult:
    rc: int | None
    timed_out: bool
    out_sha256: str
    out_bytes: int
    tail: str


def mask(text: str) -> str:
    for rx, repl in _MASKS:
        text = rx.sub(repl, text)
    return text


def _tail(raw: bytes) -> str:
    masked = mask(raw.decode("utf-8", errors="replace")).encode("utf-8")
    cut = masked[-TAIL_BYTES:]
    while cut and (cut[0] & 0xC0) == 0x80:  # 依 UTF-8 邊界截斷，不切半個字元
        cut = cut[1:]
    return cut.decode("utf-8", errors="replace")


def _env(sandbox_root: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(sandbox_root))
    return env


def _kill_tree(proc: subprocess.Popen) -> None:
    """殺行程樹（含孫行程）；兩條各在平台守衛作用域內。"""
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], check=False,
                       capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    proc.kill()


def expand(argv: list[str], sandbox_root: Path) -> list[str]:
    """`{python}`→`sys.executable`、`{sandbox}`→沙盒樹根（`{heldout}` 由呼叫端先換）。"""
    out = [a.replace("{sandbox}", str(sandbox_root)) for a in argv]
    out[0] = sys.executable if out[0] == "{python}" else out[0]
    return out


@dataclass
class RunResult:
    rc: int | None
    timed_out: bool
    out: str
    err: str


def run_argv(argv: list[str], *, env: dict[str, str], timeout: float,
             cwd: Path | None = None) -> RunResult:
    """明示環境入口（TCS-P4 R160）：`shell=False`、`communicate(timeout)`、逾時殺行程樹；
    環境**只用呼叫端明示的 `env`**（本函式不讀 `os.environ`）；輸出原文回給呼叫端（不落檔）。"""
    flags: dict = {}
    if sys.platform.startswith("win"):
        flags["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                  | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        flags["start_new_session"] = True
    proc = subprocess.Popen(
        argv, cwd=None if cwd is None else str(cwd), env=dict(env), shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        out, err = proc.communicate()
    return RunResult(None if timed_out else proc.returncode, timed_out,
                     (out or b"").decode("utf-8", errors="replace"),
                     (err or b"").decode("utf-8", errors="replace"))


def spawn_detached(argv: list[str], *, env: dict[str, str], cwd: Path | None = None,
                   out_dir: Path | None = None) -> int:
    """脫離式啟動（TCS-P4 R160、R167、D-QA-14）：新 session／process group、`shell=False`、不等待、
    回 pid；環境**只用呼叫端明示的 `env`**（不讀 `os.environ`）。`out_dir` 給了就把 stdout／stderr
    各接到該目錄的 `stdout.txt`／`stderr.txt`（供後續心跳判 harness 殺行程）。Windows 旗標三個各以
    `getattr` 兜底（breakaway 被任務 job 拒絕時 `OSError`／`PermissionError` 原樣穿出，由呼叫端
    fail-closed）。本函式不呼叫 `communicate`、不殺行程。"""
    flags: dict = {}
    if sys.platform.startswith("win"):
        flags["creationflags"] = (getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
                                  | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                  | getattr(subprocess, "DETACHED_PROCESS", 0))
    else:
        flags["start_new_session"] = True
    sink = {}
    opened = []
    try:
        if out_dir is not None:
            for name in ("stdout", "stderr"):
                fh = open(out_dir / f"{name}.txt", "wb")  # noqa: SIM115  # 交給子行程後立即關本端
                opened.append(fh)
                sink[name] = fh
        proc = subprocess.Popen(argv, cwd=None if cwd is None else str(cwd), env=dict(env),
                                shell=False, stdin=subprocess.DEVNULL,
                                stdout=sink.get("stdout", subprocess.DEVNULL),
                                stderr=sink.get("stderr", subprocess.DEVNULL), **flags)
    finally:
        for fh in opened:
            fh.close()
    return proc.pid


def kill_pid_tree(pid: int) -> None:
    """依 pid 殺行程樹（逾牆終止用）；找不到行程＝已結束，不拋。兩條各在平台守衛作用域內。"""
    if sys.platform.startswith("win"):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], check=False,
                       capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def pid_started_at(pid: int) -> float | None:
    """行程啟動時刻（epoch 秒）；不存在或量不到＝None（供「pid 被重用」核對：呼叫端比對 spawn.json
    記的啟動時刻）。Windows 問 PowerShell、POSIX 問 `ps`（經過秒數換算）。"""
    if sys.platform.startswith("win"):
        argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                f"$p = Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue; "
                "if ($p) { [DateTimeOffset]::new($p.StartTime).ToUnixTimeSeconds() }"]
    else:
        argv = ["ps", "-o", "etimes=", "-p", str(int(pid))]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
    try:
        cp = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace",
                            timeout=20, shell=False, check=False, creationflags=flags)
    except (OSError, subprocess.SubprocessError):
        return None
    text = cp.stdout.strip()
    if cp.returncode != 0 or not text.isdigit():
        return None
    value = int(text)
    if sys.platform.startswith("win"):
        return float(value)
    return time.time() - value


def run_probe(argv: list[str], *, cwd: Path, sandbox_root: Path, timeout: float) -> ProbeResult:
    """執行一個探針；回 `ProbeResult`（逾時時 `rc` 為 None、`timed_out` 為 True）。"""
    flags: dict = {}
    if sys.platform.startswith("win"):
        flags["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        flags["start_new_session"] = True
    proc = subprocess.Popen(
        expand(argv, sandbox_root), cwd=str(cwd), env=_env(sandbox_root), shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        out, err = proc.communicate()
    raw = (out or b"") + (err or b"")
    return ProbeResult(None if timed_out else proc.returncode, timed_out,
                       "sha256:" + hashlib.sha256(raw).hexdigest(), len(raw), _tail(raw))
