# SD_Improving_05 — Phase 7 Sprint 執行計畫

| 項目 | 內容 |
|------|------|
| 文件版本 | **v2.0（W5 G5 通過 + 三方覆驗修復 + 四方審議 4/4 APPROVED）** |
| 建立日期 | 2026-05-15 |
| 最後更新 | 2026-05-16 |
| 前置文件 | [SD_Improving_04.md](SD_Improving_04.md) v1.7（W4 G5 ✅ 全綠 1,199 passed / 10 skipped） |
| 三方審查 | Architect / SA / SD（v0.1~v1.3 規劃審查 2026-05-15 + W0/W1/W2/W3/W4/W5 G0~G5 覆驗 2026-05-16 + W6 G6 覆驗 2026-05-17） |
| QA 審議 | v1.1 已補 Q-C1~Q-C5 + Q-M1/M3/M4；W0/W1/W2/W3/W4/W5 G0~G5 四方核准 2026-05-16；W6 G6 四方核准 2026-05-17（部分完成 + PM §1.3 例外簽核） |
| 文件狀態 | **APPROVED (PARTIAL) — W6 G6 部分通過（1,491 passed / 15 skipped / equivalence 52/52 / importlinter 3 kept / LOC 10725 violations=0）；§6.3 22 項拔除清單完成 1/22；其餘 21 項延後 SD_06 W0~W3，PM 例外簽核（詳見 docs/08_deployment/SD05_Migration_Guide.md §1.3）** |

---

## 0. 事實澄清表（Architect/SA/SD 共識指出使用者誤解）

| 使用者陳述 | 實況 | 證據 |
|-----------|------|------|
| `playbook_runner.py` **1,962 行** | **錯**。實際 282 行 thin facade（W3-T12 已達標） | `wc -l playbook_runner.py = 282` |
| 真實肥肉位置 | `_runner_internals.py` **1,766 行 mixin** + `_runner_compat.py` 238 行 deprecated | `wc -l = 1766, 238` |
| 三檔合計 | 2,286 行 | `wc -l = 2286 total` |
| Plugin 架構不合規 | **部分正確**：12 Plugin 全部 ≤ 250 LOC、`.importlinter` 3 kept / 0 broken；但 `_runner_internals.py` 1,766 行**仍未真正下沉至 Plugin**（仍以 mixin 形式繼承） | hookspec.py 17 phase 但僅 8 個入 PHASE_RESULT_CONTRACT |
| PG 三層任務模型 | **完全未存在**：`_pg_models.py` 僅 4 表（playbook_runs / checkpoints / knowledge_entries / playbook_versions） | grep 結果 |
| 向量檢索就位 | **部分正確**：alembic 0004_pgvector 已建（HNSW m=16, ef_construction=64），但 **embedding 寫入路徑為 0**、**1536 維寫死** | _pg_models.py:110 `Vector(1536)` |
| 設定檔完整 | **部分正確**：TokenGuardConfig 已有 7 項；但缺 per-step / per-workflow override、缺涵蓋率測試、缺可觀測性 metrics | config.py:59-89 |

---

## 1. 三方審查共識 — Critical 風險彙整

### 🔴 Critical-1：hookspec 不足以承載下沉（Architect C-1, C-2 / SD A-1, A-2 共識）

`hookspec.py` 目前 17 phase 但 `PHASE_RESULT_CONTRACT` 僅 8 個入表；`IHookResult` 僅 4 種；`MergedResult` 缺 `scheduled_resume_at` / `evolved_playbook_path` 等欄位。**不先擴張，T18-P2 第 1 天就會被 `HookContractViolation` fail-fast 卡死。**

**T18-P2 啟動前必補**：
- 新增 ≥ 5 個 IHookResult：`ScheduleResumeResult`、`CounterSnapshotResult`、`PersistenceResult`、`MutationApplyResult`、`GoalValidationResult`、`EscalationDumpedResult`
- 新增 ≥ 5 個 KernelPhase：`ON_PERSISTENCE_REQUEST`、`ON_ESCALATION_DUMP_REQUEST`、`ON_EVOLUTION_PROPOSE`、`ON_EVOLUTION_APPLY`、`ON_AUTO_RESUME_WAKE`、`PRE_COMPACT`、`POST_COMPACT`、`ON_PROMPT_PREPARED`
- 擴 `PHASE_RESULT_CONTRACT` 至少 7 條（補 ON_INTERRUPT / ON_EVOLUTION / ON_FAILURE / ON_SUCCESS / ON_STATE_TRANSITION / ON_CHECKPOINT_RESTORE / ON_CHECKPOINT_SAVE_REQUEST）
- 擴 `MergedResult` 加 `scheduled_resume_at` / `evolved_playbook_path` / `evolution_metadata` / `counter_diff`

### 🔴 Critical-2：`_apply_single_mutation_full`（300 行）下沉位置 Architect 與使用者不一致

**使用者規劃**：吸收進 EvolutionPlugin
**Architect C-3 反對**：屬 Brain correction 領域，與 EvolutionPlugin 處理 ESCALATION 後 PlaybookEvolutionProposal 是不同領域；強塞會違反 SRP 並造成 god-plugin（300 行立即超 250 LOC budget）

**正確下沉**（Architect 建議）：
- (a) Mutation 套用 → `MutationApplyService.apply()`（已實作 4 種，補 DELETE/SKIP_TO/CONDITIONAL）
- (b) counter 維護 → `GotoCounterPlugin`
- (c) `early_return` 路徑 → Kernel `_apply_mutation` 加 GOTO/SKIP 分支

### 🔴 Critical-3：counter SSOT 必須先遷移再下沉 checkpoint（SD D-2）

`_run_steps` 內仍有純本地 `_goto_counter: dict` 等 5 個本地變數。下沉至 Plugin 後，CheckpointPlugin 透過 `ON_CHECKPOINT_SAVE_REQUEST` emit 收 GotoCounterPlugin 的 snapshot，但 GotoCounter 內部狀態必須與 Kernel 主迴圈本地變數同步。

**T18-P2 順序強制**：
1. **W1 Step 1**：把 5 個 local counter 完全遷出至 GotoCounterPlugin（讓 Plugin 變成 SSOT）
2. **W1 Step 2**：再動 CheckpointPlugin 的 save 邏輯
3. 否則任一順序錯誤會打破 Gap-042 / Gap-048 跨 session 防護

### 🔴 Critical-4：使用者規劃的 4 個吸收方**遺漏 4 類重要方法**（Architect M-3）

`_runner_internals.py` 有以下方法**未在使用者規劃中**：
- `_validate_global_goal_achievement` / `_build_achievement_summary` → 屬 `GoalSynthesisPlugin`
- `_fast_path_test_file_check` → 應建 **新 `FastPathPlugin`**
- `_persist_mutated_playbook` + `.mutated.yaml` 載入清理 → 應建 **新 `PlaybookPersistencePlugin`**
- `_verify_correction_applied`(git diff 部分) → 屬 `CrossStepValidatorPlugin`

### 🔴 Critical-5：PG 三層任務模型完全未列為 sprint task（Architect C-5 / SA AC-GAP-5 / SD B-1）

對應使用者特別關注 #3（Project / GoalTask / ExecutionItem Prompt），但 SD_05 v0.1 預定範圍**完全沒對應 task**。最低骨架需求：
- 新增 3 表：`projects`、`goal_tasks`、`execution_items`（含 embedding vector 欄位 + HNSW index）
- 新增 alembic `0007_three_tier_tasks.sql`、`0008_link_runs_to_goal_tasks.sql`、`0011_yaml_to_three_tier.py`（一次性匯入）
- 新增 Pydantic models + Repository ports + IVectorSearch port
- 與既有 `playbook_runs` / `checkpoints` / `knowledge_entries` / `playbook_versions` 的 FK 關聯
- 既有 60+ YAML 範本必須能匯入（否則無法切 `db_only`）

### 🔴 Critical-6：pgvector 寫入路徑為 0 + 1536 寫死 + 無 IEmbedder port（Architect M-5 / SD C-1）

alembic 0004 已建 HNSW index 但**永遠是 NULL**（無寫入路徑、無 embedding 寫入測試）。1536 與 Minimax embedding（1024 / 768）不相容。

