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
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests  # noqa: E402
from lib import windows_skip_tags  # noqa: E402  # R72：skip 標籤家族的 SSOT（見該檔頭）


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



class UntaggedWindowsLikeSkipsTest(unittest.TestCase):
    """R67-F11：`[WINDOWS-NATIVE-ONLY]` **標籤完整性**前瞻鎖。

    WHY（為何上面那組鎖不夠）：`ReportWindowsNativeSkipsTest` 全組都只驗「已經帶
    標籤的 skip 會被點名」——對「該帶而沒帶」結構性盲目，而那正是低報的來源。
    R67 動工實測：macOS 上 15 支 skip 全為 Windows 專屬，標題只印 10（低報 33%），
    其中 4 支是 R65（`01fd8c3`）、1 支是 R66（`8654975`）落地時漏標；R59 已在
    `tools/tests/test_install_windows_nightly.py:344-350` 逐字記過同一形態，兩輪後
    原地復發。掃描員動工前另做過反證：把一支帶滿 Windows 關鍵詞、**未標籤**的
    skip 附加進既有鎖檔，全套 1140 支測試**無一支轉紅**（rc=0）——前瞻鎖確實不存在。

    本組鎖的是那個新判準本身，含四個方向：命中要抓、標籤要放行、不相關的 skip
    不得誤殺、以及「在 Windows 上必須整組閉嘴」（否則 POSIX-only skip 的理由幾乎
    都會提到 Windows，會在真 Windows 機器上製造整片假紅）。
    """

    def _result_with_skips(self, *skips: tuple[str, str]) -> unittest.TestResult:
        """用 `_ErrorHolder` 之外的最小假物件組出 `result.skipped`（不跑真測試）。"""
        class _T:
            def __init__(self, tid: str) -> None:
                self._tid = tid

            def id(self) -> str:
                return self._tid

        result = unittest.TestResult()
        result.skipped = [(_T(tid), reason) for tid, reason in skips]
        return result

    def test_untagged_windows_reason_is_flagged_with_the_matched_keyword(self) -> None:
        result = self._result_with_skips(
            ("m.C.test_x", "PATHEXT 解析語意與 Git for Windows bin\\bash.exe 僅在 Windows 重現"),
        )
        offenders = run_root_unittests.untagged_windows_like_skips(result, on_windows=False)
        self.assertEqual(len(offenders), 1, f"應抓到 1 筆漏標，實得：{offenders}")
        test_id, hit, reason = offenders[0]
        self.assertEqual(test_id, "m.C.test_x")
        self.assertIn(hit, run_root_unittests._WINDOWS_LIKE_SKIP_HINTS)
        self.assertIn("PATHEXT", reason, "必須連理由一起回報，否則讀者無從判斷該不該補標籤")

    def test_tagged_reason_is_not_flagged(self) -> None:
        """對照組：帶標籤者必須放行——否則補完標籤仍然紅，這道鎖就無法被滿足。"""
        result = self._result_with_skips(
            ("m.C.test_x", f"{run_root_unittests.WINDOWS_NATIVE_SKIP_TAG} 具名 Mutex 是 Windows 語意"),
        )
        self.assertEqual(
            run_root_unittests.untagged_windows_like_skips(result, on_windows=False), []
        )

    def test_unrelated_skip_is_not_flagged(self) -> None:
        """不得誤殺：與平台無關的一般性 skip 不能被要求補 Windows 標籤。"""
        result = self._result_with_skips(("m.C.test_x", "本機缺 docker daemon，一般性 skip"))
        self.assertEqual(
            run_root_unittests.untagged_windows_like_skips(result, on_windows=False), []
        )

    def test_on_windows_the_check_is_silent(self) -> None:
        """在原生 Windows 上必須整組閉嘴。

        測意圖：標籤語意是「這支只在原生 Windows 有價值，**這次環境不符沒跑**」，
        在 Windows 上這類測試根本不會 skip；Windows 上會 skip 的是 POSIX-only 測試，
        而它們的理由幾乎必然提到 Windows（例：「Windows 無 symlink 權限」）。若少了
        這個平台閘，整片 POSIX-only skip 會在 Windows 上被誤判成漏標＝假紅。
        """
        result = self._result_with_skips(
            ("m.C.test_posix_only", "Windows 無 symlink 權限（WinError 1314），此測試僅 POSIX 有意義"),
        )
        self.assertEqual(
            run_root_unittests.untagged_windows_like_skips(result, on_windows=True), [],
            "Windows 平台上本檢查必須回空集合（反方向可見度由 report_all_skips 承接）",
        )
        self.assertEqual(
            len(run_root_unittests.untagged_windows_like_skips(result, on_windows=False)), 1,
            "同一份輸入在非 Windows 上必須被抓到——否則上一條斷言只是恆真",
        )

    def test_named_exemption_suppresses_a_false_positive(self) -> None:
        """逃生門：確實不是 Windows 專屬者可具名豁免（不接受整批略過的通用開關）。"""
        result = self._result_with_skips(("m.C.test_x", "需要 Windows 主開發機才有的 docker"))
        with mock.patch.dict(
            run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT,
            {"m.C.test_x": "測試用：本機 docker 供給問題，非平台語意"},
            clear=False,
        ):
            self.assertEqual(
                run_root_unittests.untagged_windows_like_skips(result, on_windows=False), []
            )

    def test_detector_is_pure_no_stdout(self) -> None:
        """比照 `windows_native_skips`／`all_skips` 既有紀律：純函式不得有列印副作用。"""
        result = self._result_with_skips(("m.C.test_x", "僅在 Windows 重現"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            run_root_unittests.untagged_windows_like_skips(result, on_windows=False)
        self.assertEqual(buf.getvalue(), "")

    def test_reporter_prints_offender_and_the_fix_instruction(self) -> None:
        result = self._result_with_skips(("m.C.test_x", "PATHEXT 語意僅在 Windows 成立"))
        buf = io.StringIO()
        # R72：`untagged_windows_like_skips` 已隨 skip 標籤家族搬進
        # `tools/lib/windows_skip_tags.py`（見該檔頭），平台閘讀的是**該模組**的
        # `os.name`；patch 目標跟著搬，否則這道對照組會靜默失去鑑別力。
        with mock.patch.object(windows_skip_tags.os, "name", "posix"):
            with contextlib.redirect_stderr(buf):
                offenders = run_root_unittests.report_untagged_windows_like_skips(result)
        out = buf.getvalue()
        self.assertEqual(len(offenders), 1)
        self.assertIn("m.C.test_x", out, "必須逐支點名，否則讀者不知道要改哪一支")
        self.assertIn(run_root_unittests.WINDOWS_NATIVE_SKIP_TAG, out, "訊息須指出要補哪個標籤")
        self.assertIn("_WINDOWS_SKIP_TAG_EXEMPT", out, "訊息須指路逃生門，否則誤判時無路可走")

    def test_check_is_wired_into_run_with_floor_and_reds_the_run(self) -> None:
        """接線鎖 ＋ rc 鎖：單元測了但沒接線、或接線了但不改 rc，都是假綠。

        WHY 兩者都要驗：只 grep 原始碼（比照上面 `test_reporters_are_actually_wired_
        into_run_with_floor` 的既有手法）擋不住「有呼叫但回傳值被丟掉」；只驗 rc
        又無法指出是哪一段沒接。故兩條並列。
        """
        src = inspect.getsource(run_root_unittests.run_with_floor)
        self.assertIn(
            "report_untagged_windows_like_skips(result)", src,
            "run_with_floor 未呼叫漏標檢查——reporter 存在但沒接線，等於沒有",
        )
        self.assertIn(
            "not untagged", src,
            "漏標檢查的結果必須真的參與 rc 收斂，否則印了紅字卻照樣 rc=0（fail-open）",
        )

    def test_real_run_with_floor_reds_on_an_untagged_windows_skip(self) -> None:
        """端到端：合成一棵樹、內含一支未標籤的 Windows-only skip ⇒ `run_with_floor`
        必須 rc=1；補上標籤後同一棵樹 rc=0。**這就是常駐的缺陷注入對照組**。"""
        base = Path(tempfile.mkdtemp(prefix="rru_untagged_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        mod = "test_fixture_untagged_win_skip"
        self.addCleanup(lambda: sys.modules.pop(mod, None))
        template = textwrap.dedent(
            """\
            import unittest


            class Dummy(unittest.TestCase):
                def test_skipped(self):
                    self.skipTest("__REASON__")

                def test_ok(self):
                    self.assertTrue(True)
            """
        )
        untagged = "PATHEXT 解析語意僅在 Windows 重現"
        (base / f"{mod}.py").write_text(
            template.replace("__REASON__", untagged), encoding="utf-8"
        )
        # R72：`untagged_windows_like_skips` 已隨 skip 標籤家族搬進
        # `tools/lib/windows_skip_tags.py`（見該檔頭），平台閘讀的是**該模組**的
        # `os.name`；patch 目標跟著搬，否則這道對照組會靜默失去鑑別力。
        with mock.patch.object(windows_skip_tags.os, "name", "posix"):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc_untagged = run_root_unittests.run_with_floor(base, min_tests=2)
            sys.modules.pop(mod, None)
            (base / f"{mod}.py").write_text(
                template.replace(
                    "__REASON__", f"{run_root_unittests.WINDOWS_NATIVE_SKIP_TAG} {untagged}"
                ),
                encoding="utf-8",
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                rc_tagged = run_root_unittests.run_with_floor(base, min_tests=2)
        self.assertEqual(rc_untagged, 1, "未標籤的 Windows-only skip 必須讓整輪 rc=1")
        self.assertEqual(rc_tagged, 0, "補上標籤後同一棵樹必須轉綠——否則本鎖無法被滿足")


class StaticWindowsSkipTagScanTest(unittest.TestCase):
    """R72：`[WINDOWS-NATIVE-ONLY]` 標籤完整性的**靜態、跨平台**鎖。

    WHY（為何上面那組 runtime 鎖不夠——而且不是它寫錯）：
    `untagged_windows_like_skips` 在 Windows 上整組早退（`if on_windows: return []`），
    上面 `test_on_windows_the_check_is_silent` 正是在**要求**它這麼做，理由也成立
    （Windows 上會 skip 的是 POSIX-only 測試，其 reason 幾乎必然提到 Windows，照掃
    必然假紅）。但代價是結構性的：三道 Windows 側閘門（本機 pytest／pre-push／
    windows-compat-ci）從此是**同一個瞎點的三份複本**——R71 在 Windows 落地的漏標，
    三處都看不見，只能等別的平台跑到才發現，而那正好是 R43 DEF-101-348 那條
    「Windows 專屬測試連續 5+ 輪全 APPROVE 卻從未在 Windows 跑過」的同款延遲。

    本組鎖的是那個補位判準：不看「現在跑在哪個平台」，改看 skip 條件的**方向**
    （`skipUnless(<Windows 述詞>)` vs `skipIf(<Windows 述詞>)`）。方向資訊寫在原始碼
    裡，三個平台讀到的是同一份，所以這道掃描在哪裡跑都會說話。

    落地前的鑑別力反證（Windows 11 實測）：不含方向判準的版本對同一棵樹報 **7 筆**
    假紅，全數是 `skipIf(os.name == "nt")` 的 POSIX-only 測試；加上方向判準後歸零。
    也就是說「方向」不是可有可無的精緻化，它是這道鎖能不能存在的前提。
    """

    _WIN_PRED = 'os.name == "nt"'

    @staticmethod
    def _real_tree_sources() -> dict[str, str]:
        """真實掃描面。pattern 刻意取 `run_root_unittests._PATTERN`（＝閘門的 discovery
        pattern）而非在測試裡另寫一份字面值——第二份字面值就是下一次漂移。"""
        return windows_skip_tags.read_test_sources(
            run_root_unittests._TESTS_DIR, run_root_unittests._PATTERN)

    def _src(self, decorator: str, condition: str, reason: str) -> dict[str, str]:
        """合成一份**最小可解析**的測試模組原始碼（不落磁碟、不執行）。"""
        return {
            "test_synthetic.py": textwrap.dedent(
                f"""\
                import os
                import unittest


                class Dummy(unittest.TestCase):
                    @unittest.{decorator}({condition}, {reason!r})
                    def test_x(self):
                        pass
                """
            )
        }

    def test_skipunless_windows_predicate_without_tag_is_flagged(self) -> None:
        offenders = windows_skip_tags.untagged_windows_skip_decorators(
            self._src("skipUnless", self._WIN_PRED, "PATHEXT 解析語意僅在 Windows 重現")
        )
        self.assertEqual(len(offenders), 1, f"應抓到 1 筆漏標，實得：{offenders}")
        label, hit, reason = offenders[0]
        self.assertIn("test_synthetic.py", label)
        self.assertIn("test_x", label, "必須點名到被裝飾者，否則讀者不知道要改哪一支")
        self.assertIn(hit, windows_skip_tags._WINDOWS_LIKE_SKIP_HINTS)
        self.assertIn("PATHEXT", reason, "必須連理由一起回報，否則無從判斷該不該補標籤")

    def test_skipif_windows_predicate_is_not_flagged(self) -> None:
        """🔴 本鎖的核心鑑別力：方向相反者**不得**被抓。

        `skipIf(<Windows 述詞>)` ＝「Windows 上才 skip」＝ POSIX-only 測試，它的
        reason 幾乎必然提到 Windows（例：「Windows 無 symlink 權限」），而
        `[WINDOWS-NATIVE-ONLY]`（「只在原生 Windows 才有價值、這次沒跑」）對它是
        錯的語意。少了這一條，本掃描對真實樹會噴 7 筆假紅（落地前實測值），沒有
        任何人會容忍它留在閘門裡——假紅比沒有鎖更糟。
        """
        self.assertEqual(
            windows_skip_tags.untagged_windows_skip_decorators(
                self._src("skipIf", self._WIN_PRED,
                          "Windows 無 symlink 權限，此測試僅 POSIX 有意義")
            ),
            [],
        )

    def test_tagged_reason_is_not_flagged(self) -> None:
        """對照組：補上標籤後必須轉綠——否則這道鎖無法被滿足。"""
        self.assertEqual(
            windows_skip_tags.untagged_windows_skip_decorators(
                self._src(
                    "skipUnless", self._WIN_PRED,
                    f"{windows_skip_tags.WINDOWS_NATIVE_SKIP_TAG} 具名 Mutex 是 Windows 語意",
                )
            ),
            [],
        )

    def test_unrelated_predicate_is_not_flagged(self) -> None:
        """不得誤殺：條件不是 Windows 述詞時，reason 提到 Windows 也不該被要求補標籤
        （那是「缺工具」類 skip，不是平台語意）。"""
        self.assertEqual(
            windows_skip_tags.untagged_windows_skip_decorators(
                self._src("skipUnless", "shutil.which('docker')",
                          "需要 docker daemon（作者的 Windows 開發機上才有）")
            ),
            [],
        )

    def test_non_literal_reason_is_skipped_not_guessed(self) -> None:
        """reason 取不到字面值時略過而**不猜**——判準邊界要可預期，不能靠推測。"""
        self.assertEqual(
            windows_skip_tags.skip_decorator_sites(
                {"test_synthetic.py": textwrap.dedent(
                    """\
                    import os
                    import unittest

                    REASON = "僅在 Windows 重現"


                    class Dummy(unittest.TestCase):
                        @unittest.skipUnless(os.name == "nt", REASON)
                        def test_x(self):
                            pass
                    """
                )},
            ),
            [],
        )

    def test_hints_and_tag_are_shared_with_the_runtime_lock_not_copied(self) -> None:
        """判準面必須與 runtime 那道鎖**共用同一份常數**，不是各抄一份。

        兩層驗證：
          ① 物件同一性——`run_root_unittests` 的名字必須就是 `windows_skip_tags` 的
             那個物件（R72 抽模組後靠再匯出維持既有呼叫端；若哪天變成各持一份副本，
             既有的 `mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, …)`
             會靜默失效——patch 到的是另一個 dict）。
          ② 行為——換掉關鍵詞面後靜態掃描的判定必須跟著變；若它抄了一份字面關鍵詞，
             這裡會紋風不動。兩份判準各自漂移，正是 R67-F11 當初要修的形狀的再版。
        """
        for name in ("WINDOWS_NATIVE_SKIP_TAG", "_WINDOWS_LIKE_SKIP_HINTS",
                     "_WINDOWS_SKIP_TAG_EXEMPT"):
            self.assertIs(
                getattr(run_root_unittests, name), getattr(windows_skip_tags, name),
                f"{name} 在兩個模組是不同物件 ⇒ 再匯出退化成複製，既有 mock.patch 會靜默失效",
            )
        src = self._src("skipUnless", self._WIN_PRED, "此測試依賴 zzsentinel 語意")
        self.assertEqual(windows_skip_tags.untagged_windows_skip_decorators(src), [])
        with mock.patch.object(
            windows_skip_tags, "_WINDOWS_LIKE_SKIP_HINTS", ("zzsentinel",)
        ):
            self.assertEqual(
                len(windows_skip_tags.untagged_windows_skip_decorators(src)), 1,
                "換掉共用關鍵詞面後判定未改變 ⇒ 靜態掃描抄了一份自己的字面關鍵詞",
            )

    def test_unregistered_windows_like_predicate_is_flagged(self) -> None:
        """fail-open 封口：述詞沒登記 ⇒ 方向判不出來 ⇒ 該站點靜默不報。

        這是本掃描唯一的靜默失效路徑，必須自己有人看守。反向對照（已登記者不得被
        點名）同時驗，否則上一條斷言可能只是「什麼都報」。
        """
        unknown = windows_skip_tags.unregistered_windows_like_predicates(
            self._src("skipUnless", "_brand_new_windows_probe()", "需要 Windows")
        )
        self.assertEqual(len(unknown), 1, f"未登記述詞未被點名：{unknown}")
        self.assertIn("_brand_new_windows_probe()", unknown[0][1])
        self.assertEqual(
            windows_skip_tags.unregistered_windows_like_predicates(
                self._src("skipUnless", self._WIN_PRED, "需要 Windows")
            ),
            [],
            "已登記的述詞不得被點名，否則本封口只是噪音",
        )

    def test_detector_is_pure_no_stdout(self) -> None:
        """比照 `windows_native_skips`／`all_skips` 既有紀律：純函式不得有列印副作用。"""
        src = self._src("skipUnless", self._WIN_PRED, "僅在 Windows 重現")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            windows_skip_tags.untagged_windows_skip_decorators(src)
            windows_skip_tags.unregistered_windows_like_predicates(src)
            windows_skip_tags.skip_decorator_sites(src)
        self.assertEqual(buf.getvalue(), "")

    def test_scan_surface_is_not_silently_empty(self) -> None:
        """掃描面自檢：掃到 0 份（或明顯縮水）必須紅而非靜默通過。

        同 `test_schedule_capability_parity.TestUnittestDiscoverConformance` 的既有
        慣例——一道鎖若能因為「什麼都沒掃到」而全綠，它就是 fail-open 本身。
        """
        sources = self._real_tree_sources()
        self.assertGreaterEqual(
            len(sources), 40,
            f"tools/tests/ 只讀到 {len(sources)} 份 test_*.py——掃描面疑似靜默縮小",
        )
        self.assertGreater(
            len(windows_skip_tags.skip_decorator_sites(sources)), 20,
            "整棵樹抽不到足量 skip decorator 站點——AST 抽取器疑似與現行寫法脫節",
        )

    def test_real_tree_is_clean_on_every_platform(self) -> None:
        """活體鎖：本 repo 現況不得有漏標，也不得有未登記述詞。

        **無平台條件**正是本測試的全部價值：Windows 上跑得到的判定，就是 macOS／
        Linux 上跑得到的同一個判定。
        """
        sources = self._real_tree_sources()
        self.assertEqual(
            windows_skip_tags.unregistered_windows_like_predicates(sources), [],
            "有 skip 條件看起來像 Windows 述詞卻未登記於 _WINDOWS_SKIP_PREDICATE_MARKERS"
            "——這些站點的方向判不出來，會靜默漏掉漏標",
        )
        self.assertEqual(
            windows_skip_tags.untagged_windows_skip_decorators(sources), [],
            f"有 skipUnless(<Windows 述詞>) 的 skip 未帶 "
            f"{windows_skip_tags.WINDOWS_NATIVE_SKIP_TAG}",
        )

    def test_check_is_wired_into_main_and_reds_the_run(self) -> None:
        """接線鎖 ＋ rc 鎖：單元測了但沒接線、或接線了但不改 rc，都是假綠
        （Scan-H 判準⑤：「可重跑但沒有任何閘門看它的 rc」＝不可重跑）。

        兩條並列的理由同 `test_check_is_wired_into_run_with_floor_and_reds_the_run`：
        只 grep 原始碼擋不住「有呼叫但回傳值被丟掉」，只驗 rc 又指不出哪一段沒接。
        """
        src = inspect.getsource(run_root_unittests.main)
        self.assertIn(
            "report_untagged_windows_skip_decorators(_TESTS_DIR, _PATTERN)", src,
            "main() 未呼叫靜態標籤掃描——掃描器存在但沒接線，等於沒有",
        )
        self.assertRegex(
            src,
            r"if report_untagged_windows_skip_decorators\(_TESTS_DIR, _PATTERN\):"
            r"\s*\n\s*return 1",
            "掃描結果必須真的參與 rc 收斂，否則印了紅字卻照樣 rc=0（fail-open）",
        )

    def test_reporter_reds_on_a_synthetic_offending_tree(self) -> None:
        """端到端：造一棵含漏標的合成樹 ⇒ reporter 回非空並印出指路；補上標籤後轉綠。
        **這就是常駐的缺陷注入對照組**（同上方 runtime 版的既有慣例）。"""
        base = Path(tempfile.mkdtemp(prefix="rru_static_tag_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        body = self._src("skipUnless", self._WIN_PRED, "__REASON__")["test_synthetic.py"]
        target = base / "test_synthetic.py"
        untagged = "PATHEXT 解析語意僅在 Windows 重現"
        target.write_text(body.replace("__REASON__", untagged), encoding="utf-8")
        pattern = run_root_unittests._PATTERN
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            problems = windows_skip_tags.report_untagged_windows_skip_decorators(base, pattern)
        self.assertEqual(len(problems), 1, f"合成漏標未被抓到：{problems}")
        out = buf.getvalue()
        self.assertIn("test_synthetic.py", out, "必須逐支點名，否則讀者不知道要改哪一支")
        self.assertIn(windows_skip_tags.WINDOWS_NATIVE_SKIP_TAG, out, "訊息須指出要補哪個標籤")
        target.write_text(
            body.replace("__REASON__",
                         f"{windows_skip_tags.WINDOWS_NATIVE_SKIP_TAG} {untagged}"),
            encoding="utf-8",
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                windows_skip_tags.report_untagged_windows_skip_decorators(base, pattern), [],
                "補上標籤後同一棵樹必須轉綠——否則本鎖無法被滿足",
            )

    def test_empty_scan_surface_is_fail_closed(self) -> None:
        """掃描面為空時 reporter 必須回報問題，而不是「沒發現違規」的綠燈。"""
        base = Path(tempfile.mkdtemp(prefix="rru_static_empty_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        with contextlib.redirect_stderr(io.StringIO()):
            problems = windows_skip_tags.report_untagged_windows_skip_decorators(
                base, run_root_unittests._PATTERN)
        self.assertEqual(len(problems), 1, "空掃描面必須 fail-closed")
        self.assertIn("掃描面為空", problems[0])


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


# ── R68：零相依環境（＝CI 實況）的鑑別力鎖 ────────────────────────────────────
#
# 缺陷（三支 CI 自 2026-07-14 起連續全紅，無人察覺）：`tools/tests/` 有三支測試
# import `autoclaude.*`，連帶拉進 yaml→pydantic→httpx；而 CI 三個 job 都不裝任何
# 第三方套件。缺相依時 `unittest` discovery **不報錯**，只把該模組整份覆蓋塌成一支
# `_FailedTest` 佔位測試——122 支 Windows 迴歸鎖靜默不跑，而閘門紅在一句「測試疑似
# 大規模靜默消失（目錄改名/pattern 不符/路徑錯）」上，三條指路全錯。
#
# 本組鎖的**模擬手法**：往 `sys.meta_path` 插一個對指定 top-level 模組拋
# `ModuleNotFoundError` 的 finder，即可在**任何**環境裡重現零相依環境，不需要真的
# 建一個乾淨 venv。落地時實測：此法對真實 `tools/tests/` 樹產生的收集數與佔位模組
# 集合，與 stdlib-only venv 實跑、以及三個 CI 平台回報的數字**三方完全一致**。
# 因為要隔離 `sys.meta_path` 與 `sys.modules` 的污染，一律在子行程裡跑。
_ZERO_DEP_PROBE = '''\
import json, sys
_blocked = set(json.loads(sys.argv[1]))


class _Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] in _blocked:
            raise ModuleNotFoundError("No module named %r" % fullname, name=fullname)
        return None


sys.meta_path.insert(0, _Blocker())
sys.path.insert(0, sys.argv[3])
import run_root_unittests as R

if sys.argv[2] == "main":
    sys.exit(R.main())
# "floor"：刻意繞過 main() 的 fail-fast，直接叩下限守門本身——證明**即使**前置
# 檢查被拿掉，下限層在零相依環境下仍然判紅（鑑別力不靠 fail-fast 撐著）。
sys.exit(R.run_with_floor(R._TESTS_DIR, R.MIN_TESTS))
'''


def _run_zero_dep_probe(mode: str, blocked: list[str]) -> subprocess.CompletedProcess[str]:
    tools_dir = str(Path(run_root_unittests.__file__).resolve().parent)
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "zero_dep_probe.py"
        probe.write_text(_ZERO_DEP_PROBE, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(probe), json.dumps(blocked), mode, tools_dir],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=tools_dir, timeout=300,
        )


class ThirdPartyPrereqDeclarationTest(unittest.TestCase):
    """`_THIRD_PARTY_PREREQS` 是「`MIN_TESTS` 得以成立的前提」的宣告（R68）。

    WHY（測意圖）：`MIN_TESTS` 是**單一值**——相依齊備環境下的實測值。本輪曾被提議
    改成「環境感知的雙下限」（完整相依用高值、零相依用低值），該設計會把一個**壞掉
    的環境升格成合法的第二種環境**，讓 CI 在 122 支迴歸鎖一支都沒跑的狀態下印綠燈。
    本組鎖住的正是相反的語意：零相依環境**必須**判紅，而且要說清楚紅在哪裡。
    """

    def test_declared_prereqs_are_present_in_this_environment(self) -> None:
        """宣告面的**真實性**：清單裡的每一個都必須真的裝得到。

        本測試能執行本身就蘊含相依齊備（否則 `main()` 早已 fail-fast），故它擋的是
        「宣告了一個根本沒人裝的模組」——那會讓 runner 在所有環境永久 fail-fast。
        """
        self.assertEqual(
            run_root_unittests.missing_third_party_prereqs(), [],
            "宣告的第三方相依在本環境找不到——清單可能寫錯 import 名",
        )

    def test_missing_detection_reports_pip_name_for_install(self) -> None:
        """偵測到缺漏時必須連 **pip 名**一起回報：import 名與 pip 名不一定同字
        （`yaml` 的 pip 名是 `pyyaml`），只印 import 名等於讓人自己猜安裝指令。"""
        fake = (("definitely_not_installed_xyz", "some-pip-name"),)
        missing = run_root_unittests.missing_third_party_prereqs(fake)
        self.assertEqual(missing, [("definitely_not_installed_xyz", "some-pip-name")])

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            run_root_unittests.report_missing_third_party_prereqs(missing)
        msg = buf.getvalue()
        self.assertIn("some-pip-name", msg, "訊息必須給得出可直接複製的安裝指令")
        self.assertIn("不是「測試消失」", msg, "必須當場否定掉那個錯誤診斷")


class FloorFailureAttributionTest(unittest.TestCase):
    """下限失敗訊息必須**分辨**「環境不完整」與「測試真的消失」（R68）。

    WHY（測意圖非僅行為）：舊訊息只有一種說法，把讀者指往「目錄改名／pattern 不符／
    路徑錯」三條路；三個 CI 平台實際撞上的卻是第四種原因。訊息本身就是這道閘門的
    產品——它錯了，閘門即使正確判紅也沒有價值（實證：連續多輪沒人循著它找到根因）。
    """

    def _message(self, placeholders, missing) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            run_root_unittests.report_floor_failure(
                Path("/fake/tests"), 1240, 1362, placeholders, missing,
            )
        return buf.getvalue()

    def test_placeholders_present_blames_environment_and_names_modules(self) -> None:
        msg = self._message([("mod_a", "_FailedTest")], [("yaml", "pyyaml")])
        self.assertIn("mod_a", msg, "必須點名是哪個模組沒載入，否則無從查起")
        self.assertIn("環境問題", msg)
        self.assertIn("pyyaml", msg, "既然知道缺什麼，就必須直接給安裝指令")
        self.assertNotIn(
            "真的大規模消失", msg,
            "有佔位測試時仍宣稱『測試消失』＝把讀者指往錯的方向，正是本輪缺陷本體",
        )

    def test_no_placeholders_still_blames_real_disappearance(self) -> None:
        """反方向：**沒有**佔位測試時，原本那個診斷仍然要講——鑑別力不可只往一邊倒。
        修完之後「測試真的大量消失」必須照樣被抓到並被正確歸因。"""
        msg = self._message([], [])
        self.assertIn("真的大規模消失", msg)
        self.assertIn("MIN_TESTS", msg, "刻意刪減時仍須指路到下修下限")

    def test_placeholders_but_all_prereqs_present_points_at_new_dependency(self) -> None:
        """第三種情形（未來的復發形態）：有模組載入失敗、但宣告清單全都在 ⇒ 多半是
        **新增**了一個沒登記的第三方相依。訊息必須指向「把它加進清單並同步 CI」，
        否則下一個人只會看到一份無從解釋的佔位測試清單。"""
        msg = self._message([("mod_b", "_FailedTest")], [])
        self.assertIn("mod_b", msg)
        self.assertIn("_THIRD_PARTY_PREREQS", msg)


class ZeroDepEnvironmentDiscriminationTest(unittest.TestCase):
    """零相依環境（＝三支 CI 的等價環境）下的鑑別力鎖（R68）。

    🔴 鑑別力邊界（誠實劃界）：本組證明的是「宣告清單裡那幾個相依被拿掉時，閘門會
    判紅且會正確歸因」。它**不**證明清單是完備的——若未來有人加進第四個相依而沒
    登記，本組抓不到（那半邊由 `CiPrereqInstallLockTest` 的 SSOT 綁定與 runner 的
    「相依都在卻仍有佔位測試」分支承接）。
    """

    def test_blocked_prereqs_reproduce_collection_collapse(self) -> None:
        """模擬手法的**保真度**自檢：擋掉宣告的相依後，真實樹的收集數必須真的掉到
        下限以下且產生佔位測試。若哪天這條不成立，代表本組其餘測試在測空氣。"""
        blocked = [imp for imp, _ in run_root_unittests._THIRD_PARTY_PREREQS]
        proc = _run_zero_dep_probe("floor", blocked)
        self.assertEqual(
            proc.returncode, 1,
            f"零相依環境下 run_with_floor 必須判紅（stdout={proc.stdout[-500:]!r}）",
        )

    def test_zero_dep_message_says_environment_not_disappearance(self) -> None:
        """本輪缺陷的**直接**回歸鎖：在 CI 的等價環境下，閘門印的必須是「環境不完整」
        而不是「測試疑似大規模靜默消失」。"""
        blocked = [imp for imp, _ in run_root_unittests._THIRD_PARTY_PREREQS]
        proc = _run_zero_dep_probe("floor", blocked)
        self.assertIn("環境問題", proc.stderr)
        self.assertNotIn("真的大規模消失", proc.stderr)
        for import_name, _pip in run_root_unittests._THIRD_PARTY_PREREQS:
            self.assertIn(import_name, proc.stderr, "必須點名缺哪一個相依")

    def test_main_fails_fast_with_actionable_message(self) -> None:
        """`main()` 必須在跑滿整套之前就 fail-fast——把一次 110 秒的誤診縮成一則
        0.5 秒的正確指路。同時證明零相依環境**不會**被放行（無 fail-open）。"""
        blocked = [imp for imp, _ in run_root_unittests._THIRD_PARTY_PREREQS]
        proc = _run_zero_dep_probe("main", blocked)
        self.assertEqual(proc.returncode, 1, "零相依環境必須判紅")
        self.assertIn("pip install", proc.stderr, "必須給得出可直接複製的修法")
        self.assertNotIn(
            "unittest 數量下限釘選通過", proc.stdout,
            "fail-fast 必須發生在下限守門之前，否則等於又跑了一輪才誤診",
        )


# `tools/tests/` 的**外部可執行檔**前置宣告（SSOT）——`(命令名, pip 名)`。
#
# WHY（R69 終審 SD 實測；與 `run_root_unittests._THIRD_PARTY_PREREQS` 是同一個病的
# 第二種形狀）：那份清單守的是「import 得到嗎」，對「PATH 上有沒有這支執行檔」結構性
# 盲目。R69 把 `ruff check tools/` 接進 `tools/git-hooks/pre-push` 快層第 ④ 段（缺 ruff
# ＝fail-loud，刻意不軟跳過），而 `test_pre_push_dispatcher.py` 有 5 支測試在 tmp repo
# 內**真跑**該 dispatcher 並斷言 rc==0 ⇒ 本目錄自此隱性要求 PATH 上有 ruff。當時三支跑
# runner 的 workflow 只有 root-infra-ci.yml 裝 ruff ⇒ **同一批 tools/tests 在三個平台有
# 兩種結果**，原本綠著的 macos-compat-ci 會被打紅（SD 單變因 A/B：PATH 上放假 ruff →
# Ran 17 OK；唯一差別拿掉 ruff → FAILED〔failures=5〕）。
#
# 🔴 為何解法是「三支 workflow 都補裝」而不是「缺 ruff 就 skip」：快層那道 fail-loud 是
# 本輪刻意訂的政策，軟跳過會讓它退回「宣告有、執行者無」的原病（見 tools/ruff.toml
# 檔頭）。落差在**環境**不在 dispatcher。
#
# 🔴 為何 SSOT 放在測試檔而非 `run_root_unittests.py`（誠實劃界）：該檔受
# `AutoClaude/tools/check_loc_budget.py` 的 SPECIAL_FILES **shrink-only 行數棘輪**管制
# （門檻＝納管當下行數 754，只准往下改），本包實測往該檔加 69 行當場撞紅（`[special<=754]
# 823 > 754`）。代價明說：因此**沒有** runner 開場 fail-fast 那一層，缺工具時仍會先看到
# dispatcher 那 5 支紅字；補償是下方 `ExternalToolPrereqDeclarationTest` 會在同一次執行
# 裡多紅一支並**點名真正的原因**。要買回 fail-fast 就得先把該檔壓到 754 行以下——那是
# 另一個包的工作，見交件回報的帳本請求。
_EXTERNAL_TOOL_PREREQS: tuple[tuple[str, str], ...] = (
    ("ruff", "ruff"),
)


class CiPrereqInstallLockTest(unittest.TestCase):
    """CI 安裝步驟鎖：跑本 runner 的每個 CI job 都必須先裝齊宣告的相依（R68）。

    WHY（本組最重要的一道；測意圖非僅行為）：前面幾道鎖只讓失敗**可讀**，攔不住
    「下次再多一個相依、CI 又沒裝」的復發——本輪的缺陷正是這個形狀，而且它躲過了
    連續多輪的四方複審。本鎖把「`_THIRD_PARTY_PREREQS` 這份宣告」與「CI 實際安裝
    的東西」機械綁在一起：往常數加一個相依而忘了改 workflow，這裡立刻紅。

    🔴 判準邊界（誠實劃界）：以純文字掃描認「同一個 job 內、該 step 之前出現的
    `pip install` 行」，刻意不引 YAML parser（本檔須能在最小環境下自我檢查）。
    因此它**不涵蓋**：把安裝寫進 composite action／reusable workflow／外部腳本、
    或以 `requirements.txt` 間接安裝——那些形態它一律看不到，仍是人審責任。
    """

    _WORKFLOWS = Path(run_root_unittests.__file__).resolve().parents[1] / ".github" / "workflows"
    # job key＝2 空格縮排的映射鍵。`on:` 底下的 `push:` 等也符合此形，但它們一律
    # 出現在 `jobs:` 之前，故「往回找最近一個」對 job 內的 step 永遠命中真正的 job。
    _JOB_KEY_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
    _RUNNER_RE = re.compile(r"run:.*run_root_unittests\.py")
    _PIP_INSTALL_RE = re.compile(r"pip install\b(.*)$")

    def _runner_call_sites(self) -> list[tuple[Path, int, list[str]]]:
        """回傳 `(workflow 檔, 呼叫行號, 該 job 內此行之前的所有行)`。"""
        sites: list[tuple[Path, int, list[str]]] = []
        for path in sorted(self._WORKFLOWS.glob("*.yml")):
            lines = path.read_text(encoding="utf-8").splitlines()
            job_start = 0
            for idx, line in enumerate(lines):
                if self._JOB_KEY_RE.match(line):
                    job_start = idx
                elif self._RUNNER_RE.search(line):
                    sites.append((path, idx + 1, lines[job_start:idx]))
        return sites

    def test_every_ci_job_running_the_runner_installs_all_prereqs(self) -> None:
        sites = self._runner_call_sites()
        # 下限釘選（比照本 repo 既有慣例）：抽不到任何呼叫點時本鎖會**空轉全綠**，
        # 那正是它要防的失效模式的極端形——workflow 改名或 step 改寫都會走到這裡。
        self.assertGreaterEqual(
            len(sites), 3,
            f"抽不到足夠的 run_root_unittests.py CI 呼叫點（找到 {len(sites)} 個）——"
            f"抽取 pattern 或 workflow 結構疑似漂移",
        )
        required = {pip for _imp, pip in run_root_unittests._THIRD_PARTY_PREREQS}
        for path, lineno, before in sites:
            installed: set[str] = set()
            for line in before:
                m = self._PIP_INSTALL_RE.search(line)
                if m:
                    installed.update(m.group(1).split())
            self.assertEqual(
                required - installed, set(),
                f"{path.name}:{lineno} 在同 job 內跑 run_root_unittests.py，但該 step 之前"
                f"沒有安裝 {sorted(required - installed)}——零相依環境下這些相依所屬的測試"
                f"模組會 import 失敗、整份覆蓋塌成佔位測試而**靜默不跑**（R68：三支 CI 因此"
                f"連續多輪全紅）。請在該 step 前補 pip install，清單 SSOT＝"
                f"run_root_unittests._THIRD_PARTY_PREREQS",
            )

    @staticmethod
    def _installed_package_names(before: list[str]) -> set[str]:
        """把 job 內出現過的 `pip install` 目標正規化成「套件名」集合（R69）。

        為何需要正規化（而上面那道第三方相依鎖直接比對字面 token 就夠）：釘版與引號
        是**外部工具**這一側的既有寫法——`root-infra-ci.yml` 寫的是
        `pip install ... 'ruff==0.15.21'`（版本釘選是本 repo 對 lint 工具的明文紀律，
        見 AutoClaude/pyproject.toml）。若照字面比對，一個正確裝了 ruff 的 job 會被
        判成沒裝，本鎖就只能靠「大家別釘版」活著——那不是鎖，是巧合。
        """
        names: set[str] = set()
        for line in before:
            m = CiPrereqInstallLockTest._PIP_INSTALL_RE.search(line)
            if not m:
                continue
            for token in m.group(1).split():
                token = token.strip("'\"")
                if token.startswith("-"):  # --quiet / --disable-pip-version-check 等旗標
                    continue
                names.add(re.split(r"[=<>!~\[]", token, maxsplit=1)[0].lower())
        return names

    def test_every_ci_job_running_the_runner_installs_all_external_tools(self) -> None:
        """外部**執行檔**相依（`_EXTERNAL_TOOL_PREREQS`）也必須在每一支 workflow 裝齊。

        WHY（R69 終審 SD 實測；測意圖非僅行為）：上面那道鎖只看得見 import 相依，對
        「PATH 上要有某支執行檔」結構性盲目。R69 把 `ruff check tools/` 接進 pre-push
        快層（缺 ruff＝fail-loud），而 `test_pre_push_dispatcher.py` 有 5 支測試在 tmp
        repo 內真跑該 dispatcher 並斷言 rc==0 ⇒ tools/tests 自此隱性需要 ruff。當時
        三支跑本 runner 的 workflow 只有 root-infra-ci 裝了 ruff ⇒ **同一批測試在三個
        平台有兩種結果**，而且原本綠著的 macos-compat-ci 會被打紅（SD 單變因 A/B：
        PATH 上放假 ruff → Ran 17 OK；唯一差別拿掉 ruff → FAILED〔failures=5〕）。

        本鎖擋的不是那一次，是**下一次**：再往清單加一個外部工具而忘了同步某一支
        workflow，這裡立刻紅並點名是哪一支。判準邊界同上面那道（純文字掃描，看不到
        composite action／requirements.txt 間接安裝）。
        """
        sites = self._runner_call_sites()
        self.assertGreaterEqual(
            len(sites), 3,
            f"抽不到足夠的 run_root_unittests.py CI 呼叫點（找到 {len(sites)} 個）——"
            f"抽取 pattern 或 workflow 結構疑似漂移",
        )
        required = {pip.lower() for _cmd, pip in _EXTERNAL_TOOL_PREREQS}
        self.assertNotEqual(required, set(), "_EXTERNAL_TOOL_PREREQS 為空 ⇒ 本鎖恆真空轉")
        for path, lineno, before in sites:
            installed = self._installed_package_names(before)
            self.assertEqual(
                required - installed, set(),
                f"{path.name}:{lineno} 在同 job 內跑 run_root_unittests.py，但該 step 之前"
                f"沒有安裝外部工具 {sorted(required - installed)}——這批工具是 tools/tests "
                f"的隱性前置（pre-push dispatcher 真跑鎖需要 PATH 上有 ruff），少裝的平台"
                f"會得到一批**歸因錯誤**的紅字（看起來像分流壞了，其實是環境缺工具）。"
                f"請在該 step 前補安裝，清單 SSOT＝tools/tests/test_run_root_unittests.py "
                f"的 _EXTERNAL_TOOL_PREREQS",
            )


class ExternalToolPrereqDeclarationTest(unittest.TestCase):
    """外部工具宣告的**真實性**與缺工具時的**歸因**（R69）。

    WHY（測意圖非僅行為）：這一整類缺陷的殺傷力不在紅燈本身，在**紅字把人指向哪裡**
    ——R68 對 import 相依修的正是這點（把「環境不完整」誤報成「測試消失」）。缺 ruff
    的環境會讓 `test_pre_push_dispatcher.py` 5 支測試以「rc 1 != 0」失敗，讀者被指往
    「分流邏輯壞了」這條全錯的路（R69 SD 實測即如此顯形）。本類的價值＝在同一次執行
    裡多紅一支、並在訊息裡把真正的原因與修法講清楚。
    """

    def test_declared_tools_are_present_and_name_the_real_cause_when_not(self) -> None:
        missing = [(cmd, pip) for cmd, pip in _EXTERNAL_TOOL_PREREQS if shutil.which(cmd) is None]
        self.assertEqual(
            missing, [],
            "🔴 PATH 上缺少 tools/tests 需要的外部工具："
            f"{'、'.join(cmd for cmd, _ in missing)}。\n"
            "這**不是** dispatcher 分流壞了：test_pre_push_dispatcher.py 會在 tmp repo 內"
            "真跑 pre-push dispatcher，而其 root-infra 快層對缺 ruff 是 fail-loud（刻意不"
            "軟跳過），於是那 5 支測試會以「rc 1 != 0」失敗、把你指往分流邏輯這條錯路。\n"
            "修法："
            + "python -m pip install " + " ".join(f"'{pip}'" for _, pip in missing) + "\n"
            "若在 CI 撞到：跑 run_root_unittests.py 的 job 少了安裝 step——該綁定由 "
            "CiPrereqInstallLockTest::test_every_ci_job_running_the_runner_installs_"
            "all_external_tools 機械看守，請一併檢查它為何沒紅。",
        )

    def test_the_declaration_is_not_vacuous(self) -> None:
        """反空轉：清單為空時上面那道與 CI 安裝鎖都會恆真全綠（本檔多處在治的形態）。"""
        self.assertNotEqual(
            _EXTERNAL_TOOL_PREREQS, (),
            "_EXTERNAL_TOOL_PREREQS 為空 ⇒ 兩道鎖同時失去鑑別力；要移除最後一項前，"
            "請先確認 tools/tests 真的不再需要任何外部執行檔（含 pre-push 快層那條路）",
        )


if __name__ == "__main__":
    unittest.main()
