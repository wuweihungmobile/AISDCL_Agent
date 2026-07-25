<#
.SYNOPSIS
AISDCL_Agent 整合層薄聚合閘門薄殼（Windows）。macOS/Linux 對等：tools/integration_gate.sh

.DESCRIPTION
  邏輯全部集中在 tools/integration_gate_core.py（跨平台單一事實源；DEF-101-068(b)
  收斂案，模式對齊 tools/dev_start.{py,sh,ps1} 與 AutoClaude/tools/local_ci_gate.{py,sh,ps1}）。
  本檔只做：確認直譯器 → 參數映射 → 轉呼叫核心 → 傳遞 exit code。薄殼由 monorepo 根
  tools/check_wrapper_thinness.py hash 釘選守門。介面（-SkipFull）與收斂前完全相容。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/integration_gate.ps1              # 完整
  powershell -ExecutionPolicy Bypass -File tools/integration_gate.ps1 -SkipFull    # 僅跑 [3/5]+[4/5]+[5/5]（開發快速迴圈）
#>
param(
    [switch]$SkipFull
)

# 直譯器選擇維持收斂前語意：PATH 上的 python（所有段落都靠已啟用的 venv），
# 未啟用 venv 就直接失敗提示（勝過各段落逐一噴錯）；WindowsApps 空殼排除
# 比照 tools/bootstrap.ps1／tools/dev_start.ps1 既有 SSOT（R44 收斂）
. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"
if (-not (Test-IsRealPython -CandidateName 'python')) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  exit 1
}

$env:PYTHONUTF8 = '1'
$CliArgs = @()
if ($SkipFull) { $CliArgs += '--skip-full' }
& python (Join-Path $PSScriptRoot 'integration_gate_core.py') @CliArgs
exit $LASTEXITCODE
