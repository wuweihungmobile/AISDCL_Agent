# SDD Security 情境增強規格
# SDD Enhancement for Security & Compliance Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 05 規劃
**對應 CI/CD**: `cicd/SDD_SECURITY_CICD.md`

---

## SDD 核心強化原則

Security 情境的 SDD 強化核心：**STRIDE Threat Model + SAD（Security Architecture Document）前置**

> 安全不是事後補洞，而是在設計階段即完成威脅建模，安全架構文件先於任何實作。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| Security Architecture Document | SAD | `docs_template/sdd/architecture/SAD-TEMPLATE.md` | `docs/06_quality/security/` |
| STRIDE Threat Model | STM | `docs_template/sdd/testing/STRIDE-THREAT-MODEL-TEMPLATE.md` | `docs/06_quality/security/` |
| Trust Boundary Map | - | `docs_template/sdd/architecture/TRUST-BOUNDARY-MAP-TEMPLATE.md` | `docs/02_architecture/` |
| Asset Inventory | - | `docs_template/sdd/testing/ASSET-INVENTORY-TEMPLATE.md` | `docs/06_quality/security/` |
| Compliance Matrix | CM | `docs_template/sdd/testing/COMPLIANCE-MATRIX-TEMPLATE.md` | `docs/06_quality/security/` |
| Security Test Spec | - | `docs_template/sdd/testing/SECURITY-TEST-SPEC-TEMPLATE.md` | `docs/03_testing/` |
| Security Monitoring Spec | - | `docs_template/sdd/deployment/SECURITY-MONITORING-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Incident Response Spec | - | `docs_template/sdd/deployment/INCIDENT-RESPONSE-SPEC-TEMPLATE.md` | `docs/06_quality/security/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `security-engineer-zh.yaml` | `stride_threat_model`、`security_arch_doc`、資產分類規格 |
| `compliance-officer-zh.yaml` | 合規對照矩陣格式、多框架並行（GDPR / PCI DSS / ISO 27001） |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| 🔷 SCG-5 | 安全規格凍結前（STRIDE + SAD 完成） | security-engineer |

**SCG-5 通過條件**：
- Asset Inventory 完成分類
- STRIDE 威脅模型完成（6 類威脅全分析）
- SAD 通過 security-engineer 審核
- Compliance Matrix 對應框架填寫完成

---

## STRIDE 六類威脅

| 威脅類型 | 說明 |
|---------|------|
| **S**poofing | 身份偽造 |
| **T**ampering | 資料竄改 |
| **R**epudiation | 不可否認性 |
| **I**nformation Disclosure | 資訊洩露 |
| **D**enial of Service | 服務拒絕 |
| **E**levation of Privilege | 權限提升 |

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線（Secret Scan + Dependency Check） |
| L1 | Build + Unit Test |
| SAST | 靜態安全分析 |
| Container | Docker Scan |
| DAST | 動態安全測試 |
| Compliance | 合規自動檢核 |
| SDD 強化 | STRIDE Validate + Compliance Matrix Auto-Check |

---

## SDD 執行流程差異

```
v0.01 Security：開發 → 安全審查 → 修補
SDD Security：  Asset Inventory → STRIDE 威脅建模 → 🔷 SCG-5（SAD） → 安全實作 → DAST 驗證
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [Security SOP](SOP.md)
