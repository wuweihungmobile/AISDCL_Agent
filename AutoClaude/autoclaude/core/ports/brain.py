"""IBrain — Minimax 決策（修正 / 演化）的 Port。

對應 SD_Improving_01.md v1.1 §3.4 / SD_Improving_02.md v1.1 §1.2 /
SD_Improving_06 W1 T1-1（capabilities + decide_escalation 擴張）。

實作（Phase 1）：
  - autoclaude.infra.adapters.minimax_brain.MinimaxBrainAdapter
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from ...models.step_mutation import StepMutation


@dataclass(frozen=True)
class CorrectionResult:
    """IBrain.decide_correction 的回傳值。對齊 PlaybookRunner._get_correction 四元組。"""
    correction_prompt: str
    reasoning: str
    task_goal_summary: Optional[str] = None
    step_mutation: Optional[StepMutation] = None


# ──────────────────────────────────────────────────────────────
# SD_Improving_06 W1 T1-1：BrainCapabilities + RetryPolicy + EscalationDecision
# 對應 ADR-SD06-001 §6.2 五欄定案 + §6.3 escalation 決策出口
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RetryPolicy:
    """Brain 自報重試策略，供 Coordinator 在 BEFORE_DECIDE phase 讀取以調整外層 retry。"""
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    jitter: bool = True


@dataclass(frozen=True)
class BrainCapabilities:
    """Brain 自報能力（ADR-SD06-001 §6.2 五欄定案）。

    欄位語意：
      max_context_tokens : 模型 context 上限（含 system + tool 輸出）
      supports_streaming : 是否支援 partial_output stream
      retry_policy       : Brain 自定義的 retry 行為，Coordinator 不可覆寫，只能整合
      model_id           : SA 補欄；對齊 §3.1 model registry / PG-backed 配置
      dimension          : SD 補欄；對齊 SD_06 W3 embedding 欄寬（1024 / 1536 dual-read 期間）
    """
    max_context_tokens: int
    supports_streaming: bool
    retry_policy: RetryPolicy
    model_id: str
    dimension: int


@dataclass(frozen=True)
class EscalationDecision:
    """IBrain.decide_escalation 回傳值。

    Coordinator 於 EscalationDumper 觸發前諮詢 Brain；Brain 可建議：
      - human_handoff=True   →  立刻通知並停止演化
      - retry_with_hint      →  Coordinator 改 retry（提供 reasoning + hint）
      - propose_mutation     →  改走 step_mutation 路徑
    """
    human_handoff: bool
    reasoning: str
    retry_hint: Optional[str] = None
    proposed_mutation: Optional[StepMutation] = None
    extra: dict = field(default_factory=dict)


class IBrain(Protocol):
    """Minimax / LLM 決策的契約。

    SD_Improving_06 W1 T1-1：補 capabilities() + decide_escalation()
    （Architect R-SD06-0-1 緩解：BrainPort 不再過於貧瘠）。
    """

    def capabilities(self) -> BrainCapabilities:
        """Brain 自報能力（同步呼叫，必須無副作用）。

        Coordinator 於 BEFORE_DECIDE phase 讀取以調整 retry / streaming 行為。
        """
        ...

    def decide_correction(
        self,
        *,
        task,
        failure_reason: str,
        eval_output: str,
        attempt: int,
        history_summary: str = "",
        last_correction_prompt: str = "",
        convergence_trend: str = "",
        convergence_reasoning: str = "",
        strategy_hint: str = "",
        error_class: str = "unknown",
        task_goal_summary: Optional[str] = None,
        global_goal: Optional[str] = None,
        allow_step_mutation: bool = False,
        mutation_history: Optional[list[str]] = None,
        mutation_pressure: int = 0,
    ) -> Optional[CorrectionResult]:
        """諮詢 LLM 取得修正策略。

        Returns:
            CorrectionResult（成功）或 None（API 故障）
        """
        ...

    def decide_escalation(
        self,
        *,
        task,
        failure_history: list[dict],
        convergence_trend: str,
        last_correction_prompt: str = "",
        global_goal: Optional[str] = None,
    ) -> EscalationDecision:
        """ESCALATION 觸發前的最終判斷。

        Coordinator 在 EscalationDumper 之前先諮詢 Brain；Brain 可建議
        是否真要 escalate 或改 retry / mutation 路徑。
        """
        ...
