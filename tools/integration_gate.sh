#!/usr/bin/env bash
# integration_gate.sh — AISDCL_Agent 整合層薄聚合閘門薄殼（macOS/Linux）。
# Windows 對等：tools/integration_gate.ps1
#
# 邏輯全部集中在 tools/integration_gate_core.py（跨平台單一事實源；DEF-101-068(b)
# 收斂案，模式對齊 tools/dev_start.{py,sh,ps1} 與 AutoClaude/tools/local_ci_gate.{py,sh,ps1}）。
# 本檔只做：確認直譯器 → 轉呼叫核心 → 傳遞 exit code。薄殼由 monorepo 根
# tools/check_wrapper_thinness.py hash 釘選守門。
#
# 用法（介面與收斂前完全相容）：
#   bash tools/integration_gate.sh              # 完整
#   bash tools/integration_gate.sh --skip-full  # 僅跑 [3]+[4]+[5]（快速迴圈）
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/windowsapps_guard.sh"

# 直譯器選定（DEF-200-275 第四輪 D8／C14 候選鏈，DEF-200-315（2026-09-19 掌舵者
# 裁決）訂正：單一 .venv 設計下互動式入口一律優先釘死 repo 根層 .venv，不再從
# PATH 挑 python/python3；`pick_repo_python` 同檔 SSOT，只在 CI／逃生口才落回
# PATH 候選，找不到時已在 stderr 印補救指令，本殼不必再印）。仍屬薄殼三職責之一
# （選直譯器）；殼內零迴圈（check_wrapper_thinness 黑名單：for／while／python -c
# 皆不得出現）。
PY="$(pick_repo_python "$SCRIPT_DIR/..")" || exit 1

export PYTHONUTF8=1
"$PY" "$SCRIPT_DIR/integration_gate_core.py" "$@"
exit $?
