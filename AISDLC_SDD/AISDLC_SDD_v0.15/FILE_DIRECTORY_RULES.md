# AISDLC-SDD v0.01 檔案目錄維護與分類規則
# File & Directory Maintenance Rules

**版本**: v0.05
**建立日期**: 2026-04-12
**最後更新**: 2026-04-17
**來源框架**: AISDLC v0.09

---

## 目錄結構總覽

```
AISDLC_SDD_v0.01/
│
├── 📄 AISDLC_SDD_INIT.md                 # 框架初始化配置（入口文件）
├── 📄 FILE_DIRECTORY_RULES.md            # 本文件 — 目錄結構規則
├── 📄 README.md                          # 框架概述與快速入門
├── 📄 AISDLC_SDD_UPGRADE_SOP.md         # 框架升版 SOP
├── 📄 AISDLC_SDD_UPGRADE_CHECKLIST.md   # 升版前完整檢查清單
│
├── 📁 agent/                         # Agent 配置
│   ├── 📁 core/                      # 7 核心 Agent（含 SDD 技能）
│   │   ├── 01.agent-template-zh.yaml
│   │   ├── 02.ba-business-analyst-zh.yaml
│   │   ├── 03.pm-po-agent-zh.yaml
│   │   ├── 04.sa-analyst-zh.yaml      # +sdd_brownfield, +sdd_refactoring
│   │   ├── 05.sd-architect-zh.yaml    # +sdd_brownfield, +sdd_refactoring
│   │   ├── 06.dev-developer-zh.yaml
│   │   └── 07.qa-tester-zh.yaml      # +sdd_phase03
│   ├── 📁 specialized/               # 14 專業化 Agent（含 SDD 增強）
│   │   ├── code-analyzer-zh.yaml     # +sdd_phase03
│   │   ├── compliance-officer-zh.yaml
│   │   ├── dev-senior-zh.yaml        # +sdd_refactoring
│   │   ├── devops-engineer-zh.yaml
│   │   ├── integration-specialist-zh.yaml
│   │   ├── performance-engineer-zh.yaml
│   │   ├── qa-automation-zh.yaml
│   │   ├── qa-lead-zh.yaml
│   │   ├── qa-mobile-tester-zh.yaml
│   │   ├── qa-web-tester-zh.yaml
│   │   ├── sd-mobile-architect-zh.yaml
│   │   ├── sd-web-architect-zh.yaml
│   │   ├── security-engineer-zh.yaml
│   │   └── technical-writer-zh.yaml  # +sdd_documentation
│   ├── AGENT_COLLABORATION_PATTERNS.md
│   ├── AGENT_PHASE2_UPDATE_GUIDE.md
│   └── README.md
│
├── 📁 scenarios/                     # 10 大情境（含 SDD 增強）+ 跨場景指南
│   ├── 📄 README.md                 # 場景選擇入口（含 SCG 閘門說明）
│   ├── 📄 SCENARIO_AGENT_MAPPING.md # 場景 × Agent 對應表（SDD 10 場景版）
│   ├── 📄 ERROR_RECOVERY_GUIDE.md   # 執行錯誤恢復指南
│   ├── 📄 FRONTEND_SPECIFIC_GUIDE.md # 前端特定指南
│   ├── 📄 SCALING_GUIDE.md          # 框架擴展指南
│   ├── 📄 SCENARIO_TRANSITION_GUIDE.md # 場景切換指南（含 SDD 轉換規則）
│   ├── 📁 greenfield/               # Greenfield（全新開發）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   ├── Parallel_Execution_Guide.md
│   │   ├── SDD_GREENFIELD_ENHANCEMENT.md   # ★ SDD 增強
│   │   └── 📁 checklists/
│   ├── 📁 brownfield/               # Brownfield（既有系統擴充）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_BROWNFIELD_ENHANCEMENT.md   # ★ SDD 增強
│   ├── 📁 refactoring/              # Refactoring（系統重構）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_REFACTORING_ENHANCEMENT.md  # ★ SDD 增強
│   ├── 📁 documentation/            # Documentation（文件維護）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_DOCUMENTATION_ENHANCEMENT.md # ★ SDD 增強
│   ├── 📁 devops/                   # DevOps / CI/CD
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_DEVOPS_ENHANCEMENT.md       # ★ SDD 增強（IaC-as-Spec）
│   ├── 📁 migration/                # Migration（系統遷移）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_MIGRATION_ENHANCEMENT.md    # ★ SDD 增強（MCM 先行）
│   ├── 📁 integration/              # Integration（第三方整合）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_INTEGRATION_ENHANCEMENT.md  # ★ SDD 增強（CDC + OpenAPI First）
│   ├── 📁 testing/                  # Testing / QA
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_TESTING_ENHANCEMENT.md      # ★ SDD 增強（Test Pyramid Spec）
│   ├── 📁 performance/              # Performance（效能調校）
│   │   ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│   │   └── SDD_PERFORMANCE_ENHANCEMENT.md  # ★ SDD 增強（SLO/PBS 先行）
│   └── 📁 security/                 # Security（安全合規）
│       ├── SOP.md / SOP_DeepDive.md / SOP_QuickRef.md
│       └── SDD_SECURITY_ENHANCEMENT.md     # ★ SDD 增強（STRIDE + SAD 前置）
│
├── 📁 workflow/                      # 工作流定義
│   ├── 📁 sdd-spec-first-gate/      # ★ SDD 專屬工作流
│   │   └── SDD_SPEC_FIRST_GATE.md
│   ├── 📁 sdd-fsm-engine/           # ★ SDD 閉環防護：形式化狀態機（Phase A）
│   │   └── SDD_FSM_ENGINE.md
│   ├── 📁 sdd-escalation/           # ★ SDD 閉環防護：退場機制（Phase A）
│   │   └── SDD_ESCALATION_PROTOCOL.md
│   ├── 📁 sdd-context-governor/     # ★ SDD 閉環防護：上下文管理（Phase B）
│   │   └── SDD_CONTEXT_GOVERNOR.md
│   ├── 📁 core/                     # 8 核心工作流（繼承 AISDLC）
│   │   ├── api-specification.md
│   │   ├── change-management.md
│   │   ├── consistency-check.md
│   │   ├── interaction-analysis.md
│   │   ├── requirements-extraction.md
│   │   ├── sprint-execution.md
│   │   ├── user-story-design.md
│   │   └── validation-documentation.md
│   ├── 📁 scenario-specific/        # 13 場景工作流（繼承 AISDLC）
│   │   ├── brownfield-analysis-flow.md
│   │   ├── code-analysis-flow.md
│   │   ├── devops-setup-flow.md
│   │   ├── documentation-flow.md
│   │   ├── documentation-reconstruction-flow.md
│   │   ├── greenfield-complete-flow.md
│   │   ├── integration-analysis-flow.md
│   │   ├── migration-planning-flow.md
│   │   ├── performance-optimization-flow.md
│   │   ├── refactoring-planning-flow.md
│   │   ├── security-assessment-flow.md
│   │   ├── tech-stack-selection-flow.md
│   │   └── testing-strategy-flow.md
│   ├── 📁 adr-generation/
│   │   └── ADR_GENERATION.md
│   └── README.md
│
├── 📁 docs_template/                # 文檔模板
│   ├── 📁 sdd/                      # ★ SDD 專屬模板（59 個：56 md + 3 yaml）
│   │   ├── 📁 requirements/
│   │   │   ├── INVARIANT-SPEC-TEMPLATE.md
│   │   │   └── THIRD-PARTY-API-RESEARCH-TEMPLATE.md
│   │   ├── 📁 architecture/
│   │   │   ├── ADR-INTEGRATION-ACL-TEMPLATE.md
│   │   │   ├── AFTER-ARCH-TEMPLATE.md
│   │   │   ├── AS-IS-SRD-TEMPLATE.md
│   │   │   ├── BEFORE-ARCH-TEMPLATE.md
│   │   │   ├── INFRA-REQUIREMENTS-SPEC-TEMPLATE.md
│   │   │   ├── MIGRATION-ADR-TEMPLATE.md
│   │   │   ├── MIGRATION-CONTRACT-MAP-TEMPLATE.md
│   │   │   ├── SAD-TEMPLATE.md
│   │   │   ├── SDD-COMPLIANCE-AUDIT-TEMPLATE.md
│   │   │   ├── TO-BE-SRD-TEMPLATE.md
│   │   │   └── TRUST-BOUNDARY-MAP-TEMPLATE.md
│   │   ├── 📁 adr/
│   │   │   ├── ADR-INDEX.md
│   │   │   ├── ADR-TEMPLATE.md
│   │   │   ├── AUTOMATION-FRAMEWORK-ADR-TEMPLATE.md
│   │   │   └── PERFORMANCE-OPTIMIZATION-ADR-TEMPLATE.md
│   │   ├── 📁 api/
│   │   │   ├── API-COMPAT-TEMPLATE.md
│   │   │   ├── CONSUMER-CONTRACT-TEMPLATE.yaml
│   │   │   ├── CONTRACT-TEMPLATE.yaml
│   │   │   └── PROVIDER-API-SPEC-TEMPLATE.yaml
│   │   ├── 📁 testing/
│   │   │   ├── ASSET-INVENTORY-TEMPLATE.md
│   │   │   ├── BASELINE-PERFORMANCE-REPORT-TEMPLATE.md
│   │   │   ├── CHAOS-CONTRACT-TEMPLATE.md
│   │   │   ├── COMPLIANCE-MATRIX-TEMPLATE.md
│   │   │   ├── CONTRACT-TEST-SPEC-INTEGRATION-TEMPLATE.md
│   │   │   ├── CONTRACT-TEST-SPEC-MIGRATION-TEMPLATE.md
│   │   │   ├── DATA-INTEGRITY-TEST-SPEC-TEMPLATE.md
│   │   │   ├── DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md
│   │   │   ├── ENV-CONTRACT-SPEC-TEMPLATE.md
│   │   │   ├── INVARIANT-TEST-CONTRACT-TEMPLATE.md
│   │   │   ├── LIVING-TEST-REPORT-TEMPLATE.md
│   │   │   ├── PERFORMANCE-BASELINE-SPEC-TEMPLATE.md
│   │   │   ├── RTM-EXISTING-SYSTEM-TEMPLATE.md
│   │   │   ├── RTM-TEMPLATE.md
│   │   │   ├── SECURITY-TEST-SPEC-TEMPLATE.md
│   │   │   ├── STRIDE-THREAT-MODEL-TEMPLATE.md
│   │   │   ├── TEST-CONTRACT-SPEC-TEMPLATE.md
│   │   │   └── TEST-STRATEGY-SPEC-TEMPLATE.md
│   │   ├── 📁 planning/
│   │   │   ├── GAP-ANALYSIS-TEMPLATE.md
│   │   │   └── REFACTOR-PLAN-TEMPLATE.md
│   │   ├── 📁 quality/
│   │   │   ├── CODE-QUALITY-BASELINE-TEMPLATE.md
│   │   │   └── TECH-DEBT-SPEC-TEMPLATE.md
│   │   ├── 📁 development/
│   │   │   └── LIVING-DOC-STRATEGY-TEMPLATE.md
│   │   └── 📁 deployment/
│   │       ├── CANARY-SPEC-TEMPLATE.md
│   │       ├── CUTOVER-SPEC-TEMPLATE.md
│   │       ├── INCIDENT-RESPONSE-SPEC-TEMPLATE.md
│   │       ├── MONITORING-ALERT-SPEC-TEMPLATE.md
│   │       ├── PIPELINE-SPEC-TEMPLATE.md
│   │       ├── ROLLBACK-SPEC-TEMPLATE.md
│   │       └── SECURITY-MONITORING-SPEC-TEMPLATE.md
│   ├── 📁 core/                     # 核心模板（繼承 AISDLC）
│   │   ├── 📁 api/
│   │   ├── 📁 frd/
│   │   ├── 📁 prd/
│   │   ├── 📁 srd/
│   │   └── 📁 tests/
│   ├── 📁 scenario_specific/        # 場景模板（繼承 AISDLC）
│   │   ├── 📁 analysis/
│   │   ├── 📁 brownfield/
│   │   ├── 📁 devops/
│   │   ├── 📁 documentation/
│   │   ├── 📁 integration/
│   │   ├── 📁 migration/
│   │   ├── 📁 performance/
│   │   └── 📁 testing/
│   ├── 📁 support/                  # 支援模板（繼承 AISDLC）
│   └── README.md
│
├── 📁 cicd/                         # ★ SDD CI/CD 規格（9 個）
│   ├── SDD_CICD_BASE_LAYER.md       # 基礎層（DocLint + SpecTrace + OpenAPI + RTM）
│   ├── SDD_GREENFIELD_CICD.md
│   ├── SDD_BROWNFIELD_CICD.md
│   ├── SDD_REFACTORING_CICD.md
│   ├── SDD_MIGRATION_CICD.md        # MCM Validate + Contract Test Auto-Gen
│   ├── SDD_INTEGRATION_CICD.md      # Consumer Contract Validate + Chaos Contract
│   ├── SDD_TESTING_CICD.md          # TestSpec Validate + Quality Gate + RTM Coverage
│   ├── SDD_PERFORMANCE_CICD.md      # PBS Validate + SLO Gate
│   └── SDD_SECURITY_CICD.md         # STRIDE Validate + Compliance Matrix Auto-Check
│
├── 📁 guides/                       # 參考指南（繼承 AISDLC）
│   ├── 📁 system/                   # AI Agent 技術規格
│   │   ├── 📁 agent/
│   │   ├── 📁 api/
│   │   ├── 📁 architecture/
│   │   ├── 📁 naming/
│   │   ├── 📁 planning/
│   │   ├── 📁 quality/
│   │   ├── 📁 sdd/                  # ★ SDD 核心指南
│   │   │   ├── SDD_Core_Principles.md
│   │   │   └── SDD_GUIDE.md
│   │   └── 📁 testing/
│   ├── 📁 user/                     # 使用者指南
│   │   ├── 📁 onboarding/
│   │   ├── 📁 process/
│   │   ├── 📁 sample/
│   │   ├── 📁 standards/
│   │   └── 📁 technical/
│   └── README.md
│
├── 📁 .claude/skills/               # ★ Claude Code Skills（39 個）
│   ├── README.md
│   ├── SKILL_DEVELOPMENT_PLAN.md
│   ├── SKILL_STANDARD_TEMPLATE.md
│   └── {skill-name}/SKILL.md        # 39 個 skill 目錄（各含 SKILL.md）
│
├── 📁 prompts/                      # 使用者指令集
│   ├── 📄 README.md
│   ├── 📁 quick-start/
│   │   ├── 5-minute-start.md
│   │   ├── common-commands.md
│   │   ├── scenario-quick-reference.md
│   │   └── troubleshooting-quick-guide.md
│   ├── 📁 complete-flow/
│   │   ├── end-to-end-greenfield-example.md
│   │   └── multi-scenario-combination-example.md
│   └── 📁 scenario-prompts/         # 10 個場景專用指令集
│       ├── README.md
│       ├── greenfield-prompts.md / brownfield-prompts.md / refactoring-prompts.md
│       ├── documentation-prompts.md / testing-prompts.md / devops-prompts.md
│       ├── integration-prompts.md / migration-prompts.md
│       ├── performance-prompts.md / security-prompts.md
│
├── 📁 releases/                     # 框架發布包管理
│   ├── 📄 README.md
│   ├── 📁 backups/                  # 升版前備份
│   └── 📁 v0.01/                    # v0.01 發布包
│       ├── RELEASE_NOTES_v0.01.md
│       ├── AISDLC-SDD_v0.01_release_2026-04-16.tar.gz
│       └── AISDLC-SDD_v0.01_release_2026-04-16.sha256
│
├── 📁 tools/                        # 工具腳本
│   ├── init_project.sh
│   ├── init_project.ps1
│   ├── verify_traceability.sh
│   ├── AISDLC_CLAUDE_RULES.md
│   ├── PROJECT_CLAUDE_Template.md
│   └── README.md
│
├── 📁 build/                        # 建置產出（Layer 3 — 不複製）
│   ├── 📁 reports/
│   │   ├── 📁 analysis/
│   │   ├── 📁 phase/
│   │   ├── 📁 verification/
│   │   └── 📁 kpi/
│   ├── 📁 logs/
│   └── 📁 planning/
│       ├── 📁 active/               # 進行中的框架追蹤文件（.gitkeep）
│       └── 📁 archive/              # 已完成規劃文件歸檔
│           ├── AISDLC_TO_SDD_Planning_Phase_01.md ~ Phase_06.md
│           ├── SDD_improving_Phase_07.md ~ Phase_09.md
│           ├── Skill_for_SDD_Planning_Phase_01.md
│           ├── SDD_ADOPTION_TRACKER.md
│           └── SDD_VERSION_HISTORY.md
│
└── 📁 docs/                         # ★ 專案文檔輸出目錄（Layer 3 — 不複製）
    ├── 📄 README.md
    ├── 📁 01_requirements/           # PRD, FRD, Invariant Specs（.gitkeep）
    ├── 📁 02_architecture/           # SRD, C4, ADR, Trust Boundary Map
    │   ├── 📁 adr/                   # Architecture Decision Records（.gitkeep）
    │   ├── 📁 api/                   # API Contract Spec, Consumer Contract（.gitkeep）
    │   └── 📁 migration/             # Migration Contract Maps（.gitkeep）
    ├── 📁 03_testing/                # RTM, Test Plans, Test Specs
    │   └── 📁 contracts/             # Test Contract Spec, Invariant Test Contract（.gitkeep）
    ├── 📁 04_planning/               # Gap Analysis, Refactor Plans
    │   └── 📁 performance/           # Performance Baseline Specs（.gitkeep）
    ├── 📁 05_development/            # Living Doc Strategy（.gitkeep）
    ├── 📁 06_quality/                # Code Quality Baseline, Tech Debt Spec
    │   └── 📁 security/              # SAD, STRIDE, Compliance Matrix, Asset Inventory（.gitkeep）
    ├── 📁 07_design/                 # UI/UX, Database Design（.gitkeep）
    └── 📁 08_deployment/             # Pipeline Spec, Monitoring, Release Notes
        └── 📁 iac/                   # IaC Specifications（.gitkeep）
```

