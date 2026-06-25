# AutoSDD 能力整合對照圖（Capability Integration Map）

> **性質**：跨輪、跨軌的**規劃層 SSOT**，把「AutoSDD 端到端願景（輸入 PRD → 輸出可運行系統）」拆解的
> **7 大能力 + 6 項設計決策**，逐一對應到本 monorepo 既有模組與三軌（A/B/C），標註現況、缺口與衝突校正。
> **建立日期**：2026-06-26 ｜ **狀態**：Active（規劃層對照基準，非單輪 improving_NN 迭代）
> **來源**：掌舵者提交之 `proposal.md` + `design.md` 兩份願景文件（解碼後原文見 §6 附錄）。
> **掌舵者裁定（AskUserQuestion 2026-06-26）**：①整合形式＝「能力整合對照圖 + 交叉引用（本檔）」；
> ②範本只做「最小外科式」北極星指標（不改三軌結構與四階段紀律）。

---

## 0. 定位與三條鐵律

1. **這是文件/規劃層整合，不是現在動程式**。7 大能力屬「多月 roadmap 級」願景；依本專案紀律
   （四階段 + SCG/G 閘門 + 零信任 + 絕不累積開發），任何能力的**實作**都必須走未來某輪
   `AutoSDD_improving_NN` 的完整流程。本圖只負責「願景 ↔ 模組 ↔ 三軌」的對應與分流，**不授權任何實作**。
2. **本圖是對照基準 SSOT，不是迭代輪**。它不佔用 `improving_NN` 編號；未來各輪 A/B/C 軌的 W 項
   **由本圖的能力缺口衍生**，但仍各自走其軌道紀律與檔名遞增。
3. **零信任**：下列「現況」欄的模組存在性與成熟度，錨定既有**已實測**權威源（見 §1），並標明
   **本 session 未重跑 pytest/ci-gate**——數字一律標來源與日期，非本檔現場宣稱。能力的
   「已有/部分/缺」判定基於既有架構文件 + 本 session 開檔確認，file:line 證據隨附。

---

## 1. 零信任現況錨點（既有實測權威源，非本 session 重測）

| 模組/事實 | 現況（標來源） | 權威源 |
|----------|--------------|--------|
| AutoClaude 微核心 | Hexagonal：`core/ports/`、`infra/adapters/`、`plugins/`、DAL 三後端（File/InMemory/Pg + Dual）；Port/Plugin 數量以 `AutoClaude/CLAUDE.md` `[Architecture Snapshot]` 為 SSOT（**禁寫死 9 Ports/13 Plugin 宣稱值**） | ConsoleUI PRD §0.1（2026-06-18 實測）＋ AutoClaude `[Architecture Snapshot]` |
| AutoClaude 狀態機閉環 | INIT→PRE_RUN_VALIDATE→EXECUTE→（Token Guard ≥80% /compact、≥90% checkpoint）→EVALUATE→（CORRECTION / ESCALATION → 自演化）→DONE→GOAL_SYNTHESIS | 根 `CLAUDE.md`「狀態機閉環」段 |
| A 軌橋接入口 | `SddToPlaybookAdapter`（有規格→規格驅動，spec 凍結硬閘 + 白名單模板消毒）/ `GoalDecomposer`（無規格高階 goal→DAG，三道有界閘 ≤24／Kahn 無環／非空 + 🔴 人工 signoff） | `AutoClaude/.../sdd_to_playbook_adapter.py`、`execution/goal_decomposer.py`（ConsoleUI PRD §0.1） |
| 執行器後端 | `PtyExecutor`（預設）+ `SdkExecutorAdapter`（Claude Agent SDK，可切換，預設 pty 零退化）；act-first fail-closed 硬擋（improving_70） | improving_70 §3~§5 |
| 模型路由現況 | MiniMax（修正腦 + 自主分解）+ Claude Code CLI（步驟執行器）；A/B 對比靠 `cc-switch` 切 profile | ConsoleUI PRD §0.1、範本四階段 A/B 段 |
| PRD 解析 / 目標棧 / Docker | ConsoleUI PRD §5.2（BRD/PRD 智能解析）、§11（Docker 容器化部署）；目標棧 Next.js + Spring Boot + PostgreSQL 18 與本願景**完全一致** | `docs/01_requirements/Agent_ConsoleUI_PRD.md` |
| 既有 web 程式碼 | repo 內**零** Next.js / Spring Boot / Java（全新綠地待開發） | ConsoleUI PRD §0.1 repo 全域搜尋 |
| 最近一輪基線（參考，未本 session 重測） | improving_70：pytest **階段一 floor 3349 → 階段四收斂 3351 passed / 122 skipped / 0 failed**、lint-imports **8 kept**、LOC violations=0、SDD ci-gate exit 0、SDD LATEST v0.26 | `docs/04_planning/AutoSDD_improving_70.md` |

