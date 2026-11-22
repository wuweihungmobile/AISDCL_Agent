"""監督單例鎖（Control_Handover_Design §5；W6-W2；Architect A3）。

WHY：同 sid 可同時有兩支 `sessionctl watch`（上一 session 實證：一次 TaskStop 停了兩支），
先結束者的收尾會動到共用狀態、另一支還在跑時外界誤判「無監督」。所以同 sid 只准一支 watch 持有
`trace_dir()/watch/<sid>.lock`（pid＋行程建立時間）；後來者印 `WATCH_VERDICT=duplicate`、rc 0 結束。

機制與 `holder`（保溫錨）同型：判活（`holder.is_live`／`pid_alive`／`start_token`）單一家、不複製；
只有路徑不同。互斥是優化、不是監督的前提：鎖檔寫不進去 ⇒ 視為取得（寧可重複也不讓 watch 不跑）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import endurance_env

from . import holder

SCHEMA = "autosdd.watch.lock/1"


def path(sid: str, *, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / "watch" / f"{sid}.lock"


def read(sid: str) -> dict | None:
    """鎖記錄；不存在／讀不動／結構不符 ⇒ `None`（當作沒有持有者＝可接手）。"""
    try:
        row = json.loads(path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return row if isinstance(row, dict) and type(row.get("pid")) is int else None


def live_other(sid: str, pid: int, *, alive=holder.pid_alive,
               token=holder.start_token) -> dict | None:
    """持有者活著且不是自己 ⇒ 回其記錄，否則 `None`。"""
    row = read(sid)
    return row if row is not None and row["pid"] != pid and holder.is_live(
        row, alive=alive, token=token) else None


def acquire(sid: str, pid: int, *, alive=holder.pid_alive, token=holder.start_token) -> bool:
    """取得單例：活著的別人持有（或同時搶的別人先建成）⇒ `False`；否則以 `O_CREAT|O_EXCL` 原子建立
    並回 `True`。檔案系統寫不進去 ⇒ 也回 `True`（見檔頭）。"""
    if live_other(sid, pid, alive=alive, token=token) is not None:
        return False
    target = path(sid, write=True)
    row = {"schema": SCHEMA, "sid": sid, "pid": pid, "proc_start": token(pid) or ""}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():  # 自己的舊記錄、或陳舊（行程已死／被重用／壞檔）⇒ 先清再建
            target.unlink()
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return not target.is_file()  # 同時搶的別人先建成；被目錄佔住等＝寫不進，不擋
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
