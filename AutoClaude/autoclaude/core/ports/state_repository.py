"""IStateRepository — Checkpoint 持久化的 Port（Phase 5 / SD_Improving_02.md v1.1 §1.2.1）。

設計原則：
  - 介面不暴露 path（leaky abstraction 的根源）
  - 過渡期：playbook_id = Path(playbook_path).stem
  - PostgreSQL 期：playbook_id = sha256(canonical_yaml(playbook))[:16]

實作（Phase 5）：
  - autoclaude.infra.repositories.file_state_repository.FileStateRepository
  - autoclaude.infra.repositories.in_memory_state_repository.InMemoryStateRepository

未來（Phase 6 選配）：
  - autoclaude.infra.repositories.pg_state_repository.PgStateRepository
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from ...utils.checkpoint_manager import PlaybookCheckpoint


class IStateRepository(Protocol):
    """Checkpoint 持久化的最小契約（所有後端必實作）。

    SD_06 W5-T5-7 起新增 `load_by_run_id` 與 `load_latest_by_playbook` 雙 API；
    既有 `load_checkpoint(playbook_id)` 保留為 deprecated alias，行為等同
    `load_latest_by_playbook(playbook_id)`。SD_07 起預計移除。
    """

    def save_checkpoint(
        self, playbook_id: str, checkpoint: PlaybookCheckpoint
    ) -> None:
        """原子性儲存 checkpoint。

        Raises:
            StateRepositoryError: 持久化失敗
        """
        ...

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook(playbook_id)。

        保留以維持 v1.x 相容；行為等同 load_latest_by_playbook。
        env AUTOCLAUDE_DEPRECATION_WARN=1 時將 emit DeprecationWarning。
        """
        ...

    def load_latest_by_playbook(
        self, playbook_id: str,
    ) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：載入指定 playbook_id 最新一筆 checkpoint。"""
        ...

    def load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：載入指定 run_id 的 checkpoint（三層任務模型）。

        File backend 遍歷檔案（用於 dev 環境）；PG backend 走 indexed query。
        找不到回傳 None（idempotent）。
        """
        ...

    def clear_checkpoint(self, playbook_id: str) -> None:
        """清除 checkpoint（步驟完成或 --fresh 時呼叫）。

        若不存在不視為錯誤（idempotent）。
        """
        ...

    def schedule_resume(
        self, playbook_id: str, delay_minutes: int
    ) -> datetime:
        """設定排程繼續時間，回傳預計恢復時刻。"""
        ...


class IQueryableStateRepository(IStateRepository, Protocol):
    """提供進階查詢能力的擴展介面（v1.1 ISP 修正）。

    僅實作 IStateRepository 的後端不需提供 list_recent_checkpoints；
    呼叫端透過 isinstance 判斷是否可用。
    """

    def list_recent_checkpoints(
        self, since: Optional[datetime] = None, limit: int = 50
    ) -> list[PlaybookCheckpoint]:
        """列出近期 checkpoint，依 saved_at 倒序排列。"""
        ...


class StateRepositoryError(Exception):
    """持久化失敗的統一例外。"""
