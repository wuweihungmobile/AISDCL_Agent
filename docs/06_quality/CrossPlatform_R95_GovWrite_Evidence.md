# CrossPlatform R95 — 治理檔禁寫（PRD §15.5 紅線 10）證據檔（Pkg-B）

> 本檔兩個角色：① R95 govwrite 守衛的立案、設計取捨與實測逐字帳；② R89 手法的
> **史料搬遷目的地**——`.claude/hooks/block_destructive_git.py` 為容納新判準而從模組
> docstring 搬出的敘事全文，逐字收在 §史料搬遷（該檔 `guardrail_cli` tier 已滿格
> 750/750，新增判準必須以等量史料外移抵銷，淨成長 +0）。
>
> 章節依批次追加、序號非單調（本檔 §4→§6→§5 的順序是各批次落款的時間序，不重排——
> 重排會改寫既有搬遷點指回來的座標）。

## 1. 立案

- **PRD §15.5 紅線 10**：治理面檔案須有禁寫保護；改動前全庫**零機械物**（只有散文）。
- **R87 實帳**（MEMORY「不得以模型判斷推翻機械守衛」）：一個 agent 為繞過 halt 改了
  取數層 ⇒ 13 agent 全滅、1.3M tokens 零產出。守衛的訊息就是答案，不是要繞過的牆。
- 本 repo 已三度實證「純文件約束對當下的模型零攔阻力」（`block_bash_on_windows.py`、
  `lint_powershell_command.py`、`block_destructive_git.py` 各自的立案）——所以這一條
  必須是 hook，不是第四次寫進散文。

## 2. 設計取捨

### 2.1 載體＝既有 `.claude/hooks/block_destructive_git.py`，不新開 hook 檔

該檔已是「PreToolUse × 平台中立」觀測面上唯一的住戶（鐵律六那一族入住時同一個
論證）。另開一支 hook 的代價：payload 解析、UTF-8 stdio、fail-open 契約、逃生口語意
各再抄一份（「同一份知識住兩個家」是本 repo 的頭號病），且 `.claude/settings.json`
要多兩條 exec form 條目、`hook_wiring.py` 普查面多一格、`check_hooks_liveness` 的
形態判準面多一支。佈線變更收斂為**只擴既有條目的 matcher**：
`Bash|PowerShell` → `Bash|PowerShell|Write|Edit|NotebookEdit`。

加寬合法性（動工前現查過的三道鎖）：

- `degraded_payload_verdict`（`tools/tests/test_check_hooks_liveness.py`）只約束
  「退化 payload 回 rc=2」的守衛配窄 matcher；本 hook 退化走 rc=1，且
  `test_loud_but_non_blocking_is_green_even_with_wide_matcher` 明文放行。
- `TestHookRegistrationScopeIsShrinkOnly` 的 `_REGISTRATION_BASELINE` 是**下限**：
  `test_widening_the_matcher_is_green` 逐字釘住「多守一個工具不得轉紅」。
- `test_block_destructive_git_r83.py::test_registered_as_pretooluse_on_both_shell_carriers`
  釘 matcher ＝ 腳本射程，已同步改為 `OWN_TOOLS ∪ GOV_TOOLS`（仍是「恰好相等、
  零附帶面」，只是射程多了一族）。

### 2.2 判準刻意窄（誤擋是守衛被整個關掉的路徑）

| 維度 | 取法 | 理由 |
|------|------|------|
| 觸發 | 只在 `AUTOSDD_UNATTENDED` 有設時 exit 2 | 主 session 每輪都要改治理檔；有人值守只出聲（rc=1）不阻斷 |
| 保護面 | 字面清單 SSOT＝hook 內 `_GOV_EXACT` ＋ `.claude/hooks/*.py`（`_GOV_HOOK_PREFIX`）＋ `.autoclaude/`（`_GOV_DIR_PREFIX`，R95 修復包）一處 | 清單住兩個家只有一個會被改 |
| 根界 | 目標 realpath 落在專案根之外一律放行 | scratchpad／合成樹裡的同名檔不是治理檔（同 git 族換樹放寬的方向） |
| 豁免 | **無行內豁免** | 無人值守回合自己寫得出豁免（同 `# git-guard-ok:` 在 UNATTENDED 下無效的論證，直接不開這個口） |
| 逃生口 | `AUTOSDD_GOVWRITE_GUARD_OFF`（啟動 claude 前設，模型碰不到） | 刻意不與 `AUTOSDD_GIT_GUARD_OFF` 共用；`main()` 裡治理面分支判在 `GUARD_OFF_ENV` 之前，兩族開關互相關不掉對方（具名測試雙向釘住） |
| 退化 | 判不出寫入目標 ⇒ exit 0 放行 | fail-open 是 P0（hook 誤觸 deny 會把所有工具硬鎖死） |

