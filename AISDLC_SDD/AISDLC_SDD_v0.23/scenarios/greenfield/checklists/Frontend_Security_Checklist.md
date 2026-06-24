# 前端安全檢查清單
# Frontend Security Checklist

**版本**: v1.0
**建立日期**: 2025-11-25
**最後更新**: 2025-11-25
**適用情境**: Greenfield - Web App / Mobile App / Hybrid App
**使用階段**: SOP 階段 5 (架構設計) 與階段 8 (測試執行)
**對應 SOP**: [Greenfield SOP.md](../SOP.md) - 階段 5 步驟 5.3、階段 8 步驟 8.2

---

## 📋 文檔目的

本檢查清單提供**前端應用程式的安全檢查標準**，涵蓋 Web App 和 Mobile App 的常見安全威脅與防護措施，基於 **OWASP Top 10** 和 **OWASP Mobile Top 10** 標準。

### 使用時機

**階段 5 (架構設計階段)**:
- 設計階段安全審查
- 架構安全評估
- 安全控制機制設計

**階段 8 (測試執行階段)**:
- 安全測試執行
- 漏洞掃描驗證
- 上線前安全檢查

### 使用者

- **SD-Architect Agent (Marcus)**: 架構設計時使用
- **Dev Agent (David)**: 實作時參考
- **QA Agent (Quincy)**: 安全測試時驗證
- **Security-Engineer Agent**: 專業安全審查

---

## ✅ 檢查清單總覽

本檢查清單分為 **5 大類別**，共 **50+ 檢查項目**：

| 類別 | 檢查項目數 | 適用平台 |
|------|----------|---------|
| **1. XSS 防護** | 15 項 | Web App, Hybrid App |
| **2. CSRF 防護** | 10 項 | Web App |
| **3. 敏感資料處理** | 12 項 | Web App, Mobile App |
| **4. 安全 Headers** | 8 項 | Web App |
| **5. 第三方套件與 HTTPS** | 10 項 | Web App, Mobile App |

---

## 1️⃣ XSS (Cross-Site Scripting) 防護

### 1.1 輸入驗證

- [ ] **1.1.1 所有使用者輸入都經過驗證**
  - ✅ 實作：前端使用表單驗證庫（如 Yup, Joi, Zod）
  - ✅ 檢查：Email、URL、電話號碼等格式驗證
  - ❌ 錯誤示範：直接接受使用者輸入而不驗證

- [ ] **1.1.2 限制輸入長度和格式**
  - ✅ 實作：設定 `maxLength` 屬性，防止過長輸入
  - ✅ 檢查：使用正規表達式 (Regex) 限制允許字元
  - 📋 範例：
    ```jsx
    <input type="text" maxLength="100" pattern="[A-Za-z0-9]+" />
    ```

- [ ] **1.1.3 使用白名單而非黑名單過濾**
  - ✅ 實作：定義允許的字元集合，拒絕其他輸入
  - ❌ 錯誤示範：嘗試過濾所有惡意字元（如 `<script>`）

### 1.2 輸出編碼

- [ ] **1.2.1 所有動態內容都經過 HTML 編碼**
  - ✅ 實作：React 預設自動編碼（使用 `{}` 插值）
  - ✅ 實作：Vue 使用 `{{ }}` 插值（預設編碼）
  - ❌ 錯誤示範：使用 `dangerouslySetInnerHTML` 或 `v-html` 而未消毒

- [ ] **1.2.2 避免使用 `dangerouslySetInnerHTML` 或 `v-html`**
  - ✅ 檢查：若必須使用，先通過 DOMPurify 消毒
  - 📋 範例（React）：
    ```jsx
    import DOMPurify from 'dompurify';

    function MyComponent({ userContent }) {
      const sanitized = DOMPurify.sanitize(userContent);
      return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
    }
    ```

