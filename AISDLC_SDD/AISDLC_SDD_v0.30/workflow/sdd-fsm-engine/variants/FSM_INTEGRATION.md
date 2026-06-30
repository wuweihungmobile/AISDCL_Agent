# FSM Variant — Integration

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Integration（跨系統 API / 事件整合）
**對應 Enhancement**: [scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md](../../../scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md)

## extra_states

```yaml
CONSUMER_CONTRACT_DRAFT:
  type: workstate
  description: "Consumer-Driven Contract 草擬（CDC Spec + Pact/OpenAPI）"
  output_docs:
    - "docs/02_architecture/api/CONSUMER-CONTRACT-{Integration}.md"

PROVIDER_AGREEMENT:
  type: gatekeep
  description: "SCG-Integration-1：Provider 確認接受合約"
  retry_limit: 2
  required_artifacts:
    - "Provider sign-off record（email / ticket link）"
    - "OpenAPI 3.1 spec 雙方凍結"
  on_retry_exceeded: ESCALATION

CONTRACT_TEST_RUN:
  type: gatekeep
  description: "Consumer + Provider 雙邊 contract test"
  retry_limit: 3
  checks:
    - "Pact broker / OpenAPI validator 全部 PASS"
    - "ACL（防腐層）測試通過"
    - "Chaos contract 測試（provider timeout / 5xx）通過"
```

## extra_transitions

```yaml
- AGENT_LOAD → CONSUMER_CONTRACT_DRAFT
- CONSUMER_CONTRACT_DRAFT → PROVIDER_AGREEMENT
- PROVIDER_AGREEMENT（PASS） → SPEC_DRAFTING
- PR_REVIEW（PASS） → CONTRACT_TEST_RUN
- CONTRACT_TEST_RUN（PASS） → RTM_VERIFY
- CONTRACT_TEST_RUN（FAIL, retry < 3） → IMPLEMENTATION
- CONTRACT_TEST_RUN（FAIL, retry ≥ 3） → ESCALATION
```

## retry_budget_override

```yaml
PR_REVIEW:
  retry_limit: 3    # Contract 偏移通常是設計面問題，收緊上限
```

## scg_extensions

- **SCG-Integration-1**：PROVIDER_AGREEMENT 閘（必要 sign-off）
- **SCG-Integration-2**：CONTRACT_TEST_RUN 閘（含 chaos 場景）
