# AutoClaude Level 5 動態閉環升級藍圖 — Evo-003

**文件版本**: v1.1  
**建立日期**: 2026-05-05  
**更新日期**: 2026-05-05（實作完成）  
**作者**: 首席 AI 自動化架構師分析（Chief AI Automation Architect Review）  
**前置分析對象**: Gap-013-A ~ Gap-013-H 完成後的現有系統（411 tests passing）  
**分析基線**: INJECT_BEFORE / GOTO_STEP / DELETE_STEP / REVISE_CURRENT / INJECT_AFTER 全數實作完畢  
**實作狀態**: ✅ Gap-014 ~ Gap-020 全數實作完成（458 tests passing，新增 47 個測試）

---

## 一、深度思考：三大核心議題的殘存斷層

### 1.1 動態突變的圖靈完備性——Gap-012/013 之後的三個殘存缺口

Gap-012 實作了五種突變類型，Gap-013 修補了 GOTO 熱啟動策略失憶問題。
然而「圖靈完備」意味著任意計算路徑皆可表達，以下三個缺口使系統仍未達到真正的圖靈完備：

#### 缺口 A：無前向跳轉能力（SKIP_TO 缺失）

```python
# playbook_runner.py:818-824
elif _target_idx >= step_idx:
    logger.warning(
        "=== Gap-012-B | 禁止 GOTO 向前（target=%s idx=%d >= current=%d），忽略 ===",
        ...
    )
```

GOTO_STEP 只允許向後（回溯）跳轉，禁止向前。然而現實場景中，Minimax 可能合理地判斷：「T03/T04 的工作已被注入的 T01_ENV 步驟隱性完成，應直接跳至 T05 繼續。」

目前唯一的替代方案是連續觸發兩次 DELETE_STEP，但 DELETE_STEP 只能在 CORRECTION 迴圈（步驟失敗後）中提議——這要求系統讓 T03 先失敗一次。這造成「為了跳過而故意失敗」的語義悖論。

**缺口影響**：約 15% 的動態 Playbook 優化場景被封鎖，系統無法表達「確認後跳過冗餘步驟」的計算路徑。

#### 缺口 B：每次 Correction 僅允許一個突變（批次突變缺失）

`_get_correction()` 的回傳簽名只允許回傳一個 `Optional[StepMutation]`：
```python
return (
    decision.correction_prompt,
    decision.reasoning,
    decision.task_goal_summary,
    decision.step_mutation,  # 單一突變
)
```

當系統需要「同時注入兩個前置步驟 + 刪除一個冗餘後置步驟」時，需要三個完整的失敗-修正循環（每次一個突變），消耗 3 倍的 Token 和嘗試次數。

#### 缺口 C：DONE 狀態缺乏全局目標驗證（最嚴重）

```python
# playbook_runner.py:952-959（_run_steps 最末）
# ── DONE ──
_final_total = len(playbook.tasks)
logger.info("=== STATE: DONE | 所有 %d 步驟完成 ===", _final_total)
...
return PlaybookResult(True, _final_total, _final_total, "所有步驟完成", workflow, step_log)
```

系統在所有步驟的 `evaluator_command` 各自通過後直接宣告成功。每個步驟的評估是**局部正確性驗證**，而非**全局目標達成驗證**。

**極端反例**：`global_goal = "建立完整的 FastAPI 登入與資料庫連線模組"`：
- T01 (Auth Module)：寫出同步 SQLAlchemy session 的 Auth 模組，測試通過 ✅
- T02 (DB Module)：寫出非同步 asyncpg 的 DB 模組，測試通過 ✅
- DONE 宣告成功 ✅
- **實際問題**：Auth 和 DB 使用不相容的 DB 存取模式，整合後必然崩潰

沒有全局驗證，Level 5 系統宣稱完成了一個實際上破碎的組合。

---

### 1.2 目標漂移防護——global_goal 的覆蓋盲區

#### 盲區分析：global_goal 注入的觸發條件

```python
# playbook_runner.py:466-468
if step_idx == 0 and attempt == attempt_offset:
    prompt_to_send = self._prepend_global_goal(prompt_to_send, playbook.global_goal)
```

