# API 契約 — Phase 3～6（BRD/PRD 匯入、專案執行、專案監控、系統設定）

**版本**：v1.0（契約先行；待主控核可後凍結）｜**日期**：2026-10-15｜**作者角色**：SA／SD
**讀者**：後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、QA（依本契約驗收）
**機器可讀版**：[openapi-p3-6.yaml](openapi-p3-6.yaml)（OpenAPI 3.1；schema 名稱、欄位與本文一致；兩者衝突以本文為準並回報修正）
**對應需求**：PRD §5.2～§5.5、§7.1.4～§7.1.8、附錄 B；RTM `API-IMP／SGN／EXE／MON／NTF／SSE／SET／ALR／AUT／DAG`、`US-I／E／M／S`、`NFR-SEC-03／04／05`、`NFR-OBS-01`

> **本文的使用方式**：開發者照 §1（端點）、§2（SSE）、§3（Bridge 與讀模型）施工；QA 照 §5（E2E 情境）與附錄 B（reason 常數）驗收；§4 讓前端確認「設計稿每個元素有沒有資料來源」；§6 列出本文與其他文件不一致處的裁決。
> 只有 §6 與〈未決問題〉（交卷時另附）列出的點尚待主控確認，其餘章節都是可直接施工的定案。

---

## 0. 共通約定

### 0.1 權威順位與事實來源

| 順位 | 來源 | 範圍 |
|------|------|------|
| 1 | PRD §0（校正區）、附錄 B | 需求與狀態機；與下列文件衝突時以 PRD §0 為準（§6 逐條列出實際衝突） |
| 2 | 本契約 | Phase 3～6 的 HTTP／SSE 形狀、錯誤常數、讀模型規則 |
| 3 | `AgentConsole/engine-bridge/README.md`、`app/models.py`、`app/routers/*.py`、`app/runner.py`、`tests/` | **Bridge 行為的唯一真相源**（本文引用的 Bridge 事實皆已對這些檔核對） |
| 4 | Architecture §6／§7／§8／§11、ADR-001 | 架構決策；與本契約衝突處已在 §6 裁決 |
| 5 | `agent_briefs/W3_BACKEND_P3-6.md` | 主控已拍板的後端決策；與本契約衝突處已在 §6 標註 |

### 0.2 封包、型別與格式

| 項目 | 約定 |
|------|------|
| 前綴與編碼 | `/api/v1/**`；請求與回應皆 UTF-8 JSON（檔案端點另述） |
| 成功封包 | `{ "code":200\|201, "message":"success", "data":…, "timestamp":"…", "traceId":"…" }`（`ApiResult<T>`）；`traceId` 與回應標頭 `X-Trace-Id` 相同 |
| 無內容 | 204 沒有本文也沒有封包（`review`、`acknowledge`） |
| 不包封包 | 報表下載（CSV／PDF）、設定匯出（JSON 檔）、SSE |
| 分頁封包 | `data = { content:[…], page, size, totalElements, totalPages }`；`page` 從 0 起算；預設 `size=10`、上限 100（`steps`／`logs` 預設 50、上限 200；`settings/history` 預設 20、上限 100）；超出上限回 400 |
| 排序參數 | `sort=欄位[,asc\|desc]`；欄位白名單各端點註明，未知欄位或方向回 400（沿用 Phase 2 `ProjectController` 的訊息格式） |
| 時間 | ISO-8601 且帶 offset：`Instant` 欄位輸出 `…Z`，`ApiResult.timestamp` 為伺服器時區 offset（如 `+08:00`），Bridge 轉來的 `ts` 為 `+00:00`；三者皆為合法 RFC 3339，client 一律以 `Date.parse` 類函式解析，不比對字串 |
| 列舉 | 值全大寫底線（`IN_PROGRESS`）；例外（逐字常數）：有界閘名稱 `max_steps` 等、`bucket`／`format`／`order` 查詢參數、SSE 事件名（kebab-case） |
| 欄位命名 | camelCase；DTO 命名 `XxxRequest`／`XxxResponse`；`ConfigResponse.isEncrypted`、`CheckpointResponse.isAutomatic` 的 JSON 名稱必須帶 `is` 前綴（Java record 的 boolean 欄位注意序列化名稱，必要時 `@JsonProperty`） |
| null 與缺席 | 值為 null 的欄位可能輸出 `null` 或整個省略；client 視兩者等價（用 `?? default` 讀） |
| ID | 路徑與欄位中的 id 皆小寫帶連字號 UUID；格式不合的路徑參數回 400（Phase 2 既有行為，訊息 `參數 <名> 的值格式不正確`），查無資料回 404 |
| 金額／計數 | Token 一律整數（`int64`）；百分比一律 0～100（不是 0～1）並四捨五入到小數 1 位 |

### 0.3 錯誤封包與 `reason` 常數

錯誤一律使用 Phase 1+2 的 `ApiError`：`{ code, message, reason?, errors:[{field,message}], details?, timestamp, traceId }`；整個後端只有 `GlobalExceptionHandler` 產生它。

1. **`reason` 是前後端共用的常數**：後端集中在 `ErrorReasons`（或等價常數類別），前端集中在 `lib/api/reasons.ts`，兩邊字串逐字相同；E2E 以 `reason` 逐字比對。全部常數見**附錄 B**；各端點小節只列該端點用到的。
2. `message` 是給人看的中文句子（可含動態值），**不得**用來做程式判斷；`details` 的鍵為 camelCase，每個鍵在各端點小節固定。
3. PRD 逐字指定的 reason 一律沿用：`未經人工審批的草案不可執行`、`halt_threshold_pct 必須大於 compact_threshold_pct`。Phase 1+2 既有的 reason（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`／`ACCESS_DENIED`／`MALFORMED_REQUEST_BODY`／`已 signoff`／`目前狀態不可重試`）不變。
4. 狀態碼語意（Phase 3～6 補充）：

| 碼 | 語意 |
|----|------|
| 400 | Bean Validation／格式；`approver` 缺漏；token_guard 跨鍵違規；命令含禁用字元；時間範圍不合法；加密值要求 |
| 401／403 | 未認證（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`）／角色不足（`ACCESS_DENIED`；`reveal=true` 非 ADMIN 另有專屬 reason） |
| 404 | 資源不存在或已軟刪除；`runId`／`checkpointId`／審核項不屬於所述父資源也是 404 |
| 409 | 草案未 signoff 即執行／resume／restore；匯入或執行狀態不允許該操作；並發互斥；審核項已處理；敏感參數未帶 `confirm=true`；Bridge 草案失效 |
| 413／415 | 上傳超過 10MB（匯入）或 1MB（設定檔）／副檔名或類型不支援 |
| 422 | 有界閘與消毒拒絕（含 Bridge 的 422 原因逐字帶出）；SSRF／allowlist 檢查未通過；上傳檔案內容無法讀取 |
| 429 | 超過每分鐘 100 次（見 §0.4） |
| 501 | PDF 報表（W5 前） |
| 502／504 | Bridge 無法連線／逾時（建立執行已補償刪除 run 列） |

### 0.4 認證、角色、CORS 與限流

**角色矩陣**（最低角色；ADMIN ⊃ OPERATOR ⊃ VIEWER）：

| 端點群 | VIEWER | OPERATOR | ADMIN |
|--------|:------:|:--------:|:-----:|
| 匯入讀取（`GET /import`、`GET /import/{id}`） | ✅ | ✅ | ✅ |
| 匯入寫入（upload／text／parse／result／signoff／confirm／reject） | — | ✅ | ✅ |
| 執行讀取（`GET` run／steps／dag／checkpoints／executions）、兩條 SSE | ✅ | ✅ | ✅ |
| 執行寫入（execute／pause／resume／cancel／restore／review） | — | ✅ | ✅ |
| 監控讀取（metrics／趨勢／alerts／logs／report／notifications） | ✅ | ✅ | ✅ |
| 告警確認 | — | ✅ | ✅ |
| 設定讀取（`GET /settings*`、`history`；加密值遮罩） | ✅ | ✅ | ✅ |
| `reveal=true` 揭露加密明文 | — | — | ✅ |
| 設定寫入與工具（PUT／reset／import／export／test-connection） | — | — | ✅ |

**對 `SecurityConfig` 的必要改動**（現行：`GET /api/v1/**` 為 VIEWER 以上、其餘為 OPERATOR 以上）：

1. `/api/v1/settings/**` 的**非 GET** 一律要求 ADMIN（含 `POST /settings/export`、`/settings/import`、`/settings/test-connection`，它們是 POST 但屬 ADMIN 專用）；`GET …?reveal=true` 由 Controller 檢查角色，非 ADMIN 回 403（reason `僅 ADMIN 可揭露敏感參數`）。
2. **SSE 認證**（兩種都收，主控裁決）：`/api/v1/stream/**` 先看 `Authorization: Bearer`，沒有才看查詢參數 `access_token`。只收 access token；refresh token 一律 401（`TOKEN_INVALID`）；此查詢參數**僅限 `/api/v1/stream/**`**（其他路徑出現一律忽略）。補強：存取日誌與 `AuditLoggingFilter` 須遮罩 `access_token`；SSE 回應帶 `Cache-Control: no-store`。
3. **CORS**：`allowedHeaders` 補 `Last-Event-ID`；`exposedHeaders` 補 `X-Follow-Up-Run-Id`、`Retry-After`、`Content-Disposition`。
4. **限流**（NFR-9.2-06）：每個客戶端 IP 每 60 秒 100 次（Bucket4j 記憶體實作；Redis 為選配）。對象＝`/api/**`；不計入：`/actuator/**`、`/v3/api-docs`、SSE 連線建立之後的串流本身（建立請求算 1 次）。超限回 **429**：`reason`＝`超過每分鐘 100 次請求上限`、`details={limit:100, windowSeconds:60, retryAfterSeconds:N}`，並帶標頭 `Retry-After`（秒）、`X-RateLimit-Limit: 100`、`X-RateLimit-Remaining: 0`；成功回應也帶後兩個標頭。客戶端 IP 預設取連線位址；**只在**設定 `console.security.rate-limit.trust-forwarded-for=true`（e2e profile 開啟）時取 `X-Forwarded-For` 第一段，供測試以不同 IP 隔離桶。限流以 `console.security.rate-limit.enabled` 開關（預設 `true`；單元／整合測試 profile 預設 `false`，但必須有一支測試開著它打 101 次、驗第 101 次回 429；e2e profile 為 `true`）。
5. 審計（NFR-9.2-07）：沿用 `AuditLoggingFilter` 的結構化 JSON 日誌；Phase 3～6 追加兩個欄位 `action`（例：`import.signoff`、`execution.review.APPROVE`、`settings.reveal`）與 `entity`（`<type>:<id>`）。另依任務書把寫入端點（POST／PUT／PATCH／DELETE）落一列到 `console.audit_log`（V6；**內部實作**，寫入失敗不得影響主請求；契約沒有任何端點讀它，見 §6 D-13）。

### 0.5 資料庫增補（Flyway；契約所需）

現況：V1～V4 已套用（`V3__review_requests`、`V4__monitor_alerts` 在 Phase 1+2 已建表）。本契約涉及 **V5～V7**；版號依任務書分工：V5、V6 屬後端第一棒（W3-B1），V7 屬後端第二棒（W3-B2，在 B1 交卷後的同一棵樹上接續，所以版號不會撞）；V1～V4 **不得修改**。

**V5 `V5__seed_engine_configs.sql`**（Architecture §11.4 的 V5 補充鍵；Phase 6）：新增九個鍵、補全部鍵的 `validation_rule`，並新增欄位 `system_configs.impact_note VARCHAR(500)`（US-S-08）。

| 類別 | 鍵 | valueType | 預設 |
|------|----|-----------|------|
| autoclaude | `claudeCommand` | STRING | `claude` |
| autoclaude | `claudeExtraArgs` | STRING | （空字串） |
| autoclaude | `claudeContinueFlag` | STRING | `--continue` |
| autoclaude | `claudeEncoding` | STRING | `utf-8` |
| autoclaude | `dbDsn` | ENCRYPTED（`is_encrypted=TRUE`） | （空字串） |
| autoclaude | `dualReadResolution` | ENUM | `yaml_wins` |
| model | `enableKernelBrain` | BOOLEAN | `false` |
| execution | `autoResume` | BOOLEAN | `true` |
| execution | `maxAutoResumes` | INTEGER | `10` |

中繼資料的歸屬：`options`／`min`／`max`／`effect` 放程式內的 `ConfigCatalog`（附錄 C 是唯一真相源），不入 DB；`impactNote` 讀 `system_configs.impact_note`。V5 把附錄 C 的 `validationRule` 正規表示式寫進 `system_configs.validation_rule`、把附錄 C 的 `impactNote` 寫進 `impact_note`（任務書點名的 8 個關鍵鍵為最低要求，附錄 C 有影響提示者一併寫入）。

**V6 `V6__audit_log.sql`**（W3-B1；**內部實作**，不進 HTTP 契約）：`console.audit_log(id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id)`，欄位依任務書；§0.4 第 5 點說明寫入規則。

**V7 `V7__console_event_anchors_and_token_samples.sql`**（W3-B2）：

```sql
-- Console 自產 SSE 事件（review-request／alert）的重播錨點；子序號規則見 §2.2
ALTER TABLE console.review_requests
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;
ALTER TABLE console.alerts
    ADD COLUMN event_seq INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN event_sub INTEGER NOT NULL DEFAULT 1;      -- 0＝Bridge 告警事件的持久化鏡像（SSE 不重播它）

-- console-api 已處理到的 Bridge 事件 seq（Console 擁有此欄；Bridge 不寫）
ALTER TABLE console.execution_runs
    ADD COLUMN console_last_seq INTEGER NOT NULL DEFAULT 0;

-- Token 趨勢與任務 Token 歸因的來源（Bridge 不寫 execution_steps.tokens_used，見 §6 D-16）
CREATE TABLE console.run_token_samples (
    run_id      UUID NOT NULL REFERENCES console.execution_runs(id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    tokens_used BIGINT NOT NULL,            -- 本批次累計（Bridge token 事件的 tokens_used）
    delta       BIGINT NOT NULL,            -- 與前一則的差
    context_pct DOUBLE PRECISION,
    task_id     UUID REFERENCES console.tasks(id),   -- 增量歸因的任務（目前 RUNNING 的步驟）
    PRIMARY KEY (run_id, seq)
);
CREATE INDEX idx_run_token_samples_ts ON console.run_token_samples(ts);

-- 同一規則＋對象在被確認前不重複產生告警（PRD §5.4.4；DB 層兜底）
CREATE UNIQUE INDEX uq_alerts_open_rule_subject
    ON console.alerts(project_id, rule, subject) WHERE acknowledged = FALSE;
```

實作注意：(a) `execution_runs` 的 `status／subprocess_pid／bridge_instance／advisory_lock_key／total_tokens_used／completed_at` 由 Bridge 寫，`ExecutionRunEntity` 對它們一律唯讀（`updatable=false` 或只用目標明確的 `UPDATE … SET console_last_seq=?`），避免 JPA 整列回寫蓋掉 Bridge 的更新（PRD §0.2.2）；(b) `alerts.subject` 對規則型告警永遠非 null（否則 partial unique index 對 NULL 失效）；(c) `review_requests.kind` 的 CHECK（V3）**不擴充**，四種 kind 足夠（§3.6）。

### 0.6 名詞對照

| Bridge | Console | 說明 |
|--------|---------|------|
| `run_id` | `execution_runs.id`、路徑 `{runId}` | 同一個 UUID |
| `step_id`（playbook） | `dag.nodes[].stepId`、`ExecutionStepResponse.stepId` | 例 `G1-T2`；與審核項路徑的 `{stepId}`（＝`review_requests.id`）**不是同一個東西** |
| `goal_task_id`（playbook 每步欄位） | `tasks.id` | Bridge 以它寫 `execution_steps.task_id` |
| `checkpoint_id` | `checkpoints.id`、路徑 `{checkpointId}` | 同值 |
| `seq`（事件序號） | SSE `id:` 的整數部分；`execution_steps.step_number` | 同一個序號空間 |
| 八態（INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING／COMPLETED／FAILED／CANCELLED） | `RunStatus` 六態＋`bridgeStatus` | `PAUSING`／`CANCELLING` 折為 `RUNNING`；原值放 `bridgeStatus` |
| `alert.level` `info`／`warning`／`error` | `AlertSeverity` `INFO`／`WARNING`／`CRITICAL`（SSE）；持久化只用 `WARNING`／`CRITICAL` | |

---
## 1. 端點總表與逐端點契約

### 1.0 總表（40 個端點；SSE 兩條詳見 §2）

「補」＝PRD 未列、為設計稿或 Architecture 所需的補充端點（§6 D-05、D-10…）。Phase 2 已實作的 `POST /projects|goals|tasks/{id}/signoff`（`API-SGN-02～04`）不重複定義。

| # | 方法 路徑 | 角色 | Request → Response（成功碼） | RTM／US |
|---|-----------|------|------------------------------|---------|
| 1 | `GET /api/v1/import` | VIEWER | 查詢參數 → `Page<ImportRecordResponse>`（200） | API-IMP-06／US-I-06 |
| 2 | `POST /api/v1/import/upload` | OPERATOR | multipart `file` → `ImportRecordResponse`（201） | API-IMP-01、07／US-I-01 |
| 3 | `POST /api/v1/import/text` | OPERATOR | `TextImportRequest` → `ImportRecordResponse`（201） | API-IMP-02／US-I-02 |
| 4 | `GET /api/v1/import/{id}`（補） | VIEWER | → `ImportRecordDetailResponse`（200） | API-IMP-06／US-I-03、06 |
| 5 | `POST /api/v1/import/{id}/parse` | OPERATOR | `ParseOptions` → `ParseResultResponse`（200） | API-IMP-03、08、09／US-I-03、05、07、08、10 |
| 6 | `PUT /api/v1/import/{id}/result` | OPERATOR | `EditParsedResultRequest` → `ParseResultResponse`（200） | API-IMP-04／US-I-04、10 |
| 7 | `POST /api/v1/import/{id}/signoff` | OPERATOR | `SignoffRequest` → `ImportRecordResponse`（200） | API-SGN-01／US-I-09 |
| 8 | `POST /api/v1/import/{id}/confirm` | OPERATOR | — → `ProjectResponse`（201） | API-IMP-05、10／US-I-09 |
| 9 | `POST /api/v1/import/{id}/reject`（補） | OPERATOR | — → `ImportRecordResponse`（200） | API-IMP-10 |
| 10 | `POST /api/v1/projects/{projectId}/execute` | OPERATOR | `StartExecutionRequest` → `ExecutionRunResponse`（201） | API-EXE-01、11、12、13／US-E-01、02、10 |
| 11 | `GET /api/v1/projects/{projectId}/executions`（補） | VIEWER | 查詢參數 → `Page<ExecutionRunSummaryResponse>`（200） | API-EXE-14／US-M-06 |
| 12 | `GET /api/v1/executions/{runId}` | VIEWER | → `ExecutionRunDetailResponse`（200） | API-EXE-05／US-E-07、M-10 |
| 13 | `POST /api/v1/executions/{runId}/pause` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-02／US-E-04 |
| 14 | `POST /api/v1/executions/{runId}/resume` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-03、11／US-E-05 |
| 15 | `POST /api/v1/executions/{runId}/cancel` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-04／US-E-06 |
| 16 | `GET /api/v1/executions/{runId}/steps` | VIEWER | `page,size,afterSeq` → `Page<ExecutionStepResponse>`（200） | API-EXE-06、SSE-03／US-M-03、09 |
| 17 | `GET /api/v1/executions/{runId}/dag` | VIEWER | → `DagResponse`（200） | API-EXE-07、DAG-01／US-E-09 |
| 18 | `GET /api/v1/executions/{runId}/checkpoints` | VIEWER | → `List<CheckpointResponse>`（200） | API-EXE-08／US-E-11 |
| 19 | `POST /api/v1/executions/{runId}/restore/{checkpointId}` | OPERATOR | — → `ExecutionRunResponse`（200） | API-EXE-09、11／US-E-11 |
| 20 | `POST /api/v1/executions/{runId}/review/{stepId}` | OPERATOR | `ReviewRequest` → 無內容（204） | API-EXE-10、AUT-01～06／US-E-07、08 |
| 21 | `GET /api/v1/monitor/projects/{projectId}/metrics` | VIEWER | `runId,from,to` → `ProjectMetricsResponse`（200） | API-MON-01／US-M-01、10 |
| 22 | `GET /api/v1/monitor/projects/{projectId}/token-trend` | VIEWER | `runId,from,to,bucket` → `List<TokenTrendPoint>`（200） | API-MON-02／US-M-02 |
| 23 | `GET /api/v1/monitor/projects/{projectId}/task-trend` | VIEWER | 同上 → `List<TaskTrendPoint>`（200） | API-MON-03／US-M-03 |
| 24 | `GET /api/v1/monitor/projects/{projectId}/alerts` | VIEWER | `runId,acknowledged,limit` → `List<AlertResponse>`（200） | API-MON-04、ALR-01～06／US-M-05 |
| 25 | `POST /api/v1/monitor/alerts/{alertId}/acknowledge` | OPERATOR | — → 無內容（204） | API-MON-05／US-M-05 |
| 26 | `GET /api/v1/monitor/projects/{projectId}/logs` | VIEWER | 篩選＋分頁 → `Page<LogEntryResponse>`（200） | API-MON-06／US-M-04 |
| 27 | `GET /api/v1/monitor/projects/{projectId}/report` | VIEWER | `format=csv\|pdf,…` → 檔案（200） | API-MON-07／US-M-07 |
| 28 | `GET /api/v1/notifications/summary`（補） | VIEWER | → `NotificationSummaryResponse`（200） | API-NTF-01／US-E-07 |
| 29 | `GET /api/v1/stream/executions/{runId}/logs` | VIEWER | SSE（§2） | API-SSE-01、03／US-E-03、07 |
| 30 | `GET /api/v1/stream/executions/{runId}/metrics` | VIEWER | SSE（§2） | API-SSE-02、03／US-E-03 |
| 31 | `GET /api/v1/settings` | VIEWER | `reveal` → `Map<category,List<ConfigResponse>>`（200） | API-SET-01／US-S-01、04、08 |
| 32 | `GET /api/v1/settings/{category}` | VIEWER | `reveal` → `List<ConfigResponse>`（200） | API-SET-02／US-S-01、04 |
| 33 | `PUT /api/v1/settings/{category}/{key}` | ADMIN | `UpdateConfigRequest` → `ConfigResponse`（200） | API-SET-03、10／US-S-02、08 |
| 34 | `PUT /api/v1/settings/execution/token-guard` | ADMIN | `TokenGuardRequest` → `List<ConfigResponse>`（200） | API-SET-04／NFR-SEC-05 |
| 35 | `POST /api/v1/settings/{category}/{key}/reset` | ADMIN | `confirm` → `ConfigResponse`（200） | API-SET-05／US-S-03 |
| 36 | `POST /api/v1/settings/{category}/reset`（補） | ADMIN | `confirm` → `List<ConfigResponse>`（200） | API-SET-05／US-S-03 |
| 37 | `POST /api/v1/settings/test-connection` | ADMIN | `TestConnectionRequest?` → `ConnectionTestResponse`（200） | API-SET-06／US-S-05／NFR-SEC-04 |
| 38 | `GET /api/v1/settings/history` | VIEWER | 篩選＋分頁 → `Page<ConfigHistoryResponse>`（200） | API-SET-07／US-S-07 |
| 39 | `POST /api/v1/settings/export` | ADMIN | — → `SettingsExportDocument`（200，檔案） | API-SET-08／US-S-06 |
| 40 | `POST /api/v1/settings/import` | ADMIN | multipart `file` → `ImportSettingsResponse`（200） | API-SET-09／US-S-06 |

---

### 1.1 BRD/PRD 匯入（Phase 3）

匯入記錄狀態機（`API-IMP-10`）：

```
UPLOADED ──parse──▶ PARSING ──成功──▶ PARSED ──PUT result──▶ REVIEWING
   ▲                   │失敗(422)          │                      │
   └───────────────────┘                  └────signoff／confirm───┘ ──confirm──▶ IMPORTED
任一非終態 ──reject──▶ REJECTED        （IMPORTED、REJECTED 為終態）
```

| 目前狀態 | parse | PUT result | signoff | confirm | reject |
|----------|:-----:|:----------:|:-------:|:-------:|:------:|
| UPLOADED | ✅ | ✗ | ✗ | ✗ | ✅ |
| PARSING | ✗ | ✗ | ✗ | ✗ | ✗ |
| PARSED | ✅（未 signoff） | ✅ | ✅ | ✅（需已 signoff） | ✅ |
| REVIEWING | ✅（未 signoff） | ✅（撤銷 signoff） | ✅ | ✅（需已 signoff） | ✅ |
| IMPORTED／REJECTED | ✗ | ✗ | ✗ | ✗（IMPORTED 回 `已匯入`） | ✗ |

✗ 一律 409：reason `匯入記錄狀態不允許此操作`，`details={action, status}`（`action` ∈ `parse|editResult|signoff|confirm|reject`）。signoff 後再 parse → 409 `已 signoff，不可重新解析`。

#### 1.1.1 `POST /api/v1/import/upload`　上傳檔案　〔API-IMP-01、API-IMP-07／US-I-01〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**：`multipart/form-data`，欄位 `file`（必填）。副檔名限 `.md`／`.pdf`／`.docx`（不分大小寫）；大小 ≤ 10 MB（10,485,760 bytes；Spring `max-file-size=10MB`、`max-request-size=11MB`）。
- **文字擷取**（後端，存入 `import_records.source_content`；檔名只留 basename、≤ 500 字元）：`.md` 以嚴格 UTF-8 解碼（BOM 容許）；`.pdf` 用 Apache PDFBox 逐頁抽文字；`.docx` 用 Apache POI XWPF 依序抽段落與表格儲存格文字（儲存格以 tab 分隔、段落以換行）。先驗魔術位元組（`%PDF-`／ZIP `PK\x03\x04`）再解析。
- **成功 201**：`ApiResult<ImportRecordResponse>`；`status=UPLOADED`、`signedOff=false`、`sourceType` 依副檔名為 `MARKDOWN`／`PDF`／`DOCX`。

```json
{ "code":201, "message":"success", "data":{
    "id":"7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e01", "sourceType":"MARKDOWN", "sourceFileName":"e2e-brd.md",
    "status":"UPLOADED", "signedOff":false, "createdAt":"2026-10-15T08:30:12Z" },
  "timestamp":"2026-10-15T16:30:12+08:00", "traceId":"0f7c2a58-4e1d-4b29-9d3e-6a1b5c8d9e02" }
```

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | `未提供檔案` | — | 沒有 `file` 部件 |
| 400 | `檔案是空的` | — | 0 bytes |
| 413 | `檔案超過 10MB 上限` | `{limitBytes:10485760}` | `MaxUploadSizeExceededException` |
| 415 | `只支援 .md／.pdf／.docx 檔案` | `{extension, allowed:[".md",".pdf",".docx"]}` | 副檔名不在清單 |
| 422 | `檔案內容與副檔名不符` | `{extension}` | 魔術位元組不符 |
| 422 | `檔案不是有效的 UTF-8 文字` | — | `.md` 解碼失敗 |
| 422 | `PDF 已加密，無法擷取文字` | — | 需要密碼 |
| 422 | `檔案已損毀，無法讀取` | — | PDFBox／POI 解析例外 |
| 422 | `無法從檔案擷取文字` | — | 擷取後全為空白（例：掃描檔） |
| 401／403／429 | 通用 | | |

#### 1.1.2 `POST /api/v1/import/text`　貼上純文字　〔API-IMP-02／US-I-02〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**（`TextImportRequest`）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `content` | string | ✅ | 1～2,000,000 字元；不可全為空白 |
| `sourceFileName` | string | — | ≤ 500；省略時存 null |
| `sourceType` | `PLAIN_TEXT`｜`MARKDOWN` | — | 預設 `PLAIN_TEXT`；其他值 400（`PDF`／`DOCX` 只能由 upload 產生） |

- **成功 201**：`ImportRecordResponse`（同 1.1.1）。
- **錯誤**：400 Bean Validation（`errors=[{field:"content",message:"內容不可為空"}]`，reason 省略）；401／403／429 通用。

#### 1.1.3 `POST /api/v1/import/{id}/parse`　觸發 AI 解析　〔API-IMP-03、08、09／US-I-03、05、07、08、10〕

- **角色**：OPERATOR。**Bridge**：路徑 A／C 會呼叫（§3.3）。**同步**呼叫（UI「解析中」），路徑 B 的逾時＝`model.timeout` 秒；反向代理須放寬 read timeout（建議 180 秒）。
- **Request**（`ParseOptions`）：

| 欄位 | 型別 | 必填 | 規則 |
|------|------|:----:|------|
| `executionPath` | string | ✅ | ≤ 500；絕對路徑格式（POSIX `/…`、磁碟機 `C:\…` 或 `C:/…`、UNC `\\host\share`）；不得含 NUL。Bridge 的 allowlist 在執行時才驗（ADR-001 G-15：不提供瀏覽按鈕） |
| `autonomyLevel` | int | — | 1～10，預設 3；成為落庫專案的 `autonomyLevel` |
| `additionalPrompt` | string | — | ≤ 4,000 |
| `specDir` | string | — | ≤ 500；明示的 SDD 規格目錄（絕對路徑）。省略＝以 `executionPath` 探測 |

- **處理**：狀態 `PARSING` → 依 §3.3 選路徑與轉換 → 套三道有界閘與 `prompt_too_long` → 成功存 `parsed_result`、`ai_model`、`token_used`，狀態 `PARSED`、`signedOff=false`、清空 `lastParseErrors`；失敗狀態退回 `UPLOADED` 並存 `lastParseErrors`。
- **成功 200**：`ParseResultResponse`（欄位逐一說明見 §3.3.6）：

```json
{ "code":200, "message":"success", "data":{
    "importId":"7d9f3b52-1c0a-4e8e-9a43-5f6b2c1d8e01", "status":"PARSED", "path":"LLM",
    "signedOff":false, "aiModel":"e2e-model", "tokenUsed":1152, "errors":[], "warnings":[],
    "parsedResult":{
      "project":{ "name":"E2E 匯入專案", "executionPath":"<E2E_ROOT>/proj-import",
                  "passCriteria":"三個目標全部完成", "description":"由 BRD 匯入", "autonomyLevel":3 },
      "goals":[
        { "key":"g1", "name":"基礎", "passCriteria":"基礎任務完成", "sortOrder":0, "dependsOn":[],
          "tasks":[ { "name":"初始化", "description":"請輸出 [T1_DONE]", "passCriteria":"輸出含 [T1_DONE]", "sortOrder":0 } ] },
        { "key":"g2", "name":"核心", "passCriteria":"核心任務完成", "sortOrder":1, "dependsOn":["g1"],
          "tasks":[ { "name":"實作", "description":"請輸出 [T3_DONE]", "passCriteria":"輸出含 [T3_DONE]", "sortOrder":0 } ] } ],
      "path":"LLM", "aiModel":"e2e-model", "tokenUsed":1152 } },
  "timestamp":"2026-10-15T16:30:14+08:00", "traceId":"…" }
```

| HTTP | reason | details／errors | 觸發 |
|------|--------|-----------------|------|
| 400 | （Bean Validation） | `errors=[{field:"executionPath",message:"必須是絕對路徑"}…]` | 欄位驗證 |
| 404 | （訊息）`匯入記錄不存在或已刪除：<id>` | — | |
| 409 | `解析中，請稍候` | `{status:"PARSING"}` | 同一筆並發 parse |
| 409 | `已 signoff，不可重新解析` | `{signedOffBy,signedOffAt}` | |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"parse",status}` | IMPORTED／REJECTED |
| 422 | `解析結果未通過有界閘` | `errors[]` 每項 `{field,message,gate,detail,location?}`（**列出全部違規**）；`details={path}` | §3.3.5 |
| 422 | `SDD 規格檢查未通過` | `details={bridgeReason,detail}`；`errors=[{field:"specDir",message}]` | 規格存在但被 Bridge 拒（`spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_ambiguous`；明示 `specDir` 時 `spec_not_found` 與路徑消毒失敗亦同） |
| 502／504 | `引擎橋接服務無法連線`／`引擎橋接服務逾時` | | 路徑 A（明示 specDir）或 C 的 Bridge 不可達 |
| 401／403／429 | 通用 | | |

#### 1.1.4 `PUT /api/v1/import/{id}/result`　編輯解析結果　〔API-IMP-04／US-I-04、10〕

- **角色**：OPERATOR。**Bridge**：無。
- **Request**（`EditParsedResultRequest`）：`{ "parsedResult": ParsedResult }`。`project` 與 `goals` 必填；`path`／`aiModel`／`tokenUsed`／`reasoning`／`draftIds`／`specDigest` 為伺服器擁有，**請求帶了也忽略**。
- **整樹覆寫規則**：陣列順序即排序，`sortOrder` 由伺服器重編為 0 起連續整數；每個目標的 `key` 在整棵樹內唯一（前端新增目標時自行產生，例如 `g-<短 uuid>`）；`dependsOn` 引用其他目標的 `key`。
- **驗證順序**：① 400 結構（缺必填、長度、`goals` 為空、某目標 `tasks` 為空、`name`／`passCriteria` 空白）→ ② 400 消毒（`evaluatorCommand` 含禁用字元 `` !`><~$&; `` → reason `命令含禁用字元`＋`details.violations`；`expectedOutputRegex` 無法編譯；與 Phase 2 任務建立同規則）→ ③ 422 有界閘（§3.3.5，列出全部違規）。
- **效果**：狀態 `REVIEWING`；**撤銷既有 signoff**（`signedOff=false`、`signedOffBy／At` 清空）；回 `ParseResultResponse`（`errors=[]`）。
- **錯誤**：404；409 `匯入記錄狀態不允許此操作`（`action:"editResult"`，僅 PARSED／REVIEWING 可編輯）；400；422 `解析結果未通過有界閘`；401／403／429。

#### 1.1.5 `POST /api/v1/import/{id}/signoff`　🔴 人工 signoff　〔API-SGN-01／US-I-09〕

