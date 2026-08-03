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

🔴 R67 B3（姊妹缺陷漏修 7 輪）：排除判定原本是行內 `-notlike '*\WindowsApps\*'`，
要求 WindowsApps 前後**都是反斜線**。但 Windows 的 `/` 與 `\` 是等價路徑分隔符，
而 `(Get-Command python).Source` 是「PATH 條目 + 檔名」拼出來的——PATH 條目以正
斜線書寫時 Source 就帶正斜線（同一機制在姊妹 capability 已有真機實測，見
`tools/lib/Find-GitBash.ps1` 檔頭 R60 P10-2 段：PS 5.1 上 `$env:PATH=
'C:/Windows/System32'` ⇒ `Source=C:/Windows/System32\bash.exe`）。R67 實測
（pwsh 7.6.3 -NoProfile，shadow `Get-Command` 餵入同一張 11 列樣本表）：
`C:/…/WindowsApps/python.exe`、`C:/…/WindowsApps\python.exe`、
`C:\…\Microsoft/WindowsApps\python.exe`、`C:\…\WindowsApps/python.exe`、
`/c/…/WindowsApps/python` 共 5 列本函式判「真 Python」，而另三份對稱實作
（`tools/lib/windowsapps_guard.sh`、`tools/bootstrap_core.py::
_is_windows_apps_stub`、`AutoClaude/autoclaude/execution/pre_run_validator.py::
_is_windows_apps_alias_stub`）一致判「空殼」＝同一組輸入、1 對 3 相反裁決，且
本 guard 整條失效（13 個 .ps1 呼叫端會改去執行 Store 空殼）。**另三份才是對的**
（正斜線寫法指向的是同一個空殼），故本檔改為同語意的逐段比對，手法比照 R60
P10-2 已在姊妹 capability 落地的 `tools/lib/Find-GitBash.ps1::
Test-HasSystem32Segment`。四份實作逐筆同判由
`tools/tests/test_windowsapps_guard_cross_consistency.py` ④ 節（`TestFourWay
VerdictParity` 等）的行為表 parity 鎖看著——該鎖真的起 PowerShell／bash 執行
本函式與 `.sh` 對稱實作，不只比對原始碼字面（ADR-XPLAT-002 §3.2 明令「字面
比對型 parity 鎖不計為機械釘選」）。

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

function Test-HasWindowsAppsSegment {
  # 是否含 WindowsApps 這一個**完整路徑段**（不分大小寫；`/` 與 `\` 皆為分隔符）。
  # 與另三份對稱實作同語意：`tools/bootstrap_core.py::_is_windows_apps_stub()` 與
  # `AutoClaude/autoclaude/execution/pre_run_validator.py::
  # _is_windows_apps_alias_stub()` 用 `PureWindowsPath(path).parts` 切段；
  # `tools/lib/windowsapps_guard.sh::is_real_python_candidate()` 用 `tr '\' '/'`
  # 正規化 + 前後補 `/` 定錨。逐段比對（而非 `-like` 子字串命中）才不會誤傷
  # `C:\Users\me\MyWindowsAppsBackup\python.exe` 這種使用者自訂安裝路徑
  # （bash 側 R43 二審修的就是那個偽陽性）。
  [CmdletBinding()]
  param([string]$Path)

  if ([string]::IsNullOrEmpty($Path)) { return $false }
  foreach ($segment in ($Path -split '[\\/]+')) {
    if ($segment.ToLowerInvariant() -eq 'windowsapps') { return $true }
  }
  return $false
}

function Test-IsRealPython {
  [CmdletBinding()]
  [OutputType([bool])]
  param(
    [Parameter(Mandatory = $true)]
    [string]$CandidateName
  )

  # `$cmd.Source` 為空（$null／空字串）時 `Test-HasWindowsAppsSegment` 回 $false
  # ⇒ 整式回 $true，與 R67 修改前 `$null -notlike '*\WindowsApps\*'` 的語意相同
  # （刻意不順手改成 fail-closed：本輪只修分隔符敏感這一個缺陷，Rule 3）。
  $cmd = Get-Command $CandidateName -ErrorAction SilentlyContinue
  return [bool]($cmd -and -not (Test-HasWindowsAppsSegment $cmd.Source))
}

