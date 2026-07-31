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

本安裝器管理的是一**組**任務（不是單一任務），四個模式一律作用於整組：
  ① AutoClaude_Nightly      每日 02:00 → AutoClaude/tools/run_local_nightly.ps1
  ② AutoClaude_WindowsSmoke 每日 01:00 → tools/windows_smoke_local.ps1
R60 新增 ②，收斂 DEF-101-517 的 backlog（該列明文交棒「下一輪先評估較便宜的兩條
路徑」，本輪落地其中的路徑①）。WHY 必須自動觸發：`windows_smoke_local.ps1` 正是
DEF-101-139 為「雲端 CI 帳務停擺（DEF-101-081）」而建的 Windows 側**執行級補償
控制**，而 R59 逐項實測確認 run_local_nightly.ps1 對它零呼叫、它只能手動觸發——
補償控制自己沒有心跳（這也解釋了它為何會腐化到讓 R59 踩到 DEF-101-511）。對照 mac
側：`run_local_nightly.sh` 的 [1/4] 每日自動跑 `macos_smoke_local.sh`，故「smoke 每天
自動跑一次」在 mac 早已成立，Windows 缺的就是這個。
刻意**不**把 smoke 塞成 run_local_nightly.ps1 的第 8 個 stage：那需同動 summary 行／
summary JSON／exit-decision 清單／Format-Rc 標籤共四處，而 summary 行被
tools/dev_start.py 的心跳哨兵以跨檔字面正則解析（DEF-101-263②／R25 已建跨檔字面鎖），
改動 summary 契約會連帶動到那組鎖。獨立任務與 nightly summary **零耦合**，且沿用本檔
既有的 install／-Status／-WhatIf 冪等骨架，`-WhatIf` 更可在不等 02:00、不動使用者機器
狀態的前提下當場取得驗證證據。
心跳從哪裡讀：Windows 側不另造心跳檔——`-Status` 讀 Get-ScheduledTaskInfo 的
LastRunTime／LastTaskResult 即為兩支任務各自的心跳（語意對應 mac 版讀心跳檔 mtime，
實作不同，如實揭露、不勉強模擬）。

.PARAMETER Uninstall
移除本安裝器管理的整組排程任務（冪等：不存在也視為成功）。

.PARAMETER Status
查詢整組排程任務目前狀態（存在與否、上次執行結果、下次執行時間、補跑保護設定），
不做任何變更。Windows工作排程器原生以 Get-ScheduledTaskInfo 提供「上次執行時間」，
取代 mac 版讀心跳檔案 mtime 的機制——兩者語意對應但實作不同，如實揭露、不勉強模擬。
結束代碼：整組任務**全部**存在＝0；任一缺席＝1（語意對齊 mac 版 --status，DEF-101-248）。

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
# R60（DEF-101-517 backlog 收斂）：Windows smoke 補償控制的獨立任務。名稱沿用既有
# `AutoClaude_*` 前綴慣例（同機另有 AutoClaude_Nightly／AutoClaude_SD09_G0_GateCheck）。
$SmokeTaskName = 'AutoClaude_WindowsSmoke'
$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))
$NightlyPs1 = Join-Path $RepoRoot 'AutoClaude\tools\run_local_nightly.ps1'
$SmokePs1 = Join-Path $RepoRoot 'tools\windows_smoke_local.ps1'
# smoke 排在 nightly 之前一小時：smoke 是便宜的 tripwire（PASS=12，數分鐘量級），
# nightly 是七軌深度回歸（含 mutation，小時量級）。若機器當晚只醒著很短的時間，
# 先跑完便宜那支才是對的順序；兩支彼此無資料相依（smoke 全在 OS temp 內建 fake repo）。
$SmokeAt = '01:00'

function Test-IsAdmin {
  ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-TaskPresent {
  <#
  純查詢，**零輸出**——存在性判定必須與「印報表」分離。
  DEF-101-542（R60 實測）：原本 Show-NightlyStatus 一支函式同時 Write-Output 報表
  又 `return $true/$false`，而 PowerShell 會把函式內**所有**輸出串一起當回傳值，於是
  `$loaded = Show-NightlyStatus` 拿到的是 Object[]（報表字串 + 布林），`if ($loaded)`
  對非空陣列恆為真 ⇒ `-Status` 不論任務存不存在都 exit 0，DEF-101-248 的修復被
  語意打敗（實測：把 $TaskName 換成不存在的名字後跑 -Status，REAL_EXITCODE=0）。
  分離「純函式」與「印出函式」是本 repo 既有慣例（見 tools/run_root_unittests.py 的
  windows_native_skips ／ report_windows_native_skips，理由同構）。
  #>
  param([Parameter(Mandatory = $true)][string]$Name)
  $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  return [bool]$t
}

function Show-TaskDetail {
  # 只印報表，**刻意不回傳任何值**（回傳值由 Test-TaskPresent 負責，見其註解）。
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Role
  )
  $task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
  if (-not $task) {
    Write-Output "❌ 排程任務不存在：${Name}（${Role}）——安裝：powershell -File tools\install_windows_nightly.ps1"
    return
  }
  $info = $task | Get-ScheduledTaskInfo
  Write-Output "✅ 排程任務存在：${Name}（${Role}；State=$($task.State)）"
  Write-Output "  LastRunTime    = $($info.LastRunTime)"
  Write-Output "  LastTaskResult = $($info.LastTaskResult)"
  Write-Output "  NextRunTime    = $($info.NextRunTime)"
  $s = $task.Settings
  Write-Output "  StartWhenAvailable         = $($s.StartWhenAvailable)   (expected True)"
  Write-Output "  WakeToRun                  = $($s.WakeToRun)   (expected True)"
  Write-Output "  DisallowStartIfOnBatteries = $($s.DisallowStartIfOnBatteries)   (expected False)"
  Write-Output "  StopIfGoingOnBatteries     = $($s.StopIfGoingOnBatteries)   (expected False)"
}

