# AutoClaude Agentic 閉環升級策略與 Level 5 自治藍圖

**文檔編號**: AutoClaude_Improving_003
**建立日期**: 2026-04-30
**作者角色**: 首席 AI 自動化架構師（Chief AI Automation Architect）
**分析基準**: `autoclaude/` 完整程式碼（commit: b268488）

---

## 執行摘要

本文件針對 AutoClaude PlaybookRunner 狀態機進行完整的架構深度剖析，識別出 **5 個已確認的 Bug/Gap**、**3 個代碼氣味（Code Smell）**，並提出從 Level 3 升級至 Level 4，最終達成 Level 5 自治開發系統的具體藍圖。

**核心結論**：
- 現有系統已具備 Level 3 自動化能力（自動重試 + 基本收斂偵測）
- 缺乏「錯誤收斂度評分」導致過早 ESCALATION
- `is_diverging()` 偵測到但從未觸發 ESCALATION，屬無效代碼
- `suspect_test_file_error()` 的 `impl_error_pattern` 存在框架路徑誤判問題

---

## 第一部分：深度推理與漏洞挖掘

### 1.1 狀態流轉脆弱性分析

#### 1.1.1 Bug #1：is_stuck / suspect_test_file 永遠是 False 的死代碼參數

**位置**: `playbook_runner.py` Line 392-396

```python
# 現有代碼
corr_result = self._get_correction(
    task, failure_reason, eval_output, attempt,
    history_summary=tracker.build_history_summary(),
    is_stuck=tracker.is_stuck(),           # ← 永遠是 False
    suspect_test_file=tracker.suspect_test_file_error(),  # ← 永遠是 False
)
```

**根因分析**：控制流在 Line 325 和 Line 348 已分別對 `suspect_test_file_error()` 和 `is_stuck()` 為 True 時執行 `return`（ESCALATION）。因此，程式執行到 Line 392 時，這兩個方法的返回值**必然是 False**。

**影響**：`prompt_builder.py` 中的 `context_hint` 生成邏輯（`is_stuck` / `suspect_test_file` 的警告提示）永遠不會被觸發。Minimax 從不收到這些關鍵語境提示。

**修復方案**：移除這兩個恆為 False 的參數，或重構為在 ESCALATION 決策之前傳入。

---

#### 1.1.2 Bug #2：is_diverging() 偵測有效但從不觸發提前 ESCALATION

**位置**: `failure_tracker.py` Line 52-57 vs `playbook_runner.py` Lines 325-368

```python
# failure_tracker.py — 偵測邏輯存在
def is_diverging(self) -> bool:
    """exit_code 嚴格遞增（且都非 0）→ Minimax 在惡化問題。"""
    ...

# playbook_runner.py — 主迴圈中完全缺失此分支
if tracker.suspect_test_file_error():  # ✅ 有提前退出
    ...ESCALATION...
if tracker.is_stuck():                 # ✅ 有提前退出
    ...ESCALATION...
# ❌ 缺失：if tracker.is_diverging(): ...ESCALATION...
if attempt >= max_retries:
    ...ESCALATION...
```

**影響**：當 Minimax 修正方向持續惡化（exit_code: 1 → 2 → 3），系統無法提前停止，浪費所有剩餘重試次數。

**修復方案（插入 Line 348 之後）**：

```python
# Gap 補充：發散偵測提前退出
if tracker.is_diverging():
    logger.error(
        "=== STATE: ESCALATION | [%s] exit_code 嚴格遞增，Minimax 修正方向持續惡化 ===",
        task.step_id,
    )
    self._save_escalation_dump(
        tracker, task, playbook_path, eval_output,
        human_hint=f"錯誤 exit_code 嚴格遞增，Minimax 修正方向疑似南轅北轍。請人工分析根因。",
    )
    self._notify("AutoClaude — 需要人工介入", f"[{task.step_id}] 錯誤持續惡化，請檢查日誌。")
    return PlaybookResult(
        False, len(step_log), total,
        f"[{task.step_id}] 錯誤發散（exit_code 遞增），提前升級",
        workflow, step_log,
    )
```

