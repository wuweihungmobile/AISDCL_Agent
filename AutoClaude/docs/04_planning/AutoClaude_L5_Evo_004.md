# AutoClaude Level 5 動態閉環升級藍圖 Evo-004

**文檔版本**: v1.0  
**建立日期**: 2026-05-06  
**基準版本**: Evo-003（468 tests passing，Gap-014~020 全數實作完成）  
**文檔目的**: 對 AutoClaude Level 5 自治系統進行架構級深度漏洞挖掘，提出 Evo-004 升級藍圖

---

## Executive Summary

本文件基於對 `playbook_runner.py`、`convergence_monitor.py`、`prompt_builder.py`、`minimax_evolver.py` 與 `playbook_evolver.py` 的完整原始碼審查，針對使用者提出的三大核心議題進行深度漏洞挖掘，並推演「T00_INIT_ENV 前置注入情境」的完整執行路徑，發現 8 個新 Gap。

---

## `<thinking>` 深度思考分析

### 議題一：動態突變的圖靈完備性（Turing Completeness）

#### 現況盤點

當前六種突變類型的組合理論上可以實現任意的有限步驟執行圖：

| 突變類型 | 語意 | 限制 |
|---------|------|------|
| REVISE_CURRENT | 修改當前節點屬性 | — |
| INJECT_AFTER | 有向圖後置邊插入 | — |
| INJECT_BEFORE | 前置邊插入（立即執行） | 每 step_id 最多 3 次 |
| GOTO_STEP | 後向邊（循環） | 每 target 最多 3 次 |
| DELETE_STEP | 移除節點 | 僅限當前步驟之後 |
| SKIP_TO | 前向跳轉 | 每 step_id 最多 1 次 |

這使得執行圖從 DAG（有向無環圖）升格為帶防護的有限有向圖（Bounded Directed Graph）。

#### 識別出的關鍵缺口

**斷層 1：無條件式分支（Missing Conditional Branching）**

Minimax 的所有突變提議都是無條件的。系統無法表達：

```
if T00 的輸出符合 "requirements installed successfully":
    SKIP_TO T02  （跳過重複的環境設置）
else:
    INJECT_BEFORE T01_ENV_RETRY
```

這意味著 Minimax 只能採用「保守策略」——提議確定性的步驟，而無法根據執行時的動態條件自適應分叉。這是圖靈完備性的最後一塊缺失拼圖。

**斷層 2：批次突變的索引失效（Batch Mutation Index Invalidation）**

當 `batch_mutations` 包含 `INJECT_BEFORE` + `GOTO_STEP` 時：
1. INJECT_BEFORE 在 step_idx 位置插入新步驟，所有後序步驟的索引 +1
2. 後續 GOTO_STEP 中的 `goto_step_id` 以 step_id 字串查詢，理論上不受影響（`next((i for i, t in enumerate(playbook.tasks) if t.step_id == _target_id))`）
3. **但 INJECT_AFTER 若帶有預計算的插入位置則可能失效**

實際上由於 GOTO_STEP 和 SKIP_TO 使用 step_id 字串而非索引查詢，索引問題僅在批次中出現多個位置敏感操作時才會爆發。但 batch 批次內 INJECT_BEFORE 後若再有 INJECT_BEFORE，counter 的計數在同一次 batch 中可能被重複更新（counter 在 _apply_single_mutation 內即時更新，非 batch 結束後才更新）。

**斷層 3：GOTO 硬性 3 次限制過嚴**

對於複雜環境問題（例如 T01 需要「安裝依賴 → 驗證 → 設置配置 → 再驗證」多輪環境準備），3 次 GOTO 限制可能過早觸發 ESCALATION，遺漏真正可修復的路徑。

---

### 議題二：目標漂移防護（Goal Drift Guardrails）

#### 現有保護機制

