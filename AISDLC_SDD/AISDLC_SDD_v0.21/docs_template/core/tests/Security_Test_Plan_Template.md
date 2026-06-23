# 安全測試計畫
# Security Test Plan

**專案名稱**: [專案名稱]
**文件版本**: v1.0
**建立日期**: [YYYY-MM-DD]
**負責人**: [Security Engineer / QA Lead]
**審核人**: [Security Architect / CISO]

---

## 📋 文件概述

### 目的

本文件定義專案的安全測試策略、測試範圍、測試方法、工具、執行計畫與驗收標準，確保應用程式符合安全性要求。

### 適用範圍

- **專案類型**: [Web App / Mobile App / API Service / 混合]
- **測試環境**: [Staging / Pre-Production / Production]
- **測試週期**: [Sprint X / Release Candidate / Pre-Launch]
- **法規遵循**: [GDPR / PCI-DSS / HIPAA / SOC 2 / 無]

### 參考文件

| 文件名稱 | 版本 | 連結 |
|---------|------|------|
| Security Design Document | v1.0 | `docs/srd/Security_Design_v1.0.md` |
| API Specification | v1.0 | `docs/srd/api/API_Index.md` |
| Architecture Design | v1.0 | `docs/srd/Architecture_v1.0.md` |
| Data Privacy Policy | v1.0 | `docs/compliance/Data_Privacy_Policy_v1.0.md` |

### 參考標準

- **OWASP Top 10** (2021): Web Application Security Risks
- **OWASP Mobile Top 10** (2016): Mobile Application Security Risks
- **OWASP API Security Top 10** (2023): API Security Risks
- **CWE Top 25**: Most Dangerous Software Weaknesses
- **NIST Cybersecurity Framework**

---

## 🎯 安全測試目標

### 1. 測試目標 (Security Objectives)

| 測試類型 | 目標說明 | 優先級 |
|---------|---------|-------|
| **Vulnerability Scanning** | 自動掃描已知漏洞 (CVE) | P0 (Critical) |
| **Penetration Testing** | 模擬真實攻擊場景 | P0 (Critical) |
| **Authentication Testing** | 驗證身份認證機制 | P0 (Critical) |
| **Authorization Testing** | 驗證權限控制 (RBAC/ABAC) | P0 (Critical) |
| **Input Validation Testing** | 驗證輸入過濾與驗證 | P1 (High) |
| **Session Management Testing** | 驗證 Session 安全性 | P1 (High) |
| **Cryptography Testing** | 驗證加密演算法與實作 | P1 (High) |
| **API Security Testing** | 驗證 API 端點安全性 | P1 (High) |
| **Data Privacy Testing** | 驗證個資保護機制 | P1 (High) |
| **Compliance Testing** | 驗證法規遵循 (GDPR/PCI-DSS) | P2 (Medium) |

### 2. 測試範圍 (Test Scope)

#### 2.1 包含範圍

- [x] **Web Application** (前端 + 後端)
  - 所有使用者可存取的頁面
  - 所有 API 端點 (包含內部 API)
  - 檔案上傳功能
  - 支付流程

- [x] **Mobile Application** (iOS/Android)
  - 所有使用者流程
  - 本地儲存機制
  - 網路通訊

- [x] **API Endpoints**
  - RESTful APIs
  - GraphQL APIs (如適用)
  - WebSocket 連線 (如適用)

- [x] **Third-Party Integrations**
  - OAuth/OIDC 整合
  - 支付閘道 (Stripe/PayPal)
  - 社交登入 (Google/Facebook)

- [x] **Infrastructure**
  - Cloud 配置 (AWS/GCP/Azure)
  - Container Security (Docker/Kubernetes)
  - CI/CD Pipeline

#### 2.2 排除範圍

- [ ] **Social Engineering** (社交工程攻擊)
- [ ] **Physical Security** (實體安全)
- [ ] **DDoS Attacks** (分散式阻斷服務攻擊)
- [ ] **Third-Party Services** (第三方服務的內部安全)

