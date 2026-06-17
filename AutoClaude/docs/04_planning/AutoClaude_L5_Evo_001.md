# AutoClaude Level 5 動態閉環升級藍圖 — Evo-001

**文件版本**: v1.0  
**建立日期**: 2026-05-04  
**作者**: 首席 AI 自動化架構師分析（Chief AI Automation Architect Review）  
**前置分析對象**: Gap-009 ~ Gap-011 完成後的現有系統  
**文件狀態**: CLOSED@implemented（improving_26 狀態和解，2026-06-17）— 圖靈完備核心缺口（Gap-012-A INJECT_BEFORE / Gap-012-B GOTO_STEP / Gap-012-C DELETE_STEP）**已落地**：`core/services/mutation/inject_before.py`、`goto_step.py`、`delete_step.py` + `plugins/goto_counter_plugin.py`（loop guard）+ checkpoint 4 counter。詳見根層 `docs/04_planning/AutoSDD_improving_26.md` §3.2。
**原下一步（已完成，存史）**: 實作 Gap-012-A ~ Gap-012-F

---

## 一、深度思考：三大核心議題漏洞挖掘

### 1.1 動態突變的圖靈完備性分析

#### 現況觀察

目前 `StepMutationType`（`autoclaude/models/step_mutation.py`）僅定義兩種突變：

```
REVISE_CURRENT  → 就地更新當前步驟的 prompt 定義
INJECT_AFTER    → 在當前步驟「之後」插入一個新的輔助步驟
```

`_run_steps()`（`autoclaude/execution/playbook_runner.py:263`）的執行模型為：

```
while step_idx < len(playbook.tasks):   ← 外層線性推進
    for attempt in range(...):           ← 內層重試迴圈
        if INJECT_AFTER:
            playbook.tasks.insert(step_idx + 1, _new_task)
    step_idx += 1                        ← 永遠向前推進，無跳躍機制
```

#### 致命缺口 1：缺少 INJECT_BEFORE（前置注入）

當 Minimax 發現當前步驟的「前提條件」不滿足（如環境未初始化），唯一能做的是 `INJECT_AFTER`——插入一個執行在「當前步驟成功後」才跑的步驟。

**這在邏輯上是自相矛盾的**：如果前提條件不滿足導致當前步驟失敗，那注入到其「之後」的修復步驟永遠不會執行。

缺少的類型：`INJECT_BEFORE` — 在當前步驟「之前」插入前置步驟，並立即執行該前置步驟。

#### 致命缺口 2：缺少 GOTO_STEP（步驟跳轉）

若系統在 T03 執行過程中發現 T01 的輸出物件（某個 config 檔）有誤，現有系統無法回頭重新執行 T01。這使得系統的「自修復半徑」被硬性限制在「當前步驟的 max_retries 以內」。

真正的圖靈完備閉環需要類似 `goto` 的能力：跳回指定步驟重新執行（需配合無限迴圈防護機制）。

#### 致命缺口 3：缺少 DELETE_STEP（冗餘步驟刪除）

若 Minimax 判斷後續某個步驟因為當前上下文的改變而已經成為冗餘（例如 T03 要執行的初始化，在 INJECT_BEFORE 的前置步驟中已完成），無法刪除它。

這導致系統會繼續執行明知多餘的步驟，浪費資源且可能引入衝突。

#### 圖靈完備性判定

| 能力 | 圖靈機類比 | 現有支援 | 缺口 |
|------|-----------|---------|------|
| 順序執行 | 磁帶向右移動 | ✅ while step_idx++ | — |
| 條件分支 | 狀態轉換函數 | ✅ ConvergenceMonitor | — |
| 迴圈（前向） | 插入後重新執行 | ✅ INJECT_AFTER（有限） | — |
| 迴圈（後向） | 磁帶向左移動 | ❌ 無 GOTO | Gap-012-B |
| 前置注入 | 在當前位置插入 | ❌ 無 INJECT_BEFORE | Gap-012-A |
| 狀態清除 | 抹除磁帶符號 | ❌ 無 DELETE_STEP | Gap-012-C |

**結論**：現有系統是「有向無環圖（DAG）」狀態機，不是圖靈完備的。它可以向前擴展 Playbook，但無法回頭或剪除。

---

### 1.2 目標漂移防護（Goal Drift Guardrails）分析

