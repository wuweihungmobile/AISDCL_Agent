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
#   [1] bash -n active git-tracked *.sh（AISDLC_SDD 凍結版排除、LATEST 納入）
#       + 三處無副檔名 git-hooks 目錄（與 root-infra-ci.yml 第 1 道同一份
#       git ls-files 清單、同排除式、同兩段下限釘選；R56 起由原「根層 tools/
#       + 三支 dispatcher hooks」擴面對稱化，但以系統 bash 3.2 解析）
#   [2] dispatcher 直呼煙霧（比照 CI「/bin/bash 系統 bash 直接執行驗證」step；
#       fake repo 於 OS temp，絕不對本 repo 做 git config／暫存變更）
#   [3] install_git_hooks.sh / install-hooks.sh 安裝／解除往返 + linked worktree
#       拒絕（比照 CI 對應四個 step；同樣在 fake repo）
#   [4] AISDLC_SDD LATEST install_post_commit.sh 於 worktree 實跑 + 移除後路徑斷言
#       （比照 CI 對應 step，含 2026-07-16 P1 回歸鎖）
#   [5] python tools/check_ntfs_paths.py + tools/check_script_parity.py（唯讀，
#       直接對本 repo 跑）
#   [6] install_mac_nightly.sh --render-only 產 plist 至 temp + plutil -lint
#       （R13 ARCH-R13-3 隨安裝器新增；只驗 render，不做 launchctl 實載；
#       CI 對應 step 已補於 macos-compat-ci.yml macos-smoke job〔QA-R13-3〕，
#       CI 帳務停擺中、其首次真跑取證待帳務恢復）
#   [7] nightly RunId log／RunAtLoad 補跑靜態錨點（R15 DEF-101-201②＋SCAN-C-1；
#       唯讀 grep 工作樹，平台無關——非 macOS 亦驗）
#
# 限制（如實揭露）：
#   - fake repo 以 git clone 自本 repo HEAD 建立 → 未 commit 的變更不在驗證範圍
#     （worktree/clone 隔離盲區：驗證前先 commit）。
#   - 無法本地化的 CI step（bootstrap/dev_start 實跑、pytest 全套、ci-gate.sh）
#     不在本腳本範圍，見 macos-compat-ci.yml。
#
# 相容性：嚴格 bash 3.2（macOS /bin/bash，2007 凍結版；禁 declare -A / mapfile /
# ${var,,}）+ BSD 工具（禁 sed -i 無 ''、readlink -f、grep -P、stat -c、date -d、
# timeout、xargs -r、find -printf、裸 mktemp〔BSD 無預設模板，必須帶 XXXXXX〕）。
# 另禁 date 的 %N 奈秒（GNU 擴充；BSD strftime 無此格式字元，會原樣輸出字面 N 使
# `$(( END - START ))` 算術崩）——該項的判準是 tools/tests/test_bash32_compat.py 的
# `gnu_date_nanos_problems`（**不在** `_PATTERNS` 內：存量債走 shrink-only 棘輪登記，
# 見該函式 docstring）。相容手法參照 tools/git-hooks/pre-commit。
#
# 用法：bash tools/macos_smoke_local.sh
# Exit：0＝無 FAIL；1＝任一 FAIL（結尾彙總）。
# 🔴 rc=0 有兩種、收尾字樣互斥可分辨（R60 F-01）：真 macOS 為「✅ 全部通過（SKIP=0…）」；
#    非 Darwin 為「⚠️ 部分通過（本平台 … 非 Darwin）」＋ SKIP=N —— 彙總行亦帶 SKIP=N。
#    勿把非 Darwin 的 rc=0 當成 macOS 全驗完成的取證。
set -u

# 🔴 R69（DEF-101-702／R68-21）：以 zsh（macOS 預設 shell）執行本檔時 `${BASH_SOURCE[0]}`
# 未定義 → SCRIPT_DIR 解到呼叫端 cwd → guard source 失敗、is_real_python_candidate 變成
# command not found → 印出與事實相反的「❌ 找不到 python」。fail-loud 一行擋在最前面，
# 訊息直接給正確載具。（`$BASH_VERSION` 在 zsh／sh 下皆為空。）
if [ -z "${BASH_VERSION:-}" ]; then
  echo "❌ 本腳本需以 bash 執行：bash tools/macos_smoke_local.sh" >&2
  echo "   （macOS 預設 shell 是 zsh，zsh 沒有 BASH_SOURCE，直接 source/zsh 執行會把" >&2
  echo "     腳本目錄解錯，並印出與事實相反的『找不到 python』）" >&2
  exit 2
