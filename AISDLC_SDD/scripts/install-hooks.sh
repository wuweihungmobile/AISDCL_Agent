#!/usr/bin/env bash
# AISDLC-SDD — 安裝 git hooks（approach 三）。
# monorepo 單一 git repo：設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，
# 根層 dispatcher），依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效
# （不再互斥）：AISDLC_SDD/ 變更 → .githooks/pre-push（scripts/ci-gate.sh）；
# AutoClaude/ 變更 → AutoClaude/tools/git-hooks/pre-commit + pre-push。
# 對 Claude Code 的 .claude/hooks/ 無影響（那是 settings.json 驅動，非 git hook）。
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

TOPLEVEL="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$TOPLEVEL/tools/git-hooks"

# 安裝前驗證：dispatcher hooks 必須存在
for h in pre-commit pre-push; do
  if [ ! -f "$HOOKS_DIR/$h" ]; then
    echo "❌ 缺少 dispatcher hook 檔：$HOOKS_DIR/$h" >&2
    exit 1
  fi
  chmod +x "$HOOKS_DIR/$h" 2>/dev/null || true
done
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

git config core.hooksPath "$HOOKS_DIR"

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含兩支 hook 檔（杜絕假 ✅）
cur="$(git config --get core.hooksPath || true)"
if [ "$cur" = "$HOOKS_DIR" ] && [ -d "$cur" ] && [ -f "$cur/pre-commit" ] && [ -f "$cur/pre-push" ]; then
  echo "✅ 已啟用根層 dispatcher hooks：core.hooksPath=$cur"
  echo "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  echo "   依 commit/push 涉及路徑自動分流），不再互斥。"
  echo "   AISDLC_SDD pre-push 閘門：push 涉及 AISDLC_SDD/ 時自動跑 scripts/ci-gate.sh"
  echo "   （選用）若改用 pre-commit 框架：pip install pre-commit && pre-commit install --hook-type pre-push"
else
  echo "❌ 設定失敗：core.hooksPath='$cur'（目錄或 hook 檔不存在）" >&2
  exit 1
fi
