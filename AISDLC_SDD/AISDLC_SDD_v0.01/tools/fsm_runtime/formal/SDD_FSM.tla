--------------------------- MODULE SDD_FSM ---------------------------
(***************************************************************************)
(* SDD FSM Formal Specification (Phase G M5 / ACT-041~042)                 *)
(*                                                                         *)
(* 對應實作: tools/fsm_runtime/transition_rules.py (_HAPPY_PATH)            *)
(* 對應規則: CLAUDE.md Rule 9.18 (B5.9)                                    *)
(*                                                                         *)
(* 證明目標：                                                              *)
(*   1. RetryBounded         — retry_count 永不超過 MAX_RETRY              *)
(*   2. NotInBothSets        — 任一狀態不可同時為 observation + terminal   *)
(*   3. NoDeadlock           — 非 terminal 狀態必有後繼（TLC 內建檢查）    *)
(*   4. ObservationsTransient— Rule 9.18.4：觀測狀態必為 transient        *)
(*   5. EventuallyTerminal   — 加上 fairness 後系統必達 terminal           *)
(*                                                                         *)
(* 涵蓋的 M1+M2 新增狀態（B5.4，共 4 個觀測/復原狀態加入此 .tla）：        *)
(*   - AUTO_RECOVERY_ATTEMPT     (Phase G M1 / ACT-033)                    *)
(*   - ESCALATION_FINAL          (Phase G M1 / ACT-034 — terminal)         *)
(*   - TRAJECTORY_PREDICTED      (Phase G M2 / ACT-035)                    *)
(*   - DRIFT_OBSERVATION (預留)  (Phase G M4 / ACT-040 — 尚未實作)         *)
(*                                                                         *)
(* 觀測狀態總集（B5.5：必須為 transient invariant）：                      *)
(*   PRODUCTION_SIGNAL, LEARNING_COMMIT, HUB_SYNC,                         *)
(*   TRAJECTORY_PREDICTED, AUTO_RECOVERY_ATTEMPT                           *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, TLC

CONSTANTS MAX_RETRY,           \* 最大 retry 次數（model 中設 5，匹配 PR_REVIEW limit）
          MAX_RECOVERY,        \* 最大 1-shot recovery 次數（per Rule 9.14.1）
          MAX_COMPACT,         \* AUTO_COMPACT_PENDING 進入次數上限（匹配 MAX_AUTO_COMPACT_PER_STAGE=3）
          MAX_HUB              \* HUB_SYNC 進入次數上限（生產為 one-shot sync，非無限 re-entry）

(* Phase I M2 / ACT-065（liveness 根因修復）：原模型把 AUTO_COMPACT_PENDING 與
   HUB_SYNC 設為「任一狀態 wildcard 無限 re-entry」，與現實不符 —— 現實由
   MAX_AUTO_COMPACT_PER_STAGE=3（fsm_runtime.trigger_auto_compact）與 Hub one-shot
   sync 強制有界。未編碼此有界性正是 EventuallyTerminal 無法成立的根因（假 2-cycle）。
   加 compact / hub 兩個有界計數器後，wildcard 自旋環被結構性消除，liveness 可證。 *)
VARIABLES state,               \* 當前 FSM 狀態
          retry,                \* 當前 gate 的 retry_count
          recovery,             \* 全 session AUTO_RECOVERY_ATTEMPT 次數
          compact,              \* AUTO_COMPACT_PENDING 進入累計（有界，破 compact wildcard 自旋）
          hub                   \* HUB_SYNC 進入累計（有界，破 hub wildcard 自旋）

vars == <<state, retry, recovery, compact, hub>>

(***************************************************************************)
(* State enumeration（與 transition_rules._HAPPY_PATH 鍵集 1:1 對應）      *)
(***************************************************************************)

HappyStates == {
    "INIT", "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING",
    "SCG_VALIDATION", "HUMAN_PENDING", "SPEC_REGRESSION_CHECK",
    "REMINDER", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW",
    "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY",
    "TEST_CONTRACT_NEGOTIATED",  \* Phase H M2 / ACT-049 ← H 新加入
    "EXECUTION_EVALUATION",      \* Phase H M1 / ACT-045 ← H 新加入
    "SANDBOX_HARDENING_GATE",    \* Phase I M1 / ACT-061 ← I 新加入（gatekeep）
    "BACKLOG_PRIORITIZED",       \* Phase I M3 / ACT-068 ← I 新加入（gatekeep）
    "ADVERSARIAL_EVALUATION",    \* Phase J / ACT-074 ← J 新加入（gatekeep）
    "INTENT_DECOMPOSITION"       \* Phase K M-K1 / ACT-082 ← K 新加入（gatekeep，有界）
}

(* B5.4 + B5.5：觀測狀態（OBSERVATION_STATES in transition_rules.py） *)
(* 規則 9.18.4：必須為 transient — 不可成為穩定態                       *)
ObservationStates == {
    "PRODUCTION_SIGNAL",        \* Phase E M3 / ACT-027
    "LEARNING_COMMIT",          \* Phase E M4 / ACT-028
    "HUB_SYNC",                 \* Phase F M2 / ACT-030
    "TRAJECTORY_PREDICTED",     \* Phase G M2 / ACT-035  ← M5 新加入
    "AUTO_RECOVERY_ATTEMPT",    \* Phase G M1 / ACT-033  ← M5 新加入
    "DRIFT_OBSERVATION",        \* Phase G M4 / ACT-040  ← Final 新加入
    "SCAFFOLD_GC",              \* Phase H M5 / ACT-055  ← H 新加入
    "EVALUATOR_AUDIT",          \* Phase I M1 / ACT-063  ← I 新加入
    "MONITOR_VIOLATION",        \* Phase I M2 / ACT-064  ← I 新加入
    "MEMORY_CONSOLIDATION",     \* Phase I M3 / ACT-066  ← I 新加入
    "PRODUCTION_BEHAVIORAL_SIGNAL",  \* Phase I M3 / ACT-067  ← I 新加入
    "CAPABILITY_BENCHMARK",     \* Phase J / ACT-076  ← J 新加入
    "SPEC_PATCH_PROPOSAL",      \* Phase J / ACT-078  ← J 新加入
    "SPEC_DEBATE",              \* Phase K M-K2 / ACT-084 ← K 新加入（advisory transient）
    "EXPERIMENT_REPLAY"         \* Phase L M-L2 / ACT-092 ← L 新加入（離線反事實 advisory transient）
}

EmergencyStates == {
    "ESCALATION",
    "TOKEN_BUDGET_CRITICAL",
    "AUTO_COMPACT_PENDING",
    "RESUME_VERIFICATION"
}

(* Terminal states — UNCHANGED 等於穩定態（吸收態） *)
Terminals == {
    "RELEASE",
    "TERMINATED",
    "ESCALATION_FINAL"          \* Phase G M1 / ACT-034 ← M5 新加入
}

States == HappyStates \cup ObservationStates \cup EmergencyStates \cup Terminals

(***************************************************************************)
(* Init                                                                    *)
(***************************************************************************)

Init == /\ state = "INIT"
        /\ retry = 0
        /\ recovery = 0
        /\ compact = 0
        /\ hub = 0

(***************************************************************************)
(* Transition helpers                                                      *)
(***************************************************************************)

(* 純前進（reset retry）。compact / hub 為有界 aux 計數器，純前進不動之。 *)
Move(src, dst) ==
    /\ state = src
    /\ state' = dst
    /\ retry' = 0
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* Gate fail：retry < MAX_RETRY 時退回 fallback 並 ++retry *)
GateRetry(src, fallback) ==
    /\ state = src
    /\ retry < MAX_RETRY
    /\ state' = fallback
    /\ retry' = retry + 1
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* Gate exhaust：retry == MAX_RETRY 即 ESCALATION（Rule 9.1）*)
GateExhaust(src) ==
    /\ state = src
    /\ retry >= MAX_RETRY
    /\ state' = "ESCALATION"
    /\ retry' = 0
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* 不變動 retry / recovery / compact / hub 的純狀態移轉 *)
JumpKeep(src, dst) ==
    /\ state = src
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(***************************************************************************)
(* Happy-path transitions（mirrors _HAPPY_PATH 行）                        *)
(***************************************************************************)

