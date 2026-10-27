# docker — 容器化部署資產

PRD §11（Docker 部署）與 §12（PostgreSQL 18 備援副本與災難復原）的實作：`docker-compose.yml`（全部服務）、`docker-compose.dev.yml`（本機開發）、`.env.example`，以及本目錄的各服務設定。
負責人：W2 Infra 開發者。**bash 區塊的指令都已在 macOS（Docker Desktop）實跑過；PowerShell 區塊以 macOS 上的 pwsh 7 驗過語法與引號行為（`Push-Location … Pop-Location`、`bash -c '…'`、`--target-time "…"`、`Invoke-RestMethod`），Windows 實機尚未跑（例外：〈7〉可用性 SLO 與〈14〉HTTPS 的 PowerShell 形態已於 W7 在 Windows 11＋Docker Desktop 實跑；這兩節新增的 bash 形態是同一指令的 POSIX 寫法，W7 沒有在 macOS／Linux 實跑）——`Test-NetConnection`、`curl.exe`、反斜線路徑等 Windows 專屬寫法只能在 Windows 驗，清單見〈11. Windows 接續注意〉。**

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
    ├── nginx/                    nginx.conf、conf.d/{default.conf,console-locations.inc,https-redirect.inc,https.conf.example}
    ├── postgres/primary/         Dockerfile、postgresql.conf、pg_hba.conf、pgbackrest-archive-wal.sh、init/{01-init-db.sql,02-replication.sh}
    ├── postgres/replica/         postgresql.conf、entrypoint.sh
    ├── pgbackrest/               Dockerfile、pgbackrest.conf、crontab、scripts/{backup-full,backup-incr,pg_dump-offsite,restore,verify-backup,setup-replica,pgbackrest-entrypoint,pgbackrest-metrics,pgbackrest-as-postgres,job-run,backup-ctl-export,backup-ctl-runner}.sh、tests/{stubs,fixtures}（控制面的測試替身與夾具，不進映像；〈4.6〉）
    ├── minio/                    gen-cert.sh、init-bucket.sh
    ├── redis/redis.conf
    ├── prometheus/               prometheus.yml、alerts.yml、slo.yml（可用性 SLO）、tests/{slo_test,backup_alerts_test}.yml（promtool 單元測試）
    ├── grafana/                  provisioning/{datasources,dashboards}、dashboards/{postgres-overview,app-overview}.json
    └── pgadmin/servers.json
```

### 1.1 服務（`docker compose config` 的最終結果；profile `db` 12 個、`app` 3 個、`full` 1 個）

| # | 服務 | 映像（已釘版） | profile | 網路 | 主機埠 | 資源上限 | healthcheck |
|---|------|----------------|---------|------|--------|----------|-------------|
| 1 | nginx | `nginx:1.27-alpine` | full | frontend-net、**backend-net** | 80、443 | 0.5／256M | `wget /nginx-health`（nginx 自己回 200） |
| 2 | frontend | 自建 `aisdlc-frontend:dev` | app | frontend-net、backend-net | — | 1.0／512M | `wget`／`curl` `:3000/api/health` |
| 3 | backend | 自建 `aisdlc-backend:dev` | app | backend-net、db-net | — | 2.0／1G | `wget`／`curl` `:8080/actuator/health` |
| 4 | engine-bridge | 自建 `aisdlc-engine-bridge:dev` | app | backend-net、db-net | — | 1.0／1G | python 探測 `:8081/health/deep`（深度探針：git／autoclaude／工作區可寫／DB 決定 healthy；另回報 SDD 樹但不影響 healthy，見〈9〉#28） |
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
| backend-net | 否（**固定子網** `172.31.250.0/24`，可由 `BACKEND_NET_SUBNET` 改；見〈13〉） | nginx、frontend、backend、engine-bridge、pgadmin、prometheus、grafana |
| db-net | **是**（不可出站；**對主機也不通**） | backend、engine-bridge、primary、replica、redis、pgbackrest、pgadmin、prometheus、exporters、minio（＋兩個一次性 job） |

| 卷 | 用途 |
|----|------|
| pg_data／pg_replica_data | primary／replica 資料（`PGDATA=/var/lib/postgresql/data/pgdata`） |
| pg_wal_archive | `archive_command` 的本地 WAL 複本（gzip 壓縮的 `<WAL>.gz`；replica 的 `restore_command` 唯讀讀它；每日 03:30 清 7 天前） |
| pg_backup | pgBackRest repo1（本地備份；primary 與 sidecar 共用）；另放 `.last_backup_status` |
| pg_socket | primary 的 unix socket，與 sidecar 共用（pgBackRest 本機模式，不走 SSH／TLS） |
| minio_data／minio_certs | 離站備份物件／MinIO 自簽憑證 |
| prometheus_data | Prometheus 時序資料（掛 `/prometheus`，保留期 35 天）；可用性 SLO 的 30 天歷史靠它跨 `down`／重建存活，`down -v` 才會清掉（PRD §11.3 未列，見〈9〉#34、〈7〉） |
| redis_data、nginx_certs、engine_workspace | PRD §11.3 原有 |
| app_logs | PRD §11.3 原有；backend（`console.log`）與 engine-bridge（`bridge.log`）各自把滾動檔案日誌寫在這裡（〈15〉） |
| backup_out | 備份控制面的**輸出卷**（Console「系統管理／資料庫備份」；〈4.6〉、〈9〉#35）：sidecar 寫（掛 `/backup-out`：`export/` 的 info／logical／schedule／heartbeat／jobs 與 `results/`）、backend 唯讀（`:ro,nocopy`）；PRD §11.3 未列 |
| backup_req | 備份控制面的**請求卷**：backend 寫（手動觸發的請求檔，階段二）、sidecar 唯讀（掛 `/backup-req`，`:ro,nocopy`）；PRD §11.3 未列 |

## 2. 啟動與停止

**首次**：複製環境檔並把所有 `<YOUR_...>` 換成實際值（`.env` 已被 `.gitignore` 排除；不要提交）。

```bash
cp AgentConsole/.env.example AgentConsole/.env
```

```powershell
Copy-Item AgentConsole\.env.example AgentConsole\.env
```

🔴 **`CONSOLE_ENCRYPTION_KEY` 必填**（QA DEF-AC-006）：敏感系統參數的 AES-256 金鑰，base64 編碼的 32 bytes。compose 在 `config`／`up` 階段就檢查，**未設或留空即失敗**，訊息逐字是 `required variable CONSOLE_ENCRYPTION_KEY is missing a value: CONSOLE_ENCRYPTION_KEY 必填，openssl rand -base64 32`（此前預設空值，要等 backend 啟動失敗並無限重啟約 155 秒才看得到原因）。因為 `docker-compose.dev.yml` 以 `extends` 載入整份主檔，**dev 模式也要有值**（`.env.example` 的佔位符不是空值所以 compose 放行，但 backend 啟動時會因為它不是合法的 base64 而拒絕——一定要換成真的值）。產生方式：

```bash
openssl rand -base64 32
```

```powershell
$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b)
```

金鑰遺失＝已加密的系統參數無法解密；請與資料庫備份分開保管。

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
- 全備、差異、pg_dump、驗證四條工作經 `job-run.sh` 包裝（〈4.6〉）：它只加維護鎖、狀態檔與遮罩後的輸出尾段，rc、stdout、stderr 原樣透傳，`>> cron.log` 照舊；備份腳本本體零修改。排程時間與 expire、WAL 清理兩列不變。要退回：把 `crontab` 四行改回直接呼叫 `backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`verify-backup.sh`，重建映像。

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
- **全新空卷**（QA DEF-AC-010）：換新磁碟、`pg_data` 卷被刪掉重建時，資料目錄 `…/data/pgdata` 根本不存在，而卷的根目錄屬 `root:root 0755`，postgres 無權在其下建立它。`restore.sh` 現在在 root 階段（`gosu` 之前）自己建立資料目錄、交給 `postgres`、設 `0700`，然後才進 Step 1，所以「目錄不存在」不再是失敗；此前 `find` 會在 Step 1 因 `No such file or directory` 中止。直接以 postgres 身分啟動（沒經過 root 階段）而目錄又不存在時，會印出明確原因並以 rc=1 結束。
- 🔴 **「還原後核對資料列數」是必做步驟，不可用 healthy 代替**：`restore.sh` 若中途失敗（或有人略過它）而你仍執行了 `docker compose start postgres-primary`，PG 映像的入口程序見到**空的資料目錄就 `initdb` 出一個全新的空叢集**，約 10 秒後 `docker compose ps` 照樣顯示 healthy——只看 healthy 的人會以為還原成功，其實資料全無。還原後一定要做這三項核對（都在 primary 上執行；PowerShell 形態＝`Push-Location AgentConsole; <同一段 docker compose …>; Pop-Location`）：

  ```bash
  # 1. 各表的「精確」列數（不要用 pg_stat 的估計值 n_live_tup：還原後統計是空的）；與災難前記下的數字比對
  (cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT table_name, (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS row_count FROM information_schema.tables WHERE table_schema = 'console' AND table_type = 'BASE TABLE' ORDER BY 1;")
  # 2. 時間軸：成功還原會升格出新時間軸（≥ 2）；全新的空叢集恆為 1
  (cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT timeline_id FROM pg_control_checkpoint();")
  # 3. 備份鏈健康
  (cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc check)
  ```

  判準：`console` schema 的表都在（空叢集的 `console` schema 是存在的——初始化腳本會建它——但沒有任何表，第 1 項會是 `(0 rows)`；W5 演練實測：整個 `pgdata` 刪掉直接 start，約 10 秒 healthy、第 1 項 0 列、`timeline_id`＝1）、關鍵表（例如 `projects`）的列數與災難前一致或符合 PITR 目標點、`timeline_id` ≥ 2、`check` 成功。災難前就該習慣把第 1 項的輸出存起來當基準（〈8〉每日／每週檢查可順手做）。

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

