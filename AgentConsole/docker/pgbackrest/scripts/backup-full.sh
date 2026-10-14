#!/usr/bin/env bash
# docker/pgbackrest/scripts/backup-full.sh — 完整備份（PRD §12.3.4）
# 與 PRD 的差異：以 postgres 身分執行；把成敗寫進 /var/lib/pgbackrest/.last_backup_status
#   （pgbackrest-metrics.sh 轉成 pgbackrest_backup_last_status，PRD §12.6.2 的告警指標）。
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  exec gosu postgres "$0" "$@"
fi

status_file="/var/lib/pgbackrest/.last_backup_status"
record_status() {
  local rc="$1" tmp="${status_file}.tmp" st=1
  if [ "$rc" -eq 0 ]; then st=0; fi
  printf 'type=full\nstatus=%s\ntimestamp=%s\n' "$st" "$(date +%s)" > "$tmp" && mv -f "$tmp" "$status_file" || true
}
trap 'record_status "$?"' EXIT

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP] Starting FULL backup..."

# 🔴 pgBackRest 的 backup 一次只寫「一個」repo（沒指定 --repo 就只寫 repo1；實測：
#   「repo option not specified, defaulting to repo1」）。要讓離站 repo2 也有基底備份，必須逐 repo 各跑一次；
#   archive-push 則是自動推到所有 repo，不受此限。BACKUP_REPOS 可改（預設 "1 2"）。
read -ra repos <<< "${BACKUP_REPOS:-1 2}"
failed=0
for repo in "${repos[@]}"; do
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] repo${repo}: full backup..."
  if ! pgbackrest --stanza=aisdlc --repo="$repo" --type=full backup; then
    echo "ERROR: repo${repo} full backup failed" >&2
    failed=1
  fi
done

# 驗證最新備份
pgbackrest --stanza=aisdlc info

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$failed" != "0" ]; then
  echo "[$TIMESTAMP] FULL backup FAILED on at least one repo." >&2
  exit 1
fi
echo "[$TIMESTAMP] FULL backup completed successfully."

# 可選：通知（curl webhook / email）
# curl -X POST "${WEBHOOK_URL}" -d "{\"text\": \"FULL backup completed at $TIMESTAMP\"}"
