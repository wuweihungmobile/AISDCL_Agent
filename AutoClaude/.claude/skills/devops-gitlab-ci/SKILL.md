---
name: devops-gitlab
description: 建立 GitLab CI/CD Pipeline，包含構建、測試、部署階段
user-invocable: true
disable-model-invocation: false
argument-hint: "<project_type: 專案類型 (nodejs/python/java/go/dotnet)> [deploy_target: 部署目標 (docker/k8s/vm/serverless)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# DevOps GitLab CI/CD Skill

建立完整的 GitLab CI/CD Pipeline。

---

## 觸發方式

```bash
/devops-gitlab nodejs           # Node.js 專案
/devops-gitlab python k8s       # Python + K8s 部署
/devops-gitlab --project_type=java --deploy_target=docker
```

---

## 執行流程

### 階段 1: 專案評估 🔴

**確認項目**:
- [ ] 專案類型和語言版本
- [ ] 構建工具 (npm/yarn/maven/gradle)
- [ ] 測試框架
- [ ] 部署目標環境
- [ ] 環境變數和 Secrets

🔴 **確認點**: 確認以上配置需求

---

### 階段 2: Pipeline 配置

**.gitlab-ci.yml 基本結構**:

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - security
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

# 快取設定
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/

# 構建階段
build:
  stage: build
  image: node:20-alpine
  script:
    - npm ci --cache .npm
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 hour

# 測試階段
test:unit:
  stage: test
  image: node:20-alpine
  script:
    - npm ci --cache .npm
    - npm run test:unit -- --coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      junit: junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml

test:e2e:
  stage: test
  image: cypress/browsers:latest
  script:
    - npm ci
    - npm run test:e2e
  artifacts:
    when: on_failure
    paths:
      - cypress/screenshots/
      - cypress/videos/

# 安全掃描
security:sast:
  stage: security
  include:
    - template: Security/SAST.gitlab-ci.yml

security:dependency:
  stage: security
  image: node:20-alpine
  script:
    - npm audit --audit-level=high
  allow_failure: true

# 部署階段
deploy:staging:
  stage: deploy
  environment:
    name: staging
    url: https://staging.example.com
  script:
    - echo "Deploying to staging..."
  only:
    - develop
  when: manual

deploy:production:
  stage: deploy
  environment:
    name: production
    url: https://example.com
  script:
    - echo "Deploying to production..."
  only:
    - main
  when: manual
```

#### Java/Spring Boot 專案
```yaml
# .gitlab-ci.yml (Spring Boot)
stages:
  - build
  - test
  - security
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .gradle/

build:
  stage: build
  image: eclipse-temurin:21-jdk-alpine
  script:
    - chmod +x gradlew
    - ./gradlew bootJar
  artifacts:
    paths:
      - build/libs/*.jar
    expire_in: 1 hour

test:unit:
  stage: test
  image: eclipse-temurin:21-jdk-alpine
  services:
    - postgres:18-alpine
  variables:
    POSTGRES_DB: testdb
    POSTGRES_USER: testuser
    POSTGRES_PASSWORD: testpass
    SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/testdb
  script:
    - chmod +x gradlew
    - ./gradlew test jacocoTestReport
  artifacts:
    reports:
      junit: build/test-results/test/*.xml
    paths:
      - build/reports/jacoco/

security:dependency:
  stage: security
  image: eclipse-temurin:21-jdk-alpine
  script:
    - chmod +x gradlew
    - ./gradlew dependencyCheckAnalyze
  allow_failure: true

deploy:staging:
  stage: deploy
  environment:
    name: staging
  script:
    - echo "Deploying Spring Boot to staging..."
  only:
    - develop
  when: manual
```

---

### 階段 3: Docker 構建配置

```yaml
# Docker 構建和推送
build:docker:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $DOCKER_IMAGE .
    - docker push $DOCKER_IMAGE
  only:
    - main
    - develop
```

---

### 階段 4: 環境配置

**GitLab CI/CD 變數設定**:

| 變數名稱 | 範圍 | 說明 |
|---------|------|------|
| `CI_REGISTRY_*` | 內建 | Container Registry |
| `DEPLOY_TOKEN` | Protected | 部署憑證 |
| `DATABASE_URL` | Environment | 資料庫連線 |

**環境保護規則**:
```yaml
deploy:production:
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: manual
    - when: never
  environment:
    name: production
    deployment_tier: production
```

---

### 階段 5: 驗證 🔴

**驗證清單**:
- [ ] Pipeline 語法正確 (`gitlab-ci-lint`)
- [ ] 所有 Stage 正常執行
- [ ] Artifacts 正確產出
- [ ] 環境變數正確注入
- [ ] 部署成功完成

🔴 **確認點**: 確認 Pipeline 運行正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| GitLab CI 配置 | `.gitlab-ci.yml` |
| 部署腳本 | `scripts/deploy.sh` |

---

## 相關 Skill

- `/devops-github` - GitHub Actions
- `/devops-k8s` - Kubernetes 部署
- `/devops-docker` - Docker 容器化

---


## 相關檔案

- SOP 參考: `scenarios/devops/SOP_QuickRef.md`

**基於**: AISDLC v0.09 DevOps 情境
