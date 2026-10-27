# Console「系統管理／資料庫備份」需求規格 v0.4

**狀態**：v0.4 終版（SA；三審 PASS 後修畢殘餘項，逐條見交卷報告）。**立案**：掌舵者 2026-10-27 原話「請問 Console UI 所有的資料是否有進 DB？若沒有請規劃實作進 Docker DB，並且進行定期備份！將此功能規劃在新模組『系統管理』→『系統管理』／『資料庫備份』中，進行控管！」。主控答覆：Console 業務資料在 PostgreSQL `console` schema，定期備份已由 sidecar 的 cron 在做，**缺的是可看、可控的介面**；本檔只做後者（§4 F-13 另揭露一處不在 DB 也不在備份內的資料，見 Q5b）。
**SDD 鍵**：`agentconsole-sysadmin-backup`（Console 單半；改 `AgentConsole/docker/pgbackrest/**` 同屬此鍵；流程＝LATEST 的 `SDD_AUTOCLAUDE_BRIDGE.md` §8，版本現查 `python AISDLC_SDD/scripts/sdd_version.py`）。
**規格文件組**：本檔＋TCS＋API 契約（端點、控制面檔案協定、reason 表、V15 資料所有權），路徑見 §9.4 第一列；不另寫 ADR（決策住 §9.1）。
**定位**：不重做備份。排程、腳本、保留設定的行為不變；本功能加「看」（清單、排程、狀態）與「控」（ADMIN 手動觸發全備／增備／驗證），並把控制面的安全架構寫清楚。

---

## 1. 目標與範圍

> 您打開「系統管理 › 資料庫備份」，一眼看到備份清單、排程、四種工作（全備、增備、離站 pg_dump、驗證）最近一次的結果；想補一份備份時按一個鈕（僅 ADMIN），看得到進行中與結果。

- **本版交付**：導覽項「系統管理」、`/sysadmin`（子頁入口）、`/sysadmin/backup`；備份清單、排程與保留（唯讀）、最近狀態卡、手動觸發、工作紀錄、還原與涵蓋範圍說明；sidecar 端控制面（匯出狀態、單工執行請求）。
- **成功的樣子**（症狀型，§11）：掌舵者不開終端機、不看英文，答得出「昨晚備份成功了嗎、最近一份全備是何時、離站有沒有備到、備份真的還原得起來嗎」，並能手動補一份增備、看到結果。
- **名實**：預設的離站 repo2 是同主機單碟的本機 MinIO（`docker/README.md:491`），「離站有沒有備到」會給出虛假安心；頁面須標明「與主機同碟」（AC-BK-02-6、Q8）。
- **名詞**：「全備」＝pgBackRest full；「增備」＝專案的 `backup-incr.sh`，實為**差異備份 diff**（`backup-incr.sh:2,28`），UI 寫「增備（差異）」；「邏輯備份」＝每日 `pg_dump -Fc` 離站檔；「驗證」＝`verify-backup.sh`（含還原到臨時實例的演練）；「控制面」＝console-api 與 sidecar 交換請求、結果、狀態的機制（§9.2）。

## 2. 使用者與場景

| 角色 | 能做什麼 |
|---|---|
| ADMIN（掌舵者） | 看全部；手動觸發全備、增備、驗證；看工作的輸出尾段與觸發者 |
| OPERATOR、VIEWER | 看清單、排程、狀態；按鈕停用並註明「需要 ADMIN 角色才能操作」；看不到輸出尾段與觸發者（Q6） |

- S1 每天早上看：四張卡都綠、沒有「逾期」。S2 大批資料變更後按「立即增備」，約半分鐘內見結果。S3 備份失敗或逾期：卡片變紅並說出最近一次成功是何時。S4 要還原：看「還原與說明」。

## 3. 範圍與不做什麼

- **做**：§1 本版交付；另含 crontab 包裝、兩個具名卷、V15 資料表、對帳排程、三個 Prometheus 指標與兩條規則。
- **不做**：還原按鈕（Q1）；排程與保留策略的編輯（Q3）；失敗推播（Q4）；離站 pg_dump 的手動觸發；`engine_workspace` 等非 DB 資料的備份（Q5b）；replica、failover；修改既有備份腳本本體；改引擎、Bridge、根層 `tools/`、`.claude/`、`.github/`。

## 4. 現況事實（2026-10-27 本機 Windows 11＋Docker Desktop 全棧現查；容器內只下唯讀指令）

| # | 事實 | 座標或現查結果 |
|---|---|---|
| F-01 | 排程（容器時區 `Asia/Taipei`）：全備週日 02:00、增備（diff）週一至六 02:00、pg_dump 每日 02:30、驗證週三 04:00、expire 每日 03:00、WAL 複本清理 03:30 | `docker/pgbackrest/crontab:6,9,12,15,18,21`；容器 `date` 為 CST (+0800) |
| F-02 | 全備與增備逐 repo 各跑一次，只把「最後一次」full 或 diff 的 type、status、timestamp 寫進 `.last_backup_status`（現查 `type=diff／status=0／timestamp=1793037602`＝2026-10-27 02:00:02 +08）；pg_dump 傳 `logical/aisdlc-<UTC>.dump`；**驗證與 pg_dump 沒有任何狀態檔**；cron 腳本間沒有互斥，`verify-backup.sh` 用固定暫存目錄與 5599 埠、起動輪詢單次可長達 300 秒 | `backup-full.sh:11-17,25-33`、`backup-incr.sh:14,24-32`、`pg_dump-offsite.sh:17,43-44`、`verify-backup.sh:24-26,57-65,75-86` |
| F-03 | `pgbackrest info` 現值：stanza ok、兩個 repo `status.code=0`；4 份備份：repo1 全備 `20261026-020000F`、repo2 全備 `20261026-020002F`、repo1 差異 `20261026-020000F_20261027-020000D`、repo2 差異 `20261026-020002F_20261027-020001D`；`status.lock.backup.held=false`；**只列成功的備份** | 指令見本節末；欄位 `backup[].{label,type,timestamp,info,database.repo-key,prior,error}` |
| F-04 | 全備標籤日期是 2026-10-26（週一），cron 全備在週日。**推論**：週一 02:00 的 diff 因 repo 尚無全備，被 pgBackRest 自動升格為 full（`cron.log` 已不存在，無法逐字佐證） | F-03、F-06 |
| F-05 | 指標（`:9854/metrics`，每 60 秒更新）有 `pgbackrest_backup_last_status`、`pgbackrest_backup_since_last_full_seconds` 等；**沒有** pg_dump 與驗證的指標 | `pgbackrest-metrics.sh:37-41,93-105`；`pgbackrest-entrypoint.sh:56-64` |
| F-06 | **`cron.log` 不存在**：`tail -n 50 /var/log/pgbackrest/cron.log` 回 `No such file or directory`，該目錄只有 `aisdlc-stanza-create.log`（11:47）。目錄在容器層（`df` 顯示 overlay；`docker inspect aisdlc-pgbackrest` 現查掛載＝conf、pg_data、pg_socket、pg_backup、pg_wal_archive 與映像 `VOLUME` 的匿名卷，無 `/var/log/pgbackrest`），容器 11:47 重建即歸零 ⇒ **驗證與 pg_dump 的最近結果沒有持久來源** | `docker-compose.yml:559-564`；`docker/README.md:495` |
| F-07 | 保留（`pgbackrest help expire` 現查）：repo1 `retention-full=4`、`retention-diff=7`；repo2 `retention-full=4`、**未設 diff**（未設時差異備份留到其依附的全備到期）；`retention-full-type` 未設，help 說明份數制：「repo-retention-full 為 4，完成第五份全備後最舊一份即被 expire」；邏輯備份預設 28 天。`pgbackrest.conf:21` 的「4 份＝28 天」前提是每週恰一份 | `pgbackrest.conf:21-23,30`；`docker-compose.yml:554`；`pg_dump-offsite.sh:21,47`；`help expire` 的 `current: 4`（兩 repo 同值為單值，diff 為逐 repo `repo1: 7`） |
| F-08 | 離站邏輯備份：MinIO 資料目錄 `ls /data/aisdlc-db-backup/logical/` 見 `aisdlc-20261025-183000.dump`、`aisdlc-20261026-183000.dump`（UTC＝台北 10-26、10-27 02:30）；`mc ls`（需金鑰與 `--insecure`）被 auto mode 分類器拒絕，不繞過 | `pg_dump-offsite.sh:17` |
| F-09 | sidecar 有 `bash`、`jq`、`flock`、`curl`、`perl`、busybox；**沒有 python3**。crond 以 root、httpd 以 nobody（`busybox ps` 現查 `httpd -f -p 9854 … -u nobody`）；crontab 檔 `root:root 0600`（postgres 讀不到） | `command -v`、`ls -l /etc/crontabs/` 現查；`Dockerfile:27,36-43` |
| F-10 | pgbackrest 只在 db-net；backend、Bridge 皆在 backend-net＋db-net；db-net `internal: true`，另含 pgadmin、prometheus 等。compose 內 `docker.sock` 出現 0 次 ⇒ backend、Bridge 無 docker socket | `docker-compose.yml:585-586,190-192,312-314,788-790`；`docker/README.md:58` |
| F-11 | 審計：`AuditLoggingFilter` 在請求結束時才寫 `audit_log`，列 id 由 `AuditLogWriter` 內部隨機產生，用例拿不到；表**沒有** action、detail 欄；用例以 `AuditTrail.note(action, type, id, extra)` 標註 entity | `AuditLoggingFilter.java:63-93`、`AuditLogWriter.java:44-61`、`V6__audit_log.sql:6-17`、`AuditTrail.java:14-18` |
| F-12 | Console 六條告警是「專案／批次」級（`alerts.project_id NOT NULL`）；Prometheus 已有四條 PgBackRest 規則，但**沒有 Alertmanager** | `V4__monitor_alerts.sql:7`；`docker/prometheus/alerts.yml:84-118`；`docker/README.md:384` |
| F-13 | `console` schema 現有 16 張應用表，Flyway 最高 V14。Bridge 的執行工作區檔案（`run.json`、`events.jsonl`、`_audit.jsonl`、`_drafts/`）在 `engine_workspace` 卷，**不在 DB、不在 pgBackRest 涵蓋內**（現查 `/workspace` 只有 `_audit.jsonl`） | `engine-bridge/README.md:345`；`psql` 現查 |
| F-14 | 還原：先停 primary，`restore.sh` 在 primary 運作時拒絕；還原後 replica 時間軸分岔須重建；金鑰遺失＝備份無法還原 | `docker/README.md:266,267,93,297` |
| F-15 | `pg_stat_archiver` 可由 console-api 既有連線讀取（backend 用 `POSTGRES_USER`）：現查 `archived_count=72`、`failed_count=0` | `docker-compose.yml:129`；`docker/README.md:389` |

