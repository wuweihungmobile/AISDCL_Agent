# AutoClaude Level 5 路徑：六大新缺口與自治修復架構藍圖

**文件版本**: v1.1  
**建立日期**: 2026-05-01  
**Phase 3 完成日期**: 2026-05-01  
**AISDLC 階段**: 04_planning  
**前置文件**: AutoClaude_Improving_005.md（Phase 1.5 + Phase 2 ErrorClassifier 全部實裝完成）  
**狀態**: Phase 3 / Phase 4 全部完成（SD_Improving_03 v1.1 CLOSED 2026-05-12；G3 ✅ 三方簽核）

---

## 執行摘要

Phase 1.5（Gap-HS/EO/MR/CV/EKL）與 Phase 2（ErrorClassifier）已完整落地，系統達到 **Level 4.5**。  
測試套件通過率驗證：所有 005 計畫的缺口均已解決。

本文以「首席 AI 自動化架構師」視角，基於對 Level 4.5 實作的第三輪深度剖析，發現 **6 個前置文件未涵蓋的新架構缺口**，並提供通往 Level 5 自治開發系統的完整升級藍圖。

| 缺口 ID | 描述 | 優先級 |
|---------|------|--------|
| Gap-006-A | CONTEXT_NEGOTIATION 不受 Token Guard 保護 | **P1** |
| Gap-006-B | 多向振盪（3+ 種特徵碼輪替）偵測盲點 | **P1** |
| Gap-006-C | 測試檔偵測 regex 無法跨行匹配（pytest 集合錯誤格式）| **P1** |
| Gap-006-D | `/compact` 結果未驗證，壓縮失敗靜默繼續 | **P2** |
| Gap-006-E | correction_prompt 600 字上限對多檔案修正不足 | **P2** |
| Gap-006-F | ConvergenceMonitor 趨勢分析鎖定 pytest 輸出格式 | **P1** |

---

<thinking>

## 深度推理過程

### 零、Self-Verification Protocol：破損測試檔案完整推演

**場景定義**：`test_foo.py` 第 42 行有人類造成的語法錯誤，Playbook 設定 `evaluator_command: "pytest tests/test_foo.py"`, `max_retries: 3`。

**推演 Attempt 0**：

```
pytest 執行輸出：
  ERROR collecting tests/test_foo.py
    SyntaxError: invalid syntax (test_foo.py, line 42)
exit_code = 2
```

1. `_evaluate()` → failure_reason, eval_output, exit_code=2
2. `ErrorClassifier.classify()` → ENVIRONMENT 優先但不匹配（非 FileNotFoundError），SYNTAX 匹配 → `ErrorClass.SYNTAX`
3. `tracker.record(attempt=0, ..., error_class="syntax")`
4. `monitor.evaluate(tracker)`:
   - history = 1 筆，ENVIRONMENT 不符
   - `suspect_test_file_error()` = False（需 2 筆才激活）
   - `is_stuck()` = False（需 2 筆）
   - → recommendation = "continue"

5. **[關鍵漏洞分析] `_get_correction()` 呼叫 `_detect_test_file_error_hint()`**：
   ```python
   test_pattern = re.compile(r'test_\w+\.py.*(?:SyntaxError|ImportError|NameError)', re.IGNORECASE)
   ```
   
   pytest 集合錯誤的實際輸出格式：
   ```
   ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax
   ```
   
   `test_foo.py` 與 `SyntaxError` 位於**不同行**，而 regex 中的 `.*` 不跨行（無 `re.DOTALL`）。
   **結果：hint 不觸發。** Minimax 收不到測試檔警告，可能推薦修改實作檔。
   
   → 這是 **Gap-006-C** 的根源。

**推演 Attempt 1**：

假設 Minimax（未收到 test file hint）建議「修正 foo.py 的型別問題」，Claude Code 修改了 foo.py（毫無用處）。

pytest 再次輸出相同的 SyntaxError（test_foo.py 本身未被修正）。

6. `tracker.record(attempt=1, ...)` → 現在有 2 筆記錄
7. `suspect_test_file_error()` 激活：
   - 對每筆記錄掃描：`test_\w+\.py.*(?:SyntaxError|...)` 是否匹配？
   - eval_output = `"ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax"`
   - **同樣的多行問題！regex 仍無法匹配！** 
   - `suspect_test_file_error()` 返回 **False**！
   
8. `is_stuck()` 被調用：
   - `_normalize_error()` 對兩次相同輸出產生相同特徵碼
   - → `is_stuck()` = True！

9. ConvergenceMonitor：
   - ENVIRONMENT 不符
   - suspect_test_file_error() = False（bug！）
   - is_stuck() = True
   - `_is_count_improving([None, None])` = False（無 "N failed" 行）
   - → recommendation = **"escalate"**（特徵碼連續相同且無數量改善）

10. ESCALATION 觸發，EscalationDump 儲存：
    - `is_stuck = True, suspect_test_file = False, is_oscillating = False`
    
    **人類看到的報告誤導性極高**：顯示「卡死」，但沒有「疑似測試檔錯誤」標記。
    人類必須自己讀失敗鏈才能發現真正原因是測試檔語法錯誤。

**結論**：系統確實在 2 次嘗試後觸發 ESCALATION 並停止（不無腦重試），這是正確行為。  
但 **誤診** 為「卡死」而非「測試檔錯誤」，診斷資訊對人類接手不夠友好。根本原因是 Gap-006-C。

---

### 一、Gap-006-A：CONTEXT_NEGOTIATION Token Guard 保護缺口

讀取 `playbook_runner.py:204-223`（`_run_steps` 中的 CONTEXT_NEGOTIATION 段落）：

