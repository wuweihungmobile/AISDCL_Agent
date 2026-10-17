# AutoSDD_improving_115 — 軌道① T1 再開：把 AISDLC_SDD 接成系統迴圈（Console × Bridge × AutoClaude × SDD）

> **狀態**：Architect 草稿（§1～§5；唯讀審查＋方案提案）。§6 起（裁決、四方審查表、零退化矩陣、休眠重宣告）由主控補。
> **軌道①**（驅動器＝`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`）。再開依據＝範本〈🏁〉T1（掌舵者直接立案）；T1 的最小響應本是直接做事，本輪因需跨軌設計才依範本開本檔。`docs/04_planning/AutoSDD_improving_114.md` §8 的休眠宣告自本檔起暫停效力；本輪收尾時依範本〈🏁〉重評休眠判準三條，並於末節重新宣告。
> **掌舵者 T1 原文（逐字）**：「1.AISDLC_SDD開發流程是否已經融入系統開發, 可以被整個系統(AutoClaude, AgentConsole等)充分利用?!」「==> 也調整AutoClaude, AgentConsole等做適當搭配!若需要請派出Architect / SA / SD / QA 四方專家進行規劃，分析，設計，實作，與獨立審查」「2.檢視整個AISDLC_SDD看看是否有不適當的地方(或BUGs等),讓他與整個系統耿完美融合!」「以AISDLC的程序(請Architect/SA/SD/Developer考慮如何規劃設計實作獨立審查?省去非必要文件，只留一定需要文件)」「以上若需要我決策，請依照最佳化, 最理想, 最適當的解決方案，我授權幫我決策」
> **三柱分佈**：**A 柱（主）**＝Console↔Bridge↔AutoClaude↔SDD 端到端迴圈（G-01、G-04～G-09、G-12～G-15）；**B 柱（次）**＝SDD LATEST 的接線面小改，以及框架「第一次被真實使用」的 dogfooding（G-03、G-04、G-06、G-10、G-11、G-16、G-17；框架內部 bug 體檢由另一位審查員處理，本檔只登記影響接線者）；**C 柱（小）**＝AutoClaude adapter 的 fail-closed 與摘要比對（G-02、G-06）。
> **人員**：主控 Fable 5.1（裁決、親驗、commit；不投票）；Architect（本草稿）、SA、SD、Developer（AutoClaude／SDD／Bridge／Backend／Frontend 各一棒）、QA 皆 Sonnet（`model: sonnet`）。本輪涉及安全（人工閘寫入動詞）與跨軌設計，依範本〈產品輪的固定成本瘦身〉的例外走四方。
> **文件瘦身聲明（掌舵者指示：只留必要文件）**：本輪只新增三份文件——本檔、一份 ADR、一份審查證據檔。契約變更寫進既有的契約與 openapi 檔（加節、不另開新檔）；不另寫各棒任務書（§4.4 棒次表即任務書）；不另寫 `rtm_backfill` 類檔（RTM 列隨交卷訊息、QA 單線合併）；dogfood 功能不另寫 SRS／C4／OpenAPI（以追溯 ID 引用上位文件，見 G-10）。

## §1 現況地圖

圖例：✅ 已接上且有真實使用證據；🟡 接上但無消費者、只在測試或只在單一路徑；❌ 未接上。證據為 `檔案:行`（HEAD 現查）。

