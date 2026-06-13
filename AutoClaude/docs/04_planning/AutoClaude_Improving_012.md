# AutoClaude_Improving_012 — Agentic AI 三大能力差距分析與納入執行計畫
# Gap Analysis & Implementation Plan: Agentic Capability Uplift

**專案**: AutoClaude（AISDCL_Agent monorepo 執行引擎）
**功能/模組**: Agentic 三大能力（任務拆解+工具使用 / 觀察→調整閉環 / 長期記憶）
**版本**: v1.0
**建立日期**: 2026-06-12
**建立者**: sa-analyst（依 AISDLC_SDD_v0.01 `gap_analysis_framework`，模板來源 `AISDLC_SDD/AISDLC_SDD_v0.01/docs_template/sdd/planning/GAP-ANALYSIS-TEMPLATE.md`）
**適用情境**: Brownfield

---

## 執行摘要

| 項目 | 說明 |
|------|------|
| 分析目標 | 評估 AutoClaude 是否具備 Agentic AI 三大能力（A 任務拆解+工具自主使用、B 觀察結果持續調整、C 長期記憶），並將缺口納入執行計畫 |
| As-Is 來源 | `AutoClaude/CLAUDE.md` Architecture Snapshot + 原始碼實證盤點（見 §1 證據欄） |
| To-Be 需求來源 | 使用者需求（2026-06-12）：Agentic AI 能力定義三條 |
| 整體變更複雜度 | 高（涉及 core/ports 擴充 + 新 plugin + DAL schema） |
| 預估 Story Points | 47 SP（見 §5） |

### 能力總判定

| 能力 | 判定 | 現況證據（As-Is） | 缺口 |
|------|------|------------------|------|
| **A. 任務拆解 + 工具自主使用** | 🟡 部分滿足 | Playbook YAML 靜態拆解（`autoclaude/models/playbook.py`）；PtyExecutor 驅動 Claude Code CLI（`autoclaude/infra/adapters/pty_executor.py`）；ESCALATION 後 PlaybookEvolver 可 INJECT_STEP/SPLIT_STEP（`autoclaude/evolution/playbook_evolver.py`） | 無「初始輸入高階目標→輸出完整步驟 DAG」的一次性自主拆解機制；已有事後補完（GOAL_SYNTHESIS 於 POST_RUN 注入補完步驟，見 `autoclaude/plugins/goal_synthesis_plugin.py`）與失敗演化（INJECT_STEP/SPLIT_STEP），但均為響應式。AutoClaude 本體無工具 Port；惟 PtyExecutor 委派之 Claude Code CLI 內建 WebSearch/WebFetch 等工具能力，F-A2 係在 AutoClaude 層新增統一抽象與 allowlist 治理 |
| **B. 觀察結果並持續調整** | 🟢 大致滿足 | KernelPhase 34 phase 事件閉環（`autoclaude/core/hookspec.py` 定義、`autoclaude/core/kernel.py` 發布核心子集；2026-06-12 實測 `len(list(KernelPhase))`=34）；ConvergenceMonitor 8 信號（`autoclaude/execution/convergence_monitor.py`）；EVALUATE→CORRECTION→ESCALATION→自演化→AutoResume 多層閉環 | 已有 git diff 應用驗證與 correction prompt 品質驗證（`_correction_helpers.py`）；缺 error_signature 改善比對、無改善連續 N 次提前升級、KB strategy 失效回寫 |
| **C. 保留記憶** | 🟡 部分滿足 | Checkpoint 全欄位原子持久化（schema 定義於 `autoclaude/utils/checkpoint_manager.py`〔Phase 5 起 deprecated alias〕；原子寫入 tmp+replace 實作於 `autoclaude/infra/repositories/file_state_repository.py`，Phase 1/2 持久化邏輯應加於後者）；FailureKnowledgeBase JSONL（`autoclaude/utils/knowledge_base.py`）；DAL 三後端 + pgvector（`autoclaude/infra/repositories/`、`autoclaude/infra/adapters/pg_vector_search.py`） | 無使用者偏好記憶；無跨 playbook 專案進度彙總；KB metrics 僅記憶體、重啟清零 |

> 姊妹專案 AISDLC_SDD 在「規格層」已具 INTENT_DECOMPOSITION（R-9.23 意圖分解 DAG）、FSM/ESCALATION 閉環與 FSM-STATE/Context-Snapshot/Decision-Trace 三層記憶；本計畫聚焦 AutoClaude「執行層」缺口，設計上對齊 R-9.23 / Rule 8 的有界性與人工 signoff 精神，不重複造規格層的輪子。

