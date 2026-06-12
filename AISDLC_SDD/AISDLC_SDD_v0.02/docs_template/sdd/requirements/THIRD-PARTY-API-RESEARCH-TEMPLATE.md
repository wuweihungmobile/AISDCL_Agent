# Third-Party API Research Report — 第三方 API 研究報告模板
# 使用說明：複製至 docs/01_requirements/THIRD-PARTY-API-RESEARCH-{provider}.md 後填寫

**提供者（Provider）**: {ProviderName}
**API 版本**: {version}
**研究日期**: {date}
**研究者**: {Agent: integration-specialist}
**SCG 狀態**: 待 SCG-1 確認

---

## 1. 提供者概覽

| 項目 | 內容 |
|------|------|
| 服務名稱 | {ServiceName} |
| 官方文件 | {docs_url} |
| API 基礎 URL | `{base_url}` |
| 認證方式 | {API Key / OAuth2 / JWT / mTLS} |
| 協議 | {REST / GraphQL / gRPC / WebSocket} |
| 資料格式 | {JSON / XML / Protobuf} |
| SDK 支援 | {語言清單 or None} |
| SLA | {可用性 %}（官方聲明） |

---

## 2. 認證規格

### 2.1 認證流程

```
認證類型: {OAuth2 Authorization Code / Client Credentials / API Key}

OAuth2 流程（若適用）：
1. 取得 Access Token: POST {token_url}
   Body: { grant_type: "client_credentials", client_id, client_secret }
   Response: { access_token, expires_in, token_type }
2. 使用 Token: Header Authorization: Bearer {access_token}
3. Token 刷新: {有/無} refresh_token 機制
   Refresh URL: {refresh_url}
```

### 2.2 憑證管理規格

- 存放位置：{Secret Manager / K8s Secret / Vault}
- 輪換週期：每 {N 天}
- 環境隔離：Dev/Staging/Prod 使用不同憑證

---

## 3. API 端點清單（Consumer 視角）

> 我們需要使用的端點（非全部 API 文件）

| 端點 ID | 方法 | 路徑 | 用途 | 認證 | Rate Limit |
|---------|------|------|------|------|-----------|
| EXT-API-001 | GET | `/v{N}/{resource}` | {用途} | Bearer | {N}/min |
| EXT-API-002 | POST | `/v{N}/{resource}` | {用途} | Bearer | {N}/min |
| EXT-API-NNN | {方法} | {路徑} | {用途} | {認證} | {限制} |

---

## 4. 請求/回應規格

### EXT-API-001：{端點名稱}

#### Request
```json
{
  "method": "GET",
  "url": "{base_url}/v{N}/{resource}",
  "headers": {
    "Authorization": "Bearer {token}",
    "Accept": "application/json"
  },
  "query_params": {
    "{param}": "{type} - {說明}（必填/選填）"
  }
}
```

#### Response（Success 200）
```json
{
  "data": {
    "{field_1}": "{type} - {說明}",
    "{field_2}": "{type} - {說明}"
  },
  "meta": {
    "total": "integer",
    "page": "integer"
  }
}
```

#### Error Codes
| HTTP Status | Error Code | 說明 | 我們的處理策略 |
|------------|-----------|------|-------------|
| 400 | `{ERR_CODE}` | 請求格式錯誤 | 記錄並回傳 4xx 給上游 |
| 401 | `{ERR_CODE}` | Token 無效/過期 | 自動刷新 Token 並重試 |
| 429 | `{ERR_CODE}` | Rate Limit 超出 | 指數退避重試 |
| 500 | `{ERR_CODE}` | 提供者伺服器錯誤 | 重試 3 次後回傳錯誤 |

---

## 5. SLA 分析

| 指標 | 提供者承諾 | 我們的期望 | 差距 |
|------|---------|----------|------|
| 可用性 | {%} | {%} | {符合/不足} |
| P95 延遲 | {N}ms | {N}ms | {符合/不足} |
| Rate Limit | {N}/min | {N}/min | {符合/不足} |
| 單次逾時 | {N}s | {N}s | {符合/不足} |

**SLA 差距說明**：
{若有差距，說明緩解策略：快取、熔斷器、備用提供者等}

---

## 6. 限制與約束

| 限制 | 說明 | 緩解策略 |
|------|------|---------|
| Rate Limit | {N} 請求/分鐘 | 請求佇列 + 指數退避 |
| 資料保留 | 資料保留 {N} 天 | 本地快取關鍵資料 |
| 欄位長度 | {field} 最大 {N} 字元 | 前端驗證 |
| Webhook IP | 僅接受白名單 IP | 確認 IP 並加入白名單 |
| {其他限制} | {說明} | {緩解} |

---

## 7. Consumer Contract Draft

> 我們對此 API 的期望（Consumer-Driven Contract 前身）

```yaml
consumer: "{OurSystem}"
provider: "{ProviderName}"
expectations:
  - endpoint: "EXT-API-001"
    request_format: "{JSON Schema}"
    response_format: "{JSON Schema}"
    expected_latency_p95: "{N}ms"
    expected_availability: "{%}"
    error_handling: "{策略}"
```

---

## 8. SCG-1 確認清單

- [ ] 所有需要使用的端點均已研究完畢
- [ ] 認證流程已完整記錄
- [ ] Rate Limit 分析完成
- [ ] SLA 差距分析完成，緩解策略已定義
- [ ] Consumer Contract Draft 已建立
- [ ] 🔴 Human 確認：整合需求確認，可進入 SCG-3

**最後更新**: {date}
