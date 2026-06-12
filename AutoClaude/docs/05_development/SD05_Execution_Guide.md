# SD_Improving_05 執行協議（Opus 4.7 操作指南）

| 項目 | 內容 |
|------|------|
| 目標文件 | [SD_Improving_05.md](../../docs/04_planning/SD_Improving_05.md) v1.3 |
| 執行基線 | 1,199 passed / 10 skipped（2026-05-16 確認） |
| 執行模型 | Claude Opus 4.7（標準模式，**不要用 /fast**；`/fast` 僅 Opus 4.6 可用且為降速版） |
| 建立日期 | 2026-05-16 |

---

## 0. 前置確認（每次開啟新 session 前必跑）

```bash
# 1. 確認測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：1199 passed, 10 skipped（或更高）

# 2. 確認 importlinter
python -m importlinter --config .importlinter
# 期望：3 kept / 0 broken

# 3. 確認 LOC 預算
python tools/check_loc_budget.py
# 期望：全部 ≤ 250（_runner_internals.py 例外，尚未下沉）

# 4. 確認 Docker 服務
docker compose ps
# 期望：autoclaude_pg (healthy), autoclaude_embedder (healthy)

# 5. 確認關鍵檔案 LOC
wc -l autoclaude/core/hookspec.py \
       autoclaude/execution/_runner_internals.py \
       autoclaude/execution/_runner_compat.py \
       autoclaude/execution/playbook_runner.py
# 期望：196 / 1766 / 238 / 282（G6 後 _runner_internals 和 _runner_compat 會消失）
```

---

## 1. 全程絕對規則（違反即停止）

1. **每完成一個函式群搬移 → 立即跑全測，全綠才繼續**
2. **equivalence snapshot 任一 fixture 斷裂 → 立刻停止，不得繞過**
3. **importlinter 出現 broken → 立刻停止並還原**
4. **LOC 超 250 → 立刻拆 package，不得以 mixin 形式解決**
5. **Plugin 不可互相 import；只能透過 EventBus 溝通**
6. **counter SSOT 遷移（W1 Step-1）必須在 CheckpointPlugin save 邏輯（W1 Step-2）之前完成**

---

## 2. 架構紅線（§5 全文，禁止採用）

| # | 禁止行為 |
|---|---------|
| ❌1 | Plugin 之間直接 import |
| ❌2 | Plugin 直接 import infra 層 |
| ❌3 | 用 `payload[key] = mutable_dict` 替代 IHookResult |
| ❌4 | LOC 超 250 時用 mixin 解決（必須拆 package） |
| ❌5 | `KernelResult` 與 `PlaybookResult` 並存到 SD_05 結束 |
| ❌6 | SD_05 同時做 mixin 下沉 + PG 三層 + 向量寫入 |
| ❌7 | 批次搬移多個 phase 後才跑測試（必須逐 phase 跑） |
| ❌8 | counter SSOT 未遷移就動 CheckpointPlugin save 邏輯 |

---

## 3. Wave 執行協議

### ── W0：規格化 + Builder 重構 + QA 基礎建設（10 PD）──

**目標**：
- Critical-1 修補（hookspec 擴張）→ W1 才不會 fail-fast
- wiring.py SSOT 漂移修補（M-3）
- PG 4 表 schema lock test（QA Q-C3）
- EventBus trace_id（QA Q-M1）
- 提供 `tests/plugins/_template.py` fixture 模板

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W0。

當前基線：1,199 passed / 10 skipped。

W0 任務清單（必須全部完成才過 G0）：

【T0-1】hookspec 擴張（Critical-1 優先）
  在 autoclaude/core/hookspec.py 補充：
  (a) 6 個新 IHookResult：
      - ScheduleResumeResult(scheduled_at: str)
      - CounterSnapshotResult(snapshot: dict)
      - PersistenceResult(path: str, succeeded: bool)
      - MutationApplyResult(clear_goal_summary: bool)
      - GoalValidationResult(achieved: bool, reasoning: str)
      - EscalationDumpedResult(dump_path: str)
  (b) 8 個新 KernelPhase（加入 KernelPhase enum）：
      PRE_COMPACT, POST_COMPACT, ON_PERSISTENCE_REQUEST,
      ON_ESCALATION_DUMP_REQUEST, ON_EVOLUTION_PROPOSE,
      ON_EVOLUTION_APPLY, ON_AUTO_RESUME_WAKE, ON_PROMPT_PREPARED
  (c) 擴 PHASE_RESULT_CONTRACT 補 7 條：
      ON_INTERRUPT, ON_EVOLUTION, ON_FAILURE, ON_SUCCESS,
      ON_STATE_TRANSITION, ON_CHECKPOINT_RESTORE, ON_CHECKPOINT_SAVE_REQUEST
  (d) 擴 MergedResult 加欄位：
      scheduled_resume_at, evolved_playbook_path, evolution_metadata, counter_diff
  每完成一小步立即跑全測（python -m pytest tests/ -q --tb=no | tail -3）

