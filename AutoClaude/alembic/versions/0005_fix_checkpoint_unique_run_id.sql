-- 0005_fix_checkpoint_unique_run_id.sql
-- C-6 修復：checkpoints 表 playbook_id 唯一索引 → run_id 唯一索引
-- 前置條件：0002_m4_run_id_not_null 已執行（run_id NOT NULL）
--
-- 使用 CONCURRENTLY 避免 DDL 鎖影響生產環境。
-- 注意：CONCURRENTLY 不可在交易內執行，psql 直接執行即可。

-- 1. 刪除舊索引
DROP INDEX IF EXISTS idx_ck_playbook;

-- 2. 建立新的 run_id 唯一索引（CONCURRENTLY 不鎖表）
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_ck_run_id ON checkpoints(run_id);