### 4.6 控制面（Console「系統管理／資料庫備份」；PRD `Console_SysAdmin_Backup_PRD.md` §9）

Console 的備份頁**看**得到清單、排程、最近四種工作的結果與資料新鮮度，靠的是 sidecar 把狀態寫成檔案、console-api 以**唯讀**方式讀。兩者之間**沒有網路、沒有 docker socket**，只有兩個具名卷（方向由 mount 旗標強制，不靠權限位元約定）：

| 卷（容器內路徑） | 寫入者 → 讀取者 | 掛載旗標 | 內容 |
|------------------|------------------|----------|------|
| `backup_out`（`/backup-out`） | sidecar → backend | sidecar 無旗標（寫入端）；backend `:ro,nocopy` | `export/{info,logical,schedule}.json`、`export/heartbeat`、`export/jobs/<job>.json`（job＝full／diff／dump／verify）、`results/<uuid>.json`（手動請求的結果，階段二） |
| `backup_req`（`/backup-req`） | backend → sidecar | backend 無旗標（寫入端）；sidecar `:ro,nocopy` | `<uuid>.json` 手動觸發請求（階段二；階段一沒有請求，只是掛著） |

- 🔴 **權限**：卷由**寫入端映像**定義擁有者（sidecar 映像把 `/backup-out` 建成 `postgres` 0755；entrypoint 的 root 階段再 `install -d -m 0755` 建 `export`、`export/jobs`、`results`），讀取端一律 `:ro,nocopy`（同 `app_logs` 的 `nocopy` 教訓：卷還空著時，每個容器 create 都會把映像內該目錄的擁有者複製進卷根，讀取端不該參與）。目錄 0755、檔 0644——讀取端是另一個 uid，**不可照抄 `Dockerfile` 其他目錄的 0750**。compose 旗標有 PyYAML 鎖（`engine-bridge/tests/test_backup_ctl_deploy_config.py`）。
- 寫檔一律「寫同目錄的 `.tmp` → `mv` 改名」，讀取端永遠看不到半個檔；所有檔含 `schema_rev: 1`，不含任何金鑰、密碼或 cipher。
- **三支新腳本**（`docker/pgbackrest/scripts/`，只在容器內執行；shellcheck 全嚴重度乾淨）：
  - `job-run.sh <full|diff|dump|verify> <scheduled|manual> [<uuid>]`：crontab 四條工作的包裝。以**命令形** `flock -o` 取維護鎖（`/run/backup-ctl/maintenance.lock`，sidecar 本地、不在共享卷；🔴 不用 fd 形持鎖：`/proc/locks` 看不到、verify 起的暫存 PG 會繼承鎖 fd）。排程等待至 `JOB_LOCK_WAIT_SECONDS`（7200）、逾時＝不執行腳本、記 `failed`／`lock_timeout`／rc 75；手動不等待，拿不到＝立即 rc 75（`busy`）。持鎖期間寫 `jobs/<job>.json`（running → 終態；終態一定在鎖釋放前寫完，否則清掃會把正常結束的工作誤判成中斷）、輸出尾段先遮罩（`pass`／`secret`／`key`／`token` 的值、AWS 金鑰 id、連線字串密碼）再取最後 2000 字元。結束碼＝備份腳本的 rc 原樣（75 專指 busy 與 lock_timeout）。🔴 它在每一條排程備份的路徑上，所以每一步都有退路：鎖檔開不了、狀態檔寫不了、擷取失敗一律 WARN 後照常執行。
  - `backup-ctl-runner.sh`：迴圈（背景、`postgres` 身分、每 ≤5 秒），**永不等待子行程**：每輪清掃（進行中但維護鎖沒有持有者＝容器重啟中斷，改記 `interrupted`）、更新 `export/heartbeat`＝`{schema_rev, ts, lock_held}`（`lock_held` 只讀 `/proc/locks` 比對鎖檔 dev:ino，**不取鎖探測**）、必要時在背景啟動匯出。Console 以 30 秒判斷它是否離線。階段二加請求處理。
  - `backup-ctl-export.sh`：每 60 秒與每次工作結束後由 runner 以 `timeout 120` 啟動一輪（前一個未結束就略過）：`export/info.json`＝`pgbackrest info` 的**原輸出**（逐字嵌入）加 `retention`（問 pgBackRest 自報的有效值：`pgbackrest help expire repo-retention-full`／`-diff` 的 `current:`；不自己讀 `pgbackrest.conf`，解析不到＝`null`、不填預設值）與 `repos`（repo2 端點主機名不含 `.`、或為 `localhost`／回送位址／`host.docker.internal` ⇒ `local: true`，Console 會標「與主機同碟」）；`export/logical.json`＝離站 `logical/` 的 `mc ls`（至多每 300 秒）。失敗只寫 `ok:false`（不寫部分清單、不保留舊內容冒充新鮮），結束碼仍為 0。`export/schedule.json` 在 entrypoint 的 root 階段由 crontab 產生一次（crontab 是 `root:root 0600`）。
- **對照指標與規則**：`pgbackrest-metrics.sh` 另輸出 `aisdlc_backup_job_last_status{backup_job}`（0 成功、1 失敗或中斷）、`aisdlc_backup_job_last_finished_timestamp_seconds{backup_job}`、`aisdlc_backup_ctl_heartbeat_timestamp_seconds`；`alerts.yml` 新增 `PgBackRestJobFailed`（只管 dump 與 verify；全備與差異由 `PgBackRestLastBackupFailed` 管）與 `PgBackRestControlHeartbeatStale`（心跳超過 120 秒）。🔴 標籤名是 `backup_job`、**不是 `job`**：抓取目標標籤 `job="pgbackrest"`（`prometheus.yml` 未設 `honor_labels`）會把曝光的 `job` 改名成 `exported_job`，用 `{job=~…}` 的規則就永遠匹配不到（promtool 的人造序列看不出這個，只有真抓取看得出）。執行中（`running`）的 job 不輸出序列。
- **看狀態**（唯讀；PowerShell 形態＝`Push-Location AgentConsole; <同一段 docker compose …>; Pop-Location`）：

  ```bash
  (cd AgentConsole && docker compose exec pgbackrest cat /backup-out/export/heartbeat)
  (cd AgentConsole && docker compose exec pgbackrest cat /backup-out/export/jobs/full.json)
  (cd AgentConsole && docker compose exec pgbackrest bash -c 'jq -c "{generated_at, ok, retention, repos}" /backup-out/export/info.json')
  ```

  ```powershell
  Push-Location AgentConsole; docker compose exec pgbackrest cat /backup-out/export/heartbeat; Pop-Location
  Push-Location AgentConsole; docker compose exec pgbackrest cat /backup-out/export/jobs/full.json; Pop-Location
  Push-Location AgentConsole; docker compose exec pgbackrest bash -c 'jq -c "{generated_at, ok, retention, repos}" /backup-out/export/info.json'; Pop-Location
  ```

