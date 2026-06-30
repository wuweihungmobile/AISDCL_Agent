# AISDLC → SDD 轉型執行藍圖 Phase 01
# Foundation & SDD Core Strategy（基礎建設與核心策略）

**版本**: v1.0
**建立日期**: 2026-04-11
**文件類型**: 規劃文件（Planning）
**所屬分類**: docs/04_planning/
**目標讀者**: 架構師、AI Agent 設定人員、AISDLC 框架維護者

---

## 📋 Phase 01 目標

建立 SDD（Specification/System Design Document Driven）轉型的基礎設施，包含：
1. SDD 核心原則文件化
2. 所有 Agent 的共通 Skill 升級規格
3. Workflow 改造基礎規範
4. 全局品質閘門（Spec-First Gate）機制設計

---

## 🔭 SDD 轉型核心哲學

### 現狀 vs 目標對比

| 面向 | AISDLC v0.09 現狀 | SDD 目標狀態 |
|------|------------------|-------------|
| 文件定位 | 輔助說明（記錄決策） | 主要產出（驅動開發） |
| 規格時序 | 開發前後均可補齊 | 嚴格先於實作（Spec-First Gate） |
| 架構決策 | 隱性於 SRD 文字描述中 | ADR 顯性化，每決策一文件 |
| API 契約 | 建議產出，非強制 | 強制產出（Contract-First） |
| 品質閘門 | Human Checkpoint（🔴） | 🔴 Human + 🔷 Spec Compliance Gate |
| 圖表規範 | 選配（C4 Model 指引） | 強制：Context + Container 圖必產出 |
| 測試契約 | 測試計畫文件 | Test Contract Specification（先於開發） |

### SDD 三大支柱定義

```
┌─────────────────────────────────────────────────────────┐
│                SDD 三大核心支柱                           │
├─────────────────┬──────────────────┬────────────────────┤
│  Pillar 1       │  Pillar 2        │  Pillar 3          │
│  Spec-First     │  Design-as-Doc   │  Contract-Driven   │
│  Gate           │  (設計即文件)     │  Development       │
├─────────────────┼──────────────────┼────────────────────┤
│ 規格必須先於     │ 架構圖/決策/API   │ API & Interface    │
│ 所有實作行為    │ 是主要交付物      │ 契約先於實作        │
│                 │                  │                    │
│ 觸發點：        │ 觸發點：          │ 觸發點：            │
│ 每個 Stage 入口 │ 每個架構決策點    │ 任何整合介面定義    │
│                 │                  │                    │
│ 產出物：        │ 產出物：          │ 產出物：            │
│ Spec Freeze     │ ADR + C4 圖       │ OpenAPI / Contract │
│ Checklist       │ + 決策矩陣        │ Test Spec          │
└─────────────────┴──────────────────┴────────────────────┘
```

---

## 🧩 共通 Agent Skill 升級規格（全 Agent 適用）

### Skill 1: `generate_adr` — Architecture Decision Record 生成

**適用情境**：所有 10 大情境，凡有架構或技術決策時觸發

**ADR 標準格式**：
```markdown
# ADR-{序號}: {決策標題}

**日期**: YYYY-MM-DD
**狀態**: Proposed | Accepted | Deprecated | Superseded
**決策者**: {Agent 角色} + {人類確認}

## 情境（Context）
描述面臨的問題和約束條件

## 決策（Decision）
我們選擇...

## 理由（Rationale）
選擇此方案的原因，包含評估的替代方案

## 後果（Consequences）
- 正面影響：...
- 負面影響：...
- 技術債務（如有）：...

## 替代方案評估（Alternatives Considered）
| 方案 | 優點 | 缺點 | 排除原因 |
|------|------|------|---------|

## 相關文件
- 關聯 SRD 章節：...
- 關聯 ADR：ADR-XXX
```

**觸發規則**：
- [ ] 技術棧選擇（語言、框架、資料庫）
- [ ] 架構模式選擇（Monolith / Microservices / Event-Driven）
- [ ] 整合策略（API / Event / File / DB Share）
- [ ] 安全機制選擇（Auth / Encryption / Token）
- [ ] 部署策略（Container / Serverless / VM）

---

### Skill 2: `spec_compliance_check` — 規格符合性自我驗證

**用途**：Agent 在產出文件前，驗證輸出符合 SDD 規格要求

**驗證清單**：
```yaml
spec_compliance_checklist:
  completeness:
    - [ ] 所有必填欄位已填寫
    - [ ] 追溯鏈完整（Business Need → US → AC → AT）
    - [ ] 相關 ADR 已建立
  format:
    - [ ] 文件命名符合規範
    - [ ] 目錄位置正確（依 FILE_DIRECTORY_RULES.md）
    - [ ] Markdown 格式通過 Lint
  cross_reference:
    - [ ] 上游文件引用正確
    - [ ] 下游文件連結已預留
    - [ ] ID 格式統一（EPIC/F/US/AC/AT/API/NFR）
  sdd_specific:
    - [ ] 規格產出先於任何實作描述
    - [ ] 每個架構決策有對應 ADR
    - [ ] API 定義使用 OpenAPI 格式
```

