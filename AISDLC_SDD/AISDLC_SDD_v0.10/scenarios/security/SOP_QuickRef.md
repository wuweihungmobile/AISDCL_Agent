# Security Assessment & Compliance - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 安全評估、漏洞掃描、合規檢查

---

## 🎯 一頁總覽

### 適用場景
✅ 應用程式安全評估
✅ 漏洞掃描與修復
✅ 合規性檢查（GDPR, SOC2, PCI-DSS）
✅ 安全流程建立

### 不適用場景
❌ 單純功能開發（請用 Greenfield）
❌ 效能優化（請用 Performance）
❌ 一般 Bug 修復（請用 Brownfield）

---

## 📋 5 階段快速流程

> 📝 **說明**: 本快速參考採用精簡 5 階段視圖；完整詳細步驟請參閱 [SOP.md](./SOP.md)（內含跨模組授權矩陣、QR 碼安全設計等進階指引）。

```
總時間: 1-3 天

┌─────────────────────────────────────────────┐
│ 階段 1: 安全評估與合規分析 (1-2 天) 🔴       │
│ └─ 資產識別 → STRIDE 威脅建模 → 漏洞掃描    │
│    → 合規差距分析（GDPR/PCI-DSS/個資法）    │
├─────────────────────────────────────────────┤
│ 階段 2: 安全需求與架構設計 (1-2 天) 🔴       │
│ └─ 安全需求 → 跨模組授權矩陣 → 加密策略     │
│    → QR 碼安全設計 → 安全 CI/CD 規劃        │
├─────────────────────────────────────────────┤
│ 階段 3: 安全實施與修復 (2-5 天) 🟡           │
│ └─ P0/P1 漏洞修復 → OWASP Top 10 加固      │
│    → 支付安全（Stripe Webhook 驗證）        │
├─────────────────────────────────────────────┤
│ 階段 4: 安全測試與驗證 (1-3 天) 🟡           │
│ └─ SAST/DAST 掃描 → 滲透測試 → 行動端測試  │
│    → 合規驗證（個資法/PCI-DSS/GDPR）        │
├─────────────────────────────────────────────┤
│ 階段 5: 文檔與交付 (0.5-1 天) ✅             │
│ └─ 安全評估報告 → 合規報告 → 稽核文件       │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速啟動

### 提示詞範例

```
「請載入 AISDLC (v0.01)，我需要進行安全評估」

或具體描述:
「Web 應用程式需要 OWASP Top 10 安全檢查」
「準備 SOC2 審計，需要安全評估」
「發現安全漏洞，需要修復計畫」
```

---

## 🔒 OWASP Top 10 快速檢查清單

### 2021 版本

| # | 威脅 | 檢查項目 | 優先級 |
|---|------|---------|--------|
| **A01** | Broken Access Control | 權限檢查、橫向越權 | 🔴 Critical |
| **A02** | Cryptographic Failures | 加密傳輸、敏感資料保護 | 🔴 Critical |
| **A03** | Injection | SQL/NoSQL/Command Injection | 🔴 Critical |
| **A04** | Insecure Design | 威脅建模、安全設計 | 🔴 Critical |
| **A05** | Security Misconfiguration | 預設配置、錯誤訊息 | 🟡 High |
| **A06** | Vulnerable Components | 套件漏洞、版本過舊 | 🟡 High |
| **A07** | Authentication Failures | 密碼策略、MFA、Session | 🔴 Critical |
| **A08** | Data Integrity Failures | 程式碼/資料完整性驗證 | 🟡 High |
| **A09** | Security Logging Failures | 日誌記錄、監控告警 | 🟢 Medium |
| **A10** | SSRF | Server-Side Request Forgery | 🟡 High |

---

## ⚡ 常見漏洞快速修復

### SQL Injection

**❌ 危險寫法**:
```javascript
const query = `SELECT * FROM users WHERE id = ${userId}`;
db.query(query);
```

**✅ 安全寫法**:
```javascript
const query = 'SELECT * FROM users WHERE id = ?';
db.query(query, [userId]);
```

### XSS (Cross-Site Scripting)

**❌ 危險寫法**:
```javascript
element.innerHTML = userInput;
```

**✅ 安全寫法**:
```javascript
element.textContent = userInput;
// 或使用 DOMPurify
element.innerHTML = DOMPurify.sanitize(userInput);
```

### CSRF (Cross-Site Request Forgery)

**✅ 防護措施**:
```javascript
// 使用 CSRF Token
app.use(csrf());

// 檢查 Origin/Referer
app.use((req, res, next) => {
  const origin = req.get('origin');
  if (origin !== ALLOWED_ORIGIN) {
    return res.status(403).send('Forbidden');
  }
  next();
});