- **測試**：控制面腳本的契約測試用 `docker/pgbackrest/tests/` 的替身（`stubs/` 的 `pgbackrest`、`mc`、`flock`、`mv` 與四支 stub 工作腳本；行為由 `STUB_*` 環境變數決定，用法見各檔檔頭）與夾具（`fixtures/info-2repo.json`、`logical-2.json`、`mask-probes.txt`；遮罩探針與 console-api 的 `BackupMasker` 共讀同一檔）。`flock`、`mv` 兩支替身與真命令同名，只准在需要它們的情境放進 `PATH`。靜態旗標鎖與規則的 promtool 測試：

  ```bash
  (cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && python -m pytest -q tests/test_backup_ctl_deploy_config.py)
  docker run --rm -v "$PWD/AgentConsole/docker/prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/backup_alerts_test.yml
  ```

  ```powershell
  Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; python -m pytest -q tests/test_backup_ctl_deploy_config.py; Pop-Location
  docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/backup_alerts_test.yml
  ```

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
| 告警規則 | Prometheus UI 的 Alerts 頁 | `docker/prometheus/alerts.yml`：PRD §12.6.2 的 9 項閾值＋WAL 歸檔失敗、stanza 異常、指標過期，另加備份控制面兩條（`PgBackRestJobFailed`、`PgBackRestControlHeartbeatStale`，〈4.6〉；共 14 條）；`docker/prometheus/slo.yml`：Console 可用性 SLO（3 條 recording rules＋`ConsoleDown`、`ConsoleAvailabilityBelowTarget` 兩條告警，見下方〈可用性 SLO〉）；沒有 Alertmanager，不會對外通知 |

- **PostgreSQL Overview**（38 個面板，六列對應 PRD §12.6.3）：PG 總覽、複製狀態、查詢效能、備份狀態、鎖與等待、儲存空間。**Application Overview**（19 個面板）：抓取目標狀態＋可用性 SLO（30 天可用率 stat、1／7／30 天趨勢）＋ Spring Boot（Micrometer）面板；backend 沒起時 Spring Boot 面板顯示 No data。
- **pgBackRest 指標**（ADR-001 G-04：PRD §12.6.2 的 `pgbackrest_*` 沒有現成 exporter）：sidecar 的 `pgbackrest-metrics.sh` 每 60 秒用 `pgbackrest info --output=json` 產生 Prometheus 文字格式，busybox httpd 在 `:9854/metrics` 提供。含 `pgbackrest_backup_since_last_full_seconds`、`pgbackrest_backup_last_status`（PRD 兩個指名指標）、備份份數／大小／耗時、stanza 與 repo 狀態碼，以及 `aisdlc_storage_*`（備份 repo／WAL 歸檔目錄用量、資料卷磁碟使用率）。失敗的備份不會出現在 `pgbackrest info`，所以 `last_status` 由備份腳本寫狀態檔（`pg_backup` 卷內 `.last_backup_status`）後轉出。
- PRD 指標名與 postgres_exporter 實際名稱的對照：`pg_stat_bgwriter_buffers_alloc` → `pg_stat_bgwriter_buffers_alloc_total`；`pg_stat_statements_mean_time` → `rate(pg_stat_statements_seconds_total) / rate(pg_stat_statements_calls_total)`。
- 🔴 **WAL 歸檔失敗是最危險的靜默失效**：`archive_command` 失敗時 PG 不會回收 WAL，`pg_wal` 會一直長到磁碟滿。離站儲存（MinIO／S3）一掛，`archive-push` 就失敗（兩個 repo 都要成功）。看 `PostgresWalArchiveFailing` 告警、Grafana 的「WAL 歸檔失敗（15m）」面板，或 `SELECT failed_count, last_failed_time FROM pg_stat_archiver;`。
- Prometheus 的時序資料放在具名卷 `prometheus_data`（掛 `/prometheus`；PRD §11.3 未列，見〈9〉#34）：`down` 不會清它、重新 `up` 後歷史還在；`down -v` 才會清掉（等於歷史歸零，見下方〈可用性 SLO〉）。Grafana 沒有掛資料卷（PRD 未列；資料來源與兩個 dashboard 由 provisioning 檔載入，不依賴卷內狀態）。

### 可用性 SLO（NFR-9.3-01：99.5%）怎麼看

PRD §9.3「可用性 目標 99.5% Uptime」由 `docker/prometheus/slo.yml` 量測：以 backend 的抓取結果 `up{job="spring-boot"}` 在窗口內的**平均值**當可用率，三條 recording rules（每分鐘算一次）`aisdlc:console_availability:ratio_1d`／`ratio_7d`／`ratio_30d`。30 天窗口 99.5% 的誤差預算是 3.6 小時（0.5% × 720 小時）。

| 要看什麼 | 去哪裡 |
|----------|--------|
| 30 天可用率（達標綠、未達標紅）、1／7／30 天趨勢 | Grafana〈Application Overview〉最上方「可用性 SLO」那一列：stat 面板「30 天可用率（目標 99.5%）」與時序面板「1 天可用率（另附 7 天、30 天窗口）」 |
| 精確值 | Prometheus UI（`http://localhost:9090`）查 `aisdlc:console_availability:ratio_30d`，或下方的 API 指令 |
| 告警 | Prometheus UI 的 Alerts 頁：`ConsoleDown`（backend 連續 1 分鐘抓不到，critical）、`ConsoleAvailabilityBelowTarget`（30 天可用率 < 99.5% 持續 15 分鐘，critical；停機結束後仍會響到那段停機移出 30 天窗口為止） |

```bash
curl -s 'localhost:9090/api/v1/query?query=aisdlc:console_availability:ratio_30d'
curl -s localhost:9090/api/v1/rules | python3 -c 'import json,sys; [print(g["name"], [r["name"] for r in g["rules"]]) for g in json.load(sys.stdin)["data"]["groups"] if g["name"].startswith("aisdlc-console")]'
```

```powershell
(Invoke-RestMethod 'http://localhost:9090/api/v1/query?query=aisdlc:console_availability:ratio_30d').data.result | ForEach-Object { "$($_.metric.instance) $($_.value[1])" }
(Invoke-RestMethod http://localhost:9090/api/v1/rules).data.groups | Where-Object { $_.name -like 'aisdlc-console*' } | ForEach-Object { "$($_.name): $($_.rules.name -join ', ')" }
```

規則本身有 promtool 單元測試（`docker/prometheus/tests/slo_test.yml`：停機 7 小時／1 小時、3 小時與 4 小時夾住 0.5% 邊界、1／7／30 天窗口、停機移出窗口後告警解除、`ConsoleDown` 的 `for: 1m`、`for: 15m`、歷史不足時的放大；約 20 秒）。在 monorepo 根執行，不需要先起任何容器：

```bash
docker run --rm -v "$PWD/AgentConsole/docker/prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/slo_test.yml
docker run --rm -v "$PWD/AgentConsole/docker/prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 check rules /etc/prometheus/slo.yml /etc/prometheus/alerts.yml
docker run --rm -v "$PWD/AgentConsole/docker/prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 check config /etc/prometheus/prometheus.yml
```

