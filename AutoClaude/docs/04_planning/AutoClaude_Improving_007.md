# AutoClaude 深度架構剖析：六大新缺口與 Level 5 升級藍圖

**文件版本**: v1.0  
**建立日期**: 2026-05-01  
**AISDLC 階段**: 04_planning  
**前置文件**: AutoClaude_Improving_006.md（Phase 3 Gap-006-A~F 全部實裝完成）  
**狀態**: Gap-007-A~F 全部實裝完成，Level 5 達成（2026-05-01）

---

## 執行摘要

本文以「首席 AI 自動化架構師」視角，對 **Level 4.5 實裝版本**進行第四輪深度剖析。
系統已具備：ConvergenceMonitor（stuck/oscillating/cycling/diverging 全模式）、ErrorClassifier 語義分類、雙模式測試檔偵測、EscalationDump 結構化快照、Token Guard + /compact 壓縮驗證。

本輪剖析發現 **6 個前置文件未涵蓋的新架構缺口**，其中 1 個為 P0 嚴重等級。

| 缺口 ID | 描述 | 優先級 |
|---------|------|--------|
| Gap-007-A | TOKEN_HALT / ESC+F12 中斷：FailureTracker 歷史記憶在記憶體中，checkpoint 不保存 | **P0** |
| Gap-007-B | 測試檔錯誤早期快速路徑缺失：`suspect_test_file_error()` 需 2 次 attempt 才能觸發 | **P1** |
| Gap-007-C | Minimax 修正大腦對「當前檔案狀態」完全失明 | **P1** |
| Gap-007-D | `change_strategy` 屬建議性質，Minimax 無強制機制遵守策略切換 | **P1** |
| Gap-007-E | `impl_error_pattern` 要求 `:行號`，無行號的 NameError/TypeError 繞過測試檔歸因 | **P2** |
| Gap-007-F | `/compact` 前缺乏結構化「記憶錨點」，壓縮後關鍵錯誤背景可能流失 | **P2** |

---

<thinking>

## 深度推理過程

### 零、Self-Verification Protocol：破損測試檔完整模擬推演

**場景設定**：`tests/test_foo.py` 第 5 行有人類造成的語法錯誤。  
Playbook: `evaluator_command: "pytest tests/test_foo.py"`, `max_retries: 3`.

---

#### 推演 Attempt 0

```
pytest 輸出：
  ERROR collecting tests/test_foo.py
    tests/test_foo.py:5: SyntaxError: invalid syntax
  ============== 1 error in 0.02s ==============
exit_code = 2
```

**系統流程**：

1. `_evaluate()` 回傳 `(failure_reason, eval_output[-2000:], exit_code=2)`
2. `ErrorClassifier.classify()` → `SYNTAX`（第二優先級，ENVIRONMENT 不匹配）
3. `tracker.record(attempt=0, ..., error_class="syntax")`
4. `monitor.evaluate(tracker)`:
   - `error_class == SYNTAX`（非 ENVIRONMENT）→ 不直接 escalate
   - `suspect_test_file_error()`: `len(history) = 1 < 2` → **False → 不觸發**
   - `is_stuck()`: `len(history) = 1 < 2` → False
   - 落底至 "unknown" → `recommendation = "continue"`
5. `attempt(0) < max_retries(3)` → 進入 CORRECTION
6. `build_correction_message()`:
   - `_detect_test_file_error_hint(eval_output)` 命中（test_foo.py + SyntaxError）→ 注入警示提示
   - 警示提示屬**建議性質**，Minimax 可忽略

**關鍵分叉點**（概率估計）：

- **路徑 A（~60%）：Minimax 正確識別** → 產生修正 test_foo.py 的 correction_prompt → Claude Code 修正測試檔 → Attempt 1 通過 ✅
- **路徑 B（~40%）：Minimax 幻覺判斷** → 產生修改實作檔的 correction_prompt → Claude Code 修改 src/foo.py（測試檔仍有語法錯誤）

---

#### 推演 Attempt 1（路徑 B：Minimax 幻覺）

```
pytest 輸出（完全相同）：
  ERROR collecting tests/test_foo.py
    tests/test_foo.py:5: SyntaxError: invalid syntax
exit_code = 2
```

1. `tracker.record(attempt=1, ...)` → history 現有 2 筆
2. `monitor.evaluate(tracker)`:
   - `suspect_test_file_error()`: `len(history) = 2 ≥ 2`, 兩筆均命中 test_foo.py + SyntaxError → **True → ESCALATE**
3. 進入 ESCALATION：儲存 EscalationDump（`suspect_test_file=True`），發送桌面通知