**收錄邊界（R95 修復包 m4 補；四方審查高共識項）**——一個檔要不要進 `_GOV_EXACT`，
判準＝「**改它可直接改變 cap/band/武裝裁決/守衛自身行為**」，不是「它重不重要」：

- `.env`（M3，QA 探針實證修前可寫）：`.claude/settings.json` `env` 區塊的**同義載體**
  ——hook 行程的環境變數可由它注入，寫 `AUTOSDD_QUOTA_GUARD_OFF=1` 進去＝關掉守衛，
  與 DEF-200-115 立案的 settings.json 路徑等價，保護 settings 卻放行 `.env` 是同一扇門
  留了第二把鑰匙。
- `tools/lib/quota_messages.py`（修4 的 `halt_resets_at` 住這裡）／`tools/lib/quota_escalation.py`
  （叫人＋扇出救援的唯一載體）／`tools/session_resume_planner.py`（哨兵四分支與喚醒 spawn
  本體）：三者是喚醒鏈的裁決／告警／致動面，改任一支即可讓「撞線→喚醒」靜默失效
  （ADR §2.9 事故正是這一族的失效）。
- `tools/lib/platform_utils.py`：`read_hook_payload()` 的唯一家——**所有** hook 的輸入
  面都經它，改它＝改所有守衛看到的世界（原在測試 NOT_PROTECTED 反例清單，R95 修復包
  依本判準改列保護面；反例改用 `tools/lib/git_paths.py`，它只服務路徑列舉、不碰裁決）。
- `.autoclaude/`（目錄前綴）：PRD 紅線 10 字面點名的保護面；目錄今日不存在——**先釘
  判準**，等它被建立那天才發現沒人守＝紅線失效的靜默形態。
- 刻意**不**收：`.env.example`（機械生成物，重生即覆寫）、`tools/lib/git_paths.py`
  等不碰 cap/band/武裝裁決的取數工具——判準若寬到「重要就收」，誤擋面會把守衛整個
  關掉（repo 判例）。

### 2.3 誠實劃界（本判準擋不到什麼）

- **經 shell 的寫檔**：`sed -i`／`tee`／`cp` 蓋治理檔走 Bash/PowerShell 指令字串面，
  本包**刻意不加**該判準——寫檔動詞的假紅面大（`tee` 到日誌、`cp` 備份都是日常），
  擋到讓人無法工作的守衛會被整個關掉。
- **MCP 檔案工具／別的 session**：不經本 hook 的觀測面。
- **有人值守情境**：只出聲不阻斷是刻意設計，不是缺口——紅線 10 的威脅模型是
  「無人值守的回合自作主張」，不是掌舵者本人。
- 子專案（`AutoClaude/.claude/settings.json` 等）不在保護面：另有子專案自己的守衛層。
- **根外狀態檔不受保護**（R95 修復包 m4 補記）：`$TMPDIR` 的快取／閂鎖／任務書
  （`autosdd_quota_latch.json`、`autosdd_resume_plan_*.md` 等）落在專案根之外，
  依「根界」列**結構上放行**。理由：根界判準是誤擋防線的地基（scratchpad／合成樹
  必須可寫），為狀態檔在它身上開例外＝把「專案根之外」變成一張要逐檔辯護的清單；
  且這些檔重開機即消失、消費端（哨兵）對其毀損已有自癒與 fail-loud 分形（M2 第四
  分形），失效方向是可偵測的，不是靜默的。

## 3. 實測逐字帳（2026-08-16，mac，本輪真跑）

環境：`CLAUDE_PROJECT_DIR=<repo 根>`；payload 經 stdin 餵 hook 子行程（與 production
`_hook_launcher.py` 同形）。

