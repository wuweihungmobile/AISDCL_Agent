"""KnowledgeBasePlugin — 取代 PlaybookRunner 中 record_success / record_escalation 散在 4 處的呼叫。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 6 列（priority=50）
  - SD_Improving_02.md v1.1 §2.5 W6 #5

訂閱 phase：
  - ON_SUCCESS    → record_success（含 error_signature / strategy / step_id / error_class）
  - ON_FAILURE    → 暫不記錄（重試中），交由 ON_ESCALATION 統一處理
  - ON_ESCALATION → record_escalation（含 tried_strategies）

純觀察者 — 不回傳 IHookResult。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase
from ..utils.knowledge_base import FailureKnowledgeBase

logger = logging.getLogger("autoclaude.plugins.knowledge_base")


class KnowledgeBasePlugin:
    """跨 Session 失敗知識庫 Plugin（Gap-009-E / Gap-010-F）。"""

    PRIORITY = 50

    def __init__(self, knowledge_base: Optional[FailureKnowledgeBase] = None):
        self._kb = knowledge_base

    def name(self) -> str:
        return "knowledge_base"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.ON_SUCCESS,
            KernelPhase.ON_FAILURE,
            KernelPhase.ON_ESCALATION,
        ]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if self._kb is None:
            return None

        if ctx.phase == KernelPhase.ON_SUCCESS:
            self._on_success(ctx)
        elif ctx.phase == KernelPhase.ON_ESCALATION:
            self._on_escalation(ctx)
        # ON_FAILURE：重試中，不記錄（避免污染統計）
        return None

    # ──────────────────────────────────────────────
    def _on_success(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        signature = payload.get("error_signature")
        if not signature:
            return  # 無錯誤上下文（首次即成功）→ 不記錄
        try:
            self._kb.record_success(
                error_signature=signature,
                strategy=payload.get("strategy", "unknown"),
                step_id=ctx.task.step_id if ctx.task else "N/A",
                error_class=payload.get("error_class", "unknown"),
            )
        except (TypeError, AttributeError) as exc:
            logger.warning("KnowledgeBasePlugin record_success failed: %s", exc)

    def _on_escalation(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        signature = payload.get("error_signature")
        if not signature:
            return
        try:
            self._kb.record_escalation(
                error_signature=signature,
                tried_strategies=payload.get("tried_strategies", []),
                step_id=ctx.task.step_id if ctx.task else "N/A",
            )
        except (TypeError, AttributeError) as exc:
            logger.warning("KnowledgeBasePlugin record_escalation failed: %s", exc)
