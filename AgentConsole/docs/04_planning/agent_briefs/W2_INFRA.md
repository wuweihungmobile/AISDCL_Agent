# 任務書 W2-B：基礎設施開發者（Docker Compose ＋ PostgreSQL 18 備援／備份／監控，PRD §11～§12）

> 先讀 `COMMON_CONTEXT.md`，再讀 `AgentConsole/docs/02_architecture/Architecture.md` §2／§9 與 `ADR-001`，再讀本檔。

## 你的角色
你負責 `AgentConsole/docker-compose.yml`、`docker-compose.dev.yml`、`.env.example`、`AgentConsole/docker/` 整棵樹，並**真的把資料庫層跑起來驗證**：串流複製在串、pgBackRest 全備／差備／離站（MinIO）／驗證演練都真的成功。前端／後端／Bridge 的映像由其他 agent 產，你只在 compose 內接線（本波它們可能還沒 Dockerfile——你用 `docker compose config` 驗語法、用 profile 讓資料庫層可單獨啟動）。

## 必讀（PRD 行號）
§11 全部（2109～2862）、§12 全部（2864～3576）、§0.5 NFR-REL-03（104～113）。

## 已拍板的偏離（寫進 docker/README.md 的〈與 PRD 的差異〉節）
1. `engine-bridge` 的 build context＝monorepo 根（`context: ..`，`dockerfile: AgentConsole/engine-bridge/Dockerfile`），因為映像要 COPY `AutoClaude/`；不再用 PRD 的 `../AutoClaude:/engines/autoclaude:ro` 掛載。`AISDLC_SDD` LATEST 仍以唯讀掛載 `../AISDLC_SDD:/engines/aisdlc_sdd:ro`（Bridge 用 `SDD_ROOT=/engines/aisdlc_sdd/AISDLC_SDD_v0.30`）。
2. pgBackRest 映像：PRD 寫 `FROM pgvector/pgvector:pg18` + `apk add`，但該映像是 **Debian** 基底，`apk` 不存在 → 改 `apt-get`（PGDG apt repo 的 `pgbackrest`，需支援 PG18）。
3. **Primary 也要裝 pgbackrest**（自建 `docker/postgres/primary/Dockerfile`：`FROM pgvector/pgvector:pg18` + pgbackrest），`archive_command` 改成同時做 PRD 的 `cp`（給 replica 的 restore_command 用）**和** `pgbackrest --stanza=aisdlc archive-push %p`（給 PITR 用）；sidecar 與 primary 共用 `pgbackrest_repo` volume、`/var/run/postgresql` socket volume、`pg_data` volume（sidecar 以 `pg1-path`＋`pg1-socket-path` 本機模式連線，不走 SSH/TLS）。
4. 離站 repo2 預設指向 compose 內的 **MinIO** 服務（PRD 允許「S3/MinIO」），`repo2-s3-endpoint=minio:9000`、`repo2-s3-uri-style=path`、`repo2-storage-verify-tls=n`、bucket 由 `minio/mc` 一次性 job 建立；真 S3 只要改 `.env`。
5. Prometheus 的 `postgres-exporter-primary/replica` 目標 PRD 有引用但 compose 沒列 → 補兩個 `prometheuscommunity/postgres-exporter` 服務。
6. Replica 自動初始化：自建 `docker/postgres/replica/entrypoint.sh`，PGDATA 空時自動 `pg_basebackup -R -S replica_slot_1` 後再啟動（PRD 的手動 `setup-replica.sh` 保留給「重建 replica」情境）。
7. `nginx` 的 `depends_on frontend/backend healthy` 保留，但把 `nginx` 放進 profile `full`；資料庫層（postgres-primary／replica／pgbackrest／minio／redis／exporters／prometheus／grafana／pgadmin）放 profile `db`（預設啟用）；`frontend`／`backend`／`engine-bridge` 放 profile `app`。這樣本波就能 `docker compose --profile db up -d` 驗資料庫層。
8. 映像一律**釘版本**（不要 `latest`）：nginx:1.27-alpine、redis:7-alpine、dpage/pgadmin4:9、prom/prometheus:v3.x、grafana/grafana:12.x、minio/minio:RELEASE.2025-xx、prometheuscommunity/postgres-exporter:v0.17.x——用你能 pull 到的最新 stable，把實際 tag 寫進交卷。

