#Requires -Version 5.1
<#
.SYNOPSIS
Windows nightly 排程一鍵安裝器（R19 修復包 D，鏡射 tools/install_mac_nightly.sh 定位）。

.DESCRIPTION
為何存在：mac 側有 tools/install_mac_nightly.sh 一鍵建立 launchd 排程（install/
uninstall/status/render-only 四模式）；Windows 側至今只有
AutoClaude/tools/fix_nightly_catchup.ps1——假設 AutoClaude_Nightly 這個 schtasks
任務「已經存在」（找不到就直接拋錯），只能「校正既有任務設定」，不能「從零建立」。
本腳本補上「從零建立」這一段，並把 fix_nightly_catchup.ps1 記載的補跑保護設定
（StartWhenAvailable / WakeToRun / 電池相關）直接內建在建立時——新機器不必再另外
跑一次 fix_nightly_catchup.ps1（已安裝的舊機器仍可用該腳本校正）。

任務內容對齊 AutoClaude/tools/run_local_nightly.ps1 檔頭 .NOTES 現行文件化排程
慣例：Action=powershell.exe -NoProfile -ExecutionPolicy Bypass -File
<repo>\AutoClaude\tools\run_local_nightly.ps1、Trigger=每日 02:00。

.PARAMETER Uninstall
移除 AutoClaude_Nightly 排程任務（冪等：不存在也視為成功）。

.PARAMETER Status
查詢排程任務目前狀態（存在與否、上次執行結果、下次執行時間、補跑保護設定），
不做任何變更。Windows工作排程器原生以 Get-ScheduledTaskInfo 提供「上次執行時間」，
取代 mac 版讀心跳檔案 mtime 的機制——兩者語意對應但實作不同，如實揭露、不勉強模擬。

**結束代碼是斷言，不只是查詢**（2026-07-27 起）：exit 0 代表「主任務存在，且涵蓋
清單內每個存在的任務四項電源設定皆符期望」；任一項不符即 exit 1 並 Write-Warning。
涵蓋清單＝$TaskName ＋ $AuxTaskNames（見該兩個變數上方註解說明為何一併驗、
以及為何 aux 任務缺席不判失敗）。修復前本模式**恆 exit 0 且一行輸出都不印**，
使得「排程電源設定漂移」在全 repo 沒有任何會翻紅的路徑。

.PARAMETER WhatIf
（PowerShell 內建通用參數，本腳本以 SupportsShouldProcess 支援）只印出將執行的
建立/移除動作，不實際呼叫 Register-ScheduledTask / Unregister-ScheduledTask，
方便驗證邏輯而不需真的動 Task Scheduler。

.NOTES
用法（比照 install_mac_nightly.sh 四模式；Register/Unregister-ScheduledTask
需系統管理員權限，非管理員執行 install/uninstall 會 fail-loud 提示需 elevation；
-Status / -WhatIf 唯讀查詢，不需 elevation）：
  powershell -File tools\install_windows_nightly.ps1                # install（預設）
  powershell -File tools\install_windows_nightly.ps1 -Uninstall
  powershell -File tools\install_windows_nightly.ps1 -Status
  powershell -File tools\install_windows_nightly.ps1 -WhatIf        # 僅預覽，不變更系統
#>
[CmdletBinding(SupportsShouldProcess)]
param(
  [switch]$Uninstall,
  [switch]$Status
)

$ErrorActionPreference = 'Stop'

$TaskName = 'AutoClaude_Nightly'
# -Status 的涵蓋清單：本 repo 其他腳本註冊、但**不由本安裝器管理**的排程任務。
# 為何要一併驗（2026-07-27 真 Windows 原生機器實測）：本腳本的 -Status 是全 repo
# 唯一的官方排程查詢入口，涵蓋面若只有 $TaskName，其他 repo 排程的電源設定漂移就
# 「沒有任何會翻紅的路徑」。實測當下 AutoClaude_SD09_G0_GateCheck 的
# StopIfGoingOnBatteries 就是 True（期望 False），而全 repo 沒有一支測試或腳本會發現。
# 缺席刻意不判失敗（只印一行資訊）：GateCheck 是一次性 gate check，跑完被移除是正常
# 終態，硬要求它存在會讓 -Status 在乾淨機器與 CI runner 上恆紅。
# 名稱不得與 AutoClaude/tools/reschedule_g0_gatecheck.ps1 的 $TaskName 漂移，該對齊由
# tools/tests/test_install_windows_nightly.py 機械跨檔比對守門（勿改成別的字面）。
$AuxTaskNames = @('AutoClaude_SD09_G0_GateCheck')
$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))
$NightlyPs1 = Join-Path $RepoRoot 'AutoClaude\tools\run_local_nightly.ps1'

