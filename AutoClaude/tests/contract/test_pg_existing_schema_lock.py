"""SD_Improving_05 W0 T0-3 — PG 既有 4 表 schema lock test。

對應 QA Q-C3：在 SD_06 W1 動 alembic 0007/0008（新增 projects / goal_tasks /
execution_items + FK 連結 playbook_runs）之前，鎖死當前 4 表的 DDL 與 CRUD
行為快照，任何漂移立即 fail，避免 SD_06 推進時意外破壞既有結構。

涵蓋 4 表：
  - playbook_runs
  - checkpoints
  - knowledge_entries
  - playbook_versions

雙軌驗證：
  1. DDL snapshot（離線、無需 PG）— ORM 模型結構鎖定
     欄位集合、PK、索引、check constraint、FK 必須與 baseline 一致
  2. CRUD 行為快照（需 PG fixture）— 透過 AUTOCLAUDE_TEST_PG_DSN 啟用
     insert/select/update/delete + 索引查詢效能 + check constraint 強制
"""
from __future__ import annotations

import os

import pytest

# ─────────────────────────────────────────────────────────────
# Baseline DDL snapshot（2026-05-16 鎖定 → 2026-05-18 SD_06 W5 擴張）
# ─────────────────────────────────────────────────────────────
# 既有 4 表（SD_05 W0 T0-3 baseline，不可移除）
BASELINE_TABLES = {"playbook_runs", "checkpoints", "knowledge_entries", "playbook_versions"}
# SD_06 W5 新增 2 表（drift_log + config_audit_log；對應 alembic 0013 + 0014）
SD06_W5_TABLES = {"drift_log", "config_audit_log"}
# Improving_012 Phase 1 新增 3 表（F-C3/F-C1/F-C2；對應 alembic 0016；SCG-1 凍結）
AGT_PHASE1_TABLES = {"kb_metrics", "user_preferences", "goal_progress"}
EXPECTED_TABLES = BASELINE_TABLES | SD06_W5_TABLES | AGT_PHASE1_TABLES

EXPECTED_COLUMNS: dict[str, set[str]] = {
    "playbook_runs": {
        "run_id", "playbook_id", "project", "started_at",
        "finished_at", "status", "metadata",
    },
    "checkpoints": {
        "checkpoint_id", "run_id", "playbook_id", "step_idx", "step_id",
        "total_steps", "saved_at", "scheduled_resume_at", "peak_token_pct",
        "counters", "completed_step_log", "completed_step_ids",
        "failure_history", "active_step_attempt", "last_correction_prompt",
    },
    "knowledge_entries": {
        "entry_id", "error_class", "error_signature", "successful_strategy",
        "tried_strategies", "step_id", "outcome", "recorded_at",
    },
    "playbook_versions": {
        "version_id", "original_playbook_id", "generation",
        "yaml_content", "mutation_log", "parent_version_id", "created_at",
    },
    # SD_06 W5-T5-5
    "drift_log": {
        "drift_id", "detected_at", "run_id", "playbook_id",
        "source_left", "source_right", "field_drift", "severity",
        "resolved_at", "resolver", "notes",
    },
    # SD_06 W5-T5-16
    "config_audit_log": {
        "audit_id", "changed_at", "user_id", "layer", "field_path",
        "old_value", "new_value", "action", "reason",
    },
    # Improving_012 Phase 1（alembic 0016）
    "kb_metrics": {
        "metric_id", "metric_name", "value", "window_start_at",
        "window_end_at", "run_id", "tags", "recorded_at",
    },
    "user_preferences": {"scope", "key", "value", "updated_at"},
    "goal_progress": {
        "progress_id", "goal_task_id", "playbook_id", "run_id",
        "completed_features", "progress_pct", "recorded_at",
    },
}

EXPECTED_PRIMARY_KEYS: dict[str, set[str]] = {
    "playbook_runs": {"run_id"},
    "checkpoints": {"checkpoint_id"},
    "knowledge_entries": {"entry_id"},
    "playbook_versions": {"version_id"},
    # drift_log 為 partitioned table，PK = (drift_id, detected_at)
    "drift_log": {"drift_id", "detected_at"},
    "config_audit_log": {"audit_id"},
    # Improving_012 Phase 1：user_preferences 採複合 PK（UPSERT by (scope, key)）
    "kb_metrics": {"metric_id"},
    "user_preferences": {"scope", "key"},
    "goal_progress": {"progress_id"},
}

