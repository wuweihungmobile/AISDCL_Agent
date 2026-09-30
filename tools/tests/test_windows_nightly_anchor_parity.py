#!/usr/bin/env python3
"""Windows nightly RunId log／輪替／錯過補跑的靜態錨點鎖（R57 A6）。

**不對稱屬實**：`tools/macos_smoke_local.sh` 有一整步 [7/7]「nightly RunId log／
RunAtLoad 補跑靜態錨點（R15，唯讀 grep 工作樹）」，以五個功能碼錨點守住
`AutoClaude/tools/run_local_nightly.sh` 的 RunId log／14 天輪替／當日去重，外加
`tools/install_mac_nightly.sh` plist 的 `<key>RunAtLoad</key><true/>`。
`tools/windows_smoke_local.ps1`（[1/9]~[9/9]）**完全沒有對等步驟**——[9/9] 只跑
`install_windows_nightly.ps1 -WhatIf` 預覽，不驗證 nightly 執行器本身的機制。

**Windows 側並非「本質上不需要」**（R57 實查）：對等機制全部存在且是活的——
`AutoClaude/tools/run_local_nightly.ps1` 有 RunId log（`nightly_{Today}_{RunId}.log`）、
`nightly_latest.log` pointer、14 天輪替（`AddDays(-14)` + `Remove-Item`），
`tools/install_windows_nightly.ps1` 有 `-StartWhenAvailable`／`-WakeToRun`（關機/
睡眠錯過仍補跑，即 launchd `RunAtLoad` 的 Windows 對應物）。也就是說：機制對稱，
**只有守門不對稱**——這些機制在 Windows 側可被靜默移除而無任何訊號。

補成 Python unittest（而非 `windows_smoke_local.ps1` 的 [10/10] 步驟）讓四道守門全部跑到；錨點只認
**功能碼**（剝註解的邊界以 `_platform_helpers.strip_ps_comments` 的 docstring 為準）。放置取捨與
R57 沿革全文搬至 Guard_Line_History_2.md〈R186 淨減法搬遷〉§68。  round-label-ok

執行：python3 tools/run_root_unittests.py
"""
from __future__ import annotations

import unittest
from pathlib import Path

from _platform_helpers import strip_ps_comments

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NIGHTLY_PS1 = _REPO_ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
_WIN_INSTALLER = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"


def _code_only(path: Path) -> str:
    return strip_ps_comments(path.read_text(encoding="utf-8-sig", errors="replace"))


class TestWindowsNightlyRunIdLog(unittest.TestCase):
    """對應 macOS [7/7] 的 `exec >>` + `nightly_mac_2*.log` 兩錨。"""

    def test_run_id_log_filename_anchor(self) -> None:
        code = _code_only(_NIGHTLY_PS1)
        self.assertIn(
            '"nightly_{0}_{1}.log" -f $Today, $RunId', code,
            "run_local_nightly.ps1 缺 RunId log 檔名組成（nightly_<日期>_<RunId>.log）"
            "——每次 run 獨立 log 是 Nightly 取證紀律的前提（紀律 #3「PASS 聲稱必須"
            "引用 RunId log 行號」），被移除後所有取證宣稱都不可複查",
        )
        self.assertIn(
            "$RunId = Get-Date -Format 'HHmmss'", code,
            "run_local_nightly.ps1 缺 RunId 產生式（HHmmss）——同日多次 run 會互相"
            "覆蓋 log",
        )

    def test_latest_log_pointer_anchor(self) -> None:
        self.assertIn(
            "nightly_latest.log", _code_only(_NIGHTLY_PS1),
            "run_local_nightly.ps1 缺 nightly_latest.log pointer——retrieve 端"
            "（告警/複審）靠它定位最近一次 run",
        )


class TestWindowsNightlyLogRotation(unittest.TestCase):
    """對應 macOS [7/7] 的 `-mtime +14` 錨（Windows 以 `AddDays(-14)` 表達）。"""

    def test_fourteen_day_rotation_anchors(self) -> None:
        code = _code_only(_NIGHTLY_PS1)
        for needle in ("nightly_2*.log", "AddDays(-14)", "Remove-Item -Force"):
            self.assertIn(
                needle, code,
                f"run_local_nightly.ps1 缺 14 天 log 輪替錨點 `{needle}`——輪替被"
                "移除會讓 logs/ 無限增長（macOS 側同一機制由 macos_smoke_local.sh "
                "[7/7] 的 `-mtime +14` 錨守住，Windows 側原本零守門）",
            )

    def test_rotation_keeps_latest_pointer(self) -> None:
        """輪替不得把 pointer 一起刪掉（macOS 側以檔名 glob 天然避開，Windows 側
        靠 `-ne 'nightly_latest.log'` 明文排除——這行被刪掉就會週期性弄丟 pointer）。"""
        self.assertIn(
            "$_.Name -ne 'nightly_latest.log'", _code_only(_NIGHTLY_PS1),
            "run_local_nightly.ps1 的 14 天輪替未排除 nightly_latest.log pointer",
        )


class TestWindowsMissedRunCatchup(unittest.TestCase):
    """對應 macOS [7/7] 的 `<key>RunAtLoad</key><true/>` 錨。

    Windows 對應物不是 RunAtLoad 而是 schtasks 的 `-StartWhenAvailable`（錯過的
    排程在機器可用時補跑）＋ `-WakeToRun`（睡眠中喚醒）。macOS 側另有的「當日
    去重」（`--force` ＋ `RunAtLoad 補跑去重`）**在 Windows 側本質上不需要**：
    launchd 的 RunAtLoad 每次載入（開機/登入）都會觸發，所以腳本層必須自己去重；
    schtasks 的 StartWhenAvailable 由排程器決定「這次排程有沒有跑過」，不會重複
    觸發同一次排程，故 Windows 側沒有、也不該有對應的腳本層去重錨點。
    """

    def test_start_when_available_and_wake_to_run(self) -> None:
        code = _code_only(_WIN_INSTALLER)
        for needle in ("-StartWhenAvailable", "-WakeToRun"):
            self.assertIn(
                needle, code,
                f"install_windows_nightly.ps1 缺 `{needle}`——關機/睡眠錯過排程窗口"
                "後就永遠不補跑（等同 macOS 側移除 RunAtLoad，該情境正是 "
                "DEF-101-201② 與 fix_nightly_catchup.ps1 存在的理由）",
            )

    def test_installer_verifies_catchup_settings_after_register(self) -> None:
        """安裝器自身的驗證輸出也是機制的一部分：註冊完若不回讀 StartWhenAvailable，
        設定被排程器默默忽略時使用者不會知道。"""
        self.assertIn(
            "StartWhenAvailable         = $($s.StartWhenAvailable)",
            _code_only(_WIN_INSTALLER),
            "install_windows_nightly.ps1 註冊後未回讀並印出 StartWhenAvailable 實況",
        )


if __name__ == "__main__":
    unittest.main()
