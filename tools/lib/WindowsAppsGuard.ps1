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

.NOTES
覆蓋邊界（R58 真 Windows 11 實機量測，三段式；勿改寫成「保證候選可用」）：
本函式是**純路徑字串比對**（`Get-Command` 取 `.Source` 後比對路徑片段），刻意
不執行候選直譯器——bootstrap 悖論下它必須零成本、無副作用。

已實測涵蓋：`Get-Command` 命中 `…\WindowsApps\…` 底下的 Windows Store App
  Execution Alias 空殼（`-notlike` 本身大小寫不敏感）。
已實測不涵蓋：pyenv-win shim 這類「PATH 上有、`Get-Command` 找得到、實際執行
  卻不是可用直譯器」的第二種形狀。R58 以固定 fixture 實測（`$env:PATH` 只留
  fixture 目錄）：對「印訊息到 stderr 後非零退出」（模擬 pyenv `No global/local
  python version has been set`）與「零退出但不執行任何 Python」兩種假 shim，
  `Get-Command` 皆命中該 `python3.bat`、本函式**皆回傳 `$true`**，隨後真的執行
  它時才失敗（`$LASTEXITCODE` 分別為 1 與 0）。bash 側
  `tools/lib/windowsapps_guard.sh::is_real_python_candidate` 在同款 fixture 下
  同樣回傳 ACCEPTED，兩份 guard 對稱地看不到這一類；Python 側
  `tools/bootstrap_core.py::pick_python()` 則在路徑比對之後另有 `_probe_ok()`
  執行探測層（bash／ps1 兩側沒有對應層）。
未窮舉：其他「存在但不可用」形狀（權限不足、DLL 缺失、其他 version manager 的
  shim）皆未逐一量測。

為什麼不在此補探測：修法應落在呼叫端已確定要用該直譯器之後加一道極輕探測，
而不是把成本壓進這支被多個閘門載入的純函式。

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