【T0-2】wiring.py SSOT 重構（M-3）
  抽 _build_plugin_set() + _register_in_order() 解決兩條組裝路徑漂移
  每完成立即跑全測

【T0-3】PG 4 表 schema lock test
  在 tests/contract/test_pg_existing_schema_lock.py 補：
  DDL snapshot + CRUD 行為快照（4 表：playbook_runs / checkpoints / knowledge_entries / playbook_versions）

【T0-4】EventBus trace_id（QA Q-M1）
  EventBus dispatch 加 trace_id，確保跨 phase 可追蹤

【T0-5】測試 fixture 模板
  建立 tests/plugins/_template.py（標準 Plugin 測試模板）
  包含 FakePorts v2 + fake EventBus + KernelState 初始化範例

【T0-6】子模組命名設計確認
  token_guard/ package 規劃（watcher.py / compactor.py / thresholds.py / git_verifier.py，各 ≤ 80 行）
  ✅ 只需命名設計文件（不實作，W2 才實作）

架構紅線：見執行指南 §2
完成後執行 G0 驗證命令（見下方）
```

**G0 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠

python -m importlinter --config .importlinter
# 期望：3 kept / 0 broken

python -m pytest tests/contract/test_pg_existing_schema_lock.py -v 2>&1 | tail -10
# 期望：全綠（新測試）
```

**G0 通過條件**：全測 ≥ 1199 + equivalence 13/13 + importlinter 0 broken + PG schema lock test 綠

---

### ── W1：Counter SSOT 遷移（6 PD）──

**目標**：
- 5 個 local counter 完全搬至 GotoCounterPlugin（Step-1）
- CheckpointPlugin 透過 ON_CHECKPOINT_SAVE_REQUEST 取 snapshot（Step-2）
- **Step-1 必須在 Step-2 之前完成**

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W1。

G0 已通過，基線：≥ 1199 passed。

⚠️ 強制執行順序（Critical-3）：
  Step-1 完成並全測綠 → 才能開始 Step-2
  違反順序將破壞 Gap-042 / Gap-048 跨 session 防護

【W1-Step-1】Counter SSOT 遷移至 GotoCounterPlugin
  目標：autoclaude/execution/_runner_internals.py 中的 5 個 local counter：
    _goto_counter / _inject_before_counter / _skip_to_counter /
    _step_evolution_counter / _compact_failure_count（或類似命名）
  操作：完全搬至 GotoCounterPlugin，讓 Plugin 成為唯一 SSOT
  驗證：python -m pytest tests/ -q --tb=no | tail -3（必須 ≥ 1199 passed）
  ✅ Step-1 全測綠後才能繼續

【W1-Step-2】CheckpointPlugin ON_CHECKPOINT_SAVE_REQUEST
  GotoCounterPlugin 訂閱 ON_CHECKPOINT_SAVE_REQUEST phase
  發出 CounterSnapshotResult（W0 已定義）
  CheckpointPlugin 接收並寫入持久化
  驗證：python -m pytest tests/ -q --tb=no | tail -3

【W1-新測試】補 tests/contract/test_phase_migration_flag.py
  feature flag T18_P2_PHASES_MIGRATED 啟用/停用 × 8 phase = 16 case
  coverage ≥ 80%

架構紅線：見執行指南 §2（特別注意 ❌8：Step 順序）
完成後執行 G1 驗證命令
```

**G1 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed（不可下降）

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠

python -m pytest tests/contract/test_phase_migration_flag.py -v 2>&1 | tail -10
# 期望：16 case 全綠

python -m coverage report --include="autoclaude/*" | tail -5
# 期望：≥ 80%

# 確認 4 個 local counter 物理上已搬至 plugin（W1 三方審查 SD-m1 命令更新）
# 注意：4 個 local 變數仍存在但為 plugin internal dict 的 alias（SSOT），
# 此 grep 偵測「獨立初始化為空 dict 或 dict() 的舊模式」是否殘留。
grep -nE "^\s*_goto_counter\s*=\s*(\{\}|dict\(\))|^\s*_inject_before_counter\s*=\s*(\{\}|dict\(\))|^\s*_skip_to_counter\s*=\s*(\{\}|dict\(\))|^\s*_step_evolution_counter\s*=\s*(\{\}|dict\(\))" autoclaude/execution/_runner_internals.py
# 期望：0 行（舊獨立 dict 初始化模式不應再存在）

# 驗證 plugin SSOT alias 模式已就位（4 行）
grep -nE "self\._goto_counter_plugin\.(goto_counter|inject_before_counter|skip_to_counter|step_evolution_counter)" autoclaude/execution/_runner_internals.py | wc -l
# 期望：≥ 4（4 個 alias 至少各一次）

# 第 5 個 _consecutive_compact_failures 仍在 PlaybookRunner.__init__，屬 W2 範圍（M-2）
grep -n "_consecutive_compact_failures" autoclaude/execution/playbook_runner.py
# 期望：1~2 行（W2 才搬至 TokenGuardPlugin）
```

