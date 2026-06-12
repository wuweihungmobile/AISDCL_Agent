# SD_Improving_06 — Phase 7 Sprint 規劃（PG 三層任務模型 + Brain/Executor 分工 + W6 衍生收尾）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.2（PM 8 項拍板 APPROVED + G0 啟動日鎖定 2026-05-20）** |
| 建立日期 | 2026-05-17 |
| 前置文件 | [SD_Improving_05.md](SD_Improving_05.md) v2.1（W6 G6 部分通過 + PM §1.3 例外簽核）/ [SD05_Migration_Guide.md](../08_deployment/SD05_Migration_Guide.md) v1.1 §6（SD_06 PD 重估 21 PD）|
| 三方審查 | Architect / SA / SD 三方獨立審查 2026-05-17（六大關注點對應 Critical 風險清單）|
| QA 審議 | ✅ 2026-05-17 APPROVED_WITH_CONDITIONS（4 Critical 已補強 → v1.1）|
| PM 拍板 | ✅ 2026-05-17 8/8 APPROVED（PD 42 → 44，+2 PD：W0 PII schema +1 / W3 FK staging dry-run +1）|
| 文件狀態 | **APPROVED — 所有阻塞已解除（10/10）；G0 啟動日 2026-05-20** |

---

## 0. 三方審查共識摘要（2026-05-17）

針對使用者特別關注的 6 大議題，Architect / SA / SD 三方獨立提出 Critical / Major 風險清單。共識結論：

| # | 議題 | Architect 立場 | SA 立場 | SD 立場 | 共識 |
|---|------|----------------|---------|---------|------|
| **0** | Minimax（指揮）vs Claude Code（執行）職責分工 | 🔴 BrainPort 過於貧瘠（單方法），Runner 變相 Orchestrator | — | 🔴 引入 ExecutionEvent + send_interrupt 雙向訊號 + IOrchestrationCoordinator | **W1 引入 OrchestrationCoordinator + BrainPort/ExecutorPort 擴張** |
| **1** | 異常肥胖檔案 | 🔴 `_runner_internals.py` 1,694 行為 god-class，違反 250 LOC budget | — | — | **W2 拆 6 strategy 模組（≤ 250 LOC each）** |
| **2** | Plugin 架構合規 | 🔴 mixin 與 plugin 雙寫法導致 SSOT 破裂 | — | — | **W2 同波次徹底去除 mixin，importlinter 新增 `runner-no-checkpoint-logic` contract** |
| **3** | PG 三層任務模型 + Playbook YAML 持久化 | 🔴 4 表離 PM §10 三層差距巨大 | 🔴 三表 schema + RBAC 五表 + 多 run 並存 partial index | 🔴 alembic 編號衝突（既有鏈已到 0006，必須 0007 起）| **W3 新 alembic 0007-0012 完整鏈** |
| **4** | 向量檢索（pgvector HNSW） | 🔴 1536 維寫死 vs BGE-M3 1024 維 + 寫入路徑為 0 | 🔴 IEmbedder dim 對齊 + 三表 per-table HNSW 調參 | 🔴 採「新欄位 + dual-read」模式而非 ALTER（避免 rewrite 全表 + 鎖 HNSW） | **W3 並行：IEmbedder/IVectorSearch port + 雙 adapter + per-table HNSW 調參** |
| **5** | 狀態保存與恢復機制 | 🟠 dual_state fail_loud 僅 step_idx + idempotency key 缺 | 🔴 ExecutionContext dataclass round-trip + drift_log 表 + run_id 過濾 + 365 天 partition | 🔴 _resolve_start 改 run_id 破壞 CLI 相容需 deprecation；datetime/UUID/Enum normalize | **W5 dual_state drift 升級 + run_id 過濾 + 365 天 partition + dual-write PG-first** |
| **6** | 參數設定檔（/compact + token） | 🟠 ConfigResolver 階層化（global → workflow → step → runtime）| 🔴 5 階段 AC（含 hot-reload / schema versioning / UI 友善 / audit log）| 🟠 Pydantic nested model + 自動 promote flat→nested + DeprecationWarning | **W5 ConfigResolver + Pydantic v2 nested model + config_audit_log 表** |

**SD 一票否決事項（必須採納）**：
- ⛔ **alembic migration 編號衝突**：既有 0001~0006 已存在，原 SA 規劃 0005-0010 必須整體 +2 重排為 **0007-0012**
- ⛔ **1536 → 1024 維遷移策略**：禁止直接 ALTER vector(1536) → vector(1024)（會 rewrite 全表 + drop HNSW + 鎖表）；改採「新欄位 + dual-read + 6 個月 deprecation」
- ⛔ **0010 FK backfill 必須拆三步**：add nullable FK → backfill batch job → SET NOT NULL via `NOT VALID` + `VALIDATE CONSTRAINT`

---

## 1. Sprint 範圍合併

SD_06 範圍 = **SD_05 W6 衍生 21 PD**（PM §1.3 例外簽核項）+ **原 SD_06 PG 三層 25-30 PD**（PM §10 拍板項）+ **三方審查新增 +5 PD**（OrchestrationCoordinator / Pydantic ConfigResolver / advisory lock 等）。

| 來源 | PD 範圍 | 對應 Wave |
|------|--------|----------|
| SD_05 W6 衍生（`_runner_internals.py` / `_runner_compat.py` 物理刪除 + 22 項拔除清單 + PlaybookResult→KernelResult SSOT）| **17 PD** | W2 + W6 |
| 原 SD_06 PG 三層（projects/goal_tasks/execution_items + RBAC 五表 + alembic 0007-0012 + IEmbedder 雙 adapter + YAML 匯入工具 + KB 365 天 partition）| **20 PD** | W3 + W4 + W5 |
| 三方審查新增（OrchestrationCoordinator + BrainPort/ExecutorPort 擴張 + ConfigResolver 階層化 + dual_state drift 升級）| **9 PD** | W1 + W5 |
| **合計** | **46 PD** | W0-W6 |

---

## 2. 6 大關注點 → Wave 對應表（使用者必查）

