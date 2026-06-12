# SD_Improving_07 — SD_06 延期收尾 + LOC 政策重議 + 肥胖檔案二度拆解

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.1（PM 4 項拍板 APPROVED + G0 啟動日鎖定 2026-05-20）** |
| 建立日期 | 2026-05-18 |
| 前置文件 | [SD_Improving_06.md](SD_Improving_06.md) v1.2（W6 G6 通過 ✅ 1,802 passed / 118 skipped）/ [SD06_Migration_Guide.md](../08_deployment/SD06_Migration_Guide.md) v1.0 §5 §7 |
| 三方審查 | Architect / SA / SD 三方獨立審查 2026-05-18（六大議題完整性 + LOC 政策 + 736 行新肥胖檔案）|
| QA 審議 | ✅ 2026-05-18 APPROVED_WITH_CONDITIONS（Q-C1~Q-C4 已補強至 v1.0）|
| PM 拍板 | ✅ 2026-05-18 **4/4 APPROVED**（#1 LOC 政策形式核准 + #2 真實 PG 啟用 + #3 W4 一次切 + #4 啟動日 2026-05-20）|
| 文件狀態 | **APPROVED — 所有阻塞已解除；G0 啟動日 2026-05-20** |

---

## 0. 觸發 SD_07 的事實依據（三方共識）

| 觸發事實 | 證據 | 影響 |
|---------|------|------|
| SD_06 W6 §7 延期清單 | SD06_Migration_Guide.md §5 + §7 | 3 項 NOTE(SD_07) 物理拔除待辦 |
| **新發現肥胖檔案** | `wc -l steps_orchestrator/_impl.py = 736` | SD_06 W2 拆解未完成（≫ 250 budget）|
| LOC budget violations=1 | `total=13847 > cap=12904`（W3 累積尚未消化）| 需重新校準 baseline |
| token_guard 拆 5 子模組未做 | `token_guard_plugin.py = 20 LOC shim`，子模組未生 | SD_06 §7.3 延期項 |
| 使用者明確要求 | 「250 行是否太嚴苛？請嚴正探討、研究、決定」 | LOC 政策必須三方重議 |
| 使用者議題 0 | Minimax/Claude Code 完美協作 | 需 e2e 整合驗證（SD_06 W1 已建骨架，未端對端壓測）|

---

## 1. Sprint 範圍

SD_07 範圍 = **SD_06 W6 NOTE(SD_07) 延期 9 PD** + **新肥胖檔案拆解 6 PD** + **LOC 政策研究與重設 + 整合驗證 + token_guard 拆 5 子模組 13 PD**。

| 來源 | PD | 對應 Wave |
|------|----|----------|
| SD_06 NOTE(SD_07) 延期物理拔除（_consecutive_compact_failures / _prepend_global_goal_brief / PlaybookResult→KernelResult）| 6 PD | W4 |
| 新肥胖檔案 `steps_orchestrator/_impl.py` 736 LOC 拆解 | 6 PD | W1 |
| LOC 政策三方研究 + baseline 重新校準 | 3 PD | W0 + W5 |
| 6 大議題端對端整合測試（Brain/Executor + PG 三層 + 向量 + 狀態恢復 + ConfigResolver）| 4 PD | W2 |
| token_guard_plugin 拆 5 子模組 | 3 PD | W3 |
| Plugin 架構合規性審計 + Migration Guide | 3 PD | W5 + W6 |
| **合計** | **25 PD** | W0-W6 |

PM contingency：預留 **2 PD**（W4 patch path 遷移風險）。

---

## 2. 6 大關注議題 → 對應 SD_06 完成度 + SD_07 強化項目

| 議題 | SD_06 狀態 | SD_07 強化 / 收尾 |
|------|-----------|------------------|
| **#0 Minimax/Claude Code 分工** | ✅ SD_06 W1 G1 OrchestrationCoordinator + BrainCapabilities + ExecutionEvent 落地（232 LOC ≤ 250）| **W2**：e2e 整合測試（5 種失敗情境 × Brain→Executor→Event→Coordinator 完整往返）|
| **#1 肥胖檔案** | ⚠️ `_runner_internals.py` 已刪除，但 **`steps_orchestrator/_impl.py` = 736 LOC 嚴重超標** | **W0 LOC 政策三方研究 → W1 依新政策拆 3-5 子模組** |
| **#2 Plugin 架構** | ✅ SD_06 W6 mixin 物理刪除；importlinter 5 kept | **W5**：完整 Plugin walk-through 審計 + `runner-no-checkpoint-logic` 從 grep 升級至 module-level contract |
| **#3 PG 三層任務模型** | ✅ SD_06 W3 alembic 0009 完成 + W4 YAML 匯入 100% | **W2**：三層 schema CRUD e2e + RBAC 三角色矩陣負向測試 |
| **#4 向量檢索** | ✅ SD_06 W3 IEmbedder/IVectorSearch + 雙 adapter + per-table HNSW | **W2**：recall@10 ≥ 0.95 + p95 < 50ms 真實 PG（不 skip）|
| **#5 狀態保存恢復** | ✅ SD_06 W5 ExecutionContext + drift_log + run_id 過濾 + 365 天 partition | **W2**：SIGINT → checkpoint → restart 多 run 並存 e2e（5 run × 不互相干擾）|
| **#6 參數設定檔（/compact + token）** | ✅ SD_06 W5 ConfigResolver 4 層 + Pydantic v2 invariants + audit log | **W2**：4 層 hierarchy property-based test（Hypothesis ≥ 50 example）+ hot-reload smoke |