fi

# 🔴 R69（DEF-101-702／R68-19）：原本全檔零 argv 處理 —— `--help` 或任何打錯的旗標都被
# 靜默丟棄、整套 smoke 照跑到底。同族入口（bootstrap_core／integration_gate_core／
# ci-gate.sh）都已 fail-loud，本檔是最後一個沒跟上的。
_usage() {
  cat >&2 <<'USAGE'
用法：bash tools/macos_smoke_local.sh
  本腳本不接受任何旗標（涵蓋範圍固定，見檔頭「涵蓋」段）。
  -h, --help   顯示本說明
Exit：0＝無 FAIL；1＝任一 FAIL；2＝用法錯誤／載具錯誤。
USAGE
}
for _arg in "$@"; do
  case "$_arg" in
    -h|--help) _usage; exit 0 ;;
    *)         echo "❌ 未知旗標：$_arg" >&2; _usage; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 系統 bash：macOS 上明確用 /bin/bash（3.2），不依賴 PATH（可能是 Homebrew 5.x，
# 會掩蓋 3.2 相容性問題）——與 macos-compat-ci.yml 同款手法。
SYS_BASH="/bin/bash"
[ -x "$SYS_BASH" ] || SYS_BASH="bash"

# R55：WindowsApps 空殼排除 guard（純函式定義，無副作用）。雖然本腳本是
# macOS 專屬本地驗證聚合腳本，但第 [3][4] 步會在 fake repo 內以系統 bash 直呼
# tools/git-hooks/* 與 install_git_hooks.sh／install_post_commit.sh 等已知呼叫端
# 相同的 Windows Git Bash 執行情境（見上方檔頭「相容性」與 [2b] 段落註解、
# ONBOARDING.md「已於 Windows Git Bash 實跑全綠」實跑紀錄）——此前置守門本身
# 亦沿用同一慣例，改用共用 SSOT 而非裸判斷，避免在 Windows 11 + WindowsApps
# 空殼 python 情境下誤判「找到 python」。
# 🔴 R69（DEF-101-702／R68-21(b)）：source 失敗改硬錯。原本 `.` 失敗只印一行 shell 訊息
# 就繼續跑，於是 guard 整條消失而無人知——這正是「guard 消失卻無人知」的結構成因。
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/windowsapps_guard.sh" || {
  echo "❌ 無法載入 $SCRIPT_DIR/lib/windowsapps_guard.sh（WindowsApps guard 缺席）" >&2
  exit 2
}

# 前置守門：install 共用層（tools/lib/git_hooks_install_common.sh）與守門工具
# 都需要 python —— 缺席時 fail-fast（與該共用層同款訊息），勝過中段連環爆。
if ! is_real_python_candidate python; then
  echo "❌ 找不到 python — 請先 source .venv/bin/activate（見 ONBOARDING.md §3）" >&2
  exit 1
fi

PASS=0
FAIL=0
FAIL_LIST=""
# R60 F-01：SKIP-計-PASS 的獨立計數器。兩處「非 macOS 平台無法驗證」的子測試刻意
# 計為 PASS（保住 MIN_PASS 的靜默縮面偵測力，語意不動），但**必須**在收尾另外報出
# 來——否則「Windows Git Bash 實跑」與「真 macOS 全驗」在 PASS/FAIL 計數、收尾字樣
# 與 rc 三個訊號上逐字相同，事後稽核完全無從分辨（DEF-101-511/512 立的「讓結論自己
# 說出降級事實」原則，該輪未回頭套用到本檔）。刻意不併入 pass()／不新增 helper：
# tools/tests/test_smoke_ci_sync.py 的 MIN_PASS 語意鎖以「pass 加雙引號訊息」的字面
# 呼叫點計數（本行刻意不寫出那個字面樣式——寫了就會被它算成第 14 個步驟，R60 落地
# 時當場被該鎖抓到），包一層 helper 會多算一次而讓該鎖失準。
SKIPPED_AS_PASS=0

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

