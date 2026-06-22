#!/usr/bin/env bash
# Install PostCommit advisory hooks (opt-in, git native, decoupled from
# .claude/settings.json per OPEN-G.4). 串接兩個 advisory hook（皆 never block commit）：
#   1. Phase G M4 drift（Rule 9.17.1）          — 指 v0.01（穩定凍結基線）
#   2. improving_21 closure evidence（DEF-20-001）— 指 v0.12（首個含此 hook 的版本；
#      未來版本演化時隨 Copy-on-Evolve 更新此路徑，同 drift 指 v0.01 慣例）
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_TARGET="$REPO_ROOT/.git/hooks/post-commit"
# DEF-43-002：monorepo 收斂後 git rev-parse --show-toplevel = monorepo 根，
# 各版位於 AISDLC_SDD/ 子目錄下，故路徑須含 AISDLC_SDD/ 中間層（原缺此層致裝不起來）。
HOOK_SRC_DRIFT="$REPO_ROOT/AISDLC_SDD/AISDLC_SDD_v0.01/.claude/hooks/post_commit_drift.py"
HOOK_SRC_CLOSURE="$REPO_ROOT/AISDLC_SDD/AISDLC_SDD_v0.12/.claude/hooks/closure_evidence_verify.py"

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