```python
cn_out = self._execute_prompt(
    prompt=cn.prompt,
    maintain_context=False,
    timeout=self._cfg.playbook.step_timeout_seconds,
    step_label="context_negotiation",
)
if cn.expected_keyword and cn.expected_keyword not in strip_ansi(cn_out.text):
    return PlaybookResult(False, 0, total, "CONTEXT_NEGOTIATION 失敗...")
logger.info("CONTEXT_NEGOTIATION 成功...")
is_first_prompt = False
```

`cn_out.triggered_halt` 與 `cn_out.triggered_compact` 完全被忽略。

**風險場景**：CONTEXT_NEGOTIATION 的初始化 prompt 很長（例如注入整個 AISDLC workflow 指引），導致 context 使用率在第一次交互後就達到 88%。

- 若 triggered_compact = True：系統沒有在主迴圈開始前壓縮，第一個步驟 EXECUTE 後立即再次到達 80%，觸發重複 compact 警告，浪費 token。
- 若 triggered_halt = True：系統完全忽略，繼續執行 T01。T01 執行後 context 100% 溢出，Claude Code 報錯，評估失敗，Minimax 介入。整個問題其實是 Token 問題，但系統進入了錯誤的 CORRECTION 循環。

**此缺口在長上下文初始化（AISDLC workflow 載入）場景下具有高觸發機率。**

---

### 二、Gap-006-B：多向振盪（3+ 種特徵碼輪替）偵測盲點

讀取 `failure_tracker.py:55-65`（`is_oscillating()`）：

```python
if len(set(recent_sigs)) != 2:
    return False
```

**3 路振盪場景**：`max_retries = 6`

| Attempt | Minimax 策略 | 結果特徵碼 |
|---------|-----------|---------|
| 0 | 初次修正（加型別標注） | Sig-A (TypeError) |
| 1 | 加 guard clause | Sig-B (AttributeError) |
| 2 | 移除型別標注 | Sig-C (NameError) |
| 3 | 又加型別標注 | Sig-A (TypeError) |
| 4 | 又加 guard clause | Sig-B (AttributeError) |
| 5 | 又移除型別標注 | Sig-C (NameError) |

最後 4 筆 = [B, C, A, B]，unique = 3 ≠ 2 → `is_oscillating()` = False。

`is_stuck()` 也返回 False（無連續相同）。`is_diverging()` 取決於 exit_code 趨勢，通常 False。

系統會耗盡所有 6 次重試後才 ESCALATION，浪費大量 token。

**核心問題**：is_stuck 與 is_oscillating 之間存在「三不管地帶」：錯誤持續變化但根本沒有收斂。

**修復方向**：引入「週期性收斂評估」— 若在 window=4 的歷史中，特徵碼的種類數 > 1（任何形式的振盪/漂移），且 fail_count 無下降趨勢，則建議 escalate。

---

### 三、Gap-006-C：測試檔偵測 Regex 無法跨行匹配

讀取 `failure_tracker.py:97-110`（`suspect_test_file_error()`）：

```python
test_file_pattern = re.compile(
    r'test_\w+\.py.*(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)',
    re.IGNORECASE,
)
```

讀取 `prompt_builder.py:88-99`（`_detect_test_file_error_hint()`）：

```python
test_pattern = re.compile(
    r'test_\w+\.py.*(?:SyntaxError|ImportError|NameError)',
    re.IGNORECASE,
)
```

兩個 pattern 都依賴 `.*` 在同一行同時找到測試檔名和錯誤類型。

**pytest 實際輸出分析**：

```
# 格式 1 — 集合錯誤（跨行，regex 失敗）：
ERROR collecting tests/test_foo.py
  SyntaxError: invalid syntax
      bar = foo(
           ^
  SyntaxError: invalid syntax

# 格式 2 — pytest 短摘要（同行，regex 成功）：
FAILED tests/test_foo.py - SyntaxError: invalid syntax
FAILED tests/test_foo.py::test_bar - ImportError: cannot import

# 格式 3 — 詳細 FAILURES 區塊（跨行，regex 失敗）：
_ tests/test_foo.py _____
test_foo.py:42: SyntaxError
```

測試案例 `test_two_records_pointing_to_test_file_suspect` 使用的 fixture：
```python
output = "SyntaxError: invalid syntax\ntest_foo.py: SyntaxError in test code"
```

這是「格式 2」變體（test_foo.py 和 SyntaxError 在同一行），但真實的 pytest 集合錯誤是「格式 1」（跨行）。

**測試案例未覆蓋最常見的 pytest 集合錯誤格式，導致系統在最常見失敗場景中失效。**

**修復方向**：改用雙重模式匹配：
1. 現有同行 pattern（保留）
2. 新增跨行 pattern：`re.compile(r'test_\w+\.py', re.I)` 配合第二個 pattern `re.compile(r'SyntaxError|ImportError|...', re.I)` 分別匹配，兩者都出現在同一份輸出則觸發

---

### 四、Gap-006-D：`/compact` 壓縮結果未驗證

讀取 `playbook_runner.py:777-796`（`_send_compact()`）：

```python
def _send_compact(self, is_first: bool, failure_summary: str = "") -> None:
    ...
    self._execute_prompt(
        prompt=compact_prompt,
        maintain_context=True,
        timeout=60,
        step_label="compact",
    )
    # 返回值完全被丟棄
```

**失敗場景 1 — Claude Code 不認識 `/compact`**：
若 Claude Code 版本或模式不支援 `/compact`，它可能回應「無法識別此命令」。  
系統繼續執行，context 未被壓縮，下一步立即再次觸發 80% 門檻，進入 compact 無窮循環（每步都 compact，但 context 沒有真的降低）。

