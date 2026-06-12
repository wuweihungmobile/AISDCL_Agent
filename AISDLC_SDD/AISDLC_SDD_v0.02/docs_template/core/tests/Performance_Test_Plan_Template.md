# 效能測試計畫
# Performance Test Plan

**專案名稱**: [專案名稱]
**文件版本**: v1.0
**建立日期**: [YYYY-MM-DD]
**負責人**: [QA Engineer / Performance Engineer]
**審核人**: [Tech Lead / PM]

---

## 📋 文件概述

### 目的

本文件定義專案的效能測試策略、測試場景、效能目標、測試環境配置、測試執行計畫與結果分析方法。

### 適用範圍

- **專案類型**: [Web App / Mobile App / API Service / 混合]
- **測試環境**: [Staging / Pre-Production / Production-like]
- **測試週期**: [Sprint X / Release Candidate / Pre-Launch]

### 參考文件

| 文件名稱 | 版本 | 連結 |
|---------|------|------|
| SRD (System Requirements Document) | v1.0 | `docs/srd/SRD_v1.0.md` |
| API Specification | v1.0 | `docs/srd/api/API_Index.md` |
| Architecture Design Document | v1.0 | `docs/srd/Architecture_v1.0.md` |
| Non-Functional Requirements (NFR) | v1.0 | `docs/frd/NFR_v1.0.md` |

---

## 🎯 效能測試目標

### 1. 測試目標 (Performance Objectives)

| 測試類型 | 目標說明 | 優先級 |
|---------|---------|-------|
| **Load Testing** | 驗證系統在預期負載下的行為 | P0 (Critical) |
| **Stress Testing** | 找出系統極限和故障點 | P1 (High) |
| **Spike Testing** | 驗證系統面對突發流量的穩定性 | P1 (High) |
| **Endurance Testing** | 驗證系統長時間運行的穩定性 | P2 (Medium) |
| **Scalability Testing** | 驗證系統水平/垂直擴展能力 | P2 (Medium) |

### 2. 關鍵效能指標 (KPIs)

#### 2.1 回應時間 (Response Time)

| 端點/功能 | P95 目標 | P99 目標 | 備註 |
|----------|---------|---------|------|
| **API - GET /users/:id** | < 200ms | < 500ms | 用戶資料查詢 |
| **API - POST /orders** | < 500ms | < 1000ms | 訂單建立 |
| **API - POST /payments** | < 1000ms | < 2000ms | 支付處理（第三方整合） |
| **Web - 首頁載入 (FCP)** | < 1.5s | < 3.0s | First Contentful Paint |
| **Web - 首頁載入 (LCP)** | < 2.5s | < 4.0s | Largest Contentful Paint |
| **Mobile - App 啟動時間** | < 2.0s | < 3.0s | Cold start |

**定義說明**:
- **P95**: 95% 的請求必須在此時間內完成
- **P99**: 99% 的請求必須在此時間內完成

#### 2.2 吞吐量 (Throughput)

| 系統/功能 | 目標 TPS/RPS | 峰值 TPS/RPS | 備註 |
|----------|------------|-------------|------|
| **API Server** | 1,000 RPS | 2,000 RPS | Requests Per Second |
| **Database** | 5,000 QPS | 10,000 QPS | Queries Per Second |
| **Message Queue** | 10,000 msg/s | 20,000 msg/s | Kafka/RabbitMQ |

#### 2.3 資源使用率 (Resource Utilization)

| 資源類型 | 正常上限 | 告警閾值 | 備註 |
|---------|---------|---------|------|
| **CPU** | < 70% | 85% | 平均使用率 |
| **Memory** | < 80% | 90% | 平均使用率 |
| **Disk I/O** | < 70% | 85% | IOPS 使用率 |
| **Network Bandwidth** | < 60% | 80% | 上下行總和 |
| **Database Connections** | < 80% | 90% | Connection Pool |

#### 2.4 錯誤率 (Error Rate)

| 錯誤類型 | 目標錯誤率 | 備註 |
|---------|----------|------|
| **HTTP 5xx Errors** | < 0.1% | Server errors |
| **HTTP 4xx Errors** | < 1.0% | Client errors (合理範圍) |
| **Timeout Errors** | < 0.5% | Request timeouts |
| **Database Errors** | < 0.01% | Connection/Query failures |

---

## 📊 測試場景設計

### 場景 1: Load Testing - 正常負載測試

**目標**: 驗證系統在預期用戶負載下的穩定性

**測試參數**:
- **並發用戶數**: 500 users
- **測試時長**: 30 minutes
- **Ramp-up 時間**: 5 minutes
- **預期 RPS**: 1,000 RPS

**測試腳本** (JMeter/K6/Locust):
```javascript
// K6 範例
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '5m', target: 500 },  // Ramp-up
    { duration: '30m', target: 500 }, // Steady state
    { duration: '5m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  let res = http.get('https://api.example.com/users/123');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(1);
}
```

