# AISDLC-SDD v0.01 多情境組合範例

**版本**: v0.01（SDD 版）
**主題**: 常見多情境 SDD 組合的完整執行指引
**最後更新**: 2026-04-15

---

## 常見組合 1：Greenfield + Security + Integration

**情境**: 開發全新 FinTech API 服務

### 執行指令

```
我需要開發一個全新的金融 API 服務，同時需要安全設計和第三方支付整合。

主情境：Greenfield（Spec-First 全新開發）
次情境：Security（STRIDE 威脅模型）
次情境：Integration（Stripe 支付整合）

請依以下 SDD 順序執行：
1. Greenfield → SCG-0（PRD + FRD 凍結）
2. Security STRIDE 分析 → 安全需求納入 SRD
3. Greenfield → SCG-1~2（SRD + C4 + ADR，含安全架構）
4. Integration → Consumer Contract（Stripe API Contract）
5. Greenfield → SCG-3（所有 API Contract 凍結，含整合 Contract）

載入：
- AISDLC_SDD_v0.01/scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md
- AISDLC_SDD_v0.01/scenarios/security/SDD_SECURITY_ENHANCEMENT.md
- AISDLC_SDD_v0.01/scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md
```

### 關鍵 SCG 閘門順序

```
SCG-0 → STRIDE 安全分析 → SCG-1 → SCG-2 → Consumer Contract → SCG-3
        ↑ Security 次情境在 SCG-2 前介入，安全需求納入架構
```

---

## 常見組合 2：Brownfield + Refactoring

**情境**: 既有電商系統模組重構

### 執行指令

```
我有一個既有電商系統的訂單模組需要重構，但我不清楚現有規格。

主情境：Brownfield（逆向規格工程）
次情境：Refactoring（Invariant 保護重構）

請依以下 SDD 順序：

階段 A - Brownfield 逆向規格：
1. 分析現有代碼，建立 As-Is SRD（代碼路徑：[路徑]）
2. 識別 Business Invariants（INV-XXX）
3. 執行 Gap Analysis（As-Is vs 期望的 To-Be）

階段 B - 切換 Refactoring 情境：
4. 基於 Business Invariants 建立 Invariant Test Contract
5. 規劃重構策略（Strangler Fig 推薦）
6. 執行 SCG-4 驗證重構後代碼仍符合規格

載入：
- AISDLC_SDD_v0.01/scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md
- AISDLC_SDD_v0.01/scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md
```

### 情境切換點

```
Brownfield As-Is SRD 完成 → Business Invariants 確認 → 切換 Refactoring 情境
```

---

## 常見組合 3：Greenfield + DevOps + Testing

**情境**: 新專案同時建立 CI/CD 和測試體系

### 執行指令

```
我開發新專案的同時需要建立完整的 CI/CD Pipeline 和測試策略。

主情境：Greenfield（Spec-First）
次情境：DevOps（SCG 閘門整合到 Pipeline）
次情境：Testing（RTM + Contract Testing）

並行策略：
- Greenfield 執行到 SCG-3 後，DevOps 和 Testing 可以並行開始

主線（Greenfield）：
- SCG-0 需求 → SCG-1~2 架構 → SCG-3 Contract Freeze

並行 A（DevOps，在 SCG-3 後啟動）：
- CI/CD Pipeline 規格
- 整合 SCG-4 PR Check 和 SCG-6 Release Gate

並行 B（Testing，在 SCG-3 後啟動）：
- RTM 建立（對應 F-XXX）
- Contract Test Suite
- E2E 測試規劃

最終：SCG-5 RTM 100% + SCG-6 CI/CD 全通過 → 發布

載入所有三個情境的 Enhancement 文件。
```

---

## 常見組合 4：Migration + Testing

**情境**: 資料庫遷移前建立完整測試保護

### 執行指令

```
我需要將系統從 MySQL 遷移到 PostgreSQL，需要完整的測試保護。

主情境：Migration（MCM 遷移規格）
次情境：Testing（Invariant Contract Testing）

SDD 順序：
1. Migration - 建立遷移規格文件（MCM Validate）
2. Testing - 識別資料不變量並建立 Contract
3. Migration - 執行遷移計畫，每個步驟執行 Contract 驗證
4. SCG-5 - 遷移後 RTM 100% 通過

關鍵原則：Contract Testing 必須在遷移開始前建立完成。

載入：
- AISDLC_SDD_v0.01/scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md
- AISDLC_SDD_v0.01/scenarios/testing/SDD_TESTING_ENHANCEMENT.md
```

---

## 組合情境注意事項

### SCG 閘門在組合情境中的規則

```
問：多個情境的 SCG 閘門如何協調？

答：
1. 主情境的 SCG 閘門順序不變（SCG-0 → 1 → 2 → 3 → 4 → 5 → 6）
2. 次情境在適當的主情境 SCG 閘門「之前」介入
   - Security STRIDE → 必須在 SCG-2 架構凍結前完成
   - Integration Contract → 必須在 SCG-3 Contract Freeze 前完成
   - Testing RTM → 必須在 SCG-5 前完成
3. 次情境不可延後主情境閘門執行

當組合情境時，請告訴我：
1. 每個次情境在哪個主情境閘門前介入？
2. 是否有特殊的依賴關係？
```

---

**版本**: v0.01（AISDLC-SDD）
**最後更新**: 2026-04-15
