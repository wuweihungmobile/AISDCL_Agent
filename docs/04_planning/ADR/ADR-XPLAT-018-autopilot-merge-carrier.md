# ADR-XPLAT-018：自動合入的驗證載具——獨立 clone＋`.venv` 連結＋每次自證；寫入者可用 harness 內建隔離（`baseRef: head`）

- **狀態**：**提案 v1.1**（SD-1 起草，SD-2 依 QA 複審 N-03 加 D5，2026-11-25；隨 `docs/02_architecture/Autopilot_Pipeline_Design.md` v1.1 一併送 QA 複審，通過後由主控依〈凍結常態規則〉凍結為 Accepted）。本檔是設計文件，不含生產碼。
- **平台**：平台中立（Windows 11＋PowerShell 為主控機；POSIX 差異逐項寫在 §2）。
- **關聯**：`docs/02_architecture/Autopilot_Pipeline_Design.md` §3（合入管線）、`docs/03_testing/contracts/TCS-Autopilot-20261125.md`（REQ-AP-MG-01～03、REQ-AP-WT-01）、PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.28 列（掌舵者 2026-11-25 立案原文）。
- **修訂對象**：**部分取代** [ADR-XPLAT-006](ADR-XPLAT-006-parallel-agent-snapshot-fanout.md) §7「已拒絕的方案」中兩列——「直接開 harness 內建隔離」與「linked worktree 當驗證者載具」——以及爭點 4 的裁決「不可直接開啟」。ADR-006 的其他決策（快照式唯讀驗證樹、Stage 2 放棄、Stage 3 擱置、爭點 5 的 `.pth` 事實）**全部維持**。ADR-006 原文不改；CLOSE 窗口在其 §7 表後加一行指向本檔（只增不改）。
- **立案證據**：QA-S 審查 F-04（sid `406454ea-91fc-4481-9c11-b28ed7d9e95f` scratchpad `qa_spec_report.md`）：Autopilot 設計 v1.0 §3.2 步 5 在 `%TEMP%` 的 linked worktree 跑 pre-push 全套；SD-0 與 SD-1 自己的 linked worktree 皆無 `.venv`（提交時 dispatcher 印「找不到 repo 根層 .venv 直譯器」、三層掃描未執行），即 ADR-006 §2.3 記載的「忘了帶 `PYTHONPATH` 就靜默測到主樹」與爭點 5「editable `.pth` 寫死主樹」在本案的再現。

---

## 1. 脈絡

掌舵者 2026-11-25 要求「真正的自動駕駛開發」。合入（把代理成果併回 main）原本由主控手工 cherry-pick，推送才發現紅（G4／G10）。Autopilot 設計要把它做成一支冪等指令，而那支指令必須**在合入結果上**跑 pre-push 同款全套——這裡的載具選擇就是 ADR-006 已經裁過的題目。ADR-006 的裁決對象是「並行 agent 的唯讀驗證樹」，本案多了兩個條件：(1) 驗證標的是**尚未存在於任何工作樹**的合入結果（rebase 之後才有）；(2) 寫入者（代理）已在使用 harness 內建隔離（本 ADR 撰寫時，SD-1 本身就在 `isolation: "worktree"` 內工作）。

## 2. 決定

### D1　驗證載具＝repo 外獨立 clone（不是 linked worktree）

`git clone --local --no-checkout <主樹> <tempfile.gettempdir()/autopilot-<ts>>`，在 clone 內建拋棄式分支並套上代理提交、checkout。

| ADR-006 §7 拒絕 linked worktree 的理由 | 獨立 clone 下的狀態 |
|---|---|
| 共用 `refs/stash` | **結構上不共用**：clone 有自己的 `.git`（`git rev-parse --git-common-dir` 指向 clone 自己）；`.git/config`、`.git/info/exclude` 同樣不共用（ADR-006 §8 第 10 點的附帶問題一併消失） |
| 無 `.venv`（忘了帶 `PYTHONPATH` 是靜默失效） | 由 D2 組裝；失效改為**大聲**（D3 自證 fail-closed） |
| 真實磁碟貴一個數量級 | 物件以 `--local` 硬連結共享（同一卷）；工作樹在 Windows 全額佔碟（無 clonefile），合入步驟 0 先檢查可用空間 ≥ 2×已追蹤檔總大小，不足 ⇒ `no_space`（ADR-006 §2.3「每棵驗證樹全額佔碟、開樹前檢查餘裕」逐字沿用） |

