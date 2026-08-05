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
  ① AutoClaude_Nightly      每日 $NightlyAt → AutoClaude/tools/run_local_nightly.ps1
  ② AutoClaude_WindowsSmoke 每日 $SmokeAt   → tools/windows_smoke_local.ps1
  🔴 R73（DEF-101-779）：時間改由參數提供；本檔原先把兩個時刻寫死在程式碼裡，
  **預設值一律見 param 區塊**（那裡有取捨 WHY）；**現行排程一律現查**
  `Get-ScheduledTask ... | Get-ScheduledTaskInfo`——本段刻意不寫任何 HH:mm 字面值。
  🔴 R73 二審訂正（DEF-101-781）：本段初版把兩個 param 預設值逐字抄了一份進來，
  其中 ② 抄錯（與 param 區塊實際值不符），且同段又寫「預設值＝本機現行實況」——與 param 區塊
  「之所以**不**把兩個預設都設成現行實況」直接互相打臉。方向還是危險側：讀檔頭的人
  會以為不帶參數跑不動 smoke，實際會把它搬走。**這是 DEF-101-779 要治的同一個病，
  在同一支檔、同一個 commit 內當場重生**（Architect 與 SA 二審獨立命中）。
  故本段改為零時刻字面，並由 `test_install_windows_nightly.py` 上鎖釘住——
  「不寫死」若只靠自律，第三次還會長回來。
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
既有的 install／-Status／-WhatIf 冪等骨架，`-WhatIf` 更可在不等排定時刻、不動使用者機器
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
  [switch]$Status,
  # 🔴 R73（DEF-101-779）：觸發時間必須可傳入，且**預設值＝本機現行實況**。
  #
  # WHY 這是 P0 而非美化：本檔 install 路徑是 Unregister→Register（見下方），而時間
  # 原本寫死 nightly='02:00'／smoke='01:00'。而本機實際排程是 nightly 22:30／
  # smoke 23:30（R73 以 `Get-ScheduledTask | Get-ScheduledTaskInfo` 實測 NextRunTime
  # 為 08-04 22:30 與 08-04 23:30）。於是形成一個**陷阱**：
  #   ADR-SD09-012 早已指出本機五項排程設定沒套上（ExecutionTimeLimit=PT72H 應為 PT4H、
  #   MultipleInstances=IgnoreNew 應為 StopExisting ×2、smoke LogonType=Interactive
  #   應為 S4U），而要套上就得跑本安裝器——**跑下去卻會把時間靜默改回 02:00/01:00**。
  #   「修 A 的唯一途徑會破壞 B，且 B 的破壞無聲」＝沒有人敢執行的修復指令，
  #   這正是那五項設定經 R71、R72 兩輪仍原封不動的機械原因。
  # 預設值的取法（R73 定案，兩個約束在此交會）：
  #   · `$NightlyAt = '22:30'`＝**本機現行實況**，不帶參數跑不會動到 nightly。
  #   · `$SmokeAt = '21:30'`＝**回復被鎖住的設計不變量**「smoke 早於 nightly」。
  #     本機現行 smoke 是 23:30（晚於 nightly），與該不變量相反；而該不變量有明文機械鎖
  #     （`tools/tests/test_install_windows_nightly.py::
  #     test_smoke_task_shares_catchup_settings_and_runs_before_nightly`，斷言
  #     smoke_at < nightly_at，WHY＝smoke 是 88 秒的便宜 tripwire、nightly 是 5.6 分鐘的
  #     七軌深度回歸，機器當晚只醒一小段時間時先跑完便宜那支才有意義）。
  #     🔴 兩者衝突時挑**被鎖住的那一邊**：鎖是經過論證並機械強制的產物，現行 23:30
  #     則是沒有任何文件解釋的手動漂移（R73 全庫實查，找不到把 smoke 改到 nightly
  #     之後的理由）。若要維持現況請顯式傳 `-SmokeAt 23:30`——但那會讓上述鎖與現場
  #     再度脫節，屆時應改的是鎖與其 WHY，不是靜默放著。
  # 之所以不把兩個預設都設成現行實況：那會讓 `-SmokeAt` 的預設值主動違反一條 active 的
  # 鎖，等於用預設值把技術債固化進安裝器（且下一輪的人會以為那是設計）。
  [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
  [string]$NightlyAt = '22:30',
  [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
  [string]$SmokeAt = '21:30',
  # 🔴 R73 二審補（DEF-101-782）：「smoke 早於 nightly」在參數化**之前**是由寫死的字面值
  # 由構造保證的；參數化之後，該不變量只剩一條 python 靜態鎖在看 **param 預設值**，
  # 真實安裝路徑（使用者顯式傳參）**完全無人看管**——而本檔自己有兩處在建議
  # `-SmokeAt 23:30`（＝直接違反它）。不變量降級成「只有預設值遵守」是本輪新開的洞。
  # 修法＝把檢查放到 runtime，並提供**顯式**旁路：要違反可以，但必須說出口。
  [switch]$AllowSmokeAfterNightly
)

$ErrorActionPreference = 'Stop'

# ── 不變量 runtime 守門（R73 二審／DEF-101-782）：smoke 必須早於 nightly ────────────
# WHY 見 $AllowSmokeAfterNightly 上方註解。判準與 python 靜態鎖同語意（該鎖看 param
# 預設值、本段看**實際生效值**），兩者合起來才涵蓋「預設」與「顯式傳參」兩條路。
# 刻意用字串直接比較而非 ParseExact：`HH:mm` 零填補後字典序 == 時序，且 ValidatePattern
# 已保證格式，省掉一個會因 culture 而變的 API（本 repo 對 culture 敏感 API 有前例教訓）。
if (-not $AllowSmokeAfterNightly -and ($SmokeAt -ge $NightlyAt)) {
  Write-Host "❌ SMOKE-AFTER-NIGHTLY：smoke ($SmokeAt) 未早於 nightly ($NightlyAt)。" -ForegroundColor Red
  Write-Host '   WHY：smoke 是便宜的 tripwire（實測 88 秒）、nightly 是深度回歸（實測 5 分 38 秒）；' -ForegroundColor Red
  Write-Host '        機器當晚只醒一小段時間時，先跑完便宜那支才有意義。' -ForegroundColor Red
  Write-Host '   確定要這個順序請顯式加 -AllowSmokeAfterNightly（要違反可以，但必須說出口）。' -ForegroundColor Yellow
  exit 1
}

$TaskName = 'AutoClaude_Nightly'
# R60（DEF-101-517 backlog 收斂）：Windows smoke 補償控制的獨立任務。名稱沿用既有
# `AutoClaude_*` 前綴慣例。
# R69 訂正：此處原記載「同機另有 AutoClaude_Nightly／AutoClaude_SD09_G0_GateCheck」。
# AutoClaude_SD09_G0_GateCheck 已於 R69 移除——它是一次性 TimeTrigger，2026-06-29
# 觸發一次（結論 [G0-NOT-READY]）後 NextRunTime 永遠空白，此後 34 天零檢查，是死排程。
# G0 三軌判定已改由每晚都會跑的 run_local_nightly.ps1 收尾區塊印出（[G0-READY] /
# [G0-NOT-READY]）。腳本 AutoClaude/tools/g0_gate_check.ps1（人工隨時複查）**保留**，不再有
# 常駐排程任務。R76 訂正：原寫「兩支腳本」，reschedule_g0_gatecheck.ps1 已刪＝真孤兒。
# 本 installer 從未管理 G0 任務，故無需新增移除邏輯——它只管 Nightly + WindowsSmoke。
$SmokeTaskName = 'AutoClaude_WindowsSmoke'
$ScriptDir = $PSScriptRoot
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir '..'))
$NightlyPs1 = Join-Path $RepoRoot 'AutoClaude\tools\run_local_nightly.ps1'
$SmokePs1 = Join-Path $RepoRoot 'tools\windows_smoke_local.ps1'
# 排序設計意圖：smoke 是便宜的 tripwire（PASS=12，R73 隨選觸發實測 **88 秒**），
# nightly 是七軌深度回歸（R73 由 8/3 22:30 那輪 log 實測 **5 分 38 秒**）。若機器當晚
# 只醒著很短的時間，先跑完便宜那支才是對的順序；兩支彼此無資料相依（smoke 全在 OS
# temp 內建 fake repo）。
# 🔴 R73 誠實揭露（DEF-101-779）：**本機現行排程違反上述意圖**——實測 nightly 22:30、
# smoke 23:30，smoke 落在 nightly 之**後**一小時。因此照本檔預設值安裝會把 smoke 從
# 23:30 移到 21:30（nightly 22:30 不變），這是**刻意的**：該順序有 active 機械鎖，
# 取捨理由見 param 區塊。要維持現行 23:30 請顯式傳 `-SmokeAt 23:30`。
# （$NightlyAt／$SmokeAt 現由 param 區塊提供，不再於此寫死。）

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
  # R69（S-5）：這三項是 2026-08-01/02 漏跑事故的直接成因，必須在 -Status 就看得見，
  # 否則「installer 把 S4U 降級成 Interactive」這種回歸只能等下次漏跑才被發現。
  # MultipleInstancesPolicy 刻意讀 XML 而非 $s.MultipleInstances：後者對 StopExisting
  # （值 3）會印**空白**，空白會被誤讀成沒設定（見 Set-MultipleInstancesStopExisting 註解）。
  Write-Output "  LogonType                  = $($task.Principal.LogonType)   (expected S4U — Interactive 在使用者未登入時整輪不跑)"
  Write-Output "  ExecutionTimeLimit         = $($s.ExecutionTimeLimit)   (expected PT4H)"
  $policy = try { ([xml](Export-ScheduledTask -TaskName $Name)).Task.Settings.MultipleInstancesPolicy } catch { '<unreadable>' }
  Write-Output "  MultipleInstancesPolicy    = ${policy}   (expected StopExisting)"
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

