#!/usr/bin/env bash
# DEF-38-001（P3）Copy-on-Evolve git-archive 版 —— 結構性只匯 git tracked 源碼。
#
# 用法（以 bash 呼叫 — repo 政策：755 入庫僅限 tools/git-hooks/，其餘 .sh 一律 bash xxx.sh）：
#   bash scripts/copy_on_evolve.sh <from_dir> <to_dir>
#     <from_dir>  既有凍結版本目錄（須為 git tracked 且 committed 於 HEAD）
#     <to_dir>    新版本目錄（必須尚不存在，拒絕覆蓋）
#
# WHY（取代 DEF-11-001 tar --exclude 版的設計演進）：
#   舊版以 `tar --exclude` 在複製前剔除已知 runtime 產物（build/reports/ /
#   arch-fitness.json / chaos-report.json / __pycache__ / *.pyc）。但 **--exclude 清單未含
#   `tools/fsm_runtime/formal/states/`**（TLC 模型檢查每跑一次 dump 一個時間戳目錄）——
#   DEF-38-001：來源版若跑過 TLC 累積 states，tar 會把這坨 bloat 一路搬運繼承（v0.05~v0.13
#   實證每版肥 19MB／5193 檔，皆為從 v0.01 一路拖來的同一份副本）。
#   **git archive 從根本解決**：它只輸出 git tracked（committed 於 HEAD）的內容，一切
#   untracked / gitignored 的 runtime 產物（build/reports、formal/states、arch-fitness.json、
#   chaos-report.json、__pycache__、*.pyc…）**結構性被排除**，無需維護任何 --exclude 清單，
#   且永不再因新 runtime 產物類型而 bloat 回歸。tracked 即輸入、untracked 即輸出，邊界由 git
#   單一事實源裁定。FSM 種子模板（DEF-15-001，state_loader._load_template 必需的真輸入）因為
#   是 tracked（v0.13+ 在 tools/fsm_runtime/templates/；v0.05~v0.12 在 build/reports/fsm/ 經
#   `!` negate 保持 tracked），git archive 一律納入，舊版 tar 的「排除後補回」特例自然消失。
#
#   注意：git archive 取 **HEAD（committed）** 樹，非工作樹/index——故來源版須已 commit
#   （Copy-on-Evolve 的來源恆為凍結唯讀版，必已 commit，語意正確且更安全）。
#
#   本腳本置於 AISDLC_SDD/scripts/（versioned 目錄外＝共享 CI infra）→ 免 Copy-on-Evolve
#   （同 ci-gate.sh / conftest.py / cross_version_guard.py 精神）。
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "用法: $0 <from_dir> <to_dir>" >&2
  exit 2
fi

FROM="$1"
TO="$2"

if [ ! -d "$FROM" ]; then
  echo "❌ 來源目錄不存在: $FROM" >&2
  exit 1
fi
if [ -e "$TO" ]; then
  echo "❌ 目標已存在（拒絕覆蓋，請先移除或改名）: $TO" >&2
  exit 1
fi

# git archive 需要「repo 根相對」的 tree-ish 路徑。以 `git -C "$FROM" rev-parse --show-prefix`
# 由 git 自身計算 FROM 相對 repo 根的路徑——避開 Windows Git Bash 中 `--show-toplevel`（回 D:/…）
# 與 `pwd`（回 /d/…）路徑形式不一致導致前綴剝除失敗的陷阱（smoke test 揭露）。
if ! FROM_REL="$(git -C "$FROM" rev-parse --show-prefix 2>/dev/null)"; then
  echo "❌ 來源不在 git 工作樹內: $FROM" >&2
  exit 1
fi
FROM_REL="${FROM_REL%/}"  # 去尾斜線

# 🔴 所有 tree 操作一律 `git -C "$TOP"`（以 repo 根為 cwd）。否則 `HEAD:<path>` 會被當成
# **cwd 相對**解析（從子目錄呼叫時 git 疊上 cwd 前綴 → 匯出 0 檔，smoke test 第二次揭露）。
TOP="$(git rev-parse --show-toplevel)"

