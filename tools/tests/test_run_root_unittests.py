"""run_root_unittests.py — 數量下限釘選的回歸鎖（R10 QA-2，DEF-101-127）。

WHY（測意圖非僅行為）：`python -m unittest discover` 對 0 個測試回 rc=0，
「跑了 0 個測試也算 PASS」是結構性 fail-open——本測試鎖住包裝器的兩條語意：
(1) 低於下限＝紅燈且不執行；(2) 達下限＝執行並回傳真實結果。
並以真 repo 斷言下限釘選對當前樹成立（防 MIN_TESTS 與現況脫節）。
"""
from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests  # noqa: E402


class RunRootUnittestsTest(unittest.TestCase):
    def _make_fixture(self, tmp_name: str, n_tests: int) -> Path:
        import tempfile

        d = Path(tempfile.mkdtemp(prefix=tmp_name))
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        # 模組名帶 fixture 前綴唯一化：同名模組已在 sys.modules（來自另一個 tmp 目錄）
        # 時，unittest discover 會判 "Start directory is not importable"。
        mod_name = f"test_fixture_{tmp_name.rstrip('_')}"
        self.addCleanup(lambda: sys.modules.pop(mod_name, None))
        body = "\n".join(
            f"    def test_{i}(self):\n        self.assertTrue(True)" for i in range(n_tests)
        )
        (d / f"{mod_name}.py").write_text(
            textwrap.dedent(
                """\
                import unittest


                class Dummy(unittest.TestCase):
                """
            )
            + body
            + "\n",
            encoding="utf-8",
        )
        return d

    def test_below_floor_fails_without_running(self):
        d = self._make_fixture("rru_below_", 2)
        rc = run_root_unittests.run_with_floor(d, min_tests=5)
        self.assertEqual(rc, 1, "低於下限必須 exit 1（0-test fail-open 的同構防護）")

    def test_at_floor_runs_and_passes(self):
        d = self._make_fixture("rru_at_", 3)
        rc = run_root_unittests.run_with_floor(d, min_tests=3)
        self.assertEqual(rc, 0)

    def test_real_repo_meets_pinned_floor(self):
        """真樹鎖：當前 tools/tests 發現數必須 >= MIN_TESTS（釘選與現況不脫節）。"""
        suite = run_root_unittests.discover_suite(run_root_unittests._TESTS_DIR)
        self.assertGreaterEqual(suite.countTestCases(), run_root_unittests.MIN_TESTS)


class ReportWindowsNativeSkipsTest(unittest.TestCase):
    """R43 Architect P1（DEF-101-348 方向①）：`[WINDOWS-NATIVE-ONLY]` 標籤的 skip
    必須從一般 `skipped=N` 摘要中被獨立點名，不能混在裡面看不出來。"""

    def _run_fixture(self, tagged_condition: bool, plain_condition: bool):
        class _Dummy(unittest.TestCase):
            @unittest.skipUnless(tagged_condition, "[WINDOWS-NATIVE-ONLY] 僅原生 Windows 才具驗證價值")
            def test_tagged(self):
                pass

            @unittest.skipUnless(plain_condition, "本機缺某工具，一般性 skip")
            def test_plain(self):
                pass

            def test_always_runs(self):
                self.assertTrue(True)

        suite = unittest.TestLoader().loadTestsFromTestCase(_Dummy)
        result = unittest.TestResult()
        suite.run(result)
        return result

    def test_tagged_skip_is_singled_out(self):
        result = self._run_fixture(tagged_condition=False, plain_condition=True)
        tagged_ids = run_root_unittests.report_windows_native_skips(result)
        self.assertEqual(len(tagged_ids), 1)
        self.assertIn("test_tagged", tagged_ids[0])

    def test_plain_skip_is_not_flagged(self):
        result = self._run_fixture(tagged_condition=True, plain_condition=False)
        tagged_ids = run_root_unittests.report_windows_native_skips(result)
        self.assertEqual(tagged_ids, [], "一般性 skip（無標籤）不應被誤標為 Windows 專屬未驗證")

    def test_no_skips_reports_empty(self):
        result = self._run_fixture(tagged_condition=True, plain_condition=True)
        tagged_ids = run_root_unittests.report_windows_native_skips(result)
        self.assertEqual(tagged_ids, [])


if __name__ == "__main__":
    unittest.main()
