# DevOps Setup & CI/CD Implementation DevOps 建置與 CI/CD 實作 SOP

**版本**: v0.01 | **最後更新**: 2026-02-12
> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如文檔路徑、配置檔案等）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：CI/CD Pipeline 建置、容器化部署、基礎設施自動化、監控告警設定

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依專案規模):
    - 小型專案: 1-2 週 (基本 CI/CD + Docker 部署)
    - 中型專案: 2-4 週 (完整 DevOps + 監控告警)
    - 大型專案: 1-2 月 (Kubernetes + IaC + 多環境)
- 🔨 **實際執行階段**: 1-2 週 (依基礎設施複雜度而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行 DevOps 策略、Pipeline 設計、IaC 方案規劃的時間
> - **執行時間**指實際建置 CI/CD Pipeline、配置基礎設施的時間
> - 小型專案指基本 CI/CD(GitHub Actions) + Docker 部署至單一伺服器
> - 中型專案指完整 DevOps 流程(CI/CD + IaC + 監控告警 + 備份恢復)
> - 大型專案指企業級方案(Kubernetes 叢集 + IaC + 多環境管理 + FinOps)

**涉及角色**：DevOps-Engineer, SD, QA-Automation, Dev-Developer, Security-Engineer

**最終產出**：環境規劃文件 + CI/CD Pipeline 配置 + 容器化方案 + 部署腳本 + 監控方案 + 災難恢復計畫

---

## 🤝 協作模式 (Phase 2: v0.03, v0.01 更新)

### 主要協作模式

#### 1. Lead-Support (主導-支援) + Parallel-Convergence (並行收斂)
- **主導 Agent**: DevOps-Engineer (Lead & Coordinator)
- **支援 Agents**: SD-Architect (基礎設施架構), QA-Automation (測試整合CI/CD)
- **使用階段**: 全流程
- **模式說明**: DevOps-Engineer 主導並協調多個並行任務

#### 2. Parallel-Convergence 並行任務
```
DevOps-Engineer 分配任務
    ↓
┌─────────────────┬────────────────────┬──────────────┐
│ devops: CI/CD   │ qa-auto: Test      │ sd: Infra    │
│ Pipeline設計     │ Integration        │ Architecture │
└─────────────────┴────────────────────┴──────────────┘
    ↓
DevOps-Engineer 整合所有配置
    ↓
> 🔴 **人機協作點：並行任務整合確認**
>
> **AI 提供**：
> - 整合後的 DevOps 配置方案
>
> **需人工確認**：
> - ✅ 各項配置整合無衝突
> - ✅ 配置符合團隊實際需求
>
> **產出文件**：
> - DevOps Configuration Summary
```

### 次要協作模式

#### 3. Sequential-Handoff (順序交接)
- **使用階段**: DevOps → 部署腳本 → Dev → 測試 → QA-Automation → 整合CI/CD
- **模式說明**: 部署流程建立後交接給團隊使用

---

## 🔒 Layer 0: Security Baseline（強制前置）

> **🔴 v0.01 CI/CD 強化**: 所有 CI/CD Pipeline 建置**必須先完成 Layer 0 安全基線**，再進入後續階段。
> Layer 0 是跨所有情境的強制安全基線，包含 Secret Detection、SCA、License Compliance。

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-baseline.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-baseline-template.yml)

---

## 🔨 Layer 1: Build & Verify（強制前置）

> **🔴 v0.01 CI/CD 強化**: Layer 0 通過後，**必須完成 Layer 1 建置驗證**。
> Layer 1 確保所有程式碼通過 Lint、Build、Unit Test + Coverage Gate 三道關卡。

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0.5](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/build-verify.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/build-verify-template.yml)

---

## 🛡️ 增強安全掃描: IaC SAST + Container Scan（Advanced 等級）

> **DevOps 情境安全等級: Advanced** (L0 + L1 + IaC SAST + Container Scan)
> DevOps 情境著重 IaC 配置安全掃描與容器映像安全。

| 掃描類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **IaC SAST** | Semgrep / Checkov | ⚠️ IaC 配置掃描 | Terraform/Helm/K8s 配置安全 |
| **Container Scan** | Trivy / Grype | 🔴 強制 | 所有建置映像漏洞掃描 |

**配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-scan-enhanced.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml)

### 🔔 Event-Driven Agent Notification（🔴 強制）

> DevOps 情境的 PR 事件通知 + 部署通知為強制。情境專屬觸發：IaC validate + plan 結果通知。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 🔗 Skills 整合對照表

> 💡 **說明**: 以下列出各階段可觸發的 Claude Code Skills（斜線指令），協助加速 DevOps 建置。

| SOP 階段 | 可觸發 Skill | 用途說明 |
|---------|-------------|---------|
| 前置：安全基線 | `/security-audit` | OWASP Top 10 安全審查、Secret 掃描 |
| 階段 1：啟動 | — | 手動載入 AISDLC_INIT.md |
| 階段 2：環境規劃 | `/sd-architect` | 基礎設施架構設計（含多技術棧環境） |
| 階段 3：CI Pipeline | `/devops-github-actions`、`/devops-gitlab-ci`、`/testing-strategy` | CI Pipeline 建置（依平台）、測試策略設計 |
| 階段 3：DB Migration | `/integration-database` | PostgreSQL + Flyway/Liquibase DB Migration CI 整合 |
| 階段 4：CD Pipeline | `/devops-kubernetes`、`/release-management` | K8s 部署配置、版本發布管理 |
| 階段 5：容器化 | `/devops-docker` | Dockerfile（Spring Boot/Next.js 多階段建置）、docker-compose |
| 階段 6：監控告警 | `/devops-monitoring` | Prometheus/Grafana 監控、Spring Boot Actuator 整合 |
| 階段 6：安全整合 | `/security-audit` | DevSecOps：SAST/SCA/Container Scan |
| 階段 7：文檔 | `/documentation-api` | API 文檔、Runbook 生成 |
| 行動端 CI/CD | `/mobile-development` | Android（Gradle CI）/ macOS（Xcode/fastlane）建置與分發 Pipeline |
| 效能測試 | `/performance-optimization` | k6/Locust 負載測試整合 CI/CD |

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 專案代碼庫存取權限
- [ ] 雲平台或伺服器存取權限 (AWS/GCP/Azure/Self-hosted)
- [ ] DevOps 目標描述
- [ ] 現有基礎設施資訊 (如有)
- [ ] 團隊技能和工具偏好

### 選擇性材料
- [ ] 現有部署流程文檔
- [ ] 監控需求清單
- [ ] 合規和安全要求
- [ ] 成本預算
- [ ] 流量預估和擴展需求

### 環境檢查
- [ ] Git 版本控制系統已設定
- [ ] CI/CD 平台帳號 (GitHub Actions/GitLab CI/Jenkins)
- [ ] 容器 Registry 存取 (Docker Hub/ECR/GCR)
- [ ] 雲平台 CLI 工具已安裝

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: DevOps 建置常因缺乏基礎設施資訊或權限而延遲。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **部署腳本** | 🔴 高 | • **方案 1**: 檢查代碼庫中的 CI/CD 配置檔 (`.github/workflows`, `Jenkinsfile`)<br>• **方案 2**: 訪談 DevOps 或維運人員記錄現有流程<br>• **方案 3**: 參考同技術棧專案的部署腳本模板<br>• **方案 4**: 使用 DevOps-Engineer Agent 生成基礎部署配置 | +2-4 小時 |
| **基礎設施配置 (IaC)** | 🔴 高 | • **方案 1**: 使用雲平台 Console 手動配置,後續匯出為 IaC<br>• **方案 2**: 參考同類專案的 Terraform/CloudFormation 模板<br>• **方案 3**: 使用 Terraformer 逆向生成現有基礎設施代碼<br>• **方案 4**: 先手動部署驗證,後續自動化 | +3-6 小時 |
| **監控告警配置** | 🟡 中 | • **方案 1**: 使用免費監控工具快速搭建 (Prometheus + Grafana)<br>• **方案 2**: 使用雲平台內建監控 (CloudWatch, Stackdriver)<br>• **方案 3**: 先建立基礎監控 (CPU、Memory、Disk),後續補充應用層監控<br>• **方案 4**: 暫時使用日誌監控替代 | +2-4 小時 |
| **災難恢復計畫 (DR Plan)** | 🟡 中 | • **方案 1**: 使用雲平台自動備份功能 (RDS 自動快照)<br>• **方案 2**: 編寫簡易備份腳本,定時執行<br>• **方案 3**: 先建立最小 DR 計畫 (RTO/RPO 定義 + 基本恢復步驟)<br>• **方案 4**: 暫時跳過,優先建立 CI/CD | +1-2 小時 |
| **雲平台存取權限** | 🟡 中 | • **方案 1**: 向管理員申請必要權限 (最小權限原則)<br>• **方案 2**: 先使用個人帳號測試,後續轉移到團隊帳號<br>• **方案 3**: 使用免費試用帳號快速驗證<br>• **方案 4**: 暫時使用本地 Docker 環境模擬 | +0.5-1 天 |
| **成本預算** | 🟢 低 | • **方案 1**: 使用雲平台成本計算器估算 (AWS/GCP/Azure Pricing Calculator)<br>• **方案 2**: 參考同規模專案的成本數據<br>• **方案 3**: 先使用最小配置,根據實際使用調整<br>• **方案 4**: 設定成本告警,避免超支 | +0.5-1 小時 |
| **流量預估** | 🟢 低 | • **方案 1**: 與產品/業務團隊確認預期使用者數和使用模式<br>• **方案 2**: 參考同類產品的流量數據<br>• **方案 3**: 使用 T-shirt sizing 粗估 (S/M/L/XL)<br>• **方案 4**: 先用最小配置,配合自動擴展動態調整 | +0.5-1 小時 |

### 無部署腳本時的應對流程

若完全沒有部署腳本,建議採用「**CI/CD 快速啟動策略**」:

#### 方案 A: GitHub Actions 快速模板 (推薦) - 2-4 小時

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Push to Registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push myapp:${{ github.sha }}

      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            docker pull myapp:${{ github.sha }}
            docker stop myapp || true
            docker rm myapp || true
            docker run -d --name myapp -p 80:3000 myapp:${{ github.sha }}
