# 情境 Agent 配置映射表（SDD 版）
# Scenario-Agent Mapping Guide — SDD Edition

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01 SCENARIO_AGENT_MAPPING
**最後更新**: 2026-04-15
**用途**: 定義每個 SDD 情境使用的 Agents、SDD 專屬技能與 SCG 閘門對應

---

## 📋 SDD 新增說明

本文件在 v0.01 Agent 配置基礎上，新增：
1. **SDD Skills 對應** — 每個情境使用的 SDD 專屬 Skills
2. **SCG 閘門責任** — 哪個 Agent 負責觸發/驗證哪個閘門
3. **SDD 必要產出** — 每個情境的規格文件清單

---

## 🎯 情境 Agent 配置總覽

| 情境 | Primary Agents | Supporting Agents | SDD Skills | SCG 閘門 |
|------|---------------|-------------------|-----------|---------|
| **Greenfield** | pm-po, sa-analyst | ba, sd, qa, dev; 選用: security, compliance, sd-mobile, qa-mobile, integration | sdd-gate, rtm-generate, adr-generate, contract-generate | SCG-0~6 |
| **Brownfield** | sa-analyst, dev-senior | code-analyzer, qa, sd; 選用: security, compliance, sd-mobile, qa-mobile, integration | sdd-gate, spec-compliance-check, rtm-generate | SCG-0, SCG-4 |
| **Refactoring** | sa-analyst, sd-architect | code-analyzer, dev-senior, qa | sdd-gate, spec-compliance-check, rtm-generate | INV Gate, SCG-4 |
| **Migration** | sd-architect, sa-analyst | code-analyzer, dev-senior, qa, devops, integration | sdd-gate, contract-generate, adr-generate | MCM + SCG-3 |
| **Performance** | performance-engineer | sd, dev-senior, qa-automation; 選用: devops, code-analyzer, security | sdd-gate, spec-compliance-check | PBS Gate + SCG-6 |
| **Integration** | integration-specialist | sd, qa, dev | sdd-gate, contract-generate, spec-compliance-check | Consumer Contract + SCG-3 |
| **DevOps** | devops-engineer | sd, qa-automation | sdd-gate, spec-compliance-check | Pipeline Spec + SCG-4 |
| **Testing** | qa-lead | qa-automation, qa-tester, dev | sdd-gate, rtm-generate, spec-compliance-check | RTM + SCG-5 |
| **Documentation** | technical-writer | sa, sd, dev-senior; 選用: security, compliance, sd-mobile | sdd-gate, spec-compliance-check | Living Doc + SCG-4 |
| **Security** | security-engineer | compliance-officer, qa-lead, sd | sdd-gate, spec-compliance-check, rtm-generate | STRIDE + SCG-5 |

---

## 🔹 Greenfield — 全新專案開發

### Agent 配置
```yaml
Primary Agents:
  - pm-po-agent (Lead):   PRD、業務優先級決策
  - sa-analyst:           FRD、User Stories、Invariant Spec

Supporting Agents:
  - ba-business-analyst:  業務驗證、PRD/FRD 審查
  - sd-architect:         SRD、C4 Model、ADR、API Spec
  - qa-tester:            RTM、Test Strategy Spec
  - dev-developer:        實作可行性評估

Optional Agents: ⭐
  - security-engineer:    STRIDE 威脅模型（Stage 3）
  - compliance-officer:   合規需求（Stage 3）
  - sd-mobile-architect:  行動端架構（Stage 3）
  - qa-mobile-tester:     行動端測試（Stage 6）
  - integration-specialist: 第三方整合分析（Stage 2）
```

### SDD 必要產出（依 SCG 閘門順序）
| SCG | 必要產出 | 負責 Agent |
|-----|---------|-----------|
| SCG-0 | PRD + FRD（完整性） | pm-po + sa-analyst |
| SCG-1 | SRD + API Spec | sd-architect |
| SCG-2 | C4 Model + ADR | sd-architect |
| SCG-3 | OpenAPI 3.1 凍結 | sd-architect |
| SCG-4 | 實作與規格一致性 | dev-developer |
| SCG-5 | RTM 100% 覆蓋 | qa-tester |
| SCG-6 | 所有閘門通過 | qa-lead |

