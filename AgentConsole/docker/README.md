# docker — 容器化部署資產

PRD §11（Docker 部署）與 §12（PostgreSQL 18 備援副本與災難復原）的實作：`docker-compose.yml`（全部服務）、`docker-compose.dev.yml`（本機開發）、`.env.example`，以及本目錄的各服務設定。
負責人：W2 Infra 開發者。**bash 區塊的指令都已在 macOS（Docker Desktop）實跑過；PowerShell 區塊以 macOS 上的 pwsh 7 驗過語法與引號行為（`Push-Location … Pop-Location`、`bash -c '…'`、`--target-time "…"`、`Invoke-RestMethod`），Windows 實機尚未跑——`Test-NetConnection`、`curl.exe`、反斜線路徑等 Windows 專屬寫法只能在 Windows 驗，清單見〈11. Windows 接續注意〉。**

> **指令寫法**：工作目錄一律假設在 **monorepo 根**。bash 區塊用 `(cd AgentConsole && …)` 子殼；PowerShell 區塊用 `Push-Location AgentConsole; …; Pop-Location` 同一行成對（不用裸 `cd`）。
> `docker compose` 預設讀 `AgentConsole/.env`；驗證時可改用 `--env-file .env.ci`（測試值檔，用完即刪）。
> **所有 `.sh` 只在容器內（Linux）執行**；主機側只用 `docker compose …`／`docker …`。文件一律以 `bash <腳本路徑>` 的形態執行腳本（不依賴 git 的執行位元）。

## 1. 目錄與服務總覽

```
AgentConsole/
├── docker-compose.yml            全部服務；profile：db／app／full
├── docker-compose.dev.yml        本機開發：只起 PG＋Redis；或疊加在主檔上把 PG／Redis 發布到主機
├── .env.example                  環境變數模板（只放 <YOUR_...> 佔位符）
└── docker/
    ├── nginx/                    nginx.conf、conf.d/default.conf
    ├── postgres/primary/         Dockerfile、postgresql.conf、pg_hba.conf、pgbackrest-archive-wal.sh、init/{01-init-db.sql,02-replication.sh}
    ├── postgres/replica/         postgresql.conf、entrypoint.sh
    ├── pgbackrest/               Dockerfile、pgbackrest.conf、crontab、scripts/{backup-full,backup-incr,pg_dump-offsite,restore,verify-backup,setup-replica,pgbackrest-entrypoint,pgbackrest-metrics,pgbackrest-as-postgres}.sh
    ├── minio/                    gen-cert.sh、init-bucket.sh
    ├── redis/redis.conf
    ├── prometheus/               prometheus.yml、alerts.yml
    ├── grafana/                  provisioning/{datasources,dashboards}、dashboards/{postgres-overview,app-overview}.json
    └── pgadmin/servers.json
```

### 1.1 服務（`docker compose config` 的最終結果；profile `db` 12 個、`app` 3 個、`full` 1 個）

| # | 服務 | 映像（已釘版） | profile | 網路 | 主機埠 | 資源上限 | healthcheck |
|---|------|----------------|---------|------|--------|----------|-------------|
| 1 | nginx | `nginx:1.27-alpine` | full | frontend-net、**backend-net** | 80、443 | 0.5／256M | `wget /nginx-health`（nginx 自己回 200） |
| 2 | frontend | 自建 `aisdlc-frontend:dev` | app | frontend-net、backend-net | — | 1.0／512M | `wget`／`curl` `:3000/api/health` |
| 3 | backend | 自建 `aisdlc-backend:dev` | app | backend-net、db-net | — | 2.0／1G | `wget`／`curl` `:8080/actuator/health` |
| 4 | engine-bridge | 自建 `aisdlc-engine-bridge:dev` | app | backend-net、db-net | — | 1.0／1G | python 探測 `:8081/health` |
| 5 | postgres-primary | 自建 `aisdlc-postgres-primary:pg18`（`pgvector/pgvector:pg18` ＋ pgBackRest） | db | db-net | 正式模式不發布 | 2.0／2G | `pg_isready -h 127.0.0.1` |
| 6 | postgres-replica | `pgvector/pgvector:pg18` | db | db-net | 正式模式不發布 | 1.0／1G | `pg_isready -h 127.0.0.1` |
| 7 | redis | `redis:7-alpine` | db | db-net | — | 0.5／256M | `redis-cli ping` |
| 8 | pgadmin | `dpage/pgadmin4:9.18.0` | db | db-net、**backend-net** | 5050 | 0.5／256M | `wget /misc/ping` |
| 9 | pgbackrest | 自建 `aisdlc-pgbackrest:pg18`（pgBackRest 2.59.3） | db | db-net | — | 0.5／512M | crond 活著＋stanza 存在＋指標端點 |
| 10 | prometheus | `prom/prometheus:v3.15.0` | db | db-net、backend-net | 9090 | 0.5／512M | `wget /-/healthy` |
| 11 | grafana | `grafana/grafana:12.4.13` | db | backend-net | 3001 | 0.5／256M | `wget /api/health` |
| 12 | minio | `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` | db | db-net | —（S3 API `:9000`、console `:9001` 只在容器內） | 0.5／512M | `curl -k /minio/health/live` |
| 13 | minio-init | `pgsty/mc:RELEASE.2026-09-16T00-00-00Z`（一次性） | db | db-net | — | 0.25／128M | —（結束碼 0 即成功） |
| 14 | postgres-exporter-primary | `prometheuscommunity/postgres-exporter:v0.20.1` | db | db-net | — | 0.25／128M | `wget :9187/` |
| 15 | postgres-exporter-replica | 同上 | db | db-net | — | 0.25／128M | 同上 |
| 16 | minio-certs | `aisdlc-pgbackrest:pg18`（一次性；產生 MinIO 自簽憑證） | db | db-net | — | 0.25／128M | —（結束碼 0 即成功） |

> 第 12～16 列是相對 PRD §11.2 新增的服務（PRD 11 個 ⇒ 16 個）。`app` 的服務 `depends_on` postgres-primary、redis ⇒ **`--profile app` 不能單獨使用，要與 `--profile db` 一起**。

### 1.2 網路與卷

| 網路 | internal | 成員 |
|------|----------|------|
| frontend-net | 否 | nginx、frontend |
| backend-net | 否 | nginx、frontend、backend、engine-bridge、pgadmin、prometheus、grafana |
| db-net | **是**（不可出站；**對主機也不通**） | backend、engine-bridge、primary、replica、redis、pgbackrest、pgadmin、prometheus、exporters、minio（＋兩個一次性 job） |

| 卷 | 用途 |
|----|------|
| pg_data／pg_replica_data | primary／replica 資料（`PGDATA=/var/lib/postgresql/data/pgdata`） |
| pg_wal_archive | `archive_command` 的本地 WAL 複本（gzip 壓縮的 `<WAL>.gz`；replica 的 `restore_command` 唯讀讀它；每日 03:30 清 7 天前） |
| pg_backup | pgBackRest repo1（本地備份；primary 與 sidecar 共用）；另放 `.last_backup_status` |
| pg_socket | primary 的 unix socket，與 sidecar 共用（pgBackRest 本機模式，不走 SSH／TLS） |
| minio_data／minio_certs | 離站備份物件／MinIO 自簽憑證 |
| redis_data、app_logs、nginx_certs、engine_workspace | PRD §11.3 原有 |