---

## 1. 功能差距（Functional Gap）

| 功能 | 狀態 | 描述 | 優先級 |
|------|------|------|--------|
| F-A1 GoalDecomposer（AI 自主任務拆解） | 🆕 新增 | 輸入高階 goal → Brain 產出步驟 DAG（含 evaluator 建議）→ 產生 Playbook 草稿 → 🔴 人工 signoff 後執行。硬上限步驟數（預設 ≤ 24），含環或超限即拒絕（對齊 AISDLC_SDD R-9.23 有界拆解精神） | P2 |
| F-A2 ToolInvocationPort（外部工具適配） | 🆕 新增 | 新增 core/ports 抽象：Web 搜尋、HTTP API 呼叫、訊息發送（延伸現有 notification）。adapter 落 `infra/adapters/`，需 allowlist 安全閘 | P1 |
| F-B1 AlertLadder（漸進式告警階梯） | 🔄 修改 | ConvergenceMonitor 信號觸發後不直接 ESCALATION，先經 WARNING（記錄）→ HINT（注入修正提示）→ ESCALATE 三階梯；各階計數持久化於 checkpoint | P1 |
| F-B2 Correction 效果事後驗證 | 🔄 修改 | mutation 套用後，比對下一 attempt 的 error signature／exit code 是否改善；無改善連續 N 次即提前升級，並回寫 KB strategy 失效標記 | P1 |
| F-C1 PreferenceStore（使用者偏好記憶） | 🆕 新增 | 持久化使用者層偏好：偏好修正策略（如 SPLIT_STEP > REVISE_EVALUATOR）、報告格式、常用資料來源；供 Brain decide_correction 時注入 | P1 |
| F-C2 GoalProgressLedger（跨 playbook 進度彙總） | 🆕 新增 | 以 goal_task_id 為鍵，彙總多個 playbook run 的完成 feature 清單與整體 goal 達成度，跨 session 查詢 | P2 |
| F-C3 KB Metrics 持久化 | 🔄 修改 | KnowledgeBaseMetrics（kb_hit_total 等 4 項）由純記憶體改為 JSONL append（File backend）/ PG 表（Pg backend），重啟不清零 | P0 |

**新增功能清單**（需要新 US）:
1. F-A1 → US-AGT-001（goal → 步驟 DAG → 人工 signoff）
2. F-A2 → US-AGT-002（工具 Port + allowlist 安全閘）
3. F-C1 → US-AGT-003（偏好記錄與注入）
4. F-C2 → US-AGT-004（跨 run 進度彙總查詢）

**修改功能清單**（需要更新現有 US／行為）:
1. F-B1 → 影響 escalation 路徑（`_escalation_handler.py`）
2. F-B2 → 影響 correction 迴圈（`_correction_helpers.py`）
3. F-C3 → 影響 `knowledge_base.py` metrics

**刪除功能清單**: 無。

---

## 2. 架構差距（Architectural Gap）

### 受影響模組清單

| 模組 | 影響類型 | 影響程度 | 說明 |
|------|---------|---------|------|
| `autoclaude/core/ports/` | 直接修改 | 高 | 新增 ToolInvocationPort、PreferenceStorePort（10 ports → 12 ports）；`.importlinter` 合約需同步檢視 |
| `autoclaude/infra/adapters/` | 直接修改 | 中 | 新 adapter（web/http/messaging、preference store）；遵守 adapter LOC ≤ 400 |
| `autoclaude/plugins/` | 直接修改 | 中 | 新 plugin（preference_memory、goal_progress）依新增 Plugin SOP：HookSpec 繼承 + wiring._REGISTER_ORDER + EventBus 協作、禁互 import；plugin_entry LOC ≤ 250 |
| `autoclaude/execution/convergence_monitor.py` + `steps_orchestrator/_escalation_handler.py` | 直接修改 | 中 | AlertLadder 三階梯邏輯。現況 LOC（2026-06-12 實測，`tools/check_loc_budget.py` count_loc 口徑：去空行與純註解）：convergence_monitor 117 行 / _escalation_handler 285 行（service tier ≤ 500），改動後不可超 tier；HINT 階若涉 Brain 呼叫一律走 EventBus，遵守 `.importlinter` Rule 4-5（Brain/Executor 不可互 import） |
| `autoclaude/execution/steps_orchestrator/_correction_helpers.py` | 直接修改 | 中 | mutation 效果事後驗證 |
| `autoclaude/utils/knowledge_base.py` | 直接修改 | 低 | metrics 持久化 |
| `autoclaude/utils/checkpoint_manager.py` | 間接影響 | 低 | AlertLadder 階梯計數欄位入 checkpoint（向下相容） |
| DAL（`infra/repositories/` + alembic） | 直接修改 | 中 | preference / goal_progress / kb_metrics 表（PG）+ File backend 對等 JSONL |

