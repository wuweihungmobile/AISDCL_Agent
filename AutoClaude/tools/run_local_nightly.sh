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
#   [1/5] macos_smoke     — /bin/bash 強制系統 bash 3.2（平台相容性聚合驗證）
#   [2/5] root_unittests  — 根層 tools/tests unittest 全套（含測試數量下限釘選）
#   [3/5] autoclaude_gate — AutoClaude tools/local_ci_gate.sh（鏡像 CI push gating；
#                           顯式帶 --unattended——GitHub Actions 靠 GITHUB_ACTIONS
#                           環境變數自動判定 unattended，本檔排程執行無此變數，
#                           須顯式帶旗標才是真鏡像，DEF-200-314）
#                           stage 前後另有 PG 子步驟（**不是** stage、不計入分母；DEF-200-075）：
#                           docker daemon 可達 ⇒ 起 CI 對等 PG＋migrate、stage 後收容器（剖面＝+pg）；
#                           不可達但 Docker.app 在 ⇒ 本腳本 `open -a` 開它、stage 後只收自己開的（D2 護欄）；
#                           仍不可達 ⇒ 大聲退回 +nopg 剖面（見下方〈PG 接線〉段）
#   [4/5] sdd_ci_gate     — AISDLC_SDD scripts/ci-gate.sh（凍結基線 + LATEST 雙軌）
#   [5/5] nightly_anchor  — tools/refresh_nightly_anchor.py --write：gh 現查兩支排程通道
#                           最近一次 completed run 的 job 層結論，機械回填 ONBOARDING §7
#                           表③-b 與錨的 nightly 三欄（寫回工作樹、須隨下一個 commit 收；
#                           DEF-200-506）。排最後：樣本效度戳記在所有 stage 之前取完，
#                           寫回不汙染本輪樣本。
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

STAGE_TOTAL=5  # stage 分母單一定義點（R11 P4：原 /4 硬編三處，增刪 stage 易漏改）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# WHY：launchd/cron 環境的 PATH 極簡（通常僅 /usr/bin:/bin:/usr/sbin:/sbin），
# 而 stage 3/4 的閘門腳本內部以裸 `python` 呼叫 venv 工具——.venv/bin 必須先
# prepend 進 PATH，否則排程執行時必在 venv 守門處 fail。
if [ -d "$ROOT/.venv/bin" ]; then
  PATH="$ROOT/.venv/bin:$PATH"; export PATH
fi

# WHY：launchd 極簡 PATH 也缺 Homebrew bin ⇒ 需要 pwsh 的 tools/tests 測試從 platform 語意的
# skip 落成 untagged／debt 語意，撞 skip 天花板（DEF-200-314）。兩種 Homebrew 前綴都做存在性
# 探測、不寫死單一架構（鐵律三：Apple Silicon=/opt/homebrew、Intel=/usr/local）；不可用
# `brew --prefix`——極簡 PATH 下 brew 本身可能解析不到。🔴 刻意 append 到尾端：只為讓
# pwsh 可解析，`.venv/bin` 必須維持最前（單一 .venv 原則）——往前插會把 Homebrew 排到
# `.venv/bin` 前面，若 Homebrew 目錄裡剛好有裸 `python`／`python3` 就會蓋掉單一 .venv
# 這條鐵律（本機未炸純屬僥倖：Homebrew 目錄當下無裸 python）。
for _hb_bin in /opt/homebrew/bin /opt/homebrew/sbin /usr/local/bin; do
  if [ -d "${_hb_bin}" ]; then
    case ":${PATH}:" in
      *":${_hb_bin}:"*) ;;
      *) PATH="${PATH}:${_hb_bin}" ;;
    esac
  fi
done
export PATH

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

stage：[1/${STAGE_TOTAL}] macos_smoke ／ [2/${STAGE_TOTAL}] root_unittests ／ [3/${STAGE_TOTAL}] autoclaude_gate ／ [4/${STAGE_TOTAL}] sdd_ci_gate ／ [5/${STAGE_TOTAL}] nightly_anchor
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