| # | 情境 | payload 要點 | 期望 rc | 實測 rc |
|---|------|-------------|---------|---------|
| 1 | 無人值守 × Write settings.json | `AUTOSDD_UNATTENDED=1` | 2 | 2 |
| 2 | 無人值守 × Edit hook `.py` | 同上，file_path=`.claude/hooks/context_budget_guard.py` | 2 | 2 |
| 3 | 無人值守 × NotebookEdit quota_policy.py | notebook_path 形態 | 2 | 2 |
| 4 | 有人值守 × Write settings.json | 無 UNATTENDED | 1（出聲不阻斷） | 1 |
| 5 | 無人值守 × Write 非保護檔 | file_path=本證據檔 | 0 | 0 |
| 6 | 無人值守 × 根外同名檔 | file_path=`<tmp>/.claude/settings.json` | 0 | 0 |
| 7 | 逃生口 | `AUTOSDD_GOVWRITE_GUARD_OFF=1` ＋情境 1 | 0 | 0 |
| 8 | 開關不越界（git→gov） | `AUTOSDD_GIT_GUARD_OFF=1` ＋情境 1 | 2 | 2 |
| 9 | 開關不越界（gov→git） | `AUTOSDD_GOVWRITE_GUARD_OFF=1` × Bash `git stash` | 2 | 2 |
| 10 | 無人值守 × Write `.env`（M3，R95 修復包 2026-08-17） | `AUTOSDD_UNATTENDED=1`，file_path=`.env` | 2 | 2 |
| 11 | 無人值守 × Write `.autoclaude/state.json`（m4，目錄不存在先釘判準） | 同上 | 2 | 2 |
| 12 | 無人值守 × Write 喚醒鏈同族檔（m4：quota_messages／quota_escalation／platform_utils／session_resume_planner） | 同上，PROTECTED 逐列 subTest | 2 | 2 |

（上表逐列由 `tools/tests/test_block_destructive_git_r83.py::TestGovernanceFilesAreReadOnlyWhenUnattended`
機械釘住；本表是人可讀的對照，數字以測試輸出為準。列 10~12 為 R95 修復包補列，
實測＝該類 12 tests OK（rc=0，當回合真跑）。）

## 4. §史料搬遷（自 `block_destructive_git.py` 模組 docstring 逐字外移）

> 以下各節是該檔 docstring 的**原文**，R95 為騰出 LOC 預算搬到這裡；檔內各留了
> 壓縮版與指回本節的座標。原文一字不動。

### 4.1 WHY（R83 立案事實原文）

本輪一個 subagent 在**六包並行共用的同一個工作樹**上執行了

    git stash -q -u --keep-index

瞬間清空 16 個修改檔 ＋ 4 個未追蹤檔（含其他包當時正在寫的
`tools/lib/quota_meter.py`、`tools/tests/test_dev_start.py`、`tools/lib/schedule_backend.py`）。
它自己發現後 `git stash pop` 還原，前後 `git diff --stat` 逐字相同
（16 files / 1791 insertions / 215 deletions）⇒ **沒有偵測到資料遺失，但那是運氣不是設計**：
當時若有任何 agent 正在寫檔，pop 會衝突或直接覆蓋。

那一次的任務書上**已經寫著**「不要 git add / commit / push」。
⇒ **禁令沒涵蓋到的那個動詞，就是被踩的那個。** 這正是本 repo 判過兩次的形態
（`block_bash_on_windows.py` 的立案理由、`lint_powershell_command.py` 的立案理由）：
**純文件約束對「當下的模型」零攔阻力**——規則寫進 CLAUDE.md 的同一個回合仍會再犯，
因為 CLAUDE.md 由 session 開場載入，而「主動記得」正是決策負荷第一個擠掉的東西。
所以這一條必須是 hook，不是散文；而散文那一半（動詞清單會有缺口）本檔也不修，
本檔改成**列舉會毀掉工作樹的形態**，不是列舉「不准做的事」。

### 4.2 動詞的危害射程（R83 誤攔訂正實測原文）

立案之後，兩名複審者各自在**自己 scratchpad 的拋棄式 worktree 內**跑
`git checkout -- <path>`（清掉零代價）而被本檔攔下。那是真誤擋，而誤擋正是這道鎖
被整個拔掉的路徑。但「偵測到不是共用工作樹就整條放行」是**錯的修法**——動詞的
危害射程不一樣，本回合在合成 repo（主樹 ＋ 一棵 linked worktree）逐條實測：

