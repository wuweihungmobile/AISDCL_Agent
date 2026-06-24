# API 錯誤碼標準清單
# API Error Codes Standard List

**文檔類型**: API 錯誤碼規範
**範本版本**: v0.01
**創建日期**: 2025-11-25
**最後更新**: 2025-11-25
**維護團隊**: AISDLC Team

---

## 📋 文檔目的

本文檔定義 **系統化的 API 錯誤碼標準**，確保所有 API 端點使用一致的錯誤碼，提供：
- 🎯 **前端統一錯誤處理**：前端可根據錯誤碼範圍統一處理
- 🔍 **快速問題定位**：錯誤碼範圍直接指示問題類別
- 📊 **錯誤監控分析**：便於統計和分析錯誤分佈
- 🌐 **多語言支持**：錯誤碼與訊息分離，支持國際化

---

## 🎯 錯誤碼設計原則

### 1. 錯誤碼格式

```
[錯誤碼] (數字) + [錯誤訊息] (字串)
```

**範例**:
```json
{
  "status": "error",
  "error": {
    "code": 1001,
    "message": "無效的身份驗證令牌",
    "details": "Token 已過期，請重新登入"
  }
}
```

### 2. 錯誤碼範圍規劃

| 錯誤碼範圍 | 類別 | 說明 | HTTP Status |
|-----------|------|------|-------------|
| **1000-1999** | 認證錯誤 (Authentication) | 身份驗證相關問題 | 401 Unauthorized |
| **2000-2999** | 授權錯誤 (Authorization) | 權限不足相關問題 | 403 Forbidden |
| **3000-3999** | 驗證錯誤 (Validation) | 輸入資料驗證失敗 | 400 Bad Request |
| **4000-4999** | 資源錯誤 (Resource) | 資源不存在或操作失敗 | 404 Not Found, 409 Conflict |
| **5000-5999** | 業務邏輯錯誤 (Business Logic) | 業務規則違反 | 422 Unprocessable Entity |
| **6000-6999** | 外部服務錯誤 (External Service) | 第三方服務調用失敗 | 502 Bad Gateway, 503 Service Unavailable |
| **7000-7999** | 系統錯誤 (System) | 系統內部錯誤 | 500 Internal Server Error |
| **8000-8999** | Rate Limiting 錯誤 | API 請求頻率限制 | 429 Too Many Requests |
| **9000-9999** | 自定義業務錯誤 | 專案特定業務錯誤 | 視業務邏輯而定 |

---

## 📚 標準錯誤碼清單

### 1000-1999: 認證錯誤 (Authentication Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **1001** | INVALID_TOKEN | 無效的身份驗證令牌 | 401 | Token 格式不正確或已損壞 |
| **1002** | EXPIRED_TOKEN | 令牌已過期 | 401 | Token 已超過有效期限 |
| **1003** | MISSING_TOKEN | 缺少身份驗證令牌 | 401 | 請求未包含必要的 Token |
| **1004** | INVALID_CREDENTIALS | 無效的登入憑證 | 401 | 帳號或密碼錯誤 |
| **1005** | ACCOUNT_LOCKED | 帳號已被鎖定 | 401 | 多次登入失敗導致帳號鎖定 |
| **1006** | ACCOUNT_DISABLED | 帳號已被停用 | 401 | 帳號被管理員停用 |
| **1007** | INVALID_API_KEY | 無效的 API Key | 401 | API Key 不正確或已失效 |
| **1008** | SESSION_EXPIRED | 會話已過期 | 401 | 使用者 Session 已過期 |
| **1009** | LOGOUT_REQUIRED | 需要重新登入 | 401 | 強制登出（如密碼已變更） |
| **1010** | TWO_FACTOR_REQUIRED | 需要雙因素驗證 | 401 | 需要完成 2FA 驗證 |

---

### 2000-2999: 授權錯誤 (Authorization Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **2001** | FORBIDDEN | 拒絕存取 | 403 | 使用者無權存取該資源 |
| **2002** | INSUFFICIENT_ROLE | 角色權限不足 | 403 | 角色層級不足以執行操作 |
| **2003** | RESOURCE_OWNER_ONLY | 僅資源擁有者可操作 | 403 | 只有資源建立者可執行 |
| **2004** | TEAM_MEMBER_ONLY | 僅團隊成員可存取 | 403 | 需要是團隊成員 |
| **2005** | SUBSCRIPTION_REQUIRED | 需要訂閱方案 | 403 | 需要升級訂閱 |
| **2006** | FEATURE_NOT_ENABLED | 功能未啟用 | 403 | 功能未在此帳號啟用 |
| **2007** | PERMISSION_DENIED | 權限被拒絕 | 403 | 明確的權限檢查失敗 |
| **2008** | IP_NOT_ALLOWED | IP 位址不在白名單 | 403 | IP 限制 |
| **2009** | QUOTA_EXCEEDED | 配額已用盡 | 403 | 已達使用配額上限 |
| **2010** | ACCESS_REVOKED | 存取權限已被撤銷 | 403 | 權限已被管理員撤銷 |

