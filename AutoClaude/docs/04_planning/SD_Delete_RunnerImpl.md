# SD_Delete_RunnerImpl — _runner_impl.py 刪除 Sprint 規格

**版本**：v1.1（已簽核）
**建立日期**：2026-05-12
**狀態**：Approved（Tech Lead + PM 雙人簽核 2026-05-12）
**Sprint 目標**：將 9 個測試檔案（380 tests）從 `PlaybookRunner(dry_run=True)` 模式遷移至直接測試 `AutoResumeService + Kernel`，並將 `_runner_impl.py` 的業務邏輯依責任歸位至各層，最終刪除 2,227 行的 mixin 檔案。

---

## 1. 背景

### 1.1 現況

| 項目 | 數值 |
|------|------|
| `_runner_impl.py` 行數 | 2,227 行 |
| `_PlaybookRunnerImpl` 方法數 | 27 個 |
| 受影響測試檔案 | 9 個 |
| 受影響測試函式 | 380 個 |
| 受影響測試行數 | 6,142 行 |

### 1.2 目前架構問題

```
PlaybookRunner (147 行)
  └── 繼承 _PlaybookRunnerImpl (2,227 行)   ← 這是問題所在
        ├── run() + _run_steps()             ← 應移至 AutoResumeService
        ├── _execute_prompt()                ← 應移至 Kernel / ExecutorPort
        ├── _evaluate()                      ← M1 shim 已委派 Kernel（W4 完成）
        ├── _get_correction()                ← 應移至 CorrectionPlugin / BrainPort
        ├── _handle_token_halt()             ← 應移至 TokenGuardPlugin
        ├── _save_*()                        ← 應移至 CheckpointPlugin
        └── 20+ 其他方法                      ← 各自歸位至 Plugin 或 Service
```

### 1.3 目標架構

```
PlaybookRunner (< 50 行，純 CLI adapter)
  └── AutoResumeService (core/services/auto_resume.py)
        └── PlaybookKernel (core/kernel.py)
              ├── ExecutorPort    → PtyExecutor / FakeExecutor (測試)
              ├── EvaluatorPort   → ShellEvaluator / FakeEvaluator (測試)
              ├── BrainPort       → MinimaxBrain / FakeBrain (測試)
              └── EventBus → 12 Plugins
```

### 1.4 先決條件（啟動前確認）

- [x] Phase 4 G3 已三方簽核（`use_kernel_path=True` 正式可用）
- [x] M1 shim 三個方法已委派（`_evaluate`, `_apply_single_mutation`, `_validate_batch_compatibility`）
- [x] `AutoResumeService` 已存在（`core/services/auto_resume.py`）
- [x] `PlaybookKernel` 已存在（`core/kernel.py`，215 行）
- [x] 測試基線：1,006 passed / 13 skipped

---

## 2. 範疇

### 2.1 受影響測試檔案清單

| 檔案 | Tests | 行數 | 主要模式 |
|------|-------|------|---------|
| `tests/test_playbook_runner.py` | 45 | 1,146 | `PlaybookRunner(dry_run=True)` + regex 合成 |
| `tests/test_token_checkpoint.py` | 56 | 934 | Token guard + checkpoint save/restore |
| `tests/test_gap009.py` | 42 | 427 | `_make_runner()` factory |
| `tests/test_gap010.py` | 55 | 729 | Error budget + evolution |
| `tests/test_gap012.py` | 35 | 527 | Cross-step validator |
| `tests/test_gap013.py` | 37 | 851 | GotoCounter + counter persistence |
| `tests/test_gap014_020.py` | 57 | 1,186 | Context negotiation + KB meta-learning |
| `tests/test_gap021_028.py` | 27 | 688 | StepMutation batch + goal synthesis |
| `tests/test_gap039_049.py` | 26 | 654 | Evolution counter + GOTO upper bound |
| **合計** | **380** | **6,142** | |

### 2.2 `_runner_impl.py` 方法歸位計劃

