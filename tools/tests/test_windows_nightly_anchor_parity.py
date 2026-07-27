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

**為何補在這裡而不是補一步 [10/10] 進 `windows_smoke_local.ps1`**：
  1. macOS [7/7] 自述「唯讀 grep 工作樹、平台無關」——它做的事根本不需要 pwsh，
     放在本機 smoke 只是歷史選擇（且 SA-R15-REV-6 已記載該組錨點刻意只入本地
     smoke、無 CI 對應，屬本地專屬防線）。
  2. 補成 Python unittest 者，四道守門（pre-push root-infra leg、root-infra-ci
     step 8、windows/macos smoke）**全部**都會跑到，覆蓋面嚴格大於只補進
     Windows 本機 smoke（後者只有真 Windows 機器上手動跑才生效——而本輪主題正是
     「Windows 專屬守門長期沒在 Windows 上跑過」，見 DEF-101-348）。
  3. 補進 `.ps1` 需連動 `$MinPass` 下限與 `test_smoke_ci_sync.py` 的步驟語意鎖，
     且在 macOS 上無法真跑驗證，收益/風險比不划算。

錨點只認**功能碼**（剝除 `<# … #>` 區塊註解、整行 `#` 註解與**尾隨行內註解**），
比照 macOS 側 QA-R15-REV-1 訂正：註解裡留著舊字樣會讓錨點假陽性。剝除範圍與
已知邊界以 `tools/tests/_ps_source.strip_ps_comments` 的 docstring 為準
（R57 QA-R57-03：初版漏剝尾隨行內註解，真刪 `-WakeToRun` 只要在註解留字樣即可讓
6 支全綠）。該函式與其鑑別力測試已於 R57 round 2（SA-R57R2-03）從本檔與
`test_find_git_bash_parity.py` 的兩份逐字複本收斂成 SSOT，R58 再依收納契約拆至專屬的
`_ps_source.py`（ARCH-R57R3-02）；一致性由
`test_find_git_bash_parity.py::TestPsCommentStripperSsotCallsiteLock`
機械守護（本檔不得再自帶同名定義）。

🔴 **本檔錨點的殘餘 fail-open 與 R58 落地的補強**：該剝除器是近似法，對 expression-mode
的尾隨註解（如 `$note = $x#  -WakeToRun`）漏剝 ⇒ 有人刪掉功能碼、只在註解留字樣，本檔
6 支錨點仍會全綠（R57 SD 已實證此繞過可行）。R58 未改近似法（R57 已定案禁止 whack-a-mole
補字元），而是新增 `tools/tests/test_ps_comment_golden.py`——以真 PowerShell parser 對全語料
凍結 Comment token 做離線差分，使該形態一旦真的出現在任何 `.ps1` 就立刻翻紅。故本檔的錨點
與那支差分測試是**一組**：本檔驗「錨點在不在」，差分測試驗「本檔看到的功能碼是不是真的功能碼」。

執行：python3 tools/run_root_unittests.py
"""
from __future__ import annotations

import unittest
from pathlib import Path

from _ps_source import normalize_ps_source, strip_ps_comments

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NIGHTLY_PS1 = _REPO_ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
_WIN_INSTALLER = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"


def _code_only(path: Path) -> str:
    """讀檔並剝註解。R58 改走 `normalize_ps_source()`（原為 `read_text(utf-8-sig,
    errors="replace")`）：與 golden 差分測試共用同一份正規化契約（跳 BOM + CRLF→LF），
    否則兩者對「同一支檔案的內容」會有不同看法，差分的結論就無法套用到本檔的錨點。
    另刻意去掉 `errors="replace"`——本 repo 的 `.ps1` 全數以 UTF-8 解碼成功（R58 產生
    golden 時對全 137 支實測），靜默替換無效位元組只會把編碼問題藏起來（fail loud 優先）。
    """
    return strip_ps_comments(normalize_ps_source(path.read_bytes()))


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
