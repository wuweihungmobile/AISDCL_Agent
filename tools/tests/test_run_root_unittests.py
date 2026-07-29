"""run_root_unittests.py — 數量下限釘選的回歸鎖（R10 QA-2，DEF-101-127）。

WHY（測意圖非僅行為）：`python -m unittest discover` 對 0 個測試回 rc=0，
「跑了 0 個測試也算 PASS」是結構性 fail-open——本測試鎖住包裝器的兩條語意：
(1) 低於下限＝紅燈且不執行；(2) 達下限＝執行並回傳真實結果。
並以真 repo 斷言下限釘選對當前樹成立（防 MIN_TESTS 與現況脫節）。
"""
from __future__ import annotations

import contextlib
import inspect
import io
import shutil
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

    # ── DEF-101-510（R59）：反方向的可見度 ───────────────────────────────────
    # 上面三支鎖的是「標籤 skip 要被獨立點名」；R59 於真 Windows 11 實機量到
    # `skipped=11` 而 **11 支全部無標籤**，其中兩支是真正的覆蓋損失（見
    # `run_root_unittests.report_all_skips` docstring）。故補鎖「未標籤的 skip
    # 也必須連理由一起被印出來」——否則只印一個 `skipped=N` 等於沒印。

    def test_reporters_are_actually_wired_into_run_with_floor(self):
        """QA-R59-02：單元測了但**沒接線**是本 repo 最常見的假綠形狀。

        上面 5 支鎖全部直接呼叫 `report_all_skips(result)`，沒有一支斷言 `run_with_floor`
        真的呼叫它——刪掉 runner 裡那一行，5 支鎖照樣全綠，runner 回到只印 `skipped=N`，
        DEF-101-510 完全復發。技法（`inspect.getsource`）R57 已為 `dump_failure_detail`
        用過（見本檔 DumpFailureDetailTest），本輪補上並順手把既有債
        `report_windows_native_skips` 一併鎖住。
        """
        src = inspect.getsource(run_root_unittests.run_with_floor)
        for fn in ("report_windows_native_skips(result)", "report_all_skips(result)"):
            self.assertIn(
                fn, src,
                f"run_with_floor 未呼叫 {fn}——reporter 存在但沒接線，"
                f"等於沒有（DEF-101-510／QA-R59-02）",
            )

    def test_all_skips_includes_untagged_with_reason(self):
        result = self._run_fixture(tagged_condition=False, plain_condition=False)
        entries = run_root_unittests.all_skips(result)
        self.assertEqual(len(entries), 2, "全部 skip 都要在清單裡（含未標籤者）")
        by_reason = {tid: reason for tid, reason in entries}
        plain = [t for t in by_reason if "test_plain" in t]
        self.assertEqual(len(plain), 1, "未標籤的一般性 skip 必須被納入")
        self.assertIn(
            "本機缺某工具", by_reason[plain[0]],
            "必須連 skip 理由一起回傳——只有 id 無法判斷是平台語意還是環境降級",
        )

    def test_report_all_skips_prints_untagged_entries(self):
        result = self._run_fixture(tagged_condition=True, plain_condition=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            entries = run_root_unittests.report_all_skips(result)
        out = buf.getvalue()
        self.assertEqual(len(entries), 1)
        self.assertIn("test_plain", out, "未標籤 skip 的 id 必須出現在輸出裡")
        self.assertIn("本機缺某工具", out, "未標籤 skip 的理由必須出現在輸出裡")
        self.assertIn("[未標籤]", out, "須標示該筆未帶 WINDOWS-NATIVE-ONLY 標籤")

    def test_report_all_skips_is_silent_when_nothing_skipped(self):
        """零 skip 時不得產生噪音——常亮輸出會退化成背景雜訊（同 MIN_TESTS
        兩層門檻設計對「常亮警告」的既有判斷）。"""
        result = self._run_fixture(tagged_condition=True, plain_condition=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            entries = run_root_unittests.report_all_skips(result)
        self.assertEqual(entries, [])
        self.assertEqual(buf.getvalue(), "")

    def test_all_skips_is_pure_no_stdout(self):
        """比照 `windows_native_skips` 的既有紀律（R43 二審 SA）：純函式不得有列印
        副作用，否則本檔自測時會把 fixture 的假 id 印進真實終端混淆複審者。"""
        result = self._run_fixture(tagged_condition=False, plain_condition=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_root_unittests.all_skips(result)
        self.assertEqual(buf.getvalue(), "")



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


class CollectionIntegrityTest(unittest.TestCase):
    """R60 Pkg-P8：收集面完整性——「有檔沒被收到」必須紅，且不得被 MIN_TESTS 漏掉。

    WHY（測意圖，非僅行為）：R60 並行修復期間三次量測分別得到 894／906／916，被立案
    當成「並行負載下 discovery 收集數不決定性、疑為第四個並行假紅成因」追查。實際根因
    是**磁碟真的變了**——同一支 `test_check_defect_log_crossref.py` 被另一個並行包從
    29 支測試逐步擴充到 51 支，而其餘 52 支檔固定貢獻 865 支，故
    865+29=894、865+41=906、865+51=916，三個數字是三個時間切片，沒有一次是 race。
    追查過程暴露兩個**與該事件無關、但真實存在且當時完全無守門**的缺口，本類別鎖住：
      ① **下限語意的盲區**：實況 916 vs 下限 845 ⇒ 可靜默蒸發 71 支測試仍印 ✅；
      ② **沒被收集的測試不出現在任何一行輸出裡**——它從未被 loader 交給 runner，
         故既不在 `skipped=N`、也不在 `report_all_skips` 明細裡（這就是「靜默」的核心）。
    """

    _seq = 0

    def _sandbox(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="p8_collect_"))
        self.addCleanup(lambda: shutil.rmtree(d, ignore_errors=True))
        return d

    def _unique_stem(self) -> str:
        CollectionIntegrityTest._seq += 1
        # 模組名唯一化：同名模組殘留在 sys.modules（來自另一個 tmp 目錄）時，
        # discover 會誤判 "Start directory is not importable"（沿用本檔既有慣例）。
        stem = f"test_p8fx{CollectionIntegrityTest._seq}"
        self.addCleanup(lambda: sys.modules.pop(stem, None))
        return stem

    def _write_raw(self, d: Path, body: str) -> str:
        stem = self._unique_stem()
        (d / f"{stem}.py").write_text(body, encoding="utf-8")
        return stem

    def _write_tests(self, d: Path, n: int) -> str:
        methods = "\n".join(
            f"    def test_{i}(self):\n        self.assertTrue(True)" for i in range(n)
        )
        return self._write_raw(
            d,
            textwrap.dedent(
                """\
                import unittest


                class Dummy(unittest.TestCase):
                """
            )
            + methods
            + "\n",
        )

    @staticmethod
    def _quiet_run(start_dir: Path, min_tests: int) -> tuple[int, str]:
        """跑 run_with_floor 並吞掉輸出——fixture 的假檔名不該印進真實終端混淆複審者
        （沿用本檔 `windows_native_skips` 一系列測試已建立的紀律）。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = run_root_unittests.run_with_floor(start_dir, min_tests=min_tests)
        return rc, out.getvalue() + err.getvalue()

    # ── ① 鑑別力注入：磁碟上有檔、卻一支測試都沒被收集 ──────────────────────
    def test_gap_detected_when_a_file_contributes_zero_tests(self) -> None:
        d = self._sandbox()
        self._write_tests(d, 3)
        orphan = self._write_raw(d, "PLACEHOLDER = 1  # 符合 test_*.py 但無任何 TestCase\n")
        suite = run_root_unittests.discover_suite(d)
        self.assertEqual(
            run_root_unittests.collection_gaps(suite, d),
            [orphan],
            "磁碟上有 test_*.py 卻零貢獻＝收集面缺口，必須被指名",
        )

    def test_no_gaps_when_every_file_contributes(self) -> None:
        d = self._sandbox()
        self._write_tests(d, 2)
        self._write_tests(d, 1)
        suite = run_root_unittests.discover_suite(d)
        self.assertEqual(run_root_unittests.collection_gaps(suite, d), [])

    def test_run_with_floor_reds_on_gap_although_count_clears_the_floor(self) -> None:
        """本包的核心斷言：**下限通過**但收集面有缺口時，閘門必須紅。

        修復前的行為（構造證明缺口真實存在）：`count(3) >= min_tests(1)` 成立 ⇒
        舊 `run_with_floor` 只看這一個條件就印 ✅ 並回 0，缺的那支檔全程無聲。
        """
        d = self._sandbox()
        self._write_tests(d, 3)
        orphan = self._write_raw(d, "NOTHING_HERE = True\n")
        count = run_root_unittests.discover_suite(d).countTestCases()
        self.assertGreaterEqual(count, 1, "前提：本 fixture 的總數確實高於下限")
        rc, output = self._quiet_run(d, min_tests=1)
        self.assertEqual(rc, 1, "下限之上的收集面缺口必須讓閘門變紅，否則就是靜默通過")
        self.assertIn(orphan, output, "必須指名是哪一支檔沒被收集，否則無法定位")

    def test_uncollected_file_is_invisible_in_every_skip_channel(self) -> None:
        """「靜默」的核心：沒被收集 ≠ 被 skip。前者不在 `skipped=N`、不在
        `all_skips()` 明細，完全不留痕跡——這正是 MIN_TESTS 之外必須另設一層的理由。"""
        d = self._sandbox()
        self._write_tests(d, 2)
        orphan = self._write_raw(d, "X = 0\n")
        suite = run_root_unittests.discover_suite(d)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, 2, "orphan 檔完全沒被交給 runner")
        self.assertEqual(
            run_root_unittests.all_skips(result), [],
            "沒被收集的檔案不會產生任何 skip 記錄——證明它在既有輸出通道裡完全隱形",
        )
        self.assertIn(orphan, run_root_unittests.collection_gaps(suite, d))

    def test_exempt_entry_suppresses_the_gap(self) -> None:
        """例外必須**具名**才生效（不提供整批略過的開關）。"""
        d = self._sandbox()
        self._write_tests(d, 1)
        orphan = self._write_raw(d, "Y = 1\n")
        suite = run_root_unittests.discover_suite(d)
        self.assertEqual(
            run_root_unittests.collection_gaps(suite, d, exempt=frozenset({orphan})), []
        )
        self.assertEqual(
            run_root_unittests._COLLECTION_EXEMPT, frozenset(),
            "現況不該有任何合法例外；真要加必須逐檔具名並註明理由",
        )

    # ── ② discovery 佔位測試：N 支塌成 1 支，計數靜默減少 ────────────────────
    def test_module_level_skiptest_collapses_module_and_is_named(self) -> None:
        """`ModuleSkipped` 是真正的 fail-open：整支模組覆蓋消失而 **rc 仍為 0**。"""
        d = self._sandbox()
        self._write_tests(d, 2)
        collapsed = self._write_raw(
            d,
            "import unittest\n\nraise unittest.SkipTest('模組層 skip')\n\n\n"
            "class Dummy(unittest.TestCase):\n"
            + "\n".join(f"    def test_{i}(self):\n        pass" for i in range(9))
            + "\n",
        )
        suite = run_root_unittests.discover_suite(d)
        placeholders = run_root_unittests.discovery_placeholders(suite)
        self.assertEqual(
            placeholders, [(collapsed, "ModuleSkipped")],
            "模組層 SkipTest 讓 9 支測試塌成 1 支佔位測試，必須被點名",
        )
        self.assertEqual(
            suite.countTestCases(), 3,
            "前提：9 支塌成 1 支（2+1），總數靜默少 8 支而下限完全沒感覺",
        )
        rc, output = self._quiet_run(d, min_tests=1)
        self.assertEqual(rc, 1, "覆蓋整份消失卻回 0＝fail-open，必須改判為紅")
        self.assertIn(collapsed, output)

    def test_import_error_placeholder_is_named(self) -> None:
        d = self._sandbox()
        self._write_tests(d, 1)
        broken = self._write_raw(d, "import a_module_that_does_not_exist_p8\n")
        suite = run_root_unittests.discover_suite(d)
        self.assertEqual(
            run_root_unittests.discovery_placeholders(suite), [(broken, "_FailedTest")]
        )
        rc, output = self._quiet_run(d, min_tests=1)
        self.assertEqual(rc, 1)
        self.assertIn(broken, output, "必須指名是哪一支檔 import 失敗")

    def test_placeholder_run_still_yields_traceback(self) -> None:
        """佔位測試刻意**不**提早 return：提早 return 會丟掉唯一的 ImportError
        traceback（R57 建立 `.last_failure.log` 機制的整個目的就是留下可歸因資訊）。"""
        src = inspect.getsource(run_root_unittests.run_with_floor)
        run_at = src.index("TextTestRunner")
        self.assertLess(
            src.index("report_discovery_placeholders(suite)"), run_at,
            "佔位測試須在執行前就先點名（長時間跑完才說太晚）",
        )
        self.assertIn("not placeholders", src, "佔位測試必須影響最終 rc")

    # ── ③ 主修：盤存指紋讓跨次數字可比較 ───────────────────────────────────
    def test_fingerprint_differs_when_a_file_grows_though_filecount_is_equal(self) -> None:
        """對症 R60 真正的根因：檔數不變、某支檔變胖 ⇒ 收集數本來就會變。
        指紋必須能把這件事和「同一棵樹量到不同數字」分開。"""
        d = self._sandbox()
        stem = self._write_tests(d, 2)
        before = run_root_unittests.inventory_fingerprint(d)
        self.assertEqual(
            before, run_root_unittests.inventory_fingerprint(d), "同一棵樹指紋必須穩定"
        )
        (d / f"{stem}.py").write_text(
            (d / f"{stem}.py").read_text(encoding="utf-8")
            + "    def test_added(self):\n        pass\n",
            encoding="utf-8",
        )
        after = run_root_unittests.inventory_fingerprint(d)
        self.assertEqual(before[0], after[0], "檔數相同——單看檔數分辨不出樹變了")
        self.assertNotEqual(before[1], after[1], "指紋必須改變，否則無法識破『樹變了』")

    def test_fingerprint_is_printed_by_run_with_floor(self) -> None:
        """QA 紀律：單元測了但沒接線是本 repo 最常見的假綠形狀（比照
        `test_reporters_are_actually_wired_into_run_with_floor`）。"""
        d = self._sandbox()
        self._write_tests(d, 2)
        _, fingerprint = run_root_unittests.inventory_fingerprint(d)
        rc, output = self._quiet_run(d, min_tests=1)
        self.assertEqual(rc, 0)
        self.assertIn(fingerprint, output, "指紋必須真的印出來，否則跨次比較無從進行")

    # ── ④ 真樹鎖 ────────────────────────────────────────────────────────────
    def test_real_repo_has_no_collection_gaps(self) -> None:
        """真樹鎖：tools/tests 底下每一支 test_*.py 都必須至少貢獻一支測試。
        比 `MIN_TESTS` 強得多——它抓「有檔沒被收到」，不是「總數掉太多」。"""
        tests_dir = run_root_unittests._TESTS_DIR
        suite = run_root_unittests.discover_suite(tests_dir)
        self.assertEqual(
            run_root_unittests.collection_gaps(suite, tests_dir), [],
            "有 test_*.py 檔案零貢獻——測試靜默消失，且總數下限抓不到",
        )
        self.assertEqual(
            run_root_unittests.discovery_placeholders(suite), [],
            "真樹不得有 discovery 佔位測試（import 失敗／模組層 SkipTest）",
        )

    def test_real_repo_module_count_matches_disk_file_count(self) -> None:
        tests_dir = run_root_unittests._TESTS_DIR
        suite = run_root_unittests.discover_suite(tests_dir)
        on_disk = {p.stem for p in tests_dir.glob("test_*.py")}
        self.assertEqual(
            set(run_root_unittests.suite_modules(suite)), on_disk,
            "收集到的模組集合必須與磁碟上的 test_*.py 集合完全相等",
        )


class ExecutionGapTest(unittest.TestCase):
    """R60 Pkg-P8：**收集數 ≠ 執行數**——下限守門結構性看不到的一整類覆蓋損失。

    WHY（測意圖）：`MIN_TESTS`／ratchet 守的是 `countTestCases()`（收集數），但真正
    跑了幾支是 `result.testsRun`。`setUpClass`／`setUpModule` 拋 `SkipTest` 時，
    `TestSuite.run` 對該類別每支測試走 `continue`、`test(result)` 從未被呼叫 ⇒
    `testsRun` 不增加，而收集數**完全不變**。實測（本類別 fixture）：收集 11／執行 2／
    `result.skipped` 只多一筆 `setUpClass (...)`／`wasSuccessful()` 仍為 True ⇒ rc=0。
    整個類別的覆蓋無聲消失，下限守的那個數字連動都沒動。本 repo 正在使用該模式
    （`test_macos_smoke_skip_honesty.TestSummaryTailRealRun.setUpClass` 缺 bash 時
    `raise SkipTest`），故這是實況風險而非理論風險。
    """

    @staticmethod
    def _suite_with_class_fixture(n: int, exc: Exception | None):
        class WholeClass(unittest.TestCase):
            @classmethod
            def setUpClass(cls) -> None:
                if exc is not None:
                    raise exc

        for i in range(n):
            setattr(WholeClass, f"test_{i}", lambda self: None)
        return unittest.TestLoader().loadTestsFromTestCase(WholeClass)

    def _run(self, n: int, exc: Exception | None):
        suite = self._suite_with_class_fixture(n, exc)
        collected = suite.countTestCases()
        result = unittest.TestResult()
        suite.run(result)
        return collected, result

    def test_setupclass_skip_hides_whole_class_from_execution(self) -> None:
        collected, result = self._run(9, unittest.SkipTest("環境缺工具"))
        self.assertEqual(collected, 9, "收集數不受 setUpClass skip 影響——下限守門結構性失效")
        self.assertEqual(result.testsRun, 0, "整個類別一支都沒跑")
        self.assertTrue(result.wasSuccessful(), "前提：rc 仍為 0，這正是 fail-open 之處")
        self.assertEqual(
            len(result.skipped), 1,
            "只多一筆 skip——`skipped=N` 完全不提這一筆吃掉了 9 支",
        )

    def test_execution_gap_is_reported_with_the_count_and_the_culprit(self) -> None:
        collected, result = self._run(9, unittest.SkipTest("環境缺工具"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            gap = run_root_unittests.report_execution_gap(collected, result)
        out = buf.getvalue()
        self.assertEqual(gap, 9)
        self.assertIn("9", out, "必須把「幾支沒跑」這個數字印出來")
        self.assertIn("setUpClass", out, "必須點名是哪個 fixture 吃掉了它們")

    def test_no_gap_is_silent(self) -> None:
        """零差額不得產生噪音（同 report_all_skips 對常亮輸出的既有判斷）。"""
        collected, result = self._run(3, None)
        self.assertEqual((collected, result.testsRun), (3, 3))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(run_root_unittests.report_execution_gap(collected, result), 0)
        self.assertEqual(buf.getvalue(), "")

    def test_method_level_skip_does_not_create_a_gap(self) -> None:
        """鑑別力邊界：方法層 skip **會**計入 testsRun（`TestCase.run` 先
        `startTest()` 才判 skip），故不該被誤報成執行差額——只有 fixture 層才會。"""

        class MethodSkip(unittest.TestCase):
            @unittest.skipUnless(False, "方法層 skip")
            def test_skipped(self) -> None: ...

            def test_ran(self) -> None: ...

        suite = unittest.TestLoader().loadTestsFromTestCase(MethodSkip)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(
            run_root_unittests.report_execution_gap(suite.countTestCases(), result), 0,
            "方法層 skip 不是執行差額，誤報會讓這道守門變成背景噪音",
        )

    def test_fixture_entries_distinguish_holder_from_real_testcase(self) -> None:
        _, result = self._run(4, RuntimeError("setUpClass 炸了"))
        self.assertEqual(len(run_root_unittests.fixture_level_entries(result)), 1)
        self.assertIn("setUpClass", run_root_unittests.fixture_level_entries(result)[0])

        _, clean = self._run(2, None)
        self.assertEqual(
            run_root_unittests.fixture_level_entries(clean), [],
            "正常執行不得產生 fixture 層條目",
        )

    def test_unexplained_gap_reds_but_attributable_gap_does_not(self) -> None:
        """設計取捨的鑑別力：可歸因的差額只點名（避免缺工具機器假紅），
        無法歸因的差額（如 `result.stop()` 中途中止）必須判紅。"""
        src = inspect.getsource(run_root_unittests.run_with_floor)
        self.assertIn("unexplained_gap", src, "執行差額必須影響最終 rc")
        self.assertIn("fixture_level_entries(result)", src, "判紅前必須先嘗試歸因")

        _, attributable = self._run(5, unittest.SkipTest("可歸因"))
        with contextlib.redirect_stdout(io.StringIO()):
            gap = run_root_unittests.report_execution_gap(5, attributable)
        self.assertTrue(
            gap > 0 and bool(run_root_unittests.fixture_level_entries(attributable)),
            "此情境為『有差額但可歸因』⇒ 依設計只點名不判紅",
        )


if __name__ == "__main__":
    unittest.main()
