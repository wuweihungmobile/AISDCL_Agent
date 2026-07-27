#!/usr/bin/env python3
"""tools/check_defect_log_crossref.py 的單元測試（DEF-101-068(e) 落地：DEF-101-066 這類
「改帳本忘同步姊妹文件」問題類別的機械守護，鏡子自身也要有測試，不可只憑人工複審碰運氣）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import re
import shutil
import subprocess
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

# 🔴 合成用的「帳本查無」編號一律以**字串拼接**產生，不寫完整字面值。
# WHY：D 類反向懸空引用掃描（SA-R58R1-03）的掃描面是全 repo git-tracked 檔案，
# **本測試檔自己也在裡面**。一旦某處出現完整的 `DEF-<數字>-<數字>` 字面值，就等於在
# repo 內新增一筆真的懸空引用，讓 `tools/check_defect_log_crossref.py` 對真實 repo 永遠
# 紅（而且是測試檔自己造成的假紅）。拼接後 `_REVERSE_ID_RE` 抽不到任何編號，測試意圖
# 完全不變。需要「帳本查無且**未被白名單豁免**」的編號時請沿用下面這兩個常數，
# 並且**連註解裡也不要**把它們寫成完整字面值——本次落地就是這樣自製了一筆懸空引用，
# 由新落地的掃描器當場抓出來（意外成了它有效的第一份證據）。
_FAKE_ID = "DEF-" + "77-777"
_FAKE_ID_2 = "DEF-" + "77-778"

# 凍結版目錄的**字面**前綴，供剔除規則的驗收使用。刻意獨立於
# `m._REVERSE_SCAN_EXCLUDE_RE`——用被測物自己的 regex 來驗它排對了沒，是同義反覆
# （bug-injection 實測會全綠，見 `TestTrackedScanPaths` 該案 docstring）。
_FROZEN_PREFIX = "AISDLC_SDD/AISDLC_SDD_v0."


def _patch_reverse(problems: tuple[str, ...] = ()) -> object:
    """把 D 類反向掃描隔離成固定結果。

    WHY：`_check_reverse_refs()` 掃的是**真實 repo**（`_REPO_ROOT` + `git ls-files`），
    而 `TestMain` 其餘 case 全部把 `_DEFECT_LOG` 換成只有一兩列的合成帳本——此時真實
    repo 的每一個 DEF 引用都會被判懸空，main() 恆紅，那些 case 就再也測不到它們原本
    要測的東西（A 類矛盾／體積界線／索引完整性）。故此處明確隔離，D 類自己另有
    `TestReverseRefs*` 系列直接測。
    """
    return mock.patch.object(m, "_check_reverse_refs", return_value=list(problems))


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


def _archive_name(num: int) -> str:
    return f"AutoSDD_Defect_Log_archive_{num:02d}.md"


def _index_section(entry_names: list[str], header_cn: str | None = None) -> str:
    """產生〈已歸檔內容〉索引節文字（DEF-101-510 守門的比對對象）。

    header_cn=None → 依條目數自動生成**正確**的中文數字（乾淨案例）；傳入字串則
    刻意寫死一個可能 stale 的數字（測標題新鮮度守門）。
    """
    if header_cn is None:
        header_cn = m._int_to_cn(len(entry_names)) or str(len(entry_names))
    lines = [f"> **已歸檔內容**（**{header_cn}檔**；fixture）：\n"]
    lines += [f"> - **`{n}`**（fixture 條目）：內容敘述。\n" for n in entry_names]
    return "\n" + "".join(lines)


def _build_ledger_dir(
    name: str,
    disk_nums: list[int],
    entry_names: list[str] | None = None,
    header_cn: str | None = None,
    index_section: bool = True,
    extra_text: str = "",
    archive_bytes: int = 16,
) -> Path:
    """造一份「主檔 + N 個 archive 檔」的獨立暫存帳本目錄，回傳主檔路徑。

    需獨立目錄：archive glob 掃 `_DEFECT_LOG.parent`，共用 _TMP_DIR 會讓各 case
    的 archive 互相污染（沿用 R10 QA-9／DEF-101-138 的既有教訓）。
    """
    d = _TMP_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    for num in disk_nums:
        (d / _archive_name(num)).write_text("x" * archive_bytes, encoding="utf-8")
    if entry_names is None:
        entry_names = [_archive_name(n) for n in sorted(disk_nums)]
    body = _ledger_text("| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed@x |\n")
    if index_section:
        body += _index_section(entry_names, header_cn)
    body += extra_text
    ledger = d / "AutoSDD_Defect_Log.md"
    ledger.write_text(body, encoding="utf-8")
    return ledger


def _write_scan_tree(name: str, files: dict[str, str | bytes]) -> tuple[Path, list[str]]:
    """造一棵合成「掃描面」目錄樹，回傳 `(root, rel_paths)` 供 `_scan_reverse_refs` 使用。

    值為 `bytes` 時原樣寫入（用來造二進位檔案案例）。rel 路徑一律用 `/`，與
    `git ls-files` 的輸出形式一致。
    """
    root = _TMP_DIR / name
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return root, list(files)


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
             _patch_reverse(), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        # 明確釘住「紅的原因是 A 類矛盾」，而非湊巧被別類守門帶紅
        self.assertIn("跨文件狀態不一致", printed)

    def test_main_returns_0_when_consistent(self) -> None:
        ledger_text = _ledger_text(
            "| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix+凍結版紀律 |\n"
        )
        target_text = "文件敘述 DEF-01-001（wontfix，記事存證）。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(ledger_text)), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [_write_tmp(target_text)]), \
             _patch_reverse(), \
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
             _patch_reverse(), \
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
             _patch_reverse(), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("逼近輪替上限", printed)

    def _make_isolated_ledger_dir(self, name: str, archive_bytes: int) -> Path:
        """R10 QA-9（DEF-101-138）：archive 守門測試需獨立目錄——archive glob 掃
        `_DEFECT_LOG.parent`，若沿用共用 _TMP_DIR，超線 archive 會污染其他 case。

        DEF-101-510 落地後 fixture 須額外備妥合法索引節、且 archive 編號改用 01
        （原本用 99 會被新增的「編號連續性」守門判為缺號 02~98，體積守門測試會混入
        索引守門的紅燈而失去針對性）。
        """
        return _build_ledger_dir(name, [1], archive_bytes=archive_bytes)

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
        self.assertIn("archive_01", printed)

    def test_main_warns_but_passes_when_archive_approaches_limit(self) -> None:
        """R10 QA-9：archive 檔於 240KB~256KB 預警帶 → warning 不 fail。"""
        ledger = self._make_isolated_ledger_dir(
            "archive_warn", m._LEDGER_WARN_BYTES + 100
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             _patch_reverse(), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("已逼近上限", printed)
        self.assertIn("archive_01", printed)

    def test_main_against_real_repo_clean_except_reverse_scan(self) -> None:
        """對真實 repo 現況跑一次（除 D 類反向掃描外皆無 mock）——本次修復 DEF-101-056/057
        的 ONBOARDING.md 誤記後，這是防止未來再度漂移而未被察覺的迴歸鎖。

        🔴 為何獨獨隔離 D 類（SA-R58R1-03 落地後改名自 `..._is_clean`）：D 類的紅綠取決於
        「帳本條目寫了沒」這個**流程狀態**，而寫帳本是每一輪的收尾步驟——本輪修復落地時
        帳本條目尚未寫入，D 類必然是紅的。若讓本 case 一併斷言 D 類，它就會在每一輪的
        「修復已落地、帳本還沒寫」這段時間內恆紅，逼人為了讓測試綠而把新編號塞進廢號
        白名單（＝把假綠制度化）。D 類對真實 repo 的斷言責任交給 pre-push／CI 直接跑
        CLI（`python tools/check_defect_log_crossref.py`），那才是它該擋的地方；
        本測試檔只負責鎖 D 類的**邏輯**（見 `TestReverseRefs*` 系列，全用合成 fixture）。
        """
        with _patch_reverse(), mock.patch("builtins.print"):
            self.assertEqual(m.main(), 0)

    def test_main_returns_1_when_archive_index_incomplete(self) -> None:
        """DEF-101-510 端到端：索引漏登必須讓 main() 回 1（體積全綠也不放行）。"""
        ledger = _build_ledger_dir(
            "index_e2e", [1, 2], entry_names=[_archive_name(1)], header_cn="一"
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("帳本歸檔索引與磁碟不一致", printed)
        self.assertIn(_archive_name(2), printed)


class TestChineseNumeralConversion(unittest.TestCase):
    """DEF-101-510 的中文數字轉換：索引節標題寫的是中文數字（「二十八檔」），
    要跟磁碟檔數比對就必須能雙向換算。**轉換失效即整道鎖失效**，故獨立測。"""

    def test_round_trip_over_wide_range(self) -> None:
        """1~999 全數 round-trip（涵蓋十位省略「一」、百位帶零等中文慣寫），
        另抽驗千位邊界。刻意覆蓋遠超實際需求的範圍：archive 檔數只增不減，
        鎖必須在數十年後仍有效。"""
        for n in list(range(1, 1000)) + [1000, 1001, 1010, 1100, 9999]:
            with self.subTest(n=n):
                cn = m._int_to_cn(n)
                self.assertIsNotNone(cn, f"{n} 應可轉為中文數字")
                self.assertEqual(m._cn_to_int(cn), n, f"{n} → {cn} → 反解不一致")

    def test_conventional_writings_parse(self) -> None:
        """本 repo 帳本歷史上實際出現過的寫法（「二十一」～「二十八」）與慣寫「十」。"""
        self.assertEqual(m._cn_to_int("二十八"), 28)
        self.assertEqual(m._cn_to_int("二十一"), 21)
        self.assertEqual(m._cn_to_int("十"), 10)
        self.assertEqual(m._cn_to_int("十五"), 15)
        self.assertEqual(m._int_to_cn(28), "二十八")
        self.assertEqual(m._int_to_cn(10), "十")

    def test_unsupported_writing_returns_none_for_fail_loud(self) -> None:
        """超出支援範圍／非法寫法必須回 None（由呼叫端 fail loud）——**不可**
        猜一個數字或靜默視為通過，否則這道鎖將來會自己失效（本 repo 反覆踩過
        「守門靜默縮面」）。"""
        self.assertIsNone(m._cn_to_int("一萬"))        # 「萬」未支援
        self.assertIsNone(m._cn_to_int("廿八"))        # 異體寫法未支援
        self.assertIsNone(m._cn_to_int("一二"))        # 相鄰數字非合法中文數字
        self.assertIsNone(m._cn_to_int("28"))          # 阿拉伯數字不在本轉換職責內
        self.assertIsNone(m._int_to_cn(0))
        self.assertIsNone(m._int_to_cn(10000))


class TestArchiveIndexIntegrity(unittest.TestCase):
    """帳本〈已歸檔內容〉索引 vs 磁碟 archive 檔的機械守門（DEF-101-510）。

    WHY：R56 真的漏登過一檔（DEF-101-476，引用鏈斷裂），R57 起連三輪靠人工核對
    「索引條目數 == 磁碟檔數」——靠人記得＝必然腐化。本類鎖住三道檢查各自能翻紅。
    """

    def test_clean_index_passes(self) -> None:
        ledger = _build_ledger_dir("idx_clean", [1, 2, 3])
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            self.assertEqual(m._check_archive_index(), [])

    def test_missing_entry_flagged(self) -> None:
        """磁碟有、索引沒登記 → 紅，且訊息須指名是哪一檔（R56 漏登的真實形狀）。"""
        ledger = _build_ledger_dir(
            "idx_missing", [1, 2, 3],
            entry_names=[_archive_name(1), _archive_name(2)], header_cn="二",
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("未登記", problems[0])
        self.assertIn(_archive_name(3), problems[0])

    def test_stale_entry_flagged(self) -> None:
        """索引登記了但磁碟不存在（誤刪／誤更名）→ 反向也要紅。"""
        ledger = _build_ledger_dir(
            "idx_stale", [1, 2],
            entry_names=[_archive_name(n) for n in (1, 2, 3)], header_cn="三",
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("磁碟不存在", problems[0])
        self.assertIn(_archive_name(3), problems[0])

    def test_header_numeral_stale_flagged_with_actionable_fix(self) -> None:
        """條目齊全但標題中文數字 stale（R56 實際發生過「二十一檔」stale 3 檔）→ 紅，
        且訊息要直接給出「該改成什麼」，否則人得自己數＝又回到靠人記得。"""
        ledger = _build_ledger_dir("idx_header_stale", [1, 2, 3], header_cn="二")
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("宣稱「二檔」", problems[0])
        self.assertIn("三檔", problems[0])  # 可行動：直接給正確中文數字

    def test_unparseable_header_numeral_fails_loud(self) -> None:
        """標題數字寫法無法解析 → fail loud 要求擴充轉換，**不得**靜默視為通過。"""
        ledger = _build_ledger_dir("idx_header_bad", [1], header_cn="廿")
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("無法解析", problems[0])

    def test_numbering_gap_flagged(self) -> None:
        """編號缺號（archive_02 不見了）→ 紅：缺號代表檔案被誤刪或誤命名。"""
        ledger = _build_ledger_dir("idx_gap", [1, 3])
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("編號不連續", problems[0])
        self.assertIn("[2]", problems[0])

    def test_duplicate_entry_flagged(self) -> None:
        ledger = _build_ledger_dir(
            "idx_dupe", [1], entry_names=[_archive_name(1), _archive_name(1)],
            header_cn="二",
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertTrue(any("重複列出" in p for p in problems), problems)

    def test_missing_index_section_with_archives_on_disk_flagged(self) -> None:
        """整個索引節被刪掉、磁碟卻有 archive → 紅（否則「刪掉索引節」就能繞過整道鎖）。"""
        ledger = _build_ledger_dir("idx_nosection", [1, 2], index_section=False)
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("找不到〈已歸檔內容〉索引節標題", problems[0])

    def test_no_archives_and_no_index_section_is_clean(self) -> None:
        """零 archive 且無索引節＝一致（輪替尚未開始），不是缺陷——刻意不硬要求
        索引節存在，避免對「還沒開始輪替」的帳本假紅。"""
        ledger = _build_ledger_dir("idx_empty", [], index_section=False)
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            self.assertEqual(m._check_archive_index(), [])

    def test_prose_mention_not_counted_as_index_entry(self) -> None:
        """散文中順帶提及檔名（真實帳本〈已知歷史重疊〉段落就有）不得被誤計為索引條目，
        否則條目數會虛胖、標題數字守門變成假紅製造機。"""
        prose = (
            f"> **已知歷史重疊**：`{_archive_name(1)}` 與 `{_archive_name(2)}`"
            "各自搬移了同兩列。\n"
            f"- **`{_archive_name(3)}`**（非 blockquote 條目樣式）\n"
        )
        ledger = _build_ledger_dir("idx_prose", [1, 2], extra_text=prose)
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            self.assertEqual(m._check_archive_index(), [])

    def test_unrecognized_archive_filename_flagged(self) -> None:
        """檔名不符 `archive_<數字>.md` 但仍被 glob 撈到 → 紅（不靜默忽略）。"""
        ledger = _build_ledger_dir("idx_badname", [1])
        (ledger.parent / "AutoSDD_Defect_Log_archive_XX.md").write_text(
            "x", encoding="utf-8"
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            problems = m._check_archive_index()
        self.assertTrue(any("命名規則" in p for p in problems), problems)

    def test_real_repo_index_matches_disk(self) -> None:
        """真實 repo 現況：索引條目數 == 磁碟檔數，且兩者皆非 0。

        非 0 斷言是防「兩邊一起壞成空集合」的假綠——header/entry regex 若被改壞，
        entries 會歸零而磁碟 glob 不受影響，missing 清單即會爆紅；此處再明確釘一次
        「真的有掃到東西」。檔數刻意不寫死（本 repo 反覆因快照數字 stale 翻車）。
        """
        text = m._DEFECT_LOG.read_text(encoding="utf-8-sig")
        entries = [
            line for line in text.splitlines()
            if m._ARCHIVE_INDEX_ENTRY_RE.match(line)
        ]
        disk = sorted(m._DEFECT_LOG.parent.glob(m._ARCHIVE_GLOB))
        self.assertGreater(len(disk), 0, "真實 repo 應已有 archive 檔")
        self.assertEqual(
            len(entries), len(disk),
            f"索引條目 {len(entries)} != 磁碟 {len(disk)} 檔——請補登或清除 stale 條目",
        )
        self.assertIsNotNone(
            m._ARCHIVE_INDEX_HEADER_RE.search(text),
            "真實帳本的〈已歸檔內容〉標題樣式已改變，守門 regex 需同步",
        )
        self.assertEqual(m._check_archive_index(), [])


class TestCollectKnownDefIds(unittest.TestCase):
    """「合法 DEF 編號全集」的收集（SA-R58R1-03 D 類的比對基準）。

    這支若收得太窄，反向掃描會把大量真實編號誤判懸空（假紅洪水）；收得太寬
    （把散文提及也算已登錄），則抓不到「只寫在敘事段落、從未登錄成表格列」的漏登。
    兩個方向都各有回歸鎖。
    """

    def test_plain_table_row_collected(self) -> None:
        text = _ledger_text("| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed |\n")
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            self.assertIn("DEF-01-001", m._collect_known_def_ids())

    def test_blockquote_bold_compressed_row_collected(self) -> None:
        """回歸鎖：archive 的 blockquote 壓縮表格（`> | **ID** | … |`）必須算「已登錄」。

        實測 `AutoSDD_Defect_Log_archive_02.md` 全檔都是這個格式；A 類的 `_ROW_RE`
        （綁行首 `|`、不吃粗體）對它一列都比不到。若 D 類沿用 `_ROW_RE`，archive_02
        的全部條目會被判懸空 → 整道鎖變成假紅製造機（實測落地前後差距：618 → 623
        個已知編號）。
        """
        text = _ledger_text("") + (
            "> | **DEF-01-001** | P3 | **fixed@v0.21** | 敘述。 |\n"
            "> | DEF-01-002 | P2 | routed | 敘述。 |\n"
        )
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            known = m._collect_known_def_ids()
        self.assertIn("DEF-01-001", known)
        self.assertIn("DEF-01-002", known)

    def test_prose_mention_not_collected(self) -> None:
        """散文提及**不算**已登錄——否則「narrative-only 漏登」這個真實存在的形狀
        （實測 improving_94／95 兩輪合計 5 筆）就永遠抓不到。"""
        text = _ledger_text("") + "> 本輪修復 DEF-01-001 與 DEF-01-002，詳見敘述。\n"
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            self.assertEqual(m._collect_known_def_ids(), set())

    def test_archive_rows_included(self) -> None:
        """archive 檔的列同樣算已登錄（帳本輪替後條目都搬去 archive，只認主檔＝全紅）。"""
        ledger = _build_ledger_dir("known_archive", [1])
        (ledger.parent / _archive_name(1)).write_text(
            "| DEF-02-002 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed |\n",
            encoding="utf-8",
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger):
            known = m._collect_known_def_ids()
        self.assertIn("DEF-02-002", known)   # 來自 archive
        self.assertIn("DEF-01-001", known)   # 來自主檔（_build_ledger_dir 內建列）

    def test_table_separator_row_not_collected(self) -> None:
        """`|----|` 分隔列不含編號，不該造出垃圾條目（順帶確認 regex 沒過度寬鬆）。"""
        text = _ledger_text("| DEF-01-001 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | fixed |\n")
        with mock.patch.object(m, "_DEFECT_LOG", _write_tmp(text)):
            known = m._collect_known_def_ids()
        self.assertEqual(known, {"DEF-01-001"})

    def test_real_repo_known_is_superset_of_forward_row_parse(self) -> None:
        """真實 repo 不變量：D 類的已知編號集必須**涵蓋** A 類 `_load_ledger_status()`
        解出的每一個編號，且因為多吃了 archive 與 blockquote 格式而嚴格更大。

        這條同時擋兩種壞法：`_LEDGER_ROW_ANY_RE` 被改窄（會漏掉 A 類看得到的列 →
        subset 斷言炸）、以及兩邊一起壞成空集合（非空斷言炸）。檔數／筆數刻意不寫死
        （本 repo 反覆因快照數字 stale 翻車）。
        """
        known = m._collect_known_def_ids()
        forward = set(m._load_ledger_status())
        self.assertGreater(len(forward), 0, "A 類主檔解析為空 → 載具已失去鑑別力")
        self.assertTrue(
            forward <= known,
            f"A 類看得到但 D 類漏掉的編號：{sorted(forward - known)}",
        )
        self.assertGreater(
            len(known), len(forward),
            "D 類多吃 archive + blockquote 格式，理應嚴格大於只掃主檔的 A 類",
        )


class TestScanReverseRefs(unittest.TestCase):
    """反向懸空引用掃描本體（SA-R58R1-03）。全部用合成 fixture，不依賴真實帳本狀態。"""

    def test_dangling_ref_flagged_with_file_and_line(self) -> None:
        """bug-injection ①：fixture 內放一個帳本查無的編號 → 必紅，且訊息要指出
        哪個檔案哪一行引用了哪個編號（不可行動的訊息等於沒守）。"""
        root, rels = _write_scan_tree("rev_dangling", {
            "tools/some_test.py": f"# 第一行\n# 見 {_FAKE_ID} 的說明\n",
        })
        problems = m._scan_reverse_refs(root, rels, {"DEF-01-001"})
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(_FAKE_ID, problems[0])
        self.assertIn("tools/some_test.py:2", problems[0])

    def test_existing_ref_not_flagged(self) -> None:
        """bug-injection ②：fixture 內放一個帳本查得到的編號 → 必綠。"""
        root, rels = _write_scan_tree("rev_ok", {
            "docs/note.md": "見 DEF-01-001 的說明。\n",
        })
        self.assertEqual(m._scan_reverse_refs(root, rels, {"DEF-01-001"}), [])

    def test_whitelisted_id_not_flagged(self) -> None:
        """廢號白名單內的編號即使帳本查無也放行（豁免機制真的在生效）。"""
        retired = {_FAKE_ID: "合成測試理由"}
        root, rels = _write_scan_tree("rev_retired", {
            "docs/note.md": f"見 {_FAKE_ID}。\n",
        })
        with mock.patch.object(m, "_RETIRED_DEF_IDS", retired):
            self.assertEqual(m._scan_reverse_refs(root, rels, set()), [])

    def test_multiple_sites_aggregated_and_truncated(self) -> None:
        """同一懸空編號的多處引用聚合成一筆、位置清單截斷並標「另 N 處」——
        否則單一漏登編號（實測最多 38 處引用）會吐出一面牆，反而沒人讀。"""
        total = m._REVERSE_MAX_SITES_PER_ID + 3
        root, rels = _write_scan_tree("rev_many", {
            "docs/note.md": "".join(f"第 {i} 行提到 {_FAKE_ID}\n" for i in range(total)),
        })
        problems = m._scan_reverse_refs(root, rels, set())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(f"{total} 處", problems[0])
        self.assertIn("另 3 處", problems[0])

    def test_two_dangling_ids_reported_separately_and_sorted(self) -> None:
        root, rels = _write_scan_tree("rev_two", {
            "docs/a.md": f"{_FAKE_ID_2}\n",
            "docs/b.md": f"{_FAKE_ID}\n",
        })
        problems = m._scan_reverse_refs(root, rels, set())
        self.assertEqual(len(problems), 2, problems)
        self.assertIn(_FAKE_ID, problems[0])     # 排序輸出：777 在 778 之前
        self.assertIn(_FAKE_ID_2, problems[1])

    def test_binary_file_skipped(self) -> None:
        """含 NUL 位元組的二進位檔跳過（比照 `git grep -I`）——.png/.pyc 這類檔案裡
        湊巧出現的位元組序列不該當成引用。"""
        root, rels = _write_scan_tree("rev_binary", {
            "docs/blob.bin": b"\x00\x01" + _FAKE_ID.encode("ascii") + b"\x00",
        })
        self.assertEqual(m._scan_reverse_refs(root, rels, set()), [])

    def test_series_placeholder_notation_not_treated_as_id(self) -> None:
        """`DEF-101-3xx`／`DEF-94-NN` 這類「系列／佔位」寫法不可被截斷成幻影編號。

        實測本 repo 真的這樣寫（`AISDLC_SDD_v0.30/.../test_phase_i.py`），裸
        `DEF-\\d+-\\d+` 會抽出一個誰都查不到的殘骸編號 → 永久假紅。
        """
        root, rels = _write_scan_tree("rev_wildcard", {
            "docs/note.md": "同類缺陷 DEF-101-3xx 系列；另有 DEF-94-NN 佔位寫法。\n",
        })
        self.assertEqual(m._scan_reverse_refs(root, rels, set()), [])

    def test_sub_variant_suffix_still_resolves_to_parent_id(self) -> None:
        """`DEF-10-002a` 這類子編號變體仍須抽出母號 DEF-10-002 並比對——排除規則
        只擋 x/X/n/N，不可連英文字母一律擋掉（那會漏掉真實引用）。"""
        root, rels = _write_scan_tree("rev_subvariant", {
            "docs/note.md": "見 DEF-10-002a 的處置。\n",
        })
        problems = m._scan_reverse_refs(root, rels, set())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("DEF-10-002", problems[0])

    def test_missing_file_on_disk_skipped_without_crash(self) -> None:
        """git index 有、磁碟沒有（sparse checkout／剛刪未 commit）→ 略過不崩、不誤紅。"""
        root, _ = _write_scan_tree("rev_missing", {"docs/present.md": "無編號。\n"})
        problems = m._scan_reverse_refs(
            root, ["docs/present.md", "docs/vanished.md"], set()
        )
        self.assertEqual(problems, [])

    def test_non_utf8_bytes_do_not_crash_and_still_match(self) -> None:
        """非 UTF-8 位元組（如 cp950 殘留）以 replace 解碼，不可整檔崩掉而靜默漏掃。"""
        root, rels = _write_scan_tree("rev_latin", {
            "docs/legacy.md": b"\xb7\xfa\xbd X " + _FAKE_ID.encode("ascii") + b"\n",
        })
        problems = m._scan_reverse_refs(root, rels, set())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(_FAKE_ID, problems[0])


class TestRetiredWhitelist(unittest.TestCase):
    """廢號白名單自檢（SA-R58R1-03）：豁免機制自己也要有守門，否則它就是擋紅後門。"""

    def test_empty_reason_flagged(self) -> None:
        """bug-injection ③：白名單條目理由留空 → 必紅。"""
        with mock.patch.object(m, "_RETIRED_DEF_IDS", {_FAKE_ID: "   "}):
            problems = m._check_retired_whitelist(set())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("理由為空", problems[0])
        self.assertIn(_FAKE_ID, problems[0])

    def test_stale_entry_present_in_ledger_flagged(self) -> None:
        """bug-injection ④：白名單列了一個其實存在於帳本的編號 → 必紅（白名單過期）。"""
        with mock.patch.object(m, "_RETIRED_DEF_IDS", {_FAKE_ID: "有寫理由"}):
            problems = m._check_retired_whitelist({_FAKE_ID})
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("白名單已過期", problems[0])

    def test_malformed_key_flagged(self) -> None:
        """key 不是 `DEF-<數字>-<數字>` 形狀 → 紅：這種 key 永遠不會命中任何引用，
        看起來有豁免其實沒有（比沒寫更危險，因為它會讓人以為已處理）。"""
        with mock.patch.object(m, "_RETIRED_DEF_IDS", {"DEF-777": "有寫理由"}):
            problems = m._check_retired_whitelist(set())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("形狀", problems[0])

    def test_clean_entry_passes(self) -> None:
        with mock.patch.object(m, "_RETIRED_DEF_IDS", {_FAKE_ID: "有寫理由"}):
            self.assertEqual(m._check_retired_whitelist({"DEF-01-001"}), [])

    def test_real_whitelist_is_self_consistent(self) -> None:
        """真實 repo 鎖：現行 `_RETIRED_DEF_IDS` 每一筆都有理由、且都真的不在帳本裡。

        這條與帳本「本輪條目寫了沒」無關，故可穩定綠；它守的是「白名單不腐化」。
        """
        self.assertEqual(m._check_retired_whitelist(m._collect_known_def_ids()), [])


class TestReverseRefsEndToEnd(unittest.TestCase):
    """D 類總入口 `_check_reverse_refs()` 與 `main()` 的端到端紅綠（全合成 fixture）。"""

    def _synthetic(self, name: str, note: str) -> tuple[Path, Path]:
        """回傳 `(合成帳本主檔, 合成掃描根)`；掃描根內只有一個 `docs/note.md`。"""
        ledger = _build_ledger_dir(f"{name}_ledger", [])
        root, _ = _write_scan_tree(f"{name}_root", {"docs/note.md": note})
        return ledger, root

    def _run_check(self, ledger: Path, root: Path) -> list[str]:
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=(["docs/note.md"], None)):
            return m._check_reverse_refs()

    def test_end_to_end_red_on_dangling_ref(self) -> None:
        ledger, root = self._synthetic("e2e_red", f"見 {_FAKE_ID}。\n")
        problems = self._run_check(ledger, root)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(_FAKE_ID, problems[0])

    def test_end_to_end_green_on_registered_ref(self) -> None:
        # `_build_ledger_dir` 的主檔內建 DEF-01-001 一列
        ledger, root = self._synthetic("e2e_green", "見 DEF-01-001。\n")
        self.assertEqual(self._run_check(ledger, root), [])

    def test_fails_loud_when_ledger_row_parse_returns_empty(self) -> None:
        """帳本一列都解不出來時**不可**沿用「所有引用都懸空」的結論悶著跑——那會吐出
        幾百筆假紅、把真問題埋掉。要明說是解析壞了（本 repo 反覆踩過守門靜默失效）。"""
        empty = _write_tmp("# 帳本\n\n完全沒有表格列。\n")
        root, _ = _write_scan_tree("e2e_noparse_root", {"docs/note.md": f"{_FAKE_ID}\n"})
        with mock.patch.object(m, "_DEFECT_LOG", empty), \
             mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=(["docs/note.md"], None)):
            problems = m._check_reverse_refs()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("解析結果為空", problems[0])
        self.assertNotIn(_FAKE_ID, problems[0])  # 沒有夾帶一堆假紅

    def test_git_error_surfaces_instead_of_silently_passing(self) -> None:
        """`git ls-files` 失敗 → 紅並帶原始錯誤，**不可**當成「掃完沒問題」。"""
        ledger = _build_ledger_dir("e2e_giterr_ledger", [])
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=([], "git 掛了：boom")):
            problems = m._check_reverse_refs()
        self.assertEqual(problems, ["git 掛了：boom"])

    def test_main_returns_1_and_names_dangling_id(self) -> None:
        """main() 層端到端：懸空引用必須讓 exit code 非 0，訊息含編號（給人可直接補帳本）。"""
        ledger, root = self._synthetic("e2e_main", f"見 {_FAKE_ID}。\n")
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=(["docs/note.md"], None)), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("懸空引用", printed)
        self.assertIn(_FAKE_ID, printed)

    def test_main_reports_forward_and_reverse_problems_together(self) -> None:
        """A 類紅時不可 early return 吞掉 D 類——否則修完 A 再 push 又被 D 攔一次，
        來回兩趟。兩段訊息必須同時印出。"""
        ledger = _build_ledger_dir(
            "e2e_both_ledger", [],
            extra_text="\n| DEF-01-003 | 2026-06-12 | 情境 | 現象 | P2 | 去向 | wontfix |\n",
        )
        root, _ = _write_scan_tree("e2e_both_root", {"docs/note.md": f"{_FAKE_ID}\n"})
        target = _write_tmp("文件敘述 DEF-01-003（open，記事存證）。\n")
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch.object(m, "_CROSSREF_TARGETS", [target]), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=(["docs/note.md"], None)), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 1)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("跨文件狀態不一致", printed)
        self.assertIn("懸空引用", printed)

    def test_main_success_message_mentions_reverse_check(self) -> None:
        """全綠訊息要說出 D 類也查過了——否則「D 類被人整段註解掉」時輸出看不出差別。"""
        ledger, root = self._synthetic("e2e_msg", "見 DEF-01-001。\n")
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(m, "_REPO_ROOT", root), \
             mock.patch.object(m, "_CROSSREF_TARGETS", []), \
             mock.patch.object(
                 m, "_tracked_scan_paths", return_value=(["docs/note.md"], None)), \
             mock.patch("builtins.print") as fake_print:
            self.assertEqual(m.main(), 0)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("皆可在帳本查得表格列", printed)


class TestTrackedScanPaths(unittest.TestCase):
    """掃描面取得（`git ls-files` + 凍結版剔除）——對真實 repo 驗，因為它的價值全在
    「真的有掃到東西、且真的排除了該排除的」。"""

    def test_real_repo_returns_posix_relative_paths(self) -> None:
        rels, error = m._tracked_scan_paths()
        self.assertIsNone(error, error)
        self.assertGreater(len(rels), 0)
        self.assertFalse(
            [r for r in rels if "\\" in r],
            "路徑含反斜線 → 訊息裡的檔案位置在 Windows/其他平台會不一致",
        )
        # 抽驗本檔自己在掃描面內（本測試檔的存在性是最穩的自證）
        self.assertIn("tools/tests/test_check_defect_log_crossref.py", rels)

    def test_real_repo_excludes_frozen_sdd_versions_and_exclusion_is_load_bearing(
        self,
    ) -> None:
        """剔除規則必須①真的把凍結版目錄排掉 ②真的排掉了東西，③且只排掉那些。

        🔴 判定一律用**獨立**取得的 tracked 清單與**字面前綴**，刻意不呼叫
        `m._REVERSE_SCAN_EXCLUDE_RE`：本鎖初版就是用該 regex 判「有沒有漏進來」，
        結果 bug-injection 實測（把 regex 改成 `^__never_matches__/`）**仍然全綠**
        ——因為過濾與驗收用的是同一個被改壞的 regex，成了自我循環的同義反覆。
        改成字面前綴後同一注入即翻紅。這是本檔「測試要能被 bug-injection 打紅」
        的活教材，勿改回去。
        """
        raw = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(m._REPO_ROOT), capture_output=True, check=True,
        ).stdout.decode("utf-8")
        all_tracked = [r for r in raw.split("\0") if r]
        frozen = [r for r in all_tracked if r.startswith(_FROZEN_PREFIX)]
        self.assertGreater(
            len(frozen), 0,
            f"tracked 清單裡找不到任何 {_FROZEN_PREFIX}* 檔案 → 沒有東西該被排除，"
            "本鎖失去鑑別力，請改寫",
        )
        rels, error = m._tracked_scan_paths()
        self.assertIsNone(error, error)
        leaked = sorted(set(rels) & set(frozen))
        self.assertEqual(leaked[:5], [], f"凍結版路徑漏進掃描面（共 {len(leaked)} 筆）")
        self.assertEqual(
            len(rels), len(all_tracked) - len(frozen),
            "掃描面筆數 ≠ tracked 總數 − 凍結版筆數 → 剔除規則多排或少排了東西"
            "（數字刻意不寫死，兩邊都現算）",
        )


class TestRetainedRangeClaims(unittest.TestCase):
    """`retained_range_problems()` 的鑑別力自驗（R58 round 10 擴充至 8 支）。

    **這支測試自己的歷史是本輪最貴的一課，四輪都在同一個地方犯同一種錯**：
      * round 7：判準「宣稱終點 == 主檔全域最大列」，對真實語料恰好全綠 ⇒ 看不出問題；
        round 8 四方各自注入「下一輪首列」全部假紅。述詞另漏 `\\s*` 只抓 2/3 站點。
      * round 8：改輪次界（輪次取標題欄第一個 `R<數字>`）＋ 7 支自驗。round 9 四方全數 REJECT、
        五項同一根因——那 7 支**全用本家慣例不會出現的標題**（家規是開輪列標題先提上一輪）⇒
        恆綠；QA 另實測「刪掉不變式 (2) 整段分支，7 支自驗全數仍綠」。
      * round 9：拆掉終點、縮為 4 支。round 10 四方又全數 REJECT——①述詞不認**粗體**，
        而落地當下自己寫的站點正是 `（**DEF-101-507 起**）` ⇒ 4 個站點只認 3 個，docstring 卻寫
        「現存站點皆命中」；②`ledger_text` 是**死參數**，docstring 宣稱的正向半邊（「必須還在
        主檔」）根本沒實作 ⇒ **範圍內某列被整列刪除完全靜默**；③`test_quoted_historical_wording_
        is_not_matched` 的 fixture **沒有 archive 鍵**，`archived` 恆空 ⇒ 該支**零鑑別力**、
        判準被打壞也永遠綠。
      * round 10：述詞收粗體、`ledger_text` 活化（補正向半邊）、每支 fixture 都給 archive 鍵、
        並加**平價鎖**——讓「述詞漏一種拼法」這個連三輪復發的形態自己翻紅，不再靠人數一次
        3 還是 4。

    **設計紀律（從上面四輪蒸餾出來的）**：
      1. fixture 必須採**本家慣例**的寫法（含粗體、含「先提上一輪」的標題），不是理想化寫法。
      2. 每支 fixture 都要讓被測分支**有機會開火**（缺 archive 鍵＝該支永遠綠）。
      3. 涵蓋面宣稱不得靠人工計數——用平價鎖把它變成機械斷言。
    """

    _HDR = "| ID | 日 | 標題 | 詳 | P | 負 | 狀 |\n|---|---|---|---|---|---|---|\n"
    _CLAIM = "> R58 自身全部條目（DEF-101-507 起）完整留在主檔供 R59 對帳\n"
    # 本家慣例：關鍵數字加粗。round 9 落地時自己就是這樣寫的，而述詞當時不認。
    _CLAIM_BOLD = "> R58 自身全部條目（**DEF-101-507 起**）完整留在主檔供 R59 對帳\n"

    @staticmethod
    def _row(num: int) -> str:
        """標題刻意寫成本家慣例的「先提上一輪」形態（round 8 那 7 支的致命處）。"""
        return (
            f"| DEF-101-{num} | 2026-07-28 | R57 backlog 的 R58 落地 "
            f"| 詳 | P3 | 主控 | fixed |\n"
        )

    def test_all_rows_retained_is_green(self) -> None:
        led = self._HDR + self._row(507) + self._row(508) + self._row(509)
        self.assertEqual(
            m.retained_range_problems(led, {"main": led + self._CLAIM, "archive_29.md": ""}), []
        )

    def test_a_row_moved_into_archive_is_red(self) -> None:
        """反向半邊：範圍內某列被搬進 archive，而宣稱沒跟著改。"""
        led = self._HDR + self._row(507) + self._row(509)
        arch = self._HDR + self._row(508)
        problems = m.retained_range_problems(
            led, {"main": led + self._CLAIM, "archive_29.md": arch}
        )
        self.assertTrue(any("搬進 archive" in p and "DEF-101-508" in p for p in problems), problems)

    def test_a_row_deleted_outright_is_red(self) -> None:
        """正向半邊（round 10 ARCHITECT-R58R10-01）：整列被刪、不在主檔也不在任何 archive。

        round 9 初版把 `ledger_text` 收在簽章裡卻一次都沒讀 ⇒ 此情境完全靜默，而那正是
        拆掉終點判準後**真的失去**的東西。
        """
        led = self._HDR + self._row(507) + self._row(509)  # 508 憑空消失
        problems = m.retained_range_problems(
            led, {"main": led + self._CLAIM, "archive_29.md": ""}
        )
        self.assertTrue(
            any("不在主檔、也不在任何 " in p and "508" in p for p in problems), problems
        )

    def test_bold_claim_form_is_matched(self) -> None:
        """述詞必須認**粗體**寫法（round 10 三方各自抓到；本家慣例就是加粗）。"""
        led = self._HDR + self._row(507) + self._row(509)
        arch = self._HDR + self._row(508)
        problems = m.retained_range_problems(
            led, {"main": led + self._CLAIM_BOLD, "archive_29.md": arch}
        )
        self.assertTrue(problems, "粗體宣稱未被述詞認出 ⇒ 該站點靜默脫離守門面")

    def test_the_start_row_itself_counts(self) -> None:
        """邊界（round 10 QA R59-01）：把**起點那一列本身**搬進 archive 也必須紅。

        原本 4 支自驗沒有任何 fixture 歸檔起點列 ⇒ 把 `n >= start` 改成 `n > start` 的突變
        會存活。
        """
        led = self._HDR + self._row(508)
        arch = self._HDR + self._row(507)
        problems = m.retained_range_problems(
            led, {"main": led + self._CLAIM, "archive_29.md": arch}
        )
        self.assertTrue(any("DEF-101-507" in p for p in problems), problems)

    def test_rows_below_the_start_may_be_archived(self) -> None:
        """起點以下的舊輪條目本來就該可以歸檔——不得誤報（否則每次歸檔都翻紅）。"""
        led = self._HDR + self._row(507)
        arch = self._HDR + self._row(478) + self._row(506)
        self.assertEqual(
            m.retained_range_problems(led, {"main": led + self._CLAIM, "archive_29.md": arch}), []
        )

    def test_quoted_historical_wording_is_not_matched(self) -> None:
        """帳本刻意保留的訂正痕跡（引述舊錯誤原文用較窄的「自身條目」）不得被誤報。

        🔴 **本支的鑑別力有兩個必要條件，round 10 分兩次才補齊**（SD-R58R10-01）：
          1. fixture 必須帶一個「範圍內已歸檔」的 archive 鍵——否則 `archived` 恆空 ⇒
             不論述詞被放寬到什麼程度都回傳空清單。SD 抓到的是這一半。
          2. fixture 的引述內容必須**碰得到每一個判別點**。主控補了 archive 鍵後實測**仍綠**：
             帳本真實的引述（`自身條目 507~530`）**同時缺 `全部` 與 `起` 兩個特徵**，故單獨
             弱化任一個都不會命中 ⇒ 本支對「述詞放寬」仍近乎無牙。故補上兩種**只缺其中一個
             特徵**的引述形態，讓兩個判別點各自可被殺。
             （這一步是主控自己在做注入時發現的——第一次修完仍綠，才看出「補了鍵不等於有牙」。）
        """
        led = self._HDR + self._row(507) + self._row(509)
        arch = self._HDR + self._row(508)  # 若述詞誤認任一種引述，這一列就會讓它翻紅
        quotes = (
            # (a) 帳本真實形態：兩個判別特徵都缺
            "> 引述舊錯誤原文：「R58 自身條目 507~530」應為 507~531\n"
            # (b) 只缺「全部」——殺得掉「把錨放寬成 `自身(?:全部)?條目`」這個突變
            "> 引述舊錯誤原文：「R58 自身條目（DEF-101-507 起）」措辭已廢\n"
            # (c) 只缺「起」——殺得掉「移除 `起` 要求」這個突變（round 8 帳本真的寫過此形態）
            "> 形狀說明：「自身全部條目 507~530」為 round 8 的舊措辭\n"
        )
        self.assertEqual(
            m.retained_range_problems(led, {"main": led + quotes, "archive_29.md": arch}), []
        )

    def test_sources_without_a_main_file_fails_loud(self) -> None:
        """只給 archive 來源 → 正向半邊無母體，必須 fail-loud 而非靜默零回報（SD-R58R10 #2）。"""
        with self.assertRaises(ValueError):
            m.retained_range_problems("", {"archive_29.md": self._HDR + self._row(507)})

    def test_predicate_covers_every_real_claim_site(self) -> None:
        """**平價鎖**：真實帳本內每一個活宣稱都必須被述詞認出（round 10 立）。

        立案理由：「述詞漏一種拼法就漏一個站點」已在本鎖上**連三輪**復發
        （round 7 漏 `\\s*` 抓 2/3、round 8 輪次歸屬雙向壞、round 10 漏粗體抓 3/4），
        而每次都是靠複審者手動數站點才發現、docstring 則一直寫著「現存站點皆命中」。
        本鎖把那個計數變成機械斷言：**凡「自身全部條目」後 40 字內出現「起」者即為活宣稱**
        （形狀說明用 `NNN~MMM`、引述歷史原文用較窄的「自身條目」，兩者都不含「起」），
        全部必須被 `_RETAINED_START_RE` 認出。
        """
        ledger_dir = Path(m.__file__).resolve().parents[1] / "docs" / "06_quality"
        targets = [ledger_dir / "AutoSDD_Defect_Log.md"]
        targets += sorted(ledger_dir.glob("AutoSDD_Defect_Log_archive_*.md"))
        misses: list[str] = []
        total = 0
        for path in targets:
            if not path.is_file():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for mm in re.finditer("自身全部條目", line):
                    seg = line[mm.start():mm.start() + 40]
                    if "起" not in seg:
                        continue  # 形狀說明／引述痕跡，非活宣稱
                    total += 1
                    if not m._RETAINED_START_RE.search(line[mm.start():]):
                        misses.append(f"{path.name}:{lineno} {seg[:36]!r}")
        self.assertGreater(total, 0, "帳本內找不到任何活宣稱——平價鎖失去語料，請確認措辭是否已變")
        self.assertEqual(
            misses, [],
            "下列活宣稱未被 `_RETAINED_START_RE` 認出 ⇒ 該站點已靜默脫離守門面："
            + "、".join(misses),
        )


if __name__ == "__main__":
    unittest.main()
