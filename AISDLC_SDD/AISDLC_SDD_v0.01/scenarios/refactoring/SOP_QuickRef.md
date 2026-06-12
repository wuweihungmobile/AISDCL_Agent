# Refactoring - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 程式碼重構、技術債務償還、架構改善

---

## 🎯 一頁總覽

### 適用場景
✅ 技術債務累積需要償還
✅ 程式碼可讀性差需改善
✅ 架構設計需要重新規劃
✅ 效能瓶頸需要結構性優化
✅ 🆕 **技術棧遷移**（前端/後端/DB 框架替換，如 Vue→React, Python→Java, Oracle→PostgreSQL）
✅ 🆕 **系統現代化**（含新平台擴展，如新增 Android/macOS 支援）

### 不適用場景
❌ 新功能開發（請用 Greenfield）
❌ Bug 修復 / 小功能修改（請用 Brownfield）
❌ 單純效能調優（請用 Performance）
⚠️ **技術棧遷移 + 大量新功能** → 建議組合使用 Refactoring + Greenfield SOP

### 📌 情境區分指引

| 你的需求 | 適用情境 | 說明 |
|---------|---------|------|
| 程式碼品質改善 / 降技術債 | **Refactoring** ✅ | 純代碼品質改善 |
| 部分技術棧替換（如只換前端框架） | **Refactoring** ✅ | 單層替換，結構性重構 |
| 全技術棧遷移（小團隊/Standard 安全） | **Refactoring** ✅ | 使用步驟 2.5 + 策略 F 分層漸進遷移 |
| 全技術棧遷移（高流量生產/Advanced 安全） | **Migration** ✅ | 需 L2 Contract Test + L3 Canary Deploy |
| 全技術棧遷移 + 代碼品質改善 | **Migration** 為主 + Refactoring 輔助 | 先用 Migration SOP 完成遷移，再用 Refactoring 改善品質 |
| 既有系統修 Bug / 加功能 | Brownfield | - |
| 重構 + 大量新功能開發 | **Refactoring** + Greenfield 組合 | - |

> **⚠️ Refactoring vs Migration 選擇指引**：
> - **Refactoring SOP**：技術棧不變、單層替換、或全棧遷移但安全需求為 Standard 等級
> - **Migration SOP**：全棧遷移且需要 Advanced CI/CD 安全（L2 Contract Test + L3 Canary Deploy + 自動回滾）
> - 本 SOP 的「技術棧遷移」章節（階段 2.5、4.2.1、策略 F）提供完整的分層漸進遷移流程
> - 選擇依據：團隊規模、生產環境風險等級、CI/CD 安全需求

---

## 📋 8 階段快速流程

```
總時間: 2-5 天

┌─────────────────────────────────────────────┐
│ 階段 1: 程式碼品質評估 (0.5-1 天) 🔴         │
│ └─ 靜態分析 → 技術債務識別 → 優先級排序      │
├─────────────────────────────────────────────┤
│ 階段 2: 重構目標定義 (0.5 天) 🔴             │
│ └─ 改善目標 → 範圍界定 → 成功標準           │
│     🆕 技術棧遷移時：效能基準線建立          │
├─────────────────────────────────────────────┤
│ 階段 3: 重構策略規劃 (0.5 天) 🔴             │
│ └─ 分階段計畫 → 風險評估 → Rollback Plan    │
├─────────────────────────────────────────────┤
│ 階段 4: 測試覆蓋補強 (0.5-1 天) 🟡           │
│ └─ 現有測試評估 → 補充測試 → 測試基準       │
├─────────────────────────────────────────────┤
│ 階段 5: 執行重構 (1-2 天) 🟡                 │
│ └─ 小步快跑 → 持續驗證 → 程式碼審查         │
├─────────────────────────────────────────────┤
│ 階段 6: 驗證與測試 (0.5 天) ✅               │
│ └─ 功能驗證 → 效能測試 → 品質檢查           │
├─────────────────────────────────────────────┤
│ 階段 7: 前後對比與成果展示 (0.5 天) ✅         │
│ └─ 品質對比 → ROI 計算 → 成果報告           │
├─────────────────────────────────────────────┤
│ 階段 8: 知識沉澱與文件更新 (0.5 天) ✅       │
│ └─ 經驗教訓 → 文檔更新 → 團隊知識庫         │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速啟動

### Step 1: 載入框架
```
提示詞:
「請載入 AISDLC (v0.01)，我需要進行程式碼重構」

