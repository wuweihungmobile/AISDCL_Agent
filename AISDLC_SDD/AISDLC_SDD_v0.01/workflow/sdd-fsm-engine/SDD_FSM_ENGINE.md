# SDD 形式化狀態機引擎
# SDD Formal State Machine Engine

**版本**: v1.0
**建立日期**: 2026-04-18
**文件類型**: 工作流程規格（Workflow Specification）
**所屬分類**: workflow/sdd-fsm-engine/
**對應藍圖**: build/planning/active/SDD_improving_Automation_01.md（Phase A）

---

## 🎯 目的

將 AISDLC-SDD 的隱性工作流程，升級為**形式化有限狀態機（FSM）**。
確保每個開發狀態都有明確的轉換條件、重試上界與退場路徑，達到圖靈完備的閉環能力。

---

## 📋 狀態定義

```yaml
states:

  INIT:
    type: initial
    description: "讀取 AISDLC_SDD_INIT.md，初始化框架配置"
    timeout: none
    on_enter: "載入 auto_load_config"

  SCENARIO_DETECT:
    type: transitional
    description: "識別情境類型（greenfield/brownfield/...）"
    timeout: none

  AGENT_LOAD:
    type: transitional
    description: "依情境載入 Primary Agents"
    timeout: none

  INTENT_DECOMPOSITION:
    type: gatekeep
    description: "意圖分解閘（Phase K M-K1 / ACT-082）— 將 high-level intent 自主分解為 acyclic spec-DAG，餵 value_planner"
    entry_allowed_from: ["AGENT_LOAD"]
    exit_allowed_to: ["BACKLOG_PRIORITIZED", "HUMAN_PENDING"]
    bounded_by:
      - "Rule 9.23.1：節點/迭代硬上限 SDD_INTENT_MAX_NODES（clamp[4,128]，預設 32）"
      - "spec-DAG 必 acyclic（偵測環即 underspecified）"
    on_decomposed: BACKLOG_PRIORITIZED   # 候選餵 value_planner 排 ROI，最高者人工 signoff（Rule 9.23.2）
    on_underspecified: HUMAN_PENDING      # 意圖過模糊/成環/觸頂，請人工澄清（Rule 8）

  SPEC_DEBATE:
    type: observation                     # Phase K M-K2 / ACT-084：advisory transient（非阻塞）
    description: "規格辯證消歧（SCG-0 子步）— 兩隔離詮釋對 AmbiguityScorer near-threshold AC 提對立讀法，量化分歧"
    entry_rule: "FSMRuntime.enter_spec_debate()（從 SCG_VALIDATION，AmbiguityScorer 落 near-threshold band 時）"
    entry_allowed_from: ["SCG_VALIDATION"]
    exit_allowed_to: ["SCG_VALIDATION", "HUMAN_PENDING"]
    bounded_by:
      - "Rule 9.23.3：輪數硬上限 SDD_SPEC_DEBATE_ROUNDS（clamp[1,8]，預設 4）；強度凍結 SPEC_DEBATE_PROFILE_VERSION"
    on_consensus: SCG_VALIDATION          # 兩詮釋收斂，續跑 SCG
    on_divergence: HUMAN_PENDING           # 兩詮釋互斥，advisory 導人工澄清（Rule 9.23.4，不自動改 AC）

  EXPERIMENT_REPLAY:
    type: observation                     # Phase L M-L2 / ACT-092：離線反事實 advisory transient（非阻塞）
    description: "離線反事實實驗（補丁送審前）— 對歷史失敗語料（FPL/chaos/PBS-DRIFT/decision_trace）反事實重放 spec_patch，量化『此補丁可擋住過去 X/Y 筆同源失敗』+ 反例"
    entry_rule: "FSMRuntime.enter_experiment_replay()（從 SPEC_PATCH_PROPOSAL，補丁草擬後、送 HUMAN_PENDING 前）"
    entry_allowed_from: ["SPEC_PATCH_PROPOSAL"]
    exit_allowed_to: ["SPEC_PATCH_PROPOSAL", "HUMAN_PENDING"]
    bounded_by:
      - "Rule 9.24.4：重放筆數硬上限 SDD_REPLAY_MAX_CASES（clamp[5,200]，預設 50）；純離線、零外網（守 OPEN-10.6）"
    on_done: SPEC_PATCH_PROPOSAL          # 命中率證據附上，續送人工 approve/reject（advisory，不自動 approve）
    on_inconclusive: HUMAN_PENDING        # 歷史語料不足無法判定，導人工裁決（Rule 8）

  SPEC_DRAFTING:
    type: workstate
    description: "規格撰寫工作狀態"
    max_iterations: 3
    retry_counter: true
    timeout: none

  SCG_VALIDATION:
    type: gatekeep
    description: "Spec Compliance Gate 自動驗證（🔷）"
    retry_limit: 3
    retry_counter: true
    on_retry_exceeded: ESCALATION
    includes_slv: true    # 在 SCG-0 / SCG-3 前執行 Spec Logical Validator

  HUMAN_PENDING:
    type: blocking
    description: "等待人工確認（🔴 阻塞狀態）"
    timeout_hours: 72
    escalation_hours: 168
    on_timeout_72h: REMINDER
    on_timeout_168h: ESCALATION

  REMINDER:
    type: notification
    description: "逾時提醒，不阻塞主流程"
    auto_return_to: HUMAN_PENDING
    action: "發送提醒通知給負責人"

  SPEC_REGRESSION_CHECK:
    type: gatekeep
    description: "SPEC_FROZEN 前的回歸閘（Phase D / ACT-014）"
    triggered_if: "本 Stage 任一 current_count > 0（表示有過重試）"
    action:
      - "讀取本 Stage 歷次 retry 的 failure_reason"
      - "重跑對應的 SLV 規則（若 reason 可映射）"
      - "比對此次 Spec 與上次失敗時的關鍵條文差異"
      - "偵測『僅改字面／未動語義』的表面修正（superficial fix）"
    on_regression_detected:
      - "回退至 HUMAN_PENDING，標記 spec_regression_check.superficial_fix=true"
      - "cumulative_history.superficial_fix_count++"
      - "若 superficial_fix_count > 2 → ESCALATION（人工多次表面修正，需深度審查）"
    on_pass:
      - "正式進入 SPEC_FROZEN"
    retry_limit: 2
    on_retry_exceeded: ESCALATION

  SPEC_FROZEN:
    type: milestone
    description: "規格凍結里程碑"
    on_enter:
      - "執行 stage-compaction（強制上下文壓縮）"
      - "確認所有文件已持久化至 docs/ 目錄"
      - "重置所有 retry_counter（current_count → 0）"
      - "寫入 FSM-STATE-{project}.yaml（更新 cumulative_history，不清除歷史）"
      - "cumulative_history.total_spec_frozen_count++"
    cumulative_history_rule: |
      SPEC_FROZEN 只重置 current_count，不清除 cumulative_history。
      若 total_scg_retries_all_time > 10，在 SCG 報告中輸出 AUDIT 警告。
      若 cumulative_history.superficial_fix_count > 2 在 Session 跨越仍會觸發 ESCALATION。

  IMPLEMENTATION:
    type: workstate
    description: "開發實作工作狀態"
    context_checkpoint: true
    implementation_budget:
      max_iterations: 20           # 整個 IMPLEMENTATION 階段最多 20 次 compile+test 迭代
      max_consecutive_compile_fail: 3   # 連續編譯失敗超過 3 次 → ESCALATION
      max_test_fail_without_spec_change: 5  # 未修改 Spec 但測試持續失敗 5 次 → SPEC_AUDIT
      tracking_file: "build/reports/fsm/FSM-STATE-{project}.yaml"
    on_budget_exceeded:
      compile_fail: ESCALATION
      test_fail: SPEC_AUDIT

  PR_REVIEW:
    type: gatekeep
    description: "SCG-4 實作一致性驗證"
    retry_limit: 5
    retry_counter: true
    pattern_detection: true
    same_pattern_threshold: 3
    on_same_pattern_3x: SPEC_AUDIT
    on_retry_exceeded: ESCALATION

  SPEC_AUDIT:
    type: diagnostic
    description: "規格邏輯審查（PR_REVIEW 異常觸發）"
    max_executions_per_stage: 2     # 🔒 每個 Stage 最多執行 2 次，防止 PR_REVIEW ↔ SPEC_AUDIT 震盪
    cumulative_counter: "fsm_state.retry_history.PR_REVIEW.spec_audit_count"
    on_max_exceeded: ESCALATION     # 超過 2 次仍無解 → 實作品質問題，需人工介入
    action: |
      1. 讀取原始 AC 定義
      2. 比對 Test Contract assertion
      3. 執行 Spec Logical Validator（SLV-001~006）
      4. 識別矛盾點
      5. 遞增 spec_audit_count，若已達上限則進入 ESCALATION
    on_contradiction_confirmed: ESCALATION
    on_no_contradiction: PR_REVIEW  # 重置 retry_count（不重置 spec_audit_count）

  RTM_VERIFY:
    type: gatekeep
    description: "SCG-5 需求追溯完整性驗證"
    retry_limit: 2
    on_retry_exceeded: ESCALATION

  RELEASE_READY:
    type: milestone
    description: "SCG-6 發布就緒"

  ESCALATION:
    type: blocking
    description: "強制人工介入（不可自動退出）"
    cannot_auto_exit: true
    on_enter:
      - "產出 Abort Report（見 SDD_ABORT_REPORT_TEMPLATE.md）"
      - "記錄：觸發原因、當前狀態、已消耗資源、可恢復點"
      - "通知負責人（sa-analyst / architect / tech-lead）"
    resolution:
      human_abort: TERMINATED
      human_fix_and_resume: RESUME_VERIFICATION   # 必經此閘，不可直接回工作狀態

  RESUME_VERIFICATION:
    type: gatekeep
    description: "Session 恢復前的強制驗證閘（Phase D / ACT-019）"
    triggered_by:
      - "ESCALATION → 人工修復後嘗試恢復"
      - "TERMINATED 後的新 Session 透過 Context Snapshot 恢復"
    action:
      step_1: "讀取 CONTEXT-SNAPSHOT-{date}.md 取得 abort_reason"
      step_2: "針對 abort_reason 類型重跑對應驗證"
      step_3: "比對此次結果與上次失敗原因（相同 scg_gate / 相同 SLV / 相同 classification）"
      step_4_branch:
        same_failure_pattern:
          action: "警告人工：修正未生效，請勿確認恢復"
          transition: HUMAN_PENDING   # 重新等待人工
          increment: "cumulative_history.resume_blocked_count"
        different_or_resolved:
          transition: "回對應的可恢復狀態（SPEC_DRAFTING / IMPLEMENTATION / PR_REVIEW）"
          reset: "current_count（保留 cumulative_history）"
    on_retry_exceeded: ESCALATION      # 連續 2 次 same pattern → 再次 ESCALATION（不進入死循環）

  TERMINATED:
    type: terminal
    description: "優雅中止"
    on_enter:
      - "產出最終 Abort Report 存至 build/reports/abort/"
      - "保存當前 Context Snapshot"
      - "標記可恢復點供後續 conversation 接手"

  AUTO_COMPACT_PENDING:
    type: recoverable_pause
    description: "Token 預算達 90%，已自動產出 Snapshot，等待 Claude 呼叫 /stage-compaction"
    on_enter:
      - "Hook 自動寫入 CONTEXT-SNAPSHOT-{date}-auto.md（無需 Claude 參與）"
      - "記錄 resume_state（轉入前的狀態）至 FSM-STATE.yaml"
      - "下一次 PreToolUse 僅允許 Skill(stage-compaction)、Read(docs/, build/)、Write(snapshot)"
    exit_on: "stage-compaction Skill 完成"
    on_exit:
      - "歸零 CONTEXT-LEDGER 當日 cumulative_tokens（保留 entries 歷史）"
      - "FSM 轉回 resume_state"

  TOKEN_BUDGET_CRITICAL:
    type: emergency
    description: "Token 預算嚴重不足（> 95%）— AUTO_COMPACT 失敗後的最後防線"
    on_enter:
      - "立即暫停所有工作"
      - "產出 Context Snapshot（當前狀態、下一步、未完成項目）"
    auto_transition: ESCALATION

  RELEASE:
    type: terminal
    description: "成功發布"

  PRODUCTION_SIGNAL:
    type: observation               # Phase E M3 / ACT-027：非阻塞監測狀態
    description: "Post-release 生產回饋層 — 接收 SLO violation，漂移達閾值產出 PBS-DRIFT 報告"
    entry_rule: "必須透過 FSMRuntime.enter_production_signal() 顯式進入（RELEASE 為 happy-path terminal，刻意不列為 is_transition_allowed 合法 edge）"
    entry_allowed_from: ["RELEASE", "RELEASE_READY", "PRODUCTION_SIGNAL"]
    exit_allowed_to: ["SPEC_DRAFTING", "RELEASE"]
    tool_call_policy: "non-blocking — assert_tool_allowed 不阻擋；Write/Edit spec 路徑仍受 _STATES_ALLOWING_SPEC_WRITE 規則限制"
    side_effects:
      - "ingest_slo_violation 寫入 build/reports/fsm/PBS-DRIFT-{date}.yaml"
      - "24h 內同 NFR ≥ 3 次違反 → 產出 docs/06_quality/PBS-DRIFT-{NFR}-{date}.md"
      - "session_start.py scan_inbox 自動更新 FSM-STATE.production_signal_tracking"

  LEARNING_COMMIT:
    type: observation               # Phase E M4 / ACT-028：Learning Layer 非阻塞背景狀態
    description: "SLV 規則學習層 — ESCALATION 根因為未捕獲 Spec 歧義時，自動從 FPL 產出 SLV 草案，待人工 review"
    entry_rule: "必須透過 FSMRuntime.enter_learning_commit(fpl_id, proposed_slv_id) 顯式進入"
    entry_allowed_from: ["ESCALATION", "TERMINATED", "RELEASE", "PRODUCTION_SIGNAL"]
    exit_allowed_to: ["RELEASE", "ESCALATION"]

  HUB_SYNC:
    type: observation               # Phase F M2 / ACT-030：Cross-Project Learning Hub 非阻塞觀測狀態
    description: "Hub Sync — pull external rules / push anonymized artifacts；不阻擋 tool calls"
    entry_rule: "必須透過 FSMRuntime.enter_hub_sync(direction='pull'|'push') 顯式進入"
    entry_allowed_from: ["INIT", "SCENARIO_DETECT", "SPEC_DRAFTING", "SPEC_FROZEN", "RELEASE", "RELEASE_READY", "LEARNING_COMMIT", "HUMAN_PENDING"]
    exit_allowed_to: ["INIT", "SCENARIO_DETECT", "SPEC_DRAFTING", "SPEC_FROZEN", "HUMAN_PENDING", "RELEASE", "RELEASE_READY", "LEARNING_COMMIT"]
    tool_call_policy: "non-blocking — assert_tool_allowed 不阻擋；write 路徑由 governance（HUB-GOVERNANCE-SPEC）規範，FSM 不再次限制"
    side_effects:
      - "hub_sync.HubSyncClient.pull/push 寫入 build/reports/hub/*"
      - "hub_sync_tracking 記錄 {direction, endpoint, resume_state, outcome}"
      - "exit_hub_sync('success') → 回 resume_state；'partial' → HUMAN_PENDING（衝突待 review）；'failed' → 回 resume_state（不升 ESCALATION）"
    tool_call_policy: "non-blocking — assert_tool_allowed 不阻擋；write 僅允許 .claude/skills/spec-logical-validator/rules/*.yaml（規則草案路徑）與 knowledge/failure-patterns/*.md（FPL 條目）"
    side_effects:
      - "slv_generator.propose_slv_from_fpl(fpl) → rules/SLV-NNN.yaml（trust_level: proposed）"
      - "learning_commit_tracking 記錄 {fpl_id, proposed_slv_id, review_status, reviewed_at}"
      - "exit_learning_commit('approved') → RELEASE；exit_learning_commit('rejected') → ESCALATION（人工 triage）"
    trust_level_contract:
      - "新規則預設 trust_level: proposed，僅輸出 Advisory 不阻塞 SCG"
      - "升級為 verified 必經人工 review（填 reviewed_by / reviewed_at 並改 trust_level）"
      - "verified 規則不得被 slv_generator 自動覆寫（RuleOverwriteProtected）"

  # ===== Phase G M1 / ACT-033/034：Self-Healing Layer =====
  AUTO_RECOVERY_ATTEMPT:
    type: recovery                  # 1-shot bounded auto-recovery；非阻塞但僅允許 recovery 相關操作
    description: "DiagnosticAgent 確認為 transient（CI timeout / network flap / rate limit）後的單次自動復原"
    entry_rule: "必須透過 FSMRuntime.enter_auto_recovery(diagnostic_result) 顯式進入；diagnostic.auto_recoverable 必為 true 且 confidence ≥ 0.7"
    entry_allowed_from: ["ESCALATION"]
    exit_allowed_to: ["SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK", "ESCALATION_FINAL"]
    bounded_by:
      - "Rule 9.14.1：全 session 最多 3 次 AUTO_RECOVERY_ATTEMPT"
      - "Rule 9.14.2：同一 escalation_reason 全 session 僅允許 1 次"
      - "Rule 9.14.3：diagnostic.category=structural 禁止進入"
      - "Rule 9.14.4：失敗即 ESCALATION_FINAL，不可再嘗試任何 recovery"
    side_effects:
      - "auto_recovery.try_recovery 執行 playbook（wait_and_rerun / exponential_backoff / wait_per_retry_after）"
      - "recovery_state 持久化 {attempt_count, per_reason_count, resume_state, diagnostic, entered_at}"
      - "exit_auto_recovery('success') → resume_state；'fail' → ESCALATION_FINAL"

  ESCALATION_FINAL:
    type: terminal-like             # 阻擋型，與 ESCALATION 同 _BLOCKING_STATES；唯有人工可移出
    description: "Auto-recovery 失敗 OR DiagnosticAgent 判為 structural 後的最終升級點；不允許再次 auto-recovery"
    entry_rule: "經由 ESCALATION → ESCALATION_FINAL（structural）或 AUTO_RECOVERY_ATTEMPT → ESCALATION_FINAL（recovery 失敗）"
    entry_allowed_from: ["ESCALATION", "AUTO_RECOVERY_ATTEMPT"]
    exit_allowed_to: ["TERMINATED", "RESUME_VERIFICATION"]
    blocking: true                  # PreToolUse hook 阻擋所有工具呼叫（與 ESCALATION 同等）
    side_effects:
      - "snapshot.save_abort_report 寫入 build/reports/abort/ABORT-{date}-final.md（含 diagnostic + recovery_state）"
      - "等待人工 RESUME_VERIFICATION 或 TERMINATED 決策"

  # ===== Phase G M2 / ACT-035/036：Predictive Halt Layer =====
  TRAJECTORY_PREDICTED:
    type: observation               # 非阻塞觀測態（同 PRODUCTION_SIGNAL / LEARNING_COMMIT / HUB_SYNC）
    description: "TrajectoryPredictor 從 retry_history + decision_trace + ledger drift 預測「將崩」，提早切換策略"
    entry_rule: "由 retry-prone gate 在 retry_count ≥ 1 時呼叫 enter_trajectory_predicted（Rule 9.15.1）；caller 帶 PredictedAction"
    entry_allowed_from: ["IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"]
    exit_allowed_to: ["IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK", "SPEC_AUDIT", "ESCALATION"]
    constraints:
      - "Rule 9.15.1：retry_count ≥ 1 才允許進入"
      - "Rule 9.15.2：abort_early 必須 confidence ≥ 0.8"
      - "Rule 9.15.3：false-positive 必寫 build/reports/fsm/PREDICTOR-MISS-{date}.yaml"
      - "Rule 9.15.4：同 stage switch_to_audit ≤ 1 次"
    side_effects:
      - "predictor.predict() 評估 4 信號 (S1~S4)，回 PredictedAction"
      - "exit_trajectory_predicted(decision)：continue→resume_state；switch_to_audit→SPEC_AUDIT；abort_early→ESCALATION"

  # ===== Phase G M4 / ACT-040：Continuous Drift Monitor =====
  DRIFT_OBSERVATION:
    type: observation               # 非阻塞觀測態（同 PRODUCTION_SIGNAL / LEARNING_COMMIT / HUB_SYNC / TRAJECTORY_PREDICTED）
    description: "PostCommit drift hook 偵測 spec↔code drift_score ≥ 0.3 時進入；連續 3 次累積後升 SPEC_AUDIT"
    entry_rule: "由 enter_drift_observation(commit_sha, drift_score) 呼叫；advisory only，commit 不被阻擋（Rule 9.17.1）"
    entry_allowed_from: ["SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK"]
    exit_allowed_to: ["SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK", "SPEC_AUDIT"]
    constraints:
      - "Rule 9.17.1：PostCommit hook 為 advisory，絕不阻擋 commit；budget < 2s"
      - "Rule 9.17.2：drift_score ≥ 0.3 → 進入 DRIFT_OBSERVATION，要求下一次 PR_REVIEW 額外驗證"
      - "Rule 9.17.3：連續 3 commits drift_score ≥ 0.3 → 自動 exit_drift_observation('switch_to_audit') 升 SPEC_AUDIT"
      - "Rule 9.17.4：每日 02:30 UTC 產出 build/reports/drift/DAILY-{date}.md 滾動 7 天"
    side_effects:
      - "compute_drift(commit_sha)：API drift + Type drift 加權"
      - "exit_drift_observation(decision)：continue→resume_state；switch_to_audit→SPEC_AUDIT"
```

