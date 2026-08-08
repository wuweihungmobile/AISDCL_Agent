# shellcheck shell=bash
# ↑ R80 S8-06：本檔**刻意沒有 shebang**（只被 source，加了會誤示它可直呼），但少了它 shellcheck
#   不知道方言 ⇒ 報 SC2148 並把本檔其餘所有判準一併降級（＝實質落在 lint 盲區）；`shell=bash` 兩者同治。
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
#
# 限制：僅供「子行程/獨立腳本方式」呼叫的上層 .sh source 本檔（如上例）。若在
# 互動式 shell 直接手動 source 本檔逐一測試函式，失敗分支會改用 return（見下方
# dot-source 陷阱防護），不誤殺互動 shell，但呼叫鏈也不會像生產路徑一樣中止——
# 僅供探索/除錯，正式安裝請透過既有呼叫端腳本。

_GIT_HOOKS_INSTALL_COMMON_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_GIT_HOOKS_INSTALL_COMMON_PY="$_GIT_HOOKS_INSTALL_COMMON_SH_DIR/../git_hooks_install_common.py"

# dot-source 陷阱防護（DEF-101-261）：本檔用法示範直接互動式 source，但下列
# 驗證失敗分支歷史上直接 exit——若使用者在互動式 shell 真的照做並命中任一失敗
# 分支，會把整個互動 shell 關掉。用 $0 判斷「這條呼叫鏈的源頭是不是一支真正的
# .sh 腳本檔」：生產呼叫端（install_git_hooks.sh 等）皆以 `bash foo.sh` 執行、
# 內部再 source 本檔，此時 $0 是該腳本的真實路徑，basename 不等於直譯器本身；
# 若使用者在互動提示字元或以 `bash -c "..."` 直接 source 本檔，$0 是直譯器
# 自身（"bash"/"-bash"/"sh"，或以完整路徑呼叫時的 ".../bash.exe"）——不能只用
# `[ -f "$0" ]` 判斷（完整路徑呼叫時 $0 仍指向磁碟上真實存在的 bash.exe 本身，
# 會誤判成腳本；R23 subprocess 呼叫實測重現），須先排除「$0 basename＝直譯器
# 自身名稱」再檢查是否為檔案。命中失敗分支時：前者維持 exit（生產行為零改變）、
# 後者改用 return（不誤殺使用者 shell）。與 tools/dev_start.sh 的 sourced 偵測
# 同一精神，但改用 $0 basename 判斷而非 BASH_SOURCE[0] != $0——因為本檔是函式
# 庫，失敗分支散落在稍後才被呼叫的函式內部（function 內 return 只跳出該函式
# 本身）。
case "$(basename "$0" 2>/dev/null)" in
  bash|-bash|sh|-sh|bash.exe|sh.exe|dash) _GHIC_SCRIPT_DRIVEN=0 ;;
  *) if [ -f "$0" ]; then _GHIC_SCRIPT_DRIVEN=1; else _GHIC_SCRIPT_DRIVEN=0; fi ;;
esac
_ghic_bail() {
  if [ "$_GHIC_SCRIPT_DRIVEN" = "1" ]; then exit 1; else return 1; fi
}

# venv 提示：下列各函式都靠裸 python 呼叫 _GIT_HOOKS_INSTALL_COMMON_PY，未啟用 venv
# 就直接失敗提示（勝過各函式逐一噴原生「python: command not found」）——與
# tools/integration_gate.sh / AutoClaude/tools/local_ci_gate.sh 的前置守門對稱，
# source 本檔時即檢查一次。R43 Scan-B（DEF-101-353）：三處皆改用共用 guard
# is_real_python_candidate 排除 WindowsApps 空殼候選，取代原本裸 `command -v`。
# shellcheck disable=SC1091
. "$_GIT_HOOKS_INSTALL_COMMON_SH_DIR/windowsapps_guard.sh"
is_real_python_candidate python || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; _ghic_bail; }

# 防護：core.hooksPath 寫入的是「共享 .git/config」；在 linked worktree 內執行會把
# worktree 路徑寫進去，worktree 刪除後主 checkout 閘門靜默全滅 → 拒絕執行。
# 判定邏輯見 tools/git_hooks_install_common.py 的 `assert-not-linked-worktree`
# 子指令；失敗時該子指令已把錯誤訊息印到 stderr，本函式只負責 exit 1。
assert_not_linked_worktree() {
  local prefix="${1:-}"
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" assert-not-linked-worktree --prefix "$prefix" || _ghic_bail
}

# 回傳根層 dispatcher hooks 目錄（<repo根>/tools/git-hooks，絕對路徑）。
# 演算法見 tools/git_hooks_install_common.py 的 `get-hooks-dir` 子指令。
get_dispatcher_hooks_dir() {
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" get-hooks-dir || _ghic_bail
}

# 安裝前驗證：dispatcher hooks（pre-commit/pre-push/post-commit）必須存在，
# 缺一即 exit 1（post-commit 為 .git/hooks/post-commit 委派器）。判定邏輯見
# tools/git_hooks_install_common.py 的 `assert-hooks-present` 子指令。
assert_dispatcher_hooks_present() {
  local hooks_dir="$1"
  local prefix="${2:-}"
  python "$_GIT_HOOKS_INSTALL_COMMON_PY" assert-hooks-present "$hooks_dir" --prefix "$prefix" || _ghic_bail
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