或具體描述:
「現有系統架構混亂，需要重構訂單模組」
「程式碼技術債務嚴重，需要系統性改善」
「服務層邏輯複雜，需要拆分重構」
```

### Step 2: 提供程式碼資訊
```
必須提供:
□ 當前程式碼庫（或關鍵檔案）
□ 已知問題清單
□ 重構動機和目標

建議提供:
□ 靜態分析報告（SonarQube, ESLint）
□ 測試覆蓋率報告
□ 效能 Profiling 結果
□ 架構圖（if available）
```

---

## 🎯 重構類型快速決策

| 重構類型 | 適用場景 | 風險等級 | 時間估算 | 優先級 |
|---------|---------|---------|---------|--------|
| **Extract Method** | 函數過長 | 🟢 低 | 0.5-1天 | P1 |
| **Rename** | 命名不清 | 🟢 低 | 0.5天 | P2 |
| **Extract Class** | 類別過大 | 🟡 中 | 1-2天 | P1 |
| **Move Method** | 職責錯置 | 🟡 中 | 1-2天 | P1 |
| **Replace Conditional** | 複雜條件 | 🟡 中 | 1-2天 | P1 |
| **Split Module** | 模組耦合 | 🔴 高 | 2-3天 | P0 |
| **Refactor Architecture** | 架構問題 | 🔴 高 | 1-2週 | P0 |

---

## ⚡ 重構黃金法則

### 1. 先測試，再重構
```
❌ 錯誤: 直接修改程式碼
✅ 正確: 先補充測試 → 確保綠燈 → 重構 → 測試仍綠燈

原則: 測試是重構的安全網
```

### 2. 小步快跑 (Baby Steps)
```
❌ 錯誤: 一次重構整個模組
✅ 正確: 一次重構一個方法/類別 → 測試 → Commit

原則: 每個 commit 都應該是可部署的
```

### 3. 功能不變 (Preserve Behavior)
```
❌ 錯誤: 重構時順便加新功能
✅ 正確: 重構只改結構，不改功能

原則: 重構和功能開發分離
```

### 4. 持續整合 (Continuous Integration)
```
❌ 錯誤: 重構完才合併 (Branch 太久)
✅ 正確: 頻繁合併小改動

原則: 避免 Long-lived Branch
```

---

## 🔍 技術債務評估快速檢查

### Code Smells 速查表

| Code Smell | 症狀 | 重構手法 |
|-----------|------|---------|
| **Long Method** | 函數 > 30 行 | Extract Method |
| **Large Class** | 類別 > 300 行 | Extract Class |
| **Long Parameter List** | 參數 > 3 個 | Introduce Parameter Object |
| **Duplicated Code** | 重複邏輯 | Extract Method/Class |
| **God Object** | 類別職責過多 | Split Class |
| **Shotgun Surgery** | 改一處影響多處 | Move Method, Inline Class |
| **Feature Envy** | 過度依賴他類 | Move Method |
| **Primitive Obsession** | 濫用基本型別 | Introduce Value Object |

### 複雜度指標

```yaml
Cyclomatic Complexity (圈複雜度):
- 1-10: 🟢 簡單，低風險
- 11-20: 🟡 中度複雜，需注意
- 21-50: 🔴 高複雜，建議重構
- 50+: 🔴 極高風險，必須重構

Cognitive Complexity (認知複雜度):
- 0-5: 🟢 易理解
- 6-15: 🟡 需要思考
- 16+: 🔴 難以理解，建議重構

Code Coverage (測試覆蓋率):
- 80%+: 🟢 可安心重構
- 60-80%: 🟡 補充關鍵路徑測試
- < 60%: 🔴 先補測試再重構
```

---

## 🛠️ 重構策略選擇

### Strategy 1: Strangler Fig Pattern（推薦）

```yaml
適用: 大型遺留系統重構

步驟:
1. 在舊系統外建立新服務
2. 逐步遷移流量到新服務
3. 舊功能逐漸「被新服務包圍」
4. 最終移除舊系統

優點:
✅ 風險低（可隨時 Rollback）
✅ 可漸進式遷移
✅ 業務不中斷

範例:
舊 Monolith → 新 Microservices
- 先遷移非核心功能
- 核心功能最後遷移
- 雙寫確保資料一致
```

### Strategy 2: Branch by Abstraction

```yaml
適用: 核心模組替換

