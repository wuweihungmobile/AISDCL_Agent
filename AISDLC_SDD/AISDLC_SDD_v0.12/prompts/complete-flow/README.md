# Complete Flow Examples
# 完整流程範例集

**版本**: v1.0-SDD
**用途**: 提供完整的端到端執行範例（含 SDD SCG 閘門）
**最後更新**: 2026-04-16

---

## 📚 範例清單

### 1. [Greenfield 端到端範例](./end-to-end-greenfield-example.md)
**範例專案**: TaskMaster 任務管理 Web App
**情境**: Greenfield（全新專案開發）
**亮點**:
- 從零到完整 PRD/FRD/SRD/API Specs（Spec-First）
- SCG-0 → SCG-6 完整閘門流程示範
- 技術棧選型 + ADR 決策記錄
- OpenAPI Contract Freeze 前置於後端實作

**適合對象**:
- 第一次使用 AISDLC-SDD
- 想了解 Spec-First Gate 完整流程
- 開發新專案的團隊

**預計閱讀時間**: 15-20 分鐘

---

### 2. [多情境組合範例](./multi-scenario-combination-example.md)
**範例專案**: 電商系統（支付整合 + 效能優化）
**情境**: Brownfield + Integration + Performance
**亮點**:
- 多情境協同工作示範（含 SDD 閘門協調）
- 並行執行策略
- RTM 需求追蹤跨情境整合
- 組合效率提升

**適合對象**:
- 複雜任務需要多個情境
- 想了解情境組合方式
- 需要優化執行效率的團隊

**預計閱讀時間**: 10-15 分鐘

---

## 🎯 如何使用這些範例

### 學習路徑（SDD 版）

#### 第 1 步：快速體驗（5 分鐘）
```
閱讀：prompts/quick-start/5-minute-start.md
行動：執行 5 分鐘快速體驗
```

#### 第 2 步：理解 SCG 閘門（10 分鐘）
```
閱讀：workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md
理解：SCG-0 ~ SCG-6 閘門定義與強制產出
```

#### 第 3 步：深入完整流程（20 分鐘）
```
閱讀：end-to-end-greenfield-example.md
理解：Spec-First 完整流程、人機協作確認點、SDD 文檔產出
```

#### 第 4 步：進階應用（15 分鐘）
```
閱讀：multi-scenario-combination-example.md
學習：多情境組合、並行執行、效率優化
```

#### 第 5 步：實際執行（2-4 小時）
```
選擇一個真實專案
套用對應情境 + SCG 閘門
產出完整規格文檔後再開發
```

---

## 💡 SDD 範例特色

### Spec-First Gate 示範
- ✅ 每個範例均包含 SCG 閘門驗證步驟
- ✅ 規格文件凍結（API Contract Freeze）前不進行實作
- ✅ 所有技術決策附帶 ADR 記錄

### 完整追蹤
- ✅ 每個階段都有輸入/輸出文件清單
- ✅ 人機協作 🔴 確認點清晰標註
- ✅ RTM 需求追蹤鏈貫穿全程

### 最佳實踐
- ✅ 展示 Design-as-Doc 原則
- ✅ 展示 Contract-Driven 開發順序
- ✅ 展示 SCG 閘門不可跳過的執行規範

---

## 📊 範例對比

| 範例 | 情境數 | 複雜度 | 執行時間 | 文檔數 | 適合新手 |
|------|--------|--------|---------|--------|---------|
| Greenfield 範例 | 1 | 中 | 3-4 小時 | 8+ | ✅ 是 |
| 多情境組合 | 3 | 高 | 4-6 小時 | 12+ | ⚠️ 需基礎 |

---

## 🎓 延伸學習

### 場景 SOP
- [Greenfield SDD 增強](../../scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md)
- [Brownfield SDD 增強](../../scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md)
- [Refactoring SDD 增強](../../scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md)
- [Documentation SDD 增強](../../scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md)

### 快速指令
- [Scenario Quick Reference](../quick-start/scenario-quick-reference.md)
- [Common Commands](../quick-start/common-commands.md)
- [各情境 Prompts](../scenario-prompts/)

### 框架原理
- [AISDLC_SDD_INIT.md](../../AISDLC_SDD_INIT.md)
- [SDD_Core_Principles.md](../../SDD_Core_Principles.md)
- [SDD_SPEC_FIRST_GATE.md](../../workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)

---

**版本**: v1.0-SDD
**範例數量**: 2 個核心範例
**最後更新**: 2026-04-16
**下一步**: 選擇一個範例開始你的 AISDLC-SDD 之旅！
