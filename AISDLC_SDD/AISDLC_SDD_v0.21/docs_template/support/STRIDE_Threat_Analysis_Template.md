# STRIDE 威脅分析報告
# STRIDE Threat Analysis Report

**專案名稱**: [專案名稱]
**分析日期**: YYYY-MM-DD
**分析版本**: v1.0
**分析者**: [SA 姓名 + Security Engineer 姓名]
**審查者**: [BA 姓名 / PM 姓名]

---

## 📋 文檔元資訊

| 項目 | 內容 |
|-----|------|
| **專案階段** | Greenfield Stage 2（需求分析與驗證） |
| **參考文檔** | [Security_Threat_Modeling_Guide.md](../../guides/system/quality/Security_Threat_Modeling_Guide.md) |
| **關聯文檔** | [FRD](../core/frd/FRD_Universal_Template.md) - 安全需求章節 |
| **產出需求** | NFR-SEC-001 ~ NFR-SEC-0XX |

---

## 🎯 威脅建模目標

### 分析範圍

**包含範圍**:
- [ ] 使用者認證與授權流程
- [ ] 核心業務功能（如訂單、支付、資料存取）
- [ ] 資料儲存與傳輸
- [ ] 第三方 API 整合
- [ ] 管理後台功能

**排除範圍**:
- [ ] [列出不在此階段分析的功能，如未來版本功能]

### 分析目標

- 識別系統面臨的 6 大類安全威脅（STRIDE）
- 評估威脅的可能性與影響
- 產出 5-10 個高風險威脅的安全需求（NFR-SEC-xxx）
- 為 Stage 3 架構設計提供安全設計指引

---

## 📦 階段 1: 系統資產識別

### 1.1 核心資產清單

| 資產 ID | 資產類別 | 資產項目 | 敏感等級 | 說明 |
|--------|---------|---------|---------|------|
| ASSET-01 | 使用者資料 | 個人資訊（姓名、電話、Email、地址） | 🔴 高 | 個資法保護範圍 |
| ASSET-02 | 認證資料 | 密碼（bcrypt hash）、JWT Token、Refresh Token | 🔴 高 | 洩露後可假冒使用者 |
| ASSET-03 | 金流資料 | 信用卡號（PCI-DSS）、交易記錄、帳戶餘額 | 🔴 高 | 金融監管要求 |
| ASSET-04 | 業務資料 | 訂單資訊、房源資料、評價記錄 | 🟡 中 | 商業機密 |
| ASSET-05 | 系統元件 | API 金鑰、Database 連線字串、第三方服務金鑰 | 🔴 高 | 洩露後系統全面失守 |

**敏感等級定義**:
- 🔴 **高**: 洩露或損毀會造成重大法律責任、商業損失或使用者權益損害
- 🟡 **中**: 洩露或損毀會造成商業競爭力損失或使用者體驗損害
- 🟢 **低**: 洩露或損毀影響有限

---

## 🌐 階段 2: 資料流圖 (DFD)

### 2.1 Level 1 資料流圖

```
外部實體                信任邊界                   系統元件
┌──────────┐                                    ┌──────────────┐
│   使用者   │ ──[1]── HTTPS ────┐               │   前端 App   │
│  (Browser) │                   ├──────────────▶│  (React)     │
└──────────┘                   │               └──────┬───────┘
                                 │                      │ [2] JWT
┌──────────┐                   │                      ▼
│ 第三方 API │ ◀─────[4]─────────┤               ┌──────────────┐
│ (Payment)  │                   │               │ API Gateway  │
└──────────┘                   │               │ (Authorization)│
                                 │               └──────┬───────┘
                                 │                      │ [3] 內網
信任邊界                         │                      ▼
════════════════════════════════│══════════════ ┌──────────────┐
                                                 │ 應用服務     │
                                                 │ (Spring Boot)│
                                                 └──────┬───────┘
                                                        │
                                                        ▼
                                                 ┌──────────────┐
                                                 │  資料庫      │
                                                 │ (PostgreSQL) │
                                                 └──────────────┘
                                                        ▲
                                                        │
                                                 ┌──────┴───────┐
                                                 │   快取服務   │
                                                 │   (Redis)    │
                                                 └──────────────┘
```

### 2.2 信任邊界定義