---

#### 1.1.3 Gap #3：缺乏錯誤收斂度評分（Convergence Score）

**問題場景**：
```
Attempt 0: pytest → 5 FAILED, 0 passed
Attempt 1: pytest → 3 FAILED, 2 passed  ← 有進步！
Attempt 2: pytest → 3 FAILED, 2 passed  ← is_stuck() = True → ESCALATION
```

現有設計在 Attempt 2 觸發 `is_stuck()`（error_signature 相同），但 Attempt 1→2 相比 Attempt 0 已有顯著進步。過早 ESCALATION 浪費了可能成功的機會。

**設計模式建議**：在 `FailureTracker` 中加入收斂評分機制：

```python
# failure_tracker.py 新增方法
def convergence_score(self) -> float:
    """
    基於 failed test count 趨勢，回傳 0.0（卡死）到 1.0（完全收斂）。
    需要 eval_output 包含 pytest 結果摘要。
    """
    if len(self.history) < 2:
        return 0.5  # 未知，保守估計
    
    fail_counts = [self._extract_fail_count(r.eval_output) for r in self.history]
    if all(c is None for c in fail_counts):
        return 0.5  # 無法解析，保守估計
    
    # 過濾掉 None
    valid = [(i, c) for i, c in enumerate(fail_counts) if c is not None]
    if len(valid) < 2:
        return 0.5
    
    # 計算最後兩次的差值（負 = 改善）
    last_diff = valid[-1][1] - valid[-2][1]
    if last_diff < 0:
        return 0.8   # 最近在改善
    elif last_diff == 0:
        return 0.2   # 卡死
    else:
        return 0.0   # 惡化

@staticmethod
def _extract_fail_count(eval_output: str) -> Optional[int]:
    """從 pytest 輸出中萃取失敗數量。"""
    m = re.search(r'(\d+) failed', eval_output)
    return int(m.group(1)) if m else None
```

**在 `is_stuck()` 整合收斂評分**：

```python
def is_stuck(self, consecutive_threshold: int = 2) -> bool:
    """結合特徵碼相同 AND 收斂評分低，才判定為真正卡死。"""
    if len(self.history) < consecutive_threshold:
        return False
    recent_sigs = [r.error_signature for r in self.history[-consecutive_threshold:]]
    signatures_identical = (len(set(recent_sigs)) == 1)
    
    # 如果特徵相同，但收斂分數顯示「有進步」，不觸發 stuck
    if signatures_identical and self.convergence_score() >= 0.7:
        return False  # 特徵相同但整體在改善，繼續重試
    
    return signatures_identical
```

---

### 1.2 Self-Verification 推演：pytest 測試檔語法錯誤

**場景**：`evaluator_command: "pytest tests/test_foo.py"`，且 `test_foo.py` 本身有語法錯誤。

#### 完整流程推演

**Attempt 0：**

Claude Code 執行 → 修改實作檔 → `pytest tests/test_foo.py` 輸出：
```
ERROR collecting tests/test_foo.py
ERRORS
SyntaxError: invalid syntax (test_foo.py, line 15)
=========================== short test summary info ===========================
ERROR tests/test_foo.py - SyntaxError: invalid syntax (test_foo.py, line 15)
============================== 1 error in 0.05s ==============================
```

`tracker.record(0, ..., eval_output, exit_code=1, minimax_reasoning="")`

- `len(history) == 1` → `suspect_test_file_error() = False`（threshold 未達）
- `is_stuck() = False`（單筆）
- `attempt 0 < max_retries` → 進入 CORRECTION

**Minimax 收到的 user message（prompt_builder.py 組裝）：**
```
## 關鍵錯誤行（萃取）
ERROR collecting tests/test_foo.py
SyntaxError: invalid syntax (test_foo.py, line 15)
ERROR tests/test_foo.py - SyntaxError: invalid syntax
```

Minimax 的 CORRECTION_SYSTEM_PROMPT 沒有明確區分「測試檔問題」vs「實作檔問題」，可能產生兩種回應：
- **回應 A（正確）**：「test_foo.py 第 15 行有語法錯誤，請修正它」
- **回應 B（幻覺）**：「實作檔可能缺少某方法，請在 `src/foo.py` 中補充」

