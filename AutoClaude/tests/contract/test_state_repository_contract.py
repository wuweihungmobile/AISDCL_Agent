"""IStateRepository 契約測（SD_Improving_01.md v1.1 §3.9 / SD_Improving_02.md v1.1 §2.7）。

採 abstract base class 強制所有 IStateRepository 實作通過同一組行為驗證。
任何新後端（File / InMemory / Phase 6 PG）必須繼承 IStateRepositoryContract
並實作 _make_repo()，否則 CI 阻擋合併。

≥ 7 個契約測（v1.1 §3.9 必測）:
  1. test_save_load_roundtrip
  2. test_load_missing_returns_none
  3. test_clear_idempotent
  4. test_counter_persistence_round_trip   (Gap-042 / Gap-048)
  5. test_failure_history_round_trip       (Gap-007-A)
  6. test_schedule_resume_sets_iso_timestamp
  7. test_overwrite_preserves_atomicity
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from autoclaude.core.services.auto_resume import seconds_until_resume
from autoclaude.infra.repositories import (
    FileStateRepository,
    InMemoryStateRepository,
)
from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
from autoclaude.utils.logger import _sanitize_log_filename


def _make_sample_checkpoint(**overrides) -> PlaybookCheckpoint:
    defaults = dict(
        playbook_path="x.yaml",
        step_idx=2,
        step_id="T03",
        total_steps=5,
        project="contract-test",
        completed_step_log=["[OK] T01", "[OK] T02"],
        peak_token_pct=42.5,
        completed_step_ids=["T01", "T02"],
        goto_counter={"T01": 2, "T03": 1},
        inject_before_counter={"T02": 1},
        skip_to_counter={"T04": 3},
        step_evolution_counter={"T05": 2, "T06": 1},
        failure_history=[{"attempt": 0, "reason": "regex miss"}],
        active_step_attempt=1,
        last_correction_prompt="please retry",
    )
    defaults.update(overrides)
    return PlaybookCheckpoint(**defaults)


class IStateRepositoryContract(ABC):
    """所有 IStateRepository 實作必通過的共同行為（LSP 驗證）。"""

    @abstractmethod
    def _make_repo(self, tmp_path: Path):
        ...

    def test_save_load_roundtrip(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint()
        repo.save_checkpoint("pb_001", cp)
        loaded = repo.load_checkpoint("pb_001")
        assert loaded is not None
        assert loaded.step_id == cp.step_id
        assert loaded.step_idx == cp.step_idx
        assert loaded.completed_step_ids == cp.completed_step_ids

    def test_load_missing_returns_none(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        assert repo.load_checkpoint("nonexistent_id") is None

    def test_clear_idempotent(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        repo.clear_checkpoint("pb_001")  # 不存在也不應拋例外
        repo.save_checkpoint("pb_001", _make_sample_checkpoint())
        repo.clear_checkpoint("pb_001")
        repo.clear_checkpoint("pb_001")  # 重複 clear 仍 idempotent
        assert repo.load_checkpoint("pb_001") is None

    def test_counter_persistence_round_trip(self, tmp_path: Path):
        """Gap-042 / Gap-048：4 個跨 Session 計數器須完整保留。"""
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint(
            goto_counter={"T01": 5, "T03": 2},
            inject_before_counter={"T02": 1},
            skip_to_counter={"T04": 3, "T07": 1},
            step_evolution_counter={"T05": 2, "T06": 1, "T09": 4},
        )
        repo.save_checkpoint("pb_002", cp)
        loaded = repo.load_checkpoint("pb_002")
        assert loaded.goto_counter == cp.goto_counter
        assert loaded.inject_before_counter == cp.inject_before_counter
        assert loaded.skip_to_counter == cp.skip_to_counter
        assert loaded.step_evolution_counter == cp.step_evolution_counter

    def test_failure_history_round_trip(self, tmp_path: Path):
        """Gap-007-A：FailureTracker 歷史跨 Session 持久化。"""
        repo = self._make_repo(tmp_path)
        cp = _make_sample_checkpoint(
            failure_history=[
                {"attempt": 0, "reason": "regex miss"},
                {"attempt": 1, "reason": "syntax error"},
            ],
            active_step_attempt=2,
            last_correction_prompt="apply hint",
        )
        repo.save_checkpoint("pb_003", cp)
        loaded = repo.load_checkpoint("pb_003")
        assert loaded.failure_history == cp.failure_history
        assert loaded.active_step_attempt == 2
        assert loaded.last_correction_prompt == "apply hint"

    def test_schedule_resume_sets_iso_timestamp(self, tmp_path: Path):
        repo = self._make_repo(tmp_path)
        repo.save_checkpoint("pb_004", _make_sample_checkpoint())
        resume_at = repo.schedule_resume("pb_004", delay_minutes=5)
        assert isinstance(resume_at, datetime)
        loaded = repo.load_checkpoint("pb_004")
        assert loaded.scheduled_resume_at is not None
        # 確認可被解析為 ISO 8601
        datetime.fromisoformat(loaded.scheduled_resume_at)

    def test_scheduled_resume_is_readable_by_the_consumer(self, tmp_path: Path):
        """R81（HLM-S1-02）：本後端寫下的 `scheduled_resume_at`，消費端必須算得出正數秒。

        為何要這一條而不是再加一支掃描器：既有 6 條契約只驗「欄位存在且解析得出
        datetime」，於是「產出 aware、消費端只吃 naive → 靜默回 0.0」這個組合在
        每一個後端上都是綠的。0.0 的語意是「立刻續跑」——`resume_delay_minutes: 30`
        會變成 0 秒，`max_auto_resumes` 有幾次就連燒幾次，而且只留一行 warning。
        本條刻意跨後端對稱，因為缺陷只在**某一個**後端上長出來。
        """
        repo = self._make_repo(tmp_path)
        repo.save_checkpoint("pb_006", _make_sample_checkpoint())
        repo.schedule_resume("pb_006", delay_minutes=30)
        loaded = repo.load_checkpoint("pb_006")
        secs = seconds_until_resume(loaded.scheduled_resume_at)
        assert 0 < secs <= 1800, (
            f"{type(repo).__name__} 寫下 {loaded.scheduled_resume_at!r}，"
            f"消費端卻算出 {secs}s（0.0＝不等就續跑）"
        )

    def test_overwrite_preserves_atomicity(self, tmp_path: Path):
        """先 save 一次，再 save 一次（不同內容），讀取應為最新版。"""
        repo = self._make_repo(tmp_path)
        cp1 = _make_sample_checkpoint(step_idx=0, step_id="T01")
        cp2 = _make_sample_checkpoint(step_idx=4, step_id="T05")
        repo.save_checkpoint("pb_005", cp1)
        repo.save_checkpoint("pb_005", cp2)
        loaded = repo.load_checkpoint("pb_005")
        assert loaded.step_idx == 4
        assert loaded.step_id == "T05"


# ──────────────────────────────────────────────
# 具體後端繼承（PG backend 留待 Phase 6 加入）
# ──────────────────────────────────────────────
class TestFileStateRepositoryContract(IStateRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        return FileStateRepository(checkpoint_dir=str(tmp_path))


class TestInMemoryStateRepositoryContract(IStateRepositoryContract):
    def _make_repo(self, tmp_path: Path):
        return InMemoryStateRepository()


# ──────────────────────────────────────────────
# DEF-101-384（R47）：playbook_id 落地檔名 Windows 相容性淨化
# （行為級：檢查磁碟上真實落地的檔名，比照
#  test_rtm_file_sink.py::test_reserved_device_name_not_written_bare）
# ──────────────────────────────────────────────
class TestFileStateRepositoryPlaybookIdSanitization:
    def test_forbidden_char_playbook_id_sanitized_on_disk(self, tmp_path: Path):
        """playbook_id 含 Windows 禁用字元（如 ':'）時，落地檔名須淨化，
        不可裸露寫入（否則 Windows 上 open() 會拋未捕捉的 OSError）。"""
        repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        playbook_id = "weird:name"
        repo.save_checkpoint(playbook_id, _make_sample_checkpoint())
        files = list(tmp_path.glob("*.checkpoint.json"))
        assert len(files) == 1
        assert ":" not in files[0].name
        assert files[0].name == f"{_sanitize_log_filename(playbook_id)}.checkpoint.json"
        loaded = repo.load_checkpoint(playbook_id)
        assert loaded is not None
        assert loaded.step_id == "T03"

    def test_reserved_device_name_playbook_id_not_written_bare(self, tmp_path: Path):
        """playbook_id 恰為 Windows 保留裝置名（CON/NUL/COM1/...）時，
        落地檔名須帶逃逸前導底線，不可裸露寫入。"""
        repo = FileStateRepository(checkpoint_dir=str(tmp_path))
        for reserved in ("CON", "con", "NUL", "PRN", "COM1", "LPT9"):
            repo.save_checkpoint(reserved, _make_sample_checkpoint())
            bare = tmp_path / f"{reserved}.checkpoint.json"
            assert not bare.exists(), f"保留裝置名 {reserved!r} 落地檔名裸露無防護"
            sanitized = tmp_path / f"{_sanitize_log_filename(reserved)}.checkpoint.json"
            assert sanitized.is_file()
            loaded = repo.load_checkpoint(reserved)
            assert loaded is not None
            assert loaded.step_id == "T03"