T_Init           == Move("INIT", "SCENARIO_DETECT")
T_ScenarioDetect == Move("SCENARIO_DETECT", "AGENT_LOAD")
T_AgentLoad      == Move("AGENT_LOAD", "SPEC_DRAFTING")
T_SpecDrafting   == Move("SPEC_DRAFTING", "SCG_VALIDATION")

T_ScgPass        == Move("SCG_VALIDATION", "HUMAN_PENDING")
T_ScgFail        == GateRetry("SCG_VALIDATION", "SPEC_DRAFTING")
T_ScgExhaust     == GateExhaust("SCG_VALIDATION")

T_HpToRegression == Move("HUMAN_PENDING", "SPEC_REGRESSION_CHECK")
T_HpToFrozen     == Move("HUMAN_PENDING", "SPEC_FROZEN")
T_HpToReminder   == Move("HUMAN_PENDING", "REMINDER")
T_ReminderBack   == Move("REMINDER", "HUMAN_PENDING")

T_RegPass        == Move("SPEC_REGRESSION_CHECK", "SPEC_FROZEN")
T_RegFail        == GateRetry("SPEC_REGRESSION_CHECK", "HUMAN_PENDING")
T_RegExhaust     == GateExhaust("SPEC_REGRESSION_CHECK")

(* Phase I M3 / ACT-068 — BACKLOG_PRIORITIZED（價值目標自選閘）*)
T_AgentLoadToBacklog == Move("AGENT_LOAD", "BACKLOG_PRIORITIZED")
T_BacklogToSpec      == Move("BACKLOG_PRIORITIZED", "SPEC_DRAFTING")

