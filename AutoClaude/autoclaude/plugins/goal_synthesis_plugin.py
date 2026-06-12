"""GoalSynthesisPlugin — 取代 PlaybookRunner._validate_global_goal_achievement +
GOAL_SYNTHESIS 步驟注入（Gap-014-B / 023-C / 030 / 040）。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 12 列（priority=50）
  - SD_Improving_02.md v1.1 §2.5 W11 #12（極高風險，去除 _run_steps 行 660+813 重複）

SD_Improving_05 W4-4：吸收以下 4 個 mixin 方法（與既有 POST_RUN 訂閱合併）：
  - validate_global_goal_achievement   原 PlaybookRunner._validate_global_goal_achievement
  - build_achievement_summary          原 PlaybookRunner._build_achievement_summary（靜態）
  - prepend_global_goal                原 PlaybookRunner._prepend_global_goal（完整版）
  - prepend_global_goal_brief          原 _runner_compat._prepend_global_goal_brief（精簡版）

訂閱 phase：
  - POST_RUN  → 諮詢 Minimax 驗證 global_goal 是否達成；未達成則回傳 MutationProposal(INJECT_AFTER)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, MutationProposal
from ..models.playbook import PlaybookTask
from ..models.step_mutation import StepMutation, StepMutationType

logger = logging.getLogger("autoclaude.plugins.goal_synthesis")


class GoalSynthesisPlugin:
    """GOAL_SYNTHESIS 補完 Plugin（DONE 前驗證全局目標達成）。"""

    PRIORITY = 50

    def __init__(
        self,
        minimax_client: Optional[Any] = None,
        enabled: bool = True,
        max_summary_recent: int = 10,
    ):
        self._client = minimax_client
        self._enabled = enabled
        self._max_recent = max_summary_recent
        self._latest_decision = None  # 供測試 / 觀察

    def name(self) -> str:
        return "goal_synthesis"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_RUN]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if not self._enabled or self._client is None:
            return None
        playbook = ctx.playbook
        if not playbook.global_goal:
            return None  # 無 global_goal 不驗證
        payload = ctx.payload or {}
        step_log = list(payload.get("step_log", []))

        result = self._validate(playbook, step_log)
        if result is None:
            return None  # 達成
        completion_prompt, suggested_evaluator = result

        # 注入 GOAL_SYNTHESIS 補完步驟
        mutation = StepMutation(
            mutation_type=StepMutationType.INJECT_AFTER,
            new_step_id="T_GOAL_SYNTH",
            new_step_name="GOAL_SYNTHESIS 補完",
            new_step_prompt=completion_prompt,
            new_step_evaluator_command=suggested_evaluator,
            reasoning="global_goal 未達成 → 注入補完步驟",
        )
        return MutationProposal(
            contributor=self.name(),
            mutation=mutation,
            rationale="goal_not_achieved",
        )

    # ──────────────────────────────────────────────
    # 公開 API（SD_05 W4-4 吸收 mixin 4 方法）
    # ──────────────────────────────────────────────
    def latest_decision(self):
        return self._latest_decision

    @staticmethod
    def build_achievement_summary(step_log: list[str], max_recent: int = 10) -> str:
        """Gap-040：超過 20 步時保留結構化標頭 + 最後 N 筆。

        SD_05 W4-4：吸收原 `PlaybookRunner._build_achievement_summary`。
        """
        total = len(step_log)
        if total <= 20:
            return "\n".join(step_log)
        recent = step_log[-max_recent:]
        earlier_count = total - len(recent)
        earlier_summary = (
            f"[前 {earlier_count} 個步驟已完成，以下為最後 {max_recent} 個步驟的詳細記錄]"
        )
        return earlier_summary + "\n" + "\n".join(recent)

    @staticmethod
    def prepend_global_goal(prompt: str, global_goal: Optional[str]) -> str:
        """Gap-013-F：完整版 global_goal 前置注入（首次 Prompt）。

        SD_05 W4-4：吸收原 `PlaybookRunner._prepend_global_goal`。
        """
        if not global_goal:
            return prompt
        goal_header = (
            "=== 本次自動化任務的總目標 ===\n"
            f"{global_goal[:500]}\n"
            "以上為整體目標供你參考，請確保每個步驟的實作決策與此目標方向一致。\n"
            "===========================\n\n"
        )
        return goal_header + prompt

    @staticmethod
    def prepend_global_goal_brief(
        prompt: str, global_goal: Optional[str], cfg: Optional[Any] = None,
    ) -> str:
        """Gap-015-A：精簡版 global_goal 前置（最大 global_goal_brief_chars 字元）。

        SD_05 W4-4：吸收原 `_runner_compat._prepend_global_goal_brief`。
        """
        if not global_goal:
            return prompt
        brief_chars = 100
        if cfg is not None:
            brief_chars = getattr(
                getattr(cfg, "playbook", cfg), "global_goal_brief_chars", brief_chars,
            )
        brief = global_goal[:brief_chars] + ("…" if len(global_goal) > brief_chars else "")
        return f"[總目標方向] {brief}\n\n{prompt}"

    def validate_global_goal_achievement(
        self,
        playbook,
        step_log: list[str],
        global_goal: Optional[str] = None,
        *,
        code_state_snapshot: str = "",
    ) -> Optional[tuple[str, Optional[str]]]:
        """諮詢 Minimax 判斷 global_goal 是否達成（公開 API）。

        SD_05 W4-4：吸收原 `PlaybookRunner._validate_global_goal_achievement`。
        簽名相容：未傳 ``global_goal`` 時，預設使用 ``playbook.global_goal``。

        Returns:
            None    → 已達成（或缺 global_goal / minimax client）
            (completion_prompt, suggested_evaluator) → 需注入補完步驟
        """
        goal = global_goal or getattr(playbook, "global_goal", None)
        if not goal or self._client is None:
            return None
        summary = self.build_achievement_summary(step_log, self._max_recent)
        try:
            decision = self._client.validate_goal_achievement(
                global_goal=goal,
                step_summary=summary,
                playbook_project=playbook.project,
                code_state_snapshot=code_state_snapshot,
            )
        except Exception as exc:
            # API 失敗 → 傾向視為達成（避免假陽性阻斷）
            logger.warning(
                "GoalSynthesisPlugin: validate_goal_achievement 失敗，視為達成: %s", exc,
            )
            return None
        self._latest_decision = decision
        if getattr(decision, "is_achieved", True):
            return None
        completion = getattr(decision, "completion_prompt", None)
        if not completion:
            return None
        return completion, getattr(decision, "suggested_evaluator", None)

    # ──────────────────────────────────────────────
    # 內部：保留私有 alias（POST_RUN on_event 內部使用 + backward compat）
    # ──────────────────────────────────────────────
    def _validate(
        self, playbook, step_log: list[str],
    ) -> Optional[tuple[str, Optional[str]]]:
        return self.validate_global_goal_achievement(playbook, step_log)
