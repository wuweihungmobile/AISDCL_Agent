#!/usr/bin/env bash
# bootstrap.sh — monorepo 一鍵開發環境整備薄殼（macOS / Linux）。
# Windows 對等腳本：tools/bootstrap.ps1
#
# 邏輯全部集中在 tools/bootstrap_core.py（跨平台單一事實源；第 16 輪架構最佳化
# Architect 建議 B，模式對齊 AutoClaude/tools/local_ci_gate.{py,sh,ps1} 既有先例）。
# 本檔只做：找一個可用的 python 直譯器（.venv 尚未存在，不可假設已啟用）→
# 轉呼叫核心 → 傳遞 exit code。
set -u

# DEF-101-702：zsh／sh 下 `${BASH_SOURCE[0]}` 未定義 ⇒ SCRIPT_DIR 解到呼叫端 cwd，後續 source／
# 直譯器選擇全部找錯路徑並印出與事實相反的訊息。fail-loud 擋在最前面（`$BASH_VERSION` 在 zsh／sh 下為空）。
if [ -z "${BASH_VERSION:-}" ]; then
  echo "❌ 本腳本需以 bash 執行：bash <本腳本路徑>（zsh／sh 沒有 BASH_SOURCE，會把腳本目錄解錯）" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/windowsapps_guard.sh"

PY=""
if is_real_python_candidate python3; then
  PY=python3
elif is_real_python_candidate python; then
  PY=python
else
  echo "❌ 找不到 python3/python — 無法啟動 bootstrap_core.py。請先安裝 Python >= 3.11。" >&2
  exit 1
fi

"$PY" "$SCRIPT_DIR/bootstrap_core.py" "$@"
exit $?