### 協作模式: Lead-Support + Sequential-Handoff（SCG 驅動）
```
pm-po PRD → SCG-0 🔴 → sa-analyst FRD → sd-architect SRD → SCG-1 🔴
→ C4+ADR → SCG-2 🔴 → OpenAPI → SCG-3 🔴 → 開發 → SCG-4 🔴 → SCG-6 🔴
```

---

## 🔹 Brownfield — 既有系統分析（逆向規格工程）

### Agent 配置
```yaml
Primary Agents:
  - sa-analyst (Lead):    As-Is 規格逆向、Gap Analysis
  - dev-senior:           技術債規格化、改進建議

Supporting Agents:
  - code-analyzer:        代碼品質分析、Tech Debt Spec
  - qa-tester:            As-Is 測試規格、測試差距識別
  - sd-architect:         As-Is C4 Model、ADR Archaeology

Optional Agents: ⭐
  - security-engineer:    安全漏洞修復規格（Stage 3）
  - compliance-officer:   合規驅動變更分析（Stage 3）
  - sd-mobile-architect:  行動端架構評估（Stage 2）
  - qa-mobile-tester:     行動端測試（Stage 6）
  - integration-specialist: 外部 API 整合分析（Stage 4）
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 逆向分析 | As-Is SRD + Tech Debt Spec | sa-analyst + code-analyzer |
| 規格化 | Gap Analysis + To-Be SRD | sa-analyst + sd-architect |
| 凍結 | SCG-0（改造需求凍結） | sa-analyst |
| 實作 | SCG-4 PR Review（改造與規格一致） | dev-senior |

### 協作模式: Lead-Support + Reverse Engineering
```
code-analyzer 掃描 → sa-analyst As-Is 規格化 → sd-architect ADR Archaeology
→ SCG-0 🔴 → Gap Analysis → To-Be 設計 → 改造 → SCG-4 🔴
```

---

## 🔹 Refactoring — 系統重構（Business Invariants 保護）

### Agent 配置
```yaml
Primary Agents:
  - sa-analyst (Lead):    Business Invariants 提取與確認
  - sd-architect:         重構策略、Before/After 架構對比

Supporting Agents:
  - code-analyzer:        重構範圍識別、複雜度分析
  - dev-senior:           重構技術決策、Strangler Fig / Branch by Abstraction
  - qa-tester:            Invariant Test Contract、回歸測試計畫
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 前置 | Business Invariants（INV-XXX） | sa-analyst |
| 設計 | Before Arch + Refactor Plan | sd-architect |
| 閘門 | INV Gate（Invariants 凍結確認） | sa-analyst 🔴 |
| 實作 | Invariant Test Contract | qa-tester |
| PR | SCG-4（重構不破壞 Invariants） | dev-senior |

### 協作模式: Lead-Support + Invariant-Driven
```
sa-analyst 提取 Invariants → INV Gate 🔴 → sd-architect 設計重構
→ dev-senior 實作 → qa-tester Invariant Contract 驗證 → SCG-4 🔴
```

---

## 🔹 Migration — 技術棧遷移（Contract-Driven）

### Agent 配置
```yaml
Primary Agents:
  - sd-architect (Lead):  遷移架構設計、Contract Map、Before/After 對比
  - sa-analyst:           需求重新分析、業務邏輯提取

Supporting Agents:
  - code-analyzer:        舊系統代碼分析、遷移影響評估
  - dev-senior:           跨平台開發指導、遷移技術決策
  - qa-tester:            遷移驗證測試、資料一致性驗證
  - devops-engineer:      並行部署、藍綠切換策略
  - integration-specialist: 新舊系統路由、API Gateway

Optional Agents:
  - performance-engineer: 遷移後效能基準測試（Stage 7）
  - security-engineer:    新系統安全審查（Stage 7）
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 分析 | As-Is SRD + Migration ADR | sa-analyst + sd-architect |
| 設計 | Contract Map + To-Be SRD | sd-architect |
| 閘門 | MCM Validate（Contract Map 凍結） | sd-architect 🔴 |
| Contract | SCG-3（API Contract 凍結） | sd-architect 🔴 |
| 執行 | 分層遷移 + 驗證報告 | dev-senior + qa-tester |

### 協作模式: Lead-Support + Sequential-Handoff
```
As-Is 分析 → MCM Validate 🔴 → SCG-3 🔴 → 分層遷移（DB→後端→前端）
→ 並行運行驗證 → 切換確認 🔴
```

---

## 🔹 Performance — 效能優化（PBS Spec 先行）

### Agent 配置
```yaml
Primary Agent:
  - performance-engineer (Lead): PBS 定義、效能分析、優化策略

