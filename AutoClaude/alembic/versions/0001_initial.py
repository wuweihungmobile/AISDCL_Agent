"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08

對應 SD_Improving_02.md v1.1 §1.3 PostgreSQL Schema。
等價於 0001_initial.sql；alembic 環境可使用此 .py，純 psql 環境可使用 .sql。
"""
from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


# alembic 框架可選；若未安裝則 noop（提供降級路徑）
try:
    from alembic import op
    import sqlalchemy as sa
    _alembic_available = True
except ImportError:
    _alembic_available = False


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0001_initial.sql "
            "或安裝 autoclaude[postgres] 後重試。"
        )
    # 直接執行 .sql 檔（避免維護兩份 schema）
    from pathlib import Path
    sql = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    op.execute(sa.text(sql))


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute("DROP TABLE IF EXISTS playbook_versions CASCADE;")
    op.execute("DROP TABLE IF EXISTS knowledge_entries CASCADE;")
    op.execute("DROP TABLE IF EXISTS checkpoints CASCADE;")
    op.execute("DROP TABLE IF EXISTS playbook_runs CASCADE;")