---

## 檔案分層規則

### Layer 1: 框架共享檔（根目錄）

| 檔案 | 說明 | 修改頻率 |
|------|------|---------|
| AISDLC_SDD_INIT.md | 框架初始化配置 | 升版時 |
| FILE_DIRECTORY_RULES.md | 目錄結構規則 | 結構變更時 |
| README.md | 框架概述 | 升版時 |
| AISDLC_SDD_UPGRADE_SOP.md | 升版 SOP | 升版時 |
| AISDLC_SDD_UPGRADE_CHECKLIST.md | 升版檢查清單 | 升版時 |

> **注意**：`SDD_Core_Principles.md` 位於 `guides/system/sdd/`，`SDD_VERSION_HISTORY.md` 位於 `build/planning/archive/`。

#### GitHub Actions Workflows（`.github/workflows/`）

GitHub Actions 僅讀 **repo 根目錄** `.github/workflows/`；巢狀 `AISDLC_SDD_v0.01/.github/workflows/` 不會被 GitHub 註冊。雙位置採用以下約定：

| 位置 | 性質 | 範例 |
|------|------|------|
| Repo root `.github/workflows/` | **Active**（framework 自我 dogfood） | `fsm-chaos-nightly.yml`（Rule 9.9.4）、`drift-daily.yml`（Rule 9.17.4） |
| Nested `AISDLC_SDD_v0.01/.github/workflows/` | **Reference-only**（下游採用 SDD 時複製到自家 root） | `hub-push.yml`（為下游 Hub Registry repo 範本） |

