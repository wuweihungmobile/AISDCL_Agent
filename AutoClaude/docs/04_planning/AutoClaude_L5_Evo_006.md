# AutoClaude Level 5 動態閉環升級藍圖 Evo-006

**文檔版本**: v1.0  
**建立日期**: 2026-05-07  
**基準版本**: Evo-005（532 tests passing，Gap-029~038 全數實作完成）  
**文檔目的**: 對 AutoClaude Level 5 自治系統進行第六輪架構級深度漏洞挖掘，提出 Evo-006 升級藍圖

---

## Executive Summary

本文件基於對 `playbook_runner.py`（1985 行）、`step_mutation.py`、`playbook_evolver.py`、`minimax_evolver.py`、`convergence_monitor.py`、`prompt_builder.py` 的完整原始碼審查，以及對三大核心議題（圖靈完備性、目標漂移防護、演化閉環完整性）的 Chain-of-Thought 深度推演，發現 **11 個新 Gap（Gap-039 ~ Gap-049）**，其中包含 **1 個 P1 語意安全 Bug**（`global_goal` 未注入 `/compact` anchor，壓縮後 Claude Code 失去目標對齊），**4 個 P1 架構性缺陷**，以及 6 個 P2/P3 中低影響問題。

---

## `<thinking>` 深度思考分析

### 議題一：動態突變的圖靈完備性（現況：有界非確定性有向圖）

#### Evo-005 後的控制流圖能力盤點

```
當前七種突變操作：
┌─────────────────────────────────────────────────────────────────┐
│ REVISE_CURRENT   修改節點屬性（prompt）                          │
│ INJECT_AFTER     後置插入邊（step_idx + 1）                     │
│ INJECT_BEFORE    前置插入邊（step_idx），立即執行（上限 5 次）   │
│ GOTO_STEP        後向邊（backward jump，max 3x per target）     │
│ DELETE_STEP      移除未來節點（by step_id，idx > current）      │
│ SKIP_TO          前向跳轉（forward jump，max 1x per step_id）   │
│ CONDITIONAL      條件式分支（shell exit code 決策）             │
│ batch_mutations  最多 3 個突變的原子序列（部分組合）            │
└─────────────────────────────────────────────────────────────────┘
```

現有系統理論上具備：有限循環（GOTO，≤3 次）、條件分支（CONDITIONAL）、動態 DAG 操作（INSERT / DELETE / MODIFY）。但對「圖靈完備」的更深層推演揭示了以下殘餘缺口：

#### 缺口 A：GOTO 計數器在 TOKEN_HALT 後重置（跨 Session 無限迴圈漏洞）

```python
# _run_steps() 中的本地變數
_goto_counter: dict[str, int] = {}  # ← 每次 _run_steps 呼叫重置為空
```

TOKEN_HALT 後，外層 `run()` 迴圈重新呼叫 `_run_steps()`，`_goto_counter` 歸零。若某步驟的 GOTO 觸發在 TOKEN_HALT 前僅執行 2 次，TOKEN_HALT 後再次執行又觸發 GOTO，計數仍從 1 開始——實際可執行 GOTO 超過 3 次上限，形成跨 Session 無限迴圈漏洞。

相同問題存在於 `_inject_before_counter` 與 `_skip_to_counter`。

**根本原因**：這三個計數器是 `_run_steps()` 的局部變數，未被納入 Checkpoint 持久化。

#### 缺口 B：SPLIT_STEP 的 prompt 切割策略仍是機械字符分割

`MinimaxEvolver._convert_to_proposal()` 的 SPLIT_STEP：
```python
mid = len(failed_task.prompt) // 2
split_pos = failed_task.prompt.rfind("\n", 0, mid) or mid
prompt_a = failed_task.prompt[:split_pos].strip() or failed_task.prompt
```

這是純字符位置切割。若失敗步驟的 prompt 結構為：
```
步驟 1：建立 models/user.py（需要 SQLAlchemy）
步驟 2：建立 auth/router.py（需要 JWT）
步驟 3：整合測試（需要 1 和 2 都完成）
```
字符中點切割可能落在「步驟 2」中段，Part A 包含不完整的步驟 2，Part B 從步驟 2 中段開始，兩個子步驟語意殘缺。

