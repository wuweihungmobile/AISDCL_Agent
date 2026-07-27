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
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _platform_helpers import powershell_exe  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
_FIX_CATCHUP = _REPO_ROOT / "AutoClaude" / "tools" / "fix_nightly_catchup.ps1"
_NIGHTLY_PS1 = _REPO_ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


class TestInstallWindowsNightlyStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _read(_SCRIPT)

    def _status_block(self) -> str:
        r"""定位 `-Status` 區塊，**並先鎖住「分派只有一處」**（本類唯一的定位入口）。

        R58 round 3 QA-R58R3-01：定位改**行首錨定且要求左大括號結束該行**——原正則
        `if \(\$Status\) \{(.*?)\n\}` 會把單行分派 `if ($Status) { … }` 也當成區塊起點，
        於是「在受鎖區塊之前插入一個先命中的單行分派」可短路掉整段受鎖邏輯，而三道機器
        無關防線全部看不到（只有機器相依的 E2E 第 ④ 不變式抓得到）。

        R58 round 4（SD 與 QA 各自以注入實測指出，兩人皆評 P3）：round 3 的錨寫成 `(?m)^if`，
        對**縮排**的重複分派仍隱形（PowerShell 頂層縮排無語意、照樣執行），故放寬為
        `(?m)^[ \t]*if`。同輪並把定位抽成**共用 helper**：
        `test_status_and_uninstall_combo_warns_instead_of_silently_ignoring` 原本自持一份
        **未錨定**的舊正則，是同族的防禦縱深缺口——兩支測試共用同一份定位邏輯後，
        唯一性鎖對兩者同時生效，且下次改判準只有一個地方要改。
        """
        self.assertEqual(
            len(re.findall(r"(?m)^[ \t]*if \(\$Status\)", self.text)), 1,
            "`-Status` 分派必須只有一處——重複分派會讓先命中的那個短路掉受鎖的區塊，而靜態鎖"
            "只檢查它找到的第一個區塊（縮排變體亦計入：PowerShell 頂層縮排無語意、照樣執行）",
        )
        match = re.search(r"(?m)^[ \t]*if \(\$Status\) \{$(.*?)\n\}", self.text, re.DOTALL)
        self.assertIsNotNone(match, "找不到 -Status 處理區塊——結構已變動")
        assert match is not None  # for type checkers
        return match.group(1)

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
        status_block = self._status_block()
        self.assertNotIn(
            "exit 0\n", status_block,
            "-Status 區塊不得再寫死 exit 0——須依 Show-NightlyStatus 回傳值決定結束代碼",
        )
        # R58 round 2 QA-R58R2-03：原為 `assertIn` 子字串比對，故
        # `$loaded = Show-NightlyStatus | Out-String` 這種**呼叫端退化**可完全繞過它
        # ——而型別主鎖不執行呼叫端、看不到這一行，只有 E2E 那條「機器相依」的不變式
        # 抓得到（在四項設定全對的乾淨機器／CI 上就沒有訊號）。改為整行錨定，機器無關。
        self.assertRegex(
            status_block, r"(?m)^\s*\$loaded = Show-NightlyStatus\s*$",
            "呼叫端必須是**單獨一行**的 `$loaded = Show-NightlyStatus`：此行不得再接 "
            "pipeline（如 `| Out-String`）、也不得改成賦值以外的形式——否則 `$loaded` 會"
            "捕獲非布林值，`if ($loaded)` 對元素數 ≥2 的陣列一律判真，結束代碼契約當場失效"
            "（DEF-101-512 的原始成因）。本條是三道防線中唯一看得到呼叫端那一行的。",
        )
        self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", status_block)

    def test_status_and_uninstall_combo_warns_instead_of_silently_ignoring(self) -> None:
        """DEF-101-246⑦（R19 backlog）：-Status 排在 -Uninstall 前面且直接 return/exit，
        若使用者同時給 -Status -Uninstall，-Uninstall 會被靜默忽略、無警告訊息，與 repo
        「fail loud」慣例（Rule 12）有落差。修復：偵測到兩者同時給出時明確警告。"""
        status_block = self._status_block()
        self.assertIn("if ($Uninstall)", status_block, "-Status 區塊未檢查 $Uninstall 是否同時給出")
        self.assertIn("Write-Warning", status_block, "-Status+-Uninstall 同給時未輸出警告——違反 fail-loud 慣例")


