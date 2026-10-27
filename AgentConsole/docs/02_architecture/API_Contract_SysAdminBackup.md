# API 契約 — 系統管理／資料庫備份（備份總覽與工作端點、sidecar 控制面檔案協定與指令、backup 類 reason 表、資料所有權、Prometheus 指標）

**版本**：v1.0｜**日期**：2026-10-28｜**作者角色**：Developer（契約檔棒，先於 S／K／F 三包）依 TCS 契約節（§C0～§C6）逐表抄成（**TCS 為真相，本檔不得與它不同**）
**來源 TCS**：`AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md`（Stage-2 凍結版；抄自其 L281～L385〈契約節〉）｜digest `sha256:14e4e2ffe1bc11f7fd18c7775c008dcde78aada6a9f6f29892dc30c472ed5795`
**上位 PRD**：`docs/01_requirements/Console_SysAdmin_Backup_PRD.md` v0.4＋〈勘誤一〉1-1～1-15｜digest `sha256:848c2acfae30d3034205d647effd5000189c776f29db743629d4a4bdb1d0800a`
**SDD 鍵**：`agentconsole-sysadmin-backup`（Console 單半；階段一加階段二合訂一份）
**讀者**：sidecar 維護者（bash、Prometheus）、後端開發者（Spring Boot 4.1／Java 21）、前端開發者（Next.js 16）、QA（依本契約驗收）
**與前代契約的關係**：本檔**不改**凍結的 [API_Contract_P3-6.md](API_Contract_P3-6.md)；封包與錯誤格式沿既有 `ApiResult<T>`／`ApiError`（見 C0）；backup 類 reason（〈backup 類 reason 表〉）**不進** `frontend/lib/api/reasons.ts`（它與 P3-6 附錄 B 雙向鎖；TCS R-BK-60、R-BK-61）。`Architecture.md` 的連動修改（TCS §5.7 K 包列：§2.5、§5.1、§7.2、§8.2、§9.4、§11.1）不在本檔範圍。
**機器可讀版**：本檔不另附 OpenAPI 檔。機器可讀的真相源是 backend 執行期的 `/v3/api-docs`（springdoc），入庫快照為 `frontend/lib/api/schema.d.ts`；路徑與操作數的釘值見 TCS R-BK-59。兩者與本文衝突時以本文為準並回報修正。
**對應需求**：根層 `docs/01_requirements/Console_SysAdmin_Backup_PRD.md` 的 FR-BK-01～FR-BK-10 與 §5～§9（含 TCS 增量 AC `AC-BK-04-6`＝PRD〈勘誤一〉1-1）；TCS 為 `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md`。

> **使用方式**（沿 TCS 文件資訊〈讀法〉，L26）：S 包（sidecar＋compose＋Prometheus＋README）照 C1、C2、C6 與〈附錄 A〉施工；K 包（console-api）照 C3～C5，並以 C1 為讀取端；F 包（前端）照 C3 取欄位形狀與錯誤、〈backup 類 reason 表〉取中文訊息。兩兩共同的只有 C1（控制面檔案協定：S 寫 K 讀）與〈backup 類 reason 表〉。
> **座標約定**：文內的 `R-BK-nn`、`D-BK-Tnn`、`Q7`、`F-03`、`B-24` 與 `AC-…`／`AT-…` 皆為 TCS 或 PRD 的座標，本檔不展開其全文；一律以 TCS 為準，對照見〈附錄 B〉。

**版本沿革**

| 版本 | 日期 | 範圍 | 對應來源 |
|------|------|------|----------|
| v1.0 | 2026-10-28 | 初版：控制面檔案協定 v1（C1）、sidecar 指令（C2）、console-api 端點與設定（C3）、backup 類 reason 表、資料所有權 `console.backup_jobs`（C5，Flyway V15，階二）、Prometheus 指標與規則（C6）、環境變數與設定總表（附錄 A） | TCS-SysAdminBackup-20261027 §C0～§C6（鍵 `agentconsole-sysadmin-backup`） |

---

## C0 共通約定

> 來源：TCS §C0（L285～L292）。