### 資料庫 Schema 變更範圍

| 表格/集合 | 變更類型 | 說明 |
|----------|---------|------|
| `user_preferences` | 新增表 | key/value + scope（global / per-playbook）+ updated_at；File backend 對等 `preferences.jsonl` |
| `goal_progress` | 新增表 | goal_task_id, playbook_id, completed_features(jsonb), progress_pct |
| `kb_metrics` | 新增表 | 4 項 metrics 快照 append-only；File backend 對等 `.kb_metrics.jsonl` |
| `checkpoints` | 新增欄位 | alert_ladder 計數（JSON 欄，向下相容缺省）。表名依 `_pg_models.py` 實證：PG 任務模型為 `playbook_runs` + `checkpoints` 二層 + 附加表（`knowledge_entries` / `playbook_versions` / `drift_log` / `config_audit_log`），無 `playbook_tasks` / `playbook_checkpoints` 表 |

### API 介面變更範圍

| API 端點 | 變更類型 | Breaking？ | 說明 |
|---------|---------|-----------|------|
| （無對外 HTTP API） | 內部 Port 契約新增 | NO | ToolInvocationPort / PreferenceStorePort 為新增抽象，既有 10 ports 不動 |

---

## 3. 技術差距（Technical Gap）

### 技術債影響評估（含本次 zero-trust nightly 稽核發現）

| TD ID | 技術債標題 | 對本次變更的影響 | 是否需先修復 | 狀態 |
|-------|-----------|----------------|------------|------|
| TD-N01 | nightly perf stage 缺「`perf_results.json` 確實產出」驗證（`tools/run_local_nightly.ps1` perf stage；CI `ci.yml` 有對應驗證、本機缺） | F-B 系列驗收依賴 nightly 可信度 | YES（本次 session 修復） | ✅ 2026-06-12 已修復（ps1 perf stage 缺檔即 rc=1 + ERROR log，對齊 ci.yml Verify step） |
| TD-N02 | `validate_mutmut_log.py` 對 mutmut 輸出格式無版本防衛（版本鎖散落於 `run_mutmut_in_docker.sh`） | 低；mutation 取證韌性 | YES（本次 session 修復） | ✅ 2026-06-12 已修復（.sh 版本守門後寫 `mutmut version OK: 2.4.3` 標記 + validate 新增 `--require-version-marker`（預設關閉）+ ps1 呼叫處開啟） |
| TD-N03 | observability stage 無獨立整合驗證路徑（僅單元測試） | 低 | YES（本次 session 修復或文件化豁免） | ✅ 2026-06-12 已修復（stage 5 後驗證 `.observability_history.jsonl` 末筆 UTC 日期=今日，否則 rc=1） |
| TD-N04 | `nightly_latest.log` 指標時序文件未明示（P2） | 無 | 文件補充 | 📝 2026-06-12 已文件化（Nightly_Forensic_Discipline.md 紀律 #11 TD-N04 補充） |
| TD-N05 | ADR-SD09-008 版本戳記一致性需查核（P2） | 無 | 文件查核 | ✅ 2026-06-12 已查核：`docs/04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md` 存在，狀態 ACCEPTED v0.4（2026-05-25）；`tools/run_local_nightly.ps1` 雙軌 env 區與 F2 ALERT 訊息引用「ADR-SD09-008 v0.4 ACCEPTED」與檔案版本戳記一致，無需修正 |
| TD-N06 | `.mutation_history.jsonl` 舊紀錄無 source_sha256 之向下相容語意未文件化（P2） | 無 | 文件補充 | 📝 2026-06-12 已文件化（Nightly_Forensic_Discipline.md 紀律 #12 TD-N06 補充：引入時點 + `MAX_BACKWARD_COMPAT_MISSING=2` 原因） |
| TD-C01 | KB metrics 記憶體易失（= F-C3，升級為功能項） | C 能力驗收前置 | YES（納入 Phase 1） | ⏳ 待 Phase 1（F-C3） |

