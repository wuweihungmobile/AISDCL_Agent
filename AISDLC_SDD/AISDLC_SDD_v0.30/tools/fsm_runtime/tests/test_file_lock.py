"""Tests for file_lock advisory lock (M2 QA Round-2 P1-1)."""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.file_lock import file_lock  # noqa: E402


def _worker_increment(lock_path: str, counter_path: str, hold_ms: int) -> None:
    """Acquire lock, read counter, sleep, increment, write — simulates the
    read-modify-write pattern of the CONTEXT-LEDGER hooks."""
    lock_p = Path(lock_path)
    counter_p = Path(counter_path)
    with file_lock(lock_p, timeout=30.0):
        value = int(counter_p.read_text(encoding="utf-8") or "0")
        time.sleep(hold_ms / 1000.0)
        counter_p.write_text(str(value + 1), encoding="utf-8")


class FileLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parallel_writes_do_not_lose_increments(self) -> None:
        """4 processes each +1 on a shared counter — final must equal 4."""
        counter = self.root / "counter.txt"
        counter.write_text("0", encoding="utf-8")
        lock_path = self.root / "counter.lock"
        procs = []
        for _ in range(4):
            p = mp.Process(
                target=_worker_increment,
                args=(str(lock_path), str(counter), 50),
            )
            p.start()
            procs.append(p)
        for p in procs:
            p.join(timeout=30)
            self.assertFalse(p.is_alive(), "worker hung")
            self.assertEqual(p.exitcode, 0, "worker errored")
        self.assertEqual(int(counter.read_text(encoding="utf-8")), 4)

    def test_stale_lock_auto_cleared(self) -> None:
        """Sentinel older than 30s must be treated as abandoned and reclaimed."""
        lock_path = self.root / "resource.lock"
        lock_path.write_text("pid=99999 stale", encoding="utf-8")
        # Backdate mtime by 60 seconds so the guard treats it as stale.
        old_mtime = time.time() - 60
        import os as _os
        _os.utime(lock_path, (old_mtime, old_mtime))
        # Acquisition should succeed within timeout despite the stale sentinel.
        with file_lock(lock_path, timeout=2.0):
            self.assertTrue(lock_path.exists())
        # After release the sentinel must be gone.
        self.assertFalse(lock_path.exists())

    def test_timeout_raises_when_held(self) -> None:
        """If another holder is active, acquisition must TimeoutError."""
        lock_path = self.root / "busy.lock"
        # Manually place a FRESH sentinel (mtime = now, so not stale).
        lock_path.write_text("pid=12345 fresh", encoding="utf-8")
        start = time.time()
        with self.assertRaises(TimeoutError):
            with file_lock(lock_path, timeout=0.3):
                self.fail("should not acquire")  # pragma: no cover
        elapsed = time.time() - start
        # Timeout must be ≥ configured (with small slack) and < stale threshold.
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 5.0)
        # Cleanup — sentinel remains (not ours to remove).
        lock_path.unlink()


class UnremovableSentinelTests(unittest.TestCase):
    """R60 A-02 回歸鎖：sentinel 刪不掉時的兩條路徑都不得逸出 ``OSError``。

    WHY：兩處移除 sentinel 的 ``unlink`` 原本只捕 ``FileNotFoundError``。Windows 上
    只要有第三方持著該 sentinel 的 handle（防毒掃描、搜尋索引器、備份代理，或本模組
    docstring 自己邀請的 post-mortem 讀取者），``unlink`` 就丟 ``PermissionError``
    ([WinError 32])——本機實測會**逸出 context manager**（呼叫端的例外契約裡沒有這個
    型別）且 sentinel 洩漏。修法沿用 ``tools/dev_start.py::_release_bootstrap_lock``
    的 ``except OSError: pass`` 慣例。

    第二個鎖（``..._times_out_instead_of_spinning``）守的是修法本身的陷阱：陳舊回收
    分支原本無條件 ``continue``，那會**跳過 deadline 檢查與 sleep**——單純把窄捕放寬成
    ``except OSError: pass`` 會把「刪不掉的陳舊 sentinel」變成 100% CPU 的無窮忙迴圈
    （比原缺陷更糟）。故該分支必須「刪不掉就落回 deadline/sleep」。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def _deny_unlink(_self, *_a, **_kw):
        raise PermissionError(
            32, "程序無法存取檔案，因為檔案正由另一個程序使用。（注入）"
        )

    def test_release_does_not_raise_when_sentinel_cannot_be_removed(self) -> None:
        """平台中立載具：注入 ``PermissionError`` 於 finally 的 unlink。"""
        lock_path = self.root / "ledger.lock"
        with mock.patch.object(Path, "unlink", self._deny_unlink):
            with file_lock(lock_path, timeout=2.0):
                pass   # 正常離開 → finally 走 unlink → 注入的 PermissionError
        self.assertTrue(
            lock_path.exists(),
            "載具失效：注入未生效（sentinel 竟被刪掉），本測試對本缺陷無鑑別力",
        )
        lock_path.unlink()

    @unittest.skipUnless(sys.platform == "win32",
                         "真 handle 佔用語意只在 Windows 成立（POSIX unlink 允許刪除已開啟檔案）")
    def test_release_survives_real_open_handle_on_windows(self) -> None:
        """原生 Windows 載具：不注入例外，用真的 open handle 觸發 [WinError 32]。"""
        lock_path = self.root / "held.lock"
        held = None
        try:
            with file_lock(lock_path, timeout=2.0):
                held = open(lock_path, "rb")   # 第三方持 handle（AV／索引器語意）
        finally:
            if held is not None:
                held.close()
        self.assertTrue(lock_path.exists(), "載具失效：Windows 竟刪得掉被開啟的檔案")
        lock_path.unlink()

    def test_unremovable_stale_sentinel_times_out_instead_of_spinning(self) -> None:
        lock_path = self.root / "stale_held.lock"
        lock_path.write_text("pid=99999 stale", encoding="utf-8")
        old = time.time() - 60          # 遠超 _STALE_AFTER_SEC=30 → 判定陳舊
        os.utime(lock_path, (old, old))

        outcome: list[object] = []

        def attempt() -> None:
            try:
                with file_lock(lock_path, timeout=0.3):
                    outcome.append("acquired")
            except BaseException as exc:  # noqa: BLE001
                outcome.append(exc)

        with mock.patch.object(Path, "unlink", self._deny_unlink):
            worker = threading.Thread(target=attempt, daemon=True)
            start = time.time()
            worker.start()
            worker.join(timeout=5.0)
            elapsed = time.time() - start

        self.assertFalse(
            worker.is_alive(),
            "陳舊 sentinel 刪不掉時 file_lock 沒有在 5s 內收場——無窮忙迴圈復發"
            "（陳舊回收分支的 continue 跳過了 deadline 檢查）",
        )
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(
            outcome[0], TimeoutError,
            f"應以 TimeoutError 收場（呼叫端已有降級路徑），實際為 {outcome[0]!r}",
        )
        self.assertLess(elapsed, 5.0)
        lock_path.unlink()


if __name__ == "__main__":
    unittest.main()
