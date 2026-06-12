#!/usr/bin/env bash
# 由 tools/run_local_nightly.ps1 透過 `docker run python:3.11-slim bash /workspace/tools/run_mutmut_in_docker.sh` 呼叫。
# 目的：將 mutmut 安裝 + 執行 + results 全部封裝在 Linux container 內，
#       避免 PowerShell here-string + bash -c "..." 雙層 quoting 把 --paths-to-mutate 截斷。
#
# 對應 SD_Improving_09 觀察期 #1（mutation pilot — TokenGuardPlugin）。
# CI continue-on-error: true → 即便 mutmut 不存在/失敗也持續流程，但 log 一定要有真實結果或明確錯誤。
# SD_09 W2 audit P1-AUDIT-16 修復：
# 不用 `set -e` — 因 mutmut 預期會以 bitmask exit code 結束（survived/timeout/suspicious 非零），
# 加 -e 會在 `mutmut run` 後立即終止，無法走到 P0-G cache query / counts 寫入。
# 改：每個關鍵 step 顯式檢查 $? 並 `exit` 對應 code（已實作）。
set -uo pipefail

LOG_FILE="${LOG_FILE:-mutation_token_guard.log}"
MODULE_PATH="${MODULE_PATH:-autoclaude/plugins/token_guard}"
TESTS_DIR="${TESTS_DIR:-tests/plugins/token_guard}"

