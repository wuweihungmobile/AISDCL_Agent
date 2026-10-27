# Console「每頁說明」（Page Help）需求規格 v0.3

**狀態**：v0.3 草案（SA；二審 PASS 後改字，待凍結與 §13.2 開放問題）。**立案**：掌舵者 2026-10-27 原文「請將 Console UI 的所有頁面，加入類似議題中心／狀態說明的功能，以淺顯易懂的角度，說明當下頁面的功能、使用說明與每個欄位、狀態的定義。」
**SDD 鍵**：`agentconsole-page-help`（Console 單半；徑②：TypeScript 標的，session 內自跑 `vitest run`、`playwright test` 並逐字貼證據，`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md:310-314`；LATEST 現查見 §12）。
**規格文件**：本檔（Stage-1）＋TCS（Stage-2，`AgentConsole/docs/03_testing/contracts/TCS-PageHelp-<日期>.md`，先例 `TCS-FsmTrail-20261018.md`）。零 API、後端、Bridge，不寫契約檔與 ADR，決策短編於 §9、§13.1。
**定位**：在既有畫面「之上」加一層靜態白話說明；不新增資料來源、不改頁面行為；唯一的新網路請求見 AC-PH-06-3。**變更**：v0.1 初稿；v0.2 一審修訂（F-01～F-15 已修，F-16～F-18 見 §13.3）；v0.3 二審修訂（N-01～N-04、六項 P4 改字）。

---

## 1. 目標與範圍

> 您在任何一頁按頂列的「本頁說明」，就會看到：這頁做什麼、怎麼用、每個欄位與狀態的意思；底部另有收合的「全站共通」，說明每頁頂部與底部都有的連線點、通知與搜尋。

- **本版交付**：見 §3。件數（撰寫時 16 份說明項、19 條路由，§4）是**快照**：姊妹 PRD 會增加路由（D-12），驗收一律由登記表推導、不寫死件數。
- **成功的樣子**（§11）：掌舵者逐頁開說明，不看英文就能說出該頁用途與任一狀態的意思；新增頁面沒寫說明，測試轉紅。
- **名詞**：「說明項」＝一頁的說明內容；「狀態表」＝一組狀態詞（例：專案狀態）的白話釋義，全站每組只寫一份；「畫面字樣」＝畫面上的原字（欄位名、狀態名），說明逐字引用。狀態名分兩種：`label`＝畫面印中文標籤（多數）；`raw`＝畫面直接印原值（例：任務詳情的執行歷史印 `STARTED`）。

## 2. 使用者與場景（掌舵者視角）

ADMIN、OPERATOR、VIEWER 三種角色都看得到、開得了；內容不隨角色而變。

1. **第一次進「議題中心」**，看不懂「觀察中」「待您決定」：按「本頁說明」讀到每欄與每個狀態的白話；詞表取自議題 API 的 `legend`，與頁面既有「狀態說明」同一份資料。
2. **在「專案執行」看到批次「暫停中」**：狀態表寫明那是「已按暫停、等這一步做完」的過渡狀態，通常下一步變「已暫停」（`Architecture.md:883`、契約附錄 A.1）。
3. **開發者新增一頁卻忘了寫說明**：`npx vitest run` 轉紅並指出要補哪個檔（FR-PH-08）。

## 3. 範圍與不做什麼

**做**：頂列單一「本頁說明」鈕；共用對話框（四段：這頁做什麼、怎麼用、欄位說明、狀態說明，另加收合的「全站共通」，Q7）；每頁說明項、全部狀態表與畫面私有字樣（§4）的白話釋義；路由、導覽、狀態鍵三道雙向鎖；白話機械檢查；無障礙與窄螢幕。

**不做**（本版）：登入頁 `/login`（未登入頂列不顯示動作）；即時數字（唯一例外是議題中心詞表，來自既有 API）；50 個系統參數逐鍵說明（每鍵說明由 API 回傳，`components/domain/settings/labels.ts:1-6`；只講一列的結構、六個分類、兩種標籤）；FSM 原始狀態名**全部**逐一說明（只解釋據以決策的五個，Q6）；頂列、底部、導覽各自的說明鈕；「我的專案」圓點（只有顏色）逐色說明；自動彈出、導覽教學、多語系、說明內搜尋、角色專屬內容、後台編輯（內容住程式碼庫、經 PR 修改）、全域快捷鍵；改議題中心既有「狀態說明」鈕與其測試（Q4）；改 API、後端、Bridge、資料庫、契約檔、導覽登記表。

## 4. 逐頁盤點：欄位與狀態的真相源

「欄位來源」＝作者查欄位意思該看的地方；「狀態表」＝該頁要列的狀態表 id（§8.2），〔〕內是畫面上出現該狀態的座標（F-02 逐頁現查）。座標簡寫：`契約`＝`AgentConsole/docs/02_architecture/API_Contract_P3-6.md`；`Arch`、`SI契約`、`IC契約`＝同目錄的 `Architecture.md`、`API_Contract_SelfImproving_P1b.md`、`API_Contract_IssueCenter.md`；`PRD`＝`docs/01_requirements/Agent_ConsoleUI_PRD.md`；元件路徑相對 `AgentConsole/frontend/components/domain/`（`components/`、`lib/`、`hooks/` 開頭者相對 `AgentConsole/frontend/`）。現查日 2026-10-27、HEAD `c92f8bed`。

| 說明 id | 路由樣板 | 欄位來源 | 狀態表〔畫面出處〕 |
|---|---|---|---|
| `dashboard` | `/` | KPI 算法 `DashboardView.tsx:81-92、115-139`；契約 G-06～G-10 `契約:2739-2743` | `projectStatus`〔`DashboardView.tsx:168`、`components/charts/ProjectStatusChart.tsx:13`〕 |
| `projects` | `/projects` | 卡片 `ProjectCard.tsx:52-63`；`PRD:380-396`；DTO `Arch:988-1005` | `projectStatus`〔`ProjectCard.tsx:35`、`ProjectsView.tsx:122`〕 |
| `project-detail` | `/projects/[projectId]` | 同上；SDD 治理區 `契約:2771-2796` | `projectStatus`〔`ProjectDetailView.tsx:57`〕、`goalStatus`〔`GoalListCard.tsx:24`〕、`sddPhase`〔`sdd/SddPhaseProgress.tsx:19`〕、`sddFsmState`〔`sdd/SddGovernanceCard.tsx:61-62、69`〕 |
| `goals` | `/projects/[projectId]/goals` | Goal DTO `Arch:1007-1021` | `goalStatus`〔`GoalListCard.tsx:24`〕 |
| `goal-detail` | `…/goals/[goalId]` | 同上；`PRD:469` | `goalStatus`〔`GoalDetailView.tsx:59`〕、`taskStatus`〔`TaskListCard.tsx:27`〕 |
| `tasks` | `…/goals/[goalId]/tasks` | Task DTO `Arch:1023-1042` | `taskStatus`〔`TaskListCard.tsx:27`〕 |
| `task-detail` | `…/tasks/[taskId]` | 同上 | `taskStatus`〔`TaskDetailView.tsx:75`〕、`stepStatus`＝**原值**〔`TaskDetailView.tsx:150`〕 |
| `project-form` | `/projects/new`、`/projects/[projectId]/edit` | 欄位 `entity/EntityForms.tsx:181-204`；`PRD:380-396` | （無） |
| `goal-form` | `…/goals/new`、`…/goals/[goalId]/edit` | 欄位 `EntityForms.tsx:219-288`；`Arch:1007-1021` | `goalStatus`〔`EntityForms.tsx:24、236`：前置依賴挑選器每列帶狀態〕 |
| `task-form` | `…/tasks/new`、`…/tasks/[taskId]/edit` | 欄位 `EntityForms.tsx:331-342`；`Arch:1023-1042` | （無） |
| `execute` | `/projects/[projectId]/execute` | 契約 §4.2 E-01～E-22 `契約:2658-2683`；§4.7.2 `契約:2798-2817` | `runStatus`、`runTransition`〔`execute/ProgressCard.tsx:44`、`execute/parts.tsx:147、217`〕、`reviewKind`、`reviewDecision`〔`execute/ReviewCard.tsx:124`〕、`taskStatus`〔`execute/ScopeTree.tsx:109`〕（**不含** `stepStatus`） |
| `monitor` | `/projects/[projectId]/monitor` | 契約 §4.3 M-01～M-21 `契約:2685-2709` | `runStatus`、`runTransition`〔`monitor/AgentCard.tsx:63`、`CompareCard.tsx:20、32`〕、`stepStatus`＝中文〔`lib/domain/metrics.ts:241、243`〕、`alertSeverity`、`alertRule`〔`monitor/AlertsCard.tsx:21、29、51`〕、`sddPhase`、`sddFsmState`〔`monitor/SddEngineCard.tsx:121-123`〕 |
| `import` | `/import` | 契約 §4.1 I-01～I-18 `契約:2635-2656` | `importStatus`〔`import/StructureCard.tsx:135`、`HistoryPanel.tsx:39-41、76`〕、`gateName`〔`import/parts.tsx:124`〕 |
| `settings` | `/settings` | 契約 §4.4 S-01～S-14 `契約:2711-2728`；每鍵說明取自 API，不重抄 | （無；兩種標籤 `settings/SettingRow.tsx:17-20` 寫在欄位表） |
| `self-improving` | `/self-improving` | `SI契約:146-174`；橫幅九鍵 `lib/domain/si.ts:60` | `obsClass`、`propClass`〔`lib/domain/si.ts:206、212`〕、`propState`＝**原值**〔`si/SiProposalsPanel.tsx:190`〕 |
| `issues` | `/issues` | `IC契約:46-66`；表頭八欄字面值 `issues/IssueTable.tsx:22` | `legend`（API） |
| 全站共通（無路由；`lib/help/common.ts`） | 每個對話框底部 | `components/layout/` 下：`TopRegion.tsx` 公告列 `:53-76`、搜尋 `:116-132`、最近專案 `:134-141`、通知與待審批 `:146-156`；`BottomRegion.tsx:38-41`；`ToolsRegion.tsx:82-99` | `serviceState`〔`TopRegion.tsx:59-60`、`BottomRegion.tsx:38-39`〕；「我的專案」圓點只有顏色〔`ToolsRegion.tsx:94`，顏色＝專案狀態〕 |