步驟:
1. 建立抽象層（Interface）
2. 舊實作實現 Interface
3. 新實作實現 Interface
4. 用 Feature Flag 切換
5. 驗證後移除舊實作

優點:
✅ 不需要 Long-lived Branch
✅ 可在 Production 測試
✅ 快速 Rollback

範例:
Database 從 MySQL 遷移到 PostgreSQL
- IDatabase interface
- MySQLDatabase (舊)
- PostgreSQLDatabase (新)
- Feature Flag 控制
```

### Strategy 3: Preparatory Refactoring

```yaml
適用: 為新功能做準備的重構

原則: 「先整地，再建房」

步驟:
1. 評估新功能需求
2. 重構現有程式碼使其易於擴展
3. 在乾淨的結構上新增功能

優點:
✅ 避免在爛 code 上堆疊
✅ 新功能開發更快
✅ 技術債不累積

範例:
新增優惠券功能前:
- 先重構訂單計價邏輯
- 使其支援折扣抽象
- 再實作優惠券
```

---

## ⚠️ 重構陷阱

### ❌ 避免這些錯誤

**1. Big Bang Refactoring**
```
錯誤: 一次重構整個系統

後果:
- 長時間無法部署
- 衝突難以解決
- 失敗風險極高

正確: 漸進式重構，小步快跑
```

**2. 沒有測試就重構**
```
錯誤: 測試覆蓋率低就開始重構

後果:
- 無法驗證功能正確性
- 引入 Bug 風險高
- 回歸問題難發現

正確: 先補測試，再重構
```

**3. 過度設計**
```
錯誤: 重構時追求完美設計

後果:
- 時間浪費
- 過度抽象
- YAGNI 違反

正確: 只重構到「足夠好」即可
```

**4. 忽略效能影響**
```
錯誤: 只關注結構，不測效能

後果:
- 重構後效能下降
- 生產問題

正確: 重構前後都要 Benchmark
```

---

## 📊 重構優先級矩陣

### 決策模型：影響 vs 努力

```
高影響 │ P0: 立即重構     │ P1: 排入計畫     │
       │ (核心模組問題)    │ (影響大但可控)    │
───────┼─────────────────┼─────────────────┤
低影響 │ P2: 有空再做     │ P3: 可以忽略     │
       │ (邊緣模組問題)    │ (Nice to have)   │
       └──────────────────┴─────────────────┘
         低努力             高努力
```

### P0 範例（立即重構）
```yaml
- 核心訂單計算邏輯混亂（影響營收）
- 支付模組測試覆蓋 < 20%（風險極高）
- 資料庫連接洩漏（效能問題）
- 安全漏洞（SQL Injection）
```

### P1 範例（計劃重構）
```yaml
- 使用者模組結構不清（可維護性）
- 搜尋功能效能可優化（體驗改善）
- API 回應格式不一致（開發體驗）
- 日誌系統需改善（Observability）
```

### P2 範例（有空再做）
```yaml
- 管理後台程式碼品質
- 測試腳本重複
- 文檔過時
- 變數命名不一致
```

---

## 🎯 重構成功指標

### 程式碼品質指標

```yaml
必須改善:
□ 圈複雜度下降 20%+
□ 測試覆蓋率提升到 80%+
□ Code Smells 減少 50%+
□ 技術債務時間減少 30%+

建議改善:
□ 平均函數行數 < 30
□ 平均類別行數 < 300
□ 重複程式碼 < 3%
□ 註解覆蓋率 > 20%
```

### 開發效率指標

```yaml
預期效果:
□ 新功能開發時間減少
□ Bug 修復時間減少
□ Code Review 速度加快
□ 新人上手時間縮短
```

### 系統穩定性指標

```yaml
重構後驗證:
□ 所有測試通過
□ 效能無下降（Benchmark）
□ 錯誤率未上升
□ 記憶體/CPU 使用無異常
```

---

## 🔄 重構執行檢查清單

### Pre-Refactoring Checklist

```yaml
準備工作:
□ 程式碼已納入版控
□ 建立 Feature Branch
□ 測試覆蓋率 >= 60%（核心路徑）
□ 靜態分析報告已產出
□ 效能基準已建立
□ 團隊已同步重構計畫

風險評估:
□ 識別高風險區域
□ 準備 Rollback Plan
□ 設定監控告警
□ 準備 Hotfix 流程
```

### During Refactoring Checklist

```yaml
執行規範:
□ 每個改動都有測試保護
□ 頻繁 Commit（每 30 分鐘）
□ Commit Message 清晰
□ 持續執行測試（綠燈）
□ 定期與團隊同步