此外，當 `split_pos = 0`（prompt 第一半無換行符），`rfind` 回傳 -1，`or mid` 使用字符中點——但 Python 中 `failed_task.prompt.rfind('\n', 0, mid) or mid` 的語義是：**-1（falsy）被替換為 mid**，看似正確，但 `-1` 是有效的「未找到」回傳值，此處不應用 `or` 而應用 `if != -1` 判斷。當 prompt 第一個字符恰好是換行時 `rfind` 回傳 0，`0 or mid` 使用 `mid`——邏輯正確但依賴 falsy 語義，可讀性差且易埋 Bug。

#### 缺口 C：CONDITIONAL 評估器的 shell injection 風險

```python
_cond_proc = subprocess.run(
    mutation.condition_evaluator,
    shell=True,   # ← shell=True + Minimax 生成的字串
    ...
)
```

`condition_evaluator` 來自 Minimax 生成的 JSON 字串，`shell=True` 允許嵌入 shell 特殊字符（`;`, `&&`, `|`, `` ` ``）。在受控的測試環境中這不是問題，但若 Minimax 受到 prompt injection 攻擊（例如 eval_output 中包含惡意 shell 指令被 Minimax 反映），可能執行非預期指令。

---

### 議題二：目標漂移防護（新發現的 global_goal 壓縮後失憶漏洞）

#### 最關鍵缺口：`_send_compact()` 接受 `global_goal` 但從不注入

```python
def _send_compact(
    self,
    is_first: bool,
    failure_summary: str = "",
    task: Optional[PlaybookTask] = None,
    attempt: int = 0,
    global_goal: Optional[str] = None,   # Gap-012-E：系統總目標（防止 compact 後漂移）
) -> bool:
    ...
    anchor = ""
    if task:
        anchor = (
            "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
            f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
            f"[ATTEMPT] {attempt + 1}\n"
        )
        anchor += "=== END ANCHOR ===\n"
    # ← global_goal 從未被加入 anchor 或 compact_prompt！
```

Gap-012-E 只添加了參數簽名，但實作體內完全未使用 `global_goal`。這是一個**完整的空實作**。

**觸發場景**：

```
步驟 T05（高重試場景）：
  attempt 3 → correction loop 觸發 TOKEN_COMPACT
  _send_compact(global_goal="建立完整 FastAPI 模組...")
  → compact 成功，Claude Code context 被壓縮
  → 此後 Claude Code 的 session 中已無 global_goal 記憶
  
  attempt 4 → correction_prompt 中有 goal_section（global_goal 重新注入）✓
  但 Claude Code 在 attempt 4 前若有任何自主決策（如選擇實作方向），
  仍在「無 global_goal 知曉」的狀態下進行
```

全部三個 compact 觸發點均有此問題：
1. `CONTEXT_RESET`（step_counter % interval == 0）→ `_send_compact(..., global_goal=playbook.global_goal)`
2. TOKEN_COMPACT after step execution → `_send_compact(..., global_goal=playbook.global_goal)`
3. GOTO 前置 compact（Gap-031）→ `_send_compact(..., global_goal=playbook.global_goal)`

三處都傳入了 `global_goal`，但函數體從不使用它。

#### `_validate_global_goal_achievement()` 的步驟記錄截斷問題

```python
achievement_summary = "\n".join(step_log[-20:])  # ← 只取最後 20 筆
```

對於 20 步驟以上的 Playbook（完全合理的生產場景），T01~T05 的輸出對 GOAL_SYNTHESIS 完全不可見。Minimax 驗證全局目標達成時，可能遺漏早期步驟的關鍵產出（例如 T02 寫了 `auth/router.py`，但記錄超出 20 筆視窗，GOAL_SYNTHESIS 不知道此檔案存在）。

---

### 議題三：錯誤收斂與演化閉環（新發現的演化後全重置問題）

#### 最嚴重缺口：演化後 `fresh=True` 導致所有已完成步驟重新執行

```python
# run() 外層迴圈
if result.evolved_playbook_path and _evolution_count < _max_evolutions:
    _current_path = result.evolved_playbook_path
    fresh = True    # ← 強制從頭開始！
    auto_resume_count = 0
    continue