合計 19 條路由、16 個說明 id（另有無路由的「全站共通」）；`app/` 共 20 個 `page.tsx` 扣 `/login`（指令見 §12）。

**畫面私有字樣**（無匯出常數、不進狀態表，寫進該頁欄位表；F-01）：`execute`——SSE 串流點六態（`execute/parts.tsx:35-42、54-58`；型別 `lib/api/sse.ts:48`）、引擎能力晶片兩枚各三態（`parts.tsx:159-188`；字典 `lib/domain/status.ts:201-237`）、自治等級名稱與一句說明（`status.ts:171-199`、`execute/ControlCard.tsx:71、91`）；`monitor`——Agent 連線燈六態（`monitor/AgentCard.tsx:39-44`）、任務狀態分佈四條 bar 的分組（`lib/domain/metrics.ts:138-148`）；`project-detail`、`monitor`——階段進度步驟態已過／目前／未到與標籤觀測中、委派 AutoClaude 執行中（`sdd/SddPhaseProgress.tsx:16、39、44`）。自治等級也見於 `projects`（`ProjectCard.tsx:56`）、`monitor`（`monitor/CompareCard.tsx:22`）、`import`（`import/SourceCard.tsx:340-344`）、`project-form`（`EntityForms.tsx:204`），釋義共用（`SHARED`）。

