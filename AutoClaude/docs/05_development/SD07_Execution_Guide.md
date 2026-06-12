# SD_Improving_07 嚴格執行大綱（Opus 4.7 操作指南）

| 項目 | 內容 |
|------|------|
| 目標文件 | [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.0（PM 4 項拍板 APPROVED 2026-05-18）|
| 執行基線 | 1,802 passed / 118 skipped（SD_06 W6 G6 末，2026-05-18 確認）|
| 預估終線 | W6 末 ≥ 1,857 passed（QA 估算 +55 case）|
| 執行模型 | Claude Opus 4.7（標準模式，**不要用 /fast**） |
| 總範圍 | 28 PD / 7 Wave / +2 PD contingency |
| G0 啟動日 | **2026-05-20（週三）** |
| 建立日期 | 2026-05-18 |

---

## 0. G0 啟動前置 DoD（2026-05-19 EOD 前必完成）

```
[  ] Tech Lead 提交 W0 task breakdown（含分級 LOC budget table 設計）
[  ] Architect 草擬 tools/check_loc_budget.py 升級規範（依 ADR-SD07-001 §5.1）
[  ] 確認 git branch 已切至 sprint/sd_07_phase8（或沿用 sprint/sd_06_phase7）
[  ] 確認 SD_06 W6 G6 commit 已 tag 為 sd_06_w6_g6_pass
```

每次開啟新 session 前必跑：

```bash
# 1. 測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1,802 passed / 118 skipped

# 2. importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：5 kept / 0 broken（W5 後 6 kept）

# 3. LOC 預算（W0 升級分級制後）
python tools/check_loc_budget.py
# W0 前：violations=1（13847 > 12904）
# W0 後（分級制）：violations 預期 ≤ 3（_impl.py 736 / pg_state 485 / prompt_builder 416）
# W1 末：violations=0

# 4. 關鍵檔案 LOC（追蹤拆解進度）
wc -l autoclaude/execution/steps_orchestrator/_impl.py \
      autoclaude/execution/playbook_runner.py \
      autoclaude/plugins/token_guard_plugin.py
# W0 起點：736 / 440 / 20
# W1 末：≤ 500 / 440 / 20
# W3 末：≤ 500 / 440 / 拆 5 子模組

# 5. NOTE(SD_07) 殘留
grep -rn "NOTE(SD_07)" autoclaude/ tests/ | wc -l
# W0 起點：≥ 2
# W4 末：0
```

---

## 1. 全程絕對規則（違反即停止）

```
[  ] 每完成一個函式群搬移 → 立即跑全測，全綠才繼續
[  ] equivalence snapshot 74 fixture 任一斷裂 → 立刻停止，不得繞過
[  ] importlinter 出現 broken → 立刻停止並還原
[  ] LOC 超分級 budget → 立刻拆 package 或在 .loc-budget.toml 加 override（雙簽）
[  ] Plugin 不可互相 import；只能透過 EventBus 溝通
[  ] W4 三項物理拔除順序不可顛倒（先 _consecutive_compact_failures → 再 _prepend_global_goal_brief → 最後 PlaybookResult）
[  ] _runner_internals importlinter contract 為防復活柵欄，不得拔除
[  ] 拆 _impl.py 736 行時，每搬 100 LOC 必跑 equivalence 74 fixture
```

---

## 2. 架構紅線（繼承 SD_06 §7 + 新增 3 條，共 16 條）

繼承 SD_06 §7 全部 13 條 + SD_07 新增 3 條：

| # | 禁止行為 |
|---|---------|
| ❌1~❌13 | （繼承 SD_06 §7）|
| ❌14 | 250 LOC 一刀切（取代為 ADR-SD07-001 分級政策；超過分級 budget 必拆 package 或書面例外）|
| ❌15 | W4 三項物理拔除順序顛倒（必須先 _consecutive_compact_failures → _prepend_global_goal_brief → PlaybookResult）|
| ❌16 | 拆 736 行 _impl.py 時破壞既有 equivalence snapshot（74 fixture 必須維持綠）|

⚠️ **`autoclaude.execution._runner_internals` importlinter contract 持續保留為防復活柵欄**（SD_06 Migration Guide §7.2；SD_07 不拔除）

---

## 3. Wave 執行協議

### ── W0：ADR 落地 + 工具升級 + AC scaffolding（3 PD）──

**目標**：
- ADR-SD07-001（規劃階段已完成）落地為可執行工具
- `tools/check_loc_budget.py` 升級為分級判定
- `.loc-budget.toml` per-file overrides 配置
- 重新校準 baseline + 補 contract test
- SD_07 AC Matrix scaffolding（≥ 18 條）

**逐項打勾**：
```
[✅] T0-1 ADR-SD07-001-loc-policy.md（規劃階段已完成 2026-05-18，三方共識 + PM 形式核准）
[  ] T0-2 升級 tools/check_loc_budget.py（LOC_TIERS table + per-file 分級判定，依 ADR §5.1）
[  ] T0-3 新建 .loc-budget.toml（per-file overrides 配置 + 書面理由欄位，依 ADR §5.2）
[  ] T0-4 重新測算 baseline（吸收 SD_06 W3 alembic 0007-0014 + adapter 永久增量）
[  ] T0-5 補 tests/contract/test_loc_budget_tiered.py（≥ 6 case：各分級邊界 + override 機制 + 750 絕對紅線）
[  ] T0-6 SD_07 AC Matrix scaffolding（≥ 18 條 AC：AC0×3 議題0 / AC1×3 議題1 / AC2×2 議題2 / AC3×2 議題3 / AC4×2 議題4 / AC5×3 議題5 / AC6×3 議題6）
[  ] T0-7 補 tests/integration/fixtures/sd07_e2e_samples/（5 種 Brain/Executor 失敗情境 fixture）
[  ] T0-8 .env.example 補 LOC_BUDGET_POLICY_VERSION=v2 + SD07_REAL_PG_E2E_ENABLED=true（PM #2）
[  ] T0-9 撰寫 SD07_Execution_Guide.md（本文件，依 SD_06 範本）
```

**G0 驗證**：
```bash
[  ] python tools/check_loc_budget.py                                      # 分級制下 violations ≤ 3
[  ] python -m pytest tests/contract/test_loc_budget_tiered.py -v          # ≥ 6 case 綠
[  ] cat .loc-budget.toml | grep "^\[overrides\]"                          # 存在
[  ] ls docs/04_planning/ADR/ADR-SD07-001-loc-policy.md                    # 存在 + 三方+PM 簽名
[  ] python -m pytest tests/ -q --tb=no | tail -3                          # ≥ 1,808 passed（+6 W0 新測）
[  ] grep "LOC_BUDGET_POLICY_VERSION\|SD07_REAL_PG_E2E_ENABLED" .env.example  # 兩行
```

**G0 通過條件**：分級制工具就位 + baseline 校準 + AC scaffolding 18 條 + Execution Guide 存檔

---

### ── W1：`steps_orchestrator/_impl.py` 736 行拆解（6 PD）──

**目標**：依 ADR-SD07-001 政策（Orchestrator ≤ 500 LOC）拆 736 → 多子模組

**逐項打勾**：
```
[  ] T1-1 git tag sd_07_w0_g0_pass（W1 拆解前快照，QA Q-1 強制要求）
[  ] T1-2 盤點 _impl.py 函式群（grep `def ` + 行數區段標記 + 共享 local variable map）
[  ] T1-3 制定拆分計畫（依職責，建議方向）：
      - _impl.py 保留主 _run_steps 編排骨架（≤ 500 LOC orchestrator budget）
      - _step_dispatcher.py（步驟分派 + GOTO/SKIP/INJECT 分支，≤ 300 LOC strategy）
      - _attempt_loop.py（單步重試迴圈 + state machine，≤ 300 LOC）
      - _evaluation.py（regex + evaluator_command 評估，≤ 200 LOC）
      - _state_transitions.py（attempt → result → mutation 狀態機，≤ 200 LOC）
[  ] T1-4 逐函式群搬移（每搬 50-100 LOC 立即跑全測 + equivalence 74 fixture）
[  ] T1-5 重複 T1-4 直到 _impl.py ≤ 500 LOC
[  ] T1-6 補 tests/equivalence/test_steps_orchestrator_decomposition.py（拆解前後行為等價，≥ 8 case）
[  ] T1-7 評估 pg_state_repository.py 485 LOC（Adapter ≤ 400 budget 超 85 LOC）：
      - (a) 拆 _read_path.py + _write_path.py 兩子模組；或
      - (b) .loc-budget.toml 加 override 並書面理由（PG schema 複雜度天然較重）
[  ] T1-8 評估 prompt_builder.py 416 LOC（純函數庫 ≤ 300 budget 超 116 LOC）：
      - (a) 拆 _correction.py + _compact.py + _global_goal.py 三純函式檔；或
      - (b) .loc-budget.toml 加 override（純函式集中可讀性高於分散）
```

**G1 驗證**：
```bash
[  ] wc -l autoclaude/execution/steps_orchestrator/_impl.py            # ≤ 500
[  ] wc -l autoclaude/execution/steps_orchestrator/*.py                 # 每子模組 ≤ 政策 budget
[  ] python tools/check_loc_budget.py                                   # violations=0
[  ] python -m pytest tests/ -q --tb=no | tail -3                       # ≥ 1,810 passed（不下降）
[  ] python -m pytest tests/equivalence/ -q --tb=no                     # 74/74 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                   # 5 kept / 0 broken
[  ] python -m pytest tests/equivalence/test_steps_orchestrator_decomposition.py -v   # ≥ 8 case 綠
```

---

### ── W2：6 大議題 e2e 整合測試（4 PD）──

**目標**：補強 SD_06 單元測試外的端對端整合測試，含 PM #2 真實 PG 啟用

**逐項打勾**：
```
[  ] T2-1 tests/integration/test_brain_executor_e2e.py（議題 0，≥ 8 case）：
      - Token Halt → Coordinator → CheckpointPlugin → AutoResumeService 往返
      - ESC+F12 中斷 → send_interrupt → CheckpointPlugin → restart
      - Minimax decide_correction → ExecutorPort.execute(on_event) → ON_EVENT phase
      - decide_escalation → EvolutionPlugin → ON_ESCALATION_DUMP_REQUEST
      - dry_run 模式完整 phase 序驗證
      - capabilities() 單次呼叫 + cache
      - send_interrupt ACK + seq number 序列化
      - Brain/Executor isolation callback 來源驗證
[  ] T2-2 tests/integration/test_three_tier_crud_e2e.py（議題 3，≥ 6 case）：
      - projects CRUD + RBAC（admin/dev/viewer 三角色矩陣）
      - goal_tasks 樹狀（深度 1/2/3）+ 深度 4 必 reject
      - execution_items + FK CASCADE
      - abort_run(run_id) 互不干擾
      - config_snapshot JSONB 凍結驗證
      - 5 個並存 run × 同 GoalTask
[  ] T2-3 tests/integration/test_pgvector_real_recall.py（議題 4，≥ 3 case，**PM #2 啟用真實 PG**）：
      - recall@10 ≥ 0.95（100 query × BGE-M3 真實 embedding）
      - p95 latency < 50ms
      - 雙 adapter fallback < 60s RTO（BGE 故障 → Minimax 切換）
[  ] T2-4 tests/integration/test_multi_run_resume_e2e.py（議題 5，≥ 5 case）：
      - 5 run × 同 GoalTask 並存 × abort 互不干擾
      - SIGINT → checkpoint ≤ 2s → restart 從正確 step
      - dual_state drift 全欄比對（datetime/UUID/Enum normalize）
      - run_id 過濾 vs playbook_id fallback
      - PG-first dual-write + reconcile queue
[  ] T2-5 tests/integration/test_config_resolver_hierarchy_e2e.py（議題 6，≥ 8 case）：
      - 4 層 merge property-based（Hypothesis ≥ 50 example）
      - flat → nested promote + DeprecationWarning
      - RBAC 保護欄位（api_key）runtime override 必 403
      - hot-reload smoke（SIGHUP 或 API trigger）
      - audit_log 寫入驗證
[  ] T2-6 CI matrix 補 PG service（GitHub Actions / docker-compose-test.yml，PM #2）
[  ] T2-7 補 tests/conftest.py PG fixture（autouse=False，opt-in via marker）
```

**G2 驗證**：
```bash
[  ] python -m pytest tests/integration/test_brain_executor_e2e.py -v        # ≥ 8 case 綠
[  ] python -m pytest tests/integration/test_three_tier_crud_e2e.py -v       # ≥ 6 case 綠
[  ] python -m pytest tests/integration/test_pgvector_real_recall.py -v      # recall ≥ 0.95 + p95 < 50ms
[  ] python -m pytest tests/integration/test_multi_run_resume_e2e.py -v      # ≥ 5 case 綠
[  ] python -m pytest tests/integration/test_config_resolver_hierarchy_e2e.py -v   # ≥ 8 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                            # ≥ 1,840 passed（+30）
```

---

### ── W3：`token_guard_plugin` 拆 5 子模組（3 PD）──

**目標**：SD_06 §7.3 延期項

**逐項打勾**：
```
[  ] T3-1 git tag sd_07_w2_g2_pass（W3 拆解前快照 + coverage baseline 量測，QA Q-4）
[  ] T3-2 新建 autoclaude/plugins/token_guard/ package（沿用 SD_06 W2 命名）
[  ] T3-3 watcher.py（token 使用率偵測 + 7 regex pattern，≤ 100 LOC）
[  ] T3-4 compactor.py（/compact 觸發 + prompt 構造 + 結果處理，≤ 100 LOC）
[  ] T3-5 thresholds.py（dynamic threshold + per-step override 解析，≤ 80 LOC）
[  ] T3-6 git_verifier.py（_verify_correction_applied git diff 部分，≤ 60 LOC）
[  ] T3-7 policy.py（IHookResult emit + compact_failure_count 管理，≤ 100 LOC）
[  ] T3-8 plugin.py（TokenGuardPlugin 主類別 + 依賴注入 5 子模組，≤ 150 LOC，分級為 Plugin entry ≤ 250）
[  ] T3-9 token_guard_plugin.py shim 更新（re-export 維持 backward compat）
[  ] T3-10 補 tests/plugins/token_guard/test_*.py（每子模組 ≥ 5 case，coverage ≥ 90%）
[  ] T3-11 比較 W3 baseline vs W3 末 coverage 不下降（QA Q-4 強制）
```

**G3 驗證**：
```bash
[  ] ls autoclaude/plugins/token_guard/*.py | wc -l                       # ≥ 5（+ __init__）
[  ] wc -l autoclaude/plugins/token_guard/*.py                            # 每檔 ≤ 政策 budget
[  ] python tools/check_loc_budget.py                                     # violations=0
[  ] python -m pytest tests/plugins/token_guard/ -v                       # ≥ 25 case 綠
[  ] python -m coverage report --include="autoclaude/plugins/token_guard/*"  # ≥ 90%
[  ] python -m pytest tests/ -q --tb=no | tail -3                         # ≥ 1,865 passed（+25）
```

---

### ── W4：SD_07 延期清單物理拔除（6 PD）──

**目標**：SD_06 Migration Guide §5 三項物理拔除（PM #3 拍板 W4 一次切）

⚠️ **強制順序**（紅線 ❌15）：
1. 先拔 `_consecutive_compact_failures`（9 patch path 遷移）
2. 再拔 `_prepend_global_goal_brief`（11 patch path 遷移）
3. 最後完整切換 PlaybookResult → KernelResult（50+ assertion 升級）

**QA Q-2 強制前置**：W4 開工前先 dry-run 模擬 5 處 assertion 升級驗證可行性

**逐項打勾**：
```
[  ] T4-0 W4 dry-run 模擬：選 5 處 assertion 試升級 → 確認 to_kernel_result() helper 可行（QA Q-2）

# 第一步：_consecutive_compact_failures
[  ] T4-1 grep -rn "_consecutive_compact_failures" tests/ → 盤點 9 處 patch path
[  ] T4-2 9 處 patch path 改 patch TokenGuardPlugin.compact_failure_count（plugin SSOT）
[  ] T4-3 跑全測 + grep 確認 0 residual reference
[  ] T4-4 物理拔除 playbook_runner.py:141-170 property + setter

# 第二步：_prepend_global_goal_brief
[  ] T4-5 grep -rn "_prepend_global_goal_brief" tests/ → 盤點 11 處 patch path
[  ] T4-6 11 處 patch path 改 patch GoalSynthesisPlugin.prepend_global_goal_brief
[  ] T4-7 跑全測 + grep 確認 0 residual reference
[  ] T4-8 物理拔除 playbook_runner.py:222-230 shim

# 第三步：PlaybookResult → KernelResult
[  ] T4-9 grep -rn "PlaybookResult" autoclaude/ tests/ → 盤點 50+ 處 assertion
[  ] T4-10 升級策略：PlaybookRunner.run() 改回傳 KernelResult；對 PlaybookResult 既有 assertion 用 to_kernel_result() 包裝
[  ] T4-11 50+ assertion 逐處升級（每 10 處跑全測一次）
[  ] T4-12 確認 main.py + tests/ 完全無 PlaybookResult 引用
[  ] T4-13 物理拔除 autoclaude/execution/types.py 中的 PlaybookResult class
[  ] T4-14 物理拔除 to_kernel_result() helper（PlaybookResult 已不存在）
[  ] T4-15 grep "NOTE(SD_07)" autoclaude/ tests/ 必須 = 0
```

**G4 驗證**：
```bash
[  ] grep -rn "_consecutive_compact_failures" autoclaude/execution/playbook_runner.py | wc -l   # = 0
[  ] grep -rn "_prepend_global_goal_brief" autoclaude/execution/playbook_runner.py | wc -l      # = 0
[  ] grep -rn "class PlaybookResult" autoclaude/execution/types.py | wc -l                      # = 0
[  ] grep -rn "PlaybookResult" autoclaude/ tests/ | wc -l                                       # ≤ 5（含註釋）
[  ] grep -rn "NOTE(SD_07)" autoclaude/ tests/ | wc -l                                          # = 0
[  ] python -m pytest tests/ -q --tb=no | tail -3                                               # ≥ 1,865 passed（不下降）
[  ] python -m pytest tests/equivalence/ -q --tb=no                                             # 74/74 全綠
```

**⚠️ G4 強制阻塞**：紅線 ❌15 違反 → G4 不放行 + git revert HEAD

---

### ── W5：Plugin 架構合規性審計 + LOC baseline 鎖定（3 PD）──

**目標**：
- 12 個 Plugin walk-through 審計
- `runner-no-checkpoint-logic` contract 升級至 importlinter 原生
- LOC baseline 永久鎖定

**逐項打勾**：
```
[  ] T5-1 撰寫 docs/06_quality/SD07_Plugin_Audit_Report.md：
      - 12 個 Plugin 公開 API + hook subscribe 矩陣
      - 確認無 plugin-to-plugin import（importlinter 5 kept 驗證）
      - 確認無直接 import infra（建構式注入驗證）
      - 確認每 Plugin coverage ≥ 80%
[  ] T5-2 .importlinter 升級 runner-no-checkpoint-logic：
      - 從 tests/contract/test_runner_no_checkpoint_logic.py（grep-based）
      - 升級為 importlinter 原生 forbidden contract
[  ] T5-3 lint-imports 期望 6 kept / 0 broken
[  ] T5-4 校準 tools/check_loc_budget.py baseline（執行 SD_07 末總 LOC，永久鎖定）
[  ] T5-5 補 tests/contract/test_plugin_walk_through.py（≥ 12 case：每 Plugin 一條 isolation 檢查）
[  ] T5-6 補 nightly mutation test 設定（TokenGuard / GoalSynthesis / Coordinator 三 SSOT ≥ 75% kill rate）
```

**G5 驗證**：
```bash
[  ] ls docs/06_quality/SD07_Plugin_Audit_Report.md                         # 存在
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 6 kept / 0 broken
[  ] python tools/check_loc_budget.py                                       # violations=0（新 baseline）
[  ] python -m pytest tests/contract/test_plugin_walk_through.py -v         # ≥ 12 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 1,877 passed（+12）
```

---

### ── W6：收尾 + Migration Guide + 四方審查（3 PD）──

**目標**：
- 撰寫 docs/08_deployment/SD07_Migration_Guide.md
- 四方審查（Architect / SA / SD / QA）APPROVED
- gate_audit + risk_log 完成更新

**逐項打勾**：
```
[  ] T6-1 git tag sd_07_w5_g5_pass（W6 物理拔除前快照）
[  ] T6-2 撰寫 docs/08_deployment/SD07_Migration_Guide.md v1.0：
      - §1 W0~W6 完成範圍
      - §2 Breaking Changes（PlaybookResult 移除 + _consecutive_compact_failures 移除 + _prepend_global_goal_brief 移除）
      - §3 新 LOC 政策（ADR-SD07-001 引用）
      - §4 升級步驟（測試 patch path 對照表）
      - §5 已知限制 + SD_08 延期清單（若有）
      - §6 G6 實測結果
[  ] T6-3 更新 CLAUDE.md 加入 SD_07 W0~W6 摘要區段
[  ] T6-4 更新 gate_audit.md §1-quinquies 補 G0~G6 簽核
[  ] T6-5 更新 risk_log.md §13 標 R-SD07-* 為 CLOSED（W4 三項物理拔除完成）
[  ] T6-6 四方審查（Architect / SA / SD / QA）
[  ] T6-7 PM 簽核
```

**G6 最終驗證**：
```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3              # ≥ 1,857 passed
[  ] python -m pytest tests/equivalence/ -q --tb=no            # 74/74 全綠
[  ] PYTHONUTF8=1 lint-imports --config .importlinter          # 6 kept / 0 broken
[  ] python tools/check_loc_budget.py                          # violations=0（新 baseline 永久鎖定）
[  ] grep -rn "NOTE(SD_07)" autoclaude/ tests/ | wc -l         # = 0
[  ] wc -l autoclaude/execution/steps_orchestrator/_impl.py    # ≤ 500
[  ] ls autoclaude/plugins/token_guard/*.py | wc -l            # ≥ 5
[  ] grep -rn "class PlaybookResult" autoclaude/execution/types.py | wc -l   # = 0
[  ] ls docs/08_deployment/SD07_Migration_Guide.md             # 存在
[  ] ls docs/04_planning/ADR/ADR-SD07-001-loc-policy.md        # 存在
```

---

## 4. 波次間 Session 切換協議

每個 Wave 開始前（切換新 Opus 4.7 session）：

```
我正在執行 SD_Improving_07 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] / [skipped 數]
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製上方 Wave 目標清單]
- PM 拍板事項：[列出本 Wave 對應 PM 決議]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
python tools/check_loc_budget.py
wc -l autoclaude/execution/steps_orchestrator/_impl.py

確認後依照 SD07_Execution_Guide.md W[n] 逐項打勾執行。
```

---

## 5. 緊急停止與回退協議

| 觸發條件 | 立即執行 |
|---------|---------|
| equivalence 74 fixture 任一斷裂 | `git revert HEAD`；找 SA + QA 雙簽才可重啟 |
| importlinter broken | `git stash`；找 Architect 確認再重試 |
| 全測數量下降 | `git stash`；找出哪個測試被移除/跳過 |
| W1 拆解 1,802 測試退化 | `git revert HEAD`；找 Architect + QA 雙簽（紅線 ❌16）|
| W4 patch path 遷移漏改造成 false green | `git stash`；找 SA + QA 雙簽逐處比對 |
| W4 三項順序顛倒 | `git revert HEAD`（紅線 ❌15 違反）|
| W5 runner-no-checkpoint-logic contract broken | `git stash`；找 Architect 確認 EventBus 路徑 |
| LOC 政策調整後 violations 暴增 | 凍結 W1+；回 W0 重新校準 baseline |
| 任何 3 個連續 commit 仍紅 | 停止當前 Wave，回退至前一 G-gate commit |

```bash
# 找到前一 Gate 的 commit
git log --oneline | grep "G[0-6]\|sd_07"

# 回退（確認無誤後）
git reset --hard <commit-hash>
```

---

## 6. 進度追蹤表

| Wave | 狀態 | 通過日期 | 測試基線 | PM 對應項 | 備注 |
|------|------|---------|---------|----------|------|
| W0 | 📋 啟動日 2026-05-20 | — | 1,802 → 預估 +6 | #1 LOC 政策 | ADR 落地 + 工具升級 + AC scaffolding |
| W1 | 📋 待 W0 | — | 預估 ≥ 1,810 | — | _impl.py 736 → ≤ 500 |
| W2 | 📋 待 W1 | — | 預估 ≥ 1,840 | #2 真實 PG e2e | 6 議題 e2e 整合測試 |
| W3 | 📋 待 W2 | — | 預估 ≥ 1,865 | — | token_guard 拆 5 子模組 |
| W4 | 📋 待 W3 | — | 預估 ≥ 1,865（不下降）| #3 W4 一次切 | 三項物理拔除 |
| W5 | 📋 待 W4 | — | 預估 ≥ 1,877 | — | Plugin 審計 + baseline 鎖定 |
| W6 | 📋 待 W5 | — | 預估 ≥ 1,857（吸收 W4 重構造成的 -20 緩衝）| — | Migration Guide + 四方審查 |

---

## 7. 前置已就緒項目（無需重做）

| 項目 | 狀態 | 說明 |
|------|------|------|
| Docker PostgreSQL + pgvector | ✅ | SD_05 W0 已就位 |
| Docker TEI BGE-M3 embedder | ✅ | SD_05 W0 已就位 |
| OrchestrationCoordinator | ✅ | SD_06 W1 G1 已就位（232 LOC ≤ 250）|
| PG 三層 schema（projects/goal_tasks/execution_items）| ✅ | SD_06 W3 G3 已就位 |
| IEmbedder/IVectorSearch + 雙 adapter | ✅ | SD_06 W3 G3 已就位 |
| ExecutionContext + dual_state drift + drift_log | ✅ | SD_06 W5 G5 已就位 |
| ConfigResolver 4 層 + Pydantic v2 invariants | ✅ | SD_06 W5 G5 已就位 |
| ADR-SD07-001 LOC 政策 | ✅ | 規劃階段 2026-05-18 已三方共識 + PM 形式核准 |
| PM 拍板 4 項（SD_07）| ✅ | 2026-05-18 全數 APPROVED |

---

## 8. 關鍵風險即時監控（每 Wave 末複查）

```
[ Wave W0 ] R-SD07-5-1 — tools/check_loc_budget.py 升級是否同步交付？baseline 是否校準？
[ Wave W1 ] R-SD07-1-1 — _impl.py 736 拆解過程 equivalence 74 fixture 是否全程綠？
[ Wave W2 ] R-SD07-0-1 — 5 種失敗情境 e2e 是否全部覆蓋？真實 PG 是否啟用？
[ Wave W3 ] R-SD07-4-1（QA Q-4）— token_guard 拆 5 後 coverage 是否不下降？
[ Wave W4 ] R-SD07-W4-1~3 — 三項物理拔除順序是否遵守紅線 ❌15？
[ Wave W5 ] R-SD07-2-1 — runner-no-checkpoint-logic 升級至 importlinter 是否成功？
```

---

**對應參考文件**：
- [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.0 — 主規劃文件
- [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 — LOC 政策三方共識決議
- [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2 — 前置 sprint
- [SD06_Migration_Guide.md](../08_deployment/SD06_Migration_Guide.md) v1.0 §5 §7 — SD_07 延期清單來源
- [risk_log.md](risk_log.md) §13 — SD_07 風險條目
- [gate_audit.md](gate_audit.md) §1-quinquies — SD_07 Gates

---

**文檔元數據**：
- 文件版本：v1.0
- 建立日期：2026-05-18
- 對應規劃版本：SD_Improving_07.md v1.0
- G0 啟動日：2026-05-20
- 維護者：Tech Lead + PM 共同維護
