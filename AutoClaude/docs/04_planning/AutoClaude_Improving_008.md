# AutoClaude 深度剖析與 Level 5 升級藍圖

**文件編號**: AutoClaude_Improving_008
**建立日期**: 2026-05-01
**分析視角**: 首席 AI 自動化架構師（Andrej Karpathy 風格）
**分析對象**: AutoClaude Level 4.5→Level 5 升級差距
**先決條件**: Gap-006-A~F 和 Gap-007-A~F 已全部實作完畢

---

## Executive Summary

AutoClaude 目前架構在 Level 4.5 位置——具備完整的「卡死偵測、振盪偵測、週期偵測、測試檔語法快速路徑、Checkpoint 恢復、Memory Anchor 壓縮」能力。然而在「圖靈完備的自動化閉環」要求下，仍存在 **3 個結構性盲區**，在極端邊界案例下會導致系統無法收斂，直到 Token 耗盡後被迫 ESCALATION：

1. **`is_diverging()` 依賴 exit_code，對 pytest 完全失效**（最高優先）
2. **`suspect_test_file_error()` 不覆蓋 AssertionError**（最危險語意盲區）
3. **`build_history_summary()` 線性增長無去重**（Token 炸彈，N 次相同錯誤 = N 份拷貝）

本文件提出 Gap-008-A 至 Gap-008-E 五個升級項目，並提供 Level 5 完整架構藍圖。

---

## Part I：深度剖析

### 1.1 狀態流轉脆弱性（State Transition Fragility）

#### 1.1.1 `is_diverging()` 的根本性缺陷

**程式碼位置**：`autoclaude/execution/failure_tracker.py:178-183`

```python
def is_diverging(self) -> bool:
    """exit_code 嚴格遞增（且都非 0）→ Minimax 在惡化問題。"""
    if len(self.history) < 2:
        return False
    exit_codes = [r.exit_code for r in self.history]
    return all(exit_codes[i] < exit_codes[i + 1] for i in range(len(exit_codes) - 1))
```

**問題分析**：pytest 規範定義：
- 所有測試通過 → exit_code=0
- 任何測試失敗 → exit_code=1（不管是 1 個或 100 個）
- 收集錯誤（SyntaxError）→ exit_code=2

因此，「Minimax 給出幻覺修復，失敗數從 3 個增加到 12 個」的情況下：

```
Attempt 0: 3 failed → exit_code=1
Attempt 1: 12 failed（Minimax 惡化）→ exit_code=1
is_diverging(): 1 < 1 → False → 不觸發！
```

#### 1.1.2 ConvergenceMonitor 的完整決策盲區模擬

假設 Minimax 幻覺修復導致每次失敗數遞增（3→7→12）：

| 偵測方法 | 條件 | 結果 | 說明 |
|---------|------|------|------|
| environment | FileNotFoundError? | ❌ False | 不是環境錯誤 |
| suspect_test_file | AssertionError in test file? | ❌ False | 只偵測 Syntax/Import/Name |
| is_stuck | 特徵碼相同? | ❌ False | 不同 tests 失敗，特徵碼不同 |
| is_oscillating | ABAB 交替? | ❌ False | 每次都不同 |
| is_cycling | ABCABC 週期? | ❌ False | 不夠次數 |
| is_diverging | exit_code 遞增? | ❌ False | 1→1→1 無變化 |
| _is_count_improving | 斜率 < -0.5? | ❌ False（斜率為正）| 但結果是 "continue"！ |

**最終判斷**：`"無法判定趨勢，繼續重試"` → recommendation = `"continue"`

**這是一個嚴重缺陷**：在 Minimax 幻覺修復越改越壞的情況下，系統會無腦繼續重試，直到 `max_retries` 耗盡後才 ESCALATION。每次重試都消耗大量 Token 且可能進一步污染代碼庫。

#### 1.1.3 `_should_compact_now()` 邊界條件

**程式碼位置**：`autoclaude/execution/playbook_runner.py:849-867`

當 CORRECTION 迴圈中 `attempt > 0` 且 `correction_history_len <= 1` 時，門檻提高到 85%。但如果 compact 失敗後（Gap-006-D 的 warning），系統只是記錄 warning 而不觸發 TOKEN_HALT。如果 compact 連續失敗 2 次，系統仍然繼續執行，context 會在 80-85% 之間浮動，無限循環。

---

### 1.2 上下文污染與衰減（Context Degradation）

#### 1.2.1 `build_history_summary()` 線性增長問題

**程式碼位置**：`autoclaude/execution/failure_tracker.py:221-239`

```python
def build_history_summary(self) -> str:
    lines = ["### 歷次失敗記錄（從最舊到最新）"]
    for rec in self.history:
        corr_preview = ...  # 前 150 字的 correction_prompt
        lines.append(f"- Attempt {rec.attempt}: ...")
    return "\n".join(lines)
```