若 Minimax 產生回應 B，Claude Code 修改實作，但 test_foo.py 語法錯誤依舊。

**Attempt 1：**

同樣的 pytest 輸出。`tracker.record(1, ..., eval_output, exit_code=1, "...")`

- `len(history) == 2` → 可執行 `suspect_test_file_error()`

#### 潛在 Bug #4：impl_error_pattern 框架路徑誤判

`suspect_test_file_error()` 中的 `impl_error_pattern`：
```python
impl_error_pattern = re.compile(r'\b(?!test_)[a-zA-Z]\w*\.py:\d+')
```

**問題**：pytest 完整 traceback 通常包含框架內部路徑：
```
_pytest/config/__init__.py:183   ← 匹配 !! (非 test_ 開頭的 .py:數字)
pluggy/manager.py:120            ← 匹配 !!
_pytest/python.py:608            ← 匹配 !!（以底線開頭被跳過，但仍是誤判）
```

這些路徑觸發 `impl_error_pattern`，導致 `suspect_test_file_error()` 返回 `False`，**系統無法識別測試檔問題，繼續浪費 Token 修改實作！**

**假設 pytest 輸出乾淨（只有 test_foo.py 的錯誤行）：**
- `suspect_test_file_error() = True` ✅
- ESCALATION 觸發，儲存 EscalationDump
- Human hint：「請在 AutoClaude 之外單獨執行測試指令確認測試檔本身可執行，再重跑 Playbook」
- 系統正確凍結，不浪費 Token ✅

**修復方案**：改用白名單路徑模式，過濾已知框架路徑：

```python
# 改良版 impl_error_pattern
FRAMEWORK_PATH_PREFIXES = ('_pytest', 'pluggy', 'site-packages', 'lib/python')

def suspect_test_file_error(self) -> bool:
    if len(self.history) < 2:
        return False
    test_file_pattern = re.compile(
        r'test_\w+\.py.*(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)',
        re.IGNORECASE,
    )
    # 改良：排除框架路徑，只偵測真正的實作檔路徑
    impl_error_pattern = re.compile(
        r'(?<!' + '|'.join(re.escape(p) for p in FRAMEWORK_PATH_PREFIXES) + r')' +
        r'\b(?!test_)[a-zA-Z][a-zA-Z0-9_]*\.py:\d+',
        re.IGNORECASE,
    )
    for rec in self.history:
        if not test_file_pattern.search(rec.eval_output):
            return False
        # 只計算非框架路徑的實作檔匹配
        impl_matches = [
            m.group() for m in impl_error_pattern.finditer(rec.eval_output)
            if not any(fw in rec.eval_output[max(0, m.start()-50):m.start()]
                       for fw in FRAMEWORK_PATH_PREFIXES)
        ]
        if impl_matches:
            return False
    return True
```

---

### 1.3 上下文污染與衰減分析

#### 1.3.1 /compact 的語境破壞問題（Gap #5）

**問題場景**：步驟 T05 進行第 2 次重試時，context 達到 80%：

```
EXECUTE(T05, attempt=1)
  → peak_token_pct = 0.82 → should_compact = True
  → (step 完成後) TOKEN_COMPACT state
  → _send_compact()    ← 此時 Claude Code 已收到 Minimax 的 correction_prompt 語境
  → /compact 觸發      ← 壓縮掉部分歷史，包含 Minimax 說「要修正 foo.py:42」的脈絡
EXECUTE(T05, attempt=2, correction_prompt=Minimax之前的指示)
  → Claude Code 已遺忘被壓縮的語境，可能重複犯同樣的錯
```

**改善設計**：在 CORRECTION 重試迴圈中，`_send_compact()` 應攜帶當前失敗的關鍵資訊：

