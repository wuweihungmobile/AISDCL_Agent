#!/usr/bin/env python3
"""tools/check_defect_log_crossref.py 的單元測試（DEF-101-068(e) 落地：DEF-101-066 這類
「改帳本忘同步姊妹文件」問題類別的機械守護，鏡子自身也要有測試，不可只憑人工複審碰運氣）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import re
import shutil
import sys
import tempfile
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

    def test_main_separates_vague_rows_from_valid_count_and_does_not_fail(self) -> None:
        """R9 跨平台複審：狀態含糊列（_classify 回 None）不可被計入「有效狀態紀錄」，
        須以 warning 列出 ID 分開呈現；含糊本身是帳本品質提示，不 fail（exit 0）。

        🔴 R60：含糊 fixture 由 `pending-reassessment（…）` 換成 `partial@R60（…）`。
        「含糊」（`_classify` 回 None）與「首詞非法」（不在《格式定義》合法集合內）是
        **兩個獨立概念**，舊 fixture 剛好同時命中兩者，於是兩道鎖對同一份輸入各自要求
        rc=0 與 rc=1，測試無論綠或紅都無法解讀（分野三例見
        `TestStatusFirstWordProblems` class docstring）。要驗的既然是「含糊不 fail」，
        fixture 就必須是「含糊**但首詞合法**」——`partial@R60` 正是這種形態（首詞
        `partial` 在合法集合內，而 `_classify` 認不出 `partial` 故仍為含糊）。
        ⚠️ 反過來把 `check_defect_log_crossref.py` 的首詞鎖放寬來讓本測試變綠是錯的：
        那是為了測試好看而拆掉本輪剛加的守門。
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
        self.assertIn("狀態含糊", printed)
        self.assertIn("DEF-01-002", printed)          # 含糊列 ID 有被列出
        self.assertIn("1 筆有效狀態紀錄", printed)     # 有效數＝總數 2 − 含糊 1

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


class TestEvidenceFamilyPointersResolve(unittest.TestCase):
    """帳本裡「見 `<檔>` 的 `## DEF-101-NNN` 節」必須真的找得到那個錨（DEF-101-587）。

    R60 round 3 把證據檔拆成入口檔＋姊妹檔。拆分**當下**零失實（具名節指針全部 ≤560、
    都留在入口檔），但那是**手驗**的結果——下一次有人再搬一節、或帳本新增一個指向已搬走
    節次的指針，就會靜默失實。本鎖把那次手驗機械化。

    與 `archive_defect_log.py` 判準④／⑥ 的差別：那兩項守的是**帳本家族內**的居所宣稱，
    本項守的是**帳本 → 證據檔**的跨檔錨點。同一個病（指針失實），不同的邊。
    """

    _POINTER_RE = re.compile(
        r"`(?P<file>CrossPlatform_R60_Fix_Evidence(?:_\w+)?\.md)`?\s*的\s*"
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


if __name__ == "__main__":
    unittest.main()
