# 自動駕駛開發管線設計（Autopilot Pipeline Design）

- 版本：v1.0（SD-0，2026-11-25；規格階段，實作未開始）
- 立案：掌舵者 2026-11-25 原文「以後這種不用詢問, 我要達到是真正的自動駕駛開發, 若無法達到這個目標, 請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查,請確認以上功能都已經解決完備！」；授權最佳化、不顧成本的方案由主控代決。
- 上游：AP-A Architect＋SA 報告（sid `406454ea-91fc-4481-9c11-b28ed7d9e95f` scratchpad `ap_arch_report.md`，CLOSE 窗口轉存證據檔）。PRD 只收本檔 §7（詢問類別閘）與 §8（舊視窗）兩項＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.5.12（R-4.5.12-1～5）與 §16.6 2026-11-25 第二列；其餘（合入、推送、帳本棘輪、CI 等待、測試圍籬）屬開發管線，只住本檔。
- 兄弟設計：`docs/02_architecture/QuotaVerdict_AccountSwitch_Design.md`（額度判決與換帳號；本檔的推送閘與派工決策只讀它的 `QUOTA_VERDICT=` 行）。
- 驗收：`docs/03_testing/contracts/TCS-Autopilot-20261125.md`（REQ-AP-MG-01～02、REQ-AP-G1-01～03、REQ-AP-ASK-01～02、REQ-AP-CI-01、REQ-AP-OW-01、REQ-AP-FN-01、REQ-AP-WT-01）。

---

## 0. 一頁結論

| 缺口 | 修法（一句） | 節 |
|---|---|---|
| G3 代理 worktree 起點是 origin/main | 專案 settings 設 `worktree.baseRef: "head"`（官方支援的設定，現查證實）；merge 的 rebase 留作第二道 | §3.1 |
| G4／G10 合入靠手工、合入後紅到推送才發現 | `python tools/autopilot.py merge`：repo 外拋棄式 worktree rebase → 略過已吸收 → 補連動鎖 → 跑 pre-push 同款全套 → 綠才 fast-forward 並清理；冪等 | §3 |
| G1 帳本淨額棘輪只在提交時判 | 判準移到**推送範圍**（基準＝pre-push 給的 remote sha）；提交期只出聲；帳本變更集中到尾端提交，可「前綴推送」 | §4 |
| N2 子代理可自設 `*_OFF` | `AUTOSDD_NET_RATCHET_OFF` 在 Claude Code 衍生的行程內（`CLAUDECODE=1`）與無人窗口一律無效並出聲；逃生口只屬於人在自己終端機 | §5 |
| G2 macOS 排隊 15 分鐘被取消 | `ci_wait` 新分類 `queue_timeout`，自動 `gh run rerun --failed`（同 sha 至多 2 次） | §6 |
| N1／N7 AskUserQuestion 阻塞數小時 | PreToolUse（matcher `AskUserQuestion`）類別閘：只放行 `[IRREVERSIBLE]`／`[COST]`／`[K1]` 三類（掌舵者 2026-11-25 定義），其餘阻斷並指路代決；順修 G9 的兩個假推回 | §7 |
| G8／G9 舊視窗關閉重試 3 次即交人 | 事件驅動（舊視窗自身 Stop）＋指數退避（上限 12 小時）；刪除「請手動」文案 | §8 |
| N3 單元測試污染真痕跡目錄 | `run_root_unittests.py` 加痕跡圍籬 | §9 |

---

## 1. 證據座標（AP-A 報告 §1／§2 已當場重查；本檔只列座標）

| 缺口 | 座標 |
|---|---|
| G1 | 逐字稿 L2416（HEAD＝77ddb8c5，`test_check_defect_log_crossref` 無逃生口 276 OK）、L2422（預帶 OFF）、L2424（分類器拒）、L2431→L2432（AskUserQuestion 19:02Z→01:21Z）；`tools/lib/ledger_closing_guards.py` `net_new_vs_closed_problems()`（判準＝`git show HEAD:` 對工作樹） |
| N2 | AP-A 報告 hyg_report〈連動面〉、逐字稿 L46 第 295 列（CLOSE1 子代理自設 OFF 提交通過） |
| G2 | `gh api` attempts/1 jobs：45427135743、45439253352、45456241389（`runner_name=""`、0 步驟、`completed−created`≈15:00、`cancelled`）；ci6.log、逐字稿 L1403、L1438 |
| G3 | 逐字稿 L469、L683（起點 2a56d3ff）、L651～L813；`docs/04_planning/ADR/ADR-XPLAT-006-parallel-agent-snapshot-fanout.md:228` |
| G4 | push1.log:454、push2.log:849～903、push5.log:851～875 |
| G8／G9 | `~/.autosdd/traces/oldwin/events.jsonl` 2026-11-24 20:50:38～21:08:03（四次 `not_idle`、`oldwin_retry_abandoned`）；逐字稿 L181、L221、L222、L239 |
| G10 | 逐字稿 L652、L704～L742、L762、L811 |
| N1／N7 | 逐字稿 L2431→L2432；近 14 天 15 次 AskUserQuestion 分類普查（AP-A §2 N7） |
| N3 | `~/.autosdd/traces/oldwin/events.jsonl` 85 筆 `oldwin_close_refused`（2026-11-23 16:03～2026-11-25 01:41，路徑 `%TEMP%\sc-roster-*`、夾具 sid `d4ed2654…`） |