```python
def _send_compact_with_context(self, is_first: bool, failure_summary: str = "") -> None:
    if is_first:
        return
    compact_prompt = (
        "/compact\n"
        "請在壓縮時優先保留：\n"
        "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
        "2. 測試案例的名稱與期望行為\n"
        "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
        "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。\n"
    )
    if failure_summary:
        compact_prompt += f"\n重要：壓縮後必須記住以下當前失敗背景：\n{failure_summary}\n"
    self._execute_prompt(
        prompt=compact_prompt,
        maintain_context=True,
        timeout=60,
        step_label="compact",
    )
```

#### 1.3.2 Minimax correction_prompt 長度控管

**現有機制**：`CORRECTION_SYSTEM_PROMPT` 要求「不超過 500 字」，但此為 LLM 的軟性約束，可能被違反。

**建議**：在 `minimax_client.py` 的 `decide_correction()` 加入硬性截斷：

```python
decision = CorrectionDecision.model_validate(raw)
if len(decision.correction_prompt) > 600:
    logger.warning(
        "Minimax correction_prompt 超過 600 字 (%d 字)，截斷前 600 字",
        len(decision.correction_prompt),
    )
    decision = CorrectionDecision(
        correction_prompt=decision.correction_prompt[:600] + "\n（提示已截斷）",
        reasoning=decision.reasoning,
    )
return decision
```

---

### 1.4 停機問題與防護深度分析

#### 1.4.1 EscalationDump 完整度評估

| 內容項目 | 現況 | 重要性 |
|---------|------|-------|
| 失敗鏈（error_signature + minimax_reasoning） | ✅ | High |
| 自動診斷（is_stuck / is_diverging / suspect_test_file） | ✅ | High |
| 人類建議（human_hint） | ✅ | High |
| 最後評估輸出（前 3000 字） | ✅ | High |
| 最後 Claude Code 完整輸出 log 路徑 | ❌ **缺失** | High |
| Checkpoint 繼續點資訊（可直接 --continue 的起點） | ❌ **缺失** | High |
| Playbook YAML 內容快照 | ❌ **缺失** | Medium |
| 環境資訊（Python 版本、工作目錄） | ❌ **缺失** | Low |

**修復方案**：在 `EscalationDump` 加入更多診斷資訊：

```python
# models/escalation.py 新增欄位
@dataclass
class EscalationDump:
    ...
    last_log_path: str = ""        # 最後一次執行的 log 檔路徑
    checkpoint_resume_hint: str = ""  # 如何用 --continue 繼續
    
    def to_markdown(self) -> str:
        ...
        if self.last_log_path:
            lines.append(f"## 最後執行 Log\n`{self.last_log_path}`")
        if self.checkpoint_resume_hint:
            lines.append(f"## 繼續執行指令\n```\n{self.checkpoint_resume_hint}\n```")
```

#### 1.4.2 通知可靠性問題（Gap #6）

**現有**：桌面通知（plyer / win10toast）+ ESC+F12 全域熱鍵。

**問題**：
- 用戶可能不在電腦旁（遠端工作、長時間無人值守）
- 桌面通知可能在全螢幕模式下被抑制
- 無 fallback 機制確認通知已被接收

**建議加入通知層級**（`utils/notifier.py` 擴充）：

```python
class NotificationLevel(str, Enum):
    INFO = "info"        # 桌面通知（現有）
    WARNING = "warning"  # 桌面 + 寫入 escalation.log
    CRITICAL = "critical" # 桌面 + log + webhook（若設定）

def notify_escalation(title: str, message: str, dump_path: str, cfg: AppConfig) -> None:
    """ESCALATION 級別的強化通知。"""
    notify(title, message, enabled=cfg.notification.enabled)
    
    # 永遠寫入 escalation_alert.log（無論通知是否啟用）
    alert_log = Path(cfg.checkpoint_dir) / "escalation_alert.log"
    with alert_log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {title} | {message} | dump={dump_path}\n")
    
    # Webhook 通知（若設定）
    if cfg.notification.webhook_url:
        _send_webhook(cfg.notification.webhook_url, title, message, dump_path)
```

---

## 第二部分：Agentic 閉環升級策略

### 2.1 錯誤收斂度分析升級（L3 → L4）

#### 核心設計模式：ConvergenceMonitor

