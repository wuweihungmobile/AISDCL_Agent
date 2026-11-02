# ResearchSOPtoPRD 來源規格（掌舵者 2026-11-02 原文；本檔為需求原文的逐字存檔，不是 PRD）

> 立案：掌舵者 2026-11-02 於互動視窗貼入（sid `245e80aa-71c4-443b-b8fe-d59f87a9f0e8`），原文指令：「請參考以下資訊協助設計開發新功能==> ResearchSOPtoPRD.prd，並“完美整合到目前專案功能中“」；授權句：「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案(不需要顧慮成本)，我授權幫我決策, 若真需要我決定, 請以最簡單的解釋, 讓我互動選項決策」；派工句：「若需要請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查,請確認以上功能都已經完備！」。
> 正式 PRD＝`docs/01_requirements/ResearchToPRD_PRD.md`；本檔只做追溯來源（PRD 每條需求回指本檔章節）。原文以下逐字保留（含原文的 `my-project/` 目錄名與英文術語）。

---

# ResearchSOPtoPRD.prd: 研究議題轉規格書與雙軌開發落地系統設計規範

本文件旨在為 Claude Code 提供完整、高保真且可執行的系統實作規格。系統統整多源深研檢索、規格工程化（PRD）、四方對抗式審查、雙軌分支決策與 AISDLC_SDD 自動化實作迴圈，並將整體生命週期封裝進 AgentConsoleUI 中。

---

## 1. 系統架構與設計哲學

### 1.1 核心原則：雙環漏斗模型（Two-Loop Funnel Model）

系統嚴格劃分「探索外環（Phase 0）」與「確定性內環（Phase 1~N）」，避免發散的研究雜訊污染程式碼生成的上下文：

1. **外環（Phase 0: 探索與規格工程）**：聚焦發散檢索、多源比對、結構化 PRD 撰寫與對抗式審核，產出確定性規格基準（Baseline）。
2. **Gate 0 守門員**：審查評分達標（Score $\ge$ 85）且經由人機協同決策（Human-in-the-Loop）批准，凍結為不可變規格。
3. **內環（Phase 1~N: 確定性 SDD 開發）**：規格嚴格唯讀。AutoClaude 依據 PRD 的驗收準則（AC）執行 TDD 生成、自癒迴圈（Self-healing Loop）與回歸驗證。若規格有重大瑕疵，必須發起 `Spec Change Request (SCR)` 退回 Phase 0，嚴禁實作漂移。

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AISDLC 全生命週期治理框架                         │
│                                                                        │
│  [Phase 0: 外環 - 探索與規格工程 (Exploration & Spec Engineering)]       │
│  研究議題 ──> 多源深度檢索 ──> 證據庫生成 ──> PRD 撰寫 ──> 對抗式審查     │
│                                                   │                    │
│                                            [Gate 0 守門員]             │
│                                                   ▼                    │
│  [分支路由: 專案分流精靈 (Branching Wizard)]                            │
│         ├── 軌道 A: 併入既有 AISDLC 模組                               │
│         └── 軌道 B: 初始化獨立全新專案 (Scaffold & GitHub Init)         │
│                                                   │                    │
│  [Phase 1~N: 內環 - 規格驅動開發 (Deterministic SDD Engine)]           │
│  架構拆解 ──> TDD 測試規格 ──> AutoClaude 寫 Code ──> 自癒迴圈 (Healing)│
│                                                   │                    │
│                                            [Gate 1 驗收]               │
│                                                   ▼                    │
│                                             正式交付 / 部署            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 目錄結構與元數據規範

無論是 Monorepo 模組或獨立專案，系統統一於根目錄下維護 `my-project/` 狀態儲存庫：

```text
my-project/
├── Project_01/
│   ├── 00_research/
│   │   ├── issue_scope.json          # 議題定義與檢索邊界
│   │   └── evidence_matrix.md        # 論文、開源 Repo、社群討論證據鏈
│   ├── 01_specs/
│   │   ├── PRD-v1.0.0.md             # 審批通過的不可變規格基準
│   │   └── adr_draft.md              # 架構決策記錄 (Architecture Decision Record)
│   ├── 02_governance/
│   │   ├── review_card.json          # 對抗式審查歷史評分與缺陷修訂紀錄
│   │   ├── route_decision.json       # 分支決策參數與專案型態
│   │   └── state.json                # 全域狀態機當前節點與上下文
│   └── 03_execution/
│       ├── task_decomposition.json   # 從 PRD 拆解出的原子任務清單
│       └── healing_history.log       # SDD 程式碼修復與自癒記錄
├── Project_02/                       # Project_02
└── Project_0x/                       # Project_0X
```