| 項目 | 約定 |
|---|---|
| 命名 | 對外 API 一律 camelCase；控制面檔案（§C1）與 sidecar 輸出一律 snake_case；兩者對映規則：控制面檔案鍵 snake_case → API 鍵 camelCase（例 `last_success_at`→`lastSuccessAt`、`detail_tail`→`detailTail`、`endpoint_host`→`endpointHost`），值一律不動 |
| 封包 | 成功沿既有 `ApiResult<T>`：`{code:200, message:'success', data, timestamp, traceId}`；失敗沿 `ApiError`：`{code, message, reason?, errors[{field,message}], details?, timestamp, traceId}`；任何失敗沒有 `data` |
| 時間 | 所有時間戳為 ISO-8601 UTC 帶 `Z`（控制面檔案與 API 皆然）；排程時區（`schedule.json.tz`，預設 `Asia/Taipei`）只用於計算 `nextRunAt`、`lastDueAt` 與前端「排程時區」註記 |
| 缺鍵與 null | `null`＝量不到或不適用於該資料；非 ADMIN 的 `detailTail`、`requestedBy`、`detail` 為 `null`（或鍵缺席，兩者等價，測試兩者皆接受）；資料區塊 `null`＝該區塊因 `control.reason` 或來源失敗而不提供，**不得**以空陣列或 0 代替 |
| 角色 | 所有 GET：VIEWER 以上；`POST /api/v1/sysadmin/**`：僅 ADMIN；其他方法沒有對映 |
| 單位 | 大小＝位元組；耗時＝秒（整數）；`exportAgeSeconds`、`heartbeatAgeSeconds` 為相對 console-api 時鐘（`Clock`）的整數秒（無條件捨去） |

## C1 控制面檔案協定 v1（兩個具名卷；寫入一律「寫 `.tmp` → 同目錄改名」；檔 0644、目錄 0755；內容絕不含機密）

> 來源：TCS §C1（L296～L306）。

| 路徑（容器內） | 寫入者 → 讀取者 | 內容（`schema_rev` 恆為整數 1） |
|---|---|---|
| `/backup-req/<uuid>.json` | console-api → sidecar（`:ro,nocopy`） | `{"schema_rev":1,"id":"<uuid>","type":"full｜diff｜verify","requested_at":"<ISO Z>","expires_at":"<ISO Z>"}`；`id` 須等於檔名；`expires_at＝requested_at＋request-ttl-seconds`；終態後由 console-api 刪、啟動時清逾 24 小時殘檔 |
| `/backup-out/export/info.json` | 匯出子行程 → console-api（`:ro,nocopy`） | 成功：`{"schema_rev":1,"generated_at":"<ISO Z>","ok":true,"info":[<pgbackrest --output=json info 原輸出，陣列>],"retention":<物件｜null>,"repos":[{"repo":1,"type":"posix","endpoint_host":null,"local":true},{"repo":2,"type":"s3","endpoint_host":"minio","local":true}]}`；失敗：`{"schema_rev":1,"generated_at":"<ISO Z>","ok":false}`（無其餘鍵）。`retention`＝`{"repo1":{"full":4,"diff":7},"repo2":{"full":4,"diff":null},"logical_days":28}`，欄內 `null`＝該設定未設，整個 `retention` 為 `null`＝解析不到（不填預設值）。`info` 內容為 pgBackRest 原樣輸出（F-03：`backup[].{label,type,timestamp{start,stop},info{size,repository{size}},database{repo-key},prior,error}`、`repo[].{key,status{code,message}}`、`status{code,lock{backup{held}}}`） |
| `…/export/logical.json` | 匯出子行程 → console-api | 成功：`{"schema_rev":1,"generated_at":"<ISO Z>","ok":true,"objects":[{"name":"aisdlc-20261026-183000.dump","size":1048576,"modified":"<ISO Z>"}]}`；`mc` 失敗：`{"schema_rev":1,"generated_at":"<ISO Z>","ok":false}`（不寫部分清單）；至多每 300 秒重寫 |
| `…/export/schedule.json` | entrypoint（啟動 root 階段，一次）→ console-api | `{"schema_rev":1,"tz":"Asia/Taipei","entries":[{"job":"full","cron":"0 2 * * 0"},{"job":"diff","cron":"0 2 * * 1-6"},{"job":"dump","cron":"30 2 * * *"},{"job":"verify","cron":"0 4 * * 3"},{"job":"expire","cron":"0 3 * * *"},{"job":"wal_clean","cron":"30 3 * * *"}]}`（依 crontab 出現序；`job` 值域封閉，見 D-BK-T8） |
| `…/export/jobs/<job>.json`（job＝`full`、`diff`、`dump`、`verify`） | `job-run.sh` → console-api | `{"schema_rev":1,"job":"full","last":{"trigger":"scheduled｜manual","status":"running｜succeeded｜failed｜interrupted","rc":0,"reason":null,"started_at":"<ISO Z>","finished_at":"<ISO Z>｜null","detail_tail":"<已遮罩、最後 ≤2000 字元>","note":null},"last_success_at":"<ISO Z>｜null"}`；`running` 時 `rc`、`finished_at` 為 `null`；`failed` 的 `reason`∈{`script_failed`（rc≠0）、`lock_timeout`（rc 75）}；`interrupted` 的 `reason`＝`interrupted`；`note` 為 `null` 或 `"locking:unavailable"`；`last_success_at` 只在成功時更新、失敗與中斷不改動 |
| `…/export/heartbeat` | runner 迴圈（每輪）→ console-api | `{"schema_rev":1,"ts":"<ISO Z>","lock_held":false}`；`lock_held` 由 `/proc/locks` 比對鎖檔 dev:ino 得出，不得以取鎖探測（runner、export 對維護鎖零次 `flock` 呼叫） |
| `…/results/<uuid>.json` | runner 與其背景子行程 → console-api | `{"schema_rev":1,"id":"<uuid>","type":"full｜diff｜verify","status":"running｜succeeded｜failed｜rejected","reason":null,"rc":null,"started_at":"<ISO Z>｜null","finished_at":"<ISO Z>｜null","detail_tail":"<已遮罩尾段>"}`；**存在＝已撿**，`running` 標記的 `started_at`＝撿起時刻（非 null；孤兒寬限據此判，R-BK-20）；`rejected` 的 `reason`∈{`busy`、`rejected_invalid`、`expired`}；`failed` 的 `reason`∈{`script_failed`、`interrupted`、`lock_timeout`}（缺 `reason` 視為 `script_failed`；`control_write_failed` 只由 console-api 補償 UPDATE 寫入 DB，sidecar 不寫）；留最近 50 份（超過依 mtime 刪最舊） |

