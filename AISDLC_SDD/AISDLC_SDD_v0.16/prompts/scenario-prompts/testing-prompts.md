# AISDLC-SDD Testing 指令集

**情境**: Testing — RTM 驅動的測試體系建立
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要建立完整的測試體系，使用 SDD Testing 情境。

載入：AISDLC_SDD_v0.01/scenarios/testing/SDD_TESTING_ENHANCEMENT.md

測試需求：
- 系統：[系統名稱]
- 現有覆蓋率：[X%]
- 目標：[RTM 100% 覆蓋 / Contract Testing / E2E]
- FRD 路徑：[路徑]（用於生成 RTM）
```

## 📊 階段推進

### RTM 生成（SCG-5 基礎）
```
請生成 RTM 需求追蹤矩陣。

FRD 路徑：[路徑]

請使用 rtm-generate skill：
- 對應每個 F-XXX 需求生成 TC-XXX 測試案例
- 目標：100% 覆蓋所有功能需求
- 記錄覆蓋率統計

產出：docs/03_testing/RTM-[System].md
```

### 測試策略規劃
```
請制定測試策略（測試金字塔）。

系統：[名稱]
技術棧：[後端/前端/Mobile]

策略：
- 單元測試（70%）：[覆蓋業務邏輯/Invariants]
- 整合測試（20%）：[API Contract 驗證]
- E2E 測試（10%）：[核心用戶流程]

產出：docs/03_testing/Test-Plan-[System].md
```

### Invariant Test Contract
```
請建立 Invariant Test Contract。

Business Invariants：[INV-001, INV-002, ...]

每個 Invariant 對應：
- 測試場景描述
- 通過條件
- 邊界條件

產出：docs/03_testing/contracts/Invariant-Contract-[Module].md
```

### Contract Testing（API）
```
請建立 API Contract Test Suite。

OpenAPI 規格：[路徑]

測試項目：
- 每個端點的 Request/Response 格式驗證
- 錯誤碼覆蓋（4xx/5xx）
- 認證/授權邊界

工具偏好：[Pact / Dredd / Postman Newman]
```

### SCG-5 Coverage 驗證
```
請執行 SCG-5 RTM 覆蓋率驗證。

RTM 路徑：docs/03_testing/RTM-[System].md

驗證：
- 總需求數：[N]
- 已覆蓋：[M]
- 覆蓋率：[M/N * 100%]
- 未覆蓋清單：[F-XXX 列表]

目標：100% 才可通過 SCG-5。
```

## 🔄 常見變體

### 補齊現有測試 RTM
```
我有現有的測試，但沒有 RTM，請補建。

測試文件路徑：[路徑]
FRD 路徑：[路徑]

請反向建立 RTM：從測試案例回溯對應的 F-XXX 需求，
並識別哪些需求缺少測試覆蓋。
```

### 快速測試評估
```
請評估當前測試品質。

測試路徑：[路徑]

評估：
- 測試類型分佈（Unit/Integration/E2E）
- 是否有 Invariant 測試？
- Contract Testing 是否存在？
- RTM 覆蓋率（估計值）
```
