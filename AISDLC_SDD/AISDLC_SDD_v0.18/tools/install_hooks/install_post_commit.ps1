# Install PostCommit advisory hooks (Windows). Per Rule 9.17.1 / OPEN-G.4 / DEF-20-001.
# 串接 drift（v0.01 穩定基線）+ closure evidence（v0.12，首個含此 hook 的版本），皆 advisory 不阻擋 commit。
$RepoRoot = (git rev-parse --show-toplevel).Trim()
$HookTarget = Join-Path $RepoRoot ".git\hooks\post-commit"
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD\ 子目錄下，故路徑須含 AISDLC_SDD\ 中間層（原缺此層致裝不起來）。
$HookSrcDrift = Join-Path $RepoRoot "AISDLC_SDD\AISDLC_SDD_v0.01\.claude\hooks\post_commit_drift.py"
$HookSrcClosure = Join-Path $RepoRoot "AISDLC_SDD\AISDLC_SDD_v0.12\.claude\hooks\closure_evidence_verify.py"

if (-not (Test-Path $HookSrcDrift)) {
  Write-Error "drift hook source not found at $HookSrcDrift"
  exit 1
}
if (-not (Test-Path $HookSrcClosure)) {
  Write-Error "closure hook source not found at $HookSrcClosure"
  exit 1
}

$HookContent = @"
#!/usr/bin/env bash
# PostCommit advisory hooks - never block commit
python "$HookSrcDrift" "`$@" || true
python "$HookSrcClosure" "`$@" || true
"@
$HookContent = $HookContent -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($HookTarget, $HookContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "Installed PostCommit advisory hooks at: $HookTarget"
Write-Output "  - drift   -> .git/COMMIT_DRIFT_WARNING"
Write-Output "  - closure -> .git/CLOSURE_EVIDENCE_VERDICT (DEF-20-001)"
