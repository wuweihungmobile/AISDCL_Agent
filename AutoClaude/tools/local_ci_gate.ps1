<#
.SYNOPSIS
本機 CI 閘門一鍵指令 — push 前在本機把所有問題解決完（落實「本機綠了才上版」）。

.DESCRIPTION
依序鏡像 .github/workflows/ci.yml 的 push gating jobs，全綠才建議 push：
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
Set-Location $RepoRoot
$env:PYTHONUTF8 = '1'

$results = [System.Collections.Generic.List[object]]::new()
function Invoke-Gate {
  param([string]$Name, [scriptblock]$Block)
  Write-Host "`n===== [$Name] =====" -ForegroundColor Cyan
  & $Block
  $rc = $LASTEXITCODE
  if ($null -eq $rc) { $rc = 0 }
  $status = if ($rc -eq 0) { 'PASS' } else { 'FAIL' }
  $color = if ($rc -eq 0) { 'Green' } else { 'Red' }
  Write-Host "[$Name] $status (rc=$rc)" -ForegroundColor $color
  $results.Add([pscustomobject]@{ Name = $Name; Status = $status; Rc = $rc })
}

# 0. editable install 哨兵（流程改善 #9c）：autoclaude 必須指向本 monorepo，
#    避免舊 editable .pth 殘留 shadow 至遷移前副本，導致工作樹驗證誤命中舊源碼。
Invoke-Gate 'editable sentinel' {
  python -c "import autoclaude,sys; ok='AISDCL_Agent' in autoclaude.__file__; print('autoclaude:', autoclaude.__file__); sys.exit(0 if ok else 1)"
}

# 1. LOC 預算
Invoke-Gate 'LOC budget' { python tools/check_loc_budget.py }

# 2. CLAUDE.md <= 400 行
Invoke-Gate 'CLAUDE.md <=400' {
  $lines = (Get-Content CLAUDE.md | Measure-Object -Line).Lines
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
