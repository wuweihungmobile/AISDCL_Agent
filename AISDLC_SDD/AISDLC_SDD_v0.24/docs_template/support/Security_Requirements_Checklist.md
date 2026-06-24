# 安全需求檢查清單（基於 STRIDE）
# Security Requirements Checklist (STRIDE-based)

**版本**: v0.01
**建立日期**: 2025-12-13
**適用階段**: Greenfield Stage 2（需求分析與驗證）
**目標使用者**: SA, Security Engineer, BA

---

## 📋 使用說明

本檢查清單協助快速產出安全需求（NFR-SEC-xxx），涵蓋 OWASP Top 10 和 STRIDE 6 大威脅類別。

**使用方式**:
1. 根據專案特性勾選適用的安全需求
2. 將勾選項目轉為 NFR-SEC-xxx 格式
3. 定義可驗證的驗收標準
4. 納入 FRD「非功能性需求」章節

---

## 🛡️ 類別 1: 認證與授權（Authentication & Authorization）

**對應 STRIDE**: Spoofing（S）、Elevation of Privilege（E）
**對應 OWASP**: A01 - Broken Access Control

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-001-01: 使用者認證**
  - 所有 API 請求必須包含有效的 JWT Token
  - JWT 必須簽名（RS256 或 HS256）
  - Access Token 有效期限 ≤ 30 分鐘
  - Refresh Token 有效期限 ≤ 30 天

- [ ] **NFR-SEC-001-02: 權限驗證**
  - 每個 API 端點必須驗證使用者角色
  - 使用者僅能存取自己的資源
  - 管理員操作必須二次驗證

- [ ] **NFR-SEC-001-03: 密碼安全**
  - 密碼使用 bcrypt/Argon2 加密（salt round ≥ 12）
  - 禁止儲存明文密碼
  - 密碼長度 ≥ 8 字元，包含大小寫、數字、特殊字元

### 進階需求（依專案需要）

- [ ] **NFR-SEC-001-04: 多因素認證（MFA）**
  - 提供 TOTP（如 Google Authenticator）
  - 高敏感操作強制 MFA

- [ ] **NFR-SEC-001-05: SSO 整合**
  - 支援 OAuth 2.0 / SAML 2.0
  - 整合 Google / Microsoft / 企業 SSO

- [ ] **NFR-SEC-001-06: Session 管理**
  - 支援強制登出所有裝置
  - Session Timeout: 30 分鐘無活動自動登出

---

## 🔒 類別 2: 輸入驗證與防篡改（Input Validation & Tampering Prevention）

**對應 STRIDE**: Tampering（T）
**對應 OWASP**: A03 - Injection

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-002-01: 輸入驗證**
  - 前端 + 後端雙層驗證
  - API Request 使用 JSON Schema 驗證
  - 不符合 Schema 回傳 400 Bad Request

- [ ] **NFR-SEC-002-02: SQL Injection 防護**
  - 使用 ORM Prepared Statements
  - 禁止拼接 SQL 字串
  - 輸入特殊字元過濾/轉義

- [ ] **NFR-SEC-002-03: XSS 防護**
  - 所有使用者輸入顯示前必須 HTML 編碼
  - Content-Security-Policy (CSP) Header
  - 禁止 `eval()` 和 `innerHTML`

### 進階需求（依專案需要）

- [ ] **NFR-SEC-002-04: CSRF 防護**
  - 使用 CSRF Token（同步 Token 模式）
  - SameSite Cookie 屬性
  - Double Submit Cookie

- [ ] **NFR-SEC-002-05: 業務邏輯防篡改**
  - 關鍵計算（價格、折扣）必須由後端重算
  - Request Signature 驗證（HMAC）

- [ ] **NFR-SEC-002-06: 檔案上傳驗證**
  - 檔案類型白名單（MIME Type 驗證）
  - 檔案大小限制（≤ 10MB）
  - 病毒掃描（ClamAV）

---

## 🚫 類別 3: 敏感資料保護（Information Disclosure Prevention）

**對應 STRIDE**: Information Disclosure（I）
**對應 OWASP**: A02 - Cryptographic Failures

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-003-01: HTTPS 強制**
  - 所有 HTTP 請求自動重導向至 HTTPS
  - HSTS Header (Strict-Transport-Security)
  - TLS 1.2+

- [ ] **NFR-SEC-003-02: 敏感資料加密**
  - 密碼使用 bcrypt/Argon2 加密
  - 個資（身分證、信用卡）使用 AES-256 加密
  - 加密金鑰儲存在 KMS（Key Management Service）

- [ ] **NFR-SEC-003-03: 權限過濾**
  - API 回應僅包含授權資料
  - 使用者 A 無法讀取使用者 B 的資料
  - 錯誤訊息不洩露系統資訊（SQL 錯誤、Stack Trace）

### 進階需求（依專案需要）

- [ ] **NFR-SEC-003-04: 資料庫備份加密**
  - 備份檔案使用 AES-256 加密
  - 金鑰分離儲存（不與備份檔案同處）

- [ ] **NFR-SEC-003-05: 資料遮罩（Data Masking）**
  - 日誌中敏感資料遮罩（如信用卡 `****-****-****-1234`）
  - 測試環境使用假資料（不使用生產資料）

