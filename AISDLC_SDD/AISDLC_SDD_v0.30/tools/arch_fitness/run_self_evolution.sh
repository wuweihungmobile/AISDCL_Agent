#!/usr/bin/env bash
# SDD Self-Evolution 有界驅動器（bash / CI 可攜）。
# 對應 workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md。
# 反死循環：硬迭代上限 + 單 finding retry budget + 收斂閘（score 嚴格下降）
#           + 同指紋復現偵測 + claude -p --max-turns。
# 預設 dry-run（只量測、不改檔、不需 claude）；--apply 才進入完整閉環。
#
# 🔴 退出碼契約（R68；.sh／.ps1 兩側逐碼同語意，規格側見
#    workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md「退出碼契約」節）：
#    0=收斂／乾淨收工　1=dry-run advisory 訊號（僅 warn）　2=dry-run structural fail 訊號
#    3=缺 claude CLI　4=ESCALATION（retry budget 用盡）　5=無可用 python 直譯器
#    6=平台前置不足（PowerShell < 7；bash 側不適用，保留不重用）
#    7=git 操作失敗（git switch -c）　64=未知參數（usage）
set -euo pipefail

# Windows/MSYS 上 python 的 open() 預設用 cp950 讀檔，會在 UTF-8 JSON 上爆。
# 啟用 UTF-8 模式，讓所有子進程 open() 一律 utf-8。
export PYTHONUTF8=1

MAX_ITER=3
RETRY_BUDGET=3
APPLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations) MAX_ITER="$2"; shift 2 ;;
    --retry-budget)   RETRY_BUDGET="$2"; shift 2 ;;
    --apply)          APPLY=1; shift ;;
    # R68：對齊 .ps1 側 comment-based help（`pwsh … -?` 可用），bash 側原本連
    # --help 都回 rc=64「未知參數」，兩側介面不對等且無法作為可啟動性 smoke。
    --help|-h)        sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "未知參數：$1" >&2; exit 64 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$FRAMEWORK_ROOT"
REPORT_DIR="build/reports/fse"
mkdir -p "$REPORT_DIR"

# R44 跨平台複審：本檔多處直接呼叫 python（py_field/top_fp/sense，以及 --apply
# 迭代閉環內的 `python -m pytest`/`python -c`），先前從未做過任何可用性判斷——全新
# 未裝真 Python 的 Windows 11 機器上，Git Bash 繼承 Windows PATH 會命中 WindowsApps
# App Execution Alias 空殼（`command -v python` 判定「存在」，實際執行只跳出
# Microsoft Store 安裝提示）。dot-source 共用 guard（比照 tools/bootstrap.sh 等
# 已收斂呼叫點），在首次呼叫 python 前 fail-loud。
# 🔴 R68：guard 位於 monorepo 根（框架版本根之外四層），框架被單獨 clone／經同版
# tools/init_project.sh 部署到使用者專案後該路徑不存在，原本的裸 dot-source 會讓
# 本檔在任何部署形態下第一行就死（rc=1，且解析出的路徑已逃出使用者專案）。改為
# 「存在才 source、缺席則降級回退」——同 LATEST tools/install_hooks/
# install_post_commit.sh 既有慣例，monorepo 內仍受 guard 保護、單獨交付時可跑。
GUARD_SRC="$SCRIPT_DIR/../../../../tools/lib/windowsapps_guard.sh"
if [ -f "$GUARD_SRC" ]; then
  # shellcheck disable=SC1091
  . "$GUARD_SRC"
  is_real_python_candidate python || { echo "❌ 找不到可用的 python 直譯器（PATH 上找不到，或僅命中 WindowsApps 空殼）" >&2; exit 5; }
else
  [ -n "$(command -v python || true)" ] || { echo "❌ 找不到可用的 python 直譯器（PATH 上找不到）" >&2; exit 5; }
fi

