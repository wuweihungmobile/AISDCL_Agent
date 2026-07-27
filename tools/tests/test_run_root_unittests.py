"""run_root_unittests.py — 數量下限釘選的回歸鎖（R10 QA-2，DEF-101-127）。

WHY（測意圖非僅行為）：`python -m unittest discover` 對 0 個測試回 rc=0，
「跑了 0 個測試也算 PASS」是結構性 fail-open——本測試鎖住包裝器的兩條語意：
(1) 低於下限＝紅燈且不執行；(2) 達下限＝執行並回傳真實結果。
並以真 repo 斷言下限釘選對當前樹成立（防 MIN_TESTS 與現況脫節）。
"""
from __future__ import annotations

import inspect
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests  # noqa: E402


class RatchetDriftWarningTest(unittest.TestCase):
    """R57 新增：下限 ratchet 過期提醒（`ratchet_drift_message`）。

    WHY（測意圖）：R15 把 MIN_TESTS 釘在 290 後**連續 11 輪沒人重釘**，到 R57 時
    實況已 530——下限只擋得住「蒸發 240 支以上」，鑑別力失效 45%，而整段期間
    閘門完全沒吭過聲。人工 ratchet 沒有自我提醒就必然腐化，本測試鎖住那道提醒
    真的會在漂移超過門檻時出現、且不會在正常範圍內吵人（吵人的警告會被無視，
    等於沒有）。
    """

    def test_no_warning_within_ratio(self) -> None:
        self.assertIsNone(run_root_unittests.ratchet_drift_message(100, 100))
        self.assertIsNone(run_root_unittests.ratchet_drift_message(110, 100))

    def test_warns_beyond_ratio_and_names_the_new_value(self) -> None:
        msg = run_root_unittests.ratchet_drift_message(111, 100)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("111", msg, "提醒必須直接給出該重釘的數字，否則還要人自己算")
        self.assertIn("MIN_TESTS", msg)

    def test_warn_layer_fires_before_stale_layer_blocks(self) -> None:
        """兩層門檻必須真的不同（R57 round 1 ARCH-06）：若 WARN 與紅線同值，
        「只 WARN 不 fail」就是假的——WARN 一響閘門同時已紅，緩衝區為空。
        本測試鎖住 [WARN, STALE] 之間存在非空區間，且該區間內只提醒不阻擋。"""
        self.assertLess(
            run_root_unittests.RATCHET_WARN_RATIO,
            run_root_unittests.RATCHET_STALE_RATIO,
            "WARN 倍數必須嚴格小於紅線倍數，否則 WARN 層無存在意義",
        )
        between = int(100 * run_root_unittests.RATCHET_WARN_RATIO) + 1
        self.assertIsNotNone(
            run_root_unittests.ratchet_drift_message(between, 100),
            "緩衝區下緣應已提醒",
        )
        self.assertIsNone(
            run_root_unittests.ratchet_drift_message(
                between, 100, run_root_unittests.RATCHET_STALE_RATIO
            ),
            "緩衝區內不得讓閘門變紅——那就退化成單一門檻",
        )

    def test_current_pin_is_not_already_stale(self) -> None:
        """本 repo 當下的 MIN_TESTS 不得已過期到**紅線**（`RATCHET_STALE_RATIO`）
        ——純 WARN 會被當背景噪音無視（正是 R15 起連續 11 輪沒人重釘的心理機制），
        必須有一道會紅的線。刻意用紅線倍數而非 WARN 倍數：在 [WARN, STALE] 這段
        緩衝區內只該被提醒、不該被擋（見 run_root_unittests 的兩層設計註解）。

        鑑別力邊界（不做「保鮮」的絕對宣稱）：本斷言的通過區間是
        MIN_TESTS ∈ [count / RATCHET_STALE_RATIO, count]，以 count=560 為例即
        [448, 560]——它擋得住 R15 那種釘 290 的極端腐化，**擋不住**「釘在 450」
        這種中度失準的新 pin（QA-R57-07 實測）。中度失準由 WARN 層先吭聲。
        """
        count = run_root_unittests.discover_suite(
            run_root_unittests._TESTS_DIR
        ).countTestCases()
        self.assertIsNone(
            run_root_unittests.ratchet_drift_message(
                count, run_root_unittests.MIN_TESTS, run_root_unittests.RATCHET_STALE_RATIO
            ),
            f"MIN_TESTS={run_root_unittests.MIN_TESTS} 相對實況 {count} 已過期到紅線，"
            "請重釘（R57 起本斷言即為 ratchet 的機械保鮮期）",
        )


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
        tagged_ids = run_root_unittests.windows_native_skips(result)
        self.assertEqual(len(tagged_ids), 1)
        self.assertIn("test_tagged", tagged_ids[0])

    def test_plain_skip_is_not_flagged(self):
        result = self._run_fixture(tagged_condition=True, plain_condition=False)
        tagged_ids = run_root_unittests.windows_native_skips(result)
        self.assertEqual(tagged_ids, [], "一般性 skip（無標籤）不應被誤標為 Windows 專屬未驗證")

    def test_no_skips_reports_empty(self):
        result = self._run_fixture(tagged_condition=True, plain_condition=True)
        tagged_ids = run_root_unittests.windows_native_skips(result)
        self.assertEqual(tagged_ids, [])



