#!/usr/bin/env bash
# macos_smoke_local.sh — macOS 本地驗證聚合腳本（R9 Fix-F，P1 補償控制）。
#
# 為何存在：GitHub Actions 因帳單問題停擺（DEF-101-081）期間，macOS 側機械驗證
# 真空——唯一載體 macos-compat-ci.yml 本身就是死的補償控制。本腳本讓 Mac 開發者
# （或未來 launchd 排程）一鍵跑 macos-smoke 中「可本地化」的步驟，與
# .github/workflows/macos-compat-ci.yml 對應 step 同步維護（改那邊記得改這邊）。
#
# 前置需求：git >= 2.31（[4] 用到 `git rev-parse --path-format=absolute`；
# 現代 macOS Xcode CLT 皆滿足——SD 二審 O-1 注記）。bash 3.2 相容（macOS 內建）。
#
# 涵蓋（對照 macos-compat-ci.yml macos-smoke 各 step）：
#   [1] bash -n 全根層 tools/ 下 .sh + 三支 dispatcher hooks（無副檔名）
#   [2] dispatcher 直呼煙霧（比照 CI「/bin/bash 系統 bash 直接執行驗證」step；
#       fake repo 於 OS temp，絕不對本 repo 做 git config／暫存變更）
#   [3] install_git_hooks.sh / install-hooks.sh 安裝／解除往返 + linked worktree
#       拒絕（比照 CI 對應四個 step；同樣在 fake repo）
#   [4] AISDLC_SDD LATEST install_post_commit.sh 於 worktree 實跑 + 移除後路徑斷言
#       （比照 CI 對應 step，含 2026-07-16 P1 回歸鎖）
#   [5] python tools/check_ntfs_paths.py + tools/check_script_parity.py（唯讀，
#       直接對本 repo 跑）
#
# 限制（如實揭露）：
#   - fake repo 以 git clone 自本 repo HEAD 建立 → 未 commit 的變更不在驗證範圍
#     （worktree/clone 隔離盲區：驗證前先 commit）。
#   - 無法本地化的 CI step（bootstrap/dev_start 實跑、pytest 全套、ci-gate.sh）
#     不在本腳本範圍，見 macos-compat-ci.yml。
#
# 相容性：嚴格 bash 3.2（macOS /bin/bash，2007 凍結版；禁 declare -A / mapfile /
# ${var,,}）+ BSD 工具（禁 sed -i 無 ''、readlink -f、grep -P、stat -c、date -d、
# timeout、xargs -r、find -printf）。相容手法參照 tools/git-hooks/pre-commit。
#
# 用法：bash tools/macos_smoke_local.sh
# Exit：0＝全部 PASS；1＝任一 FAIL（結尾彙總）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 系統 bash：macOS 上明確用 /bin/bash（3.2），不依賴 PATH（可能是 Homebrew 5.x，
# 會掩蓋 3.2 相容性問題）——與 macos-compat-ci.yml 同款手法。
SYS_BASH="/bin/bash"
[ -x "$SYS_BASH" ] || SYS_BASH="bash"

# 前置守門：install 共用層（tools/lib/git_hooks_install_common.sh）與守門工具
# 都需要 python —— 缺席時 fail-fast（與該共用層同款訊息），勝過中段連環爆。
if ! command -v python >/dev/null 2>&1; then
  echo "❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）" >&2
  exit 1
fi

PASS=0
FAIL=0
FAIL_LIST=""

pass() {
  PASS=$((PASS + 1))
  echo "  ✅ PASS: $1"
}

fail() {
  FAIL=$((FAIL + 1))
  FAIL_LIST="${FAIL_LIST}
  - $1"
  echo "  ❌ FAIL: $1" >&2
}