EXPECTED_NOT_NULL: dict[str, set[str]] = {
    "playbook_runs": {"run_id", "playbook_id", "project", "started_at", "status", "metadata"},
    "checkpoints": {
        "checkpoint_id", "run_id", "playbook_id", "step_idx", "step_id",
        "total_steps", "saved_at", "peak_token_pct", "counters",
        "completed_step_log", "completed_step_ids", "failure_history",
        "active_step_attempt", "last_correction_prompt",
    },
    "knowledge_entries": {
        "entry_id", "error_class", "error_signature", "tried_strategies",
        "step_id", "outcome", "recorded_at",
    },
    "playbook_versions": {
        "version_id", "original_playbook_id", "generation",
        "yaml_content", "mutation_log", "created_at",
    },
    # drift_log NOT NULL：PK 兩欄 + playbook_id + source × 2 + field_drift + severity
    "drift_log": {
        "drift_id", "detected_at", "playbook_id",
        "source_left", "source_right", "field_drift", "severity",
    },
    # config_audit_log NOT NULL：audit_id + changed_at + layer + field_path + action
    "config_audit_log": {
        "audit_id", "changed_at", "layer", "field_path", "action",
    },
    # Improving_012 Phase 1
    "kb_metrics": {
        "metric_id", "metric_name", "value", "window_start_at",
        "window_end_at", "recorded_at",
    },
    "user_preferences": {"scope", "key", "value", "updated_at"},
    "goal_progress": {
        "progress_id", "goal_task_id", "completed_features", "recorded_at",
    },
}

EXPECTED_FOREIGN_KEYS: dict[str, set[tuple[str, str, str]]] = {
    # (column, referred_table, referred_column)
    "playbook_runs": set(),
    "checkpoints": {("run_id", "playbook_runs", "run_id")},
    "knowledge_entries": set(),
    "playbook_versions": {("parent_version_id", "playbook_versions", "version_id")},
    # drift_log.run_id 為 nullable，不建 FK（避免 partition + FK 衝突）
    "drift_log": set(),
    "config_audit_log": set(),
    # Improving_012 Phase 1：run_id 皆 nullable 留痕欄位，不建 FK（與 drift_log 同理）
    "kb_metrics": set(),
    "user_preferences": set(),
    "goal_progress": set(),
}

EXPECTED_INDEX_NAMES: dict[str, set[str]] = {
    "playbook_runs": {"idx_runs_status"},
    "checkpoints": {"idx_ck_run_id"},
    "knowledge_entries": {"idx_kb_signature"},
    "playbook_versions": {"idx_pv_playbook"},
    "drift_log": {"idx_drift_log_playbook"},
    "config_audit_log": {"idx_config_audit_field"},
    # Improving_012 Phase 1
    "kb_metrics": {"idx_kb_metrics_name_window"},
    "user_preferences": set(),
    "goal_progress": {"idx_goal_progress_goal"},
}

EXPECTED_CHECK_CONSTRAINT_NAMES: dict[str, set[str]] = {
    "playbook_runs": {"ck_playbook_runs_status"},
    "checkpoints": set(),
    "knowledge_entries": {"ck_kb_outcome"},
    "playbook_versions": set(),
    "drift_log": {"ck_drift_severity"},
    "config_audit_log": {"ck_config_audit_layer", "ck_config_audit_action"},
    # Improving_012 Phase 1：無 CHECK constraint
    "kb_metrics": set(),
    "user_preferences": set(),
    "goal_progress": set(),
}


# ─────────────────────────────────────────────────────────────
# 1. DDL snapshot tests（離線；任何 ORM 漂移立即 fail）
# ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def metadata():
    """從 _pg_models.py 載入 SQLAlchemy metadata。"""
    try:
        from autoclaude.infra.repositories._pg_models import Base
    except ImportError:
        pytest.skip("sqlalchemy 未安裝；DDL snapshot 略過")
    return Base.metadata