## 2. 啟動與停止

**首次**：複製環境檔並把所有 `<YOUR_...>` 換成實際值（`.env` 已被 `.gitignore` 排除；不要提交）。

```bash
cp AgentConsole/.env.example AgentConsole/.env
```

```powershell
Copy-Item AgentConsole\.env.example AgentConsole\.env
```

| 目的 | bash | PowerShell |
|------|------|------------|
| 資料庫層（PG 主副本、備份、MinIO、監控、pgAdmin、Redis） | `(cd AgentConsole && docker compose --profile db up -d --build)` | `Push-Location AgentConsole; docker compose --profile db up -d --build; Pop-Location` |
| 全棧（經 nginx 單一入口） | `(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build)` | `Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location` |
| 本機開發：只起 PG（5432）＋Redis（6379） | `(cd AgentConsole && docker compose -f docker-compose.dev.yml up -d)` | `Push-Location AgentConsole; docker compose -f docker-compose.dev.yml up -d; Pop-Location` |
| 資料庫層＋把 PG／Redis 發布到主機（疊加） | `(cd AgentConsole && docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile db up -d --build)` | `Push-Location AgentConsole; docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile db up -d --build; Pop-Location` |
| 狀態（含一次性 job 的結束碼） | `(cd AgentConsole && docker compose --profile db ps -a)` | `Push-Location AgentConsole; docker compose --profile db ps -a; Pop-Location` |
| 日誌 | `(cd AgentConsole && docker compose --profile db logs -f --tail=100 postgres-primary)` | `Push-Location AgentConsole; docker compose --profile db logs -f --tail=100 postgres-primary; Pop-Location` |
| 停止（保留資料卷） | `(cd AgentConsole && docker compose --profile db --profile app --profile full down)` | `Push-Location AgentConsole; docker compose --profile db --profile app --profile full down; Pop-Location` |
| 停止獨立 dev（保留資料卷） | `(cd AgentConsole && docker compose -f docker-compose.dev.yml down)` | `Push-Location AgentConsole; docker compose -f docker-compose.dev.yml down; Pop-Location` |
| 停止疊加模式（保留資料卷） | `(cd AgentConsole && docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile db down)` | `Push-Location AgentConsole; docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile db down; Pop-Location` |
| 🔴 清場（**刪除全部資料卷**） | `(cd AgentConsole && docker compose --profile db --profile app --profile full down -v)` | `Push-Location AgentConsole; docker compose --profile db --profile app --profile full down -v; Pop-Location` |

- 每個服務都屬於某個 profile，所以**裸的 `docker compose up -d` 什麼都不會起**；想讓它起資料庫層，在 `.env` 取消 `COMPOSE_PROFILES=db` 的註解（代價：獨立使用 `docker-compose.dev.yml` 時會連 replica 一起帶起）。
- `docker-compose.dev.yml` 用 `extends` 重用主檔定義，**會載入整份主檔 ⇒ 主檔所有 `${VAR:?…}` 必填變數都要有值**：務必先 `cp .env.example .env`。
- 獨立／疊加的 dev 模式要用**同樣的 `-f`** 停止，否則 `dev-net` 會留下（遺留時 `docker network rm aisdlc_dev-net`）。
- 正式模式（只用主檔）**不對主機發布任何 PG 埠**，原因與實測見〈9〉#10。要從主機連 PG 用上表第 3、4 列，或 `docker compose exec`。
- 啟動順序由 `depends_on` 條件保證：minio-certs → minio（healthy）→ minio-init（結束碼 0）→ pgbackrest；primary（healthy）→ replica／pgbackrest／exporter。
- 首次啟動時 sidecar 會自動 `stanza-create`（冪等）；此後 primary 的 `archive_command` 才開始真的歸檔。**但第一份全備不會自動做**——請立刻做（〈4.2〉），否則要等到週日 02:00 才有基底備份，期間無法 PITR。

## 3. 驗證（資料庫層）

以下全部為實跑過的流程。為簡潔，PowerShell 版只在與 bash 不同時另列。

**3.1 設定與啟動**

```bash
(cd AgentConsole && docker compose --env-file .env.ci --profile db config > /dev/null && echo CONFIG_OK)
(cd AgentConsole && docker compose --env-file .env.ci --profile db up -d --build)
(cd AgentConsole && docker compose --env-file .env.ci ps)
```

```powershell
Push-Location AgentConsole; docker compose --env-file .env.ci --profile db config *> $null; "config_rc=$LASTEXITCODE"; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci --profile db up -d --build; Pop-Location
Push-Location AgentConsole; docker compose --env-file .env.ci ps; Pop-Location
```

預期：`ps` 全部 `healthy`（minio-certs／minio-init 為一次性 job，`ps -a` 顯示 `Exited (0)`）。

**3.2 串流複製（寫主讀副）**

```bash
(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr,state,sync_state FROM pg_stat_replication;")
(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "CREATE TABLE console.repl_probe(id int); INSERT INTO console.repl_probe VALUES (1);")
(cd AgentConsole && docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT * FROM console.repl_probe;")
(cd AgentConsole && docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_is_in_recovery();")
```

```powershell
Push-Location AgentConsole; docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr,state,sync_state FROM pg_stat_replication;"; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "CREATE TABLE console.repl_probe(id int); INSERT INTO console.repl_probe VALUES (1);"; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT * FROM console.repl_probe;"; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_is_in_recovery();"; Pop-Location
```

預期：`pg_stat_replication` 1 列 `streaming`／`async`；replica 讀得到那 1 列；`pg_is_in_recovery` 為 `t`。（`console` schema 由 `01-init-db.sql` 建立；Console 的表由後端 Flyway 建，這裡只用探針表。）

**3.3 pgBackRest（全備、差備、離站、演練）** — 指令都在 sidecar 內執行，主機側只有 `docker compose exec`：

```bash
(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc stanza-create)   # 冪等：回報 already exists
(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc check)           # 兩個 repo 都要出現 successfully archived
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh)
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/backup-incr.sh)
(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc info)            # full／diff 各有 repo1 與 repo2
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/pg_dump-offsite.sh)
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/verify-backup.sh)
```

```powershell
Push-Location AgentConsole; docker compose exec pgbackrest pgbackrest --stanza=aisdlc stanza-create; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest pgbackrest --stanza=aisdlc check; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/backup-incr.sh; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest pgbackrest --stanza=aisdlc info; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/pg_dump-offsite.sh; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/verify-backup.sh; Pop-Location
```

- `docker compose exec` 預設以 root 進容器；`pgbackrest`（PATH 上是降權包裝）與各腳本會自動降權成 `postgres`（pgBackRest 拒絕以 root 執行，錯誤 `[031]`）。
- `verify-backup.sh` 預設對 **repo1 與 repo2 各做一次真實還原演練**：還原到臨時資料目錄 → 起臨時實例（port 5599、不開 TCP）→ 列出 `console` schema 全部資料表的 row count（與現行 primary 並列）→ 停止並清除；最後檢查最新一份離站邏輯備份可被 `pg_restore` 讀取。要強制檢查某些表：`docker compose exec -e DRILL_REQUIRED_TABLES="console.projects console.goals" pgbackrest bash /usr/local/bin/verify-backup.sh`。
- 離站物件確認：`docker compose exec pgbackrest bash -c 'export MC_HOST_off="https://$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY@$OFFSITE_S3_ENDPOINT"; mc --insecure ls --recursive off/$OFFSITE_S3_BUCKET/logical/'`（PowerShell 把整段 `bash -c '…'` 包在單引號內即可，內容不變）。