Supporting Agents:
  - sd-architect:        架構層面優化建議
  - dev-senior:          代碼層面優化
  - qa-automation:       效能測試自動化、持續監控

Optional Agents: ⭐
  - devops-engineer:     基礎設施優化（Stage 4）
  - code-analyzer:       代碼級效能分析（Stage 2）
  - security-engineer:   安全與效能權衡（Stage 3）
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 前置 | Performance Baseline Spec + SLO 定義 | performance-engineer |
| 閘門 | PBS Gate（SLO 凍結確認） | performance-engineer 🔴 |
| 執行 | 優化方案 + Benchmark 結果 | performance-engineer + qa-automation |
| 驗收 | SCG-6（SLO 達標確認） | performance-engineer 🔴 |

### 協作模式: Lead-Support + Iterative-Refinement
```
PBS Gate 🔴（SLO 凍結）→ 識別瓶頸 → 優化 → 測量
→ 達標? → 是 → SCG-6 🔴 / 否 → 繼續迭代
```

---

## 🔹 Integration — 第三方系統整合（Consumer Contract）

### Agent 配置
```yaml
Primary Agent:
  - integration-specialist (Lead): API 研究、Consumer Contract 撰寫、整合設計

Supporting Agents:
  - sd-architect:       整合架構設計、Trust Boundary Map
  - qa-tester:          Consumer Contract 測試、整合測試計畫
  - dev-developer:      整合實作
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 研究 | Third-Party API Research + Consumer Contract | integration-specialist |
| 閘門 | SCG-3（Consumer Contract 凍結） | integration-specialist 🔴 |
| 實作 | API Client + Contract Tests | dev-developer + qa-tester |
| PR | SCG-4（實作符合 Contract） | dev-developer 🔴 |

### 協作模式: Lead-Support + Contract-First
```
API 研究 → Consumer Contract 撰寫 → SCG-3 🔴 → 實作 → SCG-4 🔴
```

---

## 🔹 DevOps — CI/CD 建置（Pipeline Spec 先行）

### Agent 配置
```yaml
Primary Agent:
  - devops-engineer (Lead): Pipeline Spec 設計、CI/CD 實作、監控配置

Supporting Agents:
  - sd-architect:       基礎設施架構、IaC 規格
  - qa-automation:      自動化測試整合 CI/CD
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 設計 | Pipeline Spec + Monitoring Alert Spec | devops-engineer |
| 建置 | CI/CD Pipeline + IaC | devops-engineer |
| PR | SCG-4（Pipeline 與 Spec 一致） | devops-engineer 🔴 |
| 發布 | SCG-6（所有 Gate 通過） | devops-engineer 🔴 |

### 協作模式: Lead-Support + Parallel-Convergence
```
Pipeline Spec → SCG-4 🔴 →
  devops: CI/CD ∥ qa-auto: Test Integration ∥ sd: Infra
→ 整合 → SCG-6 🔴
```

---

## 🔹 Testing — 測試策略與自動化（RTM Gate）

### Agent 配置
```yaml
Primary Agent:
  - qa-lead (Lead): Test Strategy Spec、RTM 完整性驗證

Supporting Agents:
  - qa-automation:  自動化測試框架、Invariant Contract Tests
  - qa-tester:      測試案例設計與執行
  - dev-developer:  可測試性支援
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 策略 | Test Strategy Spec + RTM | qa-lead |
| 閘門 | SCG-5（RTM 100% 需求覆蓋） | qa-lead 🔴 |
| 執行 | 測試結果 + Living Test Report | qa-tester + qa-automation |
| 驗收 | SCG-6（測試通過確認） | qa-lead 🔴 |

### 協作模式: Parallel-Convergence
```
RTM Gate 🔴（覆蓋確認）→ 分工執行：
  qa-auto（自動化）∥ qa-tester（手動）∥ qa-mobile（行動端）
