# Security Architecture Document — Template
# 安全架構文件（SAD）模板
# Phase 05 — Security 情境 SDD 強化（Stage 2）

**文件類型**: Security Architecture Document (SAD)
**SDD Gate**: SCG-5 Security Spec Gate（SAD 凍結）
**使用時機**: STRIDE 威脅模型完成後，開發開始前
**存放位置**: `docs/06_quality/security/SAD-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **版本** | v{1.0} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer} |
| **SCG Gate** | SCG-5 □ 待審 / □ 通過（SAD 凍結） |
| **前置文件** | STRIDE-THREAT-MODEL, ASSET-INVENTORY, TRUST-BOUNDARY-MAP |

---

## 1. 安全目標（Security Objectives）

| 目標 | 說明 | 對應威脅 |
|------|------|---------|
| 機密性（Confidentiality） | 確保資料僅被授權方存取 | STR-I-* |
| 完整性（Integrity） | 確保資料未被未授權竄改 | STR-T-* |
| 可用性（Availability） | 確保服務在需要時可存取 | STR-D-* |
| 不可否認性（Non-Repudiation） | 確保操作有不可否認的記錄 | STR-R-* |
| 最小權限（Least Privilege） | 每個實體僅有必要的權限 | STR-E-* |

---

## 2. 認證與授權規格（Authentication & Authorization）

### 2.1 認證機制規格

| 場景 | 認證方式 | 技術實作 | ADR 參考 |
|------|---------|---------|---------|
| 使用者登入 | Username + Password + MFA | {Auth0/Okta/自建} | ADR-{NNN} |
| API 存取（外部） | JWT Bearer Token（RS256） | 15 min 有效期 + Refresh Token | ADR-{NNN} |
| 服務間通信 | mTLS + Service Account | Service Mesh（Istio） | ADR-{NNN} |
| 管理員存取 | MFA + IP Whitelist + Session | {tool} | ADR-{NNN} |
| CI/CD Pipeline | OIDC Token（無長效 Secret） | GitHub Actions OIDC | ADR-{NNN} |

### 2.2 JWT Token 規格

```json
{
  "標頭 Header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "{key_id}"
  },
  "載荷 Payload": {
    "sub": "{user_id}",
    "iss": "{issuer}",
    "aud": "{audience}",
    "iat": "{issued_at}",
    "exp": "{expiry: iat + 900}",
    "jti": "{unique_token_id}",
    "scope": "{permission_scopes}",
    "roles": ["{role_list}"]
  },
  "規則": {
    "有效期": "15 分鐘（Access Token）",
    "Refresh Token": "7 天（HttpOnly Cookie）",
    "輪換策略": "每次 Refresh 後輪換 Refresh Token"
  }
}
```

### 2.3 授權模型規格（RBAC）

| 角色 | 說明 | 可存取資源 | 禁止操作 |
|------|------|----------|---------|
| Anonymous | 未登入使用者 | 公開 API 只讀 | 所有寫操作 |
| User | 一般登入使用者 | 自己的資源 | 他人資源、管理 API |
| Admin | 系統管理員 | 所有資源管理 | 刪除稽核日誌 |
| ServiceAccount | 服務間通信 | 指定 API 端點 | 管理員功能 |
| Super-Admin | 最高權限 | 全部 | 無（需 MFA + Audit） |

### 2.4 授權驗證規則

```
每個 API 請求必須：
1. 驗證 JWT Token 有效性（Signature + Expiry）
2. 驗證 Token 中的角色有存取此端點的權限
3. 驗證資源擁有者（Resource Ownership Check）
4. 記錄存取日誌（WHO + WHAT + WHEN + RESULT）

預設拒絕原則：任何未明確授權的存取 → HTTP 403
```

---

## 3. 資料分類與加密規格

### 3.1 資料分類規格

| 分類 | 定義 | 典型資料 | 加密要求 | 存取控制 | 保留期限 |
|------|------|---------|---------|---------|---------|
| Critical | 直接財務或法規影響 | 支付卡號、密碼 Hash | 傳輸 + 靜態雙重加密 | MFA + RBAC | 依法規 |
| High/PII | 個人識別資訊 | 姓名、Email、電話 | 傳輸加密 + 靜態加密 | RBAC + 最小權限 | 3 年或依 GDPR |
| Internal | 內部業務資料 | 訂單資訊、日誌 | 傳輸加密 | RBAC | 1 年 |
| Public | 公開資訊 | 產品目錄、FAQ | 傳輸加密（完整性） | 無特殊限制 | 無限制 |

### 3.2 加密規格

| 場景 | 算法 | 金鑰長度 | 實作方式 |
|------|------|---------|---------|
| HTTPS 傳輸 | TLS 1.3 | — | Nginx/ALB 強制 TLS 1.3 |
| 靜態 PII | AES-256-GCM | 256-bit | 應用層加密後存 DB |
| 密碼存儲 | bcrypt | cost=12 | 不可逆 Hash，不存明文 |
| Secrets 存儲 | AES-256 | — | Secrets Manager 加密 |
| DB 磁碟 | AES-256-XTS | 256-bit | DB 透明加密（TDE） |
| 備份 | AES-256-GCM | 256-bit | 備份前加密 |

### 3.3 金鑰管理規格

```
金鑰生命週期：
  1. 產生：使用 Secrets Manager（非自訂算法）
  2. 存儲：僅存於 Secrets Manager，永不明文存 Code
  3. 輪換：
     - JWT Signing Key: 每 90 天自動輪換
     - API Key: 每 180 天強制輪換
     - DB Encryption Key: 每年輪換
  4. 吊銷：立即吊銷機制（Revocation List）
  5. 存取：最小權限，僅允許特定 Service Account 存取
