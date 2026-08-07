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
from unittest import mock

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

    def test_small_numbers_with_keyword_not_flagged(self) -> None:
        """案 7（判準下界）：passed/skipped 同行但數字 <4 位且無千分位 → 不命中。

        smoke 腳本 PASS=10 這類小計數宣稱不屬 pytest 基線形狀，不應誤殺。
        """
        ssot = _write_tmp(_SSOT_OK)
        small = _write_tmp("smoke 全綠：10 passed / 0 skipped（PASS=10 釘選）\n")
        self.assertEqual(m.scan([ssot, small], ssot), [])

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


class TestPairShorthandForm(unittest.TestCase):
    """案 12~14（R78 QA-02）：計數簡寫 `NNNN/NNN` 形態。

    WHY：`tools/lib/baseline_origin.py` 的註解把三支直譯器的計數簡寫成斜線對、不寫
    `passed`／`skipped` 字樣，於是原判準（關鍵字＋數字）整類漏接——那一筆在磁碟上錯了
    兩輪零訊號，且**把該檔加進 `_SCAN_FILES` 也修不好**（形態不匹配才是根因）。三案分別
    釘住：真缺陷形態要紅／脈絡閘外的編號對不得誤殺／日期形狀不得誤殺。
    """

    def test_pair_shorthand_in_tool_comment_is_flagged(self) -> None:
        """案 12：真缺陷的原始形狀（工具註解裡的三組斜線對）→ 必須紅。"""
        ssot = _write_tmp(_SSOT_OK)
        bad = _write_tmp(
            "# `.venv` 4017/160、pyenv-win 4032/145、出廠 cleanvenv 3919/224。\n",
            name="pair_site.py",
        )
        problems = m.scan([ssot, bad], ssot)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("pair_site.py:1", problems[0])

    def test_numbered_pairs_without_context_word_are_not_flagged(self) -> None:
        """案 13（誤殺下界）：`improving_100/101`／`Gap-042/048` 無環境脈絡字 → 不命中。

        脈絡閘不是為了讓現況通過：落地前對真實掃描面實測，拿掉它會誤殺 4 筆編號對，
        而被迫在無關的行貼豁免標記會讓標記本身貶值。
        """
        ssot = _write_tmp(_SSOT_OK)
        clean = _write_tmp(
            "後續 improving_100/101 等輪持續累積（現行基線見 ONBOARDING.md §7）\n"
            "跨 Session 計數器持久化（Gap-042/048）：4 個 counter 寫入 checkpoint\n"
        )
        self.assertEqual(m.scan([ssot, clean], ssot), [])

    def test_dates_are_not_mistaken_for_count_pairs(self) -> None:
        """案 14（誤殺下界）：日期 `2026/08/07` 即使同行有 pytest 字樣也不得命中。"""
        ssot = _write_tmp(_SSOT_OK)
        clean = _write_tmp("2026/08/07 於 .venv 重跑 pytest 全套，結果見 SSOT。\n")
        self.assertEqual(m.scan([ssot, clean], ssot), [])