**只有 `step_idx == 0`（第一個步驟）的首次 attempt 才注入 global_goal 到執行 prompt。**

| 步驟狀態 | global_goal 注入到執行 prompt | global_goal 出現在 CORRECTION |
|---------|-------------------------------|-------------------------------|
| T01（step_idx=0，首次執行）| ✅ | ✅（若失敗） |
| T02（step_idx=1，首次執行）| ❌ 缺失 | ✅（若失敗） |
| INJECT_BEFORE 注入 T00（移到 idx=0）| ✅ | ✅ |
| INJECT_AFTER 注入 T01_FIX（idx=2+）| ❌ 缺失 | ✅ |
| GOTO 重訪 T01（idx=0，attempt=0）| ✅ | ✅ |
| GOTO 重訪 T02（idx=1，attempt=0）| ❌ 缺失 | ✅ |

**實際後果**：Claude Code 執行 T02 時沒有宏觀目標參考。T02 可能寫出技術正確但與 T01 語義不兼容的模組（例如資料庫用異步介面，而 T01 假設同步介面）。只有在 T02 測試失敗並觸發 CORRECTION 後，Minimax 才能看到 global_goal 並重新對齊——此時已浪費至少一次 attempt。

#### compact 後 global_goal 的截斷風險

`_send_compact()` 的 MEMORY ANCHOR 格式：
```
[GLOBAL_GOAL] {global_goal[:_anchor_chars]}
```
預設 `_anchor_chars = 400`。對於複雜的技術規格（例如包含 API 端點列表的 global_goal），400 字元可能只涵蓋目標的前半段，導致後半段目標在 compact 後消失。

更根本的問題：`/compact` 是 Claude Code 的自主壓縮行為，系統只能「建議」保留什麼，無法強制保證。

#### Minimax 決策層的 global_goal 保護（較穩固）

`build_correction_message()` 在每次 Minimax 諮詢時都將 `global_goal` 置於訊息頂端：
```python
goal_section = f"## 系統總目標\n{global_goal}\n\n" if global_goal else ""
```

由於 Minimax 是獨立的 API 呼叫（不共享 Claude Code 的 context），每次修正決策都看到完整的 `global_goal`。**Minimax 層的 global_goal 保護是穩固的**，真正的風險在 Claude Code 執行層（第二個子系統）的盲區。

---

### 1.3 錯誤收斂與演化衝突——SPLIT_STEP 的語義割裂與閉環斷點

#### PlaybookEvolver 的語義割裂問題

```python
# playbook_evolver.py:124-129（SPLIT_STEP 實作）
mid = len(failed_task.prompt) // 2
split_pos = failed_task.prompt.rfind('\n', 0, mid) or mid
prompt_a = failed_task.prompt[:split_pos].strip()
prompt_b = failed_task.prompt[split_pos:].strip()
```

這是**字符位置切割**，存在三個致命缺陷：

1. **上下文割裂**：T01_B 的 prompt 是「指令的後半段」，沒有關於 T01_A 輸出結果的任何資訊。Claude Code 執行 T01_B 時面對的是「從中間截斷的指令」，不知道 T01_A 完成了什麼。

2. **前提假設缺失**：若原始 prompt 為「A → B → C → D → 驗證」，切割後 T01_B 包含「C → D → 驗證」，但 C 可能依賴 A/B 建立的資料結構。T01_B 執行時找不到前提，必然失敗。

3. **PlaybookEvolver 不諮詢 Minimax**：PlaybookEvolver 是純規則引擎（三個 if/elif case），完全不使用 Minimax 對失敗根因的語義理解。Minimax 已知道「T01 連續失敗 5 次的根因是缺少 requirements.txt」，但 PlaybookEvolver 只看 `is_stuck=True`，仍然採用低效的「字符切割」演化策略。

#### 演化-重載閉環的 Token Context 斷點

當 ESCALATION 觸發後：
1. `PlaybookEvolver.apply_evolution()` 寫入 `evolved_*.yaml`
2. `_run_steps()` 回傳 `PlaybookResult(evolved_playbook_path=...)`
3. `run()` 的外層迴圈執行 `_current_path = result.evolved_playbook_path; fresh = True; continue`
4. **`fresh=True` 使 `_resolve_start` 回傳 `(0, [], True, None)`**