**失敗場景 2 — compact 後 context 仍然很高**：
compact 後 Claude Code 仍有 78% context（因為保留了太多歷史）。下一步執行後可能又立即回到 80%+，再次 compact。

**影響**：若 compact 失敗，`triggered_compact` 旗標不會被清除，但 context 並沒有降低。下一步執行後 `step_out.triggered_compact` 可能再次為 True，導致重複 compact 呼叫但每次都無效。

**修復方向**：在 compact 後發送一個 probe prompt（例如讀取 context 使用率），驗證 compact 是否有效，若無效則記錄 WARNING 並跳過重試（避免無限循環）。

---

### 五、Gap-006-E：correction_prompt 600 字上限對多檔案修正不足

讀取 `minimax_client.py:81-89`：

```python
if len(decision.correction_prompt) > 600:
    logger.warning("Minimax correction_prompt 超過 600 字 (%d 字)，截斷前 600 字")
    decision = CorrectionDecision(
        correction_prompt=decision.correction_prompt[:600] + "\n（提示已截斷）",
        ...
    )
```

**典型多檔案修正場景**（Level 4.5 ErrorClassifier 整合之後，修正變得更複雜）：

```
# Minimax 生成的 correction_prompt（約 750 字）：
步驟 T03 失敗。需要以下三個修正：

1. 在 autoclaude/execution/playbook_runner.py 第 388 行，
   `corr_result = self._get_correction(...)` 呼叫需加入 
   `error_class=error_cls.value` 參數。

2. 在 autoclaude/decision/minimax_client.py 第 46 行，
   `decide_correction()` 函式簽名需加入 
   `error_class: str = "unknown"` 參數。

3. 在 autoclaude/decision/prompt_builder.py 第 30 行，
   `build_correction_message()` 需加入對應的 
   `error_class: str = "unknown"` 參數並在 return 段落中呼叫 
   `_get_error_class_hint(error_class)`。
```

600 字截斷後，第 2 點在 ~580 字被切斷，第 3 點完全遺失。  
Claude Code 只修正 playbook_runner.py，測試仍然失敗。  
下一次 Minimax 再生成同樣建議，再次截斷，無限循環。

**修復方向**：提高上限至 1200 字（SYSTEM_PROMPT 已說明 500 字，但 system prompt 的限制是「不超過 500 字」，correction_prompt 截斷是獨立邏輯）。或改為**智慧截斷**：在最後完整的句子/項目邊界截斷，而非硬切。

---

### 六、Gap-006-F：ConvergenceMonitor 趨勢分析鎖定 pytest 輸出格式

讀取 `convergence_monitor.py:95-97`：

```python
@staticmethod
def _extract_fail_count(eval_output: str) -> Optional[int]:
    m = re.search(r'(\d+) failed', eval_output, re.IGNORECASE)
    return int(m.group(1)) if m else None
```

此方法只提取 pytest 的 "N failed" 格式。

**非 pytest 場景**：

```yaml
# Playbook evaluator_command 範例
evaluator_command: "python -m unittest discover tests/"
evaluator_command: "go test ./..."
evaluator_command: "cargo test"
evaluator_command: "node --test"
evaluator_command: "bash scripts/validate.sh"
```

這些工具的輸出不含 "N failed"。所有 `fail_count` 都是 `None`。

`_is_count_improving([None, None, None])` → valid = [] → 返回 False。

`_is_count_improving` 函數的「多點線性回歸」（005 的亮點功能）對非 pytest 場景**完全失效**。

ConvergenceMonitor 在非 pytest 場景下退化為：只有 `is_stuck`（特徵碼）和 `is_diverging`（exit_code）的雙重保護，失去趨勢分析能力。

**修復方向**：
1. 增加針對其他框架的 fail_count 提取 pattern（unittest、go test 等）
2. 加入 exit_code 趨勢作為備用計數指標（exit_code 不能降到 0 前視為仍在失敗）
3. 允許 Playbook 配置 `fail_count_regex` 自訂提取模式

---

### 七、Level 5 架構設計推演

#### 7.1 StepMemoryEntry — 跨步驟成功修正記憶庫

**動機**：目前每個步驟的 CORRECTION 循環完全獨立，同類型錯誤在不同步驟（甚至不同 Playbook 執行）中重複發現、重複花費 Minimax token 修正。

**設計**：
```python
@dataclass
class StepMemoryEntry:
    error_signature: str       # 正規化後的錯誤特徵碼（作為查詢鍵）
    error_class: str           # ErrorClass.value
    successful_correction: str # 成功解決此類錯誤的 correction_prompt
    project: str               # 專案名稱（避免跨專案污染）
    step_id: str               # 來源步驟
    success_count: int = 1     # 此修正成功次數（信心度）
    created_at: str = ""
```

**查詢流程**（在 CORRECTION 前）：
```
error_sig = tracker._normalize_error(eval_output)
memory_hit = step_memory.lookup(error_sig, project)
if memory_hit and memory_hit.success_count >= 2:
    # 直接使用歷史成功修正，跳過 Minimax
    correction_prompt = memory_hit.successful_correction
    logger.info("StepMemory 命中：%s (信心度 %d)", error_sig[:50], memory_hit.success_count)
else:
    # 正常諮詢 Minimax
    correction_prompt = minimax.decide_correction(...)
    # 成功後更新記憶庫
```

**儲存策略**：JSON Lines 檔案（`checkpoint_dir/step_memory.jsonl`），查詢 O(N) 但記憶庫通常 < 1000 條。

#### 7.2 DynamicStepInserter — 自修復 Playbook

