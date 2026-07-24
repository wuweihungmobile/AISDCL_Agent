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

# 直譯器選擇維持收斂前語意：PATH 上的 python（所有段落都靠已啟用的 venv），
# 未啟用 venv 就直接失敗提示（勝過各段落逐一噴錯）
is_real_python_candidate python || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

export PYTHONUTF8=1
python "$SCRIPT_DIR/integration_gate_core.py" "$@"
exit $?
