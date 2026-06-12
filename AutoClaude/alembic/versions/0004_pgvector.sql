-- AutoClaude pgvector migration（Phase 6 向量查詢擴充）
-- 為 knowledge_entries 加入 embedding 欄位，啟用語意相似度搜尋
-- 可直接以 psql 執行，或由 0004_pgvector.py 調用
--
-- 前置需求：superuser 執行 CREATE EXTENSION，或 DB 已預先安裝
--   sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

-- ──────────────────────────────────────────────
-- Step 1：啟用 pgvector extension（需 superuser 或 pg_extension_owner）
-- ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ──────────────────────────────────────────────
-- Step 2：knowledge_entries 加入 embedding 欄位（nullable，向下相容）
--   維度 1536 對應 text-embedding-3-small / text-embedding-ada-002
-- ──────────────────────────────────────────────
ALTER TABLE knowledge_entries
    ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- ──────────────────────────────────────────────
-- Step 3：HNSW index（cosine 距離），加速 ANN 語意查詢
--   m=16, ef_construction=64 為 pgvector 推薦預設值（平衡精度/速度）
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_kb_embedding_hnsw
    ON knowledge_entries
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
