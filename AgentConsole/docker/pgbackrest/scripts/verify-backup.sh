#!/usr/bin/env bash
# docker/pgbackrest/scripts/verify-backup.sh — 備份驗證 + 真實 restore 演練（PRD §12.3.4／§12.7.2）
# 不僅 metadata 校驗，更執行「還原到臨時實例 + row count 校驗」之真實演練；
# 預設對 repo1（本地）與 repo2（離站 S3/MinIO）各演練一次（PRD §12.7.2：離站備份須通過演練）。
#
# 與 PRD 的差異（README〈與 PRD 的差異〉）：
#   · 還原型態用 --type=immediate --target-action=promote（還原到備份的一致點後升格）：PRD 的 --type=none
#     不會寫 restore_command，而 pgBackRest 預設備份不含 WAL（archive-copy=n）⇒ 臨時實例會因找不到一致點的 WAL 起不來
#   · 臨時實例關閉 TCP、socket 放 /tmp（不碰 primary 的共用 socket 目錄）、port 5599、archive_mode=off、hot_standby=off
#   · row count 的表清單自動取 console schema 內所有資料表（PRD 寫死 projects/goals/tasks/execution_runs，
#     且沒有 schema 前綴；Console 的表在 console schema，後端 Flyway 尚未執行時它們不存在）。
#     要強制檢查某些表就設 DRILL_REQUIRED_TABLES="console.projects console.goals …"（缺表即失敗）。
#   · 另檢查最新一份邏輯備份（logical/*.dump）可被 pg_restore 讀取
# 環境變數：DRILL_REPOS（預設 "1 2"）、DRILL_PORT（預設 5599）、DRILL_REQUIRED_TABLES（預設空）
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  exec gosu postgres "$0" "$@"
fi

STANZA="aisdlc"
DB="${POSTGRES_DB:-aisdlc}"
DB_USER="${POSTGRES_USER:-aisdlc}"
DRILL_PORT="${DRILL_PORT:-5599}"
DRILL_PGDATA="/tmp/restore-drill-pgdata"
DRILL_SOCK="/tmp/restore-drill-sock"
LIVE_SOCK="${PGHOST:-/var/run/postgresql}"
BUCKET="${OFFSITE_S3_BUCKET:-aisdlc-db-backup}"
ENDPOINT="${OFFSITE_S3_ENDPOINT:-minio:9000}"
LOGICAL_DUMP="/tmp/restore-drill-logical.dump"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

cleanup() {
  if [ -f "${DRILL_PGDATA}/postmaster.pid" ]; then
    pg_ctl -D "$DRILL_PGDATA" -m immediate stop > /dev/null 2>&1 || true
  fi
  rm -rf "$DRILL_PGDATA" "$DRILL_SOCK" "$LOGICAL_DUMP" "${MC_CONFIG_DIR:-/nonexistent}"
}
trap cleanup EXIT

drill_psql() {
  psql -h "$DRILL_SOCK" -p "$DRILL_PORT" -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1 -tA "$@"
}
live_psql() {
  psql -h "$LIVE_SOCK" -p 5432 -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1 -tA "$@"
}

log "Starting backup verification + restore drill..."

# --- (1) pgBackRest 基本完整性校驗 ---
pgbackrest --stanza="$STANZA" verify
echo "=== Current Backup Inventory ==="
pgbackrest --stanza="$STANZA" info

