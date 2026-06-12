"""InMemoryMemoryStore — IMemoryStore 的記憶體後端（測試夾具）。"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional


class InMemoryMemoryStore:
    """純 dict 後端，供契約測 LSP 驗證。"""

    def __init__(self):
        self._success: dict[str, dict] = {}
        self._escalations: list[dict] = []
        self._strategy_success: dict[str, Counter] = defaultdict(Counter)

    def query(self, error_signature: str) -> Optional[dict]:
        return self._success.get(error_signature)

    def query_strategy_priority(self, error_class: str) -> list[str]:
        counter = self._strategy_success.get(error_class)
        if not counter:
            return []
        return [s for s, _ in counter.most_common()]

    def record_success(
        self, error_signature: str, strategy: str,
        step_id: str, error_class: str = "unknown",
    ) -> None:
        self._success[error_signature] = {
            "strategy": strategy, "step_id": step_id, "error_class": error_class,
        }
        self._strategy_success[error_class][strategy] += 1

    def record_escalation(
        self, error_signature: str, tried_strategies: list[str], step_id: str,
    ) -> None:
        self._escalations.append({
            "error_signature": error_signature,
            "tried_strategies": list(tried_strategies),
            "step_id": step_id,
        })

    def stats_by_error_class(self) -> dict[str, dict]:
        return {
            ec: {"success_count": sum(c.values()), "strategies": dict(c)}
            for ec, c in self._strategy_success.items()
        }