# ── [1/7] bash -n：active tracked .sh + 三處 git-hooks 目錄 ────────────────────
echo ""
echo "--- [1/7] bash -n 語法檢查（active tracked .sh + 三處 git-hooks 目錄；凍結版排除）---"
# heredoc 迴圈（非管線）：計數器在主 shell 累積——bash 3.2 無 lastpipe，
# 管線尾端 while 的變數變更會隨 subshell 消失（同 tools/git-hooks/pre-commit 手法）。
# R56 修正（Architect finding）：原範圍是 `find "$REPO_ROOT/tools"` + 三支根 hook
# ＝10 檔，與 root-infra-ci.yml 第 1 道本輪擴面後不對稱——新納管的 16 支子專案
# active .sh 在本地零訊號，只能燒 CI 額度才發現語法錯。改用與該 CI step 完全同一
# 份清單（`git ls-files` 同樣式、同凍結版排除式、同兩段下限釘選值），本地版的
# 不可取代價值仍在：以系統 bash 3.2（$SYS_BASH）解析，比 CI 的 ubuntu bash 5.x
# 更貼近真實 macOS 執行環境（2026-07-27 實測 29 檔在 bash 3.2 下全數通過）。
# 取捨（刻意，非疏漏）：改用 ls-files 後「完全未追蹤」的草稿 .sh 不再被掃到
# （原 find 會掃根層 tools/ 下的未追蹤檔），換得與 CI 第 1 道同一判準、且本地
# 暫存草稿不會造成假紅；新檔一經 `git add` 即入 index、立刻納入本檢查。
# 掃的是**工作樹內容**（$REPO_ROOT/$f）而非 HEAD，故未 commit 的修改仍會驗到。
# R56 二次修正（Architect/SA/SD round 3；本檔與 CI 第 1 道逐項對齊，理由詳見該
# step 內註解）：①凍結版 .sh 排除（bash -n 判定隨 bash 版本浮動，凍結版依
# Copy-on-Evolve 鐵律無合規改檔途徑 → 不納硬閘，政策與 CI 第 2 道 pwsh parse 一致；
# LATEST 委派 sdd_version.py SSOT，禁內嵌第二份版本 regex）；②下限釘選由「對總數
# 174 釘 150」（被 145 支凍結版稀釋、實測踢掉全部 6 支 git-hooks 仍綠燈）改為
# .sh 與 git-hooks 兩段各自釘實數；③補 index-vs-工作樹存在性守衛（見下方）；
# ④補 `-c core.quotePath=false`（非 ASCII 檔名預設輸出為引號包裹＋八進位逸出形，
# 逐行讀時路徑帶引號會使 `[ -f ]` 與 bash -n 皆指向不存在的路徑——本 repo 已在
# root-infra-ci.yml 第 3 道明文記載過此病灶 SD-R13-6。本檔逐行讀而非 -z：bash 3.2
# 無法安全處理 NUL 分隔的 heredoc，quotePath=false 已足以消除該已知病灶）。
sdd_latest="$(python "$REPO_ROOT/AISDLC_SDD/scripts/sdd_version.py" \
  --sdd-root "$REPO_ROOT/AISDLC_SDD" 2>/dev/null || true)"
sh_files="$(git -C "$REPO_ROOT" -c core.quotePath=false ls-files -- '*.sh' 'tools/git-hooks/*' \
  'AutoClaude/tools/git-hooks/*' 'AISDLC_SDD/.githooks/*')"
syntax_bad=0
syntax_sh=0
syntax_hook=0
syntax_frozen=0
syntax_gone=0
if [ -z "$sdd_latest" ]; then
  fail "AISDLC_SDD LATEST 解析失敗（sdd_version.py 無輸出）——掃描邊界不得靜默縮小"
  syntax_bad=1
