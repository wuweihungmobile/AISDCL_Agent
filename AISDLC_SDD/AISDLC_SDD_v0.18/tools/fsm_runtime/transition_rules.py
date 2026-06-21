"""FSM transition rules — mirrors SDD_FSM_ENGINE.md section 狀態轉換表."""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Set, Tuple


class TransitionError(RuntimeError):
    """Raised when a requested transition is not allowed by the FSM."""


# Happy-path transitions (source -> set of allowed targets)
_HAPPY_PATH: Dict[str, Set[str]] = {
    "INIT": {"SCENARIO_DETECT"},
    "SCENARIO_DETECT": {"AGENT_LOAD"},
    # Phase I M3 / ACT-068：加法式新增 AGENT_LOAD → BACKLOG_PRIORITIZED（價值目標
    # 自選閘）。保留 AGENT_LOAD → SPEC_DRAFTING 直達邊（向後相容、人工種子驅動）。
    # Phase K M-K1 / ACT-082：加法式新增 AGENT_LOAD → INTENT_DECOMPOSITION（意圖分解
    # 宏觀規劃閘）；落在 BACKLOG_PRIORITIZED 之前，產出候選餵 value_planner。
    "AGENT_LOAD": {"SPEC_DRAFTING", "BACKLOG_PRIORITIZED", "INTENT_DECOMPOSITION"},
    # Phase K M-K1 / ACT-082：INTENT_DECOMPOSITION（意圖分解 gatekeep，有界）出口 —
    #   decomposed     → BACKLOG_PRIORITIZED（acyclic spec-DAG，候選排 ROI 後人工 signoff）
    #   underspecified → HUMAN_PENDING（意圖過模糊/成環/觸頂，請人工澄清，Rule 8）
    "INTENT_DECOMPOSITION": {"BACKLOG_PRIORITIZED", "HUMAN_PENDING"},
    # Phase I M3 / ACT-068：BACKLOG_PRIORITIZED 人工 signoff 選定最高 ROI 後進 SPEC_DRAFTING。
    "BACKLOG_PRIORITIZED": {"SPEC_DRAFTING"},
    "SPEC_DRAFTING": {"SCG_VALIDATION"},
    "SCG_VALIDATION": {"HUMAN_PENDING", "SPEC_DRAFTING"},
    "HUMAN_PENDING": {"SPEC_REGRESSION_CHECK", "SPEC_FROZEN", "REMINDER"},
    "SPEC_REGRESSION_CHECK": {"SPEC_FROZEN", "HUMAN_PENDING"},
    "REMINDER": {"HUMAN_PENDING"},
    # Phase H M2 / ACT-049：插入 TEST_CONTRACT_NEGOTIATED（測試合約談判閘）。
    # 加法式：保留 SPEC_FROZEN → IMPLEMENTATION 既有邊（向後相容、不破既有 404 測試
    # 與 TLC 證明），同時新增 SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED。預設路由由
    # orchestrator/runtime 強制走談判閘（Rule 9.20.x），_HAPPY_PATH 僅定義「允許」。
    "SPEC_FROZEN": {"IMPLEMENTATION", "SPEC_DRAFTING", "TEST_CONTRACT_NEGOTIATED"},
    # Phase H M2 / ACT-049：談判閘出口 — 共識達成 → IMPLEMENTATION；
    # 無共識（規格不夠明確以致無法定 oracle）→ SPEC_DRAFTING 重擬規格。
    "TEST_CONTRACT_NEGOTIATED": {"IMPLEMENTATION", "SPEC_DRAFTING"},
    # QA Round-3 P1-01: test_fail_without_spec_change ≥ 5 在 IMPLEMENTATION 直接
    # 轉入 SPEC_AUDIT（should_escalate_for_implementation 回傳的「非 escalate、
    # 但需 audit」訊號），先前此轉換因不在 happy path 而被 TransitionError 吞掉。
    # Phase H M1 / ACT-045：加法式新增 IMPLEMENTATION → EXECUTION_EVALUATION
    # （執行接地評估閘）。保留既有 PR_REVIEW 直達邊以維持向後相容。
    # Phase I M1 / ACT-061：加法式新增 IMPLEMENTATION → SANDBOX_HARDENING_GATE
    # （執行接地前先過安全硬化閘；預設路由由 orchestrator 強制走硬化閘）。
    "IMPLEMENTATION": {"PR_REVIEW", "SPEC_AUDIT", "EXECUTION_EVALUATION",
                       "SANDBOX_HARDENING_GATE"},
    # Phase I M1 / ACT-061：硬化閘出口 — pass→EXECUTION_EVALUATION；
    # fail（image/簽章/lockfile/self-STRIDE 違反）→ ESCALATION（emergency target）。
    "SANDBOX_HARDENING_GATE": {"EXECUTION_EVALUATION", "ESCALATION"},
    # Phase H M1 / ACT-045：執行評估閘出口 — 沙箱實跑客觀 verdict。
    #   pass        → PR_REVIEW（再做靜態合規確認）
    #   runtime fail→ IMPLEMENTATION（回修，沿用 retry budget EXEC_EVAL_LIMIT）
    #   spec defect → SPEC_AUDIT（執行揭露規格矛盾，如 P95<0 不可滿足）
    # Phase I M1 / ACT-063：加法式新增 EXECUTION_EVALUATION → EVALUATOR_AUDIT
    # （判官自審觀測態，由 runtime API enter_evaluator_audit 進入；非新 happy 出口）。
    # Phase J / ACT-074：加法式新增 EXECUTION_EVALUATION → ADVERSARIAL_EVALUATION
    # （對抗判官閘；verdict=pass 後改走對抗評估，保留既有 PR_REVIEW 直達邊以向後相容）。
    "EXECUTION_EVALUATION": {"PR_REVIEW", "IMPLEMENTATION", "SPEC_AUDIT",
                             "ADVERSARIAL_EVALUATION"},
    # Phase J / ACT-074：ADVERSARIAL_EVALUATION（對抗判官 gatekeep）出口 —
    #   robust         → PR_REVIEW（N 輪攻擊無破）
    #   counterexample → IMPLEMENTATION（程式違反已宣告性質/崩潰，計入 retry budget）
    #   spec_gap       → SPEC_AUDIT（違反隱含 latent 關係，AC 漏寫）
    "ADVERSARIAL_EVALUATION": {"PR_REVIEW", "IMPLEMENTATION", "SPEC_AUDIT"},
    "PR_REVIEW": {"RTM_VERIFY", "SPEC_AUDIT", "IMPLEMENTATION"},
    "SPEC_AUDIT": {"PR_REVIEW"},
    "RTM_VERIFY": {"RELEASE_READY", "IMPLEMENTATION"},
    "RELEASE_READY": {"RELEASE"},
    "RELEASE": set(),
    # Phase E / ACT-027：Production Feedback（非阻塞監測狀態）
    # 入口只能透過 FSMRuntime.enter_production_signal() 明確觸發（RELEASE → PRODUCTION_SIGNAL 不在
    # happy path，避免破壞 RELEASE 為 terminal 的既有 invariant；chaos_runner 不會誤抽中此狀態）。
    # 出口回到 SPEC_DRAFTING（drift 持續 → 重新 re-spec）或 RELEASE（drift 僅為告知，無需 re-spec）。
    "PRODUCTION_SIGNAL": {"SPEC_DRAFTING", "RELEASE"},
    # Phase E M4 / ACT-028：Learning Layer（非阻塞背景狀態）
    # 入口透過 FSMRuntime.enter_learning_commit() 明確觸發（通常由 ESCALATION 後的 abort_report
    # 分析或手動 /slv-generator propose 觸發）；出口回 RELEASE（人工 review 完成）或 ESCALATION（review
    # 拒絕且無其他恢復路徑）。與 PRODUCTION_SIGNAL 一樣為 observation 類型，不阻擋工具呼叫。
    "LEARNING_COMMIT": {"RELEASE", "ESCALATION"},
    # Phase F M2 / ACT-030：Cross-Project Learning Hub Sync（非阻塞觀測狀態）
    # 入口透過 FSMRuntime.enter_hub_sync() 明確觸發；典型來源是 session_start 的
    # auto-pull 或使用者顯式 push。出口：success → 回原狀態（透過 resume_from
    # 記錄）；partial（衝突）→ HUMAN_PENDING；failed → 直接 transition 回原
    # 狀態並記 decision_trace（不升 ESCALATION，沿用 HUB-GOVERNANCE §捌）。
    "HUB_SYNC": {
        "INIT", "SCENARIO_DETECT", "SPEC_DRAFTING", "SPEC_FROZEN",
        "RELEASE", "RELEASE_READY", "LEARNING_COMMIT",
        "HUMAN_PENDING",
    },
    # Phase H M5 / ACT-055：Scaffold Metabolism（鷹架代謝，非阻塞觀測態）。
    # 結構同 PRODUCTION_SIGNAL：入口透過 FSMRuntime.enter_scaffold_gc()（排程 /
    # RELEASE 後 / 人工觸發）；出口 continue → RELEASE（無需動作）或 SPEC_DRAFTING
    # （GC 發現規格層需修正）。退役提案不直接走 FSM 邊，而是寫 SCAFFOLD-ROI 報告，
    # 由既有 LEARNING_COMMIT 人工 review 流程非同步消化（decoupled，避免污染 LC 入口契約）。
    "SCAFFOLD_GC": {"RELEASE", "SPEC_DRAFTING"},
    # ===== Phase I（規劃 phase-i-tsg）新增觀測 / 閘狀態 =====
    # Pillar A / ACT-063：EVALUATOR_AUDIT — 判官自審（OQS 校準鏈 + oracle 新鮮度）。
    # 入口 enter_evaluator_audit()（從 EXECUTION_EVALUATION/PRODUCTION_SIGNAL/DRIFT_OBSERVATION）。
    # 出口 continue→EXECUTION_EVALUATION；recalibrate（人工 gate 後）→RELEASE/SPEC_DRAFTING。
    "EVALUATOR_AUDIT": {"EXECUTION_EVALUATION", "RELEASE", "SPEC_DRAFTING"},
    # Pillar C / ACT-064：MONITOR_VIOLATION — runtime monitor 偵測 .tla invariant
    # 破壞時補位。入口 enter_monitor_violation()（任一非 terminal）。出口僅 ESCALATION（不可恢復）。
    "MONITOR_VIOLATION": {"ESCALATION"},
    # Pillar B / ACT-066：MEMORY_CONSOLIDATION — 成功結晶 sleep-phase。
    # 入口 enter_memory_consolidation()（nightly cron / LEARNING_COMMIT / RELEASE 後）。
    "MEMORY_CONSOLIDATION": {"RELEASE", "SPEC_DRAFTING"},
    # Pillar B / ACT-067：PRODUCTION_BEHAVIORAL_SIGNAL — 生產功能性偏差→FPL→SLV。
    # 入口 enter_production_behavioral_signal()（從 RELEASE/RELEASE_READY/PRODUCTION_SIGNAL）。
    "PRODUCTION_BEHAVIORAL_SIGNAL": {"SPEC_DRAFTING", "RELEASE", "LEARNING_COMMIT"},
    # ===== Phase J（規劃 SDD_improving_Automation_10）新增觀測狀態 =====
    # Pillar B / ACT-076：CAPABILITY_BENCHMARK — 模型能力基準（觀測態）。
    # 入口 enter_capability_benchmark()（從 SCAFFOLD_GC / MEMORY_CONSOLIDATION）。
    # 出口 done→RELEASE；respec→SPEC_DRAFTING（能力量測揭露規格層缺口）。
    "CAPABILITY_BENCHMARK": {"RELEASE", "SPEC_DRAFTING"},
    # Pillar C / ACT-078：SPEC_PATCH_PROPOSAL — 規格自癒（觀測態）。
    # 入口 enter_spec_patch_proposal()（從 SPEC_AUDIT / ESCALATION，spec_defect 重複時）。
    # 出口 drafted→HUMAN_PENDING（人工 approve/reject diff）；nodraft→ESCALATION。
    # Phase L M-L2 / ACT-092：加法式新增 SPEC_PATCH_PROPOSAL → EXPERIMENT_REPLAY
    # （補丁送人工前先過離線反事實重放取「歷史命中率」證據）。入口由 runtime
    # enter_experiment_replay 進入（observation），不改既有 HUMAN_PENDING/ESCALATION 出口。
    "SPEC_PATCH_PROPOSAL": {"HUMAN_PENDING", "ESCALATION", "EXPERIMENT_REPLAY"},
    # Phase L M-L2 / ACT-092：EXPERIMENT_REPLAY（離線反事實實驗觀測態，advisory transient）。
    # 入口透過 FSMRuntime.enter_experiment_replay()（從 SPEC_PATCH_PROPOSAL）。
    # 出口 done→SPEC_PATCH_PROPOSAL（附命中證據續送人工）；inconclusive→HUMAN_PENDING
    # （歷史語料不足，導人工裁決，Rule 8）。SPEC_PATCH_PROPOSAL↔EXPERIMENT_REPLAY 2-cycle
    # 由 SF_vars(T_SpecPatchToHuman) 破環（見 SDD_FSM.tla Fairness），不引入新非 terminal cycle。
    "EXPERIMENT_REPLAY": {"SPEC_PATCH_PROPOSAL", "HUMAN_PENDING"},
    # Phase K M-K2 / ACT-084：SPEC_DEBATE（規格辯證消歧觀測態，advisory transient）。
    # 入口透過 FSMRuntime.enter_spec_debate()（SCG-0 子步，AmbiguityScorer near-threshold 時）。
    # 出口 consensus→SCG_VALIDATION（續跑）；divergence→HUMAN_PENDING（人工澄清，Rule 9.23.4）。
    # SCG_VALIDATION↔SPEC_DEBATE 2-cycle 比照既有 SCG_VALIDATION↔TRAJECTORY_PREDICTED，
    # 由 SF_vars(T_ScgPass) 破環（見 SDD_FSM.tla Fairness），不引入新非 terminal cycle。
    "SPEC_DEBATE": {"SCG_VALIDATION", "HUMAN_PENDING"},
    # Phase Z / ACT-172：AUTOCLAUDE_DELEGATED（SDD→AutoClaude 委派執行觀測態，
    # 非阻塞 transient）。入口僅 FSMRuntime.enter_autoclaude_delegated()（從
    # IMPLEMENTATION 明確觸發；IMPLEMENTATION 出邊集不含本態，遵循觀測態入口慣例，
    # 比照 EVALUATOR_AUDIT/MEMORY_CONSOLIDATION）。出口：
    #   delegation_done   → IMPLEMENTATION（委派完成帶回 resume）
    #   delegation_failed → ESCALATION（AutoClaude 側演化亦失敗/越閘 → 升級）
    # IMPLEMENTATION↔AUTOCLAUDE_DELEGATED 2-cycle 由 SF_vars(T_AutoDelegToImpl)
    # 破環（見 SDD_FSM.tla Fairness），不引入新非 terminal cycle。
    "AUTOCLAUDE_DELEGATED": {"IMPLEMENTATION", "ESCALATION"},
    # Error / recovery branches
    # Phase G M1 / ACT-033: ESCALATION can branch into AUTO_RECOVERY_ATTEMPT
    # (when DiagnosticAgent classifies the cause as transient/auto_recoverable)
    # or ESCALATION_FINAL (when structural — must escalate to human).
    "ESCALATION": {
        "TERMINATED", "RESUME_VERIFICATION",
        "AUTO_RECOVERY_ATTEMPT", "ESCALATION_FINAL",
    },
    "RESUME_VERIFICATION": {"SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "ESCALATION"},
    "TERMINATED": set(),
    "TOKEN_BUDGET_CRITICAL": {"ESCALATION"},
    # Phase G M1 / ACT-033: 1-shot bounded auto-recovery window. Entry only via
    # FSMRuntime.enter_auto_recovery() after DiagnosticAgent confirms transient.
    # Exit on success → resume_state (gate-resumable subset);
    # Exit on failure → ESCALATION_FINAL (no further auto-recovery allowed,
    # per Rule 9.14.4).
    "AUTO_RECOVERY_ATTEMPT": {
        "SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW",
        "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
        "ESCALATION_FINAL",
    },
    # Phase G M1 / ACT-034: Terminal-like state reached when auto-recovery
    # fails OR DiagnosticAgent classifies cause as structural. Blocking
    # (no tool calls) like ESCALATION; only human can move out.
    "ESCALATION_FINAL": {"TERMINATED", "RESUME_VERIFICATION"},
    # Phase G M2 / ACT-035/036: Predictive halt observation state. Entry only
    # via FSMRuntime.enter_trajectory_predicted() after a retry-prone gate
    # consults TrajectoryPredictor (Rule 9.15.1 — retry_count ≥ 1).
    # Exits:
    #   - continue        → back to recorded retry gate (resume_state)
    #   - switch_to_audit → SPEC_AUDIT (saves remaining retry budget)
    #   - abort_early     → ESCALATION (covered by _EMERGENCY_TARGETS)
    "TRAJECTORY_PREDICTED": {
        "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY",
        "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
        "SPEC_AUDIT",
    },
    # Phase G M4 / ACT-040: Continuous Drift Monitor observation state.
    # Entry via FSMRuntime.enter_drift_observation() when PostCommit hook
    # detects drift_score >= 0.3 (Rule 9.17.2). Exits:
    #   - continue        → resume_state (single drift, advisory only)
    #   - switch_to_audit → SPEC_AUDIT (consecutive 3 commits, Rule 9.17.3)
    "DRIFT_OBSERVATION": {
        "SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW",
        "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
        "SPEC_AUDIT",
    },
    # AUTO_COMPACT_PENDING: entered via emergency signal, exits to the recorded
    # resume_state (any non-terminal state). We allow a permissive target set
    # here; the runtime constrains exits via resume_state stored in FSM-STATE.
    "AUTO_COMPACT_PENDING": {
        "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING",
        "SPEC_REGRESSION_CHECK", "SPEC_FROZEN", "IMPLEMENTATION",
        "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY",
        "PRODUCTION_SIGNAL",  # ACT-027：PRODUCTION_SIGNAL 期間觸發 compact 後仍回到監測狀態
        "TOKEN_BUDGET_CRITICAL", "ESCALATION",
    },
}

# States that can only be reached via emergency signals (not through happy path).
# QA Round-3 P2-06: `AUTO_COMPACT_PENDING` removed from this set — it was
# previously reachable from *any* state, including RELEASE / TERMINATED /
# TOKEN_BUDGET_CRITICAL, which makes no operational sense. Entry is now
# constrained via `AUTO_COMPACT_SOURCES` below and the runtime-side guard
# in `FSMRuntime.trigger_auto_compact()`.
_EMERGENCY_TARGETS: Set[str] = {
    "ESCALATION", "TOKEN_BUDGET_CRITICAL", "TERMINATED",
    # Phase G M1 / ACT-034: ESCALATION_FINAL reachable from ESCALATION
    # or AUTO_RECOVERY_ATTEMPT (failure path). Treat as emergency target
    # so transitions never hit TransitionError when forced via runtime guard.
    "ESCALATION_FINAL",
}

# Phase E M4 QA Round-6 P1-5：OBSERVATION_STATES 為「非阻塞觀測狀態」
# 的顯式宣告常數。這些狀態存在期間不應阻擋工具呼叫（對比 _EMERGENCY_TARGETS
# 的 ESCALATION/TERMINATED/TOKEN_BUDGET_CRITICAL 會透過 assert_tool_allowed
# deny 所有 call）。FSMRuntime.assert_tool_allowed 的 block set 邏輯應改為
# 以 _EMERGENCY_TARGETS 為 deny 清單、OBSERVATION_STATES 為顯式 allow 註記，
# 避免未來誤把新觀測狀態（ex: LEARNING_COMMIT）塞入 block set。
OBSERVATION_STATES: Set[str] = frozenset({
    "PRODUCTION_SIGNAL",     # ACT-027 Production Feedback
    "LEARNING_COMMIT",       # ACT-028 Learning Layer
    "HUB_SYNC",              # ACT-030 Cross-Project Learning Hub Sync (Phase F M2)
    "TRAJECTORY_PREDICTED",  # ACT-035 Predictive Halt (Phase G M2)
    "DRIFT_OBSERVATION",     # ACT-040 Continuous Drift Monitor (Phase G M4)
    "SCAFFOLD_GC",           # ACT-055 Scaffold Metabolism (Phase H M5)
    "EVALUATOR_AUDIT",            # ACT-063 Evaluator self-audit (Phase I M1)
    "MONITOR_VIOLATION",          # ACT-064 Runtime monitor violation (Phase I M2)
    "MEMORY_CONSOLIDATION",       # ACT-066 Success crystallization (Phase I M3)
    "PRODUCTION_BEHAVIORAL_SIGNAL",  # ACT-067 Behavioral reality loop (Phase I M3)
    "CAPABILITY_BENCHMARK",       # ACT-076 Capability benchmark (Phase J)
    "SPEC_PATCH_PROPOSAL",        # ACT-078 Spec self-repair (Phase J)
    "SPEC_DEBATE",                # ACT-084 Spec dialectic disambiguation (Phase K M-K2)
    "EXPERIMENT_REPLAY",          # ACT-092 Offline counterfactual replay (Phase L M-L2)
    "AUTOCLAUDE_DELEGATED",       # ACT-172 SDD→AutoClaude delegated execution (Phase Z landing)
})

# Sources legally allowed to transition into AUTO_COMPACT_PENDING.
# Terminal/critical states (RELEASE, TERMINATED, ESCALATION, TOKEN_BUDGET_CRITICAL)
# are deliberately excluded — a compact there is either wasted (RELEASE)
# or a shortcut around guardrails (TOKEN_BUDGET_CRITICAL must escalate).
AUTO_COMPACT_SOURCES: Set[str] = {
    "INIT", "SCENARIO_DETECT", "AGENT_LOAD",
    "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING",
    "SPEC_REGRESSION_CHECK", "SPEC_FROZEN", "IMPLEMENTATION",
    "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY",
    "REMINDER", "RESUME_VERIFICATION",
    # ACT-027：PRODUCTION_SIGNAL 監測期間的長對話也能 compact，但會回到 PRODUCTION_SIGNAL 而非升級
    "PRODUCTION_SIGNAL",
}


RETRY_LIMITS: Dict[str, int] = {
    "SCG_VALIDATION": 3,
    "PR_REVIEW": 5,
    "RTM_VERIFY": 2,
    "SPEC_REGRESSION_CHECK": 2,
}

PR_REVIEW_SAME_PATTERN_THRESHOLD = 3
SPEC_AUDIT_MAX_PER_STAGE = 2
IMPL_MAX_ITERATIONS = 20
IMPL_MAX_CONSECUTIVE_COMPILE_FAIL = 3
IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE = 5
# Phase E / ACT-026：單一 stage 內 AUTO_COMPACT_PENDING 可被觸發的上限
MAX_AUTO_COMPACT_PER_STAGE = 3


def is_transition_allowed(src: str, dst: str) -> bool:
    if dst in _EMERGENCY_TARGETS:
        return True
    # QA Round-3 P2-06: AUTO_COMPACT_PENDING is semi-emergency but gated —
    # only sources in AUTO_COMPACT_SOURCES may enter it.
    if dst == "AUTO_COMPACT_PENDING":
        return src in AUTO_COMPACT_SOURCES
    return dst in _HAPPY_PATH.get(src, set())


def assert_transition(src: str, dst: str) -> None:
    if not is_transition_allowed(src, dst):
        raise TransitionError(f"transition not allowed: {src} -> {dst}")


def next_state_on_gate_pass(gate: str) -> str:
    mapping = {
        "SCG_VALIDATION": "HUMAN_PENDING",
        "SPEC_REGRESSION_CHECK": "SPEC_FROZEN",
        "PR_REVIEW": "RTM_VERIFY",
        "RTM_VERIFY": "RELEASE_READY",
    }
    if gate not in mapping:
        raise KeyError(f"unknown gate: {gate}")
    return mapping[gate]


def next_state_on_gate_fail(gate: str, current_count: int, *, same_pattern_count: int = 0) -> Tuple[str, bool]:
    """Return (next_state, should_escalate)."""
    limit = RETRY_LIMITS.get(gate)
    if limit is None:
        raise KeyError(f"gate {gate} has no retry limit")
    if current_count >= limit:
        return "ESCALATION", True
    if gate == "PR_REVIEW" and same_pattern_count >= PR_REVIEW_SAME_PATTERN_THRESHOLD:
        return "SPEC_AUDIT", False
    if gate == "SCG_VALIDATION":
        return "SPEC_DRAFTING", False
    if gate == "PR_REVIEW":
        return "IMPLEMENTATION", False
    if gate == "RTM_VERIFY":
        return "IMPLEMENTATION", False
    if gate == "SPEC_REGRESSION_CHECK":
        return "HUMAN_PENDING", False
    return "ESCALATION", True


def should_escalate_for_implementation(budget: Dict[str, int]) -> Tuple[bool, Optional[str]]:
    if int(budget.get("consecutive_compile_fail", 0)) >= IMPL_MAX_CONSECUTIVE_COMPILE_FAIL:
        return True, "consecutive_compile_fail exceeded"
    if int(budget.get("current_iteration", 0)) >= IMPL_MAX_ITERATIONS:
        return True, "max_iterations exceeded"
    if int(budget.get("test_fail_without_spec_change", 0)) >= IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE:
        return False, "test_fail_threshold → SPEC_AUDIT"
    return False, None


def all_states() -> Iterable[str]:
    return list(_HAPPY_PATH.keys()) + list(_EMERGENCY_TARGETS)
