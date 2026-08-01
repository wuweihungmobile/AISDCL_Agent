#!/usr/bin/env bash
# AISDLC-SDD — 本機 CI 閘門（push 前必過）。
#
# 單一真相源：monorepo 根層 .github/workflows/aisdlc-sdd-ci.yml、docker-compose
# ci-runner、pre-push hook、act 一律呼叫本腳本，確保「地端 = ubuntu-latest」跑同一組檢查。
#
# 用法：
#   bash scripts/ci-gate.sh              # 離線閘門（pytest 含 offline reachability + arch_fitness）
#   bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java + tla2tools.jar）
#   SDD_RUN_TLC=1 bash scripts/ci-gate.sh
#   SDD_FW_VERSION=AISDLC_SDD_v0.04 bash scripts/ci-gate.sh   # 只測指定單一版本（debug）
#   SDD_GATE_DRY_RUN=1 bash scripts/ci-gate.sh                # 僅印出將測版本清單即離開（測試用）
#
# Exit：0 全過；非 0 任一硬閘門失敗（arch_fitness structural fail 視為失敗，
#       advisory warn 不阻擋，與 nightly-strict 同語意）。
#
# DEF-03-001（P2）修復 — 雙軌版本閘門：
#   過去 FW_DIR 寫死 AISDLC_SDD_v0.01 → 官方閘門永遠只測凍結基線，實際承載框架
#   演化的 v0.02+（EVOLUTION_LOG 自述「可修改版本」）從不進官方 CI/pre-push，與
#   「地端 = CI = ubuntu-latest 同一組檢查」初衷相違。本腳本改為對「凍結基線 v0.01
#   + 自動偵測之最新演化版」雙軌各跑一次完整閘門，使最新版恆納入官方閘門覆蓋。
set -euo pipefail

# 強制 Python 子程序統一 UTF-8（對齊 AutoClaude tools/local_ci_gate.sh 同名設定）：
# macOS/Linux 無害；Windows git-bash 下防 zh-TW cp950 UnicodeDecodeError。
export PYTHONUTF8=1

# ── pytest 收斂數下限鎖（DEF-101-386 collection-floor lock）─────────────────
# 先例：tools/run_root_unittests.py:37 的 MIN_TESTS——目錄/pattern 打字或誤增
# conftest skip-all 會讓套件靜默縮小、其餘閘門仍全綠，此為與該類失敗同構的
# 缺口（本腳本三套 pytest 過去皆無此鎖）。下方 PASSED/INFRA_PASSED 算出後即
# 檢查；下限留有餘裕（非緊貼實測值，避免良性 collection-order/parametrization
# 噪聲觸發假紅）。往後每輪只可把下限「往上棘輪」，往下調整僅限伴隨蓄意刪測試。
MIN_TESTS_FROZEN=1470   # R59 重釘（R47 為 1400）。實測 v0.01=1478，留 8 餘裕吸收
                        # docker daemon 停用的 −3（見 ONBOARDING §7 差異歸因表）
MIN_TESTS_LATEST=1650   # R47 二審修復後實測 LATEST=1729（留 ~79 餘裕；此數字會隨後續各輪
                        # 新增測試自然漂移，門檻本身不逐輪重新對齊，留有餘裕即可）
MIN_TESTS_SHARED=240    # R59 重釘（R49 為 190，其註解記的 226 亦已過期——實測 248，
                        # 比值 248/190=**1.305 已越過根層 run_root_unittests.py 自訂的
                        # RATCHET_STALE_RATIO=1.25 紅線**，鑑別力少掉三成〔可靜默蒸發 58
                        # 支仍全綠〕；依 Rule 7「兩套相反政策要擇一」對齊根層 ratchet 精神。
                        # 留 8 餘裕吸收跨平台 ±1 漂移。R59 二審 ARCH-R59-NB3 指出

