#!/usr/bin/env bash
# docker/postgres/replica/entrypoint.sh — Replica 容器的進入點（ADR-001 D14-6）
#
# PGDATA 為空 ⇒ 先呼叫 setup-replica.sh 從 primary 做 pg_basebackup（-R -S replica_slot_1），
# 再把控制權交給官方映像的 docker-entrypoint.sh（它偵測到資料目錄已有資料，會略過 initdb，
# 以 standby 模式啟動 postgres）。已有資料（容器重啟）⇒ 直接啟動，不碰資料。
#
# compose 以 `entrypoint: ["bash", "/usr/local/bin/replica-entrypoint.sh"]` 呼叫（不依賴 exec 位元）。
set -euo pipefail

: "${PGDATA:?PGDATA is required}"

if [ ! -s "${PGDATA}/PG_VERSION" ]; then
  echo "[replica] PGDATA 為空，從 ${PRIMARY_HOST:-postgres-primary} 建立基礎備份（pg_basebackup -R -S replica_slot_1）…"
  bash /usr/local/bin/setup-replica.sh
else
  if [ -f "${PGDATA}/standby.signal" ]; then
    echo "[replica] 偵測到既有資料目錄（standby.signal 存在），以 standby 模式啟動。"
  else
    echo "[replica] ⚠ 既有資料目錄沒有 standby.signal：這個節點將以 PRIMARY 身分啟動（升格後的節點屬預期；否則請重建 replica）。" >&2
  fi
fi

exec docker-entrypoint.sh "$@"