---

## 2. 外部限制（harness 事實；SD-0 2026-11-25 以 `claude-code-guide` 子代理查官方文件，WebFetch 當回合真抓）

| 題 | 結論 | 官方原文（逐字節錄）與 URL | 設計採用 |
|---|---|---|---|
| WorktreeCreate hook | **有**。取代預設 git 行為；輸入只有共通欄位＋`name`；hook 須回傳建好的 worktree 絕對路徑；建在任何 repo 內會被拒 | 「`WorktreeCreate`: When a worktree is being created via `--worktree`, `isolation: "worktree"`, or for a background session. Replaces default git behavior」「have the hook create its directories outside any repository」（hooks.md#worktreecreate、worktrees.md） | **不採用**：要求 worktree 建在 repo 外、子代理結束不跑 WorktreeRemove（「keeps the worktree your WorktreeCreate hook made for it and doesn't run your WorktreeRemove hook」），新增守衛面與清理負擔；下一列的設定鍵已足夠 |
| `isolation: "worktree"` 起點 | 預設＝遠端預設分支；可設 `worktree.baseRef: "head"` 改為本地 HEAD；不能設分支名 | 「By default, the copy branches from your default branch rather than the parent session's `HEAD`.」「`"head"`: branch from your current local `HEAD`, so the worktree carries your unpushed commits … Use this when isolating subagents that need to operate on in-progress work.」「You can't set `worktree.baseRef` to a branch name.」（sub-agents.md、worktrees.md#choose-the-base-branch） | **採用**（§3.1） |
| `/login` 事件 | **無專屬事件**；Notification `auth_success`（「Authentication completes」）是否涵蓋 `/login` 文件未載；Notification 不能阻斷 | hooks.md、authentication.md | 見 QV 設計 §2／§7（不以 hook 為觸發器） |
| AskUserQuestion 逾時 | **預設無逾時**；`askUserQuestionTimeout`（`60s`／`5m`／`10m`）只在 user settings；逾時即提交已選項並「Claude proceeds on its own judgment」；背景 session 不計時 | 「Questions stay open until you answer them by default.」「The timer never starts for a question Claude asks in a background session…」（tools-reference.md#askuserquestion-tool-behavior） | 不依賴（PRD R-4.5.12-5）：設定在 repo 外、逾時語意是「模型自己判斷」＝等同沒問，且對背景 session 無效 |
| AskUserQuestion 可被 PreToolUse 攔 | **可**；matcher 精確字串 `AskUserQuestion`；可 deny、可以 `updatedInput.answers` 代答（須搭配 `allow`）、可 defer | 「The tool names are the exact strings you use in permission rules, subagent tool lists, and hook matchers.」「`AskUserQuestion` and `ExitPlanMode` need `updatedInput` paired with `"allow"`.」（hooks.md） | **採用**：deny＋指路代決（§7）；不採用代答（代答會把可代決的決定藏進 hook，主控看不到 WHY，違反「代決 WHY 寫進帳本」） |
| auto mode 對「指令內設 `*_OFF`」 | **文件未載**具體規則；只有類別名 `[Undermining Oversight]` 等 | permission-modes.md、auto-mode-config.md | 不依賴分類器（§5）：判準放在讀 OFF 的那支程式自己 |
| 子代理經分類器 | **是**，與主控同一決策序；另有派工時與交卷時兩個檢查點 | 「While the subagent runs, each of its actions goes through the same decision order as in the parent session, with the same block and allow rules.」（permission-modes.md） | 文件說對稱、實測不對稱（N2：子代理兩次通過、主控一次被拒）＝分類器結果不可預測，佐證 §5 不靠它 |
| GitHub macOS runner 排隊逾時 | 外部、11-24 起新現象 | AP-A §1 G2 | 只能分類＋重跑（§6）；換付費 runner／改 `runs-on` 屬成本與覆蓋面決策，**K=1 類，未代決**，僅列為選項 |
| 互動 UI 無法程式目視 | harness UI | — | 替身＋真排程驗到開窗前一刻；被動觀測痕跡（TCS 備援欄） |

---

## 3. 合入管線 `autopilot merge`（G3／G4／G10）

### 3.1 G3：派工起點

- 第一道：`.claude/settings.json` 加 `"worktree": {"baseRef": "head"}`（守衛面檔，WP-HOOK 以 staged diff 交主控親套；暴露證據見 §13）。效果：之後所有 `isolation: "worktree"` 子代理從主控當下的本地 HEAD 分支。
- 已知副作用（官方文件）：「Inside a worktree, `"head"` resolves to that worktree's `HEAD`」——主控若本身在 worktree 內派工，起點是該 worktree 的 HEAD，這正是要的。fresh 模式的「同名 worktree 重開會被重置到預設分支」行為在 `head` 下不適用。
- 第二道（保留）：merge 第 1 步一律 rebase 到本地 HEAD，並記錄 `merge-base` 與派工當時 HEAD（任務書寫入 `--base-at-dispatch`）是否相等；不等 ⇒ 痕跡 `base_drift`，仍照 rebase 處理（不中止），用來偵測設定被改回。
- 派工任務書範本不再寫「首動作 `git rebase main`」（AP-A 備援案），以免代理在自己的 worktree 裡手動 rebase 造成衝突狀態殘留。