```
global_goal 注入位置：
├── 首步驟（完整版 500 字）：_prepend_global_goal()
├── 所有非首步驟的首次 attempt（精簡版 150 字）：_prepend_global_goal_brief()
├── 每次 CORRECTION 的 user message 頂端：build_correction_message() goal_section
├── 每次 /compact 的 MEMORY ANCHOR：_send_compact() [GLOBAL_GOAL] 欄位（400 字）
└── 演化版 YAML：apply_evolution() 保留 global_goal 欄位
```

#### 識別出的關鍵漏洞

**漏洞 1：MinimaxEvolver 生成步驟時缺乏 global_goal 約束**

`build_evolution_message()` 的簽名：
```python
def build_evolution_message(
    step_id, step_name, step_prompt,
    failure_summary, escalation_reasoning,
) -> str:
```

**`global_goal` 參數缺失！** 這意味著當 MinimaxEvolver 為 INJECT_STEP 生成 `new_step_prompt` 時，Minimax 只看到失敗的步驟和失敗摘要，不知道整體目標是「建立 FastAPI 登入模組」。生成的前置步驟可能在局部技術層面正確，但語意方向偏離 global_goal。

**漏洞 2：GOAL_VALIDATION 僅依賴 step_log 字串，不含程式碼狀態**

```python
achievement_summary = "\n".join(step_log[-20:])
```

step_log 的典型內容：`"[T01] 實作 Auth 模組 ✓ (attempt 2)"`，完全不包含：
- 實際程式碼是否存在
- 介面是否互相相容（T01 的 Auth 與 T02 的 DB 是否使用相同的 User Model）
- 是否有遺漏的整合膠水層

**漏洞 3：SPLIT_STEP 後 Part A 無 evaluator_command，局部驗證失效**

當 `PlaybookEvolver.apply_evolution()` 執行 SPLIT_STEP：
- Part A：只有 regex 評估（繼承原步驟的評估邏輯？不，Part A 沒有設定 evaluator_command）
- Part B：繼承原步驟的 expected_output_regex + evaluator_command

Part A 的成功判定僅依賴 Claude Code 輸出文字的 regex，可能假陽性通過，導致 Part B 在有瑕疵的基礎上執行。

---

### 議題三：錯誤收斂與演化衝突（Convergence vs. Evolution Conflict）

#### 演化閉環的完整路徑

```
ESCALATION 觸發
    ↓
MinimaxEvolver.propose_evolution_via_ai()
    ↓ (或 fallback 至 PlaybookEvolver)
evolved_*.yaml 寫入磁碟
    ↓
PlaybookResult(evolved_playbook_path=...) 返回
    ↓
外層 while 迴圈偵測 evolved_playbook_path
    ↓
fresh=True，重新載入演化版 YAML
    ↓
_run_steps() 從步驟 0 開始
```

#### 遺失的關鍵狀態

| 狀態 | 是否遺失 | 影響 |
|-----|---------|------|
| `_mutation_log` | ✅ 完全遺失 | 演化版執行時 Minimax 不知道已嘗試過哪些突變 |
| `_step_trackers`（GOTO 熱啟動） | ✅ 完全遺失 | 演化版 T01 重訪時無法繼承已嘗試策略 |
| `_goal_synthesis_injected` | ✅ 重置（但OK，演化後應重新驗證） | — |
| `self._escalation_history` 索引 | ⚠️ 索引可能失效 | INJECT_STEP 後所有後序步驟索引 +1 |
| `FailureKnowledgeBase` | ✅ 正確持久化（JSONL） | — |
| Claude Code 對話 context | ✅ 正確清空（fresh=True） | — |

#### 關鍵遺失路徑的推演

演化後的 T01 重新執行，但 Minimax 不知道：
1. T01 在演化前已嘗試過 PINPOINT、REWRITE、ADD_TYPES 等策略（因 `_step_trackers` 遺失）
2. T01 的初始失敗根因是 ImportError（FailureKnowledgeBase 可查，但 error_signature 可能不同）

**結果**：演化版的 T01 可能重蹈同樣的錯誤路徑，浪費 2-3 次 retry 才重新收斂。

---