# fake repo 全程 OS temp（macOS 的 TMPDIR / 其他平台 /tmp）；mktemp 模板寫法為
# BSD 相容（BSD mktemp 必須帶模板）。
WORK="$(mktemp -d "${TMPDIR:-/tmp}/macos_smoke_local.XXXXXX")" || {
  echo "❌ 無法建立 OS temp 工作目錄" >&2
  exit 1
}
cleanup() {
  cd / 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

echo "===== macos_smoke_local（DEF-101-081 補償控制）====="
echo "repo 根：$REPO_ROOT"
echo "系統 bash：$("$SYS_BASH" --version | head -1)"
echo "OS temp 工作目錄：$WORK"
if [ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | head -1)" ]; then
  echo "⚠ 本 repo 有未 commit 變更——[2][3][4] 驗證的是 HEAD（clone），未含這些變更"
fi

# ── [1/5] bash -n：根層 tools/ 全部 .sh + 三支 dispatcher hooks ────────────────
echo ""
echo "--- [1/5] bash -n 語法檢查（根層 .sh + dispatcher hooks）---"
# heredoc 迴圈（非管線）：計數器在主 shell 累積——bash 3.2 無 lastpipe，
# 管線尾端 while 的變數變更會隨 subshell 消失（同 tools/git-hooks/pre-commit 手法）。
sh_files="$(find "$REPO_ROOT/tools" -type f -name '*.sh')"
sh_files="${sh_files}
$REPO_ROOT/tools/git-hooks/pre-commit
$REPO_ROOT/tools/git-hooks/post-commit
$REPO_ROOT/tools/git-hooks/pre-push"
syntax_bad=0
syntax_total=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  syntax_total=$((syntax_total + 1))
  if ! "$SYS_BASH" -n "$f"; then
    fail "bash -n 語法檢查失敗：${f}"
    syntax_bad=1
  fi
done <<EOF_SH
$sh_files
EOF_SH
if [ "$syntax_bad" -eq 0 ]; then
  pass "bash -n 全數通過（${syntax_total} 檔）"
fi

# ── 建立 fake repo（供 [2][3][4]）───────────────────────────────────────────
echo ""
echo "--- 建立 fake repo（git clone HEAD → OS temp）---"
FAKE="$WORK/repo"
# -c core.longpaths=true：僅 Windows Git Bash 本地測跑本腳本時避免 MAX_PATH 炸掉，
# macOS 上為無作用的無害設定。
if git clone --quiet -c core.longpaths=true "$REPO_ROOT" "$FAKE"; then
  pass "fake repo 建立完成：$FAKE"
else
  fail "git clone 建立 fake repo 失敗——[2][3][4] 無法執行"
  echo ""
  echo "===== 彙總：PASS=$PASS FAIL=$FAIL =====$FAIL_LIST"
  exit 1
fi

# ── [2/5] dispatcher 直呼煙霧（比照 CI /bin/bash 直接執行 step）────────────────
echo ""
echo "--- [2/5] dispatcher 直呼煙霧（$SYS_BASH 直接執行，fake repo）---"
(
  cd "$FAKE" || exit 9

  # 2a. pre-commit：乾淨變更應放行
  echo "probe" > _ci_probe_clean.txt
  git add _ci_probe_clean.txt
  "$SYS_BASH" tools/git-hooks/pre-commit
  rc=$?
  git reset -q _ci_probe_clean.txt
  rm -f _ci_probe_clean.txt
  [ "$rc" -eq 0 ] || exit 1

  # 2b. pre-commit：NTFS 保留裝置名應擋下（touch + git add，鏡射 CI 同款手法；
  # macOS/APFS 可建檔且 git 預設 core.protectNTFS=false 可暫存——CI macos-latest
  # 已實證）。非 macOS 平台（如 Windows Git Bash 本地驗流程）git/檔案系統會在
  # dispatcher 之前就先擋下，此時本子測試明確 SKIP（不偽裝成 PASS）。
  ntfs_skipped=0
  if touch "CON.txt" 2>/dev/null && git add "CON.txt" 2>/dev/null; then
    "$SYS_BASH" tools/git-hooks/pre-commit
    rc=$?
    git reset -q "CON.txt" || true
    rm -f "CON.txt"
    [ "$rc" -ne 0 ] || exit 2
  else
    rm -f "CON.txt" 2>/dev/null || true
    echo "  （SKIP）本平台 git/檔案系統先於 dispatcher 擋下 CON.txt 的建立/暫存（非 macOS）——NTFS 閘子測試待真 macOS 實跑"
    ntfs_skipped=1
  fi

  # 2c. post-commit：advisory 委派器應恆 exit 0
  "$SYS_BASH" tools/git-hooks/post-commit || exit 3

  # 2d. pre-push：刪除遠端分支（local_sha 全零）跳過路徑應 exit 0
  ZERO_SHA='0000000000000000000000000000000000000000'
  head_sha="$(git rev-parse HEAD)"
  printf 'refs/heads/ci-probe %s refs/heads/ci-probe %s\n' "$ZERO_SHA" "$head_sha" \
    | "$SYS_BASH" tools/git-hooks/pre-push || exit 4
  [ "$ntfs_skipped" -eq 1 ] && exit 5
  exit 0
)
sub_rc=$?
case "$sub_rc" in
  0) pass "dispatcher 直呼煙霧（pre-commit 放行/擋 NTFS 保留名、post-commit、pre-push 刪除跳過）" ;;
  5) pass "dispatcher 直呼煙霧（pre-commit 放行、post-commit、pre-push 刪除跳過；NTFS 保留名子測試 SKIP——非 macOS 平台先擋）" ;;
  1) fail "pre-commit dispatcher 對乾淨變更應 exit 0" ;;
  2) fail "pre-commit dispatcher 應擋下 NTFS 保留裝置名（CON.txt）卻放行" ;;
  3) fail "post-commit dispatcher 應恆 exit 0" ;;
  4) fail "pre-push dispatcher 刪除分支跳過路徑應 exit 0" ;;
  *) fail "dispatcher 直呼煙霧異常中斷（rc=$sub_rc）" ;;
