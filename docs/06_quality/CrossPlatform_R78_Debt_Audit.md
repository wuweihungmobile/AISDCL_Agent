# CrossPlatform_R78_Debt_Audit — 缺陷帳本未結列逐筆實查（R78 技術債清除）

> **本檔為什麼屬於「具名治理文件」**：它承擔與缺陷帳本主檔同等的義務——複審者要逐條重驗
> 本輪的結案判定，就得讀完它；它逐筆寫出「某缺陷在今天的磁碟上是什麼狀態」的宣稱。
> 故已登記進 `tools/check_defect_log_crossref.py` 的 `_GOVERNANCE_DOCS`，同時受體積守門與
> 指針稽核管轄（登記與否不是喜好，是資格判斷，見該常數上方 WHY）。

**動工前基線（當回合實測）**：`python tools/check_defect_log_crossref.py --unresolved-count`
→ `未結列數＝85／全部 108 列｜warn=86 fail=98`，rc=0。距 fail 線 13 筆。

**判準弄清楚了才動手**：未結＝`_classify(狀態欄) ∈ {None, 'open', 'routed'}`
（`_UNRESOLVED_CLASSES`，本體住 `tools/lib/defect_ledger_index.py`）。`_classify()` 取狀態欄
內**最早出現**的已知關鍵字；`workaround` 與 `partial` 一併歸 `open`。
**本輪複查判準本身有無 R74 那種「把某個狀態字誤當活躍」的縫**：逐一比對
`_STATUS_FIRST_WORDS`（7 個合法首詞）與 `_STATUS_KEYWORDS`（5 個分類器），
`unclassifiable_first_word_problems()` 為空 ⇒ 每個合法首詞都有分類器、沒有詞會落進
「含糊桶」。85 筆的分類實測全部落在 `open`(79) / `routed`(6)，**零筆 `None`** ⇒
本輪的 85 不是判準造出來的假數字，是 85 筆真的沒結案。

---

## 一、結案（CLOSED-VERIFIED）— 3 筆，每筆都附當回合的紅→綠實測

### DEF-101-297 — pre-commit 控制字元閘看不到內嵌換行（R33 立帳，跨 45 輪）

**缺陷原文**：`tools/git-hooks/pre-commit` 的 `_ntfs_seg_bad()` 用
`printf '%s' "$p" | LC_ALL=C grep -q '[[:cntrl:]]'`，換行被 `printf` 寫成真正的換行、成為
grep 的**行分隔符**而被消耗，於是路徑段內嵌 `\n`（0x0A）零命中。

**今天先證明它還在（紅）**，載具＝Git Bash 5.2.37（經 `tools/lib/Find-GitBash.ps1` SSOT 解析）：

```
case            | old | new
embedded \n     | MISS | HIT      ← 舊式漏掉，這就是缺陷
embedded \t     | HIT  | HIT
embedded ESC    | HIT  | HIT
clean md/py/CJK/spaces | MISS | MISS
CJK under LC_ALL=C: MISS
```

**修法**：在原 grep 之前加一道 bash 自身的 pattern match
（`case "$p" in *[[:cntrl:]]*) cntrl=1 ;; esac`）——**不經任何以行為單位的載具**，
整條字串一次比對。原 grep 保留為第二層，不刪任何既有判準。

**為什麼是「加一層」而不是「換掉」**：`[[:cntrl:]]` 在 POSIX 字元類不被支援的殼上會退化成
字面 bracket set，那時舊 grep 還在＝行為與今天完全相同（漏 `\n`，不會新增假紅）。
選這個失效方向是刻意的。

**假陽性掃描（必須是 0，否則整個 repo 無法 commit）**：對全 repo **27,534 條** tracked 路徑
跑 case-pattern ⇒ **命中 0**（含 CJK 路徑、含空白路徑、含 `[` `]` `:` `$` `@` 的路徑）。

**修後端到端（綠）**：把**活的** `_ntfs_seg_bad` 從 hook 檔抽出來 eval 後直接驅動：

