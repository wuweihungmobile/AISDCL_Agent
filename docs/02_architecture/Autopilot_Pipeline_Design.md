# 自動駕駛開發管線設計（Autopilot Pipeline Design）

- 版本：v1.3（SD-3，2026-11-25；依 QA 第三輪 FAIL〔P2×2、P3×4〕修訂；規格階段，實作未開始）。v1.0（SD-0）→ v1.1 的逐條處置見 §17；v1.1 → v1.2 見 §18；v1.2 → v1.3 見 §19。
- 立案：掌舵者 2026-11-25 原文「以後這種不用詢問, 我要達到是真正的自動駕駛開發, 若無法達到這個目標, 請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查,請確認以上功能都已經解決完備！」；授權最佳化、不顧成本的方案由主控代決。
- 上游：AP-A Architect＋SA 報告（sid `406454ea-91fc-4481-9c11-b28ed7d9e95f` scratchpad `ap_arch_report.md`，CLOSE 窗口轉存證據檔）。PRD 只收本檔 §7（詢問類別閘）與 §8（舊視窗）兩項＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.5.12（R-4.5.12-1～5，及其【v2.1.29 勘誤】）與 §16.6 2026-11-25 第二列；其餘（合入、推送、帳本棘輪、CI 等待、測試圍籬）屬開發管線，只住本檔。
- 架構決策：合入管線的驗證載具與 harness 內建隔離的使用，由 `docs/04_planning/ADR/ADR-XPLAT-018-autopilot-merge-carrier.md` 定案（**部分取代** ADR-XPLAT-006 §7 兩列與爭點 4 的裁決，逐條回應見該 ADR）。
- 兄弟設計：`docs/02_architecture/QuotaVerdict_AccountSwitch_Design.md`（額度判決與換帳號；本檔的推送閘與派工決策只讀它的 `QUOTA_VERDICT=` 行）。
- 驗收：`docs/03_testing/contracts/TCS-Autopilot-20261125.md`（REQ-AP-MG-01～03、REQ-AP-G1-01～04、REQ-AP-ASK-01～02、REQ-AP-CI-01、REQ-AP-OW-01、REQ-AP-FN-01、REQ-AP-WT-01）。

---

## 0. 一頁結論

| 缺口 | 修法（一句） | 節 |
|---|---|---|
| G3 代理 worktree 起點是 origin/main | 專案 settings 設 `worktree.baseRef: "head"`（官方支援的設定，現查證實）；merge 的 rebase 留作第二道；殘留代理分支有普查鎖 | §3.1 |
| G4／G10 合入靠手工、合入後紅到推送才發現 | `python tools/autopilot.py merge`：repo 外**獨立 clone**（不是 linked worktree）rebase → 略過已吸收 → 補連動鎖 → 載具自證（import 必須解析到 clone）→ 跑 pre-push 同款全套 → 綠才 fast-forward 並清理；冪等 | §3、ADR-XPLAT-018 |
| G1 帳本淨額棘輪只在提交時判 | 判準移到**推送範圍**：逐 ref 比 pre-push stdin 的 `<local_sha>` 對 `<remote_sha>`（不讀工作樹）；提交期只出聲；帳本變更集中到尾端提交，可「前綴推送」 | §4 |
| N2 子代理可自設 `*_OFF` | 提交／推送期治理閘逃生口族（`AUTOSDD_NET_RATCHET_OFF`、`AUTOSDD_SNAPSHOT_GATE_OFF`）在 Claude Code 衍生的行程內（`CLAUDECODE`）與無人窗口一律無效並出聲；判準住單一共用述詞 `human_escape.honored()` | §5 |
| G2 macOS 排隊 15 分鐘被取消 | `ci_wait` 新分類 `queue_timeout`，自動 `gh run rerun --failed`（同 sha 至多 2 次） | §6 |
| N1／N7 AskUserQuestion 阻塞數小時 | PreToolUse（matcher `AskUserQuestion`）類別閘：只放行 `[IRREVERSIBLE]`／`[COST]`／`[K1]`；必填欄位齊全者不受名詞詞表影響，只擋「要不要＋可代決動作」句型；順修 G9 的兩個假推回 | §7 |
| G8／G9 舊視窗關閉重試 3 次即交人 | 事件驅動（舊視窗自身 Stop）＋指數退避（上限 12 小時）；刪除「請手動」文案；字樣鎖掃本 PRD 機制的全部訊息家 | §8 |
| N3 單元測試污染真痕跡目錄 | `run_root_unittests.py` 加痕跡圍籬（判準住新扁平 `tools/lib/suite_fence.py`，runner 先抽出再加） | §9 |

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
| 載具假綠（F-04） | SD-0 自己的 linked worktree 無 `.venv`，pre-commit 三層印 ⚠ 未執行（sd0_report §1）；SD-1 同一現象重現（本棒 worktree 提交時 dispatcher 印「找不到 repo 根層 .venv 直譯器」）；ADR-XPLAT-006 爭點 5 的 editable `.pth` 實查 |

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
| GitHub macOS runner 排隊逾時 | 外部、11-24 起新現象 | AP-A §1 G2 | 只能分類＋重跑（§6）。換付費 runner 屬 `[COST]` 類（非 Claude 服務、逐分鐘計費）；**現況未觸發**（分類＋重跑已足），不問人、不代決花錢；觸發條件＝`queue_timeout_exhausted` 連續 7 天每天出現（§6） |
| print 模式能否呼叫 AskUserQuestion | **未查證**（QA-S F-23） | — | TCS E2E-AP-ASK-01 第一動作以 `claude-code-guide` 現查；不可用 ⇒ 該列改用「真 hook 二進位＋錄製的 PreToolUse payload」載具（TCS 已寫備援） |
| 互動 UI 無法程式目視 | harness UI | — | 替身＋真排程驗到開窗前一刻；被動觀測痕跡（TCS 備援欄） |

---

## 3. 合入管線 `autopilot merge`（G3／G4／G10）

### 3.1 G3：派工起點

- 第一道：`.claude/settings.json` 加 `"worktree": {"baseRef": "head"}`（守衛面檔，WP-HOOK 以 staged diff 交主控親套；暴露證據見 §13）。效果：之後所有 `isolation: "worktree"` 子代理從主控當下的本地 HEAD 分支。
- 已知副作用（官方文件）：「Inside a worktree, `"head"` resolves to that worktree's `HEAD`」——主控若本身在 worktree 內派工，起點是該 worktree 的 HEAD，這正是要的。fresh 模式的「同名 worktree 重開會被重置到預設分支」行為在 `head` 下不適用。
- 第二道（保留）：merge 第 1 步一律 rebase 到本地 HEAD，並記錄 `merge-base` 與派工當時 HEAD（任務書寫入 `--base-at-dispatch`）是否相等；不等 ⇒ 痕跡 `base_drift`，仍照 rebase 處理（不中止），用來偵測設定被改回。
- 與 ADR-XPLAT-006 爭點 4（「不可直接開 harness 內建隔離」）的關係：該裁決的三項事實在本設計下各自處置——①從 `origin/main` 播種 ⇒ `baseRef: "head"` 消除；②建立具名分支（違反「只用 main」）⇒ 代理分支**只存活到合入**：merge 第 6 步 `git branch -d` 收回，main 是唯一長存分支；③不回收 ⇒ merge 第 6 步 `git worktree remove`（不帶 `--force`）＋**殘留普查鎖**（REQ-AP-WT-01 AC-WT-01c：`git worktree list` 與 `git branch --list "worktree-agent-*"` 中，合入痕跡已 ok／noop 者殘留即紅；`sessionctl status` 顯示殘留數）。逐條全文見 ADR-XPLAT-018 §3。harness 內建隔離只給**寫入者**（代理）用；**驗證**一律在 §3.2 的獨立 clone（不在代理的 linked worktree 裡驗）。
- 派工任務書範本不再寫「首動作 `git rebase main`」（AP-A 備援案），以免代理在自己的 worktree 裡手動 rebase 造成衝突狀態殘留。

