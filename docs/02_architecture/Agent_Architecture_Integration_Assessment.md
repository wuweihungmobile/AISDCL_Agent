# Agent 架構整合評估報告 — OSS Agent 架構選型 × PRD→工作節點 UI 可視化

> 本文件為正式架構評估，供掌舵者 signoff。不含任何程式碼變更，僅作評估與決策依據。

---

## 1. 文件元數據

| 項目 | 內容 |
|------|------|
| 文件編號 | Agent_Architecture_Integration_Assessment |
| 日期 | 2026-06-25 |
| 評估方法 | Architect / SA / SD / QA 四鏡，各 ×2 輪 zero-trust 對抗審查（共八份專家分析收斂） |
| 評估標的 | ①把外部 OSS Agent 架構整合進本系統的首選；②條件分析：以 PRD 產出「工作節點 UI 圖 + 節點描述」之架構路徑 |
| 適用範圍 | AutoClaude（指揮官／執行引擎）、AISDLC_SDD（手腳／方法論框架）、規劃中的 ConsoleUI（C 軌新應用） |
| 現況 | **待 signoff**；本文不改任何程式碼 |
| 北極星對齊 | 指揮官 AutoClaude × 手腳 AISDLC_SDD × 雙向協作；自治度沿 L5→L10 上升而人類不流失掌舵權 |
| 鐵律 | 系統頂層編排器已達 **L5**，任何「替換頂層編排」的整合都是**降級**；UI 需求是「看」不是「換大腦」 |

---

## 2. 執行摘要（結論先行）

- **整合首選 = Claude Agent SDK**（屬使用者候選清單第 6 項「其他」，非 1~5）：以新增 `SdkExecutorAdapter` 實作既有 `IExecutor` port、**替換 `PtyExecutor`**；安全閘**重用既有 `ToolInvocationAdapter`** 接成 SDK 的 `can_use_tool`；SSOT 仍歸 `PlaybookCheckpoint`、**無雙寫**。改動面最小：**不動 thin facade `playbook_runner.py`、不破 `.importlinter` 8 條 contract、0 新 port**。
- **複合第二腳 = PydanticAI / pydantic-graph**：僅在「EXECUTE 內部受控、有界的子圖」補上 L5→L10 動態工作流骨架；其 `End` 節點終止語意貼合本專案 TLA+/TLC 形式化文化。
- **一句話定位**：用 SDK 把「驅動 Claude Code 的脆弱 PTY 文字流」升級為官方程式化 JSON-over-stdio 介面（消滅 DEF-01-007 類解析脆弱性），頂層大腦（FSM 閉環）**原封不動**；PRD→工作節點 UI 是把既有「計畫期 DAG」投影出來給人看與審批，**不改變整合首選、不動編排核心**。

---

## 3. 評估範圍與現況系統架構錨點

本評估建立在以下已驗證的現況之上（錨點，避免後續設計漂移）：

- **Hexagonal / 微核心**：`autoclaude/core/`（Kernel + EventBus + HookSpec + `ports/` 抽象介面）只依賴 ports；`infra/adapters/` 提供具體實作（MinimaxBrain / `PtyExecutor` / ShellEvaluator / LocalLogger）；`infra/repositories/` 為 DAL 三後端（File / InMemory / Pg + Dual）；`plugins/`（16 active）彼此**不可互 import**，協作一律走 EventBus。
- **Ports 清單（18 個 port 模組，已實地核對 `autoclaude/core/ports/`）**：`executor` / `evaluator` / `playbook_repository` / `memory_store` / `embedder` / `vector_search` / `state_repository` / `observability` / `kb_metric_store` / `preference_store` / `tool_invocation` / `brain` / `topology_dashboard` / `goal_freeze_gate` / `rtm_sink` / `rtm_feedback` / `spec_source` / `translation_learning`。
- **Thin facade**：`execution/playbook_runner.py` 為無業務邏輯的薄門面。
- **FSM 閉環**：INIT → PRE_RUN_VALIDATE → EXECUTE(step) →（Token Guard：≥80% `/compact`、≥90% checkpoint）→ EVALUATE →（失敗 Minimax CORRECTION／超限 ESCALATION → 自演化）→ DONE → GOAL_SYNTHESIS。
- **架構機械強制**：`.importlinter` 8 條 contract + LOC 分級政策（data ≤150 / plugin_entry ≤250 / strategy ≤300 / adapter ≤400 / contract ≤400 / service ≤500 / 絕對紅線 ≤750）。
- **TLA+/TLC 五軌**（SDD_FSM / META_FSM / COMPOSITION_FSM / OPTIMIZATION_FSM / FLEET_FSM）形式化證明有界停機。
- **既有 PRD→DAG 兩條真實路徑**：`execution/goal_decomposer.py`（豐富 goal/context，Brain 一次拆解 + 三道有界閘 + 🔴 人工 signoff）與 `infra/adapters/sdd_to_playbook_adapter.py`（已凍結 SDD 規格，`_assert_frozen` fail-closed）。

