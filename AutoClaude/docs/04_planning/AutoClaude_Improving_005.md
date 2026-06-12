# AutoClaude Level 4 精煉：五個新發現缺口與 Phase 2 ErrorClassifier 藍圖

**文件版本**: v1.0  
**建立日期**: 2026-05-01  
**AISDLC 階段**: 04_planning  
**前置文件**: AutoClaude_Improving_004.md（Phase 1 P0 已全部實裝並通過 144/144 測試）  
**狀態**: Active

---

## 執行摘要

Phase 1 P0（振盪偵測、change_strategy 分支、測試檔感知、線性回歸趨勢、correction_prompt 可審計性）已完整落地，系統達到 **Level 4.0**。

本文以「首席 AI 自動化架構師」視角，對 Level 4.0 實作進行第二輪深度剖析，發現 5 個前置文件未涵蓋的架構缺口，並提供 Phase 2 ErrorClassifier 的具體設計藍圖。

| 缺口 ID | 描述 | 優先級 |
|---------|------|--------|
| Gap-HS | `build_history_summary()` 不含 `correction_prompt_sent` → Minimax 記憶盲點 | **P0** |
| Gap-EO | `EscalationDump` 缺少 `is_oscillating` 診斷旗標 | **P0** |
| Gap-MR | `MinimaxClient` 無退避重試，API 故障立即中止整個 Playbook | **P1** |
| Gap-CV | Checkpoint 恢復時未驗證 Playbook 一致性（step_id 僅記錄不比對） | **P1** |
| Gap-EKL | `_extract_key_error_lines()` 取前 N 行，pytest 長輸出的根因可能被截斷 | **P2** |

---

<thinking>

## 深度推理過程

### 一、Gap-HS：Minimax 記憶盲點 — 最危險的靜默缺口

讀取 `failure_tracker.py:110-121`：

```python
def build_history_summary(self) -> str:
    lines = ["### 歷次失敗記錄（從最舊到最新）"]
    for rec in self.history:
        lines.append(
            f"- Attempt {rec.attempt}: exit={rec.exit_code} "
            f"sig={rec.error_signature[:80]} "
            f"| Minimax決策: {rec.minimax_reasoning[:60]}"  # ← 只有 reasoning！
        )
    return "\n".join(lines)
```

**`correction_prompt_sent` 完全缺席**。

讀取 `playbook_runner.py:385-398`：
```python
corr_result = self._get_correction(
    ...
    history_summary=tracker.build_history_summary(),  # ← 傳給 Minimax 的歷史
    ...
)
correction_prompt, minimax_reasoning = corr_result
tracker.update_last_correction_prompt(correction_prompt)  # ← 更新到 AttemptRecord
```

**推演：** 假設 max_retries=3，同一個步驟失敗 3 次：

- **Attempt 0 失敗** → Minimax 收到 history_summary（空）→ 決策：「請在 foo.py:42 加型別標注」→ `correction_prompt_sent = "請在 foo.py:42 加型別標注..."`
- **Attempt 1 失敗** → Minimax 收到 history_summary = `["Attempt 0: exit=1 sig=TypeError... | Minimax決策: 在 foo.py:42 加型別"]` → **看不到完整修正內容** → Minimax 可能再次建議「請加型別標注」（因為它不知道已經加過了）
- **Attempt 2 失敗** → 同樣的問題，循環浪費

**核心問題**：`minimax_reasoning` 前 60 字是決策摘要（通常是「因為 TypeError，建議加型別標注」），但不是 Claude Code 實際執行的指令。Minimax 在後續 attempt 中無法得知「我在 Attempt N-1 告訴 Claude Code 做了 X，但 X 失敗了」。

**影響評估**：
- 若錯誤是「單次可修正」的（Attempt 0 修好），無影響
- 若錯誤是「需要多次迭代」的（多次 attempt），Minimax 每次都在「重新想」而非「在失敗基礎上改進」
- 這個缺口會使 change_strategy 的效果大打折扣 — Minimax 不知道上次策略是什麼，無法真正「切換」

**修復設計**：

```python
# failure_tracker.py:build_history_summary() 修改
def build_history_summary(self) -> str:
    if not self.history:
        return ""
    lines = ["### 歷次失敗記錄（從最舊到最新）"]
    for rec in self.history:
        corr_preview = ""
        if rec.correction_prompt_sent:
            # 截取前 150 字，避免 Minimax user message 超長
            corr_preview = f"\n  └─ 發送給 Claude Code 的修正指令（前 150 字）: {rec.correction_prompt_sent[:150]}"
        lines.append(
            f"- Attempt {rec.attempt}: exit={rec.exit_code} "
            f"sig={rec.error_signature[:80]} "
            f"| Minimax決策: {rec.minimax_reasoning[:60]}"
            f"{corr_preview}"
        )
    return "\n".join(lines)
```

