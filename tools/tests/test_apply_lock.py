#!/usr/bin/env python3
"""`tools/lib/apply_lock.py` 的回歸鎖（DEF-200-222 判準②：`--apply` 的序列化保護）。

三件事要驗（逐一對應 DEF-200-222 的驗收要求）：
  1. 兩個並發呼叫者只有一個能同時在臨界區內——用**真的多執行緒 + 壁鐘 barrier**逼出
     同時起跑，量測兩段臨界區的實際時間戳記是否重疊（不用 `Pool.map`：那量不到
     併發缺陷，兩個 worker 各自獨立執行完全看不出有沒有互斥）。
  2. 陳舊鎖（mtime 早於 `stale_after`）會被自動回收，不必等到 `timeout`。
  3. 拿不到鎖時 fail-loud：拋 `LockBusyError`，訊息內指名持鎖者（pid）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import apply_lock  # noqa: E402

_TMP_DIR = Path(tempfile.mkdtemp(prefix="apply_lock_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _fresh_lock_path() -> Path:
    """每支測試各自一個全新鎖檔路徑，避免測試之間互相殘留鎖檔而假紅/假綠。"""
    _tmp_counter[0] += 1
    p = _TMP_DIR / f"lock_{_tmp_counter[0]}.lock"
    if p.exists():
        p.unlink()
    return p


class TestAcquireBasicContract(unittest.TestCase):
    def test_acquire_creates_and_releases_lock_file(self) -> None:
        lock_path = _fresh_lock_path()
        with apply_lock.acquire(lock_path, timeout=5.0, stale_after=300.0):
            self.assertTrue(lock_path.exists(), "with 區塊內鎖檔應存在")
        self.assertFalse(lock_path.exists(), "離開 with 區塊後鎖檔應被釋放")

    def test_lock_file_records_holder_pid(self) -> None:
        lock_path = _fresh_lock_path()
        import os
        with apply_lock.acquire(lock_path, timeout=5.0, stale_after=300.0):
            content = lock_path.read_text(encoding="utf-8")
            self.assertIn(str(os.getpid()), content,
                          "鎖檔內容應記錄持鎖者 pid，供逾時訊息指名持鎖者")

    def test_release_survives_exception_inside_with_block(self) -> None:
        """區塊內拋例外仍須釋放鎖——否則第一次失敗就會把鎖永久卡死。"""
        lock_path = _fresh_lock_path()
        with self.assertRaises(ValueError):
            with apply_lock.acquire(lock_path, timeout=5.0, stale_after=300.0):
                raise ValueError("模擬臨界區內部失敗")
        self.assertFalse(lock_path.exists(), "例外離開後鎖檔仍應被釋放，不可永久卡死")


class TestConcurrentAcquireIsMutuallyExclusive(unittest.TestCase):
    """真實併發測試：兩個執行緒以壁鐘 barrier 同時起跑，臨界區故意 sleep 製造重疊窗口，
    若鎖沒生效，兩者的 enter~exit 區間會重疊；若鎖生效，兩者必然前後接續、零重疊。
    """

    def test_only_one_of_two_concurrent_workers_is_in_critical_section_at_once(
        self,
    ) -> None:
        lock_path = _fresh_lock_path()
        barrier = threading.Barrier(2)
        events: list[tuple[int, str, float]] = []
        events_guard = threading.Lock()  # 只保護 events.append 本身，不影響待測邏輯
        errors: list[BaseException] = []

        def worker(tid: int) -> None:
            try:
                barrier.wait(timeout=5)
                with apply_lock.acquire(lock_path, timeout=10.0, stale_after=300.0,
                                         poll_interval=0.01):
                    with events_guard:
                        events.append((tid, "enter", time.monotonic()))
                    time.sleep(0.3)  # 製造重疊窗口：鎖沒生效的話，兩支會同時在這裡
                    with events_guard:
                        events.append((tid, "exit", time.monotonic()))
            except BaseException as exc:  # noqa: BLE001  # 測試執行緒須把例外帶回主執行緒
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in (0, 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        self.assertFalse(any(t.is_alive() for t in threads), "worker 逾時未完成")
        self.assertEqual(errors, [], f"worker 執行緒內發生未預期例外：{errors}")

        spans: dict[int, dict[str, float]] = {}
        for tid, kind, ts in events:
            spans.setdefault(tid, {})[kind] = ts
        self.assertEqual(set(spans), {0, 1}, f"應各自恰好一組 enter/exit：{events}")
        (e0, x0) = spans[0]["enter"], spans[0]["exit"]
        (e1, x1) = spans[1]["enter"], spans[1]["exit"]
        overlap = not (x0 <= e1 or x1 <= e0)
        self.assertFalse(
            overlap,
            f"兩個臨界區時間重疊（thread0=[{e0},{x0}] thread1=[{e1},{x1}]）"
            "——鎖未生效，兩個 --apply 同時進入了臨界區",
        )


class TestStaleLockReaping(unittest.TestCase):
    def test_stale_lock_is_reaped_and_reacquired_quickly(self) -> None:
        """模擬「持鎖行程已死」：手動建鎖檔並把 mtime 撥回遠早於 stale_after。"""
        import os

        lock_path = _fresh_lock_path()
        lock_path.write_text("999999\n2000-01-01T00:00:00+00:00\n", encoding="utf-8")
        old = time.time() - 1000
        os.utime(lock_path, (old, old))

        start = time.monotonic()
        with apply_lock.acquire(lock_path, timeout=5.0, stale_after=1.0,
                                 poll_interval=0.05):
            pass
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed, 4.0,
            "陳舊鎖（mtime 遠早於 stale_after）應很快被回收並重新取得，"
            "不應等到接近 timeout 上限",
        )
        self.assertFalse(lock_path.exists(), "離開 with 區塊後鎖檔應被釋放")

    def test_fresh_lock_is_not_reaped_before_stale_after(self) -> None:
        """反例：鎖檔剛建立（mtime 是現在），即使 stale_after 很短也不該立刻被當陳舊——
        必須真的超過 stale_after 秒才回收，否則會把「還在正常執行中」誤殺。"""
        lock_path = _fresh_lock_path()
        lock_path.write_text("111111\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
        # stale_after 給一個明顯大於本測試 timeout 的值，逾時必然發生在「未被回收」的前提下
        with self.assertRaises(apply_lock.LockBusyError):
            with apply_lock.acquire(lock_path, timeout=0.3, stale_after=300.0,
                                     poll_interval=0.05):
                pass  # 不應執行到這裡
        lock_path.unlink()


class TestAcquireTimeoutIsFailLoud(unittest.TestCase):
    def test_timeout_raises_with_holder_pid_named_in_message(self) -> None:
        lock_path = _fresh_lock_path()
        lock_path.write_text("424242\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
        try:
            with self.assertRaises(apply_lock.LockBusyError) as ctx:
                with apply_lock.acquire(lock_path, timeout=0.3, stale_after=300.0,
                                         poll_interval=0.05):
                    pass  # 不應執行到這裡
            msg = str(ctx.exception)
            self.assertIn("424242", msg,
                          "逾時訊息必須指名持鎖者 pid，不能只說「拿不到鎖」")
            self.assertIn(str(lock_path), msg, "逾時訊息應指名鎖檔路徑")
        finally:
            lock_path.unlink()


if __name__ == "__main__":
    unittest.main()
