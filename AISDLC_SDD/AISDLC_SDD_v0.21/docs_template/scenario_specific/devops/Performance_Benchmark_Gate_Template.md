# Performance Micro-Benchmark Gate 配置範本

> **🔴 P2 效能關卡**
>
> 此範本定義如何在 CI/CD Pipeline 中整合 **Performance Benchmark Gate**，
> 防止效能退化（Performance Regression）進入主分支。
>
> - **PR 階段**: Micro-Benchmark（< 2 分鐘）— 快速偵測效能退化
> - **Nightly 排程**: Full Load Test（30-60 分鐘）— 完整效能剖析
> - **目標**: 效能從「事後檢測」提前到「PR 階段即時攔截」

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Performance Benchmark
**相關文檔**:
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 安全基線
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 Build & Verify
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 增強安全掃描
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [Documentation_Pipeline_Template.md](./Documentation_Pipeline_Template.md) - P2 文檔 Pipeline
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [Performance SOP](../../../scenarios/performance/SOP.md) - Performance 情境完整 SOP

---

## 📋 目錄

1. [雙層效能測試模型](#雙層效能測試模型)
2. [Micro-Benchmark（PR 階段）](#micro-benchmarkpr-階段)
3. [Full Load Test（Nightly 階段）](#full-load-testnightly-階段)
4. [效能基線管理](#效能基線管理)
5. [SLA Gate 閾值設定](#sla-gate-閾值設定)
6. [工具選型](#工具選型)
7. [情境適用性](#情境適用性)
8. [Pipeline 整合位置](#pipeline-整合位置)
9. [維護與更新](#維護與更新)

---

## 雙層效能測試模型

### 分層執行策略

```
PR 階段（每次 PR 觸發）              Nightly（每日/每週排程）
┌─────────────────────┐            ┌─────────────────────────┐
│ Micro-Benchmark     │            │ Full Load Test          │
│ ├── 單元效能測試     │            │ ├── 並發負載測試         │
│ ├── API 回應時間     │            │ ├── 壓力測試 (Stress)   │
│ ├── 記憶體使用量     │            │ ├── 持續穩定性測試       │
│ └── 關鍵路徑延遲     │            │ └── 資源飽和測試         │
│                     │            │                         │
│ ⏱️ < 2 分鐘         │            │ ⏱️ 30-60 分鐘           │
│ 🔴 退化 > 10% 阻塞  │            │ ⚠️ 結果次日審查          │
└─────────────────────┘            └─────────────────────────┘
```

### 為什麼需要雙層？

| 層級 | 目的 | 耗時 | 頻率 | 阻塞 |
|------|------|------|------|------|
| **Micro-Benchmark** | 快速偵測效能退化 | < 2 分鐘 | 每次 PR | 🔴 退化阻塞 |
| **Full Load Test** | 完整系統效能剖析 | 30-60 分鐘 | Nightly | ⚠️ 僅警告 |

---

## Micro-Benchmark（PR 階段）

### 測試內容

| 測試類型 | 量測指標 | 退化閾值 | 說明 |
|---------|---------|---------|------|
| **單元效能** | 函數執行時間 | > 10% 退化 | 關鍵演算法效能 |
| **API 回應** | P50 / P95 / P99 延遲 | > 15% 退化 | 核心 API 端點 |
| **記憶體** | 峰值 RSS / Heap | > 20% 增長 | 記憶體洩漏偵測 |
| **啟動時間** | 冷啟動耗時 | > 20% 退化 | 應用啟動效能 |

### 各語言 Benchmark 工具

| 語言 | Benchmark 工具 | 命令範例 |
|------|---------------|---------|
| **Node.js/TS** | Vitest bench / Benchmark.js | `vitest bench` / `node benchmark.js` |
| **Python** | pytest-benchmark / asv | `pytest --benchmark-only` |
| **Java** | JMH (Java Microbenchmark Harness) | `mvn exec:java -Dexec.mainClass="benchmarks"` |
| **Go** | go test -bench | `go test -bench=. -benchmem ./...` |
| **Rust** | cargo bench / criterion | `cargo bench` |
| **Kotlin/Android** | AndroidBenchmark | `./gradlew :benchmark:connectedAndroidTest` |

### Micro-Benchmark 配置

```yaml
micro_benchmark:
  # 觸發條件
  trigger:
    - pull_request
    - push: [main, develop]

  # 測試配置
  tests:
    unit_perf:
      command: "npm run bench"          # 依語言替換
      timeout: 60s                      # 單項測試超時
    api_latency:
      command: "npm run bench:api"      # API 端點測試
      timeout: 60s

  # 退化偵測
  regression:
    threshold: 10%                      # 效能退化 > 10% 阻塞
    comparison: baseline                # 與基線比較
    metric: mean                        # 使用平均值

  # 整體超時
  total_timeout: 120s                   # 2 分鐘硬上限

  # 基線快取
  baseline:
    cache_key: "perf-baseline-${{ branch }}"
    update_on: main                     # main 分支更新基線
```

---

## Full Load Test（Nightly 階段）

### 測試內容

| 測試類型 | 工具 | 時長 | 目標 |
|---------|------|------|------|
| **並發測試** | k6 / Gatling / Locust | 10-15 分鐘 | 正常負載下的效能表現 |
| **壓力測試** | k6 / Gatling | 10-15 分鐘 | 找到系統極限 |
| **穩定性測試** | k6 (soak) | 15-30 分鐘 | 長時間運行的記憶體/資源 |
| **資源飽和** | k6 + Prometheus | 5-10 分鐘 | CPU/Memory/IO 上限 |

### Full Load Test 配置

```yaml
full_load_test:
  # 觸發條件
  trigger:
    - schedule: "0 2 * * *"            # 每日 02:00 UTC
    - manual                            # 手動觸發

  # 測試配置
  tests:
    load_test:
      tool: k6
      script: "tests/performance/load-test.js"
      vus: 100                          # 虛擬使用者數
      duration: "10m"
    stress_test:
      tool: k6
      script: "tests/performance/stress-test.js"
      stages:
        - duration: "2m", target: 50
        - duration: "5m", target: 200
        - duration: "3m", target: 0
    soak_test:
      tool: k6
      script: "tests/performance/soak-test.js"
      vus: 50
      duration: "30m"

  # 結果處理
  results:
    format: json
    upload: true                        # 上傳至 Artifact
    compare_with_baseline: true

  # 專屬 Runner
  runner: perf-runner-pool              # 獨立 Runner，不佔通用資源
```

---

## 效能基線管理

### 基線更新策略

```
main 分支合併成功
    ↓
自動執行 Micro-Benchmark
    ↓
結果寫入基線快取
    ↓
後續 PR 與此基線比較
```

### 基線快取配置

```yaml
baseline_management:
  # 基線來源
  source: main                          # main 分支為基線

  # 快取策略
  cache:
    key: "perf-baseline-v{version}"
    path: ".perf-baseline/"
    ttl: 7d                             # 7 天過期（Nightly 會更新）

  # 更新觸發
  update_triggers:
    - push_to_main                      # main 分支推送
    - nightly_schedule                  # Nightly 排程
    - manual                            # 手動更新

  # 新專案（無基線）
  first_run:
    action: "create_baseline"           # 首次運行建立基線
    skip_regression: true               # 無基線時跳過退化檢查
```

---

## SLA Gate 閾值設定

### 預設閾值

| 指標 | PR 閾值（Micro） | Nightly 閾值（Full） | 阻塞策略 |
|------|-----------------|--------------------|---------|
| **P50 延遲** | 退化 ≤ 10% | ≤ 200ms | 🔴 PR 阻塞 |
| **P95 延遲** | 退化 ≤ 15% | ≤ 500ms | 🔴 PR 阻塞 |
| **P99 延遲** | 退化 ≤ 20% | ≤ 1000ms | ⚠️ 警告 |
| **吞吐量 (RPS)** | 退化 ≤ 10% | ≥ 1000 RPS | ⚠️ 警告 |
| **記憶體峰值** | 增長 ≤ 20% | ≤ 512MB | ⚠️ 警告 |
| **錯誤率** | ≤ 0.1% | ≤ 0.5% | 🔴 阻塞 |

### 閾值配置

```yaml
# .perf-config.yml（專案根目錄）
sla_gates:
  pr_level:
    latency_p50_regression: 10%         # P50 退化 > 10% 阻塞
    latency_p95_regression: 15%         # P95 退化 > 15% 阻塞
    memory_growth: 20%                  # 記憶體增長 > 20% 警告
    error_rate: 0.1%                    # 錯誤率 > 0.1% 阻塞

  nightly_level:
    latency_p50_absolute: 200ms
    latency_p95_absolute: 500ms
    latency_p99_absolute: 1000ms
    throughput_min: 1000                # 最低 RPS
    error_rate: 0.5%

  # 閾值調整
  overrides:
    # 效能敏感路徑更嚴格
    critical_paths:
      - path: "/api/v1/checkout"
        latency_p95_absolute: 300ms
      - path: "/api/v1/search"
        latency_p50_absolute: 100ms
```

---

## 工具選型

### 推薦工具組合

| 類型 | 推薦工具（免費） | 商業替代 | 適用場景 |
|------|----------------|---------|---------|
| **Micro-Benchmark** | Vitest bench / pytest-benchmark / JMH / go bench | - | PR 階段快速測試 |
| **Load Test** | **k6** (推薦) / Gatling / Locust | LoadRunner, BlazeMeter | Nightly 完整負載 |
| **APM 監控** | Prometheus + Grafana | Datadog, New Relic | 效能數據收集 |
| **結果比對** | benchmark-action (GitHub) | - | 自動退化偵測 |

### k6 快速配置範例

```javascript
// tests/performance/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },    // 漸增至 50 VU
    { duration: '3m', target: 50 },    // 維持 50 VU
    { duration: '1m', target: 0 },     // 漸減
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // P95 < 500ms
    http_req_failed: ['rate<0.01'],     // 錯誤率 < 1%
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

---

## 情境適用性

### Performance Benchmark Gate 適用矩陣

| 情境 | Micro-Benchmark | Full Load Test | 說明 |
|------|:---:|:---:|------|
| `performance` | 🔴 強制 | 🔴 強制 (Nightly) | 核心情境，完整效能測試 |
| `greenfield` | ⚠️ 選配 | ❌ | 新專案建立初始基線 |
| `brownfield` | ⚠️ 選配 | ❌ | 關鍵路徑退化偵測 |
| `refactoring` | ⚠️ 選配 | ❌ | 重構不引入效能退化 |
| `migration` | ⚠️ 選配 | ⚠️ 新舊棧比對 | 遷移效能不退化 |
| `integration` | ❌ | ❌ | 整合 API 效能靠 Nightly |
| `devops` | ❌ | ❌ | Pipeline 自身效能不需要 |
| `testing` | ❌ | ❌ | 測試框架效能不需要 |
| `documentation` | ❌ | ❌ | 不適用 |
| `security` | ❌ | ❌ | 安全掃描不需效能關卡 |

---

## Pipeline 整合位置

### 執行順序

```
Layer 0: Security Baseline ✅
Layer 1: Build & Verify ✅
    ↓
┌─────────────────────────────────────────────┐
│  Layer 2: Performance Benchmark (本範本)     │
│  ├── Micro-Benchmark (PR 階段, < 2min)     │
│  └── Full Load Test (Nightly, 30-60min)    │
└─────────────────────────────────────────────┘
    ↓
Layer 2: Other QA (Security Scan 等)
Layer 3: Deploy & Validate
```

### 超時設定

| 測試 | PR 階段 | Nightly | 超時後處理 |
|------|---------|---------|-----------|
| **Micro-Benchmark** | 2 分鐘 | 5 分鐘 | ⚠️ 降級為警告 |
| **Full Load Test** | N/A | 60 分鐘 | ⚠️ 降級為警告 |

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| 效能基線 | 每次 main 合併 (自動) | CI/CD |
| SLA 閾值 | 每季審查 | Performance-Engineer + SD |
| Load Test 腳本 | 功能變更時 | Dev + Performance-Engineer |
| 測試工具版本 | 每月 | DevOps-Engineer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立雙層效能測試模型 + SLA Gate |