`fresh=True` 代表 Claude Code 的對話歷史完全清空。Claude Code 忘記了：
- 已嘗試的設計方案
- 已完成的部分實作
- 失敗的具體錯誤細節（只有 FailureKnowledgeBase 保留策略摘要）

**跨越演化的持久化狀態**（存活）：
- `FailureKnowledgeBase`（檔案持久化，跨 session 策略歷史）✅
- `_escalation_history`（PlaybookRunner 實例變數，同一 `run()` 呼叫內存活）✅
- 演化版 Playbook 的任務定義（包含更詳細的 prompt）✅

**消失的狀態**（斷點）：
- Claude Code 的完整對話 context（Token HALT）
- 已寫入但未通過測試的程式碼（只剩 git diff 間接保留）
- 步驟間的隱性語義協議（例如 T01 選擇了某個 DB schema，T02 應與之對齊）

---

## 二、極端情境推演：T00_INIT_ENV 注入的完整路徑驗證

**設定**：`global_goal = "建立完整的 FastAPI 登入與資料庫連線模組"`，初始步驟：T01（寫 Auth）、T02（寫 DB）。T01 執行時發現 `requirements.txt` 和基礎 config 都沒有。

### 路徑追蹤

| attempt | 狀態 | allow_mutation | 結果 |
|---------|------|----------------|------|
| T01 attempt=0 | IMPORT error（fastapi not found）| False（`attempt >= 1` 未滿足）| 無用 correction_prompt（建議 `pip install`）|
| T01 attempt=1 | 仍 IMPORT error | True（`_is_prerequisite_error and attempt >= 1`）| Minimax 提議 INJECT_BEFORE T00_INIT_ENV |

**注入後任務清單**：`[T00_INIT_ENV(idx=0), T01(idx=1), T02(idx=2)]`

| 步驟 | step_idx | global_goal 注入到執行 prompt | 說明 |
|------|----------|-------------------------------|------|
| T00_INIT_ENV | 0 | ✅ | 移到 idx=0，觸發 `step_idx == 0` 條件 |
| T01（重執行）| 1 | ❌ **漏洞** | 清理後重新執行，但 step_idx=1 不觸發注入 |
| T02 | 2 | ❌ **漏洞** | 同上 |

**Gap-013-A 熱啟動行為**（正確）：
```
T01 在 step_idx=1 執行時，task.step_id="T01" in _step_trackers → 熱啟動
→ 繼承 tried_strategies（不重試已知失敗的 pip install 策略）✅
```

### 斷層定位

1. **attempt=0 的 1 次浪費**（可接受）：Gap-012-F 已將前提錯誤門檻降至 `attempt >= 1`，這是有意識的 trade-off。
2. **T01/T02 執行時無 global_goal 注入**（重要漏洞，Gap-015）：Claude Code 執行 T01 的完整業務邏輯時，沒有「FastAPI 登入 + DB 連線整合模組」的宏觀目標參考。
3. **DONE 前無全局驗證**（嚴重漏洞，Gap-014）：即使 T01/T02 各自通過測試，沒有驗證它們是否形成一個功能完整的整合模組。

---

## 三、Level 5 動態閉環升級藍圖

### Gap-014（P0）：GlobalGoalFinalValidator — DONE 前的全局目標驗證

**問題**：系統在所有步驟通過後直接宣告 DONE，缺乏 global_goal 的整合驗證。

**解決方案**：在 `_run_steps` 的 while 迴圈結束後（DONE 前），若 `global_goal` 非空，諮詢 Minimax 確認全局目標是否達成。若未達成，自動注入一個「目標補完步驟」繼續執行。

