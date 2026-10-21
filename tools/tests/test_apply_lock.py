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
import contextlib
import inspect
import io
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

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


# ---------------------------------------------------------------------------
# DEF-200-559（TCS-SelfImproving-P2 R100、AC-240-8）：Windows 刪除待決／共享違規的 PermissionError。
# 替身測試，任一平台可重現、不靠真實競態。
# ---------------------------------------------------------------------------
_DENIED = PermissionError(13, "denied")


def _guarded_open(lp: Path, behaviour):
    """`os.open` 的包裝：對 `lp` 的呼叫交給 `behaviour(n)`（n 為第幾次；回 None＝呼叫真實函式）。"""
    real, calls = os.open, []

    def wrapper(path, *a, **kw):
        if str(path) == str(lp):
            calls.append(path)
            exc = behaviour(len(calls))
            if exc is not None:
                raise exc
        return real(path, *a, **kw)
    return wrapper, calls


def _guarded_unlink(lp: Path, behaviour):
    real, calls = Path.unlink, []

    def wrapper(self, *a, **kw):
        if str(self) == str(lp):
            calls.append(1)
            exc = behaviour(len(calls))
            if exc is not None:
                raise exc
        return real(self, *a, **kw)
    return wrapper, calls


def _sleeps():
    real, seen = time.sleep, []

    def rec(x):
        seen.append(x)
        real(0)
    return rec, seen


