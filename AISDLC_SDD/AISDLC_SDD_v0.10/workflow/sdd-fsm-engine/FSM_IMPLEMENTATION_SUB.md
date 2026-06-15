# IMPLEMENTATION 子 FSM（Phase D / ACT-017）

**父狀態**: `IMPLEMENTATION`（見 [SDD_FSM_ENGINE.md](SDD_FSM_ENGINE.md)）
**目的**: 把原本「黑盒」的 IMPLEMENTATION 展開為可觀測、可治理的子狀態機。
**執行者**: sdd-orchestrator（主）+ dev-senior / qa-tester / devops-engineer（派遣）

父狀態的 `implementation_budget` 適用於**整個子 FSM 的總體消耗**，不因子狀態切換而重置。

## 🔁 子狀態定義

```yaml
sub_states:
  CODE_GENERATING:
    type: workstate
    description: "首次依照 Spec 產出實作（dev-senior）"
    entry_from: "父 FSM SPEC_FROZEN → IMPLEMENTATION"
    on_exit: "COMPILE_LOOP"

  COMPILE_LOOP:
    type: gatekeep
    description: "編譯 → 失敗 → 修正"
    retry_counter: "父 implementation_budget.consecutive_compile_fail"
    retry_limit: 3      # = IMPL_MAX_CONSECUTIVE_COMPILE_FAIL
    on_pass: "UNIT_TEST"
    on_retry_exceeded: "父 FSM ESCALATION"
    on_fail_retry: "CODE_GENERATING（以失敗訊息當作 fix prompt）"

  UNIT_TEST:
    type: gatekeep
    description: "執行單元測試"
    on_pass: "INTEGRATION_TEST"
    on_fail: "AUTO_DIAGNOSIS"

  AUTO_DIAGNOSIS:
    type: diagnostic
    description: "呼叫 /test-failure-analyzer → 輸出 TFA 報告"
    branches_by_classification:
      A: "AUTO_FIX_ATTEMPT"
      B: "父 FSM → SPEC_AUDIT（帶 TFA 報告 + SLV-002/005）"
      C: "TEST_PRECONDITION_FIX（派 qa-tester）"
      D: "FLAKY_RERUN（rerun ×3，quorum=2）"

  AUTO_FIX_ATTEMPT:
    type: workstate
    description: "分類 A — 派 sdd-orchestrator → dev-senior 修復"
    retry_counter: "父 implementation_budget.test_fail_without_spec_change"
    retry_limit: 3      # 針對單一 test_id 的 AUTO_FIX_ATTEMPT 次數上限（局部）
    scope:
      per_test: 3       # local：同一 test_id 連續自動修復上限 3 次（達上限 → 退回 AUTO_DIAGNOSIS 重新分類）
      global: 5         # global：父 implementation_budget.test_fail_without_spec_change 累計上限 5 次（達上限 → 父 FSM SPEC_AUDIT）
    on_pass: "UNIT_TEST"
    on_retry_exceeded: "父 FSM ESCALATION"

  TEST_PRECONDITION_FIX:
    type: workstate
    description: "分類 C — qa-tester 檢視 Test Contract / fixture"
    retry_limit: 2
    on_pass: "UNIT_TEST"
    on_retry_exceeded: "父 FSM ESCALATION"

  FLAKY_RERUN:
    type: workstate
    description: "分類 D — 重跑 3 次，取多數結果（quorum 2/3）"
    rerun_policy:
      attempts: 3
      quorum: 2
    on_pass: "UNIT_TEST"
    on_persistent_fail: "派 devops-engineer 排查 CI 環境；仍失敗 → 父 FSM ESCALATION"

  INTEGRATION_TEST:
    type: gatekeep
    description: "執行整合測試"
    on_pass: "READY_FOR_PR"
    on_fail: "AUTO_DIAGNOSIS"     # 二次路由

  READY_FOR_PR:
    type: milestone
    description: "交給父 FSM 進入 PR_REVIEW"
    exit_to_parent: "PR_REVIEW"
```

## 🔄 轉換圖（概念）

```
(parent) SPEC_FROZEN ──► CODE_GENERATING
                              │
                              ▼
                        COMPILE_LOOP ◄───── (retry ≤ 3)
                              │ pass
                              ▼
                          UNIT_TEST ◄─────┐
                          │ fail          │ pass
                          ▼               │
                    AUTO_DIAGNOSIS        │
                     ├─A → AUTO_FIX_ATTEMPT ─► UNIT_TEST
                     ├─B → (parent) SPEC_AUDIT
                     ├─C → TEST_PRECONDITION_FIX ─► UNIT_TEST
                     └─D → FLAKY_RERUN ─► UNIT_TEST
                                          │
                              INTEGRATION_TEST
                              │ fail → AUTO_DIAGNOSIS
                              │ pass
                              ▼
                         READY_FOR_PR ─► (parent) PR_REVIEW
```

## 📊 預算總表

| 計數器 | 歸屬 | Scope | 上限 | 達標後果 |
|--------|------|------|------|---------|
| `consecutive_compile_fail` | 父 FSM | global | 3 | ESCALATION |
| `test_fail_without_spec_change` | 父 FSM | global（整個 IMPLEMENTATION 累計未修 Spec 的測試失敗） | 5 | SPEC_AUDIT（非 ESCALATION） |
| `current_iteration`（COMPILE_LOOP + UNIT_TEST 全計） | 父 FSM | global | 20 | ESCALATION |
| `AUTO_FIX_ATTEMPT.retry` | 子 FSM | per-test（針對單一 test_id 的自動修復次數） | 3 | 回退 AUTO_DIAGNOSIS 重新分類 |
| `FLAKY_RERUN.attempts` | 子 FSM | per-test（針對單一 test_id 的重跑次數） | 3 | quorum 2/3，否則升級 D |

## 🔌 與既有元件的對接

- `tools/fsm_runtime/fsm_runtime.py`：`check_implementation_budget()` 對應父 FSM 預算檢查。
- `.claude/skills/test-failure-analyzer`：AUTO_DIAGNOSIS 的實作者。
- `agent/specialized/sdd-orchestrator-zh.yaml`：AUTO_FIX_ATTEMPT / TEST_PRECONDITION_FIX 的派遣者。
- `.claude/hooks/context_ledger_pre.py`：COMPILE_LOOP / UNIT_TEST 期間的 token 監控。

## 📌 進入條件

父 FSM 必須在 `SPEC_FROZEN` → `IMPLEMENTATION` 後才進入 `CODE_GENERATING`。
任何 `AUTO_DIAGNOSIS` 分類 B 都會離開子 FSM 進入父 FSM 的 `SPEC_AUDIT`。