```powershell
docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/slo_test.yml
docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 check rules /etc/prometheus/slo.yml /etc/prometheus/alerts.yml
docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 check config /etc/prometheus/prometheus.yml
```

- 🔴 **這套機制驗證的是「量測會不會算對、會不會響」，不是「Console 這 30 天實際有多少可用率」**：後者是營運觀測值，只能由持續運轉的環境在 Grafana 看；任何單次驗證都不能宣稱 30 天的數值。
- **量到的是 backend 的 `up`，不是外部使用者的體驗**：只有 frontend 或 nginx 掛掉不會讓它變 0；Prometheus 自己停機的期間沒有樣本，不計入。要涵蓋這兩者需要從外部探測入口（blackbox_exporter 打 `https://<入口>/nginx-health`），不在本專案範圍（原因：沒有 nginx exporter，見 `slo.yml` 檔頭）。
- **只起資料庫層（`--profile db`）時 backend 不存在**：`ConsoleDown` 會一直 firing、30 天可用率面板為 0%，屬預期（`spring-boot` 目標恆為 down）。
- **剛起動時查不到 `ratio_*` 屬正常**：群組每 60 秒才評估一次；W7 全棧實測 Prometheus 起動後約 2 分鐘才查得到值（`/api/v1/rules` 上規則 `health` 為 `ok` 但 `query` 回空陣列時，再等一輪即可），此前 Grafana 的 stat 面板顯示 No data。
- **保留期與歷史**：Prometheus 的 `--storage.tsdb.retention.time` 由 15d 提高到 35d——維持 15d 時 `ratio_30d` 只涵蓋 15 天卻標成 30 天。時序資料放在具名卷 `prometheus_data`（掛 `/prometheus`），容器被 `down`、重建或映像升版都不影響歷史，只有 `down -v`（或手動刪卷）才歸零；歷史不足窗口長度時（剛部署、或卷被清掉）以「已有資料的期間」計算，剛部署幾天內的短暫停機會被放大（剛起 2 小時停機 1 分鐘＝99.17%，已低於 99.5% 而告警；`slo_test.yml` 把這個現象釘成測試）。這個具名卷是相對 PRD 卷清單新增的（〈9〉#34）。

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
| 23 | §12.6.1 prometheus.yml 三個 job | 增 `pgbackrest`、`prometheus` 兩個 job、`rule_files`（`alerts.yml`、`slo.yml`）；`pgbackrest` job 指定 `fallback_scrape_protocol: PrometheusText0.0.4`；exporter 加 `stat_statements`、`stat_checkpointer`、`long_running_transactions`、`postmaster` 收集器；Prometheus 保留期 15d → 35d | busybox httpd 的 `Content-Type` 是 `application/octet-stream`，Prometheus 3 預設拒收無法辨識的型別。`slo.yml`（W7 D-14，PRD §9.3 可用性 99.5%）：30 天窗口要有 30 天以上的原始樣本，15d 保留期會讓 `ratio_30d` 名實不符（〈7〉） |
| 24 | §11.5 只給 `default.conf` | 補標準 `nginx.conf`；`/nginx-health`；Connection 標頭改用 `$connection_upgrade`；443 區塊只留註解範例 | PRD 發布了 443 並掛憑證卷，卻沒有 ssl server 區塊 |
| 25 | §12.5.2 failover＝主機側 bash 腳本；§12.3.4 `restore.sh`＝主機側腳本 | 改為 `docker compose …` 指令序列（〈4.3〉〈6〉）；容器內只保留 `restore.sh` 的清資料＋還原兩步；backend／Bridge 的 DB 主機改由 `POSTGRES_HOST` 參數化 | NFR-XPL-03：Windows 主機沒有 bash。PRD 手動改 compose 內的連線字串，改參數易錯 |
| 26 | — | 增 `name: aisdlc`、`json-file` 日誌輪替（10m×3）、primary／replica `shm_size: 256mb` 與 `stop_grace_period: 60s`、sidecar `init: true`、`BACKUP_TZ`、卷 `pg_socket`／`minio_data`／`minio_certs`、`alerts.yml`、每日清 WAL 歸檔的 cron | 可重現的卷名；日誌不撐爆磁碟；PG 預設 `/dev/shm` 64MB 對平行查詢太小；cron 時區；PRD 的 WAL 7 天保留沒有任何清理機制 |
| 27 | 卷名 `pg_backup`（PRD、Architecture、RTM） | 沿用 `pg_backup` 作為 pgBackRest repo1（任務書提到的 `pgbackrest_repo` 是同一個東西） | 與 RTM `INF-VOL-04`、Architecture §2.5 一致 |
| 28 | §11.3 Bridge 沿用淺層 healthcheck；映像基底 `python:3.11-slim` | Bridge 映像安裝 `git`＋`ca-certificates`；映像與 compose 的 healthcheck 改打 `GET /health/deep`（深度探針，逐項實測 git／autoclaude／工作區可寫／DB，前四項任一失敗回 503；W7 起另回報第五項 SDD 樹（`checks.sdd`）——**只當資訊、不影響 200／503**，所以沒掛 SDD 的 Bridge 照樣 healthy，它的狀態由 Console 的 SDD 卡顯示，規則見 `engine-bridge/README.md`）；契約 v1.4（D-17）起 console-api 的探測環預設也打它（`autoclaude.healthCheckPath`） | W4-QA **DEF-AC-003（P1）**：slim 映像沒有 git，引擎內共 11 處 subprocess 呼叫 git，Docker 全棧下任何批次一律 `FAILED`（`FileNotFoundError: 'git'`），而 `/health` 永遠 200、容器永遠 healthy——本機（有 git）、mock、pytest 全綠，只有全棧真跑才現形。深度探針每次會 spawn 一次 git、建刪一個暫存檔（v1.2 因此只給容器編排用；D-17 起探測環也打，成本對單一 Bridge 可忽略） |
| 29 | §11.5 nginx `error_log` 預設 `notice`；`/api/` 一律反代到 backend；靜態資源的 `Cache-Control` 由 nginx `add_header` 加 | `error_log … crit`；`location = /api/health` 導向 frontend；`/_next/static/` 以 `proxy_hide_header` 丟掉上游那份、只留 nginx 的一份；全部 location 抽成 `console-locations.inc`（80 與 443 共用） | **DEF-AC-008**：上游被切斷時 `error_log` 印出含 `?access_token=<JWT>` 的完整請求行（81 行 `[error]` 有 16 行含 token 值）；`log_format` 管不到它。代價見〈10〉。**O-08**：前端的 `/api/health` 被反代到 backend 而回 401。**O-09**：`Cache-Control` 出現兩次（nginx 與 Next 各一）。抽 include 的理由：HTTP 與 HTTPS 兩個 server 的路由必須一致（〈14〉） |
| 30 | §11.6 `CONSOLE_ENCRYPTION_KEY=<…>`（compose 預設空字串） | compose 改 `${CONSOLE_ENCRYPTION_KEY:?…}` 必填；`.env.example` 寫明產生方式 | **DEF-AC-006**：compose 層放行空值，backend 啟動失敗後無限重啟、約 155 秒才看得到「container is unhealthy」；改後與 `POSTGRES_PASSWORD` 一樣在 `config` 階段就失敗（〈2〉） |
| 31 | 網路不指定子網（Docker 動態分配） | `backend-net` 固定子網（預設 `172.31.250.0/24`）；backend 的 `CONSOLE_INTERNAL_PROXIES` 預設只信該子網的 `.2`～`.254` | **O-20**：Tomcat `RemoteIpValve` 預設信任所有私網位址，主機（Docker 閘道）或內網客戶端進來的請求可偽造 `X-Forwarded-For` 換掉限流的桶（〈13〉）。沒有固定子網就無法在 compose 層給出「只信 nginx 所在網段」的值 |
| 32 | §11.3 `app_logs` 卷掛在 backend／Bridge，但沒有任何東西寫進去 | backend 設 `LOG_DIR=/app/logs`（`console.log`）、Bridge 設 `BRIDGE_LOG_DIR=/app/logs`（`bridge.log`），各自每日切檔、保留 7 份；Bridge 映像把 `/app/logs` 設為 `1777`（兩個容器用不同 uid 寫同一個卷），且 backend 掛載該卷時加 `:nocopy` | **INF-VOL-06／C-16**：此前「掛載成功但卷內為空」；每行日誌帶 trace_id 的規格見〈15〉。🔴 實測陷阱：具名卷「還空著」時，Docker 在**每個**容器 create 時都把映像內該目錄的擁有者與權限複製進卷根，compose 先 create engine-bridge、後 create backend，最後一個 create 的 backend（`spring:spring 0755`）蓋掉 Bridge 映像的 `1777`，Bridge 寫 `bridge.log` 得 `Permission denied`（日誌只在 stderr 留警告）。backend 加 `:nocopy` 後卷根只由 Bridge 映像決定，與 create 順序無關（實測：`drwxrwxrwt`、uid 10001 與 1001 皆可寫） |
| 33 | §11.5 只留 443 區塊的註解範例 | 提供 `https.conf.example`（443、憑證取自 `nginx_certs` 卷）與 `https-redirect.inc`（80 轉址到 443、保留 `/nginx-health`）；預設不啟用，步驟見〈14〉 | **INF-VOL-07**：此前「憑證實際放入與 HTTPS 區塊」缺 |
| 34 | §11.3 卷清單沒有 Prometheus 的卷（時序資料落在映像宣告的匿名卷） | 增具名卷 `prometheus_data` 掛 `/prometheus`（頂層 `volumes:` 宣告，`driver: local`） | **NFR-9.3-01**：可用性 SLO 的 30 天可用率要跨 `down`／容器重建存活（〈7〉）。不掛卷時資料在匿名卷，`down` 之後重起接到的是新卷（Docker 對匿名卷的一般行為；W7 沒有做不掛卷的負向實測）。實測（Windows 11＋Docker Desktop，用獨立專案名 `w7probe` 只起 prometheus，免得污染 `aisdlc_*` 卷）：掛載型態 `volume`、`/prometheus` 屬 `nobody`（uid 65534）且可寫（`wal`、`chunks_head` 在卷內）；`down`（不帶 `-v`）後卷仍在，重起後同一時段的 3 筆 `up{job="prometheus"}` 樣本逐筆相同。`down -v` 會清掉它（〈2〉清場） |
| 35 | §11.3 卷清單 12 個；§12.3.3 crontab 直接呼叫四支備份腳本；sidecar 沒有狀態輸出，Console 看不到備份狀態 | 增具名卷 `backup_out`（sidecar 寫、backend `:ro,nocopy`）與 `backup_req`（backend 寫、sidecar `:ro,nocopy`）；crontab 四條備份與驗證工作改經 `job-run.sh` 包裝；sidecar 增 `job-run.sh`、`backup-ctl-runner.sh`、`backup-ctl-export.sh`；`pgbackrest-metrics.sh` 增三個指標；`alerts.yml` 增兩條規則（共 14 條）；entrypoint 增 root 階段建目錄、產生 `schedule.json`、背景啟 runner（細節見〈4.6〉） | Console「系統管理／資料庫備份」（`Console_SysAdmin_Backup_PRD.md`）：頁面要「看」清單、排程與最近結果，並（階段二）讓 ADMIN 手動觸發。console-api 與 sidecar 之間只准有檔案 I/O——無新埠、無 docker socket（ADR-BK-1 的 B′ 方案：兩卷、方向由 mount 旗標強制）。包裝只加鎖、寫狀態、透傳 rc，鎖檔開不了與狀態檔寫不了都 fail-open（PRD §10 R1：包裝出錯＝排程備份失敗）；各備份腳本本體零修改，`.last_backup_status` 與 `pgbackrest_backup_last_status` 的語意與值不變。真輸出實測（pgBackRest 2.59.3）：`help expire repo-retention-full` 在兩個 repo 同值時印單值 `current: 4`、各自不同時印縮排的逐 repo 列，`repo-retention-diff` 只列有設定的 repo（本專案只有 `repo1: 7`）；`--log-level-console=off` 可去掉前後各一行 INFO 日誌 |

