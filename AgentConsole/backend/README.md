# backend（console-api）

Spring Boot **4.1.1**／Java 21／Gradle 9.8.1（Kotlin DSL）／Clean Architecture。本目錄目前交付 PRD **Phase 1**（骨架、Flyway DB Schema、JWT 認證與 RBAC、統一回應封包）與 **Phase 2**（專案／目標／任務 CRUD、reorder、目標依賴 Kahn 防環、retry、四條 signoff、NFR-SEC-03 輸入消毒、`draft` 旗標）。Phase 3～6（匯入、執行、監控、設定）的端點是下一波；其資料表（V1～V4）已先建好、JPA 實體已通過 `validate`。

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

**本機啟動**（先起一個 PostgreSQL；下例用獨立容器，也可用 `AgentConsole/docker-compose.dev.yml`）
```bash
docker run -d --name console-pg -e POSTGRES_PASSWORD='<YOUR_POSTGRES_PASSWORD>' -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18
(cd AgentConsole/backend && JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' sh gradlew bootRun)
docker rm -f console-pg   # 驗完收掉
```
```powershell
docker run -d --name console-pg -e POSTGRES_PASSWORD='<YOUR_POSTGRES_PASSWORD>' -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18
Push-Location AgentConsole\backend; $env:JWT_SECRET="<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:SPRING_DATASOURCE_URL="jdbc:postgresql://localhost:5433/aisdlc"; $env:SPRING_DATASOURCE_USERNAME="aisdlc"; $env:SPRING_DATASOURCE_PASSWORD="<YOUR_POSTGRES_PASSWORD>"; .\gradlew.bat bootRun; Pop-Location
docker rm -f console-pg
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
docker run --rm -p 8080:8080 -e JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' -e SPRING_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:5433/aisdlc -e SPRING_DATASOURCE_USERNAME=aisdlc -e SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' aisdlc-backend:dev
```
```powershell
docker build -t aisdlc-backend:dev AgentConsole\backend
docker run --rm -p 8080:8080 -e JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' -e SPRING_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:5433/aisdlc -e SPRING_DATASOURCE_USERNAME=aisdlc -e SPRING_DATASOURCE_PASSWORD='<YOUR_POSTGRES_PASSWORD>' aisdlc-backend:dev
```

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `JWT_SECRET` | ✅ | HS256 密鑰，**≥ 32 字元**；缺或過短＝啟動失敗（錯誤訊息點名此變數） |
| `SPRING_DATASOURCE_URL`／`_USERNAME`／`_PASSWORD` | 密碼必填 | 預設 `jdbc:postgresql://localhost:5432/aisdlc`、使用者 `aisdlc`；密碼刻意無預設值 |
| `CONSOLE_ADMIN_PASSWORD_HASH`／`CONSOLE_OPERATOR_PASSWORD_HASH`／`CONSOLE_VIEWER_PASSWORD_HASH` | 正式環境必填 | 覆寫三個帳號的 BCrypt 雜湊（見下節）；不設則用開發預設 |
| `CONSOLE_CORS_ALLOWED_ORIGINS` | 否 | 逗號分隔，預設 `http://localhost:3000`（NFR-9.2-05） |
| `LOGGING_STRUCTURED_FORMAT_CONSOLE` | 否 | 設 `logstash` 即輸出結構化 JSON 日誌（每行含 `traceId`）；Docker 映像已預設開啟 |

## 開發預設帳號（⚠ 僅限本機開發；正式環境必須以環境變數覆寫雜湊）

| 帳號 | 密碼 | 角色 | 權限 |
|------|------|------|------|
| `admin` | `Admin#Dev2026` | ADMIN | 全部（設定寫入屬下一波） |
| `operator` | `Operator#Dev2026` | OPERATOR | 讀取、建立／編輯／刪除、signoff |
| `viewer` | `Viewer#Dev2026` | VIEWER | 只能 GET |

產生新密碼的 BCrypt 雜湊（用 Docker，不需另裝工具；Spring 接受 `$2a`／`$2b`／`$2y` 前綴，由 `BcryptPasswordVerifierTest` 釘住）：
```bash
docker run --rm httpd:2.4-alpine htpasswd -nbBC 10 x '<YOUR_NEW_PASSWORD>' | cut -d: -f2
```
```powershell
(docker run --rm httpd:2.4-alpine htpasswd -nbBC 10 x '<YOUR_NEW_PASSWORD>').Split(':', 2)[1]
```

## 端點（本波 13 個路徑、22 個操作；寫入＝OPERATOR／ADMIN，讀取＝任何已登入角色）

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

**回應封包**（PRD §7.2）：成功 `{code,message:"success",data,timestamp,traceId}`；分頁資料在 `data` 內（`content,page,size,totalElements,totalPages`）；錯誤 `{code,message,errors[{field,message}],timestamp,traceId}`，另有選填的 `reason`（例：`依賴成環`）與 `details`（例：環路 id 清單、違規字元清單）。`traceId` 每請求一個 UUID，同時在回應標頭 `X-Trace-Id` 與日誌 MDC。狀態碼：驗證 400、未認證 401、角色不足 403、找不到（含已軟刪除）404、狀態衝突 409。