**問題**：如果同一個錯誤（特徵碼相同）重複 5 次（in `is_stuck` 觸發前），Minimax 收到 5 份相同的錯誤記錄。這是純粹的 Token 浪費，且可能讓 Minimax 產生「確認偏誤」——看到同一個模式 5 次後更傾向於給出類似的「修正」。

每次 attempt 增加約 200-350 字元的 history summary。10 次 attempt 後，傳給 Minimax 的 message 增加了 2000-3500 字元。

#### 1.2.2 `/compact` 的 Memory Anchor 截斷問題

**程式碼位置**：`autoclaude/execution/playbook_runner.py:893-897`

```python
if failure_summary:
    last_err = failure_summary.split("\n")[-1][:120]
    anchor += f"[LAST_FAILURE] {last_err}\n"
```

壓縮後的 Memory Anchor 只保留最後一筆失敗的前 120 字。這意味著 Claude Code 在壓縮後：
- **丟失了**：之前嘗試過哪些修正方向
- **丟失了**：Minimax 分析的根因（reasoning）
- **保留了**：當前任務 ID 和期望 regex

如果下一次 Minimax 給出的修正方向和之前完全相同，Claude Code 會「再度嘗試已知失敗的方案」。

#### 1.2.3 `build_correction_message()` 的 Token 累積分析

每次調用 `_get_correction()` 傳給 Minimax 的 message 包含：

| 部分 | 大小 | 成長模式 |
|------|------|---------|
| 原始 prompt（前 600 字）| ~600 chars | 固定 |
| file_state_snapshot | ~200-500 chars | 每次 git diff 不同 |
| 關鍵錯誤行（最多 20 行）| ~400-800 chars | 每次不同 |
| history_summary | **N × 200-350 chars** | 線性增長 |
| convergence_trend/reasoning | ~100 chars | 固定 |
| strategy_hint | ~100 chars | 固定 |

在第 8 次重試時，history_summary 單獨就有 1600-2800 字元，超過 correction_prompt 上限 500 字的 5 倍。

---

### 1.3 停機問題與防護（Halting Problem & Guardrails）

#### 1.3.1 EscalationDump 評估

**EscalationDump 強項**（已實作良好）：
- `failure_chain` 含完整失敗歷史（attempt/exit_code/error_class/correction_prompt_sent）
- 四個診斷旗標（is_stuck/is_diverging/is_oscillating/suspect_test_file）
- `checkpoint_resume_hint` 提供繼續指令
- `human_hint` 提供具體建議
- Markdown 格式易於人類閱讀

**EscalationDump 現有 Gap**：
1. 沒有「建議優先審查的實作檔清單」（雖然 prompt_builder 有 git diff，但 dump 沒有包含）
2. `is_worsening`（失敗數遞增）診斷旗標缺失
3. 沒有「測試期望值可能錯誤」的語意診斷旗標

#### 1.3.2 桌面通知資訊密度

`notify_escalation()` 目前通知內容是：step_id + human_hint（短）。實際上，人類最想快速看到的是「失敗模式類型」（卡死？振盪？測試檔問題？）和「dump 檔路徑」。後者已有 dump_path 參數，但 human_hint 的品質依賴 ConvergenceMonitor 的推理品質。

---

## Part II：Self-Verification Protocol 推演

### 場景 A：test_foo.py 含 SyntaxError

```python
# test_foo.py（人類寫錯）
def test_compute()  # 缺少冒號
    result = compute(10)
    assert result == 100
```

**模擬流程**：

```
Attempt 0:
  evaluator: pytest tests/test_foo.py
  輸出: "ERROR collecting tests/test_foo.py ... SyntaxError: invalid syntax"
  
  → _fast_path_test_file_check() [Gap-007-B]:
    regex 匹配 "ERROR collecting tests/test_foo.py"
    運行: python -m py_compile tests/test_foo.py
    → FAIL（語法錯誤確認）
    → 返回硬性約束: "🚫 硬性約束：tests/test_foo.py 存在語法錯誤..."
  
  → Minimax 收到硬性約束，生成: "修正 tests/test_foo.py 第 N 行的語法錯誤，不得修改實作檔"
  → Claude Code 修正 test_foo.py 的語法

  [Case A1] 修正成功 → pytest 通過 → DONE ✅（1 次嘗試解決）
  
  [Case A2] Claude Code 修正方向錯誤，Attempt 1 仍然失敗（仍有 test file error）:
    → tracker.history 有 2 筆，都有 test file error
    → suspect_test_file_error() → True（len >= 2，SyntaxError in test file）
    → ConvergenceMonitor: ESCALATION "錯誤始終指向測試檔，修改實作無效"
    → EscalationDump 保存，suspect_test_file=True
    → 人類收到通知，接手診斷
```

**結論：SyntaxError 場景被正確處理 ✅**，最多 2 次 attempt 後優雅停止。

---

### 場景 B：test_foo.py 含語意錯誤（最危險盲區）

```python
# test_foo.py（人類寫錯期望值）
def test_compute():
    result = compute(10)
    assert result == 42  # 人類寫錯！compute(10) 正確答案是 100
```

