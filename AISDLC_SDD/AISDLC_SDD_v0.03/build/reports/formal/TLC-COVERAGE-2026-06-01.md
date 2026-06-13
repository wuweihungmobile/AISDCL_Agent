# TLC Reachable State Coverage — 2026-06-01 (Phase I / 6 新狀態 + liveness 健全化)

**對應 Tag**: `phase-i-tsg` → `phase-i-fleet`
**對應規則**: CLAUDE.md §9.18.3 / §9.21.7 / §9.21.13
**前次驗證**: TLC-COVERAGE-2026-04-27.md（27/27 = 100%，phase-g-final）
**本次驗證**: **36/36 = 100%**（Phase H +3、Phase I +6 後重驗；實測 -dump 可達狀態值 = 36）

> 補登原因：Phase H（30 態）與 Phase I（36 態）新增狀態後未同步產出 TLC-COVERAGE 報告，違反 §9.18.3「新增 FSM state 必須同步重跑 TLC 並更新 TLC-COVERAGE 報告」。本報告補齊並一併記錄 FLEET liveness 健全化修正。

---

## 1. SDD_FSM TLC 執行結果（safety + liveness）

| 指標 | 值 |
|------|----|
| distinct states（tuple `<<state,retry,recovery,compact,hub>>`） | 720 |
| generated states | ≈951 |
| max depth | ≈13 |
| MAX_RETRY / MAX_RECOVERY | 5 / 3 |
| Exit code | 0（PASS，`Model checking completed. No error has been found.`） |

> **數字註記**：generated / max depth 等遍歷統計依執行環境（tla2tools.jar 版本、狀態探索順序、JVM）略有差異（本次 Java 21 實機重跑：distinct=720、generated≈951、depth≈13）；distinct states=720 與 **reachable 36/36=100%、全 invariant + EventuallyTerminal + ObservationsTransient PASS** 之結論不變。

## 2. Invariant + Liveness 驗證

| 性質 | 類型 | 狀態 |
|------|------|------|
| TypeOK | safety | ✅ PASS |
| RetryBounded | safety | ✅ PASS（retry ≤ MAX_RETRY） |
| RecoveryBounded | safety | ✅ PASS（recovery ≤ MAX_RECOVERY） |
| NotInBothSets | safety（結構性互斥，constant-level） | ✅ PASS（ObservationStates ∩ Terminals = ∅） |
| EventuallyTerminal | liveness | ✅ PASS（compact/hub 有界計數器消除 wildcard 假 2-cycle，§9.21.7） |
| ObservationsTransient | liveness | ✅ PASS（觀測態必離開） |

## 3. State Set 對照（36 states，實測 -dump 全部可達）

### HappyStates (18)
INIT, SCENARIO_DETECT, AGENT_LOAD, SPEC_DRAFTING, SCG_VALIDATION, HUMAN_PENDING,
SPEC_REGRESSION_CHECK, REMINDER, SPEC_FROZEN, IMPLEMENTATION, PR_REVIEW, SPEC_AUDIT,
RTM_VERIFY, RELEASE_READY, TEST_CONTRACT_NEGOTIATED(H), EXECUTION_EVALUATION(H),
**SANDBOX_HARDENING_GATE(I/ACT-061)**, **BACKLOG_PRIORITIZED(I/ACT-068)**

### ObservationStates (11)
PRODUCTION_SIGNAL, LEARNING_COMMIT, HUB_SYNC, TRAJECTORY_PREDICTED, AUTO_RECOVERY_ATTEMPT,
DRIFT_OBSERVATION, SCAFFOLD_GC(H), **EVALUATOR_AUDIT(I/ACT-063)**, **MONITOR_VIOLATION(I/ACT-064)**,
**MEMORY_CONSOLIDATION(I/ACT-066)**, **PRODUCTION_BEHAVIORAL_SIGNAL(I/ACT-067)**

### EmergencyStates (4)
ESCALATION, TOKEN_BUDGET_CRITICAL, AUTO_COMPACT_PENDING, RESUME_VERIFICATION

### Terminals (3)
RELEASE, TERMINATED, ESCALATION_FINAL

**Reachable coverage**: 36/36 = **100%**（≥ 95% 守門通過，per §9.18.3）

## 4. FLEET_FSM TLC 執行結果（Phase I M5 / ACT-072，parametric）

| 性質 | cfg | SYMMETRY | 結果 |
|------|-----|----------|------|
| TypeOK / LockMutex / NoPartialHold | `FLEET_FSM.cfg` | ✅ 啟用（safety 健全） | ✅ PASS |
| AllEventuallyDone（liveness） | `FLEET_FSM_LIVENESS.cfg` | ❌ 停用 | ✅ PASS |

> **🔧 本次修正（liveness 健全化）**：原 `FLEET_FSM.cfg` 在 SYMMETRY 啟用下同時檢查 liveness 屬性 `AllEventuallyDone`，TLC 官方警告此為 **unsound**（"Declaring symmetry during liveness checking is dangerous — might miss violations"）。已將 liveness 拆至獨立的 `FLEET_FSM_LIVENESS.cfg`（無 SYMMETRY）窮舉驗證（12 distinct states，無 symmetry 縮減），結果仍 PASS → liveness 證明現為健全。`run_tlc.sh` Step 5 改為 5a(safety+symmetry) + 5b(liveness 無 symmetry) 兩段，皆須通過。

## 5. 其他驗收憑證（交叉佐證）

- pytest：483 passed
- chaos（含 FLAKY_EVAL）：bounded_ratio = 1.0（30 輪抽驗 100%；藍圖 100 輪基準 100%）
- 三源一致性（MD ↔ Python ↔ .tla）：test_md_python_sync.py 5 passed

---

**驗證時間**: 2026-06-01（UTC+8 實測）
**TLC Version**: tla2tools.jar（lib/，CI 動態下載）
**Java Runtime**: OpenJDK 21.0.11
