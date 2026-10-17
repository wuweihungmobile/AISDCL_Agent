# backend（console-api）

Spring Boot **4.1.1**／Java 21／Gradle 9.8.1（Kotlin DSL）／Clean Architecture。本目錄目前交付 PRD **Phase 1**（骨架、Flyway DB Schema、JWT 認證與 RBAC、統一回應封包）、**Phase 2**（專案／目標／任務 CRUD、reorder、目標依賴 Kahn 防環、retry、四條 signoff、NFR-SEC-03 輸入消毒、`draft` 旗標）、**Phase 3**（BRD/PRD 匯入：上傳／貼文字、三條解析路徑、有界閘、人工 signoff 硬閘、單一交易 confirm）、**Phase 6**（系統設定：50 個參數、敏感值 AES-256-GCM、Token Guard 成對校驗、測試連線、匯出入、歷史）與 PRD **§9.2 安全補完**（限流、審計落庫、SSRF allowlist、加密）；W3-B2 交付 PRD **Phase 4**（專案執行、自治等級審核閘、checkpoint 還原）、**Phase 5**（監控指標、告警六規則、結構化日誌、CSV 報表）與前端 **SSE** 兩條串流（Bridge 事件消費者把引擎事件投影成任務／目標／專案／批次的讀模型）；W5-BE（契約 v1.2）修復 QA 缺陷：軟刪除專案的復原與保留期、全域任務總計、PDF 報表、匯入記錄 `warnings`／`parseOptions`、`X-Trace-Id` 貫穿到 Bridge、檔案日誌與可信代理；W7-BE（契約 v1.3）：等級 6～10 傳遞引擎（`ConfigMaterializer.materialize(autonomyLevel)` 依決策表物化 `minimax.enable_kernel_brain`，批次回應與 `execution_runs.engine_capabilities` 帶 `engineCapabilities`）與引擎行程樹資源取樣 `bridge.resources` 的投影；W7-BE 第二批（契約 v1.4）：Bridge 探測改打深度探針 `/health/deep`（D-17）、`GET /engines/sdd`（AISDLC_SDD 的 FSM 狀態，只讀，D-16）、`GET /signoffs/pending`（待簽核草案清單，與通知摘要共用同一組述詞，D-18）、`POST /auth/logout` 與 refresh token 撤銷名單（Redis 優先、不在線降級為單實例記憶體，D-19）。契約 SSOT：`docs/02_architecture/API_Contract_P3-6.md`＋`openapi-p3-6.yaml`。

> 指令的工作目錄一律假設在 **monorepo 根**；每段 bash 區塊都有 PowerShell 對等區塊。`gradlew` 一律以 `sh gradlew`（Windows 用 `gradlew.bat`）呼叫，不依賴可執行位元。整合測試與 `docker build` 需要 Docker daemon 在線（`docker info` 回 rc=0）。

## 常用指令

**建置＋全部測試＋Checkstyle＋覆蓋率門檻（JaCoCo ≥ 80%，已接進 `check`）**
```bash
(cd AgentConsole/backend && sh gradlew clean build)
```
```powershell
Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
```

**只跑某一類測試**（整合測試會用 Testcontainers 起 `pgvector/pgvector:pg18`，首次需拉映像）
```bash
(cd AgentConsole/backend && sh gradlew test --tests 'com.aisdlc.console.domain.*')
(cd AgentConsole/backend && sh gradlew test --tests 'com.aisdlc.console.adapter.in.web.ProjectApiIT')
```
```powershell
Push-Location AgentConsole\backend; .\gradlew.bat test --tests 'com.aisdlc.console.domain.*'; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat test --tests 'com.aisdlc.console.adapter.in.web.ProjectApiIT'; Pop-Location
```

**覆蓋率報告**：`build/reports/jacoco/test/html/index.html`（`<tfoot>` 為總覆蓋率）。**Checkstyle 報告**：`build/reports/checkstyle/`。規則集在 `config/checkstyle/checkstyle.xml`（寬鬆版）。

**本機啟動**（先起一個 PostgreSQL；下例用獨立容器，也可用 `AgentConsole/docker-compose.dev.yml`）。🔴 `CONSOLE_ENCRYPTION_KEY` 必填（敏感參數的 AES-256-GCM 金鑰，base64 的 32 bytes；缺、非 base64 或長度不對＝啟動失敗，錯誤訊息點名此變數）：產生用 `openssl rand -base64 32`，沒有 openssl 時 PowerShell 用 `$b = New-Object byte[] 32; [System.Security.Cryptography.RandomNumberGenerator]::Fill($b); [Convert]::ToBase64String($b)`。本機 5433 若已被別的 PostgreSQL 佔用（先 `Get-NetTCPConnection -LocalPort 5433`），改映射到別的埠並同步 `SPRING_DATASOURCE_URL`。
```bash
docker run -d --name console-pg -e POSTGRES_PASSWORD='<YOUR_POSTGRES_PASSWORD>' -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' sh gradlew bootRun)
docker rm -f console-pg   # 驗完收掉
```
```powershell
docker run -d --name console-pg -e POSTGRES_PASSWORD='<YOUR_POSTGRES_PASSWORD>' -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:CONSOLE_ENCRYPTION_KEY="<YOUR_CONSOLE_ENCRYPTION_KEY>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5433/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; .\gradlew.bat bootRun; Pop-Location
docker rm -f console-pg
```
**E2E／本機驗證用 profile**（`SPRING_PROFILES_ACTIVE=e2e`，契約 §5.0.1）：載入 `application-e2e.yml`——放行「列在 allowlist 內」的 loopback（假 chat-completions 伺服器綁 `127.0.0.1`）、`rebind.e2e.test` 解析到私網 `10.0.0.5`（驗 DNS rebinding）、限流開啟並信任 Tomcat 還原的客戶端位址；W3-B2 另在此 profile 加 `console.execution.mock-env`（附到 Bridge 請求 `env` 的 `MOCK_CLAUDE_*`：每步延遲 0.6 秒、`[FAIL_ME]` 讓 mock claude 失敗）與 `console.sse.keep-alive-seconds=2`。🔴 這幾個屬性（`allow-loopback`、`test-dns-overrides`、`mock-env`）**只在 e2e／test profile 載入**：production 與 `docker` profile 不得出現，link-local／私網在任何設定下都拒絕。

**執行與監控的本機驗證（真 Engine Bridge＋映像內建的 mock claude）**——三個行程各開一個終端前景執行：PostgreSQL（上例）、backend（e2e profile）、Engine Bridge（DB 模式，連同一顆 PG；Bridge 啟動前須先有 backend 跑過 Flyway）。`<E2E_ROOT>` 是你自選的空目錄（放工作區與測試專案，不要放進 repo）；Bridge 的 `BRIDGE_ALLOWED_PATH_ROOTS` 必須含專案的 `executionPath`。起來之後以 admin 把系統參數 `autoclaude.claudeCommand` 設成 `aisdlc-mock-claude` 可執行檔的路徑、`execution.autoResume` 設 `false`，再走「建專案→execute→開 SSE」。
```bash
(cd AgentConsole/backend && SPRING_PROFILES_ACTIVE=e2e JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' ENGINE_BRIDGE_URL=http://127.0.0.1:8081 sh gradlew bootRun --args='--console.execution.mock-env[MOCK_CLAUDE_TRACE]=<E2E_ROOT>/mock-trace.jsonl')
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && ENGINE_WORKSPACE='<E2E_ROOT>/workspace' BRIDGE_ALLOWED_PATH_ROOTS='<E2E_ROOT>/projects:<E2E_ROOT>/workspace' BRIDGE_DB_DSN='postgresql://aisdlc:<YOUR_POSTGRES_PASSWORD>@localhost:5433/aisdlc' BRIDGE_DB_SCHEMA=console BRIDGE_OUTBOUND_ALLOWLIST=127.0.0.1,localhost BRIDGE_STOP_GRACE_SECONDS=5 BRIDGE_INSTANCE=e2e-bridge uvicorn app.main:app --host 127.0.0.1 --port 8081 --workers 1)
curl -N -s "http://localhost:8080/api/v1/stream/executions/<RUN_ID>/logs?access_token=<ACCESS_TOKEN>"   # 即時事件；前十行含 retry 與 step 事件
```
```powershell
Push-Location AgentConsole\backend; $env:SPRING_PROFILES_ACTIVE="e2e"; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:CONSOLE_ENCRYPTION_KEY="<YOUR_CONSOLE_ENCRYPTION_KEY>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5433/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; $env:ENGINE_BRIDGE_URL="http://127.0.0.1:8081"; .\gradlew.bat bootRun --args="--console.execution.mock-env[MOCK_CLAUDE_TRACE]=<E2E_ROOT>\mock-trace.jsonl"; Pop-Location
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; $env:ENGINE_WORKSPACE="<E2E_ROOT>\workspace"; $env:BRIDGE_ALLOWED_PATH_ROOTS="<E2E_ROOT>\projects;<E2E_ROOT>\workspace"; $env:BRIDGE_DB_DSN="postgresql://aisdlc:<YOUR_POSTGRES_PASSWORD>@localhost:5433/aisdlc"; $env:BRIDGE_DB_SCHEMA="console"; $env:BRIDGE_OUTBOUND_ALLOWLIST="127.0.0.1,localhost"; $env:BRIDGE_STOP_GRACE_SECONDS="5"; $env:BRIDGE_INSTANCE="e2e-bridge"; uvicorn app.main:app --host 127.0.0.1 --port 8081 --workers 1; Pop-Location
curl.exe -N -s "http://localhost:8080/api/v1/stream/executions/<RUN_ID>/logs?access_token=<ACCESS_TOKEN>"
```

啟動即由 Flyway 遷移（不需要手動 Flyway 指令）。另開終端驗證：

