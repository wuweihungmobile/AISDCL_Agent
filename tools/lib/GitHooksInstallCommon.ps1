<#
.SYNOPSIS
共用 git hooks 安裝流程 — linked worktree 防護／HooksDir 正規化／安裝前後驗證／
Git Bash 缺失警告文案（DEF-101-068(c) / E23 抽出）。

.DESCRIPTION
逐行比對 AutoClaude/tools/install_git_hooks.ps1 與 AISDLC_SDD/scripts/install-hooks.ps1
全文（各約 92-115 行）發現：linked worktree 偵測（git-dir vs git-common-dir 比對）、
HooksDir 正規化、安裝前存在性驗證迴圈、安裝後 curOk 正規化比對驗證、Git Bash 缺失
警告文案這五個區塊，兩檔中近乎逐字相同（只有訊息前綴與少數文字不同），共用範圍約占
每檔 115 行中的 90 行。抽出為本檔單一真相源，任一處修 bug（如 F1 PATH fallback）
只需改一處，不必人工同步兩份呼叫端。

呼叫端各自保留的部分（不在本檔內，維持產品特有文案）：
  - 是否支援 -Uninstall（僅 AutoClaude 版有）
  - 安裝成功後的閘門說明文字（兩專案 pre-commit/pre-push 內容不同）

.EXAMPLE
  . "$PSScriptRoot/../../tools/lib/GitHooksInstallCommon.ps1"
  Assert-NotLinkedWorktree -Prefix '[install_git_hooks] '
  $HooksDir = Get-DispatcherHooksDir -Prefix '[install_git_hooks] '
  Test-DispatcherHooksPresent -HooksDir $HooksDir -Prefix '[install_git_hooks] '
  git config core.hooksPath $HooksDir
  $result = Test-GitHooksPathInstalled -HooksDir $HooksDir
  if ($result.Ok) { ... } else { ... }
#>

function Assert-NotLinkedWorktree {
  <#
  .SYNOPSIS
  防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree 內執行會把
  worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
  偵測法：git-dir 與 git-common-dir 不同即是 linked worktree。
  失敗時直接 exit 1（含「不在 git repo 內」與「偵測到 linked worktree」兩種情境）。
  #>
  [CmdletBinding()]
  param([string]$Prefix = '')

  $GitDir = (git rev-parse --git-dir)
  if ($LASTEXITCODE -ne 0 -or -not $GitDir) {
    Write-Host "${Prefix}❌ 不在 git repo 內（git rev-parse --git-dir 失敗）" -ForegroundColor Red
    exit 1
  }
  $GitCommonDir = (git rev-parse --git-common-dir)
  $GitDirAbs = (Resolve-Path $GitDir).Path
  $GitCommonDirAbs = (Resolve-Path $GitCommonDir).Path
  if ($GitDirAbs -ne $GitCommonDirAbs) {
    Write-Host "${Prefix}❌ 偵測到 linked worktree（git-dir ≠ git-common-dir）" -ForegroundColor Red
    Write-Host '   core.hooksPath 寫入共享 .git/config，在 worktree 內安裝/卸載會毒化主 checkout'
    Write-Host '   （worktree 刪除後閘門靜默全滅）。請在主 checkout 執行安裝。'
    exit 1
  }
}

function Get-DispatcherHooksDir {
  <#
  .SYNOPSIS
  回傳根層 dispatcher hooks 目錄（<repo根>/tools/git-hooks，絕對路徑、正規化分隔符）。
  失敗（不在 git repo 內）時直接 exit 1。

  .DESCRIPTION
  `git rev-parse --show-toplevel` 回傳正斜線路徑，Join-Path 用反斜線銜接會產出混合
  分隔符字串（下游 tools/integration_gate.*、AutoClaude/tools/local_ci_gate.* 各自
  正規化補丁才能吃）。改於源頭一次正規化，下游既有補丁邏輯保留不動。
  #>
  [CmdletBinding()]
  param([string]$Prefix = '')

  $TopLevel = (git rev-parse --show-toplevel)
  if ($LASTEXITCODE -ne 0 -or -not $TopLevel) {
    Write-Host "${Prefix}❌ 不在 git repo 內（git rev-parse --show-toplevel 失敗）" -ForegroundColor Red
    exit 1
  }
  return [System.IO.Path]::GetFullPath((Join-Path $TopLevel 'tools/git-hooks'))
}

function Test-DispatcherHooksPresent {
  <#
  .SYNOPSIS
  安裝前驗證：dispatcher hooks（pre-commit / pre-push / post-commit）必須存在，
  缺一即 exit 1（post-commit 為 .git/hooks/post-commit 委派器）。
  #>
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$HooksDir,
    [string]$Prefix = ''
  )

  foreach ($h in @('pre-commit', 'pre-push', 'post-commit')) {
    $p = Join-Path $HooksDir $h
    if (-not (Test-Path $p)) {
      Write-Host "${Prefix}缺少 dispatcher hook 檔：$p" -ForegroundColor Red
      exit 1
    }
  }
}

function Test-GitHooksPathInstalled {
  <#
  .SYNOPSIS
  安裝後驗證：core.hooksPath 與目標「正規化後等值」且目錄實際含三支 hook 檔
  （杜絕假 ✅）。回傳 PSCustomObject { Cur; Ok }，不 exit（由呼叫端決定成功/失敗訊息）。
  #>
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$HooksDir)

  $cur = (git config --get core.hooksPath)
  $curNorm = if ($cur) { [System.IO.Path]::GetFullPath($cur).TrimEnd('\', '/') } else { '' }
  $wantNorm = [System.IO.Path]::GetFullPath($HooksDir).TrimEnd('\', '/')
  $curOk = ($cur) -and ($curNorm -eq $wantNorm) -and (Test-Path $cur -PathType Container) -and
           (Test-Path (Join-Path $cur 'pre-commit')) -and (Test-Path (Join-Path $cur 'pre-push')) -and
           (Test-Path (Join-Path $cur 'post-commit'))
  return [PSCustomObject]@{ Cur = $cur; Ok = $curOk }
}

function Write-GitBashMissingWarning {
  <#
  .SYNOPSIS
  Mac/Windows 相容性警告：dispatcher hooks（pre-commit/pre-push/post-commit）皆為
  #!/usr/bin/env bash，需要 Git for Windows 內建的 Git Bash 才能執行；core.hooksPath
  設定成功不代表 commit/push 時真的能跑。僅警告、不阻斷安裝。
  #>
  [CmdletBinding()]
  param()

  Write-Host '   ⚠️  偵測不到 Git Bash（bash.exe）：上述 dispatcher hooks 皆為 bash 腳本，' -ForegroundColor Yellow
  Write-Host '       需要 Git for Windows 內建的 Git Bash 才能執行；若非標準 Git for Windows' -ForegroundColor Yellow
  Write-Host '       安裝，commit/push 時可能因找不到直譯器而中止。建議安裝 Git for Windows。' -ForegroundColor Yellow
}