# 🔴 R68：載具守門。macOS 預設 shell 是 zsh，`zsh scripts/ci-gate.sh` 下
# ${BASH_SOURCE[0]} 未定義（zsh: parameter not set）→ REPO_ROOT/dot-source 全解錯，
# 使用者拿到的是與事實相反的診斷訊息。fail-loud 一行勝過整串錯誤級聯。
[ -n "${BASH_VERSION:-}" ] || {
  echo "❌ 本腳本需以 bash 執行：bash scripts/ci-gate.sh（macOS 預設 zsh 不支援 BASH_SOURCE）" >&2
  exit 2
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# R43 Scan-B（DEF-101-353）：WindowsApps 空殼排除 guard（純函式定義，無副作用）；
# 比照既有 scripts/install-hooks.sh 同款跨子專案 dot-source monorepo 根層
# tools/lib/*.sh 慣例（該檔第 17 行 source git_hooks_install_common.sh）。
# 🔴 R68：source 失敗改為硬錯——guard 檔被改名/移位時，原本「. 失敗仍照跑」會讓
# WindowsApps 空殼防護靜默消失（fail-open），無人知曉。
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/lib/windowsapps_guard.sh" || {
  echo "❌ 無法載入 tools/lib/windowsapps_guard.sh（WindowsApps 空殼防護缺席）" >&2
  exit 2
}

# python 缺席 fail-loud（R14 SCAN-SH-1）：現代 macOS 乾淨 PATH 只有 python3 沒有
# python，未啟 venv 直跑時下方 LATEST 解析的 `|| true` 會把 127（command not found）
# 靜默吞成「無演化版」——dry-run 假綠、非 dry-run 雙軌閘門靜默降為單軌 v0.01。
# 與姊妹腳本（tools/integration_gate.sh / AutoClaude/tools/local_ci_gate.sh）同款守門。
if ! is_real_python_candidate python; then
  echo "❌ 找不到 python — 請先啟用 venv（macOS/Linux: source .venv/bin/activate；Windows: .venv/Scripts/activate；見 ONBOARDING.md §3）" >&2
  exit 1
fi

# ── 版本解析（DEF-03-001 雙軌；R10 DEF-101-133 改走 SSOT）───────────────────
FROZEN_BASELINE="AISDLC_SDD_v0.01"   # 凍結基線：恆測，回歸防護
# 自動偵測最新演化版：委派 scripts/sdd_version.py（LATEST 解析單一真相源）。
# 歷史：原三重 glob `ls -d ... | sort -V | tail -1`（DEF-19-002/DEF-43-003 演進）尾端未錨定
# 且掃磁碟非 git tracked——`AISDLC_SDD_v0.30.bak`、檔總管複製品「v0.30 - Copy」、未 commit
# 手動複製目錄都會被選成 LATEST，閘門綠燈實為測錯樹（R10 ARCH-3 實測重現）。SSOT 語意：
# git tracked（含 index）＋完整錨定 `^AISDLC_SDD_v\d+\.\d+$`＋(major,minor) 數值取最大。
# `|| true`：resolver 找不到任何版本目錄時 exit 1，維持原「LATEST 可為空」語意
# （空 → 僅測凍結基線；stderr 警告直通 console 不吞）。python 缺席已由檔頭守門
# fail-loud 攔下，此處 `|| true` 只剩「resolver 自身失敗/無版本」兩情境，均以下方
# 降軌警示可見化（R14 SCAN-SH-1：杜絕「驗證鏡子靜默縮面」）。
LATEST="$(python "${REPO_ROOT}/scripts/sdd_version.py" || true)"

FW_VERSIONS=("${FROZEN_BASELINE}")
if [[ -n "${LATEST}" && "${LATEST}" != "${FROZEN_BASELINE}" ]]; then
  FW_VERSIONS+=("${LATEST}")   # 最新演化版：使演化版恆納入官方閘門
fi

# 可選覆寫：SDD_FW_VERSION 指定單一版本（debug / 二分定位用），跳過雙軌
if [[ -n "${SDD_FW_VERSION:-}" ]]; then
  FW_VERSIONS=("${SDD_FW_VERSION}")
fi

# 降軌警示置於 FW_VERSIONS 定案後（R14 一審 SD-R14-REV-1：若先印再被 SDD_FW_VERSION
# 覆寫，會出現「警示說僅測基線、實際測覆寫版」的誤導）；覆寫時不警示。
if [[ -z "${LATEST}" && -z "${SDD_FW_VERSION:-}" ]]; then
  echo "⚠️ LATEST 解析為空（resolver 失敗或無演化版目錄）— 本次僅測凍結基線 ${FROZEN_BASELINE}" >&2
fi

# dry-run：僅印出將測版本即離開（供 test_ci_gate_version_resolution.py 鎖定解析邏輯）
if [[ "${SDD_GATE_DRY_RUN:-0}" == "1" ]]; then
  echo "SDD_GATE_VERSIONS=${FW_VERSIONS[*]}"
  exit 0