```

考慮以下情境：
- 10 步驟 Playbook，T01~T08 全部成功（耗時 2 小時）
- T09 ESCALATION → 演化生成 `evolved_playbook.yaml`（T01~T08, T09_PRE, T09, T10）
- `fresh=True` 重啟：T01~T08 全部重新執行（再次耗時 2 小時）
- 若 T09_PRE 也失敗，又觸發二次演化，T01~T08 第三次重複執行

**根本原因**：`fresh=True` 清除了所有 checkpoint，而演化版 YAML 不知道哪些步驟「已在前次 run 中成功」。

**緩解可能性**：在 ESCALATION 前，系統已在 `step_log` 中記錄了所有已成功的步驟。演化後應能利用此資訊，在新 YAML 中設置 checkpoint（跳過已成功步驟），而非強制 `fresh=True`。

#### 演化重啟後 mutation_log 恢復機制的限制

Gap-024-C 在演化版 YAML 的 `evolution_metadata.mutation_log` 中恢復突變歷史，這是正確的。但恢復後只影響 Minimax 的 `mutation_history` 提示，不影響：
1. `_goto_counter`（跨演化的 GOTO 次數未被保護）
2. `_inject_before_counter`（INJECT_BEFORE 注入次數未被保護）
3. `_step_trackers`（所有步驟的 FailureTracker 歷史從零開始）

若演化後重執行 T09 仍失敗，系統不知道「T09_A（INJECT_BEFORE 計數）在上一次 run 已用 3/5 次」，可能無限次注入新前置步驟。

---

### 自我驗證推演（完整版）：T00_INIT_ENV 從 Evo-005 後的狀態

**Evo-005 已修復的斷層**：Gap-036 解決了 INJECT_BEFORE 步驟無評估機制的問題。Minimax 現在需提供 `new_step_evaluator_command`（否則兜底使用 `git diff --stat HEAD | grep -c .`）。

**Evo-006 發現的新斷層**：

```
T01 attempt 2 → INJECT_BEFORE 觸發，插入 T00_INIT_ENV:
    evaluator_command = "python -c 'import fastapi' && echo OK"  # Minimax 提供

TOKEN_COMPACT 在 T00 執行過程中觸發（context 達 compact 門檻）
    _send_compact(global_goal="建立 FastAPI 登入與資料庫連線模組...")
    → anchor 中無 global_goal！
    → compact 後 Claude Code 不再記得「總目標是建立 FastAPI 模組」
    → Claude Code 可能以最小化方式安裝「fastapi」但跳過資料庫依賴（sqlalchemy、alembic）
    → T00 evaluator 通過（python -c 'import fastapi' 成功），但 sqlalchemy 未安裝
    → T02（DB 步驟）因 sqlalchemy IMPORT 失敗而 ESCALATE
```

這是 Evo-005 修復後新出現的「漏掉一個鏈節」情境：T00 評估通過了，但目標對齊（確保安裝所有依賴）在 compact 後失效。

**完整推演結論**：目前系統在 T01 → T00（INJECT_BEFORE）→ T01 的路徑已基本可用（Evo-005 修復後），但在長時間執行（多次 compact）+ 部分依賴場景下，仍有目標漂移風險。

---

## Level 5 動態閉環升級藍圖

### Evo-006 四大升級軸

```
┌─────────────────────────────────────────────────────────────────┐
│  軸 1：目標對齊持久化（Goal Alignment Persistence）            │
│    Gap-039: _send_compact 補完 global_goal anchor（P1）         │
│    Gap-040: _validate_global_goal_achievement 全步驟摘要（P2）  │
│                                                                  │
│  軸 2：演化效率最佳化（Evolution Efficiency）                   │
│    Gap-041: 演化後從最後成功步驟恢復（P1）                      │
│    Gap-042: GOTO/INJECT_BEFORE/SKIP_TO 計數器持久化（P1）       │
│                                                                  │
│  軸 3：語意品質保障（Semantic Quality Hardening）               │
│    Gap-043: SPLIT_STEP 切割邏輯語意修復（P2）                   │
│    Gap-044: GOAL_SYNTHESIS ESCALATION MinimaxEvolver 嘗試（P2） │
│    Gap-045: FailureKnowledgeBase 預播種（P2）                    │
│                                                                  │
│  軸 4：安全與防護完善（Security & Guardrails）                  │
│    Gap-046: CONDITIONAL shell=True 防護（P2）                   │
│    Gap-047: compact anchor 補完 expected_output_regex（P3）     │
│    Gap-048: 演化次數 per-step 追蹤（P3）                         │
│    Gap-049: GOTO 計數上限從 3 提升至可配置（P3）                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Gap 詳細規格

### Gap-039：`_send_compact()` 未注入 `global_goal` 到 MEMORY ANCHOR（P1）