| # | 能力 | AutoClaude | AISDLC_SDD | Bridge | Console | 證據 | 狀態 |
|---|---|---|---|---|---|---|---|
| 1 | 規格凍結硬閘 | `_assert_frozen`：`frozen_stages` 非空或狀態已過 SPEC_FROZEN 即放行；選檔取字母序第一個 | `record_spec_frozen` 只記階段名＋文件路徑，無內容摘要 | `/sdd/compile` 轉呼叫 adapter | 路徑 A fail-closed（422「SDD 規格檢查未通過」） | `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py:198-213,241-252`、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/state_loader.py:237-247`、`AgentConsole/engine-bridge/app/routers/sdd.py:159-194`、`AgentConsole/backend/src/main/java/com/aisdlc/console/application/service/ImportParser.java:150-166` | 🟡（G-02、G-06） |
| 2 | 規格→playbook 編譯 | adapter＋`sdd_compile` CLI（引擎面一次真跑） | Compily agent＋R-9.38 | `/sdd/compile` 回 tasks（非 playbook） | 路徑 A 匯入：Java 只收六欄，丟 max_retries／maintain_context／spec_digest | `AutoClaude/autoclaude/tools/sdd_compile.py:29-59`、`AgentConsole/backend/src/main/java/com/aisdlc/console/application/port/out/AgentBridge.java:47-49`、`ImportParser.java:222-239` | 🟡（G-08） |
| 3 | 治理執行（越閘 deny／違反記帳／digest 防漂移） | `SddGovernancePlugin` 已在生產 wiring 建構；`workflow_type∈{aisdlc,aisdlc_sdd}` 才啟用；`main.py` 無任何 SDD 專屬旗標，治理完全由 playbook 內的 `workflow_type`／`workflow_path` 驅動；整合測試用合成 FSM 狀態檔 | R-9.38 | `PlaybookIn.workflow_type` 鎖死 `auto`、無 `workflow_path` | 契約寫明不送 | `AutoClaude/autoclaude/core/wiring.py:240`、`AutoClaude/autoclaude/plugins/sdd_governance_plugin.py:39,165-174`、`AutoClaude/autoclaude/main.py:200-217`、`AutoClaude/autoclaude/models/playbook.py:83-84`、`AutoClaude/tests/integration/test_sdd_bridge/test_bridge_rtm_e2e.py:61-67`、`AgentConsole/engine-bridge/app/models.py:76-100`、`AgentConsole/docs/02_architecture/API_Contract_P3-6.md:1717` | CLI 路徑 ✅／Console 路徑 ❌（G-01） |
| 4 | RTM 逆向回寫 | `RtmWritebackPlugin` 只認 `sdd-` 前綴 step_id，寫 `<checkpoint_dir>/rtm` | —（諮詢報告，不覆寫人工 RTM） | `/sdd/fsm/{project}` 只回 `fsm_state.rtm_coverage`（現況恆 null） | 不顯示 | `AutoClaude/autoclaude/plugins/rtm_writeback_plugin.py:55-61`、`AutoClaude/autoclaude/core/wiring.py:299-314`、`AgentConsole/engine-bridge/app/runner.py:73-83`、`sdd.py:155`、`API_Contract_P3-6.md:1535` | 🟡（G-05） |
| 5 | FSM 唯讀遙測 | — | 狀態檔 | `/sdd/fsm`、`/sdd/fsm/{project}`（只看框架目錄） | 監控頁 SDD 卡：30 秒輪詢、全域、`retryHistory／frozenStages／rtmCoverage` 不顯示 | `sdd.py:61-156`、`AgentConsole/frontend/components/domain/monitor/SddEngineCard.tsx:17-27`、`AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md:313-320` | ✅（資料面只有一份停在 INIT 的狀態檔；G-13） |
| 6 | FSM 寫入／人工閘 | — | CLI：`transition／gate／spec-frozen／resume-from-escalation` | ❌ | ❌（D22③ 只讀） | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py:3288-3346`、`ADR-001-TechStack-Lock.md:318` | ❌（G-03、G-09） |
| 7 | 委派觀察態 AUTOCLAUDE_DELEGATED | 零引用 | `enter／exit_autoclaude_delegated` 已落地（TLA＋測試），CLI 無子命令；`sdd-orchestrator-zh.yaml` 與 `session_start.py` 對 AutoClaude／委派零提及（grep 零命中） | ❌ | ❌ | `fsm_runtime.py:3213-3285`、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/transition_rules.py:135-143`、`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md:415-416` | ❌（G-04） |
| 8 | 前端規劃 Archy（PRD→三層 playbook） | `AutoClaude/tools/three_tier_to_playbook.py`（開發腳本；輸出有 `workflow_type`、無 `workflow_path`） | agent `sdd-prd-to-playbook-zh.yaml` | ❌ | ❌（D22② 只用 GoalDecomposer） | `three_tier_to_playbook.py:124-146`、`docs/04_planning/Archive/AutoSDD_improving_95.md:1-15` | 🟡（2026-06 一次真跑：sdk 後端通、pty 後端未通；無生產入口，列延後） |
| 9 | 目標拆解＋有界自動凍結閘 | `GoalDecomposer`；`BoundedGoalFreezeGate` 只被 `build_goal_decomposer` 建構（僅測試呼叫） | — | 自建 GoalDecomposer，不帶閘 | 路徑 C | `AutoClaude/autoclaude/core/wiring.py:472-508`、`AgentConsole/engine-bridge/app/decompose.py:165` | 🟡 |
| 10 | 拓樸審批儀表板 | port＋adapter＋plugin（需 `workflow_path` 下既有產物） | renderer | ❌ | ❌ | `AutoClaude/autoclaude/plugins/_sdd_topology_signoff.py:13-35` | 🟡（不在迴圈關鍵路徑） |
| 11 | LATEST 判定／健康 | — | `AISDLC_SDD/scripts/sdd_version.py` 為 SSOT | 自行實作（DEF-AC-012）；`/health/deep` 的 `sdd` 僅資訊 | 顯示版本 | `AgentConsole/engine-bridge/app/settings.py:71-81`、`AgentConsole/engine-bridge/app/health.py:92-127` | ✅／🟡 |
| 12 | 流程面：本 repo 自身開發受 SDD 治理 | — | 根 router 在 `SDD_ACTIVE_VERSION` 未設時休眠；唯一 FSM 自建立起停在 INIT | — | — | `.claude/hooks/sdd_hook_router.py:18-24`、`ONBOARDING.md:150` | ❌（G-11） |

## §2 問題 1 判定

**一句話：部分。** 引擎面（CLI 路徑：凍結規格→編譯→治理執行→RTM 回寫）已接上，且有一次真跑（F-SBR-001，2026-10-11，macOS、haiku，見 `AutoClaude/docs/03_testing/SddBridge_RealRun_Evidence_20261011.md:4-5`）；產品面（Console）只接了「凍結規格匯入」與「唯讀狀態卡」兩點，治理、RTM、FSM 同步、人工閘皆未經 Console 路徑啟動；流程面（本 repo 自身開發）未受 SDD FSM 治理。

**校正 114 §7**：「三點北極星中只有 A 柱尚未被真實使用驗證」在引擎面已被兩次真跑部分推翻——improving_95（2026-06，Archy 三層路徑，sdk 後端 5 步全過；見 `docs/04_planning/Archive/AutoSDD_improving_95.md:139-157`）與 F-SBR-001（編譯路徑）；仍成立的是三塊——Console 路徑、SCG 前半段、FSM 同步（證據見下表與 G-01～G-04）。

**「是」的判準（C1～C6；皆須當回合證據，缺 C2 或 C6 即降為「部分」）**
- C1 綁定與唯一性：一個 Console 專案綁定一個 FSM 專案；同一狀態目錄有多個 FSM 專案時，凍結判定只認被綁定者，無法指認即 fail-closed（G-02、G-07）。
- C2 人工閘：FSM 在 HUMAN_PENDING 時，Console 以已認證 approver 核准凍結；FSM `decision_trace` 與 Console 稽核各有一筆且能互相對上；`frozen_stages` 帶文件摘要（G-03、G-06、G-09）。
- C3 治理執行：路徑 A 匯入並簽核後，批次以 `aisdlc_sdd` 啟動；引擎 PRE_RUN 實際載入規格，三點摘要（凍結時、匯入時、執行前）相符；step_id 為 `sdd-<場景>-at-…`（G-01、G-06、G-08）。
- C4 狀態同步：批次期間 FSM 為 AUTOCLAUDE_DELEGATED，完成回 IMPLEMENTATION，引擎升級型失敗進 ESCALATION；Console 卡片逐值對得上狀態檔（NFR-OBS-01；G-04）。
- C5 追溯：該批次的 RTM 覆蓋（AC／AT 覆蓋、失敗 AT、規格摘要）在 Console 可見並標「諮詢視圖」（G-05）。
- C6 自食：本 repo 一個真實功能（§4.2）依此迴圈做完；證據含 FSM 狀態檔、RTM 報告、Console API／畫面、一次失敗路徑（決定性替身）、QA 獨立審查（G-11）。

**產品面迴圈逐段**

| 段 | 內容 | 狀態 | 證據 |
|---|---|---|---|
| S1 | Console 專案／BRD-PRD 匯入 | ✅ | 三路徑 `ImportParser.java:112-123`；W4～W7 QA 已結案 |
| S2 | 在 SDD 下初始化專案（場景、FSM） | ❌ | Bridge 無寫入面；FSM 檔住框架目錄（`state_loader.py:31`），Docker 又以唯讀掛載 SDD（`ADR-001-TechStack-Lock.md:97`） |
| S3 | SCG-0…SPEC_FROZEN＋人工簽核鏡射 | ❌ | D22③ 只讀；本機唯一 FSM 停在 INIT、`decision_trace` 與 `frozen_stages` 皆空；F-SBR-001 以 CLI 直接 `transition` 到 HUMAN_PENDING 再 `spec-frozen`（`SddBridge_RealRun_Evidence_20261011.md:50-72`）⇒ SCG-0～3 的內容檢查從未被走過一次 |
| S4 | 凍結規格→`/sdd/compile`→草稿 | 🟡 | 端點與路徑 A 在；選檔不認專案、凍結不綁內容、語意損耗（G-02、G-06、G-08）。Bridge 的 `PlaybookTaskIn` 為了能原樣餵回 `/sdd/compile` 的任務而多收四欄（`models.py:55-61`），但後端不走這條：先轉成 Console 草稿樹，執行時再由 `PlaybookBuilder` 重組，欄位在轉換中流失 |
| S5 | 以 `aisdlc_sdd`＋`sdd_governance` 執行 | CLI ✅／Console ❌ | F-SBR-001；Console 永遠 `auto`（G-01） |
| S6 | RTM 回寫 | CLI ✅／Console ❌ | 證據檔 RTM 全覆蓋；Console 的 step_id 是 `G<g>-T<t>`（`AgentConsole/backend/src/main/java/com/aisdlc/console/domain/service/ExecutionPlanner.java:169`）⇒ plugin no-op，且無讀者（G-05） |
| S7 | Console 顯示 FSM／閘門／RTM／ESCALATION | 🟡 | FSM 卡唯讀 ✅；retry／frozen／RTM 不顯示；引擎 ESCALATION 只有 Bridge alert（`runner.py:424-430`） |
| S8 | FSM 與執行同步（委派態） | ❌ | 無生產者（G-04） |

**流程面：否。** ① 根 session 的 SDD hooks 休眠（`sdd_hook_router.py:18-24`），本機唯一 FSM 自 2026-07 建立起停在 INIT，沒有任何專案被走過；② AgentConsole 全程是 SA／SD 契約先行＋QA 獨立審查＋RTM 回填（`AgentConsole/docs/04_planning/Implementation_Plan.md` 波次紀錄）——角色等價、機制不等價（無 FSM、無 SCG 清單、無 TCS）；D22 宣告 SDD 為「選用引擎」；③ 本整合系列自己也不走 SDD FSM。

**「程式在但沒有生產路徑讀者」（W7 同款判法；`ADR-001-TechStack-Lock.md:296-305` 為範例）**
1. `build_goal_decomposer`／`BoundedGoalFreezeGate`（`wiring.py:472-508`）只有測試呼叫；Bridge 自建 `GoalDecomposer` 不帶閘（`decompose.py:165`）。
2. `WorkflowType.AISDLC_SDD`（`AutoClaude/autoclaude/execution/workflow_detector.py:17,44`）全樹沒有任何以它為條件的分支；實際以字串判斷的只有兩處——`SddGovernancePlugin` 的 `_SDD_WORKFLOWS`（`sdd_governance_plugin.py:39,165`）與 `translation_learner_plugin.py:93`（轉譯元學習只對 `aisdlc_sdd` 啟用）；Console 永不送，兩者在 Console 路徑皆不啟用。
3. `SddGovernancePlugin` 在「有 `workflow_type`、無 `workflow_path`」時（Archy 攤平路徑）啟用卻無規格可管，退化為只記帳（`sdd_governance_plugin.py:170-174`）；`snapshot()["fsm_state"]` 是常數 `IMPLEMENTATION`（`:182`），不是讀來的值。
4. `enter／exit_autoclaude_delegated`（`fsm_runtime.py:3216-3285`）：測試與 TLA 有，生產零呼叫（G-04）。
5. RTM-COVERAGE 報告：plugin 寫、無人讀；`enable_rtm_feedback` 預設 OFF 且 Console 永不送（`wiring.py:245-252`；`ADR-001-TechStack-Lock.md:300`）。
6. `spec_format_version`：Bridge 回、Console 的 `SddCompileResult` 不收（`AgentBridge.java:51`）。

## §3 缺口清單

面向：產＝產品面、流＝流程／治理面、框＝框架面。規模 S（≤1 日單棒）／M（單棒多檔）／L（跨棒）。持有面欄依鐵律七標出「常數／史料／消費端」分住不同檔者。

| ID | 面 | 級 | 現況證據 | 建議修法 | 規模 | 持有面 |
|---|---|---|---|---|---|---|
| G-01 | 產 | P1 | Console 路徑上治理與 RTM 皆不啟動：`PlaybookIn.workflow_type` 為 `Literal["auto"]` 且無 `workflow_path`（`models.py:76-100`）；後端只送七欄、step_id 為 `G<g>-T<t>`（`PlaybookBuilder.java:42-77`、`ExecutionPlanner.java:36,169`）；契約寫明 `workflow_type` 不送、step_id 為 `G<g>-T<t>`、`maintain_context` 不送（`API_Contract_P3-6.md:1717,1720,1728`）；plugin 只認 `sdd-` 前綴（`rtm_writeback_plugin.py:55-61`） | `POST /autoclaude/runs` 增選填 `sdd:{spec_dir, fsm_project}`，由 Bridge 於 `to_engine_dict()` 注入 `workflow_type=aisdlc_sdd`＋`workflow_path`（外部契約不開 `workflow_*` 欄）；後端對「範圍內任務全為 SDD 來源且 specDir 一致」的批次送 `sdd`、沿用 `passCriteriaSpec.stepId` 為 step_id；混合批次不啟用治理，201 回應 `warnings` 帶 `sdd_governance_inactive`（不靜默） | M | Bridge `models.py`／`runner.py`；Backend `PlaybookBuilder.java`、`ExecutionPlanner.java`、`ImportParser.java`、`AgentBridge.java`；契約與 openapi |
| G-02 | 產＋C | P1 | Spec-First 硬閘選檔不認專案：`_find_fsm_state` 取字母序第一個 `FSM-STATE-*.yaml`（`sdd_to_playbook_adapter.py:249-251`）；SDD 狀態目錄多專案共處（本機框架 build 目錄現有 8 個狀態檔：1 個框架自身＋7 個測試殘檔）；`/sdd/compile`、路徑 A、引擎 PRE_RUN 全走它 ⇒ 他專案已凍結即可放行未凍結專案（fail-open） | adapter 讀 `SDD_PROJECT`（與 SDD 側 `project_from_env` 同名，`state_loader.py:435-440`）取精確檔；同目錄多檔且無法指認⇒`SpecNotFrozenError`（「狀態檔不唯一」，fail-closed）；單檔行為不變 | S | `sdd_to_playbook_adapter.py`；`AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py`；Bridge `runner.py::_child_env` 注入 `SDD_PROJECT` |
| G-03 | 產＋框 | P1 | Console 專案沒有 SDD 前半段的可驅動面：狀態目錄硬編碼 `DEFAULT_STATE_DIR`（`state_loader.py:31`），無 env／CLI 覆寫；9 支生產檔引用 `build/reports/fsm`（conversation_ledger、file_lock、event_reconciler、arch_fitness、fsm_runtime、production_monitor、spec_monitor、state_loader、trajectory_predictor）；Docker 以唯讀掛載 SDD；現行唯一走通 SPEC_FROZEN 的是 F-SBR-001 未入庫驅動腳本（改寫該常數，`SddBridge_RealRun_Evidence_20261011.md:33-34`） | SDD LATEST 原地加 `SDD_STATE_DIR`（預設不變）並把 9 檔收斂到單一解析點；`SDD_STATE_DIR` 有設＝外部專案模式：治理 yaml 遙測回寫預設 OFF（D28 只護 session 內，`fsm_runtime.py:147-163`）；`spec-frozen` CLI 補 `--reason`；Bridge 以子行程呼叫 CLI（固定環境見 §4.3-A） | M | 上列 9 檔＋`fsm_runtime.py::_cli`；`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/`；`EVOLUTION_LOG.md`、`releases/CHANGELOG.md`；`FRAMEWORK_STATUS.md` 重生 |
| G-04 | 產＋框 | P2 | 委派態無生產者：進出 API 已落地但 CLI 無子命令（`fsm_runtime.py:3290-3293`）、AutoClaude 零引用、Bridge 零呼叫 ⇒ AutoClaude 執行期間 FSM 停在 IMPLEMENTATION，Console 卡片與實況不一致 | CLI 增 `delegate-enter`／`delegate-exit` 與 `negotiate-enter`／`negotiate-exit`（R-9.20.2 要求 SPEC_FROZEN 後先過談判閘，見 §5.1-4）；Bridge 於 SDD 批次 spawn 呼叫 enter、COMPLETED 呼 exit done、**引擎升級型** FAILED（判斷依據＝`runner.py:424-430` 設定的 `_escalation`）呼 exit failed；PAUSED／CANCELLED／額度停機／孤兒不動 FSM（`failed` 會進阻塞態 ESCALATION，不可把基礎設施故障映成它） | M | SDD `fsm_runtime.py`；Bridge 新模組＋`runner.py::_spawn/_finish_normally`；`SDD_AUTOCLAUDE_BRIDGE.md` |
| G-05 | 產 | P2 | RTM 生產者／消費者錯位：plugin 寫每個 run 工作區的 checkpoint 目錄下的 rtm 子目錄（`wiring.py:311-313`、`runner.py:78`）；Bridge 只讀 `fsm_state.rtm_coverage`（`sdd.py:155`），FSM schema 無此鍵；D22 以「超出本輪」否決 Bridge 另讀（`ADR-001-TechStack-Lock.md:319`） | Bridge 增 `GET /autoclaude/runs/{id}/rtm`（讀 `RTM-COVERAGE-*.yaml`，唯讀、標諮詢視圖）；後端投影；前端執行詳情加面板；`rtm_coverage` 欄維持保留位 | S | Bridge `AgentConsole/engine-bridge/app/routers/autoclaude.py`＋新模組；Backend `AgentBridge.java`／`BridgeHttpAdapter.java`／新 Controller；Frontend 執行詳情；契約 |
| G-06 | 產＋框＋C | P2 | 凍結不綁內容：`frozen_stages` 只存 `{stage, frozen_at, compaction_report, spec_docs}`（`state_loader.py:237-247`）；adapter 只驗「有凍結」不驗「凍結的就是這份」（`sdd_to_playbook_adapter.py:198-213`）；匯入摘要 `specDigest` 只存不比（`ImportParser.java:218`）⇒ 凍結後改 TCS 仍可編譯、匯入後改檔仍可執行（僅執行中 advisory 漂移事件，`sdd_governance_plugin.py:271-283`） | 凍結時對每份 doc 記 `spec_doc_digests`（加法式）；adapter 在摘要存在時比對，不符 fail-closed，舊狀態檔無摘要則維持現行並出聲一次；Bridge 於 `sdd` 批次 spawn 前核「凍結摘要＝匯入摘要＝現檔摘要」，不符 409 `spec_digest_changed` | M | SDD `state_loader.py`／`fsm_runtime.py`；adapter；Bridge；摘要鍵名的生產者（SDD）與消費者（adapter）分屬兩子專案 ⇒ 鍵名先定進 ADR |
| G-07 | 產 | P2 | Console 專案↔FSM 專案無關聯：SDD 卡自述「FSM 專案與 Console 專案是兩個不同的東西」（`SddEngineCard.tsx:24`）；`projects` 表沒有任何 SDD 綁定欄（僅有 `execution_path`，`AgentConsole/backend/src/main/resources/db/migration/V1__init.sql:10-13`） | Flyway 次號（現有最大 V11）加 `projects.sdd_project`／`sdd_spec_dir`（nullable）；路徑 A 成功時回填；專案詳情頁「SDD 治理」區顯示綁定與階段 | M | Backend 實體／DTO／Flyway／MiniBridge 假 Bridge；Frontend 專案詳情；契約與 openapi |
| G-08 | 產 | P2 | 路徑 A 語意損耗：`SddTask` 只六欄（`AgentBridge.java:47-49`）；`sddTask()` 的 maxRetries 傳 null（`ImportParser.java:238-239`）；契約規定 maintain_context 不送（`API_Contract_P3-6.md:1728`）⇒ 同一規格經 Console 與經 `sdd_compile` 的 playbook 不等價（SCG-4=5／SCG-5=2 重試、跨 AC 脈絡隔離皆失，對照 `sdd_to_playbook_adapter.py:152-171`） | 補齊欄位對映；新增對拍測試：同一 TCS 兩條路徑逐任務欄位相等（step_id／regex／evaluator／max_retries／maintain_context／spec_digest）；對拍測試放 Bridge tests | S | Backend `AgentBridge.java`／`ImportParser.java`／`PlaybookBuilder.java`；Bridge `models.py`；Bridge tests |
| G-09 | 產（安） | P2 | 新增 FSM 寫入動詞會擴大既有 L-6 缺口：Bridge 無認證（`AgentConsole/docs/02_architecture/Architecture.md:1111`），引擎子行程繼承 `os.environ`（`runner.py:203-210`），AI 步驟能直接呼叫「核准凍結」＝自己簽自己 | 寫入動詞須帶只有 backend 持有的權杖（`BRIDGE_SDD_WRITE_TOKEN`，未設＝動詞停用 503）；`_child_env` 剝除該變數；寫入只經 FSMRuntime CLI，Bridge 原始碼不得開寫 `FSM-STATE-*.yaml`（Rule 9 第 1 條，QA 以測試釘住） | S | Bridge `runner.py`／新模組／settings；Backend `BridgeHttpAdapter.java`；compose 環境與 `.env.example` |
| G-10 | 框 | P2 | SDD 沒有「增量變更」最小文件集：SCG-0～3 清單要求 PRD／FRD／SRD／API／C4／ADR／OpenAPI 全套（`AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md:114-140`），對小功能不可行；F-SBR-001 因此以 CLI 直跳 HUMAN_PENDING，未走閘門內容 | LATEST 原地於 gate workflow 與 `sdd-gate`／`spec-compliance-check` skills 增「增量（delta）」條款：每道閘門的清單可由對已凍結上位文件的追溯 ID 滿足；增量文件集＝FRD-lite（併入 TCS 檔頭）＋TCS，有新決策才寫 ADR、有 API 變更才寫 OpenAPI delta；不動 `_HAPPY_PATH` | M | SDD LATEST 的 `SDD_SPEC_FIRST_GATE.md` 與兩支 skill；`SDD_AUTOCLAUDE_BRIDGE.md` |
| G-11 | 流 | P2 | 本 repo 自身開發未受 SDD 治理（§2 流程面；`sdd_hook_router.py:18-24`） | 不強制全面套用（§5.2 退役）；本輪 dogfood 為首例；在 `SDD_AUTOCLAUDE_BRIDGE.md` 記「何時走 SDD 迴圈」判準（有 Python 可測 AT 且規格可凍結）；主控 session 不啟用 Rule 9 hooks（避免 FSM 阻塞態鎖死工具呼叫） | S | `SDD_AUTOCLAUDE_BRIDGE.md`；ADR |
| G-12 | 流 | P2 | 偏離登記缺口：`NFR-COMPAT-01`（`AgentConsole/docs/06_quality/RTM.md:260`）、`AgentConsole/CLAUDE.md:15,139`、`AgentConsole/engine-bridge/README.md:4`、`ADR-001-TechStack-Lock.md:318` 與掌舵者本輪裁決牴觸 | 一份新 ADR（`docs/04_planning/ADR/` 現存最大號＋1）取代 D22③「只讀」與 NFR-COMPAT-01「零侵入」為「最小侵入白名單」（列檔、理由、測試）；ADR-001 補一條指標；RTM 該列改驗證口徑（不刪列、不改號）；鐵律 7 與 README 同步改寫；Console PRD §0.5 該列加一句註記 | S | 新 ADR；`ADR-001-TechStack-Lock.md`；`RTM.md`；`AgentConsole/CLAUDE.md`；`docs/01_requirements/Agent_ConsoleUI_PRD.md` |
| G-13 | 產 | P3 | SDD 卡與 API 欄位不足：`retryHistory／frozenStages／rtmCoverage` 不顯示（`SddEngineCard.tsx:26`）；`/sdd/fsm/{project}` 不暴露 `escalation_history`、階段資訊（`sdd.py:142-156`）；治理事件只進引擎 observability log（`AutoClaude/autoclaude/infra/adapters/observability/local_logger.py:178-189`） | 契約 v1.5 加法式欄：`phase{name,order,blocking,observation}`、`escalation_history` 尾 5 筆；卡片補階段進度與 ESCALATION 標示（`phase` 投影即 §4.2 的 dogfood 標的）；治理事件進 Console 列延後 | S | Bridge `AgentConsole/engine-bridge/app/routers/sdd.py`＋新純函式；Backend `SddFsmState.java`／DTO；Frontend 卡片與 `AgentConsole/frontend/lib/domain/sdd.ts` |
| G-14 | 產 | P3 | 跨 run RTM 趨勢不累積：Console 每 run 一個 `checkpoint_dir`（`runstate.py:67`），`RTM-COVERAGE-HISTORY` 與 A 軌 L5 學習（`wiring.py:245-265`）在 Console 路徑無歷史可讀 | 延後（§5.2） | — | — |
| G-15 | 產 | P3 | 路徑 A 探測 `execution_path` 時 adapter 對全樹 `rglob("*.md")`，且樹內有框架範本時範本與真 TCS 同為精確命名⇒`spec_ambiguous` 使匯入 fail-closed（`sdd_to_playbook_adapter.py:257-278`、`ImportParser.java:150-166`） | 延後（§5.2）；dogfood 專案不放範本即不觸發 | — | — |
| G-16 | 框 | P3 | 文件漂移：`SDD_AUTOCLAUDE_BRIDGE.md` §5 寫「提案，未落地」與 `SDD_FSM_ENGINE.md:415-416`／ACT-172 已落地矛盾；§3 表 evaluator 模板仍寫 `python -m pytest`（adapter 已改裸 `pytest`，`sdd_to_playbook_adapter.py:47`）；§2 exit code 缺 5（`sdd_compile.py:105-109`）；`wiring.py:304-306` docstring 寫 `build/reports/rtm/` 與實際 `<checkpoint_dir>/rtm` 不符 | LATEST 原地改，並補「Console／Bridge 路徑」一節為單一 SOP；`wiring.py` docstring 隨 G-02 棒修 | S | `AISDLC_SDD/AISDLC_SDD_v0.30/workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；`wiring.py` |
| G-17 | 框 | P4 | 7 個 `FSM-STATE-test-<數字>.yaml` 測試殘檔留在框架真實狀態目錄，污染 Console `/engines/sdd` 清單（`ADR-001-TechStack-Lock.md:320` 已知） | 併入 G-03 的單一解析點（測試固件改用暫存狀態目錄）；轉另一位框架審查員 | S | SDD tests |

