"""run_root_unittests.py — 數量下限釘選的回歸鎖（R10 QA-2，DEF-101-127）。

WHY（測意圖非僅行為）：`python -m unittest discover` 對 0 個測試回 rc=0，
「跑了 0 個測試也算 PASS」是結構性 fail-open——本測試鎖住包裝器的兩條語意：
(1) 低於下限＝紅燈且不執行；(2) 達下限＝執行並回傳真實結果。
並以真 repo 斷言下限釘選對當前樹成立（防 MIN_TESTS 與現況脫節）。
"""
from __future__ import annotations

import ast
import contextlib
import functools
import importlib
import inspect
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests  # noqa: E402
from lib import windows_skip_tags  # noqa: E402  # R72：skip 標籤家族的 SSOT（見該檔頭）

#: DEF-200-170：刻意取 **runner 手上的那一個** module 物件。`tools/lib` 同時也在 `sys.path`
#: 上（runner 自己插的），改寫成 `from lib import min_tests_margin` 會拿到**第二個副本**，
#: 於是「測試驗的常數」與「runner 讀的常數」是兩個物件、日後任何 patch 都會靜默失效——
#: 同 `test_hints_and_tag_are_shared_with_the_runtime_lock_not_copied` 已付過學費的形態。
min_tests_margin = run_root_unittests.min_tests_margin


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

    def test_current_pin_still_has_zero_dep_discrimination_headroom(self) -> None:
        """🔴 DEF-200-170：真正會先響的那道紅線——綁的是**零相依餘裕**，不是比例。

        WHY 上面那支不夠（不是重複，是它結構上到不了）：上面的紅線比 `count ÷ MIN_TESTS
        > 1.25`，而零相依沙箱只蒸發 `collapse_loss` 支（落地當回合實測 178，遠小於
        `0.25 × MIN_TESTS`）⇒ 下限失去零相依鑑別力那一刻，比例線連 WARN 都還沒到，
        五輪同型復發每次都是環境判準先炸並把讀者指往「相依沒裝齊」。

        本斷言是那五輪缺的那道線：餘裕剩不到四分之一就紅，**早於**環境判準失效，
        紅字直接帶著該重釘成多少。重釘一律由收尾單人窗口在所有並行包停工後做一次。
        """
        suite = run_root_unittests.discover_suite(run_root_unittests._TESTS_DIR)
        self.assertIsNone(
            min_tests_margin.headroom_message(
                suite.countTestCases(),
                run_root_unittests.MIN_TESTS,
                run_root_unittests.suite_modules(suite),
                min_tests_margin.HEADROOM_STALE_FRACTION,
            ),
            "↑ 這則訊息本身就是修法（含該重釘成多少）。它出現＝零相依鑑別力餘裕已剩不到"
            "四分之一，再放著就會輪到 ZeroDepEnvironmentDiscriminationTest 用錯的歸因先炸",
        )

    def test_the_absolute_gap_criterion_reds_a_pin_that_lags_too_far(self) -> None:
        """紅綠自證（合成注入，不依賴當回合實況）＋兩條門檻的相對位置。

        WHY 本軸與上面兩支不重複（`min_tests_margin.ABSOLUTE_GAP_FRACTION` 的 WHY 的
        測試面）：餘裕軸的分母是 `collapse_loss`，`loss <= 0` 時它逐字回 `None`＝
        **不適用**——那幾支相依模組哪天不再整份塌，整條軸靜音，後備只剩 25% 比例線。
        本軸的分母是實跑數自己，結構上不會變成「不適用」。
        """
        self.assertLess(
            min_tests_margin.ABSOLUTE_GAP_FRACTION,
            run_root_unittests.RATCHET_STALE_RATIO - 1.0,
            "絕對餘裕軸的容忍度必須嚴格緊於比例紅線，否則它永遠輪不到說話＝沒有牙",
        )
        allowed = int(1000 * min_tests_margin.ABSOLUTE_GAP_FRACTION)
        self.assertIsNone(
            min_tests_margin.absolute_gap_message(1000, 1000 - allowed),
            "剛好用完容忍額度就判紅＝緩衝帶為空，合法的單輪成長會被誤傷",
        )
        msg = min_tests_margin.absolute_gap_message(1000, 1000 - allowed - 1)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("1000", msg, "提醒必須直接給出該重釘的數字，否則還要人自己算")
        self.assertIn("MIN_TESTS", msg)

    def test_current_pin_gap_is_within_the_absolute_tolerance(self) -> None:
        """棘輪本體（實況面）：`實跑收集數 − MIN_TESTS` 不得吃掉超過實跑數的容忍比例。

        WHY 這一支要存在（M-20 的另一半）：`InvariantLocksArePresentTest` 已讓「整批刪掉
        INV 測試類別」變成會紅的事，但**下限自己的餘裕大小**沒人守——下限落後實跑數越
        遠，「可靜默蒸發幾支測試仍不紅」就越大，而那個數字就是本 runner 唯一的地板的
        鑑別力。紅字直接帶著該重釘成多少；重釘一律由收尾單人窗口在並行包停工後做一次。
        """
        count = run_root_unittests.discover_suite(
            run_root_unittests._TESTS_DIR
        ).countTestCases()
        self.assertIsNone(
            min_tests_margin.absolute_gap_message(count, run_root_unittests.MIN_TESTS),
            "↑ 這則訊息本身就是修法（含該重釘成多少）。它出現＝MIN_TESTS 已被實跑數"
            "甩開太遠，地板的鑑別力被榨乾，請重釘那個常數而不是放寬本容忍度",
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
        # R100：真表非空，隔離它避免合成樹被 stale 自檢誤判 rc=1。
        with mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
            rc = run_root_unittests.run_with_floor(d, min_tests=3)
        self.assertEqual(rc, 0)

    def test_real_repo_meets_pinned_floor(self):
        """真樹鎖：當前 tools/tests 發現數必須 >= MIN_TESTS（釘選與現況不脫節）。"""
        suite = run_root_unittests.discover_suite(run_root_unittests._TESTS_DIR)
        self.assertGreaterEqual(suite.countTestCases(), run_root_unittests.MIN_TESTS)

    def test_main_is_wrapped_by_the_leak_fence(self) -> None:
        """M-03：`main()` 的最終 `return` 必須真的呼叫 `sentinel_lifecycle.leak_fence(...)`
        包住 `run_with_floor(...)`——CI／pre-push 唯一呼叫的漏斗點若漏接這一層，
        leak_fence 的底線防護（`AUTOSDD_SENTINEL_OFF` 補位＋可稽核暫存檔痕跡）就是
        死碼、永遠不會被觸發。走 AST 而非字串比對：字串比對對格式重排（換行／空白）
        敏感，AST 只認呼叫形狀，改個縮排或加個註解都不影響本測試。
        """
        tree = ast.parse(Path(run_root_unittests.__file__).read_text(encoding="utf-8"))
        main_fn = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "main")
        last_stmt = main_fn.body[-1]
        self.assertIsInstance(
            last_stmt, ast.Return,
            "main() 最後一句不是 return（結構被改了，先讀懂新結構再改本測試）")
        call = last_stmt.value
        self.assertIsInstance(call, ast.Call, "main() 的最終 return 不是函式呼叫")
        self.assertEqual(getattr(call.func, "attr", None), "leak_fence",
                         f"main() 的最終 return 沒有呼叫 leak_fence(...)：{ast.dump(call.func)}")
        self.assertEqual(getattr(getattr(call.func, "value", None), "id", None),
                         "sentinel_lifecycle",
                         "呼叫的不是 sentinel_lifecycle.leak_fence")


class ParallelFallbackToSequentialTest(unittest.TestCase):
    """DEF-200-274 第七輪四方獨立複審（Architect／SD 各自命中）：`worker_count()`
    算出 1（例如 `AUTOSDD_PARALLEL_TESTS_WORKERS=1`，或單核心環境的預設公式）時，
    走 subprocess 架構零平行效益、純損耗——本測試鎖住『此時退回序列路徑、不呼叫
    `parallel_shard.run_parallel()`』這條判斷式，不管 `parallel_mode()` 是什麼
    （第九輪：`enabled()` 已刪除，改由 `should_run_parallel()` 判斷，見
    `ShouldRunParallelDecisionTest`）。"""

    def test_worker_count_one_never_calls_run_parallel(self) -> None:
        mod_name = "test_fixture_parallel_fallback"
        self.addCleanup(lambda: sys.modules.pop(mod_name, None))
        with tempfile.TemporaryDirectory(prefix="rru_fallback_") as td:
            d = Path(td)
            (d / f"{mod_name}.py").write_text(
                "import unittest\n\n\n"
                "class Dummy(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            ps = run_root_unittests.parallel_shard
            with mock.patch.object(ps, "worker_count", return_value=1), \
                 mock.patch.object(
                     ps, "run_parallel",
                     side_effect=AssertionError(
                         "run_parallel 不該在 worker_count()==1 時被呼叫——零平行效益、純損耗")
                 ) as mocked_run_parallel, \
                 mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
                rc = run_root_unittests.run_with_floor(d, min_tests=1)
        mocked_run_parallel.assert_not_called()
        self.assertEqual(rc, 0, "序列路徑（TextTestRunner）應正常執行單一通過測試並回傳 0")


class WorkerCountFormulaTest(unittest.TestCase):
    """DEF-200-274 第八輪四方獨立複審（SD／QA 各自點名）：`ParallelFallbackToSequentialTest`
    等既有測試全數用 `mock.patch.object(parallel_shard, "worker_count", ...)` 整個換掉
    函式本體，從未直接呼叫 `worker_count(cpu_count=N)` 斷言公式輸出本身——公式
    （`max(1, min(8, cpu-1))`）、環境變數覆寫、非法值退回三條路徑因此零覆蓋。本類別
    直接呼叫真正的函式，不 mock 它。"""

    def test_formula_across_cpu_counts(self) -> None:
        ps = run_root_unittests.parallel_shard
        # 第九輪：cap 8→9（worker_count 上限，見 parallel_shard.worker_count docstring）。
        cases = {0: 1, 1: 1, 2: 1, 9: 8, 10: 9, 100: 9}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ps._ENV_WORKERS, None)  # 清掉本機 shell profile 可能殘留的覆寫
            for cpu, expected in cases.items():
                self.assertEqual(
                    ps.worker_count(cpu_count=cpu), expected,
                    f"cpu_count={cpu} 應得 {expected}（公式 max(1, min(9, cpu-1))）")

    def test_workers_env_override_wins_over_formula(self) -> None:
        ps = run_root_unittests.parallel_shard
        with mock.patch.dict(os.environ, {ps._ENV_WORKERS: "3"}, clear=False):
            self.assertEqual(
                ps.worker_count(cpu_count=100), 3,
                "合法正整數覆寫應勝過公式，即使公式本會算出更大的值")

    def test_invalid_override_values_fall_back_to_formula(self) -> None:
        ps = run_root_unittests.parallel_shard
        for bad in ("0", "-5", "abc"):
            with mock.patch.dict(os.environ, {ps._ENV_WORKERS: bad}, clear=False):
                self.assertEqual(
                    ps.worker_count(cpu_count=9), 8,
                    f"非法覆寫值 {bad!r} 應退回預設公式，不應讓平行模式整支炸掉")

    def test_none_cpu_count_uses_real_os_cpu_count_within_bounds(self) -> None:
        """`cpu_count=None` 時走真的 `os.cpu_count()`——不斷言精確值（該值隨執行機器
        核心數而變），只斷言落在公式的值域 `[1, 9]` 內（第九輪：cap 8→9）。"""
        ps = run_root_unittests.parallel_shard
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ps._ENV_WORKERS, None)
            result = ps.worker_count(cpu_count=None)
        self.assertGreaterEqual(result, 1)
        self.assertLessEqual(result, 9)


class ShouldRunParallelDecisionTest(unittest.TestCase):
    """DEF-200-274 第九輪 D1：`parallel_shard.should_run_parallel()` 三條件的真值表
    ——P1 根治的機械化：`test_synthetic_tree_always_sequential_regardless_of_mode`
    是核心斷言（合成樹無論 mode 為何一律序列，即使殼層殘留 `AUTOSDD_PARALLEL_
    TESTS=1`）。"""

    def _real_and_synthetic(self):
        ps = run_root_unittests.parallel_shard
        real = run_root_unittests._TESTS_DIR
        synthetic = real.parent  # tools/ 本身必不等於 tools/tests
        return ps, real, synthetic

    def test_off_forces_sequential_even_on_real_tree_with_many_workers(self) -> None:
        ps, real, _synthetic = self._real_and_synthetic()
        with mock.patch.dict(os.environ, {ps._ENV_ON: "0"}, clear=False):
            self.assertFalse(ps.should_run_parallel(real, real, workers=8))

    def test_on_and_auto_agree_on_real_tree_with_many_workers(self) -> None:
        ps, real, _synthetic = self._real_and_synthetic()
        for raw in (None, "1", "garbage"):
            with self.subTest(raw=raw):
                with mock.patch.dict(os.environ, {}, clear=False):
                    if raw is None:
                        os.environ.pop(ps._ENV_ON, None)
                    else:
                        os.environ[ps._ENV_ON] = raw
                    self.assertTrue(
                        ps.should_run_parallel(real, real, workers=8),
                        f"raw={raw!r} 應與顯式 '1' 收斂成 True（auto 與 on 一致）")

    def test_synthetic_tree_always_sequential_regardless_of_mode(self) -> None:
        """P1 核心斷言：合成樹無論 `AUTOSDD_PARALLEL_TESTS` 為何值都必須序列。"""
        ps, _real, synthetic = self._real_and_synthetic()
        for raw in ("1", None):
            with self.subTest(raw=raw):
                with mock.patch.dict(os.environ, {}, clear=False):
                    if raw is None:
                        os.environ.pop(ps._ENV_ON, None)
                    else:
                        os.environ[ps._ENV_ON] = raw
                    self.assertFalse(
                        ps.should_run_parallel(synthetic, run_root_unittests._TESTS_DIR, workers=8),
                        f"raw={raw!r} 時合成樹仍必須被判為序列——這正是 P1 的核心修復")

    def test_workers_le_1_forces_sequential_regardless_of_mode(self) -> None:
        ps, real, _synthetic = self._real_and_synthetic()
        for raw in ("1", None):
            with self.subTest(raw=raw):
                with mock.patch.dict(os.environ, {}, clear=False):
                    if raw is None:
                        os.environ.pop(ps._ENV_ON, None)
                    else:
                        os.environ[ps._ENV_ON] = raw
                    self.assertFalse(ps.should_run_parallel(real, real, workers=1))