### 自我驗證推演（T00_INIT_ENV 情境）

**目標**：global_goal 為「建立 FastAPI 登入與資料庫連線模組」，初始步驟 T01（Auth）、T02（DB）。T01 執行時發現缺少 requirements.txt。

#### 完整執行路徑追蹤

```
T01 attempt 0 執行
    → ImportError（fastapi, sqlalchemy 未安裝）
    → error_class = IMPORT
    → _is_prerequisite_error = True

T01 attempt 1（allow_mutation = True，因 attempt >= 1 且 IMPORT）
    → Minimax CORRECTION：提議 INJECT_BEFORE（T00_INIT_ENV）
    → _apply_single_mutation():
        playbook.tasks.insert(step_idx=0, T00_INIT_ENV)  ✅
        result.inject_before_pending = True              ✅
        result.should_break = True                       ✅
    → break（跳出 attempt 迴圈）

外層 while 迴圈：
    if _inject_before_pending:
        _inject_before_pending = False
        continue  ← step_idx 不遞增！

while step_idx < len(playbook.tasks):  ← step_idx 仍為 0
    task = playbook.tasks[0] = T00_INIT_ENV  ✅ 正確
    correction_prompt = None  ← 重置！✅

T00 執行，建立 requirements.txt + pip install
T00 成功 → step_idx += 1 → step_idx = 1

task = playbook.tasks[1] = T01（原始位置）
_step_trackers 有 T01 舊 tracker → GOTO 熱啟動繼承 _tried_strategies ✅

T01 重新執行（已有 requirements.txt）→ 成功
```

**結論：機制是正確的！** INJECT_BEFORE 的完整閉環無縫運作。

#### 發現的真正斷層

**斷層 A**：`build_evolution_message()` 傳給 Minimax 時沒有 global_goal，所以 T00_INIT_ENV 的 `new_step_prompt` 缺乏目標對齊指導。T00 只知道「要修復 ImportError」，不知道最終要建立「FastAPI 登入模組」。

**斷層 B**：若 T01 在 T00 之後再次失敗（但 error 不同，例如型別錯誤），Minimax 可能再次提議 INJECT_BEFORE（T01_PRE2）。而 `_inject_before_counter["T01"]` 此時為 1（上次計數），允許再注入。但這次注入的步驟可能與 T00 功能重疊，累積無謂步驟。缺乏**步驟去重機制**（已存在的 step_id 前綴重複注入）。

**斷層 C**：T00 的 `new_step_prompt` 由 Minimax 自由生成，但沒有評估機制（演化注入的步驟沒有 evaluator_command）。T00 靠 regex 評估「pip install 成功」可能假陽性（pip 輸出含 "Requirement already satisfied" 也匹配 "successfully installed"）。

---

## Level 5 動態閉環升級藍圖

### 架構升級方向

```
Evo-004 三大升級軸：
┌─────────────────────────────────────────────────────────┐
│  軸 1：圖靈完備化（Turing Completeness）                │
│    Gap-021: ConditionalMutation — 條件式分支突變         │
│    Gap-025: Batch Mutation Index Safety — 批次索引安全   │
│                                                          │
│  軸 2：目標漂移防護強化（Goal Drift Hardening）         │
│    Gap-022: global_goal 注入 evolution message           │
│    Gap-023: GOAL_VALIDATION 語意強化（程式碼狀態感知）   │
│    Gap-026: SPLIT_STEP Part A evaluator 補完              │
│                                                          │
│  軸 3：演化狀態連續性（Evolution State Continuity）     │
│    Gap-024: Evolution Context Metadata（mutation_log持久）│
│    Gap-027: GOTO Context Contamination Guard             │
│    Gap-028: Step Deduplication（步驟去重）               │
└─────────────────────────────────────────────────────────┘
```

---

## Gap 詳細規格

### Gap-021：ConditionalMutation — 條件式分支突變（P0）

**問題**：現有突變全為無條件提議，無法表達「依執行結果動態分叉」。

