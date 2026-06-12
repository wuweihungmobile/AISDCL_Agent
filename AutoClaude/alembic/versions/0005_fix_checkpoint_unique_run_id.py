"""0005_fix_checkpoint_unique_run_id — checkpoints 表 unique index 修正

Revision ID: 0005_fix_checkpoint_unique_run_id
Revises: 0004_pgvector
Create Date: 2026-05-15

C-6 修復：checkpoints.playbook_id 上的 unique=True 索引設計有誤，
多 run 場景（同一 playbook 多次執行）會觸發 ON CONFLICT 覆蓋舊記錄，
導致只保留最新一次 run 的 checkpoint，舊資料遺失。

修正：改為 run_id 唯一索引（每次 run 獨立存在）。

注意：CONCURRENTLY 不可在 Alembic 自動管理的交易內執行；
      此 migration 改呼叫獨立 SQL 檔（0005_fix_checkpoint_unique_run_id.sql）
      並設定 transaction=False。
"""
from __future__ import annotations

revision = "0005_fix_checkpoint_unique_run_id"
down_revision = "0004_pgvector"
branch_labels = None
depends_on = None

try:
    from alembic import op
    import sqlalchemy as sa
    _alembic_available = True
except ImportError:
    _alembic_available = False


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0005_fix_checkpoint_unique_run_id.sql"
        )
    # C-C 修復：移除 deprecated op.get_bind()（Alembic 2.0+）
    # Dev/CI：使用 op.execute() 於 Alembic 事務內執行（不使用 CONCURRENTLY）
    # Production/Live DB：請直接使用 SQL 檔（支援 CONCURRENTLY 不鎖表）：
    #   psql -f alembic/versions/0005_fix_checkpoint_unique_run_id.sql
    op.execute(sa.text("DROP INDEX IF EXISTS idx_ck_playbook;"))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ck_run_id ON checkpoints(run_id);"
    ))


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(sa.text("DROP INDEX IF EXISTS idx_ck_run_id;"))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_ck_playbook ON checkpoints(playbook_id);"
    ))