> ⚠️ 本檔為規劃對照，未觸碰任何程式碼，故不需重跑零退化矩陣；上表數字僅供能力成熟度判讀的背景錨點。
> 真正動工的未來輪次，仍須依範本階段一重新實測，**不得沿用上表為門檻**。

---

## 2. 7 大能力 × 模組/三軌對照（核心）

> 狀態定義：**✅ 已有**＝既有模組已涵蓋；**⚠️ 部分**＝部分涵蓋、有明確缺口；**❌ 缺**＝目前無對應實作。

| # | 能力（附件 ID） | 現況 | 對應既有模組 / 證據 | 缺口（新工作） | 落點（軌） |
|---|----------------|------|---------------------|----------------|-----------|
| 1 | `self-correction-loop`（錯誤日誌餵回重試、Max Iterations、升級/中斷） | ✅ 已有 | AutoClaude 狀態機 CORRECTION／ESCALATION／Token Guard／自演化（根 CLAUDE.md 狀態機段）；act-first fail-closed（improving_70） | 與「Docker 沙箱 stderr/stdout 回饋」串接的端到端證據鏈尚未成形 | C 軌既有，能力 #4 落地後補閉環 |
| 2 | `agent-orchestration`（Director/Backend/Frontend/QA 多智能體調度、任務依賴、對話記憶） | ⚠️ 部分 | 狀態機 + EventBus + Plugins；`GoalDecomposer`（無規格→DAG）/`SddToPlaybookAdapter`（有規格→轉譯） | 「角色化多智能體（PM/Architect/Backend/Frontend/QA）」分工尚未顯式建模；對話記憶屬 preference/goal plugin 範疇 | C 軌（引擎）＋ A 軌（規格驅動分工）；**排除 LangGraph，見 §3-D1** |
| 3 | `model-infrastructure`（雲端高階推理 + 地端高頻產出、tier 路由） | ⚠️ 部分 | MiniMax + Claude CLI 雙腦；`cc-switch` profile A/B（ConsoleUI PRD §0.1、範本四階段） | **本地 vLLM/Ollama（Qwen-Coder）後端 + 統一 Model Gateway + `tier` 標籤路由**為新增；需高 RAM 地端工作站 | C 軌新項（未來 improving_NN） |
| 4 | `sandbox-execution`（Docker 隔離、build/單元測試、Compose 起整套 E2E API/UI） | ⚠️ 部分 | PtyExecutor/SdkExecutorAdapter（執行）；ConsoleUI PRD §11（Docker 部署） | **Docker SDK 容器生命週期管理 + Compose 一鍵起 DB/後端/前端 + E2E（API 合約測試 + Playwright UI）**為新增；測試結果＝閉環唯一真相源 | C 軌新項 ＋ ConsoleUI PRD（部署面） |
| 5 | `prd-ingestion`（PRD 語義切分、RAG 最佳實踐比對、輸出規格/Schema/API 合約） | ⚠️ 部分 | ConsoleUI PRD §5.2 BRD/PRD 智能解析；A 軌 `SddToPlaybookAdapter`（規格即 SSOT） | **RAG 最佳實踐庫 + 來源/更新機制**為新增（見附件 Open Question） | ConsoleUI PRD（解析）＋ A 軌（規格→Playbook） |
| 6 | `version-control-integration`（自動 Commit + 建 PR、開發軌跡） | ⚠️ 部分 | repo 已有 git 流程；無自動 Commit/PR 能力 | **開發完成自動 Commit + 建 PR（GitHub/GitLab API）+ 🔴 人工 approve 閘**為新增（見附件 Open Question） | C 軌新項；PR approve 對齊 A 軌 SCG-4 人工閘 |
| 7 | `code-manipulation`（Code Map + AST(Tree-sitter)/LSP 定位、僅輸出 Unified Diff、linter 驗證、禁整檔重寫） | ❌ 缺 | 目前無 AST/LSP/Diff 改碼模組 | **完整新建**：Code Map 生成、Tree-sitter AST 解析、LSP 符號定位、Unified Diff 產出 + patch 合法性 + linter 驗證閘 | 全新 roadmap（橫向能力，C 軌主導）；屬安全改碼，須對齊架構紅線消毒紀律 |

