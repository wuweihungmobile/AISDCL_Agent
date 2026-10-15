# 任務書 W5-BE：後端修復棒（Spring Boot 4.1／Java 21）

> 先讀 `W5_OVERVIEW.md`。持有面只有 `backend/**` 與 `docs/06_quality/rtm_backfill_W5BE.md`。契約 v1.2（`docs/02_architecture/API_Contract_P3-6.md`、`openapi-p3-6.yaml`）已由 SA 定稿，你**不改契約**；發現契約錯了就在交卷〈沒做／偏離〉寫明並照契約做（除非做不到）。

## 必讀

契約 v1.2 §0.3／§0.4／§0.5／§1.1.9／§1.2.2／§1.3（task-totals、report）／§1.5.10／§3.7／§6.5；QA 報告 §11 的 DEF-AC-002、DEF-AC-009、觀察 O-04／O-05／O-11／O-14／O-20；`backend/README.md`；既有測試基礎設施 `backend/src/test/java/com/aisdlc/console/support/`（`AbstractExecutionIT`、`MiniBridge`）。

## 範圍（依優先序；每條做完立即 `gradlew clean build`，不累積）

1. **C-6 DEF-AC-002**：`application/service/SettingsService.importSettings`（第 329～355 行）——在 `<encrypted>` 佔位與「加密鍵給明文」判斷之後、值規則與 allowlist 之前，`value.equals(config.value())` 即 `skipped++; continue;`。測試：匯出後原樣匯入 → `applied=0, errors=[]`、`skipped`＝全部；值未變但 URL 不在 allowlist 也 skipped；值有變且不在 allowlist 仍 `OUTBOUND_REJECTED`。
2. **C-1 DEF-AC-009**：`GET /api/v1/monitor/task-totals`（controller／dto／service／repository 查詢）；IT：建兩個專案各跑一批（MiniBridge），total 等於兩個專案 `task-trend` 各桶加總；封存與軟刪除專案不計；`to-from` >92 天 → 400；VIEWER 200。OpenApiIT 路徑數更新。
3. **C-10 F1-1／F1-2**：Flyway `V8__import_record_warnings_and_options.sql`；parse 存 `warnings`／`parseOptions`；`GET /import/{id}` 回兩欄；`SchemaMigrationIT` 覆蓋 V8（遷移名稱清單更新）；`ddl-auto=validate` 通過。
4. **C-11 F2-4**：`GET /projects/{projectId}/executions` 列表項加 `bridgeStatus`。
5. **C-7 O-14**：`domain/service/AlertRules`（或對應處）去重鍵改 `step:<runId>:<stepId>`；`AlertRulesTest` 補「兩個批次同 stepId 各自發告警」。
6. **C-8 O-05**：`GoalService`／`TaskService` 刪除前查專案是否有進行中批次（沿用 execute 的 409 判定），有則 409 `project_executing`；IT 覆蓋。
7. **C-3 NFR-9.3-04**：`POST /projects/{id}/restore`、`GET /projects?deleted=true`、`console.retention.soft-delete-days`（預設 30）、`console.retention.purge-enabled`（預設 false）與每日清除排程（開啟時才註冊）；audit_log `project.restore`；IT：復原後列表回來、目標／任務一併回來、三種 409／404、VIEWER 對 `deleted=true` 403。
8. **C-4 PDF 報表**：`MonitorService` 第 522～527 行拿掉 501；以 PDFBox 3（已在相依中）產生，內嵌 OFL CJK 字型（`src/main/resources/fonts/` 附 LICENSE；下載指令與來源寫在交卷；下載不到就英文標籤並寫明）；`ReportPdfTest`（內容含標題與產生時間、與 CSV 相同的四個區段 `summary`／`runs`／`tasks`／`alerts`、中文字可抽回）；`Content-Disposition` 檔名同 CSV 規則。OpenApi 更新。
9. **C-12 traceId**：`adapter/out/bridge/**` 的每個 Bridge 請求帶 `X-Trace-Id`（取 MDC 的 traceId；背景消費者沒有就用 run 的 traceId 或 `UUID.randomUUID()`）；`BridgeRunsAdapterTest` 斷言標頭存在。
10. **C-16 後端側**：`logback-spring.xml` 在 `LOG_DIR` 有值時加 JSON 行 `RollingFileAppender`（`${LOG_DIR}/console.log`，每日切檔保留 7 天），沒設時行為不變；`server.tomcat.remoteip.internal-proxies` 由 `CONSOLE_INTERNAL_PROXIES` 覆寫（預設值寫 README）。
11. **RTM 回填** `docs/06_quality/rtm_backfill_W5BE.md`（格式照 `rtm_backfill_W3B2.md`）：US-S-06／API-SET-09 → `✅ 實作+測試`（QA 升 ✅ 已驗證）；UI-SCR-01 後端側、API-MON-07、NFR-9.3-04、NFR-9.4-04 後端側、INF-VOL-06 後端側、O-05／O-14 相關列；新列 `API-MON-08`、`API-PRJ-06` 的四格內容（由 QA 追加列）。

