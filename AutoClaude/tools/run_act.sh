#!/usr/bin/env bash
# run_act.sh — 在本機 Docker 內以 act 重現 GitHub Actions（autoclaude-ci.yml）薄殼（macOS/Linux）。
# Windows 對等：tools/run_act.ps1
#
# 邏輯全部集中在 tools/run_act_core.py（跨平台單一事實源；仿 R12 DEF-101-070 ② local_ci_gate
# 收斂模式）。本檔只做：確認直譯器 → 轉呼叫核心 → 傳遞 exit code。
#
# 用法（介面與收斂前完全相容）：
#   bash tools/run_act.sh --job test     # 最快：只跑主測試閘門
#   bash tools/run_act.sh                 # 完整：跑 push 全部 job（含 PG 契約）
#   bash tools/run_act.sh --list          # 列出所有 job
#   bash tools/run_act.sh --dry-run       # 只解析不執行
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../../tools/lib/windowsapps_guard.sh"

is_real_python_candidate python || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

export PYTHONUTF8=1
python "$SCRIPT_DIR/run_act_core.py" "$@"
exit $?