```python
# playbook_runner.py — _run_steps() 最末修改方案
# ── DONE 前的全局目標驗證（Gap-014）──
if playbook.global_goal:
    achievement_check = self._validate_global_goal_achievement(
        playbook, step_log, playbook.global_goal
    )
    if achievement_check is not None:  # 回傳 None 表示目標達成
        # achievement_check 是需要補完的 prompt
        synth_task = PlaybookTask(
            step_id="GOAL_SYNTHESIS",
            name="全局目標最終補完與驗證",
            prompt=achievement_check,
            expected_output_regex=r"目標達成|DONE|完成",
            max_retries=2,
        )
        playbook.tasks.append(synth_task)
        # while 迴圈因 step_idx < len(playbook.tasks) 將繼續執行
        continue  # 重新進入 while，執行 GOAL_SYNTHESIS

# ── DONE ──
```

**新方法 `_validate_global_goal_achievement`**：
```python
def _validate_global_goal_achievement(
    self,
    playbook: Playbook,
    step_log: list[str],
    global_goal: str,
) -> Optional[str]:
    """
    諮詢 Minimax 驗證 global_goal 是否真正達成。
    回傳 None 表示達成；回傳 str 表示補完 prompt。
    """
    achievement_summary = "\n".join(step_log[-20:])  # 最近 20 個步驟記錄
    validation_decision = self._minimax.validate_goal_achievement(
        global_goal=global_goal,
        step_summary=achievement_summary,
        playbook_project=playbook.project,
    )
    if validation_decision.is_achieved:
        return None
    return validation_decision.completion_prompt
```

**MinimaxClient 新增 `validate_goal_achievement()` 方法**：
使用獨立的 system prompt，要求 Minimax 輸出 `{"is_achieved": bool, "completion_prompt": str, "gap_analysis": str}`。

**防無限迴圈保護**：`GOAL_SYNTHESIS` 步驟最多注入一次（用 `_goal_synthesis_injected: bool` flag 防止遞迴）。

---

### Gap-015（P1）：Universal global_goal Injection — 所有步驟首次執行注入

**問題**：`_prepend_global_goal` 只在 `step_idx == 0` 觸發，其他步驟在首次執行時沒有宏觀目標參考。

**解決方案**：將注入條件改為「首次 attempt」（不限 step_idx），但使用**精簡版 global_goal**（前 150 字元），避免每個步驟增加大量 Token 消耗。

```python
# playbook_runner.py:466 — 修改方案
# Gap-015：所有步驟的首次 attempt 都注入精簡 global_goal（取代僅 step_idx==0）
if attempt == attempt_offset:  # 原本：step_idx == 0 and attempt == attempt_offset
    if step_idx == 0:
        # 第一個步驟：完整版（現有行為，500 字元）
        prompt_to_send = self._prepend_global_goal(prompt_to_send, playbook.global_goal)
    else:
        # 後續步驟：精簡版（150 字元），僅提供方向感
        prompt_to_send = self._prepend_global_goal_brief(prompt_to_send, playbook.global_goal)
```

**新方法 `_prepend_global_goal_brief`**：
```python
def _prepend_global_goal_brief(self, prompt: str, global_goal: Optional[str]) -> str:
    """精簡 global_goal 前置（僅供非首個步驟使用，最大 150 字元）。"""
    if not global_goal:
        return prompt
    brief = global_goal[:150] + ("…" if len(global_goal) > 150 else "")
    return f"[總目標方向] {brief}\n\n" + prompt
```

---

### Gap-016（P1）：MinimaxEvolver — AI 驅動的 PlaybookEvolver

**問題**：PlaybookEvolver 是純規則引擎，SPLIT_STEP 用字符位置切割，不諮詢 Minimax。

**解決方案**：新增 `MinimaxEvolver` 類別，替換 PlaybookEvolver 的核心演化邏輯。

```python
# autoclaude/evolution/minimax_evolver.py（新建）
class MinimaxEvolver:
    """
    Level 5 AI 驅動演化引擎。
    在 ESCALATION 時諮詢 Minimax，由 AI 決定最佳演化策略（取代硬編碼規則）。
    """
    
    def propose_evolution_via_ai(
        self,
        playbook: Playbook,
        failed_step_idx: int,
        escalation_dump: EscalationDump,
        minimax_client: MinimaxClient,
    ) -> Optional[PlaybookEvolutionProposal]:
        """
        諮詢 Minimax 分析失敗根因，由 AI 提議最適合的演化策略。
        輸出 JSON schema：
        {
            "evolution_type": "INJECT_STEP" | "SPLIT_STEP" | "REVISE_EVALUATOR",
            "reasoning": "<為何選擇此演化策略>",
            "new_step": { "step_id": ..., "name": ..., "prompt": ... },
            "split_context_bridge": "<T01_B 的 context 前置摘要（用於 SPLIT_STEP）>"
        }
        """
```

