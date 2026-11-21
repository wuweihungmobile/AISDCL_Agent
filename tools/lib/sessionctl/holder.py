"""保溫錨互斥（R217 WP-A4；DES §6.2、REQ-WP-31）。

WHY：同一 sid 若同時有 `watch` 與 `keepwarm` 兩個行程各自叫醒，每次叫醒主控都冷讀 40 萬～99 萬
cache_read（M-WB2：舊 session 14 天 21 次重複叫醒）。所以保溫錨只准一個持有者：
`trace_dir()/keepwarm/<sid>.holder`（pid＋行程建立時間）。持有者判活＝pid 存在**且**建立時間相符
（pid 被別的行程重用時建立時間不同 ⇒ 接手）。

判活與取建立時間皆以參數注入（`alive`／`token`），不開任何測試用環境變數。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import endurance_env

from . import procstop

SCHEMA = "autosdd.keepwarm.holder/1"


def pid_alive(pid) -> bool:
    """Windows 沿 `handoff._alive`；其他平台 `os.kill(pid, 0)`（sys.platform 守衛內）。"""
    if sys.platform == "win32":
        from . import handoff  # noqa: PLC0415 — lazy：handoff 的依賴面大，只有 Windows 判活才付

        return handoff._alive(pid)
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # PermissionError 等：行程存在
    return True


def start_token(pid) -> str | None:
    """行程建立時間的字串記號：Windows＝GetProcessTimes FILETIME；POSIX＝`ps -o lstart=`。
    取不到 ⇒ `None`（呼叫端不比對，退回只看 pid 存在）。"""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if sys.platform == "win32":
        stamp = procstop.created_filetime(pid)
        return None if stamp is None else str(stamp)
    try:
        proc = procstop.default_runner(["ps", "-o", "lstart=", "-p", str(pid)])
    except (OSError, ValueError):
        return None
    text = (proc.stdout or "").strip()
    return text if proc.returncode == 0 and text else None


def path(sid: str, *, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / "keepwarm" / f"{sid}.holder"


def read(sid: str) -> dict | None:
    """持有者記錄；不存在／讀不動／結構不符 ⇒ `None`（當作沒有持有者＝可接手）。"""
    try:
        row = json.loads(path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return row if isinstance(row, dict) and type(row.get("pid")) is int else None


def is_live(row: dict | None, *, alive=pid_alive, token=start_token) -> bool:
    """記錄指向的行程還是**同一個**行程：pid 存在且（記錄有建立時間 ∧ 現在也取得到 ⇒ 必須相等）。"""
    if row is None or not alive(row["pid"]):
        return False
    stored = row.get("proc_start")
    now = token(row["pid"]) if isinstance(stored, str) and stored else None
    return now is None or now == stored


def live_other(sid: str, pid: int, *, alive=pid_alive, token=start_token) -> dict | None:
    """持有者活著且不是自己 ⇒ 回其記錄，否則 `None`。"""
    row = read(sid)
    return row if row is not None and row["pid"] != pid and is_live(
        row, alive=alive, token=token) else None


def acquire(sid: str, pid: int, *, alive=pid_alive, token=start_token) -> bool:
    """取得保溫錨：活著的別人持有（或同時搶的別人先建成）⇒ `False`；否則寫入自己（`O_CREAT|O_EXCL`
    原子建立）並回 `True`。檔案系統寫不進去（唯讀、目錄被檔案佔住）⇒ 也回 `True`：互斥是
    「避免重複叫醒」的優化，不是叫醒的前提——寫不進去時不能讓 watch 永遠不叫醒；保溫帳同樣寫不進
    會在叫醒當下判 cap（`keepwarm.record_ping`），失效仍往少花走。"""
    if live_other(sid, pid, alive=alive, token=token) is not None:
        return False
    target = path(sid, write=True)
    row = {"schema": SCHEMA, "sid": sid, "pid": pid, "proc_start": token(pid) or ""}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        current = read(sid)
        if current is not None and current["pid"] == pid:
            target.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8", newline="\n")
            return True
        if current is not None or target.exists():  # 陳舊（行程已死／被重用／壞檔）⇒ 先清再建
            target.unlink()
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return not target.is_file()  # 同時搶的別人先建成；被目錄佔住等＝寫不進，照上述不擋
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False))
    except OSError:
        return True
    return True


def release(sid: str, pid: int) -> None:
    """只刪自己持有的記錄（別人接手後不得被我們的收尾刪掉）。"""
    row = read(sid)
    if row is not None and row["pid"] == pid:
        try:
            path(sid, write=True).unlink()
        except OSError:
            pass
