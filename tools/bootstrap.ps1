<#
.SYNOPSIS
monorepo 一鍵開發環境整備薄殼（Windows）。macOS/Linux 對等腳本：tools/bootstrap.sh

.DESCRIPTION
  邏輯全部集中在 tools/bootstrap_core.py（跨平台單一事實源；第 16 輪架構最佳化
  Architect 建議 B，模式對齊 AutoClaude/tools/local_ci_gate.{py,sh,ps1} 既有先例）。
  本檔只做：找一個可用的 python 直譯器（.venv 尚未存在，不可假設已啟用）→
  轉呼叫核心 → 傳遞 exit code。刻意不用 [CmdletBinding()]／具名參數（核心目前
  無任何旗標）：讓未被繫結的參數落入 $args 自動變數而非拋錯，維持與收斂前
  `param()`（零參數）相容之餘仍可原樣透傳。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
#>

$PyExe = $null
foreach ($candidate in @('python', 'py', 'python3')) {
  if (Get-Command $candidate -ErrorAction SilentlyContinue) {
    $PyExe = $candidate
    break
  }
}
if (-not $PyExe) {
  Write-Host "❌ 找不到 python/py/python3 — 無法啟動 bootstrap_core.py。請先安裝 Python >= 3.11。" -ForegroundColor Red
  exit 1
}

& $PyExe (Join-Path $PSScriptRoot 'bootstrap_core.py') @args
exit $LASTEXITCODE