**規格**：

在 `StepMutationType` 新增 `CONDITIONAL`；`StepMutation` 新增欄位：

```python
class StepMutationType(str, Enum):
    ...
    CONDITIONAL = "CONDITIONAL"  # Gap-021：條件式分支

class StepMutation(BaseModel):
    ...
    # Gap-021：CONDITIONAL 欄位
    condition_evaluator: Optional[str] = None   # shell 指令，exit 0 = true
    true_mutation: Optional["StepMutation"] = None   # 條件成立時執行的突變
    false_mutation: Optional["StepMutation"] = None  # 條件不成立時執行的突變
```

在 `_apply_single_mutation()` 中處理：

```python
elif mutation.mutation_type == StepMutationType.CONDITIONAL:
    # 執行 condition_evaluator，依 exit code 選擇分支突變
    _cond_exit = subprocess.run(mutation.condition_evaluator, shell=True, ...).returncode
    _branch = mutation.true_mutation if _cond_exit == 0 else mutation.false_mutation
    if _branch:
        return self._apply_single_mutation(_branch, ...)
```

在 `_MUTATION_SCHEMA_SECTION` 新增 CONDITIONAL 的 JSON schema 說明。

**受益場景**：
- 若 requirements.txt 已存在（exit 0）→ SKIP_TO T02，否則 INJECT_BEFORE T00_INIT_ENV
- 若前序步驟輸出已含目標產出（grep 確認）→ DELETE 冗餘步驟

---

### Gap-022：Evolution Message 注入 global_goal（P0）

**問題**：`build_evolution_message()` 未傳入 `global_goal`，MinimaxEvolver 生成前置步驟時缺乏目標對齊。

**規格**：

```python
# prompt_builder.py
def build_evolution_message(
    step_id: str,
    step_name: str,
    step_prompt: str,
    failure_summary: str,
    escalation_reasoning: str,
    global_goal: Optional[str] = None,  # Gap-022：新增
) -> str:
    goal_section = f"## 系統總目標（確保演化步驟對齊此目標）\n{global_goal}\n\n" if global_goal else ""
    return (
        f"{goal_section}"  # 注入頂端
        f"## 失敗步驟\n{step_id}: {step_name}\n\n"
        ...
    )
```

```python
# minimax_client.py — propose_evolution() 新增 global_goal 參數
def propose_evolution(self, ..., global_goal: Optional[str] = None) -> EvolutionDecision:
    user_msg = build_evolution_message(..., global_goal=global_goal)
    ...
```

```python
# minimax_evolver.py — propose_evolution_via_ai() 傳遞 global_goal
def propose_evolution_via_ai(self, playbook, failed_step_idx, escalation_dump, minimax_client):
    ...
    decision = minimax_client.propose_evolution(
        ...,
        global_goal=playbook.global_goal,  # Gap-022：傳入
    )
```

```python
# playbook_runner.py — 兩個 ESCALATION 路徑均傳入 global_goal
_proposal = self._minimax_evolver.propose_evolution_via_ai(
    playbook, step_idx, _dump, self._minimax
)
# MinimaxEvolver 已從 playbook 取得 global_goal，無需額外傳入（在 propose_evolution_via_ai 中處理）
```

---

### Gap-023：GOAL_VALIDATION 語意強化（P1）

**問題**：`_validate_global_goal_achievement()` 僅使用 step_log 字串，缺乏程式碼狀態感知。

**規格**：

在 `_validate_global_goal_achievement()` 中加入 git diff 摘要：

```python
def _validate_global_goal_achievement(self, playbook, step_log, global_goal):
    achievement_summary = "\n".join(step_log[-20:])
    
    # Gap-023：補充 git diff 統計資訊（函式簽名層級）
    _code_state = build_file_state_snapshot()  # 已有此工具函式
    
    decision = self._minimax.validate_goal_achievement(
        global_goal=global_goal,
        step_summary=achievement_summary,
        playbook_project=playbook.project,
        code_state_snapshot=_code_state,  # Gap-023：新增參數
    )
```

