# 任務書 W2-A：後端開發者（Spring Boot 4.1 / Java 21，PRD Phase 1 + Phase 2）

> 先讀 `COMMON_CONTEXT.md`，再讀 `AgentConsole/docs/02_architecture/Architecture.md` 與 `ADR-001-TechStack-Lock.md`（Architect 已完成），再讀本檔。

## 你的角色
你是 console-api（後端）的唯一開發者。本波只做 PRD **Phase 1（骨架／DB Schema／認證）＋ Phase 2（專案／目標／任務 CRUD ＋ signoff）**。Phase 3～6（匯入／執行／監控／設定）是下一波，**不要做**，但 DDL 一次到位（九張表全建）。

## 必讀（PRD 行號）
- §0（40～125）、§4.1 套件樹（261～313）、§5.1 全部（353～646）、§6（1342～1689，DDL 逐字）、§7.1.1～7.1.3（1694～1725）、§7.1.4.1 signoff（1736～1746）、§7.2 回應格式（1809～1855）、§9.2 安全（1955～1966）、附錄 B 狀態機（2068～2107）、§11.4.2 Dockerfile（2600～2640）。
- `AgentConsole/docs/02_architecture/Architecture.md` §4／§7／§8／§11（DTO 欄位表）。

## 技術鎖定（不討論）
- 用 start.spring.io 產骨架（避免猜 Spring Boot 4 的 starter 名）：
  ```
  cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole && curl -fsSL https://start.spring.io/starter.zip \
    -d type=gradle-project-kotlin -d language=java -d javaVersion=21 -d packaging=jar \
    -d groupId=com.aisdlc -d artifactId=console -d name=console -d packageName=com.aisdlc.console \
    -d dependencies=web,data-jpa,validation,security,flyway,postgresql,actuator,testcontainers -o backend.zip \
    && mkdir -p backend && unzip -q -o backend.zip -d backend && rm backend.zip
  ```
  （bootVersion 不指定＝取 Initializr 預設 4.1.x；交卷貼 `build.gradle.kts` 的 plugin 版本行。）
- 另加：`org.springdoc:springdoc-openapi-starter-webmvc-ui`（選與 Spring Boot 4 相容的版本，compile 不過就換版本，把最後可用版本寫進交卷）、`io.jsonwebtoken:jjwt-api/impl/jackson 0.12.x`、`org.testcontainers:postgresql`、`spring-boot-testcontainers`。
- Spring Boot 4 已知差異（寫錯就編不過，請以編譯為準）：Jackson 3（套件 `tools.jackson.*`，`ObjectMapper` 來自 `tools.jackson.databind`）、`@MockBean`→`@MockitoBean`、Spring Framework 7、Spring Security 7。**每加一個模組就 `./gradlew compileJava compileTestJava` 一次**。
- Clean Architecture 套件樹照 PRD §4.1：`adapter.in.web`（Controller）／`adapter.out.persistence`（JPA）／`application.port.in`（UseCase 介面）／`application.port.out`（Repository 介面）／`application.service`（UseCase 實作）／`domain.model.{project,goal,task,execution,config}`／`domain.event`／`infrastructure.{config,security,persistence}`。domain 不得 import Spring／JPA（純 Java）；用 ArchUnit 寫一支測試鎖住這條規則。
- DB：Flyway 擁有 DDL。`src/main/resources/db/migration/V1__init.sql`＝PRD §6.2 DDL **逐字**（加 `CREATE SCHEMA IF NOT EXISTS console;` 開頭；所有表在 `console` schema），`V2__seed_system_configs.sql`＝PRD §5.5.1.1～5.5.1.6 六類參數的預設值（category／key／value／value_type／default_value／description／is_encrypted；apiKey／db_dsn 類 `is_encrypted=true`、value 空字串）。`application.yml`：`spring.flyway.schemas=console`、`spring.flyway.default-schema=console`、`spring.jpa.properties.hibernate.default_schema=console`、`spring.jpa.hibernate.ddl-auto=validate`（Flyway 與 JPA 實體必須一致，validate 不過就是你的實體錯）。
- JPA 實體映射九張表（execution／import／config 的實體本波只需存在且 validate 通過，不需 Controller）。
- 認證：`POST /api/v1/auth/login {username,password}` → `{accessToken,refreshToken,expiresIn,role}`；`POST /api/v1/auth/refresh`；JWT HS256，access 30 分鐘、refresh 7 天；使用者清單在 `application.yml`（`console.auth.users[]`：admin／operator／viewer，bcrypt 密碼，開發預設密碼寫在 README；secret 讀 `JWT_SECRET` 環境變數，缺就啟動失敗）。RBAC：VIEWER 只能 GET；OPERATOR 可 CRUD＋signoff；ADMIN 全部（settings 寫入下一波）。`/actuator/health`、`/v3/api-docs`、`/swagger-ui/**` 免認證。CORS 允許 `console.cors.allowed-origins`（預設 http://localhost:3000）。
- 回應格式 PRD §7.2：所有成功回應包 `{code,message:"success",data,timestamp(ISO-8601 含 offset),traceId}`；錯誤 `{code,message,errors[{field,message}],timestamp,traceId}`；分頁 `data={content,page,size,totalElements,totalPages}`。traceId＝每請求 UUID（MDC + response header `X-Trace-Id`）。用 `@RestControllerAdvice` 統一；驗證錯誤 400、找不到 404、狀態衝突 409、權限 403、未認證 401。

