#!/usr/bin/env python3
"""tools/install_windows_nightly.ps1 結構驗證（R19 修復包 D）。

沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈模組背景與靜態驗證的設計取捨〉。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import io
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ps_engine import production_engine  # noqa: E402  # R60 E-A-03：引擎述詞 SSOT

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
_FIX_CATCHUP = _REPO_ROOT / "AutoClaude" / "tools" / "fix_nightly_catchup.ps1"
_NIGHTLY_PS1 = _REPO_ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
# R60（DEF-101-517 backlog 收斂）：安裝器新增註冊的第二支任務所指向的載體。
# 路徑已在兩平台 compat-CI 的 paths 覆蓋範圍內（windows 側由 `**/*.ps1` 兜底、
# macos 側已顯式列舉），故本檔新增消費不需動 CI paths（DEF-101-042 同構檢查）。
_SMOKE_PS1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"


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

    def test_smoke_task_is_registered_alongside_nightly(self) -> None:
        """DEF-101-517 R60 收斂（backlog 解鎖條件的路徑①）：本安裝器須同時註冊
        `windows_smoke_local.ps1` 的獨立排程任務。

        WHY：`windows_smoke_local.ps1` 是 DEF-101-139 為「雲端 CI 帳務停擺
        （DEF-101-081）」而建的 Windows 側**執行級補償控制**，而 R59 逐項實測確認
        `run_local_nightly.ps1` 對它零呼叫 ⇒ 補償控制自己沒有心跳，只能手動觸發
        （也解釋了它為何腐化到讓 R59 踩到 DEF-101-511）。mac 側對照：
        `run_local_nightly.sh` 的 [1/4] 每日自動跑 `macos_smoke_local.sh`。
        刻意走「獨立 schtasks 任務」而非「run_local_nightly.ps1 第 8 個 stage」：後者
        需同動 summary 行／summary JSON／exit-decision／Format-Rc 四處，而 summary 行
        被 `tools/dev_start.py` 心跳哨兵以跨檔字面正則解析（DEF-101-263②）。
        """
        self.assertIn("$SmokeTaskName = 'AutoClaude_WindowsSmoke'", self.text)
        self.assertIn(
            "$SmokePs1 = Join-Path $RepoRoot 'tools\\windows_smoke_local.ps1'", self.text,
            "smoke 任務的載體路徑須由 $RepoRoot 動態組出（不得寫死絕對路徑）",
        )
        self.assertTrue(
            _SMOKE_PS1.is_file(),
            f"{_SMOKE_PS1} 不存在——安裝器會註冊一個指向不存在腳本的排程任務",
        )
        self.assertIn(
            '-Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File '
            '`"${SmokePs1}`""', self.text,
            "smoke 任務的 Action 須以原生 powershell.exe -File 呼叫（DEF-101-511："
            "該腳本偵測到 $env:MSYSTEM 即拒跑，故不得經由任何 bash 包裝層觸發）；"
            "且須帶 -WindowStyle Hidden（R84 訴求 7／B2 的第二層防彈窗——"
            "第一層 LogonType=S4U 實測會漂成 InteractiveToken，見 "
            "tools/scheduled_task_expectations.json 的 _why）",
        )
        # 兩支任務各自有自己的 ShouldProcess 守衛（否則 -WhatIf 只攔得住其中一支）。
        self.assertEqual(
            self.text.count("$PSCmdlet.ShouldProcess($TaskName, 'Register-ScheduledTask')"), 1,
        )
        self.assertEqual(
            self.text.count("$PSCmdlet.ShouldProcess($SmokeTaskName, 'Register-ScheduledTask')"), 1,
        )
        # 解除安裝與狀態查詢都必須覆蓋整組（只做一半＝殘留孤兒任務／狀態誤報）。
        self.assertIn("foreach ($name in @($TaskName, $SmokeTaskName))", self.text)
        self.assertIn("Show-TaskDetail -Name $SmokeTaskName", self.text)

    def test_smoke_task_shares_catchup_settings_and_runs_before_nightly(self) -> None:
        """smoke 任務必須共用同一份補跑保護 $settings，且排在 nightly 之前。

        共用 $settings 的 WHY：四項補跑保護（睡眠喚醒／關機補跑／電池不擋不砍）對
        smoke 的必要性與 nightly 完全相同（同一個「筆電夜間睡眠」漏跑成因），另立
        一份就是第二個會漂移的站點（DEF-101-249 的教訓正是這類重複）。
        時間順序的 WHY：smoke 是數分鐘量級的便宜 tripwire、nightly 是含 mutation 的
        小時量級深度回歸；機器當晚只醒著一小段時間時，先跑完便宜那支才有意義。
        """
        text = self.text
        self.assertRegex(
            text,
            r"Register-ScheduledTask -TaskName \$SmokeTaskName[\s\S]{0,200}?-Settings \$settings",
            "smoke 任務未套用 $settings——四項補跑保護只有 nightly 拿到，"
            "smoke 在睡眠/關機/電池情境下會靜默漏跑",
        )
        # 🔴 R73（DEF-101-779）：時刻已從寫死字面值改為 param 預設值（理由見該 param
        # 區塊 WHY——原本寫死在程式碼裡的時刻與本機實況不符（R73 實測），使「跑安裝器
        # 套設定」會靜默改時間，導致 ADR-SD09-012 點名的五項設定連兩輪沒人敢套）。
        # 本鎖守的不變量**不變**：兩個 trigger 都必須吃參數，且**預設值**仍須滿足
        # 「smoke 早於 nightly」。改讀 param 預設值即可繼續守住順序，不必弱化斷言。
        self.assertIn("-Daily -At $SmokeAt", text,
                      "smoke trigger 必須吃 $SmokeAt 參數，不得寫死時間字面值")
        self.assertIn("-Daily -At $NightlyAt", text,
                      "nightly trigger 必須吃 $NightlyAt 參數，不得寫死時間字面值")
        defaults = {}
        for name in ("NightlyAt", "SmokeAt"):
            m = re.search(rf"\[string\]\${name} = '(\d{{2}}:\d{{2}})'", text)
            self.assertIsNotNone(m, f"找不到 ${name} 的 param 預設值——結構已變動")
            defaults[name] = m.group(1)
        self.assertLess(
            defaults["SmokeAt"], defaults["NightlyAt"],
            f"smoke 預設時刻 {defaults['SmokeAt']} 必須早於 nightly "
            f"{defaults['NightlyAt']}（便宜的 tripwire 先跑；WHY 見本測試 docstring）。"
            "🔴 這條不變量與本機現行排程（smoke 23:30 晚於 nightly 22:30）相反——"
            "R73 選擇讓預設值站在鎖這一邊，見 install_windows_nightly.ps1 param 區塊。",
        )

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

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈DEF-101-249 兩支腳本參數名極性相反的沿革〉。
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
        # 🔴 R84：本檔的 Action 在 `-NoProfile` 與 `-ExecutionPolicy` 之間插入了
        # `-WindowStyle Hidden`（訴求 7／B1-B2 的第二層防彈窗）⇒ 慣例字串**不再是
        # 一段連續子字串**。逐字比對整段會把「補上防彈窗旗標」判成違規，故改為
        # 逐旗標判在場：慣例要釘的是「用哪些旗標」，不是「它們中間不准插東西」。
        for _flag in ("-NoProfile", "-ExecutionPolicy Bypass", "-File"):
            self.assertIn(_flag, self.text)
        self.assertIn("-WindowStyle Hidden", self.text)
        self.assertIn("run_local_nightly.ps1", self.text)
        self.assertIn("-Daily", self.text)
        # 🔴 R73（DEF-101-779）：原本斷言 help 區塊含某個時刻字面值，即把觸發時間**釘進鎖裡**
        # 釘進鎖裡。那個字面值與本機實際排程（22:30）不符，而 install 路徑是
        # Unregister→Register ⇒ 「跑安裝器套設定」會靜默把時間改掉，於是 ADR-SD09-012
        # 點名的五項排程設定連兩輪沒人敢套。時間改為參數後，鎖要釘的是**結構**：
        # 兩個 trigger 都必須吃參數（不得再回頭寫死），且參數都要有格式驗證。
        # 刻意**不**斷言預設值等於本機現行排程——那會把「這台機器排幾點」寫成鎖的常數，
        # 正是 DEF-101-777 同一個病（見 test_ps_engine_ssot.py::TestNoStaleLocalEngineClaims）。
        self.assertIn("-Daily -At $NightlyAt", self.text,
                      "nightly trigger 必須吃 $NightlyAt 參數，不得寫死時間字面值")
        self.assertIn("-Daily -At $SmokeAt", self.text,
                      "smoke trigger 必須吃 $SmokeAt 參數，不得寫死時間字面值")
        # 逐個參數檢查「宣告行的前一行是 ValidatePattern」。刻意不用單一 regex 把
        # ValidatePattern 的內容一起吃進去——那個 pattern 自己含 `(` `)`，`[^)]*`
        # 會提早收尾而假紅（本輪第一版就是這樣寫的，實測不命中）。
        lines = self.text.splitlines()
        for p in ("$NightlyAt", "$SmokeAt"):
            want = f"[string]{p}"
            idx = next(
                (i for i, ln in enumerate(lines) if ln.strip().startswith(want)), None
            )
            self.assertIsNotNone(idx, f"找不到 {p} 的 [string] 宣告行——結構已變動")
            self.assertIn(
                "[ValidatePattern(", lines[idx - 1],
                f"{p} 宣告行的前一行必須是 ValidatePattern——非法時間若放行，"
                "Register-ScheduledTask 會拋難懂的例外，或更糟："
                "建出一個時間錯誤但看起來成功的排程",
            )

    def test_help_block_contains_no_hardcoded_clock_time(self) -> None:
        """🔴 R73 二審（DEF-101-781）：`<# … #>` help 區塊不得出現任何 `HH:mm` 字面值。

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_help_block_contains_no_hardcoded_clock_time 意圖〉。
        """
        # `<#` 不在檔案第一行（第 1 行是 `#Requires -Version 5.1`），故不加 `^` 錨點。
        m = re.search(r"(?s)<#(.*?)#>", self.text)
        self.assertIsNotNone(m, "找不到 `<# … #>` help 區塊——結構已變動")
        help_block = m.group(1)
        hits = re.findall(r"\b([01]?\d|2[0-3]):[0-5]\d\b", help_block)
        self.assertEqual(
            hits, [],
            f"help 區塊出現時刻字面值 {hits}——預設值請只寫在 param 區塊（那裡有取捨 WHY），"
            "現行排程請叫讀者現查 `Get-ScheduledTask ... | Get-ScheduledTaskInfo`。"
            "寫在說明裡的時刻會過期，而過期的說明會誘發破壞性操作（DEF-101-781）",
        )

    def test_smoke_after_nightly_has_a_runtime_guard(self) -> None:
        """🔴 R73 二審（DEF-101-782）：順序不變量必須在 runtime 也被守住。

        意圖（Rule 9）：參數化**之前**，「smoke 早於 nightly」是由寫死的字面值**由構造
        保證**的；參數化之後，它只剩一條靜態鎖在看 param 預設值，而真實安裝路徑
        （使用者顯式傳參）無人看管——SD 二審實測 `-WhatIf -SmokeAt 23:30 -NightlyAt 22:30`
        → **rc=0、零警告**。更糟的是本檔自己有兩處在建議 `-SmokeAt 23:30`。
        把不變量降級成「只有預設值遵守」是把它變成裝飾品。
        """
        self.assertIn(
            "$AllowSmokeAfterNightly", self.text,
            "缺少顯式旁路開關——要違反不變量可以，但必須說出口，不能靜默通過",
        )
        self.assertRegex(
            self.text, r"if \(-not \$AllowSmokeAfterNightly -and \(\$SmokeAt -ge \$NightlyAt\)\)",
            "缺少 runtime 順序守門：顯式傳參違反「smoke 早於 nightly」時必須 fail-loud",
        )
        guard_at = self.text.index("-not $AllowSmokeAfterNightly")
        guard_block = self.text[guard_at:self.text.index("\n}", guard_at)]
        self.assertIn(
            "exit 1", guard_block,
            "順序守門必須 exit 1，不可只印警告——只印警告在排程／CI 情境下等於沒有",
        )

    def test_admin_elevation_check_present(self) -> None:
        """install/uninstall 需要 Register/Unregister-ScheduledTask 的系統管理員權限
        （比照既有 fix_nightly_catchup.ps1 慣例；R76 訂正：原文並列的
        reschedule_g0_gatecheck.ps1 已整支刪除，不再是可引用的先例），
        非管理員身分須 fail-loud 提示，而非讓 Register-ScheduledTask 自己拋出難懂的例外。"""
        self.assertIn("WindowsBuiltInRole]::Administrator", self.text)

    def test_status_exit_code_reflects_task_existence(self) -> None:
        """DEF-101-248（R20 Scan-A）：-Status 先前不論任務存不存在恆 exit 0，與 mac 版
        `install_mac_nightly.sh --status`（任務未載入時非零結束代碼）語意不對等，任何
        想拿結束代碼做自動化判斷（CI／監控腳本）在 Windows 上會拿到假陽性。修復後須
        依實際存在性決定 exit 0/1，而非寫死 exit 0。

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_status_exit_code_reflects_task_existence R60 DEF-101-542 訂正〉。
        """
        status_block_match = re.search(
            r"if \(\$Status\) \{(.*?)\n\}", self.text, re.DOTALL,
        )
        self.assertIsNotNone(status_block_match, "找不到 -Status 處理區塊——結構已變動")
        status_block = status_block_match.group(1)
        self.assertNotIn(
            "exit 0\n", status_block,
            "-Status 區塊不得再寫死 exit 0——須依實際存在性決定結束代碼",
        )
        self.assertIn(
            "$loaded = (Test-TaskPresent -Name $TaskName) -and "
            "(Test-TaskPresent -Name $SmokeTaskName)", status_block,
            "存在性判定必須走零輸出的純查詢函式，且必須涵蓋整組任務（DEF-101-542）",
        )
        self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", status_block)
        # 結構層反向守門：印報表的函式不得回傳值（否則 DEF-101-542 立刻復發）。
        printer = re.search(
            r"function Show-TaskDetail \{(.*?)\n\}", self.text, re.DOTALL,
        )
        self.assertIsNotNone(printer, "找不到 Show-TaskDetail 函式——結構已變動")
        self.assertNotRegex(
            printer.group(1), r"return\s+\$(true|false)\b",
            "Show-TaskDetail 不得 `return $true/$false`——它同時 Write-Output，"
            "回傳值會被輸出串污染成 Object[]（DEF-101-542 復發）",
        )

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

    def test_uninstall_branch_does_not_depend_on_carrier_script_existence(self) -> None:
        """DEF-101-619（R66 真機重現）：修復前 `$NightlyPs1` 的 `Test-Path` 存在性檢查
        放在 `if ($Uninstall)` 判斷「之前」，對 install／-Uninstall 兩路共用——nightly
        載體被刪掉（或腳本尚未 checkout 完整）時，連 `-Uninstall`（單純操作 Task
        Scheduler、理論上不需要讀取任何載體檔案）都會被擋下（scratchpad 隔離重現：
        REAL_EXITCODE=1），與 mac 側 `install_mac_nightly.sh` 的 `cmd_uninstall()`
        （完全不檢查底層腳本是否存在）行為不對稱。

        沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
        〈test_uninstall_branch_does_not_depend_on_carrier_script_existence 結構不變量與錨點修訂〉。
        """
        uninstall_block_match = re.search(
            r"^if \(\$Uninstall\) \{"
            r"(.*?foreach \(\$name in @\(\$TaskName, \$SmokeTaskName\)\).*?)"
            r"\n\}",
            self.text, re.DOTALL | re.MULTILINE,
        )
        self.assertIsNotNone(
            uninstall_block_match,
            "找不到含 foreach 迴圈的真正 -Uninstall 處理區塊——結構已變動",
        )
        uninstall_block = uninstall_block_match.group(1)
        self.assertNotIn(
            "Test-Path -LiteralPath $NightlyPs1", uninstall_block,
            "-Uninstall 區塊不得依賴 $NightlyPs1 是否存在——解除安裝理應比安裝更寬容"
            "（DEF-101-619：載體被刪掉時 -Uninstall 也會被誤擋）",
        )
        self.assertNotIn(
            "Test-Path -LiteralPath $SmokePs1", uninstall_block,
            "-Uninstall 區塊不得依賴 $SmokePs1 是否存在——同 DEF-101-619 理由",
        )
        nightly_check_pos = self.text.find("Test-Path -LiteralPath $NightlyPs1")
        smoke_check_pos = self.text.find("Test-Path -LiteralPath $SmokePs1")
        self.assertGreater(
            nightly_check_pos, uninstall_block_match.end(),
            "$NightlyPs1 存在性檢查必須排在 -Uninstall 區塊之後（收斂進 install-only "
            "段落），而非排在其前面（那會使兩路共用同一道守門，回歸 DEF-101-619）",
        )
        self.assertGreater(
            smoke_check_pos, uninstall_block_match.end(),
            "$SmokePs1 存在性檢查必須排在 -Uninstall 區塊之後（同上理由）",
        )


# R59 DEF-101-509：本條件原為 `shutil.which("pwsh")`（**只認 PS 7**）。判例史
# （標準 Win11 開發機必 skip、零活體覆蓋、為何改 `powershell or pwsh` 更貼近生產）
# 全文搬至 docs/06_quality/CrossPlatform_Guard_Line_History.md
# 〈DEF-101-509 pwsh→5.1 判例史〉節。5.1 的 parser 才是真正的目標文法（生產以
# `powershell -ExecutionPolicy Bypass -File` 執行＝5.1），故以 5.1 優先解析。
def _ps_engine() -> str | None:
    """回傳本機可用的 PowerShell 解析引擎路徑，Windows 上優先 5.1（見上方 WHY）。

    抽成模組層函式而非寫在測試裡，是為了讓下方 `TestSyntaxGateEngineSelection`
    能對「選誰」這件事本身做斷言——選擇邏輯若退回 pwsh-only，鎖才抓得到。

    R60 Scan-E E-A-03：判定本體收斂進 `_ps_engine.production_engine()`（同一份
    優先序 SSOT，供全 `tools/tests` 共用）——本輪掃描實查同樹另有 5 個檔案在寫
    同一件事、其中一處還是 **pwsh 優先**（與本檔上方 DEF-101-509 判準方向相反）。
    本函式保留為就地別名：下方兩支鎖與其他呼叫端逐字不動（Rule 3）。
    """
    return production_engine()


@unittest.skipUnless(
    _ps_engine(),
    "本機無 powershell/pwsh，跳過語法解析（純結構文字驗證仍會跑）",
)
class TestInstallWindowsNightlySyntax(unittest.TestCase):
    def test_parses_with_zero_errors(self) -> None:
        """[Parser]::ParseFile 只做語法樹解析，不執行——跨平台安全（macOS/Linux pwsh
        皆可跑），可及早攔住語法錯誤而不需要真的呼叫 Windows-only 的排程 API。

        引擎選擇 `powershell or pwsh`（Windows 上優先 5.1）的理由見類別上方註解。
        """
        exe = _ps_engine()
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


class TestSyntaxGateEngineSelection(unittest.TestCase):
    """DEF-101-509 回歸鎖：語法解析閘門在**標準 Windows 11** 上必須真的跑。

    鑑別力來源＝直接斷言 `TestInstallWindowsNightlySyntax` 的 `skipUnless` 判定結果
    （unittest 在條件為假時於類別上設 `__unittest_skip__ = True`），而非比對條件的
    文字。故任何「退回只認 pwsh」的改法（含改寫成別的等價寫法）在一台沒裝 pwsh 7 的
    Windows 機器上都會讓本鎖翻紅；R59 落地當下即以此機器實測（`which('pwsh') is None`、
    `which('powershell')` 命中內建 5.1）確認有鑑別力。
    """

    @unittest.skipUnless(
        platform.system() == "Windows",
        "[WINDOWS-NATIVE-ONLY] 本鎖驗的性質是「Windows 上不得 skip」，"
        "非 Windows 平台上該 skip 本身是正確行為（R43 DEF-101-348 標籤，"
        "供 run_root_unittests.py 彙整可見度）",
    )
    def test_syntax_gate_is_not_skipped_on_windows(self) -> None:
        # Windows 一律內建 Windows PowerShell 5.1；選擇器只要仍接受它就不會是 None。
        self.assertIsNotNone(
            shutil.which("powershell"),
            "Windows 上找不到內建 powershell.exe——環境異常，非本鎖要抓的迴歸",
        )
        self.assertFalse(
            getattr(TestInstallWindowsNightlySyntax, "__unittest_skip__", False),
            "TestInstallWindowsNightlySyntax 在 Windows 上被 skip 了——語法閘門對一支"
            "Windows 專屬腳本失效（DEF-101-509 迴歸；很可能是把 _ps_engine() 改回"
            "只認 pwsh）",
        )

    def test_engine_selection_prefers_windows_powershell(self) -> None:
        """兩者都在時必須選 5.1：生產是以 `powershell -File` 執行本腳本，且 `tools/`
        受 test_ps51_compat.py 的 PS 5.1 相容政策約束——用 PS 7 文法解析會漏掉
        「5.1 解析不過、7 解析得過」的寫法（CI 的 pwsh parser 是 7，本來就驗不到）。

        R60 E-A-03：本鎖刻意**保留行內 `shutil.which`**、不改走 `_ps_engine` SSOT
        ——它是這條判準的獨立 ground truth；若兩邊都用同一顆述詞算 expected，
        優先序寫反時兩邊會一起寫反、斷言恆綠＝鎖失去鑑別力。`test_ps_engine_ssot.py`
        的反增生掃描已就此列具名永久豁免（附本 WHY）。
        🔴 **R73 訂正（DEF-101-777）**：這裡原本斷言「這台機器缺 pwsh 7，於是 `expected`
        恆等於 5.1 路徑、走不到『兩者皆有』那條分支」——把撰寫當時的機器屬性寫成了常數。
        2026-08-04 實測該機器已同時具備兩個引擎（`available_engines()` 回
        `{'powershell': …\\WindowsPowerShell\\v1.0\\powershell.EXE,
        'pwsh': …\\WindowsApps\\Microsoft.PowerShell_7.6.4.0_x64__…\\pwsh.EXE}`，
        兩者皆為真實執行檔、非 0 byte 佔位版），**該分支現在每次都走得到，且本斷言通過**
        ⇒ 這條判準在此機器上首次獲得真實鑑別力。引擎可用性是**機器屬性**：這裡不再寫
        任何「這台機器有／沒有什麼」的斷言，要知道就現查 `available_engines()`。
        不依賴機器的方向驗證仍由 `test_ps_engine_ssot.py` 以合成 `shutil.which` 的
        雙引擎情境保證（那才是在**任何**機器上都測得到方向的做法）。"""
        ps51, ps7 = shutil.which("powershell"), shutil.which("pwsh")
        if ps51 is None and ps7 is None:
            self.skipTest("本機無任何 PowerShell 引擎")
        expected = ps51 or ps7
        self.assertEqual(
            _ps_engine(), expected,
            "引擎選擇順序錯誤：兩者皆有時必須優先 Windows PowerShell 5.1",
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


@unittest.skipUnless(
    platform.system() == "Windows",
    "[WINDOWS-NATIVE-ONLY] 本組鎖真的執行安裝器（-Status / -WhatIf），需 Windows 的 "
    "ScheduledTasks 模組（R43 DEF-101-348 標籤，供 run_root_unittests.py 彙整可見度）",
)
class TestStatusExitCodeRuntime(unittest.TestCase):
    """DEF-101-542 回歸鎖：`-Status` 的結束代碼必須**真的**反映任務存在性。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈TestStatusExitCodeRuntime 為何要用執行而非字面比對〉。
    """

    _ABSENT_NIGHTLY = "AutoClaude_Nightly_R60AbsentProbe"
    _ABSENT_SMOKE = "AutoClaude_WindowsSmoke_R60AbsentProbe"

    def _script_with_absent_task_names(self, tmpdir: str) -> Path:
        text = _read(_SCRIPT)
        patched, n1 = re.subn(
            r"\$TaskName = 'AutoClaude_Nightly'",
            f"$TaskName = '{self._ABSENT_NIGHTLY}'", text,
        )
        patched, n2 = re.subn(
            r"\$SmokeTaskName = 'AutoClaude_WindowsSmoke'",
            f"$SmokeTaskName = '{self._ABSENT_SMOKE}'", patched,
        )
        self.assertEqual(
            (n1, n2), (1, 1),
            "任務名賦值的字面樣式已變動——本鎖無法改寫成「保證不存在」的名字，"
            "請同步更新本測試的改寫式（不得靜默降級成不改寫，那會變成對真任務查詢）",
        )
        target = Path(tmpdir) / "install_windows_nightly_absentprobe.ps1"
        # BOM + CRLF 比照 repo .ps1 政策（.gitattributes / DEF-101-002）；此檔在 temp、
        # 不入庫，但保持一致可排除「編碼差異造成的行為差異」這個混淆變因。
        target.write_bytes(b"\xef\xbb\xbf" + patched.replace("\n", "\r\n").encode("utf-8"))
        return target

    def _run(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        # 🔴 主控台碼頁：`powershell.exe` 以 OEM 碼頁（本機 zh-TW＝cp950）寫 stdout，
        # 以 utf-8 解碼中文訊息必得亂碼。故下方斷言一律只認 **ASCII 標記**（任務名、
        # 安裝提示字串），不比對中文——不是偷懶，是不讓本鎖的成敗取決於執行者的
        # 主控台碼頁（同 windows_smoke_local.ps1 [6] 「直讀位元組、不經主控台解碼」
        # 的既有取證紀律）。
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(script), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def _task_presence(self, names: tuple[str, ...]) -> str:
        """回傳 `name=0/1;...` 的 ASCII 快照（0＝不存在、1＝存在），唯讀查詢。"""
        name_list = ",".join(f"'{n}'" for n in names)
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"$o = @(); foreach ($n in @({name_list})) {{ "
             "$t = Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue; "
             'if ($t) { $o += "$n=1" } else { $o += "$n=0" } }; '
             'Write-Output ($o -join ";")'],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(proc.returncode, 0, f"排程存在性查詢失敗：{proc.stderr}")
        return proc.stdout.strip()

    @staticmethod
    def _declared_task_names() -> tuple[str, ...]:
        """從腳本原始碼抽出它實際會註冊的任務名（不在測試裡複製第二份字面清單）。"""
        text = _read(_SCRIPT)
        names = re.findall(r"\$(?:Smoke)?TaskName = '([^']+)'", text)
        return tuple(names)

    def test_status_exits_nonzero_when_tasks_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script = self._script_with_absent_task_names(tmpdir)
            proc = self._run(script, "-Status")
        self.assertEqual(
            proc.returncode, 1,
            "-Status 對「兩支任務都不存在」回了非 1 的結束代碼——任何拿 exit code 做"
            "自動化判斷的 CI／監控腳本都會拿到假陽性（DEF-101-248 原始缺陷、"
            f"DEF-101-542 復發形態）。stdout=\n{proc.stdout}\nstderr=\n{proc.stderr}",
        )
        # 反向確認 rc=1 真的來自存在性判定、而不是腳本在別處炸掉：缺席分支印出的
        # 那一行必須同時含「任務名」與「安裝提示」兩個 ASCII 標記（present 分支印的
        # 是 LastRunTime/NextRunTime，不含安裝提示，故兩者可區分）。
        for name in (self._ABSENT_NIGHTLY, self._ABSENT_SMOKE):
            hit = [
                ln for ln in proc.stdout.splitlines()
                if name in ln and r"powershell -File tools\install_windows_nightly.ps1" in ln
            ]
            self.assertEqual(
                len(hit), 1,
                f"-Status 報表沒有恰一行是 {name} 的「不存在」分支輸出——rc=1 可能"
                f"來自無關的錯誤路徑。stdout=\n{proc.stdout}",
            )

    def test_uninstall_whatif_succeeds_when_carrier_scripts_are_unreachable(self) -> None:
        """DEF-101-619 回歸鎖：`-Uninstall` 不得依賴 nightly／smoke 載體腳本存在。

        刻意沿用 `_script_with_absent_task_names` 產生的**改名複本**（複本落在
        temp，其 `$RepoRoot` 算出來的 `$NightlyPs1`／`$SmokePs1` 絕對路徑在該複本
        所在目錄下必然不存在——`test_whatif_previews_every_task_without_touching_scheduler`
        docstring 已記載這個既有事實：install 模式的 `-WhatIf` 在這種複本下會在
        載體存在性檢查就 `exit 1`，R60 實測）。修復前若同一道 `Test-Path` 守門
        也擋 `-Uninstall`，本測試會在修復前以 rc=1 重現 DEF-101-619；修復後
        `-Uninstall -WhatIf` 完全不觸碰 `Test-Path`，應正常預覽並以 rc=0 結束——
        不需要、也不應該要求兩支載體真的存在（解除安裝理應比安裝更寬容）。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            script = self._script_with_absent_task_names(tmpdir)
            proc = self._run(script, "-Uninstall", "-WhatIf")
        self.assertEqual(
            proc.returncode, 0,
            "-Uninstall -WhatIf 在複本目錄下（nightly/smoke 載體路徑必然不存在）"
            "未能成功預覽——DEF-101-619 回歸：-Uninstall 又被載體存在性檢查誤擋。"
            f"stdout=\n{proc.stdout}\nstderr=\n{proc.stderr}",
        )
        for name in (self._ABSENT_NIGHTLY, self._ABSENT_SMOKE):
            self.assertIn(
                f'"{name}"', proc.stdout,
                f"-Uninstall -WhatIf 預覽輸出未涵蓋 {name}——ShouldProcess 守衛可能"
                f"未包住其中一支任務。stdout=\n{proc.stdout}",
            )

    def test_whatif_previews_every_task_without_touching_scheduler(self) -> None:
        """`-WhatIf` 是 DEF-101-517 解鎖條件明文點出的「不必等排定時刻就能取得驗證
        證據」那條路——本鎖把它變成每輪自動跑的證據，而不是靠人記得手動跑一次。

        刻意跑**真腳本**（非改名複本）：複本的 `$PSScriptRoot` 落在 temp，算出的
        `$RepoRoot` 是錯的，`-WhatIf` 會在 nightly 載體存在性檢查就 exit 1（R60 實測）。
        副作用檢查改用「執行前後的排程存在性快照必須完全相同」——這比「檢查某支任務
        不存在」更可靠：不論本機目前裝了哪幾支，都能抓到 `-WhatIf` 真的動了系統。
        """
        names = self._declared_task_names()
        self.assertGreaterEqual(
            len(names), 2,
            f"只抽到 {names} 個任務名——安裝器應管理 nightly ＋ Windows smoke 兩支"
            "（DEF-101-517），抽取式或腳本結構已變動",
        )
        before = self._task_presence(names)
        proc = self._run(_SCRIPT, "-WhatIf")
        after = self._task_presence(names)
        self.assertEqual(
            proc.returncode, 0, f"-WhatIf 預覽失敗：\n{proc.stdout}\n{proc.stderr}",
        )
        for name in names:
            self.assertIn(
                name, proc.stdout,
                f"-WhatIf 預覽未涵蓋 {name}——ShouldProcess 守衛可能只包住其中一支"
                f"（沒被包住的那支會在 -WhatIf 下真的動 Task Scheduler）。"
                f"stdout=\n{proc.stdout}",
            )
        self.assertEqual(
            before, after,
            "-WhatIf 前後的排程存在性快照不同 ⇒ -WhatIf 真的變更了 Task Scheduler"
            f"（before={before} after={after}）",
        )