---

### 3000-3999: 驗證錯誤 (Validation Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **3001** | VALIDATION_ERROR | 資料驗證失敗 | 400 | 通用驗證錯誤 |
| **3002** | MISSING_REQUIRED_FIELD | 缺少必填欄位 | 400 | 必要欄位未提供 |
| **3003** | INVALID_FORMAT | 格式不正確 | 400 | 資料格式不符合規範 |
| **3004** | INVALID_EMAIL | 無效的電子郵件 | 400 | Email 格式錯誤 |
| **3005** | INVALID_PHONE | 無效的電話號碼 | 400 | 電話號碼格式錯誤 |
| **3006** | INVALID_DATE | 無效的日期 | 400 | 日期格式或值不正確 |
| **3007** | INVALID_RANGE | 數值超出範圍 | 400 | 數值不在允許範圍內 |
| **3008** | STRING_TOO_SHORT | 字串過短 | 400 | 未達最小長度 |
| **3009** | STRING_TOO_LONG | 字串過長 | 400 | 超過最大長度 |
| **3010** | INVALID_ENUM_VALUE | 無效的枚舉值 | 400 | 值不在允許的枚舉列表中 |
| **3011** | INVALID_JSON | 無效的 JSON 格式 | 400 | JSON 解析失敗 |
| **3012** | FILE_TOO_LARGE | 檔案過大 | 400 | 檔案大小超過限制 |
| **3013** | INVALID_FILE_TYPE | 不支援的檔案類型 | 400 | 檔案類型不被允許 |
| **3014** | INVALID_URL | 無效的 URL | 400 | URL 格式錯誤 |
| **3015** | INVALID_UUID | 無效的 UUID | 400 | UUID 格式不正確 |

---

### 4000-4999: 資源錯誤 (Resource Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **4001** | NOT_FOUND | 資源不存在 | 404 | 找不到指定資源 |
| **4002** | ALREADY_EXISTS | 資源已存在 | 409 | 嘗試建立重複資源 |
| **4003** | DUPLICATE_ENTRY | 重複的項目 | 409 | 唯一性約束違反 |
| **4004** | RESOURCE_DELETED | 資源已被刪除 | 410 Gone | 資源已被永久刪除 |
| **4005** | CONFLICT | 資源衝突 | 409 | 資源狀態衝突 |
| **4006** | VERSION_MISMATCH | 版本不符 | 409 | 樂觀鎖版本衝突 |
| **4007** | RESOURCE_LOCKED | 資源已被鎖定 | 423 Locked | 資源正被其他操作鎖定 |
| **4008** | DEPENDENCY_EXISTS | 存在依賴關係 | 409 | 無法刪除因有依賴資源 |
| **4009** | PARENT_NOT_FOUND | 父資源不存在 | 404 | 關聯的父資源不存在 |
| **4010** | CIRCULAR_DEPENDENCY | 循環依賴 | 400 | 檢測到循環引用 |

---

### 5000-5999: 業務邏輯錯誤 (Business Logic Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **5001** | BUSINESS_RULE_VIOLATION | 違反業務規則 | 422 | 通用業務規則違反 |
| **5002** | INSUFFICIENT_BALANCE | 餘額不足 | 422 | 帳戶餘額不足 |
| **5003** | INVALID_STATE_TRANSITION | 無效的狀態轉換 | 422 | 狀態機轉換不合法 |
| **5004** | OPERATION_NOT_ALLOWED | 操作不被允許 | 422 | 當前狀態不允許此操作 |
| **5005** | DEADLINE_PASSED | 截止日期已過 | 422 | 操作已超過截止時間 |
| **5006** | MAX_ITEMS_EXCEEDED | 超過項目數量上限 | 422 | 已達項目數量限制 |
| **5007** | MINIMUM_NOT_MET | 未達最小要求 | 422 | 未滿足最小數量要求 |
| **5008** | INVALID_COMBINATION | 無效的組合 | 422 | 參數組合不合法 |
| **5009** | PRECONDITION_FAILED | 前置條件未滿足 | 412 | 需先完成其他操作 |
| **5010** | WORKFLOW_VIOLATION | 違反工作流程 | 422 | 工作流程執行順序錯誤 |

---

