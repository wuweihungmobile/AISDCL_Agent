# AISDLC DevOps/CI/CD 實戰範例：民宿預訂網站

**版本**: v0.01
**最後更新**: 2025-12-16
**情境**: DevOps/CI/CD
**平台**: Web (電子商務)
**技術棧**: Next.js + Spring Boot + PostgreSQL + Google Cloud


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 範例概述

本文檔展示如何使用 **AISDLC-SDD v0.01** 在 **Cursor AI** 環境中，透過 **Claude Code** 為民宿預訂網站建立企業級 DevOps/CI/CD 流程。

**技術棧**:
- **前端**: Next.js 14 + TypeScript + Tailwind CSS
- **後端**: Spring Boot 3.2 + PostgreSQL 15
- **CI/CD**: GitHub Actions + Google Cloud Build
- **部署**: Google Cloud Run + Cloud SQL + Cloud CDN
- **監控**: Google Cloud Monitoring + Sentry + Datadog

---

## 🎯 第一部分：環境設定

### 步驟 1.1: 設定 Cursor AI 專案路徑

```bash
# 創建 Monorepo
mkdir -p ~/projects/BnBBookingDevOps
cd ~/projects/BnBBookingDevOps

# 創建專案結構
mkdir -p frontend backend infrastructure/{terraform,docker,k8s}
mkdir -p .github/workflows scripts/{build,deploy,test}
mkdir -p docs/{devops,deployment,monitoring,runbook}

# 初始化 Git
git init
```

### 步驟 1.2: 安裝設定 AISDLC-SDD v0.01

```bash
cd ~/projects/BnBBookingDevOps
ln -s ~/projects/AISDLC_ALL/AISDLC_v0.09 ./AISDLC
```

**創建 CLAUDE.md**:

```bash
cat > CLAUDE.md << 'EOF'
# BnBBooking DevOps 專案指引

**專案**: 民宿預訂平台 CI/CD
**AISDLC**: v0.01
**情境**: DevOps/CI/CD

## 技術棧
- 前端: Next.js 14 + Vercel/Cloud Run
- 後端: Spring Boot 3.2 + Cloud Run
- 資料庫: Cloud SQL (PostgreSQL)
- CDN: Cloud CDN
- CI/CD: GitHub Actions + Cloud Build

## DevOps 目標
1. 多環境管理 (Dev/Staging/Production)
2. 自動化測試與部署
3. 零停機部署 (Blue-Green)
4. 自動擴展 (Auto-scaling)
5. 全面監控與告警

## AISDLC 路徑
- 框架: `./AISDLC/`
- SOP: `AISDLC/scenarios/devops/SOP.md`
EOF
```

---

## 🚀 第二部分：使用 Claude Code 開發 CI/CD

### 步驟 2.1: 啟動並初始化

💬 **您對 Claude 說**：
```
我要為民宿預訂網站建立企業級 DevOps/CI/CD。

技術棧:
- 前端: Next.js 14
- 後端: Spring Boot 3.2
- 資料庫: Cloud SQL PostgreSQL
- 部署: Google Cloud (Cloud Run)

需求:
- 多環境 (Dev/Staging/Prod)
- 自動化測試 (Unit/Integration/E2E)
- 零停機部署
- 自動擴展
- 完整監控

請執行:
1. 讀取 AISDLC/AISDLC_INIT.md
2. 讀取 AISDLC/scenarios/devops/SOP.md
3. 分析並建議 CI/CD 架構
```

