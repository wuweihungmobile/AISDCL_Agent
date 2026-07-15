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

.EXAMPLE
  . "$PSScriptRoot/../../tools/lib/Find-GitBash.ps1"
  $bashExe = Find-GitBash
  if ($bashExe) { & $bashExe scripts/ci-gate.sh }
#>

function Find-GitBash {
  [CmdletBinding()]
  param()

  $bashCmd = Get-Command bash -ErrorAction SilentlyContinue
  if ($bashCmd -and $bashCmd.Source -and ($bashCmd.Source -notmatch '\\System32\\')) {
    return $bashCmd.Source
  }
  foreach ($cand in @("$env:ProgramFiles\Git\bin\bash.exe",
                      "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
                      "$env:LocalAppData\Programs\Git\bin\bash.exe")) {
    if ($cand -and (Test-Path -LiteralPath $cand)) { return $cand }
  }
  return $null
}
