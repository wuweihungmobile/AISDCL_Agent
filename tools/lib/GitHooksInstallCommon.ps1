<#
.SYNOPSIS
共用 git hooks 安裝流程 — linked worktree 防護／HooksDir 正規化／安裝前後驗證／
Git Bash 缺失警告文案（DEF-101-068(c) / E23 抽出；獨立複審 finding 後改為薄殼層）。

.DESCRIPTION
判定邏輯的單一真相源是 tools/git_hooks_install_common.py（供本檔與
tools/lib/git_hooks_install_common.sh 兩份 thin wrapper 呼叫，兩者只保留該平台
原生的呈現層 —— PowerShell 的 Write-Host 顏色／exit 慣例 —— 不再各自重寫判定
邏輯本身）：任一處修 bug（如 linked worktree 偵測、HooksDir 正規化演算法）只需
改 tools/git_hooks_install_common.py 一處，不必人工同步兩份呼叫端。

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

.NOTES
  僅供「子行程/獨立腳本方式」呼叫的上層 .ps1 dot-source 本檔（如上例）。若在
  互動式 shell 直接手動 dot-source 本檔以逐一測試函式，失敗分支會改用 return
  （見下方 dot-source 陷阱防護），不會誤殺你的互動 shell，但也代表失敗時呼叫
  鏈不會像生產路徑一樣中止——僅供探索/除錯用途，正式安裝請透過既有呼叫端腳本。
#>

$script:GitHooksInstallCommonPy = [System.IO.Path]::GetFullPath(
  (Join-Path $PSScriptRoot '../git_hooks_install_common.py'))

# dot-source 陷阱防護（DEF-101-261，R27 訂正 DEF-101-272）：互動式手動 dot-source
# 本檔命中失敗分支若直接 exit 1 會關掉整個 shell，故需判斷是否為腳本驅動。舊版
# （R23~R26）只看呼叫棧**最外層** frame 的 ScriptName：巢狀呼叫（如
# `-Command "...; ./windows_smoke_local.ps1"`、該 .ps1 內再 `& $installer` 呼叫
# install_git_hooks.ps1）下最外層是 `-Command` 命令列本身（ScriptName 空），
# 合法腳本驅動鏈被誤判互動式，防呆靜默失效（R27 實測重現：[3][4] rc=1→0/哨兵9）。
# 改看**呼叫棧[1]**（本檔 dot-source 點的直接呼叫者，非本檔自身/非最外層）：
# 純互動 `-Command ". thisFile"` 時 [1] 為空白 ScriptBlock → return；被任何真實
# .ps1 dot-source 進去時，無論該 .ps1 再往上被如何呼叫，[1] 恆非空 → exit。
$script:GitHooksInstallCommonScriptDriven = [bool]((Get-PSCallStack)[1].ScriptName)
# venv 提示：下列各函式都靠裸 python 呼叫 GitHooksInstallCommonPy，未啟用 venv 就
# 直接失敗提示（勝過各函式逐一噴原生「'python' 不是內部或外部命令」）——與
# tools/integration_gate.ps1 / AutoClaude/tools/local_ci_gate.ps1 的
# `Get-Command python` 前置守門對稱，dot-source 本檔時即檢查一次。
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host '❌ 找不到 python — 請先啟用 venv：.venv\Scripts\Activate.ps1（見 ONBOARDING.md §3）' -ForegroundColor Red
  # 頂層本體（不在函式內）呼叫 exit 只終止本檔自身載入、不終止外層呼叫行程
  # （與下方函式內 exit 語意不同）；裸 `exit 1` 會讓 script-driven 呼叫端不受
  # 阻擋繼續跑，違反 fail-loud（DEF-101-261 追加修復，R23 SA/QA 命中）。
  if ($script:GitHooksInstallCommonScriptDriven) { [Environment]::Exit(1) } else { return }
}

function Assert-NotLinkedWorktree {
  <#
  .SYNOPSIS
  防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree 內執行會把
  worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
  判定邏輯見 tools/git_hooks_install_common.py 的 `assert-not-linked-worktree`
  子指令；失敗時該子指令已把錯誤訊息印到 stderr，本函式只負責 exit 1。
  #>
  [CmdletBinding()]
  param([string]$Prefix = '')

  # 注意：PowerShell 呼叫原生 exe 時，空字串引數（$Prefix 預設值）在分離成兩個
  # token（`--prefix` `''`）時會被靜默吞掉（PS 5.1 實測重現：argparse 收到
  # `--prefix` 卻找不到值報錯），故一律用單一 token 的 `--prefix=值` 形式。
  & python $script:GitHooksInstallCommonPy assert-not-linked-worktree "--prefix=$Prefix"
  if ($LASTEXITCODE -ne 0) {
    if ($script:GitHooksInstallCommonScriptDriven) { exit 1 } else { return }
  }
}

function Get-DispatcherHooksDir {
  <#
  .SYNOPSIS
  回傳根層 dispatcher hooks 目錄（<repo根>/tools/git-hooks，絕對路徑）。
  失敗（不在 git repo 內）時直接 exit 1。演算法見 tools/git_hooks_install_common.py
  的 `get-hooks-dir` 子指令。
  #>
  [CmdletBinding()]
  param([string]$Prefix = '')

  $out = & python $script:GitHooksInstallCommonPy get-hooks-dir "--prefix=$Prefix"
  if ($LASTEXITCODE -ne 0) {
    if ($script:GitHooksInstallCommonScriptDriven) { exit 1 } else { return }
  }
  return ($out | Select-Object -Last 1)
}

function Test-DispatcherHooksPresent {
  <#
  .SYNOPSIS
  安裝前驗證：dispatcher hooks（pre-commit / pre-push / post-commit）必須存在，
  缺一即 exit 1（post-commit 為 .git/hooks/post-commit 委派器）。判定邏輯見
  tools/git_hooks_install_common.py 的 `assert-hooks-present` 子指令。
  #>
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$HooksDir,
    [string]$Prefix = ''
  )

  & python $script:GitHooksInstallCommonPy assert-hooks-present $HooksDir "--prefix=$Prefix"
  if ($LASTEXITCODE -ne 0) {
    if ($script:GitHooksInstallCommonScriptDriven) { exit 1 } else { return }
  }
}

function Test-GitHooksPathInstalled {
  <#
  .SYNOPSIS
  安裝後驗證：core.hooksPath 與目標「正規化後等值」且目錄實際含三支 hook 檔
  （杜絕假 ✅）。回傳 PSCustomObject { Cur; Ok }，不 exit（由呼叫端決定成功/失敗訊息）。
  判定邏輯見 tools/git_hooks_install_common.py 的 `check-installed` 子指令。
  #>
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$HooksDir)

  $lines = & python $script:GitHooksInstallCommonPy check-installed $HooksDir
  $cur = ''
  $ok = $false
  foreach ($line in $lines) {
    if ($line -like 'CUR=*') { $cur = $line.Substring(4) }
    if ($line -like 'OK=*') { $ok = ($line.Substring(3) -eq '1') }
  }
  return [PSCustomObject]@{ Cur = $cur; Ok = $ok }
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