### 3.2 指令與步驟

```
python tools/autopilot.py merge --branch <代理分支> [--base-at-dispatch <sha>] [--dry-run]
```

| 步 | 動作 | 失敗結局（末行 `MERGE_VERDICT=`） |
|---|---|---|
| 0 | 取 repo 鎖 `~/.autosdd/autopilot.lock`（單一窗口；鐵律七「收尾單人窗口」的機械化）；主樹須乾淨 | `busy`／`dirty` |
| 1 | 在 **repo 外**（`%TEMP%`／`$TMPDIR` 下 `autopilot-<ts>`，避開 `.claude/worktrees` 掃描面）`git worktree add` 本地 HEAD，`git rebase --onto HEAD <merge-base> <branch>` 的等價逐提交套用 | 衝突 ⇒ 產衝突包（每個衝突檔的三方內容與提交訊息，寫到 `~/.autosdd/autopilot/conflict-<ts>/`），`git rebase --abort`，回 `conflict`；主控派解衝突代理，不手解 |
| 2 | 已被吸收的提交略過：`git patch-id --stable` 比對本地 HEAD 至 merge-base 之間的提交 | — |
| 3 | 帳本檔（`docs/06_quality/AutoSDD_Defect_Log*.md`、外部阻塞帳、結構性長債帳）的變更自各提交剝離，集中成**尾端單一提交**（§4.3） | 剝離後某提交為空 ⇒ 丟棄該提交並記痕跡 |
| 4 | 補連動鎖（只套工具算出、在既有上限內的值）：`--print-guard-lines` 建議值、`_TREE_FILE_FLOORS`、E501 存量、skip 普查、`MIN_TESTS`＋ONBOARDING 同步；`repin_growth_problems()` 非空 ⇒ 停 | `repin_blocked`（不改上限常數） |
| 5 | 跑 pre-push 同款全套：以合成 stdin（`refs/heads/main <新 sha> refs/heads/main <origin/main sha>`）直接呼叫 `tools/git-hooks/pre-push`，經 `sessionctl runlong`／`waitfor` 分段等待（子代理快取壽命） | `red`（附失敗 leg 與末段 40 行） |
| 6 | 全綠 ⇒ 主樹 `git merge --ff-only <拋棄式分支>`；`git worktree remove <路徑>`（**不帶 `--force`**）；`git branch -d <代理分支>` | `ff_refused`（主樹在步驟 0 後被動過） |
| 7 | 末行 `MERGE_VERDICT=ok sha=<新 HEAD>` | — |

- **冪等**：每步落痕跡 `~/.autosdd/autopilot/merge.jsonl {branch, step, sha, verdict}`；重跑同一指令時，步驟 2 會把全部提交判為已吸收 ⇒ `MERGE_VERDICT=noop`。
- **不留半套**：任何非 ok 結局都在 `finally` 移除拋棄式 worktree 並還原主樹（主樹在步驟 6 之前從未被寫）。
- 禁止形態（鐵律五）：不用 `git stash`、`git checkout --`、`git reset --hard`、`git clean`；中止只用 `git rebase --abort`／`git cherry-pick --abort`（皆不在毀滅性清單）。

### 3.3 與 pre-push 的關係（REQ-AP-MG-02）

pre-push 本身不改。「乾跑」＝以合成 stdin 呼叫它，leg 集合天然相同；`tools/git-hooks/pre-push` 已逐行解析 stdin 的 `<local_ref> <local_sha> <remote_ref> <remote_sha>`（現行第 100 行附近），不需新旗標。

---

## 4. 推送閘 `autopilot push` 與推送範圍棘輪（G1）

### 4.1 棘輪判準移到推送範圍（`tools/lib/ledger_closing_guards.py`）

| 階段 | 如何得知 | 基準 | 淨額 > 0 時 |
|---|---|---|---|
| 推送期 | pre-push 匯出 `AUTOSDD_NET_RATCHET_BASE=<remote_sha>`（新分支 remote_sha 全零時用既有 merge-base 回退值）＋`AUTOSDD_NET_RATCHET_PHASE=push` | `git show <base>:<帳本>` | 阻斷（rc≠0） |
| 提交期 | 未設 `PHASE`（pre-commit 路徑） | `git show HEAD:`（現行） | **只出聲**、不阻斷（發現輪可先提交保全） |
| CI | workflow 未匯出 base | `HEAD`（與現況相同：CI 樹＝HEAD，淨額恆 0） | 照實劃界：CI 不判推送範圍；推送範圍的唯一閘是 pre-push |

這是收緊：現況「提交後即不可見」的洞（提交時用逃生口、推送時棘輪看不到）被補上。

