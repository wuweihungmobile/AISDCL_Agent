# AISDLC-SDD — 安裝 git hooks（Windows PowerShell 版）。
# 設 core.hooksPath=.githooks，啟用 pre-push 本機 CI 閘門。
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
git config core.hooksPath .githooks
Write-Host "✅ 已設定 core.hooksPath=.githooks"
Write-Host "   pre-push 閘門已啟用：每次 push 前自動跑 scripts/ci-gate.sh"
Write-Host "   Git for Windows 會用內建 bash 執行 .githooks/pre-push。"