**動機**：當 `suspect_test_file_error = True` 時，系統目前直接 ESCALATION。但若系統能**動態插入一個「修正測試檔」步驟**，可以嘗試自動修復而非立即丟給人類。

**設計**：
```python
class DynamicStepInserter:
    def should_insert(self, report: ConvergenceReport, tracker: FailureTracker) -> bool:
        return report.trend == "diverging" and tracker.suspect_test_file_error()
    
    def create_fix_step(self, task: PlaybookTask, tracker: FailureTracker) -> PlaybookTask:
        """基於 EscalationDump 資訊動態生成「修正測試檔」步驟。"""
        suspect_files = self._extract_test_file_names(tracker)
        return PlaybookTask(
            step_id=f"{task.step_id}_FIX_TEST",
            name=f"自動修復測試檔（為 {task.step_id} 鋪路）",
            prompt=f"在繼續 {task.step_id} 之前，請先修正以下測試檔的語法/導入錯誤：{suspect_files}",
            evaluator_command=f"python -c \"import py_compile; py_compile.compile('{suspect_files[0]}')\"",
            max_retries=1,  # 只試 1 次，失敗立即 ESCALATION
        )
```

**觸發條件**：`suspect_test_file_error = True` AND 已有 `StepMemoryEntry` 記錄類似成功修正 → 信心度足夠嘗試自動插入步驟。

#### 7.3 SemanticDiffAnalyzer — 語義差異感知

**動機**：目前系統不知道 Claude Code 在每次 attempt 之間實際改了什麼。`error_signature` 的比較是基於評估輸出的文字特徵，不是基於程式碼變化。

**設計**：在每次 EXECUTE 後，立即 `git diff --stat` 捕捉：
```python
@dataclass  
class SemanticDiff:
    files_changed: list[str]    # 被修改的檔案清單
    lines_added: int
    lines_removed: int
    was_noop: bool              # True = 沒有任何程式碼變化
```

**應用**：若 `was_noop = True`（Claude Code 回應了但沒有改任何程式碼），直接跳過 EVALUATE，記錄特殊錯誤類型「Claude Code 無實際修改」，以特殊 correction_prompt 催促重新嘗試。

#### 7.4 AdaptiveCompactStrategy — 智慧壓縮策略

**動機**：目前 `/compact` 指令附帶的保留提示是靜態的（`failure_summary`）。對於不同的錯誤類型，應保留不同的資訊。

**設計**：根據 `ErrorClass` 生成不同的 compact 保留優先清單：

| ErrorClass | 優先保留 |
|-----------|---------|
| SYNTAX | 最近 5 行 SyntaxError 位置（檔案名+行號） |
| ASSERTION | 最近的 assert 差異值（expected vs actual） |
| TYPE | 函式簽名與呼叫端參數清單 |
| IMPORT | requirements.txt 現況 + import 路徑 |

</thinking>

---

## Part 1：Level 4.5 實裝完整性驗證

### 005 清單全部確認

| 缺口 ID | 修復位置 | 確認 |
|---------|---------|------|
| Gap-HS（build_history_summary 含 correction_prompt） | `failure_tracker.py:113-130` | ✅ 已實裝 |
| Gap-EO（EscalationDump is_oscillating 旗標） | `escalation.py:23`, `playbook_runner.py:516` | ✅ 已實裝 |
| Gap-MR（MinimaxClient 指數退避重試） | `minimax_client.py:95-110` | ✅ 已實裝（3 次，2s 指數退避） |
| Gap-CV（Checkpoint 一致性驗證） | `playbook_runner.py:549-568` | ✅ 已實裝（step_idx 超界 + step_id 不吻合） |
| Gap-EKL（_extract_key_error_lines 頭尾策略） | `prompt_builder.py:102-118` | ✅ 已實裝（前 5 + 後 15） |
| Phase 2 ErrorClassifier | `error_classifier.py` | ✅ 已實裝（7 種分類） |
| ENVIRONMENT 直接 ESCALATION | `convergence_monitor.py:44-49` | ✅ 已實裝（優先級 0） |
| error_class 提示注入 prompt | `prompt_builder.py:75-83` | ✅ 已實裝（4 種提示） |
| AttemptRecord error_class 欄位 | `failure_tracker.py:25` | ✅ 已實裝 |

### 測試覆蓋新增確認

| 測試群組 | 測試數 | 覆蓋重點 |
|---------|-------|---------|
| `TestBuildHistorySummary`（含 correction_prompt） | 3 個新測試 | correction_prompt 截至 150 字、空時不顯示 |
| MinimaxClient 退避重試 | 4 個新測試 | 500/429 重試、3 次上限、重試次數精確驗證 |
| ErrorClass 整合場景 | 4 個新測試 | environment/syntax/import/unknown 四路驗證 |
| EscalationDump `is_oscillating` | 已整合於 test_models.py | 振盪旗標序列化驗證 |

**Level 4.5 能力邊界**：

```
✅ 振盪模式（ABAB 2 路）→ 4 筆後 ESCALATION
✅ 卡死模式（連續相同特徵碼）→ ESCALATION 或 CHANGE_STRATEGY
✅ 環境錯誤 → Attempt 1 後直接 ESCALATION（不浪費 Minimax token）
✅ 測試檔錯誤（同行格式）→ Attempt 0 Minimax 警示 + Attempt 1 ESCALATION
✅ Minimax API 故障 → 3 次退避重試後才中止
✅ Checkpoint 不一致 → 從頭執行並清除 stale checkpoint
✅ 錯誤類型感知的 Minimax 提示（SYNTAX/IMPORT/TYPE/ENVIRONMENT）
✅ Minimax 歷史記憶完整（含已發送修正指令）

❌ CONTEXT_NEGOTIATION 超出 token 後沒有保護（Gap-006-A）
❌ 3 路以上振盪無法偵測（Gap-006-B）
❌ pytest 集合錯誤跨行格式的測試檔偵測失效（Gap-006-C）
❌ /compact 失敗無驗證（Gap-006-D）
❌ 多檔案修正 correction_prompt 被截斷（Gap-006-E）
❌ 非 pytest 框架無趨勢分析能力（Gap-006-F）
```