| 邊界 ID | 信任邊界 | 通訊協定 | 認證機制 | 威脅等級 |
|--------|---------|---------|---------|---------|
| **邊界 1** | 使用者 ↔ 前端 | HTTPS | 無（公開存取） | 🔴 高 |
| **邊界 2** | 前端 ↔ API Gateway | HTTPS + JWT | JWT Token 驗證 | 🔴 高 |
| **邊界 3** | API Gateway ↔ 內部服務 | 內網 HTTP | Service-to-Service Auth（可選） | 🟡 中 |
| **邊界 4** | 內部服務 ↔ 第三方 API | HTTPS | API Key / OAuth 2.0 | 🔴 高 |

**威脅等級說明**:
- 🔴 **高**: 跨信任邊界，需嚴格驗證與加密
- 🟡 **中**: 內網通訊，需考慮內部威脅
- 🟢 **低**: 可信環境內通訊

---

## 🛡️ 階段 3: STRIDE 威脅分析

### 3.1 威脅分析矩陣

#### 威脅 1: 使用者登入流程

**資料流**: `[使用者] → [前端] → [API Gateway] → [認證服務]`

| STRIDE 類別 | 威脅場景 | 可能性 | 影響 | 風險等級 | 應對措施 |
|------------|---------|-------|------|---------|---------|
| **S**poofing | 攻擊者竊取 JWT Token 假冒使用者登入 | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-001: JWT 短期有效、Refresh Token 輪換 |
| **T**ampering | 修改 JWT payload 提升權限（如 role: "admin"） | 🟢 低 | 🔴 高 | 🟡 **中** | NFR-SEC-001: JWT 簽名驗證（RS256） |
| **R**epudiation | 缺少登入日誌，無法追蹤可疑登入行為 | 🟡 中 | 🟡 中 | 🟡 **中** | NFR-SEC-004: 登入操作完整日誌 |
| **I**nformation Disclosure | 登入錯誤訊息洩露使用者是否存在 | 🟡 中 | 🟢 低 | 🟢 **低** | 統一錯誤訊息「帳號或密碼錯誤」 |
| **D**enial of Service | 暴力破解攻擊耗盡 API 資源 | 🔴 高 | 🟡 中 | 🔴 **高** | NFR-SEC-005: Rate Limiting（每 IP 5 次/分鐘） |
| **E**levation of Privilege | 繞過權限檢查存取其他使用者資料 | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-001: 每個 API 驗證使用者權限 |

---

#### 威脅 2: 訂單建立流程

**資料流**: `[使用者] → [API] → [訂單服務] → [資料庫]`

| STRIDE 類別 | 威脅場景 | 可能性 | 影響 | 風險等級 | 應對措施 |
|------------|---------|-------|------|---------|---------|
| **S**poofing | 攻擊者假冒房東取消訂單 | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-001: 角色驗證（只有房東可取消） |
| **T**ampering | 修改訂單價格（如 price: 1000 → 1） | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-002: Request Schema 驗證 + 後端重算 |
| **R**epudiation | 使用者否認預訂操作 | 🟢 低 | 🟡 中 | 🟢 **低** | NFR-SEC-004: 訂單操作日誌 |
| **I**nformation Disclosure | API 回傳其他使用者的訂單資訊 | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-003: 權限過濾（僅回傳當前使用者資料） |
| **D**enial of Service | 批量建立訂單耗盡資源 | 🟡 中 | 🟡 中 | 🟡 **中** | NFR-SEC-005: Rate Limiting（每使用者 10 次/秒） |
| **E**levation of Privilege | 一般使用者修改房東專屬欄位（如佣金比例） | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-002: 欄位權限驗證 |

---

#### 威脅 3: 資料存取流程

**資料流**: `[API] → [資料庫]`

