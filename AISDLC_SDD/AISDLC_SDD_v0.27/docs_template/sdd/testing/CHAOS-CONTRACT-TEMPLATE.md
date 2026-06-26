# Chaos Contract — 整合失敗模擬規格模板
# 使用說明：複製至 docs/03_testing/CHAOS-CONTRACT-{provider}.md 後填寫
# 目的：規格化第三方整合失敗情境，確保系統在整合失敗時優雅降級

**提供者**: {ProviderName}
**版本**: v1.0
**建立日期**: {date}
**前置文件**: `CONSUMER-CONTRACT-{provider}.yaml`
**SCG 狀態**: 待 SCG-4 確認

---

## 1. 混沌測試目標

> 驗證系統在第三方服務失敗時的行為符合規格，確保：
> - 不對使用者產生不可預期的錯誤
> - 降級行為符合業務規格
> - 恢復機制在規定時間內完成

---

## 2. 失敗情境規格

### CHAOS-001：提供者完全不可用（連線失敗）

| 欄位 | 值 |
|------|-----|
| **情境** | {ProviderName} 服務完全宕機，所有請求連線失敗 |
| **觸發方式** | Mock Server 回傳 Connection Refused / Timeout |
| **預期持續時間** | 模擬 {N 分鐘} |

**系統預期行為**：
- [ ] 熔斷器在 {N} 次失敗後開啟（Circuit Breaker Opens）
- [ ] 開啟熔斷器後，立即返回 Fallback 回應（不再等待逾時）
- [ ] Fallback 回應：`{描述 Fallback 內容，例如：返回快取資料 / 返回 503 + 友善訊息}`
- [ ] 監控告警觸發（ALERT-{NNN}）
- [ ] 熔斷器半開嘗試：每 {N}s 嘗試一次連線

**驗收標準**：
```
given: {ProviderName} 無法連線
when: 系統接收到需要呼叫 {ProviderName} 的請求
then:
  - 回應時間 < {N}ms（不等待逾時）
  - HTTP Status: {503 / 200 with degraded data}
  - Response Body: 符合降級規格
  - 熔斷器狀態: OPEN
  - 告警: 已觸發 ALERT-{NNN}
```

---

### CHAOS-002：提供者高延遲（Slow Response）

| 欄位 | 值 |
|------|-----|
| **情境** | {ProviderName} 回應延遲 {N}s（正常 < {N}ms） |
| **觸發方式** | Mock Server 延遲 {N}s 回應 |

**系統預期行為**：
- [ ] 請求逾時設定：{N}ms（不可等待超過此時間）
- [ ] 逾時後觸發重試（最多 {N} 次，指數退避）
- [ ] 超過重試次數後啟用降級回應
- [ ] 告警：P95 延遲超標告警觸發

**驗收標準**：
```
given: {ProviderName} 回應延遲 {N}s
when: 系統發送請求
then:
  - 請求在 {N}ms 後逾時
  - 重試 {N} 次後放棄
  - 最終回應時間 < {N}ms（逾時 × 重試次數）
  - Fallback 回應格式正確
```

---

### CHAOS-003：提供者回傳錯誤回應（500 Internal Server Error）

| 欄位 | 值 |
|------|-----|
| **情境** | {ProviderName} 持續回傳 HTTP 500 |
| **觸發方式** | Mock Server 固定回傳 `{"error": "internal_error"}` |

**系統預期行為**：
- [ ] 重試策略：指數退避，最多 {N} 次
- [ ] 超過重試後記錄錯誤並觸發告警
- [ ] 不向使用者暴露 Provider 原始錯誤訊息
- [ ] 回傳適當的業務錯誤回應

---

### CHAOS-004：Rate Limit 超出（429 Too Many Requests）

| 欄位 | 值 |
|------|-----|
| **情境** | {ProviderName} 回傳 HTTP 429 |
| **觸發方式** | Mock Server 回傳 429 + `Retry-After: {N}` |

**系統預期行為**：
- [ ] 讀取 `Retry-After` Header，等待指定時間後重試
- [ ] 實作請求佇列，避免繼續超出 Rate Limit
- [ ] 若佇列滿，回傳適當的 429 給上游消費者

---

### CHAOS-005：認證失效（Token 過期）

| 欄位 | 值 |
|------|-----|
| **情境** | Access Token 過期，{ProviderName} 回傳 HTTP 401 |
| **觸發方式** | Mock Server 在請求中注入 401 回應 |

**系統預期行為**：
- [ ] 偵測到 401 後，自動觸發 Token 刷新
- [ ] 刷新成功後重試原始請求（透明重試）
- [ ] 刷新失敗後回傳 401 給上游（不暴露 Provider 細節）

---

### CHAOS-006：部分請求失敗（{%} 失敗率）

| 欄位 | 值 |
|------|-----|
| **情境** | {%} 的請求隨機失敗 |
| **觸發方式** | Mock Server 隨機回傳失敗回應 |

**系統預期行為**：
- [ ] 在 {%} 失敗率下，系統整體可用性維持 > {%}
- [ ] 熔斷器不應在偶發失敗時誤開啟

---

## 3. Fallback 行為規格

| 整合點 | Fallback 策略 | Fallback 回應 | 快取 TTL |
|--------|--------------|--------------|---------|
| EXT-API-001（{描述}） | 返回快取資料 | `{ "data": [], "cached": true }` | {N}s |
| EXT-API-002（{描述}） | 返回錯誤訊息 | `{ "error": "service_unavailable" }` | — |
| EXT-API-NNN | {策略} | {回應} | {TTL} |

---

## 4. 執行工具與環境

| 工具 | 用途 |
|------|------|
| {WireMock / Hoverfly / Pact Mock Server} | Mock Provider 各種失敗情境 |
| {Toxiproxy} | 注入網路延遲/故障 |
| {Chaos Toolkit} | 自動化混沌測試執行 |

---

## 5. SCG-4 確認清單

- [ ] 所有整合點均有對應 Chaos Contract
- [ ] Fallback 行為已規格化並測試通過
- [ ] 熔斷器配置已驗證
- [ ] 重試策略已驗證（不會造成級聯失敗）
- [ ] 🔴 Human 確認：混沌測試規格確認

**最後更新**: {date}
