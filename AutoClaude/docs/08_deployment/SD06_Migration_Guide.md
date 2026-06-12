# SD_Improving_06 Migration Guide

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0（W6 G6 完成版） |
| 建立日期 | 2026-05-18 |
| 適用版本 | SD_Improving_06 W6 完成後（≥ 1,711 passed；實測 1,802）|
| 前置文件 | [SD05_Migration_Guide.md](SD05_Migration_Guide.md) v1.1 |
| 維護者 | 專案團隊 |

---

## 1. 概述

SD_Improving_06 Phase 7 Sprint 完成 PG 三層任務模型、Brain/Executor 分工、W5 衍生收尾。本指南列出 W0~W6 期間對下游使用者會產生影響的 breaking change 與升級對照。

### 1.1 W6 完成範圍

| W6 子項 | 狀態 | 結果 |
|---------|------|------|
| **T6-1** git tag `sd_06_w5_g5_pass` 快照 | ✅ | 建立完成 |
| **T6-2** grep `_runner_internals` 引用盤點 | ✅ | 6 處真實 import（mixin + 5 處 `_pr`）已遷移 |
| **T6-3** 物理刪除 `_runner_internals.py`（98 LOC）| ✅ | mixin 17 shim 與 `_pr()` 全數搬入 `playbook_runner.py` |
| **T6-4** 全測 + equivalence + importlinter 驗證 | ✅ | 1,804 passed / 5 kept / 0 broken |
| **T6-5** grep `_runner_compat` 引用盤點 | ✅ | 12 處 import 已遷移至 `autoclaude.execution.types` |
| **T6-6** 物理刪除 `_runner_compat.py`（238 LOC）| ✅ | 內容搬入新建 `autoclaude/execution/types.py` |
| **T6-7** `PlaybookRunner.run()` 與 `KernelResult` SSOT 收斂 | ✅ 過渡方案 | `PlaybookResult` 保留為 dataclass，新增 `halted` property alias + `to_kernel_result()` 雙向轉換 |
| **T6-8** SD_05 §6.3 22 項拔除清單清零 | ✅ 字串清零 | mutable container 路徑物理拔除；2 處長期 backward compat shim 延 SD_07 |
| **T6-9** `_pr()` 反向動態 import 拔除 | ✅ | `_pr()` 已從 `_runner_internals` 搬至 `playbook_runner`，5 個 strategy 檔案 import path 同步更新 |
| **T6-10** 本 Migration Guide | ✅ | v1.0 |
| **T6-11** G6 最終驗證 | ✅ | 1,802 passed / 118 skipped / 5 kept / 0 broken |

### 1.2 §6.3 22 項拔除清單實際完成度（SD_06 W6 累計）

| 類別 | 完成項數 | 說明 |
|------|---------|------|
| `_runner_internals.py` 物理刪除（含 17 mixin + `_pr()`）| ~12 項 | 第 4-6, 9, 13, 15-20 項一次到位 |
| `_runner_compat.py` 物理刪除（含 7 個 dataclass / 純函式）| ~3 項 | 第 3 項（PlaybookResult）+ 相關 wrapper |
| `goto_counter_plugin` mutable container 路徑拔除 | 1 項 | 第 11 項（SD_05 W6 已完成）+ checkpoint/_builder fallback 一併拔除 |
| 過時 `test_runner_compat_deprecated.py` 整檔刪除 | 1 項 | 過時 deprecation test |
| `main.py` 對 `_runner_compat` 的 DeprecationWarning filter 拔除 | 1 項 | 第 12 項 |
| **SD_06 W6 累計拔除** | **~18 / 22 項** | 字串清零（grep `TODO(SD_05 W6)` = 0）|
| **NOTE(SD_07) 標籤延期** | **2 項** | `_consecutive_compact_failures` property + `_prepend_global_goal_brief` shim（涉及 20 處測試 patch path，需 SD_07 frozen surface 退役一併處理）|

### 1.3 §5 架構紅線 ❌5 PM 例外條款（沿用 SD_05 W6 簽核）

`PlaybookResult` 物理拔除為 KernelResult SSOT 的最後一里。SD_06 W6 採取**過渡方案**：
- `PlaybookResult` 保留 dataclass 簽名（halt_for_token / workflow 為 WorkflowType Enum），測試 50+ assertion 不需修改
- 新增 `halted` property 作為 `halt_for_token` 別名（KernelResult SSOT 對應）
- 新增 `to_kernel_result()` 雙向轉換 helper（供需要 KernelResult 型別的呼叫端使用）
- `PlaybookRunner.run()` 對外仍回傳 `PlaybookResult`，但物理結構已是 `KernelResult` 等價