```python
# minimax_client.py — validate_goal_achievement() 新增 code_state_snapshot
def validate_goal_achievement(
    self, global_goal, step_summary, playbook_project,
    code_state_snapshot: str = "",  # Gap-023
) -> GoalAchievementDecision:
    user_msg = build_goal_validation_message(
        global_goal, step_summary, playbook_project,
        code_state_snapshot=code_state_snapshot,
    )
```

```python
# prompt_builder.py — build_goal_validation_message() 新增 code_state_snapshot
def build_goal_validation_message(
    global_goal, step_summary, playbook_project,
    code_state_snapshot: str = "",  # Gap-023
) -> str:
    code_section = f"## 已修改的程式碼檔案（函式級快照）\n{code_state_snapshot}\n\n" if code_state_snapshot else ""
    return (
        f"## 專案\n{playbook_project}\n\n"
        f"## 系統總目標\n{global_goal}\n\n"
        f"{code_section}"
        f"## 已完成的步驟記錄（最近 20 筆）\n{step_summary}\n\n"
        "請判斷以上步驟的組合是否真正達成了系統總目標，輸出驗證 JSON。"
    )
```

---

### Gap-024：Evolution Context Metadata 持久化（P1）

**問題**：演化版 YAML 重載後 `_mutation_log` 和失敗策略上下文完全遺失。

**規格**：

在 `Playbook` 模型中新增 `evolution_metadata` 欄位（`models/playbook.py`）：

```python
class EvolutionMetadata(BaseModel):
    """演化上下文持久化（供 evolved Playbook 重載時恢復）"""
    generation: int = 0           # 演化代數（0 = 原始，1 = 第一次演化...）
    mutation_log: list[str] = Field(default_factory=list)  # 已執行突變歷史
    escalated_step_ids: list[str] = Field(default_factory=list)  # 已 ESCALATION 步驟

class Playbook(BaseModel):
    ...
    evolution_metadata: Optional[EvolutionMetadata] = None  # Gap-024
```

在 `PlaybookEvolver.apply_evolution()` 中序列化：

```python
def apply_evolution(self, playbook, proposal, playbook_path, mutation_log=None) -> str:
    ...
    evolved_playbook = Playbook(
        ...
        evolution_metadata=EvolutionMetadata(
            generation=(playbook.evolution_metadata.generation + 1 if playbook.evolution_metadata else 1),
            mutation_log=list(mutation_log or []),
            escalated_step_ids=[d.step_id for d in self._escalation_history] if hasattr(self, '_escalation_history') else [],
        ),
    )
```

在 `PlaybookRunner._run_steps()` 重載時恢復：

```python
# 重載演化版 Playbook 後，恢復 mutation_log
if playbook.evolution_metadata and playbook.evolution_metadata.mutation_log:
    _mutation_log = list(playbook.evolution_metadata.mutation_log)
    logger.info("Gap-024 | 恢復演化版 mutation_log: %d 筆", len(_mutation_log))
```

---

### Gap-025：Batch Mutation Index Safety（P1）

**問題**：批次突變中的 INJECT_BEFORE counter 在同一批次多次更新，且複合突變間存在隱性依賴。

**規格**：

在 `_apply_single_mutation()` 批次處理前，新增相容性預驗證：

```python
def _validate_batch_compatibility(self, batch: list[StepMutation]) -> tuple[bool, str]:
    """
    Gap-025：批次突變相容性預驗證。
    規則：
    1. 批次中最多一個 INJECT_BEFORE（避免同步驟多次注入）
    2. GOTO_STEP 與 INJECT_BEFORE 不可同時存在（索引語意衝突）
    3. CONDITIONAL 突變不得嵌套於批次中（複雜度過高）
    """
    types = [m.mutation_type for m in batch]
    inject_before_count = types.count(StepMutationType.INJECT_BEFORE)
    if inject_before_count > 1:
        return False, f"批次中 INJECT_BEFORE 超過 1 次（共 {inject_before_count} 次）"
    if (StepMutationType.GOTO_STEP in types and StepMutationType.INJECT_BEFORE in types):
        return False, "GOTO_STEP 與 INJECT_BEFORE 不可同時存在於批次中"
    if StepMutationType.CONDITIONAL in types:
        return False, "CONDITIONAL 突變不支援批次模式"
    return True, ""
```

