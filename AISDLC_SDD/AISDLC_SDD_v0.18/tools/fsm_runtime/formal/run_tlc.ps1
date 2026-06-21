# Phase G M5 / ACT-042 / B5.6 — TLC runner (Windows / PowerShell)
#
# 用途：本機開發者在 Windows 跑 TLC 對 SDD_FSM.tla 做形式化驗證。
# 對應規則：CLAUDE.md Rule 9.18.1~9.18.4
#
# 使用：
#   pwsh run_tlc.ps1                    # 跑完整驗證
#   pwsh run_tlc.ps1 -InstallOnly       # 僅下載 tla2tools.jar
#   pwsh run_tlc.ps1 -Depth 100         # 自訂探索深度上限
#
# Exit codes：
#   0 — 全部通過
#   1 — TLC 偵測 invariant / liveness violation / deadlock
#   2 — 環境錯誤

[CmdletBinding()]
param(
    [switch]$InstallOnly,
    [int]$Depth = 50,
    [string]$TlaVersion = "v1.8.0"
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$LibDir = Join-Path $ScriptDir "lib"
$JarPath = Join-Path $LibDir "tla2tools.jar"
$JarUrl = "https://github.com/tlaplus/tlaplus/releases/download/$TlaVersion/tla2tools.jar"

# Step 1 — 環境檢查
$javaCmd = Get-Command java -ErrorAction SilentlyContinue
if (-not $javaCmd) {
    Write-Host "ERROR: java not found. Install JDK 11+ first." -ForegroundColor Red
    exit 2
}
Write-Host "[run_tlc] Java: $((& java -version 2>&1) | Select-Object -First 1)"

# Step 2 — 下載 tla2tools.jar
if (-not (Test-Path $LibDir)) { New-Item -ItemType Directory -Path $LibDir | Out-Null }
if (-not (Test-Path $JarPath)) {
    Write-Host "[run_tlc] tla2tools.jar 不存在，從 $JarUrl 下載..."
    try {
        Invoke-WebRequest -Uri $JarUrl -OutFile $JarPath -UseBasicParsing
    } catch {
        Write-Host "ERROR: 下載失敗：$_" -ForegroundColor Red
        exit 2
    }
    $size = (Get-Item $JarPath).Length
    Write-Host "[run_tlc] 下載完成：$([math]::Round($size/1MB, 2)) MB"
}

if ($InstallOnly) {
    Write-Host "[run_tlc] -InstallOnly：完成。"
    exit 0
}

# Step 3 — 跑 TLC
Push-Location $ScriptDir
try {
    $LogFile = Join-Path $ScriptDir "tlc_run.log"
    Write-Host "[run_tlc] Running TLC with depth=$Depth..."

    & java "-XX:+UseParallelGC" -cp $JarPath tlc2.TLC `
        -config SDD_FSM.cfg `
        -workers auto `
        -depth $Depth `
        SDD_FSM.tla *>&1 | Tee-Object -FilePath $LogFile | Out-Null
    $TlcExit = $LASTEXITCODE

    # Step 4 — 解析結果
    Write-Host "[run_tlc] TLC 退出碼: $TlcExit"
    Write-Host "[run_tlc] 完整 log: $LogFile"

    # QA 修 1：non-anchored regex（TLC 輸出 "2853 states generated, 583 distinct states found, ..."
    # 與 "The depth of the complete state graph search is 29." — 數字非行首）
    $logContent = Get-Content $LogFile -Raw
    $distinct = if ($logContent -match '(\d+)\s+distinct\s+states\s+found') { $matches[1] } else { "0" }
    $generated = if ($logContent -match '(\d+)\s+states\s+generated') { $matches[1] } else { "0" }
    $depth = if ($logContent -match 'depth of the complete state graph search is\s+(\d+)') { $matches[1] } else { "0" }

    Write-Host "[run_tlc] distinct states: $distinct"
    Write-Host "[run_tlc] generated states: $generated"
    Write-Host "[run_tlc] depth: $depth"

    # Machine-readable summary（CI assertion 直接 grep）
    Write-Host "TLC_DISTINCT=$distinct"
    Write-Host "TLC_GENERATED=$generated"
    Write-Host "TLC_DEPTH=$depth"

    if ($TlcExit -eq 0) {
        Write-Host "[run_tlc] OK TLC 驗證通過" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[run_tlc] FAIL TLC 驗證失敗（見 log 上方錯誤訊息）" -ForegroundColor Red
        Get-Content $LogFile -Tail 30
        exit 1
    }
} finally {
    Pop-Location
}
