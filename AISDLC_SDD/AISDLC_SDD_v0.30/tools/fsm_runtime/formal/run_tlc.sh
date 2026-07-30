#!/usr/bin/env bash
# Phase G M5 / ACT-042 / B5.6 — TLC runner (Linux / macOS / CI)
#
# 🔴 R65（ADR-XPLAT-002 §5 Phase 2-A）：本檔改為薄殼，實際 TLC 呼叫／摘要解析／
#    jar 下載邏輯全數委派 Python 真相源 tools.fsm_runtime.tlc_runner（同目錄上層
#    tlc_runner.py）；本檔只負責 (1) 找可用 python (2) 解析既有命令列慣例並原樣
#    轉傳 (3) 依既有三軌流程（SDD_FSM 完整 + FLEET_FSM safety + FLEET_FSM liveness）
#    依序呼叫、任一階段 rc 非 0 立即中止並原樣回傳。五軌完整驗證另可直接：
#      python -m tools.fsm_runtime.tlc_runner --module <五軌各一>
#    （scripts/ci-gate.sh --full-tlc 即以迴圈呼叫五軌，非本檔改動範圍）。
#
# 🔴 R65 修復（四方複審 MAJOR）：裸執行（非 --install-only）三軌呼叫恆帶 --download，
#    還原薄殼化前「lib/tla2tools.jar 不存在時自動下載」的既有使用者體驗（舊版
#    set -euo pipefail 主體本就無條件下載，非 opt-in）；不需額外記住旗標。
#
# 用途：在 PR / nightly 跑 TLC 對 SDD_FSM.tla 做形式化驗證。
# 對應規則：CLAUDE.md Rule 9.18.1~9.18.4
#
# 使用（既有呼叫慣例不變）：
#   bash run_tlc.sh                  # 跑完整驗證（SDD_FSM + FLEET_FSM safety/liveness；
#                                     #   jar 缺失時自動下載 DEFAULT_TLA_VERSION）
#   bash run_tlc.sh --install-only   # 僅下載 tla2tools.jar
#   bash run_tlc.sh --depth 100      # 自訂 SDD_FSM 探索深度上限（環境變數 DEPTH 亦可）
#   TLA_VERSION=v1.8.1 bash run_tlc.sh --install-only  # 覆寫下載版本（R65 item4 恢復）
#
# Exit codes：
#   0 — 全部通過
#   1 — TLC 偵測 invariant violation / liveness violation / deadlock
#   2 — 環境錯誤（Java 缺失 / jar 下載失敗 / python 缺失）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# formal/ 的祖父層即 <SDD 版本根>/，`python -m tools.fsm_runtime.tlc_runner` 須以此為 cwd
TOOLS_PARENT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
DEPTH="${DEPTH:-50}"
INSTALL_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-only) INSTALL_ONLY=1; shift ;;
        --depth) DEPTH="$2"; shift 2 ;;
        --help|-h) sed -n '2,29p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# R65 item4：TLA_VERSION 環境變數若設值才轉傳 --tla-version（薄殼化前舊行為的等價
# 恢復——沒設值就不傳、tlc_runner.py 沿用其 DEFAULT_TLA_VERSION 常數，行為不變）。
TLA_VERSION_ARGS=()
if [[ -n "${TLA_VERSION:-}" ]]; then
    TLA_VERSION_ARGS=(--tla-version "${TLA_VERSION}")
fi

# python 探測須經共用 windowsapps_guard.sh SSOT 排除 WindowsApps 空殼
# （DEF-101-353 系統性缺口收斂；同 AISDLC_SDD/scripts/ci-gate.sh 慣例，非本檔
# 獨立重寫裸 `command -v` 判斷）。
REPO_ROOT="$(cd "${TOOLS_PARENT}/../.." && pwd)"
# shellcheck disable=SC1091
. "${REPO_ROOT}/tools/lib/windowsapps_guard.sh"
PYTHON_BIN=""
for _cand in python3 python; do
    if is_real_python_candidate "${_cand}"; then PYTHON_BIN="${_cand}"; break; fi
done
if [[ -z "${PYTHON_BIN}" ]]; then
    echo "ERROR: 找不到 python3/python（或僅偵測到 WindowsApps 空殼），請安裝 Python 3.11+。" >&2
    exit 2
fi

cd "${TOOLS_PARENT}"

if [[ "${INSTALL_ONLY}" -eq 1 ]]; then
    "${PYTHON_BIN}" -m tools.fsm_runtime.tlc_runner --install-only "${TLA_VERSION_ARGS[@]}"
    exit $?
fi

echo "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 SDD_FSM（depth=${DEPTH}）..."
set +e
"${PYTHON_BIN}" -m tools.fsm_runtime.tlc_runner --module SDD_FSM --depth "${DEPTH}" --download "${TLA_VERSION_ARGS[@]}"
RC=$?
set -e
[[ "${RC}" -ne 0 ]] && exit "${RC}"

echo "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 FLEET_FSM 5a（safety + symmetry）..."
set +e
"${PYTHON_BIN}" -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --download "${TLA_VERSION_ARGS[@]}"
RC=$?
set -e
[[ "${RC}" -ne 0 ]] && exit "${RC}"

echo "[run_tlc] 委派 tools.fsm_runtime.tlc_runner 跑 FLEET_FSM 5b（liveness, NO symmetry）..."
set +e
"${PYTHON_BIN}" -m tools.fsm_runtime.tlc_runner --module FLEET_FSM --cfg FLEET_FSM_LIVENESS.cfg --download "${TLA_VERSION_ARGS[@]}"
RC=$?
set -e
exit "${RC}"
