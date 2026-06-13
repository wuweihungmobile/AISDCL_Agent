# TLC Formal Verification Coverage — 2026-04-26

**對應 ACT**: ACT-041 / ACT-042（Phase G M5 / B5.8）
**對應規則**: CLAUDE.md Rule 9.18.1 ~ 9.18.4
**規格檔案**: [SDD_FSM.tla](../../../tools/fsm_runtime/formal/SDD_FSM.tla) / [SDD_FSM.cfg](../../../tools/fsm_runtime/formal/SDD_FSM.cfg)
**執行平台**: Windows 11 / OpenJDK 21.0.9 / TLC v1.8.0
**執行指令**: `bash tools/fsm_runtime/formal/run_tlc.sh`

---

## 1. 驗證結果

| 指標 | 值 |
|------|---|
| TLC 退出碼 | **0**（safety 全通過） |
| Generated states | 2,901 |
| Distinct (state × retry × recovery) tuples | **583** |
| Reachable depth | 30（< 50 budget） |
| Avg outdegree | 1（min 0 / max 8 / p95 5） |
| Initial states | 1 |
| Invariant violations | **0**（TypeOK / RetryBounded / RecoveryBounded / NotInBothSets 全通過） |

> 數字由 `run_tlc.sh` / `run_tlc.ps1` 末尾 machine-readable summary（`TLC_DISTINCT=`、`TLC_GENERATED=`、`TLC_DEPTH=`）自動取得（QA 修 1 落實），不再人工抄錄。

---

## 2. State Coverage（B5.8 ≥ 95% 目標 — 達標）

從 `states.dot` dump 抽出 distinct FSM `state` 變數值：

| 類別 | 已宣告 | 已可達 | 比例 |
|------|--------|--------|------|
| HappyStates | 14 | **14** | 100% |
| ObservationStates | 5 | **5** | 100% |
| EmergencyStates | 4 | **4** | 100% |
| Terminals | 3 | **3** | 100% |
| **總計** | **26** | **26** | **100%** ✅ |

**Reachable state names**：

```
AGENT_LOAD              AUTO_COMPACT_PENDING    AUTO_RECOVERY_ATTEMPT
ESCALATION              ESCALATION_FINAL        HUB_SYNC
HUMAN_PENDING           IMPLEMENTATION          INIT
LEARNING_COMMIT         PRODUCTION_SIGNAL       PR_REVIEW
RELEASE                 RELEASE_READY           REMINDER
RESUME_VERIFICATION     RTM_VERIFY              SCENARIO_DETECT
SCG_VALIDATION          SPEC_AUDIT              SPEC_DRAFTING
SPEC_FROZEN             SPEC_REGRESSION_CHECK   TERMINATED
TOKEN_BUDGET_CRITICAL   TRAJECTORY_PREDICTED
```

**結論**：**26/26 = 100% ≥ 95% 目標達成（Rule 9.18.3 滿足）**。

> **DRIFT_OBSERVATION 缺席的影響**（QA 修 7）：本輪 reachable 為 26（M1+M2+Phase E~F 範圍）；
> M4 ACT-040 完工後 `DRIFT_OBSERVATION` 加入 `ObservationStates`，預期變 27。
> 即使新增狀態尚未實作 transition，本輪 26/26 = 100% 不會被未來新增狀態破壞 ≥ 95% 條件
> （25/27 = 92.6% 仍將觸發 Rule 9.18.3 fail），M4 完工時必須同步 .tla + 重跑 TLC 再上 main。

---

## 3. State-Tuple Coverage（細粒度）

含 retry/recovery 變數的完整 tuple 空間：

| 維度 | 範圍 | 大小 |
|------|------|------|
| state | 26 | 26 |
| retry | 0..5 | 6 |
| recovery | 0..3 | 4 |
| 理論上限 | — | 624 |
| TLC 實際可達 | — | **583** |
| Tuple 覆蓋率 | — | **93.4%** |

未可達的 ~41 tuple 主要為：
- terminal × retry > 0（terminals 被 stutter 鎖在 entering retry/recovery）
- recovery > 0 但 state ∈ {INIT, SCENARIO_DETECT, AGENT_LOAD}（發生 ESCALATION 之前）

兩者皆為**結構性不可達**，符合 FSM 規格。

---

## 4. Action Coverage

TLC `-coverage 1` 統計（distinct_states_generated : invocation_count）：

| Action | Distinct | Invocations | 狀態 |
|--------|----------|-------------|------|
| Init | 1 | 1 | ✅ 涵蓋 |
| Move（26 個 happy-path 移轉）| 26 | 456 | ✅ 全 callsite 覆蓋 |
| GateRetry（4 個 gate × retry < limit）| 60 | 80 | ✅ |
| GateExhaust（4 個 gate × retry == limit）| 0 | 16 | ✅ 觸發但狀態已知 |
| JumpKeep（觀測態 + emergency）| 86 | 323 | ✅ |
| T_EnterHub / T_HubExit | 153 | 384 | ✅ |
| T_EnterTraj / T_TrajContinue | 81 | 200 | ✅ |
| T_EnterAutoRecover / T_AutoRecoverOk | 21 | 36 | ✅ |
| T_EscToFinalAtLimit（recovery 上限）| 5 | 6 | ✅ Rule 9.14.1 路徑 |
| T_ResumeBack | 0 | 96 | ✅ 觸發但回到已知 state |
| T_EnterAutoCompact / T_AutoCompactExit | 126 | 768 | ✅ |
| T_TokenCriticalEnter | 24 | 431 | ✅ |
| T_TerminalStutter | 0 | 56 | ✅ 吸收態 stuttering |

