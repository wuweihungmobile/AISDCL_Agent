# R80 包 F — mac／POSIX 側落差：實測證據檔

> 本檔是 R80 包 F（舵手訴求 3：「在 Windows 開發時 mac 不能有落差」）的具名證據檔。
> 缺陷帳本列只放索引與指針，細節逐字保全於此。
>
> **量測環境**：Windows 11 Pro（**R80 當輪**本機無 mac 真機——平台覆蓋是輪次屬性、不是常數，
> 見 ADR-XPLAT-002 §6 邊界 1）、Docker server 29.5.3、
> `bash:3.2`（`GNU bash, version 3.2.57(1)-release`，與 macOS 內建 `/bin/bash` 逐字同版）、
> `koalaman/shellcheck:stable`、repo 根 `D:\CursorProject\AISDCL_Agent`。
>
> 🔴 **誠實劃界（貫穿全檔）**：容器跑的是 Linux（GNU coreutils／musl），
> **Linux 綠不蘊含 mac 綠**。本檔每一節都標注結論屬「Linux 已驗」還是「mac 推論」還是
> 「只能在 mac 真機驗」。唯一可以外推到 mac 的是 **bash 3.2 語言層**（同版直譯器）
> 與 **shellcheck 靜態分析**（純靜態、與平台無關）。

---

## S8-01 — `init_project.sh` 的 `--help` 教 `./init_project.sh`，而索引模式是 100644

### 缺陷（before：當回合實測，非引用）

從 **HEAD** 取出該檔並在 bash 3.2 容器內照著它自己印的用法跑：

```
git archive -o head.tar HEAD 'AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh'
docker run --rm -v <scratchpad>:/in:ro bash:3.2 bash -c '... ./init_project.sh -h ...'
-rw-rw-r--    1 root     root         17566 init_project.sh
ADVERTISED_FORM_RC=126
bash: ./init_project.sh: Permission denied
```

該檔第 42 行逐字 `echo -e "  ./init_project.sh [選項]"`（另 :67/:70/:73 三處同形態）。
它是框架的**安裝入口** ⇒ mac/Linux 使用者第一步就撞牆。

### 修法（走 git index，不動內容）

```
git update-index --chmod=+x AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh
git ls-files -s AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh
100755 8e3489b234635f595aa370b72550ef4148b6c5a2 0  AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh
```

**為何走索引而不是改文案**：① Windows 的 NTFS 沒有 exec bit，工作樹改不動它，
`git update-index --chmod` 是唯一通道（本 repo 既有體例，
`tools/tests/test_platform_neutral_paths.py::TestExecBitIsGovernedViaTheGitIndex` 在守）；
② 只改模式不改 blob ⇒ 不碰任何 hash 釘選（該檔在 `check_script_parity.py` 登記為
`LATEST/tools/init_project` → `tier3_os_primitive`，本來就不受 hash 釘選，但仍以不動內容為佳）。

### 修後（after：同一條指令、同一個容器）

```
git write-tree                       -> fce5aaf7a856794cd14a9d970b76afe4a722db0b
git archive -o idx.tar <tree> AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh
-rwxrwxr-x    1 root     root         17566 init_project.sh
ADVERTISED_FORM_RC=0
7:  ./init_project.sh [選項]
```

（用 `git write-tree` + `git archive` 取索引樹：本輪禁止 commit，而 `git clone` 只看得到
HEAD ⇒ 不用這條路就驗不到「已修好」，只能宣稱「應該好了」。）

### 補的鎖

`tools/check_script_parity.py::_check_self_help_advertises_executable_form`
（純函式 `self_help_offenders()` 供合成輸入注入）。

判準：**凡一支 shell 腳本的內文出現「以 `./` 直呼它自己」的形態，它的 git 索引模式就必須是
100755**。刻意只判「自己呼叫自己」——腳本裡指向別支腳本的 `./x.sh` 多半在講讀者自己專案的
檔案（沿用既有 `resolve_doc_script()` 的假紅取捨）。

**為何非補不可**：既有的那道鎖（`TestExecBitIsGovernedViaTheGitIndex::
test_docs_that_teach_bare_sh_invocation_point_at_executable_files`）只掃 **`.md` 文件**裡的
`./x.sh`。腳本**自己的 `--help` 輸出**不是 `.md`，結構上不在它的射程內 ⇒ 同一個危害、
兩個掃描面，只有一面有人守。本次補的是另一面，判準逐字同構。

紅綠自證（當回合實測）：

