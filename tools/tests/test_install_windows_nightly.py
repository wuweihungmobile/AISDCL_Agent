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
        StopIfGoingOnBatteries=False），新機器不必再手動跑一次 fix 腳本。"""
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
                f"install_windows_nightly.ps1 缺 {expected_setting} 設定——"
                f"與 {_FIX_CATCHUP.name} 記載的補跑保護目標值不同步",
            )
        self.assertIn("-DisallowStartIfOnBatteries:$false", self.text)
        self.assertIn("-StopIfGoingOnBatteries:$false", self.text)

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


if __name__ == "__main__":
    unittest.main()
