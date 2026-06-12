"""0004: pgvector extension + knowledge_entries embedding column

Revision ID: 0004_pgvector
Revises: 0002_m4_run_id_not_null
Create Date: 2026-05-14

向 knowledge_entries 加入 embedding vector(1536) 欄位，
並建立 HNSW cosine index，啟用語意相似度查詢（ANN search）。

前置：DB superuser 須先執行 CREATE EXTENSION IF NOT EXISTS vector;
"""

from alembic import op

revision = "0004_pgvector"
down_revision = "0002_m4_run_id_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute(
        "ALTER TABLE knowledge_entries "
        "ADD COLUMN IF NOT EXISTS embedding vector(1536);"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_kb_embedding_hnsw
            ON knowledge_entries
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_kb_embedding_hnsw;")
    op.execute(
        "ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS embedding;"
    )