```bash
curl -s http://localhost:8080/actuator/health
curl -s -X POST http://localhost:8080/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"operator","password":"Operator#Dev2026"}'
```
```powershell
Invoke-RestMethod http://localhost:8080/actuator/health
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v1/auth/login -ContentType 'application/json' -Body '{"username":"operator","password":"Operator#Dev2026"}'
```
API 文件：`http://localhost:8080/swagger-ui.html`（OpenAPI JSON：`/v3/api-docs`）；Prometheus 指標：`/actuator/prometheus`（皆免認證；全棧時 nginx 對外擋 `/actuator/`）。

**Docker 映像**（build context＝本目錄）
```bash
docker build -t aisdlc-backend:dev AgentConsole/backend
docker run --rm -p 8080:8080 -e JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' -e CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' -e SPRING_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:5433/aisdlc -e SPRING_DATASOURCE_USERNAME=aisdlc -e SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' aisdlc-backend:dev
```
```powershell
docker build -t aisdlc-backend:dev AgentConsole\backend
docker run --rm -p 8080:8080 -e JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' -e CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' -e SPRING_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:5433/aisdlc -e SPRING_DATASOURCE_USERNAME=aisdlc -e SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' aisdlc-backend:dev
```

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `JWT_SECRET` | ✅ | HS256 密鑰，**≥ 32 字元**；缺或過短＝啟動失敗（錯誤訊息點名此變數） |
| `CONSOLE_ENCRYPTION_KEY` | ✅ | 敏感參數（`model.apiKey`、`autoclaude.dbDsn`）的 AES-256-GCM 金鑰：**base64 的 32 bytes**；缺、非 base64、長度不對＝啟動失敗（與 `JWT_SECRET` 同款 fail-fast，錯誤訊息點名此變數）。換金鑰＝既有密文無法解密，須重新輸入敏感參數 |
| `SPRING_DATASOURCE_URL`／`_USERNAME`／`_PASSWORD` | 密碼必填 | 預設 `jdbc:postgresql://localhost:5432/aisdlc`、使用者 `aisdlc`；密碼刻意無預設值 |
| `ENGINE_BRIDGE_URL` | 否 | Engine Bridge 位址，預設 `http://localhost:8081`。管理員在設定頁改過的 `autoclaude.engineUrl`／`sdd.engineUrl`（值≠預設）優先，下一個 Bridge 呼叫立即生效 |
| `BRIDGE_SDD_WRITE_TOKEN`（`console.bridge.sdd-write-token`） | 否 | SDD 寫入權杖（v1.5；ADR-XPLAT-016 §9），**與 Bridge 同名同值**，附在 `X-Bridge-Token` 標頭，只用於會觸發 FSM 寫入的四個呼叫（`POST /projects/{id}/sdd/freeze`、帶 `sdd` 區塊的 execute、SDD run 的 resume／restore）。**空＝SDD 寫入面停用**（預設，SDD 是選用引擎）：核准凍結回 503 `sdd_write_disabled`、execute 不送 `sdd` 區塊並以 `token_not_configured` 警告。有設但**短於 32 字元，或仍是 `<…>` 佔位＝啟動失敗**（fail-loud，不靜默退回停用；`openssl rand -hex 32` 產一個）。權杖值絕不進日誌、錯誤封包或 `details` |
| `CONSOLE_SECURITY_OUTBOUND_ALLOWLIST` | 否 | SEC-04 外呼 host 白名單（逗號分隔、精確比對），預設 `api.minimax.io,api.minimax.chat`（與 Bridge 對齊）；要用其他模型供應商須明確加入，且 Bridge 的 `BRIDGE_OUTBOUND_ALLOWLIST` 也要含該 host |
| `console.security.rate-limit.*`（`enabled`／`requests-per-minute`／`trust-forwarded-for`） | 否 | 限流：每個使用者（JWT subject；未認證才以客戶端位址）每 60 秒 100 次；測試 profile 預設關閉 |
| `console.execution.consumer.*`（`idle-timeout`／`backoff-initial`／`backoff-max`） | 否 | 事件消費者：Bridge 事件串流閒置逾 45 秒視為斷線，指數退避 1→30 秒重連（位移存 `execution_runs.console_last_seq`）。`console.execution.mock-env` 只在 e2e／test profile |
| `console.sse.*`（`keep-alive-seconds`／`queue-size`） | 否 | 前端 SSE：連續 15 秒沒有事件送一行 `keep-alive` 註解（e2e／test 為 2）；每個連線送出佇列 1,000 個框架，滿了由伺服器主動關閉（客戶端以 `Last-Event-ID` 重連即補齊） |
| `console.monitor.*`（`background-enabled`／`tick-interval`／`probe-capacity`） | 否 | 啟動後的 Bridge 探測、啟動對帳與每 30 秒一次的健康探測＋時間型告警；探測結果存記憶體環 2,880 筆（24 小時）。探測的路徑是系統參數 `autoclaude.healthCheckPath`，**預設 `/health/deep`**（D-17：Bridge 行程活著但 git／autoclaude／workspace／db 任一項不通會回 503，算**不可用**；200 回應裡 `checks.sdd.ok=false` 只是資訊、不影響判定），讀取逾時 8 秒（深度探針的 `git --version` 自己最多等 5 秒）；管理員可在設定頁改回 `/health`（只檢查行程是否存活）。整合測試預設關閉背景工作 |
| `console.import.max-prompt-chars`／`max-steps` | 否 | 匯入路徑 B 的 LLM 輸入字元上限（預設 120000）／每個目標任務數與目標數上限（預設 24；只准下調，硬上限 24） |
| `CONSOLE_ADMIN_PASSWORD_HASH`／`CONSOLE_OPERATOR_PASSWORD_HASH`／`CONSOLE_VIEWER_PASSWORD_HASH` | 正式環境必填 | 覆寫三個帳號的 BCrypt 雜湊（見下節）；不設則用開發預設 |
| `CONSOLE_CORS_ALLOWED_ORIGINS` | 否 | 逗號分隔，預設 `http://localhost:3000`（NFR-9.2-05） |
| `LOGGING_STRUCTURED_FORMAT_CONSOLE` | 否 | 設 `logstash` 即輸出結構化 JSON 日誌（每行含 `traceId`）；Docker 映像已預設開啟 |
| `LOG_DIR` | 否 | **檔案日誌**（C-16）：有值時，console 輸出照舊，另把日誌以 **JSON 行**（logstash 格式，MDC 的 `traceId` 成為欄位）寫到 `${LOG_DIR}/console.log`，**每日切檔、保留 7 天**（沒設或空白＝只輸出到 console，行為不變）。docker compose 設 `/app/logs`（與 Bridge 共用 `app_logs` 卷）。由 `FileLoggingEnvironmentPostProcessor` 在日誌系統初始化前補上 Boot 的 `logging.file.name`／`logging.structured.format.file`／`logging.logback.rollingpolicy.max-history`（放在最低優先序：部署者明確設的 `logging.*` 優先）；寫不進去只在日誌系統留錯誤狀態、不會讓服務起不來 |
| `CONSOLE_INTERNAL_PROXIES` | 否（docker profile） | **可信代理**（O-20；對應 `server.tomcat.remoteip.internal-proxies`，只在 `docker` profile 載入）：Java 正規表示式，對來源 IP 字串**整串比對**；Tomcat 的 `RemoteIpValve` 只信任符合者轉送的 `X-Forwarded-For`。**預設** `172\.31\.250\.(?:[2-9]\|[1-9]\d\|1\d\d\|2[0-4]\d\|25[0-4])`＝compose 固定子網 `172.31.250.0/24` 的 `.2`～`.254`（nginx 在其中；`.1` 是 Docker 閘道＝主機端進來的位址，刻意排除），與 `docker-compose.yml` 的預設相同。預設的 Tomcat 行為是信任所有私網位址與 loopback，內網客戶端可偽造 `X-Forwarded-For` 換掉未認證限流的桶。子網改了（`Pool overlaps`）要與 compose 的 `BACKEND_NET_SUBNET` 一起改；e2e／本機 profile 刻意不縮小（測試 client 在 loopback）。`RemoteIpNarrowedProxiesIT`／`RemoteIpDefaultProxiesIT` 以真 Tomcat 驗兩種行為 |
| `console.retention.soft-delete-days`（`CONSOLE_RETENTION_SOFT_DELETE_DAYS`） | 否 | 軟刪除專案可復原的天數，預設 **30**、≥ 1（NFR-9.3-04）；超過的專案 `POST /projects/{id}/restore` 回 409 `restore_window_expired`，與清除排程是否開啟無關 |
| `SPRING_DATA_REDIS_HOST`／`SPRING_DATA_REDIS_PORT` | 否 | **refresh token 撤銷名單**的 Redis（D-19；ADR-001 D16、D23，鍵 `console:revoked-refresh:<jti>`、TTL 到該 token 的 `exp`）。**沒設 host＝完全不嘗試連線**（本機開發與 e2e 不必起 Redis），撤銷名單只存這個行程的記憶體；設了＝Redis 優先，連不上（或中途掛掉）**降級為單實例記憶體**、只在狀態轉換記一次 WARN／恢復記一次 INFO，登入、換新、登出照常運作。其餘連線屬性（密碼、TLS、逾時）照 Spring Boot 慣例 `SPRING_DATA_REDIS_*`（連線與命令逾時預設 2 秒）。Redis 沒有健康指標（`management.health.redis.enabled=false`）：它一掛不會讓 `/actuator/health` 變 DOWN、容器不會因此 unhealthy |
| `console.security.refresh-revocation.store`（`CONSOLE_SECURITY_REFRESH_REVOCATION_STORE`） | 否 | 撤銷名單的選用：`auto`（預設；有 `spring.data.redis.host` 才用 Redis）｜`redis`（只用 Redis，降級照舊；沒設 host 時連 Spring Boot 的預設位址 `localhost:6379`）｜`memory`（強制純記憶體，即使設了 host）。多個 console-api 實例要共享撤銷結果必須用 Redis；記憶體版只在單一實例內有效，且隨行程重啟清空（重啟前已登出、尚未過期的 refresh token 會復活——契約 §1.9.2 已知限制） |
| `console.retention.purge-enabled`（`CONSOLE_RETENTION_PURGE_ENABLED`） | 否 | 是否註冊**每日清除排程**（實體刪除逾保留期的軟刪除專案及其整棵子資料，**不可逆**），預設 **`false`**——部署者必須明確開啟；關閉時軟刪除資料只會累積。每個專案一個交易、單一專案失敗只記 WARN；每清一個落一筆 `project.purge` 審計（主體 `system`） |