**查證發現**：
1. **`legend` 只存在於議題中心**（指令見 §12）。自我進化頁沒有 API 詞表，提案狀態在畫面顯示英文原值（`si/SiProposalsPanel.tsx:190`），所以走「原值＋鍵鎖」、不走 API。
2. **兩份提案狀態表不一致**：Console 的 `PROP_STATUS_BY_STATE`（`si.ts:179-191`）11 鍵含 `retired`；根層 `tools/lib/selfimproving/events.py:38-39` 的 `PROP_STATES` 10 鍵、無 `retired`，`retired` 在根層只是**觀察**的處置值（`rows.py:25`、`issuemap.py:115`）。以 Console 表為準（它決定畫面），差異以一列 OBS 登記、不在本功能修（D-8）。
3. **頁標題列寫法不一**：8 個 view 檔用 `PageTitle`（`PageHeader.tsx:21`，14 條路由），5 個手刻（`IssuesView.tsx:355`、`SiView.tsx:60`、`ProjectDetailView.tsx:67`、`GoalDetailView.tsx:70`、`TaskDetailView.tsx:95`）。逐頁加鈕＝改 6 個檔、寫法各異、既有 view 測試會渲染標題列、之後每個新頁也得記得加；所以預設走頂列單一入口（Q1）。
4. `lib/**` 沒有 import `components/**` 的先例（只命中測試檔 `lib/domain/issues.test.ts:9`）；狀態名要引用 `components/domain/import/gateErrors.ts` 的 `GATE_LABEL`，所以「名稱解析」放 `components/domain/help/`，`lib/help/` 只放純文字。
5. `ParsePath`（`import/StructureCard.tsx:33`）與 `ImportSourceType`（`import/SourceCard.tsx:44`）標籤表未匯出：不進狀態表，改在匯入頁欄位表說明（不為上鎖而改既有檔）。
6. **`stepStatus` 的位置與名稱模式**（F-02）：`task-detail` 的執行歷史印原值 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING`（`TaskDetailView.tsx:150`，不經 `STEP_STATUS`）；中文標籤只在 `monitor` 的事件時間軸（`STEP_STATUS` 的非測試消費者只有 `lib/domain/metrics.ts:8、241、243`，由 `monitor/TimelineCard.tsx:32` 呼叫）；`execute` 不使用。`goal-form` 的挑選器每列帶目標狀態（`EntityForms.tsx:236`），不屬無狀態頁。
7. **FSM 原始狀態會被原樣印出**（Q6）：「目前狀態」格印任何狀態（`sdd/SddGovernanceCard.tsx:69`、`monitor/SddEngineCard.tsx:121-123`，阻塞橫幅 `sdd/SddPhaseProgress.tsx:26`，皆 `sddText(fsm.currentState)`）；程式碼點名、據以決策的只有五個：`HUMAN_PENDING`（`SddGovernanceCard.tsx:61-62`）、`SPEC_FROZEN`（`sdd/SddFreezeDialog.tsx:36、87`）、`ESCALATION`／`ESCALATION_FINAL`（`lib/domain/sdd.ts:219`）、`AUTOCLAUDE_DELEGATED`（`sdd.ts:204`）。本版只解釋這五個，其餘請看旁邊「階段」的中文（`SddPhaseProgress.tsx:33-36`）。

## 5. 功能需求（FR）與驗收準則（AC）

每條 AC 為 Given／When／Then，可由一支測試判定；元件行為以 vitest（jsdom）驗，版面與視窗尺寸以 Playwright mock 驗（jsdom 不評估 CSS，沿 `API_Contract_SelfImproving_P1b.md:270`）。

| AC | 內容 |
|---|---|
| **FR-PH-01** | **說明鈕：全站一顆、同一元件、同一 `data-testid`** |
| `AC-PH-01-1` | Given 已登入且路由有說明項 When 渲染 `RootLayout` Then `[data-region="top"]` 內恰有一個 `data-testid="page-help-open"` 的 `<button>`，可見文字「本頁說明」，與通知鈴、待審批佇列鈕同在右側群組；`[data-region="content"]` 內沒有它 |
| `AC-PH-01-2` | Given 路由為 `/login`、未登入、或路徑無對應說明項（例 `/unknown`）When 渲染 Then 不渲染該鈕 |
| `AC-PH-01-3` | Given VIEWER、OPERATOR、ADMIN 各一 When 開任一說明 Then 都看得到、開得了、內容相同 |
| `AC-PH-01-4` | Given 說明已開啟 When 路由改變（瀏覽器返回）Then 對話框關閉；再開啟的是新路由的說明，不殘留舊頁內容 |
| `AC-PH-01-5` | Given 該鈕 When 取可存取名稱 Then 含可見文字「本頁說明」（WCAG 2.5.3；沿 `layout.test.tsx:173-198`）；<768 文字改 `max-md:sr-only`、名稱不變 |
| **FR-PH-02** | **對話框內容與純文字渲染** |
| `AC-PH-02-1` | Given 任一說明項 When 開啟 Then `role=dialog` 名稱為「<`title`>・本頁說明」（固定頁名，§8.1），內有四個 `h3` 依序為「這頁做什麼」「怎麼用」「欄位說明」「狀態說明」，其後一個預設收合的 `<details>`（`data-testid="page-help-common"`，摘要「全站共通」）；`states` 為空者「狀態說明」段顯示固定一句「這一頁沒有會變動的狀態。」 |
| `AC-PH-02-2` | Given 一個說明項 When 讀兩張表 Then 欄位表三欄（欄位、意思、資料來源）、狀態表三欄（狀態〔`raw` 模式標「畫面上的原值」，AC-PH-04-3〕、意思、通常的下一步）；列數與順序＝登記內容；每表有 `aria-label` 與 `th scope="col"` |
| `AC-PH-02-3` | Given 登記文字含 `<script>`、`**`、反引號 When 渲染 Then 以字面文字顯示；`components/domain/help/**`、`lib/help/**` 非測試檔靜態掃描無 `dangerouslySetInnerHTML` 與 Markdown 渲染器 import（含負控） |
| `AC-PH-02-4` | Given 把每段登記文字（含全站共通）換成互不相同的哨兵字串、狀態名稱來源換成哨兵 When 渲染 Then 對話框文字只含哨兵、段標題、「全站共通」摘要、欄與表標題、固定空狀態句（沒有第二份寫死的說明） |
| `AC-PH-02-5` | Given 一頁有多個狀態表 When 開啟 Then 每表有小標題（取自 `stateSources`）與自己的表，順序＝登記順序 |
| `AC-PH-02-6` | Given 展開「全站共通」When 讀內容 Then 欄位表涵蓋 §4 末列各項、狀態表為 `serviceState`（名稱取自 `SERVICE_LABEL`）；任兩頁該段文字相同（只寫一份） |
| **FR-PH-03** | **登記表與路由對應** |
| `AC-PH-03-1` | Given `app/**/page.tsx` 的路由樣板（沿 `lib/nav/registry.test.ts:46-68` 的 walker，括號群組不進網址）減排除名單 `["/login"]` When 與 `HELP_ROUTES` 的鍵比對 Then 兩集合相等；缺（新頁沒說明）與多都紅，訊息含修法「在 `lib/help/<id>.ts` 新增並於 `registry.ts` 登記」 |
| `AC-PH-03-2` | Given `NAV_REGISTRY` 每個 `enabled` 項、其 `href` 的兩種解析（`currentProjectId` 為 null 與 `"p1"`）When 經 `helpForPath` Then 皆解析到說明項 |
| `AC-PH-03-3` | Given 代表路徑 When 解析 Then 靜態段優先於動態段、每路徑恰一個說明 id：`/`→`dashboard`、`/projects/new`→`project-form`、`/projects/p1`→`project-detail`、`/projects/p1/edit`→`project-form`、`/projects/p1/goals/g1/tasks/t1/edit`→`task-form`、`/projects/p1/`→`project-detail`；`""`、`/unknown`、`/projects-x`、`/login`→null |
| `AC-PH-03-4` | Given `lib/help/` When 讀目錄 Then 扣掉 `types`、`states`、`registry`、`lint`、`common` 與測試檔，頁檔 id 集合＝`HELP_PAGES` 的鍵∪`PENDING_HELP_PAGES`（兩者互斥；待寫頁的頁檔可為佔位，內容檢查豁免到移出 `PENDING_HELP_PAGES`）；每檔 `id` 欄等於檔名 |
| `AC-PH-03-5` | Given 每個已寫的說明項（不含 `PENDING_HELP_PAGES`）Then `purpose` 1～3 句、`steps` 2～8 步、`fields` ≥ 1、`sourceFiles` ≥ 1 且路徑存在；`states` 為空者必在 `NO_STATE_PAGES`（撰寫時 `project-form`、`task-form`、`settings`）；表單頁欄位涵蓋度由 AC-PH-05-7 判 |
| `AC-PH-03-6` | Given 分輪交付 When 最後一輪出口 Then `PENDING_HELP_PAGES` 為空（中間輪只准縮小；非空時其路由不渲染鈕）；路由鎖在所有輪次都成立。PageHelp 收輪後才落地的姊妹案可暫時重填 `PENDING_HELP_PAGES`，棘輪上限隨其同 commit 登記（D-12） |
| **FR-PH-04** | **狀態詞不自持；鍵集合雙向鎖** |
| `AC-PH-04-1` | Given 全部狀態表各一 When 比對登記列的鍵集合與 `STATE_SOURCES[id].keys`（執行期現讀既有常數；`sddFsmState` 例外：子字串弱鎖，§8.2 備註 2）Then 雙向相等；常數新增狀態而說明沒補、說明多出不存在的狀態，都紅 |
| `AC-PH-04-2` | Given `StateRow` 只有 `meaning`、`next`（**沒有** `label`、`name`），且有後端 enum 型別的十張表（專案、目標、任務、匯入、批次、審核種類、審核決定、步驟、告警規則、有界閘）以 `Record<該 enum, StateRow>` 宣告；`serviceState` 另以字面值聯集宣告、由 `stateKeys.test.ts` 型別等式斷言＝`ServiceState`（`hooks/useServiceStatus.ts:7`；`lib/**` 無 import `hooks/**` 先例）When `npx tsc --noEmit` Then enum 經 `schema*.d.ts` 重產而新增值時型別即紅（第一道鎖，AC-PH-04-1 是第二道）；加 `label` 欄的 `@ts-expect-error` 樣本證明型別真的擋 |
| `AC-PH-04-3` | Given 任一狀態表在某頁渲染 When 讀「狀態」欄 Then 逐列等於該頁名稱模式：`label`（預設）＝`STATE_SOURCES[id].labelOf(key)`；`raw`＝鍵本身（畫面印原值者：`task-detail` 的 `stepStatus`、`propState`、`sddFsmState`），欄標題改「畫面上的原值」；無 `labelOf` 的表只准 `raw` |
| `AC-PH-04-4` | Given 議題中心說明 When 開啟 Then 狀態、結果、來源、嚴重度四群與 `updatedAtNote` 逐字取自 `GET /api/v1/issues?limit=1` 的 `legend`；靜態鎖**只掃** `lib/help/issues.ts` 與 `components/domain/help/**` 的非測試檔（含註解、子字串比對，語意同 `issues.static.test.ts:88-92`），各檔含不到 4 個不同的議題狀態名（現讀黃金檔 `tests/fixtures/si/A.camel.json`：候選、待您決定、待解、進行中、觀察中、延後、已完成；含負控）。不掃 `states.ts` 與其他頁檔：「進行中」「已完成」「延後」是一般詞，會誤紅；TCS 階段先對草稿預跑，真紅就改寫文字、不放寬門檻 |
| `AC-PH-04-5` | Given 該請求回 503、504 或網路失敗 When 開啟議題中心說明 Then 前三段照常，狀態段顯示「狀態詞表暫時取不到：<原因>」（取 `siErrorParts`，`lib/domain/si.ts:400`）；載入中顯示「狀態詞表載入中…」；不顯示空表與過期資料；每次開啟都重取（沿 `SI_QUERY_OPTIONS`：不重試、不留快取，`lib/api/queries.ts:998`） |
| `AC-PH-04-6` | Given 自我進化說明 When 開啟 Then `propState` 名稱為畫面原值、列鍵集合＝`PROP_STATE_KEYS`；`obsClass`、`propClass` 名稱取自 `OBS_STATUS_OPTIONS`、`PROPOSAL_STATUS_OPTIONS` 去掉「全部」後的標籤 |
| `AC-PH-04-7` | Given `reviewDecision` 的每個決定鍵 When 對 `REVIEW_KIND` 每個種類呼叫 `reviewConsequence`（`execute/reviewHelp.ts:28`）Then 每個決定至少在一個種類回傳非預設句（「依後端規則處理。」，`:29`）；決定新增而後果表沒補＝紅。該表每列 `next` 為「依審核項種類而定」類固定句（§8.2 備註 3） |
| **FR-PH-05** | **白話與內容品質（機械可驗的部分）** |
| `AC-PH-05-1` | Given 全部說明文字（`purpose`、`steps`、欄位 `meaning`、`sourceNote`、狀態 `meaning`／`next`，含全站共通）When 以「。！？；」與換行切句 Then 每句 ≤ 60 個 code point；`purpose` ≤ 3 句；`steps` 每步 1 句；欄位與狀態 `meaning` ≤ 2 句、`next` 1 句 |
| `AC-PH-05-2` | Given 同上文字 When 偵測英文詞（連續 ASCII 字母、長度 ≥ 2；先剔除議題 ID 形態 `OBS-SI-NNN`、`PROP-SI-NNN`、`DEF-N-N`）Then 每個詞都在 §8.3 白名單（整詞、不分大小寫）；欄位名欄與狀態名欄是畫面字樣的逐字引用，不受此限 |
| `AC-PH-05-3` | Given 同上文字 Then 不含 emoji（`\p{Extended_Pictographic}`）、`#` 後接 ≥ 3 位十六進位字元、Markdown 記號（`**`、反引號、`](`）、HTML 標籤、`://`、磁碟機或家目錄路徑（`C:\`、`/Users/`、`/home/`）、連續 ≥ 3 位半形數字；`tests/design-rules.test.ts:53-62` 同樣掃 `lib/**`，本條提早給明確訊息 |
| `AC-PH-05-4` | Given 每個欄位列 Then `source` 屬 §8.1 的六類之一；`sourceNote` 選填且 ≤ 30 個 code point |
| `AC-PH-05-5` | Given 每個欄位名（≥ 3 個 code point，更短者免掃、由 SCG-4 人讀；同頁須互異）When 以 TypeScript AST 取**該頁 `sourceFiles`**（相對 `AgentConsole/frontend/` 的檔案或 `dir/**`，扣測試檔，每頁展開後 ≤ 30 個〔現況最大 `components/domain/execute/**` 為 12 個〕、拒絕 `components/**` 這類頂層萬用路徑，上限由 TCS 實測定案；全站共通用 `components/layout/**`、`hooks/useServiceStatus.ts`）的字串字面值、樣板字串片段與 JSX 文字（不含註解；沿 `issues.static.test.ts:51-58、202-220`）Then 至少一處含它，改名或刪欄位而說明沒改＝紅。縮到該頁是因為全庫掃描時短常用詞幾乎必中、鎖會恆真。**劃界**：`sourceFiles` 由作者宣告、SCG-4 人讀把關；只擋改名與刪除，擋不到非表單頁新增欄位與語意改變（R-1、§11 真機） |
| `AC-PH-05-6` | Given lint 純函式 When 餵負控樣本 Then 61 字的句子、白名單外英文詞（如 `Foo`）、emoji、`#abc123`、Markdown 記號、`://`、4 位數字各回非空，合規樣本回空 |
| `AC-PH-05-7` | Given `entity/EntityForms.tsx` When 以 AST 取 `ProjectForm`、`GoalForm`（含 `DependsOnField`）、`TaskForm` 內 `<Field>`、`<MarkdownField>` 的 `label` 字串屬性 Then 對應說明項的欄位名集合 ⊇ 該清單（撰寫時 5／4／6 個，`EntityForms.tsx:147、215、248、302`）；表單新增欄位而說明沒補＝紅 |
| **FR-PH-06** | **零侵入與單一真相** |
| `AC-PH-06-1` | （審查核對項）Given 全部變更 When `git diff --name-only <Stage-2 凍結 commit>..HEAD` Then 只含 §9 表列路徑；不含 `AgentConsole/backend/**`、`AgentConsole/engine-bridge/**`、`lib/api/` 的 `endpoints`／`queries`／`reasons`／`schema*.d.ts`、`openapi-p3-6.yaml`、`API_Contract_*.md`、`lib/nav/registry.ts`、`.github/**`、`tools/**`、`.claude/**`；`Architecture.md` 只准主控在發布階段改 §3、§5.2、§5.4 |
| `AC-PH-06-2` | Given 功能完成 When 跑既有 vitest Then 除 §9 所列者外原樣通過；§9「真跑清單」三個會渲染頂列的既有測試檔逐檔貼輸出；既有測試檔的 diff 只含 §9 所列檔、不刪斷言 |
| `AC-PH-06-3` | Given Playwright `installApiMock` 的 `calls` 紀錄 When 在每條路由（`Object.keys(HELP_ROUTES)`）各點一次「本頁說明」Then 點擊到對話框出現之間新增的請求，議題中心恰一個 `GET /api/v1/issues?limit=1`，其餘路由零個（頁面自身的輪詢以網址白名單排除，細節由 TCS 定）；該請求唯讀、VIEWER 以上（`IC契約:138`） |
| `AC-PH-06-4` | Given Stage-2 凍結 commit 與完成後各一次 `npm run build`（`AgentConsole/frontend/`）When 讀 `.next/diagnostics/route-bundle-stats.json`（Next 16.4.3 寫出，欄位 `route`、`firstLoadUncompressedJsBytes`；`node_modules/next/dist/build/route-bundle-stats.js:92、132、148-152`）Then 每條路由的 `firstLoadUncompressedJsBytes` 增量 ≤ 100,000 位元組（約 30 KB gzip，僅供參考）；超過就改成按下按鈕才 `import()` 說明內容，再量 |
| **FR-PH-07** | **無障礙與響應式** |
| `AC-PH-07-1` | Given 焦點在 `page-help-open` When 按 Enter 或空白鍵 Then 對話框開啟、焦點進入對話框；以 Esc 與右上關閉鈕各關一次，焦點都回到該鈕（共用層 `components/ui/dialog.tsx:23-29、65-73`） |
| `AC-PH-07-2` | Given 對話框實作 Then 建於 `DialogContent`，不自刻、不傳會 `preventDefault` 的 `onCloseAutoFocus`；內容可捲（沿用 `max-h-[88vh]`）、寬度 `max-w-[calc(100%-48px)]` |
| `AC-PH-07-3` | Given 視窗 390×844 When 開任一說明 Then 按鈕可見可點、對話框不超出視窗、`scrollWidth ≤ clientWidth`，兩張表改逐列堆疊（Playwright） |
| `AC-PH-07-4` | Given 說明開啟於 `/issues`、`/projects/p1`、`/settings` × 視窗 1440×900 與 390×844 When 跑 axe（WCAG 2.0／2.1 A／AA，`tests/e2e/a11y.ts:94-97`）Then 零違規（含 `color-contrast`、`label-content-name-mismatch`） |
| `AC-PH-07-5` | Given 新檔 Then 通過 `tests/design-rules.test.ts`（只用 token、Lucide 圖示、無陰影漸層、無 `outline-none`）；按鈕圖示用 Lucide 的 `BookOpen`（已查：安裝版 1.57.0 有，`node_modules/lucide-react/dist/lucide-react.d.ts:2772`），**不用**公告列靜態「幫助中心」已用的 `CircleHelp`（`TopRegion.tsx:69`，R-5） |
| **FR-PH-08** | **接入規範：新頁面必帶說明** |
| `AC-PH-08-1` | Given 開發者新增 `app/**/page.tsx` 而沒登記 When 跑 `npx vitest run` Then AC-PH-03-1 轉紅並指出修法 |
| `AC-PH-08-2` | Given 新增 `NAV_REGISTRY` 項而其 `href` 無說明 When 跑 vitest Then AC-PH-03-2 轉紅 |
| `AC-PH-08-3` | （審查核對項）`Architecture.md` §5.4 接入檢查表增一格「說明登記表一列」，與 §3 目錄表兩列、§5.2 Top 列同一個 commit 由主控收齊（§9） |

## 6. 非功能需求

- **安全**：說明一律以 React 文字節點渲染，不經 HTML 或 Markdown；無新端點、無寫入；議題詞表請求沿既有 JWT 與 VIEWER 以上授權；說明不得含機密、帳號、絕對路徑（AC-PH-05-3；`AgentConsole/CLAUDE.md:138`）。
- **效能與無障礙**：首屏 JS 增量見 AC-PH-06-4；開啟對話框 ≤ 100 ms、議題詞表請求 ≤ 2 秒（同既有 `export` 量級，`Issue_Center_PRD.md:416`）**無自動化量測**（jsdom 計時不可靠），由真機 V1 目測（§13.3）。無障礙見 FR-PH-07。
- **跨平台**：測試以 `path.join` 取路徑、LF、UTF-8；Playwright mock 版不需後端。CI 的 frontend job 只在 `ubuntu-latest`（`.github/workflows/agentconsole-ci.yml:117-119`），Windows 無 CI 證據，所以 §11 要求在 Windows 開發機自跑 vitest 與 tsc 並貼輸出。
- **零侵入與相容**：只加前端檔與測試；既有檔只有三處加法（`TopRegion.tsx`、`lib/domain/si.ts`、`vitest.config.mts`，§9）；不改 API、後端、Bridge、契約、導覽登記表（項數隨他案增減：現八項，`registry.ts:36-95`；姊妹 PRD 預計加第九項，D-12）；`app/layout.tsx` 的四區塊組裝（`layout.test.tsx:43-75`）、議題中心「狀態說明」鈕與其測試（`IssuesView.tsx:362-364`）不變；機械核對＝AC-PH-06-1；說明一律繁體中文，專有名詞限 §8.3 白名單。

## 7. 畫面

**頂列**（`TopRegion.tsx:145-157` 右側群組末端，在通知鈴與待審批佇列鈕之後；≥768）：

- 白底＋主色字（`bg-white`、`text-wg-primary`、`font-medium`、`rounded-full`，圖示 `BookOpen`），高度比照相鄰圓形鈕。**不得用半透明底上的白字**：約 3.5:1，低於 4.5:1（手算僅供參考，同型教訓見 `layout.test.tsx:185`）；驗收以 AC-PH-07-4 的 axe 為準。
- <768：文字隱藏（`max-md:sr-only`）、只剩圖示；頂列本就 `max-md:flex-wrap`（`TopRegion.tsx:99`），不得造成橫向捲動。只在 `showTools` 分支內渲染（`TopRegion.tsx:38、113`）：登入頁與未登入自然不出現。
- **與公告列「幫助中心」的區別**：它是不可點的靜態字樣（契約 G-G5，`契約:2764`；`TopRegion.tsx:68-71`）；本鈕名稱與圖示都不同，「全站共通」段也寫明公告列字樣目前不能點。

**對話框**（`DialogContent`，標題「<固定頁名>・本頁說明」）由上而下：這頁做什麼（1～3 句）、怎麼用（編號步驟，2～8 步）、欄位說明（欄位｜意思｜資料來源）、狀態說明（每張狀態表一個小標題與一張表：狀態｜意思｜通常的下一步；議題中心的四群詞表取自 API，載入中／失敗各一句固定文字，AC-PH-04-5）、預設收合的「全站共通」。

- 四段永遠都在；無狀態的頁「狀態說明」只有一句固定文字。<768 兩張表改逐列堆疊（欄名作列內小標）。
- 測試用 id：`page-help-open`（鈕）、`page-help-dialog`、`page-help-purpose｜steps｜fields｜states`、`page-help-common`、`page-help-states-<表 id>`；議題詞表群 `page-help-legend-statuses｜results｜sources｜severities｜note`。

## 8. 說明項格式與白話規則

### 8.1 型別（`lib/help/types.ts`；純文字，不 import 元件）

```ts
export type FieldSource = "您填寫或選擇" | "系統自動產生" | "執行引擎回報" | "自我進化帳本" | "系統參數" | "其他頁面帶入";
export type HelpField = { name: string; meaning: string; source: FieldSource; sourceNote?: string };
export type StateRow = { meaning: string; next: string };        // 刻意沒有 label／name：名稱只取自既有常數表
export type HelpStateGroup = { table: StateTableId; name?: "label" | "raw" } | { legend: "issues" };   // name 預設 "label"
export type PageHelp = { id: HelpId; title: string; purpose: readonly string[]; steps: readonly string[]; fields: readonly HelpField[]; states: readonly HelpStateGroup[]; sourceFiles: readonly string[] };
export type CommonHelp = Pick<PageHelp, "fields" | "states" | "sourceFiles">;   // common.ts 的 HELP_COMMON
// STATE_HELP: Record<StateTableId, Record<string, StateRow>>（lib/help/states.ts；有後端 enum 的表改用 Record<該 enum, StateRow>，AC-PH-04-2）
```

`title`＝固定頁名，不含專案名等動態名稱（`execute`、`monitor` 的頁標題帶專案名：契約 E-01 `契約:2662`、`ExecuteView.tsx:274`、`MonitorView.tsx:140`），故對話框標題恆為「<固定頁名>・本頁說明」。狀態釋義**每張表全站只寫一份**（`lib/help/states.ts`），頁檔只用表 id 引用；`name` 只決定「狀態」欄印什麼（AC-PH-04-3），不改釋義。跨頁共用的欄位釋義（例：自治等級）與全站共通住 `lib/help/common.ts`（`SHARED`、`HELP_COMMON`）。頁檔 `lib/help/<id>.ts` 一頁一檔（例：`projects.ts` 匯出 `projects: PageHelp`，欄位的共用釋義寫 `SHARED.autonomy`，畫面印原值的狀態表寫 `{ table: "stepStatus", name: "raw" }`；定稿由開發棒依 §4 起草、SA 對照審），`registry.ts` 彙總 `HELP_PAGES`、`HELP_ROUTES`（路由樣板→id）、`PENDING_HELP_PAGES`、`NO_STATE_PAGES`、`helpForPath(pathname)`（靜態段優先、去尾斜線）。

### 8.2 狀態表（鍵＝執行期現讀既有常數，名稱＝同一常數；撰寫時 18 張、104 列）

| 表 id | 鍵來源（座標） | 名稱來源 | 列數 |
|---|---|---|---|
| `projectStatus` | `PROJECT_STATUS` `lib/domain/status.ts:43` | `.label` | 6 |
| `goalStatus` | `GOAL_STATUS` `:52` | `.label` | 5 |
| `taskStatus` | `TASK_STATUS` `:60` | `.label` | 11 |
| `stepStatus` | `STEP_STATUS` `:134` | `.label`；`task-detail` 用 `raw` | 4 |
| `importStatus` | `IMPORT_STATUS` `:78` | `.label` | 6 |
| `runStatus` | `RUN_STATUS` `:92` | `.label` | 6 |
| `runTransition` | `BRIDGE_TRANSITION` `:102` | `.label` | 2 |
| `reviewKind` | `REVIEW_KIND` `:115` | `.label` | 4 |
| `reviewDecision` | `REVIEW_DECISION_LABEL` `:123` | 值 | 4 |
| `alertSeverity` | `ALERT_SEVERITY` `:142` | `.label` | 3 |
| `alertRule` | `ALERT_RULE_LABEL` `:160` | 值 | 8 |
| `gateName` | `GATE_LABEL` `components/domain/import/gateErrors.ts:26` | 值 | 6 |
| `sddPhase` | `SDD_PHASE_LABEL` `lib/domain/sdd.ts:162` | 值 | 12 |
| `sddFsmState`（新） | 無單一常數：`SDD_ESCALATION_STATES`（`sdd.ts:219`，兩個）＋三個程式碼字面值（§4 發現 7） | 鍵本身（原值） | 5 |
| `serviceState`（新） | `SERVICE_LABEL` `hooks/useServiceStatus.ts:58` | 值 | 5 |
| `obsClass` | `OBS_STATUS_OPTIONS` 去掉 `id===""` `lib/domain/si.ts:206` | `.label` | 3 |
| `propClass` | `PROPOSAL_STATUS_OPTIONS` 去掉 `id===""` `si.ts:212` | `.label` | 3 |
| `propState` | `PROP_STATE_KEYS`（新匯出，`si.ts:179` 的鍵） | 鍵本身（原值） | 11 |

**備註**：(1) `stepStatus` 在 `monitor` 用 `label`、在 `task-detail` 用 `raw`；`propState`、`sddFsmState` 只有 `raw`。(2) `sddFsmState` 無單一常數可現讀，鎖＝每個鍵須在 `lib/domain/sdd.ts` 或 `components/domain/sdd/**` 的非測試檔中以**子字串**出現（掃字串字面值、樣板字串片段與 JSX 文字，不含註解）；不用等號，因為 `SPEC_FROZEN` 在該目錄只出現在句中（`SddFreezeDialog.tsx:36、87`），等號版一落地就紅。**這是弱鎖**：子字串近乎恆真，只擋鍵字串從程式碼徹底消失，擋不到畫面新增第六個與語意改變（R-1）。(3) `reviewDecision` 的 `next` 寫「依審核項種類而定；按下前確認視窗會先寫明後果」類固定句：後果文字只住既有的 `execute/reviewHelp.ts:7-30`（`ReviewCard.tsx:124` 顯示）、不抄第二份；不直接渲染 `reviewConsequence`（它是「種類×決定」二維，這張表以決定為鍵）；一致性由 AC-PH-04-7 鎖。(4) `propState.retired` 的 `meaning` 寫明「根層目前不會產生這個狀態，畫面為日後預留」（D-8）。(5) `serviceState.idle`（未登入）只在 `/login` 出現、該頁無說明鈕，列保留以維持鍵鎖，無害。

每列 `next` 的依據：專案、目標、任務取 PRD 附錄 B「可轉移至」（`PRD:2070-2105`）；批次與審核取契約附錄 A（`契約:3873-3891`）；匯入取契約 §1.1；連線狀態取 `useServiceStatus.ts` 檔頭與契約 §4.5 G-03；FSM 原始狀態取 `SDD_AUTOCLAUDE_BRIDGE.md` §8；其餘取各常數檔檔頭與契約對應節。`legend` 群（議題中心）不寫釋義，來自 API。

### 8.3 白話規則

- 對「您」說話、用現在式、先說結論、一句一事；句長與列數上限見 AC-PH-05-1。
- 英文詞白名單 v1（31 詞，整詞、不分大小寫；底線與連字號當分隔）：`ID`、`API`、`URL`、`AI`、`Token`、`Agent`、`PRD`、`BRD`、`SDD`、`FSM`、`AISDLC`、`AutoClaude`、`Console`、`Engine`、`Bridge`、`Playbook`、`Markdown`、`PDF`、`DOCX`、`CSV`、`JSON`、`SSE`、`DAG`、`Regex`、`CPU`、`ADMIN`、`OPERATOR`、`VIEWER`、`signoff`、`Run`、`Level`。這些詞畫面本身就出現；增詞須在 PR 說明 WHY 並經 SA／QA 複審。
- **取捨**（F-15）：議題中心已有英文偵測（`lib/domain/issues.ts:322-358`：22 詞黑名單 `ENGLISH_STATE_WORDS`＋議題 ID 形態剔除），但只管「狀態詞」。本功能文字涵蓋全部頁面、詞彙遠多於狀態詞，黑名單擋不住任意英文，所以改採預設拒絕＋白名單；代價是新增英文詞要走複審；議題中心既有檢查不動。
- 欄位名與狀態名是「畫面字樣」，可含英文（例：「執行中 run 數」、提案狀態 `proposed`），但釋義必須是中文白話。資料來源六類見 §8.1；`sourceNote` 補一句（≤ 30 字）。
- 起草＝Dev、對照＝SA、SCG-4 由 QA 讀全文；最終判準是掌舵者真機（§11）。

## 9. 技術選型與模組落點表

沿用既有技術（`AgentConsole/frontend/package.json`），**不新增依賴**。依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2 末段「子專案內的模組不往根層放」，落點照 `AgentConsole/docs/02_architecture/Architecture.md` §3、§5.3、§5.4 填；**根層零新檔**（除本 PRD）。元件放 `components/domain/help/` 的理由見 D-3。

| 件 | 落點（`AgentConsole/frontend/` 下） | 職責（一句） | 測試（新增） | 需同步改的既有鎖 |
|---|---|---|---|---|
| 型別與狀態釋義 | `lib/help/types.ts`、`lib/help/states.ts` | 型別；全部狀態表的白話釋義（每列只有 `meaning`、`next`） | `lib/help/content.test.ts`（AC-PH-05-1～4、03-5）、`components/domain/help/stateKeys.test.ts`（AC-PH-04-1～3、6、7） | — |
| 說明項與全站共通 | `lib/help/<id>.ts`（每頁一檔，撰寫時 16 檔）、`lib/help/common.ts` | 每頁：用途、步驟、欄位、`sourceFiles`、引用的狀態表 id；共通：`HELP_COMMON`（§4 末列各項＋`serviceState`）、跨頁共用釋義 `SHARED` | 同上 | — |
| 彙總、路由與白話檢查 | `lib/help/registry.ts`、`lib/help/lint.ts` | `HELP_PAGES`、`HELP_ROUTES`、`PENDING_HELP_PAGES`、`NO_STATE_PAGES`、`helpForPath`；切句、英文詞、字元（純函式）與白名單 | `registry.test.ts`（AC-PH-03、08-1、08-2）、`lint.test.ts`（AC-PH-05-6） | — |
| 名稱解析 | `components/domain/help/stateSources.ts` | `STATE_SOURCES`：表 id→{標題、鍵、`labelOf`（可缺）}，只 import 既有常數表 | `stateKeys.test.ts` | — |
| 按鈕 | `components/domain/help/PageHelpButton.tsx` | `usePathname`→`helpForPath`；無對應不渲染；路由變更即關閉；圖示 `BookOpen` | `PageHelpButton.test.tsx`（AC-PH-01、07-1；含 `RootLayout` 斷言） | — |
| 對話框 | `components/domain/help/PageHelpDialog.tsx`、`IssuesLegendGroups.tsx` | 四段＋收合的全站共通（建於 `DialogContent`）；議題詞表群：`getIssues({ limit: 1 })`、query key `["help","issuesLegend"]`（不掛 `["issues"]` 家族）、沿 `SI_QUERY_OPTIONS` | `PageHelpDialog.test.tsx`（AC-PH-02、04-4、04-5）、`help.static.test.ts`（AC-PH-02-3、04-4 靜態半、05-5、05-7） | — |
| 頂列接入（既有，加法） | `components/layout/TopRegion.tsx` | `:17` 旁加 import；`:145-157` 右側群組末端加 `<PageHelpButton />` | （見按鈕列） | `layout.test.tsx:71-74` **不受影響**（不新增 layout 檔）；`:263-272`（/login 無動作）仍成立；`tests/design-rules.test.ts:68-69` 讀 `TopRegion.tsx` 原文斷言焦點環類名，保留該行即可 |
| 匯出常數（既有，加法） | `lib/domain/si.ts` | `:191` 後加 `export const PROP_STATE_KEYS = Object.keys(PROP_STATUS_BY_STATE)`（無行為變更） | 鎖在 `stateKeys.test.ts` | `lib/domain/si.test.ts` 不動（§13.3） |
| e2e 與覆蓋率 | `tests/e2e/page-help.mock.spec.ts`；`vitest.config.mts`（既有，加法） | e2e：每條路由各開一次、鍵盤、焦點、390 視窗、axe、請求計數（`shellHandler`，`tests/e2e/mockApi.ts:185`；議題黃金檔）；覆蓋率：`coverage.include`（`:26-72`）加 `lib/help/registry.ts`、`lib/help/lint.ts`、`components/domain/help/stateSources.ts` | （本身） | `playwright.config.ts:19` 的 `testMatch` 已涵蓋；門檻（`:73`）不動 |
| 文件（規格） | 本檔；`AgentConsole/docs/03_testing/contracts/TCS-PageHelp-<日期>.md` | `spec-frozen --root` 取 monorepo 根（Stage-1 含根層 PRD，`SDD_AUTOCLAUDE_BRIDGE.md:356`） | — | **有 glob 型根層消費者**：`tools/tests/test_root_module_layout.py:140-146` 讀全部 `*_PRD.md`；先例 `Issue_Center_PRD.md` 已列入 compat-ci `paths`（`windows-compat-ci.yml:244-246、732-734`、`macos-compat-ci.yml:107-109、603-605`）。本檔是否補入由主控收尾 commit 定奪（`.github/**` 開發棒不准改，`AgentConsole/CLAUDE.md:141`） |
| 文件（過程；主控） | `AgentConsole/docs/06_quality/SCG4-REVIEW-PageHelp-<日期>.md`；`RTM.md` 新子表 | 審查與追溯（先例 `SCG4-REVIEW-FsmTrail-20261018.md`） | — | 子表編號**由主控依落地序編號**（姊妹 `Console_SysAdmin_Backup_PRD.md` §9.4 規格文件列同樣新增 RTM 子表、編號依落地序）；RTM 計數列不動（ID 加反引號，`Arch:429`） |
| 文件（架構同步；主控，發布階段） | `AgentConsole/docs/02_architecture/Architecture.md` | §3 目錄表（`:210-218` 區）加 `frontend/lib/help/`、`frontend/components/domain/help/`；§5.2 Top 列（`:353`）補「本頁說明鈕」；§5.4 檢查表（`:421-432`）加一格 | — | 契約 `API_Contract_P3-6.md:2764`（G-G5）**不改**：本件是新增一顆鈕（Q1 (d) 例外） |
| 與姊妹 PRD 同步（唯讀） | `Console_SysAdmin_Backup_PRD.md`、`SelfImproving_Ledger_DB_PRD.md`（`docs/01_requirements/`） | 前者加導覽項與兩條路由（AC-BK-01-1、01-2），後者只在異常態於議題中心頂部多一條資料來源提示（§7 (c)） | — | 見 D-12：先落地者占號、後落地者補說明項與欄位列 |

- **真跑清單：會渲染頂列的既有測試**（F-07；訂正 v0.1 的「各 view 測試不渲染頂列」）：`components/layout/layout.test.tsx`（全檔）、`components/layout/si-login-gate.test.tsx:43、60`（`RootLayout`＋`SiView`，路徑 `/self-improving` 有說明項，鈕會出現）、`components/domain/views/DashboardView.test.tsx:355`（單獨渲染 `<TopRegion />`）。預期不紅（只多一顆鈕；`layout.test.tsx:173-198` 的名稱斷言只看既有鈕），由 TCS 階段逐檔真跑並貼輸出，不憑推論。
- **已複核不需改**：`tests/e2e/p9-w7-ui.spec.ts:180-206`（`getByText("幫助中心", { exact: true })` 不受影響）、`components/domain/si/si.static.test.ts:83`（只掃 `app/self-improving/page.tsx`）；其餘 view 測試沒有渲染頂列，TCS 階段真跑複核。
- **連動面**：新檔須遵守 `tests/design-rules.test.ts`（掃 `lib/**`，說明文字也受 emoji 與色碼規則約束）、Prettier（printWidth 200、LF）、ESLint；覆蓋率門檻不降。依賴方向：`lib/help/**`（純文字）← `components/domain/help/**` ← `components/layout/TopRegion.tsx`。

## 10. 風險

| # | 風險 | 緩解 |
|---|---|---|
| R-1 | **內容漂移**：畫面改了、說明沒跟 | 狀態鍵雙向鎖＋型別鎖、出處鎖（擋改名、刪欄位）、表單欄位清單鎖（AC-PH-05-7）、接入檢查表（FR-PH-08）；**擋不到**畫面私有字樣（SSE、能力晶片、自治等級、Agent 燈、階段進度）、`sddFsmState` 新增、非表單頁新增欄位與語意改變，由真機與 SCG-4 人讀補位 |
| R-2 | 「白話」是主觀判斷；說明文字還可能被 `design-rules.test.ts` 判違規（emoji、`#abc`） | lint 只擋機械面並提早明確報錯（AC-PH-05-3）；最終判準＝掌舵者真機（§11 V1） |
| R-3 | 頂列單點變更牽動全站；議題中心說明多一個請求、每次開啟重取 | 按鈕只在登記表命中時渲染、登記表錯誤由測試擋；axe 與焦點測試涵蓋頂列；會渲染頂列的既有測試列入真跑清單（§9）；請求用獨立 query key、失敗只降級狀態段、其餘路由零請求（AC-PH-06-3） |
| R-4 | 窄螢幕頂列多一排或擠版（右側群組已有 44px 的鈴〔`NotificationBell.tsx:50` 的 `size-11`〕與 52px 的待審批鈕〔`TopRegion.tsx:152`〕）；jsdom 不評估 CSS，<768 與無橫向捲動只能真瀏覽器驗 | <768 只留圖示、允許換行；AC-PH-07-3 以 390 視窗實測（Playwright mock），必要時改用較小圓形圖示鈕；真機 V2 |
| R-5 | 與公告列靜態「幫助中心」混淆（同在頂部、先前同用 `CircleHelp`） | 本鈕改用 `BookOpen`、鈕名「本頁說明」（D-2）、「全站共通」段寫明公告列字樣不可點；Q1 (d) 提供合併方案 |

## 11. 出口條件與分輪

**SDD 路徑**：Stage-1＝本檔（SCG-0 審查 PASS 後，依凍結常態規則由主控代執行，`SDD_AUTOCLAUDE_BRIDGE.md:538`）；Stage-2＝TCS；凍結後才實作。

**機械可驗**（徑②：session 內自跑，輸出逐字貼進證據檔與 RTM「自動測試」欄；沒貼＝未驗證）：
- (a) `npx vitest run` 全綠，含新增測試（AC-PH-01～05、06-4、07-1、07-2、07-5、08）；`npx tsc --noEmit`、`npm run lint`、`npm run build` 皆 rc=0。**Windows 開發機自跑 `npx vitest run` 與 `npx tsc --noEmit` 並貼輸出**（CI 的 frontend job 只在 ubuntu-latest，§6）。
- (b) `npx playwright test tests/e2e/page-help.mock.spec.ts`：每條路由各開一次說明、鍵盤、焦點歸還、390 視窗、axe、請求計數（AC-PH-06-3、07-3、07-4）。
- (c) 零侵入（AC-PH-06-1、06-2）；`PENDING_HELP_PAGES` 為空（AC-PH-03-6）；覆蓋率門檻不降（`vitest.config.mts:73`）；首屏 JS 增量（AC-PH-06-4）。

**掌舵者真機**：V1 逐頁開說明，不看英文就能說出該頁用途，任指 3 頁各 2 個狀態都能說出意思與下一步。V2 手機（或 390 寬視窗）看得到鈕、讀得完、不橫向捲動。V3 議題中心說明的狀態段與頁面「狀態說明」一致。V4 只用鍵盤：Tab 到「本頁說明」、Enter 開、Esc 關，焦點回到該鈕。

**分輪**（鐵律七：三輪同一持有面——`registry.ts`、`states.ts`、`lint.ts`——一律串行，前一輪經主控親驗才派下一輪）：
1. **輪 1 骨架、全部狀態表、全站共通與先導三頁**：§9 的 `lib/help/` 與 `components/domain/help/` 新檔、`TopRegion` 接入、`si.ts` 匯出，其中 `states` **一次寫完全部狀態表**（撰寫時 18 張；`Record<StateTableId,…>` 維持完整型別、不放寬成 Partial）；頁 `issues`（API 詞表）、`projects`（常數表）、`settings`（無狀態表）；其餘頁列入 `PENDING_HELP_PAGES`；e2e 骨架。
2. **輪 2 專案家族、匯入與儀表板**：`dashboard`、`project-detail`、`goals`、`goal-detail`、`tasks`、`task-detail`、三個表單頁、`import`（只新增頁檔與登記，不再動 `states.ts`）。
3. **輪 3 執行、監控、自我進化與全站驗收**：`execute`、`monitor`、`self-improving`；`PENDING_HELP_PAGES` 清空；完整 e2e；SCG-4 獨立審查、RTM 回填、真機 V1～V4。

## 12. 現查指令

既有座標已隨 §4～§9 就地標出；SDD 流程座標 `SDD_AUTOCLAUDE_BRIDGE.md:310-314、347-366、523-538、547-553`；姊妹案一律以 AC id／節號引用（行號隨稿漂移，D-12）。可重跑的現查指令：`python AISDLC_SDD/scripts/sdd_version.py`；`git ls-files 'AgentConsole/frontend/app/**/page.tsx' 'AgentConsole/frontend/app/page.tsx'`（列 20 檔）；`git grep -l -i -w legend -- AgentConsole/frontend/lib AgentConsole/frontend/components AgentConsole/frontend/app AgentConsole/engine-bridge/app AgentConsole/backend/src/main`（除議題相關檔外只命中兩個圖表內部圖例）；`git grep -n 'from "@/components' -- AgentConsole/frontend/lib`；首屏 JS：`Push-Location AgentConsole\frontend; npm run build; (Get-Content -Raw .next\diagnostics\route-bundle-stats.json | ConvertFrom-Json) | Select-Object route,firstLoadUncompressedJsBytes; Pop-Location`。