class TestUnattendedExecutionHardening(unittest.TestCase):
    """R69（S-5）：讓「重跑 installer」不再是回歸源。

    2026-08-01/02 真機事故的三個直接成因，全都能被「有人跑一次 installer」重新種回去
    （install 路徑是「存在就 Unregister 再 Register」，每跑一次就重置一次）：
      (1) 不帶 -Principal → 套預設 Interactive → 使用者未登入就整輪不跑
          （實測 AutoClaude_WindowsSmoke：事件 332、NumberOfMissedRuns=1）
      (2) 不帶 -ExecutionTimeLimit → 預設 PT72H → 被睡眠凍住 35.6 小時的實例仍在
          額度內存活，隔日 02:00 觸發被擋掉（事件 322）
      (3) MultipleInstances 預設 IgnoreNew → 同上，新觸發直接被丟棄
    """

    def setUp(self) -> None:
        self.text = _read(_SCRIPT)
        self.code = self._code_only(self.text)

    @staticmethod
    def _code_only(text: str) -> str:
        """去掉 `<# ... #>` 說明區塊與 `#` 行註解，只留可執行碼。

        WHY 必要：本檔註解密度極高（動輒數十行 WHY），註解裡會提到 cmdlet 名稱、
        也會示範「錯誤寫法」。若直接對全檔做字面掃描：
          - 正向計數會把 .PARAMETER／.NOTES 裡提到的 Register-ScheduledTask 算進去
            （實測 2 處真呼叫被算成 6）；
          - 反向鎖會被自己註解裡的反例觸發（本輪實際踩到）。
        兩者都是「鎖打到註解」而非打到行為，屬假紅。
        """
        text = re.sub(r"(?s)<#.*?#>", "", text)
        return "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        )

    def test_principal_is_s4u_and_applied_to_both_tasks(self) -> None:
        """(1) 兩支任務都必須顯式帶 S4U principal。

        意圖（Rule 9）：S4U＝以該使用者身分執行但不需其登入。少了它，nightly 只在
        「剛好有人登入著」時才跑——而 nightly 的整個存在理由就是無人值守。
        """
        self.assertRegex(
            self.text,
            r"\$principal\s*=\s*New-ScheduledTaskPrincipal[\s\S]{0,200}?-LogonType\s+S4U",
            "必須建立 -LogonType S4U 的 principal（Interactive 在未登入時整輪不跑）",
        )
        # 反引號續行必須整段抓進來，否則 -Principal 落在第二行會被漏看（假綠）。
        # 寫法注意：`[^\r\n]*` 放前面會貪婪吃掉續行的反引號且不回溯，故把「以反引號
        # 結尾的整行」設成重複單元，最後再收一行。
        registers = re.findall(
            r"(?m)^[ \t]*Register-ScheduledTask(?:[^\r\n]*`[ \t]*\r?\n)*[^\r\n]*",
            self.code,
        )
        self.assertEqual(
            len(registers), 2,
            f"預期恰好 2 處 Register-ScheduledTask（nightly + smoke），實得 {len(registers)}",
        )
        for i, reg in enumerate(registers):
            self.assertIn(
                "-Principal $principal", reg,
                f"第 {i + 1} 處 Register-ScheduledTask 未帶 -Principal $principal——"
                "會套用預設 Interactive，等於每跑一次 installer 就把 S4U 降級一次",
            )

    def test_execution_time_limit_is_bounded(self) -> None:
        """(2) 必須帶 ExecutionTimeLimit，且不得回到 72 小時等級。

        意圖：預設 PT72H 讓「凍住的實例」活過整整一個排程週期，於是它吃掉隔日觸發，
        當日觀察期三軌全部零進帳——這正是 AC4 從 10/14 退回 7/14 的機制。
        """
        m = re.search(r"-ExecutionTimeLimit\s+\(New-TimeSpan\s+-Hours\s+(\d+)\)", self.text)
        self.assertIsNotNone(
            m, "New-ScheduledTaskSettingsSet 必須帶 -ExecutionTimeLimit (New-TimeSpan -Hours N)"
        )
        assert m is not None
        hours = int(m.group(1))
        self.assertLessEqual(
            hours, 8,
            f"ExecutionTimeLimit={hours}h 過寬——正常整輪 5~8 分鐘，上限須遠小於 24h "
            "排程週期，否則凍住的實例仍會吃掉隔日觸發",
        )

    def test_stop_existing_applied_via_com_because_module_enum_cannot_express_it(self) -> None:
        """(3) StopExisting 必須走 COM，且兩支任務都要套用。

        意圖（DEF-101-249 同型加強版）：這次不是參數名不同，而是模組**根本表達不出
        這個值**——ScheduledTasks 產生的 MultipleInstancesEnum 只有
        Parallel/Queue/IgnoreNew，漏了 StopExisting。真機實測
        `New-ScheduledTaskSettingsSet -MultipleInstances StopExisting` 與
        `$t.Settings.MultipleInstances = 3` 皆被 enum 轉型擋下。
        故本鎖同時是反向鎖：若有人「簡化」成模組寫法，安裝器會在真機炸掉。
        """
        self.assertIn(
            "function Set-MultipleInstancesStopExisting", self.text,
            "必須有 COM fixup 函式（模組 enum 表達不出 StopExisting）",
        )
        self.assertRegex(
            self.text, r"\$def\.Settings\.MultipleInstances\s*=\s*3",
            "COM 路徑必須寫入數值 3（TASK_INSTANCES_STOP_EXISTING）",
        )
        calls = re.findall(r"Set-MultipleInstancesStopExisting\s+-Name\s+\$(\w+)", self.text)
        self.assertEqual(
            sorted(calls), ["SmokeTaskName", "TaskName"],
            f"兩支任務都必須套用 StopExisting fixup，實得 {calls}",
        )
        self.assertNotRegex(
            self.code, r"-MultipleInstances\s+StopExisting",
            "不得把該值直接傳給模組的 MultipleInstances 參數：ScheduledTasks 的 enum "
            "只有 Parallel/Queue/IgnoreNew，真機呼叫必炸（只掃可執行碼，註解不算）",
        )

    def test_status_surfaces_the_three_regression_prone_fields(self) -> None:
        """-Status 必須把三個回歸點印出來，否則只能等下次漏跑才發現。

        意圖：這三項漂移是**靜默**的——任務照樣 State=Ready，只是不會在該跑的時候跑。
        沒有可視化，回歸就沒有偵測管道。
        """
        for field in ("LogonType", "ExecutionTimeLimit", "MultipleInstancesPolicy"):
            self.assertIn(
                field, self.text, f"-Status 報表必須印出 {field}（回歸可偵測性）"
            )
        self.assertRegex(
            self.text,
            r"Export-ScheduledTask[\s\S]{0,140}?MultipleInstancesPolicy",
            "MultipleInstancesPolicy 必須自 Export-ScheduledTask 的 XML 讀取"
            "（Get-ScheduledTask 的 enum 對值 3 會印空白，會被誤讀成沒設定）",
        )


