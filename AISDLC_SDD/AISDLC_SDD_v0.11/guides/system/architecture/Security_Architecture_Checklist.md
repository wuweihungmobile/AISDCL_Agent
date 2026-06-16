# 安全架構設計檢查清單
# Security Architecture Checklist

**版本**: v0.01
**建立日期**: 2025-12-13
**文檔類型**: 系統參考文件 - 安全架構
**適用階段**: Greenfield SOP Stage 3（系統架構設計）
**目標使用者**: SD (System Designer), Security Engineer, SA

---

## 🎯 文檔目的

本檢查清單協助 **SD-Architect Agent** 在 **Stage 3（系統架構設計）** 執行 **C4 Model Level 2/3** 設計時，確保安全元件完整納入架構設計，避免「事後補安全」的技術債。

**核心原則**: **Security by Design（設計階段內建安全）**

---

## 📋 使用時機

### 何時使用此檢查清單？

**必須使用**:
- ✅ Greenfield SOP Stage 3.3（C4 Level 2 Container Diagram）
- ✅ Greenfield SOP Stage 3.4（C4 Level 3 Component Diagram）
- ✅ SRD「安全架構設計」章節撰寫

**建議使用**:
- 🟡 架構審查會議前（Architecture Review）
- 🟡 技術選型評估時（Technology Selection）
- 🟡 重構專案安全升級時（Refactoring Security）

---

## 🏗️ 安全元件強制清單（4 大類別）

根據 STRIDE 威脅建模（Stage 2 產出），以下 4 類安全元件 **必須** 在 C4 Model Level 2/3 中明確設計：

---

### 1️⃣ 認證與授權元件（Authentication & Authorization）

**對應 STRIDE**: Spoofing (S)、Elevation of Privilege (E)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Authentication Service (認證服務)**
  - **技術選型已定義**:
    - [ ] JWT (JSON Web Token)
    - [ ] OAuth 2.0 / OpenID Connect
    - [ ] SAML 2.0
    - [ ] Session-based (Cookie)
  - **Token 管理機制**:
    - [ ] Access Token 儲存位置（Memory / LocalStorage / Cookie）
    - [ ] Refresh Token 儲存位置（HttpOnly Cookie / Secure Storage）
    - [ ] Token 刷新機制（Refresh Token Rotation）
  - **容器部署**:
    - [ ] 獨立 Auth Service 或整合於 API Gateway

- [ ] **Authorization Engine (授權引擎)**
  - **授權模型已選擇**:
    - [ ] RBAC (Role-Based Access Control)
    - [ ] ABAC (Attribute-Based Access Control)
    - [ ] PBAC (Policy-Based Access Control)
  - **權限驗證流程**:
    - [ ] API Gateway 統一驗證
    - [ ] 各 Microservice 自行驗證
  - **權限資料儲存**:
    - [ ] Database (Users, Roles, Permissions 資料表)
    - [ ] Cache (Redis) 加速權限查詢

#### C4 Level 3 Component Diagram 檢查清單

- [ ] **JWT Handler Component**
  - **功能**: Token 生成、驗證、解析
  - **演算法**: RS256 (非對稱) 或 HS256 (對稱)
  - **Key 管理**: 金鑰儲存在環境變數或 KMS

- [ ] **Permission Checker Component**
  - **功能**: 檢查使用者是否有權限執行操作
  - **快取策略**: 權限快取 TTL = 5 分鐘

- [ ] **MFA Component (多因素認證)**
  - **適用場景**: 高敏感操作（如付款、刪除資料）
  - **實作方式**: TOTP (Google Authenticator) / SMS OTP

---

### 2️⃣ 加密元件（Encryption Components）

**對應 STRIDE**: Information Disclosure (I)、Tampering (T)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **TLS/SSL Termination (HTTPS 終止)**
  - **位置**: Load Balancer / API Gateway
  - **TLS 版本**: TLS 1.2+ (禁止 TLS 1.0/1.1)
  - **憑證管理**: Let's Encrypt / AWS ACM / 企業 CA

- [ ] **Encryption Service (加密服務)**
  - **用途**: 敏感欄位加密（密碼、信用卡、身分證）
  - **技術選型**:
    - [ ] Database 層加密（Transparent Data Encryption）
    - [ ] Application 層加密（AES-256-GCM）
  - **Key Management**:
    - [ ] KMS (AWS KMS / Azure Key Vault / GCP KMS)
    - [ ] HashiCorp Vault

#### C4 Level 3 Component Diagram 檢查清單

- [ ] **Password Hash Component**
  - **演算法**: bcrypt (cost factor ≥ 12) 或 Argon2
  - **Salt**: 每個密碼獨立 Salt

- [ ] **Data Encryption Component**
  - **加密範圍**:
    - [ ] PII (個人資料)
    - [ ] Payment Info (金流資料)
    - [ ] Sensitive Business Data
  - **加密金鑰輪換**: 每 90 天輪換一次