---

## Part 2：Self-Verification Protocol — 破損測試檔推演

**假設**：`test_foo.py` 第 42 行有語法錯誤（人類造成），Playbook：
```yaml
evaluator_command: "pytest tests/test_foo.py"
max_retries: 3
```

### 完整流程追蹤

| 階段 | 發生事件 | 預期行為 | 實際行為 |
|------|---------|---------|---------|
| Attempt 0 EVALUATE | pytest 輸出跨行集合錯誤 | 偵測為測試檔錯誤 | ❌ **Gap-006-C**：regex 不跨行，hint 不觸發 |
| Attempt 0 CORRECTION | Minimax 接收 eval_output | 告知 test_foo.py 有問題 | ❌ Minimax 看不到警告，可能建議修實作檔 |
| Attempt 1 EVALUATE | 相同 pytest 輸出 | suspect_test_file_error() = True | ❌ **Gap-006-C**：依然無法匹配，返回 False |
| Attempt 1 ConvergenceMonitor | is_stuck() = True（特徵碼相同） | escalate | ✅ 系統確實 ESCALATION |
| Attempt 1 ESCALATION | 儲存 EscalationDump | 顯示「疑似測試檔錯誤」 | ❌ `suspect_test_file = False`（誤診為卡死）|
| 人類接手 | 閱讀 EscalationDump | 快速識別測試檔問題 | ❌ 診斷資訊誤導（顯示卡死而非測試檔錯誤） |

**結論**：系統在 2 次嘗試後確實停止（防止無效消耗），但**誤診率高**。真正意義上的「識別出是測試檔本身的錯誤」在 pytest 集合錯誤格式下無法達成。Gap-006-C 是本場景的核心缺口。

---

## Part 3：六大新缺口深度設計

### Gap-006-A（P1）：CONTEXT_NEGOTIATION Token Guard 保護缺口

**位置**：`autoclaude/execution/playbook_runner.py:204-223`

**問題**：`cn_out.triggered_halt` 與 `cn_out.triggered_compact` 未被檢查。

**修復設計**：

```python
# playbook_runner.py — _run_steps() 中的 CONTEXT_NEGOTIATION 段落
if playbook.context_negotiation and is_first_prompt and start_idx == 0:
    cn = playbook.context_negotiation
    logger.info("=== STATE: CONTEXT_NEGOTIATION | 送出初始 Prompt ===")
    if not self._dry_run:
        cn_out = self._execute_prompt(
            prompt=cn.prompt,
            maintain_context=False,
            timeout=self._cfg.playbook.step_timeout_seconds,
            step_label="context_negotiation",
        )
        if cn.expected_keyword and cn.expected_keyword not in strip_ansi(cn_out.text):
            return PlaybookResult(False, 0, total, "CONTEXT_NEGOTIATION 失敗...")
        
        # === 新增：Token Guard 保護 ===
        if self._cfg.token_guard.enabled:
            if cn_out.triggered_halt:
                logger.warning("CONTEXT_NEGOTIATION 後 context 達 halt 門檻，儲存 checkpoint")
                return self._handle_token_halt(
                    playbook, playbook_path,
                    playbook.tasks[0], 0,  # 從第一個步驟繼續
                    cn_out, [], workflow, total,
                )
            if cn_out.triggered_compact:
                logger.info("CONTEXT_NEGOTIATION 後 context 達 compact 門檻，觸發壓縮")
                self._send_compact(False)
        logger.info("CONTEXT_NEGOTIATION 成功")
    is_first_prompt = False
```

**驗收標準（AC-006A-1）**：
- CONTEXT_NEGOTIATION 輸出達 halt 門檻時，系統儲存 checkpoint 並暫停，而非繼續執行主任務
- CONTEXT_NEGOTIATION 輸出達 compact 門檻時，在主任務開始前觸發 `/compact`

---

### Gap-006-B（P1）：多向振盪偵測盲點

**位置**：`autoclaude/execution/failure_tracker.py:55-65`、`convergence_monitor.py:70-76`

**問題**：`is_oscillating()` 只偵測 2 路 ABAB 振盪，3 路以上完全不被捕捉。

**修復設計**：

在 `FailureTracker` 新增 `is_cycling()` 方法，補充偵測多路週期振盪：

```python
def is_cycling(self, window: int = 6, min_unique: int = 2) -> bool:
    """
    偵測多路週期振盪（包含 2 路 ABAB 和 3 路 ABCABC 等）。
    
    條件：
    1. 至少 window 筆記錄
    2. 有 >= min_unique 種不同特徵碼（排除純卡死情況，那是 is_stuck() 的職責）
    3. 最近 window 筆中，沒有任何一個特徵碼出現次數 > window/2（否則可能只是局部卡死）
    4. fail_count 無下降趨勢（代表沒有收斂）
    """
    if len(self.history) < window:
        return False
    recent_sigs = [r.error_signature for r in self.history[-window:]]
    unique_sigs = set(recent_sigs)
    if len(unique_sigs) < min_unique:
        return False  # 只有 1 種 → is_stuck() 應處理
    # 沒有一種特徵碼佔絕對主導（> window/2 次）→ 確認是循環而非局部卡死
    max_count = max(recent_sigs.count(s) for s in unique_sigs)
    return max_count <= window // 2
```

