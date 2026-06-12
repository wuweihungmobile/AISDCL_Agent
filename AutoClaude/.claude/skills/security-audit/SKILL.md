---
name: security
description: 執行安全審查，識別漏洞並提供修復建議，基於 OWASP Top 10
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: 審查範圍 (full/api/frontend/dependencies)] [standard: 合規標準 (owasp/gdpr/pci-dss)]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Security Audit Skill

基於 AISDLC Security 情境的安全審查技能。

---

## 觸發方式

```bash
/security                      # 完整安全審查
/security api                  # API 安全審查
/security dependencies         # 依賴漏洞掃描
/security --standard=owasp     # OWASP 合規檢查
```

---

## 執行流程

### 階段 1: 自動化掃描 (10分鐘)

**依賴漏洞掃描**:
```bash
# NPM
npm audit --json > audit-report.json

# 詳細報告
npm audit --audit-level=moderate
```

**程式碼靜態分析**:
```bash
# ESLint 安全規則
npx eslint . --plugin security --rule 'security/detect-object-injection: error'

# Semgrep (推薦)
semgrep --config=p/owasp-top-ten .
```

---

### 階段 2: OWASP Top 10 檢查清單

#### A01: Broken Access Control

- [ ] 路由權限驗證
- [ ] API 端點授權檢查
- [ ] 資源存取控制 (RBAC/ABAC)
- [ ] 敏感操作二次驗證

**常見問題**:
```typescript
// ❌ 不安全
app.get('/api/users/:id', (req, res) => {
  return db.users.findById(req.params.id); // 任何人可存取任何用戶
});

// ✅ 安全
app.get('/api/users/:id', auth, (req, res) => {
  if (req.user.id !== req.params.id && !req.user.isAdmin) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  return db.users.findById(req.params.id);
});
```

#### A02: Cryptographic Failures

- [ ] 敏感資料加密儲存
- [ ] HTTPS 強制啟用
- [ ] 密碼使用 bcrypt/argon2
- [ ] API Keys 不寫死在程式碼

#### A03: Injection

- [ ] SQL 參數化查詢
- [ ] NoSQL 查詢驗證
- [ ] 命令注入防護
- [ ] XSS 輸出編碼

**SQL Injection 防護**:
```typescript
// ❌ 不安全
const query = `SELECT * FROM users WHERE id = ${userId}`;

// ✅ 安全 (Prisma)
const user = await prisma.user.findUnique({ where: { id: userId } });

// ✅ 安全 (Raw SQL)
const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);
```

#### A04: Insecure Design

- [ ] 威脅建模已完成
- [ ] 安全需求已定義
- [ ] 限流機制已實作

#### A05: Security Misconfiguration

- [ ] 錯誤訊息不洩漏敏感資訊
- [ ] 預設帳密已變更
- [ ] 不必要的功能已停用
- [ ] CORS 設定正確

**CORS 配置範例**:
```typescript
// ✅ 安全的 CORS 設定
app.use(cors({
  origin: ['https://yourdomain.com'],
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  credentials: true,
}));
```

#### A06: Vulnerable Components

- [ ] 無高風險漏洞依賴
- [ ] 依賴版本定期更新
- [ ] 未使用的依賴已移除

#### A07: Authentication Failures

- [ ] 強密碼政策
- [ ] 登入失敗限制
- [ ] Session 管理安全
- [ ] MFA 支援 (高風險系統)

#### A08: Data Integrity Failures

- [ ] CI/CD Pipeline 安全
- [ ] 依賴來源可信
- [ ] 程式碼簽章

#### A09: Logging & Monitoring

- [ ] 安全事件記錄
- [ ] 日誌不含敏感資料
- [ ] 異常行為告警

#### A10: SSRF

- [ ] 外部 URL 驗證
- [ ] 內網存取限制

---

### 階段 3: API 安全檢查

**必要標頭**:
```typescript
// 安全標頭中介層
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('Content-Security-Policy', "default-src 'self'");
  next();
});
```

**Rate Limiting**:
```typescript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 分鐘
  max: 100, // 最多 100 請求
  message: 'Too many requests',
});

app.use('/api/', limiter);
```

---

### 階段 4: 產出報告 🔴

**安全審查報告結構**:
```markdown
## 安全審查報告

### 執行摘要
- 審查日期: YYYY-MM-DD
- 審查範圍: [範圍描述]
- 風險等級: 高/中/低

### 發現問題

#### 🔴 高風險 (需立即處理)
1. [問題描述]
   - 位置: [檔案:行號]
   - 影響: [影響說明]
   - 修復建議: [建議]

#### 🟡 中風險 (建議修復)
...

#### ⚪ 低風險 (可延後)
...

### 合規檢查
- [ ] OWASP Top 10: X/10 通過
- [ ] 依賴漏洞: X 個高風險
```

🔴 **確認點**: 確認優先處理的問題

---

## 產出物

| 產出物 | 說明 |
|--------|------|
| 安全審查報告 | 問題清單與修復建議 |
| 依賴漏洞報告 | npm audit 結果 |
| 修復驗證 | 修復後重新掃描結果 |

---

## 相關 Skill

- `/integration-oauth` - 認證安全
- `/testing` - 安全測試

---


## 相關檔案

- SOP 參考: `scenarios/security/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Security 情境