在批次突變前置處理段落呼叫此驗證：

```python
# playbook_runner.py 批次突變處理（Gap-019-B 區段）
if _step_mutation is not None and _step_mutation.batch_mutations:
    _batch = _step_mutation.batch_mutations[:3]
    # Gap-025：批次相容性預驗證
    _valid, _reason = self._validate_batch_compatibility(_batch)
    if not _valid:
        logger.warning("=== Gap-025 | 批次突變相容性失敗（%s），降級為單一突變 ===", _reason)
        _step_mutation = _batch[0]  # 降級：只執行第一個突變
        # 繼續走單一突變路徑...
    else:
        for _batch_m in _batch:
            ...
```

---

### Gap-026：SPLIT_STEP Part A 評估補完（P2）

**問題**：`PlaybookEvolver` 和 `MinimaxEvolver` 的 SPLIT_STEP 產生的 Part A 步驟沒有 `evaluator_command`，只依賴 Claude Code 輸出的 regex 評估，容易假陽性。

**規格**：

在 `PlaybookEvolver.propose_evolution()` 的 SPLIT_STEP 分支中，為 Part A 加入最小評估：

```python
# Part A 步驟：加入基本語法驗證
PlaybookTask(
    step_id=sub1_id,
    name=f"{failed_task.name}（第一部分）",
    prompt=prompt_a or failed_task.prompt,
    # Gap-026：若原步驟有 evaluator_command，提取 collect-only 部分作為 Part A 的輕量評估
    evaluator_command=_derive_part_a_evaluator(failed_task.evaluator_command),
    max_retries=failed_task.max_retries,
),
```

新增 helper：

```python
def _derive_part_a_evaluator(original_evaluator: Optional[str]) -> Optional[str]:
    """
    Gap-026：從原步驟 evaluator 推導 Part A 的輕量評估指令。
    - pytest 指令 → pytest --collect-only（確保至少語法正確）
    - python 指令 → python -c 'import ast; ast.parse(open(...).read())'
    - 其他 → None（不強制評估）
    """
    if not original_evaluator:
        return None
    if "pytest" in original_evaluator:
        return "pytest --collect-only -q"
    if original_evaluator.strip().startswith("python"):
        return "python -m py_compile $(git diff --name-only HEAD | grep '.py' | head -1) 2>&1 || true"
    return None
```

---

### Gap-027：GOTO_STEP 對話 Context 污染防護（P2）

**問題**：GOTO_STEP 跳回前序步驟時，Claude Code 對話 context 仍含從 GOTO 目標到當前步驟的所有失敗歷史，可能干擾重訪的步驟。

**規格**：

在 `_step_trackers` 的 GOTO 熱啟動邏輯之後，注入 context clean hint：

```python
# playbook_runner.py — _run_steps() 中，步驟開始時
if task.step_id in _step_trackers and step_idx < _prev_step_idx:
    # 這是 GOTO 重訪（向後跳轉）
    logger.info("=== Gap-027 | GOTO 重訪 [%s]，注入 context clean hint ===", task.step_id)
    _cross_hint = (
        f"⚠️ 重要提示（GOTO 重訪）：系統已判斷需要重新執行步驟 {task.step_id}。\n"
        f"請忽略此步驟之前所有失敗的修改嘗試，從當前程式碼狀態重新分析並修正。\n"
        f"優先使用 Read 工具確認當前檔案狀態，不要假設之前的修改已套用。\n\n"
    )
```

新增 `_prev_step_idx` 追蹤：

