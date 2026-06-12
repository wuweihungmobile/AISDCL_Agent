"""0007_kb_unique_ttl_partition — KB UNIQUE + 月分區 + 365 天 TTL trigger

Revision ID: 0007_kb_unique_ttl_part
Revises: 0006_checkpoint_saved_at_tz
Create Date: 2026-05-20

SD_Improving_06 W3-1（PM #5 KB 數據保留 365 天 + AC5-5 月分區）：
  - knowledge_entries 改造為 partitioned table（RANGE recorded_at 月分區）
  - 12 個月 partition + default partition（共 13 個子表）
  - UNIQUE (error_class, error_signature, recorded_at) — PG 限制 unique 必須含分區鍵
  - per-partition HNSW (vector_cosine_ops, m=16, ef_construction=64)
  - TTL function kb_ttl_cleanup() + AFTER INSERT trigger（1% 抽樣觸發避免熱路徑開銷）

⚠️ DESTRUCTIVE：knowledge_entries 將被 rename → 新建 → 遷移 → drop 舊表。
   downgrade 可恢復為非分區表，但是 destructive（涉及 table 重建）。

對應 contract test：tests/contract/test_alembic_0007_ttl.py（≥ 8 case）。
SD_06 §11 回退策略：✅ downgrade -1（純結構 + 資料遷移）。
"""
from __future__ import annotations

revision = "0007_kb_unique_ttl_part"
down_revision = "0006_checkpoint_saved_at_tz"
branch_labels = None
depends_on = None

try:
    from alembic import op
    _alembic_available = True
except ImportError:
    _alembic_available = False


_UPGRADE_SQL = r"""
-- Step 1: rename 既有非分區表
ALTER TABLE knowledge_entries RENAME TO knowledge_entries_legacy;

-- Step 2: 建立新 partitioned table（PARTITION BY RANGE recorded_at）
--   PG 限制：partitioned table 的 PK 必須含 partition key
CREATE TABLE knowledge_entries (
    entry_id            uuid        NOT NULL DEFAULT gen_random_uuid(),
    error_class         text        NOT NULL,
    error_signature     text        NOT NULL,
    successful_strategy text,
    tried_strategies    text[]      NOT NULL DEFAULT '{}'::text[],
    step_id             text        NOT NULL,
    outcome             text        NOT NULL,
    recorded_at         timestamptz NOT NULL DEFAULT now(),
    embedding           vector(1536),
    CONSTRAINT knowledge_entries_outcome_check
        CHECK (outcome = ANY (ARRAY['success'::text, 'escalation'::text])),
    PRIMARY KEY (entry_id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Step 3: 建立 12 個月 partition + default partition
DO $do$
DECLARE
    base_month date := date_trunc('month', now())::date;
    partition_name text;
    partition_start date;
    partition_end date;
    i int;
BEGIN
    -- 過去 1 個月 + 當月 + 未來 10 個月 = 12 個 partition
    FOR i IN -1..10 LOOP
        partition_start := base_month + (i * INTERVAL '1 month')::interval;
        partition_end   := base_month + ((i + 1) * INTERVAL '1 month')::interval;
        partition_name  := 'knowledge_entries_' || to_char(partition_start, 'YYYY_MM');
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF knowledge_entries '
            'FOR VALUES FROM (%L) TO (%L);',
            partition_name, partition_start, partition_end
        );
    END LOOP;
    -- default partition：超出 12 個月範圍的 row 落入此處
    EXECUTE 'CREATE TABLE IF NOT EXISTS knowledge_entries_default '
            'PARTITION OF knowledge_entries DEFAULT;';
END
$do$;

-- Step 4: UNIQUE 約束（PG 限制：必須含分區鍵 recorded_at）
ALTER TABLE knowledge_entries
    ADD CONSTRAINT uq_kb_class_signature_recorded
    UNIQUE (error_class, error_signature, recorded_at);

-- Step 5: 一般索引
CREATE INDEX IF NOT EXISTS idx_kb_signature
    ON knowledge_entries (error_class, error_signature);
CREATE INDEX IF NOT EXISTS idx_kb_recent
    ON knowledge_entries (recorded_at DESC);

-- Step 6: 資料遷移（既有 legacy → 新 partitioned table）
INSERT INTO knowledge_entries
    (entry_id, error_class, error_signature, successful_strategy,
     tried_strategies, step_id, outcome, recorded_at, embedding)
SELECT entry_id, error_class, error_signature, successful_strategy,
       tried_strategies, step_id, outcome, recorded_at, embedding
FROM knowledge_entries_legacy
ON CONFLICT DO NOTHING;

-- Step 7: drop legacy 表
DROP TABLE knowledge_entries_legacy;

-- Step 8: per-partition HNSW（partitioned table 不支援 global hnsw，必須建在子表）
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
        idx_name := 'idx_kb_embedding_hnsw_' || p.part_name;
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS %I ON %I USING hnsw '
            '(embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);',
            idx_name, p.part_name
        );
    END LOOP;
END
$do$;

-- Step 9: TTL cleanup function（清除 > 365 天的 row）
CREATE OR REPLACE FUNCTION kb_ttl_cleanup() RETURNS bigint
LANGUAGE plpgsql AS $fn$
DECLARE
    deleted_count bigint;
BEGIN
    DELETE FROM knowledge_entries
    WHERE recorded_at < (now() - INTERVAL '365 days');
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END
$fn$;

-- Step 10: TTL trigger（statement-level + 1% 抽樣觸發避免熱路徑開銷）
CREATE OR REPLACE FUNCTION kb_ttl_trigger_fn() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF random() < 0.01 THEN
        PERFORM kb_ttl_cleanup();
    END IF;
    RETURN NULL;
END
$fn$;

CREATE TRIGGER kb_ttl_trigger
    AFTER INSERT ON knowledge_entries
    FOR EACH STATEMENT
    EXECUTE FUNCTION kb_ttl_trigger_fn();
"""