- **角色**：OPERATOR。**Bridge**：路徑 C 對每個 `draftIds` 呼叫 `POST /autoclaude/decompose/{draft_id}:approve`。
- **Request**（`SignoffRequest`，Phase 2 同名）：`{ "approver": "<非空白>" }`。
- **處理**：驗 `approver` 非空白 → 狀態須為 PARSED／REVIEWING 且未 signoff → 逐一 `:approve`（Bridge 回 `already_signed_off` 視為成功；任一其他失敗 → 502／409 且**不改任何狀態**）→ 設 `signedOff=true`、`signedOffBy=approver.strip()`、`signedOffAt=now`。
- **成功 200**：`ImportRecordResponse`（**偏離 PRD §7.1.4.1 的回傳型別**：signoff 只批准、不落庫；`confirm` 才建立專案，ADR-001 D12）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation）`approver 不可為空（人工 signoff 不可匿名）` | `errors=[{field:"approver"…}]` | 缺漏或空白 |
| 404 | （訊息） | | |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"signoff",status}` | 非 PARSED／REVIEWING |
| 409 | `已 signoff` | `{signedOffBy,signedOffAt}` | 重複 signoff（Phase 2 同常數） |
| 409 | `草案已失效，請重新解析` | `{draftId}` | Bridge 對該 draft 回 404 `draft_not_found`（workspace 被清） |
| 502／504 | 同上 | | Bridge 不可達 |
| 401／403／429 | 通用 | | |

#### 1.1.6 `POST /api/v1/import/{id}/confirm`　確認匯入　〔API-IMP-05、10／US-I-09〕

- **角色**：OPERATOR。**Bridge**：無（signoff 已處理）。
- **前置**：狀態 PARSED／REVIEWING 且 `signedOff=true`。
- **處理**：**單一交易**建立 Project（`status=DRAFT`、`autonomyLevel`＝`parsedResult.project.autonomyLevel ?? 3`、`createdBy`＝JWT subject）→ Goals（`sortOrder`＝陣列序、`dependsOn` 由 key 換成 id 並再跑 Kahn）→ Tasks（`maxRetries` 預設 3）。**全部 `signedOff=true`，`signedOffBy／At` 承襲匯入記錄**。再次套用 Phase 2 的欄位消毒（`PassCriteriaSanitizer`）；回寫 `projectId`、`status=IMPORTED`。任何一步失敗整個交易回滾。
- **成功 201**：`ApiResult<ProjectResponse>`（Phase 2 同名 schema）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation／`命令含禁用字元`） | `errors[].field` 為 `parsedResult.goals[i].tasks[j].…` | 落庫前複驗不過 |
| 404 | （訊息） | | |
| 409 | `草案尚未 signoff，不可確認匯入` | `{status,signedOff:false}` | 未 signoff（設計稿：須先 signoff 才能「確認匯入」） |
| 409 | `已匯入` | `{projectId}` | 狀態 IMPORTED |
| 409 | `匯入記錄狀態不允許此操作` | `{action:"confirm",status}` | UPLOADED／PARSING／REJECTED |
| 401／403／429 | 通用 | | |

#### 1.1.7 `POST /api/v1/import/{id}/reject`　放棄匯入（補）　〔API-IMP-10〕

- **角色**：OPERATOR。無 body。非終態且非 PARSING 的記錄 → `status=REJECTED`，回 200 `ImportRecordResponse`。IMPORTED／REJECTED／PARSING → 409 `匯入記錄狀態不允許此操作`（`action:"reject"`）。不呼叫 Bridge（Bridge 草案檔留在其 workspace，由其清理）。

#### 1.1.8 `GET /api/v1/import`　查詢匯入歷史　〔API-IMP-06／US-I-06〕

- **角色**：VIEWER。查詢參數：`page,size`、`status`（`ImportStatus`）、`q`（來源檔名模糊搜尋，不分大小寫，`%`／`_` 視為字面）、`sort`（`createdAt|status`，預設 `createdAt,desc`）。
- **成功 200**：`Page<ImportRecordResponse>`（列表不含 `sourceContent`、`parsedResult`）。錯誤：400（未知 status／sort）、401／429。

#### 1.1.9 `GET /api/v1/import/{id}`　查詢詳情（補）　〔API-IMP-06／US-I-03〕

- **角色**：VIEWER。**成功 200**：`ImportRecordDetailResponse`＝`ImportRecordResponse` ＋ `sourceContent` ＋ `parsedResult`（尚未解析為 null）。錯誤：400（id 格式）、404、401／429。

---
### 1.2 專案執行（Phase 4）

本節的 Bridge 行為皆依 `AgentConsole/engine-bridge/README.md` 與 `app/runner.py`：pause 只收 RUNNING、resume 只收 PAUSED、stop 收 RUNNING／PAUSING／PAUSED、restore 收 PAUSED 與三個終態；其餘一律 409 `invalid_state`。**同一個 run 的「控制操作」與「事件消費／讀模型更新」在 console-api 內以 per-run 互斥鎖序列化**，避免還原或取消與事件處理互相踩踏。

控制類端點（pause／resume／cancel／restore）的回應都是 `ExecutionRunResponse` **快照**：呼叫 Bridge 動作成功後，立刻再讀一次 Bridge `GET /autoclaude/runs/{id}`，`status`＝六態折疊值、`bridgeStatus`＝Bridge 原值（例：pause 後為 `RUNNING`＋`PAUSING`；暫停中的 run 被 cancel 則 Bridge 已同步到 `CANCELLED`，回應即為 `CANCELLED`）。

#### 1.2.1 `POST /api/v1/projects/{projectId}/execute`　啟動執行　〔API-EXE-01、11、12、13、DAG-01、AUT／US-E-01、02、10〕

- **角色**：OPERATOR。**Bridge**：`POST /autoclaude/runs`。
- **Request**（`StartExecutionRequest`；body 可為 `{}`）：

| 欄位 | 型別 | 必填 | 預設 | 規則 |
|------|------|:----:|------|------|
| `autonomyLevel` | int | — | 專案的 `autonomyLevel` | 1～10 |
| `tokenBudget` | int64 | — | 系統參數 `execution.globalTokenBudget` | ≥ 1 |
| `scope.mode` | `ALL`｜`SELECTED` | — | `ALL` | `ALL` 時不可帶 `goalIds`／`taskIds`；`SELECTED` 時兩者至少一個非空 |
| `scope.goalIds` | uuid[] | — | `[]` | 該專案內未刪除的目標 |
| `scope.taskIds` | uuid[] | — | `[]` | 該專案內未刪除的任務 |
| `scope.limits.taskTokens`／`goalTokens` | int64 | — | 無 | ≥ 1；US-E-10 的單一任務／目標上限 |

- **範圍解析**：`ALL`＝專案內全部「可執行」任務（狀態不是 `COMPLETED`／`SKIPPED`）；`SELECTED`＝所選目標的全部可執行任務 ∪ 所選任務。目標順序＝依 `goal_dependencies` 做 Kahn 拓撲排序，同層依 `execution.dagSchedulerStrategy` 擇一（`TOPOLOGICAL`／`PRIORITY`＝`sortOrder` 升冪；`SHORTEST_FIRST`＝所屬目標內預估 Token 總和升冪，null 視為 0，平手取 `sortOrder`）；目標內任務依 `sortOrder`（平手取 `createdAt`、`id`）。展平後為 playbook 的步驟序列。
- **驗證順序（固定，QA 依序斷言）**：

| # | 檢查 | HTTP | reason | details |
|---|------|------|--------|---------|
| 1 | 專案存在且未軟刪除 | 404 | （訊息）`專案不存在或已刪除：<id>` | — |
| 2 | Bean Validation（等級／預算／mode／ids 格式） | 400 | （無） | `errors[]` |
| 3 | 專案狀態為 `EXECUTING` | 409 | `專案正在執行中` | `{projectId, runId}` |
| 4 | 專案狀態為 `ARCHIVED`（`DRAFT`／`READY`／`FAILED`／`COMPLETED` 皆可進入後續檢查） | 409 | `專案狀態不允許執行` | `{status}` |
| 5 | 專案、所選目標、所選任務皆 `signedOff=true` | 409 | `未經人工審批的草案不可執行`（message：`草案未經人工審批，禁止執行`） | `{unsignedProjectId\|null, unsignedGoalIds[], unsignedTaskIds[]}` |
| 6 | `goalIds`／`taskIds` 皆屬於該專案 | 400 | `所選範圍不合法` | `{invalidGoalIds[], invalidTaskIds[]}` |
| 7a | `SELECTED` 內有已 `COMPLETED`／`SKIPPED` 的目標或任務 | 409 | `所選任務或目標已完成` | `{goalIds[], taskIds[]}` |
| 7b | 所選目標依賴了「未選且未完成」的目標 | 409 | `所選目標依賴未完成的前置目標` | `{missingGoalIds[]}` |
| 7c | 解析後沒有任何可執行任務 | 409 | `沒有可執行的任務` | — |
| 8 | 目標依賴成環（防禦；Phase 2 已擋） | 409 | `依賴成環` | `{cycle[]}` |
| 9a | 任一步驟 prompt（§3.4.3 樣板組好後）超過 20,000 字元 | 422 | `步驟 prompt 超過 20000 字元上限` | `{taskId, stepId, length, limit:20000}` |
| 9b | 評估指令含禁用字元（第 2 層複驗，NFR-SEC-03） | 422 | `評估指令含禁用字元` | `{taskId, chars[]}` |
| 9c | 評估指令首個 token 不在可執行檔白名單（附錄 D.3） | 422 | `評估指令不在可執行檔白名單` | `{taskId, executable}` |
| 9d | `expectedOutputRegex` 無法編譯 | 422 | `expectedOutputRegex 無法編譯` | `{taskId}` |
| 9e | 範圍任務數超過 Bridge 單一 playbook 上限（`PlaybookIn.tasks` ≤ 500） | 422 | `範圍任務數超過單一批次上限 500` | `{count, limit:500}` |
| 10 | Bridge 409 `advisory_lock_held` | 409 | `同專案同路徑已有執行中的批次` | `{holderRunId}` |
| 10 | Bridge 422（消毒／格式） | 422 | `引擎拒絕此請求` | `{bridgeReason, violations[]}`（`violations` 逐項原樣帶出） |
| 10 | Bridge 不可達／逾時／其他 5xx | 502／504／502 | `引擎橋接服務無法連線`／`…逾時`／`引擎橋接服務錯誤` | `{bridgeStatus?, bridgeReason?}` |

第 3～9e 項**不呼叫 Bridge**；第 10 項失敗時，剛建立的 `execution_runs` 列**補償刪除**，專案與任務狀態不動。檢查 5 的順序在 6 之前，所以未 signoff 時即使 ids 有誤也先回 409（與 PRD「不靜默放行」一致）。

- **成功處理**：持專案列鎖取下一個 `run_number` → 寫 `execution_runs`（僅 console 欄位：`id, project_id, run_number, autonomy_level, scope, token_budget, dag, started_at`）並提交 → Bridge `POST /autoclaude/runs` → 201 後：專案轉 `EXECUTING`（`DRAFT`／`FAILED` 先內部轉 `READY` 再轉 `EXECUTING`，同一交易；`COMPLETED` 的專案補了新任務後可再跑，屬系統重設直接 `→EXECUTING`，§3.5.3、§6 D-31；若範圍內已無可執行任務則由第 7c 項擋下）、範圍內任務 `→QUEUED`（狀態重設規則見 §3.5.3）、啟動事件消費者（§3.5.4）。
- **成功 201**：`ApiResult<ExecutionRunResponse>`，`status=RUNNING`、`bridgeStatus=RUNNING`（以 Bridge 201 回的 `status` 為準，不依賴 DB 回讀時機）、`totalTokensUsed=0`。

```json
{ "code":201, "message":"success", "data":{
    "id":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31", "projectId":"0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02",
    "runNumber":1, "status":"RUNNING", "bridgeStatus":"RUNNING", "autonomyLevel":1,
    "scope":{ "mode":"ALL", "goalIds":[], "taskIds":[] },
    "totalTokensUsed":0, "tokenBudget":100000, "startedAt":"2026-10-15T08:30:12Z" },
  "timestamp":"2026-10-15T16:30:12+08:00", "traceId":"…" }
```

#### 1.2.2 `GET /api/v1/projects/{projectId}/executions`　列出執行批次（補）　〔API-EXE-14／US-M-06〕

- **角色**：VIEWER。查詢參數：`page,size`、`status`（`RunStatus`）、`sort`（`startedAt|runNumber`，預設 `startedAt,desc`）。
- **成功 200**：`Page<ExecutionRunSummaryResponse>`。`tasksTotal`＝該批次 `dag` 的 TASK 節點數；`tasksCompleted`／`tasksFailed`＝該批次 `execution_steps` 中有 `COMPLETED`／`FAILED` 列的**相異任務數**；`successRate`＝`tasksCompleted ÷ (tasksCompleted+tasksFailed) × 100`（兩者皆 0 為 null）；`durationSec` 見 schema。
- **錯誤**：400（未知 status／sort）、404 專案、401／429。

#### 1.2.3 `GET /api/v1/executions/{runId}`　查詢執行狀態　〔API-EXE-05／US-E-07、M-10〕

- **角色**：VIEWER。**Bridge**：`GET /autoclaude/runs/{id}`（逾時 3 秒）。
- **成功 200**：`ExecutionRunDetailResponse`＝`ExecutionRunResponse` ＋：

| 欄位 | 來源 | Bridge 不可達時 |
|------|------|-----------------|
| `currentStep{stepId,stepNumber,taskId,taskName,goalId,attempt}` | Bridge `current_step`、`current_step_number`、`attempt` ＋ dag 對映 | `null` |
| `completedSteps`／`totalSteps` | Bridge `completed_steps`／`total_steps` | 由 DB 衍生：`completedSteps`＝該批次有 `COMPLETED` 列的相異任務數；`totalSteps`＝dag 的 TASK 節點數 |
| `lastEventSeq` | Bridge `last_event_seq` | DB 內最大 `step_number` 或 null |
| `reason` | Bridge `reason` | null |
| `elapsedSec` | 進行中＝現在−`startedAt`；終態＝`completedAt`−`startedAt` | 同左 |
| `pendingReviews[]` | `review_requests` 中 `status=PENDING`（依 `requestedAt` 升冪） | 同左（DB） |
| `bridge{connected,instance,status,runKnown,checkedAt}` | 見下 | `connected=false`，`status` 為 null |

- **Bridge 不可達（連線失敗或逾時）時仍回 200**，`bridge.connected=false`，**不回 5xx**（主控裁決）。Bridge 可達但回 404 `run_not_found`（workspace 被清）→ `connected=true`、`runKnown=false`、進度同 DB 衍生。`bridge.instance` 取 Bridge 的 `bridge_instance`；**不外露 pid 與 lock key**。
- **錯誤**：400（id 格式）、404、401／429。

#### 1.2.4～1.2.6 `POST /api/v1/executions/{runId}/pause｜resume｜cancel`　〔API-EXE-02、03、04、11／US-E-04、05、06〕

- **角色**：OPERATOR。無 body。成功 200 `ApiResult<ExecutionRunResponse>`（快照，見本節開頭）。

| 端點 | DB 預檢（失敗 409） | Bridge 呼叫 | 成功後典型回應 | 副作用 |
|------|---------------------|-------------|----------------|--------|
| `pause` | `status=RUNNING`（終態或 PAUSED 直接 409，不呼叫 Bridge） | `:pause` → 202 `PAUSING`（PAUSING 時冪等） | `RUNNING`＋`PAUSING` | 無；`PAUSED` 由 SSE `status-change` 通知。已在最後一步時暫停來不及，run 照常 `COMPLETED` |
| `resume` | `status=PAUSED`；**重驗範圍內專案／目標／任務 `signedOff`**（`未經人工審批的草案不可執行`，details 同 execute 第 5 項） | `:resume` → 202 `RUNNING` | `RUNNING`＋`RUNNING` | 專案回 `EXECUTING` |
| `cancel` | `status∈{RUNNING,PAUSED}` | `:stop` → 202 `CANCELLING` | `RUNNING`＋`CANCELLING`（PAUSED 者即時 `CANCELLED`） | 終態 `CANCELLED` 後：範圍內 `RUNNING`／`QUEUED` 任務→`CANCELLED`、其餘不動；專案→`READY`；`IN_PROGRESS` 目標→`PENDING`（§3.5.3） |

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 404 | （訊息）`執行批次不存在或已刪除：<id>` | | |
| 409 | `目前執行狀態不允許此操作` | `{action:"pause\|resume\|cancel", runStatus, bridgeStatus}` | DB 預檢不符，或 Bridge 409 `invalid_state` |
| 409 | `未經人工審批的草案不可執行` | `{unsignedProjectId,unsignedGoalIds[],unsignedTaskIds[]}` | 僅 resume |
| 409 | `引擎端已無此執行（工作區可能已清除）` | `{runId}` | Bridge 404 `run_not_found` |
| 502／504 | `引擎橋接服務無法連線`／`…逾時`／`引擎橋接服務錯誤` | | DB 狀態不變 |
| 401／403／429 | 通用 | | |

#### 1.2.7 `GET /api/v1/executions/{runId}/steps`　分頁查詢步驟　〔API-EXE-06、SSE-03／US-M-03、09〕

- **角色**：VIEWER。查詢參數：`page`（0 起）、`size`（預設 50、上限 200）、`afterSeq`（≥0，**嚴格大於**）。依 `stepNumber` 升冪。
- **資料來源**：`console.execution_steps`（Bridge 寫；每個 `step` 事件一列，狀態 `STARTED／RETRYING／COMPLETED／FAILED`）。**`stepNumber`＝該 step 事件的 Bridge `seq`**（Bridge 把位置放進 `input`，`step_number` 欄放 seq），所以 `afterSeq` 可直接對 SSE `Last-Event-ID` 的整數部分（Console 自產事件的子序號不影響）。
- **`ExecutionStepResponse` 欄位**：`id, runId, taskId, taskName, goalId, stepNumber, stepId(=input.step_id), attempt(=input.attempt), action("<step_id>: <任務名稱>"), status, tokensUsed, errorMessage, output, timestamp`。`tokensUsed`：**Bridge 不寫 `execution_steps.tokens_used`**，`COMPLETED`／`FAILED` 列由 console-api 以該任務在本批次的 token 歸因（`run_token_samples` 依 `task_id` 加總）回傳，其餘列為 null；`output` 目前恆為 null。
- **REST 回補用法**：SSE 斷線且 `Last-Event-ID` 已過期時，以 `afterSeq=<id 的整數部分>` 迴圈取頁補齊步驟，再重新連 SSE。注意 `steps` 只含步驟事件；引擎原始 `log` 行與告警／審核項需另以 SSE 重播或 `alerts`／`pendingReviews` 取得。
- **錯誤**：400（`afterSeq<0`、`size>200`）、404、401／429。

#### 1.2.8 `GET /api/v1/executions/{runId}/dag`　DAG 圖　〔API-EXE-07、DAG-01／US-E-09〕

- **角色**：VIEWER。成功 200：`DagResponse{runId, nodes[], edges[], statusAsOf}`。
- 節點：`GOAL`（`id`＝目標 id，`sequence`＝目標序）與 `TASK`（`id`＝任務 id，`goalId`，`stepId`，`sequence`＝展平後位置，1 起算，等於 Bridge 的 `step_number`／`current_step_number`）。邊：`DEPENDENCY`（前置目標→依賴者，只含範圍內的目標）與 `CONTAINS`（目標→其任務）。節點／邊在建立批次時凍結於 `execution_runs.dag`；`status` 於讀取時疊加目標與任務的**現況**（歷史批次亦為現況，見 `statusAsOf`；§6 D-38）。
- 錯誤：404、401／429。

#### 1.2.9 `GET /api/v1/executions/{runId}/checkpoints`　斷點列表　〔API-EXE-08／US-E-11〕

- **角色**：VIEWER。成功 200：`List<CheckpointResponse>`（舊→新）。資料來自 `console.checkpoints`（Bridge 於每個步驟完成時自行記錄歷史快照，append-only，命名 `after-<step_id>`）。`stepIdx`／`stepId` 取自 `state_snapshot` 的 `step_idx`／`step_id`（＝**還原後下一個要跑的步驟**；最後一步之後 `stepIdx=總步數`、`stepId=""`）；`completedSteps`＝快照的 `completed_step_ids` 長度。不含 `stateSnapshot` 本體。
- 錯誤：404、401／429。

#### 1.2.10 `POST /api/v1/executions/{runId}/restore/{checkpointId}`　從歷史斷點還原　〔API-EXE-09、11／US-E-11〕

- **角色**：OPERATOR。**Bridge**：`POST /autoclaude/runs/{id}/restore {checkpoint_id}`（202）。語意不同於 resume：restore **必帶** `checkpointId`、時間回退到該還原點。
- **前置**：`checkpointId` 屬於該 run（否則 404）；該 run 是專案**最新**的批次；DB `status∈{PAUSED,COMPLETED,FAILED,CANCELLED}`（`RUNNING`／`INITIALIZING` → 409）；重驗範圍內 `signedOff`；Bridge 還會重取已釋放的鎖（可能 409）並重驗 `execution_path`（TOCTOU，可能 422）。
- **成功 200**：`ExecutionRunResponse` 快照（典型 `RUNNING`＋`RUNNING`）。Bridge 隨後發 `alert`（`code=RESTORE`、level `info`）與 `status RUNNING`。
- **副作用（Bridge 接受後，同一交易）**：依快照的 `completed_step_ids` 把**其餘**範圍內任務重設為 `QUEUED`、受影響目標重設、專案回 `EXECUTING`（§3.5.3）。**restore 沿用該 run 建立時的 playbook**：還原後之前修改的任務內容不會生效；要用新內容請另開批次（`execute`）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 404 | （訊息）`checkpoint 不存在或不屬於此執行：<id>` | | |
| 409 | `目前執行狀態不允許此操作` | `{action:"restore",runStatus,bridgeStatus}` | |
| 409 | `只能還原專案最新的執行批次` | `{latestRunId,latestRunNumber}` | 該 run 不是專案 `run_number` 最大者（避免以過期的 playbook 範圍重跑已被跳過或已完成的任務） |
| 409 | `未經人工審批的草案不可執行` | 同 execute | |
| 409 | `同專案同路徑已有執行中的批次` | `{holderRunId}` | 終態還原時鎖被別的 run 取走 |
| 409 | `引擎端已無此執行（工作區可能已清除）` | | Bridge 404 `run_not_found` |
| 422 | `引擎拒絕此請求` | `{bridgeReason,violations[]}` | `execution_path` 重驗失敗 |
| 502／504 | 通用 | | |

#### 1.2.11 `POST /api/v1/executions/{runId}/review/{stepId}`　審核　〔API-EXE-10、AUT-01～06／US-E-07、08〕

- **角色**：OPERATOR。**路徑的 `{stepId}` 是 `review_requests.id`（UUID），不是 playbook 的 step_id**（主控裁決）。審核人＝JWT subject（`decided_by`）。
- **Request**（`ReviewRequest`）：`{ "decision": "APPROVE|REJECT|RETRY|SKIP", "comment": "≤2000 字元（選填）" }`。
- **成功 204**（無本文）。`SKIP`，以及找不到還原點而改開後續批次的 `RETRY`，會另建後續批次（follow-up run），其 id 放在回應標頭 **`X-Follow-Up-Run-Id`**；其餘決定不出現該標頭。審核項狀態對映：`APPROVE→APPROVED`、`REJECT→REJECTED`、`RETRY→RETRIED`、`SKIP→SKIPPED`，寫入 `decided_by／decided_at／comment`。
- **每個 `kind` 允許的決定與動作**見 §3.6.3（`ReviewRequestResponse.allowedDecisions` 即該表的資料化）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | （Bean Validation） | `errors=[{field:"decision"…}]` | decision 缺漏或不在列舉、comment 過長 |
| 404 | （訊息）`審核項不存在或不屬於此執行：<id>` | | `{stepId}` 查無或其 `run_id` 不符 |
| 409 | `審核項已處理` | `{status,decidedBy,decidedAt}` | 狀態非 `PENDING`（含並發雙擊的後者） |
| 409 | `此審核項不允許該決定` | `{kind,decision,allowedDecisions[]}` | decision 不在 `allowedDecisions` |
| 409 | `目前執行狀態不允許此操作` | `{action:"review",runStatus,bridgeStatus}` | 例：gate 審核項的 `APPROVE` 但 run 已不在 `PAUSED` |
| 409／422／502／504 | 同 execute 第 10 項 | | `SKIP`／`RETRY` 開後續批次或 restore 時 Bridge 回應 |
| 401／403／429 | 通用 | | |

**原子性**：`SKIP`／後續批次先完成「建 run 列＋Bridge 接受」，成功後才提交審核項與任務的狀態變更；任何一步失敗全部回滾，審核項維持 `PENDING`。

---
### 1.3 專案監控（Phase 5）

**共通查詢參數**（`metrics`／`token-trend`／`task-trend`／`logs`／`report`；`alerts` 只用 `runId`）：

| 參數 | 型別 | 預設 | 規則 |
|------|------|------|------|
| `runId` | uuid | 省略＝專案全部批次 | 必須屬於該專案，否則 404（訊息 `執行批次不存在或不屬於此專案：<id>`） |
| `from` | date-time（帶 offset） | `to` 之前 24 小時 | 必須早於 `to`，否則 400 `時間範圍不合法`（`details={from,to}`） |
| `to` | date-time（帶 offset） | 現在 | 視窗上限 366 天，超過同為 400 `時間範圍不合法` |
| `bucket`（僅趨勢） | `HOUR`｜`DAY` | 視窗 ≤ 48 小時用 `HOUR`，否則 `DAY` | 桶以 UTC 為界；視窗內桶數超過 1,000 回 400 `時間範圍不合法`（請改用 `DAY`） |

**Bridge**：監控端點不呼叫 Bridge（資料全來自 DB），唯一例外是 `agentAvailability`（取自 console-api 對 Bridge 的健康探測環，§3.1）。

所有監控端點共通錯誤：404 專案不存在、404 `runId` 不屬於該專案、400（參數格式）、401／429。聚合公式、前一視窗比較與日誌衍生規則統一見 **§3.8**。

#### 1.3.1 `GET /api/v1/monitor/projects/{projectId}/metrics`　〔API-MON-01／US-M-01、M-10〕

- **角色**：VIEWER。成功 200：`ProjectMetricsResponse`。
- **欄位**：十個 `MetricValue{value,previousValue,delta}`——PRD §5.4.2 八項：`projectCompletionRate`（專案完成率，**全域**，不隨 `projectId` 變）、`goalAchievementRate`、`taskSuccessRate`、`averageRetryCount`、`totalTokens`（Token 總消耗）、`tokenBudgetUsageRate`、`averageTaskDurationSec`、`agentAvailability`；加設計稿卡片用的 `taskCompletionRate`（「完成率」＝專案內任務完成進度）與 `retryRate`（「重試率」）。另有 `tokenBudget`、`taskStatusDistribution`（任務十一態現況計數，缺的態為 0 且一律出現）、`taskDurations[]`（視窗內完成的任務，耗時由長到短至多 10 筆）、`retryDistribution[]`（重試 0、1、2、3、4、≥5 次的任務數）。`generatedAt`＝伺服器產生時間。
- 數值無法計算（分母為 0、沒有探測樣本、無預算）時 `value=null`；`previousValue`／`delta` 的 null 規則見 §3.8.1。

```json
{ "code":200, "message":"success", "data":{
    "projectId":"0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02", "runId":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31",
    "from":"2026-10-14T08:40:00Z", "to":"2026-10-15T08:40:00Z", "generatedAt":"2026-10-15T08:40:00Z",
    "taskCompletionRate":{ "value":100.0, "previousValue":0.0, "delta":100.0 },
    "taskSuccessRate":{ "value":100.0, "previousValue":null, "delta":null },
    "retryRate":{ "value":0.0, "previousValue":null, "delta":null },
    "totalTokens":{ "value":3720, "previousValue":0, "delta":3720 },
    "tokenBudgetUsageRate":{ "value":3.7, "previousValue":null, "delta":null },
    "averageRetryCount":{ "value":0.0, "previousValue":null, "delta":null },
    "projectCompletionRate":{ "value":100.0, "previousValue":null, "delta":null },
    "goalAchievementRate":{ "value":100.0, "previousValue":null, "delta":null },
    "averageTaskDurationSec":{ "value":1.8, "previousValue":null, "delta":null },
    "agentAvailability":{ "value":100.0, "previousValue":null, "delta":null },
    "tokenBudget":100000,
    "taskStatusDistribution":{ "PENDING":0,"QUEUED":0,"BLOCKED":0,"RUNNING":0,"VALIDATING":0,"COMPLETED":3,"FAILED":0,"ESCALATED":0,"PAUSED":0,"SKIPPED":0,"CANCELLED":0 },
    "taskDurations":[ { "taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21", "taskName":"初始化", "goalName":"基礎", "durationSec":1.9 } ],
    "retryDistribution":[ { "retries":0, "tasks":3 } ] },
  "timestamp":"2026-10-15T16:40:00+08:00", "traceId":"…" }