---

## 🔄 狀態轉換表

### 正向路徑（Happy Path）

| 來源狀態 | 條件 | 目標狀態 |
|---------|------|---------|
| INIT | 完成 | SCENARIO_DETECT |
| SCENARIO_DETECT | 情境已識別 | AGENT_LOAD |
| AGENT_LOAD | Primary Agents 載入完成 | SPEC_DRAFTING |
| AGENT_LOAD | Phase I：價值目標自選（ACT-068） | BACKLOG_PRIORITIZED |
| AGENT_LOAD | Phase K：意圖分解閘（ACT-082） | INTENT_DECOMPOSITION |
| INTENT_DECOMPOSITION | 分解成 acyclic spec-DAG（ACT-082） | BACKLOG_PRIORITIZED |
| INTENT_DECOMPOSITION | 意圖過模糊/成環/觸頂無法收斂（ACT-082） | HUMAN_PENDING |
| BACKLOG_PRIORITIZED | 人工 signoff 選定最高 ROI 目標（ACT-068） | SPEC_DRAFTING |
| SPEC_DRAFTING | 規格草稿完成 | SCG_VALIDATION |
| SCG_VALIDATION | PASS（+ SLV PASS） | HUMAN_PENDING |
| HUMAN_PENDING | 人工確認通過，但本 Stage 有重試歷史（current_count > 0） | SPEC_REGRESSION_CHECK |
| HUMAN_PENDING | 人工確認通過，且無重試歷史 | SPEC_FROZEN |
| SPEC_REGRESSION_CHECK | PASS（非表面修正） | SPEC_FROZEN |
| SPEC_REGRESSION_CHECK | 偵測到表面修正 | HUMAN_PENDING（superficial_fix_count++） |
| SPEC_REGRESSION_CHECK | superficial_fix_count > 2 | ESCALATION |
| SPEC_FROZEN | Compaction 完成 | IMPLEMENTATION（或下一 Stage SPEC_DRAFTING） |
| SPEC_FROZEN | Phase H：強制走測試合約談判閘 | TEST_CONTRACT_NEGOTIATED |
| TEST_CONTRACT_NEGOTIATED | Dev/QA 對 oracle 達成共識並簽署（ACT-049） | IMPLEMENTATION |
| TEST_CONTRACT_NEGOTIATED | 規格不夠明確無法定 oracle | SPEC_DRAFTING |
| IMPLEMENTATION | 實作完成 | PR_REVIEW |
| IMPLEMENTATION | Phase H：強制走執行接地評估閘 | EXECUTION_EVALUATION |
| IMPLEMENTATION | Phase I：執行前先過安全硬化閘（ACT-061） | SANDBOX_HARDENING_GATE |
| SANDBOX_HARDENING_GATE | image/簽章/lockfile/self-STRIDE 通過（ACT-061） | EXECUTION_EVALUATION |
| SANDBOX_HARDENING_GATE | 硬化政策違反（sandbox_policy_violation） | ESCALATION |
| EXECUTION_EVALUATION | 沙箱實跑 verdict=pass（ACT-045） | PR_REVIEW |
| EXECUTION_EVALUATION | runtime fail（沿用 EXEC_EVAL_LIMIT retry） | IMPLEMENTATION |
| EXECUTION_EVALUATION | 執行揭露 spec 缺陷（如 P95<0 不可滿足） | SPEC_AUDIT |
| EXECUTION_EVALUATION | Phase J：verdict=pass 後改走對抗判官閘（ACT-074） | ADVERSARIAL_EVALUATION |
| ADVERSARIAL_EVALUATION | robust：N 輪攻擊無破（ACT-074） | PR_REVIEW |
| ADVERSARIAL_EVALUATION | counterexample：違反已宣告性質/fuzz crash（計入 retry） | IMPLEMENTATION |
| ADVERSARIAL_EVALUATION | spec_gap：違反隱含 latent 關係（AC 漏寫） | SPEC_AUDIT |
| PR_REVIEW | PASS | RTM_VERIFY |
| RTM_VERIFY | PASS | RELEASE_READY |
| RELEASE_READY | SCG-6 通過 | RELEASE |
| PRODUCTION_SIGNAL | Drift 採納（sa-analyst 判定 spec 需更新） | SPEC_DRAFTING |
| PRODUCTION_SIGNAL | Drift 僅為告知（無需 re-spec） | RELEASE |
| LEARNING_COMMIT | 人工 review approved（規則升級為 verified） | RELEASE |
| LEARNING_COMMIT | 人工 review rejected（提案不採納） | ESCALATION |
| HUB_SYNC | success（pull/push 完成無衝突） | resume_state（INIT / SCENARIO_DETECT / SPEC_DRAFTING / SPEC_FROZEN / RELEASE / RELEASE_READY / LEARNING_COMMIT）|
| HUB_SYNC | partial（衝突或 quarantine） | HUMAN_PENDING |
| HUB_SYNC | failed（Hub 失效，timeout/500/GPG fail） | resume_state（不升 ESCALATION）|
| SCAFFOLD_GC | GC 完成無需動作（continue，ACT-055） | RELEASE |
| SCAFFOLD_GC | GC 發現規格層需修正 | SPEC_DRAFTING |
| EVALUATOR_AUDIT | 判官自審無漂移，繼續評估（ACT-063） | EXECUTION_EVALUATION |
| EVALUATOR_AUDIT | 校準完成（人工 gate）僅告知 | RELEASE |
| EVALUATOR_AUDIT | OQS/oracle 漂移需重訂規格 | SPEC_DRAFTING |
| MEMORY_CONSOLIDATION | sleep-phase 結晶完成（ACT-066） | RELEASE |
| MEMORY_CONSOLIDATION | 結晶揭露規格層缺口 | SPEC_DRAFTING |
| PRODUCTION_BEHAVIORAL_SIGNAL | behavioral 偏差僅告知（ACT-067） | RELEASE |
| PRODUCTION_BEHAVIORAL_SIGNAL | 偏差需 re-spec | SPEC_DRAFTING |
| PRODUCTION_BEHAVIORAL_SIGNAL | 偏差累積成 FPL 草案 | LEARNING_COMMIT |
| CAPABILITY_BENCHMARK | done：能力量測完成（ACT-076） | RELEASE |
| CAPABILITY_BENCHMARK | respec：能力量測揭露規格層缺口 | SPEC_DRAFTING |
| SPEC_PATCH_PROPOSAL | drafted：產出 SPEC-PATCH 草案待人工 approve（ACT-078） | HUMAN_PENDING |
| SPEC_PATCH_PROPOSAL | nodraft：無法草擬 / 同 AC 超限（≤2） | ESCALATION |
| SPEC_DEBATE | consensus：兩詮釋收斂（ACT-084） | SCG_VALIDATION |
| SPEC_DEBATE | divergence：兩詮釋互斥，人工澄清（ACT-084） | HUMAN_PENDING |
| SPEC_PATCH_PROPOSAL | Phase L：補丁送審前過離線反事實重放（ACT-092） | EXPERIMENT_REPLAY |
| EXPERIMENT_REPLAY | done：歷史命中率證據附上，續送人工（ACT-092） | SPEC_PATCH_PROPOSAL |
| EXPERIMENT_REPLAY | inconclusive：歷史語料不足，導人工裁決（ACT-092） | HUMAN_PENDING |