## 契約 v1.2 定稿後的補充（SA 交卷，主控已採納；與上文衝突時以契約為準）

- Flyway：**V8**（`import_records.warnings jsonb not null default '[]'`、`parse_options jsonb null`）與 **V9**（`projects.deleted_at`、`projects.status_before_delete`、`goals.deleted_at`、`tasks.deleted_at`；既有 `is_deleted` 不動；刪專案時三者寫同一個時間值，復原以「`deleted_at` 等於專案的」辨識連帶軟刪者、並還原 `status_before_delete`）；SQL 範本在契約 §0.5 與 Architecture §11.3；`SchemaMigrationIT` 版本清單改到 9、`V5UpgradeMigrationIT` 補 V8／V9。
- `domain/exception/ErrorReasons.java`：新增 `project_executing`、`project_not_deleted`、`restore_window_expired`（英文識別字，契約 §0.3 第 5 點、附錄 B.2）；移除 `PDF_NOT_AVAILABLE` 與 `NotImplementedYetException`（含其 handler／測試）。`project_executing` 與既有 `專案正在執行中` 是不同 reason，不混用。
- `OpenApiIT`：路徑 53→55、操作 62→64（以契約附錄／YAML 為準現查）。
- B1-1：`ConfigCatalog.java` 第 91 行附近 `execution.globalTokenBudget` 的 `max` 由 1000000000000 改為 999999999999（12 位，與 V5 驗證規則一致），對應測試更新。
- task-totals 的 400 reason 沿用 `時間範圍不合法`（`errors[].field=to`、`details={from,to,maxDays:92}`），不新增常數。
- `ProjectSummaryResponse` 加 `deletedAt`（只在 `deleted=true` 列表帶值）；`GET /projects?deleted=true` VIEWER 403。
- 清除排程只清專案層級（連同子樹），單獨軟刪的目標／任務不清；`purge-enabled=false` 時不註冊排程（單元測試釘住）。

## 測試要求與閘門

- `Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\backend; .\gradlew.bat clean build --console=plain *> <scratchpad>\be_build.log; "rc=$LASTEXITCODE"; Pop-Location`：BUILD SUCCESSFUL、0 失敗 0 略過、Checkstyle 0、JaCoCo 指令／分支皆 ≥80%（現值 96／84，不得下降超過 1 個百分點）、ArchUnit 通過。
- 新端點有 IT（真 HTTP、Testcontainers PG）；每個新 reason 常數有測試引用；`OpenApiIT` 操作數更新。
- 不得改 `frontend/`、`engine-bridge/`、`docker/`、契約文件；測試夾具不用 `sk-` 前綴與 `user:pw@` DSN。

## 交卷

依 `W5_OVERVIEW.md` §5；〈給 QA 的提醒〉列每條缺陷對應的驗證端點與預期值、Flyway V8 對既有 e2e 資料庫的影響（舊庫啟動會自動升級）。
