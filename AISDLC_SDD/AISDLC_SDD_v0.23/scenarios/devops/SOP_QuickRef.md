# DevOps & CI/CD Setup - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: CI/CD 建立、DevOps 流程優化、自動化部署

---

## 🎯 一頁總覽

### 適用場景
✅ 建立 CI/CD Pipeline
✅ 自動化測試和部署
✅ 容器化和編排
✅ 監控和日誌系統建立

### 不適用場景
❌ 功能開發（請用 Greenfield）
❌ Bug 修復（請用 Brownfield）
❌ 安全評估（請用 Security）

---

## 📋 7 階段快速流程

```
總時間: 1-3 天

┌─────────────────────────────────────────────┐
│ 階段 1: 現狀評估 (2-3 小時) 🔴               │
│ └─ 流程分析 → 痛點識別 → 目標設定           │
├─────────────────────────────────────────────┤
│ 階段 2: 工具選擇 (2-3 小時) 🔴               │
│ └─ CI/CD 平台 → Container → 監控工具        │
├─────────────────────────────────────────────┤
│ 階段 3: CI Pipeline (3-4 小時) 🔴            │
│ └─ 構建 → 測試 → 程式碼檢查 → Artifact      │
├─────────────────────────────────────────────┤
│ 階段 4: CD Pipeline (4-6 小時) 🟡            │
│ └─ 部署策略 → 環境配置 → Rollback           │
├─────────────────────────────────────────────┤
│ 階段 5: 容器化 (4-6 小時) 🟡                 │
│ └─ Dockerfile → Registry → Orchestration    │
├─────────────────────────────────────────────┤
│ 階段 6: 監控系統 (3-4 小時) 🟡               │
│ └─ Metrics → Logs → Alerts → Dashboard      │
├─────────────────────────────────────────────┤
│ 階段 7: 文檔與培訓 (2-3 小時) ✅             │
│ └─ Runbook → SOP → 團隊培訓                 │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速啟動

```
提示詞:
「請載入 AISDLC_SDD_INIT.md (v0.01)，我需要建立 CI/CD Pipeline」

或具體描述:
「Node.js 應用需要自動化部署到 AWS」
「Docker 容器化並部署到 Kubernetes」
「建立監控和告警系統」
```

---

## 🛠️ CI/CD 工具快速選擇

### CI/CD 平台對比

| 平台 | 優點 | 適用場景 | 推薦指數 |
|------|------|---------|---------|
| **GitHub Actions** | 與 GitHub 整合好、免費額度 | GitHub 專案 | ⭐⭐⭐⭐⭐ |
| **GitLab CI** | 完整 DevOps 平台 | GitLab 用戶 | ⭐⭐⭐⭐⭐ |
| **Jenkins** | 高度客製化、插件豐富 | 企業級、複雜需求 | ⭐⭐⭐⭐ |
| **CircleCI** | 速度快、易用 | 中小型專案 | ⭐⭐⭐⭐ |
| **Travis CI** | 簡單、開源友善 | 開源專案 | ⭐⭐⭐ |

### 快速決策

```yaml
選擇 GitHub Actions 如果:
- 使用 GitHub
- 需要快速上手
- 預算有限

選擇 GitLab CI 如果:
- 使用 GitLab
- 需要完整 DevOps 平台
- Self-hosted 需求

選擇 Jenkins 如果:
- 複雜的 Pipeline 需求
- 大量客製化
- 已有 Jenkins 基礎設施

選擇 Cloud CI/CD 如果:
- 快速啟動
- 不想維護基礎設施
- 多雲部署
```

---

## ⚡ CI Pipeline 快速範本

### Node.js + GitHub Actions

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci && npm run lint && npm test && npm run build
```

### 🆕 Spring Boot (Java) + Next.js (TypeScript) + PostgreSQL

```yaml
name: CI - Spring Boot + Next.js
on:
  push:
    branches: [main, develop]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: testdb }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { java-version: '21', distribution: 'temurin', cache: 'gradle' }
      - run: chmod +x gradlew
      - run: ./gradlew checkstyleMain              # Lint
      - run: ./gradlew flywayMigrate               # DB Migration
        env: { SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb }
      - run: ./gradlew test jacocoTestCoverageVerification  # Test + Coverage≥80%
        env: { SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb }
      - run: ./gradlew bootJar -x test             # Build
      - uses: actions/upload-artifact@v4
        with: { name: backend-jar, path: build/libs/*.jar }

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
        working-directory: frontend
      - run: npm run type-check && npm run lint && npm run test -- --coverage && npm run build
        working-directory: frontend
```

