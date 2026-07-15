# Install Phase G M4 PostCommit drift hook (Windows). Per Rule 9.17.1 / OPEN-G.4.
$RepoRoot = (git rev-parse --show-toplevel).Trim()
$HookTarget = Join-Path $RepoRoot ".git\hooks\post-commit"
$HookSrc = Join-Path $RepoRoot "AISDLC_SDD_v0.01\.claude\hooks\post_commit_drift.py"

if (-not (Test-Path $HookSrc)) {
  Write-Error "hook source not found at $HookSrc"
  exit 1
}

$HookContent = @"
#!/usr/bin/env bash
# Phase G M4 drift advisory (Rule 9.17.1) - never blocks commit
exec python "$HookSrc" "`$@" || true
"@
$HookContent = $HookContent -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($HookTarget, $HookContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "Installed PostCommit drift hook at: $HookTarget"