🤖 **Claude 回應**：
```
已讀取 AISDLC DevOps SOP。

建議架構:

【前端 CI/CD】
1. ✅ Lint & Type Check (ESLint, TypeScript)
2. ✅ Unit Tests (Jest, React Testing Library)
3. ✅ Build (Next.js)
4. ✅ E2E Tests (Playwright)
5. ✅ Deploy to Cloud Run
6. ✅ Lighthouse CI (效能檢查)

【後端 CI/CD】
1. ✅ Code Quality (Checkstyle, SpotBugs)
2. ✅ Unit & Integration Tests (JUnit, Testcontainers)
3. ✅ Security Scan (OWASP Dependency Check)
4. ✅ Build Docker Image
5. ✅ Deploy to Cloud Run (Blue-Green)
6. ✅ Smoke Tests

【基礎設施】
1. ✅ Terraform IaC
2. ✅ Cloud SQL 自動備份
3. ✅ Multi-region 部署
4. ✅ CDN 快取策略

請確認需求。
```

---

### 步驟 2.2: 生成 CI/CD Pipeline

**2.2.1 前端 Pipeline**

💬 **您對 Claude 說**：
```
請生成 Next.js 前端的完整 CI/CD Pipeline:

1. .github/workflows/frontend-ci.yml (測試)
2. .github/workflows/frontend-deploy.yml (部署)
3. 包含多環境配置
4. Lighthouse CI 效能檢查
```

🤖 **Claude 執行**：
```
✅ 已生成:

【frontend-ci.yml】
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths: ['frontend/**']
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: ESLint
        run: cd frontend && npm run lint

      - name: TypeScript Check
        run: cd frontend && npm run type-check

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: cd frontend && npm ci

      - name: Unit Tests
        run: cd frontend && npm run test -- --coverage

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: frontend/coverage/lcov.info

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4

      - run: cd frontend && npm ci

      - name: Build
        run: cd frontend && npm run build
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.API_URL_STAGING }}

      - name: Upload Build
        uses: actions/upload-artifact@v4
        with:
          name: next-build
          path: frontend/.next

  e2e:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4

      - run: cd frontend && npm ci
      - run: npx playwright install --with-deps

      - name: Run E2E Tests
        run: cd frontend && npm run test:e2e

      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report

  lighthouse:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4

      - run: cd frontend && npm ci

      - name: Lighthouse CI
        run: |
          npm install -g @lhci/cli
          cd frontend && lhci autorun
        env:
          LHCI_GITHUB_APP_TOKEN: ${{ secrets.LHCI_GITHUB_APP_TOKEN }}

【frontend-deploy.yml】
name: Frontend Deploy

on:
  push:
    branches:
      - main
      - develop
    paths: ['frontend/**']
    tags:
      - 'v*.*.*'

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GCP_REGION: asia-east1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ env.GCP_PROJECT_ID }}

      - name: Determine Environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "name=production" >> $GITHUB_OUTPUT
            echo "url=https://bnbbooking.com" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/develop" ]]; then
            echo "name=staging" >> $GITHUB_OUTPUT
            echo "url=https://staging.bnbbooking.com" >> $GITHUB_OUTPUT
          fi

      - name: Build and Deploy
        run: |
          cd frontend
          gcloud builds submit \
            --tag gcr.io/$GCP_PROJECT_ID/bnb-frontend:${{ github.sha }} \
            --timeout=20m

          gcloud run deploy bnb-frontend-${{ steps.env.outputs.name }} \
            --image gcr.io/$GCP_PROJECT_ID/bnb-frontend:${{ github.sha }} \
            --platform managed \
            --region $GCP_REGION \
            --allow-unauthenticated \
            --set-env-vars="NEXT_PUBLIC_API_URL=${{ secrets.API_URL }}" \
            --memory 2Gi \
            --cpu 2 \
            --max-instances 10 \
            --min-instances 1

      - name: Smoke Test
        run: |
          curl -f ${{ steps.env.outputs.url }}/api/health || exit 1

      - name: Notify Slack
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          status: success
          text: '✅ Frontend deployed to ${{ steps.env.outputs.name }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

已生成！包含:
- ✅ 多環境部署 (Staging/Production)
- ✅ Lighthouse CI 效能檢查
- ✅ E2E 測試 (Playwright)
- ✅ 自動擴展配置
- ✅ Smoke Test 驗證
```