**必補**：
- `IEmbedder` port + `IVectorSearch` port
- `EmbeddingConfig(model: str, dimensions: int)` 配置
- 至少 1 個 adapter（Minimax 或 sentence-transformers，OpenAI 為 stretch）
- per-table HNSW 調參（goal_tasks 低基數可用 m=8, ef_construction=32 節省記憶體）
- alembic 0007 `ALTER COLUMN` migration 路徑（維度可變）
- HNSW 重建 cron（每月 `REINDEX INDEX CONCURRENTLY`）

### 🔴 Critical-7：多 run checkpoint 衝突 / dual_state drift 偵測過弱（SD D-1, D-3）

- `_resolve_start` 仍用 `playbook_id` 查 checkpoint → 多 run 並存時拿錯 checkpoint
- `dual_state_repository.fail_loud` 僅比對 `step_idx` → counters / failure_history / step_evolution_counter 不一致全部漏抓

**必修**：
- `load_checkpoint` 接 `run_id` 過濾
- drift 偵測改為 `dataclasses.asdict()` 全欄比對 + diff 報告

### 🔴 Critical-8：FailureKnowledgeBase PG backend 缺 UNIQUE + TTL/partition（SD B-3, B-4）

- `idx_kb_signature` 未加 UNIQUE → 跨 session 重複塞滿
- 無 TTL / partition → 6 個月後數百萬列、HNSW 重建 cost 失控

**必修**：
- 增 `UNIQUE(error_class, error_signature)` + UPSERT
- 補 `recorded_at < now() - interval '90 days'` 自動 archive 或 `PARTITION BY RANGE (recorded_at)` 月分割

---

## 2. 三方審查 Major 風險彙整

| ID | 來源 | 摘要 | 處理方向 |
|----|------|------|---------|
| **M-1** | Architect M-1 | CheckpointPlugin `goto_counter_plugin=None` deprecated 參數 + `_goto_counter` 屬性未拔除 | T18-P2 W1 內拔除 |
| **M-2** | Architect M-2 / SD A-3 | TokenGuardPlugin `_compact_failure_count` vs Runner `_consecutive_compact_failures` 雙寫；`record_compact_failure()` API 從未被呼叫 | T18-P2 內必拔除 inline 路徑 |
| **M-3** | Architect m-2 / SD A-4 | `wiring.py` 兩條組裝路徑（wire_plugins_with_registry vs build_kernel）SSOT 漂移 | W1 第一個 PR：抽 `_build_plugin_set()` + `_register_in_order()` |
| **M-4** | Architect M-4 | `payload[snapshot_out] = mutable_dict` 替代 IHookResult 是 anti-pattern | 改為 `CounterSnapshotResult` IHookResult |
| **M-5** | Architect M-6 | `use_kernel_path: bool` 雙路徑已 deprecated 但**仍未刪除** | SD_05 收尾必刪 |
| **M-6** | SD A-3 | `MergedResult` 缺 `evolved_playbook_path`、`evolution_metadata`、`counter_diff`、`kb_record_request` 欄位 | 與 Critical-1 合併 |
| **M-7** | SD E-1 | TokenGuardConfig 缺 per-step / per-workflow override（W1 setup 應拉高、W3 codegen 應拉低） | `PlaybookTask` 加 `token_guard: Optional[TokenGuardConfig]` 欄位 |
| **M-8** | SD E-2 | 7 個 context regex **無真實樣本涵蓋率測試** | 補 `tests/fixtures/claude_output_samples/*.txt`（≥ 30 樣本）+ ≥ 95% 涵蓋率 gate |
| **M-9** | SD E-3 | AutoResumeService 無 metrics → 連續 10 次失敗只看 log | 新增 `ON_AUTO_RESUME_WAKE` event + `AutoResumeMetrics` |
| **M-10** | SA AC-GAP-1~8 | 三層 schema、向量、狀態機、設定檔**完全沒寫 AC**（願景而非規格） | W0 補規格化 sprint，每項 ≥ 1 條 measurable AC |
| **M-11** | SA F-3 | YAML → DB 匯入工具未列為獨立 task（5 PD） | 新增獨立 task `T19-IMPORT` |

---

## 3. Sprint 範圍重劃（拆 SD_05 + SD_06）

三方一致建議**拆 sprint**。本文件採以下拆分：

### SD_05（本 sprint）— Mixin 真正下沉至 Plugin（35~42 PD）

**目標**：T18-P2 完整下沉 + hookspec 擴張 + 測試重寫；不含 PG 三層任務模型與向量擴展。

| Wave | 範圍 | PD |
|------|------|----|
| **W0** | **規格化 + Builder 重構 + QA 基礎建設**：補齊 A~F 全部 AC、抽 `_build_plugin_set()` 解 wiring.py SSOT 漂移、契約擴張 mini-PR（Critical-1 6 個 IHookResult + 8 個 KernelPhase + PHASE_RESULT_CONTRACT 補 7 條）；**QA：量測全測 baseline 時間 + 補 PG 4 表 schema lock test + EventBus 加 trace_id + 提供 `tests/plugins/_template.py` fixture 模板 + 子模組命名設計（token_guard/{watcher,compactor,thresholds,git_verifier}.py 各 ≤ 80 行）** | 10 |
| **W1** | **counter SSOT 遷移**（Critical-3 強制順序步驟 1）：5 個 local counter 完全搬至 GotoCounterPlugin；CheckpointPlugin 透過 `ON_CHECKPOINT_SAVE_REQUEST` 取 snapshot；**QA：補 `tests/contract/test_phase_migration_flag.py`（16 case）；coverage ≥ 80%** | 6 |
| **W2** | **TokenGuardPlugin 擴**：吸收 `_execute_prompt`(token watch) / `_should_compact_now` / `_send_compact` / `_get_dynamic_compact_threshold` / `_verify_correction_applied`(git diff)；拆 package（≤ 250 LOC per file）；補 per-step override（M-7）；**QA：補 `tests/contract/test_playbook_yaml_backward_compat.py`（60+ YAML + 優先序 AC）；mutation test ≥ 75% kill rate（GotoCounter / Checkpoint / TokenGuard 三 SSOT）；coverage ≥ 82%** | 7 |
| **W3** | **CheckpointPlugin 擴 + EvolutionPlugin 擴**：吸收 `_save_evolution_resume_checkpoint` / `_handle_token_halt` / `_save_interrupt_checkpoint` / `_save_escalation_dump`；新增 `ON_PERSISTENCE_REQUEST` phase；拆 package；**QA：補 `tests/equivalence/test_counter_persistence_three_paths.py`（3 路徑 × 4 case = 12 case，≥ 3 case 為「中斷時序污染」）；coverage ≥ 83%** | 7 |
| **W4** | **MutationApplyService 擴 + 新 Plugin**：補 DELETE/SKIP_TO/CONDITIONAL strategy；新增 `FastPathPlugin` + `PlaybookPersistencePlugin`（套用 `tests/plugins/_template.py`）；GoalSynthesisPlugin 吸收 `_validate_global_goal_achievement` 等；**QA：兩個新 Plugin coverage ≥ 90%** | 5 |
| **W5** | **測試重寫**（180+ patch 點）：分三批依 dependency tree（批1=plugins、批2=core+infra、批3=integration+equivalence）每批 ≤ 30 檔；批次間插入「全測綠」commit；equivalence snapshot 13 fixture 必須全綠；補 7 個 context regex 涵蓋率測試（M-8） + AutoResumeMetrics（M-9） + `tests/core/test_event_bus_metrics.py`（QA Q-M1）；**coverage ≥ 85%** | 10 |
| **W6** | **收尾 + Migration Guide**：刪 `_runner_compat.py` + `_runner_internals.py`；刪 `use_kernel_path=False` 路徑；移除 CheckpointPlugin `goto_counter_plugin=None` deprecated 參數；**補 Migration Guide（舊 config 升級指引 + warning）**；G6 三方/四方審查（QA 簽核硬指標：equivalence 13/13 + mutation kill ≥ 75% + coverage ≥ 85%） | 3 |

