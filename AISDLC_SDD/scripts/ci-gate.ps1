# AISDLC-SDD — 本機 CI 閘門（Windows PowerShell 版；與 ci-gate.sh 等價）。
# 用法：  pwsh scripts/ci-gate.ps1            # 離線閘門
#         $env:SDD_RUN_TLC=1; pwsh scripts/ci-gate.ps1   # 另跑五軌 TLC
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$fw   = Join-Path $repo "AISDLC_SDD_v0.01"
Set-Location $fw

Write-Host "==> [1/3] pytest -m 'not chaos'（全套，含 offline reachability BFS）"
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q
if ($LASTEXITCODE -ne 0) { throw "pytest 失敗" }

Write-Host "==> [2/3] arch_fitness（structural fail 阻擋；advisory warn 放行）"
# 必帶 --strict：唯有 --strict 時 structural fail 才回傳 exit 2，與雲端 nightly-strict 一致。
python -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
if ($LASTEXITCODE -ge 2) { throw "arch_fitness structural fail (exit=$LASTEXITCODE)" }
if ($LASTEXITCODE -eq 1) { Write-Host "(arch_fitness advisory warn — 不阻擋)" }

if ($env:SDD_RUN_TLC -eq "1") {
  foreach ($m in "SDD_FSM","META_FSM","FLEET_FSM","COMPOSITION_FSM","OPTIMIZATION_FSM") {
    Write-Host "==> [3/3] TLC $m"
    python -m tools.fsm_runtime.tlc_runner --module $m
    if ($LASTEXITCODE -ne 0) { throw "TLC $m 失敗" }
  }
} else {
  Write-Host "==> [3/3] 跳過完整 TLC（offline reachability 已隨 pytest 驗證）"
}

Write-Host "✅ 本機 CI 閘門全數通過"
