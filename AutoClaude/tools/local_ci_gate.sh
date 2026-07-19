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

# 直譯器選擇維持收斂前語意：PATH 上的 python（所有 gate 都靠已啟用的 venv），
# 未啟用 venv 就直接失敗提示（勝過各 gate 逐一噴錯）
command -v python >/dev/null || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

export PYTHONUTF8=1
python "$SCRIPT_DIR/local_ci_gate.py" "$@"
exit $?