**Gates**：
- **G0**（W0 末）：契約擴張 + Builder 重構 + 全部 Critical AC 寫入 → SA / Architect 兩方 ✅
- **G1**（W1 末）：counter SSOT 遷移完成；1,199+ tests 不下降；equivalence snapshot 13/13 綠
- **G2**（W2 末）：TokenGuardPlugin 拆 package + per-step override；雙寫風險解除
- **G3**（W3 末）：CheckpointPlugin / EvolutionPlugin 擴；3 條中斷路徑 counter 持久化驗證
- **G4**（W4 末）：MutationApplyService 7 種 strategy 完備；新 2 Plugin 上線
- **G5**（W5 末）：測試重寫完成；7 regex 涵蓋率 ≥ 95%；AutoResumeMetrics 上線
- **G6**（W6 末）：`_runner_internals.py` / `_runner_compat.py` 刪除；`use_kernel_path` 開關刪除；三方/四方審查 ✅

### SD_06（後續 sprint）— PG 三層任務模型 + 向量寫入路徑 + UI 前置（25~30 PD）

依賴：SD_05 G6 通過、PM 拍板嵌入 model（Minimax / sentence-transformers / OpenAI）+ UI 技術棧

| Wave | 範圍 | PD |
|------|------|----|
| **W1** | PG 三層 schema：alembic 0007（projects / goal_tasks / execution_items + HNSW per-table 調參） + 0008（playbook_runs / checkpoints 加 nullable FK） | 5 |
| **W2** | Pydantic models + Repository ports（`IProjectRepo` / `IGoalTaskRepo` / `IExecutionItemRepo` / `IVectorSearch`） + 三後端實作 | 6 |
| **W3** | `IEmbedder` port + Minimax adapter + 寫入路徑 + 寫入測試 | 5 |
| **W4** | YAML → DB 匯入工具（0011 migration / Click CLI） + 60+ YAML 範本回歸測試 | 5 |
| **W5** | KB UNIQUE + TTL/partition + HNSW 重建 cron | 3 |
| **W6** | 三後端 contract test 全綠 + storage.mode 三模式驗證 | 3 |

### SD_07（再後續）— UI 管理層（待 PM 規劃）

依賴：SD_06 G6 通過、UI 技術棧拍板（Web/Electron/TUI）、認證模式拍板（單 user / 多 user RBAC）、12 條 user story（SA C 段）審核

---

## 4. PD 估算修正表

| 子任務 | 使用者 v0.1 | 三方共識 v1.0 | 落差原因 |
|--------|-------------|--------------|---------|
| T18-P2 1,766 行下沉 | 16 PD | **30 PD** | hookspec 擴張 +5 / counter SSOT 遷移 +4 / 4 類遺漏方法 +5 |
| T16-P2 刪檔 | 1 PD | 1 PD | 同意 |
| 16 測試檔 180+ patch 點重寫 | 5 PD | **9 PD** | 動態 patch 路徑語意翻新 + equivalence 13 fixture |
| Plugin 介面重新設計 | 3 PD | 5 PD | ≥ 5 IHookResult + ≥ 5 phase + MergedResult 擴欄 + DefaultResolutionPolicy 改寫 |
| **PG 三層 schema（使用者未列）** | 0 PD | **8 PD（移 SD_06）** | 0007/0008 alembic + ORM models + IVectorSearch port |
| **向量寫入路徑（使用者未列）** | 0 PD | **5 PD（移 SD_06）** | IEmbedder port + 至少 1 adapter + 寫入測試 |
| **YAML → DB 匯入（使用者未列）** | 0 PD | **5 PD（移 SD_06）** | 60+ 既有 YAML 必須可匯入 |
| KB UNIQUE + TTL/partition | 0 PD | **3 PD（移 SD_06）** | 生產數據集無限增長 |
| Per-step token override | 0 PD | **2 PD** | 現有 TokenGuardConfig 僅全域 |
| AutoResumeMetrics | 0 PD | **2 PD** | 連續失敗無 alert |
| context regex 涵蓋率測試 | 0 PD | **2 PD** | 7 regex 無真實樣本 |
| dual_state drift 補強 | 0 PD | **2 PD** | 僅比對 step_idx |
| **總計** | 25 PD | **SD_05: 42 PD / SD_06: 28 PD** | 使用者版本嚴重低估 2.4~2.7 倍 |

---

## 5. 架構紅線（三方共識，**絕對不可採用**）

1. ❌ Plugin 之間 import（`.importlinter` 必須維持 3 kept / 0 broken）
2. ❌ Plugin 直接 import infra 層（必須走 port + 建構式注入）
3. ❌ 用 `payload[mutable_container] = result` 替代 IHookResult（M-4）
4. ❌ 為了通過 LOC budget 250 而把單一 Plugin 拆成 mixin（重蹈 W3-T12 覆轍）；超 250 必須拆 package
5. ❌ `KernelResult` 與 `PlaybookResult` 並存超過 SD_05；G6 必須統一為 `KernelResult` 單一入口
6. ❌ 在 SD_05 同時做「mixin 下沉」+「PG 三層任務模型」+「向量寫入」三件大事（必拆 sprint）
7. ❌ T18-P2 批次搬移後一次跑測（必須逐 phase 切換 + 每 sub-task 單獨 commit + 全測綠 gate）
8. ❌ counter SSOT 未遷移就動 CheckpointPlugin save（強制順序步驟 1 → 2）

---

## 6. Plugin 拆分藍圖（1,766 行 → 哪幾個 Plugin）

| 目標 Plugin / Service | 吸收 mixin 方法 | 預估 LOC | 是否需拆 package | 新 KernelPhase |
|------|------|------|------|------|
| `TokenGuardPlugin` | `_execute_prompt`(token watch) / `_should_compact_now` / `_send_compact` / `_get_dynamic_compact_threshold` / `_verify_correction_applied`(git diff) | +180 → 308 | **是**（拆 token_guard/ package） | `PRE_COMPACT` / `POST_COMPACT` |
| `CheckpointPlugin` | `_save_evolution_resume_checkpoint` / `_handle_token_halt`(checkpoint) / `_save_interrupt_checkpoint` / `_save_escalation_dump` | +120 → 366 | **是** | `ON_PERSISTENCE_REQUEST` |
| `MutationApplyService`（非 Plugin） | `_apply_single_mutation_full` 全部 7 種（含 counter increment 委派至 GotoCounterPlugin） | +280 → ~330 | **是**（拆 7 strategy 各 ≤ 60 行） | — |
| `GoalSynthesisPlugin` | `_validate_global_goal_achievement` / `_build_achievement_summary` / `_prepend_global_goal` / `_prepend_global_goal_brief` | +100 → 227 | 否 | — |
| `EvolutionPlugin` | `_save_escalation_dump`(escalation 觸發部分) + ESCALATION 後 evolution 路由 | +90 → 262 | 剛好超 | `ON_EVOLUTION_PROPOSE` / `ON_EVOLUTION_APPLY` / `ON_ESCALATION_DUMP_REQUEST` |
| **新 `PlaybookPersistencePlugin`** | `_persist_mutated_playbook` / `.mutated.yaml` 載入清理 | ~120 | 否 | 訂閱 `ON_EVOLUTION_APPLY` |
| **新 `FastPathPlugin`** | `_fast_path_test_file_check` | ~50 | 否 | 訂閱 `PRE_ATTEMPT`，回 `PromptInjectionResult` |
| `CrossStepValidatorPlugin` | `_verify_correction_applied`(git diff 另一塊) | +30 → 122 | 否 | — |
| `AutoResumeService` | `_resolve_start` 統一收歸 / `_wait_for_scheduled_resume` / `_load_playbook` / `_detect_workflow` + `AutoResumeMetrics` | +80 → 288 | 可接受 | `ON_AUTO_RESUME_WAKE` |
| `PlaybookKernel._run_step` | `_run_steps` 主迴圈控制流（while + GOTO/SKIP/INJECT_BEFORE/INJECT_AFTER 分派） | +60 → 309 | 拆 helper | — |

### 6.1 CounterSnapshotResult namespace 規範（W1 三方審查 SD-M1）

