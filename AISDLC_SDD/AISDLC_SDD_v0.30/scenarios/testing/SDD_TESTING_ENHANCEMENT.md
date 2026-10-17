# SDD Testing 情境增強規格
# SDD Enhancement for Testing / QA Scenario

**版本**: v1.0
**建立日期**: 2026-04-14
**基於**: AISDLC-SDD Phase 05 規劃
**對應 CI/CD**: `cicd/SDD_TESTING_CICD.md`

---

## SDD 核心強化原則

Testing 情境的 SDD 強化核心：**Test Pyramid Spec（測試金字塔規格）先於開發**

> 測試不是開發完才補，而是測試策略規格和測試契約必須先於實作定義清楚。

---

## 新增強制文件

| 文件 | 縮寫 | 範本 | 產出位置 |
|------|------|------|---------|
| Test Strategy Spec | TSS | `docs_template/sdd/testing/TEST-STRATEGY-SPEC-TEMPLATE.md` | `docs/03_testing/` |
| Test Contract Spec | TCS | `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md` | `docs/03_testing/contracts/` |
| RTM | - | `docs_template/sdd/testing/RTM-TEMPLATE.md` | `docs/03_testing/` |
| Defect Classification Spec | - | `docs_template/sdd/testing/DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md` | `docs/03_testing/` |
| Living Test Report | - | `docs_template/sdd/testing/LIVING-TEST-REPORT-TEMPLATE.md` | `docs/03_testing/` |
| Env Contract Spec | - | `docs_template/sdd/testing/ENV-CONTRACT-SPEC-TEMPLATE.md` | `docs/03_testing/contracts/` |

---

## SDD 新增 Agent 技能

| Agent | 新增 Skill |
|-------|-----------|
| `qa-lead-zh.yaml` | `test_strategy_spec`、`test_pyramid_spec_gen`、`test_contract_gen` |
| `qa-automation-zh.yaml` | 效能測試場景規格、Contract Test CI 整合 |
| `qa-tester-zh.yaml` | `test_contract_gen`、RTM 生成 |

---

## Spec-First Gate（SCG）

| Gate | 觸發時機 | 負責 Agent |
|------|---------|-----------|
| RG-TEST（補充閘；Test Strategy Gate） | 測試計畫凍結前（Test Strategy Spec；SCG-3 後、測試開始前） | qa-lead |
| 🔷 SCG-4（PR Review Gate） | PR Review（實作與規格一致性） | dev-senior |
| 🔷 SCG-5 | 交付前（RTM 100% 覆蓋） | qa-tester |

> 🔴 **115／S-08 訂正**：**被訂正的原文逐字保留（訂正協議：禁止靜默覆寫）**：
> 「`| 🔷 SCG-4 | 測試計畫凍結前（Test Strategy Spec） | qa-lead |`」。SCG-4 的 SSOT 名稱是 PR Review Gate
> （`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`）；「測試計畫凍結前」屬補充閘 RG-TEST（`guides/system/sdd/SDD_GUIDE.md`）。
> 同檔下方〈SDD 執行流程差異〉的同型寫法一併訂正。

---

## Quality Gate 定義

| 指標 | 門檻 |
|------|------|
| 單元測試覆蓋率 | ≥ 80% |
| 整合測試通過率 | 100% |
| RTM 追溯覆蓋 | 100% |
| 缺陷密度 | ≤ 基準值 |

---

## CI/CD 基線

| 層級 | 內容 |
|------|------|
| L0 | 安全基線 |
| L1 | Build + Unit Test |
| SAST | 靜態分析 |
| L2（Full）| Integration + E2E |
| SDD 強化 | TestSpec Validate + Quality Gate + RTM Coverage |

---

## SDD 執行流程差異

```
v0.01 Testing：需求 → 開發 → 寫測試 → 執行
SDD Testing：  Test Strategy Spec → RG-TEST → Test Contract → 開發（Testability by Design）→ 🔷 SCG-4（PR Review）→ Quality Gate
# 🔴 115／S-08 訂正：原文「SDD Testing：  Test Strategy Spec → 🔷 SCG-4 → Test Contract → 開發（Testability by Design）→ Quality Gate」
```

---

**相關文件**：
- [SDD 核心原則](../../SDD_Core_Principles.md)
- [SDD 快速指引](../../guides/system/sdd/SDD_GUIDE.md)
- [Testing SOP](SOP.md)
