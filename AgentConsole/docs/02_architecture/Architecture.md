# AgentConsole 架構文件（Architecture）

| 項目 | 內容 |
|------|------|
| 版本 | v1.0（W1 產出；變更須經 ADR） |
| 建立日期 | 2026-10-14 |
| 作者 | Architect＋SA（W1-A） |
| 唯一真相源 | PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md`（§0 權威）、UI 設計稿 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md` |
| 姊妹文件 | [ADR-001-TechStack-Lock.md](ADR-001-TechStack-Lock.md)（決策與偏離）、[RTM.md](../06_quality/RTM.md)（需求追溯）、[Implementation_Plan.md](../04_planning/Implementation_Plan.md)（波次與閘門） |
| 讀法 | 這是後續所有開發 agent 的地圖：先讀 §3 目錄、§7 資料所有權、§10 Bridge 契約，再讀自己負責的服務章節 |

> **文件規則**：與 PRD 衝突時，PRD §0 優先；與 PRD 其餘章節的差異一律登記於 ADR-001 §4／§5，本文不重複辯護。指令一律「bash 區塊＋PowerShell 區塊」並列（見 §9）；路徑一律相對 monorepo 根或 `AgentConsole/`，不寫死任何磁碟絕對路徑。

> **〔ResearchToPRD W0 增補 2026-11-02〕** 本檔 §2.2、§3、§5.1、§5.4、§6(e)、§7.2、§8.2～§8.4、§9.4、§10.1、§10.2、§10.4、§11.1、§11.3′、§12.1、§12.2 載有研究到規格功能（無新服務、無新容器）的增補，以〔ResearchToPRD …〕標記；決策見 [ADR-003-ResearchToPRD.md](ADR-003-ResearchToPRD.md) 與 [ADR-XPLAT-017](../../../docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md)，端點契約見 [API_Contract_ResearchToPRD.md](API_Contract_ResearchToPRD.md)。

---

## 1. 系統脈絡（C4 L1）

```
                          HTTPS 80/443 (JWT)
 +--------------------+                             +----------------------------------+
 | Steersman (browser)| ------------------------>   | AISDLC Agent Console             |
 | Admin / Operator / | <------------------------   | nginx -> frontend / backend      |
 | Viewer             |         REST / SSE          +----------------------------------+
 +--------------------+                                              |
                                                                     | REST + SSE (internal)
                                                                     |
                                                                     v
                                                    +----------------------------------+
                                                    | Engine Bridge (FastAPI sidecar)  |
                                                    | /autoclaude/*        /sdd/*      |
                                                    +----------------------------------+
                                                            |                  |
                                        spawn (CLI)         |                  | read files / compile
                                                            |                  |
                                                            v                  v
                                +----------------------------+    +------------------------------+
                                | AutoClaude                 |    | AISDLC_SDD (LATEST)          |
                                | python -m autoclaude       |    | specs, FSM-STATE,            |
                                +----------------------------+    | SddToPlaybookAdapter         |
                                              |                   +------------------------------+
                                              |
              claude CLI (step executor)  +  MiniMax API (brain; outbound allowlist)

 +------------------------------------------------------------------------------------------+
 | PostgreSQL 18 (pgvector)                                                                 |
 |  schema console.*    : backend Flyway owns DDL; Bridge writes runs / steps / checkpoints |
 |  schema autoclaude.* : engine-internal DAL, optional (storage.mode = both)               |
 +------------------------------------------------------------------------------------------+
```

| 角色／系統 | 說明 | 信任邊界 |
|------------|------|----------|
| 掌舵者（瀏覽器） | 人類操作員；Admin／Operator／Viewer 三種角色 | 對外唯一入口＝nginx（HTTPS；JWT） |
| AISDLC Agent Console | 本專案（frontend＋backend）；Console 領域資料的唯一寫入者 | 與 Bridge 之間走內網 HTTP |
| Engine Bridge | 單一 FastAPI 旁車，包兩個純 CLI 引擎；零侵入（NFR-COMPAT-01） | **無認證**，只准 backend-net 內可達（§12 L-6） |
| AutoClaude | Playbook 執行引擎；僅 CLI（`python -m autoclaude <playbook.yaml> [--config] [--fresh]`） | 由 Bridge 以子程序啟動；不改一行 |
| AISDLC_SDD | 規格先行框架（LATEST 現查：`python AISDLC_SDD/scripts/sdd_version.py`）；純 CLI／Markdown／Hook | Bridge 唯讀掛載 |
| PostgreSQL 18 | 與 AutoClaude 同映像 `pgvector/pgvector:pg18`；Console 表住 `console` schema | 僅 db-net（internal）可達 |
| MiniMax API／Claude Code CLI | 引擎的「修正腦」與「步驟執行器」 | MiniMax 外呼受 allowlist 管制（NFR-SEC-04）；測試一律用 mock（ADR-001 D9） |

## 2. 容器圖（C4 L2）

### 2.1 拓撲

```
 host :80 / :443
     |
     v
 +---------+   frontend-net      +----------------+
 | nginx   |-------------------->| frontend :3000 |
 +---------+                     +----------------+
     |
     | backend-net (D14-9)
     v
 +---------------+                  +---------------------+           +------------------+          +---------------+
 | backend :8080 |----------------->| engine-bridge :8081 |           | prometheus :9090 |--------->| grafana :3001 |
 +---------------+<-----------------+---------------------+           +------------------+          +---------------+
      |                                       |
      | db-net (internal)                     | db-net                scrape: backend /actuator/prometheus
      |                                       |                               postgres-exporter x2 (:9187)
      v                                       v
 +------------------+   streaming     +--------------------+          +-------+     +---------+
 | postgres-primary |---------------->| postgres-replica   |          | redis |     | pgadmin |
 | :5432            |                 | :5432 (host :5433) |          | :6379 |     | :5050   |
 +------------------+                 +--------------------+          +-------+     +---------+
        |
        | archive_command / backup
        v
 +------------+  repo2 (S3 protocol)        +----------------------+
 | pgbackrest |---------------------------->| minio (+ minio-init) |
 +------------+                             +----------------------+




```

### 2.2 服務清單（數值取自 PRD §11.2／§11.3；「調整」欄見 ADR-001 D14）

| # | 服務 | 映像 | 容器內埠 | host 發布 | 網路 | 調整 |
|---|------|------|----------|-----------|------|------|
| 1 | nginx | `nginx:1.27-alpine` | 80、443 | `80:80`、`443:443` | frontend-net、**backend-net** | D14-9 |
| 2 | frontend | 自建 `aisdlc-frontend`（Node 22） | 3000 | 不發布（nginx 反代） | frontend-net、backend-net | — |
| 3 | backend | 自建 `aisdlc-backend`（Temurin 21） | 8080 | 不發布 | backend-net、db-net | — |
| 4 | engine-bridge | 自建 `aisdlc-engine-bridge`（FastAPI／uvicorn） | 8081 | 不發布 | backend-net、db-net | D7 |
| 5 | postgres-primary | 自建 `aisdlc-postgres-primary:pg18`（`pgvector/pgvector:pg18` ＋ pgbackrest） | 5432 | 正式模式不發布（已實測：internal 網路上發布無效）；`docker-compose.dev.yml` 發布到 `127.0.0.1:${POSTGRES_PORT:-5432}` | db-net（dev 疊加時另掛 dev-net） | D14-3 |
| 6 | postgres-replica | `pgvector/pgvector:pg18` | 5432 | 正式模式不發布；dev 疊加發布到 `127.0.0.1:${POSTGRES_REPLICA_PORT:-5433}` | db-net（dev 疊加時另掛 dev-net） | D14-6 |
| 7 | redis | `redis:7-alpine` | 6379 | 不發布 | db-net | D16（W7 D-19 改寫：只有 refresh token 撤銷名單使用；Redis 不在線降級為記憶體） |
| 8 | pgadmin | `dpage/pgadmin4:9.18.0` | 5050 | `${PGADMIN_PORT:-5050}:5050` | db-net、**backend-net** | D14-8、D14-10 |
| 9 | pgbackrest | 自建 `aisdlc-pgbackrest:pg18`（Debian＋apt，pgBackRest 2.59.3；busybox crond、mc、jq） | — | —（指標端點 `:9854` 只在容器內） | db-net | D14-2 |
| 10 | prometheus | `prom/prometheus:v3.15.0` | 9090 | `${PROMETHEUS_PORT:-9090}:9090` | db-net、backend-net | D14-8 |
| 11 | grafana | `grafana/grafana:12.4.13` | 3000 | `${GRAFANA_PORT:-3001}:3000` | backend-net | D14-8 |
| 12 | minio | `pgsty/minio:RELEASE.2026-08-04T00-00-00Z`（官方 `minio/minio` 已自 Docker Hub 下架，改用社群 fork） | 9000（S3 API，HTTPS 自簽）、9001（console） | 不發布 | db-net | D14-4（追加） |
| 13 | minio-init | `pgsty/mc:RELEASE.2026-09-16T00-00-00Z`（一次性 job） | — | — | db-net | D14-4（追加） |
| 14 | postgres-exporter-primary | `prometheuscommunity/postgres-exporter:v0.20.1` | 9187 | 不發布 | db-net | D14-5（追加） |
| 15 | postgres-exporter-replica | 同上 | 9187 | 不發布 | db-net | D14-5（追加） |
| 16 | minio-certs | `aisdlc-pgbackrest:pg18`（一次性 job；產生 MinIO 自簽憑證，pgBackRest 的 S3 連線一律 HTTPS） | — | — | db-net | D14-4（追加） |

| # | 依賴（`depends_on` 條件） | 資源限制 | healthcheck |
|---|---------------------------|----------|-------------|
| 1 | frontend、backend（service_healthy） | 0.5 CPU／256M | PRD 未定義 |
| 2 | PRD §11.2 列 backend；§11.3 compose 無 `depends_on` | 1.0／512M | `curl -f http://localhost:3000/api/health`；30s／10s／3 次；start 40s |
| 3 | postgres-primary、redis、engine-bridge（皆 healthy） | 2.0／1G | `curl -f http://localhost:8080/actuator/health`；30s／10s／5 次；start 60s |
| 4 | postgres-primary（healthy） | 1.0／1G | Python 標準庫探 `http://127.0.0.1:8081/health/deep`（映像沒有 curl；非 200 即非零離開碼；W5 C-2 起，原稿為 `curl -f http://localhost:8081/health`）；30s／10s／5 次；start 30s |
| 5 | — | 2.0／2G | `pg_isready -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DB`（走 TCP，初始化階段的暫時伺服器只聽 socket）；10s／5s／5 次；start 30s |
| 6 | postgres-primary（healthy） | 1.0／1G | `pg_isready -h 127.0.0.1 -U $POSTGRES_USER`；10s／5s／5 次；start 30s |
| 7 | — | 0.5／256M | `redis-cli ping`；10s／5s／5 次 |
| 8 | postgres-primary（healthy） | 0.5／256M | `wget /misc/ping`；30s／10s／5 次；start 60s |
| 9 | postgres-primary（healthy）、minio-init（結束碼 0） | 0.5／512M | crond 活著＋stanza 存在＋指標端點；30s／10s／5 次；start 90s |
| 10 | backend（healthy；`required: false`，只起 db profile 時略過） | 0.5／512M | `wget /-/healthy`；15s／5s／5 次；start 15s |
| 11 | prometheus（healthy） | 0.5／256M | `wget /api/health`；15s／5s／5 次；start 30s |
| 12 | minio-certs（結束碼 0） | 0.5／512M | `curl -k /minio/health/live`；10s／5s／5 次；start 10s |
| 13 | minio（healthy） | 0.25／128M | 一次性 job（結束碼 0） |
| 14 | postgres-primary（healthy） | 0.25／128M | `wget :9187/`；15s／5s／5 次；start 10s |
| 15 | postgres-replica（healthy） | 0.25／128M | `wget :9187/`；15s／5s／5 次；start 10s |
| 16 | — | 0.25／128M | 一次性 job（結束碼 0） |

> 以上為 W2-B 於 2026-10-15 實跑後的回填值（服務 16 個＝PRD 11 個＋minio、minio-init、minio-certs、postgres-exporter×2）；**最終服務、埠、卷以 `docker compose config` 輸出為準**，逐項差異與實測依據見 `docker/README.md`〈9 與 PRD 的差異〉。frontend／backend 的 healthcheck 以 `wget` 失敗再試 `curl`（alpine 映像沒有 curl）。

> **〔ResearchToPRD W0 增補 2026-11-02〕** 研究到規格功能**不新增服務與容器**；各容器的變動如下（決策 ADR-003、ADR-XPLAT-017）：
>
> | 容器 | 變動 |
> |------|------|
> | frontend | 新增領域元件群 `components/domain/research/`、兩條路由 `/research`、`/research/[researchId]`；新相依 `mermaid`、`diff`（ADR-003 D9） |
> | backend（console-api） | 新增 `ResearchController`（`adapter.in.web`）、`StreamController` 加一條研究串流、JDBC 讀配接器 `adapter.out.persistence.research.*`、`BridgeHttpAdapter` 加 `/research/*` 呼叫、純函式 `domain.service.ResearchFlowPolicy`、`SecurityConfig` 的 ADMIN 規則；Flyway V16～V19 |
> | engine-bridge | 新增套件 `app/research/`（§3）、`routers/research.py`；`settings.py` 新環境變數（§9.4）；`sdd_cli.py` 研究面動詞（ADR-XPLAT-017）；`GET /health/deep` 加資訊欄 `research`（含 `mode`：`local`／`mock-only`；不影響 503 判定，同 `sdd` 先例，§10.1） |
> | AutoClaude／AISDLC_SDD | **AutoClaude 零改動**；AISDLC_SDD 由獨立鍵 `sdd-research-to-prd` 在框架側加方法層（ADR-XPLAT-017 §D7），不在 AgentConsole 鍵的權限內（`AgentConsole/CLAUDE.md` 鐵律 7） |
> | 外部 | 新增 Bridge 出站目的地（`BRIDGE_RESEARCH_FETCH_ALLOWLIST`，初始＝arXiv、Semantic Scholar、GitHub API、Stack Exchange API；產業網域由 ADMIN 加入） |
> | Docker 全棧 | Bridge 映像**不裝** `claude`／`gh`；只跑 mock claude（`aisdlc-mock-claude`）的 E2E，真研究限本機模式（ADR-003 D10） |
>
> 元件關係（文字 C4）：
> ```
> 瀏覽器 ──/api/v1/research/** (JWT)──▶ console-api ──X-Bridge-Token(BRIDGE_RESEARCH_WRITE_TOKEN)──▶ engine-bridge /research/*
>    ▲  SSE /api/v1/stream/research/{id}                │ JDBC 唯讀 console.research_*            │ psycopg 寫入 console.research_*（fail-loud＋outbox）
>    └────────────────────────────────────────────────◀─┘                                         ├─ httpx（獨立 allowlist）→ arXiv／S2／GitHub／SE
>                                                                                                 ├─ RunManager → `python -m autoclaude …`（stage run；headless claude）
>                                                                                                 ├─ FSM CLI 子行程（research 面動詞）→ FSM-STATE-*.yaml（工作區／目標根）
>                                                                                                 └─ git／gh 子行程（route 面；僅本機模式）
> ```

### 2.3 埠號總表

| 埠 | 用途 | 本機開發 | Docker 全棧 |
|----|------|----------|-------------|
| 3000 | frontend（Next.js） | host 直接聽 | 容器內；經 nginx 反代 |
| 8080 | backend（Spring Boot） | host 直接聽 | 容器內 |
| 8081 | engine-bridge | host 直接聽（建議綁 127.0.0.1） | 容器內 |
| 80／443 | nginx | — | 唯一對外入口 |
| 5432 | postgres-primary | dev compose 發布到 host（`127.0.0.1`） | 不發布（D14-10 已實測：internal 網路上發布無效） |
| 5433 | postgres-replica（容器內 5432） | dev 疊加發布到 host（`127.0.0.1`） | 不發布（同上） |
| 6379 | redis | dev compose 發布到 host（`127.0.0.1`，無密碼） | 容器內 |
| 5050 | pgadmin | — | 發布 |
| 9090 | prometheus | — | 發布 |
| 3001 | grafana（容器內 3000） | — | 發布 |
| 9187 | postgres-exporter ×2 | — | 容器內 |
| 9000／9001 | MinIO S3 API（HTTPS 自簽）／console | — | 容器內，皆不發布 |
| 9854 | pgbackrest 備份指標端點 | — | 容器內（Prometheus 抓取） |
| 9100 | `mock_brain_server.py`（測試用，`--port 9100`） | 測試時本機啟動 | — |

### 2.4 網路

| 網路 | 驅動 | internal | 成員 | 設計意圖 |
|------|------|----------|------|----------|
| frontend-net | bridge | 否 | nginx、frontend | 對外入口與前端 |
| backend-net | bridge | 否 | nginx（D14-9）、frontend、backend、engine-bridge、pgadmin（D14-10）、prometheus、grafana | 應用層；唯一有對外出口（NAT）的網路，Bridge 的外呼（MiniMax）與 nginx 的入站都經此 |
| db-net | bridge | **是** | backend、engine-bridge、postgres-primary／replica、redis、pgbackrest、pgadmin、prometheus、exporters、minio | 資料庫層不對外暴露 |

> **兩處 PRD 缺口（ADR-001 G-01／G-02）**：① PRD 讓 nginx 只掛 frontend-net，但 `backend` 不在該網路，nginx 解析不到 `backend:8080`——已調整為 nginx 同掛 backend-net；② `db-net` 為 `internal: true`，只掛在它上面的容器其 `ports:` 對 host 不可達（W2-B 已實測，見 ADR-001 §6 E-5），因此 pgadmin 另掛 backend-net，PG 在全棧模式不對 host 發布，本機開發改由 `docker-compose.dev.yml` 發布。

### 2.5 Volumes（PRD §11.1／§11.3）

| 卷 | 掛載者（容器內路徑） | 用途 |
|----|----------------------|------|
| pg_data | postgres-primary（`/var/lib/postgresql/data`）；pgbackrest 本機模式共用 | 主節點資料 |
| pg_replica_data | postgres-replica | 副本資料 |
| pg_wal_archive | postgres-primary、pgbackrest；postgres-replica 唯讀（`/var/lib/postgresql/wal_archive`） | 本地 WAL 複本（gzip）；replica 的 restore_command 讀取 |
| pg_backup | postgres-primary（archive-push 用）、pgbackrest（`/var/lib/pgbackrest`） | pgBackRest repo1（另放 `.last_backup_status`） |
| redis_data | redis（`/data`） | Redis 持久化 |
| app_logs | backend、engine-bridge（`/app/logs`） | 應用日誌 |
| nginx_certs | nginx（`/etc/nginx/certs`，唯讀） | SSL 憑證 |
| engine_workspace | engine-bridge（`/workspace`） | Bridge spawn 子程序的執行工作目錄 |
| pg_socket | postgres-primary、pgbackrest（`/var/run/postgresql`） | primary 的 unix socket，pgBackRest 本機模式共用（W2-B 追加） |
| minio_data | minio（`/data`） | 離站備份物件（W2-B 追加） |
| minio_certs | minio-certs 寫入、minio 唯讀（`/certs`） | MinIO 自簽 TLS 憑證（W2-B 追加） |
| prometheus_data | prometheus（`/prometheus`） | Prometheus 時序資料（W7 D-14 追加；PRD §11.3 未列，登記於 ADR-001 §4）：可用性 SLO 的 30 天歷史要跨 `down`／容器重建存活；保留期由 15d 改 35d（`--storage.tsdb.retention.time=35d`，大於 30d 才使 `ratio_30d` 有完整 30 天樣本）；`down -v` 才會清掉它 |
| backup_out | pgbackrest 寫（`/backup-out`，不帶 ro）、backend 唯讀（`/backup-out:ro,nocopy`） | 備份控制面輸出卷（**〔SysAdminBackup S1 已落地 2026-10-28〕**）：sidecar 寫 `export/`（heartbeat、schedule、info、logical、jobs）與 `results/`，backend 的備份頁只依它（`CONSOLE_BACKUP_OUT_DIR`）；`docker/README.md`〈4.6 控制面〉 |
| backup_req | backend 寫（`/backup-req`）、pgbackrest 唯讀（`/backup-req:ro,nocopy`） | 備份控制面請求卷（S1 已掛）：手動觸發請求檔由 console-api 寫、sidecar runner 階段二才撿取（`CONSOLE_BACKUP_REQ_DIR`） |

> 清單以 `docker compose config --volumes` 輸出為準（共 14 個；SysAdminBackup S1 自 12 加 `backup_out`、`backup_req`）。

## 3. 目錄地圖

```
AgentConsole/
├── CLAUDE.md / README.md / docker-compose.yml / docker-compose.dev.yml / .env.example
├── docs/{02_architecture,04_planning,06_quality}/
├── frontend/            Next.js 16（app/ components/{layout,ui,charts,markdown,domain} lib/ styles/ tests/ Dockerfile）
├── backend/             Spring Boot 4.1 / Java 21（src/main/java/com/aisdlc/console/{adapter,application,domain,infrastructure}；src/main/resources/db/migration/V1__init.sql；Dockerfile）
├── engine-bridge/       FastAPI（app/{main.py,settings.py,runner.py,events.py,locks.py,db.py,security.py,routers/{autoclaude.py,sdd.py,research.py},research/} tests/ pyproject.toml Dockerfile .venv/）
└── docker/{nginx,postgres/{primary,replica},pgbackrest,redis,prometheus,grafana}/
```

| 路徑 | 放什麼（一句話） | 負責 |
|------|------------------|------|
| `CLAUDE.md` | 本子專案的 agent 規範：指令、閘門、鐵律、跨平台鐵律（≤200 行） | Architect |
| `README.md` | 快速開始（≤80 行） | Architect |
| `docker-compose.yml` | Docker 全棧（15 個服務、三個網路、卷、profiles） | W2-B |
| `docker-compose.dev.yml` | 本機開發用：只起 postgres-primary（5432）與選配 redis | W2-B |
| `.env.example` | 環境變數範本，只放 `<YOUR_...>` 佔位符 | W2-B |
| `docs/02_architecture/` | Architecture.md、ADR-001、ADR-002（前端設計系統，W3 撰寫） | Architect、W3 |
| `docs/04_planning/` | Implementation_Plan.md（波次、閘門、進度帳） | Architect、主控 |
| `docs/06_quality/` | RTM.md（需求追溯矩陣）與後續 QA 報告 | Architect、QA |
| `frontend/app/` | App Router 路由與 `layout.tsx`（只組裝四區塊） | W3 |
| `frontend/components/layout/` | 四區塊：`TopRegion`、`ToolsRegion`、`ContentRegion`、`BottomRegion` | W3 |
| `frontend/components/ui/` | shadcn/ui 元件（視覺依 token 覆寫） | W3 |
| `frontend/components/charts/` | 圖表封裝（Tremor Raw 或 shadcn chart，ADR-001 D3） | W4 |
| `frontend/components/markdown/` | Markdown 編輯器與渲染器（PRD §5.1.4 八項功能） | W3 |
| `frontend/components/domain/` | 領域元件（ProjectCard、StatusDot、SignoffBanner、DagView…） | W3／W4 |
| `frontend/lib/` | `api/`（client、endpoints、`schema.d.ts`）、`auth/`、`domain/status.ts`、`sse/`（fetch 串流客戶端）、`nav/`（導覽輔助；**〔P1b 已落地 2026-10-22〕`nav/registry.ts`＝導覽登記表，Tools 區入口的單一來源，§5.2、§5.4**） | W3；登記表 P1b |
| `frontend/lib/help/` | **〔PageHelp 已落地 2026-10-28〕**每頁說明的內容層（PRD `docs/01_requirements/Console_PageHelp_PRD.md`；只有資料與純函式，不 import 元件）：`registry.ts`＝**說明登記表**（`HELP_PAGES`：路由樣板→說明項的單一來源；`PENDING_HELP_PAGES`：分輪過渡清單，收輪後為空）、`states.ts`（全站狀態釋義表，一份；頁檔只引用表 id）、`common.ts`（全站共通段）、`lint.ts`（繁中／英文白名單／數字與句長判準）、`types.ts`、每條路由一個頁檔 `<page>.ts`；鎖＝`registry.test.ts`（路由雙向鎖、`PENDING_CEILING` 棘輪）、`content.test.ts`、`lint.test.ts` | PageHelp 輪 1a～3 |
| `frontend/components/domain/help/` | **〔PageHelp 已落地 2026-10-28〕**「本頁說明」鈕與對話框：`PageHelpButton.tsx`（全站一顆、`data-testid="page-help-open"`、`key={pathname}` 隨路由重掛載；路由無說明項或仍在 `PENDING_HELP_PAGES` 者不渲染）、`PageHelpDialog.tsx`（建於共用 `DialogContent`，四段：這頁做什麼、怎麼用、欄位說明、狀態說明，其後「全站共通」收合段；議題中心頁的狀態說明改向 `GET /api/v1/issues?limit=1` 取 API 詞表）、`IssuesLegendGroups.tsx`、`stateSources.ts`（狀態名稱來源＝既有常數表，不寫死狀態詞）；由 `TopRegion.tsx` 以 `next/dynamic` 接入（§5.2） | PageHelp 輪 1a～1b |
| `frontend/styles/` | `tokens.css`（設計稿 token 逐字搬入）與全域樣式 | W3 |
| `frontend/tests/` | vitest 單元測試與 `e2e/`（Playwright，含 `__screenshots__/`） | W3／W4 |
| `backend/src/main/java/com/aisdlc/console/` | Clean Architecture 四層（§4） | W2／W3 |
| `backend/src/main/resources/db/migration/` | Flyway 遷移 V1～V5（ADR-001 D5） | W2／W3 |
| `backend/src/test/` | 單元、ArchUnit、Testcontainers 整合測試 | W2／W3 |
| `engine-bridge/app/` | `main.py`、`settings.py`、`runner.py`、`events.py`、`locks.py`、`db.py`、`security.py`、`models.py`、`routers/{autoclaude,sdd}.py`（**〔P1b 已落地 2026-10-22〕另有 `routers/si.py`、`si_cli.py`；〔P2b 已落地 2026-10-25〕另有 `si_audit.py`，§10.3**） | W1-B；SI P1b／P2b |
| `engine-bridge/app/research/` | **〔ResearchToPRD W0 增補〕**研究套件（根層落點規則不適用：子專案內模組，`docs/02_architecture/Root_Layout_and_Module_Placement.md` §2 末段）：`__init__.py`（一句用途）、`settings.py`（研究面環境變數解析）、`db.py`（`ResearchDb`：fail-loud 交易、事件配號、冪等 upsert）、`outbox.py`（寫檔→記錄→DB→標 done；啟動重放）、`layout.py`（`<slug>/{00_research,01_specs,02_governance,03_execution}` 與路徑淨化）、`fsm_ops.py`（研究面 FSM 驅動，包 `sdd_cli.run_verb`）、`fetch/{allowlist,http,arxiv,semantic_scholar,github,stackexchange}.py`、`compile/{personas,playbooks,prompts}.py`（agent YAML→`.prompts/*.md`、stage playbook、`config_overrides`）、`gates/{schemas,evidence,prd_schema,review_card,aggregate}.py`＋`gate_cli.py`（evaluator 載具，純標準庫）、`orchestrator.py`（確定性狀態機：stage→驗證→入庫→gate→下一步）、`export.py`（`state.json`／`review_card.json`／`evidence_matrix.md` 等渲染）；P1：`route.py`、`scaffold.py`、`gitops.py`（git／gh 白名單呼叫）、`scr.py`、`scaffold_templates/<name>/`；P2：`release.py` | ResearchToPRD P0～P2 |
| `engine-bridge/app/routers/research.py` | `/research/*` 薄殼（驗權杖、轉 `research` 套件） | ResearchToPRD P0～P2 |
| `frontend/app/research/` | `page.tsx`（研究專案清單＋新建）、`[researchId]/page.tsx`（研究工作區；`?step=`）；只殼 | ResearchToPRD P0 |
| `frontend/components/domain/research/` | 研究領域元件群（§5.4 填寫表）；`lib/domain/research.ts`（純函式）、`lib/help/{research,research-workspace}.ts` | ResearchToPRD P0～P2 |
| `engine-bridge/tests/` | pytest（生命週期、pause、stop、restore、409、422、SSE 重播、孤兒回收、decompose、sdd） | W1-B |
| `engine-bridge/.venv/` | **已廢止**：Bridge 改裝進根層 `.venv`（ADR-001 D6 補記；pre-commit stray_venv 閘禁止其他 venv） | — |
| `docker/nginx/` | `nginx.conf`、`conf.d/default.conf`（含 SSE 設定） | W2-B |
| `docker/postgres/{primary,replica}/` | `postgresql.conf`、`pg_hba.conf`、`init/`、replica entrypoint、primary 的自建 Dockerfile | W2-B |
| `docker/pgbackrest/` | Dockerfile、`pgbackrest.conf`、`crontab`、`scripts/`（備份、驗證、還原等，僅容器內執行） | W2-B |
| `docker/redis/`、`docker/prometheus/`、`docker/grafana/` | 各服務設定、抓取目標、provisioning 與儀表板 JSON | W2-B |
| `docker/pgadmin/` | `servers.json`（補充子目錄） | W2-B |

## 4. 後端 Clean Architecture 分層

### 4.1 套件樹（PRD §4.1；標「補」者為本文補充）

```
src/main/java/com/aisdlc/console/
├── adapter/
│   ├── in/
│   │   ├── web/        ProjectController GoalController TaskController ImportController
│   │   │               ExecutionController MonitorController SystemConfigController
│   │   │               AuthController（補） dto/（Request／Response record） GlobalExceptionHandler
│   │   └── sse/        ExecutionStreamController
│   └── out/
│       ├── persistence/  *RepositoryAdapter（實作 application.port.out.*Repository；Entity↔Domain 轉換）
│       ├── agent/        EngineBridgeClient（實作 AgentBridge；RestClient＋SSE 讀取；snake_case↔camelCase 轉換）
│       └── messaging/    SpringEventPublisher（Domain Event 橋接）
├── application/
│   ├── port/in/   ManageProjectUseCase ManageGoalUseCase ManageTaskUseCase ParseBrdPrdUseCase
│   │              ExecuteProjectUseCase MonitorProjectUseCase ManageSettingsUseCase（補） AuthUseCase（補）
│   ├── port/out/  ProjectRepository GoalRepository TaskRepository ExecutionRepository AgentBridge
│   │              ImportRepository（補） SettingsRepository（補） ReviewRepository（補） AlertRepository（補）
│   └── service/   各 UseCase 實作（@Service／@Transactional）
├── domain/
│   ├── model/{project,goal,task,execution,config}/   Aggregate／Entity／Value Object（純 Java）
│   ├── event/     Domain Events
│   └── service/   StateMachines（附錄 B.1～B.3）、DagService（Kahn）、SignoffPolicy、ReviewGatePolicy、
│                  TokenBudgetPolicy、AlertRules、PlaybookBuilder（任務物化，產出 PlaybookSpec 值物件）
└── infrastructure/
    ├── config/        Spring 配置（Bean 裝配、Jackson、CORS、OpenAPI）
    ├── security/      JWT、RBAC、RateLimit、Audit
    └── persistence/   JPA Entity＋Spring Data Repository（與 domain model 分離）
```

#### 4.1.1 與 PRD §4.1 目錄樹的差異（W7 補；完整性審查 L-04）

上面的樹是派工時的設計（W1），**實際落地的套件（`backend/src/main/java/com/aisdlc/console/`，W7-SA 於 2026-10-16 現查）與它有下列差異**；樹本身不改（保留原稿供追溯），以本段為準：

| 設計（PRD §4.1／本節樹） | 實際 | 說明 |
|---------------------------|------|------|
| `adapter/in/sse/ExecutionStreamController` | **沒有 `adapter/in/sse`**；SSE 端點在 `adapter/in/web/StreamController` | SSE 只有兩條端點，與其他 controller 同在 `adapter.in.web`；串流的事件框架與背壓在 `application/service`（`StreamService`、`StreamConnection`、`StreamFrames`），不在 adapter |
| `adapter/out/agent/EngineBridgeClient` | `adapter/out/bridge/`（`BridgeHttpAdapter`、`BridgeEndpoints`、`RequestFactoryProvider`…） | 名稱改為 `bridge`；實作 `AgentBridge`（§4.3） |
| `adapter/out/messaging/SpringEventPublisher`、`domain/event/` | **兩者都沒有** | 沒有 Domain Event 機制：Bridge 事件由 `application/service` 的 `RunConsumers`（每個活躍 run 一條虛擬執行緒）→ `RunEventProcessor` 直接更新讀模型、再經 `RunEventHub` 扇出給 SSE 訂閱者（§7.3、§6(c)） |
| （未列） | `adapter/out/{document,http,llm}` | 文件文字擷取（PDFBox／POI）、SSRF 釘 IP 的外呼 HTTP（`PinnedOutboundHttp`）、OpenAI 相容 chat completions 客戶端（匯入路徑 B） |
| `domain/model/{project,goal,task,execution,config}` | 另有 `domain/model/{auth,imports,monitor}`、`domain/exception` | 認證角色、匯入記錄、監控告警 |
| `infrastructure/{config,security,persistence}` | 另有 `infrastructure/logging`；`persistence/` 下分 `entity`、`repository` | 日誌（traceId、JSON 行檔案日誌） |

**Clean Architecture 分層由 ArchUnit 機械強制**：`backend/src/test/java/com/aisdlc/console/architecture/ArchitectureRulesTest.java` 有**八條** `@ArchTest`——§4.2 的 A1～A6（domain 純 Java、application 只依賴 domain、入站 adapter 不碰出站與 infrastructure、出站 adapter 不依賴入站、沒有東西依賴 infrastructure、頂層套件無循環）＋「JPA 實體只放在 `infrastructure.persistence`」＋「controller 只放在 `adapter.in.web`」。RTM 目前沒有任何一列引用這組規則（完整性審查 L-04，QA 合併時補一列）。