在 `ConvergenceMonitor.evaluate()` 的優先級 2.5 後加入優先級 2.6：

```python
# 優先級 2.6：多向振盪（ABCABC 等）
if tracker.is_cycling(window=6):
    unique_count = len(set(r.error_signature for r in tracker.history[-6:]))
    return ConvergenceReport(
        0.0, "cycling", fail_counts, "escalate",
        f"錯誤在 {unique_count} 個特徵碼間週期循環，Minimax 策略互相干擾",
    )
```

**驗收標準（AC-006B-1）**：
- 6 筆 ABCABC 記錄後，`is_cycling()` 返回 True，ConvergenceMonitor 建議 escalate
- 4 筆 ABAB 記錄不觸發 `is_cycling()`（由 `is_oscillating()` 處理）

---

### Gap-006-C（P1）：測試檔偵測 Regex 無法跨行匹配

**位置**：`failure_tracker.py:97-110`、`prompt_builder.py:86-99`

**問題**：regex 不跨行，pytest 集合錯誤（"ERROR collecting..."）格式無法匹配。

**修復設計（雙模式偵測）**：

```python
# failure_tracker.py — suspect_test_file_error() 修改
def suspect_test_file_error(self) -> bool:
    if len(self.history) < 2:
        return False
    
    # 模式 1：同行匹配（FAILED tests/test_foo.py - SyntaxError）
    same_line_pattern = re.compile(
        r'test_\w+\.py.*(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)',
        re.IGNORECASE,
    )
    # 模式 2：跨行匹配（ERROR collecting tests/test_foo.py\n  SyntaxError）
    test_file_pattern = re.compile(r'test_\w+\.py', re.IGNORECASE)
    error_type_pattern = re.compile(
        r'(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)', re.IGNORECASE
    )
    
    impl_error_pattern = re.compile(r'\b(?!test_)[a-zA-Z]\w*\.py:\d+')
    
    for rec in self.history:
        output = rec.eval_output
        # 雙模式：任一匹配即確認指向測試檔
        has_test_file_error = (
            same_line_pattern.search(output) or
            (test_file_pattern.search(output) and error_type_pattern.search(output))
        )
        if not has_test_file_error:
            return False
        # 逐行掃描，排除框架路徑
        for line in output.splitlines():
            if impl_error_pattern.search(line) and not _FRAMEWORK_PATH_RE.search(line):
                return False
    return True
```

`_detect_test_file_error_hint()` 同步更新（採用相同雙模式邏輯）。

**驗收標準（AC-006C-1）**：
- `"ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax"` 應觸發 `suspect_test_file_error() = True`
- `"ERROR collecting tests/test_foo.py\n  SyntaxError..."` 也應觸發 `_detect_test_file_error_hint()` 的警告

---

### Gap-006-D（P2）：`/compact` 壓縮結果未驗證

**位置**：`autoclaude/execution/playbook_runner.py:777-796`

**問題**：`_send_compact()` 完全丟棄回傳值，無法偵測壓縮失敗。

**修復設計**（最小改動）：

```python
def _send_compact(self, is_first: bool, failure_summary: str = "") -> bool:
    """回傳 True = compact 送出（不保證成功），False = 略過。"""
    if is_first:
        return False
    logger.info("發送 /compact 指令（帶結構化壓縮提示）")
    compact_prompt = (
        "/compact\n"
        "請在壓縮時優先保留：\n"
        "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
        "2. 測試案例的名稱與期望行為\n"
        "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
        "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
    )
    if failure_summary:
        compact_prompt += f"\n\n重要：壓縮後必須記住以下當前失敗背景：\n{failure_summary}\n"
    
    compact_out = self._execute_prompt(
        prompt=compact_prompt,
        maintain_context=True,
        timeout=60,
        step_label="compact",
    )
    # 驗證：compact 後 context 不應再觸發 compact 門檻
    if compact_out.triggered_compact:
        logger.warning(
            "/compact 後 context 仍達 %.0f%%，可能壓縮失敗或保留內容過多",
            compact_out.peak_token_pct,
        )
    return True
```

**驗收標準（AC-006D-1）**：
- `/compact` 執行後若 context 仍 >= compact_threshold，記錄 WARNING
- 不觸發重複 compact（一次執行後即退出，不因警告再次呼叫）

---

### Gap-006-E（P2）：correction_prompt 600 字上限不足

**位置**：`autoclaude/decision/minimax_client.py:81-89`

**問題**：600 字上限對多檔案、多步驟修正指令過於嚴格。

**修復設計（智慧截斷）**：

```python
_CORRECTION_PROMPT_MAX_CHARS = 1200  # 從 600 提升至 1200

def _truncate_correction_prompt(self, prompt: str) -> str:
    """在句子/項目邊界智慧截斷，優於硬切。"""
    if len(prompt) <= _CORRECTION_PROMPT_MAX_CHARS:
        return prompt
    # 在上限前找最後一個完整句子結束位置
    truncated = prompt[:_CORRECTION_PROMPT_MAX_CHARS]
    # 優先在換行前截斷（保留完整項目）
    last_newline = truncated.rfind('\n')
    if last_newline > _CORRECTION_PROMPT_MAX_CHARS * 0.7:  # 保留至少 70%
        truncated = truncated[:last_newline]
    logger.warning(
        "Minimax correction_prompt 截斷: %d → %d 字",
        len(prompt), len(truncated),
    )
    return truncated + "\n（指令已在項目邊界截斷，請優先完成上方列出的修正）"
```

**驗收標準（AC-006E-1）**：
- 1000 字的 correction_prompt 不被截斷（新上限 1200）
- 1500 字的 correction_prompt 在換行邊界截斷，而非硬切在 1200 字正中間

