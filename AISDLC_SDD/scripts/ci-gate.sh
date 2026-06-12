#!/usr/bin/env bash
# AISDLC-SDD — 本機 CI 閘門（push 前必過）。
#
# 單一真相源：.github/workflows/ci.yml、docker-compose ci-runner、pre-push
# hook、act 一律呼叫本腳本，確保「地端 = ubuntu-latest」跑同一組檢查。
#
# 用法：
#   bash scripts/ci-gate.sh              # 離線閘門（pytest 含 offline reachability + arch_fitness）
#   bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java + tla2tools.jar）
#   SDD_RUN_TLC=1 bash scripts/ci-gate.sh
#
# Exit：0 全過；非 0 任一硬閘門失敗（arch_fitness structural fail 視為失敗，
#       advisory warn 不阻擋，與 nightly-strict 同語意）。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FW_DIR="${REPO_ROOT}/AISDLC_SDD_v0.01"
cd "${FW_DIR}"

FULL_TLC=0
if [[ "${1:-}" == "--full-tlc" || "${SDD_RUN_TLC:-0}" == "1" ]]; then
  FULL_TLC=1
fi

echo "==> [1/3] 離線測試套件 pytest -m 'not chaos'（全套，含 offline reachability BFS）"
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q

echo "==> [2/3] 架構適應度 arch_fitness（structural fail 阻擋；advisory warn 放行）"
# 必帶 --strict：唯有 --strict 時 structural fail 才回傳 exit 2（見 arch_fitness.py
# `if args.strict and report.fails: return 2`）；否則即使有 structural fail 也只回 1
# 被當 advisory 放行 → 與雲端 nightly-strict 同語意，避免地端漏接。
set +e
python -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
AF_CODE=$?
set -e
if [[ "${AF_CODE}" -ge 2 ]]; then
  echo "::error:: arch_fitness 偵測 structural fail（exit=${AF_CODE}）"
  exit 1
fi
[[ "${AF_CODE}" -eq 1 ]] && echo "(arch_fitness advisory warn — 不阻擋)"

if [[ "${FULL_TLC}" == "1" ]]; then
  echo "==> [3/3] 五軌 TLA+/TLC 形式化驗證"
  for m in SDD_FSM META_FSM FLEET_FSM COMPOSITION_FSM OPTIMIZATION_FSM; do
    echo "  -- TLC ${m}"
    python -m tools.fsm_runtime.tlc_runner --module "${m}"
  done
else
  echo "==> [3/3] 跳過完整 TLC（offline reachability 已隨 pytest 驗證）；--full-tlc 可啟用"
fi

echo "✅ 本機 CI 閘門全數通過"