class DumpFailureDetailTest(unittest.TestCase):
    """R57 round 3 ARCH-R57R3-03：非決定性翻紅（1/14）當時無失敗明細可查，落檔補上。"""

    def _result_with(self, failures=(), errors=()):
        class _T:
            def __init__(self, tid): self._tid = tid
            def id(self): return self._tid
        r = unittest.TestResult()
        r.failures = [(_T(t), tb) for t, tb in failures]
        r.errors = [(_T(t), tb) for t, tb in errors]
        return r

    def test_unexpected_successes_are_named(self) -> None:
        """R57 round 4 SA-R57R4-01：`wasSuccessful()` 對 unexpectedSuccesses 亦回
        False，若明細不含它們就會出現「rc=1 但明細不指名任何測試」的空落檔。"""
        class _T:
            def id(self): return "m.C.test_unexpected"
        r = unittest.TestResult()
        r.unexpectedSuccesses = [_T()]
        self.assertFalse(r.wasSuccessful(), "前提失效：unexpectedSuccesses 應使執行判為失敗")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "f.log"
            run_root_unittests.dump_failure_detail(r, target)
            text = target.read_text(encoding="utf-8")
        self.assertIn("m.C.test_unexpected", text, "unexpectedSuccesses 未被指名＝空明細")
        self.assertIn("1 unexpected successes", text, "標頭未計入 unexpectedSuccesses")

    def test_writes_test_ids_and_tracebacks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "f.log"
            run_root_unittests.dump_failure_detail(
                self._result_with(
                    failures=[("m.C.test_a", "AssertionError: boom")],
                    errors=[("m.C.test_b", "RuntimeError: kaboom")],
                ),
                target,
            )
            text = target.read_text(encoding="utf-8")
        for expected in ("m.C.test_a", "AssertionError: boom", "m.C.test_b", "RuntimeError: kaboom"):
            self.assertIn(expected, text, f"失敗明細未含 {expected!r}——落檔對診斷無用")

    def test_write_failure_does_not_raise(self) -> None:
        """診斷輔助不得反過來變成新的失敗來源（寫檔失敗只印警告、不拋）。"""
        unwritable = Path(tempfile.gettempdir()) / "r57_no_such_dir" / "sub" / "f.log"
        run_root_unittests.dump_failure_detail(self._result_with(failures=[("m.C.t", "tb")]), unwritable)

    def test_only_called_when_run_is_unsuccessful(self) -> None:
        """全綠時不得落檔（否則每次成功執行都留下誤導性的 .last_failure.log）。"""
        src = inspect.getsource(run_root_unittests.run_with_floor)
        self.assertIn("if not result.wasSuccessful():", src)
        self.assertIn("dump_failure_detail(result)", src)
        guard_at = src.index("if not result.wasSuccessful():")
        self.assertLess(guard_at, src.index("dump_failure_detail(result)"),
                        "落檔呼叫必須在 wasSuccessful 守衛之內")


if __name__ == "__main__":
    unittest.main()