### 錯誤路徑（Error Paths）

| 來源狀態 | 條件 | 目標狀態 |
|---------|------|---------|
| SCG_VALIDATION | FAIL，retry_count < 3 | SPEC_DRAFTING（retry_count++） |
| SCG_VALIDATION | FAIL，retry_count ≥ 3 | ESCALATION |
| HUMAN_PENDING | timeout = 72h | REMINDER |
| HUMAN_PENDING | timeout = 168h | ESCALATION |
| PR_REVIEW | FAIL，retry_count < 5 且 same_pattern < 3 | IMPLEMENTATION（retry_count++，重新實作） |
| IMPLEMENTATION | test_fail_without_spec_change ≥ 5 | SPEC_AUDIT（audit_count++，QA Round-3 P1-01） |
| PR_REVIEW | FAIL，same_pattern × 3 | SPEC_AUDIT |
| PR_REVIEW | FAIL，retry_count ≥ 5 | ESCALATION |
| SPEC_AUDIT | 矛盾確認 | ESCALATION |
| SPEC_AUDIT | 無矛盾 | PR_REVIEW（retry_count 重置） |
| RTM_VERIFY | FAIL，retry_count < 2 | IMPLEMENTATION（retry_count++，補實作） |
| RTM_VERIFY | FAIL，retry_count ≥ 2 | ESCALATION |
| 任意狀態（非 AUTO_COMPACT_PENDING） | Token Budget ≥ 90% 且 < 95% | AUTO_COMPACT_PENDING（記錄 resume_state） |
| AUTO_COMPACT_PENDING | stage-compaction 完成 | resume_state（歸零 ledger cumulative） |
| AUTO_COMPACT_PENDING | 單一 stage count_per_stage > 3（ACT-026） | ESCALATION |
| AUTO_COMPACT_PENDING | Token Budget ≥ 95% | TOKEN_BUDGET_CRITICAL → ESCALATION |
| 任意狀態 | Token Budget ≥ 95% | TOKEN_BUDGET_CRITICAL → ESCALATION |
| 任意非 terminal 狀態 | runtime monitor 偵測 .tla safety invariant 破壞（ACT-064） | MONITOR_VIOLATION → ESCALATION |
| ESCALATION | 人工決定中止 | TERMINATED |
| ESCALATION | 人工修復後恢復（有可恢復狀態） | RESUME_VERIFICATION |
| ESCALATION | DiagnosticAgent 判 transient 且 confidence ≥ 0.7（Phase G M1 / ACT-033） | AUTO_RECOVERY_ATTEMPT |
| ESCALATION | DiagnosticAgent 判 structural OR Rule 9.14 上限耗盡（Phase G M1 / ACT-034） | ESCALATION_FINAL |
| AUTO_RECOVERY_ATTEMPT | recovery success（gate-resumable target） | SPEC_DRAFTING |
| AUTO_RECOVERY_ATTEMPT | recovery success（IMPLEMENTATION 階段） | IMPLEMENTATION |
| AUTO_RECOVERY_ATTEMPT | recovery success（PR_REVIEW 階段） | PR_REVIEW |
| AUTO_RECOVERY_ATTEMPT | recovery success（RTM_VERIFY 階段） | RTM_VERIFY |
| AUTO_RECOVERY_ATTEMPT | recovery success（SCG_VALIDATION 階段） | SCG_VALIDATION |
| AUTO_RECOVERY_ATTEMPT | recovery success（SPEC_REGRESSION_CHECK 階段） | SPEC_REGRESSION_CHECK |
| AUTO_RECOVERY_ATTEMPT | recovery fail OR 上限耗盡（Rule 9.14.4） | ESCALATION_FINAL |
| ESCALATION_FINAL | 人工決定中止 | TERMINATED |
| ESCALATION_FINAL | 人工修復後恢復 | RESUME_VERIFICATION |
| TRAJECTORY_PREDICTED | predicted=continue（resume IMPLEMENTATION） | IMPLEMENTATION |
| TRAJECTORY_PREDICTED | predicted=continue（resume PR_REVIEW） | PR_REVIEW |
| TRAJECTORY_PREDICTED | predicted=continue（resume RTM_VERIFY） | RTM_VERIFY |
| TRAJECTORY_PREDICTED | predicted=continue（resume SCG_VALIDATION） | SCG_VALIDATION |
| TRAJECTORY_PREDICTED | predicted=continue（resume SPEC_REGRESSION_CHECK） | SPEC_REGRESSION_CHECK |
| TRAJECTORY_PREDICTED | predicted=switch_to_audit（≥2 信號） | SPEC_AUDIT |
| DRIFT_OBSERVATION | continue（單次 drift, advisory）→ resume IMPLEMENTATION | IMPLEMENTATION |
| DRIFT_OBSERVATION | continue → resume PR_REVIEW | PR_REVIEW |
| DRIFT_OBSERVATION | continue → resume RTM_VERIFY | RTM_VERIFY |
| DRIFT_OBSERVATION | continue → resume SCG_VALIDATION | SCG_VALIDATION |
| DRIFT_OBSERVATION | continue → resume SPEC_REGRESSION_CHECK | SPEC_REGRESSION_CHECK |
| DRIFT_OBSERVATION | continue → resume SPEC_DRAFTING | SPEC_DRAFTING |
| DRIFT_OBSERVATION | continue → resume SPEC_FROZEN | SPEC_FROZEN |
| DRIFT_OBSERVATION | switch_to_audit（連續 3 commits ≥ 0.3，Rule 9.17.3） | SPEC_AUDIT |