**3.4 監控**

```bash
curl -s localhost:9090/api/v1/targets | python3 -c 'import json,sys; [print(t["labels"]["job"],t["health"]) for t in json.load(sys.stdin)["data"]["activeTargets"]]'
curl -s -u admin:<YOUR_GRAFANA_PASSWORD> localhost:3001/api/search | python3 -c 'import json,sys; print([d["title"] for d in json.load(sys.stdin)])'
```

```powershell
(Invoke-RestMethod http://localhost:9090/api/v1/targets).data.activeTargets | ForEach-Object { "$($_.labels.job) $($_.health)" }
curl.exe -s -u admin:<YOUR_GRAFANA_PASSWORD> http://localhost:3001/api/search
```

預期：`postgres-primary`、`postgres-replica`、`pgbackrest`、`prometheus` 皆 `up`；`spring-boot` 在 backend（profile app）沒起時為 `down` 屬預期。Grafana 兩個 dashboard：`PostgreSQL Overview`、`Application Overview`。

**3.5 埠可達性（G-02／E-5）** — 正式模式：5432／5433 連不到；5050／9090／3001 連得到。疊加 `docker-compose.dev.yml` 後 5432／5433 連得到。

```bash
curl -s -o /dev/null -w "%{http_code}\n" localhost:5050/misc/ping
python3 -c 'import socket; socket.create_connection(("127.0.0.1", 5432), 3)'    # 正式模式：ConnectionRefusedError；dev 疊加：無輸出
```

```powershell
Test-NetConnection 127.0.0.1 -Port 5432 -InformationLevel Quiet
```

**3.6 靜態檢查（.sh）** — 根層 CI 的判準是 shellcheck 嚴重度 `warning` 以上；本目錄的 `.sh` 在**全部嚴重度**下都是 0 筆。可攜做法（PATH 上有 shellcheck 就用它，否則走 docker）：

```bash
python tools/run_shellcheck.py
```

```powershell
python tools\run_shellcheck.py
```

## 4. 備份、離站與還原

### 4.1 排程（`crontab`，容器時區 `BACKUP_TZ`，預設 `Asia/Taipei`）

| 排程 | 工作 | 保留 |
|------|------|------|
| 每週日 02:00 | `backup-full.sh` — repo1＋repo2 各一份全備 | 4 份（28 天） |
| 週一至週六 02:00 | `backup-incr.sh` — repo1＋repo2 各一份**差異**備份（檔名沿用 PRD，類型為 diff） | 7 份 |
| 每日 02:30 | `pg_dump-offsite.sh` — `pg_dump -Fc` 上傳到 bucket 的 `logical/` | `LOGICAL_BACKUP_RETENTION_DAYS`（28 天） |
| 每日 03:00 | `pgbackrest expire`（repo1＋repo2） | — |
| 每日 03:30 | 清 `pg_wal_archive` 內 7 天前的本地 WAL 複本 | 7 天 |
| 每週三 04:00 | `verify-backup.sh` — 完整性校驗＋真實還原演練 | — |
| 持續 | WAL 歸檔：有 WAL 活動時每 60 秒換一段（`archive_timeout`；實測逐分鐘各一段），推到 repo1＋repo2＋本地複本；完全閒置時不再換段（實測：最後一次寫入後多換 1 段，其後的 checkpoint 週期都沒有新段） | WAL 隨備份保留 |

cron 輸出在 sidecar 的 `/var/log/pgbackrest/cron.log`：`docker compose exec pgbackrest tail -n 50 /var/log/pgbackrest/cron.log`。

- 排程已實測會觸發：探針工作以 `postgres` 身分執行、看得到 `PGBACKREST_*` 環境變數、時區為 CST（busybox crond 會把容器環境傳給工作；Debian 的 `cron` 不會）。
- 🔴 busybox crond **只在 crontab 目錄的 mtime 改變時重讀排程**：在執行中的容器內原地修改 `/etc/crontabs/postgres` 不會生效，要先寫成新檔再 `mv` 蓋過去（重建映像／容器則一律生效）。

### 4.2 首次部署後立刻做全備

```bash
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh)
```

```powershell
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh; Pop-Location
```

🔴 **pgBackRest 的 `backup` 一次只寫一個 repo**（沒指定 `--repo` 就只寫 repo1）。PRD 的備份腳本只呼叫一次，離站 repo2 永遠不會有基底備份；本實作的兩支備份腳本逐 repo 各跑一次（`BACKUP_REPOS`，預設 `"1 2"`），任一 repo 失敗即整體回非零並記入 `pgbackrest_backup_last_status`。WAL 歸檔（`archive-push`）則是自動推到全部 repo。

### 4.3 還原（整庫還原或 PITR）

三步，**前後兩步在主機、中間一步在容器**（PRD 的 `restore.sh` 是主機側腳本，Windows 沒有 bash，改成這樣）：

```bash
(cd AgentConsole && docker compose stop postgres-primary)
(cd AgentConsole && docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes --target-time "2026-10-14 16:39:17+00")
(cd AgentConsole && docker compose start postgres-primary)
(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT NOW(), version();")
```

```powershell
Push-Location AgentConsole; docker compose stop postgres-primary; Pop-Location
Push-Location AgentConsole; docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes --target-time "2026-10-14 16:39:17+00"; Pop-Location
Push-Location AgentConsole; docker compose start postgres-primary; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT NOW(), version();"; Pop-Location
```

- 還原到最新：拿掉 `--target-time …`。只想還原離站那份：加 `--repo 2`。
- 🔴 `--no-deps` 不可省：pgbackrest 服務 `depends_on` postgres-primary，沒有它 compose 會把剛停掉的 primary 又拉起來。
- 目標時間要帶時區（上例 `+00`＝UTC）：PG 以它自己的時區（容器內為 UTC）解讀沒帶時區的字串，而 sidecar 的 `TZ` 是 `BACKUP_TZ`。
- `restore.sh` 在 primary 仍接受連線時會**拒絕執行**（不會清掉執行中的資料目錄）。
- 還原後 PG 會依 `restore_command` 從 pgBackRest 重播 WAL 到目標點再升格（新時間軸）。🔴 **replica 的時間軸會與新 primary 分岔，必須重建（〈5〉）**；primary 的 `postgresql.auto.conf` 會留下 pgBackRest 寫入的 `restore_command`／`recovery_target_*`（無害，只在復原時用）。
- 還原完成後做一次 `pgbackrest check`＋新的全備。

### 4.4 邏輯備份還原（`pg_dump` 離站檔）

```bash
(cd AgentConsole && docker compose exec pgbackrest bash -c 'export MC_HOST_off="https://$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY@$OFFSITE_S3_ENDPOINT"; mc --insecure cp off/$OFFSITE_S3_BUCKET/logical/<dump 檔名> /tmp/restore.dump && pg_restore --list /tmp/restore.dump | head')
```