---

**2.2.2 後端 Pipeline**

💬 **您對 Claude 說**：
```
請生成 Spring Boot 後端的完整 CI/CD Pipeline:

1. .github/workflows/backend-ci.yml
2. .github/workflows/backend-deploy.yml
3. 包含安全掃描
4. Blue-Green 部署
5. Database Migration
```

🤖 **Claude 執行**：
```
✅ 已生成:

【backend-ci.yml】
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths: ['backend/**']
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'maven'

      - name: Checkstyle
        run: cd backend && ./mvnw checkstyle:check

      - name: SpotBugs
        run: cd backend && ./mvnw spotbugs:check

      - name: OWASP Dependency Check
        run: cd backend && ./mvnw dependency-check:check

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'maven'

      - name: Unit Tests
        run: cd backend && ./mvnw test

      - name: Integration Tests
        run: cd backend && ./mvnw verify -P integration-tests
        env:
          SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb
          SPRING_DATASOURCE_USERNAME: postgres
          SPRING_DATASOURCE_PASSWORD: test

      - name: Generate Coverage Report
        run: cd backend && ./mvnw jacoco:report

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: backend/target/site/jacoco/jacoco.xml

  build:
    runs-on: ubuntu-latest
    needs: [quality, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4

      - name: Build JAR
        run: cd backend && ./mvnw clean package -DskipTests

      - name: Upload JAR
        uses: actions/upload-artifact@v4
        with:
          name: backend-jar
          path: backend/target/*.jar

【backend-deploy.yml】
name: Backend Deploy

on:
  push:
    branches: [main, develop]
    paths: ['backend/**']
    tags: ['v*.*.*']

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GCP_REGION: asia-east1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ env.GCP_PROJECT_ID }}

      - name: Determine Environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "name=production" >> $GITHUB_OUTPUT
            echo "db_instance=bnb-db-prod" >> $GITHUB_OUTPUT
            echo "min_instances=2" >> $GITHUB_OUTPUT
          else
            echo "name=staging" >> $GITHUB_OUTPUT
            echo "db_instance=bnb-db-staging" >> $GITHUB_OUTPUT
            echo "min_instances=1" >> $GITHUB_OUTPUT
          fi

      - name: Database Migration
        run: |
          gcloud sql connect ${{ steps.env.outputs.db_instance }} \
            --user=postgres < backend/src/main/resources/db/migration/V*.sql

      - name: Build Docker Image
        run: |
          cd backend
          gcloud builds submit \
            --tag gcr.io/$GCP_PROJECT_ID/bnb-backend:${{ github.sha }}

      - name: Deploy Green (New Version)
        id: deploy_green
        run: |
          gcloud run deploy bnb-backend-${{ steps.env.outputs.name }}-green \
            --image gcr.io/$GCP_PROJECT_ID/bnb-backend:${{ github.sha }} \
            --platform managed \
            --region $GCP_REGION \
            --set-env-vars="SPRING_PROFILES_ACTIVE=${{ steps.env.outputs.name }}" \
            --set-cloudsql-instances=${{ steps.env.outputs.db_instance }} \
            --memory 2Gi \
            --cpu 2 \
            --max-instances 20 \
            --min-instances ${{ steps.env.outputs.min_instances }} \
            --no-allow-unauthenticated

      - name: Smoke Tests on Green
        run: |
          GREEN_URL=$(gcloud run services describe bnb-backend-${{ steps.env.outputs.name }}-green \
            --region $GCP_REGION --format='value(status.url)')

          curl -f $GREEN_URL/actuator/health || exit 1

          # Run critical API tests
          ./scripts/test/smoke-tests.sh $GREEN_URL

      - name: Switch Traffic (Blue → Green)
        run: |
          # Update main service to point to green
          gcloud run services update-traffic bnb-backend-${{ steps.env.outputs.name }} \
            --to-revisions bnb-backend-${{ steps.env.outputs.name }}-green=100

      - name: Wait for Traffic Switch
        run: sleep 30

      - name: Verify Production Traffic
        run: |
          PROD_URL=$(gcloud run services describe bnb-backend-${{ steps.env.outputs.name }} \
            --region $GCP_REGION --format='value(status.url)')

          curl -f $PROD_URL/actuator/health || exit 1

      - name: Cleanup Old Blue Version
        if: success()
        run: |
          gcloud run services delete bnb-backend-${{ steps.env.outputs.name }}-blue \
            --region $GCP_REGION --quiet || true

      - name: Rollback on Failure
        if: failure()
        run: |
          echo "Deployment failed, rolling back..."
          gcloud run services update-traffic bnb-backend-${{ steps.env.outputs.name }} \
            --to-revisions bnb-backend-${{ steps.env.outputs.name }}-blue=100

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Backend deployment to ${{ steps.env.outputs.name }}: ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

已生成！包含:
- ✅ Blue-Green 部署
- ✅ Database Migration
- ✅ 安全掃描 (OWASP)
- ✅ Smoke Tests
- ✅ 自動回滾機制
```

