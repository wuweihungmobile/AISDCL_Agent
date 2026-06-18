# Agent 更新指南 — AISDLC v0.09 → AISDLC-SDD v0.01

**建立日期**: 2025-10-23
**最後更新**: 2026-04-17
**用途**: AISDLC v0.09 升級至 AISDLC-SDD v0.01 的 Agent 配置更新完整規格
**狀態**: ✅ Phase 01~09 全部完成（SDD 轉型 2026-04-17）

---

## SDD 升級核心變化說明

從 AISDLC v0.09 升級至 AISDLC-SDD v0.01，Agent 配置有以下核心變化：

### 1. SDD 三大支柱新增技能

所有核心 Agents 均在 v0.01 中獲得對應 SDD 支柱的新技能：

| 支柱 | 新增要求 | 影響的 Agent |
|------|---------|------------|
| **Spec-First Gate** | 每個 Agent 必須了解自己負責的 SCG 閘門 | 所有 Agents |
| **Design-as-Doc** | 架構決策必須產出 ADR；設計必須有 C4 圖 | sd-architect、sa-analyst |
| **Contract-Driven** | OpenAPI 凍結前不實作；Consumer Contract 先行 | sd-architect、integration-specialist、dev-developer |

### 2. SCG 閘門機制（SCG-0~SCG-6）

v0.01 新增 7 道強制閘門，每個 Agent 都有對應的閘門責任：

| SCG | 閘門名稱 | 主要負責 Agent | 產出 |
|-----|---------|--------------|------|
| SCG-0 | 需求凍結 | pm-po + sa-analyst | PRD + FRD |
| SCG-1 | 設計凍結 | sd-architect | SRD + API Spec |
| SCG-2 | 架構凍結 | sd-architect | C4 + ADR |
| SCG-3 | Contract Freeze | sd-architect / integration-specialist | OpenAPI 3.1 |
| SCG-4 | PR Review | dev-developer + qa-tester | 規格一致性 |
| SCG-5 | 交付驗證 | qa-lead + sa-analyst | RTM 100% |
| SCG-6 | 發布確認 | qa-lead | 所有閘門通過 |

### 3. 核心 Agents 的 SDD 新技能（v0.01 新增）

| Agent | SDD 新增技能 |
|-------|------------|
| **sa-analyst** | 逆向規格工程（As-Is SRD）、Gap Analysis、Business Invariants 提取（INV-XXX）|
| **sd-architect** | As-Is C4 Model、ADR Archaeology、Before/After 架構對比、Contract Map（Migration）|
| **qa-tester** | As-Is 測試規格基線、Invariant Test Contract、Consumer Contract 測試 |
| **dev-developer** | Strangler Fig 模式實作、Branch by Abstraction、Contract-First 開發 |
| **code-analyzer** | Tech Debt 規格化（TD-XXX）、代碼品質基準線（Code Quality Baseline Spec）|
| **technical-writer** | Living Documentation 策略、ADR 維護、API 文件從 Contract 生成 |

---

---

## 更新狀態追蹤（v0.01 完成）

### 核心 Agents (7個) — SDD v0.01 全部完成
- [x] 04.sa-analyst ✅ 已更新（新增：逆向規格工程、Invariants 提取）
- [x] 02.ba-business-analyst ✅ 已更新（新增：SCG-0 業務驗證）
- [x] 03.pm-po-agent ✅ 已更新（新增：Spec-First 產品規劃）
- [x] 05.sd-architect ✅ 已更新（新增：C4、ADR、Contract Map）
- [x] 06.dev-developer ✅ 已更新（新增：Contract-First 開發）
- [x] 07.qa-tester ✅ 已更新（新增：Invariant Test Contract、RTM）
- [x] 01.agent-template ✅ 已更新（參考用）

### 專業 Agents (14個) — SDD v0.01 全部完成
- [x] code-analyzer ✅ 已更新（新增：Tech Debt 規格化）
- [x] performance-engineer ✅ 已更新（新增：PBS Gate 機制）
- [x] integration-specialist ✅ 已更新（新增：Consumer Contract）
- [x] devops-engineer ✅ 已更新（新增：Pipeline Spec、IaC 規格）
- [x] security-engineer ✅ 已更新（新增：STRIDE 威脅建模）
- [x] qa-lead ✅ 已更新（新增：SCG-5/6 RTM 驗證）
- [x] qa-automation ✅ 已更新（新增：Contract Test 自動化）
- [x] technical-writer ✅ 已更新（新增：Living Doc、ADR 維護）
- [x] dev-senior ✅ 已更新（新增：Strangler Fig、Branch by Abstraction）
- [x] compliance-officer ✅ 已更新（新增：合規 RTM 追蹤）
- [x] sd-mobile-architect ✅ 已更新
- [x] sd-web-architect ✅ 已更新
- [x] qa-mobile-tester ✅ 已更新
- [x] qa-web-tester ✅ 已更新

