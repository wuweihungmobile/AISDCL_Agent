"""SelfImproving 事件帳本寫入核心：鎖內「讀末行 → 配號 → 單次完整行追加」（TCS-P1 R30、R32、R33）。

能力類別 `rw`：全部寫事件的動詞只經 `append_event` 追加（`lock_path=None` 僅供測試的無鎖對照組）。
鎖＝獨佔建檔鎖（`lib.apply_lock`；不用 `msvcrt.locking`／`fcntl.flock`，不單靠 `O_APPEND`）。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from lib import apply_lock

from . import events as si_events

LockBusyError = apply_lock.LockBusyError
# 初值未校準（先例 tools/archive_apply_locked.py）；測試以 mock.patch.object 改小
LOCK_TIMEOUT_SECONDS = 60
LOCK_STALE_SECONDS = 300
PAUSE_HOOK: Callable[[], None] | None = None  # 測試鉤子：讀末行並配號之後、單次追加之前


class Reject(Exception):
    """本次寫入拒收；`codes`＝[(碼, 說明), …]（rc 1，零殘留）。"""

    def __init__(self, codes: list[tuple[str, str]]) -> None:
        super().__init__(", ".join(c for c, _ in codes))
        self.codes = codes


class HomeUnwritable(Exception):
    """家目錄機器狀態無法建立／寫入（rc 3，不退回系統暫存目錄）。"""


@dataclass
class State:
    last_seq: int
    events: list[dict]
    cleanups: list[Callable[[], None]] = field(default_factory=list)


def ensure_home(si: Path) -> Path:
    """建立並探測 `<si>/locks`、`<si>/research`；失敗拋 HomeUnwritable。回 locks 目錄。"""
    try:
        for sub in ("locks", "research"):
            (si / sub).mkdir(parents=True, exist_ok=True)
        tag = f"{os.getpid()}-{threading.get_ident()}"  # 同行程多執行緒不互踩
        probe = si / "locks" / f".probe-{tag}"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise HomeUnwritable(f"家目錄不可寫：{si}（{exc.__class__.__name__}）") from exc
    return si / "locks"


def lock_path_for(si: Path, ledger: Path) -> Path:
    key = hashlib.sha256(os.path.realpath(ledger).encode("utf-8")).hexdigest()[:16]
    return si / "locks" / f"{key}.lock"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def render_line(seq: int, event: dict, t: str | None = None) -> str:
    """事件 dict → 一行緊湊 JSON（鍵序：seq、t、kind、by，其後依 event 原序）。"""
    obj = {"seq": seq, "t": t or now_iso(), "kind": event["kind"], "by": event["by"]}
    obj.update({k: v for k, v in event.items() if k not in obj})
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _read_state(ledger: Path) -> State:
    try:
        raw = ledger.read_bytes()
    except FileNotFoundError:
        return State(0, [])
    if not raw:
        return State(0, [])
    if not raw.endswith(b"\n"):
        raise Reject([("LEDGER-TORN", "事件帳本末位元組不是 LF（撕裂的寫入）")])
    lines = si_events.read_lines(raw)
    last = lines[-1].obj if lines else None
    seq = last.get("seq") if last else None
    if not (isinstance(seq, int) and not isinstance(seq, bool)):
        raise Reject([("LEDGER-TORN", "事件帳本末行無法解析或缺 seq")])
    # 配號取原始末行的 seq；其後所有消費者（折疊、查表、card、prop-new、research）只吃通過單事件
    # 判準的事件（R37），所以型別怪異的手寫事件不會讓寫入動詞崩潰。
    return State(seq, si_events.sound([ln.obj for ln in lines if ln.obj is not None]))


def _append_locked(ledger: Path, build, max_bytes: int | None) -> dict:
    state = _read_state(ledger)
    try:
        built = build(state)
        events = built if isinstance(built, list) else [built]  # R122 (g)：全有或全無的多事件追加
        lines = [render_line(state.last_seq + 1 + i, e) for i, e in enumerate(events)]
        for line in lines:
            if max_bytes is not None and len(line.encode("utf-8")) > max_bytes:
                raise Reject([("EVENT-BYTES-OVER", f"事件行 {len(line.encode('utf-8'))} 位元組超過 "
                                                   f"{max_bytes}")])
        if PAUSE_HOOK is not None:
            PAUSE_HOOK()
        ledger.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
        fd = os.open(str(ledger), flags, 0o644)
        try:
            os.write(fd, "".join(line + "\n" for line in lines).encode("utf-8"))
        finally:
            os.close(fd)
    except BaseException:
        for undo in reversed(state.cleanups):
            try:
                undo()
            except OSError:
                pass
        raise
    return json.loads(lines[0])


def append_event(ledger: Path, lock_path: Path | None, build, *,
                 max_bytes: int | None = None) -> dict:
    """全部寫事件動詞的唯一追加路徑；回寫入的事件 dict。
    build(state)→事件 dict（含 kind、by 與欄位，不含 seq／t）或拋 Reject。"""
    if lock_path is None:
        return _append_locked(ledger, build, max_bytes)
    with apply_lock.acquire(lock_path, LOCK_TIMEOUT_SECONDS, LOCK_STALE_SECONDS):
        return _append_locked(ledger, build, max_bytes)
