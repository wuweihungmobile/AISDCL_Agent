#!/usr/bin/env bash
# Phase G M5 / ACT-042 / B5.6 — TLC runner (Linux / macOS / CI)
#
# ⚠️ LEGACY 兩軌快驗（v0.02 / DEF-01-002 註記）：本腳本僅實裝 SDD_FSM + FLEET_FSM
#    兩軌。五軌完整驗證（SDD/META/COMPOSITION/OPTIMIZATION/FLEET_FSM）請走
#    Python 真相源：python -m tools.fsm_runtime.tlc_runner --module <五軌各一>
#    （scripts/ci-gate.sh --full-tlc 即以迴圈呼叫五軌）。
#
# 用途：在 PR / nightly 跑 TLC 對 SDD_FSM.tla 做形式化驗證。
# 對應規則：CLAUDE.md Rule 9.18.1~9.18.4
#
# 使用：
#   bash run_tlc.sh                  # 跑完整驗證
#   bash run_tlc.sh --install-only   # 僅下載 tla2tools.jar
#   bash run_tlc.sh --depth 100      # 自訂探索深度上限
#
# Exit codes：
#   0 — 全部通過
#   1 — TLC 偵測 invariant violation / liveness violation / deadlock
#   2 — 環境錯誤（Java 缺失 / jar 下載失敗）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/lib"
JAR_PATH="${LIB_DIR}/tla2tools.jar"
TLA_VERSION="${TLA_VERSION:-v1.8.0}"
JAR_URL="https://github.com/tlaplus/tlaplus/releases/download/${TLA_VERSION}/tla2tools.jar"
DEPTH="${DEPTH:-50}"
INSTALL_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-only) INSTALL_ONLY=1; shift ;;
        --depth) DEPTH="$2"; shift 2 ;;
        --help|-h)
            sed -n '2,15p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# Step 1 — 環境檢查（Java）
if ! command -v java >/dev/null 2>&1; then
    echo "ERROR: java not found. Install JDK 11+ first." >&2
    exit 2
fi
JAVA_VER=$(java -version 2>&1 | head -1)
echo "[run_tlc] Java: ${JAVA_VER}"

# Step 2 — 下載 tla2tools.jar（若不存在）
mkdir -p "${LIB_DIR}"
if [[ ! -f "${JAR_PATH}" ]]; then
    echo "[run_tlc] tla2tools.jar 不存在，從 ${JAR_URL} 下載..."
    if command -v curl >/dev/null 2>&1; then
        curl -fSL --retry 3 -o "${JAR_PATH}" "${JAR_URL}"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "${JAR_PATH}" "${JAR_URL}"
    else
        echo "ERROR: curl 與 wget 皆不可用" >&2
        exit 2
    fi
    if [[ ! -s "${JAR_PATH}" ]]; then
        echo "ERROR: 下載失敗" >&2
        exit 2
    fi
    echo "[run_tlc] 下載完成：$(du -h "${JAR_PATH}" | cut -f1)"
fi

if [[ "${INSTALL_ONLY}" -eq 1 ]]; then
    echo "[run_tlc] --install-only：完成。"
    exit 0
fi

# Step 3 — 跑 TLC
cd "${SCRIPT_DIR}"
LOG_FILE="${SCRIPT_DIR}/tlc_run.log"
echo "[run_tlc] Running TLC with depth=${DEPTH}..."
set +e
java -XX:+UseParallelGC -cp "${JAR_PATH}" tlc2.TLC \
    -config SDD_FSM.cfg \
    -workers auto \
    -depth "${DEPTH}" \
    SDD_FSM.tla > "${LOG_FILE}" 2>&1
TLC_EXIT=$?
set -e

# Step 4 — 解析結果
echo "[run_tlc] TLC 退出碼: ${TLC_EXIT}"
echo "[run_tlc] 完整 log: ${LOG_FILE}"

