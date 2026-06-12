# AutoClaude_Improving_002 — Agentic 閉環升級策略與 Level 5 自治藍圖

**版本**: v1.0
**建立日期**: 2026-04-30
**作者**: 首席 AI 自動化架構師分析報告
**基於**: AutoClaude commit `b268488`（PlaybookRunner 狀態機重構版）

---

## 一、現有系統深度剖析

### 1.1 狀態機脆弱性（State Transition Fragility）

**問題：錯誤收斂度偵測完全缺失**

目前 CORRECTION 迴圈的邏輯：

```
EVALUATE 失敗
  → _get_correction(task, failure_reason, eval_output, attempt)
      └─ Minimax 收到：step_id / task_name / task_prompt[:800] / eval_output[:1500] / retry_count
  → correction_prompt 送回 Claude Code
  → 再次 EVALUATE
  → 如果仍失敗 → 再次 CORRECTION（無記憶）
  → attempt >= max_retries → ESCALATION
```

**核心缺陷**：Minimax 每次呼叫是**無狀態的**（`retry_count` 只是整數），不知道：
- 上次修正指令是否讓錯誤「惡化」（exit code 從 1 → 多個 assert 炸開）
- 歷次修正中已嘗試過哪些修改方向
- 錯誤 pattern 是否是重複出現（即改不動的根因）

**風險推演（pytest test_foo.py 語法錯誤案例）**：

```
Attempt 1: evaluator 輸出 SyntaxError: invalid syntax (test_foo.py:15)
  → Minimax 收到 eval_output → 以為是實作檔有問題 → 產出「修正 auth.py」的指令
Attempt 2: evaluator 輸出 SyntaxError: invalid syntax (test_foo.py:15)（一模一樣）
  → Minimax 收到 → 再次指向實作檔（因為沒有歷史記憶）
Attempt 3: 同上 → ESCALATION
```

系統**無法識別「錯誤來源在測試檔本身」**，Minimax 永遠基於「修改實作」的假設產生修正指令，白耗 3 次 Token 才進 ESCALATION。

---

### 1.2 上下文污染與衰減（Context Degradation）

**Token Guard：/compact 是盲目的**

`_send_compact()` 直接送 `/compact` 字串給 Claude Code：
- Claude Code 會壓縮 context，但壓縮後**保留哪些資訊由 Claude 自行決定**
- AutoClaude 無法控制「錯誤日誌摘要」是否被保留
- 若 context 中充滿 3 次 pytest 失敗的完整 stacktrace，/compact 後摘要可能模糊化關鍵錯誤訊息

**prompt_builder 無錯誤摘要壓縮**

`build_correction_message()` 每次將 `eval_output[:1500]` 完整傳給 Minimax，但：
- 沒有跨 attempt 的 diff（無法比較「這次比上次更嚴重了」）
- 沒有 pattern 去重（同一行 SyntaxError 出現 3 次，但 Minimax 每次看完整輸出）

---

### 1.3 停機問題與防護（Halting Problem & Guardrails）

**ESCALATION 的資訊密度不足**

目前 ESCALATION 回傳：
```python
PlaybookResult(
    False, len(step_log), total,
    f"[{task.step_id}] 重試超限: {failure_reason}",  # 僅最後一次 failure_reason
    ...
)
```

和桌面通知：`步驟 [T03] 失敗 3 次，請檢查日誌`

人類接手時缺少：
- 各次 attempt 的 failure_reason 歷史（只記錄最後一次）
- Minimax 歷次 `reasoning` 的決策鏈
- eval_output 的結構化摘要（哪一行錯、哪種錯誤）
- 是否懷疑「根因在測試檔而非實作檔」的旗標

**ESC+F12 中斷後無快照**

中斷後回傳：`PlaybookResult(False, ..., "使用者 ESC+F12 中斷")`

沒有儲存 checkpoint（僅 TOKEN_HALT 才儲存），使用者強制中斷後無法恢復到中斷前的 step。

---

## 二、Agentic 閉環升級策略

### 2.1 錯誤收斂度偵測（Error Convergence Detector）

**設計目標**：在 CORRECTION → EVALUATE 迴圈中追蹤錯誤是否收斂，自動辨識無法自修復的根因。