### 2.1 落地優先序建議（非承諾，供未來排程）
1. **能力 #4 sandbox-execution**：是「閉環唯一真相源」前提，且 #1 自我修正迴圈要靠它才完整 → 優先。
2. **能力 #7 code-manipulation**：安全改碼是「幻覺破壞性修改」的根本防線，技術風險最高、應早期立樁。
3. **能力 #3 model-infrastructure（tier 路由）**：成本/效能槓桿，可與既有 cc-switch A/B 漸進演化。
4. 能力 #5/#6 與 ConsoleUI PRD 高度耦合，隨該 PRD 的 SCG 進程推進。

> **對齊 design.md Migration Plan（垂直切片次序）**：附件 Migration 主張「先單一垂直切片（PM→Backend→沙箱編譯/單元）→ 加 Frontend + Compose E2E → 補齊 Git/PR 整合與混合算力 Router」。本圖上述「優先序建議」與之**不衝突但視角不同**——附件是「**端到端垂直切片**的鋪設次序」，本圖第 1~4 點是「**能力技術風險**的立樁次序」；落地排程時兩者疊用（先以 #4/#7 立樁，再按垂直切片把 PM→Backend→Frontend 逐段接上）。
> **落地工程約束（附件 Migration 衍生，跨能力適用）**：(a) 各能力以 **feature flag** 控制啟用；(b) **沙箱執行（#4）與雲端模型呼叫（#3）可獨立啟用/停用**，互不阻塞；(c) 全新標的無資料遷移。

### 2.2 Risk 緩解與 Impact 安全細節落點（design.md Risks / proposal.md Impact 衍生）

> 把附件 6 條 Risk 緩解機制與 Impact 安全細節，從 §6 解碼存底**提升為各能力列的設計約束**，避免實作輪遺漏。

| 附件來源 | 緩解/約束 | 掛載能力 |
|---------|----------|---------|
| Risk 上下文遺忘 | Code Map + 按需讀檔 + checkpoint 壓縮歷史 | #7（Code Map）、#2（記憶/壓縮） |
| Risk 無止迴圈 | Max Iterations + 升級/中斷 + 失敗模式偵測（同錯重複即升級） | #1（已有 ESCALATION，見 §3-D6） |
| Risk 幻覺破壞性修改 | Unified Diff + AST 合法性 + linter 檢查，失敗則丟棄不合併 | #7 |
| Risk 沙箱安全 | 容器**預設阻網** + 檔案系統隔離 + CPU/記憶體/逾時資源上限 | #4 |
| Risk 地端模型品質差 | 高頻輸出須過 linter/測試閘；品質不穩任務升級雲端 | #3、#4 |
| Risk E2E flaky | E2E 失敗須**區分載具 vs 邏輯**，避免 flaky 誤判為程式錯誤觸發無謂修正 | #4 |
| Risk 成本失控 | Router 設**成本上限** + 用量超額告警，優先地端 | #3 |
| Impact 安全 | **LLM 金鑰隔離**（不落明文、不入 log）；產出經 **QA Agent 安全檢查** | #3（金鑰隔離）、#2（QA 角色安全檢查）；對齊範本紅線「對外 I/O 預設 deny + allowlist」 |