```powershell
Push-Location AgentConsole; docker compose exec pgbackrest bash -c 'export MC_HOST_off="https://$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY@$OFFSITE_S3_ENDPOINT"; mc --insecure cp off/$OFFSITE_S3_BUCKET/logical/<dump 檔名> /tmp/restore.dump && pg_restore --list /tmp/restore.dump | head'; Pop-Location
```

要真的灌回資料庫：把 `pg_restore --list …` 換成 `pg_restore --clean --if-exists -h /var/run/postgresql -U aisdlc -d aisdlc /tmp/restore.dump`（socket 走本機 trust，不需密碼）。**邏輯備份檔本身沒有客戶端加密**（pgBackRest repo 才有 aes-256-cbc）：依賴 bucket 端加密（AWS S3 對新物件預設 SSE-S3）；本機 MinIO 沒有。

### 4.5 離站儲存改用真 S3

只改 `.env`：`PGBACKREST_S3_ENDPOINT=s3.amazonaws.com`、`PGBACKREST_S3_REGION=<region>`、`PGBACKREST_S3_URI_STYLE=host`、`PGBACKREST_S3_VERIFY_TLS=y`、`PGBACKREST_S3_BUCKET`、`AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`（IAM 使用者；需有該 bucket 的讀寫與列舉權限）。bucket 要先自己建好。minio 相關服務仍會被帶起但不再被使用（要省資源就用 override 檔把它們從 `db` profile 拿掉）。**`PGBACKREST_CIPHER_PASS` 遺失＝所有備份無法還原**，請另行保管。

## 5. 重建 Replica

需要重建的情境：replica 資料損壞、PITR 還原後時間軸分岔、`replica_slot_1` 遺失（log 出現 `replication slot "replica_slot_1" does not exist` 或 `new timeline N forked off current database system timeline`）。

```bash
(cd AgentConsole && docker compose stop postgres-replica)
(cd AgentConsole && docker compose run --rm --no-deps --entrypoint bash postgres-replica /usr/local/bin/setup-replica.sh --force)
(cd AgentConsole && docker compose up -d postgres-replica)
```

```powershell
Push-Location AgentConsole; docker compose stop postgres-replica; Pop-Location
Push-Location AgentConsole; docker compose run --rm --no-deps --entrypoint bash postgres-replica /usr/local/bin/setup-replica.sh --force; Pop-Location
Push-Location AgentConsole; docker compose up -d postgres-replica; Pop-Location
```

`setup-replica.sh` 清空資料目錄 → `pg_basebackup -R -c fast -S replica_slot_1`（primary 上沒有 slot 就一併建立）→ 移除複製來的 `restore_command`／`recovery_target_*`（primary 做過 PITR 時 `postgresql.auto.conf` 內有 `pgbackrest … archive-get`，replica 映像沒有 pgbackrest，不清掉會啟動即 FATAL；`recovery_target_time` 還會讓 standby 在目標點停止復原）。**資料目錄為空時 replica 容器啟動會自動做同樣的事**（`replica/entrypoint.sh`），所以最簡單的重建法也可以是 `down` 後刪掉 `aisdlc_pg_replica_data` 卷再 `up`。

## 6. 手動 Failover（PRD §12.5.2）

PRD 的 failover 是主機側 bash 腳本，這裡改成 `docker compose` 指令。**RTO 取決於人**：偵測、決策、操作都是手動。以下每一步（含善後與切回）都已在 macOS 實跑過，連同真實的 backend、engine-bridge、frontend、nginx 一起走完：failover 之後經 nginx 寫入的專案，切回拓撲後在 primary、replica 與還原演練中都還在。

**6.1 提升 replica**

```bash
(cd AgentConsole && docker compose exec postgres-primary pg_isready -h 127.0.0.1 -U aisdlc)      # 1. 確認 primary 真的不可用（還能連就要先決定是否真的 failover）
(cd AgentConsole && docker compose stop pgbackrest postgres-primary)                             # 2. 停 primary（避免腦裂），順便停 sidecar（它綁的是 primary 的資料卷）
(cd AgentConsole && docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_promote(wait => true);")   # 3. 提升；回 t
(cd AgentConsole && docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_is_in_recovery();")        # 4. 驗證：f
```

```powershell
Push-Location AgentConsole; docker compose exec postgres-primary pg_isready -h 127.0.0.1 -U aisdlc; Pop-Location
Push-Location AgentConsole; docker compose stop pgbackrest postgres-primary; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_promote(wait => true);"; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-replica psql -U aisdlc -d aisdlc -c "SELECT pg_is_in_recovery();"; Pop-Location
```

**6.2 讓應用改連升格後的節點**：在 `.env` 設 `POSTGRES_HOST=postgres-replica`（backend 的 `SPRING_DATASOURCE_URL` 與 Bridge 的 `BRIDGE_DB_DSN` 都取這個變數），再以 `--no-deps` 重建這兩個容器：

```bash
(cd AgentConsole && docker compose --profile db --profile app up -d --no-deps backend engine-bridge)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app up -d --no-deps backend engine-bridge; Pop-Location
```

🔴 `--no-deps` 不可省：這兩個服務 `depends_on` postgres-primary，沒有它 compose 會把剛停掉的 primary 又拉起來（腦裂）。**不只 `up`**：`docker compose start backend`（`engine-bridge` 同理）也會——實測輸出出現 `Container aisdlc-pg-primary Starting`，舊 primary 以自己的舊資料起成第二個可寫的節點；之後照 6.3 切回，升格節點上 failover 之後寫入的資料會被它的舊資料蓋掉（實測：`after-failover` 專案在最終拓撲中消失）。在 6.3 完成之前**不要執行裸的 `docker compose up`、也不要 `docker compose start` backend／engine-bridge**（`restart` 未實測，同樣避開）；6.3-a 動手前先確認 `docker compose ps -a` 裡 `postgres-primary` 是 `Exited`。此階段 postgres-primary 的 exporter、Grafana 的 primary 面板與 `PostgresDown` 告警會亮——屬預期。

**6.3 善後：回到 primary／replica 拓撲**（compose 的角色是固定的，所以要把兩個節點的角色換回來）：

```bash
# a. 原 primary 節點修好後，把它的資料重建成「升格節點」的 standby
(cd AgentConsole && docker compose run --rm --no-deps --entrypoint bash -e PRIMARY_HOST=postgres-replica postgres-primary /usr/local/bin/setup-replica.sh --force)
(cd AgentConsole && docker compose up -d --no-deps postgres-primary)
# b. 計畫性切回：停應用 → 停現任 primary（postgres-replica）→ 提升 postgres-primary
(cd AgentConsole && docker compose stop backend engine-bridge postgres-replica)
(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT pg_promote(wait => true);")
# c. .env 的 POSTGRES_HOST 改回 postgres-primary；把 postgres-replica 重建成新 primary 的 replica；應用與 sidecar 回來
(cd AgentConsole && docker compose run --rm --no-deps --entrypoint bash postgres-replica /usr/local/bin/setup-replica.sh --force)
(cd AgentConsole && docker compose --profile db --profile app up -d)
# d. 🔴 立刻做新的全備（升格節點上的 WAL 沒有被歸檔，備份鏈在那一段是斷的）
(cd AgentConsole && docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh)
```