| STRIDE 類別 | 威脅場景 | 可能性 | 影響 | 風險等級 | 應對措施 |
|------------|---------|-------|------|---------|---------|
| **S**poofing | N/A（內部通訊） | - | - | - | - |
| **T**ampering | SQL Injection 修改或刪除資料 | 🟡 中 | 🔴 高 | 🔴 **高** | NFR-SEC-002: ORM Prepared Statements |
| **R**epudiation | 資料修改無審計日誌 | 🟡 中 | 🟡 中 | 🟡 **中** | NFR-SEC-004: Database Audit Log |
| **I**nformation Disclosure | 資料庫備份未加密 | 🟢 低 | 🔴 高 | 🟡 **中** | Database 備份加密（AES-256） |
| **D**enial of Service | 慢查詢導致資料庫癱瘓 | 🟡 中 | 🔴 高 | 🔴 **高** | Query Timeout + 索引優化 |
| **E**levation of Privilege | 應用層使用 root 帳號連線 | 🟢 低 | 🔴 高 | 🟡 **中** | 最小權限原則（應用層帳號僅 CRUD 權限） |

---

### 3.2 風險等級統計

| 風險等級 | 威脅數量 | 百分比 | 處理優先級 |
|---------|---------|-------|----------|
| 🔴 **高** | 10 | 55.6% | 必須立即處理（轉為 NFR-SEC-xxx） |
| 🟡 **中** | 6 | 33.3% | 應優先處理（Stage 3 架構設計） |
| 🟢 **低** | 2 | 11.1% | 建議處理（視時程決定） |
| **總計** | 18 | 100% | - |

**風險計算公式**:
```
風險等級 = 可能性 × 影響

可能性: 🔴 高(3) 🟡 中(2) 🟢 低(1)
影響:   🔴 高(3) 🟡 中(2) 🟢 低(1)

風險等級:
- 🔴 高: 6-9 分（可能性×影響）
- 🟡 中: 3-4 分
- 🟢 低: 1-2 分
```

---

## ✅ 階段 4: 安全需求清單（NFR-SEC）

### 4.1 高風險威脅對應安全需求

#### NFR-SEC-001: 認證與授權

**需求來源**:
- 威脅 1 - Spoofing（竊取 Token 假冒登入）
- 威脅 1 - Elevation of Privilege（繞過權限檢查）
- 威脅 2 - Spoofing（假冒房東取消訂單）

**需求描述**:
- 所有 API 請求必須包含有效的 JWT Token（Authorization: Bearer {token}）
- JWT Token 必須使用 RS256 或 HS256 簽名
- Access Token 有效期限：15 分鐘
- Refresh Token 有效期限：7 天，使用後輪換（Rotation）
- 每個 API 端點必須驗證使用者角色（User/Host/Admin）
- 權限檢查邏輯：
  - User: 僅能存取自己的資源
  - Host: 能存取自己的房源和訂單
  - Admin: 能存取所有資源

**驗收標準**:
- [ ] 未攜帶 Token 的請求回傳 `401 Unauthorized`
- [ ] 過期 Token 回傳 `401 Token Expired`
- [ ] 無效 Token（簽名錯誤）回傳 `401 Invalid Token`
- [ ] 未授權請求回傳 `403 Forbidden`
- [ ] 測試案例 1: 一般使用者嘗試呼叫管理員 API → 403
- [ ] 測試案例 2: 使用者 A 嘗試讀取使用者 B 的訂單 → 403
- [ ] 測試案例 3: 房東嘗試取消其他房東的訂單 → 403

**技術實作建議** (Stage 3 參考):
- JWT 簽名金鑰儲存在環境變數，不可硬編碼
- 使用 Redis 儲存 Refresh Token，支援提前撤銷（Revoke）
- API Gateway 層統一驗證 JWT，減少重複驗證邏輯

---

#### NFR-SEC-002: 輸入驗證與防篡改

**需求來源**:
- 威脅 2 - Tampering（修改訂單價格）
- 威脅 3 - Tampering（SQL Injection）

**需求描述**:
- 所有使用者輸入必須經過雙層驗證：
  - **前端驗證**: 立即回饋使用者（UX 考量）
  - **後端驗證**: 安全防線（不可信任前端）
- 防止 SQL Injection:
  - 使用 ORM（如 Hibernate/TypeORM）的 Prepared Statements
  - 禁止拼接 SQL 字串
- 防止 XSS（跨站腳本）:
  - 所有使用者輸入顯示前必須 HTML 編碼
  - Content-Security-Policy Header
- API Request Schema 驗證:
  - 使用 JSON Schema 驗證 Request Body
  - 不符合 Schema 的請求回傳 `400 Bad Request`
- 關鍵業務邏輯後端重算:
  - 訂單總價必須由後端計算，不可信任前端傳送的價格
  - 折扣、優惠券規則由後端驗證