- [ ] **1.2.3 URL 參數經過編碼**
  - ✅ 實作：使用 `encodeURIComponent()` 編碼 URL 參數
  - 📋 範例：
    ```javascript
    const url = `/search?q=${encodeURIComponent(userQuery)}`;
    ```

### 1.3 Content Security Policy (CSP)

- [ ] **1.3.1 設定嚴格的 CSP Header**
  - ✅ 實作：在 HTTP Response Header 設定 CSP
  - 📋 建議設定：
    ```
    Content-Security-Policy:
      default-src 'self';
      script-src 'self' https://trusted-cdn.com;
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: https:;
      connect-src 'self' https://api.example.com;
    ```

- [ ] **1.3.2 禁止 inline scripts 和 inline styles**
  - ✅ 實作：CSP 不使用 `'unsafe-inline'`（script-src）
  - ✅ 實作：將所有 JavaScript 和 CSS 移到外部檔案
  - ❌ 錯誤示範：`<script>alert('XSS')</script>`

- [ ] **1.3.3 使用 nonce 或 hash 允許特定 inline scripts**
  - ✅ 實作：為必要的 inline script 生成 nonce
  - 📋 範例：
    ```html
    <!-- Server 端生成 nonce -->
    <script nonce="random-nonce-123">
      console.log('Safe inline script');
    </script>
    ```

### 1.4 DOM 操作安全

- [ ] **1.4.1 避免使用 `eval()`, `setTimeout(string)`, `setInterval(string)`**
  - ❌ 禁止：`eval(userInput)`
  - ✅ 替代：使用函數引用 `setTimeout(myFunction, 1000)`

- [ ] **1.4.2 避免直接操作 `innerHTML`**
  - ❌ 禁止：`element.innerHTML = userInput`
  - ✅ 替代：使用 `textContent` 或 DOM API (`createElement`, `appendChild`)

- [ ] **1.4.3 避免 `document.write()`**
  - ❌ 禁止：`document.write(userInput)`
  - ✅ 替代：使用現代 DOM API

### 1.5 框架特定防護

- [ ] **1.5.1 React: 避免 `dangerouslySetInnerHTML`**
  - ✅ 檢查：若必須使用，先通過 DOMPurify
  - ✅ 檢查：使用 ESLint 規則 `react/no-danger`

- [ ] **1.5.2 Vue: 避免 `v-html`**
  - ✅ 檢查：若必須使用，先通過 DOMPurify
  - ✅ 檢查：使用 ESLint 規則 `vue/no-v-html`

- [ ] **1.5.3 Angular: 使用 DomSanitizer**
  - ✅ 實作：注入 `DomSanitizer` 並使用 `sanitize()` 方法

---

## 2️⃣ CSRF (Cross-Site Request Forgery) 防護

### 2.1 CSRF Token

- [ ] **2.1.1 所有狀態變更請求 (POST/PUT/DELETE) 使用 CSRF Token**
  - ✅ 實作：後端生成 CSRF Token，前端在 Header 或 Body 送出
  - 📋 範例（React + Axios）：
    ```javascript
    axios.post('/api/transfer', data, {
      headers: { 'X-CSRF-Token': csrfToken }
    });
    ```

- [ ] **2.1.2 CSRF Token 儲存在 Cookie（HttpOnly, SameSite=Strict）**
  - ✅ 實作：後端設定 Cookie 屬性
  - 📋 範例：
    ```
    Set-Cookie: csrf-token=abc123; HttpOnly; SameSite=Strict; Secure
    ```

- [ ] **2.1.3 CSRF Token 在每次請求驗證**
  - ✅ 實作：後端 Middleware 驗證 Token 有效性
  - ❌ 錯誤示範：僅在登入時驗證 Token

### 2.2 SameSite Cookie 屬性

- [ ] **2.2.1 Session Cookie 設定 `SameSite=Lax` 或 `SameSite=Strict`**
  - ✅ 實作：`SameSite=Strict` 最嚴格（僅同站請求）
  - ✅ 實作：`SameSite=Lax` 允許 GET 導航（適合一般網站）
  - 📋 範例：
    ```
    Set-Cookie: session=xyz; SameSite=Lax; Secure; HttpOnly
    ```