鎖檔：`/run/backup-ctl/maintenance.lock`（sidecar 本地，不在任何共享卷）。控制面檔案不含請求檔原文、不含任何金鑰、密碼或 cipher。

## C2 sidecar 指令（皆在 `AgentConsole/docker/pgbackrest/scripts/`、映像內 `/usr/local/bin/`；測試縫環境變數見 D-BK-T16）

> 來源：TCS §C2（L310～L316）。D-BK-T16 的測試縫環境變數已彙整於〈附錄 A〉。

| 指令 | 行為與輸出 |
|---|---|
| `job-run.sh <job> <scheduled｜manual> [<uuid>]` | `<job>`∈{full,diff,dump,verify} 對映 `backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`verify-backup.sh`；以命令形 `flock -o`（`--close`）包裝；排程等鎖至 `JOB_LOCK_WAIT_SECONDS`、手動不等待；取得鎖後寫 `jobs/<job>.json`（`running`）→ 執行腳本（stdout、stderr 原樣透傳並各自同步擷取）→ **持鎖期間**寫終態（遮罩、取最後 2000 字元；有 `<uuid>` 時一併寫 `results/<uuid>.json`），之後才釋放鎖；結束碼＝腳本 rc，唯手動 busy 與排程 lock_timeout 為 75；鎖檔開不了／狀態檔寫不了皆 fail-open（WARN；前者記 `note=locking:unavailable`）；**不碰** `.last_backup_status` |
| `backup-ctl-runner.sh [--once]` | 迴圈（`--once`＝只做一輪）：每輪先清掃 interrupted、原子更新 `heartbeat`、必要時以 `timeout $BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` 背景啟動匯出子行程（前一個未結束則略過）、掃請求目錄（階段二）：撿最舊且 `results/<id>.json` 尚不存在的合法請求 → 先寫 `results`（`running`，`started_at`＝撿起時刻）→ 背景子行程跑 `job-run.sh <type> manual <id>`（終態由 `job-run.sh` 持鎖時寫入，R-BK-48；子行程僅在 rc 75 時補寫 `rejected`／`busy`）；**永不等待子行程**；非法請求依 R-BK-47 處理 |
| `backup-ctl-export.sh` | 一輪匯出（受單一實例鎖 `export.lock`〔非維護鎖〕保護，重疊則立即結束碼 0）：清掃 interrupted → 原子寫 `info.json` → （距上次 ≥300 秒才）寫 `logical.json`；失敗只寫 `ok:false`、結束碼 0 |
| `backup-ctl-export.sh schedule` | 由 `BACKUP_CTL_CRONTAB` 與 `TZ` 產生 `export/schedule.json`（啟動 root 階段呼叫一次）；無法辨識的列略過並記 WARN |
| `pgbackrest-metrics.sh <輸出檔>` | 既有 14 個指標不變；追加 §C6 的三個指標 |

## C3 console-api 端點（`/api/v1/sysadmin`；operationId 與 tag「系統管理（資料庫備份）」）

> 來源：TCS §C3（L320～L351）。

### C3.1 `GET /backups`（`getBackupOverview`；VIEWER 以上；階一）

`data` 物件（鍵序固定，以保序 Map 輸出）：

| 鍵 | 型別 | 說明 |
|---|---|---|
| `control` | object | `{available:boolean, canTrigger:boolean, reason:string｜null, heartbeatAgeSeconds:int｜null, exportAgeSeconds:int｜null, exportGeneratedAt:ISO｜null, warnings:string[]}`；`available＝reason≠not_configured`；`canTrigger`＝階二：`request-dir` 已設、心跳新鮮、無 DB 失敗、無其他 reason 時為 true（階一恆 false）；`reason` 值域與優先序見 D-BK-T5 |
| `timezone` | string｜null | `schedule.json.tz`；`reason` 為前三類或時區不合法時 null |
| `activeJob` | object｜null | 進行中的工作：`{id:string｜null, type:full｜diff｜verify｜dump, status:QUEUED｜RUNNING, trigger:manual｜scheduled, requestedAt:ISO｜null, startedAt:ISO｜null, requestedBy?:string｜null}`；來源＝階二 DB 的 QUEUED／RUNNING 列（手動）或匯出的鎖狀態（`heartbeat.lock_held` 為真且對應 job 的 `last.status=running`；排程者 `id:null`）；DB 失敗時只取後者；`requestedBy` 僅 ADMIN |
| `cards` | array｜null | 恆 4 筆（full、diff、dump、verify）：`{job, status, trigger, startedAt, finishedAt, durationSeconds, lastSuccessAt, lastDueAt, overdue, never, reason, latestBackup?, detailTail?, requestedBy?}`；`status`∈{succeeded,failed,running,interrupted,no_run}；`latestBackup`＝`{label, finishedAt, source:"pgbackrest"}｜null`（僅 full、diff 卡有此鍵）；`detailTail`、`requestedBy` 僅 ADMIN |
| `backups` | array｜null | 見 R-BK-04：`{kind, label, location, startedAt, finishedAt, durationSeconds, databaseSizeBytes, repoSizeBytes, baseLabel, result}`，新到舊 |
| `schedule` | object｜null | `{entries:[{job, cron, nextRunAt:ISO｜null}], retention:{repo1:{full:int｜null,diff:int｜null}, repo2:{…}, logicalDays:int｜null}｜null}` |
| `repos` | array｜null | `{repo:int, endpointHost:string｜null, local:boolean, statusCode:int, statusMessage:string}` |
| `walArchive` | object｜null | `{lastArchivedAt:ISO｜null, failedCount:int, lastFailedAt:ISO｜null}`（Q7；D-BK-T20） |

### C3.2 `GET /backups/jobs?limit=&before=`（`getBackupJobs`；VIEWER 以上；階二）

`data`＝`{items:[{id, type, status, requestedAt, startedAt, finishedAt, durationSeconds, exitCode, reason, requestedBy, detail}], nextBefore:ISO｜null}`；`status`∈{QUEUED,RUNNING,SUCCEEDED,FAILED,REJECTED,EXPIRED}；`requestedBy`、`detail` 僅 ADMIN；參數規則見 D-BK-T14。

### C3.3 `GET /backups/jobs/{id}`（`getBackupJob`；VIEWER 以上；階二）

`data`＝單筆同 `items[]` 形；查無或 id 非 UUID ⇒ 404 `backup_job_not_found`。

### C3.4 `POST /backups/jobs`（`postBackupJob`；僅 ADMIN；階二）

body `{type:"full｜diff｜verify", confirm:true}`；成功 202，`data`＝`{id, type, status:"QUEUED", requestedAt}`；驗證序與狀態碼（D-BK-T13）：

| 序 | 條件 | 回應 |
|---|---|---|
| 1 | 無／壞 token | 401 |
| 2 | 角色非 ADMIN | 403 `ACCESS_DENIED` |
| 3 | 本文不是 JSON 物件（含語法錯） | 400 `MALFORMED_REQUEST_BODY` |
| 4 | `type` 缺、非字串或不在 {full,diff,verify} | 422 `invalid_request`（`details.violations[{field,message}]`） |
| 5 | `confirm` 不是 JSON 布林 `true` | 400 `backup_confirm_required` |
| 6 | `export-dir` 或 `request-dir` 未設、心跳過期、匯出不可讀、DB 讀取失敗 | 503 `backup_control_unavailable` |
| 7 | 已有 QUEUED 或 RUNNING（含唯一鍵衝突） | 409 `backup_job_in_progress` |
| 8 | 頻率上限（full 86400 秒、diff 3600 秒；verify 不設） | 409 `backup_too_frequent`（`details={type, nextAllowedAt}`） |
| 9 | 寫請求檔失敗 | 補償該列為 FAILED(`control_write_failed`)，503 `backup_control_unavailable` |

### C3.5 設定（`application.yml` 的 `console.backup.*`；未設＝停用，沿 `docker-compose.yml:149-157` 的空預設寫法；服務層只經 `application/port/out/BackupSettings` 讀取，`BackupProperties` 只作綁定）

`export-dir`（`CONSOLE_BACKUP_OUT_DIR`）、`request-dir`（`CONSOLE_BACKUP_REQ_DIR`）、`request-ttl-seconds` 120、`job-max-seconds` 21600、`reconcile-interval-ms` 5000、`overdue-grace-minutes` 30、`min-full-interval-seconds` 86400、`min-diff-interval-seconds` 3600；GET 只依 `export-dir`，POST 另依 `request-dir`；compose 的 backend 環境把兩個目錄變數設成字面常數 `/backup-req`、`/backup-out`（階二），不含機密。

## backup 類 reason 表

> 來源：TCS §C4（L355～L371）；TCS 內的標題為「C4 backup 類 reason 表」，本檔依其 L355 的指示寫成不帶 `C4`。

抄入契約檔 `API_Contract_SysAdminBackup.md` 時，本節標題寫成 `backup 類 reason 表`（不帶 `C4`；`BackupReasonsContractTest` 的標題判準為 `^#{1,6}\s*backup 類 reason 表`），下列第一張表為準（鎖的解析規則同議題中心 B-24：以標題之後的第一張表、欄序固定；多一列、少一列、訊息差一字皆使鎖紅）。「狀態碼」欄為數字者是 API 錯誤 reason（`ErrorReasons` 的 `BACKUP_` 前綴常數）；為「—」者是 `console.backup_jobs.reason` 的工作理由（後端列舉 `BackupJobReason`）。前端 `BACKUP_REASONS` 持有全部 13 個鍵與中文訊息。

