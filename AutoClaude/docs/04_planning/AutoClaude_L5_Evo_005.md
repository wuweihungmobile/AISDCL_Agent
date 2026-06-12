# AutoClaude Level 5 動態閉環升級藍圖 Evo-005

**文檔版本**: v1.0  
**建立日期**: 2026-05-07  
**基準版本**: Evo-004（495 tests passing，Gap-021~028 全數實作完成）  
**文檔目的**: 對 AutoClaude Level 5 自治系統進行新一輪架構級深度漏洞挖掘，提出 Evo-005 升級藍圖

---

## Executive Summary

本文件基於對 `playbook_runner.py`（1885 行）、`step_mutation.py`、`playbook_evolver.py`、`convergence_monitor.py`、`prompt_builder.py` 的完整原始碼審查，發現 **10 個新 Gap（Gap-029 ~ Gap-038）**，其中包含 **1 個 P0 系統性 Bug**（所有 Minimax 注入步驟永遠假陽性通過評估），**4 個 P1 高影響問題**，以及 5 個 P2 中等影響設計缺陷。

---

## `<thinking>` 深度思考分析

### 議題一：動態突變的圖靈完備性（現況：Bounded Non-Deterministic Graph）

#### Gap-021~028 實作後的控制流圖能力

```
當前支援的步驟圖轉換操作：
┌─────────────────────────────────────────────────────────────────┐
│ REVISE_CURRENT   修改節點屬性（prompt）                          │
│ INJECT_AFTER     後置插入邊（step_idx + 1）                     │
│ INJECT_BEFORE    前置插入邊（step_idx），立即執行               │
│ GOTO_STEP        後向邊（backward jump，max 3x per target）     │
│ DELETE_STEP      移除未來節點（by step_id，idx > current）      │
│ SKIP_TO          前向跳轉（forward jump，max 1x per step_id）   │
│ CONDITIONAL      條件式分支（shell exit code 決策）             │
│ batch_mutations  最多 3 個突變的原子序列（部分組合）            │
└─────────────────────────────────────────────────────────────────┘
```

系統已從 DAG 升格為「有界非確定性有向圖（Bounded Non-Deterministic Directed Graph）」，具備條件分支與受限循環能力。這不是純粹的圖靈完備——GOTO 的 3 次限制與 INJECT_BEFORE 的 3 次限制確保了有限終止性，這是刻意的安全設計。

#### 識別出的殘餘缺口

**缺口 A：批次 INJECT_BEFORE + INJECT_AFTER 導致錯誤插入順序**

當 `batch_mutations = [INJECT_BEFORE(T01_PRE), INJECT_AFTER(T01_VERIFY)]` 時：

1. INJECT_BEFORE 在 `step_idx=0` 插入 T01_PRE → 任務列表：`[T01_PRE(0), T01(1), T02(2)]`
2. 批次迴圈繼續（**不** 因 `should_break=True` 停止）
3. INJECT_AFTER 在 `step_idx + 1 = 1` 插入 T01_VERIFY → 任務列表：`[T01_PRE(0), T01_VERIFY(1), T01(2), T02(3)]`

**結果**：T01_VERIFY 插入在 T01_PRE 和 T01 之間，而非 T01 之後。語意完全錯誤。

根本原因：`_validate_batch_compatibility()` 阻擋了 GOTO_STEP + INJECT_BEFORE，但未阻擋 INJECT_BEFORE + INJECT_AFTER。且批次迴圈不檢查 `_batch_result.should_break`，導致 INJECT_BEFORE 發生後後序突變仍以原始 `step_idx` 操作已位移的任務列表。

**缺口 B：INJECT_BEFORE/INJECT_AFTER 步驟無評估機制（最高嚴重性）**

`_apply_single_mutation()` 的 INJECT_BEFORE 分支：

```python
_pre_task = PlaybookTask(
    step_id=_proposed_id,
    name=mutation.new_step_name or f"前置步驟（注入於 {task.step_id} 前）",
    prompt=mutation.new_step_prompt,
    # ← 沒有 expected_output_regex
    # ← 沒有 evaluator_command
)
```

`_evaluate()` 的邏輯：

```python
def _evaluate(self, task, output):
    if task.expected_output_regex:   # None → 跳過
        ...
    if task.evaluator_command:       # None → 跳過
        ...
    return None, "", 0   # ← 永遠成功！
```