fi

# 🔴 R68 argv fail-loud：原本只做 `[[ "${1:-}" == "--full-tlc" ]]` 精確等值，全檔對
# 其餘 argv 零驗證——`--fulltlac` 這種 typo 會**靜默降級成「不跑 TLC」卻仍印
# 「✅ 本機 CI 閘門全數通過」rc=0**（實測重現）。宣稱跑了五軌 TLA+/TLC 而其實沒跑，
# 是最壞的一種假綠。未知旗標一律 usage + exit 2。
_usage() {
  cat >&2 <<'USAGE'
用法：bash scripts/ci-gate.sh [--full-tlc]
  --full-tlc   另跑五軌 TLA+/TLC 形式化驗證（需 Java + tla2tools.jar）
  -h, --help   顯示本說明
環境變數：SDD_RUN_TLC=1（等同 --full-tlc）、SDD_FW_VERSION=<版本目錄>（只測單一版本）、
          SDD_GATE_DRY_RUN=1（僅印將測版本清單即離開）
USAGE
}
FULL_TLC=0
for _arg in "$@"; do
  case "${_arg}" in
    --full-tlc) FULL_TLC=1 ;;
    -h|--help)  _usage; exit 0 ;;
    *)          echo "❌ 未知旗標：${_arg}" >&2; _usage; exit 2 ;;
  esac
done
if [[ "${SDD_RUN_TLC:-0}" == "1" ]]; then
  FULL_TLC=1
fi

# ── 逐軌計數累積（DEF-06-001 取證友善性）──────────────────────────────────
# 收斂時彙整成單行 `vX:N passed`，使單次輸出即自證逐軌結果，免審計捲動截斷輸出。
GATE_SUMMARY=()

# ── 單一版本閘門（雙軌共用）───────────────────────────────────────────────
run_gate_for_version() {
  local VER="$1"
  local FW_DIR="${REPO_ROOT}/${VER}"
  if [[ ! -d "${FW_DIR}" ]]; then
    echo "::error:: 版本目錄不存在：${FW_DIR}"
    exit 1
  fi
  echo "############## CI 閘門：${VER} ##############"
  cd "${FW_DIR}"

  echo "==> [1/3] 離線測試套件 pytest -m 'not chaos'（全套，含 offline reachability BFS）"
  # tee 保留串流到 console；set -o pipefail 確保 pytest 失敗（非零）時此處即中止，
  # 收斂彙總絕不會在任一軌紅燈時印出（硬閘語意不變）。
  local PYTEST_LOG
  # mktemp 帶模板（R11）：repo 對 BSD mktemp 是否需模板存在兩套假設（實測現代 macOS 皆可，統一帶模板為最保守跨平台寫法）
  PYTEST_LOG="$(mktemp "${TMPDIR:-/tmp}/ci_gate_pytest.XXXXXX")"
  # `-rs`（R59 ARCH-R59-01）：skip 理由必須可見，不得只併成一個數字。DEF-101-510 只把
  # 這件事補在根層 unittest runner；pytest 面本來就內建 `-rs`，本 repo 卻從未開。
  # DEF-101-515 需人工考古才解釋得出 v0.30 −4 的兩支平台硬排除，根因即此。
  # 對計數無影響：pytest_passed_count.sh 抓 `N passed`，SKIPPED 行不含該樣式（R59 實測）。
  python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -rs 2>&1 | tee "${PYTEST_LOG}"
  # DEF-06-001：擷取逐軌 `N passed` 收斂計數（取證友善性，純函式 helper 單獨可測）
  local PASSED
  PASSED="$(bash "${REPO_ROOT}/scripts/pytest_passed_count.sh" < "${PYTEST_LOG}")"
  rm -f "${PYTEST_LOG}"
  echo "==> [1/3] ${VER}: ${PASSED} passed（not chaos）"
  GATE_SUMMARY+=("${VER}:${PASSED}")

  # DEF-101-386：collection-floor 鎖 — pytest_passed_count.sh 本身刻意 fail-soft
  # （無匹配印 0，見該檔 docstring），下限守門必須放在呼叫端（本檔）。
  # R47 二審修復：下限僅在 VER 為凍結基線或「動態解析之」LATEST 時才有校準值可用；
  # SDD_FW_VERSION 指向兩者以外之歷史版（檔頭註解記載的 ad-hoc debug/bisection
  # escape hatch）沒有對應下限（~29 個歷史版通過數各異，如 v0.10=1544 <
  # MIN_TESTS_LATEST），誤套 MIN_TESTS_LATEST 會使合法的歷史版 debug 呼叫假紅。
  # 故此情況直接略過下限檢查，不為全歷史版逐一校準門檻（與此 escape hatch 的
  # ad-hoc/debug-only 定位不成比例）。
  local MIN_TESTS_FOR_VER=""
  if [[ "${VER}" == "${FROZEN_BASELINE}" ]]; then
    MIN_TESTS_FOR_VER="${MIN_TESTS_FROZEN}"
  elif [[ "${VER}" == "${LATEST}" ]]; then
    MIN_TESTS_FOR_VER="${MIN_TESTS_LATEST}"
  fi
  if [[ -n "${MIN_TESTS_FOR_VER}" && "${PASSED}" -lt "${MIN_TESTS_FOR_VER}" ]]; then
    echo "::error:: ${VER} pytest 通過數 ${PASSED} 低於下限 ${MIN_TESTS_FOR_VER}（DEF-101-386 collection-floor lock；疑似目錄/pattern 打字或誤增 conftest skip-all 靜默縮小套件，見 tools/run_root_unittests.py:37 MIN_TESTS 先例）"
    exit 1
  fi

  echo "==> [2/3] 架構適應度 arch_fitness（structural fail 阻擋；advisory warn 放行）"
  # 必帶 --strict：唯有 --strict 時 structural fail 才回傳 exit 2（見 arch_fitness.py
  # `if args.strict and report.fails: return 2`）；否則即使有 structural fail 也只回 1
  # 被當 advisory 放行 → 與雲端 nightly-strict 同語意，避免地端漏接。
  set +e
  python -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
  local AF_CODE=$?
  set -e
  if [[ "${AF_CODE}" -ge 2 ]]; then
    echo "::error:: arch_fitness 偵測 structural fail（${VER}, exit=${AF_CODE}）"
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
}