```powershell
Push-Location AgentConsole; docker compose run --rm --no-deps --entrypoint bash -e PRIMARY_HOST=postgres-replica postgres-primary /usr/local/bin/setup-replica.sh --force; Pop-Location
Push-Location AgentConsole; docker compose up -d --no-deps postgres-primary; Pop-Location
Push-Location AgentConsole; docker compose stop backend engine-bridge postgres-replica; Pop-Location
Push-Location AgentConsole; docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT pg_promote(wait => true);"; Pop-Location
Push-Location AgentConsole; docker compose run --rm --no-deps --entrypoint bash postgres-replica /usr/local/bin/setup-replica.sh --force; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app up -d; Pop-Location
Push-Location AgentConsole; docker compose exec pgbackrest bash /usr/local/bin/backup-full.sh; Pop-Location
```

> 為什麼 replica 的 `postgresql.conf` 要與 primary 的 WAL／複製參數對稱：PostgreSQL 要求 standby 的 `max_wal_senders`／`max_connections` 等**不得低於**它的 primary。實測：兩邊不一致時，原 primary 節點重建成 standby 啟動即 FATAL（`max_wal_senders = 5 is a lower setting than on the primary server, where its value was 10`）。
> 若 failover 是因為資料損壞而非單純當機，6.3-a 的 standby 重建會把損壞的資料目錄整個覆蓋，這正是期望的結果。

## 7. 監控

| 元件 | 位址 | 說明 |
|------|------|------|
| Prometheus | `http://localhost:9090` | 目標：`spring-boot`（backend）、`postgres-primary`、`postgres-replica`（postgres_exporter）、`pgbackrest`（備份指標）、`prometheus` |
| Grafana | `http://localhost:3001` | 帳密＝`.env` 的 `GRAFANA_USER`／`GRAFANA_PASSWORD`（**沒有預設密碼**）；資料來源 `Prometheus`（uid `prometheus`）與兩個 dashboard 皆由 provisioning 載入 |
| 告警規則 | Prometheus UI 的 Alerts 頁 | `docker/prometheus/alerts.yml`：PRD §12.6.2 的 9 項閾值＋WAL 歸檔失敗、stanza 異常、指標過期（共 12 條）；沒有 Alertmanager，不會對外通知 |

- **PostgreSQL Overview**（38 個面板，六列對應 PRD §12.6.3）：PG 總覽、複製狀態、查詢效能、備份狀態、鎖與等待、儲存空間。**Application Overview**（17 個面板）：抓取目標狀態＋ Spring Boot（Micrometer）面板；backend 沒起時這些面板顯示 No data。
- **pgBackRest 指標**（ADR-001 G-04：PRD §12.6.2 的 `pgbackrest_*` 沒有現成 exporter）：sidecar 的 `pgbackrest-metrics.sh` 每 60 秒用 `pgbackrest info --output=json` 產生 Prometheus 文字格式，busybox httpd 在 `:9854/metrics` 提供。含 `pgbackrest_backup_since_last_full_seconds`、`pgbackrest_backup_last_status`（PRD 兩個指名指標）、備份份數／大小／耗時、stanza 與 repo 狀態碼，以及 `aisdlc_storage_*`（備份 repo／WAL 歸檔目錄用量、資料卷磁碟使用率）。失敗的備份不會出現在 `pgbackrest info`，所以 `last_status` 由備份腳本寫狀態檔（`pg_backup` 卷內 `.last_backup_status`）後轉出。
- PRD 指標名與 postgres_exporter 實際名稱的對照：`pg_stat_bgwriter_buffers_alloc` → `pg_stat_bgwriter_buffers_alloc_total`；`pg_stat_statements_mean_time` → `rate(pg_stat_statements_seconds_total) / rate(pg_stat_statements_calls_total)`。
- 🔴 **WAL 歸檔失敗是最危險的靜默失效**：`archive_command` 失敗時 PG 不會回收 WAL，`pg_wal` 會一直長到磁碟滿。離站儲存（MinIO／S3）一掛，`archive-push` 就失敗（兩個 repo 都要成功）。看 `PostgresWalArchiveFailing` 告警、Grafana 的「WAL 歸檔失敗（15m）」面板，或 `SELECT failed_count, last_failed_time FROM pg_stat_archiver;`。
- Prometheus／Grafana 沒有掛資料卷（PRD 未列）：Prometheus 的時序資料在映像宣告的匿名卷內，`down -v` 會一併清掉。

## 8. 日常維運檢查清單（PRD §12.8）

| 週期 | 項目 | 指令（bash；PowerShell 版＝`Push-Location AgentConsole; <同一段 docker compose …>; Pop-Location`） | 預期 |
|------|------|------|------|
| 每日 | Primary 健康 | `(cd AgentConsole && docker compose exec postgres-primary pg_isready -U aisdlc)` | accepting connections |
| 每日 | Replica 健康 | `(cd AgentConsole && docker compose exec postgres-replica pg_isready -U aisdlc)` | accepting connections |
| 每日 | Replication 延遲 | `(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn FROM pg_stat_replication;")` | replay_lsn 接近 sent_lsn |
| 每日 | 最近備份狀態 | `(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc info)` | 最近備份為今日（repo1 與 repo2） |
| 每日 | 磁碟使用率 | `docker system df` | < 80% |
| 每週 | 備份驗證 | `(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc verify)` | 無錯誤（週三 04:00 的排程另外做真實還原演練） |
| 每週 | 慢查詢分析 | `(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;")` | 無超長查詢 |
| 每週 | 表膨脹 | `(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT relname, n_dead_tup, n_live_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC;")` | dead tuple 比例 < 20% |
| 每週 | WAL 歸檔空間 | `(cd AgentConsole && docker compose exec postgres-primary du -sh /var/lib/postgresql/wal_archive/)` | < 指定閾值（本地複本每日自動清 7 天前） |

## 9. 與 PRD 的差異

「依據」欄標 **實測** 的，都是本輪在 macOS（Docker Desktop，arm64）上以指令證實過的事實；其餘為設計取捨。

