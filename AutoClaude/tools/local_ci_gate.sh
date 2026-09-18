#!/usr/bin/env bash
# local_ci_gate.sh — 本機 CI 閘門薄殼（macOS/Linux）。Windows 對等：tools/local_ci_gate.ps1
#
# 邏輯全部集中在 tools/local_ci_gate.py（跨平台單一事實源；DEF-101-070 ② 收斂案，
# 模式對齊 tools/dev_start.{py,sh,ps1}）。本檔只做：確認直譯器 → 轉呼叫核心 →
# 傳遞 exit code。薄殼由 monorepo 根 tools/check_wrapper_thinness.py hash 釘選守門。
#
# 用法（介面與收斂前完全相容）：
#   bash tools/local_ci_gate.sh                  # 標準本機閘門（不含 Docker）
#   bash tools/local_ci_gate.sh --act            # 加跑 act Linux 容器真 CI
#   bash tools/local_ci_gate.sh --pg             # 加跑 PG 契約測（pg17）
#   bash tools/local_ci_gate.sh -k test_foo -v   # 非 --act/--pg 參數整批取代預設 pytest 參數
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/../../tools/lib/windowsapps_guard.sh"

# DEF-200-315：互動式入口優先釘死 repo 根層 .venv 直譯器（單一 .venv 設計，
# ONBOARDING §2.1），本機缺席時 fail-loud；CI／逃生口見 pick_repo_python 內註解。
PY="$(pick_repo_python "$SCRIPT_DIR/../..")" || exit 1

export PYTHONUTF8=1
"$PY" "$SCRIPT_DIR/local_ci_gate.py" "$@"
exit $?