---

## 4. 候選 OSS Agent 架構評估

使用者候選清單 1~5 與「其他」。四鏡兩輪一致結論：**1~5 皆非首選，第 6 項「其他」之 Claude Agent SDK 勝出**。

| 候選 | 性質 | 與本系統的衝突點 | 裁決 |
|------|------|----------------|------|
| **AutoGen** | Actor 模型多代理 | v0.2→v0.4 重寫又併入 Microsoft Agent Framework（過時）；actor 模型搶 EventBus 主權 | 避開 |
| **CrewAI** | 角色編排框架 | 搶 FSM 頂層編排主權（降級） | 避開 |
| **OpenHands** | 編排型 coding agent | 搶 FSM 主權；需 Docker + Python 3.12，撞本專案 3.11 基線 | 避開 |
| **SWE-agent / Goose** | 編排型 coding agent | 搶 FSM 主權 | 避開 |
| **LangGraph** | 圖編排 + checkpoint | 拉進 LangChain/LangSmith 生態；pydantic v1/v2 衝突高發；graph loop 需自證有界（QA 標 🔴 需 TLC 重證） | 條件性備案，非首選 |
| **Codex CLI** | OpenAI CLI | 2026-02 起 `wire_api` 只剩 responses、無法直驅 Claude、無 turn 硬上限 | 僅作「非 Claude 異質交叉驗證子 agent」 |
| **Aider** | 配對程式 CLI | 官方不支援 import + 強耦合 git | 僅 subprocess 包 CLI 利基 |
| **PydanticAI / pydantic-graph** | 型別安全 agent + 有界圖 | `End` 節點終止語意貼合 TLC；不搶頂層編排（限 EXECUTE 內子圖） | **複合第二腳** |
| **Claude Agent SDK（「其他」）** | Claude Code 官方程式化介面 | 與 `PtyExecutor` 同源（同樣驅動 Claude Code CLI），JSON-over-stdio 取代 PTY 解析 | **首選** |

**為何 1~5 皆非首選的根因**：本系統的編排器（FSM 閉環）已達 L5 且經 TLA+/TLC 形式化驗證有界。候選 1~5 全是「頂層編排框架」，引入它們等於用一個未經本專案形式化驗證的編排器**替換**已驗證的 L5 編排器——這是自治度的降級，且會把 actor／graph loop 的「有界性自證」責任重新攤開。**UI 需求只是要「看」DAG，不需要、也不應該換大腦。**

---

## 5. 整合首選決策與理由

### 5.1 首選：以 `SdkExecutorAdapter` 替換 `PtyExecutor`

**同源理由**：系統本就以 `PtyExecutor` 透過 PTY 文字流驅動 Claude Code CLI。Claude Agent SDK 是其官方程式化版本（JSON-over-stdio），消滅 PTY 解析脆弱性（DEF-01-007 教訓的正解）。

**接縫設計**：

```
core/ports/executor.py (IExecutor)  ← 介面不變
        ▲
        │ 實作（替換 PtyExecutor）
infra/adapters/sdk_executor_adapter.py (新增)
        │ 內部以 Claude Agent SDK 驅動 Claude Code
        │ can_use_tool  ←─ 重用既有 ToolInvocationAdapter（安全閘）
        ▼
PlaybookCheckpoint (SSOT，無雙寫)
```

- **0 新 port**：沿用 `IExecutor`。
- **不動 thin facade**：`playbook_runner.py` 不變。
- **不破 8 條 contract**：adapter 落在 `infra/adapters/`，依賴方向不變。
- **安全閘重用**：SDK 的 `can_use_tool` 回呼直接接到既有 `ToolInvocationAdapter`，沿用既有 `_DENY` 消毒 / guard / allowlist 三道閘。
- **SSOT 不雙寫**：狀態真相仍是 `PlaybookCheckpoint`。

