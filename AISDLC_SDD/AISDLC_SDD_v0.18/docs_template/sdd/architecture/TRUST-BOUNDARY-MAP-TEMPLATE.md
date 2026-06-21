# Trust Boundary Map — Template
# 信任邊界圖模板
# Phase 05 — Security 情境 SDD 強化（Stage 0）

**文件類型**: Trust Boundary Map (TBM)
**SDD Gate**: SCG-5 Security Spec Gate
**使用時機**: STRIDE 威脅模型建立前，Stage 0 強制產出
**存放位置**: `docs/02_architecture/TRUST-BOUNDARY-MAP-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer + SD Architect} |
| **前置文件** | ASSET-INVENTORY-{system}.md, SRD-{project}.md |

---

## 1. 信任區域定義（Trust Zones）

> **信任邊界** = 不同信任等級的系統元件之間的邊界，跨越邊界的每個資料流都是潛在威脅點。

| 區域 ID | 區域名稱 | 信任等級 | 說明 | 包含元件 |
|--------|---------|---------|------|---------|
| TZ-00 | 外部網際網路（Untrusted） | 0（最低） | 完全不受信任 | 外部使用者、攻擊者、爬蟲 |
| TZ-01 | DMZ（非軍事化區） | 1 | 部分受信任的公開接觸面 | Load Balancer, API Gateway, CDN |
| TZ-02 | 應用層（Application Tier） | 2 | 受信任的應用服務 | Backend Services, BFF |
| TZ-03 | 資料層（Data Tier） | 3 | 高度受信任的資料存儲 | Database, Cache, Queue |
| TZ-04 | 管理層（Management Tier） | 4（最高） | 最高信任的管理服務 | Secrets Manager, Admin Tools, CI/CD |
| TZ-{N} | {zone name} | {level} | {description} | {components} |

---

## 2. 信任邊界圖（ASCII 表示）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TZ-00: 外部網際網路（Untrusted）                                          │
│                                                                           │
│  [外部使用者]  [第三方服務]  [攻擊者]                                        │
│                                                                           │
│  ══════════════════ 邊界 B1: Internet → DMZ ══════════════════            │
│  （HTTPS Only, WAF, Rate Limiting, DDoS Protection）                      │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │  TZ-01: DMZ（Non-Military Zone）                                   │   │
│  │  [Load Balancer]  [API Gateway]  [CDN]  [WAF]                     │   │
│  │                                                                   │   │
│  │  ══════════════ 邊界 B2: DMZ → Application ════════════           │   │
│  │  （Service Mesh mTLS, JWT Validation, Service Account）           │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────┐     │   │
│  │  │  TZ-02: Application Tier                                │     │   │
│  │  │  [Auth Service]  [API Service]  [Business Logic]        │     │   │
│  │  │                                                         │     │   │
│  │  │  ═══════════════ 邊界 B3: App → Data ════════════       │     │   │
│  │  │  （Connection String Encrypted, RBAC, Audit Log）       │     │   │
│  │  │                                                         │     │   │
│  │  │  ┌───────────────────────────────────────────────┐     │     │   │
│  │  │  │  TZ-03: Data Tier                             │     │     │   │
│  │  │  │  [PostgreSQL]  [Redis]  [Kafka]  [S3]         │     │     │   │
│  │  │  └───────────────────────────────────────────────┘     │     │   │
│  │  └─────────────────────────────────────────────────────────┘     │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  TZ-04: Management Tier（獨立隔離）                                  │  │
│  │  [Secrets Manager]  [Monitoring]  [CI/CD]  [Admin]                 │  │
│  │  （僅允許特定 IP + MFA + VPN 存取）                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 信任邊界清單（Trust Boundaries）

| 邊界 ID | 名稱 | 從 Zone | 到 Zone | 跨越方式 | 安全控制 | STRIDE 威脅關注點 |
|--------|------|--------|--------|---------|---------|----------------|
| B1 | Internet → DMZ | TZ-00 | TZ-01 | HTTPS 443 | WAF, DDoS, TLS 1.3 | Spoofing, DoS |
| B2 | DMZ → Application | TZ-01 | TZ-02 | Internal HTTP/gRPC | JWT Validation, mTLS | Tampering, EoP |
| B3 | Application → Data | TZ-02 | TZ-03 | DB Connection | RBAC, Encrypted Conn | Info Disclosure |
| B4 | App → Third Party | TZ-02 | TZ-00 | HTTPS + API Key | TLS, API Key Rotation | Repudiation |
| B5 | Internet → Management | TZ-00 | TZ-04 | HTTPS + VPN | MFA, IP Whitelist | EoP, Spoofing |

---

## 4. 資料流追蹤（Data Flow Tracing）

### 4.1 使用者登入流程

```
使用者（TZ-00）
  → [B1] → API Gateway（TZ-01）：HTTPS + TLS 1.3
  → [B2] → Auth Service（TZ-02）：JWT 請求
  → [B3] → Users DB（TZ-03）：查詢帳號
  ← JWT Token ← Auth Service ← API Gateway ← 使用者

