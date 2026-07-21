#!/usr/bin/env bash
# bootstrap.sh — monorepo 一鍵開發環境整備薄殼（macOS / Linux）。
# Windows 對等腳本：tools/bootstrap.ps1
#
# 邏輯全部集中在 tools/bootstrap_core.py（跨平台單一事實源；第 16 輪架構最佳化
# Architect 建議 B，模式對齊 AutoClaude/tools/local_ci_gate.{py,sh,ps1} 既有先例）。
# 本檔只做：找一個可用的 python 直譯器（.venv 尚未存在，不可假設已啟用）→
# 轉呼叫核心 → 傳遞 exit code。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=""
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ 找不到 python3/python — 無法啟動 bootstrap_core.py。請先安裝 Python >= 3.11。" >&2
  exit 1
fi

"$PY" "$SCRIPT_DIR/bootstrap_core.py" "$@"
exit $?