## 13. 主控代決清單與開放問題

### 13.1 主控代決清單（我拿不準、但可給預設值；掌舵者可隨時推翻）

| # | 預設值 | 理由 |
|---|---|---|
| D-1 | 按鈕放頂列右側群組、全站一顆（Q1 的預設） | 一處改動全頁生效；不必動 6 個標題列檔（§4 發現 3）、不會漏頁（路由鎖保證）；捲動時仍可見；回歸面＝會渲染頂列的三個既有測試檔（§9 真跑清單），比逐頁加鈕小 |
| D-2 | 鈕名「本頁說明」 | 「說明文件」「幫助中心」已是靜態字樣、「狀態說明」是議題中心既有鈕，需區別（R-5） |
| D-3 | 元件落 `components/domain/help/`，內容落 `lib/help/` | `layout.test.tsx:71-74` 鎖 `components/layout` 恰四個元件檔；`components/ui/` 是不依賴領域的 shadcn 原子（`Arch:212`），而對話框要讀登記表與議題 API；`lib` 不 import 元件 |
| D-4 | 說明 id 撰寫時十六個、路由樣板十九條，登入頁排除；驗收一律由登記表推導 | `/login` 在頂列 `showTools` 之外；姊妹 PRD 會增加路由（D-12） |
| D-5～D-7、D-10 | 狀態釋義每張表全站一份（`states.ts`），頁檔只引用表 id（D-5）；議題中心詞表以 `GET /api/v1/issues?limit=1` 取、每次開啟重取（D-6）；英文白名單 v1 為 31 詞（D-7，§8.3）；不自動彈出、不加「新」標記（D-10，Q2 的預設） | 免得各頁寫法互相矛盾；沿用既有端點與 `SI_QUERY_OPTIONS`、不新增 API，詞表只有一個真相源；白名單取自畫面本身就出現的詞，寧窄勿寬、增詞走複審 |
| D-8 | 提案狀態以 Console 表（11 鍵）為準；差異**以一列觀察（OBS）作載體**：處置 `deferred；再開症狀：根層 PROP_STATES 新增 retired，或 Console 的表刪掉它`（格式見 `docs/06_quality/SelfImproving_Observation_Ledger.md:5`），由主控於發布階段入帳、不在本功能改帳本；`propState.retired` 的 `meaning` 寫明「根層目前不會產生這個狀態，畫面為日後預留」 | 它決定畫面行為；根層對齊屬另案。載體選 OBS 而非提案：`PROP_STATES` 沒有 `retired`（`events.py:38-39`），它只是觀察的處置值（`rows.py:25`、`issuemap.py:115`）；`Issue_Center_PRD.md:135` 已登記同一差異 |
| D-9 | `PROP_STATE_KEYS` 作為 `si.ts` 的一行加法匯出；`ParsePath`、`ImportSourceType` 不匯出、不入狀態表 | 前者無行為變更且是上鎖必需；後者為上鎖而改既有檔不划算（§4 發現 5） |
| D-11 | 分三輪＋`PENDING_HELP_PAGES` 過渡；輪 1 一次寫完全部狀態表，型別 `Record<StateTableId,…>` 維持完整 | 每輪 commit 都能過 CI 路由鎖；缺一張表即編譯紅，不因分輪而放寬 |
| D-12 | **與姊妹 PRD 的落地序**：`Console_SysAdmin_Backup_PRD.md` AC-BK-01-1／01-2 加第九個導覽項 `sysadmin`（`/sysadmin`、`/sysadmin/backup`；姊妹階段一起生效），其 §9.4 條件列與 D-BK-10 指向本案；`SelfImproving_Ledger_DB_PRD.md` §7 (c)（P2 的前端異常態提示條）只在異常態於議題中心頂部多一條「資料來源」提示、正常態版面不變。預設：**先落地者占號、後落地者補**——後者補 `lib/help/sysadmin*.ts`（兩條路由各一份說明項）與兩條路由樣板，內容可先入 `PENDING_HELP_PAGES`（PageHelp 已收輪者亦可暫時重填，AC-PH-03-6）；帳本案落地時視需要為 `issues` 補一列欄位（異常態才出現的資料來源提示），自我進化頁不變；本案 AC 件數一律由登記表長度推導、不寫死；姊妹頁內的「還原與說明」區（FR-BK-08）不併入本案對話框 | 路由鎖與導覽鎖會替後落地者擋下遺漏（AC-PH-03-1、03-2、03-4）；但新增欄位沒有鎖（R-1），後落地者要手動補欄位列 |
| D-13 | 儀表板的 KPI 卡（活躍專案數、待審批草案數、本週完成任務數、執行中 run 數）、進行中的執行卡、待人工審批卡、專案狀態圖都列入欄位表並白話寫明算法（原 Q3 降級） | 掌舵者原話已含「每個欄位」；這些數字的算法一望不知、最容易被誤讀 |