for VER in "${FW_VERSIONS[@]}"; do
  run_gate_for_version "${VER}"
done

# DEF-101-621（R66）：SDD_FW_VERSION 是版本迴圈的 debug-only 單版覆寫（檔頭第 11 行
# 明文記載用法），語意上只該影響上面的雙軌/單軌版本解析與 run_gate_for_version 迴圈。
# 若不在此收斂，該變數會原樣外溢進下方「共享 infra scripts/tests/」pytest 子行程；
# 而該套件內 test_ci_gate_version_resolution.py 又會用 subprocess.run 原樣繼承外層
# 環境變數去組出巢狀 dry-run 呼叫，殼層設的 SDD_FW_VERSION 因而滲透進那些巢狀呼叫、
# 把測試期待的雙軌/降軌情境覆寫成單版，造成假紅——即便官方文件記載的單版 debug 呼叫
# `SDD_FW_VERSION=X bash scripts/ci-gate.sh` 本身完全合法。
unset SDD_FW_VERSION

# ── 共享 CI infra 自身回歸鎖（DEF-12-001 修復）────────────────────────────
# scripts/tests/（versioned 目錄外＝共享 CI infra：ci-gate 版本解析 / pytest 計數
# helper / 跨版 guard / Copy-on-Evolve helper 的意圖鎖）過去未被 ci-gate.sh 或
# ci.yml 任何閘門執行 → 這些「退化即紅」保護從未被實際強制。此處於版本迴圈後跑
# 一次（版本無關，故不掛特定 vX，但仍以 GATE_SUMMARY 自證 passed 數）。
# set -o pipefail + set -e：scripts/tests 任一紅燈 → 管線非零 → 此處即中止，硬閘語意一致。
echo "############## CI 閘門：共享 infra scripts/tests/ ##############"
cd "${REPO_ROOT}"
# mktemp 帶模板（R11）：同上，統一帶模板為最保守跨平台寫法
INFRA_LOG="$(mktemp "${TMPDIR:-/tmp}/ci_gate_infra.XXXXXX")"
# `-rs` 理由同上（R59 ARCH-R59-01）。
python -m pytest scripts/tests/ -q -rs 2>&1 | tee "${INFRA_LOG}"
INFRA_PASSED="$(bash "${REPO_ROOT}/scripts/pytest_passed_count.sh" < "${INFRA_LOG}")"
rm -f "${INFRA_LOG}"
echo "==> 共享 infra scripts/tests/: ${INFRA_PASSED} passed"
GATE_SUMMARY+=("scripts/tests:${INFRA_PASSED}")