**驗證方式**：更新 `test_failure_tracker.py` 中的 `test_includes_attempt_info()` 和 `test_multiple_records_all_included()`，驗證當 `correction_prompt_sent` 非空時，summary 包含「發送給 Claude Code 的修正指令」字串。

---

### 二、Gap-EO：EscalationDump 振盪診斷旗標缺失

讀取 `escalation.py:12-27`：
```python
@dataclass
class EscalationDump:
    ...
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    # ← 沒有 is_oscillating！
```

讀取 `playbook_runner.py:487-519`（`_save_escalation_dump` 方法）：
```python
dump = EscalationDump(
    ...
    is_stuck=tracker.is_stuck(),
    is_diverging=tracker.is_diverging(),
    suspect_test_file=tracker.suspect_test_file_error(),
    # ← tracker.is_oscillating() 完全未傳入
)
```

**場景模擬**：振盪觸發 ESCALATION 後，人類查看 EscalationDump Markdown：

```markdown
## 自動診斷
- 錯誤卡死（特徵相同）: ❌ 否
- 錯誤發散（越改越壞）: ❌ 否
- 疑似測試檔本身有誤: ❌ 否
```

三個診斷旗標全部顯示「否」！人類必須讀 `human_hint` 文字才能理解是振盪觸發的。這在 ESCALATION 高壓情境下容易被忽略。

**修復設計**：

在 `EscalationDump` 加入第四個診斷旗標，並同步更新 `to_markdown()`、`_save_escalation_dump()`：

```python
# escalation.py
@dataclass
class EscalationDump:
    ...
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    is_oscillating: bool = False   # ← 新增

    def to_markdown(self) -> str:
        ...
        lines += [
            f"- 錯誤卡死（特徵相同）: {'✅ 是' if self.is_stuck else '❌ 否'}",
            f"- 錯誤發散（越改越壞）: {'✅ 是' if self.is_diverging else '❌ 否'}",
            f"- 疑似測試檔本身有誤: {'✅ 是' if self.suspect_test_file else '❌ 否'}",
            f"- 振盪錯誤（ABAB 交替）: {'✅ 是' if self.is_oscillating else '❌ 否'}",   # ← 新增
        ]
```

```python
# playbook_runner.py:_save_escalation_dump()
dump = EscalationDump(
    ...
    is_stuck=tracker.is_stuck(),
    is_diverging=tracker.is_diverging(),
    suspect_test_file=tracker.suspect_test_file_error(),
    is_oscillating=tracker.is_oscillating(),   # ← 新增
)
```

---

### 三、Gap-MR：MinimaxClient 無退避重試

讀取 `playbook_runner.py:692-722`（`_get_correction` 方法）：
```python
def _get_correction(self, ...) -> Optional[tuple[str, str]]:
    try:
        decision = self._minimax.decide_correction(...)
        ...
        return decision.correction_prompt, decision.reasoning
    except MinimaxError as exc:
        logger.error("Minimax decide_correction 失敗: %s", exc)
        return None
```

`None` 返回後，在 `_run_steps()` 中：
```python
if corr_result is None:
    return PlaybookResult(
        False, len(step_log), total, "Minimax API 故障，安全停止",
        workflow, step_log,
    )
```

**問題**：Minimax API 的一次性瞬時故障（網路抖動、429 Rate Limit）會立即終止整個 Playbook 執行，而非重試。

讀取 `minimax_client.py`，`decide_correction()` 使用 `httpx.Client` 同步呼叫，`timeout=30s`，但無任何重試邏輯。

**修復設計**：

在 `MinimaxClient` 層加入指數退避重試（不改動 `_get_correction` 介面）：

```python
# minimax_client.py
import time

MAX_API_RETRIES = 3
BASE_RETRY_DELAY = 2.0  # 秒

def decide_correction(self, ...) -> CorrectionDecision:
    last_exc = None
    for attempt_n in range(MAX_API_RETRIES):
        try:
            return self._call_api(...)
        except MinimaxError as exc:
            last_exc = exc
            if attempt_n < MAX_API_RETRIES - 1:
                wait = BASE_RETRY_DELAY * (2 ** attempt_n)
                logger.warning("Minimax API 暫時失敗（attempt %d/%d），%.0fs 後重試: %s",
                               attempt_n + 1, MAX_API_RETRIES, wait, exc)
                time.sleep(wait)
    raise last_exc  # 全部重試耗盡後才升級
```

