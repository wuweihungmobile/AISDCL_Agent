"""Tests for file_lock advisory lock (M2 QA Round-2 P1-1)."""
from __future__ import annotations

import multiprocessing as mp
import sys
import tempfile
import time
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
