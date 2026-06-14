# Baseline Performance Report — Template
# 基準效能報告模板（對照 PBS）
# Phase 05 — Performance 情境 SDD 強化

**文件類型**: Baseline Performance Report (BPR)
**SDD 原則**: 每次 Benchmark 必須對照 PBS 規格進行分析
**存放位置**: `docs/03_testing/BASELINE-PERFORMANCE-REPORT-{project}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **測試版本** | {Version} |
| **Benchmark 日期** | {YYYY-MM-DD HH:MM} |
| **執行人** | {Performance Engineer} |
| **PBS 參考** | PERFORMANCE-BASELINE-SPEC-{project}-{date}.md |
| **環境** | {Staging / Load-Test-Env} |
| **報告類型** | □ 初始基準 / □ 回歸 Benchmark / □ 發布前驗證 / □ 優化後驗證 |

---

## 1. 執行摘要

### 1.1 整體結論

| 結論 | 說明 |
|------|------|
| **整體狀態** | ✅ 通過所有 PBS Hard Criteria / ❌ {N} 個 Hard Criteria 未達標 |
| **可以發布** | □ 是（所有 Hard Criteria 通過）/ □ 否（見阻擋清單） |
| **發現瓶頸數** | {N} 個 |
| **建議行動** | {一行摘要} |

### 1.2 PBS Hard Criteria 對照

| 標準 ID | 條件 | 目標值 | 實際值 | 結果 |
|--------|------|-------|--------|------|
| PASS-001 | 正常負載 P95 延遲 | ≤ {N}ms | {N}ms | ✅ PASS / ❌ FAIL |
| PASS-002 | 正常負載錯誤率 | < 0.1% | {X}% | ✅ PASS / ❌ FAIL |
| PASS-003 | 峰值負載系統穩定性 | 不崩潰 | {穩定/崩潰} | ✅ PASS / ❌ FAIL |
| PASS-004 | 峰值負載 CPU | < {80}% | {X}% | ✅ PASS / ❌ FAIL |
| PASS-005 | 記憶體洩漏（耐久測試） | 無持續增長 | {穩定/增長} | ✅ PASS / ❌ FAIL |

---

## 2. 測試環境

| 環境項目 | 規格 |
|---------|------|
| 應用伺服器 | {N} × {instance_type}, {CPU} vCPU, {RAM} GB |
| 資料庫 | {db_type}, {instance_type}, {storage} |
| Load Balancer | {type} |
| CDN | {enabled / disabled} |
| 快取 | {Redis/Memcached} {memory} GB |
| 網路 | {region}, {bandwidth} |
| DB 資料量 | {N} million rows（vs 生產環境 {Y}%） |
| 測試工具 | {k6 / JMeter}, Version {version} |
| 測試執行節點 | {N} × {instance_type} |

---

## 3. 測試場景執行結果

### 3.1 PERF-SCEN-001：正常負載

**設定**: {N} VU, 目標 {N} RPS, 持續 {30} min

| 指標 | PBS 目標 | P25 | P50 | P95 | P99 | Max | 達標 |
|-----|---------|-----|-----|-----|-----|-----|------|
| 整體延遲 | P95 < {N}ms | {N}ms | {N}ms | **{N}ms** | {N}ms | {N}ms | ✅/❌ |
| GET /api/{ep} | P95 < {N}ms | {N}ms | {N}ms | **{N}ms** | {N}ms | {N}ms | ✅/❌ |
| POST /api/{ep} | P95 < {N}ms | {N}ms | {N}ms | **{N}ms** | {N}ms | {N}ms | ✅/❌ |

**吞吐量**: 實際達到 {N} RPS（目標 {N} RPS）— {達標/未達標}
**錯誤率**: {X}%（目標 < 0.1%）— ✅/❌

### 3.2 PERF-SCEN-002：峰值負載

**設定**: {N} VU, 目標 {N} RPS, 持續 {15} min

| 指標 | PBS 目標 | P50 | P95 | P99 | 達標 |
|-----|---------|-----|-----|-----|------|
| 整體延遲 | P95 < {N}ms | {N}ms | **{N}ms** | {N}ms | ✅/❌ |
| 錯誤率 | < 0.5% | — | — | — | ✅/❌ |
| CPU 使用率 | < {80}% | — | — | **{X}%** | ✅/❌ |
| Memory 使用率 | < {85}% | — | — | **{X}%** | ✅/❌ |

### 3.3 PERF-SCEN-003：壓力測試

**設定**: 線性增加至 {N} VU，尋找瓶頸點

| 負載點 | VU 數 | RPS | P95 延遲 | 錯誤率 | 系統狀態 |
|-------|-------|-----|---------|-------|---------|
| 25% | {N} | {N} | {N}ms | {X}% | 正常 |
| 50% | {N} | {N} | {N}ms | {X}% | 正常 |
| 75% | {N} | {N} | {N}ms | {X}% | 警告 |
| 100% | {N} | {N} | {N}ms | {X}% | {狀態} |
| **瓶頸點** | **{N} VU** | **{N} RPS** | **{N}ms** | **{X}%** | **瓶頸識別** |

### 3.4 PERF-SCEN-004：耐久測試（若有執行）

**設定**: {N} VU, 持續 {2} hr

| 時間點 | Memory 使用 | CPU 使用 | GC 頻率 | 連接池使用率 |
|-------|------------|---------|---------|------------|
| 0 min | {N} MB | {X}% | {N}/min | {X}% |
| 30 min | {N} MB | {X}% | {N}/min | {X}% |
| 60 min | {N} MB | {X}% | {N}/min | {X}% |
| 120 min | {N} MB | {X}% | {N}/min | {X}% |
| **趨勢** | **{穩定/增長 {X}%}** | **{穩定}** | **{穩定}** | **{穩定}** |

---

## 4. 資源使用分析

### 4.1 基準資源使用（正常負載）

| 資源 | 平均 | 最大 | PBS 目標 | 達標 |
|-----|------|------|---------|------|
| CPU | {X}% | {X}% | < {60}% | ✅/❌ |
| Memory | {X}% | {X}% | < {70}% | ✅/❌ |
| DB Connections | {N} / {max} | {N} / {max} | < {60}% | ✅/❌ |
| DB Query Time avg | {N}ms | {N}ms | < {N}ms | ✅/❌ |
| Network I/O | {N} MB/s | {N} MB/s | < {80}% 帶寬 | ✅/❌ |

---

## 5. 瓶頸分析

| 瓶頸 ID | 位置 | 類型 | 影響量化 | 根本原因 | 建議優化 |
|--------|------|------|---------|---------|---------|
| BOTTLENECK-001 | {service/function} | DB Query | P95 +{N}ms ({X}%) | N+1 Query | 建立 ADR-{NNN}（Eager Loading） |
| BOTTLENECK-002 | {service/function} | CPU | CPU +{X}% | 未快取計算 | 建立 ADR-{NNN}（結果快取） |
| BOTTLENECK-003 | {service/function} | Memory | {description} | {cause} | 建立 ADR-{NNN} |

---

## 6. 差距分析（對照 PBS）

### 6.1 未達標項目清單

| SLO ID | 指標 | PBS 目標 | 實際值 | 差距 | 優先級 | 對應 ADR |
|--------|------|---------|--------|------|-------|---------|
| SLO-LAT-001 | GET /api P95 | < {N}ms | {N}ms | +{N}ms | P1 | ADR-{NNN}（待建立）|

### 6.2 建議優化 ADR 清單

| ADR ID | 優化方向 | 預期改善量 | 實施複雜度 | 負責人 |
|--------|---------|----------|----------|-------|
| ADR-{NNN} | {optimization} | -{N}ms P95 | Medium | {owner} |

---

## 7. 下一步行動

| 行動 | 優先級 | 負責人 | 截止日期 |
|------|-------|-------|---------|
| 建立 PERFORMANCE-OPTIMIZATION-ADR-{NNN}.md | P1 | {name} | {date} |
| {action} | P2 | {name} | {date} |

**結論**: {是否可以發布，若不可發布說明原因}

---

> **參考文件**:
> - PBS: PERFORMANCE-BASELINE-SPEC-{project}.md
> - 優化 ADR: docs/02_architecture/adr/PERFORMANCE-OPTIMIZATION-ADR-{NNN}.md
> - 監控規格: MONITORING-ALERT-SPEC-{project}.md
