# System Integration 系統整合 SOP - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的整合工程師、技術架構師
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 遇到複雜的認證問題（OAuth 2.0 多種 flows）
- 需要設計高可用性整合方案
- 處理大規模資料轉換（百萬級記錄）
- 實施進階錯誤處理策略
- 效能優化需求
- Troubleshooting 複雜問題

❌ **不建議閱讀的情況**:
- 初次執行整合專案（請閱讀 SOP.md）
- 快速參考流程（請閱讀 SOP_QuickRef.md）
- 簡單的 RESTful API 整合

### 文檔結構

```
Part 1: 認證機制深度解析
Part 2: 資料轉換進階技術
Part 3: 錯誤處理與容錯策略
Part 4: 效能優化指南
Part 5: 安全性最佳實踐
Part 6: 監控與 Observability
Part 7: Troubleshooting Guide
Part 8: 真實案例研究
Part 10: 跨系統整合技術（Python↔Java、雙DB同步、前端整合、統一認證）
```

### 相關場景參考

本文檔專注於系統整合，以下相關場景可提供補充視角：

- **[Security 安全工程](../security/SOP_DeepDive.md)** - Part 5 API 安全和第三方整合的深度安全實踐
- **[Testing 測試策略](../testing/SOP_DeepDive.md)** - Part 9 契約測試 (Contract Testing) 和整合測試策略
- **[DevOps 持續交付](../devops/SOP_DeepDive.md)** - Part 5 監控整合點的可觀測性實踐
- **[Performance 效能優化](../performance/SOP_DeepDive.md)** - Part 4 API 效能優化和快取策略

---

## Part 1: 認證機制深度解析

### 1.1 OAuth 2.0 完整實作指南

#### OAuth 2.0 Flow Types 完整對比

**Authorization Code Flow (授權碼流程)**

使用場景：
- Web 應用程式（有後端伺服器）
- 需要長期存取權限
- 使用者授權的第三方應用

技術細節：
```yaml
流程圖:
1. 使用者訪問 Web App
2. App 重導向到 Authorization Server
   GET /oauth/authorize?
     response_type=code&
     client_id=YOUR_CLIENT_ID&
     redirect_uri=https://yourapp.com/callback&
     scope=read write&
     state=RANDOM_STRING

3. 使用者登入並授權
4. Authorization Server 重導向回 App
   https://yourapp.com/callback?code=AUTH_CODE&state=RANDOM_STRING

5. App 用 code 交換 access_token (後端執行，安全)
   POST /oauth/token
   {
     "grant_type": "authorization_code",
     "code": "AUTH_CODE",
     "redirect_uri": "https://yourapp.com/callback",
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET"
   }

6. 收到 access_token
   {
     "access_token": "ACCESS_TOKEN",
     "token_type": "Bearer",
     "expires_in": 3600,
     "refresh_token": "REFRESH_TOKEN"
   }

安全優勢:
- Client Secret 不暴露給前端
- 短期的 authorization code（通常 10 分鐘有效）
- 支援 PKCE extension 進一步增強安全性

實作範例 (Node.js):
```javascript
// Step 1: 重導向到授權頁面
app.get('/login', (req, res) => {
  const authUrl = `${AUTH_SERVER}/oauth/authorize?` +
    `response_type=code&` +
    `client_id=${CLIENT_ID}&` +
    `redirect_uri=${REDIRECT_URI}&` +
    `scope=read write&` +
    `state=${generateRandomState()}`;

  res.redirect(authUrl);
});

// Step 2: 處理 callback
app.get('/callback', async (req, res) => {
  const { code, state } = req.query;

  // 驗證 state 防止 CSRF
  if (!verifyState(state)) {
    return res.status(400).send('Invalid state');
  }

  try {
    // 交換 access_token
    const response = await axios.post(`${AUTH_SERVER}/oauth/token`, {
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: REDIRECT_URI,
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET
    });

    const { access_token, refresh_token, expires_in } = response.data;

    // 安全儲存 tokens
    await saveTokens(req.user.id, {
      access_token,
      refresh_token,
      expires_at: Date.now() + expires_in * 1000
    });

    res.redirect('/dashboard');
  } catch (error) {
    console.error('Token exchange failed:', error);
    res.status(500).send('Authentication failed');
  }
});
```
```

**Client Credentials Flow (客戶端憑證流程)**

使用場景：
- Server-to-Server 通訊
- 背景工作（Cron Jobs, Workers）
- 不需要使用者互動

技術細節：
```yaml
流程圖:
1. 應用程式向 Authorization Server 請求 token
   POST /oauth/token
   Authorization: Basic BASE64(client_id:client_secret)
   {
     "grant_type": "client_credentials",
     "scope": "api.read api.write"
   }

2. 收到 access_token
   {
     "access_token": "ACCESS_TOKEN",
     "token_type": "Bearer",
     "expires_in": 3600
   }

特點:
- 最簡單的 OAuth 2.0 流程
- 沒有 refresh_token（token 過期後重新申請）
- 代表應用程式本身，非使用者

實作範例 (Node.js):
```javascript
const axios = require('axios');

async function getAccessToken() {
  try {
    const response = await axios.post(
      `${AUTH_SERVER}/oauth/token`,
      {
        grant_type: 'client_credentials',
        scope: 'api.read api.write'
      },
      {
        auth: {
          username: CLIENT_ID,
          password: CLIENT_SECRET
        }
      }
    );

    const { access_token, expires_in } = response.data;

    // Cache token with expiry
    return {
      token: access_token,
      expiresAt: Date.now() + expires_in * 1000
    };
  } catch (error) {
    console.error('Failed to get access token:', error);
    throw error;
  }
}

// Token 管理 with caching
class TokenManager {
  constructor() {
    this.token = null;
    this.expiresAt = null;
  }

  async getToken() {
    // 如果 token 還沒過期，直接返回
    if (this.token && this.expiresAt > Date.now() + 60000) {
      return this.token;
    }

    // Token 過期或不存在，重新取得
    const tokenData = await getAccessToken();
    this.token = tokenData.token;
    this.expiresAt = tokenData.expiresAt;

    return this.token;
  }
}

// 使用範例
const tokenManager = new TokenManager();