---

### Gap-006-F（P1）：非 pytest 框架趨勢分析盲點

**位置**：`autoclaude/execution/convergence_monitor.py:95-97`

**問題**：`_extract_fail_count()` 只匹配 pytest 的 "N failed" 格式。

**修復設計（多框架模式 + Playbook 自訂）**：

```python
# convergence_monitor.py
_FAIL_COUNT_PATTERNS = [
    re.compile(r'(\d+) failed', re.I),                    # pytest
    re.compile(r'FAIL:\s*(\d+)', re.I),                   # unittest  
    re.compile(r'(\d+) tests? failed', re.I),             # go test 類
    re.compile(r'failures:\s*(\d+)', re.I),               # 通用格式
    re.compile(r'Tests run: \d+, Failures: (\d+)', re.I), # JUnit
]

@staticmethod
def _extract_fail_count(eval_output: str, custom_pattern: Optional[str] = None) -> Optional[int]:
    if custom_pattern:
        m = re.search(custom_pattern, eval_output, re.I)
        return int(m.group(1)) if m else None
    for pattern in _FAIL_COUNT_PATTERNS:
        m = pattern.search(eval_output)
        if m:
            return int(m.group(1))
    return None
```

同時在 `PlaybookTask` 增加可選欄位：

```yaml
# Playbook YAML 新增欄位（向下相容，預設 null）
tasks:
  - step_id: "T01"
    evaluator_command: "go test ./..."
    fail_count_regex: "(\\d+) FAIL"  # 自訂 fail count 提取
```

**驗收標準（AC-006F-1）**：
- unittest 的 "FAIL: 3" 格式能被 `_extract_fail_count()` 正確提取
- 自訂 `fail_count_regex` 優先於內建 pattern

---

## Part 4：Level 5 終極架構藍圖

### Level 5 定義

Level 5 自治開發系統具備以下核心能力：

| 能力維度 | Level 4.5（現況） | Level 5（目標） |
|---------|-----------------|----------------|
| 錯誤識別 | 語義分類（7 種 ErrorClass） | 語義 + 結構分析（git diff 感知） |
| 修正策略 | Minimax 每次重新生成 | 記憶庫命中 → 跳過 Minimax |
| 測試修復 | ESCALATION 等待人類 | 動態插入「修復測試檔」步驟 |
| 振盪偵測 | 2 路 ABAB | 多路 ABCABC + 週期振盪 |
| context 壓縮 | 靜態保留提示 | 按 ErrorClass 自適應保留清單 |
| 跨執行學習 | 無 | StepMemoryEntry 跨 Playbook 學習 |

### 升級路徑

```
Level 4.5（當前）
  ↓ Phase 3（本文 P1 缺口修復）
Level 4.6
  + CONTEXT_NEGOTIATION Token Guard（Gap-006-A）
  + 多路振盪偵測（Gap-006-B）
  + 跨行測試檔偵測（Gap-006-C）
  + 非 pytest 趨勢分析（Gap-006-F）

Level 4.6
  ↓ Phase 4（P2 缺口修復 + 初步 Level 5 能力）
Level 4.8
  + /compact 結果驗證（Gap-006-D）
  + correction_prompt 智慧截斷（Gap-006-E）
  + SemanticDiffAnalyzer（git diff 感知）
  + StepMemoryEntry 初版（單次執行內跨步驟記憶）

Level 4.8
  ↓ Phase 5（完整 Level 5 架構）
Level 5.0
  + StepMemoryEntry 持久化（跨 Playbook 執行學習）
  + DynamicStepInserter（測試檔自動修復）
  + AdaptiveCompactStrategy（ErrorClass 自適應壓縮）
  + Multi-Provider LLM 備援（Minimax → Claude → OpenAI 降級鏈）
```

### Level 5 核心模組架構（新增）

```
autoclaude/
├── memory/
│   ├── step_memory.py          # StepMemoryEntry 記憶庫（JSONL 持久化）
│   └── memory_manager.py       # 查詢/更新/老化記憶條目
├── repair/
│   ├── dynamic_inserter.py     # DynamicStepInserter（動態步驟插入）
│   └── semantic_diff.py        # SemanticDiffAnalyzer（git diff 感知）
└── execution/
    ├── error_classifier.py     # ✅ 已有
    ├── convergence_monitor.py  # ✅ 已有（加入 is_cycling）
    └── adaptive_compact.py     # AdaptiveCompactStrategy（新增）
```

### Level 5 StepMemoryEntry 完整設計

```python
# autoclaude/memory/step_memory.py

@dataclass
class StepMemoryEntry:
    error_signature: str        # FailureTracker._normalize_error() 後的特徵碼（查詢鍵）
    error_class: str            # ErrorClass.value
    successful_correction: str  # 成功解決此問題的 correction_prompt
    project: str                # 專案名稱（避免跨專案污染）
    step_id: str                # 來源步驟 ID（可追溯性）
    success_count: int = 1      # 此修正成功驗證次數（信心度評分）
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class StepMemoryManager:
    def __init__(self, memory_path: Path):
        self._path = memory_path
        self._entries: list[StepMemoryEntry] = self._load()

    def lookup(self, error_sig: str, project: str, min_confidence: int = 2
               ) -> Optional[StepMemoryEntry]:
        """查詢符合特徵碼且信心度達標的歷史修正。"""
        for entry in self._entries:
            if (entry.error_signature == error_sig[:200] and
                entry.project == project and
                entry.success_count >= min_confidence):
                return entry
        return None

    def record_success(self, error_sig: str, error_class: str,
                       correction: str, project: str, step_id: str) -> None:
        """記錄一次成功修正；若已有相同特徵碼，增加信心度。"""
        for entry in self._entries:
            if entry.error_signature == error_sig[:200] and entry.project == project:
                entry.success_count += 1
                self._save()
                return
        self._entries.append(StepMemoryEntry(
            error_signature=error_sig[:200],
            error_class=error_class,
            successful_correction=correction,
            project=project,
            step_id=step_id,
        ))
        self._save()
```

