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
#   bash tools/run_act.sh --list          # 列出 job ＋ 全庫盤點
#   bash tools/run_act.sh --dry-run       # 只解析不執行
#   bash tools/run_act.sh --workflow .github/workflows/root-infra-ci.yml --job root-infra
#   bash tools/run_act.sh --workflow .github/workflows/aisdlc-sdd-drift-daily.yml \
#       --event schedule --job daily      # on: 不含 push 的 5 支必須指定事件
#
# 射程（本輪補記）：不加 --workflow 時只看得到 autoclaude-ci.yml 那一支的 9 個 job；
# monorepo 根層共 11 支 workflow／25 個 job。本殼是 `"$@"` 全轉，故 --workflow 直接可用
# （Windows 對等殼 run_act.ps1 是顯式 param 映射，尚未轉該旗標，需改用環境變數
# RUN_ACT_WORKFLOW——不對稱處已寫在該檔檔頭與 run_act_core.py 檔頭 (1)）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../../tools/lib/windowsapps_guard.sh"

is_real_python_candidate python || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

export PYTHONUTF8=1
python "$SCRIPT_DIR/run_act_core.py" "$@"
exit $?