| 方法 | 行數（約） | 目標位置 |
|------|-----------|----------|
| `run()` | 120 行 | `AutoResumeService.run()`（已有骨架，需填充） |
| `_run_steps()` | 400 行 | `PlaybookKernel._run_step()` 擴展 + Plugins |
| `_execute_prompt()` | 80 行 | `ExecutorPort.execute()` 介面後移至 `PtyExecutor` |
| `_evaluate()` | 25 行 | `EvaluatorPort` / M1 shim 已委派 ✅ |
| `_get_correction()` | 60 行 | `BrainPort.decide_correction()` → `MinimaxBrain` |
| `_handle_token_halt()` | 75 行 | `TokenGuardPlugin.on_token_halt()` 擴展 |
| `_save_evolution_resume_checkpoint()` | 45 行 | `CheckpointPlugin.on_evolution_halt()` |
| `_save_interrupt_checkpoint()` | 50 行 | `CheckpointPlugin.on_interrupt()` |
| `_save_escalation_dump()` | 50 行 | `EscalationPlugin` 新增 |
| `_persist_mutated_playbook()` | 20 行 | `EvolutionPlugin` 擴展 |
| `_prepend_global_goal()` | 25 行 | `GlobalGoalAnchorPlugin` 擴展 |
| `_build_achievement_summary()` | 15 行 | `KernelState` staticmethod |
| `_validate_global_goal_achievement()` | 40 行 | `ConvergencePlugin` 擴展 |
| `_resolve_start()` | 35 行 | `AutoResumeService._resolve_start()` |
| `_wait_for_scheduled_resume()` | 20 行 | `AutoResumeService._wait_for_resume()` |
| `_load_playbook()` | 15 行 | `PlaybookRepositoryPort` |
| `_detect_workflow()` | 25 行 | `WorkflowDetector`（已獨立） |
| `_should_compact_now()` + `_send_compact()` | 80 行 | `TokenGuardPlugin` 擴展 |
| `_get_dynamic_compact_threshold()` | 20 行 | `TokenGuardPlugin` |
| `_verify_correction_applied()` | 50 行 | `CrossStepValidatorPlugin` 擴展 |
| `_apply_single_mutation()` | 120 行 | M1 shim 已委派 ✅ |
| `_validate_batch_compatibility()` | 25 行 | M1 shim 已委派 ✅ |
| `_fast_path_test_file_check()` | 40 行 | `PreRunValidatorPlugin` 擴展 |
| `_notify()` | 8 行 | `NotificationPlugin` |
| `PlaybookState` enum | 10 行 | `core/kernel_state.py` 擴展 |
| `_StepOutput` dataclass | 10 行 | `core/kernel_state.py` |
| `PlaybookResult` dataclass | 20 行 | `core/kernel_state.py` → `KernelResult` |

---

## 3. 技術策略

### 3.1 測試遷移核心模式

**舊模式（被淘汰）：**
```python
def _make_runner(dry_run=False):
    cfg = AppConfig()
    minimax = MagicMock()
    hotkey = MagicMock()
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run)

def test_something():
    runner = _make_runner(dry_run=True)
    result = runner.run("playbook.yaml")
    assert result.success
```

**新模式（目標）：**
```python
# tests/helpers/kernel_fixtures.py（W1 建立）
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.event_bus import EventBus
from autoclaude.core.wiring import wire_plugins
from autoclaude.core.services.auto_resume import AutoResumeService
from tests.helpers.fake_ports import FakeExecutor, FakeEvaluator, FakeBrain

def make_kernel(outputs: list[str] = None, eval_pass: bool = True):
    """建立帶 Fake ports 的 Kernel，供測試直接使用。
    返回 (kernel, plugins_dict)，plugins_dict 供測試斷言 plugin state。
    """
    executor = FakeExecutor(outputs=outputs or ["[DONE]"])
    evaluator = FakeEvaluator(always_pass=eval_pass)
    brain = FakeBrain()
    bus = EventBus()
    plugins = wire_plugins_with_registry(bus, config=AppConfig())  # 返回 {name: plugin}
    kernel = PlaybookKernel(
        executor=executor,
        evaluator=evaluator,
        bus=bus,
        brain=brain,
        mutation_service=plugins["mutation_service"],
    )
    return kernel, plugins

def make_service(outputs=None, eval_pass=True):
    kernel, plugins = make_kernel(outputs=outputs, eval_pass=eval_pass)
    return AutoResumeService(kernel=kernel, config=AppConfig()), plugins

# 測試寫法
def test_something():
    service, plugins = make_service(outputs=["[DONE]"])
    result = service.run("playbook.yaml")
    assert result.success
    # 如需斷言 plugin state：
    # assert plugins["goto_counter"].counter == 0
```

### 3.2 Fake Ports 設計（W1 建立）

**`tests/helpers/fake_ports.py`**：
```python
class FakeExecutor:
    """可配置輸出的測試用 ExecutorPort。"""
    def __init__(self, outputs: list[str]):
        self._outputs = iter(outputs)
        self.calls: list[str] = []

    def execute(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        return next(self._outputs, "[DONE]")

class FakeEvaluator:
    def __init__(self, always_pass=True, results: list[bool] = None):
        self._results = iter(results or [])
        self._default = always_pass

    def evaluate(self, output: str, regex: str = None, **kwargs) -> bool:
        return next(self._results, self._default)

class FakeBrain:
    def __init__(self, correction=None):
        self._correction = correction

    def decide_correction(self, **kwargs):
        return self._correction
```

