# Compliance Matrix — Template
# 合規對照矩陣模板
# Phase 05 — Security 情境 SDD 強化（Stage 3）

**文件類型**: Compliance Matrix (CM)
**SDD Gate**: SCG-5 Security Spec Gate
**使用時機**: SAD 完成後，合規要求確認
**存放位置**: `docs/06_quality/security/COMPLIANCE-MATRIX-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **適用法規** | □ GDPR □ PCI-DSS v4.0 □ ISO 27001:2022 □ HIPAA □ SOC 2 Type II □ 其他 |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Compliance Officer} |
| **稽核日期** | {YYYY-MM-DD}（計劃） |

---

## 1. GDPR 合規對照矩陣

> **適用條件**: 系統處理 EU 公民個人資料

| 條款 | 要求摘要 | 實作方式 | 證據文件 | 狀態 |
|------|---------|---------|---------|------|
| Art.5(1)(a) | 資料處理合法性、公平性、透明性 | 隱私政策 + 明確同意機制 | Privacy Policy | □ 合規 |
| Art.5(1)(b) | 目的限制（僅用於聲明目的） | 資料處理目的文件 | DPA | □ 合規 |
| Art.5(1)(c) | 資料最小化原則 | DTO 僅收集必要欄位 | API 規格審查 | □ 合規 |
| Art.5(1)(e) | 儲存限制（不超過必要期限） | 資料保留政策 + 自動刪除 | Data Retention Policy | □ 合規 |
| Art.5(1)(f) | 完整性和機密性（加密保護） | AES-256 加密 + TLS | SAD 加密規格 | □ 合規 |
| Art.13 | 資料收集時的透明告知 | 隱私聲明 + 同意紀錄 | Privacy Notice | □ 合規 |
| Art.17 | 被遺忘權（資料刪除） | 帳號刪除 API + 資料清除流程 | DEL API 規格 | □ 合規 |
| Art.20 | 資料可攜權 | 匯出個人資料功能 | Export API 規格 | □ 合規 |
| Art.25 | Privacy by Design | 設計階段納入隱私保護 | SAD + SRD | □ 合規 |
| Art.32 | 技術性安全措施 | 加密 + 存取控制 + 監控 | SAD | □ 合規 |
| Art.33 | 72 小時資料洩露通報 | 事件回應程序 | INCIDENT-RESPONSE-SPEC | □ 合規 |
| Art.35 | 資料保護衝擊評估（DPIA） | {DPIA 執行情況} | DPIA Report | □ 合規 |

---

## 2. PCI-DSS v4.0 合規對照矩陣

> **適用條件**: 系統處理、傳輸或存儲支付卡資料

| 要求 | 要求摘要 | 實作方式 | 證據文件 | 狀態 |
|------|---------|---------|---------|------|
| Req 1-2 | 防火牆安裝和維護 | 網路安全群組 + WAF | Network Security Spec | □ 合規 |
| Req 3 | 不存儲敏感認證資料 | Tokenization，不存 CVV/磁條 | SAD 資料分類 | □ 合規 |
| Req 4 | 傳輸加密 | TLS 1.3 強制 | SAD 加密規格 | □ 合規 |
| Req 5 | 反惡意軟體 | Container Security Scan | CICD 安全掃描 | □ 合規 |
| Req 6 | 安全系統開發 | SAST/DAST + Code Review | SECURITY-TEST-SPEC | □ 合規 |
| Req 7 | 存取控制最小權限 | RBAC | SAD 授權規格 | □ 合規 |
| Req 8 | 身份識別和認證 | MFA + 唯一 ID | SAD 認證規格 | □ 合規 |
| Req 10 | 稽核日誌 | Immutable Audit Log | SAD 稽核規格 | □ 合規 |
| Req 11 | 安全測試 | DAST + 滲透測試（年度） | SECURITY-TEST-SPEC | □ 合規 |
| Req 12 | 資訊安全政策 | Security Policy 文件 | Security Policy | □ 合規 |

---

## 3. ISO 27001:2022 合規對照矩陣（重要控制項）

> **適用條件**: 需要 ISO 27001 認證或合規

| 控制項 | 描述 | 實作方式 | 狀態 |
|-------|------|---------|------|
| A.5 - 組織控制 | 資訊安全政策 | Security Policy 文件 | □ |
| A.6 - 人員控制 | 安全意識培訓 | 年度安全培訓 | □ |
| A.8.8 - 漏洞管理 | 技術漏洞管理 | Snyk + Dependabot + CVE 追蹤 | □ |
| A.8.9 - 配置管理 | 安全配置 | IaC + Config as Code | □ |
| A.8.12 - 資料洩漏防護 | DLP 措施 | 資料分類 + 加密 + 存取控制 | □ |
| A.8.15 - 日誌記錄 | 日誌管理 | SIEM + Immutable Log | □ |
| A.8.16 - 監控活動 | 安全監控 | SECURITY-MONITORING-SPEC | □ |
| A.8.23 - Web 過濾 | Web 安全 | WAF + Content Policy | □ |
| A.8.24 - 加密 | 加密使用 | SAD 加密規格 | □ |

---

## 4. 多框架並行合規摘要

> **SDD Phase 05 新增**: 支持同時管理多個合規框架

| 控制領域 | GDPR | PCI-DSS | ISO 27001 | 共同實作 |
|---------|------|---------|---------|---------|
| 資料加密 | Art.32 | Req.3,4 | A.8.24 | AES-256 + TLS 1.3（SAD 加密規格） |
| 存取控制 | Art.32 | Req.7,8 | A.5.15 | RBAC + MFA（SAD 授權規格） |
| 稽核日誌 | Art.30 | Req.10 | A.8.15 | Immutable Audit Log（SAD 日誌規格） |
| 安全測試 | Art.32 | Req.11 | A.8.8 | SAST/DAST（SECURITY-TEST-SPEC） |
| 事件回應 | Art.33 | Req.12 | A.5.26 | INCIDENT-RESPONSE-SPEC（72h 通報） |
| 資料保留 | Art.5(1)(e) | Req.3 | A.8.10 | Data Retention Policy |

---

## 5. 合規缺口分析

| 缺口 ID | 法規條款 | 當前狀態 | 缺口描述 | 修復計畫 | 截止日期 | 負責人 |
|--------|---------|---------|---------|---------|---------|-------|
| GAP-001 | GDPR Art.17 | □ 未實作 | 被遺忘權 API 尚未建立 | 建立 DELETE /users/{id} API | {date} | {owner} |
| GAP-{NNN} | {clause} | □ 部分合規 | {gap description} | {remediation} | {date} | {owner} |

---

## 6. 合規控制自動化驗證

| 控制項 | 自動化驗證方式 | CI/CD 整合 |
|-------|-------------|----------|
| 依賴漏洞 | Snyk/Dependabot 每次 PR 掃描 | L1 SAST |
| 安全標頭 | OWASP ZAP 標頭掃描 | L3 DAST |
| TLS 配置 | SSL Labs A+ 評級驗證 | 部署後檢查 |
| 存取控制 | 授權測試套件（RBAC 矩陣） | L2 Integration |
| 加密配置 | IaC 安全掃描（Checkov/tfsec） | L0 IaCS-Validate |

---

## 📋 合規確認簽署

| 法規框架 | 審核人 | 審核日期 | 結論 |
|---------|-------|---------|------|
| GDPR | {Compliance Officer} | {date} | □ 合規 / □ 有缺口 |
| PCI-DSS | {Compliance Officer} | {date} | □ 合規 / □ 有缺口 |
| ISO 27001 | {Compliance Officer} | {date} | □ 合規 / □ 有缺口 |

**下次合規審查日期**: ____________
