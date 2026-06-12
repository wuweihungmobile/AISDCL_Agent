# AutoClaude_Improving_011
# 自治開發系統：全局目標錨點與 Minimax 步驟動態修正藍圖

**文件版本**: v1.0  
**建立日期**: 2026-05-03  
**作者角色**: 首席 AI 自動化架構師  
**分析基準**: AutoClaude Gap-001 ~ Gap-010 全量實作  
**文件狀態**: Active  

---

## 背景與問題陳述

針對「AutoClaude 是否符合自治開發系統三大需求」的評估結論：

| 需求 | 現狀 | 結論 |
|------|------|------|
| 1. Playbook 可設定總目標 | 只有 `project` 名稱，無全局目標宣告欄位 | ❌ 不完整 |
| 2. Playbook 可設定所有執行步驟 | `tasks` 陣列完整支援 | ✅ 符合 |
| 3. Minimax 可隨時修正執行步驟 | Minimax 僅生成 `correction_prompt`，無法改變步驟結構 | ❌ 不符合 |

本文件針對需求 1、3 的缺口，提出三個 Gap 修補方案。

---

## Gap-011-A：Playbook 全局目標錨點（Global Goal Anchor）

### 問題

- Playbook 目前只有 `project` 欄位（單純名稱字串），無法表達「要達成什麼」
- Minimax 產生 `correction_prompt` 時，不知道步驟修正是否符合整體目標
- `PlaybookEvolver` 提議演化方案時，無全局目標作為對齊基準
- `ConvergenceMonitor` 無法判斷「雖然單步驟失敗，但整體目標可能已達成」

### 方案

在 `Playbook` model 新增 `global_goal: Optional[str]` 欄位，並將其注入 Minimax 的系統提示與修正訊息，讓每次修正決策都能對齊全局目標。

### 影響檔案

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `autoclaude/models/playbook.py` | 修改 | `Playbook` 新增 `global_goal: Optional[str] = None` |
| `autoclaude/decision/prompt_builder.py` | 修改 | `build_correction_message()` 新增 `global_goal` 參數，注入訊息頭部 |
| `autoclaude/decision/minimax_client.py` | 修改 | `decide_correction()` 新增 `global_goal` 參數並傳入 |
| `autoclaude/execution/playbook_runner.py` | 修改 | 呼叫 `_get_correction()` 時傳入 `playbook.global_goal` |
| `scripts/example_playbook.yaml` | 修改 | 新增 `global_goal:` 欄位範例 |

### 實作設計

```python
# autoclaude/models/playbook.py
class Playbook(BaseModel):
    version: str = "1.0"
    project: str
    global_goal: Optional[str] = None      # ← NEW: 自治系統總目標
    workflow_type: str = "auto"
    ...
```

```python
# autoclaude/decision/prompt_builder.py — build_correction_message()
def build_correction_message(
    ...,
    global_goal: Optional[str] = None,     # ← NEW
) -> str:
    goal_section = (
        f"## 系統總目標\n{global_goal}\n\n" if global_goal else ""
    )
    return (
        f"{goal_section}"
        f"## 失敗步驟\n{step_id}: {task_name}\n\n"
        ...
    )
```

```yaml
# scripts/example_playbook.yaml（新增欄位）
global_goal: |
  建立一個符合 SDD 規格的 FastAPI JWT 驗證模組，
  包含完整的登入、Token 驗證 API，以及通過所有單元測試。
```

### 驗收標準

- `global_goal` 在 Minimax user message 的最頂端出現（測試：`test_decision.py`）
- `global_goal=None` 時不影響現有輸出（向後相容）
- `dry_run` 模式下 `global_goal` 欄位正常載入

---

## Gap-011-B：Minimax 步驟動態修正（Step Mutation on Failure）

### 問題

- 當步驟反覆失敗（`retry_count >= 2`，`convergence_trend = stuck`），根本原因往往是**步驟設計本身有問題**（prompt 過寬泛、evaluator 不準確），而非 Claude Code 的實作問題
- Minimax 目前只能回傳 `correction_prompt`（指示 Claude Code 做什麼），無法提議**修改步驟定義本身**
- `PlaybookEvolver` 雖能做 INJECT_STEP / SPLIT_STEP，但僅在 ESCALATION 後才觸發，且是規則型而非 AI 驅動