| 關注點 | 對應 Wave | 對應 Acceptance Criteria | Critical 風險編號 |
|--------|----------|------------------------|------------------|
| **#0 Minimax/Claude Code 分工** | W1（4 PD）| AC0-1~AC0-4：BrainCapabilities + ExecutionEvent + IOrchestrationCoordinator | R-SD06-0-1 (Arch) / R-SD06-0-2 (SD) |
| **#1 肥胖檔案** | W2（8 PD）| AC1-1~AC1-3：6 strategy 模組 each ≤ 250 LOC + token_guard 拆 5 子模組 + importlinter 新 contract | R-SD06-1-1 (Arch) |
| **#2 Plugin 架構** | W2（並行）| AC2-1~AC2-2：mixin 物理刪除 + `_runner_internals.py` 為 0 行 + `runner-no-checkpoint-logic` contract 綠 | R-SD06-2-1 (Arch) |
| **#3 PG 三層任務模型 + YAML 持久化** | W3 + W4（13 PD）| AC3-1~AC3-5 + AC4-1~AC4-2：三表 + RBAC 五表 + alembic 0007-0012 + 60+ YAML 匯入率 100% | R-SD06-3-1 (Arch/SA) / R-SD06-3-2 (SA) |
| **#4 向量檢索（pgvector HNSW）** | W3（並行）| AC4-1~AC4-5：IEmbedder dim==1024 + 雙 adapter + per-table HNSW + recall@10 ≥ 0.95 | R-SD06-4-1 (Arch/SD) / R-SD06-4-2 (SD) |
| **#5 狀態保存恢復** | W5（5 PD）| AC5-1~AC5-5：ExecutionContext round-trip + drift_log + run_id 過濾 + 365 天 partition | R-SD06-5-1 (Arch/SA) |
| **#6 參數設定檔（/compact + token）** | W5（並行）| AC6-1~AC6-5：4 層 ConfigResolver + Pydantic v2 + UI 友善 + audit log | R-SD06-6-1 (Arch/SA) |

---

## 3. Critical 風險清單（三方共識）

### 🔴 議題 0：Minimax vs Claude Code 分工

**R-SD06-0-1 [Architect]**：BrainPort 過於貧瘠（單 `decide_correction`），Runner 變相扮演 Orchestrator
- **緩解**：W1 引入 `OrchestrationCoordinator`，BrainPort 擴增 `capabilities() / decide_escalation()`，ExecutorPort 擴增 `send_interrupt() / on_event` callback

**R-SD06-0-2 [SD]**：Callback 反向依賴 + Interrupt 信號競態
- **緩解**：採 EventBus 而非直接 callback；`send_interrupt()` 在 Coordinator 用 `asyncio.Event` + sequence number 序列化 + Executor ACK

### 🔴 議題 1+2：肥胖檔案 + Plugin 架構

**R-SD06-1-1 [Architect]**：`_runner_internals.py` 1,694 行為 god-class
- **緩解**：W2 拆 6 strategy 模組：`steps_orchestrator.py` / `prompt_dispatcher.py` / `mutation_applier.py` / `compact_controller.py` / `halt_handler.py` / `escalation_dumper.py`（每檔 ≤ 250 LOC）

**R-SD06-2-1 [Architect]**：mixin 與 plugin 雙寫法導致 SSOT 破裂
- **緩解**：W2 將 `_save_evolution_resume_checkpoint` / `_save_interrupt_checkpoint` / `_save_escalation_dump` 物理移至 CheckpointPlugin；importlinter 新增 `runner-no-checkpoint-logic` contract

### 🔴 議題 3：PG 三層任務模型

**R-SD06-3-1 [Arch/SA]**：4 表離 PM §10 三層差距巨大 + 缺 RBAC 五表
- **緩解**：W3 alembic 0009 三表 + 0011 RBAC 五表 + 0010 既有 4 表加 nullable FK

**R-SD06-3-2 [SA]**：多 run 並存約束未設計（同 GoalTask N 個 active run）
- **緩解**：W3 `playbook_runs` 新增 partial index `WHERE status='running'`；`abort_run(run_id)` API 不影響其餘並存 run

### 🔴 議題 4：向量檢索（pgvector HNSW）

**R-SD06-4-1 [Arch/SD]**：1536 維寫死 vs BGE-M3 1024 維 + 寫入路徑為 0
- **緩解**：W3 採「新欄位 + dual-read」模式：保留舊 `embedding vector(1536)` 6 個月 deprecation；新增 `embedding_v halfvec(1024)` + `embedding_model_id text`；所有查詢以 `model_id` filter 強制隔離

**R-SD06-4-2 [SD]**：HNSW 線上重建鎖表
- **緩解**：強制 `CREATE INDEX ... USING hnsw CONCURRENTLY`；按 model_id 拆 partial index

### 🔴 議題 5+6：狀態恢復 + 設定檔

**R-SD06-5-1 [Arch/SA]**：`dual_state_repository.fail_loud` 僅比對 step_idx
- **緩解**：W5 升級為 `dataclasses.asdict()` 全欄比對 + `_normalize()` 函式（datetime → ISO8601 UTC / UUID → str / Enum → value）+ drift_log 表

**R-SD06-6-1 [Arch/SA]**：config.yaml 無 per-step / per-workflow hierarchy
- **緩解**：W5 引入 `ConfigResolver`（4 層 merge）+ Pydantic v2 `model_validator` invariants + UI 友善 OpenAPI 3.1 schema

---

## 4. Wave 執行計畫

### ── W0：規格化 + alembic 編號修正 + QA 基礎建設（3 PD）──

**目標**：
- 三方審查共識 AC 寫入規格文件
- alembic 編號鎖死從 0007 起（既有鏈到 0006）
- 補 `tests/contract/test_alembic_chain_lock.py`（既有 6 migration head 鎖死）
- QA fixture：`tests/fixtures/sample_goal_tasks.yaml`（10 個三層任務樣本）

**G0 驗證**：
```bash
ls alembic/versions/ | wc -l                    # 期望：6（無新增）
python -m pytest tests/contract/ -q --tb=no    # 期望：≥ 1,491 passed
```

---

### ── W1：OrchestrationCoordinator + BrainPort/ExecutorPort 擴張（4 PD）──

