<#
.SYNOPSIS
dev_start wrapper（Windows）。macOS/Linux 對等：tools/dev_start.sh

.DESCRIPTION
  邏輯全部集中在 tools/dev_start.py（跨平台單一事實源；本對 .sh/.ps1 為薄殼，
  業務邏輯零漂移面；薄殼樣板本身無機械比對，改動須人工同步 .sh）。本檔只做三件事：
    選直譯器（.venv 形狀正確優先，否則 py launcher / python）→ 轉呼叫核心 → 視需要啟用 venv。

.EXAMPLE
  . tools\dev_start.ps1        # 推薦：dot-source，核心完成後自動啟用 .venv
  powershell -ExecutionPolicy Bypass -File tools\dev_start.ps1   # 僅執行整備

.NOTES
  dot-source 呼叫端判斷成功/失敗請讀 $LASTEXITCODE，不要用 $?：
  dot-source 後任何「執行成功」的陳述式（包含本檔內 `$rc = $LASTEXITCODE` 這行賦值本身）
  都會把 $? 重設為 $true，導致 $? 無法反映核心邏輯（tools\dev_start.py）的真實結果。
#>
[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$RestArgs = @())

$Root = Split-Path -Parent $PSScriptRoot
# dot-source 偵測：dot-sourced 時絕不可 exit（會關掉使用者 shell），一律 return
$DotSourced = $MyInvocation.InvocationName -eq '.'
if (-not $Root) {
  # 只有 script 不在 <repo>/tools/ 下時會發生（如被複製到磁碟根）；fail loud 防連鎖怪錯
  Write-Host "❌ 無法解析 repo 根（本腳本必須位於 <repo>/tools/ 下執行）" -ForegroundColor Red
  if ($DotSourced) { $global:LASTEXITCODE = 1; return }
  exit 1
}
$Core = Join-Path $Root 'tools\dev_start.py'
$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'

$Py = $null
if (Test-Path $VenvPy) { $Py = $VenvPy }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $Py = 'py' }
else {
  # 排除 Windows Store App Execution Alias stub（未真裝 Python 時 python.exe
  # 是開商店的假直譯器）；兩步式取 .Source（紀律 #14）
  $PyCand = Get-Command python -ErrorAction SilentlyContinue
  if ($PyCand -and $PyCand.Source -notlike '*\WindowsApps\*') { $Py = 'python' }
}

if (-not $Py) {
  Write-Host "❌ 找不到 Python 直譯器（dev_start 核心需 Python 3）。" -ForegroundColor Red
  Write-Host "   Windows 安裝建議：winget install Python.Python.3.11（或 winget install astral-sh.uv）" -ForegroundColor Yellow
  if ($DotSourced) { $global:LASTEXITCODE = 1; return }
  exit 1
}

& $Py $Core @RestArgs
# ⚠️ rc 語意陷阱（dot-source 專屬，PowerShell 語言本身如此、無法在腳本內修正）：
# 下一行賦值陳述式本身「執行成功」，會把 $? 重設為 $true——即使 $LASTEXITCODE 存的是失敗值。
# 因此呼叫端（尤其未來自動化 wrapper）判斷本腳本成功/失敗務必讀 $LASTEXITCODE，不可用 $?。
$rc = $LASTEXITCODE

if ($DotSourced) {
  $Act = Join-Path $Root '.venv\Scripts\Activate.ps1'
  if ($rc -eq 0 -and (Test-Path $Act)) {
    . $Act
    # 兩步式取 .Source（紀律 #14：StrictMode 下禁 (Get-Command …).<Prop> 鏈式）
    $PyCmd = Get-Command python -ErrorAction SilentlyContinue
    $PyNow = if ($PyCmd) { $PyCmd.Source } else { '(unknown)' }
    Write-Host "✅ 已自動啟用 .venv（python → $PyNow）" -ForegroundColor Green
  } elseif ($rc -eq 0) {
    Write-Host "⚠️  .venv\Scripts\Activate.ps1 不存在，未啟用 venv" -ForegroundColor Yellow
  }
  return
}

if ($rc -eq 0) {
  Write-Host "ℹ️  以 -File 執行不會影響當前 shell — 請自行：.venv\Scripts\Activate.ps1（或改用 . tools\dev_start.ps1）"
}
exit $rc