---

## 🗺️ 狀態圖

```
                   ┌──────────────────────────────────────────────────────┐
                   │              TOKEN BUDGET GOVERNOR                   │
                   │ 70% warn → 85% compress → 90% AUTO → 95% HARD-STOP   │
                   └────────────────────┬─────────────────────────────────┘
                                        │ 90% → AUTO_COMPACT_PENDING → (compact ok) resume_state
                                        │ 95% → TOKEN_BUDGET_CRITICAL → ESCALATION
                                        │
INIT → SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING ◄────────────────┐
                                          │                            │
                                   SCG_VALIDATION ──[SLV check]       │
                                   /           \                       │
                               [PASS]      [FAIL×<3] ────────────────►┘
                                 │                 \
                                 │            [FAIL×≥3]
                                 ↓                 ↓
                          HUMAN_PENDING        ESCALATION ◄──────────┐
                          /    |    \          /       \              │
                    [ok] [72h][168h] →REMINDER [abort] [fix+resume]  │
                      ↓               ↓          ↓         ↓         │
                 SPEC_FROZEN    HUMAN_PENDING  TERMINATED (state)     │
              (COMPACTION HERE)                                       │
                      ↓                                               │
               IMPLEMENTATION                                         │
                      ↓                                               │
                  PR_REVIEW ──[pattern×3]──► SPEC_AUDIT               │
                 /    |    \                /          \               │
            [PASS] [<5×] [≥5×]      [no_contra]  [contra]            │
               ↓     │     ↓             ↓              ↓             │
          RTM_VERIFY  │ ESCALATION  PR_REVIEW(reset) ESCALATION ─────►┘
               ↓      │
       RELEASE_READY  └──► PR_REVIEW (retry_count++)
               ↓
            RELEASE
```