**注意**：429 Rate Limit 應使用更長的等待時間（例如解析 `Retry-After` header）。503 Server Error 使用指數退避。連線超時直接重試。

---

### 四、Gap-CV：Checkpoint 無 Playbook 一致性驗證

讀取 `checkpoint_manager.py`，`CheckpointCheckpoint` dataclass 含：
- `step_idx`: int
- `step_id`: str  
- `playbook_path`: str

讀取 `_resolve_start()` (playbook_runner.py:532-543)：
```python
cp = self._checkpoint_mgr.load(playbook_path)
if cp is None:
    return 0, [], True
logger.info("從檢查點繼續 | step %d [%s]", cp.step_idx + 1, cp.step_id)
return cp.step_idx, cp.completed_step_log, True
```

**問題**：恢復時沒有任何驗證：
1. `cp.step_idx` 指向的 `playbook.tasks[cp.step_idx]` 的 `step_id` 是否等於 `cp.step_id`？
2. 若使用者在 checkpoint 後修改了 Playbook（增刪步驟、重排順序），會靜默執行錯誤的步驟

**場景**：
- Checkpoint 儲存：step_idx=2, step_id="T03"
- 使用者插入一個新步驟到 index 2 的位置
- 恢復後：playbook.tasks[2].step_id = "T02-new"
- 系統靜默執行了錯誤的步驟，且對使用者完全透明

**修復設計**：

在 `_resolve_start()` 加入一致性驗證：

```python
def _resolve_start(self, playbook_path: str, fresh: bool, playbook: Playbook) -> tuple[int, list[str], bool]:
    if fresh:
        return 0, [], True
    cp = self._checkpoint_mgr.load(playbook_path)
    if cp is None:
        return 0, [], True
    
    # 一致性驗證：確認 step_idx 對應的 step_id 是否吻合
    if cp.step_idx < len(playbook.tasks):
        actual_step_id = playbook.tasks[cp.step_idx].step_id
        if actual_step_id != cp.step_id:
            logger.warning(
                "Checkpoint 不一致！期望 step_id=%s，但 Playbook[%d].step_id=%s。"
                "Playbook 可能已被修改，從頭開始執行。",
                cp.step_id, cp.step_idx, actual_step_id,
            )
            self._checkpoint_mgr.clear(playbook_path)
            return 0, [], True
    else:
        logger.warning("Checkpoint step_idx=%d 超出 Playbook 步驟數 %d，從頭開始。",
                       cp.step_idx, len(playbook.tasks))
        self._checkpoint_mgr.clear(playbook_path)
        return 0, [], True
    
    logger.info("從檢查點繼續 | step %d [%s]", cp.step_idx + 1, cp.step_id)
    return cp.step_idx, cp.completed_step_log, True
```

**注意**：`run()` 中需更新呼叫 `_resolve_start()` 時傳入 `playbook` 參數（目前是在 `_run_steps()` 內部呼叫，需調整呼叫順序）。

---

### 五、Gap-EKL：`_extract_key_error_lines()` 取前 N 行

讀取 `prompt_builder.py:88-96`：
```python
def _extract_key_error_lines(eval_output: str, max_lines: int = 20) -> list[str]:
    pattern = re.compile(r'.*(ERROR|FAILED|SyntaxError|...|assert|Traceback).*', re.IGNORECASE)
    key = [ln + "\n" for ln in eval_output.splitlines() if pattern.search(ln)]
    return key[:max_lines]  # ← 取前 20 行
```

**問題場景**：pytest 輸出結構通常為：

```
collected 50 items

FAILED tests/test_foo.py::test_a - AssertionError    ← 第 1 個 FAILED
FAILED tests/test_foo.py::test_b - AssertionError    ← 第 2 個 FAILED
...
FAILED tests/test_foo.py::test_s - AssertionError    ← 第 19 個 FAILED
FAILED tests/test_foo.py::test_t - AssertionError    ← 第 20 個 FAILED（到達截斷點）
FAILED tests/test_foo.py::test_u - TypeError         ← 第 21 個 FAILED（被截斷！）
...
E  TypeError: foo() takes 1 argument but 2 were given  ← 根因行（被截斷！）
```

若最關鍵的錯誤（例如唯一的 TypeError，其餘都是 AssertionError）恰好在第 21 個 FAILED 之後，Minimax 接收不到根因，可能做出錯誤的修正建議。

**修復設計（選項 A — 最小改動）**：
改為取最後 N 行（通常 pytest 將最重要的錯誤摘要放在最後的 FAILURES 區段）：

