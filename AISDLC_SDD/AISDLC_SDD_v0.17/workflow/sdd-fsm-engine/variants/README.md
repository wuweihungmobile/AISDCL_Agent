# Scenario FSM Variants（Phase D / ACT-016）

每個 variant 僅描述 **相對主 FSM（[SDD_FSM_ENGINE.md](../SDD_FSM_ENGINE.md)）的差異**：

1. 新增狀態（extra_states）
2. 新增轉換（extra_transitions）
3. 覆寫 retry budget（retry_budget_override）
4. 新增 SCG Gate 變體（scg_extensions）

**執行時合併規則**：variant 值 **覆蓋** 主 FSM 同名欄位；未出現的保持主 FSM 預設。
`FSMRuntime.bootstrap(scenario="...")` 會先載入主 FSM，再 overlay 對應 variant。

## 對應表

| 場景 | Variant 文件 | 關鍵新增狀態 |
|------|-------------|-------------|
| Brownfield | [FSM_BROWNFIELD.md](FSM_BROWNFIELD.md) | `CODE_ANALYSIS` / `AS_IS_SRD_DRAFTING` / `GAP_ANALYSIS` |
| Refactoring | [FSM_REFACTORING.md](FSM_REFACTORING.md) | `INVARIANT_EXTRACTION` / `BEFORE_SNAPSHOT` / `AFTER_VALIDATION` |
| Migration | [FSM_MIGRATION.md](FSM_MIGRATION.md) | `CURRENT_INVENTORY` / `MCM_FREEZE` / `CUTOVER_READY` / `ROLLBACK_READY` |
| Integration | [FSM_INTEGRATION.md](FSM_INTEGRATION.md) | `CONSUMER_CONTRACT_DRAFT` / `PROVIDER_AGREEMENT` / `CONTRACT_TEST_RUN` |
| Security | [FSM_SECURITY.md](FSM_SECURITY.md) | `STRIDE_MODEL` / `ASSET_INVENTORY` / `PEN_TEST_READY` |
| Performance | [FSM_PERFORMANCE.md](FSM_PERFORMANCE.md) | `BASELINE_CAPTURE` / `PBS_DRAFT` / `PBS_GATE` |

未列的場景（Greenfield / Documentation / DevOps / Testing）直接使用主 FSM，無 variant。