### 5.2 複合第二腳：PydanticAI / pydantic-graph（EXECUTE 內子圖）

僅在 EXECUTE 狀態內，當單一 step 需要「受控、有界的動態子工作流」時引入。其 `End` 節點終止語意與 TLA+/TLC 有界停機文化一致，可作為 L5→L10 動態骨架的安全演進路徑。**不替換頂層 FSM。**

### 5.3 Caveats（採用 SDK 必須處理的三點）

1. **Token Guard 留本側**：SDK 無公開旋鈕對應本系統的 ≥80% `/compact`、≥90% checkpoint 門檻 → Token Guard 邏輯留在本系統側，並繞過 CLI 的 auto-compact 以免雙重壓縮。
2. **`permission_mode` 預設不安全**：SDK 預設 `acceptEdits` 會自動接受檔案編輯 → 啟動時須改為最小權限模式，並與既有 `CrossStepValidator` 配合。
3. **bundled CLI 版本對齊**：SDK 內附的 Claude Code CLI 版本須與本系統假設對齊 → 在 adapter 啟動加入 capability 檢查（版本/能力探測），不符即 fail-loud。

---

## 6. 條件分析：PRD→工作節點 UI 圖 + 節點描述

### 6.1 三種節點圖必須分清（最關鍵的抽象層辨析）

| 層 | 名稱 | 時機 | 產生者 | 內容 |
|----|------|------|--------|------|
| **L1** | **業務任務 DAG** | 執行前／計畫期 | `GoalDecomposer` / `SddToPlaybookAdapter` | PRD 拆出的工作節點 — **UI 要的就是這個** |
| L2 | 編排器狀態圖 | 引擎內部 | PydanticAI BaseNode | 編排器內部結構 |
| L3 | 執行 trace 樹 | 執行後 | SDK turn / tool call | 執行軌跡 |

**裁決**：UI 要的是 **L1**，它在引入任何編排器**之前**就已存在於 `Playbook.tasks`。因此 **UI 需求不改變整合首選**（四鏡一致）。用 graph 編排器（L2）去解 L1 的渲染需求＝搞錯抽象層，且動編排核心＝降級。

### 6.2 PRD→DAG 雙路徑（依規格成熟度分流）

- **路線 A（自由 PRD，半結構化、未凍結）→ `GoalDecomposer`**：當作豐富 goal/context，Brain 一次拆解（非遞迴）+ 三道有界閘（步數 ≤24／Kahn 拓樸無環／非空）+ 🔴 人工 signoff。**不可**走 `SddToPlaybookAdapter`——其 `_assert_frozen` fail-closed 會（正確地）擋下未凍結規格。
- **路線 B（已凍結 SDD 規格）→ `SddToPlaybookAdapter`**：節點帶 AC/AT/SCG，資訊最完整、元件最成熟。

### 6.3 端到端管線（ASCII）

```
   PRD (半結構化)                   已凍結 SDD 規格
        │                                  │
        ▼ 路線A                            ▼ 路線B
  GoalDecomposer                  SddToPlaybookAdapter
  (Brain 拆解 + 三閘             (_assert_frozen fail-closed,
   + 🔴 signoff)                  節點帶 AC/AT/SCG)
        │                                  │
        ▼                                  ▼
  DecompositionDraft  ───壓平───►   Playbook.tasks (L1 DAG)
   (含 depends_on 邊)         ⚠ depends_on 邊在此被丟棄
        │                                  │
        │  唯讀純函數投影                    │
        ▼                                  ▼
  WorkNodeProjector / to_topology_view()  (0 新 port)
        │  輸出 UI metadata + 重算 canonical_graph_digest
        ▼
  薄殼 CLI: python -m autoclaude.work_node_graph <source> --emit json|mermaid
        │  (JSON + Mermaid 雙輸出、有界截斷+分頁、fail-loud exit 0/2/3、唯讀)
        ▼
  ConsoleUI engine-bridge  ──subprocess 包 CLI（禁 import 引擎，紅線）──►  前端 Mermaid.js
        │                                                                  (點節點開描述面板)
        ▼  執行期狀態 MVP 用輪詢
  PlaybookCheckpoint (FSM 執行真相, SSOT)
```

