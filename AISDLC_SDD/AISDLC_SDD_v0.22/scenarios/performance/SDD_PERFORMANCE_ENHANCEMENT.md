# SDD Performance 情境增強規格
# SDD Enhancement for Performance Optimization Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 05 規劃
**對應 CI/CD**: `cicd/SDD_PERFORMANCE_CICD.md`

---

## SDD 核心強化原則

Performance 情境的 SDD 強化核心：**SLO/SLA Spec 先行 + PBS（Performance Baseline Spec）**

> 效能優化不是「跑慢了再改」，而是先定義可量化的 SLO 規格，再以 Benchmark Gate 驗證。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| Performance Baseline Spec | PBS | `docs_template/sdd/testing/PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` | `docs/04_planning/performance/` |
| Baseline Performance Report | - | `docs_template/sdd/testing/BASELINE-PERFORMANCE-REPORT-TEMPLATE.md` | `docs/04_planning/performance/` |
| Performance Optimization ADR | - | `docs_template/sdd/adr/PERFORMANCE-OPTIMIZATION-ADR-TEMPLATE.md` | `docs/02_architecture/adr/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `performance-engineer-zh.yaml` | `slo_sla_spec`、`baseline_benchmark_spec`、量化優化 ADR |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| 🔷 SCG-6 | 效能規格凍結前（PBS 完成） | performance-engineer |

**SCG-6 通過條件**：
- SLO/SLA 指標已量化定義（P99、Throughput、Error Rate）
- Baseline 已測量並記錄
- Benchmark Gate 閾值已設定

---

## SLO 規格要求

PBS 必須包含：
```
- 回應時間：P50 / P95 / P99
- 吞吐量（TPS/RPS）
- 錯誤率上限
- 資源使用率上限（CPU/Memory）
- 測試場景（正常負載 / 峰值負載 / 壓力測試）
```

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線 |
| L1 | Build + Unit Test |
| Container | Docker Build |
| 🔴 Benchmark | PBS Gate（SLO 驗證） |
| SDD 強化 | PBS Validate + SLO Gate |

---

## SDD 執行流程差異

```
v0.01 Performance：發現瓶頸 → 優化 → 測試
SDD Performance：  PBS 規格先行（SLO 定義）→ 🔷 SCG-6 → Benchmark → 優化 → Gate 再驗證
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [Performance SOP](SOP.md)