**模擬流程**：

```
Attempt 0:
  evaluator: pytest tests/test_foo.py
  輸出: "FAILED tests/test_foo.py::test_compute - AssertionError: assert 100 == 42"
  
  → ErrorClassifier: ASSERTION
  
  → _fast_path_test_file_check() [Gap-007-B]:
    regex 匹配 "FAILED tests/test_foo.py"
    運行: python -m py_compile tests/test_foo.py
    → 語法正確，py_compile 通過
    → 返回 None（不觸發！）
  
  → _detect_test_file_error_hint() [prompt_builder]:
    搜尋 SyntaxError|ImportError|NameError|ModuleNotFoundError
    → AssertionError 不在模式中 → 不生成提示！
  
  → suspect_test_file_error():
    搜尋 SyntaxError|ImportError|NameError|ModuleNotFoundError
    → AssertionError 不在模式中 → False！
  
  → Minimax 判斷：compute(10) 應該返回 42
  → Claude Code 修改實作：compute(10) 返回 42

Attempt 1:
  compute(10) 現在返回 42，test_compute 通過！
  但是 test_compute_negative 失敗（因為 compute 邏輯被破壞）
  
  → 現在有不同的失敗：不同特徵碼 → is_stuck = False
  → exit_code 仍然 1 → is_diverging = False
  → 失敗數從 1 增加到 2 → is_worsening 應觸發但方法不存在！
  → ConvergenceMonitor: "無法判定趨勢，繼續重試"

Attempt 2, 3, 4...:
  系統持續修改實作去匹配錯誤的期望值
  整個代碼庫逐漸被污染
  
最終（max_retries 耗盡）:
  ESCALATION: "重試超限: 評估指令失敗"
  EscalationDump 保存，但 suspect_test_file=False（AssertionError 未被識別為測試檔問題）
  人類接手後需要從 failure_chain 手動判斷根因
```

**結論：語意測試錯誤是 AutoClaude 最危險的未解 Gap ❌**

系統無法區分「實作邏輯錯了」（應修實作）vs「測試期望值錯了」（應修測試），當錯誤是 AssertionError 時，系統會盲目地「修正實作去匹配錯誤的期望值」，造成代碼庫污染。

---

## Part III：現有系統完整評分

| 能力維度 | 機制 | 評分（/10）| 說明 |
|---------|------|-----------|------|
| 卡死偵測 | is_stuck + consecutive_threshold | **9** | ✅ 完善 |
| 振盪偵測 | is_oscillating + is_cycling | **9** | ✅ 完善 |
| 語法測試檔偵測 | suspect_test_file + Gap-007-B | **7** | ✅ SyntaxError 覆蓋良好 |
| **發散惡化偵測** | is_diverging（exit_code）| **3** | ❌ pytest exit_code 永遠 1 |
| **語意測試錯誤** | 無 | **0** | ❌ AssertionError 完全盲區 |
| Context 壓縮 | /compact + Memory Anchor | **7** | ⚠️ history dedup 缺失 |
| History 去重 | 無 | **2** | ❌ 線性增長 Token 炸彈 |
| 人類接手文檔 | EscalationDump Markdown | **8** | ✅ 完善 |
| 恢復能力 | Checkpoint + auto_resume | **9** | ✅ 完善 |
| 環境錯誤偵測 | ErrorClassifier + ConvergenceMonitor | **9** | ✅ 完善 |

**整體 Level 評分：4.5/5**
**Level 5 缺口：3 個結構性 Gap（008-A、008-B、008-C）**

---

## Part IV：Agentic 閉環升級策略

### Gap-008-A：失敗數惡化偵測器（Worsening Detector）

**位置**：`autoclaude/execution/failure_tracker.py` + `autoclaude/execution/convergence_monitor.py`

**問題根因**：`is_diverging()` 依賴 exit_code，對 pytest 的 1/1 失效。需要基於「失敗測試數趨勢」的惡化偵測。

**設計方案**：

```python
# failure_tracker.py 新增方法

def is_worsening(self, window: int = 3, threshold_ratio: float = 1.5) -> bool:
    """
    失敗數嚴格遞增且最後一次比第一次多 threshold_ratio 倍 → Minimax 在惡化問題。
    
    條件：
    1. 至少 window 筆記錄
    2. 所有記錄都能提取到失敗數
    3. 最後 window 筆的失敗數趨勢為嚴格遞增
    4. 最後一筆比最初多 threshold_ratio 倍（避免 1→2 這種雜訊觸發）
    
    Args:
        window: 檢查的最近 attempt 數量
        threshold_ratio: 惡化判定倍率（預設 1.5x，即失敗數增加 50%）
    """
    if len(self.history) < window:
        return False
    
    recent = self.history[-window:]
    counts = []
    for r in recent:
        count = self._extract_fail_count_from_output(r.eval_output)
        if count is None:
            return False  # 任何一次無法提取 → 無法判斷
        counts.append(count)
    
    # 所有計數都非零
    if any(c == 0 for c in counts):
        return False
    
    # 嚴格遞增且最後一次是最初的 threshold_ratio 倍以上
    is_strictly_increasing = all(counts[i] < counts[i + 1] for i in range(len(counts) - 1))
    is_significant_increase = counts[-1] >= counts[0] * threshold_ratio
    return is_strictly_increasing and is_significant_increase

@staticmethod
def _extract_fail_count_from_output(eval_output: str) -> Optional[int]:
    """從 eval_output 中提取失敗測試數（與 ConvergenceMonitor 共用邏輯）。"""
    for pattern in _FAIL_COUNT_PATTERNS:
        m = pattern.search(eval_output)
        if m:
            return int(m.group(1))
    return None
```