```
git update-index --chmod=-x ...init_project.sh ; python tools/check_script_parity.py
parity_rc_when_reverted=1
❌ 自述用法 ↔ exec bit 鎖：腳本自己的說明教人跑 `./x.sh`，但它的 git 索引模式不是 100755 …
git update-index --chmod=+x ...init_project.sh ; python tools/check_script_parity.py
rc=0
✅ 自述用法 ↔ exec bit 鎖：活版 0 筆違規（凍結版可見欠債 116 筆）
```

### 凍結版欠債（**沒有修**，誠實登記）

`_SELF_HELP_DEBT_FROZEN = 116` ＝ 29 支 `init_project.sh`（v0.01~v0.29）× 各 4 個站點。
判準是**雙向精確比對**：多一筆＝有人把同型缺陷複製進凍結版；少一筆＝有人動了
Copy-on-Evolve 禁改的凍結版（那本身就是必須被看見的事件）。體例逐字抄既有的
`_BARE_SH_DOC_DEBT_FROZEN = 87`。

⚠️ **這代表 v0.01~v0.29 任一凍結版在 mac 上仍會踩到同一個 rc=126**，而
`init_project.sh` 的 `--sdd` 預設版本正是 `0.01`。修它需要 Copy-on-Evolve 例外授權
（歷來三次例外都經掌舵者明文核准），**不在本包射程內**，列入交棒。

---

## S8-02 — shellcheck 全庫零接電，卻有 23 處 `# shellcheck disable=` 指令

### 缺陷

`# shellcheck disable=` 在全庫命中 **23 處 / 19 支檔**（Grep 工具實測，已排除缺陷帳本）：

```
tools/bootstrap.sh:1            tools/integration_gate.sh:1     tools/macos_smoke_local.sh:1
tools/git-hooks/pre-push:2      tools/dev_start.sh:3            tools/lib/git_hooks_install_common.sh:1
AutoClaude/tools/sd06_w3_staging_dryrun.sh:1  AutoClaude/tools/run_act.sh:1
AutoClaude/tools/local_ci_gate.sh:1           AutoClaude/tools/install_git_hooks.sh:1
AISDLC_SDD/scripts/install-hooks.sh:1         AISDLC_SDD/scripts/copy_on_evolve.sh:1
AISDLC_SDD/scripts/ci-gate.sh:1               AutoClaude/tools/git-hooks/pre-push:2
AutoClaude/tools/git-hooks/pre-commit:1       …（共 19 檔）
```

而 `.github/` 對 `shellcheck` 的命中數在本包落地前是 **0** ⇒ 那些 disable 指令從來沒有被
任何東西讀過。作者們**相信它在跑**並為它寫了豁免。這是本 repo 反覆判過的形態：
「政策有宣告、卻沒有任何機械物在執行它」。

### 規模量測（先量再決定，不是先開再說）

掃描面＝**active（非凍結）**tracked shell script：所有 `*.sh` ＋ 三處 git-hooks 目錄裡帶
shell shebang 的無副檔名檔，共 **29 支**。凍結版 145 支刻意排除（Copy-on-Evolve 禁改，
納管只會製造修不了的紅；政策與 `root-infra-ci.yml` 第 1 道 `bash -n` 既有射程一致）。

`koalaman/shellcheck:stable -f gcc` 四個嚴重度逐級實測（落地前）：

| `-S` | rc | findings | 檔數 |
|---|---|---|---|
| error | 1 | 1 | 1 |
| warning | 1 | 13 | 7 |
| info | 1 | 20 | 11 |
| style | 1 | 20 | 11 |

⇒ **規模很小，不需要「只擋新增」的軟啟動**，直接全開 `-S warning` ＋ 存量基線即可。
`info`／`style` 只多 7 筆、且全是風格建議，納管它們會把「新缺陷」的訊號稀釋在噪音裡，
故本輪門檻定在 `warning`（含 error）。**沒有為了讓數字好看而放寬任何東西。**

### 接電當回合就抓到真缺陷（這才是它值得存在的證據）

`-S error` 的唯一一筆與 `-S warning` 的其中一筆，正是本包另外兩個發現：

```
tools/lib/git_hooks_install_common.sh:1:1: error: Tips depend on target shell and yours is
  unknown. Add a shebang or a 'shell' directive. [SC2148]
AutoClaude/tools/run_mutmut_in_docker.sh:184:12: warning: This $? refers to echo/printf,
  not a previous command. Assign to variable to avoid it being overwritten. [SC2320]
```

後者就是 S8-03。**也就是說：如果 shellcheck 早就接電，S8-03 根本不會存在。**

### 落地

