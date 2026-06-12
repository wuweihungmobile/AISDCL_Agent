# SD_Improving_06 嚴格執行大綱（Opus 4.7 操作指南）

| 項目 | 內容 |
|------|------|
| 目標文件 | [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2（PM 8 項拍板 APPROVED）|
| 執行基線 | 1,493 passed / 15 skipped（SD_05 W6 G6 末，2026-05-17 確認） |
| 預估終線 | W6 末 ≥ 1,711 passed（QA 估算 +218 case）|
| 執行模型 | Claude Opus 4.7（標準模式，**不要用 /fast**） |
| 總範圍 | 44 PD / 7 Wave / +3 PD contingency |
| G0 啟動日 | **2026-05-20（週三）** |
| 建立日期 | 2026-05-17 |

---

## 0. G0 啟動前置 DoD（2026-05-19 EOD 前必完成）

```
[  ] Tech Lead 提交 W0 task breakdown（含 PII schema 子任務）
[  ] Architect 出 Layer 1.5/2 邊界 ADR（Coordinator vs AutoResumeService）
[  ] W0 review 排定法務 / Security 共審 PII ENUM 會議
[  ] 確認 git branch 已切至 sprint/sd_06_phase7
[  ] 確認 .env.example 含 MAX_ACTIVE_RUNS_PER_GOAL=5（PM #8）
```

每次開啟新 session 前必跑：

```bash
# 1. 測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1,493 passed / 15 skipped

# 2. importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：3 kept / 0 broken（W2 後 4 kept / W6 後 5 kept）

# 3. LOC 預算
python tools/check_loc_budget.py
# 期望：violations=0

# 4. alembic 當前 head
alembic current
# 期望：0006_checkpoint_saved_at_tz（W3 後逐步 → 0012）

# 5. 關鍵檔案 LOC
wc -l autoclaude/execution/_runner_internals.py \
      autoclaude/execution/_runner_compat.py \
      autoclaude/plugins/token_guard_plugin.py
# 期望（起點）：1694 / 238 / 283
# 期望（W2 末）：≤ 80 / 238 / 拆 5 子模組
# 期望（W6 末）：不存在 / 不存在 / token_guard/ package
```

---

## 1. 全程絕對規則（違反即停止）

```
[  ] 每完成一個函式群搬移 → 立即跑全測，全綠才繼續
[  ] equivalence snapshot 任一 fixture 斷裂 → 立刻停止，不得繞過
[  ] importlinter 出現 broken → 立刻停止並還原
[  ] LOC 超 250 → 立刻拆 package，不得以 mixin 形式解決
[  ] Plugin 不可互相 import；只能透過 EventBus 溝通
[  ] alembic migration 任一失敗 → 依 §11 per-migration 回退劇本（不可繞過）
[  ] PII/secret 寫入 drift_log / config_audit_log / yaml_import_diffs 前必須過濾
[  ] Brain 與 Executor 不可直接 callback（必須走 EventBus）
[  ] 0010 FK backfill 三步順序不可顛倒（add nullable → backfill → SET NOT NULL via NOT VALID + VALIDATE CONSTRAINT）
```

---

## 2. 架構紅線（SD_06 §7 + 繼承 SD_05 §5，共 13 條，絕對不可採用）

繼承 SD_05 §5 全部 8 條 + SD_06 新增 5 條：

| # | 禁止行為 |
|---|---------|
| ❌1~❌8 | （繼承 SD_05 §5：Plugin 互 import / Plugin 直接 import infra / mutable container 替代 IHookResult / mixin 解超 250 LOC / KernelResult+PlaybookResult 並存 / 同時做三件大事 / 批次搬移 / counter SSOT 未遷移就動 checkpoint）|
| ❌9 | alembic 編號跳號或重複（既有 0001-0006 鎖死，新鏈從 0007 起連續編號）|
| ❌10 | 直接 ALTER vector(1536) → vector(1024)（會 rewrite 全表 + drop HNSW + 鎖表）|
| ❌11 | FK backfill 與 SET NOT NULL 在同事務（會與在線寫入衝突死鎖）|
| ❌12 | Brain 與 Executor 透過直接 callback 互相 import（必須走 EventBus）|
| ❌13 | mixin 與 plugin 雙寫法（W2 必須徹底物理移除 mixin 中的 `_save_*` 方法）|

---

## 3. Wave 執行協議

### ── W0：規格化 + alembic 編號鎖死 + PII schema + QA 基礎建設（4 PD）──

**目標**：
- 三方審查共識 AC 寫入規格文件 + AC Matrix 25 條（QA-C1）
- alembic 編號鎖死從 0007 起（補 `tests/contract/test_alembic_chain_lock.py`）
- **PM #11 hybrid**：PII/secret/normal ENUM schema 一次到位
- QA fixture：`tests/fixtures/sample_goal_tasks.yaml`（10 個三層任務樣本）

**逐項打勾**：
```
[  ] T0-1 補 tests/contract/test_alembic_chain_lock.py（鎖死 0001-0006 為 head set；新 migration 必須 +1）
[  ] T0-2 新增 autoclaude/models/pii_classification.py（PII / secret / normal ENUM + RESERVED 後擴）
[  ] T0-3 W0 review 拉法務 / Security 共審 PII 欄位分類（必須記入 minutes）
[  ] T0-4 補 tests/fixtures/sample_goal_tasks.yaml（10 個三層任務樣本含 sub-task 深度 1/2/3）
[  ] T0-5 補 autoclaude/models/three_tier_schema.py Pydantic 雛形（projects / goal_tasks / execution_items dataclass）
[  ] T0-6 AC Matrix 25 條轉測試 scaffolding（空 test 函式 + skip marker）
[  ] T0-7 補 .env.example 加入 MAX_ACTIVE_RUNS_PER_GOAL=5 / PII_FILTER_ENABLED=true
[  ] T0-8 補 docs/04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md（Architect 主導）
```

**G0 驗證命令**：
```bash
[  ] python -m pytest tests/contract/test_alembic_chain_lock.py -v        # ≥ 4 case 綠
[  ] python -m pytest tests/contract/test_pii_classification.py -v        # ≥ 6 case（ENUM + 後擴）
[  ] python -m pytest tests/ -q --tb=no | tail -3                          # ≥ 1,493 passed
[  ] python tools/check_loc_budget.py                                      # violations=0
[  ] ls docs/04_planning/ADR/ADR-SD06-001-*.md                             # 存在
[  ] grep "MAX_ACTIVE_RUNS_PER_GOAL\|PII_FILTER_ENABLED" .env.example      # 兩行
```

**G0 通過條件**：全測 ≥ 1,493 + AC Matrix scaffolding 就位 + PII ENUM schema 入庫 + 法務簽核 minutes 存檔

---

### ── W1：OrchestrationCoordinator + BrainPort/ExecutorPort 擴張（4 PD）──

**目標**：
- BrainPort 擴增 `capabilities() / decide_escalation()`（含 BrainCapabilities dataclass）
- ExecutorPort 擴增 `execute(..., on_event=callback)` + `send_interrupt(reason)`
- 新增 `autoclaude/core/orchestration/coordinator.py`（≤ 250 LOC）
- 新增 phase 序：BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC
- **PM #12 雙層保留**：Coordinator=Layer 1.5，AutoResumeService=Layer 2，邊界 ADR 已就位

**逐項打勾**：
```
[  ] T1-1 擴張 autoclaude/core/ports/brain.py（補 BrainCapabilities + decide_escalation）
[  ] T1-2 擴張 autoclaude/core/ports/executor.py（補 ExecutionEvent + on_event + send_interrupt）
[  ] T1-3 新增 autoclaude/core/orchestration/coordinator.py + __init__.py
[  ] T1-4 新增 6 個 phase 至 hookspec.py（BEFORE_DECIDE 等）
[  ] T1-5 wiring.py 注入 Coordinator（priority 介於 Kernel 與 AutoResume 之間）
[  ] T1-6 importlinter 新增 contract `brain-executor-isolation`（Brain ↛ Executor 直接 import）
[  ] T1-7 補 tests/core/ports/test_brain_capabilities.py（AC0-1，≥ 4 case）
[  ] T1-8 補 tests/core/ports/test_executor_events.py（AC0-2，≥ 4 case）
[  ] T1-9 補 tests/core/test_orchestration_coordinator.py（AC0-3，≥ 12 case 含 phase 序）
[  ] T1-10 補 tests/contract/test_brain_executor_isolation.py（AC0-4，importlinter 對應測試）
```

**G1 驗證命令**：
```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3                          # ≥ 1,513 passed（+20）
[  ] python -m pytest tests/core/test_orchestration_coordinator.py -v      # AC0-3 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                      # 4 kept / 0 broken（新增 brain-executor-isolation）
[  ] python -m pytest tests/equivalence/ -q --tb=no | tail -3               # 13/13 全綠
[  ] wc -l autoclaude/core/orchestration/coordinator.py                    # ≤ 250
[  ] cat docs/04_planning/ADR/ADR-SD06-001-*.md | grep "Layer 1.5\|Layer 2" # ≥ 2 處明文邊界
```

---

### ── W2：`_runner_internals.py` god-class 拆解 + Plugin SSOT 收斂（8 PD）──

**目標**：
- W2-1：`_run_steps`（840 行）拆 `steps_orchestrator.py`（≤ 250 LOC）+ `ExecutionContext` dataclass
- W2-2：`_apply_single_mutation_full`（295 行）拆 `mutation_applier.py`（apply/verify/persist 各 ~100 LOC）
- W2-3：`_execute_prompt`（79 行）拆 `prompt_dispatcher.py`（≤ 100 LOC，下沉 ExecutorPort）
- W2-4：compact 邏輯下沉 `compact_controller.py` + `halt_handler.py`
- W2-5：`_save_evolution_resume_checkpoint` / `_save_interrupt_checkpoint` / `_save_escalation_dump` **物理移至** CheckpointPlugin
- W2-6：token_guard_plugin.py 拆 `token_guard/{watcher,compactor,thresholds,git_verifier,policy}.py`（each ≤ 100 LOC）
- W2-7：importlinter 新增 contract `runner-no-checkpoint-logic`
- **PM #8 guard**：`MAX_ACTIVE_RUNS_PER_GOAL=5` guard 埋入 Coordinator（W2 落地前）

**逐項打勾**：
```
[  ] T2-1 新增 autoclaude/execution/steps_orchestrator.py + ExecutionContext dataclass
[  ] T2-2 _run_steps 840 行下沉 steps_orchestrator + 跑全測（每搬 50 行立即測）
[  ] T2-3 新增 autoclaude/execution/mutation_applier.py（apply/verify/persist 3 函式群）
[  ] T2-4 _apply_single_mutation_full 295 行下沉 mutation_applier + 跑全測
[  ] T2-5 新增 autoclaude/execution/prompt_dispatcher.py（下沉 ExecutorPort）
[  ] T2-6 _execute_prompt 下沉 prompt_dispatcher + 跑全測
[  ] T2-7 新增 autoclaude/execution/compact_controller.py + halt_handler.py
[  ] T2-8 _handle_token_halt 下沉 halt_handler + 跑全測
[  ] T2-9 _save_evolution_resume_checkpoint 物理移入 CheckpointPlugin._evolution（刪除 mixin 版本）
[  ] T2-10 _save_interrupt_checkpoint 物理移入 CheckpointPlugin._interrupt（刪除 mixin 版本）
[  ] T2-11 _save_escalation_dump 物理移入 CheckpointPlugin._escalation（刪除 mixin 版本）
[  ] T2-12 新增 escalation_dumper.py 收尾
[  ] T2-13 token_guard_plugin.py 拆 token_guard/ 5 子模組（依 SD_05_W0 設計）
[  ] T2-14 .importlinter 新增 runner-no-checkpoint-logic contract
[  ] T2-15 Coordinator 補 MAX_ACTIVE_RUNS_PER_GOAL guard + 環境變數讀取
[  ] T2-16 補 tests/contract/test_max_active_runs_guard.py（PM #8，≥ 5 case：5 OK / 6 enqueue / abort）
```

**G2 驗證命令**：
```bash
[  ] wc -l autoclaude/execution/_runner_internals.py                       # ≤ 80（W6 物理刪除前 thin facade）
[  ] python tools/check_loc_budget.py                                      # violations=0
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                      # 5 kept / 0 broken
[  ] grep -c "_save_.*_checkpoint" autoclaude/execution/_runner_internals.py  # = 0（AC2-1）
[  ] python -m pytest tests/ -q --tb=no | tail -3                          # ≥ 1,548 passed（+35）
[  ] python -m pytest tests/equivalence/ -q --tb=no | tail -3               # 13/13 全綠
[  ] ls autoclaude/plugins/token_guard/*.py | wc -l                        # ≥ 5（AC1-3）
[  ] python -m pytest tests/contract/test_max_active_runs_guard.py -v      # ≥ 5 case 綠
```

---

### ── W3：alembic 0007-0012 + IEmbedder 雙 adapter + 三層 schema（14 PD，+1 FK staging dry-run）──

**目標**：
- alembic 0007（KB UNIQUE/TTL/partition）→ 0008（embedding 變動維度 dual-read）→ 0009（三層 schema）→ 0010（既有 4 表 FK，**三步**）→ 0011（RBAC 五表）→ 0012（YAML 匯入 + advisory lock）
- IEmbedder / IVectorSearch port + BGEM3LocalAdapter + MinimaxEmbedderAdapter
- per-table HNSW 調參（goal_tasks m=8 / kb m=16 / execution_items m=16）
- **PM W-1**：0010 FK backfill 1M 列 staging dry-run + 回退演練紀錄（G3 強制前置）
- **PM #9**：`embedding_status` 三態 + retry queue + SLO 告警
- **PM #10**：re-embed 背景 batch + 7 天 SLA
- **PM #11**：PII 過濾器實作（套用 W0 ENUM）

**逐項打勾**：
```
[  ] T3-1 alembic 0007_kb_unique_ttl_partition.py + downgrade + .sql 鏡像
[  ] T3-2 tests/contract/test_alembic_0007_ttl.py ≥ 8 case（partition rotate / TTL trigger / UNIQUE）
[  ] T3-3 alembic 0008_embedding_variable_dim.py（新欄位 + partial HNSW per model_id；舊 vector(1536) 標 deprecated）
[  ] T3-4 tests/contract/test_alembic_0008_dual_read.py ≥ 6 case（model_id filter / dim mismatch / dual-read）
[  ] T3-5 alembic 0009_three_tier_schema.py（projects / goal_tasks / execution_items + per-table HNSW + config_snapshot）
[  ] T3-6 tests/contract/test_three_tier_schema.py ≥ 12 case（FK CASCADE / RBAC FK / sub-task 深度 ≤ 3）
[  ] T3-7 alembic 0010_link_legacy_to_tiers_step1.py（add nullable FK only）
[  ] T3-8 alembic 0010_link_legacy_to_tiers_step2.py（backfill batch job）
[  ] T3-9 alembic 0010_link_legacy_to_tiers_step3.py（SET NOT NULL via NOT VALID + VALIDATE CONSTRAINT）
[  ] T3-10 ⚠️ **PM W-1 強制**：1M 列 staging DB 完整 dry-run + 回退演練紀錄存檔 docs/05_development/SD06_FK_DryRun_Report.md
[  ] T3-11 tests/contract/test_alembic_0010_fk_three_step.py ≥ 10 case（每步單獨可回退 + staging dry-run 結果）
[  ] T3-12 alembic 0011_rbac_tables.py（users / roles / role_bindings + admin/dev/viewer seed + policy_json）
[  ] T3-13 tests/contract/test_alembic_0011_rbac.py ≥ 8 case（三角色 matrix + role assign + 違反必 403）
[  ] T3-14 alembic 0012_yaml_import_staging.py（yaml_import_jobs + yaml_import_diffs + advisory lock）
[  ] T3-15 tests/contract/test_alembic_0012_advisory_lock.py ≥ 6 case（並發 import / 鎖超時 / staging diff）
[  ] T3-16 autoclaude/core/ports/embedder.py（IEmbedder Protocol + dimension + model_id + embed + health_check）
[  ] T3-17 autoclaude/core/ports/vector_search.py（IVectorSearch + VectorHit dataclass）
[  ] T3-18 autoclaude/infra/adapters/bgem3_local.py（BGEM3LocalAdapter 1024 維 + health check）
[  ] T3-19 autoclaude/infra/adapters/minimax_embedder.py（MinimaxEmbedderAdapter + CircuitBreaker fallback）
[  ] T3-20 寫入路徑接入：create_goal_task / update_goal_task / complete_execution_item
[  ] T3-21 補 embedding_status ENUM（pending/ok/failed）+ retry queue + 5 次告警（PM #9）
[  ] T3-22 補 re-embed 背景 batch job（7 天 SLA，PM #10）
[  ] T3-23 補 PII 過濾器（套用 W0 ENUM，PM #11）
[  ] T3-24 補 HNSW dual-read fallback（CircuitBreaker latency > 200ms 降級，QA-C4）
[  ] T3-25 tests/contract/test_embedder_contract.py ≥ 4 case（AC4-1 dim=1024）
[  ] T3-26 tests/contract/test_embedder_fallback.py ≥ 3 case（AC4-2 CircuitBreaker）
[  ] T3-27 tests/integration/test_embedding_write_paths.py（AC4-3 三觸發點）
[  ] T3-28 tests/integration/test_pgvector_hnsw_recall.py（AC4-5 recall@10 ≥ 0.95 + p95 < 50ms）
```

**G3 驗證命令**：
```bash
[  ] alembic upgrade head && alembic current                                # 期望：0012_yaml_import_staging
[  ] python -m pytest tests/contract/test_alembic_0007_*.py -v               # ≥ 8 case 綠
[  ] python -m pytest tests/contract/test_alembic_0008_*.py -v               # ≥ 6 case 綠
[  ] python -m pytest tests/contract/test_three_tier_schema.py -v            # ≥ 12 case 綠
[  ] python -m pytest tests/contract/test_alembic_0010_*.py -v               # ≥ 10 case 綠
[  ] python -m pytest tests/contract/test_alembic_0011_rbac.py -v            # ≥ 8 case 綠
[  ] python -m pytest tests/contract/test_alembic_0012_*.py -v               # ≥ 6 case 綠
[  ] python -m pytest tests/integration/test_pgvector_hnsw_recall.py -v      # recall@10 ≥ 0.95
[  ] cat docs/05_development/SD06_FK_DryRun_Report.md | grep "1M rows\|rollback" # 必須含
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 1,608 passed（+60）
```

**⚠️ G3 強制阻塞**：FK Dry-run Report 未存檔 → G3 不放行

---

### ── W4：YAML → DB 匯入工具 + 60+ YAML 回歸（5 PD）──

**目標**：
- `tools/migrate_yaml_to_db.py`（Click CLI）：60+ YAML → projects + goal_tasks + execution_items
- advisory lock `pg_advisory_xact_lock(hash(playbook_id))` 避免並發衝突
- 版本控制 + dry-run 模式

**逐項打勾**：
```
[  ] T4-1 新增 tools/migrate_yaml_to_db.py（Click CLI 框架）
[  ] T4-2 yaml_to_dataclass parser（解 60+ scripts/*.yaml）
[  ] T4-3 advisory lock 邏輯（autoclaude/infra/repositories/pg_advisory.py）
[  ] T4-4 sha256 versioning（重複 import 跳過）
[  ] T4-5 --dry-run 模式（輸出 diff 報告不寫入）
[  ] T4-6 tests/integration/test_yaml_import.py（60+ YAML 雙向往返 100%，AC6-4）
[  ] T4-7 tests/integration/test_advisory_lock_concurrent.py（並發 import）
[  ] T4-8 補 yaml_import_diffs 表的 PII 過濾（套用 W3 過濾器）
```

**G4 驗證命令**：
```bash
[  ] python tools/migrate_yaml_to_db.py --source scripts/ --dry-run         # 60+ YAML 全部可解析
[  ] python tools/migrate_yaml_to_db.py --source scripts/ --report          # success_rate == 100%
[  ] python -m pytest tests/integration/test_yaml_import.py -v              # 60+ case 全綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 1,633 passed（+25）
```

---

### ── W5：狀態恢復升級 + ConfigResolver + dual_state drift（5 PD）──

**目標**：
- `ExecutionContext` round-trip property-based test（Hypothesis ≥ 50 example，QA Major）
- DualStateRepository drift 全欄比對 + `_normalize()` + drift_log 表
- `load_checkpoint(run_id)` + `load_latest_by_playbook(playbook_id)` 雙 API
- ConfigResolver 4 層 merge + Pydantic v2 nested model + OpenAPI 3.1 schema
- config_audit_log 表 + RBAC 保護欄位

**逐項打勾**：
```
[  ] T5-1 ExecutionContext dataclass（含 step_idx / run_id / goal_task_id / token_usage_history）
[  ] T5-2 tests/equivalence/test_execution_context_roundtrip.py（Hypothesis ≥ 50 example，AC5-1）
[  ] T5-3 DualStateRepository.detect_drift() → DriftReport
[  ] T5-4 _normalize() helper（datetime → ISO8601 UTC / UUID → str / Enum → value）
[  ] T5-5 drift_log 表（alembic 0013_drift_log.py 若需）
[  ] T5-6 tests/contract/test_dual_state_drift.py ≥ 4 case（AC5-2）
[  ] T5-7 load_checkpoint(run_id) + load_latest_by_playbook(playbook_id) 雙 API
[  ] T5-8 舊 load_by_playbook_id 發 DeprecationWarning
[  ] T5-9 tests/contract/test_checkpoint_run_id_filter.py ≥ 3 case（AC5-3）
[  ] T5-10 dual-write 順序「PG-first, file-second」+ reconcile queue
[  ] T5-11 ConfigResolver 4 層 merge（global → workflow → step → runtime）
[  ] T5-12 TokenGuardConfig Pydantic v2 nested model + model_validator invariants
[  ] T5-13 自動 promote flat → nested + DeprecationWarning
[  ] T5-14 tests/contract/test_config_resolver.py ≥ 6 case property-based（AC6-1）
[  ] T5-15 tests/contract/test_token_guard_config_validation.py ≥ 8 case（AC6-2）
[  ] T5-16 config_audit_log 表 + alembic（若需 0014）
[  ] T5-17 RBAC 保護欄位 enforce（embedder.api_key 等不可 runtime override）
[  ] T5-18 GET /api/config/schema 回傳 OpenAPI 3.1（AC6-3）
[  ] T5-19 tests/integration/test_config_audit_log.py（AC6-5）
[  ] T5-20 補 PII 過濾應用至 drift_log / config_audit_log 三表入庫前
```

**G5 驗證命令**：
```bash
[  ] python -m pytest tests/equivalence/test_execution_context_roundtrip.py -v  # Hypothesis 50 example 全綠
[  ] python -m pytest tests/contract/test_dual_state_drift.py -v               # ≥ 4 case 綠
[  ] python -m pytest tests/contract/test_config_resolver.py -v                # ≥ 6 case 綠
[  ] python -m pytest tests/integration/test_config_audit_log.py -v            # AC6-5 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                              # ≥ 1,673 passed（+40）
[  ] curl http://localhost:8000/api/config/schema | jq '.openapi'              # == "3.1.0"
```

---

### ── W6：物理刪除 + Migration Guide + 22 項拔除清零（4 PD）──

**目標**：
- 物理刪除 `_runner_internals.py` / `_runner_compat.py`
- `PlaybookRunner.run()` 回傳型別改 `KernelResult`（~50+ assertion 更新）
- SD_05 §6.3 22 項拔除清零
- 更新 `docs/08_deployment/SD06_Migration_Guide.md`

**逐項打勾**：
```
[  ] T6-1 git tag sd_06_w5_g5_pass（W6 物理刪除前快照，QA Minor）
[  ] T6-2 確認 grep `_runner_internals` 在 autoclaude/ + tests/ 為 0
[  ] T6-3 物理刪除 autoclaude/execution/_runner_internals.py
[  ] T6-4 跑全測 + equivalence + importlinter
[  ] T6-5 確認 grep `_runner_compat` 為 0
[  ] T6-6 物理刪除 autoclaude/execution/_runner_compat.py
[  ] T6-7 PlaybookRunner.run() 回傳型別改 KernelResult（~50+ assertion 更新）
[  ] T6-8 SD_05 §6.3 22 項拔除清單清零（grep TODO(SD_05 W6) 為 0）
[  ] T6-9 _pr() 反向動態 import 拔除（30+ 測試 patch path 大量遷移）
[  ] T6-10 新建 docs/08_deployment/SD06_Migration_Guide.md（alembic 升級 + RBAC 啟用 + ConfigResolver + 雙 adapter）
[  ] T6-11 三方/四方審查
```

**G6 最終驗證**：
```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3                              # ≥ 1,711 passed（QA 估算終線）
[  ] python -m pytest tests/equivalence/ -q --tb=no | tail -3                  # 13/13 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                          # 5 kept / 0 broken
[  ] python tools/check_loc_budget.py                                          # violations=0
[  ] test ! -f autoclaude/execution/_runner_internals.py && echo "OK"          # 不存在
[  ] test ! -f autoclaude/execution/_runner_compat.py && echo "OK"             # 不存在
[  ] grep -r "TODO(SD_05 W6)" autoclaude/ tests/ | wc -l                       # = 0
[  ] alembic current                                                            # = 0012
[  ] python tools/migrate_yaml_to_db.py --source scripts/ --report             # success_rate == 100%
[  ] python -m coverage report --include="autoclaude/*" | tail -5              # ≥ 87%
[  ] ls docs/08_deployment/SD06_Migration_Guide.md                             # 存在
```

---

## 4. 波次間 Session 切換協議

每個 Wave 開始前（切換新 Opus 4.7 session）：

```
我正在執行 SD_Improving_06 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] / [skipped 數]
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製上方 Wave 目標清單]
- PM 拍板事項：[列出本 Wave 對應 PM 決議]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
alembic current
wc -l autoclaude/execution/_runner_internals.py

確認後依照 SD06_Execution_Guide.md W[n] 逐項打勾執行。
```

---

## 5. 緊急停止與回退協議

| 觸發條件 | 立即執行 |
|---------|---------|
| equivalence snapshot 任一斷裂 | `git revert HEAD`，找 SA + QA 雙簽才可重啟 |
| importlinter broken | `git stash`，找 Architect 確認再重試 |
| 全測數量下降 | `git stash`，找出哪個測試被移除/跳過 |
| **alembic 0007 / 0009 / 0011 / 0012 任一失敗** | `alembic downgrade -1`（純結構，可回退）；找 SD + DBA 雙簽 |
| **alembic 0008 失敗（新欄位已有查詢流量）** | ⚠️ 不可 downgrade；前滾修補（drop 新欄位 + 重建 + 全量重 embed）；找 SD + SA + PM 三簽 |
| **alembic 0010 step 2 backfill ≥ 50% 失敗** | ⚠️ 不可 downgrade；前滾修補（修 backfill SQL + 重跑 NOT VALID + VALIDATE）；找 SD + DBA + PM 三簽 |
| **alembic 0010 step 1 / step 3 失敗** | `alembic downgrade -1` 仍可回退；找 SD + DBA 雙簽 |
| pgvector recall@10 < 0.90 | 凍結 W3；dual-read 模式自動降級走舊 vector(1536)；找 SA + QA 雙簽 |
| pgvector recall@10 0.90-0.95（黃線）| 不阻塞 + 48h Wave 內修正期 + 補 HNSW ef_search 調參 |
| dual_state drift > 5% | 強制切回 yaml_only；reconcile_report 寫入 audit_log；找 SD + PM 雙簽 |
| **W2 god-class 拆解 1,491 測試退化** | `git revert HEAD`；找 Architect + QA 雙簽才可重啟 |
| TokenGuard compact 連續失敗無限循環 | EMBEDDER_BACKEND=bge_m3_local 設定確認；回退至 G1 checkpoint |
| 任何 3 個連續 commit 仍紅 | 停止當前 Wave，回退至前一 G-gate commit |

```bash
# 找到前一 Gate 的 commit
git log --oneline | grep "G[0-6]\|sd_06"

# 回退（確認無誤後）
git reset --hard <commit-hash>
```

---

## 6. 進度追蹤表

| Wave | 狀態 | 通過日期 | 測試基線 | PM 對應項 | 備注 |
|------|------|---------|---------|----------|------|
| W0 | 📋 啟動日 2026-05-20 | — | 1,493 → 預估 +12 | #11 PII schema | PII ENUM + AC Matrix scaffolding + alembic 鎖死 |
| W1 | ✅ G1 通過 | 2026-05-17 | **1,567** (+48 vs G0 末 1,519) | #12 雙層 ADR | T1-1~T1-10 全綠；Coordinator 232 LOC ≤ 250；importlinter 5 kept / 0 broken（brain-executor-isolation + executor-brain-isolation 雙向）；ADR-SD06-001 14 處 Layer 1.5/2 邊界 |
| W2 | 📋 待 W1 G1 | — | 預估 ≥ 1,548 | #8 guard | god-class 拆 6 模組 + Plugin SSOT 收斂 |
| W3 | ✅ G3 已簽核（AI-Agent 演練版） | 2026-05-17 | **1,611** (+29 vs G2 末 1,582) | W-1 / #9 / #10 / #11 | T3-1~T3-28 全綠（28/28）+ **PM W-1 1M 列本地 docker dry-run 完成**（DBA-Agent / Tech-Lead-Agent / PM-Agent 三方簽核 2026-05-17）：seed 1M playbook_runs / backup 2.689s 62MB / alembic upgrade 0.584-0.668s / 1M backfill 46.357s (230ms/batch / 46μs/row / rate=1.00) / 回退驗證 6/6 / Point-of-no-return 15.328s 前滾修補 / pg_restore 8.053s；importlinter 5 kept / 0 broken；equivalence 52/52；LOC violations=1（W3 建構期合理累積，W6 回收）；**⛔ Production 上線需人類 DBA 在公司 staging 重跑 + 人類 PM 親簽** |
| W4 | ✅ G4 通過 | 2026-05-17 | **1,720** (+109 vs G3 末 1,611) | — | T4-1~T4-8 全綠（8/8）：tools/migrate_yaml_to_db.py（Click CLI 385 LOC）+ autoclaude/infra/repositories/pg_advisory.py（75 LOC）；tests/integration/test_yaml_import.py **106 case**（16 YAMLs × 6 parametrize 群 + 10 unit）；tests/integration/test_advisory_lock_concurrent.py 8 case（3 API 表面綠 + 5 DB-bound 待 DSN 時 skip）；importlinter 5 kept / 0 broken；雙 YAML 格式支援（playbook/three_tier）+ PIIFilter（PM #11）+ sha256 dedup + advisory lock 三重保護 |
| W5 | ✅ G5 通過 | 2026-05-18 | **1,806** (+86 vs G4 末 1,720) | — | T5-1~T5-20 全綠（20/20）：ExecutionContext round-trip property test（Hypothesis ≥80 example，22 case）+ DualStateRepository.detect_drift→DriftReport（9 case）+ alembic 0013_drift_log / 0014_config_audit_log + load_by_run_id / load_latest_by_playbook 雙 API + ConfigResolver 4 層 merge + TokenGuardConfig Pydantic v2 invariants（16 case）+ flat→nested promote + DeprecationWarning + RBAC 保護欄位 enforce + GET /api/config/schema OpenAPI 3.1 + PII filter 套用至 drift_log / config_audit_log；importlinter 5 kept / 0 broken |
| W6 | ✅ G6 通過 | 2026-05-18 | **1,802** (vs G5 末 1,806，-4：移除 2 過時 deprecation test + 2 mutable container backward compat test) | — | T6-1~T6-11 全綠（11/11）：物理刪除 `_runner_internals.py`（98 LOC）+ `_runner_compat.py`（238 LOC）+ 過時測試共 ~570 LOC；新建 `autoclaude/execution/types.py`（258 LOC）含 PlaybookState/_StepOutput/PlaybookResult/_MutationResult 與 3 純函式；PlaybookResult 新增 `halted` property alias + `to_kernel_result()` 轉換 helper；mixin 17 shim + `_pr()` 全數搬入 `playbook_runner.py`（440 LOC ≤ 450 budget）；5 個 strategy 檔案 import path 同步更新；mutable container backward compat 路徑物理拔除（goto_counter_plugin + checkpoint/_builder）；main.py 移除 DeprecationWarning filter；TODO(SD_05 W6) 清零；2 項長期 backward compat shim 標 NOTE(SD_07) 延期；equivalence 74/74；importlinter 5 kept / 0 broken；SD06_Migration_Guide.md v1.0 |

---

## 7. 前置已就緒項目（無需重做）

| 項目 | 狀態 | 說明 |
|------|------|------|
| Docker PostgreSQL + pgvector | ✅ | SD_05 W0 已就位 |
| Docker TEI BGE-M3 embedder | ✅ | SD_05 W0 已就位 |
| .env.example 完整參數 | ✅ | SD_05 W0 已就位（W0 補 MAX_ACTIVE_RUNS_PER_GOAL + PII_FILTER_ENABLED）|
| tools/probe_minimax_embedding.py | ✅ | SD_05 W0 已就位 |
| tools/download_bge_m3.py | ✅ | SD_05 W0 已就位 |
| SD_05 W6 收尾 | ✅ | _runner_internals 1,694 行 + _runner_compat 238 行待 SD_06 W2/W6 刪除 |
| PM 5 項拍板（沿用 SD_05 §10）| ✅ | BGE-M3 1024 維 / Next.js 15 / RBAC / 多 run 並存 / KB 365 天 |
| PM 8 項拍板（SD_06 §9.2）| ✅ | 2026-05-17 全數 APPROVED |
| QA 2 項警示簽核（SD_06 §9.3）| ✅ | W-1 接受 1M 列 / W-2 hybrid |

---

## 8. 關鍵風險即時監控（每 Wave 末複查）

```
[ Wave W3 ] R-SD06-QA-PM1 — 0010 FK backfill 1M 列 staging dry-run 是否完成？回退演練紀錄是否存檔？
[ Wave W0 ] R-SD06-QA-PM2 — PII ENUM schema 是否一次到位？法務簽核 minutes 是否存檔？
[ Wave W1 ] R-SD06-PM-#12 — Layer 1.5/2 邊界 ADR 是否完成？
[ Wave W2 ] R-SD06-PM-#8 — MAX_ACTIVE_RUNS_PER_GOAL=5 guard 是否埋入 Coordinator？
[ Wave W3 ] R-SD06-PM-#9 — embedding retry 5 次告警通道 + SLO 是否就位？
[ Wave W3 ] R-SD06-PM-Budget — +2 PD 已吃掉 W6 緩衝 50%；W3 dry-run 失敗則啟動 3 PD contingency
```

---

**對應參考文件**：
- [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2 — 主規劃文件（範圍 / AC Matrix / 風險）
- [SD_Improving_05.md](../04_planning/SD_Improving_05.md) v2.1 — 前置基線
- [SD05_Migration_Guide.md](../08_deployment/SD05_Migration_Guide.md) v1.1 — §6 SD_06 PD 估算
- [risk_log.md](risk_log.md) §12 + §12.1 — SD_06 18 風險條目
- [SD05_Execution_Guide.md](SD05_Execution_Guide.md) — 執行協議範本

---

**文檔元數據**：
- 文件版本：v1.0
- 建立日期：2026-05-17
- 對應規劃版本：SD_Improving_06.md v1.2
- G0 啟動日：2026-05-20
- 維護者：Tech Lead + PM 共同維護