**ConvergenceMonitor 整合**：

```python
# convergence_monitor.py: evaluate() 方法中，在 is_diverging() 之後加入

# 優先級 3.5：失敗數嚴格遞增（Minimax 策略使情況惡化）
if tracker.is_worsening():
    return ConvergenceReport(
        0.0, "worsening", fail_counts, "escalate",
        f"失敗數嚴格遞增（{fail_counts[-3:]}），Minimax 策略持續惡化問題，需人工介入",
    )
```

**EscalationDump 整合**：

```python
# escalation.py 新增欄位
is_worsening: bool = False  # 失敗數遞增（Minimax 越改越壞）

# to_markdown() 中新增
f"- 失敗數惡化（越改越多）: {yes if self.is_worsening else no}",
```

**測試驗證**：

```python
def test_is_worsening():
    tracker = FailureTracker("T01")
    # 模擬失敗數 3→7→12（明顯惡化）
    tracker.record(0, "fail", "3 failed\n1 error", 1, "")
    tracker.record(1, "fail", "7 failed\n2 errors", 1, "")
    tracker.record(2, "fail", "12 failed\n3 errors", 1, "")
    assert tracker.is_worsening() is True

def test_is_worsening_noise_tolerant():
    tracker = FailureTracker("T01")
    # 1→2 不應觸發（閾值 1.5x）
    tracker.record(0, "fail", "2 failed", 1, "")
    tracker.record(1, "fail", "2 failed", 1, "")  # 不夠 window=3
    assert tracker.is_worsening() is False
```

---

### Gap-008-B：History Summary 去重壓縮

**位置**：`autoclaude/execution/failure_tracker.py:221-239`

**問題根因**：相同的 error_signature 在 history_summary 中重複出現 N 次。

**設計方案**：

```python
def build_history_summary(self, max_unique_records: int = 5) -> str:
    """
    給 Minimax 的跨 attempt 歷史摘要（去重 + 限制長度）。
    
    去重策略：相同 error_signature 只保留最新一筆 + 累計出現次數。
    這樣 Minimax 可以看到：
    - 這個錯誤已出現 3 次（而不是看到 3 份重複）
    - 最新一次的詳細資訊（最具代表性）
    - Minimax 針對這個錯誤已給出的修正方向（避免重複建議）
    """
    if not self.history:
        return ""
    
    # 去重：相同 error_signature 只保留最新記錄 + 計數
    sig_count: dict[str, int] = {}
    sig_latest: dict[str, AttemptRecord] = {}
    for rec in self.history:
        sig = rec.error_signature
        sig_count[sig] = sig_count.get(sig, 0) + 1
        sig_latest[sig] = rec  # 覆蓋，保留最新
    
    # 排序：最多出現的在前（代表最頑固的問題）
    sorted_sigs = sorted(sig_count.keys(), key=lambda s: sig_count[s], reverse=True)
    top_sigs = sorted_sigs[:max_unique_records]
    
    lines = [
        f"### 歷次失敗摘要（去重後 {len(top_sigs)}/{len(sig_count)} 種錯誤）",
        f"總嘗試次數: {len(self.history)}",
    ]
    
    for sig in top_sigs:
        rec = sig_latest[sig]
        count = sig_count[sig]
        repeat_tag = f"（已出現 {count} 次）" if count > 1 else ""
        corr_preview = ""
        if rec.correction_prompt_sent:
            corr_preview = (
                f"\n  └─ Minimax 針對此錯誤的最後修正方向（前 120 字）: "
                f"{rec.correction_prompt_sent[:120]}"
            )
        lines.append(
            f"- Attempt {rec.attempt}{repeat_tag}: exit={rec.exit_code} "
            f"class={rec.error_class} "
            f"sig={rec.error_signature[:80]}"
            f"{corr_preview}"
        )
    
    # 若有被截斷，說明數量
    if len(sig_count) > max_unique_records:
        lines.append(f"  ... (另有 {len(sig_count) - max_unique_records} 種錯誤已省略)")
    
    return "\n".join(lines)
```