品質把關:
□ Code Review（Pair Programming）
□ 靜態分析通過
□ 測試覆蓋率不下降
□ 效能測試通過
```

### Post-Refactoring Checklist

```yaml
驗證項目:
□ 所有測試通過（包含整合測試）
□ 效能無退化
□ 文檔已更新
□ Code Review 完成
□ 部署到 Staging 驗證
□ 監控指標正常

交付物:
□ 重構報告
□ Before/After 對比
□ 技術債務更新
□ 經驗教訓文檔
```

---

## 📚 重構手法快速參考

### 最常用的 15 種重構

```yaml
1. Extract Method - 提取函數
2. Inline Method - 內聯函數
3. Extract Variable - 提取變數
4. Rename - 重新命名
5. Move Method - 移動函數
6. Extract Class - 提取類別
7. Inline Class - 內聯類別
8. Replace Conditional with Polymorphism - 用多型替換條件
9. Introduce Parameter Object - 引入參數物件
10. Replace Magic Number with Constant - 用常數替換魔術數字
11. Decompose Conditional - 分解條件表達式
12. Consolidate Duplicate Conditional Fragments - 合併重複條件
13. Remove Dead Code - 移除死程式碼
14. Introduce Null Object - 引入空物件
15. Replace Type Code with State/Strategy - 用狀態/策略替換型別碼
```

詳細說明參考：Martin Fowler's Refactoring Catalog

---

## 🛠️ 可用 Skills 快速參考

### 核心 Skills（所有重構皆適用）
| Skill | 用途 | 觸發時機 |
|-------|------|---------|
| `/sa-analyst` | 需求重新分析、業務邏輯提取 | 階段 2（X-Large 時） |
| `/sd-architect` | 架構設計、重構策略 | 階段 2-3 |
| `/brownfield-analysis` | 既有系統分析 | 階段 1-2 |
| `/refactoring-code-quality` | 程式碼品質改善 | 階段 4-5 |
| `/testing-strategy` | 測試策略規劃 | 階段 4 |
| `/performance-optimization` | 效能基準線與優化 | 階段 2（基準線）、階段 6（驗證） |
| `/code-review` | 程式碼審查 | 階段 5-6 |

### 技術棧遷移額外 Skills
| Skill | 用途 | 觸發時機 |
|-------|------|---------|
| `/database-migration` | DB 平台遷移（如 Oracle→PostgreSQL） | 階段 4 |
| `/mobile-development` | 行動端/桌面端開發（Android/macOS） | 階段 5 |
| `/integration-database` | 新 DB 服務整合（ORM/連線池） | 階段 5 |
| `/devops-github-actions` | CI/CD Pipeline 重建 | 階段 5-6 |
| `/security-audit` | 遷移後安全審查 | 階段 6 |
| `/compliance-audit` | 合規審查（電商/支付/個資場景）| 全程 — 涉及支付處理(PCI-DSS)、個人資料(GDPR)時觸發 |

---

## 🔗 延伸閱讀

- 📘 [完整 SOP](./SOP.md)
- 📖 [Refactoring: Improving the Design of Existing Code](https://refactoring.com/)
- 🛠️ [程式碼分析模板](../../docs_template/scenario_specific/analysis/Legacy_System_Analysis_Template.md)
- 📊 [影響分析模板](../../docs_template/scenario_specific/analysis/Impact_Analysis_Template.md)

---

## 💡 快速決策：要不要重構？

### 決策流程

```
問題嚴重嗎？
├─ 是 → 影響核心功能？
│         ├─ 是 → 🔴 立即重構 (P0)
│         └─ 否 → 🟡 排入計畫 (P1)
└─ 否 → 有空閒時間？
          ├─ 是 → 🟢 Boy Scout Rule（隨手重構）
          └─ 否 → ⚪ 記錄技術債，之後處理
```

### Boy Scout Rule

「讓營地比你來的時候更乾淨」
- 修 Bug 時順手重構相關程式碼
- 加功能時先重構使其易擴展
- Code Review 時建議小重構

---

**提示**:
- 🎯 重構目標要明確（不是為了重構而重構）
- 🧪 測試是重構的信心來源
- 👥 團隊溝通很重要（避免衝突）
- 📊 量化改善效果（說服 Stakeholders）

---

**文檔版本: v0.01
**最後更新**: 2026-03-26