---

## 3. 6 項設計決策 × 本專案立場校正

| 決策 | 附件主張 | 本專案立場 | 理由 |
|------|---------|-----------|------|
| **D1 協作框架** | **LangGraph**（顯式狀態圖建模、checkpoint、中斷恢復） | ❌ **排除 LangGraph**（掌舵者已評估）；改錨定 **AutoClaude 既有微核心狀態機 + EventBus + Plugins** | 本專案已具更成熟的 Hexagonal 狀態機閉環（Token Guard/CORRECTION/ESCALATION/自演化/跨 Session 持久化）＋ DAL 三後端 checkpoint；再引入 LangGraph＝雙真相源、違 Thin Facade/微核心紅線。附件「checkpoint/中斷恢復」需求已由既有 PlaybookCheckpoint + 狀態機滿足 |
| **D2 改碼介面** | Unified Diff + AST(Tree-sitter)/LSP 定位（禁整檔重寫） | ✅ **採納為能力 #7 設計準則** | 與本專案安全紀律同向；落地時 Diff 產生路徑須套 CONDITIONAL 等強度消毒，linter/patch 驗證閘對齊架構紅線 |
| **D3 沙箱** | Docker 容器（非 WSL/本機直跑） | ✅ **採納為能力 #4 基礎** | 與 ConsoleUI PRD §11 Docker 部署一致；Docker SDK 管容器生命週期 |
| **D4 真相源** | 分層測試閘（編譯→單元→Compose→E2E）為閉環唯一真相源 | ✅ **採納**；對齊本專案「測試驗證意圖」(Rule 9) | E2E 以 API 合約測試為主、Playwright UI 為輔 |
| **D5 混合算力路由** | 高階推理走雲端、高頻產出走地端，`tier` 標籤 Router | ✅ **採納為能力 #3**；以既有 cc-switch/雙腦為起點漸進 | Model Gateway 抽象 + tier 路由；地端 vLLM/Ollama 為新增基礎設施 |
| **D6 防無止迴圈** | Max Iterations(預設 5) + 升級 Director + 中斷 + 標人工 | ✅ **已有**（能力 #1）；對齊既有 ESCALATION + 🔴 HUMAN_PENDING。**自治等級分級（人類介入點）以 ConsoleUI PRD §5.3.2 Level 1–10 表為 SSOT**（重疊以 PRD 為主） | 既有狀態機已實作，附件可作參數對齊參考；介入頻率/升級門檻依 PRD §5.3.2 自治等級 |

---

## 4. 衝突登記（須在未來各輪持續校正）

| 衝突 | 附件原文 | 校正 | 影響 |
|------|---------|------|------|
| **C-1 LangGraph** | design.md Decision 1 選 LangGraph 為協作框架 | **排除**，改錨定既有微核心狀態機（§3-D1） | 能力 #2 的所有後續設計不得引入 LangGraph 依賴 |
| **C-2 「全新綠地、無既有程式碼」** | proposal.md Impact「全新系統,無既有程式碼受影響」 | **與事實不符**：本專案為 **brownfield**（AutoClaude L5 引擎 + AISDLC_SDD 框架 + ConsoleUI PRD 皆已在）。願景能力須以「整合進既有微核心 + 走 Copy-on-Evolve/三軌紀律」方式落地，**唯一綠地部分＝目標產出系統的 web 程式碼（Next.js/Spring Boot，repo 內現為零）** | 防止未來輪次誤把能力當「從零新建平台」而繞過既有架構紅線 |
| **C-3 maturity 宣稱** | 附件描述「具自我修正能力的自動化流水線」 | 成熟度一律以 `AutoSDD_Maturity_Rubric.md` 量表、階段一實測為準（**C 軸引擎宣稱 L5，但上捲 `L_合體=min(A,B,C)` 依 Rubric 粗估僅 L3–L4**，非願景終局 L10） | 未來輪次禁以願景文字當已達成事實 |
| **C-4 「不做 Web 操作介面」vs Console Web UI** | design.md Non-Goal「不做 Web 操作介面（以 CLI/設定檔）」 | **以 ConsoleUI PRD 為主（重疊優先序）**：附件該 Non-Goal 僅指**引擎本體第一階段不自帶 GUI**（AutoClaude/AISDLC_SDD 維持純 CLI，PRD §0.1 實證）；ConsoleUI **Web UI 是「上位引擎願景的 UI/部署落地層」**（透過 Engine Bridge 旁車 subprocess 包 CLI，PRD §0.2），二者**不矛盾、分層共存** | 防止未來誤把「引擎無 GUI」擴張成「不准做 Console UI」；Console UI 走 PRD 自身 SCG 進程 |

