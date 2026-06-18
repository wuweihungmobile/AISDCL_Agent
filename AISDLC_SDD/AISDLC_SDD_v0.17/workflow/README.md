# AISDLC Workflow 目錄
# Workflow Directory

**版本**: v0.01-SDD
**最後更新**: 2026-04-16

---

## 概覽

AISDLC-SDD v0.01 提供 **8 個核心 Workflows**、**13 個情境專用 Workflows**、**1 個 SDD Spec-First Gate Workflow** 和 **1 個 ADR Generation Workflow**，共 23 個工作流，涵蓋需求分析到 Sprint 執行的完整開發生命週期，並內建 SCG 閘門品質管控。

---

## 📂 目錄結構

```
workflow/
├── README.md                                   # 本文件
│
├── core/                                       # 核心 Workflows (8個)
│   ├── requirements-extraction.md              # 統一需求提取
│   ├── validation-documentation.md             # 需求驗證與文檔化
│   ├── user-story-design.md                    # 使用者故事與系統設計
│   ├── change-management.md                    # 需求變更管理
│   ├── api-specification.md                    # API 規格生成與維護
│   ├── consistency-check.md                    # 文檔一致性檢查
│   ├── interaction-analysis.md                 # 前後端交互分析
│   └── sprint-execution.md                     # Sprint 執行與開發測試
│
└── scenario-specific/                          # 情境專用 Workflows (13個)
    ├── greenfield-complete-flow.md             # 新專案完整開發流程
    ├── brownfield-analysis-flow.md             # 舊專案分析與改造流程
    ├── refactoring-planning-flow.md            # 程式碼重構規劃流程
    ├── migration-planning-flow.md              # 技術棧遷移規劃流程
    ├── performance-optimization-flow.md        # 效能優化流程
    ├── integration-analysis-flow.md            # 系統整合分析流程
    ├── devops-setup-flow.md                    # DevOps 建置與 CI/CD 流程
    ├── testing-strategy-flow.md                # 測試策略制定與實作流程
    ├── documentation-flow.md                   # 技術文檔撰寫流程
    ├── documentation-reconstruction-flow.md    # 文檔重建流程
    ├── security-assessment-flow.md             # 安全評估與合規檢查流程
    ├── tech-stack-selection-flow.md            # 技術選型流程
    └── code-analysis-flow.md                   # 代碼分析流程
```

---

## 🔧 核心 Workflows (core/)

8 個跨情境通用的基礎工作流程，構成 AISDLC 完整開發生命週期：

| 檔案 | 工作流程名稱 | Primary Agents | 用途 |
|------|------------|----------------|------|
| `requirements-extraction.md` | 統一需求提取 | sa-analyst, ba-business-analyst | 多格式需求分析（截圖/文字/混合）|
| `validation-documentation.md` | 需求驗證與文檔化 | sa-analyst, ba-business-analyst | 深度驗證 → PRD/FRD 生成 |
| `user-story-design.md` | 使用者故事與系統設計 | sa-analyst, sd-architect | User Stories → SRD 生成 |
| `change-management.md` | 需求變更管理 | sa-analyst, pm-po | 需求變更追蹤與影響分析 |
| `api-specification.md` | API 規格生成與維護 | sd-architect, sa-analyst | API 詳細規格（系統有 API 時必用）|
| `consistency-check.md` | 文檔一致性檢查 | sa-analyst, sd-architect | 驗證 PRD/FRD/SRD/API 一致性 |
| `interaction-analysis.md` | 前後端交互分析 | sd-architect, sa-analyst | 設計與文檔 FE-BE 互動流程 |
| `sprint-execution.md` | Sprint 執行與開發測試 | dev-developer, qa-tester | Sprint 執行、開發、測試 |

### 核心 Workflow 執行順序（標準流程）

```
需求提取          驗證文檔化        使用者故事與設計      API 規格
requirements  →  validation    →  user-story      →  api-specification
-extraction       -documentation    -design

      ↓ 持續進行
change-management   consistency-check   interaction-analysis   sprint-execution
（變更發生時）        （交付前驗證）        （前後端設計時）         （開發執行期）
```

---

## 🎯 情境專用 Workflows (scenario-specific/)

13 個針對特定情境優化的專用流程：

| 檔案 | 流程名稱 | 對應情境 |
|------|---------|---------|
| `greenfield-complete-flow.md` | 新專案完整開發流程 | greenfield |
| `brownfield-analysis-flow.md` | 舊專案分析與改造流程 | brownfield |
| `refactoring-planning-flow.md` | 程式碼重構規劃流程 | refactoring |
| `migration-planning-flow.md` | 技術棧遷移規劃流程 | migration |
| `performance-optimization-flow.md` | 效能優化流程 | performance |
| `integration-analysis-flow.md` | 系統整合分析流程 | integration |
| `devops-setup-flow.md` | DevOps 建置與 CI/CD 流程 | devops |
| `testing-strategy-flow.md` | 測試策略制定與實作流程 | testing |
| `documentation-flow.md` | 技術文檔撰寫流程 | documentation |
| `documentation-reconstruction-flow.md` | 文檔重建流程 | documentation |
| `security-assessment-flow.md` | 安全評估與合規檢查流程 | security |
| `tech-stack-selection-flow.md` | 技術選型流程 | greenfield / migration |
| `code-analysis-flow.md` | 代碼分析流程 | brownfield / refactoring |

---

## 📌 情境與 Workflow 對應

| 情境 | 核心 Workflows | 情境專用 Workflows |
|------|--------------|------------------|
| greenfield | requirements-extraction, validation-documentation, user-story-design, api-specification | greenfield-complete-flow, tech-stack-selection-flow |
| brownfield | requirements-extraction, consistency-check, sprint-execution | brownfield-analysis-flow, code-analysis-flow |
| refactoring | consistency-check, sprint-execution | refactoring-planning-flow, code-analysis-flow |
| migration | change-management, api-specification | migration-planning-flow, tech-stack-selection-flow |
| performance | interaction-analysis, sprint-execution | performance-optimization-flow |
| integration | requirements-extraction, api-specification, interaction-analysis, sprint-execution | integration-analysis-flow |
| devops | sprint-execution | devops-setup-flow |
| testing | sprint-execution | testing-strategy-flow |
| documentation | consistency-check | documentation-flow, documentation-reconstruction-flow |
| security | consistency-check | security-assessment-flow |

---

## 🔒 執行規範

所有 Workflow 強制執行以下機制：

1. **🔴 人機確認點** — 標記 🔴 的步驟必須等待人工確認，不可跳過
2. **Agent 綁定** — 每個 Workflow 定義 Primary 和 Supporting Agents，按需自動載入
3. **零推測原則** — AI 遇到不確定內容必須詢問，不可假設
4. **文檔可追溯** — 每個 Workflow 產出物需維護 PRD → FRD → SRD → API 完整追蹤鏈

---

## 🔗 相關文檔

- [AISDLC_SDD_INIT.md](../AISDLC_SDD_INIT.md) - Workflow 與 Agent 映射配置
- [scenarios/README.md](../scenarios/README.md) - 十大情境 SOP 導覽
- [docs_template/README.md](../docs_template/README.md) - 文檔模板系統

---

**維護者**: AISDLC Framework Team
