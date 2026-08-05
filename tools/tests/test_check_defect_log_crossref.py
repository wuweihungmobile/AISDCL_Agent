#!/usr/bin/env python3
"""tools/check_defect_log_crossref.py 的單元測試（DEF-101-068(e) 落地：DEF-101-066 這類
「改帳本忘同步姊妹文件」問題類別的機械守護，鏡子自身也要有測試，不可只憑人工複審碰運氣）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import atexit
import io
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_defect_log_crossref as m  # noqa: E402

# 系統暫存目錄放測試用 fixture 檔（非 repo 內），process 結束自動清除，避免污染 tools/tests/。
_TMP_DIR = Path(tempfile.mkdtemp(prefix="crossref_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _write_tmp(text: str) -> Path:
    _tmp_counter[0] += 1
    p = _TMP_DIR / f"fixture_{_tmp_counter[0]}.md"
    p.write_text(text, encoding="utf-8")
    return p


# 主檔《格式定義》§ 狀態的權威散文，**逐字複製**自 docs/06_quality/AutoSDD_Defect_Log.md
# （`TestStatusFirstWordProblems::test_fixture_prose_is_verbatim_from_real_ledger` 會回主檔
# 實查逐行比對：抄錯或主檔改寫即紅，避免這批測試在一個主檔不存在的形態上全綠）。
_STATUS_PROSE_LINE = (
    ">   🔴 **合法首詞**＝`open`／`routed`／`fixed`／`wontfix`／"
    "`closed-by-decision`／`no_action_needed`／`partial`。"
)


def _ledger_text(rows: str, prose: str | None = _STATUS_PROSE_LINE) -> str:
    """組出合成帳本文字；預設**必帶**《格式定義》那句「**合法首詞**＝…。」權威散文。

    🔴 為何 fixture 非得帶那句散文：`status_first_word_problems()` 與該句**雙向綁定**，
    抽不到時是 fail-loud——回一筆「抽不到權威散文」問題並讓 `main()` rc=1，**而不是**
    靜默放行全部列（見主檔 `_prose_status_first_words()` docstring）。所以「只有表頭的
    合成帳本」在這道鎖下不是中性輸入而是**必紅輸入**：R60 加鎖後既有 4 支 `TestMain`
    就是這樣紅的，紅因（抽不到散文）與各自要驗的行為（含糊列分開計數／輪替預警帶）
    毫無關係，屬 fixture 沒跟上主檔演化，不是被驗行為退化。

    `prose=None` 只給「刻意驗證抽不到散文會 fail-loud」那一支測試用。
    """
    header = "# 缺陷帳本\n\n"
    if prose is not None:
        header += prose + "\n\n"
    header += (
        "| ID | 發現日期 | 發現情境 | 現象 | 嚴重度 | 分流去向 | 狀態 |\n"
        "|----|----------|----------|------|--------|----------|------|\n"
    )
    return header + rows


def _row(def_id: str, status: str) -> str:
    """組一列帳本表格列；只有 ID 與**最後一欄**（狀態）有意義，其餘欄位填佔位值。"""
    return f"| {def_id} | 2026-07-28 | 情境 | 現象 | P2 | 去向 | {status} |\n"


class TestClassify(unittest.TestCase):
    def test_leftmost_keyword_wins_when_multiple_present(self) -> None:
        """同一段文字先提 open 再提 fixed（巢狀提及另一 ID）→ 取最早出現者。"""
        text = "存量清理，open；其根因 DEF-101-006 已 fixed@四方複審第三輪"
        self.assertEqual(m._classify(text), "open")

    def test_wontfix_not_confused_with_fixed_substring(self) -> None:
        """wontfix 不含 "fixed" 子字串，兩者須各自獨立判別，不可誤判。"""
        text = "wontfix+凍結版紀律（known-gap）"
        self.assertEqual(m._classify(text), "wontfix")

    def test_no_keyword_returns_none(self) -> None:
        self.assertIsNone(m._classify("純粹的描述文字，不含任何狀態關鍵字"))

    def test_closed_by_decision_detected(self) -> None:
        self.assertEqual(
            m._classify("closed-by-decision（本輪四方複審拍板）"), "closed-by-decision"
        )

    def test_cjk_adjacent_to_status_word_without_separator_still_detected(self) -> None:
        """中文字緊貼英文狀態詞、無空格/標點分隔 → 仍須判讀出來。

        Python re 的 \\b 在預設 Unicode 語意下把 CJK 表意文字也算 word 字元，
        中文字緊貼英文狀態詞時兩側都判定為非邊界，\\b 比對會靜默找不到，
        導致該筆狀態直接從解析結果消失（而非被誤判）——此為回歸鎖。
        """
        self.assertEqual(m._classify("修復後open尚待驗證"), "open")
        self.assertEqual(m._classify("結論fixed，已核實"), "fixed")
        self.assertEqual(m._classify("經routed轉派處理"), "routed")

    def test_status_word_as_substring_of_longer_english_word_not_matched(self) -> None:
        """邊界改用 ASCII 字元類判斷後，仍不可誤判 "reopened"/"unfixed" 這類複合字內的子字串。"""
        self.assertIsNone(m._classify("已reopened"))
        self.assertIsNone(m._classify("unfixed issue"))

    def test_workaround_classified_as_open(self) -> None:
        """R9 跨平台複審詞彙補充：workaround＝流程繞過、程式碼缺陷仍在 → open
        （帳本實例 DEF-101-089 workaround-applied，舊詞彙表辨識不出而成含糊列）。"""
        self.assertEqual(m._classify("**workaround-applied，未改程式碼（本輪範圍判斷）**"), "open")

    def test_no_action_needed_classified_as_closed_by_decision(self) -> None:
        """R9 跨平台複審詞彙補充：no_action_needed／no action needed＝查證後決定
        不需修復 → closed-by-decision（帳本實例 DEF-101-077）。"""
        self.assertEqual(
            m._classify("**no_action_needed（[E31] 查證結果：已落地屬實）**"),
            "closed-by-decision",
        )
        self.assertEqual(m._classify("no action needed（查證結果）"), "closed-by-decision")


class TestLoadLedgerStatus(unittest.TestCase):
    def test_parses_last_column_as_status(self) -> None:
        text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@v0.02（證據…） |\n"
            "| DEF-01-002 | 2026-06-12 | 情境 | 現象 | P3 | 去向 | open（記事存證） |\n"
        )
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            status = m._load_ledger_status()
        self.assertEqual(status["DEF-01-001"], "fixed")
        self.assertEqual(status["DEF-01-002"], "open")

    def test_last_row_wins_on_duplicate_id(self) -> None:
        """理論上 append-only 帳本同 ID 不應重複，若發生則以最後一列為準（視為訂正）。"""
        text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | open（舊列） |\n"
            "| DEF-01-001 | 2026-06-13 | 情境 | 現象 | P2 | 去向 | fixed@訂正列 |\n"
        )
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            status = m._load_ledger_status()
        self.assertEqual(status["DEF-01-001"], "fixed")

    def test_last_row_unclassifiable_does_not_inherit_earlier_row(self) -> None:
        """獨立複審回歸鎖：若『最後一列』狀態欄文字無法辨識任何已知關鍵字，必須視為
        『狀態不明』（None），不可靜默沿用更早一列的舊分類值——舊實作在此情境下會
        因迴圈只在 `label` 為真時才覆寫字典，讓前一列的 fixed 殘留下來，與本函式
        docstring「僅取最後一列」的承諾矛盾（已修正：無論能否分類，一律覆寫）。"""
        text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@第一列 |\n"
            "| DEF-01-001 | 2026-06-13 | 情境 | 現象 | P2 | 去向 | "
            "pending-reassessment（無合法關鍵字） |\n"
        )
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            status = m._load_ledger_status()
        self.assertIn("DEF-01-001", status)
        self.assertIsNone(status["DEF-01-001"])

    def test_non_table_lines_ignored(self) -> None:
        text = _ledger_text("一般敘述文字提到 DEF-01-001 但不是表格列，不應被誤解析\n")
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            status = m._load_ledger_status()
        self.assertEqual(status, {})


class TestScanTarget(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = {"DEF-01-001": "wontfix", "DEF-01-002": "open"}

    def test_mismatch_flagged(self) -> None:
        """帳本實況 wontfix，文件卻宣稱 open → 必須被抓出（DEF-101-066 真實復現形狀）。"""
        target = _write_tmp("某文件敘述 DEF-01-001（open，記事存證）尚待處理。\n")
        problems = m._scan_target(target, self.ledger)
        self.assertEqual(len(problems), 1)
        self.assertIn("DEF-01-001", problems[0])
        self.assertIn("open", problems[0])
        self.assertIn("wontfix", problems[0])

    def test_matching_claim_not_flagged(self) -> None:
        target = _write_tmp("某文件敘述 DEF-01-002（open，記事存證）。\n")
        self.assertEqual(m._scan_target(target, self.ledger), [])

    def test_bare_reference_without_parenthetical_not_flagged(self) -> None:
        """單純引用「見 DEF-01-001」未緊接括號宣稱狀態 → 不誤判，刻意略過。"""
        target = _write_tmp("詳情見 DEF-01-001 的說明段落。\n")
        self.assertEqual(m._scan_target(target, self.ledger), [])

    def test_multi_id_group_claim_checks_each_id(self) -> None:
        """「DEF-01-001／DEF-01-002（open）」一組括號同時宣稱兩個 ID → 各自比對。"""
        target = _write_tmp("條列＝DEF-01-001／DEF-01-002（open）。\n")
        problems = m._scan_target(target, self.ledger)
        # DEF-01-001 實際 wontfix、宣稱 open → 矛盾；DEF-01-002 本就 open → 一致
        self.assertEqual(len(problems), 1)
        self.assertIn("DEF-01-001", problems[0])

    def test_unknown_id_flagged(self) -> None:
        target = _write_tmp("引用 DEF-99-999（open，記事存證）。\n")
        problems = m._scan_target(target, self.ledger)
        self.assertEqual(len(problems), 1)
        self.assertIn("查無此 ID", problems[0])

    def test_ledger_status_none_flagged_distinctly_from_unknown_id(self) -> None:
        """帳本『有這個 ID 但最後一列狀態不明』(None) 與『帳本裡根本沒這個 ID』
        是兩種不同情況，訊息不可混淆（None 不應被誤判為與任何宣稱狀態一致而放行）。"""
        ledger = {"DEF-01-001": None}
        target = _write_tmp("某文件敘述 DEF-01-001（open，記事存證）。\n")
        problems = m._scan_target(target, ledger)
        self.assertEqual(len(problems), 1)
        self.assertIn("狀態欄文字無法辨識", problems[0])
        self.assertNotIn("查無此 ID", problems[0])

    def test_markdown_bold_around_id_still_matches(self) -> None:
        target = _write_tmp("重點：**DEF-01-002**（open，記事存證）。\n")
        self.assertEqual(m._scan_target(target, self.ledger), [])
        target2 = _write_tmp("重點：**DEF-01-001**（open，記事存證）。\n")
        problems = m._scan_target(target2, self.ledger)
        self.assertEqual(len(problems), 1)

    def test_long_parenthetical_over_150_chars_still_flagged(self) -> None:
        """括號內容超過 150 字元的長句敘述仍須被偵測到矛盾（回歸鎖：曾因 _CLAIM_RE 括號
        內容量詞硬性上限 {0,150} 導致超長度的真實宣稱被靜默跳過比對，複審實測 ONBOARDING.md
        DEF-101-057 的括號內容達 186 字元，工具因此完全沒抓到該筆宣稱，帳本狀態即使被刻意
        改成與文件矛盾也不會被回報——本測試以同等長度的長句重現，並鎖住修復後的行為）。"""
        long_claim = (
            "install_post_commit.{sh,ps1} worktree 路徑解析 bug 在 v0.01~v0.29 之殘留，"
            "open，記事存證；本文件先前誤記為某狀態，經機械檢查揪出已訂正；"
            "不佔本表列，因與上方另一筆同源議題已合併敘述於缺陷帳本本身，"
            "此處刻意加長以確保超過 150 字元的舊上限，補足長度用的贅字贅字贅字贅字贅字贅字"
        )
        self.assertGreater(len(long_claim), 150)
        target = _write_tmp(f"某文件敘述 DEF-01-001（{long_claim}）尚待處理。\n")
        problems = m._scan_target(target, self.ledger)
        self.assertEqual(len(problems), 1, "括號內容超長不應導致該筆宣稱被靜默跳過偵測")
        self.assertIn("DEF-01-001", problems[0])


class TestStatusFirstWordProblems(unittest.TestCase):
    """`status_first_word_problems()`（SA-R60R2-06 新增的硬斷言）的正負樣本。

    🔴 落地時這道鎖是**零測試覆蓋**上線的（R60 round 3 實查 `合法首詞`／
    `status_first_word` 在本檔零命中），本類補齊。

    🔴 先釘住概念分野——「含糊」與「首詞非法」是**兩個獨立軸**，本輪逐一實測：

    | 狀態欄文字 | `_classify()` | 首詞 | 合法？ |
    |---|---|---|---|
    | `partial@R60（降級出口）` | `None`（含糊） | `partial` | ✅ |
    | `pending-reassessment（…）` | `None`（含糊） | `pending-reassessment` | ❌ |
    | `partially-fixed@R60` | `fixed`（不含糊） | `partially-fixed` | ❌ |

    第二列同時命中兩軸，所以**不能**拿它當任一軸的 fixture（誰的期望都說不清）；
    第一列是「只驗含糊」該用的樣本，第三列是本鎖真正要擋的形態。
    例外：`TestLoadLedgerStatus::test_last_row_unclassifiable_does_not_inherit_earlier_row`
    刻意留用第二列形態——它只走 `_load_ledger_status()`、不經首詞鎖，要驗的正是
    「連 `_classify` 都完全辨識不出」這種極端，兩軸交疊在那裡無害。
    """

    def test_partially_fixed_is_illegal_though_classify_silently_reads_it_as_fixed(self) -> None:
        """本鎖存在的唯一理由：`partially-fixed` 會被 `_classify` 靜默讀成 `fixed`
        （`-fixed` 對邊界 lookaround 成立），於是「只修了一部分」在跨文件比對眼中
        等於「已修」，而閘門在加鎖前對非法首詞一句話都不說。"""
        # 前提先自證：誤讀確實會發生（若哪天 _classify 改成認不出，本鎖的動機就變了）
        self.assertEqual(m._classify("partially-fixed@R60"), "fixed")
        problems = m.status_first_word_problems(
            _ledger_text(_row("DEF-01-001", "partially-fixed@R60"))
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("partially-fixed", problems[0])
        self.assertIn("不是合法值", problems[0])
        self.assertIn("DEF-01-001", problems[0])
        # 訊息必須列出完整合法清單，讀訊息的人才知道該改成什麼（不是只說「你錯了」）
        for legal in sorted(m._STATUS_FIRST_WORDS):
            self.assertIn(legal, problems[0])

    def test_novel_invented_first_word_is_illegal_so_lock_guards_form_not_one_case(self) -> None:
        """擋的是**形態**（不在宣告集合內就非法），不是 `partially-fixed` 這一個特例：
        隨手新造的 `mostly-fixed@R61` 同樣被擋，且同樣會被 `_classify` 誤讀成 fixed。"""
        self.assertEqual(m._classify("mostly-fixed@R61"), "fixed")
        problems = m.status_first_word_problems(
            _ledger_text(_row("DEF-01-002", "mostly-fixed@R61"))
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("mostly-fixed", problems[0])
        self.assertIn("DEF-01-002", problems[0])

    def test_all_declared_legal_first_words_pass_including_decorated_forms(self) -> None:
        """7 個合法首詞各一列全綠（反樣本，證明這道鎖不是一律紅）；並含 markdown 強調
        與反引號包裝變體——帳本實際寫法大量是 `**fixed@R60**`，若取首詞前不剝裝飾，
        首詞會抽成 None 而整本帳本瞬間全紅，這道鎖就得被迫下架。"""
        rows = (
            _row("DEF-01-001", "open（未分流）")
            + _row("DEF-01-002", "routed（已分流待修）")
            + _row("DEF-01-003", "fixed@R60（附證據）")
            + _row("DEF-01-004", "wontfix+凍結版紀律")
            + _row("DEF-01-005", "closed-by-decision（四方複審拍板）")
            + _row("DEF-01-006", "no_action_needed（查證後確認無需修復）")
            + _row("DEF-01-007", "partial@R60（ADR-XPLAT-001 §4.3.3 降級出口）")
            + _row("DEF-01-008", "**fixed@R60**")
            + _row("DEF-01-009", "`open`（反引號包裝）")
        )
        self.assertEqual(m.status_first_word_problems(_ledger_text(rows)), [])

    def test_decoration_is_actually_stripped_before_taking_first_word(self) -> None:
        """上一測的裝飾變體是真的走過「剝裝飾」這條路才綠的，不是因為別的原因放行。"""
        self.assertEqual(m._status_first_word("**fixed@R60**"), "fixed")
        self.assertEqual(m._status_first_word("`open`（反引號包裝）"), "open")
        self.assertEqual(m._status_first_word("  ＊partial@R60"), "partial")

    def test_prose_missing_a_token_breaks_binding_loudly(self) -> None:
        """散文少一個 token（程式有而散文沒有）→ 必紅，且指名方向與差集。
        走**合成文本**驗證，不動真實主檔。"""
        prose = _STATUS_PROSE_LINE.replace("／`partial`", "")
        self.assertNotEqual(prose, _STATUS_PROSE_LINE, "構造輸入必須真的改到字，否則本測試無意義")
        problems = m.status_first_word_problems(
            _ledger_text(_row("DEF-01-001", "open（未分流）"), prose=prose)
        )
        binding = [p for p in problems if "雙向綁定失效" in p]
        self.assertEqual(len(binding), 1, problems)
        self.assertIn("程式有而散文沒有 ['partial']", binding[0])
        self.assertIn("散文有而程式沒有 []", binding[0])

    def test_prose_extra_token_breaks_binding_loudly_in_the_other_direction(self) -> None:
        """反方向也要紅：散文是權威，但「單方面在散文加詞」也不能讓程式常數默默落後
        （否則綁定只有單向，另一半漂移無聲）。"""
        prose = _STATUS_PROSE_LINE.replace(
            "`partial`。", "`partial`／`pending-reassessment`。"
        )
        self.assertNotEqual(prose, _STATUS_PROSE_LINE, "構造輸入必須真的改到字，否則本測試無意義")
        problems = m.status_first_word_problems(
            _ledger_text(_row("DEF-01-001", "open（未分流）"), prose=prose)
        )
        binding = [p for p in problems if "雙向綁定失效" in p]
        self.assertEqual(len(binding), 1, problems)
        self.assertIn("散文有而程式沒有 ['pending-reassessment']", binding[0])
        self.assertIn("程式有而散文沒有 []", binding[0])

    def test_broken_binding_does_not_switch_off_per_row_checking(self) -> None:
        """把散文改壞**不能**成為關掉整道鎖的捷徑：綁定失效時仍逐列比對，故「散文被
        改壞」與「某列首詞非法」兩個問題必須**同時**出現在回傳清單裡。若實作改成
        「綁定不一致就 return 早退」，本測試只會看到 1 筆而紅。"""
        prose = _STATUS_PROSE_LINE.replace("／`partial`", "")
        problems = m.status_first_word_problems(
            _ledger_text(
                _row("DEF-01-001", "partially-fixed@R60")
                + _row("DEF-01-002", "open（未分流）"),
                prose=prose,
            )
        )
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("雙向綁定失效" in p for p in problems), problems)
        row_problems = [p for p in problems if "不是合法值" in p]
        self.assertEqual(len(row_problems), 1, problems)
        self.assertIn("partially-fixed", row_problems[0])
        self.assertIn("DEF-01-001", row_problems[0])

    def test_effective_set_is_intersection_not_union_when_binding_broken(self) -> None:
        """綁定失效時有效集合取**交集**（最嚴解讀）而非聯集：散文刪掉 `partial` 後，
        即使程式常數仍含 `partial`，`partial@R60` 那列也必須被判非法——若取聯集，
        「改壞散文」反而會放寬逐列檢查，等於獎勵破壞權威源。"""
        prose = _STATUS_PROSE_LINE.replace("／`partial`", "")
        rows = _row("DEF-01-007", "partial@R60（降級出口）")
        problems = m.status_first_word_problems(_ledger_text(rows, prose=prose))
        self.assertEqual(len(problems), 2, problems)
        row_problems = [p for p in problems if "不是合法值" in p]
        self.assertEqual(len(row_problems), 1, problems)
        self.assertIn("DEF-01-007", row_problems[0])
        # 控制組：同一列在散文完好時是合法的 ⇒ 上面的紅確實來自交集收窄，非該列本身有問題
        self.assertEqual(m.status_first_word_problems(_ledger_text(rows)), [])

    def test_missing_prose_fails_loud_with_actionable_message(self) -> None:
        """抽不到那句散文 → 回一筆「抽不到」問題。不得靜默放行全部列（整道鎖蒸發），
        也不得退化成空集合讓每一列都紅得莫名；訊息須帶可執行的修法。"""
        problems = m.status_first_word_problems(
            _ledger_text(
                _row("DEF-01-001", "open（未分流）") + _row("DEF-01-002", "fixed@R60"),
                prose=None,
            )
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("抽不到", problems[0])
        self.assertIn("**合法首詞**＝", problems[0])      # 指出該補回的確切格式
        self.assertIn("_STATUS_PROSE_RE", problems[0])    # 或改抽取樣式這條替代路
        # 不得混入逐列訊息，否則真因（散文不見了）會被 N 筆「首詞不合法」淹沒
        self.assertNotIn("不是合法值", problems[0])

    def test_fixture_prose_is_verbatim_from_real_ledger(self) -> None:
        """本檔 `_STATUS_PROSE_LINE` 必須與主檔那一行**逐字**相同。若憑記憶重打（全形
        `＝`／`／`、🔴、反引號任一處走樣），上面整批測試會在一個主檔根本不存在的形態上
        全綠，而真實帳本的鎖照樣可能是壞的——這正是「載具本身要被驗證」紀律。"""
        real = (m._REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn(_STATUS_PROSE_LINE, real.splitlines())

    def test_real_ledger_has_zero_illegal_first_words(self) -> None:
        """對真實主檔跑一次（零白名單上線的憑證）：存量若有任何非法首詞，這道鎖就得
        帶豁免清單才能上線，而豁免清單會腐化。此測試確保「零白名單」持續成立。"""
        real = (m._REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md").read_text(
            encoding="utf-8-sig"
        )
        self.assertEqual(m.status_first_word_problems(real), [])


# 以下四個常數是 Pkg-P6 的**實測復現輸入**，逐列說明它們各自釘住哪一種形態。
# 前兩列的欄數是**對的**（9 個切片），壞在「狀態欄空白時舊實作把空欄濾掉、`cells[-1]`
# 靜默位移到左鄰的『分流去向』欄」；後兩列相反，是欄數本身對／錯的對照。
#: (a) 狀態欄空白 ＋「分流去向」欄含 `fixed` ⇒ 修復前 `_load_ledger_status()` 回 `fixed`。
_ROW_BLANK_STATUS_FIXED_IN_ROUTING = (
    "| DEF-01-001 | 2026-07-28 | 情境 | 現象 | P2 | 已於上游 fixed 故不另修 |  |\n"
)
#: (b) 最壞複合：狀態欄空白 ＋「分流去向」欄以**合法首詞**開頭 ⇒ 修復前兩道檢查同時零訊號。
_ROW_BLANK_STATUS_LEGAL_WORD_IN_ROUTING = (
    "| DEF-01-002 | 2026-07-28 | 情境 | 現象 | P2 | open 待下輪處理 |  |\n"
)
#: 欄內**未轉義**的字面豎線 ⇒ 多切出一欄（DEF-101-560 的形狀），arity 斷言真正治的形態。
_ROW_UNESCAPED_PIPE = (
    "| DEF-01-003 | 2026-07-28 | 情境 | 現象含字面豎線 a|b | P2 | 去向 | open |\n"
)
#: 對照：豎線**已轉義** ⇒ 欄數正常，兩道檢查都必須放行（反樣本）。
_ROW_ESCAPED_PIPE = (
    "| DEF-01-004 | 2026-07-28 | 情境 | 現象含轉義豎線 a\\|b | P2 | 去向 | open |\n"
)


class TestRowArityAndHeaderAnchoredStatusColumn(unittest.TestCase):
    """欄位切分 arity ＋「狀態欄由表頭定位」（Pkg-P6）的正負樣本。

    🔴 這道修復治的是**本工具自己的假綠面**——它存在的目的就是抓「跨文件假綠」，而它
    自己切欄時寫 `[c.strip() for c in re.split(...) if c.strip()]`：`if c.strip()` 把空欄
    整個濾掉，且全程沒有任何「欄數 == 表頭欄數」的檢查，於是狀態欄留空時 `cells[-1]`
    靜默位移到左鄰的「分流去向」欄。同型漏洞長在照妖鏡自己身上。

    🔴 先釘住一件極容易搞錯的事（`test_arity_check_alone_would_not_have_caught_...`
    坐實）：前兩個復現輸入的**欄數是對的**，所以「只加 arity 斷言」根本抓不到它們；
    真正承重的是「保留空欄 ＋ 由表頭定位狀態欄」。arity 斷言治的是另一種列（欄內未轉義
    字面豎線 ⇒ 欄數變多，DEF-101-560）。兩者互補、缺一不可，不可互相冒充。
    """

    def test_blank_status_cell_no_longer_reads_fixed_out_of_the_routing_column(self) -> None:
        """(a) 狀態欄空白 ＋ 分流去向寫「已於上游 fixed 故不另修」→ 不得回 `fixed`。

        修復前實測 `_load_ledger_status()` 回 `{'DEF-01-001': 'fixed'}`，而該 ID 的狀態欄
        其實**是空的**——一筆沒人填狀態的缺陷會被閘門當成已修，且沒有任何訊號。修復後
        必須是 None（狀態不明），交由 `main()` 以「狀態含糊」warning 呈現。
        """
        text = _ledger_text(_ROW_BLANK_STATUS_FIXED_IN_ROUTING)
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            status = m._load_ledger_status()
        self.assertIn("DEF-01-001", status)
        self.assertIsNone(status["DEF-01-001"], "狀態欄是空的，不得從左鄰欄位借來 'fixed'")
        # 機制自證①：舊寫法（濾掉空欄後取 [-1]）在同一列上真的會把「分流去向」當成狀態欄，
        # 所以上面的 None 是修復的功勞，不是這列本來就抓不到 fixed。
        legacy = [
            c.strip()
            for c in m._CELL_SPLIT_RE.split(_ROW_BLANK_STATUS_FIXED_IN_ROUTING.rstrip("\n"))
            if c.strip()
        ]
        self.assertEqual(m._classify(legacy[-1]), "fixed")
        # 機制自證②：修復後由表頭定位取到的，是真正的（空）狀態欄
        layout = m._table_layout(text)
        self.assertIsNotNone(layout)
        cells = m._row_cells(_ROW_BLANK_STATUS_FIXED_IN_ROUTING.rstrip("\n"))
        self.assertEqual(cells[layout[2]], "")

    def test_blank_status_with_legal_word_in_routing_column_is_no_longer_silent(self) -> None:
        """(b) 最壞複合：狀態欄空白 ＋ 分流去向以合法首詞 `open` 開頭 → 必紅。

        修復前 `status_first_word_problems()` 回 `[]`——首詞鎖看到的「最後一欄」是
        `open 待下輪處理`，首詞 `open` 合法 ⇒ 放行；跨文件比對那邊同樣把它讀成 open ⇒
        **兩道檢查同時完全放行、零訊號**。這是本包要治的核心形態。
        """
        problems = m.status_first_word_problems(
            _ledger_text(_ROW_BLANK_STATUS_LEGAL_WORD_IN_ROUTING)
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("DEF-01-002", problems[0])
        # P6-2：訊息必須明說狀態欄是空的，而不是讓讀者去查左鄰欄位。修復前的訊息會印成
        # 「狀態欄原文開頭：'去向'」——碰巧擋到卻指向錯欄位，比沒擋更危險。
        self.assertIn("是**空的**", problems[0])
        self.assertNotIn("狀態欄原文開頭", problems[0])
        # P6-2：必須帶行號 ＋ 該列切出的**全部**欄位，讓人一眼看出是哪一欄空了
        self.assertIn("帳本 :", problems[0])
        self.assertIn("共 9 個切片", problems[0])
        self.assertIn("#6='open 待下輪處理'", problems[0])   # 分流去向欄，標號 6
        self.assertIn("#7=''", problems[0])                  # 狀態欄，標號 7、空的

    def test_arity_check_alone_would_not_have_caught_the_column_shift(self) -> None:
        """🔴 誠實劃界：上面兩個復現輸入的**欄數是對的**（9 個切片＝表頭欄數），故
        `row_arity_problems()` 對它們回 `[]`——「只加 arity 斷言」（修法甲）抓不到欄位
        位移，承重的是「保留空欄 ＋ 由表頭定位狀態欄」（修法乙）。

        本測試把這條界線釘死：若哪天有人以為 arity 斷言就夠了而拆掉表頭定位，
        `test_blank_status_*` 兩支會紅，而這一支負責解釋「為什麼 arity 綠不代表沒事」。
        """
        for row in (
            _ROW_BLANK_STATUS_FIXED_IN_ROUTING,
            _ROW_BLANK_STATUS_LEGAL_WORD_IN_ROUTING,
        ):
            self.assertEqual(m.row_arity_problems(_ledger_text(row)), [], row)

    def test_unescaped_literal_pipe_row_is_flagged_by_arity_check(self) -> None:
        """arity 斷言真正治的形態（DEF-101-560）：欄內未轉義字面豎線 ⇒ 多切一欄，表頭
        索引指到的就不再是狀態欄。訊息須指名「欄數不符」＋行號＋該列全部欄位。"""
        problems = m.row_arity_problems(_ledger_text(_ROW_UNESCAPED_PIPE))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("切出 10 個切片 ≠ 表頭 9 個", problems[0])
        self.assertIn("帳本 :", problems[0])
        self.assertIn("共 10 個切片", problems[0])
        self.assertIn("未轉義的字面豎線", problems[0])   # 訊息要帶可執行的修法
        # 首詞鎖對同一列也必須報「欄數不符」，而不是掏出一個猜來的首詞裁決
        fw = m.status_first_word_problems(_ledger_text(_ROW_UNESCAPED_PIPE))
        self.assertEqual(len(fw), 1, fw)
        self.assertIn("≠ 表頭", fw[0])
        self.assertNotIn("不是合法值", fw[0])

    def test_escaped_pipe_row_passes_both_checks(self) -> None:
        """反樣本（P6-3.2）：豎線**已轉義**的列欄數正常，arity 斷言不得誤紅。

        主檔實查有 14 列含轉義豎線，這裡若誤紅，整道鎖一上線就會讓整本帳本變紅，
        於是勢必被迫下架或掛豁免清單——反樣本比正樣本更決定這道鎖能不能活著。
        """
        text = _ledger_text(_ROW_ESCAPED_PIPE)
        self.assertEqual(m.row_arity_problems(text), [])
        self.assertEqual(m.status_first_word_problems(text), [])
        # 機制自證：轉義豎線**沒有**被當成分隔符——它必須留在第 4 欄裡面，且該列切出的
        # 欄數與表頭相同。（刻意不寫 `assertIn("\\|", _ROW_ESCAPED_PIPE)`：那只是檢查
        # 同檔上方的字面常數，恆真、對實作零鑑別力。）
        cells = m._row_cells(_ROW_ESCAPED_PIPE.rstrip("\n"))
        self.assertEqual(len(cells), 9)
        self.assertIn("\\|", cells[4])

    def test_normal_seven_column_rows_pass(self) -> None:
        """反樣本：一般 7 欄列（各式合法狀態）全綠，證明這道鎖不是一律紅。"""
        text = _ledger_text(
            _row("DEF-01-001", "open（未分流）")
            + _row("DEF-01-002", "fixed@R60（附證據）")
            + _row("DEF-01-003", "closed-by-decision（四方複審拍板）")
        )
        self.assertEqual(m.row_arity_problems(text), [])
        self.assertEqual(m.status_first_word_problems(text), [])

    def test_missing_header_fails_loud_in_both_functions(self) -> None:
        """表頭抽不到 → 兩支都必須 fail-loud 單筆報錯：既**不得**退回 `cells[-1]` 位置
        猜測（那正是本包修掉的成因），也不得靜默放行全部列（整道鎖蒸發）。"""
        headerless = (
            "# 缺陷帳本\n\n" + _STATUS_PROSE_LINE + "\n\n"
            + _row("DEF-01-001", "partially-fixed@R60")
        )
        self.assertIsNone(m._table_layout(headerless))
        for fn in (m.row_arity_problems, m.status_first_word_problems):
            problems = fn(headerless)
            self.assertEqual(len(problems), 1, (fn.__name__, problems))
            self.assertIn("找不到合格表頭", problems[0])
            self.assertIn("_HEADER_RE", problems[0])       # 指出可執行的修法
            self.assertNotIn("不是合法值", problems[0])    # 真因不得被逐列訊息淹沒

    def test_real_main_ledger_has_zero_arity_problems(self) -> None:
        """對真實主檔跑一次（零白名單上線的憑證，比照
        `TestStatusFirstWordProblems::test_real_ledger_has_zero_illegal_first_words`）。

        🔴 DEF-101-560 具名不修的 archive 側 14 列不在此列——本檔對 archive 只
        `stat()` 量大小、從不解析其表格列（下一支測試把該事實本身釘住）。
        """
        real = (m._REPO_ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md").read_text(
            encoding="utf-8-sig"
        )
        self.assertEqual(m.row_arity_problems(real), [])

    def test_broken_archive_rows_do_not_red_the_main_ledger_gate(self) -> None:
        """DEF-101-560 具名不修的 archive 側 14 列為何不會被本包誤紅：本檔對 archive
        **只 stat() 量大小**、從不解析其表格列。做法＝把一個含欄數異常列的 archive 放在
        合成主檔旁，`main()` 仍須 rc=0 ⇒ 證明「不誤紅」來自「不在解析面內」，而非
        「斷言沒牙」。對照組＝`test_unescaped_literal_pipe_row_is_flagged_by_arity_check`：
        同一種列出現在**主檔**時必紅 ⇒ 那 14 列一旦被搬進主檔就會當場被擋，
        所以這不是對整個檔的靜默豁免。
        """
        d = Path(_TMP_DIR) / "archive_arity_scope"
        d.mkdir(parents=True, exist_ok=True)
        ledger = d / "AutoSDD_Defect_Log.md"
        ledger.write_text(_ledger_text(_row("DEF-01-001", "fixed@R60")), encoding="utf-8")
        (d / "AutoSDD_Defect_Log_archive_98.md").write_text(
            _ledger_text(_ROW_UNESCAPED_PIPE), encoding="utf-8"
        )
        # 前提自證：那份 archive 的內文若真被解析，arity 斷言是會紅的
        self.assertEqual(
            len(m.row_arity_problems(_ledger_text(_ROW_UNESCAPED_PIPE))), 1
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print"):
            self.assertEqual(m.main(), 0)


class TestMain(unittest.TestCase):
    def test_main_returns_1_when_mismatch_found(self) -> None:
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
        )
        target_text = "文件敘述 DEF-01-001（open，記事存證）。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             mock.patch("builtins.print"):
            self.assertEqual(m.main(), 1)

    def test_main_returns_0_when_consistent(self) -> None:
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
        )
        target_text = "文件敘述 DEF-01-001（wontfix，記事存證）。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             mock.patch("builtins.print"):
            self.assertEqual(m.main(), 0)

    def test_a_legal_first_word_can_no_longer_land_in_the_vague_soft_exit(self) -> None:
        """🔴 B5 / SA-R60R3-07：`partial` 這條軟出口已關閉（本測試是舊測試的**繼承者**）。

        舊測試 `test_main_separates_vague_rows_from_valid_count_and_does_not_fail` 拿
        `partial@R60（降級出口）` 當「含糊但首詞合法」的 fixture —— 而**那個 fixture 本身
        就是缺陷**：`partial` 是《格式定義》宣告的合法首詞，卻沒有任何分類器對應，於是
        `_classify` 回 None、該列落進 `main()` 的「狀態含糊」桶，而含糊**只印 warning、
        永不 fail**。DEF-101-556 要消滅的「只修一半被當成已修」並沒有消失，只是從
        「靜默算 fixed」搬到「靜默算含糊」。

        修復後 `partial` 歸類為 `open`（照 `workaround` 判例：缺陷本體仍在＝未結案），
        於是同一份 fixture 的斷言**方向相反**：不再期待 warning，而是期待它被算成一筆
        有效狀態紀錄。連帶的結構後果值得寫下來：合法首詞全部可分類 ＋ 每列首詞必須合法
        ⇒ `main()` 的含糊桶**在結構上不可能被填**。含糊分支保留為第二層防線
        （`_load_ledger_status()` 對欄數不符的列仍記 None），其計數行為由
        `TestVagueBucketCountingStillWorksWhenReached` 以停用新鎖的方式驗。
        """
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
            "| DEF-01-002 | 2026-06-13 | 情境 | 現象 | P3 | 去向 | partial@R60（降級出口） |\n"
        )
        target_text = "文件敘述 DEF-01-001（wontfix，記事存證）。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertNotIn(
            "狀態含糊", printed,
            "`partial` 仍落進 warning-only 的含糊桶 ⇒ SA-R60R3-07 的軟出口沒關上",
        )
        self.assertIn("2 筆有效狀態紀錄", printed,
                      "`partial` 列未被算成有效狀態紀錄 ⇒ 分類器沒有真的接上")
        self.assertEqual(m._classify("partial@R60（降級出口）"), "open",
                         "`partial` 應歸類 open（缺陷本體仍在），照 `workaround` 既有判例")

    def test_main_returns_1_when_status_first_word_illegal(self) -> None:
        """wiring 鎖：純函式有牙不代表 `main()` 真的呼叫了它。本 fixture 刻意讓**跨文件
        比對層完全一致**（帳本 `partially-fixed@R60` 經 `_classify` 判 fixed、文件也宣稱
        fixed），所以唯一能讓 rc=1 的就是首詞鎖——`main()` 哪天漏掉那道呼叫，這裡是唯一
        會紅的地方（其餘 TestMain 案例都仍會綠）。"""
        ledger_text = _ledger_text(_row("DEF-01-001", "partially-fixed@R60"))
        target_text = "文件敘述 DEF-01-001（fixed，已修）。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("首詞不合法", printed)
        self.assertIn("partially-fixed", printed)

    def test_main_returns_1_when_row_arity_mismatched(self) -> None:
        """wiring 鎖（Pkg-P6）：純函式有牙不代表 `main()` 真的呼叫了它。

        🔴 這支的鑑別力靠**訊息前綴**而非只靠 rc：`main()` 的 arity 硬閘印
        「❌ 帳本表格欄位切分結構不合」，而若那道呼叫被刪掉，rc 仍會是 1（因為
        `status_first_word_problems()` 內層也會報同一列的 arity），但前綴會變成
        「❌ 帳本狀態欄首詞不合法」⇒ 下面的 assertIn 會紅。只斷言 rc 的話這道 wiring
        鎖是假的（本測試落地前實測過這條路徑）。
        """
        ledger_text = _ledger_text(
            _row("DEF-01-001", "open（未分流）") + _ROW_UNESCAPED_PIPE
        )
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("欄位切分結構不合", printed)
        self.assertIn("≠ 表頭", printed)
        self.assertIn("DEF-01-003", printed)          # 指名是哪一列

    def test_main_returns_1_when_ledger_missing(self) -> None:
        missing = Path(_TMP_DIR) / "does_not_exist_defect_log.md"
        with mock.patch.object(m, "_DEFECT_LOG", missing), mock.patch("builtins.print"):
            self.assertEqual(m.main(), 1)

    def test_main_fails_when_ledger_exceeds_rotation_limit(self) -> None:
        """DEF-101-123 回歸鎖：主檔 ≥ 256KB（DEF-99-001 輪替界線）必須 fail——
        R9 發現主檔默默長到 272KB 超線，政策先前零機械守門。"""
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@x |\n"
        )
        padded = ledger_text + "> pad\n" * ((m._LEDGER_FAIL_BYTES // 6) + 1)
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(padded)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("輪替上限", printed)

    def test_main_warns_but_passes_when_ledger_approaches_rotation_limit(self) -> None:
        """DEF-101-123：主檔介於 240KB~256KB 之間 → warning 不 fail（預警帶）。"""
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@x |\n"
        )
        base = len(ledger_text.encode("utf-8"))
        pad_bytes = m._LEDGER_WARN_BYTES - base + 100  # 落在預警帶內、未達 fail 線
        padded = ledger_text + "x" * pad_bytes
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(padded)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("逼近輪替上限", printed)

    def _make_isolated_ledger_dir(self, name: str, archive_bytes: int) -> Path:
        """R10 QA-9（DEF-101-138）：archive 守門測試需獨立目錄——archive glob 掃
        `_DEFECT_LOG.parent`，若沿用共用 _TMP_DIR，超線 archive 會污染其他 case。"""
        d = Path(_TMP_DIR) / name
        d.mkdir(parents=True, exist_ok=True)
        ledger = d / "AutoSDD_Defect_Log.md"
        ledger.write_text(
            _ledger_text("| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@x |\n"),
            encoding="utf-8",
        )
        (d / "AutoSDD_Defect_Log_archive_99.md").write_text(
            "x" * archive_bytes, encoding="utf-8"
        )
        return ledger

    def test_main_fails_when_archive_exceeds_limit(self) -> None:
        """R10 QA-9 回歸鎖：archive 檔 ≥ 256KB 必須 fail——R9 補的 archive glob 迴圈
        先前零測試覆蓋（fixture 目錄天然無 archive，迴圈從未被驗證會紅），glob
        pattern / parent 路徑被改壞時主檔測試仍綠、DEF-99-001 政策的一半守門無聲失效。"""
        ledger = self._make_isolated_ledger_dir(
            "archive_fail", m._LEDGER_FAIL_BYTES + 10
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("帳本歸檔", printed)
        self.assertIn("archive_99", printed)

    def test_main_warns_but_passes_when_archive_approaches_limit(self) -> None:
        """R10 QA-9：archive 檔於 240KB~256KB 預警帶 → warning 不 fail。"""
        ledger = self._make_isolated_ledger_dir(
            "archive_warn", m._LEDGER_WARN_BYTES + 100
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("已逼近上限", printed)
        self.assertIn("archive_99", printed)

    def test_main_against_real_repo_is_clean(self) -> None:
        """對真實 repo 現況跑一次（無 mock）——本次修復 DEF-101-056/057 的 ONBOARDING.md
        誤記後，這是防止未來再度漂移而未被察覺的迴歸鎖。"""
        with mock.patch("builtins.print"):
            self.assertEqual(m.main(), 0)


class TestGovernanceDocOversizeGuard(unittest.TestCase):
    """R60 round 3（DEF-101-587）：具名治理文件的體積守門。

    為何需要：本輪把帳本改「兩層化」——帳本列只寫摘要、完整證據落在
    `CrossPlatform_R60_Fix_Evidence*.md`。那些檔於是承擔了與帳本**同等**的可讀性義務
    （四方複審者要逐條重驗就得讀它們），卻**完全不在任何體積守門的涵蓋面內**：實測它
    一度達 260,963 bytes、距 262,144（Read 工具單次讀取上限）僅 1,181 bytes。
    ⇒ **把資料搬到另一支檔就繞過守門**，等於守門只綁在檔名上、沒綁在義務上。
    與 `DEF-99-001`／`DEF-101-123` 同型：政策有上限、卻無機械守門。
    """

    def test_over_limit_fails_with_an_actionable_message(self):
        with tempfile.TemporaryDirectory() as td:
            big = Path(td) / "Over.md"
            big.write_bytes(b"x" * (m._LEDGER_FAIL_BYTES + 1))
            fails, warns = m.oversize_problems([big])
        self.assertEqual((len(fails), len(warns)), (1, 0))
        self.assertIn("Read 工具單次讀取上限", fails[0])
        self.assertIn("拆分", fails[0], "訊息必須告訴人怎麼辦，不能只說『太大了』")

    def test_warn_band_warns_but_does_not_fail(self):
        """與帳本主檔既有語意一致：逼近只警告、rc 不變。"""
        with tempfile.TemporaryDirectory() as td:
            mid = Path(td) / "Warn.md"
            mid.write_bytes(b"x" * (m._LEDGER_WARN_BYTES + 10))
            fails, warns = m.oversize_problems([mid])
        self.assertEqual((len(fails), len(warns)), (0, 1))
        self.assertIn("wc -c", warns[0], "警告必須帶可執行的自保動作")

    def test_normal_size_is_silent(self):
        with tempfile.TemporaryDirectory() as td:
            ok = Path(td) / "Ok.md"
            ok.write_bytes(b"x" * 100)
            self.assertEqual(m.oversize_problems([ok]), ([], []))

    def test_a_missing_named_doc_fails_loud_instead_of_being_skipped(self):
        """涵蓋面與磁碟脫節必須 fail-loud——靜默跳過等於這份檔的守門被悄悄拿掉。"""
        with tempfile.TemporaryDirectory() as td:
            fails, warns = m.oversize_problems([Path(td) / "Missing.md"])
        self.assertEqual((len(fails), len(warns)), (1, 0))
        self.assertIn("涵蓋面已與磁碟脫節", fails[0])

    def test_the_named_set_is_what_bears_the_load(self):
        """中性化：把涵蓋面清空 ⇒ 一切靜默 ⇒ 證明承重的是那個常數、不是別的東西。"""
        self.assertEqual(m.oversize_problems([]), ([], []))
        self.assertTrue(m._GOVERNANCE_DOCS, "涵蓋面為空＝這道守門實際上不存在")

    def test_governance_paths_do_not_ride_on_the_ledger_location(self):
        """治理文件的路徑不得由 `_DEFECT_LOG.parent` 推導。

        落地時實際踩到：原版這樣寫，於是測試把 `_DEFECT_LOG` mock 到暫存目錄時，
        這些檔跟著「搬去」不存在的位置而被判缺席 ⇒ 7 支既有測試假紅。
        治理文件在哪與帳本主檔在哪是兩件事。
        """
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "fake_ledger.md"
            fake.write_text(_ledger_text(""), encoding="utf-8")
            with mock.patch.object(m, "_DEFECT_LOG", fake):
                fails, _ = m.oversize_problems(list(m._GOVERNANCE_DOCS))
        self.assertEqual(fails, [], "mock 帳本位置後治理文件被判缺席 ⇒ 路徑綁錯了來源")

    def test_real_governance_docs_are_within_limit(self):
        fails, _ = m.oversize_problems(list(m._GOVERNANCE_DOCS))
        self.assertEqual(fails, [])


class TestEveryLegalFirstWordIsClassifiable(unittest.TestCase):
    """B5 / SA-R60R3-07：`_STATUS_FIRST_WORDS` 與 `_STATUS_KEYWORDS` 兩份常數硬綁定。

    原始缺陷：`partial` 是合法首詞卻無分類器對應 ⇒ `_classify` 回 None ⇒ 該列落進
    `main()` 的「狀態含糊」桶，而含糊**只印 warning、永不 fail**。零白名單的宣稱字面
    成立（逐條盤點確實沒有任何白名單），但**軟出口**還在，只是換了門牌。

    🔴 為何要立通用鎖而不是只補一個分類器（主控傾向 (b)，本包採「(a)+(b) 都做」）：
      · 只補分類器 ⇒ 修的是這一個實例，下一個新增的合法首詞會走完全一樣的路徑再溜一次；
      · 只加硬斷言 ⇒ 上線當場紅（因為 `partial` 真的沒有分類器），根本無法落地。
    兩者不是二擇一：分類器是**修復**，硬斷言是**防復發**。手法比照本檔既有的
    「散文 ↔ `_STATUS_FIRST_WORDS` 雙向綁定」，串起來即「散文 → 程式常數 → 分類器」全鏈。
    """

    def test_every_legal_first_word_has_a_classifier(self) -> None:
        orphans = sorted(w for w in m._STATUS_FIRST_WORDS if m._classify(w) is None)
        self.assertEqual(
            orphans, [],
            f"合法首詞 {orphans} 沒有分類器對應 —— 這些列會靜默落進 warning-only 的"
            "「狀態含糊」桶（SA-R60R3-07 的形狀）。請補 _STATUS_KEYWORDS 或移除該詞",
        )
        self.assertEqual(m.unclassifiable_first_word_problems(), [],
                         "生產判準函式與上面的獨立算法不一致 ⇒ 其中一邊寫錯了")

    def test_the_lock_fires_on_a_newly_added_word_without_a_classifier(self) -> None:
        """🔴 鑑別力：模擬「未來加了一個合法首詞卻忘了加分類器」——必須當場紅並指名它。

        注入走 runtime monkeypatch（不改 tracked 檔）。刻意用一個**新造**的詞而不是把
        `partial` 拿掉：本鎖要防的是整個類別，不是那一個已修好的實例。
        """
        invented = "half" + "done"
        with mock.patch.object(
            m, "_STATUS_FIRST_WORDS", m._STATUS_FIRST_WORDS | {invented}
        ):
            problems = m.unclassifiable_first_word_problems()
        self.assertEqual(len(problems), 1, f"注入後未報一筆問題：{problems!r}")
        self.assertIn(invented, problems[0], "訊息未逐字指出是哪一個詞 ⇒ 不可行動")
        self.assertIn("永不 fail", problems[0], "訊息必須說明危害（軟出口），不能只說『缺』")
        self.assertEqual(m.unclassifiable_first_word_problems(), [],
                         "monkeypatch 未復原 ⇒ 後續測試會被污染")

    def test_main_returns_1_when_a_legal_first_word_has_no_classifier(self) -> None:
        """wiring 鎖：純函式有牙不代表 `main()` 真的呼叫了它。"""
        ledger_text = _ledger_text(_row("DEF-01-001", "fixed@R60"))
        target_text = "文件敘述 DEF-01-001（fixed，已修）。\n"
        with mock.patch.object(
                m, "_STATUS_FIRST_WORDS", m._STATUS_FIRST_WORDS | {"halfdone"}), \
             mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("合法首詞缺分類器對應", printed)

    def test_partially_fixed_is_still_caught_by_the_first_word_lock_not_the_classifier(
            self) -> None:
        """邊界：補了 `partial` 分類器**不得**順手讓 `partially-fixed` 蒙混過關。

        `partial` 後接 `l` 使 ASCII 邊界 lookahead 不成立 ⇒ `partially-fixed` 不命中新樣式，
        仍由 `_classify` 讀成 `fixed`，而它的歸屬是首詞鎖（整體不在合法集合內 ⇒ 硬紅）。
        兩道鎖分工不變，這正是「補分類器沒有削弱既有守門」的證明。
        """
        self.assertEqual(m._classify("partially-fixed@R60"), "fixed")
        problems = m.status_first_word_problems(
            _ledger_text(_row("DEF-01-001", "partially-fixed@R60")))
        self.assertEqual(len(problems), 1, f"`partially-fixed` 未被首詞鎖擋下：{problems!r}")
        self.assertIn("不是合法值", problems[0])


class TestVagueBucketCountingStillWorksWhenReached(unittest.TestCase):
    """R9 的「含糊列不計入有效狀態紀錄」行為 —— 在**新鎖被停用**的情況下仍須成立。

    🔴 為何要這樣測：B5 落地後「合法首詞 ⇒ 必可分類」，於是 `main()` 的含糊桶在結構上
    不可能被真實帳本填到（首詞非法的列早在前一道硬閘就 rc=1）。若直接刪掉 R9 那支測試，
    等於把一個仍存在的分支變成零覆蓋；若硬造 fixture，又會造出一個現實中不存在的形態。
    折衷＝**把新鎖停用一次**：這同時是 R9 行為的回歸測試，也是 B5 的**反向控制組**
    ——它逐字證明「站在帳本與那個軟出口之間的，就是本輪新加的那道鎖」。
    """

    _LEDGER_TEXT = _ledger_text(
        "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
        "| DEF-01-002 | 2026-06-13 | 情境 | 現象 | P3 | 去向 | partial@R60（降級出口） |\n"
    )
    _TARGET_TEXT = "文件敘述 DEF-01-001（wontfix，記事存證）。\n"

    def _run_main_without_the_partial_classifier(
            self, with_new_lock: bool) -> tuple[int, str]:
        """把 `partial` 從分類器移除（＝缺陷當時的狀態），可選是否保留本輪新加的硬斷言。

        兩組唯一的差別就是 `with_new_lock` 這一個布林值 —— 差異單一，紅綠才歸因得了。
        """
        crippled = dict(m._STATUS_KEYWORDS)
        crippled["open"] = re.compile(
            r"(?<![A-Za-z0-9])open(?![A-Za-z0-9])|workaround")
        lock = (m.unclassifiable_first_word_problems if with_new_lock
                else (lambda: []))
        with mock.patch.object(m, "_STATUS_KEYWORDS", crippled), \
             mock.patch.object(m, "unclassifiable_first_word_problems", lock), \
             mock.patch.object(m, "_DEFECT_LOG", _write_tmp(self._LEDGER_TEXT)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(self._TARGET_TEXT)]), \
             mock.patch("builtins.print") as fake_print:
            rc = m.main()
            printed = " ".join(
                str(arg) for call in fake_print.call_args_list for arg in call.args
            )
        return rc, printed

    def test_without_the_new_lock_the_soft_exit_reappears_and_counts_are_separated(
            self) -> None:
        rc, printed = self._run_main_without_the_partial_classifier(with_new_lock=False)
        self.assertEqual(rc, 0, "缺陷重現組應回 rc=0（軟出口＝只 warning 不 fail）")
        self.assertIn("狀態含糊", printed)
        self.assertIn("DEF-01-002", printed)       # 含糊列 ID 有被列出（R9 要求）
        self.assertIn("1 筆有效狀態紀錄", printed)  # 有效數＝總數 2 − 含糊 1（R9 要求）

    def test_with_the_new_lock_the_same_input_hard_fails(self) -> None:
        """紅向：同一份輸入、同一個殘廢分類器，只把新鎖裝回去 ⇒ rc=1。"""
        rc, _ = self._run_main_without_the_partial_classifier(with_new_lock=True)
        self.assertEqual(
            rc, 1,
            "把新鎖裝回去之後，缺分類器的合法首詞竟仍能靜默通過 ⇒ 本輪的修復沒有牙",
        )


class TestGovernanceDocRegistrationIsComplete(unittest.TestCase):
    """B1 / SA-R60R3-01 的第二半：磁碟上的姊妹治理文件必須全部登記。

    合併兩張清單消掉的是「同一份檔只進了其中一張」；**沒有**消掉「新建一份檔、兩張都沒進」
    ——而 r3 的真實路徑正是後者（有人把證據檔拆成姊妹檔，體積清單記得加、指針清單忘了加）。
    合併之後這條路徑只剩一種形狀（整份檔沒登記），本鎖就守這一種。
    """

    def test_every_sibling_on_disk_is_registered(self) -> None:
        self.assertEqual(
            m.unregistered_governance_docs(), [],
            "磁碟上有符合命名慣例卻未登記的治理文件 —— 未登記＝體積守門與指針稽核同時零覆蓋",
        )

    def test_the_three_named_docs_are_exactly_what_the_glob_finds(self) -> None:
        """雙向：登記面 == 發現面。單向只驗一邊時，多登記一支不存在的檔不會被抓到。"""
        on_disk = {p.name for p in m._GOVERNANCE_DOC_DIR.glob(m._GOVERNANCE_DOC_GLOB)}
        registered = {p.name for p in m._GOVERNANCE_DOCS}
        self.assertEqual(registered, on_disk,
                         "登記面與發現面不一致（登記了不存在的檔，或漏登記磁碟上的檔）")

    def test_an_unregistered_sibling_is_caught_and_named(self) -> None:
        """🔴 鑑別力：從登記面拿掉一支（＝忘了登記），必須當場紅並指名那支檔。"""
        dropped = m._GOVERNANCE_DOCS[-1]
        with mock.patch.object(m, "_GOVERNANCE_DOCS", m._GOVERNANCE_DOCS[:-1]):
            problems = m.unregistered_governance_docs()
        self.assertEqual(len(problems), 1, f"漏登記一支卻未報一筆：{problems!r}")
        self.assertIn(dropped.name, problems[0], "訊息未指名是哪一支檔 ⇒ 不可行動")
        self.assertIn("指針稽核", problems[0],
                      "訊息必須說明未登記同時逸出**兩種**義務，否則讀者只會補其中一張")
        self.assertEqual(m.unregistered_governance_docs(), [], "monkeypatch 未復原")

    def test_main_returns_1_on_an_unregistered_sibling(self) -> None:
        """wiring 鎖：純函式有牙不代表 `main()` 真的呼叫了它。"""
        with mock.patch.object(m, "_GOVERNANCE_DOCS", m._GOVERNANCE_DOCS[:-1]), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("具名治理文件涵蓋面與磁碟脫節", printed)


class TestFamilyHeaderUniformity(unittest.TestCase):
    """B2 / SA-R60R3-02：表頭同形性的斷言對象必須是「具表頭的檔」，且檔數不寫死。

    🔴 兩層錯（主控親自複驗 CONFIRMED）：
      (i)  訂正前本檔散文寫死「帳本家族 32 檔」，而實查家族更多，且每跑一次 `--apply` 就再變；
      (ii) 更重的一層——該句斷言的「表頭欄數全部同形」**只對其中具表格表頭的那些檔成立**，
           家族內另有一批純散文 archive 根本沒有表格。把只對子集成立的性質宣稱到全集上，
           比數字過期更重：讀者會以為「家族每一份檔都有表頭」而據此推論。
    違反的是本輪自己落地的 Scan-H 必跑項 #3（鎖的散文不得寫死可由程式現查的數字）。
    """

    @staticmethod
    def _family_files():
        import archive_defect_log as ADL  # noqa: PLC0415 — 只有本類別需要，避免全檔耦合
        return ADL._family_files()

    def test_files_with_a_header_all_share_the_same_slice_count(self) -> None:
        """正面斷言（現查，不寫死）：具表頭的檔，其表頭切片數全部相同。"""
        counts = {}
        for p in self._family_files():
            layout = m._table_layout(p.read_text(encoding="utf-8-sig"))
            if layout is not None:
                counts.setdefault(layout[0], []).append(p.name)
        self.assertTrue(counts, "家族內一支具表頭的檔都找不到 ⇒ 解析已壞，本鎖無標的")
        self.assertEqual(
            len(counts), 1,
            f"具表頭的檔出現多種切片數 ⇒ 表頭定位對其中一批不安全：{counts}",
        )

    def test_the_property_does_not_hold_for_the_whole_family(self) -> None:
        """🔴 反面斷言：具表頭的檔是家族的**真子集** —— 這正是舊散文說錯的那一層。

        若哪天家族每一份檔都有表頭，本測試會紅；那時該做的是把散文改成「全家族」，
        而不是刪掉這條——它是「當年為什麼要收窄」的活體證據。
        """
        family = self._family_files()
        with_header = [
            p for p in family
            if m._table_layout(p.read_text(encoding="utf-8-sig")) is not None
        ]
        self.assertLess(
            len(with_header), len(family),
            "家族內每一份檔都有表頭了 ⇒ 舊散文那句「家族 N 檔皆為此形態」變成真的，"
            "請把本檔與 check_defect_log_crossref.py 的措辭一併更新（並保留訂正紀錄）",
        )
        self.assertGreater(len(with_header), 0, "零檔具表頭 ⇒ 上一條斷言變成廉價恆真")


#: 「散文寫死家族檔數」的偵測樣式。刻意窄：只認 `家族` 與 `N 檔` 相鄰的那種寫法
#: ——那就是 SA-R60R3-02 實際犯規的形狀。通用的「散文寫死數字」偵測需要語意理解，本鎖不假裝有。
_FAMILY_COUNT_RE = re.compile(r"家族\s*\d+\s*檔")

#: 受本紀律管的原始碼（本包所有權內的四支）。
_SCANNED_SOURCES = (
    Path(__file__).resolve().parents[1] / "check_defect_log_crossref.py",
    Path(__file__).resolve().parents[1] / "archive_defect_log.py",
    Path(__file__).resolve(),
    Path(__file__).resolve().parent / "test_archive_defect_log.py",
)


class TestNoHardcodedFamilyCountInProse(unittest.TestCase):
    """Scan-H 必跑項 #3 的機械化：鎖的散文不得寫死家族檔數（SA-R60R3-02）。

    例外只有一種：**訂正紀錄**。帳本紀律是「原文逐字保全」，訂正註必須能引述當年寫錯的
    那句話；故判準是「該行若同時帶『訂正』字樣即放行」——與
    `TestCriteriaListIsASingleSsot::test_no_stale_criterion_seven_reference_remains_in_the_tool`
    的處理方式一致（同一條紀律，不另創第二種寫法）。
    """

    def test_no_source_hardcodes_the_family_file_count(self) -> None:
        offenders = []
        for src in _SCANNED_SOURCES:
            for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
                if "訂正" in line:
                    continue
                for hit in _FAMILY_COUNT_RE.finditer(line):
                    offenders.append(f"{src.name}:{lineno}：{hit.group(0)!r} ← {line.strip()}")
        self.assertEqual(
            offenders, [],
            "以下散文寫死了家族檔數（可由 `_family_files()` 現查，且每次 `--apply` 就變）：\n  "
            + "\n  ".join(offenders)
            + "\n改法：改成不引數字的寫法（例：「家族檔數以 `_family_files()` 現查為準」），"
              "**不要**把舊數字改成新數字——那只是把過期時點往後挪一輪。"
              "確為訂正紀錄者請在同一行寫上「訂正」。",
        )

    def test_the_detector_fires_on_the_exact_wording_that_was_wrong(self) -> None:
        """注入：把 SA-R60R3-02 逐字抓到的那句餵進偵測器，必須命中。"""
        sample = "# 實查帳本家族 " + str(32) + " 檔的表頭欄數全部同形"
        self.assertTrue(_FAMILY_COUNT_RE.search(sample), "偵測器對真實犯規形態失效")

    def test_the_detector_does_not_flag_the_fixed_wording(self) -> None:
        """對照組：修好之後的寫法不得誤報，否則這道鎖一上線就永紅。"""
        for sample in (
            "# 家族檔數以 `_family_files()` 現查為準",
            "# 帳本家族內具表格表頭的那些檔，其表頭切片數全部同形",
        ):
            with self.subTest(sample=sample):
                self.assertIsNone(_FAMILY_COUNT_RE.search(sample))


class TestEvidenceFamilyPointersResolve(unittest.TestCase):
    """帳本裡「見 `<檔>` 的 `## DEF-101-NNN` 節」必須真的找得到那個錨（DEF-101-587）。

    R60 round 3 把證據檔拆成入口檔＋姊妹檔。拆分**當下**零失實（具名節指針全部 ≤560、
    都留在入口檔），但那是**手驗**的結果——下一次有人再搬一節、或帳本新增一個指向已搬走
    節次的指針，就會靜默失實。本鎖把那次手驗機械化。

    與 `archive_defect_log.py` 判準④／⑥ 的差別：那兩項守的是**帳本家族內**的居所宣稱，
    本項守的是**帳本 → 證據檔**的跨檔錨點。同一個病（指針失實），不同的邊。
    """

    # 🔴 R75：樣式由「只認 R60 那一組檔名」放寬為**任一輪的 `CrossPlatform_R<n>_*.md`**。
    # 原因與 DEF-101-757 同型：兩層化（主檔留摘要＋指針、詳情外置）R60 用過、R68 用過、
    # R75 又用了一次（`CrossPlatform_R75_Review_Evidence.md`，20 個具名節指針），而本鎖的
    # 樣式把輪號寫死 ⇒ 同一種指針換一輪就整批逸出，這正是本鎖要防的「指針靜默失實」。
    # 放寬只擴**發現面**，判準（錨必須真的存在於被指名的那份檔）一字未改。
    _POINTER_RE = re.compile(
        r"`(?P<file>CrossPlatform_R\d+_\w+\.md)`?\s*的\s*"
        r"`## (?P<anchor>DEF-\d+-\d+)`\s*節"
    )

    def test_every_named_section_pointer_resolves(self):
        ledger = m._DEFECT_LOG.read_text(encoding="utf-8-sig")
        pointers = self._POINTER_RE.findall(ledger)
        self.assertTrue(pointers, "帳本內一個具名節指針都抽不到 ⇒ 樣式與現況脫節，本鎖無牙")
        problems = []
        for filename, anchor in pointers:
            target = m._DEFECT_LOG.parent / filename
            if not target.exists():
                problems.append(f"{anchor} → {filename}（檔不存在）")
                continue
            if f"\n## {anchor}\n" not in target.read_text(encoding="utf-8-sig"):
                where = [
                    p.name for p in m._GOVERNANCE_DOCS
                    if p.exists() and f"\n## {anchor}\n" in p.read_text(encoding="utf-8-sig")
                ]
                problems.append(
                    f"{anchor} 宣稱在 {filename}，實際在 {where or '（家族內查無）'}"
                )
        self.assertEqual(
            problems, [],
            "帳本的具名節指針失實——證據檔拆分／搬節後必須同步帳本那一列，"
            "或把該節留在被指名的檔內",
        )

    def test_the_entry_file_routes_to_the_sibling(self):
        """入口檔必須有對照表指路：14 處裸指針只寫檔名，讀者到了要知道往哪走。"""
        entry = next(p for p in m._GOVERNANCE_DOCS if p.name.endswith("Evidence.md"))
        sibling = next(p for p in m._GOVERNANCE_DOCS if p.name.endswith("_r3.md"))
        text = entry.read_text(encoding="utf-8-sig")
        self.assertIn(sibling.name, text, "入口檔沒有提到姊妹檔 ⇒ 拆分後讀者會斷線")

    def test_no_anchor_lives_in_two_files_at_once(self):
        seen = {}
        for p in m._GOVERNANCE_DOCS:
            body = p.read_text(encoding="utf-8-sig")
            for anchor in re.findall(r"^## (DEF-\d+-\d+)$", body, re.M):
                seen.setdefault(anchor, []).append(p.name)
        dupes = {a: fs for a, fs in seen.items() if len(fs) > 1}
        self.assertEqual(dupes, {}, "同一個 DEF-ID 的證據節出現在多份檔 ⇒ 拆分時複製而非搬移")


_SPEC_DOC = m._REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Scan_Dimensions.md"


def _row4(def_id: str, ctx: str, routing: str, status: str) -> str:
    """組一列帳本表格列，四個**有語意**的欄位都可指定（硬規則② 的判定同時吃這四欄）。

    既有的 `_row()` 把「發現情境」「分流去向」寫死成佔位字串，對本節測試不夠用：
    當前輪由「發現情境」欄推得、承接者可寫在「分流去向」或「狀態」欄。
    """
    return f"| {def_id} | 2026-07-31 | {ctx} | 現象 | P2 | {routing} | {status} |\n"


class TestCurrentRoundIsReadofFromTheLedgerNotHardcoded(unittest.TestCase):
    """當前輪次的取值必須是**現查**——寫死常數下一輪就 stale，那正是本鎖要治的病。"""

    def test_current_round_is_the_max_round_in_the_discovery_context_column(self) -> None:
        text = _ledger_text(
            _row4("DEF-01-001", "R7 Scan-A", "去向", "fixed")
            + _row4("DEF-01-002", "R12 Scan-D", "去向", "fixed")
            + _row4("DEF-01-003", "改良會議", "去向", "fixed")
        )
        self.assertEqual(m.current_round(text), 12)

    def test_editing_the_context_column_moves_the_current_round(self) -> None:
        """行為級證明「不是常數」：只改資料、不改程式，判定基準就跟著動。"""
        before = _ledger_text(_row4("DEF-01-001", "R7 Scan-A", "去向", "fixed"))
        after = _ledger_text(_row4("DEF-01-001", "R90 Scan-A", "去向", "fixed"))
        self.assertEqual(m.current_round(before), 7)
        self.assertEqual(m.current_round(after), 90)

    def test_only_the_context_column_counts_not_the_whole_row(self) -> None:
        """「現象」「分流去向」「狀態」欄裡的輪號是佐證/承接語境，不是當前輪。"""
        text = _ledger_text(_row4("DEF-01-001", "R7 Scan-A", "列 R55 backlog", "open（R80 實測）"))
        self.assertEqual(m.current_round(text), 7)

    def test_no_round_anywhere_returns_none_instead_of_guessing(self) -> None:
        self.assertIsNone(m.current_round(_ledger_text(_row("DEF-01-001", "open"))))

    def test_real_ledger_current_round_is_two_digit_and_not_the_planning_dir_max(self) -> None:
        """🔴 明文否決掃描員建議的取值來源（`docs/04_planning/AutoSDD_improving_NN` 最大號）。

        兩套編號**不是同一個東西**：整合迭代輪（`AutoSDD_improving_NN`）與跨平台複審輪
        （`R\\d+`）各自獨立累積。若拿前者當「當前輪」，帳本裡每一列的承接輪號都會遠小於
        它 ⇒ 整本帳本瞬間全紅。本測試就地實查兩者並斷言**不相等**，讓「哪天有人改回去」
        當場翻紅（數字一律現查，不寫死）。
        """
        cur = m.current_round(m._DEFECT_LOG.read_text(encoding="utf-8-sig"))
        self.assertIsNotNone(cur, "真實帳本推不出當前輪 ⇒ 硬規則② 失去比較基準")
        planning = m._REPO_ROOT / "docs" / "04_planning"
        improving = [
            int(mm.group(1))
            for p in planning.glob("AutoSDD_improving_*.md")
            if (mm := re.fullmatch(r"AutoSDD_improving_(\d+)\.md", p.name))
        ]
        self.assertTrue(improving, "docs/04_planning/ 找不到任何 AutoSDD_improving_NN.md")
        self.assertNotEqual(
            cur, max(improving),
            "跨平台複審輪號與整合迭代輪號被當成同一個編號了——見 current_round() docstring",
        )


class TestOrphanBacklogProblems(unittest.TestCase):
    """硬規則②（孤兒承接輪次）的機械鎖，R67 落地。

    規格權威＝`docs/06_quality/CrossPlatform_Scan_Dimensions.md`〈使用方式〉硬規則②。
    本類的每一支都用**構造輸入**，不依賴真實帳本現況（真實帳本另有 live 斷言在下方）。
    """

    # 掃描員在沙箱注入、而舊閘門照樣 rc=0 全綠的那一列，逐字沿用其形狀。
    # ⚠️ ID 序列刻意改成 `DEF-01-*`，而非原樣本用的 101 序列空號：
    # `tools/tests/test_defect_id_reference_integrity.py` 會把 repo 內每一個 101 序列的
    # 引用回帳本家族查主鍵，拿一個不存在的 101 號當 fixture 會讓那道鎖紅（落地時實際踩到，
    # 連本註解自己寫出那個號碼都會被抓，故此處刻意不寫出來）。
    _INJECTED_ORPHAN = _row4(
        "DEF-01-999", "R60 r3 Pkg-X",
        "交棒給不存在的容器「幻想帳本」",
        "open（承接輪次：**R2**，明文指派，R2 早已結束且從未接手）",
    )
    _CONTEXT = _row4("DEF-01-998", "R66 Review round 2", "去向", "fixed")

    def test_the_injected_orphan_that_used_to_pass_silently_is_now_flagged(self) -> None:
        problems = m.orphan_backlog_problems(_ledger_text(self._CONTEXT + self._INJECTED_ORPHAN))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("DEF-01-999", problems[0])
        self.assertIn("R2", problems[0])
        self.assertIn("R66", problems[0], "訊息必須同時指出當前輪，否則讀者無從判斷差多遠")

    def test_a_row_handing_to_the_current_round_is_legitimate(self) -> None:
        row = self._INJECTED_ORPHAN.replace("**R2**", "**R66**").replace("R2 早已", "R66 尚未")
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_a_row_handing_to_a_future_round_is_legitimate(self) -> None:
        row = self._INJECTED_ORPHAN.replace("**R2**", "**R99**").replace("R2 早已", "R99 尚未")
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_a_reassignment_note_on_the_same_row_clears_it(self) -> None:
        """出口①：就地附記改派（DEF-101-333／336／338 的體例），不改寫歷史原文。"""
        row = self._INJECTED_ORPHAN.rstrip("\n|\r ")
        row = row + " 🔴 R67 **改派為：未指派 backlog**（解鎖條件：…） |\n"
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_a_newer_row_naming_the_id_with_a_reassignment_clears_it(self) -> None:
        """出口②：`DEF-101-521` 對 `DEF-101-500` 的改派形狀——新條目、不動舊列。"""
        newer = _row4(
            "DEF-01-1000", "R67 Scan-G", "根層治理",
            "fixed（本列**改派** DEF-01-999：原承接者 R2 已不存在，轉未指派 backlog）",
        )
        self.assertEqual(
            m.orphan_backlog_problems(_ledger_text(self._CONTEXT + self._INJECTED_ORPHAN + newer)),
            [],
        )

    def test_an_older_row_carrying_the_reassignment_does_not_count(self) -> None:
        """方向性：規則寫的是「**更新的** DEF 條目」。放在孤兒**之前**的列不算數，
        否則帳本裡任何一句舊的「改派」都會變成後續所有列的通用赦免。"""
        older = _row4(
            "DEF-01-100", "R10 Scan-G", "根層治理",
            "fixed（本列**改派** DEF-01-999：…）",
        )
        problems = m.orphan_backlog_problems(
            _ledger_text(self._CONTEXT + older + self._INJECTED_ORPHAN)
        )
        self.assertEqual(len(problems), 1, problems)

    def test_closed_rows_are_never_judged_so_the_gate_cannot_go_permanently_red(self) -> None:
        """🔴 R59 二審 ARCH-R59-NB4 點名的坑：帳本是逐字保全的歷史檔。

        `DEF-101-500` 那列會永遠留著「列 R58 backlog」字樣。規則若寫成「不得提及不存在
        的輪次」，閘門就**永紅**。本測試把四種已結案首詞各跑一次，確認一律不判。
        """
        for closed in ("fixed@R57 round 3", "wontfix（…）", "closed-by-decision", "no_action_needed"):
            with self.subTest(closed=closed):
                row = _row4("DEF-101-500", "R57 Scan-E", "①②④⑥ 本輪修復；③⑤ 列 R58 backlog", closed)
                self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_discovery_and_evidence_round_mentions_are_not_handovers(self) -> None:
        """🔴 掃描員 proposed_fix 的取值方式（列內任一 `R\\d+`）在此被明文否決。

        實測那個寫法會把真實帳本 70 列未結列中的 60 列判成孤兒——因為「R25 Scan-A 複核」
        「R60 實測」是**發現／佐證**輪次，不是承接者。一道大量假紅的閘門會被整個關掉，
        比沒有鎖更糟。
        """
        row = _row4(
            "DEF-101-268", "R25 Scan-A", "本輪修復",
            "open（R25 Scan-A 複核；R60 實測仍成立；R30 曾回讀一次）",
        )
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_status_at_round_is_a_timestamp_not_an_assignee(self) -> None:
        """`deferred@R59`＝在 R59 這一輪被 defer（同族 `fixed@R57`），不是被指派給 R59。

        真實實例 `DEF-101-518`：狀態寫 `**routed（deferred@R59，附解鎖條件）**`，解鎖條件
        三項就寫在同列。把時點當承接者會製造假紅。
        """
        row = _row4(
            "DEF-101-518", "R59 Scan-C", "本輪只就地記錄不對稱與解鎖條件",
            "**routed（deferred@R59，附解鎖條件）**：解鎖條件三項…",
        )
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_quoting_an_old_snapshot_with_本列_is_not_a_handover(self) -> None:
        """真實實例 `DEF-101-068`：「本列 R14 快照所稱…」是引述舊快照。

        `列` 的否定回顧若漏掉，這一列會假紅——落地前的初版正是這樣被抓到的。
        """
        row = _row4(
            "DEF-101-068", "S11", "記事存證",
            "open（其餘子項 **R14 補記**：本列 R14 快照所稱「仍雙原生實作」已不成立）",
        )
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_negated_reassignment_no_longer_buys_the_exemption(self) -> None:
        """🔴 R74（`DEF-101-674` 結案）：否定語意的出口字樣**不再**買到豁免。

        本斷言的前身刻意寫成「這個缺口仍開著」，用途是在有人收掉缺口時翻紅、強迫同步更新
        兩處「已實測不涵蓋」清單。R74 收掉了（`_ledger_index.reassign_hit()` 擋否定前綴），
        清單已同步，故本斷言翻轉為正向：一列「未結案 ＋ 承接者早於當前輪 ＋ 狀態欄只寫得出
        否定形態的出口字樣」必須**被判為孤兒**。

        鑑別力：同一列把否定字拿掉（改成真正的「已回執」）就必須放行 —— 兩個方向都驗，
        否則「恆紅」也會通過本測試。
        """
        negated = (self._INJECTED_ORPHAN.rstrip("\n|\r ")
                   + " 交棒給一個輪內已消滅的實體、無輪次無回執 |\n")
        problems = m.orphan_backlog_problems(_ledger_text(self._CONTEXT + negated))
        self.assertEqual(len(problems), 1, f"否定形態必須仍被判孤兒：{problems}")
        affirmed = (self._INJECTED_ORPHAN.rstrip("\n|\r ")
                    + " 該輪已交出成果，此處追記回執 |\n")
        self.assertEqual(
            m.orphan_backlog_problems(_ledger_text(self._CONTEXT + affirmed)), [],
            "真正的『回執』必須照樣放行 —— 否則本鎖變成恆紅、合法出口被關掉",
        )

    def test_reassignment_token_outside_the_status_column_buys_nothing(self) -> None:
        """🔴 R74：出口字樣寫在**別的欄位**不再算數（原判準對整列做裸比對）。

        合法出口的體例是閘門自己的錯誤訊息逐字指定的——「就地於**狀態欄**追加一筆載明
        「改派」的附記」。判準若掃整列，一列只要在「現象與證據」欄敘述**別人的**改派，
        就替自己買到豁免。兩個方向都驗：寫在證據欄 ⇒ 仍判孤兒；寫在狀態欄 ⇒ 放行。
        """
        base = _row4("DEF-01-996", "R60 r3 Pkg-X", "去向",
                     "open（承接輪次：**R2**）")
        in_evidence = base.replace("| 現象 |", "| 現象；另見 DEF-9-9 的改派紀錄 |") \
            if "| 現象 |" in base else base
        self.assertNotEqual(in_evidence, base, "fixture 未命中證據欄，測試會空過")
        self.assertEqual(
            len(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + in_evidence))), 1,
            "出口字樣落在證據欄卻買到豁免 ⇒ 跨欄白拿又開了",
        )
        in_status = base.replace("**R2**）", "**R2**）；本輪改派為：未指派")
        self.assertEqual(
            m.orphan_backlog_problems(_ledger_text(self._CONTEXT + in_status)), [],
            "寫在狀態欄的改派必須放行 —— 否則合法出口被關掉",
        )

    def test_quoted_reassignment_token_buys_nothing(self) -> None:
        """🔴 R74：反引號內是**逐字引述**（帳本體例），引述一句舊改派不是做出新改派。"""
        base = _row4("DEF-01-995", "R60 r3 Pkg-X", "去向", "open（承接輪次：**R2**）")
        quoted = base.replace("**R2**）", "**R2**）；原欄文為 `改派為：未指派`（已被推翻）")
        self.assertEqual(
            len(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + quoted))), 1,
            "code span 內的引述買到豁免 ⇒ 引述白拿又開了",
        )

    def test_a_row_without_any_handover_round_is_not_judged(self) -> None:
        """散文式指派（「留給下一輪某人」）不含 `R\\d+` ⇒ 無從比較，不判。"""
        row = _row4("DEF-01-777", "R66 Scan-G", "留給下一輪某人", "open（未指派 backlog）")
        self.assertEqual(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row)), [])

    def test_handover_without_a_derivable_current_round_fails_loud(self) -> None:
        """推不出當前輪 ＋ 有承接者 ⇒ 明說失去比較基準，**不**靜默放行。"""
        problems = m.orphan_backlog_problems(_ledger_text(self._INJECTED_ORPHAN.replace(
            "R60 r3 Pkg-X", "四方複審")))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("無法從", problems[0])

    def test_all_five_handover_phrasings_are_covered(self) -> None:
        """**已實測涵蓋**：帳本實際用過的五種承接語境各驗一次。"""
        cases = {
            "承接輪次": "open（承接輪次：**R2**）",
            "承接者＝": "open（承接者＝**R2 主控**）",
            "R…+ 承接": "open（仍待 R2+ 承接者處理）",
            "列 R… backlog": "open（依 Rule 3 外科式原則列 R2 backlog）",
            "backlog R…": "open（backlog R2，本輪未處理）",
        }
        for name, status in cases.items():
            with self.subTest(phrasing=name):
                row = _row4("DEF-01-999", "R60 r3", "去向", status)
                problems = m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row))
                self.assertEqual(len(problems), 1, f"{name} 未被認出為承接語境：{problems}")
        with self.subTest(phrasing="交棒給 R…"):
            row = _row4("DEF-01-999", "R60 r3", "交棒給 R2 處理", "open（見分流去向）")
            self.assertEqual(len(m.orphan_backlog_problems(_ledger_text(self._CONTEXT + row))), 1)

    def test_missing_header_fails_loud(self) -> None:
        problems = m.orphan_backlog_problems("| 編號 | 狀態 |\n|---|---|\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("找不到合格表頭", problems[0])


class TestOrphanBacklogAgainstTheRealLedger(unittest.TestCase):
    """對真實帳本的 live 斷言——構造輸入證明「有牙」，這裡證明「不亂咬」。"""

    def setUp(self) -> None:
        self.text = m._DEFECT_LOG.read_text(encoding="utf-8-sig")
        layout = m._table_layout(self.text)
        assert layout is not None
        self.ncols, self.id_idx, self.status_idx = layout
        self.rows = []
        for lineno, line in enumerate(self.text.splitlines(), 1):
            if not m._ROW_RE.match(line):
                continue
            cells = m._row_cells(line)
            if len(cells) != self.ncols or not m._ID_RE.fullmatch(cells[self.id_idx]):
                continue
            self.rows.append((lineno, cells, line))

    def test_rows_that_carry_a_reassignment_record_are_never_flagged(self) -> None:
        """🔴 本鎖不得誤殺歷史檔——由**實際帳本內容**現查出「已改派的舊列」再驗。

        取值全程 live（不寫死任何 DEF-ID）：凡「未結案 ＋ 指名了早於當前輪的承接者 ＋
        該列載明改派／回執」的列，都必須通過。這正是規格文件拿 `DEF-101-500`（因 `521`
        改派而合法）舉例的那一類。
        """
        cur = m.current_round(self.text)
        self.assertIsNotNone(cur)
        legal = []
        for _lineno, cells, line in self.rows:
            if m._classify(cells[self.status_idx]) not in m._UNRESOLVED_CLASSES:
                continue
            handovers = m._handover_rounds(line)
            if not handovers or max(n for _, n, _ in handovers) >= cur:
                continue
            # 🔴 R74：判定面必須與 production 一致（狀態欄、遮 code span、擋否定），否則本
            # 測試會拿一組「整列比對才算合法」的列去要求 production 放行 ⇒ 假紅。
            if m._reassign_hit(cells[self.status_idx]):
                legal.append(cells[self.id_idx])
        self.assertTrue(
            legal,
            "帳本內找不到任何「舊承接輪次 ＋ 已改派」的列 ⇒ 本測試會空過（vacuous pass）。"
            "若真的一列都不剩，請改以構造輸入驗證出口①，不要讓斷言變成恆真",
        )
        # 🔴 刻意解析出「被判的那一列的 ID」而非對整段訊息做子字串比對：問題訊息裡帶有
        # 「體例比照 DEF-101-333／336／338」這類**建議用的** ID，子字串比對會把它們誤判
        # 成被點名者（落地時實際踩到，本註解即該次的留痕）。
        flagged = {
            mm.group(1)
            for p in m.orphan_backlog_problems(self.text)
            if (mm := re.search(r"帳本 :\d+ (DEF-\d+-\d+)：", p))
        }
        for def_id in legal:
            self.assertNotIn(
                def_id, flagged,
                f"{def_id} 已載明改派卻仍被判孤兒 ⇒ 閘門正在誤殺逐字保全的歷史列",
            )

    def test_the_naive_whole_row_rule_would_have_burned_most_of_the_ledger(self) -> None:
        """量化「為何只認承接語境」：把掃描員建議的『列內任一 R\\d+』跑一次做對照組。

        數字一律現查、不寫死（Scan-H 必跑項 #3）。斷言採比例而非絕對值：narrow 規則命中
        的列必須遠少於 naive 規則，否則就表示 narrow 化沒有實際收斂效果、設計理由不成立。
        """
        cur = m.current_round(self.text)
        naive, narrow = 0, 0
        for _lineno, cells, line in self.rows:
            if m._classify(cells[self.status_idx]) not in m._UNRESOLVED_CLASSES:
                continue
            rounds = [int(x) for x in m._ROUND_RE.findall(line)]
            if rounds and max(rounds) < cur:
                naive += 1
            handovers = m._handover_rounds(line)
            if handovers and max(n for _, n, _ in handovers) < cur:
                narrow += 1
        self.assertGreater(naive, 0, "對照組零命中 ⇒ 本測試失去對照意義")
        self.assertLess(
            narrow * 5, naive,
            f"承接語境窄化沒有收斂效果（naive={naive}／narrow={narrow}）——"
            "請重新檢視 _HANDOVER_ROUND_RES 是否又退回『列內任一 R\\d+』",
        )

    def test_real_ledger_has_zero_orphan_backlog_rows(self) -> None:
        """真實帳本不得有孤兒承接輪次（硬規則②）。

        🔴 這一支與 `TestMain::test_main_against_real_repo_is_clean` 同屬 live 斷言：
        紅了就是**帳本內容**該修（就地附記改派／回執），不是把鎖放寬。修法逐字寫在
        失敗訊息裡。
        """
        self.assertEqual(m.orphan_backlog_problems(self.text), [])


class TestHardRule2IsBoundToItsSpecProse(unittest.TestCase):
    """散文 ↔ 程式雙向綁定（手法比照本檔既有的「《格式定義》↔ `_STATUS_FIRST_WORDS`」）。

    🔴 為何非綁不可：規格段落自 R59 起寫著「本規則目前純靠紀律，尚無機械鎖」，R67 落鎖後
    那句就成了**假話**，而沒有任何機械物會發現。這正是本 repo 反覆在治的「改了程式沒改散文」。
    """

    def setUp(self) -> None:
        self.text = _SPEC_DOC.read_text(encoding="utf-8-sig")
        rule2 = re.search(
            r"\n  2\. \*\*任何 `deferred`.*?(?=\n  3\. )", self.text, re.S
        )
        self.assertIsNotNone(rule2, "規格文件抓不到硬規則② 那一段 — 段落結構已被改寫")
        self.rule2 = rule2.group(0)

    def test_the_spec_names_the_landed_function_and_its_host(self) -> None:
        self.assertIn("orphan_backlog_problems", self.rule2)
        self.assertIn("tools/check_defect_log_crossref.py", self.rule2)

    def test_the_named_function_actually_exists_and_is_a_hard_gate(self) -> None:
        self.assertTrue(callable(getattr(m, "orphan_backlog_problems", None)))
        self.assertTrue(callable(getattr(m, "current_round", None)))
        src = Path(m.__file__).read_text(encoding="utf-8")
        main_src = src[src.index("def main()"):]
        self.assertIn("orphan_backlog_problems(ledger_text)", main_src,
                      "main() 沒有消費本檢查 ⇒ 又是一支「可重跑但沒有閘門看它 rc」的稽核工具")

    def test_the_spec_no_longer_claims_rule_2_has_no_mechanical_lock(self) -> None:
        self.assertNotIn("尚無機械鎖", self.rule2,
                         "硬規則② 已落鎖，散文仍宣稱「尚無機械鎖」＝ 假話")

    def test_the_spec_still_carries_the_permanent_red_pitfall_warning(self) -> None:
        """坑的警告是本鎖的設計前提，刪掉它下一個人就會把規則寫成「永紅」的形態。"""
        self.assertIn("逐字保全", self.rule2)
        self.assertIn("永紅", self.rule2)
        self.assertIn("≥ 當前輪", self.rule2)
        self.assertIn("改派", self.rule2)

    def test_the_spec_records_the_known_uncovered_forms(self) -> None:
        for token in ("否定語意", "deferred@R59"):
            self.assertIn(token, self.rule2,
                          f"規格段落漏記已實測不涵蓋形態：{token}")

    def test_rule_3_no_longer_claims_parity_with_rule_2(self) -> None:
        """硬規則③ 原寫「同硬規則②，本條目前純靠紀律」——② 落鎖後這句話就錯了。"""
        rule3 = self.text[self.text.index("\n  3. **跨軌交棒"):]
        self.assertIn("尚無機械鎖", rule3, "③ 若已落鎖請同步改寫本測試與規格散文")
        self.assertNotIn("同硬規則②，本條目前", rule3)


# `docs/06_quality/CrossPlatform_Scan_Dimensions.md` 是**規範性規格**：它的示範指令是寫給
# 未來每一輪的稽核員照抄重跑的，所以必須在本 repo 的三種 shell（zsh／bash 3.2／PowerShell）
# 下都能跑。刻意**不**把同族的證據檔（`CrossPlatform_R60_Fix_Evidence*.md`）與 ADR 納入本鎖：
# 那些檔記錄的是「當年實際跑了什麼」，逐字保全的史料不該為了通過閘門而被改寫——與硬規則②
# 「歷史檔逐字保全」是同一條判準。要納入新檔就在下方 tuple 加一筆。
_ZSH_SAFE_COMMAND_DOCS = (_SPEC_DOC,)
# 反引號內含 `grep` 呼叫者才算「可執行示範指令」；只是**引述**壞形態的散文（本規格自己就有
# 一段在解釋 `--include=*.md` 為何危險）不在判定面內——判定面是指令，不是提到指令的句子。
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def _unquoted_glob_commands(text: str) -> list[str]:
    """回傳「含 grep 且有未被引號包住的 `*`」的反引號指令（空＝全部 zsh-safe）。"""
    bad = []
    for span in _INLINE_CODE_RE.findall(text):
        if "grep" not in span:
            continue
        quote = None
        for ch in span:
            if quote is None and ch in "'\"":
                quote = ch
            elif quote is not None and ch == quote:
                quote = None
            elif quote is None and ch == "*":
                bad.append(span)
                break
    return bad


class TestSpecDocShellCommandsAreZshSafe(unittest.TestCase):
    """R67：規格文件自己的示範指令在 macOS 預設 zsh 下必須真的跑得起來。

    🔴 原始缺陷：硬規則③ 用來示範判準的兩條指令寫成 `grep -rn "…" --include=*.md .`，
    在 zsh 下 `nomatch` 會在 **grep 被執行之前**中止整條命令列（實測 `zsh:1: no matches
    found: --include=*.md`、rc=1、連 `2>` 重導向都沒被建立）。而該規則正是以「零命中」
    推論「容器不存在」——於是**判準的示範指令在 mac 上恆答『不存在』**。
    未加引號時的零輸出**不是**零命中，是指令根本沒跑。
    """

    def test_no_registered_spec_doc_has_an_unquoted_glob_in_a_grep_command(self) -> None:
        for doc in _ZSH_SAFE_COMMAND_DOCS:
            with self.subTest(doc=doc.name):
                bad = _unquoted_glob_commands(doc.read_text(encoding="utf-8-sig"))
                self.assertEqual(
                    bad, [],
                    f"{doc.name} 的示範指令含未加引號的 glob——macOS 預設 zsh 會在 grep "
                    f"執行前 abort（nomatch），把「指令沒跑」偽裝成「零命中」。"
                    f"請寫成 --include='*.md'（三種 shell 皆正確）",
                )

    def test_the_lock_fires_on_the_pre_fix_form(self) -> None:
        """缺陷注入：把修好的形態改回壞的，鎖必須翻紅。"""
        broken = "R60 實測 `grep -rn \"一般 CI 維護\" --include=*.md .` 全庫只命中兩列"
        self.assertEqual(len(_unquoted_glob_commands(broken)), 1)

    def test_prose_that_merely_quotes_the_broken_flag_is_not_flagged(self) -> None:
        """判定面是**指令**不是句子：規格自己那段解釋 `--include=*.md` 為何危險必須放行，
        否則「說明這個坑」本身會被閘門擋下，沒有人能把邊界寫進文件。"""
        prose = "原文寫成未加引號的 `--include=*.md`，在 zsh 下會 abort"
        self.assertEqual(_unquoted_glob_commands(prose), [])

    def test_quoted_form_passes_and_double_quotes_count_too(self) -> None:
        for good in (
            "`grep -rn 'DEF-101-422' --include='*.md' . | grep -v AutoSDD_Defect_Log`",
            '`grep -rn "x" --include="*.md" .`',
        ):
            with self.subTest(good=good):
                self.assertEqual(_unquoted_glob_commands(good), [])

    def test_the_two_rule_3_example_commands_are_still_present_and_quoted(self) -> None:
        """防「靠刪掉指令通過閘門」：兩條示範指令必須仍在，且是加引號的形態。"""
        text = _SPEC_DOC.read_text(encoding="utf-8-sig")
        for needle in (
            "grep -rn \"一般 CI 維護\" --include='*.md' .",
            "grep -rn 'DEF-101-422' --include='*.md' . | grep -v AutoSDD_Defect_Log",
        ):
            self.assertIn(needle, text, "硬規則③ 的示範指令被刪或被改形，判準失去可執行示範")

    def test_the_scoped_docs_are_all_registered_governance_docs(self) -> None:
        """涵蓋面不得指向一個沒人管的檔：本鎖的標的必須同時在 `_GOVERNANCE_DOCS` 內
        （那張清單另有『磁碟有而清單沒有』的反查鎖），避免改名後兩邊一起失聯。"""
        registered = {p.resolve() for p in m._GOVERNANCE_DOCS}
        for doc in _ZSH_SAFE_COMMAND_DOCS:
            self.assertIn(doc.resolve(), registered)
            self.assertTrue(doc.exists())


class TestUnpinnedHandoverAndStaleGrandfather(unittest.TestCase):
    """硬規則② 後半句（R68）與其存量豁免 stale 自檢的鑑別力鎖。

    🔴 為何必須以**純函式**驗、不經 `main()`：這兩道與 `_UNPINNED_HANDOVER_
    GRANDFATHERED` 是一體的，而該名單列的是相對於真實主檔的存量 ID。經 `main()`
    就得餵合成帳本，名單對它全不匹配 ⇒ 兩個方向同時假紅（fixture 的未結列一律被判
    「缺承接指派」、名單每一筆一律被判「已 stale」），紅因與被驗行為無關。主檔因此
    把這兩道綁在 `_DEFECT_LOG == _DEFAULT_DEFECT_LOG`；**代價是 `main()` 路徑上
    這兩道對合成帳本沒有覆蓋**，本類別就是補上那塊覆蓋的地方——少了它，綁定就從
    「隔離假紅」變成「靜默關掉一條規則」。

    R68 補立的直接原因：這兩道在被加進主檔時**零測試**（`grep` 全 `tools/tests/`
    零命中），等於新規則自己不符合本 repo 對「鎖已落地」的認定門檻（Scan-H）。
    """

    _ROW_UNRESOLVED_NO_HANDOVER = (
        "| DEF-01-777 | 2026-08-02 | 情境 | 現象 | P2 | 去向 | open |\n"
    )
    _ROW_UNRESOLVED_UNASSIGNED = (
        "| DEF-01-777 | 2026-08-02 | 情境 | 現象 | P2 | 去向 | open（未指派） |\n"
    )
    _ROW_UNRESOLVED_WITH_ROUND = (
        "| DEF-01-777 | 2026-08-02 | 情境 | 現象 | P2 | 去向 | open（承接輪次：R99） |\n"
    )
    _ROW_CLOSED = (
        "| DEF-01-777 | 2026-08-02 | 情境 | 現象 | P2 | 去向 | fixed@R68 |\n"
    )

    def _no_grandfather(self):
        """把存量豁免清空——本類別驗的是規則本體，不是那 57 筆歷史存量。"""
        return mock.patch.object(m, "_UNPINNED_HANDOVER_GRANDFATHERED", frozenset())

    def test_unresolved_row_without_any_handover_is_caught(self) -> None:
        """缺陷注入（正向）：未結列既無輪號也無「未指派」字面 ⇒ 必須被抓。"""
        with self._no_grandfather():
            problems = m.unpinned_handover_problems(
                _ledger_text(self._ROW_UNRESOLVED_NO_HANDOVER))
        self.assertTrue(problems, "未結列缺承接指派卻零訊號 ⇒ 硬規則② 後半句無牙")
        self.assertIn("DEF-01-777", " ".join(problems))

    def test_literal_unassigned_satisfies_the_rule(self) -> None:
        """還原（反向之一）：補上字面「未指派」即為合法出口，不得再紅。"""
        with self._no_grandfather():
            self.assertEqual(
                m.unpinned_handover_problems(
                    _ledger_text(self._ROW_UNRESOLVED_UNASSIGNED)), [])

    def test_explicit_round_satisfies_the_rule(self) -> None:
        """還原（反向之二）：指名承接輪號同樣是合法出口。"""
        with self._no_grandfather():
            self.assertEqual(
                m.unpinned_handover_problems(
                    _ledger_text(self._ROW_UNRESOLVED_WITH_ROUND)), [])

    def test_closed_row_is_out_of_scope(self) -> None:
        """已結列不在本規則射程（`_UNRESOLVED_CLASSES` 之外）——防過度攔截。"""
        with self._no_grandfather():
            self.assertEqual(
                m.unpinned_handover_problems(_ledger_text(self._ROW_CLOSED)), [])

    def test_grandfathered_id_is_not_reported_as_a_problem(self) -> None:
        """存量豁免確實生效：同一列進了名單就不該再被判「缺承接指派」。"""
        with mock.patch.object(
            m, "_UNPINNED_HANDOVER_GRANDFATHERED", frozenset({"DEF-01-777"})
        ):
            self.assertEqual(
                m.unpinned_handover_problems(
                    _ledger_text(self._ROW_UNRESOLVED_NO_HANDOVER)), [])

    def test_stale_grandfather_is_caught_when_the_row_got_closed(self) -> None:
        """缺陷注入（stale 自檢正向）：豁免對象已結案 ⇒ 名單必須被要求刪除該筆。

        這正是棘輪「只准往小走」的驅動力；沒有這一條，名單只進不出。
        """
        with mock.patch.object(
            m, "_UNPINNED_HANDOVER_GRANDFATHERED", frozenset({"DEF-01-777"})
        ):
            problems = m.stale_grandfather_problems(_ledger_text(self._ROW_CLOSED))
        self.assertTrue(problems, "豁免對象已結案卻不要求刪除 ⇒ 名單變成死名單")
        self.assertIn("DEF-01-777", " ".join(problems))

    def test_stale_grandfather_is_silent_while_the_waiver_is_still_needed(self) -> None:
        """還原（stale 自檢反向）：對象仍是「未結且無指派」時，豁免仍需要，不得誤報。"""
        with mock.patch.object(
            m, "_UNPINNED_HANDOVER_GRANDFATHERED", frozenset({"DEF-01-777"})
        ):
            self.assertEqual(
                m.stale_grandfather_problems(
                    _ledger_text(self._ROW_UNRESOLVED_NO_HANDOVER)), [])

    def test_main_still_runs_both_gates_against_the_real_ledger(self) -> None:
        """綁定不得退化成「靜默關掉」：真實主檔路徑上兩道必須仍被 `main()` 執行。

        以原始碼結構斷言（兩道的呼叫確實在 `_DEFAULT_DEFECT_LOG` 的守衛區塊內，
        且該常數就是預設主檔），而非重跑一次 `main()`——後者在真 repo 綠燈時
        對「有沒有跑到」是恆真的，抓不到有人把守衛條件改成永遠為假。
        """
        self.assertEqual(m._DEFAULT_DEFECT_LOG, m._REPO_ROOT / "docs" /
                         "06_quality" / "AutoSDD_Defect_Log.md")
        src = Path(m.__file__).read_text(encoding="utf-8")
        guard = "if _DEFECT_LOG == _DEFAULT_DEFECT_LOG:"
        self.assertIn(guard, src, "守衛消失 ⇒ 兩道可能被無條件跑或無條件跳過")
        after = src.split(guard, 1)[1]
        # 守衛區塊 = 緊接其後、縮排更深的那幾行；兩道呼叫都必須落在裡面。
        block = []
        for line in after.splitlines()[:12]:
            if line.strip() and not line.startswith(" " * 8):
                break
            block.append(line)
        block_text = "\n".join(block)
        for fn in ("unpinned_handover_problems(", "stale_grandfather_problems("):
            self.assertIn(fn, block_text,
                          f"`{fn}` 不在真實主檔守衛區塊內 ⇒ 綁定已退化")

    # ── 棘輪本體（R69 假鎖修正，`DEF-101-731`）：R68 的 `_UNPINNED_HANDOVER_CEILING` 是假鎖 ──
    # 自稱「只准變小」，實測全檔零比較——加一筆豁免、rc 仍是 0，工具還把
    # 「存量豁免 58 筆／棘輪上限 57」原樣印進**成功**訊息裡。以下三道補上牙齒。

    def test_grandfather_ceiling_is_actually_enforced_when_exceeded(self) -> None:
        """缺陷注入（正向）：白名單比天花板多一筆 ⇒ 必須被抓。

        這是本輪修的假鎖本體：註解宣告 shrink-only 卻沒有任何比較，
        白名單可以每輪「順手加一筆」無聲膨脹，硬規則② 後半句被逐列贖回。
        """
        with mock.patch.object(
            m, "_UNPINNED_HANDOVER_GRANDFATHERED",
            frozenset(f"DEF-01-{i:03d}" for i in range(11))
        ), mock.patch.object(m, "_UNPINNED_HANDOVER_CEILING", 10):
            problems = m.grandfather_ceiling_problems()
        self.assertTrue(problems, "白名單超過棘輪上限卻零告警 ⇒ 棘輪不存在")
        joined = " ".join(problems)
        self.assertIn("11", joined)
        self.assertIn("10", joined)

    def test_grandfather_ceiling_is_silent_at_or_below_the_ceiling(self) -> None:
        """還原（反向）：等於／小於天花板都是合法的（棘輪允許往小走，不得誤報）。"""
        for size in (10, 9, 0):
            with mock.patch.object(
                m, "_UNPINNED_HANDOVER_GRANDFATHERED",
                frozenset(f"DEF-01-{i:03d}" for i in range(size))
            ), mock.patch.object(m, "_UNPINNED_HANDOVER_CEILING", 10):
                self.assertEqual(m.grandfather_ceiling_problems(), [],
                                 f"{size} 筆 ≤ 上限 10 卻誤報 ⇒ 棘輪擋住了合法的收縮")

    def test_shipped_ceiling_matches_the_shipped_whitelist(self) -> None:
        """出廠常數自身必須貼齊：天花板 == 白名單實際筆數。

        大於實際值＝預留了「可以再加幾筆」的無聲額度（棘輪一上線就先鬆一格）；
        小於實際值＝閘門出廠即紅。兩邊都不可接受，故釘死相等。
        """
        self.assertEqual(
            m._UNPINNED_HANDOVER_CEILING, len(m._UNPINNED_HANDOVER_GRANDFATHERED),
            "天花板未貼齊白名單實際筆數 —— 大於＝預留無聲膨脹額度，小於＝出廠即紅")

    def test_ceiling_gate_runs_unconditionally_in_main(self) -> None:
        """棘輪不得被塞進真實主檔守衛內：那樣「換一本帳本」就能繞過它。

        以原始碼結構斷言（呼叫點必須在 `main()` 內、且**不在**
        `_DEFECT_LOG == _DEFAULT_DEFECT_LOG` 的守衛區塊內），理由同上一道：
        真 repo 綠燈時重跑 `main()` 對「有沒有跑到」是恆真的。
        """
        src = Path(m.__file__).read_text(encoding="utf-8")
        call = "grandfather_ceiling_problems()"
        self.assertIn(f"    ceiling_problems = {call}", src,
                      "main() 未呼叫棘輪 ⇒ 又變回只有常數沒有比較的假鎖")
        guard = "if _DEFECT_LOG == _DEFAULT_DEFECT_LOG:"
        block = []
        for line in src.split(guard, 1)[1].splitlines()[:12]:
            if line.strip() and not line.startswith(" " * 8):
                break
            block.append(line)
        self.assertNotIn(call, "\n".join(block),
                         "棘輪被塞進真實主檔守衛內 ⇒ 換一本帳本即可繞過")


class TestAdrClosureClaimsAreMechanicallyChecked(unittest.TestCase):
    """R69 `DEF-101-735` — ADR 的散文式結案宣稱 vs 帳本狀態。

    **原始缺陷**：`ADR-XPLAT-002` §1 與 `ADR-XPLAT-003` 表頭各自寫「`DEF-101-706`
    隨之結案」，而同輪帳本該列狀態欄是 `partial`（明寫「解鎖條件①未達標故不結案」）
    ——兩份活文件對同一個 ID 各說各話。當時 ADR 目錄**不在** `_CROSSREF_TARGETS` 內，
    機械上完全盲。

    **本鎖守的是兩件事，缺一都還原不了缺陷**：
      (甲) ADR 目錄在掃描面內（且是 glob 自動註冊——具名清單必漏掉下一支新 ADR，
           而漏掉零訊號，正是本缺陷的形狀）。
      (乙) 掃描面內**看得見散文宣稱**。`_scan_target()` 的 `_CLAIM_RE` 只認
           「DEF-ID 緊接括號」，ADR 那句是純散文 ⇒ 只做 (甲) 不做 (乙)，閘門仍然全綠。
           這一條是本鎖的重點：**納入掃描面不等於看得見**。
    """

    def test_adr_directory_is_in_the_crossref_scan_surface(self):
        """(甲) 根層 ADR 目錄下每一支 `ADR-*.md` 都在掃描目標內。"""
        on_disk = sorted(p.name for p in m._ADR_DIR.glob(m._ADR_GLOB))
        self.assertTrue(on_disk, f"{m._ADR_DIR} 下查無 ADR ⇒ 本鎖的前提已失效")
        targets = {p.name for p in m._CROSSREF_TARGETS}
        self.assertEqual(
            [n for n in on_disk if n not in targets], [],
            "有 ADR 不在 _CROSSREF_TARGETS 內 —— 它對缺陷狀態的宣稱將零檢查",
        )

    def test_prose_closure_claim_contradicting_the_ledger_is_caught(self):
        """(乙) 注入散文式結案宣稱 → 必紅並指名 ID；帳本判已結時放行。"""
        unclosed = m.closure_claim_problems(
            "fake-adr.md", "本項由 DEF-101-706 隨之結案）。", {"DEF-101-706": "open"})
        self.assertEqual(len(unclosed), 1, "散文式結案宣稱未被抓到 —— 本道無牙")
        self.assertIn("DEF-101-706", unclosed[0])
        self.assertEqual(
            m.closure_claim_problems(
                "fake-adr.md", "本項由 DEF-101-706 隨之結案）。",
                {"DEF-101-706": "fixed"}),
            [], "帳本判已結時仍報紅 ⇒ 假紅，會逼人把正確的句子改掉",
        )

    def test_negated_and_far_away_forms_are_not_false_positives(self):
        """誠實劃界：否定形態與距離過遠的形態刻意不報（否則活文件會被誤紅淹沒）。

        沒有這一條，上一條無法證明本道是「有鑑別力」而不是「見到結案就紅」。
        """
        self.assertEqual(
            m.closure_claim_problems(
                "fake-adr.md", "`DEF-101-706` 的收斂標的已落地，但該筆**不結案**。",
                {"DEF-101-706": "open"}),
            [], "否定形態被誤報 ⇒ 訂正過的句子反而紅，鎖會逼人寫回錯的說法",
        )
        far = "DEF-101-706 " + "。" * (m._CLOSURE_CLAIM_WINDOW + 5) + "本項結案"
        self.assertEqual(
            m.closure_claim_problems("fake-adr.md", far, {"DEF-101-706": "open"}),
            [], "距離超出視窗仍綁定 ⇒ ADR 的數千字長列會把不相干的 ID 綁進來",
        )


# ── R71（`DEF-101-765` 解鎖條件 (c)）：程式碼註解輪號 ↔ 帳本當前輪的機械守 ──────────
#
# 根因逐字（帳本 `DEF-101-765`）：「`current_round()` **只讀帳本**，程式碼註解裡的輪號對它
# 完全不可見，兩邊可以無限漂移」。`DEF-101-757` 入規「已知的鎖射程缺口不得只以劃界結案」，
# 故本組鎖把那個盲區封起來——但**刻意射程窄而準**，判準是「超前」不是「不等於」：
#
#   ✅ 採用：輪號 **> 帳本當前輪** 即紅。
#      · 對正當歷史引用**天然免疫**：「R70 那輪做了 X」講的是已發生的輪次，恆 ≤ 當前輪。
#        這一點不是宣稱，由 `test_a_legitimate_historical_reference_is_not_flagged` 坐實。
#      · 抓得到 `DEF-101-765` 的**實際形態**：本批程式碼自稱 R72、帳本當前輪 R71。round-label-ok
#   ❌ 否決 ①「輪號 ≠ 當前輪即紅」：本 repo 的註解**大量**逐字引用往輪（`R42`／`R60`／
#      `R69`…），實測全樹逾千處 ⇒ 幾乎每支檔都紅，屬「寬而吵」，鎖會被 opt-out 掉。
#   ❌ 否決 ②「只掃未提交／本批新增的行」：可攔本次事故，但一 commit 就失明——鎖的價值
#      在下一輪，而下一輪它什麼都看不到；且 `git diff` 面對 rebase／squash 不穩定。
#   ❌ 否決 ③「凡輪號一律要求同行帶輪次來源註記」：等於強制全樹改寫上千處註解，成本遠高
#      於收益，且新格式一樣會漂移（本 repo 已有多筆「格式訂了沒人跟」的前例）。
#
# 掃描面（**實測收斂**，非拍腦袋——手法同 `DEF-101-757` 那輪「寬判準 52 命中多為誤配 →
# 收斂到零誤報」）：
#   · 檔型＝`.py/.ps1/.sh/.psm1/.bash`，取 tracked ∪ untracked-not-ignored
#     （`git ls-files` ∪ `-o --exclude-standard`；`DEF-101-752` 立的掃描面政策，
#     未追蹤檔天然隱形正是那筆的根因）。
#   · `.py` 只掃**註解與 docstring**（人寫給人看的輪號標籤只住在那裡），**不掃**一般字串
#     字面值——後者是測試構造的**合成帳本語料**（本檔的 `R80`／`R90`／`R99`、  round-label-ok
#     `test_archive_defect_log.py` 的 `R99`），逐字掃會當場多 9 筆假紅。這一刀由  round-label-ok
#     `test_a_synthetic_ledger_fixture_in_a_string_literal_is_not_flagged` 雙向坐實。
#   · `.py` 解析失敗 ⇒ 退回整檔逐行掃（**fail-closed**：寧可吵，不可瞎）。
#   · `.ps1/.sh` 整行掃（實測零假紅，不必再切註解層）。
#   · 同行帶 `round-label-ok` 具名豁免者跳過（比照本 repo `baseline-ok`／`ps7-ok` 家族）。
#     現存 7 筆，全部是**在講輪號這件事本身**的散文：本段 WHY 註解 5 行、本組鎖其中一支的
#     docstring 1 行，加上 `test_archive_defect_log.py` 那句 docstring 內的合成語料 1 行。
#     🔴 這 7 筆是本鎖第一次實跑當場自己抓出來的（它先把自己的說明文字判紅），保留為
#     「本鎖確實在看 docstring 與註解」的活體證據——它們一旦被刪，`test_scan_surface_is_alive`
#     以外再無第二個訊號說明豁免機制還活著。
#
# 誠實劃界（是判準的已知邊界，**各自附實測理由**，不是「劃界代替補鎖」）：
#   (a) 非程式碼文字檔（`.md`／`.yml`…）不在掃描面。`.yml`：實測全樹工作流只出現當前輪，
#       零命中＝納入也不會多說什麼，故不付掃描成本。`.md` 是刻意排除——
#       帳本自己就是當前輪的 SSOT，而它的列會**合法**引述別的輪號當證據
#       （`DEF-101-765` 本列逐字並列 R70／R71／R72；`DEF-101-752` 寫「到 R72 就會低於  round-label-ok
#       當前輪」的前瞻句）。實測納入 `.md` 立刻多 3 筆假紅 ⇒ 寬而吵。
#   (b) **落後值抓不到**（把本批寫成 R70）：機械上分不出「本批自稱 R70」與「引用 R70 那輪」
#       ——那要讀懂句意。本輪 131 處落後值是**人工逐處判讀**訂正的，不在本鎖射程內。
_ROUND_LABEL_RE = re.compile(r"(?<![A-Z0-9_])R(\d{1,4})(?![0-9])")
_ROUND_LABEL_EXEMPT = "round-label-ok"
_ROUND_SCAN_EXTS = (".py", ".ps1", ".sh", ".psm1", ".bash")


def _git_listed(*extra: str) -> set[str]:
    # 🔴 DEF-101-762 同族防護（本輪 R71 自己踩過一次，由收官複審抓到）：
    # `text=True` 不帶 encoding 會走 locale 解碼，zh-TW 下即 CP950 ⇒ 非 ASCII 路徑失真。
    # `core.quotepath=false` 讓 git 直接吐 UTF-8 原字，而非預設的 `\\xxx` 八進位轉義
    # ——兩者要成對，只給 encoding 仍會拿到轉義字面值。
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", *extra],
        cwd=str(m._REPO_ROOT), capture_output=True,
        text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def round_scan_surface() -> list[Path]:
    """tracked ∪ untracked-not-ignored 的程式碼檔。"""
    names = _git_listed() | _git_listed("-o", "--exclude-standard")
    return sorted(m._REPO_ROOT / n for n in names if n.endswith(_ROUND_SCAN_EXTS))


def prose_spans(name: str, text: str) -> list[tuple[int, str]]:
    """回傳 `(行號, 該行散文)`；`.py` 取註解＋docstring，其餘（與解析失敗）整檔逐行。"""
    if not name.endswith(".py"):
        return list(enumerate(text.split("\n"), 1))
    chunks: list[tuple[int, str]] = []
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    chunks.append((getattr(node.body[0], "lineno", 1), doc))
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                chunks.append((tok.start[0], tok.string))
    except (SyntaxError, IndentationError, tokenize.TokenError, ValueError):
        return list(enumerate(text.split("\n"), 1))
    out: list[tuple[int, str]] = []
    for base, chunk in chunks:
        for off, line in enumerate(chunk.split("\n")):
            out.append((base + off, line))
    return out


def future_round_labels(name: str, text: str, current: int) -> list[tuple[int, int, str]]:
    """散文面上所有 `R<n>` 且 `n > current` 的 `(行號, 輪號, 片段)`。"""
    hits: list[tuple[int, int, str]] = []
    for lineno, line in prose_spans(name, text):
        if _ROUND_LABEL_EXEMPT in line:
            continue
        for mm in _ROUND_LABEL_RE.finditer(line):
            n = int(mm.group(1))
            if n > current:
                hits.append((lineno, n, line.strip()[:120]))
    return hits


class TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound(unittest.TestCase):
    """程式碼裡的輪號標籤不得超前帳本推得的當前輪（`DEF-101-765` 解鎖條件 (c)）。

    意圖（Rule 9）：這條鎖的價值**不在**「輪號寫錯很難看」，而在 `current_round()` 是
    `check_defect_log_crossref.py` 硬規則② 的比較基準——程式碼與帳本對「現在是第幾輪」
    各說各話時，承接稽核就會拿一個錯的基準做判定（`DEF-101-765` 實測：當前輪被推成 72 時
    `DEF-101-752` 立刻被誤判為孤兒 backlog、rc=1）。所以這是**判準基準的一致性**問題。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.current = m.current_round(m._DEFAULT_DEFECT_LOG.read_text(encoding="utf-8"))

    def test_current_round_is_derivable(self) -> None:
        """前提自檢：推不出當前輪時本組鎖整組失去意義，必須 fail-loud 而非靜默放行。"""
        self.assertIsInstance(self.current, int, "帳本推不出當前輪 ⇒ 本鎖無比較基準")

    def test_scan_surface_is_alive(self) -> None:
        """載具自檢（fail-open 封死）：掃描面不得崩塌，散文抽取不得抽不到東西。

        沒有這一條，`git ls-files` 換目錄或 AST 抽取寫壞時，本鎖會安靜地零命中假綠——
        正是 `DEF-101-752`（掃描面看不到該看的地方）付過學費的形態。
        """
        surface = round_scan_surface()
        self.assertGreater(len(surface), 500, f"掃描面只有 {len(surface)} 檔 ⇒ 已崩塌")
        probe = m._REPO_ROOT / "tools" / "tests" / "test_dev_start.py"
        self.assertIn(probe, surface, "已知含大量輪號註解的檔不在掃描面內")
        alive = future_round_labels(probe.name, probe.read_text(encoding="utf-8"), current=1)
        self.assertTrue(alive, "對真實檔以 current=1 掃仍零命中 ⇒ 散文抽取或 regex 已死")

    def test_no_code_file_claims_a_round_beyond_the_ledger(self) -> None:
        """全樹實掃：任何程式碼檔的輪號標籤都不得超前帳本當前輪。"""
        assert isinstance(self.current, int)
        problems: list[str] = []
        for path in round_scan_surface():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            # 便宜前置過濾：整檔沒有超前值就不必付 AST/tokenize 的錢（25s → 1.5s）。
            if not any(int(mm.group(1)) > self.current for mm in _ROUND_LABEL_RE.finditer(text)):
                continue
            for lineno, n, snippet in future_round_labels(path.name, text, self.current):
                rel = path.relative_to(m._REPO_ROOT).as_posix()
                problems.append(f"{rel}:{lineno} 自稱 R{n} > 帳本當前輪 R{self.current}｜{snippet}")
        self.assertEqual(
            problems, [],
            "程式碼註解的輪號超前帳本當前輪（`DEF-101-765` 形態）。兩條正解擇一：\n"
            "  · 該處講的是本批 ⇒ 改成當前輪；\n"
            "  · 該處是測試用的合成帳本語料 ⇒ 同行加具名豁免 `round-label-ok`。\n"
            + "\n".join(problems),
        )

    def test_a_future_round_label_in_a_comment_is_flagged(self) -> None:
        """注入退化（.py 註解）：超前輪號必須被抓到並指出行號與輪號。"""
        text = "x = 1\n# R99 併檔：本批把某某鎖參數化過來。\n"
        self.assertEqual(
            [(ln, n) for ln, n, _ in future_round_labels("f.py", text, current=71)],
            [(2, 99)], "超前輪號沒被抓到 ⇒ 本鎖無牙",
        )

    def test_a_future_round_label_in_a_docstring_is_flagged(self) -> None:
        """docstring 也在射程內：`DEF-101-762` 那批 R72 有 4 處就住在 docstring。round-label-ok"""
        text = 'def f():\n    """WHY（R72／DEF-101-762 併檔）：說明。"""\n'
        self.assertEqual(
            [n for _, n, _ in future_round_labels("f.py", text, current=71)], [72],
            "docstring 不在射程內 ⇒ 本次事故有一半抓不到",
        )

    def test_a_future_round_label_in_a_shell_comment_is_flagged(self) -> None:
        """`.ps1/.sh` 整行掃：`run_tlc.ps1:47` 那筆就是這個形態。"""
        self.assertEqual(
            [n for _, n, _ in future_round_labels("x.ps1", "# R72 由只鎖 A 參數化過來\n", 71)],
            [72], ".ps1 註解不在射程內",
        )

    def test_a_legitimate_historical_reference_is_not_flagged(self) -> None:
        """🔴 還原為綠的關鍵條：**正當的歷史引用不得誤報**。

        沒有這一條，本鎖與「輪號 ≠ 當前輪即紅」那個被否決的寬判準在測試上不可區分——
        而那個版本會把本 repo 上千處「R60 那輪…」的 WHY 註解全部打紅。
        """
        for prose in (
            "# R70 那輪做了 X，本輪沿用其結論。",
            "# 🔴 R42／DEF-101-350 起把這串行內抄寫在多個姊妹鎖裡。",
            f"# R{71} 落地時只鎖了一支。",
            "# 判準自 R60 起改指 ONBOARDING.md §7。",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(
                    future_round_labels("f.py", prose + "\n", current=71), [],
                    "正當歷史引用被誤報 ⇒ 鎖會逼人把正確的句子改錯",
                )

    def test_a_synthetic_ledger_fixture_in_a_string_literal_is_not_flagged(self) -> None:
        """雙向坐實掃描面那一刀：同一串字放字串字面值不報、放註解要報。

        只證前者的話，`.py` 改成整檔逐行掃時本鎖不會說話（而那正是 9 筆假紅的來源）。
        """
        as_literal = 'row = "| DEF-01-001 | 情境 | open（承接輪次：R99） |"\n'
        self.assertEqual(
            future_round_labels("f.py", as_literal, current=71), [],
            "合成帳本語料被當成輪號標籤 ⇒ 假紅淹沒真訊號",
        )
        as_comment = '# 承接輪次：R99\n'
        self.assertTrue(
            future_round_labels("f.py", as_comment, current=71),
            "同一串字寫進註解卻不報 ⇒ 那一刀切過頭了",
        )

    def test_named_exemption_is_honoured_and_line_scoped(self) -> None:
        """具名豁免有效，且**只**及於同一行（不得整檔開天窗）。"""
        exempt = "# 合成語料 R99 條目 round-label-ok\n# R98 這一行沒掛豁免\n"
        self.assertEqual(
            [n for _, n, _ in future_round_labels("f.py", exempt, current=71)], [98],
            "豁免要嘛沒生效、要嘛外溢到下一行",
        )

    def test_unparseable_python_falls_back_to_whole_file_scan(self) -> None:
        """fail-closed：`.py` 解析不了就整檔掃，寧可吵也不可瞎。"""
        broken = "def f(:\n    # R99 本批\n"
        self.assertTrue(
            future_round_labels("f.py", broken, current=71),
            "解析失敗時靜默零命中 ⇒ 只要把檔寫壞就能繞過本鎖",
        )


class TestReassignHitJudgement(unittest.TestCase):
    """`_ledger_index.reassign_hit()` 的單元鑑別力（R74，`DEF-101-674` 結案的判準本體）。

    形態級逐項驗證，比 `orphan_backlog_problems()` 那一層更近判準本身：那一層還要湊出
    「未結案 ＋ 承接者早於當前輪」的前置條件，形態一多就會把測試意圖埋在 fixture 裡。
    """

    def test_affirmative_tokens_are_recognised(self) -> None:
        for cell in ("open（改派為：未指派）", "routed（本輪追記回執）",
                     "改派", "回執", "open；已於 R70 回執"):
            with self.subTest(cell=cell):
                self.assertTrue(m._reassign_hit(cell))

    def test_negated_tokens_are_rejected(self) -> None:
        """`無回執`／`零改派`／`未改派` 字面帶 token 而語意**相反**。"""
        for cell in ("open（無輪次無回執）", "open（零改派）", "open（未改派、未回執）",
                     "routed（沒有回執）", "open（非改派，只是記事）"):
            with self.subTest(cell=cell):
                self.assertFalse(m._reassign_hit(cell))

    def test_the_three_closed_forms_would_all_have_passed_the_old_judgement(self) -> None:
        """🔴 **鑑別力 A/B**：同一組輸入，舊判準（整列裸關鍵字比對）全部放行、新判準全部擋下。

        沒有這一組，上面三支「必須擋下」的斷言無法證明它們**曾經**是縫——一個從來就擋得住
        的形態，鎖上去只是裝飾。`_REASSIGN_RE` 仍以再匯出形式在（判準本體改用
        `reassign_hit()`），所以舊行為可以就地重現、不必動任何原始碼。
        """
        cases = {
            "跨欄": ("| DEF-9-9 | d | c | 另見 DEF-8-8 的改派紀錄 | P3 | 去向 | open |",
                     "open"),
            "引述": ("| DEF-9-9 | d | c | 現象 | P3 | 去向 | open（原欄文 `改派為：X`）|",
                     "open（原欄文 `改派為：X`）"),
            "否定": ("| DEF-9-9 | d | c | 現象 | P3 | 去向 | open（無輪次無回執）|",
                     "open（無輪次無回執）"),
        }
        for name, (whole_row, status_cell) in cases.items():
            with self.subTest(form=name):
                self.assertTrue(
                    m._REASSIGN_RE.search(whole_row),
                    f"{name}：舊判準（整列裸比對）本來就擋得住 ⇒ 這不是一條真縫，"
                    "本測試會是裝飾",
                )
                self.assertFalse(
                    m._reassign_hit(status_cell),
                    f"{name}：新判準仍放行 ⇒ 該形態的白拿豁免沒有真的被收掉",
                )

    def test_code_span_quotations_are_rejected(self) -> None:
        """反引號內是逐字引述（帳本體例），不是做出一次新的改派。"""
        self.assertFalse(m._reassign_hit("open（原欄文為 `改派為：未指派`，已被推翻）"))
        self.assertFalse(m._reassign_hit("routed（引述判準用語 `回執`）"))

    def test_a_bare_token_next_to_a_quotation_still_counts(self) -> None:
        """遮罩只遮反引號內：同欄另有一處**裸**的出口字樣時仍必須算數。

        沒有這一條，「把其中一處包進反引號」就會被誤讀成整欄豁免（收窄不得擴大成豁免口，
        同 `archive_defect_log.active_status_hit()` 的鑑別力保留 (a)）。
        """
        self.assertTrue(m._reassign_hit("open（原欄文 `改派為：X`）；本輪實際改派為：未指派"))

    def test_the_hit_is_shared_with_the_regex_re_export(self) -> None:
        """`_REASSIGN_RE` 與判準本體必須是**同一個 SSOT 的兩個名字**，不得漂成兩份。"""
        self.assertIs(m._REASSIGN_RE, m._ledger_index.REASSIGN_RE)
        self.assertIs(m._reassign_hit, m._ledger_index.reassign_hit)
        self.assertIs(m._CODE_SPAN_RE, m._ledger_index.CODE_SPAN_RE)


class TestResidualTodoAndSupersessionNotesHaveTeeth(unittest.TestCase):
    """🔴 R74 補測試覆蓋：這兩支偵測器在 R68 落地後**全 repo 零測試**（R74 PKG-2 補上）。

    為何非補不可：它們是「已結列殘留待辦」與「首詞待更新」這兩個中間態的**唯一**偵測器
    ——`_UNRESOLVED_CLASSES` 排除 `fixed`，所以那些列在結構上進不了承接稽核，而歸檔判準④
    同時擋住它們搬遷。零覆蓋的偵測器就是沒有牙的偵測器：它靜默失效時，那批列會同時逸出
    承接稽核與歸檔，沒有任何訊號。故兩支都要**雙向**驗（該命中的命中、不該命中的不命中）。
    """

    def test_residual_todo_flags_a_closed_row_that_still_carries_a_todo(self) -> None:
        notes = m.residual_todo_notes(_ledger_text(
            _row("DEF-01-901", "fixed@R70（殘餘兩項，承接輪次：未指派）")))
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("DEF-01-901", notes[0])
        self.assertIn("fixed", notes[0])

    def test_residual_todo_ignores_unresolved_rows(self) -> None:
        """未結列不由本支管（它們走承接稽核）——否則同一件事會被報兩次。"""
        self.assertEqual(m.residual_todo_notes(_ledger_text(
            _row("DEF-01-902", "open（承接輪次：未指派）"))), [])

    def test_residual_todo_is_silent_on_a_clean_closed_row(self) -> None:
        """不該命中的必須不命中：否則它退化成「每一列都印一次」＝等於沒印。"""
        self.assertEqual(m.residual_todo_notes(_ledger_text(
            _row("DEF-01-903", "fixed@R70（已完整落地並實測）"))), [])

    def test_supersession_flags_a_first_word_that_lags_its_own_correction(self) -> None:
        """`DEF-101-432` 的真實形態：首詞判未結，同欄後段已有「→ fixed」訂正。"""
        notes = m.supersession_notes(_ledger_text(
            _row("DEF-01-904", "open watch（R55）→ **fixed@R56**：已完整修復")))
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("DEF-01-904", notes[0])

    def test_supersession_ignores_a_quoted_correction(self) -> None:
        """反引號內是逐字引述 —— 已訂正過的列不該每輪再被點名一次。

        這正是 R74 對 `DEF-101-432` 的處置形態（首詞改 `fixed`、原欄文包進 code span
        保留於後）：處置完成後本支必須安靜，否則「該把首詞改了」這個提示永遠不會消失，
        而永不消失的提示會被讀者整批忽略。
        """
        self.assertEqual(m.supersession_notes(_ledger_text(
            _row("DEF-01-905",
                 "fixed@R56（訂正首詞）：`open watch（R55）→ **fixed@R56**`：已修"))), [])

    def test_supersession_is_silent_on_a_plain_unresolved_row(self) -> None:
        self.assertEqual(m.supersession_notes(_ledger_text(
            _row("DEF-01-906", "open（承接輪次：**R99**）"))), [])

    def test_both_detectors_are_wired_into_main(self) -> None:
        """可重跑而**沒有任何閘門看它的輸出**與不可重跑是同一個病（Scan-H 必跑項 #5）。"""
        src = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn("for note in supersession_notes(ledger_text):", src)
        self.assertIn("residual = residual_todo_notes(ledger_text)", src)
        self.assertIn("已結列殘留待辦", src)
        self.assertIn("狀態首詞待更新", src)


class TestUnresolvedInventoryHasASingleMeasurementEntry(unittest.TestCase):
    """🔴 R74 PKG-2：未結存量的唯一量測入口 ＋ 列數棘輪。

    立案理由：同一個問題「未結存量是多少」曾同時有三個互斥答案，而工作樹與上一輪收輪
    commit 完全相同 ⇒ 差異全部出自量測法不一致。三條臨時路徑其實各自回答不同問題
    （人工點數／`--plan` 的「不可搬」筆數〔六項判準聯集〕／逐列 `_classify`），只有最後
    一個才是未結列數。本類鎖住「入口只有一個、且它有上限」。
    """

    def test_unresolved_ids_counts_exactly_the_unresolved_classes(self) -> None:
        ledger = {"A": "open", "B": "routed", "C": None,
                  "D": "fixed", "E": "wontfix", "F": "closed-by-decision"}
        self.assertEqual(m._ledger_index.unresolved_ids(ledger), ["A", "B", "C"])

    def test_none_counts_as_unresolved(self) -> None:
        """「看不出結案」不等於「已結案」——含糊列必須算進存量，否則寫壞狀態欄即可脫帳。"""
        self.assertEqual(m._ledger_index.unresolved_ids({"X": None}), ["X"])

    def test_ceiling_is_a_ratchet_with_both_bands(self) -> None:
        warn, fail = (m._ledger_index.UNRESOLVED_ROWS_WARN,
                      m._ledger_index.UNRESOLVED_ROWS_FAIL)
        self.assertLess(warn, fail, "warn 必須嚴格小於 fail，否則 warn 帶不存在")
        below = {f"D-{i}": "open" for i in range(warn - 1)}
        self.assertEqual(m._ledger_index.unresolved_ceiling_problems(below), ([], []))
        at_warn = {f"D-{i}": "open" for i in range(warn)}
        f_, w_ = m._ledger_index.unresolved_ceiling_problems(at_warn)
        self.assertEqual(f_, [])
        self.assertEqual(len(w_), 1, "恰達 warn 線必須出聲")
        at_fail = {f"D-{i}": "open" for i in range(fail)}
        f2, w2 = m._ledger_index.unresolved_ceiling_problems(at_fail)
        self.assertEqual(len(f2), 1, "恰達 fail 線必須 fail，不是只 warn")
        self.assertEqual(w2, [], "同時 warn＋fail 會讓同一件事被報兩次")
        self.assertIn("不要調高本門檻", f2[0])

    def test_closed_rows_never_reduce_the_count_by_being_archived(self) -> None:
        """🔴 本鎖的核心語意：門檻面刻意是**列數**而不是 bytes。

        bytes 會被歸檔動作攪動，於是「靠歸檔把數字壓下去」可以掩蓋未結存量持續累積；
        未結列在結構上不可歸檔，所以列數問的正是「還有幾筆缺陷沒人處理」。此處以構造
        輸入證明：把任意多筆**已結**列加進帳本，未結列數一動也不動。
        """
        base = {f"U-{i}": "open" for i in range(10)}
        padded = {**base, **{f"C-{i}": "fixed" for i in range(500)}}
        self.assertEqual(len(m._ledger_index.unresolved_ids(base)),
                         len(m._ledger_index.unresolved_ids(padded)))

    def test_the_cli_entry_point_exists_and_prints_the_ids(self) -> None:
        """只印一個數字的載具無法被複驗（下一個人只能相信它）⇒ 必須連 ID 一起印。"""
        r = subprocess.run(
            [sys.executable, str(Path(m.__file__)), "--unresolved-count"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertIn("未結列數＝", r.stdout)
        self.assertIn("未結列 ID：", r.stdout)
        self.assertRegex(r.stdout, r"DEF-\d+-\d+")
        self.assertIn("--unresolved-count", m._USAGE)

    def test_main_actually_enforces_the_ceiling(self) -> None:
        """接線鎖：門檻若只被印出來而沒有任何 `return 1`，它就是 `DEF-101-731` 的重演。"""
        src = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn("unresolved_ceiling_problems(ledger)", src)
        self.assertIn("unpinned_problems += unres_fails", src)


# ── 早退遮蔽 ＋ 「訊息教人加內容的檔必須加得下」（P0-A；本批落地） ─────────────────
# 兩道鎖同源於一次實測事故：帳本目錄新增一份未登記的治理文件時，本工具**只印 2 行**
# （`❌ 具名治理文件涵蓋面與磁碟脫節` ＋ 那一筆），原本會印的 8 筆孤兒 warning、18 筆
# 已結列殘留待辦全部消失——而讀者看到的是「輸出變乾淨了」。同一則訊息教人「請在該常數
# 補上一筆」，但那支檔當時卡在 raw-line 棘輪 1474/1474、**餘裕 0 行**，照做即破另一道
# 硬閘 ⇒ 訊息在磁碟現況下不可執行，兩道鎖互為對方的違規。
#
# 誠實劃界（R76 複審後訂正——原文對第二半的宣稱在寫下當回合就是假的，見下方表的訂正段）：
#   · **早退遮蔽**那一半只管 `check_defect_log_crossref.py` 這一支工具的檢查序（`main()`
#     的 `_bail()` 紀律），其他工具不在射程內；那需要一套跨工具的檢查序模型，本鎖不假裝有。
#   · **「訊息教人加內容 ⇒ 該檔加得下」**那一半是**真的跨工具**：登記表
#     `_ADD_CONTENT_DIRECTIVES` 現為三欄，餘裕斷言逐筆迭代第三欄，加一筆就真的把那支
#     工具納管進來（現有兩支：本工具 ＋ `tools/sync_onboarding_baselines.py`）。
#     加一筆時**必須同時**在 `_message()` 的 dispatch 表補一支訊息產生器，否則當場 fail。
#   · 仍不在射程內：訊息教人加內容的檔若不在 `check_loc_budget.SPECIAL_FILES` 裡（例如
#     `AutoClaude/` 側的 tier 分級檔），本鎖量不到餘裕、會 fail-loud 要求先納管。


def _main_source() -> str:
    return Path(m.__file__).read_text(encoding="utf-8")


def _bail_headers_in_main_order() -> list[str]:
    """`main()` 原始碼裡 `_bail("<header>"…)` 的**行號序**（以 AST 取，不靠正則猜）。

    刻意依 `lineno` 排序而不是 `ast.walk()` 的輸出序：後者是 BFS，巢在 `for`／`if` 裡
    的呼叫會被排到最後（實測「帳本歸檔體積」「掃描目標齊備」兩道就是這樣被排錯的），
    那會讓本鎖對真正的順序錯置失去鑑別力，同時又對正確的程式碼假紅。
    """
    tree = ast.parse(_main_source())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "_bail"
        and node.args and isinstance(node.args[0], ast.Constant)
    ]
    return [c.args[0].value for c in sorted(calls, key=lambda c: c.lineno)]


class TestEarlyExitAnnouncesUnrunChecks(unittest.TestCase):
    """早退時必須明說「還有幾道沒跑」，且 `_CHECK_ORDER` 與 `main()` 逐名對齊。"""

    def test_main_has_no_bare_return_one(self) -> None:
        """🔴 本組鎖的本體：`main()` 內不得有任何**不經 `_bail()`** 的 `return 1`。

        繞過 `_bail()` 就等於繞過「尚有 N 道未執行」那句話——而那句話正是這次事故裡
        缺席的東西。以 AST 判（不是 grep），故 `return 1  # 註解` 之類也躲不掉。
        """
        tree = ast.parse(_main_source())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        bare = [
            node.lineno for node in ast.walk(fn)
            if isinstance(node, ast.Return)
            and isinstance(node.value, ast.Constant) and node.value.value == 1
        ]
        self.assertEqual(
            bare, [],
            f"main() :{bare} 直接 `return 1` 而未經 `_bail()` ⇒ 該早退點不會告訴讀者"
            "後面還有哪幾道檢查沒跑，輸出變短會被誤讀成「問題變少」",
        )

    def test_every_bail_header_is_registered_and_in_execution_order(self) -> None:
        """`_CHECK_ORDER` ↔ `main()` 雙向：漏登記或順序不符即紅（否則殘餘清單說謊）。"""
        used = _bail_headers_in_main_order()
        self.assertTrue(used, "main() 內找不到任何 `_bail(...)` 呼叫 ⇒ 早退未被納管")
        unknown = [h for h in used if h not in m._CHECK_ORDER]
        self.assertEqual(unknown, [], f"這些早退點的名稱不在 _CHECK_ORDER 內：{unknown}")
        ranks = [m._CHECK_ORDER.index(h) for h in used]
        self.assertEqual(ranks, sorted(ranks),
                         f"_CHECK_ORDER 的排序與 main() 實際執行序不符：{used}")
        never = [h for h in m._CHECK_ORDER if h not in used]
        self.assertEqual(never, [],
                         f"_CHECK_ORDER 登記了 main() 不會走到的名目：{never}"
                         "（會讓「尚有 N 道未執行」把不存在的檢查算進去）")

    def test_the_message_names_the_remaining_checks(self) -> None:
        """鑑別力：從**第一道**早退，訊息必須點名其後全部檢查。"""
        with mock.patch("builtins.print") as fake:
            rc = m._bail(m._CHECK_ORDER[0], detail="x")
        printed = " ".join(str(a) for c in fake.call_args_list for a in c.args)
        self.assertEqual(rc, 1)
        self.assertIn(f"尚有 {len(m._CHECK_ORDER) - 1} 道檢查", printed)
        for header in m._CHECK_ORDER[1:]:
            self.assertIn(header, printed, f"殘餘清單漏掉 {header!r}")

    def test_the_last_check_does_not_claim_phantom_remainders(self) -> None:
        """反向：最後一道早退時**不得**再說「尚有 N 道未執行」（那會是假話）。"""
        with mock.patch("builtins.print") as fake:
            m._bail(m._CHECK_ORDER[-1], ["p"])
        printed = " ".join(str(a) for c in fake.call_args_list for a in c.args)
        self.assertNotIn("尚有", printed)

    def test_an_unregistered_header_fails_loud_instead_of_lying(self) -> None:
        """未登記的名目不得靜默：殘餘清單算不出來時要說出來，不可假裝算得出。"""
        with mock.patch("builtins.print") as fake:
            m._bail("這個名目不存在", ["p"])
        printed = " ".join(str(a) for c in fake.call_args_list for a in c.args)
        self.assertIn("不在 _CHECK_ORDER", printed)

    def test_the_real_gate_still_reaches_the_late_checks(self) -> None:
        """端到端：真實 repo 上必須真的跑到**最後一道**，而不是在中途早退後顯綠。

        沒有這一條，上面幾道都可能在「工具早退但 rc 恰為 0」的世界裡全綠。
        """
        r = subprocess.run(
            [sys.executable, str(Path(m.__file__))],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        self.assertIn("未結存量", r.stdout, "成功訊息缺末段 ⇒ 尾端檢查可能沒跑到")
        self.assertNotIn("尚有", r.stderr.split("已結列殘留待辦")[0])


#: 「錯誤訊息教人往某檔加內容」的登記表：`(訊息產生器, 訊息必含的識別字, 被要求編輯的檔)`。
#: 訊息一律**當場真的產生一次**（不是讀 docstring）——讀 docstring 的鎖抓不到「訊息被改寫
#: 成指向別的檔」。
#:
#: 🔴 R76 複審 ARCH-02／SD-02 訂正：本表落地首版**只有兩欄**（第三欄「被要求編輯的檔」
#: 在註解裡宣告、在實作裡不存在），而餘裕斷言硬編 `Path(m.__file__)`、根本不讀本表 ⇒
#: 上方 `:2333` 那句「要納入就在本表加一筆」是假的：照三欄格式加一筆會 `ValueError:
#: too many values to unpack`，退成兩欄則 `_message()` 靜默跑到別支函式、產生一則講
#: 別的常數的誤導訊息。現已補成真三欄、餘裕斷言逐筆迭代、`_message()` 具名 dispatch
#: 且未知名字 fail-loud。同時把第二支工具真的納管進來（那正是它「做成表格」的意義）。
_ADD_CONTENT_DIRECTIVES: tuple[tuple[str, str, str], ...] = (
    ("unregistered_governance_docs", "_GOVERNANCE_DOCS",
     "tools/check_defect_log_crossref.py"),
    ("stale_grandfather_problems", "_UNPINNED_HANDOVER_GRANDFATHERED",
     "tools/check_defect_log_crossref.py"),
    ("unclassifiable_first_word_problems", "_STATUS_KEYWORDS",
     "tools/check_defect_log_crossref.py"),
    # 第二支工具（R76 納管）：`--write --with-slow` 在無對應平台欄時 rc=2 並教人
    # 「在 `_PLATFORM_COLUMN_LABELS` 加一筆」；`prose_problems()` 則教人「在 `_SPECS`
    # 的 `historical` 登記 (輪號, 值, WHY)」。兩則都住同一支檔，故餘裕只需量一次。
    ("sync_platform_column_labels", "_PLATFORM_COLUMN_LABELS",
     "tools/sync_onboarding_baselines.py"),
    ("sync_historical_registration", "historical",
     "tools/sync_onboarding_baselines.py"),
)

#: 「照著訊息做」最少要花掉的行數：1 行常數 ＋ 該訊息自己要求的 WHY 註解（實測 2~4 行）。
#: 低於此值時訊息在磁碟現況下**不可執行**。刻意不設更大值——那會變成憑空的舒適區。
_MIN_DIRECTIVE_HEADROOM = 5


def _loc_budget_module():
    """以檔案路徑載入 `AutoClaude/tools/check_loc_budget.py`（LOC 上限的唯一權威源）。

    🔴 `sys.modules[name] = mod` 必須在 `exec_module` **之前**：該檔用 `@dataclass`，
    而 `dataclasses` 會回查 `sys.modules[cls.__module__].__dict__`，沒先註冊會炸
    `AttributeError: 'NoneType' object has no attribute '__dict__'`（實測）。
    """
    import importlib.util
    name = "_clb_for_test"
    if name in sys.modules:
        return sys.modules[name]
    path = m._REPO_ROOT / "AutoClaude" / "tools" / "check_loc_budget.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _sync_module():
    """以檔案路徑載入 `tools/sync_onboarding_baselines.py`（本表第二支受管工具）。

    以路徑載入而非 `import`：該檔名與本檔不同層，且它自己會 `sys.path.insert` tools/。
    """
    import importlib.util
    name = "_sync_ob_for_test"
    if name in sys.modules:
        return sys.modules[name]
    path = m._REPO_ROOT / "tools" / "sync_onboarding_baselines.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _raw_line_headroom(path: Path) -> int | None:
    """該檔在 `check_loc_budget.SPECIAL_FILES` 的 raw-line 餘裕；未納管回 `None`。"""
    clb = _loc_budget_module()
    for key, budget in clb.SPECIAL_FILES.items():
        try:
            candidate = (clb.PROJECT_ROOT / key).resolve()
        except OSError:  # pragma: no cover - 非本平台的分隔符寫法
            continue
        if candidate == path.resolve():
            return budget - clb.count_raw_lines(path)
    return None


class TestActionableMessagesHaveLocHeadroom(unittest.TestCase):
    """Scan-H 必跑項⑥：訊息教人「往某檔加內容」時，該檔必須真的加得下。

    🔴 為何是**一般化**判準而不是「這次把那支檔瘦一點」：兩道硬閘各自都對，衝突在於
    沒有任何東西在看「A 的合法動作是不是 B 的違規」。一支卡在棘輪上限的檔，它所有
    「請在此加一筆」的訊息就全部變成死路，而讀者只會看到兩個互相矛盾的紅。

    🔴 「一般化」在 R76 落地首版是一句**空話**（複審 ARCH-02／SD-02）：餘裕斷言硬編
    `Path(m.__file__)`、完全不讀登記表，所以「加一筆就納入」加了也沒用；而磁碟上當時
    就有第二個實例（`tools/sync_onboarding_baselines.py` 餘裕 2 < 5）沒被看見。現在
    斷言逐筆迭代登記表第三欄，且那支檔已瘦身到餘裕 ≥5 並正式登記。
    """

    def test_each_directive_message_names_its_target_constant(self) -> None:
        """前提：訊息真的指名了要改哪個常數，否則「加得下」也無從執行。"""
        for fn_name, needle, _target in _ADD_CONTENT_DIRECTIVES:
            with self.subTest(fn=fn_name):
                self.assertIn(needle, self._message(fn_name))

    def test_the_registered_targets_still_have_room_for_those_edits(self) -> None:
        """逐筆迭代**本表第三欄**——不是硬編某一支檔。

        硬編版的病：加一筆進本表對餘裕斷言零效果，而註解卻宣稱「加一筆就納入了」，
        於是加的人拿到一個看不見的覆蓋幻覺（R76 複審 ARCH-02／SD-02）。
        """
        checked: set[str] = set()
        for fn_name, _needle, rel in _ADD_CONTENT_DIRECTIVES:
            if rel in checked:
                continue          # 同一支檔的多則訊息共用同一份餘裕，量一次即可
            checked.add(rel)
            with self.subTest(target=rel):
                target = m._REPO_ROOT / rel
                self.assertTrue(target.is_file(), f"{rel} 不存在 ⇒ 本表第三欄已 stale")
                headroom = _raw_line_headroom(target)
                self.assertIsNotNone(
                    headroom,
                    f"{rel} 不在 check_loc_budget.SPECIAL_FILES 內 —— 本鎖對它失去量測面。"
                    f"要嘛把它納管進 SPECIAL_FILES，要嘛把這一列從本表移除並說明理由",
                )
                self.assertGreaterEqual(
                    headroom, _MIN_DIRECTIVE_HEADROOM,
                    f"{rel} 的 raw-line 餘裕只剩 {headroom} 行，而它自己的錯誤訊息"
                    f"（{fn_name}）教人「請在 `{_needle}` 補上一筆」⇒ 照做即撞 LOC 棘輪，"
                    f"訊息在磁碟現況下**不可執行**。"
                    f"🔴 正解是**瘦身**（刪死碼／併註解／抽共用模組），"
                    f"**不得**調高 check_loc_budget.SPECIAL_FILES 的上限（那是砸溫度計）",
                )
        self.assertGreaterEqual(
            len(checked), 2,
            "本表只納管了一支檔 ⇒ 又退回硬編那種形態（見本表上方的 R76 訂正段）")

    def _message(self, fn_name: str) -> str:
        """具名 dispatch：未知名字 **fail-loud**，不得靜默 fallback 到別支函式。

        舊版是 if/elif 且最後一支沒有守衛，任何不認得的名字都會落到
        `unclassifiable_first_word_problems()` ⇒ 讀者拿到一則講別的常數的誤導紅。
        """
        builders = {
            "unregistered_governance_docs": self._msg_governance_docs,
            "stale_grandfather_problems": self._msg_stale_grandfather,
            "unclassifiable_first_word_problems": self._msg_unclassifiable,
            "sync_platform_column_labels": self._msg_sync_platform_labels,
            "sync_historical_registration": self._msg_sync_historical,
        }
        builder = builders.get(fn_name)
        if builder is None:
            self.fail(
                f"`{fn_name}` 沒有對應的訊息產生器 —— 在 `_ADD_CONTENT_DIRECTIVES` 加一筆"
                f"時必須同時在 `_message()` 的 dispatch 表補一支產生器。"
                f"現有：{sorted(builders)}")
        return builder()

    @staticmethod
    def _msg_governance_docs() -> str:
        with mock.patch.object(m, "_GOVERNANCE_DOCS", m._GOVERNANCE_DOCS[:-1]):
            return " ".join(m.unregistered_governance_docs())

    @staticmethod
    def _msg_stale_grandfather() -> str:
        with mock.patch.object(m, "_UNPINNED_HANDOVER_GRANDFATHERED",
                               frozenset({"DEF-99-999"})):
            return " ".join(m.stale_grandfather_problems(_LEDGER_MIN))

    @staticmethod
    def _msg_unclassifiable() -> str:
        with mock.patch.object(m, "_STATUS_FIRST_WORDS",
                               m._STATUS_FIRST_WORDS | {"never-classifiable-xyz"}):
            return " ".join(m.unclassifiable_first_word_problems())

    @staticmethod
    def _msg_sync_platform_labels() -> str:
        """真跑 `--write --with-slow` 在「本平台無對應欄」時那條路徑（stderr 捕捉）。"""
        syn = _sync_module()

        def _forbid_write(*_a, **_k):     # 探針絕不得改到真的 ONBOARDING.md
            raise AssertionError("訊息探針不該走到寫檔路徑")

        with mock.patch.object(syn, "current_platform_key", lambda *a, **k: None), \
                mock.patch.object(Path, "write_bytes", _forbid_write), \
                mock.patch("sys.stderr", io.StringIO()) as err:
            rc = syn.main(["--write", "--with-slow"])
        assert rc == 2, f"該路徑應 fail-loud rc=2，實得 {rc}"
        return err.getvalue()

    @staticmethod
    def _msg_sync_historical() -> str:
        """真跑 `prose_problems()` 的「未登記歷史值」分支（純函式，零磁碟接觸）。"""
        syn = _sync_module()
        spec = syn._SPECS[0]
        live = {f.name: 111 + i for i, f in enumerate(spec.fields)}
        return " ".join(syn.prose_problems("R42=987654 見上", spec, live))


#: 給上面 `stale_grandfather_problems` 用的最小合法帳本（表頭 ＋ 一列已結）。
_LEDGER_MIN = (
    "| ID | 日期 | 發現情境 | 現象與證據 | 嚴重度 | 分流去向 | 狀態 |\n"
    "|---|---|---|---|---|---|---|\n"
    "| DEF-01-001 | d | R75 | x | P3 | y | fixed |\n"
)


if __name__ == "__main__":
    unittest.main()