`MergedResult.counter_diff` 為跨 Plugin 共享的計數器合併視圖；多 Plugin 同 key 不同值
時 `DefaultResolutionPolicy.merge()` 將 raise `HookContractViolation`（避免 silent data loss）。

**W1 已用 key**（由 GotoCounterPlugin emit）：
- `goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter`

**W2 預留命名空間**（TokenGuardPlugin emit `_consecutive_compact_failures`）：
- 推薦：`compact_failure_count`（純 int，非 dict-of-step_id；TokenGuardPlugin 自治 SSOT）
- 若未來新 Plugin 也需 emit 計數器，請以 plugin 名稱作前綴防撞名：
  `<plugin_name>:<counter_name>`，例：`token_guard:compact_failure_count`、
  `evolution:proposal_count`

**禁止行為**：W2+ 新 Plugin 不可重用既有 4 個 key（goto/inject_before/skip_to/step_evolution）；
若需引用必透過 GotoCounterPlugin API（`increment_*` / `snapshot()`），不可旁路寫入。

### 6.2 第 5 個 counter（_consecutive_compact_failures）範圍說明

SD_05 §1 Critical-3 列出「5 個 local counter」，實際劃分：
- **W1 範圍（4 個 dict-of-step_id）**：goto / inject_before / skip_to / step_evolution → GotoCounterPlugin
- **W2 範圍（1 個 純 int）**：`_consecutive_compact_failures` → **TokenGuardPlugin**
  （SD_05 §2 M-2 雙寫拔除；型別為 `int` 而非 `dict[str, int]`；不參與 CounterSnapshotResult，
  改透過 TokenGuardPlugin 自治 snapshot 或新 IHookResult 型別）

**W2 已完成（v1.7 補註，三方審查 SA-M1）**：
- ✅ 雙寫拔除：`_runner_internals.py` grep `self\._consecutive_compact_failures\s*[+=]` = 0 writes
- ✅ Plugin SSOT：TokenGuardPlugin._compact_failure_count + 公開 property `compact_failure_count`
- ✅ Frozen Surface backward compat：PlaybookRunner._consecutive_compact_failures 為 property 委派
- **W6 拔除後遺**：plugin 目前**不**emit `CounterSnapshotResult`（不參與 counter_diff merge）；
  若未來 CheckpointPlugin 需在 checkpoint 中持久化 compact_failure_count，須補
  `TokenGuardPlugin._on_checkpoint_save_request` 訂閱（namespace key 建議 `compact_failure_count`，
  避免與 §6.1 W1 4 個 key 撞名）

### 6.3 W6 backward compat 拔除清單（W1+W2 三方審查補強）

W1+W2 為達成 SSOT 同時保 backward compat，留下下列過渡路徑，W6 必須全部拔除：

**W1 範圍（Counter SSOT）**：
1. `autoclaude/plugins/goto_counter_plugin.py::_on_checkpoint_save_request` — mutable container 寫入路徑（`counter_snapshot_out` / 舊鍵 `snapshot_out`）
2. `autoclaude/plugins/checkpoint_plugin.py::_build_checkpoint` — mutable container fallback + `self._goto_counter.snapshot()` 直接查詢路徑
3. `tests/plugins/test_goto_counter_plugin.py` / `test_checkpoint_goto_decoupling.py` — 對 mutable container 的相容測試

**W2 範圍（TokenGuard SSOT，三方審查補項）**：
4. `autoclaude/execution/playbook_runner.py::_consecutive_compact_failures` property + setter（Frozen Surface #8 backward compat）
5. `autoclaude/execution/_runner_internals.py::_get_dynamic_compact_threshold / _should_compact_now / _verify_correction_applied / _send_compact / _execute_prompt`（5 個 delegate wrapper；W6 連同 mixin 一同刪除）
6. `autoclaude/execution/_runner_internals.py::_execute_prompt` 主體（PTY + Hotkey 編排層 ~75 行；W6 評估搬至 ExecutorPort 或永久保留為 mixin/Kernel 編排）
7. `PlaybookTask.token_guard: Optional[dict]` — W3+ 評估改 `Optional[TokenGuardConfigOverride]` Pydantic 子模型（已加 field_validator typo 防呆，W6 才轉型）

**W3 範圍（CheckpointPlugin SSOT + EvolutionPlugin 觀察，三方審查補項）**：
8. `autoclaude/plugins/checkpoint_plugin.py` — backward compat re-export shim（W3-2 拆 package 後保留為相容路徑；W6 評估刪 + 加 DeprecationWarning 提示下游遷移至 `from autoclaude.plugins import CheckpointPlugin`）
9. `autoclaude/execution/_runner_internals.py::_save_evolution_resume_checkpoint / _save_interrupt_checkpoint / _save_escalation_dump / _handle_token_halt`（4 個 delegate wrapper，~110 行；W6 連同 mixin 一同刪除；對應 `_runner_internals.py` 4 處 docstring 已標 `TODO(SD_05 W6)`）
10. `autoclaude/plugins/checkpoint/plugin.py::_on_pre_run / _save_interrupt / _save_token_halt / _save_evolution / _build_checkpoint` private method alias（W3-2 拆 package 後保留為既有 30+ 測試 patch 路徑相容；邏輯下沉 `_phase_handlers.py`；W6 評估刪除）
11. `autoclaude/plugins/checkpoint/plugin.py::__init__::goto_counter_plugin=None` deprecated 參數（W4-T17 / M-11 遺留；W3 未拔除以保 backward compat；W6 必拔）
12. `autoclaude/plugins/evolution_plugin.py::on_event` 中 `ON_EVOLUTION_APPLY / ON_ESCALATION_DUMP_REQUEST` 兩 phase 的 NO-OP audit log（W3 過渡訂閱位；W6 完整下沉 MutationApplyService 結果回饋 + notify_escalation 移轉至 EvolutionPlugin）
13. `autoclaude/execution/_runner_internals.py::_save_escalation_dump` 內 `cfg_snapshot` SimpleNamespace 重構（Arch-M1 修補產物；W6 mixin 整體刪除時一併移除；屆時 notify 由 EvolutionPlugin 訂閱 ON_ESCALATION_DUMP_REQUEST 完成）
14. `tests/plugins/test_checkpoint_plugin.py::TestCheckpointPluginObserverContract::test_returns_none_when_no_persistence_triggered`（W3-2 拆 package 後更新；W6 mixin 完整下沉時測試簽名可進一步精簡）

**W4 範圍（MutationApplyService + 新 Plugin，三方審查補項）**：
15. `autoclaude/execution/_runner_internals.py::_prepend_global_goal` delegate wrapper（W4-4；W6 連同 mixin 一同刪除）
16. `autoclaude/execution/_runner_internals.py::_build_achievement_summary` delegate wrapper（W4-4；W6 連同 mixin 一同刪除；已改 module top-level import 至 GoalSynthesisPlugin）
17. `autoclaude/execution/_runner_internals.py::_validate_global_goal_achievement` delegate wrapper（W4-4；W6 連同 mixin 一同刪除；簽名已對齊 plugin Optional[str]）
18. `autoclaude/execution/playbook_runner.py::_prepend_global_goal_brief` delegate wrapper（W4-4；W6 連同 mixin 一同刪除）
19. `autoclaude/execution/_runner_internals.py::_fast_path_test_file_check` delegate wrapper（W4-2；W6 連同 mixin 一同刪除；屆時直接由 EventBus.dispatch(PRE_ATTEMPT) 取 PromptInjectionResult.prefix 注入）
20. `autoclaude/execution/_runner_internals.py::_persist_mutated_playbook` delegate wrapper（W4-3；W6 連同 mixin 一同刪除；屆時由 ON_EVOLUTION_APPLY phase payload 直接驅動 plugin 持久化）
21. `autoclaude/plugins/playbook_persistence_plugin.py::on_event` NO-OP audit log 過渡訂閱位（W4-3 對齊 PHASE_RESULT_CONTRACT ON_EVOLUTION_APPLY；W6 完整下沉 mixin 後改為真實持久化路徑）
22. `autoclaude/core/services/mutation/conditional.py::_set_service` 反向注入 anti-pattern（W4-1 / SA-M3；W6 改 constructor 必填參數，或 IMutationStrategy 加可選 set_service 抽象方法）