# 來源須 tracked 於 HEAD（git archive 只認 committed tree；未追蹤目錄會 fatal）。
if ! git -C "$TOP" rev-parse --verify -q "HEAD:$FROM_REL" >/dev/null 2>&1; then
  echo "❌ 來源未被 git tracked 於 HEAD（git archive 版只匯 committed tracked 內容）: $FROM_REL" >&2
  echo "   若來源為本輪新建尚未 commit，請先 commit 後再 Copy-on-Evolve。" >&2
  exit 1
fi

mkdir -p "$TO"
git -C "$TOP" archive "HEAD:$FROM_REL" | tar -x -C "$TO"

_N="$(git -C "$TOP" ls-tree -r --name-only "HEAD:$FROM_REL" | wc -l | tr -d ' ')"
# `$VAR` 後緊跟全形字元必須用 `${VAR}`——macOS bash 3.2 UTF-8 locale 會把全形字元
# 首位元組吃進變數名，配 set -u 直接 unbound variable 崩潰。
echo "✅ Copy-on-Evolve（git archive，純 tracked）: ${FROM} → ${TO}（匯出 ${_N} tracked 檔；結構性排除所有 untracked/gitignored runtime 產物，含 build/reports/ 與 formal/states/，DEF-38-001）"

# ── DEF-58-002（P1 根因）：建版後自動同步框架版本戳記 + 父層鏡像 ────────────────────
# WHY：新版以 git archive 逐字繼承來源版的 skill 版本戳（`**基於**: AISDLC-SDD vX.YY`、
#   README/PLAN `**版本**: vX.YY-SDD`），仍指向「來源版」而非新版 → ci-gate 的
#   skill_header_sync / sync_exposed_skills 兩道 SSOT lint 必紅。此同步原為 Copy-on-Evolve
#   的人工後步驟，DEF-CLDREV-007（v0.19）與 DEF-58-001（v0.22）兩度被遺忘致 ci-gate 帶紅
#   入庫（且 improving_57 經 `| tail` 遮蔽退出碼假報綠）。把同步釘進建版腳本本身＝「人去
#   記得改」從流程消失（對齊 DEF-CLDREV-007 哲學）。set -e ⇒ 同步失敗即 fail-loud 非零中止，
#   不容假綠。顯式傳 `--repo-root <BASE>`（BASE＝新版 TO 的父目錄＝版本目錄群所在）：production
#   下 BASE＝AISDLC_SDD/，與兩腳本預設 dirname(dirname(__file__)) 等價；顯式化使隔離測試可指向
#   tmp 版本基底而不誤觸真實 v0.0X。兩腳本以 `sort -V | tail -1` 取 LATEST（剛建的新版即 LATEST）。
#   同層 sibling 存在性 guard：隔離 harness（僅複製本腳本、無 siblings）優雅略過並 warn，不破壞
#   既有 helper 測試；production scripts/ 恆具 siblings 故必跑。
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_BASE="$(cd "$(dirname "$TO")" && pwd)"
# PYTHON 可覆寫（預設 python）：production／ci-gate 用 `python`，跨平台測試可注入 sys.executable。
# 頂層單一定義，供下方三個建版後同步 block（戳記/鏡像、.gitignore、FRAMEWORK_STATUS）共用
# ——避免 set -u 下某 block guard 不過致 _PY 未定義（DEF-96-001 補第三 block 時上提）。
_PY="${PYTHON:-python}"
if [ -f "${_SCRIPT_DIR}/skill_header_sync.py" ] && [ -f "${_SCRIPT_DIR}/sync_exposed_skills.py" ]; then
  echo "==> 同步新版框架版本戳記（skill_header_sync --write）"
  "${_PY}" "${_SCRIPT_DIR}/skill_header_sync.py" --write --repo-root "${_BASE}"
  echo "==> 重生父層曝光 skills 鏡像（sync_exposed_skills --write）"
  "${_PY}" "${_SCRIPT_DIR}/sync_exposed_skills.py" --write --repo-root "${_BASE}"
  echo "✅ 戳記 + 鏡像已隨建版自動同步（DEF-58-002：免人工後步驟，杜絕戳記 bit-rot 帶紅入庫）"
