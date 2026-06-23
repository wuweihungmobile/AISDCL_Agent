---
name: integration-api-client
description: API Client 整合，從 OpenAPI Contract 自動生成，Error Contract 定義，RTM 追蹤整合 TC
user-invocable: true
disable-model-invocation: false
argument-hint: "[api_type: rest|graphql] [framework: axios|fetch|ky|httpx|webclient]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration API Client Skill（SDD 原生）

在 SDD 中，API Client 不是手寫的，而是從凍結的 OpenAPI Contract 自動生成。本 Skill 確保 Client 實作與 Contract 一致，Error Contract 定義所有錯誤回應格式，整合測試結果追蹤至 RTM。

---

## 觸發方式

```bash
/integration-api-client rest axios
/integration-api-client graphql
/integration-api-client rest webclient
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | API Contract 已凍結 | `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml` 存在 |

---

## 執行流程

### 階段 1：從 Contract 生成 API Client（Contract-First）

**SDD 規則**：API Client 從 OpenAPI Contract 自動生成，不手動撰寫端點定義。

```bash
# TypeScript（openapi-typescript-codegen）
npx openapi-typescript docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml \
  -o src/api/generated/{Module}Client.ts

# Python（openapi-python-client）
openapi-python-client generate \
  --path docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml

# Java/Spring（openapi-generator）
openapi-generator-cli generate \
  -i docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml \
  -g java -o src/main/java/client/{Module}
```

---

### 階段 2：Error Contract 設計

**文件路徑**：`docs/02_architecture/api/ERROR-CONTRACT-{Module}.md`

SDD 規則：所有錯誤碼格式必須在 Contract 中明確定義（non-2xx responses）。

```markdown
# Error Contract — {Module}

**版本**: 與 `CONTRACT-{Module}-v{N}.yaml` 同步

## 標準錯誤回應格式

```json
{
  "code": "BUSINESS_ERROR_CODE",    // 業務錯誤碼（需在此列出）
  "message": "human-readable message",
  "details": {}                     // 可選：額外詳情
}
```

## 業務錯誤碼清單

| HTTP | 錯誤碼 | 說明 | 對應 AC |
|------|--------|------|---------|
| 400 | VALIDATION_ERROR | 請求格式不符 Contract | AC-XXX |
| 401 | UNAUTHORIZED | 未認證 | AC-XXX |
| 403 | FORBIDDEN | 無授權 | AC-XXX |
| 404 | RESOURCE_NOT_FOUND | 資源不存在 | AC-XXX |
| 409 | CONFLICT | 資源衝突（如重複建立）| AC-XXX |
| 429 | RATE_LIMIT_EXCEEDED | 超過 NFR-XXX 限流 | AC-XXX |
| 500 | INTERNAL_ERROR | 系統錯誤 | — |
| 503 | SERVICE_UNAVAILABLE | 外部依賴不可用 | — |
```

---

### 階段 3：API Client 錯誤處理（對應 Error Contract）

```typescript
// src/api/client/{Module}Client.ts
// 基於生成的 Client 加上錯誤處理層

import { ApiError } from './generated/{Module}Client';

export class ApiClientWrapper {
  async callWithRetry<T>(
    fn: () => Promise<T>,
    options = { maxRetries: 3, retryOn: [429, 503] }
  ): Promise<T> {
    let lastError: ApiError;

    for (let attempt = 0; attempt < options.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as ApiError;

        // Error Contract 定義的可重試錯誤
        if (!options.retryOn.includes(lastError.status)) {
          throw lastError;
        }

        // 指數退避（429 Rate Limit）
        await this.exponentialBackoff(attempt);
      }
    }

    throw lastError!;
  }

  // Error Contract 業務錯誤碼轉換
  handleBusinessError(error: ApiError): never {
    switch (error.body?.code) {
      case 'UNAUTHORIZED':
        // 觸發重新認證流程
        throw new AuthenticationError(error.message);
      case 'RATE_LIMIT_EXCEEDED':
        // 對應 NFR-XXX 限流策略
        throw new RateLimitError(error.message);
      default:
        throw error;
    }
  }
}
```

---

### 階段 4：Consumer Contract 測試

依賴外部 API 的 Consumer Contract（Pact）確保整合行為一致：

**文件路徑**：`docs/03_testing/contracts/CONSUMER-CONTRACT-{ExternalAPI}.md`

```markdown
# Consumer Contract — {ExternalAPI}

**Consumer**: {SystemName}
**Provider**: {ExternalAPI}

## Consumer 期望的互動

### 正常回應
- Request: {method} {endpoint}
- Response: 200 with schema matching CONTRACT

### 錯誤回應（Error Contract 驗證）
- Request: {bad request}
- Response: 400 with `code: "VALIDATION_ERROR"`
```

---

### 階段 5：RTM 更新 🔴

```bash
/rtm-generate update    # 更新 API 整合 TC（TC-API-XXX）
/spec-compliance-check docs/02_architecture/api/ERROR-CONTRACT-{Module}.md
```

🔴 確認點：生成的 Client 版本與 Contract 版本一致；Consumer Contract 測試通過。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Error Contract | `docs/02_architecture/api/ERROR-CONTRACT-{Module}.md` | SCG-3 後 |
| Consumer Contract | `docs/03_testing/contracts/CONSUMER-CONTRACT-{API}.md` | SCG-3 後 |

---

## 後置動作

```
/rtm-generate update       # 更新整合 TC
/sdd-gate SCG-4            # 整合 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-3 後（Contract 凍結的 Client 實作）

---

## 相關 Skill

- `/contract-generate` — OpenAPI Contract（Client 生成的依據）
- `/integration-oauth` — 認證 Token（API Client 使用）
- `/qa-testing` — Consumer Contract Testing

---

**基於**: AISDLC-SDD v0.20
**對應情境**: Integration 場景
**CI/CD 規格**: `cicd/SDD_INTEGRATION_CICD.md`
