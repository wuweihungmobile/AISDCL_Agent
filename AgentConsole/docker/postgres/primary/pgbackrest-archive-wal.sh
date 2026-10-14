#!/usr/bin/env bash
# docker/postgres/primary/pgbackrest-archive-wal.sh — PostgreSQL archive_command 包裝（PRD §12.2.2 偏離，ADR-001 D14-3）
#
# 🔴 檔名必須含 pgbackrest：`pgbackrest check`／`backup` 會驗 archive_command 字串含 pgbackrest（實測：
#   archive_command '/usr/local/bin/archive-wal.sh %p %f' must contain pgbackrest，錯誤碼 [068]）。
#
# 用法（postgresql.conf）：archive_command = '/usr/local/bin/pgbackrest-archive-wal.sh %p %f'
#   %p＝WAL 檔相對於 PGDATA 的路徑（cwd 即 PGDATA）；%f＝檔名。
#
# 做兩件事，任一失敗就回非零（PostgreSQL 會重試，WAL 不會被回收）：
#   (1) 複本寫到本地歸檔 /var/lib/postgresql/wal_archive（replica 的 restore_command 讀這裡；PRD 原有的 cp，
#       這裡改成 gzip -1：archive_timeout 強制換出來的 WAL 段仍是 16MB，但內容幾乎全是 0，壓縮後約 70～80KB。
#       實測：有持續寫入時每 60 秒換一段，不壓縮的複本最壞約 22GiB／天（推算）累積在 pg_wal_archive 卷）
#   (2) pgbackrest archive-push 到 repo1（本地）與 repo2（離站 S3/MinIO）（PITR 用）
#
# 🔴 守門：repo1 的 archive.info 不存在 ⇒ 尚未 stanza-create ⇒ 沒有任何基底備份，此時歸檔的 WAL
#   無法用於還原。直接回 0（並在 stderr 出聲）。這同時避免「開發模式只起 primary、沒有 sidecar」時
#   archive_command 永遠失敗、archive_timeout 每分鐘強制換 WAL 段而讓 pg_wal 無限累積。
#   stanza 一旦建立，守門即失效：之後任何歸檔失敗都會回非零（不靜默丟 WAL）。
set -euo pipefail

wal_path="${1:?usage: pgbackrest-archive-wal.sh <%p> <%f>}"
wal_name="${2:?usage: pgbackrest-archive-wal.sh <%p> <%f>}"

stanza="aisdlc"
local_archive="/var/lib/postgresql/wal_archive"
repo_info="/var/lib/pgbackrest/archive/${stanza}/archive.info"

if [ ! -s "$repo_info" ]; then
  echo "pgbackrest-archive-wal: stanza '${stanza}' 尚未建立（找不到 ${repo_info}），略過歸檔 ${wal_name}" >&2
  exit 0
fi

# (1) 本地歸檔：壓縮後先寫暫存檔再改名，replica 不會讀到半截檔；重送同一個 WAL 是冪等的（覆寫同內容）。
#     檔名多一個 .gz（歷史檔 *.history、*.backup 也是）；replica 的 restore_command 對應地 gunzip。
tmp="${local_archive}/.${wal_name}.tmp"
gzip -1 -c "$wal_path" > "$tmp"
mv -f "$tmp" "${local_archive}/${wal_name}.gz"

# (2) pgBackRest（repo1＋repo2；設定來自 /etc/pgbackrest/pgbackrest.conf 與 PGBACKREST_* 環境變數）
exec pgbackrest --stanza="$stanza" archive-push "$wal_path"