---

### Skill 3: `traceability_matrix` — 需求追溯矩陣生成

**用途**：建立從業務需求到測試案例的完整追溯鏈

**RTM 標準格式**：
```markdown
| EPIC | Feature | User Story | AC | AT | API | NFR | Status |
|------|---------|-----------|-----|-----|-----|-----|--------|
| EPIC-001 | F-001 | US-001 | AC-001-1 | AT-001-1-1 | API-001 | NFR-001 | ✅ |
```

**觸發時機**：
- Stage 3（SA 完成 FRD 後）
- Stage 5（SD 完成 SRD 後）
- Stage 6（QA 完成測試計畫後）
- 任何需求變更後

---

## 🔷 Spec-First Gate 機制設計

### 全局品質閘門定義

```
傳統 AISDLC Checkpoint：
  ...開發中... → 🔴 Human Checkpoint → ...繼續...

SDD 強化版 Checkpoint：
  ...規格撰寫中... → 🔷 Spec Compliance Gate → 🔴 Human Checkpoint → ...實作...
                         ↑
                    Agent 自動驗證
                    （spec_compliance_check）
```

### 閘門類型

| 閘門代號 | 名稱 | 觸發條件 | 負責 Agent |
|---------|------|---------|-----------|
| 🔷 SCG-1 | Requirement Spec Gate | FRD 完成前 | sa-analyst |
| 🔷 SCG-2 | Architecture Spec Gate | SRD 完成前 | sd-architect |
| 🔷 SCG-3 | API Contract Gate | API Spec 完成前 | integration-specialist / sd-architect |
| 🔷 SCG-4 | Test Strategy Gate | 測試計畫完成前 | qa-lead |
| 🔷 SCG-5 | Security Spec Gate | 安全設計完成前 | security-engineer |
| 🔷 SCG-6 | Performance Baseline Gate | 效能規格完成前 | performance-engineer |

---

## 📁 SDD 新增文件類型規範

### 新增文件類型對照表

| 文件類型 | 簡稱 | 存放位置 | 範本命名 |
|---------|------|---------|---------|
| Architecture Decision Record | ADR | `docs/02_architecture/adr/` | `ADR-{NNN}-{title}.md` |
| API Contract Spec | Contract | `docs/02_architecture/api/` | `CONTRACT-{module}-{version}.yaml` |
| Performance Baseline Spec | PBS | `docs/04_planning/performance/` | `PBS-{system}-{date}.md` |
| Security Architecture Doc | SAD | `docs/06_quality/security/` | `SAD-{system}-{date}.md` |
| Test Contract Spec | TCS | `docs/03_testing/contracts/` | `TCS-{feature}-{date}.md` |
| IaC Specification | IaCS | `docs/08_deployment/iac/` | `IaCS-{env}-{date}.md` |
| Migration Contract Map | MCM | `docs/02_architecture/migration/` | `MCM-{system}-{date}.md` |

---

## ✅ Phase 01 執行 Checklist

### 1.1 SDD 核心原則文件化

- [x] 1.1.1 建立 `docs/02_architecture/SDD_Core_Principles.md`（本文件摘要版）
- [x] 1.1.2 建立 `docs/02_architecture/adr/` 目錄結構
- [x] 1.1.3 建立 ADR 範本：`docs/02_architecture/adr/ADR-TEMPLATE.md`
- [x] 1.1.4 建立 API Contract 範本：`docs/02_architecture/api/CONTRACT-TEMPLATE.yaml`
- [x] 1.1.5 建立 RTM 範本：`docs/03_testing/RTM-TEMPLATE.md`

### 1.2 Agent Skill 升級規格文件

- [x] 1.2.1 更新 `AISDLC_v0.09/agent/core/04.sa-analyst-zh.yaml`
  - 新增 skill: `as_is_srd_reverse`（逆向規格提取）
  - 新增 skill: `to_be_srd_gen`（To-Be SRD 生成）
  - 新增 skill: `generate_adr`（共通）
  - 新增 skill: `spec_compliance_check`（共通）
  - 新增 skill: `traceability_matrix`（共通）

- [x] 1.2.2 更新 `AISDLC_v0.09/agent/core/05.sd-architect-zh.yaml`
  - 新增 skill: `contract_document_gen`（契約文件生成）
  - 新增 skill: `c4_diagram_mandatory`（C4 圖強制生成）
  - 新增 skill: `generate_adr`（共通）
  - 新增 skill: `spec_compliance_check`（共通）