```

**優點**: 免費、簡單、雲端執行
**適用**: 中小型專案

#### 方案 B: Docker Compose 簡易部署 - 1-2 小時

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: myapp:latest
    ports:
      - "80:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
    restart: always

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    restart: always

volumes:
  postgres_data:
```

**部署指令**:
```bash
# 初次部署
docker-compose -f docker-compose.prod.yml up -d

# 更新部署
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

**優點**: 簡單直接
**適用**: 單一伺服器部署

### 無監控系統時的快速搭建

若缺少監控系統,建議採用「**Prometheus + Grafana 快速部署**」- 2 小時:

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

### 無災難恢復計畫時的最小方案

若缺少 DR 計畫,建議採用「**最小 DR 策略**」- 2-3 小時:

1. **定義 RTO/RPO** - 30 分鐘
   - RTO (Recovery Time Objective): 系統恢復時間 < 4 小時
   - RPO (Recovery Point Objective): 可接受的資料遺失 < 1 小時

2. **資料庫自動備份** - 1 小時
   ```bash
   # 每日備份腳本
   #!/bin/bash
   pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > /backups/db_$(date +%Y%m%d).sql.gz
   aws s3 cp /backups/db_$(date +%Y%m%d).sql.gz s3://my-backups/database/
   ```

3. **恢復程序文檔** - 1 小時
   ```markdown
   # 災難恢復程序

   ## 資料庫恢復
   1. 下載最新備份
   2. 恢復資料庫
   3. 驗證資料完整性

   ## 應用程式恢復
   1. 切換到備援環境
   2. 更新 DNS 記錄
   3. 驗證服務正常
   ```

---

## 💰 免費工具替代方案

> 💡 **成本優化策略**: 許多企業級 DevOps 工具都有優秀的開源替代方案，適合中小型團隊或預算有限的專案。

### 核心工具替代對照表

| 工具類別 | 商業工具 💰 | 免費/開源替代方案 ✅ | 功能對比 | 安裝指令 |
|---------|-----------|-------------------|---------|---------|
| **CI/CD** | Jenkins Enterprise<br>CircleCI<br>Travis CI Pro | **GitHub Actions** (2000 分鐘/月免費)<br>**GitLab CI** (400 分鐘/月免費)<br>**Drone CI** (開源) | 功能完整度: 95%<br>學習曲線: 低<br>維護成本: 低 | **GitHub Actions**: 內建於 GitHub<br>**GitLab CI**: 內建於 GitLab<br>**Drone CI**:<br>`docker run -d -p 80:80 drone/drone:2` |
| **監控** | Datadog ($15-23/host/月)<br>New Relic ($99-349/月)<br>Dynatrace | **Prometheus + Grafana** (完全免費)<br>**VictoriaMetrics** (Prometheus 相容) | 功能完整度: 90%<br>資料保留: 無限制<br>客製化: 完全控制 | **Prometheus + Grafana**:<br>`docker-compose up -d`<br>(`prometheus.yml` + `grafana` service)<br><br>**VictoriaMetrics**:<br>`docker run -d -p 8428:8428 victoriametrics/victoria-metrics` |
| **日誌管理** | Splunk ($150/GB)<br>Datadog Logs<br>Sumo Logic | **ELK Stack** (Elasticsearch + Logstash + Kibana)<br>**Loki + Grafana** (輕量級)<br>**Graylog** | 功能完整度: 85%<br>儲存成本: 自行控制<br>適用規模: 中小型 | **ELK Stack**:<br>`docker run -d elastic/elasticsearch:8.11.0`<br>`docker run -d elastic/kibana:8.11.0`<br><br>**Loki + Grafana**:<br>`docker run -d grafana/loki:2.9.0`<br>`docker run -d grafana/promtail:2.9.0` |
| **IaC (基礎設施即代碼)** | Terraform Cloud ($0.00053/resource/hour)<br>Pulumi Service | **Terraform OSS** (開源版)<br>**OpenTofu** (Terraform fork)<br>**GitLab** (免費狀態儲存) | 功能完整度: 95%<br>限制: 無遠端協作 UI<br>狀態管理: 需自行配置 | **Terraform OSS**:<br>`brew install terraform` (macOS)<br>`apt install terraform` (Ubuntu)<br><br>**OpenTofu**:<br>`brew install opentofu`<br><br>**狀態儲存 (GitLab)**:<br>設定 `.tf` backend 為 GitLab HTTP |

**🎯 IaC 工具選擇指引（建議選擇單一工具）**：

> ⚠️ **重要**：建議團隊選擇**單一 IaC 工具**，避免維護多套工具增加成本

| 團隊背景 | 推薦工具 | 理由 |
|---------|---------|------|
| **DevOps/基礎設施團隊** | Terraform OSS | 業界標準、社群資源最豐富、多雲支援 |
| **開發團隊 (熟悉程式語言)** | Pulumi | 使用熟悉語言 (TypeScript/Python)、IDE 支援好 |
| **避免 HashiCorp 授權風險** | OpenTofu | Terraform 相容、完全開源 (MPL 2.0) |
| **AWS 專用** | AWS CDK | 原生整合、TypeScript/Python 支援 |
| **Kubernetes 專用** | Helm + Kustomize | K8s 原生、無需額外學習 |

**決策流程**：
```
團隊已有 Terraform 經驗？
├─ 是 → 繼續使用 Terraform OSS
└─ 否 → 主要雲平台？
         ├─ AWS 專用 → AWS CDK
         ├─ 多雲/混合雲 → Terraform OSS 或 OpenTofu
         └─ Kubernetes 專用 → Helm + Kustomize
```
| **Container Registry** | Docker Hub Pro ($5/月)<br>AWS ECR ($0.10/GB)<br>GCR | **GitHub Container Registry** (免費 500MB)<br>**GitLab Container Registry** (10GB 免費)<br>**Harbor** (自架) | 功能完整度: 100%<br>儲存上限: 依平台<br>私有倉庫: 無限制 | **GitHub CR**: 內建 (使用 `ghcr.io`)<br>**GitLab CR**: 內建<br>**Harbor** (Self-hosted):<br>`docker run -d -p 80:80 goharbor/harbor:v2.9.0` |
| **Secrets 管理** | HashiCorp Vault Enterprise<br>AWS Secrets Manager<br>Azure Key Vault | **HashiCorp Vault OSS** (開源版)<br>**SOPS** (加密 YAML/JSON)<br>**Git-crypt** | 功能完整度: 80%<br>企業功能: 無 DR 複製<br>適用: 中小團隊 | **Vault OSS**:<br>`docker run -d -p 8200:8200 vault:1.15`<br><br>**SOPS**:<br>`brew install sops` (macOS)<br>`apt install sops` (Ubuntu)<br><br>**Git-crypt**:<br>`brew install git-crypt` |
| **狀態儲存 (Terraform)** | Terraform Cloud<br>Terraform Enterprise | **AWS S3 + DynamoDB** (免費額度)<br>**GitLab HTTP Backend** (免費)<br>**Terraform OSS + Git** | 功能完整度: 90%<br>協作: 需手動鎖定<br>成本: AWS 免費額度內免費 | **S3 + DynamoDB Backend**:<br>```hcl<br>terraform {<br>  backend "s3" {<br>    bucket = "my-terraform-state"<br>    key    = "prod/terraform.tfstate"<br>    region = "us-east-1"<br>    dynamodb_table = "terraform-lock"<br>  }<br>}<br>```<br><br>**GitLab Backend**:<br>```hcl<br>terraform {<br>  backend "http" {<br>    address = "https://gitlab.com/api/v4/projects/PROJECT_ID/terraform/state/STATE_NAME"<br>  }<br>}<br>``` |
| **APM (應用效能監控)** | New Relic APM<br>Datadog APM<br>AppDynamics | **Jaeger** (分散式追蹤)<br>**Zipkin**<br>**OpenTelemetry + Grafana Tempo** | 功能完整度: 75%<br>追蹤深度: 完整<br>學習曲線: 中等 | **Jaeger**:<br>`docker run -d -p 16686:16686 jaegertracing/all-in-one:1.51`<br><br>**Zipkin**:<br>`docker run -d -p 9411:9411 openzipkin/zipkin` |
| **Load Testing** | BlazeMeter<br>LoadRunner | **k6** (Grafana Labs)<br>**Locust**<br>**JMeter** | 功能完整度: 90%<br>腳本語言: JavaScript/Python<br>CI/CD 整合: 優秀 | **k6**:<br>`brew install k6` (macOS)<br>`apt install k6` (Ubuntu)<br><br>**Locust**:<br>`pip install locust`<br><br>**JMeter**:<br>`brew install jmeter` |
| **Error Tracking** | Sentry ($26-80/月)<br>Rollbar | **Sentry Self-hosted** (免費)<br>**GlitchTip** (Sentry 相容)<br>**Bugsnag OSS** | 功能完整度: 95%<br>資料隱私: 完全控制<br>維護: 需自行管理 | **Sentry Self-hosted**:<br>`git clone https://github.com/getsentry/self-hosted.git`<br>`./install.sh`<br><br>**GlitchTip**:<br>`docker run -d -p 8000:8000 glitchtip/glitchtip` |

---

### 免費工具組合建議方案

#### 🏆 方案 A：完全免費方案（適合個人/小團隊）

```yaml
工具組合:
  CI/CD: GitHub Actions (2000 分鐘/月免費)
  監控: Prometheus + Grafana (自架於低成本 VPS)
  日誌: Loki + Grafana (輕量級,與監控共用)
  Registry: GitHub Container Registry (500MB 免費)
  Secrets: SOPS + Git-crypt (檔案加密)
  IaC: Terraform OSS + GitLab HTTP Backend
  APM: Jaeger (Docker 單機部署)
  Error Tracking: Sentry Self-hosted (Docker)

月成本估算: $0-10 (僅 VPS 成本,如使用 DigitalOcean $6/月)
```

