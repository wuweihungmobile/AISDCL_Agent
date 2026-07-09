<#
.SYNOPSIS
在本機 Docker 內以 act 重現 GitHub Actions（.github/workflows/ci.yml），push 前攔截 CI 紅燈。

.DESCRIPTION
解決「上版 GitHub 才發現 CI/CD 錯誤」的根因：CI 在 Linux 跑、開發在 Windows，
環境差異（PG 鏡像版本、.sh CRLF、psycopg2、alembic、apt/pip 解析）只在 push 後暴露。
act 讀取 workflow YAML，於 Linux 容器內跑與雲端同一套流程 → 本機即可重現並修復。

對應 GitHub push/PR 觸發的 gating jobs（ci.yml）：
  test               pytest + LOC budget + import-linter（主閘門）
  claude-md-budget   CLAUDE.md <= 400 行 + snapshot freshness
  equivalence        equivalence snapshot（needs: test）
  pg-contract        PG 契約測（含 postgres service；CI 標 continue-on-error）

nightly/排程 job（mutation / pg-e2e / perf）以 `if: schedule` 排除，push 事件不會觸發，
本地請改用 tools/run_local_nightly.ps1。

.PARAMETER Job
只跑單一 job（例：test）。省略則跑整份 push 圖（與 GitHub 在 push 時等價）。

.PARAMETER List
列出 workflow 所有 job 後結束（act -l）。

.PARAMETER DryRun
傳 -n，只解析不實際執行（驗證 workflow 語法 / job 圖）。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test          # 最快：只跑主測試閘門
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1                     # 完整：跑 push 全部 job（含 PG 契約）
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -List               # 看有哪些 job
#>
[CmdletBinding()]
param(
  [string]$Job,
  [switch]$List,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Workflow = '.github/workflows/ci.yml'

# ---- 1. 定位 act.exe（PATH 可能尚未刷新 → 退回 winget 安裝路徑 → 退回 gh-act）----
# 回傳字串陣列（指令 + 前置參數），gh-act 退回時為 @('gh','act')，對齊 run_act.sh 的偵測邏輯。
function Resolve-Act {
  $cmd = Get-Command act -ErrorAction SilentlyContinue
  if ($cmd) { return @($cmd.Source) }
  $wingetGlob = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\nektos.act_*\act.exe'
  $found = Get-ChildItem -Path $wingetGlob -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($found) { return @($found.FullName) }
  # gh-act 退回（對齊 run_act.sh：act 不在 PATH 時檢查 gh extension list 是否含 nektos/gh-act）
  if (Get-Command gh -ErrorAction SilentlyContinue) {
    try { $extList = & gh extension list 2>$null } catch { $extList = '' }
    if ("$extList" -match 'gh-act|nektos/gh-act') { return @('gh', 'act') }
  }
  return $null
}

$Act = @(Resolve-Act | Where-Object { $_ })
if ($Act.Count -eq 0) {
  Write-Host '[run_act] act 未安裝。請擇一安裝：' -ForegroundColor Red
  Write-Host '  winget install --id nektos.act -e'
  Write-Host '  scoop install act'
  Write-Host '  gh extension install https://github.com/nektos/gh-act   # 再以 gh act 呼叫'
  exit 127
}
$ActExe = $Act[0]
$ActPrefix = @($Act | Select-Object -Skip 1)
Write-Host "[run_act] act = $($Act -join ' ')" -ForegroundColor Cyan

# ---- 2. 確認 Docker daemon ----
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host '[run_act] Docker daemon 未啟動，請先開啟 Docker Desktop。' -ForegroundColor Red
  exit 1
}

# ---- 3. List 模式 ----
if ($List) {
  & $ActExe @($ActPrefix + @('-l', '-W', $Workflow))
  exit $LASTEXITCODE
}

# ---- 4. 預先 pull 所需鏡像（用 docker pull 而非 act forcePull）----
# 根因：act forcePull 透過 Docker Desktop credsStore 對「公開」鏡像送出無效認證
#       → Docker Hub 回 401 authentication required。改由本腳本以 docker pull 確保鏡像
#       存在（公開 pull 不送認證、可成功），再對 act 傳 --pull=false 用本地鏡像，繞過此 bug。
$RunnerImage = 'catthehacker/ubuntu:act-latest'
$NeededImages = @($RunnerImage)
# 跑整份 push 圖（未指定 -Job）含 pg-contract → 需 postgres service 鏡像
if (-not $Job) { $NeededImages += 'pgvector/pgvector:pg17' }
foreach ($img in $NeededImages) {
  & docker image inspect $img *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[run_act] 本地缺鏡像 $img → docker pull（首次約 1~1.5GB）…" -ForegroundColor Yellow
    & docker pull $img
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[run_act] docker pull $img 失敗。" -ForegroundColor Red
      exit 1
    }
  } else {
    Write-Host "[run_act] 鏡像已就緒：$img" -ForegroundColor DarkGray
  }
}

# ---- 5. 阻止 act 預設載入 repo .env（關鍵）----
# act 預設會把 cwd 的 .env 注入容器。本 repo .env 含真實 MINIMAX_API_KEY / DB 憑證：
#   (1) 安全：不應把個人憑證注入容器；
#   (2) 忠實度：GitHub runner 無 .env，注入後會讓「預期 env 未設」的測試偽 fail
#       （實測 test_minimax_missing_api_key 因 .env 的 MINIMAX_API_KEY 而 DID NOT RAISE）。
# 解法：傳一個空的 --env-file 覆蓋預設 .env 載入（temp 空檔，免污染 repo / 免踩 .gitignore）。
$EmptyEnv = Join-Path $env:TEMP 'autoclaude_act_empty.env'
Set-Content -Path $EmptyEnv -Value '' -NoNewline -Encoding ascii

# ---- 6. 組裝 act 參數 ----
# push 事件 → ci.yml 的 nightly job（if: schedule/dispatch）自動排除；只跑 gating jobs。
# --pull=false：用上一步已備妥的本地鏡像，繞過 credsStore 公開鏡像 401 bug。
# --env-file 空檔：忠實對齊 GitHub CI（無 .env）。
$actArgs = @('push', '-W', $Workflow, '--pull=false', '--env-file', $EmptyEnv)
if ($Job)    { $actArgs += @('-j', $Job) }
if ($DryRun) { $actArgs += '-n' }

Write-Host "[run_act] 執行: $($Act -join ' ') $($actArgs -join ' ')" -ForegroundColor Cyan

& $ActExe @($ActPrefix + $actArgs)
$rc = $LASTEXITCODE

if ($rc -eq 0) {
  Write-Host "[run_act] ✅ 本地 CI 通過（act 退出碼 0）— 可安全 push。" -ForegroundColor Green
} else {
  Write-Host "[run_act] ❌ 本地 CI 失敗（act 退出碼 $rc）— 請於本機修復後再 push。" -ForegroundColor Red
}
exit $rc
