"""GlobalGoalAnchorPlugin — 取代 PlaybookRunner 的 _prepend_global_goal* + _send_compact 中 anchor 注入。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 11 列（priority=35）
  - SD_Improving_02.md v1.1 §2.5 W7 #7

訂閱 phase：
  - PRE_ATTEMPT     → 注入 GLOBAL_GOAL header（首次完整版 / 後續精簡版）
  - ON_TOKEN_USAGE  → 提供 anchor payload 給 Kernel 在發送 /compact 時使用

對應 Gap：
  - Gap-011-A：每次 attempt 注入 global_goal 對齊
  - Gap-013-H：global_goal_anchor_chars 可配置（預設 400）
  - Gap-015-A：非首步驟使用精簡版（global_goal_brief_chars 預設 150）
  - Gap-039：compact MEMORY ANCHOR 持久化
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from ..utils.config import PlaybookConfig


class GlobalGoalAnchorPlugin:
    """注入 global_goal 文字至 prompt 與 compact anchor。"""

    PRIORITY = 35

    def __init__(self, playbook_cfg: Optional[PlaybookConfig] = None):
        self._cfg = playbook_cfg or PlaybookConfig()
        self._is_first_step = True   # 第一個步驟使用完整版 header

    def name(self) -> str:
        return "global_goal_anchor"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_ATTEMPT, KernelPhase.ON_TOKEN_USAGE]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if ctx.phase == KernelPhase.PRE_ATTEMPT:
            return self._on_pre_attempt(ctx)
        # ON_TOKEN_USAGE 純觀察者；anchor 內容由公開方法 build_compact_anchor() 提供
        return None

    # ──────────────────────────────────────────────
    def _on_pre_attempt(self, ctx: HookContext) -> Optional[PromptInjectionResult]:
        global_goal = ctx.playbook.global_goal
        if not global_goal:
            return None
        # 僅在 attempt=0（首次）注入
        if ctx.attempt is not None and ctx.attempt > 0:
            return None
        # 第 1 個步驟使用完整版，後續步驟使用精簡版
        if ctx.step_idx == 0 and self._is_first_step:
            prefix = self._build_full_header(global_goal)
            self._is_first_step = False
        else:
            prefix = self._build_brief_header(global_goal)
        return PromptInjectionResult(
            contributor=self.name(),
            prefix=prefix,
            position="top",
        )

    def _build_full_header(self, global_goal: str) -> str:
        """Gap-011-A：完整版 header（首步驟使用，最大 500 字元）。"""
        return (
            "=== 本次自動化任務的總目標 ===\n"
            f"{global_goal[:500]}\n"
            "以上為整體目標供你參考，請確保每個步驟的實作決策與此目標方向一致。\n"
            "===========================\n\n"
        )

    def _build_brief_header(self, global_goal: str) -> str:
        """Gap-015-A：精簡版 header（非首步驟使用，預設 150 字元）。"""
        n = self._cfg.global_goal_brief_chars
        brief = global_goal[:n] + ("…" if len(global_goal) > n else "")
        return f"[總目標方向] {brief}\n\n"

    # ──────────────────────────────────────────────
    # 公開：供 TokenGuardPlugin / Kernel 在 /compact 前構建 ANCHOR
    # ──────────────────────────────────────────────
    def build_compact_anchor(
        self,
        global_goal: Optional[str],
        task,
        attempt: int,
        failure_summary: str = "",
    ) -> str:
        """Gap-039 / Gap-013-H：建構 compact MEMORY ANCHOR 文字。"""
        if not task:
            return ""
        anchor = (
            "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
            f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
            f"[ATTEMPT] {attempt + 1}\n"
        )
        if task.expected_output_regex:
            anchor += f"[SUCCESS_CONDITION] output must match: {task.expected_output_regex}\n"
        if failure_summary:
            last_err = failure_summary.split("\n")[-1][:120]
            anchor += f"[LAST_FAILURE] {last_err}\n"
        if global_goal:
            n = self._cfg.global_goal_anchor_chars
            brief = global_goal[:n] + ("…" if len(global_goal) > n else "")
            anchor += f"[GLOBAL_GOAL] {brief}\n"
        anchor += "=== END ANCHOR ===\n"
        return anchor