```
embedded LF              rc=0 out=含控制字元      ← 缺陷已消失
embedded TAB             rc=0 out=含控制字元
clean path               rc=1 out=<empty>
CJK clean                rc=1 out=<empty>
reserved CON             rc=0 out=路徑段「CON.txt」為 Windows 保留裝置名（CON）
trailing dot             rc=0 out=路徑段「bad.」以空白或句點結尾（NTFS 不允許）
pipe char                rc=0 out=路徑段「a|b.md」含 Windows 不允許字元
```

`bash -n tools/git-hooks/pre-commit` → rc=0；`git ls-files --eol` 該檔 `i/lf w/lf`（未破行尾政策）。

**射程誠實劃界**：本修只讓**本機 hook 追上 CI**——`tools/check_ntfs_paths.py` 走 Python `str`、
本來就不分行，一直看得到 `\n`。所以這不是新增一道判準，是補一個雙軌落差。
merge/rebase 不經 pre-commit 這條既有縫隙不在本修射程內（那是 git 行為）。

### DEF-101-278 — 腳本對等閘的摘要句描述一個沒有任何 pair 掛著的機制（R28 立帳）

**缺陷原文點名兩處**：`ONBOARDING.md` §6.1 `root-infra-ci.yml` 條目第 6 項，
與 `.github/workflows/root-infra-ci.yml:25` 檔頭註解。

**逐處實查（當回合）**：

1. **ONBOARDING 那一處已經不存在了** — R68 訂正② 把該列的逐道列舉**整段物理刪除**，
   現行文字逐字為「道數與逐道內容一律以 `.github/workflows/root-infra-ci.yml` 檔頭註解為準，
   本列刻意不再就地列舉」。⇒ 這一半屬 **OBSOLETE（標的物已不存在）**，不是被修好的。
2. **workflow 那一處還在**，只是行號從 `:25` 漂到 `:40`（檔案長大了；缺陷原文寫死行號，
   這本身就是本 repo 反覆在治的形態）。原文逐字：
   「腳本對等閘 — tools/check_script_parity.py：成對 .sh/.ps1 的 step 標籤清單一致」。
3. **這句話今天為什麼是誤導**：`check_script_parity.py` docstring 逐字寫著
   「`_MARKER_PAIRS` 目前為空清單」——四對已於 R12／R16 收斂為薄殼＋Python 單核心、
   改掛 hash 釘選，標籤比對隨之退場。本項今天的實際守門力來自**註冊完整性**與 hash 釘選，
   不是標籤比對。

**修法**：把第 6 項改寫成「註冊完整性」為主述，並就地標明 `_MARKER_PAIRS` 現為空清單、
機制保留給未來新對、R9/R12 沿革一律以該檔 docstring 為準（不在 workflow 檔頭複寫第二份）。
ONBOARDING §6「雙腳本對等機械守護」那一段（第 175 行）R28 早已訂正過、與新寫法一致，
兩處不再各說各話。

**驗證**：`python tools/check_script_parity.py` → rc=0（改的是註解，機制零改動）。

### DEF-101-435 — artifact 清理器檔頭宣稱「drift-daily.yml 無 upload」為假事實（R55 立帳）

**今天先證明它還在**：

- `.github/workflows/aisdlc-sdd-artifact-cleanup.yml:17` 逐字
  「（aisdlc-sdd-drift-daily.yml 無 upload；…）」
- `.github/workflows/aisdlc-sdd-drift-daily.yml:88-95` 逐字有
  `uses: actions/upload-artifact@v6` / `name: drift-daily-report` / `retention-days: 90`
- `ALLOWLIST_PREFIXES`（同檔 :59-62）＝`ci-arch-fitness-` / `arch-fitness-findings` /
  `fsm-chaos-report-`，**不含** `drift-daily-report`

**修法（刻意只改註解、不改刪除行為）**：把假事實改寫成「刻意**不在** allowlist 內」的具名
決策，並寫出理由——`retention-days: 90` > 本檔 7 天門檻，代表它被設計為長期取證產物，
納入 allowlist 會把它殲滅；這與 AutoClaude 家族（`mutation-history`／`perf-baseline-*`）
被排除的理由同構。同時把檔頭的維護指示改成雙欄（要刪的加 allowlist、不刪的加「刻意不列入」），
讓下一個新 artifact 不能兩邊都不寫。

