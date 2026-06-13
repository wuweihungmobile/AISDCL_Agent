# SDD Migration 情境增強規格
# SDD Enhancement for Migration Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 04 規劃
**對應 CI/CD**: `cicd/SDD_MIGRATION_CICD.md`

---

## SDD 核心強化原則

Migration 情境的 SDD 強化核心：**Migration Contract Map（MCM）先行**

> 遷移不是「搬資料」，而是兩系統之間有明確契約的轉換過程，契約必須先於遷移實作。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| Migration Contract Map | MCM | `docs_template/sdd/architecture/MIGRATION-CONTRACT-MAP-TEMPLATE.md` | `docs/02_architecture/migration/` |
| Migration ADR | - | `docs_template/sdd/architecture/MIGRATION-ADR-TEMPLATE.md` | `docs/02_architecture/adr/` |
| Cutover Spec | - | `docs_template/sdd/deployment/CUTOVER-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Rollback Spec | - | `docs_template/sdd/deployment/ROLLBACK-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Contract Test Spec（Migration）| - | `docs_template/sdd/testing/CONTRACT-TEST-SPEC-MIGRATION-TEMPLATE.md` | `docs/03_testing/contracts/` |
| Data Integrity Test Spec | - | `docs_template/sdd/testing/DATA-INTEGRITY-TEST-SPEC-TEMPLATE.md` | `docs/03_testing/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `devops-engineer-zh.yaml` | `cutover_spec_gen`、`rollback_spec_gen` |
| `sd-architect-zh.yaml` | Migration Contract Map 生成 |
| `integration-specialist-zh.yaml` | `consumer_driven_contract` |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| 🔷 SCG-1 | 需求規格凍結前 | sa-analyst |
| 🔷 SCG-2 | 架構設計凍結前（MCM 完成） | sd-architect |
| 🔷 SCG-3 | API 契約凍結前 | integration-specialist |

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線 |
| L1 | Build + Unit Test |
| SAST | 靜態分析 |
| Container | Docker Build + Scan |
| L2 | Contract Test（自動生成） |
| L3 | Canary 驗證 |
| SDD 強化 | MCM Validate + Contract Test Auto-Gen |

---

## SDD 執行流程差異

```
v0.01 Migration：分析現狀 → 遷移計畫 → 實作 → 驗證
SDD Migration：  MCM 契約先行 → 🔷 SCG-2 → 遷移實作 → Contract Test 自動驗證
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [Migration SOP](SOP.md)