| reason | 狀態碼 | details | 中文訊息 | 意義 |
|---|---|---|---|---|
| `backup_control_unavailable` | 503 | — | 備份控制面目前無法使用 | 控制面未設定、心跳過期、匯出不可讀、資料庫讀取失敗或寫請求檔失敗 |
| `backup_confirm_required` | 400 | — | 請先確認後再執行 | POST 缺 `confirm:true` |
| `backup_job_in_progress` | 409 | — | 已有進行中的備份工作 | 已有 QUEUED 或 RUNNING 工作 |
| `backup_too_frequent` | 409 | `{type, nextAllowedAt}` | 距離上一份同類備份過近，請稍後再試 | 頻率上限 |
| `backup_job_not_found` | 404 | — | 查無此備份工作 | 單筆工作不存在或 id 非 UUID |
| `script_failed` | — | — | 備份腳本執行失敗，請看輸出尾段 | 工作腳本非零結束 |
| `interrupted` | — | — | 容器重啟或工作被中斷 | 進行中但鎖未持有 |
| `timeout` | — | — | 工作逾時，控制面無回應 | RUNNING 逾 `job-max-seconds` 且控制面無回應 |
| `lock_timeout` | — | — | 等待維護鎖逾時，已有其他工作在執行 | 排程等鎖逾 `JOB_LOCK_WAIT_SECONDS` |
| `control_write_failed` | — | — | 請求無法送出（控制面寫入失敗） | POST 寫請求檔失敗後由 console-api 補償寫入（sidecar 不寫此值） |
| `busy` | — | — | 排程工作執行中，稍後再試 | 手動請求遇維護鎖被持有 |
| `rejected_invalid` | — | — | 請求內容不合法，已被拒絕 | runner 判定請求不合法 |
| `expired` | — | — | 請求逾時未被執行 | 請求逾 `request-ttl-seconds` 仍未被撿起 |