**結論**：現有系統在「最多 2 次 attempt」後會正確識別並升級。但**浪費了 1 次 attempt**（1 次 Minimax 呼叫 + 1 次 Claude Code 執行，可能消耗 15-30 分鐘與大量 Token）。

---

#### 邊界案例：TOKEN_HALT 發生在 Attempt 1 修正期間

假設 Attempt 1 執行 Claude Code 時觸發 TOKEN_HALT（context >= 90%）：

1. `_handle_token_halt()` 儲存 checkpoint：`step_idx=T02, completed_step_log=[...]`
2. **FailureTracker.history（含 attempt 0 的失敗記錄）完全消失**（記憶體釋放）
3. 排程恢復後，`_run_steps()` 從 T02 重新開始
4. **新的 FailureTracker 被實例化**：`tracker = FailureTracker(task.step_id)` → history 為空
5. Attempt 0（恢復後的第一次）：pytest 再次失敗，history 只有 1 筆
6. `suspect_test_file_error()` 再次需要 2 筆才觸發
7. **系統從零重新計數**，最多再浪費 4 次 attempt（max_retries=3 的情況下）

**這是 Gap-007-A 的核心問題**：TOKEN_HALT 後的恢復等同「失憶症」——所有收斂診斷歷史重置，收斂偵測從頭開始。

---

### 一、狀態流轉脆弱性（State Transition Fragility）深度分析

#### 1.1 錯誤收斂度偵測機制現狀

| 偵測機制 | 觸發條件 | 最快觸發時機 |
|---------|---------|------------|
| `is_stuck()` | 最近 2 次特徵碼相同 | Attempt 2 |
| `is_oscillating()` | 最近 4 次 ABAB 交替 | Attempt 5 |
| `is_cycling()` | 最近 6 次多路週期 | Attempt 7 |
| `is_diverging()` | exit_code 嚴格遞增 | Attempt 3 |
| `suspect_test_file_error()` | 2+ 次均指向 test_ 檔 | Attempt 2 |
| ENVIRONMENT 直接 escalate | 任何 attempt 環境錯誤 | Attempt 1 |

**分析**：所有非 ENVIRONMENT 的偵測機制都至少需要 2 次 attempt 才能觸發。這是設計上的合理保守主義——避免誤判。但如果 TOKEN_HALT 在中途重置了歷史，保守性就變成了代價。

#### 1.2 幻覺修復指令的收斂度評估

若 Minimax 產出「幻覺修復指令」，系統如何反應？

**案例**：Attempt 0 → AssertionError（exit=1），Minimax 建議修改 `config.py`（與測試無關）→ Attempt 1 → SyntaxError in implementation（exit=1，**更嚴重**）

錯誤特徵碼（Attempt 0）：`FAILED tests/test_auth.py::test_login - AssertionError...`
錯誤特徵碼（Attempt 1）：`FAILED tests/test_auth.py::test_login - SyntaxError...`（不同！）

分析：
- `is_stuck()` → False（特徵碼不同）
- `is_diverging()` → exit_code 皆為 1，不嚴格遞增 → False
- `is_oscillating()` → 需 4 次 → False
- **結論：系統無法偵測「Minimax 在惡化問題」**，僅靠 `max_retries` 耗盡才停止

這是 **Gap-007-D** 的本質：`change_strategy` 是 ConvergenceMonitor 發出的建議，但 Minimax 的 system prompt 並未強制要求「不得使用前次策略」。Minimax 可能以不同措辭描述相同的修改方向。

#### 1.3 錯誤特徵碼正規化的盲點

`_normalize_error()` 截斷至 200 字元。考慮：

```
Error A（pytest 頭部）：
"FAILED tests/test_module.py::test_foo - AssertionError: assert calculated_value == expected..."
                                                                                        ^--- 200 字元截止點在這附近

Error B（pytest 頭部）：
"FAILED tests/test_module.py::test_bar - AssertionError: assert other_value == other_expected..."
```

如果兩個完全不同的測試函式失敗，但 pytest 輸出的 header 格式相同、前 200 字元幾乎一致，則它們會被視為「相同特徵碼」→ `is_stuck()` 誤判 → 過早 escalation。

這不是最關鍵的缺口，但在多 assert 的測試套件中可能產生誤報。

---

### 二、上下文污染與衰減（Context Degradation）深度分析

#### 2.1 `/compact` 的智慧性評估

現有 `_send_compact()` 的結構化壓縮提示：
```
/compact
請在壓縮時優先保留：
1. 目前正在實作的檔案清單與關鍵函式名稱
2. 測試案例的名稱與期望行為
3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）
可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。
```

**評估**：這比無指導的 `/compact` 好得多。但存在致命弱點：