### 3.2 指令與步驟

```
python tools/autopilot.py merge --branch <代理分支> [--base-at-dispatch <sha>] [--dry-run]
```

| 步 | 動作 | 失敗結局（末行 `MERGE_VERDICT=`） |
|---|---|---|
| 0 | 取 repo 鎖 `~/.autosdd/autopilot.lock`（單一窗口；鐵律七「收尾單人窗口」的機械化）；主樹須乾淨；暫存目錄可用空間 ≥ 2×（主樹已追蹤檔總大小）（Windows 無 clonefile，工作樹全額佔碟，ADR-XPLAT-006 §2.3）；暫存目錄與主樹不同卷（兩路徑 `os.stat().st_dev` 不等）時再加計物件庫大小（`git count-objects -v` 的 `size-pack`＋`size`；v1.3，R-02：跨卷時 git 複製物件、不硬連結） | `busy`／`dirty`／`no_space` |
| 1 | 在 **repo 外**（`tempfile.gettempdir()` 下 `autopilot-<ts>`，避開 `.claude/worktrees` 掃描面）以 `git clone --no-checkout <主樹路徑> <clone>` 建**獨立 clone**（自己的 `.git`：`refs/stash`、`.git/config`、`.git/info/exclude` 結構上不共用；物件同卷時 git 自動硬連結、跨卷時複製）。**不帶 `--local`**（v1.3，R-02）：明寫它會把硬連結失敗變成致命錯誤，主控機（暫存 `C:`、repo `D:`）實測 rc 128，見 ADR-XPLAT-018 D1；clone 內以主樹本地 HEAD 建拋棄式分支，把 `<branch>` 自 merge-base 起的提交逐一套上（`git rebase --onto` 等價） | 衝突 ⇒ 產衝突包（每個衝突檔的三方內容與提交訊息，寫到 `~/.autosdd/autopilot/conflict-<ts>/`），`git rebase --abort`，回 `conflict`；主控派解衝突代理，不手解 |
| 2 | 已被吸收的提交略過：`git patch-id --stable` 比對主樹本地 HEAD 至 merge-base 之間的提交 | — |
| 3 | 帳本檔（`docs/06_quality/AutoSDD_Defect_Log*.md`、外部阻塞帳、結構性長債帳）的變更自各提交剝離，集中成**尾端單一提交**（§4.3） | 剝離後某提交為空 ⇒ 丟棄該提交並記痕跡 |
| 4 | 補連動鎖（只套工具算出、在既有上限內的值）：`--print-guard-lines` 建議值、`_TREE_FILE_FLOORS`、E501 存量、skip 普查、`MIN_TESTS`＋ONBOARDING 同步；`repin_growth_problems()` 非空 ⇒ 停 | `repin_blocked`（不改上限常數） |
| 4.5 | **載具組裝與自證**（ADR-XPLAT-018 §2；回應 ADR-XPLAT-006 爭點 5）：①clone 根建 `.venv` 連結指向主樹 `.venv`（Windows＝directory junction，POSIX＝symlink；pre-push 的 `pick_repo_python` 只認 `$TOPLEVEL/.venv`，DEF-200-315）；②全套的環境一律設 `PYTHONPATH=<clone>/AutoClaude<sep><clone>/tools`（`os.pathsep`），讓 clone 的原始碼排在 editable `.pth` 之前；③自證：以 clone 的 `.venv` 直譯器、同一份環境，在 clone 根執行 `import autoclaude, lib.quota_policy` 並印 `__file__`，兩者都必須位於 clone 之下；④（v1.2，N-03；ADR-XPLAT-018 D5）依 `autopilot/carrier.py` 的 `CARRIER_LOCAL_STATE` 白名單處置機器本地狀態：`.dev_env_state.json` 複製並驗 clone 內存在且內容雜湊等於主樹；**`.env` 不進 clone**（v1.3，R-02；取代 v1.2 的同卷硬連結）——在 clone 的 `.git/` 寫標記 `autopilot-clone`，全套環境設 `AUTOSDD_LOCAL_ENV_FILE=<主樹>/.env`，env 鏈本機層的兩個讀者家（`quota_env_layers`、引擎 `config.py` 的 `_ENV_FILES`）在「變數有設＋標記存在＋讀預設 repo 根」時改從該路徑唯讀讀取；驗：clone 根無 `.env`、以 clone 直譯器印出兩個讀者家的本機層路徑皆解析到主樹 `.env`（規則全文 ADR-XPLAT-018 D5〈`.env` 路徑覆寫〉）；產物與快取不帶 | 任一不在 clone 之下 ⇒ `carrier_leak`（附兩個實際路徑），不跑全套；白名單項缺、雜湊不等、clone 根有 `.env`，或本機層路徑沒有解析到主樹 `.env` ⇒ `carrier_divergence`（附缺項），不跑全套 |
| 4.7 | **基線**（v1.2，N-03；ADR-XPLAT-018 D5 第 2 點）：同一 clone、同一環境，在主樹本地 HEAD（未套代理提交）上跑一次步驟 5 的同款全套——clone 內 `git switch --detach <主樹 HEAD sha>` 跑、跑完 `git switch <拋棄式分支>` 切回（clone 工作樹乾淨，皆非鐵律五毀滅形態；同鍵命中快取時不切換）；以 `(主樹 HEAD sha, 白名單內容雜湊, 主樹 .venv 直譯器路徑)` 為鍵快取於 `~/.autosdd/autopilot/baseline.jsonl`，同鍵綠者重用 | 基線紅本身不中止：記下紅 leg 集合交步驟 5 判定 |
| 5 | 跑 pre-push 同款全套：以合成 stdin（`refs/heads/main <新 sha> refs/heads/main <origin/main sha>`）在 clone 內直接呼叫 `<clone>/tools/git-hooks/pre-push`，環境同 4.5；經 `sessionctl runlong`／`waitfor` 分段等待（子代理快取壽命） | 與 4.7 基線對照：基線綠＋候選紅 ⇒ `red`（附失敗 leg 與末段 40 行）；候選紅 leg ⊆ 基線紅 leg ⇒ `carrier_divergence legs=<…>`（載具或主樹本身的問題，不算代理的；產修復任務書、不 ff）；候選多出基線沒有的紅 leg ⇒ `red`（只列多出者） |
| 6 | 全綠 ⇒ 主樹 `git fetch <clone> <拋棄式分支>` 後 `git merge --ff-only FETCH_HEAD`；刪 clone 的 `.venv` **連結本身**（不得遞迴進目標；Windows 以 `os.rmdir` 刪 junction、POSIX 以 `os.unlink`，刪前驗 `is_junction()`／`is_symlink()`，驗不到即中止清理並記痕跡）；再刪 clone 目錄；代理 worktree `git worktree remove <路徑>`（**不帶 `--force`**）；`git branch -d <代理分支>` | `ff_refused`（主樹在步驟 0 後被動過） |
| 7 | 末行 `MERGE_VERDICT=ok sha=<新 HEAD>` | — |

- **冪等**：每步落痕跡 `~/.autosdd/autopilot/merge.jsonl {branch, step, sha, verdict}`；重跑同一指令時，步驟 2 會把全部提交判為已吸收 ⇒ `MERGE_VERDICT=noop`。
- **不留半套**：任何非 ok 結局都在 `finally` 依步驟 6 的同一套「先刪連結、再刪目錄」移除 clone，並還原主樹（主樹在步驟 6 之前從未被寫）。
- 禁止形態（鐵律五）：不用 `git stash`、`git checkout --`、`git reset --hard`、`git clean`；中止只用 `git rebase --abort`／`git cherry-pick --abort`（皆不在毀滅性清單）。
- **驗證測的是合入樹的證明**：步驟 4.5 的自證（每次執行都做，fail-closed）＋ TCS AC-MG-03b 的紅綠自證（只在 clone 的三個子樹各植一個會讓該 leg 轉紅的突變、主樹不植 ⇒ 全套必紅；拿掉 `PYTHONPATH` 注入的突變 MU-MG-6 必須讓這條 AT 轉紅）。