---

## 3. Critical 風險清單（三方共識）

### 🔴 議題 1+2：肥胖檔案 + Plugin 架構

**R-SD07-1-1 [Architect]**：`steps_orchestrator/_impl.py` 736 LOC 為 SD_06 W2 拆解殘留 god-module
- **緩解**：W0 政策決定後 → W1 拆 3-5 子模組（每檔 ≤ 新政策 budget）

**R-SD07-1-2 [SA]**：250 LOC 紅線過嚴反致 SSOT 漂移（多檔同題容易出 SSOT 多源）
- **緩解**：W0 三方研究產出 ADR-SD07-001 LOC 政策（推薦：分級 budget — 純資料 ≤ 150 / 邏輯 ≤ 300 / 編排 ≤ 450 / Plugin entry ≤ 250）

**R-SD07-1-3 [SD]**：250 LOC budget 對 Plugin 入口檔案（公開 API）合理；對 strategy / orchestrator 過嚴
- **緩解**：依 ADR-SD07-001 分級調整 `tools/check_loc_budget.py` per-file 預算表

### 🔴 議題 0：Minimax/Claude Code 協作完整性驗證

**R-SD07-0-1 [Architect]**：SD_06 W1 Coordinator 為單元測試覆蓋，缺 5 種真實失敗情境 e2e
- **緩解**：W2 補 e2e（Token Halt / ESC+F12 / Minimax decide_correction / decide_escalation / send_interrupt 中斷往返 5 個情境）

**R-SD07-0-2 [SD]**：BrainPort capabilities 與 ExecutorPort on_event callback 在 dry_run 模式下未驗證
- **緩解**：W2 補 dry_run 模式整合測試 + capabilities 驗證

### 🔴 NOTE(SD_07) 延期項物理拔除

**R-SD07-W4-1 [SD]**：`_consecutive_compact_failures` property + setter（playbook_runner.py:141-170）9 處 patch path
- **緩解**：W4 分三步：(a) 遷移 9 處 test patch path → plugin SSOT；(b) 確認 grep 0 references；(c) 物理拔除 property + setter

**R-SD07-W4-2 [SD]**：`_prepend_global_goal_brief` shim（playbook_runner.py:222-230）11 處 patch path
- **緩解**：W4 分三步：(a) 遷移 11 處 → GoalSynthesisPlugin SSOT；(b) confirm grep 0；(c) 物理拔除 shim

**R-SD07-W4-3 [Architect]**：PlaybookResult → KernelResult SSOT 完整切換（50+ assertion）需先完成上述兩項 + frozen surface 全面退役
- **緩解**：W4 最後一步（上述完成後再動）；assertion 升級採 `to_kernel_result()` 自動轉換包裝

### 🔴 議題 6：LOC budget violations 持續存在

**R-SD07-5-1 [Architect]**：SD_06 G6 LOC violations=1（13847 > 12904）未解 → SD_07 W0 必校準
- **緩解**：W0 重新測算合理 baseline（含 W3 alembic / adapter 永久增量），更新 `tools/check_loc_budget.py` 基準

---

## 4. Wave 執行計畫

### ── W0：ADR-SD07-001 已就位 + 工具升級 + AC scaffolding（3 PD）──

**目標**：
- ✅ ADR-SD07-001 LOC 政策三方共識（**規劃階段已完成 2026-05-18**；分級制取代 250 一刀切）
- W0 交付：`tools/check_loc_budget.py` 升級為分級判定 + `.loc-budget.toml` overrides
- 重新校準 baseline（含 W3 alembic / adapter 永久增量）
- SD_07 AC Matrix scaffolding（每項可量測）
- 6 大議題完整性驗證 fixture（10 個三層任務 e2e 樣本）

**逐項打勾**：
```
[✅] T0-1 ADR-SD07-001-loc-policy.md（已在規劃階段完成，三方共識）
[  ] T0-2 升級 tools/check_loc_budget.py 支援分級 LOC_TIERS table（依 ADR §5.1）
[  ] T0-3 新建 .loc-budget.toml（per-file overrides，依 ADR §5.2）
[  ] T0-4 重新測算 baseline，吸收 W3 alembic 0007-0014 + adapter 永久增量
[  ] T0-5 補 tests/contract/test_loc_budget_tiered.py（≥ 6 case：各分級邊界）
[  ] T0-6 SD_07 AC Matrix scaffolding（W1~W6 共 ≥ 18 條 AC，每條含量測命令）
[  ] T0-7 補 tests/integration/fixtures/sd07_e2e_samples/（5 種 Brain/Executor 失敗情境 fixture）
[  ] T0-8 .env.example 補 LOC_BUDGET_POLICY_VERSION=v2（標記政策版本）
[  ] T0-9 撰寫 SD07_Execution_Guide.md（W0~W6 執行協議 + 緊急停止）
```