## C5 資料所有權（V15；階二）

> 來源：TCS §C5（L375）；DDL 抄自 PRD §8.1（`Console_SysAdmin_Backup_PRD.md` L165～L178）。

`console.backup_jobs` 的 DDL 逐字同 PRD §8.1（含 `ux_backup_jobs_one_active ON console.backup_jobs ((1)) WHERE status IN ('QUEUED','RUNNING')` 與 `idx_backup_jobs_requested_at`）；`BackupJobMigrationIT` 驗證部分唯一索引可建。寫入者唯一＝console-api 的 `BackupJobAdapter`（JDBC）；敘述種類恆為：INSERT（QUEUED）、條件式 UPDATE（`markRunningIfQueued`：`WHERE id=? AND status='QUEUED'`；`markTerminalIfActive`：`WHERE id=? AND status IN ('QUEUED','RUNNING')`；`markExpiredIfQueued`：`WHERE id=? AND status='QUEUED'`）與唯讀 SELECT；沒有 DELETE、TRUNCATE。`console.audit_log` 的寫入不變（由 `AuditLoggingFilter` 與 `AuditTrail` 產生）。

DDL（逐字抄自 PRD §8.1）：

```sql
CREATE TABLE console.backup_jobs (
    id           UUID PRIMARY KEY,
    type         VARCHAR(10)  NOT NULL CHECK (type IN ('full','diff','verify')),
    status       VARCHAR(12)  NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','REJECTED','EXPIRED')),
    requested_by VARCHAR(100) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at   TIMESTAMP WITH TIME ZONE,
    finished_at  TIMESTAMP WITH TIME ZONE,
    exit_code    INTEGER,
    reason       VARCHAR(30),   -- 封閉詞彙，見 AC-BK-06-8
    detail       VARCHAR(2000) NOT NULL DEFAULT ''   -- 已遮罩
);
CREATE UNIQUE INDEX ux_backup_jobs_one_active ON console.backup_jobs ((1)) WHERE status IN ('QUEUED','RUNNING');
CREATE INDEX idx_backup_jobs_requested_at ON console.backup_jobs (requested_at DESC);
```

