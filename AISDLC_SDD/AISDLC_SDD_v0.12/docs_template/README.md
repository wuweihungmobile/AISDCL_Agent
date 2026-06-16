# AISDLC-SDD 文檔模板總覽
# AISDLC-SDD Document Templates Overview

**版本**: v0.01-SDD
**最後更新**: 2026-06-02
**維護狀態**: Active
**SDD 轉型狀態**: ✅ 完成（新增 sdd/ 目錄，含 59 個 SDD 專屬模板）

---

## 📋 目錄結構 (Directory Structure)

```
docs_template/
├── sdd/                     # 🆕 SDD 專屬模板（59 個：56 md + 3 yaml）
│   ├── requirements/        # 需求類（5 個）：INVARIANT-SPEC、THIRD-PARTY-API-RESEARCH、AMBIGUITY-SCORER-SPEC、AMBIGUITY-WAIVER、SPEC-PATCH
│   ├── architecture/        # 架構類（13 個）：AS-IS/TO-BE-SRD、SAD、ADR 相關、Migration 相關、PATH-COST-MODEL-SPEC、SPEC-ANCHOR 等
│   ├── adr/                 # ADR 類（4 個）：ADR-INDEX、ADR-TEMPLATE、Automation/Performance ADR
│   ├── api/                 # API 類（4 個：1 md + 3 yaml）：API-COMPAT + 3 Contract YAML
│   ├── testing/             # 測試類（19 個）：RTM、STRIDE、Contract Test、Performance Baseline、TEST-CONTRACT-NEGOTIATION 等
│   ├── planning/            # 規劃類（2 個）：GAP-ANALYSIS、REFACTOR-PLAN
│   ├── quality/             # 品質類（3 個）：CODE-QUALITY-BASELINE、TECH-DEBT-SPEC、PBS-DRIFT-REPORT
│   ├── development/         # 開發類（1 個）：LIVING-DOC-STRATEGY
│   ├── deployment/          # 部署類（7 個）：CANARY-SPEC、CUTOVER-SPEC、INCIDENT-RESPONSE-SPEC 等
│   └── build/               # 建置類（1 個）：SDD_ABORT_REPORT（ESCALATION 中止報告）
├── core/                    # 核心文檔模板（所有情境通用）
│   ├── prd/                # 產品需求文件 (Product Requirements Document)
│   ├── frd/                # 功能需求文件 (Functional Requirements Document)
│   ├── srd/                # 系統需求文件 (System Requirements Document)
│   ├── api/                # API 規格文件
│   └── tests/              # 測試文件
├── support/                # 支援文件模板（流程記錄、報告）
│   ├── Requirement_Extraction_Report_Template.md  # 需求提取報告
│   ├── Collaboration_Log_Template.md              # 人機協作記錄
│   ├── Tech_Stack_Selection_Report_Template.md    # 技術選型報告
│   ├── monitoring/         # 監控相關文件
│   └── operations/         # 營運相關文件
└── scenario_specific/      # 情境專屬模板（特定情境使用）
    ├── analysis/          # 分析情境
    ├── documentation/     # 文件情境
    ├── testing/           # 測試情境
    ├── integration/       # 整合情境
    ├── performance/       # 效能情境
    └── devops/            # DevOps 情境
        ├── CICD_Pipeline_Template.md            # CI/CD Pipeline 標準配置
        ├── Layer0_Security_Baseline_Template.md  # 🔒 Layer 0 安全基線（所有情境強制）
        ├── Layer1_Build_Verify_Template.md       # 🔨 Layer 1 建置驗證（所有情境強制）
        ├── Migration_Pipeline_Template.md       # 🔄 Migration 專屬 Pipeline (Canary+Rollback)
        ├── Security_Scan_Integration_Template.md # 🛡️ P1 增強安全掃描整合 (SAST/Container/DAST)
        ├── Performance_Benchmark_Gate_Template.md # ⚡ P2 效能基準關卡 (Micro-Benchmark/Load Test)
        ├── Documentation_Pipeline_Template.md   # 📝 P2 文檔 Pipeline (Doc Lint/Link Check/Deploy)
        ├── Event_Driven_Agent_Notification_Template.md # 🔔 P3 事件驅動 Agent 通知
        ├── pre-commit-config-template.yaml      # Pre-commit Hook 配置範本
        ├── github-actions/
        │   ├── security-baseline.yml            # GitHub Actions Layer 0 Workflow
        │   ├── build-verify.yml                 # GitHub Actions Layer 1 Workflow
        │   ├── migration-pipeline.yml           # GitHub Actions Migration Pipeline
        │   ├── security-scan-enhanced.yml       # GitHub Actions P1 增強安全掃描
        │   ├── perf-benchmark.yml               # GitHub Actions P2 效能基準
        │   ├── docs-pipeline.yml               # GitHub Actions P2 文檔 Pipeline
        │   └── agent-notification.yml         # GitHub Actions P3 Agent 通知
        └── gitlab-ci/
            ├── security-baseline-template.yml   # GitLab CI Layer 0 Template
            ├── build-verify-template.yml        # GitLab CI Layer 1 Template
            ├── migration-pipeline-template.yml  # GitLab CI Migration Pipeline
            ├── security-scan-enhanced-template.yml # GitLab CI P1 增強安全掃描
            ├── perf-benchmark-template.yml      # GitLab CI P2 效能基準
            ├── docs-pipeline-template.yml      # GitLab CI P2 文檔 Pipeline
            └── agent-notification-template.yml # GitLab CI P3 Agent 通知
```