**G0 驗證**：
```bash
[  ] ls docs/04_planning/ADR/ADR-SD07-001-loc-policy.md    # 存在 + 三方簽名
[  ] python tools/check_loc_budget.py                        # 分級制下 violations=0
[  ] python -m pytest tests/contract/test_loc_budget_tiered.py -v   # ≥ 6 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3            # ≥ 1,802 passed（基線）
```

---

### ── W1：`steps_orchestrator/_impl.py` 736 行拆解（6 PD）──

**目標**：依 ADR-SD07-001 政策拆 `_impl.py` 736 LOC → 多子模組（每檔 ≤ 政策 budget）

**逐項打勾**：
```
[  ] T1-1 盤點 _impl.py 函式群（grep `def ` + 行數區段標記）
[  ] T1-2 依職責拆分（規劃 → 實作異動：W1 G1 評估後改為 2 模組（302+185 LOC），更貼合 strategy tier 與責任邊界）：
      - _impl.py 保留主 _run_steps 編排骨架（service tier ≤ 500 LOC；W1 G1 實測：物理 wc-l 530 / 邏輯行 ≤ 500）
      - **_escalation_handler.py（302 LOC）**：handle_convergence_escalation + handle_max_retries_escalation + 共用 _handle_goal_synthesis_recovery（convergence escalate L276-379 共 104 LOC + max_retries escalate L420-522 共 103 LOC）
      - **_correction_helpers.py（185 LOC）**：apply_step_mutations 統一 batch/single 突變（Gap-019-B / Gap-025 / Gap-034 + _MutationApplyOutcome 五旗標）+ validate_and_retry_correction（Gap-009-C 應用驗證 + Gap-008-D 品質驗證 + 策略輪換重試）
      - ~~_step_dispatcher.py / _attempt_loop.py / _evaluation.py / _state_transitions.py（原規劃 4 模組已廢棄）~~：W1 G1 評估發現原 4 模組切法會破壞 attempt for-loop 的局部變數共享（escalation_history / convergence_label / mutation 等），改 2 模組更貼合 strategy tier ≤ 300 邊界與單一責任原則
[  ] T1-3 逐函式群搬移（每搬 50-100 LOC 立即跑全測）
[  ] T1-4 確認 LOC 政策（_impl.py ≤ 450 編排層 / 子模組 ≤ 300 strategy）
[  ] T1-5 補 tests/equivalence/test_steps_orchestrator_decomposition.py（拆解前後行為等價）
[  ] T1-6 確認 importlinter 維持 5 kept / 0 broken
```

**G1 驗證**：
```bash
[  ] wc -l autoclaude/execution/steps_orchestrator/_impl.py   # ≤ 450（編排層）
[  ] wc -l autoclaude/execution/steps_orchestrator/*.py        # 每子模組 ≤ 政策 budget
[  ] python tools/check_loc_budget.py                          # violations=0
[  ] python -m pytest tests/ -q --tb=no | tail -3             # ≥ 1,802 passed（不下降）
[  ] python -m pytest tests/equivalence/ -q --tb=no            # 74/74 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter         # 5 kept / 0 broken
```

---

### ── W2：6 大議題 e2e 整合測試 + Brain/Executor 完美協作驗證（4 PD）──

**目標**：補強 SD_06 各 Wave 單元測試外的端對端整合測試，驗證使用者 6 大關注議題完整性

**逐項打勾**：
```
[  ] T2-1 tests/integration/test_brain_executor_e2e.py（議題 0，≥ 8 case）：
      - Token Halt → Coordinator → CheckpointPlugin → AutoResumeService 往返
      - ESC+F12 中斷 → send_interrupt → CheckpointPlugin → restart
      - Minimax decide_correction → ExecutorPort.execute(on_event) → ON_EVENT phase
      - decide_escalation → EvolutionPlugin → ON_ESCALATION_DUMP_REQUEST
      - dry_run 模式下完整 phase 序驗證
[  ] T2-2 tests/integration/test_three_tier_crud_e2e.py（議題 3，≥ 6 case）：
      - projects CRUD + RBAC（admin/dev/viewer 三角色矩陣 + 違反必 403）
      - goal_tasks 樹狀（深度 1/2/3 + 深度 4 必 reject）
      - execution_items + FK CASCADE
[  ] T2-3 tests/integration/test_pgvector_real_recall.py（議題 4，≥ 3 case，PG 啟用，**不再 skip**）：
      - recall@10 ≥ 0.95（100 query 取 BGE-M3 真實 embedding）
      - p95 latency < 50ms
      - 雙 adapter fallback < 60s RTO
[  ] T2-4 tests/integration/test_multi_run_resume_e2e.py（議題 5，≥ 5 case）：
      - 5 run × 同 GoalTask 並存 × abort 互不干擾
      - SIGINT → checkpoint ≤ 2s → restart 從正確 step
      - dual_state drift 全欄比對（datetime/UUID/Enum normalize）
[  ] T2-5 tests/integration/test_config_resolver_hierarchy_e2e.py（議題 6，≥ 8 case）：
      - 4 層 merge（global → workflow → step → runtime）property-based
      - flat → nested promote + DeprecationWarning
      - RBAC 保護欄位（api_key）runtime override 必 403
      - hot-reload smoke（SIGHUP 或 API trigger）
```

