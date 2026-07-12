"""TestPgStateRepositoryContract — 繼承 IStateRepositoryContract（Phase 6）。

對應 SD_Improving_02.md v1.1 §2.8 DoD：
  「PgStateRepository 必先通過 tests/contract/ 全綠才可合併」

當前狀態：
  - PG backend 介面就緒，但需要 docker-compose postgres:17 環境才能執行真實連線
  - 透過環境變數 AUTOCLAUDE_TEST_PG_DSN 設定 fixture；未設定則 skip
  - CI 啟用 PG 測試時：先啟動 docker-compose，再 export AUTOCLAUDE_TEST_PG_DSN，最後跑 pytest
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# 環境條件 skip：未配置 PG fixture 時整個 class 跳過
_PG_DSN = os.environ.get("AUTOCLAUDE_TEST_PG_DSN")
_pg_skip_reason = (
    "PG backend 契約測需 docker-compose postgres:17 + AUTOCLAUDE_TEST_PG_DSN env var；"
    "請參考 SD_Improving_02.md v1.1 §2.8 設置 fixture 後重跑"
)


@pytest.mark.skipif(_PG_DSN is None, reason=_pg_skip_reason)
class TestPgStateRepositoryContract:
    """繼承 IStateRepositoryContract，由 docker-compose CI 啟用。

    當 AUTOCLAUDE_TEST_PG_DSN 設定時：
      - 自動繼承 7 個 state repository 契約測
      - 等同 File / InMemory backend 的 LSP 行為驗證
    """

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path):
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool
        from autoclaude.infra.repositories.pg_state_repository import PgStateRepository

        # SD_09 R56 P0-1f 修復：每個契約測為 sync 方法，內部經 repo._run_async → 各自
        # asyncio.run（建立並關閉獨立 event loop）。預設 QueuePool 會把 asyncpg 連線
        # 快取並綁在「首次 asyncio.run（_truncate）」的 loop；該 loop 關閉後，後續 test
        # body 的 _run_async 取到死 loop 連線 → `'NoneType' object has no attribute 'send'`
        # / `Event loop is closed`（Win/Linux 皆然，故 CI pg-contract 從未真綠）。
        # NullPool 不跨呼叫快取連線 → 每次 acquire 在當前 loop 全新建立，根治此問題。
        self.engine = create_async_engine(_PG_DSN, echo=False, poolclass=NullPool)
        self.repo = PgStateRepository(self.engine)
        # 測試前清空（避免跨測試污染）
        import asyncio
        asyncio.run(self._truncate())
        yield
        asyncio.run(self.engine.dispose())

    async def _truncate(self):
        from sqlalchemy import text
        async with self.engine.begin() as conn:
            # M1 修正：playbook_runs 為 checkpoints 的父表，須先清父表（CASCADE 清子表）
            await conn.execute(text("TRUNCATE playbook_runs CASCADE"))

    # 7 個契約測（與 IStateRepositoryContract 對齊；待 PG 環境啟用後解 skip）
    def test_save_load_roundtrip(self):
        from .test_state_repository_contract import _make_sample_checkpoint
        cp = _make_sample_checkpoint()
        self.repo.save_checkpoint("pb_pg_001", cp)
        loaded = self.repo.load_checkpoint("pb_pg_001")
        assert loaded is not None
        assert loaded.step_id == cp.step_id

    def test_load_missing_returns_none(self):
        assert self.repo.load_checkpoint("nonexistent_pg_id") is None

    def test_clear_idempotent(self):
        self.repo.clear_checkpoint("pb_pg_002")
        self.repo.clear_checkpoint("pb_pg_002")  # idempotent

    def test_counter_persistence_round_trip(self):
        """Gap-042/048：跨 PG round-trip 計數器完整保留。"""
        from .test_state_repository_contract import _make_sample_checkpoint
        cp = _make_sample_checkpoint(
            goto_counter={"T01": 5, "T03": 2},
            step_evolution_counter={"T05": 3},
        )
        self.repo.save_checkpoint("pb_pg_003", cp)
        loaded = self.repo.load_checkpoint("pb_pg_003")
        assert loaded.goto_counter == cp.goto_counter
        assert loaded.step_evolution_counter == cp.step_evolution_counter

    def test_failure_history_round_trip(self):
        from .test_state_repository_contract import _make_sample_checkpoint
        cp = _make_sample_checkpoint(
            failure_history=[{"attempt": 0, "reason": "regex miss"}],
            active_step_attempt=2,
        )
        self.repo.save_checkpoint("pb_pg_004", cp)
        loaded = self.repo.load_checkpoint("pb_pg_004")
        assert loaded.failure_history == cp.failure_history
        assert loaded.active_step_attempt == 2

    def test_schedule_resume_sets_iso_timestamp(self):
        from datetime import datetime
        from .test_state_repository_contract import _make_sample_checkpoint
        self.repo.save_checkpoint("pb_pg_005", _make_sample_checkpoint())
        resume_at = self.repo.schedule_resume("pb_pg_005", delay_minutes=5)
        assert isinstance(resume_at, datetime)

    def test_overwrite_preserves_atomicity(self):
        from .test_state_repository_contract import _make_sample_checkpoint
        cp1 = _make_sample_checkpoint(step_idx=0, step_id="T01")
        cp2 = _make_sample_checkpoint(step_idx=4, step_id="T05")
        self.repo.save_checkpoint("pb_pg_006", cp1)
        self.repo.save_checkpoint("pb_pg_006", cp2)
        loaded = self.repo.load_checkpoint("pb_pg_006")
        assert loaded.step_idx == 4

    def test_playbook_run_record_created_on_first_save(self):
        """M4：save_checkpoint 首次呼叫時應自動建立 playbook_runs 記錄。"""
        import asyncio
        from sqlalchemy import text
        from .test_state_repository_contract import _make_sample_checkpoint
        cp = _make_sample_checkpoint()
        self.repo.save_checkpoint("pb_pg_m4_001", cp)

        async def _count():
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM playbook_runs WHERE playbook_id = 'pb_pg_m4_001'")
                )
                return result.scalar()

        count = asyncio.run(_count())
        assert count == 1, "首次 save_checkpoint 應自動建立一筆 playbook_runs 記錄"

    def test_total_steps_updated_on_upsert(self):
        """C3 修正：UPSERT 時 total_steps 應反映最新值（演化後步驟增加場景）。"""
        from .test_state_repository_contract import _make_sample_checkpoint
        cp1 = _make_sample_checkpoint(step_idx=0, step_id="T01", total_steps=3)
        cp2 = _make_sample_checkpoint(step_idx=1, step_id="T02", total_steps=5)
        self.repo.save_checkpoint("pb_pg_m4_002", cp1)
        self.repo.save_checkpoint("pb_pg_m4_002", cp2)
        loaded = self.repo.load_checkpoint("pb_pg_m4_002")
        assert loaded.total_steps == 5, "演化後 total_steps 應更新至 5"

    def test_three_tier_run_marks_run_kind(self):
        """DEF-101-051：帶 goal_task_id 的 checkpoint → run 標記 three_tier 並滿足 0017 CHECK。

        走真實 save_checkpoint 流程（Rule 9，非 fake 路徑）：先 seed 一條真實
        projects→goal_tasks（三層模型上游產物），再存帶 goal_task_id 的 checkpoint，
        驗證 playbook_runs.run_kind='three_tier' 且 goal_task_id 正確寫入。此測試證明
        判別欄非裝飾——three_tier 分支確實由資料驅動、被真實流程走到。
        """
        import asyncio
        from sqlalchemy import text
        from .test_state_repository_contract import _make_sample_checkpoint

        async def _seed_goal_task():
            async with self.engine.begin() as conn:
                # 冪等：清前次遺留（projects.name 唯一；ON DELETE CASCADE 連帶清 goal_tasks）
                await conn.execute(text(
                    "DELETE FROM projects WHERE name = 'def101051-proj'"
                ))
                pid = (await conn.execute(text(
                    "INSERT INTO projects (name) VALUES ('def101051-proj') "
                    "RETURNING project_id"
                ))).scalar()
                gid = (await conn.execute(text(
                    "INSERT INTO goal_tasks (project_id, title, depth) "
                    "VALUES (:pid, 'root goal', 1) RETURNING goal_task_id"
                ), {"pid": pid})).scalar()
                return str(gid)

        goal_id = asyncio.run(_seed_goal_task())
        cp = _make_sample_checkpoint(goal_task_id=goal_id)
        self.repo.save_checkpoint("pb_pg_three_tier", cp)

        async def _fetch_run():
            async with self.engine.connect() as conn:
                return (await conn.execute(text(
                    "SELECT run_kind, goal_task_id::text FROM playbook_runs "
                    "WHERE playbook_id = 'pb_pg_three_tier'"
                ))).one()

        run_kind, gtid = asyncio.run(_fetch_run())
        assert run_kind == "three_tier", "帶 goal_task_id 的 run 應標記 three_tier"
        assert gtid == goal_id, "goal_task_id 應正確寫入 playbook_runs"

    def test_non_uuid_goal_falls_back_to_standalone(self):
        """DEF-101-051 guard：非 UUID goal_task_id（如 fixture GT-xxx）不得弄垮 checkpoint save。

        稽核標記瑕疵不應犧牲續跑韌性——`_ensure_run_id` 對非 UUID 值 warn + 退回 standalone，
        而非讓 `uuid.UUID(...)` raise ValueError 使整筆 save_checkpoint 失敗。
        """
        import asyncio
        from sqlalchemy import text
        from .test_state_repository_contract import _make_sample_checkpoint

        cp = _make_sample_checkpoint(goal_task_id="GT-001-A")  # 非 UUID（canonical fixture 格式）
        self.repo.save_checkpoint("pb_pg_nonuuid", cp)  # 不應 raise

        async def _fetch_run():
            async with self.engine.connect() as conn:
                return (await conn.execute(text(
                    "SELECT run_kind, goal_task_id FROM playbook_runs "
                    "WHERE playbook_id = 'pb_pg_nonuuid'"
                ))).one()

        run_kind, gtid = asyncio.run(_fetch_run())
        assert run_kind == "standalone", "非 UUID goal 應退回 standalone"
        assert gtid is None, "非 UUID goal 不應寫入 playbook_runs.goal_task_id"


# ──────────────────────────────────────────────
# 即使 PG 不可用，仍驗證骨架可 import 且 raise 友善訊息
# ──────────────────────────────────────────────
class TestPgRepositoryImportSafety:
    def test_pg_state_repository_raises_import_error_when_no_sqlalchemy(self):
        """當 sqlalchemy 未安裝時 PgStateRepository(...) 應拋 ImportError。"""
        try:
            import sqlalchemy  # noqa
            pytest.skip("sqlalchemy 已安裝，無法測試 ImportError 路徑")
        except ImportError:
            pass

        from autoclaude.infra.repositories.pg_state_repository import PgStateRepository
        with pytest.raises(ImportError, match="sqlalchemy"):
            PgStateRepository(engine=object())

    def test_migrate_script_exists(self):
        path = Path(__file__).resolve().parents[2] / "scripts" / "migrate_file_to_pg.py"
        assert path.exists(), "Phase 6 DoD 要求 scripts/migrate_file_to_pg.py 存在"

    def test_alembic_initial_migration_exists(self):
        sql = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0001_initial.sql"
        py = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0001_initial.py"
        assert sql.exists() and py.exists(), \
            "Phase 6 DoD 要求 alembic initial migration（.sql + .py）存在"

    def test_pyproject_postgres_extras_exists(self):
        toml = Path(__file__).resolve().parents[2] / "pyproject.toml"
        text = toml.read_text(encoding="utf-8")
        assert "postgres = [" in text, \
            "Phase 6 DoD 要求 pyproject.toml 含 [project.optional-dependencies] postgres group"
        assert "sqlalchemy" in text
        assert "asyncpg" in text
        assert "alembic" in text