**問題**：`_send_compact()` 接受 `global_goal` 參數（Gap-012-E 添加），但函數體完全未使用它。`/compact` 後 Claude Code context 中無 `global_goal`，直到下一個 AutoClaude 消息才重新注入。在 compact 到下一個 AutoClaude 消息之間的自主決策窗口中，Claude Code 可能偏離整體目標。

**修復**：`autoclaude/execution/playbook_runner.py`，`_send_compact()` 函數體

```python
# 現有（約 1543~1560 行）：
anchor = ""
if task:
    anchor = (
        "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
        f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
        f"[ATTEMPT] {attempt + 1}\n"
    )
    anchor += "=== END ANCHOR ===\n"

# 修復後：
anchor = ""
if task:
    goal_line = ""
    if global_goal:
        _brief = global_goal[:200] + ("…" if len(global_goal) > 200 else "")
        goal_line = f"[GLOBAL_GOAL] {_brief}\n"
    anchor = (
        "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
        f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
        f"[ATTEMPT] {attempt + 1}\n"
        f"{goal_line}"
    )
    anchor += "=== END ANCHOR ===\n"
```

**測試**：在 `test_playbook_runner.py` 增加 2 個測試：
1. `test_gap039_send_compact_includes_global_goal_in_anchor`：驗證 compact_prompt 包含 `GLOBAL_GOAL`
2. `test_gap039_send_compact_no_goal_no_anchor_line`：無 `global_goal` 時 anchor 無 `GLOBAL_GOAL` 行

---

### Gap-040：`_validate_global_goal_achievement()` 步驟記錄截斷（P2）

**問題**：`achievement_summary = "\n".join(step_log[-20:])` 對 20+ 步驟的 Playbook 截斷早期步驟，GOAL_SYNTHESIS 驗證不完整。

**修復**：`autoclaude/execution/playbook_runner.py`，`_validate_global_goal_achievement()`

```python
# 現有：
achievement_summary = "\n".join(step_log[-20:])

# 修復後：使用結構化摘要（完整步數 + 詳細最後 10 筆）
def _build_achievement_summary(step_log: list[str]) -> str:
    total = len(step_log)
    if total <= 20:
        return "\n".join(step_log)
    recent = step_log[-10:]
    earlier_count = total - len(recent)
    earlier_summary = f"[前 {earlier_count} 個步驟已完成，以下為最後 10 個步驟的詳細記錄]"
    return earlier_summary + "\n" + "\n".join(recent)
```

**注意**：新增 `_build_achievement_summary` 靜態方法，替換直接切片。

**測試**：增加 `test_gap040_achievement_summary_truncation`：驗證超過 20 步時摘要包含「前 N 個步驟已完成」標頭。

---

### Gap-041：演化後 `fresh=True` 導致所有已成功步驟重新執行（P1）

**問題**：ESCALATION 觸發演化後，`fresh=True` 強制從 T01 重頭執行，忽略前次 run 中已成功完成的步驟。

**修復設計**：

**方案**：在 `_run_steps()` 於每步驟成功後記錄成功步驟的 `step_id` 到 ESCALATION 前的 checkpoint，演化後重啟時能跳過這些步驟。

**修復 1**：`autoclaude/utils/checkpoint_manager.py`，`PlaybookCheckpoint` 增加 `completed_step_ids`

```python
@dataclass
class PlaybookCheckpoint:
    ...
    completed_step_ids: list[str] = field(default_factory=list)  # Gap-041：已成功步驟 ID 清單
```

**修復 2**：`autoclaude/execution/playbook_runner.py`

在每個步驟成功的 `break` 前，記錄到一個 `_completed_step_ids` 集合：
```python
# 步驟成功後（約 554~567 行）：
_completed_step_ids.add(task.step_id)  # Gap-041：記錄已完成步驟
```

在 ESCALATION 生成 evolved_playbook_path 前，保存一個「已完成步驟快照」checkpoint：
```python
# ESCALATION 觸發演化後（約 641~645 行）：
if _proposal and _evolved_path_esc:
    # Gap-041：儲存已完成步驟快照，供演化後重啟跳過
    _pre_esc_cp = PlaybookCheckpoint(
        playbook_path=str(Path(_evolved_path_esc).name),  # 指向演化版路徑
        step_idx=step_idx,
        step_id=task.step_id,
        total_steps=total,
        project=playbook.project,
        completed_step_log=list(step_log),
        completed_step_ids=list(_completed_step_ids),
    )
    self._checkpoint_mgr.save(_pre_esc_cp, _evolved_path_esc)
```