## §4 建議方案

### 4.1 裁決建議（掌舵者已授權最佳化決策；請主控裁決後寫入 §6）

| 編號 | 建議裁決 | 理由與取捨 |
|---|---|---|
| A1 | **窄寫入、不碰檔案**：SDD FSM 的所有寫入一律經 FSMRuntime CLI 子行程；Bridge 不開任何 `FSM-STATE-*.yaml` 寫入。修訂 D22③「Console 只讀」為「Console 只經 CLI 窄寫」 | D22③ 的理由是 Rule 9「繞過 FSMRuntime 直接讀寫狀態檔」，CLI 不繞過它；換來 PRD §0.4「signoff↔HUMAN_PENDING」的真對映；代價＝多一個寫入面（由 G-09 的權杖與測試圍住） |
| A2 | **FSM 狀態住專案根**：`SDD_STATE_DIR` 導向 `<execution_path>/build/reports/fsm`；框架目錄的狀態目錄只留給框架自身 B 軌 | Docker 唯讀掛載可行；Bridge 工作區受 `AgentConsole/.gitignore` 保護（已忽略 `build/` 與 `.workspace/`），使用者自己的專案根則須忽略 `build/reports/`（綁定時警告）；`/sdd/fsm*` 增選填 `root` |
| A3 | **人工閘只開一個寫動詞「核准凍結」**（HUMAN_PENDING→SPEC_FROZEN，帶 approver、理由、文件摘要）；init／gate／退回／恢復留在 SDD session（Bridge 在批次生命週期內自動呼叫的談判／委派動作不是人工閘） | `_HAPPY_PATH` 沒有 HUMAN_PENDING→SPEC_DRAFTING 的退回邊（`transition_rules.py:28`），補它須同步 TLA+（Rule 9.18.1），不在本輪 |
| A4 | **Bridge 為委派狀態的唯一同步者**；AutoClaude 不 import SDD，adapter 只讀環境變數 `SDD_PROJECT` | 維持 `docs/04_planning/ADR/ADR-XPLAT-010-root-subproject-boundary.md` §2.1（跨子專案以子行程／資料產物，不 import） |
| A5 | **「零侵入」改「最小侵入白名單」**，由新 ADR 登記（G-12） | 掌舵者本輪明示可調整兩引擎；白名單外的引擎改動仍禁止，仍可由 git diff 機械核對 |
| A6 | **伺服端注入，外部契約不開洞**：`PlaybookIn.workflow_type` 維持只收 `auto`；SDD 批次走新的 `sdd` 區塊，由 Bridge 注入 `workflow_*` | Console 無法任意指定治理模式或路徑；Bridge 預檢凍結與摘要後才 spawn |
| A7 | **增量 SDD**：LATEST 增「增量（delta）」條款（G-10）；本輪 dogfood 是它的第一個使用者 | 沒有它，「省去非必要文件」與「走真實 SCG 閘門」互斥 |

