# docker/pgbackrest/Dockerfile — pgBackRest 備份 sidecar（PRD §11.4.3；ADR-001 D14-2）
#
# 與 PRD 的差異：
#   · 基底 pgvector/pgvector:pg18 是 Debian bookworm，沒有 apk ⇒ apt-get（PGDG apt 已在映像內設定）
#   · Debian 的 busybox 套件沒有 crond ⇒ 從官方 busybox 映像複製靜態 busybox（含 crond／httpd／pgrep／wget），
#     crontab 維持 PRD 的 Alpine crond 格式
#   · 加 mc（MinIO client，pg_dump 離站用）、jq（指標／驗證腳本）、curl
#   · ENTRYPOINT 改為 bootstrap 腳本：等 PG → stanza-create → 指標端點 → crond（PRD 直接 exec crond）
#   · 備份控制面（PRD §9.3；README〈4.6〉）：job-run.sh／backup-ctl-export.sh／backup-ctl-runner.sh 隨 scripts/
#     一起 COPY（tests/ 不進映像）；輸出卷掛載點 /backup-out 與維護鎖目錄 /run/backup-ctl 在下方 RUN 建好
ARG BUSYBOX_IMAGE=busybox:1.38.0-musl
ARG MC_IMAGE=pgsty/mc:RELEASE.2026-09-16T00-00-00Z

FROM ${BUSYBOX_IMAGE} AS busybox
FROM ${MC_IMAGE} AS mc

FROM pgvector/pgvector:pg18

# 🔴 這一段與 docker/postgres/primary/Dockerfile 的第一個 RUN 逐字相同（共用快取、版本一致）
RUN apt-get update \
 && apt-get install -y --no-install-recommends pgbackrest \
 && rm -rf /var/lib/apt/lists/*

# openssl／gosu／tzdata 基底映像已有；MinIO 憑證 job 用 openssl，cron 時區用 tzdata
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl jq ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY --from=busybox /bin/busybox /usr/local/bin/busybox
COPY --from=mc /usr/bin/mc /usr/local/bin/mc

COPY pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
COPY scripts/ /usr/local/bin/
COPY crontab /etc/crontabs/postgres

# pgBackRest 拒絕以 root 執行（[031]），而 `docker compose exec` 預設是 root ⇒ 讓 PATH 上的 pgbackrest
# 是一支會降權成 postgres 的包裝；真正的執行檔仍是 /usr/bin/pgbackrest。
RUN chmod 0755 /usr/local/bin/*.sh \
 && ln -sf /usr/local/bin/pgbackrest-as-postgres.sh /usr/local/bin/pgbackrest \
 && chmod 0600 /etc/crontabs/postgres \
 && install -d -o postgres -g postgres -m 0750 \
      /var/lib/pgbackrest /var/log/pgbackrest /var/lib/postgresql/wal_archive \
 # 指標目錄要讓 busybox httpd（降權成 nobody）讀得到 ⇒ 0755
 && install -d -m 0755 /run/pgbackrest-metrics \
 # 備份控制面（README〈4.6〉）：/backup-out 是輸出卷的掛載點（寫入端映像定義卷根的擁有者：postgres），
 # backend 是另一個 uid、只讀它 ⇒ 0755（🔴 不可照抄上面 0750）；/run/backup-ctl 放維護鎖（sidecar 本地、不在共享卷）
 && install -d -o postgres -g postgres -m 0755 /backup-out /run/backup-ctl

ENTRYPOINT ["/usr/local/bin/pgbackrest-entrypoint.sh"]
CMD ["daemon"]
