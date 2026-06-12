# AutoClaude Level 5 動態閉環升級藍圖 — Evo-002

**文件版本**: v1.0  
**建立日期**: 2026-05-04  
**作者**: 首席 AI 自動化架構師分析（Chief AI Automation Architect Review）  
**前置分析對象**: Gap-012-A ~ Gap-012-F 完成後的現有系統（374 tests passing）  
**下一步**: 實作 Gap-013-A ~ Gap-013-H

---

## 一、深度思考：三大核心議題 + 極端推演的殘存漏洞

### 1.1 動態突變的圖靈完備性——Gap-012 之後的殘存缺口

Gap-012 成功賦予系統真正的圖靈完備性（INJECT_BEFORE / GOTO_STEP / DELETE_STEP），但實作細節中存在三個**隱性語意漏洞**：

#### 漏洞 A：FailureTracker 在 GOTO 後重置導致策略「失憶」

```python
# playbook_runner.py:302 — 每個步驟開頭
tracker = FailureTracker(task.step_id)   # ← 每次都是全新的 tracker
```

當 `GOTO_STEP` 跳回 T01（idx=0），`while step_idx < len(...)` 的下一次迭代對 T01 建立了全新的 `FailureTracker`。這意味著：

- `tracker._tried_strategies`（已嘗試策略集合）被清空
- `ConvergenceMonitor` 面對空的 `history`，回傳 `"unknown"` → `"continue"`
- T01 可能會重新嘗試上次已知失敗的策略（除非 `FailureKnowledgeBase` 正好有記錄）

**後果**：GOTO_STEP 的本意是「用更好的環境重新執行」，但策略失憶讓 Minimax 可能走回相同的死路，浪費 2-3 次重試後才發現。

#### 漏洞 B：`_inject_before_counter` 跨訪次數累積不分訪次

`_inject_before_counter` 初始化在 `_run_steps()` 頂部，整個 run 生命週期共享：

```python
_inject_before_counter: dict[str, int] = {}  # Gap-012-A
```

情境：T02 在第一次訪問時 `_inject_before_counter["T02"] = 2`，之後 GOTO_STEP 跳回 T01，T01 修好後再進入 T02。此時 T02 是全新的嘗試，但計數器仍殘留 `= 2`，代表 T02 只剩最後一次 INJECT_BEFORE 機會（計數達 3 即封鎖）。

設計意圖（防遞迴）與語意正確（允許合理重試）之間存在張力。

#### 漏洞 C：GOTO 無限迴圈防護觸發時直接返回，跳過 PlaybookEvolver

```python
# playbook_runner.py:762-766
if _gc > 3:
    return PlaybookResult(
        False, ...,
        f"[{task.step_id}] GOTO 無限迴圈防護觸發",
        ...
    )  # ← 直接返回，evolved_playbook_path=None
```

此路徑完全繞過了 `PlaybookEvolver` 的諮詢。當系統偵測到 GOTO 迴圈（系統陷入某個「T01→T02→GOTO T01」的循環），正是最需要結構演化（如 SPLIT_STEP 或 INJECT_STEP）的時機，但系統卻選擇直接放棄。

---

### 1.2 目標漂移防護——Gap-012-E 的三個盲點

Gap-012-E 在 `_send_compact()` 的 MEMORY ANCHOR 中注入 `[GLOBAL_GOAL]`，確保 `/compact` 後 Claude Code 仍知道總目標。但有三個盲點：

#### 盲點 1：`global_goal` 對 Claude Code 執行層完全不可見

```
Minimax（修正大腦）← global_goal 注入 ✅（build_correction_message 頂端）
/compact ANCHOR    ← global_goal 注入 ✅（Gap-012-E，防漂移）
Claude Code（執行層）← global_goal 從未出現在任何 task.prompt 或首次 prompt ❌
```

Claude Code 只收到 `task.prompt`（步驟級指令）。它不知道整個 Playbook 的 `global_goal`，無法在任務遇到模糊情境時自主對齊總目標。

例如：`global_goal = "建立 FastAPI 登入模組"`，T01 prompt = "建立 user.py"。當 Claude Code 發現模型設計有分歧時，它沒有「總目標」作為決策依據，只能按步驟字面指令行事。

#### 盲點 2：MEMORY ANCHOR 截斷固定 300 字元，無彈性

```python
# _send_compact():1337
anchor += f"[GLOBAL_GOAL] {global_goal[:300]}\n"
```

