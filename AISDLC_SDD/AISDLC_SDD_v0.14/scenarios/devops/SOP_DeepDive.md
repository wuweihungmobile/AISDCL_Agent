# DevOps 持續交付與運維 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的 DevOps 工程師、SRE、平台工程師
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 設計企業級 CI/CD Pipeline
- 實施 GitOps 和基礎設施即代碼
- 構建可觀測性系統
- 處理大規模部署和發布管理
- 實施災難恢復和高可用架構
- 優化雲端成本和資源使用

❌ **不建議閱讀的情況**:
- 初次設置 CI/CD(請閱讀 SOP.md)
- 快速參考部署步驟(請閱讀 SOP_QuickRef.md)
- 簡單的腳本自動化

### 文檔結構

```
Part 1: CI/CD 架構設計
Part 2: GitOps 實踐
Part 3: 容器化與編排深度
Part 4: 基礎設施即代碼 (IaC)
Part 5: 可觀測性三支柱
Part 6: 發布策略與部署模式
Part 7: 災難恢復與高可用
Part 8: 安全 DevOps (DevSecOps)
Part 9: 成本優化
Part 10: 真實案例研究
```

### 相關場景參考

本文檔專注於 DevOps 持續交付，以下相關場景可提供補充視角：

- **[Security 安全工程](../security/SOP_DeepDive.md)** - Part 8 DevSecOps 時，參考完整的安全實踐和工具鏈
- **[Testing 測試策略](../testing/SOP_DeepDive.md)** - Part 8 CI/CD 整合測試，建立完整的測試 pipeline
- **[Performance 效能優化](../performance/SOP_DeepDive.md)** - Part 9 成本優化時，參考應用層級的效能優化策略
- **[Documentation 文檔工程](../documentation/SOP_DeepDive.md)** - CI/CD 流程和基礎設施的文檔化最佳實踐

---

## Part 1: CI/CD 架構設計

### 1.1 CI/CD Pipeline 最佳實踐

**完整 Pipeline 架構**:

```yaml
# .github/workflows/complete-pipeline.yml

name: Complete CI/CD Pipeline

on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ===== Stage 1: Code Quality =====
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linters
        run: |
          npm run lint
          npm run prettier:check

      - name: Run type checking
        run: npm run type-check

  # ===== Stage 2: Security Scanning =====
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run dependency check
        run: npm audit --audit-level=moderate

      - name: Run SAST (Static Application Security Testing)
        uses: github/codeql-action/analyze@v2

      - name: Run secrets scanning
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD

  # ===== Stage 3: Unit Tests =====
  test-unit:
    runs-on: ubuntu-latest
    needs: [lint]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        run: npm run test:unit -- --coverage

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          flags: unit

  # ===== Stage 4: Integration Tests =====
  test-integration:
    runs-on: ubuntu-latest
    needs: [lint]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run database migrations
        run: npm run db:migrate
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test

      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379

  # ===== Stage 5: E2E Tests =====
  test-e2e:
    runs-on: ubuntu-latest
    needs: [test-unit, test-integration]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: test-results/

  # ===== Stage 6: Build =====
  build:
    runs-on: ubuntu-latest
    needs: [security, test-unit, test-integration]
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop')

    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Scan image for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.meta.outputs.tags }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # ===== Stage 7: Deploy to Staging =====
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [build, test-e2e]
    environment:
      name: staging
      url: https://staging.example.com

    steps:
      - uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Setup Helm
        uses: azure/setup-helm@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG_STAGING }}" | base64 -d > kubeconfig
          export KUBECONFIG=./kubeconfig

      - name: Deploy to Staging with Helm
        run: |
          helm upgrade --install myapp ./helm/myapp \
            --namespace staging \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set environment=staging \
            --wait --timeout 5m

      - name: Run smoke tests
        run: |
          npm run test:smoke -- --baseUrl=https://staging.example.com

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Staging deployment completed'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

  # ===== Stage 8: Deploy to Production =====
  deploy-production:
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com

    steps:
      - uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Setup Helm
        uses: azure/setup-helm@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG_PROD }}" | base64 -d > kubeconfig
          export KUBECONFIG=./kubeconfig

      - name: Deploy to Production with Canary
        run: |
          # Deploy canary (10% traffic)
          helm upgrade --install myapp-canary ./helm/myapp \
            --namespace production \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set environment=production \
            --set replicaCount=1 \
            --set canary.enabled=true \
            --wait --timeout 5m

      - name: Monitor canary metrics
        run: |
          # Wait 10 minutes and monitor error rates
          sleep 600
          ./scripts/check-canary-health.sh

      - name: Promote canary to full deployment
        run: |
          helm upgrade --install myapp ./helm/myapp \
            --namespace production \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set environment=production \
            --set replicaCount=10 \
            --wait --timeout 10m

      - name: Cleanup canary
        run: |
          helm delete myapp-canary --namespace production

      - name: Create GitHub release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ github.run_number }}
          release_name: Release v${{ github.run_number }}
          body: |
            Deployed to production
            Image: ${{ needs.build.outputs.image-tag }}

      - name: Notify team
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: '🎉 Production deployment successful!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Part 2: GitOps 實踐

### 2.1 ArgoCD 實作

**ArgoCD Application 定義**:

```yaml
# argocd/applications/myapp.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default

  # Source repository
  source:
    repoURL: https://github.com/org/myapp-gitops
    targetRevision: HEAD
    path: kubernetes/overlays/production

    # Kustomize
    kustomize:
      images:
        - myapp=ghcr.io/org/myapp:v1.2.3

  # Destination cluster
  destination:
    server: https://kubernetes.default.svc
    namespace: production

  # Sync policy
  syncPolicy:
    automated:
      prune: true      # 自動刪除不在 Git 的資源
      selfHeal: true   # 自動修復 drift
      allowEmpty: false

    syncOptions:
      - CreateNamespace=true
      - PruneLast=true

    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  # Health assessment
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # 忽略 HPA 修改的 replicas
```

**GitOps 目錄結構**:

```
myapp-gitops/
├── kubernetes/
│   ├── base/                    # Kustomize base
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── kustomization.yaml
│   │
│   └── overlays/
│       ├── staging/             # Staging 環境
│       │   ├── kustomization.yaml
│       │   ├── namespace.yaml
│       │   └── patches/
│       │       └── replicas.yaml
│       │
│       └── production/          # Production 環境
│           ├── kustomization.yaml
│           ├── namespace.yaml
│           └── patches/
│               ├── replicas.yaml
│               └── resources.yaml
│
├── helm/                        # Helm charts
│   └── myapp/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-staging.yaml
│       ├── values-production.yaml
│       └── templates/
│
└── argocd/                      # ArgoCD 配置
    ├── applications/
    └── projects/