**修復 3**：`_run_steps()` 中的跳過邏輯

```python
# while 迴圈頂部（每個步驟開始時）：
if task.step_id in _skip_completed_ids:  # Gap-041
    logger.info("=== Gap-041 | 跳過已完成步驟（演化後恢復）: %s ===", task.step_id)
    step_log.append(f"[RESUMED] {task.step_id}（Gap-041：演化前已完成，跳過）")
    step_idx += 1
    continue
```

`_skip_completed_ids` 從 checkpoint 的 `completed_step_ids` 讀取（演化後重啟時有效，正常首次執行為空集合）。

**測試**：增加 `test_gap041_evolution_resumes_from_last_successful_step`：乾跑驗證已完成步驟被跳過。

---

### Gap-042：GOTO / INJECT_BEFORE / SKIP_TO 計數器未持久化到 Checkpoint（P1）

**問題**：`_goto_counter`、`_inject_before_counter`、`_skip_to_counter` 是 `_run_steps()` 的局部 dict，TOKEN_HALT 後重啟時歸零，GOTO 實際可超過 3 次上限。

**修復 1**：`autoclaude/utils/checkpoint_manager.py`，`PlaybookCheckpoint` 增加計數器欄位

```python
@dataclass
class PlaybookCheckpoint:
    ...
    goto_counter: dict = field(default_factory=dict)          # Gap-042
    inject_before_counter: dict = field(default_factory=dict) # Gap-042
    skip_to_counter: dict = field(default_factory=dict)       # Gap-042
```

**修復 2**：`autoclaude/execution/playbook_runner.py`，TOKEN_HALT checkpoint 儲存時包含計數器

```python
# _handle_token_halt() 中（約 1061~1076 行）：
cp = PlaybookCheckpoint(
    ...
    goto_counter=dict(_goto_counter),             # Gap-042
    inject_before_counter=dict(_inject_before_counter),  # Gap-042
    skip_to_counter=dict(_skip_to_counter),       # Gap-042
)
```

**修復 3**：`_run_steps()` 中從 checkpoint 恢復計數器

```python
# _run_steps() 初始化段（約 325~336 行）：
_goto_counter = dict(resume_cp.goto_counter) if resume_cp else {}           # Gap-042
_inject_before_counter = dict(resume_cp.inject_before_counter) if resume_cp else {}  # Gap-042
_skip_to_counter = dict(resume_cp.skip_to_counter) if resume_cp else {}     # Gap-042
```

**測試**：增加 `test_gap042_goto_counter_persisted_across_token_halt`：模擬 TOKEN_HALT → 恢復後 GOTO 計數器繼承。

---

### Gap-043：SPLIT_STEP 切割邏輯的 `rfind or mid` 語意 Bug（P2）

**問題**：`failed_task.prompt.rfind('\n', 0, mid) or mid` 當 `rfind` 回傳 `0`（換行在第一個字符）時，`0 or mid` 回傳 `mid`，語意錯誤（應使用 0 作為切割點）。同時機械字符切割可能破壞語意完整性。

**修復**：`autoclaude/evolution/playbook_evolver.py` 與 `autoclaude/evolution/minimax_evolver.py`

```python
# 現有（兩處相同）：
mid = len(failed_task.prompt) // 2
split_pos = failed_task.prompt.rfind('\n', 0, mid) or mid

# 修復後：
mid = len(failed_task.prompt) // 2
_nl_pos = failed_task.prompt.rfind('\n', 0, mid)
split_pos = _nl_pos if _nl_pos != -1 else mid
```

**額外保護**：確保 Part A 至少有 50 字符（防止空切割）：
```python
if split_pos < 50:
    split_pos = mid  # 兜底到字符中點
```

**測試**：增加 `test_gap043_split_step_rfind_zero_position`：驗證換行在位置 0 時切割正確。

---

### Gap-044：GOAL_SYNTHESIS ESCALATION 不嘗試 MinimaxEvolver（P2）

**問題**：Gap-035 實作了 GOAL_SYNTHESIS ESCALATION 直接返回人工介入，完全跳過 MinimaxEvolver。但 GOAL_SYNTHESIS 失敗通常意味著某個具體功能缺口，MinimaxEvolver 可能識別出需要注入一個「補充實作步驟」。

**修復**：`autoclaude/execution/playbook_runner.py`，GOAL_SYNTHESIS ESCALATION 路徑