**已核對的 schema 缺口**：`autoclaude/models/playbook.py` 的 `PlaybookTask` **無 `depends_on` 欄**（邊只存在於 `models/decision.py` 的 `DecompositionStep.depends_on`）。因此 draft 壓平成 `Playbook` 時，邊被丟棄。
- **MVP**：先做**計畫期**投影（直接從 draft / SDD 取邊），不動 schema 即可。
- **執行期持續顯示邊**：才需要 additive 補 `PlaybookTask.depends_on`（待決策點 ②）。

### 6.4 投影器設計（兩案，皆 0 新 port）

| 方案 | 形式 | 取捨 |
|------|------|------|
| Architect 案 | `DecompositionDraft.to_topology_view()` 方法 | 資料就近、無新元件；但把 UI 關注點掛到 data model |
| SD 案 | 獨立 `WorkNodeProjector` service | 關注點分離、可獨立測試；多一個 service（受 LOC ≤500 約束） |

兩案皆**唯讀純函數**、**0 新 port**。**裁決傾向 SD 案**（獨立 service），理由：投影屬「呈現」關注點，掛在 data model 上違反本專案 data ≤150 LOC 分級且混淆職責；獨立 service 更利於 6.4 的對抗性單測。最終由 ConsoleUI SCG-1/2 拍板。

### 6.5 渲染管線復用策略

照抄 AISDLC_SDD v0.26 `render_topology_dashboard.py` 的成熟**模式**（JSON+Mermaid 雙輸出、有界截斷+分頁、fail-loud exit 0/2/3、唯讀），並復用其 **canonical_graph_digest 防偽慣例**與 **guard 三段**。

**選項 B（採用）：復用模式，不復用 CLI 本體。** 該 CLI 綁定 meta⁸ 互遞迴算子的 `op_dict` schema，語意不同；硬複用會把工作節點偽裝成 `RecursiveOperator`，造成語意污染。故新建薄殼 CLI，只借模式。

### 6.6 節點描述 JSON Schema（核心交付）

三層欄位，每欄對映既有真實資料來源。路線 A（自由 PRD）無 AC/AT/SCG 時**誠實填 null，不偽造**（不靜默降級）。完整範例見附錄 A。

| 層 | 欄位 | 來源 |
|----|------|------|
| 身份層 | `node_id` / `title` / `description` | `step_id` / `name` / `prompt` |
| 追溯層 | `source_prd_ref` / `dependencies` / `can_parallel` | `ac_id` 或 `spec_path` / `depends_on` / 拓樸 rank |
| 審批層 | `scg_gate` / `evaluator` / `status` / `weak_regex_flag` / `decomposition_reason` / `auto_signoff_note` | `SpecContract.scg_gate` / `evaluator_command`+`max_retries` / `PlaybookCheckpoint` / `PlaybookTask.weak_regex` / `DecompositionDraft.reasoning` / `IGoalFreezeGate` verdict |

### 6.7 可追溯鏈

```
PRD/AC ──(正向 SddToPlaybookAdapter)──► 工作節點 ──(執行)──►
        ──(逆向 IRtmSink，唯讀諮詢 RtmCoverageReport)──► RTM 覆蓋
```

UI 呈現：每節點掛「源自 AC」標籤、覆蓋度熱力（`ac_coverage_pct` 100% 才綠）、SCG-5 儀表、斷鏈/孤兒節點警示。

**🔴 誠實 flag**：`IRtmSink` 只產**諮詢報告**、**絕不自動覆寫人工 RTM**（SCG-5 仍由人工所有）。UI 必須標示為「諮詢視圖」，不得讓人誤以為是權威 RTM。

### 6.8 ConsoleUI 紅線

- engine-bridge **subprocess 包 CLI、禁 import 引擎**（架構紅線）。
- 前端 Mermaid.js 渲染 DAG + 點節點開描述面板。
- status MVP 用**輪詢**（checkpoint 原子寫、節點 ≤24，輪詢足夠；event 推送留後續）。

### 6.9 本需求定位（SA 視角）

把 `GoalDecomposer` 的 🔴 signoff 硬閘從 CLI **升級為可視審批**；這是 L5→L10 自治往上爬時「人類不流失掌舵權」的安全帶，讓自治度能**合法**上升。

---

## 7. 防漂移與四／五源一致（QA 標 🔴 P0）

### 7.1 四源（加 UI 後）

