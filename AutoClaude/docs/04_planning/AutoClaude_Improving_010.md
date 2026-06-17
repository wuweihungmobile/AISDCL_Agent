# AutoClaude_Improving_010
# Level 5 自治開發系統：深度剖析、弱點挖掘與終極升級藍圖

**文件版本**: v1.0  
**建立日期**: 2026-05-03  
**作者角色**: 首席 AI 自動化架構師（Chief AI Automation Architect）  
**分析基準**: AutoClaude Gap-001 ~ Gap-009 全量實作（截至 playbook_runner.py L1145）  
**適用 AISDLC 版本**: v0.09+

---

## 目錄

1. [系統現況深度評估](#1-系統現況深度評估)
2. [三大核心弱點推演](#2-三大核心弱點推演)
   - 2.1 [狀態流轉脆弱性：錯誤收斂度偵測的盲區](#21-狀態流轉脆弱性錯誤收斂度偵測的盲區)
   - 2.2 [上下文污染與衰減：/compact 是否足夠智慧？](#22-上下文污染與衰減compact-是否足夠智慧)
   - 2.3 [停機問題與防護：ESCALATION 的資訊密度不足](#23-停機問題與防護escalation-的資訊密度不足)
3. [自我驗證推演：pytest 測試檔語法錯誤案例](#3-自我驗證推演pytest-測試檔語法錯誤案例)
4. [Agentic 閉環升級策略](#4-agentic-閉環升級策略)
   - Gap-010-A: [語意錯誤預算管理器](#gap-010-a-語意錯誤預算管理器-semantic-error-budget-manager)
   - Gap-010-B: [漸進式上下文摘要壓縮](#gap-010-b-漸進式上下文摘要壓縮-progressive-context-summarization)
   - Gap-010-C: [跨步驟狀態污染偵測](#gap-010-c-跨步驟狀態污染偵測-cross-step-state-validator)
   - Gap-010-D: [EscalationDump 可執行復原計畫生成器](#gap-010-d-escalationdump-可執行復原計畫生成器)
   - Gap-010-E: [Playbook 自演化引擎](#gap-010-e-playbook-自演化引擎-playbook-self-evolution-engine)
   - Gap-010-F: [元學習修正策略優化器](#gap-010-f-元學習修正策略優化器-meta-learning-optimizer)
5. [Level 5 終極優化藍圖](#5-level-5-終極優化藍圖)
6. [實作優先級矩陣](#6-實作優先級矩陣)

---

<thinking>
## 架構師思考過程（Chain of Thought）

### Phase 1：閱讀完整程式碼後的初步心智模型

讀取 playbook_runner.py（1145 行）、convergence_monitor.py、failure_tracker.py、
error_classifier.py、pre_run_validator.py、minimax_client.py、prompt_builder.py、
knowledge_base.py 之後，系統的閉環結構已清晰：

```
EXECUTE → EVALUATE → [成功: 下一步] / [失敗: CORRECTION→Minimax]
                                      ↓
                              ConvergenceMonitor.evaluate()
                                      ↓
              ┌──────────────────────────────────────────────────────┐
              │ Priority 0: ENVIRONMENT → ESCALATE 立即              │
              │ Priority 1: suspect_test_file_error() → ESCALATE     │
              │ Priority 1.5: assertion_baseline_mismatch() → ESCALATE│
              │ Priority 2: is_stuck() [相同sig×2] → ESCALATE/STRATEGY│
              │ Priority 2.5: is_oscillating() [ABAB×4] → ESCALATE   │
              │ Priority 2.6: is_cycling() [ABC×6] → ESCALATE        │
              │ Priority 3: is_diverging() [exit_code遞增] → ESCALATE │
              │ Priority 3.5: is_worsening() [fail數遞增×3] → ESCALATE│
              │ Default: continue                                      │
              └──────────────────────────────────────────────────────┘
```

這個層疊優先級架構非常紮實。但我注意到幾個關鍵盲區。

### Phase 2：狀態流轉脆弱性深挖

**問題 1：策略輪換的「退出條件」缺陷**

`is_stuck(consecutive_threshold=2)` 觸發後，系統執行 `change_strategy`。
但此刻 `tracker.history` 已有 ≥2 筆相同 sig 記錄。
新策略執行後，如果產生「不同但同樣失敗」的 sig，則：
- `is_stuck()` = False（sig 不同了）
- `is_oscillating()` = False（只有 2 個不同 sig，但需要 ABAB×4）
- `is_cycling()` = False（需要 6 筆）
- ConvergenceMonitor 回傳 "continue" 

結果：系統以為「改善了」，繼續進行。但可能只是 Minimax 換了個錯誤方式而已。
實際上需要的是：策略輪換後的第一個 attempt，若同樣失敗，應該更快地升級評估。

**問題 2：is_stuck() 的 consecutive_threshold 太激進**

`is_stuck(threshold=2)` 代表「最近 2 次 sig 相同就 escalate」。
但在 max_retries=5 的情境下，2 次相同可能只是 Minimax 正在「定位問題」，
第 3 次修正才是真正有效的。這個門檻設得太嚴格，可能導致過早 ESCALATION。

實際上，系統會先嘗試 `change_strategy`（若 fail count improving），
然後才 escalate，所以有一層緩衝。但 `is_count_improving()` 需要有數字可比較。
若 eval_output 無法解析出 fail count（非 pytest 格式），則直接 escalate。

**問題 3：Hallucination Guard 的「不同但無效」幻覺**

`_validate_correction_quality()` 的三個條件：
1. 長度 >= 50 字
2. Jaccard 相似度 < 90%（與上次不同）
3. 包含具體錯誤引用（正則匹配）

條件 2 基於 Jaccard（詞彙集合交集），但 Minimax 可以輕易繞過：
只要換幾個同義詞（"modify" → "change"，"fix" → "repair"），
Jaccard 就會降到 90% 以下，但語意上幾乎相同。

真正需要的是：**語意去重（semantic deduplication）**，
而非詞彙集合去重。這需要 embedding 或更複雜的比較，
但至少可以用「修正目標的核心動詞+受詞」來做輕量比較。

### Phase 3：上下文污染深挖

**問題 4：/compact 後的「記憶錨點有效性」未驗證**

`_send_compact()` 發送帶有 MEMORY ANCHOR 的 /compact 指令：
```
=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===
[ACTIVE_TASK] T01: ...
[ATTEMPT] 3
[SUCCESS_CONDITION] ...
[LAST_FAILURE] ...
```

但系統從未驗證 compact 後 Claude Code 是否真的「記住」了這些 anchor。
實際上，Claude Code 的 /compact 實現是由其內部機制決定的，
並不保證 MEMORY ANCHOR 格式能被正確保留。

若 compact 後 Claude Code 忘記了目前任務背景，
下一個 correction_prompt 送入後，Claude Code 可能從頭開始，
而非繼續當前修正方向。

**問題 5：prompt_builder 的 task_prompt[:600] 重複注入**

每次 build_correction_message() 都注入 `task_prompt[:600]`。
在第 5 次 attempt 時，Minimax 的 user_message 包含：
- task_prompt[:600]（每次相同，浪費 token）
- file_snapshot（每次更新，有價值）
- key_lines_text（每次更新，有價值）  
- history_summary（每次更新，有價值）

累積到第 5 次，user_message 已相當龐大。
對 Minimax 的 API 費用和回應速度都有影響。

**解法**：`task_prompt` 在第 2 次後可以縮減為「目標摘要」（前 100 字 + 目標陳述）。

### Phase 4：停機問題深挖

**問題 6：EscalationDump 的「可執行性缺口」**

目前 EscalationDump 包含：
```python
is_stuck, is_diverging, suspect_test_file, is_oscillating, is_worsening
suspect_assertion_mismatch, human_hint, last_log_path, checkpoint_resume_hint
```

但它告訴人類「發生了什麼」，卻不告訴人類「應該做什麼」。
一個好的 EscalationDump 應該包含**可執行的 shell 命令清單**，例如：

```bash
# 如果是 suspect_test_file = True
python -m py_compile tests/test_foo.py
# 如果是 assertion_baseline_mismatch = True
grep -n "assert.*==" tests/test_foo.py | head -20
# 如果是 is_stuck = True (相同 sig)
git log --oneline -10  # 確認 Claude 最近的修改
git diff HEAD~5 HEAD   # 查看所有變更
```

**問題 7：knowledge_base 的「衰減機制缺失」**

`FailureKnowledgeBase` 的 `_MAX_ENTRIES=1000` 以 LRU-style 清除最舊的 key。
但「最舊的」不等於「最沒用的」。某些 error_sig 可能：
- 6 個月前遇到過，當時的修復策略今天已無效（程式碼已大幅重構）
- 頻繁出現但從未成功（只記錄了 escalation 的 skip_strategies）

缺少 TTL（Time-To-Live）機制和置信度衰減。

### Phase 5：Level 5 差距評估

Level 5 定義：「系統能根據總目標，自行演化修正執行步驟」

目前系統的能力等級：
- Level 1: 固定步驟循序執行 ✅
- Level 2: 失敗重試 ✅
- Level 3: 智慧修正（Minimax CORRECTION 閉環）✅
- Level 4: 收斂偵測 + 自動 ESCALATION ✅
- Level 4.5: 跨 Session 知識庫 + 預驗證 + 動態 Token 管理 ✅
- Level 5: **Playbook 自演化**（根據執行結果動態修改步驟）❌

**Level 5 的核心缺失**：
當一個 step 的 ESCALATION 原因是「步驟設計本身有問題」
（例如：T02 要求「直接寫實作」，但發現需要先做 T01.5「設計介面」），
系統無法識別這是「步驟結構問題」而非「實作問題」，
也無法自動在 Playbook 中插入中間步驟並繼續。
</thinking>

---

## 1. 系統現況深度評估

### 1.1 架構層次評分（Level 1–5）

| 能力層次 | 描述 | 現況 |
|---------|------|------|
| **Level 1** | 固定步驟循序執行 | ✅ 完整實作 |
| **Level 2** | 失敗重試（max_retries） | ✅ 完整實作 |
| **Level 3** | 智慧修正（Minimax CORRECTION 閉環） | ✅ 完整實作 |
| **Level 4** | 收斂偵測 + ConvergenceMonitor + ESCALATION | ✅ 完整實作 |
| **Level 4.5** | 跨 Session 知識庫 + 預驗證 + 動態 Token 管理 | ✅ Gap-007~009 已實作 |
| **Level 5** | **Playbook 自演化**（根據執行結果動態修改步驟結構） | ❌ 尚未實作 |

目前系統已是市面上最先進的 Agentic Workflow 引擎之一（Level 4.8），
具備以下 Level 4.8 特徵（截至 Gap-009）：

```
PreRunValidator(Gap-009-B)
      ↓
EXECUTE(attempt N)
      ↓
EVALUATE ─── regex + evaluator_command
      ↓失敗
ErrorClassifier.classify()
      ↓
FailureTracker.record() → error_signature（ANSI strip + 路徑正規化）
      ↓
ConvergenceMonitor.evaluate() [8個優先級判斷]
      ↓
 ESCALATE?  ─→ EscalationDump + KnowledgeBase.record_escalation()
 CHANGE?    ─→ tracker.next_strategy() [確定性策略輪換]
 CONTINUE?  ─→ KnowledgeBase.query() [歷史知識加速]
      ↓
_fast_path_test_file_check() [Gap-007-B]
      ↓
Minimax CORRECTION [+Hallucination Guard Gap-008-D]
      ↓
_verify_correction_applied() [Gap-009-C git diff]
      ↓
回到 EXECUTE(attempt N+1)
```

### 1.2 已識別的系統強項

1. **多層收斂偵測**（8 種模式）：environment / test_file_suspect / assertion_baseline /
   stuck / oscillating / cycling / diverging / worsening
2. **錯誤語意分類**（ErrorClassifier）：7 種 ErrorClass，驅動差異化策略
3. **跨 Session 知識庫**（FailureKnowledgeBase）：JSONL 格式，error_sig → 有效策略映射
4. **確定性策略輪換**（FailureTracker.next_strategy）：PINPOINT→REWRITE→ADD_TYPES→SPLIT→SIMPLIFY
5. **Token 動態門檻**（Gap-009-F）：`base - (attempt/max_retries) × 15`，下限 65%
6. **Hallucination Guard**（Gap-008-D）：長度/相似度/具體引用三維驗證
7. **Pre-Run 攔截**（Gap-009-B）：在首次 attempt 前攔截「必然失敗」情況

---

## 2. 三大核心弱點推演

### 2.1 狀態流轉脆弱性：錯誤收斂度偵測的盲區

#### 弱點 A：策略輪換後的「偽改善假陽性」

**觸發場景**：

```
attempt 0: sig="SyntaxError line N in foo.py" → is_stuck=False, CORRECTION(PINPOINT)
attempt 1: sig="SyntaxError line N in foo.py" → is_stuck=True!
   → change_strategy → REWRITE 策略
attempt 2: sig="NameError bar undefined"      → is_stuck=False
   → ConvergenceMonitor: "繼續" (fail count=None, 無趨勢資料)
attempt 3: sig="NameError bar undefined"      → is_stuck=True!
   → change_strategy → ADD_TYPES 策略
attempt 4: sig="NameError bar undefined"      → is_stuck=True!
   → ESCALATE（fail count 沒有 improving）
```

問題：在 attempt 2 時，系統以為「改善了」（SyntaxError 消失），
但實際上只是 REWRITE 策略引入了新的 NameError。
有效修復本應要求原始 SyntaxError 消失**且**新 step 成功。
目前的系統無法區分「真正的前進」和「換了個問題」。

**建議修正**：`ConvergenceMonitor.evaluate()` 新增 **error_class 跨 attempt 一致性檢查**：
若最近 N 次 error_class 持續切換（syntax→name→type→syntax），
這是 Minimax 策略互相干擾的信號，應觸發 `change_strategy` 而非 `continue`。

#### 弱點 B：Hallucination Guard 的 Jaccard 盲點

`_rough_similarity()` 基於詞彙集合的 Jaccard 相似度，容易被「同義詞替換」繞過：

```python
上次: "在 foo.py 第 42 行修正 SyntaxError，補上缺失的冒號"
這次: "在 foo.py 第 42 行改正 SyntaxError，加入遺失的冒號"  # Jaccard ≈ 0.65 → 通過！
```

語意幾乎相同，但 Jaccard 計算結果遠低於 0.90 門檻，Hallucination Guard 視為有效。

**建議修正**：改用「核心動詞+受詞+位置」的結構化比較，
提取 `(action, target_file, target_element)` 三元組，
若三元組相同則視為語意重複。

#### 弱點 C：max_retries 與 ConvergenceMonitor 的競速條件

`is_stuck(threshold=2)` 至少需要 2 次失敗才偵測。
若 `max_retries=2`，則序列為：
```
attempt 0: 失敗 → tracker[1筆] → monitor.continue → CORRECTION
attempt 1: 失敗 → tracker[2筆] → monitor.stuck!
   if count_improving: change_strategy (但已是最後一次重試)
   attempt >= max_retries: ESCALATION
```
此時 `change_strategy` 的決策永遠無法被執行，
因為 `attempt >= max_retries` 的判斷在 `monitor.evaluate()` 之後。
等於 `max_retries=2` 時 ConvergenceMonitor 的 `change_strategy` 路徑是死代碼。

**建議修正**：`change_strategy` 觸發時，應允許額外一次 `grace_attempt`，
不計入 `max_retries` 配額（但全域有上限以防止無限延伸）。

### 2.2 上下文污染與衰減：/compact 是否足夠智慧？

#### 弱點 D：MEMORY ANCHOR 有效性未驗證

`_send_compact()` 發送結構化記憶錨點：
```
=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===
[ACTIVE_TASK] T01: 實作認證模組
[ATTEMPT] 3
[SUCCESS_CONDITION] output must match: \\[DONE\\]
[LAST_FAILURE] AssertionError: 3 failed
=== END ANCHOR ===
```

但系統從未驗證 compact 後 Claude Code 是否真的保留了這些資訊。
`_send_compact()` 只檢查 compact 後 `peak_token_pct` 是否下降
（Gap-008-E 的 `consecutive_compact_failures` 機制），
並未驗證 Claude Code 的「記憶品質」。

**後果**：在高重試次數的 correction 迴圈中觸發 compact 後，
Claude Code 可能忘記「目前正在修正 test_foo.py 的 SyntaxError」，
下一個 correction_prompt 被它解讀為全新任務，
導致大範圍重寫而非精準修正。

**建議修正**：compact 後立即發送一個「記憶驗證探針（Memory Probe）」，
要求 Claude Code 複述當前任務目標，
若回應不符則補發完整背景再繼續。

#### 弱點 E：高重試時 Minimax User Message 的 Token 膨脹

`build_correction_message()` 在每次 CORRECTION 都注入 `task_prompt[:600]`。
在 attempt 5 時，完整 user_message 結構如下：

```
task_prompt[:600]          → 600 字（每次相同，70% 是重複內容）
file_snapshot              → 200 字（有價值，每次更新）
failure_reason             → 100 字
key_lines_text             → 400 字（20 行 × 20 字/行）
test_file_hint             → 100 字
assertion_hint             → 150 字
error_class_hint           → 100 字
history_summary            → 500 字（5 個去重 sig × 100 字）
context_hint               → 100 字
strategy_section           → 50 字
retry_count                → 20 字
```
**合計 ~2320 字**，第 5 次 attempt 與第 1 次幾乎相同，
但 `task_prompt[:600]` 從未縮減。

**建議修正**：第 3 次 attempt 後，`task_prompt` 縮減為 `task_prompt[:100]`
並附加一行目標摘要（由 Minimax 在第 1 次 correction 時順帶生成）。

#### 弱點 F：Error Summarization 的「模式遺忘」

`build_history_summary()` 提供去重後的 error_sig 列表，這是良好設計。
但它的壓縮只是「去重計數」，不是「模式描述」：

```
目前輸出：sig=SyntaxError line N in foo.py（已出現 3 次）
目標輸出：Minimax 連續 3 次嘗試修正 foo.py:42，均失敗。
          嘗試策略：PINPOINT→REWRITE。問題根因可能在於 foo.py 整個函式的邏輯設計，
          而非單一語法位置。
```

後者是「診斷摘要」，前者是「原始數據」。
Minimax 作為修正大腦，從「診斷摘要」生成的 correction_prompt 品質更高。

### 2.3 停機問題與防護：ESCALATION 的資訊密度不足

#### 弱點 G：EscalationDump 是診斷報告，不是行動計畫

目前 EscalationDump 的 `human_hint` 欄位是自由文字，
例如：`"收斂評估（trend=stuck）：特徵碼連續相同且無數量改善"`

這告訴人類「發生了什麼」，但不告訴人類「應該執行哪些指令來診斷和修復」。
一個工程師接手時，需要自行判斷：

1. 應該先 `git log` 看 Claude 的修改？
2. 還是先 `py_compile` 驗證測試檔？
3. 還是先讀 `failure_chain` 找規律？

**建議修正**：`EscalationDump.save()` 根據 `is_stuck / suspect_test_file / ...`
自動生成「接手行動清單（Handover Action Checklist）」，
每個行動項目包含可直接執行的 shell 命令。

#### 弱點 H：FailureKnowledgeBase 的 TTL 與置信度缺失

`FailureKnowledgeBase` 以 `error_sig` 為 key，
但 error_sig 的有效性會隨著程式碼演化而降低：

- 半年前記錄的 `"SyntaxError:foo.py"` → 有效策略是 REWRITE
- 今天 foo.py 已被完全重寫，REWRITE 可能不再適用
- 但知識庫仍會優先推薦 REWRITE，而非從零評估

缺少 TTL（Time-To-Live）衰減機制，導致陳舊知識可能誤導系統。

---

## 3. 自我驗證推演：pytest 測試檔語法錯誤案例

**場景設定**：

```yaml
tasks:
  - step_id: "T03"
    name: "實作認證模組"
    prompt: "請實作 src/auth.py 的 JWT 驗證邏輯..."
    evaluator_command: "pytest tests/test_auth.py -v"
```

`tests/test_auth.py` 第 15 行有語法錯誤（人類寫錯的 `def test_login(` 缺閉括號）。

**完整推演流程**：

```
Step 1: PreRunValidator (Gap-009-B)
─────────────────────────────────
  validate_step("pytest tests/test_auth.py -v", task.prompt)
    ├─ _check_evaluator_command("pytest") → pytest 在 PATH ✅
    └─ _check_test_file_syntax("pytest tests/test_auth.py -v")
         → 萃取 tests/test_auth.py
         → py_compile tests/test_auth.py → returncode=1
         → 回傳 PreRunIssue(severity="block", category="test_syntax")
                          strategy_hint="🚫 Pre-Run 硬性約束：..."

  block_issues = [PreRunIssue(...)]
  _pre_run_hint = "🚫 Pre-Run 硬性約束：修復 tests/test_auth.py 語法..."
```

```
Step 2: attempt=0，注入 Pre-Run 約束
──────────────────────────────────────
  prompt_to_send = _pre_run_hint + "\n---\n" + task.prompt[:1000]
  # Claude Code 被告知：先修復 test_auth.py 語法，再做實作

  _pre_run_hint = None  # 只注入一次

  → 執行 EXECUTE(prompt_to_send)
```

```
Case A：Claude Code 成功修復語法並實作
─────────────────────────────────────
  pytest tests/test_auth.py → 通過
  failure_reason = None → 步驟成功 ✅
```

```
Case B：Claude Code 無視 Pre-Run 約束，直接實作 auth.py
──────────────────────────────────────────────────────────
  pytest tests/test_auth.py → 
    FAILED tests/test_auth.py - SyntaxError: unexpected EOF

  failure_reason = "評估指令失敗 (exit=1): pytest tests/test_auth.py"
  eval_output = "ERROR collecting tests/test_auth.py\n  SyntaxError: ..."

  error_cls = ErrorClassifier.classify(eval_output, 1)
    → SYNTAX（偵測到 SyntaxError）
  
  tracker.record(0, ..., error_class="syntax")  # 1 筆歷史

  report = monitor.evaluate(tracker)
    → history = 1 筆 → suspect_test_file_error() 需要 >= 2 筆 → False
    → is_stuck() 需要 >= 2 筆 → False
    → 結論：recommendation="continue"

  # 現在進入 CORRECTION
  _fast_path_test_file_check(eval_output):  ← 這是 Gap-007-B 的關鍵
    pattern matches: "ERROR collecting tests/test_auth.py"
    subprocess.run(["python", "-m", "py_compile", "tests/test_auth.py"])
    → returncode=1 ✓ 確認測試檔語法錯誤
    → 回傳 strategy_hint = "🚫 硬性約束：tests/test_auth.py 語法錯誤..."
  
  Minimax.decide_correction(..., strategy_hint="🚫 硬性約束：修復測試檔...")
    → correction_prompt 必須包含「修復測試檔語法」的指令
  
  attempt=1: 執行 correction（應修復 test_auth.py）
```

```
Case B.1：attempt 1 成功修復測試檔 → 測試通過 ✅
Case B.2：attempt 1 仍未修復（Claude Code 又改了 auth.py 而非 test_auth.py）
──────────────────────────────────────────────────────────────────────────────
  pytest → 仍然 SyntaxError in test_auth.py
  
  tracker.record(1, ...)  # 2 筆歷史

  report = monitor.evaluate(tracker)
    → suspect_test_file_error() 現在有 2 筆！
      → 每筆都有 "test_auth.py" + "SyntaxError"
      → 每筆都沒有 impl_error（auth.py 不在 error output 中）
      → 回傳 True
    → recommendation = "escalate"
    → reasoning = "錯誤始終指向測試檔，修改實作無效"
  
  ★ 關鍵時刻：ConvergenceMonitor 成功識別！
  
  → ESCALATION 觸發
  → EscalationDump 包含 suspect_test_file=True
  → human_hint = "收斂評估（trend=diverging）：錯誤始終指向測試檔，修改實作無效"
  → 桌面通知 + escalation_alert.log
```

**結論**：系統在 **2 次 attempt 後**（attempt 0 + attempt 1）成功識別並優雅停止，
未浪費 Token 在修改實作檔上。這是正確的行為！

**但存在邊界案例（Gaps）**：

1. 如果 `test_auth.py` 路徑包含非 ASCII 字元或 Windows 絕對路徑 `C:\...\test_auth.py`，
   `_fast_path_test_file_check` 的正則可能無法匹配，導致 `strategy_hint=None`，
   Minimax 收不到「修測試檔」的約束，可能生成錯誤方向的 correction。

2. 如果測試檔路徑不是 `test_*.py` 格式（如 `tests/auth_test.py`），
   `suspect_test_file_error()` 的所有正則都會失效，
   系統會把它當作「實作檔錯誤」去修，永遠無法收斂。

3. 如果 Claude Code 在 attempt 1 **同時修了** test_auth.py（修錯方向）和 auth.py，
   eval_output 中會同時出現 `test_auth.py` 錯誤和 `auth.py` 的 impl_error。
   此時 `suspect_test_file_error()` 因為 `_has_impl_error()` 回傳 True 而返回 False，
   正確的「修測試檔」方向被遮蔽。

---

## 4. Agentic 閉環升級策略

### Gap-010-A: 語意錯誤預算管理器 (Semantic Error Budget Manager)

**問題**：固定的 `max_retries` 忽視錯誤類型的差異。
`SyntaxError` 理論上 1 次就能修好；`AssertionError` 可能需要 5 次理解語意。

**設計模式**：

```python
# autoclaude/execution/error_budget.py
from dataclasses import dataclass

@dataclass
class ErrorBudget:
    """Per-error-class retry budgets with immediate-escalation classes."""
    
    BUDGETS: dict[str, int] = {
        "environment": 0,    # 環境錯誤：立即 ESCALATE（已由 ConvergenceMonitor 處理）
        "syntax":      2,    # 語法錯誤：2 次修正（低複雜度）
        "import":      2,    # 依賴問題：2 次（改 import 或裝套件）
        "type":        3,    # 型別錯誤：3 次（需理解函式簽名）
        "assertion":   5,    # 斷言失敗：5 次（需理解業務語意）
        "timeout":     1,    # 超時：1 次（需要效能優化）
        "unknown":     3,    # 未知：預設 3 次
    }
    
    def effective_max_retries(
        self,
        global_max: int,
        current_error_class: str,
        attempt: int,
    ) -> int:
        """
        返回當前錯誤類型的有效重試上限。
        若 global_max 更嚴格，以 global_max 為準。
        若錯誤類型在 attempt N 才首次出現，預算從當前 attempt 開始計。
        """
        class_budget = self.BUDGETS.get(current_error_class, global_max)
        return min(global_max, attempt + class_budget)
```

**整合到 PlaybookRunner**：

```python
# 在 _run_steps() 的 CORRECTION 前：
budget = ErrorBudget()
effective_limit = budget.effective_max_retries(
    max_retries, error_cls.value, attempt
)
if attempt >= effective_limit:
    # 提前 ESCALATION（比 max_retries 更快）
    ...
```

**效益**：
- SyntaxError 不再浪費 5 次 Token 才發現無解
- AssertionError 給足 5 次讓 Minimax 理解語意
- EnvironmentError 立即 ESCALATE（與 ConvergenceMonitor 一致，雙重保障）

---

### Gap-010-B: 漸進式上下文摘要壓縮 (Progressive Context Summarization)

**問題**：`task_prompt[:600]` 每次重複注入 Minimax，高重試時浪費 Token。

**設計模式**：

```python
# autoclaude/decision/prompt_builder.py 修改

def build_correction_message(
    ...,
    retry_count: int,
    task_goal_summary: Optional[str] = None,  # 新增：第 1 次 correction 後由 Minimax 生成
) -> str:
    
    if retry_count >= 3 and task_goal_summary:
        # 高重試：改用摘要，節省約 500 字
        task_context = f"## 任務目標（摘要）\n{task_goal_summary}\n\n"
    else:
        # 前 2 次：完整 task_prompt 保持精確性
        task_context = f"## 原始 Prompt（前 600 字）\n{task_prompt[:600]}\n\n"
    
    return (
        f"## 失敗步驟\n{step_id}: {task_name}\n\n"
        f"{task_context}"
        ...
    )
```

**同時需要新增**：`CorrectionDecision` 模型支援 `task_goal_summary` 欄位，
在第 1 次 correction 時由 Minimax 順帶生成（30 字以內的任務目標陳述）。

**壓縮率估算**：
- attempt 3+：`task_prompt[:600]` → `task_goal_summary[:80]`，每次節省 ~520 字
- 5 次重試累計節省：520 × 3 = 1560 字 → 約 2-3 次額外的 Minimax API 成本節省

---

### Gap-010-C: 跨步驟狀態污染偵測 (Cross-Step State Validator)

**問題**：步驟 T(N+1) 失敗時，可能是因為 T(N) 的 ESCALATION/CORRECTION
留下了破損的中間狀態（例如：T(N) 修改了 `config.py` 但只改了一半就 ESCALATE）。

**設計模式**：

```python
# autoclaude/execution/cross_step_validator.py

class CrossStepStateValidator:
    """
    在每個 step EXECUTE 前，驗證前一步驟的輸出產物是否符合預期狀態。
    使用 git status + 預定義的 step_output_signatures 做快速驗證。
    """
    
    def validate_before_step(
        self,
        current_step: PlaybookTask,
        prev_step: Optional[PlaybookTask],
        working_dir: str = ".",
    ) -> Optional[str]:  # 回傳警告 hint 或 None
        """
        若偵測到跨步驟污染，回傳注入到 prompt 的警告文字。
        """
        # 1. 檢查 git status（是否有未完成的 staged 變更）
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=working_dir,
        )
        staged_count = len([l for l in result.stdout.splitlines() if l.startswith("M")])
        
        if staged_count > 5:
            return (
                f"⚠️ 跨步驟污染警告：偵測到 {staged_count} 個未確認的修改（git status）。"
                f"前一步驟 [{prev_step.step_id if prev_step else '?'}] "
                f"可能未完成清理。建議先確認這些修改是預期的，再繼續實作。"
            )
        return None
```

---

### Gap-010-D: EscalationDump 可執行復原計畫生成器

**問題**：EscalationDump 是診斷報告，人類接手後需要自行判斷執行什麼命令。

**設計模式**：

```python
# autoclaude/models/escalation.py 修改

@dataclass 
class EscalationDump:
    ...
    
    def generate_handover_checklist(self) -> list[str]:
        """
        根據 ESCALATION 原因，自動生成可執行的接手行動清單。
        """
        actions = []
        
        # 1. 通用：查看最近的 Git 變更
        actions.append("# 1. 確認 Claude Code 最近的修改")
        actions.append(f"git log --oneline -10")
        actions.append(f"git diff HEAD~{min(self.total_attempts, 5)} HEAD")
        
        if self.suspect_test_file:
            # 偵測到測試檔問題
            actions.extend([
                "",
                "# 2. 測試檔語法驗證（suspect_test_file=True）",
                f"python -m py_compile tests/test_*.py",
                f"# 或指定檔案：python -m py_compile <test_file>",
                "pytest --collect-only  # 確認所有測試可被收集",
            ])
        
        if self.is_stuck:
            actions.extend([
                "",
                "# 3. 卡死診斷（is_stuck=True，相同錯誤反覆出現）",
                f"# 最後一次 eval 輸出：{self.last_log_path}",
                f"cat {self.last_log_path} | tail -50",
                "# 手動嘗試：直接在終端執行 evaluator_command",
            ])
        
        if self.suspect_assertion_mismatch:
            actions.extend([
                "",
                "# 4. 測試期望值驗證（assertion_baseline_mismatch=True）",
                "# 高度懷疑測試中的 assert 期望值有誤",
                f"grep -n 'assert.*==' tests/  -r | head -20",
                "# 請人工確認：assert 的期望值是否符合業務邏輯",
            ])
        
        if self.is_worsening:
            actions.extend([
                "",
                "# 5. 失敗數遞增診斷（is_worsening=True，Minimax 使情況惡化）",
                "# 建議：放棄 Claude Code，手動重置所有修改",
                "git checkout HEAD -- .",  # 危險操作，但此時已 ESCALATE
                f"# 然後手動修正：{self.step_id} 的實作",
            ])
        
        # 最後：恢復指令
        actions.extend([
            "",
            "# 6. 手動修正後，恢復執行",
            f"autoclaude {self.playbook_path}  # 從 checkpoint 繼續",
            f"# 或跳過此步驟（如果已手動完成）：",
            f"autoclaude {self.playbook_path} --skip-step {self.step_id}",
        ])
        
        return actions
    
    def save(self, checkpoint_dir: str) -> Path:
        ...
        # 在 Markdown 末尾追加接手行動清單
        content += "\n## 接手行動清單（可直接執行）\n\n"
        content += "```bash\n"
        content += "\n".join(self.generate_handover_checklist())
        content += "\n```\n"
        ...
```

---

### Gap-010-E: Playbook 自演化引擎 (Playbook Self-Evolution Engine)

**這是通往 Level 5 的核心架構**。

**問題**：當 ESCALATION 的根因是「步驟設計本身有問題」時，
系統無法識別，更無法自動演化 Playbook 步驟結構。

**Level 5 設計**：

```python
# autoclaude/evolution/playbook_evolver.py

class PlaybookEvolver:
    """
    Level 5 核心：根據 ESCALATION 分析，提議 Playbook 步驟修改。
    
    演化觸發條件：
    1. 連續 2 個步驟都 ESCALATION（可能是步驟依賴問題）
    2. suspect_test_file 且 PreRunValidator 未能在啟動時攔截
       （測試檔是在執行過程中被創建的）
    3. assertion_baseline_mismatch 且 total_attempts >= 4
       （測試期望值可能需要重新設計）
    
    演化類型：
    - INJECT_STEP: 在當前步驟前注入一個新的「準備步驟」
    - SPLIT_STEP: 將當前步驟拆為 2 個更小的步驟
    - REORDER_STEP: 建議調換步驟順序
    - REVISE_EVALUATOR: 建議修改 evaluator_command
    """
    
    def __init__(self, minimax_client: MinimaxClient):
        self._minimax = minimax_client
    
    def propose_evolution(
        self,
        playbook: Playbook,
        failed_step_idx: int,
        escalation_dump: EscalationDump,
        escalation_history: list[EscalationDump],  # 所有步驟的歷史 ESCALATION
    ) -> Optional[PlaybookEvolutionProposal]:
        """
        分析失敗模式，提議 Playbook 演化方案。
        回傳 None 表示無法自動演化，需人工介入。
        """
        dump = escalation_dump
        
        # Case 1: 測試檔本身設計有問題 → 注入「修復測試檔」步驟
        if dump.suspect_test_file or dump.suspect_assertion_mismatch:
            return PlaybookEvolutionProposal(
                evolution_type="INJECT_STEP",
                inject_before_idx=failed_step_idx,
                new_step=PlaybookTask(
                    step_id=f"{dump.step_id}_PRE",
                    name=f"修復 {dump.step_id} 的測試檔問題",
                    prompt=(
                        f"步驟 {dump.step_id} 的測試發現問題。"
                        f"請先診斷並修復測試檔：\n"
                        f"{dump.human_hint}\n\n"
                        f"修復完成後，確認測試可以被 pytest 收集（pytest --collect-only）。"
                    ),
                    evaluator_command="pytest --collect-only",
                    expected_output_regex=r"selected",
                    max_retries=2,
                ),
                reasoning="測試檔本身有問題，注入前置修復步驟",
            )
        
        # Case 2: 步驟卡死且多種策略無效 → 詢問 Minimax 建議步驟拆分
        if dump.is_stuck and len(escalation_dump.failure_chain) >= 3:
            evolution_prompt = self._build_evolution_prompt(playbook, failed_step_idx, dump)
            try:
                proposal = self._minimax.propose_step_evolution(evolution_prompt)
                return proposal
            except MinimaxError:
                return None
        
        return None
    
    def apply_evolution(
        self,
        playbook: Playbook,
        proposal: PlaybookEvolutionProposal,
        playbook_path: str,
    ) -> str:
        """
        將演化提議應用到 Playbook，寫入 evolved_{原檔名}.yaml。
        回傳新的 Playbook 路徑。
        """
        tasks = list(playbook.tasks)
        
        if proposal.evolution_type == "INJECT_STEP":
            tasks.insert(proposal.inject_before_idx, proposal.new_step)
        elif proposal.evolution_type == "SPLIT_STEP":
            idx = proposal.inject_before_idx
            tasks[idx:idx+1] = proposal.split_steps
        
        evolved = Playbook(
            version=playbook.version,
            project=f"{playbook.project} [EVOLVED]",
            workflow_type=playbook.workflow_type,
            global_invariants=playbook.global_invariants,
            tasks=tasks,
        )
        
        evolved_path = Path(playbook_path).parent / f"evolved_{Path(playbook_path).name}"
        with evolved_path.open("w", encoding="utf-8") as f:
            yaml.dump(evolved.model_dump(), f, allow_unicode=True)
        
        logger.info("Level 5: Playbook 演化版本已寫入 %s", evolved_path)
        return str(evolved_path)
```

**PlaybookRunner 整合點**：

```python
# 在 _run_steps() 的 ESCALATION 判斷後：

if report.recommendation == "escalate":
    self._save_escalation_dump(...)
    
    # Level 5: 嘗試自動演化
    if self._cfg.evolution.enabled:  # 新配置項
        proposal = self._evolver.propose_evolution(
            playbook, step_idx, dump, self._escalation_history
        )
        if proposal:
            evolved_path = self._evolver.apply_evolution(
                playbook, proposal, playbook_path
            )
            self._notify(
                "AutoClaude — Playbook 自動演化",
                f"已生成演化版本：{evolved_path}\n"
                f"演化原因：{proposal.reasoning}\n"
                f"請確認後執行：autoclaude {evolved_path}"
            )
    
    return PlaybookResult(...)
```

---

### Gap-010-F: 元學習修正策略優化器 (Meta-Learning Optimizer)

**問題**：`FailureKnowledgeBase` 記錄「哪個策略成功過」，
但不記錄「在哪種 error_class 下哪個策略最有效」，
導致 `next_strategy()` 的輪換順序對所有錯誤類型都相同（PINPOINT→REWRITE→...）。

**設計模式**：

```python
# autoclaude/utils/knowledge_base.py 擴充

class FailureKnowledgeBase:
    
    def get_strategy_priority(self, error_class: str) -> list[str]:
        """
        根據歷史數據，返回針對特定 error_class 的策略優先順序。
        若無足夠數據，回傳預設順序。
        """
        strategy_stats = {}
        for entry in self._cache.values():
            if entry.get("outcome") == "success":
                ec = entry.get("error_class", "unknown")
                strat = entry.get("successful_strategy", "")
                if ec == error_class and strat:
                    strategy_stats[strat] = strategy_stats.get(strat, 0) + 1
        
        if len(strategy_stats) < 3:  # 數據不足
            return list(STRATEGY_TYPES)  # 預設順序
        
        # 按歷史成功次數排序
        return sorted(STRATEGY_TYPES, key=lambda s: strategy_stats.get(s, 0), reverse=True)
    
    def record_success(
        self, error_signature: str, successful_strategy: str, step_id: str,
        error_class: str = "unknown",  # 新增：記錄 error_class
    ) -> None:
        key = error_signature[:80]
        entry = {
            "error_sig": key,
            "successful_strategy": successful_strategy,
            "error_class": error_class,   # 新增
            "step_id": step_id,
            "timestamp": time.time(),
            "outcome": "success",
        }
        ...
```

**FailureTracker 整合**：

```python
# FailureTracker.next_strategy() 改為接受 KB 建議

def next_strategy(self, kb: Optional[FailureKnowledgeBase] = None,
                  current_error_class: str = "unknown") -> str:
    if kb:
        priority_order = kb.get_strategy_priority(current_error_class)
        for s in priority_order:
            if s not in self._tried_strategies:
                self._tried_strategies.add(s)
                return s
    # 原有邏輯兜底
    for s in STRATEGY_TYPES:
        if s not in self._tried_strategies:
            ...
```

---

## 5. Level 5 終極優化藍圖

### 5.1 Level 5 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    Level 5 AutoClaude                       │
│                                                             │
│  總目標（Playbook.goal_statement）                           │
│       ↓                                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        PlaybookEvolver (新增)                        │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │  當前 Playbook                                │  │   │
│  │  │  [T01][T02][T03][T04]                        │  │   │
│  │  └─────────────┬─────────────────────────────────┘  │   │
│  │                │ ESCALATION 觸發                      │   │
│  │                ↓                                     │   │
│  │  分析失敗原因 (EscalationDump)                        │   │
│  │      ↓ suspect_test_file → INJECT_STEP              │   │
│  │      ↓ is_stuck × 策略耗盡 → SPLIT_STEP             │   │
│  │      ↓ assertion_mismatch → REVISE_EVALUATOR        │   │
│  │  生成 evolved_playbook.yaml                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  PlaybookRunner 狀態機（Level 4.8 基礎 + 演化整合）          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ INIT → EXECUTE → EVALUATE                           │   │
│  │                     │                               │   │
│  │              成功 → 下一步                           │   │
│  │                     │失敗                           │   │
│  │    ErrorClassifier + ErrorBudget(Gap-010-A)         │   │
│  │                     ↓                               │   │
│  │    FailureTracker + MetaLearningOptimizer(Gap-010-F)│   │
│  │                     ↓                               │   │
│  │    ConvergenceMonitor（8個優先級）                   │   │
│  │        ↓ continue                                   │   │
│  │    CrossStepStateValidator(Gap-010-C)                │   │
│  │        ↓                                            │   │
│  │    ProgressiveSummarizer(Gap-010-B)                  │   │
│  │        ↓                                            │   │
│  │    Minimax CORRECTION + Hallucination Guard         │   │
│  │        ↓ escalate                                   │   │
│  │    EscalationDump + ActionChecklist(Gap-010-D)       │   │
│  │        ↓                                            │   │
│  │    PlaybookEvolver(Gap-010-E) → evolved_playbook    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  知識層（持久化學習）                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FailureKnowledgeBase                               │   │
│  │  error_sig → {strategy, error_class, TTL, confidence}│   │
│  │  + Meta-Learning: error_class → strategy_priority   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Level 5 關鍵邊界案例防護矩陣

| 邊界案例 | 當前狀況 | Gap-010 後 |
|---------|---------|-----------|
| 測試檔一開始就有語法錯誤 | ✅ PreRunValidator 攔截（attempt 0 注入修復指令） | ✅ 同 + Gap-010-D 提供 `py_compile` 行動清單 |
| 測試檔路徑含非 ASCII 或 Windows 絕對路徑 | ⚠️ fast_path 正則可能失效 | ✅ Gap-010-A 的 ENVIRONMENT 類直接 ESCALATE |
| 測試檔名不以 test_ 開頭（auth_test.py） | ❌ 所有 test_file 偵測失效 | 需要新增 `_test.py` 格式的正則 |
| 測試期望值本身寫錯（assertion mismatch） | ✅ Gap-008-C 在 3 次後偵測 | ✅ Gap-010-E 自動注入測試修復步驟 |
| Minimax 幻覺（換同義詞騙過 Jaccard） | ⚠️ Hallucination Guard 可被繞過 | ✅ Gap-010-B 的結構化三元組比對 |
| 步驟設計有根本缺陷（需要中間步驟） | ❌ ESCALATE，依賴人工介入 | ✅ Gap-010-E PlaybookEvolver 自動演化 |
| 跨步驟污染（前一步驟 ESCALATE 留下殘骸） | ❌ 未偵測 | ✅ Gap-010-C CrossStepStateValidator |
| 高重試時 Minimax 收到重複 task_prompt | ⚠️ Token 浪費 | ✅ Gap-010-B 漸進式摘要壓縮 |
| FailureKnowledgeBase 陳舊知識誤導 | ❌ 無 TTL 機制 | ✅ Gap-010-F 增加 timestamp + TTL |

### 5.3 測試檔非標準命名的修復方案

```python
# failure_tracker.py 中所有 test_\w+ 正則的統一修正：

_TEST_FILE_PATTERN = re.compile(
    r'(?:test_\w+|_test)\b.*\.py',  # 支援 test_foo.py 和 foo_test.py
    re.IGNORECASE,
)

# 同時需要更新：
# - prompt_builder._detect_test_file_error_hint()
# - failure_tracker.suspect_test_file_error()
# - playbook_runner._fast_path_test_file_check()
# - pre_run_validator._check_test_file_syntax()
```

---

## 6. 實作優先級矩陣

| Gap ID | 名稱 | 影響 | 實作複雜度 | 優先級 |
|--------|------|------|-----------|--------|
| **Gap-010-A** | 語意錯誤預算管理器 | 高：減少 SyntaxError 的 Token 浪費 | 低：新增 ErrorBudget dataclass | **P0** |
| **Gap-010-D** | EscalationDump 可執行復原計畫 | 高：大幅提升人工接手效率 | 低：修改 EscalationDump.save() | **P0** |
| **測試檔非標準命名修復** | 支援 `_test.py` 格式 | 高：消除嚴重盲點 | 極低：5 個正則修改 | **P0** |
| **Gap-010-B** | 漸進式上下文摘要壓縮 | 中：節省 Minimax Token | 中：修改 prompt_builder + CorrectionDecision | **P1** |
| **Gap-010-C** | 跨步驟狀態污染偵測 | 中：防止隱性失敗 | 低：新增 CrossStepStateValidator | **P1** |
| **Gap-010-F** | 元學習修正策略優化器 | 中：加速收斂 | 中：修改 KB 格式 + FailureTracker | **P1** |
| **Gap-010-E** | Playbook 自演化引擎 | 最高：實現 Level 5 | 高：新增 PlaybookEvolver 組件 | **P2** |
| **Memory Probe 驗證** | /compact 後記憶品質驗證 | 中：防止 compact 後迷失 | 中：新增探針機制 | **P2** |
| **Hallucination Guard 語意去重** | 三元組結構比較 | 低：現有 Jaccard 已有基本防護 | 中：需要 NLP 解析 | **P3** |
| **FailureKnowledgeBase TTL** | 陳舊知識衰減 | 低：長期演化後才顯現 | 低：新增 timestamp 比較 | **P3** |

---

## 附錄：關鍵數字參考

| 指標 | 當前值 | 建議值 | 說明 |
|------|-------|--------|------|
| compact_threshold_pct | 80% | 動態（65~80%） | Gap-009-F 已實作動態調整 |
| halt_threshold_pct | 90% | 90% | 保持不變，halt 後有自動恢復 |
| max_retries | playbook 定義 | 語意預算覆蓋 | Gap-010-A：按錯誤類型設上限 |
| is_stuck threshold | 2 次 | 2 次 | 保持（有 change_strategy 緩衝） |
| history_summary max_unique | 5 筆 | 5 筆 | 合理，不需調整 |
| correction_prompt max_chars | 1200 字 | 1200 字 | Gap-006-E 已調整 |
| KB max_entries | 1000 | 1000 + TTL 30 天 | Gap-010-F 補充 TTL |
| PreRunValidator severity | block/warn | block/warn | 保持兩級制 |

---

**文件狀態**: CLOSED@implemented（improving_26 狀態和解，2026-06-17）— Gap-010-A~F 與測試檔非標準命名修復**全數已落地**。對照碼：`execution/error_budget.py`（A）、`prompt_builder.py:226`（B）、`execution/cross_step_validator.py`（C）、EscalationDump shell 行動清單（D）、`evolution/playbook_evolver.py:248-265`（E）、`utils/knowledge_base.py:167` get_strategy_priority（F）、`failure_tracker.py:26` `(?:test_\w+|\w+_test)\.py`（命名修復）。詳見根層 `docs/04_planning/AutoSDD_improving_26.md` §3.2。  
**原下一個行動項目（已完成，存史）**: 按 P0 優先級實作 Gap-010-A（ErrorBudget）、Gap-010-D（EscalationDump 行動清單）、測試檔非標準命名修復
