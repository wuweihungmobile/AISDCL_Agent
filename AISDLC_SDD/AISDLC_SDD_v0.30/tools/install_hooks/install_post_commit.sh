#!/usr/bin/env bash
# Install PostCommit advisory hooks (opt-in, git native, decoupled from
# .claude/settings.json per OPEN-G.4). 串接兩個 advisory hook（皆 never block commit）：
#   1. Phase G M4 drift（Rule 9.17.1）
#   2. improving_21 closure evidence（DEF-20-001）
# DEF-43-008（improving_44）：原寫死 drift→v0.01 / closure→v0.12，致 (a) 修了 drift 的
# repo-root bug 也裝不到（仍裝舊 v0.01 buggy 版）、(b) 與 skills SSOT「指向 LATEST」原則不一致。
# 改為動態解析 LATEST，永不再 stale、修復立即生效；R11 起 LATEST 解析委派
# scripts/sdd_version.py 單一真相源（git tracked + 錨定 fullmatch + 數值排序，
# DEF-101-133——早期 `sort -V | tail -1` 版有未錨定 glob 與掃磁碟兩病）。
set -e
# 用 --git-common-dir（非硬編 "$REPO_ROOT/.git"）：worktree checkout 下 <worktree>/.git
# 是指向主 repo 的純文字檔而非目錄，".git/hooks/..." 會找不到路徑；--git-common-dir
# 正確解析回主 repo 真正的 .git，且不受 core.hooksPath 影響（該設定只影響 git 自己
# 找 hook，不影響本檔要直寫的真實 .git/hooks/）。
GIT_COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir)"
HOOK_TARGET="$GIT_COMMON_DIR/hooks/post-commit"
# 2026-07-16 四方複審 SD 發現：原本用 `git rev-parse --show-toplevel` 算 REPO_ROOT
# 來源解析 LATEST 版本目錄與 HOOK_SRC_DRIFT/HOOK_SRC_CLOSURE，但 --show-toplevel 在
# linked worktree 內回傳的是「該 worktree 自己的根目錄」，不是主 checkout；worktree
# 一旦被移除，寫入共享 .git/hooks/post-commit 內嵌的路徑就會失效（且被 `|| true` 靜默
# 吞掉，drift/closure 兩個 advisory 閘門會永久靜默失效、零告警）。改用 GIT_COMMON_DIR
# 反推主 checkout 根目錄（GIT_COMMON_DIR 在任何 linked worktree 下都正確指向主 checkout
# 的 .git，故其父目錄即為主 checkout 根目錄），不受呼叫端是否位於 worktree 影響。
MAIN_CHECKOUT_ROOT="$(dirname "$GIT_COMMON_DIR")"
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD/ 子目錄下，故路徑須含 AISDLC_SDD/ 中間層（原缺此層致裝不起來）。
# R11（DEF-101-133）：LATEST 解析委派 scripts/sdd_version.py SSOT——原
# `ls -d ... | sort -V | tail -1` 尾端未錨定（.bak／檔總管複製品會汙染選版）
# 且掃磁碟非 git tracked，而 ci-gate/smoke/CI 全在乾淨 clone 跑、永遠測不到（假綠）。
# 現代 macOS 乾淨 PATH 只有 python3 沒有 python，故先解析直譯器、缺席 fail-loud。
PY="$(command -v python || command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "ERROR: 找不到 python/python3 — 請啟用 venv 或安裝 python3 後重試" >&2
  exit 1
fi
LATEST="$("$PY" "$MAIN_CHECKOUT_ROOT/AISDLC_SDD/scripts/sdd_version.py" --sdd-root "$MAIN_CHECKOUT_ROOT/AISDLC_SDD")" || LATEST=""
if [ -z "$LATEST" ]; then
  echo "ERROR: LATEST 解析失敗——找不到任何 AISDLC_SDD_v* 版本目錄於 $MAIN_CHECKOUT_ROOT/AISDLC_SDD，或 sdd_version.py 執行失敗（詳見上方 stderr）" >&2
  exit 1
fi
HOOK_SRC_DRIFT="$MAIN_CHECKOUT_ROOT/AISDLC_SDD/$LATEST/.claude/hooks/post_commit_drift.py"
HOOK_SRC_CLOSURE="$MAIN_CHECKOUT_ROOT/AISDLC_SDD/$LATEST/.claude/hooks/closure_evidence_verify.py"

if [ ! -f "$HOOK_SRC_DRIFT" ]; then
  echo "ERROR: drift hook source not found at $HOOK_SRC_DRIFT" >&2
  exit 1
fi
if [ ! -f "$HOOK_SRC_CLOSURE" ]; then
  echo "ERROR: closure hook source not found at $HOOK_SRC_CLOSURE" >&2
  exit 1
fi

# R11（DEF-101 家族）：hook 內容補 python fallback——現代 macOS 乾淨 PATH 只有
# python3 沒有 python，且 git hook 執行環境不繼承 venv，缺 fallback 時兩個 advisory
# hook 會被 `|| true` 吞掉、永久靜默失效零告警。
cat > "$HOOK_TARGET" <<HOOK
#!/usr/bin/env bash
# PostCommit advisory hooks - never block commit
PY="\$(command -v python || command -v python3 || true)"
if [ -z "\$PY" ]; then
  echo "[post-commit advisory] 找不到 python/python3 — drift/closure advisory 本次跳過（不阻擋 commit）" >&2
  exit 0
fi
"\$PY" "$HOOK_SRC_DRIFT" "\$@" || true
"\$PY" "$HOOK_SRC_CLOSURE" "\$@" || true
HOOK
chmod +x "$HOOK_TARGET"
echo "Installed PostCommit advisory hooks at: $HOOK_TARGET"
echo "  - drift   → .git/COMMIT_DRIFT_WARNING"
echo "  - closure → .git/CLOSURE_EVIDENCE_VERDICT (DEF-20-001 結案證據重推導)"
