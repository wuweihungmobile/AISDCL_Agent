"""驅動器執行者存活判準（`fold.driven_verdict` 的 `run_alive`；INV1 W4：整機重開機殺掉驅動器，
帳本只剩 `start`，舊判準得等 `budget_minutes`＝195 分才發現）。

只用 ctypes／標準庫，**不開任何子行程**（`gate.py` 檔頭約束：完成閘在每個 Stop 都跑）。行程身分沿用
`sandbox_scope.proc_probe`（Windows＝GetProcessTimes；POSIX＝`os.kill(pid, 0)`），不另寫一份。

回 `False`（明確死亡）的三條，任一成立：
  1. `start.ts` 早於本次開機時間——那個行程在上次開機前就開始了，不可能還活著；
  2. pid 不存在；
  3. pid 存在但建立時間與 `start.proc_start` 差超過 `IDENTITY_TOLERANCE_SECONDS`（pid 被復用）。
量不到（開機時間讀不到、pid 欄位缺、建立時間讀不到或格式不同）一律回 `None` 或略過該條——
fail-safe：寧可退回預算界，不可把活著的驅動器判死（那會觸發重掛、雙驅動器）。
"""
from __future__ import annotations

import sys
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from lib import sandbox_scope

from .ledger import parse_ts

#: 建立時間比對容差：proc_start 是 .NET 7 位小數、proc_probe 是秒精度，兩者差在秒內。
IDENTITY_TOLERANCE_SECONDS = 2
#: 開機時間比對容差：`GetTickCount64`／`btime` 與帳本時鐘各有誤差，退讓以保 fail-safe。
BOOT_TOLERANCE_SECONDS = 10


def boot_time(now: datetime) -> datetime | None:
    """本次開機時刻（aware）；量不到回 `None`。"""
    try:
        if sys.platform == "win32":
            import ctypes  # noqa: PLC0415 — Windows 專屬

            tick = ctypes.windll.kernel32.GetTickCount64
            tick.restype = ctypes.c_ulonglong
            return now - timedelta(milliseconds=int(tick()))
        if sys.platform.startswith("linux"):
            with open("/proc/stat", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("btime "):
                        return datetime.fromtimestamp(int(line.split()[1])).astimezone()
            return None
        if sys.platform == "darwin":
            import ctypes  # noqa: PLC0415

            buf = (ctypes.c_int64 * 2)()
            size = ctypes.c_size_t(ctypes.sizeof(buf))
            libc = ctypes.CDLL("libc.dylib")
            if libc.sysctlbyname(b"kern.boottime", buf, ctypes.byref(size), None, 0) == 0:
                return datetime.fromtimestamp(int(buf[0])).astimezone()
    except (OSError, ValueError, AttributeError):
        return None
    return None


def start_alive(start: dict, boot: datetime | None,
                probe: Callable[[object], tuple[bool, str | None]] | None = None) -> bool | None:
    """`start` 事件的執行者是否還活著（`True`／`False`／`None`＝量不到）。"""
    stamp = parse_ts(start.get("ts"))
    if boot is not None and stamp is not None and stamp < boot - timedelta(
            seconds=BOOT_TOLERANCE_SECONDS):
        return False
    pid = start.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        return None
    alive, created = (probe or sandbox_scope.proc_probe)(pid)
    if not alive:
        return False
    recorded = parse_ts(start.get("proc_start"))
    made = parse_ts(created)
    if recorded is not None and made is not None and abs(
            (recorded - made).total_seconds()) > IDENTITY_TOLERANCE_SECONDS:
        return False
    return True


def default_run_alive(now: datetime | None = None) -> Callable[[dict], bool | None]:
    """生產用 `run_alive`：開機時間只量一次，之後每個 `start` 只付一次 `proc_probe`。"""
    boot = boot_time(now or datetime.fromtimestamp(time.time()).astimezone())
    return lambda start: start_alive(start, boot)
