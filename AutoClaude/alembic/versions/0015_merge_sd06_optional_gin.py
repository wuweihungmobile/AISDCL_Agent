"""0015: merge SD_06 optional JSONB GIN branch (0003) into SD_08 main lineage (0014)

Revision ID: 0015_merge_sd06_optional_gin
Revises: 0003_jsonb_gin_index, 0014_config_audit_log
Create Date: 2026-05-20

對應風險：R-SD09-A-6（zero-trust audit v1.5 五方 Architect/SD 必修項 P0-ARCH-01）

背景：
alembic.script.get_heads() 回傳 ['0003_jsonb_gin_index', '0014_config_audit_log'] 雙 head。
- 0003 為 SD_06 可選 JSONB GIN 分支（depends_on=None，docstring「目前非必要」）
- 0014 為 SD_08 W4 config_audit_log 主線（0001→0002→0004→...→0013→0014）

本 merge revision 將兩 head 合併為單一 head，使 `alembic upgrade head` 不再 ambiguous fail，
為 SD_09 W2 議題 G ADR-SD09-006 落地的 0016_kb_metrics 鋪路。

本 merge 無 schema 異動（純 lineage 合併）。
"""

from alembic import op  # noqa: F401

# revision identifiers
revision = "0015_merge_sd06_optional_gin"
down_revision = ("0003_jsonb_gin_index", "0014_config_audit_log")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