* `tools/run_shellcheck.py`（新增）— 載具優先序：PATH 上的 `shellcheck` → `docker run
  koalaman/shellcheck:stable` → **兩者皆無時 rc=2 fail-loud**（刻意不 skip：「找不到工具
  就當通過」正是本檔在治的假綠）。
* `.github/workflows/shellcheck-ci.yml`（新增）— push／PR（paths 過濾）＋ `workflow_dispatch`。

**為何不併進 `root-infra-ci.yml`（誠實劃界，非疏忽）**：該 workflow 的 root-infra job 受
`tools/tests/test_root_infra_parity.py` 雙向鎖管——凡在其中以 `python3 tools/*.py` 形態出現的
守門，**必須同時接進 `tools/git-hooks/pre-push` 的快層守門迴圈**（任何 push 皆跑）。
實測：把 step 加進去之後該檔立刻三紅
（`test_ci_python_guards_all_wired_in_pre_push`／`test_header_guard_list_tool_names_match_steps`／
`TestCountFloorsDoNotDriftBehindReality::test_no_floor_lags_reality_by_the_slack_limit`，
後者訊息逐字 `_FLOOR_CI_PYTHON_TOOLS：現查 11、已釘 9`）。
而本閘門的載具是 shellcheck 或 docker，放進每一次 push 的必經路徑等於讓沒有這兩者的機器
一律 push 不了。⇒ 本輪選擇「先接電、先看得見」，**本機零接線**是已知缺口、列入交棒，
**不宣稱本地已有對等防線**。

### 基線的形狀：雙向棘輪，不是豁免清單

`_BASELINE` 是 `{"<路徑>::<SCxxxx>": 筆數}`，落地當下 **11 筆**（修掉 SC2148 與 SC2320 之後）：

```
AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.sh::SC1090  1
AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/formal/run_tlc.sh::SC1090       1
AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh::SC2011                     4
AutoClaude/tools/sd06_w3_staging_dryrun.sh::SC2034                            1
tools/git-hooks/pre-push::SC2034                                              1
tools/git-hooks/pre-push::SC2254                                              1
tools/lib/git_hooks_install_common.sh::SC2034                                 2
```

第二向（**基線變小也紅**）刻意存在：只擋「變多」的表會在債被修掉之後靜默保留一個過期
豁免，下一個人再犯同一筆時它會被當成「本來就在基線裡」放行。棘輪只准往下走。

紅綠自證（當回合實測，`baseline_problems()` 純函式 ＋ 真實掃描結果）：

```
live findings: 11 via docker
A) live vs live baseline -> GREEN
B) a NEW finding appears -> ❌ 新增 shellcheck 缺陷 …run_self_evolution.sh::SC1090
C) baseline went STALE   -> ❌ 基線已過期 …run_self_evolution.sh::SC1090：基線 2 …
D) shellcheck on the PRE-FIX form: rc=1
   old.sh:7:12: warning: This $? refers to echo/printf, not a previous command … [SC2320]
```

D 那一格是端到端證據：把 S8-03 **修復前**的寫法還原成一支合成腳本餵給同一個容器，
shellcheck 確實 rc=1 並逐字指出它 ⇒ 這道鎖對 S8-03 這一類**真的有牙**，不是裝飾。

閘門現況：

```
python tools/run_shellcheck.py
rc=0
shellcheck（載具=docker，-S warning）：11 筆 / 基線 11 筆
✅ 與基線一致（無新增、無過期）
```

---

## S8-03 — `run_mutmut_in_docker.sh` 的 `RESULTS_RC=$?` 恆為 0

### 缺陷

原始碼（修復前 :183-184）：

```bash
} >> "${LOG_FILE}"
RESULTS_RC=$?
```

該複合區塊的最後一個指令是 `echo "--- mutmut full counts (end) ---"` ⇒ `$?` 讀到的是那個
echo 的 rc，**恆為 0**。真正該取的 `mutmut results` rc（區塊中段）被中間三個 echo 蓋掉。
下一行 `echo "[run_mutmut_in_docker] log written exit=${RESULTS_RC}"` 因此永遠報 0。

bash 3.2 最小重現（當回合實測，與 macOS 內建 bash 同版）：

```
OLD() { { echo a; false; echo b; } >> /tmp/o.log; echo "OLD_RC=$?"; }
NEW() { R=0; B=0; { echo a; false; R=$?; echo b; } >> /tmp/o.log; B=$?; … }
OLD_RC=0
NEW_RC=1
```

**PowerShell 側的同型缺陷（讀 rc 前接管線）早就有 PreToolUse hook 硬擋
（`.claude/hooks/lint_powershell_command.py`），POSIX 側在本包之前一道都沒有。**

### 修法

