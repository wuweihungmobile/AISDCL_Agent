# Security & Compliance 情境 SOP
# Security & Compliance Scenario Standard Operating Procedure

**情境代碼**: `security`
**版本**: v0.01
**最後更新**: 2026-02-23
**適用範圍**: 需要安全性評估、安全加固、合規性檢查的專案

> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如安全評估報告、威脅模型、合規檢查清單等文檔路徑）為示例性質，
> 展示一般專案的安全文檔結構。實際使用時，請根據您的專案安全要求和文檔組織調整路徑。

---

## 📋 情境概述

### 什麼時候使用這個情境？

選擇 Security & Compliance 情境，如果你的專案符合以下任一情況：

- [ ] **高合規性行業**: 金融、醫療、政府、教育等受監管行業
- [ ] **處理敏感資料**: 個資、金融資料、健康資料、商業機密
- [ ] **需要安全認證**: ISO 27001、SOC 2、HIPAA、PCI-DSS、GDPR 等
- [ ] **安全漏洞修復**: 需要系統性修復已知安全漏洞
- [ ] **安全架構設計**: 新專案需要從頭建立安全架構
- [ ] **滲透測試後改善**: 根據滲透測試結果進行安全加固
- [ ] **第三方安全稽核**: 準備接受外部安全審查
- [ ] **資料隱私保護**: 需要實施資料加密、脫敏、存取控制

### 不適合使用這個情境的情況

- ❌ 只是一般性代碼 review（使用 Refactoring 情境）
- ❌ 純功能開發無安全要求（使用 Greenfield/Brownfield）
- ❌ 只需要基本的 input validation（不需要完整 SOP）

---

## 📋 Skills 整合對照表

> 下表列出 Security & Compliance 各階段建議搭配的 Claude Code Skills，確保每個步驟都能觸發正確的自動化輔助。

| Skill | 階段 1<br>安全評估 | 階段 2<br>架構設計 | 階段 3<br>實施修復 | 階段 4<br>測試驗證 | 階段 5<br>文檔交付 | 說明 |
|-------|:---:|:---:|:---:|:---:|:---:|------|
| `/security-audit` | ✅ | ✅ | | ✅ | | OWASP Top 10 安全審計 |
| `/compliance-audit` | ✅ | | | | ✅ | GDPR/PCI-DSS/SOC2 合規審查 |
| `/sd-architect` | | ✅ | | | | 安全架構設計（Zero Trust） |
| `/code-review` | | | ✅ | | | 安全程式碼審查 |
| `/integration-oauth` | | ✅ | ✅ | | | OAuth 2.0/OIDC 認證整合 |
| `/integration-database` | | ✅ | ✅ | | | 資料庫安全（加密、存取控制） |
| `/qa-testing` | | | | ✅ | | 安全測試策略與案例 |
| `/testing-strategy` | | | | ✅ | | 安全測試金字塔設計 |
| `/devops-github-actions` | | | ✅ | ✅ | | 安全 CI/CD Pipeline（SAST/DAST） |
| `/devops-docker` | | | ✅ | | | 容器安全（Golden Image/Trivy） |
| `/devops-monitoring` | | | | ✅ | | 安全事件監控與告警 |
| `/performance-optimization` | | | | ✅ | | 安全措施效能影響評估 |
| `/integration-redis` | | ✅ | ✅ | | | Session/Token 安全快取 |
| `/mobile-development` | ✅ | ✅ | ✅ | ✅ | | 行動端安全（Android/macOS） |
| `/integration-stripe` | ✅ | ✅ | ✅ | ✅ | | 支付安全（Stripe.js Tokenization、PCI-DSS 合規） |
| `/integration-webhook` | | ✅ | ✅ | ✅ | | Stripe Webhook 簽章驗證、防偽造支付回調 |

---

## 🔒 Layer 0: 全局安全基線（v0.01 CI/CD 強化）

> **🔴 重要**: Layer 0 Security Baseline 是**所有 AISDLC 情境的強制安全基線**，不僅限於 Security 情境。
> Security 情境在此基礎上提供 **Enhanced（增強版）** 安全掃描，包含額外的 SAST + Container Scan + DAST。

**Layer 0 基線（所有情境強制）**:
- Secret Detection（機密偵測）— Pre-commit + CI 雙層防護
- Dependency Scan / SCA（依賴漏洞掃描）— CRITICAL/HIGH 阻塞 PR
- License Compliance（授權合規）— GPL-3.0/AGPL 阻塞

**Security 情境增強項目**:
- SAST（靜態應用安全測試）— SonarQube / Semgrep / Checkmarx
- Container Scan（容器映像掃描）— Trivy / Clair
- DAST（動態應用安全測試）— OWASP ZAP / Burp Suite

📖 **Layer 0 配置指南**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)

---

## 🔨 Layer 1: Build & Verify（強制建置驗證）

> **🔴 v0.01 CI/CD 強化**: Layer 0 通過後，所有情境都必須通過 Layer 1 建置驗證。
> Security 情境的 Coverage 閾值為 **80%**，並建議搭配 Layer 0 Enhanced SAST 掃描。

**Layer 1 三道關卡**:
- Lint + Format Check — 程式碼風格一致性
- Compile / Build — 編譯成功、依賴正確
- Unit Test + Coverage Gate — 覆蓋率 ≥ 80%

📖 **Layer 1 配置指南**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
📄 **CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/build-verify.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/build-verify-template.yml)

---

## 🛡️ 增強安全掃描: SAST + Container + DAST + Compliance Gate（Enhanced 等級）

> **Security 情境安全等級: Enhanced** (L0 + L1 + SAST + Container Scan + DAST + Compliance Gate)
> Security 情境是唯一需要全套安全掃描的情境，所有掃描類型都是強制的。

| 掃描類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 | 程式碼漏洞靜態分析 |
| **Container Scan** | Trivy / Grype | 🔴 強制 | 所有映像漏洞掃描 |
| **DAST** | OWASP ZAP | 🔴 High 阻塞 | 運行時安全動態測試 |
| **Compliance Gate** | 自訂 | 🔴 強制 | 合規審查通過才能合併 |

**配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-scan-enhanced.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml)
**建置流程**: [devops-setup-flow.md 步驟 0.7](../../workflow/scenario-specific/devops-setup-flow.md) — Security Integration 增強安全掃描建置

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 商業安全工具價格高昂（Checkmarx $100k+/年, Burp Suite Pro $4k/年），以下提供功能相近的免費/開源替代方案。

### 安全工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **SAST (靜態分析)** | Checkmarx<br>Fortify<br>Veracode | **Semgrep**<br>**SonarQube Community**<br>**Bandit** (Python)<br>**Brakeman** (Ruby) | 核心功能相同<br>缺少: 企業級報告、優先級排序 | 代碼安全掃描<br>漏洞檢測 |
| **DAST (動態分析)** | Burp Suite Pro<br>Acunetix<br>Netsparker | **OWASP ZAP**<br>**Nikto**<br>**w3af** | 功能完整,免費<br>缺少: 自動化報告、整合度 | Web 應用掃描<br>滲透測試 |
| **SCA (依賴掃描)** | Snyk Pro<br>WhiteSource | **OWASP Dependency-Check**<br>**npm audit** (內建)<br>**pip-audit**<br>**Safety** | 開源版完全免費<br>CVE 資料庫相同 | 依賴套件漏洞<br>開源元件風險 |
| **Secret Scanning** | GitGuardian<br>GitHub Advanced Security | **GitLeaks**<br>**TruffleHog**<br>**detect-secrets** | 檢測能力相同<br>缺少: 雲端管理介面 | Git 歷史掃描<br>密鑰洩漏檢測 |
| **Container Security** | Aqua Security<br>Twistlock | **Trivy**<br>**Clair**<br>**Anchore** | 掃描精準度相同<br>缺少: Runtime 防護 | Docker 映像掃描<br>Kubernetes 安全 |
| **API Security** | Salt Security<br>42Crunch | **OWASP ZAP API Scan**<br>**Postman Security**<br>**Apisec.ai Free** | 基本功能免費<br>進階功能付費 | API 漏洞檢測<br>API Schema 驗證 |
| **Infrastructure Scan** | Nessus Pro<br>Qualys | **OpenVAS**<br>**Lynis**<br>**Nmap** | 功能齊全,免費<br>缺少: 商業支援 | 網路漏洞掃描<br>主機基線檢查 |
| **Compliance Check** | - | **InSpec**<br>**OpenSCAP**<br>**Docker Bench** | 開源方案免費<br>規則需自訂 | PCI-DSS, CIS Benchmark<br>合規性檢查 |

### 工具安裝與使用指南

#### 1. OWASP ZAP（Web 應用安全掃描）

**安裝**:
```bash
# Docker 方式（推薦）
docker pull zaproxy/zap-stable

# macOS
brew install --cask owasp-zap

# Linux
wget https://github.com/zaproxy/zaproxy/releases/download/v2.14.0/ZAP_2.14.0_Linux.tar.gz
tar -xvf ZAP_2.14.0_Linux.tar.gz
```

**基本掃描**:
```bash
# 基線掃描（快速,低誤報）
docker run -t zaproxy/zap-stable zap-baseline.py \
  -t https://your-app.com \
  -r zap-baseline-report.html

# 完整掃描（深入,可能有誤報）
docker run -t zaproxy/zap-stable zap-full-scan.py \
  -t https://your-app.com \
  -r zap-full-report.html

# API 掃描（需提供 OpenAPI/Swagger 檔案）
docker run -v $(pwd):/zap/wrk/:rw -t zaproxy/zap-stable \
  zap-api-scan.py -t https://your-api.com/openapi.json \
  -f openapi -r api-scan-report.html
```

**CI/CD 整合**:
```yaml
# .github/workflows/security-scan.yml
name: OWASP ZAP Scan
on: [push, pull_request]

jobs:
  zap_scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://staging.example.com'
          rules_file_name: '.zap/rules.tsv'
          fail_action: true  # 發現高風險漏洞時失敗

      - name: Upload ZAP Report
        uses: actions/upload-artifact@v3
        with:
          name: zap-scan-report
          path: report_html.html
```

#### 2. Semgrep（靜態代碼分析）

**安裝**:
```bash
# Python
pip install semgrep

# Homebrew
brew install semgrep

# Docker
docker pull returntocorp/semgrep
```

**使用**:
```bash
# 使用預設規則掃描（OWASP Top 10）
semgrep --config=auto .

# 使用特定規則集
semgrep --config=p/security-audit .
semgrep --config=p/owasp-top-ten .
semgrep --config=p/cwe-top-25 .

# 自訂規則
semgrep --config=.semgrep/rules/ .

# 輸出 SARIF 格式（供 GitHub Security 使用）
semgrep --config=auto --sarif -o semgrep-results.sarif .
```

