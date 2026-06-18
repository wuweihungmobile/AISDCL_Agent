# AISDLC-SDD v0.01 場景快速參考

**版本**: v0.01（SDD 版）
**用途**: 10 個 SDD 場景的快速啟動指令
**最後更新**: 2026-04-15

---

## 場景選擇快速決策

```
我需要使用 AISDLC-SDD，但不確定選哪個場景。

我的情況：[描述專案類型和目標]

請根據以下分類協助我選擇：
- 全新專案 → Greenfield
- 既有系統新功能/維護 → Brownfield
- 代碼品質改善 → Refactoring
- 文件補齊 → Documentation
- 建立測試體系 → Testing
- CI/CD 自動化 → DevOps
- 整合第三方服務 → Integration
- 系統遷移 → Migration
- 效能調優 → Performance
- 安全強化 → Security
```

---

## 10 個場景快速啟動指令

### 🟢 Greenfield — 全新 Spec-First 開發
```
請使用 AISDLC-SDD Greenfield 情境。

載入：AISDLC_SDD_v0.01/scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md

專案資訊：
- 專案名稱：[名稱]
- 業務目標：[描述]
- 目標平台：[Web/Mobile/Backend/All]

SDD 流程：PRD → SCG-0 → SRD → SCG-1~2 → API → SCG-3 → 開發
```

### 🟡 Brownfield — 逆向規格工程
```
請使用 AISDLC-SDD Brownfield 情境。

載入：AISDLC_SDD_v0.01/scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md

既有系統資訊：
- 系統名稱：[名稱]
- 代碼路徑：[路徑]
- 主要問題：[描述]

SDD 流程：As-Is SRD → Business Invariants → Gap Analysis → To-Be SRD → SCG-1~2
```

### 🔄 Refactoring — Invariant 保護重構
```
請使用 AISDLC-SDD Refactoring 情境。

載入：AISDLC_SDD_v0.01/scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md

重構目標：
- 模組/功能：[描述]
- 重構策略：[Strangler Fig / Branch by Abstraction / Big-bang]
- 主要問題：[技術債 TD-XXX]

SDD 流程：Business Invariants → Invariant Contract → 重構規劃 → SCG-4
```

### 📚 Documentation — 文件維護
```
請使用 AISDLC-SDD Documentation 情境。

載入：AISDLC_SDD_v0.01/scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md

文件需求：
- 目標：[補齊缺失文件 / ADR 回補 / Living Doc 建立]
- 系統：[系統名稱]

SDD 流程：文件盤點 → ADR Archaeology → Living Doc Strategy → RTM 補齊
```

### ✅ Testing — 測試體系建立
```
請使用 AISDLC-SDD Testing 情境。

載入：AISDLC_SDD_v0.01/scenarios/testing/SDD_TESTING_ENHANCEMENT.md

測試需求：
- 測試類型：[Unit/Integration/E2E/Contract]
- 當前覆蓋率：[X%]
- 目標：[RTM 100% 覆蓋]

SDD 流程：RTM 建立 → Invariant Test Contract → 測試策略 → SCG-5
```

### ⚙️ DevOps — CI/CD 自動化
```
請使用 AISDLC-SDD DevOps 情境。

載入：AISDLC_SDD_v0.01/scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md

CI/CD 需求：
- 目標平台：[GitHub Actions / GitLab CI / Jenkins]
- 品質閘門：[需要整合 SCG-4~6]
- 環境：[Dev/Staging/Production]

SDD 流程：Pipeline 規格 → SCG 閘門整合 → 自動化驗證
```

### 🔌 Integration — 第三方整合
```
請使用 AISDLC-SDD Integration 情境。

載入：AISDLC_SDD_v0.01/scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md

整合需求：
- 服務名稱：[服務]
- 整合類型：[REST API / Webhook / SDK / 其他]
- Consumer Contract：[需要建立]

SDD 流程：Contract-First 設計 → Consumer Contract → SCG-3 → 實作
```

### 🚚 Migration — 系統遷移
```
請使用 AISDLC-SDD Migration 情境。

載入：AISDLC_SDD_v0.01/scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md

遷移需求：
- 來源系統：[描述]
- 目標系統：[描述]
- 資料量：[估計]
- 停機容忍：[零停機 / 允許維護窗口]

SDD 流程：MCM 驗證 → 遷移規格 → Contract 比對 → 執行計畫
```

### 🚀 Performance — 效能調優
```
請使用 AISDLC-SDD Performance 情境。

載入：AISDLC_SDD_v0.01/scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md

效能需求：
- 問題描述：[描述瓶頸]
- SLO 目標：[定義 PBS SLO]
- 當前指標：[測量值]

SDD 流程：PBS SLO 定義 → Benchmark → 優化規格 → SCG-6 + PBS Gate
```

### 🔒 Security — 安全強化
```
請使用 AISDLC-SDD Security 情境。

載入：AISDLC_SDD_v0.01/scenarios/security/SDD_SECURITY_ENHANCEMENT.md

安全需求：
- 系統類型：[Web/API/Mobile]
- 威脅範圍：[執行 STRIDE 威脅模型]
- 合規要求：[GDPR/HIPAA/PCI-DSS/其他]

SDD 流程：STRIDE 威脅模型 → 安全規格 → SCG-5 STRIDE Validate
```

---

## 場景組合快速指令

### 組合 1：Greenfield + Integration
```
我的新專案需要整合第三方服務。

主情境：Greenfield（新專案 Spec-First）
次情境：Integration（[服務名稱] 整合）

請載入兩個情境的 Enhancement，優先執行 Greenfield SCG-0，
整合 API Contract 在 SCG-3 時一併凍結。
```

### 組合 2：Brownfield + Refactoring
```
我需要在理解既有系統後進行重構。

主情境：Brownfield（逆向規格工程）
次情境：Refactoring（Invariant 保護重構）

請先建立 As-Is SRD，提取 Business Invariants 後再規劃重構。
```

### 組合 3：任何情境 + Security
```
我的[情境名稱]專案需要執行安全審查。

主情境：[情境]
次情境：Security（STRIDE 威脅模型）

請在 SCG-2 架構凍結前執行 STRIDE，將安全需求納入 SRD。
```

---

**版本**: v0.01（AISDLC-SDD）
**最後更新**: 2026-04-15