---

## 各Agent更新規格

### 02. ba-business-analyst

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Peer-Review"
      role: "Peer"
      description: "與SA進行FRD/PRD交叉審查，從業務角度驗證"
      applicable_scenarios: ["Greenfield", "Brownfield", "All with BA"]
    - pattern: "Lead-Support"
      role: "Support"
      description: "提供業務分析專業建議"
      applicable_scenarios: ["Greenfield", "Integration"]

scenario_usage:
  frequency: "Medium (3/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep"
  primary_scenarios:
    - scenario: "Greenfield"
      role: "Business Validator"
      responsibilities: "業務需求驗證、利害關係人溝通"
    - scenario: "Brownfield"
      role: "Business Analyst"
      responsibilities: "業務流程分析、改進建議"

  supporting_scenarios:
    - scenario: "Integration"
      role: "Business Process Advisor"
      contributions: "業務流程整合建議"
```

### 03. pm-po-agent

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導產品決策和優先級排序"
      applicable_scenarios: ["Greenfield"]
    - pattern: "Sequential-Handoff"
      role: "Provider"
      description: "產出PRD交接給SA"
      applicable_scenarios: ["Greenfield", "All with PRD"]

scenario_usage:
  frequency: "High (6/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep"
  primary_scenarios:
    - scenario: "Greenfield"
      role: "Product Owner"
      responsibilities: "產品願景、PRD產出、優先級決策"
    - scenario: "Brownfield"
      role: "Product Manager"
      responsibilities: "功能優先級、改進方向"

  supporting_scenarios:
    - scenario: "Performance"
      role: "Priority Advisor"
      contributions: "效能優化優先級"
    - scenario: "Refactoring"
      role: "Business Value Advisor"
      contributions: "重構業務價值評估"
    - scenario: "Integration"
      role: "Integration Planning"
      contributions: "整合優先級和範圍"
    - scenario: "Testing"
      role: "Test Priority"
      contributions: "測試範圍優先級"
```

### 05. sd-architect

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導技術架構設計"
      applicable_scenarios: ["Greenfield", "Performance", "Integration"]
    - pattern: "Sequential-Handoff"
      role: "Receiver & Provider"
      description: "接收FRD產出SRD，交接給Dev"
      applicable_scenarios: ["All scenarios"]
    - pattern: "Peer-Review"
      role: "Primary & Peer"
      description: "技術設計審查"
      applicable_scenarios: ["All technical scenarios"]

scenario_usage:
  frequency: "High (8/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep"
  primary_scenarios:
    - scenario: "Greenfield"
      role: "Lead Architect"
      responsibilities: "架構設計、技術選型、SRD產出"
    - scenario: "Performance"
      role: "Performance Architect"
      responsibilities: "架構層面效能優化設計"
    - scenario: "Integration"
      role: "Integration Architect"
      responsibilities: "整合架構設計、API設計"
    - scenario: "Refactoring"
      role: "Refactoring Architect"
      responsibilities: "重構架構設計"

  supporting_scenarios:
    - scenario: "DevOps"
      role: "Infrastructure Advisor"
      contributions: "基礎設施架構建議"
    - scenario: "Security"
      role: "Security Architecture"
      contributions: "安全架構審查"
    - scenario: "Testing"
      role: "Test Architecture"
      contributions: "測試架構設計"
    - scenario: "Documentation"
      role: "Technical Review"
      contributions: "技術文檔審查"
```

### 06. dev-developer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Sequential-Handoff"
      role: "Receiver"
      description: "接收SRD進行開發評估"
      applicable_scenarios: ["All scenarios"]
    - pattern: "Peer-Review"
      role: "Peer"
      description: "技術實作可行性審查"
      applicable_scenarios: ["All scenarios"]

scenario_usage:
  frequency: "High (6/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep"
  primary_scenarios:
    - scenario: "Greenfield"
      role: "Developer"
      responsibilities: "開發評估、實作建議"
    - scenario: "Brownfield"
      role: "Code Analyst"
      responsibilities: "既有代碼分析、改進建議"

  supporting_scenarios:
    - scenario: "Performance"
      role: "Performance Developer"
      contributions: "代碼層面效能優化"
    - scenario: "Integration"
      role: "Integration Developer"
      contributions: "API整合實作評估"
    - scenario: "Testing"
      role: "Testability Advisor"
      contributions: "可測試性建議"
    - scenario: "Refactoring"
      role: "Refactoring Developer"
      contributions: "重構實作評估"
```