---

## 📚 核心文檔模板 (Core Templates)

核心模板適用於所有情境（Greenfield, Brownfield, Refactoring 等）。

### 1. PRD（產品需求文件）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **PRD Universal Template** | [`core/prd/PRD_Universal_Template.md`](./core/prd/PRD_Universal_Template.md) | 階段 4 | PM/PO Agent (Victoria) |

**用途**:
- 定義產品願景、業務目標、成功指標
- 描述目標市場、競品分析、使用者角色
- 列出功能需求清單及優先級（MoSCoW）
- 定義非功能需求（效能、安全、可用性）

**使用時機**: 需求驗證與文件化階段

---

### 2. FRD（功能需求文件）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **FRD Universal Template** | [`core/frd/FRD_Universal_Template.md`](./core/frd/FRD_Universal_Template.md) | 階段 4 | SA Agent (Amanda) + BA Agent (Beatrice) |

**用途**:
- 詳細定義每個功能的規格
- 描述業務規則和驗證邏輯
- 定義資料模型和實體關係
- 說明使用者介面流程

**使用時機**: PRD 確認後，進行詳細功能規格定義

---

### 3. SRD（系統需求文件）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **SRD Module Template** | [`core/srd/SRD_Module_Template.md`](./core/srd/SRD_Module_Template.md) | 階段 5 | SD-Architect Agent (Marcus) |

**用途**:
- 定義系統架構和技術規格
- 說明技術選型理由（ADR）
- 定義模組劃分和介面設計
- 描述部署架構和環境配置

**使用時機**: 技術選型後，進行詳細系統設計

---

### 4. API Specification（API 規格文件）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **API Specification Template** | [`core/api/API_Specification_Template.md`](./core/api/API_Specification_Template.md) | 階段 5 | SD-Architect Agent (Marcus) |
| **API Index Template** | [`core/api/API_Index_Template.md`](./core/api/API_Index_Template.md) | 階段 5 | SD-Architect Agent (Marcus) |

**用途**:
- 定義 RESTful API 端點規格
- 描述 Request/Response 格式（JSON Schema）
- 定義認證授權機制
- 說明錯誤處理和版本策略

**使用時機**:
- ✅ **需要使用**: Web App 前後端分離、Mobile App 需雲端同步、多平台共用資料
- ❌ **不需要使用**: 純本地 Mobile App、單機應用