esac

# ── [3/5] hooks 安裝／解除往返 + linked worktree 拒絕 ─────────────────────────
echo ""
echo "--- [3/5] install_git_hooks.sh / install-hooks.sh 往返 + worktree 拒絕（fake repo）---"

# 3a. AutoClaude/tools/install_git_hooks.sh 安裝／解除往返
(
  cd "$FAKE" || exit 9
  bash AutoClaude/tools/install_git_hooks.sh || exit 1
  hp="$(git config --get core.hooksPath || true)"
  [ -n "$hp" ] || exit 1
  bash AutoClaude/tools/install_git_hooks.sh --uninstall || exit 2
  hp2="$(git config --get core.hooksPath || true)"
  [ -z "$hp2" ] || exit 2
  exit 0
)
sub_rc=$?
case "$sub_rc" in
  0) pass "install_git_hooks.sh 安裝／解除往返" ;;
  1) fail "install_git_hooks.sh 安裝後 core.hooksPath 未設定" ;;
  2) fail "install_git_hooks.sh 解除後 core.hooksPath 仍殘留" ;;
  *) fail "install_git_hooks.sh 往返驗證異常中斷（rc=$sub_rc）" ;;
esac

# 3b. install_git_hooks.sh 於 linked worktree 下應正確拒絕（fail-loud）
# R10 SD-1/QA-7（DEF-101-135）：原本 worktree add 未檢查，add 失敗時 subshell 的
# cd 失敗 rc=1 恰等於「拒絕成功」預期值 → 受測腳本根本沒跑也 PASS 的假陽性。
# add 顯式檢查；subshell 內 cd 失敗改走獨立哨兵 9（比照 [2] 段 `|| exit 9` 手法）。
wt="$WORK/wt-install-git-hooks-reject"
if git -C "$FAKE" worktree add --quiet --detach "$wt" HEAD; then
  ( cd "$wt" || exit 9; bash AutoClaude/tools/install_git_hooks.sh )
  rc=$?
  git -C "$FAKE" worktree remove --force "$wt"
  if [ "$rc" -eq 1 ]; then
    pass "install_git_hooks.sh linked worktree 拒絕（rc=1 as expected）"
  else
    fail "install_git_hooks.sh 於 linked worktree 應 exit 1，實際 rc=$rc"
  fi
else
  fail "worktree add 失敗——install_git_hooks.sh 拒絕情境未能執行（非假 PASS）"
fi

# 3c. AISDLC_SDD/scripts/install-hooks.sh 安裝往返
(
  cd "$FAKE" || exit 9
  bash AISDLC_SDD/scripts/install-hooks.sh || exit 1
  hp="$(git config --get core.hooksPath || true)"
  [ -n "$hp" ] || exit 1
  git config --unset core.hooksPath || true
  exit 0
)
sub_rc=$?
if [ "$sub_rc" -eq 0 ]; then
  pass "install-hooks.sh 安裝／解除往返"
else
  fail "install-hooks.sh 安裝後 core.hooksPath 未設定或安裝失敗（rc=$sub_rc）"
fi

# 3d. install-hooks.sh 於 linked worktree 下應正確拒絕（fail-loud）
# R10 SD-1/QA-7（DEF-101-135）：同 3b——add 顯式檢查 + cd 失敗哨兵 9，堵假 PASS。
wt="$WORK/wt-install-hooks-reject"
if git -C "$FAKE" worktree add --quiet --detach "$wt" HEAD; then
  ( cd "$wt" || exit 9; bash AISDLC_SDD/scripts/install-hooks.sh )
  rc=$?
  git -C "$FAKE" worktree remove --force "$wt"
  if [ "$rc" -eq 1 ]; then
    pass "install-hooks.sh linked worktree 拒絕（rc=1 as expected）"
  else
    fail "install-hooks.sh 於 linked worktree 應 exit 1，實際 rc=$rc"
  fi