async function callAPI(endpoint) {
  const token = await tokenManager.getToken();

  return axios.get(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
}
```
```

**Refresh Token Flow (刷新 Token 流程)**

```javascript
// 完整的 Token 刷新機制
class TokenRefresher {
  constructor(clientId, clientSecret, tokenStorage) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
    this.storage = tokenStorage;
    this.refreshPromise = null; // 防止並發刷新
  }

  async refreshAccessToken(userId) {
    // 如果已經有正在執行的刷新，等待它完成
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._doRefresh(userId);

    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.refreshPromise = null;
    }
  }

  async _doRefresh(userId) {
    const tokens = await this.storage.getTokens(userId);

    if (!tokens || !tokens.refresh_token) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await axios.post(
        `${AUTH_SERVER}/oauth/token`,
        {
          grant_type: 'refresh_token',
          refresh_token: tokens.refresh_token
        },
        {
          auth: {
            username: this.clientId,
            password: this.clientSecret
          }
        }
      );

      const { access_token, refresh_token, expires_in } = response.data;

      await this.storage.saveTokens(userId, {
        access_token,
        refresh_token: refresh_token || tokens.refresh_token, // 某些 API 不會返回新的 refresh_token
        expires_at: Date.now() + expires_in * 1000
      });

      return access_token;
    } catch (error) {
      // Refresh token 也無效，需要重新授權
      if (error.response?.status === 401) {
        await this.storage.clearTokens(userId);
        throw new Error('Refresh token expired, re-authentication required');
      }
      throw error;
    }
  }

  // 自動刷新的 API 呼叫 wrapper
  async callAPIWithAutoRefresh(userId, apiCall) {
    let tokens = await this.storage.getTokens(userId);

    // 如果 token 即將過期（1分鐘內），主動刷新
    if (tokens.expires_at < Date.now() + 60000) {
      tokens.access_token = await this.refreshAccessToken(userId);
    }

    try {
      // 嘗試使用當前 token 呼叫 API
      return await apiCall(tokens.access_token);
    } catch (error) {
      // 如果是 401，嘗試刷新 token 並重試
      if (error.response?.status === 401) {
        const newToken = await this.refreshAccessToken(userId);
        return await apiCall(newToken);
      }
      throw error;
    }
  }
}

// 使用範例
const refresher = new TokenRefresher(CLIENT_ID, CLIENT_SECRET, tokenStorage);

app.get('/api/user/data', async (req, res) => {
  try {
    const data = await refresher.callAPIWithAutoRefresh(
      req.user.id,
      async (token) => {
        return axios.get(`${API_URL}/user/data`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    );

    res.json(data.data);
  } catch (error) {
    if (error.message.includes('re-authentication required')) {
      return res.status(401).json({
        error: 'Please re-authenticate',
        redirectTo: '/login'
      });
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

### 1.2 API Key 安全管理最佳實踐

**環境變數管理**

```yaml
推薦方案:
1. 開發環境: .env 檔案（不納入版控）
2. 生產環境: Secret Management Service

.env 範例:
API_KEY=sk_live_xxx
API_SECRET=whsec_xxx
ENCRYPTION_KEY=32_bytes_random_key

注意事項:
- 絕不將 .env 納入 Git
- 使用 .env.example 作為範本
- 不同環境使用不同的 keys

進階安全:
- API Keys 加密儲存
- 使用 Vault (HashiCorp Vault, AWS Secrets Manager)
- 定期輪換 keys
- 最小權限原則（限制 key 的 scope）
```

**API Key 儲存加密**

```javascript
const crypto = require('crypto');

class SecureKeyStorage {
  constructor(encryptionKey) {
    // encryptionKey 應該是 32 bytes (256 bits)
    this.key = Buffer.from(encryptionKey, 'hex');
    this.algorithm = 'aes-256-gcm';
  }

  encrypt(plaintext) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv(this.algorithm, this.key, iv);

    let encrypted = cipher.update(plaintext, 'utf8', 'hex');
    encrypted += cipher.final('hex');

    const authTag = cipher.getAuthTag();

    // 返回: iv + authTag + encrypted (all hex)
    return iv.toString('hex') + ':' + authTag.toString('hex') + ':' + encrypted;
  }

  decrypt(ciphertext) {
    const parts = ciphertext.split(':');
    const iv = Buffer.from(parts[0], 'hex');
    const authTag = Buffer.from(parts[1], 'hex');
    const encrypted = parts[2];

    const decipher = crypto.createDecipheriv(this.algorithm, this.key, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  }
}

// 使用範例
const storage = new SecureKeyStorage(process.env.ENCRYPTION_KEY);

// 儲存時加密
const encryptedKey = storage.encrypt(apiKey);
await db.saveAPIKey(userId, encryptedKey);

// 使用時解密
const encryptedKey = await db.getAPIKey(userId);
const apiKey = storage.decrypt(encryptedKey);
```

---

## Part 2: 資料轉換進階技術

### 2.1 大規模資料轉換策略

**場景：需要同步百萬級歷史訂單**

挑戰：
- 資料量大（1M+ records）
- API 限流（100 requests/minute）
- 轉換邏輯複雜
- 需要容錯和斷點續傳

**批次處理架構**

```javascript
// 批次處理引擎
class BatchSyncEngine {
  constructor(config) {
    this.batchSize = config.batchSize || 100;
    this.concurrency = config.concurrency || 5;
    this.rateLimit = config.rateLimit || 100; // requests per minute
    this.retryAttempts = config.retryAttempts || 3;
    this.checkpointInterval = config.checkpointInterval || 1000; // 每1000筆存檔
  }

  async syncData(dataSource, transformer, destination) {
    const totalCount = await dataSource.count();
    let processedCount = await this.loadCheckpoint() || 0;

    console.log(`Starting sync: ${processedCount}/${totalCount} already processed`);

    const rateLimiter = new RateLimiter(this.rateLimit, 60000); // per minute
    const progressBar = new ProgressBar(totalCount);

    while (processedCount < totalCount) {
      const batch = await dataSource.fetchBatch(processedCount, this.batchSize);

      try {
        // 並發處理 batch（受 concurrency 限制）
        await this.processBatchWithConcurrency(
          batch,
          async (item) => {
            await rateLimiter.wait(); // 限流
            const transformed = await transformer.transform(item);
            await destination.save(transformed);
          }
        );

        processedCount += batch.length;
        progressBar.update(processedCount);

        // 定期存檔進度
        if (processedCount % this.checkpointInterval === 0) {
          await this.saveCheckpoint(processedCount);
        }

      } catch (error) {
        console.error(`Batch failed at ${processedCount}:`, error);
        // 存檔失敗位置
        await this.saveCheckpoint(processedCount);
        throw error;
      }
    }

    await this.clearCheckpoint();
    console.log('Sync completed successfully');
  }

  async processBatchWithConcurrency(items, processFunc) {
    const queue = [...items];
    const results = [];
    const workers = [];

    for (let i = 0; i < this.concurrency; i++) {
      workers.push(this.worker(queue, processFunc, results));
    }

    await Promise.all(workers);
    return results;
  }

  async worker(queue, processFunc, results) {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;

      let attempts = 0;
      while (attempts < this.retryAttempts) {
        try {
          const result = await processFunc(item);
          results.push(result);
          break;
        } catch (error) {
          attempts++;
          if (attempts >= this.retryAttempts) {
            console.error(`Failed after ${attempts} attempts:`, item.id, error);
            // 記錄失敗項目
            await this.logFailedItem(item, error);
            break;
          }
          // 指數退避
          await this.sleep(Math.pow(2, attempts) * 1000);
        }
      }
    }
  }

  async loadCheckpoint() {
    // 從檔案或資料庫載入上次處理到的位置
    try {
      const data = await fs.readFile('.sync_checkpoint.json', 'utf8');
      return JSON.parse(data).processedCount;
    } catch {
      return 0;
    }
  }

  async saveCheckpoint(count) {
    await fs.writeFile(
      '.sync_checkpoint.json',
      JSON.stringify({ processedCount: count, timestamp: Date.now() })
    );
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 使用範例
const engine = new BatchSyncEngine({
  batchSize: 100,
  concurrency: 5,
  rateLimit: 100,
  retryAttempts: 3
});

await engine.syncData(
  sourceDatabase,
  new OrderTransformer(),
  targetAPI
);
```

### 2.2 複雜資料映射（Nested JSON 轉換）

```javascript
// 宣告式資料映射引擎
class DataMapper {
  constructor(mappingDefinition) {
    this.mapping = mappingDefinition;
  }

  transform(sourceData) {
    return this._applyMapping(sourceData, this.mapping);
  }

  _applyMapping(source, mapping) {
    const result = {};

    for (const [targetKey, mapRule] of Object.entries(mapping)) {
      if (typeof mapRule === 'string') {
        // 簡單映射: "target": "source.path"
        result[targetKey] = this._getNestedValue(source, mapRule);
      } else if (typeof mapRule === 'function') {
        // 自訂函數: "target": (src) => src.a + src.b
        result[targetKey] = mapRule(source);
      } else if (mapRule.path) {
        // 複雜規則
        const value = this._getNestedValue(source, mapRule.path);
        result[targetKey] = this._applyTransform(value, mapRule);
      } else if (mapRule.nested) {
        // 巢狀物件
        const nestedSource = this._getNestedValue(source, mapRule.source);
        result[targetKey] = this._applyMapping(nestedSource, mapRule.nested);
      } else if (mapRule.array) {
        // 陣列映射
        const arraySource = this._getNestedValue(source, mapRule.source);
        result[targetKey] = arraySource.map(item =>
          this._applyMapping(item, mapRule.array)
        );
      }
    }

    return result;
  }

  _getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  _applyTransform(value, rule) {
    if (rule.transform) {
      return rule.transform(value);
    }
    if (rule.default !== undefined && value === undefined) {
      return rule.default;
    }
    return value;
  }
}

// 使用範例：Stripe Payment Intent → 內部訂單格式
const paymentMapping = new DataMapper({
  // 簡單映射
  orderId: 'id',
  amount: 'amount',
  currency: 'currency',

  // 自訂函數
  amountInDollars: (src) => src.amount / 100,

  // 複雜規則（含轉換）
  status: {
    path: 'status',
    transform: (val) => ({
      'succeeded': 'COMPLETED',
      'processing': 'PENDING',
      'requires_payment_method': 'FAILED'
    }[val] || 'UNKNOWN')
  },

  // 預設值
  description: {
    path: 'description',
    default: 'No description'
  },

  // 巢狀物件
  customer: {
    source: 'customer',
    nested: {
      id: 'id',
      email: 'email',
      name: 'name'
    }
  },

  // 陣列映射
  items: {
    source: 'metadata.line_items',
    array: {
      productId: 'product_id',
      quantity: 'quantity',
      price: 'price'
    }
  }
});

// 轉換
const stripePayment = {
  id: 'pi_123',
  amount: 5000,
  currency: 'usd',
  status: 'succeeded',
  customer: {
    id: 'cus_123',
    email: 'user@example.com',
    name: 'John Doe'
  },
  metadata: {
    line_items: [
      { product_id: 'prod_1', quantity: 2, price: 2000 },
      { product_id: 'prod_2', quantity: 1, price: 1000 }
    ]
  }
};

const internalOrder = paymentMapping.transform(stripePayment);
console.log(internalOrder);
/*
{
  orderId: 'pi_123',
  amount: 5000,
  currency: 'usd',
  amountInDollars: 50,
  status: 'COMPLETED',
  description: 'No description',
  customer: {
    id: 'cus_123',
    email: 'user@example.com',
    name: 'John Doe'
  },
  items: [
    { productId: 'prod_1', quantity: 2, price: 2000 },
    { productId: 'prod_2', quantity: 1, price: 1000 }
  ]
}
*/
```

---

## Part 3: 錯誤處理與容錯策略

### 3.1 智能重試機制（Exponential Backoff with Jitter）

```javascript
class SmartRetry {
  constructor(options = {}) {
    this.maxAttempts = options.maxAttempts || 3;
    this.baseDelay = options.baseDelay || 1000; // 1 second
    this.maxDelay = options.maxDelay || 30000; // 30 seconds
    this.shouldRetry = options.shouldRetry || this.defaultShouldRetry;
  }

  async execute(fn, context = '') {
    let lastError;

    for (let attempt = 0; attempt < this.maxAttempts; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;

        // 判斷是否應該重試
        if (!this.shouldRetry(error) || attempt === this.maxAttempts - 1) {
          throw error;
        }

        // 計算延遲時間（exponential backoff + jitter）
        const delay = this.calculateDelay(attempt);

        console.warn(
          `[SmartRetry] ${context} failed (attempt ${attempt + 1}/${this.maxAttempts}). ` +
          `Retrying in ${delay}ms. Error: ${error.message}`
        );

        await this.sleep(delay);
      }
    }

    throw lastError;
  }

  calculateDelay(attempt) {
    // Exponential backoff: baseDelay * 2^attempt
    const exponentialDelay = Math.min(
      this.baseDelay * Math.pow(2, attempt),
      this.maxDelay
    );

    // Add jitter (random 0-30% variation)
    const jitter = exponentialDelay * 0.3 * Math.random();

    return Math.floor(exponentialDelay + jitter);
  }

  defaultShouldRetry(error) {
    // 5xx 錯誤或網路錯誤應重試
    if (error.response) {
      const status = error.response.status;
      return status >= 500 || status === 429; // 5xx or Rate Limit
    }

    // 網路錯誤（timeout, connection refused）
    if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') {
      return true;
    }

    return false;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 使用範例
const retry = new SmartRetry({
  maxAttempts: 5,
  baseDelay: 1000,
  maxDelay: 30000,
  shouldRetry: (error) => {
    // 自訂重試邏輯
    if (error.response?.status === 429) {
      // Rate limit: 從 header 取得建議的等待時間
      const retryAfter = error.response.headers['retry-after'];
      if (retryAfter) {
        // 可以動態調整延遲
        return true;
      }
    }
    return error.response?.status >= 500;
  }
});

// API 呼叫 with retry
async function callExternalAPI(endpoint, data) {
  return retry.execute(
    async () => {
      return await axios.post(`${API_URL}${endpoint}`, data, {
        timeout: 10000,
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    },
    `API: ${endpoint}` // context for logging
  );
}
```

### 3.2 Circuit Breaker Pattern

```javascript
class CircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5; // 連續失敗 5 次
    this.successThreshold = options.successThreshold || 2; // 連續成功 2 次恢復
    this.timeout = options.timeout || 60000; // 1 minute

    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.failureCount = 0;
    this.successCount = 0;
    this.nextAttempt = Date.now();
  }

  async execute(fn, fallback = null) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        console.warn('[CircuitBreaker] Circuit is OPEN, using fallback');
        if (fallback) return fallback();
        throw new Error('Circuit breaker is OPEN');
      }
      // 嘗試進入 HALF_OPEN 狀態
      this.state = 'HALF_OPEN';
      console.info('[CircuitBreaker] Entering HALF_OPEN state');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      if (fallback) return fallback();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;

    if (this.state === 'HALF_OPEN') {
      this.successCount++;
      if (this.successCount >= this.successThreshold) {
        this.state = 'CLOSED';
        this.successCount = 0;
        console.info('[CircuitBreaker] Circuit is now CLOSED (recovered)');
      }
    }
  }

  onFailure() {
    this.failureCount++;
    this.successCount = 0;

    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.timeout;
      console.error(
        `[CircuitBreaker] Circuit is now OPEN (${this.failureCount} failures). ` +
        `Will retry after ${this.timeout}ms`
      );
    }
  }

  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      nextAttempt: this.nextAttempt
    };
  }
}