## 開發預設帳號（⚠ 僅限本機開發；正式環境必須以環境變數覆寫雜湊）

| 帳號 | 密碼 | 角色 | 權限 |
|------|------|------|------|
| `admin` | `Admin#Dev2026` | ADMIN | 全部：另含系統設定的寫入／重置／匯出入／測試連線與 `reveal=true` 揭露敏感值 |
| `operator` | `Operator#Dev2026` | OPERATOR | 讀取、建立／編輯／刪除、signoff、匯入（上傳／parse／編輯／signoff／confirm／reject） |
| `viewer` | `Viewer#Dev2026` | VIEWER | 只能 GET（含設定，加密值遮罩） |

產生新密碼的 BCrypt 雜湊（用 Docker，不需另裝工具；Spring 接受 `$2a`／`$2b`／`$2y` 前綴，由 `BcryptPasswordVerifierTest` 釘住）：
```bash
docker run --rm httpd:2.4-alpine htpasswd -nbBC 10 x '<YOUR_NEW_PASSWORD>' | cut -d: -f2
```
```powershell
(docker run --rm httpd:2.4-alpine htpasswd -nbBC 10 x '<YOUR_NEW_PASSWORD>').Split(':', 2)[1]
```

## 端點（58 個路徑、67 個操作：Phase 1＋2 的 13 個路徑／22 個操作，加 W3-B1 的 20 個路徑／20 個操作，加 W3-B2 的 20 個路徑／20 個操作，加 W5 的 2 個路徑／2 個操作，加 W7 的 3 個路徑／3 個操作；寫入＝OPERATOR／ADMIN，讀取＝任何已登入角色，系統設定的寫入與工具＝僅 ADMIN）

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/auth/login`、`/api/v1/auth/refresh` | 免認證；回 `{accessToken,refreshToken,expiresIn,role}`（access 30 分鐘、refresh 7 天）。refresh token 無效、過期、**已被撤銷**或是 access token → 401 `INVALID_REFRESH_TOKEN`；換新時**原子地撤銷舊的 refresh token**（同一個 token 的兩個併發換新只有一個成功，另一個 401） |
| POST | `/api/v1/auth/logout` | **登出並撤銷 refresh token**（W7，D-19）：免認證（登出時 access token 可能已過期）；`{refreshToken}` 缺或空白→400；**格式合法一律 204**——token 有效就撤銷其 `jti`，無效、過期、已被撤銷、或是 access token 同樣 204 而且不撤銷任何東西（不讓它變成探測 token 有效性的管道）。不撤銷 access token（無狀態，最長 30 分鐘後自然失效）。撤銷名單的儲存見〈環境變數〉的 Redis 兩列。審計 `auth.logout`（匿名請求，主體欄為 NULL，與其他免認證端點一致） |
| POST／GET | `/api/v1/projects` | 建立（201）／列表（`page,size,q,status,sort,deleted`，預設 `0,10,updatedAt,desc,false`）。`deleted=true`＝**只列軟刪除的專案**（OPERATOR 以上，VIEWER→403 `ACCESS_DENIED`；列表項帶 `deletedAt`；保留期已過的仍會列出，按復原才得到 409） |
| GET／PUT／DELETE | `/api/v1/projects/{id}` | 詳情（含目標摘要）／更新（EXECUTING 只准改 name、description）／軟刪除（EXECUTING→409，連帶軟刪目標與任務；專案與連帶軟刪的目標／任務寫**同一個** `deleted_at`，並記下刪除前的狀態 `status_before_delete`） |
| POST | `/api/v1/projects/{id}/restore` | **復原軟刪除的專案**（W5，C-3）：專案還原為刪除前的狀態（升級前就已軟刪者：未 signoff→DRAFT、已 signoff→READY），**同一次刪除連帶軟刪**的目標與任務一併回來（`deleted_at` 與專案的相同）、**單獨先刪除**的目標／任務不回來；單一交易、專案列先鎖（並發兩個 restore 只有一個成功）；找不到或已被清除→404 `專案不存在或已清除：<id>`；未被刪除→409 `project_not_deleted`；超過保留期→409 `restore_window_expired`（`details={projectId,deletedAt,retentionDays}`）；寫審計 `project.restore` |
| POST | `/api/v1/projects/{id}/signoff` | `{approver}` 必填非空，缺→400；已 signoff→409 |
| POST／GET | `/api/v1/projects/{projectId}/goals` | 建立（可帶 `dependsOn`）／列表（含任務數、完成比例） |
| GET／PUT／DELETE | `/api/v1/goals/{id}` | 詳情（含任務標題與 `dependsOn`）／更新／軟刪除（連帶任務；所屬專案有進行中批次→409 `project_executing`，`details={projectId,runId}`（W5，C-8）；其次含 RUNNING 任務→409） |
| PUT | `/api/v1/goals/reorder` | `{projectId, orderedGoalIds[]}` 須恰好是專案下全部目標；回 204 |
| POST | `/api/v1/goals/{id}/signoff` | 同專案 signoff |
| POST／GET | `/api/v1/goals/{goalId}/tasks` | 建立／列表 |
| GET／PUT／DELETE | `/api/v1/tasks/{id}` | 詳情（含 `executionLog`、`executionHistory`＝由 `execution_steps` 依任務衍生、跨批次依時間升冪、最多最近 200 筆，`tokensUsed` 只在 COMPLETED／FAILED 列）／更新／軟刪除（所屬專案有進行中批次→409 `project_executing`；RUNNING→409） |
| POST | `/api/v1/tasks/{id}/retry` | 只允許 FAILED／ESCALATED：`retryCount+1`、轉 QUEUED；其他→409 |
| POST | `/api/v1/tasks/{id}/signoff` | 同專案 signoff |

**BRD/PRD 匯入（Phase 3；契約 §1.1、§3.3）**——狀態機 `UPLOADED→PARSING→PARSED→REVIEWING→IMPORTED｜REJECTED`；寫入＝OPERATOR／ADMIN

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/import/upload` | multipart `file`（`.md`／`.pdf`／`.docx`、≤ 10MB）；擷取純文字存 `sourceContent`；413／415／422（內容與副檔名不符、非 UTF-8、PDF 加密、檔案損毀、無文字）各有固定 reason |
| POST | `/api/v1/import/text` | 貼上純文字（`PLAIN_TEXT` 預設／`MARKDOWN`，≤ 2,000,000 字元） |
| GET | `/api/v1/import`、`/api/v1/import/{id}` | 歷史列表（`page,size,status,q,sort`，不含原文與解析結果）／詳情（含 `sourceContent`、`parsedResult`、`lastParseErrors`） |
| POST | `/api/v1/import/{id}/parse` | 同步解析；路徑選擇：明示 `specDir` 或 `executionPath` 下的凍結 SDD 規格（路徑 A，每 24 個合約切一個目標）＞純文字且 < 2,000 字元無標題行（路徑 C，Bridge decompose）＞其餘（路徑 B，OpenAI 相容 chat completions）。三道有界閘（`max_steps`／`cycle`／`empty_prompt`）與 `prompt_too_long` 對每條路徑重現，違規 422 一次列出全部並退回 `UPLOADED`（不截斷不修剪）；規格存在卻被拒＝fail-closed 422，不退回 LLM |
| PUT | `/api/v1/import/{id}/result` | 整樹覆寫（陣列順序即排序）；重新過消毒（NFR-SEC-03）與有界閘；**撤銷既有 signoff** |
| POST | `/api/v1/import/{id}/signoff` | 🔴 人工 signoff 硬閘：`approver` 非空白；路徑 C 對每個草案呼叫 Bridge `:approve`（失敗不改任何狀態）；只批准、不落庫 |
| POST | `/api/v1/import/{id}/confirm` | 要求已 signoff；**單一交易**建立專案／目標／任務，全部 `signedOff=true`、`signedOffBy/At` 承襲匯入記錄；回 201 `ProjectResponse` |
| POST | `/api/v1/import/{id}/reject` | 放棄；IMPORTED／REJECTED／PARSING 回 409 |
| GET | `/api/v1/notifications/summary` | `pendingSignoffs`（專案＋目標＋任務＋待簽匯入）、`pendingReviews`（PENDING 的審核項）、`unacknowledgedAlerts`；`bridgeConnected`／`bridgeCheckedAt` 取自 Bridge 探測環的最新一筆（啟動後尚未探測過才是 null）。`pendingSignoffs` 與下一列的 `counts.total` 由**同一組述詞**產生（`PendingSignoffSql`） |
| GET | `/api/v1/signoffs/pending` | **待簽核的草案清單**（W7，D-18；API-SGN-05／US-E-07；VIEWER 以上）：`counts{projects,goals,tasks,imports,total}`＋`items[]{kind(PROJECT／GOAL／TASK／IMPORT),id,projectId,projectName,parentId,title,createdAt}`。判準：PROJECT＝`signed_off=false` 且未軟刪；GOAL／TASK＝另要求所屬專案（與目標）未軟刪——**已簽專案底下的草案照列**（判斷是逐列的）；IMPORT＝`PARSED`／`REVIEWING` 且未簽，`projectId`／`projectName`／`parentId` 為 null、`title` 是檔名（貼上文字為「貼上文字」）。排序 `createdAt` 升冪（NULL 最後）、同值 `id` 升冪；`limit`（預設 50、1～200，非整數或超出→400 `errors[0].field=limit`）只截斷 `items`，**不影響 `counts`**。不變量：`counts.total` 恆等於 `GET /notifications/summary` 的 `pendingSignoffs`（`SignoffsPendingApiIT` 釘住） |

