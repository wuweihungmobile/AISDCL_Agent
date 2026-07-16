#!/usr/bin/env python3
"""tools/check_defect_log_crossref.py 的單元測試（DEF-101-068(e) 落地：DEF-101-066 這類
「改帳本忘同步姊妹文件」問題類別的機械守護，鏡子自身也要有測試，不可只憑人工複審碰運氣）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
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


def _ledger_text(rows: str) -> str:
    header = (
        "# 缺陷帳本\n\n"
        "| ID | 發現日期 | 發現情境 | 現象 | 嚴重度 | 分流去向 | 狀態 |\n"
        "|----|----------|----------|------|--------|----------|------|\n"
    )
    return header + rows


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
        self.assertEqual(m._classify("closed-by-decision（本輪四方複審拍板）"), "closed-by-decision")

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
            "| DEF-01-001 | 2026-06-13 | 情境 | 現象 | P2 | 去向 | pending-reassessment（無合法關鍵字） |\n"
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
        須以 warning 列出 ID 分開呈現；含糊本身是帳本品質提示，不 fail（exit 0）。"""
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
            "| DEF-01-002 | 2026-06-13 | 情境 | 現象 | P3 | 去向 | pending-reassessment（無合法關鍵字） |\n"
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


if __name__ == "__main__":
    unittest.main()