(* Phase K M-K1 / ACT-082 — INTENT_DECOMPOSITION（意圖分解 gatekeep，有界）。
   AGENT_LOAD → INTENT_DECOMPOSITION（分解閘，落在 BACKLOG 之前）；
   decomposed → BACKLOG_PRIORITIZED；underspecified → HUMAN_PENDING。
   acyclic 主幹（兩出口皆前進、無返回 AGENT_LOAD/INTENT_DECOMPOSITION 之邊），
   不引入新非 terminal cycle，WF_vars(Next) 即保證離開（無須額外 SF）。*)
T_AgentLoadToIntent == Move("AGENT_LOAD", "INTENT_DECOMPOSITION")
T_IntentDecomposed  == Move("INTENT_DECOMPOSITION", "BACKLOG_PRIORITIZED")
T_IntentUnderspec   == Move("INTENT_DECOMPOSITION", "HUMAN_PENDING")

T_FrozenToImpl   == Move("SPEC_FROZEN", "IMPLEMENTATION")
T_FrozenBack     == Move("SPEC_FROZEN", "SPEC_DRAFTING")

(* Phase H M2 / ACT-049 — TEST_CONTRACT_NEGOTIATED（測試合約談判閘）*)
T_FrozenToNegotiate == Move("SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED")
T_NegotiateToImpl   == Move("TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION")
T_NegotiateBack     == Move("TEST_CONTRACT_NEGOTIATED", "SPEC_DRAFTING")

T_ImplToReview   == Move("IMPLEMENTATION", "PR_REVIEW")
T_ImplToAudit    == Move("IMPLEMENTATION", "SPEC_AUDIT")  \* test_fail_threshold

(* Phase I M1 / ACT-061 — SANDBOX_HARDENING_GATE（執行接地前安全硬化閘）*)
T_ImplToHardening == Move("IMPLEMENTATION", "SANDBOX_HARDENING_GATE")
T_HardeningPass   == Move("SANDBOX_HARDENING_GATE", "EXECUTION_EVALUATION")
T_HardeningFail   == JumpKeep("SANDBOX_HARDENING_GATE", "ESCALATION")  \* sandbox_policy_violation

(* Phase H M1 / ACT-045 — EXECUTION_EVALUATION（執行接地評估閘）*)
T_ImplToExecEval == Move("IMPLEMENTATION", "EXECUTION_EVALUATION")
T_ExecEvalPass   == Move("EXECUTION_EVALUATION", "PR_REVIEW")
T_ExecEvalFail   == Move("EXECUTION_EVALUATION", "IMPLEMENTATION")
T_ExecEvalAudit  == Move("EXECUTION_EVALUATION", "SPEC_AUDIT")  \* runtime 揭露 spec 缺陷

T_PrPass         == Move("PR_REVIEW", "RTM_VERIFY")
T_PrToAudit      == Move("PR_REVIEW", "SPEC_AUDIT")       \* same-pattern × 3
T_PrFail         == GateRetry("PR_REVIEW", "IMPLEMENTATION")
T_PrExhaust      == GateExhaust("PR_REVIEW")

T_AuditBack      == Move("SPEC_AUDIT", "PR_REVIEW")

T_RtmPass        == Move("RTM_VERIFY", "RELEASE_READY")
T_RtmFail        == GateRetry("RTM_VERIFY", "IMPLEMENTATION")
T_RtmExhaust     == GateExhaust("RTM_VERIFY")

T_RelReady       == Move("RELEASE_READY", "RELEASE")

(***************************************************************************)
(* Observation states — Phase E~G                                          *)
(*                                                                         *)
(* B5.5：每個觀測狀態都有 ≥1 條離開路徑，保證 transient invariant 成立。  *)
(***************************************************************************)

(* PRODUCTION_SIGNAL — 入口僅 enter_production_signal()（從 RELEASE）    *)
T_EnterProdSignal   == JumpKeep("RELEASE", "PRODUCTION_SIGNAL")
T_ProdSignalRelease == JumpKeep("PRODUCTION_SIGNAL", "RELEASE")
T_ProdSignalRespec  == JumpKeep("PRODUCTION_SIGNAL", "SPEC_DRAFTING")

(* LEARNING_COMMIT — 入口從 {ESCALATION, RELEASE, PRODUCTION_SIGNAL}      *)
T_EnterLearning_Esc  == JumpKeep("ESCALATION", "LEARNING_COMMIT")
T_EnterLearning_Rel  == JumpKeep("RELEASE", "LEARNING_COMMIT")
T_EnterLearning_Prod == JumpKeep("PRODUCTION_SIGNAL", "LEARNING_COMMIT")
T_LearningOk         == JumpKeep("LEARNING_COMMIT", "RELEASE")
T_LearningNo         == JumpKeep("LEARNING_COMMIT", "ESCALATION")