### 4.2 推送流程

```
python tools/autopilot.py push [--dry-run]
```

1. 讀 `sessionctl quota` 判決：非 `CONTINUE` ⇒ 不推、依判決處置（QV 設計 §3.5）。
2. 乾跑 pre-push（§3.3）。紅 ⇒ 依 pre-push 失敗 leg 分類產修復任務書（`~/.autosdd/autopilot/fix-<ts>.md`：失敗 leg、末段輸出、涉及檔），末行 `PUSH_VERDICT=red brief=<路徑>`，主控派修復棒。
3. 淨額 > 0（推送範圍）⇒ 對每筆新未結 DEF 產同輪修復任務書（帳本列＋證據檔座標）；末行 `PUSH_VERDICT=net_positive briefs=<n> prefix=<sha|none>`。
4. 綠 ⇒ `git push origin <sha>:main` → 背景 `python tools/ci_wait.py --commit <完整 sha>` → `CI_WAIT_VERDICT=fail` 且非 `queue_timeout` ⇒ 產修復任務書。

### 4.3 帳本尾端提交與前綴推送

- merge 步驟 3 保證帳本變更只在尾端一個提交。推送範圍淨額 > 0 時，`prefix`＝尾端提交的父提交：`git push origin <prefix>:main` 先推修復本體（淨額恆 0，因帳本未變），尾端提交留本地。
- 修復棒在同一範圍把新列改 fixed ⇒ 淨額 ≤ 0 ⇒ 整段可推。
- 這一窗修不完：QV 判 `PARK` ⇒ 本地打 `*-wip-preserved` 標籤、封存、park（既有 SOP）。
- 確實無法修（外部阻塞）：移入外部阻塞帳並附外部證據座標（既有三本帳分類；外部阻塞筆數由 `print_external_blocked_count` 恆可見）。
- 守衛面缺陷：帳本列須附暴露證據；沒有證據者只進理論洞清單、不入帳、不計淨額（根 CLAUDE.md〈守衛面准入〉）。

---

## 5. 逃生口對稱（N2，REQ-AP-G1-03）

- `ledger_closing_guards.net_new_vs_closed_problems()` 讀 `AUTOSDD_NET_RATCHET_OFF` 時，若同時 `CLAUDECODE` 存在（Claude Code 衍生的任何 shell，主控與子代理皆有；本棒當回合 `$env:CLAUDECODE` 實查＝`1`）或 `AUTOSDD_UNATTENDED` 有設 ⇒ **OFF 無效**，印「逃生口只屬於人在自己終端機；Claude Code 衍生行程內設定無效」並照常判。
- WHY 不用 AP-A 提的 commit trailer `Net-Ratchet-Off-By: human`：trailer 是模型能寫的字串，不是「人」的證據；`CLAUDECODE` 是 harness 注入行程環境、判準在被呼叫程式內，與分類器無關、對主控與子代理對稱。
- 劃界：人若在 Claude Code 的 `!` 前綴殼內設 OFF，同樣無效（同一行程家族）；人的合法路徑＝自己的終端機。這是刻意的：讓「人用逃生口」必須是一個模型不能代做的動作。
- 理論洞（不立輪、不同輪修；〈守衛面准入〉P4）：其他由「agent shell 衍生的子行程」讀取的 `*_OFF`（非 hook 行程讀取者）未普查。普查指令留給 CLOSE：`git grep -n "_OFF\b" -- tools ':!tools/tests'` 逐站點標「讀取行程＝hook／agent 子行程」。

---

## 6. CI 排隊逾時自動重跑（G2，REQ-AP-CI-01）

- 落點：`tools/lib/ciwait/core.py`（現 127／400）新增 `classify_attempt(jobs_json) -> "queue_timeout"|"other"`；`wait()` 在某 run `conclusion=cancelled` 時以 `gh api repos/{o}/{r}/actions/runs/{id}/attempts/{n}/jobs` 取 jobs。
- 判準（全部成立）：該 attempt 至少一支 job `conclusion=cancelled ∧ steps==[] ∧ runner_name=="" ∧ 14.5 分 ≤ completed_at−created_at ≤ 16 分`，且同 ref 在 `[created_at, completed_at]` 間沒有更新的 run（排除 concurrency 自取消）。
- 命中 ⇒ `gh run rerun <id> --failed`（同 sha 至多 `CI_QUEUE_RERUN_MAX=2` 次）並繼續等；末行 `CI_WAIT_VERDICT=pass rerun=queue_timeout×<n>`；超過 ⇒ `CI_WAIT_VERDICT=fail reason=queue_timeout_exhausted`（rc 1，既有語意）。
- 每次命中落痕跡 `ci_queue_timeout {run, attempt, minutes}`；退役條件＝連續 7 天零命中（只記錄，不自動移除程式；退役由下一個觸及者依痕跡決定）。
- 不改 `runs-on`（§2 K=1 列）。

---

## 7. AskUserQuestion 類別閘（N1／N7；PRD R-4.5.12-3～5，REQ-AP-ASK-01）

