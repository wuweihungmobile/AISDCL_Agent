# AISDLC-SDD Framework CHANGELOG

**維護者**: AISDLC-SDD Framework Team
**最後更新**: 2026-06-12

---

## [v0.02] - 2026-06-12（Copy-on-Evolve 自 v0.01；v0.01 凍結唯讀）

### 新增（Phase Z — AutoClaude 執行引擎橋接，ACT-162~171）
- `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` — SDD 文件 → AutoClaude playbook 標準作業（compile-then-run 兩段式）
- `agent/specialized/sdd-playbook-compiler-zh.yaml` — SDD Playbook 編譯專家角色
- `governance/rules/R-9.38-playbook-translation-fidelity.yaml` — AT↔step 100% 雙向映射保真規則（違反→SPEC_AUDIT）
- 10 場景 SOP 各加「AutoClaude 自動化執行」小節（QuickRef 同步）
- `EVOLUTION_LOG.md` — 版本演化紀錄（含 TLC 證據與回退指引）

### 修正（AutoSDD_Defect_Log 分流項）
- DEF-01-001：`governance/RULES_INDEX.md` 計數過期（35→39 檔）+ next-act/next-rule 前緣同步
- DEF-01-002：`tools/fsm_runtime/formal/run_tlc.sh` 補「五軌請走 tlc_runner.py」legacy 註記
- DEF-01-003：補 `tools/__init__.py` 顯式 package 宣告

### 形式化驗證
- `_HAPPY_PATH` / `*.tla` 零修改 → 五軌 TLC 既有證明維持有效（N/A）；
  `AUTOCLAUDE_DELEGATED` 觀察態維持提案（落地前置條件見 SDD_AUTOCLAUDE_BRIDGE.md §5）

---

## [v0.01] - 2026-04-17

### 新增（SDD 轉型）

#### SDD 核心機制
- 整合 SDD Spec-First Gate（SCG-0~SCG-6）機制，建立 7 道規格品質閘門
- 新增 SDD Core Principles（`guides/system/sdd/SDD_Core_Principles.md`）— 三大支柱定義
- 新增 SDD Guide（`guides/system/sdd/SDD_GUIDE.md`）— SDD 快速指引

#### SDD Skills（6 個新增）
- `sdd-gate` — 執行 SCG 閘門驗證（所有情境通用）
- `sdd-review` — SCG-4 PR Review 輔助，驗證實作與規格一致性
- `spec-compliance-check` — SDD 文件格式與完整性驗證
- `rtm-generate` — 生成/更新需求追溯矩陣（RTM），確保 SCG-5 100% 覆蓋
- `contract-generate` — 生成 API Contract（OpenAPI 3.1）或 Consumer-Driven Contract
- `adr-generate` — 生成 Architecture Decision Record（ADR）

#### SDD 文檔模板（51+ 個）
- 新增 `docs_template/sdd/` 目錄，含 51+ 個 SDD 專屬文檔模板
- 涵蓋：需求（PRD/FRD/Invariant Spec）、架構（SRD/C4/ADR/As-Is/Trust Boundary）、測試（RTM/Contract Test Spec/Invariant Test Contract）、規劃（Gap Analysis/PBS/Refactor Plan）、品質（Tech Debt Spec/Code Quality Baseline）、安全（SAD/STRIDE/Compliance Matrix）、部署（Pipeline Spec/IaC Spec/Runbook）等

#### SDD CI/CD 規格（9 個）
- `cicd/SDD_CICD_BASE_LAYER.md` — 基礎層（全場景通用）
- `cicd/SDD_GREENFIELD_CICD.md` — Greenfield 場景
- `cicd/SDD_BROWNFIELD_CICD.md` — Brownfield 場景
- `cicd/SDD_REFACTORING_CICD.md` — Refactoring 場景
- `cicd/SDD_TESTING_CICD.md` — Testing 場景
- `cicd/SDD_PERFORMANCE_CICD.md` — Performance 場景
- `cicd/SDD_SECURITY_CICD.md` — Security 場景
- `cicd/SDD_MIGRATION_CICD.md` — Migration 場景
- `cicd/SDD_INTEGRATION_CICD.md` — Integration 場景

#### SDD 場景增強文件（10 個）
- 新增各情境 `SDD_{SCENARIO}_ENHANCEMENT.md`，定義 SDD Spec-First 流程補強
- 涵蓋全部 10 大情境：greenfield / brownfield / refactoring / documentation / devops / integration / migration / performance / security / testing