### 方案

擴展 `CorrectionDecision` 加入選填 `step_mutation` 欄位，允許 Minimax 在特定條件下提議步驟結構變更。設計保守門檻（`retry_count >= 2` + `convergence_trend in stuck/oscillating`），避免過早修改 Playbook。

### 支援的 Mutation 類型

| 類型 | 說明 | 風險 |
|------|------|------|
| `REVISE_CURRENT` | 修改當前步驟的 `prompt` 定義（非 correction，是改步驟本體） | 低 |
| `INJECT_AFTER` | 在當前步驟後插入一個新的後續步驟（例如：先修復測試、再重試主步驟） | 中 |

> P2 保留：`REVISE_FUTURE`（修改未來步驟）、`SKIP_CURRENT`（跳過當前步驟） — 風險較高，需更多驗證後實作。

### 影響檔案

| 檔案 | 變更類型 | 說明 |
|------|---------|------|
| `autoclaude/models/step_mutation.py` | **新建** | `StepMutation` / `StepMutationType` 模型 |
| `autoclaude/models/decision.py` | 修改 | `CorrectionDecision` 新增 `step_mutation: Optional[StepMutation] = None` |
| `autoclaude/decision/prompt_builder.py` | 修改 | `CORRECTION_SYSTEM_PROMPT` JSON schema 加入選填 `step_mutation`；`build_correction_message()` 加入 `allow_step_mutation: bool` gate |
| `autoclaude/decision/minimax_client.py` | 修改 | `decide_correction()` 加入 `allow_step_mutation: bool` 參數並傳入 |
| `autoclaude/execution/playbook_runner.py` | 修改 | 呼叫 `_get_correction()` 後，若有 `step_mutation` 則應用並記錄 |

### 實作設計

```python
# autoclaude/models/step_mutation.py（新建）
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class StepMutationType(str, Enum):
    REVISE_CURRENT = "REVISE_CURRENT"     # 修改當前步驟 prompt
    INJECT_AFTER = "INJECT_AFTER"         # 在當前步驟後插入新步驟


class StepMutation(BaseModel):
    mutation_type: StepMutationType
    revised_prompt: Optional[str] = None  # REVISE_CURRENT 使用
    new_step_id: Optional[str] = None     # INJECT_AFTER 使用
    new_step_name: Optional[str] = None   # INJECT_AFTER 使用
    new_step_prompt: Optional[str] = None # INJECT_AFTER 使用
    reasoning: str = ""
```

```python
# autoclaude/models/decision.py
class CorrectionDecision(BaseModel):
    correction_prompt: str
    reasoning: str
    task_goal_summary: Optional[str] = None
    step_mutation: Optional["StepMutation"] = None  # ← NEW（選填）
```

```python
# CORRECTION_SYSTEM_PROMPT 擴展（when allow_step_mutation=True）
"""
若判斷步驟設計本身有問題（prompt 過寬泛或 evaluator 不準），可填入選填欄位：
"step_mutation": {
  "mutation_type": "REVISE_CURRENT" | "INJECT_AFTER",
  "revised_prompt": "...",        // REVISE_CURRENT 時填
  "new_step_id": "T02_FIX",       // INJECT_AFTER 時填
  "new_step_name": "...",
  "new_step_prompt": "...",
  "reasoning": "..."
}
若無需修改步驟，請設為 null。
"""
```

```python
# playbook_runner.py — 應用 step_mutation
allow_mutation = (
    attempt >= 2 and
    convergence_trend in ("stuck", "oscillating", "cycling")
)
correction_prompt, minimax_reasoning, new_summary = self._get_correction(
    ...,
    allow_step_mutation=allow_mutation,
)
# _get_correction 回傳中加入第 4 個值 step_mutation
if step_mutation and step_mutation.mutation_type == StepMutationType.REVISE_CURRENT:
    task.prompt = step_mutation.revised_prompt
    logger.info("Gap-011-B: REVISE_CURRENT 步驟 %s prompt 已更新", step_id)
elif step_mutation and step_mutation.mutation_type == StepMutationType.INJECT_AFTER:
    # 插入新步驟到 task list（待 step loop 取用）
    ...
```

