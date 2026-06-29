# 安全威脅建模指南
# Security Threat Modeling Guide

**版本**: v0.01
**建立日期**: 2025-12-13
**文檔類型**: 系統參考文件 - 安全設計
**適用階段**: Greenfield SOP Stage 2（需求分析與驗證）
**目標使用者**: SA (System Analyst), Security Engineer

---

## 🎯 文檔目的

本指南協助開發團隊在 Stage 2（需求分析與驗證）執行**安全威脅建模 (Security Threat Modeling)**，使用 **STRIDE 方法**系統化識別安全威脅，並產出對應的**安全需求清單（NFR）**。

---

## 📊 STRIDE 威脅分類框架

STRIDE 是微軟提出的威脅建模方法，將安全威脅分為 6 大類別：

| STRIDE 類別 | 威脅定義 | 範例 |
|------------|---------|------|
| **S**poofing（欺騙） | 攻擊者假冒合法使用者或系統 | 竊取 JWT Token、偽造 Cookie |
| **T**ampering（篡改） | 未經授權修改資料或程式碼 | SQL Injection、修改 HTTP Request |
| **R**epudiation（否認） | 使用者否認執行的操作 | 缺少日誌審計、無法追蹤操作來源 |
| **I**nformation Disclosure（資訊洩露） | 機密資料被未授權存取 | API 回傳過多資料、錯誤訊息洩露敏感資訊 |
| **D**enial of Service（阻斷服務） | 使系統無法正常運作 | DDoS 攻擊、資源耗盡攻擊 |
| **E**levation of Privilege（權限提升） | 獲得超出授權的權限 | 越權存取其他使用者資料、繞過權限檢查 |

---

## 🔍 威脅建模執行步驟

### 步驟 1: 識別系統資產

**定義**: 列出需要保護的核心資產

**範例 (BnB 訂房網站)**:
| 資產類別 | 資產項目 | 敏感等級 |
|---------|---------|---------|
| **使用者資料** | 個人資訊（姓名、電話、Email） | 🔴 高 |
| **認證資料** | 密碼、OAuth Token、JWT | 🔴 高 |
| **金流資料** | 信用卡資訊、交易記錄 | 🔴 高 |
| **業務資料** | 訂單資訊、房源資料 | 🟡 中 |
| **系統元件** | API 金鑰、Database 連線字串 | 🔴 高 |

---

### 步驟 2: 繪製資料流圖 (DFD)

**定義**: 繪製 Level 1 或 Level 2 資料流圖，標示資料流動路徑

**範例 (預訂流程)**:
```
[使用者] → [前端 React] → [API Gateway] → [訂房服務] → [資料庫]
              ↑                  ↓
         [JWT Token]      [支付服務]
                               ↓
                        [第三方支付 API]
```

**標示威脅邊界**:
- **信任邊界 1**: 使用者 ↔ 前端（HTTP/HTTPS）
- **信任邊界 2**: 前端 ↔ API Gateway（JWT 驗證）
- **信任邊界 3**: API Gateway ↔ 內部服務（內網）
- **信任邊界 4**: 內部服務 ↔ 第三方 API（外部整合）

---

### 步驟 3: 應用 STRIDE 分析威脅

**對每個資料流和元件應用 STRIDE 分析**

#### 範例 1: 使用者登入流程

| STRIDE 類別 | 威脅場景 | 可能性 | 影響 | 風險等級 |
|------------|---------|-------|------|---------|
| **S**poofing | 攻擊者竊取使用者 JWT Token 假冒登入 | 🟡 中 | 🔴 高 | 🔴 高 |
| **T**ampering | 修改 JWT payload 提升權限（如 role: "admin"） | 🟢 低 | 🔴 高 | 🟡 中 |
| **R**epudiation | 缺少登入日誌，無法追蹤可疑登入 | 🟡 中 | 🟡 中 | 🟡 中 |
| **I**nformation Disclosure | 錯誤訊息洩露使用者是否存在 | 🟡 中 | 🟢 低 | 🟢 低 |
| **D**enial of Service | 暴力破解攻擊耗盡 API 資源 | 🔴 高 | 🟡 中 | 🔴 高 |
| **E**levation of Privilege | 繞過權限檢查存取其他使用者資料 | 🟡 中 | 🔴 高 | 🔴 高 |

**風險等級計算**:
```
風險等級 = 可能性 × 影響
🔴 高風險：必須立即處理（Stage 2 產出安全需求）
🟡 中風險：應優先處理（Stage 3 架構設計時考慮）
🟢 低風險：建議處理（視開發時程決定）
```

---

#### 範例 2: 訂單建立流程

| STRIDE 類別 | 威脅場景 | 可能性 | 影響 | 風險等級 |
|------------|---------|-------|------|---------|
| **S**poofing | 攻擊者假冒房東取消訂單 | 🟡 中 | 🔴 高 | 🔴 高 |
| **T**ampering | 修改訂單價格（如 price: 1000 → 1） | 🟡 中 | 🔴 高 | 🔴 高 |
| **R**epudiation | 使用者否認預訂操作 | 🟢 低 | 🟡 中 | 🟢 低 |
| **I**nformation Disclosure | API 回傳其他使用者的訂單資訊 | 🟡 中 | 🔴 高 | 🔴 高 |
| **D**enial of Service | 批量建立訂單耗盡資源 | 🟡 中 | 🟡 中 | 🟡 中 |
| **E**levation of Privilege | 一般使用者修改房東專屬欄位 | 🟡 中 | 🔴 高 | 🔴 高 |

---

### 步驟 4: 產出安全需求清單（NFR）

**將 🔴 高風險威脅轉換為安全需求（NFR）**

#### 範例輸出格式