### 13.2 開放問題（只有掌舵者能答；各附建議與理由）

- **Q1　說明鈕放頁首、還是導覽列？**　選項：(a) 頂列右側、全站一顆（建議）；(b) 每頁標題列右上（要改 6 個檔、既有 view 測試可能受影響、每個新頁都得記得加）；(c) 左側導覽列（窄螢幕底部 Tab 已滿六項）；(d) 把公告列既有的靜態「幫助中心」升級成入口、不新增鈕（要改契約 G-G5〔`契約:2764`：五個靜態字樣不可點〕與 `p9-w7-ui.spec.ts:190`；且公告列各 span 在 <768 個別隱藏〔`TopRegion.tsx:63,68,73`〕，手機上看不到）。**建議 (a)**：一處改動、不會漏頁、捲動時仍可見、回歸面最小；代價是它在畫面最上方右側、不在內容區，且與靜態「幫助中心」同在頂部（以不同圖示與名稱區別，R-5）。
- **Q2　第一次進頁要不要自動彈出說明？**　**建議不要**：彈窗打斷您手上的事、需要記錄「看過沒」、會搶走鍵盤焦點並增加測試面；由常駐的「本頁說明」鈕承擔。
- **Q3**　已降為主控代決 D-13（編號保留、不重排）。
- **Q4　自我進化與議題中心既有的說明，要不要併進同一個元件？**　**建議本版不併**：議題中心「狀態說明」鈕與其測試（AT-IC-08-2 系列）維持原狀，新說明的狀態段以同一份 `legend` 取數、兩處永遠一致；自我進化頁沒有 API 詞表（§4 發現 1），其狀態由登記表＋鍵鎖承擔。
- **Q5　登入頁要不要也有說明？**　**建議不要**：未登入時頂列不顯示動作，頁面只有帳號與密碼兩欄，沒有狀態詞。
- **Q6　SDD 引擎的 FSM 原始狀態名（英文）要不要逐一說明？**　「目前狀態」格會原樣印出任何狀態（§4 發現 7），畫面上可能出現沒解釋的英文狀態。**建議只解釋據以決策的五個**（`HUMAN_PENDING`、`SPEC_FROZEN`、`ESCALATION`、`ESCALATION_FINAL`、`AUTOCLAUDE_DELEGATED`；表 `sddFsmState`），外加八個主階段與四個非主階段（表 `sddPhase`），其餘請看旁邊「階段」的中文。理由：全部逐一說明會把引擎內部狀態機搬進使用者說明，且新增狀態沒有常數可鎖（只有弱鎖，§8.2 備註 2）。真機後若仍看不懂，再擴大。
- **Q7　每頁的說明要不要多一段「全站共通」？**　選項：(a) 每個對話框底部加一段預設收合的「全站共通」，寫一份、各頁共用（建議）；(b) 只在儀表板的說明裡講；(c) 本版不講。**建議 (a)**：頂列與底部的連線點、通知、搜尋每頁都看得到，卻不屬於任何一頁的內容，不講就等於全站都有「沒解釋的字」；預設收合不干擾閱讀，只寫一份不會漂移。代價是多一個收合區與一條測試（AC-PH-02-6）。選 (b) 或 (c)：移除 §4 末列、AC-PH-02-6、`common.ts` 的 `HELP_COMMON`，其餘不受影響。

