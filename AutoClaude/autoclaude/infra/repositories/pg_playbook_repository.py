"""PgPlaybookRepository — IPlaybookRepository 的 PostgreSQL 後端（Phase 6 選配）。

⚠️ 需安裝：pip install autoclaude[postgres]

playbook_id 設計：
  - File backend：path stem
  - PG backend：sha256(canonical_yaml(playbook))[:16]
  - 過渡期可同時支援（dual-id），由 main.py 注入時決定
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import yaml

from ...models.playbook import Playbook

_SQLALCHEMY_AVAILABLE = False
try:
    from sqlalchemy import select
    from ._pg_models import PlaybookVersion
    from .pg_async_utils import _run_async
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    # C-A 修復：即使 sqlalchemy 未安裝，仍提供完整的 thread-safe _run_async
    from .pg_async_utils import _run_async  # type: ignore[import]


def _canonical_id(playbook: Playbook) -> str:
    """sha256(canonical_yaml(playbook))[:16]，內容尋址避免重命名導致 checkpoint 遺失。"""
    canonical = yaml.safe_dump(
        playbook.model_dump(exclude_none=True), sort_keys=True, allow_unicode=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class PgPlaybookRepository:
    """PostgreSQL backend for IPlaybookRepository（playbook_versions 表）。"""

    def __init__(self, engine: "Any"):
        if not _SQLALCHEMY_AVAILABLE:
            raise ImportError(
                "PgPlaybookRepository 需 sqlalchemy + asyncpg；"
                "請執行：pip install autoclaude[postgres]"
            )
        self._engine = engine

    def load(self, playbook_id: str) -> Playbook:
        try:
            return _run_async(self._load(playbook_id))
        except Exception as exc:
            raise FileNotFoundError(f"playbook_id={playbook_id} 不存在於 PG: {exc}") from exc

    def persist_mutation(self, playbook_id: str, playbook: Playbook) -> None:
        # PG 後端：突變即新增一筆 version（不覆寫，保留歷史）
        self.persist_evolution(
            original_id=playbook_id, evolved=playbook, generation=0,
            mutation_log=["mutation"],
        )

    def persist_evolution(
        self, original_id: str, evolved: Playbook,
        generation: int, mutation_log: list[str],
    ) -> str:
        try:
            return _run_async(self._persist(original_id, evolved, generation, mutation_log))
        except Exception as exc:
            raise RuntimeError(f"PgPlaybookRepository.persist_evolution 失敗: {exc}") from exc

    def list_evolution_history(
        self, playbook_id: str
    ) -> list[tuple[int, str, str]]:
        try:
            return _run_async(self._list_history(playbook_id))
        except Exception:
            return []

    # ──────────────────────────────────────────────
    async def _load(self, playbook_id: str) -> Playbook:
        async with self._engine.connect() as conn:
            stmt = (
                select(PlaybookVersion)
                .where(PlaybookVersion.original_playbook_id == playbook_id)
                .order_by(PlaybookVersion.generation.desc())
                .limit(1)
            )
            row = (await conn.execute(stmt)).first()
        if row is None:
            raise FileNotFoundError(f"playbook_id={playbook_id} 不存在")
        return Playbook(**yaml.safe_load(row[0].yaml_content))

    async def _persist(
        self, original_id: str, evolved: Playbook,
        generation: int, mutation_log: list[str],
    ) -> str:
        canonical = yaml.safe_dump(
            evolved.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False,
        )
        async with self._engine.begin() as conn:
            await conn.execute(
                PlaybookVersion.__table__.insert().values(
                    original_playbook_id=original_id,
                    generation=generation,
                    yaml_content=canonical,
                    mutation_log=list(mutation_log),
                )
            )
        return f"pg:{original_id}:gen{generation}"

    async def _list_history(self, playbook_id: str) -> list[tuple[int, str, str]]:
        async with self._engine.connect() as conn:
            stmt = (
                select(
                    PlaybookVersion.generation,
                    PlaybookVersion.version_id,
                    PlaybookVersion.created_at,
                )
                .where(PlaybookVersion.original_playbook_id == playbook_id)
                .order_by(PlaybookVersion.generation)
            )
            rows = (await conn.execute(stmt)).all()
        return [
            (gen, str(vid), ts.isoformat(timespec="seconds") if isinstance(ts, datetime) else str(ts))
            for gen, vid, ts in rows
        ]