```python
# autoclaude/execution/convergence_monitor.py（新增）
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ConvergenceReport:
    score: float             # 0.0 = 完全卡死, 1.0 = 完全收斂
    trend: str               # "improving" | "stuck" | "diverging" | "unknown"
    failed_tests_history: list[Optional[int]]
    recommendation: str      # "continue" | "escalate" | "change_strategy"
    reasoning: str


class ConvergenceMonitor:
    """
    綜合評估跨 attempt 的錯誤收斂趨勢。
    整合 FailureTracker 的三個偵測方法，加入數量化收斂分析。
    """
    
    def evaluate(self, tracker: "FailureTracker") -> ConvergenceReport:
        history = tracker.history
        
        if len(history) == 0:
            return ConvergenceReport(0.5, "unknown", [], "continue", "無歷史記錄")
        
        fail_counts = [self._extract_fail_count(r.eval_output) for r in history]
        
        # 優先級 1：疑似測試檔本身有錯誤 → 立即停止
        if tracker.suspect_test_file_error():
            return ConvergenceReport(
                0.0, "diverging", fail_counts,
                "escalate",
                "錯誤始終指向測試檔，修改實作無效",
            )
        
        # 優先級 2：特徵碼相同（純卡死）
        if tracker.is_stuck():
            # 但如果有數量減少的跡象，降低判定嚴重程度
            if self._is_count_improving(fail_counts):
                return ConvergenceReport(
                    0.4, "stuck",  fail_counts,
                    "change_strategy",
                    "特徵碼相同但失敗數減少，嘗試不同修正策略",
                )
            return ConvergenceReport(
                0.0, "stuck", fail_counts,
                "escalate",
                "特徵碼連續相同且無數量改善",
            )
        
        # 優先級 3：exit_code 嚴格遞增（惡化）
        if tracker.is_diverging():
            return ConvergenceReport(
                0.0, "diverging", fail_counts,
                "escalate",
                "exit_code 嚴格遞增，修正方向錯誤",
            )
        
        # 分析收斂趨勢
        if self._is_count_improving(fail_counts):
            return ConvergenceReport(
                0.7, "improving", fail_counts,
                "continue",
                f"失敗數持續減少: {fail_counts}",
            )
        
        return ConvergenceReport(
            0.5, "unknown", fail_counts,
            "continue",
            "無法判定趨勢，繼續重試",
        )
    
    @staticmethod
    def _extract_fail_count(eval_output: str) -> Optional[int]:
        m = re.search(r'(\d+) failed', eval_output, re.IGNORECASE)
        return int(m.group(1)) if m else None
    
    @staticmethod
    def _is_count_improving(counts: list[Optional[int]]) -> bool:
        valid = [c for c in counts if c is not None]
        if len(valid) < 2:
            return False
        return valid[-1] < valid[-2]  # 最近一次比前一次少
```

#### 在 PlaybookRunner 整合 ConvergenceMonitor

```python
# playbook_runner.py 修改版
tracker = FailureTracker(task.step_id)
monitor = ConvergenceMonitor()  # 新增

for attempt in range(max_retries + 1):
    ...
    tracker.record(attempt, failure_reason, eval_output, exit_code, minimax_reasoning)
    
    # 統一收斂評估（取代分散的三個 if 檢查）
    report = monitor.evaluate(tracker)
    
    if report.recommendation == "escalate":
        logger.error("=== STATE: ESCALATION | [%s] %s ===", task.step_id, report.reasoning)
        self._save_escalation_dump(
            tracker, task, playbook_path, eval_output,
            human_hint=f"收斂評估：{report.reasoning}（trend={report.trend}）",
        )
        self._notify("AutoClaude — 需要人工介入", f"[{task.step_id}] {report.reasoning}")
        return PlaybookResult(False, ...)
    
    if attempt >= max_retries:
        ...ESCALATION（重試耗盡）...
    
    # CORRECTION：帶入收斂報告上下文
    corr_result = self._get_correction(
        task, failure_reason, eval_output, attempt,
        history_summary=tracker.build_history_summary(),
        convergence_report=report,  # 新增
    )
```