```python
# 現有（約 604~618 行 / 707~721 行）：
if _is_goal_synthesis_esc:
    logger.error("=== Gap-035 | GOAL_SYNTHESIS ESCALATION：全局目標最終驗證失敗，需人工介入 ===")
    ...
    return PlaybookResult(False, ...)

# 修復後（Gap-044）：先讓 MinimaxEvolver 嘗試，再才人工介入
if _is_goal_synthesis_esc:
    logger.warning("=== Gap-044 | GOAL_SYNTHESIS ESCALATION：先嘗試 MinimaxEvolver 修復 ===")
    _gs_proposal = self._minimax_evolver.propose_evolution_via_ai(
        playbook, step_idx, _dump, self._minimax
    )
    if _gs_proposal and _gs_proposal.evolution_type == "INJECT_STEP":
        # 允許注入補完步驟，但不允許 SPLIT_STEP（驗證步驟不應拆分）
        _gs_evolved_path = self._evolver.apply_evolution(
            playbook, _gs_proposal, playbook_path, mutation_log=_mutation_log
        )
        if _gs_evolved_path:
            logger.info("=== Gap-044 | GOAL_SYNTHESIS 補完步驟已注入，重載演化版 ===")
            return PlaybookResult(False, ..., evolved_playbook_path=_gs_evolved_path)
    # MinimaxEvolver 無法修復 → 人工介入
    logger.error("=== Gap-044 / Gap-035 | MinimaxEvolver 無法修復 GOAL_SYNTHESIS，需人工介入 ===")
    ...
    return PlaybookResult(False, ...)
```

**測試**：增加 `test_gap044_goal_synthesis_escalation_tries_minimax_evolver_first`

---

### Gap-045：FailureKnowledgeBase 對演化版新注入步驟無先驗知識（P2）

**問題**：演化後重啟，新注入的步驟（例如 T09_PRE）在 FailureKnowledgeBase 中沒有任何記錄。第一次 attempt 不能從 KB 獲益。更重要的是，原始步驟 T09 的失敗模式（`import:ModuleNotFoundError:fastapi`）已在 KB 記錄，但新步驟 T09_PRE 的目的正是解決這個錯誤，KB 的關聯尚未建立。

**修復**：在 `apply_evolution()` 中，為注入的新步驟預播種一條 KB 建議記錄

```python
# autoclaude/evolution/playbook_evolver.py，apply_evolution() 寫入 evolved YAML 後：
# Gap-045：為注入步驟預播種 KB 建議（讓首次 attempt 能直接使用 PINPOINT 策略）
# 此處只記錄元資訊，PlaybookRunner 在首次 attempt 時會查詢
# → 不改 apply_evolution（該函數無 knowledge_base 參數）
# → 改在 PlaybookRunner._run_steps() 的演化後重啟初始化時播種
```

改在 `_run_steps()` 開頭，若檢測到 `evolution_metadata` 存在，對 `escalated_step_ids` 中的每個 step 的前置步驟進行預播種：

```python
# Gap-045：演化後重啟時，為新注入步驟預播種 KB 建議
if playbook.evolution_metadata and playbook.evolution_metadata.escalated_step_ids:
    for _esc_id in playbook.evolution_metadata.escalated_step_ids:
        _pre_id = f"{_esc_id}_PRE"
        _kb_key = f"import:{_pre_id}:env_setup"
        if not self._knowledge_base.query(_kb_key):
            self._knowledge_base.record_success(
                _kb_key, "PINPOINT", _pre_id, error_class="environment"
            )
            logger.debug("Gap-045 | 為 %s 預播種 KB 記錄", _pre_id)
```

**測試**：增加 `test_gap045_knowledge_base_preseeded_for_evolved_steps`

---

### Gap-046：CONDITIONAL mutation 的 `shell=True` 安全防護（P2）

**問題**：`condition_evaluator` 使用 `shell=True` 執行，若 Minimax 受到間接 prompt injection（惡意 eval_output 被反映進 condition_evaluator），可能執行非預期 shell 指令。

**修復**：在執行前對 `condition_evaluator` 進行白名單模式驗證

```python
# autoclaude/execution/playbook_runner.py，CONDITIONAL 分支（約 1913 行）：
_SAFE_COND_PATTERN = re.compile(
    r'^[\w\s\-./|&><=:!"\']+$'  # 允許：字母、數字、常見 shell 操作符；禁止：反引號、$(...)、分號組合
)
if not _SAFE_COND_PATTERN.match(mutation.condition_evaluator.strip()):
    logger.warning(
        "=== Gap-046 | CONDITIONAL evaluator 包含不安全字符，略過: %s ===",
        mutation.condition_evaluator[:80],
    )
else:
    # 原有執行邏輯
    _cond_proc = subprocess.run(...)
```