### 4.2 Dogfood 標的

| 標的 | 內容 | 優點 | 風險 | 建議 |
|---|---|---|---|---|
| **T-G** | Bridge 純函式：FSM `current_state` → 階段／阻塞／觀測旗標（SDD 卡階段進度＝G-13 的核心；階段分組由 SA 依 `transition_rules.py` 的主路徑與 `OBSERVATION_STATES`／阻塞集合定義） | 不在關鍵路徑；純函式可機械驗；Python 可用裸 `pytest`；價值真實（G-13 要用）；不碰根層 `tools/tests` 的鎖 | 小，AI 可能寫出弱測試（§5.1-2） | **採用** |
| T-A | Bridge RTM 摘要讀取器（G-05 核心） | 價值最高 | 在關鍵路徑上且自指：產物是顯示自己 RTM 的零件 | T-G 失敗時的備選 |
| T-C | Console 專案名→FSM 專案名淨化 | 極小 | 證明力弱 | 不選 |
| （排除） | adapter 選檔（G-02） | — | 安全閘不得由 AI 自寫自驗 | 人手寫、QA 審 |

T-G 規格輪廓（供 QA 寫 TCS；Gherkin 的 Then 必含引號字面值，使 regex 可推導、避免 `weak_regex`）：AC-001-1 主路徑各狀態回正確階段且序號單調（2 AT）；AC-001-2 觀測態（AUTOCLAUDE_DELEGATED 等）回 `observation=true` 與回歸階段；AC-001-3 阻塞態（ESCALATION、ESCALATION_FINAL、TERMINATED、TOKEN_BUDGET_CRITICAL）回 `blocking=true`；AC-001-4 容錯（未知字串、缺值、非字串一律 `UNKNOWN`，不拋例外；2 AT）。全部 Unit，約 6 AT。

### 4.3 契約草案（SA 精煉；全為加法式）

**A. 跨專案環境契約（唯一真相源＝新 ADR）**

| 名稱 | 讀者 | 設定者 | 語意 |
|---|---|---|---|
| `SDD_STATE_DIR` | SDD `state_loader`（新）；有設＝外部專案模式，治理 yaml 遙測回寫預設 OFF | Bridge（FSM CLI 子行程） | 存放 `FSM-STATE-*.yaml` 的目錄；未設行為不變 |
| `SDD_PROJECT` | SDD `project_from_env`（已有）；AutoClaude adapter（新增讀取） | Bridge（FSM CLI 與引擎子行程） | FSM 專案名；adapter 據此取精確狀態檔 |
| 固定環境 | — | Bridge（FSM CLI） | `PYTHONPATH=<SDD LATEST>`、`PYTHONDONTWRITEBYTECODE=1`、`SDD_ENABLE_RULE_FIRE_TELEMETRY=0`、`SDD_ENABLE_RULE_CATCH_TELEMETRY=0`；cwd＝SDD LATEST；argv＝`sys.executable -m tools.fsm_runtime.fsm_runtime`；子行程走 `procutil.popen_platform_kwargs()` |

**B. SDD CLI**（`fsm_runtime.py::_cli`；stdout 單行 JSON、stderr 全 ASCII；rc＝0 成功、2 轉態不合法、其餘非預期）：`delegate-enter --project P --playbook-ref R --reason T`；`delegate-exit --project P --decision done|failed --reason T`；`negotiate-enter`／`negotiate-exit --outcome agreed|underspecified`（API 已有，`fsm_runtime.py:1939-1979`，補 CLI 殼）；`spec-frozen` 增 `--reason`，並對每個 `--doc` 計 sha256 寫入 `frozen_stages[].spec_doc_digests`（缺檔＝rc 非 0；相對路徑解析基準由 SD 定，建議專案根）。

**C. Bridge（契約 v1.5）**
- `GET /sdd/fsm`、`GET /sdd/fsm/{project}` 增選填 query `root`（過 `BRIDGE_ALLOWED_PATH_ROOTS`）；回應增 `phase{name,order,blocking,observation}`（T-G 產物，W4 接線前為 null；Backend／Frontend 一律當選填、缺值顯示「—」）、`escalation_history`（尾 5 筆）。
- `POST /sdd/fsm/{project}:freeze`，body `{root, stage, docs[], approver, reason}`，header `X-Bridge-Token`；前置 `current_state==HUMAN_PENDING` 否則 409 `fsm_state_conflict`；未設權杖＝503 `sdd_write_disabled`；權杖錯＝403；成功回與 GET 同形的 FSM 摘要。
- `POST /autoclaude/runs` 增選填 `sdd:{spec_dir, fsm_project}`；有則：預檢（凍結＋三點摘要相符，否則 422 `spec_not_frozen`／409 `spec_digest_changed`）→ 注入 `workflow_type`、`workflow_path`、`SDD_PROJECT`、`SDD_STATE_DIR` → FSM 預檢：IMPLEMENTATION 直接放行；SPEC_FROZEN 依 R-9.20.2 走談判閘（`negotiate-enter`＋`negotiate-exit --outcome agreed`，reason 記 Console 簽核人；只在帶權杖的 backend 請求下啟動，而 backend 在 `requireSignedOff` 通過後才呼叫）；其餘狀態 409 `fsm_state_conflict` → `delegate-enter` → 終態 COMPLETED 呼 `delegate-exit done`、引擎升級型 FAILED 呼 `delegate-exit failed`；PAUSED／CANCELLED／額度停機／孤兒不動 FSM。含 `sdd` 區塊的 `POST /autoclaude/runs` 同樣須帶 `X-Bridge-Token`（它會觸發 FSM 寫入）。
- `GET /autoclaude/runs/{id}/rtm` 回 `{scenario, spec_digest, at{passed,total,pct}, ac{covered,total,pct}, failed_at_ids[], weak_regex_at_ids[], fully_covered, advisory:true}`；缺檔 404 `rtm_not_found`、壞檔 422 `rtm_unreadable`。
- `_child_env` 剝除 `BRIDGE_SDD_WRITE_TOKEN`。

**D. Backend**：Flyway 次號加 `projects.sdd_project`／`sdd_spec_dir`；`POST /api/v1/projects/{id}/sdd/freeze`（approver＝JWT subject、reason 必填、稽核一筆、轉呼 Bridge `:freeze`）；`GET /api/v1/executions/{runId}/rtm`；`GET /api/v1/engines/sdd` 依專案綁定帶 `root`；`PlaybookBuilder` 對 SDD 批次送 `sdd` 區塊並沿用 `passCriteriaSpec` 的 stepId／maxRetries／maintain_context／spec_digest／weak_regex。
**E. Frontend**：專案詳情「SDD 治理」區（綁定、階段、核准凍結鈕＋理由必填）；執行詳情「追溯覆蓋（諮詢）」面板；SDD 卡加階段進度與 ESCALATION 標示。
**F. 對拍測試**（放 Bridge tests，不碰根層 `tools/tests`、避免重釘稅；ADR-XPLAT-010 §2.1 要求跨專案一致性斷言在整合層）：(1) 同一 TCS 經 Console 路徑與 `sdd_compile` 逐任務欄位相等；(2) 真 SDD CLI＋真 adapter：兩專案狀態共處時只認綁定者；(3) 凍結後改 TCS⇒編譯 fail-closed；(4) Bridge 原始碼不含對 `FSM-STATE` 的寫入開檔。

### 4.4 棒次、並行性與出口閘門

並行鐵律（根 `CLAUDE.md` 鐵律七）：以下三組「一道鎖的常數／史料／消費端分住不同檔」必須同棒或先定契約——(a) `SDD_PROJECT`／`SDD_STATE_DIR`（SDD `state_loader.py` 讀、adapter 與 Bridge `runner.py` 設定／讀、ADR 與 README 記載）；(b) `spec_doc_digests` 鍵名（SDD 寫、adapter 讀）；(c) 委派映射表（Bridge 呼叫、SDD CLI 語意、契約文件）。動工前 `git status` 現查，他棒未提交檔不碰。