```

---

## 4. 安全 API 規格

### 4.1 安全標頭規格

```http
# 所有 API Response 必須包含的安全標頭
Content-Security-Policy: default-src 'self'; script-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
```

### 4.2 輸入驗證規格

```
所有 API 輸入必須：
1. 白名單驗證（Allowlist）：僅接受已知合法輸入
2. 長度限制：每個欄位有明確最大長度
3. 類型驗證：強制類型轉換，拒絕類型不符
4. SQL 防護：ORM 參數化查詢，禁止字串拼接
5. XSS 防護：輸出時 HTML Encode
6. 檔案上傳：驗證 MIME Type + 副檔名 + 掃描
```

### 4.3 錯誤回應規格

```json
// 統一錯誤格式（不洩漏系統資訊）
{
  "error": {
    "code": "AUTH_001",     // 業務錯誤碼
    "message": "Authentication failed",  // 通用訊息
    "request_id": "uuid"    // 追蹤用（不含敏感資訊）
  }
}
// ❌ 禁止回傳：stack trace, SQL 錯誤, 系統路徑, 版本資訊
```

---

## 5. 稽核日誌規格

### 5.1 必須記錄的事件

| 事件類別 | 必記事件 | 日誌欄位 |
|---------|---------|---------|
| 認證事件 | 登入成功/失敗、登出、Token 刷新 | user_id, ip, timestamp, result |
| 授權事件 | 存取拒絕、權限提升 | user_id, resource, action, result |
| 資料存取 | Critical/High 資料讀取 | user_id, data_id, action, timestamp |
| 資料修改 | 所有寫入操作（含舊值/新值） | user_id, resource_id, before, after |
| 系統事件 | 配置變更、服務啟停 | admin_id, action, timestamp |
| 安全事件 | 掃描偵測、異常行為 | ip, pattern, severity, timestamp |

### 5.2 日誌保護規格

```
1. 不可竄改（Immutable）：使用 WORM 存儲或 Append-Only Log
2. 加密傳輸：日誌傳輸使用 TLS 加密
3. 存取控制：僅安全/稽核人員可讀，任何人不可刪除
4. 保留期限：最少 90 天線上 + 1 年歸檔
5. 格式：結構化 JSON（支持 SIEM 查詢）
```

---

## 6. 安全控制清單（Security Controls）

| 控制 ID | 控制類別 | 描述 | 對應威脅 | 實作優先級 |
|--------|---------|------|---------|----------|
| SC-001 | Authentication | JWT RS256，15min 有效期 | STR-S-001 | P0 |
| SC-002 | Rate Limiting | {N} req/min/IP | STR-S-002, STR-D-001 | P0 |
| SC-003 | Input Validation | ORM 參數化，Allowlist | STR-T-001 | P0 |
| SC-004 | Authorization | RBAC + 資源擁有者驗證 | STR-E-001, STR-E-002 | P0 |
| SC-005 | Encryption-Transit | TLS 1.3 強制 | STR-I-*, STR-T-002 | P0 |
| SC-006 | Encryption-Rest | AES-256 PII/PCI 加密 | STR-I-002 | P0 |
| SC-007 | Audit Logging | 不可竄改稽核日誌 | STR-R-001 | P1 |
| SC-008 | Error Handling | 統一錯誤格式，不洩漏資訊 | STR-I-001 | P1 |
| SC-{NNN} | {category} | {description} | {STR-IDs} | {priority} |

---

## 📋 SCG-5 SAD 凍結確認

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| 認證規格完整 | JWT 規格、角色定義 | □ |
| 資料分類完整 | Critical/High/Internal/Public 均有規格 | □ |
| 加密規格完整 | 傳輸 + 靜態 + 金鑰管理 | □ |
| API 安全規格 | 安全標頭 + 輸入驗證 + 錯誤格式 | □ |
| 稽核日誌規格 | 必記事件 + 保護機制 | □ |
| 安全控制清單 | 每個控制對應威脅 | □ |
| 與 STRIDE 完全對應 | 所有高/關鍵威脅有對應控制 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過（SAD 凍結）/ □ 待修訂
