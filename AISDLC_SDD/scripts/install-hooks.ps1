# AISDLC-SDD — 安裝 git hooks（Windows PowerShell 版）。
# monorepo 單一 git repo：設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，
# 根層 dispatcher），依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效
# （不再互斥）：AISDLC_SDD/ 變更 → .githooks/pre-push（scripts/ci-gate.sh）；
# AutoClaude/ 變更 → AutoClaude/tools/git-hooks/pre-commit + pre-push。
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$TopLevel = (git rev-parse --show-toplevel)
if ($LASTEXITCODE -ne 0 -or -not $TopLevel) {
  Write-Host "❌ 不在 git repo 內（git rev-parse --show-toplevel 失敗）" -ForegroundColor Red
  exit 1
}
$HooksDir = Join-Path $TopLevel 'tools/git-hooks'

# 安裝前驗證：dispatcher hooks 必須存在
foreach ($h in @('pre-commit', 'pre-push')) {
  $p = Join-Path $HooksDir $h
  if (-not (Test-Path $p)) {
    Write-Host "❌ 缺少 dispatcher hook 檔：$p" -ForegroundColor Red
    exit 1
  }
}

git config core.hooksPath $HooksDir

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含兩支 hook 檔（杜絕假 ✅）
$cur = (git config --get core.hooksPath)
$curOk = ($cur) -and (Test-Path $cur -PathType Container) -and
         (Test-Path (Join-Path $cur 'pre-commit')) -and (Test-Path (Join-Path $cur 'pre-push'))
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