- 接線：`.claude/settings.json` PreToolUse 新增 matcher `AskUserQuestion` → 既有 `sessionctl_guard.py`（新增一個分支，不新增 hook 檔；判準住新檔 `tools/lib/sessionctl/askgate.py`）。
- **可問人的定義（掌舵者 2026-11-25 原話）**：「『真正需要您決定的類別』==> 目前定義: 1. 會造成系統(本機, 專案, Gihub等)整個毀壞, 無法復原的情形 2. 目前Claude都使用訂閱制(須確認), 若非訂閱制, 有使用費用超過50美元」。據此放行類別只有三個（AP-A 報告的 `[BIZ]`／`[SECRET]`／`[VISUAL]`／`[HARNESS]` 全部退役）：

| 標籤 | 定義 | 機械可判部分 |
|---|---|---|
| `[IRREVERSIBLE]` | 會造成**任何系統**（本機、專案、GitHub、雲端服務、資料庫、帳號、第三方平台等，不限前三者）整體毀壞且無法復原的動作 | 問題必須另含一行 `系統：<名稱>`＋`不可復原原因：<一句>`（缺即阻斷）；可代決詞表命中照樣阻斷（「回不去」由程式能救的不算不可復原，例如有 `*-wip-preserved` 標籤、git 歷史、備份者） |
| `[COST]` | 帳號**非訂閱制**且該動作預估費用 > 50 美元 | 由 `askgate` 自己判計費姿態：讀 `sessionctl quota --json` 的 `billing` 欄（QV 設計 §3.3；來源與 `--pace` 派工前置行 `quota_messages.posture_line()` 同一份快取 `posture`：`credits_present`、`fallback_available`，加 spend 軸讀數）。`billing=subscription_only`（此帳號沒有 usage credits ⇒ 訂閱窗即硬牆、不會逐次計費）⇒ `[COST]` 一律阻斷；`billing=credits_fallback`（credits 可用，訂閱窗用完後會計費）或 `api_key`／`unknown` ⇒ 視為非訂閱制（判不出往保守＝讓人知道）；問題必須含 `預估：<n> 美元` 且 n > 50；換帳號（QV 設計 §7）後下一次判讀重判 |
| `[K1]` | SelfImproving K=1 決定（DEC 只認掌舵者真人發言） | 放行；但問題本文須寫明「須掌舵者親打」，選項不得包含可被直接當成決定的「核准」字樣（AskUserQuestion 只提示、不是決定載體） |

- 判準（`askgate.verdict(tool_input, env, billing) -> (allow: bool, reason)`；由上而下短路）：
  1. 無人窗口（`AUTOSDD_UNATTENDED`）⇒ 一律阻斷（沒有人能回答；`[IRREVERSIBLE]` 動作在無人窗口本來就不准做，改寫進 handback）。
  2. 任一問題缺三標籤之一 ⇒ 阻斷。
  3. 問題或選項命中**可代決詞表**（續跑、額度、park、換 session、交接、舊視窗、逃生口、`_OFF`、推送、合入、rebase、cherry-pick、重跑 CI、目視、裁決、要不要繼續）⇒ 阻斷，不論標籤。詞表住 `askgate.py` 單一常數，可擴不可縮（測試鎖）。
  4. 標籤各自的必填欄位（上表右欄）缺 ⇒ 阻斷；`[COST]` 遇訂閱制 ⇒ 阻斷。
  5. 其餘放行，落痕跡 `ask_allowed {category, sid, at, system|usd}`（再開症狀與 E2E 普查用）。
- 阻斷訊息（rc 2）：「這類決定由你代決：依最適方案決定，把 WHY 寫進帳本或 commit 訊息後繼續。只有三類可以問人：任何系統整體毀壞且不可復原（[IRREVERSIBLE]）、非訂閱制且預估超過 50 美元（[COST]）、K=1 決定（[K1]，須掌舵者親打）。」
- 同步改 `.claude/hooks/check_pending_handoff.py` 推回文案：先叫主控代決；只有上述三類才指路 AskUserQuestion（G9 的另一半）。另修兩個假推回（§13 G9 列）：描述分類規則或複述掌舵者定義的句子（「真正需要您決定的類別」「以後要請您決定的只有這兩類」）不是交棒——判準改為：句中「需要您／請您」緊接類別定義語（「類別」「只有」「定義」）或位於引號內 ⇒ 不算；同時 `check_claim_provenance.py` 對敘述過去事件的「被擋／擋下」（前文帶時間或事件座標：「先前」「當時」「L<n>」「<時刻>」）不當本場宣稱。兩者皆以真實語料重放驗證（TCS E2E-AP-ASK-02）。
- 不用 `updatedInput.answers` 代答（§2 的 WHY）。
- 劃界：模型可以把可代決的問題偽標成 `[IRREVERSIBLE]`，並寫一個看似合理的系統名避開詞表；結構上擋不下。補救＝`ask_allowed` 痕跡事後普查（TCS 再開症狀：放行者逐筆核對是否真屬三類），以及 Stop 端既有 K=1 語意；這是照實劃界，不再加碼守衛（R197「量、不挖」）。