PRD 原文（`goal_hash`）/ DAG 資料（`Playbook.tasks`）/ UI 渲染 / FSM 執行真相（`PlaybookCheckpoint`）。

### 7.2 兩個漂移點與防護

- **漂移點 A：投影圖 ≠ draft DAG**。防護：投影須純函數 + presenter 端**重算 `canonical_graph_digest` 比對 fail-closed**。
- **漂移點 B（最危險）：被 signoff／執行的 Playbook ≠ UI 當初給人看的圖 → 盲簽復辟**。防護：**`goal_hash` + 新增 `topology_digest` 雙指紋**，綁定 draft ↔ signoff ↔ 執行 Playbook。現況 approve 只記 `goal_hash`，須擴充記 `topology_digest`（待決策點 ③）。

### 7.3 🔴 最該警惕的整合接面缺口（P0）

SDD 的 meta⁸ 算子圖有 `verify_topology_consistency`（綁 `op_dict` schema，**程式碼不可復用、只可復用威脅模型**）；但 **Playbook 拓樸（PRD→節點）目前無任何一致性稽核器，UI 等於一張無人核對的漂亮圖**。

**必須新建**（列為 ConsoleUI SCG-1/2 架構草案 **P0 驗收項**；無此稽核器不得宣稱滿足 XAI 四源一致鐵律）：

- `verify_playbook_topology_consistency(render_json, playbook)`：照搬三鐵律 —（1）真實大小誠實；（2）不信 UI 自報的 budget/page；（3）每條 `depends_on` 邊與 `step_id` 逐一比對。
- `guard_playbook_visualization_bounded`：char/node budget fail-closed + 單節點描述另設長度上限。

### 7.4 安全縫合

- **Mermaid 注入面 兼 拓樸漂移面**：節點描述進 Mermaid 前須跳脫 `"` / `{` / `}` / `-->` / `;` / 反引號（這些字元可插假邊）。
- **PRD 經 subprocess 走 stdin/臨時檔，不可走 argv**：Windows ~32KB argv 截斷會使 `goal_hash` 對不上完整 PRD。
- 三道安全閘復用既有 `_DENY` 消毒 / guard / allowlist。
- **bridge 端非零 exit 必當硬失敗**：禁「exit≠0 但有 stdout 就當成功」（Nightly 紀律 #1/#9 同型陷阱）。

### 7.5 QA 風險紅黃綠燈

| 維度 | 燈號 | 說明 |
|------|------|------|
| 有界性 | 🟢 | 節點 ≤24、guard fail-closed |
| 確定性 | 🟡 | Brain 非確定但可 mock 測 |
| 四／五源一致 | 🔴 | **缺 Playbook 拓樸稽核器**（7.3，P0） |
| 可測性 | 🟡 | 純函數投影可測；Brain 需 mock |
| 安全 | 🟡 | 注入面/argv 截斷需處理（7.4） |
| 依賴增量 | 🟢 | SDK 同源、PydanticAI 輕量 |
| TLA+/TLC 衝擊 | 🟢 | GoalDecomposer 不在五軌狀態空間、UI read-only 不寫 FSM-STATE |

---

## 8. 架構紅線清單

1. **不替換頂層 FSM 編排器**（已 L5 + 形式化驗證）；任何頂層替換＝降級。
2. **0 新 port**：SDK 走既有 `IExecutor`；投影走唯讀純函數。
3. **不動 thin facade `playbook_runner.py`**。
4. **不破 `.importlinter` 8 條 contract** 與 LOC 分級。
5. **SSOT 單一**：`PlaybookCheckpoint`，**禁雙寫**。
6. **ConsoleUI engine-bridge 禁 import 引擎，只能 subprocess 包 CLI**。
7. **不靜默降級**：路線 A 無 AC/AT/SCG 一律填 null，不偽造。
8. **IRtmSink 只諮詢、不覆寫人工 RTM**；UI 標「諮詢視圖」。
9. **無 Playbook 拓樸一致性稽核器，不得宣稱滿足四源一致**（P0 硬閘）。
10. **bridge 非零 exit ＝ 硬失敗**，禁「有 stdout 就當成功」。

---

## 9. 缺口、待決策點與落地路線圖

### 9.1 落地改動量（估）

| 元件 | LOC |
|------|-----|
| WorkNodeProjector（投影器） | ~150 |
| 薄殼 CLI（work_node_graph） | ~120 |
| dataclass / guard（含拓樸稽核器） | ~100 |
| 測試 | ~200 |
| **合計** | **~470** |

