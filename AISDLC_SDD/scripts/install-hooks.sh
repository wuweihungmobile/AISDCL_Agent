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

# linked worktree 防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree
# 內執行會把 worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
# 偵測法：git-dir 與 git-common-dir 不同即是 linked worktree。
git_dir_abs="$(cd "$(git rev-parse --git-dir)" && pwd)"
common_dir_abs="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
if [ "$git_dir_abs" != "$common_dir_abs" ]; then
  echo "❌ 偵測到 linked worktree（git-dir ≠ git-common-dir）" >&2
  echo "   core.hooksPath 寫入共享 .git/config，在 worktree 內安裝會毒化主 checkout" >&2
  echo "   （worktree 刪除後閘門靜默全滅）。請在主 checkout 執行安裝。" >&2
  exit 1
fi

TOPLEVEL="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$TOPLEVEL/tools/git-hooks"

# 安裝前驗證：dispatcher hooks 必須存在（post-commit 為 .git/hooks/post-commit 委派器）
for h in pre-commit pre-push post-commit; do
  if [ ! -f "$HOOKS_DIR/$h" ]; then
    echo "❌ 缺少 dispatcher hook 檔：$HOOKS_DIR/$h" >&2
    exit 1
  fi
  chmod +x "$HOOKS_DIR/$h" 2>/dev/null || true
done
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

git config core.hooksPath "$HOOKS_DIR"

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含三支 hook 檔（杜絕假 ✅）
cur="$(git config --get core.hooksPath || true)"
if [ "$cur" = "$HOOKS_DIR" ] && [ -d "$cur" ] && [ -f "$cur/pre-commit" ] && [ -f "$cur/pre-push" ] && [ -f "$cur/post-commit" ]; then
  echo "✅ 已啟用根層 dispatcher hooks：core.hooksPath=$cur"
  echo "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  echo "   依 commit/push 涉及路徑自動分流），不再互斥。"
  echo "   AISDLC_SDD pre-push 閘門：push 涉及 AISDLC_SDD/ 時自動跑 scripts/ci-gate.sh"
  echo "   （注意）monorepo 下不支援 pre-commit 框架替代路徑（config 不在 git 根、且框架 shim 會吃掉 pre-push stdin）；一律使用根層 dispatcher 安裝腳本（本腳本或 AutoClaude/tools/install_git_hooks.sh/.ps1 任一支）。"
else
  echo "❌ 設定失敗：core.hooksPath='$cur'（目錄或 hook 檔不存在）" >&2
  exit 1
fi
