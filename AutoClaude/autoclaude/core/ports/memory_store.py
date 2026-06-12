"""IMemoryStore — 跨 Session 失敗知識庫的 Port（SD_Improving_02.md v1.1 §1.2.2）。"""
from __future__ import annotations

from typing import Optional, Protocol


class IMemoryStore(Protocol):
    """跨 Session 失敗知識庫的契約（取代 FailureKnowledgeBase 直接使用）。"""

    def query(self, error_signature: str) -> Optional[dict]:
        """查詢已知錯誤模式（精確匹配）。"""
        ...

    def query_semantic(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.8,
    ) -> list[dict]:
        """語意向量查詢（ANN cosine 相似度）；pgvector 未啟用時回傳空清單。"""
        ...

    def query_strategy_priority(self, error_class: str) -> list[str]:
        """根據歷史成功率回傳策略優先序。"""
        ...

    def record_success(
        self,
        error_signature: str,
        strategy: str,
        step_id: str,
        error_class: str = "unknown",
        embedding: Optional[list[float]] = None,
    ) -> None:
        """記錄成功修正；embedding 非 None 時同步寫入向量欄位。"""
        ...

    def record_escalation(
        self,
        error_signature: str,
        tried_strategies: list[str],
        step_id: str,
    ) -> None:
        """記錄 ESCALATION（所有策略失敗）。"""
        ...

    def stats_by_error_class(self) -> dict[str, dict]:
        """各 error_class 的成功率統計（為 dashboard 鋪路，可選實作）。"""
        ...
