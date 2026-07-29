<#
.SYNOPSIS
本機 CI 閘門薄殼（Windows）。macOS/Linux 對等：tools/local_ci_gate.sh

.DESCRIPTION
  邏輯全部集中在 tools/local_ci_gate.py（跨平台單一事實源；DEF-101-070 ② 收斂案，
  模式對齊 tools/dev_start.{py,sh,ps1}）。本檔只做：確認直譯器 → 參數映射 →
  轉呼叫核心 → 傳遞 exit code。薄殼由 monorepo 根 tools/check_wrapper_thinness.py
  hash 釘選守門。介面（-Act / -Pg / -PytestArgs）與收斂前完全相容。

  🔴 -PytestArgs 預設必須為空字串（R60 F-refuter-1）：本檔曾寫死
  'tests/ -q --tb=short'，而核心 DEFAULT_PYTEST_ARGS 在 R59 加了 -rs，於是「無參數
  呼叫」在 Windows 側被薄殼整批取代掉核心預設、-rs 被靜默吃掉（含 nightly Stage L），
  兩支宣告等價的薄殼實際給出不同的 pytest 報告面。hash 釘選只認「本檔內容有沒有變」，
  對「本檔的常數與核心的常數語意分歧」是盲的，故另有跨檔鎖：
  AutoClaude/tests/tools/test_local_ci_gate_shell_arg_parity.py。
  預設值一律由核心單一真相源決定，本檔不得再內嵌任何 pytest 參數字面值。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1            # 標準本機閘門（不含 Docker）
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Act       # 加跑 Linux 容器真 CI（最嚴格）
  powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Pg        # 加跑 PG 契約測
#>
[CmdletBinding()]
param(
  [switch]$Act,
  [switch]$Pg,
  [string]$PytestArgs = ''
)

$ErrorActionPreference = 'Continue'

# 直譯器選擇維持收斂前語意：PATH 上的 python（所有 gate 都靠已啟用的 venv），
# 未啟用 venv 就直接失敗提示（勝過各 gate 逐一噴錯）；WindowsApps 空殼排除
# 比照 tools/bootstrap.ps1／tools/dev_start.ps1 既有 SSOT（R44 收斂）
. "$PSScriptRoot/../../tools/lib/WindowsAppsGuard.ps1"
if (-not (Test-IsRealPython -CandidateName 'python')) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

$env:PYTHONUTF8 = '1'
# 參數映射：-Act/-Pg → --act/--pg；-PytestArgs 依空白切割為位置參數（同收斂前 -split 語意）。
# 未指定（預設空字串）時一個位置參數都不附加 → 核心 DEFAULT_PYTEST_ARGS 生效（見檔頭 🔴）。
$CliArgs = @()
if ($Act) { $CliArgs += '--act' }
if ($Pg) { $CliArgs += '--pg' }
if ($PytestArgs) { $CliArgs += ($PytestArgs -split '\s+') }
& python (Join-Path $PSScriptRoot 'local_ci_gate.py') @CliArgs
exit $LASTEXITCODE
