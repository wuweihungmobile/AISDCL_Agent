# SD_Improving_05 Migration Guide

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.1（三方審查覆驗版） |
| 建立日期 | 2026-05-17 |
| 適用版本 | SD_Improving_05 W6 完成後（≥ 1,491 passed） |
| 維護者 | 專案團隊 |

---

## 1. 概述

SD_Improving_05 完成 Phase 5 微核心化重構的最後一波。本指南列出 W0~W6 期間對下游使用者（CLI 操作者、設定檔維護者、Plugin 開發者）會產生影響的 breaking change，並提供升級對照。

### 1.1 W6 完成範圍（精確版）

| W6 子項 | 狀態 | 對應 §6.3 拔除清單項 |
|---------|------|------------------|
| **W6-3** use_kernel_path 雙路徑移除（main.py + config.py + test_main_deprecation.py 刪 + cli test rename） | ✅ 完整 | （獨立項目，不在 22 項清單） |
| **W6-4** CheckpointPlugin `goto_counter_plugin=None` deprecated 參數拔除（含 `_goto_counter` 屬性 + fallback） | ✅ 完整 | §6.3 第 **11** 項 |
| **W6-5** KernelResult SSOT 確認 + PlaybookResult 並存例外條款（PM 簽核） | 🟡 部分（PlaybookResult 仍存在於 PlaybookRunner.run()，SD_05 §5 ❌5 紅線**獲 PM 例外簽核** — 詳見 §1.3） | §6.3 第 **3** 項（部分） |
| **W6-6** Migration Guide（本文件 v1.1） | ✅ 完整 | （獨立項目） |
| **W6-1** `_runner_internals.py`（1,694 行）物理刪除 | ⏳ 延後 SD_06 W0 | §6.3 第 4-6, 9, 13, 15-20 項（~12 項） |
| **W6-2** `_runner_compat.py`（238 行）物理刪除 | ⏳ 延後 SD_06 W2 | §6.3 第 3 項 |
| **其他 §6.3 項** | ⏳ 延後 SD_06 | §6.3 第 1, 2, 7, 8, 10, 12, 14, 21, 22 項（~9 項） |

**§6.3 22 項拔除清單實際完成度**：W6 完成 **1/22**（第 11 項），其餘 21 項標註延後 SD_06 W0~W3，**已獲 PM 例外簽核**並列入 risk_log R-W6-4。

### 1.2 為何延後？

W6 預算 3 PD，但 `_run_steps`（840 行）+ `_apply_single_mutation_full`（295 行）+ `_execute_prompt`（79 行）為 PlaybookRunner 核心狀態機（含 6 處 early-return 耦合 evolution/auto_resume 外層迴圈），無法在 3 PD 安全下沉。詳見 §6 SD_06 估算。

### 1.3 §5 架構紅線 ❌5 PM 例外條款

SD_05 §5 ❌5「KernelResult 與 PlaybookResult 並存超過 SD_05」之紅線，於 W6 末獲 PM 例外簽核延期：

| 項 | 說明 |
|---|------|
| 例外理由 | `PlaybookResult` 物理拔除需先完成 `_run_steps` 核心狀態機下沉，超過 W6 3 PD 預算 |
| 風險評估 | 🟢 低：`main.py` 已唯一透過 `AutoResumeService.run()` 走 `KernelResult` 路徑（W6-3 拔除雙路徑後）；`PlaybookResult` 僅在 `PlaybookRunner.run()` 內部使用，未對外洩漏 |
| 補償措施 | (1) Migration Guide §6 列入 R-W6-3；(2) risk_log R-W6-3 監控；(3) SD_06 W2 強制執行（PD 估算見 §6） |
| 簽核時間 | 2026-05-17（W6 末三方審查 SA-C3 + Architect-C2 共識後 PM 簽核） |

---

## 2. 設定檔（config.yaml）欄位升級對照表

| 舊欄位 | 行為 | SD_05 W6 後 |
|--------|------|-------------|
| `playbook.use_kernel_path: true` | 走 Kernel + AutoResumeService 路徑 | **欄位已移除**；Kernel 路徑為唯一路徑。Pydantic 忽略未知欄位，舊 config 不會崩潰，但欄位值不再生效。建議移除。 |
| `playbook.use_kernel_path: false` | 走舊 PlaybookRunner 直連路徑（SD_03 §2.2 F3） | **欄位已移除**；強制升級至 Kernel 路徑。`tests/test_main_deprecation.py` 已刪除。 |

