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

🔴 射程（本輪實測後補上；先前這份說明讀起來像「act ＝ 地端跑真 CI」，沒有任何限定詞）：
  上面那四個 job 只是 autoclaude-ci.yml 一支的內容。monorepo 根層現有 11 支 workflow
  共 25 個 job——`-List` 印的 act 表只有 9 個，其餘 16 個（含 root-infra-ci.yml 這支
  承載根層全部守門的、以及兩支 compat-CI 的 nightly 告警鏈）不在預設射程內。核心
  run_act_core.py 已有 `--workflow <路徑>` 可指到任何一支，但本薄殼**尚未**轉這個旗標：
  它的正規化內容 hash 釘在 tools/check_wrapper_thinness.py，補參數會改 hash，而該檔
  本輪由另一個修復包擁有 ⇒ 補參數與更新釘選必須同一個 commit，不能分兩包做。

  在補上之前，Windows 側指定 workflow／事件的唯一入口是**環境變數**（兩平台皆生效）：
    $env:RUN_ACT_WORKFLOW = '.github/workflows/root-infra-ci.yml'
    powershell -ExecutionPolicy Bypass -File AutoClaude/tools/run_act.ps1 -Job root-infra
  或直接呼叫核心（不經薄殼，無此限制）：
    python AutoClaude/tools/run_act_core.py --workflow <路徑> --job <job>

🔴 事件（本輪實測踩到的假綠）：本殼與核心一律以 `push` 事件呼叫 act，而根層 11 支
  workflow 裡有 5 支的 `on:` **不含 push**（arch-fitness／artifact-cleanup／drift-daily／
  fsm-chaos-nightly／pg-e2e-on-label）。act 對事件對不上的處置是「不跑任何 job 然後回
  rc=0」——沒有紅字，只是什麼都沒發生。核心的 preflight 現在會把它擋成 rc=1 並指路；
  要真的跑那 5 支，請設 $env:RUN_ACT_EVENT（例 'pull_request'）或直接用核心的 --event。

  `-List` 在未指定 workflow 時會在 act 那張表之後另印一張**全庫 job 盤點**，逐行標出
  每個 job 在本機 act 有無通道——四個 non-ubuntu 的 job 結構上零通道（見盤點輸出）。

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