## 功能規格（本波必做，一條都不能少；對應 RTM 的 US-P／US-G／US-T 與 API-§7.1.1～7.1.3、signoff 三條）
### 專案 `/api/v1/projects`
- POST（201）：必填 name／executionPath／passCriteria；status 預設 DRAFT；**手動建立 signedOff=true**（PRD §5.1.1）；autonomyLevel 預設 3、範圍 1～10；createdBy＝JWT subject。
- GET 列表：分頁 `page,size`（預設 0,10）、`q`（name 模糊）、`status` 篩選、`sort`（updatedAt desc 預設；可 name／status／createdAt）；每列含 goalsCount、tasksCount（都只算未軟刪）、updatedAt。排除 is_deleted。
- GET /{id}：所有欄位＋ goals[]（id、name、status、sortOrder、signedOff、taskCount、completedTaskCount）。
- PUT /{id}：EXECUTING 狀態只准改 name／description（其他欄位有變更→409 附 reason）。
- DELETE /{id}：軟刪除（is_deleted=true、status=ARCHIVED）；EXECUTING→409；連帶軟刪 goals、tasks。
- POST /{id}/signoff：body `{approver}` 必填非空（缺→400）；設 signedOff=true／signedOffBy／signedOffAt（UTC）。
- 狀態轉移照附錄 B.1，用 domain 方法 `transitionTo()` 守，非法轉移→409。
### 目標 `/api/v1/projects/{projectId}/goals`、`/api/v1/goals/{id}`
- POST（201）、GET 列表（含 taskCount／completedTaskCount／完成比例）、GET 詳情（含 tasks[] 標題清單＋dependsOn[]）、PUT、DELETE（軟刪＋連帶軟刪 tasks）、`PUT /api/v1/goals/reorder` body `{projectId, orderedGoalIds[]}` 重排 sortOrder、POST /{id}/signoff。
- dependsOn：PUT 可帶 `dependsOn[]`，寫入 `goal_dependencies`；新增前用 **Kahn 拓撲排序**試算，成環→400（`reason:"依賴成環"`，附環路 id 清單）；自依賴→400；跨專案依賴→400。
- 手動建立 signedOff=true；狀態機附錄 B.2。
### 任務 `/api/v1/goals/{goalId}/tasks`、`/api/v1/tasks/{id}`
- POST（201）、GET 列表、GET 詳情（含 executionLog）、PUT（可改 name／description／passCriteria／maxRetries／evaluatorCommand／expectedOutputRegex／passCriteriaSpec）、DELETE（RUNNING→409）、POST /{id}/retry（只允許 FAILED／ESCALATED：retryCount+1、status=QUEUED；其他→409）、POST /{id}/signoff。
- **NFR-SEC-03**：evaluatorCommand 套黑名單字元集 `{ ! ` > < ~ $ & ; }`（與 AutoClaude `SddToPlaybookAdapter` 同一組），命中→400 列出違規字元；expectedOutputRegex 必須能 `Pattern.compile`，否則 400。
- 狀態機附錄 B.3；手動建立 signedOff=true。

## 測試要求
- 單元：domain 狀態機（每個合法轉移綠、每個非法轉移 409 例外）、Kahn 成環偵測、黑名單消毒、JWT 簽發／驗證／過期。
- 整合（Testcontainers `pgvector/pgvector:pg18`，Docker 已在跑）：Flyway 套用 V1+V2 → `ddl-auto=validate` 通過；三層 CRUD 全流程（建專案→建兩目標含依賴→建任務→列表計數正確→signoff→軟刪連帶）；signoff 缺 approver 400；EXECUTING 刪除 409；RBAC：viewer POST→403、未帶 token→401；回應封包格式與 traceId header。
- ArchUnit：domain 不依賴 org.springframework／jakarta.persistence。
- 覆蓋率：jacoco 報告，後端 ≥ 80%（PRD §9.4），交卷貼總數。

## Dockerfile
PRD §11.4.2 逐字（多階段 gradle build → temurin 21 jre），build context＝`AgentConsole/backend`。`docker build` 要成功；`docker run` 用 `SPRING_DATASOURCE_URL` 指向本機 PG 時 `/actuator/health` 回 UP（本機 PG：`docker run -d --name console-pg -e POSTGRES_PASSWORD=aisdlc -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18`，測完 `docker rm -f console-pg`）。

## 閘門（自己跑，逐字貼）
```
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole/backend
./gradlew clean build                       # 期望 BUILD SUCCESSFUL；貼 test 統計（tests completed / failed）
./gradlew jacocoTestReport && 貼 build/reports/jacoco/test/html/index.html 的總覆蓋率數字（用 grep 抓 <tfoot> 的百分比）
./gradlew bootRun 搭本機 PG → curl -s localhost:8080/actuator/health；curl -s -X POST localhost:8080/api/v1/auth/login …；用 token 建一個專案、列表、signoff、刪除——逐條貼回應 JSON 的 code 與 data 摘要
curl -s localhost:8080/v3/api-docs | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d["paths"]), sorted(d["paths"]))'   # 端點清單要涵蓋本波所有端點
docker build -t aisdlc-backend:dev AgentConsole/backend   # 在 monorepo 根跑；貼最後 3 行
```
- 把 RTM（`AgentConsole/docs/06_quality/RTM.md`）本波完成列的「實作檔／自動測試／狀態」欄回填（狀態寫 `✅ 實作+測試`，E2E 欄留給 QA）。
- 交卷附：Spring Boot 實際版本、springdoc 版本、`gradlew` 是否已 `chmod +x`、`.gitignore`（build/ .gradle/）。

## 追加（主控 2026-10-14 晚；優先於上文衝突處）
1. **骨架已由主控生成**在 `AgentConsole/backend/`（Spring Boot **4.1.1**、Gradle KTS、Java 21 toolchain）。**不要**重跑 start.spring.io。先 `cat build.gradle.kts`：Spring Boot 4 的 starter 名稱是 `spring-boot-starter-webmvc`（不是 `-web`）、`spring-boot-starter-flyway`、`spring-boot-starter-*-test` 分模組、`org.testcontainers:testcontainers-postgresql`。主控已預熱 `~/.gradle` 快取（`sh gradlew dependencies`）。`gradlew` 入庫為 644，所有指令寫 `sh gradlew …`（Windows 用 `.\gradlew.bat`）。
2. 另加依賴：`org.springdoc:springdoc-openapi-starter-webmvc-ui`（Spring Boot 4 相容版本；compile 不過就換版）、`io.micrometer:micrometer-registry-prometheus`（PRD §12.6.1 Prometheus 抓 `/actuator/prometheus`）、`com.tngtech.archunit:archunit-junit5`、jjwt 0.12.x、Checkstyle plugin（PRD §9.4；用 Google 或 Sun 預設規則集的寬鬆版，`checkstyleMain` 要過）。
3. `Create*Request`（專案／目標／任務）加選填 `draft: boolean`（預設 false）：`draft=true` 時 `signedOff=false`（讓前端 E2E 能走 signoff 流程；PRD 手動建立預設 true 不變）。
4. V2 種子：`autoclaude.dalBackend` 預設值改 `FILE`（ADR-001 D13：Bridge 的 pause／restore 靠檔案 checkpoint）。
5. 讀 `AgentConsole/docs/02_architecture/Architecture.md` §11：它列了 **V3（review 表）／V4（alerts 表）** 的 DDL 增補與系統參數對映表——本波一併放進 Flyway（V1 PRD 九表、V2 種子、V3 review、V4 alerts），實體 validate 通過即可，Controller 下一波。
6. `application.yml` 不要寫 `spring.flyway.enabled` 手動步驟（PRD §11.7 第 6 步作廢，啟動即遷移）。Prometheus 端點 `/actuator/prometheus` 免認證（nginx 會擋 `/actuator/` 對外）。
7. 讀 `AgentConsole/docs/04_planning/Implementation_Plan.md` §2 W2 的追加表，逐項對照；回填 Plan 的進度帳 W2-A 列與 RTM。
8. 若 Testcontainers 拉不到 `pgvector/pgvector:pg18`（網路被擋），改用主控已在本機的映像（`docker images | grep pgvector` 現查），仍被擋就在交卷〈沒做〉寫明並改用 `-Dspring.datasource.url` 指向 `docker-compose.dev.yml` 起的 PG 跑整合測試。
