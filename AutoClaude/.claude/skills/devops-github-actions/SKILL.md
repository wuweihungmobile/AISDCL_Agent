---
name: devops-github
description: 建立完整的 GitHub Actions CI/CD Pipeline，包含構建、測試、部署
user-invocable: true
disable-model-invocation: false
argument-hint: "<project_type: 專案類型 (nodejs/python/java/go/dotnet)> [deploy_target: 部署目標 (aws/gcp/azure/vercel/docker)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# DevOps GitHub Actions Skill

基於 AISDLC DevOps 情境的 GitHub Actions CI/CD 建置技能。

---

## 觸發方式

```bash
/devops-github nodejs aws
/devops-github python docker
/devops-github --project_type=nodejs --deploy_target=vercel
```

---

## 執行流程

### 階段 1: 現狀評估 🔴

**任務清單**:
1. 分析專案結構，識別：
   - 套件管理器 (npm/yarn/pnpm/pip/maven)
   - 構建命令
   - 測試命令
   - 入口檔案

2. 檢查現有 CI/CD 配置：
   - `.github/workflows/` 是否存在
   - 現有 Pipeline 內容

3. 🔴 **確認點**: 向使用者確認：
   - 專案類型正確嗎？
   - 部署目標正確嗎？
   - 需要哪些環境 (staging/production)?

---

### 階段 2: 工具配置

**依據專案類型選擇範本**:

#### Node.js 專案
```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: '{{package_manager}}'

      - name: Install dependencies
        run: {{install_command}}

      - name: Lint
        run: {{lint_command}}

      - name: Test
        run: {{test_command}}

      - name: Build
        run: {{build_command}}

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # 部署步驟根據 deploy_target 生成
```

#### Python 專案
```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint
        run: |
          pip install flake8
          flake8 .

      - name: Test
        run: pytest --cov
```

#### Java/Spring Boot 專案
```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Setup JDK
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Grant execute permission for gradlew
        run: chmod +x gradlew

      - name: Lint & Static Analysis
        run: ./gradlew checkstyleMain spotbugsMain

      - name: Test
        run: ./gradlew test
        env:
          SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb
          SPRING_DATASOURCE_USERNAME: testuser
          SPRING_DATASOURCE_PASSWORD: testpass

      - name: Build
        run: ./gradlew bootJar

      - name: Upload JAR
        uses: actions/upload-artifact@v4
        with:
          name: app-jar
          path: build/libs/*.jar

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Spring Boot Docker 部署
      - name: Build Docker image (Layered JAR)
        run: |
          ./gradlew bootJar
          docker build -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} .
```

#### Android 專案
```yaml
name: Android CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup JDK
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Grant execute permission
        run: chmod +x gradlew

      - name: Lint
        run: ./gradlew lint

      - name: Unit Tests
        run: ./gradlew testDebugUnitTest

      - name: Build Debug APK
        run: ./gradlew assembleDebug

  build-release:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup JDK
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Decode Keystore
        run: echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > app/release.keystore

      - name: Build Release AAB
        run: ./gradlew bundleRelease
        env:
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}

      - name: Upload to Firebase App Distribution
        uses: wzieba/Firebase-Distribution-Github-Action@v1
        with:
          appId: ${{ secrets.FIREBASE_APP_ID }}
          serviceCredentialsFileContent: ${{ secrets.FIREBASE_CREDENTIALS }}
          groups: testers
          file: app/build/outputs/bundle/release/app-release.aab
```

#### Next.js 專案
```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint & Type Check
        run: |
          npm run lint
          npx tsc --noEmit

      - name: Test
        run: npm test -- --coverage

      - name: Build
        run: npm run build

      - name: Upload build
        uses: actions/upload-artifact@v4
        with:
          name: nextjs-build
          path: .next/
```

---

### 階段 3: CI Pipeline 生成

**產出物**: `.github/workflows/ci.yml`

**必要步驟**:
1. Checkout 代碼
2. 設定運行環境
3. 安裝依賴
4. Lint 檢查
5. 執行測試
6. 構建產物
7. 上傳 Artifact

---

### 階段 4: CD Pipeline 生成

**依據 deploy_target 生成**:

#### AWS 部署
```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-1

    - name: Deploy to AWS
      run: |
        # 根據專案類型選擇部署方式
        # ECS / Lambda / S3 等
```

#### Docker 部署
```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

#### Vercel 部署
```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Deploy to Vercel
      uses: amondnet/vercel-action@v25
      with:
        vercel-token: ${{ secrets.VERCEL_TOKEN }}
        vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
        vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
```

---

### 階段 5: Secret 配置指南

**產出物**: `SECRETS_SETUP.md`

🔴 **確認點**: 提醒使用者設定必要的 GitHub Secrets:

| Secret 名稱 | 用途 | 必要性 |
|------------|------|--------|
| AWS_ACCESS_KEY_ID | AWS 存取金鑰 | AWS 部署必要 |
| AWS_SECRET_ACCESS_KEY | AWS 密鑰 | AWS 部署必要 |
| VERCEL_TOKEN | Vercel 部署 Token | Vercel 部署必要 |
| DOCKER_USERNAME | Docker Hub 帳號 | Docker 部署必要 |
| DOCKER_PASSWORD | Docker Hub 密碼 | Docker 部署必要 |

---

### 階段 6: 驗證與測試

**執行驗證**:
1. 檢查 YAML 語法正確性
2. 模擬 Push 觸發
3. 確認 Workflow 可正常啟動

---

## 產出物清單

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| CI Workflow | `.github/workflows/ci.yml` | 持續整合配置 |
| CD Workflow | `.github/workflows/cd.yml` | 持續部署配置 |
| Secret 指南 | `docs/SECRETS_SETUP.md` | Secret 設定說明 |

---

## 相關 Skill

- `/devops-gitlab` - GitLab CI 版本
- `/devops-k8s` - Kubernetes 部署
- `/testing` - 測試策略

---


## 相關檔案

- SOP 參考: `scenarios/devops/SOP_QuickRef.md`

**基於**: AISDLC v0.09 DevOps 情境
**維護者**: AISDLC Framework Team
