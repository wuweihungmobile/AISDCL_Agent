"""FilePlaybookRepository — IPlaybookRepository 的 File 後端（Phase 5）。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from ...models.playbook import Playbook


class FilePlaybookRepository:
    """以 yaml.safe_load / safe_dump 為 backend，過渡期 playbook_id == 檔案路徑。"""

    def __init__(self, base_dir: str = "scripts"):
        self._base = Path(base_dir)
        self._evolutions: dict[str, list[tuple[int, str, str]]] = {}

    def load(self, playbook_id: str) -> Playbook:
        # playbook_id 過渡期允許為相對 / 絕對路徑
        path = Path(playbook_id)
        if not path.is_absolute():
            cand = self._base / path
            if cand.exists():
                path = cand
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return Playbook(**raw)

    def persist_mutation(self, playbook_id: str, playbook: Playbook) -> None:
        path = Path(playbook_id)
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                playbook.model_dump(exclude_none=True),
                f, allow_unicode=True, sort_keys=False,
            )

    def persist_evolution(
        self, original_id: str, evolved: Playbook,
        generation: int, mutation_log: list[str],
    ) -> str:
        original = Path(original_id)
        evolved_path = original.parent / f"evolved_{generation}_{original.name}"
        with evolved_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                evolved.model_dump(exclude_none=True),
                f, allow_unicode=True, sort_keys=False,
            )
        ts = datetime.now().isoformat(timespec="seconds")
        self._evolutions.setdefault(original_id, []).append(
            (generation, str(evolved_path), ts)
        )
        return str(evolved_path)

    def list_evolution_history(
        self, playbook_id: str
    ) -> list[tuple[int, str, str]]:
        return list(self._evolutions.get(playbook_id, []))