**結論**：任何 Minimax 提議的 INJECT_BEFORE 或 INJECT_AFTER 步驟，**無論 Claude Code 實際做了什麼，都會在第一次 attempt 判定為成功**。這是系統性假陽性。

INJECT_AFTER 路徑也有相同問題：

```python
_new_task = PlaybookTask(
    step_id=mutation.new_step_id or f"{task.step_id}_INJECT",
    name=mutation.new_step_name or f"{task.name}（注入步驟）",
    prompt=mutation.new_step_prompt,
    # ← 同樣沒有評估欄位
)
```

對比：`PlaybookEvolver.propose_evolution()` 的 INJECT_STEP **確實**設定了 `expected_output_regex` 和 `evaluator_command`（Gap-013-G 已處理）。但 Minimax 路徑完全跳過了這個保護。

---

### 議題二：目標漂移防護（新發現的薄弱環節）

#### GOAL_SYNTHESIS 的評估脆弱性

```python
# playbook_runner.py 約 910 行
synth_task = PlaybookTask(
    step_id="GOAL_SYNTHESIS",
    name="全局目標最終補完與驗證",
    prompt=_completion_prompt,
    expected_output_regex=r"(?:目標達成|DONE|完成|verified|passed)",
    max_retries=2,
    # ← 沒有 evaluator_command
)
```

GOAL_SYNTHESIS 是整個 Level 5 系統最後的防線——確認 `global_goal` 已真正達成。但它的成功判定只靠 Claude Code 輸出包含「目標達成」等關鍵詞。Claude Code 可能在沒有實際驗證的情況下直接輸出「目標達成，所有功能已實作完畢」。

此外，當 GOAL_SYNTHESIS 在 2 次 retry 後仍失敗，ESCALATION 路徑會呼叫 `PlaybookEvolver.propose_evolution()`。Evolver 會分析失敗的 GOAL_SYNTHESIS 步驟（其 prompt 是一段驗證指令），然後提議 SPLIT_STEP——將驗證 prompt 拆成兩個子驗證步驟。這是語意上的謬誤：驗證步驟不應被拆分，應直接觸發人工介入。

#### REVISE_CURRENT 後 `_task_goal_summary` 的快取汙染

`_task_goal_summary` 是每步驟的「任務核心目標 30 字摘要」，在首次 Minimax correction 時由 Minimax 生成。當步驟失敗 retry >= 3 次後，此摘要取代完整 task_prompt 傳遞給 Minimax（Gap-010-B 的漸進式壓縮策略）。

問題在於：若步驟 T01 在第 2 次 attempt 收到 REVISE_CURRENT（步驟 prompt 被完整替換），`_task_goal_summary` 快取的仍是**舊 prompt 的目標摘要**。在 attempt 3+，Minimax 看到的是「修正方向 X」的摘要，但實際步驟已改為「方向 Y」。Minimax 的修正決策在錯誤的目標框架下進行。

---

### 議題三：錯誤收斂與演化衝突（新發現的協作斷層）

#### `PlaybookEvolver.propose_evolution()` 參數 `escalation_history` 從未被使用

函數簽名：
```python
def propose_evolution(
    self,
    playbook: Playbook,
    failed_step_idx: int,
    escalation_dump: EscalationDump,
    escalation_history: Optional[list[EscalationDump]] = None,  # ← 傳入但從不使用
) -> Optional[PlaybookEvolutionProposal]:
    dump = escalation_dump  # 只看當前 dump
    # 函數體中 escalation_history 從未被引用
```

`self._escalation_history` 在 PlaybookRunner 層面跨步驟累積，但 Evolver 從不進行跨步驟模式分析。

**潛在能力缺失**：若 T01、T02、T03 都因 ImportError 而 ESCALATE，Evolver 應能識別「這三個步驟都缺少同一個環境依賴」，並在 T01 之前注入一個全域環境初始化步驟，而非為每個步驟分別注入 T01_PRE、T02_PRE、T03_PRE。

#### GOTO 後的 Context 積壓問題

GOTO_STEP 觸發時，Gap-027 注入了文字提示（`_goto_revisit_hint`）告訴 Claude Code 「忽略先前的失敗嘗試」。但 Claude Code 的 context 中仍然殘留所有先前步驟的實作歷史、修正討論、以及大量 stdout log。

若 context 使用率在 GOTO 時已達 70%+，回到 T01 後的修正迴圈可能在 2~3 次 attempt 後就觸發 TOKEN_HALT，而此時 T01 根本還沒成功。GOTO 缺乏「context 壓縮前置」機制。

