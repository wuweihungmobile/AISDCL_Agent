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

# 直譯器候選鏈（DEF-200-275 第四輪 D8／C14）：python → python3 → 根層 .venv/bin/python，
# 與 tools/git-hooks/pre-push 的 $PY 候選鏈同形。WHY：未 source venv 的 macOS 只有 python3；
# pre-push 整合閘門 leg 先以候選鏈找到直譯器、再 `bash tools/integration_gate.sh`，本殼若只認
# `python` 就會在同一台機器上自相矛盾地失敗。仍屬薄殼三職責之一（選直譯器）；殼內零迴圈
# （check_wrapper_thinness 黑名單：for／while／python -c 皆不得出現）。找不到就 fail-loud。
PY=""
if is_real_python_candidate python; then PY=python
elif is_real_python_candidate python3; then PY=python3
elif is_real_python_candidate "$SCRIPT_DIR/../.venv/bin/python"; then PY="$SCRIPT_DIR/../.venv/bin/python"
fi
[ -n "$PY" ] || { echo '❌ 找不到 python／python3／.venv/bin/python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）' >&2; exit 1; }

export PYTHONUTF8=1
"$PY" "$SCRIPT_DIR/integration_gate_core.py" "$@"
exit $?