**系統設定（Phase 6；契約 §1.5、附錄 C）**——50 個參數、六個分類（`model`／`agent`／`execution`／`monitor`／`autoclaude`／`sdd`）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/settings`、`/api/v1/settings/{category}` | 依分類分組；加密值一律 `••••••••`＋`hasValue`；`?reveal=true` 僅 ADMIN（其他角色 403），每次揭露寫審計（只記範圍與次數） |
| PUT | `/api/v1/settings/{category}/{key}` | `{value,confirm?}`；型別／`validationRule`／範圍／選項／`model.apiUrl` 的 SSRF allowlist 檢查；加密參數須 `confirm=true`（否則 409）；值未變不寫歷史 |
| PUT | `/api/v1/settings/execution/token-guard` | `{compactThresholdPct,haltThresholdPct}` 原子更新，跨鍵校驗 `halt > compact`（單鍵 PUT／重置／匯入同樣成對校驗），失敗不改任何一個鍵 |
| POST | `/api/v1/settings/{category}/{key}/reset`、`/api/v1/settings/{category}/reset` | 重置為預設值（加密鍵須 `confirm=true`；整個分類重置預設略過加密鍵） |
| POST | `/api/v1/settings/test-connection` | 對**完整端點 URL** 原樣 POST 一則 1-token ping：SEC-04 規則 1～6（格式／scheme／userinfo／IP 字面類別／allowlist／DNS rebinding）任一不過 422 且未發出連線；通過後連線釘死在已驗證 IP、不跟 redirect |
| GET | `/api/v1/settings/history` | 修改歷史（新到舊；加密參數的新舊值一律遮罩） |
| POST | `/api/v1/settings/export`、`/api/v1/settings/import` | 匯出 50 鍵（加密值為 `<encrypted>`）／匯入 JSON 檔（≤ 1MB、`version=1`；逐筆驗證，部分失敗仍 200 並逐筆列 `errors`） |

**專案執行（Phase 4；契約 §1.2、§3.4～§3.6）**——引擎是 Engine Bridge（`AgentBridge` 埠）；批次狀態六態（`INITIALIZING／RUNNING／PAUSED／COMPLETED／FAILED／CANCELLED`），Bridge 的 `PAUSING／CANCELLING` 只出現在 `bridgeStatus`

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/projects/{projectId}/execute` | 啟動（201）；body 全選填：`autonomyLevel`（1～10，預設取專案值；≥ 6 視為要求自動突變、≥ 7 視為要求自演化，物化成引擎設定並如實回報在回應的 `engineCapabilities`）、`tokenBudget`、`scope`（`ALL`／`SELECTED`＋`goalIds`／`taskIds`）、`limits`。驗證順序固定：404 專案→400 欄位→409 正在執行／狀態不允許／未經人工審批的草案→400 範圍 id→409 範圍／依賴成環→422 物化失敗→Bridge（409 鎖、422、502、504；Bridge 拒絕時補償刪除剛建的 run 列）。成功＝專案 `EXECUTING`、範圍內任務 `QUEUED`、啟動事件消費者 |
| GET | `/api/v1/projects/{projectId}/executions` | 批次列表（`page,size,status,sort=startedAt｜runNumber`；每列帶 Token／時間／成功率，終態批次也有） |
| GET | `/api/v1/executions/{runId}` | 批次詳情＝DB 列合併 Bridge 快照；Bridge 不可達仍 200、`bridge.connected=false`、進度退回 DB 衍生值；`pendingReviews` 只含 PENDING。v1.3：`engineCapabilities`（`{autoMutation, selfEvolution}`，值域 `ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`；讀自 DB、建立時凍結，V10 之前的批次缺席）與 `bridge.resources`（`{cpuPercent, memoryBytes, processCount, sampledAt}`，投影 Bridge `RunStateOut.resources`、值原樣帶出；Bridge 回 null、回應缺這個鍵、Bridge 不可達、`runKnown=false` 一律缺席；不含 pid） |
| POST | `/api/v1/executions/{runId}/pause`、`/resume`、`/cancel` | 暫停（下一個步驟邊界生效；回 `bridgeStatus=PAUSING`）／恢復（先重驗範圍內 signoff）／取消（回 `CANCELLING`，任務 `CANCELLED`、專案回 `READY`；終態由 SSE 通知）。控制端點（含 restore）的快照回應帶同一份凍結的 `engineCapabilities`，不帶 `bridge` 物件 |
| GET | `/api/v1/executions/{runId}/steps`、`/dag`、`/checkpoints` | 步驟分頁（`stepNumber`＝該 step 事件的 Bridge seq，`afterSeq` 嚴格大於，`size` ≤ 200）／批次建立時凍結的 DAG＋讀取當下的節點現況／歷史快照（舊→新，不含快照本體） |
| POST | `/api/v1/executions/{runId}/restore/{checkpointId}` | 從歷史 checkpoint 還原續跑（接受 PAUSED 與終態；只允許專案最新批次；重驗 signoff） |
| POST | `/api/v1/executions/{runId}/review/{stepId}` | 審核決定 `{decision,comment?}`，`{stepId}` 是 `review_requests.id`；決定須在該審核項的 `allowedDecisions` 內（否則 409）；`SKIP`／找不到還原點的 `RETRY` 另開後續批次，其 id 放回應標頭 `X-Follow-Up-Run-Id`（CORS 已 expose）；成功 204 |

**專案監控（Phase 5；契約 §1.3、§3.7）**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/monitor/projects/{projectId}/metrics`、`/token-trend`、`/task-trend` | 八項 KPI（含前一個等長視窗的 `previousValue`／`delta`）／Token 趨勢（含預算線）／任務趨勢；`runId`、`from`、`to`、`bucket` 選填（預設最近 24 小時；視窗 ≤ 48 小時用 `HOUR` 否則 `DAY`）；時間為 ISO-8601 帶 offset（未編碼的 `+` 被解成空白時會還原） |
| GET | `/api/v1/monitor/projects/{projectId}/alerts`、`/logs` | 告警（新到舊，`limit` ≤ 200）／結構化日誌（來源 RUN／STEP／ALERT／REVIEW，由 `execution_runs`、`execution_steps`、`alerts`、`review_requests` 衍生；`level,taskId,q,order,page,size`） |
| GET | `/api/v1/monitor/task-totals` | **全域任務總計**（W5，C-1）：`from` 必填、`to` 預設現在、視窗 ≤ 92 天（違反→400「時間範圍不合法」，欄位 `to`）；`started`／`completed`／`failed`／`retried`＝跨全部未封存且未軟刪除專案的 `execution_steps` 列數，與各專案 `task-trend` 逐欄加總相等（儀表板「本週完成」只打這一支，取代每個專案各打一次） |
| GET | `/api/v1/monitor/projects/{projectId}/report` | 報表下載，**`format=csv`（預設）或 `pdf`**（不分大小寫；後端以 `format` 為準，不因 `Accept` 不符回 406）。兩者同一組資料：四個區段 `summary`／`runs`／`tasks`／`alerts`（欄與序同源，`ReportCsv` 的欄名與指標清單是唯一定義）。CSV：UTF-8 BOM、CRLF、RFC 4180，`=`／`+`／`-`／`@` 開頭的文字欄位前補單引號防 CSV 注入。**PDF**（W5，C-4）：A4 橫向純文字表格（標題＝專案名稱＋「監控報表」、時間範圍、範圍、產生時間 UTC；null 顯示 `—`；不做 CSV 的引號）、長表格自動換頁並重複表頭；以 PDFBox 3 產生，內嵌 **Noto Sans TC Regular**（SIL OFL 1.1，`src/main/resources/fonts/`，子集嵌入所以檔案只有幾十 KB），字型沒有的字元（例如 emoji）與控制字元印成 `?`、不會讓整份報表失敗。檔名 `monitor-report-<專案 id 前 8 碼>-<yyyyMMdd-HHmm>.csv｜pdf`（UTC）；`Content-Disposition` 已 expose |
| POST | `/api/v1/monitor/alerts/{alertId}/acknowledge` | 確認告警（冪等，204）；確認後同一規則＋對象可再產生新告警 |
| GET | `/api/v1/engines/sdd` | **AISDLC_SDD 引擎狀態**（W7，D-16；API-ENG-01；VIEWER 以上；只讀，console-api 不寫 SDD 目錄與任何 FSM-STATE 檔，ADR-001 D22）：依序呼叫 Bridge 的 `GET /sdd/version`、`GET /sdd/fsm`，帶 `?project=` 時再呼叫 `GET /sdd/fsm/{project}`（連線逾時 2 秒、讀取逾時 3 秒、不重試、失敗即短路）。回 `{available, reason, version, projects[], fsm, checkedAt}`——**引擎不可用也回 200**：`available=false`＋`reason`（`bridge_unreachable`／`sdd_unavailable`〔Bridge 回 503 且自述 `sdd_unavailable`〕／`bridge_error`）；`available=true` 而 `fsm=null` 時 `reason` 為 `fsm_not_found`（Bridge 對該專案回 404）或 `fsm_state_unreadable`（422）；沒帶 `project`＝`fsm=null` 且不帶 `reason`。`project` 須符合 `^[A-Za-z0-9._-]{1,128}$`，不合→400 `errors[0].field=project`。Bridge 清單裡讀不動的檔名（`errors[]`）只記日誌（去控制字元）、**不轉發**；第三個呼叫失敗時保留前兩個呼叫已取得的 `version`／`projects`。`reason` 是**回應欄位**，不是 `ApiError.reason`。`fsm` 的最外層鍵轉 camelCase、巢狀內容（`decisionTrace[]`、`humanPending.items[]`、`retryHistory.last` 等）原樣保留 snake_case，`decisionTrace` 只留尾 5 筆。乾淨 clone 沒有 FSM 狀態檔（`build/reports/` 被 git 忽略）：`available=true`、`projects=[]` 是正常狀態 |

**前端 SSE（契約 §2）**

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/v1/stream/executions/{runId}/logs`、`/metrics` | `text/event-stream`。認證：`Authorization: Bearer` 或 `?access_token=`（EventSource 不能帶標頭；只收 access token、只在此路徑）。第一個框架是 `retry:3000`；事件的 `id:` 沿用 Bridge seq，後端自產的審核項／告警用 `<seq>.<n>`，嚴格遞增；`Last-Event-ID` 重播未送達事件；`/logs` 事件＝`log`／`status-change`／`review-request`／`alert`，`/metrics` 事件＝`progress-update`／`token-update`／`metric-update`（收斂快照 `<S>.1`～`<S>.3`）；PAUSED 不結束串流，終態後送完 `status-change` 與衍生事件才關閉；run 已終態且沒有可送的內容回 204 |

