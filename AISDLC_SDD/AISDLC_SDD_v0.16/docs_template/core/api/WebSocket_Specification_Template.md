# WebSocket API 規格文件 - [WebSocket 名稱]

**版本**: v0.01
**適用情境**: Real-time Communication (Greenfield, Brownfield, Integration)
**負責 Agent**: sd-architect, integration-specialist
**產出時機**: WebSocket API 設計階段

---

## 📋 文件資訊

> 📋 **ID 命名規範**: 使用 [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
> - **WebSocket API ID**: WS-XXX (WebSocket 規格)
> - 格式：WS-001, WS-002, WS-101, WS-102
> - 建議編號規則：
>   - WS-001~099: 通知相關 WebSocket
>   - WS-101~199: 即時通訊 WebSocket
>   - WS-201~299: 即時數據同步 WebSocket
>   - WS-301~399: 協作功能 WebSocket

| 項目 | 內容 |
| --- | --- |
| 文件名稱 | [WebSocket名稱] 規格文件 |
| **WebSocket ID** | **WS-XXX** (依照 AISDLC ID 命名規範) |
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

此文件定義了 [WebSocket名稱] 的規格，該 WebSocket 用於 [主要功能描述：如即時通知、即時聊天、數據同步等]。

**對應業務需求追蹤鏈**：

```
F-XXX (功能需求 - PRD)
  └─ BR-XXX (業務規則 - FRD)
      └─ EPIC-XXX (Epic)
          └─ US-XXX (User Story)
              ├─ AC-XXX-1 (Acceptance Criteria 1)
              ├─ AC-XXX-2 (Acceptance Criteria 2)
              └─ AC-XXX-3 (Acceptance Criteria 3)
                  └─ WS-XXX (本 WebSocket)
                      └─ TC-XXX-Y-Z (測試案例)
```

**需求對應說明**：
- **Feature**: [F-XXX](../../core/prd/PRD_Universal_Template.md#f-xxx) - [功能名稱]
- **Business Rule**: [BR-XXX](../../core/frd/FRD_Universal_Template.md#br-xxx) - [業務規則名稱]
- **Epic**: [EPIC-XXX](../../scenario_specific/xxx/Epic_XXX.md) - [Epic 名稱]
- **User Story**: [US-XXX](../../scenario_specific/xxx/UserStory_XXX.md) - [Story 名稱]
- **Acceptance Criteria**: [AC-XXX-Y](../../scenario_specific/xxx/UserStory_XXX.md#ac-xxx-y) - [驗收條件]

**WebSocket 基本資訊**：
- **連接端點**: `ws://` 或 `wss://` + `/path`
- **描述**: [WebSocket 功能簡述]
- **權限要求**: [需要的角色或權限]
- **連接類型**: [全雙工 / 僅接收 / 僅發送]

---

## 1. 基本資訊

### 1.1 環境資訊

| 環境 | WebSocket 端點 (Endpoint) | 備註 |
| --- | --- | --- |
| 開發環境 (Development) | wss://dev-ws.example.com/v1 | 本地開發測試 |
| 測試環境 (Staging) | wss://staging-ws.example.com/v1 | QA 測試環境 |
| 生產環境 (Production) | wss://ws.example.com/v1 | 正式環境 |

### 1.2 通用規範

- **協議**: WebSocket (WSS - WebSocket Secure，強制加密)
- **內容格式**: JSON (application/json)
- **字元編碼**: UTF-8
- **WebSocket URL 格式**: `wss://[host]/[version]/[endpoint]?[auth-params]`
  > 例如：`wss://ws.example.com/v1/notifications?token=xxx`

### 1.3 訊息格式規範

**標準訊息結構**：

```json
{
  "type": "message_type",
  "event": "event_name",
  "data": { },
  "timestamp": "2025-11-25T10:30:00Z",
  "messageId": "msg-unique-id"
}
```

**欄位說明**：
- `type`: 訊息類型（如 `notification`, `chat`, `sync`, `control`）
- `event`: 事件名稱（如 `new_message`, `user_joined`, `data_updated`）
- `data`: 業務數據（JSON 物件）
- `timestamp`: 訊息發送時間（ISO 8601 格式）
- `messageId`: 訊息唯一識別碼（用於去重和追蹤）

---

## 2. 連接管理

### 2.1 連接建立

**連接 URL**:
```
wss://ws.example.com/v1/[endpoint]?token=[auth_token]
```

**認證方式**:
- **方式 1**: Query Parameter 傳遞 token
  ```
  wss://ws.example.com/v1/notifications?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ```

- **方式 2**: 連接後發送認證訊息
  ```json
  {
    "type": "auth",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```

**連接成功回應**:
```json
{
  "type": "control",
  "event": "connection_established",
  "data": {
    "connectionId": "conn-abc-123",
    "serverTime": "2025-11-25T10:30:00Z"
  }
}
```

**連接失敗回應**:
```json
{
  "type": "control",
  "event": "connection_error",
  "data": {
    "code": 1001,
    "message": "無效的身份驗證令牌"
  }
}
```

### 2.2 心跳機制 (Heartbeat)

**目的**: 保持連接活躍，檢測連接狀態

**客戶端 Ping**:
```json
{
  "type": "control",
  "event": "ping",
  "timestamp": "2025-11-25T10:30:00Z"
}
```

**伺服器 Pong**:
```json
{
  "type": "control",
  "event": "pong",
  "timestamp": "2025-11-25T10:30:05Z"
}
```

**心跳頻率**:
- 建議客戶端每 30 秒發送一次 ping
- 伺服器超過 60 秒未收到 ping 則斷開連接

### 2.3 重連機制

**斷線處理**:
1. 客戶端檢測斷線（如收到 `onclose` 事件）
2. 等待 1 秒後嘗試重連（第 1 次）
3. 若失敗，等待 2 秒後重連（第 2 次）
4. 若失敗，等待 4 秒後重連（第 3 次）
5. 最多重試 5 次，採用指數退避策略（1s, 2s, 4s, 8s, 16s）

**重連請求**:
```json
{
  "type": "control",
  "event": "reconnect",
  "data": {
    "lastMessageId": "msg-last-received-id",
    "sessionId": "session-xxx"
  }
}
```

**伺服器重連回應**:
```json
{
  "type": "control",
  "event": "reconnect_success",
  "data": {
    "missedMessages": [
      { /* 錯過的訊息 1 */ },
      { /* 錯過的訊息 2 */ }
    ]
  }
}
```

### 2.4 連接關閉

**客戶端主動關閉**:
```json
{
  "type": "control",
  "event": "disconnect",
  "data": {
    "reason": "user_logout"
  }
}
```

**伺服器主動關閉**:
```json
{
  "type": "control",
  "event": "server_closing",
  "data": {
    "reason": "maintenance",
    "code": 1001,
    "message": "伺服器維護中，連接將在 10 秒後關閉"
  }
}
```

**WebSocket 關閉碼**:
| 關閉碼 | 名稱 | 說明 |
| --- | --- | --- |
| 1000 | Normal Closure | 正常關閉 |
| 1001 | Going Away | 伺服器關閉或客戶端離開 |
| 1002 | Protocol Error | 協議錯誤 |
| 1003 | Unsupported Data | 不支援的數據類型 |
| 1008 | Policy Violation | 違反政策（如認證失敗） |
| 1011 | Internal Error | 伺服器內部錯誤 |

---

## 3. 訊息類型

### 3.1 客戶端發送訊息 (Client → Server)

#### 訊息 1: [訊息名稱]

**說明**: [訊息用途描述]

**訊息格式**:
```json
{
  "type": "message_type",
  "event": "event_name",
  "data": {
    "param1": "value1",
    "param2": 123
  },
  "timestamp": "2025-11-25T10:30:00Z",
  "messageId": "msg-client-001"
}
```

**參數說明**:

| 參數名稱 | 類型 | 必填 | 說明 | 範例 |
| --- | --- | --- | --- | --- |
| param1 | string | ✅ | 參數 1 說明 | "example" |
| param2 | number | ⚠️ 選填 | 參數 2 說明 | 123 |

**業務規則**:
- [規則 1]
- [規則 2]

**伺服器回應**:
```json
{
  "type": "response",
  "event": "message_received",
  "data": {
    "success": true,
    "messageId": "msg-client-001"
  }
}
```

---

### 3.2 伺服器推送訊息 (Server → Client)

#### 推送訊息 1: [推送訊息名稱]

**說明**: [推送訊息用途描述]

**觸發條件**:
- [觸發條件 1]
- [觸發條件 2]

**訊息格式**:
```json
{
  "type": "notification",
  "event": "event_name",
  "data": {
    "title": "標題",
    "content": "內容",
    "priority": "high"
  },
  "timestamp": "2025-11-25T10:30:00Z",
  "messageId": "msg-server-001"
}
```

**數據欄位說明**:

| 欄位名稱 | 類型 | 說明 | 範例 |
| --- | --- | --- | --- |
| title | string | 訊息標題 | "新訊息" |
| content | string | 訊息內容 | "您有一條新訊息" |
| priority | string | 優先級 (low/medium/high) | "high" |

**客戶端處理**:
- [處理邏輯 1]
- [處理邏輯 2]

---

## 4. 錯誤處理

### 4.1 錯誤訊息格式

```json
{
  "type": "error",
  "event": "error_occurred",
  "data": {
    "code": 3001,
    "type": "VALIDATION_ERROR",
    "message": "驗證失敗",
    "details": "param1 不能為空",
    "timestamp": "2025-11-25T10:30:00Z"
  }
}
```

### 4.2 錯誤碼清單

> **📚 參考**: 請參照 [API_Error_Codes.md](API_Error_Codes.md) **標準錯誤碼清單**。

**本 WebSocket 使用的錯誤碼**：

| 錯誤碼 | 錯誤代號 | 說明 | 處理建議 |
| --- | --- | --- | --- |
| 1001 | INVALID_TOKEN | 無效的身份驗證令牌 | 重新登入獲取有效 Token |
| 1002 | EXPIRED_TOKEN | 令牌已過期 | 刷新 Token 並重新連接 |
| 3001 | VALIDATION_ERROR | 訊息驗證失敗 | 檢查訊息格式 |
| 4001 | NOT_FOUND | 資源不存在 | 確認資源 ID |
| 7001 | INTERNAL_SERVER_ERROR | 伺服器內部錯誤 | 稍後重試或聯繫技術支援 |

---

## 5. 效能與限制

### 5.1 訊息頻率限制

| 限制類型 | 限制值 | 說明 |
| --- | --- | --- |
| 每秒訊息數 | 10 則 | 單一連接每秒最多發送 10 則訊息 |
| 訊息大小 | 64 KB | 單則訊息最大 64 KB |
| 並發連接數 | 1000 / 使用者 | 單一使用者最多 1000 個並發連接 |

**超過限制處理**:
```json
{
  "type": "error",
  "event": "rate_limit_exceeded",
  "data": {
    "code": 8001,
    "message": "超過請求頻率限制",
    "retryAfter": 60
  }
}
```

### 5.2 訊息優先級

| 優先級 | 說明 | 處理方式 |
| --- | --- | --- |
| high | 高優先級（如緊急通知） | 優先發送，即使達到頻率限制 |
| medium | 中優先級（如一般訊息） | 正常發送 |
| low | 低優先級（如統計數據） | 可能延遲或合併發送 |

---

## 6. 安全性

### 6.1 認證與授權

**認證方式**:
- JWT Token 認證（推薦）
- Session Cookie 認證
- API Key 認證

**權限檢查**:
- 連接建立時驗證使用者身份
- 每個訊息發送前檢查使用者權限
- 確保使用者只能接收有權限的訊息

### 6.2 數據加密

- **傳輸加密**: 強制使用 WSS (WebSocket Secure)
- **訊息加密**: 敏感數據可額外使用 AES-256 加密

### 6.3 CORS 配置

```javascript
// 允許的來源
Access-Control-Allow-Origin: https://app.example.com

// 允許的憑證
Access-Control-Allow-Credentials: true
```

### 6.4 惡意行為防護

**防護措施**:
- 訊息頻率限制（Rate Limiting）
- 訊息大小限制
- 異常行為檢測（如短時間大量連接）
- IP 黑名單機制

---

## 7. 監控與日誌

### 7.1 關鍵指標

| 指標名稱 | 說明 | 監控目標 |
| --- | --- | --- |
| 連接數 | 當前活躍連接數 | < 10000 |
| 訊息延遲 | 訊息從發送到接收的時間 | < 100ms (P95) |
| 訊息失敗率 | 訊息發送失敗的比例 | < 0.1% |
| 重連次數 | 客戶端重連的次數 | < 1% 連接數 |

### 7.2 日誌記錄

**必須記錄的事件**:
- 連接建立和關閉
- 認證成功和失敗
- 錯誤訊息
- 異常斷線

**日誌格式範例**:
```json
{
  "timestamp": "2025-11-25T10:30:00Z",
  "level": "INFO",
  "event": "connection_established",
  "connectionId": "conn-abc-123",
  "userId": "user-456",
  "ip": "192.168.1.1"
}
```

---

## 8. 測試場景

### 8.1 功能測試

| 測試場景 | 測試步驟 | 預期結果 |
| --- | --- | --- |
| 正常連接 | 1. 使用有效 Token 連接<br>2. 發送認證訊息 | 收到 connection_established 訊息 |
| 認證失敗 | 1. 使用無效 Token 連接 | 收到 connection_error 訊息並斷開連接 |
| 訊息發送 | 1. 發送業務訊息 | 收到 message_received 確認訊息 |
| 訊息接收 | 1. 觸發伺服器推送條件 | 客戶端收到推送訊息 |

### 8.2 異常測試

| 測試場景 | 測試步驟 | 預期結果 |
| --- | --- | --- |
| 斷線重連 | 1. 手動斷開連接<br>2. 客戶端自動重連 | 重連成功並收到錯過的訊息 |
| 頻率限制 | 1. 短時間發送大量訊息 | 收到 rate_limit_exceeded 錯誤 |
| 心跳超時 | 1. 停止發送 ping<br>2. 等待超時 | 伺服器主動斷開連接 |

---

## 9. 範例代碼

### 9.1 JavaScript 客戶端範例

```javascript
// 建立 WebSocket 連接
const ws = new WebSocket('wss://ws.example.com/v1/notifications?token=xxx');

// 連接成功
ws.onopen = () => {
  console.log('WebSocket 連接成功');

  // 發送訊息
  ws.send(JSON.stringify({
    type: 'message',
    event: 'subscribe',
    data: {
      channel: 'notifications'
    },
    timestamp: new Date().toISOString(),
    messageId: `msg-${Date.now()}`
  }));
};

// 接收訊息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('收到訊息:', message);

  // 根據訊息類型處理
  switch (message.event) {
    case 'connection_established':
      console.log('連接已建立，ID:', message.data.connectionId);
      break;
    case 'new_notification':
      handleNotification(message.data);
      break;
    case 'error_occurred':
      console.error('錯誤:', message.data.message);
      break;
  }
};

// 連接錯誤
ws.onerror = (error) => {
  console.error('WebSocket 錯誤:', error);
};

// 連接關閉
ws.onclose = (event) => {
  console.log('WebSocket 已關閉，代碼:', event.code, '原因:', event.reason);

  // 實作重連邏輯
  setTimeout(() => reconnect(), 1000);
};

// 心跳機制
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'control',
      event: 'ping',
      timestamp: new Date().toISOString()
    }));
  }
}, 30000); // 每 30 秒發送一次
```

### 9.2 Python 客戶端範例

```python
import websocket
import json
import time
import threading

def on_message(ws, message):
    data = json.loads(message)
    print(f"收到訊息: {data}")

    if data['event'] == 'connection_established':
        print(f"連接已建立，ID: {data['data']['connectionId']}")

def on_error(ws, error):
    print(f"錯誤: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"連接已關閉: {close_status_code} - {close_msg}")

def on_open(ws):
    print("WebSocket 連接成功")

    # 發送訊息
    message = {
        "type": "message",
        "event": "subscribe",
        "data": {
            "channel": "notifications"
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "messageId": f"msg-{int(time.time())}"
    }
    ws.send(json.dumps(message))

# 建立連接
ws = websocket.WebSocketApp(
    "wss://ws.example.com/v1/notifications?token=xxx",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# 執行
ws.run_forever()
```

---

## 10. 相關文檔連結

### 上游文檔
- **需求文檔**: [FRD_模組.md](../../frd/FRD_模組.md)
- **系統設計**: [SRD_模組.md](../SRD_模組.md)

### 相關 API
- **RESTful API**: [API_Module.md](./API_Module.md)
- **SSE API**: [SSE_Module.md](./SSE_Module.md)
- **錯誤碼清單**: [API_Error_Codes.md](API_Error_Codes.md)

### 測試文檔
- **驗收測試**: [AT_模組.md](../../tests/AT_模組.md)
- **WebSocket 測試工具**: [Postman WebSocket](./postman/websocket-collection.json)

---

## 📝 範本版本更新記錄

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v0.01 | 2025-11-25 | AISDLC Team | **初版建立 - 修正 MISS-017 (Stage 7-8)**: WebSocket API 規格範本缺失<br>- 定義 WebSocket 連接管理（建立、心跳、重連、關閉）<br>- 定義雙向訊息類型（客戶端→伺服器、伺服器→客戶端）<br>- 提供錯誤處理和錯誤碼清單<br>- 包含效能限制、安全性、監控指引<br>- 提供 JavaScript 和 Python 客戶端範例代碼 |

---

**文檔版本**: AISDLC-SDD v0.01
**模板維護**: AISDLC Framework Team
**最後更新**: 2025-11-25
