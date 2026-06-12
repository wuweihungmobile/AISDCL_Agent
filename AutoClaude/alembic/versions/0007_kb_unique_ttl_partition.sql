-- 0007_kb_unique_ttl_partition.sql — KB UNIQUE + 月分區 + 365 天 TTL trigger
-- SD_Improving_06 W3-1
-- 對應 .py：alembic/versions/0007_kb_unique_ttl_partition.py
-- 純 psql 環境 fallback：psql -U autoclaude -d autoclaude -f <此檔>
BEGIN;

-- =============================================================================
-- UPGRADE: knowledge_entries → partitioned table（RANGE recorded_at 月分區）
-- =============================================================================

-- Step 1: rename 既有非分區表
ALTER TABLE knowledge_entries RENAME TO knowledge_entries_legacy;

-- Step 2: 建立新 partitioned table
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

-- Step 3: 12 個月 partition + default partition
DO $do$
DECLARE
    base_month date := date_trunc('month', now())::date;
    partition_name text;
    partition_start date;
    partition_end date;
    i int;
BEGIN
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
    EXECUTE 'CREATE TABLE IF NOT EXISTS knowledge_entries_default '
            'PARTITION OF knowledge_entries DEFAULT;';
END
$do$;

-- Step 4: UNIQUE 約束（含分區鍵）
ALTER TABLE knowledge_entries
    ADD CONSTRAINT uq_kb_class_signature_recorded
    UNIQUE (error_class, error_signature, recorded_at);

-- Step 5: 一般索引
CREATE INDEX IF NOT EXISTS idx_kb_signature
    ON knowledge_entries (error_class, error_signature);
CREATE INDEX IF NOT EXISTS idx_kb_recent
    ON knowledge_entries (recorded_at DESC);

-- Step 6: 資料遷移
INSERT INTO knowledge_entries
    (entry_id, error_class, error_signature, successful_strategy,
     tried_strategies, step_id, outcome, recorded_at, embedding)
SELECT entry_id, error_class, error_signature, successful_strategy,
       tried_strategies, step_id, outcome, recorded_at, embedding
FROM knowledge_entries_legacy
ON CONFLICT DO NOTHING;

-- Step 7: drop legacy 表
DROP TABLE knowledge_entries_legacy;

-- Step 8: per-partition HNSW
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

-- Step 9: TTL cleanup function
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

-- Step 10: TTL trigger（1% 抽樣）
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

COMMIT;
