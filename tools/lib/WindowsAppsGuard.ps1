<#
.SYNOPSIS
共用 WindowsApps 空殼 Python 候選排除 guard — R37 抽出（Architect 架構最佳化建議）。

.DESCRIPTION
原判斷邏輯（`Get-Command <候選名>` → 取 `.Source` → 用
`-notlike '*\WindowsApps\*'` 排除 Windows Store App Execution Alias 空殼）在
`tools/bootstrap.ps1`（`python`／`python3` 兩處候選）與 `tools/dev_start.ps1`
（`python` 一處候選）共逐字內嵌三份，彼此互不相通，同一缺陷類別連續復發
（DEF-101-273／279／300／303）。本檔抽出為單一真相源，供三處呼叫點 dot-source
後改一行呼叫（比照 `tools/lib/Find-GitBash.ps1` 既有先例 S11 同款模式）。R38
起 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.ps1`
亦改 dot-source 呼叫本檔（第 4 個呼叫點；Architect 一審 REJECT 原地內嵌
的第 4~5 個獨立副本並收斂）。

全新 Windows 11 機器未裝真 Python 時，`Get-Command python`／`Get-Command python3`
仍會找到 WindowsApps 底下系統自動註冊的空殼 `python.exe`／`python3.exe`——
`shutil.which()`／`Get-Command` 找得到、但實際執行只會跳出 Microsoft Store
安裝提示，不會執行任何 Python 程式碼。`py` launcher 候選不需要本 guard：
Windows Store 的 App Execution Alias 只自動註冊 `python.exe`／`python3.exe`
空殼，不會註冊 `py.exe`——命中即代表可信任（呼叫端維持原有判斷，本函式
不處理 `py` 候選）。

呼叫端只需傳入候選命令的**字面名稱**（如 `'python'`／`'python3'`），函式內部
自行呼叫 `Get-Command` 並回傳布林值——呼叫端不再需要自行宣告
`$PyCand`/`$Py3Cand` 這類中繼變數，DEF-101-303 描述的「變數與命令名稱錯配」
（複製貼上時把兩個中繼變數互換）在此架構下已無存在空間：呼叫端只是
`if (Test-IsRealPython -CandidateName 'python') { ... }` 這種直接傳字面值的
單行判斷式，沒有「兩個變數」可供互換。

Python 側對稱實作見 `tools/bootstrap_core.py::_is_windows_apps_stub()`（不同
語言的獨立實作，語言邊界問題不在本次收斂範圍內，維持不動）。

.PARAMETER CandidateName
`Get-Command` 要查詢的候選命令字面名稱（如 `'python'`／`'python3'`）。

.OUTPUTS
[bool] — `$true` 表示該候選命令存在且非 WindowsApps 空殼（可信任使用）；
`$false` 表示候選命令不存在，或存在但為 WindowsApps 空殼（應排除）。

.EXAMPLE
  . "$PSScriptRoot/lib/WindowsAppsGuard.ps1"
  if (Test-IsRealPython -CandidateName 'python') { $PyExe = 'python' }
#>

function Test-IsRealPython {
  [CmdletBinding()]
  [OutputType([bool])]
  param(
    [Parameter(Mandatory = $true)]
    [string]$CandidateName
  )

  $cmd = Get-Command $CandidateName -ErrorAction SilentlyContinue
  return [bool]($cmd -and $cmd.Source -notlike '*\WindowsApps\*')
}