(* HUB_SYNC — 入口 8 個 legal pre-states *)
HubSources == {"INIT", "SCENARIO_DETECT", "SPEC_DRAFTING", "SPEC_FROZEN",
               "RELEASE", "RELEASE_READY", "LEARNING_COMMIT", "HUMAN_PENDING"}
T_EnterHub == \E src \in HubSources :
    /\ state = src
    /\ hub < MAX_HUB                        \* 有界 re-entry（破 src↔HUB_SYNC 假 2-cycle）
    /\ state' = "HUB_SYNC"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub + 1
T_HubExit == \E dst \in HubSources :
    /\ state = "HUB_SYNC"
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* TRAJECTORY_PREDICTED (Phase G M2 / ACT-035) — Rule 9.15 *)
TrajSources == {"IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY",
                "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"}
T_EnterTraj == \E src \in TrajSources :
    /\ state = src
    /\ retry >= 1                           \* Rule 9.15.1
    /\ state' = "TRAJECTORY_PREDICTED"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_TrajContinue == \E dst \in TrajSources :
    /\ state = "TRAJECTORY_PREDICTED"
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_TrajSwitchAudit == JumpKeep("TRAJECTORY_PREDICTED", "SPEC_AUDIT")
T_TrajAbortEarly  == JumpKeep("TRAJECTORY_PREDICTED", "ESCALATION")

(* DRIFT_OBSERVATION (Phase G M4 / ACT-040) — Rule 9.17 *)
DriftSources == {"SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW",
                 "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"}
T_EnterDrift == \E src \in DriftSources :
    /\ state = src
    /\ state' = "DRIFT_OBSERVATION"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_DriftContinue == \E dst \in DriftSources :
    /\ state = "DRIFT_OBSERVATION"
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_DriftSwitchAudit == JumpKeep("DRIFT_OBSERVATION", "SPEC_AUDIT")

(* SCAFFOLD_GC (Phase H M5 / ACT-055) — Rule 9.20 鷹架代謝，結構同 PRODUCTION_SIGNAL *)
(* 入口僅 enter_scaffold_gc()（從 RELEASE，排程 / 人工觸發）*)
T_EnterScaffoldGc   == JumpKeep("RELEASE", "SCAFFOLD_GC")
T_ScaffoldGcRelease == JumpKeep("SCAFFOLD_GC", "RELEASE")
T_ScaffoldGcRespec  == JumpKeep("SCAFFOLD_GC", "SPEC_DRAFTING")

(* ===== Phase I（phase-i-tsg）新增觀測狀態 ===== *)

(* EVALUATOR_AUDIT (Phase I M1 / ACT-063) — 判官自審。入口 3 個合法前置態 *)
EvalAuditSources == {"EXECUTION_EVALUATION", "PRODUCTION_SIGNAL", "DRIFT_OBSERVATION"}
T_EnterEvalAudit == \E src \in EvalAuditSources :
    /\ state = src
    /\ state' = "EVALUATOR_AUDIT"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_EvalAuditContinue == JumpKeep("EVALUATOR_AUDIT", "EXECUTION_EVALUATION")
T_EvalAuditRelease  == JumpKeep("EVALUATOR_AUDIT", "RELEASE")
T_EvalAuditRespec   == JumpKeep("EVALUATOR_AUDIT", "SPEC_DRAFTING")

(* MONITOR_VIOLATION (Phase I M2 / ACT-064) — runtime monitor 補位，任一非 terminal 可觸發，出口僅 ESCALATION *)
T_EnterMonitorViolation == \E src \in (HappyStates \cup ObservationStates) :
    /\ state = src
    /\ state' = "MONITOR_VIOLATION"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_MonitorViolationToEsc == JumpKeep("MONITOR_VIOLATION", "ESCALATION")

(* MEMORY_CONSOLIDATION (Phase I M3 / ACT-066) — 成功結晶 sleep-phase *)
MemConsolSources == {"LEARNING_COMMIT", "RELEASE"}
T_EnterMemConsol == \E src \in MemConsolSources :
    /\ state = src
    /\ state' = "MEMORY_CONSOLIDATION"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_MemConsolRelease == JumpKeep("MEMORY_CONSOLIDATION", "RELEASE")
T_MemConsolRespec  == JumpKeep("MEMORY_CONSOLIDATION", "SPEC_DRAFTING")

(* PRODUCTION_BEHAVIORAL_SIGNAL (Phase I M3 / ACT-067) — 生產功能性偏差回饋 *)
PbsSources == {"RELEASE", "RELEASE_READY", "PRODUCTION_SIGNAL"}
T_EnterPbs == \E src \in PbsSources :
    /\ state = src
    /\ state' = "PRODUCTION_BEHAVIORAL_SIGNAL"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_PbsRespec   == JumpKeep("PRODUCTION_BEHAVIORAL_SIGNAL", "SPEC_DRAFTING")