**為何不是把它加進 allowlist**：那是**行為變更**（會開始刪一批目前留著的取證產物），
需要人拍板；而缺陷本身逐字就是「文件與程式碼矛盾」，訂正文件即消滅該矛盾。

---

## 二、STILL-OPEN — 當回合實測證明「問題還在」（把不確定變成已確認）

| ID | 今天實跑什麼 | 結果 |
|----|-------------|------|
| DEF-01-007 | `Get-Command cc-switch` | `NOT FOUND` — 環境工具仍未安裝，非程式可修 |
| DEF-101-338 | `git ls-files '*COMMIT-*sha*'` | **16** 支假 SHA yaml 仍被追蹤，且比帳本記載的**更廣**：v0.01 之外 v0.02/v0.03/v0.04 各 4 支 |
| DEF-101-377 | `git ls-files --eol -- '*.sh' / '*.py'` | `.sh` 168 支中 **144** 支工作樹為 CRLF；`.py` 5474 支中 **4176** 支為 CRLF（index 全 LF）。🔴 帳本 R47 段落宣稱「168/168 皆 w/lf、5371 w/lf」——該宣稱**今日不成立**，本表為當回合重測值 |
| DEF-101-022 | 讀 `AISDLC_SDD_v0.30/tools/fsm_runtime/closure_evidence.py:89-93` | `_run_git` 仍只帶 `cwd=`，未自清 `GIT_DIR`／`GIT_WORK_TREE` |
| DEF-101-025 | 讀 `tools/git-hooks/pre-commit:377`（原 `:377`，隨本輪修補後行號後移） | 仍為 `bash -n "$TOPLEVEL/$f"`＝工作樹版本。**新事證**：同一支檔的行尾閘（R74 落地）已示範了正解 `git show ":$f"`，修法成本已比立帳當時低很多 |
| DEF-101-234 | 讀 `tools/check_script_parity.py` `_EXEMPT_PAIRS` | `LATEST/tools/init_project`（tier3）與 `LATEST/tools/arch_fitness/run_self_evolution`（unpinned）兩對仍在豁免表內。緩解已增：R69 為後者加了退出碼契約三方鎖 |
| DEF-101-243 ② | `grep -rn 'sprint-verified\|sprint_verified\|最後更新' --include=*.py` | 全 repo 只命中 `AutoClaude/tools/snapshot_sync.py`（產生器，非新鮮度鎖）⇒ badge／日期仍零機械新鮮度檢查。①③ 依帳本 R22 校正已 fixed@R19，本列只剩 ② |
| DEF-101-278 之外的姊妹：DEF-101-402 | 讀帳本＋確認 meta-lock 宿主 | 宿主 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 在子專案樹內，本輪授權面不含該樹 ⇒ 未動 |
| DEF-101-740 | 讀 `tools/git-hooks/pre-push:255／346／366` | 三處皆只探測 `python`，無 `python3` 回退。姊妹 hook 有。**未修的理由見下** |
| DEF-101-769 | `Get-Command pwsh` ＋ `$PSVersionTable` | `7.6.4`（WindowsApps MSIX 真實執行檔）⇒ 本列 R71 寫的阻塞前提「本機無 pwsh 7」確定不成立、R75 已回執其中一項；**殘餘兩項**（CI `shell: pwsh` 步驟本機重現、`.bat`／`.cmd` 例外機械鎖）仍未做 |
| DEF-101-856 ② | `Test-Path AutoClaude/tools/verify_token_guard_e2e.py` | `True` — 死碼候選仍在 |
| DEF-101-870 | 讀 `tools/lib/sdd_latest.py:34` | 仍逐字寫「（DEF-101-500 third item／DEF-101-521，未隨本次收斂修復，仍 open）」。**只能修一半**：另一處在 `tools/tests/` 既有檔內，不在本輪授權面 ⇒ 解鎖條件①「兩處都改」結構上達不到，故整列不動（改一半會讓帳本記載與磁碟再度不一致） |
| DEF-53-001 | 全樹搜 `hub_merge.py` | 30 個版本目錄各一份，皆在 `AISDLC_SDD/**`（本輪不得改） |
| DEF-101-596 | 全樹搜 `hub_sync.py` | 同上，30 份全在 `AISDLC_SDD/**`。帳本 R66 已就地訂正過座標（原記 `AutoClaude/tools/`），本輪複驗該訂正正確 |
| DEF-101-676 | `python tools/archive_defect_log.py --check` | rc=0，主檔 108 列＋archive 882 列全部可解析。但本列自訂的**雙條件**（單輪吞吐 ∧ 健康餘裕同時成立）中，26KB 級槓桿（歸檔索引 bullet 與 archive 標頭去重）仍一行未動 ⇒ 維持不結案 |