### 3.3 與 pre-push 的關係（REQ-AP-MG-02）

pre-push 本身不改。「乾跑」＝以合成 stdin 呼叫它，leg 集合天然相同；`tools/git-hooks/pre-push` 已逐行解析 stdin 的 `<local_ref> <local_sha> <remote_ref> <remote_sha>`（現行第 100 行 `while read -r local_ref local_sha remote_ref remote_sha`），不需新旗標。§4.1 的推送範圍棘輪在同一個逐行迴圈內對每一 ref 呼叫。

---

## 4. 推送閘 `autopilot push` 與推送範圍棘輪（G1）

### 4.1 棘輪判準移到推送範圍（`tools/lib/ledger_closing_guards.py`）

| 階段 | 如何得知 | 比較對象（F-05） | 淨額 > 0 時 |
|---|---|---|---|
| 推送期 | pre-push 在 stdin 逐行迴圈內，對每一行 `<local_ref> <local_sha> <remote_ref> <remote_sha>` 呼叫一次棘輪，帶 `AUTOSDD_NET_RATCHET_PHASE=push`、`AUTOSDD_NET_RATCHET_LOCAL=<local_sha>`、`AUTOSDD_NET_RATCHET_BASE=<remote_sha>`（`remote_sha` 全零＝新分支 ⇒ 既有 merge-base 回退值；`local_sha` 全零＝刪除遠端 ref ⇒ 該行跳過） | `git show <local_sha>:<帳本>` 對 `git show <base>:<帳本>`；**不讀工作樹、不讀 HEAD** | 阻斷（rc≠0）；多行時任一行淨額 > 0 即阻斷，訊息逐行列 ref |
| 提交期 | 未設 `PHASE`（pre-commit 路徑） | `git show HEAD:` 對工作樹（現行） | **只出聲**、不阻斷（發現輪可先提交保全） |
| CI | workflow 未匯出 base | `HEAD`（與現況相同：CI 樹＝HEAD，淨額恆 0） | 照實劃界：CI 不判推送範圍；推送範圍的唯一閘是 pre-push |

- WHY 比 `<local_sha>`：前綴推送（`git push origin <prefix>:main`）時，工作樹與 HEAD 都還含尾端的新未結列；比工作樹或 HEAD 會把前綴推送自己擋下，§4.3 的出口失效。pre-push stdin 的 `<local_sha>` 正是「這次真的要送出去的那一點」。
- 這是收緊：現況「提交後即不可見」的洞（提交時用逃生口、推送時棘輪看不到）被補上。

### 4.2 推送流程

```
python tools/autopilot.py push [--dry-run]
```

1. 讀 `sessionctl quota --json` 判決：非 `CONTINUE` ⇒ 不推、依判決處置（QV 設計 §3.5／§3.6）。
2. 乾跑 pre-push（§3.3；在主樹，因主樹即合入結果且有自己的 `.venv`）。紅 ⇒ 依 pre-push 失敗 leg 分類產修復任務書（`~/.autosdd/autopilot/fix-<ts>.md`：失敗 leg、末段輸出、涉及檔），末行 `PUSH_VERDICT=red brief=<路徑>`，主控派修復棒。
3. 淨額 > 0（推送範圍）⇒ 對每筆新未結 DEF 產同輪修復任務書（帳本列＋證據檔座標）；末行 `PUSH_VERDICT=net_positive briefs=<n> prefix=<sha|none>`。
4. 綠 ⇒ `git push origin <sha>:main` → 背景 `python tools/ci_wait.py --commit <完整 sha>` → `CI_WAIT_VERDICT=fail` 且非 `queue_timeout` ⇒ 產修復任務書。

### 4.3 帳本尾端提交與前綴推送

- merge 步驟 3 保證帳本變更只在尾端一個提交。推送範圍淨額 > 0 時，`prefix`＝尾端提交的父提交：`git push origin <prefix>:main` 先推修復本體——此時 pre-push stdin 的 `<local_sha>`＝`prefix`，帳本在該點與 `<remote_sha>` 相同 ⇒ 淨額恆 0 ⇒ 放行（即使工作樹與 HEAD 含尾端新列）；尾端提交留本地。
- 修復棒在同一範圍把新列改 fixed ⇒ 淨額 ≤ 0 ⇒ 整段可推。
- 這一窗修不完：判決為 `PARK` ⇒ 本地打 `*-wip-preserved` 標籤、封存、park（既有 SOP）。
- 確實無法修（外部阻塞）：移入外部阻塞帳並附外部證據座標（既有三本帳分類；外部阻塞筆數由 `print_external_blocked_count` 恆可見）。
- 守衛面缺陷：帳本列須附暴露證據；沒有證據者只進理論洞清單、不入帳、不計淨額（根 CLAUDE.md〈守衛面准入〉）。

---

## 5. 提交／推送期治理閘逃生口族（N2；REQ-AP-G1-03、REQ-AP-G1-04；主控代決 ②）

- **單一共用述詞**：新扁平檔 `tools/lib/human_escape.py`，函式 `honored(name: str, env) -> tuple[bool, str]`：`env[name]` 非空 ∧ `CLAUDECODE` 不存在 ∧ `AUTOSDD_UNATTENDED` 不存在 ⇒ `(True, "")`；`env[name]` 非空但後兩者任一存在 ⇒ `(False, "逃生口只屬於人在自己終端機；Claude Code 衍生行程內設定無效")`，呼叫端照常判並印該句；未設 ⇒ `(False, "")`。族內每一個讀取點都**必須**經它判斷，不得各自讀 `os.environ`（`QV::`／`CR::` 鎖：AST 掃族成員名稱的直接環境讀取，只准出現在 `human_escape.py`）。
- **族成員**（常數 `HUMAN_ONLY_ESCAPES`，住 `human_escape.py`；只增不減，後設鎖）：
  - `AUTOSDD_NET_RATCHET_OFF`（`ledger_closing_guards.net_new_vs_closed_problems()`；現行 `ledger_closing_guards.py:42-55` 的直接讀取改經 `honored()`）。
  - `AUTOSDD_SNAPSHOT_GATE_OFF`（SelfImproving 帳本 DB 案 AC-LD-12-3 的快照閘；**快照閘尚未實作**——實作時必須經 `honored()`，由該案 TCS 補 AT；本輪交主控以 OI 登記，見 §12 CLOSE 與 TCS §5）。
- WHY 不用 AP-A 提的 commit trailer `Net-Ratchet-Off-By: human`：trailer 是模型能寫的字串，不是「人」的證據；`CLAUDECODE` 是 harness 注入行程環境、判準在被呼叫程式內，與分類器無關、對主控與子代理對稱（本棒當回合 `$env:CLAUDECODE` 實查＝`1`，SD-0 同）。
- 劃界：人若在 Claude Code 的 `!` 前綴殼內設 OFF，同樣無效（同一行程家族）；人的合法路徑＝自己的終端機。這是刻意的：讓「人用逃生口」必須是一個模型不能代做的動作。
- **`*_OFF` 普查結果**（F-21；SD-1 當回合 `git grep -n -E "AUTOSDD_[A-Z_]+_OFF" -- tools ':!tools/tests' ':!tools/lib/realverify' ':!tools/probe'`）。判準：讀取行程是 hook（環境在 claude 啟動時定、模型改不到）還是 agent 子行程（模型可在指令裡設）；方向是「放寬閘門」還是「關掉自動化」。