| 波 | 棒 | 內容 | 持有面（只准寫） | 並行性 | 出口閘門（指令以各子專案 CLAUDE.md 為準；Windows 一律 `Push-Location`…`Pop-Location` 成對、不裸 cd、讀 rc 不接管線） |
|---|---|---|---|---|---|
| W1 | SD | 細化 §4.1：委派映射、狀態目錄單一解析點、摘要綁定、權杖方案；ADR 草稿；就 R-9.20.2／9.20.3 與「Console 簽核＝談判 agreed」的對映給裁決建議（§5.1-4） | 新 ADR、`ADR-001-TechStack-Lock.md`、`Architecture.md` §10 | 先於 SA | SD 鏡獨立審 |
| W1 | SA | 契約 v1.5（§4.3）、openapi、錯誤 reason 常數、E2E 情境（含 FSM 檔逐值對拍） | `API_Contract_P3-6.md`、`openapi-p3-6.yaml` | SD 決策表定稿後 | 主控裁決＋獨立 Architect 鏡；契約自洽、與 §4.3 逐條對照；裁決後主控立即把 `AgentConsole/CLAUDE.md` 鐵律 7 改寫為「除新 ADR 白名單列出的檔外不准動」（Console 側各棒才不與本案牴觸） |
| W2 | Dev-AutoClaude | G-02、G-06（adapter 比對 `spec_doc_digests`）、G-16 的 `wiring.py` docstring | `sdd_to_playbook_adapter.py`、對應測試、`wiring.py` | 與 Dev-SDD／Dev-Bridge 並行（檔案互斥） | `python -m pytest tests/ -q`、`$env:PYTHONUTF8=1; lint-imports`、`ruff check <改到的檔>`、`python AutoClaude/tools/check_loc_budget.py --json`（adapter 屬 ≤400 tier，先現查餘裕，逼近就抽 helper） |
| W2 | Dev-SDD | G-03、G-04、G-06（SDD 側）、G-10、G-16、G-17；僅改 LATEST（`python AISDLC_SDD/scripts/sdd_version.py` 現查，v0.01 與中間版一律不碰） | LATEST 內 9 檔＋CLI＋tests＋workflow／skills 文件、`EVOLUTION_LOG.md`、`releases/CHANGELOG.md` | 並行 | `AISDLC_SDD/scripts/ci-gate.ps1`；LATEST 內 `python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q`；`python AISDLC_SDD/scripts/framework_status_snapshot.py --check`；TLC＝N/A，證據＝`git diff` 對 `_HAPPY_PATH` 與 `*.tla` 為空 |
| W2 | Dev-Bridge | G-01、G-04（Bridge 側）、G-05、G-06（預檢）、G-09、G-13（Bridge 側只做 `escalation_history`；`phase` 欄留空，待 W4 dogfood 產物搬入後接線）；以契約＋假 CLI 開發 | `AgentConsole/engine-bridge/**` | 並行；**整合步驟串行**：Dev-AutoClaude 與 Dev-SDD 主控親驗後才換真 CLI 跑對拍 | `ruff check`（`AgentConsole/engine-bridge` 與 monorepo 根視角各一次）、`python -m pytest -q`、`GET /health`、根層 `TestDirEntryPrimitivesAreAccountedFor`、`docker build` |
| W3 | Dev-Backend | G-01、G-05、G-06（預檢錯誤對映）、G-07、G-08、G-09、G-13 的後端半，以及 A3 核准凍結端點 | `AgentConsole/backend/**` | 與 Dev-Frontend 並行（契約定稿＋Bridge 契約測試過後） | `.\gradlew.bat clean build`（BUILD SUCCESSFUL、JaCoCo ≥80%、ArchUnit、Flyway＋`ddl-auto=validate`）；`MiniBridge.java` 同步 |
| W3 | Dev-Frontend | G-07（含 A3 核准凍結鈕）、G-05、G-13 的前端半 | `AgentConsole/frontend/**`（不改真後端 e2e spec） | 並行 | `npm run gen:api-p36`（型別重產 rc=0）；`npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`；Playwright mock spec 一律帶各自 `--output` |
| W4 | 主控＋QA | dogfood 全程（§4.5）；ADR 定稿 | 專案根在 Bridge 工作區（已 gitignore） | 串行 | §4.5 驗收清單 |
| W5 | QA | 獨立零信任審查（唯讀＋證據檔；RTM 單線合併）；一審全查、二審驗修復，PASS＝無 P≤2 | 審查證據檔、`RTM.md` | 最後 | 親跑各棒閘門；`gh run list --commit <完整 sha>` 雲端對帳（`agentconsole-ci` 路徑過濾已含 `AutoClaude/autoclaude/**` 與 `AISDLC_SDD/*/tools/fsm_runtime/**`，不需改 `.github/`） |

預期零根層 `tools/`、`.claude/`、`.github/` 異動；若 QA 認為需要，走收尾單人窗口（鐵律七）。

**最小集合與切線**：回答「是」需要 C1～C6 全成立＝W1～W5 全做。若額度或時程逼迫，切線依序為——W2 加 Dev-Bridge 整合（引擎面「是」，可獨立交付）→ W3（Console 面）→ A3 核准凍結與 G-06 摘要綁定（C2 必需）；砍掉任一段，§2 的答案維持「部分」，並把被砍項以 §5.2 的延後格登記（附再開症狀），不得留成口頭待辦。

### 4.5 Dogfood 流程與驗收（C6）

1. **D-0** 主控裁決標的；專案根建在 Bridge 工作區下；`SDD_PROJECT`／`SDD_STATE_DIR` 導向專案根；主控 session 不啟用 SDD hooks。
2. **D-1** SA 寫 FRD-lite（併入 TCS 檔頭）、QA 寫 TCS（AC→AT）；以增量條款逐閘跑 `/spec-logical-validator`、`/sdd-gate`，每個 PASS 附工具輸出，用 FSM CLI `gate` 記錄；到 HUMAN_PENDING。
3. **D-2** Console「核准凍結」（掌舵者本人，或主控代決並記 approver）→ FSM 凍結、`spec_doc_digests` 入檔。
4. **D-3** Console 路徑 A 匯入→簽核→執行（`sdd` 區塊、治理啟動、委派 enter）。真 claude 一次（haiku、Brain off、同 F-SBR 組態）；Windows 為主控機，先在此機試，不穩則改 macOS 並如實登記 Windows 未驗證。
5. **D-4** 完成→委派 exit→RTM 面板；**SCG-4 人工審查點**：QA 鏡獨立核 AI 寫的測試是否忠於 Gherkin（評估指令只證「有測試且綠」，見 §5.1-2），通過後主控以 Edit 搬入 Bridge 並接線 G-13 欄位。
6. **D-5** 失敗路徑與 CI 決定性 e2e：另備「替身專用 TCS 夾具」——替身 `aisdlc-mock-claude` 只回放 prompt 內的 `[KEYWORD]` 字樣且不寫檔（`AgentConsole/engine-bridge/app/mock_claude.py:14-22,74-79`），所以夾具的 Then 引號字面值取替身必然輸出的詞（成功路徑）／必不輸出的詞（失敗路徑），並預置測試檔使評估指令不依賴 AI；期望：成功→委派 exit done、FSM 回 IMPLEMENTATION；失敗→同特徵碼重試耗盡、引擎升級→FSM 進 ESCALATION、Console 卡片同步。此夾具進 Bridge tests，是 CI 唯一能每次重跑的 SDD 全鏈證據。
7. **D-6** NFR-OBS-01 四源對拍：FSM 檔↔Bridge API↔Console 畫面↔PG；落審查證據檔，缺陷落帳。

## §5 風險與誠實劃界

### 5.1 未驗證假設
1. **Windows 真跑**：F-SBR-001 只在 macOS（`FRD_Sdd_Bridge_Real_Run.md:244`）。此機 `claude.exe` 在 PATH、根 `.venv` 無 wexpect 故走 subprocess 後備（`AutoClaude/autoclaude/perception/pty_wrapper.py:29-33`）；此機 `Get-Command pytest` 解析到 pyenv 的 `.bat` shim，評估指令的裸 `pytest` 須由 Bridge 子行程環境把 `.venv\Scripts` 置前才指向專案環境——皆未驗證。
2. **評估指令的鑑別力**：AI 同時寫測試與程式，`pytest -k AT_x` 只證「有測試且綠」，Gherkin 並未機械綁定測試內容；RTM「AT 通過」≠「規格被滿足」。SCG-4 獨立審查才是真閘；UI 一律標「諮詢視圖」（架構評估紅線 8，`docs/02_architecture/Agent_Architecture_Integration_Assessment.md:248`）。
3. **狀態目錄收斂的完整性**：9 檔是對 `tools/` 下 `*.py` 的 grep 現查；skills 文件另有提及該路徑者（例如 stage-compaction skill 文字）；SD 須全樹掃（含 hooks、skills、workflow 文件）並逐一判定。
4. **委派與談判映射語意**：R-9.20.2 要求 SPEC_FROZEN 後先過 TEST_CONTRACT_NEGOTIATED（Dev／QA 簽署 oracle）才進 IMPLEMENTATION（`AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules/R-9.20-phase-h-gae.yaml:13`，`enforcement_mechanism: manual`；runtime 保留直達邊僅為向後相容，`transition_rules.py:31-35`）。本草稿的對映＝「Console 簽核匯入草稿 ＝ 談判 agreed」，並以 reason 記簽核人；但 9.20.3「oracle 對 Generator 不可見」在 AutoClaude 路徑本就不成立（測試由同一個 AI 寫，見 2），SD 須裁定此對映可接受，或另立 oracle 來源。`failed→ESCALATION` 為阻塞態，本草稿主張只在「引擎升級型」失敗才呼 failed，且未讀恢復規則——需 SD 以真 FSM 轉態驗證。
5. **增量條款能否被判斷型 skill 接受**：`sdd-gate`／`spec-compliance-check` 是 agent 判斷，增量條款可能被讀成放水；dogfood 前半段由 QA 獨立審視。
6. **FSM CLI 子行程開銷與競態**：每個動詞起一個 Python 子行程；每批次只在 spawn 與終態各一次，預期可忽略，未量測。SDD session 與 Bridge 同時寫同一狀態檔的競態：runtime 有 `file_lock.py` 與原子替換，跨行程行為未測。
7. **Docker**：SDD 唯讀掛載下 `__pycache__` 與遙測寫入須靠 `PYTHONDONTWRITEBYTECODE=1`、兩個遙測旗標、狀態目錄在可寫處；容器級未驗證。
8. **專案名淨化一致性**：Console 專案名→FSM 專案名須與 SDD `sanitize_component` 一致（大小寫、長度、保留字）；以綁定欄解決，回填自動值時走同一淨化。
9. **工作樹現況**：撰寫時 `git status` 有 QA 對 DEF-AC-013／014 複驗的未提交改動（`AgentConsole/frontend/tests/e2e/` 下），與本案無關，勿觸碰；動工前現查。

### 5.2 刻意不做（只准三分類）

**延後（各附一句可觀測的再開症狀）**
- Console 內由 PRD 產出凍結規格（Archy 三層 playbook 跑 SDD skills）。再開症狀：掌舵者要求「Console 一鍵從 BRD 走到 SPEC_FROZEN」，或任一 Console 專案因無法預先備妥 TCS 而被路徑 A 擋下。
- Console「退回修改」（HUMAN_PENDING→SPEC_DRAFTING，須改 `_HAPPY_PATH` 並同步 TLA+）。再開症狀：審批者因無退回出口而改用 CLI 繞過，或掌舵者要求。
- Console 一鍵 init／gate 動詞。再開症狀：需要在沒有 SDD session 的情況下建立 FSM 專案。
- IMPLEMENTATION 之後的閘門動詞（EXECUTION_EVALUATION、PR_REVIEW、RTM_VERIFY、RELEASE）在 Console 內驅動。再開症狀：掌舵者要求在 Console 內完成 SCG-4 以後的核准，或 FSM 因無人推進而長期停在 IMPLEMENTATION。
- 待審批清單與通知鈴納入 SDD 待核准。再開症狀：掌舵者回報 SDD 待核准沒出現在鈴或儀表板。
- CLI-only 路徑（無 Console）的 FSM 委派同步。再開症狀：掌舵者在純 CLI 路徑要求 FSM 反映 AutoClaude 執行狀態。
- 跨 run RTM 趨勢與 A 軌 L5 學習在 Console 路徑活化（G-14）。再開症狀：同一專案連續兩個 SDD 批次需要比較覆蓋趨勢。
- 路徑 A 探測改為顯式 specDir 優先並限掃描深度（G-15）。再開症狀：實際專案因 `spec_ambiguous` 或掃描逾時而匯入失敗。
- 治理事件（spec_drift／contract_violation）進 Console 告警。再開症狀：掌舵者要求在 Console 看到契約違反。
- `BoundedGoalFreezeGate` 接入 Bridge decompose。再開症狀：要求高階目標草稿在條件成立時自動 signoff。
- DEF-AC-012（Bridge 與 SSOT 的 LATEST 判定分歧）維持已登記。再開症狀：兩者在實機上回不同版本目錄。