class TestRealRepoConfigPinning(unittest.TestCase):
    """案 11：守門自身組態釘選（ARCH-R13-REV-1/QA-R13-2）。

    WHY：9 個 fixture 案全走注入，若無本案，`_SCAN_FILES` 刪一行（如移除
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
                # R59（DEF-101-514）：使用者最先讀的入門文件，其 §1.4 標「強制」驗證
                # 步驟卻自 R13 收斂以來一直在掃描面外——實測其寫死的舊數字已落後
                # 數百支且從未翻紅。本鎖同步擴充（否則加了掃描面卻沒有 roster 鎖，
                # 等於把新加的那一項留在「刪掉也沒訊號」的狀態）。
                "docs/AISDLC_Agent_UserGuide.md",
                # R78（QA-02）：掃描面此前清一色 `.md`，而量測值最會被就地寫下的地方是
                # 讀寫基線的那一層工具原始碼。兩支一起收（只收被抓到的那一支＝個案修法）。
                "tools/lib/baseline_origin.py",
                "tools/sync_onboarding_baselines.py",
            },
        )
        self.assertEqual(m._SSOT_FILE, "ONBOARDING.md")
        self.assertIn(m._SSOT_FILE, m._SCAN_FILES)


class TestForwardLookingDiscovery(unittest.TestCase):
    """R79 ARCH：前瞻發現鎖——「在一份**新**文件裡寫下第九個基線數字」必須會紅。

    病灶：`_SCAN_FILES` 是人工白名單，擋得住「刪清單一行」（上一個 class 在守），
    擋不住「多開一個家」。R79 實測掃描面外還有 1,430 支 tracked `.md`/`.py`、
    4,495 行命中同一判準，其中命中最多的兩支是**活文件**而非史料。同一個病本 repo
    早有正確樣板（`check_script_parity` 的 enrollment 發現鎖掃全庫 `.sh`/`.ps1`），
    只有這一道沒用發現式掃描面。

    測意圖非僅行為：本組不驗「今天是幾支」，而是驗**三件事會不會說話**——
    ①新開的家會讓計數上升而紅；②合法收斂後棘輪值過時也會紅（否則餘裕就是破口）；
    ③把活文件整批豁免掉（讓計數變小的最省事手段）也會紅。
    """

    _REPO = Path(__file__).resolve().parents[2]

    def test_the_discovery_surface_is_not_vacuous(self) -> None:
        """自錨：發現面收不到東西時，棘輪會恆綠——先確認它真的看得到活文件。"""
        scanned = [
            rel for rel in m._tracked_docs_and_py(self._REPO)
            if not m.is_dated_artifact(rel)
        ]
        self.assertGreaterEqual(len(scanned), 900, "發現面異常縮小 ⇒ 豁免表疑似被擴大")
        for anchor in m._LIVE_DOC_ANCHORS:
            self.assertIn(anchor, scanned, f"活文件錨 {anchor} 不在發現面內")

    def test_real_tree_is_at_the_ratchet(self) -> None:
        """真樹現況必須恰等於棘輪值（零餘裕；上下任一方向皆紅）。"""
        self.assertEqual(m.unmanaged_site_problems(self._REPO), [])
        self.assertEqual(
            len(m.discover_unmanaged_sites(self._REPO)),
            m._UNMANAGED_HIT_FILES_RATCHET,
            "未納管站點實測數與棘輪值不符——本鎖刻意零餘裕，兩個方向都要求同步",
        )

    def test_a_new_unmanaged_site_is_red(self) -> None:
        """鑑別力①（注入）：把棘輪下修一格＝等價於「多出一個新的家」，必須紅。"""
        with mock.patch.object(
            m, "_UNMANAGED_HIT_FILES_RATCHET", m._UNMANAGED_HIT_FILES_RATCHET - 1
        ):
            problems = m.unmanaged_site_problems(self._REPO)
        self.assertTrue(problems, "新增未納管站點被放行 ⇒ 前瞻發現鎖無鑑別力")
        self.assertIn("棘輪只准下修", " ".join(problems))

    def test_a_stale_ratchet_after_shrinking_is_red(self) -> None:
        """鑑別力②（注入）：合法收斂後沒有下修棘輪，餘裕即破口 ⇒ 也要紅。"""
        with mock.patch.object(
            m, "_UNMANAGED_HIT_FILES_RATCHET", m._UNMANAGED_HIT_FILES_RATCHET + 1
        ):
            problems = m.unmanaged_site_problems(self._REPO)
        self.assertTrue(problems, "棘輪值過時被放行 ⇒ 餘裕會被無聲用掉")
        self.assertIn("已過時", " ".join(problems))

    def test_swallowing_live_docs_with_a_coarse_prefix_is_red(self) -> None:
        """鑑別力③（注入）：加一條 `AutoClaude/` 粗前綴一次豁免掉 99 支活文件——
        這是讓棘輪變綠最省事的手段，檔數下限對它感覺不到，故另設活文件錨。"""
        coarse = m._DATED_ARTIFACT_PREFIXES + (("AutoClaude/", "刻意的粗前綴（注入）"),)
        with mock.patch.object(m, "_DATED_ARTIFACT_PREFIXES", coarse):
            problems = m.unmanaged_site_problems(self._REPO)
        self.assertTrue(problems, "粗前綴豁免掉活文件被放行 ⇒ 自錨②無鑑別力")
        self.assertIn("被 `_DATED_ARTIFACT_PREFIXES` 豁免掉了", " ".join(problems))

    def test_dated_artifact_prefixes_each_carry_a_why(self) -> None:
        """豁免表的每一筆都要有非空 WHY——無 WHY 的豁免等於沒有判準。"""
        for prefix, why in m._DATED_ARTIFACT_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertIn("/", prefix, f"{prefix!r} 不像路徑前綴（無分隔符）")
                self.assertGreaterEqual(len(why.strip()), 8, f"{prefix!r} 的 WHY 過短")


if __name__ == "__main__":
    unittest.main()
