"""FileStateRepository — IQueryableStateRepository 的 File 後端（Phase 5 W1b）。

W1b（SD_03 §3.1）：移除對 CheckpointManager 的依賴，直接實作 atomic JSON 讀寫。
CheckpointManager 現在反向委派至本類別（薄包裝器）。
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ...core.ports.state_repository import StateRepositoryError
from ...utils.checkpoint_manager import PlaybookCheckpoint

logger = logging.getLogger("autoclaude.infra.file_state")

_SUFFIX = ".checkpoint.json"


class FileStateRepository:
    """File backend — atomic JSON read/write，不依賴 CheckpointManager。"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self._dir = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, playbook_id: str) -> Path:
        return self._dir / f"{playbook_id}{_SUFFIX}"

    def save_checkpoint(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        """符合 StateRepositoryPort 契約：回傳 None。"""
        try:
            p = self._path(playbook_id)
            checkpoint.saved_at = datetime.now().isoformat(timespec="seconds")
            tmp_p = p.with_suffix(".tmp")
            try:
                with tmp_p.open("w", encoding="utf-8") as f:
                    json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)
                    f.flush()
                tmp_p.replace(p)
            except Exception:
                tmp_p.unlink(missing_ok=True)
                raise
            logger.info(
                "檢查點已儲存: %s | step_idx=%d [%s] token=%.1f%%",
                p, checkpoint.step_idx, checkpoint.step_id, checkpoint.peak_token_pct,
            )
        except OSError as exc:
            raise StateRepositoryError(f"save_checkpoint 失敗: {exc}") from exc

    def load_checkpoint(self, playbook_id: str) -> Optional[PlaybookCheckpoint]:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook。

        env AUTOCLAUDE_DEPRECATION_WARN=1 時 emit DeprecationWarning。
        """
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
        """SD_06 W5-T5-7：載入指定 playbook_id 最新一筆 checkpoint。

        File backend 一個 playbook_id 對應一個檔案，自然就是 latest。
        """
        p = self._path(playbook_id)
        if not p.exists():
            return None
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
            cp = PlaybookCheckpoint(**data)
            logger.info(
                "已載入檢查點: step_idx=%d [%s]，儲存於 %s",
                cp.step_idx, cp.step_id, cp.saved_at,
            )
            return cp
        except Exception as exc:
            logger.warning("檢查點載入失敗 (%s): %s，將從頭開始", p, exc)
            return None

    def load_by_run_id(self, run_id: str) -> Optional[PlaybookCheckpoint]:
        """SD_06 W5-T5-7：遍歷 checkpoint 檔案找符合 run_id 的紀錄。

        File backend 不索引 run_id，效能 O(n)；用於 dev 環境。
        正式 production 環境請改用 PgStateRepository.load_by_run_id（indexed）。
        """
        if not run_id:
            return None
        for p in self._dir.glob(f"*{_SUFFIX}"):
            try:
                with p.open(encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("run_id") == run_id:
                    return PlaybookCheckpoint(**data)
            except Exception as exc:
                logger.debug("load_by_run_id | 跳過損毀檔案 %s: %s", p, exc)
                continue
        return None

    def clear_checkpoint(self, playbook_id: str) -> None:
        p = self._path(playbook_id)
        if p.exists():
            p.unlink()
            logger.info("檢查點已清除: %s", p)

    def schedule_resume(self, playbook_id: str, delay_minutes: int) -> datetime:
        resume_at = datetime.now() + timedelta(minutes=delay_minutes)
        cp = self.load_checkpoint(playbook_id) or PlaybookCheckpoint(
            playbook_path=playbook_id, step_idx=0, step_id="", total_steps=0,
        )
        cp.scheduled_resume_at = resume_at.isoformat(timespec="seconds")
        self.save_checkpoint(playbook_id, cp)
        return resume_at

    @staticmethod
    def seconds_until_resume(checkpoint: PlaybookCheckpoint) -> float:
        if not checkpoint.scheduled_resume_at:
            return 0.0
        try:
            resume_at = datetime.fromisoformat(checkpoint.scheduled_resume_at)
            return max(0.0, (resume_at - datetime.now()).total_seconds())
        except ValueError:
            return 0.0

    def list_recent_checkpoints(
        self, since: Optional[datetime] = None, limit: int = 50
    ) -> list[PlaybookCheckpoint]:
        results: list[PlaybookCheckpoint] = []
        for p in self._dir.glob(f"*{_SUFFIX}"):
            playbook_id = p.stem.replace(".checkpoint", "")
            cp = self.load_checkpoint(playbook_id)
            if cp is None:
                continue
            if since:
                try:
                    saved = datetime.fromisoformat(cp.saved_at)
                    if saved < since:
                        continue
                except (ValueError, TypeError):
                    pass
            results.append(cp)
        results.sort(key=lambda c: c.saved_at, reverse=True)
        return results[:limit]