**快速部署指令**:
```bash
# 1. 建立監控 Stack (Prometheus + Grafana + Loki)
cat <<EOF > docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]

  jaeger:
    image: jaegertracing/all-in-one:1.51
    ports: ["16686:16686"]
EOF

docker-compose -f docker-compose.monitoring.yml up -d

# 2. 設定 GitHub Actions (在 repo 中建立)
mkdir -p .github/workflows
cat <<EOF > .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test && npm run build
EOF

# 3. 設定 Terraform Backend (GitLab)
cat <<EOF > backend.tf
terraform {
  backend "http" {
    address = "https://gitlab.com/api/v4/projects/YOUR_PROJECT_ID/terraform/state/production"
    lock_address = "https://gitlab.com/api/v4/projects/YOUR_PROJECT_ID/terraform/state/production/lock"
    unlock_address = "https://gitlab.com/api/v4/projects/YOUR_PROJECT_ID/terraform/state/production/lock"
    username = "YOUR_GITLAB_USERNAME"
    password = "YOUR_GITLAB_ACCESS_TOKEN"
  }
}
EOF
```

---

#### 🥈 方案 B：混合方案（適合中型團隊,平衡成本與維護）

```yaml
工具組合:
  CI/CD: GitLab CI (免費 400 分鐘 + Self-hosted Runner)
  監控: VictoriaMetrics + Grafana (更高效能)
  日誌: Graylog (功能更完整)
  Registry: Harbor (自架,無限制)
  Secrets: Vault OSS (企業級安全)
  IaC: Terraform OSS + S3 Backend (AWS 免費額度)
  APM: OpenTelemetry + Tempo
  Error Tracking: GlitchTip (Sentry 相容)

月成本估算: $20-50 (中等 VPS + AWS S3 儲存)
```

**優勢**:
- ✅ 更高效能（VictoriaMetrics 比 Prometheus 快 10 倍）
- ✅ 更好的日誌查詢（Graylog 介面友善）
- ✅ 企業級 Secrets 管理（Vault）
- ✅ 無 Registry 容量限制（Harbor）

---

#### 🥉 方案 C：雲端免費額度方案（適合雲原生專案）

```yaml
工具組合:
  CI/CD: GitHub Actions (2000 分鐘) / GitLab CI (400 分鐘)
  監控: AWS CloudWatch (免費額度) / GCP Cloud Monitoring
  日誌: AWS CloudWatch Logs (5GB 免費)
  Registry: AWS ECR (500MB 免費) / GCP Artifact Registry
  Secrets: AWS Secrets Manager (30 天試用) → SOPS (長期)
  IaC: Terraform OSS + S3 Backend (免費額度)
  APM: AWS X-Ray (10 萬次免費)

月成本估算: $0-20 (在免費額度內)
```

**適用情境**:
- 已使用 AWS/GCP/Azure 雲平台
- 希望最小化維護工作
- 團隊規模 < 10 人

---

### 成本對比總覽

| 方案 | 商業工具總成本 | 免費方案成本 | 年度節省 |
|------|--------------|------------|---------|
| **完全免費方案 (A)** | $500-1000/月 | $0-10/月 | **$5,880-11,880/年** |
| **混合方案 (B)** | $500-1000/月 | $20-50/月 | **$5,400-11,760/年** |
| **雲端免費額度 (C)** | $500-1000/月 | $0-20/月 | **$5,760-12,000/年** |

---

### 遷移建議

#### 從商業工具遷移到開源工具的步驟

**階段 1：並行運行（1-2 週）**
```bash
# 同時運行商業工具和開源工具
# 驗證開源工具的準確性和穩定性
```

**階段 2：逐步切換（2-4 週）**
```bash
# 先切換非關鍵環境（Dev/Staging）
# 驗證無問題後再切換 Production
```

**階段 3：完全遷移（1 週）**
```bash
# 關閉商業工具訂閱
# 團隊培訓開源工具使用
```

---

### ⚠️ 注意事項

**開源工具的權衡（Trade-offs）**:

| 優點 ✅ | 缺點 ❌ |
|--------|--------|
| 完全免費或低成本 | 需要自行維護和更新 |
| 資料完全掌控 | 缺乏專業技術支援 |
| 高度客製化彈性 | 學習曲線可能較陡 |
| 無廠商鎖定風險 | 需要更多 DevOps 知識 |
| 社群活躍,快速迭代 | 某些企業功能可能缺失 |

**建議策略**:
1. **小團隊 (< 5 人)**: 選擇方案 A（完全免費）
2. **中型團隊 (5-20 人)**: 選擇方案 B（混合方案）
3. **大型團隊 (> 20 人)**: 考慮商業工具或混合使用
4. **關鍵系統**: 商業工具（確保 SLA 和支援）
5. **非關鍵系統**: 開源工具（降低成本）

---

### 🔐 Secret 管理方案深度比較

選擇 Secret 管理工具是 DevOps 安全的關鍵決策。以下提供詳細比較指引。

#### 方案比較矩陣

| 特性 | HashiCorp Vault | AWS Secrets Manager | SOPS | Git-crypt | 環境變數 |
|------|----------------|--------------------|----- |-----------|---------|
| **部署複雜度** | 高 | 低 | 低 | 低 | 無 |
| **成本** | OSS 免費 / Enterprise 付費 | $0.40/secret/月 | 免費 | 免費 | 免費 |
| **動態密鑰** | ✅ 支援 | ❌ 不支援 | ❌ 不支援 | ❌ 不支援 | ❌ 不支援 |
| **密鑰輪換** | ✅ 自動 | ✅ 自動 | 手動 | 手動 | 手動 |
| **審計日誌** | ✅ 完整 | ✅ CloudTrail | Git 歷史 | Git 歷史 | ❌ 無 |
| **多雲支援** | ✅ 優秀 | AWS 專用 | ✅ 優秀 | ✅ 優秀 | ✅ 優秀 |
| **學習曲線** | 陡峭 | 平緩 | 平緩 | 平緩 | 無 |
| **適合團隊規模** | 中大型 | 任意 | 小中型 | 小型 | 原型階段 |

#### 方案選擇決策樹

```
你的專案階段？
├─ 原型/POC → 環境變數 (.env + .gitignore)
├─ 生產環境 → 繼續評估...
     │
     └─ 主要雲平台？
         ├─ AWS 專用 → AWS Secrets Manager
         ├─ 多雲/混合雲 → 繼續評估...
              │
              └─ 團隊規模？
                  ├─ < 10 人 → SOPS + KMS
                  └─ >= 10 人 → HashiCorp Vault
```

#### 方案 1: HashiCorp Vault (推薦用於中大型團隊)

**優點**:
- 動態密鑰（自動生成臨時憑證）
- 完整的存取控制 (ACL/Policy)
- 密鑰輪換自動化
- 多種 Secrets Engine（Database, AWS, PKI...）

**缺點**:
- 部署和維護複雜度高
- 需要專人維護 HA 架構
- 學習曲線陡峭

**快速部署 (開發環境)**:
```bash
# Docker 單機部署
docker run -d --name vault \
  -p 8200:8200 \
  -e 'VAULT_DEV_ROOT_TOKEN_ID=dev-token' \
  -e 'VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200' \
  hashicorp/vault:1.15

# 驗證連線
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='dev-token'
vault status

# 寫入 Secret
vault kv put secret/myapp/db username=admin password=secret123

# 讀取 Secret
vault kv get secret/myapp/db
```

**生產環境架構**:
```yaml
# Vault HA 架構 (Kubernetes + Consul)
Vault Cluster:
  - Node 1: Active
  - Node 2: Standby
  - Node 3: Standby
Storage Backend: Consul Cluster (3 nodes)
Unsealing: Auto-unseal via AWS KMS / GCP Cloud KMS
```

#### 方案 2: SOPS (推薦用於小型團隊)

**優點**:
- 版本控制友好（加密後的 YAML/JSON 可 commit）
- 與 Git workflow 完美整合
- 支援多種 KMS (AWS, GCP, Azure, age, PGP)
- 部分加密（只加密 values，keys 保持可讀）

**缺點**:
- 無動態密鑰功能
- 無 Web UI
- 密鑰輪換需手動操作

**使用範例**:
```bash
# 安裝 SOPS
brew install sops  # macOS
apt install sops   # Ubuntu

# 建立加密配置 (.sops.yaml)
cat <<EOF > .sops.yaml
creation_rules:
  - path_regex: secrets/.*\.yaml$
    kms: arn:aws:kms:us-east-1:123456789:key/abc123
  - path_regex: secrets/.*\.yaml$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF

# 加密檔案
sops -e secrets/production.yaml > secrets/production.enc.yaml

# 解密檔案
sops -d secrets/production.enc.yaml

# 直接編輯加密檔案 (解密→編輯→加密)
sops secrets/production.enc.yaml
```

**與 CI/CD 整合 (GitHub Actions)**:
```yaml
jobs:
  deploy:
    steps:
      - name: Decrypt secrets
        run: |
          sops -d secrets/production.enc.yaml > secrets/production.yaml
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

#### 方案 3: Kubernetes Secrets + External Secrets Operator

**適用場景**: 已使用 Kubernetes 的團隊

```yaml
# ExternalSecret 從 AWS Secrets Manager 同步
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-secret
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: prod/database
        property: username
    - secretKey: password
      remoteRef:
        key: prod/database
        property: password
```

#### 安全最佳實踐

| 實踐 | 說明 | 工具支援 |
|------|------|---------|
| **最小權限原則** | 每個服務只能存取需要的 secrets | Vault Policy, IAM |
| **密鑰輪換** | 定期更換密鑰（建議 90 天） | Vault, Secrets Manager |
| **審計日誌** | 記錄誰在何時存取了什麼 | Vault Audit, CloudTrail |
| **加密傳輸** | TLS 加密所有 secret 傳輸 | 全部方案 |
| **避免日誌洩漏** | 確保 secrets 不會出現在日誌中 | 應用程式層面 |
| **緊急撤銷** | 可快速撤銷洩漏的 secret | Vault Lease, IAM |

---

## 🚀 完整執行流程

### 階段 1：啟動和情境確認 (20 分鐘)

#### 步驟 1.1：載入 AISDLC 框架
```
執行指令：
「請載入 AISDLC_SDD_INIT.md (v0.01)，我要建置 DevOps 和 CI/CD Pipeline」