#### `global_goal` 在 Minimax 決策層的保障（有效）

`build_correction_message()`（`autoclaude/decision/prompt_builder.py:131`）在每次 Minimax 決策的 user message 頂端注入：

```python
goal_section = f"## 系統總目標\n{global_goal}\n\n" if global_goal else ""
```

這保證 Minimax 的「修正大腦」每次都從總目標出發判斷。

**但這只保護了「診斷層」**。

#### 致命漏洞：`global_goal` 在 Claude Code 執行層消失於 `/compact`

`_send_compact()`（`autoclaude/execution/playbook_runner.py:1174`）的 MEMORY ANCHOR 只保留：

```python
anchor = (
    "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
    f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
    f"[ATTEMPT] {attempt + 1}\n"
    f"[SUCCESS_CONDITION] output must match: ...\n"
    f"[LAST_FAILURE] ...\n"
    "=== END ANCHOR ===\n"
)
```

**`global_goal` 完全不在 compact 的 MEMORY ANCHOR 中**。

這意味著：

1. 多次 `/compact` 後，Claude Code（執行者）的 context 已不知道系統總目標是什麼
2. Minimax（診斷者）看到總目標並產生修正 prompt
3. 但修正 prompt 到達 Claude Code 時，Claude Code 可能用局部最優解（通過當前測試）代替全局最優解（實現 global_goal）
4. 例如：`global_goal` = 「建立 FastAPI 登入模組」，但 Claude Code 在 compact 後忘了這個，可能用 Flask 實作（通過了某個測試，但偏離了目標）

#### `task_goal_summary` 壓縮機制的侷限（Gap-010-B）

在 retry >= 3 時，`task_prompt` 被替換為 `task_goal_summary`（30 字摘要）。這個摘要由 Minimax 在首次修正時生成，並快取在 `_task_goal_summary` 變數。

問題：此摘要是「步驟目標」，不是「系統總目標」。當系統進行多次 INJECT_AFTER 後，執行的步驟可能已不是原始步驟，`_task_goal_summary` 屬於舊步驟的快取，而 `global_goal` 的絕對不變量地位未被強制維護。

**結論**：`global_goal` 作為不變量的保障是「單層」的（Minimax 決策層），在執行層（Claude Code context）無法保證跨 compact 存活。

---

### 1.3 錯誤收斂與演化衝突分析

#### 演化閉環的致命斷層

當 ESCALATION 觸發 `PlaybookEvolver` 時（`playbook_runner.py:485-502`）：

```python
# Gap-010-E：Playbook 自演化（Level 5）
_proposal = self._evolver.propose_evolution(
    playbook, step_idx, _dump, self._escalation_history
)
if _proposal:
    _evolved_path = self._evolver.apply_evolution(playbook, _proposal, playbook_path)
    self._notify("AutoClaude — Playbook 自動演化（Level 5）", ...)

# ← 緊接著：
return PlaybookResult(
    False, len(step_log), total,
    f"[{task.step_id}] {report.reasoning}",
    workflow, step_log,
)
```

**系統在演化後立即退出（success=False）**。演化版 `evolved_*.yaml` 被寫入磁碟，但永遠不會自動執行。

這使得 `PlaybookEvolver` 實際上是「把演化結果寫入磁碟，然後告訴人類去手動執行」——它不是真正的自治演化，而是「輔助演化建議器」。

#### Token Context 的遺失問題

當 ESCALATION 發生時：
- Claude Code 的 PTY process 已結束（或即將結束）
- 如果人類手動執行 `evolved_*.yaml`，Claude Code 啟動一個全新 session
- 原本的 context（T01 執行中學到的細節、已修改的檔案、錯誤模式）全部消失

`FailureKnowledgeBase` 跨 session 持久化（JSONL 檔案），這部分是安全的。但 Claude Code 的對話 context 無法被 checkpoint 保存，演化後的 T01_PRE 步驟沒有任何「前世記憶」。

#### 演化後 Checkpoint 不一致

`apply_evolution()` 修改了 `playbook.tasks`（插入/拆分步驟），但：

1. 演化是寫入「新的 `evolved_*.yaml`」，而不是修改原 Playbook 物件
2. 原 checkpoint（`checkpoint_manager.save()`）的 `step_id` 和 `step_idx` 指向原 Playbook 結構
3. 若人類用 `evolved_*.yaml` 重跑，`_resolve_start()` 會檢測到 `step_id` 不一致（因為插入步驟改變了索引），然後從頭重跑