# P1-R62-7 修復（2026-06-13，紀律 #18）：LOG_FILE 正規化為絕對路徑（落 /workspace），
# 因後續 mutmut 改在隔離樹 /tmp/mutwork 執行（cd 後相對路徑會寫錯位置）。
case "${LOG_FILE}" in
  /*) : ;;
  *) LOG_FILE="/workspace/${LOG_FILE}" ;;
esac

# SD_09 W2 zero-trust audit P0-AUDIT-01 修復：log 一律 append，不再以末段 `>` 一次覆寫；
# 先用 truncate 清空 LOG_FILE，確保開頭乾淨 + 後續 pip/mutmut 錯誤訊息能保留。
: > "${LOG_FILE}"

echo "[run_mutmut_in_docker] $(date -u +%FT%TZ) module=${MODULE_PATH} tests=${TESTS_DIR}" | tee -a "${LOG_FILE}"

# 1) 安裝依賴：dev + postgres + pgvector + lint extras + 指定版本 mutmut（鎖 2.4.3 對齊 ADR-SD08-002 § runner spec）
#    SD_Improving_09 觀察期 #3：mutmut 2.4.3 的 pytest baseline 會 collect 整個 tests/
#    （--tests-dir 只影響「執行」哪些測試，不限制 collection 範圍 / conftest 仍 recursive 掃 tests/）。
#    若僅裝 [dev]，tests/infra/test_dual_state_repository_pg_fallback.py 會因 import sqlalchemy 失敗，
#    導致 ERROR collecting → mutmut baseline 直接 abort，無法產出真實 mutant 統計。
#    故需安裝所有 import 相依的 extras：dev / postgres / pgvector / lint。
#    notifications extras 含 win10toast（Windows only），且 nightly Docker 為 Linux 不需要，故省略。
# P1-R62-7 修復（2026-06-13，紀律 #18 — mutation 隔離樹）：
# mutmut 2.4.3 會「就地改寫」--paths-to-mutate 的真實源碼檔（變異→測→還原）。
# volume-mount 下這會突變主機工作樹：與主機並行 pytest / audit 互踩產生假紅，
# mutmut 中途被 kill 時變異源碼更可能殘留磁碟。
# 修法：把源碼 tar 複製到 container 內 ephemeral 隔離樹 /tmp/mutwork，
# editable install + mutmut 全程在隔離樹執行；輸出物（log / backlog / cache）
# 仍寫回 /workspace 維持 nightly 取證鏈相容。主機樹全程零寫入。
MUTWORK=/tmp/mutwork
rm -rf "${MUTWORK}"
mkdir -p "${MUTWORK}"
tar -C /workspace \
  --exclude=.git --exclude=logs --exclude=backups --exclude=checkpoints \
  --exclude=.pytest_cache --exclude=.mutmut-cache --exclude='__pycache__' \
  -cf - . | tar -C "${MUTWORK}" -xf -
TAR_RC=$?
if [ "${TAR_RC}" -ne 0 ]; then
  echo "[run_mutmut_in_docker] 隔離樹複製失敗 exit=${TAR_RC}" | tee -a "${LOG_FILE}"
  exit "${TAR_RC}"
fi
cd "${MUTWORK}" || exit 5
echo "[run_mutmut_in_docker] isolated worktree ready: ${MUTWORK}（主機樹零就地突變，紀律 #18）" | tee -a "${LOG_FILE}"

# editable install 必須指向隔離樹（否則 mutmut 突變 /tmp/mutwork 而 pytest
# import /workspace 版 → 全 survived 假象）
pip install --quiet -e ".[dev,postgres,pgvector,lint]" "mutmut==2.4.3"
PIP_EXIT=$?
if [ "${PIP_EXIT}" -ne 0 ]; then
  echo "[run_mutmut_in_docker] pip install 失敗 exit=${PIP_EXIT}" | tee -a "${LOG_FILE}"
  exit "${PIP_EXIT}"
fi

# 2) 確認 mutmut 真的可用
if ! command -v mutmut >/dev/null 2>&1; then
  echo "[run_mutmut_in_docker] mutmut 安裝後仍找不到 — 強制失敗" | tee -a "${LOG_FILE}"
  exit 2
fi

# 2.5) SD_09 W2 nightly audit P2-A 修復：版本守門（紀律 #1）
#      pip 雖鎖 2.4.3，但實際安裝可能被環境/cache 影響取到其他版本；
#      bitmask exit code 語意（bit0=exception）僅在 2.4.x 確認 → 必須驗版本。
#      注意：mutmut 2.4.3 用 subcommand `mutmut version`（無 `--version` flag，落入 help fallback）
INSTALLED_VER=$(mutmut version 2>&1 | head -1)
echo "[run_mutmut_in_docker] mutmut version check: ${INSTALLED_VER}" | tee -a "${LOG_FILE}"
if ! echo "${INSTALLED_VER}" | grep -q '2\.4\.3'; then
  echo "[run_mutmut_in_docker] expected mutmut 2.4.3 but got: ${INSTALLED_VER}" | tee -a "${LOG_FILE}"
  exit 4
fi
# TD-N02 修復（2026-06-12）：版本檢查通過後寫入明確版本標記行（進 LOG_FILE）。
# validate_mutmut_log.py --require-version-marker 據此驗證「log 來自版本守門通過的 run」，
# 防止格式漂移（mutmut 換版）下統計 regex 誤判仍假 pass。
echo "[run_mutmut_in_docker] mutmut version OK: 2.4.3" | tee -a "${LOG_FILE}"

# 3) 跑 mutmut（mutant 全 survived / 部分 failed 都允許繼續，後續 baseline_lock 會判斷）
#    -p no:xdist 已知為 pytest 選項；mutmut 2.x 不支援 → 不傳；若需傳給 runner 走 --runner。
#    SD_Improving_09 觀察期 #3：用 --runner 自訂 pytest command，明確指定 token_guard 測試目錄
#    並 override pyproject.toml [tool.pytest.ini_options] testpaths = ["tests"]，避免 baseline 收 1800
#    個測試（其中含 tests/test_gap014_020.py 依賴 Linux 環境不存在的 `claude` CLI → 假 baseline 失敗）。
#    --rootdir 強制 pytest 不去 inspect 上層 conftest；-c /dev/null 略過 pyproject.toml 的 testpaths。
#    -x 第一個 fail 立即停（baseline 預期 100% pass），與 mutmut 預設語意一致。
# SD_09 W0 二次 audit P0-A 修復：強制 fresh baseline
# SD_09 W2 audit P0-AUDIT-02 修復：同步清掉 .pytest_cache（紀律 #7）
# 移除舊 .mutmut-cache / .pytest_cache 避免：
#   (a) baseline crash → results 從過期 cache 撈舊資料 → 假 pass
#   (b) pytest fixture cache 殘留前次假象
# 隔離樹（cwd=/tmp/mutwork）為全新複本本就無 cache；/workspace 殘留 cache 一併清，
# 確保後續 cp 回寫的 cache 是本次 fresh run 的單一真相
rm -rf "${MUTWORK}/.mutmut-cache" "${MUTWORK}/.pytest_cache" /workspace/.mutmut-cache /workspace/.pytest_cache
echo "[run_mutmut_in_docker] cache cleared (.mutmut-cache + .pytest_cache) — forcing fresh baseline" | tee -a "${LOG_FILE}"

RUNNER_CMD="python -m pytest -x --rootdir=${TESTS_DIR} -c /dev/null ${TESTS_DIR}"
echo "[run_mutmut_in_docker] runner: ${RUNNER_CMD}"
mutmut run \
  --paths-to-mutate="${MODULE_PATH}" \
  --tests-dir="${TESTS_DIR}" \
  --runner="${RUNNER_CMD}" \
  --no-progress
MUTMUT_RC=$?
echo "[run_mutmut_in_docker] mutmut run exit=${MUTMUT_RC}"

# SD_09 W1 QA #4：bitmask 判定改委派至 tools/mutmut_exit_code.py（SSOT，有完整單元測試）。
#   bit 0 (1) = exception / baseline crash（**真 fail**）
#   bit 1 (2) = surviving mutants > 0（**預期狀態**，mutation pilot 就是要看 survived）
#   bit 2 (4) = surviving mutants timeout > 0（容忍）
#   bit 3 (8) = suspicious mutants > 0（容忍）
# CLI 退出碼：0=正常結束 / 1=real_fail（bit0=1）
python3 /workspace/tools/mutmut_exit_code.py classify "${MUTMUT_RC}" >/dev/null
EXIT_CLASSIFY_RC=$?
if [ "${EXIT_CLASSIFY_RC}" -eq 0 ]; then
  MUTMUT_OK=1
else
  MUTMUT_OK=0
fi

# 4) 從 mutmut cache (sqlite 單檔) 取得完整 counts → 寫入 log header
#    SD_09 W0 第三次 audit P0-G 修復：`mutmut results` 預設只列 Survived 區段，
#    缺 Killed N → mutation_baseline_lock 算 kill_rate=0%。
#    cache 結構：單檔 sqlite，表 Mutant(id, line, index, tested_against_hash, status)
#    status 值：ok_killed / bad_survived / bad_timeout / ok_suspicious / skipped
echo "[run_mutmut_in_docker] querying mutmut cache for full counts..."
python3 - >"${LOG_FILE}.header" 2>"${LOG_FILE}.headerr" <<'PYEOF'
import sqlite3, os, sys
path = "/tmp/mutwork/.mutmut-cache"  # P1-R62-7：cache 在隔離樹（紀律 #18）
if not os.path.exists(path) or not os.path.isfile(path):
    sys.stderr.write(f"cache file not found: {path}\n")
    sys.exit(1)
try:
    conn = sqlite3.connect(path)
    cur = conn.execute("SELECT status, COUNT(*) FROM Mutant GROUP BY status")
    counts = dict(cur.fetchall())
except Exception as e:
    sys.stderr.write(f"cache query failed: {e}\n")
    sys.exit(1)
# mutmut status → 標準 label（baseline_lock regex 認 `Killed (N)` 等）
label_map = [
    ("ok_killed", "Killed"),
    ("bad_survived", "Survived"),
    ("bad_timeout", "Timeout"),
    ("ok_suspicious", "Suspicious"),
    ("skipped", "Skipped"),
]
for status_key, label in label_map:
    n = counts.get(status_key, 0)
    print(f"{label} ({n})")
PYEOF
HEADER_RC=$?
# SD_09 W2 audit P0-AUDIT-01 修復：改 `>>` append（保留前段 pip/cache 訊息）
# SD_09 W2 audit P0-AUDIT-04 修復：明確 marker（`--- mutmut full counts ---`），
#   baseline_lock 必須認 marker 之後 5 行為單一真相（不再「取最後一筆」）。
{
  echo ""
  echo "--- mutmut results raw (begin) ---"
  # 先寫 mutmut results raw（保留 mutmut 原始 Survived 🙁 (N) + dash range 區段）
  # 讓 mutation_analysis.py 能正確 parse 第一個 Survived block 取出 mutant id。
  mutmut results 2>&1
  echo "--- mutmut results raw (end) ---"
  echo ""
  # 末尾追加完整 counts header — baseline_lock / mutation_analysis 必須認 marker 後 5 行為單一真相
  echo "--- mutmut full counts (from cache; SD_09 P0-G) ---"
  if [ "${HEADER_RC}" -eq 0 ] && [ -s "${LOG_FILE}.header" ]; then
    cat "${LOG_FILE}.header"
  else
    echo "[warn] cache query failed (rc=${HEADER_RC}); 詳見 ${LOG_FILE}.headerr"
    [ -s "${LOG_FILE}.headerr" ] && cat "${LOG_FILE}.headerr"
  fi
  echo "--- mutmut full counts (end) ---"
} >> "${LOG_FILE}"
RESULTS_RC=$?
# SD_09 W2 audit P1-AUDIT-20 修復：保留中介檔至 debug 目錄方便回查
# 不在此清除中介檔；nightly cleanup 階段或下次 fresh baseline 時統一處理
echo "[run_mutmut_in_docker] log written exit=${RESULTS_RC} log_bytes=$(wc -c < "${LOG_FILE}" 2>/dev/null || echo 0)" | tee -a "${LOG_FILE}"

# 4.5) SD_09 W2 nightly audit P0-2 修復（紀律 #1 / #9）：
#      原 PS host 上跑 mutation_analysis.py → mutmut 不可用（Windows / issue #397）→
#      show_mutation_diff() subprocess.run(["mutmut", "show", ...]) FileNotFoundError → diff=""
#      → classify_diff 全進 "other" → backlog 全 38 個 mutation 都被分類 "other"。
#      改：在 container 內（mutmut 可用）跑 mutation_analysis.py，產出真實分類 backlog。
echo "[run_mutmut_in_docker] running mutation_analysis.py inside container (P0-2 fix)..."
# cwd=/tmp/mutwork（mutmut show 需要 cwd 有 .mutmut-cache）；LOG_FILE 已為絕對路徑
python3 /workspace/tools/mutation_analysis.py token_guard \
  --log "${LOG_FILE}" \
  --output /workspace/mutation_backlog_token_guard.md
ANALYSIS_RC=$?
echo "[run_mutmut_in_docker] mutation_analysis exit=${ANALYSIS_RC}" | tee -a "${LOG_FILE}"

# 4.6) P1-R62-7：把隔離樹 cache 複製回 /workspace（保留既有「cache 可回查」行為；
#      主機樹源碼全程未被觸碰，僅新增此 artifact）
if [ -f "${MUTWORK}/.mutmut-cache" ]; then
  cp "${MUTWORK}/.mutmut-cache" /workspace/.mutmut-cache
  echo "[run_mutmut_in_docker] .mutmut-cache copied back to /workspace（取證可回查）" | tee -a "${LOG_FILE}"
fi

# 5) stage exit code 決策
if [ ! -s "${LOG_FILE}" ]; then
  echo "[run_mutmut_in_docker] log 為空 — 標記 stage 失敗"
  exit 3
fi
if [ "${MUTMUT_OK}" -ne 1 ]; then
  echo "[run_mutmut_in_docker] mutmut 真實失敗 exit=${MUTMUT_RC}（bit0=exception/baseline-crash）— 標記 stage 失敗"
  exit "${MUTMUT_RC}"
fi
echo "[run_mutmut_in_docker] mutmut 正常結束 exit=${MUTMUT_RC}（bit0=0，survived/timeout/suspicious 為觀察期預期）"
exit 0