@unittest.skipUnless(
    powershell_exe(),
    "本機無 powershell 也無 pwsh，跳過語法解析（純結構文字驗證仍會跑）",
)
class TestInstallWindowsNightlySyntax(unittest.TestCase):
    def test_parses_with_zero_errors(self) -> None:
        """[Parser]::ParseFile 只做語法樹解析，不執行——跨平台安全（macOS/Linux pwsh
        皆可跑），可及早攔住語法錯誤而不需要真的呼叫 Windows-only 的排程 API。

        **R58 修正（DEF-101-507）**：本類原本是 `skipUnless(shutil.which("pwsh"))`、且指令列
        寫死 `"pwsh"`。Windows 11 出廠只有 Windows PowerShell 5.1、不含 pwsh 7，於是這道
        「Windows 專屬安裝器的語法守門」**在它唯一要保護的平台上恆 skip**（R58 於真 Windows 11
        實測 skip 清單即含本測試），卻在裝了 pwsh 的 macOS 開發機上會跑。改走
        `_platform_helpers.powershell_exe()`（Windows 上優先出廠 5.1，理由見該函式 docstring），
        本機實測 5.1 對本檔 parse 出 0 errors。
        另注意：**本測試只驗一支檔案**；R58 同輪新增的 `test_ps_comment_golden.py` 已把
        「全 137 支 tracked `.ps1` 皆零 parse error」做成**離線**事實（由 golden 凍結），
        任何平台無條件會驗，涵蓋面遠大於本測試——本測試保留的價值是「就地、對本檔、用現場
        引擎」的第二道獨立訊號。
        """
        exe = powershell_exe()
        assert exe is not None  # skipUnless 已保證；讓型別檢查與讀者都清楚
        proc = subprocess.run(
            [
                exe, "-NoProfile", "-Command",
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


def _extract_ps_function(text: str, name: str) -> str:
    """抽出 `function <name> { ... }` 的完整區塊（含大括號），以大括號深度掃描。

    不用 regex：PowerShell 函式體內有巢狀 `{}`（`foreach {}`／`if {}`／`${var}`），
    regex 的 `.*?}` 會在第一個內層 `}` 就停下，抽到半截函式後所有斷言都失去意義。
    本 repo 的 .ps1 大括號皆成對（含字串內的 `${...}`），深度掃描足夠且無歧義。
    """
    start = text.index(f"function {name} {{")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"function {name} 大括號不成對——無法抽出完整區塊")


# 四項電源／補跑保護設定 → 期望值。與 AutoClaude/tests/tools/
# test_reschedule_g0_gatecheck_static.py 的 _POWER_SETTINGS 同一份領域知識
# （Task Scheduler 有哪些漏跑/中斷開關），兩檔各自守自己那支腳本。
_POWER_SETTINGS = {
    "StartWhenAvailable": True,
    "WakeToRun": True,
    "DisallowStartIfOnBatteries": False,
    "StopIfGoingOnBatteries": False,
}


class TestStatusVerifiesPowerSettings(unittest.TestCase):
    """`-Status` 是全 repo 唯一的官方排程查詢入口。2026-07-27 真 Windows 原生機器實測，
    它印出四項並附 `(expected …)` 字樣，卻**無條件回報成功**——於是「排程電源設定漂移」
    在整個 repo 沒有任何會翻紅的路徑（實測 AutoClaude_SD09_G0_GateCheck 的
    StopIfGoingOnBatteries=True 已漂移數週，零訊號）。

    同一次實測還揪出更嚴重的一層：`Show-NightlyStatus` 用 `Write-Output` 印報告，
    而呼叫端是 `$loaded = Show-NightlyStatus`——PowerShell 的變數指派會把 success
    stream 的所有輸出一起吃掉，所以 ① 報告一行都不顯示（`-Status` 實測輸出 0 bytes）；
    ② `$loaded` 變成「字串…＋布林」的 Object[]，PowerShell 對元素數 ≥2 的陣列一律
    判真 → `if ($loaded) { exit 0 }` 恆成立。也就是說 DEF-101-248 宣稱的「-Status
    依任務存在與否決定結束代碼」修復從未真正生效（對不存在的任務實測 exit 0）。
    """

    def setUp(self) -> None:
        self.text = _read(_SCRIPT)

    def test_power_settings_gate_covers_all_four_with_correct_polarity(self) -> None:
        """四項都要在回傳的判定式內，且期望 False 的兩項須被 `-not` 包住。"""
        fn = _extract_ps_function(self.text, "Test-TaskPowerSettings")
        m = re.search(r"return \((.*?)\)\s*\n\}", fn, re.DOTALL)
        self.assertIsNotNone(
            m, f"Test-TaskPowerSettings 找不到 `return (...)` 判定式——結構已變動：\n{fn}"
        )
        expr = " ".join(m.group(1).split())
        for name, expected in _POWER_SETTINGS.items():
            self.assertIn(
                f"$s.{name}", expr,
                f"-Status 的成功判定未納入 {name}——印了卻不驗，等於印給空氣看",
            )
            negated = re.search(rf"-not\s+\$s\.{name}\b", expr) is not None
            self.assertEqual(
                negated, not expected,
                f"{name} 極性錯誤：期望值 {expected}，"
                f"故{'不應' if expected else '應'}被 `-not` 包住。實際：{expr}",
            )

    def test_status_report_avoids_write_output_stream_capture(self) -> None:
        """回歸鎖：`-Status` 的報告不得用 `Write-Output` 印。

        呼叫端 `$loaded = Show-NightlyStatus` 會捕獲 success stream，用
        `Write-Output` 就會同時弄壞「報告顯示」與「結束代碼」兩件事（實測 0 bytes
        + 恆 exit 0）。報告一律走 `Write-Host`（PS 5.1 的 information stream，
        不被變數指派捕獲，但仍會落進被重導向的行程 stdout——已實測涵蓋
        `> file 2>&1`）。install/uninstall 分支的 `Write-Output` 不受此限（那些在
        頂層執行，沒有被指派捕獲），故本測試只掃這兩支函式。
        """
        for fn_name in ("Test-TaskPowerSettings", "Show-NightlyStatus"):
            fn = _extract_ps_function(self.text, fn_name)
            code = "\n".join(
                ln for ln in fn.splitlines() if not ln.strip().startswith("#")
            )
            self.assertNotIn(
                "Write-Output", code,
                f"{fn_name} 使用了 Write-Output——其輸出會被呼叫端 "
                f"`$loaded = Show-NightlyStatus` 的變數指派吃掉，導致報告不顯示"
                f"且結束代碼恆 0（2026-07-27 實測的原始缺陷）。請用 Write-Host。",
            )
            self.assertIn(
                "Write-Host", code, f"{fn_name} 完全沒有輸出——狀態查詢入口不得靜默",
            )

    def test_status_covers_repo_registered_tasks_not_just_the_installed_one(self) -> None:
        """涵蓋面：不得只驗本安裝器管理的單一任務。

        `$AuxTaskNames` 須包含 `AutoClaude/tools/reschedule_g0_gatecheck.ps1` 管的
        任務名，且該名稱從對方腳本實抽（不寫死字面），避免兩檔漂移後本測試變空殼。
        """
        aux_m = re.search(r"\$AuxTaskNames\s*=\s*@\(([^)]*)\)", self.text)
        self.assertIsNotNone(aux_m, "找不到 $AuxTaskNames 清單——-Status 涵蓋面登記已被移除")
        aux_names = set(re.findall(r"'([^']+)'", aux_m.group(1)))

        reschedule_ps1 = _REPO_ROOT / "AutoClaude" / "tools" / "reschedule_g0_gatecheck.ps1"
        resched_m = re.search(r"\$TaskName\s*=\s*'([^']+)'", _read(reschedule_ps1))
        self.assertIsNotNone(
            resched_m, f"{reschedule_ps1.name} 找不到 $TaskName 賦值——結構已變動"
        )
        self.assertIn(
            resched_m.group(1), aux_names,
            f"-Status 未涵蓋 {reschedule_ps1.name} 註冊的任務 "
            f"{resched_m.group(1)!r}（目前涵蓋：{aux_names}）——該任務的電源設定漂移"
            f"就會回到「全 repo 無任何翻紅路徑」的原狀",
        )

    def test_absent_aux_task_is_not_treated_as_failure(self) -> None:
        """aux 任務缺席只能印資訊、不得判失敗：一次性 gate check 跑完被移除是正常
        終態，硬要求存在會讓乾淨機器與 CI runner 上的 `-Status` 恆紅。"""
        fn = _extract_ps_function(self.text, "Show-NightlyStatus")
        m = re.search(r"if \(-not \$auxTask\) \{(.*?)\n    \}", fn, re.DOTALL)
        self.assertIsNotNone(m, "找不到 aux 任務缺席分支——結構已變動")
        branch = m.group(1)
        self.assertIn("continue", branch, "aux 任務缺席時未 continue——會誤把缺席算成漂移")
        self.assertNotIn(
            "$allOk = $false", branch,
            "aux 任務缺席被判失敗——乾淨機器/CI runner 上 -Status 會恆紅",
        )


@unittest.skipUnless(
    powershell_exe(),
    "本機無 powershell 也無 pwsh，跳過行為層驗證（純結構文字驗證仍會跑）",
)
class TestStatusPowerSettingsFunctionBehaviour(unittest.TestCase):
    """行為層：把腳本裡**真正那一支** `Test-TaskPowerSettings` 抽出來丟給真的
    PowerShell 執行。

    為何靜態層不夠：`test_status_report_avoids_write_output_stream_capture` 只擋
    `Write-Output` 這個字面，擋不掉其他會寫 success stream 的寫法（裸表達式、
    `$x` 單獨一行、忘了 `| Out-Null` 的 cmdlet）——那些同樣會讓回傳值退化成
    Object[] 並使結束代碼恆 0。這裡直接斷言回傳型別是 Boolean，從行為面封住整類。

    🔴 **本類的涵蓋面有一道當初沒說清的邊界（R58 四方複審三位各自獨立證出，故補記）**：
    它驗的是**被呼叫者** `Test-TaskPowerSettings` 的回傳型別，而結束代碼契約的所在是
    **呼叫者** `Show-NightlyStatus` 的 success stream 組成。實測反證：在
    `Show-NightlyStatus` 內插入一行裸表達式 `$info.LastTaskResult`（刻意不是
    `Write-Output`，故上面那道字面禁令無感），真實 `-Status` 的結束代碼當場由 1 退回 0
    ——而本檔當時全數綠燈。也就是說「封住整類」這句話只對 `Test-TaskPowerSettings`
    這一支成立，對真正出事的那一支不成立。補上的行為層鎖是同檔的
    `TestShowNightlyStatusReturnsCleanBoolean`（直接執行 `Show-NightlyStatus` 本身）；
    本類保留為「逐項極性」這一維的獨立訊號（那一維新類不驗）。

    刻意不碰任何真實排程任務（不需 Get-ScheduledTask、不需系統管理員）：`$Task`
    由 [pscustomobject] 合成，故可在 CI runner 與開發機上安全真跑。也因為不碰
    ScheduledTasks 模組，本類**不必**限定 Windows（對比同檔的
    TestInstallWindowsNightlySettingsConstruction 必須限定），改走
    `_platform_helpers.powershell_exe()`：Windows 上優先出廠的 5.1（＝使用者的目標
    引擎），其他平台退回 pwsh，兩處都能驗到同一組 stream 語意（DEF-101-507 判準）。
    """

    def _invoke(self, values: dict[str, bool]) -> str:
        fn = _extract_ps_function(_read(_SCRIPT), "Test-TaskPowerSettings")
        props = "; ".join(f"{k}=${str(v).lower()}" for k, v in values.items())
        script = (
            f"{fn}\n"
            f"$fake = [pscustomobject]@{{ Settings = [pscustomobject]@{{ {props} }} }}; "
            f"$r = Test-TaskPowerSettings -Task $fake; "
            'Write-Output "$($r.GetType().Name)|$r"'
        )
        exe = powershell_exe()
        assert exe is not None  # skipUnless 已保證
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(
            proc.returncode, 0,
            f"Test-TaskPowerSettings 真機執行失敗：\n{proc.stdout}\n{proc.stderr}",
        )
        # 報告走 Write-Host，理應不進 stdout 的最後一行以外；取最後一行即回傳值。
        return proc.stdout.strip().splitlines()[-1].strip()

    def test_returns_clean_boolean_true_when_all_settings_correct(self) -> None:
        self.assertEqual(
            self._invoke(dict(_POWER_SETTINGS)), "Boolean|True",
            "四項全對時未回傳純 Boolean True。若型別是 Object[]，代表函式把人類可讀"
            "報告寫進了 success stream——呼叫端 `$loaded = Show-NightlyStatus` 會拿到"
            "非空陣列（PowerShell 一律判真）→ -Status 結束代碼恆 0，即 2026-07-27 "
            "實測的原始缺陷",
        )

    def test_returns_false_when_any_single_setting_drifts(self) -> None:
        """逐項翻轉：任一項漂移都必須回 False，證明四項皆為承載項。"""
        for name, expected in _POWER_SETTINGS.items():
            with self.subTest(setting=name):
                values = dict(_POWER_SETTINGS)
                values[name] = not expected
                self.assertEqual(
                    self._invoke(values), "Boolean|False",
                    f"只把 {name} 翻成 {values[name]}，判定式仍為 True——該項不是承載項。"
                    f"實測事故：AutoClaude_SD09_G0_GateCheck 的 StopIfGoingOnBatteries"
                    f"=True 漂移數週而 -Status 照樣回報成功",
                )



# 合成任務名（刻意帶 DoNotRegister 字樣）：本檔的行為層驗證全程只餵這兩個名字給被
# 遮蔽的 Get-ScheduledTask，真實 Task Scheduler 內不存在也不會被建立。若哪天遮蔽失效
# （例如腳本改成模組限定呼叫 `ScheduledTasks\Get-ScheduledTask`），真實查詢會查不到
# 這兩個名字 → 回 $false → 「四項全對應為 True」那條當場翻紅（fail-closed，不會靜默
# 變成查真實排程）。另有 _SENTINEL_LAST_RUN 正向證明合成物件真的被消費（見下）。
_FAKE_MAIN_TASK = "AISDCL_FakeMainTask_DoNotRegister"
_FAKE_AUX_TASK = "AISDCL_FakeAuxTask_DoNotRegister"
_SENTINEL_LAST_RUN = "SENTINEL-LastRunTime"


@unittest.skipUnless(
    powershell_exe(),
    "本機無 powershell 也無 pwsh，跳過行為層驗證（純結構文字驗證仍會跑）",
)
class TestShowNightlyStatusReturnsCleanBoolean(unittest.TestCase):
    """行為層：真的執行 `Show-NightlyStatus` **本身**，斷言它的回傳型別恆為 Boolean。

    ## 為何非要驗這一支（R58 四方複審三位各自獨立證出的同一件事）

    `-Status` 的結束代碼契約由呼叫端這兩行實現：

        $loaded = Show-NightlyStatus
        if ($loaded) { exit 0 } else { exit 1 }

    PowerShell 的**變數指派會捕獲整個 success stream**，所以契約成立的前提是
    `Show-NightlyStatus`（連同它的巢狀呼叫）除了那個布林之外**什麼都不往 success
    stream 寫**。一旦多寫了任何東西，`$loaded` 就退化成 `Object[]`，而 PowerShell 對
    元素數 ≥2 的陣列一律判真 → `exit 0` 恆成立、缺陷復活。

    本檔原有的防線都擋不住這件事：
      * `test_status_report_avoids_write_output_stream_capture` 只擋 `Write-Output`
        這個**字面**——裸表達式、`$x` 單獨一行、忘了 `| Out-Null` 的 cmdlet 全數繞過。
      * `TestStatusPowerSettingsFunctionBehaviour` 雖是行為層，但驗的是**被呼叫者**
        `Test-TaskPowerSettings`，不是缺陷所在的呼叫者。

    實測反證（本輪動工前先自行複現，非引述）：在 `Show-NightlyStatus` 內
    `$info = $task | Get-ScheduledTaskInfo` 之後插一行裸表達式 `$info.LastTaskResult`
    → 真實 `-Status` 結束代碼由 1 退回 0（原缺陷復活），而本檔當時**全數綠燈**；補上
    本類後同一注入使本類翻紅（觀測值 `Object[]|1 True`／`Object[]|1 False`）。

    ## 為何斷言「型別」而不是斷言「沒有某種寫法」

    型別斷言封住的是**回傳值本身被污染**的路徑：不論退化路徑是 `Write-Output`、裸表達式、
    `$x` 單獨一行、還是哪個忘了 `| Out-Null` 的 cmdlet，結果都是回傳值不再是 Boolean。
    針對單一寫法的字面禁令是列舉法（永遠列不完），型別不變式則一次涵蓋整個方向。

    **但它不是「整個 success-stream 污染類別」——R58 round 2 QA-R58R2-04 實測證偽本處原文**：
    若污染發生在**被呼叫者**（`Test-TaskPowerSettings`），而其回傳值又被 `-not (…)` 之類
    布林運算吃掉，`Show-NightlyStatus` 的回傳型別**仍是 Boolean**（觀測值 `Boolean|True`、
    期望 `Boolean|False`）——那一類由本類的**值**斷言（五種輸入各自的期望 True/False）承擔。
    **型別斷言與值斷言缺一不可**，兩者合起來才覆蓋「回傳值被污染」與「回傳值正確但語意錯」
    兩個方向。另有第三個方向由靜態鎖承擔：**呼叫端那一行**若改成 `$loaded = Show-NightlyStatus
    | Out-String`，回傳型別在本類眼中完全正常（本類不執行呼叫端），見同檔對該行的整行錨定斷言。

    ## 隔離手法與安全性

    以同名 `function` 遮蔽 `Get-ScheduledTask`／`Get-ScheduledTaskInfo`（PowerShell 的
    命令解析優先序 Alias > Function > Cmdlet，故同名函式必然勝過模組 cmdlet），輸入改由
    `[pscustomobject]` 合成。因此：**不需要系統管理員權限、不讀不寫任何真實排程任務**，
    也不依賴 ScheduledTasks 模組存在 → 本類不必限定 Windows（比照同檔
    `TestStatusPowerSettingsFunctionBehaviour`，走 `powershell_exe()`，Windows 上優先
    出廠的 5.1＝使用者的目標引擎，DEF-101-507 判準）。

    ## 涵蓋面（三段式）

    **已實測涵蓋**：主任務缺席／主任務四項全對＋aux 缺席／主任務全對＋aux 全對／
    主任務單項漂移／aux 單項漂移，五種輸入下回傳型別皆為 Boolean 且值符期望；並以
    裸表達式注入實測本類會翻紅。
    **已實測不涵蓋**：「主任務缺席」那條走的是提早 `return $false`，注入點在其後，故該
    條在上述注入下**不會**翻紅——它鎖的是 DEF-101-248 的原始契約（任務不存在須為
    False），不是 stream 污染。翻紅責任由其餘四條承擔。
    **未窮舉**：其他 PowerShell host（ISE／遠端 session）與 pwsh 7 的 stream 語意差異
    未逐一量測（本機只有 PS 5.1）。
    """

    def _settings_literal(self, values: dict[str, bool]) -> str:
        return "; ".join(f"{k}=${str(v).lower()}" for k, v in values.items())

    def _synth_task(self, var_key: str, values: dict[str, bool]) -> str:
        return (
            f"$FakeTasks['{var_key}'] = [pscustomobject]@{{ State='Ready'; "
            f"Settings = [pscustomobject]@{{ {self._settings_literal(values)} }} }}"
        )

    def _invoke(
        self,
        main: dict[str, bool] | None,
        aux: dict[str, bool] | None = None,
    ) -> str:
        """執行腳本裡**真正那兩支**函式，回傳 `"<型別名>|<值>"`。

        main/aux 為 None 代表「該任務未註冊」（遮蔽後的 Get-ScheduledTask 回 $null）。
        """
        text = _read(_SCRIPT)
        # 連同依賴的 Test-TaskPowerSettings 一起抽（Show-NightlyStatus 會呼叫它）。
        fns = "\n".join(
            _extract_ps_function(text, name)
            for name in ("Test-TaskPowerSettings", "Show-NightlyStatus")
        )
        entries = []
        if main is not None:
            entries.append(self._synth_task(_FAKE_MAIN_TASK, main))
        if aux is not None:
            entries.append(self._synth_task(_FAKE_AUX_TASK, aux))
        payload = "\n".join(
            [
                # 鏡射腳本本體的偏好設定，讓 stream/錯誤語意與真跑一致。
                "$ErrorActionPreference = 'Stop'",
                "$FakeTasks = @{}",
                *entries,
                # [CmdletBinding()] 不可省：受測程式碼以 `-ErrorAction SilentlyContinue`
                # 呼叫，普通 function 不接受 common parameter，會拋
                # ParameterBindingException 而非走到我們要驗的路徑。
                "function Get-ScheduledTask { [CmdletBinding()] param([string]$TaskName)",
                "  if ($FakeTasks.ContainsKey($TaskName)) { return $FakeTasks[$TaskName] }",
                "  return $null }",
                # 受測程式碼以 pipeline 傳入（`$task | Get-ScheduledTaskInfo`），故遮蔽版
                # 必須宣告 ValueFromPipeline 並用 process 區塊。
                "function Get-ScheduledTaskInfo { [CmdletBinding()]",
                "  param([Parameter(ValueFromPipeline=$true)]$Task)",
                f"  process {{ [pscustomobject]@{{ LastRunTime='{_SENTINEL_LAST_RUN}';"
                " LastTaskResult=1; NextRunTime='SENTINEL-NextRunTime' } } }",
                f"$TaskName = '{_FAKE_MAIN_TASK}'",
                f"$AuxTaskNames = @('{_FAKE_AUX_TASK}')",
                fns,
                "$r = Show-NightlyStatus",
                # $null 也要能印出可讀 token（直接 .GetType() 會拋，讓失敗訊息變難懂）。
                "$t = if ($null -eq $r) { 'Null' } else { $r.GetType().Name }",
                'Write-Output "RESULT=$t|$r"',
            ]
        )
        exe = powershell_exe()
        assert exe is not None  # skipUnless 已保證
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", payload],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(
            proc.returncode, 0,
            f"Show-NightlyStatus 真機執行失敗：\n{proc.stdout}\n{proc.stderr}",
        )
        if main is not None:
            # 遮蔽是否真的生效的正向證據：報告必須印出我們合成的哨兵值。若哪天改成
            # 模組限定呼叫而讀到真實排程，這裡會少了哨兵 → 立刻顯形，不會假綠。
            self.assertIn(
                _SENTINEL_LAST_RUN, proc.stdout,
                "報告未出現合成哨兵值——Get-ScheduledTaskInfo 的遮蔽沒有生效，"
                f"本測試可能讀到了真實排程狀態：\n{proc.stdout}",
            )
        # 報告走 Write-Host，最後一行才是我們自己 Write-Output 的觀測結果。
        last = proc.stdout.strip().splitlines()[-1].strip()
        self.assertTrue(
            last.startswith("RESULT="),
            f"取不到觀測行（stdout 末行為 {last!r}）：\n{proc.stdout}",
        )
        return last[len("RESULT="):]

    _TYPE_FAILURE_HINT = (
        "回傳型別不是 Boolean，代表 Show-NightlyStatus 除了那個布林之外還往 success "
        "stream 寫了東西（Write-Output／裸表達式／`$x` 單獨一行／忘了 `| Out-Null` 的 "
        "cmdlet 皆會如此）。呼叫端 `$loaded = Show-NightlyStatus` 會把它們一起吃進去，"
        "$loaded 退化成元素數 ≥2 的 Object[]，PowerShell 一律判真 → `-Status` 恆 exit 0，"
        "「排程電源設定漂移」再度失去唯一會翻紅的路徑（2026-07-27 實測的原始缺陷）。"
    )

    def test_returns_boolean_true_when_main_ok_and_aux_absent(self) -> None:
        """乾淨機器／CI runner 的常態：aux 未註冊不算失敗，須回純 Boolean True。"""
        self.assertEqual(
            self._invoke(dict(_POWER_SETTINGS), aux=None),
            "Boolean|True", self._TYPE_FAILURE_HINT,
        )

    def test_returns_boolean_true_when_main_and_aux_both_ok(self) -> None:
        self.assertEqual(
            self._invoke(dict(_POWER_SETTINGS), aux=dict(_POWER_SETTINGS)),
            "Boolean|True", self._TYPE_FAILURE_HINT,
        )

    def test_returns_boolean_false_when_main_task_absent(self) -> None:
        """DEF-101-248 的原始契約：主任務不存在 → False → 呼叫端 exit 1。

        修復前實測為「印 0 bytes 且 exit 0」，本條是那條契約第一次被行為層鎖住。
        """
        self.assertEqual(
            self._invoke(None), "Boolean|False",
            "主任務不存在卻未回 False——DEF-101-248 宣稱的『-Status 依任務存在與否決定"
            "結束代碼』又回到了從未生效的狀態。" + self._TYPE_FAILURE_HINT,
        )

    def test_returns_boolean_false_when_main_task_drifts(self) -> None:
        """逐項翻轉主任務：任一項漂移都要回 False，且型別仍須是純 Boolean。"""
        for name, expected in _POWER_SETTINGS.items():
            with self.subTest(task="main", setting=name):
                values = dict(_POWER_SETTINGS)
                values[name] = not expected
                self.assertEqual(
                    self._invoke(values, aux=None), "Boolean|False",
                    f"主任務 {name} 漂移為 {values[name]} 卻未回 False。"
                    + self._TYPE_FAILURE_HINT,
                )

    def test_returns_boolean_false_when_aux_task_drifts(self) -> None:
        """aux 任務漂移也必須拉低整體判定——這正是真機事故的形態：主任務全對、
        AutoClaude_SD09_G0_GateCheck 的 StopIfGoingOnBatteries=True 漂移數週無訊號。"""
        for name, expected in _POWER_SETTINGS.items():
            with self.subTest(task="aux", setting=name):
                values = dict(_POWER_SETTINGS)
                values[name] = not expected
                self.assertEqual(
                    self._invoke(dict(_POWER_SETTINGS), aux=values), "Boolean|False",
                    f"aux 任務 {name} 漂移為 {values[name]} 卻未回 False——aux 只被印出"
                    f"而未納入判定，涵蓋面回到只驗主任務的原狀。" + self._TYPE_FAILURE_HINT,
                )


