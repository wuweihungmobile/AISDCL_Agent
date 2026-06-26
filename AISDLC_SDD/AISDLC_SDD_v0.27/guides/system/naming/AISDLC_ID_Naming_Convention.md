# AISDLC 統一 ID 命名規範
# AISDLC Unified ID Naming Convention

**文檔版本**: v1.0
**建立日期**: 2025-11-12
**適用範圍**: AISDLC Framework 所有情境
**AISDLC 版本**: v0.01

---

## 📋 文檔目的

本文檔定義 **AISDLC Framework 統一的 ID 命名規範**，確保所有文檔中的 ID 格式一致，便於追蹤和管理。

### 為什麼需要統一 ID？

1. **可追蹤性**: 從需求到測試的完整追蹤鏈
2. **一致性**: 所有文檔使用相同的 ID 格式
3. **易於溝通**: 團隊成員使用統一的 ID 參考需求
4. **自動化**: 便於工具自動產生追蹤矩陣

---

## 🎯 ID 命名規範總覽

### 統一 ID 命名規範表格

| ID 類型 | 格式 | 範例 | 使用階段 | 文檔 | 說明 |
|---------|------|------|---------|------|------|
| **Feature ID** | F-XXX | F-001, F-002 | 階段 2 | FRD | 功能需求編號 |
| **Non-Functional Requirement ID** | NFR-XXX | NFR-001 | 階段 2 | FRD | 非功能需求編號 |
| **User Role ID** | UR-XXX | UR-001 | 階段 2 | FRD | 使用者角色編號 |
| **Business Rule ID** | BR-XXX | BR-001 | 階段 2 | FRD | 業務規則編號 |
| **Epic ID** | EPIC-XXX | EPIC-001 | 階段 6 | User Story | Epic 編號（大功能群組） |
| **User Story ID** | US-XXX | US-001 | 階段 6 | User Story | User Story 編號 |
| **Acceptance Criteria ID** | AC-XXX-Y | AC-001-1 | 階段 6 | User Story | AC 編號（XXX=US, Y=序號） |
| **API ID** | API-XXX | API-001 | 階段 5 | API Spec | API 端點編號 |
| **Test Case ID** | TC-XXX-Y-Z | TC-001-1-1 | 階段 8 | Test Plan | 測試案例編號 |
| **Bug ID** | BUG-XXX | BUG-001 | 階段 9 | Bug Report | Bug 編號 |

---

## 📖 詳細規範說明

### 1. Feature ID (F-XXX)

**格式**: `F-XXX`

**說明**: 功能需求的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依序編號，不跳號
- 刪除功能時保留 ID，標記為 [Deprecated]

**範例**:
- `F-001`: 新增收入記錄
- `F-002`: 新增支出記錄
- `F-003`: 查看收支統計
- `F-004`: 分類管理
- `F-005`: 匯出報表

**使用階段**: 階段 2 - 需求提取
**使用文檔**: FRD (Functional Requirements Document)

---

### 2. Non-Functional Requirement ID (NFR-XXX)

**格式**: `NFR-XXX`

**說明**: 非功能需求的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依類別分組編號（可選）
  - NFR-001~099: 效能需求
  - NFR-100~199: 安全需求
  - NFR-200~299: 可用性需求

**範例**:
- `NFR-001`: App 啟動時間 < 2 秒
- `NFR-002`: 資料載入時間 < 1 秒
- `NFR-101`: 本地資料加密
- `NFR-201`: 支援 VoiceOver（無障礙）

**使用階段**: 階段 2 - 需求提取
**使用文檔**: FRD

---

### 3. User Role ID (UR-XXX)

**格式**: `UR-XXX`

**說明**: 使用者角色的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依角色重要性排序

**範例**:
- `UR-001`: 一般使用者
- `UR-002`: 管理員
- `UR-003`: 訪客

**使用階段**: 階段 2 - 需求提取
**使用文檔**: FRD

---

### 4. Business Rule ID (BR-XXX)

**格式**: `BR-XXX`