---

### 步驟 2.3: Infrastructure as Code

**2.3.1 生成 Terraform 配置**

💬 **您對 Claude 說**：
```
請生成 Terraform IaC 配置:

1. Cloud Run (前後端)
2. Cloud SQL (PostgreSQL)
3. Cloud CDN
4. Load Balancer
5. Secret Manager
6. VPC Network
```

🤖 **Claude 執行**：
```
✅ 已生成 Terraform 配置:

infrastructure/terraform/
├── main.tf                    # 主配置
├── variables.tf               # 變數定義
├── outputs.tf                 # 輸出
├── environments/
│   ├── staging.tfvars
│   └── production.tfvars
├── modules/
│   ├── cloud_run/
│   │   ├── main.tf            # Cloud Run 服務
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── cloud_sql/
│   │   ├── main.tf            # PostgreSQL 資料庫
│   │   └── backups.tf         # 自動備份
│   ├── networking/
│   │   ├── vpc.tf             # VPC 網路
│   │   ├── load_balancer.tf  # Load Balancer
│   │   └── cdn.tf             # Cloud CDN
│   └── security/
│       ├── secret_manager.tf  # Secret Manager
│       └── iam.tf             # IAM 權限

關鍵配置:

【Cloud SQL】
resource "google_sql_database_instance" "main" {
  name             = "bnb-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = var.environment == "production" ? "db-n1-standard-2" : "db-f1-micro"

    backup_configuration {
      enabled    = true
      start_time = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days  = 7
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.id
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = var.environment == "production" ? true : false
}

【Cloud Run】
resource "google_cloud_run_service" "backend" {
  name     = "bnb-backend-${var.environment}"
  location = var.region

  template {
    spec {
      containers {
        image = var.backend_image

        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }

        env {
          name  = "SPRING_PROFILES_ACTIVE"
          value = var.environment
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.db_url.secret_id
              key  = "latest"
            }
          }
        }
      }

      service_account_name = google_service_account.backend.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

【Cloud CDN】
resource "google_compute_backend_bucket" "cdn" {
  name        = "bnb-cdn-${var.environment}"
  bucket_name = google_storage_bucket.static_assets.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    client_ttl        = 7200
    negative_caching  = true
  }
}

部署命令:
terraform init
terraform workspace select production
terraform plan -var-file=environments/production.tfvars
terraform apply -var-file=environments/production.tfvars

已生成完整 IaC 配置！
```

---

### 步驟 2.4: 監控與告警

**2.4.1 配置監控系統**