- [ ] **2.2.2 重要操作 Cookie 使用 `SameSite=Strict`**
  - ✅ 適用：金融交易、密碼變更、刪除帳號

### 2.3 Double Submit Cookie

- [ ] **2.3.1 實作 Double Submit Cookie 模式（無狀態 CSRF 防護）**
  - ✅ 實作：CSRF Token 同時在 Cookie 和 Request Header 送出
  - ✅ 實作：後端驗證兩者是否一致
  - 📋 範例：
    ```javascript
    // 前端
    axios.post('/api/action', data, {
      headers: { 'X-CSRF-Token': getCookieValue('csrf-token') }
    });

    // 後端
    if (request.headers['x-csrf-token'] !== request.cookies['csrf-token']) {
      return 403; // Forbidden
    }
    ```

### 2.4 其他防護

- [ ] **2.4.1 重要操作需要重新驗證（如輸入密碼）**
  - ✅ 實作：金融交易、密碼變更、刪除帳號需二次驗證

- [ ] **2.4.2 使用自訂 Header（如 `X-Requested-With`）**
  - ✅ 實作：AJAX 請求加入自訂 Header
  - ✅ 原理：跨站請求無法設定自訂 Header

- [ ] **2.4.3 檢查 `Referer` 或 `Origin` Header**
  - ✅ 實作：後端驗證請求來源
  - ⚠️ 注意：部分使用者或代理可能移除 Referer

---

## 3️⃣ 敏感資料處理

### 3.1 資料儲存

- [ ] **3.1.1 避免在 LocalStorage 儲存敏感資料**
  - ❌ 禁止：`localStorage.setItem('token', sensitiveToken)`
  - ✅ 替代：使用 HttpOnly Cookie（後端設定）

- [ ] **3.1.2 避免在 SessionStorage 儲存敏感資料**
  - ❌ 禁止：信用卡號、密碼、個資
  - ✅ 允許：臨時 UI 狀態（如表單草稿）

- [ ] **3.1.3 Mobile App: 使用加密儲存（Keychain / Keystore）**
  - ✅ iOS：使用 Keychain Services
  - ✅ Android：使用 Android Keystore System
  - 📋 React Native 範例：
    ```javascript
    import * as Keychain from 'react-native-keychain';

    await Keychain.setGenericPassword('username', 'password');
    ```

### 3.2 資料傳輸

- [ ] **3.2.1 所有敏感資料透過 HTTPS 傳輸**
  - ✅ 實作：強制使用 HTTPS（HTTP 自動導向 HTTPS）
  - ✅ 實作：設定 HSTS Header

- [ ] **3.2.2 避免在 URL 參數傳遞敏感資料**
  - ❌ 禁止：`/user?token=abc123&ssn=123-45-6789`
  - ✅ 替代：使用 POST Body 或 HTTP Header

- [ ] **3.2.3 移除 Console.log() 中的敏感資料**
  - ✅ 實作：Production 環境禁用 `console.log()`
  - 📋 Webpack 設定：
    ```javascript
    // webpack.config.js
    new webpack.DefinePlugin({
      'console.log': JSON.stringify(function() {})
    })
    ```

### 3.3 密碼處理

- [ ] **3.3.1 密碼輸入欄位使用 `type="password"`**
  - ✅ 實作：`<input type="password" autocomplete="current-password" />`

- [ ] **3.3.2 密碼不儲存在前端（包括記憶體）**
  - ✅ 實作：送出後立即清除密碼變數

- [ ] **3.3.3 實作密碼強度檢查**
  - ✅ 實作：最少 8 字元、包含大小寫字母、數字、特殊字元
  - 📋 範例（React）：
    ```jsx
    import PasswordStrengthBar from 'react-password-strength-bar';

    <PasswordStrengthBar password={password} />
    ```