| 變數 | 讀取點 | 讀取行程 | 方向 | 處置 |
|---|---|---|---|---|
| `AUTOSDD_NET_RATCHET_OFF` | `ledger_closing_guards.py` | agent 子行程（git pre-commit／pre-push） | 放寬閘門 | 入族（本節） |
| `AUTOSDD_SNAPSHOT_GATE_OFF` | （未實作） | agent 子行程（pre-commit） | 放寬閘門 | 入族（代決 ②） |
| `AUTOSDD_GIT_GUARD_OFF` | `shell_tokens.py`（`block_destructive_git.py` hook）；`ledger_closing_guards.py:43` 只在註解提及 | hook | 放寬閘門 | 不入族：hook 行程環境模型改不到（根 CLAUDE.md 已載「模型碰不到」） |
| `AUTOSDD_CONTEXT_GUARD_OFF`、`AUTOSDD_QUOTA_GUARD_OFF` | `quota_gate.py`、`quota_policy_env.py`（`context_budget_guard.py` hook） | hook | 放寬閘門 | 不入族：同上 |
| `AUTOSDD_SESSIONCTL_GUARD_OFF`、`AUTOSDD_PARK_GUARD_OFF` | `sessionctl/forward.py`、`qw_prompt.py`、`park.py`、`qw_guard.py`（`sessionctl_guard.py` hook） | hook | 放寬閘門 | 不入族：同上 |
| `AUTOSDD_QUOTA_BURNDOWN_OFF` | `quota_burndown.py`、`quota_policy_env.py` | hook 與 agent 子行程（`--pace`、`sessionctl quota`）皆讀 | 改變 `cap` 輸入 | 不入族；**登記理論洞**：模型在指令裡設它可讓 CLI 判決的 `cap` 與 hook 判決不同（兩個答案）。無暴露證據（R197 量、不挖），進〈理論洞清單〉 |
| `AUTOSDD_KEEPWARM_OFF`、`AUTOSDD_QUOTAWALL_OFF`、`AUTOSDD_OLDWIN_AUTOCLOSE_OFF`、`AUTOSDD_RESUME_OFF`、`AUTOSDD_SENTINEL_OFF`、`AUTOSDD_SI_PATROL_OFF`、`AUTOSDD_CONTEXT_SIGNAL_OFF` | `sessionctl/keepwarm.py`、`qw_calc.py`、`qw_guard.py`、`qw_verdict.py`、`oldwin.py`、planner、`session_brief.py`、`sentinel_lifecycle.py`、`endurance_env.py`、`dispatch_granularity.py`、`parallel_shard.py`、`park_register.py`、`quota_messages.py`、`selfimproving/patrol.py`、`patrolreport.py` | 兩者皆有 | 關掉自動化（不放寬任何閘） | 不入族：方向是「少做」，不是「繞過檢查」；`SENTINEL_OFF`／`RESUME_OFF` 已有 SessionStart 🔴 出聲（DEF-200-561） |

---

## 6. CI 排隊逾時自動重跑（G2，REQ-AP-CI-01）

- 落點：`tools/lib/ciwait/core.py`（現 127／400）新增 `classify_attempt(jobs_json) -> "queue_timeout"|"other"`；`wait()` 在某 run `conclusion=cancelled` 時以 `gh api repos/{o}/{r}/actions/runs/{id}/attempts/{n}/jobs` 取 jobs。
- 判準（全部成立）：該 attempt 至少一支 job `conclusion=cancelled ∧ steps==[] ∧ runner_name=="" ∧ 14.5 分 ≤ completed_at−created_at ≤ 16 分`，且同 ref 在 `[created_at, completed_at]` 間沒有更新的 run（排除 concurrency 自取消）。
- 命中 ⇒ `gh run rerun <id> --failed`（同 sha 至多 `CI_QUEUE_RERUN_MAX=2` 次）並繼續等；末行 `CI_WAIT_VERDICT=pass rerun=queue_timeout×<n>`；超過 ⇒ `CI_WAIT_VERDICT=fail reason=queue_timeout_exhausted`（rc 1，既有語意）。
- 每次命中落痕跡 `ci_queue_timeout {run, attempt, minutes}`；退役條件＝連續 7 天零命中（只記錄，不自動移除程式；退役由下一個觸及者依痕跡決定）。
- 不改 `runs-on`。換付費 runner 屬 `[COST]`（§2）：只有 `queue_timeout_exhausted` 連續 7 天每天出現時，主控才以 `[COST]` 題（`服務：GitHub Actions；預估：<n> 美元`）問人；現況未觸發。

---

## 7. AskUserQuestion 類別閘（N1／N7；PRD R-4.5.12-3～5 及其【v2.1.29 勘誤】，REQ-AP-ASK-01）

- 接線：`.claude/settings.json` PreToolUse 新增 matcher `AskUserQuestion` → 既有 `sessionctl_guard.py`（新增一個分支，不新增 hook 檔；判準住新檔 `tools/lib/sessionctl/askgate.py`）。
- **可問人的定義（掌舵者 2026-11-25 原話）**：「『真正需要您決定的類別』==> 目前定義: 1. 會造成系統(本機, 專案, Gihub等)整個毀壞, 無法復原的情形 2. 目前Claude都使用訂閱制(須確認), 若非訂閱制, 有使用費用超過50美元」。掌舵者原話只有兩類＝`[IRREVERSIBLE]`、`[COST]`；第三類 `[K1]` **不在原話中**，來源是根 CLAUDE.md〈收尾常態規則〉的既有例外（「唯一例外＝只能由掌舵者親打的 K=1 決定」）——K=1 決定本就只能由人做，保留它不擴大可問範圍（F-24）。AP-A 報告的 `[BIZ]`／`[SECRET]`／`[VISUAL]`／`[HARNESS]` 全部退役。

| 標籤 | 定義 | 必填欄位（缺即阻斷） |
|---|---|---|
| `[IRREVERSIBLE]` | 會造成**任何系統**（本機、專案、GitHub、雲端服務、資料庫、帳號、第三方平台等，不限原話列舉的三者）整體毀壞且無法復原的動作 | `系統：<名稱>`＋`不可復原原因：<一句>`。「回不去」由程式能救的不算不可復原（例如有 `*-wip-preserved` 標籤、git 歷史、備份者）——這一點靠主控判斷與事後普查，不靠詞表 |
| `[COST]` | 該動作會產生**非訂閱制**的費用，且預估超過 50 美元 | `服務：<名稱>`＋`預估：<n> 美元`，且 n > 50。**只有 `服務` 是 Claude／Anthropic 時**才讀計費姿態：`sessionctl quota --json` 的 `billing` 欄（QV 設計 §3.3；與 `quota_messages.posture_line()` 同一推導函式 `quota_ruling.billing_from_posture()`）。`billing=subscription_only`（此帳號沒有 usage credits ⇒ 訂閱窗即硬牆、不會逐次計費）⇒ 阻斷；`credits_fallback`／`api_key`／`unknown` ⇒ 視為非訂閱制（判不出往保守＝讓人知道）。服務不是 Claude／Anthropic（GitHub 付費 runner、雲端服務…）⇒ 不讀 `billing`，只看 n > 50 |
| `[K1]` | SelfImproving K=1 決定（DEC 只認掌舵者真人發言） | 問題本文寫明「須掌舵者親打」；選項不得含可被直接當成決定的「核准」字樣（AskUserQuestion 只提示、不是決定載體） |

