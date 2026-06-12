"""IPlaybookRepository — Playbook 與演化版本的 Port（SD_Improving_02.md v1.1 §1.2.3）。"""
from __future__ import annotations

from typing import Optional, Protocol

from ...models.playbook import Playbook


class IPlaybookRepository(Protocol):
    """Playbook 與其演化版本的持久化契約。"""

    def load(self, playbook_id: str) -> Playbook:
        """載入原始 Playbook。"""
        ...

    def persist_mutation(
        self, playbook_id: str, playbook: Playbook,
    ) -> None:
        """儲存突變後的 Playbook（覆寫原檔，作為「事實當前快照」）。"""
        ...

    def persist_evolution(
        self,
        original_id: str,
        evolved: Playbook,
        generation: int,
        mutation_log: list[str],
    ) -> str:
        """儲存演化版本，回傳新 playbook_id。

        File backend：寫成 evolved_{generation}_{原檔名}.yaml
        Postgres backend：插入 playbook_versions 表，回傳 UUID
        """
        ...

    def list_evolution_history(
        self, playbook_id: str
    ) -> list[tuple[int, str, str]]:
        """回傳演化歷史 [(generation, evolved_id, timestamp), ...]。"""
        ...