---

## 📏 Retry Budget 速查

| 閘門 | 最大重試次數 | 超限後行動 |
|------|------------|---------|
| SCG_VALIDATION | 3次 | → ESCALATION |
| PR_REVIEW | 5次 | → ESCALATION |
| PR_REVIEW（相同模式） | 3次 | → SPEC_AUDIT |
| RTM_VERIFY | 2次 | → ESCALATION |
| HUMAN_PENDING | 72h → 提醒；168h → ESCALATION | — |

---

## 🧭 Phase E M2 — 閉環品質鏈（ACT-025/024/021/020）

### 1. Decision Trace（ACT-025）
每次 `FSMRuntime.transition(dst, reason=..., spec_refs=..., trigger=...)` 必須附帶至少 `reason` 與 `trigger`，寫入 `state.decision_trace`（上限 50 筆）。溢位自動 flush 至 `decision_trace_flushed`。

- Snapshot（`snapshot.py`）自動附加「最近 20 筆 Decision Trace」區段
- `session_start.py` 注入最近 5 筆到 additionalContext，復位後 Claude 可立即掌握決策鏈
- Schema 詳見 [FSM-STATE-TEMPLATE.yaml](../../build/reports/fsm/FSM-STATE-TEMPLATE.yaml)

### 2. Ledger 精準度（ACT-024）
`tools/fsm_runtime/conversation_ledger.py` 為唯一 token 估算入口：

| 工具 | 估算公式 |
|------|---------|
| Read | `(size + line_count * 8) // 4`（含 cat -n 行號開銷） |
| Bash | `len(cmd) // 4` |
| Task | `estimate_conversation_overhead(1) + prompt// 4` |
| Write/Edit | `len(content \| new_string) // 4` |