在**緊貼**受測指令的下一行落地它的 rc；區塊本身的 rc（重導向開檔失敗才會非零）另存；
最後取「先非零者」。`set -uo pipefail` 生效中，故兩個變數都先初始化。

`BLOCK_RC=$?` 那一行留了 `# shellcheck disable=SC2320` ＋ 逐字理由——那一筆是**刻意**的
（複合區塊的 rc 依定義就是最後一個指令的 rc，本行要的正是「重導向本身有沒有失敗」
這個唯一還測得到的訊號）。**R80 起 shellcheck 真的會跑，所以這個 disable 不是裝飾。**

語法驗證（bash 3.2 容器）：`bash -n AutoClaude/tools/run_mutmut_in_docker.sh` → `rc=0`。

### 補的鎖

**`$?` 不得跨過中間指令讀取」的判準＝ shellcheck 的 SC2319/SC2320，本包已接電**
（見 S8-02 的 D 格端到端證據）。刻意**不**另寫一支正則掃描器：同一份判準住兩個家、
只有一個家會被人維護，正是本 repo 判過的 `DEF-101-778` 形態。

---

## S8-06 — `tools/lib/git_hooks_install_common.sh` 無 shebang ⇒ 整支檔落在 lint 盲區

全庫 168 支 tracked `.sh` 中**唯一**沒有 shebang 的一支。shellcheck 判 **SC2148 error**
（`-S error` 的唯一一筆）。今天不會炸（它只被 `source`），但代價是：shellcheck 因不知方言，
對這支檔的**所有其他判準一併降級** ⇒ 它實質上處於 lint 盲區。

修法：檔首加 `# shellcheck shell=bash`（**不是**加 shebang——加 shebang 會誤示它可直接執行）。
修後 `-S error` findings 由 1 → **0**；`bash -n` rc=0。

---

## BSD vs GNU 逐支掃描（active shell scripts）

**22 個類別 × 29 支 active 腳本 ⇒ 命中 0。**（掃描時已剔除純註解行。）

載具自驗（先驗載具再信結論）：22 條 regex 各餵一個已知該命中的合成樣本
（`sed -i 's/a/b/' f.txt`、`readlink -f "$0"`、`base64 -w0 payload.bin`…），
結果 `PATTERNS 22  POSITIVE_CONTROL_FAILURES 0  VERDICT ALL_PATTERNS_HAVE_TEETH`
⇒ 「0 命中」不是因為 regex 恆不命中。

涵蓋的 22 類（逐筆列出，命中皆為 0）：
`sed -i`（BSD 需 `-i ''`）／`readlink -f`（BSD 無）／`date -d|--date`（GNU only）／
`date -r`／`stat -c`（GNU；BSD 是 `-f`）／`base64 -w`（BSD 無）／`grep -P`（BSD 無）／
`realpath`（舊 macOS 無）／`mktemp -p|--tmpdir`（GNU only）／`xargs -r`（BSD 無）／
`find -printf`（BSD 無）／`sha256sum`（BSD 用 `shasum -a 256`）／`md5sum`（BSD 用 `md5`）／
`nproc`（BSD 用 `sysctl`）／`tac`（BSD 用 `tail -r`）／`sed -r`（BSD 用 `-E`）／
`cp --parents`（BSD 無）／`head|tail -c <N>k`（尾綴語意差異）／`ls --time-style`（GNU only）／
`getopt --long`（GNU 增強版）／`timeout`（BSD 需 coreutils）／`readarray|mapfile`（bash 4+）。

🔴 **這一節的結論只能是靜態的**：Linux 容器裡永遠是 GNU coreutils（或 musl 的 busybox），
**掃不到違規 ≠ BSD 上跑得過**。本節的價值是「今天沒有已知違規形態」，不是「mac 上會過」。

🔴 **這 22 類目前沒有任何機械物在守**（本包沒有落地它，理由見交棒）。

---

## 只能在 mac 真機驗證的清單（交棒）

以下項目在 Windows ＋ Linux 容器上**結構上**驗不了，任何「已驗」宣稱都是假的：

1. **BSD coreutils 的執行期行為** — `sed -i`／`stat`／`date`／`base64`／`readlink` 等的
   BSD 版旗標與輸出格式。上一節的靜態掃描只能證明「沒有已知的危險形態」。
2. **`launchd` / `plutil`** — `tools/macos_smoke_local.sh` 的 `[6/7]` 在非 macOS 一律 SKIP，
   逐字 `（SKIP）非 macOS 無 launchd/plutil——plist render 驗證待真 macOS 實跑`。