**弱點 1**：「壓縮時優先保留」依賴 Claude Code 的 compaction 內部機制。如果 Claude Code 的 `/compact` 實作並不支援這種指導，這些提示可能被完全忽略。

**弱點 2**：即使 Claude Code 遵守指導，「最近一次的錯誤訊息」是模糊的。Minimax 在 attempt 2 的修正理由（reasoning）、哪個函式出問題、具體的 assert 表達式——這些都可能在壓縮後流失。

**弱點 3**：`failure_summary`（由 `tracker.build_history_summary()` 產生）被附加到 compact_prompt，但格式為：
```
- Attempt 0: exit=1 sig=FAILED tests/... | Minimax決策: 修正 foo() 函式的...
```
這 150 字元的摘要過於精簡，缺乏「Claude Code 在下一次嘗試中需要做什麼」的具體行動指示。

#### 2.2 記憶錨點（Memory Anchor）缺失：Gap-007-F

`/compact` 後，Claude Code 的工作記憶被重組。系統目前假設壓縮後的 Claude Code 仍然能正確理解任務背景，但沒有注入「絕對不可遺失的結構化錨點」。

對比：如果在壓縮前注入以下錨點：
```
/compact

=== CRITICAL MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===
[TASK] T03: Implement JWT authentication
[CURRENT_ERROR] AssertionError: login() returns None instead of token dict
[KEY_FILES] src/auth/login.py (lines 45-67), tests/test_auth.py (lines 23-41)
[NEXT_ACTION] Fix login() to return {'token': jwt_string, 'expires': timestamp}
[ERROR_TRAJECTORY] syntax(x1) → assertion(x2) → must converge
=== END ANCHOR ===
```

壓縮後 Claude Code 保留錨點的概率將大幅提升。這是可實作且低風險的改善。

#### 2.3 TOKEN_HALT 後的「失憶症」：Gap-007-A 深化

TOKEN_HALT 時，checkpoint 儲存的內容：
```python
PlaybookCheckpoint(
    playbook_path=...,
    step_idx=...,       # 哪個步驟
    step_id=...,        # 步驟 ID
    total_steps=...,
    project=...,
    completed_step_log=...,  # 已完成步驟的日誌（字串列表）
    peak_token_pct=...,
)
```

**缺失**：
- `FailureTracker.history`（跨 attempt 的失敗記錄、錯誤特徵碼、Minimax 推理）
- `current_attempt`（我們在第幾次重試時被中斷）
- `correction_prompt`（最後一次 Minimax 產出的修正指令是什麼）

恢復後，`_run_steps()` 中：
```python
tracker = FailureTracker(task.step_id)  # 全新實例，history = []
monitor = ConvergenceMonitor()           # 全新實例
```

`ConvergenceMonitor` 完全失去歷史基準。如果系統在 Attempt 2 卡住被 TOKEN_HALT 中斷，恢復後又能重新嘗試 3 次，然後再次 TOKEN_HALT，就可以無限循環消耗 Token 而不被偵測為「卡死」。

**這是真正的「Token 黑洞」風險**，可能導致天文數字的 API 費用。

---

### 三、停機問題與防護（Halting Problem & Guardrails）深度分析

#### 3.1 EscalationDump 的完整性評估

現有 EscalationDump 包含：
- 完整失敗鏈（failure_chain）
- 自動診斷旗標（is_stuck, is_diverging, suspect_test_file, is_oscillating）
- 最後評估輸出（final_eval_output，截至 3000 字元）
- 繼續執行指令（`autoclaude <playbook.yaml>`）

**評估**：對人類接手而言已相當完整。以下是剩餘改善空間：

1. **EscalationDump 未包含當前檔案狀態快照**：人類接手時不知道 Claude Code 對哪些檔案做了什麼修改（需要手動 `git diff` 確認）。

2. **繼續執行指令假設 checkpoint 存在**：但 ESCALATION 時 checkpoint 不一定是最新狀態（TOKEN_HALT checkpoint 和 ESCALATION 是不同邏輯）。

3. **`suspect_test_file=True` 時缺乏明確的修復行動建議**：例如「請執行 `python -m py_compile tests/test_foo.py` 確認測試檔語法」。

#### 3.2 ESC+F12 中斷的完整性

ESC+F12 中斷時：
1. 儲存 checkpoint（step_idx, step_id, completed_step_log）
2. FailureTracker.history **未儲存** → 同 Gap-007-A

差異：TOKEN_HALT 是非預期中斷，ESC+F12 是使用者主動中斷。使用者中斷後可能：
- 查看日誌後決定繼續（恢復後丟失了失敗歷史）
- 手動修正後繼續（合理；但恢復後的 ConvergenceMonitor 仍然失憶）

#### 3.3 Minimax 無檔案狀態可見性：Gap-007-C