### 13.2.1 掌舵者裁決（2026-10-27，本窗互動選項；Stage-1 凍結依據）

- 掌舵者對 Q1、Q2、Q4、Q5、Q6、Q7（主控回報編號 P-1～P-6）裁決「全部採建議值」：Q1＝(a) 頂列右側、全站一顆（D-1）；Q2＝不自動彈出（D-10）；Q4＝本版不併，兩處共用同一份 `legend`；Q5＝登入頁不加；Q6＝只解釋據以決策的五個狀態加八個主階段與四個非主階段；Q7＝(a) 加「全站共通」段、預設收合、只寫一份（AC-PH-02-6）。Q3 維持降為 D-13。
- 鍵 `agentconsole-page-help` 據此 Stage-1 凍結；凍結後修訂只走〈勘誤〉節（不改正文）。

### 13.3 一審 P4 登記（只登記、本版不處理）

| # | 事實 | 處置 |
|---|---|---|
| F-16 | 新畫面元件的登記慣例：`ADR-002-Frontend-Design-System.md` §4「與設計稿的已知差異」表（`:119-137`，現列 1～15）是設計稿沒有的新元件的登記處；「本頁說明」鈕與對話框屬此類 | 登記、不處理：由主控發布階段補一列，與 `Architecture.md` 同步同一個 commit（§9） |
| F-17 | 議題中心表頭八欄的字面值在 `issues/IssueTable.tsx:22`（`HEADERS`），`:99-102` 只是 `HEADERS.map` | 登記；§4 `issues` 列因同列改寫已順手更正座標，不涉設計 |
| F-18 | (1) §6 的「開啟對話框 ≤ 100 ms」「詞表請求 ≤ 2 秒」沒有對應 AC；(2) `PROP_STATE_KEYS` 新匯出（`si.ts:191` 後）與 `si.test.ts:393-398`（釘根層 `PROP_STATES` 的歸類）相鄰：該測試不釘 `si.ts` 的匯出清單，加一行匯出不會使它轉紅 | 登記、不處理：(1) 由真機 V1 目測；(2) TCS 階段真跑確認 |