// 結合使用：Circuit Breaker + Smart Retry + Fallback
class ResilientAPIClient {
  constructor(baseURL, options = {}) {
    this.baseURL = baseURL;
    this.circuitBreaker = new CircuitBreaker(options.circuitBreaker);
    this.retry = new SmartRetry(options.retry);
    this.cache = new Map(); // 簡單的記憶體 cache
  }

  async get(endpoint, options = {}) {
    const { useCache = true, cacheTTL = 60000, fallbackData = null } = options;

    return this.circuitBreaker.execute(
      async () => {
        // 檢查 cache
        if (useCache) {
          const cached = this.getFromCache(endpoint);
          if (cached) return cached;
        }

        // 實際 API 呼叫 with retry
        const result = await this.retry.execute(async () => {
          const response = await axios.get(`${this.baseURL}${endpoint}`);
          return response.data;
        }, `GET ${endpoint}`);

        // 存入 cache
        if (useCache) {
          this.setCache(endpoint, result, cacheTTL);
        }

        return result;
      },
      // Fallback: 使用 stale cache 或預設資料
      () => {
        console.warn(`[ResilientAPIClient] Using fallback for ${endpoint}`);
        const staleCache = this.getFromCache(endpoint, true); // ignore TTL
        return staleCache || fallbackData || { error: 'Service unavailable', cached: true };
      }
    );
  }

  getFromCache(key, ignoreExpiry = false) {
    const cached = this.cache.get(key);
    if (!cached) return null;
    if (!ignoreExpiry && Date.now() > cached.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    return cached.data;
  }

  setCache(key, data, ttl) {
    this.cache.set(key, {
      data,
      expiresAt: Date.now() + ttl
    });
  }
}

// 使用範例
const apiClient = new ResilientAPIClient('https://api.example.com', {
  circuitBreaker: {
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 30000
  },
  retry: {
    maxAttempts: 3,
    baseDelay: 1000
  }
});

// 呼叫 API（自動處理 retry, circuit breaker, cache, fallback）
const userData = await apiClient.get('/users/123', {
  useCache: true,
  cacheTTL: 300000, // 5 minutes
  fallbackData: { id: 123, name: 'Unknown User' }
});
```

---

## Part 4: 效能優化指南

### 4.1 Webhook 高並發處理

**問題場景**：
- Stripe 同時發送大量 webhooks（促銷活動、秒殺）
- 需要 3 秒內回應 200 OK（否則 retry）
- 實際處理需要 10-30 秒（寫資料庫、發送通知）

**解決方案：非同步處理架構**

```javascript
// Webhook Receiver (快速回應)
app.post('/webhooks/stripe', async (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    // 1. 驗證 webhook signature (< 50ms)
    event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  // 2. 立即存入 Queue (< 100ms)
  try {
    await webhookQueue.add('process-stripe-webhook', {
      eventId: event.id,
      eventType: event.type,
      data: event.data.object,
      timestamp: Date.now()
    }, {
      attempts: 5, // 失敗重試 5 次
      backoff: {
        type: 'exponential',
        delay: 2000
      },
      removeOnComplete: 1000, // 保留最近 1000 筆成功記錄
      removeOnFail: 5000 // 保留最近 5000 筆失敗記錄
    });

    // 3. 快速回應 200 OK (總時間 < 200ms)
    res.status(200).json({ received: true });

  } catch (err) {
    console.error('Failed to queue webhook:', err);
    // 即使 queue 失敗，也回應 200 避免 Stripe 重試
    // 但記錄錯誤供後續處理
    await logWebhookError(event, err);
    res.status(200).json({ received: true, queued: false });
  }
});

// Worker Process (非同步處理)
webhookQueue.process('process-stripe-webhook', async (job) => {
  const { eventId, eventType, data } = job.data;

  // 冪等性檢查
  const existing = await db.webhookEvents.findOne({ eventId });
  if (existing && existing.status === 'processed') {
    console.log(`Event ${eventId} already processed, skipping`);
    return { status: 'skipped', reason: 'already_processed' };
  }

  try {
    // 實際的業務邏輯處理
    await processWebhookEvent(eventType, data);

    // 標記為已處理
    await db.webhookEvents.updateOne(
      { eventId },
      {
        status: 'processed',
        processedAt: new Date(),
        attempts: job.attemptsMade
      },
      { upsert: true }
    );

    return { status: 'success' };

  } catch (error) {
    console.error(`Failed to process webhook ${eventId}:`, error);

    // 記錄失敗
    await db.webhookEvents.updateOne(
      { eventId },
      {
        status: 'failed',
        lastError: error.message,
        failedAt: new Date(),
        attempts: job.attemptsMade
      },
      { upsert: true }
    );

    throw error; // 讓 Bull 處理重試
  }
});
```

### 4.2 API 批次請求優化

**問題**：需要取得 1000 個使用者的詳細資訊

❌ **錯誤做法**：
```javascript
// 1000 個獨立請求（慢且可能觸發限流）
for (const userId of userIds) {
  const user = await api.getUser(userId);
  users.push(user);
}
```

✅ **優化做法 1：使用 Batch API**
```javascript
// 如果 API 支援 batch endpoint
const batchSize = 100;
const batches = chunk(userIds, batchSize); // [ids1-100, ids101-200, ...]

for (const batch of batches) {
  const batchUsers = await api.getUsersBatch(batch);
  users.push(...batchUsers);
}
```

✅ **優化做法 2：並發請求 + 限流**
```javascript
const pLimit = require('p-limit');

// 限制同時只有 10 個並發請求
const limit = pLimit(10);

const promises = userIds.map(userId =>
  limit(async () => {
    await rateLimiter.wait(); // 限流
    return api.getUser(userId);
  })
);

const users = await Promise.all(promises);
```

✅ **優化做法 3：DataLoader Pattern (自動批次 + Cache)**
```javascript
const DataLoader = require('dataloader');

// DataLoader 會自動：
// 1. 將同一 tick 的請求合併成 batch
// 2. Cache 結果避免重複請求
const userLoader = new DataLoader(async (userIds) => {
  // 一次取得多個使用者
  const users = await api.getUsersBatch(userIds);

  // 必須按照 userIds 的順序返回
  return userIds.map(id =>
    users.find(u => u.id === id) || new Error(`User ${id} not found`)
  );
}, {
  batchScheduleFn: (callback) => setTimeout(callback, 10), // 10ms 內的請求合併
  maxBatchSize: 100, // 最多 100 個一批
  cache: true
});

// 使用（自動批次處理）
const user1 = await userLoader.load('user_1');
const user2 = await userLoader.load('user_2'); // 會和 user_1 合併成一個請求
const user3 = await userLoader.load('user_1'); // 從 cache 返回，不會發請求
```

---

## Part 5: 安全性最佳實踐

### 5.1 Webhook Signature 驗證（防止偽造）

**Stripe 範例**：
```javascript
const crypto = require('crypto');

function verifyStripeWebhook(payload, signature, secret) {
  // Stripe signature format: "t=timestamp,v1=signature"
  const parts = signature.split(',');
  const timestamp = parts.find(p => p.startsWith('t=')).substring(2);
  const expectedSig = parts.find(p => p.startsWith('v1=')).substring(3);

  // 檢查時間戳（防止 replay attack）
  const tolerance = 300; // 5 minutes
  const now = Math.floor(Date.now() / 1000);
  if (now - parseInt(timestamp) > tolerance) {
    throw new Error('Webhook timestamp too old');
  }

  // 計算預期的 signature
  const signedPayload = `${timestamp}.${payload}`;
  const computedSig = crypto
    .createHmac('sha256', secret)
    .update(signedPayload, 'utf8')
    .digest('hex');

  // 安全比較（防止 timing attack）
  if (!crypto.timingSafeEqual(Buffer.from(expectedSig), Buffer.from(computedSig))) {
    throw new Error('Invalid webhook signature');
  }

  return true;
}

// Express middleware
app.post('/webhook', express.raw({ type: 'application/json' }), (req, res) => {
  const sig = req.headers['stripe-signature'];
  const payload = req.body.toString('utf8');

  try {
    verifyStripeWebhook(payload, sig, WEBHOOK_SECRET);
    // 驗證通過，處理 webhook
    const event = JSON.parse(payload);
    // ...
  } catch (err) {
    console.error('Webhook verification failed:', err);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  res.json({ received: true });
});
```

**通用 HMAC 驗證**：
```javascript
function verifyHMACSignature(payload, receivedSignature, secret, algorithm = 'sha256') {
  const computedSignature = crypto
    .createHmac(algorithm, secret)
    .update(payload)
    .digest('hex');

  // 支援不同的 signature 格式
  const normalizedReceived = receivedSignature.toLowerCase().replace(/^sha256=/, '');

  return crypto.timingSafeEqual(
    Buffer.from(normalizedReceived, 'hex'),
    Buffer.from(computedSignature, 'hex')
  );
}
```

### 5.2 敏感資料遮罩（Logging & Monitoring）

```javascript
class SensitiveDataMasker {
  constructor() {
    this.patterns = [
      { name: 'credit_card', regex: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g, replacement: '****-****-****-' },
      { name: 'api_key', regex: /\b(sk|pk)_(live|test)_[A-Za-z0-9]{24,}\b/g, replacement: '[REDACTED_API_KEY]' },
      { name: 'email', regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, replacement: (match) => {
        const [local, domain] = match.split('@');
        return `${local.substring(0, 2)}***@${domain}`;
      }},
      { name: 'jwt', regex: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g, replacement: '[REDACTED_JWT]' },
    ];
  }

  mask(data) {
    if (typeof data === 'string') {
      return this.maskString(data);
    } else if (typeof data === 'object') {
      return this.maskObject(data);
    }
    return data;
  }

  maskString(str) {
    let masked = str;
    for (const pattern of this.patterns) {
      masked = masked.replace(pattern.regex, pattern.replacement);
    }
    return masked;
  }

  maskObject(obj) {
    if (obj === null) return null;
    if (Array.isArray(obj)) {
      return obj.map(item => this.mask(item));
    }

    const masked = {};
    for (const [key, value] of Object.entries(obj)) {
      // 特定欄位完全隱藏
      if (['password', 'secret', 'token', 'apiKey'].includes(key)) {
        masked[key] = '[REDACTED]';
      } else if (typeof value === 'string') {
        masked[key] = this.maskString(value);
      } else if (typeof value === 'object') {
        masked[key] = this.maskObject(value);
      } else {
        masked[key] = value;
      }
    }
    return masked;
  }
}

// 整合到 Logger
const masker = new SensitiveDataMasker();

function safeLog(level, message, data) {
  const maskedData = masker.mask(data);
  logger[level](message, maskedData);
}

// 使用
safeLog('info', 'Processing payment', {
  customer: {
    email: 'john.doe@example.com',
    card: '4242-4242-4242-4242'
  },
  apiKey: 'sk_live_abcdefghijklmnopqrstuvwxyz'
});

// 輸出（敏感資料已遮罩）:
// { customer: { email: 'jo***@example.com', card: '****-****-****-4242' }, apiKey: '[REDACTED_API_KEY]' }
```

---

## Part 6: 監控與 Observability

### 6.1 分散式追蹤（Distributed Tracing）

**使用 OpenTelemetry**：

```javascript
const { trace, context } = require('@opentelemetry/api');
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');

// 設定 Tracer
const provider = new NodeTracerProvider();
provider.addSpanProcessor(
  new SimpleSpanProcessor(
    new JaegerExporter({
      endpoint: 'http://localhost:14268/api/traces',
    })
  )
);
provider.register();

// 自動追蹤 HTTP 和 Express
registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
  ],
});