# ── PG 接線（DEF-200-075）：stage 3 的 AutoClaude 全套需要一顆**已 migrate** 的 CI 對等 PG ──
#
# WHY：mac nightly 此前一律落在 `+nopg` 剖面（census 的欠債型整批掛在 untagged）——沒人起容器，PG 那一族測試
# 整批 skip，nightly 對 DAL 三後端／alembic 鏈的每日回歸訊號是空的。本段把「起 PG ＋ 等 healthy ＋
# migrate」搬進 nightly 自己；stage 3 一結束就收容器（stage 4／5 不需要 PG）。
# 🔴 憑證是 stage 3 輸出裡的 `[PG autodetect] 已注入…` 與 `[skip census] …@darwin+pg+…`，不是容器
# healthy（容器是 tmpfs，healthy ≠ 已 migrate；根 CLAUDE.md〈容器 healthy ≠ DB 已 migrate〉）。
# 🔴 半夜自動開 Docker Desktop＝掌舵者裁決 D2（2026-10-13，主控依授權代決，可隨時以 T1 推翻）。此前（DEV-PG）
# 刻意不開：Docker Desktop 是使用者的桌面 app（~1GB 常駐；冷啟動可能彈授權／更新對話框；收掉它會殃及
# 使用者自己的容器）——所以只在有護欄時才開，逐條對應 `nightly_docker_up`／`nightly_docker_down`：
#   ① 僅 `${NIGHTLY_DOCKER_APP}`（預設 /Applications/Docker.app）存在、且 `docker info`（有界 20s）不可達
#      才 `open -a`，並記 NIGHTLY_DOCKER_STARTED=1；
#   ② 之後輪詢 `docker info` 最長 150s，逾時＝大聲退回 +nopg（不 kill、不收：卡在授權／更新對話框的 app
#      留給人看，NIGHTLY_DOCKER_STARTED 歸零）；
#   ③ **只收自己開的**，且 stage 3 結束就收（不等 stage 4——SDD ci-gate 的 docker 後端測試會因 Docker
#      還開著而改走真容器）；收法＝先 `quit app "Docker"` 再 `quit app "Docker Desktop"`（只送前者 rc=0
#      但沒關，2026-09-19 實測），再有界輪詢 `pgrep -f Docker.app` 為空才算收完（com.docker.build 約 40s
#      自退，不必 kill）；
#   ④ 收的動作掛在既有 EXIT trap（`_nightly_lock_release`，接在 `nightly_pg_down` 之後），不新增 trap；
#   ⑤ 使用者原本就開著（`docker info` 可達）⇒ 沿用、不收；
#   ⑥ `open -a` 失敗（launchd 沒有 GUI session 等）⇒ 同樣大聲退回 +nopg。
#   ⑦（本檔補的兩條，同「只收自己開的」精神，主控可否決）：開之前 Docker.app 行程已存在而 daemon 不可達
#      （使用者剛啟動／暫停／卡住；RunAtLoad 補跑撞上登入自啟尤其可能）⇒ 不算本腳本所開、不收；
#      要收時若還有「非本腳本的」運行中容器 ⇒ 不收（使用者可能已在用）。
# 任何分支都印一行 `[nightly][docker]`／`[nightly][pg]`，讓 RunId log 事後可判「哪一晚走了哪條路」；
# 一律**不**判 FAIL（PG 是機會性覆蓋），不改 PASS+FAIL＝STAGE_TOTAL 不變式。
# 🔴 DSN 刻意**不 export**：只以 `env VAR=…` 前綴交給 alembic 那一個行程。一旦 export，stage 3 的
# `pg_autodetect()` 會走「顯式優先」剎車而印「跳過：…已由使用者顯式設定」——PG 照樣接得上，但
# 「autodetect 這條路是通的」就驗不到了（ONBOARDING §7.1 第 ③ 步同一個理由）。
# 🔴 容器若**已在跑**（使用者手動起的、或前一輪沒收乾淨的）一律沿用、不收：不收別人起的東西。
# 🔴 `nightly_pg_down`、`nightly_docker_down` 同時掛在 EXIT trap（見 `_nightly_lock_release`）：行程被
# SIGTERM／SIGHUP 殺掉也會走到（bash 3.2.57 實測 EXIT trap 在這兩個訊號下都會執行）。SIGKILL／斷電無解——
# 容器會殘留，下一輪因「已在跑」而沿用、不收，手動收法：docker compose -f <本 compose 檔> down -v。
NIGHTLY_PG_COMPOSE="${ROOT}/AutoClaude/docker-compose.ci.yml"
NIGHTLY_PG_CONTAINER="autoclaude_ci_pg"  # 同 docker-compose.ci.yml 的 container_name
# 同 ONBOARDING §7.1 第 ③ 步的 DSN；alembic/env.py 對 +asyncpg 形自動 strip，與 local_ci_gate 的
# `_PG_DSN` 指的是同一顆 DB。
NIGHTLY_PG_DSN="postgresql://autoclaude:autoclaude@localhost:5432/autoclaude"
NIGHTLY_PG_STARTED=0  # 1＝容器是本腳本起的（才有權收）；沿用既有容器時維持 0
# 可由環境覆寫（沙箱測試把它指到不存在的路徑）；launchd plist 沒有 EnvironmentVariables，正式排程恆為預設值。
NIGHTLY_DOCKER_APP="${NIGHTLY_DOCKER_APP:-/Applications/Docker.app}"
NIGHTLY_DOCKER_STARTED=0  # 1＝Docker Desktop 是本腳本 open -a 開的（才有權 quit）；使用者原本就開著時維持 0

