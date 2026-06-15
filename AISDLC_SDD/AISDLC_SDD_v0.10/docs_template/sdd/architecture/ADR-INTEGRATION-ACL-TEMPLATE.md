# ADR — Anti-Corruption Layer 整合決策 ADR 模板
# 使用說明：複製至 docs/02_architecture/adr/ADR-INTEGRATION-{NNN}-{title}.md 後填寫

**ADR ID**: ADR-INTEGRATION-{NNN}
**標題**: {系統} 整合模式決策（{ProviderName}）
**狀態**: Proposed / Accepted
**建立日期**: {date}
**決策者**: {sd-architect + integration-specialist}
**SCG**: SCG-1（整合需求確認後）
**相關文件**: `THIRD-PARTY-API-RESEARCH-{provider}.md`

---

## Context（背景）

**整合需求**：
{描述我們需要整合的系統/服務，以及整合的業務目的}

**第三方 API 特性**：
- Provider：{ProviderName}
- API 模型：{REST / GraphQL / gRPC / Event-Based}
- 資料格式：{JSON / XML}
- 認證：{OAuth2 / API Key}
- SLA：{可用性%}，P95：{N}ms

**整合挑戰**：
- {挑戰 1：例如：Provider 資料模型與我們的 Domain Model 差異大}
- {挑戰 2：例如：Provider API 不穩定，需要緩衝層}
- {挑戰 N}

---

## Decision（決策）

**選定整合模式**: {Anti-Corruption Layer / Gateway / Direct Integration / Event-Driven}

### Option 1: Direct Integration（直接整合）
- **說明**：業務程式碼直接呼叫 Provider API
- **優點**：簡單、開發快速
- **缺點**：Domain Model 與 Provider Model 耦合、Provider 變更影響業務邏輯
- **適用**：Provider 穩定且 Model 相容

### Option 2: Anti-Corruption Layer（ACL）✅（若選此）
- **說明**：在我們的 Domain 與 Provider API 之間建立翻譯層
  ```
  [我們的 Domain] ← → [ACL: Translation Layer] ← → [Provider API]
  ```
- **ACL 職責**：
  - 將 Provider 的 Model 翻譯為我們的 Domain Model
  - 隔離 Provider 的 API 變更
  - 統一錯誤處理與重試邏輯
  - 快取 Provider 回應（降低 Rate Limit 衝擊）
- **優點**：Domain 純粹、Provider 變更隔離、可替換 Provider
- **缺點**：增加程式碼量、需維護翻譯邏輯
- **適用**：Provider Model 與 Domain Model 差異大，或 Provider 可能替換

### Option 3: API Gateway Pattern
- **說明**：透過 API Gateway 統一管理所有外部 API 呼叫
- **優點**：集中管理認證、日誌、重試
- **缺點**：引入額外基礎設施

**選定理由**：
{說明選擇此模式的原因，為何拒絕其他模式}

---

## ACL 設計規格（若選 Option 2）

### 翻譯層設計

```
[Domain Request]
    ↓ ACL.toProviderRequest()
[Provider API Request]
    ↓ HTTP Call
[Provider API Response]
    ↓ ACL.toDomainModel()
[Domain Model]
```

### 錯誤映射規格

| Provider 錯誤 | ACL 對應 Domain 錯誤 | 重試策略 |
|-------------|-------------------|---------|
| 401 | `AuthenticationError` | 刷新 Token 後重試 |
| 429 | `RateLimitError` | 指數退避 |
| 500 | `ExternalServiceError` | 重試 3 次後失敗 |
| Timeout | `TimeoutError` | 重試 2 次 |

### 快取策略

| 資源 | 快取策略 | TTL | 失效觸發 |
|------|---------|------|---------|
| {資源 1} | Cache-Aside | {N}s | 寫入時失效 |
| {資源 N} | {策略} | {TTL} | {觸發} |

---

## Consequences（後果）

**正面**：
- Domain Model 不受 Provider 變更影響
- 可替換 Provider（只需修改 ACL 層）
- 統一的錯誤處理與重試邏輯

**負面（需承擔的成本）**：
- 需維護 ACL 翻譯邏輯（Provider API 升版時需同步更新）
- 翻譯層引入額外延遲（預估 < {N}ms）

---

## Consumer Contract 承諾

此 ADR 確認採用 Consumer-Driven Contract 方式驗證整合：
- Consumer Contract 文件：`CONSUMER-CONTRACT-{provider}.yaml`
- 任何 ACL 或 Provider 變更，必須通過 Contract Tests 才可合併

**SCG 狀態**: SCG-1 → 🔴 Human 確認整合模式後凍結
**最後更新**: {date}