### 3.4 敏感資料顯示

- [ ] **3.4.1 敏感資料部分遮罩顯示**
  - ✅ 實作：信用卡號顯示為 `**** **** **** 1234`
  - ✅ 實作：Email 顯示為 `t***@example.com`

- [ ] **3.4.2 避免在 DevTools 暴露敏感資料**
  - ✅ 檢查：Redux DevTools 在 Production 環境禁用
  - ✅ 檢查：React DevTools 在 Production 環境禁用

---

## 4️⃣ 安全 Headers

### 4.1 必要 Headers

- [ ] **4.1.1 設定 Strict-Transport-Security (HSTS)**
  - ✅ 實作：`Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - 📋 說明：強制瀏覽器使用 HTTPS

- [ ] **4.1.2 設定 X-Content-Type-Options**
  - ✅ 實作：`X-Content-Type-Options: nosniff`
  - 📋 說明：防止瀏覽器 MIME 類型嗅探

- [ ] **4.1.3 設定 X-Frame-Options**
  - ✅ 實作：`X-Frame-Options: DENY` 或 `SAMEORIGIN`
  - 📋 說明：防止 Clickjacking 攻擊

- [ ] **4.1.4 設定 X-XSS-Protection（舊瀏覽器）**
  - ✅ 實作：`X-XSS-Protection: 1; mode=block`
  - ⚠️ 注意：現代瀏覽器改用 CSP

### 4.2 Content Security Policy (CSP)

- [ ] **4.2.1 設定 Content-Security-Policy Header**
  - ✅ 實作：參考 1.3.1 節的 CSP 設定

- [ ] **4.2.2 CSP Report-Only 模式測試**
  - ✅ 實作：先使用 `Content-Security-Policy-Report-Only` 測試
  - ✅ 實作：設定 `report-uri` 收集違規報告

### 4.3 Referrer Policy

- [ ] **4.3.1 設定 Referrer-Policy**
  - ✅ 實作：`Referrer-Policy: strict-origin-when-cross-origin`
  - 📋 說明：控制 Referer Header 發送範圍

### 4.4 Permissions Policy

- [ ] **4.4.1 設定 Permissions-Policy（前 Feature-Policy）**
  - ✅ 實作：`Permissions-Policy: geolocation=(self), camera=(), microphone=()`
  - 📋 說明：限制瀏覽器功能（如相機、麥克風）

---

## 5️⃣ 第三方套件安全與 HTTPS

### 5.1 第三方套件管理

- [ ] **5.1.1 定期更新套件到最新版本**
  - ✅ 實作：每月執行 `npm update` 或 `yarn upgrade`
  - ✅ 工具：使用 Dependabot 或 Renovate Bot 自動更新

- [ ] **5.1.2 執行安全性掃描（npm audit / yarn audit）**
  - ✅ 實作：CI/CD Pipeline 加入 `npm audit` 步驟
  - ✅ 實作：修復所有 High / Critical 漏洞
  - 📋 範例：
    ```bash
    npm audit --audit-level=high
    ```

- [ ] **5.1.3 避免使用未維護的套件**
  - ✅ 檢查：套件最後更新時間（> 2 年視為未維護）
  - ✅ 檢查：套件 GitHub Issues 回應速度

- [ ] **5.1.4 限制套件權限（Subresource Integrity）**
  - ✅ 實作：CDN 載入的資源使用 SRI
  - 📋 範例：
    ```html
    <script
      src="https://cdn.example.com/lib.js"
      integrity="sha384-abc123..."
      crossorigin="anonymous">
    </script>
    ```

### 5.2 HTTPS 設定

- [ ] **5.2.1 所有環境強制使用 HTTPS**
  - ✅ 實作：HTTP 自動導向 HTTPS（301 Redirect）
  - ✅ 實作：設定 HSTS Header

- [ ] **5.2.2 使用有效的 SSL/TLS 證書**
  - ✅ 實作：使用 Let's Encrypt 免費證書或商業證書
  - ✅ 檢查：證書未過期、域名匹配

- [ ] **5.2.3 禁用 TLS 1.0 和 TLS 1.1**
  - ✅ 實作：伺服器僅允許 TLS 1.2 和 TLS 1.3
  - 📋 檢查：使用 SSL Labs (https://www.ssllabs.com/ssltest/) 測試

### 5.3 API 安全

- [ ] **5.3.1 所有 API 請求使用 HTTPS**
  - ✅ 實作：API Base URL 為 `https://`
  - ❌ 錯誤示範：`http://api.example.com`