**效果**：
- 原本 10 次相同錯誤 = 10 行（~3500 字元）
- 去重後 = 1 行（~400 字元）+ 「已出現 10 次」標記
- 壓縮率：約 **87.5%**，同時保留「頻率」資訊讓 Minimax 判斷頑固程度

---

### Gap-008-C：語意測試錯誤偵測（Semantic Test File Error）

**位置**：`autoclaude/execution/failure_tracker.py` + `autoclaude/execution/convergence_monitor.py` + `autoclaude/decision/prompt_builder.py`

**問題根因**：`suspect_test_file_error()` 只覆蓋 SyntaxError/ImportError/NameError，不覆蓋 AssertionError（測試期望值錯誤是最常見的「測試寫錯」情況）。

**設計方案**：

#### 階段 1：FailureTracker 新增語意分析

```python
def suspect_assertion_baseline_mismatch(self, min_attempts: int = 3) -> bool:
    """
    偵測「測試期望值可能寫錯」的語意模式：
    
    條件（同時滿足）：
    1. 至少 min_attempts 次嘗試
    2. 全部都是 ASSERTION error class
    3. 失敗數沒有減少（Minimax 改了但沒有讓更多測試通過）
    4. 錯誤特徵碼在相同測試函式之間變化（Minimax 在改不同地方）
    
    語意：「不管怎麼改實作，同一批測試始終失敗 → 可能是期望值問題」
    
    注意：這是「懷疑」而非「確認」，必須搭配 human_hint 明確說明。
    """
    if len(self.history) < min_attempts:
        return False
    
    # 條件 1：全部都是 assertion error
    all_assertion = all(r.error_class == "assertion" for r in self.history)
    if not all_assertion:
        return False
    
    # 條件 2：失敗數沒有減少（或缺失的話，嘗試次數沒有帶來收斂）
    fail_counts = [
        self._extract_fail_count_from_output(r.eval_output)
        for r in self.history
    ]
    valid_counts = [c for c in fail_counts if c is not None]
    if len(valid_counts) >= 2:
        if valid_counts[-1] < valid_counts[0]:
            return False  # 失敗數有在減少，不懷疑
    
    # 條件 3：特徵碼變動超過 2 種（Minimax 嘗試了多種修法都沒用）
    unique_sigs = set(r.error_signature for r in self.history)
    return len(unique_sigs) >= 2
```

#### 階段 2：ConvergenceMonitor 整合

```python
# 在 evaluate() 中，在 suspect_test_file_error() 之後加入

# 優先級 1.5：語意測試錯誤懷疑（AssertionError 基線不匹配）
if tracker.suspect_assertion_baseline_mismatch():
    return ConvergenceReport(
        0.1, "assertion_baseline_mismatch", fail_counts, "escalate",
        (
            "所有失敗都是 AssertionError 且多次修改實作無效。"
            "⚠️ 高度懷疑測試期望值本身有誤——請人工確認測試的 assert 值是否正確。"
        ),
    )
```

#### 階段 3：EscalationDump 新增旗標

```python
# escalation.py 新增欄位
suspect_assertion_mismatch: bool = False  # 語意：測試期望值可能錯誤

# to_markdown() 中新增
f"- 疑似測試期望值寫錯（AssertionError 多次無法收斂）: {yes if self.suspect_assertion_mismatch else no}",
```

#### 階段 4：prompt_builder 新增早期警示

```python
def _detect_assertion_test_error_hint(eval_output: str, retry_count: int) -> str:
    """
    若輸出是 AssertionError 且在 test_ 檔案中，第 2 次 attempt 後生成強警示。
    讓 Minimax 在 correction_prompt 中明確分析「是實作邏輯錯，還是期望值錯」。
    """
    if retry_count < 2:
        return ""
    
    assertion_in_test_pattern = re.compile(
        r'test_\w+\.py.*AssertionError|AssertionError.*test_\w+\.py',
        re.IGNORECASE,
    )
    if assertion_in_test_pattern.search(eval_output):
        # 嘗試提取 assert 的比較值
        assert_pattern = re.compile(r'assert\s+(\S+)\s+==\s+(\S+)', re.IGNORECASE)
        m = assert_pattern.search(eval_output)
        values_hint = f"（比較: {m.group(1)} vs {m.group(2)}）" if m else ""
        
        return (
            f"\n> ⚠️ **語意測試警告** {values_hint}: 已重試 {retry_count} 次，"
            "AssertionError 持續發生於測試檔中。\n"
            "請在 correction_prompt 中明確聲明你的判斷：\n"
            "A) 這是**實作邏輯錯誤**（assert 的實際值 wrong）→ 修改實作\n"
            "B) 這是**測試期望值錯誤**（assert 的期望值 wrong）→ 修改測試\n"
            "若判斷為 B，correction_prompt 必須包含修改測試檔的指令。\n\n"
        )
    return ""
```

---

### Gap-008-D：Minimax Prompt 置信度防護（Hallucination Guard）

**位置**：`autoclaude/decision/minimax_client.py`（後處理驗證）