💬 **您對 Claude 說**：
```
請配置完整的監控與告警:

1. Google Cloud Monitoring (基礎設施)
2. Sentry (應用程式錯誤)
3. Datadog (APM)
4. Uptime Checks
5. Alert Policies
```

🤖 **Claude 執行**：
```
✅ 已生成監控配置:

【Google Cloud Monitoring】
infrastructure/terraform/modules/monitoring/
├── uptime_checks.tf
├── alert_policies.tf
├── dashboards.tf
└── log_metrics.tf

關鍵配置:

# Uptime Checks
resource "google_monitoring_uptime_check_config" "backend_health" {
  display_name = "Backend Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/actuator/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "api.bnbbooking.com"
    }
  }
}

# Alert Policies
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 1%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"5xx\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.slack.id,
    google_monitoring_notification_channel.pagerduty.id
  ]

  alert_strategy {
    auto_close = "1800s"
  }
}

【Sentry 整合】
# backend/src/main/resources/application.yml
sentry:
  dsn: ${SENTRY_DSN}
  environment: ${SPRING_PROFILES_ACTIVE}
  traces-sample-rate: 0.1
  send-default-pii: false

# frontend/sentry.client.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  beforeSend(event, hint) {
    // 過濾敏感資料
    if (event.request) {
      delete event.request.cookies;
    }
    return event;
  },
});

【Datadog APM】
# docker-compose.yml
services:
  backend:
    environment:
      - DD_AGENT_HOST=datadog-agent
      - DD_SERVICE=bnb-backend
      - DD_ENV=${ENVIRONMENT}
      - DD_VERSION=${VERSION}
      - DD_TRACE_ENABLED=true

  datadog-agent:
    image: gcr.io/datadoghq/agent:latest
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=datadoghq.com
      - DD_LOGS_ENABLED=true
      - DD_APM_ENABLED=true

【告警規則】
docs/monitoring/Alert_Rules.md

告警類型:
1. P0 - 立即處理 (PagerDuty)
   - 服務完全無法訪問 (> 5 分鐘)
   - Error Rate > 10%
   - Database 連線失敗

2. P1 - 緊急 (Slack + Email)
   - Error Rate > 5%
   - Response Time > 3s (95th percentile)
   - CPU > 80% (持續 10 分鐘)

3. P2 - 警告 (Slack)
   - Error Rate > 1%
   - Response Time > 2s
   - Memory > 70%

已生成完整監控配置！
```

---

### 步驟 2.5: 部署腳本與 Runbook

**2.5.1 生成部署腳本**

💬 **您對 Claude 說**：
```
請生成部署相關腳本:

1. scripts/deploy/deploy-all.sh (一鍵部署)
2. scripts/deploy/rollback.sh (回滾)
3. scripts/deploy/canary-release.sh (金絲雀發布)
4. scripts/test/smoke-tests.sh
```