---

## 🛡️ 安全測試清單 (OWASP Top 10 Based)

### 1. A01:2021 - Broken Access Control

**測試目標**: 驗證權限控制機制是否正確實作

**測試項目**:
- [ ] **垂直越權 (Vertical Privilege Escalation)**
  - 測試: 一般用戶是否能存取管理員功能
  - 方法: 修改 URL、API 端點、Cookie 中的 role 參數
  - 範例: `GET /api/admin/users` (用一般用戶 Token)

- [ ] **水平越權 (Horizontal Privilege Escalation)**
  - 測試: 用戶 A 是否能存取用戶 B 的資料
  - 方法: 修改 User ID、Resource ID
  - 範例: `GET /api/users/123/profile` (用戶 A 存取用戶 B 的 profile)

- [ ] **IDOR (Insecure Direct Object References)**
  - 測試: 直接修改物件 ID 是否能存取未授權資源
  - 範例: `GET /api/orders/456` (存取他人訂單)

- [ ] **強制瀏覽 (Forced Browsing)**
  - 測試: 直接存取隱藏或受限頁面
  - 範例: `/admin`, `/debug`, `/config`

**測試工具**:
- Burp Suite Pro (Burp Intruder)
- OWASP ZAP (Forced Browse)
- Postman (手動測試 API)

**驗收標準**:
- [x] 所有權限控制測試必須通過
- [x] 無 IDOR 漏洞
- [x] 無垂直/水平越權漏洞

---

### 2. A02:2021 - Cryptographic Failures

**測試目標**: 驗證加密機制是否正確實作

**測試項目**:
- [ ] **傳輸層加密 (TLS/SSL)**
  - 測試: 所有敏感資料傳輸是否使用 HTTPS
  - 檢查: TLS 版本 ≥ 1.2, 無弱加密套件
  - 工具: `nmap --script ssl-enum-ciphers`, SSL Labs

- [ ] **敏感資料加密**
  - 測試: 密碼、信用卡號、個資是否加密儲存
  - 檢查: Database Schema, 本地儲存 (SharedPreferences/Keychain)
  - 驗證: 使用 bcrypt/Argon2 雜湊密碼

- [ ] **密鑰管理**
  - 測試: API Keys, Secrets 是否硬編碼在程式碼中
  - 檢查: Source Code Review, Git History
  - 工具: `truffleHog`, `gitleaks`

- [ ] **隨機數產生器**
  - 測試: Session Token, CSRF Token 是否使用安全的隨機數產生器
  - 檢查: 程式碼中是否使用 `crypto.randomBytes()` (Node.js) 或 `SecureRandom` (Java)

