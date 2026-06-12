"""GoalProgressPlugin — 跨 playbook run 進度記錄（F-C2 / ADR-AGT-003 L4）。

訂閱 phase：
  - POST_RUN → 自 payload 取 completed_step_ids / total_steps，計算 progress_pct
    並 append 至 GoalProgressLedger。

語意註記：
  - POST_RUN 僅於 run 正常走完時發布（halt / escalate 提前 return 不記錄），
    故 ledger 記錄的是「完成的 run」進度快照。
  - 鍵：payload 有 goal_task_id 用之（為 Coordinator 三層模型留接縫）；
    否則以 `project:{playbook.project}` fallback（yaml_only 常態）。
  - Ledger 實例由 wiring 注入（plugin 不直接 import infra / utils 路由邏輯）。
"""
from __future__ import annotations

import logging
from typing import Any

from ..core.hookspec import HookContext, KernelPhase

logger = logging.getLogger("autoclaude.plugins.goal_progress")


class GoalProgressPlugin:
    """L4 目標進度 Plugin（US-AGT-004）。"""

    PRIORITY = 50

    def __init__(self, ledger: Any | None = None):
        self._ledger = ledger

    def name(self) -> str:
        return "goal_progress"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_RUN]

    def on_event(self, ctx: HookContext) -> Any | None:
        if ctx.phase != KernelPhase.POST_RUN or self._ledger is None:
            return None
        payload = ctx.payload or {}
        completed = payload.get("completed_step_ids")
        total = payload.get("total_steps")
        if completed is None or not total:
            return None  # 無結果摘要（舊路徑 / 空 playbook）→ 不記錄
        goal_key = payload.get("goal_task_id") or f"project:{ctx.playbook.project}"
        # 保序去重：GOTO 回跳重做步驟時 payload 可能含重複 step_id，
        # 直接以長度算 pct 會 >100%（複驗 P1-1 修復附帶防禦）
        unique_completed = list(dict.fromkeys(completed))
        try:
            self._ledger.record(
                goal_key,
                playbook_id=ctx.playbook.project,
                # run_id：payload 目前無此 key（恆 None）；為 Phase 3 Coordinator
                # 三層任務模型預留接縫，屆時由 payload 傳入（複驗 P2-1 明示）
                run_id=payload.get("run_id"),
                completed_features=unique_completed,
                progress_pct=round(100.0 * len(unique_completed) / total, 2),
            )
        except Exception as exc:
            logger.warning("GoalProgressPlugin record failed: %s", exc)
        return None


__all__ = ["GoalProgressPlugin"]