**目標**：
- BrainPort 擴增：`capabilities() → BrainCapabilities` + `decide_escalation() → EscalationDecision`
- ExecutorPort 擴增：`execute(..., on_event=callback)` + `send_interrupt(reason) → bool`
- 新增 `autoclaude/core/orchestration/coordinator.py`（≤ 250 LOC）
- 新增 phase 序：`BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC`

**G1 驗證**：
```bash
python -m pytest tests/core/test_orchestration_coordinator.py -v  # ≥ 12 case
python -m pytest tests/core/ports/test_brain_capabilities.py -v   # ≥ 4 case
python -m pytest tests/ -q --tb=no | tail -3                       # ≥ 1,491 passed
```

---

### ── W2：`_runner_internals.py` god-class 拆解 + Plugin SSOT 收斂（8 PD）──

**目標**：
- W2-1：`_run_steps`（840 行）拆 `steps_orchestrator.py`（≤ 250 LOC）+ `ExecutionContext` dataclass
- W2-2：`_apply_single_mutation_full`（295 行）拆 `mutation_applier.py`（apply / verify / persist 各 ~100 LOC）
- W2-3：`_execute_prompt`（79 行）拆 `prompt_dispatcher.py`（≤ 100 LOC，下沉至 ExecutorPort）
- W2-4：`_handle_token_halt` + compact 邏輯下沉 `compact_controller.py` + `halt_handler.py`
- W2-5：`_save_evolution_resume_checkpoint` / `_save_interrupt_checkpoint` / `_save_escalation_dump` **物理移至** CheckpointPlugin
- W2-6：`token_guard_plugin.py`（283 行 > 250）拆 `token_guard/{watcher,compactor,thresholds,git_verifier,policy}.py`（每檔 ≤ 100 LOC）
- W2-7：importlinter 新增 contract `runner-no-checkpoint-logic`（grep `_save_.*_checkpoint` 在 runner 必須 0 行）

**G2 驗證**：
```bash
wc -l autoclaude/execution/_runner_internals.py
# 期望：≤ 80（thin mixin facade，準備 W6 物理刪除）

python tools/check_loc_budget.py
# 期望：violations=0

PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：4 kept / 0 broken（新增 runner-no-checkpoint-logic contract）

python -m pytest tests/ -q --tb=no | tail -3
# 期望：≥ 1,491 passed
```

---

### ── W3：alembic 0007-0012 + IEmbedder 雙 adapter + 三層 schema（13 PD）──

**目標**：
- **W3-1**：alembic 0007_kb_unique_ttl_partition（C-8：UNIQUE(error_class, error_signature) + recorded_at 月分區 + 365 天 TTL trigger）
- **W3-2**：alembic 0008_embedding_variable_dim（C-6：新欄位 `embedding_v halfvec(1024)` + `embedding_model_id text` + partial HNSW per model_id；舊 `vector(1536)` 6 個月 deprecation）
- **W3-3**：alembic 0009_three_tier_schema（projects / goal_tasks / execution_items + per-table HNSW `m={8,24,16}` + `config_snapshot JSONB` 凍結 run 設定快照）
- **W3-4**：alembic 0010_link_legacy_to_tiers（既有 4 表加 nullable FK，**拆三步**：add nullable → backfill batch → SET NOT NULL via NOT VALID + VALIDATE CONSTRAINT）
- **W3-5**：alembic 0011_rbac_tables（users / roles / role_bindings + casbin policy seed）
- **W3-6**：alembic 0012_yaml_import_staging（yaml_import_jobs + yaml_import_diffs + advisory lock）
- **W3-7**：新增 `autoclaude/core/ports/embedder.py`（IEmbedder Protocol 含 `dimension / model_id / embed / embed_one / health_check`）
- **W3-8**：新增 `autoclaude/core/ports/vector_search.py`（IVectorSearch Protocol + VectorHit dataclass）
- **W3-9**：`BGEM3LocalAdapter`（HTTP + TEI 容器，1024 維）+ `MinimaxEmbedderAdapter`（API 備援）+ CircuitBreaker fallback
- **W3-10**：寫入路徑接入 `create_goal_task()` / `update_goal_task()` / `complete_execution_item()`

**G3 驗證**：
```bash
alembic upgrade head    # 0001 → 0012 全鏈通過
python -m pytest tests/contract/test_three_tier_schema.py -v  # AC3-1~AC3-5
python -m pytest tests/contract/test_embedder_contract.py -v  # AC4-1~AC4-5
python -m pytest tests/integration/test_pgvector_hnsw_recall.py -v  # recall@10 ≥ 0.95
```

---

### ── W4：YAML → DB 匯入工具 + 60+ YAML 回歸（5 PD）──

**目標**：
- W4-1：`tools/migrate_yaml_to_db.py`（Click CLI）：讀 60+ YAML playbook → 寫 `playbook_versions` + `projects` + `goal_tasks` + `execution_items`
- W4-2：advisory lock `pg_advisory_xact_lock(hash(playbook_id))` 避免並發 import 衝突
- W4-3：版本控制：`playbook_versions.sha256 NOT NULL`，重複 import 跳過
- W4-4：dry-run 模式：`--dry-run` 輸出 diff 報告不寫入

**G4 驗證**：
```bash
python tools/migrate_yaml_to_db.py --source scripts/ --dry-run
# 期望：60+ YAML 全部可解析 + diff 報告無錯誤

python -m pytest tests/integration/test_yaml_import.py -v
# 期望：60+ YAML 雙向往返驗證 100%
```

---

### ── W5：狀態恢復升級 + ConfigResolver + dual_state drift（5 PD）──

**目標**：
- **W5-1**：`ExecutionContext` dataclass（step_idx / evolution_count / auto_resume_count / checkpoint_dir / goal_task_id / run_id / token_usage_history）+ round-trip property-based test ≥ 5 case
- **W5-2**：DualStateRepository drift 偵測升級：`detect_drift(run_id) → DriftReport`，全欄比對 + `_normalize()`（datetime → ISO8601 UTC / UUID → str / Enum → value）；drift_log 表
- **W5-3**：`load_checkpoint(run_id)` + `load_latest_by_playbook(playbook_id)` 雙 API；舊 `load_by_playbook_id` 發 DeprecationWarning
- **W5-4**：dual-write 順序「PG-first, file-second」；PG 失敗 raise；file 失敗 warn + reconcile queue
- **W5-5**：`ConfigResolver`：4 層階層 merge（global → workflow → step → runtime）+ Pydantic v2 nested model `TokenGuardConfig`（`compact_threshold_pct ∈ [50, 95]`、`halt_threshold_pct > compact_threshold_pct` invariants）
- **W5-6**：自動 promote flat → nested（向下相容舊 YAML）+ DeprecationWarning
- **W5-7**：`config_audit_log(user_id, run_id, field_path, old_value, new_value, applied_at)` 表
- **W5-8**：`GET /api/config/schema` 回傳 OpenAPI 3.1 schema（SD_07 UI 預備）

