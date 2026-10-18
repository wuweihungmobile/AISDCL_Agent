# AutoSDD_improving_116 — 軌道① T1 再開：三子專案（AutoClaude／AgentConsole／本專案根層）以 AISDLC_SDD 流程自我開發

> **狀態**：主控裁決稿（§1～§6 定稿；§7 各棒交卷、§8 零退化矩陣、§9 審查閉環與休眠重評於收尾補）。
> **軌道①**（驅動器＝`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`）。再開依據＝範本〈🏁〉T1（掌舵者直接立案）；`docs/04_planning/AutoSDD_improving_115.md` §9.3 的休眠宣告自本檔起暫停效力；本輪收尾時依範本〈🏁〉重評休眠判準三條並於末節重宣告。
> **掌舵者 T1 原文（逐字，2026-10-18）**：「3.AutoClaude, AgentConsole等模組, 是否可以完美利用AISDLC_SDD開發流程進行開發,包含本專案?!」「以AISDLC的程序(請Architect/SA/SD/Developer考慮如何規劃設計實作獨立審查?省去非必要文件，只留一定需要文件)」「因為Fable Token實在花太兇(Fable當用則用)，請派Subagent時, 使用Sonnet 5！你當主控Agent還是使用Fable 5.1」「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策」「收輪最後, 請一併將暫存檔或測試相關檔案刪除!」「==> 授權將相關檔案與目錄刪除」（指上輪留下的 `%TEMP%\e2e`、`D:\w5e2e`、Docker 卷 `aisdlc_*` 與匿名卷）。
> **問題 1／問題 2 的處置**：整合輪 115 已答「問題 1＝是（範圍 Windows／haiku／單機／Unit 類 AT）、問題 2＝完成」，兩問本輪不重答；問題 1 的但書已逐項落在 improving_115 §5.2 延後清單（各附再開症狀），本輪只在與問題 3 交集處引用。
> **三柱分佈**：**B 柱（主）**＝手腳框架 dogfooding——三子專案各以自己為 SDD 外部專案走一遍閘門；**C 柱（次）**＝AutoClaude 自身的開發方法論指向、skills 鏡像與閘門對映；**A 柱（小）**＝Bridge 路徑對「本 repo 內的子專案」的綁定與狀態目錄一致性。
> **人員**：主控 Fable 5.1（裁決、親驗、commit；不投票）；Architect、SDD 機制探針、SA、Developer（各棒）、QA 皆 Sonnet（`model: sonnet`）。依範本〈產品輪的固定成本瘦身〉：審查＝設計鏡（Architect＋探針，已完成）＋QA 零信任鏡（W3）；本輪不碰根層守衛面（例外見 D-116-14）、不修 PRD、不碰 `_HAPPY_PATH`／`*.tla`。
> **文件瘦身聲明**：本輪新增文件＝本檔、審查證據檔（docs/06_quality 下的 AutoSDD_ZeroTrust_Audit_116）、三份 dogfood 的 TCS（含 FRD-lite 檔頭，各住子專案自己的 docs/03_testing/contracts/）。不新開 ADR（決策全在 §6，收尾由主控在 `docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md` 補附錄 D 指路）；SOP 寫進既有 `AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；不另寫各棒任務書（§6 棒次表即任務書）；不寫 rtm_backfill 類檔。
> **額度紀律（開工實測）**：`python tools/session_resume_planner.py --pace`＝weekly_all 60%、cap=4、recommended=2 ⇒ 每波最多兩個 Sonnet 並行；上輪五個 Sonnet 並行四小時燒滿 5h 窗。W0 兩位（Architect 567k tokens、探針 404k）已用。

## §1 現況地圖（Architect 讀碼＋探針實測；座標相對 repo 根，HEAD `cf0d72e1`）

| 專案 | 規格文件現況 | 現行閘門 | CLAUDE.md 對方法論的指向 | 測試執行器／可否 `pytest -k` 評估 AT | FSM 鍵／狀態目錄（git 忽略？）／docs 根 |
|---|---|---|---|---|---|
| AutoClaude | 01（2 FRD）／02（4 SRD）／03（12，無 contracts/）／04（54，ADR 在 04_planning/ADR/）／05／06／08；命名底線式 | G0～G6 交付里程碑（四方＋PM 簽核；`AutoClaude/docs/05_development/gate_audit.md`）＋LOC／importlinter／ruff 機械閘 | 12 行指向不存在的 `AISDLC_v0.09/`（`AutoClaude/CLAUDE.md` 第 43、62、72～80、87～88 行）；**400／400 行零餘裕**；contract 測試鎖「Agent 自動載入」標題必留 | pytest（xdist）；可 | `autoclaude-<slug>`／`AutoClaude\build\reports\fsm`（忽略 ✓ `AutoClaude/.gitignore:9`）／`AutoClaude/docs/` |
| AgentConsole | 只有 02／04／06；**無 01／03**；PRD 住根 `docs/01_requirements/Agent_ConsoleUI_PRD.md`；無 `.claude/` | W1～W5 波次入口／出口閘＋契約先行＋QA 獨立審查＋RTM 回填（`AgentConsole/docs/04_planning/Implementation_Plan.md` §2） | 無方法論指向（SDD 只列為被包裝引擎）；164 行；鐵律 7 限 ADR-XPLAT-016 §11 白名單 | engine-bridge＝pytest 可；backend＝Gradle 否；frontend＝vitest／Playwright 否 | `agentconsole-<slug>`／`AgentConsole\build\reports\fsm`（忽略 ✓ `AgentConsole/.gitignore:16`；Bridge 固定 `<execution_path>/build/reports/fsm`）／`AgentConsole/docs/`＋根層 PRD |
| 根層（本專案） | 01（3 PRD）／02（2）／03（3 證據 JSON）／04／06；ADR 在 04_planning/ADR/ | 軌道①範本四件套＋缺陷帳本＋十二道棘輪＋雲端五支 workflow；與 SCG 無對映 | 根 `CLAUDE.md` 有 SDD 快查，未宣告子專案可採 SDD 迴圈 | `tools/tests` 是 unittest，非 `pytest -k` 評估目標；AT 應放 `AISDLC_SDD/scripts/tests/` | `monorepo-<slug>`／`build\reports\fsm`（**未忽略 ✗**，根 `.gitignore` 只有 closure／drift）／`docs/` |
| AISDLC_SDD 自身 | v0.30 `docs/` 只有骨架 | SCG-0～6＋FSM＋Rule 9＋TLA+ | `AISDLC_SDD/CLAUDE.md` 第 112、426 行把專案層文件指向框架樹（與外部專案模式矛盾） | pytest 可 | `sdd-<slug>`／`AISDLC_SDD\AISDLC_SDD_v0.30\build\reports\sdd-dogfood`（忽略 ✓；避開預設 fsm/ 的 INIT 檔）／版本目錄 `docs/` |

決定「鍵的單位」的 FSM 事實：`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/transition_rules.py` 的 `RELEASE: set()` 為終態，IMPLEMENTATION／PR_REVIEW／RTM_VERIFY 沒有回 SPEC_DRAFTING 的邊 ⇒ **一個 FSM 專案＝一個功能的完整週期**（整合輪 115 的 `tg-phase` 即此型）；狀態目錄可共處多個 FSM 檔，adapter／Bridge 以專案鍵指認、無鍵且多檔＝fail-closed。

### 1.1 探針事實矩陣（Sonnet 探針 2026-10-18；零 LLM token，只有 P9 用 haiku；逐字輸出住 scratchpad `probe_116/`，收尾刪除；摘要搬入證據檔）

| 案 | 事實（實測） |
|---|---|
| P1 | 缺檔時 `show`／`transition` 自動建 `FSM-STATE-<SDD_PROJECT 原值>.yaml`；`--must-exist` rc=5 不建檔；鍵 AutoClaude／AgentConsole／AISDCL_Agent 淨化後不變；CLI 必須 `python -m tools.fsm_runtime.fsm_runtime` 且 cwd 或 `PYTHONPATH`＝版本目錄（直接跑 .py＝ImportError rc=1） |
| P2 | `transition` 六步＋`negotiate-enter`／`negotiate-exit --outcome agreed` 共 8 步 rc 全 0，終態 IMPLEMENTATION |
| P3 | 根 router 的 SessionStart 以 `SDD_STATE_DIR`／`SDD_PROJECT` 注入 `project: AutoClaude`、`current_state: IMPLEMENTATION`、命中 11 條規則；pythonw 與 python.exe 輸出逐字相同；**不設 `SDD_STATE_DIR` 時 hook 對不存在的專案名在框架 `build\reports\fsm` 自動建檔**（git 忽略） |
| P4 | IMPLEMENTATION 的規格檔 deny＝路徑字串含 `docs/01_requirements/`｜`docs/02_architecture/`｜`docs/03_testing/`（含相對路徑、Write），**與檔案屬於哪個子專案無關**；程式碼與 `docs/04_planning/` 放行；deny 走 stdout JSON `permissionDecision=deny`、rc=0 |
| P5 | ESCALATION 下 Read／Bash／PowerShell／Edit 全 deny（附恢復指令，**但該指令不含 `SDD_STATE_DIR`／`--project`**）；去掉 `SDD_ACTIVE_VERSION` 全放行；`resume-from-escalation --to IMPLEMENTATION` 後解鎖；根 `.claude/settings.json` 的 router Pre／Post matcher 不含 PowerShell（讀 settings） |
| P6 | 兩遙測旗標＝0 時 P1～P5 後 `git status --short` 空、governance `diff --stat` 空 |
| P7 | `spec-frozen --digest --root <子專案>` 或 `--root <monorepo 根>` 皆 rc=0 且摘要相同、等於獨立計算；自訂 `SDD_STATE_DIR` 又不給 `--root`＝rc=4 `doc_not_found`、狀態不變 |
| P8 | Bridge 狀態目錄＝`<sdd.root 或 execution_path>/build/reports/fsm`、鍵＝`fsm_component(sdd.fsm_project)`、CLI 恆 `--must-exist`（狀態檔須先存在）；Bridge `fsm_component` 與 SDD `sanitize_component` 對 13 個樣本逐筆相同 |
| P9 | headless `claude -p --model haiku --debug hooks`（cwd＝repo 根、三件組設定）rc=0、SessionStart success ×2、AutoClaude@IMPLEMENTATION 注入成 `hook_additional_context`；狀態檔 sha256 不變 |
| P10 | skills 鏡像 42／42、`sync_exposed_skills.py --check` rc=0（59 檔一致） |
| P3x | `CLAUDE_PROJECT_DIR` 指向子專案時啟動器找不到 router ⇒ rc=0 空輸出（**靜默 fail-open**）；直接跑 router＝WARN＋放行 ⇒ SDD session 一律從 monorepo 根啟動 |

## §2 問題 3 的判準與判定（主控定義；「完美利用」＝七條同時成立；缺任一降為「部分」）

| 判準 | 內容 | 開工判定（W0） | 證據 |
|---|---|---|---|
| C1 入口可達 | 從 monorepo 根 session，不改凍結版、不改 Claude Code 設定，只靠 `SDD_ACTIVE_VERSION`／`SDD_STATE_DIR`／`SDD_PROJECT` 即可把任一子專案當成 SDD 外部專案：SessionStart 注入該專案 FSM 狀態與規則；context-ledger 守門生效 | **部分** | 機制成立（P3／P4／P9）；無 SOP、`ONBOARDING.md:150` 只教框架自身；Windows 根 router 不匹配 PowerShell（G-116-17） |
| C2 文件落點 | 各子專案的 SDD 產出寫進自己的 docs/0x；狀態目錄不入 git；Bridge 與 session 解析到同一目錄 | **部分** | AutoClaude／AgentConsole 忽略 ✓、根層 ✗（G-116-09）；`AISDLC_SDD/CLAUDE.md` 兩處矛盾（G-116-10）；Bridge 同址只靠 `execution_path`＝子專案根（P8） |
| C3 閘門一致 | G／W 與 SCG-0～6 有明文對映；三子專案 CLAUDE.md 指向 AISDLC_SDD LATEST | **否** | 無對映（G-116-06）；`AutoClaude/CLAUDE.md` 12 行死連結（G-116-07） |
| C4 棕地可用 | 增量條款可用；Java／TS 有明確可用或明確劃界的 AT 評估路徑 | **部分** | 增量條款已落地（整合輪 115 D-115-07）；基線採納無官方程序（G-116-08）；§7 把 Java／TS 整個排除（G-116-11） |
| C5 技能／代理可達 | SDD skills 與 agent YAML 在根 session 對子專案檔案可用 | **部分** | 42 支可用 `AISDLC_SDD:<skill>` 前綴叫起（P10）；**`AutoClaude/.claude/skills` 是 33 支 AISDLC v0.09 舊版（缺 sdd-gate 等 9 支），在 AutoClaude 檔案上 harness 優先給舊版**（G-116-13） |
| C6 實證 dogfood | 各一個 AutoClaude、AgentConsole、根層的真實小功能經 SDD 流程完成並 commit；至少一個委派路徑、至少一個純 SDD session 路徑 | **部分（1／3，僅委派）** | 只有 115 的 T-G（AgentConsole、委派、hooks-OFF） |
| C7 可重複且不鎖死 | 有 SOP；阻塞態不鎖死根 session 或有明文逃生口 | **部分** | 逃生口存在（P5）但恢復指令在外部專案模式指錯目標（G-116-01，P1）；無 SOP |

## §3 缺口清單 G-116-NN（Architect 提、探針證、主控歸格；嚴重度：P1 走不通／鎖死／資料分裂、P2 須手動繞過或文件自相矛盾、P3 文字／可用性、P4 理論洞）

| ID | 級 | 證據 | 最小修法 | 持有面 | 歸格 |
|---|---|---|---|---|---|
| G-116-01 | **P1** | P5：ESCALATION 的恢復指令不含 `SDD_STATE_DIR`／`SDD_PROJECT`／`--project`（`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/recovery_hint.py` 第 140～161 行零命中）；照貼＝打到框架預設 INIT 檔、回 noop rc=0、子專案仍鎖死 | `recovery_command()` 讀行程環境：外部專案模式下兩殼形態都帶環境賦值與 `--project`；補 `-W ignore::RuntimeWarning`；與 Bridge `AgentConsole/engine-bridge/app/sdd_state.py` 的 `recovery_commands` 對拍；回歸鎖 `tools/tests/test_recovery_hint_passes_ps_lint.py` 續綠 | Dev-SDD | 立案 DEF-200-544、W1 修 |
| G-116-02 | P2 | 三支 skill（sdd-gate／sdd-review／rtm-generate）規定報告與 RTM 寫 `docs/03_testing/`，而 Rule 9.6 #3 在 SCG_VALIDATION／PR_REVIEW／RTM_VERIFY／IMPLEMENTATION 擋寫該前綴（115 的 DEF-AC-018 六列 BLOCKED） | 報告與 RTM 落點改 `docs/06_quality/`（AgentConsole 現況即如此）；`docs/03_testing/` 保留給凍結前的測試規格（TCS／策略／計畫）；改三支 SKILL.md＋GATE 文件＋`AISDLC_SDD/CLAUDE.md` Rule 2 表 RTM 列；**不改 hook 判準** | Dev-SDD | 立案 DEF-200-545、W1 修 |
| G-116-03 | P2 | P4：規格檔 deny 看路徑子字串、不認專案根 ⇒ 一個子專案的非草擬態擋整個 monorepo 的 docs/01～03 寫入 | SOP 明文：hooks-ON 視窗同時只綁一個功能；跨專案文件編修走 hooks-OFF 視窗；不改判準 | Dev-SDD（SOP） | 本輪文件化；判準改動＝延後（再開症狀：合法寫入被他專案狀態誤擋） |
| G-116-04 | P2 | `ONBOARDING.md:150` 只教 `SDD_ACTIVE_VERSION`；`SDD_AUTOCLAUDE_BRIDGE.md` §7 寫「不要為了走這條迴圈而啟用 Rule 9 hooks」 | BRIDGE 新 §8 SOP＋三件組表；§7 改三徑；ONBOARDING §4 末一句指路 | Dev-SDD；主控（ONBOARDING） | 本輪修 |
| G-116-05 | P2 | RELEASE 終態、無回邊（§1） | SOP 定一功能一鍵（D-116-03） | Dev-SDD | 本輪修 |
| G-116-06 | P2 | G／W 與 SCG 無對映 | BRIDGE §8 對映表（D-116-05）；兩份子專案 CLAUDE.md 各一行指路 | Dev-SDD；Dev-DOC | 本輪修 |
| G-116-07 | P2 | `AutoClaude/CLAUDE.md` 12 行指向不存在的 `AISDLC_v0.09/`；400／400 行；`AutoClaude/tests/contract/` 三支 claude_md 測試鎖 | 保留「Agent 自動載入」標題，body 換成指向 `../AISDLC_SDD/`（LATEST、INIT、SCG、§8 SOP）的三行；其餘站點改指或刪；**淨 ≤0 行** | Dev-DOC | 立案 DEF-200-546、W1 修 |
| G-116-08 | P2 | 棕地 Stage-1 基線採納無官方程序（115 以五次 `transition`＋`spec-frozen --digest` 模擬） | BRIDGE §8 收錄採納鏈與 reason 慣例「baseline adoption；SCG 未重跑」；各子專案 Stage-1 文件清單；不新增 CLI | Dev-SDD | 本輪修 |
| G-116-09 | P2 | P8：根層 `build/reports/fsm/` 未被 `.gitignore` 忽略 | 根 `.gitignore` 加 `/build/reports/fsm/` | 主控 | 立案 DEF-200-547、W1 後單人窗口修 |
| G-116-10 | P2 | `AISDLC_SDD/CLAUDE.md` 第 112、426 行把專案層文件指向框架樹 | 兩處各補一句：`SDD_STATE_DIR` 有設時專案層文件寫 `<專案根>/docs/` | Dev-SDD | 立案 DEF-200-548、W1 修 |
| G-116-11 | P2 | §7 兩條件把 Java／TS 子專案連規格／閘門／RTM 一併排除；評估白名單只有 `pytest {path} -k "{at}" -q`（`AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py:54`） | §7 改三徑：委派迴圈（AT 須 pytest 可評）／SDD session-only（只需規格可凍結；AT 由 session 內自跑 gradle／vitest 並逐字貼證據）／一般流程；不擴白名單 | Dev-SDD | 本輪修；pytest 殼代跑 Java／TS＝延後（再開症狀：掌舵者要求 Java／TS 功能走 Console 委派）；擴白名單＝退役（依據 Gap-046，見根 `CLAUDE.md` 鐵律三表） |
| G-116-12 | P3 | P3：缺 `SDD_PROJECT` 退回目錄名、缺檔即建 ⇒ 子專案狀態目錄多一個 INIT 檔 | SOP：三件組缺一不可＋開場 `show --must-exist`；DF-C 的 `sdd_env.py` 一次產三件 | Dev-SDD；DF-C | 文件＋helper 本輪；碼收緊延後（再開症狀：子專案狀態目錄出現 `FSM-STATE-AISDLC_SDD.yaml`） |
| G-116-13 | P2 | `AutoClaude/.claude/skills` 33 支 AISDLC v0.09 舊版（35 個 tracked 檔，2026-07 後未動），harness「most specific wins」⇒ 在 AutoClaude 檔案上拿到非 SDD 版 | `AISDLC_SDD/scripts/sync_exposed_skills.py` 增第二鏡像目標 `AutoClaude/.claude/skills`（`--check` 同守）；根層與 AgentConsole 不另建鏡像、SOP 一句「一律 `AISDLC_SDD:<skill>` 前綴叫起」；skill 內相對路徑語意規則（`docs/`、`build/reports/` 以專案根為準；`workflow/`、`governance/`、`docs_template/`、`agent/` 以版本目錄為準） | Dev-SDD（腳本＋測試）；主控（`--write` 單人窗口） | 立案 DEF-200-549、W1 修 |
| G-116-14 | P3 | AgentConsole 無 01／03；ADR 位置與命名與 SDD 期望不同 | 不搬檔；追溯表以實際路徑引用；AgentConsole 新建 docs/03_testing/contracts/（隨 DF-B 的 TCS 建立）、CLAUDE.md 鐵律 1 改 02／03／04／06 | Dev-DOC；SA | 本輪修 |
| G-116-15 | P3 | 115 的 DEF-AC-015／016／017：增量專案的機械半段（SLV 檔名樣式、`score_frd` 表格 AC）空轉 | SOP 註明由 QA 人讀補位 | Dev-SDD | 文件本輪；碼延後（再開症狀：QA 發現機械半段放行了有缺陷 AC） |
| G-116-16 | P3 | 子專案 `.claude/settings.json` 的 hooks 只在以該目錄為根的 session 載入；根 session 無 AutoClaude 守衛（反之亦然） | SOP 註明；以 CI／ruff／LOC 兜底 | Dev-SDD | 本輪文件化 |
| G-116-17 | P4 | 根 router matcher 無 PowerShell（`.claude/settings.json` 第 60、137 行）；D-115-09 已登理論洞 | 見 D-116-14 | 主控（守衛面） | 延後（症狀由 W2 hooks-ON Windows 視窗觸發，W4 裁） |
| G-116-18 | P4 | adapter／Bridge 向上找祖先狀態目錄；根層 FSM 目錄是所有子專案的祖先 | compile 一律帶 `--fsm-project`；SOP 一句 | Dev-SDD | 延後（再開症狀：子專案 compile 回應的 `fsm_project` 不是該子專案的鍵） |
| G-116-19 | P4 | 檔案系統大小寫差異 | 標準鍵一律小寫 kebab（D-116-03） | Dev-SDD | 本輪文字 |
| G-116-20 | P4 | 狀態在被忽略的 build/ 下，凍結證據不入庫 | 每功能收尾把 `show` 逐字輸出與 `spec_doc_digests` 引進證據檔（115 §1.3 做法） | QA | 本輪文字 |
| G-116-21 | P3 | W2 實證：`HUMAN_PENDING → SPEC_DRAFTING` 不是合法邊（CLI `TransitionError`），人工閘沒有「退回修訂」的直達邊；115 §5.2 已把 Console 退回邊列延後 | SOP §8.6 寫明合法迴路＝`HUMAN_PENDING → SPEC_REGRESSION_CHECK`（允許寫規格）→ 修訂 → `HUMAN_PENDING` → `spec-frozen`；不改 `_HAPPY_PATH` | 主控（收尾） | 本輪文件化；Console 退回邊維持 115 延後（再開症狀不變） |
| G-116-22 | **P1** | W2 DF-A 真跑：引擎把 `claude -p` JSON 的跨回合累計 usage 當目前 context，真實樹 16 回合即偽 TOKEN_HALT（DEF-200-550） | `context_pct_from_claude_json` 取 `usage.iterations[-1]`，缺則退回累計 | 主控（代 Dev，額度守衛擋下扇出時） | 立案 DEF-200-550、同輪 fixed@d9dc1ff0 |
| G-116-23 | P3 | W2 DF-A 真跑：真實樹的根 CLAUDE.md 鐵律一讓 haiku 正確拒用 Bash，而委派批次的 `--allowedTools` 沿 115（TEMP 專案）只給 `Read,Edit,Write,Bash` ⇒ 評估指令跑不了（6 次 PowerShell 呼叫被 permission_denials 擋） | 真實樹的委派批次 `--allowedTools` 須含 `PowerShell`（Windows）；§8.6 徑① 補一句 | 操作員重跑；主控（SOP 一句） | 本輪修 |
| G-116-24 | P3 | W2 DF-A 真跑：引擎 subprocess 模式沒關 claude 的 stdin，每次呼叫印 `Warning: no stdin data received in 3s` 白等 3 秒 | 引擎 spawn 時以 `stdin=DEVNULL` 或關閉（須先確認 `send()` 路徑不依賴 stdin，115 的 DEF-AC-021 同族） | — | 延後（再開症狀：每步固定多 3 秒；與 DEF-AC-021 合併處理） |

## §4 風險與誠實劃界

1. **hooks-ON 的開發 session 無法由本 session 的子代理承載**（環境變數在 claude 啟動前就定案）⇒ DF-B／DF-C 以 headless `claude -p --model sonnet` 子行程承載（探針 P9 證實 headless 會跑根 hooks 並注入），`--permission-mode acceptEdits --allowedTools` 明示；若權限層拒絕，逐字記錄並退回「子代理走 CLI 顯式驅動 FSM（hooks-OFF）」並在 C1／C7 標但書。
2. **DF-A 讓真 haiku 在真實 `AutoClaude/` 樹內寫碼**（T-G 是在 TEMP 專案根）；`git diff --name-only` 機械核對只准動 §6 D-116-15 列出的檔；越界即視為該路失敗並回滾（以 Edit 改回，不用 `git checkout --`，鐵律五）。
3. **TD-1 是外連能力**：AC 只要求 https、來自設定、逾時、有界退避重試（只對 5xx／網路錯）、永不拋例外、日誌遮罩 URL；私網（SSRF）封鎖不在本輪 AC，登理論洞（再開症狀：webhook URL 可由非管理者輸入）。測試一律 `httpx.MockTransport`，不碰網路。
4. **AI 自寫自驗**：SCG-4 由未參與規格與實作的 QA 獨立審查（規格作者＝SA、實作者＝haiku／headless Sonnet、審查者＝QA 三方不同）。
5. **Windows 真機、單機**：POSIX／Docker 不在本輪範圍（沿 115 §5.2 延後列）。
6. **額度**：每波 ≤2 Sonnet 並行；每棒交卷主控親驗；撞額度時用 SendMessage「從中斷點續做」。

## §5 刻意不做（只准三分類）

- **延後（附再開症狀）**：G-116-03 判準改動；G-116-11 pytest 殼代跑 Java／TS；G-116-12 碼收緊；G-116-15 機械半段修碼；G-116-17 根 matcher（見 D-116-14）；G-116-18；SSRF 私網封鎖（§4-3）；Console 內「改綁新鍵」UI（再開症狀：同一 Console 專案要跑第二個 SDD 功能時 `PUT sdd-binding` 不夠用）；CLI-only 路徑的 FSM 委派自動同步（沿 115 §5.2）。
- **退役（附依據）**：擴大 evaluator 白名單（依據：Gap-046 資安過濾器，evaluator 命令必須是單一模板內插）；「每子專案一個 FSM 鍵」（依據：`transition_rules.py` RELEASE 終態無回邊）；根層 `.claude/skills` 第三份鏡像（依據：每份鏡像都進每個 session 的技能清單，既有 `AISDLC_SDD:` 前綴已可達）。
- **立案**：DEF-200-544～549（§3），同輪 fixed。

## §6 主控裁決（2026-10-18；掌舵者授權「最佳化、最理想、最適當」代決，可隨時以 T1 推翻）

| 編號 | 裁決 | 落點 |
|---|---|---|
| D-116-01 | SOP 唯一落點＝`SDD_AUTOCLAUDE_BRIDGE.md` 新 §8〈子專案 SDD session（根 session、外部專案模式）〉；§7 改三徑；`ONBOARDING.md` §4 末與根 `CLAUDE.md`〈AISDLC_SDD 快查〉各一句指路（主控收尾） | Dev-SDD；主控 |
| D-116-02 | 立場維持「選用」：預設 hooks-OFF；hooks-ON 只在走 §8 的視窗；§7 三徑＝委派迴圈（AT 可 `pytest -k` 評）／SDD session-only（只需規格可凍結）／一般流程 | Dev-SDD |
| D-116-03 | FSM 單位＝一功能週期一鍵：`<sub>-<slug>`，sub ∈ {autoclaude, agentconsole, monorepo, sdd}，小寫 kebab、≤30 字；每子專案一個狀態目錄、目錄內多檔共處；週期終點 RELEASE_READY；合併進 main 且雲端 CI 綠後由收尾者記一次 RELEASE（終態，不重開；下一功能新鍵）；Console 一功能一專案 | Dev-SDD |
| D-116-04 | 三件組標準值（相對 repo 根）：autoclaude→`AutoClaude\build\reports\fsm`、agentconsole→`AgentConsole\build\reports\fsm`、monorepo→`build\reports\fsm`、sdd→`AISDLC_SDD\AISDLC_SDD_v<LATEST>\build\reports\sdd-dogfood`；`SDD_ACTIVE_VERSION`＝`sdd_version.py` 輸出去前綴；Console `execution_path`＝子專案根；`spec-frozen --root`＝含全部凍結文件的最小目錄（AgentConsole 含根層 PRD 時取 monorepo 根）；雙形態啟動區塊寫進 §8 | Dev-SDD |
| D-116-05 | 閘門對映：SCG-0～3＝三子專案共同的規格閘（FSM 可驗）、SCG-4～5＝品質閘；AutoClaude G0～G6 與 AgentConsole W 波次＝交付里程碑簽核，不改名、不取代；對映表入 §8，兩份子專案 CLAUDE.md 各一行指路 | Dev-SDD；Dev-DOC |
| D-116-06 | `AutoClaude/CLAUDE.md`：淨 ≤0 行；保留「Agent 自動載入」標題；同 commit 跑 `tests/contract/test_claude_md_*.py` 與 `check_loc_budget.py --json` | Dev-DOC |
| D-116-07 | Java／TS 劃界到 session-only；不擴白名單（退役）；pytest 殼代跑＝延後 | Dev-SDD |
| D-116-08 | 阻塞態逃生口三層（不改 hook）：①預防：同時一視窗、日常視窗可設 `SDD_HOOKS_DRY_RUN=1`、開場先在第二終端備妥帶環境的恢復指令；②解除：人在第二終端跑 `resume-from-escalation`（agent 不得代跑）；③全關：關視窗重啟並清 `SDD_ACTIVE_VERSION`（或 `SDD_HOOKS_DISABLE=1`）；不採把 DRY_RUN 寫進 `$PROFILE` | Dev-SDD |
| D-116-09 | 報告與 RTM 落點＝`docs/06_quality/`；`docs/03_testing/` 保留給凍結前測試規格（TCS／策略／計畫）；改三支 skill、GATE 文件、`AISDLC_SDD/CLAUDE.md` Rule 2 表 RTM 列；不改 `_is_blocked_spec_write` | Dev-SDD |
| D-116-10 | 棕地基線採納程序文件化（五次 `transition`＋`spec-frozen --digest --root`）；approver 慣例：掌舵者授權代決時記「掌舵者代理（主控）」並把授權依據寫進 reason；不新增 CLI | Dev-SDD |
| D-116-11 | 根 `.gitignore` 加 `/build/reports/fsm/` | 主控 |
| D-116-12 | skills：`sync_exposed_skills.py` 多目標鏡像（既有父層＋`AutoClaude/.claude/skills`），`--check` 守兩者；`--write` 對 AutoClaude 由主控於 W1 收工後單人窗口執行（刪 33 支舊版＝淨減法）；根層與 AgentConsole 不建鏡像、以 `AISDLC_SDD:` 前綴叫起 | Dev-SDD；主控 |
| D-116-13 | G-116-01 歸「訊息修正」（住 LATEST runtime，非根守衛面），W1 修；`tools/tests/test_recovery_hint_passes_ps_lint.py` 須續綠（PowerShell 形態以 `$env:X='…';` 賦值＋`Push-Location`／`Pop-Location` 成對） | Dev-SDD |
| D-116-14 | S-02 根 matcher：維持理論洞；W2 的 hooks-ON Windows 視窗若實證 CONTEXT-LEDGER 缺 PowerShell 呼叫＝暴露證據成立 ⇒ W4 主控單人窗口加 matcher（受保護路徑；分類器拒絕則 staged 交掌舵者）；前提＝G-116-01 已修並由 QA 演練證實恢復指令可用 | 主控 |
| D-116-15 | Dogfood 三標的：**DF-A** AutoClaude TD-1 Webhook 發送（來源 `AutoClaude/docs/05_development/Phase6_P1_Backlog.md` TD-1、`AutoClaude/autoclaude/utils/notifier.py` 未實作註記；委派路徑＝Bridge-only＋真 haiku，執行根＝`<repo>\AutoClaude`；准動檔＝新增 autoclaude/utils/webhook_sender.py、新增 tests/utils/test_webhook_sender.py、`notifier.py` 接線、Backlog TD-1 列）；**DF-B** AgentConsole DEF-AC-023 決策軌跡 `from` 還原（純 SDD session、hooks-ON enforce、headless Sonnet；准動檔＝新增 engine-bridge/app/fsm_trail.py、`AgentConsole/engine-bridge/app/routers/sdd.py`、新增 tests/test_fsm_trail.py）；**DF-C** 根層 `sdd_env.py` 三件組產生器（鍵 `monorepo-sdd-env`、狀態目錄根層、規格住根 docs/03_testing/contracts/；程式住 AISDLC_SDD/scripts/、測試住 AISDLC_SDD/scripts/tests/；純 SDD session、hooks-ON）。Java／TS 半不實證（D-116-07） | W2 |
| D-116-16 | 文件集見檔頭；ADR 不新開 | 主控 |
| D-116-17 | 棒次：W1 Dev-SDD ∥ Dev-DOC → 主控單人（gitignore、skills `--write`、親驗、commit）→ W2 SA（三份 FRD-lite＋TCS，串行）→ 主控核准凍結（三鍵）→ DF-B ∥ DF-C（headless Sonnet）→ DF-A（operator Sonnet＋Bridge＋haiku）→ W3 QA 獨立（一審全查、二審驗修復）→ W4 主控收尾（搬入、帳本、證據檔、休眠重評、環境殘留刪除、push 對帳） | 全部 |
| D-116-18 | 立案 DEF-200-544（G-116-01）、545（G-116-02）、546（G-116-07）、547（G-116-09）、548（G-116-10）、549（G-116-13）；同輪 fixed；其餘 P3／P4 以本檔為載體 | 主控收尾 |

## §7 各棒交卷與主控親驗（「他包回報」與「主控親跑」分開寫；commit 以 `git log` 為準）

| 棒 | commit | 主控親跑（當回合逐字） | 接受的偏離 | 未做／待整合 |
|---|---|---|---|---|
| W0 Architect（唯讀）∥ 探針 | — | 探針工作目錄 `probe_116/` 全部案 `git status --short` 空、框架預設狀態目錄 95 檔 sha256 零變 | 探針 P3 控制組在框架預設目錄建後即刪一檔（任務書授權） | 報告併入 §1、§1.1、§3 |
| W1 Dev-SDD（RT＋DOC） | `9f2d36c8` | ci-gate.ps1 rc=0（1478／2149／399）；test_recovery_hint 46 passed；根層 ps-lint 鎖 2 tests OK；sync_exposed_skills 20 passed | 恢復指令多帶 `--must-exist`；GATE 文件新增〈產出落點〉節；skip 改硬依賴與訊息去裸 `python` 字由主控補 | autoclaude 鏡像 `--write` 由主控做 |
| W1 Dev-DOC | `56fed990` | 四支 claude_md 契約測試 37 passed；check_loc_budget rc=0；AutoClaude/CLAUDE.md 392 行、AgentConsole 167 行 | 路徑正斜線；「W 波次」不寫 W1～W5 | 檔頭與 footer 的 v0.09 由主控改 |
| W1 主控單人 | `56fed990`、`54a3ddeb` | `git check-ignore -v` 命中 `.gitignore:70`；`--check` 兩目標 59 檔一致；根層全套 5384 rc=0；crossref 未結 0 | — | — |
| W1 Dev-SDD 第二棒（落點全樹） | `81faa59a` | ci-gate.ps1 rc=0；兩鏡像 59 檔一致；根層全套 5384 rc=0 | 超點名 17 檔（執行期測試報告同原則）；EVOLUTION_LOG 用 `###` 小節；S-15 殘留一併訂正 | BASELINE-PERFORMANCE-REPORT 與 API_Contract 一句由主控補 |
| W2 SA／操作員 | `f3fcb709` | Stage-1 凍結三鍵 rc=0（approver 掌舵者代理（主控））；Stage-2 凍結三鍵 rc=0；B／C negotiate rc=0 → IMPLEMENTATION | 走 SPEC_REGRESSION_CHECK 修訂（G-116-21）；DF-A 加 NFR-001-9／10、DF-B trigger 第三條件 | — |
| W2.5 QA 預審 | — | 由主控執行退回轉態三鍵 rc=0 | DF-A 7 項、DF-B 1 項、DF-C 1 項全數採納 | — |
| W2 DF-B（headless Sonnet，hooks-ON） | `4c327ea0` | pytest test_fsm_trail 7 passed；ruff 三檔綠；diff 只含 R8 與 import；hooks.log SessionStart success 注入 `agentconsole-fsm-trail`／IMPLEMENTATION | 行寬折行；型別標註 `Any -> Any` | 全套 1003／24 skipped＝他包回報 |
| W2 DF-C（headless Sonnet，hooks-ON） | `343d583a`、`e73749bf` | test_sdd_env 22 passed；scripts/tests 421 passed；ruff 綠；sdd_env 實跑印五鍵；dedup 鎖 OK | stdio 改走島內共用入口（主控補） | ONBOARDING §7 基線回填於收尾 |
| W2 DF-A 第一輪（Bridge＋真 haiku） | — | 操作員回報 FAILED（TOKEN_HALT 偽陽性）；主控親跑半成品 `pytest tests -k AT_001_1_1` 1 passed | — | 重跑待 RC-1 修後 |
| RC-1 修復（主控代 Dev；額度守衛擋下扇出） | `d9dc1ff0` | test_token_regex 39 passed；AutoClaude 全套 5881 passed；lint-imports 9 kept；check_loc_budget rc=0 | — | DF-A 重跑進行中 |
| W2 DF-A 第二輪（Bridge＋真 haiku，只加 `--allowedTools` PowerShell） | `306dbb2a` | 操作員回報＝他包回報：run `4e6bd6c9` COMPLETED 9/9、peak 14.66%、RTM at 9/9 ac 6/6、越界核對恰白名單三檔；主控親跑 pytest test_webhook_sender 9 passed（見 322e1351 列） | 真實樹鐵律一讓 haiku 拒用 Bash ⇒ 委派批次 `--allowedTools` 須含 PowerShell（BRIDGE §8.6 已補） | Bridge StepTracker 被日誌遮罩漏配 5-1（P3，DEF-AC-038） |
| W3 QA 一審（SCG-4 三路獨立審查＋C1～C7 真機驗收＋C7 阻塞態演練） | `c716ec17` | 幽靈路徑鎖 OK；crossref 未結 0 | DF-B PASS→RELEASE_READY；DF-A F-01／DF-C F-02（P2，測試鑑別力）PR_REVIEW FAIL 退回 IMPLEMENTATION | F-03／F-05（P3）、G-116-17 暴露證據（兩場 hooks-ON session 各 4 次 PowerShell 未入帳）、QA 建議 G-116-17 升 P2 |
| DF-A／DF-C 修復棒（hooks-ON headless Sonnet，只動測試檔） | `322e1351` | test_webhook_sender `9 passed, 1 warning in 0.51s`；test_sdd_env `23 passed in 0.34s`；ruff 兩檔 `All checks passed!` | 修復棒未跑突變複測（任務書未要求） | 二審由 QA 以 `mutate_all.py dfa dfc` 判 12 存活者是否全殺 |
| F-03／F-05 主控單人修復 | `1c802e92` | test_sdd_env `26 passed in 0.60s`；ruff 綠；dedup 鎖 OK；編碼鎖 OK；`--shell bash` 原始位元組 CR 5→0；test_webhook_sender `9 passed, 1 warning in 0.46s` | 不用 `reconfigure(newline)`：根層行內 stdio 複本棘輪只准縮不准長 ⇒ 改經 `sys.stdout.buffer` 寫位元組 | 併入 QA 二審 |
| W4 收尾文件（API_Contract「原樣」例外、Backlog TD-1、ADR-XPLAT-016 附錄 D、§7.1 改號） | `90d911e4` | — | — | §8／§9 於收尾補 |
| G-116-17 根 router matcher＋ONBOARDING 表① | `d75a38a0` | router r158 OK；hooks liveness OK；context_budget_guard OK；doc_loc_baseline_freshness OK；`sync_onboarding_baselines.py --write` rc=0（loc 18625／rootunit 5326） | PreToolUse 那一格被 auto mode 分類器拒（Self-Modification）⇒ 只套 PostToolUse 半，CLAUDE.md 守衛總表如實記兩半；帳本列（open／partial）撞淨額棘輪（本輪無可結列）⇒ 待掌舵者套上另一半後以 `fixed@` 入帳 | 掌舵者：`/permissions`→r 核准根 `.claude/settings.json` PreToolUse matcher 加 `PowerShell` |
| W3 QA 二審（`git archive` 匯出 322e1351／90d911e4 量測） | — | 他包回報：DF-A 殺 50/50、DF-C 殺 29/29、存活 0；弱化 0；F-03 拿掉修復 3/3 轉紅、F-05 AST 同；兩鍵 gate rc 0 → RELEASE_READY；新 P4 F-10／F-11（docstring 措辭）、F-12（`encode("utf-8")` 嚴格編碼，理論洞無暴露證據） | 主控裁決：P4 三筆登記不修（成品已過二審，RELEASE_READY→RELEASE 是唯一出邊）；DEF-AC-038 依 115 慣例留證據檔 §4 不另入帳 | RTM 兩檔同步由 QA 補（≈6 行） |

