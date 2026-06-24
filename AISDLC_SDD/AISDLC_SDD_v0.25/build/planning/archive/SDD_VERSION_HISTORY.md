# AISDLC-SDD 版本歷程

**文件用途**: 記錄 AISDLC-SDD 框架每個版本的變更內容
**最後更新**: 2026-04-15

---

## v0.01（2026-04-14）— 初始版本

### 版本類型
初始建立（基於 AISDLC v0.09 全面改版）

### 核心新增：SDD 三大支柱

| 支柱 | 說明 |
|------|------|
| Spec-First Gate（SCG） | 7 個閘門（SCG-0~6），確保規格先於實作 |
| Design-as-Doc | 所有技術決策必須有 ADR；架構必須有 C4 圖 |
| Contract-Driven | OpenAPI 3.1 凍結後才允許後端實作 |

### 新增內容

**SDD 專屬文件**：
- `AISDLC_SDD_INIT.md` — 框架入口（含 SCG 閘門說明）
- `SDD_Core_Principles.md` — SDD 三大支柱詳細說明
- `FILE_DIRECTORY_RULES.md` — 完整目錄規則
- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` — SCG 閘門執行流程

**SDD Scenarios Enhancement（10 個）**：
- `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
- `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`
- `scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md`
- `scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md`
- `scenarios/testing/SDD_TESTING_ENHANCEMENT.md`
- `scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md`
- `scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md`
- `scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md`
- `scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md`
- `scenarios/security/SDD_SECURITY_ENHANCEMENT.md`

**SDD 文件模板（60+ 個）**：
- `docs_template/sdd/requirements/` — PRD, FRD, Invariant Spec
- `docs_template/sdd/architecture/` — SRD, C4, ADR, As-Is, To-Be, API-Compat
- `docs_template/sdd/testing/` — RTM, Test Plan, Invariant Contract
- `docs_template/sdd/planning/` — Gap Analysis, Refactor Plan
- `docs_template/sdd/development/` — Living Doc Strategy
- `docs_template/sdd/quality/` — Code Quality Baseline, Tech Debt
- `docs_template/sdd/design/` — UI/UX, Database Design
- `docs_template/sdd/deployment/` — CI/CD Pipeline, Release Notes

**SDD 專屬 Skills（5 個新增）**：
- `adr-generate` — ADR 自動生成
- `contract-generate` — API Contract 生成（OpenAPI 3.1）
- `rtm-generate` — 需求追蹤矩陣生成
- `sdd-gate` — SCG 閘門驗證
- `spec-compliance-check` — 規格合規性檢查

**SDD CI/CD 規格（5 個）**：
- `cicd/SDD_TESTING_CICD.md`
- `cicd/SDD_PERFORMANCE_CICD.md`
- `cicd/SDD_SECURITY_CICD.md`
- `cicd/SDD_MIGRATION_CICD.md`
- `cicd/SDD_INTEGRATION_CICD.md`

**跨場景指南（v0.01 後續補充，2026-04-15）**：
- `scenarios/README.md`
- `scenarios/SCENARIO_AGENT_MAPPING.md`
- `scenarios/ERROR_RECOVERY_GUIDE.md`
- `scenarios/SCALING_GUIDE.md`
- `scenarios/FRONTEND_SPECIFIC_GUIDE.md`
- `scenarios/SCENARIO_TRANSITION_GUIDE.md`

**Prompts 目錄（2026-04-15 補充）**：
- `prompts/quick-start/` — 4 個快速啟動指引
- `prompts/complete-flow/` — 2 個完整流程範例
- `prompts/scenario-prompts/` — 10 個場景專用指令集

**版本控管文件（2026-04-15 補充）**：
- `AISDLC_SDD_UPGRADE_SOP.md`
- `AISDLC_SDD_UPGRADE_CHECKLIST.md`
- `SDD_VERSION_HISTORY.md`（本文件）

### Agent 改善（38 個 Skills 全面改版）
全部 38 個 Skills 更新為 SDD 原生設計，引用 SDD 工作流程和 SCG 閘門。

### 已知限制
- 缺少英文版 Agent backup（`backup_en/`）— 低優先，SDD 以中文為主
- `guides/user/sample/` 下的場景範例尚未更新為 SDD 版本

---

## 升版計畫（v0.02 預計改善）

（根據框架完整性審查 Phase 07 報告）

| ID | 改善項目 | 優先級 |
|----|---------|-------|
| W-01 | 驗證 13 個 scenario-specific workflows SCG 整合 | 🟡 中 |
| G-01 | 更新 guides/user/sample/ 場景範例為 SDD 版 | 🟢 低 |
| S-02 | 新增 sdd-review skill（SCG-4 PR Review 輔助） | 🟢 低 |

---

**最後更新**: 2026-04-15