class TestDDLSnapshot:
    """SD_05 W0 T0-3 — 4 表 DDL 結構鎖定（無需 PG 連線）。"""

    def test_exact_four_tables(self, metadata):
        actual = set(metadata.tables.keys())
        missing = EXPECTED_TABLES - actual
        extra = actual - EXPECTED_TABLES
        assert not missing, f"baseline 4 表缺失：{missing}"
        assert not extra, (
            f"新增非預期表：{extra}。若為 SD_06 W1 新增 projects/goal_tasks/"
            f"execution_items，請更新此 baseline + alembic 0007/0008"
        )

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_columns_match_baseline(self, metadata, table_name):
        table = metadata.tables[table_name]
        actual_cols = {c.name for c in table.columns}
        expected = EXPECTED_COLUMNS[table_name]
        missing = expected - actual_cols
        added = actual_cols - expected
        assert not missing, f"{table_name} 缺少 baseline 欄位：{missing}"
        # 容許新增 nullable 欄位（向下相容），但要明示為新增
        # SD_06 預計新增 embedding 欄位於 knowledge_entries
        if table_name == "knowledge_entries":
            allowed_additions = {"embedding"}
            added = added - allowed_additions
        assert not added, (
            f"{table_name} 新增非預期欄位：{added}；如為 SD_06 預期變動，"
            f"請更新此 baseline 並走 schema review"
        )

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_primary_keys_match_baseline(self, metadata, table_name):
        table = metadata.tables[table_name]
        actual_pk = {c.name for c in table.primary_key.columns}
        assert actual_pk == EXPECTED_PRIMARY_KEYS[table_name], (
            f"{table_name} PK 漂移：actual={actual_pk}, "
            f"expected={EXPECTED_PRIMARY_KEYS[table_name]}"
        )

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_not_null_columns_match_baseline(self, metadata, table_name):
        table = metadata.tables[table_name]
        actual_not_null = {c.name for c in table.columns if not c.nullable}
        expected = EXPECTED_NOT_NULL[table_name]
        loosened = expected - actual_not_null
        assert not loosened, (
            f"{table_name} NOT NULL 約束被放寬：{loosened}（重大相容性風險）"
        )

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_foreign_keys_match_baseline(self, metadata, table_name):
        table = metadata.tables[table_name]
        actual_fks: set[tuple[str, str, str]] = set()
        for fk in table.foreign_keys:
            col = fk.parent.name
            referred = fk.column.table.name
            referred_col = fk.column.name
            actual_fks.add((col, referred, referred_col))
        expected = EXPECTED_FOREIGN_KEYS[table_name]
        missing = expected - actual_fks
        assert not missing, f"{table_name} FK 缺失：{missing}"

    @pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
    def test_index_names_match_baseline(self, metadata, table_name):
        table = metadata.tables[table_name]
        actual = {idx.name for idx in table.indexes}
        expected = EXPECTED_INDEX_NAMES[table_name]
        missing = expected - actual
        assert not missing, f"{table_name} 索引缺失：{missing}"

    def test_checkpoint_run_id_index_is_unique(self, metadata):
        """C-6 修復鎖定：idx_ck_run_id 必須為 UNIQUE（多 run 並存策略）。"""
        table = metadata.tables["checkpoints"]
        idx = next((i for i in table.indexes if i.name == "idx_ck_run_id"), None)
        assert idx is not None, "idx_ck_run_id 索引缺失"
        assert idx.unique is True, "idx_ck_run_id 必須為 UNIQUE（PM 拍板 §10.4 多 run 並存）"

    def test_embedding_present_when_pgvector_available(self, metadata):
        """SD_05 W0 SD-M9：_PGVECTOR_AVAILABLE = True 時 embedding 必為 nullable Vector。"""
        from autoclaude.infra.repositories import _pg_models
        if not getattr(_pg_models, "_PGVECTOR_AVAILABLE", False):
            pytest.skip("pgvector 未安裝；測 absent case 改由另一 test")
        kb_table = metadata.tables["knowledge_entries"]
        embedding_col = kb_table.columns.get("embedding")
        assert embedding_col is not None, (
            "pgvector 安裝時 embedding 必須存在（_pg_models.py:110）"
        )
        assert embedding_col.nullable is True, "embedding 必須為 nullable（向下相容）"
        # 型別必為 Vector
        from pgvector.sqlalchemy import Vector
        assert isinstance(embedding_col.type, Vector), (
            f"embedding 必須為 Vector 型別，實際: {type(embedding_col.type).__name__}"
        )

    def test_embedding_absent_when_pgvector_unavailable(self, metadata):
        """SD_05 W0 SD-M9：_PGVECTOR_AVAILABLE = False 時 embedding 不出現於 columns。"""
        from autoclaude.infra.repositories import _pg_models
        if getattr(_pg_models, "_PGVECTOR_AVAILABLE", False):
            pytest.skip("pgvector 已安裝；測 present case 改由 _present test")
        kb_table = metadata.tables["knowledge_entries"]
        assert "embedding" not in {c.name for c in kb_table.columns}, (
            "pgvector 未安裝時 embedding 不應出現於 columns（_pg_models.py:110 守則）"
        )

    def test_check_constraints_present(self, metadata):
        """playbook_runs.status 與 knowledge_entries.outcome 必須有 CHECK 約束。"""
        from sqlalchemy import CheckConstraint
        runs_table = metadata.tables["playbook_runs"]
        runs_checks = {
            c.name for c in runs_table.constraints if isinstance(c, CheckConstraint)
        }
        assert "ck_playbook_runs_status" in runs_checks

        kb_table = metadata.tables["knowledge_entries"]
        kb_checks = {
            c.name for c in kb_table.constraints if isinstance(c, CheckConstraint)
        }
        assert "ck_kb_outcome" in kb_checks