**實作模式：FailureHistory + DivergenceDetector**

```python
# autoclaude/execution/failure_tracker.py

from dataclasses import dataclass, field
import re

@dataclass
class AttemptRecord:
    attempt: int
    failure_reason: str
    eval_output: str
    exit_code: int
    error_signature: str        # 正規化後的錯誤特徵碼（去掉行號等揮發性資訊）
    minimax_reasoning: str

class FailureTracker:
    """跨 attempt 追蹤錯誤模式，偵測收斂或發散。"""

    def __init__(self, step_id: str):
        self.step_id = step_id
        self.history: list[AttemptRecord] = []

    def record(self, attempt: int, failure_reason: str, eval_output: str,
               exit_code: int, minimax_reasoning: str = "") -> None:
        sig = self._normalize_error(eval_output)
        self.history.append(AttemptRecord(
            attempt=attempt,
            failure_reason=failure_reason,
            eval_output=eval_output,
            exit_code=exit_code,
            error_signature=sig,
            minimax_reasoning=minimax_reasoning,
        ))

    def is_stuck(self, consecutive_threshold: int = 2) -> bool:
        """最近 N 次錯誤特徵碼完全相同 → 確定卡死。"""
        if len(self.history) < consecutive_threshold:
            return False
        recent_sigs = [r.error_signature for r in self.history[-consecutive_threshold:]]
        return len(set(recent_sigs)) == 1

    def is_diverging(self) -> bool:
        """exit_code 遞增 or 錯誤行數增多 → Minimax 在惡化問題。"""
        if len(self.history) < 2:
            return False
        exit_codes = [r.exit_code for r in self.history]
        # 簡易啟發式：exit code 嚴格遞增（0以外）
        return all(exit_codes[i] < exit_codes[i+1] for i in range(len(exit_codes)-1))

    def suspect_test_file_error(self) -> bool:
        """eval_output 中錯誤總是指向 test_ 開頭的檔案 → 懷疑測試檔本身有問題。"""
        if not self.history:
            return False
        test_file_pattern = re.compile(r'(test_\w+\.py):(\d+).*(?:SyntaxError|ImportError|NameError)', re.IGNORECASE)
        impl_file_pattern = re.compile(r'(?<!test_)\w+\.py:\d+')
        for rec in self.history:
            if not test_file_pattern.search(rec.eval_output):
                return False
            if impl_file_pattern.search(rec.eval_output):
                return False  # 有指向實作檔，不確定
        return True

    def build_history_summary(self) -> str:
        """給 Minimax 的跨 attempt 歷史摘要。"""
        lines = ["### 歷次失敗記錄（從最舊到最新）"]
        for rec in self.history:
            lines.append(
                f"- Attempt {rec.attempt}: exit={rec.exit_code} "
                f"sig={rec.error_signature[:80]} "
                f"| Minimax決策: {rec.minimax_reasoning[:60]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _normalize_error(eval_output: str) -> str:
        """移除行號、記憶體地址等揮發性資訊，取得穩定的錯誤特徵碼。"""
        normalized = re.sub(r'line \d+', 'line N', eval_output)
        normalized = re.sub(r'0x[0-9a-fA-F]+', '0xADDR', normalized)
        normalized = re.sub(r'/.*/(\w+\.py)', r'\1', normalized)  # 去掉絕對路徑
        # 取前 200 字作為特徵碼
        return normalized[:200].strip()
```

**整合到 PlaybookRunner**：