**驗收標準**:
- [ ] SQL Injection 測試: 輸入 `' OR '1'='1` 無效
- [ ] XSS 測試: 輸入 `<script>alert(1)</script>` 被編碼為 `&lt;script&gt;...`
- [ ] Schema 驗證: 送出不符合 Schema 的 Request 回傳 400
- [ ] 測試案例 1: 前端傳送 `price: 1`，後端重算為 `price: 1000` ✅
- [ ] 測試案例 2: 嘗試使用無效優惠券代碼 → 400 Invalid Coupon

**技術實作建議** (Stage 3 參考):
- 使用 `class-validator` (NestJS) 或 `Joi` (Express) 進行 Schema 驗證
- 使用 ORM Query Builder 而非 raw SQL
- 使用 DOMPurify (前端) + OWASP Java Encoder (後端) 防 XSS

---

#### NFR-SEC-003: 敏感資料保護

**需求來源**:
- 威脅 2 - Information Disclosure（洩露其他使用者訂單）
- 威脅 3 - Information Disclosure（資料庫備份未加密）

**需求描述**:
- 密碼儲存:
  - 使用 bcrypt 加密（salt round: 12）
  - 禁止儲存明文密碼
- HTTPS 強制:
  - 所有 HTTP 請求自動重導向至 HTTPS
  - HSTS Header (Strict-Transport-Security)
- API 回應不洩露敏感資訊:
  - 錯誤訊息不包含 SQL 錯誤、Stack Trace
  - 統一錯誤格式: `{ "error": "操作失敗", "code": "ERR_INTERNAL" }`
- 權限過濾:
  - 使用者僅能存取自己的資料
  - API 回應前必須過濾非授權資料
- 資料庫備份加密:
  - 使用 AES-256 加密備份檔案
  - 金鑰儲存在 Key Management Service (KMS)

**驗收標準**:
- [ ] 密碼儲存格式: bcrypt hash（長度 60 字元，開頭 `$2b$`）
- [ ] HTTP 請求自動重導向至 HTTPS
- [ ] 測試案例 1: 觸發錯誤，回應不包含 stack trace ✅
- [ ] 測試案例 2: 使用者 A 呼叫 `GET /orders`，僅回傳使用者 A 的訂單 ✅
- [ ] 測試案例 3: 資料庫備份檔案已加密（使用 `file` 命令驗證）

---

#### NFR-SEC-004: 日誌與審計

**需求來源**:
- 威脅 1 - Repudiation（缺少登入日誌）
- 威脅 2 - Repudiation（否認預訂操作）

**需求描述**:
- 認證操作日誌:
  - 登入成功/失敗
  - 登出
  - 密碼修改
  - 權限提升操作
- 業務操作日誌:
  - 建立訂單
  - 取消訂單
  - 付款操作
  - 資料修改（UPDATE/DELETE）
- 日誌格式（JSON）:
  ```json
  {
    "timestamp": "2025-12-13T10:30:00Z",
    "user_id": "USER-123",
    "ip_address": "203.0.113.45",
    "action": "LOGIN_SUCCESS",
    "resource": "/api/auth/login",
    "result": "success",
    "metadata": { "user_agent": "..." }
  }
  ```
- 日誌保留期限: 90 天
- 日誌集中管理: 使用 ELK Stack / CloudWatch Logs

**驗收標準**:
- [ ] 登入成功/失敗都有日誌
- [ ] 訂單建立有日誌（包含 user_id, order_id）
- [ ] 日誌包含時間戳、使用者 ID、IP 位址、操作類型
- [ ] 測試案例: 觸發登入失敗，檢查日誌存在且格式正確

---

#### NFR-SEC-005: API Rate Limiting

**需求來源**:
- 威脅 1 - Denial of Service（暴力破解）
- 威脅 2 - Denial of Service（批量建立訂單）

**需求描述**:
- 登入 API 限流:
  - 每 IP 每分鐘最多 5 次請求
  - 超過限制回傳 `429 Too Many Requests`
- 一般 API 限流:
  - 每使用者每秒最多 10 次請求
  - 每 IP 每分鐘最多 100 次請求（防止未登入濫用）
