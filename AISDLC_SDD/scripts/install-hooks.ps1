# AISDLC-SDD — 安裝 git hooks（Windows PowerShell 版）。
# monorepo 單一 git repo：設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，
# 根層 dispatcher），依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效
# （不再互斥）：AISDLC_SDD/ 變更 → .githooks/pre-push（scripts/ci-gate.sh）；
# AutoClaude/ 變更 → AutoClaude/tools/git-hooks/pre-commit + pre-push。
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# linked worktree 防護／HooksDir 正規化／安裝前後驗證／Git Bash 缺失警告文案抽共用
# （DEF-101-068(c) / E23：與 AutoClaude/tools/install_git_hooks.ps1 近乎逐字重複的
# 90 行機械邏輯已抽出單一真相源）：見 tools/lib/GitHooksInstallCommon.ps1。
. "$PSScriptRoot/../../tools/lib/GitHooksInstallCommon.ps1"

Assert-NotLinkedWorktree

$HooksDir = Get-DispatcherHooksDir
Test-DispatcherHooksPresent -HooksDir $HooksDir

git config core.hooksPath $HooksDir

$installed = Test-GitHooksPathInstalled -HooksDir $HooksDir
if ($installed.Ok) {
  Write-Host "✅ 已啟用根層 dispatcher hooks：core.hooksPath=$($installed.Cur)" -ForegroundColor Green
  Write-Host "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  Write-Host "   依 commit/push 涉及路徑自動分流），不再互斥。"
  Write-Host "   AISDLC_SDD pre-push 閘門：push 涉及 AISDLC_SDD/ 時自動跑 scripts/ci-gate.sh"

  # Mac/Windows 相容性優化（四方複審 R1 SA 發現）：dispatcher hooks（pre-commit/pre-push/
  # post-commit）皆為 #!/usr/bin/env bash，需要 Git for Windows 內建的 Git Bash 才能執行；
  # 原文字「Git for Windows 會用內建 bash 執行 hook 本體」是無保留的斷言，非標準 Git for
  # Windows 安裝（缺 Git Bash）時仍會回報安裝成功，但 commit/push 才會遇到難懂錯誤。
  # 此處僅警告、不阻斷安裝。偵測邏輯抽共用（S11）：見 tools/lib/Find-GitBash.ps1。
  . "$PSScriptRoot/../../tools/lib/Find-GitBash.ps1"
  $bashExe = Find-GitBash
  if (-not $bashExe) {
    Write-GitBashMissingWarning
  }
} else {
  Write-Host "❌ 設定失敗：core.hooksPath='$($installed.Cur)'（目錄或 hook 檔不存在）" -ForegroundColor Red
  exit 1
}