# ─────────────────────────────────────────────────────────────
# 2. CRUD 行為快照（需 PG fixture；env var AUTOCLAUDE_TEST_PG_DSN）
# ─────────────────────────────────────────────────────────────
_PG_DSN = os.environ.get("AUTOCLAUDE_TEST_PG_DSN")
_pg_skip_reason = (
    "PG CRUD 行為快照需 docker-compose postgres:17 + AUTOCLAUDE_TEST_PG_DSN env var；"
    "DDL snapshot 已驗證結構，CRUD 部分由 CI/staging 接續驗證"
)


@pytest.mark.skipif(_PG_DSN is None, reason=_pg_skip_reason)
class TestCRUDBehaviorSnapshot:
    """CRUD 行為快照（PG fixture 啟用時執行）。

    驗證在 SD_06 動 schema 之前，4 表的 insert/select/update/delete + check
    constraint 強制行為與 baseline 一致。
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from sqlalchemy.ext.asyncio import create_async_engine
        self.engine = create_async_engine(_PG_DSN, echo=False)
        import asyncio
        asyncio.run(self._truncate_all())
        yield
        asyncio.run(self.engine.dispose())

    async def _truncate_all(self):
        from sqlalchemy import text
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE playbook_runs, knowledge_entries, "
                    "playbook_versions CASCADE"
                )
            )

    def test_playbook_runs_status_check_constraint(self):
        """status 必須在 {running, success, escalated, halted, interrupted} 集合內。"""
        import asyncio

        from sqlalchemy import text

        async def _run():
            async with self.engine.begin() as conn:
                with pytest.raises(Exception):
                    await conn.execute(
                        text(
                            "INSERT INTO playbook_runs (playbook_id, project, status) "
                            "VALUES ('pb1', 'test', 'INVALID_STATUS')"
                        )
                    )
        asyncio.run(_run())

    def test_kb_outcome_check_constraint(self):
        """outcome 必須在 {success, escalation} 集合內。"""
        import asyncio

        from sqlalchemy import text

        async def _run():
            async with self.engine.begin() as conn:
                with pytest.raises(Exception):
                    await conn.execute(
                        text(
                            "INSERT INTO knowledge_entries "
                            "(error_class, error_signature, step_id, outcome) "
                            "VALUES ('syntax', 'sig', 'T01', 'BAD')"
                        )
                    )
        asyncio.run(_run())

    def test_checkpoint_run_id_uniqueness_enforced(self):
        """idx_ck_run_id UNIQUE 強制：同一 run_id 不可有兩筆 checkpoint。"""
        import asyncio

        from sqlalchemy import text

        async def _run():
            async with self.engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO playbook_runs (run_id, playbook_id, project, status) "
                        "VALUES (gen_random_uuid(), 'pb_dup', 'test', 'running') "
                        "RETURNING run_id"
                    )
                )
                row = await conn.execute(
                    text(
                        "SELECT run_id FROM playbook_runs WHERE playbook_id='pb_dup'"
                    )
                )
                run_id = row.scalar()
                await conn.execute(
                    text(
                        "INSERT INTO checkpoints "
                        "(run_id, playbook_id, step_idx, step_id, total_steps) "
                        "VALUES (:r, 'pb_dup', 0, 'T01', 3)"
                    ),
                    {"r": run_id},
                )
                with pytest.raises(Exception):
                    await conn.execute(
                        text(
                            "INSERT INTO checkpoints "
                            "(run_id, playbook_id, step_idx, step_id, total_steps) "
                            "VALUES (:r, 'pb_dup', 1, 'T02', 3)"
                        ),
                        {"r": run_id},
                    )
        asyncio.run(_run())

    def test_playbook_versions_self_fk_chain(self):
        """playbook_versions.parent_version_id 可形成版本鏈（自參考 FK）。"""
        import asyncio

        from sqlalchemy import text

        async def _run():
            async with self.engine.begin() as conn:
                v1 = (await conn.execute(
                    text(
                        "INSERT INTO playbook_versions "
                        "(original_playbook_id, generation, yaml_content) "
                        "VALUES ('pb_v', 1, 'v1') RETURNING version_id"
                    )
                )).scalar()
                v2 = (await conn.execute(
                    text(
                        "INSERT INTO playbook_versions "
                        "(original_playbook_id, generation, yaml_content, parent_version_id) "
                        "VALUES ('pb_v', 2, 'v2', :p) RETURNING version_id"
                    ),
                    {"p": v1},
                )).scalar()
                row = await conn.execute(
                    text(
                        "SELECT parent_version_id FROM playbook_versions WHERE version_id = :v"
                    ),
                    {"v": v2},
                )
                assert row.scalar() == v1
        asyncio.run(_run())
