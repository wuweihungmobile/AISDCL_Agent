# backend（console-api）

Spring Boot **4.1.1**／Java 21／Gradle 9.8.1（Kotlin DSL）／Clean Architecture。本目錄目前交付 PRD **Phase 1**（骨架、Flyway DB Schema、JWT 認證與 RBAC、統一回應封包）、**Phase 2**（專案／目標／任務 CRUD、reorder、目標依賴 Kahn 防環、retry、四條 signoff、NFR-SEC-03 輸入消毒、`draft` 旗標）、**Phase 3**（BRD/PRD 匯入：上傳／貼文字、三條解析路徑、有界閘、人工 signoff 硬閘、單一交易 confirm）、**Phase 6**（系統設定：50 個參數、敏感值 AES-256-GCM、Token Guard 成對校驗、測試連線、匯出入、歷史）與 PRD **§9.2 安全補完**（限流、審計落庫、SSRF allowlist、加密）。Phase 4～5（執行、監控、SSE）是下一波（W3-B2），同一棵樹續做。契約 SSOT：`docs/02_architecture/API_Contract_P3-6.md`＋`openapi-p3-6.yaml`。

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
**E2E／本機驗證用 profile**（`SPRING_PROFILES_ACTIVE=e2e`，契約 §5.0.1）：載入 `application-e2e.yml`——放行「列在 allowlist 內」的 loopback（假 chat-completions 伺服器綁 `127.0.0.1`）、`rebind.e2e.test` 解析到私網 `10.0.0.5`（驗 DNS rebinding）、限流開啟並信任 Tomcat 還原的客戶端位址。🔴 這幾個屬性（`allow-loopback`、`test-dns-overrides`）**只在 e2e／test profile 載入**：production 與 `docker` profile 不得出現，link-local／私網在任何設定下都拒絕。

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
| `CONSOLE_SECURITY_OUTBOUND_ALLOWLIST` | 否 | SEC-04 外呼 host 白名單（逗號分隔、精確比對），預設 `api.minimax.io,api.minimax.chat`（與 Bridge 對齊）；要用其他模型供應商須明確加入，且 Bridge 的 `BRIDGE_OUTBOUND_ALLOWLIST` 也要含該 host |
| `console.security.rate-limit.*`（`enabled`／`requests-per-minute`／`trust-forwarded-for`） | 否 | 限流：每個使用者（JWT subject；未認證才以客戶端位址）每 60 秒 100 次；測試 profile 預設關閉 |
| `console.import.max-prompt-chars`／`max-steps` | 否 | 匯入路徑 B 的 LLM 輸入字元上限（預設 120000）／每個目標任務數與目標數上限（預設 24；只准下調，硬上限 24） |
| `CONSOLE_ADMIN_PASSWORD_HASH`／`CONSOLE_OPERATOR_PASSWORD_HASH`／`CONSOLE_VIEWER_PASSWORD_HASH` | 正式環境必填 | 覆寫三個帳號的 BCrypt 雜湊（見下節）；不設則用開發預設 |
| `CONSOLE_CORS_ALLOWED_ORIGINS` | 否 | 逗號分隔，預設 `http://localhost:3000`（NFR-9.2-05） |
| `LOGGING_STRUCTURED_FORMAT_CONSOLE` | 否 | 設 `logstash` 即輸出結構化 JSON 日誌（每行含 `traceId`）；Docker 映像已預設開啟 |

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

