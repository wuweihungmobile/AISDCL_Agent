# User Story Template
# 使用者故事模板

**文檔類型**: User Story Document
**模板版本**: v0.01
**適用情境**: 所有專案類型 (Greenfield, Brownfield, Sprint, Integration)
**建立日期**: 2025-11-13
**最後更新**: 2025-11-25

> ⚠️ **Edge Cases 處理重要提醒**:
> 撰寫 AC 前，請務必閱讀 [📐 AC 撰寫標準指引 (Edge Cases 處理方式)](#-ac-撰寫標準指引-edge-cases-處理方式)，選擇適合專案的 Edge Cases 處理方式（選項 A 或 B）。

---

## 📋 文檔資訊

| 項目 | 內容 |
|-----|------|
| **專案名稱** | [Project Name] |
| **Epic ID** | EPIC-XXX |
| **Epic 名稱** | [Epic 名稱] |
| **撰寫日期** | YYYY-MM-DD |
| **最後更新** | YYYY-MM-DD |
| **負責 Agent** | SA (Amanda), PM/PO (Victoria) |
| **狀態** | Draft / Under Review / Approved / In Development / Done |

> 📋 **ID 命名規範**: 使用 [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
> - **Epic ID**: EPIC-XXX (功能史詩)
> - **User Story ID**: US-XXX (使用者故事)
> - **Acceptance Criteria ID**: AC-XXX-Y (驗收條件)
> - 範例：EPIC-001 → US-001~US-005 → AC-001-1, AC-001-2

---

## 🎯 Epic 概述

### EPIC-XXX: [Epic 名稱]

**對應需求追蹤**：
- **Feature ID**: [F-XXX](PRD_Universal_Template.md#f-xxx) (PRD)
- **Business Rule**: [BR-XXX](../frd/FRD_Universal_Template.md#br-xxx) (FRD)
- **MVP 階段**: Phase 1 (MVP) / Phase 2 / Phase 3
- **RICE 分數**: [計算結果]
- **Kano 分類**: 必備型 / 期望型 / 魅力型

**Epic 描述**：
[簡要描述這個 Epic 的目標與範圍]

**Epic 目標**：
- 目標 1: [具體目標]
- 目標 2: [具體目標]
- 目標 3: [具體目標]

**包含的 User Stories**：
- [US-001](#us-001): [Story 簡述]
- [US-002](#us-002): [Story 簡述]
- [US-003](#us-003): [Story 簡述]

**預估工作量**：
- 總 Story Points: [總計]
- 預計時程: [X 週 / Y Sprints]

---

## 📖 User Stories

> 💡 **重要提醒**：撰寫 Acceptance Criteria 時，請先閱讀 [📐 AC 撰寫標準指引 (Edge Cases 處理方式)](#-ac-撰寫標準指引-edge-cases-處理方式)，了解如何正確處理 Edge Cases。

### US-001: [User Story 標題]

**基本資訊**：
- **User Story ID**: US-001
- **對應 Epic**: [EPIC-XXX](#epic-xxx)
- **對應 Feature**: [F-XXX](PRD_Universal_Template.md#f-xxx)
- **對應 Business Rule**: [BR-XXX](../frd/FRD_Universal_Template.md#br-xxx)
- **優先級**: P0 (Must-have) / P1 (Should-have) / P2 (Nice-to-have)
- **Story Points**: [1/2/3/5/8/13/21]
- **Sprint**: Sprint XX
- **狀態**: Backlog / In Progress / Done / Blocked

**Story 描述** (使用者故事格式)：

```
作為一個 [使用者角色]
我想要 [功能/目標]
以便於 [商業價值/原因]
```

**範例 (MoneyTracker)**：
```
作為一個 MoneyTracker 使用者
我想要 快速記錄一筆支出
以便於 即時掌握我的花費情況，不需要事後回想
```

---

#### Acceptance Criteria (驗收條件)

> 📋 **AC ID 格式**: AC-XXX-Y (XXX 為 User Story 編號，Y 為 AC 序號)

> 💡 **Edge Cases 處理指引**:
> - **必讀**: 請先閱讀 [📐 AC 撰寫標準指引 (Edge Cases 處理方式)](#-ac-撰寫標準指引-edge-cases-處理方式)
> - **選項 A**: Edge Cases 整合到 AC 中（適合小型專案）
> - **選項 B**: Edge Cases 獨立區塊管理（適合大型專案）
> - 專案啟動時必須決定使用哪種方式，並在整個專案中統一使用

##### AC-001-1: [驗收條件標題]

**條件描述**：
Given [前提條件]
When [操作行為]
Then [預期結果]

**範例 (MoneyTracker)**：
```gherkin
Given 我已登入 MoneyTracker App
When 我輸入金額 250、選擇分類「食物」、備註「午餐」
Then 系統應該成功儲存這筆記錄，並顯示「記帳成功」訊息
```

**測試要點**：
- [ ] 可輸入金額 (正整數或小數點後兩位)
- [ ] 可選擇分類 (從預設分類清單)
- [ ] 可新增備註 (選填，最多 200 字)
- [ ] 儲存後立即顯示在支出總覽中

**對應測試案例**: [TC-001-1-1](../tests/TestCase_Module.md#tc-001-1-1)

---

##### AC-001-2: [驗收條件標題]

**條件描述**：
Given [前提條件]
When [操作行為]
Then [預期結果]

**範例 (MoneyTracker - 資料驗證)**：
```gherkin
Given 我已登入 MoneyTracker App
When 我輸入金額 0 或負數
Then 系統應該顯示錯誤訊息「金額必須大於 0」，且不儲存記錄
```

**測試要點**：
- [ ] 金額 = 0 時顯示錯誤
- [ ] 金額 < 0 時顯示錯誤
- [ ] 金額 > 999,999 時顯示錯誤 (超過上限)
- [ ] 未選擇分類時顯示錯誤

**對應測試案例**: [TC-001-1-2](../tests/TestCase_Module.md#tc-001-1-2)

---

##### AC-001-3: [驗收條件標題]

*依照上方格式繼續填寫其他 Acceptance Criteria*

---

#### 技術實作參考

**對應 API**:
- [API-101: POST /api/transactions](../api/API_Specification_Template.md#api-101) - 建立記帳記錄

**對應資料模型**:
- Transaction (交易記錄表)
  - id: UUID
  - amount: Decimal(10,2)
  - category_id: FK → Category
  - note: String(200)
  - created_at: Timestamp

**前端元件**:
- `ExpenseForm.tsx` - 記帳表單元件
- `CategoryPicker.tsx` - 分類選擇器
- `ExpenseSuccessModal.tsx` - 成功提示

**後端邏輯**:
- `TransactionService.create()` - 建立記錄
- `TransactionValidator.validate()` - 驗證輸入

---

#### 估算與規劃

> 📋 **參考工具**: [Estimation_Standards.md](../../../guides/system/planning/Estimation_Standards.md)

**Story Points 估算**: 5 SP

**估算依據**：
- **複雜度**: 中等 (×1.0) - 簡單 CRUD，但需前端表單驗證
- **學習曲線**: 初次使用 (×1.5) - React Native 首次開發
- **風險**: 低 (×1.0) - 需求明確，技術成熟

**調整後 Story Points**: 5 × 1.0 × 1.5 × 1.0 = **7.5 ≈ 8 SP**

**預估時間**：
- 前端開發: 0.5 天 (4 小時)
- 後端開發: 0.5 天 (4 小時)
- 整合測試: 0.25 天 (2 小時)
- **總計**: 1.25 天

**開發分工**：
- **前端開發者 A**: 實作 `ExpenseForm.tsx`, `CategoryPicker.tsx`
- **後端開發者 B**: 實作 `TransactionService`, API-101
- **QA (Quincy)**: 撰寫測試案例 TC-001-1-1 ~ TC-001-1-3

---

#### 依賴與阻礙

**依賴項目**：
- [ ] Category 資料模型已建立 (BR-002)
- [ ] User 認證機制已完成 (US-000)
- [ ] 資料庫 Schema 已部署

**潛在阻礙**：
- ⚠️ React Native 表單驗證需學習
- ⚠️ 分類選擇器 UI 設計待確認

**風險應對**：
- 使用 Formik + Yup 簡化表單驗證
- 提前與 Designer 確認 UI 設計

---

#### 定義完成 (Definition of Done)

- [ ] 程式碼已撰寫並通過 Code Review
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 所有 Acceptance Criteria 已通過測試
- [ ] API 文檔已更新 (API-101)
- [ ] 前端元件已加入 Storybook
- [ ] 整合測試已通過
- [ ] 無 P0/P1 Bug
- [ ] 已部署至 Staging 環境並驗證
- [ ] Product Owner 已確認驗收

---

### US-002: [User Story 標題]

*依照 US-001 格式繼續填寫其他 User Stories*

---

## 📊 Epic 追蹤與進度

### Story Points 統計

| User Story ID | 故事名稱 | Story Points | 狀態 | 負責人 | Sprint |
|--------------|---------|-------------|------|--------|--------|
| US-001 | [故事名稱] | 8 | In Progress | Dev A | Sprint 1 |
| US-002 | [故事名稱] | 5 | Backlog | Dev B | Sprint 1 |
| US-003 | [故事名稱] | 3 | Backlog | Dev A | Sprint 2 |
| US-004 | [故事名稱] | 8 | Backlog | Dev B | Sprint 2 |
| US-005 | [故事名稱] | 5 | Backlog | Dev A | Sprint 2 |
| **總計** | - | **29 SP** | - | - | - |

### Burndown Chart

```
Story Points
   30 ┤
      │
   25 ┤     ●
      │    /
   20 ┤   /
      │  /  ●
   15 ┤ /  /
      │/  /
   10 ┤  /    ●
      │ /    /
    5 ┤/    /     ●
      │    /     /
    0 ┤───────────────────────
      Sprint 1  Sprint 2
        (實際)   (計畫)
```

---

## 🔗 完整追蹤鏈範例 (MoneyTracker)

```
F-001 (快速記帳功能 - PRD)
  └─ BR-001 (金額必須 > 0 - FRD)
  └─ BR-002 (分類必須選擇 - FRD)
      └─ EPIC-001 (記帳管理 - Epic)
          └─ US-001 (快速記錄一筆支出 - User Story)
              ├─ AC-001-1 (可輸入金額、分類、備註)
              ├─ AC-001-2 (資料驗證)
              ├─ AC-001-3 (儲存成功提示)
              └─ AC-001-4 (顯示在支出總覽)
                  └─ API-101 (POST /api/transactions - API Spec)
                      └─ TC-001-1-1 (正常記帳測試 - Test Case)
                      └─ TC-001-1-2 (資料驗證測試 - Test Case)
                      └─ TC-001-1-3 (錯誤處理測試 - Test Case)
```

---

## 🔄 變更記錄 (Change Log)

| 版本 | 日期 | 修改人 | 修改內容 | 變更原因 |
|-----|------|--------|---------|---------|
| v1.0 | YYYY-MM-DD | SA (Amanda) | 初版建立 | Epic 啟動 |
| v1.1 | YYYY-MM-DD | PM (Victoria) | 調整 US-002 Story Points | 重新估算 |
| v1.2 | YYYY-MM-DD | SA (Amanda) | 新增 US-005 | 需求變更 |

---

## ✅ 驗證檢查清單 (Validation Checklist)

完成 User Story 撰寫後，使用此檢查清單驗證：

- [ ] **Epic ID 已定義**: EPIC-XXX 格式
- [ ] **所有 User Story 已定義 ID**: US-XXX 格式
- [ ] **所有 AC 已定義 ID**: AC-XXX-Y 格式
- [ ] **每個 US 都有明確的使用者價值**: "以便於..." 部分清楚
- [ ] **每個 AC 都使用 Given-When-Then 格式**
- [ ] **Story Points 已估算**: 使用 Planning Poker 或參考基準
- [ ] **依賴項目已識別**: 明確列出阻礙
- [ ] **Definition of Done 已定義**: 檢查清單完整
- [ ] **追蹤鏈完整**: F-XXX → BR-XXX → EPIC-XXX → US-XXX → AC-XXX-Y → API-XXX
- [ ] **對應 API 已參照**: 連結到 API Specification
- [ ] **對應測試案例已參照**: 連結到 Test Case

---

## 📚 參考文檔

- **AISDLC ID Naming Convention**: [guides/system/naming/AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
- **Estimation Standards**: [guides/system/planning/Estimation_Standards.md](../../../guides/system/planning/Estimation_Standards.md)
- **MVP Definition Template**: [docs_template/prd/MVP_Definition_Template.md](MVP_Definition_Template.md)
- **PRD Template**: [docs_template/core/prd/PRD_Universal_Template.md](PRD_Universal_Template.md)
- **FRD Template**: [docs_template/core/frd/FRD_Universal_Template.md](../frd/FRD_Universal_Template.md)
- **API Specification Template**: [docs_template/core/api/API_Specification_Template.md](../api/API_Specification_Template.md)

---

## 💡 撰寫提示 (Writing Tips)

### 好的 User Story 範例 ✅

```
作為一個 MoneyTracker 使用者
我想要 快速記錄一筆支出
以便於 即時掌握我的花費情況，不需要事後回想
```

**優點**：
- 清楚的使用者角色
- 具體的功能需求
- 明確的商業價值

### 不好的 User Story 範例 ❌

```
作為一個使用者
我想要 一個記帳功能
以便於 記帳
```

**缺點**：
- 使用者角色太模糊
- 功能需求不具體
- 沒有說明為什麼需要這個功能

---

### 好的 Acceptance Criteria 範例 ✅

```gherkin
Given 我已登入 MoneyTracker App
When 我輸入金額 250、選擇分類「食物」、備註「午餐」
Then 系統應該成功儲存這筆記錄，並顯示「記帳成功」訊息
```

**優點**：
- 使用 Given-When-Then 格式
- 條件、操作、預期結果都清楚
- 可直接轉換為測試案例

### 不好的 Acceptance Criteria 範例 ❌

```
使用者可以記帳
```

**缺點**：
- 太模糊，無法測試
- 沒有明確的操作步驟
- 沒有預期結果

---

## 📐 AC 撰寫標準指引 (Edge Cases 處理方式)

### 問題說明

在撰寫 Acceptance Criteria 時，常常會遇到 Edge Cases（邊界情況）處理的問題：
- Edge Cases 應該獨立列出，還是整合到 AC 中？
- 如何確保 Edge Cases 不會被遺漏測試？
- AC 編號如何保持連續性？

### 🚀 快速決策：選擇 A 還是 B？

```
開始
  │
  ├─ 專案規模 > 200 個 User Stories？
  │    ├─ 是 → 選項 B（獨立 Edge Cases 管理）
  │    └─ 否 ↓
  │
  ├─ 每個 US 平均有 > 5 個 Edge Cases？
  │    ├─ 是 → 選項 B
  │    └─ 否 ↓
  │
  ├─ 團隊經驗豐富，需要精細管理？
  │    ├─ 是 → 選項 B
  │    └─ 否 → 選項 A（整合到 AC 中）

**預設建議**: 小型專案優先使用選項 A，大型專案考慮選項 B
```

### 📊 Edge Cases 常見分類

無論選擇哪種方式，建議按以下類別檢查 Edge Cases：

| 分類 | 說明 | 範例 |
|------|-----|------|
| **邊界值測試** | 數值的最小值、最大值、零、負數 | 金額 = 0, -100, 1000000 |
| **輸入格式** | 小數、特殊字元、空白、超長字串 | 金額 = 250.50, 備註 = 200 字元 |
| **狀態條件** | 未登入、網路斷線、權限不足 | 未登入時新增記錄 |
| **資料完整性** | 必填欄位空白、重複資料 | 分類名稱重複 |
| **時間相關** | 未來日期、過去日期、時區差異 | 日期 = 2099-12-31 |
| **並發操作** | 同時編輯、雙重提交 | 短時間內連續點擊儲存 |

### 解決方案：兩種撰寫方式

---

#### 選項 A: Edge Cases 整合到 AC 中（建議用於小型專案）

**範例**：

```markdown
### US-001: 使用者可以新增收入記錄

#### Acceptance Criteria:

##### AC-001-1: 基本新增流程 (Happy Path)
Given 我已登入 MoneyTracker App
When 我輸入金額 250、選擇分類「薪資」、備註「月薪」
Then 系統應該成功儲存這筆記錄，並顯示「記帳成功」訊息

##### AC-001-2: 必填欄位驗證
Given 我已登入 MoneyTracker App
When 我未填寫金額或未選擇分類
Then 系統應該顯示錯誤訊息「請填寫必填欄位」，且不儲存記錄

##### AC-001-3: 成功新增確認
Given 我已登入 MoneyTracker App
When 我成功新增一筆記錄
Then 系統應該顯示「記帳成功」訊息，並自動返回交易列表

##### AC-001-4: 預設值處理
Given 我已登入 MoneyTracker App
When 我新增記錄時未填寫日期
Then 系統應該自動使用今天的日期

##### AC-001-5: 小數金額處理（Edge Case）
Given 我已登入 MoneyTracker App
When 我輸入金額 250.50（小數點後兩位）
Then 系統應該正確儲存並顯示 250.50

##### AC-001-6: 負數金額錯誤處理（Edge Case）
Given 我已登入 MoneyTracker App
When 我輸入金額 -100（負數）
Then 系統應該顯示錯誤訊息「金額必須大於 0」，且不儲存記錄

##### AC-001-7: 超大金額處理（Edge Case）
Given 我已登入 MoneyTracker App
When 我輸入金額 > 1,000,000
Then 系統應該顯示警告訊息「金額過大，請確認」，但允許儲存
```

**優點**：
- ✅ AC 編號連續（AC-001-1 ~ AC-001-7）
- ✅ 測試覆蓋率清楚（所有情況都在 AC 中）
- ✅ 不會遺漏 Edge Cases（都有 AC ID 對應測試案例）
- ✅ 簡單直觀，適合小型專案

**缺點**：
- ❌ AC 數量較多
- ❌ 核心 AC 與 Edge Cases 混在一起

**適用情境**：
- 小型專案（< 50 個 User Stories）
- 需求簡單明確
- 團隊經驗較少，需要明確指引

---

#### 選項 B: Edge Cases 獨立區塊但納入測試（建議用於大型專案）

**範例**：

```markdown
### US-001: 使用者可以新增收入記錄

#### Acceptance Criteria:

##### AC-001-1: 基本新增流程
Given 我已登入 MoneyTracker App
When 我輸入金額 250、選擇分類「薪資」、備註「月薪」
Then 系統應該成功儲存這筆記錄，並顯示「記帳成功」訊息

##### AC-001-2: 必填欄位驗證
Given 我已登入 MoneyTracker App
When 我未填寫金額或未選擇分類
Then 系統應該顯示錯誤訊息「請填寫必填欄位」，且不儲存記錄

##### AC-001-3: 成功新增確認
Given 我已登入 MoneyTracker App
When 我成功新增一筆記錄
Then 系統應該顯示「記帳成功」訊息，並自動返回交易列表

---

#### Edge Cases（必須測試）:

> 📋 **EC ID 格式**: EC-XXX-Y (XXX 為 User Story 編號，Y 為 EC 序號)

##### EC-001-1: 小數金額處理
Given 我已登入 MoneyTracker App
When 我輸入金額 250.50（小數點後兩位）
Then 系統應該正確儲存並顯示 250.50

**測試案例**: TC-001-EC1-1

##### EC-001-2: 負數金額錯誤處理
Given 我已登入 MoneyTracker App
When 我輸入金額 -100（負數）
Then 系統應該顯示錯誤訊息「金額必須大於 0」，且不儲存記錄

**測試案例**: TC-001-EC2-1

##### EC-001-3: 超大金額處理
Given 我已登入 MoneyTracker App
When 我輸入金額 > 1,000,000
Then 系統應該顯示警告訊息「金額過大,請確認」，但允許儲存

**測試案例**: TC-001-EC3-1

##### EC-001-4: 零金額處理
Given 我已登入 MoneyTracker App
When 我輸入金額 0
Then 系統應該顯示錯誤訊息「金額必須大於 0」，且不儲存記錄

**測試案例**: TC-001-EC4-1
```

**優點**：
- ✅ 核心 AC 簡潔易讀（只有 3 個核心 AC）
- ✅ Edge Cases 易於識別（獨立區塊）
- ✅ 結構清晰，適合大型專案
- ✅ Edge Cases 有獨立的 EC ID，便於追蹤

**缺點**：
- ❌ 需要額外的 EC ID 管理
- ❌ 需要團隊共識（何時用 AC，何時用 EC）

**適用情境**：
- 大型專案（> 50 個 User Stories）
- 需求複雜，Edge Cases 較多
- 團隊經驗豐富，需要結構化管理
- 需要明確區分核心功能與邊界情況

---

### 建議選擇標準

| 專案特性 | 建議選項 | 理由 |
|---------|---------|------|
| **小型專案** (< 50 US) | **選項 A** | 簡單直觀，不需要額外管理 EC ID |
| **中型專案** (50-200 US) | **選項 A** 或 **選項 B** | 依團隊偏好選擇 |
| **大型專案** (> 200 US) | **選項 B** | 結構清晰，便於管理 |
| **Edge Cases 少** (< 5 個/US) | **選項 A** | 整合到 AC 中更簡單 |
| **Edge Cases 多** (> 5 個/US) | **選項 B** | 獨立管理更清晰 |
| **團隊經驗少** | **選項 A** | 減少概念負擔 |
| **團隊經驗豐富** | **選項 B** | 更精確的管理 |

---

### 測試覆蓋率確保

**無論選擇哪種方式，都必須確保**：

1. **所有 Edge Cases 都有對應的測試案例**
   - 選項 A: AC-001-5 → TC-001-5-1
   - 選項 B: EC-001-1 → TC-001-EC1-1

2. **測試案例追蹤表完整**
   ```markdown
   | User Story | AC/EC ID | 測試案例 | 狀態 |
   |-----------|----------|---------|------|
   | US-001 | AC-001-1 | TC-001-1-1 | ✅ Pass |
   | US-001 | AC-001-5 (Edge) | TC-001-5-1 | ✅ Pass |
   | US-001 | EC-001-1 | TC-001-EC1-1 | ✅ Pass |
   ```

3. **Definition of Done 包含 Edge Cases 測試**
   - [ ] 所有 Acceptance Criteria 已通過測試
   - [ ] 所有 Edge Cases 已通過測試
   - [ ] 測試覆蓋率 ≥ 80%

---

### MoneyTracker 實際範例對比

#### 選項 A 範例（小型專案）

```markdown
US-001: 使用者可以新增收入記錄
├─ AC-001-1: 基本新增流程
├─ AC-001-2: 必填欄位驗證
├─ AC-001-3: 成功新增確認
├─ AC-001-4: 預設值處理
├─ AC-001-5: 小數金額處理（Edge）
├─ AC-001-6: 負數金額錯誤處理（Edge）
└─ AC-001-7: 超大金額處理（Edge）

測試案例: TC-001-1-1 ~ TC-001-7-1 (共 7 個)
```

#### 選項 B 範例（大型專案）

```markdown
US-001: 使用者可以新增收入記錄

Acceptance Criteria:
├─ AC-001-1: 基本新增流程
├─ AC-001-2: 必填欄位驗證
└─ AC-001-3: 成功新增確認

Edge Cases:
├─ EC-001-1: 小數金額處理
├─ EC-001-2: 負數金額錯誤處理
├─ EC-001-3: 超大金額處理
└─ EC-001-4: 零金額處理

測試案例:
├─ TC-001-1-1 ~ TC-001-3-1 (AC 測試)
└─ TC-001-EC1-1 ~ TC-001-EC4-1 (Edge Cases 測試)
```

---

### 實施建議

1. **在專案啟動時決定使用哪種方式**
   - 在 AISDLC 階段 6（User Story 設計）開始前確定
   - 記錄在專案的 [Project README](../../../Project_README.md) 中

2. **全專案統一使用同一種方式**
   - 避免混用造成混淆

3. **在 Definition of Done 中明確要求**
   - 確保所有 AC 和 Edge Cases 都有測試

4. **使用 Code Review 確保一致性**
   - 檢查 AC ID 格式是否正確
   - 檢查 Edge Cases 是否有對應測試案例

---

**參考文件**:
- [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md) - ID 命名規範
- [Estimation_Standards.md](../../../guides/system/planning/Estimation_Standards.md) - 估算標準
- [Greenfield SOP.md](../../../scenarios/greenfield/SOP.md) - 階段 6 步驟 6.2

---

**文檔結束 (End of Document)**
