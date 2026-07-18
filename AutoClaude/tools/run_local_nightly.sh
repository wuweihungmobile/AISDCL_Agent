#!/usr/bin/env bash
# run_local_nightly.sh — macOS 本機 nightly 薄聚合器（R11 Architect D1 拍板案）。
#
# 定位：launchd/cron 載體（ONBOARDING.md §8 launchd 範本對應）。只「串接既有
# 驗證腳本」，不重寫任何檢查。與 Windows 版 run_local_nightly.ps1（深度 7-stage：
# local_ci_gate/mutation/pg-e2e/perf/drift/obs/sdd-fsm-chaos）**語意刻意不同**——
# mac 側只要「平台相容性＋回歸」的每日訊號，深度 stage（mutation Docker/pg-e2e/
# perf/obs）留在 Windows 主開發機承載；不移植 929 行 .ps1（避免第二支巨型雙實作）。
# 七軌去向帳目補齊（R11 ARCH-1）：其餘兩軌——drift＝nightly 取證帳本紀律由 Windows
# 主開發機承載（drift_log_history 例行 commit 即其產物）；sdd-fsm-chaos＝非平台敏感
# 之純 Python 邏輯回歸，Windows 本地 nightly 每日承接＋CI chaos workflow 覆蓋，
# mac 薄聚合器均不重複。
# R11 教訓：smoke 全綠 ≠ unittest 全綠，故 [1] 與 [2]~[4] 都必跑。
#
# stage（任一失敗記名後續跑，結尾彙總；任一 FAIL → exit 1，對齊 .ps1 R9 ③ exit 語意）：
#   [1/4] macos_smoke     — /bin/bash 強制系統 bash 3.2（平台相容性聚合驗證）
#   [2/4] root_unittests  — 根層 tools/tests unittest 全套（含測試數量下限釘選）
#   [3/4] autoclaude_gate — AutoClaude tools/local_ci_gate.sh（鏡像 CI push gating）
#   [4/4] sdd_ci_gate     — AISDLC_SDD scripts/ci-gate.sh（凍結基線 + LATEST 雙軌）
#
# log：stdout 直出（launchd 範本已導向 log 檔），不做輪替。
# 相容性：bash 3.2（macOS /bin/bash；禁 declare -A / mapfile / ${var,,}）。
set -u

STAGE_TOTAL=4  # stage 分母單一定義點（R11 P4：原 /4 硬編三處，增刪 stage 易漏改）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# WHY：launchd/cron 環境的 PATH 極簡（通常僅 /usr/bin:/bin:/usr/sbin:/sbin），
# 而 stage 3/4 的閘門腳本內部以裸 `python` 呼叫 venv 工具——.venv/bin 必須先
# prepend 進 PATH，否則排程執行時必在 venv 守門處 fail。
if [ -d "$ROOT/.venv/bin" ]; then
  PATH="$ROOT/.venv/bin:$PATH"; export PATH
fi

# python 解析：優先 monorepo .venv（存在即用），否則退回 PATH 上的 python/python3。
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="$(command -v python || command -v python3 || true)"
fi
if [ -z "$PY" ]; then
  echo "❌ 找不到 python/python3 — 請先跑 tools/dev_start 建置 .venv（ONBOARDING.md §3）" >&2
  exit 1
fi

PASS=0; FAIL=0; FAIL_NAMES=""

run_stage() {  # $1=編號 $2=名稱 $3...=指令；失敗記名不中斷（逐 stage 收集，故不用 set -e）
  _idx="$1"; _name="$2"; shift 2
  printf '\n--- [%s/%s] %s ---\n' "$_idx" "$STAGE_TOTAL" "$_name"
  _start="$(date +%s)"
  "$@"
  _rc=$?
  _secs=$(( $(date +%s) - _start ))
  # 注意：變數展開一律加大括號——bash 3.2 變數名解析走 locale 相依 isalnum()，
  # 裸 $var 後緊接全形字元（如「（」）會被吞進變數名 → set -u 下 unbound 假死。
  if [ "${_rc}" -eq 0 ]; then
    PASS=$((PASS + 1)); printf '%s\n' "--- [${_idx}/${STAGE_TOTAL}] ${_name} PASS（${_secs}s）---"
  else
    FAIL=$((FAIL + 1)); FAIL_NAMES="$FAIL_NAMES ${_name}"
    printf '%s\n' "--- [${_idx}/${STAGE_TOTAL}] ${_name} FAIL rc=${_rc}（${_secs}s）---"
  fi
}

sdd_gate() { (cd "$ROOT/AISDLC_SDD" && bash scripts/ci-gate.sh); }

run_stage 1 macos_smoke     /bin/bash "$ROOT/tools/macos_smoke_local.sh"
run_stage 2 root_unittests  "$PY" "$ROOT/tools/run_root_unittests.py"
run_stage 3 autoclaude_gate bash "$ROOT/AutoClaude/tools/local_ci_gate.sh"
run_stage 4 sdd_ci_gate     sdd_gate

printf '\n===== nightly 彙總：PASS=%s FAIL=%s =====\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "失敗 stage：$FAIL_NAMES" >&2
  exit 1
fi
exit 0
