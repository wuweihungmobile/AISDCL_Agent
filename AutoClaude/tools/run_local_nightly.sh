#!/usr/bin/env bash
# run_local_nightly.sh — macOS 本機 nightly 薄聚合器（R11 Architect D1 拍板案）。
#
# 定位：launchd/cron 載體（ONBOARDING.md §8 launchd 範本對應）。只「串接既有
# 驗證腳本」，不重寫任何檢查。與 Windows 版 run_local_nightly.ps1（深度 7-stage：
# local_ci_gate/mutation/pg-e2e/perf/drift/obs/sdd-fsm-chaos）**語意刻意不同**——
# mac 側只要「平台相容性＋回歸」的每日訊號，深度 stage（mutation Docker/pg-e2e/
# perf/obs）留在 Windows 主開發機承載；不移植 929 行 .ps1（避免第二支巨型雙實作）。
# 七軌去向帳目補齊（R11 ARCH-1）：其餘兩軌——drift＝nightly 取證帳本紀律由 Windows
# 主開發機承載（🔴 R76 訂正：原文寫「drift_log_history 例行 commit 即其產物」已成假話——
# 該帳本自 R76 起與另四本觀察期帳本對齊，列入 AutoClaude/.gitignore 且已 git rm --cached，
# 理由見 AutoClaude/tools/drift_log_snapshot.py 檔頭：被 git 追蹤時，git checkout -- . ／
# stash ／reset --hard ／worktree 切換會靜默回捲進帳，已實測損失一整天）；sdd-fsm-chaos＝非平台敏感
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
# log（R15 DEF-101-201②）：RunId log——開頭將輸出 exec 改道
# AutoClaude/logs/nightly_mac_<時間戳>.log（BEGIN 首行帶 run_id，鏡射 .ps1 RunId 語意；
# 保留 14 天，心跳寫完後 find -mtime +14 輪替）。launchd log
#（nightly_mac_launchd.{log,err}）輪替**明確不做**：輸出改道後只剩 exec 前的啟動
# 錯誤，自限量（ARCH-R14-REV-2 結案理由）。互動終端機（`[ -t 1 ]`）手動執行時改走
# tee 雙寫，保留即時終端機輸出（ARCH-R15-REV-2 訂正：純 exec 改道會讓手動執行時
# 終端機零輸出，是未被評估的行為回歸）。
# 補跑（R15 SCAN-C-1）：plist 加 RunAtLoad 後，開機/載入亦觸發本腳本——以「心跳檔
# mtime 當日去重」保證每日至多完整跑一輪（等價 Windows StartWhenAvailable 補跑
# 語意）；手動重跑以 --force 繞過去重。**去重判斷置於 RunId log exec 改道之前**
#（ARCH-R15-REV-1 訂正：原順序下每次被去重跳過的 RunAtLoad 觸發都會留下一份僅含
# BEGIN+跳過訊息的殘留 RunId log——本機曾真實產生 nightly_mac_20260720_183245.log
# 等殘骸為證；去重時直出 stdout，由 launchd StandardOutPath／終端機自行承接）。
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

# launchd job Label（R67-F26）：必須與 tools/install_mac_nightly.sh 的 LABEL 同值
# ——它是下面觸發來源判定的比對基準，兩邊漂移會讓真排程觸發被誤標成「手動」。
# 跨檔字面一致性由 AutoClaude/tests/tools/test_run_local_nightly_sh_static.py 鎖住。
NIGHTLY_LAUNCHD_LABEL="com.autoclaude.nightly"