**針對 SPLIT_STEP 的語義切割**：Minimax 負責將 prompt 分為兩個語義完整的子任務，而非字符切割。並生成 `split_context_bridge`：一段摘要文字，作為 T01_B 的 prompt 前置，告知 T01_B 「T01_A 已完成了 XXX，你現在負責 YYY」。

**整合方式**：在 PlaybookRunner 的 ESCALATION 路徑中，優先使用 MinimaxEvolver，回退至現有規則引擎作為兜底。

```python
# playbook_runner.py：ESCALATION 路徑修改
_proposal = self._minimax_evolver.propose_evolution_via_ai(
    playbook, step_idx, _dump, self._minimax
)
if _proposal is None:
    # 回退至規則引擎
    _proposal = self._evolver.propose_evolution(
        playbook, step_idx, _dump, self._escalation_history
    )
```

---

### Gap-017（P2）：SKIP_TO Mutation — 前向跳轉能力

**問題**：GOTO_STEP 禁止向前跳轉，系統無法表達「跳過後續冗餘步驟」的路徑。

**解決方案**：新增 `SKIP_TO` 突變類型，允許 Minimax 提議向前跳轉到指定步驟（跳過中間步驟）。

```python
# step_mutation.py 新增
class StepMutationType(str, Enum):
    REVISE_CURRENT = "REVISE_CURRENT"
    INJECT_AFTER   = "INJECT_AFTER"
    INJECT_BEFORE  = "INJECT_BEFORE"
    GOTO_STEP      = "GOTO_STEP"
    DELETE_STEP    = "DELETE_STEP"
    SKIP_TO        = "SKIP_TO"   # Gap-017：跳過當前步驟之後的一組步驟，跳至目標

class StepMutation(BaseModel):
    # ... 現有欄位 ...
    skip_to_step_id: Optional[str] = None   # Gap-017：SKIP_TO 目標步驟 step_id
    skip_reason: Optional[str] = None        # Gap-017：被跳過步驟的原因摘要（記錄至 step_log）
```

```python
# playbook_runner.py：SKIP_TO 處理邏輯
elif (
    _step_mutation.mutation_type == StepMutationType.SKIP_TO
    and _step_mutation.skip_to_step_id
):
    _target_id = _step_mutation.skip_to_step_id
    _target_idx = next(
        (i for i, t in enumerate(playbook.tasks) if t.step_id == _target_id), None
    )
    if _target_idx is not None and _target_idx > step_idx:
        # 記錄被跳過的步驟
        for skipped in playbook.tasks[step_idx + 1:_target_idx]:
            step_log.append(f"[SKIPPED] {skipped.step_id}（Minimax 判定為已隱性完成）")
        _goto_target_idx = _target_idx  # 重用 GOTO 的跳轉機制
        logger.info("=== Gap-017 | SKIP_TO 跳轉至 %s，跳過 %d 個步驟 ===", ...)
        break
```

**安全限制**：
- 只允許向前跳（`_target_idx > step_idx`）
- 每個 step_id 的 SKIP_TO 最多 1 次（防止反覆跳過重要步驟）
- 被跳過的步驟記錄到 step_log，確保可審計

---

### Gap-018（P2）：SplitContextBridge — SPLIT_STEP 上下文傳遞

**問題**：SPLIT_STEP 後 T01_B 不知道 T01_A 完成了什麼。

**解決方案**：在 PlaybookEvolver 的 SPLIT_STEP 中，T01_B 的 prompt 前置一段「context bridge」，告知 Part B 的前提條件。

