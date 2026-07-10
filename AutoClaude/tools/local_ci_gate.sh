#!/usr/bin/env bash
# local_ci_gate.sh — 本機 CI 閘門一鍵指令（macOS/Linux）。
# Windows 對等：tools/local_ci_gate.ps1（本檔為其忠實對照，鏡像 monorepo 根層 .github/workflows/autoclaude-ci.yml push gating jobs）。
#
# 依序（全綠才建議 push）：
#   0. editable 哨兵       （autoclaude 指向本 monorepo）
#   1. LOC 預算
#   2. CLAUDE.md <= 400 行
#   2b. CLAUDE.md 單行 <= 800 codepoint（contract test）
#   3. snapshot 可重現
#   4. import-linter
#   5. pytest
# 可選：
#   --act  額外用 act 在 Linux 容器跑 ci.yml（呼叫 run_act.sh）
#   --pg   額外起 docker-compose.ci.yml（pg17）跑 PG 契約測
#
# 用法：
#   bash tools/local_ci_gate.sh
#   bash tools/local_ci_gate.sh --act
#   bash tools/local_ci_gate.sh --pg
set -uo pipefail   # 刻意不設 -e：逐項收集結果，最後彙總（對齊 .ps1 的 Continue 語意）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONUTF8=1

# venv 提示：所有 gate 都靠裸 python，未啟用 venv 就直接失敗提示（勝過各 gate 逐一噴錯）
command -v python >/dev/null || { echo '❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）'; exit 1; }