const tracer = trace.getTracer('integration-service');

// 手動建立 span
async function processWebhook(webhookData) {
  const span = tracer.startSpan('process_webhook');

  try {
    span.setAttributes({
      'webhook.type': webhookData.type,
      'webhook.id': webhookData.id,
      'service.name': 'integration-service'
    });

    // 子 span
    const dbSpan = tracer.startSpan('save_to_database', {
      parent: span
    });
    await saveToDatabase(webhookData);
    dbSpan.end();

    const apiSpan = tracer.startSpan('call_external_api', {
      parent: span
    });
    await callExternalAPI(webhookData);
    apiSpan.end();

    span.setStatus({ code: SpanStatusCode.OK });
  } catch (error) {
    span.recordException(error);
    span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
    throw error;
  } finally {
    span.end();
  }
}
```

**Trace Context 跨服務傳遞**：

```javascript
// Service A: 傳送請求
const axios = require('axios');
const { context, propagation } = require('@opentelemetry/api');

async function callServiceB() {
  const span = tracer.startSpan('call_service_b');

  return context.with(trace.setSpan(context.active(), span), async () => {
    try {
      // 自動注入 trace headers (traceparent, tracestate)
      const carrier = {};
      propagation.inject(context.active(), carrier);

      const response = await axios.post('http://service-b/api/process', data, {
        headers: carrier // { traceparent: '00-xxx-yyy-01', ... }
      });

      span.end();
      return response.data;
    } catch (error) {
      span.recordException(error);
      span.end();
      throw error;
    }
  });
}

// Service B: 接收請求
app.post('/api/process', (req, res) => {
  // 自動提取 trace context from headers
  const ctx = propagation.extract(context.active(), req.headers);

  context.with(ctx, () => {
    const span = tracer.startSpan('process_data');

    try {
      // 處理邏輯...
      // 這個 span 會自動連接到 Service A 的 trace

      span.end();
      res.json({ status: 'ok' });
    } catch (error) {
      span.recordException(error);
      span.end();
      res.status(500).json({ error: error.message });
    }
  });
});
```

### 6.2 SLI/SLO 監控

```javascript
// 定義 SLI (Service Level Indicators)
const prometheus = require('prom-client');

// 1. Availability SLI: 成功率
const apiSuccessRate = new prometheus.Counter({
  name: 'api_requests_total',
  help: 'Total API requests',
  labelNames: ['status', 'endpoint']
});

// 2. Latency SLI: 回應時間
const apiDuration = new prometheus.Histogram({
  name: 'api_request_duration_seconds',
  help: 'API request duration',
  labelNames: ['endpoint'],
  buckets: [0.1, 0.5, 1, 2, 5] // P50, P95, P99
});

// 3. Throughput SLI: 請求量
const webhookProcessed = new prometheus.Counter({
  name: 'webhooks_processed_total',
  help: 'Total webhooks processed',
  labelNames: ['type', 'status']
});

// Middleware 計算指標
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    apiDuration.observe({ endpoint: req.path }, duration);
    apiSuccessRate.inc({
      status: res.statusCode >= 200 && res.statusCode < 300 ? 'success' : 'error',
      endpoint: req.path
    });
  });

  next();
});

// SLO 定義 (Service Level Objectives)
const SLOs = {
  availability: {
    target: 0.999, // 99.9% 可用性
    window: '30d',
    description: 'API 成功率 >= 99.9% (30天)'
  },
  latency: {
    target: 0.95, // 95% requests < 500ms
    threshold: 0.5, // 500ms
    window: '30d',
    description: 'P95 延遲 <= 500ms (30天)'
  },
  freshness: {
    target: 0.99, // 99% webhooks processed within 30s
    threshold: 30,
    window: '1d',
    description: 'Webhook 處理時間 <= 30秒 (1天)'
  }
};

// SLO 計算與告警
async function checkSLOs() {
  const results = await prometheusQuery(`
    # Availability SLO
    sum(rate(api_requests_total{status="success"}[30d])) /
    sum(rate(api_requests_total[30d]))
  `);

  const availability = results.value;

  if (availability < SLOs.availability.target) {
    alertManager.fire({
      severity: 'critical',
      summary: 'SLO Violation: Availability',
      description: `Current: ${(availability * 100).toFixed(2)}%, Target: ${(SLOs.availability.target * 100)}%`,
      errorBudget: calculateErrorBudget(availability, SLOs.availability.target)
    });
  }
}

function calculateErrorBudget(actual, target) {
  // Error Budget = (1 - Target) - (1 - Actual)
  const allowed = 1 - target; // 允許的錯誤率
  const current = 1 - actual; // 當前錯誤率
  const remaining = allowed - current;

  return {
    allowed: (allowed * 100).toFixed(3) + '%',
    used: (current * 100).toFixed(3) + '%',
    remaining: (remaining * 100).toFixed(3) + '%',
    exhausted: remaining < 0
  };
}
```

---

## Part 7: Troubleshooting Guide

### 7.1 常見問題診斷流程

**問題 1: 認證失敗（401 Unauthorized）**

診斷步驟：
```yaml
Step 1: 檢查 API Key 是否正確
- 確認使用正確環境的 key (test vs live)
- 檢查 key 是否過期或被撤銷
- 檢查 key 的權限範圍 (scope)

Command:
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.example.com/v1/auth/verify

Expected: { "valid": true, "scopes": [...] }

Step 2: 檢查 Authorization Header 格式
- Bearer token 格式: "Bearer sk_xxx"
- Basic auth 格式: "Basic BASE64(username:password)"
- Custom header: 檢查 API 文檔

Step 3: OAuth 專屬檢查
- Access token 是否過期（檢查 expires_in）
- 嘗試用 refresh_token 更新
- 檢查 token 儲存和讀取邏輯

Debug Code:
```javascript
console.log('Token used:', token.substring(0, 10) + '***');
console.log('Expires at:', new Date(expiresAt));
console.log('Is expired:', Date.now() > expiresAt);
```
```

**問題 2: Rate Limiting (429 Too Many Requests)**

診斷步驟：
```yaml
Step 1: 檢查 rate limit headers
Response Headers:
- X-RateLimit-Limit: 100
- X-RateLimit-Remaining: 0
- X-RateLimit-Reset: 1640000000 (UNIX timestamp)
- Retry-After: 60 (seconds)

Step 2: 分析請求模式
- 是否有 retry loop 導致請求暴增？
- 是否多個實例共用同一個 API key？
- 是否有批次處理未限流？

Prometheus Query:
rate(api_requests_total[5m])  # 每秒請求數

Step 3: 實施限流策略
```javascript
// 全域限流器
const Bottleneck = require('bottleneck');

const limiter = new Bottleneck({
  maxConcurrent: 5, // 最多 5 個並發
  minTime: 100, // 每個請求間隔 100ms (= 10 req/s)
  reservoir: 1000, // Token bucket: 1000 tokens
  reservoirRefreshAmount: 1000,
  reservoirRefreshInterval: 60 * 1000 // 每分鐘補充 1000 tokens
});

// 使用
const rateLimitedCall = limiter.wrap(async (url) => {
  return axios.get(url);
});

// 處理 429 錯誤
limiter.on('failed', async (error, jobInfo) => {
  if (error.response?.status === 429) {
    const retryAfter = error.response.headers['retry-after'];
    console.log(`Rate limited, retrying after ${retryAfter}s`);
    return retryAfter * 1000; // Bottleneck 會自動延遲重試
  }
});
```
```

**問題 3: Webhook 未收到或重複**

診斷流程：
```yaml
情況 A: Webhook 未收到

Step 1: 檢查 Webhook URL 可訪問性
- 使用外部工具測試（webhook.site, ngrok）
- 檢查防火牆、Load Balancer 設定
- 確認 HTTPS 憑證有效

Test:
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

Step 2: 檢查服務商 Webhook 日誌
- Stripe Dashboard > Developers > Webhooks > Logs
- 查看 delivery attempts, response codes
- 檢查 signature verification 是否失敗