## 要建的檔案（PRD §11.8 樹，逐檔）
```
AgentConsole/docker-compose.yml           PRD §11.3 全部服務 + 上述偏離；deploy.resources.limits 照 PRD；healthcheck 全有；db-net internal: true
AgentConsole/docker-compose.dev.yml       只起 postgres-primary（port 5432）+ redis，給本機開發三服務用；可與主檔疊加
AgentConsole/.env.example                 PRD §11.6 全部鍵 + REPLICATION_PASSWORD、PGBACKREST_CIPHER_PASS、MINIO_ROOT_USER/PASSWORD、PGBACKREST_S3_*、AWS_ACCESS_KEY_ID/SECRET（全佔位符 <YOUR_...>）
AgentConsole/docker/README.md             啟動／停止／驗證／failover／restore 指令（PRD §11.7、§12.5.2、§12.8 檢查清單）+ 〈與 PRD 的差異〉
AgentConsole/docker/nginx/{nginx.conf,conf.d/default.conf}      PRD §11.5
AgentConsole/docker/postgres/primary/{Dockerfile,postgresql.conf,pg_hba.conf,init/01-init-db.sql,init/02-replication.sh}   PRD §12.2.2/12.2.3/12.2.5（01-init-db.sql：CREATE EXTENSION vector, pg_stat_statements；CREATE SCHEMA console；不要建表——表由後端 Flyway 建）
AgentConsole/docker/postgres/replica/{postgresql.conf,entrypoint.sh}   PRD §12.2.4 + 偏離 6
AgentConsole/docker/pgbackrest/{Dockerfile,pgbackrest.conf,crontab,scripts/{backup-full.sh,backup-incr.sh,pg_dump-offsite.sh,restore.sh,verify-backup.sh,setup-replica.sh}}   PRD §12.3；pg_dump-offsite 用 `mc`（MinIO client）或 aws cli 二擇一，寫清楚
AgentConsole/docker/redis/redis.conf
AgentConsole/docker/prometheus/prometheus.yml   PRD §12.6.1 + exporters
AgentConsole/docker/grafana/provisioning/{datasources/prometheus.yml,dashboards/dashboard.yml}、dashboards/{postgres-overview.json,app-overview.json}（最小可載入的合法 dashboard JSON，面板照 PRD §12.6.3 至少各 3 個）
AgentConsole/docker/pgadmin/servers.json
```
所有 `.sh`：`#!/usr/bin/env bash`、`set -euo pipefail`、LF、**shellcheck 0 警告**（根層 CI 掃全 repo `*.sh`；`shellcheck` 沒裝就 `brew install shellcheck`）。

## 驗證（真的跑；逐字貼關鍵輸出）
```
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole
cp .env.example .env.ci && 把佔位符換成測試值（.env.ci 用完刪掉，不要留）
docker compose --env-file .env.ci config > /dev/null && echo CONFIG_OK
docker compose --env-file .env.ci --profile db up -d --build
docker compose --env-file .env.ci ps                       # 全部 healthy（貼表）
docker compose --env-file .env.ci exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr,state,sync_state FROM pg_stat_replication;"   # 1 列 streaming
docker compose --env-file .env.ci exec postgres-primary psql -U aisdlc -d aisdlc -c "CREATE TABLE console.repl_probe(id int); INSERT INTO console.repl_probe VALUES (1);"
sleep 3; docker compose --env-file .env.ci exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT * FROM console.repl_probe;"   # 看到 1
docker compose --env-file .env.ci exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_is_in_recovery();"   # t
docker compose --env-file .env.ci exec pgbackrest pgbackrest --stanza=aisdlc stanza-create
docker compose --env-file .env.ci exec pgbackrest pgbackrest --stanza=aisdlc check            # 期望無錯（archive-push 真的通）
docker compose --env-file .env.ci exec pgbackrest /usr/local/bin/backup-full.sh              # 成功
docker compose --env-file .env.ci exec pgbackrest /usr/local/bin/backup-incr.sh              # 成功
docker compose --env-file .env.ci exec pgbackrest pgbackrest --stanza=aisdlc info            # repo1 與 repo2 都有備份
docker compose --env-file .env.ci exec pgbackrest /usr/local/bin/pg_dump-offsite.sh          # MinIO 內出現 logical/ 物件
docker compose --env-file .env.ci exec pgbackrest /usr/local/bin/verify-backup.sh            # 演練：臨時實例起來、row count 印出、清理
curl -s localhost:9090/api/v1/targets | python3 -c 'import json,sys; [print(t["labels"]["job"],t["health"]) for t in json.load(sys.stdin)["data"]["activeTargets"]]'   # postgres-primary/replica up（backend 本波沒起是預期的 down）
curl -s -u admin:<pw> localhost:3001/api/search | python3 -c 'import json,sys; print([d["title"] for d in json.load(sys.stdin)])'   # 兩個 dashboard
for f in $(git ls-files --others --exclude-standard docker | grep '\.sh$'); do shellcheck "$f" && bash -n "$f"; done; echo SHELLCHECK_OK
docker compose --env-file .env.ci --profile db down -v && rm -f .env.ci    # 🔴 收尾：容器與 volume 全收，交卷列「開了→收了」
```
- 手動 failover（PRD §12.5.2）本波只需把腳本寫好並 `bash -n`，不要真的 failover（那會毀掉 replica 的驗證狀態）；在 docker/README.md 寫清楚步驟。
- 回填 RTM 的 INF／DR 列（實作檔＋狀態 `✅ 已驗證`／`🟡 僅語法驗證`）。