```python
_prev_step_idx = -1  # 追蹤上一個執行的步驟索引

while step_idx < len(playbook.tasks):
    task = playbook.tasks[step_idx]
    ...
    # 在步驟結束時更新
    _prev_step_idx = step_idx
    step_idx += 1 / continue / goto
```

---

### Gap-028：INJECT_BEFORE 步驟去重機制（P2）

**問題**：若 T01 在 T00 注入後再次失敗，Minimax 可能再次提議 INJECT_BEFORE（T01_PRE2），造成語意重疊的步驟累積。

**規格**：

在 `_apply_single_mutation()` 的 INJECT_BEFORE 處理中，加入 step_id 前綴去重：

```python
elif mutation.mutation_type == StepMutationType.INJECT_BEFORE and mutation.new_step_prompt:
    _proposed_id = mutation.new_step_id or f"{task.step_id}_PRE"
    
    # Gap-028：檢查是否已存在相似功能的前置步驟
    _existing_ids = {t.step_id for t in playbook.tasks}
    _base_prefix = _proposed_id.rstrip("_0123456789").rstrip("_PRE") 
    _similar_existing = [sid for sid in _existing_ids if sid.startswith(_base_prefix) and sid != task.step_id]
    if _similar_existing:
        logger.warning(
            "=== Gap-028 | INJECT_BEFORE 偵測到相似前置步驟已存在 %s，修改 step_id 避免語意重疊 ===",
            _similar_existing,
        )
        # 使用遞增序號確保唯一性
        _cnt_suffix = _inject_before_counter.get(task.step_id, 0) + 1
        _proposed_id = f"{task.step_id}_PRE_{_cnt_suffix}"
    
    _pre_task = PlaybookTask(
        step_id=_proposed_id,
        ...
    )
```

---

## 迭代行動清單（Action Items）

### P0 — 最高優先級（必須在下次 QA 前完成）

| # | Gap | 修改檔案 | 說明 |
|---|-----|---------|------|
| 1 | Gap-021-A | `autoclaude/models/step_mutation.py` | 新增 `CONDITIONAL` 至 `StepMutationType`，新增 `condition_evaluator`, `true_mutation`, `false_mutation` 欄位 |
| 2 | Gap-021-B | `autoclaude/execution/playbook_runner.py` | `_apply_single_mutation()` 新增 CONDITIONAL 分支，遞迴呼叫自身 |
| 3 | Gap-021-C | `autoclaude/decision/prompt_builder.py` | `_MUTATION_SCHEMA_SECTION` 新增 CONDITIONAL JSON schema 說明 |
| 4 | Gap-022-A | `autoclaude/decision/prompt_builder.py` | `build_evolution_message()` 新增 `global_goal: Optional[str]` 參數 |
| 5 | Gap-022-B | `autoclaude/decision/minimax_client.py` | `propose_evolution()` 新增 `global_goal` 參數並傳遞至 build_evolution_message |
| 6 | Gap-022-C | `autoclaude/evolution/minimax_evolver.py` | `propose_evolution_via_ai()` 從 `playbook.global_goal` 取值並傳遞 |

### P1 — 重要（本次迭代完成）

| # | Gap | 修改檔案 | 說明 |
|---|-----|---------|------|
| 7 | Gap-023-A | `autoclaude/decision/prompt_builder.py` | `build_goal_validation_message()` 新增 `code_state_snapshot` 參數 |
| 8 | Gap-023-B | `autoclaude/decision/minimax_client.py` | `validate_goal_achievement()` 新增 `code_state_snapshot` 參數 |
| 9 | Gap-023-C | `autoclaude/execution/playbook_runner.py` | `_validate_global_goal_achievement()` 呼叫 `build_file_state_snapshot()` 並傳遞 |
| 10 | Gap-024-A | `autoclaude/models/playbook.py` | 新增 `EvolutionMetadata` Pydantic 模型，`Playbook` 新增 `evolution_metadata` 欄位 |
| 11 | Gap-024-B | `autoclaude/evolution/playbook_evolver.py` | `apply_evolution()` 新增 `mutation_log` 參數，序列化至 `evolution_metadata` |
| 12 | Gap-024-C | `autoclaude/execution/playbook_runner.py` | 演化版 YAML 重載後恢復 `_mutation_log`，兩個 ESCALATION 路徑傳入 `mutation_log` |
| 13 | Gap-025-A | `autoclaude/execution/playbook_runner.py` | 新增 `_validate_batch_compatibility()` 方法 |
| 14 | Gap-025-B | `autoclaude/execution/playbook_runner.py` | 批次突變前置處理段落呼叫相容性預驗證，不相容時降級為單一突變 |