---

## 8. 舊視窗事件驅動關閉（G8／G9；PRD R-4.5.12-1／2，REQ-AP-OW-01）

- 觸發：舊視窗自己的 Stop（`sessionctl_guard.py` Stop 分支）在「已交棒 ∧ 新 session 已 ack」時呼叫 `oldwin.on_old_stop(sid)`：寫 `oldwin_idle_hint` 事件，並以既有 `oldwin_sched.schedule_retry` 排一次 60 秒後的關閉檢查（`oldwin.eligible` 條件不變）。舊視窗真正閒下來的時刻就是它 Stop 的時刻。
- 重試：`oldwin.MAX_RETRIES = 3` 退役，改指數退避 `retry_at = last + min(60·2^k, 12h)`，總時長上限 12 小時（`AUTOSDD_OLDWIN_MAX_HOURS`，出廠 12）；到上限只記 `oldwin_retry_exhausted`（取代 `oldwin_retry_abandoned`）並在 `sessionctl status` 與 SessionStart 簡報顯示一行「舊視窗待關（原因 not_idle，第 n 次）」——**不交人**。
- 文案：刪除 `oldwin.py` 的 `_manual_text()`、`pending_manual_close()`、`reminder_lines()` 中「請手動關閉」字樣與 `sessionctl_guard.py` 對應文案，改為陳述事實（交棒後舊視窗收到真人提示的轉送／告知已由 `forward.py` 處理）。
- `status=shell` 長時間不變仍不強殺（R-4.5.11-3）。
- 與 `qw_prompt.py` 第 77 行的「請手動」字樣：屬 QuotaWall 提示，WP-HOOK 一併審視；若屬可代決動作即改寫，不屬者（例如 harness 信任對話框）保留並在 TCS 詞表例外清單逐筆列出。

---

## 9. 測試對真痕跡目錄的圍籬（N3，REQ-AP-FN-01）

- 前置普查（WP-FENCE 第一動作）：`git grep -n "\.autosdd" -- tools .claude ':!tools/tests'`，確認所有痕跡寫入者都經 `endurance_env.trace_dir()`；繞過者先收斂到該入口（同一 commit）。
- 圍籬（`tools/run_root_unittests.py`，比照 DEF-648 的 git 圍籬）：全套開始前把 `AUTOSDD_TRACE_DIR` 設到 `suite_tmp_*/traces`；開始時記下真 `~/.autosdd/traces` 每個檔的 (size, mtime)；結束時比對，圍籬期間新增的列只要帶 `%TEMP%`／`$TMPDIR` 路徑、`sc-*` 前綴或夾具 sid ⇒ 判洩漏、rc≠0、印檔名與首筆列。
- 平行 worker（`parallel_shard`）繼承同一環境變數；分片（`AUTOSDD_TEST_SHARD`）每片各自圍籬。
- 前置依賴：D649 修復棒合入後才派（與 HYG1 動同一 runner）。

---

## 10. 模組落點（依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

| 內容 | 落點 | SSOT §2 對應 | 備註 |
|---|---|---|---|
| 合入／推送判準 | 新套件 `tools/lib/autopilot/`（`__init__.py`、`merge.py`、`pushgate.py`、`ledgersplit.py`、`locks.py`、`verdict.py`） | 函式庫列（兩支以上檔 ⇒ 第一天成套件） | 不 import 其他套件；QV 判決以子行程呼叫 `tools/sessionctl.py quota --json` 取得（走資料、不跨套件 import，守 SSOT §2 第一列） |
| 指令入口 | 新 `tools/autopilot.py`（`merge`／`push`；薄殼） | 指令入口列 | 指令字面寫進本檔後即對外契約 |
| 推送範圍棘輪 | 既有 `tools/lib/ledger_closing_guards.py` | 存量扁平（缺陷帳本家族） | — |
| pre-push 匯出 base | 既有 `tools/git-hooks/pre-push` | — | 只加兩行 export |
| CI 排隊逾時 | 既有 `tools/lib/ciwait/core.py` | 既有套件 | — |
| 詢問類別閘 | 新 `tools/lib/sessionctl/askgate.py`；接線既有 `.claude/hooks/sessionctl_guard.py` | 既有套件（守衛面） | — |
| 舊視窗 | 既有 `tools/lib/sessionctl/oldwin.py`、`oldwin_sched.py` | 既有套件（守衛面） | — |
| worktree 起點 | 既有 `.claude/settings.json` | 守衛面 | — |
| 痕跡圍籬 | 既有 `tools/run_root_unittests.py` | — | — |
| 測試 | 新 `tools/tests/test_autopilot_merge.py`、`tools/tests/test_autopilot_push.py`；詢問閘併入既有 `tools/tests/test_sessionctl_hooks.py`；舊視窗併入既有 `tools/tests/test_sessionctl_oldwin.py`；CI 分類併入既有 `tools/tests/test_ci_wait.py`；圍籬併入既有 runner 測試檔（WP-FENCE 現查） | 測試列 | 新檔兩支；CLOSE 一次重釘 |
| 真機 E2E | `tools/lib/realverify/cases/autopilot.py`（新家族檔） | realverify 既有落點 | — |
| 痕跡 | `~/.autosdd/autopilot/`（merge.jsonl、conflict-*、fix-*.md）、`~/.autosdd/traces/`（ask_allowed、ci_queue_timeout、oldwin 事件） | repo 外 | 經 `endurance_env.trace_dir()` 或同層新函式 |
| CI 接線 | compat-ci 兩支 workflow `paths` 加 `tools/lib/autopilot/**` 與 `tools/autopilot.py` | CI 接線列 | CLOSE 同 commit；`test_ci_paths_cover_root_consumers.py` 鎖 |
| 不可進化面 | `params.json` `non_evolvable_globs` 加 `tools/lib/autopilot/**`、`tools/autopilot.py` | 不可進化面列（合入／推送屬守衛類） | CLOSE |
| SSOT §3 登記 | 規格階段以純文字說明列預告；實作 commit 後 CLOSE 改反引號登記 | §3 | 落點鎖要求反引號路徑存在 |

