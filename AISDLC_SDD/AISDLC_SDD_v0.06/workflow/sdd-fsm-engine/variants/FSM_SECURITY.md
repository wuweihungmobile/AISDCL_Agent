# FSM Variant — Security

**基底**: [SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)
**場景**: Security（安全規格驅動）
**對應 Enhancement**: [scenarios/security/SDD_SECURITY_ENHANCEMENT.md](../../../scenarios/security/SDD_SECURITY_ENHANCEMENT.md)

## extra_states

```yaml
ASSET_INVENTORY:
  type: workstate
  description: "資產清冊（資料分級 / trust boundary）"
  output_docs:
    - "docs/06_quality/security/ASSET-INVENTORY-{System}.md"
    - "docs/02_architecture/TRUST-BOUNDARY-MAP-{System}.md"

STRIDE_MODEL:
  type: workstate
  description: "STRIDE 威脅模型建置"
  output_docs:
    - "docs/06_quality/security/STRIDE-{System}.md"
    - "docs/06_quality/security/SAD-{System}.md"     # Security Architecture Document

SECURITY_SCG:
  type: gatekeep
  description: "SCG-Security：威脅模型凍結閘"
  retry_limit: 2
  checks:
    - "每個 STRIDE 類別均有至少一條對抗控制"
    - "Compliance Matrix 涵蓋適用法規（GDPR/SOC2/PCI）"
    - "敏感資料流與 trust boundary 一致"

PEN_TEST_READY:
  type: milestone
  description: "滲透測試就緒（正式發布前必要）"
  checks:
    - "SAST / DAST 全部 PASS"
    - "Pen test scope 凍結"
```

## extra_transitions

```yaml
- AGENT_LOAD → ASSET_INVENTORY
- ASSET_INVENTORY → STRIDE_MODEL
- STRIDE_MODEL → SECURITY_SCG
- SECURITY_SCG（PASS） → SPEC_DRAFTING
- RTM_VERIFY（PASS） → PEN_TEST_READY
- PEN_TEST_READY → RELEASE_READY
```

## retry_budget_override

```yaml
SCG_VALIDATION:
  retry_limit: 2     # 安全 Spec 重試即警訊
```

## scg_extensions

- **SCG-Security**：威脅模型、Compliance Matrix、SAD 同時凍結閘
- 發布前新增 **PEN_TEST_READY** 里程碑（非 SCG，但阻塞 RELEASE_READY → RELEASE）