**測試工具**:
- SSL Labs (https://www.ssllabs.com/ssltest/)
- testssl.sh
- truffleHog (Secrets Scanner)
- gitleaks (Git Secrets Scanner)

**驗收標準**:
- [x] SSL Labs 評分 A 或 A+
- [x] 無密鑰硬編碼
- [x] 所有敏感資料加密儲存

---

### 3. A03:2021 - Injection

**測試目標**: 驗證應用程式是否能防禦注入攻擊

**測試項目**:
- [ ] **SQL Injection**
  - 測試: 輸入 SQL Payload 是否能執行任意 SQL
  - Payload 範例: `' OR '1'='1`, `'; DROP TABLE users; --`
  - 測試端點: 登入表單、搜尋功能、過濾器

- [ ] **NoSQL Injection** (MongoDB/DynamoDB)
  - Payload 範例: `{"$ne": null}`, `{"$gt": ""}`
  - 測試: 登入繞過、資料洩漏

- [ ] **Command Injection**
  - 測試: 輸入 OS Command 是否能執行
  - Payload 範例: `; ls -la`, `| cat /etc/passwd`
  - 高風險功能: 檔案處理、系統呼叫

- [ ] **LDAP Injection / XPath Injection**
  - 測試: LDAP 查詢、XML 解析功能

**測試工具**:
- sqlmap (自動化 SQL Injection 測試)
- Burp Suite (Intruder + Payloads)
- OWASP ZAP (Active Scan)

**驗收標準**:
- [x] 無 SQL Injection 漏洞
- [x] 所有輸入經過 Prepared Statements / Parameterized Queries
- [x] 無 Command Injection 漏洞

---

### 4. A04:2021 - Insecure Design

**測試目標**: 驗證系統設計是否考慮安全性

**測試項目**:
- [ ] **業務邏輯漏洞 (Business Logic Flaws)**
  - 測試: 負數金額轉帳、重複提交訂單、越過工作流程
  - 範例: 提交 `amount: -100` 進行轉帳

- [ ] **Rate Limiting 缺失**
  - 測試: 無限制呼叫 API 是否被阻擋
  - 測試: 暴力破解密碼、OTP、API Abuse

- [ ] **缺少 CAPTCHA**
  - 測試: 註冊、登入、忘記密碼功能是否有 CAPTCHA

- [ ] **不當的錯誤訊息**
  - 測試: 錯誤訊息是否洩漏敏感資訊
  - 範例: "User not found" vs "Invalid credentials"

**測試工具**:
- Burp Suite (Repeater)
- Custom Scripts (Python + Requests)

**驗收標準**:
- [x] 所有業務邏輯測試通過
- [x] Rate Limiting 已實作
- [x] 關鍵功能有 CAPTCHA

---

### 5. A05:2021 - Security Misconfiguration

**測試目標**: 驗證系統配置是否安全

**測試項目**:
- [ ] **預設帳號/密碼**
  - 測試: `admin/admin`, `root/root`, `test/test`

- [ ] **Debug Mode 開啟**
  - 測試: Stack Trace 是否洩漏
  - 檢查: `/debug`, `X-Powered-By` Header

- [ ] **不必要的 HTTP Methods**
  - 測試: `OPTIONS`, `TRACE`, `PUT`, `DELETE` 是否被禁用

- [ ] **Security Headers 缺失**
  - 檢查:
    - `Content-Security-Policy` (CSP)
    - `X-Frame-Options` (Clickjacking 防護)
    - `X-Content-Type-Options: nosniff`
    - `Strict-Transport-Security` (HSTS)
    - `X-XSS-Protection`

- [ ] **Directory Listing 開啟**
  - 測試: `/uploads/`, `/images/`, `/assets/`

- [ ] **敏感檔案暴露**
  - 測試: `.git/`, `.env`, `config.yml`, `package.json`

**測試工具**:
- Nikto (Web Server Scanner)
- dirb / gobuster (Directory Brute Force)
- Security Headers (https://securityheaders.com/)

**驗收標準**:
- [x] Security Headers 評分 A
- [x] 無預設帳號
- [x] 無敏感檔案暴露

---

### 6. A06:2021 - Vulnerable and Outdated Components

**測試目標**: 驗證使用的元件是否有已知漏洞

**測試項目**:
- [ ] **依賴套件漏洞掃描**
  - 掃描: `package.json`, `pom.xml`, `requirements.txt`
  - 工具: `npm audit`, `snyk`, `OWASP Dependency-Check`

- [ ] **Container Image 漏洞掃描**
  - 掃描: Docker Base Image
  - 工具: `trivy`, `clair`, `anchore`

- [ ] **作業系統漏洞**
  - 掃描: EC2, VM, Server
  - 工具: `OpenVAS`, `Nessus`

**測試工具**:
- npm audit / yarn audit
- Snyk (https://snyk.io/)
- OWASP Dependency-Check
- Trivy (Container Scanner)

**驗收標準**:
- [x] 無 High/Critical 漏洞
- [x] 所有依賴套件更新至安全版本

---

### 7. A07:2021 - Identification and Authentication Failures

**測試目標**: 驗證身份認證機制

**測試項目**:
- [ ] **弱密碼政策**
  - 測試: 是否能設定 `123456`, `password`
  - 要求: 最少 8 字元、大小寫、數字、特殊字元

- [ ] **暴力破解防護**
  - 測試: 連續錯誤登入是否被鎖定
  - 要求: 5 次失敗後鎖定 15 分鐘

- [ ] **Session 管理**
  - 測試: Session Timeout (30 分鐘無活動)
  - 測試: 登出後 Session 是否失效
  - 測試: Session Fixation Attack

- [ ] **JWT 安全性** (如適用)
  - 測試: JWT 是否使用強簽章 (HS256/RS256)
  - 測試: JWT 是否有 `exp` (過期時間)
  - 測試: JWT None Algorithm Attack

- [ ] **Multi-Factor Authentication (MFA)**
  - 測試: OTP 是否可重複使用
  - 測試: OTP 過期時間 (5 分鐘)

**測試工具**:
- Burp Suite (Intruder - Brute Force)
- jwt.io (JWT Decoder)
- Custom Scripts

**驗收標準**:
- [x] 強密碼政策已實作
- [x] 暴力破解防護已實作
- [x] Session 管理安全

---

### 8. A08:2021 - Software and Data Integrity Failures

**測試目標**: 驗證軟體供應鏈與資料完整性

**測試項目**:
- [ ] **未驗證的 Deserialization**
  - 測試: 反序列化是否驗證資料來源
  - 高風險: Java Serialization, Python Pickle

- [ ] **CI/CD Pipeline 安全性**
  - 檢查: GitHub Actions, GitLab CI 的 Secret 管理
  - 檢查: Docker Build 是否使用官方 Base Image

- [ ] **檔案上傳驗證**
  - 測試: 上傳 `.php`, `.jsp`, `.exe` 是否被阻擋
  - 測試: 檔案類型驗證 (MIME Type + Magic Bytes)

**測試工具**:
- ysoserial (Java Deserialization)
- Custom Scripts

**驗收標準**:
- [x] 無反序列化漏洞
- [x] 檔案上傳驗證完整

---

### 9. A09:2021 - Security Logging and Monitoring Failures

**測試目標**: 驗證日誌記錄與監控機制

**測試項目**:
- [ ] **關鍵事件日誌**
  - 檢查: 登入失敗、權限變更、敏感操作是否記錄
  - 日誌必須包含: Timestamp, User ID, IP Address, Action

- [ ] **日誌保護**
  - 測試: 日誌是否防竄改 (Write-Once Storage)
  - 測試: 敏感資料 (密碼、信用卡號) 是否被記錄

- [ ] **即時告警**
  - 測試: 異常行為 (大量失敗登入) 是否觸發告警

**測試工具**:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- DataDog

**驗收標準**:
- [x] 關鍵事件日誌完整
- [x] 日誌不含敏感資料
- [x] 即時告警已配置

---

### 10. A10:2021 - Server-Side Request Forgery (SSRF)

**測試目標**: 驗證 SSRF 防護

**測試項目**:
- [ ] **SSRF Attack**
  - 測試: 輸入內部 IP 是否能存取內部服務
  - Payload 範例: `http://localhost:8080/admin`, `http://169.254.169.254/latest/meta-data/` (AWS Metadata)

- [ ] **URL Validation**
  - 測試: URL Whitelist 是否正確實作

**測試工具**:
- Burp Suite (Collaborator)
- Custom Scripts

**驗收標準**:
- [x] 無 SSRF 漏洞
- [x] URL Whitelist 已實作

---

## 📱 Mobile Application Specific Tests

### 1. 本地儲存安全性

- [ ] **Insecure Data Storage**
  - 檢查: SharedPreferences (Android), UserDefaults (iOS) 是否儲存敏感資料
  - 要求: 使用 EncryptedSharedPreferences / Keychain

- [ ] **Root Detection / Jailbreak Detection**
  - 測試: App 在 Root/JB 裝置上是否能正常運作

### 2. 網路通訊安全性

- [ ] **Certificate Pinning**
  - 測試: 是否實作 SSL Pinning
  - 工具: Burp Suite + Proxy

- [ ] **Insecure Communication**
  - 測試: 是否使用 HTTP (非 HTTPS)

---

## 🛠️ 測試工具清單

| 工具 | 類型 | 用途 | 授權 |
|-----|------|-----|------|
| **Burp Suite Pro** | Dynamic Testing | DAST, Penetration Testing | Commercial |
| **OWASP ZAP** | Dynamic Testing | DAST, Automated Scan | Open Source |
| **Nmap** | Network Scanner | Port Scanning, Service Detection | Open Source |
| **sqlmap** | Injection Testing | Automated SQL Injection | Open Source |
| **Nikto** | Web Scanner | Web Server Vulnerability Scan | Open Source |
| **Snyk** | SCA | Dependency Vulnerability Scan | Freemium |
| **Trivy** | Container Scanner | Docker Image Scan | Open Source |
| **MobSF** | Mobile Testing | Mobile App Security Testing | Open Source |

---

## 📅 測試執行計畫

### 測試時程表

| 階段 | 測試項目 | 執行日期 | 負責人 | 狀態 |
|-----|---------|---------|-------|------|
| **Phase 1** | 自動化掃描 (OWASP ZAP, Snyk) | Week 1 Day 1-2 | QA | ☐ Pending |
| **Phase 2** | 手動滲透測試 (OWASP Top 10) | Week 1 Day 3-5 | Security Engineer | ☐ Pending |
| **Phase 3** | API Security Testing | Week 2 Day 1-2 | QA + Security Engineer | ☐ Pending |
| **Phase 4** | Mobile Security Testing | Week 2 Day 3-4 | Mobile QA | ☐ Pending |
| **Phase 5** | 漏洞修復驗證 | Week 3 Day 1-2 | Security Engineer | ☐ Pending |
| **Phase 6** | 最終報告撰寫 | Week 3 Day 3 | Security Lead | ☐ Pending |

---

## ✅ 驗收標準

### 整體驗收標準

- [ ] **所有 P0/P1 測試項目必須通過**
- [ ] **無 High/Critical 漏洞**
- [ ] **所有 Medium 漏洞已記錄並納入修復計畫**
- [ ] **安全測試報告已撰寫並經 Security Lead 審核**

### 漏洞嚴重程度定義

| 嚴重程度 | 定義 | 修復時限 |
|---------|------|---------|
| **Critical** | 可直接導致資料洩漏/系統破壞 | 立即修復 (1 day) |
| **High** | 可能導致資料洩漏或權限提升 | 3 days |
| **Medium** | 可能導致資訊洩漏或 DoS | 1 week |
| **Low** | 影響有限,需要特定條件觸發 | 下一個 Sprint |

---

## 📞 聯絡資訊

| 角色 | 姓名 | Email | 職責 |
|-----|------|-------|------|
| **Security Lead** | [姓名] | [email] | 測試計畫審核、漏洞評估 |
| **Security Engineer** | [姓名] | [email] | 滲透測試執行 |
| **QA Lead** | [姓名] | [email] | 自動化掃描、測試協調 |
| **Tech Lead** | [姓名] | [email] | 漏洞修復、技術支援 |

---

**文件版本歷史**:

| 版本 | 日期 | 變更內容 | 作者 |
|-----|------|---------|------|
| v1.0 | [YYYY-MM-DD] | 初始版本 | [作者] |

---

**審核記錄**:

| 審核者 | 日期 | 審核結果 | 意見 |
|-------|------|---------|------|
| [Security Lead] | [日期] | ☐ 通過 ☐ 需修改 | [意見] |
| [CISO] | [日期] | ☐ 通過 ☐ 需修改 | [意見] |