**驗收標準**:
- [x] P95 回應時間 < 200ms
- [x] P99 回應時間 < 500ms
- [x] HTTP 5xx 錯誤率 < 0.1%
- [x] CPU 使用率 < 70%
- [x] Memory 使用率 < 80%

---

### 場景 2: Stress Testing - 壓力測試

**目標**: 找出系統的極限負載和故障點

**測試參數**:
- **並發用戶數**: 500 → 2,000 users (逐步增加)
- **測試時長**: 45 minutes
- **Ramp-up 時間**: 15 minutes
- **預期 RPS**: 1,000 → 4,000 RPS

**測試腳本**:
```javascript
// K6 Stress Test
export let options = {
  stages: [
    { duration: '5m', target: 500 },   // Normal load
    { duration: '5m', target: 1000 },  // Increase
    { duration: '5m', target: 1500 },  // Increase
    { duration: '5m', target: 2000 },  // Peak load
    { duration: '10m', target: 2000 }, // Hold peak
    { duration: '5m', target: 0 },     // Ramp-down
  ],
};
```

**驗收標準**:
- [x] 識別出系統的最大承載能力 (Max RPS)
- [x] 記錄故障點的具體指標 (CPU/Memory/DB)
- [x] 系統在壓力下降後能恢復正常運作
- [x] 無資料遺失或損壞

---

### 場景 3: Spike Testing - 突發流量測試

**目標**: 驗證系統面對突發流量的應對能力

**測試參數**:
- **並發用戶數**: 100 → 1,500 → 100 users (瞬間增加)
- **測試時長**: 20 minutes
- **Spike 時長**: 2 minutes

**測試腳本**:
```javascript
// K6 Spike Test
export let options = {
  stages: [
    { duration: '2m', target: 100 },   // Normal load
    { duration: '1m', target: 1500 },  // Spike! (瞬間增加)
    { duration: '2m', target: 1500 },  // Hold spike
    { duration: '1m', target: 100 },   // Recovery
    { duration: '5m', target: 100 },   // Observe recovery
  ],
};
```

**驗收標準**:
- [x] 系統在 Spike 期間不崩潰
- [x] 錯誤率在 Spike 期間 < 5%
- [x] Spike 結束後系統能在 2 分鐘內恢復正常
- [x] 自動擴展機制 (Auto-scaling) 能在 5 分鐘內觸發

---

### 場景 4: Endurance Testing - 長時間運行測試

**目標**: 驗證系統長時間運行的穩定性（檢測 Memory Leak、Connection Leak）

**測試參數**:
- **並發用戶數**: 300 users
- **測試時長**: 8 hours
- **預期 RPS**: 600 RPS

**測試腳本**:
```javascript
// K6 Endurance Test
export let options = {
  stages: [
    { duration: '5m', target: 300 },   // Ramp-up
    { duration: '8h', target: 300 },   // Endurance (8 hours)
    { duration: '5m', target: 0 },     // Ramp-down
  ],
};
```

**驗收標準**:
- [x] Memory 使用率保持穩定（無持續上升趨勢）
- [x] 無 Memory Leak 跡象
- [x] 無 Connection Leak 跡象
- [x] 回應時間保持穩定（P95 不超過正常值的 10%）
- [x] 錯誤率保持穩定 < 0.1%

---

### 場景 5: Scalability Testing - 可擴展性測試

**目標**: 驗證系統水平擴展的效果

**測試參數**:
- **Instance 數量**: 2 → 4 → 8 instances
- **並發用戶數**: 500 → 1,000 → 2,000 users
- **測試時長**: 1 hour

**測試計畫**:
1. **Phase 1**: 2 instances + 500 users → 記錄 RPS/P95
2. **Phase 2**: 4 instances + 1,000 users → 記錄 RPS/P95
3. **Phase 3**: 8 instances + 2,000 users → 記錄 RPS/P95

**驗收標準**:
- [x] Instance 數量翻倍 → 處理能力約翻倍 (線性擴展)
- [x] P95 回應時間保持穩定（不隨 Instance 增加而劣化）
- [x] 無單點故障 (Single Point of Failure)

---

## 🛠️ 測試環境配置

### 1. 測試環境架構

```
┌─────────────────────────────────────────────────┐
│          Load Generator (K6/JMeter)             │
│  - 3 Machines (AWS EC2 c5.2xlarge)              │
│  - Total 10,000 VUs capacity                    │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           Load Balancer (ALB)                   │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ App Server 1 │    │ App Server 2 │
│ (4 vCPU,     │    │ (4 vCPU,     │
│  16GB RAM)   │    │  16GB RAM)   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └───────┬───────────┘
               ▼
     ┌──────────────────┐
     │   Database       │
     │   (PostgreSQL)   │
     │   (8 vCPU,       │
     │    32GB RAM)     │
     └──────────────────┘
```