**這其實是正確行為**（因為 INJECT_STEP 在失敗步驟前插入了新步驟，確實需要從頭執行），但問題是系統無法自動觸發這個重跑。

---

## 二、Self-Verification Protocol：推演情境斷層定位

### 情境：T01 執行中發現 requirements.txt 缺失

**初始狀態**：`global_goal` = 「建立一個完整的 FastAPI 登入與資料庫連線模組」  
**任務**: T01（Write Auth）、T02（Write DB）

```
執行流程追蹤：

attempt=0: T01 執行 → 失敗（ModuleNotFoundError: fastapi）
           error_class = IMPORT
           allow_mutation = False（attempt < 2）
           ↓ CORRECTION：Minimax 建議修正 import 語句（治標不治本）

attempt=1: T01 執行 → 失敗（requirements.txt 仍不存在）
           allow_mutation = False（attempt < 2）
           ↓ CORRECTION：Minimax 再次建議（策略輪換）

attempt=2: T01 執行 → 失敗（同樣錯誤，error_sig 相同）
           allow_mutation = True（attempt >= 2 且 trend=stuck）
           ↓ Minimax 可以提議 INJECT_AFTER
           ↓ Minimax 提議：INJECT_AFTER → T01_INIT_ENV（建立 requirements.txt）
           ↓ playbook.tasks.insert(1, T01_INIT_ENV)
              [T01, T01_INIT_ENV, T02]
           ↓ 繼續 attempt=2 的修正循環（T01 仍在同一個 for loop 中！）

attempt=3: T01 執行 → 失敗（T01_INIT_ENV 還沒執行！）
           ↓ ErrorBudget: import class limit = 2 → attempt+budget = 3+2 = 5 > max_retries=3
              實際上 effective_max_retries = min(3, 2+2) = min(3,4) = 3
              attempt=3 >= max_retries=3 → ESCALATION

↓ ESCALATION 觸發：
   FailureKnowledgeBase.record_escalation()  ← OK，記錄失敗策略
   PlaybookEvolver.propose_evolution()
     → is_stuck=True, len(failure_chain)=3 → SPLIT_STEP
     → T01 被拆為 T01_A（前半段 prompt）和 T01_B（後半段 prompt）
     → 但 T01_A 和 T01_B 都仍需要 requirements.txt！！
   apply_evolution() 寫入 evolved_example_playbook.yaml
   return PlaybookResult(success=False)  ← 系統退出

←←← 人類必須手動執行 evolved_example_playbook.yaml ←←←
←←← T01_INIT_ENV 步驟（INJECT_AFTER 注入的那個）還在 in-memory playbook 中，
     但「evolved_」版本是由 apply_evolution 從原始 playbook 產生，
     不包含 in-memory 的 INJECT_AFTER！！！！
```

### 斷層清單

| # | 斷層位置 | 描述 | 嚴重度 |
|---|---------|------|--------|
| **B-1** | `StepMutationType` | 無 `INJECT_BEFORE`，無法在失敗步驟前注入前置步驟 | 🔴 致命 |
| **B-2** | `_run_steps()` L718 | `INJECT_AFTER` 的步驟永遠在「當前步驟成功」後才執行 | 🔴 致命 |
| **B-3** | `_run_steps()` L499-503 | ESCALATION 後立即 return，演化版 Playbook 從未自動執行 | 🔴 致命 |
| **B-4** | `apply_evolution()` L164 | 演化從原始 `playbook.tasks` 複製，不含 in-memory 的 INJECT_AFTER 步驟 | 🟠 嚴重 |
| **B-5** | `_send_compact()` L1185-1198 | MEMORY ANCHOR 不含 `global_goal`，執行層目標漂移 | 🟠 嚴重 |
| **B-6** | `PlaybookEvolver.propose_evolution()` | SPLIT_STEP 的 prompt 分割是字串切割，不理解語意 | 🟡 中等 |

---

## 三、Level 5 動態閉環升級藍圖

### 架構設計原則