→ qa-lead 整合 → SCG-5 🔴 → SCG-6 🔴
```

---

## 🔹 Documentation — 技術文檔（Living Documentation）

### Agent 配置
```yaml
Primary Agent:
  - technical-writer (Lead): Living Doc Strategy、API 文檔、知識庫

Supporting Agents:
  - sa-analyst:      功能文檔審查
  - sd-architect:    架構圖、ADR 更新
  - dev-senior:      複雜技術細節審查、代碼範例

Optional Agents: ⭐
  - security-engineer:     安全架構文檔（Stage 6）
  - compliance-officer:    合規文檔（Stage 6）
  - sd-mobile-architect:   行動端安全規範（Stage 6）
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 策略 | Living Doc Strategy | technical-writer |
| 撰寫 | API 文檔、架構文檔、ADR | technical-writer + sd-architect |
| PR | SCG-4（文檔與實作一致） | technical-writer 🔴 |

---

## 🔹 Security — 安全合規（STRIDE 先行）

### Agent 配置
```yaml
Primary Agent:
  - security-engineer (Lead): STRIDE 威脅模型、安全架構設計、安全測試計畫

Supporting Agents:
  - compliance-officer:  合規審查、稽核準備
  - qa-lead:             安全測試策略
  - sd-architect:        架構安全審查
```

### SDD 必要產出
| 階段 | 必要產出 | 負責 Agent |
|------|---------|-----------|
| 前置 | STRIDE Threat Model + Trust Boundary Map | security-engineer |
| 閘門 | SCG-5（安全需求 RTM 100%） | security-engineer 🔴 |
| 審查 | 安全測試報告 + 合規對照表 | qa-lead + compliance-officer |
| 驗收 | SCG-6（安全審查通過） | security-engineer 🔴 |

### 協作模式: Peer-Review + STRIDE-Driven
```
STRIDE 威脅模型 → security-engineer 設計
→ sd + qa-lead peer review → compliance-officer 合規審查
→ SCG-5 🔴 → SCG-6 🔴
```

---

## 📊 Agent 使用頻率統計（SDD 版）

### High Frequency
```yaml
sa-analyst:    10/10（所有情境）— SDD 新增: As-Is 規格化、Invariants 提取
sd-architect:   9/10（含 Migration 主力）— SDD 新增: C4、ADR、Contract Map
qa-tester:      8/10（含 RTM、Contract Tests）
```

### Medium Frequency
```yaml
dev-senior:         5/10（Brownfield/Refactoring/Migration 主力）
dev-developer:      4/10
qa-automation:      4/10（含 Invariant Contract Tests）
security-engineer:  4/10（Security 主導 + Greenfield/Brownfield/Performance 選配）
code-analyzer:      3/10（Brownfield/Refactoring/Migration）
integration-specialist: 2/10（Integration 主導 + Migration）
```

### SDD Skills 使用對應
```yaml
sdd-gate:               所有情境（SCG 閘門驗證）
spec-compliance-check:  Brownfield/Refactoring/Performance/DevOps/Documentation/Security
rtm-generate:           Greenfield/Brownfield/Refactoring/Testing/Security
contract-generate:      Greenfield/Migration/Integration
adr-generate:           Greenfield/Migration
```

---

---

## 📊 各情境關鍵 SCG 閘門對照說明

本段落統整各情境的關鍵 SCG 閘門，幫助 Agent 和使用者快速掌握每個情境的品質守門重點。

