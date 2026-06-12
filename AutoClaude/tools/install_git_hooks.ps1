<#
.SYNOPSIS
安裝 AutoClaude 原生 git hooks（設 core.hooksPath=tools/git-hooks）。

.DESCRIPTION
零依賴方式啟用 pre-commit / pre-push 攔截點，讓系統強制把關（取代人工記憶跑測試）。
hooks 內容鏡像 CI gating jobs，push 前在本機攔下 CI 紅燈。

  pre-commit：ruff / LOC 預算 / CLAUDE.md<=400 / .sh LF（快，< 15s）
  pre-push  ：pytest + import-linter + snapshot（完整本機 CI 閘門）

.PARAMETER Uninstall
還原 core.hooksPath（改回 .git/hooks 預設）。
#>
[CmdletBinding()]
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if ($Uninstall) {
  git config --unset core.hooksPath 2>$null
  Write-Host '[install_git_hooks] 已移除 core.hooksPath（還原 .git/hooks 預設）' -ForegroundColor Yellow
  exit 0
}

# 確認 hook 檔存在
$hooksDir = 'tools/git-hooks'
foreach ($h in @('pre-commit', 'pre-push')) {
  $p = Join-Path $RepoRoot (Join-Path $hooksDir $h)
  if (-not (Test-Path $p)) {
    Write-Host "[install_git_hooks] 缺少 hook 檔：$p" -ForegroundColor Red
    exit 1
  }
}

git config core.hooksPath $hooksDir
$cur = (git config --get core.hooksPath)
if ($cur -eq $hooksDir) {
  Write-Host "[install_git_hooks] ✅ 已啟用 git hooks：core.hooksPath = $cur" -ForegroundColor Green
  Write-Host '   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）'
  Write-Host '   pre-push    → pytest + import-linter + snapshot（push 時）'
  Write-Host '   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify'
} else {
  Write-Host "[install_git_hooks] ❌ 設定失敗：core.hooksPath = '$cur'" -ForegroundColor Red
  exit 1
}
