# Specialized Agents — 選用指引與 SDD 技能對應

**框架版本**: AISDLC-SDD v0.01
**最後更新**: 2026-04-15

---

## 14 個 Specialized Agents

| 檔案 | Agent 角色 | 適用場景 | SDD 技能 |
|------|-----------|---------|---------|
| `code-analyzer-zh.yaml` | 代碼分析師 | Brownfield/Refactoring | Tech Debt 規格化（TD-XXX）、品質基準線 |
| `compliance-officer-zh.yaml` | 合規官 | Security | GDPR/HIPAA/PCI-DSS 合規審查 |
| `dev-senior-zh.yaml` | 資深開發師 | Refactoring | Strangler Fig、Branch by Abstraction |
| `devops-engineer-zh.yaml` | DevOps 工程師 | DevOps | SCG 閘門整合 Pipeline |
| `integration-specialist-zh.yaml` | 整合專家 | Integration | Consumer Contract、Consumer-Driven Testing |
| `performance-engineer-zh.yaml` | 效能工程師 | Performance | PBS SLO 定義、Benchmark 設計 |
| `qa-automation-zh.yaml` | QA 自動化 | Testing/DevOps | Contract Test 自動化 |
| `qa-lead-zh.yaml` | QA 主管 | Testing | 測試策略、測試金字塔設計 |
| `qa-mobile-tester-zh.yaml` | 行動端 QA | Mobile Testing | Mobile E2E 測試策略 |
| `qa-web-tester-zh.yaml` | Web QA | Web Testing | Web E2E 測試、可及性測試 |
| `sd-mobile-architect-zh.yaml` | Mobile 架構師 | Greenfield Mobile | iOS/Android/跨平台架構設計 |
| `sd-web-architect-zh.yaml` | Web 架構師 | Greenfield Web | Web 系統架構、前後端分離設計 |
| `security-engineer-zh.yaml` | 安全工程師 | Security | STRIDE 威脅模型、OWASP Top 10 |
| `technical-writer-zh.yaml` | 技術寫作師 | Documentation | Living Doc 策略、ADR 維護 |

---

## SDD 特殊職責

### Code Analyzer — Brownfield/Refactoring 核心
- **Tech Debt 規格化**：將技術問題轉換為 TD-XXX 格式的技術債
- **品質基準線**：建立 Code Quality Baseline（複雜度/覆蓋率/耦合度）
- 配合工具：`verify_traceability.sh`

### Dev Senior — Refactoring 核心
- **Strangler Fig 策略**：逐步替換舊系統的重構策略
- **Branch by Abstraction**：大型系統重構的並行開發策略
- SCG-4 驗證：確保重構後實作符合原始規格

### Integration Specialist — Integration 核心
- **Consumer Contract 定義**：Consumer-Driven Contract 設計
- **Contract-First 整合**：API Contract 凍結後才實作（SCG-3）
- 支援：Pact、OpenAPI Contract、Webhook 設計

### Performance Engineer — Performance 核心
- **PBS SLO 定義**：Performance Baseline Specification + SLO
- **Benchmark 設計**：負載測試計畫（k6/Gatling/JMeter）
- SCG-6 PBS Gate 驗證

### Security Engineer — Security 核心
- **STRIDE 威脅模型**：系統性安全威脅識別與評估
- **OWASP Top 10 審查**：代碼/架構安全審查
- SCG-5 STRIDE Validate

### Technical Writer — Documentation 核心
- **Living Documentation 策略**：文件與代碼同步的維護策略
- **ADR Archaeology**：重建歷史架構決策記錄
- RTM 文件維護

---

## 選用指引

### 按場景選擇

| 場景 | 建議的 Specialized Agents |
|------|--------------------------|
| Greenfield Web | sd-web-architect, qa-web-tester |
| Greenfield Mobile | sd-mobile-architect, qa-mobile-tester |
| Brownfield | code-analyzer |
| Refactoring | code-analyzer, dev-senior |
| Documentation | technical-writer |
| Testing | qa-lead, qa-automation |
| DevOps | devops-engineer |
| Integration | integration-specialist |
| Migration | integration-specialist, qa-automation |
| Performance | performance-engineer |
| Security | security-engineer, compliance-officer |

### 按需載入原則
- Specialized Agents 按需載入，不預先全部載入
- 主要情境需要時才調用
- 避免同時載入過多 Agents（Token 效率考量）

---

## 參考

- Core Agents：[../core/README.md](../core/README.md)
- 場景 Agent 對應表：`AISDLC_SDD_v0.01/scenarios/SCENARIO_AGENT_MAPPING.md`
