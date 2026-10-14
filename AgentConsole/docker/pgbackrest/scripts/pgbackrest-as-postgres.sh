#!/usr/bin/env bash
# docker/pgbackrest/scripts/pgbackrest-as-postgres.sh — pgBackRest 的降權包裝（映像內安裝為 /usr/local/bin/pgbackrest）
#
# pgBackRest 拒絕以 root 執行（錯誤 [031]：running as root can create files that the regular user cannot
# access），而 `docker compose exec pgbackrest pgbackrest …` 預設以 root 進容器。
# 這支包裝讓這些指令不必記得加 `-u postgres`：root ⇒ 降權成 postgres 再執行；已是 postgres ⇒ 直接執行。
# 環境變數（PGBACKREST_*）原樣保留。
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  exec gosu postgres /usr/bin/pgbackrest "$@"
fi
exec /usr/bin/pgbackrest "$@"
