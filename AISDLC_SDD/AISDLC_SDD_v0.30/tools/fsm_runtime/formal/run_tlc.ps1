# Phase G M5 / ACT-042 / B5.6 — TLC runner (Windows / PowerShell)
#
# 🔴 R65（ADR-XPLAT-002 §5 Phase 2-A）：本檔改為薄殼，實際 TLC 呼叫／摘要解析／
#    jar 下載邏輯全數委派 Python 真相源 tools.fsm_runtime.tlc_runner；本檔只負責
#    (1) 找可用 python (2) 解析既有命令列慣例並原樣轉傳 (3) 依既有三軌流程
#    （SDD_FSM 完整 + FLEET_FSM safety + FLEET_FSM liveness）依序呼叫、任一階段
#    rc 非 0 立即中止並原樣回傳。原「需 pwsh 7+」限制（PS 5.1 對 native stderr 的
#    ErrorRecord 包裝在 `java ... *>&1 | Out-File` 這種重定向下會中斷）隨薄殼化
#    解除——本檔不再自行對 java 做重定向，觸發條件已不存在：Python subprocess
#    自行內部捕捉 stdout/stderr，PowerShell 端僅原樣呼叫一支外部命令並讀
#    $LASTEXITCODE。五軌完整驗證另可直接：
#      python -m tools.fsm_runtime.tlc_runner --module <五軌各一>
#
# 🔴 R65 修復（四方複審 MAJOR）：裸執行（非 -InstallOnly）三軌呼叫恆帶 --download，
#    還原薄殼化前「lib/tla2tools.jar 不存在時自動下載」的既有使用者體驗；不需額外
#    記住旗標。
#
# 用途：本機開發者在 Windows 跑 TLC 對 SDD_FSM.tla 做形式化驗證。
# 對應規則：CLAUDE.md Rule 9.18.1~9.18.4
#
# 使用（既有呼叫慣例不變）：
#   pwsh run_tlc.ps1                    # 跑完整驗證（SDD_FSM + FLEET_FSM safety/liveness；
#                                        #   jar 缺失時自動下載 DEFAULT_TLA_VERSION）
#   pwsh run_tlc.ps1 -InstallOnly       # 僅下載 tla2tools.jar
#   pwsh run_tlc.ps1 -Depth 100         # 自訂 SDD_FSM 探索深度上限
#   pwsh run_tlc.ps1 -InstallOnly -TlaVersion v1.8.1  # 覆寫下載版本（R65 item4 恢復）
#
# Exit codes：
#   0 — 全部通過
#   1 — TLC 偵測 invariant / liveness violation / deadlock
#   2 — 環境錯誤（Java 缺失 / jar 下載失敗 / python 缺失）

[CmdletBinding()]
param(
    [switch]$InstallOnly,
    [int]$Depth = 50,
    [string]$TlaVersion = ""
)

$ScriptDir = $PSScriptRoot
# formal/ 的祖父層即 <SDD 版本根>/，`python -m tools.fsm_runtime.tlc_runner` 須以此為 cwd
$ToolsParent = (Resolve-Path (Join-Path $ScriptDir "..\..\..")).Path

# python 探測須經共用 WindowsAppsGuard.ps1::Test-IsRealPython SSOT 排除空殼
# （DEF-101-273/279/300/303 復發模式；同 install_hooks/install_post_commit.ps1
# 慣例，非本檔獨立重寫裸 Get-Command 判斷）。
$GitCommonDir = (git rev-parse --path-format=absolute --git-common-dir 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $GitCommonDir) {
    Write-Host "ERROR: 找不到 git repository（git rev-parse --git-common-dir 失敗）— 請在 monorepo checkout 內執行本腳本" -ForegroundColor Red
    exit 2
}
$MainCheckoutRoot = Split-Path -Parent $GitCommonDir.Trim()
$WindowsAppsGuardPath = Join-Path $MainCheckoutRoot "tools\lib\WindowsAppsGuard.ps1"
if (-not (Test-Path $WindowsAppsGuardPath)) {
    Write-Host "ERROR: 找不到共用函式 $WindowsAppsGuardPath — 請在完整 monorepo checkout 內執行本腳本" -ForegroundColor Red
    exit 2
}
. $WindowsAppsGuardPath
# R65 item3：探測順序統一為 python3 優先（同 run_tlc.sh 的 for _cand in python3 python，
# 本專案 Unix 慣例；兩側原不一致，此後兩支皆 python3 → python）。
$PythonBin = $null
foreach ($cand in @("python3", "python")) {
    if (Test-IsRealPython -CandidateName $cand) { $PythonBin = $cand; break }
}
if (-not $PythonBin) {
    Write-Host "ERROR: 找不到 python/python3（或僅偵測到 WindowsApps 空殼），請安裝 Python 3.11+。" -ForegroundColor Red
    exit 2
}

# R65 item4：-TlaVersion 若設值才轉傳 --tla-version（薄殼化前舊行為的等價恢復——
# 沒設值就不傳、tlc_runner.py 沿用其 DEFAULT_TLA_VERSION 常數，行為不變）。
$TlaVersionArgs = @()
if ($TlaVersion) { $TlaVersionArgs = @("--tla-version", $TlaVersion) }

Push-Location $ToolsParent
try {
    if ($InstallOnly) {
        & $PythonBin -m tools.fsm_runtime.tlc_runner --install-only @TlaVersionArgs
        exit $LASTEXITCODE
    }

    Write-Host "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 SDD_FSM（depth=$Depth）..."
    & $PythonBin -m tools.fsm_runtime.tlc_runner --module SDD_FSM --depth $Depth --download @TlaVersionArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 FLEET_FSM 5a（safety + symmetry）..."
    & $PythonBin -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --download @TlaVersionArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 FLEET_FSM 5b（liveness, NO symmetry）..."
    & $PythonBin -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --cfg FLEET_FSM_LIVENESS.cfg --download @TlaVersionArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
