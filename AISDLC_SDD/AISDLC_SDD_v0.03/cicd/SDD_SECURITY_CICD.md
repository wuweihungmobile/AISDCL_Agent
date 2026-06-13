# SDD Security CI/CD Pipeline 規格
# SDD Security Scenario CI/CD Specification

**版本**: v1.0
**建立日期**: 2026-04-13
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: `AISDLC_SDD_v0.01/cicd/`
**Spec Gate**: 🔷 SCG-5 Security Spec Gate
**對應 Phase**: Phase 05 — 情境十：Security（安全與合規）

---

## 🎯 目的

定義 SDD Security 情境的 CI/CD Pipeline 規格，強制在 Pipeline 中實現「安全設計先行」原則：
- STRIDE 威脅模型完整性在 L0 驗證
- SAST 規則集基於 SAD 安全控制規格
- DAST 掃描範圍基於 Security Test Spec
- 合規對照矩陣自動驗證
- 高風險安全問題即時通知

---

## 🏗️ Pipeline 架構

```
┌─────────────────────────────────────────────────────────┐
│            SDD Security CI/CD Pipeline                   │
├─────────────────────────────────────────────────────────┤
│  L0: DocLint + STRIDE-Validate（威脅模型完整性）         │
│   ↓                                                      │
│  L1: Unit Test + Security Unit Test                      │
│   ↓                                                      │
│  SAST（SDD 強化）:                                       │
│    ├── 規則集基於 SAD 安全控制規格                       │
│    ├── OWASP Top 10 自動覆蓋                             │
│    └── SCA：依賴漏洞掃描                                 │
│   ↓                                                      │
│  Container: 容器安全掃描（Image Vulnerability Scan）     │
│   ↓                                                      │
│  DAST（SDD 強化）:                                       │
│    ├── 掃描範圍基於 Security Test Spec                   │
│    └── 自動對照 STRIDE 威脅清單                          │
│   ↓                                                      │
│  Compliance Check（SDD 新增）:                           │
│    └── 自動驗證合規對照矩陣項目                          │
│   ↓                                                      │
│  🔔 Notify: Enhanced（高風險安全問題即時通知）           │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 各階段詳細規格

### L0: DocLint + STRIDE-Validate（威脅模型完整性）

**觸發條件**：每次 PR / Merge

**驗證規則**：

```yaml
stride_validate_rules:
  stride_threat_model:
    required: true
    path: "docs/06_quality/security/STRIDE-THREAT-MODEL-*.md"
    checks:
      - "S/T/R/I/D/E 六類威脅均已分析（每類 ≥ 1 個威脅）"
      - "每個威脅有量化風險分數（可能性 × 影響）"
      - "每個威脅有緩解措施（無 N/A）"
      - "緩解後殘餘風險已評估"
      - "安全控制需求已提取（SC-* IDs）"

  sad_document:
    required: true
    path: "docs/06_quality/security/SAD-*.md"
    checks:
      - "認證機制規格存在（JWT/OAuth 2.0）"
      - "資料分類規格存在（Critical/High/Internal/Public）"
      - "加密規格存在（傳輸 + 靜態）"
      - "安全控制清單存在（SC-* 對應威脅）"

  security_test_spec:
    required: true
    path: "docs/03_testing/SECURITY-TEST-SPEC-*.md"
    checks:
      - "SAST 工具和規則集已定義"
      - "DAST 掃描範圍已定義（API 端點清單）"
      - "每個 High+ 威脅有對應 DAST 測試案例"
      - "Pass/Fail 標準量化（CVSS 閾值）"

fail_policy:
  - "STRIDE-THREAT-MODEL 不存在 → 阻擋 PR（SCG-5 Gate）"
  - "SAD 不存在 → 阻擋 PR（SCG-5 Gate）"
  - "任何 High+ 威脅無緩解措施 → 阻擋 PR"
  - "SECURITY-TEST-SPEC 不存在 → 阻擋 PR"
```

---

### L1: Unit Test + Security Unit Test

```yaml
security_unit_test_spec:
  standard_unit_tests: "繼承 SDD_TESTING_CICD.md 規格"
  
  security_specific_tests:
    - name: "認證邏輯單元測試"
      description: "JWT 驗證、Token 過期、簽名驗證"
      required: true
      
    - name: "授權邏輯單元測試"
      description: "RBAC 規則、資源擁有者驗證"
      required: true
      
    - name: "輸入驗證單元測試"
      description: "SQL Injection 防護、XSS 過濾、參數驗證"
      required: true
      
    - name: "加密邏輯單元測試"
      description: "加密/解密正確性、金鑰輪換"
      required: "when_applicable"

  gates:
    fail_when:
      - "認證/授權單元測試失敗"
      - "輸入驗證測試失敗"