## 勘誤（本檔凍結之後的訂正；正文不改，只在本節追加）

### 勘誤一（2026-10-28；Stage-2 TCS 起草與 SCG-3 獨立審查後；條號與 `AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md` §7.3 相同；掌舵者裁決座標 sid c61e3847-c8bf-4694-962f-93a657a7bf35 line 4437；主控依凍結常態規則執行，鍵 `agentconsole-page-help` 於 Stage-2 凍結記新 digest）

| 條 | PRD 座標 | 原文 | 改文 | 理由 |
|---|---|---|---|---|
| 1-1 | AC-PH-06-1、AC-PH-06-2（L112、L113） | 06-2：「既有測試檔的 diff 只含 §9 所列檔、不刪斷言」；06-1：「只含 §9 表列路徑」 | 兩條各加：「唯一例外：`AgentConsole/frontend/components/domain/si/si.static.test.ts`——其 `bridgeLeaks` 的 `checkText` 第二分支限縮為 URL 形：只判以 `/` 或 `scheme://` 起頭的字串，以及樣板運算式之後的每個片段（一律視為 URL 形）；相對檔案路徑形（如 `components/domain/si/**`）不判；並補負控（`components/domain/si/**` 回空、`${base}/si/x` 回非空，另三個只靠第二分支才紅的樣本）；§9 表加此檔一列」 | 既有鎖 AT_932_4_3 把全樹非測試原始碼中含 `/si/` 路徑段的字串字面值一律判紅；`self-improving` 頁的 `sourceFiles` 必含 `components/domain/si/**`（AC-PH-05-5），副本實測整檔 rc 1；「只在字串開頭或樣板運算式後判」等於刪掉第二分支，不可 |
| 1-2 | §9 後的「已複核不需改」（L219） | 「`components/domain/si/si.static.test.ts:83`（只掃 `app/self-improving/page.tsx`）」 | 補「；`:249-276`（AT_932_4_3：掃 `app`、`components`、`lib`、`hooks` 全部非測試原始碼）**需同步改**，見 AC-PH-06-2 的例外」 | PRD 只複核了 `:83`，漏了 `:249-276` |
| 1-3 | §4 定義「狀態表」的說明句（L34；表頭在 L36）、AC-PH-03-5（L93） | 「『狀態表』＝該頁要列的狀態表 id（§8.2）」；AC-PH-03-5 沒有鎖「頁登記了該頁該列的表」 | AC-PH-03-5 補一句：「每個已寫的 PRD 十六頁，其 `states` 的表 id 集合與名稱模式（`label`／`raw`）須等於 §4 的『狀態表』欄」 | 欄位標題明定是逐頁必列的出處，卻沒有 AC 鎖它；開發棒漏列一張表沒有任何測試紅（TCS D-PH-15、AT-PH-03-5-2） |
| 1-4 | AC-PH-05-3（L106）、AC-PH-05-2（L105）、AC-PH-05-6（L109） | 05-3：「連續 ≥ 3 位半形數字」（未說先剔除 ID 形態）；05-6：「4 位數字」 | 05-3 加「（先剔除 `OBS-SI-NNN`、`PROP-SI-NNN`、`DEF-N-N` 形態，再判英文詞與數字）」；05-6 的「4 位數字」改「3 位數字（2 位不命中）」 | `OBS-SI-001` 本身含三位數字，不先剔除則說明文字連引用一個真編號都違規；05-2 的剔除只寫在英文詞規則；兩條門檻對齊並補邊界（TCS D-PH-10） |
| 1-5 | AC-PH-03-5（L93） | 「`purpose` 1～3 句」 | 加「（以 `lint.ts` 的 `splitSentences` 對全部 `purpose` 項切句，合計 1～3 句）」 | `purpose` 是陣列，「句」與「項」不同；與 AC-PH-05-1「每頁 `purpose` 合計 ≤ 3 句」同一判準（TCS AT-PH-03-5-1） |
| 1-6 | AC-PH-04-5（L100） | 「取 `siErrorParts`」 | 加「；三項皆空（網路失敗、無詳情）時改接 `describeError`；`200` 但回應沒有 `legend` 或四群缺席同樣走失敗句，原因寫『回應沒有詞表』」 | 網路失敗時 `siErrorParts` 三項皆空，句子會斷在冒號；空表不是成功（TCS D-PH-8） |
| 1-7 | AC-PH-03-5（L93） | 「`states` 為空者必在 `NO_STATE_PAGES`」 | 改雙向：「`states` 為空者必在 `NO_STATE_PAGES`，且 `NO_STATE_PAGES` 內者必為空」 | 單向則名單可無限陳舊（TCS AT-PH-03-5-1） |
| 1-8 | AC-PH-02-1（L82）、AC-PH-02-5（L86） | 02-1：「四個 `h3`」；02-5：「每表有小標題」 | 02-5 加「小標題與詞表群標題一律 `h4`」 | 小標題若用 `h3` 會違反「恰四個 `h3`」（TCS D-PH-5） |
| 1-9 | AC-PH-06-3（L114） | 「頁面自身的輪詢以網址白名單排除，細節由 TCS 定」 | 改「以新穎性規則排除：點擊後才出現、且（方法, 路徑）在點擊前沒出現過的請求才算新增；`/api/v1/issues` 另含查詢串」 | 逐頁列舉輪詢網址脆弱易漏（TCS D-PH-13） |
| 1-10 | AC-PH-06-1（L112） | 「`git diff --name-only <Stage-2 凍結 commit>..HEAD`」 | 改「以本功能自己的 commit 範圍（`<base>..<本功能最後 commit>`）；共用分支上姊妹案 commit 交錯者不計」 | 範圍在共用分支上不明（TCS G-C1） |
| 1-11 | §8.1（L149 起） | （描述）型別小節只列型別，未定公共面簽章 | 加一句「`helpForPath` 回 `HelpId` 或 `null`、`PageHelpDialog` 的 props、`STATE_SOURCES` 欄名（`title`、`keys`、`labelOf`）、`lint.ts` 匯出名、`SHARED` 型別、`HelpId`／`StateTableId` 聯集，以 TCS 的 D 表與〈契約節〉為準」 | PRD 未定的公共面由 TCS 補齊，避免兩處各寫一份 |
| 1-12 | §7 測試 id 清單（L145） | 「議題詞表群 `page-help-legend-statuses｜results｜sources｜severities｜note`。」 | 補「；詞表載入中 `page-help-legend-loading`（`role="status"`）、詞表失敗 `page-help-legend-error`（`role="alert"`）」 | AC-PH-04-5 要求載入中與失敗各一句固定文字，需要測試鉤而清單沒列；加法、不改既有 id（TCS D-PH-7、C4） |