- [ ] **5.3.2 API Token 使用 Bearer Token（HTTP Header）**
  - ✅ 實作：`Authorization: Bearer <token>`
  - ❌ 錯誤示範：將 Token 放在 URL 參數

- [ ] **5.3.3 實作 API Rate Limiting（前端限制）**
  - ✅ 實作：防止使用者短時間內大量點擊
  - 📋 範例（React）：
    ```javascript
    import { throttle } from 'lodash';

    const handleSubmit = throttle(() => {
      // Submit logic
    }, 2000); // 2 秒內僅能執行 1 次
    ```

### 5.4 Mobile App 特定

- [ ] **5.4.1 iOS: 啟用 App Transport Security (ATS)**
  - ✅ 實作：Info.plist 預設啟用 ATS
  - ❌ 禁止：設定 `NSAllowsArbitraryLoads = true`

- [ ] **5.4.2 Android: 使用 Network Security Configuration**
  - ✅ 實作：`res/xml/network_security_config.xml` 設定 HTTPS Only
  - 📋 範例：
    ```xml
    <network-security-config>
      <base-config cleartextTrafficPermitted="false" />
    </network-security-config>
    ```

---

## 📊 檢查清單使用範例

### 階段 5: 架構設計檢查

**使用者**: SD-Architect Agent (Marcus)

**檢查重點**：
1. ✅ 設計 CSP 策略（1.3 節）
2. ✅ 設計 CSRF Token 機制（2.1 節）
3. ✅ 規劃敏感資料儲存方案（3.1 節）
4. ✅ 定義安全 Headers 配置（4.1 節）

**產出文件**：
- SRD（System Requirements Document）安全設計章節
- Security_Design_Checklist.md

### 階段 8: 安全測試檢查

**使用者**: QA Agent (Quincy)

**檢查重點**：
1. ✅ 執行 XSS 測試（1.1-1.5 節）
2. ✅ 執行 CSRF 測試（2.1-2.4 節）
3. ✅ 執行敏感資料洩漏測試（3.1-3.4 節）
4. ✅ 驗證 Security Headers（4.1-4.4 節）
5. ✅ 執行第三方套件掃描（5.1 節）

**產出文件**：
- Security_Test_Report.md
- Vulnerability_Scan_Results.md

---

## 🔗 相關文檔連結

### AISDLC 框架文檔
- [Security_Design_Checklist.md](../../guides/system/quality/Security_Design_Checklist.md) - 後端安全設計檢查清單
- [Security_Test_Plan_Template.md](../../../docs_template/core/tests/Security_Test_Plan_Template.md) - 安全測試計畫範本
- [Observability_Design_Guide.md](../../../guides/system/architecture/Observability_Design_Guide.md) - 監控日誌設計指南

### 外部參考
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **OWASP Mobile Top 10**: https://owasp.org/www-project-mobile-top-10/
- **Content Security Policy (CSP)**: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
- **SameSite Cookie**: https://web.dev/samesite-cookies-explained/

---

## 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-25 | 初版建立 - Phase 3 P2 問題修復 (Task 3.12) |

---

**文檔維護者**: AISDLC Framework Team
**最後更新**: 2025-11-25
**狀態**: ✅ Active

---

**End of Document**