---

### 自我驗證推演：T00_INIT_ENV 注入情境

**情境設定**：`global_goal` = 建立 FastAPI 登入與資料庫連線模組；初始步驟：T01（Auth）、T02（DB）。T01 發現缺少 requirements.txt。

#### 完整執行路徑追蹤（當前實作）

```
T01 attempt 0 → ImportError: No module named 'fastapi'
  error_class = IMPORT
  allow_mutation = False（attempt < 1）
  → 普通 CORRECTION：Claude Code 嘗試修正（pip install ... 但 context 無 shell 直接執行能力）
  → 仍然 ImportError

T01 attempt 1
  allow_mutation = True（IMPORT, attempt >= 1）
  → Minimax 收到 allow_step_mutation=True
  ⚠️ 但沒有 mutation pressure 提示！
  → Minimax 可能仍選擇 correction_prompt（「請確認 requirements.txt 存在」）
  → Claude Code 創建 requirements.txt 但沒有 pip install
  → 仍然 ImportError

T01 attempt 2
  → Minimax 現在提議 INJECT_BEFORE T00_INIT_ENV
  → _apply_single_mutation():
      PlaybookTask(step_id="T00_INIT_ENV", prompt="請建立 requirements.txt 並執行 pip install...")
      # ← 沒有 expected_output_regex！沒有 evaluator_command！
      playbook.tasks.insert(0, T00_INIT_ENV)
      result.inject_before_pending = True

外層 while 迴圈：step_idx = 0 → task = T00_INIT_ENV
T00 執行：Claude Code 輸出「已建立 requirements.txt，已執行 pip install」
_evaluate(T00, output):
  expected_output_regex: None → 跳過
  evaluator_command: None → 跳過
  return None, "", 0  ← 永遠成功！
```

**發現的核心斷層**：

1. **斷層 1（最嚴重）**：T00_INIT_ENV 無評估機制，即使 Claude Code 輸出「我無法執行 pip install」，T00 仍判定成功。T01 重試後仍然 ImportError，但系統不知道 T00 根本沒有真正安裝依賴。
2. **斷層 2**：Minimax 在 attempt 1 時有機會提議 INJECT_BEFORE，但沒有 mutation pressure 的引導，可能錯過最佳介入時機，白白浪費一次 attempt。
3. **斷層 3**：T00 的 prompt 是 Minimax 即興生成的，沒有驗證規格（`expected_output_regex` / `evaluator_command`），導致驗證真空。

---

## Level 5 動態閉環升級藍圖

### Evo-005 三大升級軸

```
┌─────────────────────────────────────────────────────────────────┐
│  軸 1：注入步驟評估補完（Injection Evaluation Completeness）   │
│    Gap-036: StepMutation 增加評估欄位（P0）                    │
│    Gap-029: Batch 相容性補漏（INJECT_BEFORE + INJECT_AFTER）   │
│                                                                  │
│  軸 2：終局驗證強化（Terminal Verification Hardening）         │
│    Gap-030: GOAL_SYNTHESIS 增加結構性評估                       │
│    Gap-035: GOAL_SYNTHESIS ESCALATION 特殊處理                  │
│                                                                  │
│  軸 3：突變決策品質提升（Mutation Decision Quality）           │
│    Gap-032: Mutation pressure 漸進偏置                          │
│    Gap-034: REVISE_CURRENT 清除目標摘要快取                     │
│    Gap-033: 跨步驟 Escalation 模式學習                         │
│                                                                  │
│  附加：邊界防護完善                                             │
│    Gap-031: GOTO 前置 /compact                                  │
│    Gap-037: INJECT_BEFORE counter 成功計數                      │
│    Gap-038: CONDITIONAL timeout 可配置                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gap 詳細規格

### Gap-036：StepMutation 缺少注入步驟評估欄位（P0 — 系統性假陽性 Bug）

**問題**：`StepMutation` 的 INJECT_BEFORE / INJECT_AFTER 路徑生成的 `PlaybookTask` 無 `expected_output_regex` 和 `evaluator_command`，`_evaluate()` 永遠回傳成功。

**修復 1：`autoclaude/models/step_mutation.py`**

```python
class StepMutation(BaseModel):
    # ... 現有欄位 ...
    # Gap-036：注入步驟評估欄位（INJECT_BEFORE / INJECT_AFTER 使用）
    new_step_evaluator_command: Optional[str] = None   # 注入步驟的評估指令
    new_step_expected_regex: Optional[str] = None      # 注入步驟的輸出 regex
    new_step_max_retries: Optional[int] = None         # 注入步驟的重試上限