或具體說明：
「請載入 AISDLC_INIT.md，為 Spring Boot + Next.js 專案建置 CI/CD」
「請載入 AISDLC_INIT.md，將現有專案容器化並部署到 Kubernetes」
「請載入 AISDLC_INIT.md，為包含 Android/macOS 行動端的專案建置完整 CI/CD」
```

#### 步驟 1.2：回答情境識別問題
系統會詢問：
- 專案類型 (Web/API/Mobile Backend/Microservices)
- 技術棧 (Node.js/Python/Java/Go/.NET)
- 目標平台 (AWS/GCP/Azure/On-premises)
- 部署模式 (VM/Container/Serverless/Kubernetes)
- 團隊規模和經驗

#### 步驟 1.3：確認載入結果
期待回應：
```
✅ 識別情境：DevOps Setup (DevOps 建置)
✅ 識別專案類型：[您的專案類型]
✅ 載入 Agents：DevOps-Engineer, SD, QA-Automation, Dev-Developer, Security-Engineer
✅ 推薦 Workflow：devops-setup-flow, testing-strategy-flow
準備開始環境規劃...
```

---

### 階段 2：環境規劃與架構設計 (40-60 分鐘)

#### 步驟 2.1：環境架構設計 (DevOps-Engineer + SD)

**環境分層策略**：
```
Production (生產環境)
├── 特性：高可用、自動擴展、完整監控
├── 資料：真實資料
├── 存取：限制存取、審計日誌
└── 部署：需審批、灰度發布

Staging (預生產環境)
├── 特性：與 Production 一致配置
├── 資料：匿名化的 Production 資料副本
├── 存取：開發團隊可存取
└── 部署：自動部署 main/master 分支

Development (開發環境)
├── 特性：資源較小、快速重建
├── 資料：測試資料
├── 存取：所有開發者
└── 部署：自動部署 develop 分支

Local (本地環境)
├── 特性：Docker Compose 模擬
├── 資料：Seed 資料
├── 存取：開發者本機
└── 部署：手動或 Hot Reload
```

**基礎設施選型**：

| 組件 | 小型專案 | 中型專案 | 大型專案 |
|------|---------|---------|---------|
| **計算** | 單一 VM | 多個 VM + Load Balancer | Kubernetes Cluster |
| **資料庫** | 單一 RDS | Master-Slave 複製 | 分片 + 讀寫分離 |
| **快取** | 內嵌快取 | Redis 單點 | Redis Cluster |
| **儲存** | 本地磁碟 | S3/GCS | S3 + CDN |
| **佇列** | 內嵌佇列 | Redis/RabbitMQ | Kafka/SQS |

**網路架構**：
```
Internet
  │
  ↓
[Load Balancer] (Public Subnet)
  │
  ├─> [Web Server 1] (Private Subnet)
  ├─> [Web Server 2] (Private Subnet)
  └─> [Web Server 3] (Private Subnet)
       │
       ↓
  [Application Servers] (Private Subnet)
       │
       ├─> [Database] (Private Subnet, Multi-AZ)
       ├─> [Redis Cache] (Private Subnet)
       └─> [Message Queue] (Private Subnet)
```

**基礎設施即代碼 (IaC)**：

**🔄 GitOps 流程指引**：

> GitOps = Git 作為 Single Source of Truth，所有變更透過 Git PR 觸發

```
┌──────────────────────────────────────────────────────────────┐
│                    GitOps 工作流程                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Developer ──Push──> Git Repo ──Sync──> K8s Cluster         │
│      │                  │                    │               │
│      │            [ArgoCD/FluxCD]            │               │
│      │                  │                    │               │
│      └── PR Review ─────┘                    │               │
│                                              │               │
│  ┌─────────────────────────────────────────┐ │               │
│  │ Git Repo (Config)                       │ │               │
│  │  ├── base/                              │ │               │
│  │  │   ├── deployment.yaml                │ │               │
│  │  │   └── service.yaml                   │ │               │
│  │  └── overlays/                          │ │               │
│  │      ├── dev/                           │ │               │
│  │      ├── staging/                       │ │               │
│  │      └── prod/                          │ │               │
│  └─────────────────────────────────────────┘ │               │
└──────────────────────────────────────────────────────────────┘
```

**GitOps 工具選擇**：

| 工具 | 特點 | 適用場景 |
|------|------|---------|
| **ArgoCD** | UI 完整、多叢集支援 | 中大型團隊、多環境管理 |
| **FluxCD** | 輕量、CLI 導向 | 小團隊、單一叢集 |
| **Kustomize** | K8s 原生、無需安裝 | 簡單覆蓋配置 |

**快速啟動 ArgoCD**：
```bash
# 安裝 ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 取得初始密碼
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# 建立 Application
argocd app create my-app \
  --repo https://github.com/your-org/your-repo.git \
  --path overlays/prod \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default
```

```hcl
# Terraform 範例
resource "aws_instance" "web" {
  count         = 3
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"

  tags = {
    Name = "web-server-${count.index + 1}"
    Environment = "production"
  }
}

resource "aws_lb" "main" {
  name               = "main-lb"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
}
```

#### 步驟 2.2：環境規劃確認點 (15 分鐘)

> 🔴 **人機協作點：環境架構設計確認**
>
> **AI 提供**：
> - 環境架構圖
> - 基礎設施選型建議
> - 成本預估
> - IaC 模板
>
> **需人工確認**：
> - ✅ 環境分層策略符合團隊需求
> - ✅ 基礎設施選型合理
> - ✅ 成本預算可接受
> - ✅ IaC 配置符合最佳實踐
>
> **產出文件**：
> - 環境規劃文件 (Environment Planning)
> - 基礎設施架構圖 (Infrastructure Architecture)
> - IaC 配置 (Infrastructure as Code)

---

### 階段 3：CI Pipeline 設計 (1-1.5 小時)

#### 步驟 3.1：CI Pipeline 流程設計

**標準 CI Pipeline**：
```yaml
# GitHub Actions 範例
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout 代碼
      - uses: actions/checkout@v4

      # 2. 設定環境
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      # 3. 安裝依賴
      - name: Install dependencies
        run: npm ci

      # 4. 程式碼風格檢查
      - name: Lint
        run: npm run lint

      # 5. 類型檢查 (TypeScript)
      - name: Type Check
        run: npm run type-check

      # 6. 單元測試
      - name: Unit Tests
        run: npm run test:unit -- --coverage

      # 7. 整合測試
      - name: Integration Tests
        run: npm run test:integration

      # 8. 建置
      - name: Build
        run: npm run build

      # 9. 安全性掃描
      - name: Security Scan
        run: npm audit

      # 10. 上傳 Artifacts
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

      # 11. 上傳測試覆蓋率報告
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
```

**Quality Gates (品質門檻)**：
```yaml
# 範例：SonarQube Quality Gate
- name: SonarQube Scan
  run: |
    sonar-scanner \
      -Dsonar.projectKey=my-project \
      -Dsonar.sources=src \
      -Dsonar.host.url=${{ secrets.SONAR_HOST }} \
      -Dsonar.login=${{ secrets.SONAR_TOKEN }}

    # 等待 Quality Gate 結果
    curl -u ${{ secrets.SONAR_TOKEN }}: \
      "${{ secrets.SONAR_HOST }}/api/qualitygates/project_status?projectKey=my-project" \
      | jq -e '.projectStatus.status == "OK"'
```

**多平台建置**：
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node: ['16', '18', '20']

runs-on: ${{ matrix.os }}
```

---

#### 步驟 3.1a：🆕 Spring Boot + Next.js 多技術棧 CI 範本

> **適用情境**：後端 Spring Boot（Java/Kotlin）+ 前端 React/Next.js（TypeScript）+ DB PostgreSQL

```yaml
# .github/workflows/ci.yml
name: CI - Spring Boot + Next.js

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # ─── Job 1: Spring Boot 後端 CI ────────────────────────────
  backend:
    name: Backend CI (Spring Boot)
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'gradle'

      - name: Grant Gradle execute permission
        run: chmod +x gradlew

      - name: Lint (Checkstyle)
        run: ./gradlew checkstyleMain checkstyleTest

      - name: Run DB Migration (Flyway)
        run: ./gradlew flywayMigrate
        env:
          SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb
          SPRING_DATASOURCE_USERNAME: testuser
          SPRING_DATASOURCE_PASSWORD: testpass

      - name: Unit Tests + Coverage
        run: ./gradlew test jacocoTestReport
        env:
          SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb

      - name: Coverage Gate (≥80%)
        run: ./gradlew jacocoTestCoverageVerification

      - name: Build JAR
        run: ./gradlew bootJar -x test

      - name: Upload JAR artifact
        uses: actions/upload-artifact@v4
        with:
          name: backend-jar
          path: build/libs/*.jar

  # ─── Job 2: Next.js 前端 CI ────────────────────────────────
  frontend:
    name: Frontend CI (Next.js)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: TypeScript type check
        run: npm run type-check
        working-directory: frontend

      - name: ESLint
        run: npm run lint
        working-directory: frontend

      - name: Unit Tests (Jest)
        run: npm run test -- --coverage
        working-directory: frontend

      - name: Build (Next.js)
        run: npm run build
        working-directory: frontend
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8080

  # ─── Job 3: 安全掃描 ────────────────────────────────────────
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: [backend, frontend]

    steps:
      - uses: actions/checkout@v4

      - name: Secret Detection (TruffleHog)
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./

      - name: Dependency Scan (Trivy)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
```

#### 步驟 3.1b：🆕 DB Migration 整合 CI（Spring Boot + Flyway）

> **Spring Boot + PostgreSQL DB Migration 最佳實踐**

```yaml
# Flyway 配置（推薦用於 Spring Boot）
# src/main/resources/application.yml
spring:
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true
    validate-on-migrate: true
    out-of-order: false
  datasource:
    url: ${SPRING_DATASOURCE_URL}

# Migration 檔案命名規則：
# db/migration/
# ├── V1__Create_users_table.sql
# ├── V2__Create_orders_table.sql
# └── V3__Add_index_on_email.sql
```

