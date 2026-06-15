# SSE (Server-Sent Events) API 規格文件 - [SSE 名稱]

**版本**: v0.01
**適用情境**: Server Push Scenarios (Greenfield, Brownfield, Integration)
**負責 Agent**: sd-architect, integration-specialist
**產出時機**: SSE API 設計階段

---

## 📋 文件資訊

> 📋 **ID 命名規範**: 使用 [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
> - **SSE API ID**: SSE-XXX (Server-Sent Events 規格)
> - 格式：SSE-001, SSE-002, SSE-101, SSE-102
> - 建議編號規則：
>   - SSE-001~099: 通知推送 SSE
>   - SSE-101~199: 數據更新推送 SSE
>   - SSE-201~299: 進度更新 SSE
>   - SSE-301~399: 即時監控 SSE

| 項目 | 內容 |
| --- | --- |
| 文件名稱 | [SSE名稱] 規格文件 |
| **SSE ID** | **SSE-XXX** (依照 AISDLC ID 命名規範) |
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

此文件定義了 [SSE名稱] 的規格，該 SSE 用於 [主要功能描述：如即時進度推送、數據更新通知、系統狀態監控等]。

**SSE vs WebSocket 比較**：

| 特性 | SSE | WebSocket |
|------|-----|-----------|
| **通訊方向** | 單向（伺服器 → 客戶端） | 雙向（全雙工） |
| **協議** | HTTP/HTTPS（標準 HTTP） | WS/WSS（獨立協議） |
| **連接複雜度** | 簡單（基於 HTTP） | 較複雜（需握手升級） |
| **自動重連** | 瀏覽器原生支持 | 需手動實作 |
| **適用場景** | 通知推送、數據更新、進度追蹤 | 即時聊天、協作編輯、遊戲 |
| **瀏覽器支持** | 所有現代瀏覽器（IE 除外） | 所有現代瀏覽器 |

**對應業務需求追蹤鏈**：

```
F-XXX (功能需求 - PRD)
  └─ BR-XXX (業務規則 - FRD)
      └─ EPIC-XXX (Epic)
          └─ US-XXX (User Story)
              ├─ AC-XXX-1 (Acceptance Criteria 1)
              ├─ AC-XXX-2 (Acceptance Criteria 2)
              └─ AC-XXX-3 (Acceptance Criteria 3)
                  └─ SSE-XXX (本 SSE)
                      └─ TC-XXX-Y-Z (測試案例)
```

**需求對應說明**：
- **Feature**: [F-XXX](../../core/prd/PRD_Universal_Template.md#f-xxx) - [功能名稱]
- **Business Rule**: [BR-XXX](../../core/frd/FRD_Universal_Template.md#br-xxx) - [業務規則名稱]
- **Epic**: [EPIC-XXX](../../scenario_specific/xxx/Epic_XXX.md) - [Epic 名稱]
- **User Story**: [US-XXX](../../scenario_specific/xxx/UserStory_XXX.md) - [Story 名稱]
- **Acceptance Criteria**: [AC-XXX-Y](../../scenario_specific/xxx/UserStory_XXX.md#ac-xxx-y) - [驗收條件]

**SSE 基本資訊**：
- **HTTP Method**: GET (標準 SSE 使用 GET)
- **Endpoint**: `/api/v1/sse/[stream-name]`
- **描述**: [SSE 功能簡述]
- **權限要求**: [需要的角色或權限]
- **連接類型**: 單向推送（Server → Client）

---

## 1. 基本資訊

### 1.1 環境資訊

| 環境 | SSE 端點 (Endpoint) | 備註 |
| --- | --- | --- |
| 開發環境 (Development) | https://dev-api.example.com/v1/sse | 本地開發測試 |
| 測試環境 (Staging) | https://staging-api.example.com/v1/sse | QA 測試環境 |
| 生產環境 (Production) | https://api.example.com/v1/sse | 正式環境 |

### 1.2 通用規範

- **協議**: HTTPS (強制)
- **HTTP Method**: GET
- **Content-Type**: `text/event-stream`
- **字元編碼**: UTF-8
- **Cache-Control**: `no-cache` (禁止快取)
- **Connection**: `keep-alive` (保持連接)
- **SSE URL 格式**: `https://[host]/[version]/sse/[stream-name]?[auth-params]`
  > 例如：`https://api.example.com/v1/sse/notifications?token=xxx`

### 1.3 SSE 訊息格式規範

**標準 SSE 訊息結構**：

```
event: event_name
id: message_id
retry: 3000
data: {"key": "value"}

```

**欄位說明**：
- `event`: 事件類型（選填，預設為 `message`）
- `id`: 訊息唯一識別碼（選填，用於重連時恢復）
- `retry`: 重連間隔（毫秒，選填，建議 3000ms）
- `data`: 數據內容（必填，可多行，以空行結束）

**data 欄位 JSON 格式**：

```json
{
  "type": "notification",
  "timestamp": "2025-11-25T10:30:00Z",
  "payload": {
    "title": "標題",
    "content": "內容"
  }
}
```

---

## 2. 連接管理

### 2.1 連接建立

**連接 URL**:
```
GET https://api.example.com/v1/sse/notifications?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Request Headers**:
```
Accept: text/event-stream
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Cache-Control: no-cache
```

**成功回應 Headers**:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**連接成功初始訊息**:
```
event: connected
id: conn-001
data: {"status": "connected", "connectionId": "conn-abc-123", "serverTime": "2025-11-25T10:30:00Z"}

```

**連接失敗回應**:
```
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "code": 1001,
  "message": "無效的身份驗證令牌"
}
```

### 2.2 心跳機制 (Heartbeat)

**目的**: 保持 HTTP 連接活躍，防止代理伺服器或防火牆關閉連接

**心跳訊息**:
```
event: heartbeat
data: {"timestamp": "2025-11-25T10:30:00Z"}

```

**心跳頻率**:
- 伺服器每 15-30 秒發送一次心跳
- 若客戶端超過 60 秒未收到任何訊息，應主動重連

### 2.3 重連機制

**SSE 自動重連**:
- 瀏覽器 EventSource API 原生支持自動重連
- 斷線後會自動嘗試重新建立連接
- 使用 `Last-Event-ID` Header 恢復訊息

**重連請求**:
```
GET https://api.example.com/v1/sse/notifications?token=xxx
Accept: text/event-stream
Last-Event-ID: msg-last-received-id
```

**伺服器重連處理**:
- 檢查 `Last-Event-ID` Header
- 從該 ID 之後的訊息開始推送
- 若 ID 過期（如超過 24 小時），從當前開始推送

**伺服器重連回應**:
```
event: reconnected
id: msg-current-id
data: {"status": "reconnected", "missedMessagesCount": 3}

event: notification
id: msg-missed-001
data: {"title": "錯過的訊息 1"}

event: notification
id: msg-missed-002
data: {"title": "錯過的訊息 2"}

```

### 2.4 連接關閉

**客戶端主動關閉**:
```javascript
eventSource.close(); // 關閉 SSE 連接
```

**伺服器主動關閉**:
```
event: server_closing
data: {"reason": "maintenance", "message": "伺服器維護中，連接將關閉"}

```

**HTTP 狀態碼**:
| 狀態碼 | 說明 | 客戶端行為 |
| --- | --- | --- |
| 200 OK | 連接成功 | 正常接收訊息 |
| 401 Unauthorized | 認證失敗 | 停止重連，提示使用者 |
| 403 Forbidden | 權限不足 | 停止重連，提示使用者 |
| 429 Too Many Requests | 頻率限制 | 延遲重連（使用 retry 欄位指定時間） |
| 500 Internal Server Error | 伺服器錯誤 | 自動重連（指數退避） |
| 503 Service Unavailable | 服務不可用 | 自動重連（延長間隔） |

---

## 3. 事件類型

### 3.1 事件類型定義

| 事件類型 | event 值 | 說明 | 觸發條件 |
| --- | --- | --- | --- |
| 連接事件 | `connected` | 連接建立成功 | 客戶端首次連接或重連 |
| 心跳事件 | `heartbeat` | 保持連接活躍 | 每 15-30 秒自動發送 |
| 通知事件 | `notification` | 業務通知推送 | 符合推送條件時 |
| 更新事件 | `update` | 數據更新推送 | 數據變更時 |
| 進度事件 | `progress` | 進度更新推送 | 任務進度變化時 |
| 錯誤事件 | `error` | 錯誤訊息推送 | 發生錯誤時 |
| 關閉事件 | `server_closing` | 伺服器即將關閉連接 | 伺服器維護或關閉前 |

---

### 3.2 事件詳細規格

#### 事件 1: [事件名稱 - 如「通知推送」]

**說明**: [事件用途描述]

**event 名稱**: `notification`

**觸發條件**:
- [觸發條件 1]
- [觸發條件 2]

**訊息格式**:
```
event: notification
id: notif-001
data: {"type": "notification", "timestamp": "2025-11-25T10:30:00Z", "payload": {"title": "新訊息", "content": "您有一條新訊息", "priority": "high"}}

```

**data 欄位說明**:

| 欄位路徑 | 類型 | 說明 | 範例 |
| --- | --- | --- | --- |
| type | string | 訊息類型 | "notification" |
| timestamp | string | 訊息時間（ISO 8601） | "2025-11-25T10:30:00Z" |
| payload.title | string | 通知標題 | "新訊息" |
| payload.content | string | 通知內容 | "您有一條新訊息" |
| payload.priority | string | 優先級（low/medium/high） | "high" |

**客戶端處理範例**:
```javascript
eventSource.addEventListener('notification', (event) => {
  const data = JSON.parse(event.data);
  showNotification(data.payload.title, data.payload.content);
});
```

---

#### 事件 2: [事件名稱 - 如「進度更新」]

**說明**: [事件用途描述]

**event 名稱**: `progress`

**觸發條件**:
- [觸發條件]

**訊息格式**:
```
event: progress
id: prog-001
data: {"type": "progress", "timestamp": "2025-11-25T10:30:00Z", "payload": {"taskId": "task-123", "percentage": 45, "stage": "processing", "message": "處理中..."}}

```

**data 欄位說明**:

| 欄位路徑 | 類型 | 說明 | 範例 |
| --- | --- | --- | --- |
| type | string | 訊息類型 | "progress" |
| timestamp | string | 訊息時間 | "2025-11-25T10:30:00Z" |
| payload.taskId | string | 任務 ID | "task-123" |
| payload.percentage | number | 進度百分比（0-100） | 45 |
| payload.stage | string | 當前階段 | "processing" |
| payload.message | string | 進度訊息 | "處理中..." |

---

## 4. 錯誤處理

### 4.1 錯誤事件格式

```
event: error
id: err-001
data: {"type": "error", "timestamp": "2025-11-25T10:30:00Z", "error": {"code": 5001, "type": "BUSINESS_RULE_VIOLATION", "message": "違反業務規則", "details": "無法處理此操作"}}

```

### 4.2 錯誤碼清單

> **📚 參考**: 請參照 [API_Error_Codes.md](API_Error_Codes.md) **標準錯誤碼清單**。

**本 SSE 使用的錯誤碼**：

| 錯誤碼 | 錯誤代號 | 說明 | 處理建議 |
| --- | --- | --- | --- |
| 1001 | INVALID_TOKEN | 無效的身份驗證令牌 | 重新登入並重新連接 |
| 1002 | EXPIRED_TOKEN | 令牌已過期 | 刷新 Token 並重新連接 |
| 2001 | FORBIDDEN | 拒絕存取 | 確認使用者權限 |
| 7001 | INTERNAL_SERVER_ERROR | 伺服器內部錯誤 | 自動重連或聯繫技術支援 |
| 8001 | RATE_LIMIT_EXCEEDED | 超過請求頻率限制 | 延遲重連 |

### 4.3 HTTP 錯誤處理

**客戶端錯誤處理**:
```javascript
eventSource.onerror = (error) => {
  console.error('SSE 連接錯誤:', error);

  if (eventSource.readyState === EventSource.CLOSED) {
    console.log('連接已關閉，準備重連');
  } else if (eventSource.readyState === EventSource.CONNECTING) {
    console.log('正在重新連接...');
  }
};
```

---

## 5. 效能與限制

### 5.1 連接限制

| 限制類型 | 限制值 | 說明 |
| --- | --- | --- |
| 並發連接數 | 6 / 網域 | 瀏覽器對同一網域的 HTTP 連接限制 |
| 訊息大小 | 64 KB | 單則訊息最大 64 KB |
| 訊息緩衝 | 100 則 | 伺服器緩衝最多 100 則訊息用於重連 |
| 連接時長 | 無限制 | 理論上可永久保持（實際受網路環境影響） |

### 5.2 訊息推送頻率

| 頻率類型 | 建議值 | 說明 |
| --- | --- | --- |
| 高頻率推送 | 每秒 1-5 則 | 如即時進度更新 |
| 中頻率推送 | 每分鐘 1-10 則 | 如數據更新通知 |
| 低頻率推送 | 每小時 1-10 則 | 如系統公告 |

**訊息合併策略**:
- 對於高頻率更新，可在伺服器端合併同類訊息
- 使用 `retry` 欄位控制客戶端重連間隔

---

## 6. 安全性

### 6.1 認證與授權

**認證方式 1: Query Parameter (不推薦)**
```
GET /v1/sse/notifications?token=xxx
```
> ⚠️ **安全風險**: Token 可能出現在日誌中

**認證方式 2: Authorization Header (推薦)**
```
GET /v1/sse/notifications
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**權限檢查**:
- 連接建立時驗證 Token
- 定期檢查 Token 有效性（每 5 分鐘）
- Token 過期時發送 `error` 事件並關閉連接

### 6.2 CORS 配置

```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: Authorization, Last-Event-ID
```

### 6.3 防止濫用

**防護措施**:
- IP 頻率限制（每個 IP 最多 10 個連接）
- 使用者連接數限制（每個使用者最多 5 個連接）
- 異常連接檢測（短時間重複連接斷開）

---

## 7. 監控與日誌

### 7.1 關鍵指標

| 指標名稱 | 說明 | 監控目標 |
| --- | --- | --- |
| 活躍連接數 | 當前 SSE 連接數 | < 10000 |
| 訊息推送延遲 | 訊息產生到推送的時間 | < 100ms (P95) |
| 連接存活時長 | 平均連接維持時間 | > 10 分鐘 |
| 重連率 | 重連次數 / 總連接次數 | < 5% |

### 7.2 日誌記錄

**必須記錄的事件**:
- 連接建立（包含 User ID、IP）
- 連接關閉（包含原因）
- 認證失敗
- 訊息推送失敗

**日誌格式範例**:
```json
{
  "timestamp": "2025-11-25T10:30:00Z",
  "level": "INFO",
  "event": "sse_connected",
  "userId": "user-456",
  "connectionId": "conn-abc-123",
  "ip": "192.168.1.1",
  "userAgent": "Mozilla/5.0..."
}
```

---

## 8. 測試場景

### 8.1 功能測試

| 測試場景 | 測試步驟 | 預期結果 |
| --- | --- | --- |
| 正常連接 | 1. 使用有效 Token 連接 | 收到 `connected` 事件 |
| 認證失敗 | 1. 使用無效 Token 連接 | 收到 401 錯誤 |
| 訊息接收 | 1. 觸發推送條件<br>2. 觀察客戶端 | 客戶端收到對應事件 |
| 斷線重連 | 1. 中斷網路<br>2. 恢復網路 | 自動重連並收到錯過的訊息 |

### 8.2 效能測試

| 測試場景 | 測試步驟 | 預期結果 |
| --- | --- | --- |
| 並發連接 | 1. 同時建立 1000 個連接 | 所有連接成功建立 |
| 高頻推送 | 1. 每秒推送 10 則訊息<br>2. 持續 5 分鐘 | 所有訊息成功推送 |
| 長時間連接 | 1. 保持連接 24 小時 | 連接穩定，心跳正常 |

---

## 9. 範例代碼

### 9.1 JavaScript 客戶端範例

```javascript
// 建立 SSE 連接（使用 Authorization Header）
const eventSource = new EventSource('/v1/sse/notifications', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

// 連接成功
eventSource.addEventListener('connected', (event) => {
  const data = JSON.parse(event.data);
  console.log('SSE 連接成功，ID:', data.connectionId);
});

// 心跳事件
eventSource.addEventListener('heartbeat', (event) => {
  const data = JSON.parse(event.data);
  console.log('心跳:', data.timestamp);
});

// 通知事件
eventSource.addEventListener('notification', (event) => {
  const data = JSON.parse(event.data);
  console.log('收到通知:', data.payload);
  showNotification(data.payload.title, data.payload.content);
});

// 進度事件
eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  updateProgressBar(data.payload.taskId, data.payload.percentage);
});

// 錯誤事件
eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('SSE 錯誤:', data.error.message);
});

// 伺服器關閉事件
eventSource.addEventListener('server_closing', (event) => {
  const data = JSON.parse(event.data);
  console.warn('伺服器即將關閉:', data.message);
  eventSource.close();
});

// 連接錯誤（網路錯誤、伺服器錯誤等）
eventSource.onerror = (error) => {
  console.error('SSE 連接錯誤:', error);
  // EventSource 會自動重連，無需手動處理
};

// 手動關閉連接
function closeConnection() {
  eventSource.close();
  console.log('SSE 連接已關閉');
}
```

### 9.2 Python 伺服器範例 (FastAPI)

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime

app = FastAPI()

async def event_generator(request: Request):
    """SSE 事件生成器"""
    # 發送連接成功事件
    yield f"event: connected\n"
    yield f"id: conn-{int(datetime.now().timestamp())}\n"
    yield f"data: {json.dumps({'status': 'connected', 'connectionId': 'conn-abc-123', 'serverTime': datetime.now().isoformat()})}\n\n"

    message_id = 0

    try:
        while True:
            # 檢查客戶端是否斷開
            if await request.is_disconnected():
                print("客戶端已斷開連接")
                break

            # 發送心跳（每 15 秒）
            yield f"event: heartbeat\n"
            yield f"data: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"

            # 發送業務訊息（示例）
            message_id += 1
            yield f"event: notification\n"
            yield f"id: notif-{message_id}\n"
            yield f"data: {json.dumps({'type': 'notification', 'timestamp': datetime.now().isoformat(), 'payload': {'title': f'訊息 {message_id}', 'content': '這是一條測試訊息'}})}\n\n"

            # 等待 15 秒
            await asyncio.sleep(15)

    except asyncio.CancelledError:
        print("連接被取消")

@app.get("/v1/sse/notifications")
async def sse_notifications(request: Request):
    """SSE 端點"""
    # TODO: 驗證 Authorization Header 中的 Token

    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 緩衝
        }
    )
```

---

## 10. SSE vs WebSocket 選擇指南

| 使用場景 | 推薦技術 | 原因 |
| --- | --- | --- |
| 伺服器單向推送（通知、更新） | **SSE** | 更簡單，瀏覽器原生支持重連 |
| 雙向通訊（聊天、協作） | **WebSocket** | 支持全雙工通訊 |
| 進度追蹤、日誌串流 | **SSE** | 實作簡單，HTTP 相容性好 |
| 即時遊戲、即時協作 | **WebSocket** | 低延遲，雙向即時通訊 |
| 需要通過 HTTP 代理 | **SSE** | 基於 HTTP，代理支持更好 |
| 需要二進位數據傳輸 | **WebSocket** | 支持二進位格式 |

---

## 11. 相關文檔連結

### 上游文檔
- **需求文檔**: [FRD_模組.md](../../frd/FRD_模組.md)
- **系統設計**: [SRD_模組.md](../SRD_模組.md)

### 相關 API
- **RESTful API**: [API_Module.md](./API_Module.md)
- **WebSocket API**: [WebSocket_Module.md](./WebSocket_Module.md)
- **錯誤碼清單**: [API_Error_Codes.md](API_Error_Codes.md)

### 測試文檔
- **驗收測試**: [AT_模組.md](../../tests/AT_模組.md)

### 參考資源
- [MDN - Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

---

## 📝 範本版本更新記錄

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v0.01 | 2025-11-25 | AISDLC Team | **初版建立 - 修正 MISS-017 (Stage 7-8)**: SSE API 規格範本缺失<br>- 定義 SSE 連接管理（建立、心跳、重連、關閉）<br>- 定義標準事件類型（connected, heartbeat, notification, progress, error）<br>- 提供錯誤處理和錯誤碼清單<br>- 包含效能限制、安全性、監控指引<br>- 提供 JavaScript 客戶端和 Python 伺服器範例代碼<br>- 包含 SSE vs WebSocket 選擇指南 |

---

**文檔版本**: AISDLC-SDD v0.01
**模板維護**: AISDLC Framework Team
**最後更新**: 2025-11-25