**替代方案**: 若不需要 Backend API，使用 [`core/srd/Data_Access_Layer_Template.md`](./core/srd/Data_Access_Layer_Template.md)

---

### 5. Test Templates（測試文件）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **Acceptance Test Template** | [`core/tests/AT_Module_Template.md`](./core/tests/AT_Module_Template.md) | 階段 6+ | QA Agent (Quincy) |
| **Test Report Template** | [`core/tests/Test_Report_Template.md`](./core/tests/Test_Report_Template.md) | 測試階段 | QA Agent (Quincy) |

**用途**:
- 定義驗收測試案例
- 記錄測試執行結果
- 追蹤缺陷和修復狀態

**使用時機**: User Story 確認後，進行測試案例設計

---

## 🎯 系統設計模板 (System Design Templates)

### Data Access Layer Template（資料訪問層設計模板）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **Data Access Layer Template** | [`core/srd/Data_Access_Layer_Template.md`](./core/srd/Data_Access_Layer_Template.md) | 階段 5 | SD-Architect Agent (Marcus) |

**用途**:
- 設計本地 App 的資料訪問層架構
- 定義 Repository Pattern 和 Service Layer
- 設計資料模型 Schema（Realm / SQLite / CoreData）
- 定義錯誤處理和 Schema 遷移策略

**使用時機**:
- ✅ **應使用**: 純本地 Mobile App、單機應用、工具型 App、100% 離線可用的 App
- ❌ **不應使用**: Web App 前後端分離、Mobile App 需雲端同步（應使用 API Specification）

**特色**:
- 提供完整的 Realm + TypeScript 實作範例
- 包含 Repository Pattern 完整實作（可直接使用）
- 提供 SQLite ER Diagram 對照
- 包含 Schema 遷移策略和錯誤處理

**新增時間**: v0.01 (2025-11-11)

---

## 🔧 支援文件模板 (Support Templates)

支援文件用於記錄流程、決策和分析結果。

### 1. Requirement Extraction Report（需求提取報告）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **Requirement Extraction Report Template** | [`support/Requirement_Extraction_Report_Template.md`](./support/Requirement_Extraction_Report_Template.md) | 階段 2 | SA Agent (Amanda) |

**用途**:
- 記錄需求提取階段的所有成果
- 包含功能需求、非功能需求、使用者角色、業務規則
- 提供需求完整性檢查結果
- 記錄待確認事項清單

**包含章節**:
- 需求來源（需求提供方式、原始需求內容）
- 需求解析結果（功能需求 F-XXX、非功能需求 NFR-XXX、使用者角色 UR-XXX、業務規則 BR-XXX）
- 需求完整性檢查（整合 [Completeness_Checklist](../scenarios/greenfield/checklists/Completeness_Checklist.md)）
- 需求追蹤矩陣
- 需求提取時間軸

**新增時間**: v0.01 (2025-11-11)

---

### 2. Collaboration Log（人機協作記錄）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **Collaboration Log Template** | [`support/Collaboration_Log_Template.md`](./support/Collaboration_Log_Template.md) | 所有階段 | All Agents |

**用途**:
- 記錄所有人機協作點的對話、決策和變更
- 支援 Zero Hallucination 原則（完整記錄所有對話）
- 提供協作統計與分析
- 評估人機協作品質

**包含章節**:
- 協作記錄索引（快速跳轉）
- 人機協作點記錄（AI 提問、使用者回答、決策結果、變更記錄、待辦事項）
- 協作統計與分析（協作點統計、決策分析、需求變更分析、協作效率分析）
- 人機協作品質評估
- Zero Hallucination 檢查
- 協作改善建議

**新增時間**: v0.01 (2025-11-11)

---

### 3. Tech Stack Selection Report（技術選型報告）

| 模板名稱 | 路徑 | 適用階段 | 負責 Agent |
|---------|------|---------|-----------|
| **Tech Stack Selection Report Template** | [`support/Tech_Stack_Selection_Report_Template.md`](./support/Tech_Stack_Selection_Report_Template.md) | 階段 3 | SD-Architect Agent (Marcus) |