```

**修復 2：`autoclaude/execution/playbook_runner.py`**

在 `_apply_single_mutation()` 的 INJECT_BEFORE 與 INJECT_AFTER 分支：

```python
# INJECT_BEFORE 分支
_pre_task = PlaybookTask(
    step_id=_proposed_id,
    name=mutation.new_step_name or f"前置步驟（注入於 {task.step_id} 前）",
    prompt=mutation.new_step_prompt,
    # Gap-036：使用 Minimax 提供的評估規格（若無，使用 git-diff 兜底驗證）
    expected_output_regex=mutation.new_step_expected_regex,
    evaluator_command=(
        mutation.new_step_evaluator_command
        or "git diff --stat HEAD | grep -c ."  # 兜底：確認有檔案變更
    ),
    max_retries=mutation.new_step_max_retries,
)

# INJECT_AFTER 分支（相同邏輯）
_new_task = PlaybookTask(
    step_id=mutation.new_step_id or f"{task.step_id}_INJECT",
    name=mutation.new_step_name or f"{task.name}（注入步驟）",
    prompt=mutation.new_step_prompt,
    expected_output_regex=mutation.new_step_expected_regex,
    evaluator_command=(
        mutation.new_step_evaluator_command
        or "git diff --stat HEAD | grep -c ."
    ),
    max_retries=mutation.new_step_max_retries,
)
```

**修復 3：`autoclaude/decision/prompt_builder.py`**

在 `_MUTATION_SCHEMA_SECTION` 的 INJECT_BEFORE 和 INJECT_AFTER schema 中加入評估欄位：

```json
{
  "step_mutation": {
    "mutation_type": "INJECT_BEFORE",
    "new_step_id": "<例如 T01_PRE>",
    "new_step_name": "<前置步驟名稱>",
    "new_step_prompt": "<前置步驟的完整 prompt>",
    "new_step_evaluator_command": "<驗證前置步驟成功的 shell 指令，例如 pip show fastapi>",
    "new_step_expected_regex": "<輸出應符合的 regex，選填>",
    "new_step_max_retries": <重試上限整數，選填，不填使用全域設定>,
    "reasoning": "<為何需要前置步驟>"
  }
}
```

**影響**：消除所有 INJECT_BEFORE/INJECT_AFTER 步驟的假陽性通過；T00_INIT_ENV 需真正完成 pip install 才能推進。

---

### Gap-029：批次相容性檢查缺少 INJECT_BEFORE + INJECT_AFTER 規則（P1）

**問題**：`batch_mutations = [INJECT_BEFORE, INJECT_AFTER]` 允許通過相容性驗證，但執行後 INJECT_AFTER 插入位置錯誤（插入在 PRE 步驟和原始步驟之間，而非原始步驟之後）。

**根本原因**：批次迴圈不檢查 `_batch_result.should_break`，INJECT_BEFORE 後 INJECT_AFTER 以舊的 `step_idx` 計算插入位置。

**修復：`autoclaude/execution/playbook_runner.py`**

方案 A（更安全）：在 `_validate_batch_compatibility()` 增加規則：

```python
# Gap-029：INJECT_BEFORE 後接 INJECT_AFTER 會導致插入位置錯誤
inject_after_count = types.count(StepMutationType.INJECT_AFTER)
if inject_before_count >= 1 and inject_after_count >= 1:
    return False, "INJECT_BEFORE 與 INJECT_AFTER 不可同時存在於批次中（插入位置語意衝突）"
```

方案 B（更靈活）：在批次迴圈中檢查 `should_break`：

```python
for _batch_m in _batch:
    _batch_result = self._apply_single_mutation(...)
    if _batch_result.early_return is not None:
        return _batch_result.early_return
    if _batch_result.inject_before_pending:
        _inject_before_pending = True
    if _batch_result.goto_target_idx is not None:
        _goto_target_idx = _batch_result.goto_target_idx
    if _batch_result.should_break:   # Gap-029：位置感知突變後停止批次
        break