**G5 驗證**：
```bash
python -m pytest tests/equivalence/test_execution_context_roundtrip.py -v  # AC5-1
python -m pytest tests/contract/test_dual_state_drift.py -v               # AC5-2
python -m pytest tests/contract/test_config_resolver.py -v                # AC6-1~AC6-2
python -m pytest tests/integration/test_config_audit_log.py -v            # AC6-5
```

---

### ── W6：物理刪除 + Migration Guide + 22 項拔除清單清零（4 PD）──

**目標**：
- W6-1：物理刪除 `_runner_internals.py`（前置：grep `_runner_internals` 在 autoclaude/+tests/ 為 0）
- W6-2：物理刪除 `_runner_compat.py`（前置：PlaybookResult → KernelResult SSOT 完成）
- W6-3：`PlaybookRunner.run()` 回傳型別改 `KernelResult`（~50+ assertion 更新）
- W6-4：SD_05 §6.3 22 項拔除清單清零（W6 完成 1/22；剩餘 21 項隨核心方法下沉一併處理）
- W6-5：`_pr()` 反向動態 import 拔除（30+ 測試 patch path 大量遷移）
- W6-6：更新 `docs/08_deployment/SD06_Migration_Guide.md`（含 alembic 升級 + RBAC 啟用 + ConfigResolver 升級 + 雙 adapter 切換）
- W6-7：三方/四方審查 ✅

**G6 最終驗證**：
```bash
# 1. 全測
python -m pytest tests/ -q --tb=no | tail -3
# 期望：≥ 1,491 passed（實際應更高，因新增 W1-W5 測試）

# 2. equivalence 全綠
python -m pytest tests/equivalence/ -q --tb=no | tail -3

# 3. importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：5 kept / 0 broken（新增 brain-executor-isolation + runner-no-checkpoint-logic）

# 4. LOC
python tools/check_loc_budget.py
# 期望：violations=0

# 5. 確認物理刪除
test ! -f autoclaude/execution/_runner_internals.py && echo "OK"
test ! -f autoclaude/execution/_runner_compat.py && echo "OK"

# 6. SD_05 §6.3 22 項拔除清零
grep -r "TODO(SD_05 W6)" autoclaude/ tests/ | wc -l
# 期望：0

# 7. alembic 全鏈
alembic upgrade head && alembic current
# 期望：0012 為 head

# 8. 60+ YAML 匯入率
python tools/migrate_yaml_to_db.py --source scripts/ --report
# 期望：success_rate == 100%

# 9. coverage ≥ 87%
python -m coverage report --include="autoclaude/*" | tail -5
```

---

## 5. PD 估算

| Wave | 範圍 | PD（v1.2 PM 拍板後） |
|------|------|----|
| W0 | 規格化 + alembic 編號鎖死 + QA 基礎建設 + **PII/secret 欄位分類 ENUM schema**（PM #11 hybrid）| 3 → **4** (+1) |
| W1 | OrchestrationCoordinator + BrainPort/ExecutorPort 擴張 + **Layer 1.5/2 邊界 ADR**（PM #12）| 4 |
| W2 | `_runner_internals.py` god-class 拆 6 模組 + token_guard 拆 5 子模組 + Plugin SSOT 收斂 + **MAX_ACTIVE_RUNS_PER_GOAL=5 guard**（PM #8）| 8 |
| W3 | alembic 0007-0012 + IEmbedder/IVectorSearch + 雙 adapter + 三層 schema + **0010 FK 1M 列 staging dry-run + 回退演練**（PM W-1）+ **embedding_status 三態 + retry queue + SLO 告警**（PM #9）+ **PII 過濾器實作**（PM #11）+ **re-embed batch job + 7 天 SLA**（PM #10）| 13 → **14** (+1) |
| W4 | YAML → DB 匯入工具 + 60+ YAML 回歸 + advisory lock | 5 |
| W5 | ExecutionContext + drift 升級 + ConfigResolver + Pydantic v2 + audit log | 5 |
| W6 | 物理刪除 + 22 項拔除清零 + Migration Guide | 4 |
| **合計** | | **44 PD**（+2 vs v1.1）|

**PM contingency**：預留 **3 PD**（來源：v2 feature backlog 延後），用於 W3 FK backfill dry-run 失敗回退場景。

**估算對齊**：
- PM §1.3 預估 SD_05 W6 衍生 21 PD → SD_06 涵蓋 17 PD（W2 8 + W6 4 + W5-1~4 5 = 17）
- 原 SD_06 PG 三層 25-30 PD → SD_06 涵蓋 20 PD（W3 13 + W4 5 + W5-5~8 部分 2 = 20）
- 三方審查新增 5 PD（W1 4 + W0 1 = 5）

---

## 6. alembic Migration 編號表（SD 一票否決鎖死）

⛔ **既有鏈（不可更動）**：0001 → 0002 → 0003 → 0004 → 0005 → 0006

⚠️ **SD_06 新增鏈（每支對應 contract test + per-migration 回退劇本，QA-C2/C3 補強）**：