**用途**:
- 記錄技術選型過程和決策理由
- 提供多個候選方案的詳細對比
- 評估成本（開發成本、學習成本、營運成本）
- 識別技術風險並提出緩解措施

**包含章節**:
- 技術需求分析（功能性、非功能性、團隊技能、專案約束）
- 技術棧候選方案（至少 2-3 個，每個包含技術組成、優缺點、SWOT 分析）
- 技術棧對比矩陣（權重評分法，6 個評估維度）
- 推薦方案與理由
- 技術風險評估（風險矩陣）
- ADR (Architecture Decision Records) 預告
- 實作里程碑（Phase 1-5）

**特色**:
- 提供 3 個完整候選方案範例（React Native, Flutter, 原生）
- 整合成本試算表（參考 [Cost_Estimation_Template](../scenarios/greenfield/checklists/Cost_Estimation_Template.md)）
- 整合學習曲線評估標準（參考 [Estimation_Standards](../guides/system/planning/Estimation_Standards.md)）

**新增時間**: v0.01 (2025-11-11)

---

## 🎨 情境專屬模板 (Scenario-Specific Templates)

情境專屬模板針對特定情境（如整合、效能、文件等）提供專用模板。

### 目前可用情境

| 情境 | 目錄 | 狀態 | 說明 |
|------|------|------|------|
| **Analysis** | `scenario_specific/analysis/` | ✅ 已建立 | 分析情境專用模板（3 個） |
| **Brownfield** | `scenario_specific/brownfield/` | ✅ 已建立 | Brownfield 情境模板（3 個） |
| **Migration** | `scenario_specific/migration/` | ✅ 已建立 | Migration 情境模板（3 個） |
| **Documentation** | `scenario_specific/documentation/` | 🚧 預留 | 文件情境專用模板 |
| **Testing** | `scenario_specific/testing/` | 🚧 預留 | 測試情境專用模板 |
| **Integration** | `scenario_specific/integration/` | 🚧 預留 | 整合情境專用模板 |
| **Performance** | `scenario_specific/performance/` | 🚧 預留 | 效能情境專用模板 |
| **DevOps** | `scenario_specific/devops/` | ✅ 已建立 | CI/CD Pipeline + 🔒 Layer 0 安全基線 |

### 🔒 DevOps 情境模板詳細（v0.01 CI/CD 強化）