T_PbsRelease  == JumpKeep("PRODUCTION_BEHAVIORAL_SIGNAL", "RELEASE")
T_PbsLearning == JumpKeep("PRODUCTION_BEHAVIORAL_SIGNAL", "LEARNING_COMMIT")

(* ===== Phase J（SDD_improving_Automation_10）新增狀態 ===== *)

(* ADVERSARIAL_EVALUATION (Phase J / ACT-074) — 對抗判官 gatekeep。
   接在 EXECUTION_EVALUATION verdict=pass 之後（加法式，保留 T_ExecEvalPass 直達邊）。
   出口：robust→PR_REVIEW / counterexample→IMPLEMENTATION / spec_gap→SPEC_AUDIT。 *)
T_ExecEvalToAdversarial == Move("EXECUTION_EVALUATION", "ADVERSARIAL_EVALUATION")
T_AdversarialPass    == Move("ADVERSARIAL_EVALUATION", "PR_REVIEW")
T_AdversarialCounter == Move("ADVERSARIAL_EVALUATION", "IMPLEMENTATION")
T_AdversarialSpecGap == Move("ADVERSARIAL_EVALUATION", "SPEC_AUDIT")

(* CAPABILITY_BENCHMARK (Phase J / ACT-076) — 模型能力基準觀測態。
   入口從 {SCAFFOLD_GC, MEMORY_CONSOLIDATION}；出口 done→RELEASE / respec→SPEC_DRAFTING。 *)
CapBenchSources == {"SCAFFOLD_GC", "MEMORY_CONSOLIDATION"}
T_EnterCapBench == \E src \in CapBenchSources :
    /\ state = src
    /\ state' = "CAPABILITY_BENCHMARK"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_CapBenchRelease == JumpKeep("CAPABILITY_BENCHMARK", "RELEASE")
T_CapBenchRespec  == JumpKeep("CAPABILITY_BENCHMARK", "SPEC_DRAFTING")

(* ===== Phase K M-K2 / ACT-084 — SPEC_DEBATE（規格辯證消歧觀測態，advisory transient）===== *)
(* SCG-0 子步：AmbiguityScorer 落 near-threshold 時進入；consensus→SCG_VALIDATION（續跑），
   divergence→HUMAN_PENDING（人工澄清）。SCG_VALIDATION↔SPEC_DEBATE 2-cycle 比照既有
   SCG_VALIDATION↔TRAJECTORY_PREDICTED，由 SF_vars(T_ScgPass) 破環，無須新增 fairness。*)
SpecDebateSources == {"SCG_VALIDATION"}
T_EnterSpecDebate == \E src \in SpecDebateSources :
    /\ state = src
    /\ state' = "SPEC_DEBATE"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_SpecDebateConsensus == JumpKeep("SPEC_DEBATE", "SCG_VALIDATION")
T_SpecDebateDiverge   == JumpKeep("SPEC_DEBATE", "HUMAN_PENDING")

(* SPEC_PATCH_PROPOSAL (Phase J / ACT-078) — 規格自癒觀測態。
   入口從 {SPEC_AUDIT, ESCALATION}（spec_defect 重複時）；
   出口 drafted→HUMAN_PENDING / nodraft→ESCALATION。 *)
SpecPatchSources == {"SPEC_AUDIT", "ESCALATION"}
T_EnterSpecPatch == \E src \in SpecPatchSources :
    /\ state = src
    /\ state' = "SPEC_PATCH_PROPOSAL"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub
T_SpecPatchToHuman == JumpKeep("SPEC_PATCH_PROPOSAL", "HUMAN_PENDING")
T_SpecPatchToEsc   == JumpKeep("SPEC_PATCH_PROPOSAL", "ESCALATION")

(* ===== Phase L M-L2 / ACT-092 — EXPERIMENT_REPLAY（離線反事實實驗觀測態）===== *)
(* 補丁送人工 approve 前先過離線反事實重放取「歷史命中率」證據。入口僅從
   SPEC_PATCH_PROPOSAL；出口 done→SPEC_PATCH_PROPOSAL（附證據續送人工）/
   inconclusive→HUMAN_PENDING（語料不足，Rule 8）。SPEC_PATCH_PROPOSAL↔EXPERIMENT_REPLAY
   2-cycle 比照 SCG↔SPEC_DEBATE，由 SF_vars(T_SpecPatchToHuman) 破環（見 Fairness）。*)
T_EnterExperimentReplay     == JumpKeep("SPEC_PATCH_PROPOSAL", "EXPERIMENT_REPLAY")
T_ExperimentReplayDone      == JumpKeep("EXPERIMENT_REPLAY", "SPEC_PATCH_PROPOSAL")
T_ExperimentReplayInconcl   == JumpKeep("EXPERIMENT_REPLAY", "HUMAN_PENDING")