- [ ] **HTTPS Redirect Component**
  - **功能**: 強制所有 HTTP 請求重導向至 HTTPS
  - **HSTS Header**: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

---

### 3️⃣ 輸入驗證與防護元件（Input Validation & Protection）

**對應 STRIDE**: Tampering (T)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **API Gateway / WAF (Web Application Firewall)**
  - **功能**:
    - [ ] Rate Limiting（防 DDoS）
    - [ ] IP Whitelist/Blacklist
    - [ ] SQL Injection 防護
    - [ ] XSS 防護
  - **技術選型**:
    - [ ] AWS WAF / Cloudflare WAF
    - [ ] Kong Gateway / NGINX
    - [ ] Custom Middleware

- [ ] **Input Validation Service**
  - **驗證層次**:
    - [ ] 前端驗證（User Experience）
    - [ ] 後端驗證（Security）
  - **Schema Validation**:
    - [ ] JSON Schema Validator
    - [ ] Joi / Yup / Zod

#### C4 Level 3 Component Diagram 檢查清單

- [ ] **Request Validator Component**
  - **驗證項目**:
    - [ ] 資料類型（String, Number, Boolean）
    - [ ] 資料長度（min/max length）
    - [ ] 資料格式（Email, URL, Phone）
    - [ ] 允許值範圍（Enum）

- [ ] **SQL Injection Prevention Component**
  - **實作方式**:
    - [ ] ORM Prepared Statements（Sequelize, TypeORM, Prisma）
    - [ ] 禁止字串拼接 SQL
    - [ ] 輸入特殊字元轉義

- [ ] **XSS Prevention Component**
  - **實作方式**:
    - [ ] HTML 編碼輸出（Escape HTML）
    - [ ] Content-Security-Policy (CSP) Header
    - [ ] 禁止 `eval()` 和 `innerHTML`

- [ ] **CSRF Prevention Component**
  - **實作方式**:
    - [ ] CSRF Token（同步 Token 模式）
    - [ ] SameSite Cookie 屬性
    - [ ] Double Submit Cookie

---

### 4️⃣ 日誌與審計元件（Logging & Auditing）

**對應 STRIDE**: Repudiation (R)

#### C4 Level 2 Container Diagram 檢查清單

- [ ] **Centralized Logging Service (集中化日誌服務)**
  - **技術選型**:
    - [ ] ELK Stack (Elasticsearch, Logstash, Kibana)
    - [ ] CloudWatch Logs (AWS)
    - [ ] Datadog / Splunk
  - **日誌來源**:
    - [ ] Application Logs
    - [ ] API Gateway Logs
    - [ ] Database Audit Logs
    - [ ] Security Event Logs

- [ ] **Audit Trail Database (審計追蹤資料庫)**
  - **儲存內容**:
    - [ ] 使用者操作記錄
    - [ ] 資料變更歷史（CRUD）
    - [ ] 認證事件（登入/登出/失敗）
  - **保留期限**: ≥ 90 天

#### C4 Level 3 Component Diagram 檢查清單

- [ ] **Security Event Logger Component**
  - **記錄事件**:
    - [ ] 登入成功/失敗（包含 IP、UserAgent）
    - [ ] 密碼修改
    - [ ] 權限變更
    - [ ] 敏感操作（刪除、匯出資料）

- [ ] **Audit Trail Component**
  - **記錄格式**:
    ```json
    {
      "timestamp": "2025-12-13T10:30:00Z",
      "user_id": "U-12345",
      "action": "UPDATE",
      "resource": "orders/ORD-001",
      "ip_address": "192.168.1.100",
      "result": "success"
    }
    ```

- [ ] **Data Masking Component**
  - **功能**: 日誌中敏感資料遮罩
  - **遮罩欄位**:
    - [ ] 密碼（完全遮罩）
    - [ ] 信用卡號（顯示後 4 碼: `****-****-****-1234`）
    - [ ] Email（部分遮罩: `u***@example.com`）

- [ ] **Anomaly Detection Component (異常偵測)**
  - **偵測項目**:
    - [ ] 連續登入失敗 ≥ 5 次
    - [ ] 異地登入（IP 位置異常變化）
    - [ ] 異常 API 呼叫頻率（暴力破解）

---

## 🔍 C4 Level 2/3 安全元件整合範例

### 範例：BnB 訂房系統 C4 Level 2 (含安全元件)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BnB Platform - Container Diagram             │
└─────────────────────────────────────────────────────────────────┘

👤 使用者 (Web/Mobile)
   │
   │ HTTPS
   ↓