py_field() { python -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$1" "$2"; }
top_fp() {  # 印 "severity|ff|title|fingerprint" 給最高 ROI finding（fail 優先）
  python - "$1" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
c=[f for f in d["findings"] if f["severity"]!="info"]
c.sort(key=lambda f:0 if f["severity"]=="fail" else 1)
if c:
    f=c[0]; print(f"{f['severity']}|{f['ff']}|{f['title']}|{f['fingerprint']}")
PY
}

sense() { python -m tools.arch_fitness.arch_fitness --strict --quiet --json "$1" || true; }

echo "=== FSE_SENSE：架構適應度量測 ==="
BASE="$REPORT_DIR/findings.json"
sense "$BASE"
SCORE_BEFORE="$(py_field "$BASE" score)"
NF="$(py_field "$BASE" n_fail)"; NW="$(py_field "$BASE" n_warn)"
echo "基準 score=${SCORE_BEFORE}（fail=$NF warn=${NW}）"
[[ "$SCORE_BEFORE" == "0" ]] && { echo "FSE_DONE：已收斂。"; exit 0; }

if [[ "$APPLY" -eq 0 ]]; then
  echo "[Dry-Run] $NF structural fail / $NW advisory。"
  TOP="$(top_fp "$BASE" || true)"
  if [[ -n "$TOP" ]]; then
    IFS='|' read -r sev ff title fp <<<"$TOP"
    echo "最高 ROI：[$ff] $title (fingerprint=$fp)"
    echo "[Dry-Run] FSE_PROPOSE 將執行："
    echo "  claude -p \"針對 finding $fp 產出根因+最小變更+blast radius+rollback\" \\"
    echo "         --max-turns 6 --allowedTools Read Grep Glob --permission-mode plan"
  fi
  echo "加 --apply 進入完整有界閉環（含 🔴 人工閘）。"
  [[ "$NF" -gt 0 ]] && exit 2 || exit 1
fi

command -v claude >/dev/null 2>&1 || { echo "找不到 claude CLI（--apply 需要）。" >&2; exit 3; }

for ((iter=1; iter<=MAX_ITER; iter++)); do
  echo "========== 迭代 $iter / $MAX_ITER =========="
  sense "$BASE"
  SCORE_BEFORE="$(py_field "$BASE" score)"
  [[ "$SCORE_BEFORE" == "0" ]] && { echo "FSE_DONE：收斂。"; exit 0; }
  TOP="$(top_fp "$BASE" || true)"
  [[ -z "$TOP" ]] && { echo "FSE_DONE：僅剩 info。"; exit 0; }
  IFS='|' read -r sev ff title fp <<<"$TOP"
  [[ "$sev" != "fail" ]] && { echo "FSE_DONE：僅剩 advisory（${ff}），不自動修。"; exit 0; }
  echo "FSE_TRIAGE：選定 [$ff] $title"

  echo "FSE_PROPOSE：產出提案..."
  claude -p "針對 arch_fitness finding fingerprint=${fp}（${title}）產出：①根因 ②最小變更 ③blast radius ④rollback。只規劃不改檔。" \
         --max-turns 6 --allowedTools "Read" "Grep" "Glob" --permission-mode plan || true

  read -r -p $'\n🔴 核可並套用？(yes/no/skip) ' ans
  [[ "$ans" == "skip" ]] && continue
  [[ "$ans" != "yes" ]] && { echo "人工駁回，停機。"; exit 0; }

  branch="fse/${fp}-$(date +%Y%m%d%H%M%S)"
  # R68：原本靠 set -e 中止會回傳 git 自己的 rc（實測 128/1），與 .ps1 側「git
  # switch -c 失敗有專屬退出碼」不對等；統一為契約碼 7。
  git switch -c "$branch" || { echo "FSE_FATAL：git switch -c 失敗，中止。" >&2; exit 7; }
  applied=0
  for ((r=1; r<=RETRY_BUDGET; r++)); do
    echo "FSE_APPLY（嘗試 $r/${RETRY_BUDGET}）..."
    claude -p "依已核可提案實作 arch_fitness finding $fp 的修正。改完自行 pytest。" \
           --max-turns 12 --allowedTools "Edit" "Write" "Bash(python -m pytest:*)" --permission-mode acceptEdits || true

    echo "FSE_VERIFY：pytest + fitness..."
    if python -m pytest -m "not chaos" -q; then pytest_ok=1; else pytest_ok=0; fi
    AFTER="$REPORT_DIR/findings-after.json"; sense "$AFTER"
    SCORE_AFTER="$(py_field "$AFTER" score)"
    still="$(python -c "import json,sys;d=json.load(open('$AFTER'));print(1 if any(f['fingerprint']=='$fp' for f in d['findings']) else 0)")"

    if [[ "$pytest_ok" -eq 1 && "$SCORE_AFTER" -lt "$SCORE_BEFORE" && "$still" -eq 0 ]]; then
      # git add/commit 包在 if 條件內：set -e 對 if 測試中的失敗有豁免，失敗不中止腳本，
      # 而是落到下方 FSE_WARN + rollback——避免「驗證段過但未真正 commit」被當作已解決放行。
      if git add -A && git commit -m "fse: 修正 arch_fitness finding $fp" >/dev/null; then
        echo "FSE_COMMIT：通過（score $SCORE_BEFORE → ${SCORE_AFTER}）。"
        applied=1; break
      fi
      echo "FSE_WARN：git add/commit 失敗，本次嘗試視為未完成，進入 rollback 重試。" >&2
    fi
    [[ "$still" -eq 1 ]] && echo "同指紋復現，修正未生效。"
    echo "FSE_ROLLBACK：未收斂（pytest=$pytest_ok score ${SCORE_BEFORE}→${SCORE_AFTER}），復原。"
    git restore --staged . 2>/dev/null || true; git checkout -- . 2>/dev/null || true; git clean -fd 2>/dev/null || true
  done

  if [[ "$applied" -eq 0 ]]; then
    echo "FSE_ESCALATION：finding $fp 連 $RETRY_BUDGET 次未收斂，停機等待人工。"
    git switch - ; exit 4
  fi
  git switch -
done

echo "FSE_DONE：達迭代上限 ${MAX_ITER}，乾淨收工。"
exit 0
