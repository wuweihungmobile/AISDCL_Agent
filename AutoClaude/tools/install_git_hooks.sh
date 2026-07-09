#!/usr/bin/env bash
# install_git_hooks.sh — 安裝 monorepo 根層 dispatcher git hooks（macOS/Linux）。
# Windows 對等：tools/install_git_hooks.ps1（本檔為其忠實對照，行為一致以求雙平台平價）。
#
# 設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，根層 dispatcher）：
#   dispatcher 依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效（不再互斥）：
#     AutoClaude/ 變更  → AutoClaude/tools/git-hooks/pre-commit + pre-push
#     AISDLC_SDD/ 變更 → AISDLC_SDD/.githooks/pre-push
#   pre-commit：ruff / LOC 預算 / CLAUDE.md<=400 / .sh LF（快，< 15s）
#   pre-push  ：pytest + import-linter + snapshot（完整本機 CI 閘門）
# hook 本體皆為 bash（#!/usr/bin/env bash），跨平台無礙。
#
# 用法：
#   bash tools/install_git_hooks.sh              # 安裝
#   bash tools/install_git_hooks.sh --uninstall  # 還原 .git/hooks 預設
set -euo pipefail

if [ "${1:-}" = "--uninstall" ]; then
  git config --unset core.hooksPath 2>/dev/null || true
  echo "[install_git_hooks] 已移除 core.hooksPath（還原 .git/hooks 預設）"
  exit 0
fi

TOPLEVEL="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$TOPLEVEL/tools/git-hooks"

# 安裝前驗證：dispatcher hooks 必須存在
for h in pre-commit pre-push; do
  if [ ! -f "$HOOKS_DIR/$h" ]; then
    echo "[install_git_hooks] 缺少 dispatcher hook 檔：$HOOKS_DIR/$h" >&2
    exit 1
  fi
  chmod +x "$HOOKS_DIR/$h" 2>/dev/null || true
done

git config core.hooksPath "$HOOKS_DIR"

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含兩支 hook 檔（杜絕假 ✅）
cur="$(git config --get core.hooksPath || true)"
if [ "$cur" = "$HOOKS_DIR" ] && [ -d "$cur" ] && [ -f "$cur/pre-commit" ] && [ -f "$cur/pre-push" ]; then
  echo "[install_git_hooks] ✅ 已啟用根層 dispatcher hooks：core.hooksPath = $cur"
  echo "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  echo "   依 commit/push 涉及路徑自動分流），不再互斥。"
  echo "   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）"
  echo "   pre-push    → pytest + import-linter + snapshot / ci-gate.sh（push 時）"
  echo "   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify"
else
  echo "[install_git_hooks] ❌ 設定失敗：core.hooksPath = '$cur'（目錄或 hook 檔不存在）" >&2
  exit 1
fi