| 範本 | 路徑 | 用途 |
|------|------|------|
| **CI/CD Pipeline** | [`devops/CICD_Pipeline_Template.md`](./scenario_specific/devops/CICD_Pipeline_Template.md) | CI/CD Pipeline 標準配置（GitHub Actions/GitLab CI/Jenkins） |
| **Layer 0 安全基線** | [`devops/Layer0_Security_Baseline_Template.md`](./scenario_specific/devops/Layer0_Security_Baseline_Template.md) | 🔴 **所有情境強制** — Secret Detection + SCA + License |
| **Pre-commit 配置** | [`devops/pre-commit-config-template.yaml`](./scenario_specific/devops/pre-commit-config-template.yaml) | 本地端安全攔截配置範本 |
| **GitHub Actions** | [`devops/github-actions/security-baseline.yml`](./scenario_specific/devops/github-actions/security-baseline.yml) | GitHub Actions Layer 0 Workflow |
| **GitLab CI** | [`devops/gitlab-ci/security-baseline-template.yml`](./scenario_specific/devops/gitlab-ci/security-baseline-template.yml) | GitLab CI Layer 0 Template |
| **Layer 1 建置驗證** | [`devops/Layer1_Build_Verify_Template.md`](./scenario_specific/devops/Layer1_Build_Verify_Template.md) | 🔴 **所有情境強制** — Lint + Build + Unit Test + Coverage Gate |
| **GitHub Actions** | [`devops/github-actions/build-verify.yml`](./scenario_specific/devops/github-actions/build-verify.yml) | GitHub Actions Layer 1 Workflow |
| **GitLab CI** | [`devops/gitlab-ci/build-verify-template.yml`](./scenario_specific/devops/gitlab-ci/build-verify-template.yml) | GitLab CI Layer 1 Template |
| **Migration Pipeline** | [`devops/Migration_Pipeline_Template.md`](./scenario_specific/devops/Migration_Pipeline_Template.md) | 🔄 **Migration 情境專屬** — Dual-Build + Contract Test + Canary + Rollback |
| **GitHub Actions** | [`devops/github-actions/migration-pipeline.yml`](./scenario_specific/devops/github-actions/migration-pipeline.yml) | GitHub Actions Migration Pipeline |
| **GitLab CI** | [`devops/gitlab-ci/migration-pipeline-template.yml`](./scenario_specific/devops/gitlab-ci/migration-pipeline-template.yml) | GitLab CI Migration Pipeline |
| **Security Integration** | [`devops/Security_Scan_Integration_Template.md`](./scenario_specific/devops/Security_Scan_Integration_Template.md) | 🛡️ **P1 增強安全掃描** — SAST + Container Scan + DAST（依情境等級） |
| **GitHub Actions** | [`devops/github-actions/security-scan-enhanced.yml`](./scenario_specific/devops/github-actions/security-scan-enhanced.yml) | GitHub Actions 增強安全掃描 Workflow |
| **GitLab CI** | [`devops/gitlab-ci/security-scan-enhanced-template.yml`](./scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml) | GitLab CI 增強安全掃描 Template |
| **Performance Benchmark** | [`devops/Performance_Benchmark_Gate_Template.md`](./scenario_specific/devops/Performance_Benchmark_Gate_Template.md) | ⚡ **P2 效能基準關卡** — Micro-Benchmark + Full Load Test + SLA Gate |
| **GitHub Actions** | [`devops/github-actions/perf-benchmark.yml`](./scenario_specific/devops/github-actions/perf-benchmark.yml) | GitHub Actions 效能基準 Workflow |
| **GitLab CI** | [`devops/gitlab-ci/perf-benchmark-template.yml`](./scenario_specific/devops/gitlab-ci/perf-benchmark-template.yml) | GitLab CI 效能基準 Template |
| **Documentation Pipeline** | [`devops/Documentation_Pipeline_Template.md`](./scenario_specific/devops/Documentation_Pipeline_Template.md) | 📝 **P2 文檔 Pipeline** — Doc Lint + Link Check + Build + Deploy |
| **GitHub Actions** | [`devops/github-actions/docs-pipeline.yml`](./scenario_specific/devops/github-actions/docs-pipeline.yml) | GitHub Actions 文檔 Pipeline Workflow |
| **GitLab CI** | [`devops/gitlab-ci/docs-pipeline-template.yml`](./scenario_specific/devops/gitlab-ci/docs-pipeline-template.yml) | GitLab CI 文檔 Pipeline Template |
| **Agent Notification** | [`devops/Event_Driven_Agent_Notification_Template.md`](./scenario_specific/devops/Event_Driven_Agent_Notification_Template.md) | 🔔 **P3 事件驅動 Agent 通知** — PR/Deploy/Release 事件通知 |
| **GitHub Actions** | [`devops/github-actions/agent-notification.yml`](./scenario_specific/devops/github-actions/agent-notification.yml) | GitHub Actions Agent 通知 Workflow |
| **GitLab CI** | [`devops/gitlab-ci/agent-notification-template.yml`](./scenario_specific/devops/gitlab-ci/agent-notification-template.yml) | GitLab CI Agent 通知 Template |

---

## 🗂️ 模板選擇指引 (Template Selection Guide)

### 依專案類型選擇模板

#### 1. Greenfield - 全新專案開發

**必須使用**:
- ✅ PRD Universal Template
- ✅ FRD Universal Template
- ✅ SRD Module Template
- ✅ Requirement Extraction Report Template
- ✅ Collaboration Log Template
- ✅ Tech Stack Selection Report Template