```
Level 5 真正自治系統需要的完整狀態機：

global_goal（不可變量）
    ↓ 常數注入到 Minimax AND Claude Code context
    ↓
步驟圖（動態有向圖，而非靜態 DAG）
    ↓
支援：向前插入、向後跳轉、刪除冗餘、自動重載演化版
    ↓
閉環：演化 → 立即重執行（不需人工）
```

### Gap-012-A：新增 `INJECT_BEFORE` 突變類型

**目標**：允許 Minimax 在失敗步驟「之前」注入前置步驟，並立即切換執行它。

**修改檔案**：`autoclaude/models/step_mutation.py`

```python
class StepMutationType(str, Enum):
    REVISE_CURRENT = "REVISE_CURRENT"
    INJECT_AFTER = "INJECT_AFTER"
    INJECT_BEFORE = "INJECT_BEFORE"   # ← 新增：在當前步驟前注入，並立即執行新步驟
    DELETE_STEP = "DELETE_STEP"       # ← Gap-012-C
    GOTO_STEP = "GOTO_STEP"           # ← Gap-012-B
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`

```python
# _run_steps() 中，在 for attempt loop 外層加入 flag：
_inject_before_pending = False
_goto_target_idx: Optional[int] = None

# 在 INJECT_BEFORE 處理：
elif (
    _step_mutation.mutation_type == StepMutationType.INJECT_BEFORE
    and _step_mutation.new_step_prompt
):
    _new_task = PlaybookTask(
        step_id=_step_mutation.new_step_id or f"{task.step_id}_PRE",
        name=_step_mutation.new_step_name or f"前置步驟（注入於 {task.step_id} 前）",
        prompt=_step_mutation.new_step_prompt,
    )
    playbook.tasks.insert(step_idx, _new_task)
    _inject_before_pending = True
    logger.info(
        "=== Gap-012-A | INJECT_BEFORE 插入步驟 %s 於 %s 前，立即切換執行 ===",
        _new_task.step_id, task.step_id,
    )
    break  # 跳出 for attempt loop

# for attempt loop 結束後：
if _inject_before_pending:
    # step_idx 現在指向剛插入的前置步驟，不要 increment
    continue  # 回到 while loop，執行前置步驟

step_idx += 1
```

**修改 StepMutation model**：新增 `new_step_id`, `new_step_name`, `new_step_prompt` 欄位（已存在），以及 `goto_step_id`（Gap-012-B 用）。

**修改 prompt_builder.py**：在 `_MUTATION_SCHEMA_SECTION` 中加入第 3 種 mutation type 說明：

```
3. INJECT_BEFORE — 在當前步驟「之前」插入前置步驟，並立即執行它（用於解決前提條件缺失）：
```

---

### Gap-012-B：新增 `GOTO_STEP` 突變類型

**目標**：允許 Minimax 在偵測到前序步驟輸出有誤時，跳回指定步驟重新執行。

**需要無限迴圈防護**：每個步驟的 GOTO 次數上限為 3 次，超過則 ESCALATION。

**修改檔案**：`autoclaude/models/step_mutation.py`

```python
class StepMutation(BaseModel):
    # 現有欄位...
    goto_step_id: Optional[str] = None   # GOTO_STEP 時填寫：目標步驟的 step_id
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`

```python
# _run_steps() 開頭加入 GOTO 計數器：
_goto_counter: dict[str, int] = {}  # step_id → goto 次數

# GOTO_STEP 處理：
elif _step_mutation.mutation_type == StepMutationType.GOTO_STEP and _step_mutation.goto_step_id:
    target_id = _step_mutation.goto_step_id
    target_idx = next(
        (i for i, t in enumerate(playbook.tasks) if t.step_id == target_id), None
    )
    if target_idx is None:
        logger.warning("Gap-012-B: GOTO 目標步驟 %s 不存在，忽略", target_id)
    elif target_idx >= step_idx:
        logger.warning("Gap-012-B: 禁止 GOTO 向前（target=%s），只允許向後跳轉", target_id)
    else:
        _goto_counter[target_id] = _goto_counter.get(target_id, 0) + 1
        if _goto_counter[target_id] > 3:
            logger.error("Gap-012-B: GOTO %s 已執行 %d 次，防無限迴圈 → ESCALATION",
                         target_id, _goto_counter[target_id])
            return PlaybookResult(False, ..., "GOTO 無限迴圈防護觸發")
        _goto_target_idx = target_idx
        logger.info("Gap-012-B: GOTO 跳轉至步驟 %s（第 %d 次）",
                    target_id, _goto_counter[target_id])
        break

# for loop 結束後：
if _goto_target_idx is not None:
    step_idx = _goto_target_idx
    _goto_target_idx = None
    continue

step_idx += 1
```