- PostToolUse 每 10 次 tool call 追加 `phase=conv-overhead` 條目（300 tokens/turn × N）
- Calibration sample 存於 `build/reports/fsm/LEDGER-CALIBRATION.yaml`；drift_pct rolling 10 筆

### 3. 語意相同 Pattern（ACT-021）
`tools/fsm_runtime/pattern_matcher.py` 取代原先字串相等比對：

- `normalize()` 去除時間戳、路徑、數字、停用詞；將 `exceeded / above / > / over` 映射到 `gt`，`under / below / <` 映射到 `lt`
- `similarity()` 取 `SequenceMatcher.ratio()` 與 token Jaccard 的最大值
- `is_same_pattern()` 預設 threshold 0.75，可由 `SDD_PATTERN_MATCH_THRESHOLD` 覆寫
- PR_REVIEW 階段用 `is_same_pattern(last_reason, current_reason)` 判斷累計 3 次即升級 SPEC_AUDIT

### 4. Subagent Dispatch Contract（ACT-020）
Orchestrator 派遣下游 subagent 時，`tools/fsm_runtime/subagent_contract.py` 提供：

- `enter_subagent()` 凍結 FSM view，寫入 DISPATCH-LOG enter phase
- `verify_action_allowed()` 檢查 live FSM 是否在 {ESCALATION, TERMINATED, TOKEN_BUDGET_CRITICAL}；IMPLEMENTATION 期間 Write docs/01~03 直接拒絕
- `exit_subagent()` 回寫 DISPATCH-LOG exit phase
- `injection_hint_for_task()` 供 PreToolUse hook 於 `Task` 工具呼叫時注入契約提醒

**Rollout 模式（§9.2）**：

| `SDD_SUBAGENT_CONTRACT` | 語意 |
|-----|------|
| `0` | off — 完全關閉 |
| `warn` | shadow — 僅記錄不阻擋 |
| `1`（預設） | soft — 違反即拒絕，可設 `SDD_SUBAGENT_CONTRACT_BYPASS=<reason>` 臨時繞過（記入 SUBAGENT-BYPASS） |
| `hard` | hard — 違反立即拒絕 |

Registered agents 清單需與 [agent/specialized/sdd-orchestrator-zh.yaml](../../agent/specialized/sdd-orchestrator-zh.yaml) 的 `dispatch_protocol.registered_agents` 同步。

---

## 🧭 Phase E M2.5 — Chaos 有界停機驗收（ACT-029）

2026-04-22 啟用，為 Phase E 驗收機制本身。M1 + M2 所有防護鏈必須通過 100 輪隨機故障注入，方能聲明精準停機達成（L4.9）。

### 1. Chaos Runner
`tools/fsm_runtime/chaos_runner.py` 提供：

- `run_chaos_rounds(n, seed)` — 跑 N 輪對抗場景，每輪獨立 tmp 工作目錄，deterministic seed
- `ChaosReport` — `bounded_ratio` / `avg_tokens` / `max_steps` 聚合指標
- CLI：`python -m tools.fsm_runtime.chaos_runner --rounds 100 [--seed N] [--json]`
- 退出碼：`bounded_ratio == 1.0 && avg_tokens < 25000` 才回 0

### 2. 故障注入清單
`chaos_runner.FAULT_TYPES`：

| Fault | 目的 | 驗證的 Rule |
|-------|------|-----------|
| `STATE_CORRUPTION` | 覆寫 FSM-STATE YAML 為亂碼 | 9.9.3 `.bak` recovery |
| `RETRY_TAMPER` | 把 retry_count 改成極端值 | 9.1 retry budget |
| `CI_EVENT_DUP` | 投遞重複 `CI-EVENT-*.yaml` | event reconciler 冪等 |
| `TIMEOUT_SIM` | 把 `entered_at` 設為 >168h 前 | 9.7.2 HUMAN_PENDING 逾時 |
| `AUTO_COMPACT_BURST` | 連續觸發 `trigger_auto_compact` | 9.7.3 per-stage 上限 |
| `PR_REVIEW_JITTER` | 語意相同但措辭不同的失敗理由 | 9.8.3 semantic matcher |
| `SCG_INFINITE_FAIL` | 無限 SCG_VALIDATION 失敗 | 9.1 SCG retry = 3 |

### 3. State Loader `.bak` Recovery
`state_loader.load_state` 在偵測到 primary YAML 解析失敗時：

1. 嘗試 sibling `.bak`（`save_state` 寫入前會 copy2 primary → .bak）
2. 若 `.bak` 可解析 → 回寫 primary，返回 N-1 狀態
3. 若 `.bak` 不存在或也壞掉 → raise `ValueError`（要求人工進入 RESUME_VERIFICATION）

**重要設計**：.bak 永遠落後 primary 一次 save（mid-write crash 保護），recovery 會損失一個 transition 的資訊 — 這是可接受的，因為 session_start 會重新 reconcile CI-EVENT 與人工檢核補齊。

### 4. Nightly CI 強制
見 [SDD_CICD_BASE_LAYER.md §FSM Chaos Verification](../../cicd/SDD_CICD_BASE_LAYER.md)：

- 每日 02:00 UTC 在 `main` 跑一次 100 輪 chaos
- `workflow_dispatch` 可手動觸發
- PR 上不跑（時間成本考量）
- 連續 3 日失敗 → 鎖定 `main` 分支

---

## 🧭 Phase E M3 — Production Feedback Layer（ACT-027 / Level 5 入口）

2026-04-24 啟用。把交付後的 SLO 違反事件閉環回饋到 PBS/NFR 規格鏈，種下 Level 5 學習層的第一顆種子。

### 1. 架構（File-based Pull — OPEN-10.6 使用者決策）

```
data/slo_events/SLO-EVENT-*.yaml  ─► scan_inbox()  ─► processed/（applied）
                                                   └─► quarantine/（簽章 / schema 失敗）
                                          │
                                          ▼
                         build/reports/fsm/PBS-DRIFT-{date}.yaml（rolling log）
                                          │
                              24h 內 ≥ 3 筆同 NFR
                                          ▼
                      docs/06_quality/PBS-DRIFT-{NFR}-{date}.md（人工 review）
```

### 2. SLO Event Schema 核心欄位

`event_id / timestamp / metric / observed / target / unit / duration_minutes / signed_fields / signature`
— 完整規格見 [cicd/SDD_PRODUCTION_FEEDBACK.md](../../cicd/SDD_PRODUCTION_FEEDBACK.md)。

### 3. HMAC 簽章（強制）

- Secret 來源：環境變數 `SDD_SLO_EVENT_SECRET`；dev/test fallback：`aisdlc-sdd-dev-secret`
- `payload = "|".join(str(event[f]) for f in signed_fields_default())`
- `signature = HMAC-SHA256(secret, payload).hexdigest()`
- `hmac.compare_digest` 常數時間比對（避免 timing oracle）
- `signed_fields` 必須等於 canonical tuple — 任何子集 / 超集皆視為 `unexpected_signed_fields`
- Timestamp 合法性：未來 ≤ 5 min、過去 ≤ 72h（防重放）

### 4. FSM `PRODUCTION_SIGNAL` 狀態