| 編號 | 檔名 | 用途 | Contract Test | 回退策略 |
|------|------|------|---------------|---------|
| 0007 | `0007_kb_unique_ttl_partition.py` | UNIQUE(error_class, error_signature) + 365 天月分區 + TTL trigger | `tests/contract/test_alembic_0007_ttl.py` ≥ 8 case（partition rotate / TTL trigger / UNIQUE 衝突）| ✅ `downgrade -1`（純結構） |
| 0008 | `0008_embedding_variable_dim.py` | 新欄位 `embedding_v halfvec(1024)` + `embedding_model_id` + partial HNSW per model_id；舊 `vector(1536)` 6 個月 deprecation | `tests/contract/test_alembic_0008_dual_read.py` ≥ 6 case（model_id filter / dim mismatch / dual-read） | ⚠️ **point-of-no-return**：新欄位若已有查詢流量則不可 downgrade；改前滾修補（drop 新欄位 + 重建） |
| 0009 | `0009_three_tier_schema.py` | projects / goal_tasks / execution_items + per-table HNSW + config_snapshot JSONB | `tests/contract/test_three_tier_schema.py` ≥ 12 case（FK CASCADE / RBAC / sub-task 樹）| ✅ `downgrade -1`（無業務資料） |
| 0010 | `0010_link_legacy_to_tiers.py` | 既有 4 表加 nullable FK（**三步**：add → backfill → SET NOT NULL via NOT VALID + VALIDATE CONSTRAINT） | `tests/contract/test_alembic_0010_fk_three_step.py` ≥ 10 case（每步單獨可回退 + 1M 列 staging dry-run）| ⚠️ **point-of-no-return**：backfill step 2 ≥ 50% 後改前滾修補；step 1 / step 3 仍可 `downgrade -1` |
| 0011 | `0011_rbac_tables.py` | users / roles / role_bindings + casbin policy seed | `tests/contract/test_alembic_0011_rbac.py` ≥ 8 case（admin/dev/viewer matrix / role assign / policy enforce） | ✅ `downgrade -1`（純結構 + seed） |
| 0012 | `0012_yaml_import_staging.py` | yaml_import_jobs + yaml_import_diffs + advisory lock | `tests/contract/test_alembic_0012_advisory_lock.py` ≥ 6 case（並發 import / 鎖獲取超時 / staging diff 計算）| ✅ `downgrade -1`（staging 表清空） |

**G3 驗證**：alembic upgrade head 必須無錯且 `0012` 為 head；rollback 任一階段不破壞既有 4 表既有資料；每支 migration 進入 production 前需有 **1M 列 staging DB 完整 dry-run + 回退演練紀錄**（QA-C1）。

**HNSW 重建期間查詢服務（W3-2 QA-C4 補強）**：
- 0008 dual-read 模式：查詢 SQL 加 `WHERE embedding_model_id = ANY([:active_model, :fallback_model])` 同時讀新舊欄位
- 重建期間 fallback 路徑：若新 HNSW index 未就緒，自動降級走舊 `vector(1536)` index（CircuitBreaker 偵測 query latency > 200ms 觸發）
- SLO degradation contract：recall@10 從 0.95 暫降為 0.90 視為**黃線告警**（不阻塞服務 + 48h Wave 內修正期）；< 0.90 才觸發 §11 回退

---

## 6.5 Acceptance Criteria Matrix（QA-C1 補強，每條可量測）

| AC ID | 議題 | 量測命令 | Pass 門檻 | 對應測試檔 |
|-------|------|---------|---------|----------|
| AC0-1 | Brain capabilities | `python -c "from autoclaude.core.ports.brain import IBrain; print(IBrain.capabilities)"` | 簽名含 `max_context_tokens / supports_streaming / retry_policy` | `tests/core/ports/test_brain_capabilities.py` |
| AC0-2 | Executor on_event callback | grep `on_event` in `core/ports/executor.py` | ≥ 1 行（Callable[[ExecutionEvent], None]）| `tests/core/ports/test_executor_events.py` |
| AC0-3 | Coordinator phase order | `pytest tests/core/test_orchestration_coordinator.py::test_phase_order` | 6 phase 序列正確 | `tests/core/test_orchestration_coordinator.py` |
| AC0-4 | Brain-Executor isolation | `lint-imports --config .importlinter` | `brain-executor-isolation` contract kept | `.importlinter` |
| AC1-1 | _runner_internals.py LOC | `wc -l autoclaude/execution/_runner_internals.py` | W2 末 ≤ 80；G6 末檔案不存在 | `tools/check_loc_budget.py` |
| AC1-2 | strategy 模組 LOC | `wc -l autoclaude/execution/{steps_orchestrator,prompt_dispatcher,mutation_applier,compact_controller,halt_handler,escalation_dumper}.py` | 每檔 ≤ 250 | `tools/check_loc_budget.py` |
| AC1-3 | token_guard 子模組 | `ls autoclaude/plugins/token_guard/ \| wc -l` | ≥ 5（watcher/compactor/thresholds/git_verifier/policy） | `tools/check_loc_budget.py` |
| AC2-1 | 雙寫法消除 | `grep -c "_save_.*_checkpoint" autoclaude/execution/_runner_internals.py` | W2 末 = 0 | `.importlinter` `runner-no-checkpoint-logic` |
| AC2-2 | mixin 物理刪除 | `test ! -f autoclaude/execution/_runner_internals.py` | G6 末 OK | `tests/contract/test_w6_deletion.py` |
| AC3-1 | 三表 FK | `pytest tests/contract/test_three_tier_schema.py::test_fk_cascade` | ≥ 3 case 綠 | `tests/contract/test_three_tier_schema.py` |
| AC3-2 | 既有 4 表整合 FK | `alembic upgrade 0010` + 全測 | 1,491+ passed 不退化 | `tests/contract/test_alembic_0010_fk_three_step.py` |
| AC3-3 | RBAC 五表 + role matrix | `pytest tests/contract/test_alembic_0011_rbac.py` | ≥ 5 case 綠 + 違反 role 必 403 | `tests/contract/test_alembic_0011_rbac.py` |
| AC3-4 | 多 run 並存 | `pytest tests/integration/test_concurrent_runs.py` | 5 run × abort 互不影響 | `tests/integration/test_concurrent_runs.py` |
| AC3-5 | per-table HNSW 建立 | `psql -c "SELECT indexname FROM pg_indexes WHERE indexname LIKE '%hnsw%'"` | ≥ 3 個 HNSW index（goal_tasks m=8 / kb m=16 / execution_items m=16）| `tests/contract/test_three_tier_schema.py` |
| AC4-1 | IEmbedder 維度 | `python -c "from autoclaude.infra.adapters.bgem3_local import BGEM3LocalAdapter; assert BGEM3LocalAdapter().dimension == 1024"` | exit code 0 | `tests/contract/test_embedder_contract.py` |
| AC4-2 | 雙 adapter fallback | `pytest tests/contract/test_embedder_fallback.py` | CircuitBreaker 3 fail → 切備援 < 60s | `tests/contract/test_embedder_fallback.py` |
| AC4-3 | 寫入路徑 | `pytest tests/integration/test_embedding_write_paths.py` | 3 觸發點皆有 embedding IS NOT NULL | `tests/integration/test_embedding_write_paths.py` |
| AC4-4 | 1536→1024 遷移 | `alembic upgrade 0008 && SELECT COUNT(*) FROM knowledge_entries WHERE embedding_v IS NOT NULL` | 既有資料 truncate + audit log 寫入 | `tests/contract/test_alembic_0008_dual_read.py` |
| AC4-5 | recall@10 + p95 | `pytest tests/integration/test_pgvector_hnsw_recall.py` | recall@10 ≥ 0.95 + p95 < 50ms | `tests/integration/test_pgvector_hnsw_recall.py` |
| AC5-1 | ExecutionContext round-trip | `pytest tests/equivalence/test_execution_context_roundtrip.py` | Hypothesis ≥ 50 example 100% pass（QA-M5 補強）| `tests/equivalence/test_execution_context_roundtrip.py` |
| AC5-2 | drift 全欄比對 | `pytest tests/contract/test_dual_state_drift.py` | ≥ 4 case（含 datetime/UUID/Enum normalize）| `tests/contract/test_dual_state_drift.py` |
| AC5-3 | run_id 過濾 | `pytest tests/contract/test_checkpoint_run_id_filter.py` | 5 run × 互不干擾 | `tests/contract/test_checkpoint_run_id_filter.py` |
| AC5-4 | SIGINT checkpoint SLA | `pytest tests/integration/test_sigint_checkpoint.py` | ≤ 2s 寫入完成 | `tests/integration/test_sigint_checkpoint.py` |
| AC5-5 | 365 天 partition | `psql -c "\d+ knowledge_entries"` | 12 個月 partition + default partition | `tests/contract/test_alembic_0007_ttl.py` |
| AC6-1 | 4 層 ConfigResolver | `pytest tests/contract/test_config_resolver.py` | ≥ 6 case（property-based 4 層 × 缺欄組合）| `tests/contract/test_config_resolver.py` |
| AC6-2 | Pydantic invariants | `pytest tests/contract/test_token_guard_config_validation.py` | ≥ 8 case（halt > compact / 範圍）| `tests/contract/test_token_guard_config_validation.py` |
| AC6-3 | OpenAPI 3.1 schema | `curl http://localhost:8000/api/config/schema \| jq '.openapi'` | == "3.1.0" + ≥ 15 欄位 | `tests/integration/test_config_schema_api.py` |
| AC6-4 | YAML→DB 匯入 | `python tools/migrate_yaml_to_db.py --source scripts/ --report` | success_rate == 100% + JSONB key 順序 + float ±1e-6 等價 | `tests/integration/test_yaml_import.py` |
| AC6-5 | config audit log | `pytest tests/integration/test_config_audit_log.py` | runtime override 必寫入 + RBAC 保護欄位 403 | `tests/integration/test_config_audit_log.py` |