### 4.1 第一階段 Non-Goals（scope 圍欄 — design.md Non-Goals 落地）

> 附件第一階段明列的 4 條 Non-Goals，提升為正式 **scope 圍欄**，供未來輪次界定「不做什麼」，防 roadmap 無限膨脹。標註本專案解讀。

| # | 附件 Non-Goal | 本專案解讀 / 校正 |
|---|--------------|------------------|
| NG-1 | 不做雲端部署 / 雲端 E2E（列為後續 roadmap） | 採納：第一階段驗證鏈止於**本機 Docker Compose + 本機 E2E**；雲端為日後 roadmap |
| NG-2 | 不支援任意技術棧（限 Next.js + Spring Boot + PostgreSQL 樣板） | 採納：與 ConsoleUI PRD §3 目標棧**完全一致**（能力 #4/#7 的樣板產出鎖此三棧） |
| NG-3 | 不做 Web 操作介面（引擎以 CLI/設定檔） | **校正（見 C-4）**：僅指**引擎本體**不自帶 GUI；ConsoleUI Web UI 為其上位 UI 落地層，**不在此 Non-Goal 範圍內** |
| NG-4 | 不做模型訓練 / 微調（只整合推理層與路由） | 採納：能力 #3 僅做 Model Gateway + tier 路由 + 推理層整合，**不含訓練/微調** |

---

## 5. 交叉引用登記（本次最小外科式所做的指向）

| 文件 | 變更 | 目的 |
|------|------|------|
| `docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` | 北極星段新增一句 SSOT 指標，指向本圖；7 能力標為三軌長期 roadmap 錨點（不改三軌結構/四階段） | 每輪複製範本時都能看到能力 roadmap 對照入口 |
| `docs/01_requirements/Agent_ConsoleUI_PRD.md` | §0 後新增「上位引擎願景」指標 blockquote，指向本圖 | 釐清 ConsoleUI PRD 是本願景的「上位引擎」之 UI 落地，prd-ingestion/sandbox 對應 §5.2/§11 |

> 本圖 ↔ 上述兩文件互為交叉引用；本圖為「願景能力 ↔ 模組」對照 SSOT，ConsoleUI PRD 為其 UI/部署落地 SSOT，
> 範本為三軌迭代驅動器 SSOT，三者不重複彼此職責。

---

## 6. 附錄：來源附件解碼存底（proposal.md / design.md）

> 掌舵者提交之兩份附件為 UTF-8 mojibake，下為解碼後重述要點存底（供後續輪次免再解碼）。

### 6.1 proposal.md（Why / What Changes / Capabilities / Impact）
- **Why**：單一巨型 Prompt／單一 LLM 無法把「PRD → 可運行系統」做完（遺忘上下文、幻覺、破壞性修改、
  無機制驗證產出是否真能編譯運行）；要真正閉環須以**多智能體協作為核心** + 閉環編譯/測試回饋，
  建立具自我修正能力的自動化流水線（代號 **AutoSDD**）。第一階段涵蓋：多智能體協作、AST/Diff 安全改碼、
  Docker 沙箱閉環，並把驗證鏈推進到「本機自動部署（Docker Compose）+ E2E API/UI 整合測試」。
