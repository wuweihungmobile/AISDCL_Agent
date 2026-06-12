"""IPlaybookRepository 契約測（Phase 5）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pytest
import yaml

from autoclaude.infra.repositories import (
    FilePlaybookRepository,
    InMemoryPlaybookRepository,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask


def _make_playbook(project="test"):
    return Playbook(
        version="1.0", project=project,
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="n", prompt="p")],
    )


class IPlaybookRepositoryContract(ABC):
    @abstractmethod
    def _make_repo(self, tmp_path: Path) -> tuple:
        """回傳 (repo, playbook_id) 用於測試。"""
        ...

    def test_load_returns_playbook(self, tmp_path: Path):
        repo, pid = self._make_repo(tmp_path)
        pb = repo.load(pid)
        assert pb.project == "test"
        assert len(pb.tasks) == 1

    def test_persist_evolution_returns_new_id(self, tmp_path: Path):
        repo, pid = self._make_repo(tmp_path)
        evolved = _make_playbook(project="evolved")
        new_id = repo.persist_evolution(
            original_id=pid,
            evolved=evolved,
            generation=1,
            mutation_log=["INJECT_BEFORE T_PRE"],
        )
        assert isinstance(new_id, str)
        assert new_id != pid

    def test_evolution_history_appends(self, tmp_path: Path):
        repo, pid = self._make_repo(tmp_path)
        evolved = _make_playbook(project="evolved")
        repo.persist_evolution(pid, evolved, generation=1, mutation_log=[])
        repo.persist_evolution(pid, evolved, generation=2, mutation_log=[])
        history = repo.list_evolution_history(pid)
        assert len(history) == 2
        assert history[0][0] == 1   # generation
        assert history[1][0] == 2

    def test_history_empty_for_new_id(self, tmp_path: Path):
        repo, _ = self._make_repo(tmp_path)
        assert repo.list_evolution_history("never_evolved") == []


# ──────────────────────────────────────────────
class TestFilePlaybookRepositoryContract(IPlaybookRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        # 預先建立一個 yaml playbook 檔
        pb_path = tmp_path / "test.yaml"
        pb_path.write_text(
            yaml.dump({
                "version": "1.0", "project": "test",
                "global_invariants": {"max_retries_per_step": 3,
                                      "auto_compact_interval": 0},
                "tasks": [{"step_id": "T01", "name": "n", "prompt": "p"}],
            }),
            encoding="utf-8",
        )
        return FilePlaybookRepository(base_dir=str(tmp_path)), str(pb_path)


class TestInMemoryPlaybookRepositoryContract(IPlaybookRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        pb = _make_playbook()
        repo = InMemoryPlaybookRepository(initial={"test_id": pb})
        return repo, "test_id"


class TestInMemoryPlaybookRepositorySpecificBehaviors:
    def test_load_missing_raises_filenotfound(self):
        repo = InMemoryPlaybookRepository()
        with pytest.raises(FileNotFoundError):
            repo.load("nonexistent")
