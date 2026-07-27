# AISDLC-SDD — 本機 CI 閘門（Windows PowerShell 版）。
# 行為（薄委派，防 .ps1 與 .sh 覆蓋差距單向擴大）：
#   1. 偵測到 Git Bash（bash.exe）→ 薄委派 `bash scripts/ci-gate.sh`（單一真相源，
#      完整覆蓋：凍結基線 + LATEST 演化版雙軌 + 全部硬閘；參數與 exit code 原樣傳遞，
#      故 --full-tlc 等旗標直接可用）。
#   2. 找不到 Git Bash → 退回下方 fallback 3-stage（僅「v0.01 凍結基線」單軌：
#      pytest not-chaos + arch_fitness --strict + 選跑 TLC），並明確警告
#      覆蓋範圍小於 ci-gate.sh。
# 用法（R58 DEF-101-508 訂正：原本唯一示範寫成 `pwsh scripts/ci-gate.ps1`，但 Windows 11
#   出廠只有 Windows PowerShell 5.1、**不含 pwsh 7**〔R58 於真 Windows 11 Pro 實測 pwsh
#   NOT FOUND〕，使用者照抄本檔第一行自稱的「Windows PowerShell 版」腳本卻拿到「找不到
#   pwsh」——與 SDD 閘門完全無關的怪錯，還會誤以為要先裝 PowerShell 7。本檔語法已由
#   tools/tests/test_ps51_compat.py 機械保證 5.1 可解析，powershell 直接跑得動）：
#         powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ci-gate.ps1 [--full-tlc]
#         # 有 Git Bash → 完整閘門；與 tools/windows_smoke_local.ps1、ONBOARDING.md、根 CLAUDE.md 同一慣例
#         $env:SDD_RUN_TLC=1; powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ci-gate.ps1
#         # fallback 時另跑五軌 TLC
#   裝有 PowerShell 7 者用 `pwsh` 亦可（本檔不使用 7 專屬語法）。
$ErrorActionPreference = "Stop"
# 強制 Python 子程序統一 UTF-8（對齊 AutoClaude tools/local_ci_gate.ps1 同名設定）：
# zh-TW Windows 預設 cp950，fsm_runtime subprocess 輸出含中文時會 UnicodeDecodeError。
$env:PYTHONUTF8 = "1"
$repo = Split-Path -Parent $PSScriptRoot

# --- 薄委派：找得到 Git Bash 就跑完整 ci-gate.sh ---
# 排除 WSL 的 System32\bash.exe：那是 Linux 環境（無本 repo 的 Windows venv/依賴），
# 委派過去語意不對等；只認 Git for Windows 的 bash（PATH 或常見安裝路徑）。
# 偵測邏輯抽共用（S11）：見 tools/lib/Find-GitBash.ps1。
. "$PSScriptRoot/../../tools/lib/Find-GitBash.ps1"
$bashExe = Find-GitBash
if ($bashExe) {
  Write-Host "==> 偵測到 Git Bash（$bashExe）→ 薄委派 bash scripts/ci-gate.sh（完整雙軌閘門）"
  Set-Location $repo
  & $bashExe scripts/ci-gate.sh @args
  exit $LASTEXITCODE
}

Write-Host "⚠️ 找不到 Git Bash（bash.exe）→ 退回 fallback 3-stage（僅 v0.01 凍結基線單軌）。" -ForegroundColor Yellow
Write-Host "⚠️ 覆蓋範圍小於 ci-gate.sh（無 LATEST 演化版軌與其餘硬閘）；建議安裝 Git for Windows 後重跑。" -ForegroundColor Yellow

# WindowsApps 空殼排除 guard（R44 二審 Architect 揪出：本 fallback 分支下方三處
# 裸 `python -m ...` 呼叫零可用性判斷，guard 檔案本身其實存在、只是先前沒接上
# ——比照 tools/bootstrap.ps1／tools/dev_start.ps1 既有先例收斂，見 tools/lib/
# WindowsAppsGuard.ps1）。全新 Windows 11 機器未裝真 Python、又剛好沒裝 Git Bash
# 時，`Get-Command python` 仍會找到 WindowsApps 底下的空殼，若不排除，下方
# `python -m pytest ...` 只會跳出 Microsoft Store 安裝提示。
. "$PSScriptRoot/../../tools/lib/WindowsAppsGuard.ps1"
if (-not (Test-IsRealPython -CandidateName 'python')) {
  Write-Host "❌ 找不到 python（或偵測到的是 WindowsApps 空殼別名）— 無法執行 fallback 3-stage。請先安裝 Python >= 3.11。" -ForegroundColor Red
  exit 1
}

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