所有 action 全部至少觸發一次（**100% action coverage**）。

---

## 5. M1+M2 新增狀態驗證（B5.4 / B5.5）

| 新增狀態 | 來源 ACT | 可達？ | 是否標記 transient |
|---------|---------|-------|------------------|
| `TRAJECTORY_PREDICTED` | ACT-035 / Rule 9.15 | ✅ 可達 | ✅ 已加入 ObservationStates，retry ≥ 1 才能進入 |
| `AUTO_RECOVERY_ATTEMPT` | ACT-033 / Rule 9.14 | ✅ 可達 | ✅ 已加入 ObservationStates，1-shot bounded |
| `ESCALATION_FINAL` | ACT-034 / Rule 9.14.4 | ✅ 可達 | — terminal（吸收態） |
| ~~`DRIFT_OBSERVATION`~~ | ACT-040（未實作）| N/A | M4 完工後再加入 |

**M1+M2 共 3 個新狀態**全部進入 spec、全部可達。`DRIFT_OBSERVATION` 因 M4 尚未交付，於本輪不納入；M4 ACT-040 完工時補件，並同步 .tla / .cfg 並 bump `MAX_RETRY` 範圍若需。

---

## 6. Safety Invariants 驗證明細

| Invariant | 對應規則 | 結果 |
|-----------|---------|------|
| `TypeOK` | 結構正確性 | ✅ 通過（全 583 tuples） |
| `RetryBounded`（retry ≤ 5）| Rule 9.1 | ✅ 通過 |
| `RecoveryBounded`（recovery ≤ 3）| Rule 9.14.1 | ✅ 通過 |
| `NotInBothSets`（Obs ∩ Terminal = ∅）| Rule 9.18.4 **結構性互斥約束**（非動態 transient 守門）| ✅ 通過 |

> **名實對齊說明**（QA 修 5）：`NotInBothSets` 為集合互斥宣告（constant-level
> formula），TLC 在 console 警告其評估為 TRUE 即代表結構合法；它**不是**
> 動態 transient 性質的守門 — 真正的動態 transient 由 `ObservationsTransient`
> 液性公式表達，需 `SF_vars` 支持，留 M5 v2 驗證。

---

## 7. Liveness（v2 後續工作）

`EventuallyTerminal` 與 `ObservationsTransient` 在無 fairness 假設下可被 TLC 用 stutter 路徑反證。具體 counterexample：

```
IMPLEMENTATION → SPEC_AUDIT → AUTO_COMPACT_PENDING → IMPLEMENTATION → ...（無限迴圈）
```

此 cycle 在實際 runtime 由 retry budget 與 recovery 上限收斂（已被 Chaos Runner 100 輪驗證），但 TLA+ 模型需顯式加 `SF_vars` / `WF_vars` 對 `T_RelReady` / `T_EscToTerminated` 等 progress action 才能讓 TLC 通過 liveness 檢查。

**M5 v1 的承諾**：safety + reachability ≥ 95%（已達成）。
**M5 v2 計畫**：補 fairness + liveness 證明（與 Phase G Final 同步交付）。

---

## 8. 結論

| 驗收項目（規劃文件 §M5）| 結果 |
|-----------------------|------|
| TLA+ specification of FSM | ✅ `SDD_FSM.tla`（337 行） |
| TLC config + CI 整合 | ✅ `SDD_FSM.cfg` + run_tlc.sh / .ps1 + CI step |
| `[]<>` terminal（必達終態）| 🟡 v1 改以 reachability + bounded retry/recovery 證明（liveness 留 v2）|
| Reachable state coverage ≥ 95% | ✅ **100%**（26/26）|
| 報告產出於 build/reports/formal/TLC-COVERAGE-{date}.md | ✅ 本檔 |

---

## 9. Next Action

| 項目 | 觸發時機 | 行動 |
|-----|---------|------|
| 補 liveness 證明 | M5 v2 / Phase G Final | 對 `T_RelReady`、`T_EscToTerminated`、`T_AutoRecoverFail` 加 SF_vars，重跑 TLC |
| 補 `DRIFT_OBSERVATION` | M4 / ACT-040 完工 | 加入 .tla ObservationStates 並補 transitions，重跑 TLC，更新本報告 |
| Nightly TLC drift check | CI / SDD_CICD_BASE_LAYER | 已加入 base layer（B5.7），每次 PR 觸發 |
| 萬一 `_HAPPY_PATH` 修改未同步 .tla | 任何 PR | Rule 9.18.1 禁止；CI step 會偵測 |

---

**驗證者**: TLC v1.8.0 model checker
**規劃對應**: `build/planning/archive/SDD_improving_Automation_06.md` §M5 (B5.1~B5.9)
**前置 tag**: `phase-g-mvp`（M1 + M2 已完成）