```

**推薦**：方案 A 更保守明確，避免後續開發者誤用。

---

### Gap-030：GOAL_SYNTHESIS 缺少結構性評估（P1）

**問題**：`GOAL_SYNTHESIS` 任務只有關鍵詞 regex，無法驗證 global_goal 真正達成。

**修復：`autoclaude/execution/playbook_runner.py`**

讓 `_validate_global_goal_achievement()` 返回 `(completion_prompt, evaluator_hint)` 二元組，其中 `evaluator_hint` 由 Minimax 根據 global_goal 推薦的驗證指令：

```python
# minimax_client.py — GoalAchievementDecision 新增欄位
class GoalAchievementDecision(BaseModel):
    is_achieved: bool
    completion_prompt: Optional[str] = None
    gap_analysis: Optional[str] = None
    suggested_evaluator: Optional[str] = None   # Gap-030：建議的驗證指令

# prompt_builder.py — GOAL_VALIDATION_SYSTEM_PROMPT 新增輸出欄位
# 在 JSON Schema 增加：
# "suggested_evaluator": "<若未達成，建議的 shell 驗證指令，例如 pytest tests/integration/ -v>"

# playbook_runner.py — 注入 GOAL_SYNTHESIS 時使用 suggested_evaluator
synth_task = PlaybookTask(
    step_id="GOAL_SYNTHESIS",
    name="全局目標最終補完與驗證",
    prompt=_completion_prompt,
    expected_output_regex=r"(?:目標達成|DONE|完成|verified|passed)",
    evaluator_command=decision.suggested_evaluator,   # Gap-030
    max_retries=2,
)
```

---

### Gap-032：Minimax correction prompt 缺少突變壓力偏置（P1）

**問題**：`allow_step_mutation=True` 是二元開關，Minimax 無法感知「已累積多少次無效修正」，傾向繼續選擇 correction_prompt 而非 step_mutation。

**修復：`autoclaude/decision/prompt_builder.py`**

在 `build_correction_message()` 新增 `mutation_pressure` 參數（0-3），並在高壓力時強化 mutation 建議文字：

```python
def build_correction_message(
    ...
    mutation_pressure: int = 0,   # Gap-032：突變壓力等級 0-3
) -> str:
    ...
    # Gap-032：在 mutation_history 區段後注入突變壓力提示
    mutation_pressure_section = ""
    if mutation_pressure >= 1:
        pressure_labels = {
            1: "⚠️ 注意：已有 1 次 correction 無效，建議考慮 step_mutation。",
            2: "⚠️ 強烈建議：已有 2 次 correction 無效，請優先使用 INJECT_BEFORE 或 REVISE_CURRENT。",
            3: "🚨 緊急：已有 3+ 次 correction 無效，必須使用 step_mutation，禁止再次輸出純 correction_prompt。",
        }
        mutation_pressure_section = f"\n> {pressure_labels[min(mutation_pressure, 3)]}\n\n"
    ...
```

在 `playbook_runner.py` 的 `_get_correction()` 呼叫中計算並傳入 `mutation_pressure`：

```python
# Gap-032：計算突變壓力（有效 correction 次數且 allow_step_mutation=True）
_mutation_pressure = (
    sum(1 for r in tracker.history if r.correction_prompt_sent and not r.mutation_applied)
    if allow_mutation else 0
)
```

（`FailureRecord` 需新增 `mutation_applied: bool = False` 欄位，在 `_apply_single_mutation` 成功後設為 True。）

---

### Gap-035：GOAL_SYNTHESIS ESCALATION 不應觸發 PlaybookEvolver（P1）

**問題**：GOAL_SYNTHESIS 是元驗證步驟，ESCALATION 後 `PlaybookEvolver` 提議 SPLIT_STEP，將驗證 prompt 拆成兩個子驗證——語意荒謬，且 sub-step 評估器不知如何驗證半個 global_goal。

**修復：`autoclaude/execution/playbook_runner.py`**

在兩個 ESCALATION 路徑中，為 GOAL_SYNTHESIS 步驟跳過 Evolver：

```python
# Gap-035：GOAL_SYNTHESIS ESCALATION 不使用 Evolver，直接人工介入
_is_goal_synthesis = (task.step_id == "GOAL_SYNTHESIS")
if not _is_goal_synthesis:
    _proposal = self._minimax_evolver.propose_evolution_via_ai(...)
    if _proposal is None:
        _proposal = self._evolver.propose_evolution(...)
    ...
else:
    logger.error(
        "=== Gap-035 | GOAL_SYNTHESIS ESCALATION：全局目標最終驗證失敗，需人工介入 ==="
    )
    self._notify(
        "AutoClaude — 全局目標驗證失敗，需人工介入",
        f"global_goal 在 GOAL_SYNTHESIS 步驟重試 {max_retries + 1} 次後仍無法達成。\n"
        f"缺口分析請查閱 EscalationDump。"
    )
    return PlaybookResult(
        False, len(step_log), total,
        "GOAL_SYNTHESIS ESCALATION：全局目標未達成，需人工介入",
        workflow, step_log,
    )