**G2 驗證**：
```bash
[  ] python -m pytest tests/integration/test_brain_executor_e2e.py -v       # ≥ 8 case 綠
[  ] python -m pytest tests/integration/test_three_tier_crud_e2e.py -v      # ≥ 6 case 綠
[  ] python -m pytest tests/integration/test_pgvector_real_recall.py -v     # recall ≥ 0.95
[  ] python -m pytest tests/integration/test_multi_run_resume_e2e.py -v     # ≥ 5 case 綠
[  ] python -m pytest tests/integration/test_config_resolver_hierarchy_e2e.py -v  # ≥ 8 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 1,832 passed（+30）
```

---

### ── W3：`token_guard_plugin` 拆 5 子模組（3 PD）──

**目標**：SD_06 §7.3 延期項；token_guard_plugin.py 目前 20 LOC shim re-export → 拆 5 子模組

**逐項打勾**：
```
[  ] T3-1 新建 autoclaude/plugins/token_guard/ package
[  ] T3-2 watcher.py（token 使用率偵測 + 7 regex pattern，≤ 100 LOC）
[  ] T3-3 compactor.py（/compact 觸發 + prompt 構造 + 結果處理，≤ 100 LOC）
[  ] T3-4 thresholds.py（dynamic threshold + per-step override 解析，≤ 80 LOC）
[  ] T3-5 git_verifier.py（_verify_correction_applied git diff 部分，≤ 60 LOC）
[  ] T3-6 policy.py（IHookResult emit + compact_failure_count 管理，≤ 100 LOC）
[  ] T3-7 plugin.py（TokenGuardPlugin 主類別 + 依賴注入 5 子模組，≤ 150 LOC）
[  ] T3-8 token_guard_plugin.py shim 更新（re-export 維持 backward compat）
[  ] T3-9 補 tests/plugins/token_guard/test_*.py（每子模組 ≥ 5 case，coverage ≥ 90%）
[  ] T3-10 確認 plugin coverage 維持 ≥ 90%
```

**G3 驗證**：
```bash
[  ] ls autoclaude/plugins/token_guard/*.py | wc -l           # ≥ 5
[  ] wc -l autoclaude/plugins/token_guard/*.py                # 每檔 ≤ 政策 budget
[  ] python tools/check_loc_budget.py                          # violations=0
[  ] python -m pytest tests/plugins/token_guard/ -v           # ≥ 25 case 綠
[  ] python -m coverage report --include="autoclaude/plugins/token_guard/*"   # ≥ 90%
[  ] python -m pytest tests/ -q --tb=no | tail -3             # ≥ 1,857 passed（+25）
```

---

### ── W4：SD_07 延期清單物理拔除（6 PD）──

**目標**：SD_06 §5 延期清單 4 項物理拔除（_consecutive_compact_failures / _prepend_global_goal_brief / PlaybookResult→KernelResult）

⚠️ **強制順序**（不可顛倒）：
1. 先拔 `_consecutive_compact_failures`（9 patch path 遷移）
2. 再拔 `_prepend_global_goal_brief`（11 patch path 遷移）
3. 最後完整切換 PlaybookResult → KernelResult（50+ assertion 升級）

**逐項打勾**：
```
[  ] T4-1 盤點 _consecutive_compact_failures 9 處 patch path（test_token_checkpoint.py / test_playbook_yaml_backward_compat.py）
[  ] T4-2 9 處 patch path 改 patch TokenGuardPlugin.compact_failure_count（plugin SSOT）
[  ] T4-3 跑全測 + grep 確認 0 residual reference
[  ] T4-4 物理拔除 playbook_runner.py:141-170 property + setter
[  ] T4-5 盤點 _prepend_global_goal_brief 11 處 patch path（test_gap014_020.py / test_goal_synthesis_plugin.py）
[  ] T4-6 11 處 patch path 改 patch GoalSynthesisPlugin.prepend_global_goal_brief
[  ] T4-7 跑全測 + grep 確認 0 residual reference
[  ] T4-8 物理拔除 playbook_runner.py:222-230 shim
[  ] T4-9 盤點 PlaybookResult assertion 50+ 處（autoclaude/ + tests/）
[  ] T4-10 升級策略：PlaybookRunner.run() 改回傳 KernelResult；對 PlaybookResult 既有 assertion 用 to_kernel_result() 自動轉換
[  ] T4-11 50+ assertion 逐處升級（每 10 處跑全測一次）
[  ] T4-12 物理拔除 PlaybookResult class（保留 types.py 內其他 dataclass）
[  ] T4-13 移除 to_kernel_result() helper（PlaybookResult 已不存在）
[  ] T4-14 grep "NOTE(SD_07)" autoclaude/ tests/ 必須 = 0
```