# ══════════════════════════════════════════════════════════════════════════════
# R74 — 線上排程設定的期望值 SSOT ＋ 漂移偵測器
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 **為何併進本檔而非另立新檔**：`tools/tests/` 有一道護欄層 shrink-only 棘輪
# （`DEF-101-561③`；R74 當時量的是檔數，🔴 R78 ARCH-03 訂正：R77 起已換成
# `test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的逐檔行數表，現行語意是
# **淨行數不得上升**、不是「禁止新增檔案」）。本檔是最貼近的家——它本來就是這兩支排程任務與其安裝器
# 的鎖之家，上方 TestUnattendedExecutionHardening 鎖的正是同一組設定值。
#
# 🔴 缺陷本體（R74 實測，唯讀即可證）：ADR-SD09-012 §8.2 在 2026-08-03 就列出五項
# 線上排程落差，而它連續三輪（R71/R72/R73）原封不動存活且**沒有任何東西轉紅**。
# 機械成因：線上排程只以「機器狀態」存在，repo 裡沒有任何檔案是它們 ⇒ 沒有對照組
# ⇒ 沒有任何檢查器能比。補法是兩件事一起做：
#   ① 期望值落成 repo 內的檔（tools/scheduled_task_expectations.json）；
#   ② 比對器（tools/check_scheduled_task_drift.py），不符即 rc=1。
# 本節鎖的是「① 與安裝器不得漂移」＋「② 的判定與跨平台安全性」。
_EXPECTATIONS_JSON = _REPO_ROOT / "tools" / "scheduled_task_expectations.json"
_DRIFT_CHECKER = _REPO_ROOT / "tools" / "check_scheduled_task_drift.py"

