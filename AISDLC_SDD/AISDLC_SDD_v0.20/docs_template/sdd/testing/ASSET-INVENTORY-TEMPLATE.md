# Asset Inventory — Template
# 系統資產清單模板（What to Protect）
# Phase 05 — Security 情境 SDD 強化（Stage 0）

**文件類型**: Asset Inventory (AI)
**SDD Gate**: SCG-5 Security Spec Gate
**使用時機**: 安全架構設計開始前，Stage 0 強制產出
**存放位置**: `docs/06_quality/security/ASSET-INVENTORY-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer} |
| **SCG Gate** | SCG-5 □ 待審 / □ 通過 |
| **前置文件** | SRD-{project}.md, FRD-{project}.md |

---

## 1. 資料資產清單（Data Assets）

> **分類定義**:
> - **PII**: 個人識別資訊（姓名、Email、電話、地址）
> - **PHI**: 個人健康資訊（HIPAA 規範）
> - **PCI**: 支付卡資訊（信用卡號、CVV）
> - **Confidential**: 商業機密資料
> - **Internal**: 僅限內部使用
> - **Public**: 公開資訊

| 資產 ID | 資產名稱 | 資料分類 | 存放位置 | 存取對象 | 法規要求 | 保護等級 |
|--------|---------|---------|---------|---------|---------|---------|
| DA-001 | 使用者帳號資料 | PII | DB: users table | 認證用戶 | GDPR Art.5 | High |
| DA-002 | 支付資訊 | PCI | DB: payments table | 支付服務 | PCI-DSS | Critical |
| DA-003 | 存取日誌 | Internal | Log Storage | 管理員 | — | Medium |
| DA-004 | API Keys | Confidential | Secrets Manager | 服務帳號 | — | High |
| DA-{NNN} | {asset name} | {classification} | {location} | {access} | {regulation} | {level} |

---

## 2. 系統資產清單（System Assets）

### 2.1 應用層

| 資產 ID | 元件名稱 | 類型 | 版本 | 關鍵程度 | 說明 |
|--------|---------|------|------|---------|------|
| SA-APP-001 | {Service/App Name} | Web Application | {version} | Critical/High/Med | {description} |
| SA-APP-002 | {API Gateway} | API Gateway | {version} | Critical | API 入口點 |
| SA-APP-{NNN} | {component} | {type} | {version} | {criticality} | {desc} |

### 2.2 基礎設施層

| 資產 ID | 元件名稱 | 類型 | 提供者 | 關鍵程度 |
|--------|---------|------|-------|---------|
| SA-INFRA-001 | 生產資料庫 | PostgreSQL / MySQL | {AWS RDS / GCP} | Critical |
| SA-INFRA-002 | 快取層 | Redis | {provider} | High |
| SA-INFRA-003 | 訊息佇列 | {Kafka / RabbitMQ} | {provider} | High |
| SA-INFRA-004 | 物件儲存 | S3 / GCS / Azure Blob | {provider} | High |
| SA-INFRA-005 | Secrets Manager | HashiCorp Vault / AWS SM | {provider} | Critical |

### 2.3 第三方服務

| 資產 ID | 服務名稱 | 用途 | 存取方式 | 風險等級 |
|--------|---------|------|---------|---------|
| SA-3P-001 | {Payment Gateway} | 支付處理 | API Key / Webhook | Critical |
| SA-3P-002 | {Email Service} | 郵件發送 | API Key | Medium |
| SA-3P-{NNN} | {service} | {purpose} | {access} | {risk} |

---

## 3. 資產優先保護清單

> 依據「業務影響 × 暴露風險」評估

| 優先級 | 資產 ID | 資產名稱 | 業務影響 | 暴露風險 | 優先保護原因 |
|-------|--------|---------|---------|---------|------------|
| P0 | DA-002 | 支付資訊 | Critical | High | PCI-DSS 法規，直接財務損失 |
| P0 | DA-001 | 使用者帳號 | High | High | GDPR 要求，聲譽風險 |
| P1 | SA-APP-002 | API Gateway | Critical | Medium | 所有流量入口點 |
| P1 | SA-INFRA-005 | Secrets Manager | Critical | Low | 憑證洩漏影響全系統 |

---

## 4. 資料流圖摘要（Data Flow Overview）

```
外部使用者
    ↓ HTTPS
[Load Balancer] → [API Gateway] → [Application Service]
                                        ↓
                              [Database] [Cache] [Queue]
                                        ↓
                              [Third-Party Services]
```

> 完整資料流圖見：TRUST-BOUNDARY-MAP-{system}-{date}.md

---

## 5. 資產保護等級定義

| 保護等級 | 加密要求 | 存取控制 | 稽核日誌 | 備份要求 |
|---------|---------|---------|---------|---------|
| **Critical** | 傳輸+靜態均加密（AES-256） | MFA + RBAC + 最小權限 | 所有操作 | 每日 + 異地備份 |
| **High** | 傳輸加密（TLS 1.3） | RBAC + 最小權限 | 關鍵操作 | 每日備份 |
| **Medium** | 傳輸加密 | 角色存取控制 | 異常操作 | 定期備份 |
| **Low** | 建議加密 | 基本存取控制 | 選擇性 | 定期備份 |

---

## 📋 SCG-5 人工確認點

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| 所有資料資產已識別 | 包含 PII/PCI/PHI/Confidential | □ |
| 法規要求明確標示 | GDPR/PCI-DSS/HIPAA 對應 | □ |
| 資產保護等級已定義 | 每個資產有明確等級 | □ |
| 第三方服務風險已評估 | 包含存取方式和風險等級 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