**新增 IHookResult**（共 6 個）：
- `ScheduleResumeResult(scheduled_at: str)`
- `CounterSnapshotResult(snapshot: dict)`
- `PersistenceResult(path: str, succeeded: bool)`
- `MutationApplyResult(clear_goal_summary: bool, ...)`
- `GoalValidationResult(achieved: bool, reasoning: str)`
- `EscalationDumpedResult(dump_path: str)`

---

## 7. 回滾與灰度策略（SD G-1, H 必修；QA Q-C1, Q-C2, Q-M3 已補）

1. **逐 phase 切換**：每搬移 1 個 phase 的方法群，跑全測 + equivalence snapshot 一次，作為一個獨立 commit；嚴禁批次搬移
2. **Feature flag**：`T18_P2_PHASES_MIGRATED: set[str]` 環境變數讓 fallback 能逐 phase 啟用
   - **(2a) 列舉 8 個合法 phase 名稱**：`{"PRE_COMPACT", "POST_COMPACT", "ON_PERSISTENCE_REQUEST", "ON_EVOLUTION_PROPOSE", "ON_EVOLUTION_APPLY", "ON_AUTO_RESUME_WAKE", "ON_PROMPT_PREPARED", "ON_ESCALATION_DUMP_REQUEST"}`
   - **(2b) Fallback 路徑保留期**：每搬移 1 phase，舊 mixin 方法須保留 ≥ 1 個 sub-task 週期（≥ 1 週）才可拔除
   - **(2c) Flag 拔除條件**：W6 G6 通過後 ≥ 3 個自然日無 production rollback 才可拔
   - **(2d) 兩條路徑 contract test**：`tests/contract/test_phase_migration_flag.py` 必須涵蓋 flag 啟用/停用 兩條路徑各 8 phase 共 16 case
3. **Equivalence snapshot 13 fixture**：每個 sub-task PR CI 強制綠 + `--ff-only` 規則
4. **舊測試遷移分三批**（依 dependency tree，QA Q-M3）：
   - 批 1 = `tests/plugins/`（最獨立）
   - 批 2 = `tests/core/` + `tests/infra/`
   - 批 3 = `tests/integration/` + `tests/equivalence/`
   - 每批末必須跑「全測 + equivalence + lint-imports」三 gate 全綠才進下一批
   - 每批 PR 必須附 patch 點對照表（舊 patch path → 新 patch path）QA 比對
5. **W0 量測全測時間**（QA Q-C2）：
   - 量測 baseline `pytest -n auto` 並行 vs 序列時間
   - 若 > 8 min 必導入 GitHub Actions matrix（依 7 sharding：core/plugins/infra/contract/equivalence/cli/integration）
   - equivalence 13 fixture 必須單獨 < 2 min（PR pre-merge gate）
6. **24h 自動回退觸發點**（QA Q-C2）：
   - ≥ 3 commits 連續紅 OR equivalence snapshot 任一 fixture 斷裂 → 自動 revert 至上一 G 點
   - 失敗 root cause 必須由 SA + QA 雙簽才可重啟該 wave

---

## 8. CI / Quality Gates（QA Q-C3, Q-M4 已補：分層 + 補 mutation / PG lock / regression diff）

### 8.1 PR-level（每 commit 跑，pre-merge）

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| `lint-imports` | 維持 3 kept / 0 broken | 🔴 全程阻塞 |
| `tools/check_loc_budget.py` | per-file ≤ 250 LOC（拆 package 後 per-module ≤ 250） | 🔴 全程阻塞 |
| `tools/check_frozen_surface_shim.py` | M1 shim 不破 | 🔴 全程阻塞 |
| `pytest tests/equivalence/` | 13/13 fixture 綠 + 單獨 < 2 min | 🔴 全程阻塞 |
| `pytest tests/plugins/` `tests/core/` | 變動 module 對應測試綠 | 🔴 全程阻塞 |

### 8.2 G-gate（每 wave 末跑，G0~G6）

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| `pytest tests/` | 全測 ≥ 1,199（隨 sprint 增長） | 🔴 阻塞 |
| `pytest tests/cli/` | CLI 相容性 | 🔴 阻塞 |
| `pytest tests/contract/` | 三後端契約測試 | 🔴 阻塞 |
| `pytest tests/contract/test_pg_existing_schema_lock.py` | **PG 既有 4 表 DDL snapshot + CRUD 行為快照鎖死**（W0 必補，QA Q-C3） | 🔴 阻塞 |
| `pytest tests/contract/test_phase_migration_flag.py` | flag 啟用/停用 兩路徑 × 8 phase = 16 case | 🔴 阻塞（W1+） |
| `pytest tests/contract/test_playbook_yaml_backward_compat.py` | 60+ 既有 YAML load + per-step token_guard 優先序 | 🔴 阻塞（W2+） |
| `pytest tests/equivalence/test_counter_persistence_three_paths.py` | 3 中斷路徑 × 4 case = 12 case | 🔴 阻塞（W3+） |
| `pytest tests/test_token_pattern_coverage.py` | 7 regex ≥ 95% 涵蓋率（≥ 30 樣本） | 🔴 阻塞（W5+） |
| **coverage 階段化**（QA Q-C3） | W1 ≥ 80% / W2 ≥ 82% / W3 ≥ 83% / W5 ≥ 85%；新 Plugin ≥ 90% | 🔴 階段阻塞 |
| **regression diff gate** | `tests/equivalence/snapshots/` diff report；任何 fixture diff 必須 SA + QA 雙簽 | 🔴 阻塞 |

### 8.3 Nightly（夜間自動跑，failure 隔日 alert）

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| **mutation test**（QA Q-C3） | `mutmut run` GotoCounterPlugin / CheckpointPlugin / TokenGuardPlugin 三個 SSOT plugin ≥ 75% kill rate | 🟠 nightly 阻塞（W2+） |
| `bench-test-runtime` | 全測時間趨勢；增幅 > 20% 必檢 | 🟠 警告 |
| `pytest tests/integration/` | 端對端整合（含 PG `both` 模式） | 🟠 nightly |
| **EventBus dispatch failure metrics** | `tests/core/test_event_bus_metrics.py` 連續 3 次相同 phase 失敗應 escalate（QA Q-M1） | 🔴 阻塞（W5+） |

---

## 9. 風險登記（更新 risk_log）

| 編號 | 描述 | 嚴重 | 對應 |
|------|------|------|------|
| **R-W0-1** | hookspec 擴張破壞既有 EventBus 契約 | 🔴 | Critical-1 |
| **R-W1-1** | counter SSOT 遷移順序錯誤打破 Gap-042 / Gap-048 | 🔴 | Critical-3 |
| **R-W2-1** | TokenGuardPlugin 雙寫拔除過程觸發 compact 連續失敗無限循環 | 🔴 | Major M-2 |
| **R-W3-1** | CheckpointPlugin 三條中斷路徑同步漏一條 | 🔴 | SD D-2 |
| **R-W4-1** | 新 Plugin（FastPath / PlaybookPersistence）order 錯誤 | 🟠 | Critical-4 |
| **R-W5-1** | 180+ patch 點測試重寫漏改造成 false green | 🔴 | SD H |
| **R-W6-1** | `_runner_internals.py` 刪除後仍有外部 import 殘留 | 🟠 | SD G |
| **R-SD06-1** | PG 三層 schema 與既有 4 表 FK 整合風險 | 🔴 | Critical-5 |
| **R-SD06-2** | 1536 維 vs Minimax 1024/768 維不相容 | 🔴 | Critical-6 |
| **R-SD06-3** | YAML → DB 匯入失敗 → `db_only` 模式無法上線 | 🔴 | M-11 |

---

## 10. PM/Stakeholder 拍板事項（SD_06 前置）

> **PM 拍板日期**：2026-05-16 ✅ 全部 5 項已決議