- [x] 1.2.3 更新 `AISDLC_v0.09/agent/specialized/integration-specialist-zh.yaml`
  - 新增 skill: `consumer_driven_contract`（消費者驅動契約）
  - 新增 skill: `openapi_spec_gen`（OpenAPI 優先生成）
  - 新增 skill: `generate_adr`（共通）

- [x] 1.2.4 更新 `AISDLC_v0.09/agent/specialized/performance-engineer-zh.yaml`
  - 新增 skill: `slo_sla_spec`（SLO/SLA 規格定義）
  - 新增 skill: `baseline_benchmark_spec`（基準效能規格）
  - 新增 skill: `generate_adr`（共通）

- [x] 1.2.5 更新 `AISDLC_v0.09/agent/specialized/security-engineer-zh.yaml`
  - 新增 skill: `stride_threat_model`（STRIDE 威脅模型）
  - 新增 skill: `security_arch_doc`（安全架構文件生成）
  - 新增 skill: `generate_adr`（共通）

- [x] 1.2.6 更新 `AISDLC_v0.09/agent/specialized/technical-writer-zh.yaml`
  - 新增 skill: `living_documentation`（活文件維護機制）
  - 新增 skill: `adr_index_maintenance`（ADR 索引維護）
  - 新增 skill: `spec_compliance_check`（共通）

- [x] 1.2.7 更新 `AISDLC_v0.09/agent/specialized/qa-lead-zh.yaml`
  - 新增 skill: `test_strategy_spec`（測試策略規格化）
  - 新增 skill: `test_contract_gen`（測試契約生成）
  - 新增 skill: `traceability_matrix`（共通）

- [x] 1.2.8 更新 `AISDLC_v0.09/agent/specialized/devops-engineer-zh.yaml`
  - 新增 skill: `iac_specification`（IaC 即規格）
  - 新增 skill: `pipeline_spec_doc`（Pipeline 規格文件化）
  - 新增 skill: `generate_adr`（共通）

- [x] 1.2.9 更新所有剩餘 Agent（ba, pm-po, dev-developer, dev-senior, qa-tester, qa-automation, code-analyzer, qa-web-tester, qa-mobile-tester, sd-web-architect, sd-mobile-architect, compliance-officer）
  - 新增共通 skill: `generate_adr`, `spec_compliance_check`, `traceability_matrix`

### 1.3 Workflow 基礎架構升級

- [x] 1.3.1 在所有 Workflow SOP 中加入「🔷 Spec Compliance Gate」標記
- [x] 1.3.2 建立 `AISDLC_v0.09/workflow/sdd-spec-first-gate/` Workflow 定義
- [x] 1.3.3 建立 `AISDLC_v0.09/workflow/adr-generation/` Workflow 定義
- [x] 1.3.4 更新 `AISDLC_v0.09/AISDLC_INIT.md` 加入 SDD 相關 Workflow 映射

### 1.4 CI/CD 基礎升級（Base Layer）

- [x] 1.4.1 定義 L0 基礎層 SDD 擴充：加入 `DocLint`（文件格式 Lint）
- [x] 1.4.2 定義 L0 基礎層 SDD 擴充：加入 `SpecTrace`（規格追溯驗證）
- [x] 1.4.3 定義 `DocPipeline` 標準化：Markdown Lint + Link Check + ADR Index 更新

### 1.5 文件目錄結構初始化

- [x] 1.5.1 建立 `docs/02_architecture/adr/` 目錄
- [x] 1.5.2 建立 `docs/02_architecture/api/` 目錄
- [x] 1.5.3 建立 `docs/02_architecture/migration/` 目錄
- [x] 1.5.4 建立 `docs/03_testing/contracts/` 目錄
- [x] 1.5.5 建立 `docs/04_planning/performance/` 目錄
- [x] 1.5.6 建立 `docs/06_quality/security/` 目錄
- [x] 1.5.7 建立 `docs/08_deployment/iac/` 目錄
- [x] 1.5.8 更新 `FILE_DIRECTORY_RULES.md` 納入新增目錄

---

## 📊 Phase 01 完成標準（Definition of Done）

| 項目 | 驗證方法 | 預期結果 |
|------|---------|---------|
| 共通 Skill 升級完成 | 檢查所有 Agent YAML 包含 `generate_adr` | 21 個 Agent 全部更新 |
| ADR 範本建立 | 檢查 `docs/02_architecture/adr/ADR-TEMPLATE.md` 存在 | 檔案存在且格式正確 |
| Spec Gate 機制文件化 | 檢查 SDD_Core_Principles.md | 6 個 Gate 類型全部定義 |
| 目錄結構建立 | `ls docs/` 驗證 | 7 個新目錄全部建立 |

---

**下一階段**: [Phase 02 - Greenfield & Documentation](AISDLC_TO_SDD_Planning_Phase_02.md)

**建立者**: 首席 AI-SDLC 轉型架構師
**最後更新**: 2026-04-11