**規則**：
- 凡 CLAUDE.md Rule 9.X 標註「framework dogfood」者必須位於 root（位置錯置等同停用該規則）
- 純為下游採用者 sample 的 workflow 留在 nested，並於檔頭明確聲明「reference-only / not for framework repo」
- 變更某 workflow 的 active vs reference 性質時，須同步：(a) yaml 檔頭說明 (b) CLAUDE.md 對應 Rule 措辭 (c) 本表

### Layer 2: 版本複製檔（框架核心）

升版時需要完整複製的目錄：

| 目錄 | 說明 | 檔案數 |
|------|------|--------|
| agent/ | Agent 配置 | 7 core + 14 specialized |
| scenarios/ | 場景 SOP + SDD 增強 | 10 場景 × (SOP + DeepDive + QuickRef + SDD Enhancement) |
| workflow/ | 工作流定義 | 1 SDD Gate + 8 core + 13 scenario + 1 ADR |
| docs_template/ | 文檔模板 | 59 SDD（56 md + 3 yaml）+ 50+ AISDLC |
| cicd/ | CI/CD 規格 | 9 個（Base Layer + 8 場景專屬） |
| guides/ | 參考指南 | 57+ |
| .claude/skills/ | Claude Code Skills | 39（33 繼承強化 + 6 SDD 新增） |
| tools/ | 工具腳本 | 6 個 |
| prompts/ | 使用者指令集 | 15 個 |

