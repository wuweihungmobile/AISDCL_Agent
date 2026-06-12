# SD_Improving_07 Acceptance Criteria Matrix（W0~W6 完整回填）

> **最後更新**：2026-05-18 W6 G6 末（含 W1 / W2 / W4 / W5 各 Gate 實測回填）

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.1（W0 scaffolding + W1/W2/W4/W5/W6 實測回填；AC4-1/AC4-2 改為 nightly pending）|
| 建立日期 | 2026-05-18 |
| 對應規劃 | [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.1 / [SD07_Execution_Guide.md](../05_development/SD07_Execution_Guide.md) v1.0 |
| AC 條目數 | 19 條（AC0×3 + AC1×3 + AC2×2 + AC3×2 + AC4×2 + AC5×3 + AC6×3 + AC-LOC×1 ≥ 18 門檻）|
| W2 G2 量測（2026-05-18）| **AC0 全綠**（test_brain_executor_e2e.py 10 case）/ **AC3 全綠**（test_three_tier_crud_e2e.py 21 case）/ **AC4 條件 skip**（pg_real marker；nightly CI 啟用）/ **AC5 全綠**（test_multi_run_resume_e2e.py 10 case）/ **AC6 全綠**（test_config_resolver_hierarchy_e2e.py 14 case + Hypothesis 50 example）/ G2 全測 **1,893 passed / 121 skipped**（+56 vs G1）|
| W4 G4 量測（2026-05-18）| **SD_06 §5 三項物理拔除完成**（紅線 ❌15 強制順序遵守）：_consecutive_compact_failures property/setter 拔除（5 處 patch path 遷移 plugin SSOT）/ _prepend_global_goal_brief shim 拔除（4 處 test + 1 處內部使用遷移 GoalSynthesisPlugin SSOT）/ PlaybookResult class 拔除（factory function + property alias 路線，零 caller 改動 + to_kernel_result helper 隨之刪除）；**NOTE(SD_07) 殘留 = 0** ✅；G4 全測 **1,953 passed / 121 skipped**（淨 -1 為 backward compat 保護網 test 移除預期）；equivalence 83/83；LOC violations=0（playbook_runner.py 440→394 -46 行；types.py 258→247 -11 行）|

---

## 1. 議題對應與覆蓋表

| 議題 | AC 編號 | Wave | 阻塞門 |
|------|---------|------|--------|
| #0 Minimax/Claude Code 分工 | AC0-1~AC0-3 | W2 | G2 |
| #1 肥胖檔案拆解 | AC1-1~AC1-3 | W1 | G1 |
| #2 Plugin 架構合規 | AC2-1~AC2-2 | W5 | G5 |
| #3 PG 三層任務模型 | AC3-1~AC3-2 | W2 | G2 |
| #4 向量檢索 | AC4-1~AC4-2 | W2 | G2 |
| #5 狀態保存恢復 | AC5-1~AC5-3 | W2 | G2 |
| #6 ConfigResolver | AC6-1~AC6-3 | W2 | G2 |
| LOC 政策（橫切）| AC-LOC-1 | W0~W6 | 全程 |

---

## 2. AC 詳表

### AC0：Brain/Executor 完美協作（議題 #0 / Wave W2）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC0-1** | Token Halt → Coordinator → CheckpointPlugin → AutoResumeService 完整往返；scheduled_resume_at 正確設定，wake_kinds 累計 `token_halt` 1 次 | `pytest tests/integration/test_brain_executor_e2e.py::test_token_halt_round_trip -v` | 1 case 綠 + AutoResumeMetrics.snapshot()['wake_kinds'] 含 'token_halt' | **W2 G2 ✅ 2026-05-18** |
| **AC0-2** | Minimax decide_correction → ExecutorPort.execute(on_event) → ON_EVENT phase 廣播 → Coordinator 接收 | `pytest tests/integration/test_brain_executor_e2e.py::test_decide_correction_on_event -v` | 1 case 綠 + ON_EVENT phase 在 EventBus phase_failure_counts 為 0 | **W2 G2 ✅ 2026-05-18** |
| **AC0-3** | send_interrupt ACK + seq number 嚴格遞增；ESC+F12 中斷觸發 ExecutionEvent.INTERRUPTED → CheckpointPlugin 儲存 → restart | `pytest tests/integration/test_brain_executor_e2e.py::test_send_interrupt_ack_and_restart -v` | 1 case 綠 + interrupt_seq 嚴格遞增；checkpoint round-trip 不損失欄位 | **W2 G2 ✅ 2026-05-18** |

### AC1：肥胖檔案拆解（議題 #1 / Wave W1）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC1-1** | `_impl.py` count_loc ≤ 500（service tier budget）| `python -c "from tools.check_loc_budget import count_loc; from pathlib import Path; assert count_loc(Path('autoclaude/execution/steps_orchestrator/_impl.py')) <= 500"` | exit 0 | **W1 G1 ✅ 2026-05-18** — `_impl.py` 530 wc-l / 邏輯行 ≤ 500（service tier 達標）；抽 2 strategy 子模組（_escalation_handler 302 LOC + _correction_helpers 185 LOC）|
| **AC1-2** | equivalence snapshot 74 fixture 全綠（拆解過程不破壞）| `pytest tests/equivalence/ -q --tb=no` | `74 passed`（紅線 ❌16）| **W1 G1 ✅ 2026-05-18** — equivalence 9 case 全綠（test_steps_orchestrator_decomposition.py）；74 fixture baseline 維持 |
| **AC1-3** | importlinter 維持 5 kept / 0 broken | `PYTHONUTF8=1 lint-imports --config .importlinter` | `5 kept, 0 broken` | **W1 G1 ✅ 2026-05-18** — 5 kept / 0 broken（W5 升 6 kept）|

### AC2：Plugin 架構合規（議題 #2 / Wave W5）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC2-1** | 12 個 Plugin walk-through 完成；無 plugin-to-plugin import；無直接 import infra | `pytest tests/contract/test_plugin_walk_through.py -v` | ≥ 12 case 綠 | **W5 G5 ✅ 2026-05-18** — 14 Plugin walk-through 59 case 全綠（SD_06 W6 12 + SD_05 W4 補 FastPath/PlaybookPersistence）|
| **AC2-2** | `runner-no-checkpoint-logic` contract 升級至 importlinter 原生 forbidden contract | `PYTHONUTF8=1 lint-imports --config .importlinter` | `6 kept, 0 broken` | **W5 G5 ✅ 2026-05-18** — Rule 6 升級 importlinter 原生 forbidden contract；6 kept / 0 broken |

### AC3：PG 三層任務模型 CRUD（議題 #3 / Wave W2）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC3-1** | projects / goal_tasks / execution_items CRUD + RBAC（admin/dev/viewer 矩陣）；違反必 `PermissionError` 或 403 | `pytest tests/integration/test_three_tier_crud_e2e.py::test_rbac_matrix -v` | ≥ 3 角色 × 3 表 = 9 sub-case 綠 | **W2 G2 ✅ 2026-05-18** |
| **AC3-2** | goal_tasks 樹狀深度 1/2/3 接受；深度 4 必 reject（PM #5 拍板）| `pytest tests/integration/test_three_tier_crud_e2e.py::test_depth_constraint -v` | 深度 4 觸發 `ValueError`/`DepthLimitError` | **W2 G2 ✅ 2026-05-18** |

### AC4：向量檢索（議題 #4 / Wave W2 / **PM #2 啟用真實 PG**）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC4-1** | recall@10 ≥ 0.95（100 query × BGE-M3 真實 embedding）| `SD07_REAL_PG_E2E_ENABLED=true pytest tests/integration/test_pgvector_real_recall.py::test_recall_at_10 -v` | recall ≥ 0.95 | **⏳ nightly pending**（pg_real marker；local default skip / nightly CI 啟用後填；W2 G2 僅 1 PASSED 為 CircuitBreaker 純單元測試，**非真實 pgvector recall**）|
| **AC4-2** | p95 latency < 50ms（HNSW m=16, ef_construction=64）| `SD07_REAL_PG_E2E_ENABLED=true pytest tests/integration/test_pgvector_real_recall.py::test_p95_latency -v` | p95 < 50ms | **⏳ nightly pending**（pg_real marker；local default skip / nightly CI 啟用後填；W2 G2 僅 1 PASSED 為 CircuitBreaker 純單元測試，**非真實 pgvector latency**）|

### AC5：狀態保存恢復（議題 #5 / Wave W2）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC5-1** | 5 run × 同 GoalTask 並存；abort(run_id) 互不干擾；MAX_ACTIVE_RUNS_PER_GOAL=5 guard 觸發 | `pytest tests/integration/test_multi_run_resume_e2e.py::test_concurrent_runs -v` | 5 並存綠；第 6 run 觸發 enqueue | **W2 G2 ✅ 2026-05-18** |
| **AC5-2** | SIGINT → checkpoint ≤ 2s → restart 從正確 step（不重做、不跳過）| `pytest tests/integration/test_multi_run_resume_e2e.py::test_sigint_checkpoint_under_2s -v` | checkpoint 寫入 latency < 2s | **W2 G2 ✅ 2026-05-18** |
| **AC5-3** | dual_state drift 全欄比對（datetime ISO UTC / UUID str / Enum value / set 排序 list）| `pytest tests/integration/test_multi_run_resume_e2e.py::test_dual_state_drift_normalize -v` | 0 false positive；4 種類型正規化 | **W2 G2 ✅ 2026-05-18** |

### AC6：ConfigResolver 階層（議題 #6 / Wave W2）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC6-1** | 4 層 merge（global → workflow → step → runtime）property-based；Hypothesis ≥ 50 example | `pytest tests/integration/test_config_resolver_hierarchy_e2e.py::test_four_layer_merge -v` | Hypothesis 通過；merge 結合律 + 結合性 | **W2 G2 ✅ 2026-05-18** |
| **AC6-2** | flat → nested promote + DeprecationWarning 觸發 | `pytest tests/integration/test_config_resolver_hierarchy_e2e.py::test_flat_to_nested_promote -v` | 1 case 綠 + warning catch | **W2 G2 ✅ 2026-05-18** |
| **AC6-3** | RBAC 保護欄位（minimax.api_key / embedder.api_key / storage.db_dsn）runtime 層 override 必 raise `ProtectedFieldError` + audit_log 寫入 | `pytest tests/integration/test_config_resolver_hierarchy_e2e.py::test_protected_field_audit -v` | 3 protected fields × 1 case = 3 sub-case 綠 + config_audit_log 行數 = 3 | **W2 G2 ✅ 2026-05-18** |

### AC-LOC：分級 LOC 政策橫切（W0~W6 全程）

| # | 描述 | 量測命令 | 通過門檻 | 實測 |
|---|------|---------|----------|------|
| **AC-LOC-1** | 分級表生效；絕對紅線 750；override 機制可控管；total cap 不破 | `python tools/check_loc_budget.py && pytest tests/contract/test_loc_budget_tiered.py -v` | violations ≤ 3（W0）→ 0（W1+）；contract ≥ 6 case 綠 | W0：1 tier violation（_impl.py 682；W1 處理）、test 26 case 綠 ✅ |

---

## 3. 阻塞 / 非阻塞 規則

| 嚴重度 | 行為 |
|--------|------|
| 🔴 阻塞 | Critical AC 任一 fail → 對應 Gate 不放行（git revert） |
| 🟠 警示 | nightly 圈複雜度警告 ≤ 10 / 平均 ≤ 5 不阻塞 PR（ADR-SD07-001 §4.3） |

**Critical AC**：AC0-* / AC1-* / AC3-* / AC4-* / AC5-* / AC6-* / AC-LOC-1（全部）

---

## 4. 維護規則

1. 每個 Wave G-Gate 通過後，在「實測」欄填入結果（`✅ passed (數字)` 或 `⚠️ 部分通過`）
2. 新增 AC 須附量測命令 + 門檻 + 對應 Gate
3. AC 與 [risk_log.md §13](../05_development/risk_log.md) 雙向映射（risk → mitigation AC）

---

## 5. 對應參考文件

- [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.1 — Sprint 規劃
- [SD07_Execution_Guide.md](../05_development/SD07_Execution_Guide.md) v1.0 — Wave 執行協議
- [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 — LOC 分級政策
- [risk_log.md](../05_development/risk_log.md) §13 — SD_07 風險條目
- [gate_audit.md](../05_development/gate_audit.md) §1-quinquies — Gate 簽核
