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
| 7 | redis | `redis:7-alpine` | 6379 | 不發布 | db-net | D16 |
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
| 4 | postgres-primary（healthy） | 1.0／1G | `curl -f http://localhost:8081/health`；30s／10s／5 次；start 30s |
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

> 清單以 `docker compose config --volumes` 輸出為準（共 11 個）。

## 3. 目錄地圖

```
AgentConsole/
├── CLAUDE.md / README.md / docker-compose.yml / docker-compose.dev.yml / .env.example
├── docs/{02_architecture,04_planning,06_quality}/
├── frontend/            Next.js 16（app/ components/{layout,ui,charts,markdown,domain} lib/ styles/ tests/ Dockerfile）
├── backend/             Spring Boot 4.1 / Java 21（src/main/java/com/aisdlc/console/{adapter,application,domain,infrastructure}；src/main/resources/db/migration/V1__init.sql；Dockerfile）
├── engine-bridge/       FastAPI（app/{main.py,settings.py,runner.py,events.py,locks.py,db.py,security.py,routers/{autoclaude.py,sdd.py}} tests/ pyproject.toml Dockerfile .venv/）
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
| `frontend/lib/` | `api/`（client、endpoints、`schema.d.ts`）、`auth/`、`domain/status.ts`、`sse/`（fetch 串流客戶端） | W3 |
| `frontend/styles/` | `tokens.css`（設計稿 token 逐字搬入）與全域樣式 | W3 |
| `frontend/tests/` | vitest 單元測試與 `e2e/`（Playwright，含 `__screenshots__/`） | W3／W4 |
| `backend/src/main/java/com/aisdlc/console/` | Clean Architecture 四層（§4） | W2／W3 |
| `backend/src/main/resources/db/migration/` | Flyway 遷移 V1～V5（ADR-001 D5） | W2／W3 |
| `backend/src/test/` | 單元、ArchUnit、Testcontainers 整合測試 | W2／W3 |
| `engine-bridge/app/` | `main.py`、`settings.py`、`runner.py`、`events.py`、`locks.py`、`db.py`、`security.py`、`models.py`、`routers/{autoclaude,sdd}.py` | W1-B |
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

- 方法對映 §10 契約：`health`、`startRun`、`pause`、`resume`、`stop`、`getRun`、`streamEvents(runId, afterSeq)`、`replayEvents(runId, afterSeq, limit)`、`listCheckpoints`、`restore`、`decompose`、`approveDraft`、`sddVersion`、`sddFsm`、`sddCompile`。
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
├── import/page.tsx                 # BRD/PRD 匯入解析（UI-SCR-06）
├── settings/page.tsx               # 系統參數設定（UI-SCR-09）
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
| 240px: 6 nav items  | route content container: scroll, max-width 1440    |
| + my-projects rail  |                                                    |
+---------------------+----------------------------------------------------+
| BottomRegion  Engine Bridge status dot, version, Toast host              |
+--------------------------------------------------------------------------+
```

| 區塊 | 唯一元件檔 | 對應設計稿 | 內容 |
|------|-----------|------------|------|
| Top | `frontend/components/layout/TopRegion.tsx` | Topbar＋Masthead | 公告列（說明文件、下載 CLI、GitHub、Bridge 狀態、通知、幫助、語言、使用者徽章）；logo；搜尋列與 recent chips；通知鈴；signoff 佇列鈕（draftCount badge） |
| Tools | `frontend/components/layout/ToolsRegion.tsx` | Sidebar | 導航六項（儀表板、專案管理、BRD/PRD 匯入、執行、監控、系統設定）；「我的專案」rail（狀態點＋專案名） |
| Content | `frontend/components/layout/ContentRegion.tsx` | Main | 路由內容容器；`children` 由 `app/layout.tsx` 傳入 |
| Bottom | `frontend/components/layout/BottomRegion.tsx` | （設計稿無；依掌舵者四區塊要求新增） | Engine Bridge 連線狀態點、版本號、Toast 宿主；不得放任何新功能 |