- **只限當前工作樹**（`checkout -- <path>`／`restore`／`reset --hard`／`clean`／`switch -f`）：
  在 wt 內 `git checkout -- b.txt` 之後，wt 的未提交改動消失、**主樹的
  `MAIN_UNCOMMITTED` 原封不動倖存 1 筆**。⇒ 這一族換一棵樹確實就安全了。
- **會溢出到共用 `.git`**（`stash` 全家）：在 wt 內跑事故那條
  `git stash -q -u --keep-index`，**主樹的 stash 深度 0→1、兩邊 `rev-parse refs/stash`
  是同一個 SHA**。⇒ `refs/stash` 是 repo 級不是工作樹級，**不論在哪一棵樹都必須擋**。
  這正是「只看樹就放行」會製造的新漏擋，而它漏掉的恰好是立案那一條指令。

所以判準是**動詞感知**的：先分類，再問樹。放寬只作用在「只限當前工作樹」那一族。

### 4.3 樹要從哪裡看出來？（量測原文）

複審者建議的判準是 `realpath(git rev-parse --show-toplevel) != realpath($CLAUDE_PROJECT_DIR)`。
`--show-toplevel` 確有鑑別力（實測主樹／wt 回不同值；`--git-common-dir` 兩邊相同 ⇒ 不可用），
**但問題在「在哪裡跑它」**：本回合實測 PreToolUse payload 的欄位與 hook 自己的行程狀態——

    payload keys: agent_id / agent_type / cwd / effort / hook_event_name / permission_mode /
                  prompt_id / session_id / tool_input / tool_name / tool_use_id / transcript_path
    payload["cwd"] == os.getcwd() == $CLAUDE_PROJECT_DIR == <專案根>
    ——即使被檢查的那條指令自己是 `cd /private/tmp && pwd`，這三個值仍然全是專案根。

⇒ 拿 hook 自己的 cwd 去跑 `--show-toplevel`，答案**恆等於**專案根 ⇒ 判準恆假 ⇒
放寬永遠不觸發、誤擋一次都沒少，而程式碼看起來已經修好了。那正是本 repo 反覆判紅的
「鎖存在但沒有鑑別力」。**唯一真的帶著樹資訊的東西是指令字串自己**：段內的
`cd`／`pushd`／`Set-Location` 目標，與 `git -C <path>`。故本檔從字串推導「這次呼叫會落腳在
哪個目錄」，推導不出來就**不放寬**（fail-closed 到現行行為）。

### 4.4 `git -C` 反向 ＋ pathspec 由 git 自己守住（原文）

`git -C` 是**反向**也要成立的那一半：`cd` 到別處不代表安全。實測 cwd=`/tmp`（完全在
lab 之外）時 `git -C <主樹> checkout -- b.txt` rc=0、主樹改動消失 ⇒ `-C` 必須被當成
這次呼叫的落腳目錄（於是它會判回「共用工作樹」而擋下），不是被忽略。

不需要另立判準的那一個（git 自己就守住了）：「在 wt 內用絕對路徑指主樹的檔」實測
rc=**128**、逐字 `fatal: <path>: '<path>' is outside repository at '<wt>'`，主樹的
`MAIN_AGAIN` 倖存 ⇒ pathspec 逃出當前工作樹這條路由 git 自己關掉。本檔因此**不**另加
pathspec 包含性判準（多一條判準就多一族假紅），代價是這條事實由 git 的行為擔保、
不由本檔擔保。

### 4.5 `--staged` 的取捨（原文）

`git restore --staged <path>`（且未同時帶 `--worktree`／`-W`）**只動 index**，
工作樹的檔案內容原封不動 ⇒ **放行**。本檔守的危害類是「工作樹內容被不可逆清掉」，
而 unstage 掉的東西還完整躺在檔案裡。代價誠實寫在這裡：它確實會丟掉「哪些 hunk 已暫存」
這個狀態，`--keep-index` 那種精細操作會被打斷——但那不是本檔守的東西，把它一起擋
就是拿一筆會天天發生的誤擋，去換一個沒有資料遺失的情境。
`git restore --staged --worktree <path>` 兩者同時帶時工作樹會被覆寫 ⇒ **擋**。

### 4.6 為何不加平台閘（原文）