---

### ── W2：TokenGuardPlugin 擴充（7 PD）──

**目標**：
- 吸收 5 個方法群（token watch / compact / threshold / git diff）
- 拆 token_guard/ package（超 250 LOC 必拆）
- 補 per-step override（M-7）
- 解除雙寫風險（M-2：`_compact_failure_count` vs `_consecutive_compact_failures`）

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W2。

G1 已通過，基線：≥ 1199 passed。

【W2-1】TokenGuardPlugin 吸收方法群（逐一搬移，每搬一個立即全測）
  從 autoclaude/execution/_runner_internals.py 搬移：
  (a) _execute_prompt 中的 token watch 邏輯
  (b) _should_compact_now
  (c) _send_compact
  (d) _get_dynamic_compact_threshold
  (e) _verify_correction_applied（git diff 部分）

  ⚠️ 每搬一個立即跑：python -m pytest tests/ -q --tb=no | tail -3
  ⚠️ 必須逐步搬移，不可批次

【W2-2】拆 token_guard/ package（若超 250 LOC）
  按 W0 命名設計：
  autoclaude/plugins/token_guard/__init__.py
  autoclaude/plugins/token_guard/watcher.py（≤ 80 行）
  autoclaude/plugins/token_guard/compactor.py（≤ 80 行）
  autoclaude/plugins/token_guard/thresholds.py（≤ 80 行）
  autoclaude/plugins/token_guard/git_verifier.py（≤ 80 行）

【W2-3】拔除雙寫（M-2）
  移除 _runner_internals.py 中 inline compact 路徑
  確保 record_compact_failure() 由 TokenGuardPlugin 唯一呼叫

【W2-4】per-step token_guard override（M-7）
  PlaybookTask 加 token_guard: Optional[TokenGuardConfig] 欄位
  W1 setup 可設較高門檻，W3 codegen 可設較低門檻

【W2-新測試】
  補 tests/contract/test_playbook_yaml_backward_compat.py
  60+ 現有 YAML 可載入 + per-step token_guard 優先序 AC
  coverage ≥ 82%

架構紅線：見執行指南 §2
完成後執行 G2 驗證命令
```

**G2 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠

python -m pytest tests/contract/test_playbook_yaml_backward_compat.py -v 2>&1 | tail -5
# 期望：全綠

python tools/check_loc_budget.py
# 期望：token_guard/ 各 module ≤ 250

python -m coverage report --include="autoclaude/*" | tail -5
# 期望：≥ 82%

# 確認雙寫已消除（SD_05 W2 三方審查 SD-C1 命令更新）
# 嚴格只偵測「寫入路徑」（+= 或 =）；註解與 logger 讀取允許保留（W6 一併拔除）
grep -nE "self\._consecutive_compact_failures\s*[+=]|^\s+self\._compact_failure_count\s*[+=]" autoclaude/execution/_runner_internals.py
# 期望：0 行（純寫入路徑為 0；M-2 雙寫拔除真意）

# 附加驗證：plugin 為 compact_failure SSOT
grep -nE "self\._token_guard_plugin\.(record_compact_failure|reset_compact_failure|process_compact_result)" autoclaude/execution/_runner_internals.py
# 期望：≥ 1 行（mixin 透過 plugin API 操作 counter，非直寫）
```

---

### ── W3：CheckpointPlugin 擴 + EvolutionPlugin 擴（7 PD）──

**目標**：
- CheckpointPlugin 吸收 3 條中斷路徑方法群
- EvolutionPlugin 吸收 escalation 觸發部分
- 新增 ON_PERSISTENCE_REQUEST phase（W0 已定義）
- 補 3 中斷路徑 × 4 case = 12 case 測試

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W3。

G2 已通過，基線：≥ 1199 passed。

