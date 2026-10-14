#!/usr/bin/env bash
# docker/pgbackrest/scripts/setup-replica.sh — 從 Primary 建立（或重建）Replica 的資料目錄（PRD §12.2.6）
#
# 與 PRD 的差異（ADR-001 D14-6／G-06）：
#   · PRD 版在 replica 容器內「停 PG → 清資料 → basebackup → pg_ctl start」，但容器內 postgres 是 PID 1，
#     停掉它容器就結束了；改成「只負責把資料目錄準備好」，啟動交給 replica 的 entrypoint／compose。
#   · 由 replica 容器的 entrypoint 在 PGDATA 為空時自動呼叫；「重建 replica」見 docker/README.md：
#       docker compose stop postgres-replica
#       docker compose run --rm --no-deps --entrypoint bash postgres-replica /usr/local/bin/setup-replica.sh --force
#       docker compose up -d postgres-replica
#   · 密碼走 PGPASSWORD（不放指令列）；--checkpoint=fast（預設的 spread 會等數分鐘）；
#     PGAPPNAME 讓 pg_stat_replication.application_name 是 replica1 而不是 walreceiver。
#
# 以 root 執行（Docker 預設）：目錄建立與屬主處理後，以 gosu 降權成 postgres 執行 pg_basebackup。
set -euo pipefail

: "${PGDATA:?PGDATA is required}"
: "${REPLICATION_PASSWORD:?REPLICATION_PASSWORD is required}"

primary_host="${PRIMARY_HOST:-postgres-primary}"
primary_port="${PRIMARY_PORT:-5432}"
slot="${REPLICA_SLOT:-replica_slot_1}"

force=0
if [ "${1:-}" = "--force" ]; then
  force=1
fi

as_postgres() {
  if [ "$(id -u)" = "0" ]; then
    gosu postgres "$@"
  else
    "$@"
  fi
}

if [ -s "${PGDATA}/PG_VERSION" ] && [ "$force" != "1" ]; then
  echo "setup-replica: ${PGDATA} 已有資料；要清空重建請加 --force" >&2
  exit 1
fi

echo "setup-replica: 等待 primary（${primary_host}:${primary_port}）就緒…"
ready=0
for _ in $(seq 1 60); do
  if pg_isready -q -h "$primary_host" -p "$primary_port"; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" != "1" ]; then
  echo "setup-replica: primary 在 120 秒內沒有就緒" >&2
  exit 1
fi

echo "setup-replica: 準備資料目錄 ${PGDATA}…"
if [ "$(id -u)" = "0" ]; then
  install -d -o postgres -g postgres -m 0700 "$PGDATA"
fi
if [ "$force" = "1" ]; then
  as_postgres find "$PGDATA" -mindepth 1 -delete
fi

export PGPASSWORD="$REPLICATION_PASSWORD"
export PGAPPNAME="${REPLICA_APP_NAME:-replica1}"

# slot 不存在就由 pg_basebackup 順便建立（-C）。需要這一步的情境：primary 從 pgBackRest 還原過、或 replica 升格後
# 另建新 replica——replication slot 不在備份內（pg_replslot 被排除），新的 primary 上不會有 replica_slot_1。
# 以複寫協定的 READ_REPLICATION_SLOT 查詢（slot 不存在時回一列全是 NULL）。
slot_type="$(psql "host=${primary_host} port=${primary_port} user=replicator dbname=postgres replication=true" \
  -tA -c "READ_REPLICATION_SLOT ${slot};" | cut -d'|' -f1)"
create_slot=()
if [ -z "$slot_type" ]; then
  echo "setup-replica: primary 上沒有 slot ${slot}，pg_basebackup 會一併建立（-C）。"
  create_slot=(-C)
fi

echo "setup-replica: pg_basebackup（來源 ${primary_host}:${primary_port}，slot ${slot}）…"
as_postgres pg_basebackup \
  -h "$primary_host" -p "$primary_port" -U replicator \
  -D "$PGDATA" -Fp -Xs -P -R -c fast \
  "${create_slot[@]}" -S "$slot"

# 🔴 pg_basebackup 會連 postgresql.auto.conf 一起複製。primary 若做過 pgBackRest restore（PITR），其 auto.conf 內有
#   restore_command = 'pgbackrest … archive-get …'（replica 映像沒有 pgbackrest ⇒ 啟動即 FATAL，實測）以及
#   recovery_target_time／recovery_target_action（standby 會在目標時間點停止復原甚至升格）。
#   只留 -R 寫入的 primary_conninfo／primary_slot_name，其餘復原設定一律移除；
#   replica 的 restore_command 由 postgresql.conf 提供（從 primary 的本地 WAL 歸檔補檔）。
as_postgres sed -i -E '/^(restore_command|recovery_target[a-z_]*|recovery_end_command|archive_cleanup_command)[[:space:]]*=/d' \
  "${PGDATA}/postgresql.auto.conf"

# -R 已建立 standby.signal 並把 primary_conninfo／primary_slot_name 寫進 postgresql.auto.conf
if [ ! -f "${PGDATA}/standby.signal" ]; then
  echo "setup-replica: 找不到 standby.signal（pg_basebackup -R 沒有建立）" >&2
  exit 1
fi
chmod 0700 "$PGDATA"
echo "setup-replica: 完成（standby.signal 已建立）。"