```python
# playbook_evolver.py：SPLIT_STEP 修改
# Gap-018：加入 context bridge 前置
context_bridge = (
    f"[前置步驟 {sub1_id} 已完成的工作]\n"
    f"前一個子步驟（{sub1_id}）已完成以下工作（請基於此繼續，不要重複）：\n"
    f"- {failed_task.name} 的第一部分（prompt 前半段指令）\n"
    f"請確認 {sub1_id} 的輸出結果，然後繼續完成以下剩餘任務：\n\n"
)
PlaybookTask(
    step_id=sub2_id,
    name=f"{failed_task.name}（第二部分）",
    prompt=context_bridge + prompt_b,   # Gap-018：加入 context bridge
    expected_output_regex=failed_task.expected_output_regex,
    evaluator_command=failed_task.evaluator_command,
    ...
)
```

當 Gap-016 (MinimaxEvolver) 實作後，MinimaxEvolver 生成的 `split_context_bridge` 會更精確（由 AI 生成而非硬編碼模板）。

---

### Gap-019（P2）：Batch Mutation — 批次突變支援

**問題**：每次 Correction 只能提議一個突變，多步驟重組需要多個失敗循環。

**解決方案**：將 `StepMutation` 擴展為支援批次。

```python
# models/step_mutation.py — 擴展方案
class StepMutation(BaseModel):
    # ... 現有欄位保持向下相容 ...
    batch_mutations: Optional[list["StepMutation"]] = None  # Gap-019：批次突變清單

# 若 batch_mutations 非空，PlaybookRunner 依序應用清單中每個突變
```

```python
# playbook_runner.py：批次突變應用
if _step_mutation is not None:
    mutations_to_apply = (
        _step_mutation.batch_mutations
        if _step_mutation.batch_mutations
        else [_step_mutation]
    )
    for single_mutation in mutations_to_apply:
        self._apply_single_mutation(playbook, step_idx, single_mutation, ...)
```

**限制**：批次突變最多 3 個（防止一次性過度修改導致難以追蹤）。

---

### Gap-020（P3）：AppConfig Evolution Parameters

**問題**：`_max_evolutions = 3`（`run()` 第 160 行）是硬編碼常數，應由 AppConfig 管理。

```yaml
# config.yaml 新增欄位
playbook:
  max_evolutions: 3          # Gap-020：最大自動演化次數
  goal_synthesis_enabled: true   # Gap-014：是否啟用 DONE 前的全局目標驗證
  global_goal_brief_chars: 150   # Gap-015：非首個步驟的精簡 global_goal 字元數
```

---

## 四、迭代行動清單（Action Items）

### P0 — 必須實作（影響 Level 5 完整性）

| ID | 檔案 | 函數/類別 | 修改說明 |
|----|------|-----------|---------|
| Gap-014-A | `autoclaude/decision/minimax_client.py` | `validate_goal_achievement()` | 新增全局目標驗證 API 呼叫方法 |
| Gap-014-B | `autoclaude/execution/playbook_runner.py` | `_validate_global_goal_achievement()` | 新增方法，在 DONE 前諮詢 Minimax |
| Gap-014-C | `autoclaude/execution/playbook_runner.py` | `_run_steps()` 末尾 | 插入 global_goal 達成檢查，必要時追加 GOAL_SYNTHESIS 步驟 |
| Gap-014-D | `autoclaude/decision/prompt_builder.py` | `GOAL_VALIDATION_SYSTEM_PROMPT` | 新增全局目標驗證的 system prompt 常數 |

### P1 — 重要改善（提升語義對齊質量）

| ID | 檔案 | 函數/類別 | 修改說明 |
|----|------|-----------|---------|
| Gap-015-A | `autoclaude/execution/playbook_runner.py` | `_prepend_global_goal_brief()` | 新增精簡版 global_goal 前置方法 |
| Gap-015-B | `autoclaude/execution/playbook_runner.py` | `_run_steps()` 第 466-468 行 | 將注入條件從 `step_idx == 0` 改為所有步驟的首次 attempt |
| Gap-016-A | `autoclaude/evolution/minimax_evolver.py` | `MinimaxEvolver` 類別 | 新建 AI 驅動演化引擎 |
| Gap-016-B | `autoclaude/decision/minimax_client.py` | `propose_evolution()` | 新增 AI 演化提議的 API 呼叫 |
| Gap-016-C | `autoclaude/execution/playbook_runner.py` | ESCALATION 路徑 | 優先使用 MinimaxEvolver，回退至規則引擎 |

