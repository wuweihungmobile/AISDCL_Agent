# FSM Variant — Refactoring

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Refactoring（行為不變的結構調整）
**對應 Enhancement**: [scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md](../../../scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md)

## extra_states

```yaml
INVARIANT_EXTRACTION:
  type: workstate
  description: "從 AS-IS 行為萃取 Business Invariants（INV-XXX）"
  output_docs:
    - "docs/01_requirements/INVARIANT-SPEC-{System}.md"
    - "docs/03_testing/contracts/INVARIANT-TEST-CONTRACT-{System}.md"

BEFORE_SNAPSHOT:
  type: milestone
  description: "重構前的行為快照（所有 Invariant Test 綠燈）"
  on_enter:
    - "執行全量 invariant test，結果存 build/reports/refactor/BEFORE-{date}.xml"
    - "記錄效能 baseline（p50/p95）"

AFTER_VALIDATION:
  type: gatekeep
  description: "重構後行為不變性驗證（SCG-Refactor）"
  retry_limit: 3
  on_retry_exceeded: ESCALATION
  checks:
    - "全部 Invariant Tests PASS"
    - "Mutation Score 不低於 BEFORE_SNAPSHOT"
    - "效能 baseline 偏差 ≤ 允許閾值"
```

## extra_transitions

```yaml
- AGENT_LOAD → INVARIANT_EXTRACTION
- INVARIANT_EXTRACTION → SPEC_DRAFTING   # 銜接主 FSM（Refactor Plan 當作 Spec）
- SPEC_FROZEN → BEFORE_SNAPSHOT
- BEFORE_SNAPSHOT → IMPLEMENTATION
- PR_REVIEW（PASS） → AFTER_VALIDATION   # 取代主 FSM 的直接 RTM_VERIFY
- AFTER_VALIDATION（PASS） → RTM_VERIFY
- AFTER_VALIDATION（FAIL, retry < 3） → IMPLEMENTATION
- AFTER_VALIDATION（FAIL, retry ≥ 3） → ESCALATION
```

## retry_budget_override

```yaml
PR_REVIEW:
  retry_limit: 3        # Refactor 不應反覆偏離 invariants，收緊上限
IMPLEMENTATION:
  max_test_fail_without_spec_change: 3   # 任何 invariant 偏離即是告警
```

## scg_extensions

- **SCG-Refactor**（新）：AFTER_VALIDATION 通過的必要條件
  - Invariant Test 100% PASS
  - Mutation Score ≥ BEFORE 基線
  - Strangler Fig 分支覆蓋率達 100%（若採用）
