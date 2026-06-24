**版本**: v0.01
**適用情境**: All Scenarios with API
**負責 Agent**: sd-architect
**產出時機**: API 設計階段

# API 索引 - [系統/模組名稱]

*填寫說明：此文件為 API 規格文件的總索引，提供所有 API 的概覽和導航*
*檔名格式：API_Index.md（放置於 srd/api/ 目錄下）*

---

## 文件資訊

| 項目 | 內容 |
| --- | --- |
| 系統名稱 | [系統名稱] |
| 模組名稱 | [模組名稱] |
| 版本 | v1.0 |
| 最後更新日期 | [日期] |
| 維護者 | [系統架構師/後端開發者] |

## 修訂歷史

| 版本 | 日期 | 作者 | 修改內容 |
| --- | --- | --- | --- |
| v1.0 | [日期] | [系統架構師] | 初版建立 |

---

## API 總覽

### 系統架構概要
*簡要描述此系統/模組的 API 架構和設計原則*

### API 統計資訊
- **RESTful API 總數**：[數量] 個
- **WebSocket API 總數**：[數量] 個
- **SSE API 總數**：[數量] 個
- **認證方式**：[Bearer Token / OAuth2 / API Key 等]
- **基礎路徑**：`https://api.example.com/v1/[module]`
- **WebSocket 路徑**：`wss://ws.example.com/v1/[module]`
- **SSE 路徑**：`https://api.example.com/v1/sse/[endpoint]`
- **支援格式**：JSON
- **文檔版本**：v[版本號]

---

## API 分類導航

### 1. RESTful APIs

#### 1.1 [功能分類1] APIs

| API 名稱 | HTTP 方法 | 路徑 | 描述 | 規格文檔 |
| --- | --- | --- | --- | --- |
| [API名稱1] | GET | /[resource] | [簡要描述] | [API_Module_ResourceGet.md](./API_Module_ResourceGet.md) |
| [API名稱2] | POST | /[resource] | [簡要描述] | [API_Module_ResourcePost.md](./API_Module_ResourcePost.md) |
| [API名稱3] | PUT | /[resource]/{id} | [簡要描述] | [API_Module_ResourcePut.md](./API_Module_ResourcePut.md) |

#### 1.2 [功能分類2] APIs

| API 名稱 | HTTP 方法 | 路徑 | 描述 | 規格文檔 |
| --- | --- | --- | --- | --- |
| [API名稱4] | GET | /[resource2] | [簡要描述] | [API_Module_Resource2Get.md](./API_Module_Resource2Get.md) |
| [API名稱5] | DELETE | /[resource2]/{id} | [簡要描述] | [API_Module_Resource2Delete.md](./API_Module_Resource2Delete.md) |

---

### 2. WebSocket APIs

> **📚 參考**: 請參照 [WebSocket_Specification_Template.md](./WebSocket_Specification_Template.md) 建立 WebSocket API 規格文檔

| API 名稱 | 連接路徑 | 描述 | 規格文檔 |
| --- | --- | --- | --- |
| [WebSocket名稱1] | /ws/[endpoint] | [簡要描述] | [WS_Module_Endpoint.md](./WS_Module_Endpoint.md) |
| [WebSocket名稱2] | /ws/[endpoint2] | [簡要描述] | [WS_Module_Endpoint2.md](./WS_Module_Endpoint2.md) |

**常見 WebSocket 使用場景**：
- 即時通知推送（Notifications）
- 即時聊天系統（Chat）
- 協作編輯（Collaborative Editing）
- 即時數據更新（Real-time Data Updates）
- 遊戲多人連線（Multiplayer Gaming）

---

### 3. Server-Sent Events (SSE) APIs

> **📚 參考**: 請參照 [SSE_Specification_Template.md](./SSE_Specification_Template.md) 建立 SSE API 規格文檔

| API 名稱 | 連接路徑 | 描述 | 規格文檔 |
| --- | --- | --- | --- |
| [SSE名稱1] | /sse/[endpoint] | [簡要描述] | [SSE_Module_Endpoint.md](./SSE_Module_Endpoint.md) |
| [SSE名稱2] | /sse/[endpoint2] | [簡要描述] | [SSE_Module_Endpoint2.md](./SSE_Module_Endpoint2.md) |

**常見 SSE 使用場景**：
- 單向通知推送（One-way Notifications）
- 進度追蹤（Progress Tracking）
- 日誌串流（Log Streaming）
- 儀表板數據更新（Dashboard Updates）
- 新聞/社交媒體動態推送（News Feed Updates）

---

### 4. API 選擇指南

| 需求場景 | 推薦方案 | 理由 |
| --- | --- | --- |
| 雙向即時通訊（聊天、協作） | **WebSocket** | 全雙工通訊，低延遲 |
| 單向推送通知（進度、狀態） | **SSE** | 簡單易用，自動重連 |
| 標準 CRUD 操作 | **RESTful API** | 標準化，易於理解 |
| 批量資料查詢 | **RESTful API** | 支援分頁、篩選 |
| 即時儀表板數據 | **SSE** 或 **WebSocket** | 視互動需求決定 |

