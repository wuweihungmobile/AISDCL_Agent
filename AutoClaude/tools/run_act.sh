#!/usr/bin/env bash
# run_act.sh — 在本機 Docker 內以 act 重現 GitHub Actions（autoclaude-ci.yml），push 前攔 CI 紅燈（macOS/Linux）。
# Windows 對等：tools/run_act.ps1（本檔為其忠實對照）。
# monorepo 根層接線（2026-07-10）：workflow 已遷至 monorepo 根層
# .github/workflows/autoclaude-ci.yml → act 一律於 monorepo 根執行（讀根層 .actrc）。
#
# 用法：
#   bash tools/run_act.sh --job test     # 最快：只跑主測試閘門
#   bash tools/run_act.sh                 # 完整：跑 push 全部 job（含 PG 契約）
#   bash tools/run_act.sh --list          # 列出所有 job
#   bash tools/run_act.sh --dry-run       # 只解析不執行
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# monorepo 根 = 本腳本(AutoClaude/tools/) 上兩層
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
WORKFLOW='.github/workflows/autoclaude-ci.yml'

JOB=""; LIST=0; DRYRUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --job) JOB="$2"; shift 2 ;;
    --list) LIST=1; shift ;;
    --dry-run) DRYRUN=1; shift ;;
    *) echo "未知參數：$1" >&2; exit 2 ;;
  esac
done

# ---- 1. 定位 act（含 gh-act 退回）----
echo "[1/6] 定位 act（含 gh-act 退回）"
ACT=""
if command -v act >/dev/null 2>&1; then
  ACT="act"
else
  # pipefail 下禁用 `cmd | grep -q`（tools/git-hooks/pre-commit:32 明文紀律）：grep -q 命中
  # 即提早退出，上游收 SIGPIPE → 管線非零 → 偵測靜默失敗。比照 tools/git-hooks/pre-push
  # 的作法：先落地變數（|| true 容忍 gh 未安裝），再 herestring 餵 grep。
  GH_EXT_LIST="$(gh extension list 2>/dev/null || true)"
  # 只留 'gh-act'：'nektos/gh-act' 本含此子字串（交替冗餘）；且 BRE 的 \| 交替是 GNU
  # 擴充，macOS BSD grep 不支援 → 退回偵測在 Mac 上靜默失效（R9 跨平台複審）
  if grep -q 'gh-act' <<<"$GH_EXT_LIST"; then ACT="gh act"; fi
fi
if [ -z "$ACT" ]; then
  echo '[run_act] act 未安裝。請擇一安裝：' >&2
  echo '  brew install act' >&2
  echo '  gh extension install https://github.com/nektos/gh-act   # 再以 gh act 呼叫' >&2
  exit 127
fi
echo "[run_act] act = $ACT"

# ---- 2. 確認 Docker daemon ----
echo "[2/6] 確認 Docker daemon"
if ! docker info >/dev/null 2>&1; then
  echo '[run_act] Docker daemon 未啟動，請先開啟 Docker Desktop。' >&2
  exit 1
fi

# ---- 3. List 模式 ----
echo "[3/6] List 模式"
if [ "$LIST" -eq 1 ]; then
  $ACT -l -W "$WORKFLOW"; exit $?
fi

# ---- 4. 預先 pull 鏡像（繞過 act forcePull 對公開鏡像送無效認證的 401 bug）----
echo "[4/6] 預先 pull 鏡像"
RUNNER_IMAGE='catthehacker/ubuntu:act-latest'
NEEDED=("$RUNNER_IMAGE")
[ -z "$JOB" ] && NEEDED+=('pgvector/pgvector:pg17')
for img in "${NEEDED[@]}"; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    echo "[run_act] 鏡像已就緒：$img"
  else
    echo "[run_act] 本地缺鏡像 $img → docker pull（首次約 1~1.5GB）…"
    docker pull "$img" || { echo "[run_act] docker pull $img 失敗。" >&2; exit 1; }
  fi
done

# ---- 5. 空 .env 覆蓋（安全 + 忠實：GitHub runner 無 .env，避免注入個人憑證/偽 fail）----
echo "[5/6] 空 .env 覆蓋"
# mktemp 不用 -t：BSD(macOS) 與 GNU 的 -t 語意不同，改用明確模板路徑統一兩平台語意
EMPTY_ENV="$(mktemp "${TMPDIR:-/tmp}/autoclaude_act_empty.XXXXXX")"
: > "$EMPTY_ENV"
trap 'rm -f "$EMPTY_ENV"' EXIT

# ---- 6. 組裝並執行 ----
echo "[6/6] 組裝並執行"
ACT_ARGS=(push -W "$WORKFLOW" --pull=false --env-file "$EMPTY_ENV")
[ -n "$JOB" ] && ACT_ARGS+=(-j "$JOB")
[ "$DRYRUN" -eq 1 ] && ACT_ARGS+=(-n)

echo "[run_act] 執行: $ACT ${ACT_ARGS[*]}"
set +e
$ACT "${ACT_ARGS[@]}"
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
  echo "[run_act] ✅ 本地 CI 通過（act 退出碼 0）— 可安全 push。"
else
  echo "[run_act] ❌ 本地 CI 失敗（act 退出碼 ${rc}）— 請於本機修復後再 push。"
fi
exit $rc