```

---

### Gap-031：GOTO 前缺乏 /compact 前置機制（P2）

**問題**：GOTO_STEP 跳回先前步驟時，Claude Code context 含有所有後序步驟的完整歷史。Gap-027 的文字提示不能減少實際 token 使用量。當 context 已達 70%+ 時，回跳後的修正迴圈很快就觸發 TOKEN_HALT。

**修復：`autoclaude/execution/playbook_runner.py`**

在 `_apply_single_mutation()` GOTO_STEP 分支，當 `_goto_target_idx` 設定後，在外層執行 GOTO 前置 /compact：

```python
# 在 while 主迴圈的 GOTO 處理區段（約 884 行）
if _goto_target_idx is not None:
    _prev_step_idx = step_idx
    # Gap-031：GOTO 前若 context 偏高則預先 /compact
    if (
        not self._dry_run
        and self._cfg.token_guard.enabled
        and self._step_counter > 0
    ):
        # 使用特殊 GOTO anchor，說明上下文重置原因
        _goto_anchor_task = playbook.tasks[_goto_target_idx]
        logger.info(
            "=== Gap-031 | GOTO 前置 /compact（目標步驟 %s）===",
            _goto_anchor_task.step_id,
        )
        self._send_compact(
            False,
            task=_goto_anchor_task,
            attempt=0,
            global_goal=playbook.global_goal,
        )
    step_idx = _goto_target_idx
    _goto_target_idx = None
    continue
```

---

### Gap-033：`PlaybookEvolver.propose_evolution()` 未使用 `escalation_history`（P2）

**問題**：函數接受 `escalation_history` 參數但函數體中從未引用，跨步驟失敗模式分析能力為零。

**修復：`autoclaude/evolution/playbook_evolver.py`**

在 `propose_evolution()` 開頭加入跨步驟模式分析：

```python
def propose_evolution(self, playbook, failed_step_idx, escalation_dump, escalation_history=None):
    dump = escalation_dump
    _global_max = playbook.global_invariants.max_retries_per_step
    _inject_max_retries = max(2, min(_global_max, 3))

    # Gap-033：跨步驟 escalation 模式分析（若有歷史）
    if escalation_history and len(escalation_history) >= 2:
        _error_classes = [d.failure_chain[-1].error_class for d in escalation_history
                          if d.failure_chain]
        _common_class = max(set(_error_classes), key=_error_classes.count)
        _class_count = _error_classes.count(_common_class)
        if _class_count >= 2 and _common_class in ("import", "environment"):
            # 多個步驟都因環境問題 ESCALATE → 注入全域環境初始化
            _earliest_idx = escalation_history[0].step_id  # 第一個 ESCALATION 的步驟
            logger.warning(
                "Gap-033 | 跨步驟模式：%d 個步驟均因 %s 失敗，建議全域環境前置步驟",
                _class_count, _common_class,
            )
            return PlaybookEvolutionProposal(
                evolution_type="INJECT_STEP",
                inject_before_idx=0,   # 插入到最前面
                reasoning=f"{_class_count} 個步驟均因 {_common_class} 失敗，注入全域環境設置步驟",
                new_step=PlaybookTask(
                    step_id="ENV_INIT_GLOBAL",
                    name="全域環境初始化（跨步驟模式修復）",
                    prompt=(
                        "多個步驟均因環境依賴問題失敗。\n"
                        "請執行：\n"
                        "1. 確認 requirements.txt 存在且完整\n"
                        "2. 執行 pip install -r requirements.txt\n"
                        "3. 確認 python -c 'import fastapi, sqlalchemy' 無錯誤\n"
                        "4. 輸出「環境初始化完成」"
                    ),
                    expected_output_regex="環境初始化完成",
                    evaluator_command="python -c 'import fastapi' && echo 'OK'",
                    max_retries=_inject_max_retries,
                ),
            )
    # ... 繼續原有 Case 1/2/3 邏輯
