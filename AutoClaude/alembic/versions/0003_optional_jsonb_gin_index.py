"""0003: optional JSONB GIN index on checkpoints.counters

Revision ID: 0003_jsonb_gin_index
Revises: 0002_m4_run_id_not_null
Create Date: 2026-05-12

P1 #10（DBA）：未來若需 by-counter query（例如：找出 goto_counter > 5 的 playbook）
則執行本 migration 以建立 GIN index，可大幅加速 JSONB 欄位查詢。

目前非必要，僅在確認有 counter query 需求時執行：
    alembic upgrade 0003_jsonb_gin_index
"""

from alembic import op

# revision identifiers
revision = "0003_jsonb_gin_index"
down_revision = "0002_m4_run_id_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GIN index 讓 JSONB @>, ?, ?|, ?& 操作符高效執行
    # 注意：CONCURRENTLY 不支援 transaction block，改用普通 CREATE INDEX
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS
            ix_checkpoints_counters_gin
        ON checkpoints
        USING gin (counters);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS
            ix_checkpoints_failure_history_gin
        ON checkpoints
        USING gin (failure_history);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_checkpoints_counters_gin;")
    op.execute("DROP INDEX IF EXISTS ix_checkpoints_failure_history_gin;")