🤖 **Claude 執行**：
```
✅ 已生成腳本:

【deploy-all.sh】
#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
VERSION=${2:-$(git rev-parse --short HEAD)}

echo "🚀 Deploying to $ENVIRONMENT (version: $VERSION)"

# 1. Database Migration
echo "📊 Running database migrations..."
./scripts/deploy/db-migrate.sh $ENVIRONMENT

# 2. Deploy Backend (Blue-Green)
echo "☕ Deploying backend..."
./scripts/deploy/deploy-backend.sh $ENVIRONMENT $VERSION

# 3. Deploy Frontend
echo "⚛️  Deploying frontend..."
./scripts/deploy/deploy-frontend.sh $ENVIRONMENT $VERSION

# 4. Smoke Tests
echo "🧪 Running smoke tests..."
./scripts/test/smoke-tests.sh $ENVIRONMENT

# 5. Update Traffic
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🔄 Starting canary release (10% traffic)..."
    ./scripts/deploy/canary-release.sh $VERSION
else
    echo "✅ Deployment complete!"
fi

【canary-release.sh】
#!/bin/bash
set -euo pipefail

VERSION=$1
SERVICE_NAME="bnb-backend-production"
REGION="asia-east1"

echo "🐤 Starting canary release for version $VERSION"

# Stage 1: 10% traffic
echo "Stage 1: Routing 10% traffic to new version..."
gcloud run services update-traffic $SERVICE_NAME \
  --region=$REGION \
  --to-revisions=$VERSION=10

sleep 300  # 5 minutes

# Check metrics
ERROR_RATE=$(./scripts/monitoring/get-error-rate.sh)
if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
    echo "❌ Error rate too high ($ERROR_RATE), rolling back..."
    ./scripts/deploy/rollback.sh
    exit 1
fi

# Stage 2: 50% traffic
echo "Stage 2: Routing 50% traffic to new version..."
gcloud run services update-traffic $SERVICE_NAME \
  --region=$REGION \
  --to-revisions=$VERSION=50

sleep 300

# Final check and full rollout
echo "Stage 3: Full rollout (100% traffic)..."
gcloud run services update-traffic $SERVICE_NAME \
  --region=$REGION \
  --to-revisions=$VERSION=100

echo "✅ Canary release complete!"

【smoke-tests.sh】
#!/bin/bash
set -euo pipefail

BASE_URL=$1

echo "🧪 Running smoke tests against $BASE_URL"

# Health Check
echo "Checking /health..."
curl -f $BASE_URL/actuator/health || exit 1

# Critical APIs
echo "Testing critical endpoints..."

# 1. Properties Search
curl -f -X POST $BASE_URL/api/v1/properties/search \
  -H "Content-Type: application/json" \
  -d '{"location":"Taipei","checkIn":"2025-03-01","checkOut":"2025-03-03"}' \
  || exit 1

# 2. User Login
curl -f -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' \
  || exit 1

# 3. Database Connectivity
curl -f $BASE_URL/actuator/health/db || exit 1

echo "✅ All smoke tests passed!"

已生成所有部署腳本！
```

---

**2.5.2 生成 Runbook**

💬 **您對 Claude 說**：
```
請生成完整的 Runbook:

1. 正常發布流程
2. Hotfix 緊急修復
3. 生產事故處理
4. Database 維護
5. 擴容/縮容
```

🤖 **Claude 執行**：
```
✅ 已生成 Runbook:

docs/runbook/
├── 01_Release_Process.md        # 正常發布
├── 02_Hotfix_Process.md          # 緊急修復
├── 03_Incident_Response.md       # 事故處理
├── 04_Database_Maintenance.md    # DB 維護
├── 05_Scaling_Operations.md      # 擴容操作
└── 06_Disaster_Recovery.md       # 災難恢復

【01_Release_Process.md】
# 正常發布流程

## 前置準備 (D-1)
- [ ] Code Freeze
- [ ] 建立 Release Branch
- [ ] 更新 CHANGELOG
- [ ] 通知利害關係人

## 發布日 (D-Day)

### 1. Pre-deployment (10:00)
```bash
# 備份生產資料庫
./scripts/backup/backup-db.sh production

# 驗證 Staging 環境
./scripts/test/e2e-tests.sh staging
```

### 2. Deployment (14:00)
```bash
# 一鍵部署
./scripts/deploy/deploy-all.sh production v1.2.0

# 監控儀表板
open https://console.cloud.google.com/monitoring
```

### 3. Post-deployment (14:30)
```bash
# Smoke Tests
./scripts/test/smoke-tests.sh production

# 監控關鍵指標 (30 分鐘)
# - Error Rate < 0.1%
# - Response Time < 500ms (p95)
# - CPU < 50%
```

### 4. 驗證完成 (15:00)
- [ ] 測試關鍵用戶流程
- [ ] 確認監控正常
- [ ] 更新發布記錄

【03_Incident_Response.md】
# 生產事故處理

## Severity 定義
- **P0**: 服務完全中斷 (> 50% 使用者無法使用)
- **P1**: 核心功能異常 (付款、預訂失敗)
- **P2**: 次要功能異常 (搜尋慢、圖片載入失敗)

## P0 處理流程

### 1. 立即行動 (0-5 分鐘)
```bash
# 檢查服務狀態
gcloud run services describe bnb-backend-production