## 追加（主控 2026-10-14 晚；優先於上文衝突處）
1. **G-01**：`nginx` 必須同時掛 `frontend-net` 與 `backend-net`（否則 `proxy_pass http://backend` 解析不到）；`pgadmin` 掛 `db-net`＋一個非 internal 網路才能從主機連 5050。
2. **G-02**：正式 `docker-compose.yml` 的 `db-net` 維持 `internal: true` 且 **不發布** 5432／5433 到主機（PG 只給 backend／bridge／exporters 用）；`docker-compose.dev.yml` 覆蓋：把 postgres-primary／replica／pgadmin 加掛非 internal 的 `dev-net` 並發布 5432／5433／5050。驗證兩種都要做：正式模式從主機 `psql` 連不到（預期）、dev 覆蓋模式連得到。
3. PRD 沒給 healthcheck 的服務（minio、exporters、grafana、prometheus、pgbackrest）全部補上。
4. `NEXT_PUBLIC_API_URL` 在全棧模式留空（前端用相對路徑 `/api` 經 nginx）；`.env.example` 註解寫清楚。
5. restore／failover 這類「主機側腳本」一律改成在容器內執行（`docker compose exec pgbackrest bash /usr/local/bin/restore.sh`），docker/README.md 的主機側指令只用 `docker compose …`，並給 PowerShell 對等版（同指令，`Push-Location AgentConsole; docker compose …; Pop-Location`）。
6. 讀 `AgentConsole/docs/02_architecture/Architecture.md` §2（容器表含本輪追加的 4 個服務：minio、minio-init、postgres-exporter×2）與 `docs/04_planning/Implementation_Plan.md` §2 W2-B 追加表，逐項對照；回填 Plan 進度帳 W2-B 列與 RTM 的 INF-／DR 列。
7. Bridge 的 compose 服務段：`build: {context: .., dockerfile: AgentConsole/engine-bridge/Dockerfile}`，環境變數名以 `AgentConsole/engine-bridge/README.md` 的表為準（Bridge 開發者交卷後才定案；若你先完成，照 W1_BRIDGE.md 的 settings 清單寫並標 TODO）。

## 追加二（Bridge 交卷後；優先於上文衝突處）
- Bridge 服務段環境變數與掛載照 COMMON_CONTEXT〈補充二〉的「compose 對 Bridge 的要求」逐項寫；healthcheck 用 `curl -f http://localhost:8081/health`（映像若無 curl 改 `python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8081/health').status==200 else 1)"`，先看 `AgentConsole/engine-bridge/Dockerfile` 怎麼寫）。
- 本波驗證範圍仍是 **profile `db`**（資料庫層＋監控）。`app` profile 的三個服務只要 `docker compose config` 過；Bridge 映像可以順手 `docker compose build engine-bridge` 試一次（主控已拉 `python:3.11-slim`，拉不到就寫明）。
- Docker 拉映像若逾時（Bridge 開發者遇過 `DeadlineExceeded`），先 `docker pull <image>` 單獨重試一次，仍不行就在交卷〈沒做〉寫明哪個映像，繼續做不需該映像的部分。