(* AUTO_RECOVERY_ATTEMPT (Phase G M1 / ACT-033) — Rule 9.14 *)
AutoRecoveryResume == {"SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW",
                       "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"}

(* Rule 9.14.1: 全 session 上限 MAX_RECOVERY；超過即拒絕進入 *)
T_EnterAutoRecover == /\ state = "ESCALATION"
                      /\ recovery < MAX_RECOVERY
                      /\ state' = "AUTO_RECOVERY_ATTEMPT"
                      /\ retry' = 0
                      /\ recovery' = recovery + 1
                      /\ compact' = compact
                      /\ hub' = hub

T_AutoRecoverOk == \E dst \in AutoRecoveryResume :
    /\ state = "AUTO_RECOVERY_ATTEMPT"
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* Rule 9.14.4: AUTO_RECOVERY 失敗即 ESCALATION_FINAL，不可再嘗試 *)
T_AutoRecoverFail == JumpKeep("AUTO_RECOVERY_ATTEMPT", "ESCALATION_FINAL")

(* 當 recovery 已達上限，ESCALATION 必須直升 ESCALATION_FINAL *)
T_EscToFinalAtLimit == /\ state = "ESCALATION"
                       /\ recovery >= MAX_RECOVERY
                       /\ state' = "ESCALATION_FINAL"
                       /\ retry' = retry
                       /\ recovery' = recovery
                       /\ compact' = compact
                       /\ hub' = hub

(***************************************************************************)
(* Emergency / recovery transitions                                        *)
(***************************************************************************)

T_EscToTerminated  == JumpKeep("ESCALATION", "TERMINATED")
T_EscToResume      == JumpKeep("ESCALATION", "RESUME_VERIFICATION")
T_EscFinalToTerm   == JumpKeep("ESCALATION_FINAL", "TERMINATED")
T_EscFinalToResume == JumpKeep("ESCALATION_FINAL", "RESUME_VERIFICATION")

T_ResumeBack == \E dst \in {"SPEC_DRAFTING", "IMPLEMENTATION",
                            "PR_REVIEW", "ESCALATION"} :
    /\ state = "RESUME_VERIFICATION"
    /\ state' = dst
    /\ retry' = 0
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

T_TokenCriticalToEsc == JumpKeep("TOKEN_BUDGET_CRITICAL", "ESCALATION")

(* AUTO_COMPACT_PENDING — entry from AUTO_COMPACT_SOURCES *)
AutoCompactSources == {"INIT", "SCENARIO_DETECT", "AGENT_LOAD",
                       "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING",
                       "SPEC_REGRESSION_CHECK", "SPEC_FROZEN", "IMPLEMENTATION",
                       "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY",
                       "REMINDER", "RESUME_VERIFICATION", "PRODUCTION_SIGNAL"}
T_EnterAutoCompact == \E src \in AutoCompactSources :
    /\ state = src
    /\ compact < MAX_COMPACT                \* 有界 re-entry（破 src↔AUTO_COMPACT 假 2-cycle）
    /\ state' = "AUTO_COMPACT_PENDING"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact + 1
    /\ hub' = hub
T_AutoCompactExit == \E dst \in AutoCompactSources :
    /\ state = "AUTO_COMPACT_PENDING"
    /\ state' = dst
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(* QA 修 3：對齊 _HAPPY_PATH["AUTO_COMPACT_PENDING"] —
   .py 顯式列出 TOKEN_BUDGET_CRITICAL 與 ESCALATION 兩個合法出口，
   .tla 必須對應，否則破 Rule 9.18.1 雙源一致性 *)
T_AutoCompactToEsc           == JumpKeep("AUTO_COMPACT_PENDING", "ESCALATION")
T_AutoCompactToTokenCritical == JumpKeep("AUTO_COMPACT_PENDING", "TOKEN_BUDGET_CRITICAL")

(* Token budget critical — 任一非 terminal 可觸發 *)
T_TokenCriticalEnter == \E src \in (HappyStates \cup ObservationStates) :
    /\ state = src
    /\ state' = "TOKEN_BUDGET_CRITICAL"
    /\ retry' = retry
    /\ recovery' = recovery
    /\ compact' = compact
    /\ hub' = hub

(***************************************************************************)
(* Terminal stutter（吸收態）                                              *)
(***************************************************************************)

T_TerminalStutter == /\ state \in Terminals
                     /\ UNCHANGED vars

(***************************************************************************)
(* Next                                                                    *)
(***************************************************************************)