fi
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # 凍結版排除（LATEST 保留）。$sdd_latest 為空時上方已 fail，此處不再靜默縮面。
  case "$f" in
    AISDLC_SDD/AISDLC_SDD_v*/*)
      case "$f" in
        "AISDLC_SDD/${sdd_latest}/"*) ;;
        *) syntax_frozen=$((syntax_frozen + 1)); continue ;;
      esac
      ;;
  esac
  case "$f" in
    *.sh) syntax_sh=$((syntax_sh + 1)) ;;
    *) syntax_hook=$((syntax_hook + 1)) ;;
  esac
  # git ls-files 列的是 **index**：工作樹已 rm 但尚未 git rm 的檔案仍在清單內，
  # 而 `bash -n <缺檔>` 回 rc=127 → 下方 `if !` 會誤報成「語法檢查失敗」，把
  # 「檔案不存在」講成「語法錯誤」誤導重構中的開發者（R56 SA/SD 各自實機重現；
  # R56 前的 `find` 只列磁碟實存檔，結構上免疫，是本輪擴面新引入的失效模式）。
  # 刻意在計數**之後**才跳過：下限釘選守的是「ls-files 樣式有沒有被改壞」，
  # 若把未 commit 的刪除也扣掉，大量刪除會把計數壓破下限而變成另一種假紅。
  if [ ! -f "$REPO_ROOT/$f" ]; then
    echo "  ⓘ 略過 ${f}（index 內但工作樹不存在，尚未 git rm）"
    syntax_gone=$((syntax_gone + 1))
    continue
  fi
  if ! "$SYS_BASH" -n "$REPO_ROOT/$f"; then
    fail "bash -n 語法檢查失敗：${f}"
    syntax_bad=1
  fi
done <<EOF_SH
$sh_files
EOF_SH
echo "  掃描面：active .sh ${syntax_sh} 檔 + 無副檔名 git-hooks ${syntax_hook} 檔"
echo "  （凍結版排除 ${syntax_frozen} 檔；index 內但工作樹不存在 ${syntax_gone} 檔）"
# 下限釘選（鏡射 CI 第 1 道同款保護，且釘選值必須與該 step 逐字相同——由
# tools/tests/test_smoke_ci_sync.py 機械互鎖）：ls-files 樣式被改壞／目錄搬家時
# 掃描面靜默縮小，syntax_bad=0 仍會 PASS——與本檢查存在的目的直接矛盾。
if [ "$syntax_sh" -lt 23 ]; then
  fail "active .sh 掃描面異常縮小（僅 ${syntax_sh} 檔，現況應 ≥23）——'*.sh' 樣式或凍結版排除式疑似被改壞"
  syntax_bad=1
fi
if [ "$syntax_hook" -lt 6 ]; then
  fail "無副檔名 git-hooks 掃描面異常縮小（僅 ${syntax_hook} 檔，現況應 ≥6）——三處 git-hooks 樣式疑似被改壞"
  syntax_bad=1
fi
if [ "$syntax_bad" -eq 0 ]; then
  pass "bash -n 全數通過（active .sh ${syntax_sh} + git-hooks ${syntax_hook} 檔）"
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
  echo "===== 彙總：PASS=$PASS FAIL=$FAIL SKIP=$SKIPPED_AS_PASS =====$FAIL_LIST"
  exit 1
fi

# ── [2/7] dispatcher 直呼煙霧（比照 CI /bin/bash 直接執行 step）────────────────
echo ""
echo "--- [2/7] dispatcher 直呼煙霧（$SYS_BASH 直接執行，fake repo）---"
(
  cd "$FAKE" || exit 9

  # 2a. pre-commit：乾淨變更應放行
  # R56 修正（與 macos-compat-ci.yml 同步）：原探針是根層 `_ci_probe_clean.txt`，
  # pre-commit 六個分流 pattern 全部不命中 → run_root_infra=0，A4 根層基建 leg
  # （dispatcher 內唯一含 while read / heredoc / 巢狀 case 的區塊）從未在系統
  # bash 3.2 下執行過，本子測試對它的覆蓋宣稱落空。改用 tools/*.sh 探針使 leg
  # 必定觸發，並斷言 leg 識別訊息真的出現。
  printf '#!/usr/bin/env bash\necho ok\n' > tools/_ci_probe_clean.sh
  git add tools/_ci_probe_clean.sh
  out2a="$("$SYS_BASH" tools/git-hooks/pre-commit 2>&1)"
  rc=$?
  printf '%s\n' "$out2a"
  git reset -q tools/_ci_probe_clean.sh
  rm -f tools/_ci_probe_clean.sh
  [ "$rc" -eq 0 ] || exit 1
  case "$out2a" in
    *"變更含根層基建"*) ;;
    *) exit 6 ;;
  esac

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
  5) SKIPPED_AS_PASS=$((SKIPPED_AS_PASS + 1))
     pass "dispatcher 直呼煙霧（pre-commit 放行、post-commit、pre-push 刪除跳過；NTFS 保留名子測試 SKIP——非 macOS 平台先擋）" ;;
  1) fail "pre-commit dispatcher 對乾淨變更應 exit 0" ;;
  2) fail "pre-commit dispatcher 應擋下 NTFS 保留裝置名（CON.txt）卻放行" ;;
  3) fail "post-commit dispatcher 應恆 exit 0" ;;
  4) fail "pre-push dispatcher 刪除分支跳過路徑應 exit 0" ;;
  6) fail "pre-commit dispatcher 未觸發 A4 根層基建 leg（探針失效——2a 的系統 bash 覆蓋宣稱落空）" ;;
  *) fail "dispatcher 直呼煙霧異常中斷（rc=${sub_rc}）" ;;
esac

# ── [3/7] hooks 安裝／解除往返 + linked worktree 拒絕 ─────────────────────────
echo ""
echo "--- [3/7] install_git_hooks.sh / install-hooks.sh 往返 + worktree 拒絕（fake repo）---"

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
  *) fail "install_git_hooks.sh 往返驗證異常中斷（rc=${sub_rc}）" ;;
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
  fail "install-hooks.sh 安裝後 core.hooksPath 未設定或安裝失敗（rc=${sub_rc}）"
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

# ── [4/7] AISDLC_SDD LATEST install_post_commit.sh 於 worktree 實跑 ────────────
echo ""
echo "--- [4/7] install_post_commit.sh worktree 實跑 + 移除後路徑斷言（fake repo）---"
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
    fail "install_post_commit.sh 於 worktree 執行失敗（rc=${rc}）"
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

# ── [5/7] 守門工具（唯讀，直接對本 repo）──────────────────────────────────────
echo ""
echo "--- [5/7] check_ntfs_paths.py + check_script_parity.py（本 repo，唯讀）---"
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

# ── [6/7] install_mac_nightly.sh --render-only plist 產出＋plutil -lint ────────
echo ""
echo "--- [6/7] install_mac_nightly.sh --render-only plist 產出＋plutil -lint ---"
# R13 ARCH-R13-3：只驗 render＋plutil -lint，絕不做 launchctl 實載（真安裝屬
# 使用者 ops）。非 macOS（無 launchd/plutil，安裝器依設計 fail-loud exit 1）時
# 明確 SKIP-計-PASS（比照 [2] NTFS 子測試慣例，不偽裝成已驗）。
if [ "$(uname)" = "Darwin" ]; then
  plist_out="$WORK/com.autoclaude.nightly.plist"
  # R14 QA-R14-REV-4：lint 之外加驗 log 落點內容——plist 範本若回退 /tmp
  #（macOS 週期清理會毀取證，DEF-101-201），純語法 lint 照綠、零訊號。
  if "$SYS_BASH" "$REPO_ROOT/tools/install_mac_nightly.sh" --render-only "$plist_out" \
      && plutil -lint "$plist_out" >/dev/null \
      && grep -q "AutoClaude/logs/nightly_mac_launchd.log" "$plist_out"; then
    pass "install_mac_nightly.sh --render-only plist 產出＋plutil -lint＋log 落點斷言"
  else
    fail "install_mac_nightly.sh --render-only 產出、plutil -lint 或 log 落點斷言失敗"
  fi
else
  echo "  （SKIP）非 macOS 無 launchd/plutil——plist render 驗證待真 macOS 實跑"
  SKIPPED_AS_PASS=$((SKIPPED_AS_PASS + 1))
  pass "install_mac_nightly.sh --render-only（SKIP-計-PASS：非 macOS）"
fi

# ── [7/7] nightly RunId log／RunAtLoad 補跑靜態錨點（R15，唯讀）───────────────
echo ""
echo "--- [7/7] nightly RunId log／RunAtLoad 補跑靜態錨點（R15，唯讀 grep 工作樹）---"
# R15：DEF-101-201②（RunId log 對等）＋SCAN-C-1（RunAtLoad 補跑＋當日去重）以靜態
# 錨點鎖住——任一錨點消失＝機制被靜默移除。直接 grep 本 repo 工作樹（非 fake repo
# clone），未 commit 變更亦在驗證範圍；平台無關。
# SA-R15-REV-6 觀察：本組錨點刻意只入本地 smoke，無 macos-compat-ci.yml 對應 CI
# step（帳務停擺中新增雲端 step 目前無法驗證；根 unittests 亦不覆蓋，屬本地專屬
# 防線，非遺漏——待 CI 帳務恢復後評估補齊雲端對應）。
# QA-R15-REV-1 訂正：原始 grep -qF 對整檔做子字串比對——實測把功能碼
# `-mtime +14` 改壞成 `-mtime +30`、但保留同名舊註解字樣時，五錨點仍全綠
# （假陽性）。改為「先剝除整行註解（`^[[:space:]]*#` 起頭的行，跨 BSD/GNU
# grep 相容，非 `\s` GNU 專屬類別）再比對」，比照
# tools/tests/test_workflow_schedule_sync.py SCAN-C-9 剝註解手法，錨點只認
# 功能碼行。
NIGHTLY_SH="$REPO_ROOT/AutoClaude/tools/run_local_nightly.sh"
MAC_INSTALLER="$REPO_ROOT/tools/install_mac_nightly.sh"
NIGHTLY_SH_CODE="$(grep -v '^[[:space:]]*#' "$NIGHTLY_SH")"
if echo "$NIGHTLY_SH_CODE" | grep -qF 'exec >>' \
    && echo "$NIGHTLY_SH_CODE" | grep -qF 'nightly_mac_2*.log' \
    && echo "$NIGHTLY_SH_CODE" | grep -qF -- '-mtime +14' \
    && echo "$NIGHTLY_SH_CODE" | grep -qF -- '--force' \
    && echo "$NIGHTLY_SH_CODE" | grep -qF 'RunAtLoad 補跑去重'; then
  pass "run_local_nightly.sh RunId log／14 天輪替／當日去重五錨點齊備（功能碼行，非註解）"
else
  fail "run_local_nightly.sh 缺 RunId log／輪替／去重錨點（exec >>・nightly_mac_2*.log・-mtime +14・--force・去重行；功能碼行）"
fi
if grep -qF '<key>RunAtLoad</key><true/>' "$MAC_INSTALLER"; then
  pass "install_mac_nightly.sh plist heredoc 含 RunAtLoad（關機錯過補跑窗口）"
else
  fail "install_mac_nightly.sh plist heredoc 缺 <key>RunAtLoad</key><true/>——關機錯過補跑窗口被移除"
fi

# ── 彙總 ─────────────────────────────────────────────────────────────────────
# R10 二審 QA 觀察項：PASS 下限釘選（比照 run_root_unittests MIN_TESTS 精神）——
# 只斷言 FAIL==0 時，驗證段落被整段刪除仍 exit 0（靜默縮面）；PASS 低於下限即紅。
# 刻意刪減驗證項時同步下修本值（現況滿版 PASS=13——R13 [6] plist render 步、
# R15 [7] RunId log／RunAtLoad 靜態錨點兩步入列；含非 macOS 平台 NTFS／plist
# 兩子測試的 SKIP-計-PASS 分支）。
MIN_PASS=13
if [ "$PASS" -lt "$MIN_PASS" ]; then
  fail "PASS 總數 ${PASS} 低於下限 ${MIN_PASS}——驗證段落疑似被刪減（靜默縮面）"
fi
echo ""
echo "===== 彙總：PASS=$PASS FAIL=$FAIL SKIP=$SKIPPED_AS_PASS ====="
if [ "$FAIL" -gt 0 ]; then
  echo "失敗項目：$FAIL_LIST" >&2
  exit 1
fi
# R60 F-01：收尾結論必須讓「本平台無法驗證的項目數」外顯。改法刻意只動輸出面
# （不動 PASS 計數、不動 MIN_PASS 語意），使兩種綠燈在字樣上互斥可分辨：
#   非 Darwin：⚠️ 部分通過（本平台跳過 N 項）…  ← 不再出現「全部通過 ✅」
#   真 macOS ：✅ 全部通過（SKIP=0，本平台已實際驗證全部 N 項）
# 鎖：tools/tests/test_macos_smoke_skip_honesty.py。
if [ "$SKIPPED_AS_PASS" -gt 0 ]; then
  echo "⚠️ 部分通過（本平台 $(uname) 非 Darwin）：FAIL=0，但其中 ${SKIPPED_AS_PASS} 項"
  echo "   本平台無法驗證、以 SKIP-計-PASS 計入 PASS ——【本結果不等於 macOS 全驗完成】；"
  echo "   真 macOS 上請以系統 /bin/bash 3.2 重跑本腳本取得 SKIP=0 的完整取證。"
  exit 0
fi
echo "✅ 全部通過（SKIP=0，本平台已實際驗證全部 ${PASS} 項；真 macOS 上請以系統 /bin/bash 3.2 執行本腳本）"
exit 0