### 07. qa-tester

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Sequential-Handoff"
      role: "Receiver"
      description: "接收SRD/FRD產出測試計畫"
      applicable_scenarios: ["All scenarios"]
    - pattern: "Peer-Review"
      role: "Peer"
      description: "測試性審查"
      applicable_scenarios: ["All scenarios"]

scenario_usage:
  frequency: "High (7/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep"
  primary_scenarios:
    - scenario: "Greenfield"
      role: "QA Engineer"
      responsibilities: "測試計畫、AC驗證、測試案例設計"
    - scenario: "Testing"
      role: "Test Lead"
      responsibilities: "測試策略、測試執行"

  supporting_scenarios:
    - scenario: "Performance"
      role: "Performance Tester"
      contributions: "效能測試計畫"
    - scenario: "Integration"
      role: "Integration Tester"
      contributions: "整合測試計畫"
    - scenario: "Security"
      role: "Security Tester"
      contributions: "安全測試計畫"
    - scenario: "Brownfield"
      role: "Regression Tester"
      contributions: "回歸測試策略"
    - scenario: "Refactoring"
      role: "Refactoring Validator"
      contributions: "重構驗證測試"
```

---

## 專業 Agents 更新規格

### code-analyzer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Support"
      description: "提供代碼分析專業支援"
      applicable_scenarios: ["Brownfield", "Refactoring"]
    - pattern: "Iterative-Refinement"
      role: "Analyzer"
      description: "迭代進行代碼品質改進"
      applicable_scenarios: ["Brownfield", "Refactoring"]

scenario_usage:
  frequency: "Medium (2/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐ Keep (Brownfield/Refactoring必需)"
  primary_scenarios:
    - scenario: "Brownfield"
      role: "Code Analyzer"
      responsibilities: "代碼結構分析、技術債務識別、品質評估"
    - scenario: "Refactoring"
      role: "Refactoring Advisor"
      responsibilities: "重構範圍識別、複雜度分析、重構建議"
```

### performance-engineer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導效能優化分析和策略"
      applicable_scenarios: ["Performance"]
    - pattern: "Iterative-Refinement"
      role: "Optimizer"
      description: "迭代效能優化"
      applicable_scenarios: ["Performance"]

scenario_usage:
  frequency: "Low (1/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐ Keep (Performance必需)"
  primary_scenarios:
    - scenario: "Performance"
      role: "Performance Lead"
      responsibilities: "效能剖析、瓶頸識別、優化策略、測量驗證"
```

### integration-specialist

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導系統整合分析和設計"
      applicable_scenarios: ["Integration"]
    - pattern: "Sequential-Handoff"
      role: "Provider"
      description: "產出整合規格交接給Dev"
      applicable_scenarios: ["Integration"]

scenario_usage:
  frequency: "Low (1/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐ Keep (Integration必需)"
  primary_scenarios:
    - scenario: "Integration"
      role: "Integration Lead"
      responsibilities: "API研究、認證設計、資料對應、錯誤處理策略"
```

### devops-engineer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導DevOps流程設計"
      applicable_scenarios: ["DevOps"]
    - pattern: "Parallel-Convergence"
      role: "Parallel Worker"
      description: "並行進行CI/CD和基礎設施配置"
      applicable_scenarios: ["DevOps"]

scenario_usage:
  frequency: "Low (1/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐ Keep (DevOps必需)"
  primary_scenarios:
    - scenario: "DevOps"
      role: "DevOps Lead"
      responsibilities: "CI/CD設計、容器化、監控設定、自動化部署"
```

### security-engineer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Peer-Review"
      role: "Primary"
      description: "主導安全審查"
      applicable_scenarios: ["Security", "All scenarios"]
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導安全設計"
      applicable_scenarios: ["Security"]

scenario_usage:
  frequency: "Medium (1/9 primary + cross-cutting)"
  irreplaceability: "⭐⭐⭐⭐⭐ Must Keep (Security必需)"
  primary_scenarios:
    - scenario: "Security"
      role: "Security Lead"
      responsibilities: "安全架構、威脅建模、安全測試、合規審查"

  supporting_scenarios:
    - scenario: "Greenfield"
      role: "Security Advisor"
      contributions: "安全設計建議"
    - scenario: "Integration"
      role: "Integration Security"
      contributions: "API安全審查"
```

### qa-lead

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Parallel-Convergence"
      role: "Coordinator"
      description: "整合多平台測試結果"
      applicable_scenarios: ["Testing"]
    - pattern: "Lead-Support"
      role: "Lead"
      description: "主導測試策略制定"
      applicable_scenarios: ["Testing"]

scenario_usage:
  frequency: "Medium (3/9 scenarios)"
  irreplaceability: "⭐⭐⭐ Keep (與qa-tester互補)"
  primary_scenarios:
    - scenario: "Testing"
      role: "Test Strategy Lead"
      responsibilities: "測試策略、團隊協調、品質管理"

  supporting_scenarios:
    - scenario: "Greenfield"
      role: "QA Strategy"
      contributions: "測試策略建議"
    - scenario: "Security"
      role: "Security Test Lead"
      contributions: "安全測試策略"
