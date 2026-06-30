# AISDLC-SDD Security 指令集

**情境**: Security — STRIDE 驅動的安全強化
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要執行安全審查/強化，使用 SDD Security 情境（STRIDE 驅動）。

載入：AISDLC_SDD_v0.01/scenarios/security/SDD_SECURITY_ENHANCEMENT.md

安全需求：
- 系統：[名稱]
- 系統類型：[Web API / Mobile App / 微服務]
- 合規要求：[GDPR / HIPAA / PCI-DSS / OWASP / 無特定要求]
- 主要關注：[認證/授權 / 資料保護 / API 安全 / 其他]

SDD 原則：STRIDE 威脅模型必須在安全實作前完成（設計先於實作）。
```

## 📊 階段推進

### STRIDE 威脅模型
```
請執行 STRIDE 威脅模型分析。

系統：[名稱]
架構圖：[C4 路徑 / 描述]
信任邊界：[列出主要邊界]

STRIDE 分析：
- Spoofing（身份偽造）：哪些身份驗證點可能被偽造？
- Tampering（資料篡改）：哪些資料傳輸/儲存可能被篡改？
- Repudiation（不可否認性）：哪些操作需要審計日誌？
- Information Disclosure（資訊洩露）：哪些敏感資料可能洩露？
- Denial of Service（阻斷服務）：哪些端點容易被 DoS 攻擊？
- Elevation of Privilege（權限提升）：哪些邏輯可能被繞過？

產出：STRIDE 威脅清單（含嚴重度評估）
```

### 安全需求規格化
```
STRIDE 分析完成，請將威脅轉化為安全需求。

威脅清單：[來自 STRIDE 分析]

產出安全需求：
- 格式：NFR-SEC-XXX：[安全需求描述]
- 對應的緩解措施
- 整合到 FRD/SRD 中

這些需求將成為 SCG-5 安全驗收標準。
```

### OWASP Top 10 審查
```
請針對系統執行 OWASP Top 10 審查。

系統：[名稱]
代碼路徑：[路徑]（若有）

審查項目：
1. A01 - Broken Access Control
2. A02 - Cryptographic Failures
3. A03 - Injection
4. A04 - Insecure Design
5. A05 - Security Misconfiguration
6. A06 - Vulnerable Components
7. A07 - Auth Failures
8. A08 - Software Integrity Failures
9. A09 - Logging Failures
10. A10 - SSRF

產出：安全審查報告（含修復建議優先級）
```

### 安全 ADR
```
請為以下安全設計決策生成 ADR。

決策主題：[認證機制 / 加密方案 / 授權模型 / 其他]
背景：[安全需求描述]
選項：[選項 A / B / C]
決策：[選擇和理由]

格式：ADR-[NNN]-security-[topic].md
```

### SCG-5 STRIDE Validate
```
安全實作完成，請執行 SCG-5 STRIDE 驗證。

原始 STRIDE 威脅清單：[路徑]
實作文件：[路徑]

驗證：每個高/中嚴重度威脅是否有對應的緩解措施？
未處理的威脅必須有明確的接受風險決策（ADR）。
```

## 🔄 常見變體

### 快速 API 安全審查
```
請快速審查以下 API 的安全性。

API 規格：[OpenAPI 路徑 / 端點描述]

重點檢查：
- 認證/授權機制是否完整？
- 輸入驗證是否足夠？
- 敏感資料是否在回應中洩露？
- Rate Limiting 是否存在？
```

### 合規性審查（GDPR/HIPAA/PCI-DSS）
```
請執行 [GDPR / HIPAA / PCI-DSS] 合規性審查。

系統：[名稱]
個人資料類型：[描述收集的資料]

審查：
- 哪些功能可能違反合規要求？
- 需要增加哪些控制措施？
- 建議的合規改善計畫
```