姊妹檔 `block_bash_on_windows.py` 第一件事是 `os.name != 'nt' → exit 0`，因為它守的
規則本身只在 Windows 成立。本檔相反：**`git stash` 在 mac 上清掉的檔案，和在 Windows 上
清掉的一模一樣**，而立案的那起事故就發生在 macOS。無條件把姊妹檔的平台閘抄過來，
會讓這道鎖在事故現場那個平台上一行都不跑——那是 `DEF-101-766` 的鏡像版本
（單平台判準不可無條件外推，**兩個方向都不可以**）。故本檔不看平台。

### 4.7 退化 payload 走 rc=1 的理由（原文）

payload 解析不出工具名／指令 → **exit 1（出聲但不阻斷）**，不是 exit 2。理由同
`lint_powershell_command.py`：Bash（mac）／PowerShell（Windows）是這台機器上**唯一的
shell 載具**，對一份根本讀不出內容的 payload 硬擋它，等於用一個讀不懂的輸入換掉整個
工作面；而「送壞 payload 繞過守衛」在這裡不是真實威脅面——payload 由 Claude Code 產生，
不由被守的一方撰寫。真正要防的是**守衛靜默失效**，exit 1 已經滿足（不阻斷但出聲）。

### 4.8 〈誠實劃界〉引號執行檔條目的佔位符沿革（原文；R95 修復包批自模組 docstring 外移）

> （此處刻意寫成佔位符而不是某台機器上的真實磁碟機路徑：本檔會被 commit，寫死的
>   路徑對其他 checkout 一律是錯的，且 `tools/tests/test_platform_neutral_paths.py`
>   會逐行掃描並判紅——姊妹檔 `block_bash_on_windows.py` 因同一條規則已訂正過一次。）

## 6. §史料搬遷（R95 收尾窗口批：自 `tools/tests/test_block_destructive_git_r83.py` 逐字外移）

> R89 體例：判準與判準的理由留在測試檔，事故數字／立案敘事原文住這裡；各搬出點留有
> 指回本節的座標。原文一字不動。

### 6.1 模組 docstring〈WHY 這支鎖存在〉原文

> 被守的那支 hook 的立案事實：一個 subagent 在**六包並行共用的工作樹**上跑
> `git stash -q -u --keep-index`，16 個修改檔 ＋ 4 個未追蹤檔瞬間消失（含其他包當時
> 正在寫的三支檔）。它自己 `git stash pop` 還原、前後 `git diff --stat` 逐字相同
> ——**沒有偵測到資料遺失，但那是運氣不是設計**。任務書當時已寫「不要 git add /
> commit / push」⇒ **禁令沒涵蓋到的那個動詞，就是被踩的那個**。

### 6.2 `TestWorktreeConfinedVerbsRelaxOutsideTheSharedTree` 立案原文

> WHY 這件事非做不可（不是便利性）：兩名複審者各自在自己 scratchpad 的拋棄式
> worktree 內跑 `git checkout -- <path>` 被擋下。repo 已判過「擋到讓人無法工作的守衛
> 會被整個關掉，而被關掉的守衛比沒有守衛更糟」⇒ 誤擋是這道鎖的**存亡問題**。
> 合成 repo 實測支撐這一族可以放：wt 內 `git checkout -- b.txt` 之後，主樹的
> `MAIN_UNCOMMITTED` 原封不動倖存。

### 6.3 stash 全家「不論在哪一棵樹都擋」實測原文

> 這是「只看樹就整條放行」會製造的新漏擋，而它漏掉的恰好是**立案那一條指令**。
> 實測依據（合成 repo，主樹 ＋ 一棵 linked worktree）：在 wt 內跑
> `git stash -q -u --keep-index`，主樹的 stash 深度 **0→1**，兩邊
> `git rev-parse refs/stash` 是**同一個 SHA** ⇒ `refs/stash` 是 repo 級不是工作樹級。

### 6.4 `TestTheGuardDoesNotAskGitWhereItIs` 立案量測原文

> 本回合實測 PreToolUse payload 與 hook 行程狀態：`payload["cwd"]`、`os.getcwd()`、
> `$CLAUDE_PROJECT_DIR` **三者恆等於專案根**，即使被檢查的指令自己是
> `cd /private/tmp && pwd`。⇒ 在 hook 自己的 cwd 跑 `--show-toplevel`，答案恆為專案根、
> 判準恆假、誤擋一次都沒少，**而程式碼看起來已經修好了**——那正是本 repo 反覆判紅的
> 「鎖存在但沒有鑑別力」。