### P2 — 改善（下一迭代完成）

| # | Gap | 修改檔案 | 說明 |
|---|-----|---------|------|
| 15 | Gap-026-A | `autoclaude/evolution/playbook_evolver.py` | 新增 `_derive_part_a_evaluator()` helper，SPLIT_STEP Part A 設定輕量評估 |
| 16 | Gap-026-B | `autoclaude/evolution/minimax_evolver.py` | `_convert_to_proposal()` SPLIT_STEP 分支同步加入 Part A evaluator 推導 |
| 17 | Gap-027-A | `autoclaude/execution/playbook_runner.py` | 新增 `_prev_step_idx` 追蹤，GOTO 重訪時注入 context clean hint |
| 18 | Gap-028-A | `autoclaude/execution/playbook_runner.py` | `_apply_single_mutation()` INJECT_BEFORE 分支加入 step_id 前綴去重邏輯 |

---

## 測試需求（TDD）

每個 Gap 實作後必須新增對應測試至 `tests/test_gap021_028.py`：

| 測試類別 | Gap | 測試情境 |
|---------|-----|---------|
| `TestGap021ConditionalMutation` | 021 | condition exit 0 → true_mutation 套用 |
| `TestGap021ConditionalMutation` | 021 | condition exit 1 → false_mutation 套用 |
| `TestGap021ConditionalMutation` | 021 | condition_evaluator 為 None → 跳過 |
| `TestGap022EvolutionGoalAlignment` | 022 | `build_evolution_message` 含 global_goal 區段 |
| `TestGap022EvolutionGoalAlignment` | 022 | `propose_evolution_via_ai` 傳遞 global_goal 至 Minimax |
| `TestGap023GoalValidationEnhanced` | 023 | code_state_snapshot 納入 validation message |
| `TestGap024EvolutionContextContinuity` | 024 | evolved YAML 含 evolution_metadata.mutation_log |
| `TestGap024EvolutionContextContinuity` | 024 | Runner 重載演化版後 _mutation_log 正確恢復 |
| `TestGap025BatchMutationSafety` | 025 | INJECT_BEFORE + GOTO_STEP 批次被降級 |
| `TestGap025BatchMutationSafety` | 025 | 2 個 INJECT_BEFORE 批次被降級 |
| `TestGap026SplitStepEvaluator` | 026 | pytest evaluator → `--collect-only` Part A evaluator |
| `TestGap027GotoContextClean` | 027 | GOTO 重訪時 _cross_hint 含 context clean hint |
| `TestGap028InjectBeforeDeduplicate` | 028 | 相似前綴 step_id 二次注入時使用遞增序號 |

---

## 預計新增測試數量

- P0：6 個測試（Gap-021 × 3, Gap-022 × 2, 驗證訊息 × 1）
- P1：7 個測試（Gap-023 × 1, Gap-024 × 2, Gap-025 × 2, 其他 × 2）
- P2：4 個測試（Gap-026 × 1, Gap-027 × 1, Gap-028 × 1, 整合 × 1）
- **合計：17 個新測試**（預計由 468 → 485 個通過）

---

## 文檔元數據

- **文檔版本**: v1.0
- **建立日期**: 2026-05-06
- **基準測試數**: 468 passed
- **預計新增測試**: 17 個（總計達 485）
- **維護者**: AutoClaude 專案團隊
- **文檔狀態**: Active — 待實作
