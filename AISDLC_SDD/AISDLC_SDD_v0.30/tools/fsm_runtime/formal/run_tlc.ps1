# Phase G M5 / ACT-042 / B5.6 — TLC runner (Windows / PowerShell)
#
# ⚠️ LEGACY 兩軌快驗（v0.02 / DEF-01-002 註記；R9 Fix-A 鏡射 run_tlc.sh 補齊）：
#    本腳本僅實裝 SDD_FSM + FLEET_FSM 兩軌。五軌完整驗證
#    （SDD/META/COMPOSITION/OPTIMIZATION/FLEET_FSM）請走 Python 真相源：
#    python -m tools.fsm_runtime.tlc_runner --module <五軌各一>
#    （scripts/ci-gate.sh --full-tlc 即以迴圈呼叫五軌）。
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

# R9 SD 二審 D-1（DEF-101-124）：本腳本的 native stderr 重定向模式（java -version 2>&1、
# TLC *>&1 | Tee-Object）在 Windows PowerShell 5.1 + $ErrorActionPreference=Stop 下會把
# stderr 行包成 ErrorRecord 拋 NativeCommandError（於下方 Java 版本行即中斷，永遠跑不到
# TLC）——此為既有限制，pwsh 7+ 無此行為。與其讓使用者撞難解錯誤，這裡明確 fail-loud 導流。
if ($PSVersionTable.PSVersion.Major -lt 6) {
    Write-Host "ERROR: 本腳本需 pwsh 7+（PowerShell 5.1 對 native stderr 的 ErrorRecord 包裝會在 Java 檢查行中斷）。" -ForegroundColor Red
    Write-Host "  替代：bash tools/fsm_runtime/formal/run_tlc.sh，或五軌權威路徑 python -m tools.fsm_runtime.tlc_runner" -ForegroundColor Yellow
    exit 2
}

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

    if ($TlcExit -ne 0) {
        Write-Host "[run_tlc] FAIL SDD_FSM TLC 驗證失敗（見 log 上方錯誤訊息）" -ForegroundColor Red
        Get-Content $LogFile -Tail 30
        exit 1
    }
    Write-Host "[run_tlc] OK SDD_FSM TLC 驗證通過（safety + EventuallyTerminal + ObservationsTransient）" -ForegroundColor Green

    # Step 5 — Phase I M5 / ACT-072：parametric FLEET_FSM（艦隊並行 no-deadlock + bounded join）
    # （R9 Fix-A 鏡射 run_tlc.sh Step 5a/5b 補齊——先前 .ps1 相對 .sh 漂移，缺整條 FLEET_FSM 軌）
    # 5a：safety（含 SYMMETRY 縮減狀態空間）；5b：liveness（無 SYMMETRY，健全前提）
    # 為何分兩跑：TLC 在 SYMMETRY 下檢查 liveness 屬 unsound（可能漏掉違規），故 AllEventuallyDone
    # 必在無 symmetry 的 FLEET_FSM_LIVENESS.cfg 窮舉驗證。
    $FleetLog = Join-Path $ScriptDir "fleet_tlc.log"
    $FleetLiveLog = Join-Path $ScriptDir "fleet_tlc_liveness.log"
    Write-Host "[run_tlc] Running FLEET_FSM TLC 5a (safety + symmetry: LockMutex/NoPartialHold)..."
    & java "-XX:+UseParallelGC" -cp $JarPath tlc2.TLC `
        -config FLEET_FSM.cfg `
        -workers auto `
        FLEET_FSM.tla *>&1 | Tee-Object -FilePath $FleetLog | Out-Null
    $FleetExit = $LASTEXITCODE
    if ($FleetExit -ne 0) {
        Write-Host "[run_tlc] FAIL FLEET_FSM safety 驗證失敗（見 $FleetLog）" -ForegroundColor Red
        Get-Content $FleetLog -Tail 30
        exit 1
    }
    Write-Host "[run_tlc] OK FLEET_FSM safety 通過（LockMutex + NoPartialHold）" -ForegroundColor Green

    Write-Host "[run_tlc] Running FLEET_FSM TLC 5b (liveness, NO symmetry: AllEventuallyDone)..."
    & java "-XX:+UseParallelGC" -cp $JarPath tlc2.TLC `
        -config FLEET_FSM_LIVENESS.cfg `
        -workers auto `
        FLEET_FSM.tla *>&1 | Tee-Object -FilePath $FleetLiveLog | Out-Null
    $FleetLiveExit = $LASTEXITCODE
    if ($FleetLiveExit -eq 0) {
        Write-Host "[run_tlc] OK FLEET_FSM liveness 通過（AllEventuallyDone，無 symmetry 健全驗證）" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[run_tlc] FAIL FLEET_FSM liveness 驗證失敗（見 $FleetLiveLog）" -ForegroundColor Red
        Get-Content $FleetLiveLog -Tail 30
        exit 1
    }
} finally {
    Pop-Location
}