### 3.3 遷移優先策略

1. **先遷移小檔案**（test_gap021_028, test_gap039_049），建立遷移信心
2. **相似模式批量遷移**（test_gap009, test_gap010 都用 `_make_runner()` factory）
3. **最後遷移複雜檔案**（test_token_checkpoint, test_playbook_runner）
4. **保持 1,006+ tests 全綠**：每次遷移後必須通過全套測試

---

## 4. 週次計劃

### W1（第 1 週）：審計 + 基礎設施

**目標**：建立 Fake Ports + Kernel Fixtures，完成所有測試檔案分析

| 任務 | 描述 | 估時 |
|------|------|------|
| T-001 | 建立 `tests/helpers/` 目錄 + `fake_ports.py`（FakeExecutor, FakeEvaluator, FakeBrain） | 4h |
| T-002 | 建立 `tests/helpers/kernel_fixtures.py`（make_kernel, make_service factory） | 3h |
| T-003 | 逐一分析 9 個測試檔案，標記每個 test 的遷移難度（Easy/Medium/Hard） | 4h |
| T-004 | 確認 `AutoResumeService.run()` 現有實作範圍，列出需補充的方法 | 2h |
| T-005 | 建立 `docs/05_development/RunnerImpl_Migration_Tracker.md` 逐函式追蹤表 | 1h |
| **W1 Gate G-W1** | `tests/helpers/` 中所有 fixture 自身測試通過（`tests/helpers/test_fixtures.py`） | — |

### W2（第 2 週）：第一批遷移（88 tests）

**目標**：遷移 test_gap021_028 + test_gap039_049 + test_gap012

| 任務 | 描述 | Tests | 估時 |
|------|------|-------|------|
| T-010 | 遷移 `test_gap021_028.py`（StepMutation batch + goal synthesis） | 27 | 6h |
| T-011 | 遷移 `test_gap039_049.py`（Evolution counter + GOTO upper bound） | 26 | 6h |
| T-012 | 遷移 `test_gap012.py`（Cross-step validator） | 35 | 5h |
| T-013 | 補充 `AutoResumeService` 缺失方法（`_resolve_start`, `_wait_for_resume`） | — | 4h |
| **W2 Gate G-W2** | 遷移後 3 個檔案全綠 + 全套 1,006+ tests 通過 | 88 | — |

### W3（第 3 週）：第二批遷移（134 tests）

**目標**：遷移 test_gap009 + test_gap010 + test_gap013

| 任務 | 描述 | Tests | 估時 |
|------|------|-------|------|
| T-020 | 遷移 `test_gap009.py`（KB + fast path + dynamic compact） | 42 | 8h |
| T-021 | 遷移 `test_gap010.py`（Error budget + evolution） | 55 | 10h |
| T-022 | 遷移 `test_gap013.py`（GotoCounter + counter persistence） | 37 | 8h |
| T-023 | 將 `_get_correction()` 邏輯移至 `BrainPort` / `MinimaxBrain` | — | 4h |
| **W3 Gate G-W3** | 遷移後 3 個檔案全綠 + 全套 tests 通過 | 134 | — |

### W4（第 4 週）：第三批遷移（158 tests）

**目標**：遷移 test_gap014_020 + test_token_checkpoint + test_playbook_runner

| 任務 | 描述 | Tests | 估時 |
|------|------|-------|------|
| T-030 | 遷移 `test_gap014_020.py`（Context negotiation + KB meta-learning） | 57 | 10h |
| T-031 | 遷移 `test_token_checkpoint.py`（Token guard + checkpoint） | 56 | 10h |
| T-032 | 遷移 `test_playbook_runner.py`（核心 dry_run 模式） | 45 | 10h |
| T-033 | 將 `_handle_token_halt()` 完整移入 `TokenGuardPlugin` | — | 6h |
| T-034 | 將 `_save_*()` 方法完整移入 `CheckpointPlugin` | — | 6h |
| **W4 Gate G-W4** | 全部 380 tests 在新模式下通過 + 全套 tests 通過 | 158 | — |

### W5（第 5 週）：清理與刪除

**目標**：刪除 `_runner_impl.py`，PlaybookRunner 瘦身至 < 50 行