else
  echo "⚠️ 同層無 skill_header_sync.py / sync_exposed_skills.py（隔離環境）；略過戳記自動同步" >&2
fi

# ── DEF-59-001（P2 根因，DEF-58-002 同家族）：建版後自動補新版 .gitignore runtime 產物 block ──
# WHY：新版的 build/reports/ / arch-fitness.json / chaos-report.json 為 untracked runtime 產物，
#   須在 BASE/.gitignore 補排除 block，否則 ci-gate 的 gitignore 覆蓋 lint（DEF-37-001，
#   test_gitignore_coverage_lint.py::test_real_repo_latest_covered）對 LATEST 失效報紅。此前為
#   人工後步驟（與 DEF-58-002 戳記同步**同根因家族**：「人去記得改」＝從流程消失）；improving_59
#   建 v0.23 即踩到帶紅。把它釘進建版腳本＝杜絕同類復發（對齊 DEF-58-002／DEF-CLDREV-007 哲學）。
#   idempotent：block 已存在（grep 命中首行 path）則略過，重跑安全。lint 只查 3 path 行存在，
#   自動補的 comment 用泛用敘述（改進輪敘述見 EVOLUTION_LOG.md）即足。
_NEWVER="$(basename "$TO")"
_GITIGNORE="${_BASE}/.gitignore"
if [ -f "${_GITIGNORE}" ]; then
  if grep -q "^${_NEWVER}/build/reports/" "${_GITIGNORE}"; then
    echo "==> .gitignore 已含 ${_NEWVER} runtime 產物 block（idempotent 略過）"
  else
    {
      echo ""
      echo "# ── ${_NEWVER} runtime 取證產物排除（Copy-on-Evolve 自動補；改進輪敘述見 EVOLUTION_LOG.md）──"
      echo "${_NEWVER}/build/reports/"
      echo "${_NEWVER}/arch-fitness.json"
      echo "${_NEWVER}/chaos-report.json"
    } >> "${_GITIGNORE}"
    echo "✅ 已自動補 ${_NEWVER} runtime 產物排除 block 至 .gitignore（DEF-59-001：免人工後步驟）"
  fi
else
  echo "⚠️ 找不到 ${_GITIGNORE}（隔離環境）；略過 .gitignore 自動補" >&2
fi

# ── DEF-96-001（P2 根因，DEF-58-002／59-001 同家族）：建版後自動重生 FRAMEWORK_STATUS.md SSOT ──
# WHY：framework_status_snapshot.py 掃磁碟+權威源算「最新演化版（LATEST＝sort -V|tail -1）」的
#   版本號與各類資產計數並生成唯一真相源 FRAMEWORK_STATUS.md；**新版一建立 LATEST 即改變** →
#   既有 FRAMEWORK_STATUS.md「最新演化版」段 stale → ci-gate 的「框架版本/計數 SSOT 新鮮度 lint」
#   （framework_status_snapshot.py --check）報紅。此前為人工後步驟（improving_96 建 v0.29 即踩到
#   首跑 ci-gate stale、手動 --write 後才綠）；與 DEF-58-002 戳記、DEF-59-001 .gitignore **同根因
#   家族**「人去記得改＝從流程消失」。把 --write 釘進建版腳本＝杜絕同類復發（對齊 DEF-CLDREV-007
#   哲學）。idempotent：--write 依磁碟現況重生、重跑安全；set -e ⇒ 失敗即 fail-loud 非零中止。
#   import rfc_lifecycle_lint（discover_frozen_versions/latest_version）；隔離 harness 須一併佈署。
if [ -f "${_SCRIPT_DIR}/framework_status_snapshot.py" ]; then
  echo "==> 重生框架版本/計數 SSOT（framework_status_snapshot --write）"
  "${_PY}" "${_SCRIPT_DIR}/framework_status_snapshot.py" --write --repo-root "${_BASE}"
  echo "✅ FRAMEWORK_STATUS.md 已隨建版自動重生（DEF-96-001：免人工後步驟，杜絕 SSOT stale 帶紅入庫）"
else
  echo "⚠️ 同層無 framework_status_snapshot.py（隔離環境）；略過 SSOT 重生" >&2
fi
