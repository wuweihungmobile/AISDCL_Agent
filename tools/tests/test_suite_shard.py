# 受測面：tools/lib/suite_shard.py、tools/shard_census.py、tools/run_root_unittests.py（接線）
"""DEF-200-593：tools/tests 跨機分片（`AUTOSDD_TEST_SHARD=i/N`）的回歸鎖。

存在理由：windows-compat-ci 的 tools/tests 步驟要 45 分鐘以上，改成 matrix N 片各跑在自己的
runner。分片機制若算錯（聯集≠全集、兩片重疊、各機切分不一致）＝**有測試從 CI 靜默消失**而
每片都綠——所以本檔把「聯集＝全集、兩兩無交集、可重現」釘在真實收集面（不是玩具清單）上，並把
全集級判準延後的語意（skip 天花板／M6／豁免表 stale 改由 `tools/shard_census.py` 合併後判）
逐項釘住。每條測試的 docstring 寫明它在防哪一種失效。
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests as R  # noqa: E402, I001  # import 時把 tools/lib 放進 sys.path
import suite_shard as S  # noqa: E402, I001  # 須與 R 同一個（bare 名）物件：`_LAST` 在其上

dispatch_granularity = R.dispatch_granularity
_REAL = R._TESTS_DIR
_ENV = S.ENV


def _real_tests() -> list[unittest.TestCase]:
    return R._flatten(R.discover_suite(_REAL))


class ParseTest(unittest.TestCase):
    """`tools/lib/suite_shard.py::parse`：分片參數的文法。壞格式一律 fail-loud。"""

    def test_unset_or_empty_means_no_sharding(self) -> None:
        """未設／空字串＝不分片，行為與修前逐字相同（CI 以外的所有呼叫端都靠這條不受影響）。"""
        self.assertIsNone(S.parse(None))
        self.assertIsNone(S.parse(""))

    def test_valid_specs_parse_to_one_based_index_and_total(self) -> None:
        """片號 1 起算、含上界；`1/1` 合法（N=1 等同全跑）。"""
        self.assertEqual(S.parse("1/1"), (1, 1))
        self.assertEqual(S.parse("2/3"), (2, 3))
        self.assertEqual(S.parse("3/3"), (3, 3))

    def test_malformed_specs_raise_instead_of_silently_running_everything_or_nothing(self) -> None:
        """寫錯的參數若退回「全跑」只是浪費，退回「不跑」就是假綠——兩個方向都不准默默處理。"""
        bad_specs = ("0/3", "4/3", "a/b", "1/0", "1/", "/3", " 1/3", "1/3 ", "-1/3", "1.5/3",
                     "01/3x")
        for bad in bad_specs:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.parse(bad)

    def test_main_bails_out_before_running_anything_on_a_malformed_spec(self) -> None:
        """`main()` 的早退：壞參數走 `_bail`（rc=1、一支測試都不跑），不是跑到一半才丟例外。"""
        with mock.patch.dict(os.environ, {_ENV: "9/3"}), mock.patch.object(
            sys, "stderr", new=mock.MagicMock()
        ), mock.patch.object(R, "run_with_floor") as ran:
            self.assertEqual(R.main(), 1)
        ran.assert_not_called()


class PlanTest(unittest.TestCase):
    """`tools/lib/suite_shard.py::plan`：切分判準（純函式，合成單位）。"""

    UNITS = {f"m{i:02d}": 1 + i % 4 for i in range(40)} | {"m00.A": 3, "m00.B": 2}
    HINTS = {f"m{i:02d}": float((i * 37) % 91 + 1) for i in range(40)}

    def test_every_unit_lands_in_exactly_one_shard_for_every_n(self) -> None:
        """聯集＝全集、無交集：`plan` 回傳的是 單位→片號 的函式，天然每單位一片；這裡釘的是片號
        範圍與完整性（沒有單位被漏掉、沒有越界片號）。"""
        for n in (1, 2, 3, 4, 7):
            with self.subTest(n=n):
                got = S.plan(self.UNITS, n, self.HINTS)
                self.assertEqual(set(got), set(self.UNITS))
                self.assertLessEqual(set(got.values()), set(range(1, n + 1)))

    def test_plan_is_independent_of_dict_order_and_repeatable(self) -> None:
        """各片在不同機器上各自算：輸入集合相同則輸出必須逐位相同，與插入順序無關。"""
        base = S.plan(self.UNITS, 3, self.HINTS)
        keys = list(self.UNITS)
        random.Random(7).shuffle(keys)
        shuffled = {k: self.UNITS[k] for k in keys}
        hshuf = dict(sorted(self.HINTS.items(), reverse=True))
        self.assertEqual(S.plan(shuffled, 3, hshuf), base)
        self.assertEqual(S.plan(self.UNITS, 3, self.HINTS), base)

    def test_plan_digest_is_identical_across_interpreters_with_different_hash_seeds(self) -> None:
        """三台 runner 是三個獨立行程：若切分依賴 `set`／`hash` 的迭代序（PYTHONHASHSEED 每行程
        不同），同一輸入在各片算出不同切分 ⇒ 聯集≠全集卻各片自己看不出來。以兩個不同種子的
        真子行程各算一次，摘要必須相同。"""
        import subprocess

        code = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "import suite_shard as S;"
            "units={f'm{i:02d}': 1 + i % 4 for i in range(60)};"
            "hints={f'm{i:02d}': float(i % 7 + 1) for i in range(60)};"
            "print(S.plan_digest(S.plan(units, 3, hints)))"
        )
        lib = str(_REAL.parent / "lib")
        outs = []
        for seed in ("1", "2", "3"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            cp = subprocess.run([sys.executable, "-c", code, lib], capture_output=True,
                                text=True, encoding="utf-8", env=env, check=True)
            outs.append(cp.stdout.strip())
        self.assertEqual(len(set(outs)), 1, outs)

    def test_n_equals_one_puts_everything_in_the_only_shard(self) -> None:
        """N=1 等同未分片：全部單位在第 1 片。"""
        self.assertEqual(set(S.plan(self.UNITS, 1, self.HINTS).values()), {1})

    def test_lpt_balance_is_within_one_heaviest_unit_of_the_mean(self) -> None:
        """LPT 的保證：最重片 ≤ 平均 + 最重單位。切分若退化成依字母分桶，這條會紅——
        那會讓一片獨吞重單位而 CI 牆鐘不降。"""
        w = S._weights(self.UNITS, self.HINTS)
        for n in (2, 3, 4):
            got = S.plan(self.UNITS, n, self.HINTS)
            loads = [sum(w[k] for k, s in got.items() if s == i) for i in range(1, n + 1)]
            self.assertLessEqual(max(loads), sum(w.values()) / n + max(w.values()))

    def test_equal_weights_are_tie_broken_by_unit_key(self) -> None:
        """同權重以單位鍵字典序破平手（確定性）：三個同權重單位、N=3 ⇒ a→1、b→2、c→3。"""
        units = {"c": 1, "a": 1, "b": 1}
        self.assertEqual(S.plan(units, 3, {"a": 5.0, "b": 5.0, "c": 5.0}), {"a": 1, "b": 2, "c": 3})

    def test_plan_digest_changes_when_any_assignment_changes(self) -> None:
        """摘要是彙總 job 驗「兩邊算出同一份切分」的憑證，必須對單一單位的移動敏感。"""
        a = S.plan(self.UNITS, 3, self.HINTS)
        b = dict(a)
        b["m05"] = a["m05"] % 3 + 1
        self.assertNotEqual(S.plan_digest(a), S.plan_digest(b))

    def test_weight_fallbacks_direct_children_module_share_and_mean(self) -> None:
        """種子沒有的單位也要有確定的權重：直接鍵 > 子鍵（類別級）加總（方法鍵不重複計）>
        母模組鍵按測試數分攤 > 種子平均秒／測試。fallback 若漏掉，新單位權重為 0 ⇒ 全擠同一片。"""
        units = {"mod.A": 2, "mod.B": 2, "kid": 4, "solo": 3, "known": 1}
        hints = {"mod": 40.0, "kid.X": 3.0, "kid.X.t1": 2.0, "kid.Y": 4.0, "known": 6.0}
        w = S._weights(units, hints)
        self.assertEqual(w["known"], 6000)
        self.assertEqual(w["kid"], 7000)  # kid.X(3)+kid.Y(4)；kid.X.t1 是 kid.X 的後代、不重複計
        self.assertEqual(w["mod.A"], 20000)  # 40 s × 2/(2+2)
        self.assertEqual(w["solo"], 18000)  # 種子平均 6 s／測試（known）× 3


class RealCollectionTest(unittest.TestCase):
    """真實收集面（`tools/tests` 全樹）上的分片不變量——不是玩具清單。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tests = _real_tests()
        cls.full = {t.id() for t in cls.tests}
        cls.parts: dict[int, tuple[set[str], int]] = {}
        suite = unittest.TestSuite(cls.tests)
        for i in (1, 2, 3):
            with mock.patch.dict(os.environ, {_ENV: f"{i}/3"}):
                sub, ran = S.restrict(suite, _REAL, _REAL)
            ids = {t.id() for t in R._flatten(sub)}
            cls.parts[i] = (ids, ran)
        S._LAST = None  # 模組級狀態不外洩給同行程的其他測試

    def test_three_shards_partition_the_real_collection(self) -> None:
        """聯集＝全集且兩兩無交集：分片若漏一支，那支測試在 CI 上就從此沒人跑而三片全綠。"""
        union: set[str] = set()
        for ids, ran in self.parts.values():
            self.assertEqual(len(ids), ran)
            self.assertFalse(union & ids, "兩片同時含有同一支測試")
            union |= ids
        self.assertEqual(union, self.full)
        self.assertEqual(sum(r for _, r in self.parts.values()), len(self.tests))

    def test_the_same_input_gives_the_same_partition_twice(self) -> None:
        """可重現：三台 runner 各自算，結果必須相同（plan 摘要相同即切分相同）。"""
        units = dispatch_granularity.suite_dispatch_units(self.tests)
        self.assertEqual(S.plan_digest(S.plan(units, 3)), S.plan_digest(S.plan(units, 3)))

    def test_n_equals_one_is_the_whole_collection(self) -> None:
        """N=1 等同未分片：同一批測試（以 id 集合為準）。"""
        with mock.patch.dict(os.environ, {_ENV: "1/1"}):
            sub, ran = S.restrict(unittest.TestSuite(self.tests), _REAL, _REAL)
        self.assertEqual({t.id() for t in R._flatten(sub)}, self.full)
        self.assertEqual(ran, len(self.tests))

    def test_unset_env_returns_the_very_same_suite_untouched(self) -> None:
        """未設環境變數＝現行行為逐字不變：回傳的就是原 suite 物件，不是重組出來的複本。"""
        suite = unittest.TestSuite(self.tests)
        with mock.patch.dict(os.environ):
            os.environ.pop(_ENV, None)
            sub, ran = S.restrict(suite, _REAL, _REAL)
        self.assertIs(sub, suite)
        self.assertEqual(ran, len(self.tests))
        self.assertIsNone(S._LAST)

    def test_synthetic_trees_are_never_sharded_even_when_the_env_is_set(self) -> None:
        """單元測試自己對合成樹呼叫 `run_with_floor`：若分片環境變數滲進去，合成樹的測試會被
        切走而該測試莫名其妙地紅。只有「真實 tools/tests」才受分片管轄。"""
        suite = unittest.TestSuite(self.tests[:5])
        with mock.patch.dict(os.environ, {_ENV: "2/3"}):
            sub, ran = S.restrict(suite, Path(tempfile.gettempdir()), _REAL)
        self.assertIs(sub, suite)
        self.assertEqual(ran, 5)

    def test_the_heaviest_selfimproving_module_is_split_to_class_units(self) -> None:
        """分片的前置條件：p7_push 整檔約 1948 s，是全套唯一超過「每片每 worker 份額」的單一
        派工單位。不細分到類別，N=3 的牆鐘仍被它單獨卡住（≥32 分）。"""
        units = dispatch_granularity.suite_dispatch_units(self.tests)
        kids = [k for k in units if k.startswith("test_selfimproving_p7_push.")]
        self.assertGreaterEqual(len(kids), 8, "p7_push 沒有被細分成類別級派工單位")
        self.assertNotIn("test_selfimproving_p7_push", units)

    def test_a_shard_with_no_units_is_an_error_not_an_empty_green_run(self) -> None:
        """分片數大於派工單位數時某片為空：空片「通過」＝CI 設定錯誤卻綠，必須 fail-loud。"""
        n = len(dispatch_granularity.suite_dispatch_units(self.tests)) + 1
        with mock.patch.dict(os.environ, {_ENV: f"{n}/{n}"}), self.assertRaises(ValueError):
            S.restrict(unittest.TestSuite(self.tests), _REAL, _REAL)