```

---

### Gap-034：REVISE_CURRENT 後 `_task_goal_summary` 快取未清除（P2）

**問題**：REVISE_CURRENT 替換步驟 prompt 後，`_task_goal_summary` 仍為舊 prompt 的目標摘要，導致後續高重試時 Minimax 在錯誤框架下制定修正策略。

**修復方案**：在 `_MutationResult` 新增 `clear_goal_summary: bool = False` 欄位，並在 `_apply_single_mutation()` REVISE_CURRENT 路徑設為 True；`_run_steps()` 的突變後處理中清除快取。

**修復：`autoclaude/execution/playbook_runner.py`**

```python
@dataclass
class _MutationResult:
    should_break: bool = False
    inject_before_pending: bool = False
    goto_target_idx: Optional[int] = None
    early_return: Optional["PlaybookResult"] = None
    clear_goal_summary: bool = False    # Gap-034

# _apply_single_mutation REVISE_CURRENT 分支末尾：
result.clear_goal_summary = True   # Gap-034：步驟 prompt 已變更，舊摘要失效

# _run_steps 批次/單一突變處理後：
if _mut_result.clear_goal_summary:
    _task_goal_summary = None   # Gap-034：讓下次 correction 重新生成摘要
    logger.info("Gap-034 | REVISE_CURRENT：清除 _task_goal_summary 快取")
```

---

### Gap-037：`_inject_before_counter` 計入失敗的 PRE 步驟（P2）

**問題**：INJECT_BEFORE 觸發後即刻遞增計數器，但若注入的 PRE 步驟最終 ESCALATE（因 Gap-036 修復後 PRE 步驟確實會進入評估流程），計數器已耗盡。3 次失敗的 PRE 步驟後，無法再為原始步驟注入任何前置步驟，即使問題是可修復的。

**修復方案**：改為延遲計數——在 PRE 步驟成功完成後才遞增計數（需要在步驟成功路徑中查詢「此步驟是否為 INJECT_BEFORE PRE 步驟」並更新其原始步驟的計數器）。

暫行方案：將上限從 3 提升至 5（`if _cnt > 5`），給予更多嘗試空間，同時避免架構複雜化。

---

### Gap-038：CONDITIONAL `condition_evaluator` 超時硬編碼為 30 秒（P2）

**問題**：`subprocess.run(mutation.condition_evaluator, shell=True, ..., timeout=30)` 中的 30 秒是硬編碼。在每次 CORRECTION 迴圈中若有 CONDITIONAL 突變，每次評估最長等待 30 秒。

**修復：`autoclaude/utils/config.py`**

```python
class PlaybookConfig(BaseModel):
    ...
    conditional_evaluator_timeout_seconds: int = 5   # Gap-038：CONDITIONAL 評估超時