# 有界執行：$1=上限秒數 $2...=指令；超過上限即殺掉並回 124（比照 GNU 逾時指令的慣例碼）。
# WHY 自刻：macOS 沒有那支指令，且 tools/tests/test_bash32_compat.py 把它列為禁用（BSD 紀律）。
# 為什麼非有界不可：docker daemon 半死不活（Docker Desktop 啟動中／更新中）時 `docker info` 可以
# 掛住不回——nightly 無人看管，一個卡死的行程連同去重鎖會讓之後每一晚都被「另一個 nightly 行程持有
# 去重鎖」跳過（鎖的存活判斷看 pid，活著就不清）。
_nightly_bounded() {
  _nb_max="$1"; shift
  "$@" &
  _nb_pid=$!
  _nb_t=0
  while ps -p "${_nb_pid}" >/dev/null 2>&1; do
    if [ "${_nb_t}" -ge "${_nb_max}" ]; then
      pkill -P "${_nb_pid}" 2>/dev/null
      kill "${_nb_pid}" 2>/dev/null
      wait "${_nb_pid}" 2>/dev/null
      return 124
    fi
    sleep 1
    _nb_t=$((_nb_t + 1))
  done
  wait "${_nb_pid}"
}

nightly_pg_down() {  # 只收「本腳本起的」容器；冪等（EXIT trap 與正常路徑都會呼叫）
  [ "${NIGHTLY_PG_STARTED}" = "1" ] || return 0
  NIGHTLY_PG_STARTED=0
  if _nightly_bounded 120 docker compose -f "${NIGHTLY_PG_COMPOSE}" down -v; then
    echo "[nightly][pg] 已收容器（docker compose down -v）"
  else
    echo "[nightly][pg] ⚠️ docker compose down -v 失敗或逾時，容器可能殘留；手動收：docker compose -f ${NIGHTLY_PG_COMPOSE} down -v"
  fi
}

# 輪詢 `docker info`（每次有界 10s、間隔 3s）直到可達，或牆鐘時間超過 $1 秒：可達回 0、逾時回 1。
_nightly_docker_wait_ready() {
  _dw_t0="$(date +%s)"
  while [ $(( $(date +%s) - _dw_t0 )) -lt "$1" ]; do
    if _nightly_bounded 10 docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}