# DEF-101-386：collection-floor 鎖（同上，呼叫端守門；pytest_passed_count.sh 維持 fail-soft）
if [[ "${INFRA_PASSED}" -lt "${MIN_TESTS_SHARED}" ]]; then
  echo "::error:: 共享 infra scripts/tests/ pytest 通過數 ${INFRA_PASSED} 低於下限 ${MIN_TESTS_SHARED}（DEF-101-386 collection-floor lock；見 tools/run_root_unittests.py:37 MIN_TESTS 先例）"
  exit 1
fi

# ── RFC 生命週期 lint（DEF-23-005 機械強制）─────────────────────────────────
# 框架明定「active=待決 / archive=已決」RFC 生命週期但過去無機械強制 → 已決 RFC 曾滯留
# active/（v0.12/v0.13 至今凍結著 _26/_27）。此 lint（版本無關 shared infra，read-only 純
# 觀察者）掃最新演化版 build/planning/active/，偵測已決 RFC 滯留即非零 → 硬閘擋下。
echo "############## CI 閘門：RFC 生命週期 lint（DEF-23-005）##############"
python scripts/rfc_lifecycle_lint.py "${REPO_ROOT}"

# ── Copy-on-Evolve .gitignore 覆蓋 lint（DEF-37-001 advisory）────────────────
# 每輪 Copy-on-Evolve 建新版後，新版 build/reports/ + arch-fitness.json + chaos-report.json
# 排除 block 過去全靠人工手補、無自動偵測（improving_37 v0.15 block 漏補實證）。此 lint
# （版本無關 shared infra，read-only 純觀察者）偵測磁碟最新演化版是否缺對應排除行，缺即
# advisory warn。**advisory：永遠 exit 0、不阻擋硬閘**（P3，對齊 DEF-37-001 routed「缺即 warn」）。
echo "############## CI 閘門：.gitignore 覆蓋 lint（DEF-37-001 advisory）##############"
python scripts/gitignore_coverage_lint.py "${REPO_ROOT}"

# ── Agent template 路徑存在性 lint（DEF-AGTREV-002 機械強制）──────────────────
# v0.18 全面重新接線 broken template_path（方案一）後，加此硬閘掃最新演化版 agent/
# 所有 template 引用是否解析至磁碟且為「框架根相對」（無 ../），杜絕舊接線再生。
# 版本無關 shared infra、read-only 純觀察者；broken / 非根相對即非零硬閘擋下。
echo "############## CI 閘門：Agent template 路徑 lint（DEF-AGTREV-002）##############"
python scripts/agent_template_lint.py "${REPO_ROOT}"

# ── 核心 agent collaboration 對稱性 lint（DEF-AGTREV-004 機械防復發）──────────────
# collaboration_rules 的 upstream/downstream/peer 本應構成對稱有向圖，但全靠人工同步 →
# 長期累積單向斷鏈（downstream X→Y 漏對側 upstream←X、peer 單向；DEF-AGTREV-003 只手修一處）。
# 此 lint（版本無關 shared infra、read-only 純觀察者）掃最新演化版 7 核心 agent，斷言每條
# 內部 downstream/peer 邊皆有對側宣告，不對稱即非零硬閘擋下 → 杜絕同類斷鏈再生。
echo "############## CI 閘門：核心 agent collaboration 對稱性 lint（DEF-AGTREV-004）##############"
python scripts/collaboration_symmetry_lint.py "${REPO_ROOT}"

# ── Agent scenario_usage frequency SSOT 一致性 lint（DEF-AGTREV-015 機械防復發）──────
# 各 agent 的 scenario_usage.frequency（N/10）有兩個義務全靠人工同步 → 長期漂移（第四輪
# 重審揭露 6 agent 與權威統計段系統性 off-by-one + integration「1/10 vs 自列 4」內部矛盾）：
# (1) 掌舵者裁定 SCENARIO_AGENT_MAPPING.md 頻率統計段為唯一 SSOT，凡列出之 agent 分子須等之；
# (2) 分子須等於 primary+supporting 場景項數（內部一致）。此 lint（版本無關 shared infra、
# read-only 純觀察者）掃最新演化版 agent 比對之，任一不一致即非零硬閘擋下 → 杜絕漂移再生。
echo "############## CI 閘門：Agent scenario frequency SSOT lint（DEF-AGTREV-015）##############"
python scripts/scenario_frequency_lint.py "${REPO_ROOT}"