### 6000-6999: 外部服務錯誤 (External Service Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **6001** | EXTERNAL_SERVICE_ERROR | 外部服務錯誤 | 502 | 第三方服務回應錯誤 |
| **6002** | EXTERNAL_SERVICE_UNAVAILABLE | 外部服務不可用 | 503 | 第三方服務無法連線 |
| **6003** | EXTERNAL_SERVICE_TIMEOUT | 外部服務逾時 | 504 | 第三方服務回應逾時 |
| **6004** | PAYMENT_GATEWAY_ERROR | 支付閘道錯誤 | 502 | 支付服務錯誤 |
| **6005** | SMS_SERVICE_ERROR | 簡訊服務錯誤 | 502 | 簡訊發送失敗 |
| **6006** | EMAIL_SERVICE_ERROR | 郵件服務錯誤 | 502 | 郵件發送失敗 |
| **6007** | STORAGE_SERVICE_ERROR | 儲存服務錯誤 | 502 | 檔案儲存服務錯誤 |
| **6008** | AUTH_PROVIDER_ERROR | 第三方登入錯誤 | 502 | OAuth 提供者錯誤 |
| **6009** | NOTIFICATION_SERVICE_ERROR | 通知服務錯誤 | 502 | 推播通知服務錯誤 |
| **6010** | EXTERNAL_API_RATE_LIMIT | 外部 API 頻率限制 | 429 | 第三方 API 達到限制 |

---

### 7000-7999: 系統錯誤 (System Errors)

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **7001** | INTERNAL_SERVER_ERROR | 內部伺服器錯誤 | 500 | 未預期的系統錯誤 |
| **7002** | DATABASE_ERROR | 資料庫錯誤 | 500 | 資料庫連線或查詢錯誤 |
| **7003** | CACHE_ERROR | 快取錯誤 | 500 | 快取服務錯誤 |
| **7004** | QUEUE_ERROR | 佇列錯誤 | 500 | 訊息佇列錯誤 |
| **7005** | FILE_SYSTEM_ERROR | 檔案系統錯誤 | 500 | 檔案讀寫錯誤 |
| **7006** | MEMORY_ERROR | 記憶體錯誤 | 500 | 記憶體不足 |
| **7007** | CONFIGURATION_ERROR | 配置錯誤 | 500 | 系統配置錯誤 |
| **7008** | SERVICE_DEGRADED | 服務降級 | 503 | 系統部分功能不可用 |
| **7009** | MAINTENANCE_MODE | 維護模式 | 503 | 系統維護中 |
| **7010** | FATAL_ERROR | 嚴重錯誤 | 500 | 系統致命錯誤 |

---

### 8000-8999: Rate Limiting 錯誤

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **8001** | RATE_LIMIT_EXCEEDED | 超過請求頻率限制 | 429 | API 請求過於頻繁 |
| **8002** | DAILY_LIMIT_EXCEEDED | 超過每日限制 | 429 | 已達每日請求上限 |
| **8003** | CONCURRENT_LIMIT_EXCEEDED | 超過並發限制 | 429 | 同時請求數過多 |
| **8004** | IP_RATE_LIMIT_EXCEEDED | IP 頻率限制 | 429 | 特定 IP 請求過多 |
| **8005** | USER_RATE_LIMIT_EXCEEDED | 使用者頻率限制 | 429 | 特定使用者請求過多 |

---

### 9000-9999: 自定義業務錯誤 (Custom Business Errors)

> **📝 說明**: 此範圍保留給專案特定的業務邏輯錯誤，建議按功能模組劃分子範圍。

**範例模組劃分**:
- **9000-9099**: 專案管理模組
- **9100-9199**: 任務管理模組
- **9200-9299**: 團隊協作模組
- **9300-9399**: 報表模組
- **9400-9499**: 通知模組

**範例錯誤碼**:

| 錯誤碼 | 錯誤代號 | 描述 | HTTP Status | 使用場景 |
|--------|---------|------|-------------|---------|
| **9001** | PROJECT_NAME_DUPLICATE | 專案名稱重複 | 409 | 同一團隊內專案名稱重複 |
| **9002** | PROJECT_MAX_MEMBERS | 專案成員數量已達上限 | 422 | 專案成員數限制 |
| **9101** | TASK_PARENT_INVALID | 無效的父任務 | 400 | 父任務不存在或不合法 |
| **9102** | TASK_CIRCULAR_DEPENDENCY | 任務循環依賴 | 400 | 任務依賴形成循環 |

---

## 📖 使用指引

### 1. 在 API 規格中引用錯誤碼

在每個 [API_Specification_Template.md](API_Specification_Template.md) 的 **Error Responses** 區塊中，必須引用此錯誤碼清單：

