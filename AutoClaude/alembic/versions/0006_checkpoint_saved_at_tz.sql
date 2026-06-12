-- 0006_checkpoint_saved_at_tz.sql
-- W4-T15 m-3: 確保 checkpoints.saved_at 為 TIMESTAMPTZ（微秒精度 + UTC offset）
--
-- 冪等：若已為 TIMESTAMPTZ，PostgreSQL 不做實際資料轉換。
-- Production 執行：
--   psql -f alembic/versions/0006_checkpoint_saved_at_tz.sql
--
-- ⚠️ 大表 LOCK 風險（W4 三方審查 Arch-W4-Min-1）：
-- ALTER COLUMN TYPE 會觸發 ACCESS EXCLUSIVE LOCK；對 checkpoints 表
-- >1M rows 場景需在低流量視窗執行，或先 ADD COLUMN saved_at_tz +
-- 雙寫 + 切換的 zero-downtime 模式。

BEGIN;

ALTER TABLE checkpoints
    ALTER COLUMN saved_at TYPE TIMESTAMPTZ
    USING saved_at AT TIME ZONE 'UTC';

ALTER TABLE checkpoints
    ALTER COLUMN saved_at SET DEFAULT now();

COMMIT;
