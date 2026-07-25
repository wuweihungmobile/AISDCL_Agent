<#
.SYNOPSIS
在本機 Docker 內以 act 重現 GitHub Actions（.github/workflows/autoclaude-ci.yml）薄殼（Windows）。
macOS/Linux 對等：tools/run_act.sh

.DESCRIPTION
  邏輯全部集中在 tools/run_act_core.py（跨平台單一事實源；仿 R12 DEF-101-070 ② local_ci_gate
  收斂模式）。本檔只做：確認直譯器 → 參數映射 → 轉呼叫核心 → 傳遞 exit code。介面
  （-Job / -List / -DryRun）與收斂前完全相容。

對應 GitHub push/PR 觸發的 gating jobs（autoclaude-ci.yml）：
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

# WindowsApps 空殼排除比照 tools/bootstrap.ps1／tools/dev_start.ps1 既有 SSOT（R44 收斂）
. "$PSScriptRoot/../../tools/lib/WindowsAppsGuard.ps1"
if (-not (Test-IsRealPython -CandidateName 'python')) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

$env:PYTHONUTF8 = '1'
$CliArgs = @()
if ($Job) { $CliArgs += @('--job', $Job) }
if ($List) { $CliArgs += '--list' }
if ($DryRun) { $CliArgs += '--dry-run' }
& python (Join-Path $PSScriptRoot 'run_act_core.py') @CliArgs
exit $LASTEXITCODE