現查指令（工作目錄＝monorepo 根；PowerShell；唯讀）：

```powershell
Push-Location AgentConsole; docker compose exec -T pgbackrest bash -c 'pgbackrest --stanza=aisdlc --output=json --log-level-console=off info; cat /etc/crontabs/postgres /var/lib/pgbackrest/.last_backup_status; busybox wget -q -O - http://127.0.0.1:9854/metrics; tail -n 50 /var/log/pgbackrest/cron.log; pgbackrest help expire repo-retention-full; pgbackrest help expire repo-retention-full-type'; Pop-Location
Push-Location AgentConsole; docker compose exec -T minio sh -c 'ls -la /data/aisdlc-db-backup/logical/'; Pop-Location
Push-Location AgentConsole; docker compose exec -T postgres-primary psql -U aisdlc -d aisdlc -c "SELECT archived_count, failed_count FROM pg_stat_archiver;"; Pop-Location
docker inspect aisdlc-pgbackrest --format '{{range .Mounts}}{{.Type}} {{.Destination}} rw={{.RW}}{{println}}{{end}}'
```

## 5. 功能需求（FR 與 AC；Given／When／Then，每條可由一支測試判定）

| AC | 內容 |
|---|---|
| **FR-BK-01** | **導覽與頁面骨架** |
| `AC-BK-01-1` | Given 導覽登記表 When 讀 `NAV_REGISTRY` Then 恰九項：末尾新增 `{id:"sysadmin", label:"系統管理", icon:Database, href:"/sysadmin", match:"/sysadmin"與其子路徑, order:65, enabled:true, mobile:false, roles 缺}`；原八列各欄與索引不變（`self-improving` 仍是 `[6]`、`issues` 仍是 `[7]`）；顯示序＝系統設定 60、系統管理 65、自我進化 70；九個 `order` 唯一、九個 `icon` 互異（lucide-react 1.57.0 已驗有 `Database`、`DatabaseBackup`） |
| `AC-BK-01-2` | Given 任一角色登入 When 看左列 Then 皆有「系統管理」；進 `/sysadmin` 見入口卡「資料庫備份」（一句說明＋最近全備狀態摘要），點入 `/sysadmin/backup`，導覽 active 為「系統管理」；未登入沿既有登入閘（`lib/auth/AuthProvider.tsx:52-53`），不顯示備份資料 |
| `AC-BK-01-3` | Given 視窗 <768 When 看底部 Tab Then 「系統管理」不顯示（`max-md:hidden`，DOM 內仍在）；`mobile:true` 項數仍 6 |
| **FR-BK-02** | **備份清單** |
| `AC-BK-02-1` | Given 匯出含兩個 repo 的全備與差異及離站邏輯備份 When 開「備份清單」Then 依結束時間新到舊列出：類型（全備／增備（差異）／增量／邏輯備份）、標籤、儲存位置（本地 repo1／離站 repo2／離站邏輯）、開始、結束、耗時、資料庫大小、備份大小、基準（差異備份的前一份全備標籤，其餘「—」）、結果 |
| `AC-BK-02-2` | Given 項目 `error=true`（頁校驗錯誤）When 顯示 Then 結果為「成功，但有校驗錯誤」並帶警示色，否則「成功」；清單只含成功建立的備份，頁面一行明說「失敗的工作看狀態卡與工作紀錄」 |
| `AC-BK-02-3` | Given 時間、大小、耗時 When 顯示 Then 時間用瀏覽器本機時區（`formatDateTime`，`lib/format.ts:27-30`）並於標題旁註排程時區；大小 `formatBytes`、耗時 `formatDuration`（`lib/domain/metrics.ts:87`）；缺值「—」，不新增格式化函式 |
| `AC-BK-02-4` | Given 某 repo `status.code≠0`（例：離站不可達）When 顯示 Then 該 repo 區塊頂列顯示狀態碼與中文說明，另一 repo 照常，不顯示成「沒有備份」 |
| `AC-BK-02-5` | Given 完全沒有備份 When 顯示 Then 空狀態寫「尚無備份：首次部署後請立刻做第一份全備」，四張卡為「從未執行」，不顯示 0 |
| `AC-BK-02-6` | Given 匯出的 `repos`（型別、端點主機、是否本機）When 顯示 repo 區塊與「離站 pg_dump」卡 Then 端點主機名不含 `.`（compose 服務名，例 `minio`）或為 `localhost` 者標「本機 MinIO・與主機同碟，主機損毀時一併消失」，其餘標「外部 S3」；夾具兩種端點各一，斷言文字不同，且前者不呈現成「離站已安全」 |
| **FR-BK-03** | **排程與保留策略（唯讀）** |
| `AC-BK-03-1` | Given sidecar 匯出的六條 cron When 開「排程與保留」Then 白話列出（例「每週日 02:00・全備」）並附原 cron 與時區，另加固定列「WAL 持續歸檔（有寫入時約每 60 秒一段）」；expire、WAL 清理標「維護工作」 |
| `AC-BK-03-2` | Given 前端認不得的 cron 形狀 When 顯示 Then 退回原表達式，不丟例外、不猜（白話化只認 `m h * * d`、`m h * * a-b`、`m h * * *` 三式） |
| `AC-BK-03-3` | Given 排程時區與 cron When console-api 算 `nextRunAt` Then 為該時區的下一個符合時刻（Spring `CronExpression`，前補秒欄 0），ISO-8601 回傳；IT 以固定 Clock 驗證，含週日（星期欄 0）夾具，不隨瀏覽器時區改變 |
| `AC-BK-03-4` | Given 匯出的 `retention`（取自 pgBackRest 自報的有效值：`pgbackrest help expire repo-retention-*` 的 `current:`，單值與逐 repo 列皆解析；環境變數優先於 conf，`pgbackrest.conf:3-10`）與 `LOGICAL_BACKUP_RETENTION_DAYS` When 顯示 Then 唯讀列出「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」；解析不到＝`null`、顯示「—」並入 `control.warnings`，不填預設值；無編輯控制項 |
| **FR-BK-04** | **最近狀態卡（全備、增備、離站 pg_dump、驗證）** |
| `AC-BK-04-1` | Given 四個工作 When 開頁 Then 各一張卡：狀態徽章（成功／失敗／進行中／中斷／從未執行，文字加圖示）、最近一次執行（排程或手動、開始時間、耗時）、最近一次成功時間；全備與增備卡另附「最近一份備份」，取自 pgBackRest 清單並標明來源（F-04：清單有全備時不得只顯示「從未執行」） |
| `AC-BK-04-2` | Given 最近一次失敗而更早有成功 When 顯示 Then 卡為失敗色並同時顯示「最近一次成功：<時間>」；輸出尾段只對 ADMIN 顯示（FR-BK-07） |
| `AC-BK-04-3` | Given 各工作的 cron 與排程時區 When console-api 算卡片 Then 回 `lastDueAt`（cron 在現在之前最近一次應跑時刻；`CronExpression` 只有 `next`，自 now−8 天起逐次迭代取最後一個 ≤now 者，TCS 提示）與 `overdue`：`lastDueAt` 加寬限（`overdue-grace-minutes`＝30）已過，且最近成功時間缺席或早於 `lastDueAt`，且該工作未在進行中；全備卡與增備卡的最近成功時間取「工作狀態檔」與「備份清單」較新者（清單端＝各 repo 最近一份的最舊者；全備＝full，增備＝diff 或 full）；從未成功＝`never:true`、不稱逾期；前端不重算。固定 Clock 邊界：週六 04:00（增備週六 02:00 成功）與週日 04:00（增備無週日時段、全備週日 02:00 成功）不逾期；週一 02:15（寬限內）不逾期；週一 02:31 增備未成功→增備卡逾期；週日 02:31 全備未成功→全備卡逾期 |
| `AC-BK-04-4` | Given 狀態檔記為進行中、維護鎖卻未被持有（容器重啟中斷）When 匯出 Then 卡顯示「中斷」 |
| `AC-BK-04-5` | Given 非 ADMIN 的 `GET /backups` When 讀 `cards[]`、`activeJob` Then 不含 `detailTail`、`requestedBy`（鍵缺席或 `null`）；ADMIN 才有且已遮罩；JSON 掃描測試以非 ADMIN token 驗證 |
| **FR-BK-05** | **控制面健康與資料新鮮度（fail-loud）** |
| `AC-BK-05-1` | Given `export-dir` 未設（例：本機 bootRun）When 開頁 Then 整頁顯示「備份控制面未設定（不在 Docker 全棧）」；GET 回 200 且 `control.available=false、reason=not_configured`，不顯示 0 或空表；`control.canTrigger`（階段二；`request-dir` 已設、心跳新鮮、資料庫可用才為 true）為 false 時按鈕停用、POST 回 503 `backup_control_unavailable`（含 `export-dir` 未設）；僅 `request-dir` 未設時 GET 照常 |
| `AC-BK-05-2` | Given 心跳檔缺席或超過 30 秒未更新 When 開頁 Then 紅色橫幅（`role="alert"`）「備份控制面無回應（上次心跳 N 秒前）」，資料標「可能已過期」，按鈕停用；GET 仍回已知資料並帶 `reason=runner_offline`，POST 回 503；工作進行中不算（AC-BK-09-8） |
| `AC-BK-05-3` | Given 匯出檔 `schema_rev` 不是 1 或 JSON 損毀 When 讀取 Then `reason=schema_mismatch` 或 `export_unreadable`，該區塊顯示原因，不顯示部分資料、不當成 0 件 |
| `AC-BK-05-4` | Given 匯出 `generated_at` 超過 180 秒 When 顯示 Then 「資料更新於 hh:mm:ss」旁加「已過期」（心跳新鮮而匯出舊） |
| `AC-BK-05-5` | Given 資料庫讀取失敗 When `GET /backups` Then 仍回檔案面的清單、排程、卡片，`control.warnings` 含 `db_unavailable`、`activeJob` 只取自匯出的鎖狀態，不回 500；POST 回 503 `backup_control_unavailable` |
| **FR-BK-06** | **手動觸發（全備、增備、驗證；僅 ADMIN）** |
| `AC-BK-06-1` | Given ADMIN When 按「立即全備」或「立即增備」Then 先開確認對話框：工作名稱、白話說明、上次耗時與資料庫大小，及**保留名額**（純函式）——「目前保留 X 份全備（上限 Y）；完成後若超過上限，最舊一份（<標籤>）與依附於它的差異備份會在**完成當下**刪除（備份後自動 expire，`pgbackrest help backup expire-auto`），可回溯期縮短」，增備同形，份數取差異＋全備合計（全備計入差異份數，`help expire repo-retention-diff`），該 repo 未設則不顯示；驗證另提醒「會還原整份備份到臨時實例，暫存空間約等於資料庫大小」；按「確認執行」才送 POST，取消則網路層零請求 |
| `AC-BK-06-2` | Given body 缺 `confirm:true` 或 `type` 不在 {full, diff, verify} When 送出 Then 400 `backup_confirm_required`／422 `invalid_request`，不建列、不寫請求檔 |
| `AC-BK-06-3` | Given 無進行中工作且控制面正常 When POST Then 先插入 QUEUED 列、再寫請求檔，回 202 `{id, type, status:"QUEUED", requestedAt}`；頁面顯示「進行中」橫幅（QUEUED→RUNNING→終態）並輪詢該工作，終態後顯示結果、刷新清單與卡片 |
| `AC-BK-06-4` | Given 已有進行中工作（QUEUED 或 RUNNING）When 再 POST Then 409 `backup_job_in_progress`，不建列、不寫檔；IT 兩個併發 POST 恰一個 202、一個 409（部分唯一索引兜底，§8.1） |
| `AC-BK-06-5` | Given 排程工作正在跑（sidecar 持有維護鎖）When 手動請求抵達 Then runner 回 `busy`，工作標 REJECTED，頁面顯示「排程工作執行中，稍後再試」 |
| `AC-BK-06-6` | Given 請求逾 120 秒（`request-ttl-seconds`）仍未被撿起 When 對帳 Then runner 存活時由 runner 寫 `rejected／expired`、console-api 對帳為 EXPIRED；runner 離線（心跳過期）時才由 console-api 標 EXPIRED，且以 `UPDATE … WHERE status='QUEUED'` 寫入（與撿取交錯時只有一方生效）；EXPIRED 後 console-api 刪自己的請求檔，sidecar 日後恢復也不執行過期請求 |
| `AC-BK-06-7` | Given OPERATOR 或 VIEWER When POST Then 403 `ACCESS_DENIED`，無新列、無請求檔；按鈕渲染為 `disabled` 並旁註「需要 ADMIN 角色才能操作」（文字沿 `IssueTable.tsx:73`，該處先例只顯示文字、不渲染按鈕，`:70-76`），網路層零寫入 |
| `AC-BK-06-8` | Given 工作結束 When 對帳（排程輪詢與 GET 順帶可並行）Then 以 `UPDATE … WHERE id=? AND status IN ('QUEUED','RUNNING')` 寫回狀態、`finished_at`、`exit_code`，**只有更新到列的那一次**於交易提交後補 `backup.finished` 審計列（兩執行緒同時對帳同一結果的 IT 驗證恰一列）；失敗理由 `script_failed`、`interrupted`、`timeout`（RUNNING 逾 `job-max-seconds` 且控制面無回應）、`lock_timeout`、`control_write_failed`；REJECTED 為 `busy`、`rejected_invalid`；EXPIRED 為 `expired` |
| `AC-BK-06-9` | Given POST 寫請求檔失敗（卷唯讀、已滿、權限）When 處理 Then 該列補償為 FAILED（理由 `control_write_failed`）、刪殘留 `.tmp`、回 503 `backup_control_unavailable`；唯一索引釋放，可立即重試 |
| `AC-BK-06-10` | Given 各 repo 最近一份全備都在 24 小時（`min-full-interval-seconds`）內 When 手動 POST full Then 409 `backup_too_frequent`（`details` 含 `type`、`nextAllowedAt`），不建列；任一 repo 的最近全備較舊或缺席則允許（例：離站失敗後補做）；增備同形、門檻 1 小時；驗證不設門檻 |
| `AC-BK-06-11` | Given 進行中工作的分頁 When 輪詢 Then 工作每 10 秒、總覽每 30 秒（`queries.ts:194`），單一分頁每分鐘至多 8 次；間隔常數取自 `NOTIFICATION_POLL_FLOOR_MS`（`queries.ts:201`）並有 `>=` 斷言（沿 `queries.polling.test.tsx:70-72`），守契約地板 10 秒（`API_Contract_P3-6.md:153`）；兩分頁加各自通知輪詢（`queries.ts:201-202` 每 30 秒）≤20 次，低於限流（每使用者每分鐘 100 次，`application.yml:108-111`）；vitest 以假計時器計請求數驗證 |
| **FR-BK-07** | **工作紀錄（Console 發起的動作）** |
| `AC-BK-07-1` | Given 數次手動工作 When 開「工作紀錄」Then 新到舊列出（頁大小 20、游標＝`requestedAt`）：類型、觸發者、要求時間、開始與結束、耗時、狀態、理由（中文）；排程工作不在此表（看狀態卡），頁面一行說明分工 |
| `AC-BK-07-2` | Given ADMIN 展開一列 When 看詳情 Then 顯示已遮罩的輸出尾段（≤2,000 字元）；非 ADMIN 該欄位與觸發者在 API 回 `null`、UI 不渲染 |
| `AC-BK-07-3` | Given 輸出含 `pass=…`、`secret=…`、`key=…`、AWS 金鑰 id 形、帶密碼的連線字串形 When 回應 Then sidecar 與 console-api **各遮罩一次**（任一道漏，另一道仍擋）；探針單一檔 `docker/pgbackrest/tests/fixtures/mask-probes.txt`，兩邊測試共讀；**探針值須含 `example`／`fake` 佔位詞**，否則 pre-commit 的 `tools/lib/secret_scan.py`（`:61-68`、`:191`、`:46-51`）擋 commit；遮罩器只認形狀、不因佔位詞放行；回應與 DB 皆不含原值 |
| **FR-BK-08** | **說明區：還原與涵蓋範圍（只有說明，沒有按鈕）** |
| `AC-BK-08-1` | Given 開「還原與說明」Then 顯示還原三步（停 primary → 容器內 `restore.sh` → 啟動並核對列數與時間軸；bash 與 PowerShell 雙形態）與核對三項，明寫「本頁不提供還原按鈕」及原因（F-14）；前端指令常數與 `docker/README.md` 〈4.3〉**單向相符**：UI 的每條指令都須逐字出現在該節 code block（README 刪改＝紅）；README 另增指令不紅、不鎖整段文字 |
| `AC-BK-08-2` | Given 涵蓋範圍表 Then 逐卷分類：已備份＝`pg_data`（PG 全叢集，含 `console` schema）；備份機制本身＝`pg_backup`、`minio_data`、`pg_wal_archive`、`pg_socket`、`backup_out`（階段二加 `backup_req`）；可由 primary 重建＝`pg_replica_data`（README §5）；**未涵蓋**＝`engine_workspace`、`app_logs`、`redis_data`、`prometheus_data`、`nginx_certs`、`minio_certs`（缺時由 minio-certs job 重產）；並寫明「`PGBACKREST_CIPHER_PASS` 遺失＝備份無法還原、`CONSOLE_ENCRYPTION_KEY` 遺失＝敏感參數無法解密，請另行保管」 |
| `AC-BK-08-3` | Given `docker-compose.yml` 頂層 `volumes:` When vitest 比對 Then 涵蓋表鍵集合與頂層卷集合**雙向相等**（新增卷未歸類、或表內有不存在的卷＝紅）；前端無 YAML 依賴，改以規則式取頂層區塊（自 `^volumes:$` 到下一個頂格鍵，取兩格縮排鍵名）並**自證**：取到的卷數須 ≥12，否則解析失敗而紅；現 12 卷（`docker-compose.yml:796-818`），階段一加 `backup_out` 成 13、階段二加 `backup_req` 成 14，表與 compose 同 commit |
| **FR-BK-09** | **sidecar 控制面（runner、export、包裝）** |
| `AC-BK-09-1` | Given 契約測試（Linux 容器、stub `pgbackrest`）When runner（`--once` 掃一輪）處理合法請求 Then 依序：寫 `results/<id>.json`（running＝「已撿」標記）→ 以**背景子行程**啟動 `job-run.sh`（runner 不等待）→ 子行程結束時寫終態（rc、耗時、遮罩尾段）；**不刪請求檔**，已撿與否只看 results 是否存在（至多一次，重啟不重播）；請求只認 `{schema_rev:1, id:UUID, type, requested_at, expires_at}`，多餘欄位忽略，**不解譯為指令** |
| `AC-BK-09-2` | Given 非法請求（檔名非 UUID、非常規檔或符號連結、>4 KB、非 JSON、未知 type、已過期、目錄內檔數 >16）When 掃描 Then 不執行任何命令；可寫時寫 `rejected` 結果（封閉詞彙理由），否則只記 WARN；結果與 WARN **不含請求檔任何原文**（含 jq 錯誤訊息）；以 `timeout` 子殼讀檔（擋 FIFO 阻塞）：開檔後 `lstat` 路徑，須為常規檔且 dev:ino 與 fd 一致（擋符號連結與換檔競態），只讀前 4 KB；單一壞檔不中止迴圈 |
| `AC-BK-09-3` | Given 排程與手動 When 經 `job-run.sh` 啟動 Then 共用同一把**命令形** `flock -o`（持鎖者是活的 flock 行程；`--close`，不讓 verify 起的暫存 PG 繼承鎖 fd；鎖檔在 sidecar 本地 `/run/backup-ctl/maintenance.lock`，不在共享卷）：排程等待、手動不等待（立刻 `busy`）；等待逾 2 小時（`JOB_LOCK_WAIT_SECONDS`）＝不執行腳本，狀態記失敗、理由 `lock_timeout`、rc=75、stderr 留一行；鎖檔開不了＝fail-open（照常執行、WARN、狀態註記 `locking:unavailable`）；狀態檔寫入失敗同樣只記 WARN，仍執行腳本並原樣回傳其 rc |
| `AC-BK-09-4` | Given crontab 四條備份與驗證工作改經 `job-run.sh` When 執行 Then 各腳本本體零修改；`.last_backup_status` 與 `pgbackrest_backup_last_status` 的語意與值不變；`>> cron.log` 照舊（契約測試驗證 rc 與輸出透傳） |
| `AC-BK-09-5` | Given 匯出子行程 `backup-ctl-export.sh`（runner 每 60 秒與每次工作結束後以 `timeout 120` 啟動；前一個未結束就略過，不重疊、不共用 `.tmp`）When 執行 Then 原子寫 `export/info.json`（`pgbackrest info` 原輸出外包 `{schema_rev, generated_at, ok}`，另帶 `retention`、`repos`）與 `export/logical.json`（至多每 300 秒；`mc` 失敗＝`ok:false`，不寫部分清單）；`export/schedule.json` 於啟動 root 階段由 crontab 產生一次（F-09）；runner 每輪詢更新 `export/heartbeat`（`lock_held` 讀 `/proc/locks` 比對鎖檔 dev:ino，不得以取鎖探測；fd 形持鎖時該檔無列〔實測〕，故鎖限命令形；契約測試驗持鎖期間 `lock_held=true`） |
| `AC-BK-09-6` | Given 容器重建、重啟或全新環境 When 啟動 Then `export/jobs/*.json` 仍在（卷 `backup_out`）；「進行中但鎖未持有」者改記 `interrupted`；目錄權限由**寫入端映像**定義（backend 映像建 `/backup-req` 屬 spring；sidecar 映像建 `/backup-out` 屬 postgres，啟動時再 `install -d`）：目錄 0755、檔 0644（讀取端是另一個 uid；不可照抄 `pgbackrest/Dockerfile:39` 的 0750）；讀取端一律 `:ro,nocopy`；compose 旗標鎖（PyYAML pytest）驗掛載的 `ro`／`nocopy` |
| `AC-BK-09-7` | Given `pgbackrest-metrics.sh` 追加 `aisdlc_backup_job_last_status{job}`、`aisdlc_backup_job_last_finished_timestamp_seconds{job}`、`aisdlc_backup_ctl_heartbeat_timestamp_seconds` When 執行 Then 既有指標名稱與語意不變；`alerts.yml` 增兩條（dump 或 verify 失敗、心跳過期超過 120 秒），`promtool check rules` 與單元測試皆綠；比照 `test_deploy_config.py:226-242` 加鎖：規則檔被 Prometheus 載入（`docker-compose.yml:710`）且每條規則名都出現在 promtool 測試檔 |
| `AC-BK-09-8` | Given 工作或匯出子行程長時間執行（stub 睡眠；真實驗證的起動輪詢可達 300 秒）When 觀察 Then runner 迴圈不被阻塞：`export/heartbeat` 每 ≤10 秒更新；匯出子行程被 `timeout` 終止後 `info.json` 記 `ok:false` 而迴圈照常；console-api 整段期間不出現 `runner_offline`、進行中橫幅可見（契約測試以縮短參數驗證：輪詢 1 秒、睡 15 秒、心跳間隔 ≤3 秒；真機 V7 驗真實驗證期間不誤報） |
| **FR-BK-10** | **資料、稽核與安全** |
| `AC-BK-10-1` | Given Flyway V15（階段二）When 在 V14 資料庫升級 Then 建 `console.backup_jobs`（§8.1）、既有表零變動；四個 migration IT 的版本清單補「15」；無 JPA 實體（JDBC 配接器，`ddl-auto=validate` 不檢查） |
| `AC-BK-10-2` | Given 一次成功觸發 When 查 `console.audit_log` Then 有 `method=POST、entity_type=backup、entity_id=<job id>、http_status=202` 一列；終態對帳另有 `subject=system`、同 entity 的 `backup.finished` **恰一列**（`AuditTrail.system`；併發對帳也只一列，見 AC-BK-06-8）；被拒的 POST（401、403、409）同樣留列 |
| `AC-BK-10-3` | Given `SecurityConfig` 加 `POST /api/v1/sysadmin/**`＝ADMIN（置於通用規則之前，`SecurityConfig.java:84-92`）When IT Then ADMIN 202、OPERATOR 403、VIEWER 403、無 token 401；所有 GET 為 VIEWER 以上 |
| `AC-BK-10-4` | Given 任何回應、日誌行、`audit` 的 `extra`、控制面檔案 Then 不含 MinIO 金鑰、DB 密碼、`PGBACKREST_CIPHER_PASS`、`CONSOLE_ENCRYPTION_KEY`（console-api 環境本就沒有 MinIO 金鑰與 cipher 密碼；DB 密碼與加密金鑰以注入探針的掃描測試驗證不外洩） |
| `AC-BK-10-5` | Given OpenAPI When 重產 Then 階段一增 1 個路徑、1 個操作（`getBackupOverview`），階段二再增 2 個路徑、3 個操作（`getBackupJobs`、`getBackupJob`、`postBackupJob`）；tag「系統管理（資料庫備份）」，`schema.d.ts` 隨階段重產入庫 |

