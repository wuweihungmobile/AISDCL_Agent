<#
.SYNOPSIS
本機 CI 閘門一鍵指令 — push 前在本機把所有問題解決完（落實「本機綠了才上版」）。

.DESCRIPTION
依序鏡像 monorepo 根層 .github/workflows/autoclaude-ci.yml 的 push gating jobs，全綠才建議 push：
  0. editable 哨兵       （流程改善 #9c：autoclaude 指向本 monorepo）
  1. LOC 預算            （CI: test / claude-md-budget）
  2. CLAUDE.md <= 400 行 （CI: claude-md-budget）
  2b. CLAUDE.md 單行<=800 （流程改善 #10b：對齊 contract test_claude_md_no_long_lines）
  3. snapshot 可重現     （CI: claude-md-budget）
  4. import-linter       （CI: test）
  5. pytest              （CI: test + equivalence）
可選：
  -Act  額外用 act 在 Linux 容器跑 ci.yml（100% 環境對等，攔 Windows/Linux 差異）
  -Pg   額外起 docker-compose.ci.yml（pg17）跑 PG 契約測（CI: pg-contract）

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1            # 標準本機閘門（不含 Docker）
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Act       # 加跑 Linux 容器真 CI（最嚴格）
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Pg        # 加跑 PG 契約測
#>
[CmdletBinding()]
param(
  [switch]$Act,
  [switch]$Pg,
  [string]$PytestArgs = 'tests/ -q --tb=short'
)

$ErrorActionPreference = 'Continue'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$MonoRoot = Split-Path -Parent $RepoRoot   # monorepo 根（AutoClaude 上一層）— 定位共用 tools/
Set-Location $RepoRoot
$env:PYTHONUTF8 = '1'

# venv 提示：所有 gate 都靠裸 python，未啟用 venv 就直接失敗提示（勝過各 gate 逐一噴錯）
# —— 與 local_ci_gate.sh 的 `command -v python` 前置守門對稱。
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

# --- git hooks liveness 偵測（警告不擋）---
# repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（$env:CI 有值）
# 跳過（GitHub/act 環境無 hooks 屬正常）。偵測邏輯抽共用（S11）：
# 見 tools/check_hooks_liveness.py（單一真相源，供本檔與 tools/integration_gate.ps1 呼叫）。
if (-not $env:CI) {
  try {
    $hlScript = Join-Path $MonoRoot 'tools/check_hooks_liveness.py'
    if (Test-Path -LiteralPath $hlScript) { & python $hlScript }
  } catch {
    # liveness 為 advisory：任何探測失敗都不得影響閘門本體
  }
}

$results = [System.Collections.Generic.List[object]]::new()
function Invoke-Gate {
  param([string]$Name, [scriptblock]$Block)
  Write-Host "`n===== [$Name] =====" -ForegroundColor Cyan
  # 殘值 fail-open 防護：CommandNotFoundException 等例外不更新 $LASTEXITCODE，
  # 前一 gate 的殘值 0 會讓本 gate 假 PASS → 每次執行前強制重置；
  # 「指令拋例外 / 命令不存在」以 try/catch 明確判 FAIL（PS 5.1 相容）。
  $global:LASTEXITCODE = 0
  $rc = 0
  try {
    & $Block
    $rc = $LASTEXITCODE
    if ($null -eq $rc) { $rc = 0 }
  } catch {
    Write-Host "[$Name] 例外：$($_.Exception.Message)" -ForegroundColor Red
    $rc = 1
  }
  $status = if ($rc -eq 0) { 'PASS' } else { 'FAIL' }
  $color = if ($rc -eq 0) { 'Green' } else { 'Red' }
  Write-Host "[$Name] $status (rc=$rc)" -ForegroundColor $color
  $results.Add([pscustomobject]@{ Name = $Name; Status = $status; Rc = $rc })
}

# 0. editable install 哨兵（流程改善 #9c）：autoclaude 必須指向本 monorepo，
#    避免舊 editable .pth 殘留 shadow 至遷移前副本，導致工作樹驗證誤命中舊源碼。
#    動態比對 repo 根（勿硬編碼資料夾名——clone 到任何目錄名皆應 PASS；本檔全域
#    EAP=Continue，native 2>$null 重導安全），與 local_ci_gate.sh gate_editable 對稱。
Invoke-Gate 'editable sentinel' {
  $top = (& git rev-parse --show-toplevel 2>$null | Out-String).Trim()
  if (-not $top) { $top = (Get-Location).Path }
  $env:AUTOCLAUDE_REPO_TOP = $top
  python -c "import os,pathlib,sys; import autoclaude; pkg=pathlib.Path(autoclaude.__file__).resolve(); root=pathlib.Path(os.environ['AUTOCLAUDE_REPO_TOP']).resolve(); ok=(root==pkg) or (root in pkg.parents); print('autoclaude:', pkg); print('repo root :', root); sys.exit(0 if ok else 1)"
}

