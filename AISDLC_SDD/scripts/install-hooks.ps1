# AISDLC-SDD — 安裝 git hooks（Windows PowerShell 版）。
# monorepo 單一 git repo：設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，
# 根層 dispatcher），依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效
# （不再互斥）：AISDLC_SDD/ 變更 → .githooks/pre-push（scripts/ci-gate.sh）；
# AutoClaude/ 變更 → AutoClaude/tools/git-hooks/pre-commit + pre-push。
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# linked worktree 防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree
# 內執行會把 worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
# 偵測法：git-dir 與 git-common-dir 不同即是 linked worktree。
$GitDir = (git rev-parse --git-dir)
if ($LASTEXITCODE -ne 0 -or -not $GitDir) {
  Write-Host '❌ 不在 git repo 內（git rev-parse --git-dir 失敗）' -ForegroundColor Red
  exit 1
}
$GitCommonDir = (git rev-parse --git-common-dir)
$GitDirAbs = (Resolve-Path $GitDir).Path
$GitCommonDirAbs = (Resolve-Path $GitCommonDir).Path
if ($GitDirAbs -ne $GitCommonDirAbs) {
  Write-Host '❌ 偵測到 linked worktree（git-dir ≠ git-common-dir）' -ForegroundColor Red
  Write-Host '   core.hooksPath 寫入共享 .git/config，在 worktree 內安裝/卸載會毒化主 checkout'
  Write-Host '   （worktree 刪除後閘門靜默全滅）。請在主 checkout 執行安裝。'
  exit 1
}

$TopLevel = (git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0 -or -not $TopLevel) {
  Write-Host "❌ 不在 git repo 內（git rev-parse --show-toplevel 失敗）" -ForegroundColor Red
  exit 1
}
$HooksDir = Join-Path $TopLevel 'tools/git-hooks'

# 安裝前驗證：dispatcher hooks 必須存在（post-commit 為 .git/hooks/post-commit 委派器）
foreach ($h in @('pre-commit', 'pre-push', 'post-commit')) {
  $p = Join-Path $HooksDir $h
  if (-not (Test-Path $p)) {
    Write-Host "❌ 缺少 dispatcher hook 檔：$p" -ForegroundColor Red
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
  Write-Host "✅ 已啟用根層 dispatcher hooks：core.hooksPath=$cur" -ForegroundColor Green
  Write-Host "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  Write-Host "   依 commit/push 涉及路徑自動分流），不再互斥。"
  Write-Host "   AISDLC_SDD pre-push 閘門：push 涉及 AISDLC_SDD/ 時自動跑 scripts/ci-gate.sh"
  Write-Host "   Git for Windows 會用內建 bash 執行 hook 本體。"
} else {
  Write-Host "❌ 設定失敗：core.hooksPath='$cur'（目錄或 hook 檔不存在）" -ForegroundColor Red
  exit 1
}