_SAMPLE_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Principals>
    <Principal id="Author">
      <UserId>DOMAIN\\user</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>StopExisting</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
  </Settings>
</Task>
"""


def _load_drift_module():
    """以檔案路徑載入比對器（根層 tools/ 非 package，不能 import 名稱）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_drift_checker", _DRIFT_CHECKER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestScheduledTaskExpectationsSsot(unittest.TestCase):
    """期望值 SSOT 與安裝器之間不得漂移（同一份知識只准有一個家）。"""

    def setUp(self) -> None:
        self.installer = _read(_SCRIPT)
        self.spec = json.loads(_EXPECTATIONS_JSON.read_text(encoding="utf-8"))
        self.tasks = self.spec["tasks"]

    def test_ssot_covers_exactly_the_tasks_the_installer_registers(self) -> None:
        """SSOT 的任務集合必須逐字等於安裝器註冊的兩支。

        意圖（Rule 9）：若安裝器多註冊一支而 SSOT 沒跟上，那支新任務的設定就回到
        「只以機器狀態存在」的失明狀態——本缺陷會原地復發，只是換一個任務名。
        """
        registered = set(re.findall(r"^\$(?:Smoke)?TaskName\s*=\s*'([^']+)'",
                                    self.installer, re.MULTILINE))
        self.assertEqual(
            set(self.tasks), registered,
            f"SSOT 任務集合 {sorted(self.tasks)} 與安裝器註冊的 {sorted(registered)} 不一致",
        )

    def test_every_expected_value_is_actually_applied_by_the_installer(self) -> None:
        """七項期望值逐項都要能在安裝器裡找到對應的套用手段。

        意圖：SSOT 若寫了安裝器做不到的期望值，比對器會永久紅（沒有修法），
        人就會把它關掉——期望值必須與唯一的套用途徑同源。
        對照表刻意寫死在測試裡：它就是「期望值 ↔ 套用手段」的橋，兩邊任一改動都會紅。
        """
        applied = {
            "Settings/StartWhenAvailable": r"-StartWhenAvailable",
            "Settings/WakeToRun": r"-WakeToRun",
            # 建構 cmdlet 的參數名極性相反（DEF-101-249），故期望 false ↔ Allow/DontStop
            "Settings/DisallowStartIfOnBatteries": r"-AllowStartIfOnBatteries",
            "Settings/StopIfGoingOnBatteries": r"-DontStopIfGoingOnBatteries",
            "Settings/ExecutionTimeLimit": r"-ExecutionTimeLimit\s+\(New-TimeSpan",
            "Settings/MultipleInstancesPolicy": r"\$def\.Settings\.MultipleInstances\s*=\s*3",
            "Principals/Principal/LogonType": r"-LogonType\s+S4U",
        }
        for task, spec in self.tasks.items():
            self.assertEqual(
                set(spec["expected"]), set(applied),
                f"{task} 的期望值欄位集合與「安裝器套用手段」對照表不一致",
            )
            for key, pattern in applied.items():
                self.assertRegex(
                    self.installer, pattern,
                    f"{task} 期望 {key}={spec['expected'][key]}，"
                    f"但安裝器找不到套用手段（pattern={pattern}）",
                )

    def test_execution_time_limit_expectation_matches_installer_hours(self) -> None:
        """PT<N>H 的 N 必須等於安裝器 New-TimeSpan -Hours 的 N（數值層對齊，非只有形狀）。"""
        m = re.search(r"-ExecutionTimeLimit\s+\(New-TimeSpan\s+-Hours\s+(\d+)\)", self.installer)
        assert m is not None
        for task, spec in self.tasks.items():
            self.assertEqual(
                spec["expected"]["Settings/ExecutionTimeLimit"], f"PT{m.group(1)}H",
                f"{task} 的 ExecutionTimeLimit 期望值與安裝器實際套用的小時數不一致",
            )

    def test_every_expected_setting_has_a_recorded_why(self) -> None:
        """每一項期望值都要有 WHY——沒有理由的期望值遲早被當成雜訊刪掉。"""
        why = self.spec["why_each"]
        for task, spec in self.tasks.items():
            missing = sorted(set(spec["expected"]) - set(why))
            self.assertEqual(missing, [], f"{task} 這些期望值缺 WHY：{missing}")