### Layer 3: 專案產出檔（不複製）

| 目錄 | 說明 |
|------|------|
| docs/ | 專案文檔輸出（使用框架時產生，框架內為空目錄含 .gitkeep） |
| build/ | 框架建置報告、日誌、採用追蹤（active/）、歸檔（archive/） |
| releases/ | 框架發布包（tar.gz + sha256 + RELEASE_NOTES） |

> **定位說明**：`docs/` 是**專案層**輸出，每個使用此框架的專案在此填入自己的 PRD/FRD/SRD/ADR 等文件。`build/` 是**框架層**的建置追蹤，不屬於任何一個具體專案。

---

## 寫檔規則

### SDD 模板寫入位置

| 模板類型 | 框架位置 | 專案產出位置 |
|---------|---------|------------|
| Invariant Spec | docs_template/sdd/requirements/ | docs/01_requirements/ |
| Third-Party API Research | docs_template/sdd/requirements/ | docs/01_requirements/ |
| As-Is/To-Be SRD | docs_template/sdd/architecture/ | docs/02_architecture/ |
| Before/After Arch | docs_template/sdd/architecture/ | docs/02_architecture/ |
| ADR-Integration-ACL | docs_template/sdd/architecture/ | docs/02_architecture/adr/ |
| Migration Contract Map | docs_template/sdd/architecture/ | docs/02_architecture/migration/ |
| Migration ADR | docs_template/sdd/architecture/ | docs/02_architecture/adr/ |
| Trust Boundary Map | docs_template/sdd/architecture/ | docs/02_architecture/ |
| SAD | docs_template/sdd/architecture/ | docs/06_quality/security/ |
| Infra Requirements Spec | docs_template/sdd/architecture/ | docs/08_deployment/iac/ |
| SDD Compliance Audit | docs_template/sdd/architecture/ | docs/02_architecture/ |
| ADR | docs_template/sdd/adr/ | docs/02_architecture/adr/ |
| API Compat | docs_template/sdd/api/ | docs/02_architecture/api/ |
| Consumer/Provider Contract | docs_template/sdd/api/ | docs/02_architecture/api/ |
| Contract（通用） | docs_template/sdd/api/ | docs/02_architecture/api/ |
| RTM | docs_template/sdd/testing/ | docs/03_testing/ |
| RTM-Existing-System | docs_template/sdd/testing/ | docs/03_testing/ |
| Invariant Test Contract | docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Test Strategy Spec | docs_template/sdd/testing/ | docs/03_testing/ |
| Test Contract Spec | docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Contract Test Spec（Integration）| docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Contract Test Spec（Migration） | docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Chaos Contract | docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Env Contract Spec | docs_template/sdd/testing/ | docs/03_testing/contracts/ |
| Data Integrity Test Spec | docs_template/sdd/testing/ | docs/03_testing/ |
| Defect Classification Spec | docs_template/sdd/testing/ | docs/03_testing/ |
| Living Test Report | docs_template/sdd/testing/ | docs/03_testing/ |
| Security Test Spec | docs_template/sdd/testing/ | docs/03_testing/ |
| Performance Baseline Spec（PBS） | docs_template/sdd/testing/ | docs/04_planning/performance/ |
| Baseline Performance Report | docs_template/sdd/testing/ | docs/04_planning/performance/ |
| STRIDE Threat Model | docs_template/sdd/testing/ | docs/06_quality/security/ |
| Compliance Matrix | docs_template/sdd/testing/ | docs/06_quality/security/ |
| Asset Inventory | docs_template/sdd/testing/ | docs/06_quality/security/ |
| Gap Analysis | docs_template/sdd/planning/ | docs/04_planning/ |
| Refactor Plan | docs_template/sdd/planning/ | docs/04_planning/ |
| Code Quality Baseline | docs_template/sdd/quality/ | docs/06_quality/ |
| Tech Debt Spec | docs_template/sdd/quality/ | docs/06_quality/ |
| Living Doc Strategy | docs_template/sdd/development/ | docs/05_development/ |
| Pipeline Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |
| Monitoring Alert Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |
| Security Monitoring Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |
| Incident Response Spec | docs_template/sdd/deployment/ | docs/06_quality/security/ |
| Cutover Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |
| Rollback Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |
| Canary Spec | docs_template/sdd/deployment/ | docs/08_deployment/ |

