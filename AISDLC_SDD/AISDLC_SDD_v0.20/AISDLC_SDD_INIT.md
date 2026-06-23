# AISDLC-SDD v0.01 框架初始化配置文件
# AISDLC-SDD (Spec-First / System Design Document Driven) Framework Init

> **重要**: 使用任何 AISDLC-SDD workflow 前，必須先載入此配置！

## 版本說明

AISDLC-SDD v0.01 是基於 AISDLC v0.09 的 **SDD（規格先行/系統設計文件驅動）** 擴展框架。

### SDD 三大支柱

1. **Spec-First Gate（規格先行閘門）** — SCG-0 ~ SCG-6 自動化品質閘門
2. **Design-as-Doc（設計即文件）** — ADR、C4、RTM 強制文件化
3. **Contract-Driven（契約驅動）** — OpenAPI 3.1 規格凍結後才開始實作

### 🆕 Phase D~Y — Layer 1 Runtime（自動化閉環 → 精準停機 → 閉環品質鏈 → 學習層 → 多模態 → 自我演進 meta⁸ → 具身接地 → 可解釋性視覺化）

Phase D 首開 **Layer 1 Runtime Hooks**，把 Rule 9（CLAUDE.md §9）從紙上規則升級為
Claude Code Hook 層的**強制攔截**；Phase E 在此之上依序加入**精準停機（M1）**、**閉環品質鏈（M2）**、
**Chaos 有界停機驗收（M2.5）**、**Production Feedback Layer（M3）** 與 **Learning Layer MVP（M4）**，
完成 L4.9 精準停機 → L5 學習層入口。其後 **Phase G~Y** 持續加固至 L5 Self-Driving → L6 Trustworthy Scaled → L7 對抗自癒 → L10 元停機自我演進（meta⁸ 互遞迴良基停機證書）→ 具身接地 → 可解釋性視覺化；完整禁止事項見下方清單，演進鏈與最新驗收見文末版本說明，元件索引見 [governance/RULES_INDEX.md](governance/RULES_INDEX.md) 與 CLAUDE.md §9。

> 下表為 **Phase D~F** 基礎元件（精準停機 / 閉環品質鏈 / Chaos / Production Feedback / 學習層 / Hub / 多模態）：

| 元件 | 位置 | 作用 | Phase |
|------|------|------|-------|
| FSM Runtime | [tools/fsm_runtime/](tools/fsm_runtime/) | 唯一合法的 FSM 讀寫入口（atomic write + .bak 輪替） | D / E |
| SessionStart Hook | [.claude/hooks/session_start.py](.claude/hooks/session_start.py) | reconcile `CI-EVENT-*.yaml`、HUMAN_PENDING 逾時守門、Decision Trace 注入最近 5 筆、AUTO_COMPACT snapshot 存在性檢查 | D / E |
| PreToolUse Hook | [.claude/hooks/context_ledger_pre.py](.claude/hooks/context_ledger_pre.py) | FSM guardrail + 90% AUTO_COMPACT 自動切換 + 95% token 拒絕（MAX_CONTEXT 零除防護） | D / E |
| PostToolUse Hook | [.claude/hooks/context_ledger_post.py](.claude/hooks/context_ledger_post.py) | 實測 token 記帳、conv-overhead 每 10 次累計、rolling drift 10 樣本 | D / E |
| sdd-orchestrator Agent | [agent/specialized/sdd-orchestrator-zh.yaml](agent/specialized/sdd-orchestrator-zh.yaml) | Test→Fix 閉環總指揮（TFA 分類 → 自動派遣） | D |
| Failure Pattern Library | [knowledge/failure-patterns/](knowledge/failure-patterns/) | SLV 未覆蓋模式的知識庫（FPL-001/002） | D |
| Scenario FSM Variants | [workflow/sdd-fsm-engine/variants/](workflow/sdd-fsm-engine/variants/) | 6 大場景 FSM 變體 | D |
| IMPLEMENTATION sub-FSM | [workflow/sdd-fsm-engine/FSM_IMPLEMENTATION_SUB.md](workflow/sdd-fsm-engine/FSM_IMPLEMENTATION_SUB.md) | 展開 IMPLEMENTATION 為子狀態機 | D |
| **M1 — FSM 雙源一致性測試** | [tools/fsm_runtime/tests/test_md_python_sync.py](tools/fsm_runtime/tests/test_md_python_sync.py) | 每次 CI 比對 SDD_FSM_ENGINE.md vs transition_rules._HAPPY_PATH | E M1 |
| **M1 — HUMAN_PENDING Timeout Checker** | [tools/fsm_runtime/timeout_checker.py](tools/fsm_runtime/timeout_checker.py) | 72h REMINDER / 168h 自動 ESCALATION | E M1 |
| **M1 — AUTO_COMPACT 單 Stage 限流** | [tools/fsm_runtime/fsm_runtime.py](tools/fsm_runtime/fsm_runtime.py) | 同一 stage 超 3 次 compact 即 ESCALATION | E M1 |
| **M2 — Decision Trace** | [tools/fsm_runtime/state_loader.py](tools/fsm_runtime/state_loader.py) | FSMRuntime.transition 必帶 reason/spec_refs/trigger；active 50 + flushed FIFO | E M2 |
| **M2 — Conversation Ledger** | [tools/fsm_runtime/conversation_ledger.py](tools/fsm_runtime/conversation_ledger.py) | 唯一 token 估算入口；Read 行號 overhead、Task subagent overhead、rolling drift | E M2 |
| **M2 — File Lock** | [tools/fsm_runtime/file_lock.py](tools/fsm_runtime/file_lock.py) | CONTEXT-LEDGER YAML 互斥（sentinel + 30s stale + 5s timeout） | E M2 |
| **M2 — Pattern Matcher** | [tools/fsm_runtime/pattern_matcher.py](tools/fsm_runtime/pattern_matcher.py) | `max(SequenceMatcher, Jaccard)` 語意比對，門檻 0.75（env 覆寫） | E M2 |
| **M2 — Subagent Dispatch Contract** | [tools/fsm_runtime/subagent_contract.py](tools/fsm_runtime/subagent_contract.py) | 4 種 rollout（off/shadow/soft/hard）；hard 模式 bypass 為 noop | E M2 |
| **M2 — Event Reconciler（事務性）** | [tools/fsm_runtime/event_reconciler.py](tools/fsm_runtime/event_reconciler.py) | 內容雜湊去重；save_state 於 save_event 之前持久化以防 retry 漂移 | E M2 |
| **M2.5 — Chaos Runner** | [tools/fsm_runtime/chaos_runner.py](tools/fsm_runtime/chaos_runner.py) | 100 輪隨機故障注入；bounded_ratio==1.0、avg tokens < 25K | E M2.5 |
| **M2.5 — State Loader .bak 恢復** | [tools/fsm_runtime/state_loader.py](tools/fsm_runtime/state_loader.py) | 5 種 reason 分類（read/yaml/non_dict/missing_root/absent）+ .bak 原子輪替（.bak.tmp → os.replace） | E M2.5 |
| **M3 — Production Monitor** | [tools/fsm_runtime/production_monitor.py](tools/fsm_runtime/production_monitor.py) | File-based Pull + HMAC-SHA256 簽章 + 時戳防重放（±5min/72h）；quarantine 未簽章事件 | E M3 |
| **M3 — PRODUCTION_SIGNAL 狀態** | [workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md](workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) | 非阻塞 observation state；同一 NFR 24h 內 ≥3 次 → PBS-DRIFT 報告 | E M3 |
| **M3 — SLO Event Inbox** | [data/slo_events/](data/slo_events/) | metric_nfr_map.yaml + processed/ + quarantine/；`session_start.py scan_inbox()` 消化 | E M3 |
| **M4 — SLV Generator** | [tools/fsm_runtime/slv_generator.py](tools/fsm_runtime/slv_generator.py) | FPL→SLV 草案（pattern-extraction）；Trust Level 三階（verified/proposed/external）+ 寫入保護 | E M4 |
| **M4 — LEARNING_COMMIT 狀態** | [workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md](workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) | 非阻塞 observation state；入口 {ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL} → approved/rejected | E M4 |
| **M4 — SLV-007 首個採納規則** | [.claude/skills/spec-logical-validator/rules/SLV-007.yaml](.claude/skills/spec-logical-validator/rules/SLV-007.yaml) | 從 FPL-001 時序語義矛盾升級為 verified 規則（附 reviewed_by / reviewed_at） | E M4 |
| **F M2 — Hub Sync Client** | [tools/fsm_runtime/hub_sync.py](tools/fsm_runtime/hub_sync.py) | pull/push/dry-run/diff/promote CLI；file:// + git+https 兩種 endpoint；PII 雙掃 + opt-in confirm | F M2 |
| **F M2 — PII Scanner + Anonymizer** | [tools/fsm_runtime/pii_scanner.py](tools/fsm_runtime/pii_scanner.py) / [anonymizer.py](tools/fsm_runtime/anonymizer.py) | L2 quarantine + L1 placeholder 替換；20 條 fixture 覆蓋；Luhn 信用卡精煉 | F M2 |
| **F M2 — Conflict Resolver** | [tools/fsm_runtime/hub_merge.py](tools/fsm_runtime/hub_merge.py) | 3-way merge（fast-forward / no-op / conflict / verified-blocked） | F M2 |
| **F M2 — HUB_SYNC 狀態** | [workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md](workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) | 非阻塞 observation state；success → resume_state、partial → HUMAN_PENDING、failed → resume_state（不升 ESCALATION）| F M2 |
| **F M3 — LLM Backend 抽象層** | [tools/fsm_runtime/modality/llm_backend.py](tools/fsm_runtime/modality/llm_backend.py) | Protocol + 3 backend（session 預設零成本 / claude-api stub / minimax stub）；env `SDD_MULTIMODAL_BACKEND` 切換 | F M3 |
| **F M3 — 4 Modality Adapter** | [tools/fsm_runtime/modality/](tools/fsm_runtime/modality/) | UI / API↔UI / DB Schema / C4 Diagram → 對應 SLV-008~011 | F M3 |
| **F M3 — Spec Anchor 機制** | [docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md](docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md) | `<!-- anchor:<modality>:<id> -->` HTML comment；4 種 modality target 解析路徑 | F M3 |
| **F M4 — Multimodal Validator** | [tools/fsm_runtime/multimodal_validator.py](tools/fsm_runtime/multimodal_validator.py) | 統一入口；scan FRD/SRD anchors → 派遣 4 adapter；CI 整合 `--strict` | F M4 |
| **F M4 — Multimodal SpecTrace CI step** | [cicd/SDD_CICD_BASE_LAYER.md](cicd/SDD_CICD_BASE_LAYER.md) | proposed 階段 advisory；verified 升級後改 strict 阻擋 PR | F M4 |

**啟用方式**：`.claude/settings.json` 已內建 `hooks` 與 `env` 區塊（`SDD_SUBAGENT_CONTRACT=soft`、`SDD_PATTERN_MATCH_THRESHOLD=0.75`）。Hook 失敗時 Session 仍能啟動，但會於 additionalContext 顯示 WARN。