**情境選擇**:
- ✅ API Specification Template（Web App / Mobile App 雲端同步）
- ✅ Data Access Layer Template（純本地 Mobile App）

---

#### 2. Brownfield - 既有系統改進

**必須使用**:
- ✅ FRD Universal Template（變更需求）
- ✅ SRD Module Template（變更設計）
- ✅ Collaboration Log Template

**選擇性使用**:
- ☐ PRD Universal Template（如需更新產品規劃）
- ☐ API Specification Template（如有 API 變更）
- ☐ Data Access Layer Template（如有本地資料層變更）

---

#### 3. Refactoring - 程式碼重構

**必須使用**:
- ✅ SRD Module Template（新架構設計）
- ✅ Tech Stack Selection Report Template（如有技術選型變更）

**選擇性使用**:
- ☐ FRD Universal Template（如需更新功能規格）
- ☐ Data Access Layer Template（如重構資料訪問層）

---

### 依平台類型選擇模板

#### Web App（前後端分離）

**核心模板**:
- PRD, FRD, SRD
- **API Specification Template** ✅（必須）
- Collaboration Log
- Tech Stack Selection Report

**不需要**:
- ❌ Data Access Layer Template（前端使用 API Client）

---

#### Mobile App（純本地）

**核心模板**:
- PRD, FRD, SRD
- **Data Access Layer Template** ✅（必須）
- Collaboration Log
- Tech Stack Selection Report

**不需要**:
- ❌ API Specification Template（無 Backend）

---

#### Mobile App（雲端同步）

**核心模板**:
- PRD, FRD, SRD
- **API Specification Template** ✅（雲端同步 API）
- **Data Access Layer Template** ✅（本地資料層）
- Collaboration Log
- Tech Stack Selection Report

**額外需要**:
- Data Sync Strategy Document
- Conflict Resolution Policy

---

## 📖 使用方式 (How to Use)

### 1. 選擇適合的模板

根據您的專案類型和階段，參考上方的「模板選擇指引」選擇適合的模板。

---

### 2. 複製模板到專案目錄

```bash
# 範例：複製 PRD 模板到專案目錄
cp docs_template/core/prd/PRD_Universal_Template.md your_project/docs/PRD_YourProject_v1.0.md
```

---

### 3. 填寫模板內容

- 依照模板的章節結構填寫
- 參考模板中的範例和說明
- 保持 ID 命名一致（參考 [AISDLC_ID_Naming_Convention](../guides/system/naming/AISDLC_ID_Naming_Convention.md)）

---

### 4. 使用 AI Agent 協助填寫

```
執行指令：
「請使用 PRD_Universal_Template.md 模板，產生 MoneyTracker 專案的 PRD」
```

AI Agent 會依照模板結構，自動產生對應的文檔內容。

---

## 🔗 相關文件 (Related Documents)

### 指引文件

- [AISDLC_ID_Naming_Convention.md](../guides/system/naming/AISDLC_ID_Naming_Convention.md) - 統一 ID 命名規範
- [Estimation_Standards.md](../guides/system/planning/Estimation_Standards.md) - 估算標準（SP、Effort、學習曲線）
- [C4_Model_Guidelines.md](../guides/system/architecture/C4_Model_Guidelines.md) - C4 Model 層級要求
- [Platform_Agent_Selection_Guide.md](../guides/system/agent/Platform_Agent_Selection_Guide.md) - 平台 Architect 選擇指引
- [Document_Quality_Checklist.md](../guides/system/quality/Document_Quality_Checklist.md) - 文件品質檢查清單

### 檢查清單

- [Standard_Confirmation_Questions.md](../scenarios/greenfield/checklists/Standard_Confirmation_Questions.md) - 標準確認問題清單
- [Cost_Estimation_Template.md](../scenarios/greenfield/checklists/Cost_Estimation_Template.md) - 成本試算表範本
- [Completeness_Checklist.md](../scenarios/greenfield/checklists/Completeness_Checklist.md) - 需求完整性檢查清單