## 10. 已知限制

- **failover 之後備份鏈在升格節點那一段是斷的**：replica 映像沒有 pgBackRest，升格後它的 WAL 不會歸檔；切回拓撲後必須立刻做新的全備（〈6.3-d〉）。failover 期間 sidecar 綁的是原 primary 的資料卷，建議先停掉。
- **離站儲存一掛，primary 的 `pg_wal` 就開始累積**（兩個 repo 都要歸檔成功）。已有告警規則，但沒有 Alertmanager；磁碟滿前要人介入。
- 本機 MinIO 是單碟、自簽憑證、官方映像已下架（改用社群 fork）：只適合開發與驗證，正式環境請用真 S3（〈4.5〉）。
- 邏輯備份檔沒有客戶端加密；本機 MinIO 的 bucket 沒有加密。
- Redis 沒有密碼（只在 internal 的 db-net）；開發疊加檔把它發布到 `127.0.0.1`，不要改綁對外位址。
- 只要有任何寫入，資料庫每 60 秒就換一個 16MB 的 WAL 段，離站 repo 與本地複本會持續長大（壓縮後每段約 70～80KB、保留政策會清；完全閒置時則不會）；`PostgresWalArchiveFailing` 與 `pg_stat_archiver` 是看歸檔是否健康的地方。
- `pgvector/pgvector:pg18` 映像宣告了 `VOLUME /var/lib/postgresql`，所以 primary／replica／pgbackrest／minio-certs 各會多出一個匿名卷（裡面只有 `data／wal_archive` 兩個掛載點目錄）。容器因改映像或設定而被「重建」時，舊的匿名卷會變成懸空卷，`down -v` 清不掉它們（實測 7 個）：偶爾用 `docker volume ls -f dangling=true` 檢視，確認內容只有 `data／wal_archive` 再個別 `docker volume rm`；不要無差別 `docker volume prune`。
- Grafana 沒有持久卷（PRD 未列；資料來源與 dashboard 由 provisioning 檔載入，不受影響），pgAdmin 的設定也在容器內。Prometheus 有具名卷 `prometheus_data`（〈9〉#34）：`down` 之後可用性 SLO 的 1／7／30 天歷史仍在，只有 `down -v`（〈2〉清場）會把它一併清掉、30 天可用率要重新累積（〈7〉可用性 SLO）。
- pgAdmin 9 閒置時常駐記憶體約 220MiB，PRD 的上限是 256M（`docker stats` 實測 221.7MiB／256MiB）：開幾個連線就可能被 OOM kill（`restart: unless-stopped` 會拉起）。沿用 PRD 數值；實際使用若頻繁重啟，把該服務的 `memory` 上限調到 512M。
- 回歸驗證範圍：`db`、`app`、`full` 三個 profile 都以真實映像實跑過（frontend／backend 使用其負責人建好的 `aisdlc-frontend:dev`／`aisdlc-backend:dev`，以 `up -d --no-build --wait` 啟動；**compose 的 `build:` 區段本輪沒有實際執行**，避免與他們的建置互踩）。實測內容：14 個長駐服務皆 healthy、經 nginx 登入並建立專案／目標／任務、Flyway 建出 13 張表並串流到 replica、對含應用資料的資料庫做全備與還原演練、failover 與切回（6.1～6.3）含真實 backend。尚未驗：Windows 的其餘項目（〈11〉；HTTPS 自簽流程與可用性 SLO 已在 W7 於 Windows 11 實跑）、CA 簽發的真憑證與續期（不在本專案範圍）、`frontend`／`backend` 由 compose `build:` 重建的路徑。
- 告警盲區（沿用 PRD「值 > 閾值」的寫法）：序列不存在時規則不會觸發。從未做成任何完整備份時，`pgbackrest_backup_since_last_full_seconds` 缺席，`PgBackRestNoRecentFullBackup` 不會亮（`pgbackrest_backup_count{type="full"}` 為 0、儀表板「距上次完整備份」顯示 No data）；exporter 或 sidecar 整個停掉時，`PostgresDown`（`pg_up == 0`）與 `PgBackRestMetricsStale` 同樣沒有序列可比。`Application Overview` 第一列四個 `up` 面板（`DOWN` 紅色）是目前唯一會亮的地方；要補 `absent()`／`up == 0` 類規則，應連同 Alertmanager 一起規劃。
- **備份控制面新規則的盲區**（沿用上一條「值 > 閾值」的寫法）：`PgBackRestJobFailed` 與 `PgBackRestControlHeartbeatStale` 在序列不存在時不會觸發——某個工作**從未執行**（沒有 `jobs/<job>.json`）、執行中（`running` 不輸出序列，規則只看上一次終態）、或 sidecar／runner 從來沒起來（沒有心跳檔）都不會亮；`PgBackRestJobFailed` 只管 dump 與 verify（全備與差異的失敗由 `pgbackrest_backup_last_status` 與 `PgBackRestLastBackupFailed` 管）。Console 備份頁的「從未執行」「逾期」「備份控制面無回應」標記是目前唯一覆蓋這些情形的地方；規則的 promtool 測試把盲區釘成案例（`backup_alerts_test.yml` 的「序列缺席」），日後補 `absent()` 規則時要連同這裡一起改。promtool 測試**本機限定**：`.github/workflows` 沒有 promtool 步驟。
- **runner 死掉不會被重啟**：它是 entrypoint 的背景行程，沒有監督迴圈；死掉時心跳過期（Console 紅橫幅、`PgBackRestControlHeartbeatStale`），但備份排程（crond 與 `job-run.sh`）不受影響。`docker compose restart pgbackrest` 即可恢復。`/backup-req` 在 sidecar 是唯讀掛載：runner 啟動時對逾 24 小時的殘留請求檔只能記 WARN（刪不掉，由寫入端 console-api 清理）。
- **`job-run.sh` 的 75**：結束碼 75 專指「手動拿不到鎖」與「排程等鎖逾時」；備份腳本自己若以 75 結束會與之混淆（現有四支不會）。擷取輸出的 `tee` 在工作腳本結束後最多再等 3 秒——若有子行程（例如 verify 的暫存 PG 異常殘留）仍握著管線寫端，包裝不再等它、結束 `tee` 並照常釋放鎖。
- nginx 的 `upstream` 在 nginx 啟動時解析一次主機名稱：backend／frontend 容器若換了 IP，nginx 會繼續打舊位址（502）直到重新載入。實測 `stop`／`start` 反序、`up -d --no-deps` 重建都拿回同一個 IP，未能重現；理論上別的容器佔走該位址才會發生。補救：`docker compose exec nginx nginx -s reload`。
- `app_logs` 卷：backend（`LOG_DIR=/app/logs` → `console.log`）與 engine-bridge（`BRIDGE_LOG_DIR=/app/logs` → `bridge.log`）各自寫滾動檔案日誌，stdout 的日誌（`docker compose logs`）照舊。檔案日誌的寫入失敗（舊卷權限不對、卷唯讀）不會讓服務起不來，只在該服務自己的日誌留一則警告；**既有的舊 `app_logs` 卷**（W5 之前建立）的擁有者與權限由當初第一個掛載它的映像決定（Bridge 映像當時沒有 `/app/logs` 目錄＝`root:root 0755`，或 backend 的 `spring` 0755），另一個服務因此寫不進去——`docker compose down -v` 重建，或 `docker run --rm -v aisdlc_app_logs:/l busybox chmod 1777 /l` 就地修（〈15〉）。
- **資源上限貼近實用量（QA O-19，僅記錄、本輪不調）**：全棧實跑時 backend 實用 928MiB／1GiB、pgAdmin 242MiB／256MiB（`docker stats`）。JVM 以 `MaxRAMPercentage=75` 依容器上限自行調整堆積，短期不會因此失敗；若 `docker compose ps` 看到服務反覆重啟、`docker inspect <容器> --format '{{.State.OOMKilled}}'` 為 `true`，把該服務在 `docker-compose.yml` 的 `deploy.resources.limits.memory` 調高（backend 建議 2G、pgAdmin 512M）。
- **nginx `error_log` 降到 `crit` 的代價**：nginx 平常的 error／warn 訊息（`upstream timed out`、`connect() failed`、`client intended to send too large body`…）都不再出現在 `docker compose logs nginx`，上游失敗的細節看不到（原因：`[error]` 級會把含 `?access_token=` 的完整請求行寫進日誌，DEF-AC-008）。要除錯時暫時把 `docker/nginx/nginx.conf` 最上方的 `crit` 改回 `error`、`docker compose restart nginx`，重現後**立刻改回 `crit`**，並用 `docker compose up -d --force-recreate nginx` 讓已累積含 token 的日誌隨舊容器消失（只 restart 清不掉）。治本是前端改用 fetch 串流帶 `Authorization` 標頭（契約 §2.8），不再把 token 放進網址。
- **`backend-net` 固定子網可能與本機其他網段重疊**：預設 `172.31.250.0/24`；`docker compose up` 報 `Pool overlaps with other one on this address space` 時，在 `.env` 同時改 `BACKEND_NET_SUBNET` 與 `CONSOLE_INTERNAL_PROXIES`（〈13〉）。從舊版（動態子網）升級時不必先 `down`：實測 compose 會自動停掉掛在舊 `backend-net` 上的專案容器、換成固定子網的新網路、再把容器起回來（rc=0；升級後第一次 `up -d` 這些容器會被重啟一次）。若有人用 `docker network connect` 把**非 compose 管理**的容器手動接在該網路上，換網路可能因「有作用中的端點」失敗（Docker 不會移除仍有端點的網路；此情形未實測），需先自行卸除。

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

