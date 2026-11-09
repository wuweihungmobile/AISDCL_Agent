#Requires -Version 5.1
<#
.SYNOPSIS
SelfImproving 巡邏心跳包裝腳本（OS 排程器 AutoSDD_SI_Patrol 每心跳叫醒一次；TCS-SelfImproving-P4 R161 (c)）。

.DESCRIPTION
做三件事：(1) 自 AgentConsole\.env **逐行**找 CONSOLE_SI_AUDIT_KEY，只取**第一個命中行的第一把**金鑰，
只設進**本行程**的環境變數 AUTOSDD_SI_AUDIT_KEY（不整檔載入或執行、不求值任何一行、
不印、不寫日誌）；(2) 呼叫 .venv\Scripts\python.exe tools\selfimproving.py patrol（一次性心跳，巡邏
本身的結果寫 patrol.log，那是 python 端的日誌）；(3) 輪替日誌（超過上限就改名為 .1，保留三份）。
金鑰缺席（.env 不在或沒有該鍵）不是錯誤：巡邏照跑，入帳會以 AUDIT-KEY-MISSING 記錄並保留稽核檔。
引擎：PowerShell 5.1 語意（排程任務顯式 powershell.exe -NoProfile -ExecutionPolicy Bypass -File）。
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Entry = Join-Path $RepoRoot 'tools\selfimproving.py'
$EnvFile = Join-Path $RepoRoot 'AgentConsole\.env'
$SiDir = $env:AUTOSDD_SI_DIR
if (-not $SiDir) { $SiDir = Join-Path $env:USERPROFILE '.autosdd\selfimproving' }
$LogDir = Join-Path $SiDir 'patrol'
$MaxLogBytes = 1048576

function Invoke-LogRotation {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return }
  if ((Get-Item -LiteralPath $Path).Length -le $MaxLogBytes) { return }
  foreach ($n in 3, 2, 1) {
    $from = if ($n -eq 1) { $Path } else { "$Path.$($n - 1)" }
    if (Test-Path -LiteralPath $from) { Move-Item -LiteralPath $from -Destination "$Path.$n" -Force }
  }
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Invoke-LogRotation -Path (Join-Path $LogDir 'patrol.log')
Invoke-LogRotation -Path (Join-Path $LogDir 'tick.log')

if (Test-Path -LiteralPath $EnvFile) {
  foreach ($line in [System.IO.File]::ReadLines($EnvFile)) {
    if ($line -match '^\s*CONSOLE_SI_AUDIT_KEY\s*=\s*(.*)$') {
      $first = ($Matches[1].Trim().Trim('"').Trim("'") -split ',')[0].Trim()
      if ($first) { $env:AUTOSDD_SI_AUDIT_KEY = $first }
      break
    }
  }
}

$stamp = [DateTimeOffset]::Now.ToString('o')
# PS 5.1：$ErrorActionPreference='Stop' 下以 2>&1 接原生指令，python 一寫 stderr 就成終止錯誤、本心跳的
# tick.log 不落（SCG-4 一審 B-3，TCS-P4 D-IMP-8）⇒ 只在原生呼叫段放寬為 Continue，取 rc 後還原。
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$out = & $Python $Entry patrol 2>&1
$rc = $LASTEXITCODE
$ErrorActionPreference = $prevEap
$text = ($out | ForEach-Object { "$_" }) -join "`n"
[System.IO.File]::AppendAllText((Join-Path $LogDir 'tick.log'), "$stamp rc=$rc`n$text`n", (New-Object System.Text.UTF8Encoding($false)))
exit $rc
