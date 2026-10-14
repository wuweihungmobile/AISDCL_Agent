#!/usr/bin/env bash
# docker/pgbackrest/scripts/restore.sh — 還原 Primary（PRD §12.3.4；ADR-001 D15／NFR-XPL-03）
# 用法（容器內）：restore.sh [--target-time "YYYY-MM-DD HH:MM:SS"] [--repo N] [--yes]
#
# 🔴 與 PRD 的差異：PRD 的 restore.sh 是「主機側」腳本（內部呼叫 docker compose stop／start），
#   Windows 主機沒有 bash。改成只做「容器內」該做的中間兩步（清資料目錄＋還原），
#   前後的 stop／start／驗證由 docker/README.md 的 `docker compose …` 指令負責（bash／PowerShell 雙形態）：
#
#     docker compose stop postgres-primary                                   # 1. 停 primary
#     docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes   # 2-3. 清資料＋還原（本腳本）
#     docker compose start postgres-primary                                  # 4. 啟動（PG 依 restore_command 重播 WAL）
#     docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT NOW(), version();"   # 5. 驗證
#
#   🔴 `--no-deps` 不可省：pgbackrest 服務 depends_on postgres-primary，沒有它 compose 會把剛停掉的 primary 又拉起來。
#   還原後 replica 的時間軸與新 primary 分岔，必須重建 replica（README〈重建 Replica〉）。
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  exec gosu postgres "$0" "$@"
fi

TARGET_TIME=""
REPO=""
ASSUME_YES=0
PGDATA_DIR="/var/lib/postgresql/data/pgdata"
STANZA="aisdlc"

while [[ $# -gt 0 ]]; do
    case $1 in
        --target-time)
            TARGET_TIME="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --yes)
            ASSUME_YES=1
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

echo "=================================================="
echo "      PostgreSQL 還原程序 (pgBackRest)"
echo "=================================================="

# 安全檢查：primary 還在跑就拒絕（清掉執行中的資料目錄會直接毀掉資料庫）
if pg_isready -q -h /var/run/postgresql -p 5432 -U "${POSTGRES_USER:-aisdlc}"; then
    echo "ERROR: primary 仍在接受連線。請先在主機執行：docker compose stop postgres-primary" >&2
    exit 1
fi

if [ "$ASSUME_YES" != "1" ]; then
    echo "即將清空 ${PGDATA_DIR} 並從備份還原（不可逆）。輸入 yes 繼續："
    read -r confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi
fi

# Step 1: 清理資料目錄
echo "[Step 1/2] Cleaning data directory..."
find "$PGDATA_DIR" -mindepth 1 -delete

# Step 2: 執行還原
repo_args=()
if [ -n "$REPO" ]; then
    repo_args+=("--repo=${REPO}")
fi
if [ -n "$TARGET_TIME" ]; then
    echo "[Step 2/2] Restoring to point-in-time: $TARGET_TIME"
    pgbackrest --stanza="$STANZA" "${repo_args[@]}" \
        --no-delta \
        --type=time \
        --target="$TARGET_TIME" \
        --target-action=promote \
        restore
else
    echo "[Step 2/2] Restoring latest backup (replay all archived WAL)..."
    pgbackrest --stanza="$STANZA" "${repo_args[@]}" --no-delta restore
fi

echo ""
echo "OK: 資料目錄已還原。下一步（主機）：docker compose start postgres-primary，再驗證（見 docker/README.md）。"