## 6. 非功能需求

- **安全（STRIDE 精簡）**：偽造身分→JWT＋ADMIN 規則（AC-BK-10-3）；竄改→請求卷 sidecar 唯讀、輸出卷 backend 唯讀（mount 層強制），請求只認封閉詞彙、不回顯原文（AC-BK-09-1、09-2）；否認→兩列 `audit_log`＋`backup_jobs`；外洩→兩道遮罩、非 ADMIN 不見輸出尾段（AC-BK-04-5、07）；阻斷→單工、TTL、檔數與頻率上限（AC-BK-06-10）；提權→無 docker socket，console-api 不持有 cipher 與 S3 金鑰、不掛 `pg_data`、`pg_backup`。
- **效能**：`GET /backups` 每請求讀 8 個小檔（info、logical、schedule、heartbeat、四個工作狀態；不快取），本機目標 ≤500 ms；觸發到 DB 轉 RUNNING ≤10 秒（畫面至多再晚一個輪詢間隔）。
- **並發與逾時**：同時只允許一個進行中工作（DB 與 sidecar 兩層）；各逾時值見 §8.3、AC-BK-06-6、06-8、09-3。
- **無障礙**：沿用 `PillTabs`、`Dialog`、`Button`；徽章文字加圖示、橫幅 `role="alert"`。
- **跨平台**：console-api 純 Java 檔案 I/O（`Files.move` 原子模式、處理 `IOException`），Windows 以 `@TempDir` 測；sidecar 腳本只在 Linux 容器（shellcheck 全嚴重度乾淨、`bash -n` 過）；控制面用**具名卷**不用 bind（避開 NTFS 權限語意）；時間戳一律 ISO-8601 帶 `Z`。
- **零侵入面**：見 §3「不做」與 §9.5。

