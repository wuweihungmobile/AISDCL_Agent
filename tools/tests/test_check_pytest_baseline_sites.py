#!/usr/bin/env python3
"""tools/check_pytest_baseline_sites.py 的單元測試（R13 ARCH-R13-1：pytest 基線
數字多站點漂移機械鎖——DEF-101-045／ARCH-R12-7／R13 README 漂移三度實證後落地；
鏡子自身也要有測試，不可只憑人工複審碰運氣）。

全部案例以 tmp fixture 注入（scan/audit_exemptions 收明確路徑），**不依賴真實
repo 文件現況**——工具落地當下真實文件尚未收斂（預期紅），fixture 自證即可。

執行：python3 -m unittest tools.tests.test_check_pytest_baseline_sites -v
（亦由 tools/run_root_unittests.py discover 納入）
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_pytest_baseline_sites as m  # noqa: E402

# 系統暫存目錄放測試用 fixture 檔（非 repo 內），process 結束自動清除，避免污染 tools/tests/。
_TMP_DIR = Path(tempfile.mkdtemp(prefix="baseline_sites_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _write_tmp(text: str, name: str | None = None) -> Path:
    _tmp_counter[0] += 1
    p = _TMP_DIR / (name or f"fixture_{_tmp_counter[0]}.md")
    p.write_text(text, encoding="utf-8")
    return p


# 合法 SSOT fixture：帶一行基線數字宣稱（anchor 命中 ≥1）。
_SSOT_OK = (
    "## 7. 常用驗證指令\n\n"
    "> 註：出廠環境 full pytest 實測基線約 **3,566 passed / 196 skipped**（總數 3,762）。\n"
)


class TestScan(unittest.TestCase):
    def test_all_green_fixture(self) -> None:
        """案 1：SSOT 有 anchor、非 SSOT 檔乾淨（只指向 SSOT、不載數字）→ 零違規。"""
        ssot = _write_tmp(_SSOT_OK)
        clean = _write_tmp("基線數字唯一出處＝根層 ONBOARDING.md §7，本檔不重複數字。\n")
        self.assertEqual(m.scan([ssot, clean], ssot), [])

    def test_non_ssot_hit_flagged_with_file_and_line(self) -> None:
        """案 2：非 SSOT 檔出現千分位基線宣稱 → 紅，訊息含 檔:行。"""
        ssot = _write_tmp(_SSOT_OK)
        bad = _write_tmp(
            "# 某文件\n\n全套（基線 3,566 passed / 196 skipped，2026-07-13 實測）\n",
            name="bad_site.md",
        )
        problems = m.scan([ssot, bad], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("bad_site.md:3", problems[0])
        self.assertIn("非 SSOT", problems[0])

    def test_ssot_zero_hits_flagged(self) -> None:
        """案 3：SSOT 全檔零命中 → anchor 自檢紅（防 SSOT 被刪成零訊號後守門空轉假綠）。"""
        ssot = _write_tmp("## 7. 常用驗證指令\n\n（基線數字段落被整段刪除）\n")
        clean = _write_tmp("其他文件乾淨。\n")
        problems = m.scan([ssot, clean], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("anchor", problems[0])

    def test_baseline_ok_exemption_passes_and_is_audited(self) -> None:
        """案 4：非 SSOT 命中行帶 `baseline-ok:` 標記 → 不違規，且稽核清單列出 檔:行＋WHY。"""
        ssot = _write_tmp(_SSOT_OK)
        exempt = _write_tmp(
            "| SD_07 | G6 末基線 **2,012 passed / 121 skipped** "
            "<!-- baseline-ok: SD_07 歷史結案紀錄，非現行基線 --> |\n",
            name="exempt_site.md",
        )
        self.assertEqual(m.scan([ssot, exempt], ssot), [])
        audits = m.audit_exemptions([ssot, exempt])
        self.assertEqual(len(audits), 1, audits)
        self.assertIn("exempt_site.md:1", audits[0])
        self.assertIn("SD_07 歷史結案紀錄", audits[0])

    def test_badge_url_encoded_form_flagged(self) -> None:
        """案 5：README badge 的 URL-encoded 形態（tests-3567%20passed）→ 必須命中紅。

        R13 README 漂移實證的原始形狀：badge 內數字與 SSOT 並立且無空格分隔，
        判準（passed 子字串＋≥4 位整數）須對此天然有效。
        """
        ssot = _write_tmp(_SSOT_OK)
        badge = _write_tmp(
            "[![Tests](https://img.shields.io/badge/"
            "tests-3567%20passed%20%2F%20195%20skipped-brightgreen)]()\n",
            name="readme_badge.md",
        )
        problems = m.scan([ssot, badge], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("readme_badge.md:1", problems[0])

    def test_missing_scan_file_fails_loud(self) -> None:
        """案 6：掃描檔缺席（改名/搬移未同步 _SCAN_FILES）→ fail-loud 紅，不得靜默縮面。"""
        ssot = _write_tmp(_SSOT_OK)
        missing = _TMP_DIR / "does_not_exist.md"
        problems = m.scan([ssot, missing], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("找不到掃描目標", problems[0])
        self.assertIn("does_not_exist.md", problems[0])

    def test_two_digit_counts_now_flagged_after_r58_widening(self) -> None:
        """案 7（判準下界，**R58 反轉**）：≥2 位數字＋基線關鍵詞 → 命中。

        WHY 反轉：本案原本斷言「10 passed / 0 skipped 這類小計數不命中」（理由是
        smoke PASS=10 不屬 pytest 基線形狀）。R58 揪出該下界（≥4 位）讓本 repo
        **兩組真實三位數基線**整組逃逸（根層 646、SDD scripts/tests 245），下限
        放寬到 ≥2 位後，本行形態改為命中——這是刻意承受的誤殺面，與本工具
        docstring 自訂的偏誤方向（「寧可誤殺由豁免放行，不可漏放」）一致：smoke
        小計數若真要寫進掃描面，就該用 `baseline-ok:` 標明「非 pytest 基線」，
        比留一道三位數逃逸口安全。
        """
        ssot = _write_tmp(_SSOT_OK)
        small = _write_tmp(
            "smoke 全綠：10 passed / 0 skipped 釘選\n", name="two_digit.md"
        )
        problems = m.scan([ssot, small], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("two_digit.md:1", problems[0])

    def test_single_digit_counts_still_not_flagged(self) -> None:
        """案 7b（放寬後的新下界）：一位數字＋關鍵詞 → 仍不命中。

        WHY：放寬不是取消下界。`1 passed / 0 skipped` 這類單支測試宣稱不具
        「多站點基線漂移」風險形狀，若連它都命中，掃描面上任何提到單一測試
        通過的敘述都要掛豁免，豁免會膨脹成背景噪音（本工具 docstring 明列
        「防豁免標記濫用」為設計目標）。本案把新下界釘成可執行斷言，防未來
        有人把 `\\d{2,}` 再手滑改成 `\\d+`。
        """
        ssot = _write_tmp(_SSOT_OK)
        tiny = _write_tmp("該修復的回歸鎖：1 passed / 0 skipped。\n")
        self.assertEqual(m.scan([ssot, tiny], ssot), [])

    def test_three_digit_baseline_in_non_ssot_flagged(self) -> None:
        """案 7c（**R58 核心回歸鎖**）：三位數基線在非 SSOT 檔出現必紅。

        WHY：這是 R58 發現 #16 的原始形狀——`_NUMBER_RE` 只認 ≥4 位時，本 repo
        兩組真實三位數基線寫進任何非 SSOT 檔都綠燈放行，「數字只准住一個家」
        對它們完全失效。兩組形態都鎖：
          ① 根層 runner：`646 tests OK/skipped=11`（`tests OK` 為 R58 新增關鍵詞）；
          ② AISDLC_SDD scripts/tests：`245 passed / 1 skipped / 23 subtests passed`。
        本案刻意用「真實會被寫下的整句」而非合成片段，才能同時驗到關鍵詞擴充
        與數字下限放寬兩處改動。
        """
        ssot = _write_tmp(_SSOT_OK)
        root_shape = _write_tmp(
            "> 註：根層 `tools/run_root_unittests.py` **646 tests OK/skipped=11**"
            "（量測平台：原生 Windows 11）\n",
            name="root_three_digit.md",
        )
        sdd_shape = _write_tmp(
            "逐軌：scripts/tests **245 passed / 1 skipped / 23 subtests passed**\n",
            name="sdd_three_digit.md",
        )
        for bad, tag in ((root_shape, "root_three_digit.md:1"),
                         (sdd_shape, "sdd_three_digit.md:1")):
            problems = m.scan([ssot, bad], ssot)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(tag, problems[0])
            self.assertIn("非 SSOT", problems[0])

    def test_root_runner_wording_without_passed_or_skipped_flagged(self) -> None:
        """案 7d（**R58 關鍵詞擴充鑑別力**）：不含 passed/skipped 的根層用語也要命中。

        WHY：案 7c 的根層形態帶了 `skipped=11`，光靠舊關鍵詞就會命中，**驗不到**
        關鍵詞擴充。本案刻意剝掉 passed/skipped，只留根層 runner 與 unittest 的
        原生用語——這三種寫法在 R58 前是完整逃逸的（守門對它們零訊號）：
          ① `646 tests OK`（文件慣用縮寫）
          ② `發現 646 個測試`（`run_root_unittests.py` 實際 print 的字樣）
          ③ `Ran 646 tests`（unittest 自身輸出）
        若有人把 `_KEYWORD_RE` 縮回 `passed|skipped`，本案三筆會同時轉綠。
        """
        ssot = _write_tmp(_SSOT_OK)
        for text, name in (
            ("根層現況：646 tests OK。\n", "kw_tests_ok.md"),
            ("守門輸出：發現 646 個測試（下限 616）。\n", "kw_found_cn.md"),
            ("unittest 尾行：Ran 646 tests in 91.2s。\n", "kw_ran_tests.md"),
        ):
            bad = _write_tmp(text, name=name)
            problems = m.scan([ssot, bad], ssot)
            self.assertEqual(len(problems), 1, f"{name}: {problems}")
            self.assertIn(f"{name}:1", problems[0])

    def test_plain_four_digit_integer_flagged(self) -> None:
        """案 8（判準上界）：無千分位的 ≥4 位整數（3567 passed）同樣命中。"""
        ssot = _write_tmp(_SSOT_OK)
        plain = _write_tmp("tests/ 目錄現況：3567 passed。\n", name="plain_int.md")
        problems = m.scan([ssot, plain], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plain_int.md:1", problems[0])

    def test_ssot_missing_from_disk_fails_loud(self) -> None:
        """案 9：SSOT 檔本身缺席 → 紅（anchor 自檢無從執行，不得放行）。"""
        missing_ssot = _TMP_DIR / "missing_ssot.md"
        clean = _write_tmp("乾淨文件。\n")
        problems = m.scan([missing_ssot, clean], missing_ssot)
        # 缺席一筆（掃描目標）＋ SSOT 缺席 fail-loud 一筆
        self.assertEqual(len(problems), 2, problems)
        self.assertTrue(any("找不到 SSOT 檔" in p for p in problems), problems)

    def test_empty_why_exemption_has_no_exempting_power(self) -> None:
        """案 10：空 WHY 的 baseline-ok: 標記不具豁免力 → 照列違規（QA-R13-1/SD-R13-2）。

        WHY：與同輪 encoding-ok（空 WHY 無豁免力）及 parity「豁免必附 WHY」紀律
        一致；否則「防豁免濫用」宣稱在零 WHY 情境失效。
        """
        ssot = _write_tmp(_SSOT_OK)
        bad = _write_tmp("目前全套 9,999 passed / 0 skipped <!-- baseline-ok: -->\n")
        problems = m.scan([ssot, bad], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("未填 WHY", problems[0])
        # 對照組：同行補上 WHY 即放行
        ok = _write_tmp("歷史紀錄 9,999 passed / 0 skipped <!-- baseline-ok: 歷史快照 -->\n")
        self.assertEqual(m.scan([ssot, ok], ssot), [])


class TestRealRepoConfigPinning(unittest.TestCase):
    """案 11：守門自身組態釘選（ARCH-R13-REV-1/QA-R13-2）。

    WHY：上方 fixture 案**全數**走注入（刻意不寫死案數——本檔案數每輪都會增減），
    若無本案，`_SCAN_FILES` 刪一行（如移除
    AutoClaude/README.md——恰是催生本守門的漂移檔）即靜默縮面、零機械訊號。
    QA 一審以活體攻擊實證此繞法後補上本釘選；同手法先例＝parity 的
    test_tools_lib_in_scan_dirs。清單有意變更時，須連同本案與 docstring 一併改。
    """

    def test_scan_files_and_ssot_pinned(self) -> None:
        self.assertEqual(
            set(m._SCAN_FILES),
            {
                "CLAUDE.md",
                "ONBOARDING.md",
                "useMacWin.md",
                "AutoClaude/CLAUDE.md",
                "AutoClaude/README.md",
            },
        )
        self.assertEqual(m._SSOT_FILE, "ONBOARDING.md")
        self.assertIn(m._SSOT_FILE, m._SCAN_FILES)


if __name__ == "__main__":
    unittest.main()