300 字元對複雜的 `global_goal` 可能嚴重截斷語意。此值寫死在程式碼中，無法透過 `AppConfig` 調整。

#### 盲點 3：跨演化版本的目標對齊缺乏驗證機制

`PlaybookEvolver.apply_evolution()` 確實保留了 `global_goal`：

```python
evolved_playbook = Playbook(..., global_goal=playbook.global_goal, ...)
```

但沒有任何機制驗證演化後的步驟設計是否仍對齊 `global_goal`。演化本身（SPLIT_STEP 或 INJECT_STEP）是純機械式操作，可能在拆分步驟時切割掉關鍵語意，形成演化後的步驟與總目標漸行漸遠的「演化漂移」。

---

### 1.3 錯誤收斂與演化衝突——閉環中的三條斷層線

從「失敗 → 凍結 → 演化出新 YAML → 重新載入」的完整閉環中，存在三條已知的斷層線：

#### 斷層線 1：`REVISE_EVALUATOR` 演化類型已聲明但未實作

```python
# playbook_evolver.py — propose_evolution()
# evolution_type 可以是 "REVISE_EVALUATOR"，但...

# apply_evolution()
if proposal.evolution_type == "INJECT_STEP" and proposal.new_step:
    ...
elif proposal.evolution_type == "SPLIT_STEP" and proposal.split_steps:
    ...
else:
    logger.warning("PlaybookEvolver: 未知演化類型 %s，略過", proposal.evolution_type)
    return playbook_path  # ← REVISE_EVALUATOR 落入此分支，靜默失敗
```

`REVISE_EVALUATOR` 在程式碼注釋中聲明為支援的演化類型，但 `apply_evolution()` 沒有對應的處理分支。任何觸發 `REVISE_EVALUATOR` 的演化提議都會靜默失敗（回傳原始路徑而非演化路徑），且 `evolved_playbook_path` 為 None，導致 `run()` 判定無演化、直接結束。

#### 斷層線 2：動態突變（in-memory）未持久化——Token HALT 重啟後突變消失

情境：
1. T01 成功後，Minimax 對 T02 提議 `INJECT_AFTER T02_PLUS`
2. `playbook.tasks` 現在是 `[T01, T02, T02_PLUS, T03]`（in-memory 修改）
3. 執行 T02_PLUS 時 context 達 halt 門檻 → TOKEN_HALT → checkpoint 儲存（記錄 `step_id="T02_PLUS"`）
4. 系統重啟，從 checkpoint 恢復：`_current_path = original_playbook.yaml`
5. 重新載入原始 YAML → `playbook.tasks = [T01, T02, T03]`
6. checkpoint 記錄 `step_id="T02_PLUS"`，但 tasks 中找不到 `T02_PLUS` → 系統從 T03 開始？或崩潰？

```python
# _resolve_start()
next((i for i, t in enumerate(playbook.tasks) if t.step_id == cp.step_id), 0)
```

若 `cp.step_id = "T02_PLUS"` 但 playbook 只有原始步驟，`next()` 回傳預設值 `0` → 系統從頭開始，重複執行已完成的 T01！這是一個**靜默資料損壞**的嚴重 Bug。

#### 斷層線 3：Minimax 對前次突變決策的失憶

Minimax 的修正訊息（`build_correction_message()`）包含：失敗步驟、原始 prompt、失敗原因、歷史摘要。但**不包含已執行的突變歷史**。

情境：
1. T02 失敗（attempt 1） → Minimax 建議 `INJECT_BEFORE T00_PRE`
2. T00_PRE 執行後 T02 再次失敗（attempt 2）
3. Minimax 再次被諮詢，**但它不知道自己已建議過 INJECT_BEFORE**
4. Minimax 可能再次建議 `INJECT_BEFORE T00_PRE_2`，創建套娃式前置步驟鏈

`_inject_before_counter` 雖然在第 4 次時封鎖，但 Minimax 根本不知道是計數器封鎖了它，無法做出不同的決策。它只知道「同樣的錯誤還在」，而不知道「INJECT_BEFORE 已被嘗試 3 次」。

---

## 二、自我驗證協定——T00_INIT_ENV 情境完整推演

**情境回顧**：`global_goal = "建立完整的 FastAPI 登入與資料庫連線模組"`。初始步驟：T01（Auth）、T02（DB）。T01 執行時 Minimax 發現連 `requirements.txt` 和基礎 config 都沒有。