## C6 Prometheus 指標與規則

> 來源：TCS §C6（L379～L385）。

| 項目 | 規格 |
|---|---|
| 新指標（`pgbackrest-metrics.sh`，gauge） | `aisdlc_backup_job_last_status{backup_job="full｜diff｜dump｜verify"}`（0 成功、1 失敗；`interrupted` 視為 1）；`aisdlc_backup_job_last_finished_timestamp_seconds{backup_job}`（`last.finished_at` 的 epoch 秒；`running` 中不輸出）；`aisdlc_backup_ctl_heartbeat_timestamp_seconds`（`heartbeat.ts` 的 epoch 秒）；無資料來源者不輸出序列。**標籤名不用 `job`**：抓取目標標籤 `job="pgbackrest"`（`prometheus.yml:30-33`，未設 `honor_labels`）會把曝光的 `job` 改名為 `exported_job`，規則的 `{job=~"dump\|verify"}` 永不匹配 |
| 既有 14 個指標 | 名稱與語意不變（`pgbackrest_exporter_info_ok`、`pgbackrest_exporter_scrape_timestamp_seconds`、`pgbackrest_stanza_status`、`pgbackrest_repo_status`、`pgbackrest_backup_count`、`pgbackrest_backup_since_last_full_seconds`、`pgbackrest_backup_since_last_backup_seconds`、`pgbackrest_backup_last_duration_seconds`、`pgbackrest_backup_last_database_size_bytes`、`pgbackrest_backup_last_repo_size_bytes`、`pgbackrest_backup_last_status`、`pgbackrest_backup_last_run_timestamp_seconds`、`aisdlc_storage_bytes`、`aisdlc_storage_used_ratio`） |
| 新規則（`alerts.yml`，群組 `aisdlc-backup` 末尾） | `PgBackRestJobFailed`：`expr: aisdlc_backup_job_last_status{backup_job=~"dump\|verify"} != 0`、`for: 1m`、`severity: critical`；`PgBackRestControlHeartbeatStale`：`expr: time() - aisdlc_backup_ctl_heartbeat_timestamp_seconds > 120`、`for: 1m`、`severity: warning`（`annotations.summary`／`description` 為中文，內容不鎖；`labels` 只鎖 `severity`） |
| promtool 測試 | `docker/prometheus/tests/backup_alerts_test.yml`（`rule_files: ["../alerts.yml"]`）；跑法同 `docker/README.md` 〈可用性 SLO〉的三條指令形（把測試檔換成 `backup_alerts_test.yml`） |
| README | `docker/README.md`：〈1.2〉卷表加 `backup_out`（階二另加 `backup_req`）、〈4.6 控制面〉（新增）、〈7〉「共 12 條」→「共 14 條」、〈9〉加 #35、〈10〉加「從未執行＝沒有序列＝規則不會亮」仍適用於新規則 |

