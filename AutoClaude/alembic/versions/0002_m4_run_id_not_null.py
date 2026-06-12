"""M4: checkpoints.run_id NOT NULL

Revision ID: 0002_m4_run_id_not_null
Revises: 0001_initial
Create Date: 2026-05-12

對應 SD_Improving_03.md v1.1 §1.2 M4 finding：
  - checkpoints.run_id FK 升級為 NOT NULL
  - 灰度保護：先為孤立 checkpoint 補建 playbook_runs 佔位記錄，再設 NOT NULL
"""
from __future__ import annotations

revision = "0002_m4_run_id_not_null"
down_revision = "0001_initial"
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
            "alembic 未安裝。請改用：psql -f alembic/versions/0002_m4_run_id_not_null.sql "
            "或安裝 autoclaude[postgres] 後重試。"
        )
    from pathlib import Path
    sql = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    op.execute(sa.text(sql))


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(sa.text("ALTER TABLE checkpoints ALTER COLUMN run_id DROP NOT NULL;"))