```

**修復：`autoclaude/execution/playbook_runner.py`**

```python
# _apply_single_mutation CONDITIONAL 分支
_cond_proc = subprocess.run(
    mutation.condition_evaluator,
    shell=True, capture_output=True,
    timeout=self._cfg.playbook.conditional_evaluator_timeout_seconds,  # Gap-038
)
```

---

## 迭代行動清單（Action Items）

| Gap | 優先級 | 受影響檔案 | 修改函數/位置 | 測試建議 |
|-----|--------|-----------|--------------|---------|
| **Gap-036** | P0 | `models/step_mutation.py` | `StepMutation` 新增 3 個欄位 | `test_models.py`：驗證新欄位序列化/反序列化 |
| **Gap-036** | P0 | `execution/playbook_runner.py` | `_apply_single_mutation` INJECT_BEFORE/AFTER 分支 | `test_playbook_runner.py`：inject step without evaluator should use git-diff fallback |
| **Gap-036** | P0 | `decision/prompt_builder.py` | `_MUTATION_SCHEMA_SECTION` INJECT 類型 schema | `test_decision.py`：Minimax schema 包含 evaluator 欄位 |
| **Gap-029** | P1 | `execution/playbook_runner.py` | `_validate_batch_compatibility()` | `test_playbook_runner.py`：INJECT_BEFORE + INJECT_AFTER batch 被拒絕 |
| **Gap-030** | P1 | `decision/minimax_client.py` | `GoalAchievementDecision` + `validate_goal_achievement()` | `test_decision.py`：decision 包含 suggested_evaluator |
| **Gap-030** | P1 | `execution/playbook_runner.py` | `_run_steps()` GOAL_SYNTHESIS 注入區段（約 910 行） | `test_playbook_runner.py`：GOAL_SYNTHESIS 使用 suggested_evaluator |
| **Gap-032** | P1 | `decision/prompt_builder.py` | `build_correction_message()` 新增 `mutation_pressure` | `test_decision.py`：不同壓力等級生成不同文字 |
| **Gap-032** | P1 | `execution/playbook_runner.py` | `_get_correction()` 計算並傳入 `mutation_pressure` | `test_playbook_runner.py`：dry_run 模式驗證壓力傳遞 |
| **Gap-035** | P1 | `execution/playbook_runner.py` | 兩個 ESCALATION 路徑（約 598、690 行）新增 `_is_goal_synthesis` 判斷 | `test_playbook_runner.py`：GOAL_SYNTHESIS ESCALATION 不觸發 Evolver |
| **Gap-031** | P2 | `execution/playbook_runner.py` | `_run_steps()` GOTO 跳轉前（約 884 行） | `test_playbook_runner.py`：dry_run 驗證 compact 調用邏輯 |
| **Gap-033** | P2 | `evolution/playbook_evolver.py` | `propose_evolution()` 頂端加入跨步驟分析 | `test_playbook_runner.py`：多步驟同類型 ESCALATION 觸發 ENV_INIT_GLOBAL |
| **Gap-034** | P2 | `execution/playbook_runner.py` | `_MutationResult` + `_apply_single_mutation` + `_run_steps` 突變後處理 | `test_playbook_runner.py`：REVISE_CURRENT 後 goal_summary 被清除 |
| **Gap-037** | P2 | `execution/playbook_runner.py` | `_apply_single_mutation` INJECT_BEFORE 的 `_cnt > 3` 改為 `_cnt > 5` | `test_playbook_runner.py`：第 4/5 次 INJECT_BEFORE 不被拒絕 |
| **Gap-038** | P2 | `utils/config.py` | `PlaybookConfig` 新增 `conditional_evaluator_timeout_seconds: int = 5` | `test_models.py`：config 序列化驗證 |
| **Gap-038** | P2 | `execution/playbook_runner.py` | `_apply_single_mutation` CONDITIONAL 分支 timeout 改用 config | `test_playbook_runner.py`：CONDITIONAL 使用 config timeout |

---

## 執行影響評估

### Gap-036 修復後的 T00_INIT_ENV 場景重演

```
T00_INIT_ENV 注入（Minimax 提供 new_step_evaluator_command="pip show fastapi && echo OK"）
    ↓
T00 執行：Claude Code 嘗試 pip install fastapi
    ↓
_evaluate(T00):
  evaluator_command = "pip show fastapi && echo OK"
  exit code 0 → 成功 ✅ (OR exit code != 0 → 失敗 → CORRECTION 迴圈)
    ↓
T01 繼續，fastapi 已確認安裝 → 成功
```

**效果**：T00 不再假陽性通過，系統確保環境真正就緒後才推進。

### 測試數量預估

| Gap | 新增測試數 |
|-----|----------|
| Gap-036 | 8 |
| Gap-029 | 3 |
| Gap-030 | 4 |
| Gap-032 | 5 |
| Gap-035 | 3 |
| Gap-031 | 2 |
| Gap-033 | 3 |
| Gap-034 | 3 |
| Gap-037 | 2 |
| Gap-038 | 2 |
| **合計** | **~35 新增測試** |

預計執行 Evo-005 後：**495 + 35 = ~530 測試通過**。

---

## 優先執行順序

```
Phase 1（P0，立即修復）：
    Gap-036 → 消除 INJECT 步驟假陽性
        tests/test_models.py
        tests/test_playbook_runner.py（INJECT 評估路徑）
        tests/test_decision.py（Minimax schema）

Phase 2（P1，本迭代完成）：
    Gap-029 → batch 相容性補漏
    Gap-035 → GOAL_SYNTHESIS ESCALATION 保護
    Gap-030 → GOAL_SYNTHESIS 結構性評估
    Gap-032 → mutation pressure 偏置

Phase 3（P2，下一迭代）：
    Gap-034 → REVISE_CURRENT goal summary 清除
    Gap-031 → GOTO 前置 /compact
    Gap-033 → 跨步驟 escalation 學習
    Gap-037 → counter 邏輯改善
    Gap-038 → CONDITIONAL timeout 可配置
```

---

**文檔元數據**:
- **文檔版本**: v1.0
- **建立日期**: 2026-05-07
- **適用版本**: AutoClaude Gap-029 ~ Gap-038
- **預計測試增量**: ~35 新增測試（總計約 530）
- **最高嚴重性 Gap**: Gap-036（P0 — 系統性假陽性）