| # | PRD／原設計 | 本實作 | 理由與依據 |
|---|-------------|--------|-----------|
| 1 | §11.3 Bridge 以 `./engine-bridge`、`../AutoClaude`、`../AISDLC_SDD/…v0.14` 掛載、`command: uvicorn` | build context＝monorepo 根（`context: ..`、`dockerfile: AgentConsole/engine-bridge/Dockerfile`）；整個 `AISDLC_SDD/` 唯讀掛 `/sdd`、`SDD_ROOT=/sdd`；環境變數以 Bridge README 為準（`BRIDGE_DB_DSN`、`BRIDGE_DB_SCHEMA=console` 等） | 映像要 COPY `AutoClaude/`（ADR-001 D7）。實測：容器健康、`/health` 回 `sdd.latest=AISDLC_SDD_v0.30`、DB `ok:true`、`/workspace` 可寫、`/sdd` 唯讀 |
| 2 | §11.4.3 `FROM pgvector/pgvector:pg18` ＋ `apk add pgbackrest openssh-client dcron` | `apt-get install pgbackrest`（2.59.3，PG18 已支援）；不裝 openssh（本機模式不走 SSH） | 實測：基底是 Debian 12（bookworm），沒有 `apk`（E-4） |
| 3 | 同上：`ENTRYPOINT crond -f -d 8`，crontab 放 `/etc/crontabs/root` | 從官方 `busybox:1.38.0-musl` 複製靜態 busybox，用它的 `crond`（crontab 維持 PRD 的 Alpine 格式，放 `/etc/crontabs/postgres`，以 postgres 身分執行）；ENTRYPOINT 改為 bootstrap 腳本（等 PG → `stanza-create` → 指標端點 → crond） | 實測：Debian 12 的 `busybox` 套件（1.35.0）沒有 `crond` applet（`busybox-static` 有，這裡仍取官方映像的 1.38.0 靜態執行檔以釘死版本）；Debian `cron` 不傳遞容器環境變數給排程工作，要另寫 env 墊片 |
| 4 | §12.2.2 `archive_command = 'cp %p …/wal_archive/%f'`；primary 用原映像 | primary 自建映像含 pgBackRest；`archive_command` 呼叫 `pgbackrest-archive-wal.sh`：先把 WAL **gzip 壓縮**寫到本地歸檔（`<WAL>.gz`，replica 的 `restore_command` 用；PRD 的 `cp`）再 `pgbackrest archive-push`（PITR 用）；sidecar 與 primary 共用 `pg_data`／`pg_backup`／`pg_socket` 卷（本機模式） | ADR-001 D14-3。實測：`pgbackrest check` 要求 archive_command 字串含 `pgbackrest`（錯誤 `[068]`），所以腳本檔名含 pgbackrest。**為何壓縮本地複本**：`archive_timeout` 強制換出來的 WAL 段仍是 16MB（內容幾乎全是 0）；實測有持續寫入時每 60 秒換一段，不壓縮的 `cp` 複本最壞每天 1,440 段、約 22GiB（推算：1440×16MB），7 天保留約 158GiB 堆在 `pg_wal_archive` 卷；壓縮後每段約 70～80KB（本輪實測 73～78KB），解壓後與 pgBackRest repo 內的同一個 WAL 位元組相同（`cmp` 實測）；replica 以該複本做 archive recovery 也實測可行。**守門**：repo1 的 `archive.info` 不存在（尚未 `stanza-create`）時直接回 0——沒有基底備份的 WAL 無法用於 PITR，也避免「開發模式只起 primary」時 archive 永遠失敗、`archive_timeout` 每分鐘換 WAL 段而讓 `pg_wal` 無限累積；stanza 一旦建立，守門失效、任何歸檔失敗都回非零 |
| 5 | §12.3.2 離站 repo2＝`${PGBACKREST_S3_ENDPOINT:-s3.amazonaws.com}` | 預設指向 compose 內 MinIO（`minio:9000`、path-style、`repo2-storage-verify-tls=n`）；MinIO 另有 `minio-certs`（自簽憑證）與 `minio-init`（建 bucket＋只能存取該 bucket 的專用帳號，pgBackRest 與 pg_dump 都用它）；真 S3 只改 `.env`（〈4.5〉） | PRD 允許 S3／MinIO。實測：pgBackRest 的 S3 連線一律 HTTPS（沒有明文模式），所以 MinIO 必須有憑證。🔴 **官方 `minio/minio`、`minio/mc` 映像已自 Docker Hub 下架**（`docker pull` 回 `pull access denied … repository does not exist`；`quay.io/minio/minio` 回 401）⇒ 改用社群維護的 MinIO fork `pgsty/minio`／`pgsty/mc`（版本已釘，Pigsty 維護、同一套 `minio server`／`mc` 介面）。這只影響本機離站儲存，正式環境用真 S3 不受影響 |
| 6 | §12.3.2 設定檔內用 `${PGBACKREST_CIPHER_PASS}` 等 | `pgbackrest.conf` 只放靜態值；金鑰、bucket、endpoint、region、uri-style、TLS 驗證、`pg1-user`／`pg1-database` 走 `PGBACKREST_*` 環境變數；**設定檔不寫行內註解** | 實測：conf 不展開 `${…}`；行內註解會被當成值的一部分（`repo1-retention-full=4 # …` 在 `backup` 時報 `[032] is not valid`）。sidecar 內給腳本用的變數改名 `OFFSITE_S3_*`：`PGBACKREST_` 前綴的未知變數會被 pgBackRest 當成選項並印 WARN，連 `--output=json` 的 stdout 都被污染 |
| 7 | §12.3.4 備份腳本呼叫一次 `pgbackrest backup` | `backup-full.sh`／`backup-incr.sh` 逐 repo 各跑一次；成敗寫入狀態檔供 `pgbackrest_backup_last_status` | 實測：沒指定 `--repo` 時 `backup` 只寫 repo1（`repo option not specified, defaulting to repo1`），離站 repo2 永遠沒有基底備份 |
| 8 | §12.3.4 `verify-backup.sh`：`--type=none` 還原、只驗 repo1、寫死四張表 | `--type=immediate --target-action=promote`；repo1 與 repo2 各演練一次；表清單取自 `console` schema 全部資料表（`DRILL_REQUIRED_TABLES` 可強制要求）；起實例後輪詢到真的接受連線；另驗最新邏輯備份可被 `pg_restore` 讀取 | `--type=none` 不寫 `restore_command` 而預設備份不含 WAL，臨時實例找不到一致點的 WAL。實測：`pg_ctl -w` 在「recovery 中且 `hot_standby=off`」時就回報啟動完成但尚不接受連線，WAL 段多時 psql 會失敗（已修）。PRD 寫死的表名沒有 schema 前綴，且在後端 Flyway 執行前不存在 |
| 9 | §12.3.4 `pg_dump-offsite.sh` 用 aws cli、走 TCP＋密碼 | 用 `mc`（打進映像的靜態執行檔）；`pg_dump` 走共用 unix socket（`local trust`，sidecar 不必持有 DB 密碼；`PGHOST` 可改）；上傳後 `stat` 驗證、依天數清舊檔 | mc 對 MinIO 與 AWS 都能用，免裝 python 相依 |
| 10 | §11.3 `ports: "5432:5432"`、`"5433:5432"`；pgadmin 只掛 `db-net`；nginx 只掛 `frontend-net`；prometheus 依賴 backend healthy | **正式模式不發布 PG 埠**；`docker-compose.dev.yml` 把 PG／Redis 另掛非 internal 的 `dev-net` 並發布；pgadmin 另掛 backend-net；nginx 同掛 backend-net；prometheus 對 backend 的依賴加 `required: false` | ADR-001 G-01／G-02／D14-9～10。**實測（E-5）**：掛在 `internal: true` 網路上的容器，`ports:` 對主機無效（`ps` 看不到對應，主機連線被拒）；加掛一個非 internal 網路後可達。nginx 只在 frontend-net 時 `nginx -t` 報 `host not found in upstream "backend:8080"`；同掛 backend-net 後反代、SSE 不緩衝、`/actuator/` 回 403 皆通。`db` profile 單獨啟動時 backend 不存在，`required: false` 才不會報錯 |
| 11 | §12.2.4 replica 設定檔含 `primary_conninfo = '…${REPLICATION_PASSWORD}'`；§12.2.6 手動 `setup-replica.sh`（停 PG → 清資料 → basebackup → `pg_ctl start`）；`restore_command … \|\| true` | PGDATA 為空時 `replica/entrypoint.sh` 自動 `pg_basebackup -R -c fast -S replica_slot_1`；`primary_conninfo` 由 `-R` 寫進 `postgresql.auto.conf`；`setup-replica.sh` 改為只準備資料目錄（可 `--force` 重建、slot 不存在時自動建立、移除繼承的復原設定）；`restore_command` 先 `test -f` 再 `gunzip -c`（不加 `\|\| true`）；WAL／複製參數與 primary 對稱 | ADR-001 D14-6／G-06。實測：PG 是容器內 PID 1，停掉它容器就結束，PRD 的流程無法在容器內走完；PITR 後 `pg_basebackup` 會把 primary 的 `restore_command`／`recovery_target_time` 一併複製（replica 啟動即 FATAL），所以要清掉；standby 的 `max_wal_senders` 不得低於 primary（〈6.3〉） |
| 12 | §12.2.2 `config_file` 啟動，但沒設 `hba_file` | 明確設 `hba_file`（primary、replica 共用同一份 `pg_hba.conf`）與 `unix_socket_directories` | 沒設 `hba_file` 時 PRD 的 `pg_hba.conf` 根本不會生效，生效的是 initdb 產生的那份 |
| 13 | §12.2.3 pg_hba | 增列 loopback（`127.0.0.1/32`、`::1/128`）；replication 增列 `192.168.0.0/16` | 容器內 `psql -h 127.0.0.1` 否則被 `reject`；Docker 位址池用完 172.16/12 後會落到 192.168.x，replica 在那種網段會被拒 |
| 14 | §12.2.2 `logging_collector = on` | `off`（日誌走 stderr） | PRD §11.7 的 `docker compose logs postgres-primary` 以此為前提；收集器開著時日誌寫進 `PGDATA/pg_log`，`docker logs` 看不到 |
| 15 | §12.2.2 無 slot 上限 | `max_slot_wal_keep_size = '4GB'` | replica 長時間失聯時，slot 會讓 primary 無限保留 WAL 直到磁碟滿 |
| 16 | §11.8 `init/` 以 bind mount 掛入 | 打進 primary 映像並設執行位元；`02-replication.sh` 用 psql 變數安全引用密碼、**沒有 `REPLICATION_PASSWORD` 就失敗**（PRD 預設 `replicator_pass`）；`pg_stat_statements` 延伸改在 `01-init-db.sql` 建立；`01-init-db.sql` 建 `console` schema、**不建表** | docker-entrypoint 對沒有執行位元的 `.sh` 改用 `source`（`set -u` 會外洩進 entrypoint）；git 在 Windows／macOS 檢出的檔案不保證有執行位元；表由後端 Flyway 擁有 |
| 17 | §11.2 映像寫 `:latest` | 全部釘版：見〈1.1〉 | 可重現；`prom/prometheus` v3.15.0、`grafana/grafana` 12.4.13、`postgres-exporter` v0.20.1、`pgadmin4` 9.18.0 為 2026-10-14 在 Docker Hub 查到的最新穩定版 |
| 18 | §11.2 服務 11 個 | 增 minio、minio-init、minio-certs、postgres-exporter×2（16 個） | exporter：§12.6.1 引用卻未列服務；其餘見 #5 |
| 19 | §11.3 `depends_on` 與 profile | 資料庫層／應用層／入口層分 profile（`db`／`app`／`full`）；`app` 不能單獨使用 | 資料庫層可單獨起、單獨驗證；`app` 服務 `depends_on` postgres-primary，只開 `app` 時 compose 報 `depends on undefined service` |
| 20 | §11.3 frontend／backend 的 healthcheck 用 `curl` | `wget` 失敗再試 `curl`（`CMD-SHELL`） | Node／Temurin alpine 映像沒有 curl 但有 busybox wget；healthcheck 不該綁死映像怎麼做（`nginx` 依賴它們 healthy） |
| 21 | §11.6 `NEXT_PUBLIC_API_URL=/api`；§11.7 手動 Flyway 指令 | 全棧同源時留空；刪除手動 Flyway 步驟 | ADR-001 G-07／G-05：`/api` 會與 `/api/v1/…` 疊成 `/api/api/v1`；Flyway 隨 Spring Boot 啟動自動執行 |
| 22 | §11.6 `PGADMIN_EMAIL=admin@aisdlc.local`；Grafana／pgAdmin 密碼預設 `admin` | `admin@aisdlc.example.com`；Grafana、pgAdmin 密碼改為必填（無預設） | pgAdmin 9 的 email 驗證拒絕 `.local` 這類保留網域（容器起不來）；弱預設密碼 |
| 23 | §12.6.1 prometheus.yml 三個 job | 增 `pgbackrest`、`prometheus` 兩個 job、`rule_files`（`alerts.yml`）；`pgbackrest` job 指定 `fallback_scrape_protocol: PrometheusText0.0.4`；exporter 加 `stat_statements`、`stat_checkpointer`、`long_running_transactions`、`postmaster` 收集器 | busybox httpd 的 `Content-Type` 是 `application/octet-stream`，Prometheus 3 預設拒收無法辨識的型別 |
| 24 | §11.5 只給 `default.conf` | 補標準 `nginx.conf`；`/nginx-health`；Connection 標頭改用 `$connection_upgrade`；443 區塊只留註解範例 | PRD 發布了 443 並掛憑證卷，卻沒有 ssl server 區塊 |
| 25 | §12.5.2 failover＝主機側 bash 腳本；§12.3.4 `restore.sh`＝主機側腳本 | 改為 `docker compose …` 指令序列（〈4.3〉〈6〉）；容器內只保留 `restore.sh` 的清資料＋還原兩步；backend／Bridge 的 DB 主機改由 `POSTGRES_HOST` 參數化 | NFR-XPL-03：Windows 主機沒有 bash。PRD 手動改 compose 內的連線字串，改參數易錯 |
| 26 | — | 增 `name: aisdlc`、`json-file` 日誌輪替（10m×3）、primary／replica `shm_size: 256mb` 與 `stop_grace_period: 60s`、sidecar `init: true`、`BACKUP_TZ`、卷 `pg_socket`／`minio_data`／`minio_certs`、`alerts.yml`、每日清 WAL 歸檔的 cron | 可重現的卷名；日誌不撐爆磁碟；PG 預設 `/dev/shm` 64MB 對平行查詢太小；cron 時區；PRD 的 WAL 7 天保留沒有任何清理機制 |
| 27 | 卷名 `pg_backup`（PRD、Architecture、RTM） | 沿用 `pg_backup` 作為 pgBackRest repo1（任務書提到的 `pgbackrest_repo` 是同一個東西） | 與 RTM `INF-VOL-04`、Architecture §2.5 一致 |