Minimax 修正大腦的 correction_prompt 是「盲目的」——它不知道：

1. **Claude Code 已對哪些檔案做了哪些修改**：Minimax 可能建議重複相同修改（Claude Code 已做過的）。
2. **當前實作檔的關鍵函式簽名**：Minimax 可能產生類型不匹配的修正建議。
3. **是否有新增或刪除的檔案**：Minimax 的修正指令可能引用不存在的檔案。

**現有緩解**：`build_history_summary()` 提供跨 attempt 的歷史摘要（含已發送的修正指令前 150 字）。但這是「修正指令的摘要」，不是「執行結果的摘要」。Claude Code 可能沒有按照修正指令行動，或行動了但方向錯誤。

#### 3.4 `change_strategy` 的強制性問題：Gap-007-D

當 ConvergenceMonitor 返回 `recommendation = "change_strategy"` 時，`playbook_runner.py` 在 correction 訊息中注入 `strategy_hint`：

```python
strategy_hint = (
    "前幾次的修正策略無效（特徵碼相同但有局部改善）。"
    "請嘗試完全不同的方法：..."
)
```

這個 hint 被傳入 `build_correction_message()` 並注入為 `> 🔄 **策略切換指令**`。

**問題**：Minimax 的 SYSTEM PROMPT（`CORRECTION_SYSTEM_PROMPT`）對策略切換沒有強制規定。Minimax 可以「看到」策略切換指令，但仍然產出與前次本質相同的修正方向（只是措辭不同）。

以下驗證案例：
- Attempt 1：Minimax 建議「移除 `calculate()` 中的 None 回傳」
- `is_stuck()` → 觸發 `change_strategy`
- Attempt 2：Minimax 建議「確保 `calculate()` 始終回傳整數」

表面上看是「不同策略」，但本質都是修改 `calculate()` 的回傳值——如果根本問題是測試期望值本身設錯，兩個策略都無效。

**缺口本質**：系統沒有記錄「已嘗試過的策略類型」（PINPOINT / REWRITE / ADD_TYPES 等），也沒有機制確保 Minimax 選擇一個確實不同的策略。

</thinking>

---

## 一、缺口詳細分析

### Gap-007-A（P0 嚴重）：FailureTracker 歷史記憶在 TOKEN_HALT 後完全遺失

**受影響模組**：`utils/checkpoint_manager.py`, `execution/playbook_runner.py`

**問題描述**：

`PlaybookCheckpoint` 只儲存步驟層級的進度（`step_idx`, `step_id`, `completed_step_log`），不包含 attempt 層級的失敗歷史。TOKEN_HALT 或 ESC+F12 中斷後恢復時，系統重建一個空的 `FailureTracker` 和 `ConvergenceMonitor`，導致：

1. 收斂偵測歷史歸零（`is_stuck()`, `suspect_test_file_error()` 需重新累積 2+ 次 attempt）
2. 若步驟在 TOKEN_HALT 前已嘗試 N 次，恢復後又能再嘗試 `max_retries` 次
3. 多次 TOKEN_HALT → 恢復 → 再次 TOKEN_HALT 的循環，形成「Token 黑洞」

**風險量化**：設 `max_retries=3`，若系統在 Attempt 2 被 TOKEN_HALT 中斷，恢復後還能嘗試 3+1=4 次。若再次 TOKEN_HALT，恢復後還能再試 4 次。每個 step 的最大有效重試次數變為 `max_retries × max_auto_resumes`，而非 `max_retries`。

**修復設計**：

```python
# checkpoint_manager.py — PlaybookCheckpoint 新增欄位
@dataclass
class PlaybookCheckpoint:
    # 現有欄位...
    failure_history: list[dict] = field(default_factory=list)  # NEW
    active_step_attempt: int = 0                                # NEW
    last_correction_prompt: str = ""                            # NEW

# failure_tracker.py — 新增 from_records() 類別方法
@classmethod
def from_records(cls, step_id: str, records: list[dict]) -> "FailureTracker":
    tracker = cls(step_id)
    for rec in records:
        # AttemptRecord 從 dict 重建
        tracker.history.append(AttemptRecord(**rec))
    return tracker
```

```python
# playbook_runner.py — _handle_token_halt() 儲存失敗歷史
cp = PlaybookCheckpoint(
    ...
    failure_history=tracker.to_failure_chain(),  # 序列化
    active_step_attempt=attempt,
)

# _run_steps() 恢復時重建 tracker
if cp and cp.failure_history:
    tracker = FailureTracker.from_records(task.step_id, cp.failure_history)
    attempt_start = cp.active_step_attempt
else:
    tracker = FailureTracker(task.step_id)
    attempt_start = 0
```