## 12. 正式部署前必做（預設帳號、內部端點）

### 12.1 預設帳號與密碼必須更換（QA O-06）

- Docker 全棧在 `.env` **沒有**設 `CONSOLE_ADMIN_PASSWORD_HASH`／`CONSOLE_OPERATOR_PASSWORD_HASH`／`CONSOLE_VIEWER_PASSWORD_HASH` 時，backend 使用**開發預設**的三個帳號（`admin`／`operator`／`viewer`）與寫在 `backend/README.md` 的預設密碼——那些密碼是公開文件的一部分，等於沒有密碼。任何對外、多人共用或存放真實資料的部署，**必須**在第一次啟動前於 `.env` 覆寫三個 BCrypt 雜湊（雜湊產生法見 `backend/README.md`；`.env` 內雜湊的 `$` 要寫成 `$$`，範例在 `.env.example`），並確認用舊的預設密碼登入回 401。
- 其餘服務沒有預設密碼：Grafana、pgAdmin、MinIO root、`POSTGRES_PASSWORD`、`REPLICATION_PASSWORD`、`PGBACKREST_CIPHER_PASS`、`CONSOLE_ENCRYPTION_KEY`、`JWT_SECRET` 都是必填，沒填 compose 就在 `config` 階段失敗。

### 12.2 `/actuator/prometheus` 與 `/actuator/health` 免 token，防護全靠網路隔離（QA O-16）

backend 的 `GET /actuator/prometheus`、`GET /actuator/health` **不需要 token**（`ActuatorIT` 明載；Prometheus 抓取與容器 healthcheck 需要它）：直連 backend 埠時任何人都讀得到指標。Docker 全棧靠三層隔離擋住，**缺一不可**：

1. backend 容器**不對主機發布任何埠**（compose 的 backend 沒有 `ports:`）；
2. nginx 的 `location /actuator/ { deny all; }` 擋掉經入口的存取（回 403，實測）；
3. Prometheus 在 `backend-net` 內以服務名 `backend:8080` 直接抓取，不經 nginx。

因此：不要替 backend 加 `ports:`、不要把不受信任的容器接進 `backend-net`、不要在 nginx 為 `/actuator/` 加放行。一旦 backend 埠被發布到主機或叢集外，這兩個端點就等於公開（指標含路徑、延遲、JVM 與連線池資訊）。