為什麼不用 ADR-006 的整樹拷貝（`cp -c -R`／`robocopy`）：合入結果要先 rebase 才存在，整樹拷貝會把主樹的未提交狀態與 `.git` 一起帶過去，rebase 必須在拷貝內做、等於在一份含主樹 stash 與 config 的 `.git` 上寫——那正是 ADR-006 要避免的共用面；且 Windows 無 clonefile，整樹拷貝連 `.venv` 一起全額複製（數 GB）。獨立 clone 只帶已提交內容，符合「驗證標的＝合入的提交」。

### D2　`.venv`＝連結到主樹 `.venv`＋`PYTHONPATH` 指向 clone

- clone 根建 `.venv` 連結（Windows＝directory junction，POSIX＝symlink）指向主樹 `.venv`。WHY：`tools/git-hooks/pre-push` 的 `pick_repo_python` 只認 `$TOPLEVEL/.venv`（DEF-200-315，互動式入口不落回 PATH），沒有它 pre-push 全部 leg 在「找不到 python」上 fail-loud。
- 全套環境一律設 `PYTHONPATH=<clone>/AutoClaude<os.pathsep><clone>/tools`。WHY：ADR-006 爭點 5 已證 editable `.pth` 寫死主樹；`PYTHONPATH` 項在 `sys.path` 中排在 site-packages（含 `.pth` 加入的路徑）之前，`import autoclaude`／`import lib` 先解析到 clone。這正是 ADR-006 爭點 5 的指定處置（「絕對路徑直譯器＋明文設 `PYTHONPATH` 指向拷貝樹」），本 ADR 把它機械化，不再靠任務書記得。
- 與 ADR-006 §7「symlink 或複製 `.venv` 以求隔離」的關係：那一列拒絕的是「以為連結 venv 就隔離了」——本 ADR 不靠連結隔離（連結只為讓 pre-push 找得到直譯器），隔離靠 `PYTHONPATH`，且由 D3 每次驗證。
- 清理：只刪連結本身。刪前驗 `Path.is_junction()`（Windows，Python 3.12+；3.11 以 `os.readlink` 成功與否判）或 `is_symlink()`；驗不到即中止清理並記痕跡，不遞迴刪除（記憶 `cleanup-after-tests-convention`：指向 repo 的 junction 只刪連結本身）。

### D3　每次自證（fail-closed）＋紅綠自證測試

- 執行期自證（合入步驟 4.5）：以 clone 的 `.venv` 直譯器、全套同一份環境，在 clone 根執行 `import autoclaude, lib.quota_policy` 並印兩者 `__file__`；任一不在 clone 之下 ⇒ `MERGE_VERDICT=carrier_leak`，不跑全套。這把 ADR-006「失效是靜默的」那一格改成大聲。
- 測試期紅綠自證（TCS AC-MG-03b、E2E-AP-MG-03；執行期自證的 AT 是 AC-MG-03a）：在 clone 的 `tools/`、`AutoClaude/`、`AISDLC_SDD/<LATEST>/` 三個子樹各植一個會讓對應 leg 轉紅的突變（主樹不植）⇒ 全套必紅。主樹沒有這些突變，所以「必紅」本身就證明子行程鏈（pre-push → 子專案 hook → `local_ci_gate` → pytest）每一層都在測 clone、沒有在某一層丟掉 `PYTHONPATH` 而回頭測主樹（editable `.pth` 指向的正是主樹）——執行期自證只驗頂層，這條驗全鏈。對應突變 MU-MG-6：拿掉 `PYTHONPATH` 注入 ⇒ 這條 AT 必須轉紅（全套變綠＝測到主樹）。測試一律不改真主樹。

### D4　寫入者可用 harness 內建隔離，前提三條

ADR-006 爭點 4 的三項事實逐條處置：

