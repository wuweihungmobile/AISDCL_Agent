# API 版本升級與管理指引
# API Versioning and Upgrade Guide

> **🔴 核心指引文檔 🔴**
>
> 本文檔提供 API 版本管理的完整指引，包含版本策略、升級流程、向後兼容性原則和實際範例。

---

**版本**: v0.01
**創建日期**: 2025-11-27
**文檔類型**: 開發指引 | API 管理
**適用範圍**: 所有包含 API 的專案場景
**關聯文檔**: [API_Specification_Template.md](../docs_template/core/api/API_Specification_Template.md), [API_Error_Codes.md](../docs_template/core/api/API_Error_Codes.md)

---

## 📋 目錄

1. [API 版本管理策略](#api-版本管理策略)
2. [語義化版本規範](#語義化版本規範)
3. [版本升級類型](#版本升級類型)
4. [向後兼容性原則](#向後兼容性原則)
5. [版本廢棄流程](#版本廢棄流程)
6. [版本在 URL 中的呈現](#版本在-url-中的呈現)
7. [API 變更影響分析](#api-變更影響分析)
8. [版本升級實施步驟](#版本升級實施步驟)
9. [版本文檔維護](#版本文檔維護)
10. [常見問題與最佳實踐](#常見問題與最佳實踐)

---

## 🎯 API 版本管理策略

### 為什麼需要 API 版本管理？

**核心原因**:
- 🔄 **演進需求**: API 需要持續改進和功能擴展
- 🛡️ **穩定保證**: 保護現有客戶端不被破壞性變更影響
- 📅 **平滑遷移**: 給予客戶端充足時間進行版本遷移
- 📊 **監控追蹤**: 了解各版本使用狀況，制定廢棄計畫

### 版本管理的三個層次

```plaintext
┌─────────────────────────────────────────────────────────┐
│ Level 1: URL 版本 (Major Version)                       │
│ /api/v1/, /api/v2/, /api/v3/                           │
│ - 適用於: 破壞性變更 (Breaking Changes)                 │
│ - 客戶端需求: 必須修改代碼                              │
│ - 範例: 改變資料結構、移除端點、改變驗證機制              │
└─────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Level 2: API 內部版本 (Minor Version)                   │
│ Header: API-Version: 1.2, API-Version: 1.3             │
│ - 適用於: 向後兼容的新增功能                             │
│ - 客戶端需求: 可選擇性升級                              │
│ - 範例: 新增欄位、新增可選參數、新增端點                 │
└─────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ Level 3: Bug 修復版本 (Patch Version)                   │
│ 透明處理，客戶端無需感知                                 │
│ - 適用於: Bug 修復、效能優化、安全修補                   │
│ - 客戶端需求: 無需任何變更                              │
│ - 範例: 錯誤修正、回應速度改善、安全漏洞修補              │
└─────────────────────────────────────────────────────────┘
```

---

## 📐 語義化版本規範

### 版本號格式: `MAJOR.MINOR.PATCH`

**範例**: `v2.3.1`

| 版本類型 | 說明 | 何時遞增 | 對客戶端的影響 |
|---------|------|---------|---------------|
| **MAJOR** | 主版本號 | 不兼容的 API 變更 | ⚠️ **必須修改代碼** |
| **MINOR** | 次版本號 | 向後兼容的功能新增 | ✅ 可選擇性升級 |
| **PATCH** | 修訂版本號 | 向後兼容的 Bug 修復 | ✅ 透明升級 |

### 版本號遞增規則

```plaintext
1.0.0  (初始發布)
  ↓
1.0.1  (Bug 修復: 修正登入驗證錯誤)
  ↓
1.1.0  (新增功能: 新增 OAuth2 支援，保持向後兼容)
  ↓
1.1.1  (Bug 修復: 修正 OAuth2 Token 更新問題)
  ↓
2.0.0  (破壞性變更: 移除舊有 Session 驗證機制)
```

**重要規則**:
- ✅ MAJOR 版本遞增時，MINOR 和 PATCH 歸零: `1.9.5` → `2.0.0`
- ✅ MINOR 版本遞增時，PATCH 歸零: `1.3.8` → `1.4.0`
- ✅ PATCH 版本遞增時，僅 PATCH 遞增: `1.3.5` → `1.3.6`
- ❌ 不允許跳號: `1.2.0` → `1.4.0` (錯誤，應該 `1.3.0`)

---

## 🔄 版本升級類型

### 1. Major 版本升級 (破壞性變更)

**定義**: 任何會導致現有客戶端無法正常運作的變更

**觸發條件** (任一條件符合即為 Major 變更):
- 🔴 **移除 API 端點**: 刪除整個 API
- 🔴 **移除必要欄位**: 從請求或回應中移除欄位
- 🔴 **改變資料類型**: `string` → `integer`, `array` → `object`
- 🔴 **改變欄位語義**: 欄位名稱相同但意義改變
- 🔴 **改變 HTTP 狀態碼**: 成功情境從 200 改為 201
- 🔴 **改變驗證機制**: OAuth2 改為 JWT, 移除 Basic Auth
- 🔴 **改變錯誤格式**: 錯誤回應結構改變

**範例**:

```diff
# ❌ Major 破壞性變更範例 1: 移除必要欄位

# v1.0 - 舊版 API 回應
{
  "user_id": 123,
  "username": "john",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}

# v2.0 - 新版 API 回應 (移除 username 欄位)
{
  "user_id": 123,
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}
# ⚠️ 客戶端依賴 username 的邏輯會中斷
```

```diff
# ❌ Major 破壞性變更範例 2: 改變資料結構

# v1.0 - 舊版 API 回應
{
  "tags": "tag1,tag2,tag3"  // String 格式
}

# v2.0 - 新版 API 回應
{
  "tags": ["tag1", "tag2", "tag3"]  // Array 格式
}
# ⚠️ 客戶端解析邏輯必須修改
```

**實施要求**:
1. ✅ **必須**提前至少 6 個月公告
2. ✅ **必須**在多個版本中同時提供舊版和新版
3. ✅ **必須**提供完整的遷移指南
4. ✅ **必須**在回應 Header 中警告客戶端: `Deprecation: true`

---

### 2. Minor 版本升級 (向後兼容的新增)

**定義**: 新增功能但不影響現有客戶端的運作

**允許的變更類型**:
- ✅ **新增 API 端點**: 新增新的資源或操作
- ✅ **新增可選欄位**: 在回應中新增新欄位 (不影響舊客戶端)
- ✅ **新增可選參數**: 在請求中新增可選參數 (提供預設值)
- ✅ **新增 HTTP Header**: 新增可選的請求/回應 Header
- ✅ **擴展列舉值**: 在 enum 中新增新值 (需客戶端容錯處理)
- ✅ **新增錯誤碼**: 新增更精確的錯誤碼 (保留原有錯誤碼)

**範例**:

```diff
# ✅ Minor 向後兼容變更範例 1: 新增可選欄位

# v1.0 - 舊版 API 回應
{
  "user_id": 123,
  "username": "john",
  "email": "john@example.com"
}

# v1.1 - 新版 API 回應 (新增 avatar_url)
{
  "user_id": 123,
  "username": "john",
  "email": "john@example.com",
  "avatar_url": "https://cdn.example.com/avatar/123.png"  // 新增
}
# ✅ 舊客戶端可以忽略新欄位，繼續正常運作
```

```diff
# ✅ Minor 向後兼容變更範例 2: 新增可選參數

# v1.0 - 舊版 API 請求
GET /api/v1/users?status=active

# v1.1 - 新版 API 請求 (新增 sort 參數)
GET /api/v1/users?status=active&sort=created_at:desc
# ✅ 舊客戶端不傳 sort 參數時，使用預設排序，仍正常運作
```

**實施要求**:
1. ✅ **建議**在 CHANGELOG 中記錄新增功能
2. ✅ **建議**在 API 文檔中標註 `@since v1.1` 標籤
3. ✅ 新增欄位應考慮**預設值**或**可為 null**

---

### 3. Patch 版本升級 (Bug 修復)

**定義**: 修正錯誤行為，使其符合文檔描述

**允許的變更類型**:
- ✅ **Bug 修復**: 修正不符合文檔的行為
- ✅ **效能優化**: 不改變輸入輸出的效能改善
- ✅ **安全修補**: 修復安全漏洞
- ✅ **內部重構**: 不影響外部行為的代碼重構
- ✅ **文檔修正**: 修正文檔錯誤或不清楚的描述

**範例**:

```diff
# ✅ Patch Bug 修復範例: 修正錯誤的 HTTP 狀態碼

# v1.0.0 - Bug (文檔說應該返回 404，但實際返回 500)
GET /api/v1/users/999999  # 不存在的使用者
Response: 500 Internal Server Error  # ❌ 錯誤

# v1.0.1 - 修復後 (符合文檔描述)
GET /api/v1/users/999999
Response: 404 Not Found  # ✅ 正確
```

**實施要求**:
1. ✅ **必須**在 CHANGELOG 中記錄修復內容
2. ✅ **必須**註明修復的 Issue 編號或 Bug ID
3. ⚠️ 如果 Bug 存在時間過長，客戶端可能已經依賴錯誤行為，需評估影響

---

## 🛡️ 向後兼容性原則

### Postel's Law (寬鬆接收，嚴格發送)

> **"Be conservative in what you send, be liberal in what you accept"**
> - 對發送的資料嚴格遵守規範
> - 對接收的資料寬容處理

### API 設計的向後兼容原則

#### ✅ 安全的變更 (不破壞兼容性)

| 變更類型 | 範例 | 原因 |
|---------|------|------|
| **新增可選欄位** | 回應中新增 `last_login_at` | 舊客戶端可以忽略 |
| **新增可選參數** | 新增 `?page_size=20` 參數 | 提供預設值，舊客戶端不傳也能用 |
| **新增端點** | 新增 `POST /api/v1/users/bulk` | 不影響現有端點 |
| **擴展列舉值** | `status: [active, inactive]` → `[active, inactive, suspended]` | 舊客戶端可以用 `default` 處理 |
| **放寬驗證規則** | `username` 長度從 8-20 放寬為 3-50 | 原有值仍然合法 |

#### ❌ 不安全的變更 (破壞兼容性)

| 變更類型 | 範例 | 破壞原因 |
|---------|------|---------|
| **移除欄位** | 從回應中移除 `username` | 客戶端依賴該欄位會報錯 |
| **移除端點** | 刪除 `DELETE /api/v1/users/:id` | 客戶端呼叫會得到 404 |
| **改變資料類型** | `age: 25` (integer) → `"25"` (string) | 客戶端型別檢查失敗 |
| **重新命名欄位** | `user_id` → `userId` | 客戶端找不到欄位 |
| **收緊驗證規則** | `password` 長度從 6+ 改為 8+ | 原有短密碼無法再使用 |
| **改變必填性** | `email` 從可選改為必填 | 舊客戶端不傳會失敗 |

### 兼容性測試清單

```markdown
## API 變更兼容性檢查清單 ✅

- [ ] **回應欄位**: 是否移除或重新命名了任何回應欄位？
- [ ] **請求參數**: 是否將可選參數改為必填？
- [ ] **資料類型**: 是否改變了任何欄位的資料類型？
- [ ] **HTTP 狀態碼**: 是否改變了成功或失敗情境的狀態碼？
- [ ] **錯誤格式**: 是否改變了錯誤回應的結構？
- [ ] **驗證規則**: 是否收緊了輸入驗證規則？
- [ ] **端點路徑**: 是否移除或改變了端點 URL？
- [ ] **驗證機制**: 是否改變了認證或授權方式？

**如果任一項答案為「是」，則為 Major 破壞性變更，需升級主版本號。**
```

---

## 📅 版本廢棄流程

### 廢棄時間軸 (標準流程)

```plaintext
Timeline: API 版本從發布到完全移除的生命週期

│
├─ T0: v2.0 發布
│    └─ v1.0 進入「穩定期」(Stable)
│       • 繼續支援，無廢棄警告
│       • 仍接受 Bug 修復
│
├─ T+6個月: v3.0 發布
│    └─ v1.0 進入「廢棄期」(Deprecated)
│       • ⚠️ 開始發送廢棄警告 Header
│       • 📢 官方部落格/文檔公告
│       • 📧 Email 通知重度使用客戶
│       • 僅修復關鍵安全漏洞，不再新增功能
│
├─ T+12個月: v4.0 發布
│    └─ v1.0 進入「停止支援期」(Unsupported)
│       • 🛑 不再修復任何 Bug
│       • ⚠️ 加強廢棄警告 (每個回應都包含警告)
│       • 📊 監控使用量，準備移除
│
├─ T+18個月:
│    └─ v1.0 完全移除 (Sunset)
│       • ❌ API 端點返回 410 Gone
│       • 📄 提供遷移文檔連結
│
└─ T+24個月:
     └─ 移除所有 v1.0 相關基礎設施
```

### 廢棄公告範本

#### 1. API 回應 Header 廢棄警告

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Wed, 01 Jan 2026 00:00:00 GMT
Link: <https://api.example.com/docs/v2-migration>; rel="alternate"
Warning: 299 - "This API version is deprecated. Please migrate to v2 by 2026-01-01. See https://api.example.com/docs/v2-migration"

{
  "data": { ... },
  "_deprecation": {
    "deprecated": true,
    "sunset_date": "2026-01-01",
    "alternative_version": "v2",
    "migration_guide": "https://api.example.com/docs/v2-migration",
    "contact_support": "api-support@example.com"
  }
}
```

#### 2. 文檔廢棄標註範例

```markdown
# ⚠️ API v1 廢棄公告

**廢棄日期**: 2025-07-01
**停止支援日期**: 2026-01-01
**完全移除日期**: 2026-07-01

---

## 廢棄原因

v1 API 存在以下限制，將由 v2 取代：
1. 不支援分頁，單次回傳最多 100 筆資料
2. 不支援欄位過濾，總是回傳完整資料
3. 不支援批次操作，效能較差

## 遷移指南

請參考完整的 [v1 → v2 遷移指南](./v1-to-v2-migration.md)。

**快速範例**:

| v1 API | v2 API |
|--------|--------|
| `GET /api/v1/users` | `GET /api/v2/users?page=1&page_size=20` |
| `POST /api/v1/user` | `POST /api/v2/users` (單數改為複數) |
| `user_id` (回應欄位) | `id` (欄位重新命名) |

## 聯絡我們

如有遷移問題，請聯繫: api-support@example.com
```

### 410 Gone 回應範例 (API 已完全移除)

```http
HTTP/1.1 410 Gone
Content-Type: application/json

{
  "error": {
    "code": "API_VERSION_REMOVED",
    "message": "API v1 has been permanently removed as of 2026-07-01",
    "sunset_date": "2026-07-01",
    "alternative_version": "v2",
    "migration_guide": "https://api.example.com/docs/v1-to-v2-migration",
    "support_contact": "api-support@example.com"
  }
}
```

---

## 🌐 版本在 URL 中的呈現

### 推薦方式: URL Path Versioning

**格式**: `/api/v{MAJOR}/resource`

**範例**:
```plaintext
https://api.example.com/api/v1/users
https://api.example.com/api/v2/users
https://api.example.com/api/v3/users
```

**優點**:
- ✅ **直觀易懂**: 從 URL 即可看出版本
- ✅ **快取友好**: 不同版本有不同的 URL，快取機制簡單
- ✅ **瀏覽器相容**: 可直接在瀏覽器中測試
- ✅ **文檔清晰**: Swagger/OpenAPI 文檔容易組織

**缺點**:
- ⚠️ URL 結構改變時需要更新所有文檔連結

### 替代方式: Header Versioning (不推薦用於 Major 版本)

**格式**: `API-Version: 1.2.0` (HTTP Header)

**範例**:
```http
GET /api/users
Host: api.example.com
API-Version: 2.3.0
```

**優點**:
- ✅ URL 保持不變，易於管理
- ✅ 可以精確指定到 Minor/Patch 版本

**缺點**:
- ❌ 不適合瀏覽器直接訪問
- ❌ 快取複雜度增加
- ❌ 對開發者不夠直觀

**建議使用場景**: 用於 Minor 版本控制，Major 版本仍使用 URL Path

---

## 📊 API 變更影響分析

### 變更影響評估矩陣

| 變更類型 | 影響等級 | 客戶端行動 | 測試需求 | 公告期 |
|---------|---------|-----------|---------|--------|
| **移除端點** | 🔴 Critical | 必須修改代碼 | 完整回歸測試 | 6-12 個月 |
| **改變資料結構** | 🔴 Critical | 必須修改代碼 | 完整回歸測試 | 6-12 個月 |
| **改變驗證機制** | 🔴 Critical | 必須修改代碼 | 安全測試 | 6-12 個月 |
| **新增必填欄位** | 🟠 High | 必須提供新參數 | 整合測試 | 3-6 個月 |
| **收緊驗證規則** | 🟠 High | 可能需調整輸入 | 驗證測試 | 3-6 個月 |
| **新增可選欄位** | 🟡 Medium | 可選擇性使用 | 單元測試 | 1 個月 |
| **新增端點** | 🟢 Low | 無需行動 | 新功能測試 | 即時 |
| **Bug 修復** | 🟢 Low | 無需行動 | Bug 修復測試 | 即時 |

### 客戶端影響分析流程

```markdown
## API 變更影響分析表

**變更內容**: [描述變更內容]
**計畫發布版本**: v2.0.0
**預計發布日期**: 2025-12-01

### 1. 變更類型判定

- [ ] Major (破壞性變更)
- [ ] Minor (向後兼容新增)
- [ ] Patch (Bug 修復)

### 2. 影響範圍評估

**受影響的 API 端點**:
- `GET /api/v1/users/{id}`
- `POST /api/v1/users`

**受影響的欄位**:
- `username` (已移除)
- `display_name` (新增，替代 username)

### 3. 客戶端使用分析 (來自監控數據)

| 客戶端類型 | 使用量 (QPS) | 受影響程度 | 遷移優先度 |
|-----------|-------------|-----------|-----------|
| Mobile App v3.2+ | 1200 | 高 | P0 |
| Web Frontend | 800 | 高 | P0 |
| 第三方整合 A | 200 | 中 | P1 |
| 第三方整合 B | 50 | 低 | P2 |
| Legacy System | 10 | 低 (計畫汰除) | P3 |

### 4. 遷移計畫

**Phase 1 (T+0 ~ T+1個月)**:
- 發布 v2.0.0-beta，並行運作
- 提供遷移文檔和範例代碼
- 聯繫高影響客戶端團隊

**Phase 2 (T+2個月 ~ T+6個月)**:
- v1 標記為 Deprecated
- 開始發送廢棄警告 Header
- 監控 v2 採用率

**Phase 3 (T+6個月 ~ T+12個月)**:
- v1 停止支援 (僅修復安全漏洞)
- 加強廢棄警告
- 協助剩餘客戶端遷移

**Phase 4 (T+12個月+)**:
- 完全移除 v1 (返回 410 Gone)
```

---

## 🚀 版本升級實施步驟

### Step 1: 變更評估與規劃

**1.1 識別變更類型**

```markdown
## API 變更需求

**需求來源**: US-042 (User Story)
**需求描述**: 使用者希望能夠批次更新多個資源

**提議變更**:
- 新增 `POST /api/v1/resources/bulk-update` 端點

**變更類型判定**:
- [x] Minor (新增端點，向後兼容)
- [ ] Major (破壞性變更)
- [ ] Patch (Bug 修復)

**版本號決定**: v1.2.0 → v1.3.0
```

**1.2 影響分析**

使用前面的「API 變更影響分析表」進行評估。

**1.3 遷移計畫制定**

如果是 Major 變更，必須制定詳細的遷移計畫。

---

### Step 2: API 規格文檔更新

**2.1 更新 API Specification**

在 [API_Specification_Template.md](../docs_template/core/api/API_Specification_Template.md) 中更新：

```markdown
## 修訂歷史

| 版本 | 日期 | 作者 | 修改內容 |
| --- | --- | --- | --- |
| v1.2.0 | 2025-10-01 | Alice | 新增 OAuth2 支援 |
| v1.3.0 | 2025-11-01 | Bob | 新增批次更新端點 |  ⬅️ 新增此行
```

**2.2 更新 API Index**

在 [API_Index_Template.md](../docs_template/core/api/API_Index_Template.md) 中新增端點：

```markdown
| API-015 | POST /api/v1/resources/bulk-update | 批次更新資源 | @since v1.3.0 |
```

**2.3 標註版本新增標記**

```markdown
### POST /api/v1/resources/bulk-update

**@since v1.3.0**  ⬅️ 版本標註

此端點允許批次更新多個資源...
```

---

### Step 3: 實作與測試

**3.1 開發環境測試**

```bash
# 測試新增的端點
curl -X POST https://api-dev.example.com/api/v1/resources/bulk-update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      { "id": 1, "status": "active" },
      { "id": 2, "status": "inactive" }
    ]
  }'
```

**3.2 向後兼容性測試**

```bash
# 執行舊版客戶端測試套件，確保沒有破壞既有功能
npm run test:compatibility
```

**3.3 效能測試**

```bash
# 確保新版本沒有效能衰退
npm run test:performance
```

---

### Step 4: 部署與監控

**4.1 金絲雀發布 (Canary Deployment)**

```yaml
# 部署配置範例
deployment:
  strategy: canary
  steps:
    - traffic: 10%  # 導入 10% 流量到新版本
      duration: 2h
      success_criteria:
        error_rate: < 1%
        latency_p99: < 500ms

    - traffic: 50%  # 成功後擴展到 50%
      duration: 4h

    - traffic: 100% # 全面切換
```

**4.2 監控指標**

```markdown
## 版本發布監控清單

- [ ] 錯誤率 (Error Rate): < 1%
- [ ] 回應時間 P99 (Latency P99): < 500ms
- [ ] 新端點使用量 (Adoption Rate): 追蹤 QPS
- [ ] 舊端點使用量 (Legacy Usage): 追蹤是否下降
- [ ] 客戶端錯誤 (4xx Errors): 監控新驗證邏輯
- [ ] 伺服器錯誤 (5xx Errors): 監控新功能穩定性
```

**4.3 回滾計畫**

```markdown
## 回滾決策標準

**觸發條件** (任一條件滿足即回滾):
- 錯誤率 > 5%
- P99 延遲 > 1000ms
- 關鍵客戶端報告嚴重 Bug

**回滾步驟**:
1. 立即切換流量回舊版本 (< 5 分鐘)
2. 暫停新版本部署
3. 分析問題根因
4. 修復後重新部署
```

---

### Step 5: 文檔發布與公告

**5.1 更新 CHANGELOG**

```markdown
# API Changelog

## [v1.3.0] - 2025-11-01

### Added
- 新增 `POST /api/v1/resources/bulk-update` 端點，支援批次更新資源
- 新增 `batch_size` 參數限制 (預設 100，最大 1000)

### Fixed
- 修正 `GET /api/v1/resources/:id` 在資源不存在時返回 500 的問題 (現在返回 404)

### Security
- 加強 OAuth2 Token 驗證機制
```

**5.2 公告範本**

```markdown
# 📢 API v1.3.0 發布公告

**發布日期**: 2025-11-01

## 🆕 新功能

### 批次更新端點

新增 `POST /api/v1/resources/bulk-update` 端點，允許單次請求更新多個資源，大幅提升效率。

**使用範例**:

\`\`\`bash
curl -X POST https://api.example.com/api/v1/resources/bulk-update \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "updates": [
      { "id": 1, "status": "active" },
      { "id": 2, "status": "inactive" }
    ]
  }'
\`\`\`

**限制**:
- 單次最多更新 1000 個資源
- 請求大小不得超過 10MB

## 🐛 Bug 修復

- 修正資源不存在時的錯誤回應 (404 而非 500)

## 📚 更多資訊

- [完整 API 文檔](https://docs.example.com/api/v1.3)
- [遷移指南](https://docs.example.com/api/migration/v1.2-to-v1.3)

如有問題，請聯繫: api-support@example.com
```

---

## 📝 版本文檔維護

### 文檔結構建議

```plaintext
docs/api/
├── v1/
│   ├── index.md                    # API v1 總覽
│   ├── authentication.md           # 認證機制
│   ├── endpoints/
│   │   ├── users.md                # 使用者端點
│   │   ├── resources.md            # 資源端點
│   │   └── ...
│   ├── CHANGELOG.md                # v1 變更記錄
│   └── DEPRECATION.md              # v1 廢棄公告 (如適用)
│
├── v2/
│   ├── index.md
│   ├── authentication.md
│   ├── endpoints/
│   ├── CHANGELOG.md
│   └── migration-from-v1.md        # ⬅️ 重要！從 v1 遷移指南
│
└── version-policy.md               # 本文檔
```

### 遷移指南範本

```markdown
# API v1 → v2 遷移指南

**目標讀者**: 使用 API v1 的開發者
**預計遷移時間**: 2-4 小時 (取決於整合複雜度)
**v1 廢棄日期**: 2026-01-01

---

## 重大變更摘要

### 1. 認證機制變更

| v1 | v2 | 影響 |
|----|----|----|
| Session-based (Cookies) | JWT (Bearer Token) | 所有請求需修改 Header |

**變更原因**: 支援無狀態架構，更適合分散式系統

**遷移步驟**:

\`\`\`diff
# v1 - 使用 Session Cookie
fetch('/api/v1/users', {
  credentials: 'include'  // 自動帶入 Cookie
})

# v2 - 使用 JWT Bearer Token
+ const token = localStorage.getItem('access_token');
fetch('/api/v2/users', {
  headers: {
+   'Authorization': \`Bearer \${token}\`
  }
})
\`\`\`

---

### 2. 使用者 ID 欄位重新命名

| v1 | v2 | 影響 |
|----|----|----|
| \`user_id\` | \`id\` | 所有使用者相關回應 |

**變更原因**: 統一命名規範，簡化欄位名稱

**遷移步驟**:

\`\`\`diff
# v1 回應
{
- "user_id": 123,
  "username": "john"
}

# v2 回應
{
+ "id": 123,
  "username": "john"
}
\`\`\`

**程式碼修改範例** (JavaScript):

\`\`\`diff
- const userId = user.user_id;
+ const userId = user.id;
\`\`\`

---

### 3. 分頁參數標準化

| v1 | v2 | 預設值 |
|----|----|----|
| \`offset\`, \`limit\` | \`page\`, \`page_size\` | page=1, page_size=20 |

**遷移範例**:

\`\`\`diff
# v1 請求
- GET /api/v1/users?offset=40&limit=20

# v2 請求 (第 3 頁，每頁 20 筆)
+ GET /api/v2/users?page=3&page_size=20
\`\`\`

---

## 完整變更對照表

| 功能 | v1 端點 | v2 端點 | 備註 |
|-----|---------|---------|------|
| 取得使用者清單 | GET /api/v1/users | GET /api/v2/users | 新增分頁 |
| 建立使用者 | POST /api/v1/user | POST /api/v2/users | 路徑改為複數 |
| 更新使用者 | PUT /api/v1/user/:id | PATCH /api/v2/users/:id | 改用 PATCH 支援部分更新 |
| 刪除使用者 | DELETE /api/v1/user/:id | DELETE /api/v2/users/:id | 路徑改為複數 |

---

## 測試遷移的清單

- [ ] 更新認證機制 (Cookie → JWT)
- [ ] 更新所有 \`user_id\` 欄位為 \`id\`
- [ ] 更新分頁參數 (offset/limit → page/page_size)
- [ ] 更新端點路徑 (\`/user\` → \`/users\`)
- [ ] 更新 PUT 為 PATCH (部分更新場景)
- [ ] 執行完整回歸測試
- [ ] 監控生產環境錯誤率

---

## 常見問題

### Q: 可以同時支援 v1 和 v2 嗎？

A: 可以。v1 將持續支援到 2026-01-01，請在此之前完成遷移。

### Q: 遷移過程中遇到問題怎麼辦？

A: 請聯繫 api-support@example.com 或查看 [故障排除指南](./troubleshooting.md)。

### Q: 有提供自動化遷移工具嗎？

A: 我們提供了 [migration-scripts](https://github.com/example/api-migration-scripts) 協助常見場景的自動轉換。
\`\`\`
```

---

## ❓ 常見問題與最佳實踐

### Q1: 何時應該升級 Major 版本？

**A**: 當任何以下情況發生時：

1. **無法透過向後兼容方式解決的需求**
   - 範例: 需要移除已經錯誤設計的核心欄位

2. **技術債累積過多，需要重新設計**
   - 範例: v1 不支援分頁，導致效能問題嚴重

3. **安全性需求強制變更**
   - 範例: 必須移除不安全的認證機制

4. **商業策略調整**
   - 範例: 從免費 API 轉為需要付費訂閱

**建議**:
- ⏰ Major 版本升級至少間隔 12 個月
- 📊 升級前分析使用數據，確保客戶端遷移可行

---

### Q2: 如何處理「隱藏的破壞性變更」？

**範例情境**: 修復一個存在已久的 Bug，但部分客戶端可能已經依賴這個錯誤行為。

**A**: 使用「功能開關」(Feature Flag) 漸進式推出

```python
# 使用 Feature Flag 控制行為
if feature_flags.is_enabled('fix_user_id_bug', user_id):
    # 新的正確行為
    return correct_behavior()
else:
    # 舊的錯誤行為 (保持兼容)
    return legacy_buggy_behavior()
```

**流程**:
1. 預設關閉，僅對測試帳號開啟
2. 逐步開啟給 10% → 50% → 100% 使用者
3. 監控錯誤率，如有問題立即關閉
4. 穩定後移除 Feature Flag，清理舊代碼

---

### Q3: 如何平衡「創新速度」與「穩定性」？

**A**: 採用「雙軌策略」

```plaintext
┌─────────────────────────────────────────────┐
│ Stable API (v1)                             │
│ - 變更頻率: 每 6 個月一次 Minor 版本        │
│ - 適用對象: 企業客戶、生產環境              │
│ - SLA: 99.9% uptime                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Beta API (v2-beta)                          │
│ - 變更頻率: 每 2 週一次                     │
│ - 適用對象: 早期採用者、測試環境            │
│ - SLA: 95% uptime (明確標示 Beta)          │
└─────────────────────────────────────────────┘
```

**範例**:
- Stable API: `https://api.example.com/v1/users`
- Beta API: `https://api-beta.example.com/v2/users` 或 `https://api.example.com/beta/users`

---

### Q4: API 版本號與應用程式版本號應該一致嗎？

**A**: **不應該一致**

| 類型 | 範例 | 目的 |
|------|------|------|
| **API 版本號** | v1, v2, v3 | 對外承諾的穩定性契約 |
| **應用程式版本號** | v2.5.3 | 內部版本追蹤 |

**說明**:
- API 版本號是「對外契約」，應該變化緩慢
- 應用程式版本號是「內部追蹤」，可以頻繁迭代

**範例**:
- App v2.0.0, v2.1.0, v2.2.0 都可以使用 API v1
- 只有當 API 有破壞性變更時，才從 API v1 升級到 API v2

---

### 最佳實踐總結 ✅

1. **設計 API 時優先考慮擴展性**
   - ✅ 使用可選欄位而非必填欄位
   - ✅ 預留 `metadata` 或 `extensions` 欄位供未來擴展
   - ✅ 使用包裝對象而非直接返回陣列

2. **明確的版本策略文檔**
   - ✅ 在 API 文檔首頁清楚說明版本政策
   - ✅ 提供廢棄時間軸和遷移指南
   - ✅ 設定客戶支援信箱或討論區

3. **漸進式變更與監控**
   - ✅ 使用 Feature Flag 控制新功能推出
   - ✅ 金絲雀部署 (Canary Deployment)
   - ✅ 即時監控錯誤率和效能指標

4. **充分的遷移時間**
   - ✅ Major 變更至少 6 個月公告期
   - ✅ 提供自動化遷移工具或腳本
   - ✅ 主動聯繫重度使用客戶

5. **清晰的文檔與範例**
   - ✅ 每個版本維護獨立的文檔站點
   - ✅ 提供「Before/After」對照範例
   - ✅ 維護 FAQ 和故障排除指南

---

## 📚 參考資源

### 相關文檔
- [API Specification Template](../docs_template/core/api/API_Specification_Template.md) - API 規格文件範本
- [API Error Codes](../docs_template/core/api/API_Error_Codes.md) - 錯誤碼標準化
- [Consistency Check Workflow](../workflow/core/consistency-check.md) - 文檔一致性檢查

### 外部最佳實踐參考
- [Semantic Versioning 2.0.0](https://semver.org/) - 語義化版本規範
- [Microsoft REST API Guidelines - Versioning](https://github.com/microsoft/api-guidelines/blob/vNext/Guidelines.md#12-versioning) - Microsoft API 版本指引
- [Stripe API Versioning](https://stripe.com/docs/api/versioning) - Stripe 的版本管理實踐
- [RFC 8594 - The Sunset HTTP Header Field](https://www.rfc-editor.org/rfc/rfc8594.html) - API 廢棄 Header 標準

---

## 📝 文檔修訂歷史

| 版本 | 日期 | 修改人 | 修改內容 |
|------|------|--------|---------|
| v1.0 | 2025-11-27 | Claude | 初版建立 - 完整的 API 版本升級與管理指引 |

---

**文檔維護**: 本指引應隨 API 版本策略演進持續更新，確保與實際實施保持一致。

**回饋與建議**: 如有任何問題或改進建議，請聯繫架構團隊或提交 Issue。