```python
# 在 _run_steps 的 step for-loop 中：
tracker = FailureTracker(task.step_id)

for attempt in range(max_retries + 1):
    # ... EXECUTE ...
    failure_reason, eval_output = self._evaluate(task, step_out.text)

    if failure_reason is None:
        break  # 成功

    # 記錄到 tracker
    tracker.record(attempt, failure_reason, eval_output,
                   exit_code=self._last_eval_exit_code)  # 需讓 _evaluate 回傳 exit_code

    # === 新增：收斂度檢查 ===
    if tracker.suspect_test_file_error():
        logger.error("[%s] 懷疑測試檔本身有錯誤，停止重試", task.step_id)
        return PlaybookResult(
            False, len(step_log), total,
            f"[{task.step_id}] 懷疑測試檔語法/邏輯錯誤，請人工檢查測試檔",
            workflow, step_log,
            escalation_dump=tracker.to_dump(),  # 見 2.3
        )

    if tracker.is_stuck():
        logger.error("[%s] 錯誤特徵碼連續相同，Minimax 陷入循環", task.step_id)
        # 提前進 ESCALATION，不等 max_retries 耗盡
        break  # 跳出到 ESCALATION

    # CORRECTION：附帶歷史摘要給 Minimax
    corr = self._get_correction(task, failure_reason, eval_output, attempt,
                                 history_summary=tracker.build_history_summary())
```

---

### 2.2 上下文摘要壓縮（Error Summarization for Context Preservation）

**設計目標**：在 prompt_builder 中實作跨 attempt 的 diff 式錯誤摘要，送給 Minimax 的資訊更精準、更節省 token。

**升級 build_correction_message()**：

```python
def build_correction_message(
    step_id: str,
    task_name: str,
    task_prompt: str,
    expected_regex: Optional[str],
    failure_reason: str,
    eval_output: str,
    retry_count: int,
    history_summary: str = "",            # ← 新增
    is_stuck: bool = False,               # ← 新增
    suspect_test_file: bool = False,      # ← 新增
) -> str:
    # 關鍵錯誤行萃取（只取 ERROR/FAILED/SyntaxError 相關行）
    key_lines = _extract_key_error_lines(eval_output, max_lines=20)

    context_hint = ""
    if is_stuck:
        context_hint = "\n> ⚠️ 注意：前幾次修正後錯誤特徵未變，請考慮完全不同的修正策略。\n"
    if suspect_test_file:
        context_hint += "\n> ⚠️ 警告：錯誤始終指向測試檔而非實作檔，請先確認測試檔本身是否有問題。\n"

    return (
        f"## 失敗步驟\n{step_id}: {task_name}\n\n"
        f"## 原始 Prompt（前 600 字）\n{task_prompt[:600]}\n\n"
        f"## 期望輸出 Regex\n{expected_regex or '(無)'}\n\n"
        f"## 失敗原因\n{failure_reason}\n\n"
        f"## 關鍵錯誤行（萃取）\n{''.join(key_lines)}\n\n"
        f"{history_summary}\n\n"
        f"{context_hint}"
        f"## 已重試次數\n{retry_count}\n\n"
        "請輸出修正 JSON。"
    )


def _extract_key_error_lines(eval_output: str, max_lines: int = 20) -> list[str]:
    """從完整 eval_output 中萃取錯誤關鍵行（ERROR / FAILED / SyntaxError / assert）。"""
    import re
    pattern = re.compile(
        r'.*(ERROR|FAILED|SyntaxError|NameError|ImportError|AssertionError|assert|Traceback).*',
        re.IGNORECASE
    )
    key = [ln + "\n" for ln in eval_output.splitlines() if pattern.search(ln)]
    return key[:max_lines]
```

**智慧 /compact（結構化壓縮提示）**：

```python
def _send_compact(self, is_first: bool) -> None:
    if is_first:
        return
    # 傳遞結構化提示，告知 Claude Code 壓縮時優先保留哪些資訊
    compact_prompt = (
        "/compact\n"
        "請在壓縮時優先保留：\n"
        "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
        "2. 測試案例的名稱與期望行為\n"
        "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
        "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
    )
    self._execute_prompt(
        prompt=compact_prompt,
        maintain_context=True,
        timeout=60,
        step_label="compact",
    )
```

---

### 2.3 結構化記憶體快照（Memory Dump for Human Handover）

**設計目標**：ESCALATION 或 ESC+F12 時，儲存足夠讓人類快速接手的結構化快照。

**新增 EscalationDump 資料模型**：