# 參數解析（R67-F10）：**必須在任何副作用之前**——`--help` 要真的什麼都不做。
# WHY：修復前全檔只對 $1 做兩處 `= "--force"` 二元比對，於是 `--help` 在無心跳的
# 樹上會直接開跑整套 4-stage（實測落下 nightly_mac_*.log 並跑進 macos_smoke 的
# 7 個子步驟），有心跳時則 rc=0 印「今日已有心跳…跳過本輪」——一個查說明的動作
# 被記成一次成功的 nightly 去重，事後從 log 看不出使用者其實輸錯了旗標。
# `--forse`／`-f`／`--Force` 等 typo 同樣全被吞掉（實測七種變體 rc 皆為 0）。
print_usage() {
  cat <<EOF
用法：bash AutoClaude/tools/run_local_nightly.sh [--force | -h | --help]

  （無參數）   排程/去重模式：當日已有心跳即跳過（RunAtLoad 補跑去重），否則跑完整 ${STAGE_TOTAL} stage
  --force      手動重跑：繞過當日去重
  -h, --help   印本說明後結束，不執行任何 stage

stage：[1/${STAGE_TOTAL}] macos_smoke ／ [2/${STAGE_TOTAL}] root_unittests ／ [3/${STAGE_TOTAL}] autoclaude_gate ／ [4/${STAGE_TOTAL}] sdd_ci_gate
log：AutoClaude/logs/nightly_mac_<時間戳>.log（保留 14 天）
心跳：AutoClaude/logs/nightly_mac_latest.log
EOF
}
if [ "$#" -gt 1 ]; then
  echo "❌ 參數過多（本腳本最多接受一個旗標）：$*" >&2
  print_usage >&2
  exit 2
fi
case "${1:-}" in
  "") : ;;
  --force) : ;;
  -h|--help) print_usage; exit 0 ;;
  *)
    echo "❌ 未知參數：$1" >&2
    print_usage >&2
    exit 2
    ;;
esac

# 觸發來源判定（R16 SCAN-C-3）：BEGIN 行需可歸因本輪是 launchd 排程觸發還是
# 手動/--force 呼叫，未來再遇到「同日兩輪 PASS」才能機械判讀是合理的手動重跑
# 還是真正的去重漏洞（R16 掃描時，2026-07-21 同日兩輪完整 PASS=4 因缺這行
# 無法單靠 log 本身歸因）。--force 與互動終端（[ -t 1 ]）進一步區分手動重跑樣態。
#
# 🔴 R67-F26 訂正：本段原註解宣稱「XPC_SERVICE_NAME 是 launchd 注入其管理 job 的
# 慣例環境變數，**手動終端呼叫不具備**」，判定式因此只用 `[ -n ... ]` 測存在性。
# 真機實測（Darwin 25.5.0）證偽：macOS 對一般使用者行程注入的值就是字串 `0`
# （`/bin/bash -c 'echo ${XPC_SERVICE_NAME}'` → `0`），於是任何手動/agent/CI 呼叫
# 都被標成 `launchd(...)`，而 manual-interactive／non-interactive-unknown 兩態成為
# 死碼——正好在這個欄位唯一被設計來服務的取證情境（同日兩輪 PASS 的歸因）給出
# 反向結論：去重漏洞會被記成「排程觸發」，指向無辜的 launchd。
# 真 launchd 注入的值是 **job Label**（本機 7 份真排程 log 逐份為
# `XPC_SERVICE_NAME=com.autoclaude.nightly`），故改為值比對而非存在性比對。
if [ "${1:-}" = "--force" ]; then
  TRIGGER_SRC="manual-force"
elif [ "${XPC_SERVICE_NAME:-}" = "${NIGHTLY_LAUNCHD_LABEL}" ]; then
  TRIGGER_SRC="launchd(XPC_SERVICE_NAME=${XPC_SERVICE_NAME})"
elif [ -t 1 ]; then
  TRIGGER_SRC="manual-interactive"
else
  TRIGGER_SRC="non-interactive-unknown"
fi

