# Security Test Specification — Template
# 安全測試規格模板（SAST/DAST/Pentest）
# Phase 05 — Security 情境 SDD 強化（Stage 4）

**文件類型**: Security Test Specification (STS)
**SDD Gate**: SCG-5 Security Spec Gate（安全測試規格先行）
**SDD 原則**: 安全測試規格必須先於 DAST/Pentest 執行
**存放位置**: `docs/03_testing/SECURITY-TEST-SPEC-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer + QA Lead} |
| **SCG Gate** | SCG-5 □ 待審 / □ 通過（規格凍結） |
| **前置文件** | STRIDE-THREAT-MODEL, SAD, COMPLIANCE-MATRIX |

---

## 1. 安全測試範圍

| 測試類型 | 範圍 | 工具 | 觸發時機 |
|---------|------|------|---------|
| SAST（靜態分析） | 所有原始碼 | {SonarQube/Semgrep/Checkmarx} | 每次 PR |
| SCA（依賴掃描） | 所有依賴包 | {Snyk/Dependabot} | 每次 PR + 每日 |
| Container Scan | 所有 Docker Image | {Trivy/Clair} | 每次 Build |
| DAST（動態掃描） | Staging 環境全部端點 | OWASP ZAP | 每次發布前 |
| Pentest | 依需求（年度/大版本） | 外部廠商 | 年度/按需 |
| IaC Scan | Terraform/Helm/K8s | {Checkov/tfsec} | 每次 PR |
| Secret Scan | 所有程式碼倉庫 | {TruffleHog/GitGuardian} | 每次 Commit |

---

## 2. SAST 規格（靜態應用安全測試）

### 2.1 工具與規則集

| 工具 | 規則集 | 嚴重度閾值 | ADR 參考 |
|-----|-------|----------|---------|
| {SonarQube} | OWASP Top 10 + CWE Top 25 | Critical/High → 阻擋 CI | ADR-{NNN} |
| {Semgrep} | 自訂安全規則（based on SAD SC-*） | High → 警告 | ADR-{NNN} |

### 2.2 SAST 掃描規格

| 掃描項目 | 規則 ID | 說明 | Pass/Fail 標準 |
|---------|---------|------|--------------|
| SQL Injection | CWE-89 | 所有 DB 查詢必須參數化 | 0 個 Critical 發現 |
| XSS | CWE-79 | 所有輸出必須編碼 | 0 個 Critical 發現 |
| Hard-coded Secrets | CWE-798 | 不允許明文憑證在程式碼 | 0 個 High+ 發現 |
| Insecure Crypto | CWE-327 | 禁用 MD5/SHA1/DES | 0 個 High+ 發現 |
| 路徑遍歷 | CWE-22 | 輸入驗證防止路徑遍歷 | 0 個 High+ 發現 |

### 2.3 SAST Pass/Fail Criteria

```
阻擋 CI（Block）：
  - 任何 Critical 漏洞
  - 任何 High 漏洞（Security 相關）

警告（Warn）：
  - Medium 漏洞（不阻擋，需追蹤修復）
  - Low 漏洞（記錄至 Tech Debt）
```

---

## 3. DAST 規格（動態應用安全測試）

### 3.1 掃描範圍（基於 SAD 安全控制）

| 掃描類別 | 對應 STRIDE | 測試 API 端點 | 說明 |
|---------|------------|-------------|------|
| Authentication Bypass | Spoofing | /auth/*, /admin/* | 測試認證繞過 |
| IDOR / 越權 | Elevation of Privilege | 所有帶 ID 的端點 | 水平/垂直越權 |
| SQL/NoSQL Injection | Tampering | 所有 POST/PUT 端點 | 注入攻擊 |
| XSS | Information Disclosure | 所有輸出 HTML 端點 | 跨站腳本 |
| SSRF | — | 所有接受 URL 輸入的端點 | 服務端請求偽造 |
| 安全標頭驗證 | — | 所有端點 Response | 標頭完整性 |
| 速率限制 | Denial of Service | /auth/login, /api/* | Rate Limit 驗證 |
| {test_type} | {STRIDE} | {endpoints} | {description} |

### 3.2 DAST 安全測試案例

| STS ID | 測試名稱 | 對應 STRIDE 威脅 | 測試方法 | 預期結果 | Pass/Fail |
|--------|---------|----------------|---------|---------|----------|
| STS-DAST-001 | JWT Token 偽造攻擊 | STR-S-001 | 使用無效 Signature 的 JWT | HTTP 401，不接受偽造 Token | □ |
| STS-DAST-002 | IDOR 水平越權 | STR-E-002 | 存取他人資源（修改 user_id） | HTTP 403，拒絕存取 | □ |
| STS-DAST-003 | SQL Injection | STR-T-001 | 注入 `' OR 1=1--` | HTTP 400/500，不洩漏資料 | □ |
| STS-DAST-004 | XSS 反射型 | STR-I-003 | 注入 `<script>alert(1)</script>` | 輸出已編碼，不執行 JS | □ |
| STS-DAST-005 | 速率限制 | STR-D-001 | 1000 req/min 對 /auth/login | HTTP 429，觸發 Rate Limit | □ |
| STS-DAST-006 | 安全標頭驗證 | STR-I-001 | 檢查所有必要安全標頭 | 全部 SAD 要求標頭存在 | □ |
| STS-DAST-007 | 敏感資料暴露 | STR-I-001/003 | 錯誤回應中不含 stack trace | 統一錯誤格式，無系統資訊 | □ |
| STS-DAST-{NNN} | {test name} | {threat} | {method} | {expected} | □ |