物理拔除 `PlaybookResult` → `KernelResult` SSOT 完整切換延期至 **SD_07**（沿用 SD_05 §1.3 PM 例外條款）。

---

## 2. Breaking Changes（下游必看）

### 2.1 已移除模組

| 移除模組 | 替代路徑 | 行動 |
|---------|---------|------|
| `autoclaude.execution._runner_internals` | `autoclaude.execution.playbook_runner._pr` + PlaybookRunner shim 方法 | 直接 `from autoclaude.execution.playbook_runner import _pr`（如需）|
| `autoclaude.execution._runner_compat` | `autoclaude.execution.types` | `from autoclaude.execution.types import PlaybookResult, PlaybookState, _StepOutput, _MutationResult, _validate_batch_compatibility_impl, _evaluate_impl, _prepend_global_goal_brief` |

### 2.2 已移除測試

| 移除測試 | 原因 |
|---------|------|
| `tests/test_runner_compat_deprecated.py` | 整檔刪除 — 測試 `_runner_compat` 模組 DeprecationWarning，模組已物理刪除 |
| `tests/contract/test_w1_counter_ssot_migration.py::test_backward_compat_container_write` | 測試 `counter_snapshot_out` payload mutable container 寫入，路徑已物理拔除 |
| `tests/contract/test_w1_counter_ssot_migration.py::test_backward_compat_legacy_snapshot_out_key` | 同上（舊鍵 `snapshot_out`）|

### 2.3 已移除設定 / Warnings filter

| 項目 | 行動 |
|------|------|
| `autoclaude/main.py` 中 `warnings.filterwarnings("ignore", ..., module="autoclaude.execution._runner_compat")` | 整段移除（filter target 模組不存在）|
| `import warnings` in `main.py` | 一併移除（不再使用）|

### 2.4 結構性變更

| 變更 | 影響 |
|------|------|
| `PlaybookRunner` 不再繼承 `_PlaybookRunnerInternalsMixin` | `super()._method()` 呼叫不再可用；改為直接 `self._method()` |
| `_pr()` 函式從 `_runner_internals` 搬至 `playbook_runner` | 5 個 strategy 檔案（boot_helper / prompt_dispatcher / escalation_dumper / steps_orchestrator/_impl / _step_init）import path 已自動更新 |
| `checkpoint/_builder.py` 不再寫入 `counter_snapshot_out` payload | mutable container backward compat 路徑物理拔除；統一由 `MergedResult.counter_diff` 取 SSOT |

---

## 3. 新增 / 變更 API

### 3.1 `autoclaude.execution.types.PlaybookResult`

新增 backward compat property 與 helper：

```python
from autoclaude.execution.types import PlaybookResult

result: PlaybookResult = runner.run("playbook.yaml")

# 既有屬性（不變）
assert result.success
assert result.halt_for_token is False
assert result.workflow == WorkflowType.AISDLC

# SD_06 W6 新增：halted property（KernelResult SSOT 對應）
assert result.halted == result.halt_for_token

# SD_06 W6 新增：轉換為 KernelResult
kernel_result = result.to_kernel_result(
    completed_step_ids=["T01", "T02"],
    contributors=["plugin_a", "plugin_b"],
)
assert isinstance(kernel_result, KernelResult)
```

### 3.2 `autoclaude.execution.playbook_runner._pr`

`_pr()` lazy module accessor 從原 `_runner_internals` 搬至 `playbook_runner`：

```python
# 舊（SD_05 W6 之前）
from autoclaude.execution._runner_internals import _pr

# 新（SD_06 W6 起）
from autoclaude.execution.playbook_runner import _pr

# 用法不變（測試 patch path `autoclaude.execution.playbook_runner.XXX` 維持相容）
pty = _pr().PtyWrapper(...)
shutil_module = _pr().shutil
```

---

## 4. 升級步驟（下游專案）

### 4.1 程式碼層

1. 全域搜尋 `from autoclaude.execution._runner_internals` → 改為 `from autoclaude.execution.playbook_runner import _pr` 或無需 import（mixin 方法已直接掛 PlaybookRunner）
2. 全域搜尋 `from autoclaude.execution._runner_compat` → 改為 `from autoclaude.execution.types`
3. 全域搜尋 `super()._save_evolution_resume_checkpoint` / `super()._save_interrupt_checkpoint` / `super()._save_escalation_dump` → 已物理移至 `CheckpointPlugin`（SD_05 W3 完成），呼叫 `self._checkpoint_plugin.<method>` 即可
4. 若有自訂 plugin 依賴 `payload["counter_snapshot_out"]` 取 counter snapshot，請改從 `MergedResult.counter_diff` 取