## 結構（PRD §4.1；規則由 `ArchitectureRulesTest` 以 ArchUnit 鎖住）

| 套件（`com.aisdlc.console.`） | 內容 |
|------|------|
| `domain.model.{project,goal,task,auth}`、`domain.service`、`domain.exception` | 純 Java（不依賴 Spring／JPA）：聚合與不變式、`StateMachines`（附錄 B）、`DagService`（Kahn）、`PassCriteriaSanitizer`（NFR-SEC-03） |
| `application.port.in／out`、`application.service` | 用例介面、儲存與認證埠、用例實作（`@Service`、交易邊界） |
| `adapter.in.web`（`dto`） | Controller、Request／Response record、`GlobalExceptionHandler`（全後端唯一產生錯誤封包處） |
| `adapter.out.persistence` | `*RepositoryAdapter`（實作 `port.out`；Entity↔Domain 轉換） |
| `infrastructure.persistence.{entity,repository}` | 12 個 JPA 實體（對映 V1～V4 的 12 張表）與 Spring Data 儲存庫 |
| `infrastructure.security`、`infrastructure.config` | JWT、過濾器（traceId、審計）、RBAC、CORS、OpenAPI、Bean 裝配 |

**Flyway**（`src/main/resources/db/migration/`）：`V1` 為 PRD §6.2 DDL 逐字（前置 `CREATE SCHEMA console`）；`V2` 六類系統參數種子（`autoclaude.dalBackend` 預設 `FILE`，ADR-001 D13）；`V3` review_requests；`V4` alerts。全部表在 `console` schema；`ddl-auto=validate`。`execution_runs` 的欄位所有權（Bridge 擁有 status 等欄位）由實體的 `insertable／updatable` 與 `ExecutionRunOwnershipIT` 保護。

## 行為備忘（實作時的裁量，QA 與 W3 後端請知悉）

- **signoff**：手動建立的專案／目標／任務 `signedOff=true`（`signedOffBy/At` 為空）；`draft=true` 才是 `false`。已 signoff 再簽→**409**（保護稽核軌跡，不覆寫第一位簽核者）。`approver` 去頭尾空白後存入。
- **專案狀態**：`PUT` 可帶選填 `status`，**只開放 DRAFT／READY**（Phase 2 唯一的手動轉移入口）；EXECUTING／COMPLETED／FAILED／ARCHIVED 由執行引擎事件或刪除驅動，要求其他值→409。非法轉移（附錄 B.1）一律 409。
- **目標依賴**：以 `PUT /goals/{id}` 的 `dependsOn` 整組取代（`null` 不變、`[]` 清除）；成環→400（`reason:"依賴成環"`、`details.cycle` 為環路 id 清單）、自依賴→400（`reason:"自依賴"`）、跨專案或不存在→400；改動依賴前先鎖專案列（`SELECT … FOR UPDATE`）以序列化並發請求。被軟刪的目標不再計入依賴。
- **NFR-SEC-03**：`evaluatorCommand` 命中 `! \` > < ~ $ & ;`（SSOT：`AutoClaude/autoclaude/utils/shell_deny_chars.py` 的 `BASE_DENY_CHARS`）或含換行等控制字元→400 並列出違規字元；`expectedOutputRegex` 須可 `Pattern.compile`；`passCriteriaSpec` 內若帶有同名欄位同樣消毒。
- **審計**（NFR-9.2-07）：每次寫入請求輸出一行 JSON 到 logger `audit`（subject、method、path、targetId、status、traceId），含被 401／403 拒絕者；不記請求本文。
- 列表搜尋 `q` 把 `%`、`_` 當字面值；`sort` 欄位白名單（name／status／createdAt／updatedAt）。

## 與 PRD／任務書的差異（皆有實測理由）

| 項目 | 差異 | 理由 |
|------|------|------|
| `build.gradle.kts` | 關閉 `jar` 任務，只產生 boot jar | 否則 `build/libs` 同時有 `*-plain.jar`，PRD §11.4.2 的 `COPY build/libs/*.jar app.jar` 會因多來源檔而失敗 |
| `Dockerfile` | runner 階段加 `apk add curl`、加 `LOGGING_STRUCTURED_FORMAT_CONSOLE` | `eclipse-temurin:21-jre-alpine` 沒有 curl，PRD 的 HEALTHCHECK 會永遠 unhealthy；容器內需 JSON 日誌（PRD §9.4） |
| 資料表數 | V1 建 10 張（含 `goal_dependencies`），加 V3／V4 共 12 張 | 任務書寫「九張」，PRD §6.2 實為十張 |
| 版本 | Spring Boot 4.1.1、springdoc 3.1.1、jjwt 0.12.7、ArchUnit 1.5.1、Checkstyle 13.11.0、JaCoCo 0.8.15 | PRD §3 授權鎖定時取當時 stable；jjwt 經 Jackson 2 與 Spring Boot 的 Jackson 3 並存，實測無衝突 |

## Windows 接續：本塊尚未在 Windows 驗證的點

見交卷〈Windows 接續注意〉：`gradlew.bat clean build`、Testcontainers 連 Docker Desktop（WSL2）、`host.docker.internal`、PowerShell 版 BCrypt 產生指令。
