# Layer 0: Security Baseline 安全基線配置範本

> **🔴 強制要求**
>
> Layer 0 是**所有情境、所有 PR 的強制安全基線**，無論專案使用哪個 Workflow 情境，
> 都必須在 CI/CD Pipeline 的最前端執行 Layer 0 檢查。
>
> - **適用範圍**: 所有 11 個 AISDLC 情境（greenfield ~ security）
> - **執行時機**: 每次 PR / Push / Pre-commit
> - **阻塞等級**: Critical/High 漏洞阻塞合併，Medium/Low 僅警告
> - **執行角色**: 自動化（CI Pipeline）+ DevOps Engineer（配置維護）

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Security Baseline
**相關文檔**:
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 建置驗證
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 增強安全掃描（SAST/Container/DAST）
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [Security_Test_Plan_Template.md](../../core/tests/Security_Test_Plan_Template.md) - 安全測試計畫
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準關卡
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [CICD_STRATEGIC_RESTRUCTURE_PLAN.md](../../../build/planning/archive/CICD_STRATEGIC_RESTRUCTURE_PLAN.md) - 戰略重構計畫

---

## 📋 目錄

1. [Layer 0 概覽](#layer-0-概覽)
2. [三大安全支柱](#三大安全支柱)
3. [Pre-commit Hook 配置](#pre-commit-hook-配置)
4. [CI Pipeline 安全階段](#ci-pipeline-安全階段)
5. [阻塞策略與熔斷機制](#阻塞策略與熔斷機制)
6. [情境適配規則](#情境適配規則)
7. [工具選型指引](#工具選型指引)
8. [維護與更新](#維護與更新)

---

## Layer 0 概覽

### 定位

```
所有 CI/CD Pipeline 的必經第一層：

  Code Push / PR Open
        ↓
  ┌─────────────────────────────────┐
  │  Layer 0: Security Baseline     │  ← 強制、不可跳過
  │  ├── Secret Detection           │
  │  ├── Dependency Scan (SCA)      │
  │  └── License Compliance         │
  └─────────────────────────────────┘
        ↓ (全部通過)
  Layer 1: Build & Verify
        ↓
  Layer 2: Quality Assurance
        ↓
  Layer 3: Deploy & Validate
```

### 設計原則

| 原則 | 說明 |
|------|------|
| **Shift-Left** | 安全檢查前移至開發階段，越早發現成本越低 |
| **Fail-Fast** | Critical 漏洞立即阻塞，不等後續階段 |
| **分級阻塞** | 依嚴重度決定阻塞/警告，避免過度干擾開發 |
| **超時熔斷** | 掃描超時視為 Warning，避免 Pipeline 死結 |

---

## 三大安全支柱

### 支柱 1: Secret Detection（機密偵測）

**目的**: 防止 API Key、密碼、Token 等機密資訊洩漏至版本控制。

**執行層級**:
- **Pre-commit Hook**（本地攔截，推薦）
- **CI Pipeline**（遠端防線，強制）

**偵測範圍**:

| 類型 | 範例 | 嚴重度 |
|------|------|--------|
| API Keys | `AKIAIOSFODNN7EXAMPLE` | CRITICAL |
| Private Keys | `-----BEGIN RSA PRIVATE KEY-----` | CRITICAL |
| Database URLs | `postgresql://user:pass@host/db` | HIGH |
| JWT Secrets | `eyJhbGciOiJIUzI1NiJ9...` | HIGH |
| Cloud Credentials | AWS_SECRET_ACCESS_KEY, GCP_SA_KEY | CRITICAL |
| Generic Passwords | `password = "hardcoded"` | MEDIUM |

**推薦工具**:

| 工具 | 適用場景 | 成本 |
|------|---------|------|
| **TruffleHog** | 通用 Secret 偵測（推薦首選） | 免費 |
| **GitGuardian** | 企業級 + SaaS 儀表板 | 免費/付費 |
| **detect-secrets** | Python 生態系 | 免費 |
| **gitleaks** | 輕量 Go 實作 | 免費 |

### 支柱 2: Dependency Scan / SCA（軟體組成分析）

**目的**: 掃描專案依賴是否包含已知漏洞 (CVE)。

**掃描對象**:

| 生態系 | 檔案 | 工具 |
|--------|------|------|
| Node.js | `package-lock.json` | npm audit, Snyk |
| Python | `requirements.txt`, `Pipfile.lock` | pip-audit, Safety |
| Java | `pom.xml`, `build.gradle` | OWASP Dependency-Check |
| Go | `go.sum` | govulncheck |
| .NET | `packages.lock.json` | dotnet list package --vulnerable |
| Ruby | `Gemfile.lock` | bundler-audit |
| Rust | `Cargo.lock` | cargo-audit |

**推薦工具**:

| 工具 | 適用場景 | 成本 |
|------|---------|------|
| **Snyk** | 多語言、自動修復 PR（推薦首選） | 免費/付費 |
| **Dependabot** | GitHub 原生整合 | 免費 |
| **OWASP Dependency-Check** | Java/企業場景 | 免費 |
| **Trivy** | 容器 + 依賴多合一 | 免費 |
| **npm audit** | Node.js 內建 | 免費 |

**漏洞嚴重度與處理策略**:

| CVSS 分數 | 嚴重度 | 處理 | 時限 |
|-----------|--------|------|------|
| 9.0-10.0 | CRITICAL | 🔴 阻塞 PR + 立即修復 | 24 小時 |
| 7.0-8.9 | HIGH | 🔴 阻塞 PR | 7 天 |
| 4.0-6.9 | MEDIUM | ⚠️ 警告 | 30 天 |
| 0.1-3.9 | LOW | ℹ️ 記錄 | 下次迭代 |

### 支柱 3: License Compliance（授權合規）

**目的**: 確保依賴的開源授權與專案授權相容，避免法律風險。

**授權分級**:

| 類別 | 授權 | 風險 |
|------|------|------|
| **Permissive（寬鬆）** | MIT, Apache-2.0, BSD | ✅ 低風險 |
| **Weak Copyleft** | LGPL-2.1, MPL-2.0 | ⚠️ 需注意 |
| **Strong Copyleft** | GPL-2.0, GPL-3.0, AGPL-3.0 | 🔴 需審核 |
| **Unknown/Custom** | 未知或自訂授權 | 🔴 需審核 |

**推薦工具**:

| 工具 | 適用場景 | 成本 |
|------|---------|------|
| **license-checker** | Node.js 專案 | 免費 |
| **FOSSA** | 企業級授權合規 | 付費 |
| **Snyk** | 含授權檢查功能 | 免費/付費 |
| **ScanCode** | 深度授權掃描 | 免費 |

---

## Pre-commit Hook 配置

### 配置範本

**檔案位置**: `.pre-commit-config.yaml`（專案根目錄）

```yaml
# Layer 0 Security Baseline - Pre-commit Configuration
# AISDLC-SDD v0.01 標準配置

repos:
  # ─── Secret Detection ───
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.82.13  # 請更新至最新版
    hooks:
      - id: trufflehog
        name: TruffleHog Secret Scan
        entry: trufflehog git file://. --since-commit HEAD --only-verified --fail
        language: golang
        stages: [pre-commit]

  # ─── 備選: gitleaks ───
  # - repo: https://github.com/gitleaks/gitleaks
  #   rev: v8.21.2
  #   hooks:
  #     - id: gitleaks
  #       name: Gitleaks Secret Scan

  # ─── Lint & Format（Layer 0 附加） ───
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key
        name: Detect Private Keys
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

### 安裝與啟用

```bash
# 安裝 pre-commit
pip install pre-commit

# 安裝 hooks（依據 .pre-commit-config.yaml）
pre-commit install

# 手動執行所有 hooks（驗證用）
pre-commit run --all-files
```

---

## CI Pipeline 安全階段

### GitHub Actions 配置

**檔案位置**: `.github/workflows/security-baseline.yml`

參考 [security-baseline.yml](./github-actions/security-baseline.yml) 完整範本。

**核心 Jobs**:

```yaml
jobs:
  secret-scan:        # TruffleHog / Gitleaks
  dependency-scan:    # Snyk / npm audit / pip-audit
  license-check:      # license-checker / FOSSA
```

### GitLab CI 配置

**檔案位置**: `.gitlab-ci.yml`（引入 security-baseline template）

參考 [security-baseline-template.yml](./gitlab-ci/security-baseline-template.yml) 完整範本。

---

## 阻塞策略與熔斷機制

### 分級阻塞規則

```yaml
# Layer 0 阻塞策略配置
security_policy:
  secret_detection:
    blocking: true                    # 永遠阻塞，無例外
    severity_threshold: any           # 任何 Secret 都阻塞

  dependency_scan:
    blocking_severity: [critical, high]
    warning_severity: [medium, low]
    auto_fix_pr: true                 # 自動建立修復 PR（Snyk/Dependabot）

  license_compliance:
    blocked_licenses: [GPL-3.0, AGPL-3.0]
    review_required: [GPL-2.0, LGPL-2.1]
    allowed_licenses: [MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC]
```

### 超時熔斷機制

```yaml
# 防止 Pipeline 死結
timeout_policy:
  secret_scan:
    timeout: 300s         # 5 分鐘
    on_timeout: block     # Secret 超時仍阻塞（安全優先）

  dependency_scan:
    timeout: 600s         # 10 分鐘
    on_timeout: warn      # 超時降級為警告

  license_check:
    timeout: 300s         # 5 分鐘
    on_timeout: warn      # 超時降級為警告
```

### Hotfix 旁路機制

```yaml
# 緊急修復旁路（需事後審核）
bypass_policy:
  enabled_branches: ["hotfix/*"]
  bypass_checks: [dependency_scan, license_check]
  never_bypass: [secret_detection]    # Secret 檢測永遠不可跳過
  post_merge_audit: required          # 合併後強制補充審核
  audit_assignee: security-engineer   # 事後審核負責人
```

---

## 情境適配規則

### 各情境 Layer 0 強制等級

| 情境 | Secret Detection | SCA | License | 附加要求 |
|------|:---:|:---:|:---:|---------|
| `greenfield` | 🔴 強制 | 🔴 強制 | 🔴 強制 | - |
| `brownfield` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 既有依賴全量掃描 |
| `refactoring` | 🔴 強制 | 🔴 強制 | 🔴 強制 | - |
| `migration` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 新舊棧依賴同時掃描 |
| `performance` | 🔴 強制 | 🔴 強制 | ⚠️ 選配 | Benchmark 工具授權確認 |
| `integration` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 第三方 SDK 授權審查 |
| `devops` | 🔴 強制 | 🔴 強制 | 🔴 強制 | IaC 掃描 (Checkov) |
| `testing` | 🔴 強制 | 🔴 強制 | ⚠️ 選配 | 測試框架授權確認 |
| `documentation` | 🔴 強制 | ⚠️ 選配 | ⚠️ 選配 | 文檔工具鏈安全 |
| `security` | 🔴 強制 | 🔴 強制 | 🔴 強制 | **Enhanced**: + SAST + Container Scan |

> **🛡️ 進階安全掃描**: Layer 0 提供基礎安全基線。依情境風險等級，可在此基礎上添加 SAST / Container Scan / DAST 增強掃描。
> 詳見 → [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md)

---

## 工具選型指引

### 推薦組合（依專案規模）

**小型專案（1-5 人團隊）**:
```
Secret: gitleaks (pre-commit) + GitHub Secret Scanning
SCA:    npm audit / pip-audit + Dependabot
License: license-checker (Node.js)
```

**中型專案（5-20 人團隊）**:
```
Secret: TruffleHog (pre-commit + CI)
SCA:    Snyk (Free tier, 自動修復 PR)
License: Snyk License (含在 SCA 中)
```

**大型/企業專案**:
```
Secret: GitGuardian (SaaS 儀表板 + 歷史掃描)
SCA:    Snyk / Sonatype Nexus IQ
License: FOSSA (企業級合規報告)
```

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| Pre-commit Hook 版本 | 每月 | DevOps Engineer |
| 漏洞資料庫 | 自動（工具內建） | 自動化 |
| 授權白名單 | 每季審查 | Security Engineer + Legal |
| 阻塞策略閾值 | 每季審查 | Security Engineer |
| 工具版本升級 | 每季 | DevOps Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立三大安全支柱範本 |