# --- (2)(3) 真實 restore 演練：逐 repo 還原到臨時資料目錄、啟動臨時實例、row count 校驗 ---
read -ra repos <<< "${DRILL_REPOS:-1 2}"
for repo in "${repos[@]}"; do
    rm -rf "$DRILL_PGDATA" "$DRILL_SOCK"
    mkdir -p "$DRILL_PGDATA" "$DRILL_SOCK"
    chmod 0700 "$DRILL_PGDATA" "$DRILL_SOCK"

    log "[drill] repo${repo}: Restoring latest backup to temporary instance..."
    pgbackrest --stanza="$STANZA" --repo="$repo" --pg1-path="$DRILL_PGDATA" \
        --no-delta --type=immediate --target-action=promote restore

    log "[drill] repo${repo}: Starting temporary instance (port ${DRILL_PORT}, no TCP)..."
    pg_ctl -D "$DRILL_PGDATA" -w -t 300 \
        -o "-p ${DRILL_PORT} -c listen_addresses= -c unix_socket_directories=${DRILL_SOCK} -c archive_mode=off -c hot_standby=off" \
        start

    # 🔴 pg_ctl -w 在「recovery 中且 hot_standby=off」時就回報啟動完成（postmaster.pid 狀態為 standby），
    #   但此時還不接受連線，要等 recovery 結束並升格才行；WAL 段多時這個空窗會讓下面的 psql 直接失敗
    #   （實測：切回拓撲後歸檔 WAL 較多，演練因 "not accepting connections" 失敗）。所以輪詢到真的能連線為止。
    accepting=0
    for _ in $(seq 1 150); do
        if pg_isready -q -h "$DRILL_SOCK" -p "$DRILL_PORT" -U "$DB_USER"; then
            accepting=1
            break
        fi
        sleep 2
    done
    if [ "$accepting" != "1" ]; then
        echo "FAILED: 臨時實例在 300 秒內沒有完成 recovery 並接受連線（repo${repo}）" >&2
        exit 1
    fi

    echo "=== Restore Drill (repo${repo}): Row Count Verification ==="
    in_recovery="$(drill_psql -c 'SELECT pg_is_in_recovery();')"
    echo "  server: $(drill_psql -c 'SHOW server_version;')  pg_is_in_recovery=${in_recovery}"
    if [ "$in_recovery" != "f" ]; then
        echo "FAILED: 臨時實例仍在 recovery（還原未完成升格）" >&2
        exit 1
    fi

    read -ra required_tables <<< "${DRILL_REQUIRED_TABLES:-}"
    for required in "${required_tables[@]}"; do
        found="$(drill_psql -c "SELECT to_regclass('${required}') IS NOT NULL;")"
        if [ "$found" != "t" ]; then
            echo "FAILED: 必要資料表 ${required} 在還原後不存在" >&2
            exit 1
        fi
    done

    mapfile -t tables < <(drill_psql -c "SELECT quote_ident(schemaname) || '.' || quote_ident(tablename) FROM pg_tables WHERE schemaname = 'console' ORDER BY 1;")
    if [ "${#tables[@]}" -eq 0 ]; then
        echo "  WARN: console schema 內尚無資料表（後端 Flyway 尚未執行？）：僅驗證可還原且可查詢。"
        drill_psql -c "SELECT 'schemas: ' || string_agg(nspname, ',' ORDER BY nspname) FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname <> 'information_schema';"
    fi
    for tbl in "${tables[@]}"; do
        restored="$(drill_psql -c "SELECT count(*) FROM ${tbl};")"
        live="$(live_psql -c "SELECT count(*) FROM ${tbl};" 2>/dev/null || echo '?')"
        echo "  ${tbl}: ${restored} rows (restored)  ${live} rows (live primary; 備份時點之後的新增列不計入還原結果)"
        if [ -z "$restored" ]; then
            echo "FAILED: Restore drill cannot query ${tbl}" >&2
            exit 1
        fi
    done

    # --- (4) 清理臨時實例 ---
    pg_ctl -D "$DRILL_PGDATA" -m immediate stop > /dev/null
    rm -rf "$DRILL_PGDATA" "$DRILL_SOCK"
    log "[drill] repo${repo}: OK（臨時實例已停止並清除）"
done

# --- (5) 邏輯備份（離站 logical/*.dump）可讀性檢查 ---
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    uri_encode() { jq -rn --arg s "$1" '$s|@uri'; }
    MC_HOST_offsite="https://$(uri_encode "$AWS_ACCESS_KEY_ID"):$(uri_encode "$AWS_SECRET_ACCESS_KEY")@${ENDPOINT}"
    export MC_HOST_offsite
    export MC_CONFIG_DIR="/tmp/.mc-verify-$$"
    mc_cmd=(mc)
    if [ "${OFFSITE_S3_VERIFY_TLS:-n}" = "n" ]; then
        mc_cmd+=(--insecure)
    fi
    listing="$("${mc_cmd[@]}" ls --json "offsite/${BUCKET}/logical/" 2>/dev/null || true)"
    latest="$(printf '%s\n' "$listing" | jq -r 'select(.key != null) | .key' | sort | tail -n 1)"
    if [ -n "$latest" ]; then
        "${mc_cmd[@]}" cat "offsite/${BUCKET}/logical/${latest}" > "$LOGICAL_DUMP"
        pg_restore --list "$LOGICAL_DUMP" > "${LOGICAL_DUMP}.toc"
        entries="$(grep -c '^[0-9]' "${LOGICAL_DUMP}.toc" || true)"
        rm -f "${LOGICAL_DUMP}.toc"
        echo "=== Logical dump check: ${latest} 可由 pg_restore 讀取（TOC ${entries} 筆）==="
    else
        echo "  WARN: 離站 logical/ 內沒有邏輯備份（pg_dump-offsite.sh 尚未執行過？）"
    fi
else
    echo "  WARN: 未設定 AWS_ACCESS_KEY_ID／AWS_SECRET_ACCESS_KEY，略過邏輯備份檢查"
fi

echo "=== Backup Storage Usage ==="
du -sh /var/lib/pgbackrest/backup/aisdlc/

log "OK: Backup verification + restore drill completed (data confirmed restorable)."