## 13. 反向代理與 X-Forwarded-For 信任（QA O-20）

**背景**：backend 以 `X-Forwarded-For` 還原客戶端位址（`server.forward-headers-strategy=native`，由 Tomcat `RemoteIpValve` 處理），**未認證**請求的限流以此位址分桶（登入後以 JWT subject 分桶，不受影響）。`RemoteIpValve` 預設信任**所有私網位址**作為「可信代理」——從主機進來的請求在 Docker 下以閘道的私網位址抵達 nginx，內網客戶端也是私網位址，兩者都被當成可信代理，於是其後由客戶端自填的 `X-Forwarded-For` 被採信：QA 實測連打 101 次後改 `X-Forwarded-For: 203.0.113.77`、`203.0.113.78` 即各換一個新桶，**不會 429**，未認證限流可被繞過。

**對策（compose 預設已套用）**：

- `backend-net` 固定子網；backend 的 `CONSOLE_INTERNAL_PROXIES`（對應 `server.tomcat.remoteip.internal-proxies`）預設**只信任該子網的 `.2`～`.254`**——nginx 在其中；`.1` 是 Docker 閘道（＝主機端進來的請求位址），刻意排除；其餘私網位址一律不信。客戶端偽造的 `X-Forwarded-For` 因此不會被採信。

| 設定（`.env`） | 預設 | 說明 |
|----------------|------|------|
| `BACKEND_NET_SUBNET` | `172.31.250.0/24` | `backend-net` 的子網 |
| `CONSOLE_INTERNAL_PROXIES` | `172\.31\.250\.(?:[2-9]\|[1-9]\d\|1\d\d\|2[0-4]\d\|25[0-4])` | Java 正規表示式，對 IP 字串**整串比對**；預設＝上列子網的 `.2`～`.254` |

**什麼時候要改**：`docker compose up` 報 `Pool overlaps with other one on this address space`（本機其他 Docker／VPN 網段與預設子網重疊）。**兩個要一起改**，且值在 `.env` 裡不加引號、照字面寫（例：子網改 `10.77.5.0/24`，則 `CONSOLE_INTERNAL_PROXIES=10\.77\.5\.(?:[2-9]|[1-9]\d|1\d\d|2[0-4]\d|25[0-4])`）。查實際值：

```bash
(cd AgentConsole && docker network inspect aisdlc_backend-net --format '{{(index .IPAM.Config 0).Subnet}}')
(cd AgentConsole && docker inspect aisdlc-nginx --format '{{(index .NetworkSettings.Networks "aisdlc_backend-net").IPAddress}}')
```

```powershell
Push-Location AgentConsole; docker network inspect aisdlc_backend-net --format '{{(index .IPAM.Config 0).Subnet}}'; Pop-Location
Push-Location AgentConsole; docker inspect aisdlc-nginx --format '{{(index .NetworkSettings.Networks "aisdlc_backend-net").IPAddress}}'; Pop-Location
```

**驗證偽造無效**（預期恰好 100 個 401、第 101 個 429，與 `X-Forwarded-For` 填什麼無關；先等限流視窗回滿，約 1 分鐘）：

```bash
for i in $(seq 1 101); do curl -s -o /dev/null -w '%{http_code}\n' -H "X-Forwarded-For: 203.0.113.$i" http://localhost/api/v1/projects; done | sort | uniq -c
```

```powershell
1..101 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}`n" -H "X-Forwarded-For: 203.0.113.$_" http://localhost/api/v1/projects } | Group-Object | Select-Object Count, Name
```

**前提與限制**：只有 nginx 是**唯一入口**時成立。前面若再加負載平衡器或 CDN，它們的位址也要納入 `CONSOLE_INTERNAL_PROXIES`，否則限流會以它們的位址分桶（所有人共用一個桶）。直連 backend（沒有 nginx）時維持 `server.forward-headers-strategy=none`，此時偽造的標頭本來就不被採信（契約 §0.4 第 4 點）。

## 14. 啟用 HTTPS（預設不啟用；INF-VOL-07）

compose 本來就發布 `443` 並以唯讀掛載 `nginx_certs` 卷（`/etc/nginx/certs`）；`docker/nginx/conf.d/https.conf.example` 是對應的 443 server 區塊範例（TLS 1.2／1.3、憑證取自該卷），路由與 80 埠共用同一份 `console-locations.inc`。檔名不是 `*.conf`，所以預設**不會**被載入。

以下 PowerShell 形態的指令（含自簽憑證那一條）W7 已在 Windows 11＋Docker Desktop 的 Docker 全棧（`--profile db --profile app --profile full`）從頭到尾實跑過一遍（bash 形態是同一指令的 POSIX 寫法，沒有在 macOS／Linux 實跑）；工作目錄一律是 monorepo 根。**先把全棧起來**（〈2〉），`aisdlc_nginx_certs` 卷才由 compose 建立並帶上 compose 的標籤——沒起就跑下面的 `docker run -v aisdlc_nginx_certs:…` 也會自動建卷，但之後 compose 會警告 `volume … already exists but was not created by Docker Compose`。

1. **憑證放進 `nginx_certs` 卷**（檔名固定為 `fullchain.pem`＝含中繼憑證的完整鏈、`privkey.pem`）。卷名是 `aisdlc_nginx_certs`（compose 專案名 `aisdlc`）。

   **a. 先用自簽憑證試**：直接在卷內產生，**不需要主機有 openssl**——Windows 的 PowerShell PATH 上通常沒有它（Git for Windows 附的那支不在 PATH 內），而 `nginx`、`busybox` 映像也都沒有 openssl；這裡借用 compose 的 replica 本來就會拉的 `pgvector/pgvector:pg18`（內含 openssl）。會印一串 `.+*` 進度點，屬正常；憑證含 SAN（`localhost`、`127.0.0.1`），有效 30 天：

   ```bash
   docker run --rm -v aisdlc_nginx_certs:/certs --entrypoint openssl pgvector/pgvector:pg18 req -x509 -newkey rsa:2048 -nodes -days 30 -keyout /certs/privkey.pem -out /certs/fullchain.pem -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
   ```

   ```powershell
   docker run --rm -v aisdlc_nginx_certs:/certs --entrypoint openssl pgvector/pgvector:pg18 req -x509 -newkey rsa:2048 -nodes -days 30 -keyout /certs/privkey.pem -out /certs/fullchain.pem -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
   ```

   **b. 真憑證**（CA 簽發的檔案）：先在目前目錄備好 `certs/` 資料夾（內含上述兩個檔名），以暫時容器複製進卷：

   ```bash
   docker run --rm -v aisdlc_nginx_certs:/certs -v "$PWD/certs:/src:ro" busybox sh -c 'cp /src/fullchain.pem /src/privkey.pem /certs/ && chmod 600 /certs/privkey.pem'
   ```

   ```powershell
   docker run --rm -v aisdlc_nginx_certs:/certs -v "${PWD}\certs:/src:ro" busybox sh -c "cp /src/fullchain.pem /src/privkey.pem /certs/ && chmod 600 /certs/privkey.pem"
   ```

   檢查卷內有兩個檔案（nginx 容器內看到的是同一份，唯讀）：`docker run --rm -v aisdlc_nginx_certs:/certs:ro busybox ls -l /certs`（bash 與 PowerShell 同一條）。

2. **複製範例並改網域**：把 `docker/nginx/conf.d/https.conf.example` 複製成同目錄的 `https.conf`，把 `server_name localhost;` 改成你的網域。`https.conf` 是部署本機的檔，已列入 `AgentConsole/.gitignore`（`git add -A` 不會把它帶進去；`https.conf.example`、`default.conf` 等被追蹤的檔不受影響），但它留在磁碟上時 nginx 仍會載入它：試完要刪（見下方〈回到只有 HTTP〉）。

   ```bash
   cp AgentConsole/docker/nginx/conf.d/https.conf.example AgentConsole/docker/nginx/conf.d/https.conf
   ```

   ```powershell
   Copy-Item AgentConsole\docker\nginx\conf.d\https.conf.example AgentConsole\docker\nginx\conf.d\https.conf
   ```

3. **（選用）80→443 轉址**：編輯 `docker/nginx/conf.d/default.conf`，把 80 埠 server 內的 `include /etc/nginx/conf.d/console-locations.inc;` 換成 `include /etc/nginx/conf.d/https-redirect.inc;`。轉址檔保留 `/nginx-health` 回 200（compose 的 nginx healthcheck 打 `http://127.0.0.1/nginx-health`，不能被轉址）、其餘一律 `301` 到 `https://$host$request_uri`；公開的 HTTPS 埠不是 443 時請自行改檔內的目標網址。
4. **檢查並重啟**（`nginx -t` 不過就**不要**重啟：nginx 以壞設定重啟會起不來；所以 PowerShell 形態要自己判斷 rc，不能用 `;` 直接接 `restart`）。預期 `nginx -t` 印 `syntax is ok`／`test is successful`、rc＝0：

   ```bash
   (cd AgentConsole && docker compose exec nginx nginx -t && docker compose restart nginx)
   ```

   ```powershell
   Push-Location AgentConsole; docker compose exec nginx nginx -t; if ($LASTEXITCODE -eq 0) { docker compose restart nginx }; Pop-Location
   ```