// SameSite Cookie
res.cookie('session', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict'
});
```

---

## 🛠️ 安全掃描工具快速參考

### 靜態分析工具 (SAST)

| 工具 | 語言 | 類型 | 推薦指數 |
|------|------|------|---------|
| **SonarQube** | Multi | SAST | ⭐⭐⭐⭐⭐ |
| **ESLint** | JavaScript | Linter | ⭐⭐⭐⭐⭐ |
| **Semgrep** | Multi | SAST | ⭐⭐⭐⭐⭐ |
| **Bandit** | Python | SAST | ⭐⭐⭐⭐ |
| **Brakeman** | Ruby | SAST | ⭐⭐⭐⭐ |

### 動態分析工具 (DAST)

| 工具 | 類型 | 用途 | 推薦指數 |
|------|------|------|---------|
| **OWASP ZAP** | DAST | Web 漏洞掃描 | ⭐⭐⭐⭐⭐ |
| **Burp Suite** | DAST | 滲透測試 | ⭐⭐⭐⭐⭐ |
| **Nikto** | Scanner | Web 伺服器掃描 | ⭐⭐⭐⭐ |
| **Nmap** | Scanner | 埠掃描 | ⭐⭐⭐⭐⭐ |

### 依賴掃描工具

| 工具 | 語言 | 推薦指數 |
|------|------|---------|
| **npm audit** | Node.js | ⭐⭐⭐⭐ |
| **Snyk** | Multi | ⭐⭐⭐⭐⭐ |
| **Dependabot** | Multi | ⭐⭐⭐⭐⭐ |
| **OWASP Dependency-Check** | Multi | ⭐⭐⭐⭐ |

---

## 📊 風險評級快速參考

### CVSS 評分標準

```yaml
Critical (9.0-10.0): 🔴
- 立即修復
- 可能導致系統完全妥協
- 範例: SQL Injection, RCE

High (7.0-8.9): 🔴
- 1 週內修復
- 重大安全影響
- 範例: XSS, 權限繞過

Medium (4.0-6.9): 🟡
- 1 個月內修復
- 中等安全影響
- 範例: CSRF, 資訊洩漏

Low (0.1-3.9): 🟢
- 計劃修復
- 低安全影響
- 範例: 版本洩漏

None (0.0): ⚪
- 資訊性
- 無安全影響
```

### 修復優先級矩陣

```
高影響 │ P0: 立即修復     │ P1: 1週內        │
       │ (Critical)       │ (High)           │
───────┼─────────────────┼─────────────────┤
低影響 │ P2: 1月內        │ P3: 計劃中       │
       │ (Medium)         │ (Low)            │
       └──────────────────┴─────────────────┘
         易利用             難利用
```

---

## 🎯 合規性快速檢查

### GDPR (一般資料保護規範)

```yaml
必須檢查:
□ 使用者同意機制
□ 資料存取權限（Right to Access）
□ 資料刪除權限（Right to be Forgotten）
□ 資料可攜性（Data Portability）
□ 資料洩漏通知機制（72 小時內）
□ 隱私政策透明化
□ 資料處理紀錄

技術實施:
□ 資料加密（傳輸 + 靜態）
□ 存取控制和稽核日誌
□ 資料最小化原則
□ 匿名化/假名化
```

### SOC 2 (Service Organization Control)

```yaml
五大信賴服務準則:

Security（安全性）:
□ 存取控制
□ 網路安全
□ 變更管理

Availability（可用性）:
□ 系統監控
□ 備份和災難復原
□ 事件管理

Processing Integrity（處理完整性）:
□ 資料驗證
□ 錯誤處理
□ 品質保證

Confidentiality（機密性）:
□ 資料加密
□ 存取權限管理
□ 資料分類

Privacy（隱私性）:
□ 個資保護
□ 同意管理
□ 資料生命週期管理
```

### PCI-DSS (��付卡產業資料安全標準)

```yaml
12 項要求快速檢查:

Build and Maintain:
□ 防火牆配置
□ 不使用供應商預設密碼

Protect Cardholder Data:
□ 儲存的持卡人資料加密
□ 傳輸的持卡人資料加密

Maintain Vulnerability Management:
□ 使用並定期更新防毒軟體
□ 開發安全的系統和應用程式

Implement Strong Access Control:
□ 依業務需求限制資料存取
□ 為每個系統使用者分配唯一 ID
□ 限制實體存取持卡人資料

Monitor and Test Networks:
□ 追蹤和監控所有網路資源
□ 定期測試安全系統和流程

Maintain Information Security Policy:
□ 維護資訊安全政策

重點: 不儲存 CVV/CVC
```

### 🇹🇼 台灣個人資料保護法（個資法）

```yaml
適用條件: 在台灣蒐集、處理或利用個人資料的系統（電商、民宿管理、會員系統）

必須檢查:
□ 蒐集個資時告知當事人（蒐集目的、類別、利用期間）
□ 特定目的原則（EC 訂單資料不可用於 HM 行銷）
□ 跨模組資料共用有合法依據
□ 個資安全維護義務（加密、存取控制）
□ 資料外洩 72 小時內通報主管機關
□ 委外處理契約（Stripe、AWS 等需簽 DPA）
□ 資料主體請求（查詢、更正、刪除）機制

