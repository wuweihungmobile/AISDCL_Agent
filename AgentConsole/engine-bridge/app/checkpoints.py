"""checkpoint：Bridge 自己的歷史快照＋寫成「引擎看得懂的格式」。

實證前提（2026-10-14，見 app/logparse.py 檔頭）：AutoClaude **不會在每個步驟結束時寫 checkpoint**
——只有 token HALT／ESC+F12 中斷／演化才寫，且整條 playbook 成功跑完後會把它清掉。所以：
  · pause 邊界、`GET /checkpoints`、restore 所需的還原點，全部由 Bridge 在「推得步驟 k 完成」時
    自己記錄成**歷史快照**（`<run>/history/NNNN-<id>.json`，append-only，不隨引擎清除）。
  · 續跑（resume／restore）前，用**引擎自己的** `FileStateRepository` 把選定快照寫進引擎的
    checkpoint 目錄（它會算 checksum_sha256、做保留版本輪替），再不帶 --fresh 啟動引擎，
    由引擎的 `AutoResumeService._resolve_start` 從 `step_idx` 接續。
"""
from __future__ import annotations

import dataclasses
import threading
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autoclaude.infra.repositories.factory import canonical_playbook_id
from autoclaude.infra.repositories.file_state_repository import FileStateRepository
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint

from .fsutil import read_json, write_json_atomic
from .logparse import StepDef


def _playbook_id(playbook_path: Path) -> str:
    return canonical_playbook_id(str(playbook_path), "yaml_only")


def build_checkpoint_state(*, playbook_path: Path, project: str, steps: Sequence[StepDef],
                           step_idx: int, completed_ids: Sequence[str],
                           completed_log: Sequence[str], peak_token_pct: float) -> dict[str, Any]:
    """組出一個 PlaybookCheckpoint 的 dict：step_idx＝下次從哪個步驟開始（0-based）。"""
    nxt = steps[step_idx] if 0 <= step_idx < len(steps) else None
    cp = PlaybookCheckpoint(
        playbook_path=str(playbook_path),
        step_idx=step_idx,
        step_id=nxt.step_id if nxt else "",
        total_steps=len(steps),
        project=project,
        completed_step_log=list(completed_log),
        peak_token_pct=peak_token_pct,
        completed_step_ids=list(completed_ids),
        goal_task_id=nxt.goal_task_id if nxt else None,
    )
    return dataclasses.asdict(cp)


def write_engine_checkpoint(checkpoint_dir: Path, playbook_path: Path,
                            state: dict[str, Any]) -> None:
    """用引擎自己的 repository 寫入（checksum／保留版本由它負責）。"""
    fields = {f.name for f in dataclasses.fields(PlaybookCheckpoint)}
    cp = PlaybookCheckpoint(**{k: v for k, v in state.items() if k in fields})
    FileStateRepository(str(checkpoint_dir)).save_checkpoint(_playbook_id(playbook_path), cp)


def load_engine_checkpoint(checkpoint_dir: Path, playbook_path: Path) -> PlaybookCheckpoint | None:
    """引擎目前的 checkpoint（沒有回 None；損毀時引擎的 CheckpointCorruptError 往上拋）。"""
    return FileStateRepository(str(checkpoint_dir)).load_latest_by_playbook(
        _playbook_id(playbook_path))


class CheckpointHistory:
    """`<run>/history/` 下的快照：每筆一個 JSON 檔 `NNNN-<checkpoint_id>.json`。"""

    def __init__(self, directory: Path):
        self._dir = directory
        self._mutex = threading.Lock()

    def add(self, *, name: str, step_idx: int, step_id: str, state: dict[str, Any],
            is_automatic: bool = True) -> dict[str, Any]:
        with self._mutex:
            self._dir.mkdir(parents=True, exist_ok=True)
            n = sum(1 for _ in self._dir.glob("*.json")) + 1
            meta = {
                # API 與 PG（console.checkpoints.id，UUID）同一個值：正規有連字號的寫法。
                "checkpoint_id": str(uuid.uuid4()),
                "name": name,
                "created_at": datetime.now(UTC).isoformat(),
                "step_idx": step_idx,
                "step_id": step_id,
                "is_automatic": is_automatic,
            }
            write_json_atomic(self._dir / f"{n:04d}-{uuid.UUID(meta['checkpoint_id']).hex}.json",
                              {**meta, "state": state})
            return meta

    def list_meta(self) -> list[dict[str, Any]]:
        """契約形狀的清單（建立順序，舊→新）。"""
        out: list[dict[str, Any]] = []
        for path in sorted(self._dir.glob("*.json")) if self._dir.is_dir() else []:
            doc = read_json(path)
            if isinstance(doc, dict) and "checkpoint_id" in doc:
                out.append({k: doc[k] for k in
                            ("checkpoint_id", "name", "created_at", "step_idx", "step_id",
                             "is_automatic")})
        return out

    def get(self, checkpoint_id: str) -> dict[str, Any] | None:
        """含 `state` 的完整快照。id 必須是 UUID（有無連字號皆可）；格式不對直接回 None——
        絕不拿呼叫端給的字串去拼檔名。"""
        try:
            key = uuid.UUID(checkpoint_id).hex
        except (ValueError, AttributeError, TypeError):
            return None
        for path in self._dir.glob(f"*-{key}.json") if self._dir.is_dir() else []:
            doc = read_json(path)
            if isinstance(doc, dict) and doc.get("checkpoint_id") == str(uuid.UUID(key)):
                return doc
        return None

    def latest(self) -> dict[str, Any] | None:
        metas = self.list_meta()
        return self.get(metas[-1]["checkpoint_id"]) if metas else None
