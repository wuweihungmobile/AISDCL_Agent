# SDD DevOps 情境增強規格
# SDD Enhancement for DevOps / CI/CD Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 04 規劃
**對應 CI/CD**: `cicd/SDD_CICD_BASE_LAYER.md`（DevOps 使用基礎層 + L3 進階）

---

## SDD 核心強化原則

DevOps 情境的 SDD 強化核心：**IaC-as-Spec**（基礎設施即規格）

> Pipeline 和基礎設施不是「做完就好」，而是必須有可驗證的規格先行文件。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| IaC Specification | IaCS | `docs_template/sdd/architecture/INFRA-REQUIREMENTS-SPEC-TEMPLATE.md` | `docs/08_deployment/iac/` |
| Pipeline Spec | PipeSpec | `docs_template/sdd/deployment/PIPELINE-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Cutover Spec | - | `docs_template/sdd/deployment/CUTOVER-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Rollback Spec | - | `docs_template/sdd/deployment/ROLLBACK-SPEC-TEMPLATE.md` | `docs/08_deployment/` |
| Monitoring Alert Spec | - | `docs_template/sdd/deployment/MONITORING-ALERT-SPEC-TEMPLATE.md` | `docs/08_deployment/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `devops-engineer-zh.yaml` | `iac_specification`、`pipeline_spec_doc`、`cutover_spec_gen`、`rollback_spec_gen` |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| 🔷 SCG-Pipeline | Pipeline 設計前 | devops-engineer |
| 🔷 SCG-2 | 基礎設施架構凍結前 | sd-architect |

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線（SAST + Secret Scan） |
| L1 | Build + Unit Test |
| IaC SAST | Terraform/K8s 靜態分析 |
| Container | Docker Build + Scan |
| L2 | Integration Test |
| L3 | Canary / Blue-Green |
| SDD 強化 | IaCS Validate + Pipeline Spec Doc |

---

## SDD 執行流程差異

```
v0.01 DevOps：設計 Pipeline → 實作 → 文件補齊
SDD DevOps：  IaCS 規格先行 → 🔷 SCG-Pipeline → Pipeline 實作 → Spec 一致性驗證
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [DevOps SOP](SOP.md)
