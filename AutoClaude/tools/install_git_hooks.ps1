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

if ($Uninstall) {
  git config --unset core.hooksPath 2>$null
  Write-Host '[install_git_hooks] 已移除 core.hooksPath（還原 .git/hooks 預設）' -ForegroundColor Yellow
  exit 0
}

$TopLevel = (git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0 -or -not $TopLevel) {
  Write-Host '[install_git_hooks] ❌ 不在 git repo 內（git rev-parse --show-toplevel 失敗）' -ForegroundColor Red
  exit 1
}
$HooksDir = Join-Path $TopLevel 'tools/git-hooks'

# 安裝前驗證：dispatcher hooks 必須存在
foreach ($h in @('pre-commit', 'pre-push')) {
  $p = Join-Path $HooksDir $h
  if (-not (Test-Path $p)) {
    Write-Host "[install_git_hooks] 缺少 dispatcher hook 檔：$p" -ForegroundColor Red
    exit 1
  }
}

git config core.hooksPath $HooksDir

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含兩支 hook 檔（杜絕假 ✅）
$cur = (git config --get core.hooksPath)
$curOk = ($cur) -and (Test-Path $cur -PathType Container) -and
         (Test-Path (Join-Path $cur 'pre-commit')) -and (Test-Path (Join-Path $cur 'pre-push'))
if ($curOk) {
  Write-Host "[install_git_hooks] ✅ 已啟用根層 dispatcher hooks：core.hooksPath = $cur" -ForegroundColor Green
  Write-Host '   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，'
  Write-Host '   依 commit/push 涉及路徑自動分流），不再互斥。'
  Write-Host '   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）'
  Write-Host '   pre-push    → pytest + import-linter + snapshot / ci-gate.sh（push 時）'
  Write-Host '   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify'
} else {
  Write-Host "[install_git_hooks] ❌ 設定失敗：core.hooksPath = '$cur'（目錄或 hook 檔不存在）" -ForegroundColor Red
  exit 1
}
