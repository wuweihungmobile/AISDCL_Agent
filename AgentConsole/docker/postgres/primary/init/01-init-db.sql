-- docker/postgres/primary/init/01-init-db.sql — 首次初始化（PRD §11.8；在 POSTGRES_DB 內以超級使用者執行）
-- 🔴 不在此建表：Console 九張表由後端 Flyway（V1__init.sql）擁有；AutoClaude 的 alembic 在 public schema。

-- pgvector：AutoClaude 與 Console 共用同一個映像／資料庫
CREATE EXTENSION IF NOT EXISTS vector;
-- 查詢效能監控（shared_preload_libraries 已在 postgresql.conf 設定；postgres_exporter 的 stat_statements 收集器讀它）
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Console 專屬 schema（Flyway: spring.flyway.schemas=console；Bridge: BRIDGE_DB_SCHEMA=console）
CREATE SCHEMA IF NOT EXISTS console;