> 備註（本檔）：表內的 `\|` 是 Markdown 表格欄內的豎線跳脫；PromQL 實際運算式為 `backup_job=~"dump|verify"`。

## 附錄 A 環境變數與設定總表

> 來源：TCS D-BK-T16（L119）與 §C3.5（L351）的彙整；**TCS 為真相**，本附錄只是把散在兩處的設定名稱、預設值與用到它的座標列成表。

### A.1 sidecar 的環境變數（D-BK-T16；腳本住 `AgentConsole/docker/pgbackrest/scripts/`）

預設值即生產值，環境變數只供測試與調參（D-BK-T16 原文）。

| 環境變數 | 預設值 | 備註與用到它的座標 |
|---|---|---|
| `BACKUP_CTL_OUT_DIR` | `/backup-out` | 輸出卷根：C1 的 `/backup-out/…` 各檔 |
| `BACKUP_CTL_REQ_DIR` | `/backup-req` | 請求卷根：C1 的 `/backup-req/<uuid>.json` |
| `BACKUP_CTL_LOCK_FILE` | `/run/backup-ctl/maintenance.lock` | 維護鎖檔：C1 末段、C2 `job-run.sh` |
| `BACKUP_CTL_SCRIPT_DIR` | `/usr/local/bin` | 工作腳本與 stub 的位置（D-BK-T16 原文） |
| `BACKUP_CTL_CRONTAB` | `/etc/crontabs/postgres` | C2 `backup-ctl-export.sh schedule`：由它與 `TZ` 產生 `schedule.json` |
| `BACKUP_CTL_POLL_SECONDS` | 5 | results 孤兒寬限＝6×此值＝30 秒，單一調參面（D-BK-T16 原文；R-BK-20、R-BK-51） |
| `BACKUP_CTL_EXPORT_SECONDS` | 60 | runner 啟動匯出子行程的週期（R-BK-50） |
| `BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` | 120 | C2 `backup-ctl-runner.sh`：`timeout $BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` 背景啟動匯出子行程 |
| `BACKUP_CTL_LOGICAL_MIN_SECONDS` | 300 | `logical.json` 的最短重寫間隔：C1「至多每 300 秒重寫」、C2「（距上次 ≥300 秒才）寫 `logical.json`」 |
| `JOB_LOCK_WAIT_SECONDS` | 7200 | C2 `job-run.sh`：排程等鎖的上限 |

