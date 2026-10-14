#!/usr/bin/env bash
# docker/postgres/primary/init/02-replication.sh — 在 Primary 上建立 Replication 使用者與 Slot（PRD §12.2.5）
# 只在資料目錄首次初始化時由 docker-entrypoint 執行一次（此腳本由映像 COPY 並設執行位元）。
#
# 與 PRD 的差異：
#   · 密碼用 psql 變數（:'repl_pass'）安全引用，不直接拼進 SQL（密碼含單引號也不會壞）
#   · 沒有 REPLICATION_PASSWORD 就直接失敗（PRD 預設 replicator_pass 是弱密碼）
#   · pg_stat_statements 延伸改在 01-init-db.sql 建立
set -euo pipefail

: "${REPLICATION_PASSWORD:?REPLICATION_PASSWORD is required（.env 內設定）}"

psql -v ON_ERROR_STOP=1 -v repl_pass="$REPLICATION_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
-- 建立 Replication 使用者
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD :'repl_pass';

-- 建立 Replication Slot（replica 以 -S replica_slot_1 取用；slot 讓 primary 保留 replica 尚未收到的 WAL）
SELECT pg_create_physical_replication_slot('replica_slot_1');
EOSQL

echo "Replication user and slot created successfully."