### 推演過程

```
1. step_idx=0, task=T01（Auth）
2. attempt=0: Claude Code 嘗試創建 auth.py，但 import fastapi 失敗
   → eval_output: "ModuleNotFoundError: No module named 'fastapi'"
   → error_cls = ErrorClass.IMPORT
   → _is_prerequisite_error = True
   → allow_mutation = (True and attempt >= 1) = False  ← 必須等到 attempt 1 才能突變

3. attempt=1: 再次失敗（仍然缺少 fastapi）
   → allow_mutation = (True and 1 >= 1) = True
   → Minimax 諮詢：發現 IMPORT 錯誤 + 缺少環境設定
   → 建議 INJECT_BEFORE: new_step_id="T00_INIT_ENV", prompt="創建 requirements.txt 和 config.py"
   
4. _inject_before_counter["T01"] = 1
   playbook.tasks.insert(0, T00_INIT_ENV)
   → tasks = [T00_INIT_ENV, T01, T02]
   _inject_before_pending = True
   break（跳出 attempt loop）

5. 步驟推進：if _inject_before_pending: continue（step_idx 維持 0）
   → 下次 while loop 的 task = playbook.tasks[0] = T00_INIT_ENV ✅

6. T00_INIT_ENV 執行並成功（Claude Code 創建 requirements.txt, config.py）
   step_idx += 1 → step_idx=1 → task=T01

7. T01（Auth）重新執行，此時環境已就緒
   → 通過 ✅
   step_idx=2 → T02 → 通過 ✅
   → DONE
```

**結論：Gap-012-A 的邏輯正確，T00_INIT_ENV 情境可以正常運行。**

### 情境中的潛在斷層點

但若 T00_INIT_ENV 本身失敗（Claude Code 創建了錯誤的 requirements.txt），情況如下：

```
T00_INIT_ENV attempt 0: 失敗（錯誤的套件版本）
T00_INIT_ENV attempt 1: Minimax 建議再次 INJECT_BEFORE（因為仍是 IMPORT error）
→ _inject_before_counter["T00_INIT_ENV"] = 1
→ 插入 T00_INIT_ENV_PRE（requirements.txt 修正版）
→ tasks = [T00_INIT_ENV_PRE, T00_INIT_ENV, T01, T02]

T00_INIT_ENV_PRE attempt 0: 成功
T00_INIT_ENV attempt 0: 成功（重新嘗試）
T01 attempt 0: 失敗（仍有問題）
→ Minimax 再次建議 INJECT_BEFORE for T01
→ _inject_before_counter["T01"] 此時仍為 1（之前那次）
→ 插入 T01_PRE（第 2 次，計數器 = 2）
→ ... 持續到 _inject_before_counter["T01"] > 3 被封鎖

此時 Minimax 被告知「計數器封鎖」，但 Minimax 根本不知道計數器的存在
→ 間接導致 Minimax 走到 GOTO_STEP 嘗試（它還能做什麼？）
```

這個場景暴露了 **斷層線 3（Minimax 對突變歷史失憶）** 的具體後果。

---

## 三、Level 5 動態閉環升級藍圖 — Gap-013 系列

### Gap-013-A（P0）：FailureTracker 熱啟動（GOTO 策略繼承）

**問題**：GOTO_STEP 後對同一步驟建立全新 FailureTracker，已嘗試策略集合被清空。  
**影響**：步驟重訪後 Minimax 可能走回已知死路，浪費 2-3 次重試預算。

**修改方案**：

在 `_run_steps()` 頂部維護 `_step_trackers: dict[str, FailureTracker]`，對重訪步驟執行「策略繼承式熱啟動」：

```python
# 新增於 _run_steps() 開頭（while loop 之前）
_step_trackers: dict[str, FailureTracker] = {}

# 在 while loop 內、建立 tracker 之前
if task.step_id in _step_trackers:
    # 熱啟動：繼承已嘗試策略集合，但清空失敗記錄（讓收斂評估重新計算）
    prev_tracker = _step_trackers[task.step_id]
    tracker = FailureTracker(task.step_id)
    tracker._tried_strategies = prev_tracker._tried_strategies.copy()
    logger.info(
        "=== Gap-013-A | [%s] GOTO 重訪熱啟動，繼承 %d 個已嘗試策略 ===",
        task.step_id, len(tracker._tried_strategies)
    )
else:
    tracker = FailureTracker(task.step_id)
_step_trackers[task.step_id] = tracker
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`（`_run_steps()` 方法）