@unittest.skipUnless(
    platform.system() == "Windows",
    "[WINDOWS-NATIVE-ONLY] -Status 需要 ScheduledTasks 模組（Get-ScheduledTask）才能真跑，"
    "只在 Windows 上可驗（R43 DEF-101-348 標籤，供 run_root_unittests.py 彙整可見度）",
)
class TestStatusEndToEndExitCodeContract(unittest.TestCase):
    """端到端：真的以 `-Status` 跑整支腳本，斷言結束代碼契約在**整條路徑**上成立。

    與上一類的分工：上一類遮蔽了排程 API，鎖的是函式層的 stream 語意；本類完全不遮蔽，
    連 `param()` 解析、`if ($Status)` 分派、`$loaded = Show-NightlyStatus`、
    `if ($loaded) { exit 0 } else { exit 1 }` 這條真實接線一起驗——原缺陷「輸出 0 bytes
    且恆 exit 0」正是在這一層才觀測得到。`-Status` 唯讀（本機實測不需系統管理員權限、
    不改任何排程），故可安全真跑。

    🔴 **刻意不斷言結束代碼是某個特定值**：rc 取決於執行機器上排程任務的實際設定
    （本機實測 AutoClaude_SD09_G0_GateCheck 的 StopIfGoingOnBatteries 現為 True，故現況
    rc=1；乾淨機器主任務未安裝也是 rc=1；四項全對的機器則是 rc=0）。寫死任一值都會在
    別人機器上假紅。改為斷言四件與機器無關的不變式：
      ① rc ∈ {0,1}——排除未捕捉例外（PowerShell 未處理錯誤會是別的碼）與「恆 0」；
      ② stdout 非空——直接鎖住原缺陷「印 0 bytes」那一半；
      ③ rc==0 ⇒ stdout 必含 `(expected `——rc 0 的唯一成立途徑是主任務存在並印完四項
         電源設定比對，故「回報成功卻沒印過任何比對」在邏輯上不可能；
      ④ **報告自我一致**：腳本自己印出的每一行 `X = <實際>   (expected <期望>)` 若有任一
         行實際≠期望，rc 就必須是 1。這條把「腳本說了什麼」與「腳本的結束代碼」綁在一起，
         完全不依賴本機有哪些任務、設定如何——卻正是有牙齒的那條：本機現況（aux 漂移）
         下對裸表達式注入實測翻紅（觀測 rc 0 但報告印著 `StopIfGoingOnBatteries = True
         (expected False)`）。①②③ 在該注入下皆維持綠，因為報告仍照印、rc 仍在值域內
         ——三條都只鎖到缺陷的一半，第④條才鎖到「印了卻不算」這個本體。

    涵蓋面（三段式）**已實測涵蓋**：本機真 Windows 11 Pro／PS 5.1，主任務存在且 aux 漂移
    的現況（觀測 rc=1、stdout 非空、含 `(expected `、④ 抓到漂移並要求 rc=1）；並以裸表達式
    注入實測 ④ 會翻紅。**已實測不涵蓋**：rc==0 的分支（本機 aux 漂移中，無法在不改真實排程
    的前提下製造，刻意不改）；主任務缺席的機器（該情境 ④ 無比對行可解析，退化為只驗 ①②）。
    🔴 **④ 的鑑別力是機器相依的**：它靠「腳本印出的漂移」與「rc」互相矛盾來抓 stream 污染，
    所以在一台四項設定全對的乾淨機器上，同一個注入**不會**被本類抓到（沒有漂移行可矛盾）。
    本類因此**不是** stream 污染的主鎖——主鎖是機器無關的
    `TestShowNightlyStatusReturnsCleanBoolean`（合成輸入自帶漂移情境）；本類的定位是
    「真實接線＋真實排程狀態」這一維的第二道獨立訊號，不可拿來替代前者。
    **未窮舉**：其他 Windows 版本／語言環境。
    """

    # 腳本自印的比對行格式（Test-TaskPowerSettings 的 Write-Host）。刻意從**輸出**解析而非
    # 從原始碼推導期望值：這樣驗的是「腳本自己承認的期望」與「腳本自己的結束代碼」是否一致，
    # 不需要本測試另外維護一份期望值副本（那份副本一漂移就變成假綠）。
    _REPORT_LINE_RE = re.compile(
        r"^\s*(\w+)\s*=\s*(\S+)\s+\(expected\s+(\S+)\)\s*$", re.MULTILINE
    )

    def test_status_exit_code_and_output_are_machine_independent_invariants(self) -> None:
        exe = powershell_exe()
        self.assertIsNotNone(exe, "Windows 上必有 powershell 5.1——找不到代表環境異常")
        assert exe is not None
        proc = subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(_SCRIPT), "-Status"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_REPO_ROOT),
        )
        self.assertIn(
            proc.returncode, (0, 1),
            f"-Status 結束代碼 {proc.returncode} 不在契約值域 {{0,1}}——多半是未捕捉的 "
            f"PowerShell 例外，而非任何一種正常判定結果：\n{proc.stdout}\n{proc.stderr}",
        )
        self.assertTrue(
            proc.stdout.strip(),
            "-Status 一行輸出都沒有——這正是 2026-07-27 實測的原始缺陷（報告寫進 success "
            "stream，被 `$loaded = Show-NightlyStatus` 的變數指派整批吃掉）。"
            f"stderr：\n{proc.stderr}",
        )
        if proc.returncode == 0:
            self.assertIn(
                "(expected ", proc.stdout,
                "-Status 回報成功（exit 0）卻沒印出任何 `(expected ...)` 電源設定比對——"
                "exit 0 的唯一成立途徑是主任務存在並逐項比對過四項設定，故此組合代表"
                "結束代碼與實際檢查脫鉤（原缺陷形態：恆 exit 0 且輸出 0 bytes）："
                f"\n{proc.stdout}",
            )

        drifted = [
            f"{name} = {actual}（expected {expected}）"
            for name, actual, expected in self._REPORT_LINE_RE.findall(proc.stdout)
            if actual.lower() != expected.lower()
        ]
        if drifted:
            self.assertEqual(
                proc.returncode, 1,
                "-Status 自己印出了與期望不符的設定，結束代碼卻不是 1——「印了卻不算」，"
                "正是 2026-07-27 實測的原始缺陷本體（報告照印、結束代碼恆 0，於是漂移"
                f"在全 repo 沒有任何會翻紅的路徑）。實際不符：{drifted}\n{proc.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