---

## 7. 架構紅線（SD_06 共識，絕對不可採用）

繼承 SD_05 §5 全部 8 條紅線，**新增 5 條**：

| # | 禁止行為 | 來源 |
|---|----------|------|
| ❌9 | alembic 編號跳號或重複（既有鏈 0001-0006 鎖死，新鏈從 0007 起連續編號）| SD 一票否決 |
| ❌10 | 直接 ALTER vector(1536) → vector(1024)（會 rewrite 全表 + drop HNSW + 鎖表）| SD R-SD06-4-1 |
| ❌11 | FK backfill 與 SET NOT NULL 在同事務（會與在線寫入衝突死鎖）| SD R-SD06-3-1 |
| ❌12 | Brain 與 Executor 透過直接 callback 互相 import（必須走 EventBus）| SD R-SD06-0-2 |
| ❌13 | mixin 與 plugin 雙寫法（W2 必須徹底物理移除 mixin 中的 `_save_*` 方法）| Arch R-SD06-2-1 |

---

## 8. 風險登記（更新 risk_log）

| 編號 | 描述 | 嚴重 | 對應 |
|------|------|------|------|
| **R-SD06-0-1** | BrainPort 過於貧瘠，Runner 變相 Orchestrator | 🔴 | Arch 議題 0 |
| **R-SD06-0-2** | Brain/Executor 反向依賴 + Interrupt 競態 | 🔴 | SD 議題 0 |
| **R-SD06-1-1** | `_runner_internals.py` 1,694 行 god-class | 🔴 | Arch 議題 1 |
| **R-SD06-2-1** | mixin/plugin 雙寫法 SSOT 破裂 | 🔴 | Arch 議題 2 |
| **R-SD06-3-1** | 三表 + RBAC 五表 schema 差距 | 🔴 | Arch/SA 議題 3 |
| **R-SD06-3-2** | 多 run 並存約束未設計 | 🟠 | SA 議題 3 |
| **R-SD06-4-1** | 1536 維寫死 + 寫入路徑為 0 | 🔴 | Arch/SD 議題 4 |
| **R-SD06-4-2** | HNSW 線上重建鎖表 | 🔴 | SD 議題 4 |
| **R-SD06-5-1** | dual_state fail_loud 僅 step_idx | 🔴 | Arch/SA 議題 5 |
| **R-SD06-5-2** | _resolve_start run_id 改造破壞 CLI 相容 | 🟠 | SD 議題 5 |
| **R-SD06-6-1** | config 無階層化 + 無 audit log | 🟠 | Arch/SA 議題 6 |
| **R-SD06-6-2** | Pydantic flat→nested 向下相容 | 🟠 | SD 議題 6 |

---

## 9. PM/Stakeholder 拍板事項

### 9.1 已拍板（沿用 SD_05 §10）

| # | 項目 | 拍板結論 |
|---|------|---------|
| 1 | 嵌入 model | C 方案 IEmbedder port + 雙 adapter（BGE-M3 1024 維預設 + Minimax API 備援）|
| 2 | UI 技術棧 | Next.js 15+ App Router + TS + Tailwind + Shadcn UI |
| 3 | 認證模式 | 多 user RBAC（enterprise）|
| 4 | 多 run 並存策略 | 多 run 並存（同 GoalTask 允許並發）|
| 5 | KB 數據保留期 | 365 天月分割 |

