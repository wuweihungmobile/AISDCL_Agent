"""run_root_unittests.py — 數量下限釘選的回歸鎖（R10 QA-2，DEF-101-127）。

WHY（測意圖非僅行為）：`python -m unittest discover` 對 0 個測試回 rc=0，
「跑了 0 個測試也算 PASS」是結構性 fail-open——本測試鎖住包裝器的兩條語意：
(1) 低於下限＝紅燈且不執行；(2) 達下限＝執行並回傳真實結果。
並以真 repo 斷言下限釘選對當前樹成立（防 MIN_TESTS 與現況脫節）。
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import io
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_root_unittests  # noqa: E402


def _calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    """回傳 node 子樹內所有「被呼叫函式名為 name」的 `ast.Call`（裸名或屬性存取皆算）。

    刻意只比對名稱、不比對實參：本檔的靜態鎖要防的是「呼叫被搬到守衛之外」，不是
    「呼叫簽章改了」——比對實參會讓「給 dump 多傳一個參數」這種無害改動假紅（原
    字串比對版 `assertIn("dump_failure_detail(result)", src)` 的已知假紅路徑之一）。
    """
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Call)
        and name in (getattr(n.func, "id", None), getattr(n.func, "attr", None))
    ]


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
        """全綠時不得落檔（否則每次成功執行都留下誤導性的 .last_failure.log）。

        本輪改用 AST：原版比的是 `src.index()` **字串位置**、不是 AST 巢狀關係，有
        具體假綠路徑——把落檔呼叫改成無條件、放在守衛**之後**的同一層（守衛裡改做
        別的事），`guard_at < dump_index` 仍成立、斷言全綠，但每一次**全綠**執行都會
        寫出 `.last_failure.log`，正是本測試 docstring 宣稱要防的退化。另有兩條假紅：
        `assertIn` 是純文字存在性比對，一行 `# dump_failure_detail(result)` 註解就能
        餵飽它；而給 dump 多傳一個實參則會讓 `assertIn` 找不到字串。
        改鎖真正的性質：**每一個** `dump_failure_detail` 呼叫都必須位於「失敗才進入」
        的分支子樹內（`if not …wasSuccessful():` 的 body、或反轉寫法 `if …
        wasSuccessful():` 的 orelse）。「不得出現在該分支之外」才是堵住假綠的那一半。

        已實測涵蓋（見本輪 bug-injection 紅綠對照）：守衛後同層無條件落檔（舊鎖全綠、
        本鎖翻紅）、註解冒充呼叫（AST 天生看不到註解）、dump 多傳實參（只比名稱）。
        已實測不涵蓋：把判定式改寫成先存區域變數（`ok = result.wasSuccessful()` 後
        `if not ok:`）——本鎖只認 If 判定式內**直接**出現 `wasSuccessful()` 的形態，
        該改寫會假紅（方向為 fail-closed，訊息已明說要同步更新本鎖）。其他等價改寫未窮舉。
        """
        fn = ast.parse(textwrap.dedent(inspect.getsource(run_root_unittests.run_with_floor)))
        dumps = _calls_named(fn, "dump_failure_detail")
        self.assertTrue(dumps, "run_with_floor 內找不到 dump_failure_detail 呼叫——落檔機制已消失")
        guarded: list[ast.Call] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.If) or not _calls_named(node.test, "wasSuccessful"):
                continue
            negated = isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not)
            failure_branch = node.body if negated else node.orelse
            guarded += [
                call
                for call in dumps
                if any(call in ast.walk(stmt) for stmt in failure_branch)
            ]
        outside = [call.lineno for call in dumps if not any(call is g for g in guarded)]
        self.assertEqual(
            outside,
            [],
            f"第 {outside} 行（相對 run_with_floor 起始）的 dump_failure_detail 呼叫不在"
            "「失敗才進入」的分支內：全綠執行也會落檔。若你把判定式改寫成先存區域變數"
            "（ok = result.wasSuccessful()）等等價形式，本鎖偵測不到，請同步更新本鎖。",
        )


class WindowsNativeVerificationLedgerTest(unittest.TestCase):
    """DEF-101-348 方向① 補完：`report_windows_native_skips()` 只覆蓋「**本次**這幾支
    沒跑」，完全不覆蓋「這批測試**有史以來從未**在原生 Windows 上跑過」——而後者才是
    DEF-101-348 記載的實害（Windows 專屬測試連續多輪全 APPROVE 卻從未真跑）。用瞬時
    警告防跨輪事實結構上不可能成功，故改記正面事實到一份 tracked 帳本。

    WHY（測意圖非僅行為）：這份帳本的價值全繫於四件事，本 class 逐一鎖住——
    (1) 標籤偵測不得誤判（記錄不實的「已原生驗證」比不記錄更糟）；
    (2) 新鮮期判準必須綁**源碼 sha**、不綁日曆（ADR-SD09-011：綁日曆會讓每日重測同一
        份源碼零增益、空轉數週），且同一份源碼＋同 commit 重驗不得產生 diff 噪音（噪音
        會讓人開始無視這個檔案，就是 MIN_TESTS 連續 11 輪沒人回填的同一個心理機制）；
    (3) 當前源碼真的有原生驗證證據；
    (4) 本輪新增——帳本必須**平台對稱**：兩平台各寫自己那塊、都讀得到對方那塊、寫自己
        時不碰對方，且 head 前進要更新（那是唯一能量化「對方平台落後多少 commit」的
        事實）。缺這一柱時「Windows 側證據已落後」這筆欠債在真的開機到 Windows 之前
        沒有任何地方看得到——正是使用者質疑「為何切回 Windows 就一堆問題」的結構成因。
    """

    # 帶標籤的三種形態 + 一個「標籤只出現在函式 body 內」的陷阱（本檔
    # ReportWindowsNativeSkipsTest._run_fixture 就是這個形態）。
    _MODULE_SRC = textwrap.dedent(
        '''
        import unittest


        @unittest.skipUnless(False, "[WINDOWS-NATIVE-ONLY] 整個 class 只在原生 Windows 有意義")
        class ClassLevel(unittest.TestCase):
            def test_a(self):
                pass


        class MethodLevel(unittest.TestCase):
            @unittest.skipUnless(False, "[WINDOWS-NATIVE-ONLY] 只有這支")
            def test_tagged(self):
                pass

            def test_plain(self):
                pass

            def _fixture(self):
                return unittest.skipUnless(False, "[WINDOWS-NATIVE-ONLY] 假的 reason")
        '''
    )

    def _fact(self, tid: str, sha: str, *, skipped: bool = False) -> dict[str, object]:
        return {
            "id": tid,
            "file": "tools/tests/test_x.py",
            "source_sha256": sha,
            "skipped_here": skipped,
        }

    def test_tag_detection_ignores_occurrences_outside_decorators(self) -> None:
        """只認 decorator 內的字串常數：若改用整檔字串搜尋，`_fixture` 那行會讓
        `MethodLevel` 全體（含 test_plain）被誤記成「已在原生 Windows 驗證」——本檔
        自己就是這個陷阱的持有者，故此案為機制的存亡條件而非邊角案例。"""
        self.assertEqual(
            run_root_unittests.tagged_decorator_qualnames(self._MODULE_SRC),
            {"ClassLevel", "MethodLevel.test_tagged"},
        )

    def _merge(self, existing: dict, facts: list[dict[str, object]], fp: str,
               head: str | None = "h0", key: str = "win32") -> dict:
        """本檔統一以顯式 head/key 呼叫：帳本本輪起是平台對稱的，靠預設值隱含
        「現在跑在哪個平台」會讓同一支測試在 mac 與 Windows 上驗到不同的區塊。"""
        return run_root_unittests.merge_native_ledger(existing, facts, fp, head, key)

    def _entries(self, ledger: dict, key: str = "win32") -> list[dict]:
        return ledger["platforms"][key]["verified"]

    def test_repeat_verification_of_same_source_changes_nothing(self) -> None:
        """同一份源碼＋同一個 commit 再驗一次＝零新資訊，帳本必須原封不動（連平台
        指紋都不更新）。否則 Windows 每次小版更新都讓這份 tracked 檔產生零資訊量的
        diff。注意 head 相同是前提：head 前進屬資訊量非零的 diff，該更新。"""
        facts = [self._fact("m.C.t", "aaa")]
        first = self._merge({}, facts, "win32 / 10.0.1")
        again = self._merge(first, facts, "win32 / 10.0.2")
        self.assertEqual(first, again, "同一份源碼＋同 commit 重驗不得改動帳本內容（diff 噪音）")

    def test_head_advance_updates_block_because_it_carries_information(self) -> None:
        """head 前進**必須**更新：它是唯一能量化「對方平台落後多少 commit」的事實，
        與被刻意壓抑的平台指紋噪音不同類。若這裡也去噪，dev_start 的 advisory 就會
        永遠報「落後 0」＝假綠（本輪機制的存亡條件）。"""
        facts = [self._fact("m.C.t", "aaa")]
        first = self._merge({}, facts, "win32 / 10.0.1", head="c1")
        after = self._merge(first, facts, "win32 / 10.0.2", head="c2")
        self.assertEqual(after["platforms"]["win32"]["head"], "c2")
        self.assertNotEqual(first, after, "head 前進了帳本卻沒動＝落後量永遠算成 0")

    def test_unknown_head_never_overwrites_a_known_one(self) -> None:
        """head=None（非 git repo／git 不可用）不得把已知的 head 清成未知——用未知
        覆蓋已知是資訊淨損失，且會讓 advisory 從「落後 N」退化成「未知」。"""
        first = self._merge({}, [self._fact("m.C.t", "aaa")], "win32 / 10.0.1", head="c1")
        after = self._merge(first, [self._fact("m.C.t", "bbb")], "win32 / 10.0.2", head=None)
        self.assertEqual(after["platforms"]["win32"]["head"], "c1")

    def test_writing_one_platform_never_touches_the_other(self) -> None:
        """平台對稱帳本的核心不變量：各平台只寫自己那塊。mac 上跑測試不得動到 win32
        區塊（對方平台的原生證據不是本平台能代為宣稱的事實），否則帳本會互相清空、
        「在 A 平台讀 B 平台欠債」這個唯一目的直接歸零。"""
        win = self._merge({}, [self._fact("m.C.t", "aaa")], "win32 / 10.0.1", head="c1")
        both = self._merge(win, [self._fact("m.C.t", "aaa", skipped=True)],
                           "darwin / 24.0", head="c2", key="darwin")
        self.assertEqual(both["platforms"]["win32"], win["platforms"]["win32"],
                         "寫 darwin 區塊時 win32 區塊必須逐位元不變")
        self.assertEqual(both["platforms"]["darwin"]["head"], "c2")
        self.assertEqual(both["platforms"]["darwin"]["verified"], [],
                         "mac 上 Windows 專屬測試必然 skip ⇒ darwin 區塊的 verified 應為空，"
                         "但 head 仍要記（那是 mac 側唯一可量化的欠債事實）")

    def test_schema1_ledger_is_read_as_the_windows_block(self) -> None:
        """向後相容：schema 1（僅頂層 verified、無 head）視為 win32 區塊且 head=None。
        升 schema 不得讓已取得的原生證據一夜歸零（那會讓下一輪誤判「從未驗證」並
        重跑一切）；head 缺席則如實回報未知，不得假裝成某個 commit。"""
        legacy = {"schema": 1, "verified": [
            {"id": "m.C.t", "file": "tools/tests/test_x.py", "source_sha256": "aaa",
             "verified_on": "win32 / 10.0.1"}]}
        block = run_root_unittests.platform_block(legacy, "win32")
        self.assertIsNotNone(block)
        assert block is not None
        self.assertIsNone(block["head"], "schema 1 沒記 head ⇒ 必須是 None（誠實的未知）")
        self.assertEqual(set(run_root_unittests.platform_entries(legacy, "win32")), {"m.C.t"})
        self.assertIsNone(run_root_unittests.platform_block(legacy, "darwin"),
                          "schema 1 只有 Windows 一份，不得憑空生出 darwin 區塊")

    def test_peer_keys_include_canonical_counterpart_even_when_absent(self) -> None:
        """「查無紀錄」本身就是要回報的欠債：對照平台不在帳本裡時仍必須被列出，
        否則第一次跨到新平台時 advisory 會靜默（沉默＝被讀成沒問題＝假綠）。"""
        self.assertEqual(run_root_unittests.peer_platform_keys("win32", []), ["darwin"])
        self.assertEqual(run_root_unittests.peer_platform_keys("darwin", []), ["win32"])
        self.assertEqual(
            run_root_unittests.peer_platform_keys("win32", ["win32", "darwin", "linux"]),
            ["darwin", "linux"],
            "帳本內所有非本平台的鍵都要回報（本平台自己不算對方）",
        )

    def test_source_change_invalidates_old_evidence(self) -> None:
        """源碼一改，舊證據立即失效並被本次的新證據取代（新鮮度綁 sha 的正向表現）。"""
        old = self._merge({}, [self._fact("m.C.t", "aaa")], "win32 / 10.0.1")
        new = self._merge(old, [self._fact("m.C.t", "bbb")], "win32 / 10.0.2")
        entry = self._entries(new)[0]
        self.assertEqual(entry["source_sha256"], "bbb")
        self.assertEqual(entry["verified_on"], "win32 / 10.0.2", "更新時須記下這次的平台指紋")

    def test_partial_run_does_not_erase_other_evidence(self) -> None:
        """合併而非覆寫：缺 powershell/pwsh 的 Windows 機器只跑到一部分標籤測試，
        不得把其他幾支先前確實取得過的原生證據抹掉（跨輪累積才是本帳本的存在理由）。"""
        base = self._merge(
            {}, [self._fact("m.C.a", "aaa"), self._fact("m.C.b", "bbb")], "win32 / 10.0.1"
        )
        after = self._merge(base, [self._fact("m.C.a", "aaa", skipped=True)], "win32 / 10.0.2")
        self.assertEqual({e["id"] for e in self._entries(after)}, {"m.C.a", "m.C.b"})

    def test_gap_is_reported_when_recorded_sha_is_stale(self) -> None:
        """帳本有這支、但 sha 對不上 ⇒ 上次的原生驗證是對舊源碼做的，必須被揭露；
        sha 一致則不得吭聲（綁 sha 的判準：同源碼＝有效證據，不論隔了多久）。"""
        ledger = self._merge({}, [self._fact("m.C.t", "aaa")], "win32 / 10.0.1")
        fresh = run_root_unittests.native_evidence_gaps(
            [self._fact("m.C.t", "aaa", skipped=True)], ledger, native_now=False
        )
        self.assertEqual(fresh, [], "sha 相同即為有效證據，不得因時間流逝而失效")
        stale = run_root_unittests.native_evidence_gaps(
            [self._fact("m.C.t", "zzz", skipped=True)], ledger, native_now=False
        )
        self.assertEqual(len(stale), 1)
        self.assertIn("舊源碼", stale[0], "訊息必須說出「證據對的是舊源碼」才可行動")

    def test_gap_is_reported_when_never_verified(self) -> None:
        """帳本查無此測試＝DEF-101-348 的原始實害（從未真跑），訊息要直說。"""
        gaps = run_root_unittests.native_evidence_gaps(
            [self._fact("m.C.t", "aaa", skipped=True)], {}, native_now=False
        )
        self.assertEqual(len(gaps), 1)
        self.assertIn("從未", gaps[0])

    def test_running_natively_right_now_needs_no_ledger_entry(self) -> None:
        """在原生 Windows 上、且本環境不 skip ⇒ 這支此刻正在真跑，證據新鮮，刻意不查
        帳本：帳本由 runner 在測試跑完後才寫，同一次執行內看到的必然是**上一次**的
        帳本；若這裡也查帳本，任何一次測試檔改動都會製造「同一份源碼要跑兩次才會綠」
        的假紅，而 windows CI 從乾淨 checkout 起跑更是永遠自我修不好（它不會 commit
        帳本）。非原生平台則相反：跑不到就只能靠帳本，查無即為 gap。"""
        facts = [self._fact("m.C.t", "aaa")]
        self.assertEqual(run_root_unittests.native_evidence_gaps(facts, {}, native_now=True), [])
        self.assertEqual(
            len(run_root_unittests.native_evidence_gaps(facts, {}, native_now=False)), 1
        )

    def test_no_tagged_tests_means_no_write(self) -> None:
        """一批測試裡零標籤 ⇒ 沒有正面事實可記，不得動帳本檔。

        這不是假想案例：`RunRootUnittestsTest` 的 fixture 自測會用系統暫存目錄裡的假
        測試走完整條 runner 路徑，短路前實測會把一份 `verified: []` 的**空**帳本寫到
        真正的帳本路徑上（先刪帳本再單跑 `test_at_floor_runs_and_passes` 即重現）——
        自測污染真帳本，等於機制自己毀掉自己要保存的跨輪事實。
        """
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.json"
            self.assertFalse(run_root_unittests.record_native_verification([], target))
            self.assertFalse(target.exists(), "零標籤測試時不得建立／改寫帳本檔")

    def test_every_platform_records_its_own_block(self) -> None:
        """本輪起**兩平台都要寫**（原版只在 `is_native_windows()` 時寫）。

        WHY：mac 側依定義產不出 Windows 專屬測試的正面證據（那幾支必然 skip、verified
        會是空的），但 mac 這塊的 head 本身就是「mac 最後一次跑全套在哪個 commit」——
        那是在 Windows 上開工時**唯一**能反向量化 mac 欠債的事實。只寫單邊等於讓不對稱
        永遠只能單向可見，正是使用者質疑「為何切回 Windows 就一堆問題」的結構成因。
        本測試**必須能在 Windows 上抓到守衛被加回來**——這是它的鑑別力所在：只斷言
        「有寫進本平台的鍵」在 Windows 主機上跑時，`is_native_windows()` 恆為 True、
        守衛不會攔任何東西，測試會照樣綠（本輪實測確認過這條假綠路徑）。故第二段刻意
        把 `sys.platform` 換成 'darwin' 模擬在 mac 上執行，此時守衛若存在即早退不寫檔。
        """
        fact = self._fact("m.C.t", "aaa", skipped=True)  # skipped ⇒ 不宣稱正面證據
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                wrote = run_root_unittests.record_native_verification([fact], target)
            self.assertTrue(wrote, "有標籤測試時必須落檔（含本平台的 head）")
            ledger = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn(run_root_unittests.platform_key(), ledger["platforms"])
            self.assertEqual(ledger["schema"], run_root_unittests.NATIVE_LEDGER_SCHEMA)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.json"
            buf = io.StringIO()
            with mock.patch.object(run_root_unittests.sys, "platform", "darwin"), \
                 contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                wrote = run_root_unittests.record_native_verification([fact], target)
            self.assertTrue(
                wrote,
                "模擬 mac 時沒有落檔 ⇒ 只在原生 Windows 寫的守衛回來了：mac 側的 head "
                "從此不再記錄，「在 Windows 上反向讀 mac 欠債」永久失效",
            )
            self.assertIn("darwin", json.loads(target.read_text(encoding="utf-8"))["platforms"])

    def test_corrupt_ledger_degrades_to_rebuild_without_raising(self) -> None:
        """帳本壞掉（非 JSON／被截斷）只印警告後視為空帳本重建，絕不拋——取證輔助
        不得反過來成為 runner 的新失敗來源（同 `_write_failure_log` 的降級哲學）。"""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "ledger.json"
            target.write_text("{ 這不是 JSON", encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                wrote = run_root_unittests.record_native_verification(
                    [self._fact("m.C.t", "aaa", skipped=True)], target
                )
            self.assertTrue(wrote)
            self.assertIn("讀取失敗", buf.getvalue(), "壞帳本必須留下可見的降級訊息")
            self.assertIn("platforms", json.loads(target.read_text(encoding="utf-8")))

    def test_real_repo_tagged_tests_have_current_source_evidence(self) -> None:
        """真樹查核：當前每支標籤測試的**現行源碼**都要有原生 Windows 驗證證據。

        非對稱設計（硬斷言只在原生 Windows 成立、其他平台 advisory）的理由：macOS/
        Linux 上這幾支本來就跑不了，在那裡翻紅只會製造「無法處理的常亮紅燈」，而本
        repo 已實證常亮訊號會退化成背景噪音（MIN_TESTS 連續 11 輪沒人回填）。反之在
        原生 Windows 上「gap 非空」的語意很硬：你就在 Windows 上、這支卻仍被 skip
        （例如缺 powershell/pwsh），且帳本也沒有對得上現行源碼的舊證據 ⇒ 這份源碼
        完全沒有任何原生驗證證據，該擋。
        """
        suite = run_root_unittests.discover_suite(run_root_unittests._TESTS_DIR)
        facts = run_root_unittests.windows_native_tagged_facts(suite)
        self.assertTrue(
            facts,
            f"找不到任何帶 {run_root_unittests.WINDOWS_NATIVE_SKIP_TAG} 標籤的測試"
            "——標籤本身或偵測邏輯已失效（DEF-101-348 的可見度機制整體歸零）",
        )
        ledger_path = run_root_unittests.NATIVE_LEDGER
        self.assertTrue(
            ledger_path.is_file(),
            f"原生驗證帳本 {ledger_path} 不存在——它是 tracked 檔（跨輪累積事實），"
            "被刪除或被 gitignore 都等於整個機制消失",
        )
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        gaps = run_root_unittests.native_evidence_gaps(
            facts, ledger, run_root_unittests.is_native_windows()
        )
        if run_root_unittests.is_native_windows():
            self.assertEqual(
                gaps,
                [],
                "在原生 Windows 上仍有標籤測試取不到原生驗證證據（本次被 skip 且帳本無"
                "對應現行源碼的紀錄）：\n" + "\n".join(gaps),
            )
        elif gaps:
            # advisory：非 Windows 平台不得因此翻紅（見 docstring 的非對稱理由），
            # 但要留下可行動的訊息，讓複審者知道「這幾支的原生驗證是欠著的」。
            print(
                f"⚠️  {len(gaps)} 支 Windows 專屬測試的現行源碼尚無原生驗證證據"
                "（本平台跑不了，僅提醒；請在真 Windows 上跑 tools/run_root_unittests.py）：",
                file=sys.stderr,
            )
            for gap in gaps:
                print(f"   - {gap}", file=sys.stderr)

    def test_facts_are_collected_before_the_suite_is_run(self) -> None:
        """取證必須在 `TestSuite.run()` **之前**：CPython 的 `_removeTestAtIndex` 會把
        跑完的 test 從 `_tests` 釋放成 None，取證若在 run 之後才做會拿到一串 None ⇒
        帳本恆空，且是**靜默的假綠**（沒有紅燈提示）。用 AST lineno 鎖順序（同一函式
        內的直線敘述，lineno 序即執行序），不用字串位置比對——那正是本檔
        `test_only_called_when_run_is_unsuccessful` 本輪要修掉的脆弱形態。"""
        fn = ast.parse(textwrap.dedent(inspect.getsource(run_root_unittests.run_with_floor)))
        facts_calls = _calls_named(fn, "windows_native_tagged_facts")
        run_calls = _calls_named(fn, "run")
        self.assertTrue(facts_calls, "run_with_floor 內沒有呼叫 windows_native_tagged_facts")
        self.assertTrue(run_calls, "run_with_floor 內沒有呼叫 runner 的 .run()")
        self.assertTrue(
            _calls_named(fn, "record_native_verification"),
            "run_with_floor 內沒有落檔呼叫——帳本永遠不會更新",
        )
        self.assertLess(
            max(call.lineno for call in facts_calls),
            min(call.lineno for call in run_calls),
            "取證呼叫落在 suite.run() 之後：run() 已把 test 釋放成 None，取證恆空（靜默假綠）",
        )


if __name__ == "__main__":
    unittest.main()