## 7. 畫面（左列新增「系統管理」；所有角色可看，寫入只給 ADMIN）

`/sysadmin`＝子頁入口卡（目前一張「資料庫備份」）。`/sysadmin/backup`（上到下）：

```
系統管理 › 資料庫備份
[橫幅] 紅：備份控制面無回應（上次心跳 95 秒前） ／ 黃：進行中：全備（手動，admin，已 00:42）
┌ 最近狀態 ─────────────────────────────────────────────────┐
│ 全備         增備（差異）    離站 pg_dump    備份驗證           │
│ ● 成功       ● 成功         ● 成功         ○ 從未執行         │
│ 排程 10-26   排程 10-27     排程 10-27     [逾期]            │
├ 手動操作（僅 ADMIN）──────────────────────────────────────┤
│ [立即全備] [立即增備（差異）] [立即驗證]  非 ADMIN：停用＋「需要 ADMIN 角色才能操作」│
├ [備份清單｜排程與保留｜工作紀錄｜還原與說明] ───────────────────┤
│ repo2：本機 MinIO・與主機同碟（AC-BK-02-6）                     │
│ 類型｜標籤｜儲存位置｜開始｜結束｜耗時｜資料庫｜備份｜基準｜結果（資料更新於 14:39:08）│
└───────────────────────────────────────────────────────────┘
```