| 情境 | 前置條件 | 關鍵 SCG 閘門 | 進入下一情境的最低要求 |
|------|---------|--------------|---------------------|
| **Greenfield** | 無（新專案）| SCG-0（需求凍結）→ SCG-3（Contract Freeze）→ SCG-5（RTM 100%）→ SCG-6 | SCG-4 通過（轉 Testing / DevOps） |
| **Brownfield** | 無前置 SCG，但必須先完成 As-Is 逆向規格工程 | SCG-0（改造需求凍結，基於 Gap Analysis）→ SCG-4（改造 PR Review）| SCG-0 通過（轉 Refactoring / Performance / Integration）|
| **Refactoring** | SCG-0（Brownfield 改造需求凍結或獨立 Refactoring 需求）| INV Gate（Business Invariants 凍結，核心閘門）→ SCG-4（重構不破壞 Invariants）| INV Gate + SCG-4 通過 |
| **Migration** | As-Is SRD 完成，Migration ADR 建立 | MCM Validate（Contract Map 凍結）→ SCG-3（Contract Freeze）→ SCG-4（每層遷移）| MCM + SCG-3 通過 |
| **Performance** | SCG-0 通過（有量化 NFR）| PBS Gate（SLO 量化凍結，開始優化前必須）→ SCG-6（SLO 達標確認）| PBS Gate 通過 |
| **Integration** | SCG-0 通過，已有 API 研究 | Consumer Contract → SCG-3（Contract Freeze）→ SCG-4（實作與 Contract 一致）| SCG-3 通過 |
| **DevOps** | SCG-2 通過（架構已凍結）| Pipeline Spec 設計先行 → SCG-4（Pipeline 與 Spec 一致）→ SCG-6（發布確認）| SCG-4 通過 |
| **Testing** | SCG-3 通過（有 Contract 可測試）| RTM Gate（覆蓋率確認）→ SCG-5（RTM 100%）→ SCG-6（測試全通過）| SCG-5 通過 |
| **Documentation** | SCG-2 通過（有架構可記錄）| Living Doc Strategy 先行 → SCG-4（文檔與實作一致）| SCG-4 通過 |
| **Security** | STRIDE 威脅模型先行（在任何安全設計前）| STRIDE 完成 → SCG-5（安全需求 RTM 100%）→ SCG-6（安全審查通過）| STRIDE + SCG-5 通過 |

### 特殊情境說明

**Brownfield — SCG-0 前必須建立 As-Is 基線**

Brownfield 是唯一在執行 SCG-0 前有前置步驟的情境。進入 SCG-0（改造需求凍結）之前，必須先完成：
1. 逆向規格工程（code-analyzer + sa-analyst 協作）
2. 產出 As-Is SRD + Tech Debt Spec（TD-XXX）
3. 完成 Gap Analysis（現狀 vs 目標）
4. 基於 Gap Analysis 定義 To-Be 改造需求（才是 SCG-0 的輸入）

**Refactoring — INV Gate 是核心，非 SCG-0**

Refactoring 的核心閘門是 Business Invariants Gate（INV Gate），而非標準 SCG-0。INV Gate 的產出是 `Invariant_Spec.md`（含 INV-XXX 格式的業務不變量清單），凍結後整個重構過程都以保護這些 Invariants 為最高原則。SCG-4 的 PR Review 核心檢查即為「重構不破壞任何 INV-XXX」。

**Performance — PBS Gate 必須在優化執行前完成**

Performance 的 PBS Gate（Performance Baseline Spec Gate）必須在任何優化執行前完成，確保：
- SLO 量化目標已定義（例如：API P99 < 200ms）
- 現有基準測量已完成（Baseline Benchmark）
- 優化假說已記錄（ADR 格式）

沒有量化 SLO 就執行優化，無法客觀評估優化是否成功。

---

## 📚 相關文檔

- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` — SCG 閘門詳細執行規範
- `agent/AGENT_COLLABORATION_PATTERNS.md` — 協作模式詳細說明（含 SDD SCG 閘門協作模式）
- `agent/core/*.yaml` — 各 Agent 的詳細配置
- `scenarios/*/SDD_*_ENHANCEMENT.md` — 各情境 SDD 增強說明
- `scenarios/SCENARIO_TRANSITION_GUIDE.md` — 情境切換前 SCG 驗證規範

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
**最後更新**: 2026-04-17
