# Performance Baseline Specification — Template
# 效能基準規格文件模板（PBS）
# Phase 05 — Performance 情境 SDD 強化

**文件類型**: Performance Baseline Specification (PBS)
**SDD Gate**: SCG-6 Delivery Gate
**SDD 原則**: PBS 必須先於任何效能測試執行（Spec-First 強制）
**存放位置**: `docs/03_testing/PERFORMANCE-BASELINE-SPEC-{project}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **版本** | {Version} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Performance Engineer} |
| **SCG Gate** | SCG-6 □ 待審 / □ 通過（PBS 凍結前禁止執行效能測試） |
| **前置文件** | SRD-{project}.md, INFRA-REQUIREMENTS-SPEC-{project}.md |

---

## 1. 系統 SLO 定義（Service Level Objectives）

> **SDD 原則**: 所有 SLO 必須量化，且有對應的 Pass/Fail Criteria。

### 1.1 可用性（Availability）

| SLO ID | 指標 | 目標值 | 測量週期 | 計算方式 |
|--------|------|--------|---------|---------|
| SLO-AVAIL-001 | 系統可用率 | ≥ {99.9 / 99.99}% | 30 天滾動 | (Total - Downtime) / Total × 100% |
| SLO-AVAIL-002 | API 成功率 | ≥ {99.5}% | 每小時 | 2xx responses / total requests |

### 1.2 延遲（Latency）

| SLO ID | API 端點 | P50 目標 | P95 目標 | P99 目標 | 最大可接受 |
|--------|---------|---------|---------|---------|----------|
| SLO-LAT-001 | GET /api/{resource} | < {50}ms | < {200}ms | < {500}ms | {1000}ms |
| SLO-LAT-002 | POST /api/{resource} | < {100}ms | < {500}ms | < {1000}ms | {2000}ms |
| SLO-LAT-003 | 關鍵業務流程 {name} | < {200}ms | < {800}ms | < {2000}ms | {5000}ms |

**延遲測量方式**: 從請求到達 Load Balancer 到回傳完整 Response 的時間

### 1.3 吞吐量（Throughput）

| SLO ID | 場景 | 目標 RPS | 目標 TPS | 說明 |
|--------|------|---------|---------|------|
| SLO-THRU-001 | 正常負載 | > {500} RPS | > {N} TPS | 日常業務流量 |
| SLO-THRU-002 | 峰值負載 | > {2000} RPS | > {N} TPS | 節假日高峰 |
| SLO-THRU-003 | 壓力上限 | > {5000} RPS | > {N} TPS | 系統極限（優雅降級點） |

### 1.4 錯誤率（Error Rate）

| SLO ID | 場景 | 目標錯誤率 | 計算範圍 |
|--------|------|----------|---------|
| SLO-ERR-001 | 正常負載 | < 0.1% | 所有 5xx 錯誤 |
| SLO-ERR-002 | 峰值負載 | < 0.5% | 所有 5xx 錯誤 |
| SLO-ERR-003 | Timeout 率 | < 0.05% | 超過 P99 閾值的請求 |

### 1.5 資源使用（Resource Utilization）

| SLO ID | 資源 | 正常負載 | 峰值負載 | 報警閾值 |
|--------|------|---------|---------|---------|
| SLO-RES-001 | CPU 使用率 | < {60}% | < {80}% | > {85}% |
| SLO-RES-002 | Memory 使用率 | < {70}% | < {85}% | > {90}% |
| SLO-RES-003 | DB Connection 使用率 | < {60}% | < {80}% | > {85}% |
| SLO-RES-004 | Network 帶寬使用率 | < {50}% | < {75}% | > {80}% |

---

## 2. 測試場景規格（Test Scenarios）

### 2.1 場景定義

| 場景 ID | 場景名稱 | 並發使用者數 | RPS 目標 | 持續時間 | 說明 |
|--------|---------|------------|---------|---------|------|
| PERF-SCEN-001 | 正常負載（Normal Load） | {N} VU | {N} RPS | {30} min | 代表日常業務量 |
| PERF-SCEN-002 | 峰值負載（Peak Load） | {N} VU | {N} RPS | {15} min | 代表業務高峰期 |
| PERF-SCEN-003 | 壓力測試（Stress Load） | {N} VU | {N} RPS | {10} min | 尋找系統瓶頸點 |
| PERF-SCEN-004 | 耐久測試（Soak Test） | {N} VU | {N} RPS | {2} hr | 檢測記憶體洩漏 |
| PERF-SCEN-005 | 尖刺測試（Spike Test） | {N → N} VU | 0 → max | {5} min | 測試突發流量 |

### 2.2 使用者行為模型（User Journey Weights）

| 使用者操作 | 比例 | 對應 API |
|----------|------|---------|
| {操作名稱-1} | {30}% | {endpoint} |
| {操作名稱-2} | {25}% | {endpoint} |
| {操作名稱-3} | {20}% | {endpoint} |
| 其他操作 | {25}% | 各 endpoint |

### 2.3 資料規格

| 資料類型 | 規模 | 說明 |
|---------|------|------|
| DB 記錄數 | {N} million rows | 接近生產環境規模 |
| 測試帳號數 | {N} accounts | 分散登入避免 Session 瓶頸 |
| 測試資料集 | {N} MB | {description} |

---

## 3. 通過標準（Pass/Fail Criteria）

> **SDD 核心**: 每次 Benchmark 必須對照此標準自動判斷通過/失敗

### 3.1 必須全部通過（Hard Criteria）

| 標準 ID | 條件 | 失敗時行動 |
|--------|------|----------|
| PASS-001 | 正常負載下 P95 延遲 ≤ PBS 目標值 | 阻擋發布，啟動瓶頸分析 |
| PASS-002 | 正常負載下錯誤率 < 0.1% | 阻擋發布，根因分析 |
| PASS-003 | 峰值負載下系統不崩潰 | 阻擋發布，容量規劃 |
| PASS-004 | 峰值負載下 CPU < {80}% | 發出警告，評估是否阻擋 |
| PASS-005 | 耐久測試後無記憶體洩漏 | 阻擋發布，記憶體分析 |

### 3.2 警告標準（Soft Criteria）

| 標準 ID | 條件 | 行動 |
|--------|------|------|
| WARN-001 | 正常負載下 P99 延遲 > PBS 目標的 80% | 記錄，下次 Sprint 優化 |
| WARN-002 | 資源使用率超過正常閾值 50% | 通知 DevOps 評估擴容 |

---

## 4. 效能測試工具規格

| 工具 | 用途 | ADR 參考 |
|-----|------|---------|
| {k6 / JMeter / Gatling} | 負載生成 | ADR-{NNN}-{performance-tool} |
| Grafana + Prometheus | 即時監控 | — |
| APM（{Datadog / New Relic / Jaeger}） | 效能剖析 | ADR-{NNN} |
| {flame graph tool} | CPU 剖析 | — |

---

## 5. 基準測量規劃

| 測量類型 | 執行時機 | 目的 |
|---------|---------|------|
| Baseline Benchmark | 首次部署後，任何優化前 | 建立基準線（見 BASELINE-PERFORMANCE-REPORT） |
| Regression Benchmark | 每次 PR 合併後 | 防止效能退化 |
| Release Benchmark | 每次發布前 | 確認 SLO 達標 |
| Post-Optimization | 每次優化措施後 | 驗證優化效果 |

---

## 6. 優化觸發條件

> 當以下任一條件發生，必須啟動優化流程並建立 Optimization ADR

| 觸發條件 | 嚴重度 | 對應措施 |
|---------|-------|---------|
| P95 > PBS 目標 | High | 立即瓶頸分析 |
| 錯誤率 > 0.5% | Critical | 立即根因分析 |
| CPU 使用率 > 85% | Medium | 評估擴容或優化 |
| 記憶體持續增長 | High | 記憶體洩漏分析 |
| 峰值 TPS 下降 > 20% | High | 容量規劃評估 |

---

## 7. 監控告警規格

> 每個 SLO 必須有對應的監控告警（詳見 MONITORING-ALERT-SPEC）

| SLO ID | 告警名稱 | 閾值 | 告警管道 |
|--------|---------|------|---------|
| SLO-LAT-001~003 | ALERT-LAT-{NNN} | > P99 × 1.5 | PagerDuty / Slack |
| SLO-ERR-001~003 | ALERT-ERR-{NNN} | > 0.1% for 5min | PagerDuty |
| SLO-RES-001~004 | ALERT-RES-{NNN} | > 85% for 10min | Slack |

---

## 📋 PBS 凍結確認（SCG-6 Gate）

> 🔴 **PBS 必須凍結後才能執行任何效能測試**

| 驗證項目 | 標準 | 狀態 |
|---------|------|------|
| 所有 SLO 量化完成 | 有具體數值（非「盡量快」） | □ |
| 測試場景規格完整 | Normal/Peak/Stress/Soak 均已定義 | □ |
| Pass/Fail Criteria 量化 | 有明確通過/失敗判斷標準 | □ |
| 工具選型 ADR 完成 | 測試工具已決策 | □ |
| 監控規格連結 | 每個 SLO 有對應告警 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過（PBS 凍結）/ □ 待修訂