# --- git hooks liveness 偵測（警告不擋）---
# repo 搬移/改名或未安裝時 dispatcher hooks 會靜默失效（實證）；CI 環境（$CI 有值）跳過
# （GitHub/act 環境無 hooks 屬正常）。與 tools/integration_gate.sh 的同名段落對稱。
if [ -z "${CI:-}" ]; then
  _hl_top="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -n "$_hl_top" ]; then
    _hl_expected="$_hl_top/tools/git-hooks"
    _hl_raw="$(git config --get core.hooksPath 2>/dev/null || true)"
    # 正規化：installer .ps1 可能寫入混合分隔符（D:/repo\tools/git-hooks）→ 統一為 /
    _hl_abs="$(printf '%s' "$_hl_raw" | tr '\\' '/')"
    case "$_hl_abs" in
      ""|/*|[A-Za-z]:/*) : ;;                    # 空值 / POSIX 絕對 / Windows 磁碟機絕對 → 原樣
      *) _hl_abs="$_hl_top/$_hl_abs" ;;          # 相對值：以 repo 根解析（git 語意）
    esac
    if [ "$_hl_abs" != "$_hl_expected" ] || [ ! -d "$_hl_expected" ]; then
      echo ''
      echo '⚠️⚠️⚠️ [hooks liveness] dispatcher git hooks 未生效 — pre-commit/pre-push 閘門不會執行！'
      echo "    core.hooksPath 目前值：${_hl_raw:-（未設定）}"
      echo "    預期值：$_hl_expected"
      echo '    請執行安裝腳本（兩子專案閘門同時生效，裝一次即可）：'
      echo '        bash AutoClaude/tools/install_git_hooks.sh'
      echo '    （本檢查僅警告、不阻擋閘門執行；CI 環境自動跳過）'
    fi
  fi
fi

DO_ACT=0; DO_PG=0
PYTEST_ARGS="tests/ -q --tb=short"
for arg in "$@"; do
  case "$arg" in
    --act) DO_ACT=1 ;;
    --pg)  DO_PG=1 ;;
    *)     PYTEST_ARGS="$arg" ;;
  esac
done

RESULT_NAMES=(); RESULT_STATUS=()
run_gate() {
  local name="$1"; shift
  printf '\n===== [%s] =====\n' "$name"
  "$@"
  local rc=$?
  local status="PASS"; [ "$rc" -ne 0 ] && status="FAIL"
  printf '[%s] %s (rc=%s)\n' "$name" "$status" "$rc"
  RESULT_NAMES+=("$name"); RESULT_STATUS+=("$status")
}

gate_editable() {
  # 動態比對：autoclaude 套件須位於本 repo 根之下（勿硬編碼資料夾名——clone 到
  # 任何目錄名皆應 PASS；舊寫法 'AISDCL_Agent' in __file__ 在改名 clone 誤報紅燈）
  local top
  top="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  AUTOCLAUDE_REPO_TOP="$top" python -c "
import os, pathlib, sys
import autoclaude
pkg = pathlib.Path(autoclaude.__file__).resolve()
root = pathlib.Path(os.environ['AUTOCLAUDE_REPO_TOP']).resolve()
ok = root == pkg or root in pkg.parents
print('autoclaude:', pkg)
print('repo root :', root)
sys.exit(0 if ok else 1)
"
}
gate_loc()      { python tools/check_loc_budget.py; }
gate_claudemd() {
  local n; n="$(wc -l < CLAUDE.md | tr -d ' ')"
  if [ "$n" -gt 400 ]; then echo "CLAUDE.md=$n > 400"; return 1; fi
  echo "CLAUDE.md=$n lines OK"
}
gate_claudemd_line() { python -m pytest tests/contract/test_claude_md_no_long_lines.py -q --tb=short; }
gate_snapshot() { python tools/snapshot_sync.py --check; }
gate_importlinter() {
  if command -v lint-imports >/dev/null 2>&1; then lint-imports;
  else echo 'lint-imports 未安裝（pip install -e .[lint]）'; return 1; fi
}
gate_pytest() { python -m pytest $PYTEST_ARGS; }

run_gate 'editable sentinel' gate_editable
run_gate 'LOC budget'        gate_loc
run_gate 'CLAUDE.md <=400'   gate_claudemd
run_gate 'CLAUDE.md line<=800' gate_claudemd_line
run_gate 'snapshot --check'  gate_snapshot
run_gate 'import-linter'     gate_importlinter
run_gate 'pytest'            gate_pytest

if [ "$DO_PG" -eq 1 ]; then
  gate_pg() {
    docker compose -f docker-compose.ci.yml up -d --wait || { echo 'docker compose up --wait 失敗'; return 1; }
    local dsn='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
    export AUTOCLAUDE_DB_DSN="$dsn" AUTOCLAUDE_TEST_PG_DSN="$dsn" AUTOCLAUDE_ALLOW_INSECURE_DB=1
    # alembic rc 防吞：migration 失敗即清理容器並判 FAIL，不讓後續 pytest rc 蓋過
    if ! alembic upgrade head; then
      echo 'alembic upgrade head 失敗'
      docker compose -f docker-compose.ci.yml down -v >/dev/null 2>&1 || true
      return 1
    fi
    python -m pytest tests/contract/test_pg_state_repository_contract.py -q --tb=short
    local rc=$?
    docker compose -f docker-compose.ci.yml down -v >/dev/null 2>&1 || true
    return $rc
  }
  run_gate 'PG contract (pg17)' gate_pg
fi

if [ "$DO_ACT" -eq 1 ]; then
  run_gate 'act CI (Linux test job)' bash "$REPO_ROOT/tools/run_act.sh" --job test
fi

# ----- 總結 -----
printf '\n========== 本機 CI 閘門總結 ==========\n'
failed=0
for i in "${!RESULT_NAMES[@]}"; do
  printf '  %-22s %s\n' "${RESULT_NAMES[$i]}" "${RESULT_STATUS[$i]}"
  [ "${RESULT_STATUS[$i]}" = "FAIL" ] && failed=$((failed+1))
done
if [ "$failed" -gt 0 ]; then
  printf '\n❌ %s 項失敗 — 請於本機修復後再 push。\n' "$failed"
  exit 1
fi
printf '\n✅ 全部通過 — 可安全 push。\n'
exit 0