class TestScheduledTaskDriftChecker(unittest.TestCase):
    """比對器的判定（純函式層，不觸碰真實排程；跨平台可跑）。"""

    def setUp(self) -> None:
        self.mod = _load_drift_module()
        self.expectations = self.mod.load_expectations(_EXPECTATIONS_JSON)

    def test_parses_namespaced_task_xml(self) -> None:
        """Task Scheduler XML 帶命名空間，解析必須去前綴後仍取得七項值。"""
        parsed = self.mod.parse_task_xml(_SAMPLE_TASK_XML)
        self.assertEqual(parsed["Settings/WakeToRun"], "true")
        self.assertEqual(parsed["Settings/ExecutionTimeLimit"], "PT4H")
        self.assertEqual(parsed["Settings/MultipleInstancesPolicy"], "StopExisting")
        self.assertEqual(parsed["Principals/Principal/LogonType"], "S4U")

    def test_all_settings_matching_is_ok(self) -> None:
        parsed = self.mod.parse_task_xml(_SAMPLE_TASK_XML)
        report = self.mod.evaluate(self.expectations, dict.fromkeys(self.expectations, parsed))
        self.assertEqual(report["status"], "ok", report)
        self.assertEqual(report["drifts"], [])

    def test_missing_execution_time_limit_is_drift_not_ok(self) -> None:
        """實機現況：ExecutionTimeLimit 元素**根本不存在**（＝套用預設 PT72H）。

        意圖（Rule 9）：這是本缺陷五項之二的真實形態。若比對器只在「值不同」時判紅、
        對「欄位缺席」放行，那兩項就會永久隱形——正是它要治的病。
        """
        parsed = self.mod.parse_task_xml(_SAMPLE_TASK_XML)
        del parsed["Settings/ExecutionTimeLimit"]
        report = self.mod.evaluate(self.expectations, dict.fromkeys(self.expectations, parsed))
        self.assertEqual(report["status"], "drift")
        self.assertTrue(
            any(d["setting"] == "Settings/ExecutionTimeLimit" and d["actual"] == "<missing>"
                for d in report["drifts"]),
            report["drifts"],
        )

    def test_interactive_logon_type_is_drift(self) -> None:
        """smoke 的實機現況 InteractiveToken 必須被判紅（未登入時整輪不跑）。"""
        parsed = self.mod.parse_task_xml(
            _SAMPLE_TASK_XML.replace("<LogonType>S4U</LogonType>",
                                     "<LogonType>InteractiveToken</LogonType>")
        )
        report = self.mod.evaluate(self.expectations, dict.fromkeys(self.expectations, parsed))
        self.assertEqual(report["status"], "drift")

    def test_absent_tasks_are_skip_not_drift(self) -> None:
        """任務都不存在（CI runner／未安裝的開發機）→ skip，不得判紅。

        意圖：把「這台機器沒有這個受測對象」判成失敗，等於讓每個 CI runner 永久紅，
        而人的反應會是把這道檢查關掉——那就把剛補上的偵測管道又拆了。
        """
        report = self.mod.evaluate(self.expectations, dict.fromkeys(self.expectations, None))
        self.assertEqual(report["status"], "skip")
        self.assertEqual(sorted(report["absent"]), sorted(self.expectations))

    # 沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈R75「部分缺席」這一格的缺陷實測〉。

    def test_partial_absence_is_not_green(self) -> None:
        """一支完美 ＋ 一支整支不存在 → 非 ok、非 skip，且缺席那支要點名。

        意圖（Rule 9）：這條的鑑別力來源是「存在的那支刻意設成七項全符」——只要有人
        把判準退回「只看設定值」，剩下的那支就會讓整體回綠，本 case 立刻紅。
        """
        tasks = list(self.expectations)
        self.assertGreaterEqual(len(tasks), 2, "SSOT 至少要有兩支任務，本 case 才有意義")
        perfect = self.mod.parse_task_xml(_SAMPLE_TASK_XML)
        actuals: dict[str, Any] = dict.fromkeys(self.expectations, perfect)
        actuals[tasks[-1]] = None

        report = self.mod.evaluate(self.expectations, actuals)

        self.assertEqual(report["status"], self.mod.STATUS_TASK_MISSING, report)
        self.assertNotIn(report["status"], ("ok", "skip"), "部分缺席不得判綠")
        self.assertEqual(report["absent"], [tasks[-1]])
        self.assertEqual(report["present_count"], len(tasks) - 1)
        self.assertIn(tasks[-1], report["reason"])

    def test_partial_absence_still_reports_the_surviving_tasks_drifts(self) -> None:
        """主狀態是 task_missing，但存活那支的設定漂移**不得**被吞掉。

        意圖：狀態字只有一個，資訊不該因此變少——不然「先修回任務、再跑一次才看到
        設定也不對」會變成兩趟，而每一趟都需要一次提權操作。
        """
        tasks = list(self.expectations)
        parsed = self.mod.parse_task_xml(
            _SAMPLE_TASK_XML.replace("<LogonType>S4U</LogonType>",
                                     "<LogonType>InteractiveToken</LogonType>")
        )
        actuals: dict[str, Any] = dict.fromkeys(self.expectations, parsed)
        actuals[tasks[-1]] = None

        report = self.mod.evaluate(self.expectations, actuals)

        self.assertEqual(report["status"], self.mod.STATUS_TASK_MISSING)
        self.assertTrue(
            any(d["setting"] == "Principals/Principal/LogonType" for d in report["drifts"]),
            f"存活任務的漂移被主狀態吞掉了：{report['drifts']}",
        )

    def test_partial_absence_makes_main_exit_nonzero(self) -> None:
        """端到端（注入式）：main() 對部分缺席必須 rc=1。

        意圖：evaluate() 判對了但 main() 的 rc 白名單沒跟上等於沒修——nightly 讀的是 rc
        與 `status=` 那一行。**兩條**查詢路徑都要注入，否則 Linux 上 rc 巧合也是 1。
        """
        tasks = list(self.expectations)
        absent = tasks[-1]

        def _fake_export(task_name: str) -> str | None:
            return None if task_name == absent else _SAMPLE_TASK_XML

        buf = io.StringIO()
        with mock.patch.object(self.mod.sys, "platform", "win32"), \
             mock.patch.object(self.mod, "export_task_xml", _fake_export), \
             mock.patch.object(self.mod, "query_task_info", lambda _task: None), \
             mock.patch("sys.stdout", buf):
            rc = self.mod.main([])
        out = buf.getvalue()

        self.assertEqual(rc, 1, f"部分缺席回了 rc=0（缺陷原形）。輸出：\n{out}")
        self.assertIn(f"status={self.mod.STATUS_TASK_MISSING}", out)
        self.assertIn("判定為失敗", out, f"缺席行必須自己說出它算紅。輸出：\n{out}")
        self.assertIn("install_windows_nightly.ps1", out, "必須印出修法")

    def test_all_absent_is_skip_by_default_and_fails_only_when_declared_installed(self) -> None:
        """全缺席維持 skip（CI 安全），但 --require-installed 可把那一格關上。

        意圖（DEF-101-757：已知缺口不得只以劃界結案）：偵測器在「全缺席」這個位置
        沒有證據能區分「從沒裝過」與「兩支都被移除」，故預設不判紅；但「知道自己該有
        排程」的機器必須有辦法讓它紅。預設值與顯式宣告兩向都鎖，免得日後有人為了讓
        某台機器紅而改預設（那會讓每個 fresh clone 永久紅 → 檢查被關掉）。
        """
        all_absent: dict[str, Any] = dict.fromkeys(self.expectations, None)

        default = self.mod.evaluate(self.expectations, all_absent)
        self.assertEqual(default["status"], "skip")

        declared = self.mod.evaluate(self.expectations, all_absent, require_installed=True)
        self.assertEqual(declared["status"], self.mod.STATUS_TASK_MISSING)
        self.assertEqual(declared["present_count"], 0)

    def test_require_installed_still_exits_zero_on_non_windows(self) -> None:
        """新旗標不得破壞非 Windows 的 SKIP rc=0（DEF-101-766 教訓不得回歸）。

        意圖：`--require-installed` 是「這台機器該有排程」的宣告，而 macOS/Linux 上
        連 Task Scheduler 都不存在——把宣告外推成跨平台判準，就是那筆缺陷的原形。
        """
        def _boom(*a: Any, **k: Any) -> None:
            raise AssertionError("非 Windows 不得呼叫排程 API")

        with mock.patch.object(self.mod.sys, "platform", "darwin"), \
             mock.patch.object(self.mod, "_run_powershell", _boom), \
             mock.patch("sys.stdout", io.StringIO()):
            rc = self.mod.main(["--json", "--require-installed"])
        self.assertEqual(rc, 0)

    def test_task_missing_is_not_whitelisted_as_pass_by_the_nightly_wiring(self) -> None:
        """接線層核對：新狀態字必須落在 run_local_nightly.ps1 的 fail-closed 那一側。

        意圖（Rule 9）：偵測器 rc=1 只有在接線層把它算成失敗時才有效。該檔對狀態字
        採白名單（`-notin @('ok','skip')` 即計入 finalFailures，並明文寫「含未來新增
        的狀態字」），所以 `task_missing` **不得**被加進那份白名單。
        R76 註記：`drift` 也已移出白名單（見 TestNamedExemptionRetires... 那支鎖），
        故現值只剩 ok/skip；本鎖的職責不變——task_missing 落在計失敗那一側。
        """
        whitelisted = _nightly_drift_pass_whitelist(_read(_NIGHTLY_PS1))
        self.assertNotIn(
            self.mod.STATUS_TASK_MISSING, whitelisted,
            f"task_missing 被列入不計失敗的白名單 {sorted(whitelisted)}——"
            "任務不見了會只印一行 WARN 而 nightly 照樣 exit 0",
        )
        self.assertEqual(
            whitelisted, {"ok", "skip"},
            f"白名單內容已變動（實得 {sorted(whitelisted)}）——請重新確認 "
            "task_missing 仍計入 finalFailures",
        )

    def test_non_windows_exits_zero_without_touching_task_scheduler(self) -> None:
        """非 Windows 必須 rc=0 且不得呼叫 PowerShell（macos/ubuntu CI 不可因此紅）。

        意圖（DEF-101-766 同型教訓）：單平台判準無條件外推是本 repo 踩過的坑；
        本鎖同時反向確認它沒有偷偷去跑 subprocess（那在 CI 容器裡會是另一種紅）。
        """
        called: list[Any] = []

        def _boom(*a: Any, **k: Any) -> None:
            called.append(a)
            raise AssertionError("非 Windows 不得呼叫排程 API")

        with mock.patch.object(self.mod.sys, "platform", "darwin"), \
             mock.patch.object(self.mod, "_run_powershell", _boom), \
             mock.patch("sys.stdout", io.StringIO()):
            rc = self.mod.main(["--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(called, [])

    def test_rejects_task_names_with_shell_metacharacters(self) -> None:
        """任務名會被代入 PowerShell 命令字串 → 非白名單字元必須拒絕。"""
        with self.assertRaises(ValueError):
            self.mod.export_task_xml("Bad'; rm -rf /; '")


def _nightly_drift_pass_whitelist(wiring: str) -> set[str]:
    """抽出 `run_local_nightly.ps1` 對排程漂移狀態字的「不計入 finalFailures」白名單。

    抽不到時 **raise 而不是回空集合**：回空集合會讓所有「某狀態不得被豁免」的斷言
    自動通過（fail-open），而接線層改寫正是最需要有人回來看一眼的時機。
    """
    m = re.search(r"\$schedDriftStatus\s+-notin\s+@\(([^)]*)\)", wiring)
    if m is None:
        raise AssertionError(
            "run_local_nightly.ps1 的 [SCHED-DRIFT] 狀態字白名單結構已變動——"
            "各狀態字落在哪一側需重新確認（本鎖刻意不猜）"
        )
    return set(re.findall(r"'([^']+)'", m.group(1)))


class TestNamedExemptionRetiresWhenItsUnlockConditionHolds(unittest.TestCase):
    """R76：具名豁免的**解除條件一旦成立，豁免就必須消失**——由機械物盯，不靠人讀 WARN。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈TestNamedExemptionRetiresWhenItsUnlockConditionHolds 缺陷本體與三個方向〉。
    """

    #: 偵測器回這個狀態＝受管任務都在、每一項設定都符合期望＝提權修復已完成。
    UNLOCK_STATUS = "ok"
    #: 語意上真的等於「通過」的兩格。其餘任何狀態字被列進白名單，就是一條具名豁免。
    PASS_STATUSES = frozenset({"ok", "skip"})
    #: 豁免要退場的那個狀態字（本輪的具體標的；一般化規則見上方 docstring）。
    RETIRED_EXEMPTION = "drift"

    def setUp(self) -> None:
        self.wiring = _read(_NIGHTLY_PS1)
        self.whitelist = _nightly_drift_pass_whitelist(self.wiring)

    def _revived(self, whitelist: set[str]) -> set[str]:
        """白名單裡「不等於通過」的狀態字＝仍然活著的具名豁免。"""
        return whitelist - set(self.PASS_STATUSES)

    def test_recorded_unlock_observation_forbids_the_exemption(self) -> None:
        """①：接線層已記載 status=ok 這次觀測 ⇒ 豁免必須已經不在白名單裡。

        觀測是**歷史事實**，不因今天這台機器量不到而失效，故本判準無平台條件。
        同時要求那次觀測的字面留在檔內：沒有它，「為什麼可以移除豁免」就失去來源，
        下一個人會以為 drift 計失敗是從來就有的設計，看不到真正的教訓。
        """
        self.assertIn(
            f"status={self.UNLOCK_STATUS}", self.wiring,
            "接線層必須留下『解除條件已達成』那次觀測的字面——它是移除豁免的唯一依據",
        )
        self.assertEqual(
            self._revived(self.whitelist), set(),
            f"白名單 {sorted(self.whitelist)} 仍含具名豁免，而解除條件（偵測器回 "
            f"status={self.UNLOCK_STATUS}）已經達成並記載在同一份檔案裡",
        )

    def test_live_detector_agreeing_with_the_record_forbids_the_exemption(self) -> None:
        """②：真機交叉核對——偵測器**現在**若回 status=ok，同一結論必須成立。

        本鎖存在的理由是「解除條件達成當天就要有東西說話」，所以它必須真的去問偵測器，
        而不是只讀一段人寫的紀錄（那正是 R75 那條 WARN 的失敗形態：紀錄在、沒人讀）。
        """
        status = self._live_detector_status()
        if status is None or status == "skip":
            # 量不出來（非 Windows／偵測器問不到／本機沒裝受管排程）：不 skip、不靜默，
            # 退回①的靜態結論並把原因印出來，讓「這台機器沒驗到②」是看得見的。
            print(
                "[R76-exemption-retire] 本機量不出來（status="
                f"{status!r}, sys.platform={sys.platform}）⇒ 本格退回靜態判準",
                file=sys.stderr,
            )
            self.assertEqual(
                self._revived(self.whitelist), set(),
                f"白名單 {sorted(self.whitelist)} 仍含具名豁免（靜態判準；本機未取得真機證據）",
            )
            return
        self.assertEqual(
            status, self.UNLOCK_STATUS,
            f"偵測器回 status={status!r} ⇒ 排程設定現在就有問題，先修排程再談豁免退場"
            "（修法：以系統管理員身分重跑 tools/install_windows_nightly.ps1）",
        )
        self.assertEqual(
            self._revived(self.whitelist), set(),
            f"偵測器真機回 status={self.UNLOCK_STATUS}（＝解除條件成立），"
            f"而白名單 {sorted(self.whitelist)} 仍含具名豁免 ⇒ 豁免活過了自己的解除條件",
        )

    def test_lock_turns_red_when_a_retired_exemption_is_revived(self) -> None:
        """③ 鑑別力（合成輸入，三平台都跑）：把豁免加回去必須被判紅。

        沒有這一格，①②在「白名單抽取失效」時會一起變成恆綠——本鎖自己就是它在防的
        那種「看起來有在守、其實不會紅」的護欄。
        """
        revived = "if ($schedDriftStatus -notin @('drift', 'ok', 'skip')) {"
        self.assertEqual(
            self._revived(_nightly_drift_pass_whitelist(revived)),
            {self.RETIRED_EXEMPTION},
            "合成的『豁免復活』白名單未被判出——抽取或比較失效，①②已無鑑別力",
        )
        current = "if ($schedDriftStatus -notin @('ok', 'skip')) {"
        self.assertEqual(
            self._revived(_nightly_drift_pass_whitelist(current)), set(),
            "合成的『豁免已退場』白名單被誤判——本鎖會對正確狀態誤報",
        )
        with self.assertRaises(AssertionError):
            _nightly_drift_pass_whitelist("接線層被改寫成別的形態，抽不到白名單")

    def _live_detector_status(self) -> str | None:
        """問偵測器本體要 status；問不到回 None。**唯讀**：不註冊、不移除任何排程任務。"""
        if sys.platform != "win32":
            return None
        buf = io.StringIO()
        try:
            with mock.patch("sys.stdout", buf):
                _load_drift_module().main(["--json"])
            return str(json.loads(buf.getvalue()).get("status")) or None
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            return None


class TestWindowsSmokeTaskHasWrittenExitCriteria(unittest.TestCase):
    """R74 F 項：AutoClaude_WindowsSmoke 這支排程任務必須有成文、可機械查的退出判準。

    沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md
    〈TestWindowsSmokeTaskHasWrittenExitCriteria 缺陷本體與三件事〉。
    """

    def setUp(self) -> None:
        self.smoke = _read(_SMOKE_PS1)

    def test_exit_criteria_section_exists(self) -> None:
        self.assertIn(
            "退出判準", self.smoke,
            "windows_smoke_local.ps1 檔頭必須載明退出判準——"
            "沒有退出判準的補償控制無法被結束，只能被遺忘",
        )
        for marker in ("E1.", "E2.", "E3."):
            self.assertIn(marker, self.smoke, f"退出判準必須逐條編號，缺 {marker}")

    def test_criteria_are_mechanically_checkable(self) -> None:
        """三條判準各自要指名一個可實跑的查法，不得只是形容詞。"""
        for probe in ("gh run list", "test_smoke_ci_sync.py",
                      "check_scheduled_task_drift.py"):
            self.assertIn(
                probe, self.smoke,
                f"退出判準必須指名可實跑的查法，缺 {probe}",
            )

    def test_separates_the_script_from_the_scheduled_task(self) -> None:
        """腳本與排程任務的存廢理由不同，判準必須分開陳述。"""
        self.assertIn("AutoClaude_WindowsSmoke", self.smoke)
        self.assertRegex(
            self.smoke, r"永久保留",
            "本腳本本身（push 前／離線的 88 秒 tripwire）不應有退出判準，須明說",
        )

    def _e3_paragraph(self) -> str:
        """抽出 E3 那一段（從 `#   E3.` 到該段落結束的空註解行）。"""
        m = re.search(r"^#   E3\..*?(?=^#\s*$)", self.smoke, re.S | re.M)
        self.assertIsNotNone(
            m, "抽不到 E3 段落——退出判準的排版已變動，本鎖刻意不猜（fail-closed）"
        )
        assert m is not None
        return m.group(0)

    def test_e3_measures_only_what_survives_its_own_action(self) -> None:
        """🔴 R76：E3 的量測對象不得隨「被它所判的動作」而改變（R75 頭號教訓第三次復發）。

        缺陷本體：E3 原文要求「移除後 `check_scheduled_task_drift.py` 回 rc=0」，而該工具的
        期望值 SSOT（`tools/scheduled_task_expectations.json`）**同時列兩支任務** ⇒ 執行
        E3 自己授權的動作（移除 AutoClaude_WindowsSmoke）必然讓它回 `task_missing`／rc=1。
        判準在結構上不可滿足 ⇒ 這支排程永遠退不了場，而失敗看起來只像「條件還沒到」。

        意圖（Rule 9）：本鎖守的不是「E3 現在寫得對」，而是**不可滿足的判準不得再被寫回去**。
        三個方向：①E3 必須點名它真正關心的那一支；②不得把它授權移除的那一支算進量測對象；
        ③必須是**逐任務**讀法（整支工具的 rc／status 會把 smoke 算進去）。
        """
        e3 = self._e3_paragraph()
        self.assertIn(
            "AutoClaude_Nightly", e3,
            "E3 必須點名它真正關心的那一支（每日執行級心跳＝nightly，不是 smoke）",
        )
        self.assertNotIn(
            "AutoClaude_WindowsSmoke", e3,
            "E3 把它自己授權移除的那支任務算進了量測對象 ⇒ 判準結構上不可滿足："
            "執行 E3 授權的動作必然讓 E3 轉紅（R75 頭號教訓同形態）",
        )
        self.assertIn(
            "tasks.AutoClaude_Nightly", e3,
            "E3 必須用**逐任務**欄位取證（--json 的 .tasks.<name>）；改讀整支工具的 "
            "rc／status 就等於把 smoke 任務的存在與否又綁回判準裡",
        )
        self.assertIn(
            "不得隨「被它所判的動作」而改變", self.smoke,
            "一般化規則必須成文留在判準段旁邊——只修好這一條 E3 不會阻止下一條同形態判準",
        )

    def test_zero_findings_is_explicitly_rejected_as_a_retirement_basis(self) -> None:
        """反向鎖：不得把「零發現」寫成退場依據。

        意圖（Rule 9）：「連續 N 天沒抓到東西所以撤掉」是最自然、也最錯的判準——
        它會在通道還有價值時把它撤掉，而且錯誤方向是不可逆的（撤掉後就沒有訊號了）。
        """
        self.assertIn(
            "零發現", self.smoke,
            "必須明文交代為何不以『零發現』當退場依據（否則下一個人一定會這樣做）",
        )


if __name__ == "__main__":
    # 🔴 只有「直接以本檔為入口點跑」時才需要自備保護（R76 收斂包）：本檔有一格會把中文
    # 診斷印到 stderr（TestNamedExemptionRetiresWhenItsUnlockConditionHolds 的「本機量不
    # 出來」分支刻意不 skip、改印原因），Windows 非 UTF-8 主控台會讓那行崩潰或降解成
    # \uXXXX——那正是 DEF-101-798 的形態。經 run_root_unittests.py／pytest 啟動時保護屬
    # 載具，本區塊不執行。實作走唯一 SSOT `tools/_stdio_utf8.py`，不在此複製第二份。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

    unittest.main()