### 6.5 R84「Python 層 git 呼叫」缺口第一個真實命中原文

> 立案事實（不是假想）：2026-08-12 00:21:13，一個 agent 送出的 Bash 指令裡有一行沒刪掉的
> 草稿殘留，清空了 R84 全輪工作樹（91 檔、+4658/-508）。`capture_output=True` 把
> `Saved working directory…` 吃掉 ⇒ rc=0、無 stderr、**看起來完全正常**；送出它的 agent
> 事後自陳「我全程只跑唯讀指令」——它自己看不見。已用 `git stash apply` 全額還原
> （`stash@{0}` ＝ `7b7ce22`），但那是運氣不是設計。

（R95 修復包批補搬同節首註解的教訓段，原文：）

> 🔴 這一族的教訓不是「再加一條判準」，而是：**被守的那支 hook 自己的檔頭早就寫著這兩條
> 缺口**（「不經 shell 的路徑」與「heredoc 內容」），而「已知並劃界」被當成了結案。
> 本 repo 對這個形態已有判例（`DEF-101-757`：已知的鎖射程缺口不得只以劃界結案）。
> ⇒ 下面兩張表就是那兩條劃界的**到期日**：它們現在會紅。

### 6.6 `TestR84WorktreeRemoveForce` 收窄普查原文

> 🔴 但它的判準是**量出來的**：全語料 4,017 筆／去重 3,740 種上，新舊判準各跑一次，
> 新增命中 6 種**全部**是這個動詞，逐筆判讀 6/6 都是「拆自己的拋棄式樹」——一筆事故
> 形態都沒有。無差別擋＝拿一個從未發生的危害去換一個天天發生的誤擋。故收窄成
> 「被拆的是誰」：外樹放行、harness 自己的 `.claude/worktrees/` 沙盒放行，其餘照擋。
> 收窄後新增命中降到 4 種，且**舊擋新放 0 種**（沒有任何既有守備被換掉）。

### 6.7 `TestUnattendedAuthzHasTeethOnEveryPlatform` 立案與假紅普查原文

> 🔴 立案（本輪 P3 實測，不是假想）：唯一擋 commit／push 的是
> `.claude/hooks/lint_powershell_command.py`，而它 matcher 是 `PowerShell`
> （mac 的 shell 載具是 `Bash`，連 matcher 都對不上）、且第一件事是
> `os.name != 'nt' → exit 0`。兩道各自都足以讓那條規則在 mac 上不存在
> ⇒ 無人看管代理在 mac 可自由 commit／push。該 hook 檔頭自己已把這個缺口寫成
> 〈誠實劃界〉——**登記了卻一直沒補**，而訴求 6d（reset 後自動喚醒續跑）回來的
> 正是那種 headless 代理。
>
> 🔴 假紅普查（母體＝逐字稿裡**真的送出過**的指令字串＝PreToolUse 的真實輸入面，
> 不是 tracked 面——照 tracked 面判會把「只出現在描述它的散文裡」的命中讀成假紅）：
> 3,804 條相異指令 → 命中 136 條，逐條回查「解析器或正則指不指得出一次真的
> git/gh write」＝ **0 條指不出** ⇒ 假陽性 0。

### 6.8 R84「載具類」漏擋節首敘事（原文；R95 修復包批外移）

> 🔴 這一批的共同形態：**同一件事，只因換了一個載具就一擋一放**。R84 第一版把
> heredoc 那個載具修好了，卻沒有把「載具」抽象成一類 ⇒ `-c`／尾逗號／argv 前綴三個
> 兄弟原封不動地留著。所以下面每一張表都刻意用**同一個毀滅性子指令**跑過所有載具：
> 判準要守的是「不論走哪條路進來，都判同一個結果」，不是「這幾個字面有被列到」。

### 6.9 R85／SD-B3 引號執行檔路徑兩半立案敘事（原文；R95 修復包批外移）

擋下面（`BLOCKED` 表內註）：

> 🔴 R85／SD-B3：**引號包住的執行檔絕對路徑**——根 CLAUDE.md 鐵律二對 Windows
> 明訂的正是這個寫法（`& '<絕對路徑>' …`），而兩支守衛都先把引號區段遮成空白
> 才判 ⇒ 連 `git.exe` 一起消失。實測本族修前**一條都不擋**（同一條去掉引號則
> 全部命中）＝本 repo 自己規定的寫法恰好落在射程外。

