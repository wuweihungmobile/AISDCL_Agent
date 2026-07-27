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
#
# ── 覆蓋邊界（R58 真 Windows 11 實機量測，三段式；勿改寫成「保證候選可用」）──
# 本函式是**純路徑字串比對**，不執行候選直譯器。這是刻意的：bootstrap 悖論下它
# 必須零成本、無副作用（pre-push 這類阻斷式 hook 每次 push 都會走到），執行一個
# 來歷不明的 python 本身就是要避免的成本。
#
# 已實測涵蓋：`command -v` 命中 `%LOCALAPPDATA%/Microsoft/WindowsApps` 底下的
#   Windows Store App Execution Alias 空殼（含 `WINDOWSAPPS`／`WinDowsApps` 等
#   大小寫變體；比對定錨在完整路徑片段，`MyWindowsAppsBackup/python` 不誤判）。
# 已實測不涵蓋：pyenv-win shim 這類「PATH 上有、`command -v` 判定存在、實際執行
#   卻不是可用直譯器」的第二種形狀。R58 以固定 fixture 實測（PATH 只留 fixture
#   目錄）：對「印訊息到 stderr 後非零退出」（模擬 pyenv `No global/local python
#   version has been set`）與「零退出但不執行任何 Python」兩種假 shim，本函式
#   **皆回傳 ACCEPTED**，隨後呼叫端真的執行它時才失敗（rc=1／rc=0 但什麼都沒做）。
#   同款 fixture 下 PowerShell 側 `Test-IsRealPython` 亦回傳 `True`，兩份 guard
#   對稱地看不到這一類。macOS／Linux 沒有 pyenv-win shim，故只有真 Windows 上
#   看得見。Python 側 `tools/bootstrap_core.py::pick_python()` 在同款路徑比對
#   **之後**另有 `_probe_ok()` 執行探測層（實測：對非零退出的假 shim 判 False、
#   對零退出空殼判 True），bash／ps1 兩側則沒有對應層。
# 未窮舉：其他「存在但不可用」形狀（權限不足、DLL 缺失、asdf/conda 之類其他
#   version manager 的 shim）皆未逐一量測。
#
# 為什麼不在此補探測：修法應落在**呼叫端已確定要用該直譯器之後**加一道極輕探測，
# 而不是把成本壓進這支被 pre-push 每次載入的純函式。呼叫端一覽見
# `tools/tests/test_windowsapps_guard_bash_parity.py::_CALLER_FILES`（機械維護）。

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
