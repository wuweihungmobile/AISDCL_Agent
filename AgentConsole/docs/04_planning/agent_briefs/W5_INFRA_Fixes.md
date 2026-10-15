# 任務書 W5-INFRA：Engine Bridge 與 Docker 基礎設施修復棒

> 先讀 `W5_OVERVIEW.md`。持有面：`engine-bridge/**`、`docker/**`、`docker-compose.yml`、`docker-compose.dev.yml`、`.env.example`、`docs/06_quality/rtm_backfill_W5INFRA.md`。不改 backend／frontend／契約。契約 v1.2 §3（Bridge）的 `/health/deep` 與 `X-Trace-Id` 由 SA 定稿，照它做。

## 必讀

QA 報告 §7（全棧、§7.1 金鑰空值、§7.3 nginx、§7.5 還原演練）、§11 的 DEF-AC-003／006／008／010、觀察 O-06／O-08／O-09／O-11／O-16／O-19／O-20；`engine-bridge/README.md`、`engine-bridge/Dockerfile`、`engine-bridge/app/main.py`（`build_health`）、`docker/README.md` §4.3／§9／§10、`docker/nginx/nginx.conf`、`docker/nginx/conf.d/default.conf`、`docker/pgbackrest/scripts/restore.sh`；`AgentConsole/CLAUDE.md` 鐵律 5／6（`.sh` 只給容器、shellcheck；Python 跨平台規則）。

## 範圍（依優先序；每條做完立即跑對應閘門）

1. **C-2 DEF-AC-003（P1）**：Dockerfile 安裝 `git`＋`ca-certificates`（`--no-install-recommends`，清 apt lists）、`RUN git --version`；`app/main.py` 加 `GET /health/deep`（契約 v1.2 形狀；subprocess 逾時 5 秒、`creationflags` 走 `getattr`、Windows 可跑）；pytest 覆蓋 200 與 503（以 monkeypatch 讓 git 不存在／workspace 不可寫）；`docker-compose.yml` bridge healthcheck 改打 `/health/deep`。驗：`docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:w5 .`（context＝monorepo 根）rc=0；`docker run --rm aisdlc-engine-bridge:w5 git --version` 印版本；起容器 `GET /health/deep` 200 逐字。
2. **C-16 DEF-AC-006**：`CONSOLE_ENCRYPTION_KEY: ${CONSOLE_ENCRYPTION_KEY:?…}`；`.env.example` 註解說明產生方式；驗 `docker compose config`（四種 profile 組合）在未設時失敗訊息逐字、設了之後 rc=0。同檔：backend `LOG_DIR=/app/logs`、bridge `BRIDGE_LOG_DIR=/app/logs`、backend `CONSOLE_INTERNAL_PROXIES=<compose 子網>`（值由 `docker network inspect` 或 compose 固定子網決定，寫進 README）。
3. **C-12 Bridge 側**：中介層讀 `X-Trace-Id`（缺則 uuid4）、回應回帶、contextvar 注入日誌 record 的 `trace_id`（格式化字串每行都有）；`BRIDGE_LOG_DIR` 有值時加 RotatingFileHandler（`bridge.log`，每日或 10MB 切檔保留 7 份），沒設時行為不變；pytest 覆蓋（標頭回帶、日誌行含 trace_id）。
4. **C-15 DEF-AC-008／O-08／O-09**：`nginx.conf` `error_log … crit;`、檔頭註解改寫；`default.conf` 加 `location = /api/health`（在 `/api/` 之前，proxy 到 frontend）；靜態資源 `Cache-Control` 只留一份；驗 `docker run --rm -v <conf>:/etc/nginx/...:ro nginx:1.27-alpine nginx -t` rc=0 逐字。
5. **C-17 DEF-AC-010**：`restore.sh` Step 1 前 `mkdir -p "$PGDATA_DIR"`＋擁有者＋`chmod 0700`；`docker/README.md` §4.3 補「全新空卷」與「還原後核對資料列數」必做步驟；驗 shellcheck（`docker run --rm -v …:/mnt koalaman/shellcheck:stable /mnt/restore.sh`）與 `bash -n`（容器內）rc=0、CR=0。
6. **C-20、INF-VOL-07**：`docker/README.md` 寫明預設帳密必須更換（O-06）、`/actuator/prometheus` 免 token 只靠網路隔離（O-16）、`internalProxies`（O-20）；提供 `docker/nginx/conf.d/https.conf.example`（443、憑證取自 nginx_certs 卷、80→443 轉址）與 README 啟用步驟，預設不啟用。
7. **全棧冒煙**（鐵律：做完上述後至少跑一次）：`docker compose --profile db --profile app --profile full up -d --build`（`.env` 由 `.env.example` 複製、填隨機測試值，驗完刪除）→ 所有服務 healthy（bridge 以 `/health/deep`）→ 以 REST 建一個專案跑一個批次（契約 §5.0.3 夾具 A，Level 4）到 COMPLETED（這就是 DEF-AC-003 的證明；逐字貼 run 狀態）→ `GET /api/health` 經 nginx 回前端 200 → `down -v`。
8. **RTM 回填** `docs/06_quality/rtm_backfill_W5INFRA.md`：INF-SVC-04、INF-DKR-04、INF-SVC-03／INF-HLT-01（附註）、INF-NGX-04、INF-DR-16、NFR-9.3-03（附註）、NFR-9.4-04 Bridge 側、INF-VOL-06 Bridge 側、INF-VOL-07（example 與 README）、新列 `BR-26` 的四格內容。

## 閘門（全部貼 rc 與關鍵行）

- `Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\engine-bridge; ruff check . ; python -m pytest -q -n 4 *> <log>; Pop-Location`（讀 rc 前不接管線；Windows 平行跑偶發 `test_pid_alive_checks_identity_not_just_existence`，重跑單支確認即可）；根視角 `ruff check AgentConsole/engine-bridge`；根層 `Push-Location D:\CursorProject\AISDCL_Agent\tools\tests; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; Pop-Location`。
- 上述 docker build／compose config／nginx -t／shellcheck／全棧冒煙全部 rc=0；`docker rm -f` 會被守衛擋，用 `--rm`＋`docker stop`；5432 的 `autoclaude_pg` 不准動。
- 新 Python：`encoding="utf-8"`、時間戳帶 tz、平台 API 罩 `sys.platform`、`os.replace` 類包 `try/except OSError`。

## 交卷

依 `W5_OVERVIEW.md` §5；〈給 QA 的提醒〉列：p8 的 DEF-AC-008 `test.fail` 可移除、全棧啟動改動（healthcheck、必填金鑰、新 env）、Bridge 映像 tag 與 build 指令。
