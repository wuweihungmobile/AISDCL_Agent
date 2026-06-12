# TLC Coverage Report — Phase J（2026-06-01）

對應：ACT-080 / Rule 9.18.1~9.18.4 / 9.22.7
模型：`tools/fsm_runtime/formal/SDD_FSM.tla` + `SDD_FSM.cfg`（small-model bound）

## 結果

| 項目 | 數值 |
|------|------|
| TLC 退出碼 | 0 ✅ |
| distinct states（tuples） | 747（Phase I：583 → Phase J：747） |
| generated states | 929 |
| depth | 15 |
| FSM 狀態總數 | **39**（Phase I 36 + Phase J 3） |
| reachable coverage | **39/39 = 100%** |

## Phase J 新增狀態（3）

| 狀態 | 集合 | 入口（reachable 依據） |
|------|------|----------------------|
| ADVERSARIAL_EVALUATION | HappyStates（gatekeep） | EXECUTION_EVALUATION（reachable）→ T_ExecEvalToAdversarial |
| CAPABILITY_BENCHMARK | ObservationStates | SCAFFOLD_GC / MEMORY_CONSOLIDATION（reachable）→ T_EnterCapBench |
| SPEC_PATCH_PROPOSAL | ObservationStates | SPEC_AUDIT / ESCALATION（reachable）→ T_EnterSpecPatch |

集合計數：HappyStates 19 + ObservationStates 13 + EmergencyStates 4 + Terminals 3 = **39**

## Invariant / Liveness（全 PASS）

- TypeOK ✅ / RetryBounded ✅ / RecoveryBounded ✅ / NotInBothSets ✅
- **EventuallyTerminal ✅**（ADVERSARIAL_EVALUATION 對抗閘有界 + SF_vars(T_AdversarialPass) 破「對抗↔impl」環；其餘四計數器 retry/recovery/compact/hub 皆有界 ⇒ 必達 terminal）
- **ObservationsTransient ✅**（CAPABILITY_BENCHMARK / SPEC_PATCH_PROPOSAL 無 self-loop，WF 保證離開）

## FLEET_FSM（不回歸）

- 5a safety + symmetry：LockMutex ✅ / NoPartialHold ✅
- 5b liveness（無 symmetry）：AllEventuallyDone ✅

## 驗收憑證彙總（Phase J）

- pytest：**575 passed**（Phase I 485 + Phase J +90）
- chaos 100 輪：bounded_ratio = **1.0**、avg tokens = **1996**（< 25K × 80% = 20K）
- 三源同步（_HAPPY_PATH ↔ SDD_FSM.tla ↔ SDD_FSM_ENGINE.md）：test_tla_python_sync + test_md_python_sync 全綠