### 2. 環境規格

| 元件 | 規格 | 數量 | 備註 |
|-----|------|-----|------|
| **Load Generator** | AWS EC2 c5.2xlarge (8 vCPU, 16GB RAM) | 3 | K6 Cloud / JMeter Cluster |
| **Application Server** | AWS EC2 t3.xlarge (4 vCPU, 16GB RAM) | 2 | Node.js / Python / Java |
| **Database** | AWS RDS r5.2xlarge (8 vCPU, 32GB RAM) | 1 | PostgreSQL 14 |
| **Cache** | AWS ElastiCache r5.large (2 vCPU, 13GB RAM) | 1 | Redis 6.x |
| **Load Balancer** | AWS ALB | 1 | Application Load Balancer |

### 3. 測試資料準備

| 資料類型 | 數量 | 產生方式 | 備註 |
|---------|------|---------|------|
| **Users** | 100,000 | Faker.js / SQL Script | 預先建立測試用戶 |
| **Products** | 10,000 | CSV Import | 商品資料 |
| **Orders** | 50,000 | API Pre-populate | 歷史訂單資料 |
| **Sessions** | - | Dynamic | 測試期間動態產生 |

**測試資料腳本範例**:
```bash
# Generate 100,000 test users
node scripts/generate-test-users.js --count 100000

# Import products from CSV
psql -d testdb -c "\COPY products FROM 'products.csv' CSV HEADER"

# Pre-populate orders via API
node scripts/populate-orders.js --count 50000
```

---

## 📅 測試執行計畫

### 測試時程表

| 階段 | 測試項目 | 執行日期 | 負責人 | 狀態 |
|-----|---------|---------|-------|------|
| **Phase 1** | 環境準備與驗證 | Week 1 | DevOps | ☐ Pending |
| **Phase 2** | Load Testing | Week 2 Day 1-2 | QA | ☐ Pending |
| **Phase 3** | Stress Testing | Week 2 Day 3-4 | QA | ☐ Pending |
| **Phase 4** | Spike Testing | Week 2 Day 5 | QA | ☐ Pending |
| **Phase 5** | Endurance Testing | Week 3 Day 1-2 | QA | ☐ Pending |
| **Phase 6** | Scalability Testing | Week 3 Day 3-4 | DevOps + QA | ☐ Pending |
| **Phase 7** | 結果分析與報告 | Week 3 Day 5 | QA Lead | ☐ Pending |

### 測試前檢查清單

- [ ] 測試環境已建立且與 Production 相似度 > 80%
- [ ] 測試資料已準備完成
- [ ] 監控系統已配置 (Grafana/Prometheus/DataDog)
- [ ] 測試腳本已撰寫並通過 Dry-run
- [ ] 所有相關人員已知悉測試時程
- [ ] 已取得 Staging 環境的使用許可
- [ ] 已備份測試環境資料 (可快速恢復)

---

## 📈 監控與指標收集

### 1. 監控工具配置

| 工具 | 用途 | 指標範例 |
|-----|------|---------|
| **K6 Cloud / Grafana** | 效能測試指標視覺化 | RPS, Response Time, Error Rate |
| **Prometheus + Grafana** | 系統資源監控 | CPU, Memory, Disk I/O, Network |
| **DataDog / New Relic** | APM (Application Performance Monitoring) | Transaction Trace, Slow Queries |
| **AWS CloudWatch** | 雲端資源監控 | EC2, RDS, ALB Metrics |

### 2. 關鍵監控指標

#### Application Layer
- [ ] HTTP Request Rate (RPS)
- [ ] HTTP Response Time (P50/P95/P99)
- [ ] HTTP Error Rate (5xx/4xx)
- [ ] Active Connections

#### Database Layer
- [ ] Query Execution Time
- [ ] Slow Query Count (> 1s)
- [ ] Active Connections
- [ ] Connection Pool Saturation

#### Infrastructure Layer
- [ ] CPU Utilization (%)
- [ ] Memory Utilization (%)
- [ ] Disk I/O (IOPS)
- [ ] Network Throughput (Mbps)

---

## 📊 結果分析與報告

### 1. 測試結果摘要範本

| 測試場景 | 通過/失敗 | 關鍵發現 | 改進建議 |
|---------|----------|---------|---------|
| Load Testing | ✅ Pass | P95 < 200ms, 錯誤率 0.05% | - |
| Stress Testing | ⚠️ Partial | 系統在 1,800 RPS 時 CPU 達 95% | 增加 CPU 資源或優化程式碼 |
| Spike Testing | ❌ Fail | Spike 期間錯誤率 12% | 實作 Rate Limiting 和 Circuit Breaker |
| Endurance Testing | ✅ Pass | 8 小時運行穩定 | - |
| Scalability Testing | ✅ Pass | 線性擴展效果良好 | - |

