# docs/ — 專案文檔輸出目錄

**定位**: Layer 3 — 專案產出層（Project Output Layer）
**說明**: 此目錄在框架本身中為**空目錄**（含 .gitkeep 佔位）。使用 AISDLC-SDD 框架執行專案時，所有產出文件寫入此目錄下的對應子目錄。

> ⚠️ **框架文件不放這裡**：框架本身的規劃、追蹤、報告文件請放在 `build/` 目錄。

---

## 子目錄用途

| 目錄 | 存放文件類型 | 對應模板來源 |
|------|-----------|------------|
| `01_requirements/` | PRD、FRD、Invariant Spec、第三方 API 研究 | `docs_template/sdd/requirements/`、`docs_template/core/prd/`、`docs_template/core/frd/` |
| `02_architecture/` | SRD、C4 圖、As-Is/To-Be SRD、Trust Boundary Map | `docs_template/sdd/architecture/`、`docs_template/core/srd/` |
| `02_architecture/adr/` | Architecture Decision Records (ADR-NNN-*.md) | `docs_template/sdd/adr/ADR-TEMPLATE.md` |
| `02_architecture/api/` | API Contract Spec、API Compat 聲明、Consumer Contract | `docs_template/sdd/api/` |
| `02_architecture/migration/` | Migration Contract Map (MCM) | `docs_template/sdd/architecture/MIGRATION-CONTRACT-MAP-TEMPLATE.md` |
| `03_testing/` | RTM、Test Strategy Spec、Test Plan、Defect Classification | `docs_template/sdd/testing/`、`docs_template/core/tests/` |
| `03_testing/contracts/` | Test Contract Spec (TCS)、Invariant Test Contract、Contract Test Spec | `docs_template/sdd/testing/` |
| `04_planning/` | Gap Analysis、Refactor Plan | `docs_template/sdd/planning/` |
| `04_planning/performance/` | Performance Baseline Spec (PBS) | `docs_template/sdd/testing/PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` |
| `05_development/` | Living Documentation Strategy | `docs_template/sdd/development/LIVING-DOC-STRATEGY-TEMPLATE.md` |
| `06_quality/` | Code Quality Baseline、Tech Debt Spec | `docs_template/sdd/quality/` |
| `06_quality/security/` | SAD、STRIDE Threat Model、Compliance Matrix、Asset Inventory、Incident Response | `docs_template/sdd/architecture/SAD-TEMPLATE.md`、`docs_template/sdd/testing/` |
| `07_design/` | UI/UX 設計文件、Database Schema Design | `docs_template/core/` |
| `08_deployment/` | Pipeline Spec、Monitoring Alert Spec、Security Monitoring Spec、Release Notes | `docs_template/sdd/deployment/` |
| `08_deployment/iac/` | IaC Specification (IaCS) | `docs_template/sdd/architecture/INFRA-REQUIREMENTS-SPEC-TEMPLATE.md` |

---

## 使用規則

1. **複製模板**，不修改原始模板：
   ```
   來源（不修改）: docs_template/sdd/architecture/AS-IS-SRD-TEMPLATE.md
   產出（填寫）:   docs/02_architecture/AS-IS-SRD-{SystemName}.md
   ```

2. **ADR 命名規範**：`ADR-{NNN}-{kebab-title}.md`，例如 `ADR-001-use-postgresql.md`

3. **此目錄不納入框架升版複製**（Layer 3 = 專案特有，不隨框架版本更新）

4. 完整目錄規則請參閱：[FILE_DIRECTORY_RULES.md](../FILE_DIRECTORY_RULES.md)
