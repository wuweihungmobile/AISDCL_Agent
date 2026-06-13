# SDD Performance CI/CD Pipeline 規格
# SDD Performance Scenario CI/CD Specification

**版本**: v1.0
**建立日期**: 2026-04-13
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: `AISDLC_SDD_v0.01/cicd/`
**Spec Gate**: 🔷 SCG-6 Release Gate
**對應 Phase**: Phase 05 — 情境九：Performance（效能調校）

---

## 🎯 目的

定義 SDD Performance 情境的 CI/CD Pipeline 規格，強制實現「SLO 先行」原則：
- Performance Baseline Spec（PBS）先於 Benchmark 執行
- 每次部署自動執行 Benchmark 並對照 PBS
- SLO 未達標自動阻擋部署
- 效能退化即時通知（Advanced Notify）

---

## 🏗️ Pipeline 架構

```
┌─────────────────────────────────────────────────────────┐
│            SDD Performance CI/CD Pipeline                │
├─────────────────────────────────────────────────────────┤
│  L0: DocLint + PBS-Validate（SLO 規格完整性）            │
│   ↓                                                      │
│  L1: Unit Test                                           │
│   ↓                                                      │
│  Container: 容器化驗證                                   │
│   ↓                                                      │
│  🔴 Benchmark（SDD 強化）:                               │
│    ├── 執行 Baseline Benchmark（對照 PBS）               │
│    ├── 正常/峰值/壓力負載測試                            │
│    ├── SLO 自動判斷通過/失敗                             │
│    └── SLO 未達標自動阻擋部署                            │
│   ↓                                                      │
│  🔔 Notify: Advanced（效能退化即時通知）                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 各階段詳細規格

### L0: DocLint + PBS-Validate（SLO 規格完整性）

**觸發條件**：每次 PR / Merge

**驗證規則**：

```yaml
pbs_validate_rules:
  performance_baseline_spec:
    required: true
    path: "docs/03_testing/PBS-*.md"
    checks:
      - "系統 SLO 已定義"
      - "Latency P50/P95/P99 目標值存在"
      - "Throughput 目標已設定"
      - "Error Rate 上限已定義"
      - "測試場景規格存在（Normal/Peak/Stress）"
      - "Pass/Fail 標準量化（非模糊描述）"
      - "效能測試框架 ADR 已存在"

  slo_completeness:
    required_fields:
      - "availability_target（如 99.9%）"
      - "latency_p50_ms"
      - "latency_p95_ms"
      - "latency_p99_ms"
      - "throughput_rps"
      - "error_rate_percent"

fail_policy:
  - "PBS 不存在 → 阻擋 PR（SCG-6 Gate）"
  - "SLO 欄位不完整 → 阻擋 PR"
  - "缺少效能測試框架 ADR → 警告"
```

---

### L1: Unit Test

```yaml
unit_test_spec:
  standard: "與 SDD_TESTING_CICD.md 保持一致"
  additional:
    - "效能敏感函式的單元 Benchmark 測試（microbenchmark）"
    - "確保關鍵演算法時間複雜度在可接受範圍"
```

---

### Container: 容器化驗證

```yaml
container_spec:
  build_validation:
    - "映像建置成功"
    - "Image Size 未超出閾值（Base: {max_size_mb} MB）"
    - "Container Security Scan 通過（無 Critical CVE）"
  
  startup_time:
    max_seconds: 30
    health_check_endpoint: "/health"