### 2. 效能瓶頸分析

**已識別瓶頸**:
1. **Database Query Performance**
   - 問題: `/api/orders` 端點在高並發下查詢時間 > 2s
   - 原因: 缺少 `user_id` 索引
   - 解決方案: 新增索引 `CREATE INDEX idx_orders_user_id ON orders(user_id);`
   - 預期改善: 查詢時間降低至 < 200ms

2. **Connection Pool Exhaustion**
   - 問題: 並發用戶數 > 800 時出現 Connection Pool 耗盡
   - 原因: Connection Pool Size = 100 (過小)
   - 解決方案: 增加 Pool Size 至 300
   - 預期改善: 支援 > 1,500 並發用戶

### 3. 改進建議優先級

| 優先級 | 改進項目 | 預估工時 | 預期效果 |
|-------|---------|---------|---------|
| **P0 - Critical** | 新增 Database 索引 | 2 hr | 查詢時間降低 90% |
| **P0 - Critical** | 增加 Connection Pool Size | 1 hr | 支援並發數提升 50% |
| **P1 - High** | 實作 Redis Cache | 8 hr | 回應時間降低 60% |
| **P1 - High** | 實作 Rate Limiting | 6 hr | 避免 Spike 流量衝擊 |
| **P2 - Medium** | 資料庫讀寫分離 | 16 hr | 寫入性能提升 40% |

---

## ✅ 驗收標準

### 整體驗收標準

- [ ] **所有 P0/P1 測試場景必須通過**
- [ ] **所有關鍵 KPI 必須達標** (P95 Response Time, Error Rate)
- [ ] **所有已識別的 P0 瓶頸必須修復並重測**
- [ ] **效能測試報告已撰寫並經 Tech Lead 審核**
- [ ] **改進建議清單已建立並納入 Backlog**

### 測試報告必須包含

- [ ] 測試摘要 (Executive Summary)
- [ ] 測試環境描述
- [ ] 測試場景與結果
- [ ] 效能指標圖表 (Grafana Screenshots)
- [ ] 瓶頸分析與改進建議
- [ ] 風險評估

---

## 📞 聯絡資訊

| 角色 | 姓名 | Email | 職責 |
|-----|------|-------|------|
| **QA Lead** | [姓名] | [email] | 測試計畫審核、結果分析 |
| **Performance Engineer** | [姓名] | [email] | 測試執行、腳本撰寫 |
| **Tech Lead** | [姓名] | [email] | 瓶頸分析、改進方案 |
| **DevOps Engineer** | [姓名] | [email] | 環境配置、監控設置 |

---

## 📚 附錄

### A. 測試工具參考

| 工具 | 適用場景 | 優勢 | 劣勢 |
|-----|---------|-----|------|
| **K6** | API / Web | JavaScript 腳本、雲端執行、易整合 CI/CD | GUI 較弱 |
| **JMeter** | API / Web / DB | 功能完整、GUI 友善、社群大 | Java-based, 資源消耗高 |
| **Locust** | API / Web | Python 腳本、分散式執行 | 監控功能較弱 |
| **Gatling** | API / Web | 高性能、Scala-based | 學習曲線陡 |
| **Artillery** | API / Web | YAML 配置簡單 | 進階功能較少 |

### B. 效能測試最佳實踐

1. **測試環境盡可能接近 Production**
2. **使用真實的用戶行為模式** (不是單純重複同一個請求)
3. **監控所有層級** (Application / Database / Infrastructure)
4. **逐步增加負載** (不要一次到達峰值)
5. **測試後清理資料** (避免影響下次測試)
6. **記錄所有配置變更** (測試環境的任何調整)

### C. 常見效能問題與解決方案

| 問題 | 可能原因 | 解決方案 |
|-----|---------|---------|
| **高回應時間** | 缺少 Database 索引 | 新增索引 |
| **高錯誤率** | Connection Pool 耗盡 | 增加 Pool Size 或實作 Connection Retry |
| **記憶體持續上升** | Memory Leak | 使用 Profiler 找出 Leak 位置 |
| **CPU 高使用率** | 演算法效率低 | 程式碼優化或 Cache |

---

**文件版本歷史**:

| 版本 | 日期 | 變更內容 | 作者 |
|-----|------|---------|------|
| v1.0 | [YYYY-MM-DD] | 初始版本 | [作者] |

---

**審核記錄**:

| 審核者 | 日期 | 審核結果 | 意見 |
|-------|------|---------|------|
| [Tech Lead] | [日期] | ☐ 通過 ☐ 需修改 | [意見] |
| [QA Lead] | [日期] | ☐ 通過 ☐ 需修改 | [意見] |