- [ ] **NFR-SEC-003-06: PII 合規**
  - 符合 GDPR / CCPA / 個資法
  - 提供使用者資料匯出功能（Data Portability）
  - 提供使用者資料刪除功能（Right to be Forgotten）

---

## 📝 類別 4: 日誌與審計（Logging & Auditing）

**對應 STRIDE**: Repudiation（R）

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-004-01: 認證操作日誌**
  - 登入成功/失敗
  - 登出
  - 密碼修改

- [ ] **NFR-SEC-004-02: 業務操作日誌**
  - 關鍵業務操作（建立訂單、付款、取消）
  - 資料修改（UPDATE/DELETE）

- [ ] **NFR-SEC-004-03: 日誌格式**
  - 包含：時間戳、使用者 ID、IP 位址、操作類型、結果
  - 使用 JSON 格式
  - 敏感資料遮罩（密碼、信用卡）

### 進階需求（依專案需要）

- [ ] **NFR-SEC-004-04: 集中化日誌管理**
  - ELK Stack / CloudWatch Logs / Datadog
  - 日誌保留期限 ≥ 90 天

- [ ] **NFR-SEC-004-05: 異常行為偵測**
  - 失敗登入 ≥ 5 次觸發警報
  - IP 異地登入警報
  - 異常 API 呼叫頻率警報

---

## ⏱️ 類別 5: API Rate Limiting & DoS 防護

**對應 STRIDE**: Denial of Service（D）

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-005-01: 登入 API 限流**
  - 每 IP 每分鐘最多 5 次請求
  - 超過限制回傳 429 Too Many Requests

- [ ] **NFR-SEC-005-02: 一般 API 限流**
  - 每使用者每秒最多 10 次請求
  - 每 IP 每分鐘最多 100 次請求（未登入）

- [ ] **NFR-SEC-005-03: Rate Limit Header**
  - `X-RateLimit-Limit`: 限制值
  - `X-RateLimit-Remaining`: 剩餘次數
  - `X-RateLimit-Reset`: 重置時間戳

### 進階需求（依專案需要）

- [ ] **NFR-SEC-005-04: DDoS 防護**
  - 使用 Cloudflare / AWS Shield
  - Web Application Firewall (WAF)

- [ ] **NFR-SEC-005-05: 資源限制**
  - API Timeout: 30 秒
  - 檔案上傳大小限制: 10MB
  - Database Query Timeout: 10 秒

---

## ✅ 類別 6: 安全配置（Security Configuration）

**對應 OWASP**: A05 - Security Misconfiguration

### 基礎需求（所有專案必須）

- [ ] **NFR-SEC-006-01: 安全 HTTP Headers**
  - `Strict-Transport-Security` (HSTS)
  - `Content-Security-Policy` (CSP)
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`

- [ ] **NFR-SEC-006-02: 環境變數管理**
  - 敏感資訊（API 金鑰、密碼）不可硬編碼
  - 使用環境變數或 Secret Manager

- [ ] **NFR-SEC-006-03: 最小權限原則**
  - 應用層資料庫帳號僅 CRUD 權限（非 root）
  - 檔案系統權限最小化

### 進階需求（依專案需要）

- [ ] **NFR-SEC-006-04: 定期安全掃描**
  - OWASP ZAP / Burp Suite 掃描
  - Dependency 漏洞掃描（npm audit / Snyk）

- [ ] **NFR-SEC-006-05: 安全開發流程**
  - Code Review 包含安全檢查
  - Pre-commit Hook 掃描敏感資訊洩露

---

## 📊 快速評估表

### 評估專案適用的安全需求

| 專案特性 | 建議包含的安全需求類別 |
|---------|-------------------|
| **處理個資** | 類別 1, 3, 4, 6 |
| **處理金流** | 類別 1, 2, 3, 4, 5, 6（全部） |
| **公開 API** | 類別 1, 2, 5, 6 |
| **內部系統** | 類別 1, 2, 6 |
| **MVP 快速上線** | 類別 1（基礎）, 2（基礎）, 3（基礎）|

---

## 📝 NFR-SEC 範本

將勾選的安全需求轉為以下格式：

```markdown
### NFR-SEC-XXX: [需求標題]

**需求來源**: STRIDE 分析 - [Spoofing / Tampering / ...]

**需求描述**:
- [具體需求描述 1]
- [具體需求描述 2]
- [具體需求描述 3]

**驗收標準**:
- [ ] [可測試的驗收標準 1]
- [ ] [可測試的驗收標準 2]
- [ ] 測試案例: [具體測試場景]

**技術實作建議** (Stage 3 參考):
- [實作建議 1]
- [實作建議 2]
```

---

## 📚 相關文檔

- [Security_Threat_Modeling_Guide.md](../../guides/system/quality/Security_Threat_Modeling_Guide.md) - 威脅建模指南
- [STRIDE_Threat_Analysis_Template.md](./STRIDE_Threat_Analysis_Template.md) - STRIDE 分析範本
- [FRD_Universal_Template.md](../core/frd/FRD_Universal_Template.md) - FRD 模板（安全需求章節）

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（基於 OWASP Top 10 與 STRIDE）
