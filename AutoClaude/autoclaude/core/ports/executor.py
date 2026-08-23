"""IExecutor — 執行 Claude Code（或 dummy CLI）並收集輸出的 Port。

對應 SD_Improving_01.md v1.1 §3.4 / SD_Improving_02.md v1.1 §1.2 /
SD_Improving_06 W1 T1-2（ExecutionEvent + on_event + send_interrupt）。

實作（Phase 1）：
  - autoclaude.infra.adapters.pty_executor.PtyExecutor — 真實 PTY 執行
  - autoclaude.infra.adapters.dry_run_executor.DryRunExecutor — 測試夾具

未來（Phase 2+）：
  - PlaybookKernel 透過 IExecutor.execute(...) 呼叫，不再直接持有 PtyWrapper
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ExecutionOutput:
    """IExecutor.execute 的回傳值。

    刻意精簡（不含 token guard 結果），token 偵測由 Phase 3 的 TokenGuardPlugin
    透過訂閱 ON_TOKEN_USAGE phase 處理。Phase 1 ~ Phase 2 期間，token guard 仍
    保留在 PlaybookRunner._execute_prompt 內（Frozen Surface）。
    """
    text: str
    exit_code: int = 0
    completed: bool = True   # False = 因 hotkey / timeout / CLI 拒工中斷
    # R100 P2-C（PRD §8-1 的 AutoClaude 半）：非空＝執行器在**自己的輸出裡**看到撞額度／
    # 限流跡證，該次執行沒有做到工。值＝要交給上游的 failure_reason（產生器＝
    # core/ports/quota_meter.quota_refusal()，判準一個家）。
    # 🔴 為什麼要一個欄位、而不是讓上游自己再判一次輸出：json 模式下 `text` 已被換成
    # `parsed["result"]`，撞線訊息只在**原始** stdout 裡 ⇒ 上游再判會判到一個不含證據的
    # 字串（假綠）。加欄位而非改 `completed` 的語意：`completed=False` 現有三個成因
    # （hotkey／timeout／啟動失敗），上游要分得出「是不是撞線」才決定該 halt 還是重試。
    quota_refusal: str = ""


# ──────────────────────────────────────────────────────────────
# SD_Improving_06 W1 T1-2：ExecutionEvent + EventKind
# 對應 ADR-SD06-001 §6.3 五種事件種類定案：
#   progress / partial_output / tool_use / token_pct / completion
# completion 為 QA 強制要求（避免 AFTER_EXEC 漏失終態）
# ──────────────────────────────────────────────────────────────
class ExecutionEventKind:
    """ExecutionEvent.kind 合法值（class 常數模式，避免 enum import 成本）。"""
    PROGRESS = "progress"
    PARTIAL_OUTPUT = "partial_output"
    TOOL_USE = "tool_use"
    TOKEN_PCT = "token_pct"
    COMPLETION = "completion"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.PROGRESS,
            cls.PARTIAL_OUTPUT,
            cls.TOOL_USE,
            cls.TOKEN_PCT,
            cls.COMPLETION,
        )


@dataclass(frozen=True)
class ExecutionEvent:
    """Executor 在執行過程中向 Coordinator 廣播的事件。

    透過 IExecutor.execute(..., on_event=callback) 傳入；Coordinator 收到後
    emit 為 EventBus ON_EVENT phase（ADR §6.4 R3：不可直接 callback Brain）。

    payload 結構建議：
      progress       : {"step": int, "total": int}
      partial_output : {"text": str}
      tool_use       : {"tool": str, "args": dict}
      token_pct      : {"pct": float}
      completion     : {"exit_code": int, "completed": bool, "text_len": int}
    """
    kind: str
    payload: dict = field(default_factory=dict)
    sequence: int = 0  # 單次 execute 內遞增，供 Coordinator 排序 / 防 ACK 重複


# Callback 型別別名（IExecutor.execute 的 on_event 參數）
ExecutionEventCallback = Callable[[ExecutionEvent], None]


class IExecutor(Protocol):
    """執行單一 prompt 並收集輸出的契約。

    SD_Improving_06 W1 T1-2 擴張：
      - execute() 新增 on_event=callback（可選；Phase 1 adapter 可全部不 emit）
      - send_interrupt() 新增；ACK 機制由 Coordinator 透過 ON_INTERRUPT_REQUEST event 仲裁
    """

    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
        on_event: ExecutionEventCallback | None = None,
    ) -> ExecutionOutput:
        """送出 prompt 給底層 CLI，回傳完整輸出。

        Args:
            prompt: 給 Claude Code 的 prompt 文字
            maintain_context: 是否傳遞 --continue（維持對話脈絡）
            timeout: 單次執行最大秒數
            label: log 檔名標籤（如 step_id）
            on_event: 可選 callback；adapter 收到 progress/partial_output/tool_use/
                      token_pct/completion 等事件時呼叫；Coordinator 在 EXEC phase
                      內以 lambda 封裝以將事件改 emit 為 EventBus 訊息。
                      ⚠️ adapter 不可直接 import Brain 或 Coordinator；callback 是
                      唯一允許的反向通道（仍受 ADR R3 brain-executor-isolation 規範）。

        Returns:
            ExecutionOutput 含完整輸出文字、exit_code、是否完整完成
        """
        ...

    def send_interrupt(self, reason: str = "") -> bool:
        """請求中斷當前正在執行的 prompt。

        ADR-SD06-001 §6.4 決策：走 EventBus 由 Coordinator emit
        ON_INTERRUPT_REQUEST event，adapter 訂閱並執行實際 PTY/process 訊號。
        本方法為 Coordinator 內部呼叫；外部 Plugin 不可直接呼叫。

        ACK 機制：Coordinator 採 asyncio.Event + sequence number 序列化，
        防止重複觸發或亂序。

        Args:
            reason: 中斷理由（記入 log，如 "token_halt" / "hotkey_esc_f12"）

        Returns:
            True = 中斷請求已送達且 adapter 已開始處理；
            False = 當下無進行中的 execute（no-op）；
        """
        ...