**Runtime 禁止事項**（Rule 9.6~9.9）：
- 繞過 `FSMRuntime` 直接 edit `FSM-STATE-*.yaml`（D）
- 停用／刪除 Phase D·E Hooks（D）
- IMPLEMENTATION 期間 Write/Edit `docs/01~03` 規格文件（D，Hook 拒絕）
- 手動編輯 SDD_FSM_ENGINE.md 轉換表而不同步 `transition_rules._HAPPY_PATH`（E M1）
- 清除 `human_pending_tracking.entered_at` 以規避 72/168h 逾時守門（E M1）
- 重複觸發 auto_compact 而繞過 `count_per_stage` 檢查（E M1）
- `FSMRuntime.transition()` 呼叫不傳 reason/trigger（破壞決策證據鏈）（E M2）
- 繞過 `conversation_ledger.estimate_tool_tokens` 自算 token（造成預算漂移）（E M2）
- `PR_REVIEW` 用字串相等而非 `pattern_matcher.is_same_pattern` 比對失敗原因（E M2）
- Subagent 在 hard 模式下強行 Write `docs/01_requirements/`（E M2）
- 跳過 nightly chaos 驗收或放寬 `TERMINAL_STATES` 以假性通過（E M2.5）
- 繞過 `load_state` 直接讀寫 YAML，破壞 .bak 恢復鏈（E M2.5）
- 在生產環境使用 `DEV_DEFAULT_SECRET`、繞過 HMAC 驗證、對 `PRODUCTION_SIGNAL` 加工具阻擋（E M3）
- 開啟 HTTP endpoint 接收 SLO event（違反 OPEN-10.6 File-based Pull 決策）（E M3）
- 繞過 `write_rule_candidate` 覆寫 `trust_level: verified` 規則、切斷 `source_fpl` FPL→SLV 追溯鏈（E M4）
- 讓 `proposed` 規則阻塞 SCG（等同略過人工 review gate）（E M4）
- 直接寫 hub 資料而不經 `hub_sync.HubSyncClient`、略過 anonymizer 強制（F M2）
- 取消 `deny_unlisted` 改 allow_all、Hub pull 衝突自動覆寫本地 verified（F M2）
- 把 SLV-008~011 直接以 `trust_level: verified` 提交（F M3，必經人工 review）
- 在 multimodal_validator 加 LLM 呼叫但未經 anonymizer，造成多模態 PII 洩漏（F M3）
- 把 PNG mockup 放在 `docs/99_media/` 之外，破壞 anchor 解析路徑契約（F M3）
- 在 `enter_auto_recovery` 之外手動 transition 進 `AUTO_RECOVERY_ATTEMPT`（G M1，破 1-shot bounded recovery）
- 對 `category=structural` 的 ESCALATION 強行觸發 auto-recovery（G M1，違反 Rule 9.14.3）
- 繞過 `DiagnosticAgent` 自行判斷 `auto_recoverable`（G M1，破壞分類器一致性）
- 清除 `recovery_state.session_attempt_count` 或 `per_reason_count` 以規避 Rule 9.14.1/9.14.2（G M1）
- ESCALATION_FINAL 期間用任何方式偷跑 tool call（G M1，PreToolUse hook 強制 deny）
- 在 retry_count == 0 時呼叫 `TrajectoryPredictor` 並繞過 9.15.1 檢查（G M2，製造 false positive）
- `abort_early` 不附 confidence ≥ 0.8 證據卻直升 ESCALATION（G M2，違反 Rule 9.15.2）
- 同一 retry-prone gate（key 為 gate 名稱，跨 stage 共用）反覆呼叫 `enter_trajectory_predicted` + `switch_to_audit` > 1 次（G M2，破 9.15.4 防抖動）
- 修改 `_HAPPY_PATH` 但不同步 `SDD_FSM.tla`（G M5，破 Rule 9.18.1 雙源一致性）
- 觀測狀態（`OBSERVATION_STATES` 任一）放入 Terminals 集合（G M5，破 9.18.4 transient 約束）
- `SDD_FSM.cfg` 移除 INVARIANT 區塊或將 `run_tlc.sh` 改寫成永遠 exit 0（G M5，規避 CI gate 偽通過）
- AmbiguityScorer 評分公式變更不 bump SCORER_VERSION（G M3，造成快取中毒）
- 繞過 `is_blocking()` 自行判斷阻擋條件（G M3，違反 Rule 9.16.2 一致性）
- AmbiguityScorer 對 invariants/architecture 評分（G M3，範圍越界）
- PostCommit drift hook 阻擋 commit（G M4，違反 Rule 9.17.1 advisory 契約）
- 連續 drift 累積卻不轉 SPEC_AUDIT（G M4，違反 Rule 9.17.3）
- 修改 `_HAPPY_PATH["DRIFT_OBSERVATION"]` 不同步 `SDD_FSM.tla`（G M4，違反 Rule 9.18.1）
- 把 `DRIFT_OBSERVATION` 放入 `_BLOCKING_STATES`（G M4，違反 9.17.2 非阻塞契約）
- 樣本不足卻使用 < 8000 的 cold-start default（G M6，違反 Rule 9.19.1）
- 連續 3 次 dispatch 拒絕後不轉 ESCALATION（G M6，違反 Rule 9.19.3 有界停機）
- 把 `budget_exhausted` 對應 sub_type 改為 transient（G M6，誤觸發 auto-recovery）
- `INTENT_DECOMPOSITION` 產出含環 spec-DAG，或超 `SDD_INTENT_MAX_NODES` 上限仍續分解（K，破 Rule 9.23.1）
- planner 自動選最高 ROI 目標直接 `SPEC_DRAFTING`、繞過 `BACKLOG_PRIORITIZED` 人工 signoff（K，破 Rule 9.23.2 / Rule 8）
- 調 `SPEC_DEBATE` 辯證強度權重不 bump `SPEC_DEBATE_PROFILE_VERSION`（K，破 Rule 9.23.3，辯證自我放水）
- 讓 `SPEC_DEBATE` divergence 自動阻塞 SCG 或自動改寫 AC（K，破 Rule 9.23.4 advisory 契約）
- `spec_localizer` 自動套用定位結果改 FRD/AC（K，破 Rule 9.23.5 / Rule 8，僅建議不自動改 spec）
- 把 `SPEC_DEBATE` 放入 Terminals、或 `INTENT_DECOMPOSITION` 誤列為 observation（K，破 Rule 9.23.6 / Rule 9.18.4）
- 2 新狀態（`INTENT_DECOMPOSITION` / `SPEC_DEBATE`）不同步 `SDD_FSM.tla`（K，破 Rule 9.23.6 / Rule 9.18.1）
- 學習層 `exit_learning_commit(approved)` 或 GC `set_maturity()` 繞過 `meta_halt/meta_halt_monitor` 的 `ChurnBounded` 檢查（L，破 Rule 9.24.1）
- 把被 GC 退役的規則指紋無 capability-delta 地重新學回（add↔retire 同型震盪）（L，破 Rule 9.24.2 GraduationRatchet）
- 把 `META_FSM` 狀態併入單軌 `SDD_FSM.tla`、或讓 meta churn 污染單軌 reachable 計數（L，破 Rule 9.24.3 / Rule 9.18.1）
- 讓 `EXPERIMENT_REPLAY` 命中率自動 approve 補丁、或自動改寫 AC（L，破 Rule 9.24.4 / Rule 8）
- `spec_fragility_scorer` 自動改 spec、阻塞 SCG，或調權重不 bump `FRAGILITY_PROFILE_VERSION`（L，破 Rule 9.24.5）
- `EXPERIMENT_REPLAY` 不同步三源或誤列為 Terminals/blocking（L，破 Rule 9.24.6 / Rule 9.18.4）
- 未經 OPEN-L.5 人工決策私自開 HTTP 外聯做 L9 完整活體實驗（L，破 OPEN-10.6）
- `intent_composer` 自動 commit 跨意圖排程、繞過 `BACKLOG_PRIORITIZED` 人工 signoff（M，破 Rule 9.25.1 / Rule 8 / Rule 9.23.2）
- 把 `COMPOSITION_FSM` 狀態（`CPLAN_*`）併入單軌 `SDD_FSM.tla`、或讓組合協商污染單軌/META/FLEET reachable 計數（M，破 Rule 9.25.3 / Rule 9.18.1）
- 跨意圖再協商無上限導致 livelock、或誤把 `CPLAN_ESCALATION` 列為不動點（M，破 Rule 9.25.1 / 9.25.2）
- `capability_trajectory_monitor` 的 plateau/regression 訊號自動觸發典範轉移或自動退役鷹架（M，破 Rule 9.25.4 / 9.25.7 / Rule 8）
- `scaffold_ceiling_detector` 自動退役仍在 fire 的鷹架而不經 `set_maturity(reviewed_by=)`（M，破 Rule 9.25.5 / Rule 9.20.5）
- `composition_blast_analyzer` 自動改 FRD/AC 或阻塞 SCG、調 trajectory/blast 權重不 bump 對應 `*_PROFILE_VERSION`（M，破 Rule 9.25.6）
- `composition_optimizer` 搜尋無上限指數爆炸（超 `SDD_OPT_NODE_BUDGET` 仍展開）、或自動 commit 排程繞過 `BACKLOG_PRIORITIZED` 人工 signoff（N，破 Rule 9.26.1 / 9.26.3 / Rule 8）
- 把 `OPTIMIZATION_FSM` 狀態（`OPT_*`）併入單軌 `SDD_FSM.tla`、或污染單軌/META/FLEET/COMPOSITION reachable（N，破 Rule 9.26.2 / Rule 9.18.1）
- 預算耗盡仍謊報 proven-optimal、或調 `OBJECTIVE_PROFILE_VERSION` 權重不 bump（N，破 Rule 9.26.4 / 9.26.5）
- `objective_tuner` 自動 commit / 自寫 `composition_objective_scorer` 權重常數繞過人工 `OBJECTIVE_PROFILE_VERSION` bump（O，破 Rule 9.27.3 / Rule 8）
- 用 objective scorer 自評分數充當 capability-delta tier、或 `objective_tuner` 讀寫/影響 `knowledge/held-out-corpus/` 現實代理語料（O，破 Rule 9.27.2 / 9.27.5 反 Goodhart 對抗分離）
- obj-profile 採納/退役繞過 `meta_halt_monitor`、無 capability-delta re-adopt 退役過的 profile、或候選搜尋超 `SDD_OBJ_TUNE_BUDGET` 仍指數展開（O，破 Rule 9.27.1 / 9.27.4）
- 把 obj-profile 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（O，破 Rule 9.27.4 / Rule 9.18.1）
- 任一 scorer tuner 經 `scorer_calibration_registry` 自動 commit / 自寫評分器權重常數繞過人工 `*_PROFILE_VERSION` bump（P，破 Rule 9.28.1/9.28.4）
- 用 per-scorer 自評或單獨 oracle 結果充當「聯合 capability-delta tier」、或讓 per 通過凌駕 `joint_calibration_oracle` 的 joint 不通過（P，破 Rule 9.28.2 接縫 Goodhart 對抗分離）
- 任一 tuner 讀寫 / 影響 `knowledge/held-out-corpus/` 聯合 oracle 語料、或生成器 import joint oracle（P，破 Rule 9.28.2）
- 8 命名空間採納退役繞過 `meta_halt_monitor.guard_calibration_adoption`、忽略 `CrossScorerChurnBounded` 聚合速率、或放任 A→B→A 耦合震盪不升 `MFSM_ESCALATION`（P，破 Rule 9.28.3）
- 一週期同時 bump > K（預設 2）個評分器一次改整套價值系統（P，破 Rule 9.28.4 NoBigBangValueRewrite）
- 把 calibration 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（P，破 Rule 9.28.3 / Rule 9.18.1）
- `value_dimension_registry` 自動納入新維度 / 自寫維度集合常數繞過人工 signoff + `guard_dimension_expansion`（Q，破 Rule 9.29.1/9.29.4 / Rule 8）
- 用 proposer 自評 / 自算覆蓋率充當「維度必要性 capability-delta tier」（Q，破 Rule 9.29.2 維度 Goodhart 自評放水）
- proposer 讀寫 / 影響 / import `knowledge/held-out-corpus/DIM-*` 維度必要性語料或 `dimension_necessity_oracle`（Q，破 Rule 9.29.2 對抗分離）
- value-dimension 採納退役繞過 `meta_halt_monitor`、忽略 `DimensionCardinalityBounded` stock 天花板而無界增維、或退役維度無 necessity capability-delta 地 re-adopt（Q，破 Rule 9.29.3 維度震盪繞過棘輪）
- 候選維度搜尋超 `SDD_DIM_PROPOSE_BUDGET` 仍指數展開、或一週期同時新增 > K_dim（預設 1）條維度一次劫持整個本體論（Q，破 Rule 9.29.1 / 9.29.4 NoUnboundedOntologyExpansion）
- 把 value-dimension 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（Q，破 Rule 9.29.3 / Rule 9.18.1）
- `dimension_semantics_synthesizer` 自動納入自我發明維度 / 自寫常數繞過人工 signoff + `guard_dimension_expansion`／`guard_dimension_swap`（R，破 Rule 9.30.1/9.30.4 / Rule 8）
- 用 synthesizer 自評 / 自算覆蓋率充當「自我發明必要性 capability-delta tier」（R，破 Rule 9.30.2 自我發明 Goodhart 自評放水）
- 自我發明 probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`dim_value`/`oracle_*` 等保留自指信號繞過 `self_reference_guard`）（R，破 Rule 9.30.2 反自利）
- synthesizer 讀寫 / 影響 / import `knowledge/held-out-corpus/INV-*` feature 必要性語料或 `dimension_necessity_oracle`（R，破 Rule 9.30.2 對抗分離）
- 自我發明搜尋超 `SDD_DIM_INVENT_BUDGET` 仍指數展開（R，破 Rule 9.30.1 有界生成文法，「候選池外」≠「無界」）
- retire-to-swap 入軸 tier 未嚴格 > 出軸 tier + `SDD_DIM_SWAP_MARGIN`（A↔B↔A 維度震盪繞過單調價值棘輪）、或聚合 swap 速率超 `SDD_DIM_SWAP_RATE_MAX` 仍定基數旋轉重寫本體論（R，破 Rule 9.30.3，繞過 per-fingerprint churn + cardinality stock）
- 一週期同時自我發明 > K_dim 條維度 / 多次 swap 一次劫持本體論（R，破 Rule 9.30.4 NoUnboundedSelfInvention）
- 把 self-invention/swap 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（R，破 Rule 9.30.3 / Rule 9.18.1）
- `vocabulary_genesis` 自動納入詞彙自我發明字 / 自寫常數繞過人工 signoff + `guard_vocab_genesis`／`guard_batch_swap`（S，破 Rule 9.31.1/9.31.4 / Rule 8）
- 用 genesis 自評 / 自算覆蓋率充當「詞彙自我發明必要性 capability-delta tier」（S，破 Rule 9.31.2 詞彙自我發明 Goodhart 自評放水）
- 詞彙自我發明 source/transform 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `vocab_self_reference_guard`）（S，破 Rule 9.31.2 反自利）
- `vocabulary_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/VOC-*` feature-genesis 必要性語料或 `dimension_necessity_oracle`（S，破 Rule 9.31.2 對抗分離）
- 詞彙自我發明搜尋超 `SDD_DIM_VOCAB_BUDGET` 仍指數展開（S，破 Rule 9.31.1 有界詞彙文法，「VOCAB 外」≠「無界」）、或現存活躍 vocab-genesis 字超 `SDD_DIM_VOCAB_MAX` 仍無界擴充詞彙（S，破 Rule 9.31.3 VocabGenesisBounded）
- 批次 retire-to-swap `|out|`/`|in|` 超 `SDD_DIM_BATCH_MAX`（一次劫持本體論）、批次入軸聚合 tier 未嚴格 > 出軸聚合 + margin 或 min(in_tier) 未 > max(out_tier)（批次內高低互抵）、或批次操作聚合速率超 `SDD_DIM_BATCH_RATE_MAX` 仍批次旋轉重寫本體論（S，破 Rule 9.31.3，繞過 per-swap SwapCadence + 單調棘輪）
- 一週期同時詞彙自我發明 > K_vocab 個 / 批次大小超界一次劫持本體論（S，破 Rule 9.31.4 NoUnboundedVocabGenesis）
- 把 vocab-genesis/batch-swap 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（S，破 Rule 9.31.3 / Rule 9.18.1）
- `operator_genesis` 自動納入算子自我發明 / 自寫常數繞過人工 signoff + `guard_operator_genesis`／`guard_operator_computability`（T，破 Rule 9.32.1/9.32.4 / Rule 8）
- 用 genesis 自評充當「算子自我發明必要性 capability-delta tier」（T，破 Rule 9.32.2 算子自我發明 Goodhart 自評放水）
- 算子自我發明 primary/combinator/secondary/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `operator_self_reference_guard`）（T，破 Rule 9.32.2 反自利）
- `operator_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/OPR-*` 算子必要性語料或 `dimension_necessity_oracle`（T，破 Rule 9.32.2 對抗分離）
- 自我發明算子非全函式（某輸入無定義/拋例外）/ cost 超 `SDD_DIM_OP_STEP_MAX` / 算子求值路徑含遞迴/`while`/自呼叫（T，破 Rule 9.32.3 OperatorComputabilityBounded——被發明物本身不可證停機，「圖靈完備 vs 保證停機」反噬到自我擴充產物本身）
- 算子自我發明搜尋超 `SDD_DIM_OP_BUDGET` 仍指數展開（T，破 Rule 9.32.1 有界算子文法，「TRANSFORMS/OPS 外」≠「無界」）、或現存活躍 operator-genesis 算子超 `SDD_DIM_OP_MAX` 仍無界擴充算子（T，破 Rule 9.32.4 OperatorGenesisBounded）
- 一週期同時算子自我發明 > K_op 個（T，破 Rule 9.32.4 NoUnboundedOperatorGenesis）、把 operator-genesis 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（T，破 Rule 9.32.4 / Rule 9.18.1）
- 未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（T，破 Rule 9.32.5，掏空全部反 Goodhart 對抗分離地基）
- `operator_alphabet_genesis` 自動納入字母自我發明 / 自寫常數繞過人工 signoff + `guard_alphabet_genesis`／`guard_computability_closure`（U，破 Rule 9.33.1/9.33.4 / Rule 8）
- 用 genesis 自評充當「字母自我發明必要性 capability-delta tier」（U，破 Rule 9.33.2 字母自我發明 Goodhart 自評放水）
- 字母自我發明 base_reducer/post_map/atom/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `alphabet_self_reference_guard`）（U，破 Rule 9.33.2 反自利）
- `operator_alphabet_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/ALG-*` 字母必要性語料或 `dimension_necessity_oracle`（U，破 Rule 9.33.2 對抗分離）
- 自我發明字母使擴充後 G(A') 整個算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX` / 求值路徑含遞迴/`while`/自呼叫的算子（U，破 Rule 9.33.3 ComputabilityClosureBounded——被發明的生成規則本身不可證閉包停機，「圖靈完備 vs 保證停機」反噬到自我擴充的生成規則本身）
- 字母自我發明搜尋超 `SDD_DIM_ALPHABET_BUDGET` 仍指數展開（U，破 Rule 9.33.1 有界字母表文法，「PRIMITIVES/COMBINATORS 外」≠「無界」）、或現存活躍 alphabet-genesis 字母超 `SDD_DIM_ALPHABET_MAX` 仍無界擴充字母（U，破 Rule 9.33.4 AlphabetGenesisBounded）
- 一週期同時字母自我發明 > K_alpha 個（U，破 Rule 9.33.4 NoUnboundedAlphabetGenesis）、把 alphabet-genesis 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（U，破 Rule 9.33.4 / Rule 9.18.1）
- `operator_depth_genesis` 自動納入深度自我發明 / 自寫常數繞過人工 signoff + `guard_depth_genesis`／`guard_depth_closure`（V，破 Rule 9.34.1/9.34.4 / Rule 8）
- 用 genesis 自評充當「深度自我發明必要性 capability-delta tier」（V，破 Rule 9.34.2 深度自我發明 Goodhart 自評放水）
- 深度自我發明 base/chain/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `depth_self_reference_guard`）（V，破 Rule 9.34.2 反自利）
- `operator_depth_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/DPT-*` 深度必要性語料或 `dimension_necessity_oracle`（V，破 Rule 9.34.2 對抗分離）
- 深度自我發明搜尋超 `SDD_DIM_DEPTH_BUDGET` 仍指數展開、或鏈長超 `SDD_DIM_DEPTH_LIMIT-2`（V，破 Rule 9.34.1 有界深度文法，「深度 <=2 外」≠「無界」）
- 自我發明深度算子使擴充深度後 G(A,depth) 整個深度算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX`（因 cost==depth，即深度超界）/ 求值路徑含遞迴/`while`/自呼叫的算子（V，破 Rule 9.34.3 DepthClosureBounded——被自我擴充的組合深度=計算步數參數本身不可證停機，「圖靈完備 vs 保證停機」反噬到自我擴充文法的結構性深度=步數參數本身，因 cost==depth 而最直接）
- 現存活躍 depth-genesis 算子超 `SDD_DIM_DEPTH_MAX` 仍無界擴充（V，破 Rule 9.34.4 DepthGenesisBounded）、一週期同時深度自我發明 > K_depth 個（V，破 Rule 9.34.4 NoUnboundedDepthGenesis）、把 depth-genesis 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（V，破 Rule 9.34.4 / Rule 9.18.1）
- 未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（V，破 Rule 9.34.5，掏空全部反 Goodhart 對抗分離地基）
- `operator_recursion_genesis` 自動納入互遞迴自我發明 / 自寫常數繞過人工 signoff + `guard_recursion_genesis`／`guard_recursion_closure`（W，破 Rule 9.35.1/9.35.4 / Rule 8）
- 用 genesis 自評充當「互遞迴自我發明必要性 capability-delta tier」（W，破 Rule 9.35.2 互遞迴自我發明 Goodhart 自評放水）
- 互遞迴自我發明 node/call/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `recursion_self_reference_guard`）（W，破 Rule 9.35.2 反自利）
- `operator_recursion_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/RCR-*` 互遞迴必要性語料或 `dimension_necessity_oracle`（W，破 Rule 9.35.2 對抗分離）
- 互遞迴自我發明搜尋超 `SDD_DIM_RECUR_BUDGET` 仍指數展開、或呼叫圖節點超 `SDD_DIM_RECUR_NODES`、或 fuel 超 `SDD_DIM_OP_STEP_MAX`（W，破 Rule 9.35.1 有界互遞迴文法，「非遞迴外」≠「無界」）
- 自我發明的互遞迴算子呼叫圖含無證書環（環中無回邊嚴格遞減下有界 rank）/ fuel 超 STEP_MAX / 求值器含真遞迴/`while`/自呼叫函式 / 整代數出現非全函式算子（W，破 Rule 9.35.3 RecursionClosureBounded 良基停機證書——被自我擴充的互遞迴圖結構不可證良基終止；判定任意含環圖停機=停機問題〔不可判定〕，「有界步數」device 失效，必須出示良基測度證書，「圖靈完備 vs 保證停機」第一次正面逼到不可判定臨界線本身，用全新 device「良基測度終止」取代失效的「有界步數」）
- 現存活躍 recursion-genesis 算子超 `SDD_DIM_RECUR_MAX` 仍無界擴充（W，破 Rule 9.35.4 RecursionGenesisBounded）、一週期同時互遞迴自我發明 > K_recur 個（W，破 Rule 9.35.4 NoUnboundedRecursionGenesis）、把 recursion-genesis 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（W，破 Rule 9.35.4 / Rule 9.18.1）
- 讓算子代數真正跨入圖靈完備（移除良基測度約束 / 帶無界記憶使停機不可判定）而謊稱「可證停機」（W，破 Rule 9.35.3/9.35.5——真圖靈完備無靜態 device 可保證停機，須誠實標為 horizon）
- 未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（W，破 Rule 9.35.5，掏空全部反 Goodhart 對抗分離地基）
- `embodied_grounding_oracle` 自動納入具身接地 / 自寫常數繞過人工 signoff + `guard_embodied_grounding`、用 oracle 自評充當具身增益 capability-delta tier（具身接地 Goodhart 自評放水）、`embodied_grounding_oracle` 讀寫 / 影響 / import 任何 generator（`operator_*_genesis` / `dimension_semantics_synthesizer` / `vocabulary_genesis`）或 `dimension_necessity_oracle` / held-out 語料（X，破 Rule 9.36.2 對抗分離）、grounded verdict 缺 `ExecutionObservation` 客觀資料卻放行納入（X，破 Rule 9.36.3 fail-closed，零觀測 false-green）、`guard_embodied_grounding` 盲信 oracle verdict 標籤而不獨立用 `output_quality_scorer` 重新計分驗證（X，破 Rule 9.36.3）、沙箱硬 timeout 卻 wall-clock wait 或不映 grounded_fail（X，FSM 等沙箱破有界停機，破 Rule 9.36.3）、把 embodied-grounding 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（X，破 Rule 9.36.4 / Rule 9.18.1）、未經 OPEN-X.x 私自開 HTTP 外聯做活體 canary 具身接地（X，破 OPEN-10.6 / Rule 9.36.5）
- `recursion_topology_view` / `guard_visualization_bounded` 自動 signoff 納入繞過人工 K=1、視覺化模組寫 FSM-STATE / 影響 churn / 影響 meta-loop 狀態（Y，破 Rule 9.37.4 read-only）、import 任何 generator（`operator_*_genesis` / `dimension_semantics_synthesizer` / `vocabulary_genesis`）或 `embodied_grounding_oracle` 並影響其輸出（Y，破 Rule 9.37.4 對抗分離）、渲染拓樸與 `to_dict()` 不同構卻放行（Y，破 Rule 9.37.2 拓樸防偽，視覺欺騙：畫的圖比跑的更良基/更簡單）、`guard_visualization_bounded` 盲信 renderer 輸出標籤而不獨立從 `to_dict()` 反解析重算圖比對（Y，破 Rule 9.37.2）、渲染逃逸 render budget（node/edge/depth/char）造成 token 爆炸 / OOM（Y，破 Rule 9.37.3 VisualizationBounded，須有界截斷 + 分頁而非無界渲染）、接地視圖以零觀測 false-green 渲染綠勾（Y，破 Rule 9.37.3，複用 Phase X fail-closed）、把 visualization 元迴圈併入單軌 `SDD_FSM.tla` 或新增第六形式化軌污染五軌 reachable（Y，破 Rule 9.37.4 / Rule 9.18.1）、未經 OPEN-Y.x 私自開 HTTP 外聯做活體 Playwright 軌跡渲染（Y，破 OPEN-10.6 / Rule 9.37.5）、或藉視覺化「簡化呈現」實質繞過 meta⁹（R-9.35.5）/ meta-oracle 自演化（人類凍結）紅線（Y，破 Rule 9.37.5）

### 核心特色

- 繼承 AISDLC v0.09 全部核心機制（Agent、Workflow、Scenario、按需載入）
- 新增 SDD 專屬模板（59 個：56 md + 3 yaml）、CI/CD 規格（9 個）、場景增強（10 個）
- 強制 SCG 閘門：每個開發階段都有規格合規檢查（SCG-0 ~ SCG-6）
- 支援全部 10 個場景：Greenfield、Brownfield、Refactoring、Documentation、DevOps、Integration、Migration、Performance、Security、Testing
- 內建 42 個 Claude Code Skills（33 繼承強化 + 9 SDD 核心）

📖 **SDD 核心原則**: [SDD_Core_Principles.md](guides/system/sdd/SDD_Core_Principles.md)
📖 **目錄結構規則**: [FILE_DIRECTORY_RULES.md](FILE_DIRECTORY_RULES.md)
📖 **SDD 快速指引**: [guides/system/sdd/SDD_GUIDE.md](guides/system/sdd/SDD_GUIDE.md)

---

## 核心參考指南

### SDD 專屬指南

| 指南 | 說明 | 使用時機 |
|------|------|---------|
| [SDD_Core_Principles.md](guides/system/sdd/SDD_Core_Principles.md) | SDD 三大支柱與 SCG 閘門定義 | 所有 SDD 場景 |
| [SDD_GUIDE.md](guides/system/sdd/SDD_GUIDE.md) | SDD 快速指引 | 新使用者入門 |
| [SDD_SPEC_FIRST_GATE.md](workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md) | Spec-First Gate 工作流 | SCG 閘門執行 |

### 場景增強文件

| 場景 | SDD 增強 | 說明 |
|------|---------|------|
| Greenfield | [SDD_GREENFIELD_ENHANCEMENT.md](scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md) | 全新專案的 SDD 強化流程 |
| Brownfield | [SDD_BROWNFIELD_ENHANCEMENT.md](scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md) | 逆向規格工程 + Gap Analysis |
| Refactoring | [SDD_REFACTORING_ENHANCEMENT.md](scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md) | Business Invariants + Mutation Testing |
| Documentation | [SDD_DOCUMENTATION_ENHANCEMENT.md](scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md) | Living Documentation + ADR 維護 |
| DevOps | [SDD_DEVOPS_ENHANCEMENT.md](scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md) | IaC-as-Spec + Pipeline Spec 先行 |
| Migration | [SDD_MIGRATION_ENHANCEMENT.md](scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md) | Migration Contract Map（MCM）先行 |
| Integration | [SDD_INTEGRATION_ENHANCEMENT.md](scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md) | Consumer-Driven Contract + OpenAPI First |
| Testing | [SDD_TESTING_ENHANCEMENT.md](scenarios/testing/SDD_TESTING_ENHANCEMENT.md) | Test Pyramid Spec + Quality Gate |
| Performance | [SDD_PERFORMANCE_ENHANCEMENT.md](scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md) | SLO/SLA Spec + PBS 先行 |
| Security | [SDD_SECURITY_ENHANCEMENT.md](scenarios/security/SDD_SECURITY_ENHANCEMENT.md) | STRIDE Threat Model + SAD 前置 |

### CI/CD 規格

| 規格 | 說明 |
|------|------|
| [SDD_CICD_BASE_LAYER.md](cicd/SDD_CICD_BASE_LAYER.md) | SDD CI/CD 基礎層（DocLint + SpecTrace + OpenAPI Validate + RTM Check） |
| [SDD_GREENFIELD_CICD.md](cicd/SDD_GREENFIELD_CICD.md) | Greenfield 專屬 CI/CD |
| [SDD_BROWNFIELD_CICD.md](cicd/SDD_BROWNFIELD_CICD.md) | Brownfield 專屬 CI/CD |
| [SDD_REFACTORING_CICD.md](cicd/SDD_REFACTORING_CICD.md) | Refactoring 專屬 CI/CD |
| [SDD_MIGRATION_CICD.md](cicd/SDD_MIGRATION_CICD.md) | Migration 專屬 CI/CD（MCM Validate + Contract Test Auto-Gen） |
| [SDD_INTEGRATION_CICD.md](cicd/SDD_INTEGRATION_CICD.md) | Integration 專屬 CI/CD（Consumer Contract Validate + Chaos Contract） |
| [SDD_TESTING_CICD.md](cicd/SDD_TESTING_CICD.md) | Testing 專屬 CI/CD（TestSpec Validate + Quality Gate + RTM Coverage） |
| [SDD_PERFORMANCE_CICD.md](cicd/SDD_PERFORMANCE_CICD.md) | Performance 專屬 CI/CD（PBS Validate + SLO Gate） |
| [SDD_SECURITY_CICD.md](cicd/SDD_SECURITY_CICD.md) | Security 專屬 CI/CD（STRIDE Validate + Compliance Matrix Auto-Check） |

### 繼承自 AISDLC v0.09 的指南

- **[AISDLC_ID_Naming_Convention.md](guides/system/naming/AISDLC_ID_Naming_Convention.md)** — 統一 ID 命名規範
- **[Estimation_Standards.md](guides/system/planning/Estimation_Standards.md)** — 估算標準化指南
- **[Document_Quality_Checklist.md](guides/system/quality/Document_Quality_Checklist.md)** — 文檔品質檢查清單
- **[C4_Model_Guidelines.md](guides/system/architecture/C4_Model_Guidelines.md)** — C4 架構設計指南

---

## 按需載入機制

採用與 AISDLC v0.09 相同的**情境感知按需載入**方式，初始載入僅需 ~200 tokens。

### 自動載入流程

```yaml
# 判斷：全新 Session 還是恢復 Session？

if build/reports/abort/CONTEXT-SNAPSHOT-*.md 存在:
  → 執行「Session 恢復流程」（見下方）
else:
  → 執行「全新 Session 流程」

# 全新 Session 流程
step_1: 讀取 AISDLC_SDD_INIT.md（本檔案）
step_2: 識別專案情境類型（greenfield / brownfield / refactoring / documentation / devops / migration / integration / testing / performance / security）
step_3: 從「Agent 自動載入配置表」讀取對應情境的配置
step_4: 自動載入 Primary Agents（讀取 YAML 並套用規則）
step_5: 記錄 Supporting Agents 列表（按需載入）
step_6: 載入對應 Workflows + SDD Enhancement
step_7: 確認 .claude/skills/ 已部署（含新增 Skill：spec-logical-validator, stage-compaction）
step_8: 初始化 FSM 狀態（INIT → SCENARIO_DETECT）
step_9: 顯示載入狀態確認
step_10: 開始執行 SOP（含 SDD 閘門）
```

### Session 恢復流程（ESCALATION / Token 耗盡後接力）

```yaml
session_resume:
  trigger: "build/reports/abort/ 目錄存在 CONTEXT-SNAPSHOT-*.md"
  
  steps:
    step_1: "讀取最新的 CONTEXT-SNAPSHOT-{date}.md"
    step_2: "顯示上次中止的 FSM 狀態與原因"
    step_3: "讀取對應 Stage 的 Stage Summary（build/reports/compaction/COMPACT-Stage{N}-*.md）"
    step_4: "確認所有已凍結文件仍存在於 docs/ 目錄"
    step_5: "轉入 RESUME_VERIFICATION 閘（Phase D / ACT-019）"
    step_5a: "重跑 abort_reason 對應的驗證（SLV / SCG / TFA）"
    step_5b: "比對本次結果 vs 上次 failure_pattern"
    step_5c_same_pattern: "警告人工『修正未生效』→ HUMAN_PENDING，increment cumulative_history.resume_blocked_count"
    step_5d_resolved: "詢問人工確認恢復點：{上次建議的 RESUME_STATE}"
    step_6: "重置 current_count 為 0（保留 cumulative_history）"
    step_7: "從 RESUME_STATE 恢復 FSM 執行"
    
  confirmation_message: |
    🔄 偵測到上次未完成的 SDD Session
    
    上次狀態：{FSM_STATE}
    中止原因：{reason}
    恢復點：{RESUME_STATE}
    
    已凍結 Stage：{list}
    未完成工作：{pending_items}
    
    請確認：
    1. 上次中止的問題已修復
    2. 從 {RESUME_STATE} 繼續
    
    輸入「確認恢復」繼續，或「全新開始」重新執行
```

---

## Agent 自動載入配置表

```yaml
auto_load_config:
  # 系統級 supporting agents — 對所有 scenarios 通用，由 Runtime 在對應事件觸發時載入
  system_wide_supporting_agents:
    - path: "agent/specialized/sdd-diagnostic-zh.yaml"
      load_at: "ESCALATION 觸發時（Phase G M1 self-healing diagnostic agent）"

  greenfield:
    primary_agents:
      - path: "agent/core/03.pm-po-agent-zh.yaml"
        role: "專案啟動、商業價值決策"
      - path: "agent/core/04.sa-analyst-zh.yaml"
        role: "需求分析、FRD 產出"
    supporting_agents:
      - path: "agent/core/02.ba-business-analyst-zh.yaml"
        load_at: "Stage 2 - 需求驗證"
      - path: "agent/core/05.sd-architect-zh.yaml"
        load_at: "Stage 3 - 技術架構設計 + ADR"
      - path: "agent/specialized/sd-web-architect-zh.yaml"
        load_at: "Stage 3 - sd-architect 的 extends 變體，Web 專案時載入"
      - path: "agent/specialized/sd-mobile-architect-zh.yaml"
        load_at: "Stage 3 - sd-architect 的 extends 變體，含 iOS/Android 時載入"
      - path: "agent/core/07.qa-tester-zh.yaml"
        load_at: "Stage 4 - 驗收標準 + RTM"
      - path: "agent/core/06.dev-developer-zh.yaml"
        load_at: "Stage 5 - 實施開發"
      - path: "agent/specialized/technical-writer-zh.yaml"
        load_at: "Living Documentation 維護"
    sdd_enhancement: "scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "requirements-extraction"
      - "validation-documentation"
      - "user-story-design"
      - "api-specification"
      - "consistency-check"
      - "interaction-analysis"
      - "adr-generation"
    sop_path: "scenarios/greenfield/SOP.md"
    cicd_spec: "cicd/SDD_GREENFIELD_CICD.md"

  brownfield:
    primary_agents:
      - path: "agent/core/04.sa-analyst-zh.yaml"
        role: "逆向規格工程、As-Is SRD、Gap Analysis"
      - path: "agent/specialized/dev-senior-zh.yaml"
        role: "技術評審、代碼分析"
    supporting_agents:
      - path: "agent/specialized/code-analyzer-zh.yaml"
        load_at: "Stage 1 - 代碼分析 + Tech Debt 量化"
      - path: "agent/core/05.sd-architect-zh.yaml"
        load_at: "Stage 3 - As-Is C4 + ADR Archaeology + To-Be SRD"
      - path: "agent/core/07.qa-tester-zh.yaml"
        load_at: "Stage 5 - As-Is 測試規格提取 + RTM"
      - path: "agent/core/06.dev-developer-zh.yaml"
        load_at: "Stage 8 - 實施開發"
      - path: "agent/specialized/technical-writer-zh.yaml"
        load_at: "Living Documentation 維護"
    sdd_enhancement: "scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "brownfield-analysis-flow"
      - "code-analysis-flow"
      - "requirements-extraction"
      - "change-management"
      - "api-specification"
      - "consistency-check"
      - "interaction-analysis"
      - "adr-generation"
    sop_path: "scenarios/brownfield/SOP.md"
    cicd_spec: "cicd/SDD_BROWNFIELD_CICD.md"

  refactoring:
    primary_agents:
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "Before/After 架構設計、重構 ADR"
      - path: "agent/specialized/code-analyzer-zh.yaml"
        role: "品質基準線、技術債量化"
    supporting_agents:
      - path: "agent/core/04.sa-analyst-zh.yaml"
        load_at: "Stage 0 - Business Invariants 提取"
      - path: "agent/specialized/dev-senior-zh.yaml"
        load_at: "Stage 2 - 漸進式重構策略"
      - path: "agent/core/07.qa-tester-zh.yaml"
        load_at: "Stage 3 - Invariant Test Contract + Mutation Testing"
      - path: "agent/core/06.dev-developer-zh.yaml"
        load_at: "Stage 4 - 重構實作"
      - path: "agent/specialized/technical-writer-zh.yaml"
        load_at: "Before/After 文件化"
    sdd_enhancement: "scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "refactoring-planning-flow"
      - "requirements-extraction"
      - "change-management"
      - "api-specification"
      - "consistency-check"
      - "adr-generation"
    sop_path: "scenarios/refactoring/SOP.md"
    cicd_spec: "cicd/SDD_REFACTORING_CICD.md"

  documentation:
    primary_agents:
      - path: "agent/specialized/technical-writer-zh.yaml"
        role: "Living Documentation、ADR 維護"
      - path: "agent/core/04.sa-analyst-zh.yaml"
        role: "需求文件補全、逆向規格"
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "架構文件、C4 補全"
    sdd_enhancement: "scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "documentation-flow"
      - "documentation-reconstruction-flow"
      - "adr-generation"
    sop_path: "scenarios/documentation/SOP.md"
    cicd_spec: "cicd/SDD_CICD_BASE_LAYER.md"

  devops:
    primary_agents:
      - path: "agent/specialized/devops-engineer-zh.yaml"
        role: "IaC 規格、Pipeline 設計"
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "基礎設施架構、ADR"
      - path: "agent/core/04.sa-analyst-zh.yaml"
        role: "基礎設施需求規格"
    sdd_enhancement: "scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "devops-setup-flow"
      - "adr-generation"
    sop_path: "scenarios/devops/SOP.md"
    cicd_spec: "cicd/SDD_CICD_BASE_LAYER.md"

  migration:
    primary_agents:
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "Migration Contract Map、遷移架構"
      - path: "agent/specialized/devops-engineer-zh.yaml"
        role: "遷移執行、Cutover 規格"
      - path: "agent/specialized/integration-specialist-zh.yaml"
        role: "系統整合、資料遷移契約"
    sdd_enhancement: "scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "migration-planning-flow"
      - "adr-generation"
    sop_path: "scenarios/migration/SOP.md"
    cicd_spec: "cicd/SDD_MIGRATION_CICD.md"

  integration:
    primary_agents:
      - path: "agent/specialized/integration-specialist-zh.yaml"
        role: "Consumer-Driven Contract、第三方 API 整合"
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "整合架構、ACL 設計"
      - path: "agent/core/07.qa-tester-zh.yaml"
        role: "Contract Testing、整合測試規格"
    sdd_enhancement: "scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "integration-analysis-flow"
      - "api-specification"
      - "adr-generation"
    sop_path: "scenarios/integration/SOP.md"
    cicd_spec: "cicd/SDD_INTEGRATION_CICD.md"

  testing:
    primary_agents:
      - path: "agent/specialized/qa-lead-zh.yaml"
        role: "測試策略、Quality Gate"
      - path: "agent/specialized/qa-automation-zh.yaml"
        role: "自動化測試框架、RTM 覆蓋"
      - path: "agent/core/07.qa-tester-zh.yaml"
        role: "測試規格、Contract Test"
    supporting_agents:
      - path: "agent/specialized/qa-web-tester-zh.yaml"
        load_at: "Web 測試場景"
      - path: "agent/specialized/qa-mobile-tester-zh.yaml"
        load_at: "Mobile 測試場景"
    sdd_enhancement: "scenarios/testing/SDD_TESTING_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "testing-strategy-flow"
      - "adr-generation"
    sop_path: "scenarios/testing/SOP.md"
    cicd_spec: "cicd/SDD_TESTING_CICD.md"

  performance:
    primary_agents:
      - path: "agent/specialized/performance-engineer-zh.yaml"
        role: "PBS Gate、SLO/SLA 規格、效能基準"
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "效能架構、優化 ADR"
    sdd_enhancement: "scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "performance-optimization-flow"
      - "adr-generation"
    sop_path: "scenarios/performance/SOP.md"
    cicd_spec: "cicd/SDD_PERFORMANCE_CICD.md"

  security:
    primary_agents:
      - path: "agent/specialized/security-engineer-zh.yaml"
        role: "STRIDE 威脅模型、SAD 設計"
      - path: "agent/specialized/compliance-officer-zh.yaml"
        role: "合規矩陣、法規對應"
      - path: "agent/core/05.sd-architect-zh.yaml"
        role: "信任邊界、安全架構"
    sdd_enhancement: "scenarios/security/SDD_SECURITY_ENHANCEMENT.md"
    workflows:
      - "sdd-spec-first-gate"
      - "security-assessment-flow"
      - "adr-generation"
    sop_path: "scenarios/security/SOP.md"
    cicd_spec: "cicd/SDD_SECURITY_CICD.md"
```

---

## Agent 完整清單

### Core Agents（7 個）

| 編號 | Agent 檔案 | 角色 |
|------|-----------|------|
| 01 | `agent/core/01.agent-template-zh.yaml` | Agent 模板（不直接使用） |
| 02 | `agent/core/02.ba-business-analyst-zh.yaml` | BA 業務分析師 |
| 03 | `agent/core/03.pm-po-agent-zh.yaml` | PM/PO 產品管理 |
| 04 | `agent/core/04.sa-analyst-zh.yaml` | SA 系統分析師（SDD 核心）|
| 05 | `agent/core/05.sd-architect-zh.yaml` | SD 系統設計師（SDD 核心）|
| 06 | `agent/core/06.dev-developer-zh.yaml` | 開發工程師 |
| 07 | `agent/core/07.qa-tester-zh.yaml` | QA 測試師（SDD 核心）|

### Specialized Agents（19 個）（v0.02 +sdd-playbook-compiler）

> 含 14 個場景專屬 + 4 個系統級 runtime agent（Phase D~H 自動化閉環產出，由 Runtime 在對應 observation 狀態觸發，非場景載入）+ 1 個橋接編譯 agent（v0.02 Phase Z / ACT-163：sdd-playbook-compiler）。

| Agent 檔案 | 角色 | 適用場景 |
|-----------|------|---------|
| `agent/specialized/code-analyzer-zh.yaml` | 代碼分析師 | Brownfield / Refactoring |
| `agent/specialized/compliance-officer-zh.yaml` | 合規專員 | Security |
| `agent/specialized/dev-senior-zh.yaml` | 資深開發工程師 | Brownfield / Refactoring |
| `agent/specialized/devops-engineer-zh.yaml` | DevOps 工程師 | DevOps / Migration |
| `agent/specialized/integration-specialist-zh.yaml` | 整合專家 | Integration / Migration |
| `agent/specialized/performance-engineer-zh.yaml` | 效能工程師 | Performance |
| `agent/specialized/qa-automation-zh.yaml` | QA 自動化工程師 | Testing |
| `agent/specialized/qa-lead-zh.yaml` | QA Lead | Testing |
| `agent/specialized/qa-mobile-tester-zh.yaml` | 行動端測試工程師 | Testing（Mobile）|
| `agent/specialized/qa-web-tester-zh.yaml` | Web 測試工程師 | Testing（Web）|
| `agent/specialized/sd-mobile-architect-zh.yaml` | 行動端架構師 | Mobile 開發 |
| `agent/specialized/sd-web-architect-zh.yaml` | Web 架構師 | Web 開發 |
| `agent/specialized/security-engineer-zh.yaml` | 安全工程師 | Security |
| `agent/specialized/technical-writer-zh.yaml` | 技術寫作師 | Documentation / All |
| `agent/specialized/sdd-orchestrator-zh.yaml` | SDD 閉環總指揮（Test→Fix 自動派遣） | Runtime / 系統級（Phase D） |
| `agent/specialized/sdd-diagnostic-zh.yaml` | 自癒診斷師（ESCALATION 分類 / auto_recoverable 判定） | Runtime / 系統級（Phase G M1） |
| `agent/specialized/sdd-evaluator-zh.yaml` | 執行接地評估器（沙箱運行 App、生成-評估分離對抗） | Runtime / 系統級（Phase H M1） |
| `agent/specialized/sdd-gc-zh.yaml` | 鷹架代謝 GC（規則 Scaffold ROI、退役過時鷹架） | Runtime / 系統級（Phase H M5） |
| `agent/specialized/sdd-playbook-compiler-zh.yaml` | SDD→AutoClaude Playbook 編譯者（凍結規格 → playbook YAML，R-9.38 保真） | Bridge / 系統級（v0.02 Phase Z / ACT-163） |

---

## Workflow 完整清單

### Core Workflows（`workflow/core/`）

| Workflow | 說明 |
|---------|------|
| `api-specification.md` | API 規格設計 |
| `change-management.md` | 變更管理 |
| `consistency-check.md` | 一致性驗證 |
| `interaction-analysis.md` | 互動分析 |
| `requirements-extraction.md` | 需求提取 |
| `sprint-execution.md` | Sprint 執行 |
| `user-story-design.md` | User Story 設計 |
| `validation-documentation.md` | 文件驗證 |

### SDD Gate Workflow（`workflow/sdd-spec-first-gate/`）

| Workflow | 說明 |
|---------|------|
| `SDD_SPEC_FIRST_GATE.md` | SCG-0 ~ SCG-6 閘門執行 |

### ADR Workflow（`workflow/adr-generation/`）

| Workflow | 說明 |
|---------|------|
| `ADR_GENERATION.md` | ADR 產生流程 |

### Scenario-Specific Workflows（`workflow/scenario-specific/`）

| Workflow | 說明 | 適用場景 |
|---------|------|---------|
| `brownfield-analysis-flow.md` | Brownfield 分析流程 | Brownfield |
| `code-analysis-flow.md` | 代碼分析流程 | Brownfield / Refactoring |
| `devops-setup-flow.md` | DevOps 設置流程 | DevOps |
| `documentation-flow.md` | 文件維護流程 | Documentation |
| `documentation-reconstruction-flow.md` | 文件重建流程 | Documentation |
| `greenfield-complete-flow.md` | Greenfield 完整流程 | Greenfield |
| `integration-analysis-flow.md` | 整合分析流程 | Integration |
| `migration-planning-flow.md` | 遷移規劃流程 | Migration |
| `performance-optimization-flow.md` | 效能優化流程 | Performance |
| `refactoring-planning-flow.md` | 重構規劃流程 | Refactoring |
| `security-assessment-flow.md` | 安全評估流程 | Security |
| `tech-stack-selection-flow.md` | 技術選型流程 | Greenfield / Brownfield |
| `testing-strategy-flow.md` | 測試策略流程 | Testing |

---

## Skills 完整清單（42 個）

位置：`.claude/skills/`

### SDD 核心 Skills（9 個）

| Skill | 說明 |
|-------|------|
| `sdd-gate` | SCG 閘門驗證（含 retry_count + pattern_detection） |
| `sdd-review` | SCG-4 PR Review 輔助 |
| `spec-compliance-check` | SDD 文件產出合規驗證 |
| `rtm-generate` | 需求追溯矩陣（RTM）生成與更新 |
| `brownfield-analysis` | 逆向規格工程、As-Is SRD |
| `adr-generate` | Architecture Decision Record 生成 |
| `spec-logical-validator` | 🆕 Spec 邏輯一致性驗證（SLV-001~006）— Phase A |
| `stage-compaction` | 🆕 Stage 間上下文壓縮（SPEC_FROZEN 觸發）— Phase B |
| `test-failure-analyzer` | 🆕 Test→Fix 閉環失敗分類（TFA，sdd-orchestrator 消費）— Phase D |

### 繼承強化 Skills（33 個）

| 分類 | Skills |
|------|-------|
| **需求 / 規劃** | `pm-planning`、`ba-analyst`、`sa-analyst`、`sprint-planning` |
| **架構設計** | `sd-architect`、`contract-generate` |
| **開發 / 審查** | `dev-review`、`code-review`、`refactoring-code-quality` |
| **測試** | `qa-testing`、`testing-strategy` |
| **DevOps** | `devops-docker`、`devops-github-actions`、`devops-gitlab-ci`、`devops-kubernetes`、`devops-monitoring` |
| **整合** | `integration-api-client`、`integration-aws`、`integration-database`、`integration-firebase`、`integration-oauth`、`integration-openai`、`integration-redis`、`integration-sendgrid`、`integration-stripe`、`integration-webhook` |
| **專項** | `mobile-development`、`performance-optimization`、`security-audit`、`compliance-audit`、`database-migration`、`documentation-api`、`release-management` |

---

## SDD 模板索引（59 個）

### docs_template/sdd/ 完整模板清單

| 分類 | 模板檔案 | 用途 | 適用場景 |
|------|---------|------|---------|
| **requirements** | `INVARIANT-SPEC-TEMPLATE.md` | Business Invariant 規格 | Refactoring |
| **requirements** | `THIRD-PARTY-API-RESEARCH-TEMPLATE.md` | 第三方 API 研究規格 | Integration |
| **requirements** | `AMBIGUITY-SCORER-SPEC.md` | 模糊度評分公式凍結規格（SCORER_VERSION） | All（Phase G M3） |
| **requirements** | `AMBIGUITY-WAIVER-TEMPLATE.md` | 模糊度豁免聲明 | All（Phase G M3） |
| **requirements** | `SPEC-PATCH-TEMPLATE.md` | 規格自癒 patch 提案（proposed） | All（Phase J） |
| **architecture** | `AS-IS-SRD-TEMPLATE.md` | 現況系統規格（逆向） | Brownfield |
| **architecture** | `TO-BE-SRD-TEMPLATE.md` | 目標系統規格 | Brownfield |
| **architecture** | `BEFORE-ARCH-TEMPLATE.md` | 重構前架構快照 | Refactoring |
| **architecture** | `AFTER-ARCH-TEMPLATE.md` | 重構後目標架構 | Refactoring |
| **architecture** | `SDD-COMPLIANCE-AUDIT-TEMPLATE.md` | SDD 合規審計 | All |
| **architecture** | `MIGRATION-CONTRACT-MAP-TEMPLATE.md` | 遷移契約映射 | Migration |
| **architecture** | `MIGRATION-ADR-TEMPLATE.md` | 遷移架構決策 | Migration |
| **architecture** | `TRUST-BOUNDARY-MAP-TEMPLATE.md` | 信任邊界圖 | Security |
| **architecture** | `SAD-TEMPLATE.md` | 安全架構文件 | Security |
| **architecture** | `INFRA-REQUIREMENTS-SPEC-TEMPLATE.md` | 基礎設施需求規格 | DevOps |
| **architecture** | `ADR-INTEGRATION-ACL-TEMPLATE.md` | 整合 ACL 架構決策 | Integration |
| **architecture** | `PATH-COST-MODEL-SPEC.md` | 路徑成本估算模型凍結規格 | All（Phase G M6） |
| **architecture** | `SPEC-ANCHOR-TEMPLATE.md` | 多模態 Spec Anchor（UI/API/DB/C4） | All（Phase F M3） |
| **adr** | `ADR-TEMPLATE.md` | 架構決策記錄 | All |
| **adr** | `ADR-INDEX.md` | ADR 索引 | All |
| **adr** | `AUTOMATION-FRAMEWORK-ADR-TEMPLATE.md` | 自動化框架選型 ADR | Testing |
| **adr** | `PERFORMANCE-OPTIMIZATION-ADR-TEMPLATE.md` | 效能優化 ADR | Performance |
| **api** | `API-COMPAT-TEMPLATE.md` | API 向後相容性聲明 | Brownfield |
| **api** | `CONSUMER-CONTRACT-TEMPLATE.yaml` | Consumer-Driven Contract | Integration |
| **api** | `PROVIDER-API-SPEC-TEMPLATE.yaml` | Provider API 規格 | Integration |
| **api** | `CONTRACT-TEMPLATE.yaml` | 通用 Contract 規格 | Integration / Testing |
| **testing** | `RTM-TEMPLATE.md` | 需求追蹤矩陣 | All |
| **testing** | `RTM-EXISTING-SYSTEM-TEMPLATE.md` | 既有系統 RTM | Brownfield |
| **testing** | `INVARIANT-TEST-CONTRACT-TEMPLATE.md` | 不變量測試契約 | Refactoring |
| **testing** | `TEST-STRATEGY-SPEC-TEMPLATE.md` | 測試策略規格 | Testing |
| **testing** | `TEST-CONTRACT-SPEC-TEMPLATE.md` | 測試契約規格 | Testing |
| **testing** | `DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md` | 缺陷分類規格 | Testing |
| **testing** | `LIVING-TEST-REPORT-TEMPLATE.md` | 活動測試報告 | Testing |
| **testing** | `PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` | 效能基準規格（PBS） | Performance |
| **testing** | `BASELINE-PERFORMANCE-REPORT-TEMPLATE.md` | 效能基準報告 | Performance |
| **testing** | `ASSET-INVENTORY-TEMPLATE.md` | 系統資產清單 | Security |
| **testing** | `STRIDE-THREAT-MODEL-TEMPLATE.md` | STRIDE 威脅模型 | Security |
| **testing** | `COMPLIANCE-MATRIX-TEMPLATE.md` | 合規對照矩陣 | Security |
| **testing** | `SECURITY-TEST-SPEC-TEMPLATE.md` | 安全測試規格 | Security |
| **testing** | `CHAOS-CONTRACT-TEMPLATE.md` | Chaos Contract 規格 | Integration |
| **testing** | `CONTRACT-TEST-SPEC-INTEGRATION-TEMPLATE.md` | 整合 Contract 測試規格 | Integration |
| **testing** | `CONTRACT-TEST-SPEC-MIGRATION-TEMPLATE.md` | 遷移 Contract 測試規格 | Migration |
| **testing** | `DATA-INTEGRITY-TEST-SPEC-TEMPLATE.md` | 資料完整性測試規格 | Migration |
| **testing** | `ENV-CONTRACT-SPEC-TEMPLATE.md` | 環境 Contract 規格 | DevOps |
| **testing** | `TEST-CONTRACT-NEGOTIATION-TEMPLATE.md` | 測試契約協商（生成-對抗閘） | Testing（Phase H） |
| **planning** | `GAP-ANALYSIS-TEMPLATE.md` | As-Is vs To-Be 差距分析 | Brownfield |
| **planning** | `REFACTOR-PLAN-TEMPLATE.md` | 重構計畫 | Refactoring |
| **quality** | `CODE-QUALITY-BASELINE-TEMPLATE.md` | 程式碼品質基準線 | Refactoring |
| **quality** | `TECH-DEBT-SPEC-TEMPLATE.md` | 技術債規格 | Brownfield / Refactoring |
| **quality** | `PBS-DRIFT-REPORT-TEMPLATE.md` | 效能基準漂移報告（PBS-DRIFT） | Performance（Phase E M3） |
| **development** | `LIVING-DOC-STRATEGY-TEMPLATE.md` | 活文件策略 | All |
| **deployment** | `PIPELINE-SPEC-TEMPLATE.md` | Pipeline 規格 | DevOps |
| **deployment** | `MONITORING-ALERT-SPEC-TEMPLATE.md` | 監控告警規格 | Performance / DevOps |
| **deployment** | `SECURITY-MONITORING-SPEC-TEMPLATE.md` | 安全監控規格 | Security |
| **deployment** | `INCIDENT-RESPONSE-SPEC-TEMPLATE.md` | 事件回應規格 | Security |
| **deployment** | `CUTOVER-SPEC-TEMPLATE.md` | 切換規格 | Migration |
| **deployment** | `ROLLBACK-SPEC-TEMPLATE.md` | 回滾規格 | Migration |
| **deployment** | `CANARY-SPEC-TEMPLATE.md` | 金絲雀部署規格 | Migration |
| **build** | `SDD_ABORT_REPORT_TEMPLATE.md` | ESCALATION 中止報告 | All |

> **模板使用規則**：從 `docs_template/sdd/` 複製到 `docs/` 後再填寫，禁止直接修改模板本身。

---

## 專案文件目錄結構

```
AISDLC_SDD_v0.01/
├── docs/                              # 專案文檔輸出目錄
│   ├── 01_requirements/               # 需求文檔 (PRD, FRD, Invariant Specs)
│   ├── 02_architecture/               # 架構設計 (SRD, C4, ADR)
│   │   ├── adr/                       # Architecture Decision Records
│   │   └── api/                       # API 規格與相容性聲明
│   ├── 03_testing/                    # 測試文檔 (RTM, Test Plans, Contracts)
│   │   └── contracts/                 # Invariant Test Contracts
│   ├── 04_planning/                   # 開發規劃 (Gap Analysis, Refactor Plan)
│   ├── 05_development/                # 開發文檔 (Living Doc Strategy)
│   ├── 06_quality/                    # 品質保證 (Code Quality, Tech Debt)
│   ├── 07_design/                     # 設計文檔 (UI/UX, Database)
│   └── 08_deployment/                 # 部署文檔 (CI/CD, Release Notes)
```

---

## SCG 閘門總覽

| Gate | 名稱 | 檢查內容 | 適用階段 |
|------|------|---------|---------|
| SCG-0 | Requirement Spec Gate | PRD/FRD 完整性、ID 追蹤 | 需求凍結前 |
| SCG-1 | Design Spec Gate | SRD + API Spec 完整性 | 設計凍結前 |
| SCG-2 | Architecture Review Gate | C4 圖 + ADR 完整性 | 架構凍結前 |
| SCG-3 | Contract Freeze Gate | OpenAPI 3.1 規格凍結 | 開發啟動前 |
| SCG-4 | Implementation Compliance Gate | 實作與規格一致性 | PR Review |
| SCG-5 | RTM Completeness Gate | 需求追蹤矩陣 100% | 交付前 |
| SCG-6 | Release Readiness Gate | 全閘門通過確認 | 發布前 |

---

## 閉環防護元件索引（Phase A~G 累積；Phase H~Y 元件見 governance/RULES_INDEX.md 與 CLAUDE.md §9.24~9.37）

### Phase A — 紙上規則層
| 元件 | 路徑 | 說明 |
|------|------|------|
| FSM 狀態機 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 形式化狀態轉換與 retry budget |
| 退場機制 | `workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md` | ESCALATION / TERMINATED 流程 |
| 上下文管理 | `workflow/sdd-context-governor/SDD_CONTEXT_GOVERNOR.md` | Token 預算監控 |
| 邏輯驗證 | `.claude/skills/spec-logical-validator/SKILL.md` | SLV-001~006 |
| Stage 壓縮 | `.claude/skills/stage-compaction/SKILL.md` | SPEC_FROZEN 後壓縮 |
| 中止報告 | `docs_template/sdd/build/SDD_ABORT_REPORT_TEMPLATE.md` | ESCALATION 時產出 |

### Phase D — Runtime Hook 強制層
| 元件 | 路徑 | 說明 |
|------|------|------|
| FSM Runtime（Python） | `tools/fsm_runtime/` | atomic write + .bak；唯一合法讀寫入口 |
| Hook 配置 | `.claude/settings.json` | hooks + env（SDD_SUBAGENT_CONTRACT / SDD_PATTERN_MATCH_THRESHOLD 預設聲明） |
| SessionStart Hook | `.claude/hooks/session_start.py` | reconcile CI-EVENT、逾時守門、decision_trace 注入 |
| PreToolUse Hook | `.claude/hooks/context_ledger_pre.py` | FSM guardrail + 90/95% token 閾值 |
| PostToolUse Hook | `.claude/hooks/context_ledger_post.py` | 實測 token 記帳 + conv-overhead 累計 |
| Orchestrator Agent | `agent/specialized/sdd-orchestrator-zh.yaml` | TFA 分類 + 自動派遣 |
| Failure Pattern Library | `knowledge/failure-patterns/` | FPL-001/002 |

### Phase E M1 — 精準停機
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| MD↔Python 雙源一致性 | `tools/fsm_runtime/tests/test_md_python_sync.py` | ACT-022 |
| HUMAN_PENDING 逾時守門 | `tools/fsm_runtime/timeout_checker.py` | ACT-023 |
| AUTO_COMPACT 單 Stage 限流 | `tools/fsm_runtime/fsm_runtime.py` | ACT-026 |

### Phase E M2 — 閉環品質鏈
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| Decision Trace（證據鏈） | `tools/fsm_runtime/state_loader.py` | ACT-025 |
| Conversation Ledger（精算） | `tools/fsm_runtime/conversation_ledger.py` | ACT-024 |
| File Lock（互斥寫入） | `tools/fsm_runtime/file_lock.py` | ACT-024 |
| Pattern Matcher（語意比對） | `tools/fsm_runtime/pattern_matcher.py` | ACT-021 |
| Subagent Dispatch Contract | `tools/fsm_runtime/subagent_contract.py` | ACT-020 |
| Event Reconciler（事務性） | `tools/fsm_runtime/event_reconciler.py` | ACT-020（支撐） |

### Phase E M2.5 — Chaos 有界停機驗收
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| Chaos Runner（100 輪故障注入） | `tools/fsm_runtime/chaos_runner.py` | ACT-029 |
| .bak 原子輪替恢復 | `tools/fsm_runtime/state_loader.py` | ACT-029 |
| Chaos 測試套件 | `tools/fsm_runtime/tests/test_chaos.py` | ACT-029 |
| Nightly CI Job | `cicd/SDD_CICD_BASE_LAYER.md`（FSM Chaos Verification） | ACT-029 |

### Phase E M3 — Production Feedback Layer（L5 入口）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| Production Monitor（HMAC + 時戳防重放） | `tools/fsm_runtime/production_monitor.py` | ACT-027 |
| SLO Event Inbox（File-based Pull） | `data/slo_events/` | ACT-027 |
| CI/CD 規格 | `cicd/SDD_PRODUCTION_FEEDBACK.md` | ACT-027 |
| PBS-DRIFT 報告模板 | `docs_template/sdd/quality/PBS-DRIFT-REPORT-TEMPLATE.md` | ACT-027 |
| PRODUCTION_SIGNAL 狀態 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` §Phase E M3 | ACT-027 |

### Phase E M4 — Learning Layer MVP（半自動規則產出）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| SLV Generator（FPL→SLV 草案） | `tools/fsm_runtime/slv_generator.py` | ACT-028 |
| Trust Level 寫入保護 | `slv_generator.write_rule_candidate` + `RuleOverwriteProtected` / `ImmutableFieldViolation` | ACT-028 |
| SLV-007 首個採納規則 | `.claude/skills/spec-logical-validator/rules/SLV-007.yaml` | ACT-028 |
| LEARNING_COMMIT 狀態 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` §Phase E M4 | ACT-028 |

### Phase G M1 — Self-Healing Layer（L5 入口）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| DiagnosticAgent（rule-based 6 sub_type 分類器） | `tools/fsm_runtime/diagnostic.py` + `agent/specialized/sdd-diagnostic-zh.yaml` | ACT-032 |
| Auto-Recovery 邊界（Rule 9.14.1/9.14.2） | `tools/fsm_runtime/auto_recovery.py` | ACT-033 |
| FSMRuntime self-healing API | `FSMRuntime.enter_auto_recovery` / `exit_auto_recovery` | ACT-033 |
| AUTO_RECOVERY_ATTEMPT 1-shot 復原狀態 | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` §Phase G M1 | ACT-033 |
| ESCALATION_FINAL 終局態（_BLOCKING_STATES） | `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` §Phase G M1 | ACT-034 |
| 30 fixture + 32 tests | `tools/fsm_runtime/tests/test_diagnostic.py` / `test_auto_recovery.py` | ACT-032/033/034 |

### Phase G M2 — Predictive Halt Layer（L5 入口）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| TrajectoryPredictor 4 信號預測 | `tools/fsm_runtime/trajectory_predictor.py` | ACT-035/036 |
| consult_predictor API | `tools/fsm_runtime/fsm_runtime.py` 預測諮詢入口 | ACT-035/036 |
| TRAJECTORY_PREDICTED 觀測態 | 不阻擋 tool calls，與 PRODUCTION_SIGNAL/LEARNING_COMMIT/HUB_SYNC 同類 | ACT-036 |
| Rule §9.15.1~9.15.4 | 4 條子規則（retry_count≥1 / confidence≥0.8 / PREDICTOR-MISS log / 同 gate ≤ 1 次） | ACT-035/036 |
| 20 新增 tests | `tools/fsm_runtime/tests/test_trajectory_predictor.py`（FP rate < 15%、b28 benchmark 33% 節省） | ACT-035/036 |

### Phase G M3 — Spec Ambiguity Quantifier（L5 成熟期）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| AmbiguityScorer 6 維度 rule-based | `tools/fsm_runtime/ambiguity_scorer.py` | ACT-037 |
| 評分公式凍結 | `docs_template/sdd/requirements/AMBIGUITY-SCORER-SPEC.md` | ACT-037 |
| 50 fixture corpus（25 模糊 + 25 清晰） | `tools/fsm_runtime/tests/fixtures/ambiguity_corpus/` | ACT-037 |
| WAIVER 模板 | `docs_template/sdd/requirements/AMBIGUITY-WAIVER-TEMPLATE.md` | ACT-038 |
| SCG-0 ambiguity gate（step 2a-bis） | `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | ACT-038 |
| Rule §9.16.1~9.16.4 | 範圍/閾值/override/SCORER_VERSION bump | ACT-037/038 |
| 31 新增 tests | `tools/fsm_runtime/tests/test_ambiguity_scorer.py`（corpus 準確率 ≥ 80%） | ACT-037/038 |

### Phase G M4 — Continuous Drift Monitor（L5 成熟期）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| drift_score 公式凍結 | `cicd/SDD_DRIFT_MONITOR.md` | ACT-039 |
| PostCommit hook（git native, advisory） | `.claude/hooks/post_commit_drift.py` | ACT-039 |
| Hook 安裝腳本（opt-in） | `tools/install_hooks/install_post_commit.{sh,ps1}` | ACT-039 |
| drift_monitor 核心 | `tools/fsm_runtime/drift_monitor.py` | ACT-040 |
| DRIFT_OBSERVATION 觀測態 | `transition_rules.OBSERVATION_STATES` + `SDD_FSM.tla` ObservationStates | ACT-040 |
| FSM enter/exit_drift_observation | `tools/fsm_runtime/fsm_runtime.py` | ACT-040 |
| DAILY drift report cron（02:30 UTC） | `cicd/SDD_CICD_BASE_LAYER.md` §Drift Daily Report | ACT-040 |
| Rule §9.17.1~9.17.4 | advisory/observation/consecutive/daily | ACT-039/040 |
| 16 新增 tests | `tests/test_drift_monitor.py` + `test_post_commit_drift.py` | ACT-039/040 |

### Phase G M6 — Cost-Aware Orchestration（L5 成熟期）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| PathCostEstimator（rolling-30 + 1.5σ） | `tools/fsm_runtime/path_cost.py` | ACT-043 |
| 估算模型凍結 | `docs_template/sdd/architecture/PATH-COST-MODEL-SPEC.md` | ACT-043 |
| 冷啟動 default 8000 tokens | OPEN-G.6 / Rule 9.19.1 | ACT-043 |
| FSM record_dispatch_rejection / reset | `tools/fsm_runtime/fsm_runtime.py` | ACT-044 |
| Orchestrator step_3_5_estimate_cost | `agent/specialized/sdd-orchestrator-zh.yaml` | ACT-044 |
| REJECTED log（schema_version=1） | `build/reports/orchestrator/REJECTED-{date}.yaml` | ACT-044 |
| CALIBRATION-WARN（連 5 次 > 50%） | `build/reports/orchestrator/CALIBRATION-WARN-{date}.yaml` | ACT-043 |
| Rule §9.19.1~9.19.4 | cold start / log / 3 拒 ESCALATION / 校準 | ACT-043/044 |
| 14 新增 tests | `tools/fsm_runtime/tests/test_path_cost.py`（誤差 < 30%、3 拒 ESCALATION） | ACT-043/044 |

### Phase G M5 — Formal Halt Verification（L5 MVP 收官）
| 元件 | 路徑 | 對應 ACT |
|------|------|----------|
| TLA+ FSM 規格 | `tools/fsm_runtime/formal/SDD_FSM.tla` | ACT-041 |
| TLC 模型檢查配置 | `tools/fsm_runtime/formal/SDD_FSM.cfg` | ACT-042 |
| TLC 執行入口（Linux/CI + Windows） | `tools/fsm_runtime/formal/run_tlc.sh` / `run_tlc.ps1` | ACT-042 |
| 雙源一致性測試（_HAPPY_PATH ↔ .tla） | `tools/fsm_runtime/tests/test_tla_python_sync.py` | ACT-041 |
| 4 條 invariant（TypeOK / RetryBounded / RecoveryBounded / NotInBothSets） | `SDD_FSM.tla:327-338` | ACT-041 |
| FSM Formal Verification CI step | `cicd/SDD_CICD_BASE_LAYER.md` §FSM Formal Verification | ACT-042 |
| 首次驗收覆蓋率（26/26 = 100%） | `build/reports/formal/TLC-COVERAGE-2026-04-26.md` | ACT-042 |

### Phase G MVP 收官總覽（tag: `phase-g-mvp`）
- **Self-Healing**（M1）→ **Predictive Halt**（M2）→ **Formal Halt Verification**（M5）三層協作達 L5 入口
- ESCALATION 從「死局」升級為「待診斷事件」：transient 自動復原 / structural 直升人工
- bounded halting 從「Chaos 100 輪經驗性」升級為「TLC 形式化證明」（reachable coverage 100%）
- token 浪費從「retry budget 燒滿才停」降為「2 信號預測切換 / 3 信號早停」

### 測試驗證現況（Phase G MVP 收官）
- 完整 fsm_runtime/tests：**340 passed**（M1: +32 / M2: +20 / M5: +3 雙源同步測試）
- DiagnosticAgent 30 fixture precision = 100%（≥ 93% 驗收標準）
- TrajectoryPredictor FP rate < 15%（30 fixture 校準）
- TLC reachable coverage = 100%（26/26，首次驗證 distinct=583 / generated=2853 / depth=32）
- chaos_runner 100 輪：bounded_ratio = 1.0、avg tokens = 1998（< baseline 25K × 80% = 20K）
- 五輪 QA 已累計修復 70+ 個 P0~P3 問題；Phase G M2 QA Round-1 已修復 P1×2 + P2×3

### Phase G Final 收官總覽（tag: `phase-g-final`，L5 Self-Driving SDD）
- **Spec Ambiguity Quantifier**（M3 / Rule 9.16）→ **Continuous Drift Monitor**（M4 / Rule 9.17）→ **Cost-Aware Orchestration**（M6 / Rule 9.19）三層協作
- AC 模糊性量化阻擋進入下游、commit-time drift 監控、dispatch 前估算成本三道閘門
- TLC reachable coverage 從 26/26 升 27/27（DRIFT_OBSERVATION 加入後維持 100%）

### 測試驗證現況（Phase G Final）
- 完整 fsm_runtime/tests：**401 passed**（M3: +31 / M4: +16 / M6: +14；MVP 後新增 61 tests）
- AmbiguityScorer 50 fixture 準確率 ≥ 80%（25 ambiguous + 25 clear）
- PostCommit hook 100 commit 平均 < 2s（Rule 9.17.1）；API drift 準確率 = 100%（10 fixture）
- PathCostEstimator rolling-30 誤差 < 30%（Rule 9.19.4）；冷啟動 default 8000（Rule 9.19.1）
- chaos_runner 100 輪：bounded_ratio = 1.0、avg tokens = 2098（< baseline 25K × 80%）
- TLC：reachable 27/27 = 100%、TypeOK / RetryBounded / RecoveryBounded / NotInBothSets 全 PASS

---

**來源框架**: AISDLC v0.09
**建立日期**: 2026-04-12
**最後更新**: 2026-06-06
**版本**: AISDLC-SDD v0.01 — **Phase Y 可解釋性轉向（meta⁸ 互遞迴呼叫圖人類視覺化儀表板）**

**演進鏈**：Phase A~G L5 Self-Driving → H L5 Reality-Grounded（執行接地 / 鷹架代謝 / 舵手交棒，ACT-045~058）→ I L6 Trustworthy Scaled（判官自審 / 成功結晶 / 艦隊並行 / 形式化雙證明，ACT-059~072）→ J L7 入口（對抗判官 / 規格自癒，ACT-073~080 / R-9.22）→ K 意圖規劃 + 辯證消歧 + 因果定位（ACT-081~088 / R-9.23）→ L 元停機 META_FSM 形式化 + 反事實重放 + 脆弱性（ACT-089~096 / R-9.24）→ M 組合 COMPOSITION_FSM（ACT-097~104 / R-9.25）→ N 全域組合最佳化 OPTIMIZATION_FSM（ACT-105~110 / R-9.26）→ O 自調目標權重 + 反 Goodhart held-out oracle（ACT-111~116 / R-9.27）→ P 全評分器一體化自校準（ACT-117~122 / R-9.28）→ Q 價值維度自我擴充（ACT-123~128 / R-9.29）→ R 維度語意自我發明（ACT-129~134 / R-9.30）→ S meta⁴ 詞彙自我擴充（ACT-135~140 / R-9.31）→ T meta⁵ 算子文法（ACT-141~146 / R-9.32）→ U meta⁶ 組合算子文法（ACT-147~149 / R-9.33）→ V meta⁷ 算子組合深度（ACT-150~152 / R-9.34）→ W meta⁸ 互遞迴 + 良基停機證書（ACT-153~155 / R-9.35）→ X 完整具身接地（ACT-156~158 / R-9.36）→ **Y 可解釋性視覺化儀表板（ACT-159~161 / R-9.37）**。詳見 CLAUDE.md §9.20~9.37 與 governance/RULES_INDEX.md。

**最新驗收**：pytest **1478 passed / 4 skip**、五軌 TLC（SDD / COMPOSITION / OPTIMIZATION / META / FLEET）No error（META 13 distinct 不回歸）、chaos 37 故障情境 bounded、最新 tag **v2026.06.06-01**、next_free **ACT-162 / R-9.38**。另：本機優先 CI 平價層（ADR-001）= Docker 迷你環境 + act + pre-commit/pre-push + Mock/地端LLM，單一真相源 `scripts/ci-gate.sh`。