# 查看最近日誌
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 --format json

# 如需立即回滾
./scripts/deploy/rollback.sh
```

### 2. 診斷 (5-15 分鐘)
- 檢查 Cloud Monitoring Dashboard
- 查看 Sentry 錯誤報告
- 檢查 Database 連線狀態
- 確認 Cloud Run 實例健康狀態

### 3. 修復 (15-30 分鐘)
- 如為程式碼問題 → 回滾
- 如為資源問題 → 手動擴容
- 如為資料庫問題 → 重啟連線池

### 4. 恢復驗證 (30-45 分鐘)
```bash
# 執行 Smoke Tests
./scripts/test/smoke-tests.sh production

# 監控恢復情況
watch -n 5 './scripts/monitoring/get-metrics.sh'
```

### 5. 事後分析 (事故後 24 小時內)
撰寫 Post-Mortem:
- 事故時間軸
- 根本原因分析
- 影響範圍評估
- 改進措施

已生成完整 Runbook！
```

---

## 📊 第三部分：完整 DevOps 架構總結

### 3.1 CI/CD Pipeline 總覽

```
【Frontend Pipeline】
Push → Lint → Test → Build → E2E → Lighthouse → Deploy → Smoke Test

【Backend Pipeline】
Push → Quality Scan → Test → Build → Security Scan →
       Deploy Green → Smoke Test → Traffic Switch → Cleanup Blue

【Infrastructure】
Terraform Plan → Manual Approval → Terraform Apply → Verify
```

### 3.2 環境策略

| 環境 | 用途 | 部署觸發 | 自動擴展 | 備份頻率 |
|------|------|----------|----------|---------|
| Development | 開發測試 | Push to dev | 0-2 | 每日 |
| Staging | 預發布驗證 | Push to develop | 1-5 | 每 6 小時 |
| Production | 正式環境 | Tag v*.*.* | 2-20 | 每小時 + PITR |

### 3.3 監控指標

**SLI (Service Level Indicators)**
- 可用性: > 99.9%
- 錯誤率: < 0.1%
- 回應時間: < 500ms (p95)
- 資料庫延遲: < 100ms (p95)

**告警閾值**
```yaml
alerts:
  - name: high_error_rate
    condition: error_rate > 1%
    severity: P1

  - name: slow_response
    condition: p95_latency > 2s
    severity: P2

  - name: database_connections
    condition: active_connections > 80
    severity: P1
```

---

## 🎓 第四部分：進階 DevOps 主題

### 4.1 多區域部署

💬 **命令範例**：
```
請設計多區域部署架構:

1. asia-east1 (台灣) - 主要區域
2. asia-northeast1 (日本) - 備援區域
3. Cloud Load Balancer 自動路由
4. Cross-region Database Replication
```

### 4.2 成本優化

💬 **命令範例**：
```
請分析並優化 GCP 成本:

1. Cloud Run 冷啟動優化
2. Cloud SQL Connection Pooling
3. Cloud CDN 快取策略
4. Committed Use Discounts
```

### 4.3 安全加固

💬 **命令範例**：
```
請加強安全措施:

1. VPC Service Controls
2. Binary Authorization
3. Secret Rotation
4. Workload Identity
5. DDoS Protection (Cloud Armor)
```

---

## 📁 第五部分：最終專案結構

