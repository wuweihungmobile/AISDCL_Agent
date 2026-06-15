# FSM Variant — Migration

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Migration（系統 / 資料 / 雲遷移）
**對應 Enhancement**: [scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md](../../../scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md)

## extra_states

```yaml
CURRENT_INVENTORY:
  type: workstate
  description: "現行系統資產清冊（服務 / 資料 / 依賴）"
  output_docs:
    - "docs/08_deployment/ASSET-INVENTORY-{System}.md"

MCM_DRAFT:
  type: workstate
  description: "Migration Contract Map 草擬（來源 → 目標欄位映射）"
  output_docs:
    - "docs/02_architecture/migration/MIGRATION-CONTRACT-MAP-{System}.md"

MCM_FREEZE:
  type: gatekeep
  description: "SCG-Migration-1：MCM 凍結閘"
  retry_limit: 2
  on_retry_exceeded: ESCALATION

CUTOVER_READY:
  type: milestone
  description: "切換前檢查（dual-run / rollback plan / cutover runbook）"
  checks:
    - "contract tests 100% PASS（雙寫驗證）"
    - "Rollback runbook 已演練"
    - "Cutover runbook 已通過桌面演練"

ROLLBACK_READY:
  type: milestone
  description: "Rollback 機制已測通（不用等到切換當天）"
  required_before: CUTOVER_READY
```

## extra_transitions

```yaml
- AGENT_LOAD → CURRENT_INVENTORY
- CURRENT_INVENTORY → MCM_DRAFT
- MCM_DRAFT → MCM_FREEZE
- MCM_FREEZE（PASS） → SPEC_DRAFTING
- SPEC_FROZEN → IMPLEMENTATION
- PR_REVIEW（PASS） → ROLLBACK_READY
- ROLLBACK_READY → CUTOVER_READY
- CUTOVER_READY → RTM_VERIFY
- 任意狀態（Rollback 失敗） → ESCALATION   # 切換期間的緊急通道
```

## retry_budget_override

```yaml
SCG_VALIDATION:
  retry_limit: 2    # MCM 設計必須前期收斂
RTM_VERIFY:
  retry_limit: 1    # Migration 進入發布前，不容忍追溯瑕疵
```

## scg_extensions

- **SCG-Migration-1**：MCM_FREEZE 閘（contract tests from MCM 全部 PASS）
- **SCG-Migration-2**：CUTOVER_READY 閘（dual-run + rollback 演練完成）