```

---

## Part 3: 容器化與編排深度

### 3.1 多階段 Dockerfile 優化

```dockerfile
# ===== Stage 1: Dependencies =====
FROM node:18-alpine AS deps

WORKDIR /app

# 只複製 package files (利用 Docker layer caching)
COPY package.json package-lock.json ./

# 安裝生產依賴
RUN npm ci --only=production && \
    # 清理 npm cache
    npm cache clean --force

# ===== Stage 2: Build =====
FROM node:18-alpine AS builder

WORKDIR /app

# 複製 dependencies 和 source code
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build application
RUN npm run build && \
    # 移除 devDependencies
    npm prune --production

# ===== Stage 3: Production =====
FROM node:18-alpine AS production

# 安全性: 建立非 root 使用者
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

WORKDIR /app

# 只複製必要檔案
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./

# 切換到非 root 使用者
USER nodejs

# 健康檢查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

# 啟動應用
EXPOSE 3000
CMD ["node", "dist/index.js"]

# ===== 優化結果 =====
# Before: 1.2 GB
# After:  180 MB (減少 85%)
```

### 3.2 Kubernetes 資源優化

```yaml
# deployment.yaml - 生產級別配置
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
  labels:
    app: myapp
    version: v1.0.0
spec:
  replicas: 3

  # 部署策略
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 最多多 1 個 Pod
      maxUnavailable: 0  # 保證零停機

  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"

    spec:
      # 親和性規則 - 分散到不同節點
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - myapp
              topologyKey: kubernetes.io/hostname

      # Init Container - 等待依賴服務
      initContainers:
        - name: wait-for-db
          image: busybox:1.35
          command:
            - sh
            - -c
            - |
              until nc -z postgres 5432; do
                echo "Waiting for PostgreSQL..."
                sleep 2
              done

      containers:
        - name: myapp
          image: ghcr.io/org/myapp:v1.0.0
          imagePullPolicy: Always

          ports:
            - name: http
              containerPort: 3000
              protocol: TCP

          # 環境變數
          env:
            - name: NODE_ENV
              value: "production"
            - name: PORT
              value: "3000"

          # 從 ConfigMap 載入
          envFrom:
            - configMapRef:
                name: myapp-config

          # 從 Secret 載入敏感資訊
            - secretRef:
                name: myapp-secrets

          # 資源限制
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"

          # 健康檢查
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          # Startup Probe (應用啟動可能較慢)
          startupProbe:
            httpGet:
              path: /health
              port: http
            failureThreshold: 30
            periodSeconds: 10

          # 安全性設定
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL

          # Volume mounts
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: cache
              mountPath: /app/.cache

      # Volumes
      volumes:
        - name: tmp
          emptyDir: {}
        - name: cache
          emptyDir: {}

      # 服務帳號
      serviceAccountName: myapp

      # 優雅關閉
      terminationGracePeriodSeconds: 30

---
# HPA - 水平自動擴展
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp

  minReplicas: 3
  maxReplicas: 20

  metrics:
    # CPU 使用率目標
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # 記憶體使用率目標
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # 自訂指標 - 請求速率
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
        - type: Pods
          value: 2
          periodSeconds: 60
      selectPolicy: Max

    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 1
          periodSeconds: 60
      selectPolicy: Min

---
# PDB - Pod Disruption Budget (保證可用性)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

---

## Part 4: 基礎設施即代碼 (IaC)

### 4.1 Terraform 最佳實踐

```hcl
# ===== main.tf =====

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 遠端 backend (S3 + DynamoDB 鎖定)
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# ===== variables.tf =====

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

# ===== modules/vpc/main.tf =====

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-vpc"
    }
  )
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-public-${var.availability_zones[count.index]}"
      Type = "public"
    }
  )
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 100)
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-private-${var.availability_zones[count.index]}"
      Type = "private"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-igw"
    }
  )
}

# NAT Gateways (每個 AZ 一個)
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-nat-${var.availability_zones[count.index]}"
    }
  )
}

resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.common_tags,
    {
      Name = "${var.environment}-nat-${var.availability_zones[count.index]}"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# ===== modules/eks/main.tf =====

resource "aws_eks_cluster" "main" {
  name     = "${var.environment}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_access_cidrs
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller
  ]

  tags = var.common_tags
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.environment}-node-group"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = var.private_subnet_ids

  scaling_config {
    desired_size = var.desired_capacity
    max_size     = var.max_capacity
    min_size     = var.min_capacity
  }

  instance_types = var.instance_types
  capacity_type  = "ON_DEMAND"

  update_config {
    max_unavailable_percentage = 33
  }

  labels = {
    environment = var.environment
  }

  tags = var.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy
  ]
}

# ===== outputs.tf =====

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}
```

---

## Part 5: 可觀測性三支柱

### 5.1 Metrics (指標)

**Prometheus + Grafana Stack**:

```yaml
# prometheus/values.yaml
prometheus:
  prometheusSpec:
    retention: 30d
    retentionSize: "50GB"

    resources:
      requests:
        memory: 4Gi
        cpu: 2
      limits:
        memory: 8Gi
        cpu: 4

    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 100Gi

    # 服務發現
    serviceMonitorSelector: {}
    podMonitorSelector: {}

    # 告警規則
    ruleSelector: {}

# Grafana 配置
grafana:
  adminPassword: <secret>

  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
        - name: 'default'
          orgId: 1
          folder: ''
          type: file
          disableDeletion: false
          options:
            path: /var/lib/grafana/dashboards/default

  dashboards:
    default:
      kubernetes-cluster:
        gnetId: 7249
        revision: 1
        datasource: Prometheus
      node-exporter:
        gnetId: 1860
        revision: 23
        datasource: Prometheus
```

**自訂告警規則**:

```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: myapp-alerts
  namespace: monitoring
spec:
  groups:
    - name: myapp
      interval: 30s
      rules:
        # 高錯誤率告警
        - alert: HighErrorRate
          expr: |
            sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
            /
            sum(rate(http_requests_total[5m])) by (service)
            > 0.05
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "High error rate detected"
            description: "{{ $labels.service }} has {{ $value | humanizePercentage }} error rate"

        # 高延遲告警
        - alert: HighLatency
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
            ) > 1
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High latency detected"
            description: "{{ $labels.service }} P95 latency is {{ $value }}s"

        # Pod 頻繁重啟
        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total[15m]) > 0
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Pod is crash looping"
            description: "Pod {{ $labels.namespace }}/{{ $labels.pod }} is restarting frequently"

        # 記憶體使用率過高
        - alert: HighMemoryUsage
          expr: |
            container_memory_usage_bytes{container!=""}
            /
            container_spec_memory_limit_bytes{container!=""}
            > 0.9
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High memory usage"
            description: "Container {{ $labels.container }} in pod {{ $labels.pod }} is using {{ $value | humanizePercentage }} of memory limit"
```

### 5.2 Logging (日誌)

**ELK Stack 配置**:

```yaml
# filebeat-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: logging
data:
  filebeat.yml: |
    filebeat.inputs:
      - type: container
        paths:
          - /var/log/containers/*.log
        processors:
          - add_kubernetes_metadata:
              host: ${NODE_NAME}
              matchers:
                - logs_path:
                    logs_path: "/var/log/containers/"

          # 解析 JSON 日誌
          - decode_json_fields:
              fields: ["message"]
              target: ""
              overwrite_keys: true

          # 添加標籤
          - add_labels:
              labels:
                env: production

    output.elasticsearch:
      hosts: ["elasticsearch:9200"]
      index: "filebeat-%{[agent.version]}-%{+yyyy.MM.dd}"

      # 認證
      username: ${ELASTICSEARCH_USERNAME}
      password: ${ELASTICSEARCH_PASSWORD}

    # 日誌級別
    logging.level: info
    logging.to_stderr: true
```

**結構化日誌範例**:

```javascript
// 使用 pino (Node.js)
const pino = require('pino');

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => {
      return { level: label };
    }
  },
  serializers: {
    req: (req) => ({
      method: req.method,
      url: req.url,
      headers: req.headers,
      remoteAddress: req.socket.remoteAddress
    }),
    res: (res) => ({
      statusCode: res.statusCode
    }),
    err: pino.stdSerializers.err
  }
});

// 使用
app.use((req, res, next) => {
  req.log = logger.child({
    requestId: req.id,
    userId: req.user?.id
  });

  req.log.info({ req }, 'Incoming request');
  next();
});

app.get('/api/users/:id', async (req, res) => {
  req.log.info({ userId: req.params.id }, 'Fetching user');

  try {
    const user = await db.users.findById(req.params.id);

    req.log.info({ user }, 'User fetched successfully');
    res.json(user);
  } catch (err) {
    req.log.error({ err }, 'Failed to fetch user');
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 輸出範例:
// {"level":"info","time":1640000000000,"requestId":"abc123","userId":"user456","msg":"Fetching user","userId":"user456"}
```

### 5.3 Tracing (追蹤)

**OpenTelemetry 實作**:

```javascript
// tracing.js
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'myapp',
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
  }),
  traceExporter: new JaegerExporter({
    endpoint: 'http://jaeger:14268/api/traces',
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      // 自動埋點配置
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingPaths: ['/health', '/metrics']
      },
      '@opentelemetry/instrumentation-express': {},
      '@opentelemetry/instrumentation-pg': {}
    })
  ]
});

sdk.start();

process.on('SIGTERM', () => {
  sdk.shutdown()
    .then(() => console.log('Tracing terminated'))
    .catch((error) => console.log('Error terminating tracing', error))
    .finally(() => process.exit(0));
});

// app.js
require('./tracing'); // 必須在最前面

const express = require('express');
const app = express();

// 手動添加 span
const { trace } = require('@opentelemetry/api');

app.get('/api/complex-operation', async (req, res) => {
  const tracer = trace.getTracer('myapp');

  const span = tracer.startSpan('complex-operation');

  try {
    // Step 1
    const span1 = tracer.startSpan('fetch-data', { parent: span });
    const data = await fetchData();
    span1.end();

    // Step 2
    const span2 = tracer.startSpan('process-data', { parent: span });
    const processed = await processData(data);
    span2.end();

    // Step 3
    const span3 = tracer.startSpan('save-result', { parent: span });
    await saveResult(processed);
    span3.end();

    span.setStatus({ code: SpanStatusCode.OK });
    res.json({ success: true });
  } catch (err) {
    span.recordException(err);
    span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
    res.status(500).json({ error: err.message });
  } finally {
    span.end();
  }
});
```

---

## Part 6: DevSecOps 實踐

### 6.1 安全掃描整合到 CI/CD

**多層安全掃描 Pipeline**:

```yaml
# .github/workflows/devsecops-pipeline.yml
name: DevSecOps Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # 1. 代碼質量與安全掃描
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # SonarQube 掃描
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

      # Semgrep SAST
      - name: Semgrep Security Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten

  # 2. 依賴漏洞掃描
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --fail-on=upgradable

      - name: Dependency Review
        uses: actions/dependency-review-action@v3
        with:
          fail-on-severity: moderate

  # 3. Secrets 掃描
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Gitleaks Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # 4. 容器鏡像掃描
  image-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Grype Scan (Alternative)
        uses: anchore/scan-action@v3
        with:
          image: myapp:${{ github.sha }}
          fail-build: true
          severity-cutoff: high

  # 5. IaC 掃描
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: tfsec (Terraform)
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          soft_fail: false

      - name: Checkov (Multi-IaC)
        uses: bridgecrewio/checkov-action@master
        with:
          directory: infrastructure/
          framework: terraform,kubernetes,dockerfile

  # 6. 部署 (只有通過所有檢查)
  deploy:
    needs: [code-quality, dependency-scan, secret-scan, image-scan, iac-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Production
        run: |
          echo "All security checks passed!"
          # Deploy logic...
```

### 6.2 Runtime 安全監控

**Falco 規則實作**:

