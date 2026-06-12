"""MinimaxBrainAdapter — IBrain 的 Minimax 實作（Phase 1）。

職責：
  - 將 PlaybookTask 物件展開為 MinimaxClient.decide_correction 所需的多個 kwargs
  - 將 CorrectionDecision 轉換為 IBrain 介面的 CorrectionResult
  - API 故障時回傳 None（不拋例外，由呼叫端決定 fallback）
"""
from __future__ import annotations

from ...core.ports.brain import (
    BrainCapabilities,
    CorrectionResult,
    EscalationDecision,
    RetryPolicy,
)
from ...decision.minimax_client import MinimaxClient, MinimaxError
from ...models.playbook import PlaybookTask


class MinimaxBrainAdapter:
    """以 MinimaxClient 為後端的 IBrain 實作。"""

    # SD_Improving_06 W1 T1-1：BrainCapabilities 預設值
    # max_context_tokens：Minimax abab6.5/abab7 普遍上限（保守取 245760，留 buffer）
    # dimension：對齊 SD_06 W3 default embedding 維度（BGE-M3=1024）
    _DEFAULT_MAX_CONTEXT_TOKENS = 245760
    _DEFAULT_DIMENSION = 1024

    def __init__(self, client: MinimaxClient):
        self._client = client

    def capabilities(self) -> BrainCapabilities:
        """回報 Brain 自身能力（ADR-SD06-001 §6.2 五欄）。"""
        return BrainCapabilities(
            max_context_tokens=self._DEFAULT_MAX_CONTEXT_TOKENS,
            supports_streaming=False,  # MinimaxClient 同步呼叫，不走 stream
            retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=2.0, jitter=True),
            model_id=getattr(self._client, "_model", "minimax-unknown"),
            dimension=self._DEFAULT_DIMENSION,
        )

    def decide_escalation(
        self,
        *,
        task: PlaybookTask,
        failure_history: list[dict],
        convergence_trend: str,
        last_correction_prompt: str = "",
        global_goal: str | None = None,
    ) -> EscalationDecision:
        """ESCALATION 前的最終判斷（Phase 1 預設：human_handoff）。

        Phase 1 採保守策略：直接交人工，理由說明依 convergence_trend 推導。
        Phase 2 將擴張為呼叫 MinimaxClient.decide_escalation（W3+）。
        """
        reasoning = (
            f"convergence_trend={convergence_trend or 'unknown'}；"
            f"failure_count={len(failure_history)}；"
            "Phase 1 預設交人工處理"
        )
        return EscalationDecision(
            human_handoff=True,
            reasoning=reasoning,
            retry_hint=None,
            proposed_mutation=None,
        )

    def decide_correction(
        self,
        *,
        task: PlaybookTask,
        failure_reason: str,
        eval_output: str,
        attempt: int,
        history_summary: str = "",
        last_correction_prompt: str = "",
        convergence_trend: str = "",
        convergence_reasoning: str = "",
        strategy_hint: str = "",
        error_class: str = "unknown",
        task_goal_summary: str | None = None,
        global_goal: str | None = None,
        allow_step_mutation: bool = False,
        mutation_history: list[str] | None = None,
        mutation_pressure: int = 0,
        preferences_section: str = "",
    ) -> CorrectionResult | None:
        try:
            decision = self._client.decide_correction(
                step_id=task.step_id,
                task_name=task.name,
                task_prompt=task.prompt,
                expected_regex=task.expected_output_regex,
                failure_reason=failure_reason,
                eval_output=eval_output,
                retry_count=attempt + 1,  # 與 _runner_impl._get_correction() 語意對齊（MIGRATED）
                history_summary=history_summary,
                convergence_trend=convergence_trend,
                convergence_reasoning=convergence_reasoning,
                strategy_hint=strategy_hint,
                error_class=error_class,
                last_correction_prompt=last_correction_prompt,
                task_goal_summary=task_goal_summary,
                global_goal=global_goal,
                allow_step_mutation=allow_step_mutation,
                mutation_history=mutation_history or [],
                mutation_pressure=mutation_pressure,
                preferences_section=preferences_section,  # F-C1
            )
        except MinimaxError:
            return None

        return CorrectionResult(
            correction_prompt=decision.correction_prompt,
            reasoning=decision.reasoning,
            task_goal_summary=getattr(decision, "task_goal_summary", None),
            step_mutation=getattr(decision, "step_mutation", None),
        )
