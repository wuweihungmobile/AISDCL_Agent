"""InMemoryPlaybookRepository — IPlaybookRepository 的記憶體後端（測試夾具）。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from ...models.playbook import Playbook


class InMemoryPlaybookRepository:
    """純 dict 後端，供契約測 LSP 驗證。"""

    def __init__(self, initial: dict[str, Playbook] | None = None):
        self._store: dict[str, Playbook] = dict(initial or {})
        self._evolutions: dict[str, list[tuple[int, str, str]]] = {}
        self._counter = 0

    def load(self, playbook_id: str) -> Playbook:
        if playbook_id not in self._store:
            raise FileNotFoundError(f"playbook_id 不存在於 InMemory store: {playbook_id}")
        return deepcopy(self._store[playbook_id])

    def persist_mutation(self, playbook_id: str, playbook: Playbook) -> None:
        self._store[playbook_id] = deepcopy(playbook)

    def persist_evolution(
        self, original_id: str, evolved: Playbook,
        generation: int, mutation_log: list[str],
    ) -> str:
        self._counter += 1
        new_id = f"evo:{original_id}:{self._counter}"
        self._store[new_id] = deepcopy(evolved)
        ts = datetime.now().isoformat(timespec="seconds")
        self._evolutions.setdefault(original_id, []).append(
            (generation, new_id, ts)
        )
        return new_id

    def list_evolution_history(
        self, playbook_id: str
    ) -> list[tuple[int, str, str]]:
        return list(self._evolutions.get(playbook_id, []))