---

## 🚢 容器化快速指南

### Dockerfile 最佳實踐

**Node.js 範例**:
```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
USER node
CMD ["node", "dist/index.js"]
```

**Python 範例**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
USER nobody
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000"]
```

### Docker Compose 快速配置

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://db:5432/mydb
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## 📊 部署策略快速決策

### 部署策略對比

| 策略 | 停機時間 | 風險 | 複雜度 | 成本 | 適用場景 |
|------|---------|------|--------|------|---------|
| **Rolling** | 無 | 🟡 中 | 🟢 低 | 💰 低 | 一般應用 |
| **Blue-Green** | 無 | 🟢 低 | 🟡 中 | 💰💰 高 | 高可用性 |
| **Canary** | 無 | 🟢 低 | 🔴 高 | 💰💰 高 | 風險管控 |
| **Recreate** | 🔴 有 | 🔴 高 | 🟢 低 | 💰 低 | 開發/測試 |

### Rolling Deployment

```yaml
優點:
✅ 無停機時間
✅ 逐步更新，可快速回滾
✅ 資源使用效率高

缺點:
❌ 短暫新舊版本共存
❌ 資料庫遷移需謹慎

適用: 大部分 Web 應用

實施:
- Kubernetes: rollingUpdate strategy
- 每次更新 20-25% 實例
- Health check 確保穩定後繼續
```

### Blue-Green Deployment

```yaml
優點:
✅ 零停機
✅ 快速回滾（切換流量）
✅ 完整測試新版本

缺點:
❌ 需要雙倍資源
❌ 資料庫同步複雜

適用: 關鍵業務系統

實施:
- 維護兩套完整環境
- 新版本部署到 Green
- 測試通過後切換流量
- Blue 環境保留作為備份
```

### Canary Deployment

```yaml
優點:
✅ 漸進式風險控制
✅ 實際流量測試
✅ 問題影響範圍小

缺點:
❌ 複雜度高
❌ 需要監控支援

適用: 大規模應用

實施:
- 5% 流量 → 新版本
- 監控指標正常 → 20%
- 繼續監控 → 50%
- 最終 → 100%
```

---

## 📈 監控與告警快速配置

### 監控三支柱

```yaml
1. Metrics (指標):
工具: Prometheus + Grafana
關鍵指標:
- CPU/Memory 使用率
- Request Rate (RPS)
- Response Time (P50/P95/P99)
- Error Rate
- Saturation (飽和度)

2. Logs (日誌):
工具: ELK Stack / Loki
關鍵日誌:
- Application Logs
- Access Logs
- Error Logs
- Audit Logs

3. Traces (追蹤):
工具: Jaeger / OpenTelemetry
用途:
- 分散式追蹤
- 效能瓶頸識別
- 依賴關係可視化
```

### 快速 Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'app'
    static_configs:
      - targets: ['app:3000']
    
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 告警規則範例

```yaml
groups:
  - name: app-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
        
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 10m
        annotations:
          summary: "P95 latency > 1s"
```

---

## 🎯 成熟度評估

### DevOps 成熟度模型

```yaml
Level 0: Manual (手動)
□ 手動部署
□ 無版本控制
□ 無測試自動化
行動: 建立基礎 CI

Level 1: Basic (基礎)
✅ 版本控制 (Git)
✅ 基本 CI
□ 自動化測試
□ 自動化部署
行動: 完善測試和 CD

Level 2: Automated (自動化)
✅ 完整 CI/CD
✅ 自動化測試 > 70%
✅ 自動化部署
□ 監控告警
□ Infrastructure as Code
行動: 實施監控和 IaC

Level 3: Optimized (優化)
✅ 完整自動化
✅ 監控告警完善
✅ IaC
✅ 快速回滾
□ 持續改進
行動: 優化流程和指標