資料流中的敏感資料: 密碼（Hash）, Email（PII）
邊界保護: TLS 加密傳輸, 密碼不可逆 Hash（bcrypt）
```

### 4.2 支付流程

```
使用者（TZ-00）
  → [B1] → API Gateway（TZ-01）
  → [B2] → Payment Service（TZ-02）
  → [B4] → 第三方支付服務（TZ-00）：PCI-DSS Compliant
  ← 支付結果 ← Payment Service → [B3] → Payments DB（TZ-03）

資料流中的敏感資料: 支付卡資訊（PCI），不存儲完整卡號
邊界保護: Tokenization，不通過系統傳遞卡號原文
```

---

## 5. 邊界安全控制規格

| 邊界 ID | 控制措施 | 實作方式 | 驗證方法 |
|--------|---------|---------|---------|
| B1 | TLS 1.3 強制 | Nginx/ALB 配置 | SSL Labs A+ 評級 |
| B1 | WAF 規則 | OWASP CRS | DAST 測試驗證 |
| B2 | JWT 驗證 | API Gateway Middleware | Unit + Integration Test |
| B2 | mTLS（服務間） | Service Mesh (Istio/Linkerd) | mTLS 驗證測試 |
| B3 | DB 加密連線 | SSL 強制連線 | DB 連線審計 |
| B3 | RBAC | DB 角色權限 | 權限測試 |
| B4 | API Key 輪換 | Secrets Manager 自動輪換 | 輪換測試 |
| B5 | MFA 強制 | Auth0 / Okta MFA | 登入稽核 |

---

## 6. 外部實體（External Entities）

| 實體 ID | 名稱 | 類型 | 信任等級 | 互動邊界 | 風險說明 |
|--------|------|------|---------|---------|---------|
| EE-001 | 一般使用者 | Human | 0（不受信任） | B1 | 可能是惡意攻擊者 |
| EE-002 | 管理員 | Human | 2（部分信任） | B5 + MFA | 特權帳號，需嚴格控制 |
| EE-003 | 支付服務 | Third-Party | 1（有限信任） | B4 | 外部 API，需驗證回傳 |
| EE-004 | CI/CD 系統 | Automated | 3（高度信任） | B5 | 部署管道，需限制權限 |

---

## 📋 SCG-5 人工確認點

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| 所有信任區域已識別 | ≥ 4 層（Untrusted/DMZ/App/Data） | □ |
| 所有邊界有明確安全控制 | 每個邊界有實作方式 | □ |
| 關鍵資料流已追蹤 | 含敏感資料的流程已記錄 | □ |
| 外部實體風險已評估 | 包含第三方服務 | □ |
| 與資產清單一致 | 所有 Critical 資產在 TZ-03/04 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