# 1. LOC 預算
Invoke-Gate 'LOC budget' { python tools/check_loc_budget.py }

# 2. CLAUDE.md <= 400 行
Invoke-Gate 'CLAUDE.md <=400' {
  # 用實際行計數（wc -l 語意；含空白行）：Measure-Object -Line 不計空白行，
  # CLAUDE.md 在 400~500 行區間會誤報 PASS，與 CI 的 wc -l 不對等
  $lines = [IO.File]::ReadAllLines((Resolve-Path 'CLAUDE.md')).Count
  if ($lines -gt 400) { Write-Host "CLAUDE.md=$lines > 400"; $global:LASTEXITCODE = 1 }
  else { Write-Host "CLAUDE.md=$lines lines OK"; $global:LASTEXITCODE = 0 }
}

# 2b. CLAUDE.md 單行 <= 800 codepoint（流程改善 #10b；顯式早攔，對齊 contract test
#     與 loc_budget_check.py hook #10a，避免「累積敘事單行繞過 ≤400 行紅線」復發）
Invoke-Gate 'CLAUDE.md line<=800' {
  python -m pytest tests/contract/test_claude_md_no_long_lines.py -q --tb=short
}

# 3. snapshot 可重現
Invoke-Gate 'snapshot --check' { python tools/snapshot_sync.py --check }

# 4. import-linter
Invoke-Gate 'import-linter' {
  $li = Get-Command lint-imports -ErrorAction SilentlyContinue
  if ($li) { lint-imports }
  else { Write-Host 'lint-imports 未安裝（pip install -e .[lint]）'; $global:LASTEXITCODE = 1 }
}

# 5. pytest
Invoke-Gate 'pytest' {
  $argList = $PytestArgs -split '\s+'
  python -m pytest @argList
}

# 6. （選用）PG 契約測 via docker-compose.ci.yml
if ($Pg) {
  Invoke-Gate 'PG contract (pg17)' {
    # --wait：等 healthcheck 通過才回（取代固定 sleep；慢機不會 PG 未 ready 就跑 alembic）
    docker compose -f docker-compose.ci.yml up -d --wait
    if ($LASTEXITCODE -ne 0) { Write-Host 'docker compose up --wait 失敗'; return }
    # 全程用 asyncpg DSN，與 CI 一致（alembic/env.py 會自動 strip +asyncpg 改 psycopg2）
    $asyncDsn = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
    $env:AUTOCLAUDE_DB_DSN = $asyncDsn
    $env:AUTOCLAUDE_TEST_PG_DSN = $asyncDsn
    $env:AUTOCLAUDE_ALLOW_INSECURE_DB = '1'
    alembic upgrade head
    # alembic rc 防吞：migration 失敗即清理容器並記 FAIL，不讓後續指令 rc 蓋過
    if ($LASTEXITCODE -ne 0) {
      Write-Host 'alembic upgrade head 失敗'
      docker compose -f docker-compose.ci.yml down -v | Out-Null
      $global:LASTEXITCODE = 1
      return
    }
    python -m pytest tests/contract/test_pg_state_repository_contract.py -q --tb=short
    $pytestRc = $LASTEXITCODE
    docker compose -f docker-compose.ci.yml down -v | Out-Null
    $global:LASTEXITCODE = $pytestRc
  }
}

# 7. （選用）act：Linux 容器真 CI
if ($Act) {
  Invoke-Gate 'act CI (Linux test job)' { & "$RepoRoot/tools/run_act.ps1" -Job test }
}

# ----- 總結 -----
Write-Host "`n========== 本機 CI 閘門總結 ==========" -ForegroundColor Cyan
$results | ForEach-Object {
  $c = if ($_.Status -eq 'PASS') { 'Green' } else { 'Red' }
  Write-Host ("  {0,-22} {1}" -f $_.Name, $_.Status) -ForegroundColor $c
}
$failed = @($results | Where-Object { $_.Status -eq 'FAIL' })
if ($failed.Count -gt 0) {
  Write-Host "`n❌ $($failed.Count) 項失敗 — 請於本機修復後再 push。" -ForegroundColor Red
  exit 1
}
Write-Host "`n✅ 全部通過 — 可安全 push。" -ForegroundColor Green
exit 0