Next ==
    \/ T_Init \/ T_ScenarioDetect \/ T_AgentLoad \/ T_SpecDrafting
    \/ T_ScgPass \/ T_ScgFail \/ T_ScgExhaust
    \/ T_HpToRegression \/ T_HpToFrozen \/ T_HpToReminder \/ T_ReminderBack
    \/ T_RegPass \/ T_RegFail \/ T_RegExhaust
    \/ T_FrozenToImpl \/ T_FrozenBack
    (* Phase I M3 — 價值目標自選閘 *)
    \/ T_AgentLoadToBacklog \/ T_BacklogToSpec
    (* Phase K — 意圖分解 gatekeep *)
    \/ T_AgentLoadToIntent \/ T_IntentDecomposed \/ T_IntentUnderspec
    (* Phase H M2 — 測試合約談判 *)
    \/ T_FrozenToNegotiate \/ T_NegotiateToImpl \/ T_NegotiateBack
    \/ T_ImplToReview \/ T_ImplToAudit
    (* Phase I M1 — 沙箱安全硬化閘 *)
    \/ T_ImplToHardening \/ T_HardeningPass \/ T_HardeningFail
    (* Phase H M1 — 執行接地評估 *)
    \/ T_ImplToExecEval \/ T_ExecEvalPass \/ T_ExecEvalFail \/ T_ExecEvalAudit
    \/ T_PrPass \/ T_PrToAudit \/ T_PrFail \/ T_PrExhaust
    \/ T_AuditBack
    \/ T_RtmPass \/ T_RtmFail \/ T_RtmExhaust
    \/ T_RelReady
    (* Phase E~F observation *)
    \/ T_EnterProdSignal \/ T_ProdSignalRelease \/ T_ProdSignalRespec
    \/ T_EnterLearning_Esc \/ T_EnterLearning_Rel \/ T_EnterLearning_Prod
    \/ T_LearningOk \/ T_LearningNo
    \/ T_EnterHub \/ T_HubExit
    (* Phase G M1+M2 — B5.4 新加入 *)
    \/ T_EnterTraj \/ T_TrajContinue \/ T_TrajSwitchAudit \/ T_TrajAbortEarly
    \/ T_EnterAutoRecover \/ T_AutoRecoverOk \/ T_AutoRecoverFail
    \/ T_EscToFinalAtLimit
    (* Phase G M4 — Final 新加入 *)
    \/ T_EnterDrift \/ T_DriftContinue \/ T_DriftSwitchAudit
    (* Phase H M5 — 鷹架代謝 *)
    \/ T_EnterScaffoldGc \/ T_ScaffoldGcRelease \/ T_ScaffoldGcRespec
    (* Phase I M1 — 判官自審 *)
    \/ T_EnterEvalAudit \/ T_EvalAuditContinue \/ T_EvalAuditRelease \/ T_EvalAuditRespec
    (* Phase I M2 — runtime monitor 補位 *)
    \/ T_EnterMonitorViolation \/ T_MonitorViolationToEsc
    (* Phase I M3 — 成功結晶 sleep-phase *)
    \/ T_EnterMemConsol \/ T_MemConsolRelease \/ T_MemConsolRespec
    (* Phase I M3 — 生產 behavioral 回饋 *)
    \/ T_EnterPbs \/ T_PbsRespec \/ T_PbsRelease \/ T_PbsLearning
    (* Phase J — 對抗判官 gatekeep *)
    \/ T_ExecEvalToAdversarial \/ T_AdversarialPass \/ T_AdversarialCounter \/ T_AdversarialSpecGap
    (* Phase J — 模型能力基準觀測態 *)
    \/ T_EnterCapBench \/ T_CapBenchRelease \/ T_CapBenchRespec
    (* Phase J — 規格自癒觀測態 *)
    \/ T_EnterSpecPatch \/ T_SpecPatchToHuman \/ T_SpecPatchToEsc
    (* Phase K — 規格辯證消歧觀測態 *)
    \/ T_EnterSpecDebate \/ T_SpecDebateConsensus \/ T_SpecDebateDiverge
    (* Phase L — 離線反事實實驗觀測態 *)
    \/ T_EnterExperimentReplay \/ T_ExperimentReplayDone \/ T_ExperimentReplayInconcl
    (* Emergency / recovery *)
    \/ T_EscToTerminated \/ T_EscToResume
    \/ T_EscFinalToTerm \/ T_EscFinalToResume
    \/ T_ResumeBack
    \/ T_TokenCriticalToEsc \/ T_TokenCriticalEnter
    \/ T_EnterAutoCompact \/ T_AutoCompactExit
    \/ T_AutoCompactToEsc \/ T_AutoCompactToTokenCritical
    \/ T_TerminalStutter

(* ===== Phase I M2 / ACT-065 — Liveness fairness =====
   原 M5 v1 只用 WF_vars(Next)，不足以證 EventuallyTerminal /
   ObservationsTransient：emergency / observation cycle（如 SCG_VALIDATION →
   AUTO_COMPACT_PENDING → resume → SCG_VALIDATION）可在無 per-action fairness 下
   無限自旋。對整個 Next 的 SF 太弱（cycle 內任一 ProgressAction fire 即滿足）。

   正解：對「離開每個 sticky（gate / 觀測 / emergency）狀態的前進 / 退場 action」
   個別加 Strong Fairness — 只要該 action 在某狀態反覆可行就終會 fire，強制離開
   該狀態、不被 auto-compact / retry / observation cycle 永久困住。Move/JumpKeep
   到 terminal 的吸收態不需 fairness。*)