**自訂規則範例**:
```yaml
# .semgrep/rules/hardcoded-secrets.yml
rules:
  - id: hardcoded-password
    pattern: |
      password = "..."
    message: "Hardcoded password detected"
    severity: ERROR
    languages: [python, javascript, java]

  - id: hardcoded-api-key
    pattern-either:
      - pattern: api_key = "..."
      - pattern: apiKey = "..."
      - pattern: API_KEY = "..."
    message: "Hardcoded API key detected"
    severity: ERROR
    languages: [python, javascript, java]
```

**📋 Semgrep 自訂規則撰寫指引** 🆕 (v0.01 擴展)

**規則結構說明**：

| 欄位 | 說明 | 必要性 |
|-----|------|--------|
| `id` | 規則唯一識別碼 | 🔴 必要 |
| `pattern` | 匹配模式 | 🔴 必要 |
| `message` | 告警訊息 | 🔴 必要 |
| `severity` | 嚴重等級 (INFO/WARNING/ERROR) | 🔴 必要 |
| `languages` | 適用語言 | 🔴 必要 |
| `metadata` | 額外資訊 (CWE, 修復建議) | ⚠️ 建議 |
| `fix` | 自動修復建議 | 選用 |

**進階匹配模式**：

```yaml
# 1. pattern-either: OR 邏輯（任一匹配）
- id: unsafe-eval
  pattern-either:
    - pattern: eval($X)
    - pattern: new Function($X)
  message: "避免使用動態代碼執行"

# 2. pattern-inside: 限定上下文
- id: sql-injection-in-handler
  pattern: |
    $DB.query($X)
  pattern-inside: |
    function $HANDLER(req, res) {
      ...
    }
  message: "Handler 內直接使用 DB query，可能有 SQL Injection"

# 3. pattern-not: 排除誤報
- id: hardcoded-secret-not-test
  pattern: password = "..."
  pattern-not-inside: |
    describe(..., function() { ... })
  message: "非測試代碼中的硬編碼密碼"

# 4. metavariable-regex: 正則匹配變數
- id: weak-crypto
  pattern: crypto.createHash($ALGO)
  metavariable-regex:
    metavariable: $ALGO
    regex: '(md5|sha1)'
  message: "使用弱雜湊演算法"
```

**常用規則模板**：

| 檢查項目 | 模式範例 | 風險等級 |
|---------|---------|---------|
| **SQL Injection** | `$DB.query("..." + $USER_INPUT)` | 🔴 ERROR |
| **XSS** | `innerHTML = $USER_INPUT` | 🔴 ERROR |
| **敏感日誌** | `console.log(..., password, ...)` | ⚠️ WARNING |
| **不安全反序列化** | `JSON.parse($UNTRUSTED)` | ⚠️ WARNING |
| **弱密碼學** | `crypto.createHash("md5")` | 🔴 ERROR |

**測試自訂規則**：
```bash
# 建立測試檔案
# test/semgrep-test.js
// ruleid: hardcoded-password
const password = "secret123";

// ok: hardcoded-password (使用環境變數)
const password = process.env.PASSWORD;

# 執行規則測試
semgrep --test .semgrep/rules/
```

**規則管理最佳實踐**：
```
.semgrep/
├── rules/
│   ├── security/           # 安全規則
│   │   ├── injection.yml
│   │   ├── auth.yml
│   │   └── crypto.yml
│   ├── quality/            # 程式碼品質規則
│   │   └── best-practices.yml
│   └── custom/             # 專案專屬規則
│       └── project-specific.yml
├── .semgrepignore          # 忽略檔案
└── semgrep.yml             # 整合配置
```

---

**CI/CD 整合**:
```yaml
# .github/workflows/semgrep.yml
name: Semgrep SAST
on: [push, pull_request]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
```

#### 3. GitLeaks（密鑰洩漏檢測）

**安裝**:
```bash
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Docker
docker pull zricethezav/gitleaks
```

**掃描 Git 儲存庫**:
```bash
# 掃描當前 repo
gitleaks detect --source . --report-path gitleaks-report.json

# 掃描整個歷史（包含已刪除的 commits）
gitleaks detect --source . --log-opts="--all"

# 掃描遠端 repo
gitleaks detect --source https://github.com/user/repo

# Pre-commit hook（阻止提交含密鑰的 commit）
gitleaks protect --staged --verbose
```

**配置檔案 (.gitleaks.toml)**:
```toml
title = "Custom Gitleaks Config"

[[rules]]
id = "aws-access-key"
description = "AWS Access Key"
regex = '''AKIA[0-9A-Z]{16}'''

[[rules]]
id = "github-token"
description = "GitHub Token"
regex = '''ghp_[0-9a-zA-Z]{36}'''

[allowlist]
paths = [
    '''test/fixtures/.*''',
    '''.*/examples/.*'''
]
```

**Pre-commit Hook 整合**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

#### 4. OWASP Dependency-Check（依賴套件漏洞掃描）

**安裝**:
```bash
# Docker（推薦）
docker pull owasp/dependency-check

# CLI
wget https://github.com/jeremylong/DependencyCheck/releases/download/v8.4.0/dependency-check-8.4.0-release.zip
unzip dependency-check-8.4.0-release.zip
```

**掃描專案**:
```bash
# 使用 Docker
docker run --rm -v $(pwd):/src \
  owasp/dependency-check \
  --scan /src \
  --format HTML \
  --out /src/dependency-check-report.html

# 使用 CLI
dependency-check.sh \
  --scan ./src \
  --format HTML \
  --out ./reports

# Maven 專案
mvn org.owasp:dependency-check-maven:check

# Gradle 專案
./gradlew dependencyCheckAnalyze
```

**CI/CD 整合**:
```yaml
# .github/workflows/dependency-check.yml
name: Dependency Check
on: [push, pull_request]

jobs:
  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Dependency-Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'MyApp'
          path: '.'
          format: 'HTML'
          args: >
            --failOnCVSS 7

      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: dependency-check-report
          path: reports/
```

#### 5. Trivy（容器映像安全掃描）

**安裝**:
```bash
# macOS
brew install trivy

# Linux
wget https://github.com/aquasecurity/trivy/releases/download/v0.46.0/trivy_0.46.0_Linux-64bit.tar.gz
tar zxvf trivy_0.46.0_Linux-64bit.tar.gz
sudo mv trivy /usr/local/bin/
```

**掃描 Docker 映像**:
```bash
# 掃描本地映像
trivy image nginx:latest

# 掃描並輸出 JSON
trivy image --format json -o results.json nginx:latest

# 掃描 Dockerfile
trivy config Dockerfile

# 掃描 Kubernetes manifests
trivy config k8s/deployment.yaml

# 掃描 IaC (Terraform, CloudFormation)
trivy config terraform/

# 設定嚴重度閾值
trivy image --severity HIGH,CRITICAL nginx:latest
```

**CI/CD 整合**:
```yaml
# .github/workflows/trivy-scan.yml
name: Trivy Security Scan
on: [push]

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker Image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy Scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

**🏗️ Golden Image 管理策略** 🆕 (v0.01 新增)

> **Golden Image 定義**：經過安全強化、漏洞修補的基礎容器映像，作為所有專案的標準起點。

**為什麼需要 Golden Image？**
- ✅ 統一基礎安全配置
- ✅ 減少已知漏洞暴露
- ✅ 加速安全掃描（已知安全的層不需重複掃描）
- ✅ 符合合規要求（可追溯的映像來源）

**Golden Image 建立流程**：

```
1. 選擇官方基礎映像 (Alpine/Debian/Ubuntu)
   ↓
2. 安全強化 (移除不必要套件、設定權限)
   ↓
3. 漏洞掃描 (Trivy/Clair)
   ↓
4. 簽署映像 (Cosign/Notary)
   ↓
5. 推送至私有 Registry
   ↓
6. 定期更新 (每週/每月)
```

**Golden Image Dockerfile 範例**：
```dockerfile
# golden-base-node.Dockerfile
FROM node:20-alpine3.18