**問題根因**：目前系統無法偵測 Minimax 是否給出「幻覺修復指令」（例如：與上次完全相同的 correction_prompt、過短的 prompt、沒有引用具體錯誤位置的 prompt）。

**設計方案**：

```python
# minimax_client.py 新增後處理驗證

def _validate_correction_quality(
    self,
    correction_prompt: str,
    previous_prompts: list[str],
    failure_reason: str,
) -> tuple[bool, str]:
    """
    驗證 Minimax 生成的 correction_prompt 品質。
    返回 (is_valid, reason)。
    
    品質標準：
    1. 長度合理（50-1000 字元）
    2. 與上次不完全相同（非重複建議）
    3. 包含具體錯誤引用（數字、檔案名、函式名其中一個）
    """
    if len(correction_prompt) < 50:
        return False, f"correction_prompt 過短（{len(correction_prompt)} 字元），可能是幻覺"
    
    if len(correction_prompt) > 1000:
        # 過長的 prompt 可能包含過多無關背景，截斷並警告
        return True, "correction_prompt 過長（已截斷使用前 1000 字元）"
    
    # 與上次相比相似度 > 90% → 懷疑重複
    if previous_prompts:
        last = previous_prompts[-1]
        # 簡單的 edit distance 代理：最長公共子序列長度
        similarity = _rough_similarity(correction_prompt, last)
        if similarity > 0.90:
            return False, f"correction_prompt 與上次高度相似（相似度 {similarity:.0%}），可能是幻覺重複"
    
    # 應包含具體錯誤引用（行號、Python 關鍵字、測試函式名等）
    has_specific_reference = bool(re.search(
        r'(?:line \d+|\.py|def \w+|assert\s|SyntaxError|ImportError|TypeError|'
        r'assert\s+\w+\s*==|return\s+\w+)',
        correction_prompt,
        re.IGNORECASE,
    ))
    if not has_specific_reference:
        return False, "correction_prompt 缺乏具體錯誤引用，可能是通用幻覺建議"
    
    return True, "ok"


def _rough_similarity(a: str, b: str) -> float:
    """快速估算兩段文字的相似度（基於共同詞彙）。"""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union if union > 0 else 0.0
```

**PlaybookRunner 整合**：
當 `_validate_correction_quality()` 返回 `is_valid=False` 時，記錄警告並觸發 `change_strategy`（而不是繼續使用幻覺 prompt）：

```python
# playbook_runner.py: _get_correction() 後加入驗證
if corr_result:
    correction_prompt, minimax_reasoning = corr_result
    
    # Gap-008-D：Minimax 幻覺防護
    previous_prompts = [r.correction_prompt_sent for r in tracker.history if r.correction_prompt_sent]
    is_valid, quality_reason = self._validate_correction_quality(
        correction_prompt, previous_prompts, failure_reason
    )
    if not is_valid:
        logger.warning("=== Gap-008-D | Minimax 品質驗證失敗: %s ===", quality_reason)
        # 強制切換策略後重新詢問 Minimax
        next_strat = tracker.next_strategy()
        strategy_hint = STRATEGY_PROMPTS.get(next_strat, STRATEGY_PROMPTS["PINPOINT"])
        # 重新呼叫一次 _get_correction 帶入策略提示
        ...
```

---

### Gap-008-E：連續 compact 失敗自動升級

**位置**：`autoclaude/execution/playbook_runner.py:_send_compact()`

**問題根因**：`/compact` 失敗後只記錄 warning，沒有升級路徑。

**設計方案**：

```python
# PlaybookRunner 新增計數器
self._consecutive_compact_failures = 0

# _send_compact() 修改
def _send_compact(self, is_first: bool, ...) -> bool:
    ...
    compact_out = self._execute_prompt(...)
    
    if compact_out.triggered_compact:
        self._consecutive_compact_failures += 1
        logger.warning(
            "/compact 後 context 仍達 %.0f%%（連續失敗 %d 次）",
            compact_out.peak_token_pct, self._consecutive_compact_failures,
        )
        if self._consecutive_compact_failures >= 2:
            logger.error("=== Gap-008-E | 連續 compact 失敗 2 次，升級至 TOKEN_HALT ===")
            return False  # 讓呼叫方偵測並觸發 TOKEN_HALT
    else:
        self._consecutive_compact_failures = 0  # 成功則重置
    
    return not compact_out.triggered_compact
```

---

## Part V：終極優化藍圖 — Level 5 自治開發系統

### 5.1 Level 4.5 → Level 5 的本質差異

| 能力 | Level 4.5（現有）| Level 5（目標）|
|-----|----------------|--------------|
| 錯誤發散偵測 | exit_code（對 pytest 失效）| fail_count 趨勢 + 惡化率（Gap-008-A）|
| 語意測試分析 | SyntaxError 類（Gap-007-B）| AssertionError 基線不匹配（Gap-008-C）|
| History 管理 | 線性增長（Token 炸彈）| 去重 + 按頻率排序（Gap-008-B）|
| Minimax 品質 | 無驗證（接受任何輸出）| 相似度 + 具體引用檢驗（Gap-008-D）|
| Compact 容錯 | Warning 後繼續 | 連續失敗升級 TOKEN_HALT（Gap-008-E）|
| 自我診斷精度 | 4 個旗標（stuck/diverging/oscillating/suspect_test）| 6 個旗標（+worsening/assertion_mismatch）|