**退役（附依據）**
- `NFR-COMPAT-01` 的「零侵入」字面與 `AgentConsole/CLAUDE.md` 鐵律 7、Bridge README 的同款宣稱——依據：T1 原文第二句明示可調整兩引擎；改為最小侵入白名單（A5）。
- `ADR-001-TechStack-Lock.md:319` 對「Bridge 另讀 RTM 檔」的否決——依據：否決理由是「超出本輪」，本輪即納入（G-05）。
- 架構評估報告紅線 6「Bridge 禁 import 引擎」——依據：ADR-001 的單一 venv 決策已取代（`AgentConsole/engine-bridge/app/models.py:91` 起 import `autoclaude`）；本輪不重議，但新增的 SDD 呼叫一律走子行程。

**立案（缺陷帳本 DEF 列，由主控入帳；原則同輪 fixed）**：G-01、G-02、G-06（產品缺陷）；G-16（文件漂移）；G-17（框架面 P4，轉框架審查員）。G-03、G-04、G-10 屬功能補足，以 RTM 新列追溯、不入缺陷帳。

### 5.3 與既有裁決的關係
- **D-16 輪詢**：維持；FSM 仍 30 秒輪詢，不加 SSE。
- **D-16／D22③「signoff 只讀」**：部分推翻——Console 側只新增兩類經 FSMRuntime CLI 的寫入：「核准凍結」（人工）與批次生命週期的談判／委派同步（自動，Bridge 發起）；其餘仍只讀；理由見 A1。
- **D22②「GoalDecomposer 為唯一分解器」**：維持。
- **ADR-XPLAT-010 §2.1**：維持——AutoClaude 與 SDD 互不 import；Bridge 以子行程呼叫 SDD CLI；adapter 只讀環境變數。
- **W7 無讀者旗標的教訓**：本案不送任何新的引擎旋鈕；新增的環境變數各有具名讀者與對拍測試（§4.3-F）。
- **根 `CLAUDE.md` 守衛面准入**：本案預期不新增守衛碼；若 QA 發現需要，先附暴露證據。
- **Rule 9**：不改 `_HAPPY_PATH`、不碰 `*.tla`；若 SD 發現必須改，立即停並回報（Rule 9.18.1）。
- **收尾**：push 後以 `gh run list --commit <完整 sha>` 對帳；終輪不回填；依範本〈🏁〉重評休眠判準並於末節重宣告。

## §6 主控裁決（2026-10-17；掌舵者授權「最佳化、最理想、最適當」代決，掌舵者可隨時以 T1 推翻）

框架自身體檢（問題 2）由獨立審查員並行完成：閘門全綠（v0.01 1478 支通過、v0.30 1979 支通過、`scripts/tests` 373 支通過，與 `ONBOARDING.md` §7 三格吻合；十支 lint rc=0），缺陷 S-01～S-20（P1 1／P2 4／P3 11／P4 4），原文住本輪 QA 證據檔〈附錄〉（主控於收尾時搬入）。本節把 G-xx 與 S-xx 合併裁決。

| 編號 | 裁決 | 落點 |
|---|---|---|
| D-115-01 | 採 A1：FSM 一切寫入只經 `FSMRuntime` CLI 子行程；Bridge 原始碼不得開寫 `FSM-STATE-*.yaml`（QA 以測試釘住）；D22③「只讀」修訂為「只經 CLI 窄寫」 | ADR-XPLAT-016、Bridge |
| D-115-02 | 採 A2：新增 `SDD_STATE_DIR`（未設行為不變；有設＝外部專案模式、治理 yaml 遙測回寫預設 OFF）；Console 專案的狀態目錄＝`<execution_path>/build/reports/fsm`；`/sdd/fsm*` 增選填 `root` | SDD LATEST、Bridge、Backend |
| D-115-03 | 採 A3：人工閘只開「核准凍結」一個寫動詞（HUMAN_PENDING→SPEC_FROZEN，帶 approver／理由／文件摘要）；退回邊不做（須改 `_HAPPY_PATH`＋TLA）、登 §5.2 延後 | SDD CLI、Bridge、Backend、Frontend |
| D-115-04 | 採 A4：Bridge 是委派／談判狀態唯一同步者；AutoClaude 與 SDD 互不 import，adapter 只讀 `SDD_PROJECT`（ADR-XPLAT-010 §2.1 維持） | 全部 |
| D-115-05 | 採 A5：「零侵入」改「最小侵入白名單」，登本輪唯一的新 ADR（`docs/04_planning/ADR/` 下編號 ADR-XPLAT-016、SD 撰寫，Proposed→收尾時 Accepted）；`NFR-COMPAT-01`、`AgentConsole/CLAUDE.md` 鐵律 7、Bridge README、PRD §0.5 註記由主控於收尾單人窗口同步 | ADR、收尾 |
| D-115-06 | 採 A6：外部契約不開 `workflow_*` 欄；SDD 批次以 `sdd` 區塊由 Bridge 伺服端注入，預檢（凍結＋三點摘要）不過不 spawn | Bridge、Backend |
| D-115-07 | 採 A7：LATEST 增「增量（delta）」條款；本輪 dogfood 為第一個使用者 | SDD LATEST |
| D-115-08 | Dogfood 標的＝T-G（Bridge 純函式 FSM 狀態→階段／阻塞／觀測旗標）；專案根建在 Bridge 工作區；SCG-4 由 QA 鏡獨立核 AI 寫的測試後，主控才搬入 Bridge 接線 G-13 | W4 |
| D-115-09 | 框架體檢併入：S-01（P1）補 FSM 寫入指令雙形態＋skills 同步；S-02 先修 LATEST 的 `.claude/settings.json`（＋ledger 的 PowerShell 分支＋回歸鎖），根層 router 條目屬守衛面、本輪無暴露證據 ⇒ 登理論洞附再開症狀「Windows 設 `SDD_ACTIVE_VERSION` 的真實 session 其 CONTEXT-LEDGER 缺 PowerShell 呼叫」；S-03 adapter 放寬 AT ID 文法並對「出現未編成 step 的 AT」出聲且 `sdd_compile` 回非零（模板 E 類 ID 不改）；S-04 adapter／Bridge／Backend 增選填 `spec_file`；S-05＝G-02；S-06＝G-16；S-07／S-08／S-15／S-18／S-19 文件改版本中性與訂正；S-09 測試沙盒＋刪除 7 支 `FSM-STATE-test-*.yaml` 殘檔（git 未追蹤）；S-10 Bridge 專案名白名單放寬到與 `component_sanitizer` 一致；S-11／S-12 adapter（模板增 `**scenario**:` 欄）；S-13 ci-gate 下限重釘＋新鮮度測試；S-14 根層 router 文案（每個 session 必印＝真實暴露）由主控收尾單人窗口改；S-16 測試改可攜寫法；S-17 可做可不做（P4） | 各棒 |
| D-115-10 | R-9.20.2 談判閘對映：「Console 簽核匯入草稿＝談判 agreed（reason 記簽核人）」暫採，由 SD 以真 FSM 轉態驗證後定案；`delegate-exit failed` 只對「引擎升級型」失敗（`runner.py` 設定 `_escalation` 者），其餘終態不動 FSM | SD、Bridge |
| D-115-11 | 文件集（掌舵者「只留必要文件」）：本檔＋ADR-XPLAT-016＋QA 於 W5 建立的審查證據檔（`docs/06_quality/` 下、檔名沿範本原名 AutoSDD_ZeroTrust_Audit_115）；契約寫進既有 `API_Contract_P3-6.md`（v1.5）與 `openapi-p3-6.yaml`；SDD 改動記 `EVOLUTION_LOG.md`／`releases/CHANGELOG.md`；不寫各棒任務書、不寫 `rtm_backfill_*`（RTM 列隨交卷訊息、QA 單線合併） | 全部 |
| D-115-12 | 棒次：W1 SD ∥ SA（SA 以 §4.3 為基線，SD 的差異由主控轉達）→ W2 Dev-AutoClaude ∥ Dev-SDD-RT（runtime／tests／settings／ci-gate）∥ Dev-SDD-DOC（workflow／skills／模板／README／規則文件）∥ Dev-Bridge（先以假 CLI）→ Bridge 真 CLI 整合（RT 棒主控親驗後）→ W3 Dev-Backend ∥ Dev-Frontend → W4 dogfood → W5 QA 獨立審查（一審全查、二審驗修復）。子代理一律 `model: sonnet`。LOC 事實（主控現查）：`sdd_to_playbook_adapter.py` 392 行（adapter tier ≤400，餘裕 8 行 ⇒ 新功能抽到新模組）、`sdd_compile.py` 128、`wiring.py` 463 | — |
| D-115-14 | SA 提出的循環依賴（核准凍結以專案為單位，而路徑 A 匯入要到 `confirm` 才建立專案、且要求規格已凍結）裁決：**Console 專案是錨**——路徑 A 匯入增選填 `targetProjectId`（`confirm` 時把草稿目標／任務併入該既有專案並回填 SDD 綁定，專案已有不同綁定則 409）；沒帶則維持現行「建立新專案」並以規格根回填綁定。核准凍結維持專案層端點，綁定＝`execution_path`（狀態目錄根）＋`sddProject`（預設＝專案名經 `component_sanitizer` 淨化，可編輯）。Dogfood 流程＝建專案→SDD session 在 `execution_path` 走閘門→Console 核准凍結→匯入到同一專案→簽核→執行。不採「佔位 P0 專案」（一個 FSM 專案綁兩個 Console 專案） | Backend、Frontend、契約 |
| D-115-15 | 委派退出語意（修訂 D-115-10 的「不動」）：`delegate-exit --decision done`＝「委派交還控制權、未升級」而非「成功」，成敗由後續閘門判。COMPLETED→done；引擎升級型 FAILED→failed（進 ESCALATION，恢復留在 SDD session 的 `resume-from-escalation`，Console 無恢復動詞＝§5.2 延後）；CANCELLED→done（reason 記 cancelled）；PAUSED／額度停機／孤兒→不動。預檢回收點：新 SDD 批次遇 FSM 仍在 AUTOCLAUDE_DELEGATED 時，若所引用的 run 已終態或不存在⇒Bridge 先 `delegate-exit done`（reason 記 reclaimed＋舊 run id）再前進；仍活著（RUNNING／PAUSED）⇒409 `fsm_state_conflict` | SD 驗證、Bridge |
| D-115-16 | SA 的 Q2／Q4／Q5 採 SA 建議（rtm 無報告 404 `rtm_not_found`；`sdd.approver`、compile 的 `fsm_project` 與回應 `spec_file`／`fsm_project` 採用；`ParsedResult` 四欄伺服器擁有、`unmapped_at_ids` 回 200 由 Console 轉警告、清單項不帶 `phase`、`spec_format_version` 只顯示）。AT 文法（S-03／S6）：正向 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；逆向 RTM 以前兩段歸 AC，多段尾綴不影響歸屬 | SD 定案、adapter、契約 |
| D-115-18 | SA 對齊後提出的五項：①採新端點 `PUT /api/v1/projects/{id}/sdd-binding`（OPERATOR 以上、稽核 `project.sdd.bind`；不擴充 Phase 2 的專案 PUT）；②`targetProjectId` 併入既有專案時專案層 `signedOff` 不動（草稿仍走專案 signoff）；③Bridge 路徑參數只收淨化後的 FSM 鍵，含 `/` 的原名不可由 URL 定址（已知邊界，Bridge 在回應帶 `fsm_project` 供呼叫端改用）；④`:resume`／`/restore` 對帶 `sdd` 的 run 會 `delegate-enter`＝FSM 寫入 ⇒ 同樣要 `X-Bridge-Token`（擴大 ADR §9 的兩個呼叫為四個；Backend 送）；⑤`expectedDigests` Console 層穿透、v1.5 畫面不送（無規格摘要元件） | 契約、Bridge、Backend |
| D-115-19 | Dev-Bridge 七項偏離全部採實況：`is_fsm_project_name` 尾端判準取 `rstrip(" .")` 不動點（照 ADR 字面會拒掉 sanitizer 自己的輸出）；上游 `sanitize_component` 截 80 字後不冪等＝SDD 側 P4（Bridge 鏡像逐字同源不修、測試釘現況）；approver 另拒前後空白；契約 §3.1.4 (b)「原名反查」不實作、由契約刪句（ADR 無此條，CLI 產生的檔名必等於標準鍵）；409／422 欄位頂層與 detail 並存為過渡；`sdd_governance_inactive` 由 Backend 出；resume／restore 的 CLI 呼叫在 `handle.lock` 內。根層 NTFS 站點表登記 `fsm_names.py` 為「鏡像接受器」（保持檔案 928 行、不喚醒棘輪） | Bridge、契約、收尾 |
| D-115-17 | 各棒交卷的「偏離 ADR」由主控逐條裁決，結果記在 §7 表（不另開文件）；偏離若屬「ADR 字面比實況嚴而實況有既有測試／生產端在用」一律採實況並回寫 ADR 附錄 | §7 |
| D-115-13 | 立案（缺陷帳本 `docs/06_quality/AutoSDD_Defect_Log.md`，`DEF-200-534` 起；同輪 fixed）：G-01、G-02（＝S-05）、G-06、G-16（＝S-06）、G-17（＝S-09）、S-01、S-02（LATEST 半）、S-03、S-04。其餘 S-xx P3／P4 不入帳，以本檔 §6 與審查證據檔為載體 | 收尾 |