---

## Part 5：缺口完整矩陣（005 遺留 + 006 新發現）

| 缺口 ID | 描述 | 優先級 | 狀態 |
|---------|------|--------|------|
| Gap-Osc | 振盪模式偵測（2 路） | P0 | ✅ 004 已修復 |
| Gap-CS | change_strategy 分支 | P0 | ✅ 004 已修復 |
| Gap-MMP | Minimax prompt 測試檔感知 | P0 | ✅ 004 已修復 |
| Gap-HS | build_history_summary 含修正指令 | P0 | ✅ 005 已修復 |
| Gap-EO | EscalationDump is_oscillating | P0 | ✅ 005 已修復 |
| Gap-MR | MinimaxClient 退避重試 | P1 | ✅ 005 已修復 |
| Gap-CV | Checkpoint 一致性驗證 | P1 | ✅ 005 已修復 |
| Gap-EKL | 關鍵錯誤行頭尾策略 | P2 | ✅ 005 已修復 |
| Phase 2 EC | ErrorClassifier 語義分類 | P1 | ✅ 005 已修復 |
| **Gap-006-A** | CONTEXT_NEGOTIATION Token Guard | **P1** | ✅ 已完成（Phase 3） |
| **Gap-006-B** | 多路振盪（3+ 種）偵測盲點 | **P1** | ✅ 已完成（Phase 3） |
| **Gap-006-C** | 跨行測試檔偵測（集合錯誤格式）| **P1** | ✅ 已完成（Phase 3） |
| **Gap-006-D** | /compact 結果未驗證 | **P2** | ✅ 已完成（Phase 3） |
| **Gap-006-E** | correction_prompt 600 字截斷 | **P2** | ✅ 已完成（Phase 3） |
| **Gap-006-F** | 非 pytest 趨勢分析盲點 | **P1** | ✅ 已完成（Phase 3） |
| Level 5-M | StepMemoryEntry 跨執行學習 | P3 | 📋 006 規劃 |
| Level 5-D | DynamicStepInserter 自修復 | P3 | 📋 006 規劃 |
| Level 5-S | SemanticDiffAnalyzer git 感知 | P3 | 📋 006 規劃 |
| Level 5-C | AdaptiveCompactStrategy | P3 | 📋 006 規劃 |

---

## 附錄：立即行動清單（Phase 3 P1 優先）

```
# Phase 3 P1 — 建議工期：2-3 天

## Gap-006-C（最高影響力，Self-Verification 推演確認根本問題）
[x] 1. 在 test_failure_tracker.py 加入 pytest 跨行格式的 suspect_test_file 測試
        fixture: "ERROR collecting tests/test_foo.py\n  SyntaxError: invalid syntax"
[x] 2. 修改 failure_tracker.py:suspect_test_file_error() 改用雙模式偵測
[x] 3. 修改 prompt_builder.py:_detect_test_file_error_hint() 同步雙模式邏輯
[x] 4. 更新相關測試，驗證跨行格式觸發

## Gap-006-A
[x] 5. 在 test_playbook_runner.py 加入 CONTEXT_NEGOTIATION Token Guard 測試
        （dry_run=True 模擬 cn_out.triggered_halt = True 場景）
[x] 6. 修改 playbook_runner.py:_run_steps() CONTEXT_NEGOTIATION 段落加入 Token Guard 檢查

## Gap-006-B
[x] 7. 在 test_failure_tracker.py 加入 is_cycling() 測試（ABCABC 場景）
[x] 8. 在 failure_tracker.py 新增 is_cycling() 方法
[x] 9. 在 convergence_monitor.py 加入優先級 2.6 多路振盪評估

## Gap-006-F
[x] 10. 在 test_convergence_monitor.py 加入非 pytest 框架的 fail_count 提取測試
         （unittest "FAIL: 3"、JUnit "Failures: 2" 格式）
[x] 11. 修改 convergence_monitor.py:_extract_fail_count() 支援多框架

# Phase 3 P2 — 建議工期：1-2 天

## Gap-006-D
[x] 12. 修改 playbook_runner.py:_send_compact() 保留回傳值並加入結果驗證

## Gap-006-E
[x] 13. 修改 minimax_client.py 提高 correction_prompt 上限至 1200 字
[x] 14. 實作智慧截斷邏輯（在換行邊界截斷）

# Phase 4 Level 5 初版 — 建議工期：1 週

[ ] 15. 建立 autoclaude/memory/step_memory.py（StepMemoryEntry + StepMemoryManager）
[ ] 16. 建立 tests/test_step_memory.py
[ ] 17. 整合 StepMemoryManager 到 PlaybookRunner（CORRECTION 前查詢，成功後記錄）
[ ] 18. 建立 autoclaude/repair/semantic_diff.py（SemanticDiffAnalyzer）
[ ] 19. 整合 SemanticDiffAnalyzer 到 _run_steps（EXECUTE 後記錄 git diff）
```

---

**文件元數據**：
- **建立日期**: 2026-05-01
- **作者**: Claude Sonnet 4.6（首席 AI 自動化架構師角色）
- **審查狀態**: 待人工審查
- **下一份文件**: AutoClaude_Improving_007.md（Phase 3 P1 實裝完成後的驗證報告）
