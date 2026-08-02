#!/usr/bin/env python3
"""腳本掃描面 SSOT 形狀一致性鎖（R60 Scan-E E-A-01）。

WHY（測意圖非僅行為，Rule 9）：本 repo 對 active `.sh`／`.ps1` 有兩套掃描面——
CI 的語法／BOM 掃描面（`root-infra-ci.yml` 第 2 道，`-Recurse` 三棵樹＋LATEST）與
parity 的 enrollment 發現面（`tools/check_script_parity.py`）。R60 前後者自持一份
**非遞迴的四目錄名冊**，且該名冊**沒有任何完整性鎖**（實查：生產碼／測試／缺陷帳本
三面 grep，唯一相關斷言是 `assertIn("tools/lib", _PAIR_SCAN_DIRS)` 的成員存在性）。
兩邊掃到的檔案集合當時恰好相同（各 35 支），純屬「現存腳本剛好都躺在名冊列出的
目錄裡」；任何人在既有樹下新開一層子目錄放成對腳本，CI 掃得到、parity 看不到，
「新增成對腳本必為機械攔截」這個宣稱就靜默失效而沒人會知道。

本鎖守四件事（缺任一件，E-A-01 的修復都會在下一次改動中悄悄退回去）：
  1. **單一來源**：`check_script_parity` 與兩支 `.ps1` 本地鏡射鎖都真的讀 SSOT，
     沒有人偷偷回去寫自己的字面名冊（**形狀一致性**＝「SSOT == CI 第 2 道固定樹」
     那道鎖落在 `test_ps51_compat`／`test_ps1_bom`，WHY 見下方大段註解）。
  3. **遞迴性**：列舉實作真的遞迴（改回 `glob("*.sh")` 即紅）——用合成假樹驗，
     不依賴 repo 現況剛好有／沒有巢狀腳本。
  4. **完整性**：SSOT 三棵樹底下每一支 git-tracked `.sh`／`.ps1` 都真的被 parity
     的 `_discover_scripts()` 發現（掃描面縮小即紅；沿用 `test_platform_utils_dedup.py`
     的 `git ls-files` fail-loud 慣例）。

執行：python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_TESTS_DIR))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
import test_ps1_bom  # noqa: E402
import test_ps51_compat  # noqa: E402

from _script_scan_surface import (  # noqa: E402
    LATEST_TREE_KEY,
    SCRIPT_SCAN_ROOTS,
    iter_tree_scripts,
)


def _load_parity():
    """以絕對路徑載入 `tools/check_script_parity.py`（不依賴 cwd）。"""
    spec = importlib.util.spec_from_file_location(
        "_ssot_lock_check_script_parity", _REPO_ROOT / "tools" / "check_script_parity.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 🔴 「SSOT 名冊 == CI 第 2 道固定掃描樹」這道**形狀一致性鎖**刻意**不放在本檔**，
# 而是落在 `test_ps51_compat.TestPs51ScanConfigPinning.
# test_tree_set_matches_root_infra_ci_pwsh_step`（該處期望值已改引 `SCRIPT_SCAN_ROOTS`），
# 另一份對等鎖在 `test_ps1_bom.TestScanConfigPinning.
# test_scan_prefixes_match_root_infra_ci_pwsh_step`。WHY：那兩支已是
# `test_ci_scan_anchors._SSOT_CALLERS` 的登記呼叫端，受「必須接滿三條抽取錨
# （fixed_trees／scan_statement_count／gci_call_count）」的契約管轄；本檔若自己再抽一次
# CI step，就會成為第 4 份只接一條錨的呼叫端——那正是 R56/R57 反覆修過的
# 「三份複本各帶同一個 fail-open」形態（`-Path` 位置參數、引號 filter、全小寫寫法
# 都能繞過單錨）。故本檔只鎖「SSOT 自身的單一來源／遞迴性／完整性」，CI 比對交給
# 已完整接線的那兩支，並由本檔的 `TestSsotHasNoSecondRoster` 確保它們真的讀 SSOT
# ——三者合起來構成 `SSOT == ps51/bom 鏡射 == CI 第 2 道` 的機械鏈。


class TestSsotHasNoSecondRoster(unittest.TestCase):
    """單一來源：三個 Python 消費者都必須真的讀 SSOT，不得自持第二份名冊。"""

    def test_parity_pair_scan_dirs_is_the_ssot_tuple(self) -> None:
        parity = _load_parity()
        self.assertIs(
            parity._PAIR_SCAN_DIRS, SCRIPT_SCAN_ROOTS,
            "check_script_parity._PAIR_SCAN_DIRS 不再指向 SSOT `SCRIPT_SCAN_ROOTS`"
            "——疑似有人把名冊複製回本地字面值（R60 E-A-01 迴歸）",
        )

    def test_parity_source_has_no_literal_roster(self) -> None:
        """負面斷言：生產碼不得再出現「一行列滿掃描根」的字面名冊。

        `assertIs` 只保證「現在指向 SSOT」；有人另加一份平行名冊給別的函式用時
        它仍全綠。本斷言鎖住的是「本檔不再是掃描根的持有者」這個意圖。
        """
        src = (_REPO_ROOT / "tools" / "check_script_parity.py").read_text(
            encoding="utf-8"
        )
        code = "\n".join(
            ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
        )
        for root in ("AutoClaude/tools", "AISDLC_SDD/scripts"):
            self.assertNotIn(
                f'"{root}"', code,
                f"check_script_parity.py 的功能碼出現掃描根字面值 {root!r}"
                "——掃描根一律取自 `_script_scan_surface.SCRIPT_SCAN_ROOTS` SSOT",
            )

    def test_ps51_compat_scan_trees_keys_come_from_ssot(self) -> None:
        keys = [key for key, _files, _floor in test_ps51_compat.scan_trees()]
        self.assertEqual(
            keys, list(SCRIPT_SCAN_ROOTS) + [LATEST_TREE_KEY],
            "test_ps51_compat.scan_trees() 的樹 key 序列與 SSOT 不一致",
        )

    def test_ps1_bom_scan_prefixes_come_from_ssot(self) -> None:
        prefixes = test_ps1_bom._scan_prefixes()
        self.assertEqual(
            list(prefixes[: len(SCRIPT_SCAN_ROOTS)]),
            [f"{root}/" for root in SCRIPT_SCAN_ROOTS],
            "test_ps1_bom._scan_prefixes() 的固定樹前綴與 SSOT 不一致",
        )
        self.assertTrue(
            prefixes[-1].startswith("AISDLC_SDD/")
            and prefixes[-1] != "AISDLC_SDD/scripts/",
            f"最後一項應為 LATEST 版整版目錄前綴，實得 {prefixes[-1]!r}",
        )


class TestScanSurfaceIsRecursive(unittest.TestCase):
    """遞迴性（本鎖的核心鑑別力）：用合成假樹驗，不靠 repo 現況。

    R60 實測基線：修復前 `_discover_scripts()` 對 `tools/ops/newpair.{sh,ps1}`、
    `AutoClaude/tools/hooks/hookpair.{sh,ps1}` 一律回 False（非遞迴 glob）。把
    `iter_tree_scripts()` 的 `rglob` 改回 `glob` 本類別即翻紅。
    """

    _NESTED_PAIRS = ("tools/ops/newpair", "AutoClaude/tools/hooks/hookpair")
    _NESTED_SINGLES = ("AISDLC_SDD/scripts/nested/deep.sh", "tools/lib/libonly.ps1")
    _TOP_LEVEL_PAIR = "tools/legitpair"
    _TOP_LEVEL_SINGLE = "tools/legit.sh"

    def _fake_tree(self, td: str) -> Path:
        fake = Path(td)
        rels = [f"{p}{suffix}" for p in self._NESTED_PAIRS for suffix in (".sh", ".ps1")]
        rels += list(self._NESTED_SINGLES)
        rels += [f"{self._TOP_LEVEL_PAIR}{suffix}" for suffix in (".sh", ".ps1")]
        rels.append(self._TOP_LEVEL_SINGLE)
        for rel in rels:
            path = fake / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8", newline="")
        return fake

    def test_iter_tree_scripts_walks_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            found = set(iter_tree_scripts(self._fake_tree(td)))
        for rel in self._NESTED_SINGLES:
            self.assertIn(
                rel, found,
                f"{rel} 未被列舉——`iter_tree_scripts()` 疑似退回非遞迴 glob（E-A-01 迴歸）",
            )
        # 正控：非遞迴實作也找得到的頂層檔仍在（證明本測試不是「一律通過」）
        self.assertIn(self._TOP_LEVEL_SINGLE, found)

    def test_parity_discovers_nested_pairs_and_singles(self) -> None:
        parity = _load_parity()
        with tempfile.TemporaryDirectory() as td:
            fake = self._fake_tree(td)
            with mock.patch.object(parity, "_REPO_ROOT", fake):
                pairs, singles = parity._discover_scripts(None)
        for stem in self._NESTED_PAIRS:
            self.assertIn(
                stem, pairs,
                f"巢狀成對腳本 {stem}.sh/.ps1 未被 enrollment 發現——CI 的 -Recurse "
                "掃得到它、parity 卻看不到（E-A-01 本體迴歸）",
            )
        for rel in self._NESTED_SINGLES:
            self.assertIn(rel, singles, f"巢狀單邊腳本 {rel} 未被 enrollment 發現")
        # 兩個正控（掃描面若整體壞掉，這兩條會先紅，可分辨「壞了」與「只是不遞迴」）
        self.assertIn(self._TOP_LEVEL_PAIR, pairs)
        self.assertIn(self._TOP_LEVEL_SINGLE, singles)


class TestScanSurfaceCompleteness(unittest.TestCase):
    """完整性：SSOT 三棵樹底下每支 git-tracked 腳本都真的被 enrollment 發現。"""

    def _tracked_scripts(self) -> list[str]:
        proc = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
             "ls-files", "--", "*.sh", "*.ps1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"git ls-files 失敗（rc={proc.returncode}；stderr="
                f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
            )
        prefixes = tuple(f"{root}/" for root in SCRIPT_SCAN_ROOTS)
        return sorted(
            line for line in proc.stdout.splitlines()
            if line and line.startswith(prefixes)
        )

    def test_every_tracked_script_in_ssot_trees_is_discovered(self) -> None:
        tracked = self._tracked_scripts()
        # 下限釘選：2026-07-28 實測 35 支（三棵樹內、不含 LATEST 版樹）。低於此數
        # ＝git ls-files 樣式或 SSOT 前綴被改壞，等同掃描面靜默縮小。
        self.assertGreaterEqual(
            len(tracked), 35,
            f"SSOT 三棵樹內只找到 {len(tracked)} 支 tracked .sh/.ps1（下限 35）"
            "——掃描面疑似縮小；刻意刪減腳本請同步下修本下限",
        )
        parity = _load_parity()
        pairs, singles = parity._discover_scripts(None)
        discovered = set(singles) | {
            f"{stem}{suffix}" for stem in pairs for suffix in (".sh", ".ps1")
        }
        missing = [rel for rel in tracked if rel not in discovered]
        self.assertEqual(
            missing, [],
            "以下 git-tracked 腳本落在 SSOT 掃描樹內、卻未被 check_script_parity 的 "
            f"enrollment 發現（納管完整性破洞）：{missing}",
        )


if __name__ == "__main__":
    unittest.main()