```

### qa-automation

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Lead-Support"
      role: "Support"
      description: "提供測試自動化專業支援"
      applicable_scenarios: ["Testing", "DevOps", "Performance"]
    - pattern: "Parallel-Convergence"
      role: "Parallel Worker"
      description: "並行進行自動化測試開發"
      applicable_scenarios: ["Testing"]

scenario_usage:
  frequency: "Medium (3/9 scenarios)"
  irreplaceability: "⭐⭐⭐ Keep (與qa-tester互補)"
  primary_scenarios:
    - scenario: "Testing"
      role: "Automation Engineer"
      responsibilities: "自動化框架選擇、自動化測試開發"

  supporting_scenarios:
    - scenario: "DevOps"
      role: "CI/CD Testing"
      contributions: "自動化測試整合"
    - scenario: "Performance"
      role: "Performance Test Automation"
      contributions: "效能測試自動化"
```

### technical-writer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Sequential-Handoff"
      role: "Receiver"
      description: "接收技術產出轉化為文檔"
      applicable_scenarios: ["Documentation"]
    - pattern: "Peer-Review"
      role: "Peer"
      description: "文檔品質審查"
      applicable_scenarios: ["Documentation"]

scenario_usage:
  frequency: "Medium (2/9 scenarios)"
  irreplaceability: "⭐⭐⭐ Keep (Documentation必需)"
  primary_scenarios:
    - scenario: "Documentation"
      role: "Documentation Lead"
      responsibilities: "技術文檔撰寫、知識庫建立、API文檔"

  supporting_scenarios:
    - scenario: "Greenfield"
      role: "Documentation Support"
      contributions: "文檔結構建議"
```

### dev-senior

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Peer-Review"
      role: "Peer"
      description: "資深技術審查"
      applicable_scenarios: ["Brownfield", "Refactoring", "Complex scenarios"]
    - pattern: "Lead-Support"
      role: "Support"
      description: "提供資深開發建議"
      applicable_scenarios: ["Brownfield", "Performance"]

scenario_usage:
  frequency: "Medium (4/9 scenarios)"
  irreplaceability: "⭐⭐⭐ Keep (Brownfield複雜決策必需)"
  primary_scenarios:
    - scenario: "Brownfield"
      role: "Senior Advisor"
      responsibilities: "複雜技術決策、架構評估"
    - scenario: "Refactoring"
      role: "Refactoring Lead"
      responsibilities: "重構策略、技術風險評估"

  supporting_scenarios:
    - scenario: "Performance"
      role: "Performance Code Reviewer"
      contributions: "代碼層面效能建議"
    - scenario: "Documentation"
      role: "Technical Reviewer"
      contributions: "複雜技術文檔審查"
```

### compliance-officer

```yaml
collaboration_patterns:
  primary_patterns:
    - pattern: "Peer-Review"
      role: "Peer"
      description: "合規審查"
      applicable_scenarios: ["Security"]
    - pattern: "Lead-Support"
      role: "Support"
      description: "提供合規專業建議"
      applicable_scenarios: ["Security"]

scenario_usage:
  frequency: "Low (1/9 scenarios)"
  irreplaceability: "⭐⭐⭐⭐ Keep (Security必需)"
  primary_scenarios:
    - scenario: "Security"
      role: "Compliance Reviewer"
      responsibilities: "法規遵循審查、審計準備、合規文檔"
```

---

## 批次更新指令

### 方式1：手動逐一更新
```bash
# 對每個Agent檔案，在agent:區塊後加入對應的SDD v0.01配置
# 參考sa-analyst已完成的更新
```

### 方式2：使用腳本批次更新
```bash
# 創建更新腳本後執行
cd AISDLC_SDD_v0.01/agent
# 執行批次更新腳本（v0.01 已完成）
```

---

## 驗證清單（v0.01 SDD 標準）

更新完成後驗證：
- [x] 所有 Agent 都有 collaboration_patterns 欄位
- [x] 所有 Agent 都有 scenario_usage 欄位
- [x] frequency 正確（High/Medium/Low + 數量）
- [x] irreplaceability 星級評分正確
- [x] primary_scenarios 至少有 1 個
- [x] YAML 語法正確（無縮排錯誤）
- [x] 所有 Agent 標明負責的 SCG 閘門（v0.01 新增）
- [x] 核心 Agents 標明 SDD 新增技能（v0.01 新增）
- [x] 版本號更新至 v0.01

---

**最後更新**: 2026-04-17
**狀態**: AISDLC-SDD v0.01 全部 21 個 Agents 更新完成