## 端點（33 個路徑、42 個操作：Phase 1＋2 的 13 個路徑／22 個操作，加 W3-B1 的 20 個路徑／20 個操作；寫入＝OPERATOR／ADMIN，讀取＝任何已登入角色，系統設定的寫入與工具＝僅 ADMIN）

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v1/auth/login`、`/api/v1/auth/refresh` | 免認證；回 `{accessToken,refreshToken,expiresIn,role}`（access 30 分鐘、refresh 7 天） |
| POST／GET | `/api/v1/projects` | 建立（201）／列表（`page,size,q,status,sort`，預設 `0,10,updatedAt,desc`） |
| GET／PUT／DELETE | `/api/v1/projects/{id}` | 詳情（含目標摘要）／更新（EXECUTING 只准改 name、description）／軟刪除（EXECUTING→409，連帶軟刪目標與任務） |
| POST | `/api/v1/projects/{id}/signoff` | `{approver}` 必填非空，缺→400；已 signoff→409 |
| POST／GET | `/api/v1/projects/{projectId}/goals` | 建立（可帶 `dependsOn`）／列表（含任務數、完成比例） |
| GET／PUT／DELETE | `/api/v1/goals/{id}` | 詳情（含任務標題與 `dependsOn`）／更新／軟刪除（連帶任務；含 RUNNING 任務→409） |
| PUT | `/api/v1/goals/reorder` | `{projectId, orderedGoalIds[]}` 須恰好是專案下全部目標；回 204 |
| POST | `/api/v1/goals/{id}/signoff` | 同專案 signoff |
| POST／GET | `/api/v1/goals/{goalId}/tasks` | 建立／列表 |
| GET／PUT／DELETE | `/api/v1/tasks/{id}` | 詳情（含 `executionLog`、`executionHistory`）／更新／軟刪除（RUNNING→409） |
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
| GET | `/api/v1/notifications/summary` | `pendingSignoffs`（專案＋目標＋任務＋待簽匯入）、`pendingReviews`、`unacknowledgedAlerts`；`bridgeConnected`／`bridgeCheckedAt` 本波恆為 null |

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

**回應封包**（PRD §7.2）：成功 `{code,message:"success",data,timestamp,traceId}`；分頁資料在 `data` 內（`content,page,size,totalElements,totalPages`）；錯誤 `{code,message,errors[{field,message}],timestamp,traceId}`，另有選填的 `reason`（例：`依賴成環`）與 `details`（例：環路 id 清單、違規字元清單；**不輸出 null 值**，沒有值的鍵一律缺席）。`traceId` 每請求一個 UUID，同時在回應標頭 `X-Trace-Id` 與日誌 MDC。狀態碼：驗證 400、未認證 401、角色不足 403、找不到（含已軟刪除）404、狀態衝突 409、檔案過大 413、副檔名／內容型別不支援 415、有界閘／政策拒絕 422（有界閘的 `errors[]` 另帶 `gate`／`detail`／`location`）、限流 429（`Retry-After`、`X-RateLimit-Limit`／`-Remaining`）、Bridge 無法連線／錯誤 502、Bridge 逾時 504。`reason` 一律是契約附錄 B 的中文逐字常數（集中在 `domain.exception.ErrorReasons`，前端 `reasons.ts` 與此逐字相同）。

## 結構（PRD §4.1；規則由 `ArchitectureRulesTest` 以 ArchUnit 鎖住）

| 套件（`com.aisdlc.console.`） | 內容 |
|------|------|
| `domain.model.{project,goal,task,auth,imports,config}`、`domain.service`、`domain.exception` | 純 Java（不依賴 Spring／JPA）：聚合與不變式、`StateMachines`（附錄 B）、`DagService`（Kahn）、`PassCriteriaSanitizer`（NFR-SEC-03）；W3-B1 新增 `ImportRecord`（匯入狀態機）、`ParsedResult`（三層草案樹）、`ParsedResultValidator`（有界閘）、`OutboundUrlPolicy`（SEC-04 規則 1～6）、`ConfigCatalog`（50 鍵目錄）／`ConfigValueRules`、`ErrorReasons`（reason 常數） |
| `application.port.in／out`、`application.service` | 用例介面、出站埠、用例實作（`@Service`、交易邊界）。W3-B1 的出站埠：`AgentBridge`（`decompose`／`approveDraft`／`sddCompile`／`health`；W3-B2 在同一介面補 runs 系列）、`LlmClient`、`OutboundHttp`、`SecretCipher`、`DocumentTextExtractor`、`AuditTrail`、`SettingValues`；`ImportService`（parse／signoff 以 `TransactionTemplate` 切短交易，失敗先提交再丟例外）、`ImportParser`（三條路徑）、`SettingsService`、`SettingsReader`（給其他用例讀設定的入口，加密值回解密後明文）、`ImportStartupRecovery`（啟動時把殘留的 PARSING 退回 UPLOADED） |
| `adapter.in.web`（`dto`） | Controller、Request／Response record、`GlobalExceptionHandler`（全後端唯一產生錯誤封包處）、`ErrorResponseDocumentation`（把錯誤封包與各端點實際會回的狀態碼寫進 OpenAPI） |
| `adapter.out.{persistence,bridge,llm,http,document}` | `*RepositoryAdapter`（Entity↔Domain 轉換）、`BridgeHttpAdapter`（`RestClient`；4xx→`BridgeRejectedException`、5xx→502、連線失敗→502、讀取逾時→504）、`OpenAiCompatibleClient`、`PinnedOutboundHttp`（Apache HttpClient 5：自訂 `DnsResolver` 把連線釘死在已驗證 IP、Host／SNI 用原 host、不跟 redirect）、`DocumentTextExtractorAdapter`（PDFBox 3／POI） |
| `infrastructure.persistence.{entity,repository}` | 13 個 JPA 實體（對映 V1～V6 的 13 張表）與 Spring Data 儲存庫 |
| `infrastructure.security`、`infrastructure.config` | JWT、過濾器（traceId、限流、審計）、RBAC、CORS、OpenAPI、Bean 裝配；`AesGcmSecretCipher`（`v1:<iv>:<密文>`）、`RateLimiter`（Bucket4j，固定視窗）、`AuditLogWriter`（自己的新交易寫 `audit_log`，失敗只記 WARN） |

**Flyway**（`src/main/resources/db/migration/`）：`V1` 為 PRD §6.2 DDL 逐字（前置 `CREATE SCHEMA console`）；`V2` 六類系統參數種子（`autoclaude.dalBackend` 預設 `FILE`，ADR-001 D13）；`V3` review_requests；`V4` alerts；`V5` 九個引擎對映鍵（合計 50 鍵）＋全 50 鍵的 `validation_rule` 與 `impact_note`（US-S-08）＋`import_records.parse_path／last_parse_errors`＋預設值校正（`model.apiUrl`／`model.name`／`monitor.refreshIntervalMs`，**只在值仍等於舊預設時才改**，不覆蓋管理員改過的值，由 `V5UpgradeMigrationIT` 釘住）；`V6` `audit_log`（寫入端點審計，不記請求本文與 query string）。全部表在 `console` schema；`ddl-auto=validate`。`execution_runs` 的欄位所有權（Bridge 擁有 status 等欄位）由實體的 `insertable／updatable` 與 `ExecutionRunOwnershipIT` 保護。

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

## 測試（本棒新增的基礎設施）

- **`AbstractOutboundIT`**：需要外呼的整合測試共同基底——模擬 e2e profile 的外呼設定（`allow-loopback=true`、`rebind.e2e.test→10.0.0.5`、`console.bridge.url` 指向假 Bridge）；`OutboundFakes` 提供三台 JDK `HttpServer` 假伺服器（假 Bridge、假 OpenAI 相容端點、通用目標；記錄每個請求，所以能證明「SSRF 被拒時請求數是 0」「redirect 目標請求數是 0」）。Spring context 只有四種：預設、outbound、production 外呼政策（`allow-loopback=false`）、限流開啟。
- **`ApiClient`**：包 MockMvc（含 `multipart`）；`FakeHttpServer`／`ImportFixtures`／`DocumentFixtures`（測試期用 PDFBox／POI 現場產生 PDF／DOCX，不入庫二進位檔）。
- 整合測試共用單一 PostgreSQL 18 容器；`AbstractApiIT` 每個測試前清業務資料與審計表，前後都把 `system_configs` 還原為預設並清歷史。

## 與 PRD／任務書的差異（皆有實測理由）

| 項目 | 差異 | 理由 |
|------|------|------|
| `build.gradle.kts` | 關閉 `jar` 任務，只產生 boot jar | 否則 `build/libs` 同時有 `*-plain.jar`，PRD §11.4.2 的 `COPY build/libs/*.jar app.jar` 會因多來源檔而失敗 |
| `Dockerfile` | runner 階段加 `apk add curl`、加 `LOGGING_STRUCTURED_FORMAT_CONSOLE` | `eclipse-temurin:21-jre-alpine` 沒有 curl，PRD 的 HEALTHCHECK 會永遠 unhealthy；容器內需 JSON 日誌（PRD §9.4） |
| 資料表數 | V1 建 10 張（含 `goal_dependencies`），加 V3／V4 共 12 張 | 任務書寫「九張」，PRD §6.2 實為十張 |
| 版本 | Spring Boot 4.1.1、springdoc 3.1.1、jjwt 0.12.7、ArchUnit 1.5.1、Checkstyle 13.11.0、JaCoCo 0.8.15 | PRD §3 授權鎖定時取當時 stable；jjwt 經 Jackson 2 與 Spring Boot 的 Jackson 3 並存，實測無衝突 |

## Windows 接續：本塊尚未在 Windows 驗證的點

見交卷〈Windows 接續注意〉：`gradlew.bat clean build`、Testcontainers 連 Docker Desktop（WSL2）、`host.docker.internal`、PowerShell 版 BCrypt 產生指令。