0 新 port，不動 thin facade / 執行閉環。ConsoleUI 前端另案。

### 9.2 待使用者拍板的決策點

1. **路線 A（自由 PRD） vs 路線 B（SDD 規格）哪個先做** — SD 建議 **MVP 先做路線 B**（節點帶 AC/AT/SCG、資訊最完整、元件最成熟）。
2. **`PlaybookTask.depends_on` 是否補**（僅執行期持續顯示邊才需要；MVP 計畫期投影不需）。
3. **`topology_digest` 落地版本**（建議納入 C 軌 Improving_NN）。

### 9.3 建議落地路線圖

- **Phase 0（spike）**：以路線 B + 既有 SDD 規格驗證投影 + Mermaid 輸出 + 拓樸稽核器三鐵律對抗測試。
- **Phase 1（MVP）**：薄殼 CLI（JSON/Mermaid）+ WorkNodeProjector + `verify_playbook_topology_consistency` + `guard_playbook_visualization_bounded`；ConsoleUI 唯讀渲染 + 輪詢 status。
- **Phase 2**：SdkExecutorAdapter 替換 PtyExecutor（含 Token Guard 留本側、permission_mode 最小化、capability 檢查）。
- **Phase 3**：`topology_digest` 雙指紋綁 signoff；視需要補 `PlaybookTask.depends_on`（執行期顯示邊）。

### 9.4 測試策略

- **確定性單測**：port mock `IBrain` 固定 decision，逐欄位斷言投影輸出。
- **property-based**：驗三道閘（步數 ≤24 / 無環 / 非空）必 raise。
- **一致性稽核器對抗案例（必含三類）**：謊報縮圖 / 刪邊加邊 / 縮窗自洽。
- **Rule 9 非空殼證明**：每測配一個「故意漂移必 FAIL」案例，確保測試能在業務邏輯變動時失敗。

### 9.5 Phase 0 Spike 驗證結果（2026-06-25，掌舵者指示優先驗 SDK executor）

掌舵者選擇先對「`SdkExecutorAdapter` 替換 `PtyExecutor`」（本評估首選整合）做隔離 worktree 丟棄式 spike，回答三個 make-or-break 問題。實裝 `claude-agent-sdk==0.2.110`（Python 3.11.9）親讀套件原始碼 + 主 agent 獨立複核：

| 問題 | 燈號 | 實證（已複核） |
|------|------|---------------|
| **Q1 Token Guard 相容** | 🟡 | `ClaudeAgentOptions` 無直接 `disable_compact` 欄，但 `env` + `extra_args` 注入管道**確認存在**（可透傳任意 CLI flag/env）；另有 `get_context_usage().percentage` 可餵 TokenGuardPlugin（比 PTY 解析更精準）。**唯一待辦**：autocompact 關閉旗標的確切名稱需活體 CLI 確認（本 spike 環境無外網）。 |
| **Q2 權限可控** | 🟢 | `permission_mode` 預設 = **`None`**（**修正本文件 §5.3 caveat②「預設 acceptEdits」之過度悲觀假設**）；`can_use_tool` 欄位存在（可接既有 `ToolInvocationAdapter` allowlist）；另有 `allowed_tools`/`disallowed_tools`。 |
| **Q3 零退化 + 依賴** | 🟢 | `claude-agent-sdk` 依賴僅 `anyio, mcp, sniffio`（**無 pydantic 直接依賴**）；`pip check` 乾淨；pydantic 維持 2.13.3 未降版。加入骨架 adapter 檔後：pytest 3326 passed/0 failed、lint-imports 8 kept/0 broken、LOC violations=0（adapter 未 wire 進 live path）。 |

**Spike 裁決：GO**（三題無紅燈）。**進 Phase 1 前唯一硬閘**：以活體 Claude Code CLI 確認 autocompact 關閉旗標確切名稱，並實測關閉後 AutoClaude 80%/90% Token Guard 維持權威、不被 SDK 自行壓縮搶先；若該旗標不存在或無法關，Q1 翻紅（撞掉形式化門檻），須先擋掉再往下。

> 註：spike 過程於全域 pyenv 環境（`3.11.9/site-packages`）裝入 `claude-agent-sdk`（site-packages 層、非 repo 檔，不影響 main 測試；Phase 1 本就需要，故保留）。worktree 與丟棄式骨架已清理。