- **載入與錯**：總覽每 30 秒重抓，有進行中工作時另每 10 秒輪詢該工作（分頁不可見時停止〔`queries.ts:199`〕；地板與預算 AC-BK-06-11）；量不到＝整區顯示原因（FR-BK-05），絕不顯示成 0。階段一沒有「手動操作」區與「工作紀錄」分頁。

## 8. 資料模型與介面契約

**8.1 `console.backup_jobs`（Flyway `V15__backup_jobs.sql`，階段二；只記「Console 發起的動作」，備份事實以 pgBackRest 為準）**

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

- 設計取捨：**不設 `audit_log_id`**（F-11：審計列 id 用例拿不到）＝改以 `audit_log.entity_type='backup' AND entity_id=<id>` 軟關聯；**不設 `repo`**（手動工作一律跑全部已設定的 repo，各 repo 結果以備份清單為準）。部分唯一索引的寫法由 TCS 階段以 IT 驗證可建。
- 寫入者唯一＝console-api（沿 Architecture §7.2）；Bridge、sidecar 不讀不寫。

**8.2 控制面檔案協定 v1（兩個具名卷；寫入一律「寫 `.tmp`→同目錄改名」）**

| 路徑（容器內） | 寫入者 | 內容 |
|---|---|---|
| `/backup-req/<uuid>.json`（請求卷：backend 寫、sidecar `:ro`） | console-api | `{schema_rev:1, id, type, requested_at, expires_at}`；終態後由 console-api 刪 |
| `/backup-out/export/info.json`（輸出卷：sidecar 寫、backend `:ro`） | 匯出子行程 | `{schema_rev:1, generated_at, ok, info:[<pgbackrest info 原輸出>], retention:{…}, repos:[{repo, type, endpoint_host, local}]}` |
| `…/export/logical.json` | 匯出子行程 | `{schema_rev:1, generated_at, ok, objects:[{name, size, modified}]}` |
| `…/export/schedule.json` | sidecar（啟動 root 階段） | `{schema_rev:1, tz, entries:[{job, cron}]}` |
| `…/export/jobs/<job>.json` | `job-run.sh` | `{schema_rev:1, job, last:{trigger, status, rc, reason, started_at, finished_at, detail_tail}, last_success_at}`；job＝full／diff／dump／verify |
| `…/export/heartbeat` | runner 迴圈 | `{ts, lock_held}` |
| `…/results/<uuid>.json` | runner 背景子行程 | `{schema_rev:1, id, type, status, reason, rc, started_at, finished_at, detail_tail}`；status＝running／succeeded／failed／rejected；存在＝「已撿」；留最近 50 份 |

**8.3 端點（`/api/v1/sysadmin`；回應包既有 `{code,message,data,…}`）**

| 端點 | 角色 | 階段 | 說明 |
|---|---|---|---|
| `GET /backups` | VIEWER 以上 | 一 | 總覽：`control`（available、canTrigger、reason、heartbeatAgeSeconds、exportAgeSeconds、warnings）、`timezone`、`activeJob`、`cards[4]`（含 `lastDueAt`、`overdue`、`never`）、`backups[]`、`schedule{entries[{job,cron,nextRunAt}],retention}`、`repos[]` |
| `GET /backups/jobs?limit=&before=` | VIEWER 以上 | 二 | Console 發起的工作，新到舊；`requestedBy`、`detail` 僅 ADMIN 有值 |
| `GET /backups/jobs/{id}` | VIEWER 以上 | 二 | 單筆（輪詢用）；查無 404 `backup_job_not_found` |
| `POST /backups/jobs` | **僅 ADMIN** | 二 | body `{type, confirm:true}`；成功 202；400 `backup_confirm_required`、409 `backup_job_in_progress`／`backup_too_frequent`、422 `invalid_request`、503 `backup_control_unavailable` |