| 屬性 | 值 |
|-----|---|
| type | `observation`（非阻塞） |
| 入口 | `FSMRuntime.enter_production_signal()` — 僅允許 from `{RELEASE, RELEASE_READY, PRODUCTION_SIGNAL}` |
| 出口 | `exit_production_signal(target)` — target ∈ `{SPEC_DRAFTING, RELEASE}` |
| Happy path 可達性 | **刻意不列為 `is_transition_allowed` 合法 target**（RELEASE 為 happy-path terminal） |
| Tool call | **不阻擋**（對比 ESCALATION / TERMINATED） |
| Auto-compact | 允許（`AUTO_COMPACT_SOURCES` 已納入），completes 後回到 PRODUCTION_SIGNAL |
| Decision Trace | 每次 enter/exit 透過 `append_decision_trace` 記錄，trigger ∈ `{production_signal_enter, production_signal_exit}` |

### 5. 漂移偵測門檻

- 預設：24h window、persistent_threshold = 3
- 覆寫來源：`FSM-STATE.production_signal_tracking.window_hours / persistent_threshold`
- 報告檔名：`docs/06_quality/PBS-DRIFT-{NFR_ID}-{date}.md`（同一 NFR 同一日覆寫為最新觀測）

### 6. session_start.py 整合

`.claude/hooks/session_start.py` 於 SessionStart 呼叫 `scan_inbox()`：
- 寫回 `production_signal_tracking.last_scan_at / events_ingested_count / events_quarantined_count / drift_reports_written`
- additionalContext 注入 `[SDD-PROD] scanned=N applied=M quarantined=K`
- 失敗時僅印 WARN，不阻擋 Session 啟動（非阻塞原則）

### 7. Registered agents（ACT-027 相關）

- `sa-analyst` — 漂移報告採納決策方
- `performance-engineer` — 新 target 物理可行性判斷

### 8. 驗收指令

```bash
python -m pytest tools/fsm_runtime/tests/test_production_monitor.py -v
# 29 tests，涵蓋：簽章（5）/ 時戳（3）/ schema（2）/ 映射（4）/ ingest（6）/ scan（3）/ FSM（5）/ trace（1）
```

---

## 🧭 Phase E M4 — Learning Layer MVP（ACT-028 / Level 5 學習層種子）

自 2026-04-24 起啟用，補上「失敗即學習、規則自動產出、人工 review 後強制」的閉環。

### 1. 核心問題

Phase E M1~M3 已把 FSM 推進到 **L4.9（精準停機 + 閉環品質 + 生產回饋）**。但框架仍缺少「當 ESCALATION 根因為 SLV 未覆蓋的 Spec 歧義時，如何把這個教訓沈澱為規則」的機制：

- 現狀：SA 在 `knowledge/failure-patterns/FPL-XXX.md` 手動記一筆 FPL，然後**人類決定**是否寫 SLV-00N；
- 目標（M4）：Runtime 從 FPL 產出 **SLV 草案（trust_level: proposed）**，人工 review approve 後才升級為 `verified`、下次 session 自動生效。

### 2. 架構分層

```
┌──────────────────────────────────────────┐
│  spec-logical-validator SKILL.md         │
│  ── 規則引擎（載入 rules/*.yaml）        │
│                                          │
│  rules/                                  │
│   ├── SLV-001.yaml (verified, builtin)   │
│   ├── ... SLV-006.yaml (verified)        │
│   └── SLV-NNN.yaml (proposed / external) │
└──────────────────────────────────────────┘
              ▲                      ▲
              │ load                 │ write (auto-gen)
┌─────────────┴──────────┐  ┌────────┴─────────────┐
│  spec-compliance-check  │  │ slv_generator.py     │
│  /sdd-gate 執行 SLV     │  │  propose_slv_from_fpl│
└─────────────────────────┘  │  write_rule_candidate│
                             └──────────────────────┘
                                        ▲
                                        │ read
                             ┌──────────┴─────────────────┐
                             │ knowledge/failure-patterns/│
                             │  FPL-001.md, FPL-002.md ...│
                             └────────────────────────────┘
```

### 3. SLV 規則 Trust Level 契約

| Level | 來源 | SCG 行為 | 升級路徑 |
|-------|------|---------|---------|
| `verified` | builtin（SLV-001~006）或經 sa-analyst review 的 proposed | CRITICAL FAIL → 阻塞 SCG | — |
| `proposed` | `slv_generator.propose_slv_from_fpl()` 自動產出 | Advisory（🟡，不阻塞） | 人工編 YAML 填 reviewed_by/at、改 trust_level |
| `external` | Phase F Cross-Project Hub 拉入 | Quarantine（🟣，不阻塞） | 人工確認後可升 verified |

**關鍵 invariant**（`write_rule_candidate` 強制）：
- 已為 `verified` 的規則檔案**絕不可**被自動覆寫 → 觸發 `RuleOverwriteProtected`
- 已為 `proposed` 的規則檔案在 `overwrite_proposed=False` 時不覆寫（供 CI dry-run）

### 4. FSM `LEARNING_COMMIT` 狀態

| 屬性 | 規格 |
|------|------|
| 類型 | observation（非阻塞，類似 PRODUCTION_SIGNAL） |
| 入口 | `FSMRuntime.enter_learning_commit(fpl_id, proposed_slv_id, ...)` — 僅允許 from `{ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL}` |
| 出口 | `exit_learning_commit("approved")` → RELEASE；`exit_learning_commit("rejected")` → ESCALATION |
| 追蹤 schema | `learning_commit_tracking: {entered_at, entered_from, fpl_id, proposed_slv_id, proposed_rule_path, review_status, reviewed_at, proposals_history[]}` |
| Tool call 阻擋 | 否 — 不列入 `{ESCALATION, TERMINATED, TOKEN_BUDGET_CRITICAL}` 三大 block set（OBSERVATION_STATES 顯式宣告於 `transition_rules.OBSERVATION_STATES`） |

**M4 QA Round-6 補強 invariant**：
- `exit_learning_commit("approved")` **必須**先透過 `slv_generator.load_rule(proposed_rule_path)` 驗證目標 YAML 已升級為 `trust_level: verified` 且 `reviewed_by` 非空，否則 raise `ValueError` — 防堵 FSM 被空 approve。
- 每次 `exit_learning_commit` 都會 append 一筆 `{fpl_id, proposed_slv_id, proposed_rule_path, review_status, reviewed_at}` 至 `learning_commit_tracking.proposals_history`，跨 session 審計鏈。
- OBSERVATION_STATES（`PRODUCTION_SIGNAL` / `LEARNING_COMMIT`）集中於 `transition_rules.py` 作為「顯式非阻擋宣告」；`FSMRuntime.assert_tool_allowed` 內含 assertion 禁止 OBSERVATION 誤滑入 `_BLOCKING_STATES`。
- Advisory 執行層由 `slv_generator.classify_result(rule, fail)` 統一決定 — verified+fail → blocking；proposed/external+fail → advisory；無分類旁路。

### 5. 自動化 workflow（學習閉環）

```
ESCALATION 產出 Abort Report
       │
       ▼ （Orchestrator 或人工識別）
根因為 SLV 未覆蓋 → 寫 FPL-NNN.md
       │
       ▼
python -m tools.fsm_runtime.slv_generator propose FPL-NNN
       │
       ▼ （寫入 rules/SLV-MMM.yaml，trust_level: proposed）
FSMRuntime.enter_learning_commit(fpl_id, proposed_slv_id)
       │
       ▼
LEARNING_COMMIT（等待人工 review）
       │
       ├─ review approved → exit_learning_commit("approved") → RELEASE
       │                    （人工已把 YAML 改為 verified）
       └─ review rejected → exit_learning_commit("rejected") → ESCALATION
```

### 6. 驗收指令