**回應封包**（PRD §7.2）：成功 `{code,message:"success",data,timestamp,traceId}`；分頁資料在 `data` 內（`content,page,size,totalElements,totalPages`）；錯誤 `{code,message,errors[{field,message}],timestamp,traceId}`，另有選填的 `reason`（例：`依賴成環`）與 `details`（例：環路 id 清單、違規字元清單；**不輸出 null 值**，沒有值的鍵一律缺席）。`traceId` 每請求一個 UUID，同時在回應標頭 `X-Trace-Id` 與日誌 MDC。狀態碼：驗證 400、未認證 401、角色不足 403、找不到（含已軟刪除）404、狀態衝突 409、檔案過大 413、副檔名／內容型別不支援 415、有界閘／政策拒絕 422（有界閘的 `errors[]` 另帶 `gate`／`detail`／`location`）、限流 429（`Retry-After`、`X-RateLimit-Limit`／`-Remaining`）、Bridge 無法連線／錯誤 502、Bridge 逾時 504。`reason` 一律是契約附錄 B 的中文逐字常數（集中在 `domain.exception.ErrorReasons`，前端 `reasons.ts` 與此逐字相同）。

## 結構（PRD §4.1；規則由 `ArchitectureRulesTest` 以 ArchUnit 鎖住）

| 套件（`com.aisdlc.console.`） | 內容 |
|------|------|
| `domain.model.{project,goal,task,auth,imports,config,execution,monitor,engine,signoff}`、`domain.service`、`domain.exception` | 純 Java（不依賴 Spring／JPA）：W7-BE 第二批新增 `engine.Sdd*`（`SddVersion`／`SddProjectEntry`／`SddFsmList`／`SddFsmState`／`SddEngineReason`／`SddEngineStatus`，AISDLC_SDD 引擎狀態的值物件）與 `signoff.PendingSignoff*`（待簽核草案的種類、計數與清單項）；聚合與不變式、`StateMachines`（附錄 B）、`DagService`（Kahn）、`PassCriteriaSanitizer`（NFR-SEC-03）；W3-B2 新增 `ExecutionRun`／`DagSnapshot`／`RunScope`／`BridgeStatus`（八態折六態）、`ReviewRequest`、`Alert`，與 `ExecutionPlanner`（範圍→展平 DAG）、`PlaybookBuilder`（任務→playbook、評估指令白名單）、`ReviewGatePolicy`（自治等級審核閘）、`GoalDerivation`（R-goal）、`AlertRules`（告警六規則）；W7-BE 新增 `EngineCapabilities`／`EngineCapabilityState`／`ResourceUsage`（批次的引擎能力狀態與資源取樣）與 `EngineCapabilityPolicy`（等級×旗標×金鑰→能力的決策表）；W3-B1 新增 `ImportRecord`（匯入狀態機）、`ParsedResult`（三層草案樹）、`ParsedResultValidator`（有界閘）、`OutboundUrlPolicy`（SEC-04 規則 1～6）、`ConfigCatalog`（50 鍵目錄）／`ConfigValueRules`、`ErrorReasons`（reason 常數） |
| `application.port.in／out`、`application.service` | 用例介面、出站埠、用例實作（`@Service`、交易邊界）。W3-B1 的出站埠：`AgentBridge`（`decompose`／`approveDraft`／`sddCompile`／`health`；W3-B2 在同一介面補 runs 系列；W7 補唯讀的 `sddVersion`／`sddFsmList`／`sddFsm`，並刪除 `src/main` 沒有呼叫者的 `listCheckpoints`〔完整性審查 I-07〕）、W7 新增 `RefreshTokenRevocations`（撤銷名單：`tryRevoke(jti, exp)` 原子地「沒撤銷過才撤銷」，回傳是否由這次呼叫撤銷）與 `SignoffQueue`（待簽核清單）、`LlmClient`、`OutboundHttp`、`SecretCipher`、`DocumentTextExtractor`、`AuditTrail`、`SettingValues`；`ImportService`（parse／signoff 以 `TransactionTemplate` 切短交易，失敗先提交再丟例外）、`ImportParser`（三條路徑）、`SettingsService`、`SettingsReader`（給其他用例讀設定的入口，加密值回解密後明文）、`ImportStartupRecovery`（啟動時把殘留的 PARSING 退回 UPLOADED）。W3-B2：`ExecuteProjectService`／`RunLauncher`（建 run 列→呼叫 Bridge→失敗補償刪除）、`ExecutionControlService`／`ReviewService`（暫停／恢復／取消／還原／審核）、`ExecutionQueryService`、`RunConsumers`（每個活躍 run 一條虛擬執行緒讀 Bridge 事件串流，位移存 DB，斷線指數退避重連）、`RunEventProcessor`（**每則事件一個交易**：投影任務／目標／專案狀態、審核項、告警與 `console_last_seq`，提交後才發 SSE 框架與執行 `:pause`）、`RunEventHub`／`StreamService`／`StreamConnection`（SSE 扇出、`Last-Event-ID` 重播、去重、有界送出佇列）、`MonitorService`／`TimeRuleEvaluator`／`MonitorTicker`／`BridgeHealthMonitor`、`ConfigMaterializer`（系統參數與自治等級→Bridge 的 `config_overrides` 與 `env`，並回傳該批次的 `engineCapabilities`；API Key 只進 `env`；`RunLauncher` 在交易 1 之前只呼叫一次，結果同時用於落庫與 Bridge 請求；決策表在 domain 的 `EngineCapabilityPolicy`）。W7 第二批：`SddEngineQueryService`（`GET /engines/sdd`：白名單驗證 `project`、三個 Bridge 呼叫依序失敗即短路、reason 映射）、`SignoffQueueService`（`GET /signoffs/pending`：`limit` 1～200 的驗證）、`AuthService` 加 `logout` 並在 `refresh` 對 `jti` 原子撤銷（`tryRevoke` 回 false→401 `INVALID_REFRESH_TOKEN`） |
| `adapter.in.web`（`dto`） | Controller、Request／Response record、`GlobalExceptionHandler`（全後端唯一產生錯誤封包處）、`ErrorResponseDocumentation`（把錯誤封包與各端點實際會回的狀態碼寫進 OpenAPI） |
| `adapter.out.{persistence,bridge,llm,http,document}` | `*RepositoryAdapter`（Entity↔Domain 轉換；W3-B2 的執行／步驟／checkpoint／Token 樣本／審核項／告警／監控聚合走 `JdbcTemplate`；W5 的 `ProjectPurgerAdapter` 依外鍵順序整棵清除）、`BridgeHttpAdapter`（`RestClient`；4xx→`BridgeRejectedException`、5xx→502、連線失敗→502、讀取逾時→504；事件串流用 JDK `HttpClient` 讀 SSE，不加依賴；每個請求帶 `X-Trace-Id`）、`OpenAiCompatibleClient`、`PinnedOutboundHttp`（Apache HttpClient 5：自訂 `DnsResolver` 把連線釘死在已驗證 IP、Host／SNI 用原 host、不跟 redirect）、`DocumentTextExtractorAdapter`（PDFBox 3／POI）、`PdfBoxReportRenderer`（W5：`ReportPdfRenderer` 埠的 PDFBox 實作，application 層只組「要印什麼」）；W7：`PendingSignoffSql`（**待簽核草案的唯一一組述詞**，通知摘要的 `pendingSignoffs`、清單的 `counts` 與 `items` 都由它的四段 `FROM … WHERE` 組出，不得在別處寫第二份）＋`SignoffQueueAdapter`，`BridgeHttpAdapter` 的 SDD 三呼叫（2xx 但本文形狀不是預期→`UpstreamException.Failure`，用例層映射成 `reason=bridge_error`；`decision_trace` 只留尾 5 筆） |
| `infrastructure.persistence.{entity,repository}` | 13 個 JPA 實體與 Spring Data 儲存庫（V1～V7 共 14 張表；`run_token_samples` 只走 JDBC） |
| `infrastructure.security`、`infrastructure.config` | JWT、過濾器（traceId、限流、審計）、RBAC、CORS、OpenAPI、Bean 裝配；`AesGcmSecretCipher`（`v1:<iv>:<密文>`）、`RateLimiter`（Bucket4j，固定視窗）、`AuditLogWriter`（自己的新交易寫 `audit_log`，失敗只記 WARN）；W7：`InMemoryRefreshTokenRevocations`（`jti`→到期時間，到期自動不計、每 10 分鐘順手清掃、原子 compute）／`RedisRefreshTokenRevocations`（`SET key 1 NX EX ttl`，TTL＝`max(exp − 現在, 1 秒)`）／`ResilientRefreshTokenRevocations`（先問記憶體、再問 Redis；Redis 任何執行期例外都降級、30 秒後再試；WARN／INFO 只在狀態轉換時記一次），`RefreshRevocationConfig` 依 `console.security.refresh-revocation.store` 與 `spring.data.redis.host` 選實作 |