```yaml
# falco-rules.yaml - Kubernetes Runtime Security

# 偵測容器內執行 shell
- rule: Shell Spawned in Container
  desc: Detect shell execution in container
  condition: >
    spawned_process and
    container and
    proc.name in (bash, sh, zsh, fish) and
    not proc.pname in (docker, kubectl, supervisor)
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name
     proc=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: WARNING
  tags: [container, shell]

# 偵測異常網路連接
- rule: Unexpected Outbound Connection
  desc: Detect unexpected outbound network connection
  condition: >
    outbound and
    container and
    not fd.sip in (allowed_ips) and
    not fd.sport in (80, 443, 3306, 5432, 6379)
  output: >
    Unexpected outbound connection
    (user=%user.name container=%container.name
     ip=%fd.cip port=%fd.cport proto=%fd.l4proto)
  priority: WARNING
  tags: [network]

# 偵測敏感文件訪問
- rule: Sensitive File Access
  desc: Detect access to sensitive files
  condition: >
    open_read and
    container and
    fd.name in (/etc/shadow, /etc/passwd, /root/.ssh/id_rsa)
  output: >
    Sensitive file accessed
    (user=%user.name container=%container.name
     file=%fd.name proc=%proc.name)
  priority: CRITICAL
  tags: [filesystem, secrets]

# 偵測特權容器
- rule: Privileged Container Started
  desc: Detect privileged container
  condition: >
    container_started and
    container.privileged=true
  output: >
    Privileged container started
    (container=%container.name image=%container.image)
  priority: CRITICAL
  tags: [container, privilege]
```

**Falco 部署**:

```yaml
# falco-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: falco
  namespace: falco-system
spec:
  selector:
    matchLabels:
      app: falco
  template:
    metadata:
      labels:
        app: falco
    spec:
      serviceAccountName: falco
      hostNetwork: true
      hostPID: true
      containers:
        - name: falco
          image: falcosecurity/falco:latest
          securityContext:
            privileged: true
          volumeMounts:
            - name: docker-socket
              mountPath: /host/var/run/docker.sock
            - name: dev
              mountPath: /host/dev
            - name: proc
              mountPath: /host/proc
              readOnly: true
            - name: boot
              mountPath: /host/boot
              readOnly: true
            - name: modules
              mountPath: /host/lib/modules
              readOnly: true
            - name: falco-config
              mountPath: /etc/falco
      volumes:
        - name: docker-socket
          hostPath:
            path: /var/run/docker.sock
        - name: dev
          hostPath:
            path: /dev
        - name: proc
          hostPath:
            path: /proc
        - name: boot
          hostPath:
            path: /boot
        - name: modules
          hostPath:
            path: /lib/modules
        - name: falco-config
          configMap:
            name: falco-config
```

### 6.3 Policy Enforcement (OPA Gatekeeper)

```yaml
# constraint-template.yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        violation[{"msg": msg, "details": {"missing_labels": missing}}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("必須包含標籤: %v", [missing])
        }

---
# constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
  parameters:
    labels:
      - "app"
      - "owner"
      - "environment"
```

---

## Part 7: 成本優化策略

### 7.1 雲端成本監控

**AWS Cost Explorer API 整合**:

```python
# cost-monitor.py
import boto3
from datetime import datetime, timedelta
import json

class AWSCostMonitor:
    def __init__(self):
        self.ce_client = boto3.client('ce', region_name='us-east-1')

    def get_monthly_cost(self):
        """獲取本月成本"""
        start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        end = datetime.now().strftime('%Y-%m-%d')

        response = self.ce_client.get_cost_and_usage(
            TimePeriod={'Start': start, 'End': end},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ]
        )

        costs = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                costs[service] = cost

        return costs

    def get_cost_forecast(self, days=30):
        """預測未來成本"""
        start = datetime.now().strftime('%Y-%m-%d')
        end = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

        response = self.ce_client.get_cost_forecast(
            TimePeriod={'Start': start, 'End': end},
            Metric='UNBLENDED_COST',
            Granularity='MONTHLY'
        )

        forecast = float(response['Total']['Amount'])
        return forecast

    def detect_anomalies(self):
        """檢測成本異常"""
        response = self.ce_client.get_anomalies(
            DateInterval={
                'StartDate': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                'EndDate': datetime.now().strftime('%Y-%m-%d')
            },
            MaxResults=10
        )

        anomalies = []
        for anomaly in response['Anomalies']:
            anomalies.append({
                'service': anomaly['DimensionValue'],
                'impact': float(anomaly['Impact']['TotalImpact']),
                'start_date': anomaly['AnomalyStartDate'],
                'score': float(anomaly['AnomalyScore']['CurrentScore'])
            })

        return anomalies

    def generate_report(self):
        """生成成本報告"""
        costs = self.get_monthly_cost()
        forecast = self.get_cost_forecast()
        anomalies = self.detect_anomalies()

        # 排序成本最高的服務
        top_services = sorted(costs.items(), key=lambda x: x[1], reverse=True)[:10]

        report = {
            'month': datetime.now().strftime('%Y-%m'),
            'total_cost': sum(costs.values()),
            'forecast_next_month': forecast,
            'top_10_services': dict(top_services),
            'anomalies': anomalies
        }

        return report

# 使用範例
monitor = AWSCostMonitor()
report = monitor.generate_report()

print(f"本月成本: ${report['total_cost']:.2f}")
print(f"下月預測: ${report['forecast_next_month']:.2f}")
print(f"\n前 10 大成本服務:")
for service, cost in report['top_10_services'].items():
    print(f"  {service}: ${cost:.2f}")

if report['anomalies']:
    print(f"\n⚠️  檢測到 {len(report['anomalies'])} 個成本異常:")
    for anomaly in report['anomalies']:
        print(f"  {anomaly['service']}: +${anomaly['impact']:.2f} (評分: {anomaly['score']:.2f})")
```

### 7.2 資源優化策略

**Kubernetes Resource Right-Sizing**:

