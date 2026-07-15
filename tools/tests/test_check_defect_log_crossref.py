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

    def test_markdown_bold_around_id_still_matches(self) -> None:
        target = _write_tmp("重點：**DEF-01-002**（open，記事存證）。\n")
        self.assertEqual(m._scan_target(target, self.ledger), [])
        target2 = _write_tmp("重點：**DEF-01-001**（open，記事存證）。\n")
        problems = m._scan_target(target2, self.ledger)
        self.assertEqual(len(problems), 1)


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

    def test_main_returns_1_when_ledger_missing(self) -> None:
        missing = Path(_TMP_DIR) / "does_not_exist_defect_log.md"
        with mock.patch.object(m, "_DEFECT_LOG", missing), mock.patch("builtins.print"):
            self.assertEqual(m.main(), 1)

    def test_main_against_real_repo_is_clean(self) -> None:
        """對真實 repo 現況跑一次（無 mock）——本次修復 DEF-101-056/057 的 ONBOARDING.md
        誤記後，這是防止未來再度漂移而未被察覺的迴歸鎖。"""
        with mock.patch("builtins.print"):
            self.assertEqual(m.main(), 0)


if __name__ == "__main__":
    unittest.main()