function Test-IsAdmin {
  ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-TaskPowerSettings {
  # 印出一個任務的四項「補跑／電源保護」設定實況，並回傳「是否四項全數符期望」。
  #
  # 為何四項全驗、而非印四項只驗零項（2026-07-27 真 Windows 原生機器實測）：漏跑與
  # 中斷是四個彼此獨立的失敗模式，缺一即破——StartWhenAvailable（關機錯過後補跑）、
  # WakeToRun（睡眠／休眠中喚醒）、DisallowStartIfOnBatteries=False（吃電池不擋啟動）、
  # StopIfGoingOnBatteries=False（執行中切到電池不被中途砍掉）。判準與姊妹腳本
  # AutoClaude/tools/fix_nightly_catchup.ps1 的成功條件逐項一致，避免兩支腳本對
  # 「設定正確」養出兩套定義。
  #
  # 🔴 人類可讀報告刻意走 Write-Host（不是 Write-Output），這不是風格偏好而是正確性
  # 需求：本函式的最終呼叫端是 `$loaded = Show-NightlyStatus`，PowerShell 的變數指派
  # 會把函式（含其巢狀呼叫）寫到 success stream 的**所有**東西一起吃進去。用
  # Write-Output 的後果實測為兩個疊加的 bug：① 報告一行都不顯示；② $loaded 變成
  # 「字串…＋布林」的 Object[]，而 PowerShell 對元素數 ≥2 的陣列一律判為真 →
  # 結束代碼恆 0。2026-07-27 實測修復前行為：`-Status` 對一個**不存在**的任務印出
  # 0 bytes 且 exit 0（DEF-101-248 宣稱的修復因此從未真正生效）。
  # Write-Host 在 PS 5.1 走 information stream，不被變數指派捕獲；已實測涵蓋
  # 「行程 stdout 被重導向至檔案（`> file 2>&1`）時文字仍會落進該檔」，故人類用法與
  # 文件記載的用法不受影響。已實測不涵蓋：以 `6>` 單獨重導 information stream 的呼叫端
  # （本 repo 現無此類呼叫端）。未窮舉其他 PowerShell host（ISE／遠端 session）。
  param($Task)
  $s = $Task.Settings
  Write-Host "  StartWhenAvailable         = $($s.StartWhenAvailable)   (expected True)"
  Write-Host "  WakeToRun                  = $($s.WakeToRun)   (expected True)"
  Write-Host "  DisallowStartIfOnBatteries = $($s.DisallowStartIfOnBatteries)   (expected False)"
  Write-Host "  StopIfGoingOnBatteries     = $($s.StopIfGoingOnBatteries)   (expected False)"
  return ($s.StartWhenAvailable -and $s.WakeToRun -and -not $s.DisallowStartIfOnBatteries -and -not $s.StopIfGoingOnBatteries)
}

function Show-NightlyStatus {
  # 回傳值語意（2026-07-27 擴大）：原本只回「任務是否存在」，現回「主任務存在**且**
  # 涵蓋清單內每個存在的任務四項電源設定皆符期望」。
  #
  # 為何擴大既有回傳值語意、而非另立 -Verify／-Assert 開關（三個理由，依權重）：
  #   ① tools/tests/test_schedule_capability_parity.py::test_win_switch_names_extracted_sane
  #      機械斷言本腳本的 switch 集合**恰為** {Uninstall, Status}，新增 switch 會直接
  #      弄紅一支不在本次修復範圍內的測試，並連帶要改該檔的 mac↔win 能力對照表。
  #   ② 實查全 repo 無任何自動化呼叫端使用 -Status：tools/windows_smoke_local.ps1 [9/9]
  #      與 .github/workflows/windows-compat-ci.yml 都只用 -WhatIf，其餘命中僅
  #      ONBOARDING.md 的說明文字與本腳本自己印的提示字串。擴大語意的呼叫端衝擊為零，
  #      不需要靠新開關來保護既有呼叫端。
  #   ③ 「排程存在但電源設定漂移」實質就是「排程不會如期跑完」，回報成功違反 Rule 12
  #      （fail loud）；把它藏在一個要另外記得加的開關後面，等於預設繼續說謊。
  #
  # 變數名 $loaded 在呼叫端沿用（雖已非「是否載入」的原語意）：該行字面被
  # tools/tests/test_install_windows_nightly.py::test_status_exit_code_reflects_task_existence
  # 靜態鎖住，改名會弄紅該測試而無實質收益。
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if (-not $task) {
    Write-Host "❌ 排程任務不存在：${TaskName}——安裝：powershell -File tools\install_windows_nightly.ps1"
    return $false
  }
  $info = $task | Get-ScheduledTaskInfo
  Write-Host "✅ 排程任務存在：${TaskName}（State=$($task.State)）"
  Write-Host "  LastRunTime    = $($info.LastRunTime)"
  Write-Host "  LastTaskResult = $($info.LastTaskResult)"
  Write-Host "  NextRunTime    = $($info.NextRunTime)"
  $allOk = Test-TaskPowerSettings -Task $task
  foreach ($aux in $AuxTaskNames) {
    $auxTask = Get-ScheduledTask -TaskName $aux -ErrorAction SilentlyContinue
    if (-not $auxTask) {
      Write-Host "[i] 本 repo 另一排程任務未安裝，略過（刻意不判失敗）：${aux}"
      continue
    }
    Write-Host "✅ 本 repo 另一排程任務存在：${aux}（State=$($auxTask.State)）"
    if (-not (Test-TaskPowerSettings -Task $auxTask)) { $allOk = $false }
  }
  if (-not $allOk) {
    Write-Warning ("排程電源設定與期望不符（逐行比對上方 (expected ...) 標註）——機器睡眠時會漏跑，" +
      "或筆電執行中切到電池時被工作排程器當場砍掉，取證輸出被截斷或全無。校正（需系統管理員）：" +
      "${TaskName} 跑 AutoClaude\tools\fix_nightly_catchup.ps1；一次性 gate check 任務跑 " +
      "AutoClaude\tools\reschedule_g0_gatecheck.ps1。兩支都是冪等的。")
  }
  return $allOk
}

if ($Status) {
  if ($Uninstall) {
    Write-Warning "-Status 與 -Uninstall 同時給出，-Uninstall 已被忽略（僅查詢狀態，不做任何變更）。"
  }
  $loaded = Show-NightlyStatus
  if ($loaded) { exit 0 } else { exit 1 }
}

if (-not (Test-Path -LiteralPath $NightlyPs1)) {
  Write-Error "找不到 nightly 載體：${NightlyPs1}"
  exit 1
}

if ($Uninstall) {
  if (-not (Test-IsAdmin) -and -not $WhatIfPreference) {
    Write-Warning "需要系統管理員權限——請以「以系統管理員身分執行」重新開啟 PowerShell 後再跑本腳本。"
    exit 1
  }
  $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister-ScheduledTask')) {
    if ($existing) {
      Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
      Write-Output "✅ 已解除安裝：移除排程任務 ${TaskName}"
    } else {
      Write-Output "✅ 無事可做：${TaskName} 不存在（冪等）"
    }
  }
  exit 0
}