**G4 驗證**：
```bash
[  ] grep -rn "_consecutive_compact_failures" autoclaude/execution/playbook_runner.py | wc -l   # = 0
[  ] grep -rn "_prepend_global_goal_brief" autoclaude/execution/playbook_runner.py | wc -l      # = 0
[  ] grep -rn "PlaybookResult" autoclaude/ tests/ | grep -v "types.py" | wc -l                  # 期望大幅下降至 ≤ 5
[  ] grep -rn "NOTE(SD_07)" autoclaude/ tests/ | wc -l                                          # = 0
[  ] python -m pytest tests/ -q --tb=no | tail -3                                               # ≥ 1,857 passed（不下降）
[  ] python -m pytest tests/equivalence/ -q --tb=no                                             # 74/74 全綠
```

---

### ── W5：Plugin 架構合規性審計 + LOC baseline 鎖定（3 PD）──

**目標**：
- 全部 Plugin walk-through 審計（確認 12 個 Plugin 全合規）
- `runner-no-checkpoint-logic` contract 從 grep-based 升級至 module-level（importlinter 原生）
- LOC baseline 鎖定（吸收 W3 alembic / adapter 永久增量）

**逐項打勾**：
```
[  ] T5-1 撰寫 docs/06_quality/SD07_Plugin_Audit_Report.md：
      - 12 個 Plugin 公開 API + hook subscribe 矩陣
      - 確認無 plugin-to-plugin import（importlinter 3 kept 驗證）
      - 確認無直接 import infra（建構式注入驗證）
      - 確認每 Plugin coverage ≥ 80%
[  ] T5-2 .importlinter 升級 runner-no-checkpoint-logic contract：
      - 從 tests/contract/test_runner_no_checkpoint_logic.py（grep-based）
      - 升級為 importlinter 原生 forbidden contract（autoclaude.execution.playbook_runner ↛ autoclaude.utils.checkpoint_manager 寫入）
[  ] T5-3 lint-imports 期望 6 kept / 0 broken
[  ] T5-4 校準 tools/check_loc_budget.py baseline（執行 SD_07 末總 LOC，鎖死）
[  ] T5-5 補 tests/contract/test_plugin_walk_through.py（≥ 12 case：每 Plugin 一條 isolation 檢查）
```

**G5 驗證**：
```bash
[  ] ls docs/06_quality/SD07_Plugin_Audit_Report.md                         # 存在
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 6 kept / 0 broken
[  ] python tools/check_loc_budget.py                                       # violations=0（新 baseline）
[  ] python -m pytest tests/contract/test_plugin_walk_through.py -v         # ≥ 12 case 綠
```

---

### ── W6：收尾 + SD07_Migration_Guide.md + 四方審查（3 PD）──

**目標**：
- 撰寫 docs/08_deployment/SD07_Migration_Guide.md（含 ADR-SD07-001 引用 + 三項物理拔除 breaking change）
- 四方審查（Architect / SA / SD / QA）APPROVED
- gate_audit.md + risk_log.md 更新

**逐項打勾**：
```
[  ] T6-1 git tag sd_07_w5_g5_pass（W6 物理拔除前快照）
[  ] T6-2 撰寫 docs/08_deployment/SD07_Migration_Guide.md v1.0：
      - §1 W0~W6 完成範圍
      - §2 Breaking Changes（PlaybookResult 移除 + _consecutive_compact_failures 移除 + _prepend_global_goal_brief 移除）
      - §3 新增 LOC 政策（ADR-SD07-001 引用）
      - §4 升級步驟（測試 patch path 對照表）
      - §5 已知限制 + SD_08 延期清單（若有）
[  ] T6-3 更新 CLAUDE.md 加入 SD_07 W0~W6 摘要區段
[  ] T6-4 更新 gate_audit.md 加入 §1-quinquies SD_Improving_07 Gates
[  ] T6-5 更新 risk_log.md 加入 §13 SD_Improving_07 新增風險
[  ] T6-6 四方審查（Architect / SA / SD / QA）
[  ] T6-7 PM 簽核
```

