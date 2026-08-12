# SDD 核心指引 — Spec-First Design-Driven Development

**版本**: v1.0
**建立日期**: 2026-04-14
**適用範圍**: AISDLC-SDD v0.01 框架所有使用者
**維護者**: technical-writer Agent + 首席架構師

---

## 一、SDD 是什麼

SDD（Spec-First Design-Driven Development）是 AISDLC 框架的品質強化層，核心理念是：

> **「規格是程式碼的合約，設計是程式碼的藍圖。」**
> 先定義清楚，再開始實作。

### SDD 三大支柱

| 支柱 | 原則 | 強制性 |
|------|------|--------|
| **Spec-First Gate** | 規格文件必須在實作前完成並通過 SCG 閘門 | 🔴 強制 |
| **Design-as-Doc** | 每個技術決策必須有 ADR；架構必須有 C4 圖 | 🔴 強制 |
| **Contract-Driven** | OpenAPI 規格凍結後才能開始後端實作 | 🔴 強制 |

---

## 二、SCG 閘門速查

> **版本說明**：SCG 閘門採用 SCG-0 ~ SCG-6 標準體系（與 `AISDLC_SDD_INIT.md`、`CLAUDE.md` 一致）。

> 🔴 **R85／DEF-200-081② 訂正：本表的英文閘門名原本與 SCG SSOT 互斥，四支不一致。**
> **被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）**：
> `SCG-2 | Architecture Review Gate`／`SCG-3 | Contract Freeze Gate`／
> `SCG-4 | Implementation Compliance Gate`／`SCG-6 | Release Readiness Gate`。
> （SCG-0／1／5 本來就一致，未動。）
>
> **為何以 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` 為準**：那份閘門表是
> `scripts/agent_scg_anchor_lint.py` **機械消費**的 SCG SSOT（該檔 `SCG_SSOT` 常數逐字指向它，
> 判準 2 每次執行都拿它自證主題歸屬）；本檔在同一支 lint 裡的角色是 **RG-\* 補充閘門**的 SSOT
> （`RG_SSOT`）。兩份各有其權威射程，而 SCG-N 的英文名不在本檔的射程內。
> 🔴 本表**不再是第二個家**：名稱一致性自 R85 起由該 lint 的**判準 5** 機械守住
> （任一支名稱與 SSOT 不符即紅），不靠人記得同步。

| Gate | 名稱 | 觸發時機 | 主責 Agent | 強制文件 |
|------|------|---------|-----------|---------|
| SCG-0 | Requirement Spec Gate | 需求凍結前 | sa-analyst | PRD + FRD 完整性 |
| SCG-1 | Design Spec Gate | 設計凍結前 | sd-architect | SRD + API Spec |
| SCG-2 | Architecture Spec Gate | 架構凍結前 | sd-architect | C4 圖 + ADR |
| SCG-3 | API Contract Gate（Contract Freeze） | 開發啟動前 | sd-architect | OpenAPI 3.1 凍結 |
| SCG-4 | PR Review Gate | PR Review | dev-senior | 實作與規格一致性 |
| SCG-5 | RTM Completeness Gate | 交付前 | qa-lead | RTM 100% 覆蓋 |
| SCG-6 | Release Gate | 發布前 | technical-writer | 所有閘門通過 |

> **場景專屬補充閘門**（不取代標準 SCG）：
>
> | 代碼 | 補充閘門 | 適用場景 | 觸發時機 | 強制文件 |
> |------|---------|---------|---------|---------|
> | RG-TEST | Test Strategy Gate | Testing 場景 | SCG-3 後，測試開始前 | Test Strategy Spec |
> | RG-SEC | Security Spec Gate | Security 場景 | SCG-2 後，安全設計凍結前 | SAD + STRIDE |
> | RG-PERF | Performance Baseline Gate | Performance 場景 | SCG-3 後，效能測試前 | PBS |
> | RG-DOC | Documentation Audit Gate | Documentation 場景 | 文件交付前 | Living Doc Strategy |
> | RG-PIPE | Pipeline Spec Gate | DevOps 場景 | CI/CD 設計前 | Pipeline Spec Doc |
>
> 註：`RG-*`（Role/Scenario sub-Gate）為角色／場景補充閘門代碼，供 agent 配置引用；
> 不取代主流程 SCG-0~6，亦不納入 FSM retry 上限治理。

---

## 三、情境對應快速索引

| 情境 | SDD 核心輸出 | 必讀 SOP |
|------|------------|---------|
| Greenfield | ADR + RTM + OpenAPI | `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md` |
| Brownfield | As-Is SRD + Gap Analysis | `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md` |
| Refactoring | Invariant Spec + Before/After Arch | `scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md` |
| Documentation | Living Doc Strategy + ADR Index | `scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md` |
| Migration | MCM + Cutover/Rollback Spec | `cicd/SDD_MIGRATION_CICD.md` |
| Performance | PBS + SLO Gate | `cicd/SDD_PERFORMANCE_CICD.md` |
| Integration | Consumer Contract + OpenAPI First | `cicd/SDD_INTEGRATION_CICD.md` |
| DevOps | IaC-as-Spec + Pipeline Spec | (DevOps CI/CD workflow) |
| Testing | Test Pyramid Spec + Quality Gate | `cicd/SDD_TESTING_CICD.md` |
| Security | STRIDE + SAD + Compliance Matrix | `cicd/SDD_SECURITY_CICD.md` |

---

## 四、SDD 新文件類型一覽

| 縮寫 | 全名 | 存放位置 | 觸發 Skill |
|------|------|---------|-----------|
| ADR | Architecture Decision Record | `docs/02_architecture/adr/` | `generate_adr` |
| Contract | API Contract Spec | `docs/02_architecture/api/` | `contract_document_gen` |
| PBS | Performance Baseline Spec | `docs/04_planning/performance/` | `baseline_benchmark_spec` |
| SAD | Security Architecture Document | `docs/06_quality/security/` | `security_arch_doc` |
| TCS | Test Contract Specification | `docs/03_testing/contracts/` | `test_contract_gen` |
| IaCS | IaC Specification | `docs/08_deployment/iac/` | `iac_specification` |
| MCM | Migration Contract Map | `docs/02_architecture/migration/` | `migration_contract_map` |
| GAP | Gap Analysis Report | `docs/04_planning/` | `gap_analysis` |
| BIS | Business Invariant Spec | `docs/01_requirements/` | `invariant_spec` |
| STM | STRIDE Threat Model | `docs/06_quality/security/` | `stride_threat_model` |
| CM | Compliance Matrix | `docs/06_quality/security/` | `compliance_matrix_format` |
| RTM | Requirements Traceability Matrix | `docs/03_testing/` | `traceability_matrix` |

---

## 五、共通 SDD Skills（所有 Agent 適用）

每個 Agent 均具備以下共通 Skills：

| Skill | 觸發時機 |
|-------|---------|
| `generate_adr` | 任何技術或架構決策時 |
| `spec_compliance_check` | 任何文件產出前 |
| `traceability_matrix` | FRD/SRD 完成後、需求變更後 |

---

## 六、違規防範

| 禁止行為 | 正確做法 |
|---------|---------|
| 跳過 SCG 閘門直接開發 | 規格通過 SCG 後才開發 |
| 先寫程式再補文件 | 規格先行，文件優先 |
| ADR 未記錄直接實作 | 每個技術決策觸發 `generate_adr` |
| 效能測試前未定義 SLO | PBS 必須先於 Benchmark |
| 安全測試前未做 STRIDE | SAD + STRIDE 是安全實作前置條件 |

---

## 七、相關文件

- 框架入口：`AISDLC_SDD_INIT.md`
- 目錄規則：`FILE_DIRECTORY_RULES.md`
- SDD 原則：`SDD_Core_Principles.md`
- Spec-First Gate：`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`
- Phase 轉型藍圖：`docs/04_planning/AISDLC_TO_SDD_Planning_Phase_0*.md`

---

**此文件由 Phase 06 最終驗證建立，代表 SDD 轉型完成。**
**最後更新**: 2026-04-14