else
  fail "worktree add 失敗——install-hooks.sh 拒絕情境未能執行（非假 PASS）"
fi

# ── [4/5] AISDLC_SDD LATEST install_post_commit.sh 於 worktree 實跑 ────────────
echo ""
echo "--- [4/5] install_post_commit.sh worktree 實跑 + 移除後路徑斷言（fake repo）---"
# 動態解析 LATEST：委派 AISDLC_SDD/scripts/sdd_version.py（R10 DEF-101-133 SSOT，
# 鏡射 ci-gate.sh 同款；fake repo 為完整 clone，tracked 過濾語意成立；python 已於
# 檔頭前置守門）。原 `ls -d ... | sort -V | tail -1` 尾端未錨定＋掃磁碟，複製品目錄
# 會汙染選版（R10 ARCH-3）。
latest_name="$(cd "$FAKE" && python AISDLC_SDD/scripts/sdd_version.py --sdd-root AISDLC_SDD || true)"
latest="AISDLC_SDD/${latest_name}"
if [ -z "$latest_name" ]; then
  fail "找不到任何 AISDLC_SDD_v* 版本目錄（fake repo）"
else
  echo "AISDLC_SDD LATEST 版：$latest"
  wt="$WORK/wt-install-post-commit"
  git -C "$FAKE" worktree add --quiet --detach "$wt" HEAD
  ( cd "$wt" && bash "$latest/tools/install_hooks/install_post_commit.sh" )
  rc=$?
  target="$(git -C "$FAKE" rev-parse --path-format=absolute --git-common-dir)/hooks/post-commit"
  step4_ok=1
  if [ "$rc" -ne 0 ]; then
    fail "install_post_commit.sh 於 worktree 執行失敗（rc=$rc）"
    step4_ok=0
  elif [ ! -x "$target" ]; then
    fail "post-commit 未正確安裝於 $target"
    step4_ok=0
  elif ! grep -q "post_commit_drift.py" "$target"; then
    fail "post-commit 缺 drift hook 路徑"
    step4_ok=0
  elif ! grep -q "closure_evidence_verify.py" "$target"; then
    fail "post-commit 缺 closure hook 路徑"
    step4_ok=0
  fi
  git -C "$FAKE" worktree remove --force "$wt"

  # 2026-07-16 P1 回歸鎖（比照 CI）：worktree 移除「後」重讀共用 hook，內嵌 .py
  # 路徑必須仍存在於磁碟（--show-toplevel 舊 bug 會在此現形）。
  if [ "$step4_ok" -eq 1 ]; then
    drift_path="$(grep -o '"[^"]*post_commit_drift\.py"' "$target" | tr -d '"' | head -1)"
    closure_path="$(grep -o '"[^"]*closure_evidence_verify\.py"' "$target" | tr -d '"' | head -1)"
    if [ -z "$drift_path" ] || [ -z "$closure_path" ]; then
      fail "worktree 移除後無法從 hook 擷取 drift/closure 路徑"
    elif [ ! -f "$drift_path" ] || [ ! -f "$closure_path" ]; then
      fail "worktree 移除後 hook 內嵌路徑已不存在於磁碟（P1 回歸重現）：drift=$drift_path closure=$closure_path"
    else
      pass "install_post_commit.sh worktree 實跑 + 移除後路徑仍有效（drift/closure）"
    fi
  fi
fi

# ── [5/5] 守門工具（唯讀，直接對本 repo）──────────────────────────────────────
echo ""
echo "--- [5/5] check_ntfs_paths.py + check_script_parity.py（本 repo，唯讀）---"
if (cd "$REPO_ROOT" && python tools/check_ntfs_paths.py); then
  pass "tools/check_ntfs_paths.py"
else
  fail "tools/check_ntfs_paths.py"
fi
if (cd "$REPO_ROOT" && python tools/check_script_parity.py); then
  pass "tools/check_script_parity.py"
else
  fail "tools/check_script_parity.py"
fi

# ── 彙總 ─────────────────────────────────────────────────────────────────────
echo ""
echo "===== 彙總：PASS=$PASS FAIL=$FAIL ====="
if [ "$FAIL" -gt 0 ]; then
  echo "失敗項目：$FAIL_LIST" >&2
  exit 1
fi
echo "全部通過 ✅（真 macOS 上請以系統 /bin/bash 3.2 執行本腳本）"
exit 0