**Flyway**（`src/main/resources/db/migration/`）：`V1` 為 PRD §6.2 DDL 逐字（前置 `CREATE SCHEMA console`）；`V2` 六類系統參數種子（`autoclaude.dalBackend` 預設 `FILE`，ADR-001 D13）；`V3` review_requests；`V4` alerts；`V5` 九個引擎對映鍵（合計 50 鍵）＋全 50 鍵的 `validation_rule` 與 `impact_note`（US-S-08）＋`import_records.parse_path／last_parse_errors`＋預設值校正（`model.apiUrl`／`model.name`／`monitor.refreshIntervalMs`，**只在值仍等於舊預設時才改**，不覆蓋管理員改過的值，由 `V5UpgradeMigrationIT` 釘住）；`V6` `audit_log`（寫入端點審計，不記請求本文與 query string）；`V7` 執行事件投影的基礎（W3-B2）：`review_requests`／`alerts` 加重播錨點 `event_seq`／`event_sub`、`execution_runs.console_last_seq`（console-api 已處理到的 Bridge 事件 seq）、`run_token_samples`（Token 趨勢與任務 Token 歸因的來源）、部分唯一索引 `uq_alerts_open_rule_subject`（同一規則＋對象在確認前不重複產生告警；升級行為由 `V5UpgradeMigrationIT` 釘住）；`V8`（W5-BE）`import_records.warnings`（JSONB、`NOT NULL DEFAULT '[]'`；最近一次成功的 parse／PUT result 的 `ParseWarning[]`）與 `parse_options`（JSONB，可為 NULL；最近一次 parse 請求的選項，進入 PARSING 時寫入），讓重開匯入記錄時還原黃色提示；`V9`（W5-BE）軟刪除時間：`projects`／`goals`／`tasks.deleted_at`（既有已軟刪的列以 `updated_at` 回填）、`projects.status_before_delete`（升級前軟刪者為 NULL）、partial index `idx_projects_deleted_at`；`V10`（W7-BE）`execution_runs.engine_capabilities`（JSONB，可為 NULL：該批次 spawn 時 Console 送進引擎的能力狀態 `{"autoMutation":…,"selfEvolution":…}`，建立批次時與批次列同一次 INSERT 寫入、之後不更新；NULL＝V10 之前的批次，不回填）並以 `(category, key)` 對位校正 `model.enableKernelBrain`、`agent.enableAutoMutation`、`agent.enableSelfEvolution` 三個鍵的 `impact_note`（文字逐字取自契約附錄 C，由 `SchemaMigrationIT` 與 `V5UpgradeMigrationIT` 比對）；`V11`（W7-BE，D-17）`autoclaude.healthCheckPath` 的預設改為 `/health/deep`（探測改打 Bridge 的深度探針）：**只改仍等於舊預設 `/health` 的欄位**——`value` 與 `default_value` 各自判斷（管理員設成別的值不被蓋掉；資料庫分不出「刻意設成 `/health`」與「沒動過」，這個取捨寫在 V11 檔頭），`impact_note` 一律換成契約附錄 C.5 的原文，其餘 49 個鍵一字不動（`SchemaMigrationIT`、`V5UpgradeMigrationIT` 以三種既有資料狀態驗證）——**升級到 V8～V11 對既有資料庫是自動的**（啟動時 Flyway 遷移，不需手動步驟，既有資料原樣保留）。全部表在 `console` schema；`ddl-auto=validate`。`execution_runs` 的欄位所有權（Bridge 擁有 status 等欄位）由實體的 `insertable／updatable` 與 `ExecutionRunOwnershipIT` 保護。

## 行為備忘（實作時的裁量，QA 與 W3 後端請知悉）