---

## 3. Phase 0: 深度研究與 PRD 規格工程詳細設計

### 3.1 多源深度研究引擎（Deep Research Engine）

針對研究議題啟動三維檢索，強制執行**防幻覺證據錨定（Evidence Grounding）**：

1. **學術與文獻層（Academic Layer）**：
* 介接 arXiv、Semantic Scholar 等 API，鎖定近 1–3 年論文。
* 提取論文之核心演算法、數學原理與實作邊界。

2. **產業前沿層（Industry & Enterprise Layer）**：
* 檢索頭部科技公司技術部落格（Engineering Blogs）、白皮書與技術專利。
* 評估工業級架構可行性與高可用度方案。

3. **開源與社群層（Open Source & Community Layer）**：
* 鎖定 GitHub 高 Star / 活躍維護之 Repo，分析 Issue/PR 討論焦點與授權條款（MIT/Apache 等）。
* 抓取 Reddit、Stack Overflow 開發者踩坑記錄。

4. **產出物**：生成 `my-project/00_research/evidence_matrix.md`，每項論點強制關聯引用來源（URL / DOI / Git Commit）。

### 3.2 標準 PRD Schema 規範

PRD 必須符合以下 Markdown 結構模板，不得省略區塊：

```markdown
# [PRD-ID] 專案 / 模組名稱產品規格書

## 1. 元數據 (Metadata)
- Version: v1.0.0
- Target Scope: AISDLC_MODULE | STANDALONE_PROJECT
- Associated Research: my-project/00_research/evidence_matrix.md

## 2. 問題定義與背景 (Problem Statement & Context)
- 現有業務痛點與量化指標。
- 研究依據：引用文獻與業界技術方案對比結論。

## 3. 功能性規格 (Functional Requirements)
- Epic -> Feature -> User Story 階層拆解。
- 每個 Feature 具備明確的邊界限制（Boundary Conditions）。

## 4. 驗收標準 (Acceptance Criteria - Gherkin)
- Scenario: [情境名稱]
  Given [前提條件]
  When [觸發動作]
  Then [預期結果與狀態變更]

## 5. 技術與資料架構 (Technical Architecture & Schemas)
- 模組資料模型（JSON Schema / DB Migration 定義）。
- API Interface 規格與 Sequence Diagram（Mermaid）。
- 外部相依性清單及其授權條款。

## 6. 非功能性需求 (Non-Functional Requirements - NFR)
- 效能標準：API P99 延遲、記憶體/CPU 預算。
- 資安與防護：驗證授權、輸入過濾、機密資料脫敏。
```

### 3.3 對抗式審查機制（Adversarial Review Engine）

由四組虛擬專家 Agent 進行獨立審核，產生評分卡（滿分 100 分）：

* **架構審查 Agent（Weight: 30%）**：檢核模組耦合度、第三方依賴維護風險、效能邊界。
* **產品/商業 Agent（Weight: 25%）**：檢核痛點是否具備商業價值、驗收指標是否可衡量。
* **QA/測試 Agent（Weight: 25%）**：檢核 User Story 是否存在模糊地帶、Given-When-Then 是否足以轉換為自動化測試、邊界案例（Edge Cases）覆蓋率。
* **資安/合規 Agent（Weight: 20%）**：檢核授權衝突、機密安全與注入風險。

**迭代判定邏輯**：

* 綜合得分 $\ge 85$：通過 Gate 0，解鎖 `BASELINE_APPROVED`。
* 綜合得分 $< 85$：輸出缺陷清單（Issue Backlog）至 `review_card.json`，AutoClaude 自動修訂 PRD，最多循環 3 次；若仍未通過則發出中斷警報由人工介入。

---