> **TD-N01~N03 修復後端到端取證（2026-06-12，三方 zero-trust audit QA-P1-2 補跑）**：親跑 `tools/run_local_nightly.ps1` 全綠 — `logs/nightly_2026-06-12_233820.log`（run_id=233820 commit=fa2d562），6 stage 全 exit=0（summary `mutation=0 pg-e2e=0 perf=0 drift=0 obs=0`）。三錨點實證：TD-N01 `perf_results.json present（TD-N01 強制驗證通過）`（log:227）；TD-N02 `[run_mutmut_in_docker] mutmut version OK: 2.4.3`（log:125，`--require-version-marker` 路徑實際生效）；TD-N03 `observability 整合驗證通過：末筆 ts=2026-06-12T15:44:12+00:00（UTC date=2026-06-12 = today）`（log:243）。perf green=3（decide_correction 2395.5ms，+3.2%）、mutation Killed 114 / Survived 35。附註（紀律 #12 fail loud）：同日稍早 3 次經 agent PowerShell 工具載具跑 nightly，perf stage 均 BLOCK（decide_correction +24.9%~+31.3%，run_id=230549/231410/232253）；對照實驗（同源碼裸跑 pytest：Bash 載具 2239~2451ms PASS vs PowerShell 載具 2894ms）證實為該載具 CPU 量測膨脹，非源碼回歸 — 同時實證 TD-N01 加固後 perf stage 的 fail-loud 路徑真會擋（非橡皮圖章）。

### 需要先還技術債再實作的項目

1. TD-N01～N03（nightly 可信度）→ 先完成，再啟動任何依 nightly 驗收的 workstream。
2. TD-C01 → Phase 1 第一項（F-C3）。

---

## 4. 變更風險評估

| 風險項目 | 等級 | 說明 | 緩解措施 |
|---------|------|------|---------|
| 自主拆解失控（無限步驟／自我放大） | 高 | F-A1 讓 AI 生成步驟 | 硬上限 ≤ 24 步 + DAG 無環檢查 + 🔴 人工 signoff 後才執行（對齊 R-9.23 / Rule 8 棘輪）；超限直接拒絕不重試 |
| 外部工具安全風險（任意 URL／API 呼叫） | 高 | F-A2 開放對外 I/O | allowlist 設定檔 + 預設 deny + 審計 log；訊息發送僅延伸既有 notification 通道 |
| 回歸影響（escalation 路徑變更） | 中 | F-B1 改動既有閉環時序 | AlertLadder 以 feature flag 預設關閉上線；既有 escalation 測試全綠 + 新增階梯轉換測試（coverage ≥ 90%） |
| Schema 遷移風險 | 中 | 3 新表 + 1 欄位 | alembic 前向遷移 + File backend 對等實作；dual mode 影子驗證 |
| Token 成本上升 | 中 | F-A1/F-B2 增加 Brain 呼叫 | 每 run 拆解僅 1 次；效果驗證走本地 signature 比對（不呼叫 Brain，遵守「code 能答就 code 答」） |
| LOC / import-linter 違規 | 低 | 新增模組 | 依 LOC 分級政策設計拆檔；`lint-imports` 7 contracts 過綠為 PR 閘門 |

**整體風險等級**: 中

---

## 5. 建議實施計畫

### 實施順序（Priority Order）

> **排序原則**：Phase 以能力群組之風險遞增排序（C → B → A），F-* 優先級欄僅決定群內順序與資源分配；故 F-C2（P2）早於 F-A2（P1）執行並非矛盾。

1. **Phase 0 — P0 先決條件（本次 session 內完成）**
   - [x] 修復 TD-N01～N03（nightly 程式強化），TD-N04～N06（文件補充/查核）— ✅ 2026-06-12 完成（見 §3 技術債表「狀態」欄）
   - [x] 本計畫通過 Architect / SA·SD / QA zero-trust 審查（標準：P0 發現=0、P1 發現全數修復或文件化豁免）+ 🔴 人工確認 — ✅ 2026-06-12/13 三方並行 audit：初始 P0=0 / P1=6（含跨角色重複 1）/ P2=8；P1 全數修復＋複審期抓出修復自身引入之 P0=1（CLAUDE.md:4 行長 842cp 破 contract test）即修＋P2 全數修復（無文件化豁免）；2 輪 QA 複審 PASS。取證：nightly run_id=233820 六 stage 全綠（TD-N01/N02/N03 錨點 log:227/125/243）、full pytest 2,853 passed / 122 skipped、mirror tests/tools/ 421 passed、importlinter 7 kept、LOC violations=0、snapshot OK。🔴 人工確認：koalawu（2026-06-13）— **本文件即日凍結（SCG-0）**

