#!/usr/bin/env python
"""`tools/lib/failure_log_rotation.py` 的回歸鎖（DEF-200-162）。

WHY：修前 `.last_failure.log` 是固定檔名、每次覆寫、且 gitignored——下一次執行就把上一次
的失敗證據抹掉。本檔鎖住：檔名帶時間戳／HEAD 短碼（不覆寫彼此）、輪替只留最近 N 份。
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import failure_log_rotation as F  # noqa: E402


class TestFailureLogPath(unittest.TestCase):
    def test_filename_embeds_timestamp_and_head_sha(self) -> None:
        with mock.patch.object(F, "_head_short_sha", return_value="abc1234"):
            p = F.failure_log_path(Path("/tmp/x"), when=1_700_000_000)
        self.assertIn("abc1234", p.name)
        self.assertTrue(p.name.startswith(".last_failure_"))
        self.assertTrue(p.name.endswith(".log"))

    def test_two_calls_at_different_times_do_not_collide(self) -> None:
        with mock.patch.object(F, "_head_short_sha", return_value="deadbee"):
            p1 = F.failure_log_path(Path("/tmp/x"), when=1_700_000_000)
            p2 = F.failure_log_path(Path("/tmp/x"), when=1_700_000_001)
        self.assertNotEqual(p1, p2, "不同時刻的檔名相同 ⇒ 仍會互相覆寫，鎖沒有承重")

    def test_git_unavailable_falls_back_to_a_stable_literal(self) -> None:
        """git 不可用時（非 git repo／git 不存在）不得崩潰，退化成一個穩定字面。"""
        with mock.patch.object(F, "_head_short_sha", return_value=None):
            p = F.failure_log_path(Path("/tmp/x"), when=1_700_000_000)
        self.assertIn("nogit", p.name)


class TestPruneOldFailureLogs(unittest.TestCase):
    def test_keeps_only_the_most_recent_n(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            paths = []
            for i in range(5):
                p = d / f".last_failure_sha{i}_2026010{i}T000000Z.log"
                p.write_text("x", encoding="utf-8")
                # mtime 需嚴格遞增，且部分檔案系統時間戳解析度粗（可到秒級），逐檔顯式錯開。
                import os
                os.utime(p, (1_700_000_000 + i, 1_700_000_000 + i))
                paths.append(p)
            removed = F.prune_old_failure_logs(d, keep=2)
        self.assertEqual(len(removed), 3, "5 份只留 2 份，應刪 3 份")
        self.assertEqual({p.name for p in removed}, {p.name for p in paths[:3]},
                          "刪的應是最舊的 3 份，不是任意 3 份")

    def test_fewer_than_keep_removes_nothing(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / ".last_failure_a_1.log").write_text("x", encoding="utf-8")
            removed = F.prune_old_failure_logs(d, keep=F.KEEP_RECENT)
        self.assertEqual(removed, [])

    def test_only_matches_the_failure_log_glob(self) -> None:
        """輪替不得誤刪別的檔（同目錄下其他 .log 或非 log 檔案必須全身而退）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            unrelated = d / "unrelated.log"
            unrelated.write_text("x", encoding="utf-8")
            for i in range(3):
                p = d / f".last_failure_sha{i}_2026010{i}T000000Z.log"
                p.write_text("x", encoding="utf-8")
            F.prune_old_failure_logs(d, keep=0)
            self.assertTrue(unrelated.exists(), "無關檔案被誤刪 ⇒ glob 過寬")


if __name__ == "__main__":
    unittest.main()