---

### Gap-012-C：新增 `DELETE_STEP` 突變類型

**目標**：允許 Minimax 刪除後續已確定冗餘的步驟。

**安全約束**：
- 只能刪除「當前步驟之後」的步驟（不能刪已完成的）
- 最多一次刪除 1 個步驟（防止誤操作）
- 刪除時記錄到 EscalationDump 的 step_log

**修改檔案**：`autoclaude/models/step_mutation.py`

```python
class StepMutation(BaseModel):
    # 現有欄位...
    delete_step_id: Optional[str] = None  # DELETE_STEP 時填寫：要刪除的步驟 step_id
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`，在 mutation 處理區段加入：

```python
elif _step_mutation.mutation_type == StepMutationType.DELETE_STEP and _step_mutation.delete_step_id:
    target_id = _step_mutation.delete_step_id
    target_idx = next(
        (i for i, t in enumerate(playbook.tasks) if t.step_id == target_id), None
    )
    if target_idx is not None and target_idx > step_idx:
        del playbook.tasks[target_idx]
        logger.info("Gap-012-C: DELETE_STEP 刪除步驟 %s（原 idx=%d）", target_id, target_idx)
        step_log.append(f"[DELETED] {target_id}（Minimax 判定為冗餘）")
    else:
        logger.warning("Gap-012-C: 刪除目標 %s 不存在或不在當前步驟之後，忽略", target_id)
```

---

### Gap-012-D：演化後自動重載與重執行閉環

**這是 Level 5 最關鍵的升級**：讓 `PlaybookEvolver` 演化後，系統自動重載並執行演化版 Playbook，而非退出等待人工介入。

#### 設計方案：PlaybookResult 新增 `evolved_playbook_path` 欄位

**修改檔案**：`autoclaude/execution/playbook_runner.py`

```python
@dataclass
class PlaybookResult:
    # 現有欄位...
    evolved_playbook_path: Optional[str] = None  # 若有演化版，指向新 YAML 路徑
```

**修改 `_run_steps()` 的 ESCALATION 處理**：

```python
# 現有：
return PlaybookResult(False, ..., f"[{task.step_id}] {report.reasoning}", ...)

# 修改為：
if _evolved_path:
    return PlaybookResult(
        False, len(step_log), total,
        f"[{task.step_id}] ESCALATION → 已演化至 {_evolved_path}",
        workflow, step_log,
        evolved_playbook_path=_evolved_path,  # ← 新增
    )
return PlaybookResult(False, ..., "ESCALATION（無演化方案）", ...)
```

**修改 `run()` 外層迴圈**：

```python
def run(self, playbook_path: str, fresh: bool = False) -> PlaybookResult:
    _current_path = playbook_path
    _evolution_count = 0
    _max_evolutions = 3  # 防止演化無限迴圈

    while True:
        playbook = self._load_playbook(_current_path)
        # ... 現有流程 ...

        result = self._run_steps(...)

        # 新增：自動重載演化版 Playbook
        if (
            result.evolved_playbook_path
            and _evolution_count < _max_evolutions
        ):
            _evolution_count += 1
            logger.info(
                "=== Gap-012-D | Level 5 自動重載演化版 Playbook #%d: %s ===",
                _evolution_count, result.evolved_playbook_path,
            )
            self._notify(
                f"AutoClaude — 自動重載演化版 Playbook（第 {_evolution_count} 次）",
                f"演化版: {result.evolved_playbook_path}",
            )
            _current_path = result.evolved_playbook_path
            fresh = True  # 演化版從頭執行
            continue

        # ... 現有的 token halt / 正常結束邏輯 ...
```

**同時修改 `apply_evolution()`**：將 in-memory 的動態注入步驟也納入演化版：

```python
def apply_evolution(self, playbook: Playbook, ...) -> str:
    # 使用 playbook.tasks（已含 INJECT_AFTER 的 in-memory 步驟），而非重建
    tasks = list(playbook.tasks)  # 現有實作，已正確取 in-memory 版本
    # ... 以下不變
```