## §9 四方審查閉環、缺口歸格與休眠重評（本節為本檔末節之前的結案帳；§8 零退化矩陣在其下）

### 9.1 四方審查表（範本〈🏁〉〈審查閉環的終止〉：PASS＝無 P≤2；一審全查、二審驗修復）

| 角色 | 審查者 | 結論 | 日期 | 範圍 | 處置 | 證據 |
|---|---|---|---|---|---|---|
| Architect | Sonnet，唯讀 | 問題 1＝部分；缺口 G-01～G-17（P1 三、P2 九、P3 四、P4 一） | 2026-10-17 | 三子專案整合面讀碼、F-SBR-001 與 improving_95 史料 | 全數裁決於 §6；P1／P2 皆同輪修（§7 各棒） | 本檔 §1～§5 |
| SDD 審查員（問題 2） | Sonnet，唯讀＋跑閘門 | 閘門全綠；S-01～S-20（P1 一、P2 四、P3 十一、P4 四） | 2026-10-17 | LATEST v0.30 全樹、十支 lint、ci-gate、hook 活性、平台掃描 | P1／P2 同輪修（`302aefd9`／`7197c3ca`）；P3 除 S-17 外同輪修；P4 登記（D-115-09） | 證據檔 §1 補註指路；本檔 §6 D-115-09 |
| SA／SD 鏡 | Sonnet（SA 二次對齊 ADR、SD 真 FSM 乾跑） | 契約 v1.5 與 ADR-XPLAT-016 逐條對齊（附錄 A 22 項、附錄 B S1～S8） | 2026-10-17 | 契約↔ADR↔實作 | 差異由主控裁決 D-115-14～19 | ADR 附錄 A／B／C；契約 §6.8 |
| QA 鏡（W5） | Sonnet，獨立（未參與實作與 dogfood） | **VERDICT: PASS**（無 P≤2；P3 六：Q-01／02／03／04／09／12、P4 六：Q-05～08／10／11，皆文字面） | 2026-10-18 | 全變更集 `38e46582..ae31e882`：閘門全部親跑、dogfood 證據複核、E2E-17 真後端 25／26 列、白名單機械核對、RTM 單線合併 | P3 全數當輪改字（Q-01 本節與 §7、Q-03／Q-12 ADR 附錄 C、Q-02／04／05／07／09 契約、Q-08／11 證據檔 §1 補註）；P4 登記於證據檔 §4（DEF-AC-030～034） | 證據檔 §2～§8 |
| 主控 | Fable 5.1 | 提案者，不投票 | — | — | 逐棒親驗（§7）、收尾單人窗口（NTFS 站點表、下限重釘、表②、帳本、文案） | §7、§8 |

### 9.2 缺口歸格（只准三分類；無「候選」）

| 類 | 條目 |
|---|---|
| 立案且同輪 fixed（帳本） | DEF-200-534～541（S-01／S-02 LATEST 半／S-03／S-04／G-02＝S-05／G-06／G-16＝S-06／G-17＝S-09）、DEF-200-542（G-01）；AgentConsole 面 DEF-AC-015～034 住證據檔 §1.9／§4（P3／P4，034 已修） |
| 同輪修、不入帳（P3／P4 文字或小修） | G-03／G-04／G-05／G-07／G-08／G-09／G-10／G-11／G-12／G-13（功能補足，以 RTM 新列追溯）；S-07／S-08／S-10／S-11／S-12／S-13／S-14／S-15／S-16／S-18／S-19 |
| 延後（各附再開症狀） | §5.2 延後清單十一項（Console 內由 PRD 產出凍結規格、退回修改邊、一鍵 init／gate、IMPLEMENTATION 之後閘門動詞、待審批清單納入 SDD、CLI-only 委派同步、G-14 跨 run RTM 趨勢、G-15 路徑 A 探測、治理事件進 Console、`BoundedGoalFreezeGate` 接入、DEF-AC-012）；S-17 七支 lint `--help`（症狀：有人照 `--help` 試用得 rc=1）；S-02 根層 router matcher（症狀見 D-115-09）；上游 `sanitize_component` 截 80 字後不冪等（症狀：名稱長於 80 字且第 80 字落在空白前的專案出現重複狀態檔） |
| 退役（附依據） | §5.2 退役三項（「零侵入」字面→最小侵入白名單；ADR-001 對 Bridge 另讀 RTM 的否決；架構評估紅線 6） |

### 9.3 休眠重評（範本〈🏁〉休眠判準三條）
1. 驅動本輪的規格＝掌舵者 T1 原文＋本檔 §2 判準 C1～C6＋ADR-XPLAT-016；C1～C6 皆以當回合證據成立（證據檔 §1.8，W5 第二眼 PASS）；§9.2 無未分類列 ✓
2. `python tools/check_defect_log_crossref.py --unresolved-count`：主控親跑「未結列數＝0」（§8 逐字）✓
3. 本檔無「下一輪候選」：未做項全部落在 §9.2 的延後（附症狀）或退役；W5 的 P4 住證據檔 §4 並附再開症狀 ✓

⇒ **軌道① 系列自本檔起重新休眠**（範圍結案；北極星不因此視為達成）。對掌舵者兩問的答案：問題 2（框架體檢）＝已完成、可從提示詞拿掉；問題 1（SDD 融入整個系統）＝**是**——範圍限 Windows、haiku、單機、Unit 類 AT（證據檔 §1.8／§1.10 的但書與 §8 未涵蓋），可從提示詞拿掉；再開只由範本〈🏁〉T1～T4 事件驅動。

## §8 零退化驗證矩陣（收尾單人窗口、主控親跑；逐字）

量測樹＝`dadb49f5`（矩陣起跑時 HEAD；其後僅 `4c24710c` 文件與 `45b74056` 兩支 Bridge 測試檔改動，不在下列各面的輸入內；Bridge 面另於 `45b74056` 工作樹補跑）。

| 檢查 | 命令 | 本輪實測 | 通過條件 |
|---|---|---|---|
| 缺陷帳本 | `python tools/check_defect_log_crossref.py --unresolved-count` | `未結列數＝0／全部 243 列｜warn=86 fail=98` | 未結列數＝0 |
| 根層 tools/tests 全套 | `python tools/run_root_unittests.py` | `✅ unittest 數量下限釘選通過：發現 5384 個測試（下限 5326）`，rc=0 | rc=0 |
| AutoClaude 全套 | `python -m pytest tests/ -q -n 8 --dist loadgroup` | `5875 passed, 7 skipped, 14 warnings in 54.18s`；`lint-imports` `Contracts: 9 kept, 0 broken.` | rc=0、9 kept |
| AISDLC_SDD 閘門 | `AISDLC_SDD/scripts/ci-gate.ps1` | `逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:2140 scripts/tests:383`，rc=0；TLC＝N/A（`transition_rules.py` 與 `formal/` diff 為空，W5 核） | rc=0 |
| Bridge | `ruff check` 根視角；`pytest tests/test_fsm_phase.py tests/test_sdd_dogfood_fixture.py -n 4`（`45b74056` 樹） | `All checks passed!`；`81 passed`（xdist 4 worker 收集一致）；全套 `996 passed, 24 skipped`＝他包回報（W5 於 `ae31e882`、Dev-Bridge 於最終樹各一次） | rc=0 |
| Backend | `.\gradlew.bat clean build --console=plain` | `BUILD SUCCESSFUL`（1946 支、0 失敗＝他包回報；主控只讀 BUILD 結果行） | BUILD SUCCESSFUL |
| Frontend | `npm run lint`／`npx tsc --noEmit`／`npx vitest run` | rc 皆 0；`Tests 1122 passed (1122)` | rc=0 |
| 文件鎖 | `check_pytest_baseline_sites`／`check_handoff_carriers`／`TestR81GhostPathClaims` | 皆 rc=0（本輪多次現跑；最近一次於 QA 交卷後） | rc=0 |
| 雲端 | `gh run list` 對 `5593e178`：五支 success；對 `ae31e882`：root-infra／macos／windows success、agentconsole-ci 紅（xdist 收集不一致，修於 `45b74056`）；最終 HEAD 的 run 由收尾 push 後現查 | 觸發的 workflow 皆 success |

