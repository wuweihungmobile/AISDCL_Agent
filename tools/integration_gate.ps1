# integration_gate.ps1 — AISDCL_Agent 整合層薄聚合閘門（AutoSDD_improving_01 §5.1，W8）
#
# 設計原則：不另立第三真相源，無自有檢查邏輯——僅依序呼叫兩專案既有單一真相源
# 再跑整合煙霧測試。任一段紅 → 非零 exit code。
#
#   [1/5] AutoClaude   : tools/local_ci_gate.ps1            （既有真相源，鏡像 ci.yml）
#   [2/5] AISDLC_SDD   : bash scripts/ci-gate.sh            （既有真相源；Git Bash）
#   [3/5] 整合測試     : pytest tests/integration/test_sdd_bridge/ -q
#   [4/5] 回退驗證     : pytest tests/integration/test_sdd_bridge/test_rollback_compat.py -q
#                        （v0.01/v0.02 各自 state_loader 產出真品 FSM 狀態 → sdd_compile 消費，
#                         AutoSDD_improving_01 §6 規則 4 回退驗證落地）
#   [5/5] cc-switch A/B: 多模型後端對比驗收（cc-switch 未安裝 → SKIP，
#                        記錄於 docs/06_quality/AutoSDD_Defect_Log.md DEF-01-007）
#
# 用法： powershell -ExecutionPolicy Bypass -File tools/integration_gate.ps1
#        附 -SkipFull 僅跑 [3/5]+[4/5]+[5/5]（開發快速迴圈）
param(
    [switch]$SkipFull
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$failures = @()
$passCount = 0   # P2-1：通過段數（含 cc-switch 已安裝段）
$skipCount = 0   # P2-1：SKIP 段數（cc-switch 未安裝時 = 1）

function Invoke-Section {
    param([string]$Label, [scriptblock]$Body)
    Write-Host "`n==> $Label" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) {
        $script:failures += "$Label (exit=$LASTEXITCODE)"
        Write-Host "❌ $Label FAILED (exit=$LASTEXITCODE)" -ForegroundColor Red
    } else {
        $script:passCount++
        Write-Host "✅ $Label PASS" -ForegroundColor Green
    }
}

if (-not $SkipFull) {
    Invoke-Section "[1/5] AutoClaude local_ci_gate" {
        Push-Location (Join-Path $Root "AutoClaude")
        try { powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 }
        finally { Pop-Location }
    }

    Invoke-Section "[2/5] AISDLC_SDD ci-gate.sh" {
        Push-Location (Join-Path $Root "AISDLC_SDD")
        try { bash scripts/ci-gate.sh }
        finally { Pop-Location }
    }
}

Invoke-Section "[3/5] SDD bridge 整合煙霧" {
    Push-Location (Join-Path $Root "AutoClaude")
    try { python -m pytest tests/integration/test_sdd_bridge/ -q }
    finally { Pop-Location }
}

Invoke-Section "[4/5] 回退驗證（v0.01/v0.02 真品 FSM 狀態）" {
    Push-Location (Join-Path $Root "AutoClaude")
    try { python -m pytest tests/integration/test_sdd_bridge/test_rollback_compat.py -q }
    finally { Pop-Location }
}

Write-Host "`n==> [5/5] cc-switch 多模型 A/B 驗收" -ForegroundColor Cyan
$ccSwitch = Get-Command cc-switch -ErrorAction SilentlyContinue
if ($null -eq $ccSwitch) {
    $skipCount++
    Write-Host ("⚠️  SKIP：cc-switch 未安裝（DEF-01-007，AutoSDD_Defect_Log.md）。" +
        "安裝後執行：cc-switch use <profile> && autoclaude sdd_bridge_smoke.yaml --fresh，" +
        "對比指標：一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值") `
        -ForegroundColor Yellow
} else {
    $passCount++
    Write-Host "cc-switch 已安裝：請依 AutoSDD_improving_01.md §5.2 手動執行 A/B 對比" -ForegroundColor Green
}

if ($failures.Count -gt 0) {
    Write-Host "`n❌ 整合閘門未通過：$($failures -join '; ')" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ 整合閘門通過（$passCount PASS / $skipCount SKIP）" -ForegroundColor Green
exit 0