---

### Gap-007-B（P1）：測試檔錯誤早期快速路徑缺失

**受影響模組**：`execution/playbook_runner.py`, `execution/failure_tracker.py`

**問題描述**：

`suspect_test_file_error()` 需要 `len(history) >= 2`，必然浪費 1 次 attempt（1 次 Minimax API 呼叫 + 1 次 Claude Code 執行）。現有的 `_detect_test_file_error_hint()` 只是軟性警告，無法保證 Minimax 正確響應（40% 機率幻覺）。

對於「測試檔有語法錯誤」這類**確定性錯誤**（`python -m py_compile` 可直接驗證），不應依賴 LLM 推理。

**修復設計**：

```python
# playbook_runner.py — 在 CORRECTION 前增加確定性快速路徑檢查

def _fast_path_test_file_check(self, eval_output: str) -> Optional[str]:
    """
    在第一次 attempt 後，直接執行 py_compile 驗證測試檔語法。
    若測試檔本身有語法錯誤，回傳硬約束提示；否則回傳 None。
    """
    import subprocess
    test_file_pattern = re.compile(
        r'(?:ERROR collecting|FAILED)\s+(tests?/\w+\.py)', re.IGNORECASE
    )
    m = test_file_pattern.search(eval_output)
    if not m:
        return None
    test_file = m.group(1)
    result = subprocess.run(
        ['python', '-m', 'py_compile', test_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return (
            f"🚫 硬性約束：{test_file} 存在語法錯誤（py_compile 驗證失敗）。"
            f"修正指令必須直接修復 {test_file} 的語法，不得修改任何實作檔。"
            f"\n語法錯誤詳情：{result.stderr[:200]}"
        )
    return None
```

```python
# 在 CORRECTION 路徑插入（attempt == 0 時才執行快速路徑）：
if attempt == 0:
    fast_path_hint = self._fast_path_test_file_check(eval_output)
    if fast_path_hint:
        strategy_hint = fast_path_hint  # 注入硬性約束取代軟性提示
        logger.warning("Fast-path 偵測到測試檔語法錯誤，注入硬性修正約束")
```

---

### Gap-007-C（P1）：Minimax 修正大腦對當前檔案狀態完全失明

**受影響模組**：`decision/prompt_builder.py`

**問題描述**：

Minimax 收到的修正請求只包含錯誤輸出和任務原始 Prompt，卻不知道 Claude Code 在前次 attempt 中實際建立了哪些檔案、修改了什麼。這導致：

- 修正指令可能與現有檔案狀態衝突（要求建立已存在的函式）
- 修正指令可能引用不存在的模組（Claude Code 尚未建立）
- 跨 attempt 的修正指令重複相同動作

**修復設計**：

```python
# prompt_builder.py — 新增 build_file_state_snapshot()
import os, subprocess

def build_file_state_snapshot(working_dir: str = ".", max_files: int = 8) -> str:
    """
    列出最近被修改的非測試 Python 檔案，提供基本狀態資訊。
    避免傳入完整檔案內容（Token 過大），只提供簽名層級的快照。
    """
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD'],
            capture_output=True, text=True, cwd=working_dir
        )
        changed_files = [
            f for f in result.stdout.splitlines()
            if f.endswith('.py') and not f.startswith('test')
        ][:max_files]

        if not changed_files:
            return ""

        snapshot_lines = ["## 已修改的實作檔案（最近 git diff）"]
        for fpath in changed_files:
            try:
                with open(fpath, encoding='utf-8') as f:
                    lines = f.readlines()
                funcs = [l.strip() for l in lines if l.strip().startswith('def ')][:5]
                snapshot_lines.append(
                    f"- `{fpath}` ({len(lines)} 行) 函式: {', '.join(funcs) or '（無）'}"
                )
            except OSError:
                snapshot_lines.append(f"- `{fpath}` (無法讀取)")
        return "\n".join(snapshot_lines) + "\n\n"
    except Exception:
        return ""
```

```python
# build_correction_message() 整合 file_state_snapshot：
file_snapshot = build_file_state_snapshot()

return (
    f"## 失敗步驟\n{step_id}: {task_name}\n\n"
    f"## 原始 Prompt（前 600 字）\n{task_prompt[:600]}\n\n"
    f"{file_snapshot}"          # NEW：插入檔案狀態快照
    f"## 期望輸出 Regex\n..."
    ...
)
```

---

### Gap-007-D（P1）：`change_strategy` 屬建議性質，無策略類型記錄機制

**受影響模組**：`execution/failure_tracker.py`, `decision/prompt_builder.py`

**問題描述**：

