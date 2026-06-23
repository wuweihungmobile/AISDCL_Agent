---
name: devops-gitlab-ci
description: 建立 GitLab CI/CD Pipeline，嵌入 Contract 一致性驗證 Stage，對應 SDD_TESTING_CICD 規格
user-invocable: true
disable-model-invocation: false
argument-hint: "<project_type: nodejs|python|java|go|dotnet> [deploy_target: aws|gcp|azure|docker|k8s]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# DevOps GitLab CI/CD Skill（SDD 原生）

CI/CD Pipeline 是 SDD 自動化閘門的執行者。本 Skill 在 GitLab Pipeline 中嵌入 Contract 一致性驗證、RTM 覆蓋率檢查，對應 `cicd/SDD_TESTING_CICD.md` 規格。

---

## 觸發方式

```bash
/devops-gitlab-ci nodejs docker
/devops-gitlab-ci python k8s
/devops-gitlab-ci java aws
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
- `docs/02_architecture/api/CONTRACT-*.yaml`（Pipeline Contract 驗證 Stage 依據）
- `docs/02_architecture/SRD-{System}.md`（部署架構）
- `cicd/SDD_TESTING_CICD.md`（SDD CI/CD 規格）

---

### 階段 2：GitLab CI/CD Pipeline 產出

**存放路徑**：`.gitlab-ci.yml`

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - contract-validation
  - integration
  - security
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/

# ============================================
# Stage 1: 代碼品質檢查
# ============================================
lint-and-type-check:
  stage: lint
  image: node:20-alpine
  script:
    - {install command}
    - {lint command}
    - {type-check command}

# ============================================
# Stage 2: 單元測試
# ============================================
unit-tests:
  stage: test
  image: node:20-alpine
  script:
    - {install}
    - {test command} --coverage
    - |
      COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
      if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo "Coverage $COVERAGE% < 80% (NFR-XXX 要求)"
        exit 1
      fi
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
  needs:
    - lint-and-type-check

# ============================================
# Stage 3: Contract 一致性驗證（SDD 核心）
# ============================================
contract-validation:
  stage: contract-validation
  image: node:20-alpine
  script:
    # 使用 spectral 驗證實作與 Contract 一致
    - npx @stoplight/spectral-cli lint docs/02_architecture/api/CONTRACT-*.yaml
    # 執行 Contract Tests（Pact 或等效工具）
    - {contract test command}
    # 凍結保護：Contract 被修改則 Pipeline 失敗（需重走 SCG-3）
    - |
      git diff HEAD~1 docs/02_architecture/api/CONTRACT-*.yaml
      if git diff --name-only HEAD~1 | grep -q 'CONTRACT-'; then
        echo "ERROR: Contract 被修改，需重新執行 SCG-3 凍結程序"
        exit 1
      fi
  needs:
    - unit-tests

# ============================================
# Stage 4: 整合測試
# ============================================
integration-tests:
  stage: integration
  image: node:20-alpine
  services:
    - name: {db-image}
      alias: db
  variables:
    {DB_ENV_VARS}
  script:
    - {install}
    - {integration test command}
  needs:
    - contract-validation

# ============================================
# Stage 5: 安全掃描（SCG-4 條件）
# ============================================
security-dependency:
  stage: security
  script:
    - {audit command}  # npm audit / safety check / trivy
  needs:
    - unit-tests

include:
  - template: Security/SAST.gitlab-ci.yml

# ============================================
# Stage 6: 部署（SCG-3 通過後才執行 Production 部署）
# ============================================
deploy-staging:
  stage: deploy
  environment:
    name: staging
    url: https://staging.{project}.com
  script:
    - {staging deploy command}
  rules:
    - if: $CI_COMMIT_BRANCH == "develop"
  needs:
    - integration-tests
    - security-dependency

deploy-production:
  stage: deploy
  environment:
    name: production
    url: https://{project}.com
    deployment_tier: production
  script:
    - {production deploy command}
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: manual  # 需要手動 Approve（SCG-6 人工確認）
    - when: never
  needs:
    - deploy-staging
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

🔴 確認點：Contract Validation Stage 對應的是 SCG-3 凍結的 Contract 版本。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| GitLab CI Pipeline 配置 | `.gitlab-ci.yml` | SCG-3 後 |
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

**基於**: AISDLC-SDD v0.20
**對應 CI/CD 規格**: `cicd/SDD_TESTING_CICD.md`