C2 另提到 `TZ`（與 `BACKUP_CTL_CRONTAB` 一併供 `schedule` 子命令使用）；它不在 D-BK-T16 的環境清單內，故不列入上表。

### A.2 console-api 的設定（C3.5；`application.yml` 的 `console.backup.*`）

未設＝停用，沿 `docker-compose.yml:149-157` 的空預設寫法；服務層只經 `application/port/out/BackupSettings` 讀取，`BackupProperties` 只作綁定（C3.5 原文）。GET 只依 `export-dir`，POST 另依 `request-dir`。

| 設定鍵 | 環境變數 | 預設值 |
|---|---|---|
| `export-dir` | `CONSOLE_BACKUP_OUT_DIR` | 空（未設＝停用） |
| `request-dir` | `CONSOLE_BACKUP_REQ_DIR` | 空（未設＝停用） |
| `request-ttl-seconds` | — | 120 |
| `job-max-seconds` | — | 21600 |
| `reconcile-interval-ms` | — | 5000 |
| `overdue-grace-minutes` | — | 30 |
| `min-full-interval-seconds` | — | 86400 |
| `min-diff-interval-seconds` | — | 3600 |

C3.5 末句原文：「compose 的 backend 環境把兩個目錄變數設成字面常數 `/backup-req`、`/backup-out`（階二），不含機密。」

## 附錄 B TCS 引用座標表

> 本檔 C 各節與附錄 A 引用了 TCS 內的下列座標；它們的全文不在本檔，**以 TCS 為準**。「位置」為 TCS Stage-2 凍結版（digest 見檔頭）的行號；勘誤只追加於檔尾、不改正文，故行號穩定。

| 座標 | 引用處 | 主旨 | 位置 |
|---|---|---|---|
| `D-BK-T5` | C3.1 `control` 列 | `control.reason` 的值域與優先序、`control.warnings` 的值域 | TCS L108 |
| `D-BK-T8` | C1 `schedule.json` 列 | `entries[].job` 的封閉值域與 UI 工作名 | TCS L111 |
| `D-BK-T13` | C3.4 | POST 驗證序（本檔 C3.4 的表即其表格化）；並載明 `invalid_request` 以區域常數持有、不進 `ErrorReasons` | TCS L116 |
| `D-BK-T14` | C3.2 | `GET /backups/jobs` 的 `limit`、`before` 參數規則與錯誤 | TCS L117 |
| `D-BK-T16` | C2 標題 | sidecar 指令與測試縫環境變數（已彙整為附錄 A.1） | TCS L119 |
| `D-BK-T20` | C3.1 `walArchive` 列 | `walArchive` 的讀取來源、降級與 UI 警示條件 | TCS L123 |
| `R-BK-04` | C3.1 `backups` 列 | `backups[]` 的合併、排序與各欄值域 | TCS L176 |
| `R-BK-20` | C1 `results` 列 | results 的孤兒寬限（`started_at` 為撿起時刻）與 `interrupted` 清掃 | TCS L202 |
| `R-BK-47` | C2 `backup-ctl-runner.sh` 列 | runner 對非法請求檔的處理 | TCS L254 |
| `R-BK-48` | C2 `backup-ctl-runner.sh` 列 | `job-run.sh` 於持鎖期間寫終態（`jobs/<job>.json` 與 `results/<id>.json`） | TCS L255 |
| `R-BK-50` | 附錄 A.1（`BACKUP_CTL_EXPORT_SECONDS`） | 匯出子行程的啟動週期、逾時與各匯出檔的寫入規則 | TCS L257 |
| `R-BK-51` | 附錄 A.1（`BACKUP_CTL_POLL_SECONDS`） | 心跳：runner 每輪迴圈原子更新 `export/heartbeat` | TCS L258 |
| `Q7` | C3.1 `walArchive` 列 | 掌舵者裁決：顯示 WAL 歸檔健康一行 | PRD §13（L298、L301） |
| `F-03` | C1 `info.json` 列 | PRD §4 現況事實：`pgbackrest info` 的輸出形狀 | PRD L39 |
| `B-24` | 〈backup 類 reason 表〉 | 議題中心 TCS 的 reason 鎖解析規則 | `docs/03_testing/contracts/TCS-IssueCenter-20261027.md` L1024 |