### SOP 文件

- [Greenfield SOP](../scenarios/greenfield/SOP.md) - Greenfield 情境標準作業程序
- [Brownfield SOP](../scenarios/brownfield/SOP.md) - Brownfield 情境標準作業程序
- [Refactoring SOP](../scenarios/refactoring/SOP.md) - Refactoring 情境標準作業程序

---

## 🆕 SDD 專屬模板（v0.01-SDD 新增）

SDD 模板存放於 `docs_template/sdd/` 目錄，使用規則：
- **不可直接修改模板**，必須複製到 `docs/` 對應子目錄後填寫
- 使用前參考 `AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md` 了解對應的 SCG 閘門

### SDD 模板使用規則

```
框架模板（不修改）:  docs_template/sdd/architecture/AS-IS-SRD-TEMPLATE.md
產出文件（填寫）:   docs/02_architecture/AS-IS-SRD-{SystemName}.md
```

### SDD 模板按 docs/ 輸出路徑對應

| docs/ 子目錄 | SDD 模板來源 | 說明 |
|-------------|------------|------|
| `docs/01_requirements/` | `sdd/requirements/` | Invariant Spec、Third-Party API Research |
| `docs/02_architecture/` | `sdd/architecture/` | AS-IS/TO-BE SRD、SAD、C4、Migration Contract Map |
| `docs/02_architecture/adr/` | `sdd/adr/` | ADR 模板與索引 |
| `docs/02_architecture/api/` | `sdd/api/` | API-COMPAT、Contract YAML |
| `docs/03_testing/` | `sdd/testing/` | RTM、Test Strategy、Performance Baseline 等 |
| `docs/04_planning/` | `sdd/planning/` | Gap Analysis、Refactor Plan |
| `docs/05_development/` | `sdd/development/` | Living Doc Strategy |
| `docs/06_quality/` | `sdd/quality/` | Code Quality Baseline、Tech Debt Spec |
| `docs/08_deployment/` | `sdd/deployment/` | Canary/Cutover/Rollback/Monitoring Spec 等 |

---

## 📊 模板更新歷史 (Update History)

### v0.01-SDD-J 模板代謝對賬 (2026-06-02)

**Phase E~J 累積新增 8 個模板，總數 51 → 59（56 md + 3 yaml）**，並由 `arch_fitness`
**FF-15**（docs_template 索引 ↔ 磁碟一致性）將此對賬自動化，杜絕計數再次靜默漂移：
- `sdd/requirements/`：+3（AMBIGUITY-SCORER-SPEC、AMBIGUITY-WAIVER、SPEC-PATCH）
- `sdd/architecture/`：+2（PATH-COST-MODEL-SPEC、SPEC-ANCHOR）
- `sdd/testing/`：+1（TEST-CONTRACT-NEGOTIATION）
- `sdd/quality/`：+1（PBS-DRIFT-REPORT）
- `sdd/build/`：+1（SDD_ABORT_REPORT，新增 build 類）

> FF-15 守兩道：①索引引用的模板必須在磁碟存在（structural）②索引宣稱數/涵蓋面 vs 磁碟
> 漂移（advisory）。與 FF-11（Skill）/ FF-13（Agent）對稱，補齊 artifact 三支柱結構守門。

### v0.01-SDD (2026-04-16)