| # | 項目 | 拍板結論 | 影響 / 後續行動 |
|---|------|---------|----------------|
| **1** | 嵌入 model 選擇 | **C 方案：IEmbedder port + 雙 adapter**（2026-05-16 v1.3 修正） | SD_06 W3：`IEmbedder` port + **2 個 adapter**：(a) **預設 `BGEM3LocalAdapter`**（本地 TEI 容器，BGE-M3 1024 維，零費用、< 50ms、繁體中文最佳）；(b) `MinimaxEmbedderAdapter`（embo-01 API，備援，網路依賴）；切換靠 `.env` 的 `EMBEDDER_BACKEND=bge_m3_local\|minimax_api`；alembic 0007 vector 維度為 **1024**（配合 BGE-M3）；**Minimax embo-01 維度待 `tools/probe_minimax_embedding.py` 實測**（若非 1024 → 維度轉換層或 reduce-projection） |
| **2** | UI 技術棧 | **Web — Next.js 15+ (App Router) + TypeScript + Tailwind CSS + Shadcn UI** | SD_07（UI sprint）將以 Next.js App Router 設計；SD_06 須提供 RESTful API（建議 OpenAPI 規格）+ 認證 middleware；後端建議 FastAPI（與既有 Python stack 一致） |
| **3** | 認證模式 | **多 user RBAC（enterprise）** | SD_06 §B-1 schema 必補 `users` / `roles` / `permissions` 三表；`projects.owner_user_id` 變必填；`goal_tasks` / `execution_items` 增加 RBAC 欄位；建議引入 `casbin` 或 `oso` policy engine |
| **4** | 多 run 並存策略 | **多 run 並存**（同一 GoalTask 允許並發） | SD_06 必補：(a) `idx_ck_run_id` UNIQUE 維持（已就位）；(b) `_resolve_start` 改用 `run_id` 過濾 checkpoint（對應 SD Critical-7 / R-W3-1）；(c) UI 須顯示 active run 列表並支援 abort 個別 run |
| **5** | KB 數據保留期 | **365 天** | SD_06 W5：`knowledge_entries` 採 `PARTITION BY RANGE (recorded_at)` 月分割（12 個月 partition + auto-rotate）；HNSW per-partition 重建 cron；老資料 archive 至 cold storage（未列 SD_06 範圍，待後續 sprint） |

**G0 啟動條件**：✅ 已滿足（PM 5 項全部拍板）→ **可立即啟動 SD05-G0（W0，10 PD）**

### 10.1 SD_06 範圍調整（v1.3 因 PM C 方案）

| 項目 | 原 SD_06 | v1.3 調整 |
|------|----------|----------|
| W3 IEmbedder port + adapter | 5 PD（單 adapter） | **6 PD（雙 adapter：BGEM3LocalAdapter + MinimaxEmbedderAdapter）** |
| **新 W7 Docker 部署整合** | — | **2 PD**：擴充 `docker-compose.yml`（pgvector image + TEI embedder）+ `deployment/README.md` 部署指南 + Windows 工作排程器 PG backup 腳本 |
| 總 SD_06 PD | 28 PD | **31 PD** |

### 10.2 Docker 部署形態（v1.3 新增）

**目前混合模式**（SD_05/SD_06 期間）：
- AutoClaude 主程式：host process（保留 ESC+F12 全域熱鍵 + claude CLI + git host 整合）
- PostgreSQL：Docker `pgvector/pgvector:pg16`
- BGE-M3 Embedder：Docker `ghcr.io/huggingface/text-embeddings-inference:1.5`（GPU passthrough）

**未來全容器化**（SD_07 UI sprint 後）：UI 中斷按鈕（`IInterruptSource` port）取代 ESC+F12，AutoClaude 可全容器化。

詳見 [deployment/README.md](../../deployment/README.md)。

---