┌──────────────────────┐
│  API Gateway         │ ←─ 1️⃣ 認證：JWT 驗證
│  [Kong/NGINX]        │ ←─ 3️⃣ 輸入驗證：Rate Limiting
└──────────────────────┘
   │
   ├──→ ┌────────────────────┐
   │    │  Auth Service      │ ←─ 1️⃣ 認證：OAuth 2.0 / JWT
   │    │  [Node.js]         │ ←─ 2️⃣ 加密：Password Hash (bcrypt)
   │    └────────────────────┘
   │
   ├──→ ┌────────────────────┐
   │    │  Booking Service   │ ←─ 1️⃣ 授權：Permission Check
   │    │  [Node.js]         │ ←─ 3️⃣ 輸入驗證：Schema Validation
   │    └────────────────────┘ ←─ 4️⃣ 日誌：Audit Trail
   │
   └──→ ┌────────────────────┐
        │  Payment Service   │ ←─ 2️⃣ 加密：PCI-DSS 合規加密
        │  [Node.js]         │ ←─ 4️⃣ 日誌：Security Event Log
        └────────────────────┘
           │
           ↓
        🗄️ PostgreSQL
           (Encrypted at rest) ←─ 2️⃣ 加密：Database TDE

        ┌────────────────────┐
        │  Logging Service   │ ←─ 4️⃣ 日誌：ELK Stack
        │  [Elasticsearch]   │
        └────────────────────┘
```

---

## ✅ Stage 3 安全架構設計完整檢查清單

### 階段 1: C4 Level 2 Container Diagram 安全檢查

- [ ] **認證容器已定義**
  - [ ] Authentication Service 已標示技術棧
  - [ ] Token 管理機制已說明

- [ ] **加密容器已定義**
  - [ ] TLS/SSL Termination 位置已標示
  - [ ] KMS/Vault 整合已規劃

- [ ] **輸入防護容器已定義**
  - [ ] API Gateway / WAF 已標示
  - [ ] Rate Limiting 機制已說明

- [ ] **日誌容器已定義**
  - [ ] Centralized Logging Service 已標示
  - [ ] Audit Trail Database 已規劃

### 階段 2: C4 Level 3 Component Diagram 安全檢查

- [ ] **認證元件已設計**
  - [ ] JWT Handler Component
  - [ ] Permission Checker Component
  - [ ] MFA Component (若適用)

- [ ] **加密元件已設計**
  - [ ] Password Hash Component
  - [ ] Data Encryption Component
  - [ ] HTTPS Redirect Component

- [ ] **輸入驗證元件已設計**
  - [ ] Request Validator Component
  - [ ] SQL Injection Prevention Component
  - [ ] XSS Prevention Component
  - [ ] CSRF Prevention Component

- [ ] **日誌元件已設計**
  - [ ] Security Event Logger Component
  - [ ] Audit Trail Component
  - [ ] Data Masking Component
  - [ ] Anomaly Detection Component

### 階段 3: SRD 文檔整合檢查

- [ ] **SRD「安全架構設計」章節已撰寫**
  - [ ] 引用 Stage 2 STRIDE 分析報告
  - [ ] 對應 NFR-SEC-xxx 安全需求
  - [ ] 每個安全元件有詳細技術規格

- [ ] **安全元件技術選型已說明**
  - [ ] 為什麼選擇 JWT 而非 Session？
  - [ ] 為什麼選擇 bcrypt 而非 SHA-256？
  - [ ] 為什麼使用 AWS KMS？

- [ ] **安全元件部署架構已定義**
  - [ ] 獨立部署或整合部署？
  - [ ] 高可用性設計（HA）
  - [ ] 災難復原計畫（DR）

### 階段 4: 架構審查會議檢查

- [ ] **SD 審查**: 安全元件設計完整性
- [ ] **Security Engineer 審查**: 安全措施有效性
- [ ] **SA 審查**: 需求追蹤完整性（NFR-SEC → 安全元件）
- [ ] **PM 確認**: 成本與時程可行性

---

## 📊 預期效益

### 執行安全元件設計後：

| 指標 | 改進前 | 改進後 | 提升幅度 |
|------|--------|--------|---------|
| **架構審查安全性完整度** | 40% | 90% | ↑ 50% |
| **安全元件遺漏率** | 60% | 10% | ↓ 50% |
| **事後安全補丁成本** | 8 人日 | 2 人日 | ↓ 75% |
| **安全審查通過率** | 45% | 95% | ↑ 50% |

**ROI 評估**:
- **投入成本**: 3 人日（SD 2 人日 + Security Engineer 1 人日）
- **預期效益**: 節省事後安全補丁成本 6 人日 = $12k
- **ROI**: 4:1

---

## 📚 相關文檔

- [Security_Threat_Modeling_Guide.md](../quality/Security_Threat_Modeling_Guide.md) - Stage 2 威脅建模（產出 NFR-SEC）
- [C4_Model_Guidelines.md](./C4_Model_Guidelines.md) - C4 Model 完整指南
- [Security_Design_Checklist.md](../quality/Security_Design_Checklist.md) - 安全設計詳細檢查清單
- [SRD_Universal_Template.md](../../../docs_template/core/srd/SRD_Universal_Template.md) - SRD 模板（安全架構章節）

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（P1-6 改進項目）
