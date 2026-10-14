# docker/postgres/primary/Dockerfile — PostgreSQL 18 Primary ＋ pgBackRest
# PRD §12.2.2 的 archive_command 只有 cp；PITR 需要 pgbackrest archive-push（以及 restore 時的
# archive-get），所以 primary 也要有 pgbackrest 執行檔（ADR-001 D14-3）。
# 基底 pgvector/pgvector:pg18 是 Debian bookworm（apk 不存在，ADR-001 D14-2），PGDG apt 已在映像內設定好。
FROM pgvector/pgvector:pg18

# 🔴 這一段與 docker/pgbackrest/Dockerfile 的第一個 RUN 逐字相同：兩個映像共用同一層快取，
#    也保證 primary 與 sidecar 的 pgbackrest 版本一致（版本不一致時 repo 內的 info 檔格式可能不相容）。
RUN apt-get update \
 && apt-get install -y --no-install-recommends pgbackrest \
 && rm -rf /var/lib/apt/lists/*

# 初始化腳本打進映像（而不是 bind mount）：docker-entrypoint 只對「有執行位元」的 .sh 以子行程執行，
# 沒有就改成 source 進它自己的 shell；git 在 Windows／macOS 檢出的檔案不保證有執行位元，
# 而 source 會讓腳本裡的 `set -u` 外洩進 entrypoint。
COPY init/ /docker-entrypoint-initdb.d/
COPY pgbackrest-archive-wal.sh /usr/local/bin/pgbackrest-archive-wal.sh
RUN chmod 0755 /usr/local/bin/pgbackrest-archive-wal.sh /docker-entrypoint-initdb.d/*.sh \
 # 卷第一次掛載時 Docker 會把映像內該路徑的屬主複製過去 ⇒ 這幾個目錄必須先存在且屬 postgres，
 # 否則新建的 named volume 是 root:root，archive_command 寫不進去。
 && install -d -o postgres -g postgres -m 0750 \
      /var/lib/pgbackrest /var/log/pgbackrest /var/lib/postgresql/wal_archive
