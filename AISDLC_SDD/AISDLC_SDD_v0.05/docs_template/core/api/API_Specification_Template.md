# RESTful API 規格文件 - [API 名稱]

**版本**: v0.01
**適用情境**: All Scenarios with API (Greenfield, Brownfield, Integration)
**負責 Agent**: sd-architect, integration-specialist
**產出時機**: API 設計階段

---

## 📋 文件資訊

> 📋 **ID 命名規範**: 使用 [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
> - **API ID**: API-XXX (API 規格)
> - 格式：API-001, API-002, API-101, API-102
> - 建議編號規則：
>   - API-001~099: 使用者相關 API
>   - API-101~199: 交易/業務邏輯 API
>   - API-201~299: 資料查詢 API
>   - API-301~399: 系統管理 API

| 項目 | 內容 |
| --- | --- |
| 文件名稱 | [API名稱] 規格文件 |
| **API ID** | **API-XXX** (依照 AISDLC ID 命名規範) |
| 版本 | v1.0 |
| 最後更新日期 | [YYYY-MM-DD] |
| 作者 | [系統架構師] |
| 審查人 | [Tech Lead] |
| 狀態 | [草稿/審查中/已批准] |
| **對應需求追蹤** | **F-XXX** (PRD) → **BR-XXX** (FRD) → **US-XXX** (User Story) → **AC-XXX-Y** (Acceptance Criteria) |

---

## 修訂歷史

| 版本 | 日期 | 作者 | 修改內容 |
| --- | --- | --- | --- |
| v0.1 | [日期] | [系統架構師] | 初版建立 |
| v1.0 | [日期] | [系統架構師] | 技術審查通過 |

---

## 摘要

此文件定義了 [API名稱] 的規格，API 規格為 RESTful。該 API 用於 [API主要功能描述]。

**對應業務需求追蹤鏈**：

```
F-XXX (功能需求 - PRD)
  └─ BR-XXX (業務規則 - FRD)
      └─ EPIC-XXX (Epic)
          └─ US-XXX (User Story)
              ├─ AC-XXX-1 (Acceptance Criteria 1)
              ├─ AC-XXX-2 (Acceptance Criteria 2)
              └─ AC-XXX-3 (Acceptance Criteria 3)
                  └─ API-XXX (本 API)
                      └─ TC-XXX-Y-Z (測試案例)
```

**需求對應說明**：
- **Feature**: [F-XXX](../../core/prd/PRD_Universal_Template.md#f-xxx) - [功能名稱]
- **Business Rule**: [BR-XXX](../../core/frd/FRD_Universal_Template.md#br-xxx) - [業務規則名稱]
- **Epic**: [EPIC-XXX](../../scenario_specific/xxx/Epic_XXX.md) - [Epic 名稱]
- **User Story**: [US-XXX](../../scenario_specific/xxx/UserStory_XXX.md) - [Story 名稱]
- **Acceptance Criteria**: [AC-XXX-Y](../../scenario_specific/xxx/UserStory_XXX.md#ac-xxx-y) - [驗收條件]

**API 基本資訊**：
- **HTTP Method**: GET / POST / PUT / DELETE / PATCH
- **Endpoint**: `/api/v1/[resource]`
- **描述**: [API 功能簡述]
- **權限要求**: [需要的角色或權限]

---

## 1. 基本資訊

### 1.1 環境資訊

| 環境 | API 基礎路徑 (Base URL) | 備註 |
| --- | --- | --- |
| 開發環境 (Development) | https://dev-api.example.com/v1 | 本地開發測試 |
| 測試環境 (Staging) | https://staging-api.example.com/v1 | QA 測試環境 |
| 生產環境 (Production) | https://api.example.com/v1 | 正式環境 |

### 1.2 通用規範

- **協議**: HTTPS (強制)
- **API 格式**: RESTful
- **內容類型**: JSON (application/json)
- **字元編碼**: UTF-8
- **API URL 格式**: `[protocol]://[host]/[version]/[resource-path]`
  > 例如：`https://api.example.com/v1/users/123`

### 1.3 命名規範

- **URI 路徑**: 小寫英文字母，使用連字符 `-` 分隔
- **資源名稱**: 使用名詞複數形式（如 `/users`, `/products`）
- **查詢參數**: 駝峰式命名（camelCase）
- **JSON 屬性名稱**: 駝峰式命名（camelCase）

### 1.4 日期時間格式

- **日期時間格式**: 遵循 ISO 8601 標準
- **完整日期時間**: `YYYY-MM-DDThh:mm:ss.sssZ` (例如：`2024-07-23T22:26:54.474Z`)
- **純日期**: `YYYY-MM-DD` (例如：`2024-11-22`)
- **時區**: 統一使用 UTC

---

## 2. 認證與授權

### 2.1 認證方式

API 使用 **Bearer Token** 認證機制，客戶端在每次請求時需在 HTTP Header 中加入授權資訊：

```http
Authorization: Bearer {access_token}
```

#### Token 獲取流程
1. 用戶透過 `/auth/login` 端點登入
2. 系統返回 `access_token` 和 `refresh_token`
3. 後續請求攜帶 `access_token` 於 Header
4. Token 過期時使用 `refresh_token` 更新

#### Token 生命週期
- **Access Token**: 有效期 1 小時
- **Refresh Token**: 有效期 7 天

### 2.2 使用者角色

| 角色 | 描述 | 權限範圍 | 此 API 權限 |
| --- | --- | --- | --- |
| Admin | 系統管理員 | 全部功能 | 讀寫刪 |
| User | 一般用戶 | 基本功能 | 讀寫自己的資料 |
| Guest | 訪客 | 僅瀏覽 | 唯讀 |

### 2.3 權限檢查

此 API 的權限要求：
- **最低角色要求**: [User/Admin/Guest]
- **額外權限**: [若有特殊權限需求]
- **資源擁有者**: [是否僅能操作自己的資源]

---

## 3. API 詳細說明

### 3.1 端點資訊

**端點**: `[HTTP方法] /api/v1/[resource-path]`

**HTTP 方法**: [GET/POST/PUT/PATCH/DELETE]

**完整 URL**: `https://api.example.com/v1/[resource-path]`

**描述**: [API 詳細功能描述]

**對應需求**:
- [US-XXX](../../frd/FRD_模組.md#us-xxx): [需求簡述]
- [AC-XXX-Y](../../frd/FRD_模組.md#ac-xxx-y): [驗收標準]

**業務場景**: [說明此 API 在什麼業務場景下被調用]

---

### 3.2 請求規格

#### 請求標頭 (Request Headers)

| 標頭名稱 | 必填 | 值 | 說明 |
| --- | --- | --- | --- |
| Content-Type | 是 | application/json | 請求內容類型 |
| Authorization | 是/否 | Bearer {access_token} | 認證 Token |
| X-Request-ID | 否 | UUID | 請求追蹤 ID |

#### 路徑參數 (Path Parameters)

| 參數名 | 類型 | 必填 | 說明 | 範例值 |
| --- | --- | --- | --- | --- |
| id | string/UUID | 是 | 資源 ID | `123` 或 `550e8400-e29b-41d4-a716-446655440000` |

#### 查詢參數 (Query Parameters)

| 參數名 | 類型 | 必填 | 說明 | 範例值 | 預設值 |
| --- | --- | --- | --- | --- | --- |
| page | integer | 否 | 頁碼 | `1` | `1` |
| pageSize | integer | 否 | 每頁筆數 | `20` | `10` |
| sort | string | 否 | 排序欄位 | `createdAt:desc` | - |
| filter | string | 否 | 過濾條件 | `status:active` | - |

#### 請求主體 (Request Body)

**Content-Type**: `application/json`

**Schema** (TypeScript):
```typescript
interface RequestBody {
  field1: string;      // 必填，說明
  field2: number;      // 選填，說明
  field3?: boolean;    // 選填，說明
}
```

**Schema** (Java/Spring Boot - 擇一使用):
```java
public record ResourceRequest(
    @NotBlank @Size(max = 255) String field1,  // 必填，說明
    @Min(1) @Max(100) Integer field2,          // 選填，說明
    Boolean field3                              // 選填，說明
) {}
```

**欄位說明**:

| 欄位名 | 類型 | 大小限制 | 必填 | 說明 | 範例值 | 驗證規則 |
| --- | --- | --- | --- | --- | --- | --- |
| field1 | string | 1-255 | 是 | 欄位說明 | `"example"` | 非空、長度限制 |
| field2 | integer | - | 否 | 欄位說明 | `123` | 範圍: 1-100 |
| field3 | boolean | - | 否 | 欄位說明 | `true` | true/false |

---

### 3.3 請求範例

#### cURL
```bash
curl -X POST https://api.example.com/v1/resources \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "field1": "example value",
    "field2": 123,
    "field3": true
  }'
```

#### JavaScript (Fetch API)
```javascript
fetch('https://api.example.com/v1/resources', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + accessToken
  },
  body: JSON.stringify({
    field1: 'example value',
    field2: 123,
    field3: true
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### Python (Requests)
```python
import requests

url = "https://api.example.com/v1/resources"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {access_token}"
}
data = {
    "field1": "example value",
    "field2": 123,
    "field3": True
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

#### Java (Spring Boot RestTemplate / WebClient)
```java
// 方式 1: RestTemplate
RestTemplate restTemplate = new RestTemplate();
HttpHeaders headers = new HttpHeaders();
headers.setContentType(MediaType.APPLICATION_JSON);
headers.setBearerAuth(accessToken);

ResourceRequest request = new ResourceRequest("example value", 123, true);
HttpEntity<ResourceRequest> entity = new HttpEntity<>(request, headers);

ResponseEntity<ApiResponse> response = restTemplate.exchange(
    "https://api.example.com/v1/resources",
    HttpMethod.POST, entity, ApiResponse.class);

// 方式 2: WebClient (響應式，推薦)
WebClient webClient = WebClient.builder()
    .baseUrl("https://api.example.com/v1")
    .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
    .build();

Mono<ApiResponse> response = webClient.post()
    .uri("/resources")
    .bodyValue(new ResourceRequest("example value", 123, true))
    .retrieve()
    .bodyToMono(ApiResponse.class);
```

#### Spring Boot Controller 實作範例
```java
@RestController
@RequestMapping("/api/v1/resources")
@Tag(name = "Resource", description = "資源管理 API")
public class ResourceController {

    @Operation(summary = "[API功能簡述]", description = "[API詳細描述]")
    @ApiResponses({
        @ApiResponse(responseCode = "200", description = "操作成功"),
        @ApiResponse(responseCode = "400", description = "請求參數錯誤"),
        @ApiResponse(responseCode = "401", description = "未認證")
    })
    @PostMapping
    public ResponseEntity<ApiResponse<ResourceDto>> create(
            @Valid @RequestBody ResourceRequest request) {
        ResourceDto result = resourceService.create(request);
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
```

> 💡 **Spring Boot OpenAPI 文檔**: 使用 `springdoc-openapi-starter-webmvc-ui` 自動產生 Swagger UI，
> 訪問 `http://localhost:8080/swagger-ui.html` 查看互動式 API 文檔。

---

### 3.4 回應規格

#### 回應格式

所有 API 回應遵循統一格式：

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    // 實際資料
  },
  "timestamp": "2024-01-01T12:00:00.000Z",
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

| 欄位 | 類型 | 說明 |
| --- | --- | --- |
| code | integer | HTTP 狀態碼 |
| message | string | 回應訊息 |
| data | object/array | 回應資料主體 |
| timestamp | string (ISO 8601) | 伺服器時間戳 |
| requestId | string (UUID) | 請求追蹤 ID |

#### 成功回應 (2xx)

**HTTP Status Code**: `200 OK` / `201 Created`

**回應資料結構 (Response Data Schema)**:

```typescript
interface ResponseData {
  id: string;          // 資源 ID
  field1: string;      // 欄位說明
  field2: number;      // 欄位說明
  createdAt: string;   // ISO 8601 格式
  updatedAt: string;   // ISO 8601 格式
}
```

**欄位說明**:

| 欄位名稱 | 類型 | 說明 | 範例值 |
| --- | --- | --- | --- |
| id | string (UUID) | 資源唯一識別碼 | `"550e8400-e29b-41d4-a716-446655440000"` |
| field1 | string | 欄位說明 | `"example value"` |
| field2 | number | 欄位說明 | `123` |
| createdAt | string | 創建時間 | `"2024-01-01T12:00:00.000Z"` |
| updatedAt | string | 最後更新時間 | `"2024-01-01T12:30:00.000Z"` |

#### 成功回應範例

```json
{
  "code": 200,
  "message": "Resource created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "field1": "example value",
    "field2": 123,
    "field3": true,
    "createdAt": "2024-01-01T12:00:00.000Z",
    "updatedAt": "2024-01-01T12:00:00.000Z"
  },
  "timestamp": "2024-01-01T12:00:00.000Z",
  "requestId": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### 分頁回應範例 (若適用)

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "items": [
      { "id": "1", "name": "Item 1" },
      { "id": "2", "name": "Item 2" }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 10,
      "totalPages": 5,
      "totalItems": 50,
      "hasNext": true,
      "hasPrev": false
    }
  },
  "timestamp": "2024-01-01T12:00:00.000Z",
  "requestId": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

## 4. 狀態碼與錯誤處理

### 4.1 成功狀態碼

| 狀態碼 | 說明 | 使用場景 |
| --- | --- | --- |
| 200 OK | 成功 | GET, PUT, PATCH 成功 |
| 201 Created | 已創建 | POST 創建資源成功 |
| 204 No Content | 無內容 | DELETE 成功 |

### 4.2 客戶端錯誤狀態碼 (4xx)

| 狀態碼 | 說明 | 常見原因 | 解決方案 |
| --- | --- | --- | --- |
| 400 Bad Request | 請求參數錯誤 | 缺少必填欄位、格式錯誤 | 檢查請求參數 |
| 401 Unauthorized | 授權失敗 | Token 缺失或無效 | 重新登入獲取 Token |
| 403 Forbidden | 無使用權限 | 角色權限不足 | 聯繫管理員 |
| 404 Not Found | 找不到對應項目 | 資源不存在 | 確認資源 ID |
| 409 Conflict | 資源衝突 | 重複創建、版本衝突 | 檢查資源狀態 |
| 422 Unprocessable Entity | 無法處理的實體 | 業務邏輯驗證失敗 | 檢查業務規則 |
| 429 Too Many Requests | 請求過於頻繁 | 超過 Rate Limit | 降低請求頻率 |

### 4.3 伺服器錯誤狀態碼 (5xx)

| 狀態碼 | 說明 | 常見原因 | 解決方案 |
| --- | --- | --- | --- |
| 500 Internal Server Error | 系統錯誤 | 伺服器異常 | 聯繫技術支援 |
| 502 Bad Gateway | 閘道錯誤 | 上游服務異常 | 稍後重試 |
| 503 Service Unavailable | 服務不可用 | 系統維護中 | 等待維護完成 |
| 504 Gateway Timeout | 閘道超時 | 請求處理超時 | 稍後重試 |

### 4.4 錯誤回應格式

```json
{
  "code": 400,
  "message": "Validation failed",
  "errors": [
    {
      "field": "field1",
      "message": "Field1 is required",
      "code": "REQUIRED_FIELD"
    },
    {
      "field": "field2",
      "message": "Field2 must be between 1 and 100",
      "code": "OUT_OF_RANGE"
    }
  ],
  "timestamp": "2024-01-01T12:00:00.000Z",
  "requestId": "123e4567-e89b-12d3-a456-426614174000"
}
```

### 4.5 錯誤碼清單

> **📚 參考**: 請參照 [API_Error_Codes.md](API_Error_Codes.md) **標準錯誤碼清單**，使用系統化定義的錯誤碼範圍（1000-9999）。

**本 API 使用的錯誤碼**（請根據實際情況填寫）：

| 錯誤碼 | 錯誤代號 | HTTP 狀態 | 說明 | 處理建議 |
| --- | --- | --- | --- | --- |
| 1001 | INVALID_TOKEN | 401 | 無效的身份驗證令牌 | 重新登入獲取有效 Token |
| 1002 | EXPIRED_TOKEN | 401 | 令牌已過期 | 刷新 Token 或重新登入 |
| 2001 | FORBIDDEN | 403 | 拒絕存取 | 確認使用者權限 |
| 2002 | INSUFFICIENT_ROLE | 403 | 角色權限不足 | 聯繫管理員提升權限 |
| 3001 | VALIDATION_ERROR | 400 | 資料驗證失敗 | 根據 errors 欄位修正輸入 |
| 3002 | MISSING_REQUIRED_FIELD | 400 | 缺少必填欄位 | 補充缺失的必填欄位 |
| 4001 | NOT_FOUND | 404 | 資源不存在 | 確認資源 ID 是否正確 |
| 4002 | ALREADY_EXISTS | 409 | 資源已存在 | 使用現有資源或檢查唯一性條件 |
| 5001 | BUSINESS_RULE_VIOLATION | 422 | 違反業務規則 | 檢查業務邏輯條件 |
| 7001 | INTERNAL_SERVER_ERROR | 500 | 內部伺服器錯誤 | 聯繫技術支援團隊 |

**自定義錯誤碼**（9000-9999 範圍）：

| 錯誤碼 | 錯誤代號 | HTTP 狀態 | 說明 | 處理建議 |
| --- | --- | --- | --- | --- |
| 9xxx | CUSTOM_ERROR_NAME | 4xx/5xx | [自定義錯誤說明] | [處理建議] |

> **💡 提示**:
> - 錯誤碼範圍說明：1000-1999 認證 / 2000-2999 授權 / 3000-3999 驗證 / 4000-4999 資源 / 5000-5999 業務邏輯 / 7000-7999 系統 / 9000-9999 自定義
> - 新增自定義錯誤碼時，請同步更新 [API_Error_Codes.md](API_Error_Codes.md)

---

## 5. 業務邏輯與規則

### 5.1 業務規則
- [規則 1]: [描述業務規則]
- [規則 2]: [描述業務規則]

### 5.2 資料驗證規則
- [驗證規則 1]: [描述驗證邏輯]
- [驗證規則 2]: [描述驗證邏輯]

### 5.3 特殊處理邏輯
- [特殊情境 1]: [處理方式]
- [特殊情境 2]: [處理方式]

---

## 6. 效能與限制

### 6.1 Rate Limiting（頻率限制）

> **📋 為什麼需要 Rate Limiting？**
>
> Rate Limiting（頻率限制）是 API 設計的關鍵機制，用於：
> - 🛡️ **防止濫用**：限制惡意使用者或機器人的攻擊（DDoS、爬蟲）
> - ⚖️ **資源公平分配**：確保所有使用者都能獲得合理的服務品質
> - 💰 **成本控制**：防止單一使用者消耗過多伺服器資源
> - 📈 **服務穩定性**：避免系統過載，維持高可用性

---

#### 6.1.1 Rate Limiting 策略

**採用策略**: [請選擇以下策略之一或組合]

| 策略類型 | 說明 | 適用場景 | 範例 |
|---------|------|---------|------|
| **固定視窗 (Fixed Window)** | 在固定時間視窗內限制請求次數 | 簡單場景，精確度要求不高 | 每分鐘 100 次 |
| **滑動視窗 (Sliding Window)** | 動態計算過去 N 秒的請求次數 | 需要更精確的限流控制 | 過去 60 秒內 100 次 |
| **令牌桶 (Token Bucket)** | 以固定速率補充令牌，支援 burst | 允許短時間突發流量 | 速率 10 req/s，桶容量 50 |
| **漏桶 (Leaky Bucket)** | 以固定速率處理請求，平滑流量 | 需要穩定的輸出速率 | 固定每秒處理 10 個請求 |

**本 API 採用**: [固定視窗 / 滑動視窗 / 令牌桶 / 漏桶]

---

#### 6.1.2 頻率限制規則

**基礎限制**（所有使用者）：

| 時間視窗 | 請求限制 | 適用範圍 |
|---------|---------|---------|
| **每秒** | [10] 次 | 所有 API endpoint |
| **每分鐘** | [100] 次 | 所有 API endpoint |
| **每小時** | [1,000] 次 | 所有 API endpoint |
| **每天** | [10,000] 次 | 所有 API endpoint |

**分層限制**（依使用者等級）：

| 使用者等級 | 每分鐘 | 每小時 | 每天 | 說明 |
|-----------|-------|-------|------|------|
| **Free Tier** | 60 次 | 1,000 次 | 10,000 次 | 免費使用者 |
| **Basic Plan** | 300 次 | 5,000 次 | 50,000 次 | 付費基礎方案 |
| **Pro Plan** | 1,000 次 | 20,000 次 | 200,000 次 | 付費專業方案 |
| **Enterprise** | 無限制 | 無限制 | 無限制 | 企業方案（需聯繫客服） |

**特定 Endpoint 限制**：

| Endpoint | 限制 | 原因 |
|----------|------|------|
| `POST /api/auth/login` | 5 次/分鐘（每 IP） | 防止暴力破解 |
| `POST /api/auth/register` | 3 次/小時（每 IP） | 防止大量註冊 |
| `POST /api/files/upload` | 10 次/小時 | 上傳頻寬限制 |
| `GET /api/reports/export` | 5 次/小時 | 伺服器運算成本高 |

---

#### 6.1.3 Burst（突發流量）處理

**Burst 定義**: 允許短時間內超過平均速率的請求，適用於突發性需求。

**Burst 配置**:

| 參數 | 值 | 說明 |
|------|------|------|
| **Burst 容量** | [50] 次 | 允許的突發請求總數 |
| **Burst 時間視窗** | [10] 秒 | 突發流量的時間視窗 |
| **補充速率** | [5] 次/秒 | Burst 容量的恢復速率 |

**Burst 範例**（令牌桶）:
```
配置：
- 桶容量：50 個令牌
- 補充速率：5 令牌/秒
- 每個請求消耗 1 個令牌

場景：
- 使用者突然發送 50 個請求（0-1 秒）→ ✅ 全部通過（消耗 50 個令牌）
- 第 51-60 個請求（1-2 秒）→ ❌ 被限制（令牌已用完）
- 10 秒後 → ✅ 恢復 50 個令牌（5 令牌/秒 × 10 秒）
```

**Burst 與基礎限制的關係**:
- ✅ **Burst 優先**: 優先消耗 Burst 容量
- ⚠️ **基礎限制兜底**: Burst 用完後，回到基礎限制（如每秒 10 次）
- 🔄 **動態恢復**: Burst 容量以固定速率恢復

---

#### 6.1.4 Quota（配額）管理

**Quota 定義**: 長期（月度/年度）的請求總量限制，用於商業計費。

**月度 Quota**:

| 使用者等級 | 月度 Quota | 超額處理 | 計費 |
|-----------|-----------|---------|------|
| **Free Tier** | 100,000 次 | 封鎖至下月 | 免費 |
| **Basic Plan** | 1,000,000 次 | 超額計費：$0.01/次 | $10/月 |
| **Pro Plan** | 10,000,000 次 | 超額計費：$0.005/次 | $50/月 |
| **Enterprise** | 自訂 Quota | 自訂計費方案 | 聯繫客服 |

**Quota 重置**:
- **重置時機**: 每月 1 號 00:00 UTC
- **重置通知**: 提前 3 天發送 Email 通知（當使用量 > 80%）
- **超額警告**: 使用量達 90% 時發送警告

**Quota 與 Rate Limiting 的關係**:
- **Rate Limiting**: 短期限制（秒/分鐘/小時），防止瞬間過載
- **Quota**: 長期限制（月/年），用於商業計費和成本控制
- **雙重檢查**: 請求需同時通過 Rate Limiting 和 Quota 檢查

---

#### 6.1.5 Penalty（懲罰機制）

**觸發條件**:

| 違規行為 | 懲罰措施 | 持續時間 |
|---------|---------|---------|
| **輕度違規** - 超過限制 1-10% | 降低 Rate Limit 至 50% | 15 分鐘 |
| **中度違規** - 超過限制 10-50% | 降低 Rate Limit 至 20% | 1 小時 |
| **重度違規** - 超過限制 50%+ 或持續違規 | 臨時封鎖 API 存取 | 24 小時 |
| **惡意行為** - 嘗試繞過限制、DDoS 攻擊 | 永久封鎖 + 法律行動 | 永久 |

**Penalty 實施流程**:
1. **檢測違規**: 系統自動監控請求模式
2. **記錄日誌**: 記錄違規行為（時間、IP、User ID、請求內容）
3. **發送警告**: 第一次違規發送 Email 警告（包含違規詳情）
4. **執行懲罰**: 第二次違規開始執行 Penalty
5. **申訴機制**: 使用者可透過客服申訴（需說明原因）

**Penalty 恢復**:
- **自動恢復**: 懲罰期滿後自動恢復正常 Rate Limit
- **人工審查**: 重度違規需人工審查後才能解除
- **黑名單管理**: 惡意使用者永久加入黑名單（IP + User ID）

**範例場景**:
```
場景 1: 輕度違規
- 使用者 A（Basic Plan）: 每分鐘限制 300 次
- 實際請求: 330 次/分鐘（超過 10%）
- 系統回應:
  - 發送 Email 警告：「您在過去 1 分鐘內超過限制 10%」
  - 懲罰: 降低 Rate Limit 至 150 次/分鐘（50%）
  - 持續: 15 分鐘後自動恢復

場景 2: 中度違規
- 使用者 B（Pro Plan）: 每分鐘限制 1,000 次
- 實際請求: 1,500 次/分鐘（超過 50%）
- 系統回應:
  - 發送 Email 警告：「您已嚴重超過限制，請檢查您的應用程式」
  - 懲罰: 降低 Rate Limit 至 200 次/分鐘（20%）
  - 持續: 1 小時後自動恢復

場景 3: 重度違規
- 使用者 C: 持續 10 分鐘超過限制 100%+
- 系統回應:
  - 臨時封鎖 API 存取（返回 HTTP 403）
  - 發送 Email：「您的帳號因違反使用條款已被暫時停用」
  - 持續: 24 小時，需聯繫客服解除
```

---

#### 6.1.6 Response Headers（回應標頭）

**標準 Rate Limiting Headers**:

| Header 名稱 | 說明 | 範例值 |
|------------|------|-------|
| `X-RateLimit-Limit` | 限制次數（時間視窗內的總限制） | `100` |
| `X-RateLimit-Remaining` | 剩餘次數（時間視窗內還可請求的次數） | `75` |
| `X-RateLimit-Reset` | 重置時間（Unix timestamp，秒） | `1700000000` |
| `X-RateLimit-Reset-After` | 距離重置的秒數 | `45` |
| `X-RateLimit-Window` | 時間視窗（秒） | `60` |
| `X-RateLimit-Policy` | 限制策略 | `fixed-window` / `sliding-window` / `token-bucket` |

**Burst 相關 Headers**:

| Header 名稱 | 說明 | 範例值 |
|------------|------|-------|
| `X-RateLimit-Burst-Limit` | Burst 容量 | `50` |
| `X-RateLimit-Burst-Remaining` | Burst 剩餘容量 | `20` |
| `X-RateLimit-Burst-Reset` | Burst 完全恢復的時間 | `1700000100` |

**Quota 相關 Headers**:

| Header 名稱 | 說明 | 範例值 |
|------------|------|-------|
| `X-RateLimit-Quota-Limit` | 月度 Quota 總量 | `1000000` |
| `X-RateLimit-Quota-Remaining` | 月度 Quota 剩餘量 | `750000` |
| `X-RateLimit-Quota-Reset` | Quota 重置時間（下月 1 號） | `1704067200` |

**Penalty 相關 Headers**（違規時）:

| Header 名稱 | 說明 | 範例值 |
|------------|------|-------|
| `X-RateLimit-Penalty-Applied` | 是否正在懲罰 | `true` |
| `X-RateLimit-Penalty-Expires` | 懲罰解除時間 | `1700000900` |
| `X-RateLimit-Penalty-Reason` | 懲罰原因 | `exceeded-limit-50-percent` |

---

#### 6.1.7 超限回應（HTTP 429）

**HTTP 狀態碼**: `429 Too Many Requests`

**回應範例**:

**基礎限制超限**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "您已超過每分鐘 100 次的請求限制",
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset": 1700000000,
      "reset_after": 45,
      "retry_after": 45
    }
  }
}
```

**Quota 超限**:
```json
{
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "您已用完本月的 1,000,000 次請求配額",
    "details": {
      "quota_limit": 1000000,
      "quota_used": 1000000,
      "quota_reset": 1704067200,
      "upgrade_url": "https://example.com/pricing"
    }
  }
}
```

**Penalty 封鎖**:
```json
{
  "error": {
    "code": "RATE_LIMIT_PENALTY",
    "message": "您的帳號因違反使用條款暫時被停用",
    "details": {
      "penalty_applied": true,
      "penalty_reason": "exceeded-limit-50-percent",
      "penalty_expires": 1700000900,
      "contact_support": "support@example.com"
    }
  }
}
```

**Response Headers 範例**（HTTP 429）:
```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1700000000
X-RateLimit-Reset-After: 45
Retry-After: 45

{
  "error": { ... }
}
```

---

#### 6.1.8 客戶端處理建議

**自動重試機制**（Exponential Backoff）:

```javascript
async function apiCallWithRetry(url, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);

      // 成功回應
      if (response.ok) {
        return await response.json();
      }

      // 處理 429 Too Many Requests
      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') ||
                          response.headers.get('X-RateLimit-Reset-After');
        const waitTime = parseInt(retryAfter) || Math.pow(2, attempt) * 1000;

        console.log(`Rate limit exceeded. Retrying after ${waitTime}ms...`);
        await sleep(waitTime);
        continue; // 重試
      }

      // 其他錯誤
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
    }
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

**檢查 Rate Limit 狀態**:

```javascript
function checkRateLimit(response) {
  const limit = response.headers.get('X-RateLimit-Limit');
  const remaining = response.headers.get('X-RateLimit-Remaining');
  const reset = response.headers.get('X-RateLimit-Reset');

  console.log(`Rate Limit: ${remaining}/${limit}`);
  console.log(`Resets at: ${new Date(reset * 1000).toISOString()}`);

  // 警告：剩餘次數 < 10%
  if (remaining / limit < 0.1) {
    console.warn('⚠️ Rate limit almost exhausted! Slow down requests.');
  }
}
```

**Quota 監控**:

```javascript
function checkQuota(response) {
  const quotaLimit = response.headers.get('X-RateLimit-Quota-Limit');
  const quotaRemaining = response.headers.get('X-RateLimit-Quota-Remaining');
  const quotaReset = response.headers.get('X-RateLimit-Quota-Reset');

  const usagePercent = ((quotaLimit - quotaRemaining) / quotaLimit * 100).toFixed(2);

  console.log(`Quota Usage: ${usagePercent}% (${quotaLimit - quotaRemaining}/${quotaLimit})`);

  // 警告：使用量 > 80%
  if (usagePercent > 80) {
    console.warn('⚠️ Monthly quota almost exhausted! Consider upgrading plan.');
  }
}
```

---

#### 6.1.9 測試與監控

**Rate Limiting 測試案例**:

| 測試案例 | 測試步驟 | 預期結果 |
|---------|---------|---------|
| **TC-RL-001: 基礎限制** | 在 1 分鐘內發送 101 次請求 | 前 100 次成功（HTTP 200），第 101 次失敗（HTTP 429）|
| **TC-RL-002: Burst 處理** | 在 1 秒內發送 50 次請求 | 全部成功（消耗 Burst 容量）|
| **TC-RL-003: Quota 檢查** | 使用完月度 Quota 後請求 | 返回 HTTP 429 + `QUOTA_EXCEEDED` |
| **TC-RL-004: Penalty 觸發** | 持續超過限制 50% | 觸發 Penalty，Rate Limit 降至 20% |
| **TC-RL-005: 不同使用者等級** | Free 使用者發送 61 次/分鐘，Pro 使用者發送 1001 次/分鐘 | Free 使用者在第 61 次被限制，Pro 使用者在第 1001 次被限制 |

**監控指標**:

| 指標名稱 | 說明 | 告警閾值 |
|---------|------|---------|
| `rate_limit_exceeded_total` | Rate Limit 被觸發的總次數 | > 1000 次/小時 |
| `quota_exceeded_total` | Quota 用盡的使用者數 | > 10 個/天 |
| `penalty_applied_total` | Penalty 觸發次數 | > 5 次/天 |
| `rate_limit_remaining_avg` | 平均剩餘次數 | < 10%（接近用盡）|
| `burst_usage_percent` | Burst 容量使用率 | > 80% |

**Grafana Dashboard 範例查詢** (Prometheus):

```promql
# Rate Limit 觸發率
rate(rate_limit_exceeded_total[5m])

# Quota 用盡使用者數（按等級）
sum by (user_tier) (quota_exceeded_total)

# Penalty 觸發趨勢
increase(penalty_applied_total[1h])

# 平均剩餘次數比例（按 endpoint）
avg by (endpoint) (rate_limit_remaining / rate_limit_limit)
```

### 6.2 資料大小限制
- **Request Body**: 最大 [10] MB
- **檔案上傳**: 最大 [50] MB
- **批次操作**: 最多 [100] 筆

### 6.3 效能指標
- **回應時間**: 95th percentile ≤ [500] ms
- **可用性**: ≥ 99.9%
- **併發支援**: ≥ [1000] concurrent requests

### 6.4 Pagination（分頁）標準

> **📋 為什麼需要 Pagination 標準？**
>
> Pagination（分頁）是處理大量資料列表的關鍵機制，用於：
> - 🚀 **效能優化**：避免一次載入過多資料，減少記憶體和網路消耗
> - 👤 **使用者體驗**：快速載入首頁資料，提升響應速度
> - 📊 **資料管理**：支援資料瀏覽、排序、篩選等功能
> - 🛡️ **系統穩定性**：防止大量資料查詢導致資料庫或伺服器過載

---

#### 6.4.1 Pagination 策略選擇

**策略比較表**：

| 策略類型 | 說明 | 優點 | 缺點 | 適用場景 |
|---------|------|------|------|---------|
| **Offset-based Pagination** | 使用 `page` 和 `limit` 參數 | 實作簡單、支援跳頁 | 大偏移量效能差、新增資料時頁面內容可能重複 | 一般列表查詢、資料變動不頻繁 |
| **Cursor-based Pagination** | 使用游標（通常是 ID 或時間戳）| 效能穩定、避免重複資料 | 不支援跳頁、實作較複雜 | 即時資料流、社群動態、訊息列表 |
| **Keyset Pagination** | 使用多欄位組合作為游標 | 效能優秀、資料一致性高 | 實作最複雜、需要索引支援 | 大數據量、複雜排序需求 |

**本 API 採用**: [Offset-based / Cursor-based / Keyset] Pagination

---

#### 6.4.2 Offset-based Pagination 標準

**Request 參數**：

| 參數名稱 | 類型 | 必填 | 預設值 | 說明 | 範例 |
|---------|------|------|--------|------|------|
| `page` | integer | 否 | 1 | 頁碼（從 1 開始） | `page=1` |
| `limit` | integer | 否 | 20 | 每頁筆數 | `limit=20` |
| `sort` | string | 否 | createdAt | 排序欄位 | `sort=createdAt` |
| `order` | string | 否 | desc | 排序方向（asc/desc） | `order=desc` |

**參數限制**：
- `page`: 最小值 1，最大值 [1000]
- `limit`: 最小值 1，最大值 [100]（防止一次查詢過多資料）
- `sort`: 僅允許特定欄位排序（如 `createdAt`, `updatedAt`, `name`）
- `order`: 僅允許 `asc` 或 `desc`

**Request 範例**：

```http
GET /api/v1/projects?page=2&limit=20&sort=createdAt&order=desc
Authorization: Bearer {token}
```

**Response 格式**：

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": "proj_001",
        "name": "Project Alpha",
        "createdAt": "2024-01-15T10:30:00Z"
      },
      {
        "id": "proj_002",
        "name": "Project Beta",
        "createdAt": "2024-01-14T15:20:00Z"
      }
    ],
    "pagination": {
      "page": 2,
      "limit": 20,
      "totalItems": 156,
      "totalPages": 8,
      "hasNextPage": true,
      "hasPreviousPage": true
    }
  },
  "timestamp": "2024-01-20T12:00:00.000Z",
  "requestId": "req_123456"
}
```

**Pagination Metadata 欄位說明**：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `page` | integer | 當前頁碼 |
| `limit` | integer | 每頁筆數 |
| `totalItems` | integer | 總筆數 |
| `totalPages` | integer | 總頁數（`Math.ceil(totalItems / limit)`） |
| `hasNextPage` | boolean | 是否有下一頁 |
| `hasPreviousPage` | boolean | 是否有上一頁 |

---

#### 6.4.3 Cursor-based Pagination 標準

> **使用時機**：當資料變動頻繁（如社群動態、即時訊息）或需要無限滾動（Infinite Scroll）時採用

**Request 參數**：

| 參數名稱 | 類型 | 必填 | 預設值 | 說明 | 範例 |
|---------|------|------|--------|------|------|
| `cursor` | string | 否 | null | 游標（上一次回應的 `nextCursor`） | `cursor=eyJpZCI6MTIzfQ==` |
| `limit` | integer | 否 | 20 | 每次載入筆數 | `limit=20` |

**Request 範例**：

```http
GET /api/v1/posts?cursor=eyJpZCI6MTIzLCJ0aW1lIjoxNjQwMDAwMDAwfQ==&limit=20
Authorization: Bearer {token}
```

**Response 格式**：

```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "items": [
      {
        "id": "post_456",
        "content": "Hello World",
        "createdAt": "2024-01-20T10:00:00Z"
      },
      {
        "id": "post_455",
        "content": "Another post",
        "createdAt": "2024-01-20T09:55:00Z"
      }
    ],
    "pagination": {
      "nextCursor": "eyJpZCI6NDU1LCJ0aW1lIjoxNjQwMDAwMDAwfQ==",
      "hasMore": true,
      "limit": 20
    }
  },
  "timestamp": "2024-01-20T12:00:00.000Z",
  "requestId": "req_789012"
}
```

**Cursor 編碼方式**：
- 使用 Base64 編碼的 JSON 物件
- 包含必要的排序欄位（如 `id`, `createdAt`）
- 範例：`{"id": 455, "time": 1640000000}` → Base64 編碼 → `eyJpZCI6NDU1LCJ0aW1lIjoxNjQwMDAwMDAwfQ==`

---

#### 6.4.4 Pagination 最佳實踐

**1. 效能優化**：
- ✅ 在排序欄位建立索引（如 `createdAt`, `updatedAt`）
- ✅ 限制 `limit` 最大值（建議 ≤ 100），防止單次查詢過多資料
- ✅ 使用 `SELECT` 指定欄位，避免 `SELECT *`
- ✅ 快取熱門頁面資料（如首頁、第 1 頁）

**2. 資料一致性**：
- ✅ Offset-based：適合靜態或低頻更新的資料（如商品列表、文章列表）
- ✅ Cursor-based：適合動態資料（如社群動態、即時通知）
- ❌ 避免在高頻插入/刪除的資料集使用 Offset-based（會導致跳頁或重複）

**3. 使用者體驗**：
- ✅ 提供 `totalItems` 和 `totalPages` 讓前端顯示「第 X 頁 / 共 Y 頁」
- ✅ 提供 `hasNextPage` / `hasPreviousPage` 控制「上一頁」/「下一頁」按鈕狀態
- ✅ 支援排序（`sort` 和 `order` 參數）
- ✅ 返回空列表時仍保留 pagination metadata（避免前端錯誤）

**4. 錯誤處理**：
- ✅ `page` 超出範圍：返回空列表，而非 404 錯誤
- ✅ `limit` 超出限制：自動調整為最大值（如 100），並在 response 中說明
- ✅ `cursor` 無效或過期：返回 400 Bad Request，提示重新查詢

**5. API 文檔範例**：

```markdown
### 取得專案列表

**Endpoint**: `GET /api/v1/projects`

**Query Parameters**:
| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 頁碼（1-based） |
| limit | integer | 否 | 20 | 每頁筆數（1-100） |
| sort | string | 否 | createdAt | 排序欄位 |
| order | string | 否 | desc | 排序方向（asc/desc） |

**Response**: 包含 `items` 陣列和 `pagination` 物件
```

---

#### 6.4.5 Pagination 錯誤處理

**錯誤情境與回應**：

| 錯誤情境 | HTTP 狀態碼 | 錯誤碼 | 錯誤訊息 | 處理方式 |
|---------|------------|--------|---------|---------|
| `page` 小於 1 | 400 | INVALID_PAGE | "Page number must be >= 1" | 調整為 `page=1` |
| `limit` 超出範圍 | 400 | INVALID_LIMIT | "Limit must be between 1 and 100" | 調整為允許範圍內 |
| `page` 超出總頁數 | 200 | - | 返回空列表 `items: []` | 前端顯示「無更多資料」 |
| `cursor` 無效 | 400 | INVALID_CURSOR | "Invalid or expired cursor" | 重新查詢第一頁 |
| `sort` 欄位不允許 | 400 | INVALID_SORT_FIELD | "Sort field not supported" | 使用預設排序 |

**錯誤回應範例**：

```json
{
  "code": 400,
  "message": "Invalid pagination parameters",
  "errors": [
    {
      "field": "limit",
      "message": "Limit must be between 1 and 100",
      "value": 150
    }
  ],
  "timestamp": "2024-01-20T12:00:00.000Z",
  "requestId": "req_error_123"
}
```

---

## 7. 安全性考量

### 7.1 資料加密
- **傳輸加密**: 強制 HTTPS (TLS 1.2+)
- **敏感欄位**: [列出需加密的欄位]

### 7.2 輸入驗證
- **XSS 防護**: 所有輸入經過轉義
- **SQL Injection 防護**: 使用 Prepared Statements
- **檔案上傳**: 驗證檔案類型和大小

### 7.3 審計日誌
- **記錄內容**: 請求時間、用戶、操作、結果
- **保留期限**: [90] 天

---

## 8. 測試案例

### 8.1 正常流程測試
- **測試案例 1**: [描述測試場景]
  - 輸入: [測試資料]
  - 預期輸出: [預期結果]

### 8.2 異常流程測試
- **測試案例 2**: [描述異常場景]
  - 輸入: [測試資料]
  - 預期錯誤: [錯誤碼和訊息]

### 8.3 邊界條件測試
- **測試案例 3**: [描述邊界場景]

---

## 9. 注意事項

### 9.1 重要提醒
- [特殊注意事項 1]
- [特殊注意事項 2]

### 9.2 最佳實踐
- [建議做法 1]
- [建議做法 2]

### 9.3 常見問題
- **Q**: [常見問題 1]
- **A**: [解答]

---

## 10. 相關文檔連結

### 上游文檔
- **需求文檔**: [FRD_模組.md](../../frd/FRD_模組.md)
- **系統設計**: [SRD_模組.md](../SRD_模組.md)

### 相關 API
- **相關 API 1**: [API_Module_Another.md](./API_Module_Another.md)
- **相關 API 2**: [API_Module_Related.md](./API_Module_Related.md)

### 測試文檔
- **驗收測試**: [AT_模組.md](../../tests/AT_模組.md)
- **API 測試集**: [Postman Collection](./postman/collection.json)

---

## 📝 範本版本更新記錄

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v0.01 | 2025-11-25 | AISDLC Team | **修正問題 #9 (Stage 7-8)**: 錯誤碼未系統化定義<br>- 新增「4.5 錯誤碼清單」引用 API_Error_Codes.md<br>- 提供標準錯誤碼範圍說明（1000-9999）<br>- 新增自定義錯誤碼（9000-9999）使用指引 |
| v0.01 | 2025-10-22 | AISDLC Team | 初版範本建立 |

---

**文檔版本**: AISDLC-SDD v0.01
**模板維護**: AISDLC Framework Team
**最後更新**: 2025-11-25