### 報告寫入位置

| 報告類型 | 寫入位置 |
|---------|---------|
| 分析報告 | build/reports/analysis/ |
| 階段報告 | build/reports/phase/ |
| 驗證報告 | build/reports/verification/ |
| KPI 報告 | build/reports/kpi/ |
| 規劃文件 | build/planning/active/ |
| 歸檔文件 | build/planning/archive/ |
| 版本日誌 | build/logs/ |

---

## SDD 新增內容標記

以 ★ 標記的項目為 AISDLC-SDD 新增，非繼承自 AISDLC v0.09：

- ★ `guides/system/sdd/SDD_Core_Principles.md` — SDD 核心原則
- ★ `guides/system/sdd/SDD_GUIDE.md` — SDD 核心指引
- ★ `cicd/` — 9 個 SDD CI/CD 規格
- ★ `docs_template/sdd/` — 59 個 SDD 專屬模板（56 md + 3 yaml）
- ★ `workflow/sdd-spec-first-gate/` — Spec-First Gate 工作流
- ★ `scenarios/*/SDD_*_ENHANCEMENT.md` — 10 個場景 SDD 增強
- ★ Agent SDD 技能附加（21 個 Agent 全數完成 SDD 升級）
- ★ `.claude/skills/` 中 6 個 SDD 新增 Skills（sdd-gate、sdd-review、spec-compliance-check、rtm-generate、brownfield-analysis、adr-generate）
- ★ `docs/02_architecture/migration/` — Migration Contract Map 存放目錄
- ★ `docs/04_planning/performance/` — Performance Baseline Spec 存放目錄
- ★ `docs/06_quality/security/` — 安全相關文件存放目錄
- ★ `docs/08_deployment/iac/` — IaC 規格存放目錄
- ★ `knowledge/hub/` — Cross-Project Learning Hub 客戶端資料（trust-ladder.md、CONFLICTS/、REJECTED-LOG.yaml；ACT-030 / Phase F M2）
- ★ `knowledge/hub-registry.yaml` — Hub endpoint allow-list（deny_unlisted 硬編碼）
- ★ `tools/fsm_runtime/anonymizer_rules.yaml` — L0/L1/L2 PII patterns + allow_list（治理規格 §肆 對應）
- ★ `tools/fsm_runtime/modality/` — 多模態 LLM Backend + 4 adapter（UI/API/DB/C4；ACT-031 / Phase F M3-M4）
- ★ `docs/06_quality/HUB-GOVERNANCE-SPEC.md` — Hub 商業機密治理規格（ACT-030 D-30.1）
- ★ `docs/99_media/{ui,flow,erd,arch}/` — 多模態 artifact 統一存放（Git LFS；ACT-031 D-31.8）
- ★ `build/reports/hub/` — Hub 執行產出（QUARANTINE-*.yaml / PUSH-AUDIT.yaml / pull-cache/ / push-outbox/）
- ★ `cicd/SDD_HUB_SYNC.md` — Hub Sync Pipeline 規格（ACT-030 D-30.13）
- ★ `docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md` — 多模態錨點 schema（ACT-031 D-31.7）