- 限流實作:
  - 使用 Redis 實作 Sliding Window 或 Token Bucket 演算法
  - Rate Limit Header:
    - `X-RateLimit-Limit`: 限制值
    - `X-RateLimit-Remaining`: 剩餘次數
    - `X-RateLimit-Reset`: 重置時間戳
- 429 回應格式:
  ```json
  {
    "error": "Too Many Requests",
    "retry_after": 60
  }
  ```

**驗收標準**:
- [ ] 連續 6 次登入請求，第 6 次回傳 429
- [ ] 429 回應包含 `Retry-After` header
- [ ] Rate Limit Header 正確顯示剩餘次數
- [ ] 測試案例: 模擬 100 TPS 請求，驗證限流機制生效

---

### 4.2 中風險威脅處理策略

以下威脅雖為中風險，但建議在 **Stage 3 架構設計** 時考慮：

| 威脅 ID | 威脅場景 | 建議應對措施 |
|--------|---------|-------------|
| T1-R | 缺少登入日誌 | 已納入 NFR-SEC-004 |
| T2-D | 批量建立訂單耗盡資源 | 已納入 NFR-SEC-005 |
| T3-R | 資料修改無審計日誌 | 已納入 NFR-SEC-004 |
| T3-I | 資料庫備份未加密 | 已納入 NFR-SEC-003 |
| T3-E | 應用層使用 root 帳號 | 最小權限原則（架構設計階段執行） |

---

## 📊 階段 5: 威脅建模完成檢查

### 5.1 完成度檢查清單

- [ ] **已識別核心資產**: 5 個（目標: 3-5 個）
- [ ] **已繪製資料流圖**: Level 1 DFD
- [ ] **已標示信任邊界**: 4 個（目標: 3-5 個）
- [ ] **已執行 STRIDE 分析**: 18 個威脅（目標: 至少 10 個）
- [ ] **已識別高風險威脅**: 10 個（目標: 5-10 個）
- [ ] **已產出安全需求**: 5 個 NFR-SEC（目標: 5-10 個）
- [ ] **安全需求包含驗收標準**: 所有 NFR-SEC 都有可測試的 AC

### 5.2 審查確認

| 審查角色 | 審查重點 | 審查狀態 | 審查日期 | 審查意見 |
|---------|---------|---------|---------|---------|
| **SA** | 威脅識別完整性、需求可行性 | ⏳ 待審查 | YYYY-MM-DD | |
| **Security Engineer** | 安全需求合理性、STRIDE 分析正確性 | ⏳ 待審查 | YYYY-MM-DD | |
| **BA** | 業務影響評估、優先級排序 | ⏳ 待審查 | YYYY-MM-DD | |
| **PM/PO** | 成本與時程可行性 | ⏳ 待審查 | YYYY-MM-DD | |

**審查狀態**: ⏳ 待審查 / ✅ 已通過 / ❌ 需修改

---

## 📈 預期效益

### 量化指標

| 指標 | 基準值（無威脅建模） | 目標值（執行威脅建模後） | 提升幅度 |
|------|-------------------|---------------------|---------|
| **安全需求涵蓋率** | 20% | 90%+ | ↑ 70% |
| **上線後安全漏洞數** | 15 個 | 4 個 | ↓ 73% |
| **安全審查通過率** | 40% | 95% | ↑ 55% |
| **安全事件損失風險** | $50k | $10k | ↓ 80% |

### ROI 評估

- **投入成本**: 5 人日（SA 3 人日 + Security Engineer 2 人日）
- **預期效益**: 避免安全事件損失 $40k
- **ROI**: 80:1

---

## 📚 附錄

### A. 參考資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Microsoft STRIDE Threat Modeling](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### B. 相關文檔

- [Security_Threat_Modeling_Guide.md](../../guides/system/quality/Security_Threat_Modeling_Guide.md) - 威脅建模執行指南
- [Security_Architecture_Checklist.md](../../guides/system/architecture/Security_Architecture_Checklist.md) - 安全架構檢查清單
- [Security_Design_Checklist.md](../../guides/system/quality/Security_Design_Checklist.md) - 安全設計檢查清單
- [FRD_Universal_Template.md](../core/frd/FRD_Universal_Template.md) - 功能需求文檔（安全需求章節）

---

**維護記錄**:
- v1.0 (YYYY-MM-DD): 初版建立（Stage 2 威脅分析完成）