```python
def _extract_key_error_lines(eval_output: str, max_lines: int = 20) -> list[str]:
    pattern = re.compile(r'.*(ERROR|FAILED|SyntaxError|...|assert|Traceback).*', re.IGNORECASE)
    key = [ln + "\n" for ln in eval_output.splitlines() if pattern.search(ln)]
    if len(key) <= max_lines:
        return key
    # 保留前 5 行（整體概覽）+ 後 15 行（根因通常在末尾）
    return key[:5] + ["  ... (中間部分省略) ...\n"] + key[-(max_lines - 5):]
```

**修復設計（選項 B — 語義提取）**：
加入 pytest `FAILURES` 區段偵測：

```python
# 若包含 pytest FAILURES 標記，優先提取 FAILURES 之後的內容
failures_marker = re.compile(r'^={3,}\s*FAILURES\s*={3,}', re.MULTILINE)
m = failures_marker.search(eval_output)
if m:
    failure_section = eval_output[m.start():]
    # 從 FAILURES 區段中提取關鍵行
    ...
```

選項 A 實作簡單，對 pytest 有效，P2 優先級可接受。

---

### 六、EscalationDump docstring 過時（技術債）

讀取 `escalation.py:18`：
```python
failure_chain: list[dict]  # [{attempt, failure_reason, error_signature, minimax_reasoning, exit_code}]
```

但 `to_failure_chain()` 現在回傳 6 個欄位，含 `correction_prompt_sent`。Docstring 未同步，會誤導讀者。

**修復**：單行更新 docstring：
```python
failure_chain: list[dict]  # [{attempt, failure_reason, error_signature, minimax_reasoning, exit_code, correction_prompt_sent}]
```

</thinking>

---

## Part 1：Level 4.0 現況基準評估

### Phase 1 P0 實裝確認

| 項目 | 檔案 | 行號 | 狀態 |
|------|------|------|------|
| `is_oscillating()` | failure_tracker.py | 52-62 | ✅ 通過（`test_failure_tracker.py:286-341` 覆蓋） |
| `correction_prompt_sent` 欄位 | failure_tracker.py | 24 | ✅ 通過（`to_failure_chain()` 已序列化） |
| 振盪偵測整合 | convergence_monitor.py | 57-62 | ✅ 通過（優先級 2.5） |
| `_is_count_improving()` 線性回歸 | convergence_monitor.py | 86-101 | ✅ 通過（斜率 < -0.5） |
| `change_strategy` 分支 | playbook_runner.py | 350-361 | ✅ 通過（`strategy_hint` 傳遞至 Minimax） |
| `_detect_test_file_error_hint()` | prompt_builder.py | 72-85 | ✅ 通過（Attempt 0 早期警示） |
| 振盪場景測試 | test_playbook_runner.py | 353+ | ✅ 通過 |
| 測試檔感知測試 | test_decision.py | 112+ | ✅ 通過 |

**測試套件**：`144 passed in 6.37s`（全通過）

### Level 4.0 能力邊界

```
現已保護的場景：
✅ 卡死模式（連續相同特徵碼）→ ESCALATION 或 CHANGE_STRATEGY
✅ 振盪模式（ABAB 交替）→ 4 筆後 ESCALATION
✅ 惡化模式（exit_code 嚴格遞增）→ ESCALATION
✅ 測試檔錯誤（Attempt 0 Minimax 警示 + Attempt 1 ESCALATION）
✅ Token 過高（compact / halt + checkpoint）
✅ ESC+F12 緊急中斷（checkpoint 儲存）

尚未保護的場景（本文新發現）：
❌ Minimax 重複建議相同修正（因為它看不到自己上次說了什麼）
❌ 振盪觸發 ESCALATION 後診斷旗標全顯 False（人類誤讀）
❌ Minimax API 瞬時故障導致整個 Playbook 中止
❌ Playbook 修改後 Checkpoint 靜默從錯誤步驟恢復
```

---

## Part 2：深度推演 — 新發現架構缺口

### 缺口 A：Gap-HS — Minimax 記憶盲點

**位置**：`failure_tracker.py:110-121`（`build_history_summary()`）

**問題核心**：當 Minimax 為 Attempt N 生成修正指令時，它能看到：
- ✅ 各次 attempt 的錯誤特徵碼（前 80 字）
- ✅ 各次的 Minimax reasoning（前 60 字）
- ❌ **各次實際發送給 Claude Code 的修正指令**（`correction_prompt_sent`）

這意味著 Minimax 不知道自己在 Attempt 0 說了什麼，可能在 Attempt 1 建議完全相同的修正。`change_strategy` 機制雖然能注入「嘗試不同策略」的指令，但若 Minimax 不知道上次策略是什麼，所謂的「不同」無從判斷。

**影響**：多次迭代場景（max_retries >= 2）中，Minimax 修正效率顯著降低。

