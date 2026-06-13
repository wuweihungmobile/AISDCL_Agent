"""
CorrectionVerifier — F-B2 Correction 效果事後驗證（Improving_012 Phase 2，ADR-AGT-004）。

mutation / correction 套用後，以**純本地比對**（不呼叫 Brain）檢查下一 attempt
是否改善：error_signature 改變 OR fail_count 下降 OR exit_code 下降 任一成立
即視為改善（SRD_AGT_Phase2_Closedloop §2.2）。

無改善 → no_improve_streak += 1 並回寫 KB 策略失效標記（record_strategy_failure，
常開、additive、不影響控制流）；有改善 → streak 歸零。
streak 達門檻時由 AlertLadder.intercept() 的 bypass 2 觸發提前升級（flag on 時）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .failure_tracker import FailureTracker

if TYPE_CHECKING:
    from .alert_ladder import AlertLadder

logger = logging.getLogger("autoclaude.execution.correction_verifier")


@dataclass
class EffectReport:
    """assess() 回傳值。applicable=False 表示前筆無修正可歸因（不計 streak）。"""
    applicable: bool
    improved: bool = False
    reason: str = ""


class CorrectionVerifier:
    """單次修正效果歸因（與 ConvergenceMonitor 的「趨勢判定」職責分離）。"""

    @staticmethod
    def assess(tracker: FailureTracker) -> EffectReport:
        """比較 tracker 最後兩筆 AttemptRecord 的修正效果。

        前提：前筆確曾施加修正（correction_prompt_sent 非空或 mutation_applied），
        否則本次失敗無法歸因於任何修正 → applicable=False。
        """
        if len(tracker.history) < 2:
            return EffectReport(applicable=False, reason="不足兩筆 attempt")
        prev, curr = tracker.history[-2], tracker.history[-1]
        if not prev.correction_prompt_sent and not prev.mutation_applied:
            return EffectReport(applicable=False, reason="前筆未施加修正")

        if curr.error_signature != prev.error_signature:
            return EffectReport(True, True, "error_signature 改變")

        prev_fc = FailureTracker._extract_fail_count_from_output(prev.eval_output)
        curr_fc = FailureTracker._extract_fail_count_from_output(curr.eval_output)
        if prev_fc is not None and curr_fc is not None and curr_fc < prev_fc:
            return EffectReport(True, True, f"fail_count 下降 {prev_fc}→{curr_fc}")

        if curr.exit_code < prev.exit_code:
            return EffectReport(
                True, True, f"exit_code 下降 {prev.exit_code}→{curr.exit_code}"
            )

        return EffectReport(
            True, False,
            f"同 signature 且 fail_count/exit_code 無下降（sig={curr.error_signature[:60]}）",
        )


def verify_and_update(
    *,
    tracker: FailureTracker,
    ladder: AlertLadder,
    knowledge_base,
    step_id: str,
    error_class: str,
    last_strategy: str,
) -> int:
    """F-B2 編排入口：效果評估 → streak 更新 → KB 失效回寫。

    Returns:
        更新後的 no_improve_streak（供 AlertLadder.intercept bypass 2 判定）。
    """
    effect = CorrectionVerifier.assess(tracker)
    if not effect.applicable:
        return ladder.get_no_improve_streak(step_id)

    if effect.improved:
        ladder.set_no_improve_streak(step_id, 0)
        logger.info(
            "=== F-B2 | [%s] 修正有效（%s），streak 歸零 ===", step_id, effect.reason,
        )
        return 0

    streak = ladder.get_no_improve_streak(step_id) + 1
    ladder.set_no_improve_streak(step_id, streak)
    logger.warning(
        "=== F-B2 | [%s] 修正無改善（%s），no_improve_streak=%d ===",
        step_id, effect.reason, streak,
    )
    # KB 失效回寫（常開、additive；控制流不變）
    kb_key = f"{error_class}:{tracker.history[-1].error_signature[:60]}"
    try:
        knowledge_base.record_strategy_failure(kb_key, last_strategy, step_id)
    except Exception as exc:  # KB 故障不可阻斷主流程（與既有 KB 寫入容錯一致）
        logger.warning("F-B2 KB 失效回寫失敗（warning，繼續主流程）: %s", exc)
    return streak