---

## 三、NEEDS-DECISION — 需要掌舵者拍板才能動（agent 不得自行決定）

| ID | 要問什麼 | 為什麼 agent 不能自己決定 |
|----|---------|------------------------|
| DEF-101-794 | 是否以系統管理員身分跑 `tools\install_windows_nightly.ps1` 把兩支排程 job 的 5 項設定套上線（會 Unregister→Register，要保留現行 22:30／23:30 須顯式傳參） | 需要提權；且會動到線上排程，失敗代價是 nightly 整批漏跑 |
| DEF-101-866 / DEF-101-876 | GitHub Actions **月度支出上限**何時恢復／是否調高 | 花錢。且 876 已導致 R77 四方複審一次都沒跑、三個修復包完全未執行 |
| DEF-101-268 / DEF-101-296 | 是否 repo-wide 設 `PYTHONDONTWRITEBYTECODE=1`（或 conftest 設 `sys.dont_write_bytecode`）消除 `.pyc` 併發寫入競態 | 「測試速度 vs 可靠性」的取捨，且會影響 `bootstrap_core.py` 的 pyc 快取假設 |
| DEF-101-271 / DEF-101-274 | orchestrator 級 LOC 門檻要訂多少（1500？2000？），以及為何薄殼化核心檔可以豁免既有 `ABSOLUTE_LIMIT=750`（落差 2.7 倍） | 分級門檻是設計決策。現況實測：`../tools/dev_start.py` **1999/2000＝餘裕 1 行**、`../tools/check_script_parity.py` **1618/1618＝餘裕 0** ⇒ 已經在咬人了 |
| DEF-101-764 | `DEF-101-759` 一號兩用要往哪個方向收（改 7 處 vs 改 2 處） | 兩種都合法，必須擇一且程式碼與帳本要一致 |
| DEF-101-559 | LATEST `hub-push.yml`（sample）要不要隨根層一同升 action 版本 | 升了會讓「30 版此檔為同一 git blob」這個可機械核對的不變量首次分裂 |
| DEF-101-392 / DEF-101-401 | Copy-on-Evolve 凍結基線鐵律已兩度被迫打破，政策本身是否要改 | 框架治理政策，非工程判斷 |
| DEF-101-802 ② | UEP 階梯末階需 PM signoff，而回執容器是空表 | 依其自身敘述即屬需拍板類 |
| DEF-101-740 | 需要一台**沒有 venv 的 macOS**跑一次 push 前置驗證（`python`／`python3` 兩種 PATH 形態各一）才算解鎖 | 不是決策問題，是**缺一台機器**：修法本身只有幾行，但本列自訂的解鎖條件在 Windows 上結構性達不到 |

---

## 三之二、🔴 本輪意外揪出的死結：帳本時鐘與輪號標籤鎖互為對方的違規

**這不在任務射程內，是修 `DEF-101-297` 時被自己的鎖擋下才發現的**，且它現在正擋著本輪
**每一位**同時在工作的人，故必須具名上報。

**兩道鎖**：

- **鎖 A**（`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）：任何**程式碼檔**的
  輪號標籤不得超前 `current_round()`。
- **鎖 B**（`orphan_backlog_problems()`，硬規則②）：未結列指名的承接輪次必須 ≥ `current_round()`。

**而 `current_round()` 取自帳本「發現情境」欄的最大 `R\d+`** ⇒ 本輪第一列落地前，時鐘仍讀 **R77**。

**實測（當回合，未改動任何檔）**：

```
current_round() = 77
orphan problems now = 0
orphan problems if clock were 78 = 4
  - 帳本 :139 DEF-101-856
  - 帳本 :140 DEF-101-863
  - 帳本 :141 DEF-101-866
  - 帳本 :142 DEF-101-867