_DOWNGRADE_SQL = r"""
-- 回退：partitioned → 非分區表（destructive，需資料搬遷）
DROP TRIGGER IF EXISTS kb_ttl_trigger ON knowledge_entries;
DROP FUNCTION IF EXISTS kb_ttl_trigger_fn();
DROP FUNCTION IF EXISTS kb_ttl_cleanup();

-- 暫存資料
CREATE TEMP TABLE _kb_revert_buffer AS
    SELECT entry_id, error_class, error_signature, successful_strategy,
           tried_strategies, step_id, outcome, recorded_at, embedding
    FROM knowledge_entries;

-- 移除 partitioned table 與其子分區
DROP TABLE knowledge_entries CASCADE;

-- 重建非分區表（對齊 0001/0004 schema）
CREATE TABLE knowledge_entries (
    entry_id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    error_class         text        NOT NULL,
    error_signature     text        NOT NULL,
    successful_strategy text,
    tried_strategies    text[]      NOT NULL DEFAULT '{}'::text[],
    step_id             text        NOT NULL,
    outcome             text        NOT NULL,
    recorded_at         timestamptz NOT NULL DEFAULT now(),
    embedding           vector(1536),
    CONSTRAINT knowledge_entries_outcome_check
        CHECK (outcome = ANY (ARRAY['success'::text, 'escalation'::text]))
);

INSERT INTO knowledge_entries
    (entry_id, error_class, error_signature, successful_strategy,
     tried_strategies, step_id, outcome, recorded_at, embedding)
SELECT * FROM _kb_revert_buffer;
DROP TABLE _kb_revert_buffer;

CREATE INDEX idx_kb_signature ON knowledge_entries (error_class, error_signature);
CREATE INDEX idx_kb_recent ON knowledge_entries (recorded_at DESC);
CREATE INDEX idx_kb_embedding_hnsw
    ON knowledge_entries USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
"""


def upgrade() -> None:
    if not _alembic_available:
        raise RuntimeError(
            "alembic 未安裝。請改用：psql -f alembic/versions/0007_kb_unique_ttl_partition.sql"
        )
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    if not _alembic_available:
        return
    op.execute(_DOWNGRADE_SQL)