reason 的中文由 `lib/domain/sysadminBackup.ts` 的 `BACKUP_REASONS` 持有，與契約檔 reason 表雙向鎖（`BackupReasonsContractTest`；沿議題中心先例，不入 `reasons.ts`）。設定（`console.backup.*`；未設＝停用，沿 `docker-compose.yml:149-157`；GET 只依 `export-dir`，POST 另依 `request-dir`）：`request-dir`／`export-dir`（`CONSOLE_BACKUP_REQ_DIR`／`CONSOLE_BACKUP_OUT_DIR`）、`request-ttl-seconds` 120、`job-max-seconds` 21600、`reconcile-interval-ms` 5000、`overdue-grace-minutes` 30、`min-full-interval-seconds` 86400、`min-diff-interval-seconds` 3600；sidecar：`BACKUP_CTL_POLL_SECONDS` 5、`BACKUP_CTL_EXPORT_SECONDS` 60、`JOB_LOCK_WAIT_SECONDS` 7200。

## 9. 技術選型與模組落點

**9.1 架構決策 ADR-BK-1：console-api 如何碰到 sidecar（本 PRD 最重要的一節）**

console-api 與 sidecar 之間只有網路可達性（同在 db-net，F-10；`:9854` 只供唯讀指標），沒有控制通道。候選與比較：

| 候選 | 攻擊面 | 失敗可見性 | Windows 開發機可測 | CI 可測 | 實作量 | 結論 |
|---|---|---|---|---|---|---|
| **A** sidecar 內加認證 HTTP 服務（busybox httpd CGI＋共享密鑰；或加裝 python3） | db-net 新增監聽埠（F-10 同網成員皆可連），認證、請求大小、逾時自管；busybox httpd 無 TLS、無限流，以 nobody 執行（F-09），CGI 要以 postgres 身分跑 pgbackrest 得有 setuid／sudo 類提權助手＝更大的提權面 | 狀態碼即時；服務死掉＝連線失敗，需另輪詢 | console-api 側 MockWebServer 可測；服務本體只能在 Linux 容器測 | 需起容器或 stub 服務 | 共通部分＋HTTP 服務＋密鑰注入兩端 | 不採 |
| **B** 單一共享卷佇列 | 無新埠；但整卷 backend 可寫，方向靠權限位元（1777）與 uid 約定；建立順序陷阱同 `docker/README.md:483` | 同 B′ | 同 B′ | 同 B′ | 同 B′ | 不採（弱於 B′） |
| **B′** 兩卷佇列：請求卷（backend 寫、sidecar `:ro`）、輸出卷（sidecar 寫、backend `:ro`） | **無新埠**；方向由 mount 層強制；請求只是封閉詞彙小 JSON，runner 不開啟請求以外的路徑、不回顯原文 | 心跳檔＋TTL＋結果檔，離線可偵測，延遲 ≤5 秒 | console-api 純檔案 I/O（`@TempDir`）；掛載旗標與權限測不到，改由 compose 旗標鎖＋真機 V9 | console-api 側純 JUnit；sidecar 側契約測試；compose 旗標鎖（PyYAML pytest） | 共通部分＋runner 約 100 行 bash＋兩卷 | **採用** |
| **C** 經 engine-bridge 代理 | 讓 Bridge 碰 sidecar 只能給 docker socket＝主機 root 等價（Bridge 會跑引擎的 shell），否則缺最後一跳，仍需 A 或 B′ | — | — | — | 只多一層 | **不可行**：compose 無 socket（F-10）；Bridge 契約屬引擎旁車（Architecture §10） |
| **D／E／F** D＝docker.sock 掛進 console-api；E＝console-api 自跑 pgbackrest；F＝`backup_jobs` 當佇列、sidecar 輪詢 DB | D：任何 RCE＝整台主機；E：需掛 `pg_backup`、`pg_data` 並持有 cipher 與 S3 金鑰；F：sidecar 需應用表寫權限，違反「新表由 console-api 唯一寫入」（Architecture §7.2） | — | — | — | — | 排除 |

**理由**（為何 B′）：A 的共通工作（狀態、匯出、互斥）B′ 一樣要做，B′ 只少了「HTTP 服務＋密鑰＋提權助手」這個新攻擊面；與 B 相比，B′ 把「誰能寫哪裡」從權限位元與 uid 約定換成 mount 旗標，runner 也不必刪他人的檔。代價是最多 5 秒的撿取延遲與多一個卷。狀態與清單也由 sidecar 匯出成檔，不另走 `:9854`；資料庫掛掉時讀取面仍可用（AC-BK-05-5）。

**9.2 B′ 的運作**：console-api 先插入 QUEUED 列（部分唯一索引兜底單工），再把請求寫成 `/backup-req/<id>.json`（失敗＝補償，AC-BK-06-9）→ sidecar runner 迴圈（背景、postgres 身分、每 ≤5 秒、**永不等待子行程**）撿最舊且 `results/<id>.json` 尚不存在的合法請求 → 先寫 results（running＝「已撿」，至多一次）→ 背景子行程跑 `job-run.sh` 並於結束時寫終態；匯出由另一個受 `timeout` 約束的背景子行程做。console-api 的對帳（`BackupJobReconciler`，沿 `SoftDeletePurge.java:34-103` 樣式、例外只記 WARN；有進行中工作時每 5 秒，每次 GET 順帶）寫回終態與審計（AC-BK-06-6、06-8）；終態後刪請求檔，啟動時清逾 24 小時殘檔。**權限**（沿 `docker/README.md:483`）：卷由寫入者的映像定義擁有者，讀取端 `:ro,nocopy`。

**9.3 sidecar 變更（皆為新增；既有備份腳本、verify、pg_dump 本體零修改）**：新腳本 `job-run.sh`、`backup-ctl-export.sh`、`backup-ctl-runner.sh`（階段一只做心跳與匯出，階段二加請求處理；`--once` 供測試）；`crontab` 四條工作改經 `job-run.sh`；entrypoint 在 root 階段建目錄、由 crontab 產 `schedule.json`、背景啟 runner；metrics 腳本追加三個指標；`alerts.yml` 增兩條；healthcheck 不改（runner 死掉由心跳過期在 UI 與 Prometheus 可見）。

**9.4 模組落點表**（本功能全在 AgentConsole 內；依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2「子專案內的模組不往根層放」與 `Architecture.md` §3 填；**根層無新模組、不動 `tools/`、`.claude/`、`.github/`**；CI `agentconsole-ci.yml` 的 paths 已含 `AgentConsole/**`）。行號為 2026-10-27 現況，TCS 階段重核；每處都是同 commit 的可見上修，不刪斷言；計數釘值分階段列為「階段一→階段二」。