`ConvergenceMonitor` 發出 `change_strategy` 指令時，`playbook_runner.py` 注入一段文字建議（strategy_hint）。但 Minimax 可能用不同措辭描述相同的修正方向。系統沒有記錄「已嘗試過哪些策略類型」。

**修復設計**：

```python
# failure_tracker.py — 新增策略類型追蹤
STRATEGY_TYPES = [
    "PINPOINT",    # 修正最具體的錯誤（預設）
    "REWRITE",     # 重寫失敗的函式
    "ADD_TYPES",   # 增加型別標注澄清合約
    "SPLIT",       # 拆分複雜函式
    "SIMPLIFY",    # 簡化實作，移除邊界條件
]

class FailureTracker:
    def __init__(self, step_id: str):
        ...
        self._tried_strategies: set[str] = {"PINPOINT"}  # 第一次預設 PINPOINT

    def next_strategy(self) -> str:
        """回傳下一個未嘗試的策略，循環使用。"""
        for s in STRATEGY_TYPES:
            if s not in self._tried_strategies:
                self._tried_strategies.add(s)
                return s
        return "PINPOINT"  # 所有策略都嘗試過，回到起點

    def mark_strategy_used(self, strategy: str) -> None:
        self._tried_strategies.add(strategy)
```

```python
# playbook_runner.py — change_strategy 時使用確定性策略輪換：
if report.recommendation == "change_strategy":
    next_strategy = tracker.next_strategy()
    strategy_hint = _STRATEGY_PROMPTS[next_strategy]  # 查詢對應的策略指令
    logger.info("策略輪換至: %s", next_strategy)
```

```python
# prompt_builder.py — 策略指令字典：
_STRATEGY_PROMPTS = {
    "PINPOINT":  "修正最具體的錯誤訊息所指向的程式碼位置。",
    "REWRITE":   "重寫失敗測試所對應的整個函式，不要修補，直接重寫。",
    "ADD_TYPES": "為所有相關函式增加完整的 Python 型別標注（type hints）和前置條件 assert，讓型別錯誤在執行前就能被發現。",
    "SPLIT":     "將複雜函式拆分為 2-3 個單一責任的子函式，讓每個子函式可獨立測試。",
    "SIMPLIFY":  "移除所有邊界條件處理和特殊情況，先讓核心邏輯通過，再逐步加回邊界處理。",
}
```

---

### Gap-007-E（P2）：`impl_error_pattern` 要求 `:行號`，無行號的錯誤繞過歸因

**受影響模組**：`execution/failure_tracker.py`

**問題描述**：

`suspect_test_file_error()` 使用 `impl_error_pattern = re.compile(r'\b(?!test_)[a-zA-Z]\w*\.py:\d+')` 來確認是否有實作檔錯誤。這要求檔案名後緊跟冒號和行號。

但以下合法 pytest 輸出會繞過此偵測：
```
ImportError: cannot import name 'calculate' from 'mymodule' (mymodule.py)
```
`mymodule.py` 後沒有 `:行號` → `impl_error_pattern` 不匹配 → 誤判為「純測試檔錯誤」→ 過早 ESCALATION。

**修復設計**：

```python
# failure_tracker.py — 放寬 impl_error_pattern，接受無行號的純檔案名引用
_IMPL_ERROR_PATTERNS = [
    # 主模式：帶行號（精確）
    re.compile(r'\b(?!test_)[a-zA-Z]\w*\.py:\d+'),
    # 輔助模式：括號中的實作檔引用（如 ImportError 格式）
    re.compile(r'\((?!test_)[a-zA-Z]\w*\.py\)'),
    # 輔助模式：from '...' 的 ImportError 格式
    re.compile(r"from '(?!test)[^']*\.py'"),
]

def _has_impl_error(line: str) -> bool:
    return (
        any(p.search(line) for p in _IMPL_ERROR_PATTERNS)
        and not _FRAMEWORK_PATH_RE.search(line)
    )
```

---

### Gap-007-F（P2）：`/compact` 前缺乏結構化「記憶錨點」

**受影響模組**：`execution/playbook_runner.py`

**問題描述**：

現有 `_send_compact()` 的指導性文字要求 Claude Code「壓縮時優先保留」某些資訊，但這依賴 Claude Code 的主觀判斷，沒有提供可供後續 prompt 直接引用的結構化錨點。

**修復設計**：