**修復**（詳見 Part 3 實裝藍圖）：在 `build_history_summary()` 加入 `correction_prompt_sent` 前 150 字。

---

### 缺口 B：Gap-EO — EscalationDump 振盪旗標缺失

**位置**：`escalation.py:12-27`、`playbook_runner.py:501-514`

**問題核心**：`EscalationDump` 有三個布林診斷旗標（`is_stuck`、`is_diverging`、`suspect_test_file`），但缺少 `is_oscillating`。

振盪觸發 ESCALATION 時，人類看到的診斷是：

```markdown
## 自動診斷
- 錯誤卡死（特徵相同）: ❌ 否
- 錯誤發散（越改越壞）: ❌ 否
- 疑似測試檔本身有誤: ❌ 否
```

三個旗標全是「否」。人類必須閱讀 `human_hint` 文字才能理解原因，在 ESCALATION 高壓情境下容易誤讀。

---

### 缺口 C：Gap-MR — Minimax API 無退避重試

**位置**：`minimax_client.py`、`playbook_runner.py:692-722`

一次瞬時 API 故障（網路抖動、429 Rate Limit）→ `_get_correction()` 返回 `None` → `PlaybookResult(False, ..., "Minimax API 故障，安全停止")`。

**影響**：整個 Playbook 中止，需人工重新啟動。對長時運行的 Playbook（10+ 步驟），這是不可接受的中斷。

---

### 缺口 D：Gap-CV — Checkpoint 無 Playbook 一致性驗證

**位置**：`playbook_runner.py:532-543`（`_resolve_start()`）

Checkpoint 儲存了 `step_idx` 和 `step_id`，但恢復時只驗證 `playbook_path`，不驗證 `step_idx` 對應的 `step_id` 是否仍然吻合。

**風險場景**：使用者在 Checkpoint 後插入了新步驟 → 恢復後靜默跳過或重複執行錯誤步驟。

---

### 缺口 E：Gap-EKL — 關鍵錯誤行可能被前置截斷

**位置**：`prompt_builder.py:88-96`

`_extract_key_error_lines()` 取**前** 20 個匹配行。當 pytest 有 20+ 個 FAILED 測試時，第 21 個之後的錯誤（包括唯一的 TypeError 或 ImportError）被截斷，Minimax 看不到。

---

## Part 3：Phase 1.5 — P0/P1 修復實裝藍圖

### 修復 1（P0）：`build_history_summary()` 加入修正指令記錄

**文件**：`autoclaude/execution/failure_tracker.py`  
**修改複雜度**：低（約 8 行）

```python
def build_history_summary(self) -> str:
    """給 Minimax 的跨 attempt 歷史摘要（含已發送的修正指令）。"""
    if not self.history:
        return ""
    lines = ["### 歷次失敗記錄（從最舊到最新）"]
    for rec in self.history:
        corr_preview = ""
        if rec.correction_prompt_sent:
            corr_preview = (
                f"\n  └─ 已發送給 Claude Code 的修正指令（前 150 字）: "
                f"{rec.correction_prompt_sent[:150]}"
            )
        lines.append(
            f"- Attempt {rec.attempt}: exit={rec.exit_code} "
            f"sig={rec.error_signature[:80]} "
            f"| Minimax決策: {rec.minimax_reasoning[:60]}"
            f"{corr_preview}"
        )
    return "\n".join(lines)
```

**驗收標準（AC-HS-1）**：
- 當 AttemptRecord 有 `correction_prompt_sent` 時，`build_history_summary()` 輸出包含「已發送給 Claude Code 的修正指令」
- 截斷至 150 字，避免 Minimax user message 超長

**需更新測試**：
- `test_failure_tracker.py:test_includes_attempt_info` — 加入 correction_prompt_sent 驗證
- `test_failure_tracker.py:test_multiple_records_all_included` — 同上

---

### 修復 2（P0）：EscalationDump 加入 `is_oscillating` 旗標

**文件 1**：`autoclaude/models/escalation.py`  
**修改複雜度**：低（約 6 行）

```python
@dataclass
class EscalationDump:
    ...
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    is_oscillating: bool = False   # 新增：振盪模式（ABAB 交替）診斷旗標
    
    # failure_chain 欄位說明更新：
    failure_chain: list[dict]  # [{attempt, failure_reason, error_signature, minimax_reasoning, exit_code, correction_prompt_sent}]
    
    def to_markdown(self) -> str:
        ...
        lines += [
            "## 自動診斷",
            f"- 錯誤卡死（特徵相同）: {'✅ 是' if self.is_stuck else '❌ 否'}",
            f"- 錯誤發散（越改越壞）: {'✅ 是' if self.is_diverging else '❌ 否'}",
            f"- 振盪錯誤（ABAB 交替）: {'✅ 是' if self.is_oscillating else '❌ 否'}",  # 新增
            f"- 疑似測試檔本身有誤: {'✅ 是' if self.suspect_test_file else '❌ 否'}",
        ]
```