**測試**：增加 `test_gap046_conditional_rejects_unsafe_evaluator`

---

### Gap-047：compact anchor 缺少 `expected_output_regex`（P3）

**問題**：`/compact` 後的 MEMORY ANCHOR 包含 `ACTIVE_TASK` 和 `ATTEMPT`，但沒有「成功標準」（`expected_output_regex`）。Claude Code 壓縮後可能不記得「此步驟需要輸出包含 `[DONE]`」。

**修復**：`autoclaude/execution/playbook_runner.py`，`_send_compact()` 的 anchor 建構

```python
# 在 anchor 建構段加入（與既有 [ACTIVE_TASK] / [ATTEMPT] 風格一致）：
if task.expected_output_regex:
    anchor += f"[SUCCESS_CONDITION] output must match: {task.expected_output_regex}\n"
```

**標籤名稱說明**：實作採用 `[SUCCESS_CONDITION] output must match:` 而非單純 `[SUCCESS_REGEX]`，原因是：
- 前綴 `output must match:` 更明確指出此為輸出條件約束（人類可讀）
- 標籤命名與既有 `[ACTIVE_TASK]` / `[GLOBAL_GOAL]` 等動作導向標籤一致

**測試**：`test_gap047_compact_anchor_includes_success_regex` 驗證 anchor 包含 `[SUCCESS_CONDITION]`。

---

### Gap-048：演化次數缺少 per-step 追蹤（P3）

**問題**：`_max_evolutions` 是全域上限，但沒有追蹤「同一個步驟觸發了幾次演化」。若 T09 每次演化後仍失敗，可能消耗所有演化配額（例如 `max_evolutions=3` 全被 T09 用完），T10 即使需要演化也無法觸發。

**修復**：在 `_run_steps()` 中維護 `_step_evolution_counter: dict[str, int]`，並在 ESCALATION 觸發演化前檢查

```python
_step_evolution_counter: dict[str, int] = {}  # Gap-048

# 在觸發演化時：
_step_evo_count = _step_evolution_counter.get(task.step_id, 0)
if _step_evo_count >= 2:  # 同一步驟最多演化 2 次
    logger.warning(
        "=== Gap-048 | [%s] 已觸發 %d 次演化，強制人工介入 ===",
        task.step_id, _step_evo_count,
    )
    _proposal = None  # 跳過演化，走人工介入路徑
else:
    _step_evolution_counter[task.step_id] = _step_evo_count + 1
    # 正常演化邏輯...
```

**測試**：增加 `test_gap048_same_step_evolution_limited_to_twice`

---

### Gap-049：GOTO 上限硬編碼為 3，不可從 AppConfig 配置（P3）

**問題**：`_gc > 3` 直接寫死在 `_apply_single_mutation()` 中。對於複雜的迭代開發情境（例如 TDD 循環需要多次回到 T01 確認測試），3 次限制過於保守。

**修復**：`autoclaude/utils/config.py`，`PlaybookConfig` 增加 `max_goto_per_step`

```python
class PlaybookConfig(BaseSettings):
    ...
    max_goto_per_step: int = 3  # Gap-049：GOTO_STEP 每個目標步驟的最大跳轉次數
```

`playbook_runner.py` 中替換硬編碼：
```python
if _gc > self._cfg.playbook.max_goto_per_step:
```

**測試**：增加 `test_gap049_goto_limit_configurable`

---

## 迭代行動清單（Action Items）

### P1 修復（必須立即執行）

| # | Gap | 修改檔案 | 函數 / 位置 |
|---|-----|---------|------------|
| 1 | Gap-039 | `autoclaude/execution/playbook_runner.py` | `_send_compact()` anchor 建構段 |
| 2 | Gap-041 | `autoclaude/utils/checkpoint_manager.py` | `PlaybookCheckpoint` 增加 `completed_step_ids` |
| 2 | Gap-041 | `autoclaude/execution/playbook_runner.py` | ESCALATION 前存 checkpoint；while 頂部跳過已完成 |
| 3 | Gap-042 | `autoclaude/utils/checkpoint_manager.py` | `PlaybookCheckpoint` 增加三個計數器欄位 |
| 3 | Gap-042 | `autoclaude/execution/playbook_runner.py` | `_handle_token_halt()` 儲存；`_run_steps()` 讀取 |