Step 3: 本地測試
使用 ngrok 暴露本地端點:
ngrok http 3000
# 更新 webhook URL 為 ngrok 提供的 URL

情況 B: Webhook 重複處理

Root Cause:
- 回應時間 > timeout（服務商會重試）
- 未實施冪等性檢查

Solution:
```javascript
// 冪等性 middleware
const processedEvents = new Set();

async function ensureIdempotency(eventId, handler) {
  // 檢查資料庫（持久化）
  const existing = await db.webhookEvents.findOne({ eventId });
  if (existing && existing.status === 'processed') {
    console.log(`Event ${eventId} already processed`);
    return { status: 'duplicate', result: existing.result };
  }

  // 記憶體快取檢查（快速）
  if (processedEvents.has(eventId)) {
    return { status: 'duplicate' };
  }

  // 處理事件
  try {
    const result = await handler();

    // 標記為已處理
    await db.webhookEvents.create({
      eventId,
      status: 'processed',
      result,
      processedAt: new Date()
    });

    processedEvents.add(eventId);
    return { status: 'success', result };

  } catch (error) {
    await db.webhookEvents.create({
      eventId,
      status: 'failed',
      error: error.message,
      failedAt: new Date()
    });
    throw error;
  }
}
```
```

**問題 4: 資料轉換錯誤（Mapping Issues）**

診斷工具：
```javascript
// 資料驗證和調試工具
class DataValidator {
  constructor(schema) {
    this.schema = schema; // JSON Schema
  }

  validate(data, options = {}) {
    const { throwOnError = false, verbose = false } = options;
    const errors = [];

    for (const [field, rules] of Object.entries(this.schema)) {
      const value = this.getNestedValue(data, field);

      // Required check
      if (rules.required && value === undefined) {
        errors.push({ field, error: 'missing', expected: rules.type });
      }

      // Type check
      if (value !== undefined && rules.type) {
        const actualType = Array.isArray(value) ? 'array' : typeof value;
        if (actualType !== rules.type) {
          errors.push({
            field,
            error: 'type_mismatch',
            expected: rules.type,
            actual: actualType,
            value: verbose ? value : undefined
          });
        }
      }

      // Format check
      if (value !== undefined && rules.format) {
        if (!this.checkFormat(value, rules.format)) {
          errors.push({
            field,
            error: 'format_invalid',
            expected: rules.format,
            value: verbose ? value : undefined
          });
        }
      }
    }

    if (errors.length > 0 && throwOnError) {
      const err = new Error('Data validation failed');
      err.errors = errors;
      throw err;
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  getNestedValue(obj, path) {
    return path.split('.').reduce((curr, key) => curr?.[key], obj);
  }

  checkFormat(value, format) {
    const formats = {
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      url: /^https?:\/\/.+/,
      uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      date: (v) => !isNaN(Date.parse(v))
    };

    const checker = formats[format];
    if (typeof checker === 'function') return checker(value);
    if (checker instanceof RegExp) return checker.test(value);
    return true;
  }
}

// 使用
const validator = new DataValidator({
  'id': { type: 'string', required: true, format: 'uuid' },
  'amount': { type: 'number', required: true },
  'currency': { type: 'string', required: true },
  'customer.email': { type: 'string', required: true, format: 'email' },
  'metadata.orderId': { type: 'string', required: false }
});

const result = validator.validate(webhookData, { verbose: true });
if (!result.valid) {
  console.error('Validation errors:', result.errors);
  // [{field: 'customer.email', error: 'format_invalid', expected: 'email', value: 'invalid'}]
}
```

---

## Part 9: 測試與驗證策略

### 9.1 Contract Testing (契約測試)

#### Pact - Consumer-Driven Contract Testing

**概念**: Consumer 定義期望的 API 行為,Provider 驗證是否符合

**Consumer 端測試**:
```javascript
// pact-consumer.spec.js
const { Pact } = require('@pact-foundation/pact');
const { getUser } = require('./api-client');

describe('User API Pact', () => {
  const provider = new Pact({
    consumer: 'FrontendApp',
    provider: 'UserService',
    port: 1234
  });

  beforeAll(() => provider.setup());
  afterAll(() => provider.finalize());

  describe('GET /users/:id', () => {
    it('should return user data', async () => {
      // 定義期望
      await provider.addInteraction({
        state: 'user with id 1 exists',
        uponReceiving: 'a request for user 1',
        withRequest: {
          method: 'GET',
          path: '/users/1',
          headers: {
            Accept: 'application/json'
          }
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            id: 1,
            name: 'John Doe',
            email: 'john@example.com'
          }
        }
      });

      // 執行測試
      const user = await getUser(1);

      expect(user).toEqual({
        id: 1,
        name: 'John Doe',
        email: 'john@example.com'
      });

      // 驗證 Pact
      await provider.verify();
    });
  });
});
```

**Provider 端驗證**:
```javascript
// pact-provider.spec.js
const { Verifier } = require('@pact-foundation/pact');

describe('Pact Verification', () => {
  it('should validate the expectations of FrontendApp', () => {
    return new Verifier({
      provider: 'UserService',
      providerBaseUrl: 'http://localhost:3000',
      pactUrls: ['./pacts/frontendapp-userservice.json'],
      // Provider States
      stateHandlers: {
        'user with id 1 exists': async () => {
          await db.users.create({ id: 1, name: 'John Doe', email: 'john@example.com' });
        }
      }
    }).verifyProvider();
  });
});
```

**優勢**:
- ✅ 快速反饋 - 不需要啟動真實服務
- ✅ 獨立開發 - Frontend/Backend 可獨立測試
- ✅ 契約驗證 - 確保 API 變更不破壞 Consumer

### 9.2 Mock Server 使用

#### WireMock - API Mocking

```java
// WireMock 設定
@RunWith(SpringRunner.class)
@SpringBootTest
public class PaymentIntegrationTest {

    @Rule
    public WireMockRule wireMockRule = new WireMockRule(8089);

    @Test
    public void testStripePaymentSuccess() {
        // 模擬 Stripe API 回應
        stubFor(post(urlEqualTo("/v1/payment_intents"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("{\n" +
                    "  \"id\": \"pi_test_123\",\n" +
                    "  \"object\": \"payment_intent\",\n" +
                    "  \"amount\": 2000,\n" +
                    "  \"status\": \"succeeded\"\n" +
                    "}")));

        // 執行測試
        PaymentResult result = paymentService.createPayment(2000, "usd");

        // 驗證
        assertEquals("pi_test_123", result.getPaymentIntentId());
        assertEquals("succeeded", result.getStatus());

        // 驗證 API 呼叫
        verify(postRequestedFor(urlEqualTo("/v1/payment_intents"))
            .withHeader("Content-Type", equalTo("application/x-www-form-urlencoded")));
    }
}
```

#### MSW (Mock Service Worker) - 前端測試

```javascript
// mocks/handlers.js
import { rest } from 'msw';

export const handlers = [
  // Mock user API
  rest.get('/api/users/:userId', (req, res, ctx) => {
    const { userId } = req.params;

    return res(
      ctx.status(200),
      ctx.json({
        id: userId,
        name: 'John Doe',
        email: 'john@example.com'
      })
    );
  }),

  // Mock error scenario
  rest.post('/api/payments', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({
        error: {
          type: 'api_error',
          message: 'Payment processing failed'
        }
      })
    );
  })
];

// test setup
import { setupServer } from 'msw/node';
import { handlers } from './mocks/handlers';

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 9.3 Integration Testing 策略

#### Testcontainers - 整合測試環境

```java
// 使用 Testcontainers 啟動依賴服務
@Testcontainers
@SpringBootTest
public class DatabaseIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:14")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.redis.host", redis::getHost);
        registry.add("spring.redis.port", redis::getFirstMappedPort);
    }

    @Test
    public void testUserCreationFlow() {
        // 完整的整合測試
        User user = new User("john@example.com", "John Doe");
        User saved = userRepository.save(user);

        assertNotNull(saved.getId());

        // 驗證 Redis cache
        User cached = userCache.get(saved.getId());
        assertNotNull(cached);
        assertEquals("john@example.com", cached.getEmail());
    }
}
```

#### E2E Testing with Real Third-Party Sandbox

```javascript
// Stripe Sandbox 整合測試
describe('Stripe Payment E2E', () => {
  let stripe;

  beforeAll(() => {
    // 使用 Stripe Test Mode
    stripe = new Stripe(process.env.STRIPE_TEST_KEY);
  });

  it('should complete full payment flow', async () => {
    // 1. 建立 Customer
    const customer = await stripe.customers.create({
      email: 'test@example.com',
      name: 'Test User'
    });

    // 2. 建立 Payment Intent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: 2000,
      currency: 'usd',
      customer: customer.id,
      payment_method: 'pm_card_visa', // Test card
      confirm: true
    });

    expect(paymentIntent.status).toBe('succeeded');

    // 3. 驗證 Webhook 觸發
    // (在實際測試中,需要使用 Stripe CLI 轉發 webhook)

    // 4. 清理
    await stripe.customers.del(customer.id);
  });

  it('should handle card decline', async () => {
    const paymentIntent = await stripe.paymentIntents.create({
      amount: 2000,
      currency: 'usd',
      payment_method: 'pm_card_chargeDeclined', // Test declined card
      confirm: true
    }).catch(err => err);

    expect(paymentIntent.code).toBe('card_declined');
  });
});
```

### 9.4 Chaos Engineering for Integrations

#### Simulating Third-Party Failures

```javascript
// Chaos Monkey for API Testing
class ApiChaosMonkey {
  constructor(failureRate = 0.1) {
    this.failureRate = failureRate;
  }

  // 隨機注入失敗
  async call(apiFunction) {
    if (Math.random() < this.failureRate) {
      const failures = [
        { type: 'timeout', delay: 60000 },
        { type: 'server_error', status: 500 },
        { type: 'rate_limit', status: 429 },
        { type: 'network_error', message: 'ECONNREFUSED' }
      ];

      const failure = failures[Math.floor(Math.random() * failures.length)];

      console.log(`[Chaos] Injecting ${failure.type} failure`);

      switch (failure.type) {
        case 'timeout':
          await new Promise(resolve => setTimeout(resolve, failure.delay));
          throw new Error('Request timeout');

        case 'server_error':
          throw { status: failure.status, message: 'Internal Server Error' };

        case 'rate_limit':
          throw { status: failure.status, message: 'Too Many Requests' };

        case 'network_error':
          throw new Error(failure.message);
      }
    }

    return await apiFunction();
  }
}

// 測試
describe('Integration with Chaos', () => {
  const chaos = new ApiChaosMonkey(0.2); // 20% 失敗率

  it('should handle failures gracefully', async () => {
    let attempts = 0;
    let success = false;

    while (attempts < 5 && !success) {
      try {
        const result = await chaos.call(() => apiClient.getUser(1));
        success = true;
        expect(result.id).toBe(1);
      } catch (error) {
        attempts++;
        console.log(`Attempt ${attempts} failed: ${error.message}`);
        await sleep(1000 * attempts); // Exponential backoff
      }
    }

    expect(success).toBe(true);
    console.log(`Success after ${attempts} attempts`);
  });
});
```