```

---

### SAST（SDD 強化版）

```yaml
sast_spec:
  description: "規則集基於 SAD 安全控制規格"
  
  tools:
    primary:
      name: "{SonarQube/Semgrep/Checkmarx}"
      ruleset: "OWASP Top 10 + CWE Top 25"
      custom_rules: "基於 SAD 的 SC-* 安全控制"
      
  owasp_coverage:
    required_checks:
      - "A01 - 存取控制失效（對應 SC-004 RBAC）"
      - "A02 - 加密失效（對應 SC-005/SC-006）"
      - "A03 - 注入（對應 SC-003 Input Validation）"
      - "A04 - 不安全設計（STRIDE 審查）"
      - "A05 - 安全配置錯誤（對應 SC-* 配置控制）"
      - "A06 - 易受攻擊元件（SCA 掃描）"
      - "A07 - 身份驗證失效（對應 SC-001）"
      - "A08 - 軟體完整性失效（SCA + Pipeline 審查）"
      - "A09 - 日誌失效（對應 SC-007）"
      - "A10 - SSRF（端點輸入驗證）"
      
  sca_dependency_scan:
    tool: "{Snyk/Dependabot/npm audit}"
    trigger: "每次 PR + 每日定期掃描"
    
  secret_scan:
    tool: "{TruffleHog/GitGuardian}"
    trigger: "每次 Commit"
    
  gates:
    fail_when:
      - "Critical 漏洞 > 0（CVSS ≥ 9.0）"
      - "High 漏洞 > 0（CVSS ≥ 7.0，Security 相關）"
      - "任何 Hard-coded Secret 發現"
    warn_when:
      - "Medium 漏洞（CVSS 4.0-6.9）→ 記錄 Tech Debt，1 個月修復"
```

---

### Container: 容器安全掃描

```yaml
container_security_spec:
  tools:
    - "{Trivy/Clair/Snyk Container}"
    
  scan_targets:
    - "所有 Docker Image（包含 Base Image）"
    - "Dockerfile 最佳實踐（以非 root 用戶執行）"
    - "IaC 文件（Checkov/tfsec）"
    
  gates:
    fail_when:
      - "Base Image 有 Critical CVE"
      - "Container 以 root 執行（無明確豁免）"
      - "IaC 掃描發現 Critical 安全配置問題"
    warn_when:
      - "High CVE（30 天修復 SLA）"
```

---

### DAST（SDD 強化版）

```yaml
dast_spec:
  description: "掃描範圍基於 Security Test Spec，自動對照 STRIDE 威脅清單"
  trigger: "每次發布前（Staging 環境）"
  environment: "Staging"
  tool: "OWASP ZAP（自動模式）"
  
  scan_scope:
    based_on: "docs/03_testing/SECURITY-TEST-SPEC-*.md 的 DAST 掃描範圍表"
    
  stride_threat_coverage:
    spoofing:
      tests:
        - "STS-DAST-001: JWT Token 偽造攻擊（HTTP 401 驗證）"
        - "STS-DAST-002: 帳號枚舉攻擊（統一錯誤回應）"
        
    tampering:
      tests:
        - "STS-DAST-003: SQL Injection（所有 POST/PUT 端點）"
        - "STS-DAST-004: XSS 反射型（輸出 HTML 端點）"
        
    elevation_of_privilege:
      tests:
        - "STS-DAST-005: IDOR 水平越權（帶 ID 端點）"
        - "STS-DAST-006: 垂直越權（Admin API）"
        
    information_disclosure:
      tests:
        - "STS-DAST-007: 安全標頭驗證（所有端點 Response）"
        - "STS-DAST-008: 敏感資料暴露（錯誤回應）"
        
    denial_of_service:
      tests:
        - "STS-DAST-009: Rate Limit 驗證（/auth/login, /api/*）"
        
  gates:
    fail_when:
      - "Critical/High 漏洞（CVSS ≥ 7.0）"
      - "認證/授權繞過測試失敗"
      - "OWASP Top 10 關鍵測試失敗"
    warn_when:
      - "Medium 漏洞（CVSS 4.0-6.9）→ 1 個月修復 SLA"
