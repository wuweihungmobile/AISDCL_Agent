# AISDLC 專案文檔產出規範
# AISDLC Project Documentation Standards

> **🎯 適用對象**: 所有使用 AISDLC 框架的專案團隊
> **📖 適用情境**: 九種開發情境的文檔產出與管理

---

**版本**: v0.01
**最後更新**: 2026-01-10
**文檔類型**: 使用者指南 | 文檔標準
**維護者**: AISDLC Framework Team

---

## 🎯 文檔目的

本規範定義 AISDLC 框架在專案中的**文檔產出位置、命名格式、分類管理**標準，確保：
1. ✅ 文檔輸出位置統一且易於查找
2. ✅ 命名格式一致且語義清晰
3. ✅ 版本控制友好且易於追蹤
4. ✅ 團隊協作無縫且溝通順暢

---

## 📚 目錄

- [文檔目錄結構](#文檔目錄結構)
- [文檔命名規範](#文檔命名規範)
- [文檔分類與用途](#文檔分類與用途)
- [文檔元數據標準](#文檔元數據標準)
- [九種情境專屬規範](#九種情境專屬規範)
- [常見問題](#常見問題)

---

## 📂 文檔目錄結構

### 標準目錄規範（SDD 版 v0.01）

**🔴 重要觀念**: AISDLC-SDD v0.01 採用規格先行（Spec-First）原則，`docs/` 目錄結構反映 SDD 8 層文件分類，每一層對應特定的 SCG 閘門文件產出。

所有使用 AISDLC-SDD v0.01 的專案應遵循以下目錄結構：

```
AISDLC_SDD_v0.01/                         # 工作目錄（框架即專案目錄）
├── AISDLC_SDD_INIT.md                # 框架初始化文件
├── CLAUDE.md                         # Claude Code 專案指引
│
├── docs/                             # 📋 專案文檔輸出目錄（核心）— SDD 8 層結構
│   ├── README.md                     # 文檔導覽（建議）
│   │
│   ├── 01_requirements/              # 需求文檔目錄（SCG-0 產出）
│   │   ├── PRD_{ProjectName}.md      # Product Requirements Document
│   │   ├── FRD_{ModuleName}.md       # Functional Requirements Document
│   │   ├── Invariant_Spec.md         # Business Invariants（Refactoring 必用）
│   │   └── ThirdParty_API_Research.md# Third-Party API 研究（Integration 必用）
│   │
│   ├── 02_architecture/              # 架構設計目錄（SCG-1/SCG-2 產出）
│   │   ├── SRD_{SystemName}.md       # System Requirements Document（SCG-1）
│   │   ├── C4_Model_{SystemName}.md  # C4 架構圖（SCG-2）
│   │   ├── AS-IS-SRD_{SystemName}.md # As-Is 系統現狀（Brownfield/Migration）
│   │   ├── TO-BE-SRD_{SystemName}.md # To-Be 系統設計
│   │   ├── Trust_Boundary_Map.md     # 信任邊界圖（Security 必用）
│   │   ├── adr/                      # Architecture Decision Records
│   │   │   └── ADR-{NNN}-{kebab-title}.md
│   │   └── api/                      # API 規格（SCG-3 Contract Freeze）
│   │       ├── OpenAPI_{Module}.yaml # OpenAPI 3.1 Contract（凍結後才開發後端）
│   │       ├── API_Compat_{Module}.md# API 相容性聲明
│   │       └── Consumer_Contract_{Service}.md # Consumer-Driven Contract
│   │
│   ├── 03_testing/                   # 測試文檔目錄（SCG-4/SCG-5 產出）
│   │   ├── RTM_{ProjectName}.md      # Requirements Traceability Matrix（SCG-5 必用）
│   │   ├── Test_Plan_{TestType}.md   # Test Plan
│   │   ├── Test_Strategy.md          # Test Strategy Document
│   │   ├── Defect_Classification.md  # 缺陷分類規則
│   │   └── contracts/                # Contract Testing 規格（SDD 新增 L3）
│   │       ├── Invariant_Test_Contract.md    # Business Invariant 測試契約
│   │       ├── Contract_Test_Spec.md         # Contract 測試規格
│   │       └── Chaos_Contract.md             # Chaos 測試契約
│   │
│   ├── 04_planning/                  # 專案規劃目錄
│   │   ├── Gap_Analysis_{SystemName}.md  # Gap Analysis（Brownfield/Refactoring）
│   │   ├── Refactor_Plan.md              # 重構計畫（Refactoring）
│   │   └── performance/                  # 效能規格
│   │       └── PBS_{SystemName}.md       # Performance Baseline Spec（PBS Gate）
│   │
│   ├── 05_development/               # 開發執行目錄
│   │   └── Living_Doc_Strategy.md    # Living Documentation 策略
│   │
│   ├── 06_quality/                   # 品質文檔目錄
│   │   ├── Code_Quality_Baseline.md  # 代碼品質基準線
│   │   ├── Tech_Debt_Spec.md         # 技術債規格化（TD-XXX，Brownfield 必用）
│   │   └── security/                 # 安全文檔（Security 情境）
│   │       ├── SAD_{SystemName}.md   # Security Architecture Document
│   │       ├── STRIDE_{SystemName}.md# STRIDE 威脅建模
│   │       ├── Compliance_Matrix.md  # 合規對照表
│   │       └── Asset_Inventory.md    # 資產清單
│   │
│   ├── 07_design/                    # 設計文檔目錄
│   │   ├── UI_UX_{FeatureName}.md    # UI/UX 設計規格
│   │   └── Database_Schema_v{N}.md   # 資料庫設計
│   │
│   └── 08_deployment/                # 部署維運目錄（SCG-6 產出）
│       ├── CICD_Pipeline_Spec.md     # CI/CD Pipeline 規格
│       ├── Monitoring_Alert_Spec.md  # 監控告警規格
│       ├── Release_Notes_v{N}.md     # Release Notes
│       ├── Runbook.md                # 操作手冊
│       ├── Cutover_Plan.md           # 切換計畫（Migration 必用）
│       └── iac/                      # Infrastructure as Code 規格
│           └── IaC_Spec_{Module}.md
│
├── agent/                            # Agent 配置（21 個）
├── workflow/                         # Workflow 定義（23 個）
├── scenarios/                        # 十大情境 SOP
├── docs_template/                    # SDD 文檔模板（51+ 個，使用前複製到 docs/）
├── tools/                            # 工具腳本
└── ...
```

### 目錄層級說明（SDD v0.01）

| 層級 | 目錄 | SCG 對應 | 必要性 | 主要文件類型 |
|------|------|---------|-------|------------|
| **必須** | `docs/01_requirements/` | SCG-0 | 🔴 必須建立 | PRD / FRD / Invariant Spec / Third-Party API Research |
| **必須** | `docs/02_architecture/` | SCG-1/SCG-2 | 🔴 必須建立 | SRD / C4 / ADR / As-Is / Trust Boundary Map |
| **必須** | `docs/02_architecture/adr/` | SCG-2 | 🔴 必須建立 | ADR-{NNN} 架構決策記錄 |
| **必須** | `docs/02_architecture/api/` | SCG-3 | 🔴 必須建立 | OpenAPI 3.1 Contract / Consumer Contract |
| **必須** | `docs/03_testing/` | SCG-4/SCG-5 | 🔴 必須建立 | RTM / Test Plan / Test Strategy |
| **必須** | `docs/03_testing/contracts/` | SCG-4/SCG-5 | 🔴 必須建立（SDD 新增）| Invariant Test Contract / Contract Test Spec |
| **建議** | `docs/04_planning/` | - | 🟡 建議建立 | Gap Analysis / Refactor Plan |
| **建議** | `docs/04_planning/performance/` | PBS Gate | 🟡 效能情境必用 | PBS（Performance Baseline Spec） |
| **建議** | `docs/05_development/` | - | 🟡 建議建立 | Living Doc Strategy |
| **建議** | `docs/06_quality/` | - | 🟡 建議建立 | Code Quality Baseline / Tech Debt Spec |
| **建議** | `docs/06_quality/security/` | SCG-5 | 🟡 Security 情境必用 | SAD / STRIDE / Compliance Matrix |
| **選用** | `docs/07_design/` | - | 🟢 選用 | UI/UX / Database Design |
| **選用** | `docs/08_deployment/` | SCG-6 | 🟢 DevOps 情境必用 | CI/CD Pipeline / Release Notes / Runbook |
| **選用** | `docs/08_deployment/iac/` | SCG-6 | 🟢 選用 | IaC Specifications |

> **注意**: 使用 SDD 文件模板時，從 `AISDLC_SDD_v0.01/docs_template/sdd/` 取得對應模板複製到 `docs/` 後填寫，**不可直接修改模板本身**。

---

## 🏷️ 文檔命名規範

### 通用命名原則

1. **使用 PascalCase 或 Snake_Case**
   - ✅ 推薦: `PRD_MoneyTracker_Pro.md`, `Sprint_1_Execution_Plan.md`
   - ❌ 避免: `專案需求.md`, `sprint1.md`

2. **包含文檔類型前綴**
   - 格式: `{DOCTYPE}_{DESCRIPTIVE_NAME}.md`
   - 範例: `PRD_`, `FRD_`, `SRD_`, `API_`, `AT_`, `Sprint_`

3. **使用英文命名**
   - 原因: Git 友好、跨平台相容、易於搜尋
   - 例外: 專有名詞可保留原文（如產品名稱）

4. **模組化命名**
   - 大型專案: 按模組拆分文檔
   - 範例: `FRD_Core_Transaction_Module.md`, `FRD_User_Management_Module.md`

### 各類文檔命名格式

#### 1. 需求文檔 (`docs/requirements/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| PRD | `PRD_{PROJECT_NAME}.md` | `PRD_MoneyTracker_Pro.md` |
| FRD | `FRD_{MODULE_NAME}.md` | `FRD_Core_Transaction_Module.md` |
| User Stories | `Epic_UserStory_Backlog.md` | `Epic_UserStory_Backlog.md` |
| MVP Definition | `MVP_Definition_{PROJECT}.md` | `MVP_Definition_eCommerce_Platform.md` |

#### 2. 架構設計 (`docs/architecture/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| SRD | `SRD_{MODULE_NAME}.md` | `SRD_System_Architecture.md` |
| API Specification | `API_Specification_{ENDPOINT}.md` | `API_Specification_Cloud_Sync.md` |
| Architecture Design | `Architecture_Design_Document.md` | `Architecture_Design_Document.md` |
| Database Schema | `Database_Schema_{VERSION}.md` | `Database_Schema_v1.0.md` |

#### 3. 測試文檔 (`docs/testing/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| Test Plan | `Test_Plan_{TEST_TYPE}.md` | `Test_Plan_Acceptance_Testing.md` |
| Acceptance Test | `AT_{MODULE_NAME}.md` | `AT_Core_Transaction_Module.md` |
| Test Report | `Test_Report_{SPRINT/PHASE}.md` | `Test_Report_Sprint_1.md` |
| QA Review | `QA_{REVIEW_TYPE}_{MODULE}.md` | `QA_Acceptance_Criteria_Review.md` |

#### 4. 專案規劃 (`docs/planning/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| Effort Estimation | `Effort_Estimation_Resource_Planning.md` | `Effort_Estimation_Resource_Planning.md` |
| Sprint Plan | `Sprint_{N}_Execution_Plan.md` | `Sprint_1_Execution_Plan.md` |
| Sprint Report | `Sprint_{N}_Final_Report.md` | `Sprint_1_Final_Report.md` |
| Kickoff Meeting | `Sprint_{N}_Kickoff_Meeting.md` | `Sprint_1_Kickoff_Meeting.md` |

#### 5. 執行報告 (`docs/reports/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| Phase Report | `{PHASE_NAME}_REPORT.md` | `UPGRADE_COMPLETION_REPORT.md` |
| Analysis Report | `{ANALYSIS_TOPIC}_{TYPE}.md` | `Performance_Analysis_Report.md` |
| Verification Report | `{VERIFICATION_TOPIC}_REPORT.md` | `Document_Consistency_Report.md` |

#### 6. 變更日誌 (`docs/logs/`)

| 文檔類型 | 命名格式 | 範例 |
|---------|---------|------|
| CHANGELOG | `CHANGELOG.md` | `CHANGELOG.md` |
| Decision Log | `Decision_Log_{TOPIC}.md` | `Decision_Log_Architecture.md` |

---

## 📋 文檔分類與用途

### 分類 1: 核心需求文檔

**目的**: 定義「做什麼」（What to build）

| 文檔類型 | 負責角色 | 產出階段 | 追溯關係 |
|---------|---------|---------|---------|
| **PRD** (Product Requirements Document) | PM/PO | AISDLC Stage 1-2 | → FRD |
| **FRD** (Functional Requirements Document) | SA + BA | AISDLC Stage 3-4 | PRD → FRD → SRD |
| **Epic & User Stories** | PM/PO + SA | AISDLC Stage 4-5 | PRD → EPIC → US → AC |

**輸出位置**: `docs/requirements/`

**關鍵內容**:
- PRD: 產品願景、目標使用者、核心功能、成功指標
- FRD: 功能詳細規格、業務流程、UI/UX 需求、資料需求
- User Stories: Epic 分解、User Story、Acceptance Criteria

---

### 分類 2: 技術設計文檔

**目的**: 定義「怎麼做」（How to build）

| 文檔類型 | 負責角色 | 產出階段 | 追溯關係 |
|---------|---------|---------|---------|
| **SRD** (System Requirements Document) | SD-Architect | AISDLC Stage 6-7 | FRD → SRD |
| **API Specification** | SD-Architect + QA | AISDLC Stage 7 | SRD → API Spec |
| **Architecture Design** | SD-Architect | AISDLC Stage 6 | - |

**輸出位置**: `docs/architecture/`

**關鍵內容**:
- SRD: 技術架構、系統元件、資料流程、非功能需求
- API Spec: 端點定義、請求/回應格式、錯誤處理、認證授權
- Architecture Design: C4 Model 圖表、技術選型、部署架構

---

### 分類 3: 測試與品質文檔

**目的**: 定義「如何驗證」（How to verify）

| 文檔類型 | 負責角色 | 產出階段 | 追溯關係 |
|---------|---------|---------|---------|
| **Test Plan** | QA Lead | AISDLC Stage 8 | US → TC |
| **Acceptance Test (AT)** | QA + SA | AISDLC Stage 9 | AC → AT |
| **Test Report** | QA | 實施階段 | AT → Test Report |

**輸出位置**: `docs/testing/`

**關鍵內容**:
- Test Plan: 測試策略、測試範圍、測試環境、資源分配
- AT: 驗收準則、測試步驟、預期結果、實際結果
- Test Report: 測試覆蓋率、缺陷統計、品質評估

---

### 分類 4: 專案管理文檔

**目的**: 定義「時程與資源」（When & Who）

| 文檔類型 | 負責角色 | 產出階段 | 追溯關係 |
|---------|---------|---------|---------|
| **Effort Estimation** | PM + Tech Lead | AISDLC Stage 5 | US → Story Points → Sprint |
| **Sprint Plan** | PM + Scrum Master | Sprint Planning | Sprint Backlog → Tasks |
| **Sprint Report** | PM + QA Lead | Sprint Review | Sprint Plan → Sprint Report |

**輸出位置**: `docs/planning/`

**關鍵內容**:
- Effort Estimation: Story Points、工時估算、資源分配、風險評估
- Sprint Plan: Sprint 目標、User Stories、任務分配、時程規劃
- Sprint Report: 完成度、燃盡圖、問題與風險、下一步行動

---

## 📝 文檔元數據標準

### 必要元數據

每個文檔應包含以下標準元數據（置於文檔開頭或結尾）:

```markdown
## 文檔元數據
- **專案名稱**: [專案名稱]
- **文檔類型**: [PRD/FRD/SRD/API/AT/...]
- **文檔版本**: v1.0
- **建立日期**: YYYY-MM-DD
- **最後更新**: YYYY-MM-DD
- **負責人**: [姓名 (角色)]
- **文檔狀態**: [Draft/Review/Final/Archived]
- **追溯編號**: [US-XXX, EPIC-XXX, F-XXX, etc.]
```

### 文檔狀態定義

| 狀態 | 說明 | 允許修改 | 允許交付 |
|------|------|---------|---------|
| **Draft** | 草稿階段，內容未完成 | ✅ | ❌ |
| **Review** | 評審階段，等待 Stakeholder 審核 | ✅ (限負責人) | ❌ |
| **Final** | 最終版本，已通過審核 | ❌ (需變更管理) | ✅ |
| **Archived** | 已歸檔，不再使用（舊版本文檔） | ❌ | ❌ |

### 追溯編號規範

使用 AISDLC ID 命名規範（詳見 [AISDLC_ID_Naming_Convention.md](../../system/naming/AISDLC_ID_Naming_Convention.md)）:

- **Epic**: `EPIC-XXX`
- **User Story**: `US-XXX`
- **Acceptance Criteria**: `AC-XXX-Y`
- **Acceptance Test**: `AT-XXX-Y-Z`
- **API**: `API-XXX`
- **Test Case**: `TC-XXX-Y-Z`
- **Bug**: `BUG-XXX`

---

## 🎯 九種情境專屬規範

### 1. Greenfield（新專案開發）

**額外目錄**:
```
docs/planning/sprints/       # Sprint 計劃
docs/requirements/mvp/       # MVP 定義
```

**必要文檔**:
- ✅ PRD (Product Requirements Document)
- ✅ FRD (所有核心模組)
- ✅ Epic & User Story Backlog
- ✅ SRD (System Architecture)
- ✅ Effort Estimation & Resource Planning

**推薦工具**:
- 72 個標準確認問題 (scenarios/greenfield/checklists/Standard_Confirmation_Questions.md)
- 120 項完整性檢查清單 (scenarios/greenfield/checklists/Completeness_Checklist.md)

---

### 2. Brownfield（舊專案維護）

**額外目錄**:
```
docs/analysis/codebase/      # 現有系統分析
docs/analysis/legacy_system/ # Legacy 系統文檔
docs/migration/              # 遷移計劃
```

**必要文檔**:
- ✅ Legacy System Analysis Report
- ✅ Code Audit Report
- ✅ FRD (變更需求)
- ✅ Migration Plan

---

### 3. Refactoring（系統重構）

**額外目錄**:
```
docs/refactoring/before/     # 重構前狀態
docs/refactoring/after/      # 重構後狀態
docs/refactoring/migration_plan/  # 遷移計劃
```

**必要文檔**:
- ✅ Refactoring Plan
- ✅ Code Quality Report (Before/After)
- ✅ Test Coverage Report

---

### 4. Integration（第三方整合）

**額外目錄**:
```
docs/integration/api_research/       # API 研究
docs/integration/authentication/     # 認證設計
docs/integration/data_mapping/       # 資料轉換
```

**必要文檔**:
- ✅ API Specification (第三方 API)
- ✅ Integration Test Plan
- ✅ Data Mapping Document

---

### 5. Performance（效能優化）

**額外目錄**:
```
docs/performance/baseline/   # 效能基準
docs/performance/profiling/  # 效能分析
docs/performance/optimization/  # 優化計劃
```

**必要文檔**:
- ✅ Performance Baseline Report
- ✅ Profiling Analysis Report
- ✅ Optimization Plan

---

### 6. Testing（測試策略）

**額外目錄**:
```
docs/testing/strategy/       # 測試策略
docs/testing/automation/     # 自動化測試
docs/testing/coverage/       # 測試覆蓋率
```

**必要文檔**:
- ✅ Test Strategy Document
- ✅ Test Automation Plan
- ✅ Test Coverage Report

---

### 7. Security（安全審查）

**額外目錄**:
```
docs/security/threat_model/  # 威脅模型
docs/security/vulnerability/ # 漏洞評估
docs/security/compliance/    # 合規檢查
```

**必要文檔**:
- ✅ Threat Model Document
- ✅ Security Checklist (OWASP Top 10)
- ✅ Vulnerability Assessment Report

---

### 8. DevOps（CI/CD 部署）

**額外目錄**:
```
docs/devops/pipeline/        # CI/CD Pipeline
docs/devops/infrastructure/  # 基礎設施
docs/devops/monitoring/      # 監控配置
```

**必要文檔**:
- ✅ CI/CD Pipeline Configuration
- ✅ Deployment Guide
- ✅ Infrastructure as Code (IaC) Documentation

---

### 9. Documentation（技術文檔）

**額外目錄**:
```
docs/documentation/api_docs/         # API 文檔
docs/documentation/user_guides/      # 使用者指南
docs/documentation/developer_guides/ # 開發者指南
```

**必要文檔**:
- ✅ Documentation Standards
- ✅ API Documentation (Swagger/OpenAPI)
- ✅ User Guide / Developer Guide

---

## ❓ 常見問題

### Q1: 專案文檔應該放在專案內還是單獨管理？

**A**: **建議放在專案內**（`docs/` 目錄）

**原因**:
- ✅ 文檔與程式碼同步，版本控制一致
- ✅ 易於追蹤變更歷史
- ✅ 團隊成員容易找到
- ✅ CI/CD 可自動產生文檔網站

**例外情況**:
- 🔄 多個 Repo 共享文檔（使用 Git Submodule）
- 🔄 大型文檔（UI 設計稿、影片）可使用外部連結

---

### Q2: 文檔應該用中文還是英文？

**A**: **文檔內容推薦中文，檔案命名推薦英文**

**原因**:
- 📝 內容中文: 團隊溝通效率高、理解無誤
- 🏷️ 命名英文: Git 友好、跨平台相容、易搜尋

**範例**:
```
✅ 推薦:
   檔名: PRD_MoneyTracker_Pro.md
   內容: 繁體中文

❌ 避免:
   檔名: 產品需求文檔.md
   內容: 中英混雜
```

---

### Q3: FILE_DIRECTORY_RULES.md 與本規範的關係？

**A**: **兩者層次不同，互補使用**

| 文檔 | 用途 | 適用範圍 |
|------|------|---------|
| **FILE_DIRECTORY_RULES.md** | AISDLC-SDD 框架完整目錄規則（框架層） | 框架本身的檔案配置與路徑規則 |
| **PROJECT_DOCUMENTATION_STANDARDS.md**（本文檔） | 使用 SDD 時的專案文件產出標準（專案層） | 所有使用 AISDLC-SDD 的專案文件管理 |

**使用方式**:
1. 查閱框架本身的目錄與路徑規則 → 閱讀 `FILE_DIRECTORY_RULES.md`
2. 新專案啟動時規劃文件目錄 → 參考本規範的 SDD 8 層目錄
3. 使用 SDD 模板 → 從 `docs_template/sdd/` 複製到 `docs/` 後填寫
4. 根據專案情境選擇性建立子目錄（保留核心必要層）

---

### Q4: 如何處理大型專案的文檔數量爆炸？

**A**: **按模組/階段分層管理**

**策略 1 - 按模組拆分**:
```
docs/requirements/frd/
├── FRD_Core_Transaction_Module.md
├── FRD_Account_Management_Module.md
├── FRD_Category_Management_Module.md
└── FRD_Dashboard_Analytics_Module.md
```

**策略 2 - 按階段歸檔**:
```
docs/planning/sprints/
├── active/                  # 進行中的 Sprint
│   └── sprint_5/
└── archive/                 # 已完成的 Sprint
    ├── sprint_1/
    ├── sprint_2/
    ├── sprint_3/
    └── sprint_4/
```

**策略 3 - 使用索引文檔**:
```markdown
# docs/README.md
## 文檔快速導航

### 需求文檔
- [PRD](requirements/prd/PRD_MoneyTracker_Pro.md)
- [FRD 清單](requirements/frd/README.md)

### 架構設計
- [SRD](architecture/srd/SRD_System_Architecture.md)
- [API 清單](architecture/api/README.md)
```

---

### Q5: 文檔版本如何管理？

**A**: **使用 Git + 文檔元數據**

**方式 1 - Git 版本控制（推薦）**:
```bash
# 每次文檔變更提交 Git
git add docs/requirements/PRD_MoneyTracker_Pro.md
git commit -m "docs: update PRD v1.2 - add cloud sync feature"
git tag docs-prd-v1.2
```

**方式 2 - 文檔元數據版本號**:
```markdown
## 文檔元數據
- **文檔版本**: v1.2
- **最後更新**: 2026-01-10
- **變更摘要**: 新增雲端同步功能需求
```

**方式 3 - 歷史版本歸檔**:
```
docs/requirements/prd/
├── PRD_MoneyTracker_Pro.md           # 最新版本
└── archive/
    ├── PRD_MoneyTracker_Pro_v1.0.md  # 歷史版本
    └── PRD_MoneyTracker_Pro_v1.1.md
```

---

## 📚 相關文檔

- [PROJECT_INITIALIZATION_GUIDE.md](../onboarding/PROJECT_INITIALIZATION_GUIDE.md) - 專案初始化指南
- [AISDLC_ID_Naming_Convention.md](../../system/naming/AISDLC_ID_Naming_Convention.md) - ID 命名規範
- [Document_Quality_Checklist.md](../../system/quality/Document_Quality_Checklist.md) - 文檔品質檢查清單
- [FILE_DIRECTORY_RULES.md](../../../FILE_DIRECTORY_RULES.md) - AISDLC-SDD 框架完整目錄規則
- [SDD_Core_Principles.md](../../system/sdd/SDD_Core_Principles.md) - SDD 三大支柱核心原則
- [SDD_SPEC_FIRST_GATE.md](../../../workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md) - SCG 閘門執行規範

---

**維護者**: AISDLC Framework Team
**最後更新**: 2026-01-10
**版本**: v0.01