def _stale_lock(lp: Path) -> None:
    lp.write_text("99999\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
    old = time.time() - 3600
    import os as _os
    _os.utime(lp, (old, old))


class TestWindowsDeletePending(unittest.TestCase):
    def test_AT_240_8_1_acquire_retries_permission_error(self) -> None:
        lp = _fresh_lock_path()
        wrapper, calls = _guarded_open(lp, lambda n: _DENIED if n <= 3 else None)
        rec, seen = _sleeps()
        t0 = time.monotonic()
        with mock.patch.object(apply_lock.os, "open", wrapper), \
                mock.patch.object(apply_lock.time, "sleep", rec):
            with apply_lock.acquire(lp, 5, 60, poll_interval=0.01):
                body = lp.read_text(encoding="utf-8")
                self.assertTrue(lp.exists())
        self.assertEqual(len(calls), 4)
        self.assertRegex(body, rf"^{os.getpid()}\n\d{{4}}-\d{{2}}-\d{{2}}T[^\n]+\n$")
        self.assertFalse(lp.exists())
        self.assertEqual(seen, [0.01, 0.01, 0.01])
        self.assertLess(time.monotonic() - t0, 2)

    def test_AT_240_8_2_reap_swallows_permission_error_once(self) -> None:
        for exc in (PermissionError(13, "denied"), FileNotFoundError(2, "gone")):
            lp = _fresh_lock_path()
            _stale_lock(lp)
            wrapper, calls = _guarded_unlink(lp, lambda n, e=exc: e if n == 1 else None)
            with mock.patch.object(Path, "unlink", wrapper):
                with apply_lock.acquire(lp, 5, 60, poll_interval=0.01):
                    self.assertIn(str(os.getpid()), lp.read_text(encoding="utf-8"))
                    n_acquire = len(calls)
            self.assertGreaterEqual(n_acquire, 2)
        lp = _fresh_lock_path()
        lp.write_text("1\nx\n", encoding="utf-8")
        wrapper, calls = _guarded_unlink(lp, lambda n: None)
        with mock.patch.object(Path, "unlink", wrapper), self.assertRaises(
                apply_lock.LockBusyError), apply_lock.acquire(lp, 0.2, 60, poll_interval=0.02):
            pass
        self.assertEqual(len(calls), 0)
        lp.unlink()

    def test_AT_240_8_3_release_retries_are_bounded(self) -> None:
        lp = _fresh_lock_path()
        k = apply_lock.RELEASE_RETRIES
        self.assertTrue(isinstance(k, int) and k > 0)
        state = {"in_body": True}

        def behaviour(n):
            return _DENIED if n <= k else None
        wrapper, calls = _guarded_unlink(lp, behaviour)
        rec, seen = _sleeps()
        err = io.StringIO()
        with mock.patch.object(Path, "unlink", wrapper), \
                mock.patch.object(apply_lock.time, "sleep", rec), \
                contextlib.redirect_stderr(err):
            with apply_lock.acquire(lp, 5, 60, poll_interval=0.01):
                seen.clear()
            del state
        self.assertFalse(lp.exists())
        self.assertEqual(len(calls), k + 1)
        self.assertEqual(seen, [0.01] * k)
        self.assertEqual(err.getvalue(), "")

    def test_AT_240_8_E_1_timeout_exception_types(self) -> None:
        sig = inspect.signature(apply_lock.acquire)
        self.assertEqual(list(sig.parameters), ["lock_path", "timeout", "stale_after",
                                                "poll_interval"])
        self.assertEqual(sig.parameters["poll_interval"].default, 0.2)
        self.assertTrue(issubclass(apply_lock.LockBusyError, RuntimeError))

        def attempt(lp, behaviour=None):
            wrapper, _ = _guarded_open(lp, behaviour or (lambda n: None))
            t0 = time.monotonic()
            with mock.patch.object(apply_lock.os, "open", wrapper):
                try:
                    with apply_lock.acquire(lp, 0.4, 60, poll_interval=0.02):
                        pass
                except BaseException as exc:  # noqa: BLE001
                    return exc, time.monotonic() - t0
            return None, time.monotonic() - t0

        lp = _fresh_lock_path()
        exc, dt = attempt(lp, lambda n: _DENIED)
        self.assertIsInstance(exc, PermissionError)
        self.assertNotIsInstance(exc, apply_lock.LockBusyError)
        self.assertEqual(exc.errno, 13)
        self.assertTrue(0.35 <= dt < 3, dt)
        lp = _fresh_lock_path()
        lp.write_text(f"{os.getpid()}\nnow\n", encoding="utf-8")
        exc, _ = attempt(lp)
        self.assertIsInstance(exc, apply_lock.LockBusyError)
        self.assertIn(str(os.getpid()), str(exc))
        self.assertIn("持鎖者資訊", str(exc))
        lp.unlink()
        lp = _fresh_lock_path()

        def then_exists(n):
            if n == 3:
                lp.write_text(f"{os.getpid()}\nnow\n", encoding="utf-8")
            return _DENIED if n <= 2 else None
        exc, _ = attempt(lp, then_exists)
        self.assertIsInstance(exc, apply_lock.LockBusyError)
        lp.unlink()
        gone = _TMP_DIR / "no_such_dir" / "x.lock"
        exc, dt = attempt(gone)
        self.assertIsInstance(exc, FileNotFoundError)
        self.assertLess(dt, 0.3)
        lp = _fresh_lock_path()
        exc, dt = attempt(lp, lambda n: OSError(5, "EIO"))
        self.assertIsInstance(exc, OSError)
        self.assertEqual(exc.errno, 5)
        self.assertLess(dt, 0.3)

    def test_AT_240_8_E_2_reap_negatives(self) -> None:
        lp = _fresh_lock_path()
        _stale_lock(lp)
        wrapper, calls = _guarded_unlink(lp, lambda n: _DENIED)
        t0 = time.monotonic()
        with mock.patch.object(Path, "unlink", wrapper), self.assertRaises(
                apply_lock.LockBusyError), apply_lock.acquire(lp, 0.4, 1, poll_interval=0.02):
            pass
        self.assertLess(time.monotonic() - t0, 3)
        self.assertGreater(len(calls), 1)
        real = Path.unlink
        real(lp)
        lp = _fresh_lock_path()
        _stale_lock(lp)
        wrapper, calls = _guarded_unlink(lp, lambda n: OSError(5, "EIO"))
        with mock.patch.object(Path, "unlink", wrapper), self.assertRaises(OSError) as cm, \
                apply_lock.acquire(lp, 0.4, 1, poll_interval=0.02):
            pass
        self.assertEqual(cm.exception.errno, 5)
        real(lp)
        lp = _fresh_lock_path()
        lp.write_text("1\nx\n", encoding="utf-8")
        wrapper, calls = _guarded_unlink(lp, lambda n: None)
        with mock.patch.object(Path, "unlink", wrapper), self.assertRaises(
                apply_lock.LockBusyError), apply_lock.acquire(lp, 0.4, 60, poll_interval=0.02):
            pass
        self.assertEqual(len(calls), 0)
        real(lp)

    def test_AT_240_8_E_3_release_exhausted_is_silent_but_warned(self) -> None:
        k = apply_lock.RELEASE_RETRIES
        lp = _fresh_lock_path()
        wrapper, calls = _guarded_unlink(lp, lambda n: _DENIED)
        err = io.StringIO()
        with mock.patch.object(Path, "unlink", wrapper), contextlib.redirect_stderr(err):
            with apply_lock.acquire(lp, 5, 60, poll_interval=0.001):
                pass
        self.assertEqual(len(calls), k + 1)
        self.assertTrue(lp.exists())
        self.assertIn(str(lp), err.getvalue())
        self.assertIn("PermissionError", err.getvalue())
        real = Path.unlink
        real(lp)
        lp2 = _fresh_lock_path()
        wrapper, calls = _guarded_unlink(lp2, lambda n: _DENIED)
        err = io.StringIO()
        with mock.patch.object(Path, "unlink", wrapper), contextlib.redirect_stderr(err):
            with self.assertRaises(ValueError), apply_lock.acquire(lp2, 5, 60, poll_interval=0.001):
                raise ValueError("body")
        self.assertEqual(len(calls), k + 1)
        self.assertTrue(lp2.exists())
        _stale_lock(lp2)  # (c) 殘留鎖被當陳舊鎖回收
        with apply_lock.acquire(lp2, 5, 60, poll_interval=0.01):
            self.assertIn(str(os.getpid()), lp2.read_text(encoding="utf-8"))
        self.assertFalse(lp2.exists())


class TestWriteVerbsAbsorbLockFix(unittest.TestCase):
    """AT-240-8-E-4：`evwrite` 層承接修法（釋放用盡不再被回報成「帳本未變動」）。"""

    @classmethod
    def setUpClass(cls) -> None:
        import _selfimproving_fixtures as fx
        cls.fx = fx
        fx.setup("si_al_")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fx.teardown()

    def setUp(self) -> None:
        fx = self.fx
        import _selfimproving_p2_fixtures as fx2
        self.fx2 = fx2
        self.home = fx.new_dir("home")
        self.home.mkdir()
        patcher = mock.patch.dict(os.environ, {**fx.hermetic(), "AUTOSDD_SI_DIR": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.R = fx2.make_p2_repo(fx.new_dir("r"))

    def run_verb(self):
        import selfimproving
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = selfimproving.main(["run-open", "--trigger", "a", "--coord", "tools/a.py:1",
                                     "--by", "main", "--repo", str(self.R)])
        return rc, out.getvalue(), err.getvalue()

    def lock_file(self) -> Path:
        files = list((self.home / "locks").glob("*.lock"))
        return files[0] if files else None

    def test_AT_240_8_E_4_evwrite_layer(self) -> None:
        from lib.selfimproving import evwrite
        ledger = self.R / self.fx.EVL
        real_unlink = Path.unlink

        def deny_lock(self_, *a, **kw):
            if str(self_).endswith(".lock"):
                raise PermissionError(13, "denied")
            return real_unlink(self_, *a, **kw)
        with mock.patch.object(Path, "unlink", deny_lock):
            rc, out, err = self.run_verb()
        self.assertEqual(rc, 0, out + err)
        self.assertRegex(out, r"^ok run\.open seq=1 id=RUN-SI-001 ")
        self.assertEqual(len(ledger.read_bytes().splitlines()), 1)
        self.assertIn("PermissionError", err)
        self.assertNotIn("帳本未變動", out + err)
        lock = self.lock_file()
        self.assertIsNotNone(lock)
        self.assertIn(str(lock), err)
        old = time.time() - 3600
        os.utime(lock, (old, old))
        with mock.patch.object(evwrite, "LOCK_STALE_SECONDS", 60):
            rc, out, err = self.run_verb()
        self.assertEqual(rc, 0, out + err)
        self.assertRegex(out, r"^ok run\.open seq=2 ")
        # (b) 取鎖階段的 PermissionError 逾時：rc 3，且「帳本未變動」為真
        lock = self.lock_file() or (self.home / "locks" / "x.lock")
        real_open = os.open

        def deny_open(path, *a, **kw):
            if str(path).endswith(".lock"):
                raise PermissionError(13, "denied")
            return real_open(path, *a, **kw)
        before = ledger.read_bytes()
        with mock.patch.object(os, "open", deny_open), mock.patch.object(
                evwrite, "LOCK_TIMEOUT_SECONDS", 0.3):
            rc, out, err = self.run_verb()
        self.assertEqual(rc, 3)
        self.assertIn("事件追加失敗（PermissionError），帳本未變動", err)
        self.assertEqual(ledger.read_bytes(), before)
        # (c) 新鮮的鎖：rc 1 的 LOCK-BUSY
        lock = evwrite.lock_path_for(self.home, ledger)
        lock.write_text(f"{os.getpid()}\nnow\n", encoding="utf-8")
        os.utime(lock, None)
        with mock.patch.object(evwrite, "LOCK_TIMEOUT_SECONDS", 0.3):
            rc, out, err = self.run_verb()
        self.assertEqual(rc, 1, out + err)
        self.assertIn("LOCK-BUSY", out)
        self.assertIn(f"持鎖者資訊（pid / 取得時間）：{os.getpid()} / now", out)  # 既有語意不變
        self.assertEqual(ledger.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