### 9.2 SD_06 PM 8 項拍板（✅ 2026-05-17 全數 APPROVED）

| # | 項目 | 三方建議 | **PM 決議** | 影響 |
|---|------|---------|-----------|------|
| 6 | GoalTask sub-task 樹狀深度上限 | SA 建議：深度 ≤ 3 | **(B) 深度 ≤ 3**（採 SA 建議；對齊 epic/story/task 三層）| W3 schema 加深度 CHECK constraint |
| 7 | RBAC role seed data | SA 建議：admin/developer/viewer | **(A) 三角色**（admin=全權；developer=project CRUD；viewer=read-only；保留 `policy_json` 欄位後擴 casbin）| W3 0011 seed data 三角色 |
| 8 | 多 run 並存資源上限 | Arch 建議：≤ 5 | **(B) ≤ 5**（環境變數 `MAX_ACTIVE_RUNS_PER_GOAL=5`，超限 enqueue 為 pending；配額監控延至 W6）| W2 OrchestrationCoordinator 落地前埋入 guard |
| 9 | embed 失敗時 GoalTask 建立行為 | SA 建議：最終一致 | **(B) 最終一致**（`embedding_status` 三態 pending/ok/failed；背景 retry 上限 5 次後告警）| W3 補 retry queue + 告警通道（W3 設計時必含 SLO，不可延至 W6）|
| 10 | re-embed 觸發策略 | SA 建議：背景 batch + 7 天 SLA | **(B) 背景 batch + 7 天 SLA**（避免停服；雙模型 dual-read 工程成本過高 +3 PD）| W3 補 re-embed job 設計 |
| 11 | PII 過濾 / secret mask 規則 | SA：W3 設計 / QA 警示：前移 W0 | **(C) hybrid**：W0 完成欄位分類 schema (PII/secret/normal ENUM) + W3 實作過濾器與 audit | **W0 +1 PD**（折衷 QA 警示與 PD 預算）|
| 12 | OrchestrationCoordinator vs AutoResumeService | Arch 建議：雙層保留 | **(B) 雙層保留**（AutoResumeService=Layer 2 stable legacy；Coordinator=Layer 1.5；要求 Architect 出 ADR 明文邊界）| W1 任務加 ADR 撰寫 |

### 9.3 SD_06 QA 2 項強制警示（✅ 2026-05-17 PM 簽核）

| # | 警示 | **PM 決議** | 影響 |
|---|------|-----------|------|
| W-1 | 0010 FK backfill 單點失效 — W3-4 進入前需 1M 列 staging dry-run + 回退演練 | **(A) 接受 1M 列 staging dry-run**（不可降級；資料層回退失敗將造成 partition 災難）| **W3 +1 PD**（G3 強制前置條件）|
| W-2 | PII/secret mask 規則前移 W0 | **(C) hybrid，連動 #11**（W0 schema 分類 + W3 過濾器實作）| 與 #11 合併 PD 計算 |

### 9.4 PM 附加風險警示

**致 Tech Lead**：
- #8 並存 run 限制需在 W2 OrchestrationCoordinator 落地前即埋入 guard，避免 W4 才補導致行為不一致
- #11 hybrid 方案要求 W0 schema 必須一次到位，後續 W3 過濾器若發現遺漏欄位將觸發 migration；W0 review 拉法務/Security 共審

**致 Architect**：
- #12 雙層架構需明文 ADR (Layer 1.5 vs Layer 2 邊界)，否則 6 個月內易退化為循環依賴
- #9 最終一致下，embedding retry 失敗 5 次後的告警通道與 SLO 需於 W3 設計時補齊（不可遺漏至 W6 監控階段）

**全局風險**：+2 PD 已吃掉 W6 緩衝 50%，若 W3 FK backfill dry-run 失敗需回退，PM 預留 **3 PD contingency**（來源：v2 feature backlog 延後）

---

## 10. CI / Quality Gates

### 10.1 PR-level

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| `lint-imports` | 5 kept / 0 broken（新增 brain-executor-isolation + runner-no-checkpoint-logic）| 🔴 全程阻塞 |
| `check_loc_budget.py` | violations=0；新增模組 ≤ 250 LOC | 🔴 全程阻塞 |
| `tests/equivalence/` | 13/13 fixture 綠 | 🔴 全程阻塞 |
| `alembic check` | 編號連續 + head 為 0012 | 🔴 W3+ 阻塞 |
| `tests/contract/test_alembic_chain_lock.py` | 既有 0001-0006 鎖死 | 🔴 W0+ 阻塞 |

### 10.2 G-gate

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| `tests/` | 全測 ≥ 1,491（隨 sprint 增長）| 🔴 阻塞 |
| `tests/contract/test_three_tier_schema.py` | AC3-1~AC3-5 全綠 | 🔴 W3+ |
| `tests/contract/test_embedder_contract.py` | AC4-1~AC4-5 全綠 | 🔴 W3+ |
| `tests/integration/test_pgvector_hnsw_recall.py` | recall@10 ≥ 0.95 + p95 < 50ms | 🔴 W3+ |
| `tests/integration/test_yaml_import.py` | 60+ YAML 雙向往返 100% | 🔴 W4+ |
| `tests/contract/test_config_resolver.py` | AC6-1~AC6-5 全綠 | 🔴 W5+ |
| `coverage` | ≥ 87%；新模組 ≥ 90% | 🔴 階段阻塞 |

### 10.3 Nightly

| Gate | 命令 / 規則 | 階段門檻 |
|------|-------------|--------|
| `mutation test` | OrchestrationCoordinator / ConfigResolver / ExecutionContext 三 SSOT ≥ 75% kill rate | 🟠 W2+ |
| `pg lock detector` | alembic upgrade 模擬 1M 列 backfill 不鎖寫入 ≥ 5 分鐘 | 🟠 W3+ |
| `dual_adapter health` | BGE-M3 + Minimax 備援切換 RTO < 60s | 🟠 W3+ |

---

## 11. 回退策略

