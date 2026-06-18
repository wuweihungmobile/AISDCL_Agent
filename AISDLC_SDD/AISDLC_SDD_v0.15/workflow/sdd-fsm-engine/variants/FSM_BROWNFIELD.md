# FSM Variant — Brownfield

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Brownfield（逆向規格工程）
**對應 Enhancement**: [scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md](../../../scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md)

## extra_states

```yaml
CODE_ANALYSIS:
  type: workstate
  description: "靜態掃碼 + 依賴圖 + 熱點識別（code-analyzer）"
  on_enter:
    - "呼叫 /code-analyzer 產出 docs/04_planning/Gap-Analysis-{System}.md 草稿"
  context_checkpoint: true

AS_IS_SRD_DRAFTING:
  type: workstate
  description: "逆向撰寫 AS-IS SRD + As-Is C4"
  includes_slv: true   # 完成前執行 SLV-001/003 檢查
  output_docs:
    - "docs/02_architecture/AS-IS-SRD-{System}.md"
    - "docs/02_architecture/AS-IS-C4-{System}.md"

GAP_ANALYSIS:
  type: gatekeep
  description: "AS-IS vs TO-BE 差異清單凍結閘"
  retry_limit: 2
  on_retry_exceeded: ESCALATION
```

## extra_transitions

```yaml
- AGENT_LOAD → CODE_ANALYSIS
- CODE_ANALYSIS → AS_IS_SRD_DRAFTING
- AS_IS_SRD_DRAFTING → GAP_ANALYSIS
- GAP_ANALYSIS（PASS） → SPEC_DRAFTING   # 銜接主 FSM
- GAP_ANALYSIS（FAIL, retry < 2） → AS_IS_SRD_DRAFTING
- GAP_ANALYSIS（FAIL, retry ≥ 2） → ESCALATION
```

## retry_budget_override

```yaml
SCG_VALIDATION:
  retry_limit: 2        # Brownfield 規格重寫成本高，收緊上限
IMPLEMENTATION:
  max_iterations: 30    # 逐步替換（Strangler Fig）可能需要更多 iteration
```

## scg_extensions

- **SCG-0 前置**：必須同時通過 GAP_ANALYSIS 與 AS-IS Invariants 清單確認
- **新增 gate**：SCG-0.5（Gap Analysis Freeze）