放行面（`MUST_PASS` 表內註）：

> 🔴 R85／SD-B3 的另一半：假紅同樣是缺陷。git 的**設定鍵天生以子指令名開頭**
> （`push.*`／`commit.*`），修前 `git config push.default` 這種唯讀查詢被判成
> push；而 `&` 之後是**下一個**指令，跨過去等於把別人的參數算到 git 頭上。

### 6.10 M3 `.env` QA 實證敘事（原文；R95 收尾窗口批自 M3 測試 docstring 外移）

原 `test_unattended_write_to_dot_env_is_blocked` docstring 首行括注，一字未刪：

> （QA 實證修前可寫）

## 5. 收尾窗口待辦（本包越不出持有面的部分）

- **Windows 側待驗承接＋下輪順手項（R95 修復包 m9；帳本索引列＝DEF-200-147）**：
  1. govwrite 九格 rc 矩陣（§3，含 R95 修復包補列 10~12）在 Windows 重跑——mac 側
     全綠不外推（鐵律三：單平台判準兩個方向都不可無條件外推）。
  2. NTFS 大小寫繞行探針：`.ENV`／`Tools/Lib/Quota_Gate.py` 這類大小寫變體是否仍命中
     `_GOV_EXACT`（判準是字面比對；mac APFS 預設同為大小寫不敏感，但 `os.path.realpath`
     兩平台對大小寫的正規化行為不同源，不得以 mac 綠推 Windows 綠）。
  3. 修3（哨兵活性欄）／修4（halt 多軸武裝）的 schtasks 取證：憑證＝`NextRunTime`
     的**值**不是 rc（mac 只驗過 launchd 後端，該側憑證是 rc——兩後端憑證形態不同，
     各自取證）。
  4. SD 下輪順手項：prepare 帶動作的一次性閂鎖鍵是否比照 halt 鍵改記 `halt_resets_at`
     期程半（`tools/lib/quota_gate.py` prepare 分支現查）。
  5. Arch 下輪順手項：`halt@<binding.kind>@<reset>` 閂鎖鍵混用 binding 軸與被武裝
     reset 軸，兩軸不同源時鍵語意待釐清（Pace 證據檔 §7-R95-修4 的已知殘項）。
- **DEF-200-115 原列原文（R95 修復包批：該列因單列 700 bytes 上限瘦身成索引，原文
  一字不動搬此；「§7」即指本段）**：

  > | DEF-200-115 | 2026-08-14 | R89 讀 PRD §15.5 紅線 10 後實查本 repo | **守衛可被受守衛者關閉**：`.claude/settings.json` 的 `env` 區塊會注入 hook 行程（`quota_policy` docstring 載明），而全 repo **無任何 hook 保護該檔** ⇒ 模型自己寫入 `AUTOSDD_QUOTA_GUARD_OFF=1` 即可關掉整條額度節流，且外觀是一次合理的設定編輯。與 `DEF-200-107`（繞過守衛）同族 | P1 | 未修。需裁決：禁寫清單放哪一層、逃生口怎麼留（人改得動、模型不行）。🔴 fail-closed 風險高（該檔記載過的 P0：hook 誤觸 deny 會把所有工具硬鎖死）⇒ 需第三方複審 | fixed@R95：詳 DEF-200-144 |

- 根 `CLAUDE.md`〈機械守衛總表〉`block_destructive_git.py` 列：事件欄宜補
  `Write／Edit／NotebookEdit`、逃生口欄宜補 `AUTOSDD_GOVWRITE_GUARD_OFF`（表為文件
  導航，不改不會紅——`TestR74`/`TestR79` 只釘「已註冊者被點名且不被標成不會跑」，
  不解析 matcher 明細；但表已 stale，收尾單人窗口請順手補）。
- `tools/tests/test_check_hooks_liveness.py::_REGISTRATION_BASELINE` 的
  `("PreToolUse", ".claude/hooks/block_destructive_git.py")` 格仍釘
  `{Bash, PowerShell}`（下限，加寬不紅）；收尾窗口可將下限升為含
  `Write/Edit/NotebookEdit`，讓「治理面射程縮回去」也會轉紅。該檔不在本包持有面，
  依該表自己的紀律（「由並行包新增條目、收輪者讓帳對得上」）留給收尾。
