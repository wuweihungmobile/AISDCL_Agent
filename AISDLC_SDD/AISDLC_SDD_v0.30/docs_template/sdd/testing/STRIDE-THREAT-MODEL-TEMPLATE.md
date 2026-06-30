# STRIDE Threat Model — Template
# STRIDE 威脅模型規格模板
# Phase 05 — Security 情境 SDD 強化（Stage 1）

**文件類型**: STRIDE Threat Model (STM)
**SDD Gate**: SCG-5 Security Spec Gate（威脅模型凍結）
**使用時機**: 信任邊界確認後，安全控制設計前
**存放位置**: `docs/06_quality/security/STRIDE-THREAT-MODEL-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **模型版本** | v{1.0} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer} |
| **SCG Gate** | SCG-5 □ 待審 / □ 通過（凍結） |
| **前置文件** | TRUST-BOUNDARY-MAP, ASSET-INVENTORY |

---

## STRIDE 威脅類別說明

| 類別 | 縮寫 | 定義 | 對應安全屬性 |
|------|------|------|------------|
| **Spoofing** | S | 偽冒合法身份 | Authentication |
| **Tampering** | T | 未授權修改資料或程式碼 | Integrity |
| **Repudiation** | R | 否認已執行的操作 | Non-Repudiation |
| **Information Disclosure** | I | 向未授權方洩露資訊 | Confidentiality |
| **Denial of Service** | D | 讓服務無法使用 | Availability |
| **Elevation of Privilege** | E | 獲取超過授予的權限 | Authorization |

---

## 風險評分公式

```
風險分數 = 可能性（1-5）× 影響（1-5）

風險等級:
  Critical: 20-25
  High:     15-19
  Medium:   8-14
  Low:      1-7