【W3-1】CheckpointPlugin 吸收（逐一搬移，每搬一個立即全測）
  從 _runner_internals.py 搬移：
  (a) _save_evolution_resume_checkpoint（TOKEN_HALT 觸發）
  (b) _handle_token_halt 的 checkpoint 部分
  (c) _save_interrupt_checkpoint（ESC+F12 中斷）
  (d) _save_escalation_dump

  ⚠️ 每搬一個立即全測，不可批次
  訂閱 ON_PERSISTENCE_REQUEST phase，回傳 PersistenceResult

【W3-2】CheckpointPlugin 若超 250 LOC → 拆 package
  autoclaude/plugins/checkpoint/__init__.py
  各子模組 ≤ 250 行

【W3-3】EvolutionPlugin 擴
  吸收 _save_escalation_dump（escalation 觸發部分）
  訂閱 ON_ESCALATION_DUMP_REQUEST
  訂閱 ON_EVOLUTION_PROPOSE / ON_EVOLUTION_APPLY（W0 已定義）

【W3-新測試】tests/equivalence/test_counter_persistence_three_paths.py
  3 條中斷路徑（TOKEN_HALT / ESC+F12 / ESCALATION）× 4 case = 12 case
  ≥ 3 case 必須是「中斷時序污染」場景
  coverage ≥ 83%

架構紅線：見執行指南 §2
完成後執行 G3 驗證命令
```

**G3 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠（51 case 含 13 新 W3 case）

python -m pytest tests/equivalence/test_counter_persistence_three_paths.py -v 2>&1 | tail -15
# 期望：13/13 全綠（12 case 規格 + 1 case 真實 deep-copy 防護，SD-M3 修補強）

python -m coverage report --include="autoclaude/*" | tail -5
# 期望：≥ 83%

# SD_05 W3 三方審查 SD-M4 補：驗證 4 個 mixin 方法已 delegate（非 double-write）
grep -nE "self\._checkpoint_plugin\." autoclaude/execution/_runner_internals.py | wc -l
# 期望：≥ 4（4 個 delegate wrapper 各至少呼叫一次 plugin 公開 API）

# 確認沒有直接 instantiate CheckpointManager（應只走 plugin 注入）
grep -cE "^\s+CheckpointManager\(" autoclaude/execution/_runner_internals.py
# 期望：0（mixin 不應直接建立 CheckpointManager）

# 確認 PlaybookRunner 注入 self._checkpoint_plugin
grep -n "self\._checkpoint_plugin\s*=" autoclaude/execution/playbook_runner.py
# 期望：1 行（__init__ 內注入）
```

---

### ── W4：MutationApplyService 擴 + 新 Plugin（5 PD）──

**目標**：
- MutationApplyService 補 3 個 strategy（DELETE / SKIP_TO / CONDITIONAL）
- 新建 FastPathPlugin
- 新建 PlaybookPersistencePlugin

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W4。

G3 已通過，基線：≥ 1199 passed。

【W4-1】MutationApplyService 補齊 7 種 strategy
  現有 4 種：REVISE_CURRENT / INJECT_AFTER / INJECT_BEFORE / GOTO_STEP
  補充 3 種：DELETE / SKIP_TO / CONDITIONAL
  每種 strategy ≤ 60 行，若超限拆子模組
  counter increment 委派至 GotoCounterPlugin（不在 MutationApplyService 內部維護）

【W4-2】新建 FastPathPlugin（~50 行）
  位置：autoclaude/plugins/fast_path_plugin.py
  功能：訂閱 PRE_ATTEMPT phase
  方法：_fast_path_test_file_check（從 _runner_internals.py 搬移）
  回傳：PromptInjectionResult
  使用 tests/plugins/_template.py 作為基礎（W0 已建）
  coverage ≥ 90%

【W4-3】新建 PlaybookPersistencePlugin（~120 行）
  位置：autoclaude/plugins/playbook_persistence_plugin.py
  功能：訂閱 ON_EVOLUTION_APPLY phase
  方法：_persist_mutated_playbook + .mutated.yaml 載入清理
  從 _runner_internals.py 搬移這兩個方法
  coverage ≥ 90%

【W4-4】GoalSynthesisPlugin 補齊
  吸收：_validate_global_goal_achievement / _build_achievement_summary /
         _prepend_global_goal / _prepend_global_goal_brief
  確認 LOC ≤ 250

【W4-5】wiring.py 注入兩個新 Plugin
  FastPathPlugin + PlaybookPersistencePlugin 加入 plugin 清單
  確認 order 正確（PRE_ATTEMPT 在 before_step 之前）