---

### Gap-013-B（P0）：PlaybookEvolver 補全 REVISE_EVALUATOR 處理分支

**問題**：`apply_evolution()` 無 `REVISE_EVALUATOR` 的實作分支，靜默落入 `else → warning → return playbook_path`（回傳原始路徑）。  
**影響**：任何需要修改 `evaluator_command` 的演化提議都會靜默失效；`evolved_playbook_path=None`，`run()` 認為無演化發生，直接結束。

**修改方案**：

```python
# playbook_evolver.py apply_evolution()
elif proposal.evolution_type == "REVISE_EVALUATOR" and proposal.revised_evaluator:
    idx = proposal.inject_before_idx   # 重用此欄位表示「目標步驟索引」
    if 0 <= idx < len(tasks):
        tasks[idx].evaluator_command = proposal.revised_evaluator
        logger.info(
            "PlaybookEvolver: REVISE_EVALUATOR 步驟 %d evaluator 更新為: %s",
            idx, proposal.revised_evaluator[:80],
        )
    else:
        logger.warning("PlaybookEvolver: REVISE_EVALUATOR idx=%d 超出範圍，略過", idx)
        return playbook_path
```

同時補上 `PlaybookEvolutionProposal` 的欄位文件（`inject_before_idx` 對 REVISE_EVALUATOR 表示目標步驟索引）。

**修改檔案**：`autoclaude/evolution/playbook_evolver.py`（`apply_evolution()` 方法）

---

### Gap-013-C（P0）：動態突變狀態持久化（防止 Token HALT 重啟後突變消失）

**問題**：`playbook.tasks` 的 in-memory 動態突變（INJECT_AFTER/INJECT_BEFORE/DELETE_STEP/REVISE_CURRENT）在 Token HALT 後重啟時消失，導致系統從原始 YAML 重載，`checkpoint.step_id` 找不到對應步驟 → 靜默從頭開始。  
**影響**：已完成步驟被重複執行；插入的前置步驟（如 T00_INIT_ENV）在重啟後消失。

**修改方案**：

在 `_run_steps()` 內，每次執行任何 `StepMutation` 後，立即將當前 `playbook.tasks` 序列化至 `{checkpoint_dir}/{playbook_stem}.mutated.yaml`：

```python
# 新增輔助方法 _persist_mutated_playbook()
def _persist_mutated_playbook(self, playbook: Playbook, playbook_path: str) -> None:
    """每次突變後將當前 task 列表寫入 .mutated.yaml，防止重啟後突變消失。"""
    stem = Path(playbook_path).stem
    mutated_path = Path(self._cfg.checkpoint_dir) / f"{stem}.mutated.yaml"
    try:
        with mutated_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                playbook.model_dump(exclude_none=True),
                f, allow_unicode=True, default_flow_style=False,
            )
        logger.debug("Gap-013-C | 突變後持久化: %s", mutated_path)
    except Exception as exc:
        logger.warning("Gap-013-C | 突變持久化失敗: %s", exc)
```

在 `_resolve_start()` 中，優先載入 `.mutated.yaml`（若存在且 checkpoint 匹配）：

```python
# _resolve_start() 修改
mutated_path = Path(self._cfg.checkpoint_dir) / f"{Path(playbook_path).stem}.mutated.yaml"
if mutated_path.exists() and checkpoint_exists:
    logger.info("Gap-013-C | 偵測到 .mutated.yaml，恢復突變狀態")
    return self._load_playbook(str(mutated_path)), start_idx, ...
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`（新增 `_persist_mutated_playbook()`，修改 `_resolve_start()`）

---

### Gap-013-D（P1）：突變歷史注入 Minimax 修正訊息

**問題**：Minimax 在每次修正決策時看不到「本步驟已被突變過幾次、突變類型為何」，導致它在不知情的狀況下再次提議相同類型的突變。  
**影響**：INJECT_BEFORE 建議可能被反覆提出，直到計數器封鎖（但 Minimax 不知為何失效）。

**修改方案**：

在 `_run_steps()` 內維護 `_mutation_log: list[str]`（每次突變後 append 一條記錄），並將其傳入 `_get_correction()`，最終注入 `build_correction_message()`：

