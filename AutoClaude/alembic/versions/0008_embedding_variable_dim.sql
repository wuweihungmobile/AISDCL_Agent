-- 0008_embedding_variable_dim.sql — embedding 變動維度 dual-read
-- SD_Improving_06 W3-2
-- 對應 .py：alembic/versions/0008_embedding_variable_dim.py
BEGIN;

-- Step 1: 新增 4 個欄位（halfvec(1024) + model_id + status + attempts）
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS embedding_v halfvec(1024),
    ADD COLUMN IF NOT EXISTS embedding_model_id text,
    ADD COLUMN IF NOT EXISTS embedding_status text NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS embedding_attempts int NOT NULL DEFAULT 0;

-- Step 2: embedding_status 三態 CHECK
ALTER TABLE knowledge_entries
    ADD CONSTRAINT ck_kb_embedding_status
    CHECK (embedding_status IN ('pending', 'ok', 'failed'));

-- Step 3: 舊欄位 deprecated comment
COMMENT ON COLUMN knowledge_entries.embedding IS
    'DEPRECATED 2026-05-20：將於 2026-11-20 移除，請改用 embedding_v halfvec(1024) + embedding_model_id 過濾';

-- Step 4: per-partition partial HNSW per model_id
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

-- Step 5: retry queue B-tree index
CREATE INDEX IF NOT EXISTS idx_kb_embedding_status
    ON knowledge_entries (embedding_status, embedding_attempts)
    WHERE embedding_status != 'ok';

-- Step 6: model_id filter index
CREATE INDEX IF NOT EXISTS idx_kb_embedding_model_id
    ON knowledge_entries (embedding_model_id)
    WHERE embedding_model_id IS NOT NULL;

COMMIT;