## 10. 已知限制

- **failover 之後備份鏈在升格節點那一段是斷的**：replica 映像沒有 pgBackRest，升格後它的 WAL 不會歸檔；切回拓撲後必須立刻做新的全備（〈6.3-d〉）。failover 期間 sidecar 綁的是原 primary 的資料卷，建議先停掉。
- **離站儲存一掛，primary 的 `pg_wal` 就開始累積**（兩個 repo 都要歸檔成功）。已有告警規則，但沒有 Alertmanager；磁碟滿前要人介入。
- 本機 MinIO 是單碟、自簽憑證、官方映像已下架（改用社群 fork）：只適合開發與驗證，正式環境請用真 S3（〈4.5〉）。
- 邏輯備份檔沒有客戶端加密；本機 MinIO 的 bucket 沒有加密。
- Redis 沒有密碼（只在 internal 的 db-net）；開發疊加檔把它發布到 `127.0.0.1`，不要改綁對外位址。
- 只要有任何寫入，資料庫每 60 秒就換一個 16MB 的 WAL 段，離站 repo 與本地複本會持續長大（壓縮後每段約 70～80KB、保留政策會清；完全閒置時則不會）；`PostgresWalArchiveFailing` 與 `pg_stat_archiver` 是看歸檔是否健康的地方。
- `pgvector/pgvector:pg18` 映像宣告了 `VOLUME /var/lib/postgresql`，所以 primary／replica／pgbackrest／minio-certs 各會多出一個匿名卷（裡面只有 `data／wal_archive` 兩個掛載點目錄）。容器因改映像或設定而被「重建」時，舊的匿名卷會變成懸空卷，`down -v` 清不掉它們（實測 7 個）：偶爾用 `docker volume ls -f dangling=true` 檢視，確認內容只有 `data／wal_archive` 再個別 `docker volume rm`；不要無差別 `docker volume prune`。
- Prometheus／Grafana 沒有持久卷（PRD 未列）；pgAdmin 的設定也在容器內。
- pgAdmin 9 閒置時常駐記憶體約 220MiB，PRD 的上限是 256M（`docker stats` 實測 221.7MiB／256MiB）：開幾個連線就可能被 OOM kill（`restart: unless-stopped` 會拉起）。沿用 PRD 數值；實際使用若頻繁重啟，把該服務的 `memory` 上限調到 512M。
- 回歸驗證範圍：`db`、`app`、`full` 三個 profile 都以真實映像實跑過（frontend／backend 使用其負責人建好的 `aisdlc-frontend:dev`／`aisdlc-backend:dev`，以 `up -d --no-build --wait` 啟動；**compose 的 `build:` 區段本輪沒有實際執行**，避免與他們的建置互踩）。實測內容：14 個長駐服務皆 healthy、經 nginx 登入並建立專案／目標／任務、Flyway 建出 13 張表並串流到 replica、對含應用資料的資料庫做全備與還原演練、failover 與切回（6.1～6.3）含真實 backend。尚未驗：Windows（〈11〉）、真實 TLS 443、`frontend`／`backend` 由 compose `build:` 重建的路徑。
- 告警盲區（沿用 PRD「值 > 閾值」的寫法）：序列不存在時規則不會觸發。從未做成任何完整備份時，`pgbackrest_backup_since_last_full_seconds` 缺席，`PgBackRestNoRecentFullBackup` 不會亮（`pgbackrest_backup_count{type="full"}` 為 0、儀表板「距上次完整備份」顯示 No data）；exporter 或 sidecar 整個停掉時，`PostgresDown`（`pg_up == 0`）與 `PgBackRestMetricsStale` 同樣沒有序列可比。`Application Overview` 第一列四個 `up` 面板（`DOWN` 紅色）是目前唯一會亮的地方；要補 `absent()`／`up == 0` 類規則，應連同 Alertmanager 一起規劃。
- nginx 的 `upstream` 在 nginx 啟動時解析一次主機名稱：backend／frontend 容器若換了 IP，nginx 會繼續打舊位址（502）直到重新載入。實測 `stop`／`start` 反序、`up -d --no-deps` 重建都拿回同一個 IP，未能重現；理論上別的容器佔走該位址才會發生。補救：`docker compose exec nginx nginx -s reload`。
- `app_logs` 卷：backend 日誌只走 stdout 的結構化 JSON（`LOGGING_STRUCTURED_FORMAT_CONSOLE`），掛載成功但卷內為空；保留此卷是為了與 PRD §11.3 一致，要檔案日誌需後端另設 file appender。