### P2 — 架構完善（圖靈完備性補完）

| ID | 檔案 | 函數/類別 | 修改說明 |
|----|------|-----------|---------|
| Gap-017-A | `autoclaude/models/step_mutation.py` | `StepMutationType` | 新增 `SKIP_TO` 突變類型 |
| Gap-017-B | `autoclaude/models/step_mutation.py` | `StepMutation` | 新增 `skip_to_step_id`, `skip_reason` 欄位 |
| Gap-017-C | `autoclaude/execution/playbook_runner.py` | `_run_steps()` 突變處理區段 | 實作 SKIP_TO 邏輯（防護：`_target_idx > step_idx`，最多 1 次）|
| Gap-017-D | `autoclaude/decision/prompt_builder.py` | `_MUTATION_SCHEMA_SECTION` | 在文件中新增 SKIP_TO 的 JSON schema 說明 |
| Gap-018-A | `autoclaude/evolution/playbook_evolver.py` | `propose_evolution()` SPLIT_STEP 分支 | 加入 context bridge 前置文字生成 |
| Gap-019-A | `autoclaude/models/step_mutation.py` | `StepMutation` | 新增 `batch_mutations` 欄位 |
| Gap-019-B | `autoclaude/execution/playbook_runner.py` | `_run_steps()` 突變應用區段 | 重構為 `_apply_single_mutation()` + 批次應用 |

### P3 — 配置化（工程品質）

| ID | 檔案 | 函數/類別 | 修改說明 |
|----|------|-----------|---------|
| Gap-020-A | `autoclaude/utils/config.py` | `PlaybookConfig` | 新增 `max_evolutions`, `goal_synthesis_enabled`, `global_goal_brief_chars` |
| Gap-020-B | `autoclaude/execution/playbook_runner.py` | `run()` 第 160 行 | 將 `_max_evolutions = 3` 替換為 `self._cfg.playbook.max_evolutions` |

---

## 五、測試需求估算

| Gap | 預估新測試數 | 測試焦點 |
|-----|-------------|---------|
| Gap-014 | 8 | 全局目標達成判定、GOAL_SYNTHESIS 注入、防遞迴保護 |
| Gap-015 | 4 | 非首個步驟的精簡 global_goal 注入、Token 節省驗證 |
| Gap-016 | 10 | MinimaxEvolver 的三種演化類型、回退至規則引擎、context bridge 生成 |
| Gap-017 | 6 | SKIP_TO 前向跳轉、防止向後跳轉、最多 1 次保護 |
| Gap-018 | 3 | context bridge 前置正確性 |
| Gap-019 | 5 | 批次突變應用順序、最多 3 個限制 |
| Gap-020 | 2 | AppConfig 欄位讀取 |
| **合計** | **~38** | |

---

## 六、系統完備性評估（Gap-014~020 完成後）

| 維度 | 完成後狀態 |
|------|-----------|
| 圖靈完備性 | ✅ 完整（前向/後向跳轉、注入、刪除、批次突變） |
| global_goal 覆蓋率 | ✅ 所有步驟首次執行均有 global_goal 方向感 |
| 全局目標驗證 | ✅ DONE 前主動驗證，不滿足則自動補完 |
| 演化智能 | ✅ AI 驅動（MinimaxEvolver）+ 規則引擎雙保險 |
| 上下文完整性 | ✅ SPLIT_STEP context bridge 防止語義割裂 |
| 配置管理 | ✅ 所有關鍵常數可配置 |

**Level 5 自治開發系統的核心判斷**：Gap-014（全局目標驗證）是從「局部正確性合集」升級到「全局目標達成」的關鍵一躍。沒有它，系統可能以高自信宣告完成了一個在整合層面破碎的產物。

---

**文件元數據**:
- **文件版本**: v1.0
- **建立日期**: 2026-05-05
- **適用 AISDLC 版本**: v0.09+
- **前置文件**: AutoClaude_L5_Evo_001.md、AutoClaude_L5_Evo_002.md
- **覆蓋範圍**: Gap-014 ~ Gap-020（7 個升級項目，預估 38 個新測試）
- **文件狀態**: Active