# 開 Docker Desktop（D2 護欄 ①②⑥⑦）：呼叫端已確認 daemon 不可達。daemon 等到了回 0，其餘回 1（原因已大聲印出）。
nightly_docker_up() {
  if [ ! -d "${NIGHTLY_DOCKER_APP}" ]; then
    echo "[nightly][docker] 找不到 ${NIGHTLY_DOCKER_APP} ⇒ 不嘗試 open -a"
    return 1
  fi
  _dk_t0="$(date +%s)"
  if pgrep -f 'Docker[.]app' >/dev/null 2>&1; then
    # 護欄 ⑦：app 行程已在（使用者剛啟動／暫停／卡住）只是 daemon 還不可達 ⇒ 不是本腳本開的，只等、不開、不收。
    echo "[nightly][docker] Docker.app 行程已存在但 daemon 不可達（啟動中／暫停／卡住）⇒ 不算本腳本所開、不收；只輪詢等 daemon（最長 150s）"
  else
    _nightly_bounded 30 open -g -a "${NIGHTLY_DOCKER_APP}"
    _dk_rc=$?
    if [ "${_dk_rc}" -ne 0 ]; then
      echo "[nightly][docker] open -a ${NIGHTLY_DOCKER_APP} 失敗 rc=${_dk_rc}（launchd 沒有 GUI session？）⇒ 沒開成、不收"
      return 1
    fi
    NIGHTLY_DOCKER_STARTED=1  # 先記帳再等：等待中被殺，EXIT trap 也要能把自己開的收掉
    echo "[nightly][docker] daemon 不可達 ⇒ 已 open -a ${NIGHTLY_DOCKER_APP}；輪詢等 daemon（最長 150s）"
  fi
  if _nightly_docker_wait_ready 150; then
    if [ "${NIGHTLY_DOCKER_STARTED}" = "1" ]; then
      echo "[nightly][docker] daemon 已可達（約 $(( $(date +%s) - _dk_t0 ))s）；Docker Desktop 是本腳本開的 ⇒ stage 3 後由本腳本收"
    else
      echo "[nightly][docker] daemon 已可達（約 $(( $(date +%s) - _dk_t0 ))s）；Docker Desktop 非本腳本所開 ⇒ stage 3 後不收"
    fi
    return 0
  fi
  NIGHTLY_DOCKER_STARTED=0  # 逾時＝狀態不明（可能卡在授權／更新對話框）：不 kill、不收，留給人看
  echo "[nightly][docker] 150s 內 docker info 仍不可達 ⇒ 不 kill、不收（請人工檢視 Docker Desktop 是否卡在對話框）"
  return 1
}

