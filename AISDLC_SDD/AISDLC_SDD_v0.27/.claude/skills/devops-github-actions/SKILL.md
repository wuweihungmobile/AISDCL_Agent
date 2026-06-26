---
name: devops-github-actions
description: 建立 GitHub Actions CI/CD Pipeline，嵌入 Contract 一致性驗證 Step，對應 SDD_TESTING_CICD 規格
user-invocable: true
disable-model-invocation: false
argument-hint: "<project_type: nodejs|python|java|go|dotnet> [deploy_target: aws|gcp|azure|vercel|docker]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# DevOps GitHub Actions Skill（SDD 原生）

CI/CD Pipeline 是 SDD 自動化閘門的執行者。本 Skill 在 Pipeline 中嵌入 Contract 一致性驗證、RTM 覆蓋率檢查，對應 `cicd/SDD_TESTING_CICD.md` 規格。

---

## 觸發方式

```bash
/devops-github-actions nodejs aws
/devops-github-actions python docker
/devops-github-actions java gcp
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | API Contract 已凍結 | `docs/02_architecture/api/CONTRACT-*.yaml` 存在 |
| SRD 部署架構章節存在 | 部署策略已有 ADR 支撐 | `docs/02_architecture/SRD-{System}.md` 第 8 章 |

---

## 執行流程

### 階段 1：讀取規格依據

讀取：
- `docs/02_architecture/api/CONTRACT-*.yaml`（Pipeline Contract 驗證 Step 依據）
- `docs/02_architecture/SRD-{System}.md`（部署架構）
- `cicd/SDD_TESTING_CICD.md`（SDD CI/CD 規格）

---

### 階段 2：GitHub Actions Workflow 產出

**存放路徑**：`.github/workflows/`

```yaml
# .github/workflows/ci.yml
name: SDD CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # ============================================
  # Stage 1: 代碼品質檢查
  # ============================================
  lint-and-type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup {language}
        uses: actions/setup-{language}@v4
        with:
          {language}-version: '{version}'
      - run: {install command}
      - run: {lint command}
      - run: {type-check command}

  # ============================================
  # Stage 2: 單元測試
  # ============================================
  unit-tests:
    runs-on: ubuntu-latest
    needs: lint-and-type-check
    steps:
      - uses: actions/checkout@v4
      - run: {install}
      - run: {test command} --coverage
      - name: Enforce Coverage ≥ 80%（NFR 要求）
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% < 80% (NFR-XXX 要求)"
            exit 1
          fi

  # ============================================
  # Stage 3: Contract 一致性驗證（SDD 核心）
  # ============================================
  contract-validation:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Validate API Contract（SCG-3 凍結版本）
        run: |
          # 使用 spectral 或 openapi-validator 驗證實作與 Contract 一致
          npx @stoplight/spectral-cli lint docs/02_architecture/api/CONTRACT-*.yaml
      - name: Run Contract Tests（Pact 或等效工具）
        run: {contract test command}
      - name: Check Contract Version Not Changed（凍結保護）
        run: |
          git diff HEAD~1 docs/02_architecture/api/CONTRACT-*.yaml
          # 若 Contract 被修改，Pipeline 失敗（需重走 SCG-3）

  # ============================================
  # Stage 4: 整合測試
  # ============================================
  integration-tests:
    runs-on: ubuntu-latest
    needs: contract-validation
    services:
      db:
        image: {db-image}
        env:
          {DB_ENV_VARS}
    steps:
      - uses: actions/checkout@v4
      - run: {install}
      - run: {integration test command}

  # ============================================
  # Stage 5: 安全掃描（SCG-4 條件）
  # ============================================
  security-scan:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - name: Dependency Vulnerability Scan
        run: {audit command}  # npm audit / safety check / trivy
      - name: SAST Scan
        uses: github/codeql-action/analyze@v3

  # ============================================
  # Stage 6: 部署（SCG-3 通過後才執行 Production 部署）
  # ============================================
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [integration-tests, security-scan]
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to Staging
        run: {staging deploy command}

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment: production  # 需要手動 Approve（SCG-6 人工確認）
    steps:
      - name: Deploy to Production
        run: {production deploy command}
```

---

### 階段 3：SDD ADR 補充（若部署策略有新決策）

若 Pipeline 引入新的部署決策（如 Canary / Blue-Green），呼叫 `/adr-generate`。

---

### 階段 4：RTM 更新與文件存放 🔴

Pipeline 配置存入：`docs/08_deployment/CI-CD-PIPELINE-{System}.md`（說明 Pipeline 設計決策）

```bash
/rtm-generate update    # 更新 CI/CD 相關部署驗收 TC 狀態
/spec-compliance-check docs/08_deployment/CI-CD-PIPELINE-{System}.md
```

🔴 確認點：Contract Validation Step 對應的是 SCG-3 凍結的 Contract 版本。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| GitHub Actions Workflow | `.github/workflows/ci.yml` | SCG-3 後 |
| Pipeline 設計說明 | `docs/08_deployment/CI-CD-PIPELINE-{System}.md` | SCG-3 後 |

---

## 後置動作

```
/sdd-gate SCG-4    # Pipeline 設置完成，可開始 PR Review
```

🔷 **本 Skill 協助通過**：SCG-4（透過 CI Pipeline 自動驗證 Contract 一致性）

---

## 相關 Skill

- `/contract-generate` — API Contract（Pipeline Contract 驗證的依據）
- `/devops-docker` — Docker 配置（Pipeline 使用）
- `/devops-kubernetes` — K8s 部署（Pipeline 觸發）
- `/sdd-gate SCG-3` — 必須通過後才建立 Pipeline

---

**基於**: AISDLC-SDD v0.27
**對應 CI/CD 規格**: `cicd/SDD_TESTING_CICD.md`
