# AISDLC-SDD — 本機 CI 閘門（Windows PowerShell 版）。
# 行為（薄委派，防 .ps1 與 .sh 覆蓋差距單向擴大）：
#   1. 偵測到 Git Bash（bash.exe）→ 薄委派 `bash scripts/ci-gate.sh`（單一真相源，
#      完整覆蓋：凍結基線 + LATEST 演化版雙軌 + 全部硬閘；參數與 exit code 原樣傳遞，
#      故 --full-tlc 等旗標直接可用）。
#   2. 找不到 Git Bash → 退回下方 fallback 3-stage（僅「v0.01 凍結基線」單軌：
#      pytest not-chaos + arch_fitness --strict + 選跑 TLC），並明確警告
#      覆蓋範圍小於 ci-gate.sh。
# 用法：  pwsh scripts/ci-gate.ps1 [ci-gate.sh 參數，如 --full-tlc]  # 有 Git Bash → 完整閘門
#         $env:SDD_RUN_TLC=1; pwsh scripts/ci-gate.ps1               # fallback 時另跑五軌 TLC
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
# 🔴 DEF-200-315（2026-09-19 掌舵者裁決）：訂正上述協議——單一 .venv 設計下互動式
# 入口一律優先釘死 monorepo 根層 .venv（`$repo` 指向 AISDLC_SDD/，故傳
# `Join-Path $repo '..'`），不再只檢查 PATH 上有沒有 python；`$py` 取代下方全部
# 執行用裸 `python`（`Get-RepoPython` 同檔 SSOT，內部沿用 Test-IsRealPython 判
# 空殼，只在 CI／逃生口才落回 PATH 候選，找不到時已印補救訊息，本處不必再印）。
. "$PSScriptRoot/../../tools/lib/WindowsAppsGuard.ps1"
$py = Get-RepoPython -RepoRoot (Join-Path $repo '..')
if (-not $py) {
  exit 1
}

# 跨 leg CPU 預算廣播（DEF-200-289）— fallback 版首個 pytest 呼叫之前。
# WHY：與 ci-gate.sh／pre-push 同名區塊同一顆 SSOT（tools/lib/cpu_budget.py），
# 廣播給下游任何會讀這兩個變數的呼叫端；使用者已顯式設定其一則不覆寫。
if (-not $env:AUTOSDD_PARALLEL_TESTS_WORKERS -and -not $env:PYTEST_XDIST_AUTO_NUM_WORKERS) {
  $_cpuBudget = & $py "$repo/tools/lib/cpu_budget.py" --legs 1 2>$null
  if ($_cpuBudget -match '^\d+$') {
    $env:AUTOSDD_PARALLEL_TESTS_WORKERS = $_cpuBudget
    $env:PYTEST_XDIST_AUTO_NUM_WORKERS = $_cpuBudget
  }
}

$fw   = Join-Path $repo "AISDLC_SDD_v0.01"
Set-Location $fw

Write-Host "==> [1/3] pytest -m 'not chaos'（全套，含 offline reachability BFS）"
# `-rs`（R59 ARCH-R59-01）：與 ci-gate.sh 對稱，skip 理由必須可見。
# 🔴 GAP-D 判讀（DEF-200-289 四方審查列為 P1 缺口）：本行**刻意不加**
# `-n auto --dist worksteal`——本 fallback 只跑 `AISDLC_SDD_v0.01`（凍結基線，
# 見上方 `$fw`），而 ci-gate.sh 的差異化理由（該檔 XDIST_ARGS 判斷區塊，
# `"${VER}" == "${LATEST}"` 才開 xdist）明文記載：凍結基線的 `snapshot.py`
# 仍是舊版固定檔名 `.tmp`，多 worker 平行觸發 `save_abort_report()` 會互相
# 競態，實測約 1/3~4/9 翻紅；只有 LATEST 帶著已修好的 `_atomic_write_text`。
# 本 fallback 沒有 LATEST 軌（硬寫死 v0.01），若無條件加上 `-n auto`，等於
# 把凍結基線唯一沒有的那個修法需求強加給它，複製回 ci-gate.sh 已經修掉的
# 那個競態——這不是「與 .sh LATEST 軌一致」，而是「與 .sh 凍結基線軌一致」
# （序列執行），對稱點是允許清單語意本身，不是逐字複製旗標。
& $py -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -rs
if ($LASTEXITCODE -ne 0) { throw "pytest 失敗" }

Write-Host "==> [2/3] arch_fitness（structural fail 阻擋；advisory warn 放行）"
# 必帶 --strict：唯有 --strict 時 structural fail 才回傳 exit 2，與雲端 nightly-strict 一致。
& $py -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
if ($LASTEXITCODE -ge 2) { throw "arch_fitness structural fail (exit=$LASTEXITCODE)" }
if ($LASTEXITCODE -eq 1) { Write-Host "(arch_fitness advisory warn — 不阻擋)" }

if ($env:SDD_RUN_TLC -eq "1") {
  foreach ($m in "SDD_FSM","META_FSM","FLEET_FSM","COMPOSITION_FSM","OPTIMIZATION_FSM") {
    Write-Host "==> [3/3] TLC $m"
    & $py -m tools.fsm_runtime.tlc_runner --module $m
    if ($LASTEXITCODE -ne 0) { throw "TLC $m 失敗" }
  }
} else {
  Write-Host "==> [3/3] 跳過完整 TLC（offline reachability 已隨 pytest 驗證）"
}

# DEF-101-512（R59）：本行原本輸出的字串，是 ci-gate.sh 完整閘門收尾行
# 「✅ 本機 CI 閘門全數通過（版本：…）」去掉括號後綴後的**前綴子字串**（非逐字相同，
# 但 grep 該前綴會同時命中兩者）。實務上稽核取證（人工回報、歷輪帳本引用、grep）用的
# 錨點正是那段前綴，故兩條路徑在該錨點下**無法分辨**。
# （本註解刻意只引述完整閘門那一版字面值一次，避免自己成為 grep 稽核的雜訊來源。）
# 而這條 fallback 只跑 v0.01 凍結基線單軌的 3 個 stage
# （見上方 `$fw = Join-Path $repo "AISDLC_SDD_v0.01"`），**不含** LATEST 軌、不含 ci-gate.sh
# 的 10 道 lint 硬閘、不含 scripts/tests 共享 infra 測試——覆蓋率差距是數量級的。
# 只有 Windows 走得到這條路（mac 一律有 bash），屬單邊平台的取證可信度缺口。
# 修法刻意選「讓字串在結構上無法冒充」而非「加更多 warning」：起頭已有一行 ⚠️ 警告，
# 但人讀 log 取的是**最後那行結論**；讓結論自己說出降級事實，才不依賴讀者記得往上看。
Write-Host "✅ fallback 3-stage 通過（僅 AISDLC_SDD_v0.01 凍結基線單軌；**未含** LATEST 軌、未含 ci-gate.sh 的 lint 硬閘與 scripts/tests 共享 infra 測試——非完整閘門）"