- **What Changes**：新增 7 能力（見 §2）＋目標產出技術棧 React/Next.js（前端）/ Spring Boot（後端）/ PostgreSQL。
- **Capabilities（New）**：`prd-ingestion`／`agent-orchestration`／`code-manipulation`／`sandbox-execution`／
  `self-correction-loop`／`model-infrastructure`／`version-control-integration`（逐項定義已併入 §2）。
- **Modified Capabilities**：無（首次建立，無修改項）。
- **Impact**：附件宣稱「全新系統、無既有程式碼」（**本專案校正為 brownfield，見 §4 C-2**）；
  外部相依＝LLM API（Claude/GPT）／本機推理（vLLM/Ollama）／Docker＋Compose／Tree-sitter＋各語言 LSP／
  Git 平台 API（GitHub/GitLab）；基礎設施＝可跑 Docker 主機 + 高 RAM（建議 128GB）地端推理工作站；
  安全＝沙箱阻網路/檔案隔離＋資源上限、LLM 金鑰隔離、產出經 QA Agent 安全檢查。

### 6.2 design.md（Context / Goals-NonGoals / Decisions / Risks / Migration / Open Questions）
- **Context**：核心鎖定 LLM 三大失敗模式（上下文遺忘、幻覺破壞性修改、缺乏實際執行驗證）；分層架構
  ①需求解析與知識檢索（prd-ingestion）②多智能體協作中樞（agent-orchestration）③閉環驗證與沙箱執行
  （sandbox-execution + self-correction-loop）④模型與算力基礎設施（model-infrastructure）；橫向＝
  code-manipulation（安全改碼）、version-control-integration（軌跡保存）。
- **Goals**：LangGraph 可控/可觀測/可恢復多智能體流程；AI 改碼以 Unified Diff 為唯一介面經 AST/LSP+linter
  驗證；沙箱實跑 build/單元/Compose E2E 為唯一真相源；自我修正迴圈具明確 Max Iterations/升級/中斷；
  混合算力路由。
- **Non-Goals（第一階段）**：不做雲端部署/雲端 E2E（後續 roadmap）；不支援任意技術棧（限 Next.js+Spring
  Boot+PostgreSQL 樣板）；不做 Web 操作介面（以 CLI/設定檔）；不做模型訓練/微調（只整合推理層與路由）。
- **Decisions（6 項）**：見 §3 對照（D1 LangGraph **本專案排除**／D2 Unified Diff+AST/LSP／D3 Docker 沙箱／
  D4 分層測試閘為真相源／D5 tier 路由 Router／D6 Max Iterations+升級+中斷）。
- **Risks/Trade-offs**：上下文遺忘→Code Map+按需讀檔+checkpoint 壓縮；無止迴圈→Max Iter+升級/中斷+失敗
  模式偵測；幻覺破壞→Unified Diff+AST 合法性+linter；沙箱安全→預設阻網/檔案隔離/資源上限；地端模型品質
  差→經 linter/測試閘把關、可升級雲端；E2E flaky→失敗區分載具 vs 邏輯；成本失控→Router 成本上限+地端優先。
- **Migration Plan**：全新標的無資料遷移；分階段（對應 tasks）：先單一垂直切片（PM→Backend→沙箱編譯/單元）
  →加 Frontend 與 Compose E2E→補齊 Git/PR 整合與混合算力 Router；功能以 feature flag 控制、沙箱與雲端
  呼叫可獨立啟用。
- **Open Questions**：①vLLM vs Ollama（地端推理選型）；②RAG 最佳實踐庫的初始來源與更新機制（人工策展 vs
  自動擷取官方文件）；③E2E UI 測試覆蓋廣度/深度；④PR 自動建立後是否強制人工 approve 才合併。
  → 這些 Open Questions 對應能力 #3/#5/#4/#6 的缺口，未來輪次設計時須先收斂。