### 5.2 架構升級路線圖

```
當前 Level 4.5
    │
    ▼ Gap-008-A（1-2 天）
失敗數惡化偵測器
    │  - FailureTracker.is_worsening()
    │  - ConvergenceMonitor 優先級 3.5
    │  - EscalationDump.is_worsening 旗標
    │
    ▼ Gap-008-B（1 天）
History Summary 去重壓縮
    │  - build_history_summary() 去重版本
    │  - 按特徵碼頻率排序
    │  - 截斷至 max_unique_records=5
    │
    ▼ Gap-008-C（2-3 天）
語意測試錯誤偵測
    │  - FailureTracker.suspect_assertion_baseline_mismatch()
    │  - ConvergenceMonitor 優先級 1.5
    │  - prompt_builder._detect_assertion_test_error_hint()
    │  - EscalationDump.suspect_assertion_mismatch 旗標
    │
    ▼ Gap-008-D（1 天）
Minimax 幻覺防護
    │  - MinimaxClient._validate_correction_quality()
    │  - 高相似度自動觸發 change_strategy
    │
    ▼ Gap-008-E（0.5 天）
連續 compact 失敗升級
    │  - _consecutive_compact_failures 計數器
    │  - 連續 2 次失敗 → TOKEN_HALT
    │
    ▼
Level 5：圖靈完備的 Self-Healing Agentic Workflow
```

### 5.3 Level 5 核心設計原則

#### 原則 1：「不改比改壞更好」（Primum Non Nocere）

Level 5 系統在每次 CORRECTION 之後，應先問：「這次修正有沒有讓情況更糟？」
- Gap-008-A 的 `is_worsening()` 實現了這一原則
- 配合 `threshold_ratio=1.5x`，容忍小幅波動，對明顯惡化提前觸發 ESCALATION

#### 原則 2：「測試是合約，不是目標」

實作應該符合「正確的業務邏輯」，而不是「讓測試通過」。Level 5 系統必須能偵測「測試本身可能是錯的」：
- Gap-007-B 覆蓋語法層面
- Gap-008-C 覆蓋語意層面（AssertionError 無法收斂）

#### 原則 3：「壓縮資訊，不是遺忘資訊」

Context 壓縮（`/compact`）不應讓 Claude Code「忘記」歷史嘗試方向：
- Gap-007-F 的 Memory Anchor 保留當前任務關鍵資訊（已實作）
- Gap-008-B 的 history 去重確保 Minimax 收到的歷史是「有效密度最高的摘要」

#### 原則 4：「Minimax 的建議是假設，不是事實」

每次 Minimax 的 correction_prompt 都應被視為一個「假設」，系統應保留足夠的診斷能力來驗證這個假設是否正確：
- Gap-008-D 的品質驗證防止低品質假設被直接執行
- ConvergenceMonitor 的 worsening/oscillating 偵測在假設被驗偽後提前終止

### 5.4 Level 5 完整狀態機（升級後）

```
INIT
  ↓
CONTEXT_NEGOTIATION（可選）
  ↓
EXECUTE（送出 Prompt 給 Claude Code）
  ↓
TOKEN_COMPACT（context ≥ 80%）→ /compact + Memory Anchor
TOKEN_HALT（context ≥ 90%）→ 儲存 Checkpoint，排程恢復
CONTEXT_RESET（每 N 步）
  ↓
EVALUATE（regex + evaluator_command）
  ↓ 成功                ↓ 失敗
next step            ErrorClassifier（syntax/import/type/assertion/environment/timeout）
                        ↓
                     ConvergenceMonitor（評估收斂趨勢）
                     優先級：
                     0. ENVIRONMENT → ESCALATION（無法自動修復）
                     1. suspect_test_file（SyntaxError in test）→ ESCALATION
                     1.5. suspect_assertion_mismatch（Gap-008-C）→ ESCALATION（提示期望值可能錯）
                     2. is_stuck → change_strategy 或 ESCALATION
                     2.5. is_oscillating → ESCALATION
                     2.6. is_cycling → ESCALATION
                     3. is_diverging（exit_code）→ ESCALATION
                     3.5. is_worsening（Gap-008-A，fail count）→ ESCALATION
                     4. _is_count_improving → continue / change_strategy
                        ↓
                     CORRECTION（諮詢 Minimax）
                        ↓
                     Gap-008-D Hallucination Guard
                     （品質驗證，失敗則 change_strategy）
                        ↓
                     retry（回到 EXECUTE）
                        ↓ 超過 max_retries
                     ESCALATION → EscalationDump（6 個診斷旗標）→ 人工介入
DONE
  ↓
清除 Checkpoint，桌面通知
```