```python
# k8s-rightsizing.py
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect
from datetime import datetime, timedelta

class ResourceOptimizer:
    def __init__(self):
        config.load_kube_config()
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.prom = PrometheusConnect(url="http://prometheus:9090")

    def analyze_pod_usage(self, namespace, days=7):
        """分析 Pod 資源使用情況"""
        # 查詢 Prometheus 過去 7 天的數據
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # CPU 使用率
        cpu_query = f'''
            max_over_time(
                container_cpu_usage_seconds_total{{namespace="{namespace}"}}[{days}d]
            )
        '''
        cpu_results = self.prom.custom_query(cpu_query)

        # 記憶體使用量
        mem_query = f'''
            max_over_time(
                container_memory_working_set_bytes{{namespace="{namespace}"}}[{days}d]
            )
        '''
        mem_results = self.prom.custom_query(mem_query)

        recommendations = []

        # 獲取所有 Deployment
        deployments = self.apps_api.list_namespaced_deployment(namespace)

        for deployment in deployments.items:
            for container in deployment.spec.template.spec.containers:
                # 當前請求和限制
                current_requests = container.resources.requests or {}
                current_limits = container.resources.limits or {}

                current_cpu_request = self._parse_cpu(current_requests.get('cpu', '0'))
                current_mem_request = self._parse_memory(current_requests.get('memory', '0'))

                # 實際使用量 (從 Prometheus)
                actual_cpu = self._get_actual_usage(cpu_results, container.name)
                actual_mem = self._get_actual_usage(mem_results, container.name)

                # 建議值 (實際使用量 * 1.2 + 安全邊際)
                recommended_cpu = actual_cpu * 1.2
                recommended_mem = actual_mem * 1.2

                # 計算節省
                if current_cpu_request > recommended_cpu * 1.5:
                    recommendations.append({
                        'deployment': deployment.metadata.name,
                        'container': container.name,
                        'resource': 'CPU',
                        'current': f'{current_cpu_request}m',
                        'recommended': f'{recommended_cpu:.0f}m',
                        'saving': f'{(current_cpu_request - recommended_cpu) / current_cpu_request * 100:.1f}%'
                    })

                if current_mem_request > recommended_mem * 1.5:
                    recommendations.append({
                        'deployment': deployment.metadata.name,
                        'container': container.name,
                        'resource': 'Memory',
                        'current': f'{current_mem_request}Mi',
                        'recommended': f'{recommended_mem:.0f}Mi',
                        'saving': f'{(current_mem_request - recommended_mem) / current_mem_request * 100:.1f}%'
                    })

        return recommendations

    def _parse_cpu(self, cpu_str):
        """解析 CPU 字串 (例如 '100m', '0.1')"""
        if cpu_str.endswith('m'):
            return int(cpu_str[:-1])
        else:
            return int(float(cpu_str) * 1000)

    def _parse_memory(self, mem_str):
        """解析記憶體字串 (例如 '128Mi', '1Gi')"""
        units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3}
        for unit, multiplier in units.items():
            if mem_str.endswith(unit):
                return int(mem_str[:-2]) * multiplier / (1024**2)  # 轉換為 Mi
        return int(mem_str) / (1024**2)

    def generate_yaml_patch(self, recommendations):
        """生成 YAML patch 檔案"""
        for rec in recommendations:
            print(f"""
# {rec['deployment']} - {rec['container']}
kubectl patch deployment {rec['deployment']} -n default --type='json' -p='[
  {{
    "op": "replace",
    "path": "/spec/template/spec/containers/0/resources/requests/{rec['resource'].lower()}",
    "value": "{rec['recommended']}"
  }}
]'
""")

# 使用
optimizer = ResourceOptimizer()
recommendations = optimizer.analyze_pod_usage('production', days=30)

print(f"發現 {len(recommendations)} 個優化機會:\n")
for rec in recommendations:
    print(f"📦 {rec['deployment']} / {rec['container']}")
    print(f"   {rec['resource']}: {rec['current']} → {rec['recommended']} (節省 {rec['saving']})")
    print()

optimizer.generate_yaml_patch(recommendations)
```

### 7.3 Spot Instance 自動化

```python
# spot-instance-manager.py
import boto3
from datetime import datetime, timedelta

class SpotInstanceManager:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.autoscaling = boto3.client('autoscaling')

    def get_spot_price_history(self, instance_type, az, days=7):
        """獲取 Spot 價格歷史"""
        start_time = datetime.now() - timedelta(days=days)

        response = self.ec2.describe_spot_price_history(
            InstanceTypes=[instance_type],
            AvailabilityZone=az,
            StartTime=start_time,
            ProductDescriptions=['Linux/UNIX']
        )

        prices = [(item['Timestamp'], float(item['SpotPrice']))
                  for item in response['SpotPriceHistory']]

        # 計算統計
        price_values = [p[1] for p in prices]
        avg_price = sum(price_values) / len(price_values)
        max_price = max(price_values)

        return {
            'average': avg_price,
            'max': max_price,
            'current': price_values[0] if price_values else 0
        }

    def calculate_savings(self, instance_type, hours_per_month=730):
        """計算 Spot vs On-Demand 節省"""
        # 獲取 On-Demand 價格
        response = self.ec2.describe_instance_types(
            InstanceTypes=[instance_type]
        )

        # 獲取 Spot 價格 (多個 AZ 平均)
        azs = ['us-east-1a', 'us-east-1b', 'us-east-1c']
        spot_prices = []

        for az in azs:
            price_info = self.get_spot_price_history(instance_type, az, days=30)
            spot_prices.append(price_info['average'])

        avg_spot_price = sum(spot_prices) / len(spot_prices)

        # 假設 On-Demand 價格 (實際應從 AWS API 獲取)
        on_demand_prices = {
            't3.medium': 0.0416,
            't3.large': 0.0832,
            'm5.large': 0.096,
            'm5.xlarge': 0.192
        }

        on_demand_price = on_demand_prices.get(instance_type, 0.1)

        monthly_on_demand = on_demand_price * hours_per_month
        monthly_spot = avg_spot_price * hours_per_month
        savings = monthly_on_demand - monthly_spot
        savings_pct = (savings / monthly_on_demand) * 100

        return {
            'on_demand_monthly': monthly_on_demand,
            'spot_monthly': monthly_spot,
            'savings': savings,
            'savings_percentage': savings_pct
        }

    def create_mixed_asg(self, name, min_size, max_size, desired):
        """建立混合 On-Demand 和 Spot 的 ASG"""
        response = self.autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=name,
            MixedInstancesPolicy={
                'LaunchTemplate': {
                    'LaunchTemplateSpecification': {
                        'LaunchTemplateName': 'my-launch-template',
                        'Version': '$Latest'
                    },
                    'Overrides': [
                        {'InstanceType': 't3.medium'},
                        {'InstanceType': 't3.large'},
                        {'InstanceType': 't3a.medium'},  # 更便宜的 AMD 變體
                    ]
                },
                'InstancesDistribution': {
                    'OnDemandBaseCapacity': 1,  # 至少 1 個 On-Demand
                    'OnDemandPercentageAboveBaseCapacity': 20,  # 20% On-Demand, 80% Spot
                    'SpotAllocationStrategy': 'capacity-optimized',  # 最佳策略
                    'SpotMaxPrice': ''  # 不設上限,使用 On-Demand 價格
                }
            },
            MinSize=min_size,
            MaxSize=max_size,
            DesiredCapacity=desired,
            VPCZoneIdentifier='subnet-xxx,subnet-yyy,subnet-zzz',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': f'{name}-instance',
                    'PropagateAtLaunch': True
                }
            ]
        )

        return response

# 使用
manager = SpotInstanceManager()

# 分析節省
savings = manager.calculate_savings('t3.medium')
print(f"t3.medium 每月成本:")
print(f"  On-Demand: ${savings['on_demand_monthly']:.2f}")
print(f"  Spot:      ${savings['spot_monthly']:.2f}")
print(f"  節省:      ${savings['savings']:.2f} ({savings['savings_percentage']:.1f}%)")

# 建立混合 ASG
# manager.create_mixed_asg('my-app-asg', min_size=2, max_size=10, desired=5)
```