- 判準（`askgate.verdict(tool_input, env, billing) -> (allow: bool, reason)`；由上而下短路）：
  1. 無人窗口（`AUTOSDD_UNATTENDED`）⇒ 一律阻斷（沒有人能回答；`[IRREVERSIBLE]` 動作在無人窗口本來就不准做，改寫進 handback）。
  2. 任一問題不以三標籤之一開頭 ⇒ 阻斷。
  3. 標籤的必填欄位（上表右欄）缺或不合格（`[COST]` n ≤ 50、`[COST]` 服務為 Claude 且 `subscription_only`、`[K1]` 缺字樣或選項含「核准」）⇒ 阻斷。
  4. **可代決句型**命中 ⇒ 阻斷，不論標籤（v1.2 依 QA 複審 N-04 收窄為「動作詞是被問的對象」）：把問題本文以「？」「?」「。」「；」切成問句；某一問句中，疑問詞（要不要／是否／需不需要／該不該／可不可以）**之後 12 個字元內**出現可代決動作詞 ⇒ 命中。動作詞一律是**複合動作詞**（被問的就是這個動作）：續跑、繼續跑、繼續等、繼續派、park、換 session、交接、關閉舊視窗、逃生口、`_OFF`、重跑 CI、目視、等重置。**泛用的單詞「繼續」刻意不收**（v1.1 收了它，必填齊全的「`[IRREVERSIBLE]` 系統：GitHub；不可復原原因：`push --force` 覆寫遠端歷史。是否繼續？」會被擋——「是否繼續」問的是那個不可復原動作本身，正是掌舵者要能問的題）；疑問詞與動作詞隔得遠（另一子句才出現動作詞）也不命中。動作詞表住 `askgate.py` 單一常數 `SELF_DECIDE_VERBS`，可擴不可縮（測試鎖）；單詞「繼續」不得加入（反向鎖）。**刻意不收名詞詞表**（v1.0 的「推送」「合入」「rebase」「cherry-pick」「額度」「裁決」）：那些詞會出現在真正的不可復原題（「`push --force` 覆寫遠端歷史」）與 Claude 計費題（「啟用超額使用」），v1.0 讓掌舵者第 1、2 類實際上問不出口（F-11）。
  5. 其餘放行，落痕跡 `ask_allowed {category, sid, at, system|service, usd}`（再開症狀與 E2E 普查用）。
- 阻斷訊息（rc 2；v1.2 依阻斷原因分三種，N-04——**任何一種都不得叫模型自行決定不可復原或花錢的動作**）：
  - 判準 2（無標籤或舊標籤）：「這一題沒有可問人的類別標籤。若它屬於下列三類，請補上標籤與必填欄位後重問；不屬於就依最適方案代決，把 WHY 寫進帳本或 commit 訊息後繼續。三類：任何系統整體毀壞且不可復原（[IRREVERSIBLE]，附系統與原因）、非訂閱制且預估超過 50 美元（[COST]，附服務與金額）、K=1 決定（[K1]，須掌舵者親打）。在得到回答之前，不得執行該不可復原或花錢的動作。」
  - 判準 3（必填欄位缺或不合格）：「[<標籤>] 缺 <欄位> 或不合格（<原因>）：請補齊後重問。在得到回答之前，不得執行該動作。」（`[COST]` 因 `subscription_only` 被擋者另附「此帳號沒有 usage credits，不會逐次計費，不需要問」）
  - 判準 4（標籤題含可代決子問題）：「這一題帶 [<標籤>]，但其中『<命中的問句>』是可代決的子問題：請改寫問句、去掉可代決的子問題（子問題依最適方案代決並把 WHY 寫進帳本），只留下真正屬於 [<標籤>] 的那一問。在得到回答之前，不得執行該 [<標籤>] 動作。」——**不得**出現「由你代決」「依最適方案決定」套在整題上。
  - 判準 1（無人窗口）：沿用既有：把題目與必填欄位寫進 handback 後結束，不得在無人窗口執行該動作。
- 同步改 `.claude/hooks/check_pending_handoff.py` 推回文案：先叫主控代決；只有上述三類才指路 AskUserQuestion（G9 的另一半）。另修兩個假推回（§13 G9 列）：描述分類規則或複述掌舵者定義的句子（「真正需要您決定的類別」「以後要請您決定的只有這兩類」）不是交棒——判準改為：句中「需要您／請您」緊接類別定義語（「類別」「只有」「定義」）或位於引號內 ⇒ 不算；同時 `check_claim_provenance.py` 對敘述過去事件的「被擋／擋下」（前文帶時間或事件座標：「先前」「當時」「L<n>」「<時刻>」）不當本場宣稱。兩者皆以真實語料重放驗證（TCS E2E-AP-ASK-02）。
- 不用 `updatedInput.answers` 代答（§2 的 WHY）。
- 劃界：模型可以把可代決的問題偽標成 `[IRREVERSIBLE]`，並寫一個看似合理的系統名與原因、避開可代決句型；結構上擋不下。補救＝`ask_allowed` 痕跡事後普查（TCS 再開症狀：放行者逐筆核對是否真屬三類），以及 Stop 端既有 K=1 語意；這是照實劃界，不再加碼守衛（R197「量、不挖」）。

---

## 8. 舊視窗事件驅動關閉（G8／G9；PRD R-4.5.12-1／2，REQ-AP-OW-01）

- 觸發：舊視窗自己的 Stop（`sessionctl_guard.py` Stop 分支）在「已交棒 ∧ 新 session 已 ack」時呼叫 `oldwin.on_old_stop(sid)`：寫 `oldwin_idle_hint` 事件，並以既有 `oldwin_sched.schedule_retry` 排一次 60 秒後的關閉檢查（`oldwin.eligible` 條件不變）。舊視窗真正閒下來的時刻就是它 Stop 的時刻。
- 重試：`oldwin.MAX_RETRIES = 3` 退役，改指數退避 `retry_at = last + min(60·2^k, 12h)`，總時長上限 12 小時（`AUTOSDD_OLDWIN_MAX_HOURS`，出廠 12）；到上限只記 `oldwin_retry_exhausted`（取代 `oldwin_retry_abandoned`）並在 `sessionctl status` 與 SessionStart 簡報顯示一行「舊視窗待關（原因 not_idle，第 n 次）」——**不交人**。
- 文案：刪除 `oldwin.py` 的 `_manual_text()`、`pending_manual_close()`、`reminder_lines()` 中「請手動關閉」字樣與 `sessionctl_guard.py` 對應文案，改為陳述事實（交棒後舊視窗收到真人提示的轉送／告知已由 `forward.py` 處理）。
- `status=shell` 長時間不變仍不強殺（R-4.5.11-3）。
- **字樣鎖射程**（F-15；R-4.5.12-1 涵蓋本 PRD 全部機制的訊息）：掃 `tools/lib/quota_*.py`、`tools/lib/sessionctl/**`、`tools/session_resume_planner.py`、`tools/lib/session_brief.py`、`tools/lib/sentinel_lifecycle*.py`、`tools/lib/resume_route.py`、`tools/lib/relay_machine.py`、`.claude/hooks/{context_budget_guard,sessionctl_guard,check_pending_handoff,check_claim_provenance}.py` 的全部字串常值；禁字＝「請手動」「請您」「手動跑」「請人」。例外清單住測試檔，逐筆列「檔:函式＋WHY」；SD-1 普查已知站點與處置：

| 站點 | 現況 | 處置 |
|---|---|---|
| `sessionctl/oldwin.py` `_manual_text()`、`pending_manual_close()`、`reminder_lines()` | 「請手動關閉」 | 改寫（本節） |
| `.claude/hooks/sessionctl_guard.py` 對應文案 | 同上 | 改寫 |
| `.claude/hooks/context_budget_guard.py:916` | 「本次自動產生失敗，請手動跑」 | 改寫：產生失敗即記痕跡，下一次工具呼叫由程式重試（R-4.5.12-1「由程式持續重試或改道」）；訊息改陳述「已排重試」 |
| `tools/lib/quota_messages.py:496` | 「收斂後請手動跑 planner」 | 改寫：指路的動作屬主控可代決 ⇒ 改為「主控收斂後執行 …」或由程式在收斂點自動執行（WP-HOOK 依該分支現查決定，二擇一寫進交卷） |
| `sessionctl/qw_prompt.py:77` | 「請手動」 | WP-HOOK 審視：屬 harness 信任對話框等程式做不到的人機介面 ⇒ 入例外清單附 WHY；否則改寫 |
| 月度支出上限（spend 軸撞限）提示 | 要人提高上限 | 例外：屬 `[COST]` 型人工動作（QV 設計 §3.2 第 1 列） |

