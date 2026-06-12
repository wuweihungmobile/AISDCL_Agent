#!/usr/bin/env bash
# Install Phase G M4 PostCommit drift hook (Rule 9.17.1, opt-in).
# Per OPEN-G.4: git native, decoupled from .claude/settings.json.
set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_TARGET="$REPO_ROOT/.git/hooks/post-commit"
HOOK_SRC="$REPO_ROOT/AISDLC_SDD_v0.01/.claude/hooks/post_commit_drift.py"

if [ ! -f "$HOOK_SRC" ]; then
  echo "ERROR: hook source not found at $HOOK_SRC" >&2
  exit 1
fi

cat > "$HOOK_TARGET" <<HOOK
#!/usr/bin/env bash
# Phase G M4 drift advisory (Rule 9.17.1) — never blocks commit
exec python "$HOOK_SRC" "\$@" || true
HOOK
chmod +x "$HOOK_TARGET"
echo "Installed PostCommit drift hook at: $HOOK_TARGET"
echo "Run any commit to verify; warnings (if any) appear in .git/COMMIT_DRIFT_WARNING"
