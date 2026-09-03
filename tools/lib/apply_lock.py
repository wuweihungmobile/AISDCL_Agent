#!/usr/bin/env python3
"""跨平台檔案鎖（DEF-200-222 判準②）：`archive_defect_log.py --apply` 的序列化保護。

## 立案

`check_archive_required.py` 的 commit 期阻斷判準觸發時，會導引使用者跑
`archive_defect_log.py --apply --archive-num <N>`。多個 agent 共用同一份工作樹時，
每一個撞到同一道阻斷的 agent 都可能各自照著訊息跑同一條指令——對同一份主檔／同一個
`<N>` 並發執行，`--apply` 本身完全沒有鎖定或序列化（DEF-200-222 立案原文）。本模組
提供的鎖，讓 `tools/archive_apply_locked.py`（見該檔）在呼叫 `archive_defect_log.apply()`
前先取得互斥權。

## 🔴 為何不用 `os.O_APPEND` 或 `msvcrt.locking`（本 repo R81 已付過學費）

R81 已實測：Windows 上 `os.O_APPEND` 單次 `os.write()` 不是原子的（高併發下仍掉
12.2%）；`msvcrt.locking` 在高併發下本身會變成故障源。兩者都是「位元組層級」的競態，
語意在兩個平台上還不一樣。改走**獨佔建檔**（`os.open(path, O_CREAT | O_EXCL)`）：
鎖的是「這個檔案存在與否」這件事，Windows 與 POSIX 對 `O_CREAT | O_EXCL` 的保證一致
——同時只有一個呼叫者能成功建立該檔，另一者必得到 `FileExistsError`。這是兩個平台
語意相同的原語，不是位元組層級的寫入競態。

## 契約

  - `acquire(lock_path, timeout, stale_after)` 是一個 context manager：
    成功取得鎖時，鎖檔內容為 `"<pid>\\n<acquired_at ISO8601>\\n"`；
    離開 `with` 區塊（正常或例外皆然）時刪除鎖檔。
  - **逾時 fail-loud**：`timeout` 秒內都拿不到鎖 → 拋 `LockBusyError`，訊息內含
    **持鎖者是誰、何時取得**（讀鎖檔內容），不是靜默等待到永遠、也不是靜默放行。
  - **陳舊鎖回收**：鎖檔存在但其 mtime 已超過 `stale_after` 秒 → 視為「持鎖行程已死」，
    嘗試刪除後重新嘗試取鎖。刪除本身也可能與另一個回收者競爭（TOCTOU）——刪除失敗
    （`FileNotFoundError`）視為對方已經清理，不視為錯誤，直接進入下一輪重試（有界：
    仍受 `timeout` 總時限管，不會無限迴圈）。
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class LockBusyError(RuntimeError):
    """`timeout` 秒內仍無法取得鎖。"""


def _read_holder(lock_path: Path) -> str:
    """鎖檔內容（`<pid>\\n<acquired_at>`），供逾時訊息指名持鎖者；讀不到就誠實說讀不到。"""
    try:
        text = lock_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "（無法讀取鎖檔內容——可能正被持鎖者或回收者同時操作）"
    return text.replace("\n", " / ") if text else "（鎖檔為空）"


def _try_acquire(lock_path: Path) -> bool:
    """獨佔建檔：成功回 `True`；鎖已被別人持有（`FileExistsError`）回 `False`。"""
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        payload = f"{os.getpid()}\n{datetime.now(UTC).isoformat()}\n"
        os.write(fd, payload.encode("utf-8"))
    finally:
        os.close(fd)
    return True


def _reap_if_stale(lock_path: Path, stale_after: float) -> None:
    """鎖檔 mtime 超過 `stale_after` 秒即視為持鎖行程已死，嘗試刪除以便下一輪重試。"""
    try:
        age = time.time() - lock_path.stat().st_mtime
    except FileNotFoundError:
        return  # 鎖已被持有者釋放或被另一個回收者清掉，屬正常狀態
    if age <= stale_after:
        return
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass  # TOCTOU：已被另一個回收者搶先清掉，不是錯誤


@contextmanager
def acquire(
    lock_path: Path, timeout: float, stale_after: float, poll_interval: float = 0.2,
) -> Iterator[None]:
    """取得 `lock_path` 這把鎖；逾時拋 `LockBusyError`，成功則離開區塊時自動釋放。"""
    deadline = time.monotonic() + timeout
    while not _try_acquire(lock_path):
        _reap_if_stale(lock_path, stale_after)
        if time.monotonic() >= deadline:
            raise LockBusyError(
                f"取得鎖逾時（{timeout}s）：{lock_path} 目前由另一個行程持有 —— "
                f"持鎖者資訊（pid / 取得時間）：{_read_holder(lock_path)}。"
                f"本機制已對超過 {stale_after}s 的陳舊鎖自動回收，逾時仍發生代表"
                "確有另一個 --apply 正在進行；若能確認上述行程已不存在，"
                f"可手動刪除 {lock_path} 後重試"
            )
        time.sleep(poll_interval)
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass  # 已被自己刪過或被回收器清掉（不應發生於正常路徑，但不視為致命）