---

## 9. 測試對真痕跡目錄的圍籬（N3，REQ-AP-FN-01）

- 前置普查（WP-FENCE 第一動作）：`git grep -n "\.autosdd" -- tools .claude ':!tools/tests'`，確認所有痕跡寫入者都經 `endurance_env.trace_dir()`；繞過者先收斂到該入口（同一 commit）。
- 圍籬判準住新扁平檔 `tools/lib/suite_fence.py`（`suite_` 前綴現 1 支 `suite_shard.py`，加入後 2 支 <3，不觸散落鎖）：`arm(env) -> Fence`（把 `AUTOSDD_TRACE_DIR` 設到 `suite_tmp_*/traces`、記下真 `~/.autosdd/traces` 每個檔的 (size, mtime)）、`leaks(fence) -> list[str]`（結束時比對，圍籬期間新增的列只要帶 `%TEMP%`／`$TMPDIR` 路徑、`sc-*` 前綴或夾具 sid ⇒ 判洩漏）。
- runner 只加呼叫（`fence = suite_fence.arm(...)`；結束 `rc = rc or report(suite_fence.leaks(fence))`，約 +6 行）；洩漏 ⇒ rc≠0、印檔名與首筆列。
- 平行 worker（`parallel_shard`）繼承同一環境變數；分片（`AUTOSDD_TEST_SHARD`）每片各自圍籬。
- 前置依賴：D649 修復棒合入後才派（與 HYG1 動同一 runner）。

---

## 10. 模組落點（依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）

| 內容 | 落點 | SSOT §2 對應 | 備註 |
|---|---|---|---|
| 合入／推送判準 | 新套件 `tools/lib/autopilot/`（`__init__.py`、`merge.py`、`carrier.py`、`pushgate.py`、`ledgersplit.py`、`locks.py`、`outcome.py`） | 函式庫列（兩支以上檔 ⇒ 第一天成套件） | 不 import 其他套件；判決以子行程呼叫 `tools/sessionctl.py quota --json` 取得（走資料）。`outcome.py`＝`MERGE_VERDICT`／`PUSH_VERDICT` 末行組字（v1.0 名 `verdict.py`，改名以免與 `quota_ruling`、`qw_verdict` 混淆，F-26）；`carrier.py`＝§3.2 步 4.5 的 clone、連結與自證 |
| 指令入口 | 新 `tools/autopilot.py`（`merge`／`push`；薄殼） | 指令入口列 | 指令字面寫進本檔後即對外契約 |
| 推送範圍棘輪 | 既有 `tools/lib/ledger_closing_guards.py` | 存量扁平（缺陷帳本家族） | — |
| 治理閘逃生口述詞 | 新扁平 `tools/lib/human_escape.py`（`honored()`、`HUMAN_ONLY_ESCAPES`） | 函式庫：單檔共用工具（`human` 前綴 1 支） | 守衛面（CLOSE 加入根 CLAUDE.md〈守衛面准入〉清單） |
| pre-push 逐 ref 呼叫棘輪 | 既有 `tools/git-hooks/pre-push` | — | 逐行迴圈內加呼叫 |
| CI 排隊逾時 | 既有 `tools/lib/ciwait/core.py` | 既有套件 | — |
| 詢問類別閘 | 新 `tools/lib/sessionctl/askgate.py`；接線既有 `.claude/hooks/sessionctl_guard.py` | 既有套件（守衛面） | — |
| 舊視窗 | 既有 `tools/lib/sessionctl/oldwin.py`、`oldwin_sched.py` | 既有套件（守衛面） | — |
| worktree 起點 | 既有 `.claude/settings.json` | 守衛面 | — |
| 痕跡圍籬 | 新扁平 `tools/lib/suite_fence.py`；呼叫端既有 `tools/run_root_unittests.py` | 函式庫：單檔共用工具 | — |
| 測試 | 新 `tools/tests/test_autopilot_merge.py`、`tools/tests/test_autopilot_push.py`；詢問閘併入既有 `tools/tests/test_sessionctl_hooks.py`；舊視窗併入既有 `tools/tests/test_sessionctl_oldwin.py`；CI 分類併入既有 `tools/tests/test_ci_wait.py`；圍籬併入既有 runner 測試檔（WP-FENCE 現查）；`human_escape` 併入 `tools/tests/test_check_defect_log_crossref.py` | 測試列 | 新檔兩支；CLOSE 一次重釘 |
| 真機 E2E | `tools/lib/realverify/cases/autopilot.py`（新家族檔） | realverify 既有落點 | — |
| 痕跡 | `~/.autosdd/autopilot/`（merge.jsonl、conflict-*、fix-*.md）、`~/.autosdd/traces/`（ask_allowed、ci_queue_timeout、oldwin 事件） | repo 外 | 經 `endurance_env.trace_dir()` 或同層新函式 |
| CI 接線 | compat-ci 兩支 workflow `paths` 加 `tools/lib/autopilot/**`、`tools/autopilot.py`、`tools/lib/human_escape.py`、`tools/lib/suite_fence.py` | CI 接線列 | CLOSE 同 commit；`test_ci_paths_cover_root_consumers.py` 鎖 |
| 不可進化面 | `params.json` `non_evolvable_globs` 加 `tools/lib/autopilot/**`、`tools/autopilot.py`、`tools/lib/human_escape.py` | 不可進化面列（合入／推送與逃生口屬守衛類） | CLOSE |
| SSOT §3 登記 | 規格階段以純文字說明列預告；實作 commit 後 CLOSE 改反引號登記 | §3 | 落點鎖要求反引號路徑存在 |

---

## 11. LOC 處置（SD-0 當回合實量；實作前現查 `python AutoClaude/tools/check_loc_budget.py --json`）

| 檔 | 現值／上限 | 估計新增 | 處置 |
|---|---|---|---|
| `tools/lib/autopilot/*`（新） | — ／400 每檔 | merge 約 220、carrier 約 120、pushgate 約 200、ledgersplit 約 120 | 依職責分檔，任一檔逼近 360 即再拆 |
| `tools/autopilot.py`（新，cli 750） | — | 約 80 | — |
| `tools/lib/ledger_closing_guards.py` | 175／400 | +35 | 無需抽出 |
| `tools/lib/human_escape.py`（新） | — ／400 | 約 40 | — |
| `tools/lib/ciwait/core.py` | 127／400 | +60 | 無需抽出 |
| `tools/lib/sessionctl/oldwin.py` | 354／400 | 退避 +10、刪文案 −15 | 若淨增 >40：`bg_shells()`（L149～L200）搬 `oldwin_sched.py`（164／400）或新檔 `oldwin_bg.py` |
| `tools/lib/sessionctl/oldwin_sched.py` | 164／400 | +20 | 無需抽出 |
| `tools/lib/sessionctl/askgate.py`（新） | — | 約 90 | — |
| `.claude/hooks/sessionctl_guard.py` | 90／750 | +8 | 無需抽出 |
| `.claude/hooks/check_pending_handoff.py` | 226／750 | ±5 | 無需抽出 |
| `tools/run_root_unittests.py`（**SPECIAL_FILES**） | raw 765／門檻 765（QA-S 當回合實量，餘裕 0） | 呼叫端 +6 | **先抽、再加**（F-12）：`min_tests_note_stale_tokens()`＋`report_min_tests_note_stale_tokens()`（現 L645～L700，約 56 行）搬到其自然家既有扁平檔 `tools/lib/min_tests_margin.py`（同屬 MIN_TESTS 棘輪族；實作前現查該檔分級餘裕），runner 留 re-export 一行（既有測試的 import 端不動）；圍籬判準全住新 `tools/lib/suite_fence.py`。淨效果約 −49。SPECIAL 門檻由 CLOSE 下修為新實值（棘輪雙邊咬人：門檻明顯高於現值即紅） |
| `tools/lib/suite_fence.py`（新） | — ／400 | 約 90 | — |
| `tools/lib/min_tests_margin.py` | 現查 | +56 | 若超出分級：改搬 `tools/lib/onboarding_snapshot_note.py`（同為 ONBOARDING 基線註記族），兩者擇一寫進 WP-FENCE 交卷 |