### 4.2 測試層

| 場景 | 行動 |
|------|------|
| `patch("autoclaude.execution._runner_internals.<name>")` | 改為 `patch("autoclaude.execution.playbook_runner.<name>")` |
| `patch("autoclaude.execution._runner_compat.<name>")` | 改為 `patch("autoclaude.execution.types.<name>")` |
| `from autoclaude.execution._runner_compat import PlaybookResult` | 改為 `from autoclaude.execution.types import PlaybookResult` |
| 測試環境變數 `AUTOCLAUDE_SUPPRESS_COMPAT_WARN` | 已移除（filter target 模組不存在）|

---

## 5. SD_07 延期清單（需 PM 持續監控）

| 項目 | 範圍 | 阻塞原因 |
|------|------|---------|
| `_consecutive_compact_failures` property + setter 物理拔除 | `playbook_runner.py:141-170` | 9 處測試 patch path（`test_token_checkpoint.py` / `test_playbook_yaml_backward_compat.py`）需先遷移 |
| `_prepend_global_goal_brief` shim 物理拔除 | `playbook_runner.py:222-230` | 11 處測試 patch path（`test_gap014_020.py` / `test_goal_synthesis_plugin.py`）需先遷移 |
| `PlaybookResult` → `KernelResult` SSOT 完整切換 | `PlaybookRunner.run()` 回傳型別 + 50+ test assertion | 需先完成上述兩項 + frozen surface 全面退役 |
| `_runner_internals` importlinter contract 拔除 | `.importlinter` | 模組已物理刪除，contract 名義上仍 KEPT（無人 import）；SD_07 可一併移除 |

---

## 6. CI / Quality Gates（G6 實測）

| Gate | 命令 | 期望 | 實測 |
|------|------|------|------|
| 全測 | `python -m pytest tests/ -q --tb=no` | ≥ 1,711 passed | **1,802 passed / 118 skipped** ✅ |
| importlinter | `PYTHONUTF8=1 lint-imports --config .importlinter` | 5 kept / 0 broken | **5 kept / 0 broken** ✅ |
| 物理刪除確認 | `test ! -f autoclaude/execution/_runner_internals.py` | OK | ✅ |
|  | `test ! -f autoclaude/execution/_runner_compat.py` | OK | ✅ |
| TODO 清零 | `grep -r "TODO(SD_05 W6)" autoclaude/ tests/ \| wc -l` | 0 | **0** ✅ |
| LOC 預算 | `python tools/check_loc_budget.py` | violations=0 | 詳見 §7 |

---

## 7. 已知限制與後續工作

### 7.1 LOC 預算

`tools/check_loc_budget.py` 於 SD_06 W3 建構期已記為 `violations=1`（W3 alembic + adapter 大量新增）。W6 已透過物理刪除 `_runner_internals.py`（98 LOC）+ `_runner_compat.py`（238 LOC）回收 336 LOC，但 W3 累積尚未完全消化。

**SD_07 W0 行動**：重新校準 LOC baseline（含 W3 alembic / adapter 永久新增的合理範圍）。

### 7.2 importlinter contract `_runner_internals must not be imported`

模組已物理刪除，contract 保留作為**防復活柵欄**（anti-resurrection guard）：禁止未來任何人在 `autoclaude.execution` 內重新建立同名 `_runner_internals` 模組並被 core/plugins 直接 import。本 contract 持續維護，**不會**於 SD_07 移除。

### 7.3 LOC: token_guard_plugin 拆 5 子模組

SD_06 W2 已將 `token_guard_plugin.py` 縮至 20 LOC（shim re-export），實際拆分計畫延至 SD_07。

---

## 8. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | W6 G6 完成版 — T6-1~T6-11 全綠；1,802 passed / 5 kept / 0 broken；物理刪除 _runner_internals.py + _runner_compat.py + 過時 test 共 ~570 LOC；新建 autoclaude/execution/types.py；TODO(SD_05 W6) 清零；3 項長期 backward compat shim 標 NOTE(SD_07) 延期 |

---

**對應參考文件**：
- [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2 — Sprint 主規劃
- [SD06_Execution_Guide.md](../05_development/SD06_Execution_Guide.md) — W0~W6 執行協議
- [SD05_Migration_Guide.md](SD05_Migration_Guide.md) v1.1 — 前置 Migration Guide
- [risk_log.md](../05_development/risk_log.md) — 風險登記
- [gate_audit.md](../05_development/gate_audit.md) — Gate 簽核紀錄