(* ===== Phase I M2 / ACT-065 — Liveness（根因修復後完整啟用）=====
   兩條液性性質皆由 TLC 窮舉驗證 PASS：
     - ObservationsTransient（Rule 9.18.4）：觀測態無 self-loop 且非 terminal，
       WF 即保證必離開。
     - EventuallyTerminal：原失敗根因為模型未編碼 AUTO_COMPACT/HUB 的有界 re-entry
       （現實由 MAX_AUTO_COMPACT_PER_STAGE / Hub one-shot 強制有界）。加 compact /
       hub 有界計數器後，wildcard 假 2-cycle 結構性消除；其餘 cycle（trunk gate /
       SPEC_AUDIT↔PR / TRAJ↔gate / ESCALATION↔recovery）由下列「推向 terminal 的
       單一 action SF」破除。retry/recovery/compact/hub 四計數器皆有界 ⇒ 無 fair
       非 terminal cycle ⇒ 每條行為必達 {RELEASE, TERMINATED, ESCALATION_FINAL}。

   SF 只加在「把 recurrent sticky 狀態推向更靠近 terminal」的特定單一 action，
   數量精簡（落在 TLC DNF 上限內，已實測 PASS）。 *)
Fairness ==
    (* success 路徑：強制 happy trunk 一路前進至 RELEASE *)
    /\ SF_vars(T_SpecDrafting)   \* SPEC_DRAFTING → SCG_VALIDATION（破 SPEC_DRAFTING↔DRIFT/HUB）
    /\ SF_vars(T_ScgPass) /\ SF_vars(T_HpToFrozen) /\ SF_vars(T_RegPass)
    /\ SF_vars(T_FrozenToImpl) /\ SF_vars(T_NegotiateToImpl)
    /\ SF_vars(T_ImplToReview) /\ SF_vars(T_HardeningPass) /\ SF_vars(T_ExecEvalPass)
    /\ SF_vars(T_AdversarialPass)  \* Phase J：對抗閘 robust → PR_REVIEW（破對抗↔impl 環）
    /\ SF_vars(T_PrPass) /\ SF_vars(T_RtmPass) /\ SF_vars(T_RelReady)
    (* fail 路徑：強制 emergency 最終觸及 terminal *)
    /\ SF_vars(T_EscToTerminated) /\ SF_vars(T_EscFinalToTerm)
    (* Phase K M-K2 / ACT-084：SPEC_DEBATE consensus 出口 SF — 強化 observation
       transient（ObservationsTransient 含 SF_vars(T_SpecDebateConsensus)），確保
       辯證收斂時必離開 SPEC_DEBATE 回 SCG_VALIDATION，不被 SCG↔DEBATE 2-cycle 困住 *)
    /\ SF_vars(T_SpecDebateConsensus)
    (* Phase L M-L2 / ACT-092：破 SPEC_PATCH_PROPOSAL↔EXPERIMENT_REPLAY 2-cycle。
       補丁反覆進出反事實重放時，SF 強制 SPEC_PATCH_PROPOSAL 終究送 HUMAN_PENDING
       （人工裁決），不被重放 2-cycle 永久困住，保 EventuallyTerminal 不回歸。*)
    /\ SF_vars(T_SpecPatchToHuman)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next) /\ Fairness

(***************************************************************************)
(* Safety invariants                                                       *)
(***************************************************************************)

TypeOK == /\ state \in States
          /\ retry \in 0..MAX_RETRY
          /\ recovery \in 0..MAX_RECOVERY
          /\ compact \in 0..MAX_COMPACT
          /\ hub \in 0..MAX_HUB

(* Rule 9.1：retry_count never exceeds MAX_RETRY *)
RetryBounded == retry <= MAX_RETRY

(* Rule 9.14.1：recovery 全 session 上限 *)
RecoveryBounded == recovery <= MAX_RECOVERY

(* Trivial sanity：observation 集合與 terminal 集合互斥（B5.5） *)
NotInBothSets == ObservationStates \cap Terminals = {}

(***************************************************************************)
(* Liveness — Termination & Observations Transient                         *)
(***************************************************************************)

(* 主要液性：每一條行為最終必達 terminal *)
EventuallyTerminal == <>(state \in Terminals)

(* Rule 9.18.4：觀測狀態 transient — 從觀測狀態出發必定離開 *)
ObservationsTransient ==
    \A obs \in ObservationStates :
        [](state = obs => <>(state # obs))

=============================================================================
\* Modification History
\* Created 2026-04-26 — Phase G M5 / ACT-041 (B5.2~B5.5)
