"""真 schtasks 載具（Windows）：`AutoSDD_RV_` 前綴、全域檔案鎖串行、必清、回讀
NextRunTime／Principal。

非 Windows 呼叫一律 `EnvMissing`（結構上走不到＝rc 2，不 skip 成綠）。
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

from lib.win_spawn import quiet_python

from .driver import EnvMissing

PREFIX = "AutoSDD_RV_"
LOCK_PATH = Path(tempfile.gettempdir()) / "AutoSDD_RV_sched.lock"
_LOCK_STALE_S = 900


def rv_name(suffix: str) -> str:
    name = suffix if suffix.startswith(PREFIX) else PREFIX + suffix
    if not name.startswith(PREFIX):  # 防呆：任何路徑都不得產出前綴之外的名字
        raise ValueError(name)
    return name


def _ps(script: str, timeout: int = 60) -> tuple[int, str]:
    if os.name != "nt":
        raise EnvMissing("真 schtasks 案例只在 Windows 可跑")
    exe = "powershell.exe" if os.name == "nt" else ""
    enc = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    pr = subprocess.run(  # noqa: S603
        [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],  # noqa: E501
        capture_output=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # noqa: E501
    )
    return pr.returncode, pr.stdout.decode("utf-8", errors="replace").strip()


@contextlib.contextmanager
def sched_lock(timeout_s: int = 1800) -> Iterator[None]:
    """全域檔案鎖：真 schtasks 案例彼此串行（同一排程器命名空間）。"""
    t0 = time.monotonic()
    while True:
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - LOCK_PATH.stat().st_mtime > _LOCK_STALE_S:
                    LOCK_PATH.unlink()
                    continue
            if time.monotonic() - t0 > timeout_s:
                raise TimeoutError("等不到 schtasks 全域鎖") from None
            time.sleep(1.0)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            LOCK_PATH.unlink()


def read_back(name: str) -> dict | None:
    """回讀工作：{state, next_run_time, logon_type, execute, arguments}；不存在回 None。
    憑證是 NextRunTime 這個「值」，不是 rc（Get-ScheduledTask 對不存在的工作 rc 也是 0）。"""
    name = rv_name(name)
    rc, out = _ps(
        f"$t = Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue; if (-not $t) {{ exit 0 }}; "  # noqa: E501
        f"$i = $t | Get-ScheduledTaskInfo; $a = $t.Actions[0]; "
        "[pscustomobject]@{state=[string]$t.State; next_run_time=if($i.NextRunTime){$i.NextRunTime.ToString('o')}else{''}; "  # noqa: E501
        "logon_type=[string]$t.Principal.LogonType; execute=$a.Execute; arguments=$a.Arguments} | ConvertTo-Json -Compress"  # noqa: E501
    )
    return json.loads(out) if rc == 0 and out.startswith("{") else None


def register_once(name: str, run_at_local_iso: str, arguments: str) -> dict:
    """註冊一次性工作（Interactive 登入型態），回讀後回傳 read_back 結果；讀不到 next_run_time 即 RuntimeError。

    載具固定走 `quiet_python()`（GUI 子系統 pythonw）：驗證載具自己不得在掌舵者桌面畫 console 視窗
    （`test_check_hooks_liveness` 的排程 Action 判準認 `quiet_python` 賦值來源）。
    """  # noqa: E501
    name = rv_name(name)
    q = lambda s: s.replace("'", "''")  # noqa: E731
    python = q(quiet_python())
    rc, out = _ps(
        f"$a = New-ScheduledTaskAction -Execute '{python}' -Argument '{q(arguments)}'; "
        f"$t = New-ScheduledTaskTrigger -Once -At ([datetime]'{q(run_at_local_iso)}'); "
        "$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive; "
        f"Register-ScheduledTask -TaskName '{name}' -Action $a -Trigger $t -Principal $p -Force | Out-Null"  # noqa: E501
    )
    if rc != 0:
        raise RuntimeError(f"Register-ScheduledTask rc={rc}: {out[:300]}")
    rb = read_back(name)
    if not rb or not rb.get("next_run_time"):
        raise RuntimeError(f"註冊後回讀不到 NextRunTime：{rb}")
    return rb


def remove(name: str) -> None:
    name = rv_name(name)
    _ps(f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false -ErrorAction SilentlyContinue")  # noqa: E501


def list_rv() -> list[str]:
    if os.name != "nt":
        return []
    rc, out = _ps(f"Get-ScheduledTask | Where-Object TaskName -like '{PREFIX}*' | Select-Object -ExpandProperty TaskName")  # noqa: E501
    return [ln.strip() for ln in out.splitlines() if ln.strip()] if rc == 0 else []


def cleanup_all_rv() -> list[str]:
    gone = list_rv()
    for n in gone:
        remove(n)
    return gone