# ─────────────────────────────────────────────────────────────────────────────
# R69 P2：「挑一個 >= 3.11 直譯器」候選鏈（PowerShell 側）。
# 與 tools/lib/windowsapps_guard.sh 的 `pick_python_ge_min` 同構（同一套候選鏈
# 語意、同一段探測碼、同形狀的 fail-loud 補救訊息）——雙平台落差本身就是 R69
# 要消滅的東西，故 mac 側修好、Windows 側不修 == 沒修完。
# WHY 併入本檔而非另開 lib：見 .sh 對稱實作上方的同名 WHY 區塊。
# 版本下限 SSOT＝tools/dev_start.py::_MIN_PY，由 tools/tests/test_dev_start.py::
# test_min_python_version_is_consistent_across_dev_start_ssots 機械鎖住三處同步。
$script:PythonGeMinMM = '3.11'
# 順序＝優先序，形狀對齊 tools/bootstrap_core.py::pick_python() 的 Windows 分支：
# `py` launcher 指定版最優先（官方多版本入口），再裸 python/python3。
$script:PythonGeMinCandidates = @(
  'py -3.11', 'py -3.12', 'py -3.13',
  'python3.11', 'python3.12', 'python3.13',
  'python', 'python3'
)
# 探測碼與 .sh 側 `PYTHON_GE_MIN_PROBE` 逐字相同：版本達標印直譯器絕對路徑，
# 否則印空字串。逐字相同由 tools/tests/test_dev_start.py::TestMinPythonVersionSsotSync
# ::test_version_probe_literal_is_byte_identical_across_both_shells 機械鎖住。
#
# 🔴 空字串寫 `str()` 而**不是** `""`（DEF-101-760；改回去 = 整條 guard 立刻復活成
# 死的）：Windows PowerShell 5.1 把參數交給**原生執行檔**時，會自己重組一次命令列
# 字串再讓 `CreateProcess`／`CommandLineToArgvW` 拆解，過程中**吃掉字串內嵌的一個
# 雙引號**。本機真機實測（powershell.exe 5.1，CP=950）：`else ""` 送到 python.exe
# 後 argv[1] 尾巴只剩一個 `"`，直譯器回
#   `SyntaxError: unterminated string literal (detected at line 1)` ⇒ rc=1
# ⇒ 迴圈把**每一個**候選都當成不合格 ⇒ `Get-PythonGeMin` 恆回 $null
# ⇒ `tools/dev_start.ps1` 的「無 .venv 開箱」路徑在全新 Windows 機器上直接死掉。
# `str()` 與 `""` 語意完全相同（皆為空字串）但**不含任何引號字元**，故對這個重組
# 過程免疫；bash 側同步採用同一寫法以維持逐字相同。
# 這條「原生指令引數的引號傳遞」由 tools/tests/test_ps51_compat.py::
# TestPs51NativeArgvRoundTrip 以真的起一支 powershell.exe 做 argv round-trip 看守
# （行級 regex 掃描器對此類缺陷架構上無能為力：它掃的是已被剝除字串的程式碼）。
$script:PythonGeMinProbe = 'import sys;print(sys.executable if sys.version_info[:2] >= (3, 11) else str())'