---

## 12. 工作包、持有面與順序（鐵律七）

| WP | 內容（本檔節） | 持有面 | 守衛面 | 與誰串行 |
|---|---|---|---|---|
| WP-QV | QV 設計全部（含 SI 消費端） | quota 族＋sessionctl watch／park／parkearly／parkprobe／switchplan／switchfacts／keepwarm＋`selfimproving/{sched,patrol,fourq,writeverbs,evspec}.py`（v1.2 統一清單，N-08） | 是 | 先於 WP-AC |
| WP-AC | QV 設計 §7 | 同上 | 是 | WP-QV 收工親驗後 |
| WP-MERGE | §3、§4、§5 | `tools/lib/autopilot/**`、`tools/autopilot.py`、`ledger_closing_guards.py`、`human_escape.py`、`tools/git-hooks/pre-push`；v1.3（R-02）加 `.env` 路徑覆寫的讀者與拒寫者：`tools/lib/quota_env_layers.py`、`AutoClaude/autoclaude/utils/config.py`（`_ENV_FILES`）、`tools/git-hooks/post-merge`（quota 族中只有 `quota_env_layers.py` 歸本包；QVD 普查表無此檔，WP-QV／WP-AC 不動它，持有面仍不交集；兩側讀者同序由既有 `tools/tests/test_quota_env_layers.py` 雙邊對跑守，覆寫分支同 commit 加雙邊案例；動前現查 LOC） | 是（`human_escape.py`） | 可與 WP-AC、WP-CI 並行（持有面不交集） |
| WP-CI | §6 | `tools/lib/ciwait/core.py`、`tools/ci_wait.py`、`tools/tests/test_ci_wait.py` | 否 | 可並行 |
| WP-FENCE | §9、§11 runner 列 | `tools/run_root_unittests.py`、`suite_fence.py`、`min_tests_margin.py`（＋普查後的繞過站點） | 否 | D649 合入後；與 WP-MERGE 不交集 |
| WP-HOOK | §3.1 settings、§7、§8、QV 設計的兩個 hook 改動 | `.claude/hooks/**`、`.claude/settings.json`、`sessionctl/oldwin*.py`、`sessionctl/askgate.py` | 是 | 單一 staged diff 交主控親套；WP-QV 之後（要判決字面） |
| CLOSE | 重釘（c1c2、`_TREE_FILE_FLOORS`、`SPECIAL_FILES` 下修兩檔、skip、E501、MIN_TESTS／ONBOARDING）、CI paths、`non_evolvable_globs`、SSOT §3 反引號登記；**根 CLAUDE.md**（守衛面清單加 `tools/lib/model_window_table.py`、`tools/lib/quota_ruling.py`、`tools/lib/human_escape.py`；現查表加 `sessionctl quota`、`autopilot merge／push`；〈換 session 的 SOP〉`park --why`→`--next-est`；〈收尾常態規則〉「真需要掌舵者者，在同一回合用 AskUserQuestion」改為「只有 `[IRREVERSIBLE]`／`[COST]`／`[K1]` 三類可用 AskUserQuestion，其餘代決」；機械守衛總表 `sessionctl_guard.py` 列補 PreToolUse／AskUserQuestion、`check_pending_handoff.py` 列文案同步）；**記憶檔**（`no-prose-handoff-ask-with-options.md`、`quota-stop-must-park.md`、`ci-wait-no-handwritten-poll.md` 加 `queue_timeout` 一句）；QuotaWall DES／TCS-QuotaWall／TCS-SessionPark／ADR-XPLAT-004 註記（QV 設計 §6）；**N8（Stop 額度推回噪音）與 `AUTOSDD_QUOTA_BURNDOWN_OFF` 入證據檔〈理論洞清單〉**；**既有「畫面目視」類 OI 的轉載具處置**（見 §16）；帳本列；AP-A 報告轉存證據檔；交主控以 OI 登記「快照閘實作時經 `human_escape.honored()`」（§5） | 全部鎖檔 | — | 以上全部之後 |
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
| 治理閘逃生口族 | `tools/lib/human_escape.py`、`tools/lib/ledger_closing_guards.py` | 逐字稿 L46 第 295 列（CLOSE1 子代理自設 OFF 提交通過）；L2422 |
| 非守衛面（不需證據，仍附） | `ciwait/core.py`、`run_root_unittests.py`、`suite_fence.py`、`tools/lib/autopilot/**` | G2、N3、G4／G10 各列 |

---

## 14. 修復不留後遺症三問

1. **另一台機器會不會回來？** `worktree.baseRef` 寫在 repo 的 `.claude/settings.json`，隨 clone 走；`CLAUDECODE` 由 harness 注入、跨平台；ci_wait 判準只吃 GitHub API 欄位；merge 的 clone 用平台暫存目錄（`tempfile.gettempdir()`），它與 repo 是否同卷因機器而異（主控機即不同卷）——v1.3 起 clone 不帶 `--local`、`.env` 以路徑覆寫唯讀讀取，同卷與跨卷走同一條路，只差步驟 0 是否加計物件庫（R-02）；`.venv` 連結在 Windows 用 junction、POSIX 用 symlink，刪除只刪連結本身；editable `.pth` 寫死主樹的跨機器假綠由步驟 4.5 每次自證擋下（fail-closed），不靠記得。
2. **有沒有文件／座標不一致？** CLOSE 同 commit 收齊：CI paths、`non_evolvable_globs`、SSOT §3、根 CLAUDE.md（鐵律七檢查表第 4 條「收尾單人窗口」加註 `autopilot merge` 為其機械形態；現查表；換 session SOP；收尾常態規則）、三份記憶檔、被取代條文（§16、QV 設計 §6）、ADR-XPLAT-006 由 ADR-XPLAT-018 部分取代的註記（只增不改，加在 ADR-006 §7 表後）。
3. **有沒有「之後再看」？** 照實列：N8 與 `QUOTA_BURNDOWN_OFF` 入〈理論洞清單〉（P4，無暴露證據）；快照閘尚未實作 ⇒ 交主控以 OI 登記（不得留散文）；macOS runner 換付費屬 `[COST]`、現況未觸發，觸發條件已寫明（§6）。

---

## 15. 與 AP-A 報告的差異（SD-0 決定，v1.1 部分改寫）