| 任務 | 描述 | 估時 |
|------|------|------|
| T-040 | 確認 `_runner_impl.py` 所有 27 個方法均已在新位置實作 | 3h |
| T-041 | 移除 `playbook_runner.py` 中的 `from ._runner_impl import ...` + mixin 繼承 | 2h |
| T-042 | PlaybookRunner 改為純委派 `AutoResumeService.run()` | 3h |
| T-043 | 刪除 `autoclaude/execution/_runner_impl.py` | 0.5h |
| T-044 | 更新 Frozen Surface check script（9 項 → 新 facade 結構） | 2h |
| T-045 | 執行全套測試，確認 1,006+ 全綠（LOC 減少 ≥ 2,000 行） | 2h |
| T-046 | 更新 `CLAUDE.md` 架構圖（移除 `_runner_impl.py` 說明） | 1h |
| T-047 | 更新 `risk_log.md` / `gate_audit.md` 加入新 Gate（G6） | 1h |
| **W5 Gate G6（刪除門）** | 全套 1,006+ tests 通過 + `_runner_impl.py` 不存在 + LOC 減少 ≥ 2,000 | — |

---

## 5. Gate 定義

| Gate | 觸發時機 | 通過條件 |
|------|----------|----------|
| G-W1 | W1 末 | `tests/helpers/test_fixtures.py` 全綠；FakeExecutor / FakeEvaluator / FakeBrain 三個 Fake 完成 |
| G-W2 | W2 末 | test_gap021~028 / test_gap039~049 / test_gap012 三檔遷移完成全綠；全套 tests ≥ 1,006 |
| G-W3 | W3 末 | test_gap009 / 010 / 013 三檔遷移完成全綠；全套 tests ≥ 1,006 |
| G-W4 | W4 末 | 所有 9 個測試檔案遷移完成；全套 tests ≥ 1,006 |
| G6 | W5 末 | `_runner_impl.py` 已刪除；`playbook_runner.py` ≤ 50 行；全套 tests ≥ 1,006；LOC 減少 ≥ 2,000 |

G-W1 ~ G-W4 由 Tech Lead 單人確認即可；**G6 需 Tech Lead + PM 雙人簽核**。

---

## 6. 難點與風險

### R-A：dry_run 模式語意轉換

**問題**：`_runner_impl.py` 的 `dry_run=True` 模式透過正則 keyword 合成輸出，跳過真實 Claude Code 執行。`FakeExecutor` 需完整重現此語意。

**緩解**：`FakeExecutor` 支援 `outputs: list[str]` 逐步返回，每個 test 預設輸出含 regex keyword 字串。Equivalence fixture 驗證兩者 semantic 等價。

### R-B：193 處 mock.patch 耦合

**問題**：現有測試中 `mock.patch('autoclaude.execution.playbook_runner.PlaybookRunner._method')` 的 patching 路徑在新架構下無效。

**緩解**：遷移時改用 DI 注入 Fake Port，無需 mock.patch。逐一審視 193 處，確認全部轉換。

### R-C：Plugin state 依賴

**問題**：某些測試驗證 plugin 的 state 變化（如 goto_counter），在新測試模式下需直接存取 Plugin 物件。

**緩解**：`make_kernel()` 返回 `(kernel, plugins_dict)` tuple（§3.1 已更正），測試可直接斷言 `plugins["goto_counter"].counter == expected`。

### R-D：Sprint 時程（5 週）

**問題**：380 個 test 遷移量大，若中途出現 blocking issue 可能延誤。

**緩解**：按難度排序（W2 先做簡單的），每週有 Gate 確認；任一週延誤 > 2 個工作日則啟動 Tech Lead + PM 評估。

---

## 7. 定義完成（DoD）

每個遷移任務（T-010 ~ T-034）完成前需確認：

- [ ] 遷移後測試數量 = 遷移前（不得刪除 test）
- [ ] 所有遷移後的 test 全部通過（無 skip / xfail 新增）
- [ ] 全套 1,006+ tests 仍通過（無退化）
- [ ] `_runner_impl.py` 對應方法標記 `# MIGRATED: <新位置>` 注解
- [ ] PR review 通過

整體 Sprint DoD（T-040 ~ T-047）：
- [ ] `_runner_impl.py` 已刪除（`git rm`）
- [ ] `playbook_runner.py` ≤ 50 行，僅含 CLI adapter 邏輯
- [ ] LOC 減少 ≥ 2,000 行（`git diff --stat HEAD~1`）
- [ ] `tools/check_loc_budget.py` CI gate 通過
- [ ] G6 Tech Lead + PM 雙人簽核