```python
# autoclaude/models/escalation.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class EscalationDump:
    """ESCALATION 或強制中斷時儲存的完整診斷快照。"""
    playbook_path: str
    step_id: str
    step_name: str
    total_attempts: int
    failure_chain: list[dict]       # [{attempt, failure_reason, error_signature, minimax_reasoning}]
    final_eval_output: str
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    saved_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    human_hint: str = ""            # 給人類的建議行動

    def to_markdown(self) -> str:
        lines = [
            f"# AutoClaude Escalation Dump",
            f"**步驟**: {self.step_id} — {self.step_name}",
            f"**時間**: {self.saved_at}",
            f"**重試次數**: {self.total_attempts}",
            f"",
            f"## 失敗鏈",
        ]
        for rec in self.failure_chain:
            lines.append(
                f"- Attempt {rec['attempt']}: `{rec['error_signature'][:100]}`"
                f"\n  Minimax 決策: {rec['minimax_reasoning']}"
            )
        lines += [
            f"",
            f"## 最後評估輸出",
            f"```",
            self.final_eval_output[:3000],
            f"```",
            f"",
            f"## 自動診斷",
            f"- 錯誤卡死（特徵相同）: {'✅ 是' if self.is_stuck else '❌ 否'}",
            f"- 錯誤發散（越改越壞）: {'✅ 是' if self.is_diverging else '❌ 否'}",
            f"- 疑似測試檔本身有誤: {'✅ 是' if self.suspect_test_file else '❌ 否'}",
            f"",
            f"## 建議行動",
            f"{self.human_hint or '請檢查上方失敗鏈，優先確認測試檔是否有獨立錯誤。'}",
        ]
        return "\n".join(lines)
```

**ESC+F12 中斷也儲存 checkpoint**（修補現有缺口）：

```python
# 在 _run_steps 的 hotkey 檢查中：
if self._hotkey.triggered:
    # 儲存中斷點（讓使用者可以 --continue 而非從頭）
    cp = PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=step_idx,
        step_id=task.step_id,
        total_steps=total,
        project=playbook.project,
        completed_step_log=list(step_log),
    )
    self._checkpoint_mgr.save(cp, playbook_path)
    return PlaybookResult(False, len(step_log), total, "使用者 ESC+F12 中斷（已儲存中斷點）", ...)
```

---

## 三、Level 5 自治開發系統升級藍圖

### 3.1 Level 定義對照

| Level | 特徵 | 現狀 |
|-------|------|------|
| L1 | 人工執行每個指令 | 已超越 |
| L2 | 腳本自動化，人工監控 | 已超越 |
| L3 | 狀態機執行 + 異常通知 | **目前位置** |
| L4 | 自主修復 + 根因分析 + 智慧 /compact | 本文升級目標 |
| L5 | 自我演化 Playbook + 多代理協作 + 自適應策略 | 終極藍圖 |

### 3.2 L3 → L4 升級路徑（可立即實施）

```
優先級 P0（修補安全缺口）：
  ✅ ESC+F12 中斷時儲存 checkpoint
  ✅ ESCALATION 產出 EscalationDump（Markdown 格式）
  ✅ 測試檔錯誤偵測（suspect_test_file_error）→ 提前 ESCALATION

優先級 P1（收斂度品質）：
  ✅ FailureTracker 跨 attempt 追蹤
  ✅ is_stuck / is_diverging 偵測 → 提前退出
  ✅ prompt_builder 加入 history_summary + 關鍵行萃取

優先級 P2（Context 品質）：
  ✅ 智慧 /compact（帶結構化壓縮提示）
  ✅ eval_output 傳入 Minimax 前先 _extract_key_error_lines
```

### 3.3 L4 → L5 架構（中長期）

**自我演化 Playbook（Meta-Playbook）**

```
PlaybookOptimizer（新模組）：
  - 每次 ESCALATION 後，分析失敗的 step
  - 自動產出「分解版 Playbook」：把一個大 step 拆成多個更小的驗證步驟
  - 例：T03（實作並通過測試）→ T03a（只建立檔案框架）→ T03b（通過第一個 test case）→ ...
```

**多代理診斷架構**

```
現在：單一 Minimax 負責修正決策
升級：
  Agent A（Minimax）：提出修正方案
  Agent B（另一個 LLM 端點）：對 Agent A 的方案進行批評（"critic"）
  → 只有通過批評的方案才送給 Claude Code
  → 防止 Minimax 幻覺