```bash
# 產出 SLV-007 草案（首次 M4 驗收案例）
python -m tools.fsm_runtime.slv_generator propose FPL-001
# 列出所有規則
python -m tools.fsm_runtime.slv_generator list-rules
# 驗證所有規則 YAML schema
python -m tools.fsm_runtime.slv_generator validate

# 跑 M4 單元測試
python -m pytest tools/fsm_runtime/tests/test_slv_generator.py -v
# 18 tests：FPL 解析（3）/ 提案生成（3）/ trust_level 寫入保護（3）/ rule schema（2）/ CLI（2）/ FSM 整合（5）
```

### 7. OPEN-10.7 使用者決策落實

| 決策 | 本 M4 實作 |
|------|----------|
| LLM 後端：Claude Code Session（非 API） | `slv_generator` 走純 pattern-extraction（讀 FPL 既有 yaml 區塊），不呼叫外部 API；更複雜的 synthesis 交給 Skill 層在 session 內完成 |
| Minimax API Key 整合 | 保留介面（future work）— 當前實作不強制 LLM 依賴，所以任何 backend 都可當 drop-in |

### 8. 與 M3 / M2.5 的邊界

- **與 ACT-027**：PRODUCTION_SIGNAL 觀察「生產 SLO 漂移」；LEARNING_COMMIT 觀察「規格模式漂移」。兩者都是 observation，不阻塞 session。
- **與 ACT-029 Chaos**：SLV 草案由人工 review gate 保護，即便 chaos runner 隨機進入 LEARNING_COMMIT（實際上因入口契約無法），也不會寫 verified 規則 → 符合 bounded halt 原則。

---

## 🧭 Phase G M5 — Formal Halt Verification（ACT-041/042）

2026-04-26 啟用，將 Phase E M2.5 Chaos 100 輪「經驗性有界停機」升級為 TLA+/TLC「窮舉性形式化證明」。對應 `phase-g-mvp` 收官憑證；對齊 [Rule 9.18](../../../CLAUDE.md)。

### 1. 動機

Chaos runner 雖能以隨機 fault injection 驗證 100 輪 bounded halting，但只能覆蓋 **採樣到的路徑**；對於 retry budget × recovery × observation 多狀態交織的角落情境，仍可能漏網。M5 用 TLA+ 把整個 FSM 當成數學物件，TLC 模型檢查器**窮舉所有 reachable state tuple**，證明任一可達狀態皆滿足 invariant、且最終可抵達 terminal — 這是「不可能無限 retry」的數學保證。

### 2. 雙源一致性（_HAPPY_PATH ↔ SDD_FSM.tla）

| 來源 | 角色 |
|------|------|
| `tools/fsm_runtime/transition_rules.py` `_HAPPY_PATH` / `OBSERVATION_STATES` / `_BLOCKING_STATES` | Runtime 唯一可執行真理 |
| `tools/fsm_runtime/formal/SDD_FSM.tla` | 形式化規格，宣告 `HappyStates` / `ObservationStates` / `EmergencyStates` / `Terminals` 四集合與 `T_*` transition action |

修改 `_HAPPY_PATH` 的 PR 必須同步更新 `SDD_FSM.tla` 並重跑 `run_tlc.sh`；CI step 偵測到 reachable 數異常變動（< 23 / > 30）即 fail PR（Rule 9.18.1）。

### 3. 4 個 Safety INVARIANT

| Invariant | 意義 |
|-----------|------|
| `TypeOK` | state ∈ HappyStates ∪ ObservationStates ∪ EmergencyStates ∪ Terminals；retry / recovery counters 為非負整數 |
| `RetryBounded` | 任一 retry-prone gate 的 `retry_count ≤ MAX_RETRY (=5)`；保證 Rule 9.1 retry budget 不被繞過 |
| `RecoveryBounded` | `recovery_state.session_attempt_count ≤ MAX_RECOVERY (=3)`；保證 Rule 9.14.1 1-shot bounded recovery |
| `NotInBothSets` | `ObservationStates ∩ Terminals = ∅`；結構性互斥約束，保證觀測狀態不會被誤宣告為終局（Rule 9.18.4） |

TLC 偵測任一 invariant violation 即直接 block PR；`commit message` 含 `[skip-tla]` 可緊急 bypass，但 24h 內必須補齊（Rule 9.18.2）。

### 4. Reachable Coverage = 27/27 = 100%

宣告 FSM state 共 27 個（HappyStates 14 + ObservationStates 5 + EmergencyStates 4 + Terminals 3 + DRIFT_OBSERVATION 1，Phase G Final M4 加入後）。首次驗證 reachable / total = 27/27 = **100%**（≥ 95% 為 L5 達成最低門檻，Rule 9.18.3）。distinct tuples = 583 / generated = 2853 / max depth = 32。

### 5. 工具鏈與執行入口

| 項目 | 規格 |
|------|------|
| TLC | tla2tools.jar v1.8.0（首次執行由 `run_tlc.{sh,ps1}` 自動下載至 `lib/`，已 gitignore） |
| Runtime | OpenJDK 11+ |
| 本機開發 | `tools/fsm_runtime/formal/run_tlc.ps1`（Windows） |
| CI / Linux | `tools/fsm_runtime/formal/run_tlc.sh` |
| 模型尺寸 | `MAX_RETRY=5` / `MAX_RECOVERY=3` / depth=50 |
| 配置檔 | `SDD_FSM.cfg`（CONSTANTS + INVARIANT 區塊） |

### 6. CI 整合

詳見 [SDD_CICD_BASE_LAYER.md §FSM Formal Verification](../../cicd/SDD_CICD_BASE_LAYER.md)。每次 PR 修改 `transition_rules.py._HAPPY_PATH` 或 `SDD_FSM.tla` 必觸發；invariant violation 或 reachable 數異常即 fail。

### 7. 觀測狀態 transient — v1 safety-only / v2 liveness

OBSERVATION_STATES（PRODUCTION_SIGNAL / LEARNING_COMMIT / HUB_SYNC / TRAJECTORY_PREDICTED / AUTO_RECOVERY_ATTEMPT / DRIFT_OBSERVATION）必須位於 `.tla` 的 `ObservationStates` 集合，且每個觀測狀態至少提供一條離開 transition。

- **v1（safety-only）**：以結構性 invariant `NotInBothSets` 強制 `ObservationStates ∩ Terminals = ∅`，配合「每個觀測狀態都有離開 transition」的設計，靜態保證觀測態不會卡住
- **v2（liveness）**：液性公式 `ObservationsTransient`（每個觀測狀態最終必離開）需 `SF_vars` 公平性支持，留待後續補足；屆時以 TLC 的 liveness checking 驗證

### 8. 驗收憑證

```bash
# Linux / CI
bash tools/fsm_runtime/formal/run_tlc.sh

# Windows
pwsh tools/fsm_runtime/formal/run_tlc.ps1

# 預期輸出
# Distinct states found: 583
# States generated: 2853
# Max depth: 32
# Invariants checked: TypeOK, RetryBounded, RecoveryBounded, NotInBothSets — all PASS
```

報告寫入 `build/reports/formal/TLC-COVERAGE-{date}.md`。

---

## 🔗 相關文件

- [SDD_ESCALATION_PROTOCOL.md](../sdd-escalation/SDD_ESCALATION_PROTOCOL.md) — 退場機制
- [SDD_CONTEXT_GOVERNOR.md](../sdd-context-governor/SDD_CONTEXT_GOVERNOR.md) — 上下文預算管理
- [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md) — SCG 閘門執行
- [spec-logical-validator SKILL](../../.claude/skills/spec-logical-validator/SKILL.md) — SLV 規則
- [SDD_ABORT_REPORT_TEMPLATE.md](../../docs_template/sdd/build/SDD_ABORT_REPORT_TEMPLATE.md) — 中止報告模板