### 7.1 W1 持有面（互斥；§6 D-116 裁決的派工附表，W1 派工時用）

| 棒 | 只准寫的檔 | 出口閘門（主控親跑） |
|---|---|---|
| Dev-SDD | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/recovery_hint.py`＋其測試；`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`；`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/skills/{sdd-gate,sdd-review,rtm-generate}/SKILL.md`＋父層鏡像（`sync_exposed_skills.py --write`）；`AISDLC_SDD/scripts/sync_exposed_skills.py`＋`AISDLC_SDD/scripts/tests/test_sync_exposed_skills.py`；`AISDLC_SDD/CLAUDE.md`；`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`；`AISDLC_SDD/AISDLC_SDD_v0.30/releases/CHANGELOG.md`；`AISDLC_SDD/FRAMEWORK_STATUS.md`（重生） | `AISDLC_SDD/scripts/ci-gate.ps1` rc=0；`framework_status_snapshot.py --check`；`sync_exposed_skills.py --check`；`python tools/run_root_unittests.py`（含 recovery_hint ps-lint 鎖）；`git diff` 對 `transition_rules.py`／`formal/` 為空；`git status` 對其他版本目錄為空 |
| Dev-DOC | `AutoClaude/CLAUDE.md`（淨 ≤0）；`AgentConsole/CLAUDE.md`（≤200 行） | `check_loc_budget.py --json`；`pytest tests/contract/test_claude_md_*.py`（cwd `AutoClaude/`）；AgentConsole 行數 |
| 主控 | 根 `.gitignore`；`AutoClaude/.claude/skills`（`--write`）；`ONBOARDING.md`；根 `CLAUDE.md` | 根層全套、`sync_exposed_skills.py --check` |

## §8 零退化矩陣（收尾單人窗口，2026-10-18；數字一律取自主控當回合 tool_result，「他包回報」另標）

| 面 | 載具／來源 | 結果 | 備註 |
|---|---|---|---|
| 根層 unittest（`tools/tests`） | `python tools/run_root_unittests.py`（`AUTOSDD_PARALLEL_TESTS=1`），**最後一次跑在本檔定稿之後**，結果逐字記在收尾 commit 訊息（`git log`） | 收集數 5326（`sync_onboarding_baselines.py --write` 的 `rootunit-baseline-live`） | 守衛鎖逐支：router r158 OK、hooks liveness OK、context_budget_guard OK、doc_loc_baseline_freshness OK、platform_utils_dedup OK、subprocess_encoding_hygiene OK、幽靈路徑鎖 OK、帳本 crossref rc=0（未結 0） |
| AutoClaude 全套 | 乾淨 venv 載具 `tools/lib/clean_venv_carrier.py`（Windows、`pgextras: absent`、`docker: up`） | `5693 passed / 169 skipped`（ONBOARDING §7 表② Windows 欄同值） | lint-imports 9 kept（d9dc1ff0 列）；`check_loc_budget` total 18625／violations 0（表① live 格）；test_webhook_sender 9 passed |
| AISDLC_SDD ci-gate 三軌 | 同一載具的 `ci-gate.sh` 逐軌計數自證行 | v0.01 `1478`／v0.30 `2149`／scripts `425` passed | test_sdd_env 26 passed；recovery_hint 46 passed（W1 列） |
| AgentConsole Engine Bridge | `python -m pytest -q`（cwd `AgentConsole/engine-bridge`）＋ `ruff check AgentConsole/engine-bridge` | `1003 passed, 24 skipped, 1 warning in 458.75s`；ruff `All checks passed!` | DF-B 只動 Bridge；frontend／backend 本輪未動 ⇒ lint／tsc／gradlew **未觸發（N/A）**，不是隨全套通過 |
| SCG-4 突變鑑別力 | QA `mutate_all.py dfa dfc`（`git archive` 匯出 322e1351／90d911e4） | 他包回報：DF-A 殺 50/50、DF-C 殺 29/29、存活 0 | 一審 12 存活者全轉紅；F-03 拿掉修復 3/3 轉紅 |
| 三鍵 FSM 終態 | QA `show --must-exist` | 他包回報：三鍵皆 RELEASE_READY；框架真狀態檔 `FSM-STATE-AISDLC_SDD.yaml` 未動（2026-07-16、2417 bytes） | RELEASE 轉態在 push＋雲端綠之後由主控做（`transition_rules.py:69` 唯一出邊） |

## §9 審查閉環・歸格・休眠重評

### 9.1 審查閉環（SCG-4 獨立審查 × 三路 dogfood）
- DF-B（hooks-ON headless Sonnet）一審 PASS → RELEASE_READY。DF-A（Bridge 委派＋真 haiku）／DF-C（hooks-ON headless Sonnet）一審 FAIL（各一筆 P2：測試鑑別力）→ 兩個只動測試檔的修復棒（`322e1351`）→ 二審 PASS（殺 50/50、29/29）；P3 F-03／F-05 同輪修（`1c802e92`）並經二審複核。QA 新登 P4 三筆（F-10／F-11 docstring 措辭、F-12 嚴格編碼理論洞）：成品已過二審、`RELEASE_READY` 唯一出邊是 `RELEASE` ⇒ **登記不修**，留證據檔 §9；DEF-AC-038（Bridge StepTracker 被日誌遮罩漏配）依 115 慣例住證據檔 §4。
- 審查形態本身的驗證：QA 以 `git archive` 匯出的 commit 量突變（不量工作樹）——第一次在工作樹量到主控同時在改 `sdd_env.py` 而作廢，是「審查期間主控不動工作樹」（鐵律七檢查表 3）的真實違例，本輪以 QA 重量而不是放過收場。

### 9.2 問題 3 歸格：「AutoClaude、AgentConsole 等模組（含本專案）是否可以完美利用 AISDLC_SDD 流程進行開發？」
- **答：是（範圍＝Windows／Sonnet 實作＋haiku 委派／單機；Unit 類 AT）**。判準 C1～C7（§2）在 W1 修齊缺口後全部成立，三路 dogfood 各自走完 Stage-1／Stage-2 凍結（digest 綁內容）→ 談判閘 → IMPLEMENTATION（hooks deny 守規格檔）→ SCG-4 獨立審查 → RTM 100% → RELEASE_READY，三個鍵的狀態檔各住自家 `build/reports/fsm`（`.gitignore` 已收）、框架真狀態檔零變。
- 「完美」的誠實劃界（不是本輪沒做完，是結構上的邊界）：(1) Java／TS 面走 session-only（AT 由 `gradlew test --tests`／`vitest run -t` 自跑、逐字貼證據，D-116 裁決）；(2) 委派徑的 evaluator 白名單不擴（D-116）；(3) 一個 hooks-ON 視窗同時只綁一個功能（規格檔 deny 看路徑子字串）；(4) G-116-17 的 PreToolUse 半格待掌舵者本人套上（分類器 Self-Modification）。
- 問題 1／2 上輪已答、本輪不重答，可從提示詞拿掉；問題 3 本輪答畢，下輪提示詞亦可拿掉。

### 9.3 休眠重評（範本〈🏁 終止條件・休眠・再開〉T1～T4）
- T1（掌舵者明示新需求）＝本輪的問題 3，已消化；T2～T4 本輪結束時無一成立 ⇒ **軌道① 回休眠**：不開 117、不產四件套，直接做產品工作；掌舵者可隨時以 T1 推翻。
- 下一個會自然觸發的事件不是迭代輪而是產品工作：用 BRIDGE §8 的 SOP 開下一個功能鍵（`python AISDLC_SDD/scripts/sdd_env.py --sub <sub> --slug <功能> --shell powershell`）。

### 9.4 收尾清單（本檔定稿時的實況）
- 已做：`%TEMP%\e2e` 刪除、Docker 懸空卷 49 個與 `aisdlc_*` 卷清空（`docker volume ls` 現查 0 筆 aisdlc）、scratchpad 於 push 後刪除、記憶檔更新。
- 待掌舵者：`D:\w5e2e`（工具層受保護路徑擋下兩次，不繞過；`rmdir /s /q D:\w5e2e`）；根 `.claude/settings.json` 第 60 行 PreToolUse matcher 加 `PowerShell`（`/permissions`→Recently denied→`r`），之後帳本補一列 `fixed@`（編號屆時取現存最大號＋1；本輪不先立號，立了就是未結列、撞淨額棘輪）、根 CLAUDE.md 守衛總表列改回兩格齊。
