#!/usr/bin/env bash
# dev_start.sh — 每日開工自動啟動 wrapper（macOS/Linux）。Windows 對等：tools/dev_start.ps1
#
# 用法：
#   source tools/dev_start.sh     # 推薦：核心完成後自動於當前 shell 啟用 .venv
#   bash tools/dev_start.sh       # 僅執行整備；結尾請自行 source .venv/bin/activate
#
# 邏輯全部集中在 tools/dev_start.py（跨平台單一事實源；本對 .sh/.ps1 為薄殼，
# 業務邏輯零漂移面；薄殼樣板本身無機械比對，改動須人工同步 .ps1）。本檔只做三件事：
#   選直譯器（.venv 形狀正確優先，否則 SSOT 候選鏈挑 >= 3.11）→ 轉呼叫核心 → 視需要啟用 venv。
# 刻意不用 set -e / 頂層 exit：被 source 時會殺掉使用者 shell，一律以 return code 傳遞。
#
# 限制（bash/zsh 專用）：
#   - POSIX sh（dash）不支援本檔語法（Bad substitution）——請勿以 dash source/執行。
#   - source 不帶參數時繼承呼叫端 shell 的位置參數（bash/zsh 語言限制）——
#     請勿在自帶位置參數的 script/function 內無參數 source 本檔（互動 prompt 不受影響）。

_ds_sourced=0
if [ -n "${ZSH_EVAL_CONTEXT:-}" ]; then
  case "$ZSH_EVAL_CONTEXT" in *:file*) _ds_sourced=1 ;; esac
elif [ -n "${BASH_SOURCE:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
  _ds_sourced=1
fi

_ds_main() {
  local script_path script_dir root py
  if [ -n "${ZSH_EVAL_CONTEXT:-}" ]; then
    # zsh：%x＝當前被 source 的檔案路徑（zsh -c 下 $0 是 "zsh"，不可靠）；
    # 本行僅在 zsh 分支執行，bash 不會展開到這個 zsh 專屬語法
    # shellcheck disable=SC2296  # zsh 專屬展開，shellcheck 誤報
    script_path="${(%):-%x}"
  else
    script_path="${BASH_SOURCE[0]:-$0}"
  fi
  script_dir="$(cd "$(dirname "$script_path")" && pwd)" || return 1
  root="$(cd "$script_dir/.." && pwd)" || return 1

  # R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
  # shellcheck disable=SC1091
  . "$root/tools/lib/windowsapps_guard.sh"

  # R69 P2：候選鏈由 SSOT `pick_python_ge_min` 提供（>= 3.11 才算數）。原本只試
  # `python3`/`python`，在 macOS 上恆撿到系統 3.9 → 核心版本閘 rc=2（見該 SSOT
  # 函式上方的 WHY 區塊）。`.venv` 仍最優先：換平台/重建由核心自己處理。
  if [ -x "$root/.venv/bin/python" ]; then
    py="$root/.venv/bin/python"
  else
    py="$(pick_python_ge_min)"
  fi

  if [ -z "$py" ]; then
    python_ge_min_remediation
    return 1
  fi

  "$py" "$root/tools/dev_start.py" "$@" || return $?

  if [ "$_ds_sourced" -eq 1 ]; then
    if [ -f "$root/.venv/bin/activate" ]; then
      # shellcheck disable=SC1091
      . "$root/.venv/bin/activate"
      echo "✅ 已自動啟用 .venv（python → $(command -v python)）"
    else
      echo "⚠️  .venv/bin/activate 不存在，未啟用 venv" >&2
    fi
  else
    echo "ℹ️  以 bash 執行不會影響當前 shell — 請自行：source .venv/bin/activate"
  fi
  return 0
}

_ds_main "$@"
_ds_rc=$?
unset -f _ds_main
if [ "$_ds_sourced" -eq 1 ]; then
  unset _ds_sourced
  # eval 先把 $_ds_rc 展開成字面值再執行 → unset 之後仍 return 正確 rc，
  # 使用者 shell 零 _ds_* 殘留（rc 來自 $?，恆為數字，無注入面）。
  # 不可用「函式內 unset -f 自身」：bash/zsh 會中止剩餘函式體，rc 變 0。
  eval "unset _ds_rc; return $_ds_rc"
fi
unset _ds_sourced
exit "$_ds_rc"