**文件 2**：`autoclaude/execution/playbook_runner.py`（`_save_escalation_dump()`）

```python
dump = EscalationDump(
    ...
    is_stuck=tracker.is_stuck(),
    is_diverging=tracker.is_diverging(),
    suspect_test_file=tracker.suspect_test_file_error(),
    is_oscillating=tracker.is_oscillating(),   # 新增
)
```

**驗收標準（AC-EO-1）**：
- 振盪觸發 ESCALATION 後，`EscalationDump.to_markdown()` 輸出包含「振盪錯誤（ABAB 交替）: ✅ 是」

---

### 修復 3（P1）：MinimaxClient 加入指數退避重試

**文件**：`autoclaude/decision/minimax_client.py`  
**修改複雜度**：中（約 25 行）

```python
import time

_MAX_API_RETRIES = 3
_BASE_RETRY_DELAY_S = 2.0

class MinimaxClient:
    ...
    def decide_correction(self, ...) -> CorrectionDecision:
        """含指數退避重試的 Minimax API 呼叫。"""
        last_exc: Exception = MinimaxError("未知錯誤")
        for attempt_n in range(_MAX_API_RETRIES):
            try:
                return self._call_once(...)
            except MinimaxError as exc:
                last_exc = exc
                if attempt_n < _MAX_API_RETRIES - 1:
                    wait = _BASE_RETRY_DELAY_S * (2 ** attempt_n)
                    logger.warning(
                        "Minimax API 暫時失敗（attempt %d/%d），%.0fs 後重試: %s",
                        attempt_n + 1, _MAX_API_RETRIES, wait, exc,
                    )
                    time.sleep(wait)
        raise last_exc

    def _call_once(self, ...) -> CorrectionDecision:
        """原有的單次 API 呼叫邏輯（從 decide_correction 分離出來）。"""
        ...
```

**驗收標準（AC-MR-1）**：
- 前 N-1 次 API 呼叫失敗時，自動重試並記錄 WARNING
- 全部重試耗盡後才 raise MinimaxError（讓 _get_correction 處理）

---

### 修復 4（P1）：Checkpoint 一致性驗證

**文件**：`autoclaude/execution/playbook_runner.py`（`_resolve_start()`）  
**修改複雜度**：低（約 15 行，含 _run_steps 傳參調整）

```python
def _resolve_start(
    self, playbook_path: str, fresh: bool, playbook: Playbook
) -> tuple[int, list[str], bool]:
    if fresh:
        return 0, [], True
    cp = self._checkpoint_mgr.load(playbook_path)
    if cp is None:
        return 0, [], True

    # 一致性驗證
    if cp.step_idx >= len(playbook.tasks):
        logger.warning("Checkpoint step_idx=%d 超出步驟數 %d，從頭執行。", cp.step_idx, len(playbook.tasks))
        self._checkpoint_mgr.clear(playbook_path)
        return 0, [], True
    actual_id = playbook.tasks[cp.step_idx].step_id
    if actual_id != cp.step_id:
        logger.warning("Checkpoint step_id 不一致（期望 %s，實際 %s），Playbook 已修改，從頭執行。",
                       cp.step_id, actual_id)
        self._checkpoint_mgr.clear(playbook_path)
        return 0, [], True

    logger.info("從檢查點繼續 | step %d [%s]", cp.step_idx + 1, cp.step_id)
    return cp.step_idx, cp.completed_step_log, True
```

**驗收標準（AC-CV-1）**：
- Playbook 修改後（step_id 不吻合），自動從頭執行並清除 stale checkpoint
- 記錄 WARNING 告知使用者發生了什麼

---

## Part 4：Phase 2 — ErrorClassifier 詳細設計

### 設計動機

目前所有評估失敗都進入同一個 Minimax 修正路徑，無視錯誤的語義分類。這導致：

1. **ENVIRONMENT 類**（FileNotFoundError、PermissionError）：AutoClaude 無法修復環境問題，應直接 ESCALATION，不浪費 Minimax token
2. **SYNTAX 類**：通常一次修正可解決，不需要長篇 correction_prompt
3. **IMPORT 類**：應優先建議 Minimax 檢查 requirements.txt / imports，而非修改邏輯

### 模組設計

**文件**：`autoclaude/execution/error_classifier.py`（新增）