| 件 | 落點 | 職責 | 測試（新增） | 需同步改的既有鎖與文件（逐檔逐行） |
|---|---|---|---|---|
| 規格文件 | 本檔；`AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-<日期>.md`；`AgentConsole/docs/02_architecture/API_Contract_SysAdminBackup.md` | 需求、測試契約、端點與檔案協定 | — | `Architecture.md` §2.5 `:169-186`（卷 12→13→14）、§5.1 `:300-331`、§7.2 `:614-618`、§8.2 `:660-673`、§9.4 `:856-869`、§11.1 `:973-982`；`docker/README.md` `:60-69`、`:384`（「共 12 條」→14）、新增〈4.6 控制面〉、§9 加 #35、§10；RTM 新增子表（編號依落地序） |
| sidecar 新增 | `AgentConsole/docker/pgbackrest/scripts/{job-run,backup-ctl-export,backup-ctl-runner}.sh`；`docker/pgbackrest/tests/`（stub、`fixtures/mask-probes.txt`） | §9.3 | `BackupSidecarContractIT`（Testcontainers：`debian:bookworm-slim`＋`jq`＋`util-linux`，掛腳本與 stub，非 root 執行以略過 `gosu`）；`engine-bridge/tests/test_backup_ctl_deploy_config.py`（PyYAML：掛載旗標、規則檔載入；先例 `test_deploy_config.py:99-108,226-242`） | shellcheck：`**/*.sh` 在 `shellcheck-ci.yml:33` 的 paths 內，基線以「路徑::規則」計筆數（`tools/run_shellcheck.py:67-69`）⇒ 新腳本須 0 筆、不得新增基線鍵 |
| sidecar 既有小改 | `crontab:6,9,12,15`；`pgbackrest-entrypoint.sh:56-67`；`pgbackrest-metrics.sh:93-105` 之後；`Dockerfile:36-43`（加 `/backup-out`、`/run/backup-ctl`）；`docker/prometheus/alerts.yml` 末尾（+2 條）；新增 `docker/prometheus/tests/backup_alerts_test.yml` | 包裝、啟動、指標、規則 | 契約測試；`promtool`（比照 `tests/slo_test.yml`） | — |
| compose 與映像 | `docker-compose.yml`：頂層 `volumes:`（`:796-818`）階段一加 `backup_out`、階段二加 `backup_req`；pgbackrest（`:559-564`）掛 `backup_out:/backup-out`、`backup_req:/backup-req:ro,nocopy`；backend（`:170-175`）掛 `backup_req:/backup-req`、`backup_out:/backup-out:ro,nocopy` 並設 `CONSOLE_BACKUP_REQ_DIR`、`CONSOLE_BACKUP_OUT_DIR`；`.env.example` 加選填項；`backend/Dockerfile:32`（階段二加 `/backup-req`，屬 spring） | 兩卷、方向由 mount 旗標強制 | `docker compose config`；旗標鎖（上列 pytest）；AC-BK-08-3 | **已複核不破**：`test_deploy_config.py:99-108`（backend 區塊子字串檢查）、`:226-235`；`test_si_deploy_config.py:232-281,428-448`（只驗 engine-bridge 掛載與 backend SI 變數）；M5 實跑 |
| console-api 新增 | `backend/src/main/java/com/aisdlc/console/`：`adapter/in/web/BackupController`＋`dto/Backup*`；`application/{port/{in,out}/Backup*,service/{BackupQueryService,BackupJobService,BackupJobReconciler}}`；`domain/model/backup/`（cron 前後時刻、逾期、遮罩純函式）；`adapter/out/{persistence/BackupJobAdapter,control/FileBackupControlAdapter}`；`infrastructure/config/BackupProperties`；`db/migration/V15__backup_jobs.sql`（階段二） | §9.1～9.2 | `BackupApiIT`、`FileBackupControlAdapterTest`（`@TempDir`）、`BackupJobMigrationIT`、`BackupArchTest`、`BackupReasonsContractTest`（映像沿 `SharedPostgres.java:14`）；名稱不符 `Si*Controller`，不受 `SiReadOnlyArchTest.java:72,91-92` 計數鎖 | — |
| console-api 既有 | `SecurityConfig.java`（`:41-53` 說明、`:84-92` 加規則，階段二）、`ErrorReasons.java`（`:144` 後）、`application.yml`（`:136-142` 旁） | ADMIN 規則、reason、設定 | `BackupApiIT` | `OpenApiIT.java:136、160`（`hasSize(74)`：→75→77）、`:144`（85：→86→89）、`EXPECTED` `:38`；階段二：`SchemaMigrationIT.java:68`、`V5UpgradeMigrationIT.java:135`、`SiConsoleWritesMigrationIT.java:129`、`IssuePriorityMigrationIT.java:131`（補 "15"） |
| frontend 新增 | `AgentConsole/frontend/`：`app/sysadmin/{page,backup/page}.tsx`；`components/domain/sysadmin/`（`SysAdminHome`、`BackupView` 與其子元件）；`lib/domain/sysadminBackup.ts`；`lib/api/{endpoints,queries,types}.ts`＋`schema.d.ts` | 畫面與純函式；角色沿 `useAuth`（`IssuesView.tsx:197-199`） | `*.test.tsx`、`lib/domain/sysadminBackup.test.ts`、`tests/e2e/sysadmin-backup.mock.spec.ts`、`tests/e2e/sysadmin-backup-docker.stack.ts`；守 `tests/design-rules.test.ts` | 見下列 |
| frontend 既有鎖 | `lib/nav/registry.ts`（`:11` 註解「八項」→「九項」、`:36-95` 末尾加一列）；**`lib/nav/issues-nav.test.ts:17-34`**（`:18` 長度 8→9、`:19` id 清單、`:27` 顯示序插在 settings 與 self-improving 之間、`:32-33` order 唯一與 icon 互異 8→9；`:23` `NAV_REGISTRY[7]` 仍是 issues）；`lib/nav/registry.test.ts:16-42、100-109、122、138、350-361`；`components/layout/ToolsRegion.test.tsx:76-95、115、121、147、154-161`；`lib/api/endpoints.test.ts:198-201`（83：→84→87）、`si.endpoints.test.ts:43-46` | 九項、函式計數 | — | 導覽鎖階段一同 commit 上修；`AT_950_10_E_1` 改述「原八列不變，另加系統管理」；不動 `reasons.ts`，新函式不以 `Si` 起頭 |
| 條件列：每頁說明 PRD（草案；行號隨稿漂移） | `Console_PageHelp_PRD.md`：AC-PH-03-1（撰寫時 `:90` 路由集合＝`HELP_ROUTES` 鍵）、AC-PH-03-2（`:91` enabled 導覽項皆有說明）、AC-PH-03-4（`:93` 頁檔 id＝`HELP_PAGES`∪`PENDING_HELP_PAGES`） | 新增兩路由與導覽項會使三條轉紅 | — | PageHelp 先落地＝本案補兩個頁檔並登記 `HELP_ROUTES`（內容可先入 `PENDING_HELP_PAGES`，AC-PH-03-6）；本案先落地＝PageHelp 實作時納入（以其 TCS 為準） |

- **已複核不需改**：`si-login-gate.test.tsx:65-67`（只比「自我進化」label 與 href）、`layout.test.tsx:135-137`（長度由登記表推導）、E2E `shells-and-layout.spec.ts:26-41`、`p9-w7-ui.spec.ts:180-206`（逐名點選、不計項數；新名稱與既有導覽名互不為子字串）。

**9.5 連動面（同一個 commit 收齊，根 `CLAUDE.md` 第 5 條）**：上表第五欄全部上修；Architecture 與 README 同步；RTM 回填四格（鐵律 12）；`git diff --name-only` 只動 `AgentConsole/**` 與本檔（鐵律 7）。派工（鐵律七）：sidecar＋compose、console-api、前端各一包；先凍結 API 契約檔（含 §8.2 協定）再並行；一鍵一視窗。

## 10. 風險

| # | 風險 | 緩解 |
|---|---|---|
| R1 | **最嚴重**：crontab 包裝出錯＝排程備份失敗 | 包裝只做 `flock`、寫狀態、透傳 rc，狀態寫入失敗與鎖檔開不了皆 fail-open（AC-BK-09-3）；契約測試；隔日 02:00 真實排程驗證（V6）；退回＝還原 crontab 四行 |
| R2 | 卷權限與掛載旗標出錯（同 `docker/README.md:483` 型） | 寫入端映像定義擁有者、讀取端 `:ro,nocopy`（AC-BK-09-6）；compose 旗標鎖；真機 V9 |
| R3 | runner 死掉只剩心跳過期可見；長工作若阻塞迴圈會誤報離線 | 迴圈永不等待子行程（AC-BK-09-8）；AC-BK-05-2、09-7；不改 healthcheck |
| R4 | verify 吃容器層暫存與 CPU（上限 0.5 CPU、512M，`docker-compose.yml:578-582`）；pgBackRest 升版使 `info` JSON 形狀改變 | 對話框提示、單工；`schema_rev`＋fail-loud，契約夾具取自 F-03 |
| R5 | 時區混淆（sidecar 台北、瀏覽器本機、pg_dump 檔名 UTC）；`info` 不列失敗備份 | 各處標註時區（AC-BK-02-3）；失敗由狀態卡與工作紀錄補 |
| R6 | 跨案耦合（D-BK-10）；Windows 上控制面未驗（`docker/README.md:4,506`） | §9.4 條件列；真機項全在 Windows＋Docker Desktop 跑 |
| R7 | **資料遺失路徑**：手動全備、增備擠掉保留名額（份數制，F-07）——已有 4 份時，每完成一份全備就當下（備份後自動 expire）刪最舊一份與依附備份，可回溯期縮短 | 對話框寫明保留名額與將被刪標籤（AC-BK-06-1）；伺服器端頻率上限（AC-BK-06-10）；Q3 |
| R8 | runner 讀不可信請求檔（符號連結、替換競態、FIFO 阻塞） | `timeout` 子殼內開檔後 lstat 並比對 fd 的 dev:ino、只讀前 4 KB、結果與 WARN 不回顯原文（AC-BK-09-2）；請求卷 sidecar `:ro` |

## 11. 分階段與出口條件（症狀型）

| 階段 | 交付與 AC 歸屬 | 出口 |
|---|---|---|
| 階段一（看） | 導覽、`GET /backups`、清單、排程、狀態卡、說明區；`job-run.sh`、匯出、心跳、crontab 包裝、`backup_out` 卷。AC：BK-01～04、05-1～05-4、08、09-3～09-8（09-6 僅 `backup_out`）、10-4、10-5（`getBackupOverview`） | 屬本階段的機械項全綠；真機 V1、V2、V3、V6 |
| 階段二（控） | runner 請求處理、`POST` 與工作紀錄、V15、對帳、確認對話框、`backup_req` 卷與 backend 映像目錄。AC：BK-05-5、06、07、09-1、09-2、09-6（`backup_req`）、10-1～10-3、10-5（其餘三個操作） | M1～M6 全綠；真機 V4、V5、V7、V8、V9 |