# R69（S-5，P0 回歸源）：明確指定 -Principal。
# WHY：本檔的 install 路徑是「存在就 Unregister 再 Register」，而原本**不帶
# -Principal** → Register-ScheduledTask 套用預設的 Interactive 登入類型。後果是
# 任何人跑一次 installer，就把已經是 S4U 的 AutoClaude_Nightly **降級成 Interactive**
# ——installer 自己是回歸源。Interactive 的任務在「符合啟動條件時使用者未登入」
# 會整輪不跑：2026-08-02 實測 AutoClaude_WindowsSmoke 正是此形態（事件 332
# 「由於符合啟動條件時使用者…並未登入，工作排程器並未啟動工作」、
# NumberOfMissedRuns=1），而同機 AutoClaude_Nightly 是 S4U 就沒這問題。
# S4U（Service For User）＝以該使用者身分執行但**不需其登入、也不需存密碼**，正是
# 無人值守 nightly 的正確選擇；RunLevel 維持 Limited（兩支載體都不需要提權）。
# ⚠️ 註冊 S4U 任務需要系統管理員權限（實測非提權時 Access is denied），這與本檔
# 既有的 Test-IsAdmin 守門一致，不新增額外前提。
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType S4U -RunLevel Limited

# R69（S-5）：MultipleInstances=StopExisting 只能走 COM，**不能**走 ScheduledTasks 模組。
# 這是 DEF-101-249（建構 cmdlet 參數名 vs 物件屬性名不一致）的加強版：這次不是名字
# 不同，而是**模組根本表達不出這個值**。實測（真機三次）：把該值傳給
# New-ScheduledTaskSettingsSet 的 MultipleInstances 參數，或直接指派數值 3 給
# $t.Settings.MultipleInstances，兩者都被 enum 轉型擋下，錯誤訊息明列可用值只有
# "Parallel,Queue,IgnoreNew"。
# （本註解刻意不寫出「該參數名＋該值」相鄰的字面組合：測試以字面反向鎖掃描全檔，
#   在註解裡示範錯誤寫法會誤觸自己的鎖——本輪已實際踩過一次。）
# 也就是 Task Scheduler XML schema 有 StopExisting，但 PowerShell 產生的
# MultipleInstancesEnum 漏了它。唯一可行路徑是 Schedule.Service COM 物件直接寫
# 數值 3（TASK_INSTANCES_STOP_EXISTING）後以 TASK_UPDATE(4) 旗標重新註冊。
# 驗證方式必須用 Export-ScheduledTask 讀 XML 的 MultipleInstancesPolicy——
# `Get-ScheduledTask ... | Select MultipleInstances` 對值 3 會印**空白**（enum 找不到
# 對應名稱），空白極易被誤讀成「沒設成功」（本輪實測踩過這個坑）。
# 為何仍要設：ExecutionTimeLimit=PT4H 已能解決「凍住實例吃掉隔日觸發」，
# StopExisting 是第二道防線（4 小時內就再次觸發的邊角情境）。失敗不致命，故只 Warning。
function Set-MultipleInstancesStopExisting {
  param([Parameter(Mandatory = $true)][string]$Name)
  try {
    $svc = New-Object -ComObject Schedule.Service
    $svc.Connect()
    $folder = $svc.GetFolder('\')
    $def = $folder.GetTask($Name).Definition
    $def.Settings.MultipleInstances = 3
    $null = $folder.RegisterTaskDefinition(
      $Name, $def, 4, $def.Principal.UserId, $null, $def.Principal.LogonType)
    $policy = ([xml](Export-ScheduledTask -TaskName $Name)).Task.Settings.MultipleInstancesPolicy
    if ($policy -eq 'StopExisting') {
      Write-Output "   MultipleInstances=StopExisting 已套用（XML 實測 MultipleInstancesPolicy=$policy）"
    } else {
      Write-Warning "MultipleInstances 設定後回讀為 '${policy}'（預期 StopExisting）——${Name} 仍靠 ExecutionTimeLimit 兜底。"
    }
  } catch {
    Write-Warning "MultipleInstances=StopExisting 套用失敗（${Name}）：$($_.Exception.Message)。ExecutionTimeLimit=PT4H 仍生效，不阻斷安裝。"
  }
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"${NightlyPs1}`""
$trigger = New-ScheduledTaskTrigger -Daily -At $NightlyAt
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
# R69（S-5，DEF-101-249 同型第二例）：補 -ExecutionTimeLimit。
# WHY：預設 ExecutionTimeLimit 是 PT72H（3 天）。2026-08-01 那輪 nightly 在
# sdd-fsm-chaos 執行中機器進入睡眠，整個實例被凍住 35.6 小時仍在 72 小時額度內
# → 隔日 02:00 觸發被 MultipleInstances 擋掉（事件 322「相同工作的執行個體已在
# 執行中」）→ 該日觀察期三軌全部零進帳。正常整輪 5~8 分鐘，PT4H 已極寬鬆，
# 卻能把「凍住的實例」在 4 小時後強制收掉，隔日觸發就不再被吃掉。
# 參數型別是 TimeSpan（不是 'PT4H' 字串——字串會綁定失敗），故用 New-TimeSpan。
$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -WakeToRun `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 4)

if ($PSCmdlet.ShouldProcess($TaskName, 'Register-ScheduledTask')) {
  $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal `
    -Description 'AutoClaude nightly 本地聚合驗證（見 AutoClaude/tools/run_local_nightly.ps1）' | Out-Null
  Set-MultipleInstancesStopExisting -Name $TaskName
  Write-Output "✅ 已安裝並註冊排程任務：${TaskName}（每日 ${NightlyAt} → ${NightlyPs1}）"
  Write-Output "   另含 StartWhenAvailable/WakeToRun 補跑保護（關機/睡眠錯過仍可補跑）"
  Write-Output "   LogonType=S4U（使用者未登入也會跑）；ExecutionTimeLimit=PT4H（凍住的實例不會吃掉隔日觸發）"
}
if ($PSCmdlet.ShouldProcess($SmokeTaskName, 'Register-ScheduledTask')) {
  $smokeExisting = Get-ScheduledTask -TaskName $SmokeTaskName -ErrorAction SilentlyContinue
  if ($smokeExisting) {
    Unregister-ScheduledTask -TaskName $SmokeTaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $SmokeTaskName -Action $smokeAction -Trigger $smokeTrigger `
    -Settings $settings -Principal $principal `
    -Description 'AutoClaude Windows smoke 執行級補償控制（見 tools/windows_smoke_local.ps1；DEF-101-139/517）' | Out-Null
  Set-MultipleInstancesStopExisting -Name $SmokeTaskName
  Write-Output "✅ 已安裝並註冊排程任務：${SmokeTaskName}（每日 ${SmokeAt} → ${SmokePs1}）"
  Write-Output "   這是 CI 停擺期間 Windows 側唯一的執行級活體驗證管道，此前只能手動觸發"
}
Write-Output "   驗證：powershell -File tools\install_windows_nightly.ps1 -Status"
exit 0
