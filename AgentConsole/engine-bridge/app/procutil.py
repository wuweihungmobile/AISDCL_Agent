"""子行程治理的跨平台小工具（全部走 psutil，不碰 os 層的 kill 與 signal 模組）。

Windows 行為對照（本機只在 macOS 驗證，Windows 未實測，見 README〈Windows 接續注意〉）：
  · `Process.terminate()`  POSIX＝SIGTERM；Windows＝TerminateProcess
                           （立即強終止，沒有「優雅」階段）。
  · `Process.kill()`       POSIX＝SIGKILL；Windows＝同 terminate。
  · pid 存活判定           探測用的 kill(pid, 0) 在 Windows 不是探測（會真的終止行程）
                           ⇒ 一律 psutil.pid_exists。
  · spawn                  POSIX 用 start_new_session（自成 session／行程組）；Windows 用
                           CREATE_NEW_PROCESS_GROUP（並加 CREATE_NO_WINDOW，避免閃視窗）。
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from typing import Any

import psutil

#: pid 重用判定的容差（秒）：create_time 在不同平台精度不同，1 秒足以分辨「同一個行程」。
CREATE_TIME_TOLERANCE = 1.0


def popen_platform_kwargs() -> dict[str, Any]:
    """spawn 引擎時的平台專屬參數（讓引擎自成行程組，不收到 Bridge 的 Ctrl+C）。"""
    if sys.platform == "win32":
        flags = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                 | getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"creationflags": flags}
    return {"start_new_session": True}


def process_create_time(pid: int) -> float | None:
    try:
        return psutil.Process(pid).create_time()
    except psutil.Error:
        return None


def pid_alive(pid: int | None, create_time: float | None = None) -> bool:
    """pid 存在，且（若給了 create_time）仍是**同一個**行程——pid 會被作業系統重用。"""
    if not isinstance(pid, int) or pid <= 0 or not psutil.pid_exists(pid):
        return False
    if create_time is None:
        return True
    actual = process_create_time(pid)
    return actual is not None and abs(actual - create_time) <= CREATE_TIME_TOLERANCE


def _is_alive(proc: psutil.Process) -> bool:
    try:
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def begin_terminate(pid: int) -> list[psutil.Process]:
    """先快照 `pid` 與其**所有後代**，再逐一 terminate()，回傳快照清單（根在最前）。

    一定要「先快照再送訊號」：根行程一死，它的子孫就被 init 收養，之後再也列舉不出來。
    引擎把 claude 子行程放在自己的 session 裡，所以光殺引擎，claude 會變成孤兒繼續跑。
    """
    try:
        root = psutil.Process(pid)
    except psutil.Error:
        return []
    try:
        descendants = root.children(recursive=True)
    except psutil.Error:          # 列舉子孫失敗（權限／競態）不可連根都不殺
        descendants = []
    procs = [root, *descendants]
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    return procs


def survivors(procs: Iterable[psutil.Process], *,
              exclude_pid: int | None = None) -> list[psutil.Process]:
    """快照清單中仍活著的行程。`exclude_pid`＝我們自己的 Popen 子行程（由 Popen.poll 判，
    因為 psutil 對「已結束但尚未被 wait 的殭屍」仍可能回報存在）。"""
    return [p for p in procs if p.pid != exclude_pid and _is_alive(p)]


def force_kill(procs: Iterable[psutil.Process]) -> list[int]:
    """對仍活著的行程 kill()；回傳被強殺的 pid（供審計／alert 事件）。"""
    killed: list[int] = []
    for proc in procs:
        if not _is_alive(proc):
            continue
        try:
            proc.kill()
            killed.append(proc.pid)
        except psutil.Error:
            pass
    return killed