---

## Part 10: 擴展性與維護

### 10.1 多整合點管理

#### Integration Registry Pattern

```javascript
// integration-registry.js
class IntegrationRegistry {
  constructor() {
    this.integrations = new Map();
  }

  register(name, config) {
    this.integrations.set(name, {
      name,
      type: config.type, // 'rest', 'graphql', 'soap', 'webhook'
      baseUrl: config.baseUrl,
      auth: config.auth,
      retryPolicy: config.retryPolicy || this.defaultRetryPolicy(),
      timeout: config.timeout || 30000,
      healthCheck: config.healthCheck,
      dependencies: config.dependencies || [],
      status: 'inactive'
    });
  }

  get(name) {
    const integration = this.integrations.get(name);
    if (!integration) {
      throw new Error(`Integration ${name} not found`);
    }
    return integration;
  }

  async healthCheckAll() {
    const results = {};

    for (const [name, integration] of this.integrations) {
      try {
        const startTime = Date.now();
        await integration.healthCheck();
        const latency = Date.now() - startTime;

        results[name] = {
          status: 'healthy',
          latency
        };

        integration.status = 'active';

      } catch (error) {
        results[name] = {
          status: 'unhealthy',
          error: error.message
        };

        integration.status = 'inactive';
      }
    }

    return results;
  }

  getDependencyGraph() {
    const graph = {};

    for (const [name, integration] of this.integrations) {
      graph[name] = {
        type: integration.type,
        dependencies: integration.dependencies,
        status: integration.status
      };
    }

    return graph;
  }
}

// 使用
const registry = new IntegrationRegistry();

registry.register('stripe', {
  type: 'rest',
  baseUrl: 'https://api.stripe.com',
  auth: { type: 'bearer', token: process.env.STRIPE_KEY },
  healthCheck: async () => {
    const response = await fetch('https://api.stripe.com/v1/account', {
      headers: { Authorization: `Bearer ${process.env.STRIPE_KEY}` }
    });
    if (!response.ok) throw new Error('Stripe health check failed');
  }
});

registry.register('salesforce', {
  type: 'rest',
  baseUrl: 'https://login.salesforce.com',
  auth: { type: 'oauth2' },
  dependencies: ['stripe'], // Salesforce depends on Stripe for payment info
  healthCheck: async () => {
    // OAuth health check
  }
});

// 定期健康檢查
setInterval(async () => {
  const health = await registry.healthCheckAll();
  console.log('Integration Health:', health);

  // 發送到監控系統
  metrics.gauge('integration.health', health);
}, 60000); // 每分鐘
```

### 10.2 API Version 管理

#### Versioning Strategies

**策略 1: URL Versioning**
```javascript
// v1/users.js
app.get('/api/v1/users/:id', async (req, res) => {
  const user = await User.findById(req.params.id);
  res.json({
    id: user.id,
    name: user.name,
    email: user.email
  });
});

// v2/users.js (新增欄位)
app.get('/api/v2/users/:id', async (req, res) => {
  const user = await User.findById(req.params.id);
  res.json({
    id: user.id,
    name: user.name,
    email: user.email,
    phone: user.phone, // 新欄位
    createdAt: user.createdAt // 新欄位
  });
});
```

**策略 2: Header Versioning**
```javascript
app.get('/api/users/:id', async (req, res) => {
  const version = req.headers['api-version'] || '1';

  const user = await User.findById(req.params.id);

  let response;
  switch (version) {
    case '1':
      response = { id: user.id, name: user.name, email: user.email };
      break;

    case '2':
      response = {
        id: user.id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        createdAt: user.createdAt
      };
      break;

    default:
      return res.status(400).json({ error: 'Unsupported API version' });
  }

  res.header('API-Version', version);
  res.json(response);
});
```

**策略 3: GraphQL Versioning (欄位廢棄)**
```graphql
type User {
  id: ID!
  name: String!
  email: String!
  phone: String

  # 廢棄欄位標記
  fullName: String @deprecated(reason: "Use 'name' instead")
}

type Query {
  user(id: ID!): User

  # 廢棄查詢標記
  getUser(id: ID!): User @deprecated(reason: "Use 'user' query instead")
}
```

#### Version Sunset Policy

```javascript
// version-sunset.js
class ApiVersionManager {
  constructor() {
    this.versions = {
      'v1': {
        releaseDate: new Date('2023-01-01'),
        deprecationDate: new Date('2024-01-01'),
        sunsetDate: new Date('2024-07-01'),
        status: 'deprecated'
      },
      'v2': {
        releaseDate: new Date('2024-01-01'),
        status: 'current'
      },
      'v3': {
        releaseDate: new Date('2025-01-01'),
        status: 'beta'
      }
    };
  }

  checkVersion(version) {
    const versionInfo = this.versions[version];

    if (!versionInfo) {
      return { allowed: false, reason: 'Version not found' };
    }

    const now = new Date();

    // 已下線
    if (versionInfo.sunsetDate && now > versionInfo.sunsetDate) {
      return {
        allowed: false,
        reason: `Version ${version} was sunset on ${versionInfo.sunsetDate}`
      };
    }

    // 即將廢棄
    if (versionInfo.deprecationDate && now > versionInfo.deprecationDate) {
      return {
        allowed: true,
        warning: `Version ${version} is deprecated and will be sunset on ${versionInfo.sunsetDate}`,
        sunsetDate: versionInfo.sunsetDate
      };
    }

    return { allowed: true, status: versionInfo.status };
  }

  // Middleware
  versionCheckMiddleware() {
    return (req, res, next) => {
      const version = this.extractVersion(req);
      const check = this.checkVersion(version);

      if (!check.allowed) {
        return res.status(410).json({ error: check.reason });
      }

      if (check.warning) {
        res.header('Sunset', check.sunsetDate.toUTCString());
        res.header('Deprecation', 'true');
        res.header('Link', '<https://api.example.com/docs/migration>; rel="sunset"');
      }

      req.apiVersion = version;
      next();
    };
  }

  extractVersion(req) {
    // URL versioning
    const urlMatch = req.path.match(/\/v(\d+)\//);
    if (urlMatch) return `v${urlMatch[1]}`;

    // Header versioning
    return req.headers['api-version'] || 'v2'; // 預設版本
  }
}
```

### 10.3 整合文檔維護

#### OpenAPI/Swagger Auto-Generation

```javascript
// swagger-config.js
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Integration API',
      version: '2.0.0',
      description: 'API for third-party integrations',
      contact: {
        name: 'API Support',
        email: 'api@example.com'
      }
    },
    servers: [
      { url: 'https://api.example.com/v2', description: 'Production' },
      { url: 'https://sandbox.example.com/v2', description: 'Sandbox' }
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT'
        },
        apiKey: {
          type: 'apiKey',
          in: 'header',
          name: 'X-API-Key'
        }
      }
    },
    security: [{ bearerAuth: [] }]
  },
  apis: ['./routes/*.js'] // 自動掃描註解
};

const specs = swaggerJsdoc(options);

app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

/**
 * @swagger
 * /users/{id}:
 *   get:
 *     summary: Get user by ID
 *     tags: [Users]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: User data
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/User'
 *       404:
 *         description: User not found
 */
app.get('/users/:id', async (req, res) => {
  // Implementation
});
```

### 10.4 第三方變更應對

#### Breaking Change Detection

```javascript
// schema-validator.js
class ApiSchemaValidator {
  constructor(schemaRegistry) {
    this.schemas = schemaRegistry;
  }

  async validateResponse(apiName, endpoint, response) {
    const schema = this.schemas.get(`${apiName}.${endpoint}`);

    if (!schema) {
      console.warn(`No schema found for ${apiName}.${endpoint}`);
      return { valid: true, warnings: ['No schema validation'] };
    }

    const validation = this.validate(response, schema);

    if (!validation.valid) {
      // 偵測到 Breaking Change
      await this.handleBreakingChange(apiName, endpoint, validation.errors);
    }

    return validation;
  }

  async handleBreakingChange(apiName, endpoint, errors) {
    console.error(`Breaking change detected in ${apiName}.${endpoint}:`, errors);

    // 1. 記錄到資料庫
    await db.breakingChanges.create({
      apiName,
      endpoint,
      errors: JSON.stringify(errors),
      detectedAt: new Date()
    });

    // 2. 發送告警
    await alertManager.send({
      severity: 'critical',
      title: `Breaking Change: ${apiName}`,
      message: `API ${endpoint} schema validation failed`,
      errors
    });

    // 3. 啟動降級機制（如果有設定）
    if (this.hasFallback(apiName)) {
      await this.activateFallback(apiName);
    }
  }

  validate(data, schema) {
    // 使用 JSON Schema validator
    const Ajv = require('ajv');
    const ajv = new Ajv();
    const validate = ajv.compile(schema);

    const valid = validate(data);

    return {
      valid,
      errors: validate.errors || []
    };
  }
}

// 監控第三方 API 變更
const validator = new ApiSchemaValidator(schemaRegistry);

app.use(async (req, res, next) => {
  const originalJson = res.json;

  res.json = function(data) {
    // 驗證回應 schema
    validator.validateResponse(req.integrationName, req.path, data);

    return originalJson.call(this, data);
  };

  next();
});
```

---

## Part 8: 真實案例研究

### Case Study 1: Stripe Payment Integration

**背景**：
- 電商平台整合 Stripe 支付
- 需求：信用卡支付、訂閱、Webhook 處理
- 挑戰：高可用性（99.9%）、資料一致性、處理失敗重試