Level 4: Advanced (進階)
✅ 全自動化
✅ Chaos Engineering
✅ 自我修復
✅ 預測性監控
行動: AI/ML 整合
```

---

## ✅ DevOps 檢查清單

### CI/CD 就緒檢查

```yaml
程式碼管理:
□ 使用 Git 版本控制
□ 分支策略明確 (GitFlow/Trunk-based)
□ Code Review 流程
□ Commit Message 規範

CI Pipeline:
□ 自動化構建
□ 自動化測試 (Unit + Integration)
□ 程式碼品質檢查 (Linter, SAST)
□ 測試覆蓋率報告
□ Artifact 管理

CD Pipeline:
□ 環境配置管理
□ 自動化部署 (至少 Staging)
□ Smoke Tests
□ Rollback 機制
□ 部署通知

基礎設施:
□ Infrastructure as Code (Terraform/CloudFormation)
□ 容器化 (Docker)
□ 編排工具 (K8s/ECS/Docker Compose)
□ Secret 管理 (Vault/AWS Secrets Manager)

監控:
□ Application Metrics
□ Infrastructure Metrics
□ Logs 集中管理
□ 告警規則設定
□ Dashboard 建立

安全:
□ Secret 掃描
□ 依賴漏洞掃描
□ Container 掃描
□ HTTPS/TLS
□ 最小權限原則
```

---

## 🚨 常見陷阱

### ❌ 避免這些錯誤

**1. 過早優化**
```
錯誤: 一開始就建立複雜的 Pipeline

正確: 從簡單的 CI 開始，逐步優化
- MVP: Build + Test
- v1: + Lint + Coverage
- v2: + CD
- v3: + 多環境部署
```

**2. 忽略監控**
```
錯誤: 部署後不監控

正確: 先建立監控，再自動化部署
- 沒有監控 = 盲目飛行
- 告警 > 手動檢查
- Dashboard > SSH 登入查看
```

**3. 沒有 Rollback 計畫**
```
錯誤: 只考慮成功場景

正確: 每次部署都要有 Rollback 方案
- 一鍵回滾
- 測試回滾流程
- 保留前 N 個版本
```

**4. Secret 管理不當**
```
錯誤: Secret 寫在 code 或 .env 提交

正確: 使用 Secret 管理工具
- GitHub Secrets
- AWS Secrets Manager
- HashiCorp Vault
- 環境變數注入
```

---

## 🔗 延伸閱讀

- [DevOps SOP 完整版](./SOP.md)
- [DevOps DeepDive 深度指南](./SOP_DeepDive.md)
- [DevOps 快速啟動指令集](../../prompts/scenario-prompts/devops-prompts.md)
- [devops-setup-flow Workflow](../../workflow/scenario-specific/devops-setup-flow.md)
- [CI/CD 模板](../../docs_template/scenario_specific/devops/CICD_Pipeline_Template.md)
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
- `/devops-github-actions` - GitHub Actions CI/CD Pipeline（Spring Boot + Next.js 範本）
- `/devops-gitlab-ci` - GitLab CI/CD Pipeline
- `/devops-docker` - Docker 容器化配置（Spring Boot/Next.js 多階段建置）
- `/devops-kubernetes` - Kubernetes 部署配置
- `/devops-monitoring` - 監控告警系統（含 Spring Boot Actuator 整合）
- `/testing-strategy` - CI 測試策略設計（覆蓋率門檻、測試分層）🆕
- `/release-management` - 版本發布管理
- `/security-audit` - 安全審查（DevSecOps：SAST/SCA/Container Scan）
- `/integration-database` - PostgreSQL + Flyway/Liquibase DB Migration CI 整合 🆕
- `/mobile-development` - Android（Gradle CI）/ macOS（fastlane）CI/CD 🆕

---

**提示**:
- 從小開始，持續改進
- 監控是 DevOps 的眼睛
- 自動化測試是部署的信心來源
- DevOps 是文化，不只是工具

---

**文檔版本: v0.01
**最後更新**: 2026-03-30

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

規格凍結（SPEC_FROZEN）→ `python -m autoclaude.tools.sdd_compile` 編譯 playbook → 人工 review YAML → `python -m autoclaude playbooks/sdd_bridge.yaml` 執行（🔴 人工閘門不可跳過）。
全文見：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`。
