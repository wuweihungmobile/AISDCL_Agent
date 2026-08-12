#!/usr/bin/env python3
"""R79：成熟度判準 M1／M5／M6 的**單一定義**、**防稀釋**與**證據面新鮮度**機械物。

被守的是什麼（四筆實測缺陷，逐條對應下面的 class）
--------------------------------------------------
0. **M1 在自己的 SSOT 裡有兩個不等價定義**（R79 四方複審 ARCH blocking，收輪後補）。
   門檻欄只提 UEP／ADR、且是「二擇一」；〈五個收斂條件〉第 1 條卻寫「鎖檔行數不再上升」。
   達標判定走的是門檻欄那一個 ⇒ 寫一段 ADR 宣告 UEP 為終態，M1 就翻成達標，而護欄層
   可以繼續每輪長近兩千行——**「護欄層停止自我增殖」這條判準，可以在護欄層根本沒有
   停止增殖的情況下被滿足**。修法：門檻改成合取（UEP 半 **且** 護欄行數半），
   三處措辭統一，並由 `TestM1ThresholdIsAConjunction` 機械守（刪掉任一半即紅）。
1. **M5 可以靠加語料刷分。** SSOT 開宗明義寫「成熟度的量必須量缺陷穿過幾道閘，不能量
   有幾道閘——後者可以靠新增鎖無限刷分」，並特別點名 M5「加鎖不會讓它上升」。實測是：
   M5 當時的門檻是**比率**，而唯一在守它的棘輪釘的是**絕對攔截數**，分母完全不受任何
   約束 ⇒ 複製十幾題「現行判準本來就攔得到」的語料（語料裡現成就有可抄的），兩個方向
   的比率都能跨門檻、差距也在容許內，而 `test_the_corpus_covers_both_directions_and_
   is_not_shrinking`（題數只准增）、`test_the_interception_rate_only_improves`（攔截數
   只准升）、`test_every_sample_matches_its_recorded_verdict`（判決要相符）**三支全綠**。
   ⇒ 這份專門用來防刷分的文件，自己有一條是可以刷的。

2. **刪難題補簡單題**也能讓數字變好看：既有的 `len(corpus) >= 22` 只看總數，一題換一題
   不會被它看見，而「換掉的是唯一一題攔不到的」與「換掉一題攔得到的」在它眼裡一樣。

3. **M6 的達標判定綁在一份輪次專屬的凍結檔上。** R78 ARCH-05 的整個立論是「活判準不能
   寄生在輪次專屬文件裡，那種文件按定義不會有人回頭維護」；判準表搬了家，M6 的證據面
   沒搬——同一個病只治了上半身。

🔴 為何鎖住的是「**門檻的形狀**」而不是「當下的數字」
----------------------------------------------------
把現在的攔截數字釘進本檔，本檔就會變成第二個會過期的家（那正是 R78 ARCH-05 在治的
病，也是本檔絕不重蹈的）。所以：
  · 數字一律**現跑**（`live_interception()` 是唯一權威來源，本檔 import 它，不抄）；
  · 本檔釘的是**結構**：門檻的量必須是不可稀釋的那一種、已知攔不到的題不得消失、
    M6 的達標語句不得再指向帶輪次號的檔名。
這三件事都是「改了就是真的改了」的形狀，不會因為時間過去而失準。

🔴 為何新增一支檔案而不是併進既有鎖檔（照實寫，同 `test_context_budget_guard.py`）
----------------------------------------------------------------------------------
唯一在守成熟度 SSOT 的既有鎖住在 `test_doc_loc_baseline_freshness_r60.py`——那支檔案
本輪已被獨立判為「雜物抽屜」（5,649 行／32 class／橫跨 R60~R78，檔名只描述其中一小塊）
且由別的包在改。往一個已知過載、且正被別人動的檔案裡再塞一段，是把兩個問題疊在一起。
代價明說：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 逐檔
行數棘輪會因此暫時紅，重釘一律由收尾包在所有包停工後做一次——**不在本包射程內**，
已列入交件回報。這是已知且已回報的狀態，不是漏看。
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SSOT = _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Maturity_Criteria.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_platform_neutral_paths as xplat  # noqa: E402  # 語料與判準的唯一權威來源


def uncaught_ids(corpus=None, hits=None) -> dict[str, set[str]]:
    """兩個方向各自「現在還攔不到」的題號集合——**現算，不是快照**。

    這是 M5 那個不可稀釋的量的實作：抄一題已經攔得到的語料進來，這裡的集合一動也不動。

    兩個參數只給**自證**用（預設一律走現場語料與現場判準）。抽出來的理由：原本
    「稀釋攻擊對本鎖零效果」這條性質是用一個恆真式在斷言的（`len({"u1","u2"}) == 2`），
    改壞 `injection_hits` 的接法也不會紅——判準要走真正的計算路徑才算被考過。
    """
    corpus = xplat._XPLAT_INJECTION_CORPUS if corpus is None else corpus
    hits = xplat.injection_hits if hits is None else hits
    out: dict[str, set[str]] = {}
    for case_id, direction, source, _expected in corpus:
        if not hits(source):
            out.setdefault(direction, set()).add(case_id)
        else:
            out.setdefault(direction, set())
    return out


def uncaught_count(corpus, hits) -> int:
    """兩方向合計的「還攔不到」題數——M5 門檻在量的那一個數字。"""
    return sum(len(ids) for ids in uncaught_ids(corpus, hits).values())


def corpus_ids() -> set[str]:
    return {case_id for case_id, _d, _s, _e in xplat._XPLAT_INJECTION_CORPUS}


#: 判準表的欄序（M1〜M6 五欄）。**逐欄**取值而不是對整列做子字串比對，是本檔第一版
#: 被自己的注入抓到的東西：整列比對時，「門檻欄改回比率」仍會綠——因為「未攔到題數」
#: 這幾個字還留在**量測配方**欄裡。宣稱射程與實作射程不一致，正是 M4 那條在量的東西，
#: 而它當時就長在專門用來守 M5／M6 的這支鎖自己身上。
_COLUMNS = ("criterion", "recipe", "threshold", "owner")


def row_cells(row: str) -> dict[str, str]:
    """把判準表的一列拆成具名欄位。欄數不符一律拋——格式變了要當場說話，不是靜默錯位。"""
    parts = [cell.strip() for cell in row.strip().strip("|").split("|")]
    if len(parts) != len(_COLUMNS) + 1:
        raise AssertionError(
            f"判準表欄數變成 {len(parts)}（預期 {len(_COLUMNS) + 1}）⇒ 逐欄判準會錯位。"
            f"若表格結構真的改了，請同步改本檔的 _COLUMNS：{parts!r}"
        )
    return dict(zip(_COLUMNS, parts[1:], strict=True))


#: R79 當回合現查的「攔不到」題號。這是**下限型**釘選：這些題只准被修好（從集合裡
#: 消失＝有人補了判準），不准整題被刪掉。刻意釘題號而不是題數——題數會被「刪一題難的、
#: 補一題簡單的」騙過去，題號不會。
_R79_KNOWN_UNCAUGHT: frozenset[str] = frozenset({
    "a1-posix-sep-concat", "a2-tmp-hardcode", "a5-chmod-exec",
    "a8-shebang-exec", "a9-lf-only-write",
    "b2-backslash-join", "b4-exe-suffix", "b5-cp950-encoding",
    "b10-case-insensitive",
    # 🔴 R85／ARCH-02 移除 `b8-schtasks` 與 `b11-powershell-shell`：把
    # `scan_foreign_exe_argv` 接進 `_injection_criteria()` 之後這兩題**攔得到了**
    # （語料表那一格已同步改成 True、Win→mac 攔截下限由 6 上修為 8）。
    # 本表留著它們的話，這張釘選表就會與現場脫節而守不到任何東西。
})


def dilution_problems(ids_now: set[str], uncaught_now: set[str],
                      pinned: frozenset[str]) -> list[str]:
    """`[]`＝沒有稀釋。純函式，紅綠由合成注入自證（見 `TestTheCriterionItself`）。

    兩種違規：
      ① 釘選的題號整題消失 ⇒ 「刪掉攔不到的題」也能讓未攔到數變小，而鑑別力不變；
      ② 釘選的題號還在、但它從「攔不到」變成「攔得到」而**沒有人把它從釘選表移除**
         ——這一種**不判紅**（那是進步），只在下面以訊息提醒重釘。所以本函式只回 ①。
    """
    vanished = sorted(pinned - ids_now)
    if not vanished:
        return []
    return [
        f"這些「目前攔不到」的注入題整題從語料裡不見了：{vanished}。"
        "刪掉攔不到的題會讓『還有幾題攔不到』變小，而真實鑑別力一點沒動——"
        "那正是 M5 門檻由比率改成絕對筆數要防的事。要合法移除，請在同一次變更裡"
        "改本檔的 _R79_KNOWN_UNCAUGHT 並在交件裡寫出理由，讓這個決定被複審看見。"
        f"（未使用參數 uncaught_now={len(uncaught_now)} 僅供訊息對照）"
    ]


#: M1 門檻欄的兩半：各自的**必要字樣** ＋「少了這一半會怎樣」。判的是「這一半在不在
#: 門檻欄裡」，不是措辭——換句話說寫沒關係，整半不見才是違規。
_M1_HALVES: dict[str, tuple[tuple[str, ...], str]] = {
    "UEP": (
        ("UEP",),
        "少了它，M1 就不再要求那個自 R65 起連續為 0 的量被正式承認",
    ),
    "護欄行數": (
        ("_FROZEN_GUARD_LINES", "總量"),
        "少了它，只要寫一段 ADR 宣告 UEP 為終態 M1 就翻成達標，而護欄層可以繼續每輪長"
        "近兩千行——「護欄層停止自我增殖」這條判準會在護欄層根本沒有停止增殖時被滿足",
    ),
}
#: 合取標記：門檻必須明說兩半要**同時**成立。
_M1_CONJUNCTION = "合取"
#: 訂正前的字面形態。它出現在門檻欄裡就代表兩半又變回了「達成一半即可」。
_M1_DISJUNCTION_MARK = "二擇一"


def m1_threshold_problems(threshold: str) -> list[str]:
    """M1 門檻欄兩半俱在、且以合取相連嗎？`[]`＝合格。純函式（紅綠由注入自證）。"""
    problems: list[str] = []
    for label, (needles, why) in _M1_HALVES.items():
        missing = [needle for needle in needles if needle not in threshold]
        if missing:
            problems.append(f"門檻欄缺「{label}」這一半（找不到 {missing}）——{why}")
    if _M1_CONJUNCTION not in threshold:
        problems.append(
            f"門檻欄沒有明說兩半是「{_M1_CONJUNCTION}」——兩個條件並排寫著，讀者可以"
            "（而且曾經真的可以）讀成達成其中一個就算數"
        )
    if _M1_DISJUNCTION_MARK in threshold:
        problems.append(
            f"門檻欄又出現「{_M1_DISJUNCTION_MARK}」字樣 ⇒ 回到 R79 訂正前的形態"
        )
    return problems


class TestM1ThresholdIsAConjunction(unittest.TestCase):
    """M1 的門檻必須同時要求 UEP 與護欄行數兩半（刪掉任一半即紅）。

    🔴 被守的缺陷（R79 四方複審 ARCH blocking）：M1 在**自己的 SSOT 裡**有兩個不等價
    定義——門檻欄只提 UEP／ADR，〈五個收斂條件〉第 1 條卻寫「鎖檔行數不再上升」。
    後果不是措辭不一致，是**達標判定會走門檻欄那一個**：寫一段 ADR 宣告 UEP 為終態，
    M1 就翻成達標，而護欄層可以繼續每輪長近兩千行。也就是說，「護欄層停止自我增殖」
    這條判準可以在護欄層根本沒有停止增殖的情況下被滿足。

    形狀刻意照抄本檔守 M5 的那兩支：釘**門檻的形狀**（哪一半必須被寫進去），
    不釘任何當下的數字——數字一律現跑（`--print-guard-lines`）。
    """

    #: 本檔另外兩處會述及 M1 達標條件的地方。同一條判準在同一份 SSOT 裡分頭演化，
    #: 正是這一筆的本體，所以「三處講同一件事」也要有機械物，不能靠人記得一起改。
    _ECHO_ROWS = (
        ("〈五個收斂條件〉第 1 條", "| 1 |", ("_FROZEN_GUARD_LINES", "總量")),
        ("〈現況總判〉M1 那一列", "| M1 |", ("護欄",)),
    )

    def setUp(self) -> None:
        self.text = _SSOT.read_text(encoding="utf-8-sig")
        self.m1_row = next(ln for ln in self.text.splitlines() if "**M1**" in ln)
        self.cells = row_cells(self.m1_row)

    def test_the_threshold_column_demands_both_halves(self) -> None:
        problems = m1_threshold_problems(self.cells["threshold"])
        self.assertEqual(problems, [], "M1 門檻欄：" + "；".join(problems))

    def test_deleting_either_half_is_red(self) -> None:
        """注入（對**現行門檻欄的真實內容**做）：拿掉任一半，本鎖必須指名那一半轉紅。

        同時買到「表內沒有空轉的格子」——每一半都真的對現行文字生效。
        """
        threshold = self.cells["threshold"]
        for label, (needles, _why) in _M1_HALVES.items():
            with self.subTest(half=label):
                injected = threshold
                for needle in needles:
                    injected = injected.replace(needle, "")
                problems = m1_threshold_problems(injected)
                self.assertTrue(
                    any(label in problem for problem in problems),
                    f"拿掉「{label}」這一半之後本鎖仍未指名它 ⇒ 該半零鑑別力（實得：{problems}）",
                )

    def test_the_pre_r79_wording_is_red(self) -> None:
        """掃描器自檢：餵進訂正前的門檻原文必須命中，否則上面那條是恆真的。

        下面這段字串是**掃描器的輸入**，不是本檔對現況的任何宣稱（同 M6 那支自檢的體例）。
        """
        before = ("二擇一：§8.1 出現回執且 UEP 較現值少 1；**或** ADR 正式宣告現值為終態"
                  "並把 _EXEMPT_PAIRS 凍成 shrink-only、不再列為「目標」")
        problems = m1_threshold_problems(before)
        self.assertTrue(
            any("護欄行數" in problem for problem in problems),
            f"掃描器認不出「整格沒提護欄行數」的原始缺陷形態 ⇒ 本鎖恆綠：{problems}",
        )
        self.assertTrue(
            any(_M1_DISJUNCTION_MARK in problem for problem in problems),
            f"掃描器認不出「{_M1_DISJUNCTION_MARK}」這個原始字面形態：{problems}",
        )

    def test_a_conforming_threshold_is_green(self) -> None:
        """對照組：合格的門檻不得被判紅——否則本鎖只是「一律判紅」（同樣沒有鑑別力）。"""
        good = ("兩半必須同時成立（合取）。①UEP 半：§8.1 出現回執且 UEP 較現值少 1。"
                "②護欄行數半：sum(_FROZEN_GUARD_LINES.values()) 這個總量連續三輪不上升")
        self.assertEqual(m1_threshold_problems(good), [])

    def test_the_other_two_statements_of_m1_say_the_same_thing(self) -> None:
        """本檔內另外兩處述及 M1 達標條件的地方必須與門檻欄同義（不得各自演化）。"""
        for label, prefix, needles in self._ECHO_ROWS:
            with self.subTest(row=label):
                row = next(
                    (ln for ln in self.text.splitlines() if ln.startswith(prefix)), None)
                self.assertIsNotNone(
                    row, f"{label} 找不到（開頭 {prefix!r}）——表格結構已變動，"
                         "本鎖不得以「抽不到」靜默放行")
                assert row is not None
                for needle in needles:
                    self.assertIn(
                        needle, row,
                        f"{label} 沒提到「{needle}」⇒ M1 又在同一份 SSOT 裡長出第二個"
                        "不等價定義（而達標判定會走門檻欄那一個）",
                    )


class TestM5ThresholdIsNotDilutable(unittest.TestCase):
    """M5 的門檻必須是「還有幾題攔不到」，不是比率。"""

    def setUp(self) -> None:
        self.text = _SSOT.read_text(encoding="utf-8-sig")
        self.m5_row = next(ln for ln in self.text.splitlines() if "**M5**" in ln)
        self.cells = row_cells(self.m5_row)

    def test_the_threshold_column_names_the_undilutable_quantity(self) -> None:
        """注入：把**門檻欄**寫回「兩方向皆 ≥80%」即紅（那是可稀釋的量）。"""
        self.assertIn(
            "未攔到題數", self.cells["threshold"],
            "M5 的門檻沒有指名「未攔到題數」⇒ 它又變回可以靠加語料刷分的比率門檻。"
            "R79 實測：補十幾題現行判準已經攔得到的語料，兩向比率都能跨門檻而三支鎖全綠",
        )

    def test_the_row_says_the_ratio_is_no_longer_the_gate(self) -> None:
        """比率可以留著當輔助顯示，但**門檻欄**必須明說它不是達標依據。"""
        self.assertIn("不再是達標依據", self.cells["threshold"])

    def test_the_row_still_names_its_carrier(self) -> None:
        """本檔不得把 R78 已經守住的性質弄丟（數字只能來自載具）。"""
        self.assertIn("TestXplatInjectionMatrix", self.m5_row)

    def test_the_false_claim_was_corrected_in_place(self) -> None:
        """SSOT 裡那句「加鎖不會讓它上升」對當時的 M5 為假，不得原封不動留著。

        樹裡不留假句子——下一個人 grep 到它會以為那是現行說法（本 repo 既有判例）。
        """
        self.assertNotIn("加鎖不會讓它上升", self.text)
        self.assertIn("R79 訂正", self.text)


class TestKnownUncaughtSamplesCannotVanish(unittest.TestCase):
    """已知攔不到的那幾題只准被修好，不准被刪掉。"""

    def test_every_pinned_sample_still_exists(self) -> None:
        self.assertEqual(dilution_problems(corpus_ids(), set(), _R79_KNOWN_UNCAUGHT), [])

    def test_the_pin_still_describes_reality(self) -> None:
        """釘選表與現場一致性檢查。

        不一致時**不是**紅在「有人補了判準」（那是進步，訊息會說怎麼重釘），而是紅在
        「釘選表已經與現場脫節」——脫節的釘選表守不到任何東西，正是本 repo 的既有病。
        """
        live = {case for ids in uncaught_ids().values() for case in ids}
        newly_caught = sorted(_R79_KNOWN_UNCAUGHT - live)
        self.assertEqual(
            newly_caught, [],
            f"這些題現在攔得到了：{newly_caught}。這是好事——請把它們從本檔的 "
            "_R79_KNOWN_UNCAUGHT 移除（並依既有紀律把語料表那一格改成 True），"
            "否則這張釘選表會與現場脫節而守不到任何東西",
        )
        unregistered = sorted(live - _R79_KNOWN_UNCAUGHT)
        self.assertEqual(
            unregistered, [],
            f"語料裡多了攔不到的新題卻沒登記進 _R79_KNOWN_UNCAUGHT：{unregistered}。"
            "登記新的危害類是好事、且不會讓任何門檻變難——但沒登記的題不受本鎖保護，"
            "下一輪可以被無聲刪掉",
        )


class TestTheCriterionItself(unittest.TestCase):
    """判準自證：不靠語料現況剛好是哪一種（少了這一組，上面兩類可能恆綠）。"""

    def test_deleting_a_pinned_sample_is_red(self) -> None:
        pinned = frozenset({"x1", "x2"})
        problems = dilution_problems({"x1"}, set(), pinned)
        self.assertEqual(len(problems), 1)
        self.assertIn("x2", problems[0])

    def test_keeping_every_pinned_sample_is_green(self) -> None:
        pinned = frozenset({"x1", "x2"})
        self.assertEqual(dilution_problems({"x1", "x2", "x3"}, set(), pinned), [])

    #: 合成語料的兩種來源字串與對應的合成判準（只有 `_CAUGHT_SRC` 會被「攔到」）。
    _CAUGHT_SRC = "SOURCE-THAT-THE-CRITERIA-ALREADY-CATCH"
    _MISSED_SRC = "SOURCE-THAT-NOTHING-CATCHES"

    @classmethod
    def _synthetic_hits(cls, source: str) -> list[str]:
        return ["syn"] if source == cls._CAUGHT_SRC else []

    def test_adding_already_caught_samples_moves_nothing(self) -> None:
        """本鎖的核心性質：稀釋攻擊對它零效果。

        合成一個「加了 18 題已經攔得到的語料」的世界，並讓數字**真的走
        `uncaught_ids()` 那條計算路徑**算出來——題數變大、未攔到題數不變。

        🔴 R79 四方複審（QA nonblocking）訂正：本支原本的第二個斷言是
        `len({"u1", "u2"}) == 2`——一個恆真式，卻掛著「本鎖的核心性質」的名義。
        它對 `uncaught_ids()` 被改壞（例如把命中判斷接反）零訊號，而那正是 M5 這條
        判準唯一的計算路徑。現改為兩向對照：稀釋不得讓數字動、補一題真的攔不到的
        則**必須**讓它動 1（少了後者，前者可以靠「這個數字恆為常數」滿足）。
        """
        base = (("u1", "d1", self._MISSED_SRC, False),
                ("c1", "d1", self._CAUGHT_SRC, True))
        diluted = base + tuple(
            (f"easy{i}", "d1", self._CAUGHT_SRC, True) for i in range(18))
        plus_hard = base + (("u2", "d2", self._MISSED_SRC, False),)

        n_base = uncaught_count(base, self._synthetic_hits)
        self.assertEqual(n_base, 1, "合成語料本身就算錯了 ⇒ 下面兩條比較沒有意義")
        self.assertEqual(
            uncaught_count(diluted, self._synthetic_hits), n_base,
            "加了 18 題已經攔得到的語料之後，「還攔不到幾題」變了 ⇒ M5 的門檻仍可被稀釋",
        )
        self.assertEqual(
            uncaught_count(plus_hard, self._synthetic_hits), n_base + 1,
            "補一題真的攔不到的，數字卻沒動 ⇒ 這個量對鑑別力的變化沒有反應，"
            "上一條就會是「常數等於常數」那種恆真式（本支被訂正前的樣子）",
        )
        # dilution_problems 不得因為語料變大而誤紅（誤紅會擋住正當的擴充）
        pinned = frozenset({"u1"})
        self.assertEqual(
            dilution_problems({cid for cid, _d, _s, _e in diluted}, set(), pinned), [])


class TestM6EvidenceIsNotParasitic(unittest.TestCase):
    """M6 的達標判定不得再綁在帶輪次號的凍結檔上。"""

    def setUp(self) -> None:
        self.text = _SSOT.read_text(encoding="utf-8-sig")
        self.m6_row = next(ln for ln in self.text.splitlines() if "**M6**" in ln)
        self.cells = row_cells(self.m6_row)

    #: 檔名帶輪次號的形態（例：底線接兩三位輪號）。判的是**形狀**不是某一個檔名，
    #: 所以換一個輪次號的新凍結檔照樣會被抓到。
    #: 🔴 刻意不以反引號寫出示意字面：反引號框住的裸識別字受
    #: `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR78GhostSymbolClaims`
    #: 判定為「必須在符號索引裡找得到定義」，示意用的假名會被判成幽靈符號（R79 實測轉紅）。
    _ROUND_STAMPED = re.compile(r"[A-Za-z_]+_R\d{2,3}(?:\.md)?")

    def test_the_threshold_column_does_not_point_at_a_round_stamped_file(self) -> None:
        """注入：把配方或門檻改回指名 `Skipped_Test_Inventory_R76` 即紅。
        這正是 R78 ARCH-05 為 M1〜M6 修掉、卻漏掉 M6 證據面的那個病。

        射程刻意涵蓋**配方欄＋門檻欄**（不是只有門檻欄）：M6 修復前的病灶在配方欄，
        只守門檻欄會讓原始缺陷狀態照樣綠。
        """
        for column in ("recipe", "threshold"):
            stamped = self._ROUND_STAMPED.findall(self.cells[column])
            self.assertEqual(
                stamped, [],
                f"M6 的 {column} 欄仍指向帶輪次號的檔案 {stamped} ⇒ 達標與否讀的是一份"
                "按定義不會有人回頭維護的凍結記錄。改成「指向現查載具＋當輪 rc」（同 M5 體例）",
            )

    def test_the_threshold_demands_current_round_evidence(self) -> None:
        self.assertIn("當輪", self.cells["threshold"])

    def test_the_criterion_catches_the_pre_r79_wording(self) -> None:
        """掃描器自檢：餵進修復前的原文必須命中，否則上一條是恆綠的。"""
        before = ("| **M6** | ... | `Skipped_Test_Inventory` §4.7.1 的三基線即該形態 "
                  "| 盤點文件內「零覆蓋」欄為 0 | Fixer |")
        self.assertNotEqual(
            self._ROUND_STAMPED.findall(
                before.replace("Skipped_Test_Inventory", "Skipped_Test_Inventory_R76")),
            [], "掃描器認不出帶輪次號的檔名 ⇒ 上面那條判準恆真",
        )


if __name__ == "__main__":
    unittest.main()
