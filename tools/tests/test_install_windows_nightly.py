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
靜態文字結構驗證（＋若本機有 powershell/pwsh 則額外做語法解析，純解析不執行，
跨平台安全），不嘗試真的呼叫排程 API。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
            '-Argument "-NoProfile -ExecutionPolicy Bypass -File `"${SmokePs1}`""', self.text,
            "smoke 任務的 Action 須以原生 powershell.exe -File 呼叫（DEF-101-511："
            "該腳本偵測到 $env:MSYSTEM 即拒跑，故不得經由任何 bash 包裝層觸發）",
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

        意圖（Rule 9）：DEF-101-779 把觸發時刻從程式碼裡的寫死值改成參數，但 R73 首版
        **同時在 help 區塊寫下一組錯的預設值**（`② … 預設 23:30`，實際 param 是 21:30），
        且同段又寫「預設值＝本機現行實況」——與 param 區塊「刻意不把兩個預設都設成現況」
        直接互相打臉。方向仍是危險側：讀 help 的人以為不帶參數跑不會動 smoke，實際會被
        搬走。**「靜默改掉時間」這個陷阱沒被消滅，只是從程式碼搬進了說明文字**
        （Architect／SA／SD 三方二審獨立命中同一筆）。

        所以鎖的判準不是「說明要正確」（那無法機械判定），而是「說明裡**不准有時刻**」
        ——預設值只有 param 區塊一個權威源，現行排程只有 `Get-ScheduledTaskInfo` 一個
        權威源。只靠自律的話，這個形態已證實會在同一支檔、同一個 commit 內重生。
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
        （比照既有 fix_nightly_catchup.ps1／reschedule_g0_gatecheck.ps1 慣例），
        非管理員身分須 fail-loud 提示，而非讓 Register-ScheduledTask 自己拋出難懂的例外。"""
        self.assertIn("WindowsBuiltInRole]::Administrator", self.text)

    def test_status_exit_code_reflects_task_existence(self) -> None:
        """DEF-101-248（R20 Scan-A）：-Status 先前不論任務存不存在恆 exit 0，與 mac 版
        `install_mac_nightly.sh --status`（任務未載入時非零結束代碼）語意不對等，任何
        想拿結束代碼做自動化判斷（CI／監控腳本）在 Windows 上會拿到假陽性。修復後須
        依實際存在性決定 exit 0/1，而非寫死 exit 0。

        🔴 R60 DEF-101-542：本斷言原文要求 `$loaded = Show-NightlyStatus`，而該修法
        **在 PowerShell 上根本不成立**——函式內所有 `Write-Output` 都會併入回傳值，
        `$loaded` 實得 `Object[]`（報表字串 + 布林），`if ($loaded)` 對非空陣列恆為真
        ⇒ `-Status` 又變回「恆 exit 0」，DEF-101-248 的修復被語意打敗且**本測試看不到**
        （它只比對原始碼字面，從不執行）。修法：把「印報表」與「判定存在」拆成兩支
        函式（`Show-TaskDetail`／`Test-TaskPresent`，沿用 run_root_unittests.py
        `report_windows_native_skips`／`windows_native_skips` 的既有慣例），並由
        `TestStatusExitCodeRuntime` 以真的執行取代字面比對來守這條不變量。
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

        本測試鎖住結構層不變量：真正的 `-Uninstall` 處理區塊——以行首（無縮排）的
        `if ($Uninstall) {` 為起點錨點（真正區塊頂格書寫；`-Status` 區塊內那個只印
        警告、同名但不同語意的巢狀 `if ($Uninstall)` 有縮排，`^` + `re.MULTILINE`
        會跳過它），以其內含的 `foreach ($name in @($TaskName, $SmokeTaskName))`
        迴圈為終點錨點——本體不得包含任何 `Test-Path -LiteralPath $NightlyPs1` /
        `$SmokePs1` 呼叫，且兩個存在性檢查必須出現在該區塊**之後**（即收斂進
        install-only 段落）。

        錨點修訂記錄：原始版本起點無 `^`／`re.MULTILINE`，`re.search` 實際抓到的是
        `-Status` 區塊內那個縮排的巢狀 `if ($Uninstall)`（第一個出現的匹配），而非
        本文件宣稱排除的對象；因兩者在原始碼中相鄰、捕獲範圍恰好完整涵蓋真正區塊，
        對 DEF-101-619 這個特定回歸仍有鑑別力，但與文件描述的機制不符（Review round
        1 發現）。加 `^` 錨點後才是文件宣稱的行為。
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


# R59 DEF-101-509：本條件原為 `shutil.which("pwsh")`（**只認 PS 7**）。後果是本檔
# 唯一真的解析語法的測試，在「一台標準 Windows 11 開發機」上必定 skip——ONBOARDING §1
# 明列 pwsh 7 為**選用**（`winget install Microsoft.PowerShell` 才有），Windows 11 內建
# 的是 Windows PowerShell 5.1。於是一支 **Windows 專屬**腳本的語法閘門，恰恰在它唯一
# 能真正執行的平台上不跑，且因該 skip 未帶 `[WINDOWS-NATIVE-ONLY]` 標籤而被
# `run_root_unittests.py` 的可見度機制漏掉（同 DEF-101-343~345／R43 的缺陷類別）。
# 唯一還會跑到它的環境是 GitHub-hosted runner（ubuntu/windows 皆預裝 pwsh）——而 CI
# 因帳務停擺（DEF-101-081/208）目前不啟動 runner，等於此閘門現況零活體覆蓋。
#
# 改用 `powershell or pwsh`（與同目錄 `test_bootstrap_ps1.py::_windows_pwsh_available`／
# `test_dev_start_ps1_lastexitcode.py` 既有慣例逐字同構）不只是「讓它別 skip」，語意上
# **更貼近生產**：本腳本在生產是以 `powershell -ExecutionPolicy Bypass -File` 執行（＝5.1），
# 而 `pwsh` 解析用的是 PS 7 文法。5.1 的 parser 才是真正的目標文法，且本檔所在的
# `tools/` 樹受 `test_ps51_compat.py` 的「PS 5.1 相容」政策約束，故以 5.1 優先解析
# 與該政策一致（R59 實測：PS 5.1 `Parser::ParseFile` 對本腳本 errs=0）。
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

    WHY 一定要用執行而不能用字面比對：原本的靜態斷言（比對 `$loaded = Show-...`）
    在腳本行為完全壞掉（恆 exit 0）的情況下照樣全綠——R60 實測把 `$TaskName` 換成
    一個不存在的名字後跑 `-Status`，真實結束代碼是 **0**。「字面對了但語意反了」
    是 PowerShell 特有的陷阱（函式輸出串併入回傳值），只有跑起來才看得到。

    方法：把安裝器複製到 temp、把兩個任務名改寫成保證不存在的名字後執行——
    **不註冊、不移除任何排程任務**（純唯讀查詢；本 repo 紀律：真安裝屬使用者 ops，
    須另行核可）。`-Status` 區塊在腳本中位於載體存在性檢查之前，故複本雖然算出錯的
    $RepoRoot 也不影響本測試（R60 實測確認）。
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


if __name__ == "__main__":
    unittest.main()