```

---

### 🔴 Benchmark（SDD 核心 — SLO 自動驗證）

```yaml
benchmark_spec:
  trigger: "每次 Merge to main / Release candidate 部署前"
  environment: "Staging（類生產配置）"
  based_on: "docs/03_testing/PBS-{system}-{date}.md"

  test_scenarios:
    normal_load:
      description: "正常業務負載"
      concurrent_users: "{from_PBS}"
      duration: "10 minutes"
      warmup: "2 minutes"
      
    peak_load:
      description: "峰值負載（業務高峰期）"
      concurrent_users: "{from_PBS}"
      duration: "5 minutes"
      ramp_up: "2 minutes"
      
    stress_load:
      description: "壓力測試（超出設計上限）"
      concurrent_users: "{from_PBS}"
      duration: "3 minutes"
      purpose: "識別系統崩潰點（非 Gate 標準）"

  slo_validation:
    description: "自動對照 PBS 判斷通過/失敗"
    thresholds:
      latency_p50: "< {PBS.latency_p50_ms} ms"
      latency_p95: "< {PBS.latency_p95_ms} ms"
      latency_p99: "< {PBS.latency_p99_ms} ms"
      throughput: "> {PBS.throughput_rps} RPS"
      error_rate: "< {PBS.error_rate_percent}%"
      
  pass_criteria:
    - "所有 SLO 在峰值負載下仍達標"
    
  fail_actions:
    - "阻擋部署（不允許 SLO 未達標版本上線）"
    - "自動建立效能 Bug Issue"
    - "觸發 Advanced 通知"
    
  regression_detection:
    enabled: true
    description: "與上一個成功版本比較"
    threshold: "P95 Latency 退化 > 20% → 警告 + 通知"
    
  report_generation:
    output: "build/reports/Benchmark-{version}-{date}.md"
    compare_with_pbs: true
    include_graphs: true
```

---

### 🔔 Notify: Advanced（效能退化即時通知）

```yaml
advanced_notifications:
  on_slo_pass:
    channel: "Slack #performance"
    message: |
      ✅ {version} 效能測試通過
      P95: {p95}ms（目標 < {target_p95}ms）
      Throughput: {rps} RPS（目標 > {target_rps}）
      
  on_slo_fail:
    channel: "Slack #performance-alerts"
    message: |
      🔴 SLO 未達標！部署已阻擋
      版本: {version}
      失敗指標: {failed_metrics}
      詳情: {report_url}
    notify_users:
      - "@performance-engineer"
      - "@dev-lead"
      
  on_regression_detected:
    channel: "Slack #performance-alerts"
    message: |
      ⚠️ 效能退化偵測！
      {metric} 退化 {percent}%（{current} → {previous}）
      版本: {version}
    severity: "warning"
    notify_users:
      - "@performance-engineer"
```

---

## 📊 Benchmark 報告格式規格

```markdown
# Benchmark Report — {version} — {date}

## SLO 達標狀況
| 指標 | PBS 目標 | 正常負載 | 峰值負載 | 狀態 |
|------|---------|---------|---------|------|
| Latency P50 | < Xms | Yms | Zms | ✅/❌ |
| Latency P95 | < Xms | Yms | Zms | ✅/❌ |
| Latency P99 | < Xms | Yms | Zms | ✅/❌ |
| Throughput | > X RPS | Y RPS | Z RPS | ✅/❌ |
| Error Rate | < X% | Y% | Z% | ✅/❌ |

## 與上版本比較
| 指標 | 上版本 | 本版本 | 變化 |

## 部署決策
□ 通過（所有 SLO 達標）/ □ 失敗（阻擋部署）
```

---

## 🔗 相關文件

| 文件 | 路徑 |
|------|------|
| Performance Baseline Spec 模板 | `docs_template/sdd/testing/PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` |
| Baseline Performance Report 模板 | `docs_template/sdd/testing/BASELINE-PERFORMANCE-REPORT-TEMPLATE.md` |
| Performance Optimization ADR 模板 | `docs_template/sdd/adr/PERFORMANCE-OPTIMIZATION-ADR-TEMPLATE.md` |
| SDD CI/CD 基礎層 | `cicd/SDD_CICD_BASE_LAYER.md` |

---

> **SDD 原則**: PBS 文件是 Benchmark CI 步驟的輸入規格。Benchmark 不是「看看跑多快」，而是「對照 SLO 規格驗收效能」。SLO 未達標即視為功能缺陷，不允許上線。