# 收 Docker Desktop（D2 護欄 ③④⑦）：只收 NIGHTLY_DOCKER_STARTED=1 的；冪等（正常路徑與 EXIT trap 都會呼叫）。
nightly_docker_down() {
  [ "${NIGHTLY_DOCKER_STARTED}" = "1" ] || return 0
  NIGHTLY_DOCKER_STARTED=0
  _dk_others="$(_nightly_bounded 20 docker ps --format '{{.Names}}' 2>/dev/null | grep -v -x "${NIGHTLY_PG_CONTAINER}")"
  if [ -n "${_dk_others}" ]; then
    echo "[nightly][docker] 仍有非本腳本的運行中容器（$(printf '%s' "${_dk_others}" | tr '\n' ' ')）⇒ 不收 Docker Desktop（使用者可能已在用）"
    return 0
  fi
  # 先讓 VM 內檔案系統落盤再 quit：剛 `down -v` 完立刻收 Docker，移除動作可能沒 commit 進虛擬磁碟，下次啟動容器
  # 會復活成壞掉的殼。sync(2) 是全核心的（任一容器內呼叫即 flush 整個 VM）；用 compose 檔裡的那個映像（剛用過，必在本機）。
  _dk_img="$(_nightly_bounded 20 docker compose -f "${NIGHTLY_PG_COMPOSE}" config --images 2>/dev/null | head -n 1)"
  if [ -n "${_dk_img}" ]; then
    if _nightly_bounded 60 docker run --rm --entrypoint sync "${_dk_img}" >/dev/null 2>&1; then
      echo "[nightly][docker] 已在 VM 內 sync（讓 down -v 的移除落盤後再 quit）"
    else
      echo "[nightly][docker] ⚠️ VM 內 sync 失敗；下次啟動可能有復活的殘容器（nightly_pg_up 會先清）"
    fi
  fi
  echo "[nightly][docker] 收 Docker Desktop：quit app \"Docker\" → quit app \"Docker Desktop\"（只送前者可能沒關）"
  _nightly_bounded 30 osascript -e 'quit app "Docker"'
  _dk_q1=$?
  _nightly_bounded 30 osascript -e 'quit app "Docker Desktop"'
  _dk_q2=$?
  _dk_t0="$(date +%s)"
  while pgrep -f 'Docker[.]app' >/dev/null 2>&1; do
    if [ $(( $(date +%s) - _dk_t0 )) -ge 120 ]; then
      echo "[nightly][docker] ⚠️ 120s 後 pgrep -f Docker.app 仍有行程（osascript rc=${_dk_q1}/${_dk_q2}）⇒ 沒收乾淨，請人工 quit Docker Desktop"
      return 0
    fi
    sleep 2
  done
  echo "[nightly][docker] 已收 Docker Desktop（pgrep -f Docker.app 為空；osascript rc=${_dk_q1}/${_dk_q2}；約 $(( $(date +%s) - _dk_t0 ))s）"
}

# 起 PG ＋ migrate；任何一步不成都只是「大聲退回 +nopg」，函式恆回 0（PG 是機會性覆蓋，不是 stage）。
nightly_pg_up() {
  if [ ! -f "${NIGHTLY_PG_COMPOSE}" ]; then
    echo "[nightly][pg] 找不到 ${NIGHTLY_PG_COMPOSE} ⇒ 本晚為 nopg 剖面（DEF-200-075）"
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "[nightly][pg] Docker 不可達（PATH 上沒有 docker）⇒ 本晚為 nopg 剖面（DEF-200-075）"
    return 0
  fi
  if _nightly_bounded 20 docker info >/dev/null 2>&1; then
    echo "[nightly][docker] daemon 已可達（非本腳本所開；多半是使用者原本就開著）⇒ 沿用，stage 3 後不收 Docker Desktop"
  elif nightly_docker_up; then
    :  # 開成功且 daemon 等到了（原因已由 nightly_docker_up 印出）
  else
    echo "[nightly][pg] Docker 不可達 ⇒ 本晚為 nopg 剖面（DEF-200-075）"
    return 0
  fi
  _pg_running="$(_nightly_bounded 20 docker ps -q --filter "name=^${NIGHTLY_PG_CONTAINER}\$" 2>/dev/null)"
  if [ -n "${_pg_running}" ]; then
    echo "[nightly][pg] 容器 ${NIGHTLY_PG_CONTAINER} 已在跑（非本腳本所起）⇒ 沿用，stage 結束不收"
  else
    # 殘留的「非運行中」同名容器要先清：`down -v` 後 Docker Desktop 被立刻收掉時，已移除的容器可能於下次啟動
    # 復活成壞掉的殼（Exited 128／RWLayer … is unexpectedly nil；2026-10-13 D2 實測），compose 會沿用它而 up 失敗。
    # 本容器是 tmpfs 拋棄式，直接 rm -f（只動這個名字，不碰別人的容器）。
    _pg_stale="$(_nightly_bounded 20 docker ps -aq --filter "name=^${NIGHTLY_PG_CONTAINER}\$" 2>/dev/null)"
    if [ -n "${_pg_stale}" ]; then
      echo "[nightly][pg] 發現殘留的非運行中容器 ${NIGHTLY_PG_CONTAINER}（上輪沒收乾淨或重啟復活）⇒ docker rm -f -v 後重起"
      _nightly_bounded 60 docker rm -f -v "${NIGHTLY_PG_CONTAINER}" >/dev/null 2>&1
    fi
    echo "[nightly][pg] Docker 可達 ⇒ docker compose up -d --wait（CI 對等 PG17；stage 3 結束後收）"
    NIGHTLY_PG_STARTED=1  # 先記帳再 up：up 中途失敗或被殺，nightly_pg_down 也要能收乾淨
    if ! _nightly_bounded 240 docker compose -f "${NIGHTLY_PG_COMPOSE}" up -d --wait; then
      echo "[nightly][pg] docker compose up --wait 失敗或逾時 ⇒ 本晚為 nopg 剖面（DEF-200-075）"
      nightly_pg_down
      return 0
    fi
  fi
  # 容器是 tmpfs、每次新建都是空庫 ⇒ 必須 migrate，否則 stage 3 的 autodetect 剎車④ 會拒絕注入。
  if ! ( cd "${ROOT}/AutoClaude" && _nightly_bounded 180 env AUTOCLAUDE_DB_DSN="${NIGHTLY_PG_DSN}" "${PY}" -m alembic upgrade head ); then
    echo "[nightly][pg] alembic upgrade head 失敗或逾時 ⇒ 本晚為 nopg 剖面（DEF-200-075）"
    nightly_pg_down
    return 0
  fi
  # 取證：upgrade 成功時是靜默的，RunId log 上看不出它跑過——把 migrate 後的版本逐行寫進 log。
  ( cd "${ROOT}/AutoClaude" && _nightly_bounded 60 env AUTOCLAUDE_DB_DSN="${NIGHTLY_PG_DSN}" "${PY}" -m alembic current ) 2>&1 \
    | sed 's/^/[nightly][pg] alembic current: /'
  echo "[nightly][pg] CI 對等 PG 已起且已 migrate ⇒ stage 3 預期為 +pg 剖面（憑證看 stage 3 的 [PG autodetect]／[skip census]）"
}