注意：目前 `apply_evolution()` 的 `tasks = list(playbook.tasks)` 已是正確的——取的是傳入的 `playbook` 物件的 tasks，而這個物件在 `_run_steps()` 中已被 INJECT_AFTER 修改過。**B-4 斷層實際上是誤判，不存在。**

---

### Gap-012-E：`global_goal` 納入 Compact Memory Anchor

**目標**：確保 Claude Code 在 `/compact` 後仍記得系統總目標。

**修改 `_send_compact()` 函數簽名**（`playbook_runner.py:1174`）：

```python
def _send_compact(
    self,
    is_first: bool,
    failure_summary: str = "",
    task: Optional[PlaybookTask] = None,
    attempt: int = 0,
    global_goal: Optional[str] = None,  # ← 新增 Gap-012-E
) -> bool:
```

**修改 MEMORY ANCHOR 建構**：

```python
anchor = (
    "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
    f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
    f"[ATTEMPT] {attempt + 1}\n"
)
if task.expected_output_regex:
    anchor += f"[SUCCESS_CONDITION] output must match: {task.expected_output_regex}\n"
if failure_summary:
    last_err = failure_summary.split("\n")[-1][:120]
    anchor += f"[LAST_FAILURE] {last_err}\n"
# ← 新增 Gap-012-E
if global_goal:
    anchor += f"[GLOBAL_GOAL] {global_goal[:300]}\n"
anchor += "=== END ANCHOR ===\n"
```

**修改所有 `_send_compact()` 呼叫點**（共 3 處），傳入 `global_goal=playbook.global_goal`。

---

### Gap-012-F：Minimax 的 INJECT_BEFORE 觸發門檻調整

目前 `allow_mutation` 門檻（`playbook_runner.py:612-616`）：

```python
allow_mutation = (
    attempt >= 2 and
    report.trend in ("stuck", "oscillating", "cycling")
)
```

對於「前提條件缺失」類型的錯誤（`error_class == IMPORT` 或 `error_class == ENVIRONMENT`），**第一次失敗就能確定前提缺失**，不應等到 attempt >= 2。

**修改觸發條件**：

```python
# Gap-012-F：前提條件錯誤（IMPORT/ENVIRONMENT）第一次就允許 INJECT_BEFORE
_is_prerequisite_error = error_cls in (ErrorClass.IMPORT, ErrorClass.ENVIRONMENT)
allow_mutation = (
    _is_prerequisite_error and attempt >= 1  # 前提錯誤：1 次就觸發
) or (
    attempt >= 2 and report.trend in ("stuck", "oscillating", "cycling")
)
```

注意：`INJECT_BEFORE` 在 `allow_mutation=False` 時也應允許，因此可以單獨設計 `allow_inject_before` flag。

---

## 四、迭代行動清單（Action Items）

### P0：必須實作（阻斷 Level 5 自治性）

| 編號 | 修改檔案 | 函數/位置 | 行動描述 |
|------|---------|---------|---------|
| **Gap-012-A** | `autoclaude/models/step_mutation.py` | `StepMutationType` | 新增 `INJECT_BEFORE`, `DELETE_STEP`, `GOTO_STEP` 枚舉值 |
| **Gap-012-A** | `autoclaude/execution/playbook_runner.py` | `_run_steps()` L644-668 | 實作 `INJECT_BEFORE` mutation 處理（插入 + break + continue） |
| **Gap-012-D** | `autoclaude/execution/playbook_runner.py` | `run()` L154-204 | 演化後自動重載閉環（`evolved_playbook_path` + while loop） |
| **Gap-012-D** | `autoclaude/execution/playbook_runner.py` | `PlaybookResult` dataclass | 新增 `evolved_playbook_path: Optional[str] = None` |
| **Gap-012-D** | `autoclaude/execution/playbook_runner.py` | `_run_steps()` ESCALATION 段 | 回傳含 `evolved_playbook_path` 的 `PlaybookResult` 而非直接 return False |

### P1：應該實作（補強 Goal Drift 防護）