**安全需求文檔**:
```markdown
## 安全需求 (Security Requirements)

### NFR-SEC-001: 認證與授權

**需求來源**: STRIDE 分析 - Spoofing & Elevation of Privilege

**需求描述**:
- 所有 API 請求必須包含有效的 JWT Token
- JWT Token 必須簽名（使用 RS256 或 HS256）
- Token 有效期限：15 分鐘（Access Token）、7 天（Refresh Token）
- 權限檢查：每個 API 端點驗證使用者角色（User/Host/Admin）

**驗證標準**:
- [ ] 未認證請求回傳 401 Unauthorized
- [ ] 過期 Token 回傳 401 Token Expired
- [ ] 未授權請求回傳 403 Forbidden
- [ ] 測試案例：嘗試使用一般使用者 Token 呼叫管理員 API

---

### NFR-SEC-002: 輸入驗證與防篡改

**需求來源**: STRIDE 分析 - Tampering

**需求描述**:
- 所有使用者輸入必須驗證（前端 + 後端雙層驗證）
- 防止 SQL Injection（使用 ORM Prepared Statements）
- 防止 XSS（HTML 編碼輸出）
- API Request Schema 驗證（使用 JSON Schema）

**驗證標準**:
- [ ] SQL Injection 測試：輸入 `' OR '1'='1` 無效
- [ ] XSS 測試：輸入 `<script>alert(1)</script>` 被編碼
- [ ] Schema 驗證：送出不符合 Schema 的 Request 回傳 400

---

### NFR-SEC-003: 敏感資料保護

**需求來源**: STRIDE 分析 - Information Disclosure

**需求描述**:
- 密碼使用 bcrypt 加密（salt round: 12）
- HTTPS 強制（禁止 HTTP）
- API 回應不洩露敏感資訊（錯誤訊息不顯示 SQL 錯誤）
- 權限過濾：使用者僅能存取自己的訂單

**驗證標準**:
- [ ] 密碼儲存格式：bcrypt hash（長度 60 字元）
- [ ] HTTP 請求自動重導向至 HTTPS
- [ ] 錯誤訊息不包含 stack trace 或 SQL 語句
- [ ] 測試案例：使用者 A 無法讀取使用者 B 的訂單

---

### NFR-SEC-004: 日誌與審計

**需求來源**: STRIDE 分析 - Repudiation

**需求描述**:
- 記錄所有認證操作（登入、登出、密碼修改）
- 記錄關鍵業務操作（建立訂單、取消訂單、付款）
- 日誌包含：時間戳、使用者 ID、IP 位址、操作類型、結果

**驗證標準**:
- [ ] 登入成功/失敗都有日誌
- [ ] 訂單建立有日誌（包含使用者 ID、訂單 ID）
- [ ] 日誌保留期限：90 天

---

### NFR-SEC-005: API Rate Limiting

**需求來源**: STRIDE 分析 - Denial of Service

**需求描述**:
- 登入 API：每 IP 每分鐘最多 5 次請求
- 一般 API：每使用者每秒最多 10 次請求
- 超過限制回傳 429 Too Many Requests
- 使用 Redis 實作 Rate Limiting

**驗證標準**:
- [ ] 連續 6 次登入請求，第 6 次回傳 429
- [ ] Rate Limit Header 顯示剩餘請求數
- [ ] 測試案例：模擬 100 TPS 請求，驗證限流機制
```

---

## 📋 威脅建模檢查清單

### 階段 1: 準備階段
- [ ] **識別核心資產**（使用者資料、認證、金流等）
- [ ] **繪製資料流圖 (DFD)** Level 1
- [ ] **標示信任邊界**（使用者 ↔ 系統、系統 ↔ 第三方）

### 階段 2: STRIDE 分析
- [ ] **對每個資料流應用 STRIDE**
- [ ] **計算風險等級**（可能性 × 影響）
- [ ] **識別 🔴 高風險威脅**（至少 10 個）

### 階段 3: 產出安全需求
- [ ] **將高風險威脅轉換為 NFR**
- [ ] **定義驗收標準**（可測試）
- [ ] **納入 FRD 文檔**（新增「安全需求」章節）

### 階段 4: 驗證與審查
- [ ] **SA 審查**：威脅識別完整性
- [ ] **Security Engineer 審查**：安全需求合理性
- [ ] **PM 確認**：成本與時程可行性

---

## 🛠️ 工具支援

### STRIDE 分析工具
- **Microsoft Threat Modeling Tool** (免費)
- **OWASP Threat Dragon** (開源)
- **手動填寫 STRIDE 矩陣** (Excel/Google Sheets)

### 參考資源
- **OWASP Top 10** (最新版本)
- **Microsoft SDL Threat Modeling**
- **NIST Cybersecurity Framework**

---

## 📈 預期效益

### Stage 2 執行威脅建模後：

| 指標 | 改進前 | 改進後 | 提升幅度 |
|------|--------|--------|---------|
| **安全需求涵蓋率** | 20% | 90%+ | ↑ 70% |
| **上線後安全漏洞數** | 15 個 | 4 個 | ↓ 73% |
| **安全事件損失** | $50k（風險） | $10k（風險） | ↓ 80% |
| **安全審查通過率** | 40% | 95% | ↑ 55% |

**ROI 評估**:
- **投入成本**: 5 人日（SA 3 人日 + Security Engineer 2 人日）
- **預期效益**: 避免安全事件損失 $40k
- **ROI**: 80:1

---

## 📚 相關文檔

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Security_Architecture_Checklist.md](../architecture/Security_Architecture_Checklist.md)
- [Security_Design_Checklist.md](./Security_Design_Checklist.md)
- [FRD_Universal_Template.md](../../../docs_template/core/frd/FRD_Universal_Template.md)

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（P1-5 改進項目）