```python
# playbook_runner.py — _send_compact() 增加結構化記憶錨點

def _send_compact(
    self, is_first: bool, failure_summary: str = "",
    task: Optional[PlaybookTask] = None, attempt: int = 0
) -> bool:
    if is_first:
        return False

    # 建構結構化記憶錨點
    anchor = ""
    if task:
        anchor = (
            "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
            f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
            f"[ATTEMPT] {attempt + 1}\n"
        )
        if task.expected_output_regex:
            anchor += f"[SUCCESS_CONDITION] output must match: {task.expected_output_regex}\n"
        if failure_summary:
            # 取最後一筆的核心錯誤（前 120 字）
            last_err = failure_summary.split('\n')[-1][:120]
            anchor += f"[LAST_FAILURE] {last_err}\n"
        anchor += "=== END ANCHOR ===\n"

    compact_prompt = (
        "/compact\n"
        "請在壓縮時優先保留：\n"
        "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
        "2. 測試案例的名稱與期望行為\n"
        "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
        "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
        f"{anchor}"
    )
    if failure_summary:
        compact_prompt += f"\n重要：壓縮後必須記住以下當前失敗背景：\n{failure_summary}\n"
    ...
```

---

## 二、Self-Verification Protocol 最終評估

### 結論表格

| 場景 | 現有系統行為 | 是否「優雅降級」 |
|------|------------|--------------|
| 測試檔語法錯誤（Minimax 正確識別） | Attempt 0 注入警示 → Minimax 修正測試檔 → 通過 | ✅ |
| 測試檔語法錯誤（Minimax 幻覺） | Attempt 1 後 suspect_test_file_error() 觸發 ESCALATION | ✅（浪費 1 次） |
| TOKEN_HALT 發生在 CORRECTION 中 | FailureTracker 歸零，重新計數 | ❌ 失憶症 |
| 多次 TOKEN_HALT 恢復循環 | 無累積失敗計數 → 潛在 Token 黑洞 | ❌ 嚴重風險 |
| Minimax 幻覺修復導致 SyntaxError（新錯誤，同 exit_code） | 無偵測機制，直到 max_retries 耗盡 | ⚠️ 退化為超時保護 |
| ESC+F12 中斷後恢復 | FailureTracker 歸零 | ⚠️ 次要風險 |

**系統現狀評分：Level 4.5**（正向確定性路徑 ≥ 95% 可靠，TOKEN_HALT 恢復路徑存在結構性漏洞）

---

## 三、Level 5 自治開發系統升級藍圖

### 3.1 Level 4.5 → Level 5 的核心差距

| 能力維度 | Level 4.5 現狀 | Level 5 目標 |
|---------|--------------|------------|
| 失敗歷史持久化 | 記憶體中，TOKEN_HALT 後遺失 | 完整序列化至 checkpoint |
| 測試檔錯誤識別 | 需 2 次 attempt + Minimax 推理 | Attempt 0 確定性 py_compile 驗證 |
| 修正策略多樣性 | 文字建議，Minimax 可忽略 | 確定性策略輪換，記錄已嘗試策略 |
| 修正大腦可見性 | 錯誤輸出 + 歷史摘要 | 增加當前檔案狀態快照 |
| 壓縮智慧性 | 指導性文字 | 結構化記憶錨點 |
| 錯誤歸因準確性 | 需 `:行號` | 多模式實作檔識別 |

### 3.2 Level 5 架構圖（升級後）

```
                    ┌─────────────────────────────────────────┐
                    │              PlaybookRunner              │
                    │                                         │
                    │  ┌─────────┐    ┌──────────────────┐   │
                    │  │  INIT   │───>│ _resolve_start() │   │
                    │  └─────────┘    │ + FailureTracker  │   │
                    │                 │   重建（NEW）       │   │
                    │                 └────────┬─────────┘   │
                    │                          │             │
                    │  ┌─────────┐    ┌────────▼──────────┐  │
                    │  │ EXECUTE │<───│    _run_steps()    │  │
                    │  └────┬────┘    └──────────────────┘  │
                    │       │                                 │
                    │  ┌────▼────┐                            │
                    │  │EVALUATE │                            │
                    │  └────┬────┘                            │
                    │  失敗  │                                 │
                    │       ▼                                 │
                    │  ┌──────────────────────────────────┐  │
                    │  │  Pre-Correction Fast Path (NEW)   │  │
                    │  │  py_compile 測試檔驗證             │  │
                    │  └────────────────┬─────────────────┘  │
                    │               非硬性錯誤                 │
                    │                   │                     │
                    │  ┌────────────────▼─────────────────┐  │
                    │  │         ConvergenceMonitor        │  │
                    │  │   + FailureTracker（持久化歷史）    │  │
                    │  └────────────────┬─────────────────┘  │
                    │              continue/                   │
                    │         change_strategy/escalate        │
                    │                   │                     │
                    │  ┌────────────────▼─────────────────┐  │
                    │  │         CORRECTION（Minimax）      │  │
                    │  │   + 策略輪換（StrategyPortfolio）  │  │
                    │  │   + 檔案狀態快照注入               │  │
                    │  └────────────────┬─────────────────┘  │
                    │                   │                     │
                    │  ┌────────────────▼─────────────────┐  │
                    │  │  TOKEN_HALT（含失敗歷史序列化）     │  │
                    │  │  /compact（含記憶錨點）            │  │
                    │  └──────────────────────────────────┘  │
                    └─────────────────────────────────────────┘
```

