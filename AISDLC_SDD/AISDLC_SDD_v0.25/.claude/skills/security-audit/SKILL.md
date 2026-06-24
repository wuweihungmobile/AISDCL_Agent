---
name: security-audit
description: 安全審查，STRIDE 威脅建模為第一步驟，安全設計先於實作，對應 SDD_SECURITY_CICD 規格
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: full|api|frontend|dependencies] [standard: owasp|gdpr|pci-dss]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Security Audit Skill（SDD 原生）

安全在 SDD 中屬於「設計先行」範疇：STRIDE 威脅建模必須在任何安全相關實作前完成，安全需求必須在 FRD 中以 NFR-SEC-XXX 格式量化，安全架構在 SCG-2 前凍結。本 Skill 不是「事後掃描」，而是「安全設計閘門」。

---

## 觸發方式

```bash
/security-audit full
/security-audit api owasp
/security-audit dependencies
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | 架構設計完成（需要 C4 圖做 STRIDE） | `docs/02_architecture/SRD-{System}.md` 存在 |
| NFR-SEC 量化 | 安全需求已在 FRD 定義 | `docs/01_requirements/FRD-{System}.md` 中 `NFR-SEC-XXX` 存在 |

---

## 執行流程

### 階段 1：STRIDE 威脅建模（第一步，不可跳過）🔴

STRIDE 威脅建模必須在安全實作之前完成，依據 C4 架構圖識別威脅：

**文件路徑**：`docs/06_quality/security/STRIDE-{SystemName}.md`

```markdown
# STRIDE 威脅模型 — {SystemName}

**基礎架構**: `docs/02_architecture/SRD-{SystemName}.md` C4 圖
**版本**: {N}.{N}
**狀態**: Draft → Validated（SCG-2 前）

## 資產清單

| 資產 ID | 名稱 | 類型 | 敏感度 | 信任邊界 |
|---------|------|------|--------|---------|
| A-001 | 使用者認證 Token | 資料資產 | 高 | 外部→內部 |
| A-002 | 用戶個資 | 資料資產 | 高 | 內部 |

## 信任邊界定義

| 邊界 ID | 名稱 | 說明 |
|---------|------|------|
| TB-001 | 外部使用者→API Gateway | 最高風險邊界 |
| TB-002 | API→Database | 內部通訊 |

## STRIDE 威脅分析

| 威脅 ID | STRIDE 類型 | 資產 | 攻擊向量 | 風險等級 | 對應控制措施 | NFR-SEC ID |
|---------|------------|------|---------|---------|------------|-----------|
| T-001 | Spoofing（偽冒） | A-001 | 偽造 JWT Token | 高 | JWT 簽章驗證 | NFR-SEC-001 |
| T-002 | Tampering（篡改）| A-002 | SQL Injection | 高 | 參數化查詢 | NFR-SEC-002 |
| T-003 | Repudiation（否認）| 操作記錄 | 日誌偽造 | 中 | 不可變日誌 | NFR-SEC-003 |
| T-004 | Info Disclosure（資訊洩漏）| A-002 | API 錯誤洩漏 | 高 | 統一錯誤回應 | NFR-SEC-004 |
| T-005 | DoS（阻斷服務）| API | Rate Limit 繞過 | 中 | Rate Limiting | NFR-SEC-005 |
| T-006 | Elevation（權限提升）| 系統 | IDOR | 高 | 資源授權驗證 | NFR-SEC-006 |
```

🔴 確認點：STRIDE 威脅模型由 SD 確認後才可開始安全設計。

---

### 階段 2：安全架構設計（SAD）

依據 STRIDE 輸出，建立安全架構設計文件：

**文件路徑**：`docs/06_quality/security/SAD-{SystemName}.md`

```markdown
# Security Architecture Document (SAD) — {SystemName}

## 安全控制措施（對應 STRIDE 威脅）

| T-ID | 威脅 | 控制措施 | 實作方式 | NFR-SEC |
|------|------|---------|---------|---------|
| T-001 | JWT 偽造 | RS256 非對稱簽章 | jwt library + Key Rotation | NFR-SEC-001 |
| T-002 | SQL Injection | 參數化查詢 | ORM（Prisma/TypeORM） | NFR-SEC-002 |
| T-005 | DoS | Rate Limiting | express-rate-limit / Kong | NFR-SEC-005 |

