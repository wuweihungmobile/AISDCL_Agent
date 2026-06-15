# AISDLC-SDD Refactoring 指令集

**情境**: Refactoring — Business Invariant 保護下的系統重構
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要重構 [模組/系統名稱]，使用 SDD Refactoring 情境（Invariant 保護）。

載入：AISDLC_SDD_v0.01/scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md

重構目標：
- 模組：[名稱/路徑]
- 問題：[描述：高複雜度/技術債 TD-XXX/效能瓶頸]
- 重構策略偏好：[Strangler Fig/Branch by Abstraction/Big-bang]

SDD 流程：Invariants 識別 → Test Contract → 重構規劃 → 實作 → SCG-4 驗證
```

## 📊 階段推進

### Business Invariants 識別
```
請識別 [模組名稱] 的 Business Invariants。

代碼路徑：[路徑]

找出：不管如何重構都不能違反的業務規則
格式：INV-001：[規則描述]

這些是重構的邊界條件，必須在重構前確認。
```

**🔴 人工確認點**：確認 Invariants 清單後才繼續

### Invariant Test Contract 建立
```
Business Invariants 已確認，請建立 Invariant Test Contract。

Invariants：[INV-001, INV-002, ...]

產出：docs/03_testing/contracts/Invariant-Contract-[Module].md
每個 INV-XXX 對應至少一個可執行的測試案例。
```

### 重構策略規劃
```
請規劃重構策略。

當前問題：[描述]
技術債：[TD-XXX 列表]
Invariants：[已確認的 INV-XXX]

推薦策略：
- Strangler Fig（逐步替換，低風險）
- Branch by Abstraction（並行開發，適合大型系統）
- Big-bang（一次性重構，高風險但簡單）

請分析並建議最適合的策略，並提供分階段執行計畫。
```

### SCG-4 重構驗證
```
重構完成，請執行 SCG-4 驗證。

驗證項目：
1. 所有 Invariant Test Contract 是否全數通過？
2. 現有 API 是否維持相容性（API-COMPAT）？
3. 效能指標是否達標？

重構代碼：[PR/路徑]
```

## 🔄 常見變體

### 緊急熱修復下的最小重構
```
系統有緊急問題需要修復，同時需要最小範圍重構。

緊急問題：[描述]
最小重構範圍：[模組]

請先識別核心 Invariants，確保修復不違反業務規則。
```

### 技術債清除計畫
```
我有一批技術債需要計畫性清除。

技術債：[TD-001, TD-002, ... 列表]

請根據 Invariants 影響範圍排序技術債，
制定分 Sprint 清除計畫，每個 Sprint 後執行 SCG-4 驗證。
```