```python
"""
ErrorClassifier — 對 eval_output 進行語義分類。
輸出 ErrorClass enum，供 ConvergenceMonitor 和 PlaybookRunner 使用。
"""
from __future__ import annotations
from enum import Enum
import re


class ErrorClass(str, Enum):
    SYNTAX      = "syntax"        # SyntaxError / IndentationError
    IMPORT      = "import"        # ImportError / ModuleNotFoundError
    ASSERTION   = "assertion"     # AssertionError / pytest FAILED
    TYPE        = "type"          # TypeError / AttributeError
    ENVIRONMENT = "environment"   # FileNotFoundError / PermissionError / 環境問題
    TIMEOUT     = "timeout"       # 執行超時（exit_code=124 或特定訊息）
    UNKNOWN     = "unknown"


_PATTERNS: list[tuple[ErrorClass, re.Pattern]] = [
    (ErrorClass.SYNTAX,      re.compile(r'SyntaxError|IndentationError', re.I)),
    (ErrorClass.IMPORT,      re.compile(r'ImportError|ModuleNotFoundError|No module named', re.I)),
    (ErrorClass.ENVIRONMENT, re.compile(r'FileNotFoundError|PermissionError|No such file|Access is denied', re.I)),
    (ErrorClass.TYPE,        re.compile(r'TypeError|AttributeError', re.I)),
    (ErrorClass.ASSERTION,   re.compile(r'AssertionError|assert |\d+ failed', re.I)),
    (ErrorClass.TIMEOUT,     re.compile(r'Timeout|timed out|exit code.*124', re.I)),
]


class ErrorClassifier:
    """根據 eval_output 和 exit_code 分類錯誤語義。"""

    def classify(self, eval_output: str, exit_code: int) -> ErrorClass:
        for error_class, pattern in _PATTERNS:
            if pattern.search(eval_output):
                return error_class
        return ErrorClass.UNKNOWN
```

### 整合策略

**整合點 1**：`ConvergenceMonitor.evaluate()` — 對 ENVIRONMENT 類直接返回 "escalate"：

```python
# 優先級 0（在所有現有優先級之前）
if tracker.history:
    last_record = tracker.history[-1]
    error_class = ErrorClassifier().classify(last_record.eval_output, last_record.exit_code)
    if error_class == ErrorClass.ENVIRONMENT:
        return ConvergenceReport(
            0.0, "environment_error", fail_counts, "escalate",
            "環境錯誤（FileNotFoundError/PermissionError）：AutoClaude 無法修復，需人工介入",
        )
```

**整合點 2**：`build_correction_message()` — 根據 ErrorClass 調整 System Prompt 提示：

```python
# prompt_builder.py 新增參數
def build_correction_message(..., error_class: str = "unknown") -> str:
    error_class_hint = _get_error_class_hint(error_class)
    ...

def _get_error_class_hint(error_class: str) -> str:
    hints = {
        "syntax": "\n> 💡 錯誤類型：語法錯誤。請直接修正語法，不需要邏輯重構。\n",
        "import": "\n> 💡 錯誤類型：Import 錯誤。請優先檢查 requirements.txt 和 import 語句。\n",
        "type": "\n> 💡 錯誤類型：型別錯誤。請確認函式簽名和呼叫端參數是否匹配。\n",
    }
    return hints.get(error_class, "")
```

**整合點 3**：`AttemptRecord` 新增 `error_class` 欄位（供歷史分析）：

```python
@dataclass
class AttemptRecord:
    ...
    correction_prompt_sent: str = ""
    error_class: str = "unknown"   # 新增：ErrorClass.value
```

### 驗收標準（Phase 2）

- **AC-EC-1**：ENVIRONMENT 類錯誤在第 1 次 attempt 後直接 ESCALATION，不進入 CORRECTION
- **AC-EC-2**：`build_correction_message()` 對不同 ErrorClass 加入對應的 Minimax 提示
- **AC-EC-3**：EscalationDump 的 `failure_chain` 包含每次的 `error_class`

---

## Part 5：優先級排序與完整藍圖更新

### 缺口完整矩陣（含 004 遺留 + 005 新發現）