## 4. 專案分流與雙軌路徑規劃（Branching Wizard）

PRD 審批通過後，系統依據專案屬性提供雙軌路徑：

| 評估維度 | 軌道 A：併入 AISDLC 本體模組 | 軌道 B：初始化獨立全新專案 |
| --- | --- | --- |
| **目標場景** | 系統底層共用能力、Agent 工具鏈、工作流擴充 | 獨立商用產品、獨立技術棧、外部終端專案 |
| **路徑規劃** | 切入 Monorepo 的 `packages/` 或 `services/` | 建立全新資料夾或指定獨立工作目錄 |
| **Git 流程** | 自動建立 `feature/issue-<id>` 分支 | 執行 `git init`，設定 Remote Origin，推送 Initial Commit |
| **CI/CD 與環境** | 繼承既有 AISDLC 測試與 Token 治理管線 | 自動生成 GitHub Actions Workflow、Docker Compose 與環境設定檔 |
| **規格掛載** | 自動掛載至全域模組登錄表（Module Registry） | 將 `my-project/` 完整移至新專案根目錄 |

---

## 5. 系統狀態機定義（State Machine Definition）

系統整體狀態機及資料結構定義如下：

```json
{
  "system": "AISDLC_Research_to_Execution",
  "version": "1.0.0",
  "states": {
    "TOPIC_INGESTION": {
      "entry_action": "init_research_workspace",
      "next": "DEEP_RESEARCH",
      "required_input": ["topic", "scope", "depth_level"]
    },
    "DEEP_RESEARCH": {
      "agent": "ResearchAgent",
      "output": "my-project/00_research/evidence_matrix.md",
      "next": "PRD_DRAFTING"
    },
    "PRD_DRAFTING": {
      "agent": "SpecEngineerAgent",
      "output": "my-project/01_specs/PRD_draft.md",
      "next": "ADVERSARIAL_REVIEW"
    },
    "ADVERSARIAL_REVIEW": {
      "agent": "ReviewCommitteeAgents",
      "output": "my-project/02_governance/review_card.json",
      "transitions": {
        "score_ge_85": "BASELINE_APPROVAL",
        "score_lt_85_retry_le_3": "PRD_DRAFTING",
        "score_lt_85_retry_gt_3": "HUMAN_ESCALATION"
      }
    },
    "BASELINE_APPROVAL": {
      "gate": "Gate_0",
      "trigger": "User_Manual_Signoff",
      "output": "my-project/01_specs/PRD-v1.0.0.md",
      "next": "BRANCHING_ROUTER"
    },
    "BRANCHING_ROUTER": {
      "wizard": "BranchingWizard",
      "output": "my-project/02_governance/route_decision.json",
      "branches": {
        "INTEGRATE_AISDLC": "AISDLC_FEATURE_SETUP",
        "STANDALONE_PROJECT": "STANDALONE_SCAFFOLD_SETUP"
      }
    },
    "AISDLC_FEATURE_SETUP": {
      "action": "git_checkout_feature_branch",
      "next": "SDD_TASK_DECOMPOSITION"
    },
    "STANDALONE_SCAFFOLD_SETUP": {
      "action": "init_repo_and_github_remote",
      "next": "SDD_TASK_DECOMPOSITION"
    },
    "SDD_TASK_DECOMPOSITION": {
      "agent": "ArchitectAgent",
      "output": "my-project/03_execution/task_decomposition.json",
      "next": "SDD_TDD_GENERATION"
    },
    "SDD_TDD_GENERATION": {
      "agent": "QAAgent",
      "action": "generate_failing_tests_from_ac",
      "next": "SDD_CODE_IMPLEMENTATION"
    },
    "SDD_CODE_IMPLEMENTATION": {
      "agent": "AutoClaudeCoder",
      "action": "implement_source_code",
      "next": "SDD_SELF_HEALING_LOOP"
    },
    "SDD_SELF_HEALING_LOOP": {
      "agent": "AutoClaudeFixer",
      "action": "run_test_suite_and_heal",
      "transitions": {
        "tests_passed": "SDD_REGRESSION_VERIFIED",
        "healing_failed_exceed_limit": "HUMAN_ESCALATION"
      }
    },
    "SDD_REGRESSION_VERIFIED": {
      "gate": "Gate_1",
      "output": "traceability_matrix.json",
      "next": "PROJECT_DELIVERED"
    },
    "PROJECT_DELIVERED": {
      "action": "create_git_tag_and_release",
      "final": true
    }
  }
}
```

