#!/usr/bin/env bash
# integration_gate.sh — AISDCL_Agent 整合層薄聚合閘門（macOS/Linux）。
# Windows 對等：tools/integration_gate.ps1（本檔為其忠實對照）。
#
# 設計原則：不另立第三真相源，僅依序呼叫兩專案既有單一真相源再跑整合煙霧測試。
#   [1/5] AutoClaude   : tools/local_ci_gate.sh
#   [2/5] AISDLC_SDD   : bash scripts/ci-gate.sh
#   [3/5] 整合測試     : pytest tests/integration/test_sdd_bridge/ -q
#   [4/5] 回退驗證     : pytest tests/integration/test_sdd_bridge/test_rollback_compat.py -q
#   [5/5] cc-switch A/B: 多模型後端對比（未安裝 CLI → SKIP）
#
# 用法：
#   bash tools/integration_gate.sh              # 完整
#   bash tools/integration_gate.sh --skip-full  # 僅跑 [3]+[4]+[5]（快速迴圈）
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# venv 提示：各節都靠裸 python，未啟用 venv 就直接失敗提示（勝過各節逐一噴錯）
command -v python >/dev/null || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

SKIP_FULL=0
[ "${1:-}" = "--skip-full" ] && SKIP_FULL=1

FAILURES=(); PASS_COUNT=0; SKIP_COUNT=0

run_section() {
  local label="$1"; shift
  printf '\n==> %s\n' "$label"
  ( "$@" )
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    FAILURES+=("$label (exit=$rc)")
    printf '❌ %s FAILED (exit=%s)\n' "$label" "$rc"
  else
    PASS_COUNT=$((PASS_COUNT+1))
    printf '✅ %s PASS\n' "$label"
  fi
}

sec_autoclaude() { cd "$ROOT/AutoClaude" && bash tools/local_ci_gate.sh; }
sec_sdd()        { cd "$ROOT/AISDLC_SDD" && bash scripts/ci-gate.sh; }
sec_bridge()     { cd "$ROOT/AutoClaude" && python -m pytest tests/integration/test_sdd_bridge/ -q; }
sec_rollback()   { cd "$ROOT/AutoClaude" && python -m pytest tests/integration/test_sdd_bridge/test_rollback_compat.py -q; }

if [ "$SKIP_FULL" -eq 0 ]; then
  run_section "[1/5] AutoClaude local_ci_gate" sec_autoclaude
  run_section "[2/5] AISDLC_SDD ci-gate.sh" sec_sdd
fi
run_section "[3/5] SDD bridge 整合煙霧" sec_bridge
run_section "[4/5] 回退驗證（v0.01/v0.02 真品 FSM 狀態）" sec_rollback

printf '\n==> [5/5] cc-switch 多模型 A/B 驗收\n'
CC_CLI=""
for name in cc-switch cc-switch-cli ccs; do
  if command -v "$name" >/dev/null 2>&1; then CC_CLI="$name"; break; fi
done
SMOKE_PB="$ROOT/AutoClaude/scripts/sdd_bridge_smoke.yaml"
if [ -f "$SMOKE_PB" ]; then PB_REL="scripts/sdd_bridge_smoke.yaml"; else PB_REL="⚠️載具缺失:scripts/sdd_bridge_smoke.yaml(DEF-10-001a)"; fi
if [ -z "$CC_CLI" ]; then
  SKIP_COUNT=$((SKIP_COUNT+1))
  echo "⚠️  SKIP：未偵測到 cc-switch CLI（DEF-01-007）。farion1231/cc-switch 為 GUI app 不上 PATH；"
  echo "    headless A/B 需 CLI 變體（SaladDay/cc-switch-cli）。裝好後於 AutoClaude/ 執行："
  echo "    cc-switch use <profile-A> && autoclaude $PB_REL --fresh（換 profile-B 再跑一次），"
  echo "    對比：一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / token 峰值"
else
  PASS_COUNT=$((PASS_COUNT+1))
  echo "cc-switch CLI 已偵測（${CC_CLI}）：於 AutoClaude/ 對 ${PB_REL} 切換 profile 各跑一次 --fresh，收集 A/B 四指標"
fi

if [ "${#FAILURES[@]}" -gt 0 ]; then
  # 多字元 join：IFS 只取首字元（'; ' 只會用 ';'），改用迴圈以 "; " 連接
  joined=""
  for f in "${FAILURES[@]}"; do
    if [ -z "$joined" ]; then joined="$f"; else joined="$joined; $f"; fi
  done
  printf '\n❌ 整合閘門未通過：%s\n' "$joined"
  exit 1
fi
printf '\n✅ 整合閘門通過（%s PASS / %s SKIP）\n' "$PASS_COUNT" "$SKIP_COUNT"
exit 0