---

## 11. LOC 處置（SD-0 當回合實量；實作前現查 `python AutoClaude/tools/check_loc_budget.py --json`）

| 檔 | 現值／上限 | 估計新增 | 處置 |
|---|---|---|---|
| `tools/lib/autopilot/*`（新） | — ／400 每檔 | merge 約 250、pushgate 約 200、ledgersplit 約 120 | 依職責分檔，任一檔逼近 360 即再拆 |
| `tools/autopilot.py`（新，cli 750） | — | 約 80 | — |
| `tools/lib/ledger_closing_guards.py` | 175／400 | +30 | 無需抽出 |
| `tools/lib/ciwait/core.py` | 127／400 | +60 | 無需抽出 |
| `tools/lib/sessionctl/oldwin.py` | 354／400 | 退避 +10、刪文案 −15 | 若淨增 >40：`bg_shells()`（L149～L200）搬 `oldwin_sched.py`（164／400）或新檔 `oldwin_bg.py` |
| `tools/lib/sessionctl/oldwin_sched.py` | 164／400 | +20 | 無需抽出 |
| `tools/lib/sessionctl/askgate.py`（新） | — | 約 80 | — |
| `.claude/hooks/sessionctl_guard.py` | 90／750 | +8 | 無需抽出 |
| `.claude/hooks/check_pending_handoff.py` | 226／750 | ±5 | 無需抽出 |
| `tools/run_root_unittests.py` | 現查 | +40 | WP-FENCE 開工前現查其分級 |

---

## 12. 工作包、持有面與順序（鐵律七）

| WP | 內容（本檔節） | 持有面 | 守衛面 | 與誰串行 |
|---|---|---|---|---|
| WP-QV | QV 設計全部 | quota 族＋sessionctl watch／park | 是 | 先於 WP-AC |
| WP-AC | QV 設計 §7 | 同上 | 是 | WP-QV 收工親驗後 |
| WP-MERGE | §3、§4、§5 | `tools/lib/autopilot/**`、`tools/autopilot.py`、`ledger_closing_guards.py`、`tools/git-hooks/pre-push` | 否 | 可與 WP-AC、WP-CI 並行（持有面不交集） |
| WP-CI | §6 | `tools/lib/ciwait/core.py`、`tools/ci_wait.py`、`tools/tests/test_ci_wait.py` | 否 | 可並行 |
| WP-FENCE | §9 | `tools/run_root_unittests.py`（＋普查後的繞過站點） | 否 | D649 合入後；與 WP-MERGE 不交集 |
| WP-HOOK | §3.1 settings、§7、§8、QV 設計的兩個 hook 改動 | `.claude/hooks/**`、`.claude/settings.json`、`sessionctl/oldwin*.py`、`sessionctl/askgate.py` | 是 | 單一 staged diff 交主控親套；WP-QV 之後（要 QV 字面） |
| CLOSE | 重釘（c1c2、`_TREE_FILE_FLOORS`、`SPECIAL_FILES` 下修、skip、E501、MIN_TESTS／ONBOARDING）、CI paths、`non_evolvable_globs`、SSOT §3 反引號登記、根 CLAUDE.md（守衛面清單加 `tools/lib/model_window_table.py`；現查表加 `sessionctl quota`、`autopilot merge／push`；〈換 session 的 SOP〉`park --why`→`--next-est`）、QuotaWall DES 註記、帳本列、AP-A 報告轉存證據檔 | 全部鎖檔 | — | 以上全部之後 |
| QA | 獨立審查（opus，唯讀）＋E2E 全跑入帳 `docs/06_quality/RealVerify_Result_Ledger.md` | 唯讀 | — | CLOSE 之後 |

紀律：並行包一律不重釘、不寫帳本，交卷只回報建議值；`tools/git-hooks/pre-push` 只屬 WP-MERGE；`.claude/settings.json` 只屬 WP-HOOK。

---

## 13. 守衛面准入：暴露證據座標