```markdown
### Error Responses

| HTTP Status | Error Code | Error Message | 說明 |
|-------------|-----------|---------------|------|
| 401 | 1001 | INVALID_TOKEN | 無效的身份驗證令牌 |
| 403 | 2001 | FORBIDDEN | 使用者無權存取此資源 |
| 400 | 3002 | MISSING_REQUIRED_FIELD | 缺少必填欄位：projectName |
| 404 | 4001 | NOT_FOUND | 找不到指定的專案 |
| 422 | 5001 | BUSINESS_RULE_VIOLATION | 專案開始日期不能晚於結束日期 |

> **參考**: [API_Error_Codes.md](API_Error_Codes.md) 標準錯誤碼清單
```

### 2. 錯誤回應格式標準

**標準錯誤回應結構**:

```json
{
  "status": "error",
  "error": {
    "code": 3002,
    "type": "MISSING_REQUIRED_FIELD",
    "message": "缺少必填欄位",
    "details": "欄位 'projectName' 為必填",
    "field": "projectName",
    "timestamp": "2025-11-25T10:30:00Z",
    "requestId": "req-abc-123"
  }
}
```

**欄位說明**:
- `code`: 數字錯誤碼（1000-9999）
- `type`: 錯誤代號（大寫英文，便於程式處理）
- `message`: 使用者友善的錯誤訊息（支持多語言）
- `details`: 詳細錯誤說明（可選）
- `field`: 相關欄位名稱（驗證錯誤時使用，可選）
- `timestamp`: 錯誤發生時間
- `requestId`: 請求追蹤 ID（用於除錯）

### 3. 前端錯誤處理範例

**JavaScript/TypeScript 範例**:

```typescript
// 根據錯誤碼範圍統一處理
function handleApiError(error: ApiError) {
  const code = error.code;

  if (code >= 1000 && code < 2000) {
    // 認證錯誤 - 導向登入頁
    redirectToLogin();
  } else if (code >= 2000 && code < 3000) {
    // 授權錯誤 - 顯示權限不足訊息
    showPermissionDeniedMessage();
  } else if (code >= 3000 && code < 4000) {
    // 驗證錯誤 - 顯示表單驗證訊息
    showValidationError(error.field, error.message);
  } else if (code >= 4000 && code < 5000) {
    // 資源錯誤 - 顯示資源相關錯誤
    showResourceError(error.message);
  } else if (code >= 7000 && code < 8000) {
    // 系統錯誤 - 顯示系統錯誤並通知技術團隊
    showSystemError();
    reportToErrorTracking(error);
  }
}
```

### 4. 新增自定義錯誤碼流程

1. **選擇範圍**: 在 9000-9999 範圍內選擇未使用的錯誤碼
2. **定義錯誤**: 在此文檔的「自定義業務錯誤」區塊新增
3. **更新 API 規格**: 在相關 API_Specification_Template.md 中引用
4. **實作**: 在後端實作錯誤回應
5. **前端處理**: 在前端新增對應的錯誤處理邏輯

---

## ✅ 檢查清單

使用此錯誤碼清單時，請確認以下項目：

**建立新 API 規格時**:
- [ ] 是否在 Error Responses 區塊引用標準錯誤碼？
- [ ] 是否遵循標準錯誤回應格式？
- [ ] 是否為每個錯誤情境選擇適當的錯誤碼？
- [ ] 是否提供清晰的錯誤訊息和 details？

**新增自定義錯誤碼時**:
- [ ] 是否在 9000-9999 範圍內選擇？
- [ ] 是否避免與現有錯誤碼衝突？
- [ ] 是否更新此文檔記錄新錯誤碼？
- [ ] 是否通知前端團隊新增錯誤處理？

**錯誤處理實作時**:
- [ ] 是否使用標準錯誤回應格式？
- [ ] 是否包含 requestId 便於追蹤？
- [ ] 是否在日誌中記錄完整錯誤資訊？
- [ ] 是否對敏感錯誤訊息進行脫敏？

---

## 📚 相關文檔

- [API_Specification_Template.md](API_Specification_Template.md) - API 規格範本
- [API_Index_Template.md](API_Index_Template.md) - API 索引範本
- [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md) - ID 命名規範

---

## 📝 版本更新記錄

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v0.01 | 2025-11-25 | AISDLC Team | **初版建立**：<br>- 定義 9 個主要錯誤碼範圍（1000-9999）<br>- 提供 60+ 個標準錯誤碼<br>- 包含使用指引和前端處理範例<br>- 定義標準錯誤回應格式<br>- **修正問題 #9 (Stage 7-8)**: 錯誤碼未系統化定義 |

---

**文檔結束 (End of Document)**