# install（冪等：重複執行不應報錯或建立重複任務——鏡射 install_mac_nightly.sh
# cmd_install() 的 unload-then-load 冪等手法，這裡改為「存在就先移除再重建」）。
if (-not (Test-IsAdmin) -and -not $WhatIfPreference) {
  Write-Warning "需要系統管理員權限——請以「以系統管理員身分執行」重新開啟 PowerShell 後再跑本腳本。"
  exit 1
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"${NightlyPs1}`""
$trigger = New-ScheduledTaskTrigger -Daily -At '02:00'
# 補跑保護設定直接內建於建立時（語意對齊 AutoClaude/tools/fix_nightly_catchup.ps1
# 的目標終態，省去新機器安裝後還要再手動跑一次 fix 腳本）：
#   StartWhenAvailable = True   關機錯過時，開機後補跑
#   WakeToRun          = True   睡眠/休眠時，喚醒機器準時執行
#   DisallowStartIfOnBatteries = False  筆電吃電池時不擋啟動
#   StopIfGoingOnBatteries     = False  執行中切到電池不中途砍掉
# DEF-101-249（R20 真 Windows 機器驗證）：New-ScheduledTaskSettingsSet 這個「建構」
# cmdlet 的參數名與 Settings 物件本身的屬性名極易混淆——物件屬性叫
# DisallowStartIfOnBatteries／StopIfGoingOnBatteries（fix_nightly_catchup.ps1 讀寫既有
# 任務時用的正是這兩個屬性名，那裡沒錯），但這個「建構」cmdlet 的參數名極性相反、
# 名稱也不同：-AllowStartIfOnBatteries（開關，給了＝物件屬性 Disallow...=False）／
# -DontStopIfGoingOnBatteries（開關，給了＝物件屬性 Stop...=False）。原參數名
# -DisallowStartIfOnBatteries/-StopIfGoingOnBatteries 在這個 cmdlet 上根本不存在，
# 只在磁碟真機（非 -WhatIf 也非純語法解析）呼叫時才會拋
# ParameterBindingException（NamedParameterNotFound）——CI 與既有測試只做語法解析，
# 從未真的呼叫過這個 cmdlet，R19 未曾發現；真機實測 New-ScheduledTaskSettingsSet
# 後讀物件屬性確認兩者對應正確（本節新參數名產出的 Settings 物件屬性值符合預期）。
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -WakeToRun `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries

if ($PSCmdlet.ShouldProcess($TaskName, 'Register-ScheduledTask')) {
  $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description 'AutoClaude nightly 本地聚合驗證（見 AutoClaude/tools/run_local_nightly.ps1）' | Out-Null
  Write-Output "✅ 已安裝並註冊排程任務：${TaskName}（每日 02:00 → ${NightlyPs1}）"
  Write-Output "   另含 StartWhenAvailable/WakeToRun 補跑保護（關機/睡眠錯過仍可補跑）"
  Write-Output "   驗證：powershell -File tools\install_windows_nightly.ps1 -Status"
}
exit 0
