# Install PostCommit advisory hooks (Windows). Per Rule 9.17.1 / OPEN-G.4 / DEF-20-001.
# 串接 drift + closure evidence，皆 advisory 不阻擋 commit。
# DEF-43-008（improving_44）：原寫死 drift→v0.01 / closure→v0.12，致修了 drift 的 repo-root bug
# 也裝不到、且與「指向 LATEST」原則不一致。改為動態解析 LATEST（version 排序取最高），永不再 stale。
# 用 --git-common-dir（非硬編 "$RepoRoot\.git"）：worktree checkout 下 <worktree>\.git
# 是指向主 repo 的純文字檔而非目錄，".git\hooks\..." 會炸「找不到路徑一部分」；
# --git-common-dir 正確解析回主 repo 真正的 .git，且不受 core.hooksPath 影響
# （此設定僅影響 git 自己找 hook，不影響本檔要直寫的真實 .git/hooks/）。
$GitCommonDir = (git rev-parse --path-format=absolute --git-common-dir).Trim()
$HookTarget = Join-Path $GitCommonDir "hooks\post-commit"
# 2026-07-16 四方複審 SD 發現：原本用 `git rev-parse --show-toplevel` 算 $RepoRoot
# 來源解析 LATEST 版本目錄與 $HookSrcDrift/$HookSrcClosure，但 --show-toplevel 在
# linked worktree 內回傳的是「該 worktree 自己的根目錄」，不是主 checkout；worktree
# 一旦被移除，寫入共享 .git/hooks/post-commit 內嵌的路徑就會失效（且被 `|| true` 靜默
# 吞掉，drift/closure 兩個 advisory 閘門會永久靜默失效、零告警）。改用 $GitCommonDir
# 反推主 checkout 根目錄（$GitCommonDir 在任何 linked worktree 下都正確指向主 checkout
# 的 .git，故其父目錄即為主 checkout 根目錄），不受呼叫端是否位於 worktree 影響。
$MainCheckoutRoot = Split-Path -Parent $GitCommonDir
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD\ 子目錄下，故路徑須含 AISDLC_SDD\ 中間層（原缺此層致裝不起來）。
$Latest = (Get-ChildItem -Path (Join-Path $MainCheckoutRoot "AISDLC_SDD") -Directory -Filter "AISDLC_SDD_v*" |
  Sort-Object { [version]($_.Name -replace '^AISDLC_SDD_v','') } | Select-Object -Last 1).Name
if (-not $Latest) {
  Write-Error "找不到任何 AISDLC_SDD_v* 版本目錄於 $MainCheckoutRoot\AISDLC_SDD"
  exit 1
}
$HookSrcDrift = Join-Path $MainCheckoutRoot "AISDLC_SDD\$Latest\.claude\hooks\post_commit_drift.py"
$HookSrcClosure = Join-Path $MainCheckoutRoot "AISDLC_SDD\$Latest\.claude\hooks\closure_evidence_verify.py"

if (-not (Test-Path $HookSrcDrift)) {
  Write-Error "drift hook source not found at $HookSrcDrift"
  exit 1
}
if (-not (Test-Path $HookSrcClosure)) {
  Write-Error "closure hook source not found at $HookSrcClosure"
  exit 1
}

# DEF（Mac/Windows 相容性優化）：原用 `Out-File -Encoding ascii` 寫入，非 ASCII 字元
# （如中文使用者路徑）會被靜默替換為 `?`，導致 hook 內嵌路徑損毀、advisory hook 永久靜默失效
# （|| true 吞錯不會有任何提示）。`-Encoding utf8` 在 PowerShell 5.1 會加 UTF-8 BOM，混進
# `#!/usr/bin/env bash` shebang 前會讓 bash 無法辨識直譯器；改用 .NET UTF8Encoding($false)
# 寫入不帶 BOM 的 UTF-8，且統一正規化為 LF（避免 .ps1 檔案本身 CRLF 混進 bash 腳本內容）。
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