**G6 最終驗證**：
```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3              # ≥ 1,857 passed
[  ] python -m pytest tests/equivalence/ -q --tb=no            # 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter          # 6 kept / 0 broken
[  ] python tools/check_loc_budget.py                          # violations=0（新 baseline）
[  ] grep -rn "NOTE(SD_07)" autoclaude/ tests/ | wc -l         # = 0
[  ] wc -l autoclaude/execution/steps_orchestrator/_impl.py    # ≤ 450
[  ] ls autoclaude/plugins/token_guard/*.py | wc -l            # ≥ 5
[  ] test ! "$(grep -c 'class PlaybookResult' autoclaude/execution/types.py)" -ne 0 && echo "OK"  # 已移除
[  ] ls docs/08_deployment/SD07_Migration_Guide.md             # 存在
[  ] ls docs/04_planning/ADR/ADR-SD07-001-loc-policy.md        # 存在
```

---

## 5. PD 估算

| Wave | 範圍 | PD |
|------|------|----|
| W0 | LOC 政策三方研究 + ADR-SD07-001 + baseline 重新校準 + AC scaffolding | 3 |
| W1 | `steps_orchestrator/_impl.py` 736 行拆解 | 6 |
| W2 | 6 大議題 e2e 整合測試 + Brain/Executor 完美協作驗證 | 4 |
| W3 | `token_guard_plugin` 拆 5 子模組 | 3 |
| W4 | SD_07 延期清單物理拔除（3 項，含 50+ assertion 升級）| 6 |
| W5 | Plugin 架構合規性審計 + LOC baseline 鎖定 | 3 |
| W6 | Migration Guide + 四方審查 + 文件更新 | 3 |
| **合計** | | **28 PD** |

PM contingency：預留 **2 PD**（W4 patch path 遷移風險）

---

## 6. 架構紅線（繼承 SD_06 §7 + 新增 3 條）

繼承 SD_06 §7 全部 13 條紅線（❌1~❌13），**新增 3 條**：

| # | 禁止行為 | 來源 |
|---|----------|------|
| ❌14 | 250 LOC 一刀切（取代為 ADR-SD07-001 分級政策；超過分級 budget 必拆 package）| Arch R-SD07-1-2 |
| ❌15 | W4 三項物理拔除順序顛倒（必須先 _consecutive_compact_failures → _prepend_global_goal_brief → PlaybookResult）| SD R-SD07-W4-1~3 |
| ❌16 | 拆 736 行 _impl.py 時破壞既有 equivalence snapshot（74 fixture 必須維持綠）| Arch R-SD07-1-1 |

⚠️ **特別注意**：`autoclaude.execution._runner_internals` importlinter contract **持續保留為防復活柵欄**（SD_06 Migration Guide §7.2 明確；SD_07 不拔除）

---

## 7. 風險登記（新增 §13）

| 編號 | 描述 | 嚴重 | 對應 |
|------|------|------|------|
| **R-SD07-0-1** | Brain/Executor 缺 e2e 整合測試 | 🟠 | Arch 議題 0 |
| **R-SD07-0-2** | dry_run 模式 capabilities/on_event 未驗證 | 🟠 | SD 議題 0 |
| **R-SD07-1-1** | `steps_orchestrator/_impl.py` 736 LOC god-module 殘留 | 🔴 | Arch 議題 1 |
| **R-SD07-1-2** | 250 LOC 一刀切過嚴反致 SSOT 漂移 | 🟠 | SA 議題 1 |
| **R-SD07-1-3** | 250 LOC 對 orchestrator 過嚴 | 🟠 | SD 議題 1 |
| **R-SD07-5-1** | LOC violations=1 持續存在（13847 > 12904）| 🟠 | Arch 議題 6 |
| **R-SD07-W4-1** | _consecutive_compact_failures 9 處 patch path 遷移 | 🔴 | SD 延期項 |
| **R-SD07-W4-2** | _prepend_global_goal_brief 11 處 patch path 遷移 | 🔴 | SD 延期項 |
| **R-SD07-W4-3** | PlaybookResult → KernelResult 50+ assertion 升級 | 🔴 | Arch 延期項 |

---

## 8. CI / Quality Gates

### 8.1 PR-level（繼承 SD_06 + 新增）

| Gate | 命令 | 階段門檻 |
|------|------|--------|
| `lint-imports` | 6 kept / 0 broken（W5+ 新增 runner-no-checkpoint-logic 升級）| 🔴 全程阻塞 |
| `check_loc_budget.py` | 分級制下 violations=0 | 🔴 全程阻塞（W0+）|
| `tests/equivalence/` | 74/74 fixture 綠 | 🔴 全程阻塞 |
| `tests/contract/test_loc_budget_tiered.py` | ≥ 6 case 綠 | 🔴 W0+ 阻塞 |
| `tests/contract/test_plugin_walk_through.py` | ≥ 12 case 綠 | 🔴 W5+ 阻塞 |

### 8.2 G-gate

| Gate | 命令 | 階段門檻 |
|------|------|--------|
| 全測 | ≥ 1,802（SD_06 baseline；隨 sprint 增長至 ≥ 1,857）| 🔴 |
| coverage | ≥ 87%（新模組 ≥ 90%）| 🔴 |
| `tests/integration/test_brain_executor_e2e.py` | AC0-* 全綠（≥ 8 case）| 🔴 W2+ |
| `tests/integration/test_pgvector_real_recall.py` | recall@10 ≥ 0.95 + p95 < 50ms | 🔴 W2+ |