# 去重鎖（R16 SCAN-C-2）：下面的心跳 mtime 判斷本身是 check-then-act，若 launchd
# 的 RunAtLoad 與 StartCalendarInterval(02:00) 兩個觸發源、或手動重跑與排程觸發
# 時間點重疊，兩個行程可能同時通過「今日尚未有心跳」的檢查，導致重複跑一整套
# 4-stage gate。本機查無 `flock`（GNU 專屬，macOS 無此指令）；`shlock` 雖存在
# 但非所有 macOS 版本保證都有，改用最保險的 POSIX `mkdir` atomic lock pattern
# （同一路徑下 mkdir 建立目錄具原子性，兩個行程不可能同時成功）。陳舊鎖清除
# 比照 tools/dev_start.py `_acquire_bootstrap_lock()` 慣例：以鎖檔內 PID 是否
# 仍存活判斷（而非固定逾時秒數）——4-stage gate 本身執行時間會變動，固定逾時
# 容易誤殺仍在跑的合法行程。
NIGHTLY_LOCK_DIR="${ROOT}/AutoClaude/logs/.nightly_mac.lock"
_nightly_lock_release() {
  rm -f "${NIGHTLY_LOCK_DIR}/pid" 2>/dev/null
  rmdir "${NIGHTLY_LOCK_DIR}" 2>/dev/null
}
_nightly_lock_acquire() {
  mkdir -p "${ROOT}/AutoClaude/logs" 2>/dev/null
  _attempt=1
  while [ "${_attempt}" -le 2 ]; do
    if mkdir "${NIGHTLY_LOCK_DIR}" 2>/dev/null; then
      echo "$$" > "${NIGHTLY_LOCK_DIR}/pid" 2>/dev/null || true
      return 0
    fi
    _lock_pid="$(cat "${NIGHTLY_LOCK_DIR}/pid" 2>/dev/null || true)"
    if [ -n "${_lock_pid}" ] && kill -0 "${_lock_pid}" 2>/dev/null; then
      return 1  # 另一行程仍存活，真的忙碌
    fi
    # 陳舊鎖（pid 檔缺失、內容非法或行程已死）：清除後重試一次
    rm -f "${NIGHTLY_LOCK_DIR}/pid" 2>/dev/null
    rmdir "${NIGHTLY_LOCK_DIR}" 2>/dev/null
    _attempt=$((_attempt + 1))
  done
  return 1
}
if ! _nightly_lock_acquire; then
  echo "另一個 nightly 行程持有去重鎖（${NIGHTLY_LOCK_DIR}）——本輪跳過，避免 launchd 多觸發源或手動重跑時間重疊造成重複執行整套 gate（觸發來源：${TRIGGER_SRC}）"
  exit 0
fi
trap _nightly_lock_release EXIT

# 當日去重（R15 SCAN-C-1；ARCH-R15-REV-1 訂正：判斷提前至 RunId log exec 改道之前
# ——原順序下每次去重跳過都會留下一份僅含 BEGIN+跳過訊息的殘留 RunId log）：
# launchd 呼叫載體為 `/bin/bash <本腳本>` 無參數——排程路徑（StartCalendarInterval
# 02:00 與 RunAtLoad 補跑）永遠走本去重。心跳檔 mtime 日期（BSD stat）等於今日＝
# 當日已完整跑過一輪 → 跳過（直出 stdout，無 RunId log 副作用；launchd 呼叫時由
# StandardOutPath／nightly_mac_launchd.log 兜底承接），使 RunAtLoad 語意成為
#「載入時若今日尚未跑過才補跑」，冪等重裝/多次開機不重複跑；stat 失敗視為無心跳
# 照常執行；手動重跑：--force 繞過。R16 SCAN-C-2 起本檢查已受上方去重鎖保護，
# 不再有 TOCTOU 窗口。
HB_FILE="${ROOT}/AutoClaude/logs/nightly_mac_latest.log"
if [ "${1:-}" != "--force" ] && [ -f "${HB_FILE}" ]; then
  _hb_day="$(stat -f %Sm -t %Y-%m-%d "${HB_FILE}" 2>/dev/null || true)"
  if [ -n "${_hb_day}" ] && [ "${_hb_day}" = "$(date +%Y-%m-%d)" ]; then
    echo "今日已有心跳（${_hb_day}）——RunAtLoad 補跑去重，跳過本輪（手動重跑：--force）"
    exit 0
  fi
fi

# RunId log（R15 DEF-101-201②，Architect 設計）：心跳檔＝「最新一輪」指標、RunId log
# ＝當輪完整實體（取證紀律 #3「PASS 聲稱引 RunId log:L」自此可在 mac 履行）。
# 互動終端機（ARCH-R15-REV-2 訂正）：tee 雙寫，保留手動執行時的即時終端機輸出；
# 非互動（launchd/排程）：純 exec 改道，避免額外 tee 行程。mkdir 失敗 → 不 exec、
# 照舊直出 stdout 並印警告（launchd StandardOutPath 兜底），不改 exit 語意。
# 已知限制（ARCH-R15-RR-1，R15 複審觀察）：tee 是腳本的子行程，本腳本 exit 時不
# `wait` 它——理論上存在「腳本已回報 exit code、tee 尚未 flush 最後幾行進 RUN_LOG」
# 的競態窗口（170 次真機壓力測試 0 次重現，見複審記錄；心跳檔走獨立同步寫入不經
# tee，三站點契約不受影響；RunId log 定位人工/audit 事後取證，非即時機器解析）。
RUN_TS="$(date +%Y%m%d_%H%M%S)"
RUN_LOG="${ROOT}/AutoClaude/logs/nightly_mac_${RUN_TS}.log"
if mkdir -p "${ROOT}/AutoClaude/logs" 2>/dev/null; then
  if [ -t 1 ]; then
    exec > >(tee -a "${RUN_LOG}") 2>&1
  else
    exec >> "${RUN_LOG}" 2>&1
  fi
  printf 'BEGIN nightly_mac run_id=%s trigger=%s log=%s\n' "${RUN_TS}" "${TRIGGER_SRC}" "${RUN_LOG}"