# ── 框架版本/計數 SSOT 新鮮度 lint（DEF-AGTREV 全面收尾，機械強制）────────────────
# 版本（Copy-on-Evolve）不斷累積，過去「最新版本號 + 各類資產計數」硬寫散落多份文件
# （root/子 CLAUDE.md、INIT、RULES_INDEX…），任一處變動其餘 stale → 必然遺漏（實證：
# governance 規則由 34/35 漂到 38/39 無人察覺）。改以唯一真相源 FRAMEWORK_STATUS.md
# （磁碟+權威源實算）+ CLAUDE.md version-agnostic 指向之。此 lint（版本無關 shared infra，
# read-only 純觀察者）重生並比對，stale 即非零硬閘擋下 → 「人去記得改多處」從流程消失。
echo "############## CI 閘門：框架版本/計數 SSOT 新鮮度 lint（DEF-AGTREV 收尾）##############"
python scripts/framework_status_snapshot.py --check --repo-root "${REPO_ROOT}"

# ── Skill 版本戳記 SSOT 新鮮度 lint（DEF-CLDREV-007 系統性根除）────────────────────
# 每版 skill 的框架版本戳（SKILL.md footer `**基於**: AISDLC-SDD vX.YY`、README/PLAN 套件版
# `**版本**: vX.YY-SDD`）應對齊所在版本目錄，但全靠人工在每輪 Copy-on-Evolve 手改 → 系統性
# 漏改（DEF-CLDREV-007 實證：v0.19 內 42 footer 仍寫 v0.01、README 停在 v0.02-SDD）。此 lint
# （版本無關 shared infra、read-only 純觀察者）校最新演化版戳記是否全等其目錄版本；stale 即
# 非零硬閘擋下。前綴鎖死故不誤觸 provenance / 歷史 / 模板佔位版。先於 skills 鏡像守門（戳記＝
# 源頭，鏡像在後）。修復：python scripts/skill_header_sync.py --write
echo "############## CI 閘門：Skill 版本戳記 SSOT 新鮮度 lint（DEF-CLDREV-007）##############"
python scripts/skill_header_sync.py --check --repo-root "${REPO_ROOT}"

# ── 對外曝光 skills SSOT 新鮮度 lint（AutoSDD_improving 方案 C ②）──────────────────
# 父層 .claude/skills（版本無關曝光集）曾為早期凍結快照、與 LATEST 漂移且不受治理。
# 改以「LATEST 版 = SSOT、父層為機械鏡像」+ 此 check 硬閘，stale 即非零擋下。
# 修復：python scripts/sync_exposed_skills.py --write
echo "############## CI 閘門：對外曝光 skills SSOT 新鮮度 lint（方案 C ②）##############"
python scripts/sync_exposed_skills.py --check --repo-root "${REPO_ROOT}"

# ── Router hook 覆蓋 lint（DEF-43-008 / DEF-B 機械防破口）──────────────────────
# Claude Code 不遞迴載入子目錄 hooks → 各版 .claude/hooks 須經根層守衛式 router 橋接，且根
# settings.json 須 wire 該 router。router _HOOK_MAP 與根 settings 的 CC hook event 集合全靠人工
# 同步：若某版 settings.json 新增第 4 種 CC event（如 Stop）卻忘改根 router/settings，該版治理
# hook 在 monorepo 根 session 下靜默失效。此 lint（版本無關 shared infra、read-only 純觀察者）斷言
# 最新演化版宣告之 CC event ⊆ (router 涵蓋 ∩ 根 settings wire)；不可達即非零硬閘擋下（fail-loud）。
echo "############## CI 閘門：Router hook 覆蓋 lint（DEF-43-008）##############"
python scripts/router_hook_coverage_lint.py "${REPO_ROOT}"

echo "✅ 本機 CI 閘門全數通過（版本：${FW_VERSIONS[*]}）"
# DEF-06-001：單行自證逐軌 passed 計數，免零信任取證捲動截斷輸出
echo "   逐軌計數：${GATE_SUMMARY[*]}"
