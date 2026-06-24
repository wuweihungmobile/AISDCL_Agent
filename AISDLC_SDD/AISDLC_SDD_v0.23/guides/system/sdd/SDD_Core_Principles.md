# SDD 核心原則文件
# Specification-Driven Development — Core Principles

**版本**: v1.1
**建立日期**: 2026-04-12
**最後更新**: 2026-04-17
**文件類型**: 框架指引
**所屬分類**: guides/system/sdd/

---

## 🎯 SDD 轉型核心哲學

### 現狀 vs 目標對比

| 面向 | AISDLC-SDD v0.01 現狀 | SDD 目標狀態 |
|------|------------------|-------------|
| 文件定位 | 輔助說明（記錄決策） | 主要產出（驅動開發） |
| 規格時序 | 開發前後均可補齊 | 嚴格先於實作（Spec-First Gate） |
| 架構決策 | 隱性於 SRD 文字描述中 | ADR 顯性化，每決策一文件 |
| API 契約 | 建議產出，非強制 | 強制產出（Contract-First） |
| 品質閘門 | Human Checkpoint（🔴） | 🔴 Human + 🔷 Spec Compliance Gate |
| 圖表規範 | 選配（C4 Model 指引） | 強制：Context + Container 圖必產出 |
| 測試契約 | 測試計畫文件 | Test Contract Specification（先於開發） |

> SDD 三大支柱定義與場景對應，請參閱 **[CLAUDE.md Rule 3](../../../CLAUDE.md)**。

---

## 🔷 Spec-First Gate（SCG）機制

### 閘門流程對比

```
傳統 AISDLC Checkpoint：
  ...開發中... → 🔴 Human Checkpoint → ...繼續...

SDD 強化版 Checkpoint：
  ...規格撰寫中... → 🔷 Spec Compliance Gate → 🔴 Human Checkpoint → ...實作...
                         ↑
                    Agent 自動驗證
                    （spec_compliance_check）
```

### 七大閘門定義

| 閘門代號 | 時機 | 強制文件 | 負責 Agent |
|---------|------|---------|-----------|
| 🔷 SCG-0 | 需求凍結前 | PRD + FRD 完整性 | sa-analyst |
| 🔷 SCG-1 | 設計凍結前 | SRD + API Spec | sd-architect |
| 🔷 SCG-2 | 架構凍結前 | C4 圖 + ADR | sd-architect |
| 🔷 SCG-3 | 開發啟動前 | OpenAPI 3.1 凍結 | integration-specialist |
| 🔷 SCG-4 | PR Review | 實作與規格一致性 | dev-senior / qa-lead |
| 🔷 SCG-5 | 交付前 | RTM 100% 覆蓋 | qa-lead |
| 🔷 SCG-6 | 發布前 | 所有閘門通過 | technical-writer |

---

## 🧩 共通 Agent Skill 定義

### Skill: `generate_adr` — Architecture Decision Record 生成

**適用情境**：所有 10 大情境，凡有架構或技術決策時觸發

**觸發規則**：
- 技術棧選擇（語言、框架、資料庫）
- 架構模式選擇（Monolith / Microservices / Event-Driven）
- 整合策略（API / Event / File / DB Share）
- 安全機制選擇（Auth / Encryption / Token）
- 部署策略（Container / Serverless / VM）

**ADR 存放位置**：`docs/02_architecture/adr/ADR-{NNN}-{title}.md`

---

### Skill: `spec_compliance_check` — 規格符合性自我驗證

**驗證維度**：
- `completeness`：必填欄位、追溯鏈、ADR 建立
- `format`：命名規範、目錄位置、Markdown Lint
- `cross_reference`：上游引用、下游連結、ID 格式
- `sdd_specific`：規格先於實作、架構決策有 ADR、API 使用 OpenAPI

---

### Skill: `traceability_matrix` — 需求追溯矩陣生成

**RTM 格式**：
```
| EPIC | Feature | User Story | AC | AT | API | NFR | Status |
```

**觸發時機**：SCG-0（FRD 後）、SCG-1（SRD 後）、SCG-4（測試計畫後）、任何需求變更後

---

## 📁 SDD 新增文件類型規範

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

## 🔗 相關文件

- [CLAUDE.md — Rule 3（SDD 框架使用規則）](../../../CLAUDE.md)
- [ADR 範本](../../docs_template/sdd/adr/ADR-TEMPLATE.md)
- [API Contract 範本](../../docs_template/sdd/api/CONTRACT-TEMPLATE.yaml)
- [RTM 範本](../../docs_template/sdd/testing/RTM-TEMPLATE.md)
- [SDD 快速指引](SDD_GUIDE.md)
- [Spec-First Gate 執行流程](../../workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)
