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

# linked worktree 防護／HooksDir 取得／安裝前後驗證抽共用（與
# AISDLC_SDD/scripts/install-hooks.sh 近乎逐字重複的邏輯已抽出單一真相源，對應
# tools/lib/GitHooksInstallCommon.ps1 的 bash 版）：見 tools/lib/git_hooks_install_common.sh。
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$_SCRIPT_DIR/../../tools/lib/git_hooks_install_common.sh"

assert_not_linked_worktree "[install_git_hooks] "

if [ "${1:-}" = "--uninstall" ]; then
  git config --unset core.hooksPath 2>/dev/null || true
  echo "[install_git_hooks] 已移除 core.hooksPath（還原 .git/hooks 預設）"
  exit 0
fi

HOOKS_DIR="$(get_dispatcher_hooks_dir)"
assert_dispatcher_hooks_present "$HOOKS_DIR" "[install_git_hooks] "

git config core.hooksPath "$HOOKS_DIR"

check_git_hooks_path_installed "$HOOKS_DIR"
if [ "$GIT_HOOKS_PATH_OK" = "1" ]; then
  echo "[install_git_hooks] ✅ 已啟用根層 dispatcher hooks：core.hooksPath = $CUR_HOOKS_PATH"
  echo "   兩子專案閘門同時生效（AutoClaude pre-commit/pre-push ＋ AISDLC_SDD pre-push，"
  echo "   依 commit/push 涉及路徑自動分流），不再互斥。"
  echo "   pre-commit  → ruff / LOC / CLAUDE.md / .sh EOL（commit 時）"
  echo "   pre-push    → pytest + import-linter + snapshot / ci-gate.sh（push 時）"
  echo "   post-commit → 委派回 .git/hooks/post-commit（advisory，不影響 commit）"
  echo "   緊急跳過    → AUTOCLAUDE_SKIP_HOOKS=1 或 git commit/push --no-verify"
else
  echo "[install_git_hooks] ❌ 設定失敗：core.hooksPath = '$CUR_HOOKS_PATH'（目錄或 hook 檔不存在）" >&2
  exit 1
fi