### 2.2 上下文摘要壓縮升級（L3 → L4）

#### 智慧壓縮決策：壓縮時機控制

```python
# 在 CORRECTION 重試迴圈中，精細控制 /compact 時機
def _should_compact_now(
    self,
    step_out: _StepOutput,
    in_correction_loop: bool,
    correction_history_len: int,
) -> bool:
    """
    判斷是否應立即 /compact。
    在 CORRECTION 迴圈中，避免在關鍵修正語境中途壓縮。
    """
    if not step_out.triggered_compact:
        return False
    
    # 若在 CORRECTION 迴圈的第 1 次修正中，稍微容忍更高的 context
    # 等到修正成功或卡死後再壓縮，避免破壞修正語境
    if in_correction_loop and correction_history_len <= 1:
        return step_out.peak_token_pct >= 85  # 提高門檻到 85%
    
    return True
```

#### 錯誤摘要壓縮：Error History Digest

```python
# prompt_builder.py 新增
def build_error_digest(tracker: "FailureTracker") -> str:
    """
    生成給 /compact 的錯誤歷史摘要，確保壓縮後保留關鍵錯誤資訊。
    限制在 200 字以內，只保留最關鍵的錯誤模式。
    """
    if not tracker.history:
        return ""
    
    latest = tracker.history[-1]
    summary_lines = [f"步驟 {tracker.step_id} 失敗歷史摘要："]
    summary_lines.append(f"- 已重試 {len(tracker.history)} 次")
    summary_lines.append(f"- 最新錯誤特徵: {latest.error_signature[:80]}")
    
    if tracker.is_stuck():
        summary_lines.append("- 狀態: 卡死（特徵相同）")
    elif tracker.is_diverging():
        summary_lines.append("- 狀態: 惡化（exit_code 遞增）")
    
    return "\n".join(summary_lines)
```

---

## 第三部分：Level 5 自治開發系統終極升級藍圖

### 3.1 Level 定義對照

| Level | 自治能力 | 人類介入頻率 | 現況 |
|-------|---------|------------|------|
| L1 | 手動執行每個步驟 | 每步都需要 | 已超越 |
| L2 | 自動執行，失敗立即停止 | 任何失敗都停 | 已超越 |
| L3 | 自動重試 + 基本收斂偵測 | 複雜失敗才停 | **現況** |
| L4 | 錯誤分類 + 收斂評分 + 智慧壓縮 | 罕見根因錯誤 | **本文目標** |
| L5 | 自我修改策略 + 跨任務學習 + 根因假設 | 幾乎無需 | 終極目標 |

### 3.2 L3 → L4 升級路線圖

#### Phase 1（優先級 High，1-2 週）

**任務 1：修復 is_diverging 提前觸發 ESCALATION**
- 在 `playbook_runner.py` Line 348 後插入 `is_diverging()` 分支
- 對應測試：`tests/test_playbook_runner.py` 新增 `test_escalation_on_diverging`

**任務 2：修復 impl_error_pattern 框架路徑誤判**
- 改良 `failure_tracker.py` 中 `suspect_test_file_error()` 的路徑過濾邏輯
- 對應測試：`tests/test_failure_tracker.py` 新增框架路徑邊界案例

**任務 3：清除死代碼 is_stuck/suspect_test_file 參數**
- 從 `_get_correction()` 呼叫中移除這兩個永遠是 False 的參數
- 對應：`minimax_client.py` 和 `prompt_builder.py` 對應簽名清理

#### Phase 2（優先級 High，2-3 週）

**任務 4：實作 ConvergenceMonitor**
- 新增 `autoclaude/execution/convergence_monitor.py`
- 整合 ConvergenceReport 到 PlaybookRunner 主迴圈
- 取代原有三個分散的收斂檢查 if 分支

**任務 5：智慧 /compact（語境保護版）**
- `_send_compact()` 改為 `_send_compact_with_context()`，帶入失敗摘要
- 在 CORRECTION 迴圈中採用更高的 compact 門檻（85% vs 80%）

