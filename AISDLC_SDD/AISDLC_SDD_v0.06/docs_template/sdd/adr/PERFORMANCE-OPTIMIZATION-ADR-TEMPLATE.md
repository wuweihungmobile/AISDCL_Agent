# ADR-{NNN}: 效能優化決策記錄
# Performance Optimization Architecture Decision Record — Template
# Phase 05 — Performance 情境 SDD 強化

**狀態**: □ Proposed / □ Accepted / □ Implemented / □ Verified
**決策日期**: {YYYY-MM-DD}
**實施日期**: {YYYY-MM-DD}
**驗證日期**: {YYYY-MM-DD}
**負責人**: {Performance Engineer / Dev-Senior}

> **SDD 原則**: 每個效能優化措施必須有量化 ADR，包含預期改善量和對應 SLO 指標。

---

## 背景（Context）

### 觸發原因

| 瓶頸指標 | 當前值 | PBS 目標值 | 差距 |
|---------|-------|----------|------|
| {metric} | {actual} | {target} | -{N}% |
| {metric} | {actual} | {target} | -{N}% |

**來源**: Baseline Benchmark #{build_number}（{date}）
**根本原因分析**:

```
瓶頸識別：
1. {bottleneck_1}：影響 {X}% 的 P95 延遲
2. {bottleneck_2}：影響 {X}% 的吞吐量
3. {bottleneck_3}：CPU 使用率超出 SLO-RES-001
```

---

## 優化選項分析

### 選項 1: {優化方案名稱}

**描述**: {方案描述}

| 評估維度 | 說明 |
|---------|------|
| 預期改善量 | P95 延遲降低 {X}ms（{Y}%），吞吐量提升 {Z}% |
| 對應 SLO | SLO-LAT-001, SLO-THRU-001 |
| 實施複雜度 | Low / Medium / High |
| 實施風險 | {risk description} |
| 回滾難度 | Low / Medium / High |
| 預估工時 | {N} 人天 |

**技術細節**:
```
{implementation approach}
```

**驗證方法**: 執行 Benchmark PERF-SCEN-001, PERF-SCEN-002，對照 PBS 目標

---

### 選項 2: {優化方案名稱}

**描述**: {方案描述}

| 評估維度 | 說明 |
|---------|------|
| 預期改善量 | {quantified improvement} |
| 對應 SLO | {SLO IDs} |
| 實施複雜度 | Low / Medium / High |
| 實施風險 | {risk} |
| 回滾難度 | Low / Medium / High |
| 預估工時 | {N} 人天 |

---

### 選項 3: {優化方案名稱}

**描述**: {方案描述}

| 評估維度 | 說明 |
|---------|------|
| 預期改善量 | {quantified improvement} |
| 對應 SLO | {SLO IDs} |
| 實施複雜度 | Low / Medium / High |
| 實施風險 | {risk} |

---

## 選項比較矩陣

| 選項 | 改善量 | 複雜度 | 風險 | 工時 | 推薦 |
|------|-------|-------|------|------|------|
| 選項 1 | +{X}% | Low | Low | {N}d | ✅ |
| 選項 2 | +{X}% | Medium | Medium | {N}d | |
| 選項 3 | +{X}% | High | High | {N}d | |

---

## 決策（Decision）

**選定**: 選項 {N}

**決策理由**:
1. {reason 1}
2. {reason 2}
3. {reason 3}

---

## 實施規格（Implementation Spec）

### 實施步驟

| 步驟 | 描述 | 負責人 | 預計完成 |
|------|------|-------|---------|
| 1 | {step description} | {owner} | {date} |
| 2 | {step description} | {owner} | {date} |
| 3 | {step description} | {owner} | {date} |

### 配置變更

```yaml
# Before
{config_before}

# After  
{config_after}
```

### 驗收標準（Quantified）

| 指標 | 優化前（Baseline） | 預期優化後 | 實際優化後 | 達標 |
|-----|------------------|----------|----------|------|
| P95 Latency | {before}ms | < {target}ms | {actual}ms | □ |
| P99 Latency | {before}ms | < {target}ms | {actual}ms | □ |
| Throughput | {before} RPS | > {target} RPS | {actual} RPS | □ |
| Error Rate | {before}% | < {target}% | {actual}% | □ |
| CPU Usage | {before}% | < {target}% | {actual}% | □ |

---

## 風險與緩解措施

| 風險 | 可能性 | 影響 | 緩解措施 | 回滾計畫 |
|------|-------|------|---------|---------|
| {risk_1} | Low/Med/High | Low/Med/High | {mitigation} | {rollback} |
| {risk_2} | Low/Med/High | Low/Med/High | {mitigation} | {rollback} |

---

## 後果（Consequences）

### 正面後果
- P95 延遲預期降低 {X}%，達到 SLO-LAT-001 目標
- 吞吐量預期提升 {X}%，支持峰值負載場景

### 負面後果 / 技術債
- {tradeoff}: 可能影響 {area}
- 需定期監控 {metric} 確保無副作用

---

## 驗證記錄

| 驗證日期 | Build # | Benchmark 結果 | SLO 達標 | 備註 |
|---------|---------|--------------|---------|------|
| {date} | #{N} | {summary} | □ 全部達標 / □ 部分未達 | {note} |

**最終狀態**: □ SLO 全部達標，ADR 狀態更新為 Verified
          □ 部分 SLO 未達，啟動下一輪優化

---

## 版本記錄

| 日期 | 版本 | 變更 | 作者 |
|------|------|------|------|
| {date} | v1.0 | 初始決策 | {author} |
| {date} | v1.1 | 驗證結果更新 | {author} |