| 編號 | 修改檔案 | 函數/位置 | 行動描述 |
|------|---------|---------|---------|
| **Gap-012-E** | `autoclaude/execution/playbook_runner.py` | `_send_compact()` | 函數簽名加入 `global_goal` 參數，MEMORY ANCHOR 含 `[GLOBAL_GOAL]` |
| **Gap-012-E** | `autoclaude/execution/playbook_runner.py` | 3 個 `_send_compact()` 呼叫點 | 傳入 `global_goal=playbook.global_goal` |
| **Gap-012-F** | `autoclaude/execution/playbook_runner.py` | `_run_steps()` L612-616 | 前提條件錯誤（IMPORT/ENVIRONMENT）第 1 次就允許 `INJECT_BEFORE` |
| **Gap-012-F** | `autoclaude/decision/prompt_builder.py` | `_MUTATION_SCHEMA_SECTION` | 加入 `INJECT_BEFORE` 的 JSON Schema 說明 |

### P2：擴充圖靈完備性

| 編號 | 修改檔案 | 函數/位置 | 行動描述 |
|------|---------|---------|---------|
| **Gap-012-B** | `autoclaude/models/step_mutation.py` | `StepMutation` model | 新增 `goto_step_id: Optional[str]` |
| **Gap-012-B** | `autoclaude/execution/playbook_runner.py` | `_run_steps()` | 實作 `GOTO_STEP` 處理（`_goto_counter` + 安全跳轉） |
| **Gap-012-C** | `autoclaude/execution/playbook_runner.py` | `_run_steps()` | 實作 `DELETE_STEP` 處理（只允許刪除 step_idx 之後的步驟） |

### 測試要求

| 測試檔案 | 新增測試案例 | 覆蓋的 Gap |
|---------|------------|-----------|
| `tests/test_gap012.py` | 新建（參考 `test_gap009.py` 結構） | 全部 Gap-012 |
| `tests/test_playbook_runner.py` | 補充 INJECT_BEFORE + 演化自動重載場景 | Gap-012-A, 012-D |
| `tests/test_decision.py` | 補充 INJECT_BEFORE Minimax 提議解析 | Gap-012-A |

---

## 五、演進後的完整 Level 5 執行流程

```
user: global_goal = "建立完整 FastAPI 登入模組"
      T01: 寫 Auth, T02: 寫 DB

system:
  EXECUTE T01
    attempt=0 → FAIL (ModuleNotFoundError: fastapi)
    error_class = IMPORT
    allow_inject_before = True（IMPORT 第 1 次就觸發）
    
    CORRECTION → Minimax（帶 global_goal）
      → 提議 INJECT_BEFORE: T00_INIT_ENV
      → "建立 requirements.txt 並安裝 FastAPI"
    
    INJECT_BEFORE: 插入 T00_INIT_ENV 於 T01 前
    playbook.tasks = [T00_INIT_ENV, T01, T02]
    break from attempt loop → step_idx 仍指向 T00_INIT_ENV（idx=0）
  
  EXECUTE T00_INIT_ENV（立即執行！）
    attempt=0 → 建立 requirements.txt + pip install → SUCCESS
  
  EXECUTE T01（step_idx=1）
    attempt=0 → Claude Code 現在有 FastAPI 了 → 繼續開發
    attempt=0 → SUCCESS（希望如此）
  
  EXECUTE T02（step_idx=2）
    → SUCCESS
  
  DONE → global_goal 達成！
  
  ← 整個過程全自動，無需人工介入 ←
```

---

## 六、風險評估

| 風險 | 描述 | 緩解方案 |
|------|------|---------|
| INJECT_BEFORE 無限遞迴 | A 插入 B，B 又插入 A | 每個步驟的 INJECT_BEFORE 次數上限（3 次） |
| GOTO_STEP 無限迴圈 | A → goto B → B → goto A | `_goto_counter` 每步驟上限 3 次 |
| 演化重載深度過大 | 演化版 → 失敗 → 再演化 | `_max_evolutions = 3` |
| 刪錯步驟 | DELETE_STEP 刪了關鍵步驟 | 只允許刪除 `step_idx > current_step_idx` 的步驟 |
| global_goal 過長撐爆 compact | 100K token goal | compact anchor 只取前 300 字 |

---

**文件狀態**: Active — 待實作  
**關聯 Gap**: Gap-012-A, B, C, D, E, F  
**預計影響範圍**: `autoclaude/models/`, `autoclaude/execution/`, `autoclaude/decision/`, `tests/`