```yaml
# CI 中的 Migration 驗證步驟
- name: Validate DB Schema (Flyway)
  run: ./gradlew flywayInfo flywayValidate
  env:
    SPRING_DATASOURCE_URL: jdbc:postgresql://localhost:5432/testdb

# Rollback 驗證（確保 migration 可回滾）
- name: Test Migration Rollback
  run: |
    ./gradlew flywayMigrate
    ./gradlew flywayUndo  # 僅 Flyway Teams 支援；替代方案：手動 undo script
```

#### 步驟 3.2：Docker 容器化

**Dockerfile 最佳實踐**：
```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder

WORKDIR /app

# 利用 Layer Caching
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

# 非 root 使用者
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 只複製必要文件
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs package.json ./

USER nodejs

EXPOSE 3000

CMD ["node", "dist/main.js"]
```

**Docker Compose (本地開發)**：
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src  # Hot reload

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

#### 步驟 3.3：CI Pipeline 確認點 (20 分鐘)

> 🔴 **人機協作點：CI Pipeline 設計確認**
>
> **AI 提供**：
> - 完整 CI Pipeline 配置
> - Quality Gates 設定
> - Docker 容器化方案
> - 建置時間優化建議
>
> **需人工確認**：
> - ✅ CI 步驟完整且順序合理
> - ✅ Quality Gates 閾值適當
> - ✅ Docker 配置符合安全最佳實踐
> - ✅ 建置時間可接受
>
> **產出文件**：
> - CI Pipeline 配置 (CI Configuration)
> - Dockerfile 和 Docker Compose
> - 容器化最佳實踐指南

---

### 🆕 階段 3.A：行動端 CI/CD 前期規劃（已知行動端需求時）(SD-Mobile + DevOps)

> **適用情境**：主系統包含或計畫包含 Android + macOS 應用時，必須在 Stage 3 預留行動端 CI/CD 空間。

#### Android CI Pipeline（Gradle）

```yaml
# .github/workflows/android-ci.yml
name: Android CI

on:
  push:
    branches: [main, develop]
    paths: ['android/**']

jobs:
  android:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Cache Gradle
        uses: actions/cache@v4
        with:
          path: ~/.gradle/caches
          key: gradle-${{ hashFiles('**/*.gradle*') }}

      - name: Run Tests
        run: ./gradlew test
        working-directory: android

      - name: Build Debug APK
        run: ./gradlew assembleDebug
        working-directory: android

      - name: Distribute to Firebase App Distribution
        uses: wzieba/Firebase-Distribution-Github-Action@v1
        with:
          appId: ${{ secrets.FIREBASE_APP_ID }}
          serviceCredentialsFileContent: ${{ secrets.FIREBASE_CREDENTIALS }}
          file: android/app/build/outputs/apk/debug/app-debug.apk
          testers: ${{ secrets.QA_TESTERS }}
```

#### macOS App CI Pipeline（Xcode/fastlane）

```yaml
# .github/workflows/macos-ci.yml
name: macOS CI

on:
  push:
    branches: [main, develop]
    paths: ['macos/**']

jobs:
  macos:
    runs-on: macos-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Xcode
        uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: 'latest-stable'

      - name: Install fastlane
        run: gem install fastlane

      - name: Run Tests
        run: fastlane test
        working-directory: macos

      - name: Build & Export
        run: fastlane build
        working-directory: macos
        env:
          APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
          APPLE_PROFILE: ${{ secrets.APPLE_PROVISIONING_PROFILE }}
```

#### 行動端 CI/CD 設計決策清單
- [ ] **CI 觸發範圍**：僅在 `android/` 或 `macos/` 目錄有變更時觸發（避免不必要的建置）
- [ ] **Signing 管理**：Android Keystore + macOS Certificate 存入 GitHub Secrets
- [ ] **分發策略**：Dev → Firebase App Distribution；Release → Play Store / Mac App Store
- [ ] **API 端點設計**：後端 REST API 從 Day 1 支援行動端（適當的 Pagination、離線快取欄位）

> **產出文件**：`docs/08_deployment/Mobile_CICD_Pipeline.md`

---

### 階段 4：CD Pipeline 設計 (1-1.5 小時)

#### 步驟 4.1：部署策略選擇

**策略 A：滾動部署 (Rolling Deployment)**
```
[V1] [V1] [V1] [V1]
  ↓
[V2] [V1] [V1] [V1]
  ↓
[V2] [V2] [V1] [V1]
  ↓
[V2] [V2] [V2] [V1]
  ↓
[V2] [V2] [V2] [V2]
```
- **優點**：無額外資源成本
- **缺點**：回滾較慢、部分時間新舊版本共存

**策略 B：藍綠部署 (Blue-Green Deployment)**
```
Production (Blue)  →  [Load Balancer]
Staging (Green)    →  驗證通過後切換
```
- **優點**：快速回滾、零停機
- **缺點**：需要 2 倍資源

**策略 C：金絲雀發布 (Canary Deployment)**
```
V1: 90% 流量
V2: 10% 流量 → 監控 → 逐步增加到 100%
```
- **優點**：風險可控、漸進式驗證
- **缺點**：複雜度高、需要流量分配機制

**策略 D：Feature Flags**
```javascript
if (featureFlags.isEnabled('new-checkout')) {
  return <NewCheckout />;
} else {
  return <OldCheckout />;
}
```
- **優點**：即時開關、A/B Testing
- **缺點**：代碼複雜度增加

#### 步驟 4.2：CD Pipeline 實作

**GitHub Actions 部署範例**：
```yaml
name: CD Pipeline

on:
  push:
    branches: [ main ]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      # 建置 Docker Image
      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      # 推送到 Registry
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_URL }}
          docker tag myapp:${{ github.sha }} ${{ secrets.ECR_URL }}/myapp:${{ github.sha }}
          docker push ${{ secrets.ECR_URL }}/myapp:${{ github.sha }}

      # 部署到 Kubernetes
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/myapp \
            myapp=${{ secrets.ECR_URL }}/myapp:${{ github.sha }} \
            --namespace=staging

      # 等待部署完成
      - name: Wait for rollout
        run: kubectl rollout status deployment/myapp -n staging

      # Smoke Test
      - name: Run smoke tests
        run: npm run test:smoke -- --baseUrl=https://staging.example.com

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      # 類似 staging 但需要手動審批
      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp \
            myapp=${{ secrets.ECR_URL }}/myapp:${{ github.sha }} \
            --namespace=production
```

**Kubernetes 部署配置**：
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # 確保零停機

  selector:
    matchLabels:
      app: myapp

  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 3000

        # 健康檢查
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5

        # 資源限制
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        # 環境變數 (從 ConfigMap/Secret 讀取)
        envFrom:
        - configMapRef:
            name: myapp-config
        - secretRef:
            name: myapp-secrets
```

**自動擴展**：
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

#### 步驟 4.3：CD Pipeline 確認點 (20 分鐘)

> 🔴 **人機協作點：CD Pipeline 設計確認**
>
> **AI 提供**：
> - 部署策略建議
> - 完整 CD Pipeline 配置
> - Kubernetes 部署文件
> - 回滾方案
>
> **需人工確認**：
> - ✅ 部署策略符合業務需求（零停機/快速回滾）
> - ✅ CD Pipeline 流程完整
> - ✅ Kubernetes 配置符合最佳實踐
> - ✅ 回滾機制可靠
>
> **產出文件**：
> - CD Pipeline 配置 (CD Configuration)
> - Kubernetes Manifests
> - 部署 Runbook (Deployment Runbook)

---

### 階段 5：監控與告警 (40-60 分鐘)

#### 步驟 5.1：監控體系建立

**四大黃金指標 (Four Golden Signals)**：
1. **Latency** (延遲)：請求回應時間
2. **Traffic** (流量)：每秒請求數
3. **Errors** (錯誤)：錯誤率
4. **Saturation** (飽和度)：資源使用率

**監控層次**：
```
Infrastructure (基礎設施層)
├── CPU/Memory/Disk/Network
├── 工具：Prometheus + Node Exporter
└── 告警：CPU > 80%, Memory > 85%

Application (應用層)
├── 回應時間、QPS、錯誤率
├── 工具：Prometheus + Application Metrics
└── 告警：P95 > 1s, Error Rate > 1%

Business (業務層)
├── 註冊數、訂單量、轉換率
├── 工具：自定義業務指標
└── 告警：業務異常 (如訂單量驟降)

Logs (日誌層)
├── Application Logs、Access Logs、Error Logs
├── 工具：ELK Stack (Elasticsearch, Logstash, Kibana)
└── 告警：特定錯誤模式

Tracing (追蹤層)
├── 分散式追蹤、請求鏈路
├── 工具：Jaeger, Zipkin, OpenTelemetry
└── 用途：效能診斷、瓶頸分析
```

**Prometheus 監控配置**：
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'myapp'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: myapp
```

**應用程式指標暴露**：
```javascript
// Node.js + Prometheus Client
const client = require('prom-client');

// 預設指標 (CPU, Memory)
client.collectDefaultMetrics();

// 自定義指標
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code']
});

const httpRequestTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

// Middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestDuration.observe(
      { method: req.method, route: req.route.path, status_code: res.statusCode },
      duration
    );
    httpRequestTotal.inc({ method: req.method, route: req.route.path, status_code: res.statusCode });
  });
  next();
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(client.register.metrics());
});
```

**Grafana 儀表板**：
```json
{
  "dashboard": {
    "title": "Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }]
      },
      {
        "title": "Response Time (P95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])"
        }]
      }
    ]
  }
}
```

**告警規則**：
```yaml
# alert-rules.yml
groups:
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} (threshold: 0.01)"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"

      - alert: PodDown
        expr: kube_pod_status_phase{phase="Running"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Pod {{ $labels.pod }} is down"
```

#### 步驟 5.2：監控確認點 (15 分鐘)