### 門檻設計理由

| 條件 | 理由 |
|------|------|
| `retry_count >= 2` | 第 1 次失敗可能只是 Claude Code 的實作問題，不宜過早動步驟 |
| `convergence_trend in stuck/oscillating/cycling` | 確認是「卡死」而非「正在收斂」 |
| 只允許 `REVISE_CURRENT` + `INJECT_AFTER` | 不能修改未來步驟或跳過步驟，避免破壞 Playbook 設計意圖 |

### 驗收標準

- `allow_step_mutation=False` 時，Minimax system prompt 不包含 `step_mutation` schema（節省 token）
- `step_mutation=null` 時，行為與現有完全相同
- `REVISE_CURRENT` 成功後，log 記錄步驟修改（`Gap-011-B: REVISE_CURRENT`）
- 新增測試：`test_decision.py` 驗證 `StepMutation` 解析；`test_playbook_runner.py` 驗證應用

---

## Gap-011-C：Minimax 目標對齊主動規劃（Pre-Step Goal Alignment）[P2]

### 問題

Minimax 目前為**完全被動**（只在步驟失敗時被呼叫）。當前一步驟完成後揭露了新資訊（例如：發現 SDD 規格有歧義），後續步驟的設計可能已過時，但 AutoClaude 無法主動更新。

### 方案

在每個步驟 EXECUTE 前，以輕量 prompt 請 Minimax 做「目標對齊審查」：
- 輸入：`global_goal` + 已完成步驟摘要 + 當前步驟定義
- 輸出：`PlanReview { needs_revision: bool, suggested_mutation: Optional[StepMutation] }`
- Gate：僅當 `global_goal` 已設定 + `step_idx > 0` + 此步驟尚未被前次審查修改過

> ⚠️ P2 優先級原因：每步驟多一次 Minimax API call（成本增加），需先驗證 Gap-011-A/B 的效益後再決定是否實作。

---

## 實作優先級矩陣

| Gap | 說明 | 優先級 | 影響 | 複雜度 | 建議順序 |
|-----|------|--------|------|--------|---------|
| Gap-011-A | Playbook global_goal 欄位 | **P0** | 高 | 低 | 第 1 |
| Gap-011-B | Minimax Step Mutation | **P1** | 高 | 中 | 第 2 |
| Gap-011-C | Pre-Step Goal Alignment | P2 | 中 | 高 | 待評估 |

---

## 執行 Checklist

### Gap-011-A（P0）
- [x] `autoclaude/models/playbook.py` — 新增 `global_goal` 欄位
- [x] `autoclaude/decision/prompt_builder.py` — `build_correction_message()` 注入 `global_goal`
- [x] `autoclaude/decision/minimax_client.py` — `decide_correction()` 傳遞 `global_goal`
- [x] `autoclaude/execution/playbook_runner.py` — 傳遞 `playbook.global_goal`
- [x] `scripts/example_playbook.yaml` — 新增範例欄位
- [x] 執行 `pytest tests/ -q` 確認 268+ tests pass

### Gap-011-B（P1）
- [x] 新建 `autoclaude/models/step_mutation.py`
- [x] `autoclaude/models/decision.py` — 加入 `step_mutation` 欄位
- [x] `autoclaude/decision/prompt_builder.py` — 加入 `allow_step_mutation` gate
- [x] `autoclaude/decision/minimax_client.py` — 傳遞 gate 參數
- [x] `autoclaude/execution/playbook_runner.py` — 應用 mutation 邏輯
- [x] 新增測試：`StepMutation` 解析、`REVISE_CURRENT` 應用、`INJECT_AFTER` 應用
- [x] 執行 `pytest tests/ -q` 確認所有 tests pass
