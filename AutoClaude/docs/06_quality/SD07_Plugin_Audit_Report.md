# SD_Improving_07 W5 — Plugin 架構合規性審計報告

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0 |
| 建立日期 | 2026-05-18 |
| 對應 Sprint | SD_Improving_07 W5（T5-1）|
| 對應 ADR | [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 |
| 對應規格 | [SD_Improving_07.md](../04_planning/SD_Improving_07.md) §4 W5 |
| 對應執行指南 | [SD07_Execution_Guide.md](../05_development/SD07_Execution_Guide.md) §3 W5 |
| 測試基線 | 1,953 passed / 121 skipped（SD_07 W4 G4 末）|
| importlinter | 5 kept / 0 broken（W5 升級後 6 kept / 0 broken）|

---

## 1. 審計範圍

本報告針對 AutoClaude `autoclaude/plugins/` 下所有公開 Plugin 進行架構合規性 walk-through：

1. **Plugin 公開 API + hook subscribe 矩陣**（§3）
2. **plugin-to-plugin import 隔離驗證**（§4，importlinter `plugin-isolation` contract）
3. **直接 import infra 隔離驗證**（§5，建構式注入）
4. **每 Plugin coverage ≥ 80% 驗證**（§6）
5. **`runner-no-checkpoint-logic` contract 升級至 importlinter 原生**（§7）

---

## 2. Plugin 註冊清單（14 個公開 Plugin，依 wiring `_REGISTER_ORDER`）

> SD_06 W6 後 12 個 Plugin → SD_05 W4 補入 `FastPathPlugin` + `PlaybookPersistencePlugin`，目前實際 14 個（CLAUDE.md 與 wiring docstring 仍稱 12 Plugin 為歷史名詞，本報告以實際登記為準）。

| # | 名稱 | 檔案 | PRIORITY | 註冊順序 |
|---|------|------|----------|---------|
| 1 | PreRunValidatorPlugin | `pre_run_validator_plugin.py` | 5 | 1 |
| 2 | HotkeyPlugin（optional）| `hotkey_plugin.py` | 10 | 2 |
| 3 | CrossStepValidatorPlugin | `cross_step_validator_plugin.py` | 15 | 3 |
| 4 | TokenGuardPlugin | `token_guard/policy.py`（package + shim）| 30 | 4 |
| 5 | GlobalGoalAnchorPlugin | `global_goal_anchor_plugin.py` | 35 | 5 |
| 6 | PlaybookPersistencePlugin | `playbook_persistence_plugin.py` | 40 | 6 |
| 7 | FastPathPlugin | `fast_path_plugin.py` | 50 | 7（tie-breaker）|
| 8 | NotificationPlugin | `notification_plugin.py` | 50 | 8 |
| 9 | KnowledgeBasePlugin | `knowledge_base_plugin.py` | 50 | 9 |
| 10 | GoalSynthesisPlugin | `goal_synthesis_plugin.py` | 50 | 10 |
| 11 | ConvergencePlugin | `convergence_plugin.py` | 65 | 11 |
| 12 | EvolutionPlugin | `evolution_plugin.py` | 70 | 12 |
| 13 | GotoCounterPlugin | `goto_counter_plugin.py` | 85 | 13 |
| 14 | CheckpointPlugin | `checkpoint/plugin.py`（package + shim）| 90 | 14 |

⚠️ Tie-breaker 註記（priority=50）：`fast_path` 先於 notification/knowledge_base/goal_synthesis 註冊，確保 `PRE_ATTEMPT` phase 早觸發語意。

---

## 3. Plugin 公開 API + hook subscribe 矩陣

| Plugin | 訂閱 phases | 主要公開 API（非 hook）| LOC | coverage |
|--------|------------|---------------------|-----|----------|
| **PreRunValidatorPlugin** | `PRE_RUN`, `PRE_ATTEMPT` | （無；純 hook）| 69 | 100% |
| **HotkeyPlugin** | `PRE_STEP`, `PRE_ATTEMPT` | （無；純 hook，建構式注入 `HotkeyHandler`）| 50 | 100% |
| **CrossStepValidatorPlugin** | `PRE_STEP`, `PRE_ATTEMPT` | （無；純 hook）| 92 | 91% |
| **TokenGuardPlugin** | `POST_ATTEMPT`, `ON_TOKEN_USAGE` | `get_dynamic_compact_threshold` / `should_compact` / `verify_correction_applied` / `build_compact_prompt` / `process_compact_result` / `observe_token_line` / `resolve_per_step_cfg` / `compact_failure_count` property | 183（policy.py）+ 5 子模組 | 100% |
| **GlobalGoalAnchorPlugin** | `PRE_ATTEMPT`, `ON_TOKEN_USAGE` | （無；純 hook）| 112 | 98% |
| **PlaybookPersistencePlugin** | `ON_EVOLUTION_APPLY` | `persist_mutated_playbook` / `load_mutated_if_exists` / `cleanup_mutated_for_paths` | 152 | 100% |
| **FastPathPlugin** | `PRE_ATTEMPT` | `_check` / `_default_compiler` | 129 | 100% |
| **NotificationPlugin** | `ON_ESCALATION`, `ON_EVOLUTION`, `POST_RUN`, `ON_AUTO_RESUME_WAKE` | （建構式注入 `enabled` + `app_config`）| 117 | 95% |
| **KnowledgeBasePlugin** | `ON_SUCCESS`, `ON_FAILURE`, `ON_ESCALATION` | （建構式注入 `FailureKnowledgeBase`）| 85 | 95% |
| **GoalSynthesisPlugin** | `POST_RUN` | `prepend_global_goal` / `prepend_global_goal_brief` / `build_achievement_summary` / `validate_global_goal_achievement` | 187 | 100% |
| **ConvergencePlugin** | `POST_ATTEMPT` | （無；純 hook，內部 `ConvergenceMonitor`）| 88 | 80% |
| **EvolutionPlugin** | `ON_ESCALATION`, `ON_EVOLUTION_PROPOSE`, `ON_EVOLUTION_APPLY`, `ON_ESCALATION_DUMP_REQUEST` | （建構式注入 `MinimaxClient`）| 212 | 97% |
| **GotoCounterPlugin** | `PRE_RUN`, `POST_ATTEMPT`, `ON_INTERRUPT`, `ON_TOKEN_USAGE`, `ON_CHECKPOINT_RESTORE`, `ON_CHECKPOINT_SAVE_REQUEST` | `goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter` properties / `restore` / `snapshot` | 225 | 94% |
| **CheckpointPlugin** | `PRE_RUN`, `POST_STEP`, `ON_INTERRUPT`, `ON_TOKEN_USAGE`, `ON_EVOLUTION`, `ON_PERSISTENCE_REQUEST`, `ON_ESCALATION_DUMP_REQUEST` | `attach_bus` / `save_evolution_resume_checkpoint` / `handle_token_halt` / `save_interrupt_checkpoint` / `save_escalation_dump` | 235（plugin.py）+ 6 子模組 | 95%（含子模組 86~100%）|

**phase 訂閱統計**：27 個 `KernelPhase`（含 SD_06 W1 新增 7 個 Brain/Executor phases）；本表共覆蓋 17 種 phase 訂閱。

> **註（shim 不獨立計數）**：`autoclaude/plugins/` 目錄下共 15 個 `*.py` 檔案，但本 Audit Report 列出 14 個 Plugin。差異來自 `token_guard_plugin.py` 與 `checkpoint_plugin.py` 為 thin shim re-export（分別 20 / 16 LOC），實際 Plugin 主體位於 `token_guard/policy.py`（183 LOC）與 `checkpoint/plugin.py`（235 LOC）package 內，shim 不獨立計數。`tests/contract/test_plugin_walk_through.py` 14 plugin × 5 case = 70 case 中 `priority_constant_matches_audit_report` 對齊以本表 LOC + coverage 為 SSOT，shim 僅作 backward compat 介面對應。

---

## 4. plugin-to-plugin import 隔離（importlinter `plugin-isolation`）

**契約規範**：任何 Plugin 不可直接 `import` 另一 Plugin；協作必須透過 EventBus（HookSpec phases）。

**驗證命令**：
```bash
PYTHONUTF8=1 lint-imports --config .importlinter
```

**結果**：
```
Plugins must not import other plugins (use EventBus instead) KEPT
```

✅ **全部 14 個 Plugin 合規**（contract `plugin-isolation` 涵蓋 13 個獨立 plugin module；`checkpoint`/`token_guard` 兩個 package 透過 shim re-export，public surface 仍由 `checkpoint_plugin.py` / `token_guard_plugin.py` 代表）。

> ⚠️ **特例**：`autoclaude/execution/playbook_runner.py` constructor 內透過 lazy import 取得 `FastPathPlugin` / `PlaybookPersistencePlugin` / `GoalSynthesisPlugin`（line 145-147）— 這屬於 **Runner → Plugin** 方向（Plugin 之間仍互不 import），對 contract 沒有違反。

---

## 5. 直接 import infra 隔離（建構式注入驗證）

**規範**：Plugin 不可直接 import `autoclaude.infra.*`；所有 infra 依賴必須透過建構式注入（DI）。

**驗證方法**：grep 檢查 + importlinter `core-purity` 旁證（Plugin 與 core/services 同樣不允許跨界）。

```bash
grep -rn "from \.\.infra\|from autoclaude\.infra" autoclaude/plugins/
```

**結果**：✅ **0 處違規**

**注入路徑審計**：

| Plugin | infra 依賴 | 注入方式 |
|--------|----------|---------|
| HotkeyPlugin | `HotkeyHandler`（perception 層）| constructor `hotkey_handler=` |
| TokenGuardPlugin | `TokenGuardConfig` | constructor `token_guard_cfg=` |
| GlobalGoalAnchorPlugin | `PlaybookConfig` | constructor `playbook_cfg=` |
| PlaybookPersistencePlugin | `checkpoint_dir` callable | constructor `checkpoint_dir=` |
| NotificationPlugin | `notification.enabled` + `AppConfig` | constructor `enabled=` / `app_config=` |
| KnowledgeBasePlugin | `FailureKnowledgeBase`（utils）| constructor `knowledge_base=` |
| GoalSynthesisPlugin | `MinimaxClient`（decision）| constructor `minimax_client=` |
| EvolutionPlugin | `MinimaxClient` | constructor `minimax_client=` |
| GotoCounterPlugin | `PlaybookConfig` | constructor `playbook_cfg=` |
| CheckpointPlugin | `CheckpointManager`（utils，內部 lazy 持 `IStateRepository`）| constructor `checkpoint_manager=` |

✅ **全部 14 個 Plugin 合規**（infra 依賴皆透過 `wiring.py` 集中組裝注入）。

---

## 6. Plugin coverage 驗證（≥ 80% 門檻）

**驗證命令**：
```bash
python -m pytest tests/plugins/ tests/core/ --cov=autoclaude/plugins --cov-report=term -q --tb=no
```

**結果**（TOTAL = 95% / 14 Plugin 全部 ≥ 80%）：

| Plugin | Stmts | Cover | 是否 ≥ 80% |
|--------|-------|-------|----------|
| PreRunValidatorPlugin | 29 | **100%** | ✅ |
| HotkeyPlugin | 18 | **100%** | ✅ |
| CrossStepValidatorPlugin | 45 | **91%** | ✅ |
| TokenGuardPlugin（policy + 5 子模組）| 162 | **100%** | ✅ |
| GlobalGoalAnchorPlugin | 51 | **98%** | ✅ |
| PlaybookPersistencePlugin | 66 | **100%** | ✅ |
| FastPathPlugin | 55 | **100%** | ✅ |
| NotificationPlugin | 63 | **95%** | ✅ |
| KnowledgeBasePlugin | 42 | **95%** | ✅ |
| GoalSynthesisPlugin | 79 | **100%** | ✅ |
| ConvergencePlugin | 40 | **80%** | ✅（恰達門檻）|
| EvolutionPlugin | 72 | **97%** | ✅ |
| GotoCounterPlugin | 101 | **94%** | ✅ |
| CheckpointPlugin（plugin + 6 子模組）| 218 | **95%**（_token_halt.py 33% 由 integration 補強，其餘 80~100%）| ✅ |

✅ **14 個 Plugin 全部達標**（TOTAL 95%，門檻 80%）。

---

## 7. `runner-no-checkpoint-logic` contract 升級

### 7.1 既有 grep-based 契約（SD_06 W2-T2-14）

- 檔案：`tests/contract/test_runner_no_checkpoint_logic.py`
- 機制：scan `_runner_internals.py` 是否含 `_save_.*_checkpoint` 字串
- **失效**：`_runner_internals.py` 已於 SD_06 W6 G6 物理刪除（2026-05-18），contract 變成空轉（無檔可 scan）

### 7.2 升級方案：importlinter 原生 forbidden contract

**設計目標**：禁止 `playbook_runner` 與 strategy 模組直接 import `autoclaude.plugins.checkpoint` package 的內部實作模組（`_phase_handlers` / `_token_halt` / `_builder` / `_escalation` / `_interrupt` / `_evolution`），僅允許透過公開 `CheckpointPlugin` API（`from autoclaude.plugins.checkpoint import CheckpointPlugin`）。

**理由**：
1. importlinter 僅能管 module-level import；無法 grep 函式名稱。但 import 內部模組即等於繞過 plugin 封裝、直接觸碰 checkpoint 寫入細節。
2. SD_05 W3 將 `checkpoint_plugin.py` 拆為 6 子模組 + plugin.py public entry；plugin 公開 API 是唯一允許的調用面。
3. 違反此 contract 即代表 runner 重新引入 checkpoint logic 雙寫法（❌13），與 SSOT 原則衝突。

**.importlinter contract 定義**（新增 Rule 6）：

```ini
[importlinter:contract:runner-no-checkpoint-logic]
name = playbook_runner / strategy modules must not import checkpoint internal modules
       (use CheckpointPlugin public API)
type = forbidden
source_modules =
    autoclaude.execution.playbook_runner
    autoclaude.execution.steps_orchestrator
    autoclaude.execution.boot_helper
    autoclaude.execution.prompt_dispatcher
    autoclaude.execution.escalation_dumper
forbidden_modules =
    autoclaude.plugins.checkpoint._phase_handlers
    autoclaude.plugins.checkpoint._token_halt
    autoclaude.plugins.checkpoint._builder
    autoclaude.plugins.checkpoint._escalation
    autoclaude.plugins.checkpoint._interrupt
    autoclaude.plugins.checkpoint._evolution
```

**升級後 contract 總數**：5 kept → **6 kept / 0 broken**

### 7.3 既有 grep-based test 保留作為 anti-resurrection 退化保護

`tests/contract/test_runner_no_checkpoint_logic.py` 保留作為 W3+ regression guard 標記：若有人重建 `_runner_internals.py` 並重新引入 `_save_.*_checkpoint` 函式，contract 立即抓出（與 anti-resurrection `runner-internals-isolation` 平行運作）。

---

## 8. 結論

| 項目 | 結果 |
|------|------|
| 14 個 Plugin 公開 API + hook 訂閱矩陣 | ✅ 全部記錄 §3 |
| plugin-to-plugin import 隔離（importlinter）| ✅ KEPT |
| 直接 import infra 隔離（grep + DI 注入審計）| ✅ 0 違規 |
| 每 Plugin coverage ≥ 80% | ✅ TOTAL 95% / 14 個全部達標 |
| `runner-no-checkpoint-logic` 升級至 importlinter 原生 | ✅ 新增 Rule 6（W5 期望 6 kept / 0 broken）|

**簽核**：
- Architect ✅ 2026-05-18
- SA ✅ 2026-05-18
- SD ✅ 2026-05-18

---

**對應參考文件**：
- [.importlinter](../../.importlinter) — Rule 1~6 全清單
- [tests/contract/test_plugin_walk_through.py](../../tests/contract/test_plugin_walk_through.py) — W5 T5-5 ≥ 12 case 程式化驗證
- [tools/check_loc_budget.py](../../tools/check_loc_budget.py) — ADR-SD07-001 分級工具
- [SD06_Migration_Guide.md](../08_deployment/SD06_Migration_Guide.md) §7.2 — anti-resurrection guard 設計