### P2 修復（本批次執行）

| # | Gap | 修改檔案 | 函數 / 位置 |
|---|-----|---------|------------|
| 4 | Gap-040 | `autoclaude/execution/playbook_runner.py` | 新增 `_build_achievement_summary()` 方法 |
| 5 | Gap-043 | `autoclaude/evolution/playbook_evolver.py` | `propose_evolution()` SPLIT_STEP 切割邏輯 |
| 5 | Gap-043 | `autoclaude/evolution/minimax_evolver.py` | `_convert_to_proposal()` SPLIT_STEP 切割邏輯 |
| 6 | Gap-044 | `autoclaude/execution/playbook_runner.py` | GOAL_SYNTHESIS ESCALATION 兩處（行約 604 / 707） |
| 7 | Gap-045 | `autoclaude/execution/playbook_runner.py` | `_run_steps()` 初始化段 KB 預播種 |
| 8 | Gap-046 | `autoclaude/execution/playbook_runner.py` | `_apply_single_mutation()` CONDITIONAL 分支 |

### P3 修復（可選本批次）

| # | Gap | 修改檔案 | 函數 / 位置 |
|---|-----|---------|------------|
| 9 | Gap-047 | `autoclaude/execution/playbook_runner.py` | `_send_compact()` anchor 建構段 |
| 10 | Gap-048 | `autoclaude/execution/playbook_runner.py` | `_run_steps()` ESCALATION 兩處 |
| 11 | Gap-049 | `autoclaude/utils/config.py` | `PlaybookConfig` 增加 `max_goto_per_step` |
| 11 | Gap-049 | `autoclaude/execution/playbook_runner.py` | `_apply_single_mutation()` GOTO 上限判斷 |

---

## 預期測試增量

| 類別 | 新增測試數量 |
|------|------------|
| Gap-039（compact anchor goal） | 2 |
| Gap-040（achievement summary） | 1 |
| Gap-041（evolution resume） | 2 |
| Gap-042（counter persistence） | 2 |
| Gap-043（split_step rfind bug） | 2 |
| Gap-044（goal_synthesis minimax） | 2 |
| Gap-045（KB pre-seeding） | 1 |
| Gap-046（conditional safety） | 2 |
| Gap-047（compact regex anchor） | 1 |
| Gap-048（per-step evolution limit） | 1 |
| Gap-049（goto limit configurable） | 1 |
| **總計** | **17 個新測試** |

**預期測試基線**：532 → **549 tests passing**

---

## 架構演進評估

### 圖靈完備性評分（Evo-006 後）

| 能力維度 | Evo-005 | Evo-006 後 |
|---------|---------|------------|
| 有限循環（GOTO，上限可配置） | ⚠️ 硬編碼 3 | ✅ 可配置 |
| 跨 Session 循環安全 | ❌ 計數器重置 | ✅ 持久化 |
| 條件分支（CONDITIONAL） | ⚠️ shell injection | ✅ 白名單驗證 |
| 動態步驟操作（7 種突變） | ✅ | ✅ |
| 目標對齊（compact 後） | ❌ global_goal 丟失 | ✅ anchor 保留 |
| 演化效率（避免全重跑） | ❌ fresh=True | ✅ 跳過已完成 |

### Level 5 自治成熟度評分

```
Evo-005：████████░░ 82%（核心閉環完整，但目標漂移與演化效率有缺陷）
Evo-006：█████████░ 90%（目標對齊持久化 + 演化效率 + 跨 Session 安全完善）
```

---

**文檔元數據**:
- **文檔版本**: v1.1
- **建立日期**: 2026-05-07
- **最後更新**: 2026-05-07（QA 修復與測試補強）
- **基準測試數**: 532 passed
- **預期測試數**: 549 passed
- **實際測試數**: 558 passed（含 QA 修復後新增測試）
- **實作狀態**: 已完成（558 tests passing）
- **QA 修復內容**: Gap-039 截斷符號、Gap-041 儲存失敗回退、Gap-042 ESC+F12 計數器持久化、Gap-044 fallback 放寬至 REVISE_EVALUATOR、Gap-045 KB 兜底查詢、Gap-046 白名單拒絕鏈式攻擊、Gap-047 標籤名一致性、Gap-048 step_evolution_counter 跨 Session 持久化
- **維護者**: AutoClaude Architecture Team