else
  echo "⚠️ logs 目錄建立失敗——RunId log 停用，輸出照舊直出 stdout（launchd log 兜底）：${ROOT}/AutoClaude/logs" >&2
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
# DEF-101-506：本檔的直譯器**已**釘成絕對路徑（不靠 PATH 現場解析，故無 Windows
# 側「誰啟動就用誰的 python」問題），但先前同樣沒把它印進 log——事後無從指認。
# 補印解析結果，與 .ps1 側取證對稱（紀律 #14 延伸）。
printf 'python 直譯器：%s [v%s]\n' "$PY" "$("$PY" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null)"

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

# 心跳檔（R12 ARCH-R12-2）：launchd/cron 是否真的在跑過去零機械查核（DEF-101-164
# ARCH-8），CI 停擺（DEF-101-081）期間本地 nightly 是唯一每日兜底層。成功與失敗
# 路徑皆寫（tools/dev_start.py step_platform 讀 mtime 做 advisory 三態哨兵）。
# logs/ 已 gitignored（AutoClaude/.gitignore）；寫入失敗絕不改變 nightly exit 語意。
write_heartbeat() {
  _hb_dir="${ROOT}/AutoClaude/logs"
  _hb_file="${_hb_dir}/nightly_mac_latest.log"
  if mkdir -p "${_hb_dir}" 2>/dev/null; then
    {
      # 🔴 前 2 行格式為三站點契約（dev_start.py mtime 讀取／install_mac_nightly.sh
      # --status／本函式寫入），絕不可變；彙總行之後（FAIL>0 時多一行失敗 stage）
      # 附 log= 末行指標（R15 DEF-101-201②：心跳＝指標、RunId log＝實體；SA-R15-REV-1
      # 訂正：FAIL=0 常態時 log= 落在第 3 行、非固定第 4 行）。
      printf 'nightly_mac heartbeat（UTC）：%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      printf '===== nightly 彙總：PASS=%s FAIL=%s =====\n' "${PASS}" "${FAIL}"
      if [ "${FAIL}" -gt 0 ]; then printf '失敗 stage：%s\n' "${FAIL_NAMES}"; fi
      printf 'log=%s\n' "${RUN_LOG}"
    } > "${_hb_file}" 2>/dev/null || echo "⚠️ 心跳檔寫入失敗（不影響 nightly exit 語意）：${_hb_file}" >&2
  else
    echo "⚠️ 心跳目錄建立失敗（不影響 nightly exit 語意）：${_hb_dir}" >&2
  fi
}

run_stage 1 macos_smoke     /bin/bash "$ROOT/tools/macos_smoke_local.sh"
run_stage 2 root_unittests  "$PY" "$ROOT/tools/run_root_unittests.py"
run_stage 3 autoclaude_gate bash "$ROOT/AutoClaude/tools/local_ci_gate.sh"
run_stage 4 sdd_ci_gate     sdd_gate

printf '\n===== nightly 彙總：PASS=%s FAIL=%s =====\n' "$PASS" "$FAIL"
write_heartbeat
# RunId log 輪替（R15）：保留 14 天；pattern 只掃 nightly_mac_2*.log（時間戳家族），
# 絕不觸及 nightly_mac_latest.log（心跳）與 nightly_mac_launchd.{log,err}（launchd
# 兜底，依 ARCH-R14-REV-2 明確不輪替）；BSD find 相容；失敗不改 exit 語意。
find "${ROOT}/AutoClaude/logs" -name 'nightly_mac_2*.log' -mtime +14 -delete 2>/dev/null || true
if [ "$FAIL" -gt 0 ]; then
  echo "失敗 stage：$FAIL_NAMES" >&2
  exit 1
fi
exit 0