架構紅線：見執行指南 §2
完成後執行 G4 驗證命令
```

**G4 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed（W4 實測：1,435 passed）

python -m pytest tests/plugins/test_fast_path.py tests/plugins/test_playbook_persistence.py -v 2>&1 | tail -10
# 期望：全綠，coverage ≥ 90%（W4 實測：fast_path 100% / playbook_persistence 100%）

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠（W4 實測：52 passed）

python tools/check_loc_budget.py
# 期望：全部 ≤ 250（W4 實測：total=10563 / cap=12183 / violations=0）

# W4 mixin delegate grep 驗證（SA-C1/C2 修復把關）
grep -n "self._fast_path_plugin\._check\|self._playbook_persistence_plugin\.\|self._goal_synthesis_plugin\." autoclaude/execution/_runner_internals.py autoclaude/execution/playbook_runner.py | wc -l
# 期望：≥ 8（6 delegate + load_mutated_if_exists + cleanup_mutated_for_paths）

# W4 conditional 安全縱深驗證
grep -n "shell=False\|_DENY_CHARS\|_MAX_RECURSION_DEPTH" autoclaude/core/services/mutation/_conditional_evaluator.py autoclaude/core/services/mutation/conditional.py | wc -l
# 期望：≥ 3（shell=False + _DENY_CHARS + _MAX_RECURSION_DEPTH 三層縱深）

# W4 importlinter 對齊
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：Contracts: 3 kept, 0 broken
```

---

### ── W5：測試重寫（180+ patch 點）（10 PD）──

**目標**：
- 分三批遷移測試（plugins → core/infra → integration/equivalence）
- 補 7 個 context regex 涵蓋率測試（M-8）
- AutoResumeMetrics 上線（M-9）
- coverage ≥ 85%

**給 Opus 4.7 的指令（批 1）**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W5 批次 1。

G4 已通過，基線：≥ 1199 passed。

⚠️ W5 必須分三批，每批末必須「全測 + equivalence + lint-imports」三 gate 全綠才進下一批

【W5-批1】tests/plugins/ 目錄重寫（最獨立，先做）
  目標：所有 plugins/ 下的測試，將 patch 路徑從 _runner_internals.py 改為各 Plugin 的新路徑
  操作：依序處理每個 test 檔，逐檔更新 patch path，每更新一檔立即跑該測試
  必須附 patch 點對照表：
    舊 patch path → 新 patch path（每個測試檔一條）

  特別注意：
  - tests/plugins/test_token_guard_plugin.py → 改為 token_guard/ package 路徑
  - tests/plugins/test_checkpoint_plugin.py → 改為新的 ON_PERSISTENCE_REQUEST 路徑
  - tests/plugins/test_evolution_plugin.py → 改為 ON_EVOLUTION_PROPOSE / APPLY 路徑
  - tests/plugins/test_fast_path.py → 新建（FastPathPlugin）
  - tests/plugins/test_playbook_persistence.py → 新建（PlaybookPersistencePlugin）

批1 末執行三 gate：
  python -m pytest tests/ -q --tb=no | tail -3          # ≥ 1199 passed
  python -m pytest tests/equivalence/ -q --tb=no | tail -3  # 13/13
  python -m importlinter --config .importlinter          # 0 broken
```

**給 Opus 4.7 的指令（批 2）**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W5 批次 2。

W5 批1 已通過三 gate，繼續批2。

【W5-批2】tests/core/ + tests/infra/ 重寫
  更新所有 core/ 和 infra/ 下測試的 patch 路徑
  特別注意：
  - tests/core/test_kernel.py → 更新 ON_PERSISTENCE_REQUEST / ON_EVOLUTION_* 等新 phase 路徑
  - tests/infra/ → 更新 repository 相關測試
  - 新建 tests/core/test_event_bus_metrics.py（EventBus trace_id metrics，QA Q-M1）
    連續 3 次相同 phase 失敗應觸發 escalate
  coverage ≥ 84%

批2 末執行三 gate（同批1）
```

**給 Opus 4.7 的指令（批 3）**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W5 批次 3。

W5 批2 已通過三 gate，繼續批3。

【W5-批3-A】tests/integration/ + tests/equivalence/ 重寫
  最複雜批次，equivalence snapshot 必須維持 13/13 全綠