- **signoff**：手動建立的專案／目標／任務 `signedOff=true`（`signedOffBy/At` 為空）；`draft=true` 才是 `false`。已 signoff 再簽→**409**（保護稽核軌跡，不覆寫第一位簽核者）。`approver` 去頭尾空白後存入。
- **專案狀態**：`PUT` 可帶選填 `status`，**只開放 DRAFT／READY**（Phase 2 唯一的手動轉移入口）；EXECUTING／COMPLETED／FAILED／ARCHIVED 由執行引擎事件或刪除驅動，要求其他值→409。非法轉移（附錄 B.1）一律 409。
- **目標依賴**：以 `PUT /goals/{id}` 的 `dependsOn` 整組取代（`null` 不變、`[]` 清除）；成環→400（`reason:"依賴成環"`、`details.cycle` 為環路 id 清單）、自依賴→400（`reason:"自依賴"`）、跨專案或不存在→400；改動依賴前先鎖專案列（`SELECT … FOR UPDATE`）以序列化並發請求。被軟刪的目標不再計入依賴。
- **NFR-SEC-03**：`evaluatorCommand` 命中 `! \` > < ~ $ & ;`（SSOT：`AutoClaude/autoclaude/utils/shell_deny_chars.py` 的 `BASE_DENY_CHARS`）或含換行等控制字元→400 並列出違規字元；`expectedOutputRegex` 須可 `Pattern.compile`；`passCriteriaSpec` 內若帶有同名欄位同樣消毒。
- **審計**（NFR-9.2-07）：每次寫入請求輸出一行 JSON 到 logger `audit`（subject、method、path、targetId、status、traceId；用例標註的 `action`／`entity`，例：`import.signoff`、`settings.update`），含被 401／403 拒絕者，並落一列到 `console.audit_log`（失敗只記 WARN、不影響主請求）；不記請求本文與 query string。被限流的 429 不審計（沒有執行任何寫入，且逐筆落庫會讓限流變成寫入放大器）。`GET /settings?reveal=true` 是讀取但會寫一筆 `settings.reveal`（只記範圍與次數，不記值）。
- 列表搜尋 `q` 把 `%`、`_` 當字面值；`sort` 欄位白名單（name／status／createdAt／updatedAt；匯入歷史只有 createdAt／status）。
- **匯入**：失敗的 `parse` 一律退回 `UPLOADED`，只有「被有界閘拒絕」才寫 `lastParseErrors`，且**不寫** `parsedResult`／`parsePath`（先前成功的結果保留）；`GET /import/{id}` 的 `parsedResult` 在第一次成功解析前為 null。`model.apiUrl` 是**完整的 chat-completions 端點**，後端原樣 POST、不補任何路徑。外呼金鑰只經 `Authorization` 標頭送出，絕不進日誌、審計、錯誤訊息或給 Bridge 的請求本文。
- **限流**（NFR-9.2-06）：鍵＝JWT subject（未認證才用 `getRemoteAddr()`；過濾器**不**解析 `X-Forwarded-For`），固定 60 秒視窗 100 次，只套 `/api/**`；超限者先得 429 而不是 401／403。
- **actuator**：只暴露 `health`／`prometheus`（免認證）與 ADMIN 專用的 `info`，其餘端點（env／beans／heapdump／loggers…）不存在（`ActuatorIT` 釘住）。
- **執行的讀模型是「事件驅動」的**（W3-B2）：任務／目標／專案／批次的狀態不是 REST 呼叫當下改的，而是 `RunConsumers` 讀到 Bridge 事件後在 `RunEventProcessor` 的單一交易內投影——所以 `POST execute` 回 201 時專案已是 `EXECUTING`、任務 `QUEUED`，但 `RUNNING`／`COMPLETED` 要等事件；`pause` 回 `bridgeStatus=PAUSING`、`status` 仍是 `RUNNING`，直到 SSE 送出 `status-change`（`PAUSED`）；審核決定的後續（恢復或另開後續批次）同樣先回 204、狀態隨事件更新。讀模型只反映**專案最新的批次**：審核 `SKIP`／`RETRY` 另開後續批次後，舊批次遲到的終態事件不會把已交給新批次的任務重設回去。人工 `REJECT` 的目標一律 `FAILED`（人類的否決優先於機械推導，AR-11）。
- **自治等級審核閘**：「提前一步」——要在某一步之後停，必須在那一步 `STARTED` 時就呼叫 `:pause`（等它 `COMPLETED` 才呼叫就晚了一步）；暫停落在步驟邊界，審核項在 `PAUSED` 事件處理時建立（`<seq>.1`）。Level 1＝每個任務之間都停（`TASK_CONFIRM`，可 `APPROVE`／`REJECT`）、2＝每個目標之間停（`GOAL_CONFIRM`）、3＝每個目標完成後停（`GOAL_COMPLETED`，可 `APPROVE`／`REJECT`／`RETRY`）、4＝只有引擎升級（ESCALATION）時才介入、5～10 行為同 5（任何失敗都建審核項）；最後一步完成時 run 直接 `COMPLETED`，不暫停也不建審核項。**等級 6～10 的審核閘行為同 5，差異只在引擎能力旗標**（API-AUT-06，契約 §3.4.2、§3.6.1）：≥ 6 視為要求自動突變、≥ 7 視為要求自演化，物化成 `minimax.enable_kernel_brain`（**只在有 `model.apiKey` 時送**，並顯式送 `true`／`false`；沒有金鑰一律不送 `minimax.*`，因為真引擎對「`enable_kernel_brain=true` 但沒有金鑰」是啟動即失敗）。`engineCapabilities` 描述的是「實際送進引擎的」：`autoMutation`＝Brain 逐步校正（失敗步驟先由 Brain 改寫 prompt 再重試）、`selfEvolution`＝有金鑰就是 `ENABLED`（引擎沒有演化開關，只產生提案、不套用）；`playbook.max_evolutions`／`require_evolution_signoff` 等在引擎執行路徑上沒有讀者的鍵**永不送**（`ConfigMaterializerTest` 逐一否定斷言）。旗標設 `false` 關不掉等級的強制開啟（公式是 ∨）；要關 Brain 校正請降等級或清掉金鑰。`ESCALATED` 審核項可 `RETRY`（還原到失敗步驟之前的 checkpoint，沒有就另開後續批次）、`SKIP`（跳過失敗任務，另開後續批次）、`REJECT`。
- **SSE 的順序與重連**：終態時先送 `status-change`（id＝S），再送它衍生的事件（審核項、告警；id＝`S.n`，n ≥ 1），之後才關閉連線——id 必須嚴格遞增，客戶端依 id 去重，順序顛倒會丟事件。重連用 `Last-Event-ID`（`<seq>` 或 `<seq>.<n>`；格式不合視為沒帶）；`/metrics` 每次連線先送三則最新快照（`<S>.1`～`<S>.3`）。建議的前端做法：優先用 fetch 串流帶 `Authorization`，收到 `retry:3000` 後斷線 3 秒重連並帶最後收到的 id；收到 204 表示不必再重連。串流在連線建立時只算限流的一次請求（連線結束的 ASYNC dispatch 不重複計），被限流的使用者已開著的串流不受影響。**客戶端斷線不是錯誤**（DEF-AC-014）：伺服器下一次寫出（事件或 keep-alive）失敗時，Tomcat 通知、Spring 把原因 `IOException` 包成 `AsyncRequestNotUsableException`（原因訊息因平台而異：Linux 是 Broken pipe、Windows 是「連線已被您主機上的軟體中止」，所以只認型別、不比對字樣）並以非同步分派交給例外解析器——`GlobalExceptionHandler.handleClientGone` 專收它：不回本文（連線已死、回應也已是 `text/event-stream`，寫不出 `ApiError`）、只以**一行 DEBUG** 記 `run`、該請求自己的 `traceId`（取自回應標頭 `X-Trace-Id`，非同步分派的 MDC 是空的）與路徑（不含 query string）；`handleOther` 與其他例外的對映不變，真正未預期的例外照樣記 ERROR。要看那一行：`--logging.level.com.aisdlc.console.adapter.in.web.GlobalExceptionHandler=DEBUG`（命令列引數；環境變數形式的 `LOGGING_LEVEL_…_GLOBALEXCEPTIONHANDLER` 會被轉成小寫、對類別名不生效，實測 0 行）。`StreamDisconnectApiIT` 對真 HTTP 伺服器驗「讀到第一個框架後關連線 → 無 WARN／ERROR、訂閱釋放、DEBUG 行帶 run 與 traceId」。
- **告警**：六條規則（`TOKEN_BUDGET_WARNING`／`TOKEN_BUDGET_EXCEEDED`／`CONSECUTIVE_FAILURES`／`AGENT_UNRESPONSIVE`／`TASK_DURATION_EXCEEDED`／`HIGH_RETRY_RATE`）加引擎升級（`ENGINE_ESCALATION`）與 Token 暫停（`ENGINE_TOKEN_HALT`）的持久化鏡像；同一規則＋對象在被確認前不重複產生（資料庫部分唯一索引兜底）；預算超出與連續失敗會連帶呼叫 `:pause`。其餘 Bridge 的 `alert` 事件（例：`RESTORE`）只轉發給 SSE，不落庫。
- **啟動對帳**：console-api 啟動後對 `RUNNING`／`PAUSED` 的批次問 Bridge——404 只記 WARN、資料庫不動（狀態欄由 Bridge 擁有）；Bridge 不可達時仍啟動消費者（由連線層重試）。另補一條契約沒寫的：批次在資料庫已是終態、專案卻仍是 `EXECUTING`（停機期間 Bridge 把 run 跑完了），同樣依 `console_last_seq` 補處理。
- **traceId 貫穿到 Bridge**（W5，C-12；NFR-9.4-04）：`TraceIdFilter` 為每個使用者請求自產一個 UUID（不採信入站標頭），寫進 MDC、回應標頭 `X-Trace-Id` 與封包 `traceId`；對 **Bridge 的每一個請求**（`/autoclaude/*`、`/sdd/*`、健康探測、**SSE 事件串流**——它走的是另一個 HTTP 客戶端）都帶標頭 `X-Trace-Id`：使用者請求觸發的呼叫取當前請求的值；沒有請求上下文的背景工作用「該 run 的 traceId」＝啟動它的 execute（或審核後續）請求的值，只存記憶體（`RunRegistry.Runtime.traceId`、不入庫），事件消費者整條執行緒的 MDC 與日誌都以它為脈絡，啟動對帳的 `GET run` 與之後的消費者沿用同一個（console-api 重啟後記憶體裡沒有就新產一個並記住）；探測環沒有 run，每次探測新產一個 UUID；同一次 GET 呼叫的重試沿用同一個值。`MiniBridge` 記錄每個請求帶的值（`traced()`）並回帶標頭，`ExecutionLifecycleApiIT` 以「execute→消費者串流→pause」驗整條鏈。
- **不外露金鑰與 pid**（W7-BE；契約 §5.0.4 A5、§1.2.3、§3.1.2）：`model.apiKey` 解密後只進給 Bridge 的 `env`（`ConfigMaterializer`），回應、日誌（含 `com.aisdlc.console` 的 TRACE）都不出現——`ExecutionSecretLeakApiIT` 以「有金鑰的 level 7 批次」擷取日誌逐行比對。Bridge 自己的狀態文字會帶引擎行程編號（每個 run 一開始的 `引擎已啟動（pid=<編號>，第 n 次 spawn）`、強制終止告警的 `pid=[…]`），`BridgeHttpAdapter` 在出口（`BridgeText`）把狀態事件的 `reason`、告警事件的 `message` 與快照的 `reason` 裡的 pid 去掉，所以批次詳情的 `reason` 與 SSE 的 `status-change`／`alert` 都乾淨（引擎自己輸出的 `log` 行不動）。`bridge.resources` 本身不含 pid。
- **引擎能力在建立時凍結**（W7-BE；契約 §3.4.2 一致性規則）：`RunLauncher` 在交易 1 之前呼叫一次 `ConfigMaterializer.materialize(level)`，結果同時用於 `execution_runs.engine_capabilities` 的 INSERT 與 Bridge 請求（兩次分開讀設定，設定可能在中間被改，落庫的值就會與實際送出的不符）；`resume`／`restore`／審核 `APPROVE` 只取 `.env()`（依該批次的等級重新帶上，因為 Bridge 重啟後請求層 env 會遺失），不重算也不更新能力；審核 `SKIP`／`RETRY` 開的後續批次繼承原批次的等級、依當下的設定重新決定。讀回時缺鍵或值不認得一律當成「該鍵缺席」，不丟例外。
- **軟刪除、保留期與清除**（W5，C-3；契約 §1.6）：軟刪除專案時，專案與它當時仍未刪除的目標／任務在同一交易內寫**同一個** `deleted_at`——復原靠「目標／任務的 `deleted_at` 等於專案的」辨識同一次刪除連帶軟刪的列（單獨先刪除的不回來）。保留期 `console.retention.soft-delete-days`（預設 30）決定能不能復原（與清除排程無關）；清除排程（`SoftDeletePurge`，**預設關閉**）每日清 `deleted_at` 逾保留期的**專案**及其整棵子資料（依外鍵順序：審核項→告警→checkpoint→Token 樣本→步驟→批次→任務→目標→`import_records.project_id` 置 NULL→專案），範圍只有專案層級——存活專案內單獨軟刪的目標／任務不清。`GET /projects?deleted=true` 的 `goalsCount`／`tasksCount` 是 0（子資料在刪除時就都軟刪了，列表只算未刪的）。
- **檔案日誌**（W5，C-16）：見〈環境變數〉的 `LOG_DIR`。端到端驗證 `FileLoggingProcessTest` 在獨立 JVM 起真的 Spring Boot（日誌系統是整個 JVM 共用的，在測試 JVM 內重新初始化會污染其他測試）。
- **Bridge 探測只看狀態碼**（W7，D-17；契約 §3.1）：`BridgeHttpAdapter.health()` 不讀回應本文——2xx＝可用；深度探針的 503 `degraded`、其他非 2xx、連線失敗、逾時一律＝不可用（`BridgeHealthMonitorTest`、`BridgeHttpAdapterTest` 各釘住一段，`DeepProbeApiIT` 釘住整條鏈：迷你 Bridge 的 503→頂列連線燈熄滅、可用率下降）。200 回應裡 `checks.sdd.ok=false` 只是資訊（SDD 目錄問題不該拉低 Agent 可用率，主控裁決 Q4），要看 SDD 狀態走 `GET /engines/sdd`。探測路徑改回 `/health`（管理員在設定頁）時只檢查行程存活。
- **待簽核的述詞只有一份**（W7，D-18）：`PendingSignoffSql` 的四段 `FROM … WHERE` 同時組出通知摘要的 `pendingSignoffs`、`GET /signoffs/pending` 的 `counts` 與 `items`；判斷是**逐列**的（專案已簽，它底下仍是草案的目標／任務照列——儀表板舊的前端近似清單漏列這種，造成「徽章數字大於點得到的項目」）。`ImportService.signoff` 對路徑 C 會呼叫 Bridge `:approve`，所以匯入項要經 API 簽核才會從清單消失。
- **refresh token 撤銷**（W7，D-19）：`refresh` 的順序是「驗證 token（要有 `jti` 與 `exp`）→ `tryRevoke(jti, exp)`（false→401 `INVALID_REFRESH_TOKEN`）→ 查帳號 → 簽發」，撤銷在簽發之前、且是原子的，所以併發換新同一個 token 恰好一個成功；撤銷只作用在 refresh token，已簽發的 access token 不撤銷（無狀態，最長 30 分鐘後自然失效）。`logout` 對格式合法的請求一律 204 且**先寫審計**（`auth.logout`）再嘗試撤銷。Redis 掛掉時登入／換新／登出照常（改記在單實例記憶體）；**降級期間撤銷的項目 Redis 恢復後不回補**（每次先查記憶體名單），重啟會清空記憶體名單——契約 §1.9.2 已知限制，目前單實例部署可接受。
- **引擎狀態只讀、不外洩**（W7，D-16）：`GET /engines/sdd` 只呼叫 Bridge 的三個 GET，不快取（前端 30 秒輪詢）；Bridge 清單的 `errors[]`（讀不動的檔名）只進日誌、不轉發，且先去控制字元防日誌注入；`version.root` 是 Bridge 看到的目錄路徑，僅供顯示。