> **💡 提示**: 詳細的 WebSocket vs SSE 選擇指南請參考 [SSE_Specification_Template.md](./SSE_Specification_Template.md) 的「選擇指南」章節。

---

## API 依賴關係圖

### 核心 API 流程
```mermaid
graph TD
    A[用戶認證] --> B[權限驗證]
    B --> C[業務操作]
    C --> D[結果回傳]
    
    A1[POST /auth/login] --> B1[GET /auth/verify]
    B1 --> C1[GET/POST /resource]
    C1 --> D1[Response]
```

### API 呼叫序列
*描述典型的 API 呼叫順序和依賴關係*

---

## 快速開始指南

### 1. 認證流程
```bash
# 1. 獲取 Access Token
curl -X POST https://api.example.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'

# 2. 使用 Token 呼叫 API
curl -X GET https://api.example.com/v1/resource \
  -H "Authorization: Bearer {access_token}"
```

### 2. 常用 API 範例
*提供最常用的 API 呼叫範例*

### 3. 錯誤處理指南
*說明通用的錯誤處理機制和狀態碼*

---

## 環境資訊

### 開發環境
- **基礎 URL**：https://dev-api.example.com/v1
- **文檔 URL**：https://dev-docs.example.com
- **測試工具**：Swagger UI / Postman Collection

### 測試環境
- **基礎 URL**：https://staging-api.example.com/v1
- **文檔 URL**：https://staging-docs.example.com
- **測試資料**：[測試資料說明]

### 生產環境
- **基礎 URL**：https://api.example.com/v1
- **文檔 URL**：https://docs.example.com
- **監控面板**：[監控 URL]

---

## 通用規範

### 請求格式
- **內容類型**：application/json
- **字元編碼**：UTF-8
- **日期格式**：ISO 8601 (YYYY-MM-DDThh:mm:ss.sssZ)

### 回應格式
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    // 實際資料
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 認證標頭
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## 版本控制

### API 版本策略
*說明 API 版本控制策略和向後兼容性原則*

### 版本更新記錄
| API 版本 | 發佈日期 | 主要變更 | 影響範圍 |
| --- | --- | --- | --- |
| v1.0 | [日期] | 初版發佈 | 全新 API |

---

## 相關文檔

### 系統設計文檔
- [SRD - 系統需求文檔](../SRD_[模組名稱].md)
- [系統架構設計](../SRD_[模組名稱].md#系統架構)

### 需求文檔
- [FRD - 功能需求文檔](../../frd/FRD_[模組名稱].md)
- [User Stories](../../frd/FRD_[模組名稱].md#user-stories)

### 測試文檔
- [AT - 驗收測試](../../tests/AT_[模組名稱].md)
- [API 測試案例](../../tests/AT_[模組名稱].md#api-測試)

---

## 開發工具與資源

### 開發工具
- **API 測試**：Postman Collection / Insomnia
- **文檔生成**：Swagger / OpenAPI
- **監控工具**：[監控工具名稱]

### 程式碼範例
- **前端整合**：[前端範例 Repository]
- **SDK/Library**：[相關 SDK 連結]
- **測試工具**：[測試工具設定檔]

### 支援與聯絡
- **技術支援**：[聯絡方式]
- **Bug 回報**：[Issue Tracker]
- **功能請求**：[功能請求平台]

---

## 注意事項

### 使用限制
- **頻率限制**：每分鐘最多 [數量] 次請求
- **資料大小限制**：單次請求最大 [大小] MB
- **同時連線數**：最多 [數量] 個並發連線

### 安全要求
- 所有 API 呼叫必須使用 HTTPS
- 存取 Token 需要定期更新
- 敏感資料需要額外加密

### 最佳實踐
- 建議使用連線池複用連線
- 實作適當的重試機制
- 遵循 RESTful 設計原則

---

## 版本更新記錄

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v0.01 | 2025-11-25 | AISDLC Team | **修正 MISS-017 (Stage 7-8)**: WebSocket/SSE API 規格範本缺失<br>- 新增「2. WebSocket APIs」分類與範例表格<br>- 新增「3. Server-Sent Events (SSE) APIs」分類與範例表格<br>- 新增「4. API 選擇指南」協助選擇適當的 API 類型<br>- 更新「API 統計資訊」包含 WebSocket/SSE 統計與路徑<br>- 提供 WebSocket/SSE 常見使用場景說明 |
| v0.01 | 2025-10-22 | AISDLC Team | 初版範本建立 |

---

*此索引文件應與所有 API 規格文件保持同步更新。當新增、修改或刪除 API 時，請同時更新此索引。*

**文檔版本**: AISDLC-SDD v0.01
**最後更新**: 2025-11-25