**任務 6：EscalationDump 增強**
- 加入 `last_log_path` 和 `checkpoint_resume_hint` 欄位
- 加入 `escalation_alert.log` 持久化通知

#### Phase 3（優先級 Medium，3-4 週）

**任務 7：correction_prompt 硬性長度截斷**
- `minimax_client.py` 加入 600 字截斷邏輯

**任務 8：Webhook 通知支援**
- `utils/notifier.py` 加入 webhook 通知選項
- `utils/config.py` 加入 `webhook_url` 配置項

### 3.3 L4 → L5 升級藍圖

#### 核心新增能力：跨 Playbook 失敗記憶庫

```
autoclaude/
└── intelligence/
    ├── failure_memory.py       # 持久化失敗模式資料庫（SQLite/JSONL）
    ├── root_cause_analyzer.py  # 根因假設生成（基於歷史模式）
    └── strategy_selector.py   # 動態選擇修正策略
```

**FailureMemory 設計**：

```python
# intelligence/failure_memory.py
@dataclass
class FailurePattern:
    """一個可復用的失敗模式記錄。"""
    error_signature: str        # 正規化錯誤特徵碼
    task_type: str              # 任務類型（pytest / build / lint）
    successful_fix: str         # 最終成功的修正 prompt 關鍵詞
    failed_strategies: list[str]  # 嘗試過但失敗的策略
    occurrence_count: int       # 歷史出現次數
    last_seen: str              # 最近一次出現的時間

class FailureMemory:
    """跨 Playbook 的失敗模式持久化庫。"""
    
    def lookup(self, error_signature: str) -> Optional[FailurePattern]:
        """查詢是否有相似錯誤的歷史修復記錄。"""
        ...
    
    def record_success(self, error_signature: str, correction_prompt: str) -> None:
        """記錄成功修復的 prompt，供未來複用。"""
        ...
    
    def record_failure(self, error_signature: str, strategy: str) -> None:
        """記錄失敗的策略，讓 L5 系統避開已知無效路徑。"""
        ...
```

**RootCauseAnalyzer（L5 核心）**：

```python
# intelligence/root_cause_analyzer.py
class RootCauseAnalyzer:
    """
    L5 根因假設生成器。
    不同於 Minimax 只修正當前失敗，RootCauseAnalyzer 嘗試推斷深層根因。
    """
    
    def generate_hypotheses(
        self,
        failure_chain: list[AttemptRecord],
        memory: FailureMemory,
    ) -> list[str]:
        """
        生成 2-3 個根因假設，按可能性排序。
        整合：失敗歷史 + 歷史記憶庫 + 錯誤模式分析。
        """
        hypotheses = []
        
        # 假設 1：基於歷史記憶庫的模式匹配
        latest_sig = failure_chain[-1].error_signature
        historical = memory.lookup(latest_sig)
        if historical and historical.successful_fix:
            hypotheses.append(
                f"[歷史匹配] 此錯誤模式曾在 {historical.occurrence_count} 個任務中出現，"
                f"成功修復關鍵詞：{historical.successful_fix}"
            )
        
        # 假設 2：基於收斂趨勢的策略建議
        if len(failure_chain) >= 2:
            signatures = [r.error_signature for r in failure_chain]
            if len(set(signatures)) == 1:
                hypotheses.append(
                    "[策略問題] 錯誤特徵完全相同，Minimax 修正策略可能方向錯誤，"
                    "建議嘗試：重新審視 task prompt 的目標定義"
                )
        
        # 假設 3：基於錯誤類型的分類建議
        if any('SyntaxError' in r.error_signature for r in failure_chain):
            hypotheses.append(
                "[語法錯誤] 多次出現語法錯誤，可能根因：Claude Code 產生的代碼與"
                "現有代碼 API 不相容，建議提供更多現有代碼語境"
            )
        
        return hypotheses[:3]
```

### 3.4 測試檔語法錯誤防護架構（L4 完整方案）