#### 文檔目錄結構（SDD 8 層）
- `docs/01_requirements/` — PRD / FRD / Invariant Spec / Third-Party API Research
- `docs/02_architecture/` — SRD / C4 / ADR / As-Is / Trust Boundary Map
- `docs/02_architecture/adr/` — ADR-{NNN} 架構決策記錄
- `docs/02_architecture/api/` — OpenAPI 3.1 Contract / Consumer Contract
- `docs/03_testing/` — RTM / Test Plan / Test Strategy / Defect Classification
- `docs/03_testing/contracts/` — Invariant Test Contract / Contract Test Spec / Chaos Contract
- `docs/04_planning/` — Gap Analysis / Refactor Plan
- `docs/04_planning/performance/` — Performance Baseline Spec（PBS）
- `docs/05_development/` — Living Doc Strategy
- `docs/06_quality/` — Code Quality Baseline / Tech Debt Spec
- `docs/06_quality/security/` — SAD / STRIDE / Compliance Matrix / Asset Inventory
- `docs/07_design/` — UI/UX / Database Design
- `docs/08_deployment/` — CI/CD Pipeline Spec / Monitoring Alert Spec / Release Notes / Runbook / Cutover Plan
- `docs/08_deployment/iac/` — IaC Specifications

---

### 修改（v0.09 → v0.01 升級）

#### Agents（21 個全部更新）
- 21 個 Agents 版本更新至 v0.01（7 core + 14 specialized）
- 核心 Agents 新增 SDD 技能：
  - `sa-analyst`：逆向規格工程（As-Is SRD）、Gap Analysis、Business Invariants 提取（INV-XXX）
  - `sd-architect`：As-Is C4 Model、ADR Archaeology、Before/After 架構對比、Migration Contract Map
  - `qa-tester`：As-Is 測試規格基線、Invariant Test Contract、Consumer Contract 測試
  - `dev-developer`：Strangler Fig 模式、Branch by Abstraction、Contract-First 開發
  - `code-analyzer`：Tech Debt 規格化（TD-XXX）、Code Quality Baseline Spec
  - `technical-writer`：Living Documentation 策略、ADR 維護、API 文件從 Contract 生成

#### Workflows（23 個全部更新）
- 所有 23 個 Workflows 整合 SCG 閘門驗證點
- 新增 SDD Spec-First Gate Workflow（`workflow/sdd-spec-first-gate/`）
- 核心 8 個 Workflow + 13 個場景特定 Workflow + 1 個 ADR Workflow

#### 場景 SOP（10 個全部更新）
- 所有 10 個場景 SOP 反映 SDD Spec-First 流程
- 每個場景新增強制 SCG 閘門步驟說明
- Brownfield / Refactoring / Migration 場景新增逆向規格工程步驟

#### 工具與腳本
- `tools/init_project.sh` 新增 `--sdd` 模式（v3.3-SDD），自動建立 SDD 8 層 docs/ 目錄結構

#### 指南文件更新
- `guides/user/onboarding/QUICK_START_GUIDE.md` — 新增 SDD 三大支柱說明與 SCG 閘門引導
- `guides/user/onboarding/SCENARIO_DECISION_TREE.md` — 各情境新增對應 SCG 閘門說明
- `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md` — 目錄結構更新為 SDD 8 層，FILE_DIRECTORY_RULES.md 引用
- `agent/AGENT_COLLABORATION_PATTERNS.md` — 新增「SDD SCG 閘門協作模式」章節
- `agent/AGENT_PHASE2_UPDATE_GUIDE.md` — 更新為 v0.09 → v0.01 升級指南
- `scenarios/SCENARIO_TRANSITION_GUIDE.md` — 新增「場景切換前的 SCG 驗證」強制章節
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 新增各情境 SCG 對照說明與特殊情境說明

---

### 歸檔

- AISDLC v0.09 保留於 `AISDLC_v0.09/` 目錄（僅供參考，不修改）
- v0.09 版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`

---

## [v0.09] - 2026-04-14（歸檔）

> 此版本為 AISDLC 開發專注版（Development-Focused Edition），版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`。
>
> v0.09 定義了 10 大情境、21 個 Agents、23 個 Workflows 的基礎框架，v0.01 在此基礎上加入 SDD Spec-First Gate 機制完成框架轉型。

### 主要特性（v0.09 歸檔記錄）
- 10 大開發情境（含 migration）
- 21 個 Agents（7 core + 14 specialized）
- 23 個 Workflows
- 雙層 guides 架構（system + user）
- 中文優先 Agents（-zh.yaml）
- 開發專注版 docs/ 目錄結構（8 個目錄）
