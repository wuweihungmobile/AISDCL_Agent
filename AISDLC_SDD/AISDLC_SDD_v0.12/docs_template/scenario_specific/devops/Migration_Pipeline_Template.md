# Migration 專屬 Pipeline 配置範本（Canary + Rollback）

> **🔴 最高風險情境**
>
> Migration 是 AISDLC 所有情境中風險最高的作業，涉及技術棧全面替換、資料庫遷移、流量切換。
> 本範本定義 Migration 情境專屬的 **Layer 2 (Contract Test) + Layer 3 (Canary Deploy + Rollback Gate)** Pipeline。
>
> - **適用範圍**: Migration 情境（技術棧遷移、資料庫平台遷移、系統現代化）
> - **前置條件**: Layer 0 (Security Baseline) + Layer 1 (Build & Verify) 已通過
> - **觸發分支**: `migration/*`
> - **Pipeline 類型**: `migration-pipeline`

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Migration Pipeline
**相關文檔**:
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 安全基線
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 建置驗證
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 增強安全掃描（SAST/Container/DAST）
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準關卡
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [Migration SOP](../../../scenarios/migration/SOP.md) - Migration 情境 SOP

---

## 📋 目錄

1. [Pipeline 概覽](#pipeline-概覽)
2. [Dual-Build 雙棧建置](#dual-build-雙棧建置)
3. [Contract Test API 相容性驗證](#contract-test-api-相容性驗證)
4. [Canary Deploy 金絲雀部署](#canary-deploy-金絲雀部署)
5. [Rollback Gate 回滾閘門](#rollback-gate-回滾閘門)
6. [DB Migration 安全策略](#db-migration-安全策略)
7. [效能比對驗證](#效能比對驗證)
8. [完整 Pipeline 流程](#完整-pipeline-流程)
9. [情境變體](#情境變體)
10. [維護與更新](#維護與更新)

---

## Pipeline 概覽

### 定位

```
Layer 0: Security Baseline ✅ 已通過
Layer 1: Build & Verify   ✅ 已通過
        ↓
┌──────────────────────────────────────────┐
│  Layer 2: Migration Quality Assurance     │ ← Migration 專屬
│  ├── 2.1 Dual-Build (舊棧 + 新棧)        │
│  ├── 2.2 Contract Test (API 相容性)       │
│  └── 2.3 Performance Comparison (效能比對) │
└──────────────────────────────────────────┘
        ↓ (全部通過)
┌──────────────────────────────────────────┐
│  Layer 3: Migration Deploy & Validate     │ ← Migration 專屬
│  ├── 3.1 DB Migration Dry-Run            │
│  ├── 3.2 Canary Deploy (5→25→50→100%)    │
│  ├── 3.3 Rollback Gate (每階段自動檢查)    │
│  └── 3.4 Smoke + E2E Validation          │
└──────────────────────────────────────────┘
```

### 觸發規則

```yaml
trigger:
  branches:
    - "migration/*"          # 遷移功能分支
    - "migrate/*"            # 別名
  events:
    - push                   # 分支推送觸發 Layer 2
    - pull_request            # PR 觸發完整 Layer 2 + Layer 3 (Staging)
    - release_tagged          # 正式標籤觸發 Production Canary
```

### 設計原則

| 原則 | 說明 |
|------|------|
| **Zero Downtime** | 遷移全程不停機，使用 Canary 漸進切換 |
| **Forward-Only DB** | DB Migration 必須使用 Expand-Contract Pattern，支持向前相容 |
| **Dual Verification** | 新舊系統並行驗證，結果必須一致 |
| **Automatic Rollback** | 任何階段錯誤率 > 閾值即自動回滾 |
| **Require Rollback Script** | 每個 Migration PR 必須附帶可驗證的 Rollback Script |

---

## Dual-Build 雙棧建置

### 目的

在遷移過程中，同時建置舊棧和新棧，確保兩者都能正常編譯和通過測試。

### 執行策略

```yaml
dual_build:
  old_stack:
    directory: "legacy/"       # 或獨立 repo
    build_command: "<舊棧建置命令>"
    test_command: "<舊棧測試命令>"
    required: true             # 舊棧必須繼續可建置
  new_stack:
    directory: "."             # 主目錄
    build_command: "<新棧建置命令>"
    test_command: "<新棧測試命令>"
    required: true
  parallel: true               # 新舊棧平行建置
  timeout: 15m                 # 單棧超時
```

### 各技術棧組合範例

| 遷移類型 | 舊棧命令 | 新棧命令 |
|---------|---------|---------|
| **Python → Java** | `pytest legacy/` | `mvn test` |
| **Vue → React** | `cd legacy && npm test` | `npm test` |
| **Express → Spring Boot** | `cd legacy && npm test` | `gradle test` |
| **Oracle → PostgreSQL** | `flyway validate -url=oracle` | `flyway validate -url=postgres` |
| **Monolith → Microservices** | `mvn test -pl legacy` | `mvn test -pl service-a,service-b` |

### 失敗處理

| 失敗情境 | 處理方式 |
|---------|---------|
| 舊棧建置失敗 | 🔴 阻塞 — 遷移不得破壞舊系統 |
| 新棧建置失敗 | 🔴 阻塞 — 新實作有錯誤 |
| 舊棧測試失敗 | 🔴 阻塞 — 遷移引入了舊系統回歸 |
| 新棧測試失敗 | 🔴 阻塞 — 新實作邏輯有問題 |

---

## Contract Test API 相容性驗證

### 目的

驗證新系統的 API 與舊系統完全相容，確保消費端（前端/行動端/第三方）在遷移期間不受影響。

### Contract Test 策略

```yaml
contract_test:
  approach: consumer-driven     # 消費者驅動的契約測試
  tools:
    recommended: Pact           # Pact Contract Testing Framework
    alternatives:
      - Spring Cloud Contract   # Java 生態
      - Dredd                   # API Blueprint 驗證
      - Schemathesis            # OpenAPI Schema 驗證
  scope:
    - api_endpoints             # 所有 API 端點
    - request_format            # Request Schema
    - response_format           # Response Schema
    - status_codes              # HTTP 狀態碼
    - error_format              # 錯誤回應格式
    - pagination                # 分頁格式
    - auth_flow                 # 認證流程
```

### 驗證矩陣

| 驗證項目 | 舊系統行為 | 新系統行為 | 判斷標準 |
|---------|-----------|-----------|---------|
| **API 端點路徑** | 基準 | 必須一致 | Exact Match |
| **Request Schema** | 基準 | 必須相容（可擴展不可移除） | Backward Compatible |
| **Response Schema** | 基準 | 必須相容（可擴展不可移除） | Backward Compatible |
| **HTTP Status Codes** | 基準 | 必須一致 | Exact Match |
| **Response Time** | 基準 | ≤ 1.5x 基準 | Performance Gate |
| **Error Format** | 基準 | 必須一致 | Exact Match |

### 執行方式

```bash
# 1. 從舊系統錄製 Contract
pact-mock-service record --provider=legacy-api --port=8080

# 2. 對新系統驗證 Contract
pact-provider-verifier \
  --provider-base-url=http://new-api:8081 \
  --pact-url=./pacts/consumer-legacy_api.json

# 3. 報告結果
# ✅ All contracts verified
# ❌ Contract violation: POST /api/orders response missing field 'tracking_id'
```

### 失敗處理

| 失敗類型 | 處理方式 | 說明 |
|---------|---------|------|
| 端點缺失 | 🔴 阻塞 | 新系統必須實作所有舊 API |
| Schema 不相容 | 🔴 阻塞 | Response 移除欄位會破壞消費端 |
| 新增欄位 | ✅ 允許 | 向後相容的擴展 |
| 效能退化 > 1.5x | ⚠️ 警告 | 需 Performance-Engineer 確認 |

---

## Canary Deploy 金絲雀部署

### 目的

以漸進式方式將流量從舊系統切換到新系統，降低全面上線的風險。

### Canary 階段設計

```
                    5%         25%        50%        100%
                  ┌────┐     ┌────┐     ┌────┐     ┌────┐
流量分配:         │新5% │     │新25│     │新50│     │新100│
                  │舊95│     │舊75│     │舊50│     │    │
                  └────┘     └────┘     └────┘     └────┘
                     │          │          │          │
觀察時間:          15 min     30 min     60 min      ──
                     │          │          │          │
Rollback Gate:    Error>1%?  Error>1%?  Error>0.5%?  Final
                     │          │          │
                  ❌→回滾    ❌→回滾    ❌→回滾
```

### Canary 配置

```yaml
canary_deploy:
  strategy: weighted           # 加權路由
  steps:
    - weight: 5
      pause: 15m               # 觀察 15 分鐘
      analysis:
        error_rate: "< 1%"     # 錯誤率 < 1%
        latency_p99: "< 2x"   # P99 延遲 < 2 倍基準
        success_rate: "> 99%"  # 成功率 > 99%
    - weight: 25
      pause: 30m
      analysis:
        error_rate: "< 1%"
        latency_p99: "< 1.5x"
        success_rate: "> 99%"
    - weight: 50
      pause: 60m
      analysis:
        error_rate: "< 0.5%"
        latency_p99: "< 1.2x"
        success_rate: "> 99.5%"
    - weight: 100
      analysis:
        error_rate: "< 0.5%"
        latency_p99: "< 1.1x"
        success_rate: "> 99.9%"

  # 自動回滾條件（任一觸發）
  rollback_triggers:
    - metric: error_rate
      threshold: "> 1%"
      window: 5m               # 5 分鐘滑動視窗
    - metric: latency_p99
      threshold: "> 2x baseline"
      window: 5m
    - metric: 5xx_count
      threshold: "> 10"
      window: 1m               # 1 分鐘內超過 10 個 5xx
```

### Canary 實作方式

| 工具 | 適用平台 | 方式 |
|------|---------|------|
| **Kubernetes + Istio** | K8s | VirtualService 加權路由 |
| **AWS ALB** | AWS | Target Group 加權 |
| **Nginx Upstream** | 通用 | upstream weight 配置 |
| **Argo Rollouts** | K8s | 原生 Canary CRD |
| **Flagger** | K8s + Istio/Linkerd | 自動化 Canary 分析 |

### Kubernetes + Istio 範例

```yaml
# Istio VirtualService - Canary 5%
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-service
spec:
  hosts:
    - my-service
  http:
    - route:
        - destination:
            host: my-service
            subset: legacy       # 舊版本
          weight: 95
        - destination:
            host: my-service
            subset: canary       # 新版本
          weight: 5
```

---

## Rollback Gate 回滾閘門

### 目的

在 Canary 部署的每個階段設置自動化檢查點，一旦超過閾值立即回滾。

### Rollback Gate 設計

```yaml
rollback_gate:
  # 每個 Canary 階段的檢查頻率
  check_interval: 30s

  # 回滾判斷指標
  metrics:
    - name: error_rate
      source: prometheus        # Prometheus PromQL
      query: 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])'
      threshold: 0.01           # 1%
      operator: ">"

    - name: latency_p99
      source: prometheus
      query: 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))'
      threshold_multiplier: 2.0 # 2 倍基準
      operator: ">"
      baseline_source: "legacy" # 從舊系統取基準

    - name: success_rate
      source: prometheus
      query: 'rate(http_requests_total{status=~"2.."}[5m]) / rate(http_requests_total[5m])'
      threshold: 0.99           # 99%
      operator: "<"

  # 回滾執行策略
  rollback_strategy:
    type: immediate             # 立即回滾
    steps:
      1. route_all_traffic_to_legacy   # 100% 流量回舊系統
      2. notify_oncall                  # 通知 On-Call
      3. preserve_canary_logs           # 保留 Canary 日誌供分析
      4. create_incident_ticket         # 自動建立事件單
    timeout: 60s                # 回滾必須在 60 秒內完成
```

### Rollback 自動化腳本要求

每個 Migration PR 必須附帶以下檔案：

```
migration-pr/
├── deploy/
│   ├── canary-config.yaml      # Canary 配置
│   ├── rollback.sh             # 應用層回滾腳本
│   └── db-rollback.sql         # DB 回滾腳本（如適用）
├── tests/
│   ├── contract-tests/         # API Contract Tests
│   └── rollback-test.sh        # 回滾腳本驗證
└── monitoring/
    └── alerts.yaml             # 監控告警配置
```

### CI 驗證回滾可執行性

```yaml
rollback_verification:
  # CI 中驗證回滾腳本
  steps:
    - name: "Verify rollback script exists"
      check: "test -f deploy/rollback.sh"
    - name: "Verify rollback script is executable"
      check: "bash -n deploy/rollback.sh"
    - name: "Verify DB rollback (dry-run)"
      check: "flyway validate -target=previous"
    - name: "Run rollback test"
      check: "bash tests/rollback-test.sh --dry-run"
  blocking: true                # 無回滾腳本不允許合併
```

---

## DB Migration 安全策略

### Expand-Contract Pattern（強制）

Migration 的 DB Schema 變更**必須**使用 Expand-Contract Pattern，確保新舊系統可並行運行。

```
Phase 1: EXPAND（擴展）
  ├── 新增欄位/表（不刪除舊的）
  ├── 新舊系統都能寫入
  └── 觸發器/CDC 同步資料

Phase 2: MIGRATE（遷移）
  ├── 新系統開始處理流量
  ├── 雙寫驗證（新舊系統寫入結果一致）
  └── 資料一致性校驗

Phase 3: CONTRACT（收縮）
  ├── 舊系統完全退役後
  ├── 移除舊欄位/表
  └── 清理觸發器/CDC
```

### DB Migration CI 檢查

```yaml
db_migration_checks:
  # 必要檢查
  - name: "Schema backward compatible"
    check: "不可刪除/重命名現有欄位（EXPAND 階段）"
    blocking: true

  - name: "Migration reversible"
    check: "flyway undo 或自訂 rollback SQL 存在"
    blocking: true

  - name: "No data loss"
    check: "ALTER 不含 DROP COLUMN（EXPAND 階段）"
    blocking: true

  - name: "Dry-run success"
    check: "flyway migrate -dryRun=true"
    blocking: true

  # 警告檢查
  - name: "Migration execution time"
    check: "預估執行時間 < 5 分鐘（大表需 online DDL）"
    blocking: false
```

### 雙寫驗證

```yaml
dual_write_verification:
  enabled: true
  strategy:
    - write_to: [legacy_db, new_db]     # 同時寫入
    - compare: "SELECT COUNT(*), SUM(amount) FROM orders"
    - tolerance: 0                       # 零容差
  schedule: "every 5 minutes"
  on_mismatch:
    action: alert_and_pause              # 告警並暫停遷移
    notify: [devops-engineer, sd-architect]
```

---

## 效能比對驗證

### 目的

在遷移過程中持續比對新舊系統的效能指標，確保新系統不退化。

### 比對指標

| 指標 | 資料來源 | 新系統要求 | 阻塞等級 |
|------|---------|-----------|---------|
| **API 回應時間 P50** | Prometheus | ≤ 1.2x 舊系統 | ⚠️ 警告 |
| **API 回應時間 P99** | Prometheus | ≤ 1.5x 舊系統 | 🔴 阻塞 |
| **吞吐量 (RPS)** | Prometheus | ≥ 0.8x 舊系統 | 🔴 阻塞 |
| **錯誤率** | Prometheus | ≤ 舊系統 | 🔴 阻塞 |
| **CPU 使用率** | Grafana | ≤ 1.5x 舊系統 | ⚠️ 警告 |
| **記憶體使用量** | Grafana | ≤ 1.5x 舊系統 | ⚠️ 警告 |
| **DB Query 時間** | Slow Query Log | ≤ 1.2x 舊系統 | ⚠️ 警告 |

### 自動化比對配置

```yaml
performance_comparison:
  baseline_source: "legacy-production"
  canary_source: "canary-production"
  comparison_window: 5m         # 5 分鐘滑動視窗
  report_format: markdown       # PR Comment 報告

  # PR Comment 範例
  report_template: |
    ## 🔄 Migration Performance Comparison

    | Metric | Legacy | Canary | Ratio | Status |
    |--------|--------|--------|-------|--------|
    | P50 Latency | {legacy_p50}ms | {canary_p50}ms | {ratio}x | {status} |
    | P99 Latency | {legacy_p99}ms | {canary_p99}ms | {ratio}x | {status} |
    | RPS | {legacy_rps} | {canary_rps} | {ratio}x | {status} |
    | Error Rate | {legacy_err}% | {canary_err}% | - | {status} |
```

---

## 完整 Pipeline 流程

### 流程圖

```
migration/* branch push
        │
        ▼
┌── Layer 0: Security Baseline ──┐
│   Secret Scan → SCA → License  │
└──────────── ✅ ────────────────┘
        │
        ▼
┌── Layer 1: Build & Verify ─────┐
│   Lint → Build → Unit Test     │
│   Coverage Gate (≥ 70%)        │
└──────────── ✅ ────────────────┘
        │
        ▼
┌── Layer 2: Migration QA ───────┐
│   ┌─────────────────────────┐  │
│   │ 2.1 Dual-Build          │  │
│   │   Old Stack ──┐ (parallel)│ │
│   │   New Stack ──┘          │  │
│   └─────────────────────────┘  │
│           │ ✅                  │
│   ┌─────────────────────────┐  │
│   │ 2.2 Contract Test        │  │
│   │   Pact / Schema Verify   │  │
│   └─────────────────────────┘  │
│           │ ✅                  │
│   ┌─────────────────────────┐  │
│   │ 2.3 Performance Compare  │  │
│   │   Legacy vs New Bench    │  │
│   └─────────────────────────┘  │
└──────────── ✅ ────────────────┘
        │
        ▼ (PR Merge / Release Tag)
┌── Layer 3: Migration Deploy ───┐
│   ┌─────────────────────────┐  │
│   │ 3.1 DB Migration Dry-Run│  │
│   │   + Rollback Verify      │  │
│   └─────────────────────────┘  │
│           │ ✅                  │
│   ┌─────────────────────────┐  │
│   │ 3.2 Canary Deploy        │  │
│   │   5% → 25% → 50% → 100% │  │
│   │   ↕ Rollback Gate 每階段  │  │
│   └─────────────────────────┘  │
│           │ ✅                  │
│   ┌─────────────────────────┐  │
│   │ 3.3 Smoke + E2E Test     │  │
│   │   + 雙寫驗證             │  │
│   └─────────────────────────┘  │
└──────────── ✅ ────────────────┘
        │
        ▼
    遷移完成 🎉
```

### 超時設定

| 階段 | 建議超時 | 說明 |
|------|---------|------|
| Layer 2 - Dual-Build | 15 分鐘/棧 | 平行執行 |
| Layer 2 - Contract Test | 10 分鐘 | API 驗證 |
| Layer 2 - Performance Compare | 10 分鐘 | Micro-Benchmark |
| Layer 3 - DB Dry-Run | 10 分鐘 | 乾跑驗證 |
| Layer 3 - Canary (每階段) | 觀察時間 + 5m | 含分析時間 |
| Layer 3 - Smoke + E2E | 15 分鐘 | 完整端對端 |

---

## 情境變體

### 僅 DB 遷移（小規模）

```yaml
# 簡化 Pipeline：跳過 Dual-Build，聚焦 DB
variant: db-only
skip:
  - dual_build                 # 無新應用棧
  - contract_test              # API 未變
focus:
  - db_migration_dryrun
  - db_rollback_verify
  - dual_write_verification
  - data_integrity_check       # 資料完整性
canary:
  scope: db_reads_only         # 先切讀流量，再切寫流量
```

### 前端遷移（中規模）

```yaml
# 前端遷移不涉及 DB
variant: frontend-only
skip:
  - db_migration_dryrun
  - dual_write_verification
focus:
  - dual_build                 # 新舊前端都要建置
  - contract_test              # 前端→後端 API 相容
  - visual_regression_test     # 視覺回歸測試
canary:
  strategy: url_based          # 新 URL 路徑先上線
```

### 全棧遷移（大規模）

```yaml
# 全部啟用
variant: full-stack
enable_all: true
additional:
  - dual_write_verification
  - cross_platform_test        # 如涉及行動端
canary:
  strategy: weighted
  extended_observation: true   # 延長觀察時間
```

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| Canary 閾值 | 每次遷移後回顧 | DevOps + SD |
| Contract Test 工具版本 | 每季 | DevOps Engineer |
| Rollback 腳本範本 | 每次遷移後更新 | Dev-Senior |
| 效能基準值 | 每次遷移後更新 | Performance-Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立完整 Migration Pipeline 範本 |