### 8.3 Nightly

| Gate | 命令 | 階段門檻 |
|------|------|--------|
| mutation test | TokenGuard / GoalSynthesis / Coordinator 三 SSOT ≥ 75% kill rate | 🟠 |
| pg performance | 1M 列 backfill / 並發 5 run 不退化 | 🟠 |

---

## 9. PM/Stakeholder 拍板事項

### 9.1 已拍板（沿用 SD_05 §10 + SD_06 §9）

PM 5 項拍板（嵌入 model / UI / RBAC / 多 run / KB 365 天）+ PM 8 項拍板（深度 / 三角色 / MAX_ACTIVE_RUNS / embed 最終一致 / re-embed batch / PII hybrid / Coordinator 雙層 / FK 1M dry-run）皆繼承。

### 9.2 SD_07 三方已決議事項（1 項）+ PM 待拍板事項（3 項）

#### 9.2.1 三方已決議（依使用者指示嚴正研究後決定，PM 僅需形式核准）

| # | 項目 | 三方共識決議 | 文件 |
|---|------|------------|------|
| **1** | **LOC 政策（取代 250 一刀切）** | ✅ **APPROVED（Arch / SA / SD 三方獨立研究 + 共識）**：取消 250 一刀切，改採**分級制**——資料 ≤ 150 / Plugin entry ≤ 250 / 純函數庫/Strategy ≤ 300 / Adapter/Repository ≤ 400 / Service/Orchestrator ≤ 500 / Contract/Assembly ≤ 400 / **絕對紅線 ≤ 750**；圈複雜度 nightly 輔助（≤ 10 函式 / 平均 ≤ 5），不阻塞 PR；既有 14 個違規檔，12 立即合規 + 3 個（`_impl.py` 736 / `pg_state_repository.py` 485 / `prompt_builder.py` 416）SD_07 W1 評估 | [ADR-SD07-001-loc-policy.md](ADR/ADR-SD07-001-loc-policy.md) v1.0 |

**研究方法論**：
- 業界對照：Linux Kernel / Google C++ / Robert C. Martin Clean Code / SonarQube / FxCop（共識：函式 ≤ 20-40 行比檔案 ≤ N 行更重要；檔案紅線通常 500-750）
- AutoClaude 實證：151 檔案 p50=84 / p75=151 / **p90=234**（250 已涵蓋 90%）/ p95=309 / max=736
- 認知負擔：人類短時記憶 7±2 chunk；強拆反致 SSOT 多源（SD_05 W3 checkpoint package 已驗證）

**取代規則**：
- 取代 SD_02 §3.1 R-3「per-file ≤ 250 LOC」
- 修訂 SD_05 §5 紅線 #4 / SD_06 §7 紅線 #4「超 250 必拆」為「超分級 budget 必拆」

#### 9.2.2 PM 拍板事項（✅ 2026-05-18 全數 APPROVED）

| # | 項目 | 三方建議 | **PM 決議** | 影響 / 後續行動 |
|---|------|---------|-----------|----------------|
| **2** | W2 真實 PG 整合測試啟用 | Architect 建議：CI matrix 加 PG service（不再 skip）| ✅ **採納啟用**（Docker PG 已就位，避免持續 skip 形成技術債）| W2 CI matrix 加 PG service；對 PG 測試 opt-in via marker（autouse=False）；nightly 跑完整 e2e |
| **3** | W4 PlaybookResult 物理拔除節奏 | SD 建議：W4 完整切換 50+ assertion；SA 建議：拆 SD_07/SD_08 兩 sprint | ✅ **採納 W4 一次切**（拆兩 sprint 反致過渡期延長 + patch 風險疊加；W4 PD 預留 6 含緩衝）| W4 風險集中；QA Q-2 強制 W4 開工前先 5 處 assertion dry-run 模擬；PM contingency 預留 2 PD 緩衝 |
| **4** | SD_07 啟動日 | 三方建議：SD_06 W6 後 ≥ 1 自然日穩定期 | ✅ **2026-05-20**（SD_06 W6 已 2026-05-18 通過 + 1 自然日穩定期已過；沿用個人開發場景 A，無 production smoke 需求）| 2026-05-19 EOD 前 Tech Lead 確認 SD_06 commit 穩定 + tag sd_06_w6_g6_pass；2026-05-20 G0 Kickoff |

### 9.3 QA 強制警示

| # | 警示 | 對 PM 建議 |
|---|------|-----------|
| Q-1 | W1 拆解 736 行同時破壞 equivalence 74 fixture 風險高 | 拆解前必先 git tag + W1 末強制 equivalence 全綠 |
| Q-2 | W4 三項物理拔除為 SD_07 單點失效；50+ assertion 升級若失敗將整個 W4 卡死 | W4 開工前先 dry-run 模擬 5 處 assertion 升級驗證可行性 |
| Q-3 | LOC 政策調整若不更新 tools/check_loc_budget.py 將失去 CI guard | W0 同步更新工具 + 加 tests/contract/test_loc_budget_tiered.py |
| Q-4 | token_guard 拆 5 子模組會影響 SD_06 W5 已就位的 plugin coverage 100% | W3 開工前先量 baseline coverage，W3 末強制驗證不下降 |