【W5-批3-B】補 7 個 context regex 涵蓋率測試（M-8）
  建立 tests/test_token_pattern_coverage.py
  tests/fixtures/claude_output_samples/*.txt（≥ 30 個真實 Claude 輸出樣本）
  7 個 regex 每個 ≥ 95% 涵蓋率

【W5-批3-C】AutoResumeMetrics（M-9）
  新增 AutoResumeMetrics 資料類別
  新增 ON_AUTO_RESUME_WAKE event（W0 已定義 phase）
  AutoResumeService 於每次重試時發出此 event + 記錄 metrics

coverage ≥ 85%（全測）+ 新 Plugin ≥ 90%

批3 末執行完整 G5 驗證
```

**G5 驗證命令**：
```bash
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed（實際會更高，因為新增了測試）

python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3
# 期望：13/13 全綠

python -m pytest tests/test_token_pattern_coverage.py -v 2>&1 | tail -10
# 期望：全綠，coverage ≥ 95%

python -m coverage report --include="autoclaude/*" | tail -5
# 期望：≥ 85%

python -m importlinter --config .importlinter
# 期望：0 broken
```

---

### ── W6：收尾 + 刪除 + Migration Guide（3 PD）──

**目標**：
- 刪除 `_runner_internals.py`（1,766 行）
- 刪除 `_runner_compat.py`（238 行）
- 刪除 `use_kernel_path=False` 路徑
- 移除 CheckpointPlugin `goto_counter_plugin=None` deprecated 參數
- 補 Migration Guide

**給 Opus 4.7 的指令**：
```
請以 dev-developer Agent 角色執行 SD_Improving_05 W6（最終收尾）。

G5 已通過，基線：≥ 1199 passed。

【W6-1】刪除 _runner_internals.py
  前置確認：grep -r "_runner_internals" autoclaude/ tests/
  期望：0 行（表示已無任何 import 或 patch 引用）
  若有殘留 import → 先清理再刪除
  刪除後立即全測

【W6-2】刪除 _runner_compat.py
  前置確認：grep -r "_runner_compat" autoclaude/ tests/
  同上，確認 0 引用再刪除
  刪除後立即全測

【W6-3】刪除 use_kernel_path 雙路徑
  autoclaude/execution/playbook_runner.py 移除 use_kernel_path 參數
  autoclaude/core/kernel.py 移除對應分支
  全測

【W6-4】移除 deprecated 參數
  CheckpointPlugin.__init__ 移除 goto_counter_plugin=None 參數
  全測

【W6-5】統一 KernelResult（✅ 移除 PlaybookResult 並存）
  確認所有呼叫端已統一使用 KernelResult
  移除 PlaybookResult（若尚未移除）

【W6-6】Migration Guide
  新建 docs/08_deployment/SD05_Migration_Guide.md
  內容：
  - 舊 config 欄位升級對照表
  - use_kernel_path 移除說明 + DeprecationWarning 發出時間
  - TokenGuardConfig per-step override 使用方式
  - Plugin 架構變化摘要（含新 phase 列表）

架構紅線：見執行指南 §2
完成後執行 G6 最終驗證
```

**G6 最終驗證命令（三方/四方審查前）**：
```bash
# 1. 全測（最重要）
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1199 passed（實際應更高）

# 2. equivalence 13/13 全綠
python -m pytest tests/equivalence/ -q --tb=no 2>&1 | tail -3

# 3. importlinter 0 broken
python -m importlinter --config .importlinter

# 4. LOC 全部 ≤ 250
python tools/check_loc_budget.py

# 5. 確認刪除完成
test ! -f autoclaude/execution/_runner_internals.py && echo "OK: _runner_internals.py 已刪"
test ! -f autoclaude/execution/_runner_compat.py && echo "OK: _runner_compat.py 已刪"

# 6. 確認 use_kernel_path 已移除
grep -r "use_kernel_path" autoclaude/ && echo "ERROR: 仍有殘留" || echo "OK: 已清除"

# 7. coverage ≥ 85%
python -m coverage report --include="autoclaude/*" | tail -5

# 8. 7 regex 涵蓋率 ≥ 95%
python -m pytest tests/test_token_pattern_coverage.py -v 2>&1 | tail -5

# 9. mutation test（nightly gate，G6 必須）
# mutmut run --paths-to-mutate autoclaude/plugins/goto_counter_plugin.py
# mutmut results  # 期望 kill rate ≥ 75%

# 10. LOC 減少驗證
wc -l autoclaude/execution/*.py
# 期望：playbook_runner.py 應 ≤ 300；_runner_internals.py 和 _runner_compat.py 不存在
```

---

## 4. 波次間 Session 切換協議

每個 Wave 開始前（切換到新 Opus 4.7 session 時），使用以下開場指令：

```
我正在執行 SD_Improving_05 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] passed / [skipped 數] skipped
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製上方 Wave 目標清單]

請先執行前置確認：
python -m pytest tests/ -q --tb=no | tail -3
python -m importlinter --config .importlinter
wc -l autoclaude/execution/_runner_internals.py

確認後依照 SD05_Execution_Guide.md W[n] 指令執行。
```

---

## 5. 緊急停止與回退協議

| 觸發條件 | 立刻執行 |
|---------|---------|
| equivalence snapshot 任一斷裂 | `git revert HEAD`，找 SA + QA 雙簽才可重啟 |
| importlinter broken | `git stash`，找 Architect 確認再重試 |
| 全測數量下降 | `git stash`，找出哪個測試被移除/跳過 |
| TokenGuard compact 連續失敗無限循環（R-W2-1） | `EMBEDDER_BACKEND=bge_m3_local` 設定是否正確；回退至 G1 checkpoint |
| 任何 3 個連續 commit 仍紅 | 停止當前 Wave，回退至前一 G-gate commit |

```bash
# 找到前一 Gate 的 commit
git log --oneline | grep "G[0-6] passed\|gate\|Gate"

# 回退（確認無誤後）
git reset --hard <commit-hash>
```

---

## 6. 進度追蹤表

| Wave | 狀態 | 通過日期 | 測試基線 | 備注 |
|------|------|---------|---------|------|
| W0 | ✅ G0 通過 | 2026-05-16 | 1275/15 | T0-1~T0-6 全綠 + 三方覆驗 7 Critical 全部修復 + 四方審查 APPROVED |
| W1 | ✅ G1 通過 | 2026-05-16 | 1312/15 | Counter SSOT 遷移（4 counter→Plugin）+ Step-2 CounterSnapshotResult；三方覆驗 1 Major+4 Minor 全部修復 + 四方審查 APPROVED；第 5 個 compact_failure 移交 W2 |
| W2 | ✅ G2 通過（覆驗版） | 2026-05-16 | 1349/15 | TokenGuardPlugin 5 方法群下沉 + M-2 雙寫拔除（0 writes）+ M-7 per-step override + typo validator；三方覆驗 4 Critical+3 Major **全部修復**（G2 grep / 3 方法測試 / docstring / setter lazy / 公開 property / typo validator / §6 更新）；plugin LOC=219≤250 暫不拆；37 case YAML compat 測試；四方審查 APPROVED |
| W3 | ✅ G3 通過（覆驗版） | 2026-05-16 | 1368/15 | CheckpointPlugin 吸收 4 中斷路徑方法（delegate）+ 拆 6 子模組 package（全 ≤ 250 LOC）+ EvolutionPlugin 訂閱 4 phase；新訂閱 ON_PERSISTENCE_REQUEST / ON_ESCALATION_DUMP_REQUEST；13 case test_counter_persistence_three_paths.py（含 1 真實 deep-copy 防護）；三方覆驗 3 Critical+多 Major **全部修復**（C1 dump_path 真實路徑 / C2 NO-OP docstring + audit log / Arch-M1 closure snapshot / SA-M1+M2 6 case 正向 IHookResult / SD-M1 失敗分支 None / SD-M3 改名+真實 race case / SD-M4 G3 grep / SA-M4 §6.3 補 7 條 W3 拔除）；coverage TOTAL 87%；importlinter 3 kept / 0 broken；四方審議 APPROVED |
| W4 | ✅ G4 通過（覆驗版） | 2026-05-16 | 1435/15 | (W4-1) MutationApplyService 補 `ConditionalStrategy`（Gap-021，三層縱深防禦 + 巢狀深度 4）+ conditional.py 拆 `_conditional_evaluator.py` ≤80 LOC；(W4-2) `FastPathPlugin`（PRE_ATTEMPT phase，coverage 100%，22 case）；(W4-3) `PlaybookPersistencePlugin`（ON_EVOLUTION_APPLY phase + 3 公開 API + callable resolver，coverage 100%，17 case）；(W4-4) `GoalSynthesisPlugin` 吸收 4 mixin 方法（prepend_global_goal / brief / build_achievement_summary / validate_global_goal_achievement，14 case boundary）；(W4-5) wiring 注入 2 新 plugin + register_order_invariant test 3 case；**mixin delegate** 6 方法（_fast_path_test_file_check / _persist_mutated_playbook / _prepend_global_goal / _build_achievement_summary / _validate_global_goal_achievement / _prepend_global_goal_brief）；三方覆驗 2 Critical+多 Major **全部修復**（SA-C1/C2 plugin 接線 / Arch-M1+SD-M2+SA-M1 shell 安全 / SD-M1 巢狀深度 / SD-M3 假陰性 logger / SA-M4+Arch-M2 PersistenceResult NO-OP / Minor 12 條）；importlinter 3 kept/0 broken；LOC violations 0；四方審議 APPROVED |
| W5 批1 | ✅ 通過 | 2026-05-16 | 1477/15 | tests/plugins/ 246 case 全綠（grep _runner_internals 無命中）；新增 test_fast_path 22 case 100% + test_playbook_persistence 17 case 100%；三 gate（全測 1477 + equivalence 52/52 + importlinter 3 kept）|
| W5 批2 | ✅ 通過 | 2026-05-16 | 1477/15 | tests/core/ + tests/infra/ 264 case 全綠；test_event_bus_metrics 18 case（trace_id / phase_failure / escalate / migration_flag）；三 gate 全綠 |
| W5 批3 | ✅ 通過 | 2026-05-16 | 1494/15 | (A) integration+equivalence 115 case；(B) M-8 `tests/test_token_pattern_coverage.py` 38 case + 8 樣本檔 70+ 行（regex2 從 70%→100%）+ TestMutationCoverage + TestFixtureInvariant + TestKnownFalsePositiveBoundary；(C) M-9 AutoResumeMetrics dataclass + record_wake_and_emit keyword-only + NotificationPlugin 訂閱 ON_AUTO_RESUME_WAKE，test_auto_resume_metrics 18 case |
| W5 G5 | ✅ 通過（覆驗版） | 2026-05-16 | 1494/15 | **W5 G5 三方覆驗 7 Critical+13 Major+12 Minor 全部修復**：(C-A1+SD1) `_make_stub_playbook()` 工廠 / (C-A2) except 收斂 + HookContractViolation 冒泡 / (C-SA1) TestMutationCoverage / (C-SA2) negative 重寫 + TestKnownFalsePositiveBoundary / (C-SD2) 真實 EventBus contract violation 測試 / (C-SD3) LOC 口徑統一 / (M-A1) metrics 改 snapshot dict / (M-A2) bus=None logger.error / (M-A3) 演化 wait_secs / (M-SA1) failed_emits+deque(maxlen=200) / (M-SA2) Literal kind+ValueError / (M-SA3) NotificationPlugin 訂閱避死碼 / (M-SD2) MagicMock 取代 _SeqKernel / (M-SD5) keyword-only；coverage TOTAL **87%**；importlinter 3 kept/0 broken；LOC violations 0；equivalence 52/52；**四方審議 4/4 APPROVED** |
| W6 | 🟡 部分完成（PM §1.3 例外簽核） | 2026-05-17 | 1491/15 | (W6-3) use_kernel_path 雙路徑移除（含 test_main_deprecation.py 刪 + cli test rename） / (W6-4) CheckpointPlugin goto_counter_plugin=None deprecated 參數拔除 + `**deprecated_kwargs` alias 過渡期 / (W6-5) KernelResult SSOT 確認（PlaybookResult 延後 SD_06 W2，PM 例外簽核） / (W6-6) SD05_Migration_Guide.md v1.1 + §6.3 完成度 1/22（PM 例外）；W6-1 _runner_internals.py 1,694 行 + W6-2 _runner_compat.py 238 行**未物理刪除**，延後 SD_06 W0/W2；三方審查 6 Critical + 6 Major 全部修復；importlinter 3 kept / 0 broken；LOC violations 0；equivalence 52/52；risk_log R-W6-1~5 登記 |

---

## 7. 已完成的前置工作（執行前已就緒）

| 項目 | 狀態 | 說明 |
|------|------|------|
| Docker PostgreSQL | ✅ | pgvector/pgvector:pg16，port 5432 |
| Docker TEI BGE-M3 | ✅ | ghcr.io/huggingface/text-embeddings-inference:89-1.5，port 8080，Dimensions=1024，Latency≈96ms |
| deployment/README.md | ✅ | SD_06 W7 提前完成 |
| .env.example 完整 | ✅ | 含 MINIMAX_GROUP_ID / TEI_EMBED_DIMENSIONS / EMBEDDER_BACKEND |
| tools/probe_minimax_embedding.py | ✅ | --list-models 功能已補 |
| tools/download_bge_m3.py | ✅ | BGE-M3 已下載至 .model_cache/ |
| Minimax embo-01 | ⚠️ | embo-01 帳號未訂閱，MinimaxEmbedderAdapter 列入 SD_06 W3 但需另行開通 |
| 測試基線確認 | ✅ | 1199 passed / 10 skipped（2026-05-16） |
