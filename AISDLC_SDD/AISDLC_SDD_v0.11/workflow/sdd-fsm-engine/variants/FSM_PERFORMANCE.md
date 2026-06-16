# FSM Variant — Performance

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Performance（效能基準規格驅動）
**對應 Enhancement**: [scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md](../../../scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md)

## extra_states

```yaml
BASELINE_CAPTURE:
  type: workstate
  description: "量測當前系統效能基準（AS-IS baseline）"
  output_docs:
    - "docs/04_planning/performance/BASELINE-{System}.md"
  required_metrics:
    - "p50 / p95 / p99 latency"
    - "throughput (RPS)"
    - "resource usage (CPU / RAM / I/O)"

PBS_DRAFT:
  type: workstate
  description: "Performance Baseline Spec 草擬（SLO + 測試方案）"
  output_docs:
    - "docs/04_planning/performance/PBS-{System}.md"

PBS_GATE:
  type: gatekeep
  description: "SCG-Performance：PBS 凍結閘"
  retry_limit: 2
  checks:
    - "每個關鍵路徑均有量化 SLO"
    - "定義冷啟動 / cache miss / degraded 情境的回退值（參考 FPL-001/002）"
    - "壓測腳本可重現 baseline"
  on_retry_exceeded: ESCALATION

PBS_REGRESSION_CHECK:
  type: gatekeep
  description: "PR_REVIEW 通過後的效能回歸比對"
  retry_limit: 3
  checks:
    - "p95 不惡化 > 5%（可調）"
    - "throughput 不惡化 > 10%"
```

## extra_transitions

```yaml
- AGENT_LOAD → BASELINE_CAPTURE
- BASELINE_CAPTURE → PBS_DRAFT
- PBS_DRAFT → PBS_GATE
- PBS_GATE（PASS） → SPEC_DRAFTING
- PR_REVIEW（PASS） → PBS_REGRESSION_CHECK
- PBS_REGRESSION_CHECK（PASS） → RTM_VERIFY
- PBS_REGRESSION_CHECK（FAIL, retry < 3） → IMPLEMENTATION
- PBS_REGRESSION_CHECK（FAIL, retry ≥ 3） → ESCALATION
```

## retry_budget_override

```yaml
PR_REVIEW:
  retry_limit: 3
```

## scg_extensions

- **SCG-Performance**：PBS_GATE（強制在 Benchmark 執行前）
- **PBS_REGRESSION_CHECK**：發布前對比 BASELINE，防止新變更把效能拖下去
- 與 FPL-001/002 連動：Spec 階段即可發現「時序／快取」假設缺口
