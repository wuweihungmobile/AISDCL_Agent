# 情境選擇決策樹
# Scenario Decision Tree

> **🎯 1 分鐘快速選擇最適合的開發情境**
>
> 根據以下決策樹，快速找到適合您專案的 AISDLC-SDD 情境。每個情境都有對應的強制 SCG 閘門，選擇情境後請確認閘門要求。

---

**版本**: v0.01
**創建日期**: 2025-01-15
**最後更新**: 2026-04-17
**閱讀時間**: 2 分鐘
**關聯文檔**: [SCENARIO_SELECTOR.md](./SCENARIO_SELECTOR.md)（詳細版）

---

## SDD SCG 閘門說明

每個情境選擇後，必須遵循對應的 **SCG 閘門（Spec-First Gate）**。閘門不可跳過，這是 SDD 框架的核心原則。

| 閘門 | 強制文件 | 說明 |
|------|---------|------|
| SCG-0 | PRD + FRD | 需求凍結 |
| SCG-1 | SRD + API Spec | 設計凍結 |
| SCG-2 | C4 Model + ADR | 架構凍結 |
| SCG-3 | OpenAPI Contract | Contract Freeze（開發啟動前） |
| SCG-4 | PR Review | 實作與規格一致性 |
| SCG-5 | RTM 100% | 交付前品質驗證 |
| SCG-6 | 所有閘門 | 發布前最終確認 |

---

## 🔀 主決策樹

```
┌─────────────────────────────────────────────────────────────────┐
│                    您的專案是什麼狀態？                          │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │   🆕 新專案   │   │  📦 既有專案  │   │  🔧 特定任務  │
    │  (無代碼庫)   │   │   (有代碼庫)  │   │   (跨專案)   │
    └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
           │                  │                  │
           ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │  GREENFIELD  │   │  見「既有專案  │   │  見「特定任務  │
    │    情境      │   │   決策樹」    │   │   決策樹」    │
    └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 📦 既有專案決策樹

```
┌─────────────────────────────────────────────────────────────────┐
│                    您的主要目標是什麼？                          │
└─────────────────────────────────────────────────────────────────┘
                              │
     ┌────────────┬───────────┼───────────┬────────────┐
     │            │           │           │            │
     ▼            ▼           ▼           ▼            ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ 新增功能 │ │ 改善品質 │ │ 提升效能 │ │ 整合系統 │ │ 其他目標 │
│ 修改功能 │ │ 重構代碼 │ │ 優化速度 │ │ 第三方API│ │   ↓     │
│ 修復 Bug│ │ 減技術債 │ │ 降資源耗 │ │ 資料對接 │ │         │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │
     ▼           ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     見下方
│ 🏚️      │ │ ♻️       │ │ ⚡       │ │ 🔌       │
│BROWNFIELD│ │REFACTOR │ │PERFORMANCE│ │INTEGRATION│
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### 其他既有專案目標

```
┌─────────────────────────────────────────────────────────────────┐
│                    其他目標分支                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │  建立自動化   │    │  補充測試    │    │  整理文檔    │
   │  CI/CD 部署  │    │  建立測試策略 │    │  技術文檔    │
   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │   🚀 DEVOPS  │    │  ✅ TESTING  │    │ 📚 DOCUMENT │
   └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 🔧 特定任務決策樹

```
┌─────────────────────────────────────────────────────────────────┐
│                 您需要處理什麼特定任務？                         │
└─────────────────────────────────────────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
        ┌──────────────┐              ┌──────────────┐
        │  安全評估    │              │  合規檢查    │
        │  滲透測試    │              │  安全加固    │
        │  漏洞修復    │              │  ISO/GDPR    │
        └──────┬───────┘              └──────┬───────┘
               │                             │
               └──────────────┬──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ 🔒 SECURITY  │
                       └──────────────┘
