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

# WindowsApps 空殼排除 guard 共用實作（R37 抽出，DEF-101-273/279/300/303 反覆
# 復發後收斂為單一真相源）：見 tools/lib/WindowsAppsGuard.ps1。
. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"

$PyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
  # `py` launcher 不需要 WindowsApps 排除 guard：Windows Store 的 App Execution
  # Alias 只自動註冊 python.exe／python3.exe 空殼，不會註冊 py.exe——`py` 只在
  # 真的裝了 Python（或等效安裝程式）時才會出現，命中即代表可信任。
  $PyExe = 'py'
} else {
  # 排除 Windows Store App Execution Alias stub（DEF-101-273，比照 tools/dev_start.ps1
  # 既有 guard）：全新 Windows 11 機器未裝真 Python 時，`Get-Command python` 仍會找到
  # WindowsApps 底下的空殼 python.exe（實際執行只跳出 Microsoft Store 提示，不會執行
  # 任何 Python 程式碼）；本檔是「`.venv` 尚未存在、不可假設已啟用」的第一步 onboarding
  # 入口，恰是最需要此 guard 的情境，故候選順序改為 py → python（排除 WindowsApps）→
  # python3（排除 WindowsApps）。dev_start.ps1 同款 guard 邏輯一致，但候選清單非逐字
  # 相同（該檔假設 venv 可能已啟用、無 python3 兜底；本檔 venv 尚不存在，保留 python3
  # 作為第三候選）。DEF-101-279：python3 分支原本沒有同款 guard——全新 Windows 11
  # 機器上 python.exe 與 python3.exe 常常都是系統自動註冊的 WindowsApps 空殼，漏 guard
  # 會讓 python3 分支重現與 DEF-101-273 相同的失敗模式，故此處補齊同款排除。
  if (Test-IsRealPython -CandidateName 'python') {
    $PyExe = 'python'
  } else {
    if (Test-IsRealPython -CandidateName 'python3') {
      $PyExe = 'python3'
    }
  }
}
if (-not $PyExe) {
  Write-Host "❌ 找不到 python/py/python3 — 無法啟動 bootstrap_core.py。請先安裝 Python >= 3.11。" -ForegroundColor Red
  exit 1
}

& $PyExe (Join-Path $PSScriptRoot 'bootstrap_core.py') @args
exit $LASTEXITCODE