## 11. Windows 接續注意

下一輪在 Windows 11 ＋ PowerShell 接續。以下是這一塊**尚未在 Windows 驗證**的點（PowerShell 形態；不用裸 `cd`）：

| # | 待驗證 | 指令 ／ 判準 |
|---|--------|--------------|
| 1 | Docker Desktop（WSL2 後端）可啟動資料庫層，且所有容器 healthy | `Push-Location AgentConsole; docker compose --profile db up -d --build; Pop-Location` 之後 `docker compose --profile db ps -a`：minio-certs／minio-init 為 `Exited (0)`，其餘 `healthy`；pgbackrest 約需 1～2 分鐘 |
| 2 | 檔案行尾：`.sh`／`.conf`／`Dockerfile` 在 Windows 檢出必須是 LF（CRLF 會讓容器內 `bash` 報 `$'\r': command not found`） | `git ls-files --eol AgentConsole/docker` 的 `w/` 欄不得出現 `crlf`；`git config core.autocrlf` 不得覆寫 `.gitattributes` |
| 3 | 單檔 bind mount（`pgbackrest.conf`、`postgresql.conf`、`pg_hba.conf`、`servers.json`）在 NTFS 上可讀；PG 容器吃得下 Windows 掛載進來的設定檔 | `docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SHOW hba_file;"` 回 `/etc/postgresql/pg_hba.conf` 且 `pg_hba_file_rules` 無 `error` |
| 4 | pgBackRest 本機模式（兩個容器經命名卷共用 unix socket 與資料目錄）在 WSL2 上可行 | 〈3.3〉整段，特別是 `check` 兩個 repo 都 `successfully archived`、`verify-backup.sh` 兩個 repo 皆 `OK` |
| 5 | 主機埠發布：正式模式 5432／5433 不可達、疊加 dev 檔後可達；5050／9090／3001 可達 | `Test-NetConnection 127.0.0.1 -Port 5432 -InformationLevel Quiet`（`False`／`True`）；`curl.exe -s -o NUL -w "%{http_code}\n" http://localhost:5050/misc/ping` |
| 6 | PowerShell 引號：`restore.sh --target-time "…"`、含雙引號的 `psql -c "…"`、`bash -c '…'` 都照〈4.3〉〈4.4〉寫成單行 | 逐條貼上執行；`docker compose exec` 在非互動管線內需要時加 `-T` |
| 7 | 〈4.3〉的 `docker compose run --rm --no-deps …` 在 Windows 上不會把已停的 primary 拉起來 | `docker compose ps -a` 確認 `postgres-primary` 仍是 `Exited` |
| 8 | 時區：`BACKUP_TZ`（預設 `Asia/Taipei`）只影響 sidecar 的 cron；PG 容器為 UTC | `docker compose exec pgbackrest date`、PITR 的 `--target-time` 要帶 `+00` |
| 9 | 根層 shellcheck 閘門可在 Windows 以 docker 載具跑（PATH 上沒有 shellcheck 時） | `python tools\run_shellcheck.py` |
| 10 | 真實 frontend／backend／nginx 一起跑（`full`；第一次在 Windows 走 compose 的 `build:` 路徑） | `Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build --wait; Pop-Location`；`curl.exe -s -o NUL -w "%{http_code}\n" http://localhost/`（200）、`…/api/v1/projects`（401）、`…/actuator/health`（403）；80／443 被占用時 nginx 起不來 |
