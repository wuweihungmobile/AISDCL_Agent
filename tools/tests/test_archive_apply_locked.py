#!/usr/bin/env python3
"""`tools/archive_apply_locked.py` 的回歸鎖（DEF-200-222 判準②的 CLI 外殼）。

本檔驗兩件事，皆為「外殼有沒有真的接上鎖與底層 apply()」，不重跑
`archive_defect_log.apply()` 本身的判準（那些鎖住在 `tools/tests/test_archive_defect_log.py`）：
  1. 正常路徑：取得鎖後才呼叫 `archive_defect_log.apply()`，引數原封不動轉送。
  2. 鎖被佔用時：不呼叫 `apply()`，直接 fail-loud 回傳非 0。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import archive_apply_locked as wrapper  # noqa: E402
import archive_defect_log as adl  # noqa: E402

_TMP_DIR = Path(tempfile.mkdtemp(prefix="archive_apply_locked_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))


class TestWrapperForwardsUnderLock(unittest.TestCase):
    def test_apply_is_called_with_parsed_arguments_while_holding_the_lock(
        self,
    ) -> None:
        lock_path = _TMP_DIR / "forward_test.lock"
        if lock_path.exists():
            lock_path.unlink()
        seen_during_apply: dict[str, object] = {}

        def fake_apply(archive_num, ack, note, only, keep):  # noqa: ANN001
            # 斷言呼叫 apply() 的當下鎖檔確實存在——證明「先取鎖、再委派」的順序關係，
            # 不是鎖與委派各自獨立、恰好都發生過。
            seen_during_apply["lock_held"] = lock_path.exists()
            seen_during_apply["args"] = (archive_num, ack, note, only, keep)
            return 0

        with mock.patch.object(wrapper, "_LOCK_PATH", lock_path), \
             mock.patch.object(adl, "apply", side_effect=fake_apply):
            rc = wrapper.main([
                "--archive-num", "31",
                "--ack-handoff", "DEF-1-1,DEF-2-2",
                "--note", "測試備註",
                "--only", "DEF-1-1",
                "--keep", "DEF-2-2",
            ])
        self.assertEqual(rc, 0)
        self.assertTrue(seen_during_apply.get("lock_held"),
                         "呼叫 apply() 當下鎖檔應存在——委派必須發生在取鎖之後")
        self.assertEqual(
            seen_during_apply["args"],
            (31, frozenset({"DEF-1-1", "DEF-2-2"}), "測試備註",
             frozenset({"DEF-1-1"}), frozenset({"DEF-2-2"})))
        self.assertFalse(lock_path.exists(), "委派完成後鎖應被釋放")

    def test_lock_busy_prevents_apply_and_returns_nonzero(self) -> None:
        lock_path = _TMP_DIR / "busy_test.lock"
        lock_path.write_text("777777\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
        apply_called = []

        def fake_apply(*args, **kwargs):  # noqa: ANN002,ANN003
            apply_called.append(True)
            return 0

        try:
            with mock.patch.object(wrapper, "_LOCK_PATH", lock_path), \
                 mock.patch.object(wrapper, "_LOCK_TIMEOUT_SECONDS", 0.3), \
                 mock.patch.object(adl, "apply", side_effect=fake_apply), \
                 contextlib.redirect_stderr(io.StringIO()) as err:
                rc = wrapper.main(["--archive-num", "31"])
            self.assertNotEqual(rc, 0, "鎖被佔用時應 fail-loud，不得回傳 0")
            self.assertEqual(apply_called, [], "鎖被佔用時不應委派給 apply()")
            self.assertIn("777777", err.getvalue(),
                          "錯誤訊息應指名持鎖者，讓使用者知道卡在哪裡")
        finally:
            lock_path.unlink()

    def test_unknown_flag_is_rejected_by_argparse(self) -> None:
        """argparse 內建的未知旗標拒收——本檔不必另接 `_cli_flags`，天生就會 rc!=0。"""
        with contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaises(SystemExit) as ctx:
            wrapper.main(["--archive-num", "1", "--bogus-flag-xyz"])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_missing_required_archive_num_is_rejected(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaises(SystemExit) as ctx:
            wrapper.main([])
        self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