### 升級步驟

```yaml
# 舊 config.yaml
playbook:
  use_kernel_path: true   # ← 整行移除
  max_evolutions: 3
  ...
```

```yaml
# 新 config.yaml（SD_05 W6 後）
playbook:
  max_evolutions: 3
  ...
```

---

## 3. Plugin API 變動

### 3.1 CheckpointPlugin.__init__ 簽名變更（breaking change）

**SD_04 W4-T17 (M-11) 已 deprecated；SD_05 W6 正式拔除。**

| 舊簽名 | 新簽名（SD_05 W6） |
|--------|---------------------|
| `CheckpointPlugin(checkpoint_manager=..., goto_counter_plugin=GotoCounterPlugin(...), checkpoint_dir=...)` | `CheckpointPlugin(checkpoint_manager=..., checkpoint_dir=..., event_bus=...)` |

**升級方法（SD_05 W6 三方審查 SA-M1 修：推薦 constructor 注入避免 race condition）**：

```python
from autoclaude.core.event_bus import EventBus
from autoclaude.plugins import CheckpointPlugin, GotoCounterPlugin
from autoclaude.utils.checkpoint_manager import CheckpointManager

# 舊路徑（Backward compat，已 W6 拔除）
# counter = GotoCounterPlugin()
# cp = CheckpointPlugin(checkpoint_manager=mgr, goto_counter_plugin=counter)
# ⚠️ SD_06 W0 前仍透過 `**deprecated_kwargs` + DeprecationWarning 接受此呼叫，
#   但僅警告後忽略；新代碼必須改用下方路徑。

# 新路徑（SD_05 W6）— 推薦：constructor 注入（避免後綁 race condition）
bus = EventBus()
counter = GotoCounterPlugin()
mgr = CheckpointManager("checkpoints")

# 1. 註冊 GotoCounterPlugin（必須先於 CheckpointPlugin，以保證 ON_CHECKPOINT_SAVE_REQUEST
#    被 counter 訂閱者接收）
bus.register(counter)

# 2. 建立 CheckpointPlugin（constructor 注入 event_bus；不要用 attach_bus 後綁）
cp = CheckpointPlugin(checkpoint_manager=mgr, event_bus=bus)

# 3. 註冊 CheckpointPlugin
bus.register(cp)

# 4. 觸發任何 phase 之前，已完整 wire 完成
#    GotoCounterPlugin 自動訂閱 ON_CHECKPOINT_RESTORE / ON_CHECKPOINT_SAVE_REQUEST
#    （見 autoclaude/plugins/goto_counter_plugin.py:50-61）
```

**舊版 attach_bus 路徑（仍支援，但不推薦）**：

```python
cp = CheckpointPlugin(checkpoint_manager=mgr)
bus.register(counter)
bus.register(cp)
cp.attach_bus(bus)  # 後綁；對 PRE_RUN 在註冊瞬間觸發場景有潛在 race
```

**理由**：解耦 Plugin 間直接 import（架構紅線 ❌1）；統一透過 EventBus 廣播 `ON_CHECKPOINT_RESTORE` / `ON_CHECKPOINT_SAVE_REQUEST` phase 完成 counter snapshot / restore。`GotoCounterPlugin` 訂閱這兩個 phase 並回傳 `CounterSnapshotResult` IHookResult。

### 3.2 已不再支援的屬性

- `CheckpointPlugin._goto_counter` 屬性已**徹底拔除**，下游不可再以 `getattr` / `hasattr` 探測。
- `_phase_handlers.on_pre_run` 中 `elif plugin._goto_counter is not None: plugin._goto_counter.restore(snap)` fallback 已移除；無 EventBus 時 PRE_RUN 不再 push counter。

---

## 4. Kernel Phase（IHookResult）新增

**SD_05 W0 新增** 8 個 KernelPhase + 6 個 IHookResult：