| 爭點 4 事實 | 處置 | 機械物 |
|---|---|---|
| ① 從 `origin/main` 播種（看不到在途成果） | `.claude/settings.json` `worktree.baseRef: "head"`（官方設定鍵，SD-0 2026-11-25 查官方文件：「`"head"`: branch from your current local `HEAD`, so the worktree carries your unpushed commits」） | TCS AC-WT-01a（設定存在）、E2E-AP-WT-01（真 `claude -p` 派隔離子代理，斷言起點含未推送提交） |
| ② 建立具名分支（與「只用 main」抵觸） | 代理分支只存活到合入：合入步驟 6 `git branch -d` 收回；main 是唯一長存分支、唯一推送目標。「只用 main」的原意（不開長期 feature branch、不推非 main 分支）不受影響 | TCS AC-MG-01e（清理後 `git branch --list "worktree-agent-*"` 回到起始集合） |
| ③ 不回收（殘留分支落後 105 commit） | 合入步驟 6 `git worktree remove`（不帶 `--force`）；殘留普查鎖：合入痕跡判 ok／noop 的代理分支或 worktree 仍在 ⇒ 紅；`sessionctl status` 顯示殘留數 | TCS AC-WT-01c |

驗證**不在**代理的 linked worktree 內做（D1）；代理自己在 worktree 內跑的單元測試只是開發迴圈，不是合入閘。

### D5　機器本地狀態：白名單帶入＋基線對照（v1.1，QA 複審 N-03；接手 ADR-006 爭點 3「量測機器本地狀態的那一族另案處理」）

獨立 clone 只帶已提交內容，主樹的 ignored 機器本地狀態不在裡面。SD-2 當回合唯讀普查主樹（`git ls-files --others --ignored --exclude-standard --directory`）的現存項：`.env`（四層 env 鏈第三層）、`.dev_env_state.json`（`tools/dev_start.py` L54 寫、`tools/lib/dev_platform_provenance.py` 與 `tools/git-hooks/prepare-commit-msg` 讀）、`AISDLC_SDD/AISDLC_SDD_v0.01/arch-fitness.json`、`AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/**`、`.hypothesis/`、`.act-runs/`、`.vscode/`、`.claude/worktrees/`、`.venv/`。缺了它們，clone 內的全套可能出現主樹推送不會有的紅（假紅：merge 永遠 `red`、自動駕駛卡死），或因 `.env` 缺席讀到出廠值而假綠。兩道處置：

1. **白名單帶入**（tools/lib/autopilot/carrier.py（實作階段新建）單一常數 `CARRIER_LOCAL_STATE`，每筆附 WHY；**預設不帶**，只有「全套會讀它當判定輸入、缺席會改變判定」者才入表）。初始成員與處置：

   | 項 | 處置 | WHY |
   |---|---|---|
   | `.env` | 帶入：同卷**硬連結**（不複製內容到別處；跨卷 ⇒ 不帶並以 `carrier_divergence` 記「無法帶入」，不跑全套） | 四層 env 鏈的本機層；缺席＝讀出廠值，可能假綠。硬連結使 clone 刪除時只刪目錄項、主樹檔不受影響；機密不出現第二份內容 |
   | `.dev_env_state.json` | 帶入：複製（非機密、數百位元組） | 平台出處判準讀它；缺席會走「未跑 dev_start」分支而與主樹不同 |
   | `.venv/` | D2（連結） | — |
   | `arch-fitness.json`、`build/reports/**` | 不帶 | 全套的**產物**，不是輸入；clone 內重新產生 |
   | `.hypothesis/` | 不帶 | 快取；缺席只影響速度與範例重播，不改判定（重播差異由基線吸收） |
   | `.act-runs/`、`.vscode/`、`.claude/worktrees/` | 不帶 | 與全套無關 |

   WP-MERGE 第一動作以「同一 HEAD 的乾淨 clone 跑全套 vs 主樹 pre-push」逐 leg 對照，把普查中缺席會改變判定的項補進表（同一 commit 改本表）；之後新增 ignored 輸入檔＝改表。帶入後、跑全套前，**每筆白名單項在 clone 內必須存在且內容雜湊等於主樹**（主樹本身沒有該檔者跳過並記痕跡），否則 `MERGE_VERDICT=carrier_divergence`（附缺項），不跑全套。