## 測試（本棒新增的基礎設施）

- **`AbstractOutboundIT`**：需要外呼的整合測試共同基底——模擬 e2e profile 的外呼設定（`allow-loopback=true`、`rebind.e2e.test→10.0.0.5`、`console.bridge.url` 指向假 Bridge）；`OutboundFakes` 提供三台 JDK `HttpServer` 假伺服器（假 Bridge、假 OpenAI 相容端點、通用目標；記錄每個請求，所以能證明「SSRF 被拒時請求數是 0」「redirect 目標請求數是 0」）。Spring context 只有四種：預設、outbound、production 外呼政策（`allow-loopback=false`）、限流開啟。
- **`AbstractExecutionIT`＋`MiniBridge`**（W3-B2）：執行與監控的整合測試共同基底——完整 Spring context（`RANDOM_PORT`，真 HTTP）＋迷你 Bridge（`com.aisdlc.minibridge`，JVM 內第二個 Spring 應用，真 HTTP／SSE；事件序列由旋鈕決定：`manualSteps`＋`release(n)` 決定性地控制步驟時序、`failStepIds` 讓步驟重試後失敗、`failNext(route,…)` 注入錯誤回應、`dropStreams()` 模擬斷線、`resourcesMode`＝快照的 `resources` 怎麼回〔預設 `SAMPLE`：引擎行程樹存活時回一筆樣本、暫停與終態回 null，對照真 Bridge；`NULL`：恆回 null；`OMIT`：不帶這個鍵，模擬舊版 Bridge〕）。迷你 Bridge 與真 Bridge 一樣「事件先、欄位後」並把狀態／Token／步驟列／checkpoint 鏡射進同一顆 PG。**`SseProbe`** 是對真伺服器讀 SSE 的測試客戶端（逐行解析 `id／event／data／retry` 與註解）。測試分 2 個 JVM fork 平行（`maxParallelForks=2`），所以迷你 Bridge 一律以命令列引數 `--server.port=0` 起在隨機埠（`application.yml` 的 `server.port: 8080` 會蓋掉 default properties，兩個 fork 會搶同一個埠）。
- **`ApiClient`**：包 MockMvc（含 `multipart`）；`FakeHttpServer`／`ImportFixtures`／`DocumentFixtures`（測試期用 PDFBox／POI 現場產生 PDF／DOCX，不入庫二進位檔）。
- 整合測試共用單一 PostgreSQL 18 容器；`AbstractApiIT` 每個測試前清業務資料與審計表，前後都把 `system_configs` 還原為預設並清歷史。
- **真 Redis 與降級**（W7，D-19）：`SharedRedis`（`redis:7-alpine`，JVM 級單例的 Testcontainers）只給 `RefreshRevocationRedisIT` 用——對真 Redis 驗鍵 `console:revoked-refresh:<jti>`、TTL（到 `exp`，快過期者至少 1 秒）、`SET NX` 的原子性（6 個併發換新同一個 token 恰好一個 200）；`RefreshRevocationRedisDownIT`（`host=127.0.0.1`、`port=1`、`store=redis`）驗「Redis 不在線仍可登出與換新」、`/actuator/health` 仍 UP 且沒有 Redis 指標、日誌不逐請求記；`ResilientRevocationsTest` 以可控制的替身與時鐘驗「進入降級恰好一次 WARN、恢復恰好一次 INFO、降級期間每 30 秒才再試 Redis」；`RefreshRevocationConfigTest` 驗選用邏輯（沒設 host 時連 `opsForValue()` 都不碰）。其他整合測試完全不碰 Redis。
- **`MiniBridge` 的 v1.4 夾具**：`GET /health/deep`（`deepHealthMode`：`HEALTHY`／`DEGRADED`〔前四項失敗＝503〕／`SDD_NOT_OK`〔200，`checks.sdd.ok=false`〕）與 `GET /sdd/version`、`/sdd/fsm`、`/sdd/fsm/{project}`（`MiniBridge.Sdd`：`unavailable`／`delayMillis`／`latest`／`root`／`projects`／`errors`／`states`／`unreadable`，預設有 `e2e-alpha`〔`IMPLEMENTATION`、重試 3 次、5 筆決策〕與 `e2e-bravo`〔`HUMAN_PENDING`〕兩個專案；形狀對照 Bridge 的 `app/routers/sdd.py`、`app/health.py`）。
- **HTML 測試報告放 `build/rt`，測試方法名要短**（W7，路徑長度）：Gradle 9.8 的新版 HTML 報告為每個測試類別／方法各產生一個 `<類別全名>/<方法簽章>` 的檔案或目錄，路徑一旦超過 Windows 的 260 字元，根層 `tools/tests` 的檔案樹掃描會整批 `FileNotFoundError`；所以報告改輸出到 `build/rt/`（比預設 `build/reports/tests/test/` 短 17 字元），並要求新增的測試方法名 ≤ 70 字元、`@ParameterizedTest(name = …)` 取短（參數化的方法簽章會被展開成檔名）。驗收：`Get-ChildItem -LiteralPath '<repo>\AgentConsole\backend\build' -Recurse -Force | ForEach-Object { $_.FullName.Length } | Sort-Object -Descending | Select-Object -First 1` 必須 < 240（Windows 路徑上限 260 留餘裕）。

## 與 PRD／任務書的差異（皆有實測理由）

| 項目 | 差異 | 理由 |
|------|------|------|
| `build.gradle.kts` | 關閉 `jar` 任務，只產生 boot jar | 否則 `build/libs` 同時有 `*-plain.jar`，PRD §11.4.2 的 `COPY build/libs/*.jar app.jar` 會因多來源檔而失敗 |
| `Dockerfile` | runner 階段加 `apk add curl`、加 `LOGGING_STRUCTURED_FORMAT_CONSOLE` | `eclipse-temurin:21-jre-alpine` 沒有 curl，PRD 的 HEALTHCHECK 會永遠 unhealthy；容器內需 JSON 日誌（PRD §9.4） |
| 資料表數 | V1 建 10 張（含 `goal_dependencies`），加 V3／V4 共 12 張 | 任務書寫「九張」，PRD §6.2 實為十張 |
| 版本 | Spring Boot 4.1.1、springdoc 3.1.1、jjwt 0.12.7、ArchUnit 1.5.1、Checkstyle 13.11.0、JaCoCo 0.8.15 | PRD §3 授權鎖定時取當時 stable；jjwt 經 Jackson 2 與 Spring Boot 的 Jackson 3 並存，實測無衝突 |
| 檔案日誌（W5，C-16） | 以 `FileLoggingEnvironmentPostProcessor`（`META-INF/spring.factories`）補 Boot 的檔案日誌屬性，**沒有** `logback-spring.xml` | 「`LOG_DIR` 有值才加 appender」在 Logback 1.5 只能用 `<if>`，那需要 Janino（不新增相依）；`application.yml` 又算不出「有值才加 `/console.log`」。行為與任務書相同（JSON 行、`${LOG_DIR}/console.log`、每日切檔保留 7 天、沒設＝不變），`FileLoggingProcessTest` 在獨立 JVM 端到端驗證 |
| 測試報告位置（W7-BE） | HTML 測試報告輸出到 `build/rt/`，不是預設的 `build/reports/tests/test/` | 見〈測試〉：Gradle 9.8 新版報告的逐方法檔案讓最長路徑逼近 Windows 的 260 字元上限；全 repo 沒有任何文件或 CI 引用舊路徑（已搜尋確認）。非本棒寫的長名測試因 RTM 以方法名引用而不改名 |
| 登出審計的匿名主體（W7-BE） | 契約 §1.9.1 寫「匿名請求的 `subject` 為 `-`」，實作維持 `NULL` | 與既有慣例一致：V6 的欄位註解、`AuditLogIT`／`AuditPersistenceApiIT` 對 login 等免認證請求都斷言 `NULL`；只讓 logout 寫 `-` 會讓兩種匿名列用不同寫法。待 SA 訂正契約，或另案統一改寫法 |
| 可信代理（W5，C-16） | `server.tomcat.remoteip.internal-proxies` 只在 `application-docker.yml` 對應 `CONSOLE_INTERNAL_PROXIES`，base／e2e 不設 | e2e 的測試 client 在 loopback，縮小後 `X-Forwarded-For` 不被信任會讓 e2e 的限流情境失效；production 直連沒有 `RemoteIpValve`，這個值用不到 |

## Windows 接續：本塊尚未在 Windows 驗證的點

見交卷〈Windows 接續注意〉：`gradlew.bat clean build`、Testcontainers 連 Docker Desktop（WSL2）、`host.docker.internal`、PowerShell 版 BCrypt 產生指令。