---

## Part 8: 災難恢復與高可用

### 8.1 備份策略

**Velero Kubernetes 備份**:

```yaml
# velero-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-backup
  namespace: velero
spec:
  # 每天凌晨 2 點執行
  schedule: "0 2 * * *"
  template:
    # 包含所有命名空間
    includedNamespaces:
      - "*"
    # 排除某些命名空間
    excludedNamespaces:
      - kube-system
      - kube-public
    # 包含 PV
    includePVs: true
    # TTL 30 天
    ttl: 720h
    # 標籤選擇器
    labelSelector:
      matchLabels:
        backup: "true"

---
# 應用程式一致性備份 (使用 pre/post hooks)
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: postgres-backup
  namespace: velero
spec:
  includedNamespaces:
    - database
  hooks:
    resources:
      - name: postgres-backup-hook
        includedNamespaces:
          - database
        labelSelector:
          matchLabels:
            app: postgres
        pre:
          - exec:
              command:
                - /bin/bash
                - -c
                - |
                  pg_dump -U postgres mydb > /backup/dump.sql
                  echo "Database dump completed"
        post:
          - exec:
              command:
                - /bin/bash
                - -c
                - |
                  rm -f /backup/dump.sql
                  echo "Cleanup completed"
```

**自動化恢復測試**:

```bash
#!/bin/bash
# test-disaster-recovery.sh

set -e

BACKUP_NAME="daily-backup-20240101120000"
TEST_NAMESPACE="dr-test"

echo "🔄 開始災難恢復測試..."

# 1. 建立測試命名空間
kubectl create namespace $TEST_NAMESPACE || true

# 2. 從備份恢復
velero restore create test-restore \
  --from-backup $BACKUP_NAME \
  --namespace-mappings production:$TEST_NAMESPACE \
  --wait

# 3. 驗證恢復結果
echo "✅ 驗證 Pod 狀態..."
kubectl wait --for=condition=ready pod \
  -l app=myapp \
  -n $TEST_NAMESPACE \
  --timeout=300s

# 4. 健康檢查
echo "✅ 執行健康檢查..."
POD=$(kubectl get pod -n $TEST_NAMESPACE -l app=myapp -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $TEST_NAMESPACE $POD -- curl -f http://localhost:8080/health

# 5. 資料完整性檢查
echo "✅ 驗證資料完整性..."
RECORD_COUNT=$(kubectl exec -n $TEST_NAMESPACE $POD -- \
  psql -U postgres -d mydb -t -c "SELECT COUNT(*) FROM users")

if [ "$RECORD_COUNT" -gt 0 ]; then
  echo "✅ 資料恢復成功: $RECORD_COUNT 筆記錄"
else
  echo "❌ 資料恢復失敗!"
  exit 1
fi

# 6. 清理測試環境
echo "🧹 清理測試環境..."
kubectl delete namespace $TEST_NAMESPACE

echo "✅ 災難恢復測試完成!"
```

### 8.2 高可用架構

**Multi-Region Kubernetes 架構**:

```yaml
# multi-region-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
  annotations:
    # AWS Load Balancer Controller
    service.beta.kubernetes.io/aws-load-balancer-type: "external"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 6  # 跨多個 AZ
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      # Pod 反親和性 (分散到不同節點和 AZ)
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: myapp
                topologyKey: kubernetes.io/hostname
            - weight: 50
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: myapp
                topologyKey: topology.kubernetes.io/zone

      # 拓撲分布約束 (確保跨 AZ 均勻分佈)
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: myapp

      containers:
        - name: myapp
          image: myapp:v1.0.0
          ports:
            - containerPort: 8080

          # 健康檢查
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          # 資源請求和限制
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi

      # PodDisruptionBudget (防止過多 Pod 同時下線)
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-pdb
spec:
  minAvailable: 4  # 至少保持 4 個 Pod 運行
  selector:
    matchLabels:
      app: myapp
```

### 8.3 Chaos Engineering

**Chaos Mesh 實驗**:

```yaml
# network-chaos.yaml - 模擬網路延遲
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
  namespace: chaos-testing
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  delay:
    latency: "100ms"
    correlation: "50"
    jitter: "10ms"
  duration: "30s"
  scheduler:
    cron: "@every 1h"

---
# pod-chaos.yaml - 隨機殺死 Pod
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
  namespace: chaos-testing
spec:
  action: pod-kill
  mode: fixed-percent
  value: "10"  # 隨機殺死 10% 的 Pod
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  duration: "60s"
  scheduler:
    cron: "0 */6 * * *"  # 每 6 小時

---
# stress-chaos.yaml - CPU/記憶體壓力測試
apiVersion: chaos-mesh.org/v1alpha1
kind: StressChaos
metadata:
  name: stress-test
  namespace: chaos-testing
spec:
  mode: one
  selector:
    namespaces:
      - production
    labelSelectors:
      app: myapp
  stressors:
    cpu:
      workers: 2
      load: 80
    memory:
      workers: 1
      size: "256MB"
  duration: "5m"
```

---

## Part 9: Troubleshooting 指南

### 9.1 常見問題診斷

**Pod 無法啟動**:

