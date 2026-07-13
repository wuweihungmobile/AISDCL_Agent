#!/usr/bin/env bash
# Install PostCommit advisory hooks (opt-in, git native, decoupled from
# .claude/settings.json per OPEN-G.4). 串接兩個 advisory hook（皆 never block commit）：
#   1. Phase G M4 drift（Rule 9.17.1）
#   2. improving_21 closure evidence（DEF-20-001）
# DEF-43-008（improving_44）：原寫死 drift→v0.01 / closure→v0.12，致 (a) 修了 drift 的
# repo-root bug 也裝不到（仍裝舊 v0.01 buggy 版）、(b) 與 skills SSOT「指向 LATEST」原則不一致。
# 改為動態解析 LATEST（對齊 ci-gate.sh 的 sort -V | tail -1），永不再 stale、修復立即生效。
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
# 用 --git-common-dir（非硬編 "$REPO_ROOT/.git"）：worktree checkout 下 <worktree>/.git
# 是指向主 repo 的純文字檔而非目錄，".git/hooks/..." 會找不到路徑；--git-common-dir
# 正確解析回主 repo 真正的 .git，且不受 core.hooksPath 影響（該設定只影響 git 自己
# 找 hook，不影響本檔要直寫的真實 .git/hooks/）。
GIT_COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir)"
HOOK_TARGET="$GIT_COMMON_DIR/hooks/post-commit"
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD/ 子目錄下，故路徑須含 AISDLC_SDD/ 中間層（原缺此層致裝不起來）。
# 三 glob 同 ci-gate.sh：v0.0*（~v0.09）+ v0.[1-9]*（v0.10+）+ v[1-9]*（v1.x+，`|| true` 吞無匹配）。
LATEST="$(cd "$REPO_ROOT/AISDLC_SDD" && { ls -d AISDLC_SDD_v0.0* AISDLC_SDD_v0.[1-9]* AISDLC_SDD_v[1-9]* 2>/dev/null || true; } | sort -V | tail -1)"
if [ -z "$LATEST" ]; then
  echo "ERROR: 找不到任何 AISDLC_SDD_v* 版本目錄於 $REPO_ROOT/AISDLC_SDD" >&2
  exit 1
fi
HOOK_SRC_DRIFT="$REPO_ROOT/AISDLC_SDD/$LATEST/.claude/hooks/post_commit_drift.py"
HOOK_SRC_CLOSURE="$REPO_ROOT/AISDLC_SDD/$LATEST/.claude/hooks/closure_evidence_verify.py"

if [ ! -f "$HOOK_SRC_DRIFT" ]; then
  echo "ERROR: drift hook source not found at $HOOK_SRC_DRIFT" >&2
  exit 1
fi
if [ ! -f "$HOOK_SRC_CLOSURE" ]; then
  echo "ERROR: closure hook source not found at $HOOK_SRC_CLOSURE" >&2
  exit 1
fi

cat > "$HOOK_TARGET" <<HOOK
#!/usr/bin/env bash
# PostCommit advisory hooks — never block commit
python "$HOOK_SRC_DRIFT" "\$@" || true
python "$HOOK_SRC_CLOSURE" "\$@" || true
HOOK
chmod +x "$HOOK_TARGET"
echo "Installed PostCommit advisory hooks at: $HOOK_TARGET"
echo "  - drift   → .git/COMMIT_DRIFT_WARNING"
echo "  - closure → .git/CLOSURE_EVIDENCE_VERDICT (DEF-20-001 結案證據重推導)"