| 缺口 ID | 描述 | 優先級 | 狀態 |
|---------|------|--------|------|
| Gap-Osc | 振盪模式偵測 | **P0** | ✅ 004 已修復 |
| Gap-CS | change_strategy 建議忽略 | **P0** | ✅ 004 已修復 |
| Gap-MMP | Minimax prompt 缺測試檔感知 | **P0** | ✅ 004 已修復 |
| Gap-EDC | EscalationDump 缺 correction_prompt | **P1** | ✅ 004 已修復 |
| Gap-Trend | _is_count_improving() 弱信號 | **P1** | ✅ 004 已修復 |
| Gap-1 | is_diverging() 從未提前觸發 | **P0** | ✅ 已存在 |
| Gap-2 | impl_error_pattern 框架路徑誤判 | **P0** | ✅ 已修復 |
| Gap-3 | is_stuck/suspect_test_file 參數永遠 False | **P1** | ✅ 已修復 |
| **Gap-HS** | build_history_summary 缺 correction_prompt | **P0** | 🔴 005 新發現 |
| **Gap-EO** | EscalationDump 缺 is_oscillating 旗標 | **P0** | 🔴 005 新發現 |
| **Gap-MR** | MinimaxClient 無退避重試 | **P1** | 🔴 005 新發現 |
| **Gap-CV** | Checkpoint 無 Playbook 一致性驗證 | **P1** | 🔴 005 新發現 |
| **Gap-EKL** | _extract_key_error_lines 截前 N 行 | **P2** | 🔴 005 新發現 |
| Phase 2 EC | ErrorClassifier 語義分類 | **P1** | 📋 004 規劃 |

### 升級路徑更新

```
Level 4.0（現況）: 振盪偵測 + change_strategy + 測試檔感知 + 線性回歸 + correction_prompt 可審計

Level 4.1（本文 P0 修復後）:
  + Minimax 歷史記憶完整（Gap-HS 修復）
  + EscalationDump 四旗標完整診斷（Gap-EO 修復）

Level 4.2（本文 P1 修復後）:
  + Minimax API 退避重試（Gap-MR 修復）
  + Checkpoint 一致性驗證（Gap-CV 修復）
  + ErrorClassifier 語義分類（Phase 2 EC）

Level 4.5（Phase 2 完整後）:
  + ENVIRONMENT 類直接 ESCALATION（不浪費 Token）
  + 錯誤類型感知的 Minimax 提示（更精準修正）
  + AttemptRecord 含 error_class（歷史可查）

Level 5.0（Phase 3 跨步驟記憶 + 自修復 Playbook）:
  + StepMemoryEntry（跨步驟成功修正記憶庫）
  + 動態步驟插入（修復評估器本身）
  + 自適應 compact 策略
```

---

## 附錄：立即行動清單（Phase 1.5 P0 優先）

```
# Phase 1.5 P0 — 建議工期：1 天
[ ] 1. 為 build_history_summary() 含 correction_prompt_sent 撰寫測試（TDD 先行）
[ ] 2. 修改 failure_tracker.py:build_history_summary() 加入 correction_prompt_sent 前 150 字
[ ] 3. 更新 test_failure_tracker.py 驗證新的 summary 格式
[ ] 4. 為 EscalationDump.is_oscillating 旗標撰寫測試
[ ] 5. 修改 escalation.py 加入 is_oscillating 欄位與 to_markdown() 更新
[ ] 6. 修改 playbook_runner.py:_save_escalation_dump() 傳入 is_oscillating=tracker.is_oscillating()
[ ] 7. 更新 escalation.py failure_chain docstring

# Phase 1.5 P1 — 建議工期：1-2 天
[ ] 8. 為 MinimaxClient 退避重試撰寫測試（mock httpx 返回 500 / 429）
[ ] 9. 重構 minimax_client.py:decide_correction() → _call_once() + 外層重試迴圈
[ ] 10. 為 Checkpoint 一致性驗證撰寫測試（step_idx 對應錯誤 step_id）
[ ] 11. 修改 playbook_runner.py:_resolve_start() 加入一致性驗證（接受 playbook 參數）
[ ] 12. 調整 _run_steps() 傳遞 playbook 到 _resolve_start()

# Phase 2 — 建議工期：3-4 天
[ ] 13. 建立 autoclaude/execution/error_classifier.py 模組與單元測試
[ ] 14. 整合 ErrorClassifier 到 ConvergenceMonitor（ENVIRONMENT 類直接 ESCALATE）
[ ] 15. 整合 ErrorClassifier 到 prompt_builder（錯誤類型提示）
[ ] 16. AttemptRecord 新增 error_class 欄位
[ ] 17. EscalationDump.failure_chain 加入 error_class 輸出
[ ] 18. 更新 test_decision.py 覆蓋 ENVIRONMENT/SYNTAX/IMPORT 分類場景
```

---

**文件元數據**：
- **建立日期**: 2026-05-01
- **作者**: Claude Sonnet 4.6（首席 AI 自動化架構師角色）
- **審查狀態**: 待人工審查
- **下一份文件**: AutoClaude_Improving_006.md（Phase 1.5 實裝完成後的驗證報告）