**架構設計**：
```yaml
Components:
1. Payment Service (Express.js)
   - /api/payments/create-intent
   - /api/payments/confirm
   - /webhooks/stripe

2. Background Worker (Bull Queue)
   - process-payment-webhook
   - retry-failed-payments

3. Database (PostgreSQL)
   - payments table (transactional data)
   - webhook_events table (idempotency)

4. Monitoring (Prometheus + Grafana)
   - Payment success rate
   - Webhook processing latency
   - Error rate by type
```

**關鍵實作**：

```javascript
// 1. 建立 Payment Intent
app.post('/api/payments/create-intent', async (req, res) => {
  const { amount, currency, customerId, metadata } = req.body;

  try {
    const paymentIntent = await stripe.paymentIntents.create({
      amount,
      currency,
      customer: customerId,
      metadata: {
        orderId: metadata.orderId,
        userId: req.user.id
      },
      automatic_payment_methods: { enabled: true }
    });

    // 儲存到資料庫（狀態：pending）
    await db.payments.create({
      paymentIntentId: paymentIntent.id,
      orderId: metadata.orderId,
      amount,
      currency,
      status: 'pending',
      createdAt: new Date()
    });

    res.json({
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id
    });

  } catch (error) {
    console.error('Failed to create payment intent:', error);
    res.status(500).json({ error: 'Payment creation failed' });
  }
});

// 2. Webhook 處理（非同步）
app.post('/webhooks/stripe', express.raw({ type: 'application/json' }), async (req, res) => {
  const sig = req.headers['stripe-signature'];

  try {
    const event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      WEBHOOK_SECRET
    );

    // 快速回應
    res.json({ received: true });

    // 非同步處理
    await webhookQueue.add('process-stripe-webhook', {
      eventId: event.id,
      eventType: event.type,
      data: event.data.object
    });

  } catch (err) {
    console.error('Webhook error:', err.message);
    res.status(400).send(`Webhook Error: ${err.message}`);
  }
});

// 3. Worker 處理邏輯
webhookQueue.process('process-stripe-webhook', async (job) => {
  const { eventId, eventType, data } = job.data;

  // 冪等性檢查
  const existing = await db.webhookEvents.findOne({ eventId });
  if (existing) return { status: 'duplicate' };

  try {
    switch (eventType) {
      case 'payment_intent.succeeded':
        await handlePaymentSucceeded(data);
        break;
      case 'payment_intent.payment_failed':
        await handlePaymentFailed(data);
        break;
      // ... other events
    }

    await db.webhookEvents.create({
      eventId,
      eventType,
      status: 'processed',
      processedAt: new Date()
    });

  } catch (error) {
    console.error(`Webhook processing failed:`, error);
    await db.webhookEvents.create({
      eventId,
      eventType,
      status: 'failed',
      error: error.message,
      failedAt: new Date()
    });
    throw error; // 觸發重試
  }
});

async function handlePaymentSucceeded(paymentIntent) {
  const { id, amount, metadata } = paymentIntent;

  await db.transaction(async (trx) => {
    // 更新 payment 狀態
    await db.payments.update(
      { paymentIntentId: id },
      { status: 'succeeded', paidAt: new Date() },
      { transaction: trx }
    );

    // 更新 order 狀態
    await db.orders.update(
      { orderId: metadata.orderId },
      { paymentStatus: 'paid', paidAt: new Date() },
      { transaction: trx }
    );

    // 發送確認郵件（非同步）
    await emailQueue.add('send-payment-confirmation', {
      orderId: metadata.orderId,
      amount,
      userId: metadata.userId
    });
  });
}
```

**成果**：
- Payment success rate: 99.95%
- Webhook processing latency P95: 250ms
- Zero duplicate payments (idempotency)
- Failed payments automatically retried (exponential backoff)

---

### Case Study 2: Salesforce CRM Integration

**背景**：
- B2B SaaS 產品整合 Salesforce
- 需求：同步 Leads, Contacts, Opportunities
- 挑戰：大量資料（10萬+ records）、雙向同步、衝突解決

**架構決策**：

```yaml
Integration Pattern: Event-Driven Sync

Components:
1. Sync Engine (Node.js)
   - Bulk API for initial sync
   - Streaming API for real-time updates
   - Conflict resolution logic

2. Data Mapping Layer
   - Field mapping configuration
   - Transform rules
   - Validation

3. Sync Queue (Bull)
   - Batch sync jobs
   - Delta sync jobs
   - Conflict resolution jobs

4. Sync State Database (MongoDB)
   - Sync metadata
   - Conflict records
   - Audit log
```

**關鍵挑戰與解決方案**：

**挑戰 1: 初始同步 10萬+ records**

```javascript
// 使用 Salesforce Bulk API 2.0
class SalesforceBulkSync {
  async initialSync(objectType) {
    // 1. 建立 Bulk Job
    const job = await sf.createBulkJob({
      object: objectType,
      operation: 'query',
      query: `SELECT Id, Name, Email, CreatedDate, LastModifiedDate FROM ${objectType}`
    });

    // 2. 批次處理結果
    const processor = new BatchProcessor({
      batchSize: 1000,
      concurrency: 5
    });

    let recordsProcessed = 0;

    for await (const batch of sf.getBulkJobResults(job.id)) {
      await processor.process(batch, async (record) => {
        const mapped = this.mapSalesforceToInternal(record);
        await db.contacts.upsert(mapped, { conflictFields: ['salesforceId'] });
        recordsProcessed++;

        if (recordsProcessed % 10000 === 0) {
          console.log(`Synced ${recordsProcessed} records`);
          await this.saveCheckpoint(objectType, recordsProcessed);
        }
      });
    }

    console.log(`Initial sync completed: ${recordsProcessed} records`);
  }
}
```

**挑戰 2: 即時雙向同步與衝突解決**

```javascript
// Conflict Resolution Strategy: Last-Write-Wins with Manual Review

class ConflictResolver {
  async resolveConflict(localRecord, remoteRecord) {
    const conflict = {
      localVersion: localRecord,
      remoteVersion: remoteRecord,
      detectedAt: new Date()
    };

    // 比較 lastModifiedDate
    if (remoteRecord.lastModifiedDate > localRecord.lastModifiedDate) {
      // Remote 更新，接受 remote 版本
      console.log(`Conflict resolved: accepting remote version for ${localRecord.id}`);
      return { resolution: 'accept_remote', data: remoteRecord };

    } else if (localRecord.lastModifiedDate > remoteRecord.lastModifiedDate) {
      // Local 更新，推送到 Salesforce
      console.log(`Conflict resolved: pushing local version for ${localRecord.id}`);
      await sf.update(remoteRecord.salesforceId, localRecord);
      return { resolution: 'push_local', data: localRecord };

    } else {
      // 時間戳相同但內容不同，需要人工審查
      console.warn(`Conflict requires manual review: ${localRecord.id}`);
      await db.conflicts.create({
        recordId: localRecord.id,
        objectType: 'Contact',
        localVersion: JSON.stringify(localRecord),
        remoteVersion: JSON.stringify(remoteRecord),
        status: 'pending_review',
        createdAt: new Date()
      });

      return { resolution: 'manual_review_required', conflict };
    }
  }
}
```

**挑戰 3: 監控同步狀態和資料一致性**

```javascript
// 定期一致性檢查
class DataConsistencyChecker {
  async checkConsistency(objectType) {
    console.log(`Running consistency check for ${objectType}...`);

    // 1. 取得兩邊的記錄計數
    const localCount = await db.contacts.count();
    const remoteCount = await sf.count(objectType);

    console.log(`Local: ${localCount}, Remote: ${remoteCount}`);

    // 2. 抽樣檢查（隨機 100 筆）
    const sample = await db.contacts.aggregate([
      { $sample: { size: 100 } }
    ]);

    let inconsistencies = 0;

    for (const localRecord of sample) {
      const remoteRecord = await sf.retrieve(objectType, localRecord.salesforceId);

      const isConsistent = this.compareRecords(localRecord, remoteRecord);
      if (!isConsistent) {
        inconsistencies++;
        console.warn(`Inconsistency detected: ${localRecord.id}`);
        await this.logInconsistency(localRecord, remoteRecord);
      }
    }

    const consistencyRate = ((100 - inconsistencies) / 100) * 100;
    console.log(`Consistency rate: ${consistencyRate}%`);

    // 發送告警（如果一致性 < 95%）
    if (consistencyRate < 95) {
      await alertManager.send({
        severity: 'warning',
        title: 'Data Consistency Issue',
        message: `${objectType} consistency rate dropped to ${consistencyRate}%`
      });
    }

    return { consistencyRate, inconsistencies };
  }

  compareRecords(local, remote) {
    const fields = ['Name', 'Email', 'Phone', 'Company'];

    for (const field of fields) {
      if (local[field] !== remote[field]) {
        return false;
      }
    }

    return true;
  }
}

// 每小時執行一次
cron.schedule('0 * * * *', async () => {
  await checker.checkConsistency('Contact');
  await checker.checkConsistency('Lead');
});
```

**成果**：
- Initial sync: 100K records in 30 minutes
- Real-time sync latency: < 5 seconds
- Data consistency: 99.8%
- Conflict rate: < 0.1% (mostly auto-resolved)

---

## Part 10: 跨系統整合技術

### 10.1 跨語言 API 整合 (Python ↔ Java)

**場景**：Python FastAPI 電商系統 ↔ Spring Boot 進銷存系統

#### API Gateway 統一入口

```yaml
# api-gateway-config.yml (Kong / AWS API Gateway)
services:
  ecommerce-api:
    url: http://ecommerce-python:8000
    routes:
      - paths: ["/api/v1/orders", "/api/v1/products"]
        methods: [GET, POST, PUT]

  inventory-api:
    url: http://inventory-java:8080
    routes:
      - paths: ["/api/v1/inventory", "/api/v1/warehouses"]
        methods: [GET, POST, PUT]

plugins:
  - name: jwt
    config:
      secret_is_base64: false
      key_claim_name: iss
  - name: rate-limiting
    config:
      minute: 100
      policy: redis
```

#### 跨系統資料契約 (Shared Schema)

```json
// shared-schemas/order-event.json (JSON Schema)
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["orderId", "items", "timestamp", "source"],
  "properties": {
    "orderId": { "type": "string", "format": "uuid" },
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["sku", "quantity"],
        "properties": {
          "sku": { "type": "string" },
          "quantity": { "type": "integer", "minimum": 1 },
          "unitPrice": { "type": "number" }
        }
      }
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "source": { "enum": ["ecommerce", "inventory"] }
  }
}
```