## §7 各棒交卷與主控親驗（W2 起逐棒填；「他包回報」與「主控親跑」分開寫）

| 棒 | commit | 主控親跑（當回合逐字） | 接受的偏離（D-115-17） | 未做／待整合 |
|---|---|---|---|---|
| Dev-AutoClaude | `7197c3ca`（16 檔，+1975／−96） | 聚焦七檔 `377 passed`（`-n 0`）；全套 `5875 passed, 7 skipped in 57.20s`（`-n 8 --dist loadgroup`）；`lint-imports` `Contracts: 9 kept, 0 broken.`；`ruff check` 16 檔 `All checks passed!`；`check_loc_budget.py --json` rc=0（adapter 計價 343/400、`_sdd_frozen_gate` 123/400） | D1 版本／場景宣告收 HTML 註解形、表格列形與 BOM 行首；D2 掃描略過圍欄程式碼區塊；D3 `sdd.at_unmapped` 事件多帶 `reasons`；D4 `ac_id_of_at()` 一家；D5 壞 YAML 一律 `SpecNotFrozenError`、`spec_dir` 為檔又給 `spec_file` ⇒ `ValueError`；D6 `tests/conftest.py` autouse 隔離 `SDD_PROJECT` | N1 專案鍵 NFC／NFD 未正規化（Bridge 先淨化）；N2 官方模板未讀進 AutoClaude 測試（一次性探針：模板本體編譯 unmapped＝`AT-001-1-1`／`AT-001-1-2`、rc 6），交 QA；N3 macOS／Linux／Docker 未實跑；N4 §15 對拍屬 Bridge 側。他包回報：突變鏡 23 個修法逐一拿掉皆 KILLED |
| Dev-SDD-RT | `302aefd9`（與 DOC 同 commit） | `ci-gate.ps1` rc=0：`AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:2140 scripts/tests:383`、v0.30 `2140 passed, 6 skipped`、arch_fitness `fail=0 warn=3`；`framework_status_snapshot.py --check` rc=0；九支 lint rc=0；v0.01 與中間版 `git status` 零筆、`transition_rules.py` 與 `formal/` diff 空；`git diff --check` rc=0 | `--digest` 需 ≥1 `--doc`；`--root` 須絕對且存在、沒搭 `--digest` 為 rc 2；摘要鍵取 `resolve()` 後相對 root 的 POSIX 路徑（Windows 為磁碟實際大小寫）；`--digest` 無 `--json` 時沿用人讀輸出；兩支 hook 各持 `_resolve_ledger_dir()`；沙盒另導向 abort／test-analysis；`test_e2e_smoke` hook 子行程帶 `SDD_STATE_DIR` | 〔未驗〕`claude --debug hooks` 對 PowerShell matcher 正負兩面、Docker 容器級、mac／linux；〔未跑〕chaos_runner 100 輪；下限餘裕為推算（mac≈2135 最緊）；他包回報：突變 17/17 detected、chaos 34 支通過、`build/reports` 497 檔 sha256 零差異。收尾單人窗口：`skip_group_policy.py` untagged 表、`sync_onboarding_baselines.py --write --with-slow`、`fsm_names.py` 登 NTFS 站點表 |
| Dev-SDD-DOC | `302aefd9`（與 RT 同 commit） | 同上列（RT＋DOC 合併後的工作樹一次親跑） | 見上一列（TCS 模板 E 類改寫、S-08 範圍放大、README 去版號範圍放大、ADR §6.3① 由 Backend 擋、`--retry-reset` 無對應動詞只註明） | 同族殘留見 EVOLUTION_LOG〈同族殘留〉 |
| Dev-Bridge（T-G 搬入） | `ae31e882` | ruff 根視角 rc=0；聚焦六檔 `324 passed, 2 skipped`；`git diff --check` rc=0 | 搬入只改檔名／import／型別／docstring／對映表唯讀包裝；順手修壞檔 `current_state` 非字串 500→200 | 他包回報：全套 996 通過／24 略過、煙霧 phase 非 null；雲端 agentconsole-ci 對 `ae31e882` 紅＝`test_fsm_phase` 參數化 id 跨 xdist worker 不一致（收尾修） |
| W5 QA（獨立鏡） | 見 §9 | 主控親驗：`npm run lint` rc=0、`tsc` rc=0、RTM Grep 現查 392 列全 ✅、baseline sites rc=0、carriers rc=0、diff --check rc=0 | — | VERDICT PASS（無 P≤2）；P3 六／P4 六皆文字面（證據檔 §4）；未涵蓋：Docker 全棧、POSIX／macOS、真 AI、S-02 活體 |
| Dev-Bridge | `2f643ae2`（36 檔）＋修復 `e19814b4` | `ruff check` 兩視角 rc=0；`python -m pytest -q`（根 `.venv` 直譯器、序列）`898 passed, 25 skipped`；根層 `TestDirEntryPrimitivesAreAccountedFor` OK；`docker build`（context＝monorepo 根）rc=0；修復後 `test_spec_digest`＋`test_sdd_freeze` 本機 77 支、Linux 映像內 78 支通過 | D-115-19 七項（尾端判準不動點、approver 拒前後空白、原名反查不實作、頂層與 detail 並存、`sdd_governance_inactive` 由 Backend 出、resume／restore CLI 呼叫在 `handle.lock` 內、上游 sanitize 不冪等＝SDD 側 P4） | 他包回報：uvicorn 18089 煙霧、映像內真 CLI 11 支、突變 12/12 KILLED；〔未驗〕Docker 全棧（compose）、macOS／Linux 主機直跑（只在 Linux 容器內驗）；雲端 agentconsole-ci 對 `8d0aa093` 紅＝`file_digest` 先量大小把 POSIX 目錄（st_size 4096）判成超限，修於 `e19814b4` |
| Dev-Backend | `93ac5ecf`（70 檔 M＋36 新） | `.\gradlew.bat clean build --console=plain` `BUILD SUCCESSFUL in 1m 54s`（測試結果行與 JaCoCo／Checkstyle／ArchUnit 細數＝他包回報：1946 支 0 失敗、96.85%／85.80%、0、8）；`backend\build` 最長真實路徑 238；`git diff --check` rc=0；改動全在 `backend/` | 九項（sdd-binding 400 先於 404；匯入 specDir 與目標已綁不同也 409；規格根前綴比對純字串；approver 原樣送；freeze 省略 docs 由綁定檔換算；RTM 404 一律 `rtm_not_found`；OpenAPI 的 advisory 以 boolean＋說明；逾時只驗請求值；RTM 列測試類名以實際為準） | 〔未驗〕MiniBridge 與真 Bridge 逐值對照（交 W4／W5）；流程備註：Dev-Backend 誤派一次 noop 子代理（4 秒內回、零副作用，如實記） |
| W4 dogfood（操作員兼 SA／QA／掌舵者代理） | `10b10a8a`（證據檔 §1＋Bridge 失敗路徑夾具） | 夾具 `2 passed`（11.4 秒）；ruff rc=0；`check_pytest_baseline_sites` rc=0；`check_handoff_carriers` rc=0；`git diff --check` rc=0；雲端對 `5593e178` 五支 workflow 全 success（主控 `gh run list` 現查） | TCS 多一條 AC-001-5（三個過渡態→TRANSIENT，否則契約 §3.1.5 的 43 個鍵有 3 個無歸屬）；SCG-4 審查者＝TCS 作者＝操作員（被審程式由另一行程 haiku 所寫），W5 為第二眼 | C1～C6 皆成立、各附但書（§1.8）；DEF-AC-015～027（P3 五、P4 八、無 P≤2）；〔未驗〕macOS／Linux／Docker 全棧、真 AI 的 Integration／E2E 類 AT、PR_REVIEW 以後各態、取消／回收／外來委派在 Console 實跑；`phase` 全程 null 直到 T-G 搬入（D-115-08 後半由 Dev-Bridge 續做） |
| Dev-Frontend | `642ce477`（54 檔） | `npm run lint` rc=0；`npx tsc --noEmit` rc=0；`npx vitest run` `Test Files 68 passed`、`Tests 1122 passed`；`npm run build` rc=0（`NEXT_PUBLIC_API_URL=http://localhost:18080`）；四區塊掃描 0 命中；`git diff --check` rc=0；未觸碰任何真後端 spec | 恢復指令為上下兩段各有複製鈕（非契約字面的分頁）；核准凍結對話框多一個選填階段名（留白不送）；恢復指令不做前端後備；對話框以共用 `dialog.tsx` 自組而非 ConfirmDialog；新視覺元件（階段進度條、可收合治理卡、複製鈕）只用既有 token——待 QA 於 ADR-002 §4 登記 | 只以 route mock 驗（mock spec p10 18 支、既有 mock 74 支＝他包回報）；RTM 列 UI-SDD-01～03 與 API-IMP-12 前端半待 QA 單線合併；FE 自修一缺陷（RTM 查詢鍵脫離 executions 家族，終態開頁請求 2→1 次） | 接受：TCS 模板 §4 E 類改寫為「文件內編號、不可編譯；要執行請命名 `AT-{NNN}-{Y}-E-{n}` 並列入 §1」（比任務書字面準確）；S-08 擴到兩份場景增強文件；README／FILE_DIRECTORY_RULES 去版號範圍放大（原文收 EVOLUTION_LOG）；ADR §6.3① 的「已綁定 `sdd_spec_file` 須在 `docs[]`」由 Backend 擋（400）而非 Bridge（ADR 附錄待補註）；`/sdd-gate --retry-reset` 無對應 FSM 動詞只註明不補（P4） | 同族殘留（EVOLUTION_LOG〈同族殘留〉）：`tools/AISDLC_CLAUDE_RULES.md`、`guides/system/sdd/SDD_Core_Principles.md` 與三份測試模板內部仍把 SCG-4 當測試計畫閘、Greenfield Stage 樹 SCG-1／SCG-5 標註、INIT〈最新驗收〉過期、UPGRADE_SOP／CHECKLIST「Agent YAML 更新 version」與 `agent_scg_anchor_lint` 判準 4 互斥；他包回報：十支 lint rc=0、ci-gate rc=0（v0.01 1478／v0.30 2140／scripts 383，含 RT 當時工作樹）、二十九個凍結版 diff 皆零 |
