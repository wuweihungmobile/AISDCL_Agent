#!/usr/bin/env bash
# AISDLC-SDD — 安裝 git hooks（approach 三）。
# monorepo 單一 git repo：設 core.hooksPath=<repo根>/tools/git-hooks（絕對路徑，
# 根層 dispatcher），依 commit/push 涉及路徑自動分流，兩子專案閘門同時生效
# （不再互斥）：AISDLC_SDD/ 變更 → .githooks/pre-push（scripts/ci-gate.sh）；
# AutoClaude/ 變更 → AutoClaude/tools/git-hooks/pre-commit + pre-push。
# 對 Claude Code 的 .claude/hooks/ 無影響（那是 settings.json 驅動，非 git hook）。
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
cd "${REPO_ROOT}"

# linked worktree 防護／HooksDir 取得／安裝前後驗證抽共用（與
# AutoClaude/tools/install_git_hooks.sh 近乎逐字重複的邏輯已抽出單一真相源，對應
# tools/lib/GitHooksInstallCommon.ps1 的 bash 版）：見 tools/lib/git_hooks_install_common.sh。
# shellcheck source=/dev/null
source "$_SCRIPT_DIR/../../tools/lib/git_hooks_install_common.sh"

assert_not_linked_worktree

HOOKS_DIR="$(get_dispatcher_hooks_dir)"
assert_dispatcher_hooks_present "$HOOKS_DIR"
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

git config core.hooksPath "$HOOKS_DIR"

check_git_hooks_path_installed "$HOOKS_DIR"
if [ "$GIT_HOOKS_PATH_OK" = "1" ]; then
  echo "✅ 已啟用根層 dispatcher hooks：core.hooksPath=$CUR_HOOKS_PATH"
  echo "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  echo "   依 commit/push 涉及路徑自動分流），不再互斥。"
  echo "   AISDLC_SDD pre-push 閘門：push 涉及 AISDLC_SDD/ 時自動跑 scripts/ci-gate.sh"
  echo "   （注意）monorepo 下不支援 pre-commit 框架替代路徑（config 不在 git 根、且框架 shim 會吃掉 pre-push stdin）；一律使用根層 dispatcher 安裝腳本（本腳本或 AutoClaude/tools/install_git_hooks.sh/.ps1 任一支）。"
else
  echo "❌ 設定失敗：core.hooksPath='$CUR_HOOKS_PATH'（目錄或 hook 檔不存在）" >&2
  exit 1
fi
