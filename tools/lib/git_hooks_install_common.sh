# git_hooks_install_common.sh — 共用 git hooks 安裝流程（bash 版薄殼層，對應
# tools/lib/GitHooksInstallCommon.ps1 的 bash 版；獨立複審 finding 後改為薄殼層）。
#
# 判定邏輯的單一真相源是 tools/git_hooks_install_common.py（供本檔與
# tools/lib/GitHooksInstallCommon.ps1 兩份 thin wrapper 呼叫，兩者只保留該平台
# 原生的呈現層 —— bash 的全域變數回傳慣例 —— 不再各自重寫判定邏輯本身）：任一處
# 修 bug（如 linked worktree 偵測、HooksDir 正規化演算法）只需改
# tools/git_hooks_install_common.py 一處，不必人工同步兩份呼叫端。
#
# 呼叫端各自保留的部分（不在本檔內，維持產品特有文案）：
#   - 是否支援 --uninstall（僅 AutoClaude 版有）
#   - 安裝成功後的閘門說明文字（兩專案 pre-commit/pre-push 內容不同）
#
# 用法：
#   _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "$_SCRIPT_DIR/../../tools/lib/git_hooks_install_common.sh"
#   assert_not_linked_worktree "[prefix] "
#   HOOKS_DIR="$(get_dispatcher_hooks_dir)"
#   assert_dispatcher_hooks_present "$HOOKS_DIR" "[prefix] "
#   git config core.hooksPath "$HOOKS_DIR"
#   check_git_hooks_path_installed "$HOOKS_DIR"
#   if [ "$GIT_HOOKS_PATH_OK" = "1" ]; then ... else ... fi

_GIT_HOOKS_INSTALL_COMMON_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_GIT_HOOKS_INSTALL_COMMON_PY="$_GIT_HOOKS_INSTALL_COMMON_SH_DIR/../git_hooks_install_common.py"

# venv 提示：下列各函式都靠裸 python 呼叫 _GIT_HOOKS_INSTALL_COMMON_PY，未啟用 venv
# 就直接失敗提示（勝過各函式逐一噴原生「python: command not found」）——與
# tools/integration_gate.sh / AutoClaude/tools/local_ci_gate.sh 的
# `command -v python` 前置守門對稱，source 本檔時即檢查一次。
command -v python >/dev/null || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

# 防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree 內執行會把
# worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
# 判定邏輯見 tools/git_hooks_install_common.py 的 `assert-not-linked-worktree`
# 子指令；失敗時該子指令已把錯誤訊息印到 stderr，本函式只負責 exit 1。
assert_not_linked_worktree() {
  local prefix="${1:-}"
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" assert-not-linked-worktree --prefix "$prefix" || exit 1
}

# 回傳根層 dispatcher hooks 目錄（<repo根>/tools/git-hooks，絕對路徑）。
# 演算法見 tools/git_hooks_install_common.py 的 `get-hooks-dir` 子指令。
get_dispatcher_hooks_dir() {
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" get-hooks-dir || exit 1
}

# 安裝前驗證：dispatcher hooks（pre-commit/pre-push/post-commit）必須存在，
# 缺一即 exit 1（post-commit 為 .git/hooks/post-commit 委派器）。判定邏輯見
# tools/git_hooks_install_common.py 的 `assert-hooks-present` 子指令。
assert_dispatcher_hooks_present() {
  local hooks_dir="$1"
  local prefix="${2:-}"
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" assert-hooks-present "$hooks_dir" --prefix "$prefix" || exit 1
}

# 安裝後驗證：core.hooksPath 解析出的目錄實際存在且含三支 hook 檔（杜絕假 ✅）。
# 不 exit，設全域變數 CUR_HOOKS_PATH / GIT_HOOKS_PATH_OK（bash function 無法回傳
# 複合值），由呼叫端決定成功/失敗訊息。判定邏輯見 tools/git_hooks_install_common.py
# 的 `check-installed` 子指令。
check_git_hooks_path_installed() {
  local hooks_dir="$1"
  local out
  out="$(python "$_GIT_HOOKS_INSTALL_COMMON_PY" check-installed "$hooks_dir")"
  CUR_HOOKS_PATH="$(echo "$out" | sed -n 's/^CUR=//p')"
  GIT_HOOKS_PATH_OK="$(echo "$out" | sed -n 's/^OK=//p')"
}