## 11. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v0.1 | 2026-05-15 | 使用者初版（25 PD） |
| v1.0-draft | 2026-05-15 | 三方審查共識重列：拆 SD_05（42 PD）+ SD_06（28 PD）；Critical 8 項；Major 11 項；新增 4 紅線、Plugin 拆分藍圖、回滾策略、Quality Gates |
| **v1.1** | 2026-05-15 | **QA 第四方審議補強：W0 +2 PD（QA 基礎建設）/ W2 +1 PD / W3 +1 PD / W5 +1 PD / W6 +1 PD；總 SD_05 = 48 PD；Q-C1 列舉 8 phase + fallback 保留期 + 拔除條件 + contract test；Q-C2 全測時間量測 + sharding + 24h 回退；Q-C3 補 mutation test + PG schema lock + coverage 階段化 + regression diff gate；Q-C4 補 3 中斷路徑 12 case；Q-C5 補 YAML backward-compat；Q-M1 EventBus trace_id；Q-M3 批次依 dependency tree；Q-M4 gate 分層（PR/G/Nightly）** |
| **v1.2** | 2026-05-16 | **PM 5 項拍板**：嵌入 model = Minimax API；UI = Next.js 15+ App Router + TS + Tailwind + Shadcn UI；認證 = 多 user RBAC；多 run 並存；KB 365 天月分割；G0 啟動條件達成 |
| **v1.3** | 2026-05-16 | **C 方案修正**：嵌入 model 改為 IEmbedder port + 雙 adapter（預設 BGEM3LocalAdapter）；新增 SD_06 W7 Docker 部署整合（+2 PD）；SD_06 W3 +1 PD（單→雙 adapter）；SD_06 總 28→31 PD；新增 docker-compose.yml（pgvector + TEI）+ deployment/README.md + tools/probe_minimax_embedding.py + .env.example 完整參數 |
| **v1.4** | 2026-05-16 | **W0 G0 通過 + 三方覆驗修復項**：T0-1 hookspec 27 phase / 10 IHookResult / 22 PHASE_RESULT_CONTRACT + MergedResult 11 欄；T0-2 wiring `_build_plugin_set` + `_register_in_order` SSOT；T0-3 PG 4 表 schema lock 25 case；T0-4 EventBus trace_id + escalate(N=3)；T0-5 FakePorts v2；T0-6 token_guard 子模組命名設計；**Architect/SA/SD 三方獨立審查**列 7 Critical（C1 frozen setattr 死碼 / C3 endswith 字串嗅探 / C4 MergedResult 無 round-trip 測試 / C5 escalate 未實作 / C6 wiring SSOT 無等價測試 / C7 feature flag 未實作 / C2 LOC 紅線提醒），**全部修復**：r._priority 改 object.__setattr__ / PersistenceResult.kind 欄位 / try-finally 確保失敗計數 / trace_id 不污染 payload / CounterSnapshot 衝突偵測 / `phase_migration_flag.py` 環境變數 / wire_plugins_with_registry 補 state_repository / FakePorts 對齊真實 port 簽名 / embedding 雙向測試 / hookspec docstring 統一；**覆驗測試基線 1,275 passed / 15 skipped**（+45 vs G0 起點 1,230） |
| **v1.5** | 2026-05-16 | **W1 G1 通過 + Counter SSOT 遷移**：Step-1 4 個 counter（goto/inject_before/skip_to/step_evolution）搬至 GotoCounterPlugin（property + live alias 機制）；Step-2 `_on_checkpoint_save_request` 改回傳 `CounterSnapshotResult` IHookResult；CheckpointPlugin 從 `MergedResult.counter_diff` 取資料（M-4 anti-pattern 過渡，W6 拔除）；**Architect/SD 三方獨立審查**列 1 Major + 4 Minor，**全部修復**：(A-M2) restore() 改就地 clear+update 避免 alias 失效；(SD-M1) counter_diff key namespace 規範文件化（§6.1）；(A-m3+SD-m4) backward compat 加 TODO(W6) + 拔除 3 點清單；(A-m4) snapshot_out → counter_snapshot_out 命名統一兼容舊鍵；(A-m5) alias 集中至連續宣告；(SD-m1) Execution_Guide G1 grep 命令更新；(SD-m2) 5th counter（_consecutive_compact_failures）型別路徑說明（W2 範圍）；(SD-m3) test_w1 改用公開 API；**SA 補**端對端整合測試（CheckpointRoundTrip 4 case + Gap-042/048 跨 session 防護 3 case）；**覆驗測試基線 1,312 passed / 15 skipped**（+37 vs G0 末 1,275） |
| **v1.6** | 2026-05-16 | **W2 G2 通過 + TokenGuardPlugin 5 方法群下沉**：(W2-0) PlaybookRunner 注入 TokenGuardPlugin；(W2-1a/b/c) `_get_dynamic_compact_threshold` / `_should_compact_now` / `_verify_correction_applied` delegate plugin；(W2-1d) `_send_compact` 重構 — prompt 構造 → `build_compact_prompt`；結果處理 → `process_compact_result`；(W2-1e) `_execute_prompt` token watch → `observe_token_line`；(W2-3 M-2) `_consecutive_compact_failures` 雙寫**完全拔除**（grep 0 writes），改為 property 委派 plugin SSOT；(W2-4 M-7) `PlaybookTask.token_guard: Optional[dict]` per-step override（W1 setup 高門檻 / W3 codegen 低門檻）；(W2-2) token_guard_plugin.py count_loc=219 ≤ 250 budget **暫不拆 package**（風險警示於 docstring，後續擴張前先拆 token_guard/ 四子模組設計已就位 SD_05_W0_token_guard_package_design.md v1.1）；**新測試** `tests/contract/test_playbook_yaml_backward_compat.py` **18 case**（schema backward compat 6 + per-step override 優先序 6 + W1/W3 情境 2 + M-2 雙寫拔除 4）；**測試基線 1,330 passed / 15 skipped**（+18 vs G1 末 1,312） |
| **v1.7** | 2026-05-16 | **W2 G2 三方覆驗修復**：Architect/SA/SD 三方獨立審查 4 Critical + 3 Major + 多 Minor，**全部修復**：(SD-C1) SD05_Execution_Guide G2 grep 命令更新為「寫入路徑」嚴格偵測；(SA-C1) 補 build_compact_prompt / observe_token_line / verify_correction_applied 三方法 **19 case** 測試（plugin coverage 預期 ≥ 90%）；(SA-C2 / C3) PlaybookTask.token_guard docstring 三層→兩層 + plugin docstring 移除誤列 `_handle_token_halt`；(Arch-C1) property setter lazy init 邏輯收緊（getter 不副作用，回傳 0；setter 仍允許 lazy 但僅供測試）；(SD-M1) plugin 補 `compact_failure_count` 公開 property + _runner_internals 兩處 logger 改用公開 API；(SD-M2 / Arch-M2) PlaybookTask 加 `field_validator("token_guard")` 攔截 typo（白名單 = TokenGuardConfig.model_fields）；(Arch-M3 / SA-M1) §6.2 補 W2 完成狀態 + namespace 建議；§6.3 補 W2 4 條 backward compat 拔除項；**覆驗測試基線 1,349 passed / 15 skipped**（+19 vs v1.6 末 1,330） |
| **v1.9** | 2026-05-16 | **W4 G4 通過 + MutationApplyService + 2 新 Plugin + GoalSynthesisPlugin 吸收 4 方法**：(W4-1) `MutationApplyService` 補 `ConditionalStrategy`（Gap-021）+ 反向注入 `_set_service`；conditional.py 拆 `_conditional_evaluator.py`（≤ 80 LOC 限制）；三層縱深防禦：regex 白名單 + 黑名單 `_DENY_CHARS` + shell=False + shlex.split；巢狀深度 `_MAX_RECURSION_DEPTH=4`（SD-M1 防 IO 風暴）；(W4-2) 新建 `FastPathPlugin`（PRE_ATTEMPT phase；_default_compiler 4 種例外明確分流 logger.warning 假陰性風險明示 SD-M3）；(W4-3) 新建 `PlaybookPersistencePlugin`（ON_EVOLUTION_APPLY phase；3 公開 API：persist / load / cleanup；callable resolver 動態 cfg.checkpoint_dir；on_event 回 `PersistenceResult(succeeded=True, kind="no_op")` 對齊 PHASE_RESULT_CONTRACT）；(W4-4) `GoalSynthesisPlugin` 吸收 4 mixin 方法（prepend_global_goal / prepend_global_goal_brief / build_achievement_summary / validate_global_goal_achievement）；(W4-5) wiring._REGISTER_ORDER + plugins/__init__.py 注入 2 新 plugin；**mixin delegate**：`_fast_path_test_file_check` / `_persist_mutated_playbook` / `_prepend_global_goal` / `_build_achievement_summary` / `_validate_global_goal_achievement` / `_prepend_global_goal_brief` 全部委派至 plugin；**三方審查** Architect / SA / SD 列 2 Critical（SA-C1/C2 plugin 未接線）+ 多 Major（Arch-M1+SD-M2+SA-M1 shell 安全 / Arch-M2+SA-M4 PHASE_RESULT_CONTRACT / SD-M1 巢狀深度 / SD-M3 假陰性）+ 多 Minor，**全部修復**；新測試：ConditionalStrategy **12 case**（14 unsafe + nested depth + shlex error + recursive 注入）/ FastPathPlugin **22 case** + coverage 100% / PlaybookPersistencePlugin **17 case** + coverage 100% / GoalSynthesisPluginW4Absorbed **14 case** boundary / TestW4PriorityInvariant **3 case** register_order 不變式；**覆驗測試基線 1,435 passed / 15 skipped**（+67 vs v1.8 末 1,368） |
| **v2.0** | 2026-05-16 | **W5 G5 通過 + 測試重寫 3 批次 + M-8（7 context regex coverage）+ M-9（AutoResumeMetrics）**：(批 1 plugins) tests/plugins/ 246 case 全綠（grep `_runner_internals` 無命中）；新增 test_fast_path（22 case，100%）+ test_playbook_persistence（17 case，100%）；(批 2 core+infra) 264 case 全綠 + test_event_bus_metrics 18 case（trace_id / phase_failure / escalate / migration_flag）；(批 3-A) integration+equivalence 115 case + equivalence 52/52；(批 3-B M-8) `tests/test_token_pattern_coverage.py` **38 case** + `tests/fixtures/claude_output_samples/` 8 樣本檔（70+ 行）；每 regex ≥ 95% 命中 + negative precision 100% + `TestMutationCoverage` + `TestFixtureInvariant` + `TestKnownFalsePositiveBoundary`（4 已知 limitation）；(批 3-C M-9) `autoclaude/core/services/_auto_resume_metrics.py`（151 LOC）`AutoResumeMetrics` dataclass + `record_wake_and_emit`（keyword-only）；AutoResumeService 三路徑 emit ON_AUTO_RESUME_WAKE + metrics 累計；`NotificationPlugin` 訂閱 ON_AUTO_RESUME_WAKE 回 `ScheduleResumeResult`；新增 test_auto_resume_metrics **18 case**（deque memory leak / Literal kind ValueError / HookContractViolation 冒泡）；**三方審查** Architect/SA/SD 列 **7 Critical + 13 Major + 12 Minor**，**全部修復**：(C-A1+SD1) `_make_stub_playbook()` 工廠每次新建；(C-A2) except 收斂 `(OSError, ValueError, RuntimeError)` + HookContractViolation 冒泡；(C-SA1) TestMutationCoverage；(C-SA2) negative_no_match 重寫 + TestKnownFalsePositiveBoundary；(C-SD2) 真實 EventBus + BadHook 驗證 contract violation；(C-SD3) LOC 口徑統一 wc -l；(M-A1) metrics property → snapshot dict；(M-A2) bus=None logger.error；(M-A3) 演化 wait_secs 由 seconds_until_resume 計算；(M-SA1) failed_emits + deque(maxlen=200)；(M-SA2) Literal kind + ValueError；(M-SA3) NotificationPlugin 訂閱避死碼；(M-SD2) MagicMock(side_effect) 取代 _SeqKernel；(M-SD5) keyword-only；Minor 12 條全修；**四方審議 4/4 APPROVED**（Architect/SA/SD/QA）；**覆驗測試基線 1,494 passed / 15 skipped**（+59 vs v1.9 末 1,435；coverage TOTAL **87%**；new plugins fast_path/playbook_persistence 各 100%；importlinter **3 kept / 0 broken**；LOC total=10754 / cap=12675 / **violations=0**；equivalence **52/52**） |
| **v2.1** | 2026-05-17 | **W6 G6 部分通過 + PM §1.3 例外簽核**：(W6-3) main.py + config.py 移除 use_kernel_path 雙路徑（tests/test_main_deprecation.py 刪除；tests/cli/test_cli_compatibility_v2.py 改名 TestUnknownConfigFieldTolerance）；(W6-4) CheckpointPlugin.__init__ 移除 `goto_counter_plugin=None` deprecated 參數 + `self._goto_counter` 屬性 + _phase_handlers.py/_builder.py fallback 拔除；(W6-5) KernelResult 確認 SSOT（main.py 唯一透過 AutoResumeService.run() 路徑）；**PlaybookResult 並存獲 PM §1.3 例外簽核**延後至 SD_06 W2（理由：物理拔除需 `_run_steps` 核心狀態機下沉，超過 W6 3 PD 預算）；(W6-6) **docs/08_deployment/SD05_Migration_Guide.md v1.1** 新建（含 §1.1 W6 完成範圍精確表 / §1.3 PM 例外條款 / §3.1 升級範例 constructor 注入 / §4 IHookResult 完整簽名 + PHASE_RESULT_CONTRACT / §6 SD_06 PD 重估 21 PD / §6.6 W6 物理 diff 摘要）；**W6-1/W6-2 部分執行**：_runner_internals.py（1,694 行）+ _runner_compat.py（238 行）**未物理刪除**，已標註 SD_06 W0~W3 範圍（risk_log R-W6-1~5 登記）；**§6.3 22 項拔除清單完成度 1/22**（僅第 11 項 CheckpointPlugin deprecated 參數）；**三方審查** Architect / SA / SD 列 **6 Critical + 6 Major + 多 Minor**，**全部修復**：(SD-C1) plugin.py 補回 `Any` import + `Optional[IHookResult]`；(SD-C2) config.yaml.example 刪除 use_kernel_path: true 行；(Arch-C1 + SA-C2) tests/cli/test_cli_compatibility_v2.py 改名 TestUnknownConfigFieldTolerance + fixture 改 legacy_unused_field；(Arch-C2) main.py filterwarnings 加註解保留至 SD_06；(SA-C1 + Arch-M2 + SA-C3) Migration Guide §1.1 22 項清單精確 + §1.3 PM 例外條款；(Arch-M3 + SA-m2) SD_06 PD 重估 14→21；(SA-M1) §3.1 範例 constructor 注入避免 race；(SA-M2 + M3) §4 IHookResult 簽名完整 + PHASE_RESULT_CONTRACT；(Arch-M4) _interrupt.py docstring；(SD-M2) CheckpointPlugin 補 `**deprecated_kwargs` + DeprecationWarning alias 過渡期；(SA-M4) §11 v2.1 補本條 + §3 進度表 W6 行更新；(SD-m3) Migration Guide §6.6 W6 物理 diff 摘要；(SD-m4) §7 grep 範圍擴大 autoclaude/+tests/+config.yaml.example；**覆驗測試基線 1,491 passed / 15 skipped**（-3 vs v2.0 末 1,494：test_main_deprecation 2 + test_backward_compat_when_bus_not_attached 1）；importlinter 3 kept / 0 broken；LOC violations 0；equivalence 52/52 |
| **v1.8** | 2026-05-16 | **W3 G3 通過 + CheckpointPlugin 吸收 3 中斷路徑**：(W3-1a~d) 4 個 mixin 方法 delegate plugin — `_save_evolution_resume_checkpoint` / `_handle_token_halt` / `_save_interrupt_checkpoint` / `_save_escalation_dump`；(W3-2) `checkpoint_plugin.py` 拆 6 子模組 package（`plugin.py` 175 / `_phase_handlers.py` 175 / `_builder.py` 71 / `_token_halt.py` 79 / `_escalation.py` 65 / `_interrupt.py` 54 / `_evolution.py` 45，全 ≤ 250 LOC）+ `checkpoint_plugin.py` re-export shim；(W3-3) EvolutionPlugin 訂閱 4 phase（ON_ESCALATION + ON_EVOLUTION_PROPOSE 正向 / ON_EVOLUTION_APPLY + ON_ESCALATION_DUMP_REQUEST NO-OP 過渡訂閱位）；(W3-新增 ON_PERSISTENCE_REQUEST / ON_ESCALATION_DUMP_REQUEST) CheckpointPlugin 訂閱 7 phase；**新測試** `tests/equivalence/test_counter_persistence_three_paths.py` **13 case**（3 中斷路徑 × 4 case = 12 規格 + 1 真實 deep-copy 防護 SD-M3 補強）；**三方審查** Architect / SA / SD 各列 1 Critical + 多 Major：(Arch-C1 + SD-C1) EscalationDumpedResult.dump_path 改為 `plugin._last_dump_path` 對齊 dump.save 真實路徑（修字串失真）；(Arch-C2 + SA-C1) EvolutionPlugin 2 NO-OP phase docstring + logger.info audit；(SA-M1+M2) 補 6 case ON_PERSISTENCE_REQUEST/ON_ESCALATION_DUMP_REQUEST 正向 IHookResult + EvolutionPlugin NO-OP 測試；(SD-M1) dump_path="" 失敗分支 notify_callback 傳 None + 補測試；(SD-M3) 12 case timing_pollution 改名為 caller_snapshot_discipline + 補 1 case 真實 plugin deep-copy 防護；(SD-M4) G3 grep delegate 驗證命令；(Arch-M1) `_save_escalation_dump` mixin closure 改 SimpleNamespace snapshot 避免 cfg 洩漏；(SA-M4) §6.3 補 W3 7 條 backward compat 拔除項（第 8~14 項）；**覆驗測試基線 1,368 passed / 15 skipped**（+19 vs v1.7 末 1,349；W3 新增：13 case 三中斷路徑 + 4 case ON_PERSISTENCE_REQUEST/ON_ESCALATION_DUMP_REQUEST 正向 + 2 case EvolutionPlugin NO-OP；coverage TOTAL 87%）） |