class RunWithFloorNeverParallelizesSyntheticTreeTest(unittest.TestCase):
    """端到端：`run_with_floor()` 對合成目錄、即使殼層設了
    `AUTOSDD_PARALLEL_TESTS=1`，也不觸發 `run_parallel()`（P1 根治的整合驗證，
    補上 `ShouldRunParallelDecisionTest` 的純函式覆蓋）。"""

    def test_synthetic_tree_with_env_forced_on_never_calls_run_parallel(self) -> None:
        mod_name = "test_fixture_p1_synthetic_guard"
        self.addCleanup(lambda: sys.modules.pop(mod_name, None))
        with tempfile.TemporaryDirectory(prefix="rru_p1_") as td:
            d = Path(td)
            (d / f"{mod_name}.py").write_text(
                "import unittest\n\n\nclass Dummy(unittest.TestCase):\n"
                "    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            ps = run_root_unittests.parallel_shard
            with mock.patch.dict(os.environ, {ps._ENV_ON: "1"}, clear=False), \
                 mock.patch.object(ps, "worker_count", return_value=8), \
                 mock.patch.object(
                     ps, "run_parallel",
                     side_effect=AssertionError("run_parallel 不該被合成樹觸發"),
                 ) as mocked, \
                 mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
                rc = run_root_unittests.run_with_floor(d, min_tests=1)
        mocked.assert_not_called()
        self.assertEqual(rc, 0)


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

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈UntaggedWindowsLikeSkipsTest WHY（低報 33% 的實測）〉。
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
        # `tools/lib/windows_skip_tags.py`（見該檔頭），平台閘讀的是**該模組**的判定。
        # 🔴 R82（SA B-1）：patch 目標由 `windows_skip_tags.os` 的 `name` 屬性改為
        # 模組層函式 `running_on_windows`——前者改的是**行程全域**的 `os.name`，會讓
        # `pathlib.Path()` 在 Windows 上整段拋 `PosixPath` 例外，於是同一份判準在
        # pytest 與 unittest 兩個載具下給出相反判決（WHY 全文見 `running_on_windows`）。
        with mock.patch.object(windows_skip_tags, "running_on_windows", lambda: False):
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
        # `tools/lib/windows_skip_tags.py`（見該檔頭），平台閘讀的是**該模組**的判定。
        # 🔴 R82（SA B-1）：這裡原本 patch 的是 `windows_skip_tags.os` 的 `name` ＝
        # **行程全域**的 `os.name`。pytest 載具下 `AssertionRewritingHook` 會對每一支
        # 新 import 的模組呼叫 `Path()`，patch 期間那必定拋 `PosixPath` 例外 ⇒ 下面
        # 合成出來的樹 import 失敗、塌成 `_FailedTest`、收集數低於下限 ⇒ **兩次**
        # `run_with_floor` 都回 1：紅的那一半理由是錯的，綠的那一半永遠綠不了。
        # R100：真表自本輪起非空，隔離它避免合成樹被 stale 自檢誤判 rc=1。
        with mock.patch.object(windows_skip_tags, "running_on_windows", lambda: False), \
             mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
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


class WindowsSkipTagExemptionSelfCheckTest(unittest.TestCase):
    """本輪：具名豁免表 `_WINDOWS_SKIP_TAG_EXEMPT` 的 stale／格式自檢。

    WHY（實測到的缺口，不是理論）：動工前往該表塞一筆指向不存在檔案的豁免、以及
    一筆指向真檔但根本不需要豁免的條目，整支本檔（73 tests）兩次都**零 failure**。
    對照組是同一支 runner 的姊妹表 `_COLLECTION_EXEMPT`：塞一筆多餘豁免當場紅。
    ⇒ 同一個 repo 對「豁免表要有 stale 自檢」有明確認知，卻只實作在兩張表中的一張；
    本表現在是空的所以看起來乾淨，第一筆進去的那天起它就是一張只進不出的永久豁免表。

    本組鎖的是判準本身（純函式 ＋ 合成注入），另加一支接線鎖確認 rc 真的被消費。
    """

    def _result_with_skips(self, *skips: tuple[str, str]) -> unittest.TestResult:
        class _T:
            def __init__(self, tid: str) -> None:
                self._tid = tid

            def id(self) -> str:
                return self._tid

        result = unittest.TestResult()
        result.skipped = [(_T(tid), reason) for tid, reason in skips]
        return result

    def test_an_exemption_that_suppresses_nothing_is_stale(self) -> None:
        """注入：豁免指向的站點**在本平台真的 skip 了**，卻在「當表是空的」重掃裡
        根本不會被判違規 ⇒ 必紅（reason 改寫／已補標籤，豁免已無壓制對象）。"""
        problems = windows_skip_tags.exemption_problems(
            {"m.C.test_gone": "R70 起改走別的路，暫時豁免"},
            flagged_without_exempt={},
            skipped_here={"m.C.test_gone"},
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("stale", problems[0])

    def test_an_exemption_that_still_suppresses_something_is_accepted(self) -> None:
        """對照組：仍在壓住真違規的豁免必須放行，否則本鎖無法被滿足。"""
        self.assertEqual(
            windows_skip_tags.exemption_problems(
                {"m.C.test_x": "R70 複查：本機 docker 供給問題，非平台語意"},
                flagged_without_exempt={"m.C.test_x": "需要 Windows 主開發機才有的 docker"},
                skipped_here={"m.C.test_x"},
            ),
            [],
        )

    def test_an_exemption_is_not_stale_where_its_test_actually_ran(self) -> None:
        """🔴 DEF-200-233 迴歸鎖（macos-compat-ci 連續紅的真因，方向鎖不是門檻鎖）。

        WHY（Rule 9 — 鎖的是意圖）：stale 面的輸入是**本平台這一次真的 skip 了什麼**。
        一支測試在本平台**跑掉了**（例：zsh 站點在 darwin 上，zsh 是預設殼）時，它當然
        不會出現在重掃結果裡——但那是「本平台對這筆豁免沒話可說」，**不是**「豁免過期」。
        修前兩者塌成同一個結論，於是 darwin 把 7 筆**仍在 linux 上承重**的豁免全判 stale；
        照那個判決移除會當場讓 root-infra-ci 轉紅（同一份判準在兩個平台給出互斥的指示）。
        本鎖釘住方向：`skipped_here` 不含它 ⇒ 一個字都不准說。
        """
        self.assertEqual(
            windows_skip_tags.exemption_problems(
                {"m.C.test_ran_here": "R100：reason 只是拿 Windows 做比較性陳述"},
                flagged_without_exempt={},          # 本平台沒 skip ⇒ 不可能在重掃結果裡
                skipped_here=set(),                 # ← 判準的分水嶺：它這次真的跑了
                known_ids={"m.C.test_ran_here"},    # 收集面仍有它 ⇒ 也不是改名／刪除
            ),
            [],
            "測試在本平台跑掉了不等於豁免過期——這正是 macos-compat-ci 那 7 筆假紅",
        )

    def test_an_exemption_whose_test_left_the_tree_is_stale_on_every_platform(self) -> None:
        """🔴 DEF-200-233 補位鎖：收窄 stale 面之後，「測試改名／刪除」不得因此變成永久豁免。

        這一面刻意**不分平台**（連 Windows 都說話，修前那裡整組早退），故豁免表的
        「只進不出」防線射程比修前更大，不是被放寬。
        """
        problems = windows_skip_tags.exemption_problems(
            {"m.C.test_renamed_away": "R100：曾經需要豁免"},
            known_ids={"m.C.test_something_else"},
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("stale", problems[0])
        self.assertIn("收集面", problems[0], "訊息須說清楚是哪一種過期，否則讀者無從下手")

    def test_the_vanished_face_is_off_when_the_caller_has_no_collection_surface(self) -> None:
        """對照組：拿不到收集面（合成樹呼叫端）時消失面不判——否則整片假紅。"""
        self.assertEqual(
            windows_skip_tags.exemption_problems({"m.C.test_x": "R100：理由"}), [])

    def test_an_exemption_without_a_handover_round_is_flagged(self) -> None:
        """格式面：沒寫承接輪次的豁免＝沒有人負責拿掉它。"""
        problems = windows_skip_tags.exemption_problems(
            {"m.C.test_x": "本機 docker 供給問題，非平台語意"},
            flagged_without_exempt={"m.C.test_x": "需要 Windows 的 docker"},
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("承接輪次", problems[0])

    def test_the_stale_face_is_off_when_the_detector_is_silent(self) -> None:
        """🔴 Scan-H⑥ 互鎖：偵測器在 Windows 上整組早退，此時不得判 stale。

        沒有這一條，Windows 上每一筆合法豁免都會被判 stale ＝整片假紅，而那個早退
        本身是對的（見 `untagged_windows_like_skips` 的 WHY）。
        """
        self.assertEqual(
            windows_skip_tags.exemption_problems(
                {"m.C.test_x": "R70 複查：非平台語意"}, flagged_without_exempt=None),
            [],
        )

    def test_the_live_table_passes_its_own_check(self) -> None:
        """現況自檢：活體表（讀 assert 當下的模組屬性，不快照）必須合格。"""
        self.assertEqual(
            windows_skip_tags.exemption_problems(
                windows_skip_tags._WINDOWS_SKIP_TAG_EXEMPT), [])

    def test_the_check_is_wired_into_the_runner_and_reds_the_run(self) -> None:
        """接線鎖 ＋ rc 鎖：單元測了卻沒接線、或接線了不改 rc，都是假綠。

        注入方式刻意是 `mock.patch.dict` **活體模組屬性**——`run_root_unittests`
        的名字與 `windows_skip_tags` 的必須是同一個 dict，否則既有的 patch 契約
        （見 `test_hints_and_tag_are_shared_with_the_runtime_lock_not_copied`）
        已經悄悄退化成兩份副本。
        """
        # R100：`clear=True`——真表非空，`clear=False` 會讓既有筆數疊進 `problems`。
        # DEF-200-233：注入的豁免必須指向**本次真的 skip 掉**的那一支，否則新判準（正確地）
        # 判它「本平台沒話可說」而回空——接線鎖會退化成恆綠。
        result = self._result_with_skips(("m.C.test_x", "一般性 skip，與平台無關"))
        buf = io.StringIO()
        with mock.patch.object(windows_skip_tags, "running_on_windows", lambda: False), \
             mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT,
                             {"m.C.test_x": "R70 暫時豁免"}, clear=True), \
             contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            problems = run_root_unittests.report_windows_skip_tag_exemption_problems(result)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("m.C.test_x", buf.getvalue(), "必須逐筆點名，否則讀者不知道刪哪一筆")

    def test_real_run_with_floor_reds_on_a_bad_exemption(self) -> None:
        """端到端常駐對照組：合成樹本身乾淨，只有豁免表壞掉 ⇒ rc 必須由 0 變 1。

        沒有這一支，「印了紅字卻照樣 rc=0」這種 fail-open 不會被任何東西看見。
        注入的是**格式面**（沒有承接輪次）——它不分平台，故本支在三個平台都說話。
        """
        base = Path(tempfile.mkdtemp(prefix="rru_exempt_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        mod = "test_fixture_clean_for_exempt"
        self.addCleanup(lambda: sys.modules.pop(mod, None))
        (base / f"{mod}.py").write_text(
            textwrap.dedent(
                """\
                import unittest


                class Dummy(unittest.TestCase):
                    def test_a(self):
                        self.assertTrue(True)

                    def test_b(self):
                        self.assertTrue(True)
                """
            ),
            encoding="utf-8",
        )
        # R100：真表自本輪起非空，隔離它避免合成樹被 stale 自檢誤判 rc=1。
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()), \
             mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
            rc_clean = run_root_unittests.run_with_floor(base, min_tests=2)
            with mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT,
                                 {"m.C.test_x": "沒有承接者的理由"}, clear=False):
                rc_bad = run_root_unittests.run_with_floor(base, min_tests=2)
        self.assertEqual(rc_clean, 0, "乾淨樹必須 rc=0——否則下一條比較沒有意義")
        self.assertEqual(rc_bad, 1, "豁免表壞掉時 rc 仍為 0 ⇒ 判準沒有接進 rc（fail-open）")

    def test_run_with_floor_really_hands_the_collection_surface_to_the_check(self) -> None:
        """🔴 DEF-200-233 接線鎖：`known_ids` 是消失面的**唯一**輸入，沒傳等於那一面不存在。

        判別力來源：注入的豁免指向一個**收集面裡沒有**的 id，而它同時**沒有** skip
        （合成樹根本不認識它）⇒ 只有拿到收集面的判準說得出話。runner 若漏傳
        `known_ids`，本支恆綠——那正是收窄 stale 面之後最容易靜默出現的退化。
        """
        base = Path(tempfile.mkdtemp(prefix="rru_exempt_known_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        mod = "test_fixture_clean_for_known_ids"
        self.addCleanup(lambda: sys.modules.pop(mod, None))
        (base / f"{mod}.py").write_text(
            textwrap.dedent(
                """\
                import unittest


                class Dummy(unittest.TestCase):
                    def test_a(self):
                        self.assertTrue(True)

                    def test_b(self):
                        self.assertTrue(True)
                """
            ),
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()), \
             mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT,
                             {"m.C.test_never_collected": "R108 複查：注入用"}, clear=True):
            rc = run_root_unittests.run_with_floor(base, min_tests=2)
        self.assertEqual(
            rc, 1,
            "豁免指向一個不在收集面裡的 test id，rc 仍為 0 ⇒ runner 沒把收集面傳給判準",
        )


class UnregisteredSkipTagVocabularyTest(unittest.TestCase):
    """本輪：`ALL_SKIP_TAGS` 的**成員檢查**（R76 §3 finding F3，當輪未修）。

    WHY：該常數此前只被用來「比對已知標籤」，沒有任何機械物反向問「這個看起來像
    標籤的字面有沒有登記過」⇒ 發明一個新標籤是零成本的，而後果是人看起來有標籤、
    機器看起來沒標籤，同一支 skip 在兩份報表上分類不一致。
    """

    def test_an_unregistered_tag_beyond_the_ratchet_is_flagged(self) -> None:
        """語料含存量那一筆（讓它對帳），另加一個未登記標籤 ⇒ 只該多出一筆問題。"""
        problems = windows_skip_tags.unregistered_tag_problems(
            ["[CARRIER-NO-DISCRIMINATION] 存量那一筆", "[TOOL-MISSING] ruff 不在 PATH"])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("[TOOL-MISSING]", problems[0])
        self.assertIn(windows_skip_tags.TOOL_ABSENCE_SKIP_TAG, problems[0],
                      "訊息須給出可行動的替代標籤，否則作者只能再發明一個")

    def test_registered_tags_and_untagged_reasons_are_accepted(self) -> None:
        """對照組：已登記標籤與完全沒有標籤的 reason 都不歸本判準管。"""
        self.assertEqual(
            windows_skip_tags.unregistered_tag_problems(
                [f"{tag} 說明" for tag in windows_skip_tags.ALL_SKIP_TAGS]
                + ["本機缺 docker daemon"]
                + ["句中提到 [SOME-MARKER] 但不在開頭"]
                + ["[CARRIER-NO-DISCRIMINATION] 存量那一筆"]),
            [],
        )

    def test_clearing_the_debt_also_speaks(self) -> None:
        """棘輪雙向：存量清掉而沒下修，訊息必須指名要改哪一個常數。"""
        problems = windows_skip_tags.unregistered_tag_problems([])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("_UNREGISTERED_TAG_DEBT", problems[0])

    def test_nonliteral_reasons_are_recovered_for_the_vocabulary_lock(self) -> None:
        """R79 的**非字面 reason** 抽取面（`nonliteral_skip_reason_prefixes`）。

        WHY 這一支非補不可（QA-R79）：上面那道詞彙鎖的輸入原本只有 `literal_eval`
        成功的站點，而 R76 指名的唯一已知違規實例（`self.skipTest(f"[TOOL-MISSING] …")`）
        正好是 f-string ⇒「已知缺陷 → 建了鎖 → 鎖看不到那個已知缺陷」，隱形三輪。
        R79 補上抽取面卻**零回歸鎖**，注入證明只活在會被丟掉的 scratchpad。
        判準的核心是「標籤依契約住在 reason 最前面 ⇒ 取開頭常數片段就夠判，不需求值」，
        兩種形態（f-string／`+` 串接）都要吃得下，而**字面值不得重複計**（那一批由
        `skip_decorator_sites` 承接，兩面各自對自己的存量帳）。
        """
        source = textwrap.dedent(
            """\
            import unittest


            class C(unittest.TestCase):
                def test_a(self):
                    self.skipTest(f"[TOOL-MISSING] {tool} 不在 PATH")

                def test_b(self):
                    self.skipTest("[PG-CORPUS-STALE] " + why)

                def test_c(self):
                    self.skipTest("[TOOL-ABSENCE] 字面值，由另一面承接")
            """
        )
        got = windows_skip_tags.nonliteral_skip_reason_prefixes({"m.py": source})
        self.assertEqual(
            sorted(got), ["[PG-CORPUS-STALE] ", "[TOOL-MISSING] "],
            "f-string／串接的開頭標籤沒被抽出來（或字面值被重複計入）——"
            "前者讓已知違規繼續隱形，後者會污染另一面的對帳",
        )

    def test_the_two_populations_keep_separate_ledgers(self) -> None:
        """非字面那一面用**自己的**存量帳；新的未登記標籤照樣當場紅。

        WHY 分兩張帳：兩者是不同的量測母體，併表會讓其中一面的站點增減污染另一面的
        對帳（落地當回合實測：併表當場弄紅本類上面那三支合成語料測試）。
        """
        self.assertEqual(
            windows_skip_tags.unregistered_tag_problems(
                ["[TOOL-MISSING] x"], debt={"[TOOL-MISSING]": 1}),
            [],
        )
        problems = windows_skip_tags.unregistered_tag_problems(
            ["[TOOL-MISSING] x", "[BRAND-NEW-TAG] y"], debt={"[TOOL-MISSING]": 1})
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("[BRAND-NEW-TAG]", problems[0])


class StaticWindowsSkipTagScanTest(unittest.TestCase):
    """R72：`[WINDOWS-NATIVE-ONLY]` 標籤完整性的**靜態、跨平台**鎖。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈StaticWindowsSkipTagScanTest WHY（三道閘門同一個瞎點）〉。
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
        # 🔴 R86：判準由字面 `return 1` 放寬為 `return 1` 或 `return _bail(...)`，
        # 而 rc 那一半改由**真的呼叫**來量（見下方 assert），不再靠字面推論。
        # WHY：本鎖把「rc 有沒有被收斂」綁在一個字面上，於是本輪把四條早退
        # 路徑改成 `_bail(<階段名>)`（同 rc=1，只多印一行「零執行」）時它判紅
        # ——而那個改動**嚴格增強**了它要守的東西（修前 rc=1 但畫面零 FAIL
        # 行，人會誤讀成通過；R85 已具名交棒）。字面鎖的代價正是這個：**它會
        # 擋住讓它守的性質變強的修法**，而該鎖的是「rc 真的非零」這個行為。
        self.assertRegex(
            src,
            r"if report_untagged_windows_skip_decorators\(_TESTS_DIR, _PATTERN\):"
            r"\s*\n\s*return (?:1|_bail\()",
            "掃描結果必須真的參與 rc 收斂，否則印了紅字卻照樣 rc=0（fail-open）",
        )
        # 牙齒沒放鬆：走 `_bail` 那條路時，實際回傳值必須仍是非零。
        if "return _bail(" in src:
            self.assertEqual(
                run_root_unittests._bail("靜態標籤掃描（不分平台）"), 1,
                "_bail() 必須回非零，否則早退靜默 fail-open（本鎖真正標的）",
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


class ProblemReportItemizationTest(unittest.TestCase):
    """R83：「表頭報 N 筆，明細只印其中兩類」的回歸鎖（舵手當回合實測到的 2 行輸出）。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈ProblemReportItemizationTest 修前實況〉。
    """

    @staticmethod
    def _producer_keys() -> set[str]:
        """以 AST 讀出生產端那個 dict literal 的鍵。

        刻意用靜態讀取而非「跑一次掃描看回傳了哪些前綴」：後者只看得到**本次真的觸發**
        的類別，而本鎖要抓的正是「原始碼裡多了一鍵、但那一鍵這次沒觸發」。
        """
        src = inspect.getsource(
            windows_skip_tags.report_untagged_windows_skip_decorators)
        calls = [
            node for node in ast.walk(ast.parse(textwrap.dedent(src)))
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "_ordered_buckets"
        ]
        assert len(calls) == 1, f"生產端入口不是恰好一個 `_ordered_buckets(...)`：{calls}"
        literal = calls[0].args[0]
        assert isinstance(literal, ast.Dict), "生產端必須是 dict literal，否則本鎖讀不到鍵"
        return {k.value for k in literal.keys if isinstance(k, ast.Constant)}

    def test_every_message_is_itemized_including_unregistered_categories(self) -> None:
        """不變量①②：每一筆明細都被印出，且表頭數字＝明細行數。

        合成的 `尚未登記的新類別` 就是「下一個人新增一類卻忘了登記」的注入對照組：
        它必須**照印並被點名**，而不是靜默消失——靜默消失正是修前那個病的極端形。
        """
        buckets = {
            name: [f"{name}-合成第一筆", f"{name}-合成第二筆"]
            for name in windows_skip_tags._PROBLEM_CATEGORY_WHY
        }
        buckets["尚未登記的新類別"] = ["合成：未登記類別的唯一一筆"]
        lines = windows_skip_tags.render_problem_report(buckets)
        blob = "\n".join(lines)
        for category, msgs in buckets.items():
            for msg in msgs:
                self.assertIn(
                    msg, blob,
                    f"類別 `{category}` 的明細沒有被印出來——讀者會看到一個報了 N 筆卻"
                    f"列不出 N 筆的清單，然後去找一個不存在的問題（修前實況）",
                )
        self.assertIn(
            "沒有登記在", blob,
            "未登記的類別必須被點名（fail-loud）：漏登記本身是缺陷，但不得因此吃掉問題本文",
        )
        itemized = [line for line in lines if line.startswith("   - ")]
        total = sum(len(msgs) for msgs in buckets.values())
        self.assertEqual(
            len(itemized), total,
            f"印出 {len(itemized)} 行明細、實際有 {total} 筆問題——兩者一旦不等，"
            f"表頭那個數字就是在替看不見的東西背書",
        )
        self.assertIn(
            f"發現 {total} 個問題", lines[0],
            "表頭數字必須與明細同源（修前是 len(總和) vs 只涵蓋兩類的迴圈）",
        )

    def test_extra_detail_is_never_silently_dropped(self) -> None:
        """補充明細（逐站點理由／修法指路）自己也受同一條不變量管轄。

        它沒有自己的計數，所以「鍵名打錯 ⇒ 整段消失」不會讓任何數字對不上——這正是
        同型缺陷的第二個入口，故歸屬不到 bucket 的補充明細一律照印並點名。
        """
        lines = windows_skip_tags.render_problem_report(
            {"漏標": ["合成：某支測試漏標"]},
            {"漏標": ["       · 合成的逐站點理由"], "鍵名打錯了": ["       · 合成的孤兒明細"]},
        )
        blob = "\n".join(lines)
        self.assertIn("合成的逐站點理由", blob)
        self.assertIn(
            "合成的孤兒明細", blob,
            "歸屬不到任何類別的補充明細被靜默丟掉 ⇒ 沒有任何計數會對不上，永遠不會被發現",
        )

    def test_producer_keys_and_the_registry_are_the_same_set(self) -> None:
        """不變量③：雙向相等。多一鍵沒登記＝紅；登記了卻沒有生產者（死類別）＝也紅。

        單向（只查「登記的都有人生產」）擋不住本輪這個缺陷的復發形態——新增一鍵才是
        危險的那個方向。反向也判是因為死類別會讓這張表變成「說了不算」的散文。
        """
        self.assertEqual(
            self._producer_keys(), set(windows_skip_tags._PROBLEM_CATEGORY_WHY),
            "生產端的類別鍵與 `_PROBLEM_CATEGORY_WHY` 不一致：多的那一鍵沒有 WHY 可印"
            "（讀者只會看到一行「這個類別沒有登記」），少的那一鍵是死類別",
        )

    def test_the_returned_problems_are_derived_only_from_the_buckets(self) -> None:
        """封住旁路：問題只能經 buckets 出去。

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_the_returned_problems_are_derived_only_from_the_buckets 三形態與 R83 補款〉。
        """
        fn = ast.parse(textwrap.dedent(inspect.getsource(
            windows_skip_tags.report_untagged_windows_skip_decorators))).body[0]
        collectors: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                collectors.add(node.target.id)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"append", "extend"}
                    and isinstance(node.func.value, ast.Name)):
                collectors.add(node.func.value.id)
        self.assertNotIn(
            "problems", collectors,
            "reporter 又出現扁平的 `problems` 累積器 ⇒ 有問題不經 buckets ⇒ 印列面看不到它。"
            "請改成在那個 dict literal 內多一鍵，並到 `_PROBLEM_CATEGORY_WHY` 登記",
        )
        returns = [node for node in ast.walk(fn) if isinstance(node, ast.Return)]
        self.assertTrue(returns, "reporter 沒有 return——本鎖無從取值")
        for node in returns:
            if isinstance(node.value, ast.List) and not node.value.elts:
                continue  # 「沒有問題」的那條路徑，回空 list 是對的
            self.assertIn(
                "buckets", ast.dump(node.value),
                f"第 {node.lineno} 行的 return 不是從 `buckets` 展開的 ⇒ 回傳的問題可能"
                f"從來沒有被印出來（表頭數字與明細再度脫鉤）",
            )
            merged = [n for n in ast.walk(node.value)
                      if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)]
            starred = [n for n in ast.walk(node.value) if isinstance(n, ast.Starred)]
            self.assertEqual(
                (len(merged), len(starred) > 1), (0, False),
                f"第 {node.lineno} 行的 return 把 buckets 展開的結果與**另一個來源**併接"
                f"（`+` 或多個 `*` 展開）⇒ 那一半不經 `render_problem_report`、永遠不會被"
                f"印出來，而 `buckets` 仍出現在同一條 return 裡故上一道判準放行（獨立複審"
                f"注入 case G 實測）。新問題請進那個 dict literal，不要在 return 上併接",
            )

    def test_empty_scan_surface_is_itemized_not_merely_counted(self) -> None:
        """端到端注入（**修前必紅**的那一支）：空掃描面是七類中唯一沒人印的那一類。

        修前輸出＝只有一行「發現 1 個問題：」，之後空無一物（舵手實測形態）。
        """
        base = Path(tempfile.mkdtemp(prefix="rru_report_empty_"))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            problems = windows_skip_tags.report_untagged_windows_skip_decorators(
                base, run_root_unittests._PATTERN)
        out = buf.getvalue()
        self.assertEqual(len(problems), 1, f"空掃描面必須 fail-closed：{problems}")
        self.assertIn("掃描面為空", out, "類別名必須出現，否則讀者不知道紅在哪一層")
        for problem in problems:
            self.assertIn(
                problem.split("：", 1)[1], out,
                "回傳了問題卻沒有印出它的明細——讀者只會看到一個空清單",
            )

    def test_the_live_gate_prints_every_problem_it_returns(self) -> None:
        """活體鎖：真 repo 這一棵樹上，回傳的每一筆都必須印得出來。

        兩個分支都有斷言（刻意不寫成「有問題才檢查」的空轉鎖）：有問題時驗逐筆覆蓋，
        沒問題時驗「什麼都不該印」——後者是修前另一半的對稱風險（替空清單印表頭）。
        """
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            problems = windows_skip_tags.report_untagged_windows_skip_decorators(
                run_root_unittests._TESTS_DIR, run_root_unittests._PATTERN)
        out = buf.getvalue()
        if not problems:
            self.assertEqual(out, "", "沒有問題卻印了東西＝表頭在替一個空清單背書")
            return
        self.assertIn(f"發現 {len(problems)} 個問題", out, "表頭數字必須是回傳的筆數")
        for problem in problems:
            self.assertIn(
                problem.split("：", 1)[1], out,
                f"閘門回報了 `{problem}` 卻沒印出它的明細——讀者會去找一個看不到的問題",
            )


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

    def test_failure_detail_is_also_printed_to_stderr(self) -> None:
        """DEF-200-274 CI 事故（commit 9478bda，root-infra-ci run 34358252409）：
        平行模式此前只把明細落檔、從未印到 console——CI runner 的落檔目錄是 job
        臨時工作目錄，job 結束即銷毀，三支 CI workflow 也都沒有 upload-artifact
        步驟，主控台因而完全看不到任何 FAIL:/ERROR:/Traceback。本測試鎖住修法：
        落檔內容必須同時印到 stderr，與序列模式 `TextTestRunner` 內建
        `printErrors()` 的行為對等。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "f.log"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                run_root_unittests.dump_failure_detail(
                    self._result_with(
                        failures=[("m.C.test_a", "AssertionError: boom")],
                        errors=[("m.C.test_b", "RuntimeError: kaboom")],
                    ),
                    target,
                )
        printed = stderr.getvalue()
        expected_all = (
            "m.C.test_a", "AssertionError: boom",
            "m.C.test_b", "RuntimeError: kaboom",
        )
        for expected in expected_all:
            self.assertIn(expected, printed,
                          f"失敗明細未印到 stderr（{expected!r} 缺席）——CI 主控台仍會看不到內容")

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

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈CollectionIntegrityTest WHY（894／906／916 三個時間切片）〉。
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
        （沿用本檔 `windows_native_skips` 一系列測試已建立的紀律）。

        R100：真表非空，隔離它避免合成樹被 stale 自檢誤判 rc=1。
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, {}, clear=True):
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


# 沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈R68 零相依環境鑑別力鎖的立案與模擬手法〉。
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

if sys.argv[2] == "collect":
    # DEF-200-170：**只 discover、不執行任何測試**的收集面快照（秒級），回答「沙箱裡哪幾支
    # 模組塌了、各留幾支」——`min_tests_margin` 唯一的釘選面就靠它保鮮，不靠靜態猜測。
    _s = R.discover_suite(R._TESTS_DIR)
    print(json.dumps({"count": _s.countTestCases(), "mods": R.suite_modules(_s),
                      "placeholders": [m for m, _k in R.discovery_placeholders(_s)]}))
    sys.exit(0)
if sys.argv[2] == "main":
    sys.exit(R.main())
# "floor"：刻意繞過 main() 的 fail-fast，直接叩下限守門本身——證明**即使**前置
# 檢查被拿掉，下限層在零相依環境下仍然判紅（鑑別力不靠 fail-fast 撐著）。
sys.exit(R.run_with_floor(R._TESTS_DIR, R.MIN_TESTS))
'''


#: `floor` 模式的探針會在**本套件內部**再把整棵真實樹跑一次（`run_with_floor` 會 discover
#: 並執行）。逾時沿革（R74 兩支 TimeoutExpired、為何不是調大常數、真正主因是遞迴、
#: 結構性修法已登記 DEF-101-803）全文搬至
#: docs/06_quality/CrossPlatform_Guard_Line_History.md〈DEF-101-803 floor 探針沿革〉節。
#: 正解是斷遞迴——子行程帶 `_ZERO_DEP_PROBE_ENV` 旗標，本類別見到旗標即自我 skip，
#: 於是子行程只跑一層（零相依下收集本就會塌縮，該層很快）；同參數只跑一次（見下方快取）。
_ZERO_DEP_PROBE_ENV = "RRU_IN_ZERO_DEP_PROBE"
_ZERO_DEP_PROBE_TIMEOUT = 600


def _zero_dep_child_env() -> dict[str, str]:
    """斷『平行』遞迴（與既有 `_ZERO_DEP_PROBE_ENV` 斷『skip 掃描』遞迴的精神一致，
    但是兩件獨立的事，不合併成同一個旗標）。DEF-200-274 第九輪 P0：D1 把
    `AUTOSDD_PARALLEL_TESTS` 未設的語意從「序列」改成「auto（真實樹＋workers>1
    即平行）」後，本探針子行程對 `R._TESTS_DIR`（貨真價實的真樹）整套重跑一次時
    （`floor`／`main` 模式）會被新語意捲入、疊加在外層已在跑的 fan-out 之上
    （DEF-101-803 遞迴熱點史料：823s→3813s 且仍逾時）。不管外層 `AUTOSDD_
    PARALLEL_TESTS` 是什麼值（未設／"1"／zshrc 殘留），探針子行程一律強制序列
    ——退回 D1 之前的「未設＝序列」基準，不被新語意捲入。
    """
    child_env = {**os.environ, _ZERO_DEP_PROBE_ENV: "1"}
    child_env[run_root_unittests.parallel_shard._ENV_ON] = "0"
    return child_env


@functools.cache
def _zero_dep_probe_cached(
    mode: str, blocked_key: tuple[str, ...]
) -> subprocess.CompletedProcess[str]:
    tools_dir = str(Path(run_root_unittests.__file__).resolve().parent)
    child_env = _zero_dep_child_env()
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "zero_dep_probe.py"
        probe.write_text(_ZERO_DEP_PROBE, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(probe), json.dumps(list(blocked_key)), mode, tools_dir],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=tools_dir, timeout=_ZERO_DEP_PROBE_TIMEOUT, env=child_env,
        )


class ZeroDepProbeForcesSequentialChildEnvTest(unittest.TestCase):
    """DEF-200-274 第九輪 P0：即使外層環境要求平行，探針子行程必須強制序列，
    否則 D1 的 auto 預設會讓 DEF-101-803 的遞迴熱點在每次全套執行時重演。"""

    def test_child_env_forces_off_even_when_parent_env_requests_parallel(self) -> None:
        R = run_root_unittests
        with mock.patch.dict(os.environ, {R.parallel_shard._ENV_ON: "1"}, clear=False):
            child_env = _zero_dep_child_env()
        self.assertEqual(child_env[R.parallel_shard._ENV_ON], "0",
                          "探針子行程必須無條件強制序列，不得繼承外層的平行請求")

    def test_child_env_forces_off_when_parent_env_unset(self) -> None:
        R = run_root_unittests
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(R.parallel_shard._ENV_ON, None)
            child_env = _zero_dep_child_env()
        self.assertEqual(child_env[R.parallel_shard._ENV_ON], "0",
                          "D1 之後「未設」會被判成 auto——這支測試釘住探針層不能被 auto 捲入")


def _run_zero_dep_probe(mode: str, blocked: list[str]) -> subprocess.CompletedProcess[str]:
    """同一組 (mode, blocked) 只真的跑一次。

    探針是**唯讀**的（子行程只讀樹、不寫回），故重用結果不會讓任一斷言失去鑑別力；
    而它每跑一次的代價是整套時間，兩支測試各跑一次是純粹的浪費。
    """
    return _zero_dep_probe_cached(mode, tuple(blocked))


def _blocked_prereqs() -> list[str]:
    return [imp for imp, _pip in run_root_unittests._THIRD_PARTY_PREREQS]


def _zero_dep_collect() -> dict:
    """零相依沙箱的**收集面**快照（`collect` 模式：只 discover、不執行任何測試）。

    與 `floor`／`main` 的差別是代價：那兩個會把整棵樹再跑一次，這個是秒級 ⇒
    「拿真沙箱當保鮮看守」對每一次全套執行都負擔得起。
    """
    proc = _run_zero_dep_probe("collect", _blocked_prereqs())
    if proc.returncode != 0:  # fail-loud：探針壞掉時不得讓依賴它的斷言靜默通過
        raise AssertionError(
            f"零相依 collect 探針 rc={proc.returncode}——依賴它的保鮮鎖失去取值面。\n"
            f"stderr 尾段：{proc.stderr[-1200:]}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


@unittest.skipIf(
    os.environ.get(_ZERO_DEP_PROBE_ENV) == "1",
    "本類別與 ZeroDepEnvironmentDiscriminationTest 同樣會 spawn 零相依探針；在探針**內部**"
    "再跑一次就會遞迴生出孫探針（DEF-101-803 實測：整套牆鐘 823s→3813s 且仍逾時）。"
    "此 skip 是**斷遞迴**，不是放棄覆蓋——外層那一次照跑，本組斷言全部在外層被驗證。",
)
class MinTestsMarginCriterionTest(unittest.TestCase):
    """🔴 DEF-200-170 的回歸鎖：`MIN_TESTS` 的重釘提醒改綁**零相依餘裕**這根軸。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈MinTestsMarginCriterionTest 四個方向〉。
    """

    @staticmethod
    def _live_suite_modules() -> dict[str, int]:
        return run_root_unittests.suite_modules(
            run_root_unittests.discover_suite(run_root_unittests._TESTS_DIR)
        )

    def test_the_criterion_speaks_before_the_environment_check_dies(self) -> None:
        """① 可達性：在環境判準失效的**前一支**，新判準必須已經開口、舊判準必須還沒。

        判準刻意寫成「叩真的那兩個函式」而不是在測試裡重算一次門檻公式——第二份公式
        就是下一次漂移（本 repo 對「鎖抄一份自己的判準」已有多次判例）。
        """
        min_tests = run_root_unittests.MIN_TESTS
        mods = self._live_suite_modules()
        loss = min_tests_margin.collapse_loss(mods)
        self.assertGreater(
            loss, 0,
            "本 repo 的零相依沙箱竟然一支模組都不塌 ⇒ 整個判準不適用，"
            "請先確認 _THIRD_PARTY_PREREQS 與 PREREQ_DEPENDENT_MODULES 是否已失實",
        )
        dead = min_tests_margin.discrimination_lost_count(min_tests, loss)
        self.assertIsNotNone(
            min_tests_margin.headroom_message(dead - 1, min_tests, mods),
            f"收集數 {dead - 1}（環境判準失效的前一支）時新判準還不說話 ⇒ "
            "換了公式但沒換到「先說話」這件事，DEF-200-170 沒被修掉",
        )
        self.assertIsNone(
            run_root_unittests.ratchet_drift_message(dead - 1, min_tests),
            f"舊比例 WARN 在收集數 {dead - 1} 就已經說話了？那 DEF-200-170 的前提"
            "（緩衝帶結構上到不了）已經改變，本鎖的對照組失效，請重新驗算再改判準",
        )
        for label, fraction in (
            ("WARN", min_tests_margin.HEADROOM_WARN_FRACTION),
            ("STALE", min_tests_margin.HEADROOM_STALE_FRACTION),
        ):
            with self.subTest(layer=label):
                self.assertLess(
                    min_tests_margin.first_speaking_count(min_tests, loss, fraction), dead,
                    f"{label} 層第一次說話的收集數不早於環境判準失效點 ⇒ 又是一個死判準",
                )

    def test_growth_into_the_warn_band_says_repin_not_environment(self) -> None:
        """② 「成長到該 WARN、但還沒到 FAIL」的情境：判準要說話，且說的是重釘。

        合成輸入（不動真樹）：一支宣告內的模組貢獻 201 支 ⇒ `collapse_loss` 為 200。
        """
        min_tests, mods = 1000, {"test_gha_action_versions": 201}
        self.assertEqual(min_tests_margin.collapse_loss(mods), 200)
        count = min_tests_margin.first_speaking_count(
            min_tests, 200, min_tests_margin.HEADROOM_WARN_FRACTION)
        msg = min_tests_margin.headroom_message(count, min_tests, mods)
        self.assertIsNotNone(msg, "成長進 WARN 帶卻一個字都沒說＝這一層又是死的")
        assert msg is not None
        self.assertIn("MIN_TESTS", msg)
        self.assertIn("重釘", msg)
        self.assertIn(
            str(count), msg,
            "訊息必須直接給出「該重釘成多少」，否則讀者還要自己算——"
            "而那正是五輪都沒有人動手的原因之一",
        )
        self.assertNotIn(
            "環境問題", msg,
            "新判準的歸因不得與環境判準混用同一句話：`report_floor_failure` 的"
            "「環境問題」是另一件事，兩邊講同一句就等於沒有修掉歸錯因",
        )
        self.assertIsNone(
            min_tests_margin.headroom_message(
                count, min_tests, mods, min_tests_margin.HEADROOM_STALE_FRACTION),
            "WARN 帶內紅線層就開口 ⇒ 緩衝區為空、退化成單一門檻"
            "（R57 round 1 ARCH-06 判過的那個形態，換一根軸也不准復發）",
        )
        self.assertIsNone(
            min_tests_margin.headroom_message(count - 1, min_tests, mods),
            "帶下緣之前一支就開口 ⇒ 常亮警告會退化成背景噪音，等於沒有",
        )

    def test_a_genuinely_incomplete_environment_stays_the_environment_checks_job(self) -> None:
        """③ 環境真的不完整時：新判準必須閉嘴，環境判準必須照樣說得出「環境問題」。

        沒有這一支，最可能的退化是「新判準把兩件事都攬過去講」——那不是修好歸錯因，
        是把錯歸因換一個方向再犯一次。
        """
        sandbox = {name: 1 for name in min_tests_margin.PREREQ_DEPENDENT_MODULES}
        sandbox["test_not_dependent_on_third_party"] = 900
        self.assertEqual(
            min_tests_margin.collapse_loss(sandbox), 0,
            "沙箱形狀（每支已塌成一支佔位測試）下 collapse loss 必須為 0＝判準不適用",
        )
        self.assertIsNone(
            min_tests_margin.headroom_message(5000, 1000, sandbox),
            "相依真的缺席時新判準竟然開口 ⇒ 它搶走了環境判準的歸因，製造第二個錯方向",
        )
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            run_root_unittests.report_floor_failure(
                Path("/fake/tests"), 900, 1000,
                [("test_gha_action_versions", "_FailedTest")], [("yaml", "pyyaml")],
            )
        out = buf.getvalue()
        self.assertIn("環境問題", out, "環境判準被新判準蓋掉了——那一面的覆蓋不得有淨損失")
        self.assertIn("pyyaml", out, "環境歸因仍必須給得出可直接複製的安裝指令")

    def test_the_runner_does_not_cry_repin_on_real_sandbox_counts(self) -> None:
        """③ 的真資料半格：餵**真沙箱量到的**逐模組收集數給提醒層，不得喊重釘。

        WHY 不看沙箱 `floor` 的 stdout（第一版就那樣寫、當場自查發現它今天**恆真**）：
        沙箱裡收集數低於下限 ⇒ `run_with_floor` 在 `report_floor_failure` 就 `return 1`，
        根本走不到提醒層 ⇒ 那是一道 vacuous 鎖。改餵真沙箱計數，判準就得自己撐住。
        `count` 刻意取遠高於下限的值，讓「不適用」是判準的決定而非數字不夠大。
        """
        sandbox_mods = _zero_dep_collect()["mods"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_root_unittests.warn_ratchet_drift(
                99999, run_root_unittests.MIN_TESTS, sandbox_mods)
        self.assertNotIn(
            "零相依沙箱的鑑別力餘裕", buf.getvalue(),
            "相依缺席的環境裡竟然喊重釘 ⇒ 新判準搶走了環境判準的歸因，"
            "那是把 DEF-200-170 的錯歸因換個方向再犯一次",
        )
        self.assertIn(
            "環境問題", _run_zero_dep_probe("floor", _blocked_prereqs()).stderr,
            "沙箱裡該說話的仍然是環境判準——它的覆蓋不得因為本輪新增判準而有淨損失",
        )

    def test_the_declared_collapsing_set_matches_the_real_sandbox(self) -> None:
        """④ 唯一釘選面的保鮮：宣告的「會塌模組集合」必須逐字等於真沙箱量到的那一組。

        這是本模組敢只釘集合、不釘支數的前提。落地當回合實測過反例：改用 top-level
        import 靜態掃描會漏掉 `test_ntfs_trailing_space_device_name`（**間接**拉進相依）
        ⇒ 猜測面不可信，只有真沙箱能當保鮮看守。
        """
        got = set(_zero_dep_collect()["placeholders"])
        want = set(min_tests_margin.PREREQ_DEPENDENT_MODULES)
        self.assertEqual(
            got, want,
            f"宣告集合與真沙箱不符（沙箱多出 {sorted(got - want)}／宣告多出 {sorted(want - got)}）"
            "⇒ collapse loss 算錯 ⇒ 餘裕與兩層門檻全部失真。"
            "修法：把 min_tests_margin.PREREQ_DEPENDENT_MODULES 改成沙箱實測的那一組",
        )

    def test_the_loss_arithmetic_matches_the_real_sandbox(self) -> None:
        """④ 的第二半：`collapse_loss` 的「減掉模組數」修正項必須對得上真沙箱。

        刻意逐模組比對而**不**比兩邊總數：總數是跨行程的兩次量測，並行包在那幾秒內動樹
        就會讓真鎖變 flaky（DEF-101-886 判例）。而本判準的內容就是「集合 ＋ 每支塌成 1」，
        逐模組比對正好等價。
        """
        sandbox_mods = _zero_dep_collect()["mods"]
        live = self._live_suite_modules()
        for name in sorted(min_tests_margin.PREREQ_DEPENDENT_MODULES):
            with self.subTest(module=name):
                self.assertEqual(
                    sandbox_mods.get(name), 1,
                    "沙箱裡必須恰好塌成一支佔位測試——不是 1 就代表 collapse_loss 的"
                    "「−模組數」修正項用錯了模型",
                )
                self.assertGreater(
                    live.get(name, 0), 1,
                    "相依齊備時它必須貢獻不只一支，否則把它列進宣告集合毫無意義",
                )

    def test_the_criterion_is_wired_into_the_runner_not_just_unit_tested(self) -> None:
        """接線鎖：單元測了卻沒接線是本 repo 最常見的假綠形狀（比照本檔既有數處手法）。

        兩條缺一不可：漏傳逐模組收集數 ⇒ `collapse_loss` 恆為 0 ⇒ 新判準永遠閉嘴而
        本檔其餘合成斷言照樣全綠；接了參數卻仍只叩舊比例判準 ⇒ 換了模組沒換判準。
        """
        self.assertIn(
            "warn_ratchet_drift(count, min_tests, suite_modules(suite))",
            inspect.getsource(run_root_unittests.run_with_floor),
            "runner 沒把逐模組收集數交給判準 ⇒ collapse loss 恆為 0 ⇒ 新判準永遠不說話",
        )
        self.assertIn(
            "min_tests_margin.headroom_message",
            inspect.getsource(run_root_unittests.warn_ratchet_drift),
            "第一層仍是舊比例判準 ⇒ 模組建好了但沒有人叩它，等於沒有",
        )

    def test_the_ratio_layers_remain_as_the_outer_fallback(self) -> None:
        """不適用的樹（loss 為 0：合成樹、探針內部）必須由外層後備接手，不得整個啞掉。

        這是「把第一層換掉」與「把提醒整個拆掉」的分界線——沒有這一支，
        用一個恆回 None 的新判準取代舊層也會全綠。
        """
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            msg = run_root_unittests.warn_ratchet_drift(1000, 100, {})
        self.assertIsNotNone(msg, "loss 為 0 時後備層也不說話 ⇒ 這棵樹上完全沒有提醒了")
        self.assertIn("MIN_TESTS", msg or "")
        self.assertIn("1000", buf.getvalue(), "後備層同樣必須印出該重釘成多少")

    def test_the_new_layer_takes_precedence_when_both_apply(self) -> None:
        """兩層都適用時，說話的必須是新判準——否則讀者拿到的仍是量錯分母的那個數字。"""
        mods = {"test_gha_action_versions": 201}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_root_unittests.warn_ratchet_drift(5000, 1000, mods)
        out = buf.getvalue()
        self.assertIn("零相依", out, "印出來的不是零相依餘裕那一層")
        self.assertNotIn(
            "下限的鑑別力只剩", out,
            "印出來的是舊比例判準的訊息 ⇒ 優先序寫反，新判準被後備蓋掉",
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


@unittest.skipIf(
    os.environ.get(_ZERO_DEP_PROBE_ENV) == "1",
    "本類別自己會 spawn 一個把整棵樹再跑一次的探針；若在探針**內部**也跑本類別，"
    "就會遞迴生出孫探針、曾孫探針，只被逾時值截斷（DEF-101-803 實測：整套牆鐘 823s→3813s "
    "且仍 TimeoutExpired）。此 skip 是**斷遞迴**，不是放棄覆蓋——外層那一次照跑，"
    "本組的斷言全部在外層被驗證。",
)
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
        # DEF-101-803 方向 B：守門真的失守（數量下限竟然通過、整棵樹被跑起來）時，
        # 要變成這一條具名 fail，而不是難以歸因的 TimeoutExpired error。
        self.assertNotIn("unittest 數量下限釘選通過", proc.stdout,
                         "floor 探針在零相依環境下竟通過數量下限 ⇒ 整棵真實樹被跑起來了")

    def test_zero_dep_message_says_environment_not_disappearance(self) -> None:
        """本輪缺陷的**直接**回歸鎖：在 CI 的等價環境下，閘門印的必須是「環境不完整」
        而不是「測試疑似大規模靜默消失」。"""
        blocked = [imp for imp, _ in run_root_unittests._THIRD_PARTY_PREREQS]
        proc = _run_zero_dep_probe("floor", blocked)
        self.assertIn("環境問題", proc.stderr)
        self.assertNotIn("真的大規模消失", proc.stderr)
        self.assertNotIn("unittest 數量下限釘選通過", proc.stdout,
                         "同上（DEF-101-803）：守門失守須轉為具名 fail")
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


class ZeroDepProbeFlagIsNotAFailOpenTest(unittest.TestCase):
    """上一組的自我 skip 是 **fail-open**，本組是它唯一的看守者。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈ZeroDepProbeFlagIsNotAFailOpenTest WHY（fail-open 看守者）〉。
    """

    def test_probe_flag_implies_dependencies_really_blocked(self) -> None:
        """旗標與「相依真的被擋掉」必須同真同假——旗標本身不足以自證身在探針內。

        這是「注入該變數即紅」的那條斷言：正常環境（相依齊備）只要旗標為 1，左右不等即紅。
        判準刻意取旗標**之外的獨立訊號**（`find_spec` 找不找得到宣告相依）——只看旗標的話，
        「真的在探針內」與「旗標漏進外層」在觀測上完全一樣，而那正是這個缺陷藏身的地方。
        """
        flag_set = os.environ.get(_ZERO_DEP_PROBE_ENV) == "1"
        missing = run_root_unittests.missing_third_party_prereqs()
        self.assertEqual(
            flag_set, bool(missing),
            f"{_ZERO_DEP_PROBE_ENV}={os.environ.get(_ZERO_DEP_PROBE_ENV)!r} 與「宣告相依是否"
            f"真的取不到」不一致（缺漏={[imp for imp, _ in missing]}）。\n"
            f"  · 旗標為 1 但相依都在 ⇒ 該變數**漏進了外層環境**："
            f"{ZeroDepEnvironmentDiscriminationTest.__name__} 三支鑑別力鎖會全部自我 skip，"
            f"而 unittest 把 skipped 計入 `Ran N tests` ⇒ MIN_TESTS 看不出來、閘門照綠。"
            f"處置：把該變數從環境中移除（它只該由 _zero_dep_probe_cached() 傳給子行程）。\n"
            f"  · 旗標未設但相依取不到 ⇒ 環境不完整（非本組職責，main() 會 fail-fast 判紅）。",
        )

    def test_group_is_skipped_exactly_when_the_probe_flag_is_set(self) -> None:
        """釘住 skip 的**接線**：條件必須恰好是那個旗標，不寬不窄。

        `@unittest.skipIf` 在 class 建立時就把判定結果寫成 `__unittest_skip__`，故此處讀到的
        是「本次執行到底 skip 了沒」這個既成事實，不是重算一次條件。上一支保證「旗標為 1 時
        真的在探針內」，本支保證「不在探針內時那三支鎖真的被執行」——把條件改寬（例如改成
        任何非空值即 skip、或退化成無條件 `@unittest.skip`）會讓本支當場紅。
        """
        in_probe = os.environ.get(_ZERO_DEP_PROBE_ENV) == "1"
        skipped = bool(getattr(ZeroDepEnvironmentDiscriminationTest, "__unittest_skip__", False))
        self.assertEqual(
            skipped, in_probe,
            f"{ZeroDepEnvironmentDiscriminationTest.__name__} 的 skip 狀態（{skipped}）與"
            f"「是否在探針子行程內」（{in_probe}）不符。skip 只准為了斷遞迴而發生；"
            f"在正常環境被 skip ＝ 那三支零相依鑑別力鎖沒跑，而下限守門對此失明。",
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

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈CiPrereqInstallLockTest WHY 與判準邊界〉。
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

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_every_ci_job_running_the_runner_installs_all_external_tools〉。
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


# ── 載具一致性（R82／複審 SA B-1）─────────────────────────────────────────────
#: 兩個載具子行程的逾時上限。刻意與本檔零相依探針同值：`DEF-101-803` 的事故正是
#: 「逾時被放寬」把 823s 放大成 3813s，故這個數字只准往下、不准再加。
_CARRIER_TIMEOUT_S = 300


def _is_mock_patch_call(func: ast.expr) -> bool:
    """被呼叫端是不是 `mock.patch` 家族（`patch`／`patch.object`／`patch.dict`）。"""
    parts: list[str] = []
    node: ast.AST = func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    parts.reverse()
    return len(parts) >= 2 and parts[0] == "mock" and parts[1] == "patch"


def classes_that_monkeypatch(source: str) -> list[str]:
    """純函式：原始碼裡會 monkeypatch 模組屬性的**頂層測試類別**名（排序、去重）。

    這是「這一類鎖」的**機械定義**，不是一份手寫清單——日後任何人新寫一個會 patch
    模組屬性的類別，就自動落進載具一致性的射程，不必有人記得把它加進某張表。
    """
    out: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and any(
            isinstance(sub, ast.Call) and _is_mock_patch_call(sub.func)
            for sub in ast.walk(node)
        ):
            out.add(node.name)
    return sorted(out)


def carrier_parity_problems(label: str, rc_unittest: int, rc_pytest: int) -> list[str]:
    """純函式：同一組測試在兩個載具下的**判決**不一致即紅（回空＝一致）。

    判的是判決（rc 是否為 0）而不是 rc 的字面值：`1` 與 `2` 都是「紅」，那不是分歧；
    `0` 對上 `5`（pytest 的「一支都沒收到」）則是分歧，而且是最該被抓的那一種。
    """
    if (rc_unittest != 0) == (rc_pytest != 0):
        return []
    return [
        f"[載具分歧] {label}：unittest rc={rc_unittest}、pytest rc={rc_pytest}"
        "——同一份原始碼、同一棵樹，兩個載具給出相反的判決。"
        "🔴 這比單純的紅更危險：push 閘門走的是 unittest，所以**只有 unittest 那一側**"
        "的判決會被人看見；另一側是紅是綠沒有人知道。已知成因（`DEF-101-996`）＝測試把"
        "行程全域的東西 monkeypatch 掉（例：`mock.patch.object(<任何模組>.os, \"name\", …)`"
        "改的是 stdlib 那一個 `os` 模組物件），而兩個載具在那段期間跑的程式碼並不相同"
        "（pytest 的 `AssertionRewritingHook` 會對每一支新 import 的模組呼叫 `Path()`）。"
        "修法是把注入接縫收回**自己模組層的名字**，不要動行程全域。"
    ]


class CarrierVerdictParityTest(unittest.TestCase):
    """🔴 同一組測試在 `unittest` 與 `pytest` 兩個載具下的判決必須一致（R82／SA B-1）。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈CarrierVerdictParityTest WHY 與射程〉。
    """

    _SELF = "CarrierVerdictParityTest"

    def _carrier_rc(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        """跑一個載具子行程，回 `(rc, 合併輸出)`。"""
        proc = subprocess.run(
            [sys.executable, *argv], cwd=str(cwd),
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_CARRIER_TIMEOUT_S, check=False,
        )
        return proc.returncode, proc.stdout + proc.stderr

    def _both_carriers(self, tests_dir: Path, module: str,
                       classes: list[str]) -> tuple[int, int, str]:
        """同一組類別各跑一次 unittest 與 pytest，回 `(rc_u, rc_p, 診斷文字)`。"""
        rc_u, out_u = self._carrier_rc(
            ["-m", "unittest", *(f"{module}.{c}" for c in classes)], tests_dir)
        rc_p, out_p = self._carrier_rc(
            ["-m", "pytest", "-q", "-p", "no:cacheprovider",
             *(f"{module}.py::{c}" for c in classes)], tests_dir)
        return rc_u, rc_p, f"--- unittest ---\n{out_u[-2000:]}\n--- pytest ---\n{out_p[-2000:]}"

    def test_the_parity_judgment_is_red_only_on_divergence(self) -> None:
        """判準本體的紅綠（純函式、構造輸入）：只有「一邊綠一邊紅」才算分歧。"""
        self.assertEqual(carrier_parity_problems("X", 0, 0), [])
        self.assertEqual(carrier_parity_problems("X", 1, 1), [],
                         "兩邊都紅是同一個判決，不是載具分歧——判紅會製造假紅")
        self.assertEqual(carrier_parity_problems("X", 1, 2), [],
                         "rc 字面值不同但判決相同 ⇒ 不是分歧")
        for pair in ((0, 1), (1, 0), (0, 5)):
            with self.subTest(pair=pair):
                problems = carrier_parity_problems("X", *pair)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(str(pair[0]), problems[0])
                self.assertIn(str(pair[1]), problems[0])

    def test_the_scope_extractor_discriminates(self) -> None:
        """射程抽取器必須真的在分辨，而不是「全抓」或「全不抓」（否則鎖是空轉的）。"""
        source = textwrap.dedent(
            """\
            class PatchesAModuleAttr(unittest.TestCase):
                def test_a(self):
                    with mock.patch.object(mod, "flag", False):
                        pass


            class PatchesADict(unittest.TestCase):
                def test_b(self):
                    with mock.patch.dict(mod.TABLE, {}):
                        pass


            class TouchesNothing(unittest.TestCase):
                def test_c(self):
                    self.assertTrue(True)
            """
        )
        self.assertEqual(classes_that_monkeypatch(source),
                         ["PatchesADict", "PatchesAModuleAttr"])

    def test_the_live_scope_is_not_empty_and_excludes_this_class(self) -> None:
        """對本檔實跑抽取器：射程非空（空＝下面那道恆真），且**不含本類**。

        排除本類不是潔癖：本類會 spawn 子行程去跑射程內的每一個類別，把自己算進去
        就是無限遞迴。它沒有用 `mock.patch`，所以今天本來就不在射程內——這條斷言
        是把「今天剛好不在」升級成「不准進來」。
        """
        live = classes_that_monkeypatch(Path(__file__).read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(live), 2, f"射程只有 {live}——抽取器疑似壞了")
        self.assertNotIn(self._SELF, live,
                         "本類進入自己的射程 ⇒ 子行程會再 spawn 子行程（無限遞迴）")
        self.assertIn("UntaggedWindowsLikeSkipsTest", live,
                      "本鎖的立案標的不在射程內 ⇒ 它守不到讓它誕生的那個缺陷")

    def _synth(self, prefix: str, module: str, body: str) -> tuple[int, int, str]:
        """把一支合成測試模組落到暫存樹，兩個載具各跑一次。"""
        base = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(lambda: shutil.rmtree(base, ignore_errors=True))
        (base / f"{module}.py").write_text(
            textwrap.dedent(body), encoding="utf-8", newline="\n")
        return self._both_carriers(base, module, ["Synth"])

    def test_a_synthesized_carrier_divergence_is_caught(self) -> None:
        """🔴 合成注入（**紅**這一半）：判決取決於「誰在跑」的模組必須被抓出來。

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_a_synthesized_carrier_divergence_is_caught 注入體選型〉。
        """
        rc_u, rc_p, diag = self._synth(
            "carrier_parity_red_", "test_carrier_injected",
            """\
            import sys
            import unittest


            class Synth(unittest.TestCase):
                def test_the_verdict_depends_on_who_is_running_it(self):
                    # 合成分歧：判決取決於載具而不是被判的東西——那正是載具分歧的定義。
                    self.assertNotIn("pytest", sys.modules)
            """,
        )
        self.assertEqual(
            len(carrier_parity_problems("injected", rc_u, rc_p)), 1,
            f"合成注入沒有製造出載具分歧（rc_u={rc_u} rc_p={rc_p}）"
            f"——本鎖已失去鑑別力：\n{diag}",
        )

    def test_a_synthesized_clean_module_agrees_and_is_green(self) -> None:
        """合成注入（**綠**這一半）：同一份形狀、判決不依賴載具 ⇒ 判準必須回空。

        沒有這一條，上面那支只證明了「本判準會說話」，沒證明「它不是恆紅」。
        """
        rc_u, rc_p, diag = self._synth(
            "carrier_parity_green_", "test_carrier_clean",
            """\
            import sys
            import unittest

            ON_WINDOWS = True


            class Synth(unittest.TestCase):
                def test_a_module_local_seam_is_carrier_neutral(self):
                    me = sys.modules[__name__]
                    from unittest import mock
                    with mock.patch.object(me, "ON_WINDOWS", False):
                        self.assertFalse(me.ON_WINDOWS)
                    self.assertTrue(me.ON_WINDOWS)
            """,
        )
        self.assertEqual(rc_u, 0, f"對照組在 unittest 下就不是綠的：\n{diag}")
        self.assertEqual(rc_p, 0, f"對照組在 pytest 下就不是綠的：\n{diag}")
        self.assertEqual(carrier_parity_problems("clean", rc_u, rc_p), [])

    def test_the_live_monkeypatching_locks_agree_across_carriers(self) -> None:
        """活體：本檔所有會 monkeypatch 的類別，兩個載具的判決必須一致。

        刻意判「一致」而不是「都綠」：別的並行包把樹弄紅時兩邊會一起紅，那不是本鎖
        要說的事（判成紅就是把別人的紅記到本鎖頭上，這種鎖活不過一輪）。
        """
        tests_dir = Path(__file__).resolve().parent
        module = Path(__file__).stem
        targets = [c for c in classes_that_monkeypatch(
            Path(__file__).read_text(encoding="utf-8")) if c != self._SELF]
        rc_u, rc_p, diag = self._both_carriers(tests_dir, module, targets)
        self.assertEqual(
            carrier_parity_problems("／".join(targets), rc_u, rc_p), [],
            f"{diag}",
        )


class ParallelShardMergeSmokeTest(unittest.TestCase):
    """DEF-200-274 AC8：JSON 彙總協定的純函式驗證——**不**真的 spawn subprocess

    （那會測到 Popen 本身而非彙總邏輯）。直接餵兩份手造 shard payload 給
    `merge_results`，斷言 testsRun 加總正確、fixture 筆 isinstance 為 False、
    非 fixture 筆為 True 且 id 相符。恆跑、不用 skip/skipUnless。
    """

    def test_two_shards_merge_counts_and_fixture_flag_correctly(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        case = _Case("test_ok")
        known = {case.id(): case}
        shard_a = {
            "testsRun": 3,
            "skipped": [[case.id(), "只在 CI 跑", False]],
            "errors": [],
            "failures": [],
            "unexpectedSuccesses": [],
        }
        shard_b = {
            "testsRun": 2,
            "skipped": [],
            "errors": [["setUpClass (mod.Cls)", "boom", True]],
            "failures": [],
            "unexpectedSuccesses": [],
        }
        merged = parallel_shard.merge_results([shard_a, shard_b], known)

        self.assertEqual(merged.testsRun, 5, "兩個 shard 的 testsRun 未正確加總")
        self.assertEqual(len(merged.skipped), 1)
        skipped_test, skipped_reason = merged.skipped[0]
        self.assertIsInstance(skipped_test, unittest.TestCase)
        self.assertEqual(skipped_test.id(), case.id())
        self.assertEqual(skipped_reason, "只在 CI 跑")

        self.assertEqual(len(merged.errors), 1)
        error_test, error_detail = merged.errors[0]
        self.assertNotIsInstance(error_test, unittest.TestCase)
        self.assertEqual(str(error_test), "setUpClass (mod.Cls)")
        self.assertEqual(error_detail, "boom")
        self.assertFalse(merged.wasSuccessful(), "有 1 筆 error ⇒ 不應判為成功")


def _fake_shard_procs(crash_shard: list[str], crash_stderr: str, ok_payload: str):
    """建一個 `subprocess.Popen` 替身：命中 `crash_shard` 的呼叫回崩潰態
    （rc=1、空 stdout），其餘一律回 `ok_payload` 這份合法 JSON。"""

    class _CrashProc:
        returncode = 1

        def communicate(self):
            return "", crash_stderr

    class _OkProc:
        returncode = 0

        def communicate(self):
            return ok_payload + "\n", ""

    def fake_popen(argv, **_kwargs):
        return _CrashProc() if argv[3:] == crash_shard else _OkProc()

    return fake_popen


class ParallelShardCrashDoesNotRaiseTest(unittest.TestCase):
    """DEF-200-274 收尾複審發現：shard 崩潰時 `run_parallel()` 曾 `raise
    SystemExit(1)`，直接穿透 `sentinel_lifecycle.leak_fence()` 的 `rc = run()`
    這一行（無 try/except），讓收尾快照／洩漏比對整段沒有執行。修法＝崩潰改記
    一筆 `errors` 條目正常 return，`wasSuccessful()` 因此為 False，呼叫方讀到
    的 rc 依然非零，但不再犧牲 `leak_fence()` 的收尾動作。
    """

    def test_shard_crash_returns_failed_result_instead_of_raising(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        ok_payload = json.dumps({
            "testsRun": 1, "skipped": [], "errors": [], "failures": [],
            "unexpectedSuccesses": [],
        })
        stderr = "boom: shard interpreter crashed"
        fake_popen = _fake_shard_procs(["mod.crash"], stderr, ok_payload)
        module_counts = {"mod.crash": 1, "tests.mod_ok": 1}

        with mock.patch.object(parallel_shard, "worker_count", return_value=2), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            try:
                result = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, module_counts,
                )
            except SystemExit as exc:  # 這正是本測試要鎖住的回歸
                self.fail(f"run_parallel() 仍以 SystemExit 中斷呼叫鏈：{exc}")

        self.assertFalse(
            result.wasSuccessful(),
            "崩潰的 shard 沒有讓彙總結果判為失敗——rc 會被靜默蓋成綠燈",
        )
        self.assertEqual(len(result.errors), 1)
        crashed_test, reason = result.errors[0]
        self.assertNotIsInstance(crashed_test, unittest.TestCase)
        self.assertIn("mod.crash", str(crashed_test))
        self.assertIn(stderr, reason, "崩潰診斷（stderr）沒有被帶進彙總結果")


class ParallelShardCrashLeakFenceIntegrationTest(unittest.TestCase):
    """端到端：把一個會 shard 崩潰的 `run_parallel()` 呼叫真的包進
    `sentinel_lifecycle.leak_fence()`，斷言收尾快照／洩漏比對確實跑完，不是被
    `SystemExit` 中斷。假排程後端只認 `list_jobs()` 呼叫次數：兩次（收尾前後
    各一次）即證明 `rc = run()` 那一行沒有被例外打斷。
    """

    def test_leak_fence_completes_its_teardown_when_a_shard_crashes(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        sentinel_lifecycle = run_root_unittests.sentinel_lifecycle

        class _FakeBackend:
            name = "fake-carrier"

            def __init__(self) -> None:
                self.calls = 0

            def list_jobs(self, _prefix: str) -> list[str]:
                self.calls += 1
                return []

            def evidence_hint(self) -> str:
                return "（假後端：本測試不對真載具取證）"

        backend = _FakeBackend()

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        ok_payload = json.dumps({
            "testsRun": 1, "skipped": [], "errors": [], "failures": [],
            "unexpectedSuccesses": [],
        })
        fake_popen = _fake_shard_procs(["mod.crash"], "boom", ok_payload)
        captured: list = []

        def _run() -> int:
            result = parallel_shard.run_parallel(
                suite, Path(__file__).resolve().parent,
                {"mod.crash": 1, "tests.mod_ok": 1},
            )
            captured.append(result)
            return 0 if result.wasSuccessful() else 1

        tmp = Path(tempfile.mkdtemp(prefix="leak-fence-shard-crash-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        trace_env = sentinel_lifecycle.endurance_env.TRACE_DIR_ENV

        with mock.patch.object(parallel_shard, "worker_count", return_value=2), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen), \
                mock.patch.object(sentinel_lifecycle.schedule_backend, "select",
                                  return_value=backend), \
                mock.patch.object(tempfile, "gettempdir", return_value=str(tmp)), \
                mock.patch.dict(os.environ, {trace_env: str(tmp)}):
            try:
                rc = sentinel_lifecycle.leak_fence(_run)
            except SystemExit as exc:  # 這正是本測試要鎖住的回歸
                self.fail(f"leak_fence() 的 rc = run() 被 SystemExit 打斷：{exc}")

        self.assertEqual(len(captured), 1, "run() 沒有被 leak_fence 真的呼叫到")
        self.assertFalse(captured[0].wasSuccessful())
        self.assertEqual(rc, 1, "run() 判失敗卻沒有傳遞到 leak_fence() 的 rc")
        self.assertEqual(
            backend.calls, 2,
            "leak_fence 前後兩次真排程器快照沒有都執行——"
            "代表 rc = run() 那行被例外打斷，收尾沒跑完",
        )
        trace = tmp / sentinel_lifecycle.LEAK_FENCE_LOG_NAME
        self.assertTrue(trace.is_file(), "leak_fence 沒有落痕跡——收尾沒跑完")


class ParallelShardStderrBackpressureRegressionTest(unittest.TestCase):
    """DEF-200-274 第三輪複審 Problem 1：stderr backpressure 真實子行程回歸測試。

    刻意**不** mock `subprocess.Popen`（既有 `ParallelShard*` 測試全 mock，從未真的
    碰到 `_worker_main()` 的 fd 重導向與真實 OS pipe 行為）：SLOW 模組只 sleep，
    LOUD 模組同時對 stderr 寫超過 OS pipe buffer 的內容並自量耗時；修復前序列
    `Popen()` 會讓 LOUD 被 SLOW 的 `communicate()` 卡住，修復後動態工作竊取應使
    兩者耗時互不相干。事故經過與逐輪修復細節史料見證據檔〈第七輪 史料搬遷
    （Dev-Trim8）〉。
    """

    _SLOW_MODULE = f"_zzz_backpressure_repro_a_slow_{os.getpid()}"
    _LOUD_MODULE = f"_zzz_backpressure_repro_z_loud_{os.getpid()}"
    _SLEEP_SECONDS = 2.5
    _PAYLOAD_BYTES = 5_000_000

    def setUp(self) -> None:
        self._tests_dir = Path(__file__).resolve().parent
        fd, result_path = tempfile.mkstemp(prefix="backpressure_elapsed_", suffix=".txt")
        os.close(fd)
        self._result_path = Path(result_path)
        self._slow_path = self._tests_dir / f"{self._SLOW_MODULE}.py"
        self._loud_path = self._tests_dir / f"{self._LOUD_MODULE}.py"
        self._slow_path.write_text(
            "import time\n"
            "import unittest\n\n\n"
            "class SlowTest(unittest.TestCase):\n"
            f"    def test_sleep(self):\n        time.sleep({self._SLEEP_SECONDS})\n",
            encoding="utf-8",
        )
        self._loud_path.write_text(
            "import sys\n"
            "import time\n"
            "import unittest\n"
            "from pathlib import Path\n\n\n"
            f"_RESULT = Path({str(self._result_path)!r})\n\n\n"
            "class LoudTest(unittest.TestCase):\n"
            "    def test_write_big_stderr(self):\n"
            "        start = time.monotonic()\n"
            f"        sys.stderr.write('X' * {self._PAYLOAD_BYTES})\n"
            "        sys.stderr.flush()\n"
            "        _RESULT.write_text(str(time.monotonic() - start), encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.addCleanup(self._slow_path.unlink, missing_ok=True)
        self.addCleanup(self._loud_path.unlink, missing_ok=True)
        self.addCleanup(self._result_path.unlink, missing_ok=True)

    def test_loud_shard_stderr_write_does_not_block_on_slow_shard_sleep(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        module_counts = {self._SLOW_MODULE: 1, self._LOUD_MODULE: 1}
        suite = unittest.TestSuite()

        with mock.patch.object(parallel_shard, "worker_count", return_value=2):
            merged = parallel_shard.run_parallel(suite, self._tests_dir, module_counts)

        self.assertTrue(
            merged.wasSuccessful(),
            f"合成 shard 應該全部通過：errors={merged.errors} failures={merged.failures}",
        )
        self.assertEqual(merged.testsRun, 2)
        elapsed = float(self._result_path.read_text(encoding="utf-8"))
        self.assertLess(
            elapsed, self._SLEEP_SECONDS / 2,
            f"LOUD shard 的 stderr write() 耗時 {elapsed:.3f}s 過於接近 SLOW shard 的"
            f" sleep（{self._SLEEP_SECONDS}s）——stderr backpressure 回歸復發",
        )


class LoadBalancingRegressionTest(unittest.TestCase):
    """DEF-200-274 第四輪：證明動態工作竊取真的達成負載平衡，不靠測試方法數這個
    權重估計準不準。

    形狀刻意對舊版 `weighted_shards()`（已刪除；依方法數貪婪裝箱）不利：TRIVIAL
    （10 支瞬間通過的方法）＋ SLOW_A／SLOW_B（各 1 支 `sleep()`）。實際以
    `worker_count=3`（＝模組數）跑，讓三模組啟動瞬間各自被一條 thread 認領、
    全程零佇列競爭；斷言總耗時遠低於 `2 × _SLEEP_SECONDS`，`worker_count` 改回 1
    重跑則因排隊而逼近該值、已手動驗證過。取捨動機、`worker_count=2` 手算對照組
    與兩輪對抗式複審 finding 的因果敘事訂正史料見證據檔〈第七輪 史料搬遷
    （Dev-Trim8）〉。
    """

    _TRIVIAL_MODULE = f"_zzz_loadbalance_repro_trivial_{os.getpid()}"
    _SLOW_MODULE_A = f"_zzz_loadbalance_repro_slow_a_{os.getpid()}"
    _SLOW_MODULE_B = f"_zzz_loadbalance_repro_slow_b_{os.getpid()}"
    _SLEEP_SECONDS = 2.5

    def setUp(self) -> None:
        self._tests_dir = Path(__file__).resolve().parent
        self._paths: list[Path] = []

        trivial_path = self._tests_dir / f"{self._TRIVIAL_MODULE}.py"
        methods = "\n\n".join(f"    def test_{i}(self):\n        pass" for i in range(10))
        trivial_path.write_text(
            f"import unittest\n\n\nclass TrivialTest(unittest.TestCase):\n{methods}\n",
            encoding="utf-8",
        )
        self._paths.append(trivial_path)

        for name in (self._SLOW_MODULE_A, self._SLOW_MODULE_B):
            slow_path = self._tests_dir / f"{name}.py"
            slow_path.write_text(
                "import time\n"
                "import unittest\n\n\n"
                "class SlowTest(unittest.TestCase):\n"
                f"    def test_sleep(self):\n        time.sleep({self._SLEEP_SECONDS})\n",
                encoding="utf-8",
            )
            self._paths.append(slow_path)

        for p in self._paths:
            self.addCleanup(p.unlink, missing_ok=True)

    def test_two_slow_modules_run_concurrently_not_sequentially(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        module_counts = {
            self._TRIVIAL_MODULE: 10,
            self._SLOW_MODULE_A: 1,
            self._SLOW_MODULE_B: 1,
        }
        suite = unittest.TestSuite()

        # worker_count=3（＝模組數）：3 個模組在啟動瞬間各自被 1 條 thread 一次
        # 認領到位，全程零佇列競爭，避免「TRIVIAL 完成後回頭偷認領第二個 SLOW」
        # 這種會疊加兩次 Popen 啟動延遲的複合效應（見上方 docstring 的 Architect
        # finding 段落）。
        with mock.patch.object(parallel_shard, "worker_count", return_value=3):
            start = time.monotonic()
            merged = parallel_shard.run_parallel(suite, self._tests_dir, module_counts)
            elapsed = time.monotonic() - start

        self.assertTrue(
            merged.wasSuccessful(),
            f"合成模組應該全部通過：errors={merged.errors} failures={merged.failures}",
        )
        self.assertEqual(merged.testsRun, 12)
        self.assertLess(
            elapsed, self._SLEEP_SECONDS * 1.6,
            f"總耗時 {elapsed:.3f}s 過於接近兩個慢模組序列相加"
            f"（{self._SLEEP_SECONDS * 2}s）——動態負載平衡疑似失效，"
            "兩個慢模組被綁進同一條 thread 序列執行",
        )


class ParallelShardMergeResultsMissingKeyStillRaisesTest(unittest.TestCase):
    """DEF-200-274 第三輪複審 Problem 2 基準：`merge_results()` 本身維持嚴格、不做
    `.get()` 防護——防護移到呼叫端 `run_parallel()`（見下一支測試）。本測試釘住這個
    現況，證明修復前後 `merge_results()` 對缺鍵 payload 的行為沒有改變：改的是呼叫端
    有沒有把這個例外接住，不是把它吞掉。
    """

    def test_merge_results_raises_keyerror_on_missing_testsrun(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        with self.assertRaises(KeyError):
            parallel_shard.merge_results(
                [{"skipped": [], "errors": [], "failures": [], "unexpectedSuccesses": []}], {},
            )


class ParallelShardRunParallelExceptionSafetyTest(unittest.TestCase):
    """DEF-200-274 第三輪複審 Problem 2：`run_parallel()` 對 Popen／communicate／
    `merge_results()` 整段缺 try/except；`merge_results()` 對缺鍵 payload 拋出的
    `KeyError` 並非 `SystemExit`，一樣會穿透 `sentinel_lifecycle.leak_fence()` 的
    `rc = run()`（該行無 try/except），讓收尾快照／洩漏比對整段不執行——與已修復的
    `raise SystemExit` 繞過屬同一失效模式，只是觸發條件換成例外類型。修復後任何例外
    都轉成一筆 `errors` 條目、正常 return。
    """

    def test_a_payload_missing_required_keys_does_not_raise_out_of_run_parallel(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        # 故意缺 "testsRun" 鍵——merge_results() 對它會 KeyError。
        bad_payload = json.dumps(
            {"skipped": [], "errors": [], "failures": [], "unexpectedSuccesses": []}
        )

        class _OkProc:
            returncode = 0

            def communicate(self):
                return bad_payload + "\n", ""

        def fake_popen(argv, **_kwargs):
            return _OkProc()

        with mock.patch.object(parallel_shard, "worker_count", return_value=1), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            try:
                result = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, {"mod.bad": 1},
                )
            except KeyError as exc:
                self.fail(f"run_parallel() 讓 merge_results() 的 KeyError 穿透，未被攔截：{exc}")

        self.assertFalse(result.wasSuccessful(), "缺鍵 payload 應被記成失敗而非靜默通過")
        self.assertEqual(len(result.errors), 1)
        _, reason = result.errors[0]
        self.assertIn("KeyError", reason)


class ParallelShardMergeExceptionLeakFenceIntegrationTest(unittest.TestCase):
    """端到端：`merge_results()` 因缺鍵 payload 拋出 `KeyError` 的情境，真的包進
    `sentinel_lifecycle.leak_fence()`，斷言收尾快照／洩漏比對確實跑完——與既有的
    `ParallelShardCrashLeakFenceIntegrationTest`（shard crash 情境）成對，涵蓋
    Problem 2 指出的「例外而非 SystemExit」這條穿透路徑。
    """

    def test_leak_fence_completes_its_teardown_when_merge_results_raises(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        sentinel_lifecycle = run_root_unittests.sentinel_lifecycle

        class _FakeBackend:
            name = "fake-carrier"

            def __init__(self) -> None:
                self.calls = 0

            def list_jobs(self, _prefix: str) -> list[str]:
                self.calls += 1
                return []

            def evidence_hint(self) -> str:
                return "（假後端：本測試不對真載具取證）"

        backend = _FakeBackend()

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        bad_payload = json.dumps(
            {"skipped": [], "errors": [], "failures": [], "unexpectedSuccesses": []}
        )

        class _OkProc:
            returncode = 0

            def communicate(self):
                return bad_payload + "\n", ""

        def fake_popen(argv, **_kwargs):
            return _OkProc()

        captured: list = []

        def _run() -> int:
            result = parallel_shard.run_parallel(
                suite, Path(__file__).resolve().parent, {"mod.bad": 1},
            )
            captured.append(result)
            return 0 if result.wasSuccessful() else 1

        tmp = Path(tempfile.mkdtemp(prefix="leak-fence-merge-exc-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        trace_env = sentinel_lifecycle.endurance_env.TRACE_DIR_ENV

        with mock.patch.object(parallel_shard, "worker_count", return_value=1), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen), \
                mock.patch.object(sentinel_lifecycle.schedule_backend, "select",
                                  return_value=backend), \
                mock.patch.object(tempfile, "gettempdir", return_value=str(tmp)), \
                mock.patch.dict(os.environ, {trace_env: str(tmp)}):
            try:
                rc = sentinel_lifecycle.leak_fence(_run)
            except KeyError as exc:
                self.fail(f"leak_fence() 的 rc = run() 被 KeyError 打斷：{exc}")

        self.assertEqual(len(captured), 1, "run() 沒有被 leak_fence 真的呼叫到")
        self.assertFalse(captured[0].wasSuccessful())
        self.assertEqual(rc, 1, "run() 判失敗卻沒有傳遞到 leak_fence() 的 rc")
        self.assertEqual(
            backend.calls, 2,
            "leak_fence 前後兩次真排程器快照沒有都執行——"
            "代表 rc = run() 那行被例外打斷，收尾沒跑完",
        )
        trace = tmp / sentinel_lifecycle.LEAK_FENCE_LOG_NAME
        self.assertTrue(trace.is_file(), "leak_fence 沒有落痕跡——收尾沒跑完")


class ParallelShardPopenFailureKillsAlreadyStartedProcsTest(unittest.TestCase):
    """SD 複審 finding 2（順手處理，未獨立復現，收斂進同一批修復）：Popen() 迴圈若在
    啟動到一半時失敗，已啟動的子行程不應被放生成孤兒——`run_parallel()` 必須
    `kill()`＋`wait()` 已啟動的 procs 再把這次失敗併入統一的例外處理路徑（合成一筆
    `errors` 條目、正常 return）。
    """

    def test_a_later_popen_failure_kills_already_started_procs(self) -> None:
        """DEF-200-274 第四輪：動態佇列下 Popen 由多條 worker thread 併發呼叫，
        「誰先誰後」不再確定——原本靠呼叫次數（第一次成功、第二次失敗）判斷的假
        Popen，改成依 argv 裡的模組名決定成敗（`mod.b` 恆失敗、`mod.a` 恆成功），
        讓斷言不依賴 thread 排程的先後順序。
        """
        parallel_shard = run_root_unittests.parallel_shard

        class _FakeProc:
            def __init__(self) -> None:
                self.killed = False
                self.waited = False
                # 🔴 第四輪複審發現的既存 fixture 缺口（非本輪引入）：本 mock 原本漏了
                # `returncode`，`_worker_thread_loop()` 對成功 Popen 的分支一定會存取它
                # （`results.put((module, proc.returncode, ...))`）——先前的舊版
                # `run_parallel()` 只取 `thread_errors` 第一筆例外就 raise，恰好讓
                # mod.b 那個「刻意」的 OSError 蓋過這個「意外」的 AttributeError，兩者
                # 長得一樣（都是「有例外被攔下」），此測試因此從未真的獨立驗證過
                # mod.a 分支能走到 `results.put()` 那一步。修復後的 `run_parallel()`
                # 會把兩條 worker thread 的例外都排空印出，讓這個潛在缺口第一次現形。
                self.returncode = 0

            def kill(self) -> None:
                self.killed = True

            def wait(self, timeout=None) -> None:
                self.waited = True

            def communicate(self):
                return "", ""

        started: list = []
        started_lock = threading.Lock()

        def fake_popen(argv, **_kwargs):
            module = argv[3]
            if module == "mod.b":
                raise OSError("boom: mod.b Popen failed")
            proc = _FakeProc()
            with started_lock:
                started.append(proc)
            return proc

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])

        with mock.patch.object(parallel_shard, "worker_count", return_value=2), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            try:
                result = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, {"mod.a": 1, "mod.b": 1},
                )
            except OSError as exc:
                self.fail(f"run_parallel() 讓 Popen() 失敗的例外穿透，未被攔截：{exc}")

        self.assertEqual(len(started), 1, "應該只成功啟動 mod.a 這個子行程")
        self.assertTrue(
            started[0].killed,
            "mod.b 的 Popen 失敗時，已啟動的 mod.a 子行程沒有被 kill()——孤兒子行程",
        )
        self.assertFalse(result.wasSuccessful())


class ParallelShardMultipleThreadFailuresAreAllReportedTest(unittest.TestCase):
    """DEF-200-274 第四輪 Architect 複審阻斷條件：`run_parallel()` 此前只用
    `thread_errors.get_nowait()` 取**第一筆**例外就 `raise`，兩條以上 worker thread
    幾乎同時失敗時，其餘例外物件永遠留在佇列裡、從未被印出——診斷資訊真的遺失。

    本測試讓 3 個 worker thread 全部因不同的 Popen 失敗而拋出例外（3 個模組、
    `worker_count=3` 保證每個模組各自一條 thread、無人能倖存去消化佇列），斷言
    最終結果的 `errors` 訊息裡看得到**全部三筆**失敗的線索，而不是只有一筆
    ——這正是 Architect 建議的回歸測試形狀。
    """

    def test_three_simultaneous_popen_failures_all_surface_in_the_error_text(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        def fake_popen(argv, **_kwargs):
            module = argv[3]
            raise OSError(f"boom: {module} Popen failed")

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        modules = {"mod.x": 1, "mod.y": 1, "mod.z": 1}

        with mock.patch.object(parallel_shard, "worker_count", return_value=3), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            try:
                result = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, modules,
                )
            except OSError as exc:
                self.fail(f"run_parallel() 讓 Popen() 失敗的例外穿透，未被攔截：{exc}")

        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1, "run_parallel() 本身的例外合成一筆 errors 條目")
        _, reason = result.errors[0]
        for module in modules:
            self.assertIn(
                f"{module} Popen failed",
                reason,
                f"合併後的例外訊息裡看不到 {module} 那一筆失敗——多筆例外只留了其中幾筆，"
                "回到修復前『只取第一筆就 raise』的靜默漏失",
            )


class ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest(unittest.TestCase):
    """DEF-200-274 第四輪第二次對抗式複審 Architect finding 1(a)：worker thread 內部若拋出非
    `Exception` 子類的 `BaseException`（如 `SystemExit`），`run_parallel()` 不得
    讓它穿透——`_crash_fallback()` 直接收尾，不依賴外層 `except Exception` 篩選
    型別。刻意用 `SystemExit` 而非既有測試已覆蓋的 `OSError`：`OSError` 是
    `Exception` 子類，舊版「合成後 `raise`、交外層 `except Exception` 接」的寫法
    對它本來就成立，換不出這個型別缺口；`SystemExit` 才是舊版寫法會真的漏接的
    具體反例。
    """

    def test_worker_thread_system_exit_is_captured_not_propagated(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        def fake_popen(argv, **_kwargs):
            raise SystemExit("boom: simulated non-Exception BaseException")

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])

        with mock.patch.object(parallel_shard, "worker_count", return_value=1), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            try:
                result = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, {"mod.exit": 1},
                )
            except SystemExit as exc:
                self.fail(f"run_parallel() 讓 worker thread 的 SystemExit 穿透，未被攔截：{exc}")

        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1)
        _, reason = result.errors[0]
        self.assertIn("simulated non-Exception BaseException", reason)


class ParallelShardRealSubprocessProtocolIntegrationTest(unittest.TestCase):
    """DEF-200-274 第三輪複審 Problem 3：涵蓋 `run_parallel()`/`_worker_main()` JSON
    協定通道本身的真實子行程整合測試，刻意**不** mock `subprocess.Popen`。

    3 個 shard 同時涵蓋兩件既有 mock 版測試從未真的走過的路徑：(a) `shard0` 單一
    payload 塞五種結果型態，證明真實 stdout JSON 能被 `json.loads`／`merge_results()`
    正確彙總；(b) `shard1`／`shard2` 匯入當下即對 stderr／stdout 寫超過 OS pipe
    buffer 的內容並自量耗時，驗證 backpressure 不會卡死（另包硬性逾時避免真卡死
    拖住整個測試行程）。與既有 `ParallelShardStderrBackpressureRegressionTest`
    的差異史料見證據檔〈第七輪 史料搬遷（Dev-Trim8）〉。
    """

    _MIXED_MODULE = f"_zzz_protocol_repro_a_mixed_{os.getpid()}"
    _LOUD_STDERR_MODULE = f"_zzz_protocol_repro_b_loud_stderr_{os.getpid()}"
    _LOUD_STDOUT_STDERR_MODULE = f"_zzz_protocol_repro_c_loud_stdout_stderr_{os.getpid()}"
    _SLEEP_SECONDS = 2.0
    _PAYLOAD_BYTES = 5_000_000
    _HARD_TIMEOUT_SECONDS = _SLEEP_SECONDS + 15

    def setUp(self) -> None:
        self._tests_dir = Path(__file__).resolve().parent

        fd_b, result_path_b = tempfile.mkstemp(prefix="protocol_loud_b_elapsed_", suffix=".txt")
        os.close(fd_b)
        fd_c, result_path_c = tempfile.mkstemp(prefix="protocol_loud_c_elapsed_", suffix=".txt")
        os.close(fd_c)
        self._result_path_b = Path(result_path_b)
        self._result_path_c = Path(result_path_c)

        self._mixed_path = self._tests_dir / f"{self._MIXED_MODULE}.py"
        self._loud_stderr_path = self._tests_dir / f"{self._LOUD_STDERR_MODULE}.py"
        self._loud_stdout_stderr_path = self._tests_dir / f"{self._LOUD_STDOUT_STDERR_MODULE}.py"

        self._mixed_path.write_text(
            "import time\n"
            "import unittest\n\n\n"
            "class MixedResultsTest(unittest.TestCase):\n"
            f"    def test_a_sleep(self):\n        time.sleep({self._SLEEP_SECONDS})\n\n"
            "    def test_b_pass(self):\n        pass\n\n"
            "    def test_c_fail(self):\n"
            "        self.assertEqual(1, 2, 'deliberate failure for protocol test')\n\n"
            "    def test_d_error(self):\n"
            "        raise RuntimeError('deliberate error for protocol test')\n\n"
            "    def test_e_skip(self):\n"
            "        self.skipTest('deliberate skip for protocol test')\n\n"
            "    @unittest.expectedFailure\n"
            "    def test_f_unexpected_success(self):\n        pass\n",
            encoding="utf-8",
        )
        self._loud_stderr_path.write_text(
            "import sys\n"
            "import time\n"
            "import unittest\n"
            "from pathlib import Path\n\n\n"
            f"_RESULT = Path({str(self._result_path_b)!r})\n"
            "_start = time.monotonic()\n"
            f"sys.stderr.write('Y' * {self._PAYLOAD_BYTES})\n"
            "sys.stderr.flush()\n"
            "_RESULT.write_text(str(time.monotonic() - _start), encoding='utf-8')\n\n\n"
            "class LoudStderrTest(unittest.TestCase):\n"
            "    def test_pass(self):\n        pass\n",
            encoding="utf-8",
        )
        self._loud_stdout_stderr_path.write_text(
            "import sys\n"
            "import time\n"
            "import unittest\n"
            "from pathlib import Path\n\n\n"
            f"_RESULT = Path({str(self._result_path_c)!r})\n"
            "_start = time.monotonic()\n"
            f"sys.stdout.write('Z' * {self._PAYLOAD_BYTES})\n"
            "sys.stdout.flush()\n"
            f"sys.stderr.write('Z' * {self._PAYLOAD_BYTES})\n"
            "sys.stderr.flush()\n"
            "_RESULT.write_text(str(time.monotonic() - _start), encoding='utf-8')\n\n\n"
            "class LoudStdoutStderrTest(unittest.TestCase):\n"
            "    def test_pass(self):\n        pass\n",
            encoding="utf-8",
        )
        self.addCleanup(self._mixed_path.unlink, missing_ok=True)
        self.addCleanup(self._loud_stderr_path.unlink, missing_ok=True)
        self.addCleanup(self._loud_stdout_stderr_path.unlink, missing_ok=True)
        self.addCleanup(self._result_path_b.unlink, missing_ok=True)
        self.addCleanup(self._result_path_c.unlink, missing_ok=True)

    def test_real_subprocess_protocol_channel_and_stderr_backpressure(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        module_counts = {
            self._MIXED_MODULE: 6,
            self._LOUD_STDERR_MODULE: 1,
            self._LOUD_STDOUT_STDERR_MODULE: 1,
        }
        suite = unittest.TestSuite()
        result_holder: dict = {}

        def _call() -> None:
            result_holder["merged"] = parallel_shard.run_parallel(
                suite, self._tests_dir, module_counts,
            )

        with mock.patch.object(parallel_shard, "worker_count", return_value=3):
            thread = threading.Thread(target=_call, daemon=True)
            thread.start()
            thread.join(timeout=self._HARD_TIMEOUT_SECONDS)

        self.assertFalse(
            thread.is_alive(),
            f"run_parallel() 逾時 {self._HARD_TIMEOUT_SECONDS}s 未返回——"
            "疑似 stderr backpressure 死鎖復發，真實子行程被 pipe buffer 卡死",
        )
        self.assertIn("merged", result_holder, "run_parallel() 沒有正常回傳結果")
        merged = result_holder["merged"]

        # (a) 協定通道本身：三個真實 subprocess 各自印出的一行 JSON 都被正確
        # json.loads 並經 merge_results() 彙總成數量與型別正確的結果。
        self.assertEqual(merged.testsRun, 8)
        self.assertFalse(merged.wasSuccessful())
        self.assertEqual(len(merged.skipped), 1, f"skipped={merged.skipped}")
        self.assertIn("test_e_skip", merged.skipped[0][0].id())
        self.assertEqual(len(merged.errors), 1, f"errors={merged.errors}")
        self.assertIn("test_d_error", merged.errors[0][0].id())
        self.assertEqual(len(merged.failures), 1, f"failures={merged.failures}")
        self.assertIn("test_c_fail", merged.failures[0][0].id())
        self.assertEqual(
            len(merged.unexpectedSuccesses), 1, f"unexpectedSuccesses={merged.unexpectedSuccesses}"
        )
        self.assertIn("test_f_unexpected_success", merged.unexpectedSuccesses[0].id())

        # (b) stderr 管線行為：兩個「LOUD」shard 各自寫入遠超過 OS pipe buffer
        # （常見 64KB）的內容，量到的耗時應與 SLOW shard 的 sleep 秒數無關
        # （近乎瞬間完成），而非被卡到 SLOW shard 的 communicate() 完成才解除。
        elapsed_b = float(self._result_path_b.read_text(encoding="utf-8"))
        elapsed_c = float(self._result_path_c.read_text(encoding="utf-8"))
        self.assertLess(
            elapsed_b, self._SLEEP_SECONDS / 2,
            f"LOUD(stderr) shard 的寫入耗時 {elapsed_b:.3f}s 過於接近 SLOW shard 的"
            f" sleep（{self._SLEEP_SECONDS}s）——stderr backpressure 回歸復發",
        )
        self.assertLess(
            elapsed_c, self._SLEEP_SECONDS / 2,
            f"LOUD(stdout+stderr) shard 的寫入耗時 {elapsed_c:.3f}s 過於接近 SLOW shard 的"
            f" sleep（{self._SLEEP_SECONDS}s）——stderr backpressure 回歸復發",
        )


class ParallelTimingCacheLoadHintsTest(unittest.TestCase):
    """DEF-200-274 第九輪 D2：`tools/lib/parallel_timing_cache.py` 的
    `read_json()`／`load_hints()` 純函式紅綠自證。"""

    def _ptc(self):
        return run_root_unittests.parallel_shard.parallel_timing_cache

    def test_read_json_missing_file_returns_empty(self) -> None:
        # R69：不得用 POSIX 絕對路徑字面值斷言（Windows 上會渲染成反斜線、字面值
        # 必然落空）——改用「存在的暫存目錄 + 保證不存在的檔名」表達同一件事。
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_missing_") as td:
            missing = Path(td) / "no-such-file-xyz.json"
            self.assertEqual(ptc.read_json(missing), {})

    def test_read_json_invalid_json_returns_empty(self) -> None:
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_") as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(ptc.read_json(bad), {})

    def test_read_json_non_dict_returns_empty(self) -> None:
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_") as td:
            arr = Path(td) / "arr.json"
            arr.write_text("[1, 2, 3]", encoding="utf-8")
            self.assertEqual(ptc.read_json(arr), {})

    def test_read_json_filters_non_numeric_and_bool_values(self) -> None:
        """第九輪批評 D2-BOOL-COERCED-AS-TIMING 回歸鎖：bool 是 int 子類別，
        `{"mod": true}` 不得被 `float()` 轉成 1.0 秒。"""
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_") as td:
            mixed = Path(td) / "mixed.json"
            mixed.write_text(
                json.dumps({"a": 1.5, "b": "nope", "c": True, "d": False, "e": 2}),
                encoding="utf-8",
            )
            self.assertEqual(ptc.read_json(mixed), {"a": 1.5, "e": 2.0})

    def test_load_hints_prefers_live_over_seed_and_filters_by_keys(self) -> None:
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_") as td:
            seed = Path(td) / "seed.json"
            live = Path(td) / "live.json"
            seed.write_text(json.dumps({"mod.a": 10.0, "mod.b": 20.0}), encoding="utf-8")
            live.write_text(json.dumps({"mod.a": 99.0}), encoding="utf-8")
            with mock.patch.object(ptc, "SEED_PATH", seed), \
                 mock.patch.object(ptc, "LIVE_CACHE_PATH", live):
                hints = ptc.load_hints({"mod.a", "mod.b", "mod.c"})
        self.assertEqual(hints, {"mod.a": 99.0, "mod.b": 20.0},
                          "活體快取應覆蓋種子；不在 keys 內或缺席的鍵不應出現")


class ParallelTimingCacheOrderDispatchUnitsTest(unittest.TestCase):
    """`order_dispatch_units()`：`hints={}` 時與舊排序位元級相同（零回歸承諾）；
    已知鍵優先於未知鍵；已知鍵之間依秒數遞減。"""

    def _ptc(self):
        return run_root_unittests.parallel_shard.parallel_timing_cache

    def test_empty_hints_matches_legacy_test_count_ordering(self) -> None:
        ptc = self._ptc()
        units = {"a": 3, "b": 1, "c": 2}
        legacy = sorted(units, key=lambda m: (-units[m], m))
        self.assertEqual(ptc.order_dispatch_units(units, {}), legacy)

    def test_known_keys_come_before_unknown_keys(self) -> None:
        ptc = self._ptc()
        units = {"known": 1, "unknown": 100}
        hints = {"known": 5.0}
        self.assertEqual(ptc.order_dispatch_units(units, hints), ["known", "unknown"])

    def test_known_keys_sorted_by_seconds_descending(self) -> None:
        ptc = self._ptc()
        units = {"a": 1, "b": 1, "c": 1}
        hints = {"a": 10.0, "b": 30.0, "c": 20.0}
        self.assertEqual(ptc.order_dispatch_units(units, hints), ["b", "c", "a"])


class ParallelTimingCacheSaveLiveCacheTest(unittest.TestCase):
    """`save_live_cache()`：成功寫入可被 `read_json()` 讀回；寫入失敗只印 warning。"""

    def _ptc(self):
        return run_root_unittests.parallel_shard.parallel_timing_cache

    def test_save_then_read_round_trips(self) -> None:
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_save_") as td:
            live = Path(td) / "live.json"
            with mock.patch.object(ptc, "LIVE_CACHE_PATH", live):
                ptc.save_live_cache({"mod.a": 1.25, "mod.b": 2.5})
                readback = ptc.read_json(live)
        self.assertEqual(readback, {"mod.a": 1.25, "mod.b": 2.5})

    def test_write_failure_prints_warning_and_does_not_raise(self) -> None:
        ptc = self._ptc()
        with tempfile.TemporaryDirectory(prefix="ptc_save_fail_") as td:
            live = Path(td) / "live.json"
            buf = io.StringIO()
            with mock.patch.object(ptc, "LIVE_CACHE_PATH", live), \
                 mock.patch.object(Path, "write_text", side_effect=OSError("boom")), \
                 contextlib.redirect_stderr(buf):
                ptc.save_live_cache({"mod.a": 1.0})
        self.assertIn("寫入失敗", buf.getvalue())


class ParallelTimingCacheStalenessReportTest(unittest.TestCase):
    """`staleness_report()`：重疊率高於門檻回 `None`；低於門檻回訊息且含
    `refresh_parallel_timing_seed.py`；任一邊為空回 `None`。"""

    def _ptc(self):
        return run_root_unittests.parallel_shard.parallel_timing_cache

    def test_high_overlap_returns_none(self) -> None:
        ptc = self._ptc()
        data = {f"mod.{i}": float(100 - i) for i in range(20)}
        self.assertIsNone(ptc.staleness_report(data, dict(data)))

    def test_low_overlap_returns_message_naming_the_refresh_tool(self) -> None:
        ptc = self._ptc()
        seed = {f"seed.{i}": float(100 - i) for i in range(20)}
        live = {f"live.{i}": float(100 - i) for i in range(20)}
        msg = ptc.staleness_report(seed, live)
        self.assertIsNotNone(msg)
        assert msg is not None
        self.assertIn("refresh_parallel_timing_seed.py", msg)

    def test_either_side_empty_returns_none(self) -> None:
        ptc = self._ptc()
        self.assertIsNone(ptc.staleness_report({}, {"a": 1.0}))
        self.assertIsNone(ptc.staleness_report({"a": 1.0}, {}))


class RunParallelPersistsLiveCacheOnlyForLargeRunsTest(unittest.TestCase):
    """第九輪批評 D2-TEST-MOCK-TARGET-WRONG 接受並修正：mock 目標必須是
    `parallel_shard.parallel_timing_cache.save_live_cache`（`parallel_shard` 模組
    本身透過 `import parallel_timing_cache` 把該模組物件掛在自己的命名空間下）。
    <20 個派工單位的既有合成測試不觸發寫入；>=20 個才觸發。
    """

    @staticmethod
    def _fake_popen_factory():
        class _FakeProc:
            returncode = 0

            def communicate(self):
                return (
                    json.dumps({
                        "testsRun": 1, "skipped": [], "errors": [], "failures": [],
                        "unexpectedSuccesses": [],
                    }) + "\n",
                    "",
                )

        def fake_popen(argv, **_kwargs):
            return _FakeProc()

        return fake_popen

    def test_small_run_does_not_persist_live_cache(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        suite = unittest.TestSuite()
        modules = {f"mod.{i}": 1 for i in range(3)}
        with mock.patch.object(parallel_shard, "worker_count", return_value=2), \
                mock.patch.object(parallel_shard.subprocess, "Popen",
                                   side_effect=self._fake_popen_factory()), \
                mock.patch.object(parallel_shard.parallel_timing_cache, "save_live_cache") as saved:
            parallel_shard.run_parallel(suite, Path(__file__).resolve().parent, modules)
        saved.assert_not_called()

    def test_large_run_persists_live_cache(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        suite = unittest.TestSuite()
        modules = {f"mod.{i}": 1 for i in range(25)}
        with mock.patch.object(parallel_shard, "worker_count", return_value=4), \
                mock.patch.object(parallel_shard.subprocess, "Popen",
                                   side_effect=self._fake_popen_factory()), \
                mock.patch.object(parallel_shard.parallel_timing_cache, "save_live_cache") as saved:
            parallel_shard.run_parallel(suite, Path(__file__).resolve().parent, modules)
        saved.assert_called_once()


class ParallelShardSigtermCleanupTest(unittest.TestCase):
    """DEF-200-274 第九輪 D4：主執行緒收到真的 SIGTERM 時，(a) `KeyboardInterrupt`
    從 `run_parallel()` 冒出、(b) 所有已啟動的（即使是在清理快照之後才登記的）
    子行程都被 `kill()`、(c) 舊的 SIGTERM handler 事後被還原。"""

    def test_sigterm_during_join_kills_all_started_procs_and_restores_handler(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard
        started: list = []
        started_lock = threading.Lock()

        class _FakeProc:
            def __init__(self):
                self.killed = False

            def kill(self):
                self.killed = True

        # Windows：`os.kill(pid, SIGTERM)`＝TerminateProcess，沒有 handler 可攔（windows-compat-ci
        # 實測 rc=15、整個 worker 被殺）⇒ 此平台只驗 (c) handler 掛上／還原，(a)(b) 由 POSIX 承擔。
        on_windows = sys.platform.startswith("win")

        def fake_popen(argv, **_kwargs):
            proc = _FakeProc()
            with started_lock:
                idx = len(started)
                started.append(proc)

            def _communicate():
                if idx == 0 and not on_windows:
                    os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(0.3)  # 模擬「還在跑」，時間夠讓其餘 worker 也真的登記進 started
                return "", ""

            proc.communicate = _communicate
            return proc

        old_handler = signal.getsignal(signal.SIGTERM)

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        modules = {f"mod.{i}": 1 for i in range(4)}

        with mock.patch.object(parallel_shard, "worker_count", return_value=4), \
                mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
            if on_windows:
                parallel_shard.run_parallel(suite, Path(__file__).resolve().parent, modules)
            else:
                with self.assertRaises(KeyboardInterrupt):
                    parallel_shard.run_parallel(suite, Path(__file__).resolve().parent, modules)

        self.assertEqual(signal.getsignal(signal.SIGTERM), old_handler,
                          "run_parallel() 結束後必須還原原本的 SIGTERM handler")
        if on_windows:
            return
        with started_lock:
            snapshot = list(started)
        self.assertTrue(snapshot)
        for proc in snapshot:
            self.assertTrue(proc.killed, "已啟動的子行程必須被 kill()，不得放生成孤兒")


class ParallelShardSigtermIgnoredOffMainThreadTest(unittest.TestCase):
    """非主執行緒呼叫 `run_parallel()` 不因為掛 SIGTERM handler 而 `ValueError`。"""

    def test_run_parallel_called_off_main_thread_does_not_raise_valueerror(self) -> None:
        parallel_shard = run_root_unittests.parallel_shard

        class _FakeProc:
            def kill(self):
                pass

        def fake_popen(argv, **_kwargs):
            proc = _FakeProc()
            proc.communicate = lambda: (
                json.dumps({
                    "testsRun": 1, "skipped": [], "errors": [], "failures": [],
                    "unexpectedSuccesses": [],
                }) + "\n",
                "",
            )
            proc.returncode = 0
            return proc

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        suite = unittest.TestSuite([_Case("test_ok")])
        result_holder: dict = {}

        def _call() -> None:
            with mock.patch.object(parallel_shard, "worker_count", return_value=2), \
                    mock.patch.object(parallel_shard.subprocess, "Popen", side_effect=fake_popen):
                result_holder["result"] = parallel_shard.run_parallel(
                    suite, Path(__file__).resolve().parent, {"mod.a": 1, "mod.b": 1})

        t = threading.Thread(target=_call)
        t.start()
        t.join(timeout=10)
        self.assertIn("result", result_holder, "非主執行緒呼叫不該因 ValueError 而整段沒完成")


class _TopLevelDispatchFixtureA(unittest.TestCase):
    """DEF-200-274 第六輪：供 `DispatchGranularity*Test` 使用的頂層 fixture 類別。

    刻意定義在模組層（非某個測試方法內部），使 `__qualname__` 不含 `<locals>`，
    才能拿來驗證「白名單模組的頂層類別會被 `dispatch_key()` 細分」這條正向路徑
    ——巢狀類別測（fail-closed 分支）則沿用既有慣例、直接在測試方法內部定義
    區域類別即可自然取得含 `<locals>` 的 `__qualname__`，不需要本 fixture。
    """

    def test_ok(self) -> None:
        pass


class DispatchGranularityDispatchKeyTest(unittest.TestCase):
    """DEF-200-274 第六輪四方獨立複審（Architect/SA/SD/QA）共同點名的缺口：
    `tools/lib/dispatch_granularity.py` 落地時零測試覆蓋，且該檔 docstring 曾
    宣稱『兩份 `_PLACEHOLDER_MODULE`／`_module_of()` 複本是否同步由本測試檔
    看守』——查無實據。本測試類別（與下面兩個姊妹類別）補齊覆蓋，讓這句話
    從『說了才知道是假的』變成『真的有回歸鎖看守』。

    白名單一律用 `mock.patch.object` 暫時覆寫成只含本模組（`__name__`），
    不改動真正的 `CLASS_LEVEL_DISPATCH_MODULES`（那兩個真實白名單檔案另有
    `DispatchGranularityWhitelistHasNoModuleLevelFixturesTest` 專門驗證）。
    """

    def test_non_whitelisted_module_stays_at_module_granularity(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity

        class _Case(unittest.TestCase):
            def test_ok(self):
                pass

        case = _Case("test_ok")
        key = dispatch_granularity.dispatch_key(case)
        self.assertEqual(key, type(case).__module__, "非白名單模組不該被細分")

    def test_whitelisted_module_top_level_class_is_split_by_class(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        case = _TopLevelDispatchFixtureA("test_ok")
        with mock.patch.object(
            dispatch_granularity, "CLASS_LEVEL_DISPATCH_MODULES", frozenset({__name__}),
        ):
            key = dispatch_granularity.dispatch_key(case)
        self.assertEqual(
            key, f"{__name__}.{_TopLevelDispatchFixtureA.__qualname__}",
            "白名單模組的頂層類別應被細分成 module.ClassName",
        )

    def test_nested_class_in_whitelisted_module_falls_back_to_module(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity

        class _NestedCase(unittest.TestCase):
            def test_ok(self):
                pass

        case = _NestedCase("test_ok")
        self.assertIn(
            "<locals>", type(case).__qualname__, "本測試前提：受測類別須為巢狀類別")
        with mock.patch.object(
            dispatch_granularity, "CLASS_LEVEL_DISPATCH_MODULES", frozenset({__name__}),
        ):
            key = dispatch_granularity.dispatch_key(case)
        self.assertEqual(
            key, __name__, "巢狀類別必須 fail-closed 退回模組粒度，不得誤判為可細分")

    def test_unresolvable_qualname_falls_back_to_module(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        # 用 type() 現造一個一次性類別、`__qualname__` 從一開始就設成模組上不存在
        # 的名字——刻意不對既有共用 fixture 類別做 mock.patch.object(cls,
        # "__qualname__", ...)：`__qualname__` 是 dunder slot，mock 的清理階段對它
        # 呼叫 delattr 會拋 TypeError（immutable type），且若真的清理失敗會讓
        # 汙染跨測試殘留（本測試曾實際踩過這個坑，見本行的存在理由）。
        fixture_cls = type(
            "_UnresolvableQualnameFixture", (unittest.TestCase,), {
                "test_ok": lambda self: None,
                "__qualname__": "NameThatIsNotOnTheModule",
                "__module__": __name__,
            },
        )
        case = fixture_cls("test_ok")
        with mock.patch.object(
            dispatch_granularity, "CLASS_LEVEL_DISPATCH_MODULES", frozenset({__name__}),
        ):
            key = dispatch_granularity.dispatch_key(case)
        self.assertEqual(
            key, __name__, "getattr(module, qualname) 解不回同一個類別物件時必須 fail-closed")

    def test_placeholder_test_is_never_split_even_if_its_module_name_is_whitelisted(
        self,
    ) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        placeholder = unittest.loader._FailedTest(
            "some_module_that_failed_to_import", ImportError("boom"))
        with mock.patch.object(
            dispatch_granularity, "CLASS_LEVEL_DISPATCH_MODULES",
            frozenset({"some_module_that_failed_to_import"}),
        ):
            key = dispatch_granularity.dispatch_key(placeholder)
        self.assertEqual(key, "some_module_that_failed_to_import")


class DispatchGranularityPlaceholderConstantStaysInSyncTest(unittest.TestCase):
    """`dispatch_granularity.py` 為避免與 `run_root_unittests.py` 循環 import 而
    獨立持有一份 `_PLACEHOLDER_MODULE`／`_module_of()` 複本（見該檔頭 WHY）。
    本測試是那份 WHY 的機械兌現：任一邊獨立改掉這個值都會讓本測試變紅，而不是
    悄悄漂移到下一次有人手動比對才發現。
    """

    def test_placeholder_module_constant_matches(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        self.assertEqual(
            dispatch_granularity._PLACEHOLDER_MODULE,
            run_root_unittests._PLACEHOLDER_MODULE,
            "兩份 _PLACEHOLDER_MODULE 複本已經漂移——dispatch_key() 對 placeholder "
            "測試的判斷會悄悄跑偏",
        )

    def test_module_of_behaviour_matches_on_a_real_placeholder(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        placeholder = unittest.loader._FailedTest("some_module", ImportError("boom"))
        self.assertEqual(
            dispatch_granularity._module_of(placeholder),
            run_root_unittests._module_of(placeholder),
            "兩份 _module_of() 複本對同一筆 placeholder 測試算出不同結果",
        )


class DispatchGranularityWhitelistHasNoModuleLevelFixturesTest(unittest.TestCase):
    """DEF-200-274 第六輪四方獨立複審 Architect finding：白名單機制目前完全依賴
    人工核實『類別間無隱性共享狀態依賴』，最容易被忽略、後果最隱蔽的違反方式是
    未來有人替白名單模組新增 `setUpModule`／`tearDownModule`（原本整檔在同一個
    subprocess 跑一次，細分成 (module, class) 後每個 class 各自的 subprocess 都
    會重跑一次）。本測試把這條最低限度的前提轉成機械不變量。
    """

    def test_no_whitelisted_module_defines_module_level_fixtures(self) -> None:
        dispatch_granularity = run_root_unittests.dispatch_granularity
        problems = []
        for module_name in sorted(dispatch_granularity.CLASS_LEVEL_DISPATCH_MODULES):
            module = importlib.import_module(module_name)
            for fixture_name in ("setUpModule", "tearDownModule"):
                if hasattr(module, fixture_name):
                    problems.append(f"{module_name} 定義了 {fixture_name}")
        self.assertEqual(
            problems, [],
            "白名單模組出現模組層 fixture，細分成 (module, class) 派工後會被重複"
            "執行、破壞其『整檔只跑一次』的假設：\n  " + "\n  ".join(problems),
        )


class DispatchGranularityAutoSplitCandidatesTest(unittest.TestCase):
    """DEF-200-274 第九輪 D2：`auto_class_level_candidates()` 自動細分候選——
    倍率判準沿用 `dispatch_imbalance.detect_imbalance()`，只保留通過安全網
    （頂層、非 placeholder、模組未定義 setUpModule/tearDownModule）的候選。
    用本測試檔自己（`__name__`，已知無 setUpModule/tearDownModule）當天然樣本。
    """

    def _dg(self):
        return run_root_unittests.dispatch_granularity

    def test_module_over_fair_share_and_safe_is_selected(self) -> None:
        dg = self._dg()
        hints = {__name__: 100.0, "other.mod": 1.0}
        candidates = dg.auto_class_level_candidates(hints, worker_count=2)
        self.assertIn(__name__, candidates)

    def test_already_class_level_key_is_not_a_candidate(self) -> None:
        dg = self._dg()
        key = f"{__name__}.SomeClass"
        hints = {key: 100.0, "other.mod": 1.0}
        candidates = dg.auto_class_level_candidates(hints, worker_count=2)
        self.assertEqual(candidates, frozenset())

    def test_known_module_is_excluded(self) -> None:
        dg = self._dg()
        hints = {__name__: 100.0, "other.mod": 1.0}
        candidates = dg.auto_class_level_candidates(
            hints, worker_count=2, known_modules=frozenset({__name__}))
        self.assertNotIn(__name__, candidates)

    def test_module_with_module_level_fixture_is_excluded(self) -> None:
        dg = self._dg()
        fake_name = "test_fixture_autosplit_fixture_module"
        fake_module = types.ModuleType(fake_name)
        fake_module.setUpModule = lambda: None
        sys.modules[fake_name] = fake_module
        self.addCleanup(sys.modules.pop, fake_name, None)
        hints = {fake_name: 100.0, "other.mod": 1.0}
        candidates = dg.auto_class_level_candidates(hints, worker_count=2)
        self.assertNotIn(fake_name, candidates)

    def test_unimportable_module_is_excluded_without_raising(self) -> None:
        dg = self._dg()
        hints = {"no_such_module_xyz_9999": 100.0, "other.mod": 1.0}
        candidates = dg.auto_class_level_candidates(hints, worker_count=2)
        self.assertEqual(candidates, frozenset())


class DispatchGranularityAutoSuiteDispatchUnitsTest(unittest.TestCase):
    """`auto_suite_dispatch_units()`：無快取時與 `suite_dispatch_units(tests)` 逐位元
    相同（零回歸）；有 hints 命中安全、非白名單模組時回傳的 dict 含 `module.Class` 鍵。
    """

    def _dg(self):
        return run_root_unittests.dispatch_granularity

    @staticmethod
    def _ptc():
        # 第九輪：`dispatch_granularity.auto_suite_dispatch_units()` 對
        # `parallel_timing_cache` 是**函式內延遲 import**（見該函式 docstring），
        # 該名字不是 `dispatch_granularity` 模組本身的屬性——`mock.patch.object`
        # 必須對準真正掛著這個函式的模組物件（`sys.modules` 裡只有一份，
        # `parallel_shard` 頂層 `import parallel_timing_cache` 恰好持有同一份引用）。
        return run_root_unittests.parallel_shard.parallel_timing_cache

    def test_no_hints_matches_plain_suite_dispatch_units(self) -> None:
        dg = self._dg()
        tests = [_TopLevelDispatchFixtureA("test_ok")]
        with mock.patch.object(self._ptc(), "load_hints", return_value={}):
            auto = dg.auto_suite_dispatch_units(tests, worker_count=4)
        self.assertEqual(auto, dg.suite_dispatch_units(tests))

    def test_hints_hitting_a_safe_non_whitelisted_module_splits_by_class(self) -> None:
        dg = self._dg()
        tests = [_TopLevelDispatchFixtureA("test_ok")]
        fake_hints = {__name__: 100.0, "other.mod": 1.0}
        with mock.patch.object(self._ptc(), "load_hints", return_value=fake_hints):
            auto = dg.auto_suite_dispatch_units(tests, worker_count=2)
        expected_key = f"{__name__}.{_TopLevelDispatchFixtureA.__qualname__}"
        self.assertIn(expected_key, auto)


class DispatchImbalanceDetectionTest(unittest.TestCase):
    """DEF-200-274 第七輪：`tools/lib/dispatch_imbalance.py` 純函式的紅綠自證
    （掌舵者要求「自動偵測未來新熱點，不再只能靠人眼」）。純函式邏輯測完後，
    再驗 `report_dispatch_imbalance()` 的印出接線本身（見下方
    `ReportDispatchImbalanceTest`）。
    """

    def test_balanced_timings_flag_nothing(self) -> None:
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        # 4 個單位、worker=4，每個單位恰好等於公平均分基準 → 倍率=1.0，不觸發。
        timings = {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0}
        self.assertEqual(dispatch_imbalance.detect_imbalance(timings, worker_count=4), [])

    def test_single_dominant_unit_is_flagged_with_correct_ratio(self) -> None:
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        # 總耗時 130s／worker=4 → 公平均分基準 32.5s；"hot" 耗時 100s → 倍率
        # ≈3.08，遠超預設門檻 1.5，其餘三個各 10s（倍率 <1）不該出現。
        timings = {"hot": 100.0, "a": 10.0, "b": 10.0, "c": 10.0}
        flagged = dispatch_imbalance.detect_imbalance(timings, worker_count=4)
        self.assertEqual(len(flagged), 1, f"只有 hot 該被標記，實際：{flagged}")
        key, elapsed, ratio = flagged[0]
        self.assertEqual(key, "hot")
        self.assertEqual(elapsed, 100.0)
        self.assertAlmostEqual(ratio, 100.0 / 32.5, places=6)

    def test_multiple_flagged_units_sorted_by_ratio_descending(self) -> None:
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        timings = {"mid_hot": 60.0, "hottest": 100.0, "cold": 5.0}
        # 公平均分基準 = 165/4 = 41.25；60/41.25≈1.45（未過門檻）、100/41.25≈2.42（過）。
        # 刻意讓其中一個落在門檻附近但不過，驗證「只標超過門檻的」而非「全部排序」。
        flagged = dispatch_imbalance.detect_imbalance(timings, worker_count=4)
        keys = [item[0] for item in flagged]
        self.assertEqual(keys, ["hottest"], f"mid_hot 倍率未過門檻不該被標記，實際：{flagged}")

    def test_empty_timings_returns_empty(self) -> None:
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        self.assertEqual(dispatch_imbalance.detect_imbalance({}, worker_count=4), [])

    def test_non_positive_worker_count_returns_empty(self) -> None:
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        timings = {"hot": 100.0, "a": 1.0}
        self.assertEqual(dispatch_imbalance.detect_imbalance(timings, worker_count=0), [])
        self.assertEqual(dispatch_imbalance.detect_imbalance(timings, worker_count=-1), [])

    def test_fewer_units_than_workers_and_balanced_flags_nothing(self) -> None:
        """第七輪四方獨立複審（Architect/SA/SD/QA）共同點名並經 QA 合成場景證實
        的真缺陷：派工單位數 < worker_count 時，若分母誤用未經 cap 的名目
        `worker_count`，即使所有單位耗時完全相同也會被全數誤判為不均（QA 實測：
        3 個耗時皆 20.0 的單位、worker_count=8 時倍率恆 2.67、全部 3 個都被標記）。
        本測試釘住修復後的正確行為：`min(worker_count, len(module_timings))`
        當分母，完全均衡的資料在任何 worker_count 下都不該被標記。
        """
        dispatch_imbalance = run_root_unittests.dispatch_imbalance
        timings = {"a": 20.0, "b": 20.0, "c": 20.0}
        for worker_count in (2, 3, 4, 8, 50):
            with self.subTest(worker_count=worker_count):
                self.assertEqual(
                    dispatch_imbalance.detect_imbalance(timings, worker_count), [],
                    f"3 個完全均衡的單位在 worker_count={worker_count} 下不該被標記",
                )


class ReportDispatchImbalanceTest(unittest.TestCase):
    """`dispatch_imbalance.report_dispatch_imbalance()` 的印出接線：序列模式
    （無 `module_timings`）與「有均衡資料但無不均」皆不印；有不均時印出可執行的
    建議（不是只印數字，讓讀者不必再自己推導該做什麼）。
    """

    class _FakeResult:
        def __init__(self, module_timings=None):
            if module_timings is not None:
                self.module_timings = module_timings

    def test_sequential_result_without_module_timings_prints_nothing(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(
                self._FakeResult(), worker_count=4,
            )
        self.assertEqual(buf.getvalue(), "")

    def test_balanced_module_timings_prints_nothing(self) -> None:
        buf = io.StringIO()
        result = self._FakeResult({"a": 10.0, "b": 10.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=2)
        self.assertEqual(buf.getvalue(), "")

    def test_imbalanced_module_timings_prints_flagged_key_and_suggestion(self) -> None:
        buf = io.StringIO()
        result = self._FakeResult({"hot": 100.0, "a": 1.0, "b": 1.0, "c": 1.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        output = buf.getvalue()
        self.assertIn("hot", output)
        self.assertIn(
            "dispatch_granularity.py", output,
            "建議文字必須指向現成的白名單機制，不能只丟數字給讀者",
        )

    def test_github_actions_env_adds_warning_annotation(self) -> None:
        """DEF-200-274 第八輪：CI 上（`GITHUB_ACTIONS=true`）額外印一行 GitHub
        Actions 原生 `::warning::` annotation，讓不均訊號直接上 run 摘要頁面，
        不需要人工捲動冗長 log 中段。"""
        buf = io.StringIO()
        result = self._FakeResult({"hot": 100.0, "a": 1.0, "b": 1.0, "c": 1.0})
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False), \
             contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        lines = buf.getvalue().splitlines()
        warning_lines = [ln for ln in lines if ln.startswith("::warning::")]
        self.assertEqual(
            len(warning_lines), 1,
            f"預期恰 1 行 ::warning:: annotation（一個熱點），實際：{warning_lines}")
        self.assertIn("hot", warning_lines[0])

    def test_non_ci_env_has_no_warning_annotation(self) -> None:
        """未設 `GITHUB_ACTIONS` 時維持原本純 print 行為，不多印 `::warning::`。"""
        buf = io.StringIO()
        result = self._FakeResult({"hot": 100.0, "a": 1.0, "b": 1.0, "c": 1.0})
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_ACTIONS", None)
            with contextlib.redirect_stdout(buf):
                run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(
                    result, worker_count=4)
        self.assertNotIn("::warning::", buf.getvalue())


class _FakeParallelResult:
    """DEF-200-274 第九輪 D3：`ReportDispatchImbalanceOverFairShareBandTest`／
    `ReportDispatchImbalanceWallClockLossTest` 共用的假結果——比既有
    `ReportDispatchImbalanceTest._FakeResult` 多支援 `wall_clock`／
    `module_finish_times` 兩個可選欄位（不設時該屬性根本不存在，
    `getattr(result, "...", None)` 回 `None`，與序列模式／舊呼叫端同構）。
    """

    def __init__(self, module_timings=None, wall_clock=None, module_finish_times=None):
        if module_timings is not None:
            self.module_timings = module_timings
        if wall_clock is not None:
            self.wall_clock = wall_clock
        if module_finish_times is not None:
            self.module_finish_times = module_finish_times


class ReportDispatchImbalanceOverFairShareBandTest(unittest.TestCase):
    """DEF-200-274 第九輪 D3：1.0~1.5 倍率帶——排程救不了，需細分，去重後只印一次
    （不重複既有 1.5 熱點門檻那組）。"""

    def test_unit_between_1_0_and_1_5_is_printed_with_warn_prefix(self) -> None:
        # 公平份額 = 130/4 = 32.5；"mid" 40.0 倍率 ≈1.23（1.0~1.5 之間）。
        buf = io.StringIO()
        result = _FakeParallelResult({"mid": 40.0, "a": 30.0, "b": 30.0, "c": 30.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        output = buf.getvalue()
        self.assertIn("⚠️", output)
        self.assertIn("mid", output)
        self.assertNotIn("🚨", output, "倍率未過 1.5 熱點門檻不該出現在 🚨 那組")

    def test_unit_over_1_5_is_not_duplicated_in_the_over_share_band(self) -> None:
        buf = io.StringIO()
        result = _FakeParallelResult({"hot": 100.0, "a": 1.0, "b": 1.0, "c": 1.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        output = buf.getvalue()
        # 只數 bullet 行：CI（GITHUB_ACTIONS=true）多印的 ::warning:: annotation 不算重複
        self.assertEqual(output.count("- hot:"), 1, "hot 已在 🚨 組出現，不該在 1.0~1.5 帶重複列出")
        self.assertNotIn("⚠️ 以下派工單位耗時超過公平份額", output,
                          "唯一超標的 hot 已被 🚨 組吸收，1.0~1.5 帶去重後應無殘留可印")

    def test_all_units_at_or_below_fair_share_prints_neither_band(self) -> None:
        buf = io.StringIO()
        result = _FakeParallelResult({"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        self.assertEqual(buf.getvalue(), "")


class ReportDispatchImbalanceWallClockLossTest(unittest.TestCase):
    """DEF-200-274 第九輪 D3：整體排程效率 `wall/ideal`——`wall_clock` 屬性不存在
    （既有 5 支 `ReportDispatchImbalanceTest` 皆用此形狀）時該區塊不印，回歸鎖。
    """

    def test_loss_at_or_below_threshold_prints_nothing_extra(self) -> None:
        # ideal = max(sum/eff_workers, max_unit) = max(40/4, 10) = 10；wall=11 → loss=1.1<=1.15。
        buf = io.StringIO()
        result = _FakeParallelResult(
            {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0}, wall_clock=11.0)
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        self.assertNotIn("🐢", buf.getvalue())

    def test_loss_above_threshold_prints_efficiency_and_last_finishers(self) -> None:
        # ideal=10；wall=15 → loss=1.5>1.15。
        buf = io.StringIO()
        result = _FakeParallelResult(
            {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0}, wall_clock=15.0,
            module_finish_times={"a": 15.0, "b": 5.0, "c": 8.0, "d": 3.0},
        )
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        output = buf.getvalue()
        self.assertIn("🐢", output)
        self.assertIn("loss=", output)
        self.assertIn("最後完工", output)
        # 依 finish_at 遞減排序：a(15) 應排在 c(8) 之前，c 應排在 b(5) 之前。
        self.assertLess(output.index(" - a:"), output.index(" - c:"))
        self.assertLess(output.index(" - c:"), output.index(" - b:"))

    def test_no_wall_clock_attribute_prints_nothing_extra(self) -> None:
        """回歸鎖：既有 `ReportDispatchImbalanceTest._FakeResult` 皆無 `wall_clock`
        屬性，本區塊必須整段不印、不拋例外——即既有 5 支測試不受影響。"""
        buf = io.StringIO()
        result = ReportDispatchImbalanceTest._FakeResult({"hot": 100.0, "a": 1.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=2)
        self.assertNotIn("🐢", buf.getvalue())

    def test_missing_finish_times_prints_efficiency_line_without_finisher_list(self) -> None:
        buf = io.StringIO()
        result = _FakeParallelResult(
            {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0}, wall_clock=15.0)
        with contextlib.redirect_stdout(buf):
            run_root_unittests.dispatch_imbalance.report_dispatch_imbalance(result, worker_count=4)
        output = buf.getvalue()
        self.assertIn("🐢", output)
        self.assertNotIn("最後完工", output, "缺一個可選欄位不該讓整段不印，但也不該憑空造清單")


class ReportModuleTimingsPrintsWorkerCountTest(unittest.TestCase):
    """DEF-200-274 第九輪 D3 SA-09：標題行印實際 worker 數。"""

    class _FakeResult:
        def __init__(self, module_timings, workers_used=None):
            self.module_timings = module_timings
            if workers_used is not None:
                self.workers_used = workers_used

    def test_workers_used_present_shows_worker_count(self) -> None:
        buf = io.StringIO()
        result = self._FakeResult({"a": 1.0}, workers_used=6)
        with contextlib.redirect_stdout(buf):
            run_root_unittests.report_module_timings(result)
        self.assertIn("worker=6", buf.getvalue())

    def test_workers_used_absent_shows_worker_none_without_raising(self) -> None:
        buf = io.StringIO()
        result = self._FakeResult({"a": 1.0})
        with contextlib.redirect_stdout(buf):
            run_root_unittests.report_module_timings(result)
        self.assertIn("worker=None", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