# 去重鎖（R16 SCAN-C-2）：下面的心跳 mtime 判斷本身是 check-then-act，若 launchd
# 的 RunAtLoad 與 StartCalendarInterval(02:00) 兩個觸發源、或手動重跑與排程觸發
# 時間點重疊，兩個行程可能同時通過「今日尚未有心跳」的檢查，導致重複跑一整套
# 整套 stage gate。本機查無 `flock`（GNU 專屬，macOS 無此指令）；`shlock` 雖存在
# 但非所有 macOS 版本保證都有，改用最保險的 POSIX `mkdir` atomic lock pattern
# （同一路徑下 mkdir 建立目錄具原子性，兩個行程不可能同時成功）。陳舊鎖清除
# 比照 tools/dev_start.py `_acquire_bootstrap_lock()` 慣例：以鎖檔內 PID 是否
# 仍存活判斷（而非固定逾時秒數）——整套 stage gate 本身執行時間會變動，固定逾時
# 容易誤殺仍在跑的合法行程。
NIGHTLY_LOCK_DIR="${ROOT}/AutoClaude/logs/.nightly_mac.lock"
_nightly_lock_release() {
  nightly_pg_down  # DEF-200-075：本函式是 EXIT trap（正常結束／SIGTERM／SIGHUP 皆會走到），順手收 PG 容器
  nightly_docker_down  # D2：容器收完才收「本腳本自己開的」Docker Desktop（沿用的不收）
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

# python 解析：釘死根層 .venv（DEF-200-302，mac 側補齊）——不再退回 PATH 現場
# 解析，缺席即 fail-loud。原 else 分支的 `command -v python || command -v
# python3` 退路正是本輪要拔除的「沒人維護的第二套環境」（DEF-101-506 事故的
# 病根：schtasks 排程與已啟用 venv 的終端機/agent 觸發各自解析到不同直譯器）。
PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "❌ 根層 .venv 直譯器不存在：${PY}（DEF-200-302：nightly 釘死根層 .venv，不再退回 PATH 現場解析）— 修法：在 repo 根執行 tools/bootstrap.sh 或 source tools/dev_start.sh 建立 .venv" >&2
  exit 1
fi
# DEF-101-506：本檔的直譯器**已**釘成絕對路徑（不靠 PATH 現場解析，故無 Windows
# 側「誰啟動就用誰的 python」問題）。DEF-200-302 訂正：原本只有主路徑釘死，缺席
# 時仍退回上述 PATH 現場解析，與「已釘死」的自我宣稱矛盾；本輪拔除該退路，改為
# 缺席即 fail-loud（對稱 run_local_nightly.ps1／windows_smoke_local.ps1 既有設計）。
# 補印解析結果，與 .ps1 側取證對稱（紀律 #14 延伸）。
printf 'python 直譯器：%s [v%s]\n' "$PY" "$("$PY" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null)"

# 樹身分（DEF-200-450）：本輪「到底跑的是哪棵樹」必須寫進 RunId log。
# WHY：2026-09-28～10-01 連續四晚 nightly 跑在舊樹 1118bc30 上（立案時落後 30 個 commit），
# RunId log 逐字相同（「發現 4662 個測試（下限 4543）」）而無人察覺——log 沒有樹身分，
# 「跑舊樹」與「跑 HEAD」的日誌無從區分，這份 log 對「HEAD 綠不綠」的驗收力為零。
# Windows 側 run_local_nightly.ps1（DEF-101-887）早有 `git context:`／`SAMPLE VALIDITY:`
# 兩行，本函式是 mac 側對等實作（欄位名逐字沿用，兩平台 log 可用同一條 grep）。
# 🔴 只印 stdout（進 RunId log），**不碰心跳檔**：write_heartbeat 的行格式是三站點契約。
# 🔴 全程唯讀、取樣失敗絕不中斷 nightly：GIT_OPTIONAL_LOCKS=0 讓 `git status` 連順手刷新
# index 的寫入都不做（不與使用者同時進行的 git 操作搶 index.lock）；任何取值失敗一律印
# unknown。指紋刻意含內容（status 狀態列 ＋ tracked 檔的 diff 全文）：只雜湊狀態列的話，
# 「對已在清單內的檔再改一次」對它完全不可見（理由同 .ps1 的樣本效度戳記）。diff 取
# plumbing `diff-index -p`、不用 porcelain `git diff HEAD`：後者實測即使帶
# GIT_OPTIONAL_LOCKS=0 仍會為刷新 stat 資訊改寫 index（git 2.54 實測；兩者輸出逐位元相同）。
# HEAD 年齡用 git 的 epoch 秒（%ct）配 `date +%s` 算，不碰 BSD/GNU 分歧的 `date -d`。
TREE_STALE_HOURS=72  # HEAD 超過此小時數未更新 ⇒ 疑似本機沒 git pull（立案的四晚即此形態）
_ro_git() { GIT_OPTIONAL_LOCKS=0 git -C "${ROOT}" "$@" 2>/dev/null; }
_ro_val() {  # 唯讀取值：失敗或空輸出 ⇒ 印 unknown（取樣失敗不得讓腳本死掉）
  if _g_out="$(_ro_git "$@")" && [ -n "${_g_out}" ]; then printf '%s' "${_g_out}"; else printf 'unknown'; fi
}
print_tree_identity() {
  _ti_branch="$(_ro_val rev-parse --abbrev-ref HEAD)"
  _ti_sha="$(_ro_val rev-parse --short HEAD)"
  _ti_head="$(_ro_val log -1 --format='%cI %ct' HEAD)"  # "<ISO 時間> <epoch 秒>"；取不到則整串為 unknown
  printf 'git context: branch=%s sha=%s head_date=%s origin_main=%s origin_main_date=%s behind_origin_main=%s（本機 ref，未 fetch，落後數可能低估）\n' \
    "${_ti_branch}" "${_ti_sha}" "${_ti_head%% *}" \
    "$(_ro_val rev-parse --short origin/main)" "$(_ro_val log -1 --format=%cI origin/main)" \
    "$(_ro_val rev-list --count HEAD..origin/main)"
  _ti_state="unknown"; _ti_dirty="-1"; _ti_fp="unknown"
  if _ti_porcelain="$(_ro_git -c core.quotepath=false status --porcelain)"; then
    _ti_dirty="$(printf '%s\n' "${_ti_porcelain}" | grep -c .)"
    if [ -n "${_ti_porcelain}" ]; then _ti_state="dirty"; else _ti_state="clean"; fi
    _ti_fp="$({ printf '%s\n' "${_ti_porcelain}"; _ro_git diff-index -p --no-ext-diff HEAD; } \
      | "$PY" -c 'import hashlib,sys;'\
' sys.stdout.write(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:12])' 2>/dev/null)"
    # 只認非空的十六進位：子行程往 stdout 印垃圾（橫幅／警告）時，單判空字串會照單全收。
    # 用 write 不用 print：輸出不帶換行——Windows 原生 python.exe 會把 \n 譯成 \r\n，而 $(…) 只
    # 剝 \n，CR 會黏進指紋。程式碼刻意維持「無換行、無引號」的單一 argv（兩段單引號以行尾反斜線
    # 相接成同一個字），不引入 MSYS 傳參的新變數。
    case "${_ti_fp}" in ''|*[!0123456789abcdef]*) _ti_fp="unknown" ;; esac
  fi
  printf 'SAMPLE VALIDITY: tree_state=%s dirty_entries=%s tree_fingerprint=%s head=%s\n' \
    "${_ti_state}" "${_ti_dirty}" "${_ti_fp}" "${_ti_sha}"
  case "${_ti_state}" in
    clean) ;;
    dirty) printf '⚠️ SAMPLE VALIDITY: 本輪在**非乾淨**工作樹上採集（%s 筆未提交變更）⇒ 本輪任何紅燈都可能是「量到半成品」而非真缺陷，任何綠燈也不代表 HEAD 為綠；判讀本輪 log 前先確認上列指紋對應的是誰的作業\n' "${_ti_dirty}" ;;
    *) printf '⚠️ SAMPLE VALIDITY: 工作樹狀態取樣失敗——本輪樣本效度**未知**，不得當成乾淨\n' ;;
  esac
  _ti_ts="${_ti_head##* }"
  case "${_ti_ts}" in
    ''|*[!0-9]*) ;;  # 取不到 commit 時間（unknown）⇒ 不判陳舊；上面的 git context 行已把 unknown 攤開
    *)
      _ti_age_s=$(( $(date +%s) - _ti_ts ))
      if [ "${_ti_age_s}" -gt $(( TREE_STALE_HOURS * 3600 )) ]; then
        printf '⚠️ SAMPLE VALIDITY: HEAD 已 %s 小時未更新（%s）——本機可能尚未 git pull；本輪綠燈不代表 origin/main 綠\n' \
          "$(( _ti_age_s / 3600 ))" "${_ti_head%% *}"
      fi
      ;;
  esac
}
print_tree_identity

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
run_stage 2 root_unittests  env AUTOSDD_PARALLEL_TESTS=1 "$PY" "$ROOT/tools/run_root_unittests.py"
nightly_pg_up    # DEF-200-075：stage 3 要有已 migrate 的 PG（docker 不可達 ⇒ 大聲退回 +nopg）
run_stage 3 autoclaude_gate bash "$ROOT/AutoClaude/tools/local_ci_gate.sh" --unattended
nightly_pg_down  # stage 3 無論成敗都收（run_stage 不中斷）；stage 4／5 不需要 PG
nightly_docker_down  # D2：本腳本開的 Docker Desktop 也在 stage 3 後立刻收（不等 stage 4）；沿用的不收
run_stage 4 sdd_ci_gate     sdd_gate
run_stage 5 nightly_anchor  "$PY" "$ROOT/tools/refresh_nightly_anchor.py" --write

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