| KernelPhase | 觸發時機 | 對應 IHookResult |
|-------------|---------|-------------------|
| `PRE_COMPACT` | TokenGuardPlugin 發 /compact 前 | （無） |
| `POST_COMPACT` | TokenGuardPlugin 發 /compact 後 | （無） |
| `ON_PERSISTENCE_REQUEST` | 通用持久化請求（kind=evolution_resume / interrupt） | `PersistenceResult` |
| `ON_ESCALATION_DUMP_REQUEST` | ESCALATION dump 觸發 | `EscalationDumpedResult` |
| `ON_EVOLUTION_PROPOSE` | Minimax 提出演化提案 | （observer，目前 NO-OP audit） |
| `ON_EVOLUTION_APPLY` | PlaybookEvolver 套用完成 | `PersistenceResult` |
| `ON_AUTO_RESUME_WAKE` | AutoResumeService 從 halt / evolution / checkpoint 喚醒 | `ScheduleResumeResult` |
| `ON_PROMPT_PREPARED` | （預留，目前 NO-OP） | （無） |

**新增 IHookResult 完整清單**（含預設值與 contributor 欄位；對應 `autoclaude/core/hookspec.py:145-205`）：

```python
@dataclass(frozen=True)
class ScheduleResumeResult:
    contributor: str
    scheduled_at: str          # ISO 8601 with UTC offset
    wait_secs: float = 0.0

@dataclass(frozen=True)
class CounterSnapshotResult:
    contributor: str
    snapshot: dict[str, dict[str, int]]   # namespace -> {step_id: count}

@dataclass(frozen=True)
class PersistenceResult:
    contributor: str
    path: str
    succeeded: bool
    kind: str = "checkpoint"   # "checkpoint" / "interrupt" / "no_op"

@dataclass(frozen=True)
class MutationApplyResult:
    contributor: str
    clear_goal_summary: bool = False
    should_break: bool = False
    inject_before_pending: bool = False
    goto_target_idx: Optional[int] = None

@dataclass(frozen=True)
class GoalValidationResult:
    contributor: str
    achieved: bool
    reasoning: str = ""
    incomplete_subgoal: Optional[str] = None

@dataclass(frozen=True)
class EscalationDumpedResult:
    contributor: str
    dump_path: str = ""
```

**PHASE_RESULT_CONTRACT**（`hookspec.py:220-247`，共 22 條）：每個 KernelPhase 對應允許的 IHookResult 型別，第三方 Plugin `on_event()` 回傳型別違反 contract 時 EventBus 會 fail-fast raise `HookContractViolation`。Plugin 開發者**必須**參考 hookspec.py 內 `PHASE_RESULT_CONTRACT` dict 確認本 phase 允許的 IHookResult 型別。

範例：
```python
KernelPhase.ON_TOKEN_USAGE → (PersistenceResult, ResourceRequest, None)
KernelPhase.ON_CHECKPOINT_SAVE_REQUEST → (CounterSnapshotResult,)
KernelPhase.ON_AUTO_RESUME_WAKE → (ScheduleResumeResult, None)
```

---

## 5. TokenGuardConfig per-step override

**SD_05 W2 (M-7) 新增。** `PlaybookTask.token_guard: Optional[dict]` 允許單一步驟覆寫全域 token_guard 設定（含 `compact_threshold_pct` / `halt_threshold_pct`）。

### 使用方式

```yaml
version: "1.0"
project: "MyProject"
global_invariants:
  max_retries_per_step: 3
tasks:
  - step_id: "T01_setup"
    name: "環境設定"
    prompt: "..."
    token_guard:
      compact_threshold_pct: 70   # 較低門檻，較早觸發 /compact
      halt_threshold_pct: 85
  - step_id: "T02_codegen"
    name: "程式碼生成"
    prompt: "..."
    token_guard:
      compact_threshold_pct: 85   # 較高門檻，盡量保持 context
      halt_threshold_pct: 95
```

優先序：`task.token_guard` > `config.token_guard`（全域預設）。

**typo 防呆**：`field_validator` 會拒絕不合法欄位名（例如 `compact_threshold_pc` 拼錯），啟動時即報錯。

---

## 6. SD_06 後續範圍（W6 部分執行的延後項）

下列項目於 SD_05 W6 期間因 LOC 預算（≤ 250）+ 3 PD 預算限制，標註為「SD_06 W0 處理」：