**機械可驗（M；工作目錄＝monorepo 根）**
- M1 `Push-Location AgentConsole\backend; .\gradlew.bat clean build; Pop-Location` 為 BUILD SUCCESSFUL（含 §9.4 列的 console-api 新測試與 `OpenApiIT`；`BackupApiIT` 以測試內的假 runner 執行緒替代 sidecar；JaCoCo ≥80%）。
- M2 `Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; npm run build; npx vitest run; Pop-Location`；`npx playwright test sysadmin-backup.mock.spec --output=test-results-mock`。
- M3 `BackupSidecarContractIT`（需 Docker，隨 backend leg 執行）；`python tools\run_shellcheck.py` rc=0。M4 `promtool check rules` 與單元測試（命令同 `docker/README.md` 〈可用性 SLO〉），**本機限定**：`.github/workflows` 無 promtool 步驟（`Grep` 現查），列為已知缺口。
- M5 §9.4 既有鎖同 commit 上修後綠；`Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; python -m pytest -q tests/test_deploy_config.py tests/test_si_deploy_config.py tests/test_backup_ctl_deploy_config.py; Pop-Location`；`git diff --name-only` 只含 `AgentConsole/**` 與本檔。M6 說明區兩把文件鎖（AC-BK-08-1、08-3）。

**掌舵者真機（V；Windows＋Docker Desktop 全棧）**
- V1 開頁，不看英文答出 §1 的四題。V2 清單與 `pgbackrest info` 逐份相符。V3 `docker compose up -d --force-recreate pgbackrest` 後卡片與最近結果仍在。V4 按一次「立即增備」：進行中→成功、清單多一列、`console.audit_log` 的 `entity_type='backup'` 有 POST 與 system 兩列。
- V5 OPERATOR 或 VIEWER 登入：看得到、按不到、網路面板零 POST；`docker compose stop pgbackrest` 後 ≤60 秒出現紅橫幅且按鈕停用，`start` 後恢復。V6 部署後隔日 02:00 排程備份照常成功。V7 按一次「立即驗證」：進行中橫幅全程在、不出現「控制面無回應」，完成後卡片成功。V8 兩個分頁同時按：恰一個成功、另一個見「已有進行中工作」。
- V9 掛載方向與權限：`docker compose exec backend sh -c 'touch /backup-out/x'` 與 `docker compose exec pgbackrest sh -c 'touch /backup-req/x'` 都必須失敗（唯讀）；`docker compose exec backend ls /backup-out/export` 必須列得出檔；`down -v` 重建後第一次 POST 即成功。

## 12. 與既有系統的整合點（檔案:行號）

逐檔逐行見 §4 與 §9.4；另列只在此引用者：`Architecture.md:396-433`（導覽接入檢查表）、`RequestAuditTrail.java:42-59,85-98`（審計標註）。主要入口：`registry.ts:36-95`、`SecurityConfig.java:84-94`、`AuditLoggingFilter.java:63-93`、`SoftDeletePurge.java:34-103`、`docker-compose.yml:535-586,796-818`、`pgbackrest-entrypoint.sh:56-67`、`pgbackrest-metrics.sh:93-105`、`alerts.yml:84-118`。

## 13. 主控代決清單與開放問題

**主控代決（SA 預設；掌舵者可隨時推翻）**
- D-BK-1 控制面載具＝B′（兩卷；§9.1；原 Q2 轉入，不再開放）。D-BK-2 UI 稱「增備（差異）」，API `type` 用 `diff`。D-BK-3 導覽 `sysadmin`、order 65、`mobile:false`、`roles` 缺、圖示 `Database`；`/sysadmin` 為入口、`/sysadmin/backup` 為備份頁。D-BK-4 GET＝VIEWER 以上、POST＝ADMIN；觸發者與輸出尾段僅 ADMIN 可見（Q6）。
- D-BK-5 各項預設值見 §8.3。D-BK-6 離站 pg_dump 不提供手動觸發。D-BK-7 不設 `audit_log_id`、`repo` 欄（§8.1）。D-BK-8 POST 需 `confirm:true`（沿設定頁二次確認先例）。D-BK-9 備份清單含離站邏輯備份。
- D-BK-10 跨案協調：本案取 V15（現最高 V14）；「自我進化帳本改 DB」案用根層自有 `V<NNN>` 與 Python runner、Flyway 只管 `console`（`SelfImproving_Ledger_DB_PRD.md` §9.1），**無撞號**。真正的耦合：(i) 「每頁說明」案三條 AC 會因新頁與導覽項轉紅（§9.4 條件列）——規則同其 D-12：先落地者占號，後落地者補 `lib/help/sysadmin*.ts` 說明項與欄位列，AC 計數由登記表長度推導、不寫死；(ii) 帳本案 B 方案要改 `docker/README.md` 〈4.3〉（同 PRD §9 落點表「文件」列），故 AC-BK-08-1 只鎖指令；(iii) 帳本案若採專屬容器會新增卷，AC-BK-08-3 須同 commit 補分類。
- D-BK-11 逾期由 API 依排程算（非前端常數、非告警規則）。D-BK-12 新增兩條 Prometheus 規則、不接通知。D-BK-13 階段切分見 §11。

**開放問題（只有掌舵者能答；Q2 已轉為 D-BK-1）**

| # | 問題 | SA 建議與理由 |
|---|---|---|
| Q1 | 要不要做「還原演練」按鈕？ | 手動「驗證」已是還原演練（還原到臨時實例、不碰正式庫）。「還原回正式庫」按鈕**建議不做**：要先停 primary、`restore.sh` 在 primary 運作時拒絕、replica 時間軸須重建（F-14），而 console-api 依賴正被還原的資料庫。維持「說明＋指令」；堅持要做另開 PRD |
| Q3 | 保留策略與排程要不要可調？ | **都不可調，唯讀顯示**。保留：調小＝下一次 expire 即**不可逆地**刪備份，本頁沒有還原安全網（見 R7）。排程：crond 只在 crontab 目錄 mtime 改變時重讀（`docker/README.md:231`），改它須 root 寫新檔再 `mv`，壞 cron 會讓備份靜默停掉。要改走 `pgbackrest.conf`、`.env`、`crontab` 並重建 |
| Q4 | 備份失敗要不要通知？ | **本版不推播**：有失敗與逾期規則但無 Alertmanager（F-12）；Console 六條告警是專案級，加第七條要改 V4 資料表。盲區：**從未執行＝沒有序列＝規則不會亮**（`docker/README.md:499`）；頁面「從未執行」「逾期」標記是目前唯一覆蓋它的地方 |
| Q5a | 「系統管理」下原話有兩個子項（系統管理、資料庫備份），第一個放什麼？ | **本版只交付「資料庫備份」**，`/sysadmin` 只放入口卡；另一個請指定 |
| Q5b | `engine_workspace`（F-13）不在 DB 也不在備份內，要不要納入？ | **本版不納入**，頁面列為「未涵蓋」（AC-BK-08-2）。要「Console 所有資料都進 DB」屬 **Bridge 契約變更**（`run.json`、`events.jsonl`、`_audit.jsonl`、`_drafts/` 改寫入 DB，動 `engine-bridge/app/{events,runner,db}.py` 與 Architecture §10，console-api 切讀），**粗估 3～4 輪**；較省替代＝定期 `tar` 到 MinIO（粗估 1 輪） |
| Q6 | VIEWER、OPERATOR 是否該看到備份頁？ | **維持可看（唯讀）**：內容是時間、大小、狀態，低敏；觸發者與輸出尾段僅 ADMIN。要全藏：導覽項加 `roles:["ADMIN"]`（`registry.ts:24-27`）、`GET` 改 ADMIN 專屬一條規則 |
| Q7 | 要不要顯示 WAL 歸檔健康？ | **建議顯示一行唯讀**（最近歸檔時間、失敗次數、最近失敗時間）：WAL 歸檔失敗是最危險的靜默失效（`docker/README.md:389`）；console-api 既有連線可直接查 `pg_stat_archiver`（F-15），只多一個 AC（查不到顯示「—」、不當 0）與一個唯讀查詢；`info.json` 的 `archive` 段看不出失敗，故不用 |
| Q8 | 預設離站是同機單碟 MinIO（`docker/README.md:491`），「離站」要不要改稱「同機副本」？ | **保留「離站」給外部 S3；本機 MinIO 一律標「與主機同碟」徽章**並在涵蓋說明寫明（AC-BK-02-6）：避免「離站有沒有備到」給虛假安心 |

## 14. 變更記錄

- **v0.2～v0.4**（2026-10-27）：一審 R-01～R-15、二審 N-01～N-05、三審 RS-1～RS-4 已處理。