> 🔴 **人機協作點：監控與告警方案確認**
>
> **AI 提供**：
> - 完整監控架構
> - Prometheus + Grafana 配置
> - 告警規則
> - On-call 流程
>
> **需人工確認**：
> - ✅ 監控覆蓋四大黃金指標
> - ✅ 告警閾值合理（避免告警疲勞）
> - ✅ Grafana 儀表板清晰易讀
> - ✅ On-call 流程明確可執行
>
> **產出文件**：
> - 監控方案 (Monitoring Plan)
> - Grafana 儀表板配置
> - 告警規則 (Alert Rules)
> - On-call Playbook

---

### 階段 6：災難恢復與備份 (30-40 分鐘)

#### 步驟 6.1：備份策略

**資料庫備份**：
```bash
# 自動化備份腳本
#!/bin/bash

# 每日完整備份
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME \
  | gzip > /backups/db_$(date +%Y%m%d).sql.gz

# 上傳到 S3
aws s3 cp /backups/db_$(date +%Y%m%d).sql.gz \
  s3://my-backups/database/

# 保留 30 天備份
find /backups -name "db_*.sql.gz" -mtime +30 -delete
```

**RTO/RPO 目標**：
- **RTO (Recovery Time Objective)**：系統恢復時間 < 1 小時
- **RPO (Recovery Point Objective)**：可接受的資料遺失 < 15 分鐘

**災難恢復計畫**：
```
Scenario: 資料庫完全損毀

1. 檢測（5 分鐘）
   - 監控告警觸發
   - On-call 工程師確認

2. 決策（10 分鐘）
   - 評估損毀程度
   - 決定恢復策略

3. 恢復（30 分鐘）
   - 從最新備份恢復
   - 應用事務日誌（如有）
   - 驗證資料完整性

4. 驗證（10 分鐘）
   - Smoke Test
   - 資料一致性檢查

5. 切換（5 分鐘）
   - 流量切換到恢復的資料庫
   - 持續監控

Total: < 60 分鐘 (符合 RTO)
```

> **⚠️ DR 演練流程 (Disaster Recovery Drill)**
>
> 災難恢復計畫需要定期演練,確保真實災難時能有效執行:
>
> **演練頻率建議**:
> - 🔴 Critical 系統: 每季 1 次完整演練 + 每月 1 次桌面演練
> - 🟡 Important 系統: 每半年 1 次完整演練
> - 🟢 Standard 系統: 每年 1 次完整演練
>
> **演練類型**:
> 1. **桌面演練 (Tabletop Exercise)** - 2 小時
>    - 團隊討論災難場景
>    - 檢視 DR 文件
>    - 不實際執行
>    - 低成本,高頻率
>
> 2. **模擬演練 (Simulation Drill)** - 半天
>    - 在測試環境執行 DR
>    - 驗證腳本可行性
>    - 測量 RTO/RPO
>
> 3. **完整演練 (Full Drill)** - 1 天
>    - 實際切換到 DR 環境
>    - 生產流量切換
>    - 完整驗證
>
> **演練清單範例**:
> ```yaml
> dr_drill_2024_Q2:
>   date: "2024-06-15"
>   type: "Full Drill"
>   scenario: "區域性資料中心故障"
>   
>   checklist:
>     preparation:
>       - [ ] 通知所有利害關係人
>       - [ ] 確認備份最新且可用
>       - [ ] 準備 DR 環境
>       - [ ] 設定監控和日誌
>     
>     execution:
>       - [ ] T0: 模擬主機房故障
>       - [ ] T+5min: 觸發 DR 程序
>       - [ ] T+15min: 啟動備援系統
>       - [ ] T+30min: 恢復資料庫
>       - [ ] T+45min: 切換流量
>       - [ ] T+60min: 驗證系統功能
>     
>     validation:
>       - [ ] 所有 API 正常回應
>       - [ ] 資料一致性驗證
>       - [ ] 效能指標達標
>       - [ ] 監控告警正常
>     
>     rollback:
>       - [ ] 切換回主環境
>       - [ ] 驗證主環境正常
>       - [ ] 記錄演練結果
>   
>   success_criteria:
>     - "RTO < 60 minutes"
>     - "RPO < 15 minutes"
>     - "Zero data loss"
>     - "All critical functions operational"
> ```
>
> **演練後檢討 (Post-Drill Review)**:
> 1. 記錄實際 RTO/RPO
> 2. 識別問題和改善點
> 3. 更新 DR 文件
> 4. 安排後續行動

