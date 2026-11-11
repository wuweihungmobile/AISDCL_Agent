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
    note: str = ""  # 逾時收尾字樣：job-terminated／taskkill-fallback:<原因>／output-incomplete


KILL_GRACE_SECONDS = 5  # 逾時殺完後再收輸出的寬限；仍收不完就放棄讀取並在 `note` 如實報告


def _job_open(pid: int):
    """Windows：建 Job Object 並把子行程指派進去（不設 KILL_ON_JOB_CLOSE、不設 BREAKAWAY_OK：
    正常結束只關句柄、不殺任何東西）。回（句柄或 None, 失敗原因）。誠實劃界：`Popen` 回來到本函式
    指派完成之間有一小段競態窗——這段時間內子行程若已 fork 出孫行程，孫行程不在 job 裡；只用文件化
    的 `OpenProcess`／`AssignProcessToJobObject`，不用未文件化 API 去消它（逾時時 `_kill_tree` 的
    `taskkill /T` 仍會再補殺一次仍連得上的子樹）。非 Windows 一律回 (None, "not-windows")。"""
    if sys.platform != "win32":
        return None, "not-windows"
    try:
        import ctypes

        vp, u32, ci = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = k32.OpenProcess.restype = vp
        k32.CreateJobObjectW.argtypes = [vp, ctypes.c_wchar_p]
        k32.OpenProcess.argtypes = [u32, ci, u32]
        k32.AssignProcessToJobObject.argtypes = [vp, vp]
        k32.AssignProcessToJobObject.restype = ci
        k32.TerminateJobObject.argtypes = [vp, u32]
        k32.TerminateJobObject.restype = ci
        k32.CloseHandle.argtypes = [vp]
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return None, f"CreateJobObjectW winerror={ctypes.get_last_error()}"
        proc = k32.OpenProcess(0x0101, 0, pid)  # PROCESS_SET_QUOTA｜PROCESS_TERMINATE
        assigned = bool(proc) and bool(k32.AssignProcessToJobObject(job, proc))
        why = "" if assigned else f"assign winerror={ctypes.get_last_error()}"
        if proc:
            k32.CloseHandle(proc)
        if not assigned:
            k32.CloseHandle(job)
            return None, why
        return job, ""
    except Exception as exc:  # noqa: BLE001  # Job 建不起來一律退回 taskkill，不得讓外呼本身失敗
        return None, type(exc).__name__


def _job_end(job, *, terminate: bool) -> bool:
    """Windows：（可選）終結整個 job 後關句柄；回終結是否成功。句柄一律關閉。"""
    if job is None or sys.platform != "win32":
        return False
    import ctypes

    vp = ctypes.c_void_p
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.TerminateJobObject.argtypes = [vp, ctypes.c_uint32]
    k32.TerminateJobObject.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [vp]
    try:
        return bool(terminate and k32.TerminateJobObject(job, 1))
    finally:
        k32.CloseHandle(job)


def _timeout_kill(proc: subprocess.Popen, job, why: str) -> str:
    """逾時收尾：有 job 先終結整個 job（含父行程鏈斷掉的孫行程），否則退回 `_kill_tree`
    （`taskkill /T`／`killpg`）；POSIX 子行程自成行程群組，`killpg` 即整棵樹。回 `note` 字樣。"""
    if job is not None and _job_end(job, terminate=True):
        proc.kill()
        return "job-terminated"
    _kill_tree(proc)
    return "" if sys.platform != "win32" else f"taskkill-fallback:{why or 'terminate-failed'}"


def run_argv(argv: list[str], *, env: dict[str, str], timeout: float,
             cwd: Path | None = None) -> RunResult:
    """明示環境入口（TCS-P4 R160）：`shell=False`、`communicate(timeout)`、逾時殺行程樹；
    環境**只用呼叫端明示的 `env`**（本函式不讀 `os.environ`）；輸出原文回給呼叫端（不落檔）。
    逾時後第二次收輸出帶 `KILL_GRACE_SECONDS` 寬限，仍收不完就放棄讀取（`note` 含
    output-incomplete）。"""
    flags: dict = {}
    if sys.platform.startswith("win"):
        flags["creationflags"] = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                  | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        flags["start_new_session"] = True
    proc = subprocess.Popen(
        argv, cwd=None if cwd is None else str(cwd), env=dict(env), shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    job, why = _job_open(proc.pid)
    timed_out, note = False, ""
    try:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            note = _timeout_kill(proc, job, why)
            job = None  # 已在 `_timeout_kill` 內關閉
            try:
                out, err = proc.communicate(timeout=KILL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                out, err, note = b"", b"", (note + " output-incomplete").strip()
    finally:
        _job_end(job, terminate=False)  # 正常結束只關句柄；留下的背景行程不動
    return RunResult(None if timed_out else proc.returncode, timed_out,
                     (out or b"").decode("utf-8", errors="replace"),
                     (err or b"").decode("utf-8", errors="replace"), note)


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