---

## 10. 附錄

### 附錄 A：節點描述 JSON Schema 完整範例

```json
{
  "schema_version": "1.0",
  "source_route": "B",
  "goal_hash": "sha256:9f2c…",
  "topology_digest": "sha256:4ab1…",
  "canonical_graph_digest": "sha256:7de0…",
  "node_count": 12,
  "truncated": false,
  "nodes": [
    {
      "identity": {
        "node_id": "STEP-003",
        "title": "實作 OrderService.create",
        "description": "依凍結 OpenAPI 契約實作建立訂單端點，回傳 201 與 Location header"
      },
      "traceability": {
        "source_prd_ref": "AC-ORDER-007",
        "spec_path": "docs/03_contract/order_api.frozen.yaml",
        "dependencies": ["STEP-001", "STEP-002"],
        "can_parallel": false,
        "topo_rank": 2
      },
      "approval": {
        "scg_gate": "SCG-4",
        "evaluator": {
          "evaluator_command": "pytest tests/order/test_create.py -q",
          "max_retries": 3
        },
        "status": "PENDING",
        "weak_regex_flag": false,
        "decomposition_reason": null,
        "auto_signoff_note": null
      }
    },
    {
      "identity": {
        "node_id": "STEP-004",
        "title": "撰寫整合測試（自由 PRD 拆出）",
        "description": "PRD 要求對外部金流做整合驗證"
      },
      "traceability": {
        "source_prd_ref": null,
        "spec_path": null,
        "dependencies": ["STEP-003"],
        "can_parallel": false,
        "topo_rank": 3
      },
      "approval": {
        "scg_gate": null,
        "evaluator": null,
        "status": "PENDING",
        "weak_regex_flag": true,
        "decomposition_reason": "PRD 第 4 節要求金流整合驗證；無凍結 AC，由 Brain 拆出",
        "auto_signoff_note": "IGoalFreezeGate: PENDING_HUMAN_SIGNOFF"
      }
    }
  ]
}
```

> 說明：`STEP-004` 為路線 A（自由 PRD）節點，無 AC/AT/SCG → `source_prd_ref` / `scg_gate` / `evaluator` 誠實填 `null`，並以 `decomposition_reason` 記錄拆解理由、`auto_signoff_note` 記錄 freeze gate verdict（不偽造合規）。

### 附錄 B：關鍵檔案路徑（已實地核對）

| 用途 | 絕對路徑 |
|------|---------|
| IExecutor port（SDK 接點） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\core\ports\executor.py` |
| 待替換的 PtyExecutor | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\infra\adapters\pty_executor.py` |
| 安全閘（can_use_tool 重用） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\infra\adapters\tool_invocation_adapter.py` |
| Thin facade（不動） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\execution\playbook_runner.py` |
| 路線 A：GoalDecomposer | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\execution\goal_decomposer.py` |
| 路線 B：SddToPlaybookAdapter | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\infra\adapters\sdd_to_playbook_adapter.py` |
| DecompositionStep.depends_on（邊來源） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\models\decision.py` |
| PlaybookTask（無 depends_on、有 weak_regex） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\models\playbook.py` |
| goal_freeze_gate port | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\core\ports\goal_freeze_gate.py` |
| rtm_sink port（諮詢報告） | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\core\ports\rtm_sink.py` |
| topology_dashboard port | `d:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\core\ports\topology_dashboard.py` |
| 渲染模式來源（復用模式不復用本體） | `AISDLC_SDD/AISDLC_SDD_v0.26/.../render_topology_dashboard.py` |

### 附錄 C：查證來源

- 八份專家分析（Architect / SA / SD / QA × 2 輪 zero-trust）收斂結論。
- 現況程式碼實地核對（2026-06-25）：`autoclaude/core/ports/` 18 個 port 模組、`PlaybookTask` 無 `depends_on`、`SpecContract.scg_gate`、`SddToPlaybookAdapter._assert_frozen`、`GoalDecomposer`、`weak_regex` 旗標鏈。
- 根 CLAUDE.md 三軌定義；MEMORY.md ConsoleUI 規劃與紅線。

---

*本文件為架構評估，非實作授權。任何程式碼變更須另經 ConsoleUI SCG-1/2 架構草案與掌舵者 signoff。*
