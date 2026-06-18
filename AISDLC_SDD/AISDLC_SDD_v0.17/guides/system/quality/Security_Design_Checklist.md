# 安全設計檢查清單
# Security Design Checklist

**文檔版本**: v1.0
**建立日期**: 2025-11-19
**適用階段**: SOP 階段 5 - SRD 撰寫
**對應 SOP**: Greenfield/Brownfield SOP - 階段 5

---

## 📋 文檔目的

本文檔提供 **安全設計檢查清單**，確保系統在設計階段即考慮全面的安全需求。

### 使用者

- **SD-Architect Agent (Marcus)**: 安全架構設計
- **QA Agent (Quincy)**: 安全測試規劃
- **Dev Agent (David)**: 安全實作

---

## 1️⃣ 身份驗證與授權

### 1.1 身份驗證

- [ ] 支援多因素驗證 (MFA)
- [ ] 密碼強度要求（8+ 字元、大小寫、數字、符號）
- [ ] 密碼雜湊使用安全演算法（bcrypt, Argon2）
- [ ] 帳號鎖定機制（5 次失敗後鎖定 15 分鐘）
- [ ] Session 管理安全（HttpOnly, Secure, SameSite）
- [ ] JWT Token 設計（短效、refresh token 機制）
- [ ] OAuth 2.0 / OIDC 整合（如需要）

### 1.2 授權

- [ ] 角色權限設計 (RBAC / ABAC)
- [ ] 最小權限原則
- [ ] 權限檢查在每個 API endpoint
- [ ] 資源層級授權（用戶只能存取自己的資料）

---

## 2️⃣ 資料安全

### 2.1 傳輸安全

- [ ] HTTPS 強制（HSTS 啟用）
- [ ] TLS 1.2+ 版本
- [ ] 敏感 API 使用額外加密
- [ ] Certificate Pinning（Mobile App）

### 2.2 儲存安全

- [ ] 敏感資料加密（AES-256）
- [ ] 資料庫加密 at rest
- [ ] 金鑰管理（KMS）
- [ ] PII 資料標記與保護

### 2.3 資料分類

- [ ] 公開資料
- [ ] 內部資料
- [ ] 機密資料
- [ ] 高度機密資料

---

## 3️⃣ 輸入驗證與輸出編碼

### 3.1 輸入驗證

- [ ] 白名單驗證優先
- [ ] SQL Injection 防護（參數化查詢）
- [ ] XSS 防護（輸入過濾）
- [ ] Command Injection 防護
- [ ] Path Traversal 防護
- [ ] 檔案上傳驗證（類型、大小、內容）

### 3.2 輸出編碼

- [ ] HTML 編碼
- [ ] JavaScript 編碼
- [ ] URL 編碼
- [ ] CSS 編碼

---

## 4️⃣ Web 安全（Web App 專屬）

### 4.1 HTTP 安全標頭

- [ ] Content-Security-Policy (CSP)
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Referrer-Policy
- [ ] Permissions-Policy

### 4.2 CSRF 防護

- [ ] CSRF Token 機制
- [ ] SameSite Cookie 設定
- [ ] Origin/Referer 檢查

### 4.3 CORS 設定

- [ ] 白名單 Origins
- [ ] 適當的 Methods 限制
- [ ] Credentials 設定

---

## 5️⃣ Mobile 安全（Mobile App 專屬）

### 5.1 本地儲存

- [ ] Keychain/Keystore 使用
- [ ] 避免明文儲存敏感資料
- [ ] 資料庫加密（Realm Encryption）

### 5.2 程式碼安全

- [ ] 程式碼混淆
- [ ] 反逆向工程措施
- [ ] Root/Jailbreak 檢測

### 5.3 通訊安全

- [ ] Certificate Pinning
- [ ] 禁用不安全協議

---

## 6️⃣ API 安全

### 6.1 API 設計

- [ ] Rate Limiting
- [ ] 請求大小限制
- [ ] API 版本管理
- [ ] 敏感操作需額外驗證

### 6.2 API 文檔安全

- [ ] 生產環境隱藏 Swagger
- [ ] API Key 管理
- [ ] Webhook 簽名驗證

---

## 7️⃣ 日誌與監控

### 7.1 安全日誌

- [ ] 登入/登出記錄
- [ ] 敏感操作記錄
- [ ] 異常行為記錄
- [ ] 不記錄敏感資料

### 7.2 監控告警

- [ ] 可疑活動告警
- [ ] DDoS 攻擊偵測
- [ ] 異常流量監控

---

## 8️⃣ 錯誤處理

- [ ] 不洩漏系統資訊
- [ ] 統一錯誤格式
- [ ] Stack Trace 只在開發環境
- [ ] 敏感操作失敗不透露原因

---

## 9️⃣ 第三方安全

- [ ] 定期更新依賴
- [ ] 漏洞掃描（Dependabot, Snyk）
- [ ] License 合規檢查
- [ ] 第三方 API 安全評估

---

## 🔟 合規需求

- [ ] GDPR（歐盟用戶）
- [ ] 個資法（台灣）
- [ ] PCI DSS（支付處理）
- [ ] HIPAA（醫療資料）
- [ ] SOC 2（企業服務）

---

## 📋 安全設計審查

### 審查結果

| 類別 | 檢查項目 | 已確認 | 完整性 |
|-----|---------|-------|--------|
| 1. 身份驗證與授權 | 11 | - | - |
| 2. 資料安全 | 10 | - | - |
| 3. 輸入驗證與輸出編碼 | 10 | - | - |
| 4. Web 安全 | 11 | - | - |
| 5. Mobile 安全 | 8 | - | - |
| 6. API 安全 | 7 | - | - |
| 7. 日誌與監控 | 7 | - | - |
| 8. 錯誤處理 | 4 | - | - |
| 9. 第三方安全 | 4 | - | - |
| 10. 合規需求 | 5 | - | - |

---

## 🔗 相關文件

- [SRD_Universal_Template.md](../docs_template/srd/SRD_Universal_Template.md)
- [Security_Test_Plan_Template.md](Security_Test_Plan_Template.md)

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-19 | 初版建立 - Phase 1 P0 問題修正 |

---

**文檔維護者**: AISDLC Framework Team
**最後更新**: 2025-11-19
**狀態**: ✅ Active

---

**End of Document**