```bash
# 診斷腳本
#!/bin/bash
# debug-pod.sh

POD_NAME=$1
NAMESPACE=${2:-default}

echo "🔍 診斷 Pod: $POD_NAME"

# 1. 檢查 Pod 狀態
echo -e "\n📊 Pod 狀態:"
kubectl get pod $POD_NAME -n $NAMESPACE -o wide

# 2. 檢查 Events
echo -e "\n📝 Events:"
kubectl describe pod $POD_NAME -n $NAMESPACE | grep -A 20 "Events:"

# 3. 檢查容器日誌
echo -e "\n📋 容器日誌 (最近 50 行):"
kubectl logs $POD_NAME -n $NAMESPACE --tail=50

# 如果 Pod 有多個容器
CONTAINERS=$(kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.containers[*].name}')
for container in $CONTAINERS; do
  echo -e "\n📦 容器: $container"
  kubectl logs $POD_NAME -n $NAMESPACE -c $container --tail=20
done

# 4. 檢查前一個容器 (如果 CrashLoopBackOff)
echo -e "\n🔄 前一個容器日誌:"
kubectl logs $POD_NAME -n $NAMESPACE --previous --tail=50 2>/dev/null || echo "無前一個容器日誌"

# 5. 檢查資源限制
echo -e "\n💾 資源使用:"
kubectl top pod $POD_NAME -n $NAMESPACE 2>/dev/null || echo "Metrics Server 未啟用"

# 6. 檢查節點狀態
NODE=$(kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.nodeName}')
if [ -n "$NODE" ]; then
  echo -e "\n🖥️  節點資源:"
  kubectl top node $NODE 2>/dev/null
fi

# 7. 檢查 PVC (如果有)
echo -e "\n💿 PVC 狀態:"
kubectl get pvc -n $NAMESPACE -o wide | grep $(kubectl get pod $POD_NAME -n $NAMESPACE -o jsonpath='{.spec.volumes[*].persistentVolumeClaim.claimName}') || echo "無 PVC"

# 8. 執行互動式 Debug
echo -e "\n🛠️  啟動 Debug 容器? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
  kubectl debug $POD_NAME -n $NAMESPACE -it --image=busybox --share-processes --copy-to=${POD_NAME}-debug
fi
```

**網路連接問題**:

```bash
#!/bin/bash
# debug-network.sh

POD_NAME=$1
NAMESPACE=${2:-default}
TARGET_SERVICE=$3

echo "🌐 診斷網路連接: $POD_NAME -> $TARGET_SERVICE"

# 1. DNS 解析測試
echo -e "\n🔍 DNS 解析:"
kubectl exec $POD_NAME -n $NAMESPACE -- nslookup $TARGET_SERVICE

# 2. Ping 測試 (如果容器有 ping)
echo -e "\n📡 Ping 測試:"
kubectl exec $POD_NAME -n $NAMESPACE -- ping -c 3 $TARGET_SERVICE 2>/dev/null || echo "容器無 ping 命令"

# 3. TCP 連接測試
echo -e "\n🔌 TCP 連接測試:"
kubectl exec $POD_NAME -n $NAMESPACE -- nc -zv $TARGET_SERVICE 80 2>&1

# 4. 檢查 NetworkPolicy
echo -e "\n🛡️  NetworkPolicy:"
kubectl get networkpolicy -n $NAMESPACE

# 5. 檢查 Service Endpoints
echo -e "\n🎯 Service Endpoints:"
kubectl get endpoints $TARGET_SERVICE -n $NAMESPACE

# 6. Trace route
echo -e "\n🗺️  Traceroute:"
kubectl exec $POD_NAME -n $NAMESPACE -- traceroute -m 5 $TARGET_SERVICE 2>/dev/null || echo "容器無 traceroute"
```

### 9.2 效能瓶頸分析

**應用程式 Profiling**:

```javascript
// profiling-middleware.js
const v8Profiler = require('v8-profiler-next');
const fs = require('fs');

class PerformanceProfiler {
  constructor() {
    this.profiles = new Map();
  }

  // CPU Profiling
  startCPUProfile(name) {
    v8Profiler.startProfiling(name, true);
  }

  stopCPUProfile(name) {
    const profile = v8Profiler.stopProfiling(name);
    profile.export((error, result) => {
      fs.writeFileSync(`./profiles/${name}-${Date.now()}.cpuprofile`, result);
      profile.delete();
    });
  }

  // Heap Snapshot
  takeHeapSnapshot(name) {
    const snapshot = v8Profiler.takeSnapshot(name);
    snapshot.export((error, result) => {
      fs.writeFileSync(`./profiles/${name}-${Date.now()}.heapsnapshot`, result);
      snapshot.delete();
    });
  }

  // Express Middleware
  middleware() {
    return async (req, res, next) => {
      const profileName = `${req.method}-${req.path}`;

      // 隨機 profiling (1% 的請求)
      const shouldProfile = Math.random() < 0.01;

      if (shouldProfile) {
        this.startCPUProfile(profileName);

        res.on('finish', () => {
          this.stopCPUProfile(profileName);
        });
      }

      next();
    };
  }

  // 定期 Heap Snapshot
  scheduleHeapSnapshots(intervalMinutes = 60) {
    setInterval(() => {
      this.takeHeapSnapshot('scheduled');
    }, intervalMinutes * 60 * 1000);
  }
}

module.exports = PerformanceProfiler;
```

---

## Part 10: 真實案例研究

### 案例 1: Netflix - Chaos Engineering 先驅

**背景**:
- 全球最大串流平台
- 每天服務 2 億用戶
- 微服務架構 (1000+ 服務)

**挑戰**:
- AWS 區域故障導致服務中斷 (2011)
- 需要驗證系統韌性

**解決方案 - Chaos Monkey**:

```python
# chaos-monkey-lite.py - 簡化版實作
import random
import time
import boto3
from datetime import datetime, time as dt_time

class ChaosMonkey:
    def __init__(self, enabled=True, business_hours_only=True):
        self.enabled = enabled
        self.business_hours_only = business_hours_only
        self.ec2 = boto3.client('ec2')
        self.autoscaling = boto3.client('autoscaling')

    def is_business_hours(self):
        """只在工作時間執行 (更容易發現問題)"""
        now = datetime.now().time()
        return dt_time(9, 0) <= now <= dt_time(17, 0)

    def should_run(self):
        """決定是否執行"""
        if not self.enabled:
            return False

        if self.business_hours_only and not self.is_business_hours():
            return False

        # 1% 機率執行
        return random.random() < 0.01

    def get_target_instances(self):
        """獲取可以被終止的實例"""
        # 只針對有特定標籤的實例
        response = self.ec2.describe_instances(
            Filters=[
                {'Name': 'tag:chaos-monkey', 'Values': ['enabled']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )

        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # 檢查 ASG 是否有足夠的實例
                asg_name = self._get_asg_name(instance)
                if asg_name and self._asg_has_min_instances(asg_name):
                    instances.append(instance['InstanceId'])

        return instances

    def _get_asg_name(self, instance):
        """獲取實例所屬的 ASG"""
        for tag in instance.get('Tags', []):
            if tag['Key'] == 'aws:autoscaling:groupName':
                return tag['Value']
        return None

    def _asg_has_min_instances(self, asg_name, min_count=3):
        """確認 ASG 有足夠的實例"""
        response = self.autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )

        if response['AutoScalingGroups']:
            asg = response['AutoScalingGroups'][0]
            return len(asg['Instances']) > min_count

        return False

    def terminate_instance(self, instance_id):
        """終止實例"""
        print(f"🐵 Chaos Monkey 終止實例: {instance_id}")

        self.ec2.terminate_instances(InstanceIds=[instance_id])

        # 記錄到 CloudWatch Logs
        self._log_termination(instance_id)

    def run(self):
        """執行 Chaos Monkey"""
        if not self.should_run():
            return

        instances = self.get_target_instances()
        if not instances:
            print("沒有符合條件的實例")
            return

        # 隨機選擇一個實例
        target = random.choice(instances)
        self.terminate_instance(target)

# 使用 (Lambda 函數)
def lambda_handler(event, context):
    chaos = ChaosMonkey(
        enabled=True,
        business_hours_only=True
    )

    chaos.run()

    return {'statusCode': 200}
```

