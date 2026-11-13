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
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from .git import mask as git_mask

_ENV_KEYS = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL")
TAIL_BYTES = 300


@dataclass
class ProbeResult:
    rc: int | None
    timed_out: bool
    out_sha256: str
    out_bytes: int
    tail: str


#: 探針輸出尾段的遮罩：與推送結果共用 `git.mask` 的單一實作，只是標記字樣不同（不另定義函式）
mask = partial(git_mask, mark="[REDACTED]")


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


def _taskkill_exe() -> str:
    """`taskkill` 的絕對路徑（`%SystemRoot%\\System32`；審查 F-10：裸名會先在目前目錄與 venv 找）。
    找不到系統目錄時退回裸名。"""
    if sys.platform.startswith("win"):
        root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT")
        return str(Path(root) / "System32" / "taskkill.exe") if root else "taskkill"
    return ""


def _kill_tree(proc: subprocess.Popen) -> None:
    """殺行程樹（含孫行程）；兩條各在平台守衛作用域內。"""
    if sys.platform.startswith("win"):
        try:  # 不開視窗（pythonw 載具）；taskkill 找不到不得讓逾時收尾本身拋例外（審查 F-11／F-12）
            subprocess.run([_taskkill_exe(), "/T", "/F", "/PID", str(proc.pid)], check=False,
                           capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError:
            pass
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
    # 空格分隔的可查字樣：job-unavailable:<原因>（Job 沒建起來，不論逾時與否）、job-terminated、
    # taskkill-fallback:<原因>、output-incomplete；`push-run` 把它寫進結果檔（F-05）
    note: str = ""


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
    return "killpg" if sys.platform != "win32" else f"taskkill-fallback:{why or 'terminate-failed'}"


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
    notes = [f"job-unavailable:{why}"] if job is None and sys.platform == "win32" else []
    timed_out = False
    try:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            held, job = job, None  # 句柄交給 `_timeout_kill`：它關一次，之後 finally 不再碰（F-12）
            notes.append(_timeout_kill(proc, held, why))
            try:
                out, err = proc.communicate(timeout=KILL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                out, err = b"", b""
                notes.append("output-incomplete")
    finally:
        _job_end(job, terminate=False)  # 正常結束只關句柄；留下的背景行程不動
    return RunResult(None if timed_out else proc.returncode, timed_out,
                     (out or b"").decode("utf-8", errors="replace"),
                     (err or b"").decode("utf-8", errors="replace"),
                     " ".join(n for n in notes if n))


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
        subprocess.run([_taskkill_exe(), "/T", "/F", "/PID", str(pid)], check=False,
                       capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def pid_started_at(pid: int) -> float | None:
    """行程啟動時刻（epoch 秒）；不存在或量不到＝None（供「pid 被重用」核對：呼叫端比對 spawn.json
    記的啟動時刻）。Windows 以 ctypes `GetProcessTimes` 直接查（不起 powershell 子行程：平行負載下
    每次起 powershell 要數百毫秒到數秒，逾牆終止路徑吃不起）、POSIX 問 `ps`（經過秒數換算）。"""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k32.GetProcessTimes.restype = wintypes.BOOL
            ft = ctypes.POINTER(wintypes.FILETIME)
            k32.GetProcessTimes.argtypes = [wintypes.HANDLE, ft, ft, ft, ft]
            k32.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return None
            try:
                created, a, b, c = (wintypes.FILETIME() for _ in range(4))
                if not k32.GetProcessTimes(handle, *map(ctypes.byref, (created, a, b, c))):
                    return None
            finally:
                k32.CloseHandle(handle)
            ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime  # 100ns、自 1601
            return float((ticks - 116444736000000000) // 10_000_000)
        except Exception:  # noqa: BLE001  # 量不到＝None（呼叫端 fail-closed）
            return None
    try:
        # `etime`（`[[DD-]hh:]mm:ss`）而非 `etimes`：macOS 的 BSD ps 沒有 `etimes` 欄位，
        # procps（Linux）兩者皆有
        cp = subprocess.run(["ps", "-o", "etime=", "-p", str(int(pid))], capture_output=True,
                            encoding="utf-8", errors="replace", timeout=20, shell=False,
                            check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    elapsed = _parse_etime(cp.stdout)
    if cp.returncode != 0 or elapsed is None:
        return None
    return time.time() - elapsed


def _parse_etime(text: str) -> int | None:
    """`ps -o etime=` 的 `[[DD-]hh:]mm:ss`→秒；格式不符＝None。"""
    m = re.fullmatch(r"\s*(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)\s*", text)
    if m is None:
        return None
    days, hours, mins, secs = (int(g or 0) for g in m.groups())
    return ((days * 24 + hours) * 60 + mins) * 60 + secs


IDENTITY_TOLERANCE_SECONDS = 5  # 行程建立時間與 `spawn.json` 記的實測值允許的誤差（秒）


def _ts(value) -> float | None:
    """ISO 字串→epoch 秒；非字串、空字串、無法解析＝None（不拋例外，E-46）。"""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def process_identity(pid: int, started_at: str, created: str | None = None, *,
                     window_seconds: float | None) -> str:
    """pid 的身分判定，值域四值：`gone`（不存在或量不到）／`match`／`mismatch`（pid 已被別的行程
    使用）／`unverified`（`created` 或 `started_at` 不是可解析的 ISO，或沒有 `created` 而
    `window_seconds` 為 None：不退回寬鬆窗，呼叫端殺行程時不殺、判活與回收時視為活著；E-23、E-46）。
    有 `created`（spawn 當下實測的行程建立時間，UTC ISO）時只准 `IDENTITY_TOLERANCE_SECONDS`
    的誤差；沒有時以窗 `[started_at−120 秒, started_at＋window_seconds]` 判（`window_seconds` 必填、
    無預設值，由記錄自己的牆鐘長度加 600 秒推得，不寫死）。"""
    try:
        start = pid_started_at(int(pid))
    except (TypeError, ValueError):
        return "unverified"
    if start is None:
        return "gone"
    want = _ts(started_at)
    if want is None or (created is not None and _ts(created) is None):
        return "unverified"
    if created is not None:
        return "match" if abs(start - _ts(created)) <= IDENTITY_TOLERANCE_SECONDS else "mismatch"
    if window_seconds is None:
        return "unverified"
    return "match" if want - 120 <= start <= want + window_seconds else "mismatch"


def alive(pid: int, started_at: str, created: str | None = None,
          window_seconds: float | None = None) -> bool:
    """判活與回收：身分 `match` 與 `unverified`（無法驗證）都算活著——安全側；逾牆終止另走
    `spawn_identity`，那裡 `unverified` 是不殺。"""
    return process_identity(pid, started_at, created,
                            window_seconds=window_seconds) in ("match", "unverified")


def overdue(now: datetime, wall_due_at) -> bool:
    """`now` 已到或超過牆鐘到期時刻；到期時刻被竄改（不是可解析的帶時區 ISO）＝視為逾牆（E-46）。"""
    try:
        return now >= datetime.fromisoformat(wall_due_at)
    except (TypeError, ValueError):
        return True


def spawn_identity(data: dict) -> str:
    """`spawn.json` 內容對應的行程身分（只認實測建立時間，不退回寬鬆窗；逾牆終止前用）。"""
    return process_identity(data["pid"], data["started_at"], data.get("process_started_utc"),
                            window_seconds=None)


def spawn_record(pid: int, started: datetime, wall_due: datetime) -> dict:
    """`patrol/<RUN>/spawn.json` 的內容：pid、心跳時刻、硬牆到期，加 spawn 當下實測的行程建立時間
    （`process_started_utc`，UTC ISO；量不到＝None）供逾牆終止前核對身分（審查 F-07）。"""
    return {"pid": pid, "started_at": started.isoformat(timespec="seconds"),
            "wall_due_at": wall_due.isoformat(timespec="seconds"),
            "process_started_utc": started_utc(pid)}


def started_utc(pid: int) -> str | None:
    """行程建立時間（UTC ISO 秒）；量不到＝None。"""
    real = pid_started_at(pid)
    return None if real is None else datetime.fromtimestamp(real, UTC).isoformat(timespec="seconds")


def run_probe(argv: list[str], *, cwd: Path, sandbox_root: Path, timeout: float) -> ProbeResult:
    """執行一個探針；回 `ProbeResult`（逾時時 `rc` 為 None、`timed_out` 為 True）。"""
    # 探針是 console 程式：Windows 要 NO_WINDOW，否則 pythonw 之下會多配一個 conhost
    flags: dict = {"start_new_session": True}
    if sys.platform.startswith("win"):
        flags = {"creationflags": (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))}
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
