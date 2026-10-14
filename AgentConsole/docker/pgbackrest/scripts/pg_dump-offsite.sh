#!/usr/bin/env bash
# docker/pgbackrest/scripts/pg_dump-offsite.sh — 每日邏輯備份（pg_dump）推送離站（PRD §12.3.4／§12.7.2）
# 與 pgBackRest 物理備份互補（防物理備份邏輯損壞的單點），與 repo2 同 bucket、路徑 logical/ 區隔。
#
# 與 PRD 的差異（README〈與 PRD 的差異〉）：
#   · 上傳用 mc（MinIO client，已打進映像）而非 aws cli：mc 對 MinIO 與 AWS S3 都能用，且是單一靜態執行檔
#   · pg_dump 預設走共用 unix socket（PGHOST 預設 /var/run/postgresql，pg_hba 的 local trust）⇒ sidecar 不必持有資料庫密碼；
#     要改連遠端節點就設 PGHOST／PGPASSWORD
#   · 上傳後 stat 驗證物件確實存在；依 LOGICAL_BACKUP_RETENTION_DAYS（預設 28 天，與 repo 保留期對齊）清舊檔
#   · 邏輯備份檔本身不做客戶端加密（pgBackRest repo 才有 aes-256-cbc）：依賴 bucket 端加密（AWS S3 預設即 SSE-S3）
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  exec gosu postgres "$0" "$@"
fi

TS=$(date -u +"%Y%m%d-%H%M%S")
DUMP_FILE="/tmp/aisdlc-${TS}.dump"
BUCKET="${OFFSITE_S3_BUCKET:-aisdlc-db-backup}"
ENDPOINT="${OFFSITE_S3_ENDPOINT:-minio:9000}"
KEEP_DAYS="${LOGICAL_BACKUP_RETENTION_DAYS:-28}"

: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"

export MC_CONFIG_DIR="/tmp/.mc-dump-$$"
trap 'rm -f "$DUMP_FILE"; rm -rf "$MC_CONFIG_DIR"' EXIT

# mc 的連線資訊走環境變數 MC_HOST_<alias>（不落檔、不進指令列）；金鑰要做 URL 編碼
uri_encode() { jq -rn --arg s "$1" '$s|@uri'; }
MC_HOST_offsite="https://$(uri_encode "$AWS_ACCESS_KEY_ID"):$(uri_encode "$AWS_SECRET_ACCESS_KEY")@${ENDPOINT}"
export MC_HOST_offsite
mc_cmd=(mc)
if [ "${OFFSITE_S3_VERIFY_TLS:-n}" = "n" ]; then
  mc_cmd+=(--insecure)   # 自簽憑證的本機 MinIO
fi

# 邏輯備份（custom 格式，含壓縮）
pg_dump -h "${PGHOST:-/var/run/postgresql}" -p 5432 -U "${POSTGRES_USER:-aisdlc}" \
    -d "${POSTGRES_DB:-aisdlc}" -Fc -Z6 -f "$DUMP_FILE"

# 推送至離站物件儲存（與 pgBackRest repo2 同 bucket，路徑區隔）
"${mc_cmd[@]}" cp --quiet "$DUMP_FILE" "offsite/${BUCKET}/logical/aisdlc-${TS}.dump"
"${mc_cmd[@]}" stat "offsite/${BUCKET}/logical/aisdlc-${TS}.dump" > /dev/null

# 清理逾期的邏輯備份
if ! "${mc_cmd[@]}" rm --recursive --force --older-than "${KEEP_DAYS}d" "offsite/${BUCKET}/logical/"; then
    echo "WARN: 清理逾期邏輯備份失敗（不影響本次備份）" >&2
fi

echo "pg_dump offsite backup pushed: aisdlc-${TS}.dump"
