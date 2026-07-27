#!/usr/bin/env bash
# 共用 WindowsApps 空殼 python/python3 候選排除 guard（bash 側）— R43 Scan-B
# 系統性缺口收斂（DEF-101-353）。
#
# 背景：R37/R40 已把 PowerShell 側（tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython）
# 與 Python 側（bootstrap_core.py::_is_windows_apps_stub）各自收斂為單一真相源，但兩者
# 皆只掃描 .ps1/.py，repo 內另有多支 tracked bash 腳本（含 tools/git-hooks/pre-push
# 這個每次 push 都會實際執行的 dispatcher）各自用裸 `command -v python`/`command -v
# python3` 判斷可用性，從未排除 Windows Store App Execution Alias 空殼——全新未裝真
# Python 的 Windows 11 機器上，Git Bash 繼承 Windows PATH 同樣會命中
# %LOCALAPPDATA%\Microsoft\WindowsApps 下的空殼 python.exe/python3.exe（`command -v`
# 判定為「存在」，實際執行只會跳出 Microsoft Store 安裝提示，對 pre-push 這類阻斷式
# hook 而言即為掛起）。本檔為該語言邊界補上對稱實作。
#
# R56 修正：本段原寫死「另有 12 支」（R43 寫 9、R55 訂為 12、實測皆錯）。呼叫端
# 實數不再寫在敘述裡——唯一真相源＝tools/tests/test_windowsapps_guard_bash_parity.py
# 的 _CALLER_FILES，並由該檔 test_caller_files_matches_repo_wide_scan 以全庫掃描
# 機械斷言其與實況相等（人工重數三度數錯後的治本手段）。
#
# 用法：
#   . "<repo根>/tools/lib/windowsapps_guard.sh"
#   if is_real_python_candidate python; then PY=python; fi
#
# 純函式定義檔，無副作用（不 set -e／不 exit）：可安全被 dev_start.sh 這類
# source 語意腳本間接載入而不影響呼叫端 shell 狀態。

# R43 二審 Architect/SD 各自獨立 bug-injection 揪出（訂正一審初版）：初版
# `case "$resolved" in *WindowsApps*)` 有兩個真實缺口，與另兩份 SSOT
# （WindowsAppsGuard.ps1::Test-IsRealPython 的 -notlike 本身大小寫不敏感；
# bootstrap_core.py::_is_windows_apps_stub 對每個路徑片段呼叫 .lower() 後精確
# 比對 "windowsapps"）不對稱：
#   ① 大小寫繞過：bash `case` 預設大小寫敏感，`WINDOWSAPPS`/`WinDowsApps` 等
#      大小寫變體完全漏放。
#   ② 子字串誤判（假陽性）：裸子字串比對會誤傷路徑僅「含有」WindowsApps 字面值
#      但並非該路徑片段本身的合法目錄（如 `MyWindowsAppsBackup/python`），對
#      pre-push 這類阻斷式 hook 而言會誤報「找不到 python」。
# 修法：正規化分隔符（`\`→`/`）+ 全轉小寫 + 前後補 `/` 使比對定錨在「完整路徑
# 片段」而非任意子字串，與另兩份 SSOT 的「逐片段精確比對」語意對齊。
is_real_python_candidate() {
  local name="$1"
  local resolved
  resolved="$(command -v "$name" 2>/dev/null)" || return 1
  local normalized
  normalized="$(printf '%s' "$resolved" | tr '\\' '/' | tr '[:upper:]' '[:lower:]')"
  case "/$normalized/" in
    */windowsapps/*) return 1 ;;
    *) return 0 ;;
  esac
}