3. **macOS 檔案系統語意** — HFS+/APFS 的大小寫不敏感（預設）、Unicode NFD 正規化檔名、
   資源分支／`._*` 檔。Linux 容器是 ext4/overlayfs，行為相反。
4. **macOS 系統 bash 的實際路徑綁定** — 凍結版 `verify_traceability.sh` 的 shebang 是
   `#!/bin/bash`（不是 `env bash`）⇒ 在 mac 上**無條件**綁到 3.2，連 Homebrew bash 5 都繞不過。
   容器裡沒有這個「兩個 bash 並存、shebang 決定用哪個」的環境。
5. **Gatekeeper／quarantine 屬性** — 下載取得的腳本帶 `com.apple.quarantine`，
   對 `curl … | bash` 這條安裝路徑的影響。
6. **`macos-compat-ci.yml` 的 2 個 job / 29 個 step** — act 對 `runs-on: macos-latest`
   印 `Skipping unsupported platform` 卻**回 rc=0**（S8-03 掃描員原編號那一筆），
   `.actrc` 的 `-P` 映射只有三個 ubuntu 鍵。本機零通道。

---

## 交棒（本包**沒有**做的事，逐條說明為什麼）

| # | 項目 | 為什麼本包沒做 |
|---|---|---|
| T-1 | 把 `tools/run_shellcheck.py` 接進 `tools/git-hooks/pre-push` 快層 ＋ `root-infra-ci.yml` | 需同時改 `pre-push`、`root-infra-ci.yml` 檔頭守門清單、以及 `tools/tests/test_root_infra_parity.py` 的 `_FLOOR_CI_PYTHON_TOOLS`（9→11）與「N 支守門工具」中文計數宣稱。三者都不在本包持有面，並行輪次動它們會造成假紅。**且需先決定**：docker/shellcheck 缺席時要讓 push 直接紅嗎？ |
| T-2 | 把上節 22 類 BSD/GNU 形態做成機械物 | 正確的家是 `tools/tests/test_bash32_compat.py` 的 `_PATTERNS`，而它與 `tools/macos_smoke_local.sh` 檔頭的散文禁令清單由 `TestProseBanListIsFullyMechanised` **雙向**綁定 ⇒ 必須同一次改兩側。同時 `tools/tests/` 這一層受淨行數棘輪管（`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`），新增 22 條 regex 需在同一次變更內刪等量以上的行。兩個約束都跨出本包持有面。現成的 pattern 表與正控樣本見本檔上一節，落地成本很低。 |
| T-3 | 凍結版 v0.01~v0.29 的 `init_project.sh` exec bit（116 個站點） | Copy-on-Evolve 禁改凍結版，歷來三次例外都經掌舵者明文核准。已登記為可見欠債（`_SELF_HELP_DEBT_FROZEN = 116`，雙向精確比對），不是豁免。**附帶風險**：`init_project.sh` 的 `--sdd` 預設版本是 `0.01`，正好指向壞的那一批。 |
| T-4 | 凍結版 29 支 `verify_traceability.sh` 的 `declare -A`（bash 3.2 無關聯陣列） | 同 T-3 的 Copy-on-Evolve 邊界。LATEST(v0.30) 已改用「名稱\|模式」平行清單、已修好；`tools/tests/test_bash32_compat.py` 檔頭逐字宣告「凍結版 v0.01~v0.2X 依鐵律不掃、也不可修」⇒ 現行鎖是**正確地**綠。 |
| T-5 | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh` 的 4 筆 SC2011（`ls \| grep`） | 真缺陷（含空白／換行的檔名會壞），但改動 LATEST 版下載流程屬另一個授權面。已入 shellcheck 基線（可見、只准變小）。 |

---

## 本包動到的檔（持有面內）

| 檔 | 動作 |
|---|---|
| `AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh` | **只改 git 索引模式** 100644 → 100755（內容零變更） |
| `AutoClaude/tools/run_mutmut_in_docker.sh` | S8-03 修復（rc 緊貼落地）＋ 一筆有理由的 `# shellcheck disable=SC2320` |
| `tools/lib/git_hooks_install_common.sh` | S8-06 修復（檔首加 `# shellcheck shell=bash`） |
| `tools/check_script_parity.py` | 新增 `_check_self_help_advertises_executable_form()` ＋ 純函式 `self_help_offenders()` ＋ `_SELF_HELP_DEBT_FROZEN` |
| `tools/run_shellcheck.py` | 新增（shellcheck 驅動器 ＋ 雙向基線棘輪） |
| `.github/workflows/shellcheck-ci.yml` | 新增（shellcheck 的第一個雲端執行者） |