---

## 6. AgentConsoleUI 介面編排與使用體驗

全站介面採單一工作流導覽架構，避免頁面跳轉破碎與卡頓：

### 6.1 導覽架構與全域佈局

* **頂部全域狀態列（Header）**：
* 專案與模組切換下拉選單（Scope Selector）。
* AutoClaude 狀態指示燈（Idle / Running / Healing / Escalated）。
* 即時 Token 消耗速率與預算儀表板。

* **左側主導覽列（Sidebar）**：
1. `探索與研究 (Research)`
2. `規格工程 (PRD Studio)`
3. `分流精靈 (Branching Hub)`
4. `SDD 執行看板 (Execution Kanban)`
5. `終端與驗證日誌 (Terminal & Logs)`

### 6.2 頁面詳細規範

#### 頁面 1：研究探索工作區（Research & Ingestion View）

* **介面組件**：
* 議題輸入面板：支援輸入研究命題、目標技術棧、檢索深度開關（論文 / 官方文獻 / 開源 Repo）。
* 證據鏈即時動態欄：以時間軸串流輸出 arXiv 抓取結果、GitHub 活躍度指標與技術優缺點矩陣。
* 主動作按鈕：點擊 `[啟動深研]`；完成後觸發 `[生成 PRD 初稿 ->]` 自動跳轉至 PRD Studio。

#### 頁面 2：PRD 工作室與對抗式審查（PRD Studio & Gate 0）

* **介面組件**：
* **左欄（目錄樹）**：導航 PRD 章節（痛點、FR、Gherkin AC、NFR、架構）。
* **中欄（PRD 即時編輯器）**：支援 Markdown 語法高亮、Diff 比對模式與 Mermaid 架構圖即時渲染。
* **右欄（Gatekeeper 審批面板）**：
* 四方雷達評分圖（架構、商業、QA、資安）。
* 缺陷清單與修訂建議卡片。

* **動作按鈕**：
* 分數 $< 85$：顯示 `[一鍵自動迭代修正 (AutoClaude)]`。
* 分數 $\ge 85$：解鎖綠色按鈕 `[核准 PRD (Approve Baseline) ->]`。

#### 頁面 3：專案分流引導精靈（Branching & Scaffolding Wizard）

* **介面組件**：
* 點擊核准後滑出 Drawer 引導抽屜，提供雙軌卡片選擇：
* **卡片 A（併入 AISDLC）**：顯示目標分支名稱、Monorepo 掛載路徑，點擊確認自動建立分支。
* **卡片 B（獨立專案）**：輸入新專案名稱、技術棧範本、GitHub 儲存庫設定（Public/Private），點擊確認自動完成 `git init`、產生 CI/CD 與初始化 Commit。

* 完成後畫面彈出成功提示，並自動將上下文載入 SDD 看板。

#### 頁面 4：AISDLC_SDD 執行監控看板（Execution Kanban & Self-healing）

* **介面組件**：
* **階段狀態看板**：Task 拆解 -> 測試規格產生 -> 程式碼實作 -> 自癒修復 -> 回歸驗收。
* **自癒監視器（Self-healing Tracker）**：視覺化顯示測試失敗日誌、AutoClaude 歸因分析與補丁修復嘗試次數。
* **即時終端窗格（Terminal View）**：以 WebSocket 串流輸出背景命令列日誌，支援最小化/展開。
* **人機協同決策彈窗（Human Intervention Modal）**：當自癒超出上限或面臨重大架構選擇時彈出，確保開發不失控。

#### 頁面 5：交付驗收與歸檔（Release & Delivery View）

* **介面組件**：
* 規格追溯性矩陣（Traceability Table）：檢視每條 PRD User Story 與 Gherkin AC 對應的單元測試與端到端測試通過狀態。
* 發布動作列：`[建立 Release Tag]`、`[開啟本地專案]`、`[檢視 GitHub PR]`。

---
