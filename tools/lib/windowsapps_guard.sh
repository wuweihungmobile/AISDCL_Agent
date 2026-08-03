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

# ─────────────────────────────────────────────────────────────────────────────
# R69 P2：「挑一個 >= 3.11 直譯器」候選鏈（bash 側）。
#
# WHY 放在本檔而不是另開一支 lib：本檔就是 repo 內「python 候選是否可用」的
# SSOT（`is_real_python_candidate` 判「這個候選是不是真直譯器」），版本下限只是
# 同一個問題的第二個維度（「是不是**能用的**直譯器」）；另開檔會多出一組
# check_script_parity 納管／_CALLER_FILES 登記面，卻不會讓判斷更集中。
#
# 為何需要（R69 前 macOS 入門路徑實際是斷的，真機重現）：`tools/dev_start.sh`
# 的候選清單只有 `python3` / `python`，而 macOS 的 `python3` 恆為系統 3.9.6
# （Homebrew 的 python@3.11 是 keg-only，`brew install python@3.11` **不會**
# 改寫 `python3`，只放 `/opt/homebrew/bin/python3.11`）。於是照 ONBOARDING §1
# 逐字裝完 3.11 之後，dev_start 仍撿到 3.9 → `tools/dev_start.py` 版本前置閘
# rc=2，ONBOARDING §2.1「全新機器可直接執行 dev_start」在 mac 上為假。R68 只
# 把 traceback 換成友善訊息（DEF-101-628），沒動選擇邏輯，缺陷本體仍在。
#
# 版本下限 SSOT＝`tools/dev_start.py::_MIN_PY`；本檔與 `WindowsAppsGuard.ps1`
# 的字面值由 tools/tests/test_dev_start.py::
# test_min_python_version_is_consistent_across_dev_start_ssots 機械鎖住同步。
PYTHON_GE_MIN_MM="3.11"
# 順序＝優先序：先 `.python-version` 目標版（3.11）、再較新版、最後裸 python3/
# python（Linux 上常已是 3.11+）；PATH 全失手時再試 Homebrew（arm64 /opt、
# Intel /usr/local）與 pyenv shim 的常見絕對路徑——`brew install python@3.11`
# 後 PATH 尚未 rehash／未把 /opt/homebrew/bin 加進 PATH 的新機器就靠這段救。
# 形狀對齊 tools/bootstrap_core.py::pick_python() 的 candidates 清單。
# 🔴 用**陣列**而非空白分隔字串：`source tools/dev_start.sh` 的主場是 macOS 預設
# 的 zsh，而 zsh 對未加引號的參數展開**不做**字詞切分（SH_WORD_SPLIT 預設關閉）
# ⇒ `for c in $LIST` 在 zsh 下整條清單會變成單一候選、一支都命中不了（實測
# `source tools/dev_start.sh` rc=1，bash 下卻正常——正是最難察覺的那種雙 shell
# 落差）。`"${arr[@]}"` 在 bash 3.2（macOS /bin/bash）與 zsh 皆為逐元素展開。
PYTHON_GE_MIN_CANDIDATES=(
  python3.11 python3.12 python3.13 python3 python
  /opt/homebrew/opt/python@3.11/bin/python3.11 /opt/homebrew/bin/python3.11
  /usr/local/opt/python@3.11/bin/python3.11 /usr/local/bin/python3.11
  "${HOME:-/nonexistent}/.pyenv/shims/python3.11"
)

# 探測程式：版本達標才印出直譯器絕對路徑，否則印空字串（rc 仍為 0）。
# 與 .ps1 側 `Get-PythonGeMin` 用**同一段**探測碼（同構，非各自發明）。逐字相同由
# tools/tests/test_dev_start.py::TestMinPythonVersionSsotSync::
# test_version_probe_literal_is_byte_identical_across_both_shells 機械鎖住——在此之前
# 只有散文宣稱「逐字相同」，單邊改可以通過所有閘門（DEF-101-760 就是這樣只修一邊）。
#
# 🔴 空字串寫 `str()` 而**不是** `""`：bash 這邊 `""` 本來沒問題，但 Windows
# PowerShell 5.1 把參數交給原生執行檔時會吃掉內嵌的一個雙引號，讓 .ps1 側同一段
# 探測碼變成 `SyntaxError: unterminated string literal` ⇒ 所有候選被淘汰
# （詳見 tools/lib/WindowsAppsGuard.ps1 同位置的 WHY 區塊）。`str()` 語意相同且
# 不含引號字元，兩側同步採用才能維持「逐字相同」這個前提。
PYTHON_GE_MIN_PROBE='import sys;print(sys.executable if sys.version_info[:2] >= (3, 11) else str())'

# 回傳（stdout）第一個可用且 >= 3.11 的直譯器**絕對路徑**；一個都沒有回 rc=1。
pick_python_ge_min() {
  local cand resolved
  for cand in "${PYTHON_GE_MIN_CANDIDATES[@]}"; do
    is_real_python_candidate "$cand" || continue
    resolved="$("$cand" -c "$PYTHON_GE_MIN_PROBE" 2>/dev/null)" || continue
    if [ -n "$resolved" ]; then
      printf '%s\n' "$resolved"
      return 0
    fi
  done
  return 1
}

# fail-loud 補救指引（stderr）——只印**逐字可執行**的指令，不印「請安裝 Python」
# 這種要使用者自己翻文件的句子。
python_ge_min_remediation() {
  echo "❌ 找不到 Python >= ${PYTHON_GE_MIN_MM} 直譯器（dev_start 核心需 ${PYTHON_GE_MIN_MM}+）。" >&2
  echo "   已依序嘗試：${PYTHON_GE_MIN_CANDIDATES[*]}" >&2
  echo "   macOS 補救（擇一，逐字可執行）：" >&2
  echo "     brew install python@3.11" >&2
  echo "     curl -LsSf https://astral.sh/uv/install.sh | sh && uv python install 3.11" >&2
  echo "   Linux 補救（擇一，逐字可執行）：" >&2
  echo "     sudo apt-get update && sudo apt-get install -y python3.11" >&2
  echo "     sudo dnf install -y python3.11" >&2
  echo "   裝完重開終端機（PATH 需重新載入）後再執行：source tools/dev_start.sh" >&2
}
