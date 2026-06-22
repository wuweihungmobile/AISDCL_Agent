# AISDLC-SDD Brownfield 指令集

**情境**: Brownfield — 逆向規格工程 + 既有系統維護
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我有一個既有系統需要逆向建立規格文件，使用 SDD Brownfield 情境。

載入：AISDLC_SDD_v0.01/scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md

系統資訊：
- 系統名稱：[名稱]
- 代碼路徑：[路徑]
- 主要模組：[列出]
- 主要問題：[描述技術債/規格缺失]

SDD 流程：As-Is 分析 → 逆向 SRD → Business Invariants → Gap Analysis → To-Be 規劃
```

## 📊 階段推進

### As-Is 逆向規格工程
```
請分析既有代碼，建立 As-Is SRD。

代碼路徑：[路徑]
目標模組：[模組名稱]

產出：
- As-Is SRD（現有系統架構描述）
- 資料模型（逆向 ERD）
- 現有 API 清單（非規格，是現況描述）
```

### Business Invariants 提取
```
請從既有系統代碼中提取 Business Invariants。

識別：系統中不管如何修改都不能違反的業務規則
格式：INV-001：[描述]，INV-002：[描述]...

參考代碼：[路徑]
這些 Invariants 將成為 Invariant Test Contract 的基礎。
```

### Gap Analysis
```
請執行 Gap Analysis。

As-Is SRD：[路徑]
期望 To-Be：[描述業務目標]

產出：
- 現有 vs 期望的差距清單
- 技術債（TD-XXX）
- 改善建議優先級
```

### ADR Archaeology（補回 ADR）
```
請為既有系統補回架構決策記錄（ADR Archaeology）。

系統：[名稱]
需要補回的主要決策：
- 資料庫選型
- 認證機制
- [其他主要決策]

格式：ADR-NNN（從 ADR-001 開始補回）
```

## 🔄 常見變體

### 新功能加入既有系統
```
我要在既有系統中新增功能 [功能描述]。

既有系統：[系統名稱/路徑]
新功能：[描述]

請先建立 As-Is SRD（如未存在），
再使用 Spec-First 方式設計新功能（SCG-0 → SCG-3）。
```

### 技術債盤點
```
請對既有系統執行技術債盤點。

代碼路徑：[路徑]

產出：
- TD-XXX 技術債清單（含嚴重度）
- 優先修復建議
- 對應的 Code Quality Baseline
```