**說明**: 業務規則的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 可依功能分組（與 Feature ID 對應）

**範例**:
- `BR-001`: 金額必須大於 0
- `BR-002`: 日期不可為未來日期
- `BR-003`: 分類名稱不可重複
- `BR-004`: 每筆交易必須指定分類

**使用階段**: 階段 2 - 需求提取
**使用文檔**: FRD

---

### 5. Epic ID (EPIC-XXX)

**格式**: `EPIC-XXX`

**說明**: Epic（大功能群組）的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 一個 Epic 包含多個 User Story

**範例**:
- `EPIC-001`: 交易管理
- `EPIC-002`: 報表與統計
- `EPIC-003`: 分類管理
- `EPIC-004`: 設定與偏好

**使用階段**: 階段 6 - User Story 設計
**使用文檔**: User Story Document

**關聯關係**:
```
EPIC-001 (交易管理)
  ├─ US-001: 使用者可以新增收入記錄
  ├─ US-002: 使用者可以新增支出記錄
  ├─ US-003: 使用者可以編輯交易記錄
  └─ US-004: 使用者可以刪除交易記錄
```

---

### 6. User Story ID (US-XXX)

**格式**: `US-XXX`

**說明**: User Story 的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依優先級排序（P0 → P1 → P2）
- 可分組編號（與 Epic 對應）

**範例**:
- `US-001`: 使用者可以新增收入記錄
- `US-002`: 使用者可以新增支出記錄
- `US-003`: 使用者可以編輯交易記錄

**使用階段**: 階段 6 - User Story 設計
**使用文檔**: User Story Document

---

### 7. Acceptance Criteria ID (AC-XXX-Y)

**格式**: `AC-XXX-Y`

**說明**: Acceptance Criteria 的唯一識別碼

**編號規則**:
- XXX: 對應的 User Story ID（去掉 US- 前綴）
- Y: AC 序號（1, 2, 3...）

**範例** (對應 US-001):
- `AC-001-1`: 使用者點擊「新增」按鈕後，顯示新增表單
- `AC-001-2`: 必填欄位（金額、日期）未填寫時，顯示錯誤訊息
- `AC-001-3`: 成功新增後，顯示確認訊息並返回列表頁
- `AC-001-4`: 新增的記錄立即出現在交易列表中

**使用階段**: 階段 6 - User Story 設計
**使用文檔**: User Story Document

---

### 8. API ID (API-XXX)

**格式**: `API-XXX`

**說明**: API 端點的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依 API 類型分組（可選）
  - API-001~099: 認證相關
  - API-100~199: 交易相關
  - API-200~299: 報表相關

**範例**:
- `API-001`: POST /api/auth/login - 使用者登入
- `API-002`: POST /api/auth/logout - 使用者登出
- `API-101`: POST /api/transactions - 新增交易
- `API-102`: GET /api/transactions - 查詢交易列表
- `API-103`: PUT /api/transactions/:id - 更新交易
- `API-104`: DELETE /api/transactions/:id - 刪除交易

**使用階段**: 階段 5 - 系統設計
**使用文檔**: API Specification

---

### 9. Test Case ID (TC-XXX-Y-Z)

**格式**: `TC-XXX-Y-Z`

**說明**: 測試案例的唯一識別碼

**編號規則**:
- XXX: 對應的 User Story ID（去掉 US- 前綴）
- Y: 對應的 AC 序號
- Z: 測試案例序號（同一個 AC 可能有多個測試案例）

**範例** (對應 US-001, AC-001-1):
- `TC-001-1-1`: 測試新增按鈕點擊（正常情況）
- `TC-001-1-2`: 測試新增按鈕點擊（無網路情況）

**範例** (對應 US-001, AC-001-2):
- `TC-001-2-1`: 測試必填欄位驗證（金額為空）
- `TC-001-2-2`: 測試必填欄位驗證（日期為空）
- `TC-001-2-3`: 測試必填欄位驗證（金額為負數）

**使用階段**: 階段 8 - 測試計畫
**使用文檔**: Test Plan / Test Case Document