| 範圍 | 內容 | 估算工作 |
|------|------|---------|
| **R-W6-1** | `autoclaude/execution/_runner_internals.py`（1,694 行）物理刪除 | 需先將 `_run_steps`（840 行）、`_apply_single_mutation_full`（295 行）、`_execute_prompt`（79 行）等核心方法下沉至 plugin/playbook_runner package |
| **R-W6-2** | `autoclaude/execution/_runner_compat.py`（238 行）物理刪除 | `PlaybookResult` 改用 `KernelResult` SSOT；`_evaluate_impl` / `_validate_batch_compatibility_impl` 改 delegate 至 `ShellEvaluator` / `MutationApplyService` |
| **R-W6-3** | `PlaybookRunner.run()` 回傳型別由 `PlaybookResult` 改為 `KernelResult` | 需更新測試 ~50+ assertion |
| **R-W6-4** | 22 項 backward compat 拔除（§6.3 拔除清單） | 含 W1/W2/W3/W4 各 wave 遺留的 delegate wrapper |
| **R-W6-5** | `_runner_internals.py::_pr()` 反向動態 import 拔除 | 30+ 測試以 `patch("autoclaude.execution.playbook_runner.X")` 模式，需 SD_06 同步改 patch path |

### 估算（SD_05 W6 三方審查 Arch-M3 + SA-m2 重估後 ≥ 21 PD）

| Wave | 估算 PD | 內容 |
|------|--------|------|
| SD_06 W0 | **8 PD** | `_run_steps` 840 行拆 sub-functions（每個 ≤ 250 LOC）+ 引入 `ExecutionContext` dataclass 解 6 處 early-return 外層 scope 耦合（evolution_count / auto_resume_count / checkpoint_dir）+ 下沉至 plugin |
| SD_06 W1 | **4 PD** | `_apply_single_mutation_full` 295 行拆解（7 strategy 改 plugin call；含 counter increment 委派 GotoCounterPlugin） |
| SD_06 W2 | **4 PD** | `_runner_compat.py` 物理刪除 + `PlaybookResult` → `KernelResult` SSOT（含 ~50+ test assertion 更新 + main.py filterwarnings 拔除） |
| SD_06 W3 | **4 PD** | 30+ 測試 patch path 大量遷移（從 `patch("autoclaude.execution.playbook_runner.X")` 改至 plugin / Kernel module 路徑）+ `_pr()` 反向 import 拔除 |
| SD_06 W4 | **1 PD** | 物理刪除 `_runner_internals.py` + §6.3 22 項拔除清單剩餘 21 項清零 + 三方/四方覆驗 |
| **合計** | **21 PD** | （原 14 PD 估算過低，主因未計入 ExecutionContext 重構 + test patch path 大量遷移工作）|

**重要前提**：SD_06 範圍與原 SD_06「PG 三層任務模型 + 向量寫入路徑 + YAML→DB 匯入工具（25-30 PD）」並行；W6 衍生範圍應作為 SD_06 W0 前置條件，建議先完成 SD_06 W0~W4（21 PD）後再進入原 SD_06 PG 三層工作。

---

## 6.6 W6 物理 diff 摘要（SD-m3 補強）

| 檔案 | 變動 | 行數變化 |
|------|------|---------|
| autoclaude/main.py | 移除 use_kernel_path 雙路徑 + import PlaybookRunner（W6-3 + Arch-C2 註解） | -16 / +6 |
| autoclaude/utils/config.py | PlaybookConfig 移除 use_kernel_path 欄位 | -3 |
| autoclaude/plugins/checkpoint/plugin.py | 移除 goto_counter_plugin 參數 + 補 deprecated alias + IHookResult import + warnings import | -8 / +18 |
| autoclaude/plugins/checkpoint/_phase_handlers.py | 移除 `elif _goto_counter` fallback | -2 |
| autoclaude/plugins/checkpoint/_builder.py | 移除 `elif _goto_counter` fallback + docstring | -8 / +2 |
| autoclaude/plugins/checkpoint/_interrupt.py | docstring 修正（W6 Arch-M4） | -1 / +3 |
| config.yaml.example | 刪除 use_kernel_path: true 行（W6 SD-C2） | -2 / +1 |
| tests/cli/test_cli_compatibility_v2.py | TestKernelPathConfigFlag 改名 TestUnknownConfigFieldTolerance；移除 use_kernel_path:true fixture | -23 / +28 |
| tests/plugins/test_checkpoint_plugin.py | _make_plugin 改用 EventBus 路徑 | -5 / +12 |
| tests/plugins/test_checkpoint_goto_decoupling.py | 刪 backward_compat_when_bus_not_attached + 改寫 test_two_plugins_have_no_direct_reference | -28 / +9 |
| tests/test_main_deprecation.py | **整檔刪除** | -163 |
| docs/08_deployment/SD05_Migration_Guide.md | **新建** | +280 |
| docs/05_development/gate_audit.md | SD05-G6 行更新 | +1 / -1 |
| docs/05_development/risk_log.md | 補 §11 R-W6-1~5 + 元數據更新 | +20 / -5 |