```

---

## 📊 情境快速對照表（含 SCG 閘門）

| 情境 | 適用時機 | 預計時間 | 主導 Agent | 強制 SCG 閘門 |
|------|----------|----------|------------|--------------|
| 🌱 **Greenfield** | 新專案從零開始 | 3-5 天 | PM/PO → SA → SD | SCG-0/1/2/3/4/5/6 完整 |
| 🏚️ **Brownfield** | 既有專案新增/修改功能 | 1-3 天 | SA + Code-Analyzer | As-Is 基線 → SCG-0 → SCG-4 |
| ♻️ **Refactoring** | 代碼重構/技術債清理 | 2-4 天 | SD + Code-Analyzer | INV Gate → SCG-4 |
| ⚡ **Performance** | 效能優化/速度提升 | 1-2 天 | Performance-Engineer | PBS Gate → SCG-6 |
| 🔌 **Integration** | 第三方 API 整合 | 0.5-2 天 | Integration Specialist | Consumer Contract → SCG-3 → SCG-4 |
| 🚀 **DevOps** | CI/CD Pipeline 建置 | 1-3 天 | DevOps-Engineer | Pipeline Spec → SCG-4 → SCG-6 |
| ✅ **Testing** | 測試策略/自動化測試 | 1-2 天 | QA-Lead | RTM Gate → SCG-5 → SCG-6 |
| 📚 **Documentation** | 技術文檔撰寫 | 0.5-1 天 | Technical-Writer | Living Doc → SCG-4 |
| 🔒 **Security** | 安全評估/合規檢查 | 1-3 天 | Security-Engineer | STRIDE → SCG-5 → SCG-6 |

### 各情境 SCG 閘門詳細說明

**🌱 Greenfield**（完整 SCG-0~6）:
- SCG-0：PRD + FRD 完整性凍結（需求基線）
- SCG-1/2：SRD + C4 + ADR 架構凍結
- SCG-3：OpenAPI Contract Freeze — 關鍵！凍結後才開發
- SCG-4：每次 PR 均需驗證實作與規格一致
- SCG-5：RTM 100% 覆蓋，交付前必通過
- SCG-6：最終發布品質守門

**🏚️ Brownfield**（SCG-0 前先建立 As-Is 基線）:
- 前置：逆向規格工程，產出 As-Is SRD + Tech Debt Spec + Gap Analysis
- SCG-0：改造需求凍結（基於 Gap Analysis 的 To-Be 需求）
- SCG-4：改造實作與改造規格一致性確認

**♻️ Refactoring**（INV Gate 是核心）:
- INV Gate：Business Invariants 凍結，確認重構不破壞業務不變量
- SCG-4：重構 PR Review，驗證 Invariant Test Contract 全過

**🔌 Integration**（Consumer Contract 先行）:
- SCG-3：Consumer Contract 凍結後才開始整合實作
- SCG-4：整合實作與 Consumer Contract 一致性確認

**⚡ Performance**（PBS Gate 是核心）:
- PBS Gate：Performance Baseline Spec + SLO 量化定義，凍結後才執行優化
- SCG-6：優化結果達到 SLO 目標後才可確認完成

---

## 🎯 常見組合情境（含 SCG 轉換要求）

有些專案可能需要組合多個情境，以下是常見組合。**情境切換前必須確認當前 SCG 閘門已通過**。

### 組合 1: 新專案完整開發
```
Greenfield → DevOps → Testing
    │           │         │
    ▼           ▼         ▼
  需求分析    建置CI/CD   測試策略
  架構設計    自動部署    自動化測試

SCG 轉換要求：
  Greenfield → DevOps: 至少 SCG-4 通過
  DevOps → Testing:    SCG-4 通過
  Testing 完成: SCG-5 + SCG-6
```

### 組合 2: 既有專案大改造
```
Brownfield → Refactoring → Performance → Testing
    │           │              │           │
    ▼           ▼              ▼           ▼
  影響分析    代碼重構      效能優化     回歸測試

SCG 轉換要求：
  Brownfield → Refactoring: SCG-0 通過（改造需求凍結）
  Refactoring → Performance: INV Gate + SCG-4 通過
  Performance → Testing: PBS Gate 通過
  Testing 完成: SCG-5 + SCG-6
