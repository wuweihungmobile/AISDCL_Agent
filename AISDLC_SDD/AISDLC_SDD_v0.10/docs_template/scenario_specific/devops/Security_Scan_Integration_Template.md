# Security 掃描整合至所有情境配置範本

> **🔴 P1 安全整合**
>
> 此範本定義如何將**增強安全掃描 (SAST / Container Scan / DAST)** 整合至所有 AISDLC 情境。
> Layer 0 提供基礎安全基線（Secret + SCA + License），本範本在此基礎上為各情境添加適切的深度掃描。
>
> - **基礎**: Layer 0 — 所有情境強制（已由 P0 完成）
> - **增強**: SAST / Container Scan / DAST — 依情境風險等級選配或強制
> - **目標**: 將安全從獨立的 `security` 情境，擴展為貫穿所有情境的防護網

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Security Integration
**相關文檔**:
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 基礎安全基線
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 建置驗證
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準關卡
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [Security SOP](../../../scenarios/security/SOP.md) - Security 情境完整 SOP

---

## 📋 目錄

1. [安全掃描層級模型](#安全掃描層級模型)
2. [三大增強掃描工具](#三大增強掃描工具)
3. [情境安全矩陣](#情境安全矩陣)
4. [SAST 靜態應用安全測試](#sast-靜態應用安全測試)
5. [Container Scan 容器映像掃描](#container-scan-容器映像掃描)
6. [DAST 動態應用安全測試](#dast-動態應用安全測試)
7. [整合策略與執行時機](#整合策略與執行時機)
8. [阻塞策略與例外處理](#阻塞策略與例外處理)
9. [維護與更新](#維護與更新)

---

## 安全掃描層級模型

### 三層安全防護

```
Layer 0: Security Baseline（所有情境強制）
├── Secret Detection       — 機密洩漏防護
├── Dependency Scan (SCA)  — 已知漏洞掃描
└── License Compliance     — 授權合規

    ↓ P1 Security Integration（本範本）

Enhanced Security Scans（依情境風險等級）
├── SAST                   — 程式碼漏洞靜態分析
├── Container Scan         — Docker 映像漏洞掃描
└── DAST                   — 運行時安全動態測試
```

### 安全等級定義

| 等級 | 名稱 | 包含內容 | 適用情境 |
|------|------|---------|---------|
| **Basic** | 基礎安全 | Layer 0 (Secret + SCA + License) | documentation |
| **Standard** | 標準安全 | Basic + SAST | greenfield, brownfield, refactoring, testing |
| **Advanced** | 進階安全 | Standard + Container Scan | migration, integration, performance, devops |
| **Enhanced** | 增強安全 | Advanced + DAST + Compliance Gate | security |

---

## 三大增強掃描工具

### 工具選型總覽

| 掃描類型 | 推薦工具（免費） | 商業替代 | 掃描時間 |
|---------|----------------|---------|---------|
| **SAST** | Semgrep / CodeQL | Checkmarx, SonarQube Enterprise | 2-10 分鐘 |
| **Container Scan** | Trivy / Grype | Snyk Container, Prisma Cloud | 1-5 分鐘 |
| **DAST** | OWASP ZAP (Baseline) | Burp Suite Enterprise, Invicti | 10-60 分鐘 |

### 各語言 SAST 工具

| 語言 | Semgrep 規則集 | CodeQL | 其他 |
|------|---------------|--------|------|
| **JavaScript/TypeScript** | `p/javascript` | `javascript-security-and-quality` | ESLint security plugin |
| **Python** | `p/python` | `python-security-and-quality` | Bandit |
| **Java** | `p/java` | `java-security-and-quality` | SpotBugs + Find-Sec-Bugs |
| **Go** | `p/golang` | `go-security-and-quality` | gosec |
| **Kotlin** | `p/kotlin` | N/A | detekt security |
| **Rust** | `p/rust` | N/A | cargo-audit |
| **C#/.NET** | `p/csharp` | `csharp-security-and-quality` | Security Code Scan |

---

## 情境安全矩陣

### 各情境安全掃描要求

| 情境 | L0 基礎 | SAST | Container | DAST | 安全等級 | 說明 |
|------|:---:|:---:|:---:|:---:|:---:|------|
| `greenfield` | 🔴 強制 | 🔴 強制 | ⚠️ 有 Docker 時 | ❌ | Standard | 新專案從一開始就建立安全基線 |
| `brownfield` | 🔴 強制 | 🔴 強制 | ⚠️ 有 Docker 時 | ❌ | Standard | 聚焦新增/修改代碼的 SAST |
| `refactoring` | 🔴 強制 | 🔴 強制 | ❌ | ❌ | Standard | 確保重構不引入安全漏洞 |
| `migration` | 🔴 強制 | 🔴 強制 | 🔴 有 Docker 時 | ⚠️ 選配 | Advanced | 新舊棧都要掃描 |
| `performance` | 🔴 強制 | ⚠️ 選配 | ⚠️ 有 Docker 時 | ❌ | Advanced | 效能工具自身安全性 |
| `integration` | 🔴 強制 | 🔴 強制 | ⚠️ 有 Docker 時 | ⚠️ 選配 | Advanced | 第三方 API 安全驗證 |
| `devops` | 🔴 強制 | ⚠️ IaC SAST | 🔴 強制 | ❌ | Advanced | IaC 掃描 + 容器安全 |
| `testing` | 🔴 強制 | 🔴 強制 | ❌ | ❌ | Standard | 測試代碼品質安全 |
| `documentation` | 🔴 強制 | ❌ | ❌ | ❌ | Basic | 僅需基礎 L0 |
| `security` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 🔴 強制 | **Enhanced** | 全套安全掃描 + Compliance Gate |

> **圖例**: 🔴 強制 = 必須通過才能合併 | ⚠️ 選配/條件 = 建議啟用或特定條件下啟用 | ❌ 不適用

---

## SAST 靜態應用安全測試

### 目的
在編譯前分析源碼，發現 SQL Injection、XSS、Path Traversal 等漏洞。

### Semgrep 配置（推薦）

```yaml
sast_config:
  tool: semgrep
  rules:
    - "p/owasp-top-ten"        # OWASP Top 10 規則
    - "p/security-audit"        # 安全審計規則
    # 語言專屬規則（依專案選擇）:
    # - "p/javascript"
    # - "p/python"
    # - "p/java"
  severity_blocking: [ERROR]    # ERROR 阻塞，WARNING 僅警告
  timeout: 600s                 # 10 分鐘超時
  exclude:
    - "tests/**"                # 排除測試目錄
    - "**/*.test.*"
    - "node_modules/**"
    - "vendor/**"
```

### CodeQL 配置（GitHub 原生）

```yaml
# .github/codeql/codeql-config.yml
name: "AISDLC Security Scan"
queries:
  - uses: security-and-quality
paths-ignore:
  - tests
  - "**/*.test.*"
```

### SAST 阻塞策略

| 嚴重度 | 處理方式 | 說明 |
|--------|---------|------|
| **Critical** | 🔴 阻塞 PR | 必須立即修復 |
| **High** | 🔴 阻塞 PR | 必須修復後才能合併 |
| **Medium** | ⚠️ 警告 | 記錄為技術債，限期修復 |
| **Low/Info** | 📝 記錄 | 下次迭代處理 |

---

## Container Scan 容器映像掃描

### 目的
掃描 Docker Image 中的 OS 套件漏洞和應用依賴漏洞。

### Trivy 配置（推薦）

```yaml
container_scan:
  tool: trivy
  scan_target: "image"
  severity: "CRITICAL,HIGH"     # 掃描嚴重度
  exit_code: 1                  # 發現漏洞時失敗
  ignore_unfixed: true          # 忽略尚無修復的漏洞
  timeout: 300s
  format: "sarif"               # SARIF 格式上傳至 GitHub
```

### 觸發條件

```yaml
container_scan_triggers:
  # 僅在以下情況觸發：
  - file_changed: "Dockerfile"
  - file_changed: "docker-compose*.yml"
  - file_changed: ".dockerignore"
  - schedule: "weekly"          # 每週掃描一次（抓新發現的 CVE）
```

---

## DAST 動態應用安全測試

### 目的
對運行中的應用進行安全測試，發現 Runtime 漏洞。

### OWASP ZAP 配置

```yaml
dast_config:
  tool: owasp-zap
  mode: "baseline"              # baseline（快速）/ full-scan（完整）
  target: "$STAGING_URL"        # 掃描目標 URL
  timeout: 1800s                # 30 分鐘超時
  rules_to_ignore:
    - 10096                     # Timestamp Disclosure
    - 10027                     # Information Disclosure - Suspicious Comments
  alert_threshold: "Medium"     # Medium 以上告警
```

### 執行時機

| 時機 | 掃描模式 | 耗時 | 適用 |
|------|---------|------|------|
| **PR 階段** | Baseline Scan | 5-10 分鐘 | security 情境 |
| **Staging 部署後** | Full Scan | 30-60 分鐘 | security + migration |
| **Nightly** | Full Scan | 30-60 分鐘 | 所有有部署的情境 |

---

## 整合策略與執行時機

### Pipeline 整合位置

```
Layer 0: Security Baseline ✅
Layer 1: Build & Verify ✅
    ↓
┌─────────────────────────────────────┐
│  Security Integration (本範本)       │
│  ├── SAST (Lint 之後、Deploy 之前)  │
│  ├── Container Scan (Build 之後)    │
│  └── DAST (Deploy to Staging 之後)  │
└─────────────────────────────────────┘
    ↓
Layer 2/3: QA + Deploy
```

### 執行順序

```yaml
security_integration:
  # PR 階段（同步執行）
  pr_level:
    parallel:
      - sast_scan              # 與 Build 平行
      - container_scan         # Build 完成後
    blocking: true             # 失敗阻塞 PR

  # Staging 階段
  staging_level:
    sequential:
      - deploy_staging
      - dast_baseline_scan     # 部署後掃描
    blocking: false            # 僅警告（DAST 誤報率高）

  # Nightly 排程
  nightly_level:
    - dast_full_scan
    - container_scan_all_images
    blocking: false            # 結果次日處理
```

### 超時設定

| 掃描 | PR 階段 | Nightly | 超時後處理 |
|------|---------|---------|-----------|
| **SAST** | 10 分鐘 | 30 分鐘 | ⚠️ 降級為警告 |
| **Container** | 5 分鐘 | 10 分鐘 | ⚠️ 降級為警告 |
| **DAST** | N/A | 60 分鐘 | ⚠️ 降級為警告 |

---

## 阻塞策略與例外處理

### 統一阻塞策略

```yaml
security_blocking_policy:
  # 所有情境統一
  sast:
    block_on: [critical, high]
    warn_on: [medium, low]
  container:
    block_on: [critical, high]
    warn_on: [medium]
    ignore_unfixed: true
  dast:
    block_on: [high]            # DAST 僅 High 阻塞（誤報率考量）
    warn_on: [medium, low]

  # Hotfix 旁路
  bypass:
    branches: ["hotfix/*"]
    requires: "security-engineer post-merge review"
    never_skip: ["secret-detection"]  # Secret 永不跳過
```

### 例外處理機制

```yaml
# .security-ignore.yml（專案根目錄）
exceptions:
  - rule: "javascript.lang.security.audit.xss"
    file: "legacy/old-module.js"
    reason: "Legacy code, scheduled for removal in Sprint 12"
    expires: "2026-06-30"
    approved_by: "security-engineer"
```

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| SAST 規則集 | 每月（或 CVE 發布時） | Security-Engineer |
| Container 基礎映像 | 每月 | DevOps-Engineer |
| DAST 掃描規則 | 每季 | Security-Engineer |
| 例外清單審查 | 每季 | Security-Engineer + Tech Lead |
| 安全等級矩陣 | 每半年 | SD-Architect + Security-Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立情境安全矩陣 + SAST/Container/DAST 配置 |