function Show-NightlyStatus {
  # 印整組任務的報表；同上，**不回傳值**。
  Show-TaskDetail -Name $TaskName -Role 'nightly 七軌深度回歸'
  Show-TaskDetail -Name $SmokeTaskName -Role 'Windows smoke 執行級補償控制（DEF-101-139/517）'
}

if ($Status) {
  if ($Uninstall) {
    Write-Warning "-Status 與 -Uninstall 同時給出，-Uninstall 已被忽略（僅查詢狀態，不做任何變更）。"
  }
  Show-NightlyStatus
  $loaded = (Test-TaskPresent -Name $TaskName) -and (Test-TaskPresent -Name $SmokeTaskName)
  if ($loaded) { exit 0 } else { exit 1 }
}

if ($Uninstall) {
  if (-not (Test-IsAdmin) -and -not $WhatIfPreference) {
    Write-Warning "需要系統管理員權限——請以「以系統管理員身分執行」重新開啟 PowerShell 後再跑本腳本。"
    exit 1
  }
  foreach ($name in @($TaskName, $SmokeTaskName)) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($PSCmdlet.ShouldProcess($name, 'Unregister-ScheduledTask')) {
      if ($existing) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Output "✅ 已解除安裝：移除排程任務 ${name}"
      } else {
        Write-Output "✅ 無事可做：${name} 不存在（冪等）"
      }
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

# 兩支載體（nightly／smoke）的存在性檢查都收斂在 install 分支內部，刻意不與
# -Uninstall 共用：DEF-101-619（R66 實機重現）——修復前 $NightlyPs1 的存在性檢查
# 放在 $Uninstall 判斷「之前」，對 install／-Uninstall 兩路共用，使「nightly 載體
# 被刪掉」連帶讓 -Uninstall 也無法執行（scratchpad 隔離重現：REAL_EXITCODE=1），
# 與 mac 側 install_mac_nightly.sh 的 cmd_uninstall()（不檢查底層腳本是否存在）
# 行為不對稱、且違反解除安裝理應比安裝更寬容的直覺。-Uninstall 分支（上方）
# 現在完全不觸碰 Test-Path，只操作 Task Scheduler 本身。
if (-not (Test-Path -LiteralPath $NightlyPs1)) {
  Write-Error "找不到 nightly 載體：${NightlyPs1}"
  exit 1
}
if (-not (Test-Path -LiteralPath $SmokePs1)) {
  Write-Error "找不到 Windows smoke 載體：${SmokePs1}"
  exit 1
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"${NightlyPs1}`""
$trigger = New-ScheduledTaskTrigger -Daily -At '02:00'
# smoke 任務：同款原生 powershell.exe 呼叫慣例。🔴 載具必須是原生 PowerShell——
# windows_smoke_local.ps1 自 R59（DEF-101-511）起偵測到 $env:MSYSTEM 即 exit 1 拒跑，
# 因為經 Git Bash 呼叫會在非 ASCII 路徑情境產生假紅（實測 PASS=11 FAIL=2 vs 原生
# PASS=12 FAIL=0）。schtasks 直接起 powershell.exe，不經任何 msys 層，符合該要求。
$smokeAction = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"${SmokePs1}`""
$smokeTrigger = New-ScheduledTaskTrigger -Daily -At $SmokeAt
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
# 兩支任務共用同一份 $settings：四項補跑保護對 smoke 的必要性與 nightly 完全相同
# （筆電夜間睡眠／關機是同一個漏跑成因），刻意不為 smoke 另立一份而製造第二處漂移點。
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
}
if ($PSCmdlet.ShouldProcess($SmokeTaskName, 'Register-ScheduledTask')) {
  $smokeExisting = Get-ScheduledTask -TaskName $SmokeTaskName -ErrorAction SilentlyContinue
  if ($smokeExisting) {
    Unregister-ScheduledTask -TaskName $SmokeTaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $SmokeTaskName -Action $smokeAction -Trigger $smokeTrigger `
    -Settings $settings `
    -Description 'AutoClaude Windows smoke 執行級補償控制（見 tools/windows_smoke_local.ps1；DEF-101-139/517）' | Out-Null
  Write-Output "✅ 已安裝並註冊排程任務：${SmokeTaskName}（每日 ${SmokeAt} → ${SmokePs1}）"
  Write-Output "   這是 CI 停擺期間 Windows 側唯一的執行級活體驗證管道，此前只能手動觸發"
}
Write-Output "   驗證：powershell -File tools\install_windows_nightly.ps1 -Status"
exit 0
