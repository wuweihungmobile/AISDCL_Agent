<#
.SYNOPSIS
安裝 monorepo 根層 dispatcher git hooks（設 core.hooksPath=<repo根>/tools/git-hooks，絕對路徑）。

.DESCRIPTION
零依賴方式啟用 pre-commit / pre-push 攔截點，讓系統強制把關（取代人工記憶跑測試）。
core.hooksPath 指向根層 dispatcher，依 commit/push 涉及路徑自動分流，
兩子專案閘門同時生效（不再互斥）：
  AutoClaude/ 變更  → AutoClaude/tools/git-hooks/pre-commit + pre-push
  AISDLC_SDD/ 變更 → AISDLC_SDD/.githooks/pre-push

  pre-commit：ruff / LOC 預算 / CLAUDE.md<=400 / .sh LF（快，< 15s）
  pre-push  ：pytest + import-linter + snapshot（完整本機 CI 閘門）

.PARAMETER Uninstall
還原 core.hooksPath（改回 .git/hooks 預設）。
#>
[CmdletBinding()]
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$Prefix = '[install_git_hooks] '

# linked worktree 防護／HooksDir 正規化／安裝前後驗證／Git Bash 缺失警告文案抽共用
# （DEF-101-068(c) / E23：與 AISDLC_SDD/scripts/install-hooks.ps1 近乎逐字重複的
# 90 行機械邏輯已抽出單一真相源）：見 tools/lib/GitHooksInstallCommon.ps1。
. "$PSScriptRoot/../../tools/lib/GitHooksInstallCommon.ps1"

Assert-NotLinkedWorktree -Prefix $Prefix

if ($Uninstall) {
  git config --unset core.hooksPath 2>$null
  Write-Host "${Prefix}已移除 core.hooksPath（還原 .git/hooks 預設）" -ForegroundColor Yellow
  exit 0
}

$HooksDir = Get-DispatcherHooksDir -Prefix $Prefix
Test-DispatcherHooksPresent -HooksDir $HooksDir -Prefix $Prefix

git config core.hooksPath $HooksDir

$installed = Test-GitHooksPathInstalled -HooksDir $HooksDir
if ($installed.Ok) {
  Write-Host "${Prefix}✅ 已啟用根層 dispatcher hooks：core.hooksPath = $($installed.Cur)" -ForegroundColor Green
  Write-Host '   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，'
  Write-Host '   依 commit/push 涉及路徑自動分流），不再互斥。'
  Write-Host '   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）'
  Write-Host '   pre-push    → pytest + import-linter + snapshot / ci-gate.sh（push 時）'
  Write-Host '   post-commit → 委派回 .git/hooks/post-commit（advisory，不影響 commit）'
  Write-Host '   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify'

  # Mac/Windows 相容性優化：dispatcher hooks（pre-commit/pre-push/post-commit）皆為
  # #!/usr/bin/env bash，需 POSIX shell 直譯器才能執行。core.hooksPath 設定成功不代表
  # commit/push 時真的能跑——非標準 Git for Windows 安裝（缺 Git Bash）會讓使用者要到
  # 第一次 commit/push 才遇到難懂錯誤。此處僅警告、不阻斷安裝（理論上仍可能有其他方式
  # 讓 bash 可執行）。偵測邏輯抽共用（S11）：見 tools/lib/Find-GitBash.ps1。
  . "$PSScriptRoot/../../tools/lib/Find-GitBash.ps1"
  $bashExe = Find-GitBash
  if (-not $bashExe) {
    Write-GitBashMissingWarning
  }
} else {
  Write-Host "${Prefix}❌ 設定失敗：core.hooksPath = '$($installed.Cur)'（目錄或 hook 檔不存在）" -ForegroundColor Red
  exit 1
}