```

---

### Compliance Check（SDD 新增）

```yaml
compliance_check_spec:
  description: "自動驗證合規對照矩陣可自動化驗證的項目"
  based_on: "docs/06_quality/security/COMPLIANCE-MATRIX-*.md"
  
  automated_checks:
    gdpr:
      - check: "TLS 強制（Art.32 加密要求）"
        method: "SSL Labs API 評級驗證（≥ A）"
      - check: "安全標頭完整性（Art.32）"
        method: "DAST 安全標頭掃描結果"
        
    pci_dss:
      - check: "依賴漏洞掃描（Req.6）"
        method: "SCA 掃描報告（無 Critical CVE）"
      - check: "SAST 執行記錄（Req.6）"
        method: "SAST 掃描通過記錄"
        
    iso_27001:
      - check: "Secret 掃描（A.8.12 資料洩漏防護）"
        method: "Secret Scan 掃描記錄"
      - check: "Container 安全（A.8.9 配置管理）"
        method: "Container Scan 報告"
        
  compliance_report:
    output: "build/reports/Compliance-{date}.md"
    format:
      - "自動化控制項達標率"
      - "需人工審查的控制項清單"
      - "未通過項目清單"
      
  gates:
    fail_when:
      - "PCI-DSS 關鍵控制項自動驗證失敗"
      - "TLS 配置不符合 A+ 要求"
    warn_when:
      - "GDPR 可自動化項目有未通過"
```

---

### 🔔 Notify: Enhanced（高風險安全問題即時通知）

```yaml
enhanced_notifications:
  on_critical_security:
    channel: "Slack #security-incidents"
    message: |
      🔴 [SECURITY CRITICAL] Pipeline 發現高風險安全問題！
      類型: {vuln_type}（CVSS: {cvss_score}）
      版本: {version} / Branch: {branch}
      詳情: {report_url}
    notify_users:
      - "@security-engineer"
      - "@dev-lead"
      - "@cto"
    pagerduty: true  # P0 級別觸發 PagerDuty
    
  on_sast_high:
    channel: "Slack #security-alerts"
    message: |
      ⚠️ SAST 發現 High 漏洞（部署已阻擋）
      漏洞: {vuln_name}（{cwe_id}）
      版本: {version}
      詳情: {report_url}
    notify_users:
      - "@security-engineer"
      - "@developer"
      
  on_secret_detected:
    channel: "Slack #security-alerts"
    message: |
      🚨 偵測到 Secret 洩漏！
      請立即輪換相關憑證！
      Commit: {commit_hash}
      詳情: {report_url}
    priority: "IMMEDIATE"
    notify_users:
      - "@security-engineer"
      - "@devops-lead"
      
  on_success:
    channel: "Slack #security"
    message: |
      ✅ {version} 安全掃描通過
      SAST: 通過 | Container: 通過 | DAST: 通過 | Compliance: {compliance_rate}%
```

---

## 📊 Security Scan Report 格式規格

```markdown
# Security Pipeline Report — {version} — {date}

## 掃描摘要
| 掃描類型 | 工具 | 發現 Critical | 發現 High | 狀態 |
|---------|------|-------------|---------|------|
| SAST | {tool} | 0 | 0 | ✅/❌ |
| SCA | {tool} | 0 | 0 | ✅/❌ |
| Secret Scan | {tool} | 0 | N/A | ✅/❌ |
| Container | {tool} | 0 | 0 | ✅/❌ |
| DAST | OWASP ZAP | 0 | 0 | ✅/❌ |
| Compliance | — | N/A | N/A | {rate}% |

## STRIDE 威脅覆蓋率
| STRIDE 類別 | 測試案例數 | 通過 | 失敗 |

## 合規自動化結果
| 法規 | 自動化覆蓋率 | 達標項目 | 未達標 |

## 部署決策
□ 通過 / □ 阻擋（原因：___）
```

---

## 🔗 相關文件

| 文件 | 路徑 |
|------|------|
| STRIDE 威脅模型模板 | `docs_template/sdd/testing/STRIDE-THREAT-MODEL-TEMPLATE.md` |
| SAD 模板 | `docs_template/sdd/architecture/SAD-TEMPLATE.md` |
| Security Test Spec 模板 | `docs_template/sdd/testing/SECURITY-TEST-SPEC-TEMPLATE.md` |
| Compliance Matrix 模板 | `docs_template/sdd/testing/COMPLIANCE-MATRIX-TEMPLATE.md` |
| Security Monitoring Spec 模板 | `docs_template/sdd/deployment/SECURITY-MONITORING-SPEC-TEMPLATE.md` |
| Incident Response Spec 模板 | `docs_template/sdd/deployment/INCIDENT-RESPONSE-SPEC-TEMPLATE.md` |
| SDD CI/CD 基礎層 | `cicd/SDD_CICD_BASE_LAYER.md` |

---

> **SDD 原則**: 安全不是 Pipeline 最後一步的「安全掃描」，而是從 STRIDE 威脅模型到 SAD 到 Security Test Spec 的完整規格鏈，Pipeline 僅是規格的自動化驗收工具。每個安全控制（SC-*）都必須在 Pipeline 中有對應的驗證步驟。
