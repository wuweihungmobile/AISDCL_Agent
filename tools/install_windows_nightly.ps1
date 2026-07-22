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
$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))
$NightlyPs1 = Join-Path $RepoRoot 'AutoClaude\tools\run_local_nightly.ps1'

function Test-IsAdmin {
  ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Show-NightlyStatus {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if (-not $task) {
    Write-Output "❌ 排程任務不存在：${TaskName}——安裝：powershell -File tools\install_windows_nightly.ps1"
    return $false
  }
  $info = $task | Get-ScheduledTaskInfo
  Write-Output "✅ 排程任務存在：${TaskName}（State=$($task.State)）"
  Write-Output "  LastRunTime    = $($info.LastRunTime)"
  Write-Output "  LastTaskResult = $($info.LastTaskResult)"
  Write-Output "  NextRunTime    = $($info.NextRunTime)"
  $s = $task.Settings
  Write-Output "  StartWhenAvailable         = $($s.StartWhenAvailable)   (expected True)"
  Write-Output "  WakeToRun                  = $($s.WakeToRun)   (expected True)"
  Write-Output "  DisallowStartIfOnBatteries = $($s.DisallowStartIfOnBatteries)   (expected False)"
  Write-Output "  StopIfGoingOnBatteries     = $($s.StopIfGoingOnBatteries)   (expected False)"
  return $true
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
