#!/usr/bin/env bash
# docker/pgbackrest/scripts/pgbackrest-entrypoint.sh — pgBackRest sidecar 的進入點（PRD §11.4.3 偏離）
#
# 參數為 "daemon"（映像預設 CMD）時依序做：
#   1. 等 primary 就緒（共用 socket）
#   2. stanza-create（冪等；MinIO 剛啟動等短暫失敗會重試）——此後 primary 的 pgbackrest-archive-wal.sh 才會真的歸檔
#   3. pgbackrest check（只供診斷，失敗不終止）
#   4. 背景：每 METRICS_INTERVAL 秒更新指標檔；busybox httpd 在 9854 提供 /metrics
#   5. 前景：busybox crond（PRD §12.3.3 的排程）
# 其他參數（例如 `docker compose run --rm --no-deps pgbackrest bash restore.sh`）原樣 exec，不做上述準備。
#
# 🔴 不自動做第一次全備：PRD 排程的第一份全備要等週日 02:00；首次部署後請手動 backup-full.sh
#   （自動做會與維運人員手動呼叫的備份搶 backup 鎖，docker/README.md 的驗證流程就會時好時壞）。
set -euo pipefail

if [ "${1:-}" != "daemon" ]; then
  exec "$@"
fi

stanza="aisdlc"
log() { printf '[%s] [pgbackrest-sidecar] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }

log "等待 PostgreSQL（unix socket /var/run/postgresql）…"
ready=0
for _ in $(seq 1 60); do
  if pg_isready -q -h /var/run/postgresql -p 5432 -U "${POSTGRES_USER:-aisdlc}"; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" != "1" ]; then
  log "ERROR: PostgreSQL 在 120 秒內沒有就緒"
  exit 1
fi

created=0
for attempt in $(seq 1 30); do
  if pgbackrest --stanza="$stanza" stanza-create; then
    created=1
    break
  fi
  log "stanza-create 失敗（第 ${attempt} 次；離站儲存可能尚未就緒），5 秒後重試…"
  sleep 5
done
if [ "$created" != "1" ]; then
  log "ERROR: stanza-create 持續失敗，請檢視上方 pgBackRest 輸出（S3 金鑰／endpoint／加密密碼？）"
  exit 1
fi

log "pgbackrest check（診斷用，失敗不終止）…"
if ! pgbackrest --stanza="$stanza" check; then
  log "WARN: check 失敗：WAL 歸檔或備份設定有問題，請檢視上方輸出"
fi

metrics_dir="/run/pgbackrest-metrics"
mkdir -p "$metrics_dir"
(
  while true; do
    /usr/local/bin/pgbackrest-metrics.sh "${metrics_dir}/metrics" || log "WARN: 指標更新失敗"
    sleep "${METRICS_INTERVAL:-60}"
  done
) &
busybox httpd -f -p 9854 -h "$metrics_dir" -u nobody &

log "啟動 crond（時區 ${TZ:-UTC}；排程見 /etc/crontabs/postgres）…"
exec busybox crond -f -d 8 -c /etc/crontabs