```

---

## STRIDE 威脅分析矩陣

### S — Spoofing（身份偽冒）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-S-001 | 攻擊者偽造 JWT Token 存取 API | API Gateway | 偽造/篡改 JWT Payload | 3 | 5 | 15 | High | 強制驗證 JWT Signature（RS256），Token 短期有效（15min） | Low |
| STR-S-002 | 憑證填充攻擊（Credential Stuffing） | Auth Service | 使用洩漏帳密批量登入 | 4 | 4 | 16 | High | Rate Limiting, MFA 強制, 異常登入檢測 | Medium |
| STR-S-003 | API Key 洩漏後被冒用 | API Gateway | 第三方 API Key 洩漏 | 2 | 4 | 8 | Medium | API Key 輪換機制，使用 Secrets Manager | Low |
| STR-S-{NNN} | {threat} | {asset} | {attack path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

### T — Tampering（資料竄改）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-T-001 | SQL Injection 竄改資料庫 | Users DB | 惡意 SQL 注入 | 3 | 5 | 15 | High | ORM / 參數化查詢，Input Validation | Low |
| STR-T-002 | MITM 攻擊竄改 API 傳輸資料 | API 傳輸 | 中間人攔截 | 2 | 5 | 10 | Medium | TLS 1.3 強制，Certificate Pinning（Mobile） | Low |
| STR-T-003 | 未授權修改訂單資料 | Orders DB | 越權操作 | 2 | 4 | 8 | Medium | RBAC 驗證，業務不變量檢查（INV-XXX） | Low |
| STR-T-{NNN} | {threat} | {asset} | {path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

### R — Repudiation（否認行為）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-R-001 | 使用者否認已完成支付 | Payments | 無法舉證操作記錄 | 2 | 4 | 8 | Medium | 不可否認日誌（Immutable Audit Log），加密簽署 | Low |
| STR-R-002 | 管理員否認系統配置變更 | Admin Log | 日誌被刪除/竄改 | 1 | 3 | 3 | Low | WORM 日誌存儲，多重簽名稽核 | Low |
| STR-R-{NNN} | {threat} | {asset} | {path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

### I — Information Disclosure（資訊洩露）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-I-001 | 錯誤訊息洩露系統架構 | 所有 API | verbose error response | 3 | 3 | 9 | Medium | 統一錯誤回應格式，不暴露 stack trace | Low |
| STR-I-002 | 資料庫未加密靜態 PII 洩露 | Users DB | 資料庫備份外洩 | 2 | 5 | 10 | Medium | AES-256 靜態加密，備份加密 | Low |
| STR-I-003 | 過度資料暴露（API 回傳非必要欄位） | API | 回傳完整 DB 記錄 | 3 | 3 | 9 | Medium | DTO 嚴格定義，僅回傳必要欄位 | Low |
| STR-I-{NNN} | {threat} | {asset} | {path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

### D — Denial of Service（服務拒絕）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-D-001 | DDoS 攻擊淹沒 API Gateway | API Gateway | 大量請求 | 3 | 5 | 15 | High | CDN DDoS 防護, Rate Limiting, Auto-Scaling | Medium |
| STR-D-002 | 資源耗盡攻擊（複雜查詢） | Database | 惡意複雜 SQL | 2 | 4 | 8 | Medium | 查詢超時限制，複雜度分析 | Low |
| STR-D-003 | 大量檔案上傳耗盡存儲 | File Storage | 無限制上傳 | 2 | 3 | 6 | Medium | 上傳大小/速率限制，用戶配額 | Low |
| STR-D-{NNN} | {threat} | {asset} | {path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

### E — Elevation of Privilege（特權提升）威脅

| 威脅 ID | 威脅描述 | 目標資產 | 攻擊路徑 | 可能性 | 影響 | 風險分數 | 等級 | 緩解措施 | 緩解後風險 |
|--------|---------|---------|---------|-------|------|---------|------|---------|----------|
| STR-E-001 | 普通用戶存取管理員 API | Admin API | 水平/垂直越權 | 2 | 5 | 10 | Medium | RBAC 嚴格驗證，預設拒絕，伺服器端授權 | Low |
| STR-E-002 | IDOR（直接物件引用） | Any API | 竄改 ID 存取他人資料 | 3 | 4 | 12 | Medium | 所有資源驗證擁有者，使用 UUID | Low |
| STR-E-003 | CI/CD Pipeline 注入執行任意程式 | CI/CD | 依賴包投毒 | 2 | 5 | 10 | Medium | 依賴鎖定，SCA 掃描，Pipeline 最小權限 | Low |
| STR-E-{NNN} | {threat} | {asset} | {path} | {1-5} | {1-5} | {score} | {level} | {mitigation} | {residual} |

---

## 威脅優先級總覽

| 等級 | 數量 | 威脅 IDs |
|------|------|---------|
| Critical（20-25） | {N} | {list} |
| High（15-19） | {N} | STR-S-001, STR-S-002, STR-D-001 |
| Medium（8-14） | {N} | STR-S-003, STR-T-001... |
| Low（1-7） | {N} | {list} |

---

## 安全控制需求（從威脅模型提取）

| 控制 ID | 控制類別 | 描述 | 緩解威脅 | 對應 ADR |
|--------|---------|------|---------|---------|
| SC-001 | Authentication | JWT RS256 + 15min 有效期 | STR-S-001 | ADR-{NNN} |
| SC-002 | Rate Limiting | 每 IP 每分鐘 100 請求 | STR-S-002, STR-D-001 | ADR-{NNN} |
| SC-003 | Input Validation | ORM 參數化查詢 | STR-T-001 | — |
| SC-004 | Authorization | RBAC + 資源擁有者驗證 | STR-E-001, STR-E-002 | ADR-{NNN} |
| SC-{NNN} | {category} | {description} | {STR-IDs} | ADR-{NNN} |

---

## 📋 SCG-5 威脅模型凍結確認

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| 6 類 STRIDE 均已分析 | S/T/R/I/D/E 每類 ≥ 2 威脅 | □ |
| 每個威脅有量化風險分數 | 可能性 × 影響 = 分數 | □ |
| 每個威脅有緩解措施 | 無 "N/A" 或空白 | □ |
| 緩解後殘餘風險已評估 | 標示緩解後風險等級 | □ |
| 安全控制需求已提取 | 每個控制有對應威脅 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過（凍結）/ □ 待修訂