class DeferredJudgementTest(unittest.TestCase):
    """全集級判準（skip 天花板／M6／豁免 stale）在分片下的語意。"""

    def test_unsharded_judge_calls_the_real_check(self) -> None:
        """不分片（本機 pre-push、nightly）＝原判準照舊在 runner 內跑，行為與修前相同。"""
        S._LAST = None
        fn = mock.MagicMock(return_value=1)
        self.assertEqual(S.judge(fn, 0, "result"), 1)
        fn.assert_called_once_with("result")

    def test_sharded_judge_defers_and_never_calls_the_check(self) -> None:
        """分片下單片只看得到一部分 skip：判了只會誤紅（M6 集合漂移）或永不紅（天花板）——所以
        延後；延後的去處是 `tools/shard_census.py` 對合併紀錄的判準。"""
        fn = mock.MagicMock(return_value=1)
        with mock.patch.object(S, "_LAST", {"shard": [1, 3]}):
            self.assertEqual(S.judge(fn, 0, "result"), 0)
        fn.assert_not_called()

    def test_run_with_floor_wires_all_four_sites_for_a_sharded_synthetic_real_tree(self) -> None:
        """端到端接線：把「真實樹」換成一棵 3 模組的小樹，分別以 1/2、2/2 經 `run_with_floor`
        真跑——兩片實跑數相加＝全集、各片執行落差為 0、紀錄檔寫出、且不呼叫天花板判準。"""
        tmp = Path(tempfile.mkdtemp(prefix="shard_e2e_"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        self.addCleanup(setattr, S, "_LAST", None)
        skip_method = (
            "\n    @unittest.skip(\"[ENV-DISABLED] shard e2e probe\")\n"
            "    def test_c(self):\n        pass\n"
        )
        for k in range(3):
            stem = f"test_shardfx{os.getpid()}_{k}"
            self.addCleanup(lambda s=stem: sys.modules.pop(s, None))
            body = textwrap.dedent(f"""\
                import unittest


                class T{k}(unittest.TestCase):
                    def test_a(self):
                        self.assertTrue(True)

                    def test_b(self):
                        self.assertTrue({k} != 99)
                """)
            # 只有第 0 個模組帶一支 skip：紀錄檔的 skipped 欄必須真的把它帶出來。
            src = body + (skip_method if k == 0 else "")
            (tmp / f"{stem}.py").write_text(src, encoding="utf-8")
        out = tmp / "records"
        total_run, skipped_ids = 0, []
        for i in (1, 2):
            env = {_ENV: f"{i}/2", S.ENV_OUT: str(out), "AUTOSDD_PARALLEL_TESTS": "0"}
            with mock.patch.dict(os.environ, env), mock.patch.object(R, "_TESTS_DIR", tmp), \
                    mock.patch.object(R, "report_skip_census") as census:
                rc = R.run_with_floor(tmp, 1)
            self.assertEqual(rc, 0)
            census.assert_not_called()
            rec = json.loads((out / f"shard-{i}-of-2.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["tests_run"], len(rec["planned_ids"]))
            total_run += rec["tests_run"]
            skipped_ids += [sid for sid, _why in rec["skipped"]]
        self.assertEqual(total_run, 7)
        self.assertEqual(len(skipped_ids), 1)
        self.assertTrue(skipped_ids[0].endswith(".T0.test_c"), skipped_ids)


class _RecordsMixin:
    """合成三片紀錄的共用載具（真實收集面＋真實切分，只在紀錄內容上動手腳）。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tests = _real_tests()
        cls.units = dispatch_granularity.suite_dispatch_units(cls.tests)
        cls.assign = S.plan(cls.units, 3)
        cls.sha = S.plan_digest(cls.assign)

    def _write(self, d: Path, drop: int | None = None, mutate=None) -> None:
        for i in (1, 2, 3):
            if i == drop:
                continue
            ids = sorted(t.id() for t in self.tests
                         if self.assign[dispatch_granularity.dispatch_key(t)] == i)
            rec = {"shard": [i, 3], "plan_sha": self.sha, "planned_ids": ids,
                   "tests_run": len(ids), "skipped": [[ids[0], "[ENV-DISABLED] x"]]}
            if mutate:
                mutate(i, rec)
            (d / f"shard-{i}-of-3.json").write_text(json.dumps(rec), encoding="utf-8")

    def _dir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="shard_rec_"))
        self.addCleanup(lambda: shutil.rmtree(d, ignore_errors=True))
        return d


class MergeRecordsTest(_RecordsMixin, unittest.TestCase):
    """`tools/lib/suite_shard.py::merge_records` 與 `tools/shard_census.py`：彙總 job 的自檢。"""

    def test_complete_consistent_records_merge_cleanly(self) -> None:
        """正控組：完整、一致的三片紀錄合併後無問題，且 skip 逐筆合併進同一個 result。"""
        d = self._dir()
        self._write(d)
        merged, problems = S.merge_records(d, self.tests)
        self.assertEqual(problems, [])
        self.assertEqual(merged.testsRun, len(self.tests))
        self.assertEqual(len(merged.skipped), 3)

    def test_a_missing_shard_is_a_problem(self) -> None:
        """缺片＝那一片的測試全都沒人跑：必須紅（job 被取消或 artifact 沒上傳時的唯一訊號）。"""
        d = self._dir()
        self._write(d, drop=2)
        self.assertTrue(any("不完整" in p for p in S.merge_records(d, self.tests)[1]))

    def test_a_plan_digest_mismatch_is_a_problem(self) -> None:
        """某片與本機重算的切分摘要不同＝兩邊看到的測試集合或種子檔不同，聯集不可信。"""
        d = self._dir()
        bad = {"plan_sha": "deadbeef0000"}
        self._write(d, mutate=lambda i, rec: rec.update(bad) if i == 1 else None)
        self.assertTrue(any("切分摘要" in p for p in S.merge_records(d, self.tests)[1]))

    def test_overlapping_shards_are_a_problem(self) -> None:
        """同一支測試出現在兩片＝重複跑（浪費）且代表切分機制壞了。"""
        d = self._dir()
        stolen: list[str] = []

        def mutate(i: int, rec: dict) -> None:
            if i == 1:
                stolen.append(rec["planned_ids"][0])
            if i == 2:
                rec["planned_ids"].append(stolen[0])

        self._write(d, mutate=mutate)
        self.assertTrue(any("同時屬於" in p for p in S.merge_records(d, self.tests)[1]))

    def test_a_lost_test_is_a_problem(self) -> None:
        """聯集≠全集（有測試沒被任何一片計畫到）＝它在 CI 上靜默消失，這是分片最該防的失效。"""
        d = self._dir()
        self._write(d, mutate=lambda i, rec: rec["planned_ids"].pop() if i == 3 else None)
        self.assertTrue(any("聯集" in p for p in S.merge_records(d, self.tests)[1]))

    def test_a_shard_that_ran_fewer_tests_than_planned_is_a_problem(self) -> None:
        """P2-2：某片計畫 N 支、實跑 N-1 支且沒有 fixture 層條目可歸因＝有測試靜默沒跑。這是不依賴
        分片 runner 自己 `report_execution_gap` 的第二道：那個呼叫被拿掉，census 仍必須紅。"""
        d = self._dir()
        self._write(d, mutate=lambda i, rec: rec.update(tests_run=rec["tests_run"] - 1)
                    if i == 2 else None)
        problems = S.merge_records(d, self.tests)[1]
        self.assertTrue(any("實跑" in p and "差額" in p for p in problems), problems)

    def test_a_gap_explained_by_a_fixture_level_skip_is_not_a_problem(self) -> None:
        """與 runner 同一條規則：整個 class 被 `setUpClass` 的 SkipTest 吃掉是本 repo 刻意採用的
        合法模式（缺工具的機器）；差額能由 fixture 層條目歸因就不判紅，否則缺工具機器全假紅。"""
        d = self._dir()

        def mutate(i: int, rec: dict) -> None:
            if i == 2:
                rec["tests_run"] -= 3
                rec["skipped"].append(["setUpClass (x.Y)", "[TOOL-ABSENCE] no tool"])

        self._write(d, mutate=mutate)
        self.assertEqual(S.merge_records(d, self.tests)[1], [])

    def test_a_shard_that_ran_more_tests_than_planned_is_a_problem(self) -> None:
        """實跑多於計畫＝跑了不屬於本片的東西（切分與執行對不上），不論有無 fixture 條目都紅。"""
        d = self._dir()
        self._write(d, mutate=lambda i, rec: rec.update(tests_run=rec["tests_run"] + 1)
                    if i == 1 else None)
        self.assertTrue(any("實跑" in p for p in S.merge_records(d, self.tests)[1]))

    def test_shard_census_cli_rejects_missing_argument(self) -> None:
        """薄殼的用法錯誤＝rc 2（與 `_cli_flags` 族一致：不讓缺引數被當成通過）。"""
        import shard_census

        with mock.patch.object(sys, "stderr", new=mock.MagicMock()):
            self.assertEqual(shard_census.main([]), 2)


class CensusMainEndToEndTest(_RecordsMixin, unittest.TestCase):
    """F3／P2-1：`tools/shard_census.py::main([...])` 的 rc 組合。這是「全集級 skip 保護在 CI 上
    仍有人跑」的唯一承重點（skip 天花板、M6 id 集合、豁免表 stale 都是在這裡收斂成 rc），此前
    只有 `merge_records` 與無引數 rc=2 有測試，`main` 的收斂邏輯被整段換成 `return 0` 全套照綠。
    收集用真實收集面（快取一份，避免每條重跑 discovery）；全集級判準以 mock 隔離，使每條測試
    只有一個變因。"""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.suite = unittest.TestSuite(cls.tests)

    def _main(self, d: Path, *, census: int = 0, exempt: list | None = None,
              args: list[str] | None = None):
        """跑 `main`，回 `(rc, census_mock, exempt_mock)`；兩個全集級判準預設回「通過」。"""
        import shard_census

        with mock.patch.object(R, "discover_suite", return_value=self.suite), \
                mock.patch.object(R, "report_skip_census", return_value=census) as c, \
                mock.patch.object(R, "report_windows_skip_tag_exemption_problems",
                                  return_value=exempt or []) as e, \
                mock.patch.object(sys, "stdout", new=mock.MagicMock()), \
                mock.patch.object(sys, "stderr", new=mock.MagicMock()):
            rc = shard_census.main([str(d)] if args is None else args)
        return rc, c, e

    def test_complete_clean_records_pass_and_both_global_judgements_really_run(self) -> None:
        """正控：三片齊全且乾淨 ⇒ rc 0；且兩個全集級判準**確實被呼叫、吃到合併後的結果**
        （把呼叫換成常數 0 的突變會讓 rc 照樣是 0，只有「被呼叫」這條斷言殺得掉它）。"""
        d = self._dir()
        self._write(d)
        rc, census, exempt = self._main(d)
        self.assertEqual(rc, 0)
        census.assert_called_once()
        exempt.assert_called_once()
        merged = census.call_args.args[0]
        self.assertEqual(merged.testsRun, len(self.tests))
        self.assertEqual(len(merged.skipped), 3)
        self.assertIs(exempt.call_args.args[0], merged)
        self.assertEqual(exempt.call_args.kwargs["known_ids"], {t.id() for t in self.tests})

    def test_a_missing_shard_fails_and_skips_the_global_judgements(self) -> None:
        """缺片 ⇒ rc 1（機制自檢先於全集級判準；缺片時合併結果不可信，不該再拿去判）。"""
        d = self._dir()
        self._write(d, drop=3)
        rc, census, exempt = self._main(d)
        self.assertEqual(rc, 1)
        census.assert_not_called()
        exempt.assert_not_called()

    def test_a_duplicated_shard_fails(self) -> None:
        """同一片紀錄出現兩份（artifact 重複／手動複製）⇒ rc 1（片號不全且測試同屬兩片）。"""
        d = self._dir()
        self._write(d, drop=3)
        (d / "shard-2-of-3-dup.json").write_text(
            (d / "shard-2-of-3.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(self._main(d)[0], 1)

    def test_a_plan_digest_mismatch_fails(self) -> None:
        """切分摘要不符＝兩邊看到的測試集合或種子檔不同 ⇒ rc 1。"""
        d = self._dir()
        self._write(d, mutate=lambda i, rec: rec.update(plan_sha="dead00") if i == 1 else None)
        self.assertEqual(self._main(d)[0], 1)

    def test_skip_census_failure_makes_main_fail(self) -> None:
        """skip 天花板／M6 判準回報問題（rc 1）⇒ main 必須 rc 1，不得被吞掉。"""
        d = self._dir()
        self._write(d)
        self.assertEqual(self._main(d, census=1)[0], 1)

    def test_stale_exemption_table_makes_main_fail(self) -> None:
        """豁免表 stale 判準回報問題（非空清單）⇒ main 必須 rc 1，不得被吞掉。"""
        d = self._dir()
        self._write(d)
        self.assertEqual(self._main(d, exempt=["stale exemption x"])[0], 1)

    def _real_census_with(self, d: Path, *, ceiling_problems: list[str], m6_rc: int) -> int:
        """走**真的** `report_skip_census`，只把它的兩個底層判準換成指定結果（天花板問題清單／
        M6 id 集合 rc）——驗 `main` 與 `report_skip_census` 之間的接線，而不只是 mock 的回傳值。"""
        import shard_census

        with mock.patch.object(R, "discover_suite", return_value=self.suite), \
                mock.patch.object(R, "report_windows_skip_tag_exemption_problems",
                                  return_value=[]), \
                mock.patch.object(R.skip_group_policy, "skip_group_census_problems",
                                  return_value=ceiling_problems), \
                mock.patch.object(R.skip_group_policy, "profile_registered", return_value=True), \
                mock.patch.object(R.skip_runtime_report, "report_m6_id_sets",
                                  return_value=m6_rc) as m6, \
                mock.patch.object(sys, "stdout", new=mock.MagicMock()), \
                mock.patch.object(sys, "stderr", new=mock.MagicMock()):
            rc = shard_census.main([str(d)])
        m6.assert_called_once()  # M6 閘門條件（start_dir 即真實樹）在彙總 job 上成立
        return rc

    def test_real_skip_census_ceiling_problem_makes_main_fail(self) -> None:
        """天花板不合格 ⇒ rc 1；同一接線在無問題時 ⇒ rc 0（正控，排除「怎麼都紅」）。"""
        d = self._dir()
        self._write(d)
        over = self._real_census_with(d, ceiling_problems=["skipped 超過天花板"], m6_rc=0)
        self.assertEqual(over, 1)
        self.assertEqual(self._real_census_with(d, ceiling_problems=[], m6_rc=0), 0)

    def test_real_m6_id_set_mismatch_makes_main_fail(self) -> None:
        """M6 id 集合不成立 ⇒ rc 1（計數面對「換一支 test-id 而計數不變」恆綠，集合面才守得住）。"""
        d = self._dir()
        self._write(d)
        self.assertEqual(self._real_census_with(d, ceiling_problems=[], m6_rc=1), 1)

    def test_usage_error_is_rc_2(self) -> None:
        """無引數／多引數 ⇒ rc 2，不跑 discovery、不被當成通過。"""
        import shard_census

        with mock.patch.object(sys, "stderr", new=mock.MagicMock()):
            self.assertEqual(shard_census.main([]), 2)
            self.assertEqual(shard_census.main(["a", "b"]), 2)


class StalenessAdvisoryTest(unittest.TestCase):
    """F2：分片模式下不發「計時種子可能過期」advisory（`parallel_shard.run_parallel`）。"""

    def _advisory_calls(self, *, sharded: bool) -> int:
        import contextlib
        import io

        import parallel_shard

        class FakeProc:
            returncode = 0

            def __init__(self, *a, **kw) -> None:
                pass

            def communicate(self):
                return json.dumps({"testsRun": 0, "skipped": [], "errors": [], "failures": [],
                                   "unexpectedSuccesses": []}) + "\n", ""

        counts = {f"m{i:02d}": 1 for i in range(parallel_shard._CACHE_PERSIST_MIN_UNITS)}
        last = {"shard": [1, 3]} if sharded else None
        with mock.patch.dict(os.environ, {"AUTOSDD_PARALLEL_TESTS": "1"}), \
                mock.patch.object(S, "_LAST", last), \
                mock.patch.object(parallel_shard.subprocess, "Popen", FakeProc), \
                mock.patch.object(parallel_shard, "adopt_kill_on_close_job"), \
                mock.patch.object(parallel_shard.parallel_timing_cache, "save_live_cache"), \
                mock.patch.object(parallel_shard.parallel_timing_cache, "current_staleness_report",
                                  return_value="種子可能過期") as report, \
                contextlib.redirect_stdout(io.StringIO()):
            parallel_shard.run_parallel(unittest.TestSuite(), _REAL, counts)
        return report.call_count

    def test_unsharded_run_still_raises_the_staleness_advisory(self) -> None:
        """正控：未分片（本機／nightly）時提醒照舊——過期的種子會讓切分與派工變差，不能因此靜音。"""
        self.assertEqual(self._advisory_calls(sharded=False), 1)

    def test_sharded_run_does_not_compare_a_one_third_live_cache_with_the_seed(self) -> None:
        """分片時每片活體快取只含約 1/N 的熱點，與整份種子的 Top-N 重疊率結構上低於門檻 ⇒ 每片每次
        都誤報；久了人會習慣忽略真正的過期訊號。分片模式不得做這項比對。"""
        self.assertEqual(self._advisory_calls(sharded=True), 0)


class _WorkflowTextMixin:
    _WF = _REAL.parents[1] / ".github" / "workflows" / "windows-compat-ci.yml"

    @classmethod
    def _jobs(cls) -> dict:
        import yaml

        return yaml.safe_load(cls._WF.read_text(encoding="utf-8"))["jobs"]


class CensusJobCancellationTest(_WorkflowTextMixin, unittest.TestCase):
    """F1：被取代的舊 run 不得由 cancelled 變 failure。"""

    def test_census_does_not_run_when_the_shard_matrix_was_cancelled(self) -> None:
        """同 ref 連推時舊 run 的分片被 job 層 concurrency 取消（workflow 層 `cancelled()` 仍為
        false），分片紀錄不存在；彙總若照跑會判「缺片」，把舊 run 由 cancelled
        變 failure（假紅，且白燒一台 runner）。matrix 的 `needs.<job>.result` 是聚合值，
        任一 leg 被取消即 'cancelled'。"""
        cond = self._jobs()["windows-unittests-census"]["if"]
        self.assertIn("needs.windows-unittests.result != 'cancelled'", cond)

    def test_census_still_runs_after_a_shard_failure_and_never_on_schedule(self) -> None:
        """不弱化保護：條件仍含 `!cancelled()`（分片失敗時彙總照跑、缺紀錄照判紅），且排程觸發
        （分片 job 被 skip）時不跑；而且不得改成只在全綠時才跑（那會讓失敗片之後沒有彙總判準）。"""
        cond = self._jobs()["windows-unittests-census"]["if"]
        self.assertIn("!cancelled()", cond)
        self.assertIn("github.event_name != 'schedule'", cond)
        self.assertNotIn("success()", cond)
        self.assertNotIn("needs.windows-unittests.result == 'success'", cond)


class CensusJobMatchesShardCollectionConditionsTest(_WorkflowTextMixin, unittest.TestCase):
    """F4／P3-1：彙總 job 為重算切分而做 discovery，收集面必須與分片 job 同條件；且它不跑測試。"""

    @staticmethod
    def _checkout_depth(job: dict):
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/checkout"):
                return step.get("with", {}).get("fetch-depth")
        raise AssertionError("沒有 checkout 步驟")

    @staticmethod
    def _third_party_line(job: dict) -> str:
        lines = [s["run"] for s in job["steps"]
                 if "pip install" in s.get("run", "") and "pyyaml" in s.get("run", "")]
        assert len(lines) == 1, lines
        return " ".join(lines[0].split())

    def test_checkout_depth_and_third_party_deps_are_identical_to_the_shard_job(self) -> None:
        """discovery 結果若依環境而異（淺層 clone 缺歷史、缺第三方相依使模組塌成佔位測試），
        彙總重算的 plan_sha／全集 id 與各片不同 ⇒ 假紅。兩邊逐項對齊，不靠「現在剛好沒依賴」。"""
        jobs = self._jobs()
        shard, census = jobs["windows-unittests"], jobs["windows-unittests-census"]
        self.assertEqual(self._checkout_depth(census), self._checkout_depth(shard))
        self.assertEqual(self._checkout_depth(census), 0)
        self.assertEqual(self._third_party_line(census), self._third_party_line(shard))

    def test_census_job_collects_but_never_executes_tests(self) -> None:
        """F4 的前提：彙總只收集、不跑測試，所以不必備 ruff／舊直譯器／PYENV_ROOT（它們只影響測試
        執行期）。若某天彙總步驟開始跑 runner，這條紅、逼人把那幾項補齊。"""
        census = self._jobs()["windows-unittests-census"]
        runs = [s.get("run", "") for s in census["steps"] if "pip install" not in s.get("run", "")]
        self.assertTrue(any("tools/shard_census.py" in r for r in runs))
        self.assertFalse(any("run_root_unittests" in r or "unittest" in r or "pytest" in r
                             for r in runs), runs)
        self.assertNotIn("PYENV_ROOT", str(census))


class ShardArtifactRetentionTest(_WorkflowTextMixin, unittest.TestCase):
    """F8：分片 job 的 artifact 不留預設 90 天。"""

    def test_every_shard_artifact_sets_a_short_retention(self) -> None:
        """repo 既有「單次 run 診斷物」慣例＝7 天（aisdlc-sdd-ci／fsm-chaos-nightly）；記錄檔與失敗
        明細只供同一 run 消費或當次排錯，每次 push 多留三個 90 天預設檔沒有用途。"""
        uploads = [s for s in self._jobs()["windows-unittests"]["steps"]
                   if str(s.get("uses", "")).startswith("actions/upload-artifact")]
        self.assertEqual(len(uploads), 2)
        for step in uploads:
            self.assertEqual(step["with"].get("retention-days"), 7, step["name"])


class GrowthTripwireTest(_WorkflowTextMixin, unittest.TestCase):
    """F5：成長要有東西出聲。任務是在「CI 逼近 timeout」之前由測試轉紅，而不是等人發現。

    刻度說明（誠實劃界）：以種子權重（本機量測的秒，合計約 23,213 s）為尺。它與 CI 實際牆鐘不是
    同一個單位（CI 實測總工作量約 10,294 s），所以兩個門檻都是**以現況實測錨定的比例外推**，
    不是牆鐘預測；用途是「新增測試或重刷種子後，負載比錨定當下多了 25%」這個事件觸發複核，
    複核的內容是重量測 CI 牆鐘後在本檔重釘錨點（寫 WHY）。"""

    #: 錨定：N=3 時最重一片的種子負載現值 7,737.6 s ⇔ 預期每片 CI 牆鐘約 15～18 分（timeout 35）。
    #: ×1.25 ⇒ 約 19～22.5 分，仍 ≤ timeout 的 65%。超過這個數字＝加片數。
    _SHARD_LOAD_CEILING_S = 9_700
    #: 錨定：macOS 單 runner（不分片）現約 24 分（證據檔 DEF-200-274 Evidence 2〈DEF-200-593〉），
    #: 其 timeout 35、再評觸發條件「逼近 30 分」。種子總量現值 23,212.6 s ⇔ 24 分 ⇒ 30 分對應
    #: 23,212.6×30/24≈29,016 s，取 29,000。超過＝評估把 macOS 也分片（機制平台中立）或重釘錨點。
    _SINGLE_RUNNER_TOTAL_CEILING_S = 29_000

    @classmethod
    def setUpClass(cls) -> None:
        tests = _real_tests()
        cls.units = dispatch_granularity.suite_dispatch_units(tests)
        cls.hints = S.parallel_timing_cache.read_json(S.parallel_timing_cache.SEED_PATH)
        cls.weights = S._weights(cls.units, cls.hints)
        cls.n = len(cls._jobs()["windows-unittests"]["strategy"]["matrix"]["shard"])

    def test_the_heaviest_shard_stays_within_the_anchored_ceiling(self) -> None:
        """(a) 分片數 N 寫死在 matrix 的 `shard: [1, 2, 3]`：測試與種子成長時每片會變重，而 35 分
        timeout 不會跟著變。最重一片超過錨定上限＝該加片數（只改 matrix 清單，N 取自
        strategy.job-total，別處不必動）。"""
        assign = S.plan(self.units, self.n, self.hints)
        loads = [sum(self.weights[k] for k, s in assign.items() if s == i) / 1000
                 for i in range(1, self.n + 1)]
        self.assertLessEqual(
            max(loads), self._SHARD_LOAD_CEILING_S,
            f"N={self.n} 下最重一片種子負載 {max(loads):.0f} s > 錨定上限 "
            f"{self._SHARD_LOAD_CEILING_S} s——該加片數（windows-compat-ci.yml 的 matrix.shard）；"
            "並重量測 CI 牆鐘後視情況重釘本檔錨點")

    def test_total_load_stays_within_the_single_runner_anchor(self) -> None:
        """(b) macOS（與其他不分片的 leg）單 runner 跑全集：靜態算不出牆鐘，但「全集負載比錨定當下
        多 25%」是可機械偵測的事件——現約 24 分、timeout 35，逼近 30 分前就在這裡紅。"""
        total = sum(self.weights.values()) / 1000
        self.assertLessEqual(
            total, self._SINGLE_RUNNER_TOTAL_CEILING_S,
            f"全集種子負載 {total:.0f} s > {self._SINGLE_RUNNER_TOTAL_CEILING_S} s——"
            "不分片的 CI leg（macos-compat-ci 約 24 分／timeout 35）將逼近 30 分："
            "評估把 macOS 也分片，或重量測後重釘錨點並寫 WHY")

    def test_the_shard_count_comes_from_one_place(self) -> None:
        """N 的單一來源＝matrix.shard 清單；env 用 `strategy.job-total`，不得再寫死第二份數字
        （寫死了，加片數時漏改一處就是「聯集≠全集」的假紅或漏跑）。"""
        step = [s for s in self._jobs()["windows-unittests"]["steps"]
                if "AUTOSDD_TEST_SHARD" in s.get("env", {})]
        self.assertEqual(len(step), 1)
        self.assertEqual(step[0]["env"]["AUTOSDD_TEST_SHARD"],
                         "${{ matrix.shard }}/${{ strategy.job-total }}")


class LocalGatesStayUnshardedTest(unittest.TestCase):
    """本機閘門與其他 workflow 不得設分片變數（`tools/lib/suite_shard.py` 檔頭：單機沒有多台
    runner；全集級 skip 判準在未分片時才在 runner 內判）。"""

    _ROOT = _REAL.parents[1]
    _FILES = (
        "tools/git-hooks/pre-push",
        "AutoClaude/tools/local_ci_gate.py", "AutoClaude/tools/local_ci_gate.ps1",
        "AutoClaude/tools/local_ci_gate.sh", "AutoClaude/tools/run_local_nightly.ps1",
        "AutoClaude/tools/run_local_nightly.sh", "AISDLC_SDD/scripts/ci-gate.ps1",
        "AISDLC_SDD/scripts/ci-gate.sh", ".github/workflows/root-infra-ci.yml",
        ".github/workflows/macos-compat-ci.yml",
    )

    def test_no_local_gate_or_other_workflow_sets_the_shard_variable(self) -> None:
        """若 pre-push／nightly 某天被設了 AUTOSDD_TEST_SHARD，本機全套就只跑一片而閘門照綠
        ——那是「有測試從本機閘門消失」，與 CI 分片丟測試同一種失效，只是更難被看見。"""
        # 名單列的必須全部是真實路徑：缺檔即紅（檔被改名或搬走時掃描面不得悄悄縮小）。
        missing = [p for p in self._FILES if not (self._ROOT / p).is_file()]
        self.assertEqual(missing, [], f"掃描面名單含不存在的路徑：{missing}")
        def live_text(p: str) -> str:
            # 註解行（說明文字、paths 清單旁的註記）提到變數名不等於設了它。
            lines = (self._ROOT / p).read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))

        offenders = [p for p in self._FILES if _ENV in live_text(p)]
        self.assertEqual(offenders, [])


class ChildEnvTest(unittest.TestCase):
    """`tools/lib/parallel_shard.py::run_parallel`：worker 子行程不繼承分片參數。"""

    def test_workers_do_not_inherit_the_shard_variables(self) -> None:
        """worker 內若有測試再啟 runner 子行程，繼承 AUTOSDD_TEST_SHARD 會讓它再切一次片
        （子行程 runner 沒有 start_dir 保護）；與拔掉 AUTOSDD_PARALLEL_TESTS 同一理由。"""
        import parallel_shard

        seen: list[dict] = []

        class FakeProc:
            returncode = 0

            def __init__(self, *a, **kw) -> None:
                seen.append(kw["env"])

            def communicate(self):
                return json.dumps({"testsRun": 0, "skipped": [], "errors": [], "failures": [],
                                   "unexpectedSuccesses": []}) + "\n", ""

        env = {_ENV: "1/3", S.ENV_OUT: "x", "AUTOSDD_PARALLEL_TESTS": "1"}
        with mock.patch.dict(os.environ, env), mock.patch.object(
            parallel_shard.subprocess, "Popen", FakeProc
        ), mock.patch.object(parallel_shard, "adopt_kill_on_close_job"):
            parallel_shard.run_parallel(unittest.TestSuite(), _REAL, {"m": 1})
        self.assertTrue(seen)
        for child in seen:
            self.assertNotIn(_ENV, child)
            self.assertNotIn(S.ENV_OUT, child)
            self.assertNotIn("AUTOSDD_PARALLEL_TESTS", child)


if __name__ == "__main__":
    unittest.main()