---

### 10. Bug ID (BUG-XXX)

**格式**: `BUG-XXX`

**說明**: Bug 的唯一識別碼

**編號規則**:
- 使用 3 位數字（001-999）
- 依發現時間順序編號

**範例**:
- `BUG-001`: 新增交易時，負數金額未被阻擋
- `BUG-002`: 統計圖表在沒有資料時顯示錯誤
- `BUG-003`: 刪除分類後，相關交易未更新

**使用階段**: 階段 9 - 測試與修復
**使用文檔**: Bug Report

---

## 🔗 ID 追蹤關係

### 完整追蹤鏈範例

```
Business Need: 使用者需要管理個人財務

    ↓ (階段 2)

F-001: 新增收入記錄
BR-001: 金額必須大於 0
NFR-001: 操作回應時間 < 300ms

    ↓ (階段 6)

EPIC-001: 交易管理
    └─ US-001: 使用者可以新增收入記錄
        ├─ AC-001-1: 點擊新增按鈕顯示表單
        ├─ AC-001-2: 必填欄位驗證
        ├─ AC-001-3: 成功新增確認
        └─ AC-001-4: 記錄出現在列表

    ↓ (階段 5，若有 Backend)

API-101: POST /api/transactions

    ↓ (階段 8)

TC-001-1-1: 測試新增按鈕點擊
TC-001-2-1: 測試必填欄位驗證（金額為空）
TC-001-2-2: 測試必填欄位驗證（日期為空）
TC-001-3-1: 測試成功新增確認訊息
TC-001-4-1: 測試記錄出現在列表

    ↓ (階段 9，若有問題)

BUG-001: 負數金額未被阻擋
```

---

## 📊 ID 追蹤矩陣範例

### 需求追蹤矩陣 (Requirement Traceability Matrix)

| Feature ID | Business Rule | Epic | User Story | AC | API | Test Case | 狀態 |
|-----------|---------------|------|------------|-------|-----|-----------|------|
| F-001 | BR-001, BR-002 | EPIC-001 | US-001 | AC-001-1~4 | API-101 | TC-001-1-1~4-1 | ✅ 完成 |
| F-002 | BR-001, BR-002 | EPIC-001 | US-002 | AC-002-1~4 | API-101 | TC-002-1-1~4-1 | ⏳ 進行中 |
| F-003 | BR-003 | EPIC-002 | US-010 | AC-010-1~3 | API-201 | TC-010-1-1~3-1 | ⚪ 未開始 |

---

## 📝 ID 編號最佳實踐

### 編號原則

1. **依序編號，不跳號**
   - ✅ 正確：F-001, F-002, F-003
   - ❌ 錯誤：F-001, F-003, F-005

2. **刪除時保留 ID，標記為 Deprecated**
   - 範例：`F-002: [Deprecated] 舊功能`
   - 原因：避免 ID 重複使用造成混淆

3. **使用前導零**
   - ✅ 正確：F-001, F-002, F-010
   - ❌ 錯誤：F-1, F-2, F-10
   - 原因：便於排序和對齊

4. **ID 與名稱分離**
   - ✅ 正確：`F-001`: 新增收入記錄
   - ❌ 錯誤：F-新增收入記錄

---

### 分組建議

**小型專案** (< 50 個功能):
- 不需要分組，依序編號即可

**中型專案** (50-200 個功能):
- 可依模組分組
  - F-001~099: 交易管理
  - F-100~199: 報表統計
  - F-200~299: 設定管理

**大型專案** (> 200 個功能):
- 建議使用兩層編號
  - 範例：`F-TXN-001` (交易模組 001)
  - 範例：`F-RPT-001` (報表模組 001)

---

## 🔄 ID 版本管理

### 需求變更時的 ID 處理

#### 情況 1: 需求刪除
- 保留 ID，標記為 `[Deprecated]`
- 範例：`F-005: [Deprecated] 舊的匯出功能`