```

### 組合 3: 安全加固專案
```
Security → Brownfield → Testing
    │           │          │
    ▼           ▼          ▼
  漏洞掃描    漏洞修復    安全測試

SCG 轉換要求：
  Security → Brownfield: STRIDE 完成
  Brownfield → Testing: SCG-0 + SCG-4 通過
  Testing 完成: SCG-5 + SCG-6
```

---

## 🔗 詳細文檔連結

| 情境 | SOP | 快速參考 | 深度指南 |
|------|-----|----------|----------|
| Greenfield | [SOP](../../../scenarios/greenfield/SOP.md) | [QuickRef](../../../scenarios/greenfield/SOP_QuickRef.md) | [DeepDive](../../../scenarios/greenfield/SOP_DeepDive.md) |
| Brownfield | [SOP](../../../scenarios/brownfield/SOP.md) | [QuickRef](../../../scenarios/brownfield/SOP_QuickRef.md) | [DeepDive](../../../scenarios/brownfield/SOP_DeepDive.md) |
| Refactoring | [SOP](../../../scenarios/refactoring/SOP.md) | [QuickRef](../../../scenarios/refactoring/SOP_QuickRef.md) | [DeepDive](../../../scenarios/refactoring/SOP_DeepDive.md) |
| Performance | [SOP](../../../scenarios/performance/SOP.md) | [QuickRef](../../../scenarios/performance/SOP_QuickRef.md) | [DeepDive](../../../scenarios/performance/SOP_DeepDive.md) |
| Integration | [SOP](../../../scenarios/integration/SOP.md) | [QuickRef](../../../scenarios/integration/SOP_QuickRef.md) | [DeepDive](../../../scenarios/integration/SOP_DeepDive.md) |
| DevOps | [SOP](../../../scenarios/devops/SOP.md) | [QuickRef](../../../scenarios/devops/SOP_QuickRef.md) | [DeepDive](../../../scenarios/devops/SOP_DeepDive.md) |
| Testing | [SOP](../../../scenarios/testing/SOP.md) | [QuickRef](../../../scenarios/testing/SOP_QuickRef.md) | [DeepDive](../../../scenarios/testing/SOP_DeepDive.md) |
| Documentation | [SOP](../../../scenarios/documentation/SOP.md) | [QuickRef](../../../scenarios/documentation/SOP_QuickRef.md) | [DeepDive](../../../scenarios/documentation/SOP_DeepDive.md) |
| Security | [SOP](../../../scenarios/security/SOP.md) | [QuickRef](../../../scenarios/security/SOP_QuickRef.md) | [DeepDive](../../../scenarios/security/SOP_DeepDive.md) |

---

## 💡 不確定時怎麼辦？

如果您不確定該選擇哪個情境：

1. **問自己**: 「這個專案的核心目標是什麼？」
2. **選擇主要情境**: 先選擇最符合核心目標的情境
3. **組合使用**: 如需要，後續再加入其他情境

**還是不確定？** 請參考 [SCENARIO_SELECTOR.md](./SCENARIO_SELECTOR.md) 的詳細問答指南。

---

---

## 💡 不確定時怎麼辦？（補充：SCG 視角）

如果您確定了情境但不確定從哪個 SCG 閘門開始：

1. **新建立文件** → 從 SCG-0 開始（需求先行）
2. **已有部分規格** → 使用 `/spec-compliance-check` 確認現有規格符合哪個 SCG 程度
3. **繼承其他情境的規格** → 參考 `scenarios/SCENARIO_TRANSITION_GUIDE.md` 規格傳遞包

**還是不確定？** 請參考 [SCENARIO_SELECTOR.md](./SCENARIO_SELECTOR.md) 的詳細問答指南，或直接使用 `/sdd-gate` Skill 讓 AI 幫您評估當前 SCG 狀態。

---

**文檔版本**: v0.01
**最後更新**: 2026-04-17
**維護者**: AISDLC-SDD Framework Team
