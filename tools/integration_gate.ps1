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

# --- git hooks liveness 偵測（警告不擋）---
# repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（$env:CI 有值）
# 跳過（GitHub/act 環境無 hooks 屬正常）。與 AutoClaude/tools/local_ci_gate.ps1 對稱。
if (-not $env:CI) {
  $prevEAP = $ErrorActionPreference
  try {
    # 探測段局部 EAP=Continue：PS5.1 + EAP=Stop 下 native stderr 重導（2>$null）會擲
    # NativeCommandError（同 tools/bootstrap.ps1 Select-Python 已文件化的修法）
    $ErrorActionPreference = 'Continue'
    $hlTop = (& git -C $Root rev-parse --show-toplevel 2>$null | Out-String).Trim()
    if ($hlTop) {
      $hlExpected = [System.IO.Path]::GetFullPath((Join-Path $hlTop 'tools/git-hooks'))
      $hlRaw = (& git -C $Root config --get core.hooksPath 2>$null | Out-String).Trim()
      $hlAbs = ''
      if ($hlRaw) {
        if ([System.IO.Path]::IsPathRooted($hlRaw)) { $hlAbs = [System.IO.Path]::GetFullPath($hlRaw) }
        else { $hlAbs = [System.IO.Path]::GetFullPath((Join-Path $hlTop $hlRaw)) }
      }
      if ((-not $hlAbs) -or ($hlAbs -ne $hlExpected) -or (-not (Test-Path -LiteralPath $hlExpected))) {
        $hlShown = if ($hlRaw) { $hlRaw } else { '（未設定）' }
        Write-Host ''
        Write-Host '⚠️⚠️⚠️ [hooks liveness] dispatcher git hooks 未生效 — pre-commit/pre-push 閘門不會執行！' -ForegroundColor Yellow
        Write-Host "    core.hooksPath 目前值：$hlShown" -ForegroundColor Yellow
        Write-Host "    預期值：$hlExpected" -ForegroundColor Yellow
        Write-Host '    請執行安裝腳本（兩子專案閘門同時生效，裝一次即可）：' -ForegroundColor Yellow
        Write-Host '        powershell -ExecutionPolicy Bypass -File AutoClaude/tools/install_git_hooks.ps1' -ForegroundColor Yellow
        Write-Host '    （本檢查僅警告、不阻擋閘門執行；CI 環境自動跳過）' -ForegroundColor Yellow
      }
    }
  } catch {
    # liveness 為 advisory：任何探測失敗都不得影響閘門本體
  } finally {
    $ErrorActionPreference = $prevEAP
  }
}

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
# DEF-10-001(b)（improving_10 階段一重偵察）：主流 cc-switch（farion1231）為 Tauri GUI
# 桌面 app，安裝後**不會**在 PATH 放 cc-switch 指令 → 原 Get-Command 永遠偵測不到。
# headless 自動 A/B 需 CLI 變體（SaladDay/cc-switch-cli 等）。逐一偵測已知 CLI 名。
$ccCli = $null
foreach ($name in @("cc-switch", "cc-switch-cli", "ccs")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -ne $cmd) { $ccCli = $cmd; break }
}
# DEF-10-001(a)：A/B 載具 playbook 須存在，否則文件化指令會 file-not-found。
$smokePb = Join-Path $Root "AutoClaude\scripts\sdd_bridge_smoke.yaml"
$pbRel = if (Test-Path $smokePb) { "scripts/sdd_bridge_smoke.yaml" } `
         else { "⚠️載具缺失:scripts/sdd_bridge_smoke.yaml(DEF-10-001a)" }
if ($null -eq $ccCli) {
    $skipCount++
    Write-Host ("⚠️  SKIP：未偵測到 cc-switch CLI（DEF-01-007，AutoSDD_Defect_Log.md）。" +
        "注意：farion1231/cc-switch 為 GUI app 不上 PATH；headless A/B 需 CLI 變體" +
        "（SaladDay/cc-switch-cli）。裝好 CLI 後於 AutoClaude/ 執行：" +
        "cc-switch use <profile-A> && autoclaude $pbRel --fresh（換 profile-B 再跑一次），" +
        "對比指標：一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值") `
        -ForegroundColor Yellow
} else {
    $passCount++
    Write-Host ("cc-switch CLI 已偵測（$($ccCli.Source)）：於 AutoClaude/ 對 $pbRel 切換 " +
        "profile 各跑一次 --fresh，依 $pbRel 檔頭程序收集 A/B 四指標" +
        "（一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值）") `
        -ForegroundColor Green
}

if ($failures.Count -gt 0) {
    Write-Host "`n❌ 整合閘門未通過：$($failures -join '; ')" -ForegroundColor Red
    exit 1
}
Write-Host "`n✅ 整合閘門通過（$passCount PASS / $skipCount SKIP）" -ForegroundColor Green
exit 0
