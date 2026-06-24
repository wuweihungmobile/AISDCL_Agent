# Install PostCommit advisory hooks (Windows). Per Rule 9.17.1 / OPEN-G.4 / DEF-20-001.
# 串接 drift + closure evidence，皆 advisory 不阻擋 commit。
# DEF-43-008（improving_44）：原寫死 drift→v0.01 / closure→v0.12，致修了 drift 的 repo-root bug
# 也裝不到、且與「指向 LATEST」原則不一致。改為動態解析 LATEST（version 排序取最高），永不再 stale。
$RepoRoot = (git rev-parse --show-toplevel).Trim()
$HookTarget = Join-Path $RepoRoot ".git\hooks\post-commit"
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD\ 子目錄下，故路徑須含 AISDLC_SDD\ 中間層（原缺此層致裝不起來）。
$Latest = (Get-ChildItem -Path (Join-Path $RepoRoot "AISDLC_SDD") -Directory -Filter "AISDLC_SDD_v*" |
  Sort-Object { [version]($_.Name -replace '^AISDLC_SDD_v','') } | Select-Object -Last 1).Name
if (-not $Latest) {
  Write-Error "找不到任何 AISDLC_SDD_v* 版本目錄於 $RepoRoot\AISDLC_SDD"
  exit 1
}
$HookSrcDrift = Join-Path $RepoRoot "AISDLC_SDD\$Latest\.claude\hooks\post_commit_drift.py"
$HookSrcClosure = Join-Path $RepoRoot "AISDLC_SDD\$Latest\.claude\hooks\closure_evidence_verify.py"

if (-not (Test-Path $HookSrcDrift)) {
  Write-Error "drift hook source not found at $HookSrcDrift"
  exit 1
}
if (-not (Test-Path $HookSrcClosure)) {
  Write-Error "closure hook source not found at $HookSrcClosure"
  exit 1
}

@"
#!/usr/bin/env bash
# PostCommit advisory hooks - never block commit
python "$HookSrcDrift" "`$@" || true
python "$HookSrcClosure" "`$@" || true
"@ | Out-File -FilePath $HookTarget -Encoding ascii

Write-Output "Installed PostCommit advisory hooks at: $HookTarget"
Write-Output "  - drift   -> .git/COMMIT_DRIFT_WARNING"
Write-Output "  - closure -> .git/CLOSURE_EVIDENCE_VERDICT (DEF-20-001)"
