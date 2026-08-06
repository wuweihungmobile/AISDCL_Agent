<#
.SYNOPSIS
在本機 Docker 內以 act 重現 GitHub Actions（.github/workflows/autoclaude-ci.yml）薄殼（Windows）。
macOS/Linux 對等：tools/run_act.sh

.DESCRIPTION
  邏輯全部集中在 tools/run_act_core.py（跨平台單一事實源；仿 R12 DEF-101-070 ② local_ci_gate
  收斂模式）。本檔只做：確認直譯器 → 參數映射 → 轉呼叫核心 → 傳遞 exit code。介面
  （-Job / -List / -DryRun）與收斂前完全相容。

🔴 本檔刻意只留「這一版與上一版差在哪」；jobs 清單、act 與雲端的落差、實跑帳本語意等
  完整說明一律住核心 run_act_core.py 的檔頭（本檔受 100 行薄殼上限，塞說明會擠爆它）。

🔴 SD-06（本輪修的技術債）：R77 給 `.sh` 接上 `--workflow`／`--event`（該側 "$@" 全轉），
  本檔卻沒跟上 ⇒ Windows（本 repo 主要開發平台）的薄殼指不到 11 支 workflow 裡的 10 支。
  而 check_script_parity.py／check_wrapper_thinness.py **雙雙 rc=0**：hash 釘選只問「這份
  檔案有沒有變」，從不把兩側互相比較（LOCKBLIND）。修法三件同批：① 本檔補齊參數；
  ② 同 commit 更新 hash 釘選；③ 補判準讓下一次落差自己轉紅——
  tools/tests/test_act_local_runner_image.py::TestRunActShellFlagParity（核心 argparse
  宣告的每個長旗標，兩側殼都必須到得了）。只補旗標不補判準，同型缺陷會再來一次。

.PARAMETER Job
只跑單一 job（例：test）。省略則跑整份 push 圖（與 GitHub 在 push 時等價）。

.PARAMETER Workflow
要跑哪一支 workflow（repo 相對路徑）。省略＝autoclaude-ci.yml（零行為變更）。

.PARAMETER EventName
模擬哪個 GitHub 事件（預設 push）；命令列寫 `-Event` 亦可（Alias）。無該事件觸發的
workflow 不指定時，act 會「零執行卻回 rc=0」＝假綠，核心 preflight 會擋成 rc=1。
🔴 變數名刻意不是 `$Event`：那是 PowerShell **自動變數**，拿來當參數名會遮蔽 runtime
語意（PSScriptAnalyzer `PSAvoidAssignmentToAutomaticVariable`）。`[Alias]` 讓「對外與
--event 對稱」與「不碰自動變數」同時成立——鐵律三「這個名字在另一個環境是什麼意思」。

.PARAMETER List
列出 job（act -l）＋全庫盤點：每個 job 落在 ✅ 已實跑通過／🟡 可解析未實跑／
❌ 結構上無本機通道／⚠️ 需 -Event 哪一格，逐行附替代驗證出口。

.PARAMETER DryRun
傳 -n，只解析不執行。🔴 dry-run 全綠只證明 YAML 寫對——R77 實測 root-infra dry-run
rc=0、真跑第 3 步 rc=127。

.PARAMETER BuildImage
（重）建本機 act runner 映像（tools/act/Dockerfile：base ＋ pwsh ＋ gh）後結束。

.PARAMETER NoCache
搭配 -BuildImage：不吃 docker layer cache（改了 Dockerfile 的 ARG 版本號時必用）。

.PARAMETER VerifyAll
🔴 推 GitHub 前的一鍵本機全驗：跑得動的 job 全部真跑並記帳，跑不動的逐個列出替代
驗證出口；任一支「該跑而失敗」即回非 0。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -BuildImage   # 先備妥 runner 映像
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -VerifyAll    # 推送前一鍵本機全驗
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test     # 最快：只跑主測試閘門
  powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 `
      -Workflow .github/workflows/root-infra-ci.yml -Job root-infra        # 指定別支 workflow
#>
[CmdletBinding()]
param(
  [string]$Job,
  [string]$Workflow,
  [Alias('Event')]
  [string]$EventName,
  [switch]$List,
  [switch]$DryRun,
  [switch]$BuildImage,
  [switch]$NoCache,
  [switch]$VerifyAll
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
if ($Workflow) { $CliArgs += @('--workflow', $Workflow) }
if ($EventName) { $CliArgs += @('--event', $EventName) }
if ($List) { $CliArgs += '--list' }
if ($DryRun) { $CliArgs += '--dry-run' }
if ($BuildImage) { $CliArgs += '--build-image' }
if ($NoCache) { $CliArgs += '--no-cache' }
if ($VerifyAll) { $CliArgs += '--verify-all' }
& python (Join-Path $PSScriptRoot 'run_act_core.py') @CliArgs
exit $LASTEXITCODE