### 5.5 升級後的 EscalationDump 完整診斷旗標

```python
@dataclass
class EscalationDump:
    # 現有旗標
    is_stuck: bool                     # 特徵碼卡死
    is_diverging: bool                 # exit_code 遞增
    is_oscillating: bool               # ABAB 振盪
    suspect_test_file: bool            # 測試檔語法/import 問題
    
    # Gap-008 新增旗標
    is_worsening: bool = False         # 失敗數遞增（Minimax 越改越壞）
    suspect_assertion_mismatch: bool = False  # 測試期望值可能錯誤
    
    # 新增資訊
    changed_impl_files: list[str] = field(default_factory=list)  # git diff 修改的實作檔
    minimax_strategies_tried: list[str] = field(default_factory=list)  # 已嘗試的策略
```

### 5.6 人類接手速查表（Level 5 EscalationDump 強化版）

ESCALATION 後，人類看到的第一段資訊應包含：

```markdown
## 🤖 AutoClaude 自動診斷

| 症狀 | 狀態 | 建議行動 |
|-----|------|---------|
| 特徵碼卡死 | ✅ 是 | 查看 error_signature，根因在同一行 |
| 失敗數惡化 | ✅ 是 | Minimax 策略方向錯誤，檢查 failure_chain |
| 測試語法錯誤 | ❌ 否 | - |
| 測試期望值可疑 | ✅ 是 | **優先確認 assert 的期望值是否正確！** |

## 📁 被修改的實作檔案
- `src/compute.py` (最近 3 次 attempt 都修改了此檔)

## 🔄 已嘗試的策略
PINPOINT → REWRITE → ADD_TYPES（全部無效）

## ▶️ 確認後繼續執行
autoclaude scripts/playbook.yaml
```

---

## Part VI：實作優先順序建議

### P0（立即實作，解除最大 Risk）

| Gap | 工作量 | 影響 |
|-----|--------|------|
| **Gap-008-A** 失敗數惡化偵測 | 1-2 天 | 阻止 Minimax 幻覺修復無限循環 |
| **Gap-008-C** 語意測試錯誤 | 2-3 天 | 防止代碼庫被錯誤期望值污染 |

### P1（重要，解除 Token 炸彈）

| Gap | 工作量 | 影響 |
|-----|--------|------|
| **Gap-008-B** History 去重壓縮 | 1 天 | 降低 Minimax 輸入 Token 50%+ |

### P2（優化，提升系統健壯性）

| Gap | 工作量 | 影響 |
|-----|--------|------|
| **Gap-008-D** Minimax 幻覺防護 | 1 天 | 防止低品質修正被執行 |
| **Gap-008-E** 連續 compact 失敗升級 | 0.5 天 | 防止 80% context 附近無限循環 |

---

## Appendix：Gap 對照表（001-008 全覽）

| Gap 編號 | 核心問題 | 狀態 |
|---------|---------|------|
| Gap-006-A | CONTEXT_NEGOTIATION Token Guard | ✅ 已實作 |
| Gap-006-B | ConvergenceMonitor 統一收斂 | ✅ 已實作 |
| Gap-006-C | 測試檔錯誤跨行雙模式偵測 | ✅ 已實作 |
| Gap-006-D | compact 效果驗證 | ✅ 已實作 |
| Gap-006-E | correction_prompt 長度控制 | ✅ 已實作 |
| Gap-006-F | ConvergenceMonitor 振盪偵測 | ✅ 已實作 |
| Gap-007-A | FailureTracker checkpoint 序列化 | ✅ 已實作 |
| Gap-007-B | 測試檔語法快速路徑（py_compile）| ✅ 已實作 |
| Gap-007-C | git diff 檔案狀態快照 | ✅ 已實作 |
| Gap-007-D | 確定性策略輪換（PINPOINT/REWRITE/...）| ✅ 已實作 |
| Gap-007-E | 多模式實作檔錯誤偵測 | ✅ 已實作 |
| Gap-007-F | /compact Memory Anchor | ✅ 已實作 |
| **Gap-008-A** | **失敗數惡化偵測器（Worsening）** | ✅ 已實作 |
| **Gap-008-B** | **History Summary 去重壓縮** | ✅ 已實作 |
| **Gap-008-C** | **語意測試錯誤偵測（Assertion Mismatch）** | ✅ 已實作 |
| **Gap-008-D** | **Minimax Hallucination Guard** | ✅ 已實作 |
| **Gap-008-E** | **連續 compact 失敗升級 TOKEN_HALT** | ✅ 已實作 |

---

**文件元數據**:
- **建立日期**: 2026-05-01
- **分析者**: Claude（首席 AI 自動化架構師角色）
- **審閱狀態**: 待人工審閱
- **下一步**: 依 P0/P1/P2 優先順序實作 Gap-008-A ~ Gap-008-E