```python
# 在 while loop 頂部初始化
_mutation_log: list[str] = []  # 本次 run 的突變紀錄

# 每次突變後追加
_mutation_log.append(
    f"attempt {attempt}: {_step_mutation.mutation_type} "
    f"→ {_step_mutation.new_step_id or _step_mutation.goto_step_id or _step_mutation.delete_step_id}"
)
```

在 `prompt_builder.build_correction_message()` 加入 `mutation_history: list[str] = []` 參數，注入新的區段：

```python
mutation_section = (
    "## 本步驟已執行的突變紀錄\n"
    + "\n".join(f"- {m}" for m in mutation_history) + "\n\n"
) if mutation_history else ""
```

**修改檔案**：  
- `autoclaude/decision/prompt_builder.py`（`build_correction_message()` 加入 `mutation_history` 參數與對應區段）  
- `autoclaude/execution/playbook_runner.py`（維護 `_mutation_log` 並傳入修正訊息）

---

### Gap-013-E（P1）：GOTO 無限迴圈防護觸發後諮詢 PlaybookEvolver

**問題**：GOTO > 3 次的防護直接 `return PlaybookResult(False, ...)` 且 `evolved_playbook_path=None`，完全跳過 PlaybookEvolver。  
**影響**：GOTO 迴圈本質上是「系統反覆在兩個步驟間彈跳」的卡死模式，正是最需要 SPLIT_STEP 或 INJECT_STEP 演化的時機。

**修改方案**：

```python
# playbook_runner.py，GOTO 無限迴圈防護分支修改
if _gc > 3:
    logger.error("=== Gap-012-B / Gap-013-E | GOTO %s 已 %d 次，嘗試演化 ===", _target_id, _gc)
    # 合成一個 ESCALATION dump 給 evolver 分析
    _goto_dump = self._save_escalation_dump(
        tracker, task, playbook_path, eval_output,
        human_hint=f"GOTO 無限迴圈防護觸發（目標={_target_id}，執行 {_gc} 次）",
    )
    self._escalation_history.append(_goto_dump)
    _proposal_goto = self._evolver.propose_evolution(
        playbook, step_idx, _goto_dump, self._escalation_history
    )
    _evolved_goto_path: Optional[str] = None
    if _proposal_goto:
        _evolved_goto_path = self._evolver.apply_evolution(
            playbook, _proposal_goto, playbook_path
        )
    return PlaybookResult(
        False, len(step_log), total,
        f"[{task.step_id}] GOTO 無限迴圈防護觸發（目標={_target_id}）",
        workflow, step_log,
        evolved_playbook_path=_evolved_goto_path,  # Gap-013-E
    )
```

**修改檔案**：`autoclaude/execution/playbook_runner.py`（GOTO > 3 分支）

---

### Gap-013-F（P1）：global_goal 注入 Claude Code 執行層（首次 Prompt 前置區塊）

**問題**：`global_goal` 僅存在於 Minimax 決策訊息和 `/compact` MEMORY ANCHOR。Claude Code 執行層對系統總目標完全無感知。  
**影響**：Claude Code 在模糊決策點無法自主對齊總目標，可能在細節步驟中做出偏離整體架構的選擇。

**修改方案**：

若 `playbook.global_goal` 存在，在發送給 Claude Code 的**第一個 prompt**（context_negotiation 或 task[0]）前置一個摘要區塊：

```python
# _run_steps()，context_negotiation 或 is_first_prompt 的處理位置

def _prepend_global_goal(self, prompt: str, global_goal: Optional[str]) -> str:
    """若有 global_goal，在 prompt 前置目標摘要，讓執行層有方向感。"""
    if not global_goal:
        return prompt
    goal_header = (
        "=== 本次自動化任務的總目標 ===\n"
        f"{global_goal[:500]}\n"
        "以上為整體目標供你參考，請確保每個步驟的實作決策與此目標方向一致。\n"
        "===========================\n\n"
    )
    return goal_header + prompt
```

此方法僅在 `is_first_prompt=True` 時呼叫一次（避免每步驟重複）。

**修改檔案**：`autoclaude/execution/playbook_runner.py`（新增 `_prepend_global_goal()`，在首次 prompt 套用）

---

### Gap-013-G（P2）：PlaybookEvolver 注入步驟繼承 global_invariants.max_retries_per_step