```
測試檔錯誤防護層次架構
───────────────────────────────────────────────────────────────
Layer 1: FailureTracker.suspect_test_file_error()（現有）
  → 觸發條件：2 次失敗均指向 test_*.py 且無實作檔錯誤
  → 修復：改良 impl_error_pattern 過濾框架路徑

Layer 2: ConvergenceMonitor（新增 L4）
  → 觸發條件：收斂評分 = 0，trend = "diverging"，suspect_test_file = True
  → 動作：ESCALATION + 詳細診斷報告

Layer 3: EscalationDump + alert.log（L4 強化）
  → 包含：last_log_path + checkpoint_resume_hint
  → 人類接手後可直接 `autoclaude pb.yaml --continue`

Layer 4: FailureMemory（L5 新增）
  → 記錄「測試檔語法錯誤」模式及其成功處理方式
  → 下次遇到類似模式，直接建議人類手動修正測試檔
───────────────────────────────────────────────────────────────
```

### 3.5 完整升級後的狀態機架構

```
INIT
  ↓
CONTEXT_NEGOTIATION（可選）
  ↓
EXECUTE[step N]
  ↓ (產生 _StepOutput)
TOKEN_COMPACT ← context >= compact_threshold（智慧壓縮版）
TOKEN_HALT    ← context >= halt_threshold（儲存 checkpoint，排程恢復）
  ↓
EVALUATE（regex + evaluator_command）
  ↓ 成功                    ↓ 失敗
next_step              tracker.record()
  ↓                         ↓
DONE ← 所有步驟完成    ConvergenceMonitor.evaluate()
                            ↓
                      report.recommendation == "escalate" ?
                       ├─ Yes → ESCALATION（帶 ConvergenceReport）
                       └─ No  → CORRECTION（Minimax + 歷史摘要）
                                    ↓
                              FailureMemory.lookup()（L5）
                                    ↓
                              correction_prompt → EXECUTE（retry）
                                    ↓
                              成功 → FailureMemory.record_success()（L5）
                                    繼續 next_step
```

---

## 第四部分：實施優先順序矩陣

| 任務 | 優先級 | 難度 | 影響面 | 建議順序 |
|------|-------|------|-------|---------|
| Bug #2: is_diverging 提前 ESCALATION | High | 低 | 正確性 | **第 1 順位** |
| Bug #4: impl_error_pattern 框架路徑誤判 | High | 中 | 正確性 | **第 2 順位** |
| Code Smell #1: 死代碼參數清理 | Medium | 低 | 可維護性 | **第 3 順位** |
| Gap #3: ConvergenceMonitor 收斂評分 | High | 高 | 效率 | **第 4 順位** |
| Gap #5: 智慧 /compact 語境保護 | Medium | 中 | 穩定性 | **第 5 順位** |
| Gap #6: EscalationDump 增強 + alert.log | Medium | 中 | 可操作性 | **第 6 順位** |
| Gap #7: correction_prompt 長度截斷 | Low | 低 | 穩定性 | **第 7 順位** |
| L5: FailureMemory 跨任務學習 | Low | 高 | 長期能力 | **第 8 順位** |

---

## 結論

AutoClaude 目前已達 **Level 3 自治能力**，核心狀態機設計穩固，`FailureTracker` + `EscalationDump` 的組合提供了良好的基礎。

**最高優先修復**（破壞性 Bug）：
1. `is_diverging()` 從未觸發提前 ESCALATION（空轉偵測）
2. `impl_error_pattern` 框架路徑誤判（導致無法識別測試檔問題）
3. 死代碼參數 `is_stuck/suspect_test_file` 傳入 `_get_correction()`

**升級至 L4 的關鍵投資**：
- `ConvergenceMonitor`（統一收斂評估，取代三個分散 if）
- 智慧 `/compact`（CORRECTION 迴圈語境保護）
- `EscalationDump` 增強（包含 log 路徑 + 繼續指令）

**L5 長期願景**：`FailureMemory` 跨 Playbook 學習 + `RootCauseAnalyzer` 根因假設生成，使系統真正達到「只有系統架構級問題才需要人類介入」的自治目標。

---

**文檔版本**: v1.0
**下一步**: 依照「第 1 順位」的 Bug #2 修復開始，按順序執行至第 3 順位，再進行完整測試套件驗證。
