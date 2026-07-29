<#
.SYNOPSIS
共用 Git Bash（bash.exe）偵測函式 — S11 抽出。

.DESCRIPTION
原偵測邏輯（PATH 找 bash → 排除 WSL System32 佔位 → PATH 找不到再查常見安裝路徑
fallback）在三支 .ps1（AISDLC_SDD/scripts/ci-gate.ps1、AutoClaude/tools/
install_git_hooks.ps1、AISDLC_SDD/scripts/install-hooks.ps1）逐行複製，抽出為
本檔單一真相源，供三個呼叫點 dot-source 後改一行呼叫（DEF-101-068(c) / S11）。

標準 Git for Windows 安裝預設只把 Git\cmd 加進 PATH，Git\bin\bash.exe 本來就
不在 PATH（官方建議設定），單查 PATH 會對絕大多數標準安裝誤報「找不到 Git Bash」。
排除 WSL 的 System32\bash.exe：那是 Linux 環境（無本 repo 的 Windows venv/依賴），
與其等同視之不對等。

🔴 R60 P10-2（真 parity 缺陷）：排除判定原本是行內 regex `-notmatch '\\System32\\'`，
要求 System32 前後**都是反斜線**。但 Windows 的 `/` 與 `\` 是等價路徑分隔符（實測
`Test-Path -LiteralPath 'C:/Windows/System32/bash.exe'` 為 True，與反斜線寫法指向同一
個檔案），而 `(Get-Command bash).Source` 是「PATH 條目 + 檔名」拼出來的——PATH 條目
以正斜線書寫時 Source 就帶正斜線。實測（本機 PS 5.1，`$env:PATH='C:/Windows/System32'`）：
Source=`C:/Windows/System32\bash.exe`、舊 regex 判 accepts=True、`Find-GitBash` 因此
**回傳了 WSL 的 bash**＝guard 整條失效。對照側 `tools/integration_gate_core.py::
_has_system32_segment()` 用 `PureWindowsPath` 逐段比對（`/` 與 `\` 皆視為分隔符），
同一組輸入判「排除」——兩側對同一個問題給出相反答案。**Python 側才是對的**（目的是
避開 WSL 啟動器，而正斜線寫法就是同一支 WSL bash），故本檔改為同語意的逐段比對。
兩側逐筆同判由 `tools/tests/test_find_git_bash_parity.py` 的行為表 parity 鎖看著
（該鎖真的起 PowerShell 執行本函式，不只比對原始碼字面）。

判準邊界（刻意不處理、不靜默略過）：`C:\Windows\Sysnative\bash.exe` 兩側一致**不**
排除。Sysnative 是 32-bit 行程看到的 64-bit System32 別名，指向的其實是同一支 WSL
bash；不在本輪處理是因為排除段字面值 `system32` 是 `tools/lib/bash_probe_spec.py`
的共用常數，5 個 Python 消費點（含 3 份刻意獨立重寫的回歸鎖）都吃它，把它擴成集合
會牽動本輪所有權外的檔案。此為已知殘餘盲區，非「已驗證安全」。

.EXAMPLE
  . "$PSScriptRoot/../../tools/lib/Find-GitBash.ps1"
  $bashExe = Find-GitBash
  if ($bashExe) { & $bashExe scripts/ci-gate.sh }
#>

function Test-HasSystem32Segment {
  # 是否含 System32 這一個**完整路徑段**（不分大小寫；`/` 與 `\` 皆為分隔符）。
  # 與 tools/integration_gate_core.py::_has_system32_segment() 同語意：後者用
  # `PureWindowsPath(path).parts` 切段，本函式用 regex 字元類 `[\\/]+` 切段。
  # 逐段比對（而非子字串命中）才不會誤傷 `C:\MySystem32Tools\bash.exe` 這種
  # 使用者自訂安裝路徑（DEF-101-236 修的就是那個偽陽性）。
  [CmdletBinding()]
  param([string]$Path)

  if ([string]::IsNullOrEmpty($Path)) { return $false }
  foreach ($segment in ($Path -split '[\\/]+')) {
    if ($segment.ToLowerInvariant() -eq 'system32') { return $true }
  }
  return $false
}

function Find-GitBash {
  [CmdletBinding()]
  param()

  $bashCmd = Get-Command bash -ErrorAction SilentlyContinue
  if ($bashCmd -and $bashCmd.Source -and -not (Test-HasSystem32Segment $bashCmd.Source)) {
    return $bashCmd.Source
  }
  # DEF-101-236 修復：先前對 $env:ProgramFiles(x86) 等環境變數不存在時直接做字串
  # 插值，未設定時會插出空字串（如 "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
  # 缺變數時變成裸路徑 "\Git\bin\bash.exe"），仍會呼叫 Test-Path——比對端
  # tools/integration_gate_core.py::find_git_bash() 對此明確 `if not base: continue`
  # 跳過。改用 GetEnvironmentVariable + 明確空值判斷對齊兩邊行為。
  foreach ($envVarName in @('ProgramFiles', 'ProgramFiles(x86)', 'LocalAppData')) {
    $base = [System.Environment]::GetEnvironmentVariable($envVarName)
    if (-not $base) { continue }
    $sub = if ($envVarName -eq 'LocalAppData') { 'Programs\Git\bin\bash.exe' } else { 'Git\bin\bash.exe' }
    $cand = Join-Path $base $sub
    if (Test-Path -LiteralPath $cand) { return $cand }
  }
  return $null
}