繼承 SD_05 §7 + 新增 6 條（QA-C3 補 per-migration 回退劇本）：

| 觸發條件 | 立即執行 |
|---------|---------|
| alembic 0007 / 0009 / 0011 / 0012 任一失敗 | `alembic downgrade -1`，找 SD + DBA 雙簽才可重啟 |
| alembic 0008 失敗（新欄位已有查詢流量）| ⚠️ **不可 downgrade**：drop 新欄位 + 重建 + 全量重 embed；找 SD + SA + PM 三簽 |
| alembic 0010 step 2（backfill）≥ 50% 失敗 | ⚠️ **不可 downgrade**：前滾修補（修 backfill SQL + 重跑 NOT VALID + VALIDATE）；找 SD + DBA + PM 三簽 |
| alembic 0010 step 1 / step 3 失敗 | `alembic downgrade -1`（仍可回退）；找 SD + DBA 雙簽 |
| pgvector recall@10 < 0.90 | 凍結 W3，dual-read 模式自動降級走舊 vector(1536) index；HNSW 重建期間維持服務；找 SA + QA 雙簽 |
| pgvector recall@10 0.90-0.95（黃線告警）| 不阻塞服務 + 48h Wave 內修正期 + 補 HNSW ef_search 調參；自動 alert SA |
| dual_state drift > 5% 全欄不一致 | 強制切回 `yaml_only`；reconcile_report 寫入 audit_log；找 SD + PM 雙簽決定 root cause |
| W2 god-class 拆解 byte-level 1199 測試退化 | `git revert HEAD`，找 Architect + QA 雙簽才可重啟 |

---

## 12. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-17 | 三方審查共識初版：Architect / SA / SD 獨立審查 6 大議題 → Critical 12 項 + Wave 7 個 + 42 PD 估算；alembic 編號 0007-0012 鎖死；6 待拍板事項移交 PM |
| **v1.1** | 2026-05-17 | **QA 四方審議 APPROVED_WITH_CONDITIONS + 4 Critical 補強**：(QA-C1) §6.5 AC Matrix 25 條（每條含量測命令 + Pass 門檻 + 測試檔路徑）；(QA-C2) §6 alembic 表新增 contract test 對位（0007/0010/0011/0012 各 ≥ 6-10 case）；(QA-C3) §11 per-migration 回退劇本（point-of-no-return 標記 + 黃線告警 48h 修正期）；(QA-C4) §6 HNSW 重建期 fallback_query_path（dual-read + CircuitBreaker latency > 200ms 降級）；Major 補強：mutation test 升 🔴、drift/audit/staging 三表 retention policy、ExecutionContext Hypothesis ≥ 50 example、PII 過濾器前移至 W0；PM 警示 2 項（0010 backfill 單點失效 + PII 合規債務）|
| **v1.2** | 2026-05-17 | **PM 8 項拍板 APPROVED + G0 啟動日鎖定 2026-05-20**：(#6) sub-task 深度 ≤ 3；(#7) RBAC 三角色（admin/dev/viewer + policy_json 後擴）；(#8) MAX_ACTIVE_RUNS_PER_GOAL=5（W2 OrchestrationCoordinator 落地前埋 guard）；(#9) embed 最終一致 + embedding_status 三態 + retry 5 次告警；(#10) re-embed 背景 batch + 7 天 SLA；(#11) PII hybrid（W0 欄位分類 ENUM + W3 過濾器實作）；(#12) Coordinator/AutoResume 雙層保留 + Architect 出 ADR；(W-1) FK backfill 1M 列 staging dry-run 不可降級；(W-2) PII 連動 #11 hybrid；**PD 42 → 44 (+2)**：W0 +1 PII schema、W3 +1 FK staging dry-run；PM contingency 預留 3 PD（v2 backlog 延後）；G0 啟動條件全數解除（10/10）；2026-05-19 EOD 前 Tech Lead 提交 W0 task breakdown |

---

## 13. 簽核狀態

| 角色 | 狀態 | 備註 |
|------|------|------|
| Architect | ✅ 三方審查 APPROVED | 議題 1/2/3/5/6 主導；2026-05-17 |
| SA | ✅ 三方審查 APPROVED | 議題 3/4/5/6 AC 主導；§6.5 AC Matrix 已補；2026-05-17 |
| SD | ✅ 三方審查 APPROVED | 議題 0/4/5 主導 + alembic 編號一票否決（0007-0012）；2026-05-17 |
| QA | ✅ 四方審議 APPROVED_WITH_CONDITIONS | 4 Critical 已補強 → v1.1；測試 baseline 預估 W6 末 ≥ 1,711 passed；2026-05-17 |
| PM | ✅ 8 項拍板 APPROVED | 8/8 全數解除阻塞；PD 42 → 44；G0 啟動日鎖定 2026-05-20；2026-05-17 |

**G0 啟動 DoD**（PM 鎖定）：
- 2026-05-19 EOD 前：Tech Lead 提交 W0 task breakdown（含 PII schema 子任務）
- 2026-05-19 EOD 前：Architect 出 Layer 1.5/2 邊界 ADR
- 2026-05-20：G0 Kickoff
- W0 review 拉法務 / Security 共審 PII 欄位分類 ENUM

**QA 給 PM 的特別警示（強制 PM 確認）**：
1. **0010 FK backfill 三步是 SD_06 單點失效**：必須 W3-4 進入前先有 1M 列 staging DB 完整 dry-run + 回退演練紀錄，否則 G3 不放行
2. **PII / secret mask 規則必須前移至 W0**：drift_log / config_audit_log / yaml_import_diffs 三表會在 W3 上線即累積敏感資料，365 天 partition 內將有合規債務無法回收

---

**對應參考文件**：
- [SD_Improving_05.md](SD_Improving_05.md) v2.1 — SD_05 W6 G6 部分通過 + PM §1.3 例外簽核
- [SD05_Migration_Guide.md](../08_deployment/SD05_Migration_Guide.md) v1.1 §6 — SD_06 PD 估算 21 PD（W6 衍生）
- [risk_log.md](../05_development/risk_log.md) §11 — R-W6-1~5 + R-SD06-1~3
- [gate_audit.md](../05_development/gate_audit.md) — SD_05 G0~G6 簽核紀錄