#### 情況 2: 需求合併
- 保留主要 ID，其他 ID 標記為 `[Merged into F-XXX]`
- 範例：
  - `F-003`: 查看收支統計（保留）
  - `F-004`: `[Merged into F-003]` 查看支出統計

#### 情況 3: 需求拆分
- 原 ID 保留，新增子 ID
- 範例：
  - `F-003`: 查看收支統計（父需求）
  - `F-003-A`: 查看收入統計（子需求）
  - `F-003-B`: 查看支出統計（子需求）

---

## 🛠️ 工具支援

### 建議工具

| 工具 | 用途 | ID 管理功能 |
|-----|------|------------|
| **Jira** | 專案管理 | 自動產生 Issue ID |
| **Linear** | 專案管理 | 自動產生 Issue ID |
| **Notion** | 文檔管理 | 手動管理 ID，可建立資料庫 |
| **Excel / Google Sheets** | 追蹤矩陣 | 手動管理，適合小型專案 |
| **Git** | 版本控制 | Commit 訊息引用 ID |

### Git Commit 訊息範例

```
feat(F-001): 實作新增收入記錄功能

- 實作 UI 表單
- 實作資料驗證（BR-001）
- 整合 Repository Pattern

Resolves: US-001, AC-001-1, AC-001-2
```

---

## 📋 MoneyTracker 實際範例

### Feature 清單

| Feature ID | 功能名稱 | 優先級 | 相關 BR | Epic |
|-----------|---------|-------|---------|------|
| F-001 | 新增收入記錄 | Must-have | BR-001, BR-002 | EPIC-001 |
| F-002 | 新增支出記錄 | Must-have | BR-001, BR-002 | EPIC-001 |
| F-003 | 編輯交易記錄 | Must-have | BR-001, BR-002 | EPIC-001 |
| F-004 | 刪除交易記錄 | Must-have | - | EPIC-001 |
| F-005 | 查看交易列表 | Must-have | - | EPIC-001 |
| F-006 | 查看收支統計 | Must-have | - | EPIC-002 |
| F-007 | 分類管理 | Must-have | BR-003 | EPIC-003 |
| F-008 | 匯出報表 | Nice-to-have | - | EPIC-002 |

### Business Rules

| BR ID | 業務規則 | 相關 Feature |
|-------|---------|-------------|
| BR-001 | 金額必須大於 0 | F-001, F-002, F-003 |
| BR-002 | 日期不可為未來日期 | F-001, F-002, F-003 |
| BR-003 | 分類名稱不可重複 | F-007 |
| BR-004 | 每筆交易必須指定分類 | F-001, F-002 |

### Epic 與 User Story

| Epic ID | Epic 名稱 | User Stories |
|---------|----------|-------------|
| EPIC-001 | 交易管理 | US-001 ~ US-005 |
| EPIC-002 | 報表與統計 | US-006 ~ US-008 |
| EPIC-003 | 分類管理 | US-009 ~ US-010 |
| EPIC-004 | 設定與偏好 | US-011 ~ US-012 |

---

## 🔗 相關文件

### 模板引用
- [PRD_Universal_Template.md](../docs_template/prd/PRD_Universal_Template.md) - 使用 Feature ID, NFR ID
- [FRD_Universal_Template.md](../docs_template/frd/FRD_Universal_Template.md) - 使用 BR ID, UR ID
- [User_Story_Template.md](../docs_template/prd/User_Story_Template.md) - 使用 Epic ID, US ID, AC ID
- [API_Specification_Template.md](../docs_template/srd/api/API_Specification_Template.md) - 使用 API ID

### 相關指引
- [Greenfield SOP.md](../scenarios/greenfield/SOP.md) - 各階段使用對應 ID
- [Requirement_Extraction_Report_Template.md](../docs_template/support/Requirement_Extraction_Report_Template.md) - 記錄 Feature ID, BR ID

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-12 | 初版建立 - Phase 2 P1 問題修正 |

---

**文檔維護者**: AISDLC Framework Team
**最後更新**: 2025-11-12
**狀態**: ✅ Active

---

**End of Document**