---

**簽核狀態**：
- ✅ Architect（2026-05-15 規劃審查 / 2026-05-16 W0 G0 覆驗，C1~C7 修復後 APPROVED）
- ✅ SA（2026-05-15 規劃審查 / 2026-05-16 W0 G0 覆驗，補 round-trip / escalate / wiring 等價測試後 APPROVED）
- ✅ SD（2026-05-15 規劃審查 / 2026-05-16 W0 G0 覆驗，frozen setattr / kind 欄位 / feature flag 修復後 APPROVED）
- ✅ QA（2026-05-15 v1.1 + 2026-05-16 W0 G0 四方核准，APPROVED）
- ✅ **PM（2026-05-16 §10 5 項全部拍板 + W0 G0 同意進入 W1 + W1 G1 同意進入 W2）**

**W1 G1 簽核狀態**（2026-05-16）：
- ✅ Architect（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 A-M2/m3/m4/m5 後 APPROVED）
- ✅ SA（規格對齊 + 文件更新 APPROVED）
- ✅ SD（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 SD-M1/m1/m2/m3/m4 後 APPROVED）
- ✅ QA 四方核准（測試基線 1,312 / 13 case W1 SSOT + 4 case CheckpointRoundTrip + 3 case Gap-042/048）

**W2 G2 簽核狀態**（2026-05-16）：
- ✅ Architect（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 Arch-C1/M2/M3/M4 後 APPROVED）
- ✅ SA（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 SA-C1/C2/M1/m1~m4 後 APPROVED）
- ✅ SD（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 SD-C1/M1/M2/m1~m6 後 APPROVED）
- ✅ QA 四方核准（測試基線 1,349 / 37 case W2 contract + 18 backward compat + 19 三方法測試）

**W3 G3 簽核狀態**（2026-05-16，待四方審議）：
- ⏳ Architect（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 Arch-C1/C2/M1 後待四方覆驗）
- ⏳ SA（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 SA-C1/M1/M2/M3/M4 後待四方覆驗）
- ⏳ SD（三方覆驗 APPROVED_WITH_CONDITIONS → 補修 SD-C1/M1/M3/M4 後待四方覆驗）
- ⏳ QA（待覆驗：測試基線 1,374 / 13 case 三中斷路徑 + 6 case 正向 IHookResult + EvolutionPlugin 2 NO-OP + checkpoint package 6 子模組 ≤ 250）