### 3.3 DAST Pass/Fail Criteria

```
阻擋發布：
  - 發現 Critical/High 漏洞（CVSS ≥ 7.0）
  - 認證/授權繞過測試失敗
  - PCI-DSS/GDPR 關鍵合規測試失敗

需記錄（不阻擋）：
  - Medium 漏洞（CVSS 4.0-6.9）→ 1 個月內修復
  - Low 漏洞（CVSS < 4.0）→ 下個 Sprint 評估
```

---

## 4. OWASP Top 10 覆蓋計畫

| OWASP 類別 | ID | 測試方式 | 工具 | 覆蓋狀態 |
|----------|-----|---------|------|---------|
| Broken Access Control | A01:2021 | IDOR 測試 + RBAC 驗證 | DAST | □ 已覆蓋 |
| Cryptographic Failures | A02:2021 | TLS 配置 + 加密算法驗證 | SSL Labs + SAST | □ 已覆蓋 |
| Injection | A03:2021 | SQLi/XSS/Command Injection | SAST + DAST | □ 已覆蓋 |
| Insecure Design | A04:2021 | 威脅建模審查 | STRIDE Review | □ 已覆蓋 |
| Security Misconfiguration | A05:2021 | 配置掃描 + IaC Scan | Checkov + ZAP | □ 已覆蓋 |
| Vulnerable Components | A06:2021 | 依賴漏洞掃描 | Snyk/Dependabot | □ 已覆蓋 |
| Authentication Failures | A07:2021 | 認證測試套件 | DAST | □ 已覆蓋 |
| Software Integrity | A08:2021 | CI/CD Pipeline 審查 + SCA | Snyk + Pipeline Audit | □ 已覆蓋 |
| Logging Failures | A09:2021 | 稽核日誌驗證測試 | 自動化測試 | □ 已覆蓋 |
| SSRF | A10:2021 | SSRF 測試 | DAST | □ 已覆蓋 |

---

## 5. 安全回歸測試規格

> **SDD 原則**: 每次發現新威脅或安全事件後，必須建立對應回歸測試

| 觸發條件 | 回歸測試更新要求 |
|---------|---------------|
| 發現新的 OWASP 分類威脅 | 新增對應 STS-DAST-* 測試案例 |
| Pentest 發現漏洞 | 修復後新增回歸測試防止復發 |
| CVE 漏洞影響系統 | 新增 SCA 掃描規則 |
| 安全事件（Incident） | 根本原因分析後新增測試 |

---

## 6. Pentest 範圍規格（按需）

| 項目 | 說明 |
|------|------|
| **觸發條件** | 年度 / 大版本發布 / 合規要求（PCI-DSS Req.11） |
| **範圍** | Staging 環境，所有對外 API + Admin 介面 |
| **方法論** | OWASP Testing Guide v4.2 |
| **期限** | {N} 週 |
| **報告要求** | CVSS 評分 + 復現步驟 + 修復建議 |
| **修復 SLA** | Critical: 7 天, High: 30 天, Medium: 90 天 |

---

## 📋 SCG-5 安全測試規格凍結確認

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| SAST 規格完整 | 工具/規則集/閾值均已定義 | □ |
| DAST 掃描範圍完整 | 基於 SAD 安全控制清單 | □ |
| OWASP Top 10 全覆蓋 | 10 個類別均有測試方式 | □ |
| 每個 STRIDE 威脅有 DAST 案例 | High+ 威脅有對應測試 | □ |
| Pass/Fail 標準量化 | CVSS 閾值明確 | □ |
| 回歸測試機制 | 有新威脅/事件的更新流程 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過（凍結）/ □ 待修訂