2. **Phase 1 — 記憶基座（C 能力，最低風險先行）**
   - [x] F-C3 KB metrics 持久化（含 alembic migration + File 對等）— ✅ 2026-06-13：採 ADR-SD09-006 canonical（IKbMetricStore port + Local/Pg adapter + alembic 0016 + importlinter Rule 8，7→8 kept）
   - [x] F-C1 PreferenceStore（Port + adapter + plugin + Brain 注入點）— ✅ 2026-06-13：IPreferenceStore + File/Pg adapter + PreferenceMemoryPlugin + Kernel 補發 PRE_CORRECTION + `preferences_section` 注入鏈（SRD §2.3 實作修正註記）
   - [x] F-C2 GoalProgressLedger — ✅ 2026-06-13：GoalProgressLedger（File/Pg）+ GoalProgressPlugin（POST_RUN 補 payload）+ project fallback 鍵
   - 驗收：重啟後 metrics 不清零 ✅（test_knowledge_base_metric_store）；偏好可寫可讀並出現在 correction prompt ✅（test_kernel_pre_correction 端到端）；跨 ≥ 2 個 playbook run 的進度可彙總查詢 ✅（test_goal_progress_ledger）。閘門：SCG-1（SRD_AGT_Phase1_Memory.md）+ SCG-2（ADR-AGT-003）🔴 koalawu 2026-06-13；full pytest 2,931/122、importlinter 8 kept、LOC=0

3. **Phase 2 — 閉環強化（B 能力）**
   - [x] F-B1 AlertLadder（feature flag 預設 off → nightly 觀察 7 天 → 預設 on）— ✅ 2026-06-13：AlertLadder（WARNING→HINT→ESCALATE 三階梯，strategy tier）+ AlertLadderConfig（enabled 預設 off）+ checkpoint additive `alert_ladder` 欄（File + PG counters JSONB 子鍵，零 alembic）+ 五條存檔路徑接線（interrupt/token-halt/evolution×3/payload）
   - [x] F-B2 Correction 效果事後驗證 + KB 失效回寫 — ✅ 2026-06-13：CorrectionVerifier（signature/fail_count/exit_code 三分量純本地比對，不呼叫 Brain）+ no_improve_streak 提前升級（門檻可配置 1~5）+ `record_strategy_failure`（skip_strategies merge + 失效清 successful_strategy，常開 additive）
   - 驗收：階梯轉換有測試；同 error signature 無改善 N=2 次提前升級；既有 escalation 測試零回歸 — ✅ 全達成。閘門：SCG-1（SRD_AGT_Phase2_Closedloop）+ SCG-2（ADR-AGT-004 ACCEPTED）🔴 koalawu 2026-06-13。三方 zero-trust audit（P0=0 / P1×3 / P2×4 全修，含 evolution-resume 接線經 koalawu 🔴 拍板）+ QA 最終複審變異實證 4/4 PASS。full pytest **3,020 passed / 122 skipped**（前基線 2,972，+48 零回歸）、新模組 coverage 100%、importlinter 8 kept、LOC=0、snapshot OK