```
BnBBookingDevOps/
├── .github/workflows/
│   ├── frontend-ci.yml
│   ├── frontend-deploy.yml
│   ├── backend-ci.yml
│   └── backend-deploy.yml
│
├── frontend/                  # Next.js
├── backend/                   # Spring Boot
│
├── infrastructure/
│   ├── terraform/
│   │   ├── environments/
│   │   └── modules/
│   └── docker/
│
├── scripts/
│   ├── deploy/
│   │   ├── deploy-all.sh
│   │   ├── deploy-backend.sh
│   │   ├── deploy-frontend.sh
│   │   ├── canary-release.sh
│   │   └── rollback.sh
│   ├── test/
│   │   ├── smoke-tests.sh
│   │   └── e2e-tests.sh
│   └── monitoring/
│       └── get-metrics.sh
│
└── docs/
    ├── devops/
    │   ├── CICD_Architecture.md
    │   ├── Deployment_Strategy.md
    │   └── Secrets_Management.md
    ├── monitoring/
    │   ├── Alert_Rules.md
    │   ├── Dashboard_Setup.md
    │   └── Sentry_Integration.md
    └── runbook/
        ├── 01_Release_Process.md
        ├── 02_Hotfix_Process.md
        ├── 03_Incident_Response.md
        ├── 04_Database_Maintenance.md
        └── 05_Scaling_Operations.md
```

---

## 🔍 常見問題 (FAQ)

### Q1: 如何實現真正的零停機部署？

**A**: 使用 Blue-Green + Health Check
```bash
# 1. 部署 Green (新版本)
gcloud run deploy app-green --image=new-version

# 2. Health Check 通過後切換流量
gcloud run services update-traffic app \
  --to-revisions app-green=100

# 3. 保留 Blue 一段時間以便回滾
```

### Q2: Database Migration 如何安全執行？

**A**: 使用 Backward Compatible 策略
```sql
-- Bad: 直接刪除欄位 (會中斷舊版本)
ALTER TABLE users DROP COLUMN old_field;

-- Good: 分階段刪除
-- Phase 1: 應用程式停止使用該欄位 (部署新版本)
-- Phase 2: 等待 7 天確認無問題
-- Phase 3: 刪除欄位 (再次部署)
```

### Q3: 如何監控前端效能？

**A**: 結合多種工具
```javascript
// 1. Lighthouse CI (CI/CD 中自動執行)
// 2. Real User Monitoring (Sentry Performance)
// 3. Core Web Vitals (Google Analytics)

// Sentry Performance
Sentry.addGlobalEventProcessor((event) => {
  event.contexts = {
    ...event.contexts,
    performance: {
      fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime,
      lcp: performance.getEntriesByName('largest-contentful-paint')[0]?.startTime,
    },
  };
  return event;
});
```

### Q4: 成本如何控制？

**A**: 多重策略
1. **Cloud Run**: 設定 min-instances=0 (非高峰時段)
2. **Cloud SQL**: 使用 Proxy + Connection Pooling
3. **Cloud CDN**: 高 TTL 快取靜態資源
4. **監控**: 設定 Budget Alert

---

## ✅ 結論

透過本範例，您已學會:

1. ✅ 企業級 CI/CD Pipeline (前後端分離)
2. ✅ Infrastructure as Code (Terraform)
3. ✅ Blue-Green 部署與金絲雀發布
4. ✅ 多環境管理 (Dev/Staging/Prod)
5. ✅ 完整監控與告警體系
6. ✅ 標準化 Runbook

**核心價值**: AISDLC DevOps SOP 提供企業級的 CI/CD 最佳實踐，確保高可用性 (99.9%)、快速部署 (< 15 分鐘) 和安全可靠的生產環境。

**下一步建議**:
1. 實際部署到 GCP
2. 閱讀 [DevOps SOP](../../scenarios/devops/SOP.md)
3. 探索進階主題 (Multi-region, Cost Optimization)

---

**文檔版本**: v1.0
**適用 AISDLC 版本**: v0.01
**最後更新**: 2025-12-16
**作者**: AISDLC 框架維護團隊