| 項 | AP-A | SD-0 | SD-1 | WHY |
|---|---|---|---|---|
| G3 起點 | WorktreeCreate hook（待查）或任務書首動作 rebase | `worktree.baseRef: "head"`＋merge rebase 第二道 | 同；加殘留普查鎖、回應 ADR-006 爭點 4 | 官方設定鍵已存在；ADR-006 三項事實逐一處置 |
| 合入驗證載具 | 未定 | `%TEMP%` 下 linked worktree | 獨立 clone＋`.venv` 連結＋`PYTHONPATH`＋每次自證 | ADR-XPLAT-006 §7 已拒 linked worktree 當驗證載具；editable `.pth` 會讓全套靜默測到主樹（F-04） |
| N2 | commit-msg 強制 trailer | `CLAUDECODE`／無人窗口下 NET_RATCHET_OFF 無效 | 擴為族＋單一述詞 `human_escape.honored()`；納入 SNAPSHOT_GATE_OFF | 主控代決 ②；不讓兩個家各判各的 |
| 推送範圍比較對象 | — | 未定義 | 逐 ref `<local_sha>` 對 `<remote_sha>` | 比工作樹會擋掉前綴推送（F-05） |
| 帳本拆分 | 「autopilot merge 自動拆分」 | 帳本檔變更整批剝離成尾端單一提交 | 同 | 規則簡單、可證 |
| 詢問閘落點 | 新 hook 或併入 sessionctl_guard | 併入 `sessionctl_guard.py`＋判準 `askgate.py` | 同 | 不新增 hook 檔 |
| 詢問閘類別 | 五類 | 三類 | 三類；`[K1]` 註明來源；`[COST]` 加 `服務：` | 掌舵者原話兩類＋既有 K=1 例外（F-24）；非 Claude 服務不讀 Claude 計費姿態（F-11） |
| 詢問閘判準 | 只看標籤 | 標籤＋必填欄＋名詞詞表優先 | 標籤＋必填欄＋「要不要＋可代決動作」句型 | 名詞詞表擋掉真正的第 1、2 類題（F-11） |
| 付費 runner | — | 「K=1 類，未代決」 | `[COST]`，現況未觸發 | 三類定義下 K1 只指 SelfImproving DEC（F-11 ③） |
| 合入／推送末行組字檔名 | — | `autopilot/verdict.py` | `autopilot/outcome.py` | 與 `quota_ruling`／`qw_verdict` 混淆（F-26） |
| runner LOC | — | 「現查」 | 具體抽出清單 | SPECIAL 餘裕 0（F-12） |

---

## 16. 被取代條文與既有承諾（AskUserQuestion 與交人面；F-09）

| 被取代者 | 座標 | 新條文 | 處置（CLOSE 同 commit） |
|---|---|---|---|
| 根 CLAUDE.md〈收尾常態規則〉「真需要掌舵者者，在同一回合用 AskUserQuestion 給互動選項」 | 根 `CLAUDE.md` | PRD R-4.5.12-3、本檔 §7 | 改寫為「只有 `[IRREVERSIBLE]`／`[COST]`／`[K1]` 三類可用 AskUserQuestion（掌舵者 2026-11-25 定義），其餘依最適方案代決並把 WHY 寫進帳本或 commit」；機械守衛總表 `check_pending_handoff.py` 列同步 |
| `check_pending_handoff.py` 推回文案（指路 AskUserQuestion） | `.claude/hooks/check_pending_handoff.py` | §7 末段 | WP-HOOK 改；`tools/tests/test_check_pending_handoff.py` 對應斷言同 commit 改 |
| 記憶檔 `no-prose-handoff-ask-with-options.md`（「真需掌舵者就同回合 AskUserQuestion」） | 使用者記憶目錄 | 同上 | 主控親改（記憶不在 repo），交卷列出 |
| 既有「待掌舵者目視」類 OI（〔OI-20261120-010〕、〔OI-20261120-015〕等 V1～V8 真機目視） | `docs/06_quality/` OI 帳 | 類別閘下「目視」屬可代決（§7 動作詞表含「目視」），不得再以 AskUserQuestion 問人 | 轉載具：改由 realverify 真行程＋痕跡或替身驗到「畫面前一刻」（同 TCS 備援欄的劃界）；畫面層本身無程式載具者，OI 改記「劃界：harness UI 不可程式目視」並以被動觀測痕跡結案條件取代人工目視。逐筆處置由 CLOSE 以 `openitems` 動詞改寫（主控執行），本設計不自行改帳 |
| ADR-XPLAT-006 §7「直接開 harness 內建隔離」「linked worktree 當驗證者載具」兩列、爭點 4 裁決 | `docs/04_planning/ADR/ADR-XPLAT-006-parallel-agent-snapshot-fanout.md` L223～L235、L611、L614 | ADR-XPLAT-018 | ADR-006 不改原文；CLOSE 在其 §7 表後加一行「部分取代：見 ADR-XPLAT-018（2026-11-25）」 |

---

## 17. v1.0 → v1.1 處置索引（QA-S 報告發現編號）

| 發現 | 本檔落點 |
|---|---|
| F-04 合入載具與 ADR-XPLAT-006 衝突 | §3.1、§3.2 步 0／1／4.5／5／6、ADR-XPLAT-018 |
| F-05 推送範圍比較對象 | §3.3、§4.1、§4.3 |
| F-09 被取代者（APD 面） | §12 CLOSE、§16 |
| F-11 類別閘落差 | §2 GitHub 列、§6 末、§7 |
| F-12 runner LOC | §9、§11 |
| F-15 字樣鎖射程 | §8 |
| F-21 `*_OFF` 普查 | §5 普查表 |
| F-23 print 模式 AskUserQuestion | §2 新列 |
| F-24 `[K1]` 來源 | §7 |
| F-26 N8 與 `verdict.py` 改名 | §10、§12 |
| 主控代決 ②（SNAPSHOT_GATE_OFF） | §5、§10、§12 |

---

## 18. v1.1 → v1.2 處置索引（QA 複審 `qa_spec2_report.md` 發現編號）

| 發現 | 本檔落點 |
|---|---|
| N-03 獨立 clone 缺主樹機器本地狀態 | §3.2 步 4.5 ④、新步 4.7 基線、步 5 判定；ADR-XPLAT-018 D5 |
| N-08 SI 檔案清單不一致 | §12 WP-QV 持有面 |
| N-04 詢問閘擋掉必填齊全的「是否繼續？」、阻斷訊息叫模型代決 | §7 判準 4（疑問詞之後 12 字元內的複合動作詞；單詞「繼續」不收）、阻斷訊息三分；PRD R-4.5.12-3【v2.1.29 勘誤（續）】 |

---

## 19. v1.2 → v1.3 處置索引（QA 第三輪 `qa_spec3_report.md` 發現編號；SD-3）

| 發現 | 本檔落點 |
|---|---|
| R-02 `.env` 同卷硬連結在主控機（暫存 `C:`、repo `D:`）必然失敗，且硬連結使 clone 內寫入改到主樹機密檔 | §3.2 步 4.5 ④ 改為路徑覆寫 `AUTOSDD_LOCAL_ENV_FILE`（`.env` 不進 clone、唯讀讀主樹那一份；採 QA 建議 (b)，主控代決）；步 4.5 失敗分支；§12 WP-MERGE 持有面加三個讀者／拒寫者；§14 三問第 1 問；ADR-XPLAT-018 D5〈`.env` 路徑覆寫〉 |
| R-02 附帶（SD-3 實測新增）：`git clone --local` 跨卷 rc 128，clone 本身建不起來 | §3.2 步 1 去 `--local`、步 0 跨卷加計物件庫；ADR-XPLAT-018 D1 |
| R-05 判準 4 動作詞「舊視窗」在 v1.2 收窄為「關閉舊視窗」未記錄 | 本列。**變化**：v1.1 的動作詞表收「舊視窗」，v1.2 改為複合詞「關閉舊視窗」。**WHY**：v1.2 的判準 4 要求「動作詞是被問的對象」（N-04），「舊視窗」本身是名詞——收它會讓「要不要先看舊視窗的輸出？」這類只是提到舊視窗的問題被擋，違反 R-4.5.12-3 勘誤③「不以名詞阻斷」。可代決的那個動作是「關閉」（§8 已改為事件驅動、不交人），所以動作詞取「關閉舊視窗」。**後果**：「要不要重開舊視窗？」不再命中——重開舊視窗不是本機制的任何動作（交棒後舊視窗收到提示由 `forward.py` 轉送或告知），它是一般問題，交由判準 1～3 的類別檢查處理（無合法類別標籤即擋）。PRD 勘誤③ 括號內的「舊視窗」是動作類別的例示（句末「等」），具體字面以本節動作詞表為準，PRD 不改字 |