**成果**:
- 系統韌性大幅提升
- 2015 年 AWS 大規模故障,Netflix 零影響
- Simian Army 工具套件 (Chaos Kong, Latency Monkey 等)

---

### 案例 2: Spotify - Multi-Cloud 策略

**背景**:
- 4.5 億用戶
- 原本全部在自建資料中心
- 2016 年開始遷移到 GCP

**挑戰**:
- 零停機遷移
- 保持服務可用性 > 99.9%

**解決方案 - 混合雲架構**:

```yaml
# spotify-deployment-strategy.yaml
# 使用 Istio 實現多雲流量分配

apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: music-service
spec:
  hosts:
    - music-service
  http:
    - match:
        - headers:
            canary:
              exact: "true"
      route:
        - destination:
            host: music-service
            subset: gcp
          weight: 100

    - route:
        # 漸進式遷移: 逐步增加 GCP 流量
        - destination:
            host: music-service
            subset: onprem
          weight: 30  # 30% 本地資料中心
        - destination:
            host: music-service
            subset: gcp
          weight: 70  # 70% GCP

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: music-service
spec:
  host: music-service
  subsets:
    - name: onprem
      labels:
        location: onprem
    - name: gcp
      labels:
        location: gcp
```

**成果**:
- 2018 年完成遷移
- 基礎設施成本降低 ~30%
- 部署速度提升 4x

---

### 案例 3: Airbnb - Kubernetes at Scale

**背景**:
- 2018 年開始 Kubernetes 遷移
- 1000+ 服務
- 峰值 QPS > 100萬

**優化實踐**:

```yaml
# airbnb-optimization.yaml

# 1. 使用 Cluster Autoscaler
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-priority-expander
  namespace: kube-system
data:
  priorities: |-
    10:
      - .*-spot-.*
    50:
      - .*-ondemand-.*

---
# 2. Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: myapp-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  updatePolicy:
    updateMode: "Auto"  # 自動調整 requests
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 2
          memory: 4Gi

---
# 3. HPA + Custom Metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 10
  maxReplicas: 1000
  metrics:
    # CPU
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # 自定義 - 請求隊列長度
    - type: External
      external:
        metric:
          name: sqs_queue_length
        target:
          type: AverageValue
          averageValue: "30"

    # 自定義 - 請求延遲
    - type: Pods
      pods:
        metric:
          name: http_request_duration_p95
        target:
          type: AverageValue
          averageValue: "200m"  # 200ms
```

**成果**:
- 部署頻率: 2次/天 → 20次/天
- 基礎設施成本降低 40%
- P99 延遲改善 50%

---

## 總結

本深度技術指南涵蓋了 DevOps 的進階主題:

✅ **CI/CD 架構** - 完整 Pipeline 設計和最佳實踐
✅ **GitOps** - ArgoCD 實作和聲明式部署
✅ **容器編排** - Docker 優化和 Kubernetes 生產配置
✅ **基礎設施即代碼** - Terraform 模組化設計
✅ **可觀測性** - Metrics, Logging, Tracing 三支柱
✅ **DevSecOps** - 安全掃描、Runtime 監控、Policy Enforcement
✅ **成本優化** - 雲端成本監控、資源 Right-Sizing、Spot 實例
✅ **災難恢復** - 備份策略、高可用架構、Chaos Engineering
✅ **Troubleshooting** - 問題診斷、效能分析
✅ **真實案例** - Netflix、Spotify、Airbnb 的 DevOps 實踐

### 關鍵要點

1. **自動化優先**: 一切能自動化的都應該自動化
2. **可觀測性**: 沒有觀測就無法優化
3. **安全左移**: 在開發早期整合安全
4. **持續改進**: DevOps 是旅程,不是目的地
5. **文化轉變**: 技術工具只是一部分,文化更重要

---

## 📚 延伸閱讀

- [DevOps SOP 完整版](./SOP.md)
- [DevOps QuickRef 快速參考](./SOP_QuickRef.md)
- [DevOps 快速啟動指令集](../../prompts/scenario-prompts/devops-prompts.md)
- [devops-setup-flow Workflow](../../workflow/scenario-specific/devops-setup-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（基礎設施架構設計）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（CI 測試自動化）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（Pipeline 腳本開發）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（DevSecOps）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端 CI/CD，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端自動化測試，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（效能監控整合，選用）

### 相關 Skills
- `/devops-github-actions` - GitHub Actions CI/CD Pipeline 建置
- `/devops-gitlab-ci` - GitLab CI/CD Pipeline 建置
- `/devops-docker` - Docker 容器化配置（Dockerfile、docker-compose）
- `/devops-kubernetes` - Kubernetes 部署配置（Deployment、Service、Ingress）
- `/devops-monitoring` - 監控告警系統（Prometheus/Grafana）
- `/release-management` - 版本發布流程管理
- `/security-audit` - 安全審查（OWASP Top 10、DevSecOps）
- `/integration-database` - 資料庫整合（PostgreSQL 備份、連線池）
- `/performance-optimization` - 效能基準測試整合 CI/CD
- `/mobile-development` - 行動端 CI/CD（涉及 Android/iOS/macOS 時）

---

**文檔版本: v0.01
**最後更新**: 2025-10-29
**維護者**: AISDLC Framework Team
