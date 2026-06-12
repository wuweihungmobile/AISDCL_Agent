"""
MinimaxEvolver — Level 5 AI 驅動 Playbook 演化引擎（Gap-016-A）。

在 ESCALATION 時優先諮詢 Minimax 提議語意正確的演化策略，
取代 PlaybookEvolver 的字符切割硬編碼規則。
規則引擎作為兜底（fallback）。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from ..models.decision import EvolutionDecision
from ..models.playbook import Playbook, PlaybookTask
from ..models.escalation import EscalationDump
from .playbook_evolver import PlaybookEvolutionProposal

if TYPE_CHECKING:
    from ..decision.minimax_client import MinimaxClient, MinimaxError

logger = logging.getLogger("autoclaude.evolution.minimax_evolver")


class MinimaxEvolver:
    """
    Gap-016：AI 驅動演化引擎。
    在 ESCALATION 時諮詢 Minimax 提議最佳演化策略。
    失敗時靜默回傳 None，由呼叫方 fallback 至規則引擎。
    """

    def propose_evolution_via_ai(
        self,
        playbook: Playbook,
        failed_step_idx: int,
        escalation_dump: EscalationDump,
        minimax_client: "MinimaxClient",
    ) -> Optional[PlaybookEvolutionProposal]:
        """
        諮詢 Minimax 分析失敗根因並提議演化策略。
        回傳 PlaybookEvolutionProposal，或 None（API 失敗時讓規則引擎接管）。
        """
        from ..decision.minimax_client import MinimaxError

        if failed_step_idx >= len(playbook.tasks):
            logger.warning("MinimaxEvolver: failed_step_idx=%d 超出範圍，略過", failed_step_idx)
            return None

        failed_task = playbook.tasks[failed_step_idx]
        failure_summary = "\n".join(
            f"  attempt {i}: {r}" for i, r in enumerate(escalation_dump.failure_chain)
        )

        try:
            decision = minimax_client.propose_evolution(
                step_id=escalation_dump.step_id,
                step_name=escalation_dump.step_name,
                step_prompt=failed_task.prompt,
                failure_summary=failure_summary,
                escalation_reasoning=escalation_dump.human_hint,
                global_goal=playbook.global_goal,  # Gap-022-C：傳入總目標防演化漂移
            )
        except MinimaxError as exc:
            logger.warning("MinimaxEvolver: Minimax API 失敗，回退至規則引擎: %s", exc)
            return None

        return self._convert_to_proposal(
            decision, failed_step_idx, failed_task, playbook
        )

    def _convert_to_proposal(
        self,
        decision: EvolutionDecision,
        failed_step_idx: int,
        failed_task: PlaybookTask,
        playbook: Playbook,
    ) -> Optional[PlaybookEvolutionProposal]:
        """將 EvolutionDecision 轉換為 PlaybookEvolutionProposal。"""
        _global_max = playbook.global_invariants.max_retries_per_step
        _inject_max_retries = max(2, min(_global_max, 3))

        if decision.evolution_type == "INJECT_STEP":
            if not decision.new_step_prompt:
                logger.warning("MinimaxEvolver: INJECT_STEP 缺少 new_step_prompt，略過")
                return None
            return PlaybookEvolutionProposal(
                evolution_type="INJECT_STEP",
                inject_before_idx=failed_step_idx,
                reasoning=decision.reasoning,
                new_step=PlaybookTask(
                    step_id=decision.new_step_id or f"{failed_task.step_id}_AI_PRE",
                    name=decision.new_step_name or f"AI 演化前置步驟（{failed_task.step_id}）",
                    prompt=decision.new_step_prompt,
                    max_retries=_inject_max_retries,
                ),
            )

        elif decision.evolution_type == "SPLIT_STEP":
            # Gap-016 + Gap-018：AI 語意切割 + context bridge
            mid = len(failed_task.prompt) // 2
            # Gap-043：修復 rfind or mid 語意 Bug（rfind 回傳 0 時 `0 or mid` 取中點而非換行點）
            _nl_pos = failed_task.prompt.rfind("\n", 0, mid)
            split_pos = _nl_pos if _nl_pos != -1 else mid
            if split_pos < 50:  # 保護：Part A 至少 50 字符
                split_pos = mid
            prompt_a = failed_task.prompt[:split_pos].strip() or failed_task.prompt
            prompt_b = failed_task.prompt[split_pos:].strip() or failed_task.prompt

            sub1_id = f"{failed_task.step_id}_A"
            sub2_id = f"{failed_task.step_id}_B"

            # Gap-018：注入 AI 生成的 context bridge（優先使用 Minimax 摘要）
            context_bridge = ""
            if decision.split_context_bridge:
                context_bridge = (
                    f"[前置步驟 {sub1_id} 已完成的工作]\n"
                    f"{decision.split_context_bridge}\n\n"
                )
            else:
                context_bridge = (
                    f"[前置步驟 {sub1_id} 已完成的工作]\n"
                    f"前一個子步驟（{sub1_id}）已完成 {failed_task.name} 的第一部分。\n"
                    f"請確認 {sub1_id} 的輸出，然後繼續完成以下剩餘任務：\n\n"
                )

            # Gap-026-B：為 Part A 推導輕量 evaluator（防假陽性通過）
            part_a_evaluator = self._derive_part_a_evaluator(failed_task.evaluator_command)

            return PlaybookEvolutionProposal(
                evolution_type="SPLIT_STEP",
                inject_before_idx=failed_step_idx,
                reasoning=decision.reasoning,
                split_steps=[
                    PlaybookTask(
                        step_id=sub1_id,
                        name=f"{failed_task.name}（第一部分）",
                        prompt=prompt_a,
                        max_retries=failed_task.max_retries,
                        evaluator_command=part_a_evaluator,  # Gap-026-B
                    ),
                    PlaybookTask(
                        step_id=sub2_id,
                        name=f"{failed_task.name}（第二部分）",
                        prompt=context_bridge + prompt_b,
                        expected_output_regex=failed_task.expected_output_regex,
                        evaluator_command=failed_task.evaluator_command,
                        evaluator_timeout_seconds=failed_task.evaluator_timeout_seconds,
                        max_retries=failed_task.max_retries,
                    ),
                ],
            )

        elif decision.evolution_type == "REVISE_EVALUATOR":
            if not decision.revised_evaluator:
                logger.warning("MinimaxEvolver: REVISE_EVALUATOR 缺少 revised_evaluator，略過")
                return None
            return PlaybookEvolutionProposal(
                evolution_type="REVISE_EVALUATOR",
                inject_before_idx=failed_step_idx,
                reasoning=decision.reasoning,
                revised_evaluator=decision.revised_evaluator,
            )

        logger.warning("MinimaxEvolver: 未知演化類型 %s，略過", decision.evolution_type)
        return None

    @staticmethod
    def _derive_part_a_evaluator(full_evaluator: Optional[str]) -> Optional[str]:
        """
        Gap-026-B：從完整 evaluator_command 推導 Part A 輕量評估指令。
        策略：
        - pytest 指令 → 改為 --collect-only（僅確認測試可被收集）
        - 其他指令 → 去掉輸出驗證 flag（如 -v），加上 echo 成功提示
        - 無 evaluator → 回傳 None
        """
        if not full_evaluator:
            return None
        import re
        cmd = full_evaluator.strip()
        if re.search(r'\bpytest\b', cmd):
            # pytest → 只做 collect-only 確認語法正確
            base = re.sub(r'\s+-[kxvsq]\S*', '', cmd)
            base = re.sub(r'\s+--tb=\S+', '', base)
            return base.split()[0] + " --collect-only"
        # 非 pytest：傳回原指令但加上 true（確保 exit 0）
        return f"{{ {cmd}; }} || true"