## 安全 NFR 對應

| NFR-SEC ID | 需求描述 | 目標值 | 驗證方式 |
|-----------|---------|--------|---------|
| NFR-SEC-001 | 認證強度 | JWT RS256，TTL ≤ 1h | 滲透測試 |
| NFR-SEC-002 | Injection 防護 | OWASP A03 Pass | SAST + Semgrep |
| NFR-SEC-003 | 審計日誌 | 所有敏感操作記錄 | 日誌完整性測試 |
```

---

### 階段 3：OWASP Top 10 自動化掃描

```bash
# 依賴漏洞掃描
npm audit --json > audit-report.json

# SAST（對應 STRIDE T-XXX）
semgrep --config=p/owasp-top-ten .

# API 安全（對應 SAD 設計）
npx @stoplight/spectral-cli lint docs/02_architecture/api/CONTRACT-*.yaml \
  --ruleset .spectral-security.yml
```

**OWASP Top 10 檢查清單（對應 STRIDE 威脅）**：

| OWASP | 對應 STRIDE | NFR-SEC | 狀態 |
|-------|-----------|---------|------|
| A01 Broken Access Control | T-006 Elevation | NFR-SEC-006 | 待確認 |
| A02 Cryptographic Failures | T-002 Tampering | NFR-SEC-007 | 待確認 |
| A03 Injection | T-002 Tampering | NFR-SEC-002 | 待確認 |
| A04 Insecure Design | T-001~T-006 | 全部 | 待確認 |
| A07 Authentication Failures | T-001 Spoofing | NFR-SEC-001 | 待確認 |
| A09 Logging & Monitoring | T-003 Repudiation | NFR-SEC-003 | 待確認 |
| A10 SSRF | T-004 Info Disclosure | NFR-SEC-004 | 待確認 |

---

### 階段 4：安全審查報告產出

**文件路徑**：`docs/06_quality/security/SECURITY-AUDIT-REPORT-{SystemName}-{date}.md`

```markdown
# 安全審查報告 — {SystemName}

**審查日期**: {YYYY-MM-DD}
**審查範圍**: {範圍描述}
**STRIDE 威脅模型**: STRIDE-{SystemName}.md
**整體風險等級**: 高/中/低

## 發現問題

### 高風險（需立即修復，阻擋 SCG-5）
| T-ID | OWASP | 位置 | 描述 | 修復建議 | NFR-SEC |
|------|-------|------|------|---------|---------|

### 中風險（SCG-5 前修復）
| T-ID | OWASP | 位置 | 描述 | 修復建議 | NFR-SEC |
|------|-------|------|------|---------|---------|

## 合規結論
- OWASP Top 10: {X}/10 通過
- SCG-5 安全閘門: Pass/Fail
```

---

### 階段 5：RTM 更新與 SCG-5 準備 🔴

```bash
/rtm-generate update    # 更新安全相關 TC（TC-SEC-XXX）
/spec-compliance-check docs/06_quality/security/STRIDE-{System}.md
/sdd-gate SCG-5         # 提交安全驗證證據
```

🔴 確認點：高風險問題全部修復後才可執行 SCG-5。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| STRIDE 威脅模型 | `docs/06_quality/security/STRIDE-{System}.md` | SCG-2 前 |
| SAD 安全架構 | `docs/06_quality/security/SAD-{System}.md` | SCG-2 |
| 安全審查報告 | `docs/06_quality/security/SECURITY-AUDIT-REPORT-{System}.md` | SCG-5 |

---

## 後置動作

```
/sdd-gate SCG-5              # 安全通過後提交閘門
/compliance-audit            # 若有法規合規需求
/release-management          # 發布前安全確認
```

🔷 **本 Skill 協助通過**：SCG-2（安全架構凍結）、SCG-5（安全驗收）

---

## 相關 Skill

- `/sd-architect` — C4 架構圖（STRIDE 威脅建模的輸入）
- `/adr-generate` — 安全控制措施 ADR
- `/compliance-audit` — 法規合規（GDPR/PCI-DSS）
- `/rtm-generate` — 安全 TC 追蹤

---

**基於**: AISDLC-SDD v0.25
**對應 CI/CD 規格**: `cicd/SDD_SECURITY_CICD.md`
**SDD Enhancement**: `scenarios/security/SDD_SECURITY_ENHANCEMENT.md`
