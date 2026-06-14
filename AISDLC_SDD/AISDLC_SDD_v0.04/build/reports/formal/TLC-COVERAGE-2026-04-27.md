# TLC Reachable State Coverage — 2026-04-27 (Phase G Final / DRIFT_OBSERVATION 加入後重驗)

**對應 Tag**: `phase-g-final`
**對應規則**: CLAUDE.md §9.18.3
**前次驗證**: TLC-COVERAGE-2026-04-26.md（26/26 = 100%，phase-g-mvp）
**本次驗證**: 27/27 = **100%**（M4 加入 DRIFT_OBSERVATION 後）

---

## 1. TLC 執行結果

| 指標 | 值 |
|------|----|
| distinct states | 607 |
| generated states | 3285 |
| max depth | 29 |
| MAX_RETRY | 5 |
| MAX_RECOVERY | 3 |
| Exit code | 0（PASS） |

## 2. Invariant 驗證

| Invariant | 狀態 |
|-----------|------|
| TypeOK | ✅ PASS（state ∈ States, retry ∈ 0..5, recovery ∈ 0..3） |
| RetryBounded | ✅ PASS（retry <= MAX_RETRY） |
| RecoveryBounded | ✅ PASS（recovery <= MAX_RECOVERY） |
| NotInBothSets | ✅ PASS（ObservationStates ∩ Terminals = ∅） |

## 3. State Set 對照（27 states）

### HappyStates (14)
INIT, SCENARIO_DETECT, AGENT_LOAD, SPEC_DRAFTING, SCG_VALIDATION,
HUMAN_PENDING, SPEC_REGRESSION_CHECK, REMINDER, SPEC_FROZEN,
IMPLEMENTATION, PR_REVIEW, SPEC_AUDIT, RTM_VERIFY, RELEASE_READY

### ObservationStates (6 — Final 後加 1)
PRODUCTION_SIGNAL, LEARNING_COMMIT, HUB_SYNC, TRAJECTORY_PREDICTED,
AUTO_RECOVERY_ATTEMPT, **DRIFT_OBSERVATION** ⬅ 新加入（Phase G M4 / ACT-040）

### EmergencyStates (4)
ESCALATION, TOKEN_BUDGET_CRITICAL, AUTO_COMPACT_PENDING, RESUME_VERIFICATION

### Terminals (3)
RELEASE, TERMINATED, ESCALATION_FINAL

**Reachable coverage**: 27/27 = **100%**（≥ 95% 守門通過，per Rule 9.18.3）

## 4. DRIFT_OBSERVATION 轉換覆蓋

| Transition | TLA+ 名稱 | 對應 .py |
|-----------|----------|---------|
| EnterDrift（從 7 個 retry-prone gate） | T_EnterDrift | `enter_drift_observation()` |
| Continue（回 resume_state） | T_DriftContinue | `exit_drift_observation("continue")` |
| SwitchAudit（連續 drift 升 SPEC_AUDIT） | T_DriftSwitchAudit | `exit_drift_observation("switch_to_audit")` |

## 5. Phase G Final 收官憑證

- Chaos 100 輪 + TLC 形式化雙重驗證
- 雙源一致性（_HAPPY_PATH ↔ SDD_FSM.tla）測試 PASS（test_tla_python_sync.py 3 tests）
- 觀測狀態 invariant `NotInBothSets` 維持

---

**驗證時間**: 2026-04-27（UTC）
**TLC Version**: tla2tools.jar v1.8.0
**Java Runtime**: OpenJDK 21+
