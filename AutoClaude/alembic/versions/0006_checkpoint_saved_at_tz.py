"""0006_checkpoint_saved_at_tz — checkpoints.saved_at TIMESTAMPTZ 對齊

Revision ID: 0006_checkpoint_saved_at_tz
Revises: 0005_fix_checkpoint_unique_run_id
Create Date: 2026-05-15

W4-T15 m-3：確保 checkpoints.saved_at 使用 TIMESTAMP WITH TIME ZONE
（TIMESTAMPTZ），提供原生微秒精度 + UTC offset，符合多 run/多時區情境
的時序需求。

注意：早期 schema（0001_initial）已使用 TIMESTAMPTZ；本 migration 為
**冪等對齊（idempotent alignment）**：若欄位已為 TIMESTAMPTZ，
ALTER COLUMN ... TYPE TIMESTAMPTZ USING saved_at AT TIME ZONE 'UTC'
仍可安全執行（PostgreSQL 不做實際資料轉換）。

⚠️ **大表 LOCK 風險（W4 三方審查 Arch-W4-Min-1）**：
ALTER COLUMN TYPE 會觸發 ACCESS EXCLUSIVE LOCK；
對 checkpoints 表 >1M rows 場景需在低流量視窗執行，或先
ADD COLUMN saved_at_tz + 雙寫 + 切換的 zero-downtime 模式。
"""
from __future__ import annotations

revision = "0006_checkpoint_saved_at_tz"
down_revision = "0005_fix_checkpoint_unique_run_id"
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
            "alembic 未安裝。請改用：psql -f alembic/versions/0006_checkpoint_saved_at_tz.sql"
        )
    # 冪等：若已為 TIMESTAMPTZ，PostgreSQL 不會做實際資料轉換
    op.execute(sa.text(
        "ALTER TABLE checkpoints "
        "ALTER COLUMN saved_at TYPE TIMESTAMPTZ "
        "USING saved_at AT TIME ZONE 'UTC';"
    ))
    op.execute(sa.text(
        "ALTER TABLE checkpoints "
        "ALTER COLUMN saved_at SET DEFAULT now();"
    ))


def downgrade() -> None:
    if not _alembic_available:
        return
    # 不建議降級（會遺失時區資訊），但提供路徑
    op.execute(sa.text(
        "ALTER TABLE checkpoints "
        "ALTER COLUMN saved_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING saved_at AT TIME ZONE 'UTC';"
    ))
