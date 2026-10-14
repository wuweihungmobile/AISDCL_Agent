"""run 的持久化狀態（`<workspace>/<run_id>/run.json`）與目錄佈局。

run.json 只放**非機密**的執行狀態：env 的值從不落盤（env 只有名稱清單），config.yaml 也不收機密
（security.validate_config_overrides 擋掉 api_key／db_dsn）。
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .fsutil import read_json, write_json_atomic

SCHEMA_VERSION = 1


@dataclass
class RunRecord:
    run_id: str
    project: str
    execution_path: str
    status: str = "INITIALIZING"
    reason: str = ""
    pid: int | None = None
    pid_create_time: float | None = None
    last_pid: int | None = None
    bridge_instance: str = ""
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    exit_code: int | None = None
    spawn_count: int = 0
    current_step: str | None = None
    current_step_number: int | None = None
    attempt: int = 0
    completed_step_ids: list[str] = field(default_factory=list)
    total_steps: int = 0
    tokens_used: int = 0
    peak_token_pct: float = 0.0
    lock_key: str | None = None
    db_lock_key: int | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)   # [{step_id,name,goal_task_id}]
    env_keys: list[str] = field(default_factory=list)           # 只記名稱，不記值
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


class RunPaths:
    """單一 run 的檔案佈局（全部在 `<workspace>/<run_id>/` 之下）。"""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.run_json = run_dir / "run.json"
        self.events = run_dir / "events.jsonl"
        self.playbook = run_dir / "playbook.yaml"
        self.config = run_dir / "config.yaml"
        self.history = run_dir / "history"
        self.engine = run_dir / "engine"
        self.checkpoints = self.engine / "checkpoints"
        self.logs = self.engine / "logs"
        self.backups = self.engine / "backups"
        self.scripts = self.engine / "scripts"

    def engine_log(self, spawn_index: int) -> Path:
        return self.run_dir / f"engine-{spawn_index}.log"


def save_record(paths: RunPaths, record: RunRecord) -> None:
    write_json_atomic(paths.run_json, record.to_dict())


def load_record(run_json: Path) -> RunRecord | None:
    data = read_json(run_json)
    if not isinstance(data, dict) or "run_id" not in data:
        return None
    return RunRecord.from_dict(data)