**問題**：`PlaybookEvolver.propose_evolution()` 的 Case 1（suspect_test_file）和 Case 2（assert_fix）對注入的 `PlaybookTask` 硬編碼 `max_retries=2`，可能與全域設定不符。  
**影響**：若使用者設定 `max_retries_per_step=5`，注入的前置步驟只有 2 次重試機會，過早 ESCALATION。

**修改方案**：

```python
# playbook_evolver.py，propose_evolution() 簽名修改
def propose_evolution(
    self,
    playbook: Playbook,
    failed_step_idx: int,
    escalation_dump: EscalationDump,
    escalation_history: Optional[list[EscalationDump]] = None,
) -> Optional[PlaybookEvolutionProposal]:
    global_max_retries = playbook.global_invariants.max_retries_per_step
    inject_max_retries = max(2, min(global_max_retries, 3))  # 注入步驟：2~3 次（不超過全域）
    
    # Case 1/2 中使用 inject_max_retries 替換 max_retries=2
    new_step = PlaybookTask(
        ...,
        max_retries=inject_max_retries,  # 從 global_invariants 推算
    )
```

**修改檔案**：`autoclaude/evolution/playbook_evolver.py`（`propose_evolution()` 讀取 `playbook.global_invariants`）

---

### Gap-013-H（P2）：global_goal MEMORY ANCHOR 截斷長度可配置

**問題**：`_send_compact()` 硬編碼 `global_goal[:300]`，複雜目標可能語意截斷。  
**影響**：目標被截斷後，`/compact` 後 Claude Code 可能看到一個不完整的總目標描述。

**修改方案**：

在 `AppConfig.token_guard` 或 `playbook` 配置群組新增欄位：

```python
# utils/config.py
class PlaybookConfig(BaseSettings):
    ...
    global_goal_anchor_chars: int = Field(default=400, ge=100, le=1000)
    # compact 時 [GLOBAL_GOAL] 最大字元數（100~1000）
```

在 `_send_compact()` 使用：

```python
max_chars = self._cfg.playbook.global_goal_anchor_chars
anchor += f"[GLOBAL_GOAL] {global_goal[:max_chars]}\n"
```

**修改檔案**：  
- `autoclaude/utils/config.py`（`PlaybookConfig` 新增 `global_goal_anchor_chars`）  
- `autoclaude/execution/playbook_runner.py`（`_send_compact()` 使用設定值）

---

## 四、迭代行動清單（Action Items）

### P0 — 必須先完成（系統正確性）

| Gap | 檔案 | 修改重點 | 測試覆蓋 |
|-----|------|---------|---------|
| 013-A | `playbook_runner.py` | `_run_steps()` 加 `_step_trackers`，GOTO 後熱啟動 tracker | `test_gap013.py::TestGotoTrackerWarmStart` |
| 013-B | `playbook_evolver.py` | `apply_evolution()` 補 `REVISE_EVALUATOR` 分支 | `test_gap013.py::TestReviseEvaluator` |
| 013-C | `playbook_runner.py` | `_persist_mutated_playbook()` + `_resolve_start()` 讀取 `.mutated.yaml` | `test_gap013.py::TestMutationPersistence` |

### P1 — 第二優先（語意完整性）

| Gap | 檔案 | 修改重點 | 測試覆蓋 |
|-----|------|---------|---------|
| 013-D | `prompt_builder.py` + `playbook_runner.py` | `mutation_history` 參數注入修正訊息 | `test_gap013.py::TestMutationHistoryInPrompt` |
| 013-E | `playbook_runner.py` | GOTO > 3 分支諮詢 `PlaybookEvolver` | `test_gap013.py::TestGotoLoopEvolution` |
| 013-F | `playbook_runner.py` | `_prepend_global_goal()` 注入首次 prompt | `test_gap013.py::TestGlobalGoalInClaudeContext` |

### P2 — 品質改善（可與 P1 同步進行）

| Gap | 檔案 | 修改重點 | 測試覆蓋 |
|-----|------|---------|---------|
| 013-G | `playbook_evolver.py` | 注入步驟 max_retries 從 `global_invariants` 推算 | `test_gap013.py::TestEvolverMaxRetries` |
| 013-H | `config.py` + `playbook_runner.py` | `global_goal_anchor_chars` 可配置 | `test_gap013.py::TestGoalAnchorSize` |

---

## 五、測試要求

新增 `tests/test_gap013.py`，共預計 **32+ 測試案例**：

