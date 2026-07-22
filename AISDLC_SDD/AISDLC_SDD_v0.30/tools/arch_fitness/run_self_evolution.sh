#!/usr/bin/env bash
# SDD Self-Evolution 有界驅動器（bash / CI 可攜）。
# 對應 workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md。
# 反死循環：硬迭代上限 + 單 finding retry budget + 收斂閘（score 嚴格下降）
#           + 同指紋復現偵測 + claude -p --max-turns。
# 預設 dry-run（只量測、不改檔、不需 claude）；--apply 才進入完整閉環。
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
    *) echo "未知參數：$1" >&2; exit 64 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$FRAMEWORK_ROOT"
REPORT_DIR="build/reports/fse"
mkdir -p "$REPORT_DIR"

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
echo "基準 score=$SCORE_BEFORE（fail=$NF warn=$NW）"
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
  [[ "$sev" != "fail" ]] && { echo "FSE_DONE：僅剩 advisory（$ff），不自動修。"; exit 0; }
  echo "FSE_TRIAGE：選定 [$ff] $title"

  echo "FSE_PROPOSE：產出提案..."
  claude -p "針對 arch_fitness finding fingerprint=$fp（$title）產出：①根因 ②最小變更 ③blast radius ④rollback。只規劃不改檔。" \
         --max-turns 6 --allowedTools "Read" "Grep" "Glob" --permission-mode plan || true

  read -r -p $'\n🔴 核可並套用？(yes/no/skip) ' ans
  [[ "$ans" == "skip" ]] && continue
  [[ "$ans" != "yes" ]] && { echo "人工駁回，停機。"; exit 0; }

  branch="fse/${fp}-$(date +%Y%m%d%H%M%S)"
  git switch -c "$branch"
  applied=0
  for ((r=1; r<=RETRY_BUDGET; r++)); do
    echo "FSE_APPLY（嘗試 $r/$RETRY_BUDGET）..."
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
        echo "FSE_COMMIT：通過（score $SCORE_BEFORE → $SCORE_AFTER）。"
        applied=1; break
      fi
      echo "FSE_WARN：git add/commit 失敗，本次嘗試視為未完成，進入 rollback 重試。" >&2
    fi
    [[ "$still" -eq 1 ]] && echo "同指紋復現，修正未生效。"
    echo "FSE_ROLLBACK：未收斂（pytest=$pytest_ok score $SCORE_BEFORE→$SCORE_AFTER），復原。"
    git restore --staged . 2>/dev/null || true; git checkout -- . 2>/dev/null || true; git clean -fd 2>/dev/null || true
  done

  if [[ "$applied" -eq 0 ]]; then
    echo "FSE_ESCALATION：finding $fp 連 $RETRY_BUDGET 次未收斂，停機等待人工。"
    git switch - ; exit 4
  fi
  git switch -
done

echo "FSE_DONE：達迭代上限 $MAX_ITER，乾淨收工。"
exit 0
