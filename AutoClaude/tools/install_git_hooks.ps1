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

# linked worktree 防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree
# 內執行會把 worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
# 偵測法：git-dir 與 git-common-dir 不同即是 linked worktree。
$GitDir = (git rev-parse --git-dir)
if ($LASTEXITCODE -ne 0 -or -not $GitDir) {
  Write-Host '[install_git_hooks] ❌ 不在 git repo 內（git rev-parse --git-dir 失敗）' -ForegroundColor Red
  exit 1
}
$GitCommonDir = (git rev-parse --git-common-dir)
$GitDirAbs = (Resolve-Path $GitDir).Path
$GitCommonDirAbs = (Resolve-Path $GitCommonDir).Path
if ($GitDirAbs -ne $GitCommonDirAbs) {
  Write-Host '[install_git_hooks] ❌ 偵測到 linked worktree（git-dir ≠ git-common-dir）' -ForegroundColor Red
  Write-Host '   core.hooksPath 寫入共享 .git/config，在 worktree 內安裝/卸載會毒化主 checkout'
  Write-Host '   （worktree 刪除後閘門靜默全滅）。請在主 checkout 執行安裝。'
  exit 1
}

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

# 安裝前驗證：dispatcher hooks 必須存在（post-commit 為 .git/hooks/post-commit 委派器）
foreach ($h in @('pre-commit', 'pre-push', 'post-commit')) {
  $p = Join-Path $HooksDir $h
  if (-not (Test-Path $p)) {
    Write-Host "[install_git_hooks] 缺少 dispatcher hook 檔：$p" -ForegroundColor Red
    exit 1
  }
}

git config core.hooksPath $HooksDir

# 安裝後驗證：core.hooksPath 與目標「正規化後等值」且目錄實際含三支 hook 檔（杜絕假 ✅）
$cur = (git config --get core.hooksPath)
$curNorm = if ($cur) { [System.IO.Path]::GetFullPath($cur).TrimEnd('\', '/') } else { '' }
$wantNorm = [System.IO.Path]::GetFullPath($HooksDir).TrimEnd('\', '/')
$curOk = ($cur) -and ($curNorm -eq $wantNorm) -and (Test-Path $cur -PathType Container) -and
         (Test-Path (Join-Path $cur 'pre-commit')) -and (Test-Path (Join-Path $cur 'pre-push')) -and
         (Test-Path (Join-Path $cur 'post-commit'))
if ($curOk) {
  Write-Host "[install_git_hooks] ✅ 已啟用根層 dispatcher hooks：core.hooksPath = $cur" -ForegroundColor Green
  Write-Host '   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，'
  Write-Host '   依 commit/push 涉及路徑自動分流），不再互斥。'
  Write-Host '   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）'
  Write-Host '   pre-push    → pytest + import-linter + snapshot / ci-gate.sh（push 時）'
  Write-Host '   post-commit → 委派回 .git/hooks/post-commit（advisory，不影響 commit）'
  Write-Host '   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify'
} else {
  Write-Host "[install_git_hooks] ❌ 設定失敗：core.hooksPath = '$cur'（目錄或 hook 檔不存在）" -ForegroundColor Red
  exit 1
}