### TestGotoTrackerWarmStart（Gap-013-A）
- `test_warm_start_inherits_tried_strategies`：GOTO 後的 tracker 繼承 `_tried_strategies`
- `test_warm_start_clears_failure_history`：熱啟動後 `tracker.history` 為空
- `test_warm_start_does_not_inherit_attempt_offset`：`attempt_offset` 從 0 開始
- `test_first_visit_creates_fresh_tracker`：首次訪問不觸發熱啟動

### TestReviseEvaluator（Gap-013-B）
- `test_revise_evaluator_applies_to_task`：正確更新 `evaluator_command`
- `test_revise_evaluator_invalid_idx_returns_original`：idx 超出範圍靜默回傳原路徑
- `test_revise_evaluator_writes_evolved_yaml`：確認 `evolved_*.yaml` 被寫入

### TestMutationPersistence（Gap-013-C）
- `test_inject_after_persists_mutated_yaml`：INJECT_AFTER 後 `.mutated.yaml` 存在
- `test_inject_before_persists_mutated_yaml`：INJECT_BEFORE 後 `.mutated.yaml` 存在
- `test_resolve_start_loads_mutated_yaml`：restart 時從 `.mutated.yaml` 載入
- `test_missing_step_id_not_restart_from_zero`：mutated step_id 找得到正確索引

### TestMutationHistoryInPrompt（Gap-013-D）
- `test_mutation_history_in_correction_message`：`mutation_history` 出現在 Minimax 訊息中
- `test_empty_mutation_history_no_section`：空歷史不生成區段
- `test_mutation_log_accumulated_across_attempts`：多次突變累積記錄

### TestGotoLoopEvolution（Gap-013-E）
- `test_goto_loop_triggers_evolver`：GOTO > 3 後 `_evolver.propose_evolution()` 被呼叫
- `test_goto_loop_returns_evolved_path`：若有演化提議，`evolved_playbook_path` 不為 None
- `test_goto_loop_no_proposal_returns_false`：無演化提議時正常返回失敗

### TestGlobalGoalInClaudeContext（Gap-013-F）
- `test_global_goal_prepended_to_first_prompt`：首次 prompt 包含 `=== 本次自動化任務的總目標 ===`
- `test_global_goal_not_repeated_in_second_prompt`：第二個步驟 prompt 不重複注入
- `test_no_global_goal_no_header`：無 `global_goal` 時 prompt 無額外區塊

### TestEvolverMaxRetries（Gap-013-G）
- `test_inject_step_uses_global_max_retries`：注入步驟 max_retries 從 global_invariants 計算
- `test_inject_step_caps_at_3`：最大 3 次（不超過）
- `test_inject_step_minimum_2`：最小 2 次

### TestGoalAnchorSize（Gap-013-H）
- `test_compact_uses_configurable_anchor_size`：使用 `global_goal_anchor_chars` 截斷
- `test_compact_default_400_chars`：預設 400 字元
- `test_compact_config_field_validated`：100-1000 範圍驗證

---

## 六、預期影響

| 改善維度 | Gap-013 前 | Gap-013 後 |
|---------|-----------|-----------|
| GOTO 後策略重試效率 | 重新從零學習（浪費 2-3 次） | 繼承已嘗試策略，直接使用下一個 |
| REVISE_EVALUATOR 演化 | 靜默失效（bug） | 正確更新 evaluator_command |
| Token HALT 後突變保存 | 消失（靜默資料損壞） | 透過 .mutated.yaml 持久化 |
| Minimax 突變決策品質 | 不知前次突變結果 | 明確看到突變歷史，避免重複提議 |
| GOTO 迴圈卡死處理 | 直接放棄（無演化） | 諮詢 PlaybookEvolver 嘗試演化 |
| Claude Code 目標對齊 | 只看步驟級 prompt | 首次 prompt 前置 global_goal |
| 注入步驟重試次數 | 固定 2 次 | 從 global_invariants 推算（2~3） |
| global_goal anchor 靈活性 | 硬編碼 300 字元 | AppConfig 可配置 100~1000 字元 |

---

**文件元數據**:
- **文件版本**: v1.0  
- **建立日期**: 2026-05-04  
- **最後更新**: 2026-05-04  
- **適用 AISDLC 版本**: v0.09+  
- **下一個文件**: AutoClaude_L5_Evo_003.md（待 Gap-013 完成後分析）
