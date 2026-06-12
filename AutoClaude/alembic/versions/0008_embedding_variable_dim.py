"""0008_embedding_variable_dim — embedding 變動維度 dual-read

Revision ID: 0008_embedding_variable_dim
Revises: 0007_kb_unique_ttl_part
Create Date: 2026-05-20

SD_Improving_06 W3-2（議題 #4 + SD R-SD06-4-1）：
  BGE-M3 出 1024 維、Minimax embo-01 出未知維度，與既有 vector(1536) 衝突。
  禁止直接 ALTER vector(1536) → vector(1024)（會 rewrite 全表 + drop HNSW + 鎖表）。
  改採「新欄位 + dual-read + 6 個月 deprecation」策略：

新增欄位：
  - embedding_v          halfvec(1024)   半精度向量（節省一半儲存空間）
  - embedding_model_id   text            BGE-M3 / Minimax embo-01 等 model 識別
  - embedding_status     text            pending / ok / failed（PM #9 三態）
  - embedding_attempts   int             retry 次數（5 次告警，PM #9）

partial HNSW per model_id：
  - 對每個 partition 建立 (embedding_v IS NOT NULL) WHERE 子句的 HNSW
  - 查詢時加 WHERE embedding_model_id = :active_model filter

⚠️ point-of-no-return：新欄位若已有查詢流量則不可 downgrade；
   downgrade 改前滾修補（drop 新欄位 + 重建 + 全量重 embed）。

對應 contract test：tests/contract/test_alembic_0008_dual_read.py（≥ 6 case）。
"""
from __future__ import annotations

revision = "0008_embedding_variable_dim"
down_revision = "0007_kb_unique_ttl_part"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- =============================================================================
-- 0008: 新欄位 + per-partition partial HNSW per model_id（dual-read 模式）
-- =============================================================================

-- Step 1: 新增 4 個欄位至 partitioned table（會自動傳播至所有子分區）
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS embedding_v halfvec(1024),
    ADD COLUMN IF NOT EXISTS embedding_model_id text,
    ADD COLUMN IF NOT EXISTS embedding_status text NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS embedding_attempts int NOT NULL DEFAULT 0;

-- Step 2: embedding_status 三態 CHECK 約束（PM #9）
ALTER TABLE knowledge_entries
    ADD CONSTRAINT ck_kb_embedding_status
    CHECK (embedding_status IN ('pending', 'ok', 'failed'));

-- Step 3: 標記舊欄位 embedding vector(1536) 為 deprecated（comment-only，保留 6 個月）
COMMENT ON COLUMN knowledge_entries.embedding IS
    'DEPRECATED 2026-05-20：將於 2026-11-20 移除，請改用 embedding_v halfvec(1024) + embedding_model_id 過濾';

-- Step 4: per-partition partial HNSW per model_id（新欄位）
DO $do$
DECLARE
    p record;
    idx_name text;
BEGIN
    FOR p IN
        SELECT c.relname AS part_name
        FROM pg_inherits i
        JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'knowledge_entries'::regclass
    LOOP
        idx_name := 'idx_kb_embedding_v_hnsw_' || p.part_name;
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON %I USING hnsw '
            '(embedding_v halfvec_cosine_ops) WITH (m = 16, ef_construction = 64) '
            'WHERE embedding_v IS NOT NULL AND embedding_model_id IS NOT NULL;',
            idx_name, p.part_name
        );
    END LOOP;
END
$do$;

-- Step 5: B-tree index for embedding_status filter (retry queue lookup)
CREATE INDEX IF NOT EXISTS idx_kb_embedding_status
    ON knowledge_entries (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';

-- Step 6: model_id index for filter
CREATE INDEX IF NOT EXISTS idx_kb_embedding_model_id
    ON knowledge_entries (embedding_model_id)
    WHERE embedding_model_id IS NOT NULL;
"""


_DOWNGRADE_SQL = r"""
-- ⚠️ point-of-no-return：若已有查詢流量則不可 downgrade
-- 此 downgrade 僅供 staging dry-run / 開發環境使用
DROP INDEX IF EXISTS idx_kb_embedding_model_id;
DROP INDEX IF EXISTS idx_kb_embedding_status;

-- Drop per-partition partial HNSW for embedding_v
DO $do$
DECLARE
    p record;
    idx_name text;
BEGIN
    FOR p IN
        SELECT c.relname AS part_name
        FROM pg_inherits i
        JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'knowledge_entries'::regclass
    LOOP
        idx_name := 'idx_kb_embedding_v_hnsw_' || p.part_name;
        EXECUTE format('DROP INDEX IF EXISTS %I;', idx_name);
    END LOOP;
END
$do$;

-- Drop CHECK 約束與新欄位
ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS ck_kb_embedding_status;
ALTER TABLE knowledge_entries
    DROP COLUMN IF EXISTS embedding_attempts,
    DROP COLUMN IF EXISTS embedding_status,
    DROP COLUMN IF EXISTS embedding_model_id,
    DROP COLUMN IF EXISTS embedding_v;

-- 還原舊 embedding comment
COMMENT ON COLUMN knowledge_entries.embedding IS NULL;
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0008_embedding_variable_dim.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