# 安全強化
RUN apk update && apk upgrade --no-cache \
    && apk add --no-cache dumb-init \
    && rm -rf /var/cache/apk/* \
    && addgroup -g 1001 -S appgroup \
    && adduser -u 1001 -S appuser -G appgroup

# 移除不必要的工具
RUN rm -rf /usr/bin/wget /usr/bin/curl 2>/dev/null || true

# 設定非 root 使用者
USER appuser
WORKDIR /app

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s \
  CMD node -e "require('http').get('http://localhost:3000/health')"

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
```

**Golden Image 更新策略**：

| 更新觸發 | 頻率 | 行動 |
|---------|------|------|
| **定期更新** | 每週 | 更新基礎映像、套件 |
| **安全公告** | 即時 | 評估影響後緊急更新 |
| **重大漏洞 (CVE)** | 24 小時內 | 緊急發布新版本 |
| **相依套件更新** | 每月 | 驗證相容性後更新 |

**Golden Image CI/CD Pipeline**：
```yaml
# .github/workflows/golden-image.yml
name: Golden Image Build

on:
  schedule:
    - cron: '0 0 * * 0'  # 每週日更新
  workflow_dispatch:      # 手動觸發

jobs:
  build-golden:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Golden Image
        run: docker build -t golden-node:latest -f golden-base-node.Dockerfile .

      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'golden-node:latest'
          exit-code: '1'  # 有 CRITICAL 漏洞則失敗
          severity: 'CRITICAL'

      - name: Sign Image
        run: cosign sign --key cosign.key golden-node:latest

      - name: Push to Registry
        run: |
          docker tag golden-node:latest registry.example.com/golden-node:$(date +%Y%m%d)
          docker push registry.example.com/golden-node:$(date +%Y%m%d)
```

**Golden Image 使用檢查清單**：
- [ ] 所有專案 Dockerfile 以 Golden Image 為基礎
- [ ] Golden Image 每週自動更新
- [ ] Golden Image 有映像簽署驗證
- [ ] Golden Image 版本有清晰標籤 (日期/版本號)
- [ ] 有 Golden Image 漏洞監控告警

---

### 完整安全 CI/CD Pipeline 範例

```yaml
# .github/workflows/security-suite.yml
name: Security Scan Suite
on: [push, pull_request]

jobs:
  # SAST: 靜態代碼分析
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Semgrep Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit

  # Secret Scanning
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # 完整歷史

      - name: GitLeaks Scan
        uses: gitleaks/gitleaks-action@v2

  # SCA: 依賴套件掃描
  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: npm Audit
        run: npm audit --audit-level=moderate

      - name: OWASP Dependency-Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'MyApp'
          path: '.'
          format: 'HTML'

  # Container Scanning
  container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Image
        run: docker build -t myapp:latest .

      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:latest'
          severity: 'CRITICAL,HIGH'

  # DAST: 動態掃描（僅在部署到 staging 後）
  dast:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    steps:
      - name: ZAP Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'https://staging.example.com'
```

### 工具選擇建議

| 專案規模 | SAST | DAST | SCA | Secret Scan | 年度成本 |
|---------|------|------|-----|------------|---------|
| **小型** (<10人) | Semgrep | OWASP ZAP | npm audit | GitLeaks | $0 |
| **中型** (10-50人) | SonarQube Community + Semgrep | OWASP ZAP | Dependency-Check | GitLeaks + TruffleHog | $0 |
| **大型** (50+人) | 開源組合 或 Checkmarx | ZAP + 手動滲透測試 | Snyk (付費) | GitGuardian (付費) | $0 或 $50k+ |

### 商業方案 vs 開源方案對比

| 考量因素 | 商業方案 | 開源方案 |
|---------|---------|---------|
| **成本** | $50k-200k/年 | $0 (僅人力成本) |
| **整合度** | 統一平台 | 需自行整合 |
| **誤報率** | 較低（AI 輔助） | 中等（需人工驗證） |
| **支援** | 專業技術支援 | 社群支援 |
| **合規報告** | 自動生成 | 需手動整理 |
| **適用團隊** | 大型企業 | 中小型團隊 |

---

## 🎯 情境目標

### 主要目標

1. **安全性評估**: 系統性識別安全風險和漏洞
2. **安全加固**: 實施防禦措施和安全控制
3. **合規性檢查**: 確保符合相關法規和標準
4. **安全文檔**: 產出完整的安全和合規文檔

### 預計時間

**預計時間**:
- 📋 **AISDLC 規劃階段**: 2-3 天
  - **規劃時間** (AI 分析 + 人工確認): 2-3 天
  - **執行時間** (依專案規模):
    - 小型專案 (基本安全加固): 5-7 天
    - 中型專案 (完整合規實施): 1-2 週
    - 大型專案 (多標準合規+滲透測試): 2-4 週
- 🔨 **實際執行階段**: 5 天-4 週 (依專案規模而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行安全評估、威脅建模、修復策略文檔產出的時間
> - **執行時間**指實際安全加固和合規實施的時間，會因安全問題嚴重度、合規標準複雜度而有很大差異
> - 時間估算包含人工確認和 AI 輔助分析的完整流程

**時間分配參考**:
- 階段 1 (安全評估與合規分析): 1-2 天
- 階段 2 (安全需求與架構設計): 1-2 天
- 階段 3 (安全實施與修復): 2-5 天
- 階段 4 (安全測試與驗證): 1-3 天
- 階段 5 (文檔與交付): 0.5-1 天

### 預期產出

- ✅ Security Assessment Report（安全評估報告）
- ✅ Threat Model（威脅模型）
- ✅ Security Requirements Document（安全需求文件）
- ✅ Compliance Checklist（合規檢查清單）
- ✅ Security Test Plan（安全測試計畫）
- ✅ Remediation Plan（修復計畫）
- ✅ Security Architecture Diagram（安全架構圖）
- ✅ Compliance Report（合規報告）

---

## 🤝 協作模式 (Phase 2: v0.03)

### 主要協作模式

#### 1. Peer-Review (同儕審查)
- **主導 Agent**: Security-Engineer (Primary)
- **審查 Agents**: SD-Architect + QA-Lead (Peers)
- **使用階段**: 安全設計產出後的審查階段
- **模式說明**: 安全設計需要多方專業審查確保完整性

#### 2. Peer-Review 流程
```
Security-Engineer 產出安全設計
    ↓
SD + QA-Lead peer review
    ↓
Security-Engineer 修訂
    ↓
Compliance-Officer 合規審查
    ↓
🔴 人類批准
```

### 次要協作模式

#### 3. Lead-Support (主導-支援)
- **使用階段**: 威脅建模和安全架構設計
- **模式說明**: Security-Engineer 主導，其他 Agents 提供專業輸入

#### 4. Sequential-Handoff (順序交接)
- **流程**: 安全設計 → 🔴 → Dev → 安全實作 → 🔴 → QA-Lead → 安全測試
- **模式說明**: 安全設計完成後依序實作和測試

### 🔔 Event-Driven Agent Notification（🔴 強制）

> Security 情境的 PR 事件通知 + 部署通知為強制。情境專屬觸發：enhanced-SAST + DAST 掃描報告 + compliance-check 結果。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 📋 前置準備檢查清單

> ⚠️ **重要提示**: 以下前置材料為理想狀態。若材料缺失,請參考「材料缺失應對方案」。

### 必要材料
- [ ] 系統架構文檔 (系統邊界、組件圖、資料流圖)
- [ ] 現有安全政策文件 (如有)
- [ ] 合規要求文件 (GDPR/HIPAA/PCI-DSS/ISO 27001 等相關法規)
- [ ] 敏感資料清單 (個資、金融資料、健康資料等)
- [ ] 代碼庫存取權限
- [ ] 測試環境存取權限

### 選擇性材料
- [ ] 過往滲透測試報告
- [ ] 安全事件歷史記錄
- [ ] 第三方服務清單及其安全文檔
- [ ] 現有安全工具配置 (SAST/DAST/SCA)
- [ ] 安全稽核歷史報告
- [ ] 使用者權限管理文檔
- [ ] 資料備份與災難恢復計畫

### 環境檢查
- [ ] 可存取生產環境配置 (僅查看,不修改)
- [ ] 可執行安全掃描工具
- [ ] 可存取日誌和監控系統
- [ ] 可聯繫合規/法務團隊 (若有合規問題)

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 許多專案在開始安全評估時缺乏完整的安全文檔。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **系統架構文檔** | 🔴 高 | • **方案 1**: 使用 Code-Analyzer 掃描生成基本架構圖<br>• **方案 2**: 訪談開發團隊繪製系統邊界和資料流圖<br>• **方案 3**: 從部署配置 (Kubernetes/Docker Compose) 反推架構<br>• **方案 4**: 先進行「快速架構重建」(2-3小時) 再開始安全評估 | +2-4 小時 |
| **合規要求文件** | 🔴 高 | • **方案 1**: 諮詢法務或合規部門取得相關法規清單<br>• **方案 2**: 根據行業和地區查詢常見合規標準 (金融→PCI-DSS, 醫療→HIPAA, 歐盟→GDPR)<br>• **方案 3**: 使用 Compliance-Officer Agent 生成初步合規檢查清單<br>• **方案 4**: ⚠️ **重要**: 若涉及法律合規,必須諮詢法律顧問,技術實施不等於法律合規 | +1-2 小時 |
| **敏感資料清單** | 🔴 高 | • **方案 1**: 掃描資料庫 Schema 識別可能的敏感欄位 (email, phone, SSN, card_number 等)<br>• **方案 2**: 檢查代碼中的加密/脫敏邏輯反推敏感資料<br>• **方案 3**: 訪談產品團隊或業務人員確認資料類型<br>• **方案 4**: 使用資料分類工具自動掃描 (如 AWS Macie, Google DLP) | +1-3 小時 |
| **過往滲透測試報告** | 🟡 中 | • **方案 1**: 執行基本漏洞掃描替代 (使用免費工具如 OWASP ZAP, Nikto)<br>• **方案 2**: 使用 SAST 工具掃描代碼漏洞 (如 Bandit, Semgrep)<br>• **方案 3**: 參考 OWASP Top 10 進行手動檢查<br>• **方案 4**: 先完成本次評估,建議未來進行專業滲透測試 | +2-4 小時 |
| **現有安全政策** | 🟡 中 | • **方案 1**: 使用 Security-Engineer Agent 基於行業最佳實踐生成初步政策框架<br>• **方案 2**: 參考類似規模公司的開源安全政策 (GitHub Security Policy templates)<br>• **方案 3**: 從合規標準反推必要的安全政策 (如 ISO 27001 Annex A)<br>• **方案 4**: 先建立最小安全政策集,後續逐步完善 | +2-3 小時 |
| **第三方服務安全文檔** | 🟡 中 | • **方案 1**: 查詢第三方服務的官方安全文檔 (通常在 `/security` 或 `/compliance` 頁面)<br>• **方案 2**: 檢查服務提供商的 SOC 2/ISO 27001 認證狀態<br>• **方案 3**: 使用網路掃描工具檢查第三方 API 的 SSL/TLS 配置<br>• **方案 4**: 若無文檔,列為高風險項目並建議更換服務商 | +1-2 小時 |
| **安全工具配置** | 🟢 低 | • **方案 1**: 使用免費/開源工具建立基本安全掃描 (詳見「免費工具替代方案」)<br>• **方案 2**: 先進行手動安全檢查,後續再建立自動化<br>• **方案 3**: 使用 CI/CD 內建的基本安全檢查 (如 GitHub Dependabot, GitLab Security Scanning) | +1-2 小時 |

### 合規文件完全缺失時的應對流程

若專案處於高合規行業但缺乏任何合規文件,建議採用「**合規啟動包 (Compliance Starter Kit)**」策略:

#### 階段 1: 識別適用法規 (0.5-1 小時)
根據以下因素判斷:
- **行業**: 金融 → PCI-DSS/SOX, 醫療 → HIPAA, 政府 → FedRAMP
- **地區**: 歐盟 → GDPR, 加州 → CCPA, 中國 → PIPL, **台灣 → 個人資料保護法（個資法）**
- **資料類型**: 信用卡 → PCI-DSS, 健康資料 → HIPAA, 個資 → GDPR/CCPA/**台灣個資法**

> 🇹🇼 **台灣個人資料保護法（個資法）補充說明**（適用於電商、民宿、會員管理系統）:
>
> | 要求 | 技術實施 |
> |-----|--------|
> | 告知當事人蒐集目的（第 8 條） | 註冊/購物流程加入明確告知文字 |
> | 特定目的原則（第 20 條） | 跨模組資料使用需有合法依據（電商訂單資料不可用於民宿行銷） |
> | 安全維護義務（第 27 條） | PII 欄位加密、存取控制、稽核日誌 |
> | 違規通報義務（第 12 條） | 建立 72 小時通報 SOP（需通報主管機關） |
> | 委外處理契約（第 21 條） | 與 Stripe、AWS 等第三方簽訂資料處理協議（DPA） |
> | 跨境傳輸限制（第 21 條） | 確認第三方服務的資料儲存位置是否符合個資法要求 |
>
> ⚠️ **複合型系統特別注意**: 電商+民宿+內容+知識管理系統，跨模組共用個人資料時，需確保每次資料使用均符合原蒐集之特定目的，否則構成違法使用。

#### 階段 2: 建立最小合規檢查清單 (1-2 小時)
使用 Compliance-Officer Agent 生成:
1. 資料處理合法性檢查
2. 資料主體權利實施 (查詢、刪除、匯出)
3. 資料外洩通知機制 (GDPR 要求 72 小時通知)
4. 資料加密要求 (傳輸中/靜態)
5. 存取控制和稽核日誌

#### 階段 3: 法律諮詢確認 (必要!)
⚠️ **關鍵警告**: 技術實施僅是合規的一部分,必須:
- 諮詢法律顧問確認法規解讀
- 確認資料處理協議 (DPA) 的法律效力
- 確認跨境資料傳輸的合法性
- 準備隱私政策和使用條款的法律審查

---

## 👥 團隊角色配置

### 核心 Agents

| Agent | 角色 | 主要職責 |
|-------|------|---------|
| **Security-Engineer** | 安全工程師 | 安全架構設計、漏洞分析、安全測試 |
| **Compliance-Officer** | 合規專員 | 法規解讀、合規檢查、稽核準備 |
| **SA (Amanda)** | 系統分析師 | 需求分析、影響評估 |
| **SD (Marcus)** | 系統設計師 | 安全架構設計、技術方案 |
| **QA-Lead (Quincy)** | QA 主管 | 安全測試策略、測試執行 |
| **Dev-Senior** | 資深開發 | 安全修復實施、Code Review |

### 可選 Agents（依需求）

- **BA (Beatrice)**: 業務合規需求分析
- **PM/PO (Victoria)**: 安全預算和優先級決策
- **DevOps-Engineer**: 安全 CI/CD Pipeline 建置
- **Technical-Writer**: 安全文檔撰寫
- **Integration-Specialist**: 第三方整合安全審查（支付 Stripe/ECPay、OAuth、Webhook 驗證）— 電商/支付系統必載
- **SD-Mobile-Architect**: 行動端安全架構設計（Android/iOS/macOS QR 碼安全）
- **QA-Mobile-Tester**: 行動端安全測試執行
- **QA-Web-Tester**: Web 前端安全測試（XSS/CSRF/CSP）

---

## 🔄 標準作業流程

### 階段 1：安全評估與合規分析（1-2 天）

#### 步驟 1.1: 情境確認與範圍界定
**負責 Agent**: Security-Engineer + Compliance-Officer

> 🔴 **人機協作點**: 確認評估範圍和合規標準
> - 確認專案類型（Web App / Mobile App / API / 混合）
> - 識別適用的合規標準（GDPR / HIPAA / PCI-DSS / ISO 27001 等）
> - 界定評估範圍（系統邊界、資料流、第三方服務）
> - 識別敏感資料類型（個資 / 金融 / 健康 / 商業機密）

**執行內容**:
1. 確認專案類型（Web App / Mobile App / API / 混合）
2. 識別適用的合規標準（GDPR / HIPAA / PCI-DSS / ISO 27001 等）
3. 界定評估範圍（系統邊界、資料流、第三方服務）
4. 識別敏感資料類型（個資 / 金融 / 健康 / 商業機密）

**產出**:
- Security Assessment Scope Document
- Compliance Standards Checklist

**範例對話**:
```
Security-Engineer:
我需要了解以下資訊來界定安全評估範圍：

1. 系統類型: [ ] Web App  [ ] Mobile App  [ ] API  [ ] 其他
2. 資料類型: [ ] 個人資料  [ ] 金融資料  [ ] 健康資料  [ ] 其他
3. 合規要求: [ ] GDPR  [ ] HIPAA  [ ] PCI-DSS  [ ] ISO 27001  [ ] 其他
4. 評估範圍: [ ] 完整系統  [ ] 特定模組  [ ] 新增功能
5. 第三方服務: 請列出所有整合的外部服務（支付、雲端儲存等）

🔴 請確認以上資訊
```

---

#### 步驟 1.2: 威脅建模（Threat Modeling）
**負責 Agent**: Security-Engineer + SA

> 🔴 **人機協作點**: 確認威脅優先級
> - 審查資料流圖的完整性和準確性
> - 確認信任邊界劃分是否合理
> - 驗證 STRIDE 威脅識別的全面性
> - 確認威脅風險等級評估（Critical / High / Medium / Low）

**執行內容**:
1. 繪製資料流圖（Data Flow Diagram）
2. 識別信任邊界（Trust Boundaries）
3. 使用 STRIDE 方法識別威脅
   - **S**poofing（身份偽造）
   - **T**ampering（資料竄改）
   - **R**epudiation（否認性）
   - **I**nformation Disclosure（資訊洩露）
   - **D**enial of Service（阻斷服務）
   - **E**levation of Privilege（權限提升）
4. 評估威脅風險等級（Critical / High / Medium / Low）

**產出**:
- Data Flow Diagram
- Threat Model Document（使用 STRIDE）
- Risk Priority Matrix

**威脅評分公式**:
```
Risk Score = Likelihood (1-5) × Impact (1-5)
- Critical: 20-25
- High: 15-19
- Medium: 8-14
- Low: 1-7
```

---

#### 步驟 1.3: 安全漏洞掃描（如果是既有系統）
**負責 Agent**: Security-Engineer + QA-Lead
**人機協作點**: 無（自動化掃描）

**執行內容**:
1. 靜態代碼掃描（SAST）
   - SonarQube / Checkmarx / Fortify
   - 檢查 OWASP Top 10 漏洞
2. 依賴套件漏洞掃描
   - npm audit / pip-audit / Snyk
   - 檢查已知 CVE
3. 配置檢查
   - 密碼強度、加密設定、HTTPS 配置
4. 敏感資料掃描
   - 檢查硬編碼密碼、API Key、Token

> **⚠️ 開源安全工具替代方案 (Open Source Security Tools)**
>
> 商業工具 (SonarQube/Checkmarx) 價格昂貴,以下開源工具提供類似功能:
>
> **工具對照表**:
> | 商業工具 | 開源替代方案 | 功能對比 | 適用場景 |
> |---------|------------|---------|---------|
> | **SonarQube Enterprise** | SonarQube Community | 90% 功能相同,缺少分支分析 | 中小型專案 |
> | **Checkmarx** | Semgrep | 靜態分析,規則可自訂 | 多語言專案 |
> | **Fortify** | Bandit (Python)<br>Brakeman (Ruby)<br>ESLint Security | 語言特定分析 | 單一語言專案 |
> | **Snyk** | OWASP Dependency-Check | 依賴套件漏洞掃描 | 免費但較慢 |
> | **Burp Suite Pro** | OWASP ZAP | Web 漏洞掃描 | 功能齊全,免費 |
> | **Nessus** | OpenVAS | 網路漏洞掃描 | 基礎設施掃描 |
>
> **工具 1: OWASP ZAP (Web Application Scanner)**
> ```bash
> # 安裝
> docker pull zaproxy/zap-stable
> 
> # 執行自動掃描
> docker run -t zaproxy/zap-stable zap-baseline.py \
>   -t https://your-app.com \
>   -r zap-report.html
> 
> # CI/CD 整合
> # .github/workflows/security-scan.yml
> - name: ZAP Scan
>   uses: zaproxy/action-baseline@v0.7.0
>   with:
>     target: "https://staging.example.com"
>     rules_file_name: ".zap/rules.tsv"
>     fail_action: true
> ```
>
> **工具 2: Semgrep (靜態程式碼分析)**
> ```bash
> # 安裝
> pip install semgrep
> 
> # 執行掃描 (使用 OWASP Top 10 規則)
> semgrep --config=auto .
> 
> # 自訂規則範例
> # .semgrep/rules/hardcoded-secrets.yml
> rules:
>   - id: hardcoded-password
>     pattern: |
>       password = "..."
>     message: "Hardcoded password detected"
>     severity: ERROR
>     languages: [python, javascript]
> 
> # CI/CD 整合
> semgrep ci --config=auto --sarif -o semgrep-results.sarif
> ```
>
> **工具 3: Bandit (Python 安全分析)**
> ```bash
> # 安裝
> pip install bandit
> 
> # 執行掃描
> bandit -r src/ -f json -o bandit-report.json
> 
> # 忽略特定規則
> bandit -r src/ -s B404,B603  # 忽略 import subprocess
> 
> # 配置檔案
> # .bandit
> [bandit]
> exclude_dirs = ["/test", "/venv"]
> skips = ["B404", "B603"]
> ```
>
> **工具 4: OWASP Dependency-Check (依賴漏洞掃描)**
> ```bash
> # 使用 Docker
> docker run --rm -v $(pwd):/src owasp/dependency-check \
>   --scan /src \
>   --format HTML \
>   --out /src/dependency-check-report.html
> 
> # Gradle 整合
> plugins {
>     id "org.owasp.dependencycheck" version "8.4.0"
> }
> 
> dependencyCheck {
>     format = "HTML"
>     failBuildOnCVSS = 7
> }
> ```
>
> **工具 5: GitLeaks (密鑰洩漏檢測)**
> ```bash
> # 安裝
> brew install gitleaks  # macOS
> 
> # 掃描當前 repo
> gitleaks detect --source . --report-path gitleaks-report.json
> 
> # 掃描整個歷史
> gitleaks detect --source . --log-opts="--all"
> 
> # Pre-commit hook
> # .git/hooks/pre-commit
> #!/bin/sh
> gitleaks protect --staged --verbose
> ```
>
> **完整 CI/CD 整合範例**:
> ```yaml
> # .github/workflows/security-suite.yml
> name: Security Scan Suite
> 
> on: [push, pull_request]
> 
> jobs:
>   security-scan:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v3
>       
>       # SAST: Semgrep
>       - name: Semgrep Scan
>         uses: returntocorp/semgrep-action@v1
>         with:
>           config: auto
>       
>       # Dependency Check
>       - name: Dependency Check
>         run: |
>           npm audit --audit-level=moderate
>           # 或使用 OWASP Dependency-Check
>       
>       # Secret Scanning
>       - name: GitLeaks Scan
>         uses: gitleaks/gitleaks-action@v2
>       
>       # DAST: ZAP (僅在 PR 時執行)
>       - name: ZAP Baseline Scan
>         if: github.event_name == "pull_request"
>         uses: zaproxy/action-baseline@v0.7.0
>         with:
>           target: "https://pr-${{ github.event.number }}.staging.example.com"
> ```
>
> **成本對比**:
> | 方案 | 年度成本 | 優點 | 缺點 |
> |------|---------|------|------|
> | **商業工具組合** | $50,000-200,000 | 整合度高,支援好 | 價格昂貴 |
> | **開源工具組合** | $0 (僅人力成本) | 完全免費,可自訂 | 需自行整合維護 |
> | **混合方案** | $10,000-30,000 | 平衡成本與功能 | 需管理多工具 |

   - 檢查硬編碼密碼、API Key、Token

**產出**:
- Vulnerability Scan Report
- Dependency Audit Report
- Security Findings Summary

---

#### 步驟 1.4: 合規性差距分析（Compliance Gap Analysis）
**負責 Agent**: Compliance-Officer + BA
**人機協作點**: 🔴 確認合規要求解讀

**執行內容**:
1. 對照適用法規要求（如 GDPR 的 99 條款）
2. 檢查現有系統符合度
3. 識別合規差距（Gap）
4. 評估差距風險等級

**產出**:
- Compliance Gap Analysis Report
- Compliance Checklist（標註符合/不符合/部分符合）
- Remediation Priority List

**常見合規標準**:

| 標準 | 適用行業 | 核心要求 |
|-----|---------|---------|
| **GDPR** | 處理歐盟居民資料 | 資料最小化、同意機制、資料主體權利 |
| **HIPAA** | 美國醫療健康 | PHI 保護、存取控制、稽核記錄 |
| **PCI-DSS** | 信用卡交易 | 加密傳輸、存取控制、定期測試 |
| **ISO 27001** | 通用資訊安全 | ISMS 建立、風險評估、持續改進 |
| **SOC 2** | SaaS 服務商 | 安全性、可用性、機密性控制 |
| **台灣個資法** | 台灣境內蒐集個資 | 告知義務、特定目的原則、安全維護、72h 違規通報 |

---

#### 步驟 1.5（特殊）: 跨模組授權矩陣設計（複合型系統必做）
**負責 Agent**: Security-Engineer + SA + SD-Architect
**適用條件**: 系統包含 2 個以上獨立業務模組（如電商+民宿+內容+知識管理）

> 🔴 **人機協作點**: 確認跨模組授權邊界
> - 確認每個角色在各模組的最大權限範圍
> - 確認模組間資料存取是否有業務依據
> - 確認多租戶資料隔離策略

**授權矩陣範例（電商+民宿+內容+知識管理）**:

| 角色 | EC 電商 | HM 民宿 | CP 內容 | KM 知識庫 | 說明 |
|-----|---------|---------|---------|-----------|------|
| **匿名用戶** | 瀏覽商品 | 查詢房況 | 讀已發布 | 讀公開文章 | 無需登入 |
| **一般會員** | 購物/訂單 | 查/新建預訂 | 讀已發布 | 讀基本知識庫 | 自身資料 |
| **付費會員** | 全功能 | 全功能 | 讀付費內容 | 讀全部知識庫 | 訂閱驗證 |
| **內容作者** | 無 | 無 | 管理自己文章 | 編輯知識文章 | 僅限自身內容 |
| **民宿管理員** | 查訂單（房客）| 全部管理 | 無 | 無 | 跨模組限制 |
| **EC 管理員** | 全部管理 | 無 | 無 | 無 | 跨模組限制 |
| **超級管理員** | 全部 | 全部 | 全部 | 全部 | 稽核日誌必啟用 |

**實施要點**:
```
1. 每個 Spring Boot API 端點必須有 @PreAuthorize 標注
2. 跨模組 API 呼叫必須通過統一 API Gateway 授權層
3. 禁止前端直接暴露跨模組管理 API
4. 超級管理員操作必須記錄完整 Audit Log
5. 多租戶隔離：PostgreSQL Row-Level Security (RLS) 強制租戶過濾
```

---

#### 步驟 1.6（特殊）: QR 碼安全設計（含行動端掃碼場景）
**負責 Agent**: Security-Engineer + SD-Mobile-Architect + Integration-Specialist
**適用條件**: 系統使用 QR 碼進行業務操作（入住/核銷/商品查詢）

> 🔴 **人機協作點**: 確認 QR 碼安全機制設計

**QR 碼安全設計規範**:

```
❌ 不安全的 QR 碼設計：
  QR 碼內容 = bookingId (純文字，可偽造)

✅ 安全的 QR 碼設計：
  QR 碼內容 = base64({
    "bookingId": "B-2026-001",
    "timestamp": 1711900000,     // Unix timestamp（生成時間）
    "expiry": 1711903600,        // 有效期（生成後 60 分鐘）
    "hmac": "SHA256(bookingId + timestamp + expiry + secret)"
  })

  後端驗證流程：
  1. 解碼 base64 取得 payload
  2. 驗證 expiry > now（防截圖重放）
  3. 重新計算 HMAC，與 payload.hmac 比對
  4. 驗證 bookingId 對應預訂狀態為 CONFIRMED
  5. 記錄 check-in 事件（防重複掃碼）
```

**行動端安全要求（Android / macOS）**:
- ✅ HTTPS + Certificate Pinning（OkHttp / URLSession）
- ✅ JWT 存入 Encrypted Storage（Jetpack Security / Keychain）
- ✅ App Link / Universal Link 驗證（防 URL Scheme 劫持）
- ✅ QR 碼掃描結果本地不快取敏感資料
- ✅ 掃碼請求加入 Nonce 防重放

---

### 階段 2：安全需求與架構設計（1-2 天）

#### 步驟 2.1: 制定安全需求
**負責 Agent**: Security-Engineer + SA + Compliance-Officer

> 🔴 **人機協作點**: 確認安全需求優先級
> - 審查安全需求的完整性和可行性
> - 確認需求優先級排序（Critical / High / Medium / Low）
> - 驗證需求與威脅模型的對應關係
> - 確認合規性要求的覆蓋程度

**執行內容**:
1. 根據威脅模型和合規要求制定安全需求
2. 分類安全需求
   - **身份與存取控制** (Authentication & Authorization)
   - **資料保護** (Data Protection)
   - **通訊安全** (Communication Security)
   - **稽核與日誌** (Audit & Logging)
   - **錯誤處理** (Error Handling)
   - **會話管理** (Session Management)
3. 定義安全驗收標準
4. 優先級排序（P0 / P1 / P2）

**產出**:
- Security Requirements Document (SRD-Security)
- Security Acceptance Criteria

**範例安全需求**:
```markdown
## SR-001: 身份驗證
- 優先級: P0
- 需求: 所有 API 端點必須實施 OAuth 2.0 身份驗證
- 驗收標準:
  - AC-001-1: 未認證請求回應 401 Unauthorized
  - AC-001-2: Token 有效期不超過 1 小時
  - AC-001-3: 實施 Refresh Token 機制
  - AC-001-4: 支援 Multi-Factor Authentication (MFA)
```

---

#### 步驟 2.2: 設計安全架構
**負責 Agent**: Security-Engineer + SD
**人機協作點**: 🔴 確認架構設計方案

**執行內容**:
1. 設計安全層級架構（Defense in Depth）
   - **網路層**: Firewall、WAF、DDoS Protection
   - **應用層**: Input Validation、Output Encoding、CSRF Protection
   - **資料層**: Encryption at Rest、Encryption in Transit、Key Management
   - **身份層**: SSO、MFA、RBAC
2. 設計加密策略
   - 傳輸加密: TLS 1.3
   - 靜態加密: AES-256
   - 密鑰管理: AWS KMS / Azure Key Vault / HashiCorp Vault
3. 設計存取控制模型（RBAC / ABAC）
4. 設計稽核日誌策略

**產出**:
- Security Architecture Diagram
- Encryption Strategy Document
- Access Control Model

---

#### 步驟 2.3: 選擇安全工具與服務
**負責 Agent**: Security-Engineer + DevOps-Engineer
**人機協作點**: 🔴 確認工具選擇和預算

**執行內容**:
1. 選擇 SAST/DAST 工具
2. 選擇 WAF 服務（CloudFlare / AWS WAF / Azure WAF）
3. 選擇 Secret Management（Vault / AWS Secrets Manager）
4. 選擇 SIEM 工具（如需）
5. 規劃安全 CI/CD Pipeline

**產出**:
- Security Tools Selection Document
- Security Pipeline Design

---

### 階段 3：安全實施與修復（2-5 天）

#### 步驟 3.1: 安全加固實施
**負責 Agent**: Dev-Senior + Security-Engineer
**人機協作點**: 🔴 每個模組完成後確認

**執行內容**:
1. 實施身份驗證與授權機制
2. 實施資料加密（傳輸 + 靜態）
3. 實施 Input Validation 和 Output Encoding
4. 實施 CSRF / XSS / SQL Injection 防護
5. 實施安全日誌和監控
6. 修復已知漏洞

**實施檢查清單**:
```markdown
## 身份與存取控制
- [ ] 實施強密碼策略（最少 12 字元，複雜度要求）
- [ ] 實施 MFA（至少支援 TOTP）
- [ ] 實施 Session Timeout（閒置 15 分鐘）
- [ ] 實施 RBAC 或 ABAC
- [ ] 禁用預設帳號和密碼

## 資料保護
- [ ] 所有敏感資料加密儲存（AES-256）
- [ ] 所有通訊使用 TLS 1.3
- [ ] 實施資料遮罩（data masking）
- [ ] 實施資料保留政策
- [ ] 安全刪除機制（資料主體權利）

## 應用安全
- [ ] 所有 Input 進行 Validation 和 Sanitization
- [ ] 所有 Output 進行 Encoding
- [ ] 實施 CSRF Token
- [ ] 實施 Content Security Policy (CSP)
- [ ] 使用參數化查詢（防 SQL Injection）
- [ ] 安全的錯誤處理（不洩露敏感資訊）

## 稽核與日誌
- [ ] 記錄所有認證事件（成功/失敗）
- [ ] 記錄所有授權決策
- [ ] 記錄敏感資料存取
- [ ] 記錄配置變更
- [ ] 日誌包含 timestamp、user、action、result
- [ ] 日誌本身受保護（防竄改）
```

**產出**:
- Security Implementation Code
- Security Configuration Files
- Implementation Checklist (Completed)

---

#### 步驟 3.1.1: 行動端安全加固（Mobile Security Hardening）
**負責 Agent**: Security-Engineer + SD-Mobile-Architect
**人機協作點**: 🔴 確認行動平台安全策略
**適用條件**: 專案包含 Android / iOS / macOS 行動端應用時執行

> 💡 **使用 Skill**: `/mobile-development` 搭配本節使用，取得行動端架構與安全實作指引。

**執行內容**:
1. 實施通訊安全（Certificate Pinning + TLS 1.3）
2. 實施裝置認證與綁定機制
3. 實施本地資料加密與安全儲存
4. 實施條碼掃描安全驗證
5. 實施離線操作安全策略

**行動端安全檢查清單**:
```markdown
## 通訊安全
- [ ] 實施 Certificate Pinning（防中間人攻擊）
- [ ] 強制 TLS 1.3，禁用降級
- [ ] API 通訊使用 JWT + RS256 簽章驗證
- [ ] 偵測 Proxy / MITM 並阻斷連線

## 裝置認證與綁定
- [ ] 裝置首次登入需管理員核准（Device Enrollment）
- [ ] 裝置指紋綁定（Device ID + User 對應）
- [ ] 單一帳號裝置上限設定（建議 ≤ 3 台）
- [ ] 遠端裝置撤銷功能（Lost/Stolen 處理）
- [ ] Root/Jailbreak 偵測（偵測到則限制功能或阻斷）

## 本地資料保護
- [ ] 敏感資料使用平台安全儲存
      - Android: EncryptedSharedPreferences / Keystore
      - macOS/iOS: Keychain Services
- [ ] 本地資料庫加密（SQLCipher 或平台等效方案）
- [ ] 快取資料自動過期清除（≤ 24 小時）
- [ ] 禁止螢幕截圖含敏感資料頁面（FLAG_SECURE）
- [ ] App 切換背景時模糊化敏感畫面

## 條碼掃描安全
- [ ] 掃描結果需經後端 API 驗證（不信任本地解析）
- [ ] 掃描輸入實施 Input Validation（長度、格式、字元集）
- [ ] 防止惡意 QR Code 注入攻擊（URL Scheme Hijacking）
- [ ] 掃描記錄包含操作員、時間、GPS（可選）、裝置 ID

## 離線操作安全
- [ ] 離線操作需先通過本地生物辨識 / PIN 驗證
- [ ] 離線資料同步時重新驗證 Token 有效性
- [ ] 離線累積交易量上限設定（超過需上線同步）
- [ ] 衝突解決策略（Server-wins / Last-write-wins 依業務決定）
- [ ] 離線逾時自動登出（建議 ≤ 8 小時）

## 應用完整性
- [ ] 實施 App 簽章驗證（防止重新打包）
- [ ] 實施程式碼混淆（ProGuard/R8 for Android）
- [ ] 偵測偵錯工具附加（Anti-debugging）
- [ ] 自動更新強制機制（最低版本控制）
```

**產出**:
- Mobile Security Implementation Code
- Mobile Security Configuration
- Mobile Security Checklist (Completed)

---

#### 步驟 3.2: 合規性實施
**負責 Agent**: Compliance-Officer + Dev-Senior
**人機協作點**: 🔴 確認合規措施實施

**執行內容**:
1. 實施資料主體權利機制（GDPR）
   - 查閱權、更正權、刪除權、可攜權
2. 實施同意管理機制
3. 實施資料處理記錄（ROPA）
4. 實施隱私通知（Privacy Notice）
5. 實施資料外洩通知機制（72 小時內）

**GDPR 實施檢查清單**:
```markdown
- [ ] 隱私政策和使用條款頁面
- [ ] Cookie 同意橫幅（必要/分析/行銷分類）
- [ ] 資料主體存取請求（DSAR）API
- [ ] 個資下載功能（JSON/CSV 格式）
- [ ] 帳號刪除功能（30 天內完成）
- [ ] 資料處理記錄（ROPA）維護
- [ ] DPO 聯絡資訊揭露
- [ ] 資料外洩應變計畫

> **⚠️ 資料外洩應變 Playbook (Data Breach Response Playbook)**
>
> GDPR 要求在發現資料外洩後 **72 小時內** 通知監管機關,需要詳細的應變流程:
>
> **⏰ 時間軸總覽**:
> ```
> T+0:    發現外洩 → 啟動應變團隊
> T+1h:   初步調查 → 確認影響範圍
> T+4h:   遏制措施 → 停止外洩擴散
> T+24h:  詳細分析 → 準備通知內容
> T+72h:  通知監管機關 (GDPR 要求)
> T+7天:  通知受影響個人
> T+30天: 事後檢討與改善
> ```
>
> **階段 1: 發現與啟動 (T+0 ~ T+1h)**
>
> **觸發條件**:
> - 監控系統偵測異常存取
> - 員工發現可疑活動
> - 第三方通知
> - 白帽駭客揭露
>
> **立即行動**:
> 1. **啟動應變團隊** (Incident Response Team)
>    - 📞 通知: CISO, CTO, Legal, PR, DPO (Data Protection Officer)
>    - 📝 建立事件追蹤編號: `BREACH-2024-001`
>    - 💬 開啟專用溝通頻道 (Slack/Teams 私密頻道)
>
> 2. **記錄時間軸** (所有行動需記錄時間戳)
>    ```markdown
>    # Incident Log: BREACH-2024-001
>    - 2024-03-15 14:23 UTC: 監控系統偵測異常查詢 (10,000+ user records)
>    - 2024-03-15 14:30 UTC: Security Team 確認並啟動應變
>    - 2024-03-15 14:35 UTC: CISO 通知,召集應變團隊
>    ```
>
> **階段 2: 遏制 (T+1h ~ T+4h)**
>
> **遏制措施檢查清單**:
> - [ ] **隔離受影響系統**: 斷開網路連線或關閉服務
> - [ ] **撤銷受損憑證**: API Keys, Tokens, Passwords
> - [ ] **啟用 WAF 規則**: 封鎖可疑 IP
> - [ ] **資料庫唯讀模式**: 防止進一步資料變更
> - [ ] **保留證據**: 備份日誌和系統快照
>
> ```bash
> # 緊急遏制腳本範例
> # scripts/emergency-containment.sh
> 
> # 1. 切換資料庫為唯讀
> mysql -e "SET GLOBAL read_only = ON;"
> 
> # 2. 撤銷所有 API Tokens
> psql -c "UPDATE api_tokens SET is_active = false WHERE created_at < NOW();"
> 
> # 3. 封鎖可疑 IP
> iptables -A INPUT -s 192.0.2.100 -j DROP
> 
> # 4. 備份當前日誌
> tar -czf logs-backup-$(date +%Y%m%d-%H%M%S).tar.gz /var/log/
> ```
>
> **階段 3: 調查與分析 (T+4h ~ T+24h)**
>
> **調查問題清單**:
> 1. **Who (誰)**: 攻擊者身份? 內部/外部?
> 2. **What (什麼)**: 哪些資料被存取/外洩?
> 3. **When (何時)**: 外洩發生時間? 持續多久?
> 4. **Where (哪裡)**: 哪些系統/資料庫受影響?
> 5. **Why (為何)**: 攻擊手法? 漏洞為何?
> 6. **How (如何)**: 攻擊路徑? 如何進入系統?
>
> **影響評估**:
> ```yaml
> breach_assessment:
>   affected_records: 50000
>   data_types:
>     - name: "姓名"
>       sensitivity: medium
>     - name: "Email"
>       sensitivity: low
>     - name: "電話號碼"
>       sensitivity: medium
>     - name: "信用卡號 (後四碼)"
>       sensitivity: high
>   
>   risk_level: HIGH  # LOW/MEDIUM/HIGH/CRITICAL
>   gdpr_notification_required: true
>   affected_jurisdictions: ["EU", "US-CA", "TW"]
> ```
>
> **階段 4: 通知 (T+24h ~ T+72h)**
>
> **通知優先順序**:
> 1. **內部通知** (立即)
>    - 董事會/管理層
>    - 全體員工 (需要時)
>
> 2. **監管機關** (72 小時內) ⚠️ **GDPR 強制要求**
>    - EU: 各國 DPA (Data Protection Authority)
>    - US: 州法律要求 (如加州 CCPA)
>    - TW: 個資保護委員會
>
> 3. **受影響個人** (無不當延遲)
>    - Email 通知
>    - App 推播
>    - 官網公告
>
> **通知範本**:
> ```markdown
> # 資料外洩通知信 (給受影響用戶)
> 
> 主旨: 重要安全通知 - 您的個人資料可能受影響
> 
> 親愛的用戶您好,
> 
> 我們於 2024 年 3 月 15 日發現資料安全事件。經調查,您的以下資料可能
> 在此事件中被未授權存取:
> 
> - 姓名
> - Email 地址
> - 電話號碼
> 
> **您的信用卡完整號碼、密碼未受影響。**
> 
> ## 我們已採取的措施
> - 已關閉安全漏洞
> - 已通知主管機關
> - 已加強監控措施
> 
> ## 建議您採取的行動
> - 警惕釣魚郵件 (我們不會要求您提供密碼)
> - 如收到可疑訊息,請通知我們
> - 考慮變更密碼
> 
> ## 聯絡我們
> 如有疑問: security@example.com
> 
> 我們深感抱歉,並承諾持續改善安全措施。
> ```
>
> **階段 5: 復原與改善 (T+7天 ~ T+30天)**
>
> **Post-Incident Review (事後檢討)**:
> 1. **Root Cause Analysis (根因分析)**
>    - 5 Whys 方法找出根本原因
>    - 技術漏洞分析
>    - 流程缺失檢討
>
> 2. **改善行動計畫**
>    ```yaml
>    action_plan:
>      - action: "修補 SQL Injection 漏洞"
>        owner: "Dev Team Lead"
>        deadline: "2024-03-20"
>        status: "completed"
>      
>      - action: "實施 Rate Limiting"
>        owner: "DevOps Engineer"
>        deadline: "2024-03-25"
>        status: "in_progress"
>      
>      - action: "員工安全訓練"
>        owner: "CISO"
>        deadline: "2024-04-15"
>        status: "planned"
>    ```
>
> 3. **更新應變計畫** (從此次事件學習)
>
> **應變團隊聯絡清單範本**:
> ```yaml
> incident_response_team:
>   core_team:
>     - role: "CISO (Chief Information Security Officer)"
>       name: "張安全"
>       phone: "+886-912-345-678"
>       email: "ciso@example.com"
>     
>     - role: "Legal Counsel"
>       name: "李法務"
>       phone: "+886-912-345-679"
>       email: "legal@example.com"
>     
>     - role: "DPO (Data Protection Officer)"
>       name: "王隱私"
>       phone: "+886-912-345-680"
>       email: "dpo@example.com"
>     
>     - role: "PR Manager"
>       name: "陳公關"
>       phone: "+886-912-345-681"
>       email: "pr@example.com"
>   
>   external_contacts:
>     - name: "資安顧問公司"
>       phone: "+886-2-xxxx-xxxx"
>     - name: "律師事務所"
>       phone: "+886-2-yyyy-yyyy"
> ```

- [ ] 資料外洩應變計畫
```

**產出**:
- Compliance Implementation Evidence
- Privacy Policy Document
- Cookie Policy Document
- DSAR Process Documentation

---

### 階段 4：安全測試與驗證（1-3 天）

#### 步驟 4.1: 安全測試執行
**負責 Agent**: QA-Lead + Security-Engineer
**人機協作點**: 🔴 確認測試範圍和方法

**執行內容**:
1. **SAST** (Static Application Security Testing)
   - 靜態代碼分析
   - 檢查 OWASP Top 10
2. **DAST** (Dynamic Application Security Testing)
   - 黑箱測試
   - 漏洞掃描（OWASP ZAP / Burp Suite）
3. **滲透測試** (Penetration Testing) - 如預算允許
   - 模擬攻擊者行為
   - 驗證防禦措施有效性
4. **合規性測試**
   - 驗證所有合規檢查項目

> **⚠️ 滲透測試廠商評估標準 (Penetration Testing Vendor Selection)**
>
> 若選擇外包滲透測試,需審慎評估廠商能力和信譽:
>
> **基本資格檢查**:
> - [ ] **認證資格**: 是否持有 OSCP, CEH, GPEN, CREST 等國際認證?
> - [ ] **產業經驗**: 是否有類似產業 (金融/醫療/電商) 測試經驗?
> - [ ] **測試範圍**: 能否涵蓋 Web/Mobile/API/IoT/Cloud 等所需範圍?
> - [ ] **報告品質**: 是否提供詳細的漏洞描述、PoC、修復建議?
> - [ ] **保密協議**: 是否願意簽署 NDA 和資料保密協議?
>
> **評估矩陣**:
> | 評估項目 | 權重 | 評分標準 (1-5 分) | 說明 |
> |---------|------|------------------|------|
> | **技術能力** | 30% | 5=多項國際認證<br>3=部分認證<br>1=無認證 | OSCP/CEH/CREST |
> | **產業經驗** | 25% | 5=5+ 相同產業案例<br>3=2-4 案例<br>1=無經驗 | Case studies |
> | **報告品質** | 20% | 5=Executive + Technical 雙層報告<br>3=基本報告<br>1=簡陋 | 樣本報告審查 |
> | **價格合理性** | 15% | 5=市場價 80-100%<br>3=100-120%<br>1=>150% | 市場行情比對 |
> | **溝通與支援** | 10% | 5=提供修復諮詢<br>3=僅提供報告<br>1=溝通困難 | 售後支援 |
>
> **詢價與比較流程**:
> ```
> 1. 準備 RFP (Request for Proposal)
>    - 系統架構概述
>    - 測試範圍 (IP 範圍、URL、API 端點)
>    - 測試時間窗口
>    - 特殊要求 (如不可測試項目)
>    
> 2. 邀請 3-5 家廠商報價
>    - 國際知名: Synack, Cobalt, HackerOne
>    - 區域廠商: (依所在地)
>    - 獨立顧問: OSCP 認證個人
>    
> 3. 評估與選擇
>    - 計算評估矩陣總分
>    - 檢查客戶推薦信 (References)
>    - 小規模試測 (Pilot Test)
>    
> 4. 簽約與執行
>    - 簽署 NDA 和 MSA (Master Service Agreement)
>    - 明確測試規則 (Rules of Engagement)
>    - 設定緊急聯絡窗口
> ```
>
> **測試規則範本 (Rules of Engagement)**:
> ```yaml
> penetration_test_rules:
>   scope:
>     in_scope:
>       - "https://app.example.com/*"
>       - "https://api.example.com/*"
>       - "iOS/Android App (latest version)"
>     out_of_scope:
>       - "https://admin.example.com" # 內部管理系統
>       - "Third-party integrations" # 第三方服務
>   
>   allowed_methods:
>     - "SQL Injection Testing"
>     - "XSS Testing"
>     - "Authentication Bypass"
>     - "API Fuzzing"
>   
>   forbidden_methods:
>     - "DoS/DDoS attacks"
>     - "Social Engineering"
>     - "Physical intrusion"
>   
>   testing_window:
>     start: "2024-03-01 00:00 UTC"
>     end: "2024-03-07 23:59 UTC"
>     business_hours_only: false
>   
>   emergency_contact:
>     name: "Security Team Lead"
>     phone: "+886-xxx-xxx-xxx"
>     email: "security@example.com"
> ```
>
> **成本參考 (2024 市場行情)**:
> | 測試類型 | 小型專案 | 中型專案 | 大型專案 |
> |---------|---------|---------|---------|
> | Web App 測試 | $3,000-5,000 | $8,000-15,000 | $20,000-50,000 |
> | Mobile App 測試 | $5,000-8,000 | $10,000-20,000 | $25,000-60,000 |
> | API 測試 | $2,000-4,000 | $5,000-10,000 | $15,000-30,000 |
> | Cloud 架構審查 | $5,000-10,000 | $15,000-30,000 | $40,000-80,000 |
> | 完整滲透測試 | $10,000-20,000 | $30,000-60,000 | $80,000-150,000 |
>
> **替代方案 (預算有限時)**:
> - **Bug Bounty 平台**: HackerOne, Bugcrowd (按漏洞付費)
> - **Crowdsourced 測試**: Synack, Cobalt (混合模式)
> - **自動化工具**: OWASP ZAP, Burp Suite Pro (見 P2-6.4)

   - 驗證所有合規檢查項目

**測試範圍（OWASP Top 10 2021）**:
1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

**產出**:
- Security Test Report
- Penetration Test Report（如有）
- Vulnerability Assessment Report

---

#### 步驟 4.2: 修復驗證與復測
**負責 Agent**: Security-Engineer + Dev-Senior
**人機協作點**: 🔴 確認所有 Critical 和 High 漏洞已修復

**執行內容**:
1. 依風險等級修復漏洞
   - Critical: 立即修復（24 小時內）
   - High: 1 週內修復
   - Medium: 1 個月內修復
   - Low: 下次 Sprint 修復
2. 每次修復後復測
3. 驗證修復沒有引入新漏洞

**產出**:
- Remediation Report
- Re-test Results
- Residual Risk Assessment

---

### 階段 5：文檔與交付（0.5-1 天）

#### 步驟 5.1: 產出安全與合規文檔
**負責 Agent**: Security-Engineer + Compliance-Officer + Technical-Writer
**人機協作點**: 🔴 確認文檔完整性

**執行內容**:
1. 整合所有安全評估報告
2. 產出最終合規報告
3. 產出安全操作手冊（Security Runbook）
4. 產出事件應變計畫（Incident Response Plan）
5. 產出稽核證據包（Audit Evidence Package）

**🚨 安全事件回應流程 (Security Incident Response Process)**：

> 當安全事件發生時，依以下流程執行

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 偵測與通報 (Detection & Reporting) - 15 分鐘內   │
├─────────────────────────────────────────────────────────────┤
│ 1. 確認事件真實性（排除誤報）                              │
│ 2. 初步分類嚴重程度 (P1-P4)                                │
│ 3. 通報緊急聯絡人                                          │
│ 4. 開立事件單 (Incident Ticket)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 遏制 (Containment) - 1 小時內                    │
├─────────────────────────────────────────────────────────────┤
│ 1. 隔離受影響系統                                          │
│ 2. 阻斷攻擊來源 (IP/帳號)                                  │
│ 3. 保留證據 (日誌、記憶體快照)                             │
│ 4. 啟動備援機制 (如適用)                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 根除與復原 (Eradication & Recovery)              │
├─────────────────────────────────────────────────────────────┤
│ 1. 識別根本原因 (Root Cause)                               │
│ 2. 移除惡意程式/修補漏洞                                   │
│ 3. 重置受影響帳號                                          │
│ 4. 還原系統至安全狀態                                      │
│ 5. 驗證系統正常運作                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: 事後檢討 (Post-Incident Review) - 72 小時內      │
├─────────────────────────────────────────────────────────────┤
│ 1. 撰寫事件報告 (5W1H)                                     │
│ 2. 識別改進項目                                            │
│ 3. 更新安全控制措施                                        │
│ 4. 分享 Lessons Learned                                    │
└─────────────────────────────────────────────────────────────┘
```

**嚴重程度分類**：

| 等級 | 定義 | 回應時間 | 通報層級 |
|------|------|---------|---------|
| **P1** | 資料外洩/服務中斷 | 15 分鐘 | CTO + 法務 |
| **P2** | 高風險漏洞被利用 | 1 小時 | Tech Lead + 資安 |
| **P3** | 可疑活動/未遂攻擊 | 4 小時 | 資安團隊 |
| **P4** | 低風險/資訊性事件 | 24 小時 | 記錄追蹤 |

**最終交付文檔清單**:
```markdown
## 安全文檔
- [ ] Security Assessment Report（安全評估報告）
- [ ] Threat Model（威脅模型）
- [ ] Security Requirements Document（安全需求文件）
- [ ] Security Architecture Diagram（安全架構圖）
- [ ] Security Test Report（安全測試報告）
- [ ] Vulnerability Scan Report（漏洞掃描報告）
- [ ] Remediation Plan（修復計畫）
- [ ] Residual Risk Assessment（殘餘風險評估）
- [ ] Security Runbook（安全操作手冊）
- [ ] Incident Response Plan（事件應變計畫）

## 合規文檔
- [ ] Compliance Gap Analysis Report（合規差距分析）
- [ ] Compliance Checklist（合規檢查清單）
- [ ] Compliance Report（合規報告）
- [ ] Privacy Policy（隱私政策）
- [ ] Cookie Policy（Cookie 政策）
- [ ] Data Processing Record (ROPA)（資料處理記錄）
- [ ] DSAR Process Documentation（資料主體存取請求流程）
- [ ] Audit Evidence Package（稽核證據包）
```

**產出**:
- 完整的安全與合規文檔包

---

#### 步驟 5.2: 安全知識轉移
**負責 Agent**: Security-Engineer + Technical-Writer
**人機協作點**: 🔴 確認團隊理解安全實踐

**執行內容**:
1. 對開發團隊進行安全培訓
2. 交付安全開發指南（Secure Coding Guidelines）
3. 交付安全配置基線（Security Configuration Baseline）
4. 建立安全問題回報機制

**產出**:
- Security Training Materials
- Secure Coding Guidelines
- Security Configuration Baseline
- Security Contact List

---

## 📊 情境特定檢查清單

### 啟動前檢查

- [ ] 確認適用的合規標準（GDPR / HIPAA / PCI-DSS 等）
- [ ] 確認評估範圍（系統邊界、資料類型）
- [ ] 確認專案敏感度等級（Public / Internal / Confidential / Restricted）
- [ ] 確認預算和時程（是否允許滲透測試）
- [ ] 確認是否有現成的安全基線可參考

### 執行中檢查

- [ ] 威脅模型已完成並經過 review
- [ ] 所有 Critical 和 High 風險威脅都有對應控制措施
- [ ] 安全需求已納入 Sprint Backlog
- [ ] SAST/DAST 工具已整合到 CI/CD
- [ ] 所有敏感資料已識別並分類
- [ ] 加密機制已實施並測試
- [ ] 存取控制已實施並測試
- [ ] 日誌和監控已配置

### 交付前檢查

- [ ] 所有 Critical 漏洞已修復（100%）
- [ ] 所有 High 漏洞已修復或有緩解措施（90%+）
- [ ] 合規檢查清單完成度達標（依標準要求，通常 95%+）
- [ ] 安全測試報告已產出
- [ ] 合規報告已產出
- [ ] 殘餘風險已評估並經過批准
- [ ] 安全文檔已交付
- [ ] 事件應變計畫已建立

---

## ⚠️ 常見陷阱與注意事項

### 陷阱 1: 過度依賴自動化工具
**問題**: 自動掃描工具有誤報和漏報
**解決**: 結合手動 Code Review 和專家判斷

### 陷阱 2: 忽略第三方依賴
**問題**: 80% 的代碼來自第三方套件，但常被忽略
**解決**: 定期執行 dependency audit，訂閱安全公告

### 陷阱 3: 合規形式主義
**問題**: 只做文檔不做實質改善
**解決**: 將合規要求轉化為可驗證的技術需求

### 陷阱 4: 安全與可用性衝突
**問題**: 過度的安全措施影響使用者體驗
**解決**: 平衡安全性和可用性，風險導向決策

### 陷阱 5: 缺乏持續性
**問題**: 一次性評估，後續沒有追蹤
**解決**: 建立持續安全監控機制，定期 re-assessment

---

## 📚 實際案例走查

### 案例 1：OWASP Top 10 漏洞修復專案

#### 背景
某電商平台在安全稽核中發現多個 OWASP Top 10 漏洞（SQL Injection、XSS、不安全的反序列化），需要在 4 週內完成修復並通過複查。

#### 挑戰
- ❌ **遺留代碼問題**：10 年老系統，缺少輸入驗證和參數化查詢
- ❌ **測試覆蓋不足**：安全測試覆蓋率 < 20%
- ❌ **時程壓力**：4 週內需完成修復
- ❌ **知識缺口**：團隊對安全最佳實踐不熟悉

#### 執行步驟

**Week 1：漏洞掃描與優先級排序**
```
載入 AISDLC_INIT.md
→ 執行 OWASP ZAP 自動掃描
→ Security-Engineer 分析報告
→ 🔴 確認風險評分矩陣
→ 產出：67 個漏洞清單（14 Critical、23 High、30 Medium）
→ 優先修復：Critical + High (37 個)
```

**Week 2-3：分類修復**
```
SQL Injection 修復 (9 個):
- 所有資料庫查詢改用參數化查詢 (Prepared Statements)
- 使用 ORM (Sequelize/TypeORM) 避免手寫 SQL
- 補充輸入驗證 (Joi/Yup)

XSS 修復 (12 個):
- 前端使用 DOMPurify 清理使用者輸入
- React 改用 dangerouslySetInnerHTML 的安全替代方案
- 啟用 Content-Security-Policy (CSP)

不安全的反序列化 (6 個):
- 移除 eval() 和 Function() 動態執行
- JSON 資料驗證 Schema
- 改用安全的序列化函式庫
```

**Week 4：驗證與複查**
```
安全測試:
- OWASP ZAP 重新掃描：0 Critical、2 High (已修復 95%)
- Burp Suite 手動滲透測試
- 補充安全單元測試 (覆蓋率 65% → 85%)

複查結果:
✅ 所有 Critical 漏洞已修復
✅ High 漏洞剩餘 2 個 (計畫下個 Sprint 修復)
✅ 安全測試通過
```

#### 關鍵成果
- ✅ **漏洞修復率**：Critical 100%、High 91%
- ✅ **安全測試覆蓋率**：20% → 85%
- ✅ **知識提升**：團隊完成 OWASP 安全培訓
- ✅ **流程建立**：導入 Snyk 自動化漏洞掃描至 CI/CD

#### 經驗教訓
1. **分類修復效率高**：依漏洞類型分類，套用統一修復模式
2. **自動化工具必備**：OWASP ZAP + Snyk 節省 60% 人工掃描時間
3. **測試先行**：先補充安全測試，再重構（避免引入新問題）
4. **知識傳承**：建立 Security Playbook，未來類似問題 2 天修復

---

### 案例 2：GDPR 合規改造專案

#### 背景
SaaS 平台需符合 GDPR 要求以拓展歐盟市場，涉及資料保護、使用者同意、資料可攜性、被遺忘權等。

#### 挑戰
- ❌ **個資散落**：使用者資料分散 12 個資料表
- ❌ **缺少同意機制**：無明確的使用者同意記錄
- ❌ **日誌不完整**：無法追溯資料存取歷史
- ❌ **刪除機制缺失**：無資料刪除/匿名化流程

#### 執行步驟

**階段 1：資料盤點與分類 (2 週)**
```
載入 AISDLC_INIT.md + Compliance-Officer
→ 盤點所有個資欄位 (姓名、Email、電話、地址、IP、Cookie)
→ 資料流向分析 (12 個資料表 + 5 個第三方服務)
→ 🔴 確認資料分類矩陣
→ 產出：個資地圖 (Data Inventory Map)

資料分類:
- 基本個資 (Basic PII): 姓名、Email、電話
- 敏感個資 (Sensitive PII): 付款資訊、健康資料
- 技術資料: IP 位址、Cookie、Session ID
```

**階段 2：同意機制建立 (2 週)**
```
實作功能:
1. Cookie Banner (必要/分析/行銷 分類)
   - 使用 Cookie Consent Library
   - 整合 Google Consent Mode v2

2. 隱私權設定頁面
   - 使用者可查看/修改同意項目
   - 同意歷史記錄 (Consent Audit Log)

3. 資料處理同意
   - Newsletter 訂閱: Opt-in (明確同意)
   - 第三方分享: 明確告知並取得同意
```

**階段 3：使用者權利實作 (3 週)**
```
1. 資料可攜性 (Right to Data Portability)
   - 實作「匯出我的資料」功能
   - JSON/CSV 格式下載
   - 包含所有個資 (12 個資料表整合)

2. 被遺忘權 (Right to Erasure)
   - 「刪除我的帳號」功能
   - 30 天冷靜期 (Soft Delete)
   - 30 天後永久刪除或匿名化
   - Cascade Delete (關聯資料一併處理)

3. 存取權 (Right of Access)
   - 「查看我的資料」功能
   - 展示所有收集的個資

4. 更正權 (Right to Rectification)
   - 個資設定頁面可修改
```

**階段 4：技術措施強化 (2 週)**
```
1. 加密強化
   - Database 加密: Transparent Data Encryption (TDE)
   - 敏感欄位欄位級加密 (Field-level Encryption)
   - 傳輸加密: 強制 HTTPS (HSTS)

2. 存取控制
   - RBAC (Role-Based Access Control)
   - 個資存取需 2FA 驗證
   - 稽核日誌 (Audit Log): 誰、何時、存取了哪些個資

3. 資料保留政策
   - 自動刪除 3 年未登入使用者資料
   - Backup 保留期限: 30 天
```

**階段 5：流程與文件 (1 週)**
```
建立文件:
1. 隱私權政策 (Privacy Policy)
2. Cookie 政策 (Cookie Policy)
3. 資料處理協議 (Data Processing Agreement)
4. 資料外洩應變計畫 (Data Breach Response Plan)

建立流程:
1. DPIA (Data Protection Impact Assessment) 模板
2. 個資事件通報流程 (72 小時內通報)
3. DPO (Data Protection Officer) 聯絡機制
```

#### 關鍵成果
- ✅ **GDPR 合規性**：通過外部顧問稽核
- ✅ **使用者信任**：透明化資料處理，使用者滿意度 +15%
- ✅ **技術改善**：加密、存取控制、稽核日誌完整
- ✅ **法務風險降低**：避免 GDPR 罰款（最高營收 4%）

#### 時程與成本
- **總時程**：10 週
- **人力**：2 後端工程師 + 1 前端工程師 + 1 法務顧問
- **成本**：約 $50k (工程師薪資 + 法務顧問費)
- **ROI**：避免潛在罰款（數百萬美元）+ 符合歐盟市場准入要求

#### 經驗教訓
1. **資料盤點是基礎**：清楚知道個資在哪，才能有效保護
2. **使用者體驗很重要**：Cookie Banner、隱私設定介面需易用
3. **技術 + 流程並重**：不只實作功能，流程文件同等重要
4. **持續監控**：GDPR 合規是持續過程，需定期稽核

---

## 🔗 相關資源

### Workflows
- [security-assessment-flow.md](../../workflow/scenario-specific/security-assessment-flow.md) - Security 專屬 Workflow
- [consistency-check.md](../../workflow/core/consistency-check.md)
- [api-specification.md](../../workflow/core/api-specification.md)
- [interaction-analysis.md](../../workflow/core/interaction-analysis.md)
- [testing-strategy-flow.md](../../workflow/scenario-specific/testing-strategy-flow.md) - 安全測試案例設計（Stage 4 安全測試規劃）
- [sprint-execution.md](../../workflow/core/sprint-execution.md) - 修復實施追蹤（Stage 3 安全修復 Sprint 管理）

### 相關 Agents

**Primary Agents（主要負責）**:
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - 安全工程師（主導安全評估與設計）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - 合規專員（法規解讀與稽核準備）

**Supporting Agents（按需載入）**:
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（安全測試策略）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（威脅建模資料流圖）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（安全架構設計）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - 資深開發（安全加固實施）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（安全 CI/CD Pipeline）

**Optional Agents（選用）**:
- [02.ba-business-analyst-zh.yaml](../../agent/core/02.ba-business-analyst-zh.yaml) - Beatrice（業務合規需求分析）
- [03.pm-po-agent-zh.yaml](../../agent/core/03.pm-po-agent-zh.yaml) - Victoria（安全預算與優先級決策）
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - 技術文檔（安全文檔撰寫）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - 行動端架構（Android/iOS/macOS 安全）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端安全測試）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（跨瀏覽器安全測試、XSS/CSRF 驗證）
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - 整合專家（支付安全/Webhook 驗證/OAuth 安全設計）— **電商/支付系統必載**

### 相關 Skills

- `/security-audit` - OWASP Top 10 安全審計（觸發 Security-Engineer）
- `/compliance-audit` - GDPR/PCI-DSS/SOC2/ISO 27001 合規審查
- `/sd-architect` - 安全架構設計（Zero Trust、加密策略）
- `/code-review` - 安全程式碼審查（漏洞檢測）
- `/qa-testing` - 安全測試策略與案例設計
- `/testing-strategy` - 安全測試金字塔設計
- `/integration-oauth` - OAuth 2.0/OIDC 認證整合
- `/integration-database` - 資料庫安全配置（PostgreSQL 加密、RLS）
- `/integration-redis` - Session/Token 安全快取策略
- `/devops-github-actions` - 安全 CI/CD Pipeline（SAST/DAST/SCA）
- `/devops-docker` - 容器安全（Golden Image、Trivy 掃描）
- `/devops-monitoring` - 安全事件監控與告警
- `/performance-optimization` - 安全措施效能影響評估
- `/mobile-development` - 行動端安全（Android Keystore、macOS Keychain、QR 碼簽章驗證）
- `/integration-stripe` - 支付安全（Stripe.js Tokenization、PCI-DSS 合規、不儲存 CVV）
- `/integration-webhook` - Stripe Webhook 簽章驗證（防偽造支付成功回調）

### 文檔模板
- [STRIDE_Threat_Analysis_Template.md](../../docs_template/support/STRIDE_Threat_Analysis_Template.md)
- [Security_Requirements_Checklist.md](../../docs_template/support/Security_Requirements_Checklist.md)
- Security_Assessment_Template.md（模板規劃中，v0.01+）
- Compliance_Report_Template.md（模板規劃中，v0.01+）

### Prompts
- [security-prompts.md](../../prompts/scenario-prompts/security-prompts.md)

---

## 📈 成功指標

### 安全性指標
- ✅ Critical 漏洞數量: 0
- ✅ High 漏洞數量: ≤ 5（有緩解措施）
- ✅ 敏感資料加密率: 100%
- ✅ 認證覆蓋率: 100%（所有 API 端點）
- ✅ 日誌覆蓋率: 100%（所有安全事件）

### 合規性指標
- ✅ 合規檢查項完成度: ≥ 95%
- ✅ 稽核發現（Findings）數量: ≤ 10（Minor）
- ✅ 資料主體權利回應時間: ≤ 30 天
- ✅ 資料外洩通知時效: ≤ 72 小時

### 流程指標
- ✅ 安全評估完成時間: ≤ 2 天
- ✅ Critical 漏洞修復時間: ≤ 24 小時
- ✅ High 漏洞修復時間: ≤ 7 天
- ✅ 文檔完整度: 100%

---

## 📞 支援與協助

### 疑難排解
參考：[troubleshooting-quick-guide.md](../../prompts/quick-start/troubleshooting-quick-guide.md)

### 常見問題
參考：[security-prompts.md](../../prompts/scenario-prompts/security-prompts.md) 中的 FAQ 章節

### 外部資源
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)

---

**版本歷史**:
- v0.02 (2025-10-22): 初版發布，Security & Compliance 情境完整 SOP