```

#### 1.3.2 `GET …/token-trend`　〔API-MON-02／US-M-02〕

- **角色**：VIEWER。成功 200：`List<TokenTrendPoint>{bucketStart,tokens,cumulativeTokens,budget}`（依 `bucketStart` 升冪）。來源 `console.run_token_samples`（§0.5）：`tokens`＝桶內 `delta` 之和、`cumulativeTokens`＝自視窗起點累計；沒有資料的桶不補零；`budget`＝所屬批次的 `tokenBudget`（多批次取視窗內最新批次；無預算為 null）。

#### 1.3.3 `GET …/task-trend`　〔API-MON-03／US-M-03〕

- **角色**：VIEWER。成功 200：`List<TaskTrendPoint>{bucketStart,started,completed,failed,retried}`。來源 `execution_steps`：桶內 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 列的筆數。成功／失敗比率由前端以 `completed`、`failed` 計算。

#### 1.3.4 `GET …/alerts`　〔API-MON-04、ALR-01～06／US-M-05〕

- **角色**：VIEWER。查詢參數：`runId`、`acknowledged`（`true`／`false`／省略）、`limit`（1～200，預設 50）。成功 200：`List<AlertResponse>`（`createdAt` 由新到舊）。
- `rule` 值域＝PRD 六條規則＋`ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`；各規則的判定與訊息樣板見 §3.7。

#### 1.3.5 `POST /api/v1/monitor/alerts/{alertId}/acknowledge`　〔API-MON-05／US-M-05〕

- **角色**：OPERATOR。無 body。成功 **204**。**冪等**：已確認者再次呼叫仍 204，且不改寫第一次的 `acknowledgedBy／At`。404（訊息 `告警不存在：<id>`）、400（id 格式）、401／403／429。確認後同一規則＋對象可再產生新告警。

#### 1.3.6 `GET …/logs`　〔API-MON-06／US-M-04〕

- **角色**：VIEWER。額外查詢參數：`level`（`ALL|INFO|WARN|ERROR`，預設 `ALL`）、`taskId`（uuid）、`q`（訊息關鍵字，不分大小寫，`%`／`_` 視為字面，≤200）、`order`（`asc|desc`，預設 `desc`）、`page`、`size`（預設 50、上限 200）。
- 成功 200：`Page<LogEntryResponse{id,timestamp,level,source,message,runId,taskId,stepId}>`。日誌**由既有資料衍生，不新增日誌表**，且**不含引擎原始 stdout**（原始行只在 SSE `log` 事件，`source=ENGINE`）；衍生規則見 §3.8.3。
- 錯誤：400（level／order／size 不合法、時間範圍）、404、401／429。

#### 1.3.7 `GET …/report?format=csv|pdf`　〔API-MON-07／US-M-07〕

- **角色**：VIEWER。查詢參數：`format`（`csv|pdf`，預設 `csv`）、`runId`、`from`、`to`。**不包 ApiResult 封包**。呼叫端須送 `Accept: text/csv`（或 `*/*`）。
- **CSV（必做）**：`Content-Type: text/csv; charset=UTF-8`；`Content-Disposition: attachment; filename="monitor-report-<projectId 前 8 碼>-<yyyyMMdd-HHmm>.csv"`（時間為 UTC）；UTF-8 含 BOM、行尾 CRLF、欄位依 RFC 4180 引號跳脫；**CSV 注入防護**：任何以 `=`、`+`、`-`、`@` 開頭的文字欄位在前面補一個單引號 `'`。內容為連續的區段，每段以 `#section,<名稱>` 行起頭、下一行是欄名、之後是資料列、段與段之間空一行：

```
#report,<專案名稱>,<from>,<to>,<runId 或 ALL>
#section,summary
metric,value,previousValue,delta,unit
taskCompletionRate,100.0,0.0,100.0,PERCENT
…（十個 KPI，順序同 §1.3.1；null 輸出空字串；unit ∈ PERCENT|COUNT|SECONDS|TOKENS）

#section,runs
runNumber,runId,status,autonomyLevel,startedAt,completedAt,durationSec,totalTokensUsed,tokenBudget,tasksTotal,tasksCompleted,tasksFailed

#section,tasks
goalName,taskName,status,retryCount,maxRetries,actualTokens,startedAt,completedAt,durationSec

#section,alerts
createdAt,severity,rule,subject,message,acknowledged,acknowledgedBy,acknowledgedAt
```

- **PDF**：目標格式為同樣四段內容的 `application/pdf`（openhtmltopdf），**W5 之前一律回 501**，reason `PDF 報表尚未提供（W5）`。
- 錯誤：400 `不支援的報表格式`（`details={format,supported:["csv","pdf"]}`）、400 `時間範圍不合法`、404、501、401／429。

### 1.4 通知

#### 1.4.1 `GET /api/v1/notifications/summary`（補）　〔API-NTF-01／US-E-07〕

- **角色**：VIEWER。成功 200：`NotificationSummaryResponse{pendingSignoffs, pendingReviews, unacknowledgedAlerts, bridgeConnected, bridgeCheckedAt}`，前三者為跨專案的整數：
  - `pendingSignoffs`＝`projects`、`goals`、`tasks` 三表中 `signed_off=false` 且未軟刪者（目標與任務所屬的專案、目標也須未軟刪）＋ `import_records` 中 `status∈{PARSED,REVIEWING}` 且 `signed_off=false` 者。每個待簽核的列算一次（執行閘要求三層全簽，每一列都是一次待做的 signoff）；`UPLOADED`／`PARSING` 的匯入記錄尚無可簽核內容，不計（§6 D-46）；
  - `pendingReviews`＝`review_requests.status='PENDING'` 總數；
  - `unacknowledgedAlerts`＝`alerts.acknowledged=false` 總數；
  - `bridgeConnected`／`bridgeCheckedAt`＝最近一次 Bridge 健康探測（每 30 秒，`GET {autoclaude.healthCheckPath}`，逾時 3 秒）的結果與時間；從未探測為 null。供頂列「Engine Bridge · 已連線」綠點（設計稿全域元素；`/actuator/health` 只代表 console-api 自己）。
- 供頂列通知鈴與 signoff 佇列徽章輪詢（建議間隔＝`monitor.refreshIntervalMs`，不得小於 3 秒）；401／429。

### 1.5 系統參數（Phase 6）

**Bridge**：設定端點不呼叫 Bridge（`test-connection` 是 console-api 直連模型端點，不經 Bridge）；參數經 `ConfigMaterializer` 在**執行時**才物化給 Bridge（§3.4.2）。**每個鍵的型別、預設、驗證、範圍、選項、影響提示與引擎效果＝附錄 C（唯一真相源）**。以下通則：

- `value` 一律是字串：`INTEGER`／`LONG`＝`^(0|-?[1-9][0-9]*)$`；`FLOAT`＝`^-?[0-9]+(\.[0-9]+)?$`；`BOOLEAN`＝小寫 `true`／`false`；`ENUM`＝選項之一（區分大小寫）；`STRING`＝不含 NUL、≤ 4,000 字元；`ENCRYPTED`＝非空 ≤ 512 字元，或空字串表示清除。
- 加密參數（`is_encrypted=true`：`model.apiKey`、`autoclaude.dbDsn`）以 AES-256-GCM 儲存（金鑰 `CONSOLE_ENCRYPTION_KEY`，base64 的 32 bytes；缺少或長度不對＝**啟動失敗**）；GET 一律回遮罩字串 `••••••••`（U+2022 共八個）＋`hasValue`；歷史與匯出同樣遮罩；明文只在 `reveal=true`（ADMIN）時回傳，且每次揭露寫審計日誌（只記分類與次數，不記值）。
- 每次成功寫入都寫一筆 `system_config_history`（加密參數的新舊值一律存遮罩標記，不存明文或密文）。

#### 1.5.1 `GET /api/v1/settings`　〔API-SET-01／US-S-01、04、08〕

- **角色**：VIEWER；`reveal=true` 需 ADMIN（其他角色 403，reason `僅 ADMIN 可揭露敏感參數`）。成功 200：`Map<category, List<ConfigResponse>>`，分類順序 `model,agent,execution,monitor,autoclaude,sdd`，分類內依附錄 C 順序。
- `ConfigResponse`：`id, category, key, value, valueType, defaultValue, description, isEncrypted, hasValue, validationRule, options, min, max, impactNote, effect, updatedAt, updatedBy`（`options`／`min`／`max`／`effect` 來自附錄 C 的 `ConfigCatalog`，`impactNote` 讀 `system_configs.impact_note`（V5 依附錄 C 寫入，§0.5）；`effect∈ENGINE|CONSOLE|STORED_ONLY|UNVERIFIED`，誠實標示該參數是否真的影響引擎）。

#### 1.5.2 `GET /api/v1/settings/{category}`　〔API-SET-02〕

- 同 1.5.1，只回一個分類（`List<ConfigResponse>`）；分類不在六個之內 → 404（訊息 `設定分類不存在：<category>`）。

#### 1.5.3 `PUT /api/v1/settings/{category}/{key}`　〔API-SET-03、10／US-S-02、08〕

- **角色**：ADMIN。**Request**（`UpdateConfigRequest`）：`{ "value": "<字串>", "confirm": true|false(選填) }`。
- **驗證順序**：

| # | 檢查 | HTTP | reason | details |
|---|------|------|--------|---------|
| 1 | 鍵存在 | 404 | （訊息）`設定鍵不存在：<category>.<key>` | — |
| 2 | 型別、`validationRule`、`min`／`max`、`options` | 400 | `參數值不符合型別或驗證規則` | `errors=[{field:"value",message:"需為整數（1～10）"}]`；`details={valueType,validationRule,min,max,options}` |
| 3 | `model.apiUrl`：SEC-04（scheme／userinfo／IP 字面類別／allowlist，**不做 DNS**） | 400 | `目標位址未通過 SSRF／allowlist 檢查` | `{host,violation}` |
| 4 | token_guard 單鍵：讀對端鍵現值，`halt > compact` 且各自在範圍內 | 400 | `halt_threshold_pct 必須大於 compact_threshold_pct` | `{compactThresholdPct,haltThresholdPct}`（以更新後的值為準） |
| 5 | 加密鍵未帶 `confirm=true` | 409 | `敏感參數更新需二次確認（confirm=true）` | `{category,key}` |

- **成功 200**：`ConfigResponse`（加密值遮罩）。值未變更（與現值相同）仍回 200，但**不寫歷史**。
- 錯誤另有 401／403（非 ADMIN）／429。

#### 1.5.4 `PUT /api/v1/settings/execution/token-guard`　〔API-SET-04／NFR-SEC-05〕

- **角色**：ADMIN。**Request**（`TokenGuardRequest`）：`{ "compactThresholdPct": 70, "haltThresholdPct": 95 }`（皆整數；`compact` 1～99、`halt` 2～100）。同一交易內校驗並寫兩個鍵。
- **成功 200**：`List<ConfigResponse>`（`compactThresholdPct`、`haltThresholdPct` 兩筆）；各寫一筆歷史（值未變者不寫）。
- **錯誤**：400 `halt_threshold_pct 必須大於 compact_threshold_pct`（`halt <= compact`，含相等；`errors=[{field:"haltThresholdPct",message:"必須大於 compactThresholdPct"}]`、`details={compactThresholdPct,haltThresholdPct}`）；400 Bean Validation（缺欄位、非整數、超出範圍；`errors[]`，reason 省略）；401／403／429。**任何失敗都不改任何一個鍵**。

#### 1.5.5 `POST /api/v1/settings/{category}/{key}/reset`　〔API-SET-05／US-S-03〕

- **角色**：ADMIN。查詢參數 `confirm`（布林，預設 false）。把 `value` 設回 `default_value` 並寫歷史。
- **錯誤**：404；409 `敏感參數重置需二次確認（confirm=true）`（加密鍵未帶 `confirm=true`）；400 `halt_threshold_pct 必須大於 compact_threshold_pct`（重置單一 token_guard 鍵後違反跨鍵約束，例如 halt 目前 75 時重置 compact→80）；401／403／429。
- **成功 200**：`ConfigResponse`。

#### 1.5.6 `POST /api/v1/settings/{category}/reset`（補）　〔API-SET-05／US-S-03〕

- **角色**：ADMIN。設計稿底部「全部重置為預設值」。查詢參數 `confirm`。同一交易內逐鍵重置並各寫歷史；**加密鍵預設略過**（要連同重置須 `confirm=true`）；token_guard 以重置後的最終值做跨鍵校驗，不滿足 → 400（同上 reason，且整批不套用）。
- **成功 200**：`List<ConfigResponse>`（該分類全部鍵的最新狀態）；404 分類不存在。

#### 1.5.7 `POST /api/v1/settings/test-connection`　〔API-SET-06／US-S-05／NFR-SEC-04〕

- **角色**：ADMIN。**Request**（選填；`TestConnectionRequest`）：`{ "apiUrl"?, "apiKey"?(僅寫入、不回顯), "model"? }`；省略的欄位取已儲存的 `model.apiUrl`／`model.apiKey`／`model.name`。金鑰**不寫日誌、不回顯**。
- **檢查順序（任一不過 → 422，且未發出任何連線）**：

| # | 規則 | `details.violation` |
|---|------|---------------------|
| 1 | URL 可解析；無空白／控制字元／反斜線；連接埠合法；**IP 字面必須是標準寫法**（IPv4 點分十進位四段、IPv6 標準寫法）——十進位整數、十六進位、八進位、縮寫（如 `127.1`）一律拒絕 | `malformed_url` |
| 2 | scheme 只能 `http`／`https` | `scheme` |
| 3 | 不得含 userinfo（`user:pw@`） | `userinfo` |
| 4 | host 為 **IP 字面**（已過 1 的標準寫法）時分類：`127.0.0.0/8`、`::1`→`loopback`；`169.254.0.0/16`（含 `169.254.169.254`）、`fe80::/10`→`link_local`；`10/8`、`172.16/12`、`192.168/16`、`fc00::/7`、`100.64/10`、`0.0.0.0/8` 等→`private_ip`。**只有 `loopback` 類、且該字面完全等於 allowlist 某項時放行**；`link_local`、`private_ip` 即使列在 allowlist 也一律拒絕 | `loopback`／`link_local`／`private_ip` |
| 5 | host（小寫、去尾端 `.`、IDN 轉 punycode）必須與 `console.security.outbound-allowlist` 的某項**完全相等** | `not_in_allowlist` |
| 6 | DNS 解析所有 A／AAAA：任一位址落在 `link_local`／`private_ip` 類 → 拒絕（名稱解析到內網＝DNS rebinding 型態，即使該名稱在 allowlist 內）；解析到 `loopback` 類位址 → 拒絕，**除非 host 就是 `localhost`**（已過 5，即 allowlist 內有它） | `dns_rebinding` |

  預設 allowlist（production）：`api.anthropic.com,api.openai.com,api.minimax.io,api.minimax.chat`；e2e／本機 profile 另加 `127.0.0.1,localhost`（loopback 在 allowlist 內才放行，沒有額外的開關；§6 D-47）。通過 1～6 後：**連線釘死在已驗證的 IP**（以原 host 作 `Host` 標頭與 TLS 主機名驗證），**不自動跟隨 redirect**。
- **探測請求**：`GET <scheme>://<host>[:<port>]/v1/models`（只取 origin，丟棄原路徑），標頭 `Authorization: Bearer <apiKey>`（無金鑰則不帶）、`Accept: application/json`、`User-Agent: aisdlc-console`；總逾時 `min(model.timeout, 10)` 秒、連線逾時 5 秒。
- **成功 200**（只要實際嘗試過連線，成功或失敗都是 200）：`ConnectionTestResponse{success,latencyMs,message,resolvedHost,httpStatus}`：

| 結果 | `success` | `message` |
|------|-----------|-----------|
| HTTP 2xx | true | `連線成功` |
| HTTP 401／403 | false | `認證失敗（HTTP 401）` |
| HTTP 404／405 | false | `端點不支援模型列表探測（HTTP 404）` |
| 3xx | false | `目標回應重新導向，已拒絕跟隨（HTTP 302）` |
| 其他 4xx／5xx | false | `服務回應錯誤（HTTP 503）` |
| 逾時 | false | `連線逾時（<N> 秒）` |
| 拒絕連線／其他 I/O | false | `無法連線：<簡短原因>` |

  `latencyMs`＝送出請求到收到回應標頭的毫秒數（無回應為 null）；`resolvedHost`＝URL 的 host（小寫）。
- **422**：`目標位址未通過 SSRF／allowlist 檢查`，`details={host,violation}`（無連線）。每次呼叫（含被拒）寫審計：`settings.testConnection`＋host＋結果，絕不記金鑰與 userinfo。
- 另：400（body 格式）、401／403／429。

#### 1.5.8 `GET /api/v1/settings/history`　〔API-SET-07／US-S-07〕

- **角色**：VIEWER。查詢參數：`category`、`key`（需與 `category` 併用，單獨給 `key` → 400）、`page`、`size`（預設 20、上限 100）。成功 200：`Page<ConfigHistoryResponse{id,configId,category,key,oldValue,newValue,changedAt,changedBy}>`（`changedAt` 由新到舊；加密參數兩個值一律 `••••••••`）。

#### 1.5.9 `POST /api/v1/settings/export`　〔API-SET-08／US-S-06〕

- **角色**：ADMIN。**不包 ApiResult**，直接回 `application/json` 檔：`Content-Disposition: attachment; filename="aisdlc-settings-<yyyyMMdd>.json"`。

```json
{ "version":1, "exportedAt":"2026-10-15T08:45:00Z",
  "configs":[ { "category":"model","key":"apiUrl","value":"https://api.anthropic.com" },
              { "category":"model","key":"apiKey","value":"<encrypted>" } ] }
```

- 全部 50 個鍵都輸出；加密參數的 `value` 固定為字串 `<encrypted>`（W3 任務書的作法；偏離 Architecture「不含敏感值」只是形式，§6 D-24）。

#### 1.5.10 `POST /api/v1/settings/import`　〔API-SET-09／US-S-06／NFR-SEC-05〕

- **角色**：ADMIN。`multipart/form-data`，欄位 `file`（≤ 1 MB；內容為 `version=1` 的 `SettingsExportDocument`）。
- **處理**：逐筆驗證（型別／規則／範圍／選項／SEC-04 allowlist，同 1.5.3 的 2、3）；值為 `<encrypted>` 的項目**略過**（計入 `skipped`）；值與現值相同者亦計 `skipped`；未知的 `category.key` 計入 `errors`（`reason:"設定鍵不存在"`）。通過者在**同一交易**套用並各寫歷史。token_guard 兩鍵以**合併後的最終值**做 `halt > compact` 跨鍵校驗，不滿足則兩鍵皆列入 `errors`（`reason:"halt_threshold_pct 必須大於 compact_threshold_pct"`）且都不套用。
- **成功 200**：`ImportSettingsResponse{applied,skipped,errors:[{category,key,reason}]}`（部分失敗仍是 200）。

| HTTP | reason | details | 觸發 |
|------|--------|---------|------|
| 400 | `設定檔格式錯誤` | `{problem:"invalid_json\|missing_configs\|unsupported_version"}` | 不是 JSON／缺 `configs`／`version≠1` |
| 413 | `設定檔超過 1MB 上限` | `{limitBytes:1048576}` | |
| 415 | `只接受 JSON 設定檔` | | 非 `.json` 或非 JSON 內容型別 |
| 401／403／429 | 通用 | | |

---
## 2. SSE 契約（`API-SSE-01～03`／`US-E-03、07`）

兩個端點：`GET /api/v1/stream/executions/{runId}/logs`（事件 `log`、`status-change`、`review-request`、`alert`）與 `GET /api/v1/stream/executions/{runId}/metrics`（事件 `metric-update`、`token-update`、`progress-update`）。console-api 的 `RunEventConsumer`（每個活躍 run 一條虛擬執行緒）讀 Bridge `GET /autoclaude/runs/{id}/stream?after=<seq>`，更新讀模型並扇出給前端訂閱者；Bridge 的 `seq` 是整個鏈路的序號基礎（Bridge 事件單調連續、重啟後延續，已由其測試鎖定）。

### 2.1 連線、認證與框架

| 項目 | 契約 |
|------|------|
| 角色 | VIEWER 以上 |
| 認證 | `Authorization: Bearer <access token>` 與 `?access_token=<access token>` **兩者皆收**（EventSource 不能帶標頭）；標頭優先；只收 access token（refresh token 一律 401）。無效／過期 → **401 JSON**（`UNAUTHENTICATED`／`TOKEN_EXPIRED`／`TOKEN_INVALID`，在串流開始前回；已開始的串流若 token 在中途過期**不中斷**，下次重連才驗） |
| 查無 run | 404 JSON（訊息 `執行批次不存在或已刪除：<id>`） |
| 回應標頭 | `Content-Type: text/event-stream;charset=UTF-8`、`Cache-Control: no-cache, no-store`、`X-Accel-Buffering: no` |
| 框架 | 第一個框架 `retry: 3000`＋空行；之後每個事件三行＋空行：`id: <id>`、`event: <名稱>`、`data: <單行 JSON>`；`data` 為 UTF-8、不含換行（`ensure_ascii=false` 的緊湊 JSON） |
| keep-alive | 連續 **15 秒**沒有任何事件就送一行註解 `: keep-alive` 加空行（任何事件都重置計時） |
| 順序 | 依 `(seq, sub)` 升冪送出；Bridge 事件的 `sub` 視為 0 |
| 慢速訂閱者 | 每個連線有 1,000 個框架的送出佇列；佇列滿＝伺服器主動關閉該連線，客戶端以 `Last-Event-ID` 重連即補齊（不丟事件） |
| 代理 | nginx 對 `/api/v1/stream/` 須 `proxy_buffering off`、`proxy_read_timeout ≥ 3600s`、`proxy_http_version 1.1` |

### 2.2 `id:` 規則

- **Bridge 事件**：`id` ＝ Bridge `seq`（正整數，例 `41`）。
- **console-api 自產的事件**（`review-request`、Console 規則產生的 `alert`，以及 `/metrics` 的 `metric-update`）：`id` ＝ `<seq>.<n>`，其中 `<seq>` ＝建立當下**已處理到的最後一則 Bridge 事件 seq**（錨點；尚未處理任何事件時為 `0`），`<n>` ≥ 1。同一個錨點下 `n` 依建立順序遞增。
- **比較**：把 id 解析成數對 `(seq, n)`（無小數點者 `n=0`）做字典序比較。因此 `41` < `41.1` < `41.2` < `42`。
- **子序號配置**：`/logs` 串流的 `n` ＝「同 run 同錨點下，`review_requests` 與 `alerts` 兩表中 `event_sub` 的最大值＋1」（交易內計算，錨點與子序號寫入該列的 `event_seq`／`event_sub`，§0.5）。`/metrics` 的 `n` 固定規則：`token-update`／`progress-update` 用 `<seq>`，隨之的 `metric-update` 用 `<seq>.1`。
- **連線層的暫態告警**（`BRIDGE_UNREACHABLE`、`BRIDGE_RUN_UNKNOWN`，不持久化）**不帶 `id:` 行**（SSE 允許省略；瀏覽器的 last event id 不變），避免它與日後才配置的子序號撞號而被客戶端去重誤丟。
- **Bridge 告警事件的持久化鏡像**（ESCALATION／TOKEN_HALT 寫入 `alerts`）`event_sub=0`，**SSE 重播時不從 DB 再送一次**（Bridge 事件本身就會重播）。

### 2.3 `Last-Event-ID` 重播語意（at-least-once）

1. 連線時帶 `Last-Event-ID: <id>`（瀏覽器 EventSource 重連時自動帶；fetch 串流自行帶）→ 伺服器重播所有 `(seq, n)` **嚴格大於**該值的事件，再接即時事件。格式不合（不符 `^[0-9]+(\.[0-9]+)?$`）視為沒有帶，不回 400。
2. **`/logs` 重播來源**：Bridge 事件取自 Bridge `GET /autoclaude/runs/{id}/events?after=<seq>&limit=500`（逐頁；Bridge 記憶體環 5,000 則，更舊的自動掃 `events.jsonl`，所以任何歷史位置都可重播，Bridge 重啟後亦然）再套用 §2.7 的對映；Console 自產事件取自 `review_requests`／`alerts`（依 `event_seq`／`event_sub`，且 `event_sub ≥ 1`）。兩者合併後依 `(seq, n)` 排序。
3. **沒有 `Last-Event-ID` 時**（新開頁面）：`/logs` 先重播最後 `tail` 則事件（查詢參數，預設 200，0＝只收之後的新事件，上限 5,000）再接即時；`/metrics` 見 2.5。
4. **客戶端必須去重**：at-least-once 表示可能重複；客戶端記住已處理的最大 `(seq, n)`，小於等於者忽略。
5. **Bridge 暫時不可達**：串流**不關閉**，持續送 keep-alive，並送一則 `alert`（`origin=CONSOLE`、`code=BRIDGE_UNREACHABLE`、`severity=WARNING`、不持久化、同一次中斷只送一次）；每 5 秒重試，恢復後自動補齊。Bridge 回 404 `run_not_found` 則送一則 `alert`（`code=BRIDGE_RUN_UNKNOWN`、`WARNING`）後關閉。
6. **REST 回補**（不能或不想重播時）：`GET /executions/{runId}/steps?afterSeq=<id 整數部分>` 補步驟；`GET /executions/{runId}`（`pendingReviews`）補審核項；`GET …/alerts` 補告警。引擎原始 `log` 行無 REST 回補（只在 SSE 與 Bridge 的 events）。

### 2.4 終態、暫停與關閉

- `PAUSED` **不結束**串流（run 仍持鎖、可 resume）；`PAUSING`／`CANCELLING` 同。
- run 進入終態（`COMPLETED`／`FAILED`／`CANCELLED`）：先送該 `status-change`，再送完它之後衍生的事件（例如終態時才建立的 `review-request`），然後**關閉連線**。
- **重連一個已終態的 run**：`/logs` 若重播集合為空 → **HTTP 204**（EventSource 收到 204 不再重連；fetch 客戶端視為串流結束）；不為空 → 送完重播後關閉。`/metrics` 若帶的 `Last-Event-ID` 已 ≥ 終態事件 id → 204，否則送最終快照後關閉。
- **restore 會讓終態 run 重新變回 `RUNNING`**：呼叫 restore 的客戶端須在 restore 回應之後**重新連線**（原連線早已因終態關閉）。

### 2.5 `/logs` 的事件

所有事件的 `data` 都含 `seq`（錨點或 Bridge seq，整數）與 `ts`（ISO-8601 帶 offset）。

#### `log`

`LogEventData`：`{ seq, ts, source, level, message, stepId?, stepNumber?, taskId?, taskName?, goalId?, attempt?, stepStatus?, tokensUsed? }`

| 欄位 | 說明 |
|------|------|
| `source` | `ENGINE`＝Bridge `log` 事件（引擎 stdout 一行，`message` 為原行，單則上限 8,000 字元由 Bridge 截斷並附註）；`STEP`＝由 Bridge `step` 事件衍生的摘要行 |
| `level` | `DEBUG`｜`INFO`｜`WARN`｜`ERROR`｜`CRITICAL`；ENGINE 取 Bridge `level`（`WARNING`→`WARN`）；STEP：`STARTED`／`COMPLETED`→`INFO`、`RETRYING`→`WARN`、`FAILED`→`ERROR` |
| `message`（STEP） | `STARTED` `開始：<任務名>（<stepId>，第 <attempt> 次）`；`RETRYING` `重試：<任務名>（<stepId>，第 <attempt> 次）`；`COMPLETED` `完成：<任務名>（<stepId>）`＋（有值時）` Token: <n>`；`FAILED` `失敗：<任務名>（<stepId>，第 <attempt> 次）：<errorMessage>` |
| `stepId`／`stepNumber`／`taskId`／`taskName`／`goalId`／`attempt`／`stepStatus` | STEP 一律帶（`stepNumber`＝步驟位置，1 起）；ENGINE 行若消費者已知目前步驟則帶 `stepId`／`taskId`，否則省略 |
| `tokensUsed` | 只有 STEP 的 `COMPLETED` 帶：該任務在本批次累計的 Token（歸因規則 §3.5.2） |

```
id: 17
event: log
data: {"seq":17,"ts":"2026-10-15T08:30:13.482+00:00","source":"STEP","level":"INFO","message":"開始：初始化（G1-T1，第 1 次）","stepId":"G1-T1","stepNumber":1,"taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21","taskName":"初始化","goalId":"a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11","attempt":1,"stepStatus":"STARTED"}
```

#### `status-change`

`StatusChangeEventData`：`{ seq, ts, runStatus, bridgeStatus, reason }`。`runStatus` 為六態折疊值，`bridgeStatus` 為 Bridge 原值（`PAUSING`／`CANCELLING` 在此可見），`reason` 為 Bridge `reason` 原文（例 `在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）`、`引擎升級（ESCALATION）：…`）。每次 Bridge `status` 事件都送一則（含 `INITIALIZING`）。

```
id: 41
event: status-change
data: {"seq":41,"ts":"2026-10-15T08:30:20.101+00:00","runStatus":"PAUSED","bridgeStatus":"PAUSED","reason":"在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）"}
```

#### `review-request`

`ReviewRequestEventData`：`{ seq, sub, ts, review }`，`review` 為完整 `ReviewRequestResponse`（含 `allowedDecisions`）。`id` ＝ `<seq>.<sub>`（`sub ≥ 1`）。審核項建立時機見 §3.6；導覽列 Badge 以 `GET /notifications/summary` 為準，這個事件只用來即時刷新。

```
id: 41.1
event: review-request
data: {"seq":41,"sub":1,"ts":"2026-10-15T08:30:20.140+00:00","review":{"id":"f0b1c2d3-e4f5-4a6b-8c7d-9e0f1a2b3c41","runId":"e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31","kind":"TASK_CONFIRM","status":"PENDING","taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c22","goalId":"a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11","taskName":"設定","goalName":"基礎","reason":"Level 1：請確認是否繼續執行任務「設定」","requestedAt":"2026-10-15T08:30:20Z","allowedDecisions":["APPROVE","REJECT"]}}
```

#### `alert`

`AlertEventData`：`{ seq, sub?, ts, origin, alertId?, rule?, code?, severity, subject?, message, stepId? }`。

| `origin` | id | 內容 |
|----------|----|------|
| `ENGINE` | `<seq>`（Bridge `alert` 事件） | `code`＝Bridge 的 `code`（`ESCALATION`、`TOKEN_HALT`、`LIMIT_RETRY`、`RESTORE`、`FORCE_KILL`、`CONFIG_OVERRIDE_IGNORED`、`STEP_TRACKING_GAP`、`ENV_LOST`、`BRIDGE_INTERNAL`…）；`severity`：`info→INFO`、`warning→WARNING`、`error→CRITICAL`；只有 `ESCALATION`、`TOKEN_HALT` 會持久化（規則 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`）；該事件**新增了一列**才帶 `alertId`／`rule`，被 §3.7 的「未確認前不重複產生」擋下者不帶（SSE 照常轉發） |
| `CONSOLE` | `<seq>.<sub>` | 六條 PRD 規則（§3.7）產生並持久化的告警，帶 `alertId`、`rule`、`subject`；或不持久化、**不帶 `id:` 行**的連線告警（`code=BRIDGE_UNREACHABLE`／`BRIDGE_RUN_UNKNOWN`；其 `seq` 為目前錨點、無 `sub`） |

### 2.6 `/metrics` 的事件（三者皆為狀態快照，latest-wins）

- **收斂重播**：不重播歷史；每次連線（不論有無 `Last-Event-ID`）伺服器**先各送一則最新快照**（`progress-update` 與 `token-update` 的 id ＝目前最後處理的 Bridge seq，`metric-update` 的 id ＝該 seq ＋ `.1`），再接即時事件。這與「從 `Last-Event-ID` 之後重播」在語意上等價，因為客戶端只需要最新狀態（§6 D-32）。
- 事件與觸發：

| Bridge 事件 | 送出 | id |
|-------------|------|----|
| `status`（任何值） | `progress-update` | `<seq>` |
| 終態 `status` | `progress-update`，再一則最終 `metric-update` | `<seq>`、`<seq>.1` |
| `step` `STARTED`／`RETRYING` | `progress-update` | `<seq>` |
| `step` `COMPLETED`／`FAILED` | `progress-update`，再 `metric-update` | `<seq>`、`<seq>.1` |
| `token` | `token-update`，再 `metric-update` | `<seq>`、`<seq>.1` |
| `log`、`alert` | —（這個串流不送） | |

| 事件 | `data` 欄位 |
|------|-------------|
| `progress-update`（`ProgressUpdateEventData`） | `seq, ts, runStatus, bridgeStatus, completedSteps, totalSteps, progressPct(=completedSteps÷totalSteps×100，小數 1 位), currentStep?{stepId,stepNumber,taskId,taskName,goalId,attempt}` |
| `token-update`（`TokenUpdateEventData`） | `seq, ts, tokensUsed(本批次累計，＝Bridge token 事件的 tokens_used), delta(與前一則的差；第一則＝tokensUsed), contextPct(引擎回報的 context 視窗使用%，不是預算%), tokenBudget?, budgetUsageRate?(=tokensUsed÷tokenBudget×100，小數 1 位), taskId?(增量歸因的任務)` |
| `metric-update`（`MetricUpdateEventData`） | `seq, sub, ts, completedTasks, failedTasks, totalTasks, retriedTasks, averageRetryCount, totalTokensUsed, tokenBudgetUsageRate?, elapsedSec`（範圍＝本批次；公式同 §3.8.1 的批次層級） |

```
id: 36
event: token-update
data: {"seq":36,"ts":"2026-10-15T08:30:14.020+00:00","tokensUsed":1240,"delta":1240,"contextPct":0.6,"tokenBudget":100000,"budgetUsageRate":1.2,"taskId":"c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21"}

id: 36.1
event: metric-update
data: {"seq":36,"sub":1,"ts":"2026-10-15T08:30:14.020+00:00","completedTasks":0,"failedTasks":0,"totalTasks":3,"retriedTasks":0,"averageRetryCount":0.0,"totalTokensUsed":1240,"tokenBudgetUsageRate":1.2,"elapsedSec":2}
```

### 2.7 Bridge 事件 → Console SSE 對映（逐事件）

Bridge 的 `data` 是扁平封包 `{seq, ts, …}`（事件名在 `event:` 行；`review-request` 事件 Bridge **從不發送**）。

| Bridge `event:` 與 `data` 欄位 | `/logs` | `/metrics` |
|-------------------------------|---------|------------|
| `log` `{level,line}` | `log`（`source=ENGINE`），id `<seq>` | — |
| `status` `{status,reason}`（8 態） | `status-change`，id `<seq>` | `progress-update`（＋終態時 `metric-update`） |
| `step` `{step_id,step_number,status,attempt,name,total_steps}`（`status`∈`STARTED／RETRYING／COMPLETED／FAILED`） | `log`（`source=STEP`），id `<seq>` | `progress-update`（`COMPLETED`／`FAILED` 另加 `metric-update`） |
| `token` `{pct,tokens_used}` | — | `token-update`＋`metric-update` |
| `alert` `{level,code,message,step_id?}` | `alert`（`origin=ENGINE`），id `<seq>` | — |
| （Console 自產）`review_requests` 新列 | `review-request`，id `<seq>.<sub>` | — |
| （Console 自產）規則告警 | `alert`（`origin=CONSOLE`），id `<seq>.<sub>` | — |

### 2.8 客戶端建議流程

1. 頁面載入：`GET /executions/{runId}`（狀態、進度、`pendingReviews`）＋`GET …/dag`＋（可選）`GET …/steps` 取步驟歷史；再開 SSE。
2. 開 SSE：優先用 fetch 串流並帶 `Authorization: Bearer`（可控制 `Last-Event-ID`、避免 token 進 URL）；使用瀏覽器 `EventSource` 時改用 `?access_token=`。
3. 收到事件：依 `event` 更新 UI，並記錄最大 `(seq, n)` 去重。
4. 斷線：自動重連並帶 `Last-Event-ID`；連續失敗兩次以上，退回 REST 回補（2.3 第 6 點）後再連。
5. 收到 `status-change` 且 `runStatus` 為終態：不再重連；若收到 204 同樣停止。restore 後主動重新連線。
6. 前端「SSE 串流」狀態點＝客戶端連線狀態（不是伺服器欄位）。

---
## 3. Bridge 對映、匯入路徑與讀模型

本章是 §1、§2 的實作規則：console-api 如何呼叫 Engine Bridge、如何把外部結果轉成 Console 的資料。所有 Bridge 事實已對 `AgentConsole/engine-bridge/`（README、`app/*.py`、`tests/`）核對；Bridge 只有 console-api 以服務身分呼叫（內網，無認證，Architecture §12 L-6）。

### 3.1 呼叫總表

Bridge 基底位址＝系統參數 `autoclaude.engineUrl`（`/autoclaude/*`）與 `sdd.engineUrl`（`/sdd/*`），預設 `http://engine-bridge:8081`；健康探測路徑＝`autoclaude.healthCheckPath`（預設 `/health`）。

`AgentBridge`（application 層的 out port）建議的方法名列在最後一欄：後端第一棒先放 `sddCompile`、`decompose`、`approveDraft`、`health`，第二棒在同一介面補其餘（runs 系列）。

| Console 操作 | Bridge 呼叫 | 成功碼 | 逾時（連線／讀取） | 重試 | 方法名 |
|--------------|-------------|--------|--------------------|------|--------|
| execute | `POST /autoclaude/runs` | 201 | 2s／30s | 無（非冪等；失敗即補償） | `startRun` |
| pause | `POST /autoclaude/runs/{id}:pause` | 202 | 2s／5s | 無 | `pauseRun` |
| resume | `POST /autoclaude/runs/{id}:resume`（可帶 `env`） | 202 | 2s／15s | 無 | `resumeRun` |
| cancel | `POST /autoclaude/runs/{id}:stop` | 202 | 2s／10s | 無 | `stopRun` |
| restore | `POST /autoclaude/runs/{id}/restore` | 202 | 2s／15s | 無 | `restoreRun` |
| 取快照 | `GET /autoclaude/runs/{id}` | 200 | 2s／3s | 2 次（200ms 退避） | `getRun` |
| 事件重播 | `GET /autoclaude/runs/{id}/events?after=&limit=` | 200（裸陣列） | 2s／10s | 2 次 | `listEvents` |
| 事件串流 | `GET /autoclaude/runs/{id}/stream?after=<last_seq>` | 200 SSE | 3s／45s（閒置逾 45 秒視為斷線，以 `after=<last_seq>` 重連；Bridge 每 15 秒送 keep-alive） | 指數退避 1→30s | `streamEvents` |
| 匯入規格 | `POST /sdd/compile {spec_dir}` | 200 | 2s／15s | 無 | `sddCompile` |
| 匯入拆解 | `POST /autoclaude/decompose` | 200 | 2s／`model.timeout`＋15s | 無 | `decompose` |
| signoff | `POST /autoclaude/decompose/{draft_id}:approve` | 200 | 2s／10s | 無（對已簽署者 409 視為成功） | `approveDraft` |
| 健康探測 | `GET {healthCheckPath}` | 200 | 2s／3s | 無；每 30 秒一次，**console-api 啟動時與每個 run 開始時各立即探測一次**，結果存記憶體環（2,880 筆＝24 小時） | `health` |
| 斷點列表 | `GET /autoclaude/runs/{id}/checkpoints`（`checkpoint_id,name,created_at,step_idx,step_id,is_automatic`；與 `console.checkpoints` 等價但沒有 `completedSteps`，契約的 `GET /executions/{runId}/checkpoints` 以 DB 為準，這條供審核 `RETRY` 找 `step_idx` 快照時使用） | 200 | 2s／5s | 2 次 | `listCheckpoints` |

`:resume` 與 `restore` 的 body 可帶 `env`（Bridge 重啟後請求層 env 會遺失，見其 `ENV_LOST` 告警）：console-api 一律重新物化並帶上 §3.4.2 的 `env`。**機密只能走 `env`**（Bridge 的 `config_overrides` 拒絕 `api_key`／`db_dsn`，且 `run.json` 只記 env 的名稱）。

### 3.2 錯誤轉譯（Bridge → Console）

Bridge 錯誤封包一律 `{"code":<狀態>,"reason":"…",…}`；422 另帶 `violations[]`（`{field,rule,message,…}`）。

| Bridge 回應 | 發生於 | Console 回應 |
|-------------|--------|--------------|
| 409 `advisory_lock_held`＋`holder_run_id` | execute、restore | **409** `同專案同路徑已有執行中的批次`，`details={holderRunId}`（execute 另補償刪除剛建的列） |
| 409 `invalid_state`＋`{run_id,status,detail}` | pause／resume／stop／restore | **409** `目前執行狀態不允許此操作`，`details={action,runStatus,bridgeStatus}`（`bridgeStatus`＝Bridge 的 `status`） |
| 409 `no_checkpoint` | resume | **409** `找不到可續跑的 checkpoint` |
| 404 `run_not_found` | 控制類呼叫 | **409** `引擎端已無此執行（工作區可能已清除）`；`GET` 詳情改以 `bridge.runKnown=false` 表達，不報錯 |
| 404 `checkpoint_not_found` | restore | **404**（訊息 `checkpoint 不存在或不屬於此執行：<id>`） |
| 404 `draft_not_found` | approve | **409** `草案已失效，請重新解析`，`details={draftId}` |
| 409 `already_signed_off` | approve | 視為成功（冪等） |
| 422 `sanitization_failed`＋`violations[]` | execute、resume、restore | **422** `引擎拒絕此請求`，`details={bridgeReason:"sanitization_failed",violations}`（逐項原樣帶出，不改寫） |
| 422 `invalid_request`＋`violations[]` | 任何 | **422** `引擎拒絕此請求`（`bridgeReason:"invalid_request"`）；代表 console-api 組出的請求不符契約＝缺陷，另記 ERROR 日誌 |
| 422 帶 `gate`／`detail`（`max_steps`／`cycle`／`empty_prompt`／`brain_unsupported`／`brain_failed`；Bridge 還會把 `duplicate_step_id`、`dangling_dependency` 歸入 `cycle`，`empty_goal` 歸入 `empty_prompt`，`no_steps`、`brain_returned_none` 歸入 `brain_failed`） | decompose | 轉成 **422** `解析結果未通過有界閘`，`errors[]` 項目 `gate`／`detail` 取 Bridge 值（`location` 省略） |
| 422 `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_not_found`／`spec_ambiguous`＋`detail` | sdd compile | **422** `SDD 規格檢查未通過`，`details={bridgeReason,detail}`（匯入探測模式下的 `spec_not_found` 例外，見 §3.3.1） |
| 503 `sdd_unavailable` | sdd compile | 探測模式：略過路徑 A；明示 `specDir`：**502** `引擎橋接服務錯誤` |
| 500 `spawn_failed`、503 `lock_backend_unavailable`、`run_exists`（console 的 id 是新 UUID，不應發生）、其餘 5xx | execute 等 | **502** `引擎橋接服務錯誤`，`details={bridgeStatus,bridgeReason}`；execute 補償刪除 run 列 |
| 連線失敗（拒絕連線、DNS、連線逾時） | 任何 | **502** `引擎橋接服務無法連線` |
| 讀取逾時 | 任何 | **504** `引擎橋接服務逾時` |

### 3.3 匯入：三條解析路徑

#### 3.3.1 路徑選擇（`POST /import/{id}/parse`；依序，先符合者勝）

1. **明示 `specDir`**（非空白）→ **路徑 A**。任何 Bridge 失敗都報錯（含 `spec_not_found`）。
2. **探測 `executionPath`**：`POST /sdd/compile {spec_dir: executionPath}`（`sdd.engineUrl`）。
   - 200 → **路徑 A**。
   - 422 `spec_not_found`，或 422 `sanitization_failed`（路徑不存在／不在 allowlist 內；匯入階段的探測不因此擋下，執行階段才由 Bridge 把關）→ 視為「沒有規格」，繼續第 3 步。
   - 422 `spec_not_frozen`／`spec_tainted`／`spec_format_version_unsupported`／`spec_ambiguous` → **規格存在但被拒＝fail-closed**：回 422 `SDD 規格檢查未通過`，**不**退回 LLM 路徑瞎猜（PRD §0.4 的凍結硬閘）。
   - Bridge 不可達／逾時／503 → 略過路徑 A（記日誌），繼續第 3 步。
3. **路徑 C**：`sourceType=PLAIN_TEXT` 且 `content.strip()` 長度 **< 2,000 字元** 且**沒有 Markdown 標題行**（無符合 `^[ ]{0,3}#{1,6}[ \t]` 的行）→ 視為高階目標。
4. **路徑 B**：其餘全部。

`sourceType=MARKDOWN／PDF／DOCX` 一律不會走 C（它們是文件）。

**所有路徑共通**：`parsedResult.project.executionPath` 與 `project.autonomyLevel` 一律取自 `ParseOptions`（不採模型或規格建議的值）；`ImportRecordResponse.parsePath` 記錄採用的路徑；任務數、目標數的上限與 `prompt_too_long` 對每條路徑都適用（§3.3.5）。

#### 3.3.2 路徑 A：規格驅動（`path=SDD`）

- **請求**：`POST /sdd/compile {"spec_dir": "<specDir 或 executionPath>"}`。
- **Bridge 回應**：`{tasks[], scenario, contracts[], spec_path, digest, spec_format_version}`；`tasks[]` 是 `SddToPlaybookAdapter.compile_tasks` 的 PlaybookTask（`step_id,name,prompt,expected_output_regex?,evaluator_command?,spec_digest,weak_regex,…`）。
- **轉換**（1 個 Goal ＋ N 個 Task，ADR-001 D18）：

| Console 欄位 | 來源 |
|--------------|------|
| `project.name` | `scenario`（空則 `executionPath` 的最後一段目錄名） |
| `project.passCriteria` | `規格「<scenario>」的全部合約驗收通過` |
| `project.description` | `由凍結 SDD 規格匯入（<spec_path>；digest <digest 前 12 碼>）` |
| `goals[0]` | `key=g1`、`name=<scenario>`、`passCriteria=全部 <N> 個合約的驗收標準通過`、`description=` 同專案 description |
| `tasks[i].name` | `task.name` |
| `tasks[i].description` | `task.prompt`（完整，不截斷） |
| `tasks[i].passCriteria` | `輸出符合 <expected_output_regex>`；無 regex 則 `規格合約 <step_id> 的驗收標準` |
| `tasks[i].expectedOutputRegex` | `task.expected_output_regex`（無法編譯 → 清空＋warning `regex_dropped`） |
| `tasks[i].evaluatorCommand` | `task.evaluator_command`（過 Phase 2 消毒；含禁用字元 → 清空＋warning `evaluator_command_dropped`） |
| `tasks[i].passCriteriaSpec` | `{"source":"sdd","specDigest":"<digest>","stepId":"<step_id>","weakRegex":<bool>}` |
| `specDigest` | `digest`；`aiModel`／`tokenUsed` 皆 null；不呼叫任何 Brain |

#### 3.3.3 路徑 B：自由文件 → OpenAI 相容 chat completions（`path=LLM`）

- **設定來源**：`model.apiUrl`、`model.apiKey`（解密）、`model.name`、`model.timeout`、`model.temperature`、`model.topP`、`model.maxTokensPerRequest`（皆取呼叫當下的值）。
- **呼叫前的檢查**（不過 → `brain_unsupported`，`detail` 說明原因）：`model.apiKey` 非空；`model.apiUrl` 通過 SEC-04（§1.5.7 的檢查 1～6，含 DNS 釘 IP 與不跟隨 redirect）。
- **URL 決定**：取 `model.apiUrl` 去尾端 `/`；其路徑已以 `/chat/completions` 結尾則照用；以 `/v1` 結尾（OpenAI 慣例的 base URL，例 `https://api.openai.com/v1`）則附加 `/chat/completions`；其餘附加 `/v1/chat/completions`（例 `http://127.0.0.1:<port>` → `http://127.0.0.1:<port>/v1/chat/completions`）。兩種常見寫法都能用，不會出現 `/v1/v1`（§6 D-48）。
- **請求**：`POST <URL>`，標頭 `Authorization: Bearer <apiKey>`、`Content-Type: application/json`；body：

```json
{ "model": "<model.name>",
  "messages": [
    { "role": "system", "content": "<系統訊息，見下>" },
    { "role": "user",   "content": "<PRD §5.2.4 樣板代入後的全文，見下>" } ],
  "temperature": <model.temperature>, "top_p": <model.topP>, "max_tokens": <model.maxTokensPerRequest>,
  "response_format": { "type": "json_object" }, "stream": false }
```

- **系統訊息**（逐字）：

```
你是一位資深的軟體架構師。只輸出一個 JSON 物件，不要輸出任何其他文字，也不要使用 Markdown 程式碼框。
JSON 結構：
{
  "project": { "name": "string", "executionPath": "string（建議）", "passCriteria": "string（Markdown）", "description": "string（Markdown）" },
  "goals": [
    { "key": "g1", "name": "string", "description": "string（Markdown）", "passCriteria": "string（Markdown）",
      "sortOrder": 0, "dependsOn": ["其他目標的 key；沒有則為空陣列"],
      "tasks": [ { "name": "string", "description": "string（Markdown，不可為空）", "passCriteria": "string（Markdown）", "sortOrder": 0, "estimatedTokens": 0 } ] }
  ]
}
限制：最多 24 個目標、每個目標最多 24 個任務；key 在整份輸出內唯一；dependsOn 只能引用其他目標的 key 且不得成環；每個任務的 description 都必須有實質內容。
```

- **使用者訊息**＝PRD §5.2.4 的輸入 Prompt 樣板逐字，代入 `{autonomyLevel}`（`ParseOptions.autonomyLevel`，影響任務粒度，US-I-07）、`{additionalPrompt}`（空則 `（無）`）、`{documentContent}`（`sourceContent`）：

```
你是一位資深的軟體架構師。請分析以下需求文件，並將其拆解為三層結構：

1. **專案 (Project)**：整體專案名稱、執行路徑建議、通過標準、說明描述
2. **目標 (Goal)**：專案下的主要里程碑或功能模組，含說明描述與通過標準
3. **任務 (Task)**：目標下的具體可執行開發任務，含說明描述與通過標準

自治等級: {autonomyLevel}
補充說明: {additionalPrompt}

---
需求文件內容:
{documentContent}
---

請以 JSON 格式輸出結果。
```

- **長度上限**：系統訊息＋使用者訊息總字元數 > `console.import.max-prompt-chars`（預設 120,000）→ 不呼叫模型，直接 `prompt_too_long`（`location=sourceContent`）。
- **回應處理**：取 `choices[0].message.content`；`finish_reason=length` → `brain_failed`（`detail`：輸出被截斷，請縮短文件或調高 `model.maxTokensPerRequest`）；內容空白／非 JSON（容許外層 ``` 程式碼框，先剝除）／缺 `project` 或 `goals`／`goals` 為空／某目標 `tasks` 為空 → `brain_failed`（`detail` 指出缺什麼）；HTTP 非 2xx、逾時（`model.timeout`）、連線失敗 → `brain_failed`（`detail` 含 HTTP 狀態或例外類別，**不含金鑰與完整 URL**）。成功時 `tokenUsed`＝`usage.total_tokens`（缺則 `prompt_tokens+completion_tokens`，再缺為 null）、`aiModel`＝回應的 `model`（缺則 `model.name`）。
- **轉成 `ParsedResult`**：目標缺 `key` 則依序補 `g1、g2…`；`project.executionPath` 一律以 `ParseOptions.executionPath` 為準（LLM 的建議丟棄）；任務／目標的 `passCriteria` 空白 → 填佔位字串 `（AI 解析未提供通過標準，請於 signoff 前補齊）` 並加 warning `passcriteria_placeholder`；`sortOrder` 一律依陣列順序重編；LLM 帶的未知欄位忽略。

#### 3.3.4 路徑 C：高階目標 → Bridge decompose（`path=DECOMPOSE`）

- **請求**：`POST /autoclaude/decompose`，body `{"goal": <content.strip()>, "context": <additionalPrompt 或 "">, "project": <內容第一行（≤ 60 字元）或 "decomposed-goal">, "max_steps": 24, "config_overrides": {"minimax": {"base_url","model","timeout_seconds"}}}`；`minimax` 區段只在 `model.apiKey` 有值時帶（取 `model.apiUrl`／`model.name`／`model.timeout`）。**注意**：Bridge 的 decompose **只從它自己的行程環境讀 `MINIMAX_API_KEY`**，請求無法帶金鑰（`config_overrides` 禁放機密）；Bridge 環境沒有金鑰 → 422 `brain_unsupported`（`detail`＝「無法建立 Brain：…」），這是部署設定問題，訊息逐字顯示給使用者。
- **Bridge 回應**：`{draft_id, goal_hash, reasoning, playbook:{project, global_goal, tasks[{step_id,name,prompt,evaluator_command?,…}]}, signed_off:false}`；`tasks[]` 已是拓撲序，**不含依賴資訊**（引擎只在驗證時用 `depends_on`，草稿不保留）。
- **轉換**（1 個 Goal ＋ N 個 Task）：

| Console 欄位 | 來源 |
|--------------|------|
| `project.name` | 請求的 `project` |
| `project.passCriteria` | `goal`（原文） |
| `project.description` | `reasoning`（空則 `由高階目標自動拆解`） |
| `goals[0]` | `key=g1`、`name=<project.name>`、`description=reasoning`、`passCriteria=拆解出的全部步驟依序完成` |
| `tasks[i].name` | `step.name`（空則 `step_id`） |
| `tasks[i].description` | `step.prompt` |
| `tasks[i].passCriteria` | 有 `evaluator_command` 則 `評估指令通過`，否則佔位字串（同 3.3.3）＋warning `passcriteria_placeholder` |
| `tasks[i].evaluatorCommand` | `step.evaluator_command`（消毒不過 → 清空＋warning `evaluator_command_dropped`） |
| `tasks[i].passCriteriaSpec` | `{"source":"decompose","stepId":"<step_id>","draftId":"<draft_id>"}` |
| `draftIds`／`reasoning` | `[draft_id]`／`reasoning`；`aiModel`／`tokenUsed` 為 null（Bridge 不回報） |

- Bridge 草稿存於其 workspace 的 `_drafts/<draft_id>.json`；signoff 時對每個 `draftIds` 呼叫 `:approve`（審計）。

#### 3.3.5 三道有界閘與相關檢查

三條路徑與 `PUT /import/{id}/result` 共用同一個後端實作（`ParsedResultValidator`），在樹層級**一次列出全部違規**（US-I-10：完整顯示、不截斷、不修剪；`errors[]` 依下表順序，同閘內依樹的位置）。路徑 C 的 Bridge 閘（對映見 §3.2）先於本表；路徑 B 的 `brain_*` 發生在還沒有樹的時候，所以只會單獨出現。

| 順序 | `gate` | 定義 | `location` 格式 | `detail` 範例 |
|------|--------|------|-----------------|---------------|
| 1 | `empty_prompt` | 任務 `name` 或 `description` 去空白後為空 | `goals[i].tasks[j].name`／`.description` | `任務「（未命名）」的描述為空（goals[0].tasks[2]）` |
| 2 | `max_steps` | 目標數 > 24；或任一目標的任務數 > 24（硬上限，config 可下調不可上調；**不截斷、不修剪**） | `goals`／`goals[i].tasks` | `目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）` |
| 3 | `cycle` | 目標依賴圖不是 DAG：Kahn 排序失敗（成環）、自依賴、`dependsOn` 引用不存在的 `key`、目標 `key` 重複（Bridge 同樣把這些 DAG 結構問題歸入 `cycle`） | `goals[i].dependsOn`／`goals[i].key` | `目標依賴成環：基礎 -> 核心 -> 基礎` |
| 4 | `prompt_too_long` | 任務依 §3.4.3 樣板組出的 prompt 超過 20,000 字元（Windows 命令列上限，Architecture §12 L-9） | `goals[i].tasks[j]` | `任務「實作」的 prompt 長度 23412 超過上限 20000` |
| — | `brain_unsupported` | 路徑 B：`model.apiKey` 為空，或 `model.apiUrl` 未通過 SEC-04；路徑 C：Bridge 無法建立 Brain | 省略 | `模型位址未通過 SSRF／allowlist 檢查（not_in_allowlist）` |
| — | `brain_failed` | 模型呼叫失敗、輸出非 JSON／缺必要欄位／結果為空／被截斷（路徑 B）；Bridge 回報無步驟或 Brain 回 None（路徑 C） | 省略 | `模型輸出不是合法 JSON：…` |
| — | `prompt_too_long`（文件層） | 路徑 B 的 LLM 輸入總長超過 `console.import.max-prompt-chars` | `sourceContent` | `文件過長：<n> 字元，上限 120000` |

結構性問題（缺必填、空陣列）與消毒問題（禁用字元、regex 無法編譯）**不是**閘，回 400（見 1.1.4）。

#### 3.3.6 `ParseResultResponse` 各欄位

| 欄位 | parse 成功 | PUT result 成功 |
|------|-----------|-----------------|
| `importId` | 記錄 id | 同左 |
| `status` | `PARSED` | `REVIEWING` |
| `path` | `SDD`／`LLM`／`DECOMPOSE` | 沿用庫內值 |
| `parsedResult` | 三層樹＋`path`／`aiModel`／`tokenUsed`／`reasoning?`／`draftIds?`／`specDigest?` | 以請求的 `project`＋`goals` 覆寫後的樹（伺服器欄位沿用庫內值） |
| `signedOff` | `false` | `false`（編輯撤銷 signoff） |
| `aiModel`／`tokenUsed`／`reasoning` | 路徑 B：模型回報；路徑 C：只有 `reasoning`；路徑 A：皆 null | 沿用庫內值 |
| `errors` | `[]`（閘違規走 422，不走這裡） | `[]` |
| `warnings` | `evaluator_command_dropped`／`regex_dropped`／`passcriteria_placeholder`，每項 `{code,detail,location}` | 重新計算（只含仍成立者） |

---
### 3.4 執行：Playbook 組裝與 Bridge 請求

#### 3.4.1 Playbook 欄位表（`PlaybookBuilder`；Bridge `PlaybookIn` 為 `extra=forbid`，多送欄位即 422）

| Playbook 欄位 | 來源 | 備註 |
|---------------|------|------|
| `version` | 固定 `"1.0"` | |
| `project` | 專案名稱淨化後（見下） | 1～200 字元；同名同路徑會共用 Bridge 的 advisory lock 鍵 |
| `global_goal` | `project.passCriteria` | 主控裁決（W3 任務書；Architecture 寫「說明、缺則通過標準」，§6 D-07） |
| `workflow_type` | 不送（預設 `auto`） | |
| `global_invariants.max_retries_per_step` | 系統參數 `agent.maxRetries` | 0～20（設定驗證已保證） |
| `global_invariants.auto_compact_interval` | 不送（引擎預設 5） | **E2E 專案任務數須 ≤ 5**，避免觸發引擎的 `/compact` 額外呼叫而改變 Token 帳（§5.0） |
| `tasks[].step_id` | `G<g>-T<t>`（§3.4.4） | 1～128 字元、無控制字元；整份 playbook 內唯一 |
| `tasks[].name` | `task.name` | 1～500 字元 |
| `tasks[].prompt` | §3.4.3 樣板 | 1～20,000 字元 |
| `tasks[].expected_output_regex` | `task.expectedOutputRegex` | 無則不送 |
| `tasks[].evaluator_command` | `task.evaluatorCommand` | 先過第 2 層複驗（§1.2.1 第 9b、9c）；無則不送 |
| `tasks[].max_retries` | `task.maxRetries` | 0～20 |
| `tasks[].goal_task_id` | `task.id`（UUID 字串） | **必送**：Bridge 只有帶 UUID 的步驟才寫 `execution_steps` |
| `tasks[].command` | **永不送** | 引擎 Kernel 路徑對它零消費（ADR-001 D17）；E2E 的替身走 `claude.command` |
| `tasks[].maintain_context`／`evaluator_timeout_seconds`／其他 | 不送 | 用 Bridge／引擎預設 |

**專案名稱淨化**：把不在 `[A-Za-z0-9._\-一-鿿]` 內的字元換成 `_`，截到 200 字元；結果為空則用 `project-<專案 id 前 8 碼>`。

Bridge 請求：`{ "run_id": "<execution_runs.id>", "project": "<淨化名>", "execution_path": "<project.executionPath>", "playbook": {…}, "config_overrides": {…}, "env": {…}, "fresh": false }`。

#### 3.4.2 `config_overrides` 與 `env` 物化（`ConfigMaterializer`；`API-SET-10`）

Bridge 對 `config_overrides` 的規則：頂層鍵限 `claude, minimax, embedder, loop, playbook, token_guard, alert_ladder, notification, tool_invocation, executor, preferences`；未知鍵 → 422（引擎會靜默丟棄打錯字的欄位，所以 Bridge 擋）；機密鍵（`minimax.api_key`、`storage.db_dsn` 等）→ 422；`storage`／`checkpoint_dir`／`log_dir` 等管控鍵**合法但被忽略並發 `CONFIG_OVERRIDE_IGNORED` 告警**（所以 Console **不送**，避免每個 run 都帶噪音告警）。

| 送到 Bridge 的位置 | 來源（系統參數） | 條件 |
|--------------------|------------------|------|
| `config_overrides.claude.command` | `autoclaude.claudeCommand`（預設 `claude`；E2E 為 `aisdlc-mock-claude`） | 永遠 |
| `config_overrides.claude.extra_args` | `autoclaude.claudeExtraArgs` 以空白切成陣列 | 非空才送；每個 token 須符合 `^[A-Za-z0-9_.=:,/@\-]+$` |
| `config_overrides.claude.continue_flag`／`encoding` | `autoclaude.claudeContinueFlag`／`claudeEncoding` | 永遠 |
| `config_overrides.playbook.step_timeout_seconds` | `agent.taskTimeout` | 永遠 |
| `config_overrides.token_guard.compact_threshold_pct`／`halt_threshold_pct` | `execution.compactThresholdPct`／`haltThresholdPct`（整數轉數字） | 永遠；**不送 `token_guard.enabled`**（不得經 Console 繞過安全收斂，NFR-SEC-05） |
| `config_overrides.token_guard.auto_resume`／`max_auto_resumes` | `execution.autoResume`／`maxAutoResumes` | 永遠 |
| `config_overrides.minimax.base_url`／`model`／`timeout_seconds`／`enable_kernel_brain` | `model.apiUrl`／`model.name`／`model.timeout`／`model.enableKernelBrain` | **只在 `model.apiKey` 有值時**送（否則 Bridge 會把預設的 Anthropic URL 當 MiniMax 外呼位址驗證而拒絕，且引擎本來也用不到 Brain） |
| `env.MINIMAX_API_KEY` | `model.apiKey` 解密後 | 只在有值時送；絕不進 `config_overrides`、日誌或回應 |
| `env.MOCK_CLAUDE_*` | profile `e2e`／`test` 的 `console.execution.mock-env` 映射（例 `MOCK_CLAUDE_DELAY`、`MOCK_CLAUDE_FAIL_REGEX`、`MOCK_CLAUDE_TRACE`） | **只在測試 profile**；production 永不送 |

不送／只儲存：`autoclaude.dalBackend`／`dbDsn`／`dualReadResolution`（Bridge 固定 `yaml_only`，`effect=STORED_ONLY`，§6 D-27）、`agent.maxConcurrentTasks`／`execution.maxParallelGoals`（引擎序列執行）、`agent.enableAutoMutation`／`enableSelfEvolution` 與 Level 6～10（`UNVERIFIED`：Console 不另送引擎設定，行為同 Level 5；待 W4 驗證後回寫）。

#### 3.4.3 prompt 樣板與長度上限

`tasks[].prompt` ＝ 下列文字（行以 `\n` 連接）；`task.description` 去空白後為空時，描述那一段（連同它前後的空行）整段省略：

```
## 任務 <stepId>：<task.name>
所屬目標：<goal.name>

<task.description>

## 通過標準
<task.passCriteria>
```

- 加入 `<stepId>` 與任務名稱是為了讓每步 prompt **互不為子字串**——Bridge 以「步驟 prompt 是否出現在引擎啟動行」辨識步驟邊界，prompt 相同或互為子字串會讓邊界判定退化。
- **長度**以 Java `String.length()`（UTF-16 code unit）計，≤ **20,000**；超過 → execute 第 9a 項 422（匯入階段為 `prompt_too_long` 閘）。依據：引擎把 prompt 當命令列參數傳給 claude，Linux 單一參數上限 128 KiB、**Windows 整條命令列 32,767 字元**（Architecture §12 L-9；CI run 以 50,000 個中文字實證 spawn 失敗）。
- `task.description`／`passCriteria` 的 Markdown 原文原樣帶入，不另轉義（它們不是命令；命令欄位只有 `evaluatorCommand`，已走三層消毒）。

#### 3.4.4 DAG 與 `step_id`

- **目標位置 `g`**＝該批次範圍內的目標依拓撲＋策略排序後的序號（1 起）；**任務位置 `t`**＝該目標在**本批次範圍內**的任務序（1 起，依 `sortOrder`、`createdAt`、`id`）。`step_id` ＝ `G<g>-T<t>`（例 `G1-T1`、`G1-T2`、`G2-T1`）。整份 playbook 內唯一，且每個批次獨立編號（後續批次重新從 `G1-T1` 起；`dag.nodes[].stepId` 是權威對映）。這取代 Architecture 的全域 `T001…` 與 W3 任務書的 `G<sortOrder>-T<sortOrder>`（後者在 `sortOrder` 重複時會撞 id，§6 D-06）。
- **展平順序**＝DAG 節點的 `sequence`：`TASK` 節點的 `sequence` 等於 Bridge 的 `step_number`（1 起）。
- `execution_runs.dag`（建立時凍結，只含結構，不含狀態）：

```json
{ "nodes":[
    { "id":"a1f4c2d3-…-4e11", "kind":"GOAL", "label":"基礎", "sequence":1 },
    { "id":"c7e2b1a0-…-1c21", "kind":"TASK", "label":"初始化", "goalId":"a1f4c2d3-…-4e11", "stepId":"G1-T1", "sequence":1 },
    { "id":"c7e2b1a0-…-1c22", "kind":"TASK", "label":"設定",   "goalId":"a1f4c2d3-…-4e11", "stepId":"G1-T2", "sequence":2 },
    { "id":"a1f4c2d3-…-4e12", "kind":"GOAL", "label":"核心", "sequence":2 },
    { "id":"c7e2b1a0-…-1c23", "kind":"TASK", "label":"實作", "goalId":"a1f4c2d3-…-4e12", "stepId":"G2-T1", "sequence":3 } ],
  "edges":[
    { "from":"a1f4c2d3-…-4e11", "to":"a1f4c2d3-…-4e12", "kind":"DEPENDENCY" },
    { "from":"a1f4c2d3-…-4e11", "to":"c7e2b1a0-…-1c21", "kind":"CONTAINS" },
    { "from":"a1f4c2d3-…-4e11", "to":"c7e2b1a0-…-1c22", "kind":"CONTAINS" },
    { "from":"a1f4c2d3-…-4e12", "to":"c7e2b1a0-…-1c23", "kind":"CONTAINS" } ] }
```

#### 3.4.5 建立流程與補償

1. 驗證（§1.2.1 表的 1～9）。
2. **交易 1**：鎖專案列 → 取 `run_number = max+1` → 插入 `execution_runs`（`id` 新 UUID、`autonomy_level`、`scope`、`token_budget`、`dag`；Bridge 欄位留 DDL 預設）→ 提交。（Bridge 的 `UPDATE … WHERE id=run_id` 需要列已存在。）
3. 呼叫 Bridge `POST /autoclaude/runs`。
4. 成功（201）→ **交易 2**：專案與任務狀態（§3.5.3）→ 啟動 `RunEventConsumer`（`after=0`）→ 回應。
5. 失敗 → **交易 3**：刪除剛建的 `execution_runs` 列（僅在它仍是 `INITIALIZING` 且沒有任何 `execution_steps` 時）→ 依 §3.2 轉譯回應；專案與任務狀態不動。
6. 崩潰保護：console-api 啟動時，對「`INITIALIZING` 且建立逾 60 秒」的列問 Bridge `GET run`；Bridge 回 404 → 視同第 5 步補償刪除。

### 3.5 事件 → 讀模型（`RunEventConsumer`）

#### 3.5.1 Bridge 事實（實作消費者前必讀；皆有對應 Bridge 測試）

1. 事件序號從 1 起連續單調；第一則 `status` 是 `INITIALIZING`，接著 `RUNNING`。
2. **`step COMPLETED(k)` 在「步驟 k+1 的啟動行出現」或「引擎結束」時才發**，所以 `COMPLETED(k)` 與 `STARTED(k+1)` 幾乎同時、前者在前；最後一步的 `COMPLETED` 緊接 `status COMPLETED`。
3. **pause 邊界**：被要求暫停時，步驟 k 完成、k+1 剛 spawn 就被終止；k+1 的 `STARTED` **不發**（除非引擎已推進），`status PAUSED` 之前最後一則 `step` 是 `COMPLETED(k)`。一次續跑至少前進一步才允許再暫停。
4. **resume／restore 後引擎重做被打斷的那一步：同一步會再發一次 `STARTED`（`attempt=1`）**——消費者必須冪等：任務已是 `RUNNING` 時忽略重複的 `STARTED`（`execution_steps` 因此可能有兩列同一任務的 `STARTED`，屬正常）。
5. `RETRYING`＝同一步驟的啟動行再次出現，`attempt` 從 2 起；重試耗盡 → `step FAILED`（`attempt`＝最後一次）→ `alert`（`code=ESCALATION`、level `error`）→ run `FAILED`，`reason` 以「引擎升級（ESCALATION）」開頭。Token Guard halt 判 `FAILED`（`reason`＝`引擎因 token／額度門檻停機（halted），未自動續跑`）並發 `alert`（`TOKEN_HALT`、`warning`）；其他異常 `reason` 為 `引擎異常結束（exit=N）：…`；Bridge 重啟回收的孤兒 `reason` 含 `orphaned`。
6. `token` 事件每個 **attempt** 一則（引擎印出 `STEP_TOKEN_PEAK` 時才有，僅 context% > 0），`tokens_used` 是**本 run 累計**（每個 attempt 加最後一筆 usage 的 input＋cache_read＋cache_creation＋output），**不帶 `step_id`**；mock claude 每次呼叫固定 1,240（1,200＋40）。消費者以「目前尚未結束的步驟」歸因。
7. Bridge 只為帶 UUID `goal_task_id` 的步驟寫 `execution_steps`；`review-request` 事件 Bridge 從不發送；`alert.level` 為 `info`／`warning`／`error`（`RESTORE` 為 `info`）。
8. 終態釋放鎖；`PAUSED` 持鎖；Bridge 重啟會把「RUNNING 但行程已不存在」的 run 標 `FAILED`（reason 含 `orphaned`）。
9. 單則 `log` 的 `line` 由 Bridge 截到 8,000 字元；事件 `ts` 為 UTC（`+00:00`）。

#### 3.5.2 事件對讀模型的更新

本表以 Architecture §7.3 為底，補上 §3.5.1 的 Bridge 事實（重複的 `STARTED`、`COMPLETED` 的發出時機、Token 歸因、失敗分類）與審核、告警、系統重設的連動。

「重算目標」＝套用 §3.5.3 的 R-goal 規則重新計算受影響目標的狀態。每處理完一則事件，**同一交易**更新 `execution_runs.console_last_seq`（冪等：重複處理同一 seq 不得產生第二筆審核項／告警／Token 樣本）。

| Bridge 事件 | 任務 | 目標／專案 | 其他副作用 |
|-------------|------|------------|-----------|
| `step STARTED`（第一次） | `→RUNNING`（`QUEUED→RUNNING`；來源不是 `QUEUED` 者先系統重設為 `QUEUED`）；`started_at` 為 null 才寫；`assigned_agent="AutoClaude"` | 重算目標（首個任務開始時 `PENDING→IN_PROGRESS`） | 套 §3.6.1 的 pause 決策；記錄「目前步驟」 |
| `step STARTED`（任務已 `RUNNING`） | 忽略（重做被打斷的步驟） | — | — |
| `step RETRYING` | `retry_count += 1`；維持 `RUNNING`（引擎內的 `FAILED→QUEUED→RUNNING` 折疊） | — | 評估 `HIGH_RETRY_RATE` |
| `step COMPLETED` | `RUNNING→VALIDATING→COMPLETED`；`completed_at`；`actual_tokens`（見下） | 重算目標 | 評估 `TASK_DURATION_EXCEEDED` |
| `step FAILED` | `RUNNING→FAILED`；`execution_log` 附錯誤訊息 | 重算目標 | 等 `status FAILED` 才分類（見下） |
| `token` | 依歸因加到該任務 `actual_tokens` | — | 寫 `run_token_samples`；評估 `TOKEN_BUDGET_*` 與 `scope.limits` |
| `alert` `ESCALATION`／`TOKEN_HALT` | — | — | 持久化 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT`（`event_sub=0`）；一律轉發 SSE |
| `status PAUSED` | 無任務在跑 | 專案 `EXECUTING→READY`；重算目標 | 若有待決的閘 → 建審核項（§3.6.2） |
| `status RUNNING`（resume／restore 之後） | — | 專案 `→EXECUTING` | — |
| `status COMPLETED` | 殘留的 `RUNNING／VALIDATING`→`COMPLETED`（補正） | 重算目標；專案：全部未刪任務皆 `COMPLETED／SKIPPED`→`COMPLETED`，否則→`READY`（部分範圍的批次） | 最終 `metric-update`；關閉串流 |
| `status FAILED` | 依 `reason` 分類：以「引擎升級（ESCALATION）」開頭 → 最後一個 `FAILED` 任務 `FAILED→ESCALATED`；其餘（halt／異常／orphaned）維持 `FAILED`；範圍內仍 `QUEUED` 者→`PENDING`（系統重設） | 重算目標；專案→`FAILED` | 依自治等級建審核項（§3.6.2）；評估 `CONSECUTIVE_FAILURES` |
| `status CANCELLED` | 範圍內 `RUNNING`／`QUEUED`→`CANCELLED`（系統重設，US-E-06） | 重算目標；專案→`READY` | — |

**Token 歸因與 `actual_tokens`**：`delta = tokens_used − 上一則樣本的 tokens_used`（沒有上一則為 0）；歸因給「目前尚未 `COMPLETED`／`FAILED` 的步驟」所屬任務（`token` 事件先於同一步的 `COMPLETED`，所以對得上；沒有目前步驟則 `task_id` 為 null）。`tasks.actual_tokens` ＝跨所有批次的累計（每次加 `delta`）；`ExecutionStepResponse.tokensUsed` 取該任務**在本批次**的 `run_token_samples` 加總。

**`tasks.execution_log`**（US-T-05「最近一次執行日誌」）：寫入該任務最近一次執行的 STEP 摘要行與引擎 `WARN`／`ERROR`／`CRITICAL` 行，單任務上限 20,000 字元（超出保留尾端）；新一次 `STARTED`（第一次）時清空重寫。

#### 3.5.3 系統重設規則（PRD 附錄 B 沒有涵蓋 cancel／restore／後續批次）

附錄 B.3 不含 `QUEUED→CANCELLED`、`CANCELLED／COMPLETED／FAILED→QUEUED`、`QUEUED→PENDING`，附錄 B.2 不含 `FAILED→IN_PROGRESS`；但 US-E-06（取消）、US-E-11（還原）與「失敗後可重新執行」必須有這些結果。**裁決（§6 D-19）**：這些屬 **console-api 的系統重設操作**（由執行事件或審核決定觸發，領域層以專用方法直接設定狀態，不經 `StateMachines.requireTransition`），**手動 API（`PUT` 專案／`POST /tasks/{id}/retry` 等）仍完全遵守附錄 B**，`StateMachinesTest` 不受影響。

**R-goal（目標狀態推導；每個重算點都套用）**：令目標下未軟刪的任務集合為 T。
1. T 非空且全為 `COMPLETED`／`SKIPPED`：全為 `SKIPPED`→`SKIPPED`，否則→`COMPLETED`；
2. 否則若有任一 `FAILED`／`ESCALATED`→`FAILED`；
3. 否則若有任一 `RUNNING`／`VALIDATING`／`COMPLETED`→`IN_PROGRESS`；
4. 否則→`PENDING`。

| 觸發 | 專案 | 目標 | 任務 |
|------|------|------|------|
| execute 成功 | `→EXECUTING`（`DRAFT`／`FAILED` 先 `→READY`；`COMPLETED` 為系統重設，直接 `→EXECUTING`） | 不動（首個任務開始時才 `IN_PROGRESS`） | 範圍內非 `COMPLETED`／`SKIPPED` 者→`QUEUED`（`PENDING／FAILED／ESCALATED／PAUSED→QUEUED` 屬 B.3；`CANCELLED／BLOCKED／RUNNING／VALIDATING→QUEUED` 屬系統重設） |
| run `FAILED` | `→FAILED` | R-goal | 範圍內 `QUEUED→PENDING`；失敗任務依 §3.5.2 |
| run `CANCELLED` | `→READY` | R-goal | 範圍內 `RUNNING／QUEUED→CANCELLED` |
| run `COMPLETED` | 全完成→`COMPLETED`，否則→`READY` | R-goal | — |
| restore 被 Bridge 接受 | `→EXECUTING` | R-goal | 範圍內**不在**快照 `completed_step_ids` 內的任務→`QUEUED`（來源可為 `COMPLETED／FAILED／ESCALATED／CANCELLED／PENDING`；`SKIPPED` 不重設，restore 只允許最新批次故不會與之衝突）；被重設任務的 `actual_tokens` 保留（Token 已實際花費） |
| 審核 `SKIP`（後續批次） | 同 execute（後續批次） | R-goal | 該任務→`SKIPPED`；後續批次範圍＝專案內其餘非 `COMPLETED`／`SKIPPED` 任務 |
| 審核 `REJECT`（gate 類） | 隨 `CANCELLED` | 被審目標強制設為 `FAILED`（人類判定） | 同 `CANCELLED` |
| 新批次建立時 | — | — | **前一批次尚 `PENDING` 的審核項自動關閉**：`status=REJECTED`、`decided_by=system`、`comment=已由第 <N> 批次取代`（避免對過期批次下決定） |
| run 進入 `COMPLETED`／`CANCELLED` | — | — | 該批次仍 `PENDING` 的 **gate 類**審核項（`TASK_CONFIRM`／`GOAL_CONFIRM`／`GOAL_COMPLETED`）自動 `REJECTED`（`decided_by=system`、`comment=執行已取消` 或 `執行已結束`）；`FAILED` 批次的 `ESCALATED` 審核項不在此列（它們正是待處置的對象） |
| 手動 `resume`／`restore`（不經審核） | — | — | 該批次 `PENDING` 的 gate 類審核項自動關閉：`resume`→`APPROVED`（`decided_by`＝呼叫者、`comment=以手動恢復處理`）；`restore`→`REJECTED`（`decided_by=system`、`comment=執行已還原`） |

#### 3.5.4 消費者生命週期（`RunEventConsumer`）

- **啟動時機**：① execute 成功（`after=0`）；② restore 被 Bridge 接受（終態 run 被 restore 後，原消費者已結束，須重啟；`PAUSED` 的 resume 沿用現有消費者）；③ **console-api 啟動時**，對每個 DB 狀態非終態的批次（`RUNNING`、`PAUSED`；`INITIALIZING` 見 §3.4.5 第 6 點）各啟一條，`after=console_last_seq`。
- **啟動掃描的對帳**：③ 先問 Bridge `GET /autoclaude/runs/{id}`：回 404 `run_not_found` → 不啟動消費者、DB 不動（狀態欄由 Bridge 擁有）、寫 WARN 日誌；`GET /executions/{runId}` 以 `bridge.runKnown=false` 表達，SSE 依 §2.3 第 5 點處理。Bridge 不可達 → 仍啟動消費者（由連線層重試，§3.1）。
- **重連**：連線失敗或閒置逾 45 秒視為斷線，指數退避 1→30 秒，以最後已處理的 Bridge seq 作 `after`（Bridge 的 stream 會先重播 `after` 之後的事件再接即時，毋須另外回補；缺口很大時可改以 `GET …/events?after=&limit=` 分頁取回）。
- **冪等與順序**：每則事件依 `seq` 處理，`seq ≤ console_last_seq` 一律略過（§3.5.2）；同一 run 的事件處理與控制操作以 per-run 互斥鎖序列化（§1.2）。
- **結束**：處理完終態 `status` 事件（含其衍生的審核項、告警、專案與任務狀態）後結束消費者，並依 §2.4 關閉該 run 的 SSE 訂閱連線；之後若 restore，由第 ② 點重啟。
- **位移持久化**：`console_last_seq` 存在 DB（V7），console-api 重啟不丟事件、不靠記憶體位移。

---

### 3.6 審核閘（自治等級 1～10）

AutoClaude 沒有審核鉤子，也不改它：閘點由 `ReviewGatePolicy` 依自治等級計算，以 Bridge 的 `:pause` 實現。**`:pause` 在「呼叫之後的下一個步驟邊界」生效**（Bridge `README`、`runner.py`、`test_e2e_lifecycle.py::test_pause_stops_at_the_step_boundary…` 已實證），所以閘點一律「**提前一步**」：在要停的那一步 `STARTED` 時就呼叫，等它的 `COMPLETED` 才呼叫就晚了一步（W3 任務書「每個 `step COMPLETED` 後立即 `:pause`」會多跑一個任務，§6 D-09）。

#### 3.6.1 pause 決策表（`step STARTED` 第一次出現時評估；每個 `(run, 步驟)` 只呼叫一次；Bridge 狀態不是 `RUNNING` 時不呼叫）

記號：`N`＝總步驟數；`i`＝剛開始的步驟位置（1 起）。

| 自治等級 | 呼叫 `:pause` 的條件 | 效果（邊界落點） | 之後建的審核項 `kind` |
|----------|----------------------|------------------|-----------------------|
| 1 Manual Confirm | `i < N` | 第 `i` 步完成後、第 `i+1` 步開始前停下 | `TASK_CONFIRM`（確認下一個任務）。第 1 個任務的確認＝使用者按「啟動執行」本身 |
| 2 Goal Confirm | `i` 是所屬目標的最後一步且 `i < N` | 該目標完成後、下一個目標開始前停下 | `GOAL_CONFIRM`（確認下一個目標） |
| 3 Review & Approve（預設） | 同等級 2 | 同等級 2 | `GOAL_COMPLETED`（審核剛完成的目標）；任務失敗另見 3.6.2 |
| 4 Exception Only | 不 pause | — | 只有失敗時（3.6.2） |
| 5 Full Autonomy | 不 pause | — | 只有致命失敗（3.6.2） |
| 6～10 Advanced | 不 pause；等級照常記錄在 `execution_runs.autonomy_level`，**不另送引擎設定**（`enableAutoMutation`／`enableSelfEvolution` 為 `UNVERIFIED`） | — | 同等級 5 |

- 最後一個步驟（`i = N`）完成時 run 直接 `COMPLETED`，不暫停、不建審核項。
- **精度（Architecture §12 L-7）**：極短的步驟可能在 `:pause` 抵達前就越過邊界，暫停會晚一步生效。此時 `status PAUSED` 的位置不在預期的目標邊界；建審核項時以**實際位置**為準（`completedSteps=k`）：等級 1 照常 `TASK_CONFIRM`；等級 2／3 若 `k` 不是目標邊界則降級為 `TASK_CONFIRM`，`reason` 加註「（暫停點比預期晚一步）」。
- 使用者手動 `pause`、`TOKEN_BUDGET_EXCEEDED` 自動暫停造成的 `PAUSED` **不建審核項**（沒有待決的閘）。

#### 3.6.2 審核項建立（`review_requests`；`kind` 的 CHECK 沿用 V3 的四種）

| 觸發 | `kind` | `goalId` | `taskId` | 佐證 `stepId`（`execution_steps.id`） | `reason` 樣板 | `allowedDecisions` |
|------|--------|----------|----------|--------------------------------------|---------------|--------------------|
| 等級 1 的閘點 `status PAUSED` | `TASK_CONFIRM` | 下一個任務的目標 | 下一個任務 | 剛完成步驟的 `COMPLETED` 列 | `Level 1：請確認是否繼續執行任務「<任務名>」` | `APPROVE`、`REJECT` |
| 等級 2 的閘點 | `GOAL_CONFIRM` | 下一個目標 | 該目標第一個任務 | 剛完成目標最後一步的 `COMPLETED` 列 | `Level 2：請確認是否開始目標「<目標名>」` | `APPROVE`、`REJECT` |
| 等級 3 的閘點 | `GOAL_COMPLETED` | 剛完成的目標 | 其最後一個任務 | 該步 `COMPLETED` 列 | `目標「<目標名>」已完成，等待人類審核` | `APPROVE`、`REJECT`、`RETRY` |
| `status FAILED` 且 `reason` 以「引擎升級（ESCALATION）」開頭（**等級 1～4**） | `ESCALATED` | 失敗任務的目標 | 失敗任務 | 該任務的 `FAILED` 列 | `任務「<任務名>」重試 <n> 次仍失敗，需要人類介入：<引擎 reason>`（`<n>`＝`FAILED` 列的 `attempt`−1）；若同時觸發 `CONSECUTIVE_FAILURES` 另附 `（連續 <n> 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）` | `RETRY`、`SKIP`、`REJECT` |
| `status FAILED`（**等級 ≥ 5**，任何原因） | `ESCALATED` | 同上（找不到失敗任務則 null） | 同上（找不到則 null） | 同上 | 引擎升級時同上；否則 `執行失敗：<引擎 reason>` | 有 `taskId`：`RETRY`、`SKIP`、`REJECT`；無：`RETRY`、`REJECT` |

等級 1～4 遇到**非升級**的失敗（halt、異常、orphaned）不建審核項（只有 `status-change`、`alert` 與 FAILED 狀態可見）——這是 W3 任務書的字面規則；等級 5 與以上因引擎沒有「替代方案」能力，Console 行為與等級 4 相同，只是任何失敗都會建審核項（§6 D-18）。建立審核項時寫入 `event_seq`／`event_sub`（§2.2）並發 SSE `review-request`；`status` 初值 `PENDING`。

#### 3.6.3 審核決定的動作（`POST /executions/{runId}/review/{stepId}`）

| `kind` | `APPROVE` | `REJECT` | `RETRY` | `SKIP` |
|--------|-----------|----------|---------|--------|
| `TASK_CONFIRM` | Bridge `:resume`（run 須 `PAUSED`）→ 審核項 `APPROVED` | `:stop`→run `CANCELLED`（系統重設同 cancel）→ `REJECTED` | ✗ | ✗ |
| `GOAL_CONFIRM` | `:resume` | `:stop`→`CANCELLED` | ✗ | ✗ |
| `GOAL_COMPLETED` | `:resume` | `:stop`→`CANCELLED`，該目標設為 `FAILED` | **restore** 到 `stepIdx` ＝「該目標第一個步驟的位置−1」的 checkpoint（＝該目標第一步之前的快照）；任務重設為 `QUEUED`、`retry_count+1`；`RETRIED` | ✗ |
| `ESCALATED` | ✗ | 關閉審核項（`REJECTED`）；run 維持 `FAILED`、任務維持 `ESCALATED`／`FAILED`、目標維持 `FAILED`；**不呼叫 Bridge** | **restore** 到 `stepIdx` ＝「失敗步驟位置−1」的 checkpoint（Bridge `restore` 接受終態 run，需重取鎖，可能 409）；失敗任務 `ESCALATED→QUEUED`、`retry_count+1`；`RETRIED`。沿用原 playbook（見 1.2.10 的注意） | 失敗任務設為 `SKIPPED`，並**以剔除它的新 playbook 開後續批次**（原因：Bridge `resume` 只收 `PAUSED`、`restore` 無法跳過步驟）；後續批次範圍＝專案內其餘非 `COMPLETED`／`SKIPPED` 任務，繼承原批次的自治等級與 `tokenBudget`／`limits`；回應標頭 `X-Follow-Up-Run-Id`；`SKIPPED` |

- 「步驟位置」指該批次 playbook 內的 1 起位置；checkpoint 以快照的 `step_idx`（0 起、＝還原後下一步）比對：要還原到位置 `p` 的步驟「之前」，取 `step_idx = p−1` 的快照。**找不到該快照（目標／失敗步驟是第一步，沒有更早的快照）**時，`RETRY` 改為：先 `:stop`（run 非終態時）、再開後續批次（範圍＝該目標／失敗任務及其後所有非完成任務），回應標頭 `X-Follow-Up-Run-Id`。
- 前置：gate 類的 `APPROVE`／`REJECT` 需 run 為 `PAUSED`；`ESCALATED` 類的 `RETRY`／`SKIP` 需 run 為終態（`FAILED`）。不符 → 409 `目前執行狀態不允許此操作`。
- 所有決定都寫 `decided_by`（JWT subject）、`decided_at`、`comment`；`REJECT` 於 ESCALATED 類不改變 run 狀態。審計日誌 `action=execution.review.<DECISION>`。
- 審核以外的操作（手動 resume／restore、cancel、run 進入終態、新批次建立）如何自動關閉待決審核項，見 §3.5.3 表的最後三列。

---

### 3.7 告警規則（`API-ALR-01～06`；由消費者在每則事件後與 30 秒排程 tick 評估）

閾值**每次評估時**讀系統參數（快取不超過 5 秒）。去重：同一 `(project, rule, subject)` 在**未確認**前不重複產生（DB partial unique index 兜底；`INSERT … ON CONFLICT DO NOTHING`，Console 規則告警只有真的新增才發 SSE）。`ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT` 同受此去重（同一步驟在未確認前再次升級不新增列），但 Bridge 的 `alert` 事件本身一律照常轉發 SSE。持久化欄位：`project_id`、`run_id`、`rule`、`severity`、`subject`、`message`、`event_seq`／`event_sub`。

| 規則（`rule`） | 嚴重度 | 輸入 | 閾值來源 | 判定 | `subject` | 動作 | 訊息樣板 |
|----------------|--------|------|----------|------|-----------|------|----------|
| `TOKEN_BUDGET_WARNING` | WARNING | `token` 事件的累計 `tokens_used`、批次 `tokenBudget` | `execution.tokenBudgetWarningThreshold`（0.8） | `tokenBudget` 非 null 且 `used ≥ budget × 閾值` | `run:<runId>` | 持久化＋SSE | `Token 使用量已達預算的 <pct>%（<used> / <budget>）` |
| `TOKEN_BUDGET_EXCEEDED` | CRITICAL | 同上；另含 `scope.limits.taskTokens`／`goalTokens` 對該任務／目標的歸因累計 | — | `used > budget`；或任務累計 > `taskTokens`；或目標累計 > `goalTokens` | `run:<runId>`／`task:<taskId>`／`goal:<goalId>` | 持久化＋SSE＋**`:pause`**（Bridge 狀態為 `RUNNING` 時；不建審核項，使用者以 resume 或 cancel 處置） | `Token 使用量已超出預算（<used> / <budget>），已要求暫停執行`；限額版：`任務「<名>」Token 用量 <n> 超過上限 <limit>，已要求暫停執行` |
| `CONSECUTIVE_FAILURES` | CRITICAL | 該目標下任務的終局結果序列（依其終局步驟時間；`COMPLETED` 為成功、`FAILED`／`ESCALATED` 為失敗、`SKIPPED` 略過） | `monitor.alertConsecutiveFailures`（3） | 最近 N 個終局結果全是失敗（在 `status FAILED` 與 `step FAILED` 處理後評估） | `goal:<goalId>` | 持久化＋SSE；Bridge 狀態仍為 `RUNNING` 才 `:pause`（Bridge 只能暫停整個 run；實務上首個 ESCALATION 已讓 run 結束，此規則在跨後續批次累計時才會觸發）；在該次 ESCALATED 審核項的 `reason` 註明 | `目標「<名>」連續 <n> 個任務失敗` |
| `AGENT_UNRESPONSIVE` | CRITICAL | 最後一則 Bridge 事件時間、`/health` 探測環 | `monitor.alertAgentTimeoutSec`（300） | run 為 `RUNNING／PAUSING／CANCELLING`，且 `現在−最後事件時間 > 閾值`，**且**最近一次探測失敗（或 Bridge 不可達）；單純長步驟（探測正常）不告警 | `run:<runId>` | 持久化＋SSE（不自動動作） | `Agent 已超過 <sec> 秒無回應` |
| `TASK_DURATION_EXCEEDED` | WARNING | `RUNNING` 任務的已執行時間（現在−`started_at`）；亦在 `COMPLETED` 時以實際耗時再評估一次 | `agent.taskTimeout` × `monitor.alertTaskDurationMultiplier`（600 × 2.0＝1,200 秒） | `耗時 > 閾值` | `task:<taskId>` | 持久化＋SSE | `任務「<名>」已執行 <sec> 秒，超過門檻 <threshold> 秒（<倍數> 倍）` |
| `HIGH_RETRY_RATE` | WARNING | 該目標在本批次已開始的任務與其中發生過 `RETRYING` 的任務 | 固定 50%（PRD；最小樣本 2 個已開始的任務） | `有重試的任務數 ÷ 已開始的任務數 > 0.5` | `goal:<goalId>` | 持久化＋SSE | `目標「<名>」重試率 <pct>%，超過 50%` |
| `ENGINE_ESCALATION` | CRITICAL | Bridge `alert`（`code=ESCALATION`） | — | 每則 | `step:<stepId>` | 持久化（`event_sub=0`）＋轉發 | `引擎升級（ESCALATION）：<detail>` |
| `ENGINE_TOKEN_HALT` | WARNING | Bridge `alert`（`code=TOKEN_HALT`） | — | 每則 | `step:<stepId>`（無則 `run:<runId>`） | 持久化＋轉發 | `引擎因 Token／額度門檻停機：<detail>` |

其餘 Bridge `alert`（`LIMIT_RETRY`、`RESTORE`、`FORCE_KILL`、`CONFIG_OVERRIDE_IGNORED`、`STEP_TRACKING_GAP`、`ENV_LOST`、`BRIDGE_INTERNAL`）只轉發 SSE、**不持久化**。百分比一律四捨五入到整數。

---

### 3.8 監控聚合公式

#### 3.8.1 KPI（`GET …/metrics`）

記號：視窗 `W=[from,to)`；前一視窗 `W'=[from−(to−from), from)`；範圍任務集合 `S`＝有 `runId` 時為該批次 `dag` 內的任務，否則為專案內全部未軟刪任務；「步驟列」＝`execution_steps` 中屬於 `S` 的列（`timestamp` 為 Bridge 寫入時間）。

| KPI | 公式 | `previousValue` |
|-----|------|-----------------|
| `taskCompletionRate` | `S` 中「在時點 `T` 之前已有 `COMPLETED` 步驟列」的相異任務數 ÷ `\|S\|` × 100；`value` 取 `T=to` | 取 `T=from` |
| `taskSuccessRate` | `C ÷ (C+F) × 100`，`C`＝`W` 內有 `COMPLETED` 列的相異任務數、`F`＝`W` 內有 `FAILED` 列的相異任務數；`C+F=0`→null | 同公式套 `W'` |
| `retryRate` | `W` 內有 `RETRYING` 列的相異任務數 ÷ `W` 內有 `STARTED` 列的相異任務數 × 100；分母 0→null | 同公式套 `W'` |
| `averageRetryCount` | `W` 內 `RETRYING` 列數 ÷ `W` 內有 `STARTED` 列的相異任務數（小數 2 位）；分母 0→null | 同公式套 `W'` |
| `totalTokens` | `run_token_samples.delta` 在 `W` 內之和（限範圍批次） | 套 `W'` |
| `averageTaskDurationSec` | `S` 中 `completed_at ∈ W` 且 `started_at` 非 null 的任務之 `completed_at−started_at` 平均（秒，小數 2 位）；無樣本→null | 套 `W'` |
| `tokenBudgetUsageRate` | 範圍批次中 `started_at < to` 者：`Σ total_tokens_used ÷ Σ token_budget × 100`（只算有預算的批次）；無預算→null | null |
| `projectCompletionRate` | 全域：`status=COMPLETED` 的專案數 ÷ 非 `ARCHIVED` 且未軟刪的專案數 × 100（現況，不隨視窗） | null |
| `goalAchievementRate` | 專案內 `COMPLETED` 目標數 ÷ 未軟刪目標數 × 100（有 `runId` 時限該批次範圍的目標；現況） | null |
| `agentAvailability` | `W` 內成功的健康探測數 ÷ 探測總數 × 100（探測環在記憶體，重啟即清空；視窗超出保留範圍就用現有樣本；沒有樣本→null） | null |

`delta`＝`value − previousValue`（兩者皆非 null 才有）。分布類欄位：`taskStatusDistribution`＝`S` 的 `tasks.status` 現況計數（十一態一律出現）；`taskDurations`＝`S` 中 `completed_at ∈ W` 的任務依耗時由長到短取 10 筆；`retryDistribution`＝`S` 中任務依 `retry_count`（現值，≥5 併入 5）分桶，桶 0～5 一律出現。

#### 3.8.2 趨勢

- **token-trend**：視窗內的 `run_token_samples` 依 `bucket`（UTC 整點或整日）分桶，`tokens`＝桶內 `delta` 之和，`cumulativeTokens`＝自 `from` 起累計；有資料的桶才輸出；`budget`＝樣本所屬批次的 `token_budget`（多批次取桶內最新批次）。
- **task-trend**：視窗內步驟列依 `bucket` 分桶，`started`／`completed`／`failed`／`retried`＝桶內 `STARTED`／`COMPLETED`／`FAILED`／`RETRYING` 列數；有資料的桶才輸出。

#### 3.8.3 日誌衍生（`GET …/logs`）

| 來源 | `id` | `source` | `level` | `message` | 時間 |
|------|------|----------|---------|-----------|------|
| `execution_steps` 列 | `step:<列 id>` | `STEP` | `STARTED`／`COMPLETED`→`INFO`；`RETRYING`→`WARN`；`FAILED`→`ERROR` | 同 §2.5 的 STEP 訊息（`COMPLETED` 不含 Token） | `timestamp` |
| `execution_runs` 開始 | `run:<runId>:started` | `RUN` | `INFO` | `Run #<n> 開始執行（自治等級 <L>）` | `started_at` |
| `execution_runs` 終態 | `run:<runId>:<status>` | `RUN` | `COMPLETED`→`INFO`、`CANCELLED`→`WARN`、`FAILED`→`ERROR` | `Run #<n> 已完成`／`已取消`／`失敗` | `completed_at` |
| `alerts` 列 | `alert:<id>` | `ALERT` | `WARNING`→`WARN`、`CRITICAL`→`ERROR` | 告警 `message` | `created_at` |
| `review_requests` 建立／決定 | `review:<id>:requested`／`review:<id>:decided` | `REVIEW` | `INFO` | `待審核：<reason>`／`審核 <決定>：<decided_by>` | `requested_at`／`decided_at` |

篩選：`level`（衍生等級，`ALL` 不篩）、`taskId`（只留帶該 `task_id` 的 STEP 列；RUN／ALERT／REVIEW 列在有 `taskId` 篩選時排除）、`q`（`message` 含關鍵字）、`runId`、`from`／`to`；穩定排序鍵＝`(timestamp, id)`（`order` 決定升降冪）。

---
## 4. 前端頁面 ↔ 端點矩陣

依據：設計稿 `Design_ConsoleUI/README.md` 畫面 6～9 與 `screenshots/06-import.png`～`09-settings.png`，並補上 PRD §5.2.5、§5.3.6、§5.4.5、§5.5.4 有、而設計稿沒畫的元素。表中「→」前是端點，「→」後是欄位。**Phase 1+2 已有的資料（專案名稱、目標清單、`signedOff` 旗標等）用 `Phase 2` 標示，不重列端點。**

### 4.1 匯入頁 `/import`（畫面 6）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| I-01 | 來源頁籤：上傳檔案／貼上文字／歷史記錄 | 純前端狀態 | 設計稿 README 文字提到「URL 之類」，**截圖只有這三個頁籤**；契約不提供 URL 匯入（§4.6 G-I1） |
| I-02 | 拖放區（.md／.pdf／.docx，10MB） | `POST /import/upload`（multipart `file`）→ `ImportRecordResponse.id/status` | 413／415／422 的 `reason` 顯示在拖放區下方（附錄 B） |
| I-03 | 貼上文字的文字區 | `POST /import/text`（`content`、`sourceType`）→ `ImportRecordResponse` | |
| I-04 | 自治等級下拉（Level 1～10） | `ParseOptions.autonomyLevel`；預設值 ← `GET /settings/agent`→`defaultAutonomyLevel` | |
| I-05 | 執行路徑輸入 | `ParseOptions.executionPath` | 無瀏覽按鈕（ADR-001 G-15）；絕對路徑格式驗證錯誤見 `errors[]` |
| I-06 | 補充說明文字區 | `ParseOptions.additionalPrompt`（≤4,000） | |
| I-07 | 「開始解析」按鈕與「解析中」畫面 | `POST /import/{id}/parse`（同步，最長約 `model.timeout` 秒） | 設計稿說明文字「套用有界閘：步驟 ≤24／Kahn 無環／prompt 非空」為靜態字串 |
| I-08 | 有界閘違規顯示（US-I-10） | parse／result 的 **422** → `errors[].gate／detail／location`（全部列出，不截斷） | 設計稿沒有這個錯誤區塊；須補一個清單元件（§4.6 G-I3） |
| I-09 | 規格被拒顯示 | 422 `SDD 規格檢查未通過` → `details.bridgeReason／detail` | 同上 |
| I-10 | 步驟 2 樹狀預覽（專案→目標→任務） | `ParseResultResponse.parsedResult`；重新整理後以 `GET /import/{id}` → `parsedResult` 還原 | |
| I-11 | 節點編輯（✏️）／刪除（🗑️）／新增目標／新增任務／拖曳排序 | 前端先改本地樹，儲存時 `PUT /import/{id}/result`（整樹覆寫） | 新增目標須自行產生 `key`；拖曳後 `dependsOn` 仍用 `key` 引用，不受順序影響；**編輯會撤銷 signoff**，UI 應提示 |
| I-12 | 解析提示（evaluator 被清空、通過標準為佔位） | `ParseResultResponse.warnings[]` | 設計稿沒有；建議用黃色提示列 |
| I-13 | 「signed_off=false」警示橫幅與「signoff 審批」按鈕 | `ParseResultResponse.signedOff`；按鈕 → `POST /import/{id}/signoff {approver}` | **approver 由前端以目前登入者帶入**（登入回應 `TokenResponse` 無 username：從 access token 的 `sub` 取，Phase 1+2 已如此） |
| I-14 | 已 signoff 綠勾 | `ImportRecordResponse.signedOff／signedOffBy／signedOffAt` | |
| I-15 | 「放棄」 | `POST /import/{id}/reject`（補充端點） | |
| I-16 | 「確認匯入」（未 signoff 時禁用） | `POST /import/{id}/confirm` → 201 `ProjectResponse`；成功後導向 `/projects/{id}` | 後端對未 signoff 回 409 `草案尚未 signoff，不可確認匯入`（前端禁用只是體驗） |
| I-17 | 歷史記錄列表：匯入時間、來源檔名、狀態、專案連結 | `GET /import?page&size&status&q` → `createdAt／sourceFileName／status／projectId` | 點一筆 → `GET /import/{id}` 重新開啟審核 |

### 4.2 執行頁 `/projects/[projectId]/execute`（畫面 7）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| E-01 | 標題「專案執行：{名稱}」 | Phase 2 `GET /projects/{id}` | |
| E-02 | 「執行已鎖定 — 草案未 signoff」橫幅＋「前往審批」 | Phase 2 `projectDetail.signedOff`；觸發 409 時另以 `details.unsignedGoalIds／unsignedTaskIds` 標示哪些未審批 | 啟動按鈕禁用邏輯＝專案、所選目標、所選任務皆 signedOff |
| E-03 | 自治等級下拉 | `StartExecutionRequest.autonomyLevel`（預設專案的 `autonomyLevel`） | |
| E-04 | Token 預算輸入（設計稿示例 100,000） | `StartExecutionRequest.tokenBudget`；預設值 ← `GET /settings/execution`→`globalTokenBudget`（種子 1,000,000） | 設計稿的 100,000 只是示例 |
| E-05 | 執行範圍 checkbox（目標＋「(N tasks)」） | Phase 2 `projectDetail.goals[]`（`name`、`taskCount`、`signedOff`）→ 勾選結果組成 `scope.mode=SELECTED, goalIds[]` | 全勾＝`mode=ALL`。任務層級選取（US-E-02「特定任務」）設計稿沒畫；契約支援 `scope.taskIds`（§4.6 G-E1） |
| E-06 | 「啟動執行」 | `POST /projects/{id}/execute` → 201 `ExecutionRunResponse` | 409／422 的 `reason`＋`details` 顯示（附錄 B） |
| E-07 | 「暫停」「恢復」「取消」 | `POST /executions/{runId}/pause｜resume｜cancel`；按鈕啟用規則看 `ExecutionRunDetailResponse.status` 與 `bridge.status`（`PAUSING`／`CANCELLING` 時顯示處理中、禁用） | |
| E-08 | 「從斷點恢復」 | `GET /executions/{runId}/checkpoints`（列表）→ 選一筆 → `POST /executions/{runId}/restore/{checkpointId}` | **設計稿沒有選擇斷點的對話框**（§4.6 G-E2）；列表欄位：`name`、`createdAt`、`completedSteps` |
| E-09 | 「Run #N」與狀態點（閃爍） | `ExecutionRunDetailResponse.runNumber／status`（`RUNNING` 閃爍）；即時更新 ← SSE `status-change` | |
| E-10 | 「x / y 任務完成」與進度條 | `completedSteps／totalSteps`；即時 ← SSE `progress-update.completedSteps／totalSteps／progressPct` | |
| E-11 | 「Token: 45,230 / 100,000」與進度條（超閾值變色） | `totalTokensUsed／tokenBudget`；即時 ← SSE `token-update.tokensUsed／budgetUsageRate`；變色閾值 ← `GET /settings/execution`→`tokenBudgetWarningThreshold`（預設 0.8）與 100% | |
| E-12 | 耗時（PRD 有、截圖未見） | `elapsedSec`；即時 ← SSE `metric-update.elapsedSec` | |
| E-13 | DAG 視覺化（G1→G2→G3、任務節點、展開／收合／全螢幕） | `GET /executions/{runId}/dag` → `nodes[].kind／label／status／goalId／sequence`、`edges[]`；即時更新節點狀態 ← SSE `log`（STEP）的 `taskId`＋`stepStatus` | 節點色票由前端依狀態表（`lib/domain/status.ts`）；展開／收合為前端狀態 |
| E-14 | 即時日誌（深色終端機）與「SSE 串流」狀態點 | SSE `/stream/executions/{runId}/logs` 的 `log`（`ts`、`level`、`message`）；狀態點＝客戶端連線狀態 | 預設顯示 `source=STEP`，另設「顯示引擎原始輸出」開關（`source=ENGINE` 量大）。重新載入頁面：`tail=200` 重播 |
| E-15 | 自動捲動、日誌搜尋 | 純前端（對已收到的行過濾） | |
| E-16 | 待審核項目卡：計數 badge、列標題 | `ExecutionRunDetailResponse.pendingReviews[]`（`reason`、`goalName`、`taskName`）；badge 計數與即時新增 ← SSE `review-request` | |
| E-17 | 每列按鈕：通過／重試／跳過／拒絕 | `POST /executions/{runId}/review/{review.id}`，`decision` ← 按鈕；**按鈕是否可按＝`review.allowedDecisions`** | 設計稿四顆按鈕對所有項目顯示；`ESCALATED` 無「通過」、gate 類無「跳過」→ 以 `allowedDecisions` 禁用 |
| E-18 | 「查看結果／查看日誌」「修改任務」（PRD） | 導向：任務詳情 `/projects/…/tasks/{taskId}`（Phase 2）＝`review.taskId` | |
| E-19 | 空狀態文字（無待審核項目） | `pendingReviews=[]` | |
| E-20 | 後續批次切換 | 審核 `SKIP`／`RETRY` 回 `X-Follow-Up-Run-Id`；或 `GET /projects/{id}/executions` 取最新一筆 | 前端收到標頭後改看該 run 並重連 SSE |

### 4.3 監控頁 `/projects/[projectId]/monitor`（畫面 8）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| M-01 | 時間範圍下拉（預設 24 小時） | 前端換算成 `from`／`to` 帶給每個監控端點 | |
| M-02 | 執行批次下拉（PRD §5.4.5 有、設計稿未畫） | `GET /projects/{id}/executions` → `runNumber／status` → `runId` 參數 | §4.6 G-M1 |
| M-03 | 指標卡「完成率」 | `GET …/metrics` → `taskCompletionRate.value／delta` | 設計稿「完成率 34.8%」＝專案內任務完成進度，**不是** PRD 的「專案完成率」（全域，`projectCompletionRate`） |
| M-04 | 指標卡「任務成功率」 | `taskSuccessRate.value／delta` | ↑／↓ 與顏色由前端依語意決定（成功率升＝好） |
| M-05 | 指標卡「重試率」 | `retryRate.value／delta` | 升＝壞；顏色由前端決定 |
| M-06 | 指標卡「Token 消耗」 | `totalTokens.value／delta` | |
| M-07 | PRD 另外六項 KPI（專案完成率、目標達成率、平均重試次數、Token 預算使用率、平均任務執行時間、Agent 可用率） | 同一個 `metrics` 回應的其餘 `MetricValue` | 設計稿只畫四張卡；其餘供 Dashboard 或日後版面（ADR-001 G-13） |
| M-08 | Token 使用趨勢（折線＋虛線預算線＋面積） | `GET …/token-trend` → `bucketStart／tokens／cumulativeTokens／budget`（折線畫 `cumulativeTokens`；預算線畫 `budget`） | 圖例「預算線／Token 使用」靜態 |
| M-09 | 任務狀態分佈（完成／執行中／失敗／待處理 四條） | `metrics.taskStatusDistribution`（前端分組：完成＝`COMPLETED`；執行中＝`RUNNING＋VALIDATING＋QUEUED`；失敗＝`FAILED＋ESCALATED`；待處理＝其餘） | |
| M-10 | 執行時間分佈（垂直柱） | `metrics.taskDurations[]` → `taskName／durationSec` | |
| M-11 | 任務執行趨勢、成功／失敗比率、重試次數分佈（PRD §5.4.2 趨勢圖表，設計稿未畫） | `GET …/task-trend`、`metrics.retryDistribution` | §4.6 G-M2 |
| M-12 | 事件時間軸（PRD，設計稿未畫） | `GET /executions/{runId}/steps`（`timestamp／status／taskName`；一個批次的步驟事件，`size` 最大 200，以 `afterSeq` 續頁） | §4.6 G-M2。`task-trend` 依 PRD §7.1.6 只回 `List<TaskTrendPoint>`（不含事件清單）；M-02 選「全部批次」時，時間軸取最新一筆批次（`executions` 列表第一筆）當來源 |
| M-13 | 執行日誌查詢卡：等級下拉（全部／INFO／WARN／ERROR）、日誌列 | `GET …/logs?level&q&page&size` → `timestamp／level／message` | PRD 另有關鍵字搜尋（`q`）、任務 id 篩選（`taskId`）；設計稿只畫等級下拉 |
| M-14 | 告警卡：列、「已確認」或「確認」 | `GET …/alerts` → `createdAt／message／severity／acknowledged`；確認 → `POST /monitor/alerts/{id}/acknowledge`（204） | 即時新增 ← SSE `alert`（執行頁／監控頁皆可訂閱同一 run） |
| M-15 | 「查看詳情」（PRD） | 無專用端點：展開該列顯示 `rule／subject／runId／message` | |
| M-16 | 「匯出報表」 | `GET …/report?format=csv`（檔案下載；`Accept: text/csv`） | PDF 回 501（W5） |
| M-17 | 「設定告警」 | 導向 `/settings` 的「監控」分頁（`monitor.*`） | 無專用端點 |
| M-18 | 「自訂儀表板」（US-M-08） | 純前端（版面存 `localStorage`，ADR-001 G-18） | 無後端欄位 |
| M-19 | Agent 狀態指示燈（US-M-10；設計稿未畫） | `metrics.agentAvailability`；即時連線 ← `GET /executions/{runId}`→`bridge.connected／status`、`currentStep` | 「資源使用情況（CPU／記憶體）」Bridge 契約沒有此資料（ADR-001 G-18） |

### 4.4 設定頁 `/settings`（畫面 9）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| S-01 | 分類頁籤（模型／Agent／執行／監控／AutoClaude／SDD） | `GET /settings` 的六個 key | 頁籤文字與圖示由前端字典提供 |
| S-02 | 每個參數列：label、說明 | **label**：前端字典（鍵 `category.key`；契約不含）；**說明**：`ConfigResponse.description` | §4.6 G-S1 |
| S-03 | 控制項型別（text／number／password／enum／bool） | `valueType`：`STRING`→text、`INTEGER／LONG／FLOAT`→number、`ENCRYPTED`→password、`ENUM`→enum（選項＝`options`）、`BOOLEAN`→bool；數字範圍＝`min`／`max` | |
| S-04 | 值與預設值 | `value／defaultValue`；重置圖示 → `POST /settings/{category}/{key}/reset` | 加密鍵重置需 `?confirm=true` |
| S-05 | 密碼欄遮罩與顯示切換 | 預設 `value=••••••••`＋`hasValue`；顯示 → `GET /settings/{category}?reveal=true`（**僅 ADMIN**） | 非 ADMIN 時切換按鈕應禁用（設計稿未畫角色差異，§4.6 G-S2） |
| S-06 | 驗證錯誤紅字 | 400 `errors[].field／message`；token_guard 違規見 reason `halt_threshold_pct 必須大於 compact_threshold_pct` | 前端以 zod 鏡射同規則（NFR-SEC-05 第 ③ 道） |
| S-07 | 「測試連線」與結果（連線成功（延遲 230ms）） | `POST /settings/test-connection`（可帶表單內尚未儲存的 `apiUrl`／`apiKey`）→ `success／latencyMs／message` | 422（SSRF／allowlist）顯示 reason 與 `details.violation` |
| S-08 | 修改歷史卡（時間／參數／舊值→新值／@使用者） | `GET /settings/history?category&page&size` → `changedAt／category.key／oldValue／newValue／changedBy` | 加密值顯示 `••••••••` |
| S-09 | 「儲存變更」 | **逐鍵** `PUT /settings/{category}/{key}`（僅送有修改的鍵）；token_guard 兩鍵都改 → 改用 `PUT /settings/execution/token-guard`（原子） | 沒有單一的批次儲存端點；PRD 的「修改後立即儲存」也可逐欄儲存 |
| S-10 | 「全部重置為預設值」 | `POST /settings/{category}/reset`（補充端點；整個分類） | |
| S-11 | 「匯出設定」「匯入設定」 | `POST /settings/export`（下載 JSON）；`POST /settings/import`（multipart）→ `applied／skipped／errors[]` | |
| S-12 | 影響範圍提示（US-S-08） | `ConfigResponse.impactNote`：寫入前的確認對話框顯示 | |
| S-13 | 「僅儲存、不影響引擎」標示（設計稿未畫） | `ConfigResponse.effect=STORED_ONLY／UNVERIFIED` | 建議在 label 旁加小標籤（誠實呈現，Architecture §11.4） |
| S-14 | 敏感參數二次確認（US-S-02） | 第一次 `PUT` 不帶 `confirm` → 409 `敏感參數更新需二次確認（confirm=true）`；使用者確認後帶 `confirm=true` 重送 | 或前端先彈窗再直接帶 `confirm=true` |

### 4.5 全域元素（Phase 3～6 相關）

| # | UI 元素 | 資料來源 | 備註 |
|---|---------|----------|------|
| G-01 | 頂列通知鈴紅點數字 | `GET /notifications/summary` → `pendingReviews＋unacknowledgedAlerts`（前端加總） | 輪詢間隔 ≥ `monitor.refreshIntervalMs`、不小於 3 秒 |
| G-02 | signoff 佇列徽章 | `summary.pendingSignoffs` | |
| G-03 | 頂列「Engine Bridge · 已連線」綠點 | `summary.bridgeConnected／bridgeCheckedAt`（最近一次健康探測結果；從未探測為 null） | 契約補此二欄是因為沒有其他全域來源；`/actuator/health` 只代表 console-api 自己 |
| G-04 | 頂列使用者徽章 | 登入者名稱 ← access token 的 `sub`（Phase 1+2） | |
| G-05 | 搜尋列「搜尋專案、目標、任務…」 | Phase 2 `GET /projects?q=`（只搜專案名稱） | PRD §7 沒有跨目標／任務的搜尋端點（§4.6 G-G1） |
| G-06 | Dashboard「待審批草案數」 | `summary.pendingSignoffs`（跨專案、含目標與任務層級，§1.4.1） | 取代 Phase 2 前端只算專案與草案目標的近似值（ADR-002 已知限制） |
| G-07 | Dashboard「執行中 run 數」「進行中的執行」卡 | Phase 2 `GET /projects?status=EXECUTING` 的 `totalElements`；每個執行中專案再 `GET /projects/{id}/executions?size=1` 取最新批次的 `tasksCompleted／tasksTotal` 畫進度條 | 沒有全域 run 端點；一個專案同時只會有一個 `EXECUTING` 批次。已暫停的批次其專案為 `READY`，不計入「執行中」 |
| G-08 | Dashboard「本週完成任務數」 | 無全域端點（§4.6 G-G3） | 建議值見該列 |

### 4.6 設計稿元素在契約裡沒有資料來源（或需補設計）

| 編號 | 元素 | 狀態 | 建議處置 |
|------|------|------|----------|
| G-I1 | 匯入「URL」來源頁籤（README 文字） | 契約無 URL 匯入 | 不做；以截圖（上傳／貼上／歷史）為準 |
| G-I2 | 路徑「瀏覽按鈕」（PRD US-I-05） | 無（ADR-001 G-15） | 以路徑輸入＋Bridge allowlist 取代 |
| G-I3 | 有界閘違規清單、解析警告列 | 設計稿沒畫，但資料齊備（§4.1 I-08、I-12） | 前端補元件（錯誤清單：閘別徽章＋位置＋原因） |
| G-E1 | 任務層級的執行範圍選取 | 契約支援，設計稿只有目標層級 | 先做目標層級；任務層級列入 W4 增強 |
| G-E2 | 「從斷點恢復」的斷點選擇對話框 | 資料齊備，設計稿沒畫 | 前端補對話框（列表＋確認） |
| G-E3 | 後續批次（follow-up run）切換 | 契約以 `X-Follow-Up-Run-Id` 與 `executions` 列表表達 | 前端處理標頭並重連 SSE |
| G-M1 | 監控頁「執行批次」下拉 | PRD §5.4.5 有、設計稿沒畫；資料齊備（`executions`＋`runId`） | 建議補（US-M-06 需要） |
| G-M2 | 事件時間軸、任務趨勢／成功失敗比率／重試分佈圖 | 資料齊備（`steps`、`task-trend`、`retryDistribution`），設計稿沒畫 | 依 PRD §5.4.2 補圖或列為後續 |
| G-M3 | 「資源使用情況」（CPU／記憶體） | **Bridge 無此資料**（ADR-001 G-18） | 不做；以連線、目前任務、Token 與步驟進度呈現 |
| G-S1 | 參數 label 的中文名稱 | 契約只給 `description` | 前端字典（50 鍵；附錄 C 的鍵名即索引） |
| G-S2 | 非 ADMIN 角色的唯讀呈現（輸入框、儲存、顯示切換、測試連線） | 設計稿未畫角色差異；契約 403 | 前端依角色禁用控制項（角色取自登入回應 `role`） |
| G-G1 | 全域搜尋跨目標／任務 | PRD §7 沒有端點 | 超出 Phase 3～6；目前只搜專案 |
| G-G2 | 頂列「通知總覽」連結頁 | 無對應頁面與端點 | 暫以通知鈴的計數取代，不做列表頁 |
| G-G3 | Dashboard「本週完成任務數」（跨專案） | 沒有全域聚合端點（`metrics`／`task-trend` 都以單一專案為範圍） | 建議預設：前端對每個非封存專案呼叫 `task-trend?from=<本週一 00:00>&bucket=DAY`，加總各桶 `completed`（同一任務被還原重跑會重複計，屬近似值）；專案數多時另開全域端點列入 W5 |

---
## 5. E2E 情境（QA 與兩位開發者共用；全部以 `aisdlc-mock-claude` 為 Claude 替身，結果可決定）

### 5.0 共用夾具與斷言慣例

#### 5.0.1 環境

| 元件 | 設定 |
|------|------|
| PostgreSQL | `pgvector/pgvector:pg18`（Testcontainers 或 compose）；Flyway 套用 V1～V7 |
| Engine Bridge（真行程） | `uvicorn app.main:app --port 18081`（Windows 用 `.venv\Scripts\uvicorn.exe`）；環境變數：`BRIDGE_DB_DSN`（同一個 DB）、`BRIDGE_DB_SCHEMA=console`、`ENGINE_WORKSPACE=<E2E_ROOT>/workspace`、`BRIDGE_ALLOWED_PATH_ROOTS=<E2E_ROOT>`（多個以 `os.pathsep` 分隔）、`BRIDGE_OUTBOUND_ALLOWLIST=127.0.0.1,localhost`、`BRIDGE_STOP_GRACE_SECONDS=5`、`BRIDGE_INSTANCE=e2e-bridge`；**單一 worker** |
| WireMock | 假 OpenAI 相容端點（`<WM_PORT>`）：`POST /v1/chat/completions`、`GET /v1/models`（可由任何能依路徑與請求本文標記回應的假伺服器取代，例如 Python `http.server`；路徑一律是這兩條） |
| console-api（profile `e2e`） | `ENGINE_BRIDGE_URL=http://127.0.0.1:18081`；`console.security.outbound-allowlist=127.0.0.1,localhost,rebind.e2e.test`；`console.security.test-dns-overrides={rebind.e2e.test: 10.0.0.5}`；`console.security.rate-limit.enabled=true`；`console.security.rate-limit.trust-forwarded-for=true`；`console.sse.keep-alive-seconds=2`；`console.execution.mock-env={MOCK_CLAUDE_DELAY: "0.6", MOCK_CLAUDE_FAIL_REGEX: "\\[FAIL_ME\\]", MOCK_CLAUDE_TRACE: "<E2E_ROOT>/mock-trace.jsonl"}`；`CONSOLE_ENCRYPTION_KEY`、`JWT_SECRET` 為測試值 |
| 帳號 | `admin`／`operator`／`viewer`（backend README 的三組內建帳號） |

`<E2E_ROOT>` 是測試建立的暫存根目錄（不寫死磁碟路徑）；每個專案的 `executionPath` 是其下已存在的空目錄。

#### 5.0.2 系統參數前置（admin 以 `PUT /settings/{category}/{key}` 設定；情境前執行一次）

| 鍵 | 值 | 目的 |
|----|----|------|
| `autoclaude.claudeCommand` | `aisdlc-mock-claude` | 引擎用替身（非真 Claude） |
| `execution.autoResume` | `false` | 避免 Token halt 時引擎自己長時間等待 |
| `agent.maxRetries` | `1` | 失敗步驟只重試一次（STARTED→RETRYING→FAILED） |
| `model.apiUrl` | `http://127.0.0.1:<WM_PORT>` | 匯入路徑 B 的假模型（e2e allowlist 放行） |
| `model.apiKey` | `sk-e2e-dummy`（`confirm=true`） | 同上；設定後 execute 會帶 `minimax.*` 與 `MINIMAX_API_KEY`，對 mock 流程無影響 |
| `model.name`／`model.timeout` | `e2e-model`／`30` | |

#### 5.0.3 固定夾具與替身常數

- **夾具專案**（每個情境各建一份獨立的，名稱含情境編號，路徑各自一個子目錄）以 Phase 2 REST 手動建立（手動建立即 `signedOff=true`；E2E-02 例外用 `draft:true`）：
  - **PRJ-A**（3 任務）：`G1「基礎」`（sortOrder 0）含 `T1「初始化」`、`T2「設定」`；`G2「核心」`（sortOrder 1，`dependsOn=[G1]`）含 `T3「實作」`。每個任務 `description`＝`請輸出 [T<n>_DONE]`、`passCriteria`＝`輸出含 [T<n>_DONE]`、`expectedOutputRegex`＝`\[T<n>_DONE\]`、`maxRetries=1`。專案 `autonomyLevel=4`。
  - **PRJ-B**（5 任務）：`G1` 含 `T1、T2、T3`；`G2`（依賴 G1）含 `T4、T5`；其餘同 PRJ-A。
  - **任務數須 ≤ 5**：引擎預設 `auto_compact_interval=5`，超過會多一次 `/compact` 呼叫而改變 Token 帳。
- **mock claude 的行為（已對 `app/mock_claude.py` 核對）**：每次呼叫回放 prompt 內所有 `[KEYWORD]`；用量固定 `input=1200`、`output=40`（**每個 attempt 1,240 Token**；context% ＝ 0.6）；延遲 0.6 秒；prompt 命中 `\[FAIL_ME\]` 時不輸出任何關鍵字（evaluator 判失敗）。因此**任務 `description` 含 `[FAIL_ME]` 就會失敗**，不含就成功。
- **Token 帳**：一個成功的步驟 ＝ 1 個 attempt ＝ 1,240；失敗步驟（`maxRetries=1`）＝ 2 個 attempt ＝ 2,480。被 pause 中止、從未回傳的 spawn 不產生 token 事件。
- **step_id**：依 §3.4.4，PRJ-A 全範圍為 `G1-T1`、`G1-T2`、`G2-T1`（T1、T2、T3）。

#### 5.0.4 斷言慣例與共通後置斷言

- 等待狀態轉換一律輪詢（逾時 60 秒），不用固定 sleep；SSE 斷言比對**事件子序列與欄位**，不比對引擎原始 `log` 行數；Token、步驟數、狀態、reason 字串一律精確比對。
- **限流桶隔離**：e2e 環境所有請求都來自同一個連線位址，而限流是每個 IP 每分鐘 100 次；每個情境的 HTTP client 一律帶自己的 `X-Forwarded-For: 198.51.100.<情境編號>`（e2e profile 信任該標頭），否則多個情境（含輪詢）共用同一個桶而誤判 429。E2E-11 自行設定其標頭。
- **每個涉及 run 的情境結束時都驗**：(A1) DB `execution_runs.status` ＝ Bridge `GET /autoclaude/runs/{id}` 的狀態折疊值，`total_tokens_used` 相等（NFR-OBS-01）；(A2) 每個非 2xx 回應都是 `ApiError` 封包且 `traceId` 等於 `X-Trace-Id`；(A3) 整段測試的 console-api 日誌沒有「未預期的例外」（500）；(A4) 任一 SSE 連線的 id 依 `(seq,n)` 嚴格遞增、無重複；(A5) 任何回應與日誌都不含 API 金鑰明文（除 `reveal=true` 回應）。
- 下列 HTTP 簡寫：`POST execute` ＝ `POST /api/v1/projects/{projectId}/execute`；`GET run` ＝ `GET /api/v1/executions/{runId}`。

---

### E2E-01　匯入貼文字（路徑 B）→ 編輯 → signoff → confirm → 專案全部 signedOff　〔API-IMP-01～10、SGN-01／US-I-01～05、07～10／NFR-SEC-04〕

**前置**：operator；§5.0.2 的模型參數已設；WireMock stub **S-OK**（請求本文含 `需求文件內容`、無其他標記時）回 200：

```json
{ "id":"chatcmpl-e2e", "object":"chat.completion", "model":"e2e-model",
  "choices":[{ "index":0, "finish_reason":"stop", "message":{ "role":"assistant", "content":
    "{\"project\":{\"name\":\"E2E 匯入專案\",\"executionPath\":\"/ignored\",\"passCriteria\":\"三個目標全部完成\",\"description\":\"由 BRD 匯入\"},\"goals\":[{\"key\":\"g1\",\"name\":\"基礎\",\"description\":\"\",\"passCriteria\":\"基礎任務完成\",\"sortOrder\":0,\"dependsOn\":[],\"tasks\":[{\"name\":\"初始化\",\"description\":\"請輸出 [T1_DONE]\",\"passCriteria\":\"輸出含 [T1_DONE]\",\"sortOrder\":0},{\"name\":\"設定\",\"description\":\"請輸出 [T2_DONE]\",\"passCriteria\":\"輸出含 [T2_DONE]\",\"sortOrder\":1}]},{\"key\":\"g2\",\"name\":\"核心\",\"description\":\"\",\"passCriteria\":\"核心任務完成\",\"sortOrder\":1,\"dependsOn\":[\"g1\"],\"tasks\":[{\"name\":\"實作\",\"description\":\"請輸出 [T3_DONE]\",\"passCriteria\":\"輸出含 [T3_DONE]\",\"sortOrder\":0}]}]}" } }],
  "usage":{ "prompt_tokens":812, "completion_tokens":340, "total_tokens":1152 } }
```

**主流程**（文件內容：以 `# BRD` 與兩個 `##` 標題開頭、≥ 200 字元的 Markdown，確保走路徑 B 而非 C）：

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST /import/text` `{content, sourceFileName:"e2e-brd.md", sourceType:"MARKDOWN"}` | **201**；`status=UPLOADED`、`signedOff=false`、`sourceType=MARKDOWN` |
| 2 | `POST /import/{id}/parse` `{autonomyLevel:3, executionPath:"<E2E_ROOT>/proj-import", additionalPrompt:"盡量少於 5 個任務"}` | **200**；`status=PARSED`、`path=LLM`、`aiModel=e2e-model`、`tokenUsed=1152`、`signedOff=false`、`errors=[]`、`warnings=[]`；`parsedResult.goals` 2 個（g1 任務 2、g2 任務 1）、`goals[1].dependsOn=["g1"]`；`project.executionPath` ＝請求值（LLM 的 `/ignored` 被丟棄）。**WireMock 驗證**：收到 1 次請求，標頭 `Authorization: Bearer sk-e2e-dummy`；本文 `model=e2e-model`、`stream=false`、`response_format.type=json_object`；`messages[0].role=system`；`messages[1].content` 含 `自治等級: 3`、`補充說明: 盡量少於 5 個任務` 與文件原文 |
| 3 | `GET /import/{id}` | **200**；含 `sourceContent` 與與步驟 2 相同的 `parsedResult` |
| 4 | `PUT /import/{id}/result`：把 g1 改名「基礎建設」、在 g2 新增任務 T4（`請輸出 [T4_DONE]`） | **200**；`status=REVIEWING`、`signedOff=false`；goals／tasks 順序與 `sortOrder`（0 起連續）依陣列重編 |
| 5 | `POST /import/{id}/confirm`（尚未 signoff） | **409**；`reason=草案尚未 signoff，不可確認匯入`；`GET /projects?q=E2E 匯入專案` 的 `totalElements=0` |
| 6 | `POST /import/{id}/signoff` `{approver:"  "}` | **400**；`errors[0].field=approver` |
| 7 | `POST /import/{id}/signoff` `{approver:"e2e-approver"}` | **200**；`signedOff=true`、`signedOffBy=e2e-approver`、`signedOffAt` 非 null |
| 8 | 再次 `signoff` | **409**；`reason=已 signoff`；`details.signedOffBy=e2e-approver` |
| 9 | `PUT result`（同一棵樹、改一個任務描述） | **200**；`signedOff=false`（**編輯撤銷 signoff**）；`GET /import/{id}` 的 `signedOffBy=null` |
| 10 | 重新 `signoff` `{approver:"e2e-approver"}` | **200** |
| 11 | `POST /import/{id}/confirm` | **201**：`signedOff=true`、`signedOffBy=e2e-approver`、`status=DRAFT`、`goalsCount=2`、`tasksCount=4`、`autonomyLevel=3`、`executionPath=<E2E_ROOT>/proj-import`、`name=E2E 匯入專案`、`createdBy=operator` |
| 12 | Phase 2 讀取：`GET /projects/{pid}/goals`、`GET /goals/{g2}`、`GET /goals/{g}/tasks` | 兩個目標皆 `signedOff=true`、`signedOffBy=e2e-approver`；g2 的 `dependsOn=[g1 的 id]`；四個任務皆 `signedOff=true`；DB：專案／目標／任務的 `signed_off_at` 與匯入記錄的 `signed_off_at` 相同 |
| 13 | `GET /import/{id}` | `status=IMPORTED`、`projectId=pid`；再次 `confirm` → **409** `已匯入`（`details.projectId`）；`reject` → **409** `匯入記錄狀態不允許此操作`（`details.action=reject`） |
| 14 | `GET /import?status=IMPORTED&sort=createdAt,desc` | 含此筆，`projectId` 已回填 |
| 15 | 角色：viewer `POST /import/text` → **403**（`ACCESS_DENIED`）；viewer `GET /import` → **200**；operator `PUT /settings/…` 不在此情境 | |

**有界閘變體**（各用一筆新記錄與下列文件標記，WireMock 依請求本文含的標記回不同 stub；每筆 parse 都預期 **422**、`reason=解析結果未通過有界閘`、記錄 `status=UPLOADED`、`GET /import/{id}` 的 `lastParseErrors` 非空；之後改用正常文件重新 parse → 200 且 `lastParseErrors` 清空）：

| 文件標記 | stub 回應的樹 | `errors` 預期（`gate`＋`location`） |
|----------|---------------|-------------------------------------|
| `GATE_MAX` | 一個目標含 25 個任務 | `max_steps`＋`goals[0].tasks`；`detail` 含 `25` 與 `24` |
| `GATE_CYCLE` | g1 依賴 g2、g2 依賴 g1 | `cycle`＋`goals[0].dependsOn`；`detail` 含 `->` |
| `GATE_EMPTY` | 第二個任務 `description` 為 `"  "` | `empty_prompt`＋`goals[0].tasks[1].description` |
| `GATE_LONG` | 一個任務 `description` 長 20,500 字元 | `prompt_too_long`＋`goals[0].tasks[0]` |
| `GATE_MULTI` | 25 個任務且其中一個描述為空 | **兩項**，順序 `empty_prompt`、`max_steps`（§3.3.5 的固定順序） |
| `GATE_BADJSON` | `content` 為 `not json` | `brain_failed`（無 `location`） |
| `GATE_HTTP500` | stub 回 HTTP 500 | `brain_failed`；`detail` 含 `500`，不含金鑰 |
| （先清空 `model.apiKey`） | — | `brain_unsupported`；`detail` 含 `model.apiKey` |

**消毒變體（NFR-SEC-03）**：對 REVIEWING 狀態的記錄 `PUT result`，把某任務 `evaluatorCommand` 設為 `pytest -q; echo done`（含 `;`）→ **400**，`reason=命令含禁用字元`，`details.violations` 列出 `;`；`expectedOutputRegex` 設為 `([` → **400**（無法編譯）；改為合法值 `pytest -q` 與 `\[T1_DONE\]` → **200**。

**上傳變體**：小的 `.md` 檔 → **201**（`sourceType=MARKDOWN`）；`.txt` → **415**（`只支援 .md／.pdf／.docx 檔案`）；11MB 檔 → **413**（`檔案超過 10MB 上限`）；內容為 `hello` 但副檔名 `.pdf` → **422**（`檔案內容與副檔名不符`）；空檔 → **400**（`檔案是空的`）；viewer 上傳 → **403**。

**不在本 E2E 的範圍**：路徑 A（SDD）與 C（decompose）以「WireMock 假 Bridge」的後端整合測試覆蓋——Bridge 的 decompose 需要 `MINIMAX_API_KEY` 與真 Brain，而 `mock_brain_server.py` 不支援拆解（ADR-001 D9）。

---

### E2E-02　execute 未 signoff → 409　〔API-EXE-11／US-E-01〕

**前置**：operator；以 `draft:true` 建立 PRJ-U（3 任務，專案、目標、任務皆 `signedOff=false`）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{}` | **409**；`reason=未經人工審批的草案不可執行`；`message=草案未經人工審批，禁止執行`；`details.unsignedProjectId`＝專案 id，`unsignedGoalIds`＝兩個目標 id，`unsignedTaskIds`＝三個任務 id |
| 2 | 檢查沒有副作用 | `GET /projects/{id}/executions` 的 `totalElements=0`；專案 `status=DRAFT`；DB `execution_runs` 無此專案的列；Bridge workspace 沒有新的 run 目錄 |
| 3 | 只 signoff 專案後 `POST execute` | **409**；`unsignedProjectId=null`；目標、任務清單仍在 |
| 4 | 再 signoff 兩個目標與其中兩個任務後 `POST execute` | **409**；`unsignedGoalIds=[]`、`unsignedTaskIds` 只含第三個任務 |
| 5 | `POST execute` `{scope:{mode:"SELECTED", goalIds:[<他專案的目標 id>]}}`（仍有未 signoff） | **409**（檢查順序：未 signoff 先於範圍檢查）；全部 signoff 後同一請求 → **400** `所選範圍不合法`（`details.invalidGoalIds`） |
| 6 | signoff 第三個任務後 `POST execute` `{autonomyLevel:4}` | **201**；專案 `status=EXECUTING`（`DRAFT` 經內部 `READY`）；隨即 `POST cancel` → **200** 收尾 |
| 7 | 在 EXECUTING 期間再 `POST execute` | **409**；`reason=專案正在執行中`；`details.runId`＝步驟 6 的 run |
| 8 | 角色與參數：viewer `POST execute` → **403**；不存在的專案 → **404**；`autonomyLevel:11` → **400**；`scope:{mode:"ALL", goalIds:[…]}` → **400** | |

---

### E2E-03　execute 成功 → SSE 收到 step 事件 → Task／run COMPLETED → metrics 對得上　〔API-EXE-01、05～08、MON-01～06、SSE-01／US-E-01、03、09、11、M-01～04〕

**前置**：PRJ-A（新）；operator；SSE 用 `?access_token=`（operator 的 access token）。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4, tokenBudget:100000, scope:{mode:"ALL"}}` | **201**；`runNumber=1`、`status=RUNNING`、`bridgeStatus=RUNNING`、`tokenBudget=100000`、`totalTokensUsed=0`、`scope.mode=ALL` |
| 2 | Phase 2 讀取（可能與引擎啟動競速） | 專案 `status=EXECUTING`；T2、T3 為 `QUEUED`；T1 為 `QUEUED` 或 `RUNNING` |
| 3 | 立即開 `GET /stream/executions/{runId}/logs?access_token=…`，收到串流結束為止（≤ 60 秒） | 第一個框架為 `retry: 3000`；id 依 `(seq,n)` 嚴格遞增且不重複；`status-change` 序列含 `RUNNING`…最後一則 `COMPLETED`（`bridgeStatus=COMPLETED`）且其後連線關閉；`source=STEP` 的 `log` 依序為 `STARTED G1-T1`、`COMPLETED G1-T1`、`STARTED G1-T2`、`COMPLETED G1-T2`、`STARTED G2-T1`、`COMPLETED G2-T1`，且 `taskId` 為夾具任務 id、`COMPLETED` 的 `message` 結尾為 `Token: 1240`；至少 1 則 `source=ENGINE`；0 則 `review-request`、0 則 `alert` |
| 4 | `GET run` | `status=COMPLETED`、`bridgeStatus=COMPLETED`、`completedSteps=3`、`totalSteps=3`、`totalTokensUsed=3720`、`tokenBudget=100000`、`completedAt` 非 null、`pendingReviews=[]`、`bridge.connected=true`、`bridge.instance=e2e-bridge`、`lastEventSeq` ＝ SSE 最後一則的 `seq` |
| 5 | `GET /executions/{runId}/steps?size=200` | 6 列（三個任務各 `STARTED`＋`COMPLETED`），依 `stepNumber` 嚴格遞增；`stepId` 依序 `G1-T1`…；`COMPLETED` 列 `tokensUsed=1240`、`STARTED` 列為 null；`action` 形如 `G1-T1: 初始化`。再以 `afterSeq=<第 3 列的 stepNumber>` 查 → 剩 3 列 |
| 6 | `GET …/dag` | 5 個節點（2 `GOAL`＋3 `TASK`）、邊 1 條 `DEPENDENCY`＋3 條 `CONTAINS`；全部 `status=COMPLETED`；`TASK` 節點 `sequence` 為 1、2、3 |
| 7 | `GET …/checkpoints` | 3 筆：`after-G1-T1`、`after-G1-T2`、`after-G2-T1`；`stepIdx` 為 1、2、3；`stepId` 為 `G1-T2`、`G2-T1`、`""`；`isAutomatic=true` |
| 8 | Phase 2 讀取 | 專案、兩個目標、三個任務皆 `COMPLETED`；每個任務 `actualTokens=1240`、`retryCount=0`、`startedAt`／`completedAt` 非 null；`GET /tasks/{id}` 的 `executionHistory` 有 2 筆（`STARTED`、`COMPLETED`） |
| 9 | `GET /monitor/projects/{pid}/metrics?runId={runId}` | `totalTokens.value=3720`；`taskCompletionRate.value=100.0`（`previousValue=0.0`、`delta=100.0`）；`taskSuccessRate.value=100.0`；`retryRate.value=0.0`；`averageRetryCount.value=0.0`；`tokenBudgetUsageRate.value=3.7`；`taskStatusDistribution.COMPLETED=3`（其餘 0）；`averageTaskDurationSec.value` 介於 0.5 與 30；`taskDurations` 3 筆；`agentAvailability.value=100.0`（run 開始時立即探測一次） |
| 10 | `GET …/token-trend?runId={runId}&bucket=HOUR` | 各點 `tokens` 加總 3720；最後一點 `cumulativeTokens=3720`；各點 `budget=100000` |
| 11 | `GET …/task-trend?runId={runId}` | `started` 加總 3、`completed` 加總 3、`failed` 與 `retried` 皆 0 |
| 12 | `GET …/logs?runId={runId}&order=asc&size=200` | 含 `Run #1 開始執行（自治等級 4）`（`source=RUN`）、六筆 `source=STEP` 與 `Run #1 已完成`；`level=ERROR` 篩選 → 0 筆 |
| 13 | `GET …/alerts?runId={runId}`；`GET /projects/{pid}/executions` | `[]`；一筆批次：`runNumber=1`、`status=COMPLETED`、`tasksTotal=3`、`tasksCompleted=3`、`tasksFailed=0`、`successRate=100.0`、`durationSec≥1` |
| 14 | 一致性（A1） | Bridge 直接 `GET /autoclaude/runs/{runId}`：`status=COMPLETED`、`completed_steps=3`、`tokens_used=3720`，與 Console 回應、DB 列一致 |
| 15 | 報表：`GET /monitor/projects/{pid}/report?format=csv&runId={runId}`（`Accept: text/csv`） | **200**；`Content-Type` 為 `text/csv`；`Content-Disposition` 含 `monitor-report-`；本文以 BOM 開頭，第一行 `#report,`，依序含 `#section,summary`、`#section,runs`、`#section,tasks`、`#section,alerts` 四段；`summary` 段有 `totalTokens,3720,0,3720,TOKENS`；`runs` 段 1 列、`tasks` 段 3 列、`alerts` 段 0 列；`format=pdf` → **501**（`PDF 報表尚未提供（W5）`）；`format=xls` → **400**（`不支援的報表格式`）；viewer 亦可下載 |

---

### E2E-04　自治閘：Level 1 在第一步之後 PAUSED＋review-request，APPROVE 後 resume 跑完（含 Level 2／3 對照與 SSE 重播）　〔API-AUT-01～03、EXE-10、SSE-03／US-E-04、05、07、08〕

**前置**：PRJ-A（新）；operator。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:1, tokenBudget:100000}` | **201** |
| 2 | 開 `/logs` SSE，觀察到 `status-change` 為 `PAUSED` 為止 | 事件順序：`STARTED G1-T1` → `COMPLETED G1-T1` → `status-change PAUSED`（`reason` 含 `在步驟邊界暫停`、`已完成 1 步`）→ `review-request`：`kind=TASK_CONFIRM`、`status=PENDING`、`taskId`＝T2、`goalId`＝G1、`allowedDecisions=[APPROVE,REJECT]`、`reason=Level 1：請確認是否繼續執行任務「設定」`，其 `id`＝`<PAUSED 事件的 seq>.1`。**PAUSED 之前不得出現 `G1-T2` 的 `STARTED`**（被中止的 spawn 不發 STARTED） |
| 3 | `GET run`、`GET /notifications/summary`、Phase 2 專案 | `status=PAUSED`、`bridgeStatus=PAUSED`、`completedSteps=1`、`currentStep=null`、`pendingReviews` 恰 1 筆且 id 同 SSE；`summary.pendingReviews=1`；專案 `status=READY` |
| 4 | **重播**：另開 `/logs`，`Last-Event-ID` ＝步驟 2 收到的第一則 `log` 的 id | 依序重播其後所有事件（含該 `review-request`，`review.id` 相同），每則恰一次、無 id ≤ 該值者；連線保持開啟（PAUSED 不結束）；閒置 ≥ 2 秒（e2e 的 keep-alive 設定）後收到 `: keep-alive` 註解 |
| 5 | 以 `Last-Event-ID` ＝ `review-request` 的 id 重連 | 不再重播任何事件，只有 keep-alive |
| 6 | `POST review/{reviewId}` `{decision:"SKIP"}` | **409**；`reason=此審核項不允許該決定`；`details.allowedDecisions=[APPROVE,REJECT]` |
| 7 | `POST review/{隨機 uuid}`；以另一個 run 的審核項 id | 皆 **404** |
| 8 | `POST review/{reviewId}` `{decision:"APPROVE", comment:"ok"}` | **204**；**無** `X-Follow-Up-Run-Id` 標頭。隨即再送一次 → **409** `審核項已處理`（`details.status=APPROVED`、`decidedBy=operator`） |
| 9 | SSE 續看 | `status-change RUNNING` → `STARTED G1-T2`（**恰一次**）→ `COMPLETED G1-T2` → `status-change PAUSED`（`已完成 2 步`）→ 第二個 `review-request`：`kind=TASK_CONFIRM`、`taskId`＝T3、`goalId`＝G2 |
| 10 | `POST review/{#2}` `APPROVE` | **204**；`STARTED G2-T1`（最後一步，**不再 pause**）→ `COMPLETED G2-T1` → `status-change COMPLETED`；串流關閉 |
| 11 | 終態檢查 | `GET run`：`COMPLETED`、`completedSteps=3`、`totalTokensUsed=3720`（被中止的 spawn 不產生 token 事件）；DB `review_requests` 2 列 `status=APPROVED`、`decided_by=operator`（第一列 `comment=ok`）、`event_sub=1`；`execution_steps` 中 T1、T2 的 `STARTED` 各恰 1 列 |
| 12 | 手動 resume 處理待決審核項 | 另開一個 Level 1 批次，PAUSED 後改用 `POST /executions/{runId}/resume`（不走審核）→ **200**；該審核項自動關閉為 `APPROVED`（`decidedBy`＝呼叫者、`comment=以手動恢復處理`）；run 續跑（§3.6.3 備註） |

**自治等級對照**（各用新的 PRJ-A；`tokenBudget` 皆 100000）：

| 等級 | `:pause` 呼叫時機 | PAUSED 位置 | review `kind`／`goalId`／`taskId` | `allowedDecisions` | 之後 |
|------|-------------------|-------------|-----------------------------------|--------------------|------|
| 1 | `STARTED G1-T1`、`STARTED G1-T2` | 第 1、2 步之後（各一次） | `TASK_CONFIRM`／T2 的目標／T2；再來 `TASK_CONFIRM`／T3 的目標／T3 | `APPROVE,REJECT` | 兩次 APPROVE 後 COMPLETED |
| 2 | 只有 `STARTED G1-T2`（G1 的最後一步） | 第 2 步之後（G1 與 G2 之間） | `GOAL_CONFIRM`／G2／T3 | `APPROVE,REJECT` | 一次 APPROVE 後 COMPLETED |
| 3 | 同等級 2 | 同等級 2 | `GOAL_COMPLETED`／G1／T2 | `APPROVE,REJECT,RETRY` | 一次 APPROVE 後 COMPLETED |
| 4 | 無 | 無 | 無審核項 | — | 直接 COMPLETED |

**REJECT 變體**（等級 3，PAUSED 後 `REJECT`）：**204**；run `CANCELLED`；專案 `READY`；G1 `FAILED`（人類判定）；審核項 `REJECTED`；等級 1 的 `TASK_CONFIRM` `REJECT` 同樣 → run `CANCELLED`。

**等級 3 的 RETRY 變體**：PAUSED 在 G1 之後，`RETRY` → 目標 G1 是第一個目標、沒有 `step_idx=0` 的快照 → 走後續批次：**204** 且帶 `X-Follow-Up-Run-Id`；原 run 被 `:stop` 為 `CANCELLED`；新批次（`runNumber=2`，`scope.followUpOfRunId` ＝原 run）自 G1 起重跑。

---
### E2E-05　ESCALATED（`MOCK_CLAUDE_FAIL_REGEX` 製造失敗）→ 審核 RETRY → 再失敗 → SKIP　〔API-EXE-10、AUT-03、04、ALR-03／US-E-06～08、T-06〕

**前置**：PRJ-A（新）但 **T2 的 `description`＝`請輸出 [T2_DONE] [FAIL_ME]`**（T2 在 mock 下必失敗）；`maxRetries=1`；operator。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4}` 並開 `/logs` SSE 到串流關閉 | `COMPLETED G1-T1` → `STARTED G1-T2`(attempt 1) → `RETRYING G1-T2`(attempt 2) → `FAILED G1-T2`(attempt 2) → `alert`（`origin=ENGINE`、`code=ESCALATION`、`severity=CRITICAL`，id 為 Bridge seq）→ `status-change FAILED`（`reason` 以 `引擎升級（ESCALATION）` 開頭）→ `review-request`（`kind=ESCALATED`，id `<FAILED 事件的 seq>.1`）→ 串流關閉（終態） |
| 2 | `GET run` | `status=FAILED`、`completedSteps=1`；`reason` 以 `引擎升級（ESCALATION）` 開頭；`pendingReviews[0]`：`kind=ESCALATED`、`taskId`＝T2、`goalId`＝G1、`allowedDecisions=[RETRY,SKIP,REJECT]`、`reason` 含 `重試 1 次仍失敗` |
| 3 | Phase 2 與告警 | 專案 `FAILED`；G1 `FAILED`；G2 `PENDING`；T1 `COMPLETED`；T2 `ESCALATED`（`retryCount≥1`）；T3 `PENDING`（`QUEUED` 被系統重設）。`GET …/alerts`：一筆 `rule=ENGINE_ESCALATION`、`severity=CRITICAL`、`subject=step:G1-T2`、未確認；`summary`：`pendingReviews=1`、`unacknowledgedAlerts=1` |
| 4 | `POST review/{id}` `{decision:"APPROVE"}` | **409** `此審核項不允許該決定`（`allowedDecisions=[RETRY,SKIP,REJECT]`） |
| 5 | **RETRY**：`{decision:"RETRY", comment:"再試一次"}` | **204**，**無** `X-Follow-Up-Run-Id`（找得到還原點 `after-G1-T1`，`stepIdx=1`，走 Bridge restore）；5 秒內 `GET run` 為 `RUNNING`；SSE（新連線，`Last-Event-ID`＝步驟 1 的最後 id）：`alert`（`origin=ENGINE`、`code=RESTORE`、`severity=INFO`、**無 `alertId`**）→ `status-change RUNNING` → `STARTED G1-T2`(attempt 1) → `RETRYING`(2) → `FAILED`(2) → `alert ESCALATION` → `status-change FAILED` → 第二個 `review-request`（`ESCALATED`，PENDING）。第一個審核項 `status=RETRIED`、`decidedBy=operator`、`comment=再試一次`；`runNumber` 仍為 1；mock trace 中 `[T1_DONE]` 恰 1 次（T1 未重跑）。**注意**：restore 沿用原 playbook，T2 的 prompt 未變，所以再次失敗是預期行為 |
| 6 | **SKIP**（對第二個審核項）：`{decision:"SKIP"}` | **204**，**帶 `X-Follow-Up-Run-Id`**＝R2。`GET /executions/{R2}`：`runNumber=2`、`scope.mode=SELECTED`、`scope.taskIds=[T3]`、`scope.followUpOfRunId`＝R1、`autonomyLevel=4`、`tokenBudget` 同 R1；R2 的 DAG 只有 G2、T3（**step_id 為 `G1-T1`**：每個批次獨立編號，§3.4.4）；R2 跑到 `COMPLETED`（`totalTokensUsed=1240`） |
| 7 | 終態檢查 | T2 `SKIPPED`；T3 `COMPLETED`；G1 `COMPLETED`（T1 完成＋T2 跳過）；G2 `COMPLETED`；專案 `COMPLETED`；第二個審核項 `status=SKIPPED`；R1 仍為 `FAILED`；`GET /projects/{pid}/executions` 兩筆（R2 在前）；`unacknowledgedAlerts` 仍為 1（第一次升級的 `ENGINE_ESCALATION`：告警不因處置自動確認；步驟 5 的第二次同一步驟升級在未確認前不重複產生，故沒有第二列，只有 SSE 轉發） |

**變體 V1：第一步失敗的 RETRY**（T1 帶 `[FAIL_ME]`）：run `FAILED` 後 `RETRY` → 沒有 `step_idx=0` 的快照 → **204＋`X-Follow-Up-Run-Id`**；新批次（範圍＝專案內全部非完成任務）重跑並再度失敗，產生新的 `ESCALATED` 審核項；舊審核項 `RETRIED`。
**變體 V2：REJECT**：對 `ESCALATED` 審核項 `REJECT` → **204**，審核項 `REJECTED`；run 維持 `FAILED`、任務維持 `ESCALATED`、**不呼叫 Bridge**（Bridge 的 run 狀態不變）。
**變體 V3：新批次取代舊審核項**：run `FAILED` 且審核項 `PENDING` 時，直接 `POST execute` 開新批次 → 舊審核項自動 `status=REJECTED`、`decided_by=system`、`comment` 含 `已由第 2 批次取代`。
**變體 V4：Level 5**：`autonomyLevel:5` 執行同一專案 → 行為與等級 4 相同（失敗時建 `ESCALATED` 審核項）；其他失敗型態（halt、異常結束、orphaned）的「等級 1～4 不建審核項、等級 ≥5 建審核項」由後端單元測試的決策表覆蓋（難以在 mock 下決定性製造）。

---

### E2E-06　cancel → CANCELLED（並可重新執行）　〔API-EXE-04／US-E-06〕

**前置**：PRJ-A（新）；operator；`autonomyLevel:4`。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute`，開 `/logs` SSE，等到 `STARTED G1-T1` | **201** |
| 2 | `POST cancel` | **200**；`bridgeStatus∈{CANCELLING,CANCELLED}`（`status` 為 `RUNNING` 或 `CANCELLED`） |
| 3 | SSE | `status-change`（`runStatus=RUNNING`、`bridgeStatus=CANCELLING`）→ `status-change CANCELLED`；15 秒內串流關閉 |
| 4 | `GET run` 與 Bridge 快照 | `status=CANCELLED`、`completedAt` 非 null、`completedSteps=0`、`pendingReviews=[]`；Bridge `pid=null`（無殘留行程） |
| 5 | Phase 2 | 專案 `READY`；T1 `CANCELLED`（原 `RUNNING`）、T2／T3 `CANCELLED`（原 `QUEUED`，US-E-06）；G1／G2 `PENDING`（R-goal：沒有進度） |
| 6 | 再 `cancel`、`pause`、`resume` | 皆 **409** `目前執行狀態不允許此操作`（`details.runStatus=CANCELLED`、`details.action` 為各自動作） |
| 7 | **可重新執行**：`POST execute` `{}` | **201**；`runNumber=2`；三個任務由 `CANCELLED` 系統重設為 `QUEUED` 後跑到 `COMPLETED`；專案 `COMPLETED` |
| 8 | **PAUSED 時取消**（新專案，等級 1）：待決審核項存在時 `POST cancel` | **200**，狀態直接 `CANCELLED`（`:stop` 對 PAUSED 即時收尾）；該批次的待決 gate 審核項自動 `REJECTED`（`decided_by=system`、`comment=執行已取消`） |

---

### E2E-07　restore：從歷史 checkpoint 續跑　〔API-EXE-08、09／US-E-11〕

**前置**：PRJ-A（新）以等級 4 跑到 `COMPLETED`（`totalTokensUsed=3720`）；operator。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `GET …/checkpoints` | 3 筆（見 E2E-03 步驟 7）；記下 `after-G1-T1` 的 id（`stepIdx=1`） |
| 2 | `POST restore/{after-G1-T1}` | **200**；`status=RUNNING`、`bridgeStatus=RUNNING`；專案回 `EXECUTING`；T2、T3 重設為 `QUEUED`（T1 維持 `COMPLETED`） |
| 3 | SSE（`Last-Event-ID`＝還原前最後一則的 id） | `alert`（`ENGINE`、`RESTORE`、`INFO`）→ `status-change RUNNING` → `STARTED G1-T2` → `COMPLETED G1-T2` → `STARTED G2-T1` → `COMPLETED G2-T1` → `status-change COMPLETED`；**沒有** `G1-T1` 的 `STARTED` |
| 4 | 終態檢查 | `COMPLETED`、`completedSteps=3`、`totalTokensUsed=6200`（3,720＋2×1,240，Bridge 的累計跨 restore 持續）；`GET …/checkpoints` 數量大於 3（append-only）；`GET steps` 共 10 列（原 6＋T2、T3 各 `STARTED`＋`COMPLETED`）；mock trace 中 `[T1_DONE]` 1 次、`[T2_DONE]` 2 次、`[T3_DONE]` 2 次；T2、T3 `actualTokens=2480`（兩次執行累計）、T1 `1240`；專案回到 `COMPLETED` |
| 5 | 負向 | 對 `RUNNING` 的 run restore → **409** `目前執行狀態不允許此操作`；他人 run 的 `checkpointId` → **404**；專案已有較新批次（`runNumber` 更大）時對舊批次 restore → **409** `只能還原專案最新的執行批次`（`details.latestRunNumber`）；viewer → **403** |
| 6 | **PAUSED 時 restore**（等級 1）：第一次 PAUSED 後 `restore` 到 `after-G1-T1` | **200**；run 繼續；待決 gate 審核項自動 `REJECTED`（`decided_by=system`、`comment=執行已還原`） |

---

### E2E-08　Token 預算告警（小預算）　〔API-ALR-01、02／US-M-05、E-10〕

**前置**：PRJ-B（5 任務，新）；operator；`tokenBudget:1500`；同時開 `/logs` 與 `/metrics` 兩條 SSE。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `POST execute` `{autonomyLevel:4, tokenBudget:1500}` | **201** |
| 2 | T1 的 token 事件（1,240）後 | `/metrics`：`token-update` `tokensUsed=1240`、`budgetUsageRate=82.7`；`/logs`：`alert`（`origin=CONSOLE`、`rule=TOKEN_BUDGET_WARNING`、`severity=WARNING`、`subject=run:<runId>`、`message=Token 使用量已達預算的 83%（1240 / 1500）`，id 為 `<seq>.<n>`、`n≥1`） |
| 3 | T2 的 token 事件（累計 2,480）後 | `token-update` `tokensUsed=2480`、`budgetUsageRate=165.3`；`alert`（`rule=TOKEN_BUDGET_EXCEEDED`、`severity=CRITICAL`、`message=Token 使用量已超出預算（2480 / 1500），已要求暫停執行`）；Console 對 Bridge 呼叫 `:pause` |
| 4 | 等 `status-change PAUSED` | `completedSteps` 介於 **2 與 4**（含）——`:pause` 的送達只要在最後一步之前就必然暫停；因每步 ≥0.6 秒遠大於消費者延遲，實務上為 3。**不得**直接 `COMPLETED`。`pendingReviews=[]`（預算暫停不建審核項） |
| 5 | `GET …/alerts?runId={runId}` | 恰 2 筆：`TOKEN_BUDGET_WARNING`、`TOKEN_BUDGET_EXCEEDED`，皆 `acknowledged=false`；`summary.unacknowledgedAlerts=2` |
| 6 | `POST resume` → 跑完 | **200**；run `COMPLETED`、`totalTokensUsed=6200`；告警仍恰 2 筆（**去重**：未確認前不重複產生）；專案 `COMPLETED` |
| 7 | 確認告警 | operator `POST /monitor/alerts/{warningId}/acknowledge` → **204**；再次確認 → **204**（冪等，`acknowledgedBy／At` 不變）；`GET …/alerts?acknowledged=false` 只剩 CRITICAL 一筆；viewer 確認 → **403**；不存在的 id → **404** |
| 8 | 指標 | `GET …/metrics?runId=…`：`tokenBudgetUsageRate.value=413.3`；`totalTokens.value=6200` |

**變體 V1：單一任務上限**：`scope.limits.taskTokens=1000`、`tokenBudget=1000000` → T1 的 token 事件（1,240 > 1,000）後出現 `TOKEN_BUDGET_EXCEEDED`、`subject=task:<T1 id>`、`message` 含 `任務「初始化」` 與 `1000`，並 `:pause`。

---

### E2E-09　系統參數：token_guard 跨鍵校驗、敏感值、reveal、重置、匯出匯入、歷史　〔API-SET-01～09、NFR-SEC-05／US-S-01～08〕

**前置**：admin；其他角色見各步。每步的「DB 不變」指 `system_configs` 該鍵的 `value` 與 `system_config_history` 筆數不變。

| # | 動作 | 預期 |
|---|------|------|
| 1 | viewer `GET /settings` | **200**；六個分類鍵數 `model=10、agent=9、execution=10、monitor=6、autoclaude=11、sdd=4`（共 50）；每筆都有 `effect`；`model.apiKey`：`value=••••••••`、`isEncrypted=true`；`execution.compactThresholdPct`：`value=80`、`min=1`、`max=99`、`effect=ENGINE` |
| 2 | `PUT /settings/execution/token-guard` `{compactThresholdPct:90, haltThresholdPct:80}` | **400**；`reason=halt_threshold_pct 必須大於 compact_threshold_pct`（PRD 逐字）；兩鍵 DB 不變（80／90） |
| 3 | 同上 `{80, 80}`；`{100, 100}`；`{0, 50}` | 相等 → **400** 同 reason；`100`（超過 compact 上限 99）與 `0` → **400**（Bean Validation，`errors[0].field` 為對應欄位，無該 reason） |
| 4 | `{compactThresholdPct:70, haltThresholdPct:95}` | **200**；回兩筆 `ConfigResponse`；歷史新增 2 筆（`80→70`、`90→95`，`changedBy=admin`） |
| 5 | **單鍵跨鍵校驗**：`PUT /settings/execution/haltThresholdPct` `{value:"60"}`；`PUT …/compactThresholdPct` `{value:"96"}` | 皆 **400**，reason 同步驟 2（讀對端現值 70／95）；DB 不變 |
| 6 | `PUT …/compactThresholdPct` `{value:"abc"}` | **400**；`reason=參數值不符合型別或驗證規則`；`errors[0].field=value` |
| 7 | **敏感值**：`PUT /settings/model/apiKey` `{value:"sk-new"}`（不帶 confirm） | **409**；`reason=敏感參數更新需二次確認（confirm=true）`；DB 不變。改帶 `confirm:true` → **200**，`value=••••••••`、`hasValue=true`；歷史該筆 `oldValue`／`newValue` 皆 `••••••••` |
| 8 | **reveal**：operator `GET /settings/model?reveal=true`；viewer 同；admin 同 | operator／viewer **403**（`reason=僅 ADMIN 可揭露敏感參數`）；admin **200**，`apiKey.value=sk-new`（明文）；審計日誌有 `settings.reveal`（不含值）。未帶 `reveal` 的 operator `GET` → 仍是 `••••••••` |
| 9 | **角色**：operator `PUT` 任一參數／`POST reset`／`POST export`／`POST import`／`POST test-connection` | 皆 **403** `ACCESS_DENIED`；viewer 與 operator 的 `GET` 皆 **200** |
| 10 | **重置與跨鍵**（此時 compact=70、halt=95）：① `PUT /settings/execution/token-guard` `{70, 75}`；② `POST /settings/execution/compactThresholdPct/reset`；③ `POST …/haltThresholdPct/reset`；④ 再 `POST …/compactThresholdPct/reset` | ① **200**；② **400**（compact 預設 80 ≥ 目前 halt 75；reason 同步驟 2；compact 仍為 70）；③ **200**（halt→`90`）；④ **200**（compact→`80`，80 < 90）。每個成功的重置各寫一筆歷史 |
| 11 | 加密鍵重置 | `POST /settings/model/apiKey/reset`（無 confirm）→ **409** `敏感參數重置需二次確認（confirm=true）`；`?confirm=true` → **200**，`hasValue=false`。`POST /settings/execution/reset` → **200**，回該分類 10 筆且值皆為預設 |
| 12 | **匯出匯入**：`POST /settings/export` | **200** JSON：`version=1`、`configs` 50 筆；`model.apiKey`／`autoclaude.dbDsn` 的 `value="<encrypted>"`；標頭 `Content-Disposition` 含 `aisdlc-settings-` |
| 13 | 改檔案中 `monitor.refreshIntervalMs` 為 `"900"` 後 `POST /settings/import` | **200**；`applied=1`、`skipped=49`（含 2 筆 `<encrypted>` 佔位＋47 筆值未變）、`errors=[]`；歷史新增 1 筆。再匯入 compact=90／halt=80 的檔 → **200**，`errors` 含兩筆（`compactThresholdPct`、`haltThresholdPct`），`reason=halt_threshold_pct 必須大於 compact_threshold_pct`，兩鍵皆未套用 |
| 14 | 匯入異常檔 | `version:2` → **400** `設定檔格式錯誤`（`details.problem=unsupported_version`）；不是 JSON → **400**（`invalid_json`）；2MB 檔 → **413** `設定檔超過 1MB 上限`；`.txt` → **415** |
| 15 | **SEC-04（儲存時）**：`PUT /settings/model/apiUrl` `{value:"http://10.0.0.5"}`；`{value:"https://example.com"}`；`{value:"http://127.0.0.1:<WM_PORT>"}` | **400**（`目標位址未通過 SSRF／allowlist 檢查`，`details.violation=private_ip`）；**400**（`not_in_allowlist`）；**200**（e2e allowlist 放行） |
| 16 | **歷史**：`GET /settings/history?category=execution&key=haltThresholdPct&page=0&size=2` | **200**；`totalElements≥3`；`changedAt` 由新到舊；單獨給 `key`（無 `category`）→ **400** |

---

### E2E-10　test-connection：私網 URL 被 SSRF 拒絕　〔API-SET-06／US-S-05／NFR-SEC-04〕

**前置**：admin；WireMock `GET /v1/models` 預設 stub 回 200；`model.timeout=3`。

| 請求（`POST /settings/test-connection` body） | 預期 |
|-----------------------------------------------|------|
| `{apiUrl:"http://10.0.0.5:8080"}` | **422**；`reason=目標位址未通過 SSRF／allowlist 檢查`；`details={host:"10.0.0.5", violation:"private_ip"}`；**沒有任何連線**（WireMock 與網路皆無請求） |
| `{apiUrl:"http://192.168.1.1"}`、`http://172.16.0.9`、`http://100.64.0.1` | **422** `private_ip` |
| `{apiUrl:"http://169.254.169.254/latest/meta-data"}` | **422** `link_local` |
| `{apiUrl:"http://[::1]:8080"}` | **422** `loopback`（`::1` 不在 allowlist） |
| `{apiUrl:"http://0x7f.0.0.1"}`、`http://2130706433` | **422** `malformed_url`（非標準 IP 寫法一律拒絕） |
| `{apiUrl:"ftp://api.anthropic.com"}` | **422** `scheme` |
| `{apiUrl:"http://user:your_password_here@api.anthropic.com"}`（userinfo 一律拒絕；此為測試夾具，不是真值） | **422** `userinfo` |
| `{apiUrl:"https://example.com"}`、`http://localhost.evil.example` | **422** `not_in_allowlist` |
| `{apiUrl:"http://rebind.e2e.test"}`（e2e 把此名稱加入 allowlist，DNS 覆寫為 `10.0.0.5`） | **422** `dns_rebinding` |
| `{apiUrl:"http://127.0.0.1:<WM_PORT>", apiKey:"sk-secret-xyz"}` | **200**；`success=true`、`message=連線成功`、`httpStatus=200`、`resolvedHost=127.0.0.1`、`latencyMs≥0`；**WireMock 驗證**：收到 `GET /v1/models` 一次、`Authorization: Bearer sk-secret-xyz`；回應本文與日誌**都不含** `sk-secret-xyz` |
| WireMock `/v1/models` 回 401 | **200**；`success=false`、`message=認證失敗（HTTP 401）` |
| WireMock `/v1/models` 回 302 `Location: http://127.0.0.1:<WM_PORT>/redirected` | **200**；`success=false`、`message` 含 `已拒絕跟隨`；WireMock 的 `/redirected` **請求數為 0** |
| WireMock `/v1/models` 延遲 8 秒（`model.timeout=3`） | **200**；`success=false`、`message` 含 `連線逾時`（約 3 秒內返回） |
| 空 body，且已儲存的 `model.apiUrl` 被（以 DB 直接改成）`http://10.0.0.5` | **422** `private_ip`（已儲存值同樣被檢查） |
| operator／viewer 呼叫 | **403** |

稽核：每次呼叫（含被拒）都有一行 `settings.testConnection` 審計日誌（host＋結果），整份日誌不含任何 API 金鑰與 userinfo。

---

### E2E-11　限流：第 101 次請求 → 429　〔NFR-9.2-06〕

**前置**：`trust-forwarded-for=true`（e2e profile）；用唯一的 `X-Forwarded-For: 203.0.113.<n>` 隔離桶；viewer。

| # | 動作 | 預期 |
|---|------|------|
| 1 | 同一個 `X-Forwarded-For` 連續 100 次 `GET /api/v1/projects` | 全部 **200**；每個回應 `X-RateLimit-Limit: 100`，`X-RateLimit-Remaining` 由 99 遞減到 0 |
| 2 | 第 101 次 | **429**；`code=429`、`reason=超過每分鐘 100 次請求上限`、`details={limit:100, windowSeconds:60, retryAfterSeconds:N}`（1≤N≤60）；標頭 `Retry-After`＝N、`X-RateLimit-Remaining: 0`；封包含 `traceId` |
| 3 | 換一個 `X-Forwarded-For` 請求 | **200**（桶隔離） |
| 4 | 被限流的 IP 打 `GET /actuator/health` | **200**（不計入） |
| 5 | 等 `Retry-After` 秒後再請求 | **200** |
| 6 | 同一 IP 開 SSE 連線並維持 | 建立算 1 次；串流期間的事件不消耗額度 |
| 7 | `trust-forwarded-for=false`（production 預設）時帶 `X-Forwarded-For` | 標頭被忽略，以連線位址計（後端單元／整合測試，不在 E2E 環境） |

---

### E2E-12　SSE 認證、重播與終態語意　〔API-SSE-01～03／US-E-03〕

**前置**：E2E-03 產生的已完成 run（R，`lastEventSeq=S`）；E2E-04 的 PAUSED run 用於步驟 10。

| # | 動作 | 預期 |
|---|------|------|
| 1 | `/logs` 無 token；`?access_token=garbage`；已過期的 access token；以 **refresh token** 放進 `?access_token=` | 皆 **401 JSON**（`UNAUTHENTICATED`／`TOKEN_INVALID`／`TOKEN_EXPIRED`／`TOKEN_INVALID`），在串流開始前回 |
| 2 | viewer 的 token（標頭） | **200** 串流（VIEWER 可看） |
| 3 | 標頭帶有效 token、查詢參數帶無效 token | **200**（標頭優先） |
| 4 | 不存在的 `runId` | **404 JSON** |
| 5 | 已完成的 R：`/logs` 無 `Last-Event-ID` | **200**；重播最後 `tail`（預設 200）則事件後關閉；最後一則 `status-change` 為 `COMPLETED` |
| 6 | `/logs` 帶 `Last-Event-ID: <S>` | **204**（無內容、EventSource 不再重連） |
| 7 | `Last-Event-ID: garbage`；`?tail=0`（無 `Last-Event-ID`） | 前者視為未帶 → 同步驟 5；後者重播集合為空 → **204** |
| 8 | 已完成的 R：`/metrics` | **200**，恰 3 則：`progress-update`（`completedSteps=3`、`totalSteps=3`、`progressPct=100.0`）、`token-update`（`tokensUsed=3720`）、`metric-update`（`completedTasks=3`、`totalTasks=3`、`totalTokensUsed=3720`），id 依序 `<S>`、`<S>`、`<S>.1`；之後關閉。`Last-Event-ID: <S>.1` → **204** |
| 9 | 進行中的 run 開 `/metrics` | 連線後先收到 3 則最新快照，再隨事件更新；`Last-Event-ID` 的值不影響（收斂重播） |
| 10 | PAUSED 的 run（E2E-04）閒置 | 連線保持；每 ≤ `console.sse.keep-alive-seconds`（e2e 為 2 秒）收到一行 `: keep-alive` |
| 11 | 瀏覽器預檢：自允許的 origin 對 `/api/v1/stream/…` 送 `OPTIONS`，`Access-Control-Request-Headers: last-event-id,authorization` | 回應的 `Access-Control-Allow-Headers` 含 `Last-Event-ID` |
| 12 | 日誌稽核 | 整份存取日誌與審計日誌**不含**任何 `access_token` 的值 |
| 13 | Bridge 暫時不可達（後端整合測試：假 Bridge 回連線重設） | 串流不關閉；送一則**不帶 `id:` 行**的 `alert`（`origin=CONSOLE`、`code=BRIDGE_UNREACHABLE`、`severity=WARNING`）；Bridge 恢復後自動補齊事件、無缺漏 |

---
## 6. 差異與裁決

### 6.1 與規格、既有程式的差異（D-01～D-48）

比對對象：PRD §0／§5／§7／附錄 B、Architecture §6／§7／§8／§11、ADR-001（D12、D18、G-xx）、`W3_BACKEND_P3-6.md`（簡稱「W3」）、Bridge 真實行為（README／`app/`／`tests/`）、Phase 1+2 已落地程式；與五份任務書的差異見 §6.2。**主控已定、本文照做的裁決**（stepId＝審核項 id、204、自由文件走 OpenAI 相容 chat completions 與六個 gate、報表路徑、加密值遮罩與 `reveal`、時間與列舉、Bridge 不可達回 200）不在此重列。「裁決」欄是本契約採用的作法；標 ⚠ 者另列在交卷的〈未決問題〉，附建議預設（主控未另裁決則採建議值）。

| 編號 | 項目 | 來源 A | 來源 B | 裁決 | 理由 |
|------|------|--------|--------|------|------|
| D-01 | signoff 與 confirm 的分工與回傳型別 | PRD §7.1.4.1：signoff 回 `ProjectResponse` 並落庫；W3：signoff 即建專案、confirm 合流 | ADR-001 D12／Architecture §6(b)：signoff 只批准（回 `ImportRecordResponse`），confirm 才落庫 | 採 **D12** | 設計稿是「先 signoff、再按確認匯入」兩個動作；signoff 即落庫會讓 confirm 失去意義，也會讓兩個端點各建一次專案。`confirm` 未 signoff → 409 |
| D-02 | 自由文件的解析手段 | Architecture §6(b)／ADR D12 第 2 點：Bridge decompose 二段拆解 | ADR D18／W3／主控裁決：後端呼叫 OpenAI 相容 chat completions | 採 **D18**（D12 第 2 點作廢，其餘保留） | decompose 回扁平步驟 DAG，產不出多目標三層樹（ADR G-11）；且 decompose 只能讀 Bridge 環境的金鑰 |
| D-03 | 路徑 A 的觸發 | D12：呼叫端給 `specDir` 且 `GET /sdd/fsm/{project}` 顯示已凍結 | D18／W3：`executionPath` 下有凍結規格 | 兩者並存：明示 `specDir` 或以 `executionPath` 探測 `POST /sdd/compile`；「規格存在但被拒」fail-closed 不退回 LLM | 設計稿沒有 `specDir` 欄位；`/sdd/fsm/{project}` 讀的是 SDD 自己的專案狀態，不是使用者目錄；compile 本身就是最準的探針 |
| D-04 | 解析失敗的 HTTP 形式與 `ParseResultResponse.errors` | Architecture §11.1：422；W3：422 結構化錯誤 | 主控裁決：`ParseResultResponse.errors[]` 形狀 `{gate,detail,location?}` | **HTTP 422**，本文為 `ApiError` 的特化（`errors[]` 項目＝`FieldError`＋`gate/detail/location`）；`ParseResultResponse.errors` 保留但成功時恆為 `[]` ⚠ | 單一失敗通道（一般 client 把項目當 `FieldError` 讀即可）；`errors` 欄位維持裁決的形狀。若主控要「200＋errors」請改這一條 |
| D-05 | 補充端點 | PRD §7.1.4／§7.1.8 未列 | 設計稿「歷史記錄」重開審核、「放棄」、「全部重置為預設值」；測試連線要用未儲存的表單值 | 新增 `GET /import/{id}`、`POST /import/{id}/reject`、`POST /settings/{category}/reset`；`test-connection` 的 body 選填 ⚠ | 皆為設計稿元素的最小資料來源；不改動 PRD 既有端點的語意 |
| D-06 | playbook `step_id` | Architecture §6(c)：`T001`、`T002`… | W3：`G{goal.sortOrder}-T{task.sortOrder}` | **`G<目標位置>-T<任務位置>`**（位置＝批次範圍內的 1 起序號，§3.4.4）；prompt 標頭含 stepId | `sortOrder` 非唯一（Phase 2 允許重複），會撞 id 使 Bridge 422；位置序保證唯一且保留 W3 要的可讀性；每步 prompt 互異對 Bridge 的邊界判定也必要 |
| D-07 | `global_goal` | Architecture：專案說明，缺則通過標準 | W3：`project.passCriteria` | 採 **W3** | `passCriteria` 必填、是整個專案的終點，最適合給引擎對齊目標 |
| D-08 | 審核項 `kind` | W3：`TASK_CONFIRM／GOAL_CONFIRM／GOAL_REVIEW／TASK_FAILED` | V3 migration 的 CHECK 與 Architecture §11.3：`TASK_CONFIRM／GOAL_CONFIRM／GOAL_COMPLETED／ESCALATED` | 採 **V3 的四種**；等級 ≥5 的「run FAILED」與任務失敗一律用 `ESCALATED` | V1～V4 已套用、不得改；四種足夠表達（§3.6.2） |
| D-09 | 審核閘的 `:pause` 時機 | W3：每個 `step COMPLETED` 後立即 pause | Architecture §6(c).c.4：提前一步（`STARTED` 時 pause） | 採 **Architecture**（§3.6.1） | Bridge 的 pause 在「呼叫後的下一個步驟邊界」生效，而 `COMPLETED(k)` 與 `STARTED(k+1)` 同一瞬間發出——等到 `COMPLETED` 才呼叫會多跑一個任務（Bridge `test_pause_stops_at_the_step_boundary…` 已實證邊界語意） |
| D-10 | `StartExecutionRequest` | Architecture §11.2：`autonomyLevel`／`tokenBudget`／`scope` 必填，`scope` 含 `mode`、`limits` | W3：全部可省，`scope:{goalIds?,taskIds?}` | **全部可省，預設值明定**；`scope` 含 `mode`、`limits`（超集） | 設計稿表單永遠送齊；API 對腳本更友善；`limits` 是 US-E-10 所需 |
| D-11 | `ConnectionTestResponse` 與 SSRF 拒絕 | Architecture §11.2：`{success,latencyMs,message,resolvedHost}` | W3：`{ok,latencyMs,error}`，拒絕以 `ok=false` 表達 | 採 **Architecture 欄位**＋`httpStatus`；SSRF／allowlist 拒絕是 **422**（網路層失敗才是 200＋`success=false`） | 政策拒絕與「試了但失敗」要能區分（監控與 QA 都需要）；並與其他 422 的「結構化原因」一致 |
| D-12 | Bridge 不可達的表達 | W3：`bridgeReachable=false` | Architecture §11.2＋主控裁決：`bridge{connected,instance}` | 採 **`bridge.connected`**，另加 `status`／`runKnown`／`checkedAt` | 主控裁決；`runKnown` 區分「網路不通」與「工作區已清」 |
| D-13 | 審計 | W3：`audit_log` 表（V5）；W3-B1 任務書：寫入端點落 `console.audit_log`（V6） | Architecture §8.6：結構化日誌、不新增資料表；Phase 2 已有 `AuditLoggingFilter` | **兩者並行**：沿用結構化日誌並追加 `action`／`entity`，另依任務書落 `audit_log`（V6，內部實作）；契約**不含**審計查詢端點 | 契約無任何端點讀審計，表是內部實作、不影響 HTTP 契約；版號依任務書（V6，§0.5） |
| D-14 | 限流儲存 | Architecture §8.6／ADR D16：Redis，無則記憶體 | W3：Bucket4j 記憶體，Redis 選配 | 記憶體為基準，Redis 選配；行為（100／分／IP、429 封包與標頭）在 §0.4 固定 | 行為對外一致；儲存是實作細節 |
| D-15 | SSE 的 token 傳遞 | Architecture §8.1：「SSE 以 fetch 串流帶 Bearer，禁止 query-string token」 | 主控裁決／W3：標頭與 `?access_token=` 兩者皆收 | 採**兩者皆收**，加補強：僅 `/api/v1/stream/**`、只收 access token、日誌遮罩、`Cache-Control: no-store`；前端優先用 fetch＋標頭 | 瀏覽器 `EventSource` 無法帶標頭；補強降低 URL 洩漏面（token 30 分鐘過期） |
| D-16 | Token 趨勢的資料來源 | Architecture §6(d)：`execution_steps.tokens_used` 分桶加總 | Bridge `mirror_step` 從不寫 `tokens_used`（`db.py`、`runner.py`） | 新增 Console 擁有的 `run_token_samples`（V7），由 `token` 事件寫入；`ExecutionStepResponse.tokensUsed` 由歸因回算 ⚠ | 照原設計圖表會永遠是空的；不要求改 Bridge（若主控願意改 Bridge 寫該欄，可移除此表） |
| D-17 | 引擎告警的持久化 | W3：ESCALATION／TOKEN_HALT 寫 alerts 並對映 §5.4.4 | PRD §5.4.4 只有六條規則；`alerts.rule` 無 CHECK | 新增 `ENGINE_ESCALATION`／`ENGINE_TOKEN_HALT` 兩個規則名；其餘 Bridge 告警只轉發 | `rule` 欄無約束，不需改 DDL；避免硬套進六條規則造成語意錯置 |
| D-18 | 自治等級 4 與 5 以上的行為 | PRD §5.3.2：4＝重試失敗後介入、5＝僅致命錯誤；W3：4 只在 ESCALATED、≥5 只在 run FAILED | 引擎沒有等級 5 的「替代方案」能力（Architecture §12） | 照 W3 字面：1～4 只對升級型失敗建審核項，≥5 對任何 run 失敗建審核項；等級 6～10 不另送引擎設定（`UNVERIFIED`） | 字面保守；Console 行為在 4 與 5 以上實際相同，差異留待引擎支援（V-8） |
| D-19 | 附錄 B 沒涵蓋的狀態結果 | PRD 附錄 B.3：無 `QUEUED→CANCELLED`、`CANCELLED／COMPLETED→QUEUED`；B.2 無 `FAILED→IN_PROGRESS` | US-E-06（取消標 CANCELLED）、US-E-11（還原）、失敗後重新執行 | 定義「**系統重設**」操作與 R-goal 推導（§3.5.3）；手動 API 仍嚴守附錄 B ⚠ | 不改 PRD 附錄、不動 `StateMachinesTest` 鎖住的轉移表；結果可決定、可測 |
| D-20 | 審核 `SKIP` 的可行性（Architecture V-4 待驗） | W3：任務 SKIPPED 後 `:resume` | Bridge：`resume` 只收 `PAUSED`；ESCALATION 後 run 已是 `FAILED`；`restore` 無法跳過步驟 | `SKIP`＝標 `SKIPPED`＋**以剔除該任務的新 playbook 開後續批次**（`X-Follow-Up-Run-Id`） | 這是 Bridge 能力下唯一可行的作法；V-4 結論回寫 Architecture §12 |
| D-21 | `RETRY` 的機制 | W3／Architecture：restore 到失敗步驟前的 checkpoint | 使用者可能先「修改任務」再重試 | 採 **restore**（找不到快照的首步改開後續批次）；**restore 沿用原 playbook**，改過的任務內容要另開批次才生效（§1.2.10） | 守主控裁決；限制明文化，避免使用者誤以為改了就會生效 |
| D-22 | `execution_steps.step_number` 的意義 | PRD §5.3.5：「步驟序號」 | Bridge 寫入該 step 事件的 `seq`（位置放在 `input`） | `stepNumber`＝事件 `seq`，`afterSeq` 直接對 `Last-Event-ID` | PRD §7.1.7 本來就要求 `step_number`「對應事件序」；位置另有 `stepId`／`input.step_id` |
| D-23 | `ExecutionStepResponse.tokensUsed` | Architecture §11.2：由 `execution_steps` 帶出 | Bridge 不寫 | 同 D-16：COMPLETED／FAILED 列由歸因回算，其餘 null | |
| D-24 | 設定匯出的加密值 | Architecture §11.2：匯出「不含敏感值」 | W3：輸出 `"<encrypted>"` 佔位、匯入跳過 | 採 **W3 佔位** | 匯出檔與匯入檔同形狀、可往返；敏感值仍不出現 |
| D-25 | 報表 | PRD §7.1.6：`application/pdf` or `text/csv` | 主控裁決：CSV 必做、PDF 標 W5 | CSV 格式在 §1.3.7 固定（四段、BOM、CRLF、注入防護）；PDF＝501 | |
| D-26 | KPI 集合 | PRD §5.4.2：八項 | 設計稿：四張卡（含「完成率」「重試率」） | `metrics` 回十個 KPI（八項＋`taskCompletionRate`＋`retryRate`）與分布 | ADR-001 G-13（兩者皆實作）；設計稿「完成率」是專案內進度，不是 PRD 的全域專案完成率 |
| D-27 | `autoclaude.dalBackend` 等的物化 | Architecture §11.4：`dalBackend`→`storage.mode` | Bridge：`storage` 固定 `yaml_only`，帶了會發 `CONFIG_OVERRIDE_IGNORED` | Console **不送** `storage`／`checkpoint_dir`／`log_dir`；三個鍵標 `STORED_ONLY` | 避免每個 run 都帶噪音告警；誠實標示無效參數 |
| D-28 | `model.*` → `minimax.*` | Architecture §11.4：一律映射 | Bridge 會驗證「實際生效的 MiniMax URL」，而種子預設是 Anthropic 網域 | **只在 `model.apiKey` 有值時**才送 `minimax.*` 與 `MINIMAX_API_KEY` | 否則出廠設定下每個 run 都被 Bridge 以 `outbound_not_allowed` 422 拒絕 |
| D-29 | `ConfigResponse` 欄位 | Architecture §11.2：11 欄 | US-S-08、遮罩、型別控制項 | 增加 `hasValue`、`options`、`min`、`max`、`impactNote`、`effect` | 皆為 UI 必需的中繼資料（附錄 C 為 SSOT）；除 `impactNote`（存 `system_configs.impact_note`，W3-B1 任務書與 V5）外不入 DB |
| D-30 | execute 的檢查順序與狀態碼 | PRD §7.1.5：僅提 409 | Architecture §6(c)：409／422／502 | 固定 10 級驗證順序（§1.2.1），QA 可逐項斷言 | |
| D-31 | execute 可接受的專案狀態 | W3：`READY／DRAFT／FAILED`；W3-B2 任務書另含 `COMPLETED` | 附錄 B.1：`DRAFT→EXECUTING`、`FAILED→EXECUTING`、`COMPLETED→EXECUTING` 都不是合法轉移（`COMPLETED` 只能 `→ARCHIVED`） | 接受 `DRAFT`／`READY`／`FAILED`／`COMPLETED`（只擋 `EXECUTING`、`ARCHIVED`）；`DRAFT`／`FAILED` 在同一交易內先 `→READY` 再 `→EXECUTING`（兩步都合法）；`COMPLETED` 屬系統重設（§3.5.3） | 不違反 B.1 的手動轉移表，又保留任務書的可用性；`COMPLETED` 專案補了新任務後可再跑（沒有可執行任務則由 7c 擋下） |
| D-32 | `/metrics` 串流的重播 | PRD §7.1.7：每個 event 帶單調遞增 id，重連從 `Last-Event-ID` 重播 | 三個事件都是 latest-wins 的狀態快照 | **收斂重播**：重連先送各一則最新快照，不重播歷史 | 對快照語意等價；省去為歷史指標再存一份 |
| D-33 | 審核產生後續批次時如何回報 | PRD：`204 No Content` | 需要告訴客戶端新 run id | 204 保持，新 run id 放回應標頭 `X-Follow-Up-Run-Id`（CORS 已暴露） | 不違反主控的 204 裁決 |
| D-34 | Phase 2 `POST /tasks/{id}/retry` | PRD：重試失敗任務 | 引擎無「單任務重跑」介面 | 維持 Phase 2 行為：只改 DB（`QUEUED`、`retryCount+1`），**不啟動 run**；實際重跑要 `execute`（範圍含該任務）或審核 `RETRY` | 避免兩條重試路徑語意混淆 |
| D-35 | `scope.limits` 的執行 | PRD US-E-10：單一任務／目標／整體 Token 上限 | 引擎只認整體 token_guard | 整體＝`tokenBudget`；任務／目標上限由 Console 依 token 事件歸因判定，超過走 `TOKEN_BUDGET_EXCEEDED`＋`:pause` | 不改引擎即可滿足 |
| D-36 | 分頁預設 | PRD §7.2：`size:10` 範例 | `steps`／`logs` 資料量大 | 預設 10／上限 100；`steps`、`logs` 預設 50／上限 200；`settings/history` 預設 20 | |
| D-37 | 時間格式 | 主控裁決：ISO-8601 帶 offset | Phase 2：`Instant` 輸出 `Z`、封包 `timestamp` 輸出伺服器 offset | 兩種都是合法 offset 表示；client 以日期函式解析，不比對字串 | 不改 Phase 2 已鎖的輸出 |
| D-38 | DAG 的 `status` | Architecture §7.1：狀態於讀取時疊加 | 歷史批次的當時狀態沒有保存 | 疊加**現況**並以 `statusAsOf` 明示 | 歷史重建不是本期需求；需要時可擴充 |
| D-39 | 監控端點的篩選參數 | PRD §7.1.6：端點表未列參數 | ADR-001 G-16：補 `runId`／`from`／`to` | `runId`、`from`、`to`（及趨勢的 `bucket`），預設與上限在 §1.3 | |
| D-40 | 評估指令的可執行檔白名單 | Architecture §8.3：「預設值由 W3 後端定案」 | — | 預設名單見附錄 D.3（可由 `console.security.evaluator-allowlist` 覆寫） | 本契約給出建議預設，後端可擴充並記入交卷 |
| D-41 | restore 的對象 | PRD §7.1.5：任何 run | 較舊的批次其 playbook 範圍可能已過期（任務被跳過／完成） | 只允許對專案**最新**的批次 restore，否則 409 `只能還原專案最新的執行批次` ⚠ | 避免以過期範圍重跑已 `SKIPPED` 的任務 |
| D-42 | Flyway 版號 | Architecture §11.4：V5＝`seed_engine_configs` | W3：V5＝`audit_log` | V5＝`seed_engine_configs`（含 `impact_note` 欄位）、V6＝`audit_log`（皆 W3-B1）、V7＝事件錨點與 token 樣本（W3-B2） | 版號不得撞；依任務書分工（W3-B2 任務書寫「需要欄位時開 V7」）；V1～V4 不動 |
| D-43 | 過期的待決審核項 | 未規定 | 新批次、resume、restore、cancel 後舊審核項會懸空 | 一律自動關閉並註明（§3.5.3、§3.6.3 備註） | 避免對已不存在的閘下決定 |
| D-44 | 頂列 Bridge 連線燈 | 設計稿有 | 沒有全域端點（`/actuator/health` 只代表 console-api） | `NotificationSummaryResponse` 加 `bridgeConnected`／`bridgeCheckedAt` | 沿用頂列已在輪詢的端點，不增加端點 |
| D-45 | 暫態告警的 SSE id | PRD：每個 event 帶 id | 暫態告警不持久化，無法重播 | 不帶 `id:` 行 | 避免與日後配置的子序號撞號而被客戶端去重誤丟 |
| D-46 | `pendingSignoffs` 的計數範圍 | Architecture §11.1：只定形狀 | W3-B1 任務書：projects＋goals＋tasks＋import_records 中 `signed_off=false` 且未軟刪／未 REJECTED；ADR-002 前端現況：專案＋草案專案底下的目標 | 專案、目標、任務三表中未 signoff 且未軟刪的列，加上匯入記錄中 `PARSED`／`REVIEWING` 且未 signoff 者（§1.4.1） ⚠ | 每個未簽核的列都是一次待做的 signoff（執行閘要求三層全簽）；`UPLOADED`／`PARSING` 的記錄尚無可簽核內容，計入會讓「從未解析的上傳」使徽章永遠不歸零 |
| D-47 | SSRF 的 loopback 例外 | W3-B1 任務書：host 字面列於 allowlist 即不檢查解析後 IP 的類別 | NFR-SEC-04：禁私網／loopback／link-local | loopback（IP 字面或 `localhost`）在 allowlist 內才放行，**不設額外開關**；`link_local`／`private_ip` 一律拒絕，allowlist 內的名稱解析到它們＝`dns_rebinding`（§1.5.7） | 採任務書的「不加開關」以縮小設定面，但不採「allowlist 內全免檢」：否則被攻陷的 allowlist 名稱可把請求導向內網 |
| D-48 | 路徑 B 的 URL 組法 | W3-B1 任務書：`POST {model.apiUrl}/chat/completions`（base URL 須含 `/v1`） | 種子預設值 `https://api.anthropic.com`、常見的 `https://api.openai.com` 與本機假伺服器都不含 `/v1` | 已以 `/chat/completions` 結尾照用；以 `/v1` 結尾附加 `/chat/completions`；其餘附加 `/v1/chat/completions`（§3.3.3） | 兩種寫法都能用，不會出現 `/v1/v1`；E2E 的假伺服器路徑固定為 `/v1/chat/completions` |

### 6.2 與五份任務書的差異（衝突時以契約為準）

W3-B1／B2、W4-F1／F2、W4-QA 五份任務書寫於本契約之前，都規定「衝突時以契約為準」。下表列的是**字面不同**的點：實作者照契約；主控若要改採任務書的寫法，請改契約，不要各包各自偏離。Flyway 版號、`impact_note` 欄位、限流屬性名、loopback 例外、`COMPLETED` 專案可再執行、`audit_log` 已在本契約內對齊任務書（§0.5、§0.4、D-13、D-31、D-47），不在此列。

| # | 項目 | 任務書字面 | 契約 | 出處 |
|---|------|-----------|------|------|
| 1 | playbook `step_id` | W3-B2：`T001…` | `G<目標位置>-T<任務位置>`（批次範圍內的 1 起序號） | D-06、§3.4.4 |
| 2 | 錯誤 `reason` 的風格 | W3-B1／B2：英文蛇形（`rate_limited`、`bounded_gate_violation`、`draft_expired`、`empty_document`、`missing_dependencies`、`redirect_not_allowed`） | 中文逐字常數：`超過每分鐘 100 次請求上限`、`解析結果未通過有界閘`、`草案已失效，請重新解析`、`無法從檔案擷取文字`、`所選目標依賴未完成的前置目標`；測試連線遇 3xx 以 200＋`success=false` 表達，不是錯誤碼 | 附錄 B；與 PRD 逐字 reason 及 Phase 2 既有的中文 reason 同風格 ⚠ |
| 3 | 未簽核的明細 | W3-B2：`details.unsignedIds[]` | `details.unsignedProjectId／unsignedGoalIds／unsignedTaskIds`（分開列，前端可直接標示哪一層未簽） | §1.2.1 第 5 項 |
| 4 | 路徑 B 的請求內容 | W3-B1：只有一則 user 訊息；`{apiUrl}/chat/completions` | system＋user 兩則訊息，另帶 `top_p`、`stream:false`；URL 規則見 D-48 | §3.3.3 |
| 5 | 解析路徑的選擇 | W3-B1：`specDir` 非空才走規格路徑 | 另探測 `executionPath`（ADR-001 D18 與 W3 原始決策）；規格存在但被拒＝fail-closed，不退回 LLM | §3.3.1、D-03 |
| 6 | `parsedResult.path` 的大小寫 | W3-B1：`sdd／llm／decompose` | `SDD／LLM／DECOMPOSE`（主控「列舉全大寫」裁決） | §0.2 |
| 7 | 有界閘 422 的 `reason` | W3-B1：`bounded_gate_violation` | `解析結果未通過有界閘`；`errors[]` 項目的 `gate／detail／location` 與任務書相同 | §1.1.3 |
| 8 | 事件時間軸的資料來源 | W3-B2、W4-F2：`task-trend` 另回 `events[]` | `task-trend` 依 PRD §7.1.6 只回 `List<TaskTrendPoint>`；時間軸改用 `GET /executions/{runId}/steps` | §4.3 M-12 |
| 9 | 自治等級 3 的行為 | W4-QA、W4-F2：「Level 3 啟動，跑到 COMPLETED」 | Level 3 在目標邊界暫停、等 `GOAL_COMPLETED` 審核：多目標專案需 APPROVE 一次才跑完（E2E-03 用 Level 4 一路跑完） | §3.6.1 |
| 10 | 引擎 halt 的處置 | W3-B2：`ESCALATION`／`halted` 判 `ESCALATED` 並建審核項 | 只有 `ESCALATION` 判 `ESCALATED`；halt、異常結束、orphaned 維持 `FAILED`，等級 1～4 不建審核項、等級 5 以上才建 | D-18、§3.5.2 |
| 11 | 審核 `SKIP` | W3-B2：任務標跳過後 `:resume` | Bridge 的 resume 只收 `PAUSED`，ESCALATION 後 run 已是 `FAILED`；故標跳過並以剔除該任務的新 playbook 開後續批次 | D-20 |
| 12 | 測試用的 mock 旗標 | W3-B2：`console.execution.mock-cli=true` | `console.execution.mock-env`（map；值即 `MOCK_CLAUDE_*`，只有 map 才帶得出各情境的延遲、失敗樣式與 trace 路徑） | §3.4.2、附錄 D.2 |
| 13 | 事件位移 | W3-B2：存記憶體 | 存 DB 的 `execution_runs.console_last_seq`（V7），console-api 重啟不丟事件 | §3.5.4 |
| 14 | Dashboard「本週完成任務數」 | W4-F2：取 `metrics`（from＝本週一） | `metrics` 只有比率與分布、沒有完成任務數；改以 `task-trend` 各桶 `completed` 加總（近似值） | §4.6 G-G3 |
| 15 | Bridge 健康探測環的容量 | W3-B2：120 筆（約 1 小時） | 2,880 筆（24 小時），因為監控視窗預設 24 小時，`agentAvailability` 才有足夠樣本 | §3.1、§3.8.1 |

---

## 附錄 A　狀態機速查（本期涉及的部分）

**A.1 執行批次**（六態寫入 PG；Bridge 八態折疊）

| 轉移 | 觸發 |
|------|------|
| `INITIALIZING→RUNNING` | Bridge 引擎啟動（`status RUNNING`） |
| `RUNNING→PAUSED` | pause 後在步驟邊界（Bridge 先 `PAUSING`，折為 `RUNNING`） |
| `PAUSED→RUNNING` | resume／restore／審核 `APPROVE` |
| `RUNNING／PAUSED→CANCELLED` | cancel／審核 `REJECT`（Bridge 先 `CANCELLING`，折為 `RUNNING`；`PAUSED` 即時收尾） |
| `RUNNING→COMPLETED` | 引擎正常結束 |
| `RUNNING→FAILED` | 升級（ESCALATION）、Token halt、異常結束、Bridge 孤兒回收 |
| 終態或 `PAUSED→RUNNING` | restore（終態 run 重新進行；SSE 須重連） |

**A.2 審核項**：`PENDING→APPROVED／REJECTED／RETRIED／SKIPPED`（人工決定）；`PENDING→REJECTED`（系統自動關閉：新批次取代、cancel、restore）；`PENDING→APPROVED`（以手動 resume 處理）。

**A.3 匯入記錄**：見 §1.1 的狀態圖與表。

**A.4 專案／目標／任務**：手動 API 遵守 PRD 附錄 B；執行引擎事件與審核決定造成的結果見 §3.5.2、§3.5.3（含 R-goal）。

---

## 附錄 B　錯誤 `reason` 常數總表（前後端共用；逐字）

HTTP 狀態與端點見各小節。**404 沿用 Phase 2：`reason` 省略，只有 `message`（樣板見 B.3）。**

### B.1 Phase 1+2 既有（不變）

| HTTP | reason |
|------|--------|
| 400 | `MALFORMED_REQUEST_BODY` |
| 401 | `UNAUTHENTICATED`、`TOKEN_EXPIRED`、`TOKEN_INVALID`（登入端點另有 `INVALID_CREDENTIALS`、`INVALID_REFRESH_TOKEN`） |
| 403 | `ACCESS_DENIED` |
| 409 | `已 signoff`、`目前狀態不可重試`、`RUNNING 狀態的任務不可刪除` 等 Phase 2 常數 |
| 400／409 | `命令含禁用字元`（400）、`依賴成環`（400；執行時偵測到成環為 409，同字串） |

### B.2 Phase 3～6 新增

| 區 | HTTP | reason（逐字） | `details` 鍵 |
|----|------|----------------|--------------|
| 通用 | 429 | `超過每分鐘 100 次請求上限` | `limit,windowSeconds,retryAfterSeconds` |
| 通用 | 502 | `引擎橋接服務無法連線` | — |
| 通用 | 504 | `引擎橋接服務逾時` | — |
| 通用 | 502 | `引擎橋接服務錯誤` | `bridgeStatus,bridgeReason` |
| 匯入 | 400 | `未提供檔案` | — |
| 匯入 | 400 | `檔案是空的` | — |
| 匯入 | 413 | `檔案超過 10MB 上限` | `limitBytes` |
| 匯入 | 415 | `只支援 .md／.pdf／.docx 檔案` | `extension,allowed` |
| 匯入 | 422 | `檔案內容與副檔名不符` | `extension` |
| 匯入 | 422 | `檔案不是有效的 UTF-8 文字` | — |
| 匯入 | 422 | `PDF 已加密，無法擷取文字` | — |
| 匯入 | 422 | `檔案已損毀，無法讀取` | — |
| 匯入 | 422 | `無法從檔案擷取文字` | — |
| 匯入 | 409 | `解析中，請稍候` | `status` |
| 匯入 | 409 | `已 signoff，不可重新解析` | `signedOffBy,signedOffAt` |
| 匯入 | 409 | `匯入記錄狀態不允許此操作` | `action,status` |
| 匯入 | 422 | `解析結果未通過有界閘` | `path`；`errors[]` 項目帶 `gate,detail,location` |
| 匯入 | 422 | `SDD 規格檢查未通過` | `bridgeReason,detail` |
| 匯入 | 409 | `草案已失效，請重新解析` | `draftId` |
| 匯入 | 409 | `草案尚未 signoff，不可確認匯入` | `status,signedOff` |
| 匯入 | 409 | `已匯入` | `projectId` |
| 執行 | 409 | `未經人工審批的草案不可執行`（PRD 逐字） | `unsignedProjectId,unsignedGoalIds,unsignedTaskIds` |
| 執行 | 409 | `專案正在執行中` | `projectId,runId` |
| 執行 | 409 | `專案狀態不允許執行` | `status` |
| 執行 | 400 | `所選範圍不合法` | `invalidGoalIds,invalidTaskIds` |
| 執行 | 409 | `所選任務或目標已完成` | `goalIds,taskIds` |
| 執行 | 409 | `所選目標依賴未完成的前置目標` | `missingGoalIds` |
| 執行 | 409 | `沒有可執行的任務` | — |
| 執行 | 422 | `步驟 prompt 超過 20000 字元上限` | `taskId,stepId,length,limit` |
| 執行 | 422 | `評估指令含禁用字元` | `taskId,chars` |
| 執行 | 422 | `評估指令不在可執行檔白名單` | `taskId,executable` |
| 執行 | 422 | `expectedOutputRegex 無法編譯` | `taskId` |
| 執行 | 422 | `範圍任務數超過單一批次上限 500` | `count,limit` |
| 執行 | 409 | `同專案同路徑已有執行中的批次` | `holderRunId` |
| 執行 | 422 | `引擎拒絕此請求` | `bridgeReason,violations` |
| 執行 | 409 | `目前執行狀態不允許此操作` | `action,runStatus,bridgeStatus` |
| 執行 | 409 | `找不到可續跑的 checkpoint` | — |
| 執行 | 409 | `引擎端已無此執行（工作區可能已清除）` | `runId` |
| 執行 | 409 | `只能還原專案最新的執行批次` | `latestRunId,latestRunNumber` |
| 執行 | 409 | `審核項已處理` | `status,decidedBy,decidedAt` |
| 執行 | 409 | `此審核項不允許該決定` | `kind,decision,allowedDecisions` |
| 監控 | 400 | `時間範圍不合法` | `from,to` |
| 監控 | 400 | `不支援的報表格式` | `format,supported` |
| 監控 | 501 | `PDF 報表尚未提供（W5）` | — |
| 設定 | 403 | `僅 ADMIN 可揭露敏感參數` | — |
| 設定 | 400 | `參數值不符合型別或驗證規則` | `valueType,validationRule,min,max,options` |
| 設定 | 400 | `halt_threshold_pct 必須大於 compact_threshold_pct`（PRD 逐字） | `compactThresholdPct,haltThresholdPct` |
| 設定 | 400／422 | `目標位址未通過 SSRF／allowlist 檢查`（儲存、匯入時 400；測試連線 422） | `host,violation`（`violation` ∈ `malformed_url,scheme,userinfo,loopback,link_local,private_ip,not_in_allowlist,dns_rebinding`） |
| 設定 | 409 | `敏感參數更新需二次確認（confirm=true）` | `category,key` |
| 設定 | 409 | `敏感參數重置需二次確認（confirm=true）` | `category,key` |
| 設定 | 400 | `設定檔格式錯誤` | `problem` |
| 設定 | 413 | `設定檔超過 1MB 上限` | `limitBytes` |
| 設定 | 415 | `只接受 JSON 設定檔` | — |

### B.3 404 訊息樣板（`reason` 省略）

`匯入記錄不存在或已刪除：<id>`、`專案不存在或已刪除：<id>`、`執行批次不存在或已刪除：<id>`、`執行批次不存在或不屬於此專案：<id>`、`checkpoint 不存在或不屬於此執行：<id>`、`審核項不存在或不屬於此執行：<id>`、`告警不存在：<id>`、`設定分類不存在：<category>`、`設定鍵不存在：<category>.<key>`。

---
## 附錄 C　設定鍵目錄（50 鍵；`ConfigCatalog` 與 V5 `validation_rule` 的唯一真相源）

欄位：`validationRule`＝Java 正規表示式（對完整字串比對，寫入 `system_configs.validation_rule`）；`min／max`＝數值範圍（含邊界；`FLOAT` 亦同）；`effect`：**E**＝ENGINE、**C**＝CONSOLE、**S**＝STORED_ONLY、**U**＝UNVERIFIED（定義見 §1.5）。除特別註明，`impactNote` 為 null。「新批次起生效」指已在跑的批次沿用啟動時的值（引擎設定在 spawn 時物化）。

### C.1 `model`（10）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote`（US-S-08） |
|----|------|------|------------------------------|:------:|--------------------------|
| `provider` | ENUM | `ANTHROPIC` | `^(ANTHROPIC\|OPENAI\|LOCAL\|CUSTOM)$` | S | 僅為 Console 抽象層欄位；引擎是 MiniMax＋Claude CLI 雙腦，不會依此切換 |
| `apiUrl` | STRING | `https://api.anthropic.com` | `^https?://[^\s/?#][^\s]*$`；另過 SEC-04（§1.5.7 的 1～5） | E（`apiKey` 有值時） | 與 MINIMAX_BASE_URL 同受 SEC-04 allowlist 檢查；新批次起生效；也用於匯入解析（路徑 B） |
| `apiKey` | ENCRYPTED | （空） | `^.{0,512}$` | E | 加密儲存；新批次起使用新金鑰；留空＝不再帶 MiniMax 設定 |
| `name` | STRING | `claude-sonnet-4-20250514` | `^[A-Za-z0-9._:/\-]{1,100}$` | E（`apiKey` 有值時） | 新批次起生效；也用於匯入解析 |
| `maxTokensPerRequest` | INTEGER | `8192` | `^[1-9][0-9]{0,5}$`；1～200000 | C | 只影響匯入解析（路徑 B）的 `max_tokens`；引擎無對應欄位 |
| `temperature` | FLOAT | `0.3` | `^[0-9](\.[0-9]+)?$`；0～2 | C | 只影響匯入解析（路徑 B） |
| `topP` | FLOAT | `0.9` | `^[01](\.[0-9]+)?$`；0～1 | C | 只影響匯入解析（路徑 B） |
| `timeout` | INTEGER | `120` | `^[1-9][0-9]{0,2}$`；1～600 | E | 引擎 `minimax.timeout_seconds` 與匯入解析逾時；測試連線上限 10 秒 |
| `rateLimitPerMinute` | INTEGER | `60` | `^[1-9][0-9]{0,4}$`；1～10000 | S | 目前不影響任何呼叫 |
| `enableKernelBrain` | BOOLEAN | `false` | `^(true\|false)$` | E（`apiKey` 有值時） | 開啟後引擎的 Brain 可改寫失敗步驟並可能觸發升級；新批次起生效 |

### C.2 `agent`（9）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `defaultAutonomyLevel` | INTEGER | `3` | `^([1-9]\|10)$`；1～10 | C | 只改之後匯入與執行表單的預設值，不改動既有專案 |
| `maxConcurrentTasks` | INTEGER | `3` | `^[1-9][0-9]?$`；1～32 | S | 引擎序列執行，目前不生效（Architecture L-1） |
| `taskTimeout` | INTEGER | `600` | `^[1-9][0-9]{1,4}$`；10～86400 | E | 新批次的單步逾時（秒）；同時是「任務執行過長」告警門檻的基準（×`monitor.alertTaskDurationMultiplier`） |
| `maxRetries` | INTEGER | `3` | `^([0-9]\|1[0-9]\|20)$`；0～20 | E | 新批次的預設最大重試次數（每個任務自己的 `maxRetries` 優先） |
| `retryBackoffMs` | INTEGER | `5000` | `^[0-9]{1,7}$`；0～3600000 | S | 引擎無對應欄位 |
| `retryBackoffMultiplier` | FLOAT | `2.0` | `^([1-9]\|10)(\.[0-9]+)?$`；1～10 | S | 引擎無對應欄位 |
| `checkpointInterval` | INTEGER | `5` | `^[1-9][0-9]{0,3}$`；1～1000 | S | Bridge 於每個步驟邊界自行記錄歷史快照，此值不生效 |
| `enableAutoMutation` | BOOLEAN | `false` | `^(true\|false)$` | U | 與引擎演化開關的對映尚未驗證（Level 6+） |
| `enableSelfEvolution` | BOOLEAN | `false` | `^(true\|false)$` | U | 同上（Level 7+） |

### C.3 `execution`（10）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `globalTokenBudget` | LONG | `1000000` | `^[1-9][0-9]{0,11}$`；1～1000000000000 | C | 新批次的預設 Token 預算；不改動既有批次 |
| `tokenBudgetWarningThreshold` | FLOAT | `0.8` | `^0\.[0-9]{1,2}$`；0.01～0.99 | C | 即時生效於進行中的批次（告警每次評估時讀取） |
| `maxParallelGoals` | INTEGER | `2` | `^([1-9]\|1[0-6])$`；1～16 | S | 引擎序列執行，目前不生效 |
| `dagSchedulerStrategy` | ENUM | `TOPOLOGICAL` | `^(TOPOLOGICAL\|PRIORITY\|SHORTEST_FIRST)$` | C | 影響新批次同層目標的排序 |
| `enableRollback` | BOOLEAN | `true` | `^(true\|false)$` | S | 引擎無對應欄位 |
| `logRetentionDays` | INTEGER | `90` | `^[1-9][0-9]{0,3}$`；1～3650 | C | 日誌與 Bridge 工作區的保留天數（清理排程依此） |
| `compactThresholdPct` | INTEGER | `80` | `^([1-9]\|[1-9][0-9])$`；1～99；**須小於 `haltThresholdPct`** | E | Token Guard：context 達此百分比觸發 `/compact`；新批次起生效；不得經 Console 提高上限以繞過安全收斂（NFR-SEC-05） |
| `haltThresholdPct` | INTEGER | `90` | `^([2-9]\|[1-9][0-9]\|100)$`；2～100；**須大於 `compactThresholdPct`** | E | Token Guard：context 達此百分比儲存 checkpoint 並停機；新批次起生效 |
| `autoResume` | BOOLEAN | `true` | `^(true\|false)$` | E | halt 後引擎是否等待並自動續跑（會讓 run 長時間維持 RUNNING）；新批次起生效 |
| `maxAutoResumes` | INTEGER | `10` | `^([1-9]\|[1-9][0-9]\|100)$`；1～100 | E | 單次 playbook 最多自動恢復次數；新批次起生效 |

### C.4 `monitor`（6）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `refreshIntervalMs` | INTEGER | `3000` | `^[0-9]{3,5}$`；500～60000 | C | 前端輪詢間隔（通知摘要、監控儀表板） |
| `alertConsecutiveFailures` | INTEGER | `3` | `^([2-9]\|1[0-9]\|20)$`；2～20 | C | 「連續任務失敗」告警門檻；即時生效 |
| `alertAgentTimeoutSec` | INTEGER | `300` | `^[0-9]{2,5}$`；30～86400 | C | 「Agent 無回應」告警門檻（秒）；即時生效 |
| `alertTaskDurationMultiplier` | FLOAT | `2.0` | `^([1-9]\|1[0-9]\|20)(\.[0-9]+)?$`；1～20 | C | 「執行時間過長」＝`agent.taskTimeout` × 此倍數；即時生效 |
| `enableEmailNotification` | BOOLEAN | `false` | `^(true\|false)$` | S | 目前沒有郵件發送功能，只儲存 |
| `notificationEmail` | STRING | （空） | `^$\|^[^@\s]+@[^@\s]+\.[^@\s]+$` | S | 同上 |

### C.5 `autoclaude`（11）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `engineUrl` | STRING | `http://engine-bridge:8081` | `^https?://[A-Za-z0-9.\-]+(:[0-9]{1,5})?/?$` | C | 所有 Bridge 呼叫改走新位址；填錯會讓執行與監控失效 |
| `healthCheckPath` | STRING | `/health` | `^/[A-Za-z0-9_\-./]*$` | C | Bridge 健康探測路徑（Agent 可用率、頂列連線燈） |
| `eventBusType` | ENUM | `INTERNAL` | `^(INTERNAL\|KAFKA\|RABBITMQ)$` | S | 引擎只有 INTERNAL |
| `dalBackend` | ENUM | `FILE` | `^(FILE\|IN_MEMORY\|POSTGRESQL)$` | S | Bridge 固定用檔案型 checkpoint（`yaml_only`），此值不生效（ADR-001 D13） |
| `playbookPath` | STRING | `./playbooks` | `^.{1,500}$` | S | Bridge 自行管理 playbook 檔，不生效 |
| `claudeCommand` | STRING | `claude` | `^[A-Za-z0-9_.\-/\\:]{1,200}$`（不可含空白，引擎不做 shlex 切分） | E | 新批次起生效；E2E 設為 `aisdlc-mock-claude`；填錯會讓每個步驟在第一秒失敗 |
| `claudeExtraArgs` | STRING | （空） | `^[A-Za-z0-9_.=:,/@\- ]{0,500}$`（以空白切成陣列，每段須符合 §3.4.2） | E | 新批次起生效 |
| `claudeContinueFlag` | STRING | `--continue` | `^--[A-Za-z0-9\-]{1,60}$` | E | 新批次起生效 |
| `claudeEncoding` | STRING | `utf-8` | `^[A-Za-z0-9_\-]{1,30}$` | E | 新批次起生效 |
| `dbDsn` | ENCRYPTED | （空） | `^.{0,512}$` | S | Bridge 固定 `yaml_only`，不生效 |
| `dualReadResolution` | ENUM | `yaml_wins` | `^(yaml_wins\|db_wins\|fail_loud)$` | S | 同上 |

### C.6 `sdd`（4）

| 鍵 | 型別 | 預設 | `validationRule`／範圍／選項 | effect | `impactNote` |
|----|------|------|------------------------------|:------:|--------------|
| `engineUrl` | STRING | `http://engine-bridge:8081` | 同 `autoclaude.engineUrl` | C | 匯入路徑 A 的 `/sdd/compile` 位址 |
| `specFormat` | ENUM | `YAML` | `^(YAML\|JSON\|TOML)$` | U | 與 `/sdd/compile` 行為的對映尚未驗證 |
| `workflowEngine` | ENUM | `DYNAMIC` | `^(STATIC\|DYNAMIC\|ADAPTIVE)$` | U | 同上 |
| `validationLevel` | ENUM | `STRICT` | `^(LAX\|NORMAL\|STRICT)$` | U | 同上 |

合計 10＋9＋10＋6＋11＋4＝**50**。`model.apiKey` 與 `autoclaude.dbDsn` 的 `valueType=ENCRYPTED`、`is_encrypted=TRUE`。

---

## 附錄 D　常數與設定屬性

### D.1 上限與固定常數

| 常數 | 值 | 出處 |
|------|----|------|
| 匯入檔案大小 | 10 MB（10,485,760 bytes；multipart 請求 11MB） | US-I-01 |
| 設定檔大小 | 1 MB（1,048,576 bytes） | §1.5.10 |
| 文字匯入長度 | 2,000,000 字元 | §1.1.2 |
| 每個目標任務數／目標數 | ≤ 24／≤ 24（可下調不可上調） | §3.3.5 |
| 步驟 prompt 長度 | ≤ 20,000 字元（UTF-16 code unit） | §3.4.3、Architecture L-9 |
| 路徑 B 的 LLM 輸入長度 | ≤ 120,000 字元（`console.import.max-prompt-chars`） | §3.3.3 |
| 路徑 C 判斷門檻 | 全文 < 2,000 字元且無 Markdown 標題 | §3.3.1 |
| 審核 `comment` | ≤ 2,000 字元 | §1.2.11 |
| 設定 `value` | ≤ 4,000 字元（加密值 ≤ 512） | §1.5 |
| 遮罩字串 | `••••••••`（U+2022 ×8） | §1.5 |
| 加密佔位字串（匯出） | `<encrypted>` | §1.5.9 |
| 限流 | 100 次／60 秒／IP | §0.4 |
| SSE keep-alive／佇列 | 15 秒／1,000 框架 | §2.1 |
| 監控視窗上限 | 366 天；趨勢桶數 ≤ 1,000 | §1.3 |
| 命令黑名單字元（NFR-SEC-03 第 1、2 層） | `` ! ` > < ~ $ & ; ``（8 個）＋換行、回車、NUL（Bridge 另加） | SSOT：`AutoClaude/autoclaude/utils/shell_deny_chars.py` 的 `BASE_DENY_CHARS`；後端複製並於檔頭註明（W4 QA 腳本比對兩端字元集一致） |

### D.2 `console.*` 屬性（Spring，環境變數以 `CONSOLE_…` 覆寫）

| 屬性 | 預設 | 說明 |
|------|------|------|
| `console.security.outbound-allowlist` | `api.anthropic.com,api.openai.com,api.minimax.io,api.minimax.chat` | SEC-04 外呼 host 白名單（精確比對）；e2e／本機 profile 另加 `127.0.0.1,localhost`（loopback 在名單內才放行，§1.5.7） |
| `console.security.test-dns-overrides` | （空；僅 e2e） | 測試用 DNS 覆寫（`host: ip`），讓 `dns_rebinding` 可決定性重現 |
| `console.security.evaluator-allowlist` | 見 D.3 | 評估指令首個 token 的可執行檔白名單 |
| `console.security.rate-limit.enabled` | `true`（單元／整合測試 profile 為 `false`） | 限流開關；須有一支測試開著它驗第 101 次回 429 |
| `console.security.rate-limit.requests-per-minute` | `100` | |
| `console.security.rate-limit.trust-forwarded-for` | `false`（e2e 為 `true`） | 是否取 `X-Forwarded-For` 第一段作為客戶端 IP |
| `console.sse.keep-alive-seconds` | `15`（e2e 為 `2`） | |
| `console.sse.queue-size` | `1000` | |
| `console.import.max-prompt-chars` | `120000` | |
| `console.execution.mock-env` | （空；僅 e2e／test profile） | 附加到 Bridge 請求 `env` 的 `MOCK_CLAUDE_*` |
| `CONSOLE_ENCRYPTION_KEY`（環境變數） | 必填 | base64 的 32 bytes（AES-256-GCM）；缺少或長度不對＝啟動失敗 |
| `spring.servlet.multipart.max-file-size`／`max-request-size` | `10MB`／`11MB` | 匯入上傳（設定檔另有 1MB 檢查） |

### D.3 評估指令可執行檔白名單（建議預設，Architecture §8.3「預設值由 W3 後端定案」）

判定：取 `evaluatorCommand` 去前後空白後的**第一個以空白分隔的 token**，去掉路徑前綴與 `.exe`／`.cmd`／`.bat` 後綴，**不分大小寫**比對下列名單；不在名單 → execute 回 422 `評估指令不在可執行檔白名單`。

`pytest, python, python3, py, npm, npx, node, pnpm, yarn, mvn, mvnw, gradle, gradlew, java, dotnet, go, cargo, make, tsc, eslint, ruff, mypy, git`

不含 shell 與 shell 內建（`sh`、`bash`、`cmd`、`powershell`、`pwsh`、`echo`、`test`…）——引擎的評估器以平台原生殼執行（Windows 為 `cmd.exe`），白名單加上禁用字元集是兩層獨立防線。後端可擴充名單並記入交卷。

---

## 附錄 E　RTM 對照（契約位置與驗收情境）

「IT」＝後端整合測試（不在 §5 的 E2E 內）。

| RTM ID | 契約位置 | 驗收 |
|--------|----------|------|
| API-IMP-01、07 | §1.1.1 | E2E-01（上傳變體） |
| API-IMP-02 | §1.1.2 | E2E-01 |
| API-IMP-03、09 | §1.1.3、§3.3.3 | E2E-01（含有界閘變體） |
| API-IMP-04 | §1.1.4 | E2E-01 步驟 4、9 |
| API-IMP-05 | §1.1.6 | E2E-01 步驟 5、11 |
| API-IMP-06 | §1.1.8、§1.1.9 | E2E-01 步驟 3、14 |
| API-IMP-08 | §3.3.1、§3.3.2 | IT（假 Bridge：compile 200／各 422／不可達） |
| API-IMP-10 | §1.1 狀態圖與表 | E2E-01 步驟 13、IT（非法轉移矩陣） |
| API-SGN-01 | §1.1.5 | E2E-01 步驟 6～10 |
| API-SGN-02～04 | Phase 2 | Phase 2 測試；E2E-02 步驟 3～6 |
| API-EXE-01、11 | §1.2.1 | E2E-02、E2E-03 |
| API-EXE-02、03 | §1.2.4、§1.2.5 | E2E-04、E2E-08；手動 pause／resume 為 IT |
| API-EXE-04 | §1.2.6 | E2E-06 |
| API-EXE-05 | §1.2.3 | E2E-03 步驟 4；Bridge 不可達回 200 為 IT |
| API-EXE-06 | §1.2.7 | E2E-03 步驟 5、E2E-12 |
| API-EXE-07、DAG-01 | §1.2.8、§3.4.4 | E2E-03 步驟 6 |
| API-EXE-08 | §1.2.9 | E2E-03 步驟 7、E2E-07 |
| API-EXE-09 | §1.2.10 | E2E-07 |
| API-EXE-10 | §1.2.11、§3.6.3 | E2E-04、E2E-05 |
| API-EXE-12 | §1.2.1 第 10 項 | IT（同專案同路徑兩次 execute，Bridge 409＋補償）；E2E-02 步驟 7 為 Console 層檢查 |
| API-EXE-13 | §3.4 | E2E-03（mock trace 驗 prompt 與關鍵字）、IT（欄位逐項） |
| API-EXE-14 | §1.2.2 | E2E-03 步驟 13、E2E-05 步驟 7 |
| API-AUT-01～03 | §3.6.1、§3.6.2 | E2E-04（含 Level 2／3 對照） |
| API-AUT-04、05 | §3.6.2 | E2E-05 變體 V4；決策表單元測試 |
| API-AUT-06 | §3.6.1 | 單元（等級 6～10 行為同 5；`UNVERIFIED`） |
| API-MON-01～04、06 | §1.3.1～§1.3.4、§1.3.6 | E2E-03 步驟 9～13 |
| API-MON-05 | §1.3.5 | E2E-08 步驟 7 |
| API-MON-07 | §1.3.7 | E2E-03 步驟 15 |
| API-NTF-01 | §1.4.1 | E2E-04 步驟 3、E2E-05 步驟 3、E2E-08 步驟 5 |
| API-ALR-01、02 | §3.7 | E2E-08 |
| API-ALR-03 | §3.7 | E2E-05（`ENGINE_ESCALATION`）；連續失敗規則為單元（假事件序列） |
| API-ALR-04～06 | §3.7 | 單元（假時鐘與假探測環） |
| API-SSE-01～03 | §2 | E2E-03、E2E-04（重播）、E2E-12 |
| API-SET-01、02 | §1.5.1、§1.5.2 | E2E-09 步驟 1、8 |
| API-SET-03、04 | §1.5.3、§1.5.4 | E2E-09 步驟 2～7 |
| API-SET-05 | §1.5.5、§1.5.6 | E2E-09 步驟 10、11 |
| API-SET-06 | §1.5.7 | E2E-10 |
| API-SET-07 | §1.5.8 | E2E-09 步驟 16 |
| API-SET-08、09 | §1.5.9、§1.5.10 | E2E-09 步驟 12～14 |
| API-SET-10 | §3.4.2 | E2E-03（替身 `claude.command` 生效）、IT（物化表逐列） |
| NFR-SEC-03 | §1.1.4、§1.2.1 第 9 項 | E2E-01（消毒變體）、IT（第 2 層複驗與白名單） |
| NFR-SEC-04 | §1.5.7、§3.3.3 | E2E-10、E2E-01（`brain_unsupported`）、E2E-09 步驟 15 |
| NFR-SEC-05 | §1.5.3～§1.5.6、§1.5.10 | E2E-09 |
| NFR-OBS-01 | §5.0.4 A1 | E2E-03 步驟 14；每個 run 情境的共通後置斷言 A1 |
| US-I-01～10 | §1.1 | E2E-01（US-I-10＝有界閘變體；US-I-05、07、08＝步驟 2 的請求欄位） |
| US-E-01～02、10 | §1.2.1 | E2E-02、E2E-03、E2E-08 變體 V1 |
| US-E-03、09 | §2、§1.2.8 | E2E-03、E2E-12 |
| US-E-04～06 | §1.2.4～§1.2.6 | E2E-04、E2E-06、E2E-08 |
| US-E-07、08 | §1.2.11、§1.4.1 | E2E-04、E2E-05 |
| US-E-11 | §1.2.9、§1.2.10 | E2E-07 |
| US-M-01～07、09 | §1.3 | E2E-03、E2E-08；US-M-06 見 `executions` 列表（E2E-03 步驟 13） |
| US-M-08 | 純前端（§4.3 M-18） | 前端測試 |
| US-M-10 | §1.2.3、§1.3.1 | E2E-03 步驟 4、9 |
| US-S-01～08 | §1.5 | E2E-09、E2E-10 |
