"""FileMemoryStore — IMemoryStore 的 File 後端（薄包裝 FailureKnowledgeBase）。"""
from __future__ import annotations

from typing import Optional

from ...utils.knowledge_base import FailureKnowledgeBase


class FileMemoryStore:
    """委派至既有 FailureKnowledgeBase（JSONL）。"""

    def __init__(self, jsonl_path: str):
        self._kb = FailureKnowledgeBase(jsonl_path)

    def query(self, error_signature: str) -> Optional[dict]:
        return self._kb.query(error_signature)

    def query_strategy_priority(self, error_class: str) -> list[str]:
        # FailureKnowledgeBase 提供 get_strategy_priority；fallback 至空列表
        getter = getattr(self._kb, "query_strategy_priority", None) \
                 or getattr(self._kb, "get_strategy_priority", None)
        return list(getter(error_class)) if getter else []

    def record_success(
        self, error_signature: str, strategy: str,
        step_id: str, error_class: str = "unknown",
    ) -> None:
        # FailureKnowledgeBase 簽章為 successful_strategy（內部欄位名）
        self._kb.record_success(
            error_signature=error_signature,
            successful_strategy=strategy,
            step_id=step_id,
            error_class=error_class,
        )

    def record_escalation(
        self, error_signature: str, tried_strategies: list[str], step_id: str,
    ) -> None:
        # FailureKnowledgeBase 簽章為 failed_strategies
        self._kb.record_escalation(
            error_signature=error_signature,
            failed_strategies=tried_strategies,
            step_id=step_id,
        )

    def stats_by_error_class(self) -> dict[str, dict]:
        # 可選實作；fallback 至空 dict（File backend 暫不提供）
        getter = getattr(self._kb, "stats_by_error_class", None)
        return dict(getter()) if getter else {}