```

另一側實測：`python -m unittest test_check_defect_log_crossref` 現有 **35 筆**鎖 A 違規，
分佈於 `.claude/hooks/lint_powershell_command.py`、`AutoClaude/tools/hooks/loc_budget_check.py`、
`tools/check_pytest_baseline_sites.py`、`tools/check_wrapper_thinness.py`、
`tools/lib/baseline_origin.py`、`tools/lib/skip_tag_policy.py`、`tools/probe/audit_session.py`
及數支 `tools/tests/*.py` —— **全部是本輪其他工作寫下的 `R78`**（本檔作者持有的檔案零違規，
已逐檔核對）。

**死結長這樣**：要讓那 35 筆合法 ⇒ 得把時鐘推到 78 ⇒ 得在「發現情境」欄寫一列 R78 ⇒
那一瞬間上面 4 列的承接輪次（R77）就地變成孤兒 ⇒ `check_defect_log_crossref.py` 對**所有人**
rc=1。反過來，不推時鐘，那 35 筆就一直紅。**兩道鎖各自合理，合起來沒有一個合法的下一步。**

**為何本檔作者不逕自解**：唯一的完整解是「落地本輪首列 **並且** 同時把那 4 列的承接輪次
改派」——後者是**改別人的列的語意**，且「本輪到底算不算 R78」是掌舵者的定義。逕自推時鐘
＝把 4 筆紅留給別人；逕自改那 4 列＝替別人決定他們的交棒對象。兩者都不是本任務授權的事。

**建議的解（供掌舵者裁決，兩步必須同一次落地，缺一即紅）**：
① 在帳本寫下本輪第一列（「發現情境」欄含 `R78`）；
② 同一次編輯把 `DEF-101-856`／`863`／`866`／`867` 的承接輪次由 R77 改派為 R78 或「未指派」＋解鎖條件。
落地後立刻跑 `python tools/check_defect_log_crossref.py` 確認 rc=0 再繼續。

**這是 `R76 Scan-H⑥`「兩道鎖的合法動作互為對方違規」的同型復發**，只是這次的兩道鎖分別
長在「程式碼註解」與「帳本狀態欄」兩個看起來毫不相干的面上，中間靠 `current_round()`
這個共用讀數耦合起來——**沒有任何一支測試在觀測這個耦合本身**。

---

## 四、本輪沒做到的、不確定的（誠實劃界）

1. **85 筆沒有逐筆到磁碟實查**。深度實查＝上表列出的那些（約 20 筆）。其餘約 65 筆的分類
   依據是**它們自己記載的內容**（watch item／架構前瞻議題／需人工拍板），沒有新的磁碟證據。
   這是資源取捨，不是「已確認還在」——不得被引用為「已複查」。
2. **可修面被授權範圍卡住**。85 筆裡真正「有具體修法、修完就能結」的那批，修法標的大量落在
   `AutoClaude/**`、`AISDLC_SDD/**`、`tools/tests/` 既有檔——本輪一律不得動。
   典型：`DEF-101-205`（exec-bit 守門）／`DEF-101-557`（工作樹行尾守門）的落地建議
   都是「在 `tools/tests/` 新增一支 unittest」，而該樹受棘輪管、新增鎖檔須併入既有檔。
3. **DEF-101-297 的修法未在 bash 3.2（macOS 內建）上實測**。本機只有 Git Bash 5.2.37。
   風險已用「加一層而非換一層」的結構壓到最小（見上），但**沒有實測就是沒有實測**。
4. **DEF-101-278 的第 1 處是 OBSOLETE 而非被修好**（ONBOARDING 那一半在 R68 就被整段刪了）。
   本輪結案的依據是「兩處都不再有錯誤陳述」，不是「兩處都被本輪改過」。
5. 未結列從 85 降到 82，**距 fail 線 98 仍只有 16 筆餘裕**。本輪四方複審若照往例產生數十筆
   新列，這條線還是會撞上——真正的槓桿不在「多結幾筆」，而在 `DEF-101-676` 點名的
   26KB 級結構解，以及讓「有修法的列」不要因授權切分而永遠修不了。