```

#### 步驟 6.2：災難恢復確認點 (10 分鐘)

> 🔴 **人機協作點：災難恢復方案確認**
>
> **AI 提供**：
> - 備份策略
> - 災難恢復計畫
> - RTO/RPO 定義
> - DR 演練流程
>
> **需人工確認**：
> - ✅ RTO/RPO 目標符合業務需求
> - ✅ 備份頻率和保留期適當
> - ✅ DR 計畫可執行且已演練
> - ✅ 恢復步驟清晰明確
>
> **產出文件**：
> - 備份策略 (Backup Strategy)
> - 災難恢復計畫 (Disaster Recovery Plan)
> - RTO/RPO 定義


---

### 階段 7：雲端成本管理 (FinOps)

> **⚠️ 雲端成本監控與優化 (Cloud Cost Monitoring & Optimization)**
>
> DevOps 自動化可能導致成本失控,需建立 FinOps 機制:
>
> **成本監控工具**:
> - AWS: Cost Explorer + Budgets + Compute Optimizer
> - GCP: Cloud Billing Reports + Recommender
> - Azure: Cost Management + Advisor
> - 第三方: CloudHealth, Kubecost, Infracost
>
> **快速優化檢查清單**:
> ```yaml
> cost_optimization_checklist:
>   compute:
>     - [ ] 刪除閒置資源 (停用的 VM/DB)
>     - [ ] 使用 Spot/Preemptible Instances (節省 60-90%)
>     - [ ] Right-sizing (調整過大的 Instance)
>     - [ ] 使用 Reserved Instances (長期負載節省 30-60%)
>   
>   storage:
>     - [ ] 刪除未連接的磁碟
>     - [ ] 舊資料移至 Cold Storage
>     - [ ] 啟用 Lifecycle Policies
>   
>   network:
>     - [ ] 使用 CDN 減少流量
>     - [ ] 跨區流量優化
>     - [ ] NAT Gateway 優化
> ```
>
> **成本告警範例**:
> ```yaml
> # AWS Budget Alert
> budget:
>   name: "Monthly Production Budget"
>   limit: 5000  # USD
>   alerts:
>     - threshold: 80%
>       recipients: ["team@example.com"]
>     - threshold: 100%
>       recipients: ["cto@example.com"]
> ```
>
> **FinOps 最佳實踐**:
> 1. **每週成本檢視** (團隊儀表板)
> 2. **每月成本檢討會議**
> 3. **成本標籤策略** (Team/Project/Environment)
> 4. **Showback/Chargeback** (各團隊成本可見)

#### 多雲部署考量 (Multi-Cloud Deployment Considerations)

**多雲策略類型**:
- **Multi-Cloud**: 同時使用多個雲 (AWS + GCP + Azure)
- **Hybrid Cloud**: 雲端 + 地端
- **Active-Active**: 多雲同時提供服務
- **Active-Passive**: 主雲 + 備援雲

**優缺點對比**:

| 策略 | 優點 | 缺點 |
|------|------|------|
| 單一雲 | 簡單、整合好 | 廠商鎖定風險 |
| 多雲 | 避免鎖定、高可用 | 複雜度高、成本增加 |

**技術方案**:
- **容器化**: Kubernetes (跨雲可攜)
- **IaC**: Terraform (多雲支援)
- **服務網格**: Istio (跨雲通訊)
- **資料同步**: Multi-region replication

**建議**:
- ✅ 小型團隊: 單一雲 + 多區域
- ✅ 中型團隊: 單一主雲 + DR 備援雲
- ✅ 大型企業: 多雲策略 + 專職 FinOps


---

## 🎯 成功標準

### CI/CD 自動化
- [ ] 代碼提交自動觸發 CI
- [ ] 測試全部通過才能部署
- [ ] 部署流程自動化
- [ ] 回滾機制可用

### 可靠性
- [ ] 零停機部署
- [ ] 自動擴展配置
- [ ] 健康檢查有效
- [ ] 回滾時間 < 5 分鐘

### 監控完整性
- [ ] 四大黃金指標已監控
- [ ] 告警及時有效
- [ ] 儀表板清晰易讀
- [ ] On-call 流程明確

### 安全性
- [ ] Secrets 安全存儲
- [ ] 最小權限原則
- [ ] 審計日誌完整
- [ ] 定期安全掃描

---

## 📊 時間分配參考

| 階段 | 預估時間 |
|------|---------|
| 啟動和情境確認 | 20 分鐘 |
| 環境規劃與架構設計 | 40-60 分鐘 |
| CI Pipeline 設計 | 1-1.5 小時 |
| CD Pipeline 設計 | 1-1.5 小時 |
| 監控與告警 | 40-60 分鐘 |
| 災難恢復與備份 | 30-40 分鐘 |
| **準備階段總計** | **3-4 小時** |
| **實際建置時間** | 1-2 週 |

---

## 💡 最佳實踐

### 1. 基礎設施即代碼
- 使用 Terraform/CloudFormation
- 版本控制所有配置
- Code Review IaC 變更

### 2. 不可變基礎設施
- 容器化應用
- 不要修改運行中的容器
- 部署新版本而非修改舊版本

### 3. 持續監控
- 監控四大黃金指標
- 及時告警
- 定期檢視儀表板

### 4. 漸進式部署
- 小步快跑
- 灰度發布
- 隨時可回滾

### 5. 自動化一切
- 測試自動化
- 部署自動化
- 備份自動化

---

## 📚 實際案例走查

> 💡 **學習價值**: 透過真實 DevOps 專案案例,了解從零建立 CI/CD Pipeline、容器化遷移的完整流程,掌握最佳實踐並避免常見陷阱。

### 案例 1: CI/CD Pipeline 從零建立 (GitHub Actions)

**專案背景**:
- **專案類型**: Node.js Web API 服務
- **團隊規模**: 4 人 (2 Backend Dev + 1 DevOps Engineer + 1 QA)
- **技術棧**: Node.js 18 + Express + PostgreSQL + Redis + Docker
- **專案週期**: 2 週 (AISDLC 規劃 4 小時 + CI/CD 建置 1 週 + 優化測試 1 週)
- **專案目標**: 從手動部署遷移到自動化 CI/CD,實現「推送代碼 → 自動測試 → 自動部署」全流程自動化

**執行過程** (依 SOP 階段):

#### 階段 1: 啟動和情境確認 (實際耗時: 15 分鐘)
- ✅ 載入 AISDLC_INIT.md 並識別為 DevOps Setup 情境
- ✅ 確認專案類型: Web API、技術棧 Node.js、目標平台 AWS EC2
- ✅ 載入 DevOps-Engineer、SD-Architect、QA-Automation Agent
- 📊 階段產出: 情境確認文檔

#### 階段 2: 環境規劃與架構設計 (實際耗時: 1.5 小時)
- ✅ 完成項目:
  - 設計三層環境架構 (Development、Staging、Production)
  - 選擇基礎設施: AWS EC2 + RDS + ElastiCache (Redis)
  - 設計網路架構 (Public Subnet: ALB, Private Subnet: EC2/RDS)
  - 撰寫 Terraform IaC 配置 (VPC、Subnet、Security Group、EC2、RDS)

- ⚠️ 遇到問題:
  - 團隊對 Terraform 不熟悉,擔心學習曲線
  - 不確定如何管理多環境配置 (Dev/Staging/Prod)

- 💡 解決方案:
  - 使用 Terraform Workspace 管理多環境
  - 提供 Terraform 快速上手培訓 (2 小時)
  - 先手動建立 Development 環境驗證,後續 IaC 化

- 📊 階段產出:
  - 環境架構圖 (Lucidchart)
  - Terraform 配置檔案 (`main.tf`, `variables.tf`, `outputs.tf`)
  - 成本預估報告 (每月約 $150)

#### 階段 3: CI Pipeline 設計 (實際耗時: 2 天)
- ✅ 完成項目:
  - 建立 GitHub Actions Workflow (`.github/workflows/ci.yml`)
  - 設定 CI 步驟: Checkout → Setup Node.js → Install Deps → Lint → Type Check → Unit Test → Build
  - 整合 SonarQube 進行代碼品質掃描
  - 設定測試覆蓋率要求 (≥ 80%)
  - Docker 容器化 (Multi-stage build 優化 Image 大小)

- ⚠️ 遇到問題:
  - CI 執行時間過長 (首次執行 12 分鐘)
  - npm install 每次重新下載依賴,浪費時間
  - Docker Build 每次重新建置所有 Layer

- 💡 解決方案:
  - 使用 GitHub Actions Cache 快取 node_modules (CI 時間縮短至 4 分鐘)
  - 使用 Docker Layer Caching 加速建置 (Build 時間從 8 分鐘降至 2 分鐘)
  - 並行執行 Lint、Type Check、Test (節省 30% 時間)

- 📊 階段產出:
  - CI Pipeline 配置 (`.github/workflows/ci.yml`)
  - Dockerfile (Multi-stage build)
  - CI 執行時間優化報告 (從 12 分鐘降至 3.5 分鐘)

#### 階段 4: CD Pipeline 設計 (實際耗時: 3 天)
- ✅ 完成項目:
  - 建立 CD Workflow (`.github/workflows/deploy.yml`)
  - 實作部署流程: Build Docker Image → Push to ECR → SSH to EC2 → Pull Image → Rolling Update
  - 設定環境隔離 (GitHub Environments: staging, production)
  - 實作 Production 部署需手動審批機制
  - 實作健康檢查和自動回滾 (若健康檢查失敗,自動回滾到上一版本)

- ⚠️ 遇到問題:
  - SSH 部署方式安全性疑慮 (需管理 SSH Key)
  - 部署過程中短暫服務中斷 (約 5-10 秒)
  - 回滾機制不明確,擔心出錯時無法快速恢復

- 💡 解決方案:
  - 使用 AWS Systems Manager Session Manager 取代 SSH (無需管理 Key)
  - 實作「藍綠部署」策略:先啟動新容器,健康檢查通過後切換流量,再關閉舊容器 (零停機部署)
  - 實作「一鍵回滾」腳本,可快速切換回上一版本 Docker Image

- 📊 階段產出:
  - CD Pipeline 配置 (`.github/workflows/deploy.yml`)
  - 部署腳本 (`scripts/deploy.sh`, `scripts/rollback.sh`)
  - 部署 Runbook (包含回滾步驟)

#### 階段 5: 監控與告警 (實際耗時: 2 天)
- ✅ 完成項目:
  - 部署 Prometheus + Grafana (Docker Compose)
  - 應用程式埋點 (使用 `prom-client` 暴露 Metrics)
  - 建立 Grafana 儀表板 (四大黃金指標: Latency、Traffic、Errors、Saturation)
  - 設定 Prometheus 告警規則 (錯誤率 > 1%、P95 延遲 > 1s、CPU > 80%)
  - 整合 Slack Webhook 接收告警通知

- ⚠️ 遇到問題:
  - Prometheus 資料保留時間有限 (預設 15 天)
  - 告警過於頻繁,造成「告警疲勞」
  - 無法追蹤跨服務的請求鏈路

- 💡 解決方案:
  - 使用 VictoriaMetrics 取代 Prometheus (更高效能,更長保留時間)
  - 調整告警閾值和評估時間 (避免短暫波動觸發告警)
  - 整合 Jaeger 實作分散式追蹤

- 📊 階段產出:
  - Prometheus + Grafana 配置 (`docker-compose.monitoring.yml`)
  - Grafana Dashboard JSON (4 個儀表板)
  - 告警規則配置 (`alert-rules.yml`)
  - On-call Playbook

#### 階段 6: 災難恢復與備份 (實際耗時: 1 天)
- ✅ 完成項目:
  - 設定 RDS 自動備份 (每日 3:00 AM,保留 7 天)
  - 撰寫資料庫備份腳本並上傳至 S3 (每日備份 + 每週完整備份)
  - 定義 RTO/RPO: RTO < 1 小時, RPO < 15 分鐘
  - 撰寫災難恢復手冊 (包含資料庫恢復、應用恢復步驟)
  - 執行 DR 演練 (模擬 EC2 故障,驗證恢復流程)

- ⚠️ 遇到問題:
  - RDS 恢復時間較長 (實測約 25 分鐘)
  - 備份腳本缺乏錯誤處理,偶爾備份失敗未察覺

- 💡 解決方案:
  - 設定 RDS Multi-AZ 部署 (自動容錯轉移,RTO < 5 分鐘)
  - 備份腳本加入錯誤處理和 Slack 通知
  - 設定 CloudWatch Alarm 監控備份任務狀態

- 📊 階段產出:
  - 備份策略文檔
  - 災難恢復計畫 (DR Plan)
  - DR 演練報告 (實際 RTO: 45 分鐘, RPO: 10 分鐘)

#### 階段 7: 成本優化與 FinOps (實際耗時: 1 天)
- ✅ 完成項目:
  - 設定 AWS Cost Explorer 和 Budgets
  - 識別閒置資源 (發現 2 個未使用的 EBS Volume,每月浪費 $20)
  - 設定成本告警 (每月預算 $200,達 80% 時告警)
  - 使用 Spot Instances 用於 Staging 環境 (節省 60%)

- 📊 階段產出:
  - 成本優化報告 (每月成本從 $180 降至 $120,節省 33%)
  - FinOps 儀表板

**關鍵經驗**:
- 💡 **成功經驗**:
  - GitHub Actions 免費額度充足 (2000 分鐘/月),無需額外成本
  - Docker Layer Caching 大幅加速 CI/CD (節省 60% 時間)
  - 藍綠部署實現零停機部署,用戶體驗無影響
  - 監控告警及早發現問題 (曾在凌晨 2 點自動告警資料庫連線池耗盡)

- ⚠️ **避坑指南**:
  - **錯誤 1**: 未設定 CI Cache → CI 執行時間過長 (12 分鐘 → 4 分鐘)
  - **錯誤 2**: 部署未實作健康檢查 → 部署失敗版本導致服務中斷
  - **錯誤 3**: 告警閾值設定過敏感 → 告警疲勞,真實問題被忽略
  - **錯誤 4**: 未執行 DR 演練 → 真實災難時手忙腳亂

- 🔄 **流程調整**:
  - 原計畫使用滾動部署,後改為藍綠部署 (實現零停機)
  - 原計畫手動管理 SSH Key,後改用 AWS Session Manager (更安全)

**量化成果**:
- ✅ CI/CD 建置時間: 2 週 (符合預期)
- ✅ 部署頻率: 從每週 1 次提升至每日 3-5 次
- ✅ 部署時間: 從 30 分鐘縮短至 5 分鐘
- ✅ 部署失敗率: < 2% (目標 < 5%)
- ✅ 平均修復時間 (MTTR): 從 2 小時降至 15 分鐘
- ✅ CI 執行時間: 3.5 分鐘 (優化前 12 分鐘)
- ✅ 零停機部署成功率: 100%
- ✅ 團隊開發效率提升: 約 40% (自動化減少手動操作)

---

### 案例 2: Kubernetes 容器化遷移 (從 VM 到 K8s)

**專案背景**:
- **專案類型**: Microservices 電商平台 (5 個服務)
- **團隊規模**: 6 人 (3 Backend Dev + 2 DevOps Engineer + 1 SRE)
- **技術棧**: Java Spring Boot + Python Flask + Node.js + PostgreSQL + MongoDB + Redis
- **專案週期**: 6 週 (AISDLC 規劃 4 小時 + 容器化 2 週 + K8s 遷移 3 週 + 穩定優化 1 週)
- **專案目標**: 從傳統 VM 部署遷移到 Kubernetes,實現自動擴展、高可用性、資源利用率優化

**執行過程** (依 SOP 階段):

#### 階段 1: 啟動和情境確認 (實際耗時: 20 分鐘)
- ✅ 識別為 DevOps Setup 情境,專案類型 Microservices
- ✅ 確認目標: VM → Kubernetes 容器化遷移
- ✅ 評估現有架構: 5 個服務分別部署在 5 台 EC2 (資源利用率僅 30-40%)
- 📊 階段產出: 遷移需求分析

#### 階段 2: 環境規劃與架構設計 (實際耗時: 1 週)
- ✅ 完成項目:
  - 選擇 Kubernetes 平台: AWS EKS (Elastic Kubernetes Service)
  - 設計 K8s 架構: 3 個 Worker Nodes (t3.large) + 1 個 Bastion Host
  - 規劃 Namespace 隔離 (dev, staging, production)
  - 設計服務網格: Istio (流量管理、服務發現、安全通訊)
  - 撰寫 Terraform 配置建立 EKS Cluster

- ⚠️ 遇到問題:
  - EKS 成本高於預期 (Control Plane $0.10/hour + Worker Nodes)
  - 團隊對 Kubernetes 不熟悉,學習曲線陡峭
  - 不確定如何處理有狀態服務 (PostgreSQL, MongoDB)

- 💡 解決方案:
  - 使用 EKS Fargate (Serverless) 減少管理負擔,但保留 EC2 Worker Nodes 用於有狀態服務
  - 提供 Kubernetes 培訓課程 (1 週,包含實戰演練)
  - 資料庫暫不容器化,繼續使用 RDS/DocumentDB (降低風險)

- 📊 階段產出:
  - K8s 架構設計文檔
  - Terraform 配置 (EKS Cluster)
  - 成本預估 (每月約 $500,比 VM 方案節省 20%)

#### 階段 3: 應用容器化 (實際耗時: 2 週)
- ✅ 完成項目:
  - 為 5 個服務分別撰寫 Dockerfile (Multi-stage build)
  - 優化 Docker Image 大小 (使用 Alpine base image,平均減少 60%)
  - 建立 Helm Charts 管理 K8s 部署配置
  - 設定 ConfigMap 和 Secret 管理配置和敏感資訊
  - 本地測試容器化應用 (使用 Minikube)

- ⚠️ 遇到問題:
  - Java 服務 Docker Image 過大 (1.2GB)
  - 環境變數配置混亂,不同環境需手動修改
  - 本地測試時資源不足 (Minikube 需 8GB RAM)

- 💡 解決方案:
  - 使用 `eclipse-temurin:17-jre-alpine` 減少 Image 大小 (降至 350MB)
  - 使用 Helm Values 管理多環境配置 (`values-dev.yaml`, `values-prod.yaml`)
  - 使用 Docker Desktop Kubernetes 取代 Minikube (資源管理更友善)

- 📊 階段產出:
  - 5 個服務的 Dockerfile
  - Helm Charts (`charts/api-service`, `charts/auth-service`, ...)
  - Docker Image 優化報告 (平均大小從 800MB 降至 280MB)

#### 階段 4: CI/CD Pipeline 更新 (實際耗時: 1 週)
- ✅ 完成項目:
  - 更新 CI Pipeline: Build → Test → Build Docker Image → Push to ECR
  - 更新 CD Pipeline: Helm Install/Upgrade 部署到 K8s
  - 實作 GitOps 流程 (使用 ArgoCD 自動同步 Git → K8s)
  - 設定 Image Tag 策略 (使用 Git Commit SHA)

- ⚠️ 遇到問題:
  - Helm Upgrade 時偶爾失敗,回滾機制不明確
  - ArgoCD 與 GitHub Actions 整合複雜

- 💡 解決方案:
  - 使用 `helm upgrade --install --atomic` 確保失敗時自動回滾
  - 簡化流程: GitHub Actions 只負責 Build 和 Push Image,ArgoCD 監控 Git Repo 自動部署

- 📊 階段產出:
  - 更新後的 CI/CD Pipeline
  - ArgoCD 配置
  - GitOps 流程文檔

#### 階段 5: K8s 進階功能配置 (實際耗時: 1.5 週)
- ✅ 完成項目:
  - 設定 HPA (Horizontal Pod Autoscaler): CPU > 70% 時自動擴展
  - 設定 Resource Requests/Limits (避免資源競爭)
  - 設定 Liveness/Readiness Probe (健康檢查)
  - 設定 Ingress Controller (Nginx Ingress) + TLS (Let's Encrypt)
  - 設定 Network Policy (服務間通訊隔離)

- ⚠️ 遇到問題:
  - HPA 擴展延遲,高峰期仍有短暫效能下降
  - Liveness Probe 配置不當導致健康的 Pod 被誤殺

- 💡 解決方案:
  - 調整 HPA 評估週期 (從 30 秒降至 15 秒) + 預留 Buffer Pods (最小 3 個)
  - Liveness Probe 增加 `initialDelaySeconds` 和 `failureThreshold`

- 📊 階段產出:
  - K8s Manifests (Deployment, Service, HPA, Ingress)
  - 健康檢查配置
  - 自動擴展測試報告

#### 階段 6: 監控與日誌 (實際耗時: 1 週)
- ✅ 完成項目:
  - 部署 Prometheus Operator + Grafana
  - 設定 ServiceMonitor 自動發現服務 Metrics
  - 部署 ELK Stack (Elasticsearch + Logstash + Kibana) 集中日誌管理
  - 設定 Fluentd DaemonSet 收集所有 Pod 日誌
  - 整合 Jaeger 分散式追蹤

- ⚠️ 遇到問題:
  - Elasticsearch 資源消耗大 (需 16GB RAM)
  - 日誌量過大導致 Elasticsearch 儲存快速增長

- 💡 解決方案:
  - 使用 AWS Elasticsearch Service (Managed Service)
  - 設定日誌保留策略 (保留 7 天,舊日誌自動刪除)
  - 使用 Loki 取代 ELK (輕量級,成本更低)

- 📊 階段產出:
  - Prometheus + Grafana 儀表板 (K8s Cluster、Pod、服務指標)
  - Loki + Grafana 日誌查詢介面
  - Jaeger 分散式追蹤

#### 階段 7: 遷移與驗證 (實際耗時: 1 週)
- ✅ 完成項目:
  - 灰度遷移: 10% 流量 → K8s, 90% 流量 → VM
  - 監控關鍵指標 (錯誤率、延遲、可用性)
  - 逐步增加流量至 100%
  - 舊 VM 下線 (保留 1 週作為備援)

- ⚠️ 遇到問題:
  - 遷移過程中發現 K8s 環境 DNS 解析偶爾失敗
  - 部分舊 API 客戶端硬編碼 VM IP,導致切換後無法存取

- 💡 解決方案:
  - 設定 CoreDNS Cache + 增加 DNS Timeout
  - 保留舊 VM 的 Elastic IP,設定轉發至 K8s Ingress

- 📊 階段產出:
  - 遷移驗證報告
  - 效能對比分析 (K8s vs VM)

**關鍵經驗**:
- 💡 **成功經驗**:
  - Kubernetes 自動擴展有效應對流量高峰 (雙十一流量增 5 倍,自動擴展至 15 個 Pod)
  - 資源利用率提升至 70-80% (原 VM 僅 30-40%)
  - 部署速度提升 3 倍 (從 20 分鐘降至 6 分鐘)
  - GitOps 流程提升協作效率 (代碼即配置,可追溯)

- ⚠️ **避坑指南**:
  - **錯誤 1**: 資料庫過早容器化 → 增加風險,建議先用 Managed Service
  - **錯誤 2**: 未設定 Resource Limits → 某服務記憶體洩漏拖垮整個 Node
  - **錯誤 3**: HPA 配置過於敏感 → 頻繁擴縮容,浪費資源
  - **錯誤 4**: 未執行灰度遷移 → 全量切換風險高

- 🔄 **流程調整**:
  - 原計畫使用 ELK Stack,後改用 Loki (成本降低 60%)
  - 原計畫直接遷移資料庫,後改為使用 RDS (降低風險)

**量化成果**:
- ✅ 遷移完成時間: 6 週 (符合預期)
- ✅ 部署頻率: 從每週 2 次提升至每日 10+ 次
- ✅ 資源利用率: 從 30-40% 提升至 70-80%
- ✅ 基礎設施成本: 節省 20% (從 $600/月降至 $480/月)
- ✅ 平均回應時間: 優化 15% (從 450ms 降至 380ms)
- ✅ 自動擴展效果: 高峰流量 5 倍時,自動擴展至 15 個 Pod,服務穩定
- ✅ 可用性: 從 99.5% 提升至 99.9% (Multi-AZ + 自動容錯)
- ✅ MTTR (平均修復時間): 從 1 小時降至 10 分鐘 (自動重啟 + 健康檢查)

---

## 🎓 相關資源

- [DevOps SOP 完整版](./SOP.md)
- [DevOps DeepDive 深度指南](./SOP_DeepDive.md)
- [DevOps QuickRef 快速參考](./SOP_QuickRef.md)
- [DevOps 快速啟動指令集](../../prompts/scenario-prompts/devops-prompts.md)
- [devops-setup-flow Workflow](../../workflow/scenario-specific/devops-setup-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（基礎設施架構設計）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（CI 測試自動化）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（Pipeline 腳本開發）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（DevSecOps 安全掃描）
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

**下一步**：準備好環境後，執行 [階段 1](#階段-1啟動和情境確認-20-分鐘) 開始你的 DevOps 建置之旅！

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

> 規格凍結（SPEC_FROZEN）後，本場景的 AT 契約可交由 AutoClaude 引擎自動執行實作與雙重驗證。
> 標準作業全文：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；
> 翻譯保真規則：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`。

1. **編譯**（AutoClaude/ 目錄）：`python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out playbooks/sdd_bridge.yaml`
   - 規格未凍結 → exit 2 拒絕（Spec-First 硬閘）；weak_regex 斷言入 audit log。
2. **人工 review** 生成的 playbook YAML（SCG-4 精神：生成物 = 待審工件）。
3. **執行**：`python -m autoclaude playbooks/sdd_bridge.yaml` — SddGovernancePlugin 自動守 SCG 閘門、記帳契約違反、防規格 drift。
4. 🔴 人工確認閘門不可由自動化跳過（Rule 8）；ESCALATION 後必等人工。