#### Python 端 (FastAPI) 呼叫 Java API

```python
# src/integrations/inventory_client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit
import logging

logger = logging.getLogger(__name__)

class InventoryClient:
    """與 Spring Boot 進銷存系統整合的客戶端"""

    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "X-Source-System": "ecommerce-python",
            },
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    @circuit(failure_threshold=5, recovery_timeout=30)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def check_stock(self, sku: str) -> dict:
        response = await self.client.get(f"/api/v1/inventory/stock/{sku}")
        response.raise_for_status()
        return response.json()

    @circuit(failure_threshold=5, recovery_timeout=30)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def reserve_stock(self, order_id: str, items: list[dict]) -> dict:
        response = await self.client.post(
            "/api/v1/inventory/reserve",
            json={"orderId": order_id, "items": items, "source": "ecommerce"},
        )
        response.raise_for_status()
        return response.json()
```

#### Java 端 (Spring Boot) 呼叫 Python API

```java
// src/main/java/com/inventory/integration/EcommerceClient.java
@Component
@Slf4j
public class EcommerceClient {

    private final WebClient webClient;

    public EcommerceClient(
            @Value("${integration.ecommerce.base-url}") String baseUrl,
            @Value("${integration.ecommerce.api-key}") String apiKey) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader("X-API-Key", apiKey)
                .defaultHeader("X-Source-System", "inventory-java")
                .filter(retryFilter())
                .build();
    }

    private ExchangeFilterFunction retryFilter() {
        return (request, next) -> next.exchange(request)
                .retryWhen(Retry.backoff(3, Duration.ofSeconds(1))
                        .maxBackoff(Duration.ofSeconds(10))
                        .filter(ex -> ex instanceof WebClientResponseException.ServiceUnavailable
                                || ex instanceof ConnectException));
    }

    public Mono<OrderDto> getOrder(String orderId) {
        return webClient.get()
                .uri("/api/v1/orders/{id}", orderId)
                .retrieve()
                .bodyToMono(OrderDto.class)
                .doOnError(e -> log.error("Failed to fetch order {}: {}", orderId, e.getMessage()));
    }

    public Mono<Void> notifyShipment(String orderId, ShipmentDto shipment) {
        return webClient.post()
                .uri("/api/v1/orders/{id}/shipment", orderId)
                .bodyValue(shipment)
                .retrieve()
                .bodyToMono(Void.class);
    }
}
```

---

### 10.2 雙 PostgreSQL 資料庫同步

**場景**：電商 DB (PostgreSQL A) ↔ 進銷存 DB (PostgreSQL B)

#### 同步策略比較

| 策略 | 延遲 | 一致性 | 複雜度 | 適用場景 |
|------|------|--------|--------|---------|
| CDC (Debezium) | 秒級 | 最終一致 | 中 | 即時庫存同步 |
| 事件驅動 (MQ) | 秒級 | 最終一致 | 中高 | 訂單狀態同步 |
| ETL 批次 | 分鐘~小時 | 批次一致 | 低 | 報表、歷史資料 |
| 雙寫 | 即時 | 強一致 | 高 | 關鍵交易（不推薦） |

#### CDC 方案 (Debezium + Kafka)

```yaml
# docker-compose.cdc.yml
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092

  debezium-ecommerce:
    image: debezium/connect:2.4
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      CONFIG_STORAGE_TOPIC: ecommerce-configs
      OFFSET_STORAGE_TOPIC: ecommerce-offsets

  debezium-inventory:
    image: debezium/connect:2.4
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      CONFIG_STORAGE_TOPIC: inventory-configs
      OFFSET_STORAGE_TOPIC: inventory-offsets
```

```json
// debezium-ecommerce-connector.json
{
  "name": "ecommerce-postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "ecommerce-db",
    "database.port": "5432",
    "database.dbname": "ecommerce",
    "database.user": "debezium",
    "table.include.list": "public.orders,public.order_items,public.products",
    "topic.prefix": "ecommerce",
    "slot.name": "ecommerce_slot",
    "publication.name": "ecommerce_pub",
    "transforms": "route",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "ecommerce\\.public\\.(.*)",
    "transforms.route.replacement": "sync.$1"
  }
}
```

#### 事件驅動方案 (Redis Pub/Sub 輕量版)

```python
# Python 端：發布訂單事件
import redis.asyncio as aioredis
import json

class OrderEventPublisher:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    async def publish_order_created(self, order: dict):
        event = {
            "type": "order.created",
            "source": "ecommerce",
            "data": order,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.redis.publish("cross-system:orders", json.dumps(event))
```

```java
// Java 端：訂閱訂單事件
@Component
@Slf4j
public class OrderEventSubscriber {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @PostConstruct
    public void subscribe() {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(redisTemplate.getConnectionFactory());
        container.addMessageListener(
            (message, pattern) -> {
                String body = new String(message.getBody());
                OrderEvent event = objectMapper.readValue(body, OrderEvent.class);
                handleOrderEvent(event);
            },
            new ChannelTopic("cross-system:orders")
        );
        container.start();
    }

    private void handleOrderEvent(OrderEvent event) {
        switch (event.getType()) {
            case "order.created" -> inventoryService.reserveStock(event.getData());
            case "order.cancelled" -> inventoryService.releaseStock(event.getData());
            default -> log.warn("Unknown event type: {}", event.getType());
        }
    }
}
```

---

### 10.3 前端整合策略 (Vue 3 ↔ React/Next.js)

#### 方案比較

| 方案 | 獨立部署 | 共享狀態 | 技術耦合 | 適用場景 |
|------|---------|---------|---------|---------|
| Module Federation | ✅ | 可選 | 低 | 大規模微前端 |
| iframe | ✅ | postMessage | 無 | 快速隔離整合 |
| Web Components | ✅ | Props/Events | 低 | 跨框架元件共享 |
| Reverse Proxy | ✅ | Cookie/Token | 無 | 路由級別整合 |

#### Reverse Proxy 路由級整合 (推薦起步方案)

```nginx
# nginx.conf
upstream ecommerce_frontend {
    server ecommerce-vue:3000;
}
upstream inventory_frontend {
    server inventory-nextjs:3001;
}

server {
    listen 80;
    server_name app.example.com;

    # 電商模組 (Vue 3)
    location /shop/ {
        proxy_pass http://ecommerce_frontend/;
    }

    # 進銷存模組 (Next.js)
    location /inventory/ {
        proxy_pass http://inventory_frontend/;
    }

    # 共用認證
    location /api/auth/ {
        proxy_pass http://auth-service:4000/;
    }
}
```

---

### 10.4 統一認證方案

#### JWT 共享策略

```
┌──────────────────────────────────────────────────┐
│                 Auth Service (SSO)                │
│            簽發 JWT (共用 Secret/公鑰)              │
└────────┬──────────────────────────────┬───────────┘
         │ JWT                          │ JWT
    ┌────▼────┐                    ┌────▼────┐
    │ Python  │                    │  Java   │
    │ FastAPI │                    │ Spring  │
    │ (驗證)   │                    │ (驗證)   │
    └─────────┘                    └─────────┘
```

```python
# Python 端 JWT 驗證
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()
PUBLIC_KEY = open("keys/auth-service-public.pem").read()

async def verify_token(credentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience="ecommerce-api",
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

```java
// Java 端 JWT 驗證 (Spring Security)
@Configuration
@EnableWebSecurity
public class JwtSecurityConfig {

    @Value("${auth.public-key-path}")
    private String publicKeyPath;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt.decoder(jwtDecoder()))
        );
        return http.build();
    }

    @Bean
    public JwtDecoder jwtDecoder() {
        RSAPublicKey publicKey = loadPublicKey(publicKeyPath);
        return NimbusJwtDecoder.withPublicKey(publicKey).build();
    }
}
```

---

## 總結

本深度技術指南涵蓋了系統整合的進階主題，包括：

✅ **認證機制深度解析**（OAuth 2.0 完整實作、API Key 安全管理）
✅ **資料轉換進階技術**（大規模批次處理、複雜資料映射）
✅ **錯誤處理與容錯策略**（智能重試、Circuit Breaker）
✅ **效能優化指南**（高並發 Webhook、批次請求優化）
✅ **安全性最佳實踐**（Signature 驗證、敏感資料遮罩）
✅ **監控與 Observability**（分散式追蹤、SLI/SLO 監控）
✅ **Troubleshooting Guide**（常見問題診斷與解決）
✅ **真實案例研究**（Stripe、Salesforce 整合實戰）
✅ **跨系統整合技術**（Python↔Java API、雙 DB 同步、前端整合、統一認證）

---

## 📚 延伸閱讀

- [Integration SOP 完整版](./SOP.md)
- [Integration QuickRef 快速參考](./SOP_QuickRef.md)
- [Integration 快速啟動指令集](../../prompts/scenario-prompts/integration-prompts.md)
- [integration-analysis-flow Workflow](../../workflow/scenario-specific/integration-analysis-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 外部參考
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Stripe API Best Practices](https://stripe.com/docs/api)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Site Reliability Engineering (Google)](https://sre.google/books/)
- [Designing Data-Intensive Applications](https://dataintensive.net/)

### 相關 Agents
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - Integration Specialist（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（整合架構設計）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（整合測試規劃）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（認證與授權實作）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（監控與告警）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（OAuth/支付/敏感資料，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（高頻 API/大量同步，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端整合架構，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端整合測試，選用）

### 相關 Skills
- `/integration-api-client` - API 客戶端建立（錯誤處理、重試、型別安全）
- `/integration-oauth` - OAuth 2.0 認證整合
- `/integration-stripe` - Stripe 支付整合
- `/integration-webhook` - Webhook 處理系統
- `/integration-database` - 資料庫整合（PostgreSQL、連線池、讀寫分離）
- `/integration-redis` - Redis 快取整合
- `/documentation-api` - API 文檔生成（OpenAPI/Swagger）
- `/security-audit` - 安全審查（OWASP Top 10）
- `/qa-testing` - 測試策略與測試計畫
- `/devops-monitoring` - 監控告警系統（Prometheus/Grafana）
- `/mobile-development` - 行動端整合開發（涉及 Android/iOS/macOS 時）

---

**文檔版本: v0.01
**最後更新**: 2026-02-15
**維護者**: AISDLC Framework Team