```

**自適應重試策略**

```python
class AdaptiveRetryStrategy:
    """根據歷史失敗模式調整重試策略。"""

    def next_action(self, tracker: FailureTracker) -> str:
        if tracker.suspect_test_file_error():
            return "ESCALATE_TEST_FILE"   # 直接升級，不浪費 token
        if tracker.is_stuck():
            return "RESET_CONTEXT"        # 送 /clear 重置 context 後重試
        if tracker.is_diverging():
            return "ROLLBACK_STEP"        # 回到上一個成功 step 重新開始
        return "CONTINUE_CORRECTION"      # 正常 Minimax 修正
```

**結構化 Memory Dump 整合 CI**

```yaml
# .github/workflows/autoclaude_escalation.yml
on:
  push:
    paths: 'checkpoints/escalation_*.md'
jobs:
  notify:
    steps:
      - name: 解析 Escalation Dump
        run: python tools/parse_escalation_dump.py
      - name: 建立 GitHub Issue
        uses: actions/github-script@v6
        # 自動建立 Issue，附帶 Dump 內容，標記 needs-human-review
```

---

## 四、實施優先順序與工作量估計

| 項目 | 優先級 | 影響 | 預估工作量 |
|------|--------|------|-----------|
| ESC+F12 儲存 checkpoint | P0 | 防止使用者中斷後失去進度 | 0.5h |
| EscalationDump Markdown 快照 | P0 | 人類接手時有完整脈絡 | 2h |
| FailureTracker（is_stuck + suspect_test_file） | P1 | 防止無用重試，節省大量 Token | 3h |
| prompt_builder 關鍵行萃取 + history_summary | P1 | 提升 Minimax 決策品質 | 2h |
| 智慧 /compact（帶結構化提示） | P2 | 壓縮後 context 品質更好 | 1h |
| AdaptiveRetryStrategy | P3 | L4 自適應重試 | 4h |
| PlaybookOptimizer（Meta-Playbook） | P4 | L5 自我演化 | 8h+ |

---

## 五、模擬推演驗證

**情境**：`evaluator_command: "pytest tests/test_foo.py"` 但 `test_foo.py` 有語法錯誤。

**升級後的流程**：

```
Attempt 1: pytest 回傳 SyntaxError: invalid syntax (test_foo.py:15)
  → FailureTracker.record(0, failure_reason, eval_output, exit_code=2)
  → suspect_test_file_error() = False（只有 1 次，threshold 未達）
  → CORRECTION：Minimax 收到關鍵行萃取版（僅 SyntaxError 那行）
  → correction_prompt 產出，送 Claude Code 嘗試「修正實作」

Attempt 2: pytest 回傳同樣的 SyntaxError（因為測試檔沒變）
  → FailureTracker.record(1, ...)
  → is_stuck() = True（error_signature 連續 2 次相同）
  → suspect_test_file_error() = True（兩次都指向 test_foo.py，無實作檔錯誤）

  → 觸發提前 ESCALATION（不等 max_retries 耗盡）
  → EscalationDump 寫入：
    - suspect_test_file: ✅ 是
    - human_hint: "請先在 AutoClaude 之外單獨執行 pytest tests/test_foo.py
                   確認測試檔本身可以被 import，再重跑 Playbook"
  → 桌面通知：「[T03] 疑似測試檔語法錯誤，請人工確認」
```

**結果**：第 2 次重試後即識別根因並提前升級，節省 1 次無效 Minimax 呼叫 + 1 次無效 Claude Code 執行，且提供精確的人類接手指引。

---

## 六、下一步行動（Next Action）

1. **實作 FailureTracker**（`autoclaude/execution/failure_tracker.py`）並整合進 `_run_steps`
2. **新增 EscalationDump**（`autoclaude/models/escalation.py`）並在 ESCALATION / ESC+F12 時呼叫
3. **升級 prompt_builder**（加入 `_extract_key_error_lines` + `history_summary` 參數）
4. **升級 `_send_compact`**（帶結構化壓縮提示）
5. **補測試**：`test_failure_tracker.py`（驗證 is_stuck / suspect_test_file 邊界案例）

---

*文檔版本*: v1.0 | *狀態*: Active | *下次審查*: 實作 P0/P1 後更新