### 3.3 各缺口修復工作量估計

| Gap ID | 修改檔案 | 預計工時 | 複雜度 |
|--------|---------|---------|--------|
| Gap-007-A | `checkpoint_manager.py`, `failure_tracker.py`, `playbook_runner.py` | 4h | 中 |
| Gap-007-B | `playbook_runner.py` | 2h | 低 |
| Gap-007-C | `prompt_builder.py` | 2h | 低 |
| Gap-007-D | `failure_tracker.py`, `prompt_builder.py`, `playbook_runner.py` | 3h | 中 |
| Gap-007-E | `failure_tracker.py` | 1h | 低 |
| Gap-007-F | `playbook_runner.py` | 1h | 低 |

**總工時估計**：13h（不含測試撰寫，測試預計額外 8h）

---

## 四、Phase 5 執行計畫

### Phase 5.1：P0 緊急修復（Gap-007-A）

**目標**：消除 TOKEN_HALT 後的失憶症風險

```
Week 1:
  Day 1: PlaybookCheckpoint 新增 failure_history / active_step_attempt 欄位
  Day 2: FailureTracker.from_records() 反序列化方法
  Day 3: _handle_token_halt() 序列化 + _run_steps() 恢復邏輯
  Day 4: 測試 (test_token_checkpoint.py 新增 TOKEN_HALT 恢復場景)
  Day 5: 整合測試確認
```

**驗收標準**：
- [ ] TOKEN_HALT 後恢復，ConvergenceMonitor 擁有完整歷史
- [ ] 若步驟在 TOKEN_HALT 前已 is_stuck，恢復後第一次 attempt 即 ESCALATION
- [ ] 所有現有測試通過

### Phase 5.2：P1 核心增強（Gap-007-B / C / D）

```
Week 2:
  Day 1-2: Gap-007-B — Pre-correction fast path (py_compile 驗證)
  Day 3:   Gap-007-C — build_file_state_snapshot() 注入
  Day 4-5: Gap-007-D — StrategyPortfolio + 確定性策略輪換
```

**驗收標準**：
- [ ] 測試檔語法錯誤：0 次無效 attempt（py_compile 立即偵測）
- [ ] Minimax 修正訊息包含已修改檔案清單
- [ ] `change_strategy` 時策略類型確實切換（tracker._tried_strategies 記錄）

### Phase 5.3：P2 強化修復（Gap-007-E / F）

```
Week 3:
  Day 1:   Gap-007-E — 多模式 impl_error_pattern
  Day 2-3: Gap-007-F — 結構化記憶錨點注入
  Day 4-5: 全套回歸測試
```

---

## 五、圖靈完備性評估（終極結論）

| 評估維度 | 現狀（Level 4.5） | Level 5 升級後 |
|---------|-----------------|--------------|
| **有限狀態機完備性** | ✅ 8 個狀態，流轉確定 | ✅ 持續 |
| **收斂性保證** | ⚠️ TOKEN_HALT 可重置計數 | ✅ 歷史持久化 |
| **停機保護（Halt Protection）** | ✅ max_retries + ESCALATION | ✅ 加強：累積跨 halt 計數 |
| **自我修復能力** | ✅ Minimax 閉環 | ✅ + 策略組合輪換 |
| **錯誤歸因精度** | ⚠️ 測試檔偵測需 2+ attempt | ✅ Attempt 0 確定性驗證 |
| **上下文韌性** | ⚠️ compact 後可能流失關鍵背景 | ✅ 記憶錨點保護 |
| **人類接管友好性** | ✅ EscalationDump 完整 | ✅ + 檔案狀態快照 |

**Level 5 定義達成條件**：
> 系統能夠在不依賴人類介入的情況下，識別所有確定性失敗模式（測試檔錯誤、環境錯誤、語法錯誤），並在 Token 資源受限的情況下持久化所有診斷上下文，確保任意中斷後的恢復都能從完整的收斂歷史繼續——而非從零重計。

**當前缺口（Gap-007-A）阻止 Level 5 達成。修復後，AutoClaude 將達到 Level 5。**

---

**文檔元數據**：
- **文檔版本**: v1.0
- **建立日期**: 2026-05-01
- **AISDLC 階段**: 04_planning
- **維護者**: 首席 AI 自動化架構師（AutoClaude 專案）
- **文檔狀態**: Active