2. **基線對照**：同一 clone、同一環境，在套上代理提交**之前**（主樹本地 HEAD）先跑一次同款全套作基線；以 `(主樹 HEAD sha, CARRIER_LOCAL_STATE 內容雜湊, 主樹 .venv 直譯器路徑)` 為鍵快取於 `~/.autosdd/autopilot/baseline.jsonl`，同鍵且結果為綠者重用、不重跑（主樹 HEAD 不變時連續合入只付一次基線）。判定：基線綠＋候選紅 ⇒ `red`（代理的）；基線紅 ⇒ 候選的紅 leg 集合 ⊆ 基線紅 leg 集合 ⇒ `MERGE_VERDICT=carrier_divergence legs=<基線紅 leg>`（載具或主樹本身的問題，不算到代理頭上；產修復任務書，主控派修載具／主樹，不 ff）；候選多出基線沒有的紅 leg ⇒ `red`（只列多出的 leg）。
   - WHY 不用「最近一次主樹 pre-push 綠的痕跡」當基線：主樹 pre-push 跑在主樹、不跑在 clone，它證不出 clone 這個載具本身是否與主樹等價——正是要量的東西。
   - 誠實劃界：基線只吸收「主樹 HEAD 在 clone 內就紅」的載具差異；代理提交**與**機器本地狀態互動才出現的差異（代理新增一個讀 ignored 檔的測試），基線看不見，由白名單普查與 `carrier_divergence` 的缺項檢查承接；假綠方向（缺檔讓某 leg 變寬鬆）只由白名單帶入防。

## 3. 被拒絕的替代

| 方案 | 拒絕理由 |
|---|---|
| 維持 v1.0：`%TEMP%` 下 linked worktree 跑全套 | 無 `.venv` ⇒ pre-push fail-loud；補上 `.venv` 連結後仍共用 `refs/stash` 與 `.git/config`（ADR-006 §2.3） |
| 在主樹上 rebase＋跑全套 | 主樹常為髒（ADR-006 爭點 2 實測）；違反「主樹在 ff 之前從未被寫」的不留半套條件 |
| 每次合入建新 venv | 分鐘級＋需網路（ADR-006 §7 同列理由） |
| 設 `AUTOSDD_ALLOW_PATH_PYTHON=1` 讓 pre-push 落回 PATH python | 那是人為逃生口；由 Claude Code 衍生行程設定它等同模型自設逃生口（Autopilot 設計 §5 的同型問題） |
| 容器 | ADR-006 §7 同列理由（大量判準量測主機狀態） |

## 4. 後果

- 正面：合入閘測到的是合入樹，且這件事每次被驗；寫入者隔離與 main-only 原則並存；殘留分支有鎖；機器本地狀態的差異不會被算成代理的紅（D5 基線）。
- 負面（D5）：主樹 HEAD 每變一次多付一次基線全套（同鍵重用）；`.env` 跨卷時無法帶入、該次合入改走 `carrier_divergence`。
- 負面：Windows 每次合入一棵全額工作樹（數百 MB 等級，以 `df` 類工具量，不用 `du`，ADR-006 §2.3）；連結的建立與刪除是新的平台差異面（D2 已逐平台寫明）。
- 誠實劃界：執行期自證只驗兩個頂層套件的解析；以 `importlib` 動態載入或子行程清空環境的路徑，只有測試期紅綠自證（三子樹各一突變）看得到，且只對植了突變的那幾條 leg 有鑑別力。

## 5. 三問

1. 另一台機器會不會回來？junction／symlink 依平台分支、刪除前驗身分；`PYTHONPATH` 分隔符取 `os.pathsep`；自證每次執行；每台機器不同的 `.env`／`.dev_env_state.json` 由 D5 白名單帶入該機器自己的那一份並逐筆驗雜湊，其餘機器本地差異由同機基線對照吸收（基線鍵含主樹 HEAD 與白名單雜湊，跨機器不共用）。
2. 文件／座標是否一致？Autopilot 設計 §3、TCS、ADR-006 §7 後加的指向行（CLOSE）、根 CLAUDE.md 鐵律七檢查表第 4 條加註，同 commit 收齊。
3. 有沒有「之後再看」？無；Windows 佔碟是已知成本，已由步驟 0 的空間檢查處置；ADR-006 爭點 3 的機器本地狀態族由 D5 接手（白名單初始成員由 WP-MERGE 第一動作以逐 leg 對照補齊，屬實作步驟、不是延後）。