技術實施:
□ PII 欄位資料庫加密（pgcrypto）
□ 稽核日誌記錄個資存取行為
□ 跨模組 API 授權矩陣（防止非目的性利用）
□ 資料保留期限設定與自動刪除

重點: 複合型系統（電商+民宿+內容+知識管理）的跨模組個資使用，
      每次使用必須符合原蒐集之特定目的，否則需重新取得當事人同意。
```

---

## 🚨 安全事件應變流程

### 快速應變步驟

```
1. 識別 (Identify) - 10 分鐘內
   └─ 確認事件類型和影響範圍

2. 隔離 (Contain) - 30 分鐘內
   └─ 隔離受影響系統，防止擴散

3. 根除 (Eradicate) - 2-4 小時
   └─ 移除威脅，修補漏洞

4. 恢復 (Recover) - 4-8 小時
   └─ 系統恢復正常運作

5. 經驗學習 (Lessons Learned) - 1 週內
   └─ 事後檢討，改善流程
```

### 通報時程

```yaml
Internal (內部):
- 安全團隊: 立即
- 管理層: 1 小時內
- 相關團隊: 2 小時內

External (外部):
- 客戶: 24 小時內（視影響）
- 監管機構: 72 小時內（GDPR）
- 執法機關: 視情況
```

---

## ✅ 安全檢查清單

### Pre-Launch Security Checklist

```yaml
認證與授權:
□ 強密碼政策（8+ 字元，混合）
□ 實施 MFA（多因素認證）
□ Session 過期機制
□ 正確實施 OAuth 2.0 / OIDC

資料保護:
□ HTTPS（TLS 1.2+）
□ 敏感資料加密（AES-256）
□ 資料庫加密
□ 安全的密鑰管理

輸入驗證:
□ 所有輸入都驗證和消毒
□ 使用 Prepared Statements（SQL）
□ Content Security Policy (CSP)
□ 檔案上傳驗證

安全配置:
□ 移除預設帳號
□ 最小權限原則
□ 安全 Headers（HSTS, X-Frame-Options）
□ 錯誤訊息不洩漏資訊

日誌與監控:
□ 安全事件日誌
□ 異常偵測告警
□ 定期安全掃描
□ 稽核日誌保留

合規性:
□ 隱私政策
□ 服務條款
□ Cookie 同意
□ 資料處理協議
```

---

## 🔗 延伸閱讀

- 📘 [Security SOP 完整版](./SOP.md)
- 📖 [Security DeepDive 深度指南](./SOP_DeepDive.md)
- 🔒 [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- 📋 [Security Requirements Checklist](../../docs_template/support/Security_Requirements_Checklist.md)
- 🛡️ [STRIDE 威脅分析模板](../../docs_template/support/STRIDE_Threat_Analysis_Template.md)
- 🚀 [Security 快速啟動指令集](../../prompts/scenario-prompts/security-prompts.md)
- 🔧 [Security Assessment Workflow](../../workflow/scenario-specific/security-assessment-flow.md)
- 📄 [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（主導）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（合規審查）
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（安全測試策略）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（威脅建模）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（安全架構設計）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（安全加固實施）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（安全 CI/CD）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（選用）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（選用）
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - Technical Writer（選用）
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - 整合專家（**電商/支付必載**：Stripe 安全、Webhook 驗證、OAuth 安全設計）

### 相關 Skills
- `/security-audit` - OWASP Top 10 安全審計
- `/compliance-audit` - GDPR/PCI-DSS/SOC2/台灣個資法 合規審查
- `/sd-architect` - 安全架構設計（含跨模組授權矩陣）
- `/code-review` - 安全程式碼審查
- `/qa-testing` - 安全測試策略
- `/integration-oauth` - OAuth 2.0/OIDC 認證
- `/integration-database` - 資料庫安全配置（pgcrypto、RLS）
- `/integration-stripe` - 支付安全（Stripe.js Tokenization、PCI-DSS）— **電商必載**
- `/integration-webhook` - Stripe Webhook 簽章驗證 — **電商必載**
- `/devops-github-actions` - 安全 CI/CD Pipeline（SAST/DAST）
- `/devops-docker` - 容器安全（Golden Image、非 root 執行）
- `/devops-monitoring` - 安全事件監控與告警
- `/mobile-development` - 行動端安全（QR 碼 HMAC 簽章、Certificate Pinning）

---

**提示**:
- 🔒 Security is everyone's responsibility
- 🔄 Security is continuous, not one-time
- 📊 Measure and improve security metrics
- 👥 Security awareness training is crucial

---

**文檔版本: v0.01
**最後更新**: 2026-03-31

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

規格凍結（SPEC_FROZEN）→ `python -m autoclaude.tools.sdd_compile` 編譯 playbook → 人工 review YAML → `python -m autoclaude playbooks/sdd_bridge.yaml` 執行（🔴 人工閘門不可跳過）。
全文見：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`。
