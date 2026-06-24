# SDD Integration 情境增強規格
# SDD Enhancement for Integration / Third-Party Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 04 規劃
**對應 CI/CD**: `cicd/SDD_INTEGRATION_CICD.md`

---

## SDD 核心強化原則

Integration 情境的 SDD 強化核心：**Consumer-Driven Contract（CDC）+ OpenAPI First**

> 整合不是兩端各自實作再對接，而是先有可驗證的消費者契約，再各自實作。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| Consumer Contract | CDC | `docs_template/sdd/api/CONSUMER-CONTRACT-TEMPLATE.yaml` | `docs/02_architecture/api/` |
| Provider API Spec | - | `docs_template/sdd/api/PROVIDER-API-SPEC-TEMPLATE.yaml` | `docs/02_architecture/api/` |
| Contract Test Spec（Integration）| - | `docs_template/sdd/testing/CONTRACT-TEST-SPEC-INTEGRATION-TEMPLATE.md` | `docs/03_testing/contracts/` |
| Chaos Contract | - | `docs_template/sdd/testing/CHAOS-CONTRACT-TEMPLATE.md` | `docs/03_testing/contracts/` |
| ADR-Integration-ACL | - | `docs_template/sdd/architecture/ADR-INTEGRATION-ACL-TEMPLATE.md` | `docs/02_architecture/adr/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `integration-specialist-zh.yaml` | `consumer_driven_contract`、`openapi_spec_gen`、Chaos Contract |
| `sd-architect-zh.yaml` | `contract_document_gen`、OpenAPI First 設計 |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| 🔷 SCG-3 | API Contract 凍結前（OpenAPI Freeze） | integration-specialist / sd-architect |
| 🔷 SCG-2 | 架構設計凍結前 | sd-architect |

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線 |
| L1 | Build + Unit Test |
| SAST | 靜態分析 |
| Container | Docker Build + Scan |
| Contract | Consumer Contract Validate |
| SDD 強化 | Consumer Contract Validate + Chaos Contract |

---

## SDD 執行流程差異

```
v0.01 Integration：研究 API → 實作整合 → 測試對接
SDD Integration：  Consumer Contract 先行 → 🔷 SCG-3 → 各自實作 → Contract Test CI 驗證
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [Integration SOP](SOP.md)