4. **Phase 3 — 自主拆解與工具（A 能力，風險最高最後）**
   - [x] F-A2 ToolInvocationPort + allowlist 閘（先行，因 F-A1 拆解出的步驟需要工具可用）— ✅ 2026-06-13：SCG-1（SRD_AGT_Phase3）+ SCG-2（ADR-AGT-001）🔴 koalawu；IToolInvocation port（ports 12→13）+ ToolInvocationAdapter（預設 deny + allowlist domain/子域比對 + 全程審計 + send_message 委派 notifier）+ ToolInvocationConfig（flag off）；tag v2026.06.13-05。full pytest 3,035/122（+15 零回歸）、新模組 coverage 100%、importlinter 8 kept、LOC=0
   - [x] F-A1 GoalDecomposer（產出 Playbook 草稿 + 🔴 人工 signoff 流程）— ✅ 2026-06-13：`IBrain.decide_decomposition` + `BrainCapabilities.supports_decomposition`（additive 預設 False，capability 守門不靜默降級）+ MinimaxBrain/MinimaxClient/prompt_builder 拆解鏈 + `execution/goal_decomposer.py`（GoalDecomposer：三道機械有界閘 ≤24 硬上限 `min()` 鉗制／DAG 無環 Kahn 拓撲排序／非空 prompt，超限拒絕不截斷不重試，每 run 僅 1 次 Brain 呼叫非遞迴）+ `DecompositionDraft` frozen + 🔴 signoff 硬閘（`release_for_execution` 未簽署拒絕釋出 + 審計人/日期/goal hash）+ `wiring.build_goal_decomposer` 注入 F-A2 `ToolInvocationAdapter`（消費 allowlist 安全閘，不再 dead code）。沿用既有 Playbook schema 產 YAML 草稿（往返載入驗證）。
   - 驗收：allowlist 外呼叫被拒並留審計 log ✅（test_tool_invocation）；拆解超限／含環被拒 ✅（test_too_many_steps_rejected_no_retry/test_cycle_rejected）；signoff 前不執行任何步驟 ✅（test_release_before_signoff_denied）；不支援 decomposition 的 brain 被拒 ✅（test_unsupported_brain_rejected，brain.calls==0）；Playbook 草稿可被既有 validator 載入 ✅（test_draft_roundtrip_loadable）。閘門：full pytest **3,056/122**（前基線 3,035，+21 零回歸）、新模組 coverage 100%、importlinter 8 kept、LOC=0（goal_decomposer 機械錨定 strategy ≤300）、新檔 ruff 零違規。三方 zero-trust audit（Architect·SD / QA·RTM）OVERALL PASS（P0=0 / P1=0），2 項 P2（LOC tier 錨定 + evaluator_command 往返）已修；QA 突變實證（signoff 閘與步驟數閘改 `if False:` → 對應測試 FAILED，證非套套邏輯）+ 收斂閉環未污染 + ADR-AGT-002 原設計無弱化。**Phase 3 完成，Improving_012 三能力（A/B/C）全數交付。**

### SCG 閘門對應（每 Phase 皆須過）

| 閘門 | 本計畫對應產出 | 人工點 |
|------|---------------|--------|
| SCG-0 | 本文件（PRD/FRD 級需求）凍結；凍結後需求範圍變更須重開 gap analysis 變更單並重走 SCG-0 | 🔴 |
| SCG-1 | 各 Phase SRD 增補 + Port 介面規格 | 🔴 |
| SCG-2 | ADR：ADR-AGT-001 工具安全閘、ADR-AGT-002 拆解有界性、ADR-AGT-003 記憶分層 | 🔴 |
| SCG-3 | Port 契約（介面簽名）凍結後才實作 adapter | 🔴 |
| SCG-4 | 每 PR：pytest 全綠 + lint-imports + LOC budget + coverage ≥ 90% | 🔴 |
| SCG-5 | RTM：US-AGT-001~004 → TC 100% 覆蓋 | 🔴 |
| SCG-6 | nightly 連續 7 天綠 + feature flag 轉正 | 🔴 |

### 預估 Story Points

| 類別 | SP |
|------|-----|
| 新增功能（F-A1 8、F-A2 8、F-C1 5、F-C2 5） | 26 |
| 修改功能（F-B1 5、F-B2 5、F-C3 3） | 13 |
| 技術債還債（TD-N01~N06） | 3 |
| 回歸測試 + RTM | 5 |
| **總計** | **47** |

---

## 🔴 Human 確認

> 本區為**初版計畫批准**（2026-06-12）；最終凍結（SCG-0）以 §5 Phase 0 第二項 checkbox（zero-trust 審查通過 + 🔴 人工確認）勾選為準。

**確認日期**: 2026-06-12
**確認者**: koalawu 確認
**確認內容**:
- [x] 變更範圍已充分理解
- [x] 優先級排序符合業務需求（C → B → A 的風險遞增順序）
- [x] 風險評估已接受（特別是 F-A1/F-A2 的有界性與安全閘設計）
- [x] 實施計畫已批准

---

**相關文件**:
- 模板來源: `AISDLC_SDD/AISDLC_SDD_v0.01/docs_template/sdd/planning/GAP-ANALYSIS-TEMPLATE.md`
- As-Is 架構: [AutoClaude/CLAUDE.md](../../CLAUDE.md)（Architecture Snapshot）
- Nightly 取證紀律: [Nightly_Forensic_Discipline.md](../06_quality/Nightly_Forensic_Discipline.md)
- 姊妹框架對照: `AISDLC_SDD/AISDLC_SDD_v0.01/governance/RULES_INDEX.md`（R-9.23 意圖分解、Rule 8 人工棘輪）