---

**變更記錄**:

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-04-12 | v0.01 | 初始建立，基於 AISDLC v0.09 + SDD Phase 01-03 轉換 |
| 2026-04-14 | v0.02 | Phase 04-06 完成：新增 CI/CD 規格（5個）、模板（30+）、docs 子目錄（migration/performance/security/iac）、SDD_GUIDE.md |
| 2026-04-14 | v0.03 | 目錄定位修正：SDD_ADOPTION_TRACKER 移至 build/planning/active/；docs/ 加入 README.md + .gitkeep；Layer 3 定位說明補充 |
| 2026-04-15 | v0.04 | Phase 07 補充：新增 scenarios/ 跨場景指南、prompts/、releases/、版本管理文件、agent README.md |
| 2026-04-25 | v0.05 | Phase F M2-M4 補充：新增 knowledge/hub/、knowledge/hub-registry.yaml、tools/fsm_runtime/{anonymizer_rules.yaml,modality/}、docs/99_media/、build/reports/hub/、HUB-GOVERNANCE-SPEC.md、SDD_HUB_SYNC.md、SPEC-ANCHOR-TEMPLATE.md |
| 2026-04-17 | v0.05 | 對齊實際專案內容：SDD_Core_Principles 路徑修正至 guides/system/sdd/；SDD_VERSION_HISTORY 移至 build/planning/archive/；docs_template/sdd/ 補全 8 個缺失模板；guides/system/sdd/ 與 guides/user/sample/ 補入目錄樹；.claude/skills/ 數量更正為 39；build/planning/archive/ 補入 Phase 07-09 改善文件；寫檔規則補全所有新增模板對應 |