---

## 8. 人天估算（Tech Lead 複核）

| 週次 | 估時合計 | 折合人天（8h） |
|------|---------|--------------|
| W1（基礎設施）| 14h | 1.75 PD |
| W2（88 tests）| 21h | 2.6 PD |
| W3（134 tests）| 30h | 3.75 PD |
| W4（158 tests）| 42h | 5.25 PD |
| W5（刪除清理）| 14.5h | 1.8 PD |
| **合計** | **121.5h** | **~15 PD（≈ 5 週 × 60% FTE）** |

**ROI**：刪除 2,227 行 mixin 死碼，`playbook_runner.py` 瘦身 97%（147 行 → < 50 行），長期維護成本顯著降低。

---

## 9. 簽核紀錄

### Tech Lead 審核（wuweihungmobile，2026-05-12）

**審核發現（v1.0 → v1.1 修正項）：**

| # | 類別 | 發現 | 處置 |
|---|------|------|------|
| TL-1 | 數字錯誤 | W2 標題「116 tests」，實際 27+26+35=88 | ✅ 已更正為 88 |
| TL-2 | 設計不一致 | §3.1 `make_kernel()` 返回 `kernel`，§6 R-C 說返回 tuple | ✅ 已統一為 `(kernel, plugins_dict)` tuple；`make_service()` 同步更新 |
| TL-3 | 缺 ROI | 無人天估算，PM 無法評估可行性 | ✅ 新增 §8 人天估算（15 PD / 5 週 @ 60% FTE） |

**技術可行性結論**：

- ✅ 先決條件全部就緒（G3 簽核、M1 shim、AutoResumeService 骨架已存在）
- ✅ FakeExecutor/FakeEvaluator/FakeBrain 設計正確，可完整替代 dry_run 語意
- ✅ 週次遷移順序合理（由簡至難，每週有 Gate 守門）
- ✅ R-A ~ R-D 風險緩解措施充分

**Tech Lead 決定：APPROVE**（v1.1 修正後啟動）

---

### PM 審核（wuweihungmobile，2026-05-12）

**業務影響評估：**

| 面向 | 評估 |
|------|------|
| 業務風險 | 低：不修改任何 production 行為，僅測試架構遷移 + 死碼刪除 |
| 用戶影響 | 無：外部 CLI 介面不變（PlaybookRunner public API 維持） |
| 回歸風險 | 低：每週 Gate 守門 + 1,006+ tests 持續全綠 |
| 時程可行 | ✅：5 週 / 15 PD，與 Tech Lead 評估一致；G-W1~G-W4 每週確認點清楚 |
| ROI | 明確：2,227 行技術債一次性清除；架構圖清晰度大幅提升 |

**PM 附加條件（無阻擋項，啟動建議）：**

1. W1 結束前提交 `RunnerImpl_Migration_Tracker.md` 逐函式追蹤表供 PM 確認範疇
2. 任一週 Gate 超過 2 個工作日未過，須於下一個工作日內書面說明原因

**PM 決定：APPROVE**（無條件，立即可啟動）

---

### 最終結論

| 簽核人 | 角色 | 日期 | 決定 |
|--------|------|------|------|
| wuweihungmobile | Tech Lead | 2026-05-12 | ✅ APPROVE |
| wuweihungmobile | PM | 2026-05-12 | ✅ APPROVE |

**Sprint 狀態：已核准啟動（Approved to Start）**

---

## 10. 文件關聯

| 文件 | 用途 |
|------|------|
| [SD_Improving_02.md](SD_Improving_02.md) | Phase 0~5 重構背景 |
| [SD_Improving_03_Phase4_Real_Switch.md](SD_Improving_03_Phase4_Real_Switch.md) | Phase 4 Kernel 切換（G3 已完成） |
| [docs/05_development/gate_audit.md](../05_development/gate_audit.md) | G6 簽核追蹤 |
| [docs/05_development/risk_log.md](../05_development/risk_log.md) | R-A ~ R-D 風險追蹤 |
| [docs/05_development/RunnerImpl_Migration_Tracker.md](../05_development/RunnerImpl_Migration_Tracker.md) | 逐函式遷移進度追蹤（W1 建立） |

---

**文檔元數據**：
- 撰寫者：wuweihungmobile
- 建立日期：2026-05-12
- 最後更新：2026-05-12（v1.1 Tech Lead + PM 雙人簽核）
- 下次審查：W1 末 G-W1 Gate 確認 / G6 刪除門 Tech Lead + PM 雙人簽核
- 對應 Gate：G6（刪除門）