合計：source -38 LOC / tests -174 LOC / docs +295 LOC；總 codebase LOC `10754 → 10725`（`-29`，violations=0）；測試數 1494 → 1491（-3 case：test_main_deprecation 2 + test_backward_compat_when_bus_not_attached 1）。

---

## 7. 驗證命令

升級後請執行：

```bash
# 確認測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 1,491 passed / 15 skipped

# 確認 importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：3 kept / 0 broken

# 確認 LOC 預算
python tools/check_loc_budget.py
# 期望：violations=0

# 確認 use_kernel_path 已移除（涵蓋 autoclaude/ + tests/（排除說明性註解）+ config.yaml.example）
# SD-m4 修：grep 範圍擴大避免 false negative
{
  grep -rn "use_kernel_path" autoclaude/ tests/ config.yaml.example 2>/dev/null \
    | grep -v "__pycache__" \
    | grep -v "SD_05 W6\|W6 三方審查\|SD_Improving_05 W6\|legacy_unused_field\|不再含 use_kernel_path\|已移除" \
    | head -5
} && echo "ERROR: 仍有實質殘留" || echo "OK: 已清除（僅說明性註解）"

# 確認 CheckpointPlugin._goto_counter 已拔除
python -c "from autoclaude.plugins import CheckpointPlugin; cp = CheckpointPlugin(); assert not hasattr(cp, '_goto_counter'); print('OK')"

# 確認 CheckpointPlugin deprecated alias 仍可用（過渡期）
python -c "
import warnings
from autoclaude.plugins import CheckpointPlugin, GotoCounterPlugin
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    cp = CheckpointPlugin(goto_counter_plugin=GotoCounterPlugin())
    assert any(issubclass(x.category, DeprecationWarning) for x in w), 'expected DeprecationWarning'
    print('OK: deprecated alias 仍正常工作（DeprecationWarning 觸發）')
"

# 注意：以下命令在 SD_06 W0 物理刪除後才會回 OK；W6 期間 _runner_internals.py / _runner_compat.py 仍存在
# test ! -f autoclaude/execution/_runner_internals.py && echo "OK: 已刪" || echo "DEFERRED: SD_06 W0"
# test ! -f autoclaude/execution/_runner_compat.py && echo "OK: 已刪" || echo "DEFERRED: SD_06 W2"
```

---

## 8. 風險與回退

若升級後遇到問題：

| 問題 | 回退方式 |
|------|---------|
| Plugin 自訂程式碼仍使用 `CheckpointPlugin(goto_counter_plugin=...)` | 改為 EventBus 模式（見 §3.1） |
| 既有 config.yaml 含 `playbook.use_kernel_path` 欄位 | 移除該欄位（Pydantic 預設 ignore extra fields，舊欄位不會崩潰但失效） |
| 自訂測試以 `patch("autoclaude.plugins.checkpoint.plugin.CheckpointPlugin._goto_counter")` 模式 | 改為 EventBus + register GotoCounterPlugin |
| 仍依賴 `_runner_compat.py` 內資料類別 import | 暫時保留，計畫 SD_06 W2 統一拔除 |

完整風險條目參考 [risk_log.md](../05_development/risk_log.md) R-W6-* 系列。

---

## 9. 參考文件

- [SD_Improving_05.md](../04_planning/SD_Improving_05.md) v1.x — 規劃文件
- [SD05_Execution_Guide.md](../05_development/SD05_Execution_Guide.md) — 執行協議
- [gate_audit.md](../05_development/gate_audit.md) — Gate 審查紀錄
- [risk_log.md](../05_development/risk_log.md) — 風險登記

---

**文件元數據**：
- 文件版本：v1.0
- 建立日期：2026-05-16
- 文件狀態：Active
- 適用 SD_Improving_05 W6+