**新增 SDD 專屬模板（51 個）**：
- `sdd/requirements/`：2 個（INVARIANT-SPEC、THIRD-PARTY-API-RESEARCH）
- `sdd/architecture/`：11 個（AS-IS-SRD、TO-BE-SRD、SAD、SDD-COMPLIANCE-AUDIT 等）
- `sdd/adr/`：4 個（ADR-INDEX、ADR-TEMPLATE、Automation ADR、Performance ADR）
- `sdd/api/`：4 個（API-COMPAT md + 3 Contract yaml）
- `sdd/testing/`：18 個（RTM、STRIDE、Invariant Test Contract、Living Test Report 等）
- `sdd/planning/`：2 個（GAP-ANALYSIS、REFACTOR-PLAN）
- `sdd/quality/`：2 個（CODE-QUALITY-BASELINE、TECH-DEBT-SPEC）
- `sdd/development/`：1 個（LIVING-DOC-STRATEGY）
- `sdd/deployment/`：7 個（CANARY/CUTOVER/ROLLBACK/INCIDENT-RESPONSE/MONITORING/PIPELINE/SECURITY-MONITORING SPEC）

---

### v0.01 (2025-11-11)

**新增模板**:
- ✅ Requirement_Extraction_Report_Template.md（需求提取報告）
- ✅ Collaboration_Log_Template.md（人機協作記錄）
- ✅ Tech_Stack_Selection_Report_Template.md（技術選型報告）
- ✅ Data_Access_Layer_Template.md（資料訪問層設計）

**改善**:
- 建立 `support/` 目錄，統一管理支援文件模板
- `srd/` 根目錄已移除，系統設計模板整合至 `core/srd/`
- 新增模板選擇指引（依專案類型、平台類型）

**相關問題修正**:
- 問題 #8: 產出文件格式未定義（階段 2）
- 問題 #11: 產出文件格式未定義（階段 3）
- 問題 #18: Mobile 本地應用不需要 RESTful API

---

### v0.04 及之前

**核心模板**:
- PRD_Universal_Template.md
- FRD_Universal_Template.md
- SRD_Module_Template.md
- API_Specification_Template.md
- API_Index_Template.md
- AT_Module_Template.md
- Test_Report_Template.md

---

## ❓ 常見問題 (FAQ)

### Q1: 我應該使用 API Specification 還是 Data Access Layer？

**判斷準則**:
- **需要 Backend API**: Web App 前後端分離、Mobile App 需雲端同步、多平台共用資料
  → 使用 **API Specification Template**
- **不需要 Backend API**: 純本地 Mobile App、單機應用、100% 離線可用
  → 使用 **Data Access Layer Template**

詳細說明請參考 [Greenfield SOP 階段 5.2.3](../scenarios/greenfield/SOP.md#步驟-523-api--data-access-layer-設計情境適配)

---

### Q2: 模板中的 ID 命名規則是什麼？

請參考 [AISDLC_ID_Naming_Convention.md](../guides/system/naming/AISDLC_ID_Naming_Convention.md)

**常見 ID 格式**:
- Feature ID: `F-XXX`
- Business Rule ID: `BR-XXX`
- User Story ID: `US-XXX`
- Acceptance Criteria ID: `AC-XXX-Y`
- API ID: `API-XXX`
- Test Case ID: `TC-XXX-Y-Z`

---

### Q3: 模板可以客製化嗎？

✅ **可以！** 模板提供標準結構，您可以根據專案需求：
- 調整章節順序
- 新增專案特定章節
- 移除不適用的章節
- 調整 ID 格式（建議保持一致性）

---

### Q4: 如何確保文檔品質？

使用 [Document_Quality_Checklist.md](../guides/system/quality/Document_Quality_Checklist.md) 進行文檔品質檢查：
- 可讀性檢查（專有名詞定義、縮寫說明）
- 視覺元素檢查（圖表清晰、有標題）
- 連結檢查（交叉連結正確、無 404）
- 一致性檢查（ID 命名、術語、日期格式）

---

## 📧 回饋與貢獻 (Feedback & Contribution)

如對模板有任何建議或發現問題，請透過以下方式聯絡：
- GitHub Issues: [AISDLC Repository Issues](https://github.com/AISDLC/framework/issues)
- 更新本 README.md 並提交 Pull Request

---

**文檔建立時間**: 2025-11-11
**文檔路徑**: `docs_template/README.md`
**維護者**: AISDLC Framework Team
**維護狀態**: Active

---

**End of README**