---

## 10. 回退策略（繼承 SD_06 §11 + 新增 3 條）

| 觸發條件 | 立即執行 |
|---------|---------|
| W1 拆解破壞 equivalence 74 fixture | `git revert HEAD`；找 Architect + QA 雙簽 |
| W4 patch path 遷移漏改造成 false green | `git stash`；找 SA + QA 雙簽逐處比對 |
| W5 runner-no-checkpoint-logic contract broken | `git stash`；找 Architect 確認 EventBus 路徑 |
| LOC 政策調整後 violations 暴增 | 凍結 W1+，回 W0 重新校準 baseline |

---

## 11. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | 三方審查共識初版：Architect / SA / SD 獨立審查 6 大議題完整性 + LOC 政策 + 736 行新肥胖檔案 + SD_06 NOTE(SD_07) 延期項；7 Wave / 28 PD / 4 PM 待拍板 / 9 風險條目 / QA 四方審議 APPROVED_WITH_CONDITIONS（Q-1~Q-4 已補強）|
| **v1.1** | 2026-05-18 | **PM 4 項拍板 APPROVED + G0 啟動日鎖定 2026-05-20**：(#1) LOC 政策（ADR-SD07-001）形式核准；(#2) W2 真實 PG 整合測試**啟用**（CI matrix 加 PG service + opt-in marker + nightly e2e）；(#3) W4 PlaybookResult 物理拔除**採納一次切**（拆兩 sprint 反致過渡期延長 + patch 風險疊加；W4 PD 預留 6 含緩衝 + QA Q-2 強制 dry-run 模擬 + PM contingency 2 PD）；(#4) SD_07 啟動日**鎖定 2026-05-20**（SD_06 W6 已通過 + 1 自然日穩定期已過，沿用個人開發場景 A）；新增 [SD07_Execution_Guide.md](../05_development/SD07_Execution_Guide.md) + risk_log.md §13（10 風險條目 + 4 PM 拍板連動）+ gate_audit.md §1-quinquies（G0~G6 簽核表 + PM 拍板事項）|

---

## 12. 簽核狀態

| 角色 | 狀態 | 備註 |
|------|------|------|
| Architect | ✅ 三方審查 APPROVED | 議題 1/5/6 主導 + ADR-SD07-001 業界對照支持分級制；2026-05-18 |
| SA | ✅ 三方審查 APPROVED | 議題 1/3/6 LOC 分級提案（職責分類）+ Q-1~Q-4 補強；2026-05-18 |
| SD | ✅ 三方審查 APPROVED | 議題 0/4 + W4 延期項主導 + ADR W0 工具升級可執行性；2026-05-18 |
| QA | ✅ 四方審議 APPROVED_WITH_CONDITIONS | Q-1~Q-4 已補強至 v1.0；2026-05-18 |
| **PM** | ✅ **4 項拍板 APPROVED** | #1 LOC 政策形式核准 + #2 真實 PG 啟用 + #3 W4 一次切 + #4 啟動日 2026-05-20；2026-05-18 |

**G0 啟動 DoD**（PM 鎖定 / W6 末已全部完成）：
- ✅ 2026-05-19 EOD 前：Tech Lead 提交 W0 task breakdown（含分級 LOC budget table 設計）
- ✅ 2026-05-19 EOD 前：Architect 草擬 tools/check_loc_budget.py 升級規範（依 ADR-SD07-001 §5.1）
- ✅ 2026-05-19 EOD 前：確認 SD_06 W6 G6 commit 已 tag 為 sd_06_w6_g6_pass
- ✅ 2026-05-20：G0 Kickoff

> **W6 補述 (2026-05-18)**：v1.0 早期版本曾有一段「**G0 啟動 DoD（待 PM 簽核）**」TODO 段落（含 PM 4 項拍板 / Tech Lead breakdown / Architect ADR 三條），與 v1.1 頂部 §0 PM ✅ APPROVED + §12 G0 DoD 已完成矛盾。**W6 G6 修復時整段刪除**，避免後續 reviewer 混淆。

---

**對應參考文件**：
- [SD_Improving_06.md](SD_Improving_06.md) v1.2 — 前置 sprint
- [SD06_Migration_Guide.md](../08_deployment/SD06_Migration_Guide.md) v1.0 §5 §7 — SD_07 延期清單來源
- [SD06_Execution_Guide.md](../05_development/SD06_Execution_Guide.md) — 執行協議範本
- [risk_log.md](../05_development/risk_log.md) §13（待新增）— SD_07 風險條目
- [gate_audit.md](../05_development/gate_audit.md) §1-quinquies（待新增）— SD_07 Gates