function Resolve-NativeExecutable {
  # 把候選命令名解析成「Windows 真能直接執行」的具體路徑；沒有就回 $null。
  #
  # WHY（DEF-101-759，本機 pyenv-win 真機才顯形）：pyenv-win 會在 shims 目錄
  # 同時放兩支同名檔——無副檔名的 POSIX `sh` wrapper（內容為
  # `#!/bin/sh` + `pyenv exec ...`，供 Git Bash/MSYS 使用）與對應的 `.bat`
  # （供 cmd/PowerShell 使用）。而 `Get-Command <裸名>` 回的**第一筆就是無副檔名
  # 那支**（實測 `Get-Command python3.11 -All` 順序：無副檔名 → .bat），
  # 因為 PowerShell 的命令探索不受 PATHEXT 約束。
  # 接著 `& $exe` 對它 CreateProcess 失敗、回退 ShellExecute，Windows 查不到
  # 副檔名關聯，於是**彈出「你要如何開啟這個檔案？」GUI 對話框**：
  #   · 互動式 → 每次探測騷擾使用者一次，且該次候選判定停在對話框上
  #   · 無人值守（schtasks／CI）→ 沒有桌面可彈，直接失敗或掛住
  # 雲端 Windows runner 不裝 pyenv，故此缺陷**只有真機跑得出來**。
  # 修法＝只接受副檔名落在 PATHEXT 內的候選（與 cmd.exe 的解析規則一致）。
  [CmdletBinding()]
  [OutputType([string])]
  param([Parameter(Mandatory = $true)][string]$CandidateName)

  # 🔴 PATHEXT 是 Windows-only 概念（DEF-101-766）：PS Core 跑在 macOS/Linux 時
  # `$env:PATHEXT` 不存在，且 POSIX 執行檔本來就不帶副檔名 ⇒ 若照 Windows 規則過濾，
  # **每一個候選都會被淘汰**，`Get-PythonGeMin` 於是恆回 $null——與本函式要修的
  # DEF-101-759 是同一個病，只是換平台發作。故非 Windows 平台直接退回「第一個
  # Application」，也就是本函式導入前的原行為（該平台上沒有 shim 歧義問題）。
  # 判定式順序不可調換：`$IsWindows` 在 PS 5.1 未定義，必須先由版本短路擋掉。
  # 左側版本比較先短路 ⇒ PS 5.1 上右側運算元永不被求值（5.1 恆 $null 的陷阱在此構不成），
  # 而 PS 6+ 上它才是唯一能分辨 Windows／非 Windows 的判準。此「短路必須在前」不是宣稱——由
  # tools/tests/test_dev_start.py::TestResolveNativeExecutableShortCircuitOrder 機械看守（兩側對調即紅）。
  $isWindowsHost = ($PSVersionTable.PSVersion.Major -lt 6) -or $IsWindows  # ps7-ok: 左側先短路，5.1 上不求值；順序由 TestResolveNativeExecutableShortCircuitOrder 機械看守
  if (-not $isWindowsHost) {
    foreach ($cmd in @(Get-Command $CandidateName -All -ErrorAction SilentlyContinue)) {
      if ($cmd.CommandType -eq 'Application') { return [string]$cmd.Source }
    }
    return $null
  }

  $exts = @(($env:PATHEXT -split ';') |
            Where-Object { $_ } |
            ForEach-Object { $_.Trim().ToLowerInvariant() })
  foreach ($cmd in @(Get-Command $CandidateName -All -ErrorAction SilentlyContinue)) {
    if ($cmd.CommandType -ne 'Application') { continue }
    $ext = [System.IO.Path]::GetExtension([string]$cmd.Source)
    if ($ext -and ($exts -contains $ext.ToLowerInvariant())) { return [string]$cmd.Source }
  }
  return $null
}

function Get-PythonGeMin {
  # 回傳第一個可用且 >= 3.11 的直譯器**絕對路徑**；一個都沒有回 $null。
  [CmdletBinding()]
  [OutputType([string])]
  param()

  foreach ($cand in $script:PythonGeMinCandidates) {
    $parts = $cand -split '\s+'
    $exe = $parts[0]
    # `py` launcher 不會被 Store 註冊成空殼（見檔頭），只需存在性檢查；
    # 裸 python/python3 候選才走 WindowsApps 空殼 guard。
    if ($exe -eq 'py') {
      if (-not (Get-Command 'py' -ErrorAction SilentlyContinue)) { continue }
    } elseif (-not (Test-IsRealPython -CandidateName $exe)) {
      continue
    } else {
      # DEF-101-759：裸名交給 `&` 會選到 pyenv-win 的無副檔名 POSIX shim
      # 並彈出 ShellExecute 對話框，故先解析成 PATHEXT 內的真執行檔再跑。
      $resolved = Resolve-NativeExecutable -CandidateName $exe
      if (-not $resolved) { continue }
      $exe = $resolved
    }
    $rest = @()
    if ($parts.Count -gt 1) { $rest = $parts[1..($parts.Count - 1)] }
    $out = $null
    try {
      $out = & $exe @rest -c $script:PythonGeMinProbe 2>$null
    } catch {
      continue
    }
    if ($LASTEXITCODE -ne 0) { continue }
    $first = @($out)[0]
    if ($first) { return ([string]$first).Trim() }
  }
  return $null
}

function Write-PythonGeMinRemediation {
  # fail-loud 補救指引——只印**逐字可執行**的指令（與 .sh 側
  # `python_ge_min_remediation` 同形狀）。
  [CmdletBinding()]
  param()

  Write-Host "❌ 找不到 Python >= $($script:PythonGeMinMM) 直譯器（dev_start 核心需 $($script:PythonGeMinMM)+）。" -ForegroundColor Red
  Write-Host "   已依序嘗試：$($script:PythonGeMinCandidates -join ' ')" -ForegroundColor Yellow
  Write-Host "   Windows 補救（擇一，逐字可執行）：" -ForegroundColor Yellow
  Write-Host "     winget install -e --id Python.Python.3.11" -ForegroundColor Yellow
  Write-Host "     winget install -e --id astral-sh.uv ; uv python install 3.11" -ForegroundColor Yellow
  Write-Host "   裝完請重開終端機（PATH 需重新載入）後再執行：. tools\dev_start.ps1" -ForegroundColor Yellow
}