### 4.2 依賴方向規則（ArchUnit 可機械強制）

| 規則 | 內容 |
|------|------|
| A1 | `domain..` 不得依賴 `application..`、`adapter..`、`infrastructure..`、`org.springframework..`、`jakarta.persistence..`（純 Java；W2-A 任務書已要求至少落此條） |
| A2 | `application..` 只依賴 `domain..` 與自身；不得依賴 `adapter..`、`infrastructure..`（infrastructure 只經 port 反向注入） |
| A3 | `adapter.in..` 只依賴 `application.port.in..`、`domain..` 與自身 DTO；不得依賴 `adapter.out..`、`infrastructure.persistence..` |
| A4 | `adapter.out..` 實作 `application.port.out..`，可依賴 `infrastructure.persistence..`；不得依賴 `adapter.in..` |
| A5 | `infrastructure..` 不得被 `domain..`、`application..` 引用；Bean 裝配只發生在 `infrastructure.config` |
| A6 | 各頂層套件之間無循環依賴 |

依賴方向：`adapter → application → domain`；`infrastructure` 只透過 `application.port.out` 由 adapter 實作後注入。A2～A6 由 W3 後端補齊測試。

### 4.3 `AgentBridge` 埠（反腐層）

- 方法對映 §10 契約：`health`、`startRun`、`pause`、`resume`、`stop`、`getRun`、`streamEvents(runId, afterSeq)`、`replayEvents(runId, afterSeq, limit)`、`restore`（`listCheckpoints` 已於 W7 依完整性審查 I-07 刪除：斷點清單讀 DB）、`decompose`、`approveDraft`、`sddVersion`、`sddFsmList`（W7 D-16：FSM 專案清單）、`sddFsm`、`sddCompile`。
- `EngineBridgeClient` 負責：snake_case（Bridge）↔ camelCase（Console）轉換；逾時（連線 3 秒、一般請求 30 秒、SSE 不設讀取逾時）；GET 可重試 2 次、**POST 一律不重試**（避免重複 spawn）；Bridge 的 409／422 原樣轉成領域例外（見 §11.1 狀態碼語意）。
- 測試替身：W3 後端以 MockWebServer／WireMock 模擬 Bridge 契約；真 Bridge 於 W4 E2E 才接。

## 5. 前端結構

### 5.1 App Router 路由樹（PRD §4.2；`login` 為補）

```
app/
├── layout.tsx                      # Root：只組裝 Top／Tools／Content／Bottom 四區塊
├── page.tsx                        # Dashboard（UI-SCR-01）
├── login/page.tsx                  # 登入（補；不在設計稿，風格依 token）
├── projects/
│   ├── page.tsx                    # 專案列表（UI-SCR-02）
│   ├── new/page.tsx                # 新建專案（深連結頁；與 Dialog 共用 EntityForm）
│   └── [projectId]/
│       ├── page.tsx                # 專案詳情（UI-SCR-03）
│       ├── edit/page.tsx           # 編輯專案
│       ├── goals/
│       │   ├── page.tsx            # 目標列表
│       │   ├── new/page.tsx        # 新建目標
│       │   └── [goalId]/
│       │       ├── page.tsx        # 目標詳情（UI-SCR-04）
│       │       ├── edit/page.tsx   # 編輯目標
│       │       └── tasks/
│       │           ├── page.tsx    # 任務列表
│       │           ├── new/page.tsx
│       │           └── [taskId]/
│       │               ├── page.tsx        # 任務詳情（UI-SCR-05）
│       │               └── edit/page.tsx
│       ├── execute/page.tsx        # 專案執行控制台（UI-SCR-07）
│       └── monitor/page.tsx        # 專案監控儀表板（UI-SCR-08）
├── execute/page.tsx                # 執行中心無專案入口頁（2026-11-01；Console PRD §0.8；只殼，組 components/domain/entry/CenterEntryView kind="execute"）
├── monitor/page.tsx                # 監控中心無專案入口頁（同上，kind="monitor"）
├── import/page.tsx                 # BRD/PRD 匯入解析（UI-SCR-06）
├── settings/page.tsx               # 系統參數設定（UI-SCR-09）
├── self-improving/page.tsx         # 自我進化：SelfImproving 帳本／提案／事件鏡像（〔P1b 已落地 2026-10-22〕；SelfImproving PRD §9.1 C18、C20；只殼，見 §5.4）
├── issues/page.tsx                 # 議題中心：三類帳本的中文議題清單、順位與決定（〔IssueCenter 已落地 2026-10-27〕；左列第八項；本行 2026-10-31 補入，OBS-SI-321 文件漂移）
├── sysadmin/
│   ├── page.tsx                    # 系統管理入口（〔SysAdminBackup F1 已落地 2026-10-28〕；只殼；左列第九項「系統管理」Database 圖示、底部 Tab 不顯示；order 原 65 介於系統設定與自我進化之間，〔導覽整併 2026-11-01〕改 75 介於自我進化與系統設定（80）之間）
│   └── backup/page.tsx             # 資料庫備份：狀態卡、備份清單、排程與保留、控制面健康與資料新鮮度、還原與涵蓋範圍說明（唯讀；階段二加手動觸發與工作紀錄）
├── research/                       # 研發工作流（〔ResearchToPRD P0〕；側欄第十項「研發工作流」，order 35、mobile:false；D-13；只殼，見 §5.4）
│   ├── page.tsx                    # 研究專案清單＋新建（只殼；組 ResearchListView）
│   └── [researchId]/page.tsx       # 研究工作區：步驟列＋面板；?step=topic|studio|route|build|deliver（只殼；組 ResearchWorkspaceView）
└── api/health/route.ts             # 前端健康檢查（API-HLT-03）；PRD §4.2 的 BFF 層不實作
```

- 路由採 PRD §4.2 的巢狀形態；設計稿 README 〈實作建議〉 的扁平路由建議（`/goals/[id]`）不採用（W3 任務書已拍板）。
- 設計稿以 Dialog 做建立／編輯；PRD 的 `new`／`edit` 路由保留為可深連結的整頁表單，與 Dialog 共用同一個 `EntityForm` 元件。

### 5.2 四區塊共用版面（UI-LAY-01～05）

```
+--------------------------------------------------------------------------+
| TopRegion     Topbar (announcement bar, 34px) + Masthead (logo, search,  |
|               bell, signoff-queue button)                                |
+---------------------+----------------------------------------------------+
| ToolsRegion         | ContentRegion                                      |
| 240px: nav registry | route content container: scroll, max-width 1440    |
| + my-projects rail  |                                                    |
+---------------------+----------------------------------------------------+
| BottomRegion  Engine Bridge status dot, version, Toast host              |
+--------------------------------------------------------------------------+
```

| 區塊 | 唯一元件檔 | 對應設計稿 | 內容 |
|------|-----------|------------|------|
| Top | `frontend/components/layout/TopRegion.tsx` | Topbar＋Masthead | 公告列（說明文件、下載 CLI、GitHub、Bridge 狀態、通知、幫助、語言、使用者徽章）；logo；搜尋列與 recent chips；通知鈴；signoff 佇列鈕（draftCount badge）；**本頁說明鈕**（**〔PageHelp 已落地 2026-10-28〕**右側群組末端、`showTools` 分支內，`components/domain/help/PageHelpButton.tsx` 以 `next/dynamic` 載入，說明本體不進首屏；顯示與內容由 `frontend/lib/help/registry.ts` 的說明登記表決定——路由無說明項或仍在 `PENDING_HELP_PAGES` 者不渲染；§5.4） |
| Tools | `frontend/components/layout/ToolsRegion.tsx` | Sidebar | 導航項由 `frontend/lib/nav/registry.ts` 的**登記表**決定（P1b 落地後為七項：儀表板、專案管理、BRD/PRD 匯入、執行、監控、系統設定、自我進化〔訂正（2026-10-31，OBS-SI-321 根因修法）：現為九項，加議題中心〔2026-10-27〕與系統管理〔2026-10-28〕；項數改由 `registry.ts` 推導，`registry.test.ts`／`issues-nav.test.ts`／`sysadmin-nav.test.ts`／`ToolsRegion.test.tsx` 不再釘「恰 N 項」，新增入口只改登記表一列〕〔訂正（導覽整併 2026-11-01，Console PRD §0.7）：登記表仍九列，`import` 列 `enabled: false` 不渲染 ⇒ 側欄顯示八項，序為儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定；`/import` 由專案管理頁按鈕「BRD/PRD 匯入」進入〕；**〔P1b 已落地 2026-10-22〕**——`ToolsRegion.tsx` 只消費登記表，由 `registry.test.ts` 的 `AT_932_6_4` 讀檔斷言釘住）；「我的專案」rail（狀態點＋專案名）〔訂正（SelfImproving PRD T1 修訂 v0.10，⚖14；T1：sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13）：原文「導航六項（儀表板、專案管理、BRD/PRD 匯入、執行、監控、系統設定）」；導覽項改由登記表決定，新增入口只加登記表一列，見硬規則 2、5 與 §5.4〕 |
| Content | `frontend/components/layout/ContentRegion.tsx` | Main | 路由內容容器；`children` 由 `app/layout.tsx` 傳入 |
| Bottom | `frontend/components/layout/BottomRegion.tsx` | （設計稿無；依掌舵者四區塊要求新增） | Engine Bridge 連線狀態點、版本號、Toast 宿主；不得放任何新功能 |

**硬規則**：
1. `app/layout.tsx` 是唯一組裝處；任何 `app/**/page.tsx`、巢狀 `layout.tsx` 不得 import 這四個元件，也不得自帶其內容。
2. **三個共用區塊（Top／Tools／Bottom）各只有一個元件檔，改一處全站生效**；Content 是路由容器，不是第四份導覽。**Tools 區的導覽項目另有單一來源——`frontend/lib/nav/registry.ts` 的 `NAV_REGISTRY`**：新增入口只加登記表一列、不改 `ToolsRegion.tsx`（第 5 點、§5.4）〔訂正（SelfImproving PRD T1 修訂 v0.10，⚖14）：原文僅「三個共用區塊…改一處全站生效；Content 是路由容器，不是第四份導覽」；其「改一處」對新增導覽項原意指改 `ToolsRegion.tsx` 的 `NAV` 常數，現改為改登記表〕。
3. 響應式（PRD §8.3）：≥1280 完整側欄；768～1279 側欄收合為圖示；<768 以底部 Tab 導航取代側欄——三者都在 `ToolsRegion.tsx` 內以響應式切換，不另開元件檔。
4. 機械檢查（期望輸出為空；有任何一行輸出＝有頁面違規組裝了共用區塊）：

```bash
grep -rnE "TopRegion|ToolsRegion|BottomRegion" AgentConsole/frontend/app --include='*.tsx' | grep -v 'app/layout.tsx'
```

```powershell
Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
```