5. **驗證**（期望值逐項實跑過；`curl.exe` 是 Windows 內建的那支，`-k` 因為是自簽憑證）：

   | 檢查 | 預期 |
   |------|------|
   | HTTPS 健康：`curl.exe -k -s -o NUL -w "%{http_code}\n" https://localhost/nginx-health` | `200` |
   | 80 埠健康（compose 的 nginx healthcheck 打這裡，不可被轉址）：`curl.exe -s -o NUL -w "%{http_code}\n" http://localhost/nginx-health` | `200` |
   | 80→443 轉址（有做步驟 3 才適用）：`curl.exe -s -o NUL -w "%{http_code} %{redirect_url}\n" http://localhost/x` | `301 https://localhost/x`（`http://localhost/api/v1/projects` 同樣 301） |
   | 路由與 HTTP 相同：對 `https://localhost` 的 `/`、`/api/health`、`/api/v1/projects`（沒帶 token）、`/actuator/health` 各打一次 | `200`、`200`、`401`、`403` |
   | 經 HTTPS 登入真實後端（見下方指令） | `200`，回應 `data` 內有 `accessToken` |
   | nginx 容器：`docker compose --profile db --profile app --profile full ps nginx` | `healthy`；重啟後立即查會是 `health: starting`（實測 1 分鐘內轉為 healthy；healthcheck 間隔 15 秒），**等它變 healthy 再判**。🔴 **要帶 `--profile`**：不帶時 `ps nginx` 回 rc＝1 與 `no such service: backend`（nginx `depends_on` 的 backend 屬 profile `app`；`exec`／`restart` 則不帶也行；以上為 Docker Compose 5.1.4 實測） |

   登入的帳密：開發預設見 `backend/README.md`〈開發預設帳號〉（正式環境必須已覆寫，〈12.1〉）。PowerShell 的 `curl.exe` 吃不好行內 JSON 的雙引號，所以用檔案帶：

   ```bash
   curl -k -s -X POST -H 'Content-Type: application/json' -d '{"username":"admin","password":"<YOUR_PASSWORD>"}' -w '\n%{http_code}\n' https://localhost/api/v1/auth/login
   ```

   ```powershell
   Set-Content -Path login.json -Value '{"username":"admin","password":"<YOUR_PASSWORD>"}' -Encoding ascii -NoNewline
   curl.exe -k -s -X POST -H "Content-Type: application/json" --data "@login.json" -w "\n%{http_code}\n" https://localhost/api/v1/auth/login
   Remove-Item login.json
   ```

   （選用）**不靠 `-k` 驗證憑證鏈與 SAN**：先 `docker cp aisdlc-nginx:/etc/nginx/certs/fullchain.pem fullchain.pem`，再 `curl.exe --cacert fullchain.pem --ssl-no-revoke https://localhost/nginx-health` 回 `200`（`--ssl-no-revoke` 只有 Windows 的 Schannel 版 curl 需要：自簽憑證沒有 CRL 可查，不加會報撤銷檢查失敗；沒給 `--cacert` 時 rc＝60、代表不受信任——對照組）。

回到只有 HTTP：刪掉 `https.conf`、把 `default.conf` 的 include 改回 `console-locations.inc`、`nginx -t` 通過後重啟 nginx（同上述步驟 4）。實測回到原狀：`https://localhost/nginx-health` 握手失敗（curl rc＝35，與啟用前相同）、`http://localhost/` 回 200、`http://localhost/x` 回 404（不再是 301）、`git status` 對 `docker/nginx/` 沒有任何殘留。注意 `https.conf` 已被忽略，忘了刪也不會出現在 `git status`：要用 `Test-Path AgentConsole\docker\nginx\conf.d\https.conf`（應為 `False`）或上述握手結果確認。

```bash
rm AgentConsole/docker/nginx/conf.d/https.conf
```

```powershell
Remove-Item AgentConsole\docker\nginx\conf.d\https.conf
```

其他注意：HSTS 在範例內是註解（瀏覽器會記住一年，確認 HTTPS 穩定再開，且 nginx 的 `add_header` 不會繼承到自己有 `add_header` 的 `/_next/static/`）；`X-Forwarded-Proto` 因 `$scheme` 自動變 `https`；憑證申請與續期（例如 Let's Encrypt）不在本專案範圍。

## 15. 日誌與追蹤碼（trace_id）

- **stdout**：`docker compose logs backend｜engine-bridge｜nginx`（`json-file` 輪替 10m×3）。backend 是 JSON 行（含 `traceId`），engine-bridge 自 W5 起每一行都是 `<UTC 時間>Z <等級> [<logger>] trace_id=<值> <訊息>`（含 uvicorn 的啟動／存取日誌；沒有請求上下文的行是 `trace_id=-`；一筆日誌恆為一行，traceback 內的換行寫成字面 `\n`）。
- **檔案日誌（`app_logs` 卷）**：backend `LOG_DIR=/app/logs` → `console.log`（JSON 行）；engine-bridge `BRIDGE_LOG_DIR=/app/logs` → `bridge.log`（同上的文字行）。兩者每日（UTC 午夜）切檔、保留 7 份；兩個容器以不同 uid 寫同一個卷，所以 Bridge 映像把 `/app/logs` 設成 `1777`，並且 backend 掛載該卷時加 `:nocopy`（為什麼：〈9〉#32——沒有它，最後 create 的 backend 會把卷根改成 `spring:spring 0755`、Bridge 寫不進去）。寫不進去不會讓服務起不來，只在 stderr 留一則警告。

  ```bash
  (cd AgentConsole && docker compose exec engine-bridge tail -n 20 /app/logs/bridge.log)
  ```

  ```powershell
  Push-Location AgentConsole; docker compose exec engine-bridge tail -n 20 /app/logs/bridge.log; Pop-Location
  ```

- **跟著一次操作查**（契約 §0.4 第 6 點、§3.1.1）：console-api 為每個請求產生 `traceId`（回應標頭 `X-Trace-Id`、錯誤封包的 `traceId`），並對 Bridge 的**每個請求**帶同名標頭；Bridge 把它原樣放進回應標頭與當次請求內每一行日誌的 `trace_id=`（缺漏或格式不合時 Bridge 自產 uuid4；run 的監督執行緒沿用啟動它的請求的值）。所以同一次使用者操作在 backend 與 Bridge 的日誌可用同一個值串起來：

  ```bash
  (cd AgentConsole && docker compose logs engine-bridge | grep 'trace_id=<值>')
  ```

  ```powershell
  Push-Location AgentConsole; docker compose logs engine-bridge | Select-String 'trace_id=<值>'; Pop-Location
  ```
