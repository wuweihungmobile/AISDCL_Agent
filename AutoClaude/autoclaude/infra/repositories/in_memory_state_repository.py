"""InMemoryStateRepository — IStateRepository 的記憶體後端（測試夾具）。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Optional

from ...utils.checkpoint_manager import PlaybookCheckpoint


class InMemoryStateRepository:
    """純記憶體 dict 後端，供單元 / 契約測使用。"""

    def __init__(self):
        self._store: dict[str, PlaybookCheckpoint] = {}

    def save_checkpoint(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        # deepcopy 避免外部修改污染儲存
        self._store[playbook_id] = deepcopy(checkpoint)
        self._store[playbook_id].saved_at = datetime.now().isoformat(timespec="seconds")

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook。"""
        import os, warnings  # noqa: E401
        if os.environ.get("AUTOCLAUDE_DEPRECATION_WARN") == "1":
            warnings.warn(
                "load_checkpoint(playbook_id) is deprecated since SD_06 W5; "
                "use load_latest_by_playbook(playbook_id) instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return self.load_latest_by_playbook(playbook_id)

    def load_latest_by_playbook(
        self, playbook_id: str,
    ) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：載入指定 playbook_id 最新一筆（單條目即 latest）。"""
        cp = self._store.get(playbook_id)
        return deepcopy(cp) if cp else None

    def load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：遍歷 store 找符合 run_id 的紀錄。"""
        if not run_id:
            return None
        for cp in self._store.values():
            if cp.run_id == run_id:
                return deepcopy(cp)
        return None

    def clear_checkpoint(self, playbook_id: str) -> None:
        self._store.pop(playbook_id, None)  # idempotent

    def schedule_resume(self, playbook_id: str, delay_minutes: int) -> datetime:
        resume_at = datetime.now() + timedelta(minutes=delay_minutes)
        cp = self._store.get(playbook_id)
        if cp is None:
            cp = PlaybookCheckpoint(
                playbook_path=playbook_id, step_idx=0, step_id="", total_steps=0,
            )
            self._store[playbook_id] = cp
        cp.scheduled_resume_at = resume_at.isoformat(timespec="seconds")
        return resume_at