**硬規則**：
1. `app/layout.tsx` 是唯一組裝處；任何 `app/**/page.tsx`、巢狀 `layout.tsx` 不得 import 這四個元件，也不得自帶其內容。
2. **三個共用區塊（Top／Tools／Bottom）各只有一個元件檔，改一處全站生效**；Content 是路由容器，不是第四份導覽。
3. 響應式（PRD §8.3）：≥1280 完整側欄；768～1279 側欄收合為圖示；<768 以底部 Tab 導航取代側欄——三者都在 `ToolsRegion.tsx` 內以響應式切換，不另開元件檔。
4. 機械檢查（期望輸出為空；有任何一行輸出＝有頁面違規組裝了共用區塊）：

```bash
grep -rnE "TopRegion|ToolsRegion|BottomRegion" AgentConsole/frontend/app --include='*.tsx' | grep -v 'app/layout.tsx'
```

```powershell
Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
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

## 6. 資料流四條

### 6(a) CRUD（US-P／G／T、API-PRJ／GOL／TSK）

1. 瀏覽器 → nginx `/api/v1/**`（本機開發則直連 8080）→ backend；帶 `Authorization: Bearer`，`X-Trace-Id` 缺則由後端生成。
2. `JwtAuthenticationFilter` → RBAC（§8.2）→ Controller（`adapter.in.web`）→ Bean Validation → UseCase（`application.service`，`@Transactional`）。
3. UseCase 經 Repository 埠載入聚合 → 領域方法（狀態機守門、signoff 預設、Kahn 防環）→ 經埠儲存 → JPA 轉接器 → `console.*`。
4. 回應包 `{code,message,data,timestamp,traceId}`；分頁 `data={content,page,size,totalElements,totalPages}`；錯誤由 `GlobalExceptionHandler` 輸出 `{code,message,errors[],timestamp,traceId}`。
5. 軟刪除：`is_deleted=true`；專案同時 `status=ARCHIVED`；連帶軟刪其目標與任務；EXECUTING 的專案、RUNNING 的任務回 409。
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

1. `RunEventConsumer` 讀 Bridge `GET /autoclaude/runs/{run_id}/stream?after=<seq>`；斷線以最後 `seq` 重連，缺口用 `GET .../events?after=&limit=` 回補；位移存 Redis（`console:run:{runId}:last_seq`），無 Redis 退回記憶體。
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
| 6～10 | 同 5；等級傳遞給引擎（`agent.enableAutoMutation`／`enableSelfEvolution` 的對映見 §11.4，待驗） | 無 | — |

1. 停在閘點時：Bridge 狀態 `PAUSED`；console-api 新增 `review_requests`（`PENDING`）並對前端發 `review-request`（導覽 Badge 計數＝待審核數）。最後一個目標的最後一步完成時 run 直接 `COMPLETED`，不再 pause、也不建立審核項。
2. `POST /executions/{runId}/review/{stepId}`（`ReviewRequest{decision: APPROVE|REJECT|RETRY|SKIP, comment?}`；審核人取自 JWT subject）：

| 決定 | 動作 |
|------|------|
| APPROVE | Bridge `:resume` |
| RETRY | 目標審核：`restore` 到該目標第一個步驟之前的 checkpoint；任務 ESCALATED：run 此時為 FAILED 態（Bridge 的 `resume` 只收 PAUSED），改用 `restore` 回到失敗步驟之前的 checkpoint（Bridge 的 `restore` 接受終態 run；終態已放的鎖須重新取得，可能 409） |
| SKIP | 僅限 ESCALATED 任務：標記任務 SKIPPED，並以剔除該步驟的 Playbook 重新啟動（`fresh=false`）；**可行性待驗（V-4）**，不可行則於 RTM 記 `🟡` 並登缺陷 |
| REJECT | Bridge `:stop` → `CANCELLED`；目標標 FAILED |

3. 引擎自行 ESCALATION（重試耗盡）：W1-B 目前把它判為 run `FAILED`（reason 以「引擎升級（ESCALATION）」開頭），並發 `step` FAILED 與 `alert` 事件；console-api 辨識該 reason，把任務標 `ESCALATED` 並建立審核項。Token Guard halt 同理（reason 帶「halted」）。人工處置走 `restore`（V-3、V-4；以 W1-B 交卷為準）。

**c.5 終態與對帳**：`COMPLETED／FAILED／CANCELLED` → 關閉消費者、更新專案／目標／任務狀態（§7.3）；console-api 啟動時對所有 `RUNNING／PAUSED` 的 run 呼叫 `GET /autoclaude/runs/{id}` 對帳（狀態只讀，不回寫 Bridge 擁有的欄位）；Bridge 回 404 → 發 `alert`「Bridge 失聯」，由 Bridge 自己的啟動回收把孤兒標 FAILED。

### 6(d) 監控（US-M、API-MON／ALR）

1. 資料來源：`execution_runs`、`execution_steps`、`tasks`、`goals`、`projects`、`checkpoints`、`alerts`；Agent 狀態來自 console-api 對 Bridge `/health` 的定期探測（結果環形緩衝存 Redis，無則記憶體）。

| KPI（`UI-KPI-*`） | 計算（資料來源） |
|-------------------|------------------|
| 專案完成率 | `projects`：COMPLETED ÷ 非 ARCHIVED 總數 |
| 目標達成率 | `goals`：COMPLETED ÷ 總數 |
| 任務成功率 | `tasks`：COMPLETED ÷（COMPLETED＋FAILED＋ESCALATED） |
| 平均重試次數 | Σ`tasks.retry_count` ÷ 已執行任務數 |
| Token 總消耗 | Σ`execution_runs.total_tokens_used` |
| Token 預算使用率 | `total_tokens_used` ÷ `token_budget` |
| 平均任務執行時間 | avg(`tasks.completed_at − started_at`) |
| Agent 可用率 | 窗口內健康探測成功次數 ÷ 總探測次數 |

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

JWT（HS256）；access 30 分鐘、refresh 7 天；`POST /api/v1/auth/login`、`/auth/refresh`；使用者清單在 `application.yml`（bcrypt）；`JWT_SECRET` 必填且 ≥32 字元；前端存 `sessionStorage`；SSE 以 fetch 串流帶 Bearer，禁止 query-string token。

### 8.2 RBAC（NFR-9.2-02；SA 設計，PRD §9.2 只列角色名）

| 能力 | 匿名 | Viewer | Operator | Admin |
|------|------|--------|----------|-------|
| 登入、續期、`/actuator/health`、`/v3/api-docs`、`/swagger-ui/**` | ✅ | ✅ | ✅ | ✅ |
| 讀取專案／目標／任務／匯入記錄／執行／監控／SSE 串流 | — | ✅ | ✅ | ✅ |
| 讀取系統參數（敏感值遮罩）、匯出監控報表 | — | ✅ | ✅ | ✅ |
| 專案／目標／任務的建立、編輯、刪除、重試 | — | — | ✅ | ✅ |
| signoff（匯入／專案／目標／任務） | — | — | ✅ | ✅ |
| 匯入 upload／text／parse／編輯／confirm | — | — | ✅ | ✅ |
| 執行 execute／pause／resume／cancel／restore／review | — | — | ✅ | ✅ |
| 告警確認 | — | — | ✅ | ✅ |
| 修改系統參數（單鍵、token-guard、reset、匯入設定） | — | — | — | ✅ |
| 測試模型連線、匯出設定（不含敏感明文） | — | — | — | ✅ |
| 揭露敏感參數明文（US-S-04「顯示」；每次寫審計） | — | — | — | ✅ |

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

### 8.4 NFR-SEC-04：外呼預設 deny＋allowlist，與 SSRF 防護

> **誠實劃界（主控 2026-10-15 回寫）**：Bridge 的 SEC-04 實作為精確 host 白名單＋兩種 URL 解析器一致性校驗＋拒絕 userinfo／反斜線／IDN 差異／十進位與十六進位 IP 寫法＋私網 IP 除非明列否則拒絕；**DNS 解析後驗 IP 與釘住連線 IP 未做**（實際外呼由引擎行程自己解析，Bridge 釘不住），decompose 的 httpx 不跟隨 redirect。後端 Phase 6 的 `test-connection` 須自行補 DNS 解析後驗 IP。

- **範圍**：(a) console-api 的 `POST /settings/test-connection` 與任何由 Console 發起的 HTTP；(b) Bridge 對 MiniMax 等模型端點的外呼（`config_overrides` 的 `minimax.base_url`、環境變數 `MINIMAX_BASE_URL`）。
- **規則**：預設 deny；域名 allowlist（Bridge：`BRIDGE_OUTBOUND_ALLOWLIST`；console：`console.security.outbound-allowlist`）；校驗欄位明列 `model.apiUrl` 與 `MINIMAX_BASE_URL`；**禁私網段與 loopback／link-local**（`127.0.0.0/8`、`10/8`、`172.16/12`、`192.168/16`、`169.254/16`，另補 IPv6 的 `::1`、`fe80::/10`、`fc00::/7`）；禁 DNS rebinding（解析後驗 IP、連線用已驗 IP）；禁 redirect 跳出 allowlist（不自動跟隨，或每一跳重驗）；全程審計 log。
- **本機例外**：`localhost`／`127.0.0.1` 只在 e2e／本機開發 profile 的 allowlist 內明列時放行（供 `mock_brain_server.py`）；Docker 全棧預設 allowlist 不含 loopback 與私網。

### 8.5 NFR-SEC-05：token_guard 群組校驗

- `compactThresholdPct` 與 `haltThresholdPct` 皆 1～100 且 **halt > compact**。
- 執行點：① `PUT /settings/execution/token-guard` 原子事務＋跨鍵校驗，不滿足回 400（`reason:"halt_threshold_pct 必須大於 compact_threshold_pct"`）；② `PUT /settings/{category}/{key}` 直接更新單鍵時讀對端鍵一併校驗（禁止逐鍵繞過）；③ 前端表單以 zod 鏡射同一規則；④ 引擎自身 `TokenGuardConfig` 的驗證為最後一道。
- **不得經 Console 繞過安全收斂**：config_overrides 只傳 `compact_threshold_pct`、`halt_threshold_pct`、`auto_resume`、`max_auto_resumes`，不暴露 `token_guard.enabled`。

### 8.6 其他控制

| 項目 | 設計 |
|------|------|
| 敏感資料（NFR-9.2-03） | `is_encrypted` 欄位以 AES-256 加密儲存；金鑰由環境變數 `CONSOLE_ENCRYPTION_KEY` 提供（缺則禁止寫入敏感參數）；明文不入 log、不回傳（除 Admin 揭露） |
| CORS（NFR-9.2-05） | 只允許 `console.cors.allowed-origins`（開發預設 `http://localhost:3000`）；全棧同源，經 nginx |
| Rate Limit（NFR-9.2-06） | 每分鐘 100 次（以 Redis 計數；無 Redis 退回記憶體） |
| 審計（NFR-9.2-07） | 每次寫入輸出 `audit` 結構化 JSON 日誌（subject、method、path、目標 id、status、traceId）；PRD §6.2 無審計表，故不新增資料表 |
| SQL 注入（NFR-9.2-04） | 全部經 JPA／參數化查詢；Bean Validation 於 Controller 邊界 |
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
| `SPRING_DATA_REDIS_HOST`／`_PORT` | backend | 容器：`redis`／`6379`；本機未起 Redis 則不設（退回記憶體） |
| `ENGINE_BRIDGE_URL` | backend | 本機 `http://localhost:8081`；容器 `http://engine-bridge:8081` |
| `BRIDGE_HOST`／`BRIDGE_PORT`／`ENGINE_WORKSPACE`／`AUTOCLAUDE_ROOT`／`SDD_ROOT` | Bridge | 預設 `127.0.0.1`（Docker CMD 另帶 `0.0.0.0`）、8081、`engine-bridge/.workspace`、monorepo 內的 `AutoClaude`、`AISDLC_SDD` 下數字最大的版本目錄（以 `engine-bridge/app/settings.py` 為準） |
| `BRIDGE_DB_DSN`／`BRIDGE_DB_SCHEMA` | Bridge | 無 DSN＝純檔案模式；schema 預設 `console` |
| `BRIDGE_INSTANCE`／`BRIDGE_STOP_GRACE_SECONDS` | Bridge | 預設 hostname＋pid＋uuid4／30 |
| `BRIDGE_ALLOWED_PATH_ROOTS`／`BRIDGE_OUTBOUND_ALLOWLIST` | Bridge | 路徑 allowlist 以 `os.pathsep` 分隔（POSIX `:`、Windows `;`）；外呼 allowlist 以逗號分隔（§8.3、§8.4） |
| `MINIMAX_API_KEY`／`MINIMAX_BASE_URL`／`MINIMAX_MODEL` | Bridge | 修正腦；`MINIMAX_API_KEY` 只放環境變數，不入 config |
| `NEXT_PUBLIC_API_URL` | frontend | 後端 origin（不含 `/api/v1`）；全棧同源為空 |

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
GET  /autoclaude/runs/{run_id} → {"run_id","status","pid","started_at","completed_at","exit_code","current_step","completed_steps","total_steps","tokens_used","last_event_seq"}
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
GET  /sdd/fsm/{project} → FSM-STATE-{project}.yaml 內容（current_state、decision_trace 尾 5 筆）或 404
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
| 落地差異 | W1-B 交卷須列出與本節的差異；主控回寫本節與 RTM `BR-*`；回寫前以 Bridge 實作與其 `/openapi.json` 為準 |

## 11. 後端 API

### 11.1 端點與狀態碼語意

端點表以 **PRD §7.1.1～§7.1.8 為 SSOT**，本文不重抄。補充端點（PRD 缺口，ADR-001 G-16／G-17）：`POST /api/v1/auth/login`、`/api/v1/auth/refresh`、`GET /actuator/health`、`GET /actuator/prometheus`、`GET /api/v1/projects/{projectId}/executions`（列出專案執行批次，`API-EXE-14`）、`GET /api/v1/notifications/summary`（`API-NTF-01`，回 `NotificationSummaryResponse{pendingSignoffs, pendingReviews, unacknowledgedAlerts}`，供頂列通知鈴與 signoff 佇列徽章）；監控端點補充查詢參數 `runId`、`from`、`to`（對應設計稿「執行批次」「時間範圍」選單）。回應格式依 PRD §7.2。狀態碼語意：

| 碼 | 語意 |
|----|------|
| 400 | 驗證失敗；`approver` 缺漏或空白；halt ≤ compact；goal 依賴成環／自依賴／跨專案；黑名單字元命中 |
| 401／403 | 未認證／角色不足 |
| 404 | 資源不存在或已軟刪除 |
| 409 | 草案未 signoff 即執行／resume／restore；EXECUTING 專案受限操作；非法狀態轉移；並發互斥（Bridge 409）；import 未 signoff 即 confirm；Bridge 草案失效 |
| 422 | Bridge 有界閘或消毒拒絕（結構化原因逐字帶出） |
| 502／504 | Bridge 不可達／逾時（建立執行失敗已補償刪除 run 列） |

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
| `ParseResultResponse` | `importId, status, parsedResult, signedOff(=false), aiModel, tokenUsed, reasoning?, errors?[{gate,detail}]` |

**ExecutionRun**

| DTO | 欄位 |
|-----|------|
| `StartExecutionRequest` | `autonomyLevel`●*（1～10）、`tokenBudget`●（Long ≥1）、`scope`●*`{mode: ALL／SELECTED, goalIds[], taskIds[], limits{taskTokens?, goalTokens?}}` |
| `ExecutionRunResponse` | `id, projectId, runNumber, status(6 態), autonomyLevel, scope, totalTokensUsed, tokenBudget, startedAt, completedAt` |
| `ExecutionRunDetailResponse` | 上列＋`currentStep, completedSteps, totalSteps, lastEventSeq, pendingReviews[{id,kind,stepId,taskId,goalId,reason,requestedAt}], bridge{connected,instance}`（不含 pid、lock key） |
| `ExecutionStepResponse` | `id, runId, taskId, stepNumber, action, status, tokensUsed, errorMessage, output, timestamp` |
| `DagResponse` | `nodes[{id,kind(GOAL／TASK),label,status,goalId?}]`、`edges[{from,to}]` |
| `CheckpointResponse` | `id, runId, name, createdAt, isAutomatic, stepIdx?, stepId?`（不含 `stateSnapshot`） |
| `ReviewRequest` | `decision`●*（APPROVE／REJECT／RETRY／SKIP）、`comment`● |

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
```

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
| `agent.enableAutoMutation`／`enableSelfEvolution` | 可能對映 `playbook.max_evolutions`／演化相關開關 | 🟡 |
| `execution.globalTokenBudget` | 建立執行時 `token_budget` 的預設 | Console |
| `execution.tokenBudgetWarningThreshold`、`monitor.*`（除 Email） | 告警閾值與刷新間隔 | Console |
| `execution.dagSchedulerStrategy` | `DagService` 同層排序 | Console |
| `execution.enableRollback` | 無 | ⛔ |
| `execution.logRetentionDays` | Console／Bridge workspace 清理排程 | Console |
| `execution.compactThresholdPct`／`haltThresholdPct` | `token_guard.compact_threshold_pct`／`halt_threshold_pct` | ✅（SEC-05） |
| `autoclaude.engineUrl`／`healthCheckPath`、`sdd.engineUrl` | Bridge 位址與健康路徑（console 讀；預設 `http://engine-bridge:8081`） | Console |
| `autoclaude.eventBusType` | 無（僅 INTERNAL 存在） | ⛔ |
| `autoclaude.dalBackend` | `storage.mode`：FILE→`yaml_only`；POSTGRESQL→`both`；IN_MEMORY→`yaml_only`＋警告（D13） | ✅ |
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
| `model` | `enableKernelBrain` | `false` | `minimax.enable_kernel_brain` |
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
| L-9 | **argv 長度上限（平台相依）**：引擎把每步 prompt 以命令列參數傳給 claude——Linux 單一參數上限 128KiB（`MAX_ARG_STRLEN`），Windows 整條命令列 32,767 字元，macOS 無單參數上限；超過即 spawn 失敗、run 判 FAILED（agentconsole-ci run 38621708871 以 50,000 個中文字實證） | 後端 Phase 4 編 Playbook 時對每步 prompt 設上限（建議 ≤ 20,000 字元）並回 422；Bridge 測試已改用 12,000 字 |

### 12.2 待驗證項（誰在哪一波負責驗；結論須回寫本表）

| 編號 | 待驗項 | 驗證方式 | 負責 |
|------|--------|----------|------|
| V-1 | 步驟邊界的判定來源：W1-B 已對真引擎實證「引擎不寫步驟級 checkpoint，邊界由日誌的下一步驟啟動行推得，checkpoint 由 Bridge 於 pause 時寫入」（其 `runner.py`／`logparse.py` 檔頭自述）；待其 pytest「pause 在步驟邊界」全綠與交卷確認 | Bridge pytest | W1-B |
| V-2 | SIGTERM（Windows：`terminate()`）後引擎乾淨退出、checkpoint 完整可續跑 | Bridge pytest（pause→resume 接續）＋Windows 實跑 | W1-B、Windows 接續 |
| V-3 | 引擎 Token Guard halt 與 ESCALATION 的判定：W1-B 目前判為 FAILED 並發 `alert`；console 端的對映（任務→ESCALATED、審核項）與以 `restore` 續跑的路徑須驗證 | Bridge 測試＋後端對映測試 | W1-B／W3 後端 |
| V-4 | 審核閘提前 pause 的精度；ESCALATED 後 retry／skip 的可行路徑；Bridge 對 escalation 的狀態判定 | 後端 E2E（mock CLI，製造失敗步驟） | W3 後端、W4 QA |
| V-5 | `internal` 網路上的發布埠可達性（D14-10）；nginx→backend 連通（G-01） | `docker compose exec` 與 host 端連線測試 | W2-B |
| V-6 | Spring Boot 4 相容：springdoc、jjwt（Jackson 3）、Testcontainers、Flyway 對 PG18。**結論（W2-A，2026-10-14，已驗證）**：Spring Boot 4.1.1＋Hibernate 7.4.5＋Flyway 12.4.0 在 PG18.6 套用 V1～V4 並通過 `ddl-auto=validate`；springdoc 3.1.1 可用（真伺服器上 `/v3/api-docs`、Swagger UI 皆回 200）；jjwt 0.12.7 的 jackson-databind（Jackson 2，BOM 對齊 2.21.5）與 Spring 的 Jackson 3.1.5 並存、簽發與驗證實測正常；Testcontainers 以 `pgvector/pgvector:pg18` 可跑；注意 `@SpringBootTest` 預設關閉指標匯出，測 `/actuator/prometheus` 須設 `management.prometheus.metrics.export.enabled=true` | `./gradlew clean build` | W2-A |
| V-7 | Tremor Raw 於 Tailwind 4 的 build＋render | 圖表 spike（ADR-002） | W3 前端 |
| V-8 | `@uiw/react-md-editor` 與 React 19／Next 16 相容；`enableAutoMutation`／`enableSelfEvolution`、`sdd.*` 的引擎對映 | 前端 build＋行為測試；後端對映測試 | W3 |
| V-9 | Bridge 草案（`draft_id`）存放方式：W1-B 實作為 `<workspace>/_drafts/<draft_id>.json`（檔頭自述），重啟後仍可 approve | 待其測試與交卷確認 | W1-B |
| V-10 | `pgbackrest_*` 指標的產出方式（G-04） | Prometheus targets 與指標查詢 | W2-B |