5. **導覽項目的單一來源＝登記表**（SelfImproving PRD ADR-SI-13；T1：sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d` line 13）：新導覽項只准加 `frontend/lib/nav/registry.ts` 的 `NAV_REGISTRY` 一列；`ToolsRegion.tsx` 不得再出現硬編的 NAV 清單，也不得出現以路徑字串分支決定 active／href 的邏輯（那些都搬進各列的 `match`／`href`）。機械檢查（期望無輸出）：**〔P1b 已落地 2026-10-22〕**——`ToolsRegion.tsx` 不再持有 `const NAV`，此檢查為空，並由 `registry.test.ts` 的讀檔斷言（`AT_932_6_4`）釘住（SelfImproving PRD §9.1 C20）：

```bash
grep -n 'const NAV' AgentConsole/frontend/components/layout/ToolsRegion.tsx
```

```powershell
Select-String -Path AgentConsole\frontend\components\layout\ToolsRegion.tsx -Pattern 'const NAV'
```

### 5.3 前端目錄與慣例

| 位置 | 慣例 |
|------|------|
| `lib/api/client.ts` | 單一 fetch 包裝：自動帶 Bearer；401 時以 refresh token 換新、失敗跳登入；解 PRD §7.2 封包；錯誤訊息帶 `traceId` |
| `lib/api/schema.d.ts` | 由 `openapi-typescript` 依後端 `/v3/api-docs` 產生並**入庫**（建置不依賴後端在線） |
| `lib/api/endpoints.ts` | 每個端點一個函式，名稱與 PRD §7.1 一一對應 |
| `lib/sse/` | fetch 串流 SSE 客戶端：帶 Bearer 與 `Last-Event-ID`；斷線先走 REST `steps?afterSeq=` 回補再續接（ADR-001 D4） |
| `lib/auth/store.ts` | token 存 `sessionStorage` |
| `lib/domain/status.ts` | 專案 6／目標 5／任務 11 個狀態的中文標籤與顏色，**單一出處**（設計稿 README〈狀態 enum〉） |
| `styles/tokens.css` | 設計稿 `_ds/.../tokens/*.css` 逐字搬入；元件只引用 token，不寫死色碼 |
| 資料存取 | 全部 client-side（TanStack Query）；Server Components 只做靜態殼 |
| 表單 | react-hook-form＋zod；錯誤訊息繁中；後端 400 的 `errors[]` 對應到欄位顯示 |

### 5.4 新功能接入規範（檢查表；SelfImproving PRD ADR-SI-13、AC-SI-32-6；T1：sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d` line 13）

> **狀態：〔P1b 已落地 2026-10-22〕**——登記表 `frontend/lib/nav/registry.ts` 與其測試已在 P1b 鍵（`agentconsole-si-mirror`，commit `0596cfec`）落地；`ToolsRegion.tsx` 只消費登記表。本節是之後每個新功能（含 SelfImproving 的「自我進化」頁）的接入規範：**任一項缺＝該功能未接入完成**；全部在**同一個 commit** 收齊（根 `CLAUDE.md` 第 5 條「修復不留後遺症」：連動面不分批）。

導覽登記表的形狀（唯一來源；元件只消費、不持有清單）：

```ts
// frontend/lib/nav/registry.ts（〔P1b 已落地 2026-10-22〕；實作以 repo 檔為準，本段為設計示意）
export type NavCtx = { currentProjectId: string | null };
export interface NavEntry {
  id: string;                               // 唯一；穩定鍵（key、測試選取）
  label: string;                            // 繁中標籤；同時是 aria-label 與 title
  icon: LucideIcon;                         // lucide-react
  href: string | ((ctx: NavCtx) => string); // 動態段（如目前專案）用函式；無專案時的退回邏輯寫在函式內（execute／monitor 自 2026-11-01 起退回各自的入口頁 /execute、/monitor，不再退回 /projects；Console PRD §0.8）
  match: (pathname: string) => boolean;     // 此項是否 active：純函式，不讀 React 狀態
  order: number;                            // 升冪；唯一
  roles?: Role[];                           // 缺＝所有已登入角色（Role 見 lib/api/types.ts）
  enabled: boolean;                         // false＝不渲染；2026-11-01 起 `import` 列以此停用側欄入口（頁面、href、match 保留；PRD §0.7）
  mobile: boolean;                          // <768 底部 Tab 是否顯示（上限 6 項 true，registry.test.ts 斷言）
}
export const NAV_REGISTRY: ReadonlyArray<NavEntry> = [/* … */];
```

渲染規則：`enabled` 為真且（`roles` 缺或含目前角色）者才渲染，依 `order` 升冪；active＝依序第一個 `match(pathname)` 為真者（**不再有未知路徑 fallback 成「專案管理」**）；768～1279 為圖示側欄、≥1280 為完整側欄（`mobile` 不影響這兩者）；<768 底部 Tab 只渲染 `mobile: true` 的項（新功能預設 `false`，窄螢幕實測後再升）。**〔導覽整併 2026-11-01（Console PRD §0.7；鍵 `agentconsole-nav-consolidation`）〕**：`import` 列 `enabled: false`（側欄不顯示；`/import` 由專案管理頁按鈕「BRD/PRD 匯入」與儀表板主按鈕進入）；`order` 現值 dashboard 10、projects 20、import 30（停用）、execute 40、monitor 50、issues 55、self-improving 70、sysadmin 75、settings 80 ⇒ 顯示序 儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定；已交付列快照 `frontend/tests/helpers/navDelivered.ts` 同步。

接入檢查表（逐項勾）：

- [ ] 路由頁：`frontend/app/<feature>/page.tsx`——**只殼**，只組領域元件、不寫業務邏輯；不得 import 四區塊元件（§5.2 硬規則 1）
- [ ] 領域元件：`frontend/components/domain/<feature>/<Feature>View.tsx`（＋子元件）
- [ ] API 條目：`frontend/lib/api/endpoints.ts`（每端點一函式）、`queries.ts`（查詢鍵與 hook）、`types.ts`；`schema.d.ts` 由 `openapi-typescript` 重產並**入庫**（§5.3；建置不依賴後端在線）
- [ ] 純函式：`frontend/lib/domain/<feature>.ts`（可單測的轉換；不碰 React、不碰 fetch）＋同名 `.test.ts`
- [ ] 導覽登記表一列：`frontend/lib/nav/registry.ts`（欄位如上）；**不改 `ToolsRegion.tsx`**；`registry.test.ts` 通過（`id`／`order` 唯一、`href` 解析結果對應一個存在的 `app/**/page.tsx`、`mobile: true` 項數 ≤ 6、各項 `match` 對代表路徑互斥、`ToolsRegion.tsx` 不含 `const NAV`）；**消費端測試**（`ToolsRegion` 的 vitest，PRD AC-SI-32-6 (a)～(c)、C20）：登記表加一列即出現入口且元件原始碼不變、`enabled` 為假或角色不在 `roles` 者不渲染、入口依 `order` 排序
- [ ] 說明登記表一列（**〔PageHelp 已落地 2026-10-28〕**；PRD `docs/01_requirements/Console_PageHelp_PRD.md` FR-PH-03、FR-PH-08）：每條新路由（含 `NAV_REGISTRY` 新項的 `href` 解析結果）都要有說明項——寫 `frontend/lib/help/<page>.ts`（`title`、`purpose`、`steps`、`fields`、`states`（只引用 `lib/help/states.ts` 的表 id，不自持狀態詞）、`sourceFiles`）並登記進 `frontend/lib/help/registry.ts` 的 `HELP_PAGES`；文字須過 `lib/help/lint.ts`（繁中、英文白名單、句長）；路由鎖由 `lib/help/registry.test.ts` 守（新增 `app/**/page.tsx` 或導覽項而沒說明，`npx vitest run` 即紅並印修法）；來不及寫完只准放 `PENDING_HELP_PAGES` 且同 commit 上修 `registry.test.ts` 的 `PENDING_CEILING`（棘輪只准縮；後落地的姊妹案例外，PRD D-12）；**不改 `TopRegion.tsx`**（鈕全站一顆，§5.2）
- [ ] `layout.test.tsx`：導覽斷言由登記表驅動，**不需手改**；新項若有特殊 `roles`／`enabled` 規則，在消費端元件測試加一個「不渲染」斷言（登記表自身的唯一性與路由存在性仍由 `registry.test.ts` 守；二審 N-5）
- [ ] RTM：`docs/06_quality/RTM.md` 的本地編號子表加一列（先例 RTM.md:469 的 FsmTrail 子表；ID 加反引號故不計入總列數，不往計數列加列——該檔有「US 58」對帳）
- [ ] 本文同步：§5.1 路由樹加一行；有新端點時 §10（Bridge）、§11（後端）；有新限制或待驗項時 §12
- [ ] CI：`.github/workflows/agentconsole-ci.yml` 的 `paths` 若涉及新目錄須加——`.github/` 屬根層，開發 agent 回報、由主控代做（`AgentConsole/CLAUDE.md` 鐵律 7）
- [ ] 契約：HTTP 形狀的唯一消費者是 console-api；Bridge 新端點先改 §10 與 `engine-bridge/README.md`

**〔ResearchToPRD W0 填寫〕**逐項（任一缺＝未接入；同一個 commit 收齊）：

| 檢查項 | 填寫 |
|--------|------|
| 路由頁只殼 | 上列 2 頁；不 import 四區塊元件 |
| 領域元件 | `components/domain/research/{ResearchListView,ResearchWorkspaceView,FlowStepper,ResearchFlowHeader,TopicPanel,EvidenceTimeline,EvidenceMatrixTable,AllowlistDialog,StudioPanel,PrdOutline,PrdDiffView,MermaidBlock,GatekeeperPanel}.tsx`（P0）；`RouteDrawer.tsx`（P1）；`BuildPanel.tsx`、`DeliverPanel.tsx`、`ResearchBackLink.tsx`（P2）；重用 `SddEscalationBlock`、`CopyCommand`、`RtmPanel`、`ReviewCard`、`LiveLogCard`、`TokenTrendChart`、`MarkdownEditor`／`MarkdownView`、`EntityDialog`、`ConfirmDialog`、`NotificationBell` |
| API 條目 | `endpoints.ts` 每端點一函式；`queries.ts` 查詢鍵 `qk.research*`；`types.ts`；`schema.d.ts` 重產入庫 |
| 純函式 | `lib/domain/research.ts`（`deriveSteps`、`scoreRadar`、`diffLines`、`stepReachable`）＋`.test.ts` |
| 導覽登記表 | `{ id:"research", label:"研發工作流", icon: FlaskConical, href:"/research", match:(p)=>/^\/research(\/.*)?$/.test(p), order:35, enabled:true, mobile:false }`，加在陣列**末尾**；`mobile` 必須 false（`registry.test.ts:107,143` 數的是 `NAV_REGISTRY.filter(e=>e.mobile)` 全列，含停用的 `import`，現況已 6 列＝上限）；`order` 不可用既有值（現況 10／20／30〔import，停用〕／40／50／55／70／75／80，`lib/nav/registry.ts:42-115`），35 為空缺；圖示以落檔當時實檔為準（P0 TCS 重驗）；`DELIVERED_NAV_ROWS` 前綴斷言（`registry.test.ts:409-411`）不受影響；四份凍結 TCS（IssueCenter／SysAdminBackup／ConsoleNavConsolidation／SelfImprovingMirror）的「恰 N 項」陳述以勘誤處理 |
| 說明登記表 | 新增 `research`（清單頁）、`research-workspace`（工作區；五步差異寫在 `steps` 欄）兩條，寫實不走 pending，`PENDING_CEILING` 維持 0；`HELP_ROUTES` 加 `"/research": "research"`、`"/research/[researchId]": "research-workspace"`；`states` 引用 `lib/help/states.ts` 表 id（`lib/help/types.ts` 的 `StateTableId` 聯集新增成員 `researchFlow`——camelCase，沿既有成員命名，D-49——並新增同 id 的狀態表，詞彙取自 `flow_status`／`flow_phase`；PageHelp 既有凍結 TCS 對 `StateTableId` 成員的陳述以勘誤處理） |
| layout 測試 | 導覽斷言由登記表驅動，不需手改；加一個「`mobile:false` 不在底部 Tab」斷言 |
| RTM | `AgentConsole/docs/06_quality/RTM-ResearchToPRD-P<N>-<日期>.md`（每期一檔，先例 `RTM-ExecMonitorEntry-20261101.md`）＋ `RTM.md` 存根（ID 加反引號故不計入總列數；D-34） |
| 本文同步 | §2.2、§3、§5.1、§6(e)、§7.2、§8.2～8.4、§9.4、§10.2／§10.4、§11.1、§11.3、§12 |
| CI | `.github/workflows/agentconsole-ci.yml` 的 `paths` 兩處（`on.push`、`on.pull_request`）加 `AISDLC_SDD/*/agent/**`、`AISDLC_SDD/*/docs_template/sdd/requirements/**`、`AISDLC_SDD/*/workflow/sdd-research-to-prd/**`（Bridge 讀框架檔的對拍測試需要；先例＝同檔 `:27-28` 與 `:44-45` 的 `AISDLC_SDD/scripts/**`、`AISDLC_SDD/*/tools/fsm_runtime/**`；兩份 `paths` 清單分別在 `:21-35`、`:38-52`）——根層檔，開發 agent 回報、主控代做 |
| 契約 | `API_Contract_ResearchToPRD.md`；Bridge 端點先改 §10.4 與 `engine-bridge/README.md` |

兩個既有頁的唯一改動：`app/projects/[projectId]/execute/page.tsx`、`…/monitor/page.tsx` 的**頁殼**加 `ResearchBackLink`（`?from=research:<uuid>` 且可讀該研究專案時顯示「回到研發工作流」，P2）；`ExecuteView`／`MonitorView` 本體與其凍結 TCS 零改。

## 6. 資料流五條

### 6(a) CRUD（US-P／G／T、API-PRJ／GOL／TSK）

1. 瀏覽器 → nginx `/api/v1/**`（本機開發則直連 8080）→ backend；帶 `Authorization: Bearer`；後端 `TraceIdFilter` 對每個請求自產 traceId（回應標頭 `X-Trace-Id`；**不採信**入站值，與契約 §0.4 第 6 點一致）。
2. `JwtAuthenticationFilter` → RBAC（§8.2）→ Controller（`adapter.in.web`）→ Bean Validation → UseCase（`application.service`，`@Transactional`）。
3. UseCase 經 Repository 埠載入聚合 → 領域方法（狀態機守門、signoff 預設、Kahn 防環）→ 經埠儲存 → JPA 轉接器 → `console.*`。
4. 回應包 `{code,message,data,timestamp,traceId}`；分頁 `data={content,page,size,totalElements,totalPages}`；錯誤由 `GlobalExceptionHandler` 輸出 `{code,message,errors[],timestamp,traceId}`。
5. 軟刪除：`is_deleted=true`；專案同時 `status=ARCHIVED`；連帶軟刪其目標與任務；EXECUTING 的專案、RUNNING 的任務回 409。W5（ADR-001 D19）：同時寫 `deleted_at`（同一次刪除連帶軟刪的專案、目標、任務寫同一個值）與 `status_before_delete`；`POST /projects/{id}/restore` 於 30 天保留期內復原（只復原同一次連帶軟刪者）；專案有進行中批次時刪除其目標／任務回 409 `project_executing`。
6. 手動建立的專案／目標／任務 `signedOff=true`；建立請求帶 `draft=true` 則 `signedOff=false`（AI／外部程式與 E2E 造草案用，ADR-001 D12）。
7. 每次寫入輸出一行 `audit` 結構化日誌（subject、method、path、目標 id、status、traceId）。

### 6(b) BRD/PRD 匯入（US-I、API-IMP／SGN-01）

```
 Browser              console-api                              Engine Bridge
   | upload / text        |                                          |
   |--------------------->| ImportRecord(UPLOADED); extract text (pdf/docx)
   | parse(options)       |                                          |
   |--------------------->| detect frozen spec (API-IMP-08)          |
   |                      |-- frozen spec: GET /sdd/fsm/{project}, POST /sdd/compile -->
   |                      |-- otherwise, pass 1: POST /autoclaude/decompose (document) -->
   |                      |<-- 200 {draft_id, playbook, signed_off:false}  or  422 {gate, detail}
   |                      |-- pass 2: POST /autoclaude/decompose (once per Goal) -->
   |<---------------------| parsedResult (3-tier tree, signedOff=false), status=PARSED
   | edit result          | PUT /import/{id}/result  (status=REVIEWING)
   | signoff(approver)    | approver non-empty -> :approve every draft_id (audit) -> import.signed_off/by/at
   | confirm              | requires signoff (else 409) -> ONE transaction: create Project/Goal/Task (signed_off=true)
```

1. `upload`：副檔名限 `.md／.pdf／.docx`、大小 ≤10MB；`text`：直接貼上。兩者都建 `import_records`（`status=UPLOADED`，`source_type` 為 MARKDOWN／PDF／DOCX／PLAIN_TEXT）。
2. `parse` 請求 `ParseOptions{autonomyLevel, executionPath, additionalPrompt, specDir?}`；狀態 `PARSING`。
3. 路徑 A（規格驅動）：`specDir` 存在且 Bridge 回報 FSM 已凍結 → `POST /sdd/compile {spec_dir}` → 取得任務清單；規格未凍結時 Bridge 回 422（fail-closed），Console 原因照顯示。
4. 路徑 B（意圖拆解，預設）：二段拆解（ADR-001 D12）。每次呼叫各受三道有界閘：步驟 ≤24、Kahn 無環、每節點 prompt 非空；任一 422 → 以結構化錯誤（`gate` 為 `max_steps／cycle／empty_prompt／brain_unsupported／brain_failed`＋`detail`）回前端，`status` 退回 `UPLOADED`，`parsed_result.error` 記錄原因；**不截斷、不自動修剪**（US-I-10）。
5. 成功：`parsed_result` 存三層樹與各 `draft_id`，`status=PARSED`；`PUT /import/{id}/result` 編輯後轉 `REVIEWING`。
6. **signoff**（`API-SGN-01`）：`approver` 缺漏或空白 → 400；逐一呼叫 Bridge `:approve`；任一失敗 → 502 且不改任何狀態；成功後設 `signed_off/by/at`，回傳 `ImportRecordResponse`。
7. **confirm**（`API-IMP-05`）：未 signoff → 409；已 signoff → 單一交易建立 Project／Goal／Task（`signed_off=true`，`signed_off_by/at` 承襲 import）、寫入 `projectId`、`status=IMPORTED`，回傳 201 `ProjectResponse`。「放棄」→ `status=REJECTED`。
8. Bridge 的草案存於其 workspace 檔案（`_drafts/`），重啟後仍可 approve；workspace 被清掉時 `:approve` 回 404 → Console 回 409 並提示「草案已失效，請重新解析」。對已簽署草案重送 `:approve` 回 409 `already_signed_off`，Console 視為成功（使整體 signoff 可冪等重試）。

### 6(c) 執行（US-E、API-EXE／SSE／AUT）

**c.1 啟動** — `POST /api/v1/projects/{projectId}/execute`

1. 前端：草案（`signedOff=false`）時按鈕禁用並顯示鎖定橫幅（體驗層）；**後端為權威**。
2. console-api `ExecuteProjectUseCase`：
   1. 權限 Operator 以上；專案存在且非 ARCHIVED。
   2. 專案與所選全部 Goal／Task 皆 `signed_off=true`；否則 **409**，body 含 `reason:"未經人工審批的草案不可執行"` 與未審批 id 清單（`API-EXE-11`）。resume／restore 同樣校驗。
   3. 解析範圍 `scope{mode:ALL|SELECTED, goalIds[], taskIds[], limits{taskTokens?, goalTokens?}}`；所選 Goal 依賴了未選且未 COMPLETED 的 Goal → 409 並列出缺漏依賴。
   4. `DagService`：Goal 依 `goal_dependencies` 做 Kahn 拓撲排序，同層依 `execution.dagSchedulerStrategy`（TOPOLOGICAL＝`sortOrder`；SHORTEST_FIRST＝預估 Token 總和升序；PRIORITY 無優先欄位，視同 `sortOrder`）；Goal 內任務依 `sortOrder` → 展平為序列；寫入 `dag`（節點、邊）。
   5. `PlaybookBuilder`（`API-EXE-13`）：展平序列 → Playbook：

| Playbook 欄位 | 來源 |
|---------------|------|
| `version` | `"1.0"` |
| `project` | 專案名稱（淨化為檔名安全字串） |
| `global_goal` | 專案說明；缺則通過標準 |
| `global_invariants` | `max_retries_per_step`＝`agent.maxRetries`；`auto_compact_interval` 取引擎預設 |
| `tasks[].step_id` | `T001`、`T002`…（依展平順序，3 位補零） |
| `tasks[].goal_task_id` | **Console 任務的 UUID**（Bridge 以此寫 `execution_steps.task_id`） |
| `tasks[].name` | 任務名稱 |
| `tasks[].prompt` | 「## 任務」＋名稱＋說明＋「## 通過標準」＋通過標準（Markdown 原文）；Goal 與專案的通過標準以前綴摘要帶入 |
| `tasks[].evaluator_command`／`expected_output_regex` | 任務欄位（先過 §8.3 第二層複驗） |
| `tasks[].max_retries` | 任務 `maxRetries` |
| `tasks[].command` | 僅在 `console.execution.mock-cli=true` 時補（ADR-001 D9） |

   6. 組 `config_overrides` 與 `env`（`API-SET-10`，對映表見 §11.4）；`execution_path`＝專案 `executionPath`。
   7. 新增 `execution_runs`（僅 D10 的 console 欄位）並**提交交易**（Bridge 的 UPDATE 需要列已存在）。
   8. `AgentBridge.startRun` → Bridge `POST /autoclaude/runs`：**201** → 回 `ExecutionRunResponse`；**409**（`advisory_lock_held`，帶 `holder_run_id`）→ 補償刪除剛建的列並回 409（`API-EXE-12`）；**422** → 補償刪除並回 422；逾時／5xx → 補償刪除並回 502。
   9. 成功後：專案 `EXECUTING`；範圍內任務 `PENDING→QUEUED`；啟動 `RunEventConsumer`（虛擬執行緒）。

**c.2 事件消費與轉發**

1. `RunEventConsumer` 讀 Bridge `GET /autoclaude/runs/{run_id}/stream?after=<seq>`；斷線以最後 `seq` 重連，缺口用 `GET .../events?after=&limit=` 回補；位移存資料庫（`execution_runs.console_last_seq`，與事件處理同一交易推進，契約 §0.5 V7）。**W7 訂正（完整性審查 V-11②）**：原稿寫「位移存 Redis（`console:run:{runId}:last_seq`），無 Redis 退回記憶體」，實作從未用 Redis 存位移（ADR-001 D16 已改寫）。
2. 每則事件：(i) 依 §7.3 更新 Console 讀模型；(ii) 觸發告警評估（§6(d)）；(iii) 以 SSE 轉發給前端訂閱者，**`id:` 沿用 Bridge 的 `seq`**，使 `Last-Event-ID` 端到端有效。
3. 事件名稱對映：

| Bridge `event:` | Console `/stream/executions/{runId}/logs` | Console `/stream/executions/{runId}/metrics` |
|-----------------|-------------------------------------------|----------------------------------------------|
| `log` | `log` | — |
| `status` | `status-change` | `progress-update` |
| `step` | `log`（附步驟摘要） | `progress-update` |
| `token` | — | `token-update`、`metric-update` |
| `alert` | 原樣轉發；console-api 另依 §6(d) 本地產生自己的告警事件 | — |
| （`review-request`） | Bridge 不發；由 console-api 本地產生並於此串流注入（審核閘在 Console，見 c.4） | — |

4. 前端斷線回補：先 `GET /api/v1/executions/{runId}/steps?afterSeq={lastId}` 分頁補齊，再以 `Last-Event-ID` 續接 SSE（`API-SSE-03`）。

**c.3 控制操作**

| Console 端點 | Bridge 呼叫 | 狀態變化 |
|--------------|-------------|----------|
| `POST /executions/{runId}/pause` | `POST /autoclaude/runs/{id}:pause` → 202 `PAUSING` | 下一步驟邊界 → `PAUSED`（專案轉 READY，附錄 B.1） |
| `POST /executions/{runId}/resume` | `:resume` → 202 `RUNNING` | 專案回 EXECUTING |
| `POST /executions/{runId}/cancel` | `:stop` → 202 `CANCELLING` | → `CANCELLED`；QUEUED 任務轉 CANCELLED |
| `POST /executions/{runId}/restore/{checkpointId}` | `POST /autoclaude/runs/{id}/restore {checkpoint_id}` → 202 | 自該 checkpoint 續跑；`checkpointId`＝`checkpoints.id`，Bridge 的 `checkpoint_id` 與之同值 |

**c.4 審核閘（自治等級，API-AUT-01～06；US-E-07／E-08）** — 設計層，待 W3 後端落地驗證（§12 V-4）

AutoClaude 沒有審核鉤子，也不改它；閘點由 console-api 的 `ReviewGatePolicy` 依自治等級計算，並以既有的 `:pause` 實現。**閘點一律「提前一步」**：因為 pause 在「呼叫之後的下一個步驟邊界」生效（邊界＝引擎開始下一個步驟的那一刻），若等到閘點步驟完成事件才呼叫，邊界已過，會晚一步才停。

| 等級 | 閘點（需人工通過才續跑） | 觸發時機（提前一步） | review_requests.kind |
|------|--------------------------|----------------------|----------------------|
| 1 | 每個任務開始前 | 第 1 個任務以「啟動前確認」處理；之後每收到任一步驟的 `STARTED`（或前一步的 `COMPLETED`）即呼叫 `:pause`，使其於該步驟完成後停下 | `TASK_CONFIRM` |
| 2 | 每個目標開始前 | 目標內最後一個任務 `STARTED` 時呼叫 `:pause` | `GOAL_CONFIRM` |
| 3（預設） | 目標完成時、任務失敗時 | 目標最後任務 `STARTED` 時 `:pause`；任務失敗見下 | `GOAL_COMPLETED`、`ESCALATED` |
| 4 | 重試耗盡（ESCALATED） | 不預先 pause | `ESCALATED` |
| 5 | 僅致命錯誤 | 無 | — |
| 6～10 | 審核閘同 5。引擎能力旗標依等級物化（W7 契約 v1.3，主控裁決 D-11）：≥ 6 視為要求自動突變、≥ 7 視為要求自演化，有金鑰時送 `minimax.enable_kernel_brain`，並在批次回應回報 `engineCapabilities`（決策表見契約 §3.4.2；對映見 §11.4） | 無 | — |

1. 停在閘點時：Bridge 狀態 `PAUSED`；console-api 新增 `review_requests`（`PENDING`）並對前端發 `review-request`（導覽 Badge 計數＝待審核數）。最後一個目標的最後一步完成時 run 直接 `COMPLETED`，不再 pause、也不建立審核項。
2. `POST /executions/{runId}/review/{stepId}`（`ReviewRequest{decision: APPROVE|REJECT|RETRY|SKIP, comment?}`；審核人取自 JWT subject）：

| 決定 | 動作 |
|------|------|
| APPROVE | Bridge `:resume` |
| RETRY | 目標審核：`restore` 到該目標第一個步驟之前的 checkpoint；任務 ESCALATED：run 此時為 FAILED 態（Bridge 的 `resume` 只收 PAUSED），改用 `restore` 回到失敗步驟之前的 checkpoint（Bridge 的 `restore` 接受終態 run；終態已放的鎖須重新取得，可能 409） |
| SKIP | 僅限 ESCALATED 任務：標記任務 SKIPPED，並以剔除該步驟的 Playbook 重新啟動（`fresh=false`）；**可行性待驗（V-4）**，不可行則於 RTM 記 `🟡` 並登缺陷 |
| REJECT | Bridge `:stop` → `CANCELLED`；目標標 FAILED |

3. 引擎自行 ESCALATION（重試耗盡）：W1-B 目前把它判為 run `FAILED`（reason 以「引擎升級（ESCALATION）」開頭），並發 `step` FAILED 與 `alert` 事件；console-api 辨識該 reason，把任務標 `ESCALATED` 並建立審核項。Token Guard halt 同理（reason 帶「halted」）〔訂正（SA 修復棒；SelfImproving PRD v0.10 的 QA 複審 F-10，依本檔 V-3 結論）：原文「Token Guard halt 同理」；`RunEventProcessor.java`:314 只認 reason 前綴「引擎升級（ESCALATION）」，Token Guard halt 的 reason 帶「halted」而不帶該前綴，console 只把它映成 `ENGINE_TOKEN_HALT` 告警，不標任務 `ESCALATED`、不建審核項（讀碼所得、無對應 E2E）〕。人工處置走 `restore`（V-3、V-4；以 W1-B 交卷為準）。

**c.5 終態與對帳**：`COMPLETED／FAILED／CANCELLED` → 關閉消費者、更新專案／目標／任務狀態（§7.3）；console-api 啟動時對所有 `RUNNING／PAUSED` 的 run 呼叫 `GET /autoclaude/runs/{id}` 對帳（狀態只讀，不回寫 Bridge 擁有的欄位）；Bridge 回 404 → 發 `alert`「Bridge 失聯」，由 Bridge 自己的啟動回收把孤兒標 FAILED。

### 6(d) 監控（US-M、API-MON／ALR）

1. 資料來源：`execution_runs`、`execution_steps`、`tasks`、`goals`、`projects`、`checkpoints`、`alerts`；Agent 狀態來自 console-api 對 Bridge 的定期探測（W7 D-17：預設打 `/health/deep`，2xx 為成功、503 與連線失敗皆為失敗，契約 §3.1、§3.1.1；結果環形緩衝存**記憶體**〔`BridgeHealthMonitor`，2,880 筆＝24 小時〕——**W7 訂正（V-11②）**：原稿寫「存 Redis，無則記憶體」，實作從未用 Redis）；資源使用（CPU／記憶體／行程數，W7 D-12）來自 `GET /executions/{runId}` 的 `bridge.resources`（Bridge 以 psutil 取樣引擎行程樹，契約 §3.1.2），不入庫、不進 SSE。

| KPI（`UI-KPI-*`） | 計算（資料來源） |
|-------------------|------------------|
| 專案完成率 | `projects`：COMPLETED ÷ 非 ARCHIVED 總數 |
| 目標達成率 | `goals`：COMPLETED ÷ 總數 |
| 任務成功率 | `tasks`：COMPLETED ÷（COMPLETED＋FAILED＋ESCALATED） |
| 平均重試次數 | Σ`tasks.retry_count` ÷ 已執行任務數 |
| Token 總消耗 | Σ`execution_runs.total_tokens_used` |
| Token 預算使用率 | `total_tokens_used` ÷ `token_budget` |
| 平均任務執行時間 | avg(`tasks.completed_at − started_at`) |
| Agent 可用率 | 窗口內健康探測成功次數 ÷ 總探測次數（W7 D-17：探測打 `/health/deep`，503＝失敗，契約 §3.8.1） |

2. 趨勢：Token 趨勢＝`execution_steps.timestamp` 分桶 × Σ`tokens_used`，疊預算線；任務趨勢＝依步驟狀態轉移分桶；成功／失敗比率、執行時間分佈、重試次數分佈皆由上述表聚合。
3. 日誌查詢（`API-MON-06`）：以 `execution_steps` 衍生結構化日誌（FAILED→ERROR、RETRYING→WARN、其餘 INFO），可依時間範圍、等級、任務 id、關鍵字篩選；不新增日誌表。
4. 告警（`API-ALR-01～06`；持久化於 V4 `alerts` 表，同一規則＋對象在被確認前不重複產生）：

| 規則 | 觸發 | 動作 |
|------|------|------|
| Token 預算警告 | 使用量達預算 80%（`execution.tokenBudgetWarningThreshold`） | WARNING；頁面通知＋Badge |
| Token 預算超限 | 超過預算 | CRITICAL；呼叫 Bridge `:pause`（run 層級） |
| 連續任務失敗 | 同一目標下連續 3 個失敗（`monitor.alertConsecutiveFailures`） | CRITICAL；`:pause` 並建立審核項 |
| Agent 無回應 | 逾 300 秒無事件且探測失敗（`monitor.alertAgentTimeoutSec`） | CRITICAL；頁面通知 |
| 執行時間過長 | 單任務逾閾值 200%（`monitor.alertTaskDurationMultiplier`） | WARNING |
| 高重試率 | 目標內重試率逾 50% | WARNING |

5. 評估時機：每則被消費的事件觸發一次；另有 30 秒排程 tick 處理純時間型規則。確認告警 `POST /monitor/alerts/{alertId}/acknowledge` 寫 `acknowledged*` 欄位。
6. 報表 `API-MON-07`：PDF／CSV 由後端產生（函式庫由 W3 後端選定並記入交卷）。

### 6(e) 研究到規格（ResearchToPRD；P0 起，隨期擴充）

1. **建立**：瀏覽器 `POST /api/v1/research/projects`（OPERATOR 以上）→ console-api 驗輸入（slug、topic、深度列舉、層開關）、配 UUID、`AuditTrail.note("research.create","research",id)` → Bridge `POST /research/projects`（`X-Bridge-Token`）→ Bridge：**單一交易**寫 `research_projects`（DB 序列配 `rp_no`）＋`research_artifacts(ISSUE_SCOPE)`＋`research_events(seq=1)`，再建工作區（`BRIDGE_RESEARCH_ROOT/<slug>/`）、渲染 `issue_scope.json`、建外環 FSM 鍵 `research-<slug>`（INIT→AGENT_LOAD）→ 201。無 `BRIDGE_DB_DSN` 即 503，零檔案寫入。
2. **深研**：`POST …/stages/research` → Bridge 編譯 `RESEARCH` stage run（`.prompts/*.md`、`playbook.yaml`、`config.yaml`；`config_overrides.claude.extra_args=["--permission-mode","acceptEdits","--allowedTools","<清單>"]`；每步 `maintain_context:false`；請求 `env` 帶 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`），Bridge 原生抓取先行（arXiv／S2／GitHub／SE：原檔＋sha256＋`research_fetches`）→ 啟動 run → 事件流（引擎 `log／step／token` → `research_events`）→ run 終態 → `gates` 驗 `evidence_items.json` → 入庫（`research_sources`／`research_evidence_items`）→ 渲染 `evidence_matrix.md` → `flow_phase=EVIDENCE_READY`。
3. **起草**：`stages/draft` → `DRAFT` run（`spec-engineer`）→ 驗 SE-PRD 結構與 `E-NNN` 引用 → `research_prd_versions`(AGENT)。
4. **審查迴圈**：`stages/review`（或 `iterate`）→ `transition →SCG_VALIDATION` → `REVIEW-k` run（4 步，各自 `maintain_context:false`）→ 解析 `reviews/round-k/<dim>.json`（不合 schema 重試一次，仍不合＝`REVIEW_INVALID`：不寫輪列、不呼叫 gate，stage run 記 `exit_reason=review_invalid`）→ 前置否決＋聚合（純碼；地板 60、未結 P1）→ `gate SCG_VALIDATION PASS／FAIL`（FSM 計數；POST_HUMAN 再審通過不呼叫）→ **同一交易**一次寫 `research_review_*`（輪列、四維分數、缺陷）與事件（輪列只在輪有結果時寫入，進行中只在 stage run；D-57）→ PASS：`WAITING_HUMAN`／FAIL：`REVISE-k` run（缺陷清單進起草者 prompt）→ 再審；第 3 次 FAIL＝`ESCALATED`（外環鍵 `SDD_ENABLE_AUTO_RECOVERY=0`）；ESCALATION 人工恢復後預算不歸零，至多再得一次審查（D-60；§12.1 L-R12）。
5. **Gate 0**：`POST …/approve`（**僅 ADMIN**；`expectedDigests`＝人當時看到的版本摘要）→ Bridge `:approve-baseline`：複製核准版為 `PRD-v1.0.0.md` →（有重試史才）`transition →SPEC_REGRESSION_CHECK` → `spec-frozen --stage Gate-0 …`（docs＝PRD＋證據矩陣＋issue_scope＋adr_draft）→ `research_gate_decisions`（append-only）＋`research_artifacts(PRD_BASELINE)` → `flow_step=route`。人工退回＝`POST …/return`（`gate SCG_VALIDATION FAIL`，共用預算）。
6. **分流**（P1）：`POST …/route/preview`（OPERATOR，零副作用）→ `POST …/route`（**僅 ADMIN**）→ console-api 先建 `projects` 列（`execution_path`、`sdd_project`）→ Bridge `:route`（git／scaffold／發佈文件／建內環鍵／Stage-1 採納）→ `research_route_decisions`＋`research_route_steps` → `flow_step=build`。
7. **內環**（P1 TCS 草擬、P2 看板）：`tcs-draft` stage run → 既有 `POST /projects/{id}/sdd/freeze`（Stage-2）→ 既有 import／signoff／execute（console-api 原路徑）→ 事件仍由既有 `RunConsumers` 寫 `execution_*`；研究面只做連結與衍生相態；SCG-4／SCG-5 由 ADMIN 以 `POST …/gates` 登錄（P2）。
8. **斷線續做**：任何時間重進 `/research/{id}`：`GET` 回 `flow.currentStep`；SSE 以 `Last-Event-ID` 或 `?after=` 從 `research_events` 重播；「我已恢復，繼續（僅一次機會）」＝`stages/revise` 帶 `afterEscalation=true`，Bridge 唯讀驗 FSM 已離開 ESCALATION*；「換世代」＝`POST …/reinit` 帶 `generation:"next"`（D-60、D-64；**僅 ADMIN**：VIEWER 由既有授權鏈擋下〔403 `ACCESS_DENIED`〕、OPERATOR 由 console-api 的 `ResearchCommandService` 在服務層擋下〔403 `research_write_forbidden`〕，兩者 Bridge 請求數 0；FSM 現態須為 ESCALATION*、理由必填）：Bridge 建新世代鍵 `research-<slug>-g<N+1>`、`fsm_generation`＋1、`fsm_project` 改指新鍵、寫 `research_gate_decisions(ABANDON_KEY)`，舊鍵留 ESCALATION、不呼叫 `resume-from-escalation`。

## 7. `execution_runs` 寫入分工與資料所有權

### 7.1 `execution_runs` 欄位寫入分工（ADR-001 D10；PRD §0.2.2「狀態真相單一」）

| 欄位 | 寫入者 | 時機 | 備註 |
|------|--------|------|------|
| `id` | console-api | 建立 | UUID；同時是 Bridge 的 `run_id` |
| `project_id` | console-api | 建立 | |
| `run_number` | console-api | 建立 | 同專案遞增；`UNIQUE(project_id, run_number)`，取號須鎖專案列避免競態 |
| `autonomy_level` | console-api | 建立 | |
| `scope` | console-api | 建立 | JSONB：`{mode, goalIds, taskIds, limits}` |
| `token_budget` | console-api | 建立 | |
| `dag` | console-api | 建立 | JSONB：節點與邊；狀態於讀取時疊加 |
| `started_at` | console-api | 建立 | DDL default `NOW()` |
| `engine_capabilities` | console-api | 建立（W7，V10） | JSONB，可 NULL：該批次 spawn 時 Console 送進引擎的能力狀態 `{autoMutation, selfEvolution}`（`ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`）；與批次列同一次 INSERT 寫入、之後不更新；NULL＝V10 之前的批次（契約 §3.4.2、ADR-001 D20） |
| `status` | **Bridge** | 之後全程 | 初值由 DDL default `INITIALIZING` 帶入（非 console 顯式寫入）；只寫 PRD 六態 |
| `subprocess_pid` | **Bridge** | spawn 後 | |
| `bridge_instance` | **Bridge** | spawn 後 | |
| `advisory_lock_key` | **Bridge** | 取鎖後 | |
| `total_tokens_used` | **Bridge** | token 事件／步驟完成 | |
| `completed_at` | **Bridge** | 終態 | |

console-api 對 Bridge 欄位**只讀**；Bridge 對 console 欄位**只讀**（SQL 僅 `UPDATE … WHERE id=run_id` 於其擁有的欄位，列不存在則略過並記 log）。

### 7.2 其他表所有權與狀態映射

| 表 | 寫入者 | 讀取者 |
|----|--------|--------|
| `execution_steps`、`checkpoints` | **Bridge**（INSERT；`task_id`＝playbook 的 `goal_task_id`） | console-api（唯讀） |
| `projects`、`goals`、`tasks`、`goal_dependencies`、`import_records`、`system_configs`、`system_config_history`、`review_requests`、`alerts` | **console-api**（唯一） | Bridge 不寫；僅 `execution_steps.task_id` 的外鍵檢查會觸及 `tasks` |
| `issue_priority`（V14；議題中心的順位，PRD `docs/01_requirements/Issue_Center_PRD.md` §6.5、TCS-IssueCenter R-IC-59） | **console-api**（唯一；JDBC 配接器只有 UPSERT 與 DELETE 兩條敘述，經 `PUT／DELETE /api/v1/issues/{id}/priority`、僅 ADMIN；無 JPA 實體，`ddl-auto=validate` 不檢查本表；不存歷史，變更軌跡在 `audit_log`） | Bridge 不讀不寫（議題本身住根層 SelfImproving 帳本，Bridge 只經 `GET /si/issues` 唯讀鏡像）；順位只在 console-api 合併進 `GET /api/v1/issues` 回應 |
| `backup_jobs`（V15；手動備份工作，PRD `docs/01_requirements/Console_SysAdmin_Backup_PRD.md` §6、TCS-SysAdminBackup §C5；**〔K1 已落地 2026-10-28〕**） | **console-api**（唯一；`BackupJobService` 先插列後寫請求檔、寫檔失敗補償為 FAILED；`BackupJobReconciler` 把 sidecar `results/` 對帳回終態、QUEUED 逾 2×`request-ttl-seconds` 標 EXPIRED、RUNNING 逾 `job-max-seconds` 且心跳過期標 timeout；只有 ADMIN 經 `POST /api/v1/sysadmin/backups/jobs` 建列；無 JPA 實體，`ddl-auto=validate` 不檢查本表；變更軌跡在 `audit_log`） | Bridge 不讀不寫；sidecar 不碰 DB（只經兩個具名卷的檔案協定，§2.5） |
| `research_projects`（V16；含 `rp_no`、`flow_*` 游標、`last_event_seq`、`console_project_id`） | **Bridge**（INSERT；條件式 UPDATE；`id` 由 console-api 配號、同 `run_id` 先例；`rp_no` 由 DB 序列配號）；游標與引擎動作**同一交易** | console-api（JDBC 唯讀）。**console-api 對 `research_*` 零寫入**：ArchUnit 加一條「`adapter.out.persistence.research..` 不得出現 `INSERT｜UPDATE｜DELETE`」的字串掃描測試 |
| `research_events`（V16；append-only，DB 觸發器擋 UPDATE／DELETE） | **Bridge** | console-api；時間軸、SSE 重播、對帳結果與稽核的共同事實來源 |
| `research_stage_runs`、`research_artifacts`（V16） | **Bridge** | console-api；研究 stage run **不進** `execution_runs`／`execution_steps`（`db.py:100-114` 的跳過行為，§6(e)） |
| `research_sources`、`research_fetches`、`research_evidence_items`、`research_allowlist_entries`（V17） | **Bridge**（`research_fetches`、`research_evidence_items` append-only；`research_sources` 只准升級查證層級；`research_allowlist_entries` 只准更新 `enabled`／停用欄） | console-api；allowlist 的 POST／PATCH 經 console-api 轉 Bridge，僅 ADMIN |
| `research_prd_versions`（含本文，V18） | **Bridge**（人工編輯經 `PUT /research/projects/{id}/prd` 由 Bridge 寫檔＋寫列；console-api 不直寫） | console-api；append-only（新版新列） |
| `research_review_rounds`／`_scores`／`_defects`（V18） | **Bridge**（rounds 與 scores append-only：輪列只在輪有結果時、與分數列、缺陷列同一交易一次寫入，D-57；defects 的 `status` 單向可轉移） | console-api；評分由 Bridge 純碼聚合，審查者 agent 只提供各維度分數與缺陷 |
| `research_gate_decisions`（V18；append-only） | **Bridge** | console-api；人工決定的內容；V6 `audit_log` 另記「誰對哪個實體做了請求」（`V6__audit_log.sql:4-5`，無本文），兩者以 `audit_trace_id`＝`trace_id` 對應 |
| `research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`、`research_deliveries`、視圖 `v_research_healing_attempts`（V19） | **Bridge** | console-api；`research_route_decisions.console_project_id` 指向 console-api 先建的 `projects` 列；視圖建在既有 `execution_runs`／`execution_steps` 之上、不新增寫入路徑 |

研究專案的內環 run＝`execution_runs.project_id=research_projects.console_project_id`；工作區檔案由 Bridge 寫、人唯讀；`state.json` 是 Bridge 匯出的**非權威**投影，不得被任何程式讀回當輸入（ADR-003 D3）。

W5（契約 v1.2）增補的欄位，同樣只由 console-api 寫：`import_records.warnings`（JSONB，預設 `[]`）、`import_records.parse_options`（JSONB，可 NULL）——重開匯入記錄時還原黃色解析提示與解析選項（V8，主控裁決 C-10）；`projects.deleted_at`／`projects.status_before_delete`、`goals.deleted_at`、`tasks.deleted_at`——軟刪除保留期與復原（V9，主控裁決 C-3，ADR-001 D19；刪除專案時專案與連帶軟刪的目標、任務寫同一個 `deleted_at`）。欄位定義見 §11.3 與契約 §0.5。

W7（契約 v1.3）再增補：`execution_runs.engine_capabilities`（JSONB，可 NULL）——該批次 spawn 時 Console 送進引擎的能力狀態，建立時與批次列同一次 INSERT 寫入、之後不更新（V10，主控裁決 D-11，ADR-001 D20）；V10 同時校正 `system_configs.impact_note` 三個鍵（`model.enableKernelBrain`、`agent.enableAutoMutation`、`agent.enableSelfEvolution`）的文字。資源取樣（D-12）**不入庫**：`bridge.resources` 每次由 Bridge 的記憶體樣本現取（契約 §3.1.2）。

| Bridge 狀態（8 態） | 寫入 PG `execution_runs.status`（PRD 6 態） |
|--------------------|-----------------------------------------------|
| INITIALIZING | INITIALIZING |
| RUNNING | RUNNING |
| PAUSING | RUNNING |
| PAUSED | PAUSED |
| CANCELLING | RUNNING |
| COMPLETED | COMPLETED |
| FAILED | FAILED |
| CANCELLED | CANCELLED |

### 7.3 事件 → Console 讀模型更新（由 console-api 的 `RunEventConsumer` 執行）

| Bridge 事件 | Console 更新 |
|-------------|--------------|
| `step` STARTED | 任務 `RUNNING`、`started_at`；首任務時目標 `IN_PROGRESS` |
| `step` COMPLETED | 任務 `COMPLETED`（經 VALIDATING）、`completed_at`、`actual_tokens`；目標任務全完成 → `COMPLETED` |
| `step` RETRYING | 任務 `retry_count+1`（FAILED→QUEUED→RUNNING） |
| `step` FAILED | 重試未耗盡 → `FAILED→QUEUED`；耗盡 → `ESCALATED` 並建立 `review_requests`（kind＝ESCALATED） |
| `status` PAUSED | 專案 `READY`（附錄 B.1）；若為閘點則建立 `review_requests` |
| `status` RUNNING（resume 後） | 專案回 `EXECUTING` |
| `status` COMPLETED | 專案 `COMPLETED` |
| `status` FAILED | 專案 `FAILED`；進行中任務 `FAILED` |
| `status` CANCELLED | 專案 `READY`（可重新執行）；QUEUED 任務 `CANCELLED` |
| `token` | `execution_runs.total_tokens_used` 由 Bridge 寫；console-api 僅用來評估預算告警 |

## 8. 安全

### 8.1 認證（NFR-9.2-01；ADR-001 D4）

JWT（HS256）；access 30 分鐘、refresh 7 天；`POST /api/v1/auth/login`、`/auth/refresh`、`/auth/logout`（W7 D-19）；使用者清單在 `application.yml`（bcrypt）；`JWT_SECRET` 必填且 ≥32 字元；前端存 `sessionStorage`；SSE 以 fetch 串流帶 Bearer，禁止 query-string token。

**refresh token 撤銷名單（W7 D-19；契約 §1.9、ADR-001 D16／D23）**：每個 token 已有 `jti`（`JwtTokenService` 簽發時 `.id(UUID)`）；換新（`/auth/refresh`）時**原子地撤銷舊 refresh token**（`tryRevoke(jti)`，回 false 即 401 `INVALID_REFRESH_TOKEN`），登出（`/auth/logout`，免認證、一律 204）同樣撤銷；名單只存 `jti`，存活到該 token 的 `exp`。儲存 Redis 優先（鍵 `console:revoked-refresh:<jti>`），**Redis 不在線降級為單實例記憶體名單並記 WARN**（只在狀態轉換時記）；必須設 `management.health.redis.enabled=false`，否則 Redis 一掛 `/actuator/health` 變 DOWN、降級承諾落空。access token 無狀態、不在名單內（最長 30 分鐘後自然失效）。**限流計數與 SSE 位移不使用 Redis**（ADR-001 D16 如實登記）。

### 8.2 RBAC（NFR-9.2-02；SA 設計，PRD §9.2 只列角色名）

| 能力 | 匿名 | Viewer | Operator | Admin |
|------|------|--------|----------|-------|
| 登入、續期、登出（W7）、`/actuator/health`、`/v3/api-docs`、`/swagger-ui/**` | ✅ | ✅ | ✅ | ✅ |
| 讀取專案／目標／任務／匯入記錄／執行／監控／SSE 串流／引擎狀態（`GET /engines/sdd`）／待審批清單（`GET /signoffs/pending`）（後兩者 W7） | — | ✅ | ✅ | ✅ |
| 讀取系統參數（敏感值遮罩）、匯出監控報表 | — | ✅ | ✅ | ✅ |
| 專案／目標／任務的建立、編輯、刪除、重試 | — | — | ✅ | ✅ |
| 專案復原（`POST /projects/{id}/restore`）、檢視已刪除專案（`GET /projects?deleted=true`；VIEWER 回 403，由 controller 檢查）——W5 C-3 | — | — | ✅ | ✅ |
| signoff（匯入／專案／目標／任務） | — | — | ✅ | ✅ |
| 匯入 upload／text／parse／編輯／confirm | — | — | ✅ | ✅ |
| 執行 execute／pause／resume／cancel／restore／review | — | — | ✅ | ✅ |
| 告警確認 | — | — | ✅ | ✅ |
| 讀取系統管理／資料庫備份總覽與工作紀錄（`GET /api/v1/sysadmin/backups`、`…/backups/jobs`、`…/backups/jobs/{id}`；**〔K1 已落地 2026-10-28〕**ADMIN 另見 `detailTail`／`requestedBy`／`detail`，其餘角色該欄為 null） | — | ✅ | ✅ | ✅ |
| 手動觸發備份工作（`POST /api/v1/sysadmin/backups/jobs`；`SecurityConfig` 規則置於通用規則之前；sidecar runner 階段二落地前真機不可用） | — | — | — | ✅ |
| 修改系統參數（單鍵、token-guard、reset、匯入設定） | — | — | — | ✅ |
| 測試模型連線、匯出設定（不含敏感明文） | — | — | — | ✅ |
| 揭露敏感參數明文（US-S-04「顯示」；每次寫審計） | — | — | — | ✅ |
| 讀研究專案／事件／來源／證據／PRD 版本／審查／分流／SCR／交付／allowlist（`GET /api/v1/research/**`、`/api/v1/stream/research/**`；**〔ResearchToPRD〕**） | — | ✅ | ✅ | ✅ |
| 建研究專案、啟動 stage（研究／草擬／審查／修訂／迭代／TCS 草擬）、存 PRD 新版、分流預演、發起 SCR、取消／對帳／封存／復原／重試初始化（`POST／PUT` 通用規則） | — | — | ✅ | ✅ |
| **Gate 0 核准與退回修改、分流確認、SCG-4／SCG-5 登錄、建立 Release Tag／PR、新增／停用研究來源 allowlist**（`POST …/approve`、`…/return`、`…/route`、`…/gates`、`…/delivery/tag`、`…/delivery/pr`、`POST／PATCH /research/allowlist`；`SecurityConfig` 逐條規則**置於通用規則之前**，先例 `SecurityConfig.java:88-97`；D-12） | — | — | — | ✅ |
| **換世代**（`POST …/reinit` 帶 `generation:"next"`；同一路徑的重試初始化模式為 OPERATOR 以上，`SecurityConfig` 的 matcher 無法依請求本文分流，所以角色檢查分兩段：VIEWER 由既有授權鏈擋下（403 `ACCESS_DENIED`），OPERATOR 通過授權鏈後由 console-api 的 `ResearchCommandService` 在服務層擋下（403 `research_write_forbidden`），兩者 Bridge 請求數 0，以 `RbacIT` 各釘一個斷言；D-64） | — | — | — | ✅ |

`approver` 一律取 JWT subject，請求本文不收（先例 `SddFreezeRequest.java:11`）；`RbacIT` 補：VIEWER 對所有 POST／PUT／PATCH 回 403、OPERATOR 對 ADMIN 專屬端點回 403、對 `reinit` 帶 `generation:"next"`：VIEWER 回 403 `ACCESS_DENIED`（授權鏈）、OPERATOR 回 403 `research_write_forbidden`（服務層），兩者 Bridge 請求數皆為 0（D-64）、匿名 401。

Bridge 端點不對任何使用者開放，只有 console-api 以服務身分呼叫（內網）。

### 8.3 NFR-SEC-03：UI 輸入 → 引擎指令／路徑的消毒鏈

| 層 | 位置 | 規則 | 違規回應 |
|----|------|------|----------|
| 1 輸入驗證 | console-api，任務建立／更新 | `evaluatorCommand` 不得含黑名單字元；`expectedOutputRegex` 須可編譯；`executionPath` 為絕對路徑格式 | 400，列出違規字元與欄位 |
| 2 物化前複驗 | console-api，`PlaybookBuilder` | 逐步驟重驗第 1 層規則；Phase 4 並加**可執行檔白名單**（`console.security.evaluator-allowlist`，預設值由 W3 後端定案並記入交卷） | 400／422，且**不呼叫** Bridge |
| 3 Bridge 入口 | `engine-bridge/app/security.py` | `execution_path` 須絕對、存在、`resolve()`＋`normcase()` 後位於 allowlist root 之下（擋 `..` 與 symlink 逃逸）；`evaluator_command` 套同一黑名單字元集 | 422，`violations[]` 列出字元與步驟 |
| 4 引擎末端 | AutoClaude `pre_run_validator` 與 shell 評估器 | 引擎自身的整體驗證與 CONDITIONAL 防線 | 引擎拒絕啟動／步驟失敗 |

- **黑名單字元集 SSOT**：`AutoClaude/autoclaude/utils/shell_deny_chars.py` 的 `BASE_DENY_CHARS = frozenset("!`><~$&;")`（8 個字元）。Bridge 以 parity 測試直接比對該常數；後端複製常數並在檔頭註明 SSOT 路徑，W4 QA 以腳本比對兩者字元集一致（Plan W4）。
- 引擎的 SDD 路徑另有模板白名單（`SddToPlaybookAdapter._EVALUATOR_TEMPLATE`）；UI 自由輸入的 `evaluatorCommand` 不走該模板，故依上表第 2 層以可執行檔白名單補強。

**〔ResearchToPRD 增列〕UI 輸入 → 引擎指令／路徑**

| 層 | 位置 | 規則 | 違規 |
|----|------|------|------|
| 1 | console-api | `slug`＝`^[a-z0-9][a-z0-9-]{0,29}$`；`topic` ≤500 字、無 NUL；`depthLevel` 列舉；層開關布林；`targetPath` 絕對路徑；`stackTemplate`／`visibility` 列舉；`repoName`＝`^[a-z][a-z0-9-]{1,38}$`；allowlist `host` 正規式 | 400（欄位級 `errors[]`） |
| 2 | Bridge 入口 | `execution_path`／`targetPath` 過 `security.check_path`（allowed roots，含自動併入的 research／scaffold 根）；`prd` 本文 ≤1 MiB、UTF-8、無 NUL；`expectedDigests` 鍵為相對 POSIX 路徑；寫入面需 `X-Bridge-Token`（`BRIDGE_RESEARCH_WRITE_TOKEN`，規則同 SI 權杖） | 422 `violations[]`／403／503 |
| 3 | Bridge 子行程 | `git`／`gh`／FSM CLI 一律 **argv 陣列、不經 shell**；所有使用者可影響的 argv 片段先過列舉或正規式；環境以白名單重建（移除 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`）；`GH_TOKEN` 只進子行程 env、**不入 argv／檔案／log／DB**；子行程一律經 `procutil.popen_platform_kwargs()`；git／gh 允許集合見 ADR-003 D16 | `sdd_cli_usage`（Bridge 自己的 bug）500 |
| 4 | 引擎末端 | stage run 以 `--allowedTools` 分角色最小授權（研究：Read／Write／Edit／Glob／Grep，Web 層啟用時加 WebSearch／WebFetch；起草修訂：Read／Write／Edit／Glob／Grep；審查：Read／Glob／Grep＋`Write(<工作區>/02_governance/reviews/**)`）；一律不給 Bash／PowerShell／Task／Agent；`evaluator_command` 受 `DENY_CHARS`（`security.py:35,246-271`）與引擎 PRE_ATTEMPT 驗證，路徑一律 `resolve()` 長名（避 Windows 8.3 短名的 `~`） | 步驟失敗 |

### 8.4 NFR-SEC-04：外呼預設 deny＋allowlist，與 SSRF 防護

> **誠實劃界（主控 2026-10-15 回寫）**：Bridge 的 SEC-04 實作為精確 host 白名單＋兩種 URL 解析器一致性校驗＋拒絕 userinfo／反斜線／IDN 差異／十進位與十六進位 IP 寫法＋私網 IP 除非明列否則拒絕；**DNS 解析後驗 IP 與釘住連線 IP 未做**（實際外呼由引擎行程自己解析，Bridge 釘不住），decompose 的 httpx 不跟隨 redirect。後端 Phase 6 的 `test-connection` 須自行補 DNS 解析後驗 IP。

- **範圍**：(a) console-api 的 `POST /settings/test-connection` 與任何由 Console 發起的 HTTP；(b) Bridge 對 MiniMax 等模型端點的外呼（`config_overrides` 的 `minimax.base_url`、環境變數 `MINIMAX_BASE_URL`）。
- **規則**：預設 deny；域名 allowlist（Bridge：`BRIDGE_OUTBOUND_ALLOWLIST`；console：`console.security.outbound-allowlist`）；校驗欄位明列 `model.apiUrl` 與 `MINIMAX_BASE_URL`；**禁私網段與 loopback／link-local**（`127.0.0.0/8`、`10/8`、`172.16/12`、`192.168/16`、`169.254/16`，另補 IPv6 的 `::1`、`fe80::/10`、`fc00::/7`）；禁 DNS rebinding（解析後驗 IP、連線用已驗 IP）；禁 redirect 跳出 allowlist（不自動跟隨，或每一跳重驗）；全程審計 log。
- **本機例外**：`localhost`／`127.0.0.1` 只在 e2e／本機開發 profile 的 allowlist 內明列時放行（供 `mock_brain_server.py`）；Docker 全棧預設 allowlist 不含 loopback 與私網。
- **〔ResearchToPRD 增列〕研究抓取**：Bridge 對研究來源的抓取使用新包裝函式 `check_research_url`（`app/research/fetch/allowlist.py`；先呼叫既有 `security.check_outbound_url`〔`security.py:275-303`，接受 http、任意埠與尾點〕取 parser 一致性，再加 https 限定、埠 443 限定、尾點拒絕與解析後私網 IP 拒絕；不修改 `check_outbound_url`，D-62(3)）、**獨立清單**（`BRIDGE_RESEARCH_FETCH_ALLOWLIST`＋ADMIN 管理的 `research_allowlist_entries`；與模型端點清單 `BRIDGE_OUTBOUND_ALLOWLIST` 分開，D-35），預設 deny。Bridge 自己是 HTTP 客戶端，所以補上上方誠實劃界承認缺的「DNS 解析後驗 IP、釘連線」（**僅限研究抓取**）：resolve → 拒 `127/8、10/8、172.16/12、192.168/16、169.254/16、::1、fe80::/10、fc00::/7` → 以解析後 IP 連線並設 `Host`／SNI → 不自動 redirect（`follow_redirects=false`，同 `decompose` 先例）、逐跳重驗 → 逐筆寫 `research_fetches`（含被拒者，`outcome=DENIED_*`）；回應體上限 5 MiB、逾時 20 s；各 host 套 `min_interval_seconds` 並遵守伺服器回傳的限流訊號。httpx 釘 IP＋SNI 的可行性由 V-R4 實測，不可行則退回「解析後比對 IP 非私網」。headless claude 的 WebFetch／WebSearch 不經此清單（引擎行程自己外呼）→ 以 `WebFetch(domain:…)` 規則與 `allowed_domains` 約束（V-R1），**Web 層預設關閉**（Web allowlist 為空），並在 §12.1 L-R1 如實登記為「Bridge 觀測不到單筆呼叫，只認 agent 宣告」。GitHub token：console-api 從 `system_configs`（`is_encrypted`，AES-256）取出後**僅在單次請求本文**傳給 Bridge；Bridge 不落地。Mermaid：`securityLevel:'strict'`，渲染逾時 3 s，失敗顯示原始碼。

### 8.5 NFR-SEC-05：token_guard 群組校驗

- `compactThresholdPct` 與 `haltThresholdPct` 皆 1～100 且 **halt > compact**。
- 執行點：① `PUT /settings/execution/token-guard` 原子事務＋跨鍵校驗，不滿足回 400（`reason:"halt_threshold_pct 必須大於 compact_threshold_pct"`）；② `PUT /settings/{category}/{key}` 直接更新單鍵時讀對端鍵一併校驗（禁止逐鍵繞過）；③ 前端表單以 zod 鏡射同一規則；④ 引擎自身 `TokenGuardConfig` 的驗證為最後一道。
- **不得經 Console 繞過安全收斂**：config_overrides 只傳 `compact_threshold_pct`、`halt_threshold_pct`、`auto_resume`、`max_auto_resumes`，不暴露 `token_guard.enabled`。

### 8.6 其他控制

| 項目 | 設計 |
|------|------|
| 敏感資料（NFR-9.2-03） | `is_encrypted` 欄位以 AES-256 加密儲存；金鑰由環境變數 `CONSOLE_ENCRYPTION_KEY` 提供（缺則禁止寫入敏感參數）；明文不入 log、不回傳（除 Admin 揭露） |
| CORS（NFR-9.2-05） | 只允許 `console.cors.allowed-origins`（開發預設 `http://localhost:3000`）；全棧同源，經 nginx |
| Rate Limit（NFR-9.2-06） | 每分鐘 100 次（Bucket4j **記憶體**固定視窗，契約 §0.4 第 4 點；**W7 訂正（完整性審查 V-11②）**：原稿寫「以 Redis 計數；無 Redis 退回記憶體」，實作從未使用 Redis，ADR-001 D16 已改寫） |
| 審計（NFR-9.2-07） | 每次寫入輸出 `audit` 結構化 JSON 日誌（subject、method、path、目標 id、status、traceId）；PRD §6.2 無審計表，故不新增資料表 |
| SQL 注入（NFR-9.2-04） | 全部經 JPA／參數化查詢；Bean Validation 於 Controller 邊界 |
| traceId 貫穿（NFR-9.4-04；W5 C-12） | console-api 的 `TraceIdFilter` 對每個請求自產 traceId（寫入 MDC、回應標頭 `X-Trace-Id` 與封包 `traceId`，不採信入站值）；console-api 對 Bridge 的**每個請求**帶 `X-Trace-Id`（背景消費者用該 run 的 traceId 或新產）；Bridge 中介層讀取（缺則自產 uuid4）、回應回帶同名標頭、每一行應用日誌帶 `trace_id`（契約 §0.4 第 6 點、§3.1.1） |
| Bridge 暴露面 | 無認證（§12 L-6）：僅 backend-net 可達；本機開發綁 `127.0.0.1`；對 host 發布 8081 視為缺陷 |

## 9. 執行模式

> 所有指令為 **bash＋PowerShell 雙區塊**。PowerShell 區塊遵守本 repo 鐵律：不用裸 `cd`／`Set-Location`（以 `Push-Location …; …; Pop-Location` 同行成對）、不用 `VAR=value cmd` 前綴（改 `$env:VAR="value"; cmd`）、不接管線讀 rc。每個服務各開一個終端前景執行；不要用 `&`／`nohup` 把服務推到背景。指令的工作目錄假設在 monorepo 根。

### 9.1 前置需求

| 軟體 | 版本 | 用途 |
|------|------|------|
| Docker | Docker Desktop（Windows 為 WSL2 後端）或 Engine，含 Compose v2 | PG 與全棧 |
| Java | 21 | backend |
| Node.js | 22 LTS（npm 10） | frontend |
| Python／uv | Python 3.11（由 uv 管理）／uv | Bridge（**不可用系統 python3；macOS 預設為 3.9**） |

```bash
docker --version; docker info > /dev/null; echo "docker_rc=$?"
java -version
node -v; npm -v
uv --version
```

```powershell
docker --version; docker info *> $null; "docker_rc=$LASTEXITCODE"
java -version
node -v; npm -v
uv --version
```

### 9.2 本機開發（只起 PG 容器；三個服務本機跑，埠 3000／8080／8081）

**步驟 0（一次）：準備環境檔**

```bash
cp AgentConsole/.env.example AgentConsole/.env
```

```powershell
Copy-Item AgentConsole\.env.example AgentConsole\.env
```

**步驟 1：起 PostgreSQL**（`docker-compose.dev.yml`：postgres-primary 發布 5432；redis 為選配）

```bash
(cd AgentConsole && docker compose -f docker-compose.dev.yml up -d)
```

```powershell
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml up -d; Pop-Location
```

**步驟 2：Engine Bridge（終端 A，埠 8081）**

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && uv pip install -e .)
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && BRIDGE_DB_DSN='postgresql://aisdlc:<YOUR_POSTGRES_PASSWORD>@localhost:5432/aisdlc' uvicorn app.main:app --host 127.0.0.1 --port 8081)
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; $env:BRIDGE_DB_DSN="postgresql://aisdlc:<YOUR_POSTGRES_PASSWORD>@localhost:5432/aisdlc"; uvicorn app.main:app --host 127.0.0.1 --port 8081; Pop-Location
```

**步驟 3：backend（終端 B，埠 8080）**

```bash
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' ENGINE_BRIDGE_URL=http://localhost:8081 ./gradlew bootRun)
```

```powershell
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5432/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; $env:ENGINE_BRIDGE_URL="http://localhost:8081"; .\gradlew.bat bootRun; Pop-Location
```

`./gradlew` 出現 Permission denied 時改 `sh gradlew bootRun`（索引模式見 ADR-001 D15）。

**步驟 4：frontend（終端 C，埠 3000）**；`frontend/.env.local` 設 `NEXT_PUBLIC_API_URL=http://localhost:8080`

```bash
(cd AgentConsole/frontend && npm ci && npm run dev)
```

```powershell
Push-Location AgentConsole\frontend; npm ci; npm run dev; Pop-Location
```

**步驟 5：驗證**（另開終端）

```bash
curl -s http://localhost:8081/health
curl -s http://localhost:8080/actuator/health
```

```powershell
Invoke-RestMethod http://localhost:8081/health
Invoke-RestMethod http://localhost:8080/actuator/health
```

預期：Bridge 回 `"status":"ok"`；backend 回 `"status":"UP"`；瀏覽器開 `http://localhost:3000` 見登入頁。

### 9.3 Docker 全棧（compose 全部服務，經 nginx 單一入口）

**步驟 1：準備環境檔並填值**（同 9.2 步驟 0；全棧的 `NEXT_PUBLIC_API_URL` 留空＝同源，見 ADR-001 D14-12）

**步驟 2：建置並啟動**（profile 名稱以 W2-B 的 `docker/README.md` 為準；若有出入由 W2-B 回寫本節）

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location
```

**步驟 3：驗證**

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full ps)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/api/v1/projects
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full ps; Pop-Location
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost/
curl.exe -s -o NUL -w "%{http_code}\n" http://localhost/api/v1/projects
```

預期：`ps` 各服務皆 healthy；第一個 curl 回 `200`（nginx→frontend 通）；第二個回 `401`（nginx→backend 通，且未帶 token 被擋；回 `502` 代表 nginx 連不到 backend，即 ADR-001 G-01 未解）。`/actuator/` 依 PRD §11.5 由 nginx 擋下（`deny all`），後端健康改看 `ps` 的 healthy 欄。注意：全棧下專案的 `executionPath` 是 Bridge **容器內**的路徑（預設在 `/workspace/` 之下），見 §12.1 L-8。

**步驟 4：收尾**（保留資料卷；`down -v` 會刪全部資料，僅限清場）

```bash
(cd AgentConsole && docker compose --profile db --profile app --profile full down)
(cd AgentConsole && docker compose -f docker-compose.dev.yml down)
```

```powershell
Push-Location AgentConsole; docker compose --profile db --profile app --profile full down; Pop-Location
Push-Location AgentConsole; docker compose -f docker-compose.dev.yml down; Pop-Location
```

### 9.4 環境變數

| 變數 | 服務 | 說明 |
|------|------|------|
| `POSTGRES_DB`／`POSTGRES_USER`／`POSTGRES_PASSWORD` | compose、PG | 預設 `aisdlc`／`aisdlc`／（必填佔位符） |
| `JWT_SECRET` | backend | 必填，≥32 字元 |
| `CONSOLE_ENCRYPTION_KEY` | backend | AES-256 金鑰（敏感參數加密） |
| `SPRING_DATASOURCE_URL`／`_USERNAME`／`_PASSWORD` | backend | 本機：`jdbc:postgresql://localhost:5432/aisdlc`；容器：`…@postgres-primary:5432/…` |
| `SPRING_DATA_REDIS_HOST`／`_PORT` | backend | **選填**（W7 D-19）：容器：`redis`／`6379`；本機未起 Redis 則不設（refresh token 撤銷名單退回單實例記憶體）。**只有撤銷名單使用 Redis**（限流計數與 SSE 位移不用，ADR-001 D16／D23；契約附錄 D.2） |
| `ENGINE_BRIDGE_URL` | backend | 本機 `http://localhost:8081`；容器 `http://engine-bridge:8081` |
| `CONSOLE_BACKUP_OUT_DIR`／`CONSOLE_BACKUP_REQ_DIR` | backend | **〔K1 已落地 2026-10-28〕**備份控制面兩個卷根（容器 `/backup-out` 唯讀、`/backup-req` 可寫；compose 字面常數，不含機密）；**未設＝備份頁顯示「控制面未設定」**（`control.reason=not_configured`），本機 bootRun 保持空即可。其餘 `console.backup.*`（`request-ttl-seconds` 120、`job-max-seconds` 21600、`reconcile-interval-ms` 5000、`overdue-grace-minutes` 30、`min-full-interval-seconds` 86400、`min-diff-interval-seconds` 3600）為 `application.yml` 預設、不經環境變數 |
| `BRIDGE_HOST`／`BRIDGE_PORT`／`ENGINE_WORKSPACE`／`AUTOCLAUDE_ROOT`／`SDD_ROOT` | Bridge | 預設 `127.0.0.1`（Docker CMD 另帶 `0.0.0.0`）、8081、`engine-bridge/.workspace`、monorepo 內的 `AutoClaude`、`AISDLC_SDD` 下數字最大的版本目錄（以 `engine-bridge/app/settings.py` 為準） |
| `BRIDGE_DB_DSN`／`BRIDGE_DB_SCHEMA` | Bridge | 無 DSN＝純檔案模式；schema 預設 `console`。**Console 需要 Bridge 的 DB 模式**（W7，完整性審查 I-07）：斷點清單與步驟時間軸讀的 `checkpoints`／`execution_steps` 只由 Bridge 寫入，純檔案模式下這兩個畫面會是空的（§12.1 L-12）；本機開發跑 Console 時務必給 Bridge 一個 DSN（上方步驟 2 的指令已帶） |
| `BRIDGE_INSTANCE`／`BRIDGE_STOP_GRACE_SECONDS` | Bridge | 預設 hostname＋pid＋uuid4／30 |
| `BRIDGE_ALLOWED_PATH_ROOTS`／`BRIDGE_OUTBOUND_ALLOWLIST` | Bridge | 路徑 allowlist 以 `os.pathsep` 分隔（POSIX `:`、Windows `;`）；外呼 allowlist 以逗號分隔（§8.3、§8.4） |
| `MINIMAX_API_KEY`／`MINIMAX_BASE_URL`／`MINIMAX_MODEL` | Bridge | 修正腦；`MINIMAX_API_KEY` 只放環境變數，不入 config |
| `NEXT_PUBLIC_API_URL` | frontend | 後端 origin（不含 `/api/v1`）；全棧同源為空 |
| `BRIDGE_RESEARCH_ROOT` | Bridge | **〔ResearchToPRD〕**研究工作區根；預設 **repo 外**（D-28）：Windows `%USERPROFILE%\.autosdd\my-project\`、POSIX `~/.autosdd/my-project/`、Docker `/workspace/my-project`；必須在 `BRIDGE_ALLOWED_PATH_ROOTS` 之下（自動併入允許根），啟動時驗證並於 `GET /health/deep` 的 `research.root` 揭露；根 `.gitignore` 仍加 `/my-project/` |
| `BRIDGE_SCAFFOLD_ROOT` | Bridge | 軌道 B 新專案的父目錄；未設＝軌道 B 停用（`capabilities.scaffoldRoot=null`）；自動併入允許根 |
| `BRIDGE_RESEARCH_WRITE_TOKEN` | Bridge、backend（`console.bridge.research-write-token`） | 研究寫入面權杖（≥32 字元，佔位字串＝啟動失敗；未設＝研究寫入端點 503 `research_write_disabled`）；引擎／FSM／git 子行程環境一律剝除 |
| `BRIDGE_RESEARCH_FETCH_ALLOWLIST` | Bridge | Bridge 原生抓取主機基底（逗號分隔）；預設 `export.arxiv.org,arxiv.org,api.semanticscholar.org,api.github.com,api.stackexchange.com`（D-17）；有效清單＝本變數 ∪ 啟用中的 ADMIN 條目 |
| `BRIDGE_RESEARCH_WEB_ALLOWLIST` | Bridge | headless WebSearch／WebFetch 的 `allowed_domains` 基底；**預設空＝Web 層關閉**（產業層需 ADMIN 明列）；有效清單＝本變數 ∪ 啟用中的 ADMIN 條目 |
| `BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS` | Bridge | 同時 stage run 數；預設 1（額度保守；D-27） |
| `BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS` | Bridge | 寫入 `config_overrides.playbook.step_timeout_seconds`；預設 1200 |
| `BRIDGE_RESEARCH_CLAUDE_COMMAND` | Bridge | `claude.command`；Docker E2E＝`aisdlc-mock-claude` |
| `BRIDGE_RESEARCH_FETCH_MAX_BYTES`／`BRIDGE_RESEARCH_FETCH_TIMEOUT_SECONDS` | Bridge | 單檔位元組上限與逾時；預設 5 MiB／20 s |
| `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | 由 Bridge 寫入每個 stage run 的請求 `env`（非部署變數） | headless `claude -p` 背景等待上限（DEF-200-575）；值＝`BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS`×1000，與步驟牆鐘同源、不另立數字；`_ENV_DENY` 不含它（`security.py:41-50`）；步驟 prompt 另禁背景任務與子代理 |

`docker-compose.yml` 的 engine-bridge 區塊同步加 `BRIDGE_RESEARCH_ROOT: /workspace/my-project`、`BRIDGE_RESEARCH_WRITE_TOKEN: ${BRIDGE_RESEARCH_WRITE_TOKEN:-}`、`BRIDGE_RESEARCH_CLAUDE_COMMAND: aisdlc-mock-claude`；backend 區塊加同名權杖；`.env.example` 只放 `<YOUR_…>`；`BRIDGE_ALLOWED_PATH_ROOTS` 不必改（自動併入）。研究端點需要 `BRIDGE_DB_DSN`（無 DSN＝503 `research_requires_db`，唯一例外是 `GET /research/capabilities`：仍 200、`db:false`〔D-49〕；與純檔案模式的既有說明並存：純檔案模式只適用單獨驗 Bridge）。

## 10. Bridge API 契約（逐字採用；Bridge 開發者同時依此實作）

> **落地差異（主控 2026-10-15 回寫）**：Bridge 已實作，**實際契約以 `engine-bridge/README.md` 與其 `tests/` 為準**；本節為派工時的原始契約。主要差異：狀態前置條件（pause 只收 RUNNING、resume 只收 PAUSED、stop 收 RUNNING／PAUSING／PAUSED、restore 收 PAUSED 或終態，否則 409 `invalid_state`）；`GET …/events` 回裸陣列、SSE `data` 為扁平封包且 PAUSED 不結束串流；`config_overrides` 不收 `storage`／`checkpoint_dir` 等 Bridge 管控鍵（一律忽略並發 `CONFIG_OVERRIDE_IGNORED`）、機密只能走 `env`；`review-request` 事件目前從不發送；ID 皆 UUID、`execution_steps.step_number`＝SSE seq；新增相依 psutil。完整 16 條見 `docs/04_planning/agent_briefs/DOC_CORRECTIONS.md`。

```
GET  /health → {"status":"ok","bridge_instance":"<id>","engines":{"autoclaude":{"ok":true,"version":"…"},"sdd":{"ok":true,"latest":"AISDLC_SDD_v0.30"}}}
POST /autoclaude/runs
  body {"run_id":"<uuid=console execution_runs.id>","project":"…","execution_path":"<abs>",
        "playbook":{version,project,global_goal,global_invariants,tasks[{step_id,name,prompt,command?,expected_output_regex?,evaluator_command?,max_retries?,goal_task_id?}]},
        "config_overrides":{…AutoClaude config.yaml 子集…},"env":{…},"fresh":false}
  → 201 {"run_id","status":"RUNNING","pid","workspace","bridge_instance"}
  → 409 {"code":409,"reason":"advisory_lock_held","holder_run_id"}   → 422 {"code":422,"reason":"…","violations":[…]}
POST /autoclaude/runs/{run_id}:pause  → 202 {"status":"PAUSING"}（下一步驟邊界轉 PAUSED）
POST /autoclaude/runs/{run_id}:resume → 202 {"status":"RUNNING"}
POST /autoclaude/runs/{run_id}:stop   → 202 {"status":"CANCELLING"}（SIGTERM→30s→SIGKILL→CANCELLED）
GET  /autoclaude/runs/{run_id} → {"run_id","status","pid","started_at","completed_at","exit_code","current_step","completed_steps","total_steps","tokens_used","last_event_seq","resources"?}
     resources（W7，D-12）＝{"cpu_percent","rss_bytes","process_count","sampled_at"} 或 null；規格見契約 §3.1.2
GET  /autoclaude/runs/{run_id}/stream?after=<seq>   SSE（亦認 Last-Event-ID）
     每則 `id:<seq>` `event:<log|status|step|token|review-request|alert>` `data:<json>`
     log {seq,ts,level,line}；status {seq,ts,status,reason}；step {seq,ts,step_id,step_number,status:STARTED|COMPLETED|FAILED|RETRYING,attempt}；token {seq,ts,pct,tokens_used}
GET  /autoclaude/runs/{run_id}/events?after=<seq>&limit=<n> → REST 重播（SSE 斷線回補基礎）
GET  /autoclaude/runs/{run_id}/checkpoints → [{"checkpoint_id","name","created_at","step_idx","step_id","is_automatic"}]
POST /autoclaude/runs/{run_id}/restore  body {"checkpoint_id"} → 202
POST /autoclaude/decompose  body {"goal","context","project","max_steps"≤24,"config_overrides"}
  → 200 {"draft_id","goal_hash","reasoning","playbook":{…},"signed_off":false}
  → 422 {"code":422,"gate":"max_steps|cycle|empty_prompt|brain_unsupported|brain_failed","detail"}
POST /autoclaude/decompose/{draft_id}:approve body {"approver":"<非空>"} → {"signed_off":true,"approver","approved_at","playbook"}；approver 空→400
GET  /sdd/version → {"latest":"AISDLC_SDD_v0.30","root":"<abs>"}
GET  /sdd/fsm → {"root":"<版本目錄名>","projects":[{"project","source","current_state","updated_at"}],"errors":["<讀不動的檔名>"…]}（W7 D-16；唯讀，契約 §3.1.3）
GET  /sdd/fsm/{project} → {project,current_state,current_sprint,session_id,updated_at,frozen_stages,decision_trace 尾 5 筆,source,
     human_pending{count,items[]},retry_history{count,last},rtm_coverage}（後三欄 W7 D-16 新增，只增不減）或 404 fsm_not_found／422 fsm_state_unreadable
POST /sdd/compile body {"spec_dir":"<abs>"} → {"tasks":[…PlaybookTask…],"scenario","contracts"} 或 422（spec 未凍結／格式）
```

Bridge 執行狀態：INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING／COMPLETED／FAILED／CANCELLED；**寫進 PG `execution_runs.status` 時只用 PRD 六態**（PAUSING→RUNNING、CANCELLING→RUNNING）。

### 10.1 補充約定（不改上列契約的形狀）

| 約定 | 內容 |
|------|------|
| ID 對映 | `run_id`＝`execution_runs.id`；`checkpoint_id`＝`checkpoints.id`（UUID）；`tasks[].goal_task_id`＝Console 任務 UUID；`tasks[].step_id` 慣例為 `T001…` |
| 消費者 | 唯一消費者是 console-api；瀏覽器不直連 Bridge |
| `review-request` | Bridge 不發送；由 console-api 於本地產生（§6(c).c.4）；若日後 Bridge 發出則原樣轉發 |
| 目錄 | `workspace`＝Bridge 為該 run 配置的目錄；建議以 `config_overrides` 把引擎的 `checkpoint_dir`／`log_dir` 指進 workspace，避免污染專案目錄（實際落點以 W1-B 交卷為準） |
| 狀態前置條件（W1-B 實作） | `:pause` 僅 RUNNING（PAUSING 重送冪等）；`:resume` 僅 PAUSED；`:restore` 僅 PAUSED 或終態；`:stop` 於 RUNNING／PAUSING／PAUSED；不符回 409（`invalid_state`） |
| `env` 不落盤 | `resume`／`restore` 的 body 可選帶 `env`：Bridge 不把請求層 `env`（可能含 `MINIMAX_API_KEY` 等機密）寫進磁碟，重啟後 console-api 須在續跑時重送（契約形狀外的選填欄位） |
| 重複 approve | 對已簽署草案再送 `:approve` 回 409 `already_signed_off`；console-api 視為成功 |
| `alert` 事件 | Bridge 會發（ESCALATION、TOKEN_HALT、LIMIT_RETRY、RESTORE、ENV_LOST 等）；console-api 轉發，並依 §6(d) 另行產生 Console 自己的告警 |
| 時間戳 | ISO-8601 含 offset（UTC），不得為 naive 時間 |
| 錯誤封包 | 400／409／422 皆含 `code` 與 `reason`／`gate`／`violations`；console-api 轉成 PRD §7.2 錯誤格式並逐字保留原因 |
| 深度探針（W5 C-2；`BR-26`；W7 D-17 加 `sdd`） | `GET /health/deep`（免認證）：`git --version`（逾時 5 秒）、`import autoclaude`、workspace 可寫、DB ping（有設 DSN 才做）——**這四項任一失敗＝整體 503**；另有第五項 **`sdd`（W7，只當資訊）**；全過 → 200 `{"status":"ok","checks":{"git":{"ok":true,"version":"…"},"autoclaude":{…},"workspace":{"ok":true},"db":{"ok":true｜null},"sdd":{"ok":true｜null｜false,"latest":"AISDLC_SDD_v0.30"｜null}}}`，前四項任一失敗 → 503 `{"status":"degraded","reason":"…","checks":{…}}`（頂層 `reason` 不含 `sdd`）。`sdd` 三態：`null`＝沒有可用的 SDD 目錄；`true`＝目錄存在且有 `build/reports/fsm` **或**入口文件 `AISDLC_SDD_INIT.md`；`false`＝目錄不存在／不是目錄，或兩者都沒有（空的或掛錯的唯讀掛載）——**判準不能只看 `build/reports/fsm`**：它被 git 忽略，乾淨 clone 沒有（契約 §3.1.1、§6.7.3 Q1）。**`sdd.ok=false` 不觸發 503**（主控裁決 Q4：SDD 是選用引擎，壞了只顯示在 Console 的 SDD 卡〔`GET /engines/sdd` 的 `available=false`〕，不該讓 Agent 可用率下降或誤報告警）。**compose 的 bridge healthcheck 與 console-api 的探測環（預設 `autoclaude.healthCheckPath=/health/deep`，讀取逾時 8 秒）都打它**；Bridge 映像須安裝 `git`（QA DEF-AC-003）**〔ResearchToPRD〕**另有資訊欄 `research`（`{"mode":"local"｜"mock-only","root":…,"db":…,"claude_cli":{…},"gh_cli":{…},"git":{…},"web_layer_enabled":…,"scaffold_templates":[…]}`；**不影響 503 判定**，同 `sdd` 先例；`mode=mock-only`＝Bridge 在容器內、無真 `claude`，UI 停用「啟動深研」，D-29）。 |
| AISDLC_SDD 唯讀查詢（W7 D-16；`BR-13`／`BR-14`） | `GET /sdd/version`、`GET /sdd/fsm`（專案清單）、`GET /sdd/fsm/{project}`；三者全唯讀，**不寫 SDD 目錄、不寫 FSM-STATE**（AISDLC_SDD Rule 9：繞過 `FSMRuntime` 直接讀寫是違反即停機的禁令；ADR-001 D22）。`SDD_ROOT` 無效 → 503 `sdd_unavailable`；`build/reports/fsm` 不存在（乾淨 clone）→ 清單回 200 空陣列。現行 FSM-STATE 的真實結構：`retry_history` 是以重試閘為鍵的映射、`human_pending_tracking` 是單一映射、沒有 RTM 覆蓋鍵——三個新欄位的語意以此為準（契約 §3.1.3）。console-api 經 `GET /api/v1/engines/sdd` 消費（契約 §1.7.1） |
| `X-Trace-Id`（W5 C-12） | console-api 對 Bridge 的每個請求帶此標頭；Bridge 中介層讀取（缺則自產 uuid4）、回應回帶同名標頭、每一行應用日誌帶 `trace_id`。契約 §0.4 第 6 點、§3.1.1 |
| 資源取樣（W7 D-12；`US-M-10`） | `GET /autoclaude/runs/{run_id}` 的回應新增 `resources: {cpu_percent, rss_bytes, process_count, sampled_at} \| null`（只增不減）。Bridge 背景每 5 秒以 psutil 對每個「引擎行程樹存活」的 run 取樣一次，請求路徑只回最近一筆；`cpu_percent`＝行程樹各行程 `cpu_percent` 總和 ÷ 邏輯核心數（整機正規化，小數 1 位）、`rss_bytes`＝RSS 總和；取樣器須跨 tick 持有 `psutil.Process` 物件（否則 CPU 恆為 0.0）。引擎行程不存活（尚未啟動、PAUSED、終態）、尚無第一筆樣本、樣本超過 15 秒未更新時為 null。不含 pid。契約 §3.1.2 |
| 引擎設定檔位置（W7，供 E2E 斷言） | Bridge 為每個 run 把物化後的引擎設定寫成 `<ENGINE_WORKSPACE>/<runId>/config.yaml`（`runner.py` 的 `_materialize`，`RunPaths.config`），引擎以 `--config` 讀它；機密只走 `env`，不進這個檔。契約 §3.4.2、E2E-14 |
| 落地差異 | W1-B 交卷須列出與本節的差異；主控回寫本節與 RTM `BR-*`；回寫前以 Bridge 實作與其 `/openapi.json` 為準 |

### 10.2 SDD 寫入面（improving_115；ADR-XPLAT-016）

> §10.1「AISDLC_SDD 唯讀查詢」列對三個 GET 端點仍成立；本小節只記 Bridge 新增**寫入面**的不變量。HTTP 欄位形狀以契約 v1.5（`API_Contract_P3-6.md`）為準，裁決、證據與白名單見 [ADR-XPLAT-016](../../../docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md)。

| 不變量 | 內容 |
|------|------|
| 寫入只經 CLI | Bridge 以子行程呼叫 `python -m tools.fsm_runtime.fsm_runtime`：cwd＝SDD 版本目錄、`PYTHONPATH`＝版本目錄、`PYTHONDONTWRITEBYTECODE=1`、兩個規則遙測旗標 `0`、`SDD_STATE_DIR=<專案根>/build/reports/fsm`、`SDD_PROJECT=<專案鍵>`、不繼承任何 `BRIDGE_*`；Bridge 原始碼不得開寫 `FSM-STATE-*.yaml`（Rule 9 禁令 #1，AST 測試釘住）；每次呼叫必帶 `--must-exist`（現行 CLI 會替不存在的專案自動建檔） |
| 動詞白名單 | **`:freeze`／`/autoclaude/runs` 的 `sdd` 區塊**：`spec-frozen`（僅經 `POST /sdd/fsm/{project}:freeze`）、`negotiate-enter`、`negotiate-exit --outcome agreed`、`delegate-enter`、`delegate-exit --decision done｜failed`；其餘動詞一律不呼叫。人工閘只有「核准凍結」；談判與委派同步是批次生命週期的自動動作。**〔ResearchToPRD〕研究寫入面**（獨立權杖 `BRIDGE_RESEARCH_WRITE_TOKEN`、獨立端點 `/research/*`，不開放給 `:freeze` 與 `sdd` 區塊）另加：唯一建檔例外 `show`（不帶 `--must-exist`，僅 `POST /research/projects` 與 `:route` 兩個呼叫點）、受限 `transition`、`gate`（SCG_VALIDATION／PR_REVIEW／RTM_VERIFY／RELEASE_READY）、`spec-refreeze`——實作為 `sdd_cli.py` 內**獨立的** `RESEARCH_VERBS`／`_RESEARCH_VERB_FLAGS` 兩張表，既有 `ALLOWED_VERBS` 與 `tests/test_sdd_cli.py` 零改動（D-49）；`resume-from-escalation` **仍不入**；細節與測試鎖見 [ADR-XPLAT-017](../../../docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md) §D2、§5 |
| 權杖 | 兩個寫入入口（`:freeze`、含 `sdd` 區塊的 `POST /autoclaude/runs`）須帶標頭 `X-Bridge-Token`；Bridge 未設 `BRIDGE_SDD_WRITE_TOKEN`＝503 `sdd_write_disabled`、缺或錯＝403 `sdd_write_forbidden`；backend 的屬性是 `console.bridge.sdd-write-token`（未設時 freeze 回 503、execute 不送 `sdd` 並以警告出聲）；`_child_env` 剝除該變數，引擎子行程不持有；佔位字串或短於 32 字元＝兩端啟動即失敗**〔ResearchToPRD〕**研究寫入面另有 `BRIDGE_RESEARCH_WRITE_TOKEN`（backend 屬性 `console.bridge.research-write-token`；未設＝503 `research_write_disabled`、缺或錯＝403 `research_write_forbidden`；規則同上，兩端啟動即失敗）。 |
| 狀態目錄 | `<root>/build/reports/fsm`；`GET /sdd/fsm*` 的 `root` 選填（過 `BRIDGE_ALLOWED_PATH_ROOTS`），不帶＝框架目錄（相容）；進入 Bridge 的專案名一律先過與 SDD `sanitize_component` 一致的鏡像淨化；引擎子行程只帶 `SDD_PROJECT`、不帶 `SDD_STATE_DIR`（繼承自 Bridge 環境的兩者先剝除） |
| 綁定（Console 專案為錨，D-115-14） | 綁定＝`execution_path`（狀態目錄根）＋`sdd_project`（預設＝專案名，由 Bridge 淨化、第一次使用時寫回）；路徑 A 匯入帶選填 `targetProjectId` 併入既有專案；同一 `(execution_path, sdd_project)` 只能綁一個未刪除專案；核准凍結維持專案層端點、不帶 `binding` |
| 凍結綁內容 | `frozen_stages[].spec_doc_digests`（換行正規化後的 UTF-8 文字的 sha256，與 adapter 的 `SddSpec.digest` 逐位元相同）；編譯、匯入、執行前、`resume`／`restore` 皆比對；不吻合＝409 `spec_digest_changed`、未凍結＝422 `spec_not_frozen`；規格出現卻未編成的 AT 不是錯誤（`/sdd/compile` 回 200＋`unmapped_at_ids`，Console 轉警告） |
| 委派同步 | 建立順序＝唯讀預檢→鎖→FSM 寫入→工作區→spawn；終態 COMPLETED 與 CANCELLED⇒`delegate-exit done`（語意＝委派交還控制權，不是「成功」）、引擎升級型 FAILED⇒`failed`，其餘（PAUSED、額度停機、引擎異常、孤兒、Bridge 關閉）不動 FSM；新批次遇 FSM 仍在 AUTOCLAUDE_DELEGATED 時，依 `playbook_ref`（`run:<run_id>`）所指的 run 判定：終態或不存在⇒先 `delegate-exit done`（reason 記 RECLAIMED）再前進，活躍或外來委派⇒409 |
| 失敗之後 | `failed`⇒ESCALATION（阻塞態）；恢復**只有人**（`resume-from-escalation --to IMPLEMENTATION`，R-9.5），Bridge 與 Console 不提供恢復動詞，只顯示狀態與可複製的恢復指令 |
| SI 寫入只落稽核 JSON（SelfImproving PRD §9.3、ADR-SI-03′；**〔P2b 已落地 2026-10-25：`si_audit.py` 獨佔建檔、三個寫入 POST 加 validate、AST 鎖 W5 判準 1′～5′；真容器未實測（V3）〕**；T1：sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13） | Bridge 對 SelfImproving 帳本的寫入**只有一條**：把 console-api 簽好的稽核 JSON **原始位元組**以獨佔建檔（同名不覆寫）寫進稽核目錄 `<BRIDGE_SI_AUDIT_DIR>/<audit_ref>.json`；Bridge **不驗簽、只解外層鍵（`audit_ref`、`subject` 等）而不解 `body`、不開帳本檔、不呼叫任何寫入型 CLI 動詞**（`/si/*` 的子行程只呼叫唯讀的 `export`，以及唯讀預檢 `obs-add --dry-run`）；入帳由主機端 `si decide`／`obs-add`／`obs-close --carrier console --audit-ref` 在寫入鎖內完成；三個寫入端點須帶 `X-Bridge-Token`（`BRIDGE_SI_WRITE_TOKEN`，未設或 `BRIDGE_SI_AUDIT_DIR` 未設＝503 `si_write_disabled`、缺或錯＝403 `si_write_forbidden`；規則同 SDD 權杖，佔位字串或短於 32 字元＝兩端啟動即失敗）；Bridge 原始碼寫入形態開啟 SI 相關路徑只准出現在 `si_audit.py`，且 `si_cli.py` 組出的 argv 動詞只准 `export` 與 `obs-add --dry-run`（同一 AST 測試 `tests/test_si_readonly_lock.py` 釘住；SelfImproving PRD AC-SI-35-1 ②、QA 複審 F-09）；無 DELETE／PUT／PATCH〔訂正（SA 修復棒；SelfImproving PRD v0.10 的 QA 複審 F-12）：原文「不驗簽、不解 `body`」；稽核 JSON 外層加 `audit_ref`、`subject`，Bridge 只解外層鍵以比對 `{id}`，`body` 內一致性由 backend 與 CLI 驗〕 |

### 10.3 SelfImproving 鏡像與寫入載體（**〔P1b 已落地 2026-10-22〕**唯讀鏡像、**〔P2b 已落地 2026-10-25〕**寫入載體；形狀的唯一細節來源＝`docs/01_requirements/SelfImproving_PRD.md` §9.3，本節只是簡表）

Bridge 回 snake_case、backend 轉 camelCase；SI 資料面取不到一律明確失敗、不回空表（PRD AC-SI-32-3）。

| 端點 | 階段 | 說明 | 成功 | 失敗（`reason`） |
|------|------|------|------|-------------------|
| `GET /si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs` | P1b | 查詢參數只有 `since`（整數游標）與 `limit`；Bridge 以子行程呼叫根層 `tools/selfimproving.py export --json --kind <k>`（逾時 15 秒、環境白名單、不繼承任何機密）；`{id}` 為 `PROP-SI-NNN`；backend 回應型別＝單一 `SiExportResponse`（`@JsonValue` 無型別樹，保住缺鍵≠null 與未知鍵透傳）＋`SiKeyNames` 深層欄名對映，**取代** PRD §9.1 C18 列示的四個具型別 DTO（⚖-A；TCS 勘誤 1；契約 `API_Contract_SelfImproving_P1b.md` §0.2） | 200：`schema_rev`、`kind`、`generated_at`、`head_sha`、`items[]`、`next_since`、`truncated`、`ne[]`、`problems[]` | 503 `si_unavailable`（`cause` 九值、先中者定案：`si_root_unset`／`si_script_missing`／`spawn_failed`／`timeout`／`stdout_too_large`／`nonzero_rc`／`bad_json`／`schema_rev_mismatch`／`bad_shape`；契約 §2.3）、404 `si_not_found`（單筆查無）、422 `invalid_request` |
| `POST /si/proposals/{id}:decide` | P2b | 落稽核 JSON（`kind=decide`）；`{id}` 為 `PROP-SI-NNN`，`resume` 為 `RUN-SI-NNN`，且須等於稽核外層 `subject` | 201：`{"audit_ref","stored":true}` | 503 `si_write_disabled`、403 `si_write_forbidden`、409 `si_audit_exists`、422 `invalid_request`、503 `si_unavailable`（稽核落檔 I/O 失敗，§11.1；二審 N-4） |
| `POST /si/observations` | P2b | 落稽核 JSON（`kind=obs-add`） | 同上 | 同上 |
| `POST /si/observations/{id}:close` | P2b | 落稽核 JSON（`kind=obs-close`）；`{id}` 為 `OBS-SI-NNN` 且須等於稽核外層 `subject`（Bridge 只解外層鍵；`body.obs_id` 的一致性由 backend 與 CLI 驗）〔訂正（SA 修復棒；SelfImproving PRD v0.10 的 QA 複審 F-12）：原文「須等於稽核 `body.obs_id`」；Bridge 不解 `body` 無從比對〕 | 同上 | 同上 |
| `POST /si/observations:validate` | P2b | 唯讀預檢（**不需權杖、不落檔**）：請求＝未簽的 `body` 物件；子行程 `obs-add --dry-run --body-file -`（stdin 餵入） | 200：`{"ok","row","row_bytes","row_max_bytes","findings":[{code,detail}]}`（`ok=false` 仍 200） | 503 `si_unavailable`、422 `invalid_request` |

backend 對應 `GET /api/v1/si/**`（JWT；Viewer 以上可讀；逐一代理，連線 2 秒、讀取 20 秒、不重試）與 `POST /api/v1/si/proposals/{id}/decide`、`POST /api/v1/si/observations`、`POST /api/v1/si/observations/{id}/close`、`POST /api/v1/si/observations/validate`（`ADMIN` 且帳號名在 `console.si.deciders`；DB 表 `si_console_writes`）；瀏覽器不直連 Bridge（§10.1 消費者列）。

### 10.4 研究寫入面（ResearchToPRD；ADR-003、ADR-XPLAT-017；形狀細節見 `API_Contract_ResearchToPRD.md` §2）

| 不變量 | 內容 |
|--------|------|
| 唯一寫入者 | Bridge 是 `console.research_*` 唯一寫入者；`ResearchDb` **fail-loud**（與 `BridgeDb` best-effort 相反，`db.py:12-13`）；`BRIDGE_DB_DSN` 未設⇒研究端點 503 `research_requires_db`（唯一例外：能力探針 `GET /research/capabilities` 仍 200、`db:false`；D-49） |
| 持久化協定 | 寫檔（原子 replace，重用 `fsutil.write_text_atomic`；**不新增** `os.replace`／`rename`／`move` 站點）→ outbox 記錄 → DB 交易（資料列＋`research_events`＋`last_event_seq`）→ 標 done；DB 不可用⇒stage run `BLOCKED_DB`＋`research.alert`、退避重試；重啟重放 outbox（自然鍵 UNIQUE 保冪等） |
| FSM 寫入 | 只經 CLI 子行程（`sdd_cli.run_verb`）；研究面動詞表＝ADR-XPLAT-017 §D2（`sdd_cli.py` 內獨立的 `RESEARCH_VERBS` 表，既有 `ALLOWED_VERBS` 零改動）；外環鍵環境 `SDD_ENABLE_AUTO_RECOVERY=0`；Bridge 原始碼不得開寫 `FSM-STATE-*.yaml`（AST 鎖） |
| HUMAN_PENDING 守則 | 外環鍵現態為 HUMAN_PENDING 時，Bridge **不呼叫 `gate SCG_VALIDATION PASS`**（PASS 路徑直接 `transition(HUMAN_PENDING)`，HUMAN_PENDING→HUMAN_PENDING 非合法邊＝rc 1）；人工退回＝`gate SCG_VALIDATION FAIL`（態不動、計數＋1、trace 記 `gate_fail_blocked`）；退回後再審通過只記 DB、未通過仍呼叫 `gate FAIL`（D-50；ADR-XPLAT-017 D6；AST 鎖與暫存狀態目錄負控） |
| ESCALATION 恢復後（D-60） | 引擎的 `resume-from-escalation` 不動 retry 計數（只有 `gate PASS` 與 `spec-frozen` 歸零）⇒ 人工恢復後 `SCG_VALIDATION` 的 `current_count` 仍為 3：至多再得一次審查（PASS 歸零；FAIL 立即再 ESCALATION，歷史列帶引擎的 tamper 字樣，見 §12.1 L-R12）；`iterate` 只跑一輪，迴圈續停以每輪 `gate` 回傳的 `next_state`／`escalated` 為準，Bridge 不自以 `3 − current_count` 判斷；全新預算＝換世代（僅 ADMIN〔D-64〕；`POST …/reinit` 的 `generation:"next"`：`show` 建新鍵〔建檔例外的第三個呼叫點〕、`fsm_generation`＋1、`fsm_project` 改指新鍵、`research_gate_decisions(ABANDON_KEY)`、舊鍵留 ESCALATION；ADR-XPLAT-017 D6） |
| stage run | 內部呼叫 `RunManager`；`execution_path`＝工作區；每步 `maintain_context:false`；不寫 `execution_runs`／`execution_steps`（`db.py:100-114` 的跳過行為）；同時 stage run 數 ≤ `BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS` |
| 對帳 | `:reconcile` 重雜湊檔案對 `research_artifacts`／`research_prd_versions`／`research_sources.raw_sha256`，**只報告不修復**，結果追加 `research_events`（`research.reconcile`） |
| 人工決定 | `approver` 由 console-api 取 JWT subject 轉傳；Bridge 驗非空、非保留字（`bridge`／`agent`／`system`）、長度 1 至 100 且符合 `^[A-Za-z0-9._@-]+$`；沒有任何 Bridge 內程式路徑呼叫 `:approve-baseline`（AST 鎖） |
| allowlist 稽核 | ADMIN 新增／停用 allowlist 條目：Bridge 寫 `research_allowlist_entries`（`added_by`／`disabled_by`＝JWT subject）並回應成功後，console-api 以既有 `AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)` 標註（`audit` 日誌行帶 `action=research.allowlist`、`entity=research_allowlist:<id>`；V6 `audit_log` 列〔每個 `/api/` 寫入請求本就恆一列，含被拒的 401／403／422／429〕的 `entity_type='research_allowlist'`、`entity_id`＝條目 id；不新增欄位、不改 V6、不改 `AuditLoggingFilter`）；**不寫 `research_events`**（該表以 `research_id` 為鍵，allowlist 是全域資源；D-52、D-62(1)） |
| 審查輪列寫入時點 | 輪列只在輪有結果時（前置否決已判，或四維審查卡皆通過驗證並彙整、`gate` 已回傳）與分數列、缺陷列、`research_events` 同一交易一次寫入（`research_review_rounds` append-only，D-57）；取消、中斷、Bridge 重啟、無效輸出一律不寫輪列、不佔 `round_no`、不耗預算；進行中只由 REVIEW stage run（`UNIQUE(research_id, stage, round_no, attempt)`）與 `research.run` 事件表達，`research.review` 只在輪完成時送；`round_no`＝已完成評估的序號，與 FSM `gate` 呼叫一一對應（POST_HUMAN 通過輪除外）；審查結果的寫入順序與崩潰窗口（D-58(b)）：Bridge 在呼叫 `gate` **之前**先把輪結果（聚合分數、四維分數、缺陷、`prd_version_no`、`trigger_kind`）落到 outbox；`gate` 回傳後補 `fsm_gate_result`／`fsm_retry_count`／`verdict`，並在同一交易寫輪列、分數、缺陷、事件；重放 outbox 時先以 FSM `show` 讀 `decision_trace`／`retry_history` 判斷該輪的 `gate` 是否已呼叫（已呼叫＝只補 DB、不重呼叫；未呼叫＝先呼叫再寫），使 `gate` 呼叫與輪列寫入對崩潰冪等（`gate` 已呼叫而 DB 未寫是 D-57 必然留下的窗口）。**例外（D-59(5)）**：POST_HUMAN 通過輪依設計不呼叫 `gate`（D-50），重放時不得套「未呼叫就補呼叫」（否則在 HUMAN_PENDING 送出非法的 `gate PASS`），該輪只補 DB。 |
| 無效審查輸出 | `REVIEW_INVALID`（審查者輸出重試一次後仍不合 schema，evaluator 無法評分）：**不寫 `research_review_rounds` 列、不佔 `round_no`**，只記 REVIEW stage run（`status=FAILED`、`exit_reason=review_invalid`）與事件 `research.review_invalid`；不呼叫 FSM gate、不耗預算；重新審查沿用同一輪號（`attempt`＋1；D-55） |
| FSM 視圖 | `GET /api/v1/research/projects/{id}/fsm`（API-RP-13）轉 Bridge `GET /sdd/fsm/{key}?root=`，回 `ResearchFsmViewDto`＝既有 `SddFsmState` 原樣、只增不減，另加 `retryHistory.gates`（各閘 `currentCount`＝FSM 檔該閘 `current_count`、`entries`＝該閘 `history` 筆數；既有 `retryHistory.count`／`last` 不動）與 `humanReturnCount`（整數：目前 `fsm_generation` 內 `research_gate_decisions` 中 `gate=GATE0`、`decision=CHANGES` 的筆數，console-api 讀 DB 計得）；各閘分項由 Bridge 在 `GET /sdd/fsm/{key}` 的投影新增同級鍵 `retry_gates`（additive；既有 `retry_history`＝`{count,last}` 與其測試不動）；供 UI 做 FR-R2P-08 邊界條件的「第 n 輪 vs retry_history」對照（D-59(4)） |
| 內環 | 不變：`POST /autoclaude/runs`（含 `sdd`）、`POST /sdd/compile`、`POST /sdd/fsm/{project}:freeze`（Stage-2）；Gate 0 專用 `:approve-baseline` 與 `:freeze` 並存 |

Bridge 端點表（僅 console-api 呼叫；寫入端須 `X-Bridge-Token`）：

| 端點 | 期 | 成功 | 失敗（`reason`） |
|------|----|------|-----------------|
| `GET /research/capabilities` | P0 | 200 | — |
| `POST /research/projects` | P0 | 201 | 503 `research_write_disabled`／`research_requires_db`；403 `research_write_forbidden`；409 `slug_in_use`；422 |
| `POST /research/projects/{id}/stages/{stage}:start` | P0（`research/draft/review/revise/iterate`）、P1（`tcs-draft`） | 202 `{stageRunId}` | 409 `stage_conflict`／`fsm_state_conflict`／`escalated`；503 `db_blocked` |
| `PUT /research/projects/{id}/prd` | P0 | 201 新版 | 409 `prd_version_conflict`／`spec_frozen` |
| `POST /research/projects/{id}:approve-baseline`、`:return` | P0 | 200 | 409 `fsm_state_conflict`／`spec_digest_changed`／`review_not_passed`／`escalated`；422 `sanitization_failed` |
| `POST /research/projects/{id}:route-preview`、`:route` | P1 | 200／202 | 409 `route_conflict`／`branch_exists`；422 `target_not_empty`／`public_confirmation_required`／`route_unsupported_in_deployment`；502 `route_step_failed`（帶 `failureStep`） |
| `POST /research/projects/{id}:scr` | P1 | 202／201 | 409 `scr_limit`／`scr_open` |
| `POST /research/projects/{id}:gates`、`:tag`、`:pr` | P2 | 200／201 | 409 `tag_exists`；422 |
| `POST /research/projects/{id}:cancel`、`:reconcile`、`:reinit`、`:archive`、`:restore` | P0 | 200 | 404 `research_not_found`；`:reinit` 的換世代模式另有 409 `fsm_state_conflict`（現態非 ESCALATION*）、422（缺理由） |
| `GET／POST /research/allowlist`、`PATCH /research/allowlist/{id}` | P0 | 200／201 | 422 `terms_ack_required` |
| `GET /research/projects/{id}/events?after=`、`/stream` | P0 | 200／SSE | 404 |

## 11. 後端 API

### 11.1 端點與狀態碼語意

端點表以 **PRD §7.1.1～§7.1.8 為 SSOT**，本文不重抄。補充端點（PRD 缺口，ADR-001 G-16／G-17）：`POST /api/v1/auth/login`、`/api/v1/auth/refresh`、`GET /actuator/health`、`GET /actuator/prometheus`、`GET /api/v1/projects/{projectId}/executions`（列出專案執行批次，`API-EXE-14`）、`GET /api/v1/notifications/summary`（`API-NTF-01`，回 `NotificationSummaryResponse{pendingSignoffs, pendingReviews, unacknowledgedAlerts}`，供頂列通知鈴與 signoff 佇列徽章）；監控端點補充查詢參數 `runId`、`from`、`to`（對應設計稿「執行批次」「時間範圍」選單）。W5（契約 v1.2）再增補：`GET /api/v1/monitor/task-totals`（全域任務總計，`API-MON-08`，儀表板「本週完成」用，取代前端對各專案扇出 `task-trend`）、`POST /api/v1/projects/{id}/restore` 與 `GET /api/v1/projects?deleted=true`（軟刪除復原，`API-PRJ-06`，ADR-001 D19）。W7（契約 v1.4）再增補三條：`GET /api/v1/engines/sdd`（AISDLC_SDD 引擎狀態，`API-ENG-01`；Bridge 不可達也回 200、以 `available`／`reason` 表達，ADR-001 D22）、`GET /api/v1/signoffs/pending`（待審批清單，`API-SGN-05`；與通知摘要的 `pendingSignoffs` 同一判準，`counts.total` 恆等於它）、`POST /api/v1/auth/logout`（登出並撤銷 refresh token，`API-AUTH-03`，免認證、一律 204，ADR-001 D16／D23）。**〔SysAdminBackup K1 已落地 2026-10-28〕**再增補 `GET /api/v1/sysadmin/backups`（備份總覽，`API-BK-01`）、`GET …/backups/jobs`（工作紀錄分頁，`API-BK-02`）、`GET …/backups/jobs/{id}`（`API-BK-03`）、`POST …/backups/jobs`（手動觸發，`API-BK-04`；202）；OpenAPI 77 路徑／89 操作（`OpenApiIT`）；形狀以 `docs/02_architecture/API_Contract_SysAdminBackup.md` 為準。回應格式依 PRD §7.2。狀態碼語意：

| 碼 | 語意 |
|----|------|
| 400 | 驗證失敗；`approver` 缺漏或空白；halt ≤ compact；goal 依賴成環／自依賴／跨專案；黑名單字元命中 |
| 401／403 | 未認證／角色不足 |
| 404 | 資源不存在或已軟刪除 |
| 409 | 草案未 signoff 即執行／resume／restore；EXECUTING 專案受限操作；非法狀態轉移；並發互斥（Bridge 409）；import 未 signoff 即 confirm；Bridge 草案失效；專案有進行中批次時刪除其目標／任務（`project_executing`）；專案復原前提不符（`project_not_deleted`、`restore_window_expired`）（W5） |
| 422 | Bridge 有界閘或消毒拒絕（結構化原因逐字帶出） |
| 502／504 | Bridge 不可達／逾時（建立執行失敗已補償刪除 run 列） |

**SelfImproving 相關的 `reason`**（〔P1b 已落地 2026-10-22／P2b 已落地 2026-10-25〕；SelfImproving PRD §9.3；多由 Bridge 產生、backend 逐字轉出，`si_decision_duplicate` 由 backend 自產〔2026-10-31 增量，鍵 `agentconsole-si-decide-dedupe`〕；T1：sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d` line 13）：

| HTTP | `reason` | 何時 |
|------|----------|------|
| 503 | `si_unavailable` | `SI_ROOT` 未設或不含 `tools/selfimproving.py`、子行程逾時／rc 非 0／stdout 非單一合法 JSON、`schema_rev` 不符（P1b；`detail`＝`rc=<n>; stderr=<末 1,000 字元>`，不得顯示空表）；〔P2b 已落地 2026-10-25〕稽核 JSON 落檔的 I/O 失敗（EACCES／ENOSPC 等）亦回本碼，`detail` 帶 errno（SelfImproving PRD v0.10 QA 複審 P4-6） |
| 404 | `si_not_found` | `GET /si/proposals/{id}` 查無（P1b） |
| 503 | `si_write_disabled` | Bridge 未設 `BRIDGE_SI_WRITE_TOKEN` 或 `BRIDGE_SI_AUDIT_DIR`（P2b；沿 `sdd_write_disabled` 體例） |
| 403 | `si_write_forbidden` | 缺或錯 `X-Bridge-Token`（Bridge）；或 backend 端帳號不在 `console.si.deciders`（P2b；角色不足者先被 `SecurityConfig` 擋成一般 403） |
| 409 | `si_audit_exists` | 稽核目錄已有同名 `<audit_ref>.json`（P2b；不覆寫） |
| 409 | `si_decision_duplicate` | 同一卡（`subject`＋`digest`）同一個帶 digest 的決定動詞已有稽核列（不論是否已入帳；`rollback`／`unblock`／`resume` 無 digest 不受閘）；backend 在取 `audit_ref`／簽章／INSERT 之前擋、零副作用；`details`＝`existingAuditRef`、`dkind`、`subject`、`digest8`（增量 2026-10-31；TCS-SelfImprovingDecideDedupe W-D1、契約 §8） |
| 422 | `invalid_request` | `{id}` 或 `audit_ref` 形態不符、`{id}` 與稽核外層 `subject` 不符、`kind` 與端點不符、請求非單一 JSON 物件或超過 64KB、`schema_rev` 不符（P1b／P2b） |

**系統管理／資料庫備份的 `reason`**（〔K1 已落地 2026-10-28〕；TCS-SysAdminBackup §C4；不進 `lib/api/reasons.ts`，前端 `BACKUP_REASONS`、backend `ErrorReasons` 的 `BACKUP_` 五常數與契約表三方雙向鎖）：

| HTTP | `reason` | 何時 |
|------|----------|------|
| 503 | `backup_control_unavailable` | 目錄未設定（`not_configured`）、心跳過期、匯出檔不可讀或 schema 不符、資料庫讀取失敗、寫請求檔失敗（該列已補償為 FAILED） |
| 400 | `backup_confirm_required` | POST 缺 `confirm:true`（JSON 布林；字串 "true"、數字 1 不算） |
| 409 | `backup_job_in_progress` | 已有 QUEUED 或 RUNNING 的工作（含部分唯一索引衝突） |
| 409 | `backup_too_frequent` | 距上一份同類備份過近（`details.type`、`details.nextAllowedAt`；full 86400 秒、diff 3600 秒、verify 不設） |
| 404 | `backup_job_not_found` | 單筆工作不存在或 id 不是 UUID |
| 422 | `invalid_request` | `limit` 不在 1..100、`before` 非 ISO-8601、`type` 不是 full／diff／verify（區域常數，不入契約表） |

**〔ResearchToPRD 增補〕研究端點（`API_Contract_ResearchToPRD.md` 為 SSOT；本表是簡表）**

| 端點 | 角色 | 成功 | 備註 |
|------|------|------|------|
| `GET /api/v1/research/capabilities` | V+ | 200 | 轉 Bridge，快取 30 s；無 DSN 仍 200（`db:false`，503 規則的唯一例外；D-49） |
| `GET／POST /api/v1/research/projects`、`GET …/{id}` | V+／O+／V+ | 200／201／200 | `{id}` 回 `flow`（`steps[]`、`currentStep`、`furthestStep`、`effective` 相態）；`AuditTrail.note("research.create",…)` |
| `GET …/{id}/events?afterSeq=&limit=`、`GET /api/v1/stream/research/{id}` | V+ | 200／SSE | `Last-Event-ID`；與 `StreamController` 同款背壓 |
| `GET …/{id}/sources｜evidence｜prd/versions｜prd/versions/{n}｜review-rounds｜review-rounds/{n}｜fsm｜route｜scr｜decomposition｜delivery｜records/audit` | V+ | 200 | 純讀 DB（`fsm`＝轉 Bridge `GET /sdd/fsm/{key}?root=`，另回 `retryHistory.gates` 與 `humanReturnCount`；D-59(4)） |
| `PUT …/{id}/prd` | O+ | 201 | 樂觀鎖 `baseVersion` |
| `POST …/{id}/stages/{stage}` | O+ | 202 | `stage` 列舉；`afterEscalation` |
| `POST …/{id}/approve`、`POST …/{id}/return` | **ADMIN** | 200 | Gate 0；`approver`＝JWT subject（不收請求內 approver） |
| `POST …/{id}/route/preview` | O+ | 200 | 零副作用 |
| `POST …/{id}/route`、`…/gates`、`…/delivery/tag`、`…/delivery/pr` | **ADMIN** | 202／200／201 | P1／P2 |
| `POST …/{id}/scr`、`…/cancel`、`…/reconcile`、`…/reinit`（重試初始化）、`…/archive`、`…/restore` | O+ | 200／202 | `reinit`（不帶 `generation`）只在 `flow_status=FAILED` 且 `flow_detail` 以 `init_failed:` 起頭時可呼叫，其餘 409 `stage_conflict`（`details.flowStatus`／`flowDetail`）、零寫入（D-65） |
| `POST …/{id}/reinit` 帶 `generation:"next"`（換世代） | **ADMIN**（由 `ResearchCommandService` 檢查；matcher 無法依本文分流，D-64） | 200 | D-60；FSM 現態須為 ESCALATION*、理由必填；VIEWER 回 403 `ACCESS_DENIED`（授權鏈）、OPERATOR 回 403 `research_write_forbidden`（服務層），兩者 Bridge 請求數 0 |
| `GET／POST /api/v1/research/allowlist`、`PATCH …/{id}` | V+／**ADMIN**／**ADMIN** | 200／201／200 | D-17 |

`OpenApiIT` 的 `EXPECTED` 路徑／操作計數、`schema.d.ts`、`ErrorResponseDocumentation`（先例 `:49`、`:141`）同 commit 更新；計數以當下實測為準。**研究 `reason`**（雙向鎖：前端 `lib/api/reasons.ts` 或區域常數、backend `ErrorReasons`、契約表）：`research_write_disabled`(503)、`research_write_forbidden`(403)、`research_requires_db`(503)、`db_blocked`(503)、`research_not_found`(404)、`slug_in_use`(409)、`stage_conflict`(409)、`prd_version_conflict`(409)、`review_not_passed`(409)、`spec_digest_changed`(409)、`fsm_state_conflict`(409)、`escalated`(409)、`spec_frozen`(409)、`route_conflict`(409)、`branch_exists`(409)、`scr_open`(409)、`scr_limit`(409)、`decomposition_stale`(409)、`tag_exists`(409)、`layer_unavailable`(400)、`sanitization_failed`(422)、`target_not_empty`(422)、`public_confirmation_required`(422)、`route_unsupported_in_deployment`(422)、`terms_ack_required`(422)。

### 11.2 DTO 欄位表（camelCase；取自 PRD §5／§6）

圖例：`C`＝CreateRequest、`U`＝UpdateRequest、`R`＝建立／更新後的 `XxxResponse`（＝Detail 去掉關聯清單）、`S`＝Summary、`D`＝Detail；`●`有、`●*`必填、`—`無。

**Project**（`CreateProjectRequest`／`UpdateProjectRequest`／`ProjectResponse`／`ProjectSummaryResponse`／`ProjectDetailResponse`）

| 欄位 | 型別 | C | U | R | S | D | 規則 |
|------|------|---|---|---|---|---|------|
| id | UUID | — | — | ● | ● | ● | 自動 |
| name | String(200) | ●* | ● | ● | ● | ● | NotBlank |
| executionPath | String(500) | ●* | ● | ● | ● | ● | 絕對路徑；EXECUTING 時不可改 |
| passCriteria | String(Markdown) | ●* | ● | ● | — | ● | NotBlank |
| description | String(Markdown) | ● | ● | ● | — | ● | |
| status | ProjectStatus | — | — | ● | ● | ● | DRAFT／READY／EXECUTING／COMPLETED／FAILED／ARCHIVED；轉移依附錄 B.1 |
| autonomyLevel | Integer | ● | ● | ● | ● | ● | 1～10，預設 3 |
| draft | Boolean | ● | — | — | — | — | 預設 false；true → signedOff=false（W2-A 任務書未列，W3 後端補） |
| signedOff | Boolean | — | — | ● | ● | ● | 手動建立 true |
| signedOffBy／signedOffAt | String／Instant | — | — | ● | — | ● | signoff 不可匿名 |
| goalsCount／tasksCount／tasksDone | Integer | — | — | ● | ● | ● | 僅算未軟刪 |
| goals | List<GoalBrief> | — | — | — | — | ● | `{id,name,status,sortOrder,signedOff,taskCount,completedTaskCount}` |
| createdAt／updatedAt／createdBy | Instant／Instant／String | — | — | ● | updatedAt | ● | createdBy＝JWT subject |
| deletedAt | Instant | — | — | — | ● | — | W5（V9，主控裁決 C-3）：軟刪除時間；只有 `GET /projects?deleted=true` 的列表項帶值，其餘缺席 |

**Goal**（`CreateGoalRequest`／`UpdateGoalRequest`／`GoalResponse`／`GoalSummaryResponse`／`GoalDetailResponse`／`ReorderRequest{projectId, orderedGoalIds[]}`）

| 欄位 | 型別 | C | U | R | S | D | 規則 |
|------|------|---|---|---|---|---|------|
| id、projectId | UUID | 路徑 | — | ● | ● | ● | projectId 取自路徑 |
| name | String(200) | ●* | ● | ● | ● | ● | NotBlank |
| description／passCriteria | String(Markdown) | ●／●* | ● | ● | — | ● | passCriteria 必填 |
| sortOrder | Integer | — | ● | ● | ● | ● | 建立時排末；批次重排走 reorder |
| status | GoalStatus | — | — | ● | ● | ● | PENDING／IN_PROGRESS／COMPLETED／FAILED／SKIPPED；附錄 B.2 |
| dependsOn | List<UUID> | ● | ● | — | — | ● | 寫入 `goal_dependencies`；Kahn 防環；自依賴／跨專案 → 400 |
| draft | Boolean | ● | — | — | — | — | 同 Project |
| signedOff／signedOffBy／signedOffAt | Boolean／String／Instant | — | — | ● | signedOff | ● | |
| taskCount／completedTaskCount／completionRatio | Integer／Integer／Double | — | — | — | ● | ● | 僅算未軟刪 |
| tasks | List<TaskBrief> | — | — | — | — | ● | `{id,name,status,sortOrder,retryCount,maxRetries,signedOff}` |
| createdAt／updatedAt | Instant | — | — | ● | — | ● | |

**Task**（`CreateTaskRequest`／`UpdateTaskRequest`／`TaskResponse`／`TaskSummaryResponse`／`TaskDetailResponse`）

| 欄位 | 型別 | C | U | R | S | D | 規則 |
|------|------|---|---|---|---|---|------|
| id、goalId | UUID | 路徑 | — | ● | ● | ● | goalId 取自路徑 |
| name | String(200) | ●* | ● | ● | ● | ● | NotBlank |
| description／passCriteria | String(Markdown) | ●／●* | ● | ● | — | ● | |
| evaluatorCommand | String(1000) | ● | ● | ● | — | ● | NFR-SEC-03；命中黑名單 → 400 列出違規字元 |
| expectedOutputRegex | String(1000) | ● | ● | ● | — | ● | 須可 `Pattern.compile`，否則 400 |
| passCriteriaSpec | JSON | ● | ● | ● | — | ● | 結構化通過標準 |
| sortOrder | Integer | — | ● | ● | ● | ● | |
| status | TaskStatus | — | — | ● | ● | ● | 11 態；附錄 B.3 |
| estimatedTokens／actualTokens | Long | ●／— | ●／— | ● | ● | ● | actual 由事件寫入 |
| retryCount／maxRetries | Integer | —／● | —／● | ● | ● | ● | maxRetries 預設 3 |
| assignedAgent | String | — | — | ● | — | ● | 執行時填 |
| executionLog | Text | — | — | — | — | ● | 最近一次執行日誌 |
| executionHistory | List<ExecutionStepBrief> | — | — | — | — | ● | 由 `execution_steps` 依 `task_id` 衍生（US-T-02「執行歷史」）；Phase 2 為空清單，Phase 4（W3-B2）起為真資料：跨批次、時間升冪、最多最近 200 筆，`tokensUsed` 只在 COMPLETED／FAILED 列 |
| draft | Boolean | ● | — | — | — | — | 同 Project |
| signedOff／signedOffBy／signedOffAt | Boolean／String／Instant | — | — | ● | signedOff | ● | |
| createdAt／updatedAt／startedAt／completedAt | Instant | — | — | ● | updatedAt | ● | |

**ImportRecord**

| DTO | 欄位 |
|-----|------|
| upload（multipart） | `file`（`.md／.pdf／.docx`，≤10MB） |
| `TextImportRequest` | `content`●*、`sourceFileName`●、`sourceType`●（預設 PLAIN_TEXT） |
| `ParseOptions` | `autonomyLevel`●（1～10，預設 3）、`executionPath`●、`additionalPrompt`●、`specDir`● |
| `EditParsedResultRequest` | `parsedResult`●*（三層樹 JSON） |
| `SignoffRequest` | `approver`●*（非空；用於所有 signoff 端點） |
| `ImportRecordResponse` | `id, sourceType, sourceFileName, status, signedOff, signedOffBy, signedOffAt, projectId, createdAt, aiModel, tokenUsed`（列表不含 `sourceContent`、`parsedResult`） |
| `ImportRecordDetailResponse`（`GET /import/{id}`） | `ImportRecordResponse` 全部欄位＋`parsePath, lastParseErrors, sourceContent, parsedResult`；W5（V8，主控裁決 C-10）另帶 `warnings[]`（最近一次成功 parse／PUT result 的解析提示，永遠出現）與 `parseOptions`（最近一次 parse 請求的選項，可 null） |
| `ParseResultResponse` | `importId, status, parsedResult, signedOff(=false), aiModel, tokenUsed, reasoning?, errors?[{gate,detail}]` |

**ExecutionRun**

| DTO | 欄位 |
|-----|------|
| `StartExecutionRequest` | `autonomyLevel`●*（1～10）、`tokenBudget`●（Long ≥1）、`scope`●*`{mode: ALL／SELECTED, goalIds[], taskIds[], limits{taskTokens?, goalTokens?}}` |
| `ExecutionRunResponse` | `id, projectId, runNumber, status(6 態), autonomyLevel, scope, totalTokensUsed, tokenBudget, startedAt, completedAt`；W7（契約 v1.3，D-11）另帶 `engineCapabilities{autoMutation, selfEvolution}`（`ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`；V10 之前的批次缺席） |
| `ExecutionRunDetailResponse` | 上列＋`currentStep, completedSteps, totalSteps, lastEventSeq, pendingReviews[{id,kind,stepId,taskId,goalId,reason,requestedAt}], bridge{connected,instance,status,runKnown,checkedAt,resources}`（不含 pid、lock key）；W7（D-12）`bridge.resources{cpuPercent,memoryBytes,processCount,sampledAt}` 可為 null（行程不存活、尚無樣本、樣本過期、Bridge 不可達） |
| `ExecutionStepResponse` | `id, runId, taskId, stepNumber, action, status, tokensUsed, errorMessage, output, timestamp` |
| `DagResponse` | `nodes[{id,kind(GOAL／TASK),label,status,goalId?}]`、`edges[{from,to}]` |
| `CheckpointResponse` | `id, runId, name, createdAt, isAutomatic, stepIdx?, stepId?`（不含 `stateSnapshot`） |
| `ReviewRequest` | `decision`●*（APPROVE／REJECT／RETRY／SKIP）、`comment`● |

**Engines／Signoffs／Auth（W7，契約 v1.4）**

| DTO | 欄位 |
|-----|------|
| `SddEngineStatusResponse`（`GET /engines/sdd?project=`） | `available, reason?, version?{latest,root}, projects[{project,source,currentState,updatedAt}], fsm?, checkedAt`；`fsm`＝`{project,currentState,currentSprint,sessionId,updatedAt,frozenStages[],decisionTrace[≤5],source,humanPending{count,items[]},retryHistory{count,last},rtmCoverage}`（最外層 camelCase、巢狀內容原樣＝保留 FSM 檔的 snake_case 鍵）；`reason` 是**回應欄位**（`bridge_unreachable`／`sdd_unavailable`／`bridge_error`／`fsm_not_found`／`fsm_state_unreadable`），不是 `ApiError.reason`（契約附錄 B.4） |
| `PendingSignoffsResponse`（`GET /signoffs/pending?limit=`） | `counts{projects,goals,tasks,imports,total}`、`items[{kind,id,projectId?,projectName?,parentId?,title,createdAt}]`；`kind`＝PROJECT／GOAL／TASK／IMPORT；**IMPORT 項的 `projectId`／`projectName`／`parentId` 為 null**（`confirm` 之前沒有專案）；`limit` 預設 50、上限 200，只截斷 `items` |
| `LogoutRequest`（`POST /auth/logout`） | `refreshToken`●*（NotBlank）；回 204 |

**SystemConfig**

| DTO | 欄位 |
|-----|------|
| `ConfigResponse` | `id, category, key, value, valueType, defaultValue, description, isEncrypted, validationRule, updatedAt, updatedBy`；`isEncrypted=true` 時 `value` 為 `••••••••`，Admin 以查詢參數 `reveal=true` 揭露（寫審計；補充於 `API-SET-01／02`） |
| `UpdateConfigRequest` | `value`●*、`confirm`●（敏感參數須 `true`，否則 409） |
| `TokenGuardRequest` | `compactThresholdPct`●*、`haltThresholdPct`●*（1～100；halt > compact） |
| `ConnectionTestResponse` | `success, latencyMs, message, resolvedHost` |
| `ConfigHistoryResponse` | `id, configId, category, key, oldValue, newValue, changedAt, changedBy`（敏感值遮罩） |
| 匯出／`ImportSettingsResponse` | 匯出 `{version, exportedAt, configs[{category,key,value}]}`（不含敏感值）；匯入回 `applied, skipped, errors[{category,key,reason}]` |

### 11.3 DDL 增補（PRD §6.2 缺口；ADR-001 D5）

```sql
-- V3__review_requests.sql（Phase 4）
CREATE TABLE console.review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES console.execution_runs(id),
    step_id UUID REFERENCES console.execution_steps(id),
    task_id UUID REFERENCES console.tasks(id),
    goal_id UUID REFERENCES console.goals(id),
    kind VARCHAR(20) NOT NULL
        CHECK (kind IN ('TASK_CONFIRM','GOAL_CONFIRM','GOAL_COMPLETED','ESCALATED')),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','APPROVED','REJECTED','RETRIED','SKIPPED')),
    reason TEXT,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decided_by VARCHAR(100),
    decided_at TIMESTAMP WITH TIME ZONE,
    comment TEXT
);
CREATE INDEX idx_review_requests_run_status ON console.review_requests(run_id, status);

-- V4__monitor_alerts.sql（Phase 5）
CREATE TABLE console.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES console.projects(id),
    run_id UUID REFERENCES console.execution_runs(id),
    rule VARCHAR(40) NOT NULL,   -- TOKEN_BUDGET_WARNING／TOKEN_BUDGET_EXCEEDED／CONSECUTIVE_FAILURES／AGENT_UNRESPONSIVE／TASK_DURATION_EXCEEDED／HIGH_RETRY_RATE
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('WARNING','CRITICAL')),
    subject VARCHAR(100),
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_alerts_project_ack ON console.alerts(project_id, acknowledged);

-- V5～V7 的欄位與表見契約 API_Contract_P3-6.md §0.5；W5（契約 v1.2）再增補 V8、V9，W7（契約 v1.3）增補 V10：
-- V8__import_record_warnings_and_options.sql（主控裁決 C-10）
ALTER TABLE console.import_records
    ADD COLUMN warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN parse_options JSONB;

-- V9__soft_delete_timestamps.sql（主控裁決 C-3；ADR-001 D19）
ALTER TABLE console.projects ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE,
                             ADD COLUMN status_before_delete VARCHAR(20);
ALTER TABLE console.goals ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE console.tasks ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- V10__execution_run_engine_capabilities.sql（W7；主控裁決 D-11；ADR-001 D20）
ALTER TABLE console.execution_runs ADD COLUMN engine_capabilities JSONB;   -- NULL＝V10 之前建立的批次
-- 同一支遷移另以 UPDATE 校正 system_configs.impact_note 的三個鍵（model.enableKernelBrain、agent.enableAutoMutation、
-- agent.enableSelfEvolution），文字逐字取自契約附錄 C.1／C.2
```

### 11.3′ 研究到規格 DDL（V16～V19；〔ResearchToPRD W0 增補 2026-11-02〕）

**K.1　`V16__research_core.sql`**
```sql
-- V16__research_core.sql — ResearchToPRD P0：研究專案（流程脊游標）、事件帳、stage run、檔案登記
-- 寫入者唯一＝engine-bridge（Architecture §7.2）；console-api 只讀（JDBC，無 JPA 實體，ddl-auto=validate 不檢查本表；先例 V13／V15）。
-- 人工決定的「誰對哪個實體做了請求」由既有 V6 audit_log 記；內容住 V18 research_gate_decisions。
CREATE SEQUENCE console.research_rp_seq START 1;

CREATE FUNCTION console.research_next_rp_no() RETURNS text LANGUAGE sql AS
$$ SELECT 'RP-' || lpad(n::text, GREATEST(4, length(n::text)), '0') FROM (SELECT nextval('console.research_rp_seq') AS n) s $$;   -- 超過 4 位數不截斷

CREATE TABLE console.research_projects (
    id UUID PRIMARY KEY,                                   -- console-api 配號（同 execution_runs.id 先例）
    rp_no VARCHAR(12) NOT NULL UNIQUE DEFAULT console.research_next_rp_no() CHECK (rp_no ~ '^RP-[0-9]{4,}$'),   -- 顯示編號（D-37）
    slug VARCHAR(30) NOT NULL CHECK (slug ~ '^[a-z0-9][a-z0-9-]{0,29}$'),
    title VARCHAR(200) NOT NULL,
    topic TEXT NOT NULL CHECK (char_length(topic) <= 500),
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,              -- issue_scope.json 的鏡像：技術棧、層開關、檢索邊界
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    depth_level VARCHAR(10) NOT NULL DEFAULT 'STANDARD' CHECK (depth_level IN ('QUICK','STANDARD','DEEP')),
    target_scope VARCHAR(20) NOT NULL DEFAULT 'UNDECIDED'
        CHECK (target_scope IN ('UNDECIDED','AISDLC_MODULE','STANDALONE_PROJECT')),
    workspace_path VARCHAR(500) NOT NULL,                  -- <BRIDGE_RESEARCH_ROOT>/<slug>（絕對路徑；預設 repo 外，D-28）
    fsm_project VARCHAR(100) NOT NULL,                     -- 外環鍵 research-<slug>[-g<N>]
    fsm_state_dir VARCHAR(500) NOT NULL,                   -- <workspace>/build/reports/fsm
    fsm_generation INTEGER NOT NULL DEFAULT 1 CHECK (fsm_generation >= 1),
    -- 流程脊游標（Bridge 與引擎動作同一交易寫入；步驟 3 之後的相態為衍生，不落此欄）
    flow_step VARCHAR(10) NOT NULL DEFAULT 'topic' CHECK (flow_step IN ('topic','studio','route','build','deliver')),
    flow_phase VARCHAR(20) NOT NULL DEFAULT 'INGESTED' CHECK (flow_phase IN (
        'INGESTED','RESEARCHING','EVIDENCE_READY','DRAFTING','REVIEWING','REVISING','GATE0_PENDING','FROZEN',
        'ROUTING','ROUTED','TCS_DRAFTING','TCS_PENDING','SCR_OPEN')),
    flow_status VARCHAR(14) NOT NULL DEFAULT 'IDLE' CHECK (flow_status IN (
        'IDLE','RUNNING','WAITING_HUMAN','BLOCKED','ESCALATED','FAILED','CANCELLED','COMPLETED')),
    flow_detail VARCHAR(300) NOT NULL DEFAULT '',
    console_project_id UUID REFERENCES console.projects(id),   -- 分流後綁定的 Console 專案（console-api 先建、Bridge 後填；D-37）
    parent_research_id UUID REFERENCES console.research_projects(id),   -- 大型 SCR 的前身
    last_event_seq BIGINT NOT NULL DEFAULT 0,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE
);
CREATE UNIQUE INDEX ux_research_projects_slug_active ON console.research_projects (slug) WHERE archived_at IS NULL;
CREATE UNIQUE INDEX ux_research_projects_console_project ON console.research_projects (console_project_id) WHERE console_project_id IS NOT NULL;
CREATE INDEX idx_research_projects_flow ON console.research_projects (flow_step, flow_status) WHERE archived_at IS NULL;

-- 共用的 append-only 守衛（V13 si_console_writes_guard 的泛化：任何 UPDATE／DELETE 一律拒絕）
CREATE FUNCTION console.research_append_only_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    RAISE EXCEPTION '% 為 append-only（不可改、不可刪）', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

-- 受控可更新表的通用守衛（D-49）：表名→允許更新欄位清單；清單外欄位的 UPDATE 與任何 DELETE 一律拒絕（更正＝追加新列）。
-- 全部 18 張 research_* 表不是掛 research_append_only_guard() 就是掛本函式，所以沒有任何一張表可被 DELETE；兩者拒絕時一律 ERRCODE = 'integrity_constraint_violation'（SQLSTATE 23000；D-53）。審查輪表 research_review_rounds 是 append-only（掛 research_append_only_guard()），不在下方允許清單內（D-57）。
-- V19 各表的條目一併在此宣告（函式於 V16 一次建立；V19 只掛觸發器，Flyway 已發佈檔不改）。
CREATE FUNCTION console.research_controlled_update_guard() RETURNS trigger
    LANGUAGE plpgsql AS
$$
DECLARE
    allowed text[];
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION '% 不可刪除（更正＝追加新列）', TG_TABLE_NAME
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    allowed := CASE TG_TABLE_NAME
        WHEN 'research_projects' THEN ARRAY['title','topic','scope','scope_rev','depth_level','target_scope','fsm_project','fsm_generation',
                                            'flow_step','flow_phase','flow_status','flow_detail','console_project_id',
                                            'last_event_seq','updated_at','archived_at']
        WHEN 'research_stage_runs' THEN ARRAY['status','tokens_used','exit_reason','started_at','finished_at']
        WHEN 'research_sources' THEN ARRAY['verification']
        WHEN 'research_review_defects' THEN ARRAY['status','fixed_in_version_no','waived_by','waiver_reason','resolved_at']
        WHEN 'research_allowlist_entries' THEN ARRAY['enabled','disabled_by','disabled_at']
        WHEN 'research_route_decisions' THEN ARRAY['status','failure_step','finished_at','repo_url','published_docs',
                                                   'console_project_id','impl_fsm_project','impl_state_dir']
        WHEN 'research_route_steps' THEN ARRAY['status','exit_code','stdout_tail','stderr_tail','finished_at']
        WHEN 'research_decompositions' THEN ARRAY['status','draft_id','import_record_id','tcs_rel_path','tcs_sha256','tasks_count','gate_rejection']
        WHEN 'research_scr' THEN ARRAY['status','prd_to_version_no','successor_research_id','impl_fsm_actions','decided_by','decided_at']
        ELSE NULL
    END;
    IF allowed IS NULL THEN
        RAISE EXCEPTION '% 未登記於 research_controlled_update_guard 的允許清單', TG_TABLE_NAME
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (to_jsonb(NEW) - allowed) IS DISTINCT FROM (to_jsonb(OLD) - allowed) THEN
        RAISE EXCEPTION '% 只准更新 %', TG_TABLE_NAME, allowed
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_projects_guard BEFORE UPDATE OR DELETE ON console.research_projects
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_events (
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    seq BIGINT NOT NULL CHECK (seq >= 1),                  -- 每專案單調；＝SSE id
    event_type VARCHAR(40) NOT NULL,                       -- research.step／run／source／evidence／prd／review／review_invalid／defect／gate／reconcile／route／scr／delivery／alert
    step VARCHAR(10) NOT NULL,
    actor VARCHAR(100) NOT NULL,                           -- JWT subject 或 'bridge'
    ref_kind VARCHAR(30),
    ref_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (research_id, seq)
);
CREATE INDEX idx_research_events_type ON console.research_events (research_id, event_type);
CREATE TRIGGER trg_research_events_guard BEFORE UPDATE OR DELETE ON console.research_events
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_stage_runs (
    id UUID PRIMARY KEY,                                   -- Bridge 配號；＝引擎 run_id
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    stage VARCHAR(10) NOT NULL CHECK (stage IN ('RESEARCH','DRAFT','REVIEW','REVISE','TCS_DRAFT')),
    round_no INTEGER NOT NULL DEFAULT 0 CHECK (round_no >= 0),   -- REVIEW stage run：本次要產生的輪號（已完成評估的輪數＋1）；取消／中斷／無效輸出後重審沿用同號、attempt＋1，審查輪列不因此新增或佔號（D-57）
    attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1),
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    status VARCHAR(10) NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED','BLOCKED_DB')),
    playbook_sha256 CHAR(64) CHECK (playbook_sha256 ~ '^[0-9a-f]{64}$'),
    config_sha256 CHAR(64) CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    prompt_manifest JSONB NOT NULL DEFAULT '[]'::jsonb,    -- [{role, agent_yaml, yaml_sha256, persona_sha256}]
    allowlist_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb, -- 本 run 的有效 FETCH／WEB 清單（D-17 事後稽核）
    tokens_used BIGINT NOT NULL DEFAULT 0,
    exit_reason VARCHAR(300) NOT NULL DEFAULT '',
    requested_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (research_id, stage, round_no, attempt)
);
CREATE INDEX idx_research_stage_runs_status ON console.research_stage_runs (status) WHERE status IN ('QUEUED','RUNNING','BLOCKED_DB');
CREATE UNIQUE INDEX ux_research_stage_runs_active ON console.research_stage_runs (research_id) WHERE status IN ('QUEUED','RUNNING');   -- D-61（D-27）：同一研究專案同時至多一個進行中的 stage run；並行上限 1 由資料庫守，應用層 409 stage_conflict 在其前
-- 編譯結果欄（playbook_sha256／config_sha256／prompt_manifest／allowlist_snapshot）於建立列時一併寫入、之後唯讀（通用守衛的允許清單只有 status／tokens_used／exit_reason／started_at／finished_at）
CREATE TRIGGER trg_research_stage_runs_guard BEFORE UPDATE OR DELETE ON console.research_stage_runs
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_artifacts (                  -- 檔案登記：每個具名檔案版本一列（「檔案 ↔ 表」的樞紐）
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    kind VARCHAR(20) NOT NULL CHECK (kind IN (
        'ISSUE_SCOPE','EVIDENCE_ITEMS','EVIDENCE_MATRIX','PRD_DRAFT','PRD_BASELINE','ADR_DRAFT','REVIEW_CARD',
        'ROUTE_DECISION','STATE_EXPORT','TASK_DECOMPOSITION','TCS','HEALING_LOG')),
    version INTEGER NOT NULL CHECK (version >= 1),
    rel_path VARCHAR(500) NOT NULL,                        -- 相對工作區
    sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    bytes BIGINT NOT NULL CHECK (bytes >= 0),
    origin VARCHAR(6) NOT NULL CHECK (origin IN ('AGENT','HUMAN','BRIDGE')),
    content TEXT CHECK (content IS NULL OR octet_length(content) <= 1048576),   -- JSON 類產物全文（nullable，≤1 MiB 位元組：octet_length 計位元組、length 計字元，多位元組字元會使後者低估；D-53、D-59(2)）：kind=EVIDENCE_ITEMS 者為 evidence_items.json 位元組原樣全文，含 counter_evidence／honest_bounds（D-43；P0 不另立表）
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, kind, version)
);
CREATE TRIGGER trg_research_artifacts_guard BEFORE UPDATE OR DELETE ON console.research_artifacts
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();
```

**K.2　`V17__research_evidence.sql`**
```sql
-- V17__research_evidence.sql — 來源實體、每次抓取、證據抽取、ADMIN 管理的 allowlist（根層研究 SOP S2／S3 的資料化）
CREATE TABLE console.research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    source_no VARCHAR(8) NOT NULL CHECK (source_no ~ '^S-[0-9]{3,4}$'),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    tier VARCHAR(2) NOT NULL CHECK (tier IN ('T1','T2','T3')),                     -- SOP S2:58
    verification VARCHAR(2) NOT NULL CHECK (verification IN ('V1','V2','V3')),     -- SOP S2:69（V0 不得列入）
    anchor_kind VARCHAR(6) NOT NULL CHECK (anchor_kind IN ('URL','DOI','COMMIT')),
    url TEXT NOT NULL,
    doi VARCHAR(200),
    git_commit VARCHAR(64),
    title TEXT NOT NULL,
    authors_org TEXT NOT NULL DEFAULT '',
    published_at DATE,
    source_type VARCHAR(10) NOT NULL DEFAULT 'OTHER'
        CHECK (source_type IN ('PAPER','PREPRINT','ENG_BLOG','WHITEPAPER','PATENT','REPO','ISSUE_PR','FORUM','DOC','OTHER')),
    license_spdx VARCHAR(100),
    license_note TEXT NOT NULL DEFAULT '',
    clue_only BOOLEAN NOT NULL DEFAULT FALSE,                -- T3 強制 true 由下方 CHECK 鎖；T1／T2 的 clue_only 由 Bridge 寫入器依證據分層規則設定，不下沉為 CHECK（D-61：應用層保證、AT 守）
    first_fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,    -- 首次出現時間：Bridge 抓取＝抓取時間；宣告型來源＝其網址首次出現於 search_log 的時間
    UNIQUE (research_id, source_no),
    UNIQUE (research_id, url),
    CHECK (tier <> 'T3' OR clue_only),                                              -- SOP S2:58：T3 只當線索、不入正式證據
    CHECK (anchor_kind <> 'DOI' OR doi IS NOT NULL),
    CHECK (anchor_kind <> 'COMMIT' OR (git_commit IS NOT NULL AND git_commit ~ '^[0-9a-f]{40}$')),               -- 證據矩陣模板 §2.3 規則 3；NULL 不得靜默通過（D-59(1)）：CHECK 對 NULL 視為通過，COMMIT 錨點缺 git_commit 時 ~ 運算為 NULL，所以先判 IS NOT NULL
    CHECK (url ~ '^https://')                                                       -- 同上：來源網址必須 https
);
-- 受控可更新＋單向（D-49）：通用守衛只放行 verification 並擋任何 DELETE；專用守衛再鎖「只升不降」
CREATE FUNCTION console.research_source_verification_guard() RETURNS trigger LANGUAGE plpgsql AS
$$
BEGIN
    IF substr(NEW.verification, 2)::int < substr(OLD.verification, 2)::int THEN        -- V1 < V2 < V3
        RAISE EXCEPTION 'research_sources.verification 只升不降（% → %）', OLD.verification, NEW.verification
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_sources_guard BEFORE UPDATE OR DELETE ON console.research_sources
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_sources_verification BEFORE UPDATE OF verification ON console.research_sources
    FOR EACH ROW EXECUTE FUNCTION console.research_source_verification_guard();

CREATE TABLE console.research_fetches (                    -- 每次抓取（含被拒）；append-only
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    source_id UUID REFERENCES console.research_sources(id),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    fetch_no VARCHAR(10) NOT NULL CHECK (fetch_no ~ '^F-[0-9]{4,}$'),    -- 每研究專案單調：Bridge 於同交易 max+1 配號（同專案同時只有一個 RUNNING stage run，UNIQUE 兜底）；來源的 fetch_refs 指向它
    fetch_method VARCHAR(10) NOT NULL CHECK (fetch_method IN ('API','WEB_FETCH','WEB_SEARCH','MANUAL')),
    observed_by VARCHAR(14) NOT NULL CHECK (observed_by IN ('BRIDGE','AGENT_DECLARED')),   -- WEB_* 由 agent 宣告，Bridge 觀測不到單筆
    search_no INTEGER CHECK (search_no IS NULL OR search_no >= 1),                         -- 只有 agent 宣告的 search_log 列有：Q-NNN 的數字部分（search_log[].id；D-43、D-53）
    result_urls JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(result_urls) = 'array'),   -- search_log[].result_urls（https 字串陣列；D-53）
    host VARCHAR(255),                                                                     -- WEB_SEARCH 列為空（搜尋沒有單一網址）；解析不出 host 的被拒外呼寫保留字 '(unparsed)'（非空、不是合法主機名，D-61 的非空 CHECK 放行；D-66）
    url TEXT,
    query_text TEXT,
    http_status INTEGER,
    outcome VARCHAR(18) NOT NULL CHECK (outcome IN (
        'OK','DENIED_ALLOWLIST','DENIED_PRIVATE_IP','HTTP_ERROR','TIMEOUT','TOO_LARGE','PARSE_ERROR','RATE_LIMITED')),
    raw_rel_path VARCHAR(500),
    raw_sha256 CHAR(64) CHECK (raw_sha256 IS NULL OR raw_sha256 ~ '^[0-9a-f]{64}$'),
    raw_bytes BIGINT CHECK (raw_bytes IS NULL OR raw_bytes >= 0),
    duration_ms INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, fetch_no),
    -- NULL 不得靜默通過（D-59(1)）：非 WEB_SEARCH 列 url、host 皆必填；WEB_SEARCH 列兩欄皆空（搜尋沒有單一網址）；兩條都只用 IS NULL／IS NOT NULL 判，不產生 NULL 結果
    CHECK (fetch_method = 'WEB_SEARCH' OR (url IS NOT NULL AND host IS NOT NULL)),
    CHECK (fetch_method <> 'WEB_SEARCH' OR (url IS NULL AND host IS NULL)),
    CHECK (host IS NULL OR host <> ''),                                              -- D-61：非 NULL 的 host 不得為空字串（DENIED 列也一樣，否則空 host 的被拒紀錄無從稽核）
    CHECK (observed_by = 'AGENT_DECLARED' OR search_no IS NULL)
);
CREATE UNIQUE INDEX ux_research_fetches_search_no ON console.research_fetches (research_id, search_no) WHERE search_no IS NOT NULL;
CREATE INDEX idx_research_fetches_research ON console.research_fetches (research_id, fetched_at);
CREATE TRIGGER trg_research_fetches_guard BEFORE UPDATE OR DELETE ON console.research_fetches
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_evidence_items (             -- SOP S3 七欄；缺欄寫「未見」（NOT NULL＋gate 驗非空）；以 matrix_version 新增、不改
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    matrix_version INTEGER NOT NULL CHECK (matrix_version >= 1),    -- ＝ research_artifacts(kind='EVIDENCE_ITEMS').version
    scope_rev INTEGER NOT NULL DEFAULT 1 CHECK (scope_rev >= 1),
    evidence_no VARCHAR(8) NOT NULL CHECK (evidence_no ~ '^E-[0-9]{3,4}$'),
    source_id UUID NOT NULL REFERENCES console.research_sources(id),
    candidate VARCHAR(200),                                         -- 候選技術名（供優缺點矩陣分組；可空；D-43）
    claim TEXT NOT NULL,                                            -- PRD 引用的論點
    f1_mechanism TEXT NOT NULL,
    f2_evidence TEXT NOT NULL,
    f3_critique TEXT NOT NULL,
    f4_risk_tags TEXT[] NOT NULL DEFAULT '{}',
    f5_applicability JSONB NOT NULL,                                -- 六格 A／M／N＋理由（技術可行｜授權相容｜維護風險｜效能邊界｜資安｜成本）
    f6_limits TEXT NOT NULL,
    f7_verification VARCHAR(2) NOT NULL CHECK (f7_verification IN ('V1','V2','V3')),
    strength VARCHAR(9) NOT NULL DEFAULT 'WEAK' CHECK (strength IN ('STRONG','MEDIUM','WEAK','CANDIDATE')),   -- 必須等於證據矩陣模板 §3.3 函式值（Bridge 驗）
    unanchored BOOLEAN NOT NULL DEFAULT FALSE,                      -- F2 數字在抓取原文比對不到：Bridge 入庫時計算，研究者不寫；TRUE 的列 PRD 不得引用
    UNIQUE (research_id, matrix_version, evidence_no)
);
CREATE INDEX idx_research_evidence_source ON console.research_evidence_items (source_id);
CREATE TRIGGER trg_research_evidence_items_guard BEFORE UPDATE OR DELETE ON console.research_evidence_items
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_allowlist_entries (          -- D-17：產業網域由 ADMIN 逐一加入；Reddit 預設不在任何清單
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_kind VARCHAR(5) NOT NULL CHECK (list_kind IN ('FETCH','WEB')),
    host VARCHAR(255) NOT NULL CHECK (host ~ '^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$'),
    layer VARCHAR(9) NOT NULL CHECK (layer IN ('ACADEMIC','INDUSTRY','OSS','COMMUNITY')),
    purpose VARCHAR(200) NOT NULL DEFAULT '',
    tos_note TEXT NOT NULL DEFAULT '',
    min_interval_seconds INTEGER NOT NULL DEFAULT 3 CHECK (min_interval_seconds BETWEEN 1 AND 3600),   -- 實際間隔＝max(Bridge 內建下限, 本值)（PRD NFR-R2P-03-6）；建立後不可改（受控更新守衛只放行 enabled／disabled_*），要調整＝停用後重建
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    tos_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    added_by VARCHAR(100) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    disabled_by VARCHAR(100),
    disabled_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (list_kind, host),
    CHECK (host !~ '(^|\.)(reddit\.com|redd\.it)$' OR tos_acknowledged),            -- Reddit 須先確認條款
    CHECK (enabled OR (disabled_by IS NOT NULL AND disabled_at IS NOT NULL))
);
-- 受控可更新（D-49）：由通用守衛 research_controlled_update_guard() 只放行 enabled／disabled_by／disabled_at，並擋任何 DELETE
CREATE TRIGGER trg_research_allowlist_guard BEFORE UPDATE OR DELETE ON console.research_allowlist_entries
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

```

**K.3　`V18__research_prd_review_gate.sql`**
```sql
-- V18__research_prd_review_gate.sql — PRD 版本（含本文，供工作室編輯器與 Diff）、四方審查輪、分數、缺陷、人工決定（Gate 0 屬 P0，所以決定表隨 V18）
CREATE TABLE console.research_prd_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    semver VARCHAR(30) NOT NULL CHECK (semver ~ '^v[0-9]+\.[0-9]+\.[0-9]+(-draft)?$'),   -- 含 v 前綴：例 v0.3.0-draft、v1.0.0（審查卡與 route_decision.json 的 prd_version 字串；D-43）
    kind VARCHAR(8) NOT NULL CHECK (kind IN ('DRAFT','BASELINE')),
    author_kind VARCHAR(5) NOT NULL CHECK (author_kind IN ('AGENT','HUMAN')),
    author VARCHAR(100) NOT NULL,                          -- agent id 或 JWT subject
    parent_version_no INTEGER,
    content TEXT NOT NULL CHECK (octet_length(content) <= 1048576),   -- 位元組（非字元數；D-59(2)）
    rel_path VARCHAR(500) NOT NULL,
    sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    bytes INTEGER NOT NULL CHECK (bytes >= 0),
    evidence_refs VARCHAR(8)[] NOT NULL DEFAULT '{}',      -- PRD 內 [E-NNN] 引用（M1 證據錨定率的分子分母）
    change_summary VARCHAR(500) NOT NULL DEFAULT '',
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, version_no),
    FOREIGN KEY (research_id, parent_version_no) REFERENCES console.research_prd_versions (research_id, version_no)
);
CREATE TRIGGER trg_research_prd_versions_guard BEFORE UPDATE OR DELETE ON console.research_prd_versions
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

-- 審查輪列只在輪有結果時（前置否決已判，或四維審查卡皆通過驗證並彙整、`gate` 已回傳）與四維分數列、缺陷列、research_events 同一交易一次寫入（D-57）。
-- 列存在＝輪已完成評估，所以沒有 status 欄：單值欄位沒有資訊量，還會留下「日後有人寫 RUNNING 列」的後路；
-- 進行中、取消、中斷（額度或 API）、Bridge 重啟、輸出無效（REVIEW_INVALID）一律不寫列、不佔 round_no、不耗預算，
-- 只記 REVIEW stage run（research_stage_runs，UNIQUE(research_id, stage, round_no, attempt)）與事件。
-- round_no＝已完成評估的序號，與 FSM gate 呼叫一一對應（POST_HUMAN 通過輪除外；人工退回呼叫 gate FAIL 但不是審查輪）。
-- round_no 連續（1、2、3…不跳號）由 Bridge 寫入器於同交易 max+1 配號保證、AT 守（D-61）：UNIQUE(research_id, round_no) 只擋重複、不擋跳號，連續性不下沉為 DDL。
CREATE TABLE console.research_review_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    round_no INTEGER NOT NULL CHECK (round_no >= 1),
    fsm_generation INTEGER NOT NULL DEFAULT 1,
    prd_version_no INTEGER NOT NULL,
    trigger_kind VARCHAR(10) NOT NULL CHECK (trigger_kind IN ('AUTO','MANUAL','POST_HUMAN')),
    precheck_passed BOOLEAN NOT NULL,                      -- 前置否決 P1（SLV-001／SLV-002／SLV-003／AMBIGUITY）；FALSE＝不計分直接 FAIL
    precheck_detail JSONB NOT NULL DEFAULT '{}'::jsonb,    -- {"checks":[{"id","passed","detail"}×4]}（審查卡 precheck.checks[]）
    weighted_score NUMERIC(5,2) CHECK (weighted_score BETWEEN 0 AND 100),   -- W100/100 精確值，不四捨五入（D-42）；前置否決不過時 NULL
    threshold NUMERIC(5,2) NOT NULL DEFAULT 85.00 CHECK (threshold BETWEEN 50.00 AND 100.00),   -- D-61：產品常數的範圍鎖（passed 的 CHECK 以它為比較基準，被寫成 0 會使 passed 恆真）
    floor_score INTEGER NOT NULL DEFAULT 60 CHECK (floor_score BETWEEN 50 AND 100),   -- D-14／D-42／D-65：任一維度不低於地板（初值 60、未校準）；範圍鎖與 threshold 對稱，地板被寫成 0 會架空 D-14
    min_dimension_score INTEGER CHECK (min_dimension_score BETWEEN 0 AND 100),
    open_p1_count INTEGER NOT NULL DEFAULT 0 CHECK (open_p1_count >= 0),
    passed BOOLEAN NOT NULL,
    verdict VARCHAR(8) NOT NULL CHECK (verdict IN ('PASS','REVISE','ESCALATE')),     -- REVIEW_INVALID 不是輪的 verdict：無效輸出不寫輪列、不佔 round_no，只記 stage run（exit_reason=review_invalid）與事件 research.review_invalid（D-55）
    fsm_gate_result VARCHAR(4) CHECK (fsm_gate_result IN ('PASS','FAIL')),
    fsm_retry_count INTEGER,                               -- gate FAIL 的回傳 retry_count；gate PASS 的回傳不帶 retry_count，引擎於 PASS 時歸零，故寫 0；POST_HUMAN 通過輪未呼叫 gate ⇒ NULL（D-61；與 fsm_gate_result 同為 NULL）
    escalated BOOLEAN NOT NULL DEFAULT FALSE,
    stage_run_id UUID NOT NULL REFERENCES console.research_stage_runs(id),   -- 產生本輪的 REVIEW stage run；進行中的狀態只住那裡（D-57）
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,          -- 取自該 stage run 的 started_at；列到有結果才寫，不能用 DEFAULT NOW()（那會變成寫入時刻）
    finished_at TIMESTAMP WITH TIME ZONE NOT NULL,         -- 取自該 stage run 的 finished_at
    UNIQUE (research_id, round_no),
    FOREIGN KEY (research_id, prd_version_no) REFERENCES console.research_prd_versions (research_id, version_no),
    CHECK (finished_at >= started_at),
    -- 以 IS TRUE 形式寫，避免 NULL 比較使 CHECK 靜默通過（D-14 三條件＋預檢＋verdict；D-42：weighted_score 是 W100/100 精確值，比較不經四捨五入）
    CHECK (passed IS NOT TRUE OR ((weighted_score >= threshold) IS TRUE AND (min_dimension_score >= floor_score) IS TRUE
                                  AND open_p1_count = 0 AND precheck_passed IS TRUE AND verdict IS NOT DISTINCT FROM 'PASS')),
    -- D-50：自動／手動觸發的通過輪必有 gate PASS；人工退回後的再審（POST_HUMAN）通過只記 DB、不呼叫 gate PASS
    CHECK (passed IS NOT TRUE OR trigger_kind = 'POST_HUMAN' OR fsm_gate_result IS NOT DISTINCT FROM 'PASS'),
    CHECK (NOT (trigger_kind = 'POST_HUMAN' AND passed IS TRUE) OR fsm_gate_result IS NULL),
    -- D-57：輪與 gate 呼叫一一對應——未通過的輪必有 gate FAIL（與上兩條合起來：fsm_gate_result 為 NULL ⇔ POST_HUMAN 通過）
    CHECK (passed IS TRUE OR fsm_gate_result IS NOT DISTINCT FROM 'FAIL'),
    -- 前置否決不過＝不計分（審查卡：weighted_total、min_dimension_score 為 null）
    CHECK (precheck_passed IS NOT FALSE OR (weighted_score IS NULL AND min_dimension_score IS NULL AND passed IS NOT TRUE)),
    -- D-61：單向 CHECK 留下的反向缺口（以下三條只用 NOT NULL 欄或 IS NULL 判，不產生 NULL 結果）
    CHECK ((verdict = 'PASS') = (passed IS TRUE)),                       -- PASS 與 passed 互為充要（補「passed 為 false 卻 verdict='PASS'」）
    CHECK (escalated = (verdict = 'ESCALATE')),                          -- escalated 與 ESCALATE 互為充要
    CHECK ((fsm_retry_count IS NULL) = (fsm_gate_result IS NULL))        -- 兩欄同為 NULL（POST_HUMAN 通過輪未呼叫 gate）或同非 NULL
);
-- append-only（D-57）：任何 UPDATE／DELETE 一律拒絕；輪列沒有「事後寫終態欄」這回事，所以不在通用守衛的允許清單內
CREATE TRIGGER trg_research_review_rounds_guard BEFORE UPDATE OR DELETE ON console.research_review_rounds
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_review_scores (
    round_id UUID NOT NULL REFERENCES console.research_review_rounds(id),
    dimension VARCHAR(12) NOT NULL CHECK (dimension IN ('ARCHITECTURE','PRODUCT','QA','SECURITY')),
    weight NUMERIC(4,3) NOT NULL CHECK (weight > 0 AND weight <= 1),                -- 0.300／0.250／0.250／0.200
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),                        -- 五項 rubric（各 0～20）之和；整數（D-42）
    agent_id VARCHAR(80) NOT NULL,                         -- sd-architect／pm-po／qa-tester／security-engineer（PRODUCT 維度＝pm-po，即 agent/core/03.pm-po-agent-zh.yaml 的 agent.id；D-44）
    assist_agent_id VARCHAR(80),                           -- 只有 SECURITY：compliance-officer（授權項輔助），其餘 NULL
    assist_agent_yaml_sha256 CHAR(64) CHECK (assist_agent_yaml_sha256 IS NULL OR assist_agent_yaml_sha256 ~ '^[0-9a-f]{64}$'),
    agent_yaml_path VARCHAR(300) NOT NULL,
    agent_yaml_sha256 CHAR(64) NOT NULL CHECK (agent_yaml_sha256 ~ '^[0-9a-f]{64}$'),
    persona_sha256 CHAR(64) NOT NULL CHECK (persona_sha256 ~ '^[0-9a-f]{64}$'),
    summary TEXT NOT NULL DEFAULT '',
    raw_rel_path VARCHAR(500) NOT NULL,
    raw_sha256 CHAR(64) NOT NULL CHECK (raw_sha256 ~ '^[0-9a-f]{64}$'),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    CHECK ((assist_agent_id IS NULL) = (assist_agent_yaml_sha256 IS NULL)),
    PRIMARY KEY (round_id, dimension)
);
CREATE TRIGGER trg_research_review_scores_guard BEFORE UPDATE OR DELETE ON console.research_review_scores
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

CREATE TABLE console.research_review_defects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES console.research_review_rounds(id),
    defect_no VARCHAR(16) NOT NULL,                        -- D-<輪>-<NNN>（審查卡 defects[].id）
    dimension VARCHAR(12) NOT NULL CHECK (dimension IN ('ARCHITECTURE','PRODUCT','QA','SECURITY')),
    severity VARCHAR(2) NOT NULL CHECK (severity IN ('P1','P2','P3','P4')),
    code VARCHAR(40) NOT NULL,
    prd_anchor VARCHAR(200) NOT NULL DEFAULT '',
    description TEXT NOT NULL,
    suggestion TEXT NOT NULL DEFAULT '',
    evidence_refs VARCHAR(8)[] NOT NULL DEFAULT '{}',
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FIXED','WAIVED','SUPERSEDED','REGRESSED')),
    fixed_in_version_no INTEGER,
    waived_by VARCHAR(100),
    waiver_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (round_id, defect_no),
    CHECK (status <> 'WAIVED' OR (waived_by IS NOT NULL AND waiver_reason IS NOT NULL)),          -- 審查卡 waiver{by,reason,at}：by／reason 必填（D-53）
    CHECK (status NOT IN ('FIXED','WAIVED','SUPERSEDED') OR resolved_at IS NOT NULL)            -- 離開 OPEN 的終態必有解決時間（D-53）；WAIVED 的 waiver.at＝resolved_at
);
-- 缺陷 status 單向轉移（D-49；審查卡模板 §5.3）：OPEN→FIXED／WAIVED／SUPERSEDED、FIXED→REGRESSED、REGRESSED→FIXED，其餘一律拒；status 未變動的 UPDATE 不受限
CREATE FUNCTION console.research_defect_status_guard() RETURNS trigger LANGUAGE plpgsql AS
$$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
           (OLD.status = 'OPEN'      AND NEW.status IN ('FIXED','WAIVED','SUPERSEDED'))
        OR (OLD.status = 'FIXED'     AND NEW.status = 'REGRESSED')
        OR (OLD.status = 'REGRESSED' AND NEW.status = 'FIXED')) THEN
        RAISE EXCEPTION 'research_review_defects.status 不得由 % 轉為 %', OLD.status, NEW.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_research_defects_guard BEFORE UPDATE OR DELETE ON console.research_review_defects
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_defects_status BEFORE UPDATE OF status ON console.research_review_defects
    FOR EACH ROW EXECUTE FUNCTION console.research_defect_status_guard();
CREATE INDEX idx_research_defects_open ON console.research_review_defects (round_id) WHERE status = 'OPEN';

CREATE TABLE console.research_gate_decisions (             -- append-only；內容與 V6 audit_log 以 audit_trace_id 對應
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    gate VARCHAR(11) NOT NULL CHECK (gate IN ('GATE0','SCR','ROUTE','STAGE2','SCG4','SCG5','ABANDON_KEY')),
    decision VARCHAR(9) NOT NULL CHECK (decision IN ('APPROVED','REJECTED','CHANGES','ABANDONED')),
    decided_by VARCHAR(100) NOT NULL,                      -- JWT subject（人；僅 ADMIN 動作，D-12）
    decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
    prd_version_no INTEGER,
    review_round_no INTEGER,
    fsm_project VARCHAR(100) NOT NULL,
    fsm_stage VARCHAR(64),                                 -- Gate-0／Gate-0-SCR1／Stage-1／Stage-2
    fsm_state_after VARCHAR(40),
    frozen_digests JSONB NOT NULL DEFAULT '{}'::jsonb,     -- {相對路徑: sha256}；＝frozen_stages[-1].spec_doc_digests
    reason TEXT NOT NULL DEFAULT '',
    audit_trace_id VARCHAR(64),
    CHECK (gate <> 'GATE0' OR decision <> 'APPROVED' OR (frozen_digests <> '{}'::jsonb AND fsm_stage IS NOT NULL))
);
CREATE INDEX idx_research_gate_research ON console.research_gate_decisions (research_id, decided_at);
CREATE TRIGGER trg_research_gate_guard BEFORE UPDATE OR DELETE ON console.research_gate_decisions
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();
```

**K.4　`V19__research_route_scr_delivery.sql`（P1 一次建立；P2 只寫入列）**
```sql
-- V19__research_route_scr_delivery.sql — 分流、SCR、拆解、交付；自癒視圖
CREATE TABLE console.research_route_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    track CHAR(1) NOT NULL CHECK (track IN ('A','B')),
    target_kind VARCHAR(10) NOT NULL CHECK (target_kind IN ('MODULE','STANDALONE')),
    target_module VARCHAR(12) CHECK (target_module IN ('autoclaude','agentconsole','sdd','monorepo')),
    target_path VARCHAR(500) NOT NULL,
    git_branch VARCHAR(200),
    base_ref VARCHAR(200),
    repo_url VARCHAR(500),
    repo_visibility VARCHAR(7) CHECK (repo_visibility IN ('PUBLIC','PRIVATE')),
    stack_template VARCHAR(40),
    console_project_id UUID REFERENCES console.projects(id),
    impl_fsm_project VARCHAR(100),
    impl_state_dir VARCHAR(500),
    published_docs JSONB NOT NULL DEFAULT '{}'::jsonb,     -- {目標 docs/ 相對路徑: sha256}
    scope_differs_reason VARCHAR(200),                     -- 分流與 PRD target_scope 不同時必填（FR-R2P-11）
    status VARCHAR(11) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','COMPENSATED')),
    failure_step VARCHAR(30),
    decided_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    CHECK ((track = 'A' AND target_kind = 'MODULE' AND target_module IS NOT NULL)
        OR (track = 'B' AND target_kind = 'STANDALONE' AND target_module IS NULL)),
    CHECK (repo_visibility IS DISTINCT FROM 'PUBLIC' OR track = 'B')
);
CREATE UNIQUE INDEX ux_research_route_active ON console.research_route_decisions (research_id)
    WHERE status IN ('PENDING','RUNNING','SUCCEEDED');

CREATE TABLE console.research_route_steps (
    route_id UUID NOT NULL REFERENCES console.research_route_decisions(id),
    step_no INTEGER NOT NULL CHECK (step_no >= 1),
    step VARCHAR(24) NOT NULL CHECK (step IN (
        'VALIDATE_TARGET','GIT_SWITCH','SCAFFOLD_FILES','GIT_INIT','GIT_COMMIT','GH_REPO_CREATE','PUBLISH_DOCS',
        'COPY_WORKSPACE','REGISTER_STUB','IMPL_KEY_INIT','BASELINE_ADOPT')),               -- GIT_SWITCH＝git worktree add（獨立 worktree，D-20 SA-08）
    status VARCHAR(11) NOT NULL CHECK (status IN ('RUNNING','OK','FAILED','SKIPPED','COMPENSATED')),
    argv_redacted TEXT NOT NULL DEFAULT '',                -- 去敏後的 argv（不含 token）
    exit_code INTEGER,
    stdout_tail VARCHAR(2000) NOT NULL DEFAULT '',
    stderr_tail VARCHAR(2000) NOT NULL DEFAULT '',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (route_id, step_no)
);

CREATE TABLE console.research_scr (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    scr_no INTEGER NOT NULL CHECK (scr_no >= 1),
    kind VARCHAR(5) NOT NULL CHECK (kind IN ('MINOR','MAJOR')),
    source_kind VARCHAR(14) NOT NULL CHECK (source_kind IN ('HUMAN','REVIEW_FINDING','SCG4','HEALING_FAILED')),
    reason TEXT NOT NULL,
    reason_class VARCHAR(10) NOT NULL DEFAULT 'OTHER' CHECK (reason_class IN ('EVIDENCE','AC_VAGUE','REQ_CHANGE','INFEASIBLE','OTHER')),   -- PRD 缺漏證據／AC 模糊／需求變更／技術不可行／其他（M6 分群）
    affected_sections TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','APPROVED','REJECTED','APPLIED','SUPERSEDED')),
    prd_from_version_no INTEGER,
    prd_to_version_no INTEGER,
    successor_research_id UUID REFERENCES console.research_projects(id),   -- MAJOR：新研究專案
    impl_fsm_actions JSONB NOT NULL DEFAULT '[]'::jsonb,                   -- 實際呼叫過的 FSM 動詞序列（稽核）
    requested_by VARCHAR(100) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    decided_by VARCHAR(100),
    decided_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (research_id, scr_no)
);

CREATE TABLE console.research_decompositions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    path CHAR(1) NOT NULL CHECK (path IN ('A','B','C')),                    -- 沿 import 解析路徑 A／B／C（ImportController.java:108-116）
    draft_id VARCHAR(64),                                                   -- /autoclaude/decompose 草稿 id（路徑 C）
    import_record_id UUID REFERENCES console.import_records(id),
    tcs_rel_path VARCHAR(500),
    tcs_sha256 CHAR(64) CHECK (tcs_sha256 IS NULL OR tcs_sha256 ~ '^[0-9a-f]{64}$'),
    prd_sha256 CHAR(64) CHECK (prd_sha256 IS NULL OR prd_sha256 ~ '^[0-9a-f]{64}$'),   -- 拆解綁凍結 PRD（stale 判定）
    tasks_count INTEGER NOT NULL DEFAULT 0 CHECK (tasks_count >= 0),
    gate_rejection VARCHAR(30),                                             -- max_steps／cycle／empty_prompt／brain_*（decompose.py:37-47）
    status VARCHAR(10) NOT NULL DEFAULT 'DRAFTED'
        CHECK (status IN ('DRAFTED','SCG_PASSED','FROZEN','IMPORTED','SIGNED_OFF','REJECTED','STALE')),
    stage_run_id UUID REFERENCES console.research_stage_runs(id),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 受控可更新表掛通用守衛（D-49；允許清單已在 V16 的函式內宣告）
CREATE TRIGGER trg_research_route_decisions_guard BEFORE UPDATE OR DELETE ON console.research_route_decisions
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_route_steps_guard BEFORE UPDATE OR DELETE ON console.research_route_steps
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_scr_guard BEFORE UPDATE OR DELETE ON console.research_scr
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();
CREATE TRIGGER trg_research_decompositions_guard BEFORE UPDATE OR DELETE ON console.research_decompositions
    FOR EACH ROW EXECUTE FUNCTION console.research_controlled_update_guard();

CREATE TABLE console.research_deliveries (                 -- append-only（P2 寫入；表隨 V19 建立，Flyway 已發佈檔不改）
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID NOT NULL REFERENCES console.research_projects(id),
    kind VARCHAR(12) NOT NULL CHECK (kind IN ('RELEASE_TAG','PULL_REQUEST','RELEASE_NOTE')),
    ref VARCHAR(200) NOT NULL,                             -- tag 名或 PR 編號
    commit_sha VARCHAR(40) CHECK (commit_sha IS NULL OR commit_sha ~ '^[0-9a-f]{40}$'),
    url VARCHAR(500),
    rtm_run_id UUID REFERENCES console.execution_runs(id),
    rtm_report_ref VARCHAR(300),
    fsm_state_after VARCHAR(40),
    status VARCHAR(7) NOT NULL CHECK (status IN ('CREATED','FAILED')),
    detail VARCHAR(2000) NOT NULL DEFAULT '',
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (research_id, kind, ref)
);
CREATE TRIGGER trg_research_deliveries_guard BEFORE UPDATE OR DELETE ON console.research_deliveries
    FOR EACH ROW EXECUTE FUNCTION console.research_append_only_guard();

-- 自癒嘗試＝既有 execution_steps（RETRYING／FAILED）；視圖不新增任何寫入路徑
CREATE VIEW console.v_research_healing_attempts AS
SELECT rp.id AS research_id, er.id AS run_id, er.run_number, es.task_id, es.step_number, es.action,
       es.status, es.error_message, es.tokens_used, es."timestamp" AS occurred_at
FROM console.research_projects rp
JOIN console.execution_runs er ON er.project_id = rp.console_project_id
JOIN console.execution_steps es ON es.run_id = er.id
WHERE es.status IN ('RETRYING', 'FAILED');
```

> **DDL 驗收**：`ResearchSchemaMigrationIT`（新類別；既有 `SchemaMigrationIT` 只改 Flyway 版本清單）對 V16～V19 套用成功＋`ddl-auto=validate` 不因新表報錯；每個 CHECK／觸發器各一個 Testcontainers 斷言（越界值被擋、append-only 表 UPDATE／DELETE 被擋、`tier='T3' AND clue_only=false` 被擋、`passed=true` 但分數不足或某維度低於地板或有 open P1 被擋、Reddit 網域未確認條款被擋、`rp_no` 超過四位數不截斷）。**D-49 三種觸發器**：受控可更新表更新清單外欄位與任何 DELETE 被通用守衛擋（含 `research_allowlist_entries` 只准 `enabled`／停用欄、`research_stage_runs` 編譯結果欄唯讀）、缺陷 `status` 非法轉移被擋（`OPEN→FIXED／WAIVED／SUPERSEDED`、`FIXED→REGRESSED`、`REGRESSED→FIXED` 放行）、來源 `verification` 降級被擋。**D-42／D-50 一致性**：`weighted_score` 以 `NUMERIC(5,2)` 精確比較（84.95 對 85.00 不過）、`passed` 且非 `POST_HUMAN` 而 `fsm_gate_result` 非 `PASS` 被擋、`POST_HUMAN` 通過而 `fsm_gate_result` 非 NULL 被擋、前置否決不過而帶分數被擋。**D-57 輪列 append-only**：對 `research_review_rounds` 任一列的 UPDATE（含 `round_no`、`verdict`、`finished_at` 任一欄）與 DELETE 被擋；輪列缺 `precheck_passed`、`passed`、`verdict`、`stage_run_id`、`started_at` 或 `finished_at`、或 `finished_at` 早於 `started_at` 被擋；`passed` 為 false 而 `fsm_gate_result` 非 `FAIL` 被擋。**D-61 型別層補鎖**：`research_review_rounds` 的 `verdict='PASS'` 而 `passed` 非 true（或 `passed` 為 true 而 `verdict` 非 `PASS`）被擋、`escalated` 與 `verdict='ESCALATE'` 不一致被擋、`fsm_retry_count` 與 `fsm_gate_result` 一邊為 NULL 另一邊非 NULL 被擋、`threshold` 低於 50.00 或高於 100.00 被擋；`research_stage_runs` 同一 `research_id` 的第二筆 QUEUED／RUNNING 被部分唯一索引擋；`research_fetches.host` 為空字串被擋；`round_no` 連續性與 T1／T2 的 `clue_only` 不在 DDL 斷言範圍（應用層保證，由 Bridge 寫入器的測試守）。**D-65 地板鎖**：`research_review_rounds.floor_score` 低於 50 或高於 100 被擋（與 `threshold` 的範圍鎖對稱；寫成 0 會架空 D-14 的每維度地板；初值 60 與邊界 50、100 通過）。**D-43／D-53 對映**：`research_artifacts.content` 與 `research_prd_versions.content` 超過 1 MiB（以位元組計，多位元組字元的字元數不得充當位元組數；D-59(2)）被擋、`research_fetches` 的 `WEB_SEARCH` 列帶 url 或 host、非 `WEB_SEARCH` 列的 url 或 host 為 NULL 被擋（D-59(1)）、`result_urls` 非 JSON 陣列被擋、`research_sources` 的 `url` 非 https、或 `COMMIT` 的 `git_commit` 為 NULL 或非 40 位 hex 被擋（D-59(1)）、`research_prd_versions.semver` 不合 `v` 前綴格式被擋、`research_review_scores` 的 `assist_agent_id` 與其 sha256 不成對被擋、`WAIVED` 缺 `waived_by` 或 `waiver_reason` 被擋、`FIXED`／`WAIVED`／`SUPERSEDED` 缺 `resolved_at` 被擋、`trigger_kind` 越出列舉被擋、`verdict` 為 `REVIEW_INVALID` 被擋（D-55）、`precheck_passed IS FALSE` 而 `passed` 為 true 或帶 `weighted_score` 被擋；**所有 18 張 `research_*` 表逐表 DELETE 一律被擋；觸發器拒絕的 SQLSTATE 一律為類別 23（`integrity_constraint_violation`）**（D-53）。`gen_random_uuid()` 與 V1 同款（PG13+ 內建）。V16～V18 於 P0、V19 於 P1 套用；每支遷移只追加、已發佈檔不改。

**M　檔案 ↔ 表 對照表（工作區 `<BRIDGE_RESEARCH_ROOT>/<slug>/`）**

| 檔案（相對工作區） | 作者 | 流向 | 登記（`research_artifacts.kind`） | 結構化落點 | 驗證／備註 |
|---|---|---|---|---|---|
| `00_research/issue_scope.json` | BRIDGE（由 UI 輸入渲染） | DB→檔 | `ISSUE_SCOPE` | `research_projects.scope`、`topic`、`depth_level` | 建立時渲染；之後僅在人改範圍時升版（`scope_rev`＋1） |
| `00_research/raw/<sha256>.<ext>` | BRIDGE（API 抓取）／AGENT（節錄） | 檔→DB | （不登記為 artifact） | `research_fetches.raw_rel_path`、`raw_sha256` | 內容定址；**git-ignored、不進任何版控與備份**（D-18）；API 類為真位元組，WEB 類為 agent 節錄 |
| `00_research/evidence_items.json` | AGENT | 檔→驗→DB | `EVIDENCE_ITEMS` | `research_sources`、`research_evidence_items`、`research_fetches`（宣告者的 `search_log`）、`research_artifacts.content`（全文，含 `counter_evidence`／`honest_bounds`） | `gates/evidence.py` 驗證證據矩陣模板 §2.3 的 16 條；evaluator 載具 |
| `00_research/evidence_matrix.md` | BRIDGE（確定性渲染，含 S8 三桶） | DB→檔 | `EVIDENCE_MATRIX` | 同上 | 供人讀、供 `spec-frozen --doc` |
| `01_specs/PRD_draft.md`（`PRD-v0.N.md`） | AGENT／HUMAN | 檔→驗→DB | `PRD_DRAFT` | `research_prd_versions`（`content`、`sha256`、`evidence_refs`） | `gates/prd_schema.py`：家規必讀章＋來源六節錨點、`E-NNN` 引用、Gherkin AC |
| `01_specs/PRD-v1.0.0.md` | BRIDGE（核准時複製 head 版） | 檔→DB | `PRD_BASELINE` | `research_prd_versions(kind=BASELINE)`、`research_gate_decisions.frozen_digests` | **FSM `spec-frozen` 的 `--doc`** |
| `01_specs/adr_draft.md` | AGENT | 檔→DB | `ADR_DRAFT` | （僅登記） | 隨 Gate 0 一併凍結 |
| `02_governance/reviews/round-<k>/<dimension 小寫>.json` | AGENT（審查者） | 檔→驗→DB | （不登記；`raw_*` 在分數列） | `research_review_scores`、`research_review_defects` | `gates/review_card.py` 驗審查卡模板 §6.2；分數僅取各維度整數，加權由碼（`W100`，D-42） |
| `02_governance/review_card.json` | BRIDGE（跨輪彙整，append 式重渲） | DB→檔 | `REVIEW_CARD` | `research_review_rounds`＋`_scores`＋`_defects` | 規格 §2 的「歷史評分與缺陷修訂紀錄」 |
| `02_governance/route_decision.json` | BRIDGE | DB→檔 | `ROUTE_DECISION` | `research_route_decisions`、`research_route_steps` | |
| `02_governance/state.json` | BRIDGE（匯出） | FSM＋DB→檔 | `STATE_EXPORT` | `research_projects.flow_*`＋FSM 唯讀視圖 | 🔴 **非權威**：FSM 真相＝`FSM-STATE-*.yaml`（只經 `FSMRuntime`）、游標真相＝DB；不得被任何程式讀回當輸入 |
| `build/reports/fsm/FSM-STATE-research-<slug>.yaml` | FSM CLI | — | （不登記） | （Bridge 唯讀鏡像於 `GET /sdd/fsm/{key}?root=`） | 被 `.gitignore` 忽略（BRIDGE §8.1:364-365）；每次 Gate／SCR 把 `show` 輸出引進證據 |
| `03_execution/TCS-<Feature>-<日期>.md` | AGENT（P1） | 檔→驗→DB | `TCS` | `research_decompositions.tcs_*` | 發佈到目標 `docs/03_testing/contracts/` 後才是內環 Stage-2 的 `--doc` |
| `03_execution/task_decomposition.json` | BRIDGE（由 TCS／draft 渲染） | DB→檔 | `TASK_DECOMPOSITION` | `research_decompositions`、`import_records.parsed_result` | |
| `03_execution/healing_history.log` | BRIDGE（append） | 引擎事件→檔 | `HEALING_LOG` | **既有表**：`execution_steps`、`checkpoints`（視圖 `v_research_healing_attempts`） | 檔案是衍生日誌，DB 真相不重複；寫檔前遮蔽疑似機密 |
| `traceability_matrix.json`（規格 §5） | — | — | — | `GET /autoclaude/runs/{id}/rtm`（`rtm.py:79`）；`research_deliveries.rtm_report_ref` 只存參照 | 不發明第二套 RTM |

### 11.4 系統參數 → 引擎設定對映（`API-SET-10`；Phase 4 起由 `ConfigMaterializer` 實作）

> **主控 2026-10-15 回寫**：`autoclaude.dalBackend → storage.mode` 的對映**實際不生效**——Bridge 固定 `yaml_only`（pause／restore 靠檔案式 checkpoint）；以 `config_overrides` 指定 `checkpoint_dir`／`log_dir` 亦不採用（落點由 Bridge 決定、`workspace` 欄位回報）。

「生效」欄：✅＝物化進 `config_overrides`／`env`／playbook；`Console`＝Console 內部使用；⛔＝只儲存不生效（引擎無對應欄位）；🟡＝待驗。引擎欄位以 `AutoClaude/autoclaude/utils/config.py` 為準。

| Console 參數 | 引擎落點 | 生效 |
|--------------|----------|------|
| `model.provider` | 無（Console 抽象層；引擎為 MiniMax＋Claude CLI 雙腦） | ⛔ |
| `model.apiUrl` | `minimax.base_url`（環境變數 `MINIMAX_BASE_URL`）；受 SEC-04 allowlist | ✅ |
| `model.apiKey` | 環境變數 `MINIMAX_API_KEY`（加密儲存；不入 config 檔與 log） | ✅ |
| `model.name` | `minimax.model`（環境變數 `MINIMAX_MODEL`） | ✅ |
| `model.timeout` | `minimax.timeout_seconds` | ✅ |
| `model.maxTokensPerRequest`／`temperature`／`topP`／`rateLimitPerMinute` | 無對應欄位 | ⛔ |
| `agent.defaultAutonomyLevel` | 建立執行時的預設自治等級 | Console |
| `agent.maxConcurrentTasks`／`execution.maxParallelGoals` | 無（引擎序列執行，§12 L-1） | ⛔ |
| `agent.taskTimeout` | `playbook.step_timeout_seconds` | ✅ |
| `agent.maxRetries` | playbook `global_invariants.max_retries_per_step`；任務 `maxRetries` 覆蓋 | ✅ |
| `agent.retryBackoffMs`／`retryBackoffMultiplier`／`checkpointInterval` | 無對應欄位（引擎只在 token halt、中斷、演化時寫 checkpoint；歷史快照由 Bridge 於每個步驟邊界自行產生） | ⛔ |
| `agent.enableAutoMutation` | `minimax.enable_kernel_brain`（Brain 逐步校正；與 `model.enableKernelBrain` 任一為真即開，自治等級 ≥ 6 視為要求）；**只在 `model.apiKey` 有值時送**（引擎對「旗標為真而沒有金鑰」是啟動即失敗）；批次回應回報 `engineCapabilities.autoMutation`（W7 契約 v1.3，D-11） | ✅（`apiKey` 有值時） |
| `agent.enableSelfEvolution` | **無有效對映（W7 已驗證）**：引擎沒有演化開關，AI 演化提案只由金鑰有無決定、且只提案不套用；`playbook.max_evolutions`／`require_evolution_signoff` 在引擎生產路徑沒有讀者，Console 不送（契約 §6.6.2、ADR-001 D20）。本鍵只影響無金鑰時 `engineCapabilities.selfEvolution` 報 `OFF` 或 `UNAVAILABLE_NO_API_KEY` | ⛔ |
| `execution.globalTokenBudget` | 建立執行時 `token_budget` 的預設 | Console |
| `execution.tokenBudgetWarningThreshold`、`monitor.*`（除 Email） | 告警閾值與刷新間隔 | Console |
| `execution.dagSchedulerStrategy` | `DagService` 同層排序 | Console |
| `execution.enableRollback` | 無 | ⛔ |
| `execution.logRetentionDays` | Console／Bridge workspace 清理排程 | Console |
| `execution.compactThresholdPct`／`haltThresholdPct` | `token_guard.compact_threshold_pct`／`halt_threshold_pct` | ✅（SEC-05） |
| `autoclaude.engineUrl`／`healthCheckPath`、`sdd.engineUrl` | Bridge 位址與健康路徑（console 讀；預設 `http://engine-bridge:8081`）。**`healthCheckPath` 的預設自 W7（D-17）起為 `/health/deep`**（v1.3 以前 `/health`；種子預設與既有列由 Flyway V11 校正，只改仍等於舊預設者，契約 §0.5） | Console |
| `autoclaude.eventBusType` | 無（僅 INTERNAL 存在） | ⛔ |
| `autoclaude.dalBackend` | **無有效對映**：Bridge 固定 `storage.mode=yaml_only`（pause／restore 靠檔案式 checkpoint；見本節開頭的 2026-10-15 回寫與 ADR-001 D13；`ConfigCatalog` 標 `STORED_ONLY`，契約附錄 C.5）。原稿的對映（FILE→`yaml_only`、POSTGRESQL→`both`、IN_MEMORY→`yaml_only`＋警告）**不生效**（W7 訂正，完整性審查 V-11①：此列原標 ✅，與同節開頭的回寫矛盾） | ⛔ |
| `autoclaude.playbookPath` | 無（Bridge 以 workspace 管理 playbook 檔） | ⛔ |
| `sdd.specFormat`／`workflowEngine`／`validationLevel` | 可能對映 `/sdd/compile` 行為 | 🟡 |

**V5 補充鍵（PRD §0.6 權威校正；`V5__seed_engine_configs.sql`，Phase 6）**

| 類別 | 鍵 | 預設 | 引擎落點 |
|------|----|------|----------|
| `autoclaude` | `claudeCommand` | `claude` | `claude.command` |
| `autoclaude` | `claudeExtraArgs` | （空） | `claude.extra_args` |
| `autoclaude` | `claudeContinueFlag` | `--continue` | `claude.continue_flag` |
| `autoclaude` | `claudeEncoding` | `utf-8` | `claude.encoding` |
| `autoclaude` | `dbDsn` | （空；ENCRYPTED） | 環境變數 `AUTOCLAUDE_DB_DSN` |
| `autoclaude` | `dualReadResolution` | `yaml_wins` | `storage.dual_read_resolution` |
| `model` | `enableKernelBrain` | `false` | `minimax.enable_kernel_brain`（W7：與 `agent.enableAutoMutation`／等級 ≥ 6 共用同一個引擎鍵，任一為真即開；有金鑰時顯式送 `true`／`false`） |
| `execution` | `autoResume` | `true` | `token_guard.auto_resume` |
| `execution` | `maxAutoResumes` | `10` | `token_guard.max_auto_resumes` |

## 12. 已知限制與待驗證項

### 12.1 已知限制

| 編號 | 限制 | 影響 |
|------|------|------|
| L-1 | AutoClaude Playbook 逐步序列執行 | 並行設定只儲存不生效；DAG 並行度恆為 1 |
| L-2 | Docker 映像不含 Claude Code CLI | 全棧預設走 mock；真 Claude 只在「Bridge 本機執行且 PATH 有 `claude`」可用 |
| L-3 | backend 只連 primary | replica 專供 DR，不分流讀取 |
| L-4 | 步驟級 at-least-once | pause／stop 後 resume 會重做被打斷的步驟，步驟須可重入 |
| L-5 | Windows 的 `terminate()` 為強制結束 | stop 的 30 秒寬限在 Windows 無意義；子行程樹須以 psutil 連帶清理 |
| L-6 | Bridge 無認證 | 只准 backend-net 可達；對 host 發布 8081 視為缺陷 |
| L-7 | 審核閘以 pause 近似實現 | 閘點精度受 SSE 延遲與步驟時長影響（極短步驟可能晚一步）；每個閘點＝一次 SIGTERM＋重新 spawn，引擎重啟成本與 `--continue` 對話延續性須實測（V-4） |
| L-8 | Docker 全棧下 `executionPath` 是 Bridge **容器內**的路徑 | 預設落在 `engine_workspace` 卷（`/workspace/` 之下）；要讓 Agent 改主機上的專案目錄，須另行 bind mount 並把掛載點加入 `BRIDGE_ALLOWED_PATH_ROOTS`；本機開發模式則直接是主機路徑（Windows 為含磁碟機代號的路徑，Bridge 以 `normcase` 比對）。UI 需提示兩種模式的寫法不同 |
| L-9 | **argv 長度上限（平台相依）**：引擎把每步 prompt 以命令列參數傳給 claude——Linux 單一參數上限 128KiB（`MAX_ARG_STRLEN`），Windows 整條命令列 32,767 字元，macOS 無單參數上限；超過即 spawn 失敗、run 判 FAILED（agentconsole-ci run 38621708871 以 50,000 個中文字實證） | 後端 Phase 4 編 Playbook 時對每步 prompt 設上限（建議 ≤ 20,000 字元）並回 422；Bridge 測試已改用 12,000 字。**已實作（2026-10-21 現查；回寫自體檢子代理 OBS-SI-203）**：`StepPrompt.MAX_LENGTH = 20_000`（`AgentConsole/backend/src/main/java/com/aisdlc/console/domain/service/StepPrompt.java`:26，以 `String.length()`＝UTF-16 code unit 計）；編 Playbook 時 `PlaybookBuilder.requirePromptsWithinLimit`（`…/domain/service/PlaybookBuilder.java`:170–181）超限拋 `UnprocessableException`＝422，`reason`＝`ErrorReasons.PROMPT_TOO_LONG`（帶 `taskId`／`stepId`／`length`／`limit`）；匯入面以 `GateError.PROMPT_TOO_LONG`（`prompt_too_long`，`ParsedResultValidator.java`:207–208、`ImportParser.java`:389）同限；單元測試 `StepPromptTest.java`:44（常數釘 20,000）、`PlaybookBuilderTest.java`:112–122（邊界）。20,000 個 UTF-16 code unit 在 Windows 整條命令列 32,767 字元以內（`StepPrompt.java`:20–21 的上限依據）；換成 UTF-8 最多約 60,000 位元組，在 Linux 單一參數 128KiB 以內（算術值，未另以真 spawn 實測） |
| L-10 | **引擎的「自演化」只提案、不套用**（W7 查證，契約 §6.6.2）：失敗型 ESCALATION 時只寫 `=== EVOLUTION PROPOSAL ===` 日誌；`KernelResult.evolved_playbook_path` 恆為 `None`，`AutoResumeService` 的演化重載迴圈進不去也沒有核可閘，`playbook.max_evolutions`／`require_evolution_signoff` 在生產路徑沒有讀者 | 等級 7～10 或 `agent.enableSelfEvolution` 不會讓引擎自動改寫 Playbook；Console 不送這兩個鍵，`engineCapabilities.selfEvolution=ENABLED` 的意思只是「有金鑰、會產生提案」。若日後 AutoClaude 讓 Kernel 真的套用演化，必須同時在 `AutoResumeService` 補核可閘，Console 才可回頭送這兩個鍵 |
| L-11 | **有金鑰的批次一律多出外呼，與旗標和等級無關**：最後一步之後一次目標驗證（`GoalSynthesisPlugin`，POST_RUN，fail-open，結果在 Kernel 路徑不套用）、每次失敗型 ESCALATION 一次演化提案；Brain 開啟時另加每個失敗且尚有重試次數的 attempt 一次校正。Docker 全棧的 `engine-bridge` 服務本身必填 `MINIMAX_API_KEY`，所以那種部署裡引擎**永遠有金鑰** | 外呼失敗時每個請求被引擎重試 3 次（退避 2＋4 秒），拉長完成時間但不改變結果；Console 只認 `model.apiKey`，Bridge 環境金鑰它看不到，`engineCapabilities` 因此是低估（契約 §3.4.2 劃界 1） |
| L-12 | **Console 的斷點清單與步驟時間軸依賴 Bridge 的 DB 模式**（W7，完整性審查 I-07）：`GET /executions/{runId}/checkpoints`、審核 `RETRY` 找還原點、事件時間軸（`steps`）都讀 `console` schema 的 `checkpoints`／`execution_steps`，而這兩張表**完全由 Bridge 寫入**（`engine-bridge/app/db.py`，§7）；`AgentBridge.listCheckpoints`（Bridge 的 `GET …/checkpoints`）在 `backend/src/main` 沒有呼叫者，只有 adapter 測試〔**已處理（2026-10-21 現查；回寫自體檢子代理 OBS-SI-203）**：`listCheckpoints` 已自 `AgentBridge` 刪除（完整性審查 I-07），`AgentConsole/backend/src` 全樹僅剩 `src/test/java/com/aisdlc/minibridge/MiniRun.java`:95 的註記句說明其刪除；原文「在 `backend/src/main` 沒有呼叫者，只有 adapter 測試」為刪除前的現況〕 | Bridge 以純檔案模式啟動（沒設 `BRIDGE_DB_DSN`）時，這兩個畫面會是空的（純檔案模式下的實際表現：**已由 W7-QA 實測取代**——兩個畫面確為空，結論見 `AgentConsole/CLAUDE.md`:108〈環境變數〉`BRIDGE_DB_DSN` 列；2026-10-21 回寫；〔訂正：原文「純檔案模式下的實際表現**待驗**」〕）。compose 與 e2e README 都有設 DSN，標準部署不受影響；本機開發跑 Console 時必須同時給 Bridge 一個 DSN——`AgentConsole/CLAUDE.md` 所載的純檔案模式只適用於單獨驗 Bridge。`listCheckpoints` 的死碼由 BE 另案刪除或補用途（完整性審查 V-11④；**已刪**，見上） |
| L-13 | **backend 不採用 JDT 註解式空值分析**（2026-10-19 掌舵者 IDE 診斷清單：VS Code Java 擴充的 `java.compile.nullAnalysis.mode` 預設 `automatic`，偵測到 classpath 上 Spring Framework 7／JSpecify 的空值註解即自動開啟，對每個未標註型別的方法參照報「Null type safety … needs unchecked conversion」，實測 185 筆；backend 原始碼沒有任何 `@NullMarked`／`@NonNull`，Gradle 編譯與測試不報、不是程式缺陷） | 開發機設定：在 VS Code 使用者或工作區設定把 `java.compile.nullAnalysis.mode` 設為 `disabled`（根 `.vscode/` 被 `.gitignore` 排除，無法隨 repo 分發，故以本列為唯一依據）。若日後要採用 JSpecify，須另立 ADR、逐 package 加 `@NullMarked` 並補齊可空標註，不得只開分析不標註 |
| L-14 | **SelfImproving 鏡像要求 Bridge 容器唯讀掛載 repo 的一部分**（SelfImproving PRD §9.7 FC-b；**〔P1b 已落地 2026-10-22：採設計 A，`docker-compose.yml` 六條長語法唯讀 bind＋`SI_ROOT=/repo`，`AT-932-4-4`／`AT-940-3-1` 靜態鎖；真容器掛載行為已於 2026-10-25 實測（P2b V3，見本列末段）〕**；T1：sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13）：Bridge 映像（`engine-bridge/Dockerfile`:33–34）只 COPY `AutoClaude/` 與 `engine-bridge/`、無 `.git`（`:27–30` 只安裝 `git` 執行檔並冒煙 `git --version`），現行 compose 只掛 `../AISDLC_SDD:/sdd:ro`、`engine_workspace`、`app_logs`（`docker-compose.yml`:217–219）；`/si/*` 以子行程呼叫根層 `tools/selfimproving.py export`，須由 compose 以**長語法**（`bind.create_host_path: false`）唯讀掛載六條到 `<SI_ROOT>`（`SI_ROOT=/repo`）：`../tools`、`../docs/06_quality`、`../.git/HEAD`、`../.git/refs`、`../.git/objects`、`../.git/packed-refs`；**不掛 `.git/config`**（remote URL 可能內嵌憑證，且 repo 的 remote URL 不得內嵌憑證）、**不掛 repo 根**（根下被忽略的 `AgentConsole/.env` 含 `JWT_SECRET`、`CONSOLE_ENCRYPTION_KEY`，而 Bridge 容器內跑的是引擎執行的使用者指令） | 未掛載或 `SI_ROOT` 未設＝`/si/*` 回 503 `si_unavailable`（不是空表）；`.git/packed-refs` 於主機不存在時，短語法會讓 Docker 在主機建立同名目錄而破壞 repo（故用長語法、來源不存在即啟動失敗）；單檔 bind mount（`HEAD`、`packed-refs`）在 git 以 lock＋rename 換檔（切分支、`pack-refs`）後，容器可能保留舊 inode ⇒ `head_sha` 靜默過期（**未實測**；備案＝掛整個 `.git` 唯讀並以空檔覆蓋 `.git/config`，P1b 以真容器二擇一）；`git` 對 bind mount 的擁有者檢查見 V-12；**〔P2b 已落地 2026-10-25：compose 恰一條可寫稽核 bind（長語法、`create_host_path: false`，主機目錄須預先存在）；真容器可寫 bind 權限已於 2026-10-25 實測（V3：容器內 uid 10001 對 `/si-audit`〔9p rw〕寫入成功、六條 `/repo` bind 皆 9p ro、`touch /repo/tools/.probe` 回 Read-only file system；主機讀得到容器寫的稽核檔並由 CLI 入帳 OBS-SI-308／309；主機目錄缺席時 compose 是否明確失敗與 Linux 主機仍未驗）〕**另需一個**可寫** bind mount：`BRIDGE_SI_AUDIT_DIR`（容器內稽核檔目錄）↔ 主機 `<AUTOSDD_SI_DIR>/console_audit`，只掛這個子目錄、不連帶掛家目錄其餘部分；缺＝寫入面 503 `si_write_disabled` |
| L-R1 | headless WebSearch／WebFetch 的逐筆呼叫 Bridge 觀測不到，只認 agent 在 `evidence_items.json` 宣告（`observed_by=AGENT_DECLARED`，查證層級 ≤V2）；Web 層預設關閉 | 審查發現宣告的 URL 不可開／內容不符→降級該來源並記缺陷 |
| L-R2 | 審查獨立性（R-9.20.3 型）在 AutoClaude 路徑結構上不成立：同一 AI、同工作區可互讀（BRIDGE §6.4:211-213） | 補償：分 run、`maintain_context:false`、聚合由碼、Gate 0 人工；**不宣稱滿足** |
| L-R3 | Docker 全棧無 `claude`／`gh`、無 repo 可寫 bind：真研究與軌道 A／B 的 git／GitHub 只在本機模式；容器模式只跑 mock claude 的 E2E | `GET /research/capabilities`（`mode`）＋UI 停用說明（D-29） |
| L-R4 | 工作區預設 repo 外（D-28）；若部署者把 `BRIDGE_RESEARCH_ROOT` 設到 monorepo 下，每個 `claude -p` 載入根 `CLAUDE.md` 鏈與根 hooks（token 成本、額度守衛干擾） | V-R2 負向驗證；根 `.gitignore` 仍加 `/my-project/` |
| L-R5 | `transition`／`gate` 為舊 CLI 契約（非單行 JSON） | Bridge 預檢＋事後驗證；再開症狀：誤判一次→框架 CLI 加 `--json` |
| L-R6 | 非 Python 標的無 AT 綁定（evaluator 只收 `pytest`，BRIDGE §7） | P1 只做 `python-fastapi`（D-32）；其餘棧警告「無凍結綁內容」 |
| L-R7 | 狀態檔 load-modify-save 無跨行程鎖（同 BRIDGE §6.10:301） | 研究面只由 Bridge 單行程寫外環鍵；人在 SDD session 手動並寫＝已知競態 |
| L-R8 | 軌道 B `gh repo create` 與建 PR 需操作者本機 `gh` 已登入或請求帶 token | `capabilities.ghCli`；V-R8 |
| L-R9 | `research_events` 與 `research_projects.last_event_seq` 配號在單一 Bridge 行程下安全；多實例 Bridge 需改用序列或 advisory lock | 現行單 worker（`Dockerfile:57`）；再開症狀：Bridge 水平擴展 |
| L-R10 | Stack Exchange 速率限制官方數值未現查（官方頁無法抓取；arXiv、GitHub、Semantic Scholar 已現查並回填 PRD NFR-R2P-03-6） | 保守節流初值（非事實宣稱）＋遵守伺服器回傳限流訊號；V-R9 殘餘落證 |
| L-R11 | 框架對 HUMAN_PENDING 的 72 小時提醒／168 小時升級只由 hooks SessionStart 執行（`SDD_FSM_ENGINE.md:433-434`；`.claude/hooks/session_start.py:279`）；Console 路徑沒有 hooks（D-48(3)） | P0 以 UI 顯示等待時長＋滿 72 小時橫幅提醒，不轉 REMINDER、不自動升級（PRD AC-R2P-09-10、NFR-R2P-06-5）；再開症狀：掌舵者回報因 Gate 0 久未核准而錯過提醒 |
| L-R12 | ESCALATION 人工恢復後的重試計數不歸零：引擎的 `resume-from-escalation` 不動 retry 計數（只有 `gate PASS` 與 `spec-frozen` 歸零）；`increment_retry` 見計數已達上限時把 `current_count` 夾在上限，並在該筆歷史的 `failure_reason` 標「(tamper detected: …)」字樣——這是引擎對「已達上限後再 FAIL」的既有標記（`state_loader.py:211-269`），不是研究面被竄改 | 恢復後至多再得一次審查（PASS 歸零、FAIL 立即再 ESCALATION；D-60）；歷史列照引擎原文顯示、不改寫也不隱藏；全新預算＝換世代（API-RP-20 `generation:"next"`）；再開症狀：掌舵者要求恢復後重新得 3 輪（須先改引擎 `state_loader.py` 與 TLA+，或走換世代） |

### 12.2 待驗證項（誰在哪一波負責驗；結論須回寫本表）

| 編號 | 待驗項 | 驗證方式 | 負責 |
|------|--------|----------|------|
| V-1 | 步驟邊界的判定來源：W1-B 已對真引擎實證「引擎不寫步驟級 checkpoint，邊界由日誌的下一步驟啟動行推得，checkpoint 由 Bridge 於 pause 時寫入」（其 `runner.py`／`logparse.py` 檔頭自述）；待其 pytest「pause 在步驟邊界」全綠與交卷確認。**結論（2026-10-21 現查；已驗）**：W1 出口閘由主控親跑（`Implementation_Plan.md` §5.1 W1 列）；`engine-bridge/tests/test_e2e_lifecycle.py`:80–121 `test_pause_stops_at_the_step_boundary_and_resume_continues_from_the_checkpoint` 斷言邊界＝第一步完成後、第二步開始前（`completed_steps==1`、引擎行程已退出、Bridge 的 `after-T01` checkpoint 與引擎自己帶 `checksum_sha256` 的 checkpoint 並存），resume 由引擎日誌「已載入檢查點: step_idx=1 [T02]」證明接續、T01 不重做；W4-QA 真後端 `p4b-execute-more.spec.ts` 情境 2（手動暫停／恢復：PAUSED 時沒有懸空的 `STARTED`、每步恰一次；`docs/06_quality/QA_P3-6_E2E_Verification.md` §4.3）與 `p4-execute.spec.ts` 情境 2、3（目標邊界與 Level 1 的 `TASK_CONFIRM` 暫停；同檔 §4.2）。邊界訊號定案＝引擎 stdout 的步驟啟動行（`agent_briefs/DOC_CORRECTIONS.md`:12 D8 加註）；at-least-once 語意＝L-4 | Bridge pytest | W1-B |
| V-2 | SIGTERM（Windows：`terminate()`）後引擎乾淨退出、checkpoint 完整可續跑。**結論（2026-10-21 現查；已驗，Windows 另有註記）**：`engine-bridge/tests/test_e2e_lifecycle.py`:80–121（PAUSED 時 `psutil.pid_exists(engine_pid)` 為假；checkpoint 帶 `checksum_sha256`；resume 接續）、:124–138（stop 後無孤兒 claude 子行程）、:141 起（忽略 SIGTERM 的子行程於寬限期後被強殺）；Windows：`Implementation_Plan.md` §5.1「Windows 接續」列——Bridge pytest 首跑唯一失敗是 `tests/test_procutil.py::test_terminate_takes_the_grandchild_too` 的等號斷言（venv 的 `python.exe` 是啟動器、行程樹多一層），改為 win32 超集合斷言後該檔全過；`terminate()` 在 Windows 為強制結束＝L-5；W4 起整套於 Windows 由主控親驗（同檔 §5.1 W4 列：真後端 Playwright 八支 spec rc=0） | Bridge pytest（pause→resume 接續）＋Windows 實跑 | W1-B、Windows 接續 |
| V-3 | 引擎 Token Guard halt 與 ESCALATION 的判定：W1-B 目前判為 FAILED 並發 `alert`；console 端的對映（任務→ESCALATED、審核項）與以 `restore` 續跑的路徑須驗證。**結論（2026-10-21 現查；ESCALATION 路徑已驗、Token Guard halt 部分未驗）**：ESCALATION——Bridge 判 run `FAILED`（reason 以「引擎升級（ESCALATION）」開頭）並發 `alert`；console 端 `backend/src/main/java/com/aisdlc/console/application/service/RunEventProcessor.java`:70、:314 以該前綴把失敗任務標 `ESCALATED` 並建審核項（`RunEventProjectionIT.java`:446–460 斷言任務 `ESCALATED`、審核項 `kind=ESCALATED`）；W4-QA 真後端 `p4-execute.spec.ts` 情境 4（`[FAIL_ME]`：RETRY 同批次還原重跑再失敗、SKIP 另開後續批次、REJECT；`QA_P3-6_E2E_Verification.md` §4.2）與情境 5（終態批次從 `after-G1-T1` 以 `restore` 還原續跑）。Token Guard halt——Bridge 的 reason 是「引擎因 token／額度門檻停機（halted），未自動續跑」（`engine-bridge/app/runner.py`:629–630）並發 `TOKEN_HALT` alert；console 只把它映成 `ENGINE_TOKEN_HALT` 告警（`RunEventProjectionIT.java`:361–367），**不當作 ESCALATION**（`RunEventProcessor.java`:314 只認前綴「引擎升級（ESCALATION）」；讀碼所得、無對應 E2E，與 §6(c) c.4 第 3 點「Token Guard halt 同理」的字面不一致，以程式為準；§6 不在本次回寫範圍，未改）。**未驗、再開症狀**：真引擎因 Token Guard 停機的批次在 Console 顯示非預期的任務或專案狀態（附 run id 與 Console 畫面） | Bridge 測試＋後端對映測試 | W1-B／W3 後端 |
| V-4 | 審核閘提前 pause 的精度；ESCALATED 後 retry／skip 的可行路徑；Bridge 對 escalation 的狀態判定。**結論（2026-10-21 現查；功能已驗、精度項未量測）**：審核閘功能情境已過——Level 1 第一步後 `PAUSED`＋`TASK_CONFIRM`、Level 3 目標邊界 `GOAL_COMPLETED`（`QA_P3-6_E2E_Verification.md` §4.2 情境 2、3）、Level 2 `GOAL_CONFIRM`（同檔 §4.3 情境 3）；ESCALATED 後的可行路徑：RETRY＝同批次還原重跑（再失敗則出現第二個審核項）、**SKIP＝標任務 SKIPPED 並以剔除該任務的新 playbook 開後續批次**（Bridge 的 `resume` 只收 `PAUSED`、`restore` 無法跳過步驟；契約 D-20，見 `API_Contract_P3-6.md` 的 D-20 段）、REJECT 只關審核項（§4.2 情境 4、§4.3 情境 5）；Bridge 對 escalation 的判定見 V-3。**未驗、再開症狀（L-7 的精度）**：極短步驟下「閘點晚一步」（被審核的步驟已執行完才暫停）——E2E 的步驟長度皆足以先到閘點，未做壓力量測；症狀＝審核卡出現時被審步驟的 `COMPLETED` 事件已先到 | 後端 E2E（mock CLI，製造失敗步驟） | W3 後端、W4 QA | <!-- baseline-ok: 本列的 SKIPPED 是任務狀態字、2026-10-21 是現查日期，不是 pytest 基線數字 -->
| V-5 | `internal` 網路上的發布埠可達性（D14-10）；nginx→backend 連通（G-01）。**結論（2026-10-21 現查；已驗）**：D14-10——ADR-001 §6 E-5（2026-10-15 實跑）：只掛 internal 網路的玩具容器，主機連發布埠被拒；正式堆疊只掛 `db-net` 的 primary／replica，主機連 5432、5433 皆被拒，5050、9090、3001 可連（`AgentConsole/docker/README.md`〈9〉#10）；W7-QA 唯讀重驗（`QA_W7_Closure.md` §8.3，`INF-NET-01`～`INF-NET-03`）：`db-net` 為 `internal=true`，pg-primary、pg-replica、redis、minio、pgbackrest 的 `docker port` 全空，對主機發布的只有 nginx 80／443、pgadmin 5050、prometheus 9090、grafana 3001（「主機連 5433 被拒」不能當證據——主機 5433 有本機原生 PostgreSQL 在聽）。G-01：W5-QA 在 Docker 全棧經 nginx 同源跑 Playwright 全數通過（`QA_W5_Reverification.md` §6） | `docker compose exec` 與 host 端連線測試 | W2-B |
| V-6 | Spring Boot 4 相容：springdoc、jjwt（Jackson 3）、Testcontainers、Flyway 對 PG18。**結論（W2-A，2026-10-14，已驗證）**：Spring Boot 4.1.1＋Hibernate 7.4.5＋Flyway 12.4.0 在 PG18.6 套用 V1～V4 並通過 `ddl-auto=validate`；springdoc 3.1.1 可用（真伺服器上 `/v3/api-docs`、Swagger UI 皆回 200）；jjwt 0.12.7 的 jackson-databind（Jackson 2，BOM 對齊 2.21.5）與 Spring 的 Jackson 3.1.5 並存、簽發與驗證實測正常；Testcontainers 以 `pgvector/pgvector:pg18` 可跑；注意 `@SpringBootTest` 預設關閉指標匯出，測 `/actuator/prometheus` 須設 `management.prometheus.metrics.export.enabled=true` | `./gradlew clean build` | W2-A |
| V-7 | Tremor Raw 於 Tailwind 4 的 build＋render。**結論（已驗〔W3-A 完成時〕；2026-10-21 回寫）**：圖表 spike **成功**——Tremor Raw AreaChart＋recharts 2.15.4，須 `overrides.react-is`＝19.3.0（ADR-002 §D6；回填 ADR-001 §6 E-3；`Implementation_Plan.md` §5.1 W3-A 列） | 圖表 spike（ADR-002） | W3 前端 |
| V-8 | `@uiw/react-md-editor` 與 React 19／Next 16 相容；`enableAutoMutation`／`enableSelfEvolution`、`sdd.*` 的引擎對映。**W7 結論（2026-10-16，契約 §6.6.2）**：`enableAutoMutation` 已驗證對映 `minimax.enable_kernel_brain`；`enableSelfEvolution` 已驗證**無有效對映**（見 L-10）；`sdd.*` 仍待驗 | 前端 build＋行為測試；後端對映測試 | W3 |
| V-9 | Bridge 草案（`draft_id`）存放方式：W1-B 實作為 `<workspace>/_drafts/<draft_id>.json`（檔頭自述），重啟後仍可 approve。**結論（2026-10-21 現查；已驗）**：實作與自述一致——`engine-bridge/app/main.py`:80 以 `DraftStore(cfg.engine_workspace / "_drafts")` 建構、`app/decompose.py`:9 檔頭自述；`tests/test_decompose.py`:157–165 `test_a_draft_survives_a_bridge_restart`：第一個 Bridge 分解後停止，第二個 Bridge 對同一 `draft_id` `:approve` 回 200 且 playbook 逐項相同 | 待其測試與交卷確認 | W1-B |
| V-10 | `pgbackrest_*` 指標的產出方式（G-04）。**結論（2026-10-21 現查；已驗）**：產出方式＝pgbackrest sidecar 的 `pgbackrest-metrics.sh` 每 60 秒以 `pgbackrest info --output=json` 產生 Prometheus 文字格式，busybox httpd 在 `:9854/metrics` 提供（`AgentConsole/docker/README.md`:387；Prometheus 目標 `pgbackrest:9854`，`docker/prometheus/prometheus.yml`:33）；W7-QA 實測（`QA_W7_Closure.md` §8.3）：該目標 up，備份後 `pgbackrest_stanza_status`＝0、`pgbackrest_backup_since_last_full_seconds` 與 `pgbackrest_backup_last_status` 皆有序列；新部署尚無備份時這兩個序列不存在，屬預期（`alerts.yml` 註解） | Prometheus targets 與指標查詢 | W2-B |
| V-11 | Bridge 與 SSOT 對「SDD LATEST」的判定可能分歧（完整性審查 I-04）：Bridge 取 `engine-bridge/app/settings.py` 的「目錄名數字最大的 `AISDLC_SDD_v<M>.<N>`」（不看 git），SSOT `tools/lib/sdd_latest.py` 以 `git ls-files` 判定；兩者在「工作樹有未入庫的版本目錄」時**實驗確認分歧**（W7-QA 以拋棄式 git repo 比對：v9.99 只在工作樹時 SSOT 回 v0.30 並警告未 tracked、Bridge 回 v9.99；`git add` 後兩者一致；`.bak` 與「- Copy」兩者都排除；登 DEF-AC-012，P4，主控裁決保留——分歧只在有未入庫版本目錄的開發機出現，正式部署的 `SDD_ROOT` 掛載面沒有未入庫目錄）。CI 路徑過濾已於 W7 補 `AISDLC_SDD/scripts/**` 與 `AISDLC_SDD/*/tools/fsm_runtime/**` | 若要消除分歧，Bridge `settings.py` 改呼叫 SSOT（需 git 可用；Docker 映像內沒有 `.git`，所以要另定無 git 時的退路）；暫以文件登記 | 主控（保留） |
| V-12 | **〔P1b 已落地 2026-10-22；真容器未實測〕**容器內 `git` 的 `safe.directory` 環境變數式放行對唯讀 bind mount 是否足夠（SelfImproving PRD §9.2 鐵律三自問表、§9.7 FC-b；T1：sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13）：映像使用者 uid 10001 與主機擁有者不同，`git` 會報 `dubious ownership`；放行法＝`GIT_CONFIG_COUNT=1`、`GIT_CONFIG_KEY_0=safe.directory`、`GIT_CONFIG_VALUE_0=<SI_ROOT>`（只對該路徑，不用 `*`），映像 `git --version` 須 ≥ 2.31。**結論（2026-10-25 真容器實測；已驗）**：`docker compose exec -T -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo engine-bridge sh -c 'git -C /repo rev-parse HEAD'` 回主機 HEAD（`5997bb1a…`），不帶放行回 `fatal: detected dubious ownership`（rc 128）；bind 在容器內擁有者 uid 0、Bridge 程序 uid 10001、映像 git 2.47.3；`GET /api/v1/si/status` 的 `headSha` 等於主機 HEAD、`ne` 為空。P1b 實作已把環境變數式放行寫進 `engine-bridge/app/si_cli.py`（`GIT_CONFIG_COUNT=1`、`GIT_CONFIG_KEY_0=safe.directory`、`GIT_CONFIG_VALUE_0=<SI_ROOT>`，單元測試釘住），真容器行為已驗（上述）；再開症狀＝容器內 `export` 的 `head_sha` 回 `null` 並於 `ne` 列 `git`（附 stderr 的 `dubious ownership` 字樣） | P1b 實作輪以真容器驗：`docker compose exec -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo engine-bridge git -C /repo rev-parse HEAD`（bash 與 PowerShell 同形） | P1b 開發（鍵 `agentconsole-si-mirror`） |
| V-R1 | headless `claude -p` 的 `--allowedTools "WebFetch(domain:…)"` 語法與無提示行為 | 暫存目錄 `claude -p --permission-mode acceptEdits --permission-prompts none --allowedTools … "<一句提示>"`，看 rc 與輸出（PowerShell 與 bash 同形） | PKG-BR-C 開發棒（P0，本機模式） |
| V-R2 | 負向：repo 外工作區不載入根 `CLAUDE.md` 鏈與根 hooks、每回合 token | 同一提示分別在 repo 外工作區與 repo 內 `my-project/x` 各跑一次，比 `--output-format json` 的 usage 與 `--debug hooks` | PKG-BR-C＋主控（P0） |
| V-R3 | Windows `-p <prompt>` 命令列長度與 `.prompts/` 參照法 | 構造 20 KB／40 KB 提示對比 | PKG-BR-C（P0） |
| V-R4 | httpx 釘 IP＋SNI 的可行性 | 單元測試對本機假伺服器；不可行則退回「解析後比對 IP 非私網」 | PKG-BR-B（P0） |
| V-R5 | 無 `MINIMAX_API_KEY` 時 evaluator 失敗後的重試行為 | mock claude＋失敗 evaluator 觀察 `engine-N.log` | PKG-BR-C（P0） |
| V-R6／V-R7 | 新狀態目錄首次 `show`（不帶 `--must-exist`）建檔行為、第 3 次 FAIL 後現態；`spec-frozen --stage Gate-0 --digest --root <工作區>` 的相對 `--doc` 與摘要 | 暫存 `SDD_STATE_DIR` 下實跑（腳本見 `ResearchToPRD_Plan.md` 附錄） | PKG-BR-A（P0） |
| V-R8 | Bridge 環境下 `gh auth status`／`GH_TOKEN` 行為 | 本機模式 | P1 的 route 棒 |
| V-R9 | Stack Exchange 官方速率限制（arXiv、GitHub、Semantic Scholar 主控已現查並回填 PRD NFR-R2P-03-6） | 以官方頁 `https://api.stackexchange.com/docs/throttle` 現查，回填 PRD NFR-R2P-03-6 與 allowlist 條目 | PKG-BR-B（P0） |