| 條目 | 守衛面檔 | 暴露證據 |
|---|---|---|
| `worktree.baseRef: "head"` | `.claude/settings.json` | 逐字稿 L683（代理起點 2a56d3ff）、L651～L813（cherry-pick 衝突）；ADR-XPLAT-006:228 reflog |
| 詢問類別閘 | `.claude/settings.json`、`.claude/hooks/sessionctl_guard.py`、`tools/lib/sessionctl/askgate.py` | 逐字稿 L2431→L2432（6 小時 19 分阻塞）；N7 普查 6 筆可代決提問 |
| 推回文案與兩個假推回 | `.claude/hooks/check_pending_handoff.py`、`.claude/hooks/check_claim_provenance.py` | 逐字稿 L221、L222、L239（兩支 hook 互相矛盾）；sid 406454ea 2026-11-25 兩次 `check_pending_handoff` 假推回：①「真正需要您決定的類別」（描述分類規則，命中「需要您」）②「以後要請您決定的只有這兩類」（複述掌舵者定義，命中「請您」），本回合皆無待決事項；同時 `check_claim_provenance` 把敘述過去事件的「被擋」「擋下」當本場宣稱（登記於 sid 406454ea scratchpad `def647_pending.md` 末條，CLOSE 轉存證據檔） |
| 舊視窗事件驅動與退避 | `tools/lib/sessionctl/oldwin.py`、`oldwin_sched.py`、`.claude/hooks/sessionctl_guard.py` | `oldwin/events.jsonl` 2026-11-24 20:50:38～21:08:03；逐字稿 L181 |
| 非守衛面（不需證據，仍附） | `ledger_closing_guards.py`、`ciwait/core.py`、`run_root_unittests.py`、`tools/lib/autopilot/**` | G1／N2、G2、N3、G4／G10 各列 |

---

## 14. 修復不留後遺症三問

1. **另一台機器會不會回來？** `worktree.baseRef` 寫在 repo 的 `.claude/settings.json`，隨 clone 走；`CLAUDECODE` 由 harness 注入、跨平台；ci_wait 判準只吃 GitHub API 欄位；merge 的拋棄式 worktree 用平台暫存目錄（`tempfile.gettempdir()`）。
2. **有沒有文件／座標不一致？** CLOSE 同 commit 收齊：CI paths、`non_evolvable_globs`、SSOT §3、根 CLAUDE.md（鐵律七檢查表第 4 條「收尾單人窗口」加註 `autopilot merge` 為其機械形態；現查表；換 session SOP）、記憶檔 `ci-wait-no-handwritten-poll.md`（新增 `queue_timeout` 一句）。
3. **有沒有「之後再看」？** 兩項照實列：§5 其他 `*_OFF` 讀取行程普查（理論洞 P4，附普查指令）；macOS runner 根治屬 K=1（§2）。

---

## 15. 與 AP-A 報告的差異（SD-0 決定）

| 項 | AP-A | SD-0 | WHY |
|---|---|---|---|
| G3 起點 | WorktreeCreate hook（待查）或任務書首動作 rebase | `worktree.baseRef: "head"`＋merge rebase 第二道；不採 WorktreeCreate、不寫任務書 rebase | 官方設定鍵已存在；WorktreeCreate 要求 repo 外目錄且子代理結束不清理 |
| N2 | commit-msg 強制 `Net-Ratchet-Off-By: human` trailer | `CLAUDECODE`／`AUTOSDD_UNATTENDED` 下 OFF 無效 | trailer 是模型可寫字串，不構成「人」的證據 |
| 帳本拆分 | 「autopilot merge 自動拆分」 | 帳本檔變更整批剝離成尾端單一提交 | 規則簡單、可證：前綴恆不含帳本變更 ⇒ 淨額恆 0 |
| 詢問閘落點 | 新 hook 或併入 sessionctl_guard | 併入 `sessionctl_guard.py`＋判準 `askgate.py` | 不新增 hook 檔（liveness 註冊、載具、CLAUDE.md 總表成本） |
| 詢問閘類別 | `[K1]`／`[BIZ]`／`[SECRET]`／`[VISUAL]`／`[HARNESS]` 五類 | 只剩 `[IRREVERSIBLE]`（任何系統整體毀壞不可復原）、`[COST]`（非訂閱制且 > 50 美元）、`[K1]` | 掌舵者 2026-11-25 定義（§7 原話）；業務、機密、目視、harness 對話框改由主控代決或載具替代 |
| 詢問閘判準 | 只看標籤 | 標籤＋各類必填欄＋可代決詞表（詞表優先）＋`[COST]` 讀計費姿態＋無人窗口全擋 | 只看標籤可被偽標；詞表讓最常見的可代決題無法靠標籤通過 |
| AskUserQuestion 逾時 | 「沒有逾時」 | harness 有 user 層 `askUserQuestionTimeout`，但不採用 | §2；PRD R-4.5.12-5 |
| pre-push 乾跑 | 「乾跑模式」（未定義） | 合成 stdin 直接呼叫，pre-push 不改 | 零新旗標，leg 集合天然一致 |
| 新增 REQ | — | REQ-AP-WT-01（worktree 起點） | G3 修法換成設定鍵後需要自己的驗收 |
