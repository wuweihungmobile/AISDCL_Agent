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
# R11（DEF-101-133）：LATEST 解析委派 scripts/sdd_version.py SSOT——原
# Get-ChildItem + [version] 排序尾端未錨定（.bak／檔總管複製品會汙染選版）且掃磁碟
# 非 git tracked。Windows 環境有 python 才會裝 hook（本腳本本就依賴 python），
# 解析失敗即 fail-loud。
$SddRoot = Join-Path $MainCheckoutRoot "AISDLC_SDD"
# R11 P4：python 缺席前置檢查（與 .sh 的 command -v 守門對稱）——否則 `& python`
# 直接丟 CommandNotFoundException，訊息不指路。
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "找不到 python — 請啟用 venv 或安裝 Python 後重試"
  exit 1
}
$Latest = (& python (Join-Path $SddRoot "scripts\sdd_version.py") --sdd-root $SddRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $Latest) {
  Write-Error "LATEST 解析失敗（sdd_version.py SSOT）：找不到任何 AISDLC_SDD_v* 版本目錄於 $SddRoot"
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
# R11（DEF-101 家族）：hook 內容補 python fallback——現代 macOS 乾淨 PATH 只有
# python3 沒有 python，且 git hook 執行環境不繼承 venv，缺 fallback 時兩個 advisory
# hook 會被 `|| true` 吞掉、永久靜默失效零告警（與 .sh 產生器寫出同款 hook 內容）。
$HookContent = @"
#!/usr/bin/env bash
# PostCommit advisory hooks - never block commit
PY="`$(command -v python || command -v python3 || true)"
if [ -z "`$PY" ]; then
  echo "[post-commit advisory] 找不到 python/python3 — drift/closure advisory 本次跳過（不阻擋 commit）" >&2
  exit 0
fi
"`$PY" "$HookSrcDrift" "`$@" || true
"`$PY" "$HookSrcClosure" "`$@" || true
"@
$HookContent = $HookContent -replace "`r`n", "`n"
# R11 四方複審（SD-1/QA-7/SA-1）：here-string 產物天生無檔尾換行，而 .sh 的 heredoc
# 有——差這 1 byte 使「兩產生器輸出逐位元一致」宣稱為假。補單一 \n（EndsWith 守門，
# 絕不會補成兩個），使 pwsh/bash 雙產生器 cmp BYTE_IDENTICAL 為真。
if (-not $HookContent.EndsWith("`n")) { $HookContent += "`n" }
[System.IO.File]::WriteAllText($HookTarget, $HookContent, (New-Object System.Text.UTF8Encoding($false)))

# 非 Windows 載體（pwsh on macOS/Linux——R11 取證即實際走過此載體）下 git 要求 hook
# 有 exec bit：WriteAllText 不設 file mode，缺位時 git 直呼僅印 hint 後忽略、根層
# dispatcher 的 [ -x ] 判 false 後零告警跳過（advisory 恆 exit 0）＝靜默失效
#（R14 SCAN-SH-2）。PS 5.1 無 $IsWindows 自動變數，改以 OSVersion.Platform 判 Unix。
if ([System.Environment]::OSVersion.Platform -eq 'Unix') {
    & chmod +x $HookTarget
    # chmod 失敗 fail-loud（R14 一審 SD-R14-REV-2：.sh 版在 set -e 下 chmod 失敗即中止，
    # .ps1 無 Stop preference 時 native 失敗屬 non-terminating——不攔即靜默裝出壞 hook）。
    if ($LASTEXITCODE -ne 0) {
        Write-Error "chmod +x failed for ${HookTarget} (exit ${LASTEXITCODE}) - git would silently ignore a non-executable hook"
        exit 1
    }
}

Write-Output "Installed PostCommit advisory hooks at: $HookTarget"
Write-Output "  - drift   -> .git/COMMIT_DRIFT_WARNING"
Write-Output "  - closure -> .git/CLOSURE_EVIDENCE_VERDICT (DEF-20-001)"