# 抓 reachable states / distinct states / depth（QA 修 1：non-anchored regex）
# TLC 實際輸出範例：
#   "2853 states generated, 583 distinct states found, 0 states left on queue."
#   "The depth of the complete state graph search is 29."
DISTINCT=$(grep -oE '[0-9]+ distinct states found' "${LOG_FILE}" | head -1 | awk '{print $1}' || true)
GENERATED=$(grep -oE '[0-9]+ states generated' "${LOG_FILE}" | head -1 | awk '{print $1}' || true)
DEPTH=$(grep -oE 'depth of the complete state graph search is [0-9]+' "${LOG_FILE}" | head -1 | awk '{print $NF}' || true)
DISTINCT="${DISTINCT:-0}"
GENERATED="${GENERATED:-0}"
DEPTH="${DEPTH:-0}"
echo "[run_tlc] distinct states: ${DISTINCT}"
echo "[run_tlc] generated states: ${GENERATED}"
echo "[run_tlc] depth: ${DEPTH}"

# Machine-readable summary (供 CI assertion 直接 grep)
echo "TLC_DISTINCT=${DISTINCT}"
echo "TLC_GENERATED=${GENERATED}"
echo "TLC_DEPTH=${DEPTH}"

if [[ "${TLC_EXIT}" -ne 0 ]]; then
    echo "[run_tlc] ❌ SDD_FSM TLC 驗證失敗（見 log 上方錯誤訊息）" >&2
    tail -30 "${LOG_FILE}" >&2
    exit 1
fi
echo "[run_tlc] ✅ SDD_FSM TLC 驗證通過（safety + EventuallyTerminal + ObservationsTransient）"

# Step 5 — Phase I M5 / ACT-072：parametric FLEET_FSM（艦隊並行 no-deadlock + bounded join）
# 5a：safety（含 SYMMETRY 縮減狀態空間）；5b：liveness（無 SYMMETRY，健全前提）
# 為何分兩跑：TLC 在 SYMMETRY 下檢查 liveness 屬 unsound（可能漏掉違規），故 AllEventuallyDone
# 必在無 symmetry 的 FLEET_FSM_LIVENESS.cfg 窮舉驗證。
FLEET_LOG="${SCRIPT_DIR}/fleet_tlc.log"
FLEET_LIVE_LOG="${SCRIPT_DIR}/fleet_tlc_liveness.log"
echo "[run_tlc] Running FLEET_FSM TLC 5a (safety + symmetry: LockMutex/NoPartialHold)..."
set +e
java -XX:+UseParallelGC -cp "${JAR_PATH}" tlc2.TLC \
    -config FLEET_FSM.cfg \
    -workers auto \
    FLEET_FSM.tla > "${FLEET_LOG}" 2>&1
FLEET_EXIT=$?
set -e
if [[ "${FLEET_EXIT}" -ne 0 ]]; then
    echo "[run_tlc] ❌ FLEET_FSM safety 驗證失敗（見 ${FLEET_LOG}）" >&2
    tail -30 "${FLEET_LOG}" >&2
    exit 1
fi
echo "[run_tlc] ✅ FLEET_FSM safety 通過（LockMutex + NoPartialHold）"

echo "[run_tlc] Running FLEET_FSM TLC 5b (liveness, NO symmetry: AllEventuallyDone)..."
set +e
java -XX:+UseParallelGC -cp "${JAR_PATH}" tlc2.TLC \
    -config FLEET_FSM_LIVENESS.cfg \
    -workers auto \
    FLEET_FSM.tla > "${FLEET_LIVE_LOG}" 2>&1
FLEET_LIVE_EXIT=$?
set -e
if [[ "${FLEET_LIVE_EXIT}" -eq 0 ]]; then
    echo "[run_tlc] ✅ FLEET_FSM liveness 通過（AllEventuallyDone，無 symmetry 健全驗證）"
    exit 0
else
    echo "[run_tlc] ❌ FLEET_FSM liveness 驗證失敗（見 ${FLEET_LIVE_LOG}）" >&2
    tail -30 "${FLEET_LIVE_LOG}" >&2
    exit 1
fi
