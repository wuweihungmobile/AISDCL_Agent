#!/usr/bin/env python3
"""tools/install_windows_nightly.ps1 結構驗證（R19 修復包 D）。

背景：mac 側 tools/install_mac_nightly.sh 提供一鍵 install/uninstall/status/
render-only 排程安裝器；Windows 側先前只有 AutoClaude/tools/fix_nightly_catchup.ps1
——假設 AutoClaude_Nightly 這個 schtasks 任務已存在，只能校正設定、不能從零建立。
本測試驗證新補上的 tools/install_windows_nightly.ps1 結構正確且與既有生態系（
fix_nightly_catchup.ps1 的補跑保護目標值、run_local_nightly.ps1 檔頭記載的排程慣例）
不漂移。

`Register-ScheduledTask`/`Get-ScheduledTask` 屬 Windows ScheduledTasks 模組，非
Windows 主機（含本專案開發常用的 macOS/Linux pwsh）無法真的執行——本測試刻意只做
靜態文字結構驗證（＋若本機有 pwsh 則額外做語法解析，純解析不執行，跨平台安全），
不嘗試真的呼叫排程 API。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
_FIX_CATCHUP = _REPO_ROOT / "AutoClaude" / "tools" / "fix_nightly_catchup.ps1"
_NIGHTLY_PS1 = _REPO_ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class TestInstallWindowsNightlyStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _read(_SCRIPT)

    def test_file_exists(self) -> None:
        self.assertTrue(_SCRIPT.is_file(), f"{_SCRIPT} 不存在")

    def test_supports_whatif(self) -> None:
        """render-only/預覽模式：以 PowerShell 內建 SupportsShouldProcess 支援
        -WhatIf，而非自製旗標（可省去自行判斷「哪些呼叫要跳過」的重複邏輯）。"""
        self.assertIn(
            "SupportsShouldProcess", self.text,
            "缺 [CmdletBinding(SupportsShouldProcess)]——無法透過內建 -WhatIf 預覽而不變更系統",
        )
        self.assertIn("$PSCmdlet.ShouldProcess(", self.text, "系統變更呼叫（Register/Unregister-ScheduledTask）未包在 ShouldProcess 守衛內")

    def test_provides_install_uninstall_status_modes(self) -> None:
        self.assertIn("[switch]$Uninstall", self.text)
        self.assertIn("[switch]$Status", self.text)
        self.assertIn("Register-ScheduledTask", self.text)
        self.assertIn("Unregister-ScheduledTask", self.text)
        self.assertIn("Get-ScheduledTaskInfo", self.text)

    def test_task_name_matches_existing_ecosystem(self) -> None:
        """新安裝器建立的任務名必須與既有 fix_nightly_catchup.ps1 校正的任務同名，
        否則新安裝的任務不會被既有校正腳本認得。"""
        fix_text = _read(_FIX_CATCHUP)
        m = re.search(r"\$TaskName\s*=\s*'([^']+)'", fix_text)
        self.assertIsNotNone(m, "fix_nightly_catchup.ps1 找不到 $TaskName 賦值——結構已變動")
        expected_name = m.group(1)
        self.assertIn(
            f"$TaskName = '{expected_name}'", self.text,
            f"install_windows_nightly.ps1 的任務名須與 fix_nightly_catchup.ps1 一致（{expected_name}）",
        )

    def test_catchup_settings_match_fix_nightly_catchup_target_values(self) -> None:
        """建立時直接內建 fix_nightly_catchup.ps1 記載的補跑保護目標值
        （StartWhenAvailable=True / WakeToRun=True / DisallowStartIfOnBatteries=False /
        StopIfGoingOnBatteries=False），新機器不必再手動跑一次 fix 腳本。

        DEF-101-249（R20 真 Windows 機器驗證）：`fix_nightly_catchup.ps1` 讀寫既有
        任務走「物件屬性賦值」（`$t.Settings.DisallowStartIfOnBatteries = $false`），
        物件屬性名就是 DisallowStartIfOnBatteries／StopIfGoingOnBatteries，那裡沒錯；
        但 `install_windows_nightly.ps1` 是用「建構」cmdlet
        `New-ScheduledTaskSettingsSet` 從零產生同一份設定，這個 cmdlet 的參數名
        極性相反、名稱也不同——`-AllowStartIfOnBatteries`／
        `-DontStopIfGoingOnBatteries`，原參數名在此 cmdlet 上根本不存在，真機呼叫
        會拋 ParameterBindingException（見同檔 TestInstallWindowsNightlySettingsConstruction
        的真機呼叫驗證）。此處只做語意對齊靜態檢查：目標值透過描述性註解與正確的
        cmdlet 參數名雙重確認一致，不斷言（也不可斷言）兩支腳本使用同一組參數字面。
        """
        fix_text = _read(_FIX_CATCHUP)
        for expected_setting in (
            "StartWhenAvailable", "WakeToRun",
            "DisallowStartIfOnBatteries", "StopIfGoingOnBatteries",
        ):
            self.assertIn(
                expected_setting, fix_text,
                f"{_FIX_CATCHUP.name} 不再提及 {expected_setting}——登記表已腐化，需同步核對",
            )
            self.assertIn(
                expected_setting, self.text,
                f"install_windows_nightly.ps1 缺 {expected_setting} 描述性註解——"
                f"與 {_FIX_CATCHUP.name} 記載的補跑保護目標值不同步",
            )
        self.assertIn(
            "-AllowStartIfOnBatteries", self.text,
            "New-ScheduledTaskSettingsSet 建構呼叫缺 -AllowStartIfOnBatteries——"
            "此 cmdlet 無 -DisallowStartIfOnBatteries 參數（DEF-101-249）",
        )
        self.assertIn(
            "-DontStopIfGoingOnBatteries", self.text,
            "New-ScheduledTaskSettingsSet 建構呼叫缺 -DontStopIfGoingOnBatteries——"
            "此 cmdlet 無 -StopIfGoingOnBatteries 參數（DEF-101-249）",
        )
        # DEF-101-249（R20 QA 二審對抗式 bug-injection 發現）：上面兩個 assertIn 只做
        # 子字串比對，若參數名字面保留正確、但被加上 `:$false` 反轉極性（例如
        # `-AllowStartIfOnBatteries:$false`——實際行為與原始錯誤參數名效果相同，
        # 真正把「筆電吃電池時擋啟動」打開），兩個 assertIn 仍會誤判為 PASS；只有
        # 真機執行測試（TestInstallWindowsNightlySettingsConstruction）能擋下這種
        # 繞過。補這兩條負向斷言直接堵值反轉，不必等真機測試單獨扛全部責任。
        # DEF-101-253 複審（R20 QA 二輪對抗式 bug-injection）：`$false`/`$False`
        # 在 PowerShell 完全等價（真機驗證行為相同），但原正則大小寫敏感，
        # `:$False`（大寫 F）可繞過——補 re.IGNORECASE 堵大小寫變體。
        self.assertNotRegex(
            self.text, re.compile(r"-AllowStartIfOnBatteries\s*:\s*\$false", re.IGNORECASE),
            "New-ScheduledTaskSettingsSet 不得將 -AllowStartIfOnBatteries 反轉為 :$false"
            "——這會使筆電吃電池時排程無法啟動，與 DEF-101-249 修復意圖相反",
        )
        self.assertNotRegex(
            self.text, re.compile(r"-DontStopIfGoingOnBatteries\s*:\s*\$false", re.IGNORECASE),
            "New-ScheduledTaskSettingsSet 不得將 -DontStopIfGoingOnBatteries 反轉為 :$false"
            "——這會使執行中切到電池時任務被中途砍掉，與 DEF-101-249 修復意圖相反",
        )
        self.assertNotIn(
            "-DisallowStartIfOnBatteries:", self.text,
            "New-ScheduledTaskSettingsSet 建構呼叫不得使用 -DisallowStartIfOnBatteries——"
            "此參數名在此 cmdlet 上不存在，真機會拋 ParameterBindingException（DEF-101-249 回歸）",
        )
        self.assertNotIn(
            "-StopIfGoingOnBatteries:", self.text,
            "New-ScheduledTaskSettingsSet 建構呼叫不得使用 -StopIfGoingOnBatteries——"
            "此參數名在此 cmdlet 上不存在，真機會拋 ParameterBindingException（DEF-101-249 回歸）",
        )

    def test_action_invokes_run_local_nightly_ps1_matching_documented_convention(self) -> None:
        """Action 須指向 run_local_nightly.ps1 檔頭 .NOTES 記載的既有排程慣例
        （powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...），不得另創
        第三種呼叫慣例造成漂移。"""
        nightly_text = _read(_NIGHTLY_PS1)
        self.assertIn(
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File", nightly_text,
            f"{_NIGHTLY_PS1.name} 檔頭 .NOTES 已不再記載既有排程慣例文字——結構已變動，需同步核對",
        )
        self.assertIn("-Execute 'powershell.exe'", self.text)
        self.assertIn("-NoProfile -ExecutionPolicy Bypass -File", self.text)
        self.assertIn("run_local_nightly.ps1", self.text)
        self.assertIn("-Daily", self.text)
        self.assertIn("'02:00'", self.text)

    def test_admin_elevation_check_present(self) -> None:
        """install/uninstall 需要 Register/Unregister-ScheduledTask 的系統管理員權限
        （比照既有 fix_nightly_catchup.ps1／reschedule_g0_gatecheck.ps1 慣例），
        非管理員身分須 fail-loud 提示，而非讓 Register-ScheduledTask 自己拋出難懂的例外。"""
        self.assertIn("WindowsBuiltInRole]::Administrator", self.text)

    def test_status_exit_code_reflects_task_existence(self) -> None:
        """DEF-101-248（R20 Scan-A）：-Status 先前不論任務存不存在恆 exit 0，與 mac 版
        `install_mac_nightly.sh --status`（任務未載入時非零結束代碼）語意不對等，任何
        想拿結束代碼做自動化判斷（CI／監控腳本）在 Windows 上會拿到假陽性。修復後須
        依 Show-NightlyStatus 的回傳值決定 exit 0/1，而非寫死 exit 0。"""
        status_block_match = re.search(
            r"if \(\$Status\) \{(.*?)\n\}", self.text, re.DOTALL,
        )
        self.assertIsNotNone(status_block_match, "找不到 -Status 處理區塊——結構已變動")
        status_block = status_block_match.group(1)
        self.assertNotIn(
            "exit 0\n", status_block,
            "-Status 區塊不得再寫死 exit 0——須依 Show-NightlyStatus 回傳值決定結束代碼",
        )
        self.assertIn("$loaded = Show-NightlyStatus", status_block)
        self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", status_block)

    def test_status_and_uninstall_combo_warns_instead_of_silently_ignoring(self) -> None:
        """DEF-101-246⑦（R19 backlog）：-Status 排在 -Uninstall 前面且直接 return/exit，
        若使用者同時給 -Status -Uninstall，-Uninstall 會被靜默忽略、無警告訊息，與 repo
        「fail loud」慣例（Rule 12）有落差。修復：偵測到兩者同時給出時明確警告。"""
        status_block_match = re.search(
            r"if \(\$Status\) \{(.*?)\n\}", self.text, re.DOTALL,
        )
        self.assertIsNotNone(status_block_match, "找不到 -Status 處理區塊——結構已變動")
        status_block = status_block_match.group(1)
        self.assertIn("if ($Uninstall)", status_block, "-Status 區塊未檢查 $Uninstall 是否同時給出")
        self.assertIn("Write-Warning", status_block, "-Status+-Uninstall 同給時未輸出警告——違反 fail-loud 慣例")


@unittest.skipUnless(shutil.which("pwsh"), "本機無 pwsh，跳過語法解析（純結構文字驗證仍會跑）")
class TestInstallWindowsNightlySyntax(unittest.TestCase):
    def test_parses_with_zero_errors(self) -> None:
        """[Parser]::ParseFile 只做語法樹解析，不執行——跨平台安全（macOS/Linux pwsh
        皆可跑），可及早攔住語法錯誤而不需要真的呼叫 Windows-only 的排程 API。"""
        proc = subprocess.run(
            [
                "pwsh", "-NoProfile", "-Command",
                "$errors = $null; $tokens = $null; "
                f"$null = [System.Management.Automation.Language.Parser]::ParseFile("
                f"'{_SCRIPT}', [ref]$tokens, [ref]$errors); "
                "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Output $_.Message }; exit 1 } "
                "else { exit 0 }",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(
            proc.returncode, 0,
            f"install_windows_nightly.ps1 語法解析有誤：\n{proc.stdout}\n{proc.stderr}",
        )


@unittest.skipUnless(
    platform.system() == "Windows",
    "[WINDOWS-NATIVE-ONLY] New-ScheduledTaskSettingsSet 屬 ScheduledTasks 模組，只在 "
    "Windows 上真的可呼叫（R43 DEF-101-348 標籤，供 run_root_unittests.py 彙整可見度）",
)
class TestInstallWindowsNightlySettingsConstruction(unittest.TestCase):
    """DEF-101-249（R20 真 Windows 機器驗證）：New-ScheduledTaskSettingsSet 是「建構」
    cmdlet，參數名與 Settings 物件本身的屬性名不同、甚至極性相反——物件屬性叫
    DisallowStartIfOnBatteries／StopIfGoingOnBatteries（fix_nightly_catchup.ps1 讀寫
    既有任務用的正是這兩個屬性名，那裡沒錯），但這個「建構」cmdlet 的參數名是
    -AllowStartIfOnBatteries／-DontStopIfGoingOnBatteries。原參數名
    -DisallowStartIfOnBatteries/-StopIfGoingOnBatteries 在此 cmdlet 上根本不存在，
    只有真的呼叫這個 cmdlet（非純語法解析、非 -WhatIf 抽象層——ShouldProcess 之前
    PowerShell 就會先做參數綁定）才會拋 ParameterBindingException，R19 一路只做
    語法解析從未真的呼叫過，未曾發現。

    本測試不假設腳本目前寫的是哪個參數名——直接從原始碼抽出
    `$settings = New-ScheduledTaskSettingsSet ...` 這段實際文字，原封不動丟給真正
    的 PowerShell 執行（此 cmdlet 本身不需要系統管理員權限，只有後續
    Register-ScheduledTask 才需要，故 windows-latest CI runner 可安全真跑），斷言
    建構成功且回傳物件的屬性值符合預期極性——未來若又被改回錯誤參數名，本測試會
    直接重現當初的真實 ParameterBindingException。"""

    def test_settings_construction_snippet_executes_with_expected_property_values(self) -> None:
        text = _read(_SCRIPT)
        m = re.search(
            r"\$settings\s*=\s*New-ScheduledTaskSettingsSet.*?(?=\n\s*\n)",
            text, re.DOTALL,
        )
        self.assertIsNotNone(m, "找不到 $settings = New-ScheduledTaskSettingsSet 區塊——結構已變動")
        snippet = m.group(0)

        proc = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-Command",
                f"{snippet}; "
                'Write-Output "$($settings.DisallowStartIfOnBatteries)|'
                '$($settings.StopIfGoingOnBatteries)|'
                '$($settings.StartWhenAvailable)|$($settings.WakeToRun)"',
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(
            proc.returncode, 0,
            "New-ScheduledTaskSettingsSet 真機呼叫失敗（真實 ParameterBindingException 或"
            f"其他錯誤，非語法問題）：\n{proc.stdout}\n{proc.stderr}",
        )
        self.assertEqual(
            proc.stdout.strip(), "False|False|True|True",
            f"建構出的 Settings 物件屬性值不符預期（DisallowStartIfOnBatteries/"
            f"StopIfGoingOnBatteries/StartWhenAvailable/WakeToRun 應為 "
            f"False/False/True/True）：{proc.stdout.strip()!r}",
        )


if __name__ == "__main__":
    unittest.main()
