# Test Contract Specification — 系統管理／資料庫備份：備份清單與狀態卡、sidecar 控制面（runner、匯出、包裝）、手動觸發與工作紀錄、還原說明與涵蓋範圍、Flyway V15、導覽「系統管理」
# 測試契約規格文件（新功能；FRD-lite 併入檔頭；一份 TCS 涵蓋一把 SDD 鍵）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位 PRD 已於 Stage-1 凍結）的單一 Feature（系統管理／資料庫備份，階段一加階段二）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因 Stage-1 的 PRD 在根層 `docs/01_requirements/`、本檔在 `AgentConsole/docs/`，兩份文件跨兩個目錄）
**spec-format-version**: 1.0
**scenario**: brownfield

---

> **上位 PRD digest**：`sha256:848c2acfae30d3034205d647effd5000189c776f29db743629d4a4bdb1d0800a`（`docs/01_requirements/Console_SysAdmin_Backup_PRD.md` v0.4＋〈勘誤一〉1-1～1-15；68,126 bytes；2026-10-28 由主控追加勘誤節後重算，與本檔同於 Stage-2 凍結；Stage-1 凍結值為 `sha256:f61fd7cbd2f1e6d100b6f1f41d0bc04ec7589065346ea088c33dbe3883cd7287`（60,936 bytes，commit `000a217b`，鍵 `agentconsole-sysadmin-backup`））。🔴 **查證基準＝commit `000a217b`**（撰寫期間 HEAD 前進為 `99c9a868`，只動根層 `tools/tests` 與缺陷帳本，`AgentConsole/**` 與 `docs/01_requirements/` 零差異，現況座標仍成立）。本檔不改 PRD 正文；PRD 的問題一律寫成 §7.3 的〈勘誤〉草稿，凍結後走 PRD〈勘誤〉（PRD 目前沒有〈勘誤〉節，須新建）。
> **範圍**：階段一（看）加階段二（控）合訂一份（PRD §11）。PRD §5 的 AC 共 53 條（本檔機械計算；PRD 檔頭沒有計數宣稱）；另依掌舵者 Q7 裁決（PRD §13：「顯示 WAL 歸檔健康一行」）補 1 條 TCS 增量 AC（`AC-BK-04-6`，PRD §5 沒有對應條文，勘誤 1-1）。每條 AC 至少一個 AT，需要負控、邊界或錯誤路徑者另有反向 AT。

## 文件資訊

| 項目 | 內容 |
|---|---|
| 檔案 | `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md`（新；SDD 規格階段 Stage-2 契約。置於子專案目錄，沿 AgentConsole 單鍵功能的先例如 `TCS-FsmTrail-20261018.md`；根層 `docs/03_testing/contracts/` 留給 monorepo 鍵與跨兩鍵的功能） |
| 版本與狀態 | v0.3 草案（一審 FAIL→v0.2→抽驗 PASS 後補 N-1～N-9；首稿 v0.1），待 Stage-2 凍結（一鍵）；2026-10-27 起草；作者角色＝QA Engineer（Sonnet 5.5，依主控任務書）；〈勘誤〉節凍結前留空 |
| 上位規格 | `docs/01_requirements/Console_SysAdmin_Backup_PRD.md` v0.4（digest 見檔頭）；先例 TCS：`docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（節體例、契約節、突變規格、閘門指令）；姊妹 TCS：`TCS-PageHelp-20261027.md`；運維真相 `AgentConsole/docker/README.md` |
| SDD 鍵（BRIDGE §8，一功能一鍵） | `agentconsole-sysadmin-backup`（Console 單半；改 `AgentConsole/docker/pgbackrest/**` 同屬此鍵） |
| 規模 | R 條文 62 條；AT 226 個（正向 148、反向 68、真機 10）；AC 54／54 全覆蓋（§1、§6；含 1 條 TCS 增量 AC）；契約節 §C0～§C6；§5.7 允許變更集合一張；閘門指令一組（SCG-4 通過標準） |
| 載具與判定指令 | backend JUnit 5（`gradlew test --tests`）、sidecar 契約測試（Testcontainers）、Bridge 目錄 pytest、promtool、vitest、Playwright、審查閘（G 指令）、真機手動；細節見 §2、§3.1 |
| 讀法 | 三個開發包：**S 包**（sidecar＋compose＋Prometheus＋README）＝§C1、§C2、§C6＋載具 BS、PY、PT＋§5.7 S 表；**K 包**（console-api）＝§C3～§C5＋載具 BQ、BU、BF、BD、BV、BM、BA、BC＋§5.7 K 表；**F 包**（前端）＝§C3 的消費面＋載具 FN、FT、FH、FV、FD、FL、FK、FS、E2、ES＋§5.7 F 表。兩兩共同的只有 §C1（控制面檔案協定：S 寫 K 讀）與 §C4（reason 表）；契約檔 `API_Contract_SysAdminBackup.md` 由 K 包依 §C 逐表抄成，**先於三包**；三包依 S→K→F 串行（PRD §9.5 的「再並行」在此收斂：S、K 共用 `compileTestJava`） |

### 凍結後修訂路由（本案單鍵）

1. 只動本檔（R 條文、§C 契約、AT、§5.7、D 表）的勘誤：落本檔〈勘誤〉節並附新 digest，由 `agentconsole-sysadmin-backup` `spec-refreeze`。
2. 上位 PRD 的修訂（PRD 已凍結、不可原地改；本案＝§7.3 的〈勘誤一〉1-1～1-15）：PRD 目前沒有〈勘誤〉節，須先於檔尾新建並貼入（只追加），同步更新本檔檔頭 digest，再 `spec-refreeze`；兩處引同一條號。
3. 與姊妹案的耦合（PRD §9.4 條件列：每頁說明 `agentconsole-page-help`、帳本改 DB `monorepo-si-ledgerdb-p0`）：若落地順序使他案文件需要改（例：PageHelp 的 AC-PH-03-1／03-2／03-4 因新路由轉紅），先落地者占號、後落地者補；牽動他鍵文件時主鍵先 refreeze、副鍵引同一勘誤條號隨後 refreeze，兩鍵引用的 digest 須相同。
4. 凍結審批依根 CLAUDE.md〈凍結常態規則〉（SCG／QA 審查 PASS 且主控親驗無 P1、P2 才代執行）。

## 增量變更專用：FRD-lite 與〈增量追溯表〉

### FRD-lite

**Before／After（現值皆於基準 `000a217b` 實查；每處上修都是同 commit 的可見釘值上修、不刪斷言）**

| 面 | Before | After |
|---|---|---|
| 導覽登記表 | 8 項（`lib/nav/registry.ts:36-95`；`self-improving` 為 `[6]`、`issues` 為 `[7]`） | 9 項（末尾加 `sysadmin`，order 65，`[8]`） |
| 前端路由 | 無 `/sysadmin` | `/sysadmin`（入口卡）、`/sysadmin/backup`（備份頁） |
| backend 路徑／操作（`OpenApiIT.java:136,144,160`） | 74 路徑、85 操作 | 階一 75／86；階二 77／89 |
| Flyway | V1～V14（最高 `V14__issue_priority.sql`） | 階二 V15（`V15__backup_jobs.sql`） |
| compose 頂層具名卷（`docker-compose.yml:796-818`） | 12 | 階一 13（`backup_out`）；階二 14（`backup_req`） |
| `alerts.yml` 規則數（`docker/README.md:384` 「共 12 條」） | 12 條 | 14 條（`aisdlc-backup` 群組末尾 +2） |
| sidecar | crontab 直接呼叫四支工作腳本；無控制面；`cron.log` 在容器層（重建即歸零，F-06）；無 pg_dump／驗證的狀態與指標 | 四條工作改經 `job-run.sh`；新增 `job-run.sh`、`backup-ctl-export.sh`、`backup-ctl-runner.sh`；狀態與匯出住具名卷 `backup_out`；指標 +3 |
| `endpoints.ts` 匯出函式（`endpoints.test.ts:198-201`） | 83 | 階一 84（`getBackupOverview`）；階二 87（`getBackupJobs`、`getBackupJob`、`postBackupJob`） |
| 四個 migration IT 的版本清單 | 1～14 | 階二補 15 |
| `ErrorReasons` | 以 `ISSUE_NOT_RANKABLE` 結尾（`:144`） | +5 個 `BACKUP_` 前綴常數（階二） |
| 根層、Bridge、引擎、`.claude`、`.github` | — | 零變動（PRD §9.5） |

**使用者故事（US，一 FR 一則；AC 對應見 §1、§6）**

| US | 身為掌舵者，我要… | 以便… | FR |
|---|---|---|---|
| US-BK-01 | 左列有「系統管理」，點進去有「資料庫備份」入口 | 找得到備份頁、不迷路 | FR-BK-01 |
| US-BK-02 | 看到備份清單（含離站與邏輯備份）、標明「與主機同碟」 | 不被「離站已安全」的假象誤導 | FR-BK-02 |
| US-BK-03 | 看到排程與保留策略（唯讀） | 知道備份何時跑、留多久，且不會誤改 | FR-BK-03 |
| US-BK-04 | 四張卡一眼看出昨晚備份成功了嗎、有沒有逾期，並看到 WAL 歸檔健康 | 不開終端機就能判斷備份是否安全 | FR-BK-04 |
| US-BK-05 | 控制面壞掉、匯出過期、資料讀不到時明說原因 | 「量不到」不被讀成「沒有」 | FR-BK-05 |
| US-BK-06 | 按一個鈕（僅 ADMIN）補一份全備、增備或驗證，並看到進行中與結果 | 大批變更後立刻補備份，且不因手滑刪掉舊備份 | FR-BK-06 |
| US-BK-07 | 看 Console 發起的工作紀錄（ADMIN 看輸出尾段） | 追得到誰何時做了什麼、為何失敗 | FR-BK-07 |
| US-BK-08 | 看還原步驟與「哪些資料沒被備份」 | 出事時知道怎麼救、也知道哪些救不回 | FR-BK-08 |
| US-BK-09 | sidecar 端有安全、不阻塞的控制面 | 備份排程不被手動請求或匯出拖累 | FR-BK-09 |
| US-BK-10 | 資料、稽核與權限都守規矩，機密不外洩 | 控制面不成為新的攻擊面 | FR-BK-10 |

**User Story INVEST 自檢（SCG-0；AC 與 AT 數由 §1、§3 機械計算）**

| US | I 獨立 | N 可協商 | V 有價值 | E 可估 | S 夠小 | T 可測（AC／AT） |
|---|---|---|---|---|---|---|
| US-BK-01 | 是（最先交付） | 是 | 是 | 是 | 是（3 條 AC） | 是（3／12） |
| US-BK-02 | 依 US-BK-01 | 是 | 是 | 是 | 否（FR 級，6 條 AC） | 是（6／19） |
| US-BK-03 | 依 US-BK-01 | 是 | 是 | 是 | 是（4 條 AC） | 是（4／13） |
| US-BK-04 | 依 US-BK-01、02 | 是 | 是 | 是 | 否（FR 級，6 條 AC） | 是（6／24） |
| US-BK-05 | 依 US-BK-02（匯出檔） | 是 | 是 | 是 | 是（5 條 AC） | 是（5／19） |
| US-BK-06 | 依 US-BK-04、05、09（階段二） | 是 | 是 | 是 | 否（FR 級，11 條 AC） | 是（11／50） |
| US-BK-07 | 依 US-BK-06 | 是 | 是 | 是 | 是（3 條 AC） | 是（3／13） |
| US-BK-08 | 依 US-BK-01 | 是 | 是 | 是 | 是（3 條 AC） | 是（3／9） |
| US-BK-09 | 是（S 包獨立；與 K 包只靠 §C1） | 是 | 是 | 是 | 否（FR 級，8 條 AC） | 是（8／48） |
| US-BK-10 | 跨切面，依 US-BK-06 | 是 | 是 | 是 | 是（5 條 AC） | 是（5／19） |

註：N 的可協商處＝畫面用語與細節；S 為「否」者是 FR 級故事，以 AC 為最小可測單位、以持有面（S／K／F 包）為最小派工單位；I 的依賴即派工順序（契約檔先、S 先 K 後、F 最後；compose 卷由 S 先落地 F 才補涵蓋表）。以上為作者自檢，審查可推翻。

**持有面、鎖的住所與提交順序（鐵律七：一道鎖的常數、史料、消費端若不在同一持有面，不得派並行包）**

| 鎖或件 | 常數（真相） | 史料與消費端 | 持有面與順序 |
|---|---|---|---|
| 控制面檔案協定 v1（§C1） | 本檔 §C1 與契約檔 | S 包寫（sidecar 腳本）、K 包讀（`FileBackupControlAdapter`、假 runner） | 契約檔先凍結；**S 先、K 後（串行）**：`BackupSidecarContractIT` 住 backend 測試樹，與 K 包同一個 `compileTestJava`，並行會互踩編譯與夾具；兩端只靠 §C1，欄位變動走勘誤 |
| 頂層卷集合 ↔ 前端涵蓋表（AC-BK-08-3） | `docker-compose.yml` 頂層 `volumes:` | `test_backup_ctl_deploy_config.py`（釘 13／14）、前端 `backup-docs.test.ts` 與 `VOLUME_COVERAGE` | **串行**：S 包先落地卷，F 包再補涵蓋表與測試；不得並行（同一檔、兩個持有面） |
| `OpenApiIT` 計數、`schema.d.ts`、`endpoints.test.ts` | backend 路徑與操作 | 前端 `schema.d.ts`（`npm run gen:api` 對在線 backend 重產）、`endpoints.ts` | K 先；F 於 K 完成、backend 在線後重產並入庫 |
| backup 類 reason 雙向鎖（R-BK-60） | 契約檔〈backup 類 reason 表〉（K 包依 §C4 建檔） | `ErrorReasons`、後端工作理由列舉（K）、前端 `BACKUP_REASONS`（F） | 契約檔與 `ErrorReasons` 同包先做；`BACKUP_REASONS` 後做並與表逐字相同 |
| 共用夾具檔（`mask-probes.txt`〔R-BK-42〕、`info-2repo.json`、`logical-2.json`） | `docker/pgbackrest/tests/fixtures/` 下的三個單一檔（內容見 §5.1） | S 包 `BackupSidecarContractIT`（stub 的輸出）與 K 包 `BackupDomainTest`、`BackupApiIT`、`BackupServiceTest` 共讀 | S 包先建檔（唯一真相）；K 包只讀、不建第二份；K 包相關測試待 S 包落檔後才能綠 |
| 導覽鎖（`registry.ts`、`issues-nav.test.ts`、`registry.test.ts`、`ToolsRegion.test.tsx`） | `registry.ts` | 三支既有測試 | F 包同 commit 收齊 |
| Prometheus 規則與其測試、`docker/README.md`（〈4.6〉、〈9〉#35、〈10〉、`:384`、`:60-69`） | `alerts.yml`、`backup_alerts_test.yml` | `test_backup_ctl_deploy_config.py` | S 包（README 與 compose、規則同包同 commit；F 包不改 README、只讀） |
| 落點規範、護欄層棘輪、compat-ci `paths` | — | — | **不適用**：本案零根層檔（PRD §9.4）；`agentconsole-ci.yml` 的 `paths` 已含 `AgentConsole/**` |

**D 表：本檔（TCS 階段）對 PRD 未寫死之處的定案；開發棒照做，不得另取他法；每條皆可由掌舵者推翻（走勘誤）**

| D | 定案 |
|---|---|
| D-BK-T1 | 階段切分沿 PRD §11：每個 AT 的「階」欄為一或二；跨階的 AC（05-1、05-2、08-2、09-6、09-8、10-5）以 AT 為單位分階。階段一出口＝階一 AT 全綠＋真機 V1、V2、V3、V6、V10（V10＝TCS 補列，AT-BK-09-7-R-1）；階段二出口＝全部 AT 全綠＋真機 V4、V5、V7、V8、V9 |
| D-BK-T2 | backend 建置與測試工具為 Gradle（Kotlin DSL），非 Maven；判定指令 `.\gradlew.bat test --tests "*<類>.<id>_*"`（零測試＝失敗） |
| D-BK-T3 | 本檔新增的測試類（PRD §9.4 未列）：`BackupDomainTest`（`domain/model/backup/` 的 `BackupMasker`）、`BackupServiceTest`（服務層＋假埠；`BackupCron`、`BackupOverdue` 在 `application/service/`，一併在此驗）、`BackupApiUnconfiguredIT`（共用預設 context＝未設定情境，不開新容器）；測試輔助 `support/MutableClock.java`、`support/FakeBackupRunner.java`、`support/BackupSeam.java`（`@TestConfiguration`，**只**以 `@Primary` 換專屬時鐘型別 `BackupClock` 與審計觀察包裝，**不換**全域 `Clock`：JWT、限流、審計都吃它，`SiWriteSeam.java:26-28` 先例；`AbstractApiIT` 的 JVM 靜態 token 因此不受影響）；前端新檔見 §5.7 |
| D-BK-T4 | API 約定：JSON camelCase；所有時間戳為 UTC 帶 `Z` 的 ISO-8601（`nextRunAt`、`lastDueAt` 於 `schedule.json.tz` 計算後換成 UTC 輸出）；包既有 `ApiResult`／`ApiError`；任何失敗無 `data` |
| D-BK-T5 | `control.reason` 值域與優先序：`not_configured`＞`schema_mismatch`＞`export_unreadable`＞`runner_offline`＞null；前三者所有資料區塊（`cards`、`backups`、`schedule`、`repos`、`walArchive`、`activeJob`、`timezone`）為 null；`runner_offline` 資料照回。`control.warnings` 值域封閉：`db_unavailable`、`retention_unavailable`、`info_unavailable`、`logical_unavailable`、`cron_unparsable:<job>` |
| D-BK-T6 | console-api 每請求讀 8 個檔（`info.json`、`logical.json`、`schedule.json`、`heartbeat`、`jobs/{full,diff,dump,verify}.json`；不快取）。**缺席**：`info.json`／`logical.json`／`schedule.json` ⇒ `export_unreadable`；`heartbeat` ⇒ `runner_offline`；`jobs/<job>.json` ⇒ 該 job 尚無狀態（合法，`status=no_run`）。**存在但壞**：任一檔（含 `heartbeat`、`jobs/*`）`schema_rev` 不是整數 1 ⇒ `schema_mismatch`、JSON 損毀或空檔 ⇒ `export_unreadable`。`ok:false` 是合法檔案（匯出行程自報失敗），見 D-BK-T5 的 `*_unavailable` |
| D-BK-T7 | 控制面各檔欄位的精確形狀見 §C1（含 PRD §8.2 未列的 `retention`、`repos` 欄型、`heartbeat` 的 `schema_rev`、results 的 `reason` 詞彙）；`ts`、`generated_at`、`started_at`、`finished_at`、`requested_at`、`expires_at` 一律 ISO-8601 帶 `Z` |
| D-BK-T8 | `schedule.json` 的 `entries[].job` 值域封閉：`full`、`diff`、`dump`、`verify`、`expire`、`wal_clean`；UI 工作名：全備、增備（差異）、離站 pg_dump、驗證、清理過期備份（維護工作）、清理 WAL 複本（維護工作） |
| D-BK-T9 | 卡片 `status` 值域：`succeeded`、`failed`、`running`、`interrupted`、`no_run`（UI 文字對應「成功／失敗／進行中／中斷／從未執行」）；`never`＝「最近成功時間缺席」（與 `no_run`＝「無任何執行記錄」不同：失敗過但從未成功＝`status=failed`、`never=true`；無狀態檔但清單有備份＝`status=no_run`、`never=false`）；`latestBackup` 的「最近」＝該卡類型的各 repo 最近一份中 `stop` 最大者 |
| D-BK-T10 | 逾期細則：寬限比較嚴格大於（`now > lastDueAt + 30 分`）；`never=true` ⇒ `overdue=false`（PRD 兩處文字的調和：「缺席」併入 `never`）；成功時間＝`max(狀態檔 last_success_at, 清單端)`；清單端＝（已設定的各 repo 中）最近一份符合者的 `stop` 之**最舊者**，任一已設定 repo 沒有符合者 ⇒ 清單端缺席（保守：不能保證每個 repo 都有成功）；cron 解析不了 ⇒ `lastDueAt:null`、`overdue:false`＋`cron_unparsable:<job>` |
| D-BK-T11 | `retentionQuota` 的「最舊一份」：full ⇒ 該 repo 最舊的全備標籤；diff ⇒ 該 repo 最舊的差異備份標籤；`willExpire`＝`current ≥ limit`（完成後即超過上限）；diff 的 `current`＝差異份數＋全備份數（pgBackRest 的 diff 保留把全備計入，PRD AC-BK-06-1） |
| D-BK-T12 | 頻率上限：full 以各 repo 最近一份**全備**、diff 以各 repo 最近一份**差異備份**的 `stop` 判定；「皆在門檻內」＝每個已設定 repo 都有該類備份且距今 **嚴格小於** 門檻；`nextAllowedAt`＝各 repo（最近該類備份 stop＋門檻）的最小值；判不了（info 不可讀、控制面不可用）⇒ 503 而非 409 |
| D-BK-T13 | POST 驗證序：401 → 403 → 本文為 JSON 物件（否則 400 `MALFORMED_REQUEST_BODY`）→ `type` 合法（否則 422 `invalid_request`，`details.violations[{field,message}]`）→ `confirm` 為 JSON 布林 true（否則 400 `backup_confirm_required`）→ 控制面可用（否則 503）→ 無進行中（否則 409 `backup_job_in_progress`）→ 頻率（否則 409 `backup_too_frequent`）→ 建列並寫檔。`invalid_request` 以區域常數持有、不進 `ErrorReasons`（先例 `SiWriteGates`） |
| D-BK-T14 | `GET /backups/jobs`：`limit` 預設 20、1～100；`before` 為 ISO-8601 瞬間（嚴格小於 `requested_at`）；回 `{items, nextBefore}`；參數非法 ⇒ 422 `invalid_request`；`GET /backups/jobs/{id}`：id 非 UUID 亦回 404 `backup_job_not_found` |
| D-BK-T15 | 遮罩規格與探針格式見 R-BK-42 與 §5.1；替代記號固定為 `***`；兩端（sidecar 的 perl／sed 與 console-api 的 `BackupMasker`）對探針檔的每一行須產出**逐字相同**的期望輸出；取尾段順序＝先遮罩、後取最後 2000 字元 |
| D-BK-T16 | sidecar 的指令與環境變數（測試縫）：`job-run.sh <job> <scheduled\|manual> [<uuid>]`；`backup-ctl-runner.sh [--once]`；`backup-ctl-export.sh [schedule]`；環境：`BACKUP_CTL_OUT_DIR`（預設 `/backup-out`）、`BACKUP_CTL_REQ_DIR`（`/backup-req`）、`BACKUP_CTL_LOCK_FILE`（`/run/backup-ctl/maintenance.lock`）、`BACKUP_CTL_SCRIPT_DIR`（`/usr/local/bin`，工作腳本與 stub 的位置）、`BACKUP_CTL_CRONTAB`（`/etc/crontabs/postgres`）、`BACKUP_CTL_POLL_SECONDS`（5；results 孤兒寬限＝6×此值＝30 秒，單一調參面）、`BACKUP_CTL_EXPORT_SECONDS`（60）、`BACKUP_CTL_EXPORT_TIMEOUT_SECONDS`（120）、`BACKUP_CTL_LOGICAL_MIN_SECONDS`（300）、`JOB_LOCK_WAIT_SECONDS`（7200）；預設值即生產值，環境變數只供測試與調參 |
| D-BK-T17 | 結束碼：`job-run.sh` 的 75（EX_TEMPFAIL）專指「手動拿不到鎖（busy）」與「排程等鎖逾時（lock_timeout）」；其餘一律原樣回傳工作腳本的 rc；runner 子行程見 rc 75 且為手動 ⇒ results `rejected`／`busy` |
| D-BK-T18 | results 的 `status` 值域：`running`、`succeeded`、`failed`、`rejected`；`reason` 封閉詞彙見 §C4 的八個工作理由；rejected 的 `reason`∈{`busy`、`rejected_invalid`、`expired`}；runner 對檔名非 UUID 者不寫 results（無從命名）、只記 WARN；目錄內檔數 >16＝目錄級拒絕：不執行任何請求、不寫任何 results、只記 WARN（與 PRD AC-BK-09-2〔`:116`〕「可寫時寫 `rejected`」字面不同，走勘誤 1-15；被漏處理的合法請求由 R-BK-34 的 2×TTL 兜底標 EXPIRED） |
| D-BK-T19 | 兩條新 Prometheus 規則名：`PgBackRestJobFailed`、`PgBackRestControlHeartbeatStale`（命名沿既有 `PgBackRest*`；`expr`、`for`、`severity` 見 R-BK-54）；「每條規則名都在 promtool 測試檔」只要求**新增**兩條（既有 12 條 `alerts.yml` 規則目前無 promtool 測試，不在本案補，見 §7.1 Q3） |
| D-BK-T20 | `walArchive`（Q7）＝`{lastArchivedAt, failedCount, lastFailedAt}`，讀取為一條 `SELECT failed_count, last_archived_time, last_failed_time FROM pg_stat_archiver`；port＝`WalArchiveStatsPort`、adapter＝`adapter/out/persistence/WalArchiveStatsAdapter`（TCS 命名）；讀不到 ⇒ `walArchive:null`＋`db_unavailable`（只影響本區塊，`canTrigger`、`activeJob` 不變）；`failedCount>0` 且 `lastFailedAt` 晚於 `lastArchivedAt`（或前者為 null）時 UI 為警示色 |
| D-BK-T21 | `repos[].local` 的判定由匯出端負責（`local`＝端點主機不含 `.`、或為 `localhost`；TCS 加嚴：另含 `127.0.0.0/8`、`::1`（含帶括號的 `[::1]:9000`，去括號與埠後為 `::1`）、`host.docker.internal`——這些位址只可能指向同一台主機，不加嚴會把本機儲存呈現成「外部 S3」，與 PRD Q8 的目的相反；可推翻，推翻時把 AT-BK-02-6-1 的三個回送端點期望改為 false 即可）；repo1（posix）恆 `local:true`；console-api 不重算 |
| D-BK-T22 | 被拒的 POST（401、403、409、422）的審計列只鎖 `method`、`path`、`http_status`、`subject`、`role`；`entity_type` 不鎖（`AuditLoggingFilter` 無標註時由路徑導出 `sysadmin`，用例若先標註則為 `backup`） |
| D-BK-T23 | `docker/README.md` 〈4.3〉的 UI 指令常數：還原三步兩種形態都須逐字存在於該節 code block；核對三項只有 bash 形態逐字存在於 README（PowerShell 形態在 README 是一句前後綴說明，沒有指令行），故 UI 對核對三項只呈現 bash 形態並以一句話說明 PowerShell 的前後綴，不另造 README 沒有的指令行（避免 AC-BK-08-1 的單向鎖紅燈） |
| D-BK-T24 | 本機限定的閘：promtool 單元測試（CI 無 promtool 步驟，PRD M4）；真機 AT（V 系列）；`BackupSidecarContractIT` 與全部 IT 需 Docker（CI 的 backend job 已有 runner 內建 Docker） |

**追溯矩陣**：F-BK（系統管理／資料庫備份）← PRD FR-BK-01～10（§5 的 53 條 AC）、§1～§4、§6～§11、§13（掌舵者裁決 Q1～Q8 與 D-BK-1～D-BK-13）；US-BK-01～10 → AC-BK-01-1～10-5 加 AC-BK-04-6（TCS 增量）→ AT（本檔 §1）；R-BK-01～R-BK-62 → AC（R 條文表的 AT 欄）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；FSM 鍵 `agentconsole-sysadmin-backup`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.4 全文（三審 R-01～R-15、N-01～N-05、RS-1～RS-4 已結；掌舵者裁決 Q1～Q8 全採建議值，PRD §13）；Stage-1 於本鍵凍結（commit `000a217b`） | docs/01_requirements/Console_SysAdmin_Backup_PRD.md | sha256:848c2acfae30d3034205d647effd5000189c776f29db743629d4a4bdb1d0800a（含勘誤一；Stage-1 值 f61fd7cb…cd7287） |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-BK ＝ FR-BK-01～10（PRD §5）；本檔 FRD-lite 的 US-BK-01～10 與 §1 | 同 L135 | 同 L135 |
| SCG-0／NFR 已量化定義 | PRD §6（≤500 ms、觸發到 RUNNING ≤10 秒、單工與逾時、跨平台、零侵入面）與 AC-BK-05-2／05-4、06-11（心跳 30 秒、匯出 180 秒、輪詢預算）；本檔 §6.2 | 同 L135 | 同 L135 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-BK-01～10（本檔〈User Story INVEST 自檢〉表與其註） | 同 L135 | 同 L135 |
| SCG-0／利害關係人已確認簽核 | PRD 檔頭立案（掌舵者原話）、掌舵者裁決（PRD §13，互動選項「全部採建議值」）、主控代決 D-BK-1～D-BK-13；凍結依常態規則由主控執行，掌舵者可隨時以 T1 推翻 | 同 L135 | 同 L135 |
| SCG-0／RTM 初版已建立 | 本檔 §1 與 §6；Console 側 RTM 回填 `AgentConsole/docs/06_quality/RTM.md` 新增子表（開發棒交 rtm_backfill 檔、由主控回填） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（功能級增量；設計載於 PRD §1～§9）；最近依據 PRD §4（現況事實）、§8（資料模型與介面契約） | 同 L135 | 同 L135 |
| SCG-1／API Spec 草稿完成 | PRD §8.2（控制面檔案協定 v1）、§8.3（端點）；細則＝本檔 §C1～§C4，契約檔 `AgentConsole/docs/02_architecture/API_Contract_SysAdminBackup.md` 由 K 包依 §C 產出 | 同 L135 | 同 L135 |
| SCG-1／資料模型設計完成 | PRD §8.1（`console.backup_jobs`）、§8.2（檔案協定）；本檔 R-BK-55、§C1、§C5 | 同 L135 | 同 L135 |
| SCG-1／NFR 設計對應完成 | PRD §6 對應本檔 R-BK-24、26、32、34、39、51、58、62（心跳、新鮮度、單工、TTL、輪詢預算、不阻塞、不洩漏機密、跨平台與腳本品質） | 同 L135 | 同 L135 |
| SCG-1／整合架構說明完整 | 無第三方服務；依賴＝pgBackRest（`info`）、MinIO／S3（`mc`）、PostgreSQL（`pg_stat_archiver`、`console.backup_jobs`）、既有元件（`PillTabs`、`Dialog`、`Button`、`formatDateTime`）；PRD §9.1～§9.2、§12 | 同 L135 | 同 L135 |
| SCG-2／C4 Context 圖完成 | PRD §1、§4～§9（掌舵者→Console→sidecar 控制面→pgBackRest／MinIO；console-api 與 sidecar 間只有兩個具名卷）；不新增系統邊界 | 同 L135 | 同 L135 |
| SCG-2／C4 Container 圖完成 | PRD §9.4 模組落點表（`AgentConsole/backend`、`frontend`、`docker/pgbackrest`、`docker/prometheus`）；本檔 §5.7 允許變更集合 | 同 L135 | 同 L135 |
| SCG-2／所有架構決策有對應 ADR | ADR-BK-1（控制面載具＝B′ 兩具名卷）寫於 PRD §9.1（PRD 檔頭聲明「不另寫 ADR」）；本檔無新架構決策（D-BK-T 皆為 TCS 層定案） | 同 L135 | 同 L135 |
| SCG-2／Trust Boundary Map 完成 | PRD §6 STRIDE 精簡與 §9.1 比較表：無新埠、方向由 mount 層強制、請求只認封閉詞彙、無 docker socket、console-api 不持有 cipher 與 S3 金鑰；本檔 R-BK-35、47、52、58 | 同 L135 | 同 L135 |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈Before／After〉；PRD §9.4 | 同 L135 | 同 L135 |
| SCG-3／OpenAPI 3.1 規格完整 | 本檔 §C3（四個端點）；機器可讀版由 backend `/v3/api-docs` 與 `schema.d.ts` 鎖住（`OpenApiIT` 75／86→77／89） | （本檔 §C0～C6；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／Request／Response Schema 定義完整 | 本檔 §C1（控制面檔案）、§C3（欄位表、鍵序、null 語意）、§C5 | （本檔 §C0～C6；自引） | n/a（自引） |
| SCG-3／錯誤碼定義 | 本檔 §C3.4 驗證序與狀態碼表、§C4（backup 類 reason 表） | （本檔 §C0～C6；自引） | n/a（自引） |
| SCG-3／Consumer Contract 完成 | 消費者＝前端 `/sysadmin/backup`、掌舵者（真機 V 系列）；假 runner（K 包）與 sidecar 契約測試（S 包）即協定兩端的對拍（§C1）；PRD §8.2、§8.3 | 同 L135 | 同 L135 |
| SCG-3／API ID 與 RTM 已對應 | API-BK-01～04（本檔 §C3）↔ AC-BK-02～05、06-1～06-11、07-1～07-3、10-2、10-3、10-5；AT 到 RTM 見本檔 §1 與 §6 | 同 L135 | 同 L135 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（審查報告）；本檔起草後的獨立審查結果於凍結前併入正文 | 同 L135 | 同 L135 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值；PRD 的值是 Stage-1 凍結的 digest（`f61fd7cb…cd7287`；60,936 bytes），2026-10-27 以 SHA-256 重算一致，查證基準 commit `000a217b8b35095976d04b031254a4fe133f6675`。與該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 不符時以 `show` 為準並更正本表。

### R 條文（把 PRD §5～§9 逐條化；每條可判定）

「突變」欄格式為「位置 ⇒ 轉紅的 AT」：會使所列 AT 轉紅的最小改動（在 `git archive` 副本上套用，見 §2〈突變規格〉；生產碼尚未存在，位置以「檔案或類別＋構件」表示）。「AT」欄為 AC 簡碼（`04-3`＝`AT-BK-04-3-*` 全部）。「階」見 PRD §11。

#### A 導覽與骨架（PRD §5 FR-BK-01、§7；`registry.ts`、`/sysadmin`）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-01 | 一 | 導覽登記表恰九項：`sysadmin` 加在陣列**末尾**（index 8；label「系統管理」、href `/sysadmin`、order 65、mobile false、enabled true、roles 缺、icon `Database`）；原八列各欄與陣列位置不變（self-improving 仍 `[6]`、issues 仍 `[7]`）；顯示序為 settings 60、sysadmin 65、self-improving 70；九個 order 唯一、九個 icon 互異 | `registry.ts`：把 sysadmin 列插到 `[6]` ⇒ AT-BK-01-1-1、AT-BK-01-1-E-1 轉紅；加了 sysadmin 列卻不同步既有三支導覽測試 ⇒ AT-BK-01-1-2 轉紅；order 65 改 55 ⇒ AT-BK-01-1-1（order 唯一與顯示序）轉紅；icon 換成 `DatabaseBackup` ⇒ AT-BK-01-1-1（`icon === Database`）轉紅；mobile 改 true ⇒ AT-BK-01-3-E-1 轉紅 | 01-1、01-3 |
| R-BK-02 | 一 | `/sysadmin` 為入口頁（`app/sysadmin/page.tsx` 只殼）：一張「資料庫備份」入口卡（一句說明＋最近全備狀態摘要），連到 `/sysadmin/backup`；任一角色可見；導覽 active 為「系統管理」；未登入不呼叫備份 API、不顯示備份資料（沿既有登入閘，不新增第二套）；摘要取不到顯示「—」並帶原因，不顯示成功或 0 | `SysAdminHome.tsx`：把 failed 摘要渲染成「成功」⇒ AT-BK-01-2-3 轉紅；`cards` 為 null 時顯示 0 ⇒ AT-BK-01-2-3 轉紅；移除 `useEnabled` 閘（未登入也請求）⇒ AT-BK-01-2-E-1 轉紅；卡片 href 改 `/sysadmin` ⇒ AT-BK-01-2-1 轉紅；`match` 漏掉 `/sysadmin/backup` 子路徑 ⇒ AT-BK-01-2-2、AT-BK-01-2-E-2（導覽 active）轉紅；新增路由而未登記每頁說明（條件列成立時）⇒ AT-BK-01-2-4 轉紅 | 01-2 |
| R-BK-03 | 一 | 「系統管理」在 <768 的底部 Tab 不顯示（`mobile:false` 對映 `max-md:hidden`，DOM 內仍在）；`ToolsRegion.tsx` 不改（登記表驅動）；`mobile` 為 true 的項數仍 6 | `ToolsRegion.tsx`：改成不帶 `max-md:hidden` 判準（或登記表 mobile 改 true）⇒ AT-BK-01-3-1、AT-BK-01-3-E-1 轉紅 | 01-3 |

#### B 備份清單（PRD §5 FR-BK-02；`BackupQueryService`、`BackupList`、匯出端 `repos`）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-04 | 一 | `backups[]` 由 `info.json` 的每份備份與 `logical.json` 的每個物件合併，依 `finishedAt` 新到舊（同值依 label 字典序降冪）；每筆鍵齊：kind（full、diff、incr、logical）、label、location（repo1、repo2、logical）、startedAt、finishedAt、durationSeconds（stop−start）、databaseSizeBytes（`info.size`）、repoSizeBytes（`info.repository.size`）、baseLabel（差異＝`prior`，其餘 null）、result；時間為 UTC `Z`；前端依 API 序渲染、表頭十欄固定序 | `BackupQueryService`：合併後不排序 ⇒ AT-BK-02-1-1、AT-BK-02-1-E-1 轉紅；`durationSeconds` 改 `start−stop` 或改用 `backup.timestamp.start` 當結束 ⇒ AT-BK-02-1-1 轉紅；kind 把 incr 歸成 diff ⇒ AT-BK-02-1-E-1 轉紅；`BackupList.tsx` 自行重排 ⇒ AT-BK-02-1-2 轉紅 | 02-1 |
| R-BK-05 | 一 | `info` 的 `error:true`（頁校驗錯誤）⇒ `result=ok_with_errors`，UI 文字「成功，但有校驗錯誤」並 `data-tone=warn`；缺 `error` 鍵＝`ok`；清單只含成功建立的備份，頁面恆有一行「失敗的工作看狀態卡與工作紀錄」 | `BackupQueryService`：忽略 `error` ⇒ AT-BK-02-2-1 轉紅；UI 對 `ok_with_errors` 顯示「成功」⇒ AT-BK-02-2-2 轉紅；只在有錯誤時才渲染說明行 ⇒ AT-BK-02-2-E-1 轉紅 | 02-2 |
| R-BK-06 | 一 | 格式化沿用既有函式：時間 `formatDateTime`（`lib/format.ts:27-30`，瀏覽器本機時區）、`formatClock`、`formatBytes`、`formatDuration`（`lib/domain/metrics.ts:87`）；缺值「—」；分頁標題旁註排程時區；新檔不得自定同名函式 | `BackupList.tsx`：內嵌自寫的 `toLocaleString`／`formatBytes` ⇒ AT-BK-02-3-1（與既有函式輸出逐字比對）、AT-BK-02-3-2 轉紅；null 顯示「0 B」⇒ AT-BK-02-3-E-1 轉紅 | 02-3 |
| R-BK-07 | 一 | `repos[]`＝`{repo, endpointHost, local, statusCode, statusMessage}`；某 repo `status.code≠0` ⇒ 該 repo 區塊頂列顯示狀態碼與中文說明（`REPO_STATUS_ZH`，鍵 {0,1,2,3,4,5,6,99}，未知碼退回含數字的「其他」），另一 repo 照常；不把 repo 異常顯示成「沒有備份」；該 repo 沒有備份時不補佔位列 | `BackupQueryService`：repo 異常時整個 `backups` 回空 ⇒ AT-BK-02-4-1 轉紅；`BackupList.tsx` 把 `statusCode≠0` 的 repo 顯示為空表 ⇒ AT-BK-02-4-2 轉紅；`REPO_STATUS_ZH` 缺 99 或對未知碼丟例外 ⇒ AT-BK-02-4-E-1 轉紅 | 02-4 |
| R-BK-08 | 一 | 完全沒有備份是合法空狀態：`backups=[]`、四張卡 `no_run`（`never=true`、`overdue=false`），UI 顯示「尚無備份：首次部署後請立刻做第一份全備」；不顯示 0；`info` 為空陣列（無 stanza）時 `repos=[]`、`schedule.retention=null` 並帶 `retention_unavailable` | `BackupQueryService`：空備份時回 `control.reason=export_unreadable` ⇒ AT-BK-02-5-1 轉紅；UI 空狀態文字少「首次部署後請立刻做第一份全備」⇒ AT-BK-02-5-2 轉紅；無 stanza 時 retention 填預設 4／7 ⇒ AT-BK-02-5-E-1 轉紅 | 02-5 |
| R-BK-09 | 一 | `repos[].local` 的唯一判定者是匯出端 `backup-ctl-export.sh`：repo1 posix ⇒ `local:true`、`endpoint_host:null`；repo2 s3 ⇒ 取 `OFFSITE_S3_ENDPOINT` 去埠號的主機名，**不含 `.` 或為 `localhost`（TCS 加嚴：另含回送位址 127.0.0.0/8、`::1`、`host.docker.internal`）⇒ `local:true`**，其餘 false；console-api 逐值透傳、缺鍵或非布林＝`schema_mismatch`；UI：true ⇒「本機 MinIO・與主機同碟，主機損毀時一併消失」、false ⇒「外部 S3」，`local:true` 時任何處不得稱「離站已安全」且 dump 卡同樣標「與主機同碟」 | `backup-ctl-export.sh`：判準改為「含 `.` 才算本機」⇒ AT-BK-02-6-1 轉紅；漏掉 `127.0.0.1` ⇒ AT-BK-02-6-1 轉紅；`BackupQueryService` 對缺 `local` 預設 false ⇒ AT-BK-02-6-E-1 轉紅；UI 對 local:true 顯示「外部 S3」或在 dump 卡省略同碟標示 ⇒ AT-BK-02-6-2 轉紅 | 02-6 |

#### C 排程與保留（PRD §5 FR-BK-03；`humanizeCron`、`BackupCron.next`、`retention`）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-10 | 一 | `humanizeCron` 只認三式 `m h * * d`（d＝0～6）、`m h * * a-b`（0≤a<b≤6）、`m h * * *`：回「每週<星期> HH:MM」「每週<a>至週<b> HH:MM」「每日 HH:MM」（0 日、1 一…6 六，時分補零）；`schedule` 區列「<白話>・<工作名>」六列加固定列「WAL 持續歸檔（有寫入時約每 60 秒一段）」；工作名：全備、增備（差異）、離站 pg_dump、驗證、清理過期備份（維護工作）、清理 WAL 複本（維護工作）；每列另附原 cron 與時區 | `sysadminBackup.ts`：星期對照 0 與 6 互換 ⇒ AT-BK-03-1-2 轉紅；對缺少的 expire、wal_clean 補出佔位列 ⇒ AT-BK-03-1-E-1 轉紅；漏掉固定 WAL 列 ⇒ AT-BK-03-1-1 轉紅；expire 工作名少「（維護工作）」⇒ AT-BK-03-1-1 轉紅；範圍式 `1-6` 誤判為不認得 ⇒ AT-BK-03-1-2 轉紅 | 03-1 |
| R-BK-11 | 一 | 不認得的 cron 一律原字串回傳（不 trim、不猜、不丟例外）；星期欄 7、列表式、名稱式、步進式、欄數不是五、數值越界、反向範圍皆屬不認得 | `humanizeCron`：對 `0 2 * * 1,3` 回猜測白話 ⇒ AT-BK-03-2-1 轉紅；對空字串丟例外 ⇒ AT-BK-03-2-1 轉紅；把 `7` 當週日 ⇒ AT-BK-03-2-1（`0 2 * * 7`）轉紅；元件在不認得時 `console.error` ⇒ AT-BK-03-2-E-1 轉紅 | 03-2 |
| R-BK-12 | 一 | `nextRunAt` 由 console-api 以 `schedule.json.tz` 計算（`application/service/BackupCron.next`，Spring `CronExpression`，前補秒欄 `0 `；Spring 相依不得進 domain，ArchUnit A1），回傳 UTC `Z`；嚴格晚於 now；星期欄 0 為週日；不依 JVM 預設時區；cron 無法解析 ⇒ 該條 `nextRunAt:null` 加 `cron_unparsable:<job>`；時區不合法 ⇒ `reason=schema_mismatch`（整區 null，D-BK-T5） | `BackupCron.next`：改用 `ZoneId.systemDefault()` ⇒ AT-BK-03-3-2（JVM 時區改變後值不變）轉紅；`next` 改為「≥ now」⇒ AT-BK-03-3-1（now＝觸發時刻那列）轉紅；不前補秒欄 ⇒ AT-BK-03-3-1 轉紅（Spring 要 6 欄）；無法解析的 cron 丟 500 ⇒ AT-BK-03-3-E-1 轉紅；`BackupSeam` 改以 `@Primary Clock` 換全域時鐘 ⇒ AT-BK-03-3-2（全域 `Clock` 不被換）轉紅 | 03-3 |
| R-BK-13 | 一 | `retention` 由匯出端取 pgBackRest 自報有效值（`help expire repo-retention-full`／`-diff` 的 `current:`；單值套用全部 repo、逐 repo 列各取各的）加 `LOGICAL_BACKUP_RETENTION_DAYS`；格式 `{repo1:{full,diff},repo2:{full,diff},logical_days}`，欄內 null＝該設定未設；整體解析不到＝`retention:null`（不填預設）；console-api 轉 `schedule.retention`（camelCase），null 加 `retention_unavailable`；UI 唯讀顯示「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」，null ⇒「—」 | `backup-ctl-export.sh`：解析失敗時填 4／7 預設 ⇒ AT-BK-03-4-2、AT-BK-03-4-E-1 轉紅；改讀 `pgbackrest.conf` 而非自報值 ⇒ AT-BK-03-4-1（換 conf 值匯出值不變）轉紅；單值形態只套 repo1 ⇒ AT-BK-03-4-1 轉紅；UI 對 repo2.diff＝null 顯示「差異 0」⇒ AT-BK-03-4-3 轉紅 | 03-4 |
| R-BK-14 | 一 | 保留與排程沒有任何可寫面：`BackupController` 只有一個 `@PostMapping`（階段二，觸發工作）與 GET；沒有 PUT、PATCH、DELETE 對映；`/api/v1/sysadmin/**` 的非 GET、非 POST 方法無 2xx；「排程與保留」分頁無輸入元件與編輯類按鈕、不發任何寫入請求；OpenAPI 的 sysadmin 路徑無 put、patch、delete | `BackupController`：加 `@PutMapping("/retention")` ⇒ AT-BK-10-3-E-2（映射掃描）、AT-BK-10-3-E-1（HTTP 層回 2xx）、AT-BK-10-5-E-1（OpenAPI 出現 put）轉紅；`BackupSchedule.tsx` 加 `<input>` ⇒ AT-BK-03-4-E-2 轉紅 | 03-4、10-3、10-5 |

#### D 最近狀態卡（PRD §5 FR-BK-04；`BackupOverdue`、`cards`、Q7 `walArchive`）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-15 | 一 | `cards[4]` 恆依序 full、diff、dump、verify；`status` ∈ {succeeded、failed、running、interrupted、no_run}（UI「成功／失敗／進行中／中斷／從未執行」，文字加 Lucide 圖示）；欄位：trigger（scheduled、manual、null）、startedAt、finishedAt、durationSeconds、lastSuccessAt、lastDueAt、overdue、never、reason、`latestBackup`（僅 full、diff 卡；`{label, finishedAt, source:"pgbackrest"}`，full 取全備、diff 取差異或全備中最近者）；無狀態檔但清單有備份 ⇒ `status=no_run`、`never=false`、顯示最近一份備份與來源（F-04），不得只顯示「從未執行」 | `BackupQueryService`：cards 依檔名字母序輸出 ⇒ AT-BK-04-1-1 轉紅；dump 卡也帶 `latestBackup` ⇒ AT-BK-04-1-1 轉紅；無 `jobs/full.json` 時略過 `latestBackup` ⇒ AT-BK-04-1-E-1 轉紅；徽章只靠顏色不放圖示 ⇒ AT-BK-04-1-2 轉紅；`BackupStatusCards.tsx` 使用 `dangerouslySetInnerHTML` ⇒ AT-BK-04-1-E-2 轉紅 | 04-1 |
| R-BK-16 | 一 | 最近一次失敗而更早有成功：卡為失敗色（`data-tone=danger`）並顯示「最近一次成功：<時間>」，從未成功顯示「最近一次成功：從未成功」；失敗不覆蓋 `lastSuccessAt`；輸出尾段只對 ADMIN 顯示 | `job-run.sh`：失敗時把 `last_success_at` 清空或覆寫成失敗時間 ⇒ AT-BK-09-3-3、AT-BK-09-3-4（`last_success_at` 保持原值）轉紅；UI 對非 ADMIN 也渲染 `bk-tail-*` ⇒ AT-BK-04-2-2 轉紅；從未成功顯示「—」⇒ AT-BK-04-2-E-1 轉紅；`BackupQueryService` 把 failed 卡的 `lastSuccessAt` 取成 `finishedAt` ⇒ AT-BK-04-2-1 轉紅 | 04-2 |
| R-BK-17 | 一 | `lastDueAt`（`BackupCron.lastDue`）：cron 在 now 之前（含）最近一次應跑時刻；以該 cron 時區自 `now − 8 天` 起逐次呼叫 `next`、取最後一個 ≤ now 者；週期工作的 `lastDueAt` 因此落在 7 天內；增備（週一至週六）在週日沒有時段 ⇒ 週日的 `lastDueAt` 為週六 02:00 | `BackupCron.lastDue` 內呼叫 `Instant.now()` ⇒ AT-BK-04-3-E-2 轉紅；`BackupCron.lastDue`：回溯起點改為 `now − 1 天` ⇒ AT-BK-04-3-1（O2、O14、O20 列：`lastDueAt` 在一天以前）轉紅；取第一個而非最後一個 ≤ now 者 ⇒ AT-BK-04-3-1 轉紅；`≤ now` 改 `< now` ⇒ AT-BK-04-3-1（now＝觸發時刻那列）轉紅；使用 `ZoneId.systemDefault()` ⇒ AT-BK-04-3-E-2（掃描）轉紅 | 04-3 |
| R-BK-18 | 一 | `overdue`（`BackupOverdue.evaluate`）：`now > lastDueAt + 寬限`（寬限＝`overdue-grace-minutes`＝30 分；嚴格大於）且成功時間早於 `lastDueAt` 且該工作未進行中；從未成功（狀態檔與清單皆無）⇒ `never=true`、`overdue=false`；算不出（cron 無法解析）⇒ `overdue=false`、`lastDueAt=null`；前端只顯示 `card.overdue`、不重算（無 cron 函式庫、無 grace 識別字） | `BackupOverdue`：`>` 改 `>=` ⇒ AT-BK-04-3-1（`+30 分整` 列）轉紅；寬限改 25 或 35 分 ⇒ AT-BK-04-3-1（週一 02:31 與寬限邊界列）轉紅；略過 running 判斷 ⇒ AT-BK-04-3-1（running 列）與 AT-BK-04-3-2 轉紅；從未成功時回 `overdue=true` ⇒ AT-BK-04-3-1（never 列）轉紅；`BackupStatusCards.tsx` 引入 `cron-parser` 重算 ⇒ AT-BK-04-3-3 轉紅；cron 無法解析時回 `overdue=true` ⇒ AT-BK-04-3-E-1 轉紅 | 04-3 |
| R-BK-19 | 一 | full、diff 卡的「最近成功時間」＝狀態檔 `last_success_at` 與清單端的**較新者**；清單端＝各 repo 最近一份符合者（full 卡＝full；diff 卡＝diff 或 full）的 `timestamp.stop` 之**最舊者**（TCS D-BK-T10：任一已設定 repo 沒有符合的備份 ⇒ 清單端缺席）；dump、verify 卡只取狀態檔 | `BackupOverdue`：清單端改取各 repo 最近者的**最新者**（`max`）⇒ AT-BK-04-3-1（O12 一新一舊列）轉紅；清單端忽略某 repo 無備份而只取有備份者 ⇒ AT-BK-04-3-1（O13 列）轉紅；只看狀態檔不看清單 ⇒ AT-BK-04-1-E-1、AT-BK-04-3-1（O11、O14 列）轉紅 | 04-1、04-3 |
| R-BK-20 | 一 | 「中斷」：`backup-ctl-export.sh` 每輪匯出前清掃——`jobs/<job>.json` 的 `last.status=running`，或 `results/<id>.json` 的 `status=running` 且 `started_at`（撿起時刻，R-BK-46）距今逾 6×`BACKUP_CTL_POLL_SECONDS`（預設 30 秒；避開剛撿起、尚未取鎖的視窗），而維護鎖無持有者 ⇒ 改寫 `interrupted`（jobs：`reason=interrupted`、補 `finished_at`、保留 `last_success_at`；results：`failed`／`interrupted`）；console-api 防禦性導出：`running` 且心跳新鮮、心跳 `ts` ≥ 該工作 `last.started_at`（心跳早於工作開始＝鎖資訊過時，不下結論）且 `lock_held=false` ⇒ `interrupted`；心跳過期時不下結論（保持 running＋`runner_offline`） | `backup-ctl-export.sh`：不清掃 ⇒ AT-BK-04-4-1 轉紅；清掃時不檢查鎖持有者（一律改 interrupted）⇒ AT-BK-09-6-3（diff 保持 running）轉紅；`BackupQueryService` 在心跳過期時也導出 interrupted ⇒ AT-BK-04-4-E-1（b 列）轉紅；`lock_held=true` 仍導出 interrupted ⇒ AT-BK-04-4-E-1（a 列）轉紅；`BackupQueryService` 完全不做防禦性導出 ⇒ AT-BK-04-4-2 轉紅；清掃只看 jobs、不認 results ⇒ AT-BK-09-6-5 轉紅；清掃不設寬限 ⇒ AT-BK-09-6-5（5 秒列）轉紅；runner 寫 running 標記時 `started_at` 為 null ⇒ AT-BK-09-1-1 轉紅（真孤兒永不清）；`BackupQueryService` 不比對心跳 `ts` 與 `started_at` ⇒ AT-BK-04-4-E-1（d 列）轉紅 | 04-4、09-6 |
| R-BK-21 | 一 | 非 ADMIN 的 `GET /backups`、`GET /backups/jobs`、`GET /backups/jobs/{id}`：`cards[].detailTail`、`cards[].requestedBy`、`activeJob.requestedBy`、`items[].requestedBy`、`items[].detail` 為 null 或缺席；ADMIN 才有，且已遮罩、尾段 ≤2000 字元；以遞迴掃描的 JSON 測試驗證 | `BackupQueryService`／DTO：不分角色一律序列化 `detailTail` ⇒ AT-BK-04-5-1 轉紅；`requestedBy` 只在 cards 遮、`activeJob` 漏遮 ⇒ AT-BK-04-5-3 轉紅；`/jobs` 清單漏遮 `detail` ⇒ AT-BK-04-5-E-1 轉紅；ADMIN 尾段超過 2000 ⇒ AT-BK-04-5-2 轉紅 | 04-5、07-2 |
| R-BK-22 | 一 | （TCS 補列，Q7）`walArchive`＝`{lastArchivedAt, failedCount, lastFailedAt}`，由 `WalArchiveStatsAdapter` 以**一條唯讀 SELECT** 讀 `pg_stat_archiver`（console-api 既有連線）；讀取失敗 ⇒ `walArchive:null` 並加 `db_unavailable`（不當 0、不丟 500、與 `backup_jobs` 讀取互相獨立降級；`canTrigger`、`activeJob` 不受影響）；真實的零（全新叢集）仍為物件；UI 單行唯讀：「WAL 歸檔：最近 <時間>・失敗 N 次」，`failedCount>0` 且 `lastFailedAt` 晚於 `lastArchivedAt` ⇒ 警示色；null ⇒「WAL 歸檔：—」 | `WalArchiveStatsAdapter`：例外時回 `{failedCount:0,…}` ⇒ AT-BK-04-6-2（經真實 adapter）轉紅；把真實零回成 null ⇒ AT-BK-04-6-1 轉紅；加第二條敘述或改成 UPDATE ⇒ AT-BK-04-6-E-1 轉紅；UI 對 null 顯示「失敗 0 次」⇒ AT-BK-04-6-3 轉紅；DB 讀取失敗連帶讓整個概覽失敗 ⇒ AT-BK-05-5-E-1 轉紅；walArchive 失敗連帶 `canTrigger=false` ⇒ AT-BK-04-6-2 轉紅 | 04-6、05-5 |

#### E 控制面健康與資料新鮮度（PRD §5 FR-BK-05；fail-loud）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-23 | 一 | `console.backup.export-dir` 未設 ⇒ `GET /backups` 回 200 與 `control={available:false,canTrigger:false,reason:not_configured,…}`，所有資料區塊（cards、backups、schedule、repos、walArchive、activeJob、timezone）為 null；UI 整頁只顯示「備份控制面未設定（不在 Docker 全棧）」；GET 只依 `export-dir`、POST 另依 `request-dir`；POST 於未設定時 503 `backup_control_unavailable` | `BackupQueryService`：未設定時回空陣列而非 null ⇒ AT-BK-05-1-1 轉紅；未設定時回 500 ⇒ AT-BK-05-1-1 轉紅；POST 在 `request-dir` 未設時仍建列 ⇒ AT-BK-05-1-E-1、AT-BK-05-1-2 轉紅；UI 在 null 區塊時顯示「0 份」⇒ AT-BK-05-1-3 轉紅 | 05-1 |
| R-BK-24 | 一 | 心跳判斷：`heartbeat` 缺席或 `now − ts > 30 秒` ⇒ `reason=runner_offline`（嚴格大於；30 秒整仍正常）、`canTrigger=false`、資料區塊照回已知資料（非 null）；UI 紅橫幅（`role="alert"`）「備份控制面無回應（上次心跳 N 秒前／尚未收到心跳）」＋「可能已過期」標記；進行中的工作不是豁免；POST 503 | `BackupQueryService`：門檻 30 改 60 ⇒ AT-BK-05-2-1（31 秒列）轉紅；`>` 改 `>=` ⇒ AT-BK-05-2-1（30 秒列）轉紅；offline 時把區塊設 null ⇒ AT-BK-05-2-1 轉紅；有進行中工作時略過離線判斷 ⇒ AT-BK-05-2-E-1、AT-BK-09-8-3 轉紅；橫幅缺 `role=alert` ⇒ AT-BK-05-2-2 轉紅；offline 時 POST 仍建列 ⇒ AT-BK-05-2-3 轉紅 | 05-2 |
| R-BK-25 | 一 | 匯出檔守門：任一必讀檔（info、logical、schedule、jobs 四檔、heartbeat）`schema_rev` 不是整數 1（含字串 "1"、缺鍵、頂層型別不對）⇒ `reason=schema_mismatch`；JSON 損毀或空檔 ⇒ `reason=export_unreadable`；兩者並存 `schema_mismatch` 優先；一旦有 reason，所有資料區塊為 null（整區顯示原因，不顯示部分資料、不當成 0 件）；`ok:false`（匯出行程自報失敗而檔案本身合法）⇒ 該來源的衍生區塊缺席並加 `info_unavailable`／`logical_unavailable`、其餘照常（`reason` 仍 null），UI 以提示條說明缺的來源 | `BackupQueryService`：`schema_rev` 用寬鬆比對（接受 "1"）⇒ AT-BK-05-3-1 轉紅；損毀時回部分資料 ⇒ AT-BK-05-3-1 轉紅；兩類並存時回 export_unreadable ⇒ AT-BK-05-3-E-2(a)(a2) 轉紅；讀到第一個問題就回傳（不掃完必讀檔）⇒ AT-BK-05-3-E-2(a)(a2) 轉紅；heartbeat 不驗 `schema_rev` ⇒ AT-BK-05-3-1（第九項）轉紅；`ok:false` 時當成損毀而整區 null ⇒ AT-BK-05-3-E-1 轉紅；UI 對 reason 顯示「尚無備份」⇒ AT-BK-05-3-2 轉紅 | 05-3 |
| R-BK-26 | 一 | 資料新鮮度：`control.exportAgeSeconds = now − info.generated_at`、`control.exportGeneratedAt`（TCS 補欄，ISO `Z`）；UI 顯示「資料更新於 hh:mm:ss」（`formatClock`），`exportAgeSeconds > 180` ⇒ 加「已過期」（180 整不加）；匯出舊不改變 `reason` | `BackupView.tsx`：門檻 180 改 120 ⇒ AT-BK-05-4-2（180 列）轉紅；`exportAgeSeconds` 為 null 時顯示「已過期」⇒ AT-BK-05-4-E-1 轉紅；`>` 改 `>=` ⇒ AT-BK-05-4-2（180 列）轉紅；`BackupQueryService` 把 `generated_at` 取成 `logical.json` 的 ⇒ AT-BK-05-4-1 轉紅；匯出舊時設 `reason` ⇒ AT-BK-05-4-1 轉紅 | 05-4 |
| R-BK-27 | 二 | 資料庫讀取失敗（`backup_jobs` 讀取丟 `DataAccessException`）⇒ 概覽仍 200，`warnings` 含 `db_unavailable`，`activeJob` 只取自匯出鎖狀態（`{type, status:RUNNING, trigger, id:null}`）、`canTrigger=false`；POST 503 `backup_control_unavailable`；`walArchive` 與 `backup_jobs` 兩個 DB 讀取獨立降級 | `BackupQueryService`：DB 例外外洩成 500 ⇒ AT-BK-05-5-1 轉紅；DB 失敗時 `activeJob` 回舊快取 ⇒ AT-BK-05-5-1 轉紅；POST 在 DB 失敗時仍寫請求檔 ⇒ AT-BK-05-5-1 轉紅；兩個 DB 讀取共用一個 try ⇒ AT-BK-05-5-E-1 轉紅 | 05-5 |
| R-BK-28 | 一 | `control.reason` 值域與優先序：`not_configured`（export-dir 未設）＞`schema_mismatch`＞`export_unreadable`＞`runner_offline`；前三者資料區塊全 null，`runner_offline` 資料照回；`warnings` 值域封閉：`db_unavailable`、`retention_unavailable`、`info_unavailable`、`logical_unavailable`、`cron_unparsable:<job>` | `BackupQueryService`：把 `runner_offline` 排在 `export_unreadable` 之前 ⇒ AT-BK-05-3-E-2(b) 轉紅；把 `not_configured` 排在 `schema_mismatch` 之後 ⇒ AT-BK-05-1-E-2 轉紅；warnings 出現契約表以外的值 ⇒ AT-BK-05-3-E-1、AT-BK-03-4-E-1 轉紅 | 05-1、05-2、05-3 |

#### F 手動觸發（PRD §5 FR-BK-06；皆階段二）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-29 | 二 | 確認對話框：顯示工作名稱、白話說明、上次耗時（`formatDuration`）與資料庫大小（`formatBytes`）、保留名額；`retentionQuota(type, repoBackups, retention)` 純函式：full ⇒ 各 repo 的全備份數 vs `retention.full`；diff ⇒ 各 repo 的（差異＋全備）合計 vs `retention.diff`；上限 null 的 repo 無項；`current ≥ limit` ⇒ `willExpire`、`oldestLabel`＝該 repo 最舊的同類備份（diff 為最舊差異）；verify 無名額、另提醒暫存空間；按「確認執行」才送 POST、取消與 Esc 零請求、處理中連點只送一次 | `retentionQuota`：diff 只算差異份數 ⇒ AT-BK-06-1-1（(c) 列）轉紅；`≥` 改 `>` ⇒ AT-BK-06-1-1（(a) 列）轉紅；上限 null 的 repo 仍輸出一項 ⇒ AT-BK-06-1-1(e)、AT-BK-06-1-2 轉紅；`BackupTriggerDialog.tsx` 在開啟時就送 POST ⇒ AT-BK-06-1-3 轉紅；移除連點防護 ⇒ AT-BK-06-1-E-1 轉紅 | 06-1 |
| R-BK-30 | 二 | POST 驗證序（TCS D-BK-T13）：401 → 403 → 本文須為 JSON 物件（否則 400 `MALFORMED_REQUEST_BODY`）→ `type` ∈ {full,diff,verify}（否則 422 `invalid_request`，`details.violations[]`）→ `confirm` 為 JSON 布林 true（否則 400 `backup_confirm_required`）→ 控制面可用（否則 503）→ 無進行中（否則 409）→ 頻率（否則 409）→ 建列；任一前序失敗零列、零檔；多餘鍵忽略；`dump`、`incr` 非法 | `BackupController`：以 `Boolean.parseBoolean` 接受字串 "true" ⇒ AT-BK-06-2-1（字串列）轉紅；type 與 confirm 的檢查序對調 ⇒ AT-BK-06-2-1（`{}` 列）轉紅；允許 `dump` ⇒ AT-BK-06-2-1 轉紅；驗證失敗仍先建列 ⇒ AT-BK-06-2-1（零列斷言）轉紅；把 body 的 `id` 當請求檔 id ⇒ AT-BK-06-2-E-1 轉紅 | 06-2 |
| R-BK-31 | 二 | 成功路徑：**先** `insertQueued` **後** `writeRequest`；202 `{id（UUID）, type, status:"QUEUED", requestedAt}`；`expires_at = requested_at + request-ttl-seconds（120）`；請求檔 `{schema_rev:1, id, type, requested_at, expires_at}`，`Files.move(…, ATOMIC_MOVE)` 自 `.tmp` 落地；對帳把 QUEUED→RUNNING→終態，終態後刪自己的請求檔；頁面顯示進行中橫幅（QUEUED→RUNNING→終態）並於終態後刷新總覽與清單 | `BackupJobService.trigger`：呼叫序改 `[writeRequest, insertQueued]` ⇒ AT-BK-06-3-1 轉紅；回 200 或 201 ⇒ AT-BK-06-3-E-1 轉紅；回 `status:"RUNNING"` ⇒ AT-BK-06-3-E-1 轉紅；終態後不刪請求檔 ⇒ AT-BK-06-3-3 轉紅；`expires_at` 用 60 秒 ⇒ AT-BK-06-3-2 轉紅；UI 終態後不重抓總覽 ⇒ AT-BK-06-3-4 轉紅 | 06-3 |
| R-BK-32 | 二 | 單工：已有 QUEUED 或 RUNNING ⇒ 409 `backup_job_in_progress`（零列、零檔）；兜底＝部分唯一索引 `ux_backup_jobs_one_active`，`insertQueued` 對唯一鍵衝突（SQLState 23505／`DuplicateKeyException`）轉為同一個 409（不是 500）；兩併發 POST 恰一個 202、一個 409 | `V15__backup_jobs.sql`：刪掉部分唯一索引 ⇒ AT-BK-06-4-2、AT-BK-06-4-3 轉紅；`BackupJobService` 不捕捉重複鍵 ⇒ AT-BK-06-4-E-1、AT-BK-06-4-2（出現 500）轉紅；進行中檢查只看 RUNNING、漏 QUEUED ⇒ AT-BK-06-4-1（QUEUED 列）轉紅；索引條件漏 QUEUED ⇒ AT-BK-06-4-3 轉紅；先查後插而不靠索引且不處理競態 ⇒ AT-BK-06-4-2 轉紅 | 06-4 |
| R-BK-33 | 二 | `busy`：手動請求遇排程工作持鎖（活的命令形 `flock -o` 持有者）⇒ `job-run.sh` 不等待、rc 75、runner 子行程把 results 寫成 `rejected`／`busy`；對帳為 `REJECTED`／`busy`；頁面顯示 `BACKUP_REASONS.busy`＝「排程工作執行中，稍後再試」；鎖檔存在但無持有者**不是** busy | `job-run.sh`：手動路徑改 `flock -w 7200`（等待）⇒ AT-BK-06-5-1、AT-BK-09-3-2 轉紅；以「鎖檔存在」判 busy ⇒ AT-BK-06-5-E-1 轉紅；對帳把 busy 標為 FAILED ⇒ AT-BK-06-5-2 轉紅；`BACKUP_REASONS.busy` 文字差一字 ⇒ AT-BK-06-5-3 轉紅 | 06-5、09-3 |
| R-BK-34 | 二 | 請求 TTL（120 秒）：runner 存活（心跳新鮮）⇒ 由 runner 對過期請求寫 `rejected`／`expired`，console-api 對帳為 `EXPIRED`（不自行標）；runner 離線（心跳過期）⇒ console-api 以 `UPDATE … WHERE status='QUEUED'` 標 `EXPIRED`（嚴格逾 120 秒），標後刪請求檔；**絕對上限**：不論心跳，QUEUED 逾 2×TTL（240 秒，嚴格大於）仍無 results 者同樣由 console-api 條件式標 `EXPIRED`（Q8 兜底：results 不可寫時 runner 不處理請求，否則該列永遠 QUEUED 而鎖死唯一索引）；與 runner 撿取交錯時只有一方生效；sidecar 日後恢復不執行過期或已有 results 的請求 | `BackupJobReconciler`：runner 存活時也自行標 EXPIRED ⇒ AT-BK-06-6-2 轉紅；離線過期 UPDATE 拿掉 `WHERE status='QUEUED'` ⇒ AT-BK-06-6-4 轉紅；離線過期門檻 120 秒改 90 秒 ⇒ AT-BK-06-6-3（t0＋119 秒列不得標）轉紅；`backup-ctl-runner.sh` 不檢查 `expires_at` ⇒ AT-BK-06-6-1 轉紅；恢復後重播已處理請求 ⇒ AT-BK-06-6-E-1、AT-BK-09-1-2 轉紅；移除 2×TTL 絕對上限 ⇒ AT-BK-06-6-5 轉紅 | 06-6 |
| R-BK-35 | 二 | RBAC：POST 僅 ADMIN（OPERATOR、VIEWER 403 `ACCESS_DENIED`，零列、零檔）；UI：非 ADMIN 三顆按鈕存在但 `disabled` 並旁註「需要 ADMIN 角色才能操作」、點擊不開對話框、網路層零寫入；role 未知（載入中）⇒ 失敗關閉（disabled）；ADMIN 且 `canTrigger=false` ⇒ disabled | `SecurityConfig`：刪掉 POST sysadmin 規則 ⇒ AT-BK-06-7-1、AT-BK-10-3-1 轉紅；UI 以 `role !== "VIEWER"` 判可用 ⇒ AT-BK-06-7-2（OPERATOR）轉紅；role 為 undefined 時可用 ⇒ AT-BK-06-7-E-1 轉紅；`canTrigger=false` 仍可按 ⇒ AT-BK-06-7-3 轉紅 | 06-7、10-3 |
| R-BK-36 | 二 | 終態對帳（`BackupJobReconciler.reconcileOnce`，排程輪詢加每次 GET 順帶，可並行）：只用 `UPDATE … WHERE id=? AND status IN ('QUEUED','RUNNING')`；**只有更新到列的那一次**於交易提交後以 `AuditTrail.system("backup.finished","backup",id,…)` 補審計；映射：succeeded→SUCCEEDED；failed→FAILED（reason 取 results 的，限 `script_failed`／`interrupted`／`lock_timeout`，詞彙外一律 `script_failed`）；rejected `busy`／`rejected_invalid`→REJECTED；rejected `expired`→EXPIRED；`timeout`＝RUNNING 逾 `job-max-seconds`（嚴格大於）**且**心跳過期；例外只記 WARN、排程不死 | `BackupJobAdapter`：UPDATE 去掉 `AND status IN (…)` ⇒ AT-BK-06-8-E-1（掃描）、AT-BK-06-8-2 轉紅；審計改為無條件補 ⇒ AT-BK-06-8-2（兩筆）轉紅；審計在交易提交前寫 ⇒ AT-BK-06-8-2 轉紅；rejected／expired 映射成 REJECTED ⇒ AT-BK-06-8-1(h) 轉紅；`timeout` 不看心跳 ⇒ AT-BK-06-8-3(b) 轉紅；`runOnceQuietly` 移除 try/catch ⇒ AT-BK-06-8-4 轉紅；詞彙外 reason 原樣寫入 ⇒ AT-BK-06-8-1(e) 轉紅 | 06-8 |
| R-BK-37 | 二 | 補償：`writeRequest` 失敗（IOException）⇒ 刪殘留 `.tmp`、該列以**條件式** UPDATE 補償為 FAILED（`control_write_failed`）、回 503 `backup_control_unavailable`；唯一索引釋放、可立即重試；已被別處改為 EXPIRED 的列不覆蓋 | `BackupJobService`：失敗時不補償（列留 QUEUED）⇒ AT-BK-06-9-1（再 POST 得 409）轉紅；補償改無條件 UPDATE ⇒ AT-BK-06-9-E-1 轉紅；`FileBackupControlAdapter` 失敗時不刪 `.tmp` ⇒ AT-BK-06-9-1、AT-BK-06-9-2 轉紅；寫檔失敗回 500 ⇒ AT-BK-06-9-1 轉紅 | 06-9 |
| R-BK-38 | 二 | 頻率上限（伺服器端）：full——各 repo 最近一份全備的 `stop` 距 now **皆** < 86400 秒（`min-full-interval-seconds`）⇒ 409 `backup_too_frequent`，`details={type, nextAllowedAt}`，`nextAllowedAt`＝各 repo（最近全備＋86400 秒）的最小值；任一 repo 較舊或缺席 ⇒ 允許；恰 24 小時 ⇒ 允許；diff——各 repo 最近一份**差異**備份、門檻 3600 秒（`min-diff-interval-seconds`）；verify 不設；info 不可讀或控制面不可用 ⇒ 503 而非 409 | `BackupJobService`：`<` 改 `<=` ⇒ AT-BK-06-10-1（c 列）轉紅；缺席視為「剛備份過」⇒ AT-BK-06-10-1（d 列）轉紅；改為「任一 repo 在內」才擋 ⇒ AT-BK-06-10-1（b 列）轉紅；`nextAllowedAt` 取最大值 ⇒ AT-BK-06-10-1（a、e 列）轉紅；對 verify 也擋 ⇒ AT-BK-06-10-1、AT-BK-06-10-2 轉紅；info 不可讀時放行 ⇒ AT-BK-06-10-E-1 轉紅 | 06-10 |
| R-BK-39 | 二 | 輪詢預算：`BACKUP_JOB_POLL_MS`＝`NOTIFICATION_POLL_FLOOR_MS`（10 秒）、`BACKUP_OVERVIEW_POLL_MS`＝30 秒；兩者 `>=` 地板；單分頁每分鐘至多 8 次（工作 6＋總覽 2）；分頁不可見停止；無進行中工作不輪詢工作；兩分頁加各自通知輪詢 ≤20 次／分（限流 100） | `queries.ts`：`BACKUP_JOB_POLL_MS` 改 5000 ⇒ AT-BK-06-11-1、AT-BK-06-11-2 轉紅；常數寫死 10_000 而非取自地板常數 ⇒ AT-BK-06-11-1（靜態字面）轉紅；兩分頁各多開一條重複的總覽輪詢 ⇒ AT-BK-06-11-3（合計 ≤20）轉紅；`refetchIntervalInBackground: true` ⇒ AT-BK-06-11-2（不可見）轉紅；無進行中工作仍輪詢 ⇒ AT-BK-06-11-E-1 轉紅 | 06-11 |

#### G 工作紀錄與遮罩（PRD §5 FR-BK-07；皆階段二）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-40 | 二 | `GET /backups/jobs?limit=&before=`：Console 發起的工作，`requested_at` 嚴格新到舊；`limit` 預設 20、1～100；`before` 為 ISO 時間（嚴格小於）；回 `{items[], nextBefore}`，`nextBefore`＝最後一筆 `requestedAt`（尚有更多時）否則 null；參數非法 ⇒ 422 `invalid_request`；排程工作不建列、不在此表；UI 八欄表頭、狀態與理由中文（`BACKUP_REASONS`）、「載入更多」以 `nextBefore` 續取、空狀態「尚無手動工作」、一行說明排程工作看狀態卡 | `BackupJobAdapter`：游標改 `<=` ⇒ AT-BK-07-1-1（邊界列重複）轉紅；排序改升冪 ⇒ AT-BK-07-1-1 轉紅；`limit` 上限放寬到 1000 ⇒ AT-BK-07-1-2（`limit=101`）轉紅；sidecar 完成排程工作時也建列 ⇒ AT-BK-07-1-E-1 轉紅；UI 理由欄顯示英文 reason 原值 ⇒ AT-BK-07-1-3 轉紅；空狀態顯示 0 ⇒ AT-BK-07-1-E-2 轉紅 | 07-1 |
| R-BK-41 | 二 | `GET /backups/jobs/{id}`：查無或 id 非 UUID ⇒ 404 `backup_job_not_found`；`detail`（已遮罩的**最後** ≤2000 字元）與 `requestedBy` 僅 ADMIN 有值，非 ADMIN 為 null；UI：ADMIN 每列可展開看尾段與觸發者，非 ADMIN 無展開控制、DOM 不含尾段與觸發者文字 | `BackupController`：非 UUID 回 500 或 422 ⇒ AT-BK-07-2-E-1 轉紅；`detail` 取前 2000 而非後 2000 ⇒ AT-BK-07-2-1（`END-MARK`）轉紅；單筆端點漏遮 `requestedBy` ⇒ AT-BK-07-2-1 轉紅；UI 對非 ADMIN 以 CSS 隱藏而非不渲染 ⇒ AT-BK-07-2-2 轉紅 | 07-2 |
| R-BK-42 | 二 | 遮罩兩道、規格相同：sidecar（`job-run.sh`／runner，perl 或 sed）與 console-api（`BackupMasker.mask`）各遮罩一次；形狀（不分大小寫）：鍵名含 `pass`／`secret`／`key`／`token` 且後接 `=` 或 `:` ⇒ 值（引號字串或到空白、逗號、分號、`&` 為止）改 `***`、保留鍵名與分隔；AWS 存取金鑰 id `AKIA[0-9A-Z]{16}` ⇒ `***`；連線字串 `scheme://user:密碼@host` ⇒ 密碼改 `***`；遮罩器只認形狀、不因 `example`／`fake` 放行；冪等；先遮罩後取最後 2000 字元；探針單檔 `docker/pgbackrest/tests/fixtures/mask-probes.txt`（三欄 TAB：輸入行、機密片段、期望輸出）兩邊共讀且通過 `tools/lib/secret_scan.py` | `BackupMasker`：漏掉 DSN 形 ⇒ AT-BK-07-3-2 轉紅；遇到含 `example` 的值就放行 ⇒ AT-BK-07-3-2（`pass=example`）轉紅；先截斷再遮罩 ⇒ AT-BK-07-3-E-1（跨 2000 邊界機密）轉紅；`job-run.sh` 不遮罩尾段 ⇒ AT-BK-07-3-1 轉紅；console-api 信任 sidecar 已遮罩而不再遮 ⇒ AT-BK-07-3-3 轉紅；探針值不含 example／fake ⇒ AT-BK-07-3-4 轉紅（pre-commit 掃描） | 07-3 |

#### H 說明區（PRD §5 FR-BK-08）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-43 | 一 | 「還原與說明」分頁只有說明、沒有任何還原按鈕與寫入請求；顯示還原三步（停 primary → 容器內 `restore.sh` → 啟動並核對；bash 與 PowerShell 兩種形態）、核對三項（列數、時間軸、`pgbackrest check`；bash 形態，PowerShell 以一句前後綴說明）、明寫「本頁不提供還原按鈕」與原因（F-14）；UI 指令常數（`RESTORE_STEPS`、`RESTORE_CHECKS`）的每條指令整行等於 `docker/README.md` 〈4.3〉節 code block 的某一行（兩邊去前後空白後比；README 的 code block 縮排兩格；單向：README 另增指令不紅、不鎖整段文字） | `sysadminBackup.ts`：把 `--target-time` 例值改一字 ⇒ AT-BK-08-1-1 轉紅；README 刪掉含 `restore.sh` 的行 ⇒ AT-BK-08-1-1／AT-BK-08-1-E-1(a) 轉紅；`BackupHelp.tsx` 加「立即還原」按鈕 ⇒ AT-BK-08-1-E-2 轉紅；少了「本頁不提供還原按鈕」句 ⇒ AT-BK-08-1-2 轉紅；README 另增一行即紅（鎖過嚴）⇒ AT-BK-08-1-E-1(c) 轉紅 | 08-1 |
| R-BK-44 | 一 | 涵蓋範圍表（`VOLUME_COVERAGE`）逐卷分類且類別封閉 {backed_up、backup_mechanism、rebuildable、not_covered}：`pg_data`＝已備份；`pg_backup`、`minio_data`、`pg_wal_archive`、`pg_socket`、`backup_out`（階二加 `backup_req`）＝備份機制本身；`pg_replica_data`＝可由 primary 重建；`engine_workspace`、`app_logs`、`redis_data`、`prometheus_data`、`nginx_certs`、`minio_certs`＝未涵蓋（`engine_workspace` 明寫「未涵蓋」；`minio_certs` 註「缺時由 minio-certs job 重產」）；並寫明「`PGBACKREST_CIPHER_PASS` 遺失＝備份無法還原、`CONSOLE_ENCRYPTION_KEY` 遺失＝敏感參數無法解密，請另行保管」 | `sysadminBackup.ts`：把 `engine_workspace` 歸為 `backed_up` ⇒ AT-BK-08-2-1、AT-BK-08-2-E-1 轉紅；少了金鑰遺失句 ⇒ AT-BK-08-2-1 轉紅；某卷出現兩個類別 ⇒ AT-BK-08-2-E-1 轉紅 | 08-2 |
| R-BK-45 | 一 | 涵蓋表鍵集合與 `docker-compose.yml` 頂層 `volumes:` 卷集合**雙向相等**（新增卷未歸類或表內有不存在的卷皆紅）；前端無 YAML 依賴，以規則式取區塊（自行首 `volumes:` 到下一個頂格鍵或檔尾、兩格縮排鍵名、容許鍵後註解、CRLF）並自證卷數 ≥12（否則「解析失敗」而紅）；現 12 卷、階一 13（`backup_out`）、階二 14（`backup_req`），表與 compose 同 commit | `backup-docs.test.ts` 的解析：改成「到下一個縮排鍵」而不認檔尾 ⇒ AT-BK-08-3-E-1(f) 轉紅；解析不到時回空集合而不報錯 ⇒ AT-BK-08-3-E-1(c) 轉紅；compose 加 `backup_out` 而表未加 ⇒ AT-BK-08-3-1 轉紅；compose 階二漏 `backup_req` ⇒ AT-BK-08-3-2 轉紅（釘值 14） | 08-3 |

#### I sidecar 控制面與 Prometheus（PRD §5 FR-BK-09）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-46 | 二 | runner（`backup-ctl-runner.sh`）處理合法請求的順序與語意：先原子寫 `results/<id>.json`（`running`＝已撿標記；`started_at`＝撿起時刻，非 null）→ 以**背景子行程**啟動 `job-run.sh <type> manual <id>`（runner 不等待）→ 終態由 `job-run.sh` 於持鎖期間寫入 results（rc、`started_at`／`finished_at`、遮罩尾段，R-BK-48）；rc 75（未持鎖）由子行程補寫 `rejected`／`busy`；**不刪請求檔**；已撿與否只看 results 是否存在（至多一次、重啟不重播）；請求只認 `{schema_rev:1,id:UUID(須等於檔名),type∈{full,diff,verify},requested_at,expires_at}`，多餘鍵忽略、不解譯為指令（`type` 只經封閉 `case` 對映到腳本） | `backup-ctl-runner.sh`：先啟動腳本後寫 results ⇒ AT-BK-09-1-1（標記檔須為 1）轉紅；前景等待工作 ⇒ AT-BK-09-1-1（2 秒內返回）與 AT-BK-09-8-1 轉紅；結束後刪請求檔 ⇒ AT-BK-09-1-1 轉紅；以 `eval` 或組字串執行 `type` ⇒ AT-BK-09-1-3 轉紅；不看 results 而看請求檔存在判已處理 ⇒ AT-BK-09-1-2 轉紅；接受 `dump` ⇒ AT-BK-09-1-E-1 轉紅 | 09-1 |
| R-BK-47 | 二 | 請求檔防禦：檔名須為小寫 UUID（`*.tmp` 一律略過、不記 WARN）且為常規檔（非符號連結、非目錄、非 FIFO）、≤4096 位元組、JSON、type 合法、未過期、`id` 等於檔名；目錄內檔數 >16 ⇒ 目錄級拒絕（不執行、不寫 results、只記 WARN；D-BK-T18、勘誤 1-15）；讀檔在 `timeout` 子殼內（擋 FIFO 阻塞）：開檔後 `lstat` 路徑，須為常規檔且 dev:ino 與 fd 一致，只讀前 4 KB；不合法者可寫則寫 `rejected`（封閉詞彙 `rejected_invalid`／`expired`）否則只記 WARN（無 results 的壞檔，同一檔在 runner 生命期內至多一行，免得每輪淹沒日誌）；results、WARN、stderr 不含請求檔任何原文（含 jq 錯誤訊息）；results 不可寫時不執行請求（無法保證至多一次）；單一壞檔不中止迴圈 | `backup-ctl-runner.sh`：只驗內容、不驗檔案型態 ⇒ AT-BK-09-2-3（符號連結指向合法請求）轉紅；不用 `timeout` ⇒ AT-BK-09-2-1（FIFO）轉紅；4096 改成 8192 ⇒ AT-BK-09-2-2 轉紅；WARN 帶出 jq 錯誤訊息 ⇒ AT-BK-09-2-1（canary、`parse error`）轉紅；17 份時仍逐份處理 ⇒ AT-BK-09-2-2 轉紅；單一壞檔 `exit` ⇒ AT-BK-09-2-1（uuidH 須執行）轉紅；results 不可寫仍執行 ⇒ AT-BK-09-2-E-1 轉紅；對 `*.tmp` 記 WARN 或同一壞檔每輪都記 WARN ⇒ AT-BK-09-2-E-2 轉紅；接受大寫 UUID 檔名 ⇒ AT-BK-09-2-E-2 轉紅 | 09-2 |
| R-BK-48 | 一 | `job-run.sh <job> <scheduled\|manual> [<id>]`：以**命令形** `flock -o`（`--close`）包裝，鎖檔 `/run/backup-ctl/maintenance.lock`（sidecar 本地、不在共享卷）；排程等待至 `JOB_LOCK_WAIT_SECONDS`（7200）、逾時 ⇒ 不執行腳本、`jobs/<job>.json` 記 `failed`／`lock_timeout`／rc 75、stderr 恰一行；手動 `flock -n`、拿不到 ⇒ 立即 rc 75（`busy`、不改狀態檔）；鎖檔開不了 ⇒ fail-open（照常執行、WARN、`last.note="locking:unavailable"`）；狀態檔寫入失敗 ⇒ 只 WARN、仍執行並原樣回傳腳本 rc 與輸出；暫存 PG 不繼承鎖 fd；**終態寫入（`jobs/<job>.json`，有 `<id>` 時含 `results/<id>.json`）須在持鎖行程內完成**，鎖在終態寫完之後才釋放（否則清掃會在空窗內把正常結束的工作誤判為 interrupted） | `job-run.sh`：移除 `-o`／`--close` ⇒ AT-BK-09-3-6 轉紅；排程路徑改 `-n`（不等待）⇒ AT-BK-09-3-1 轉紅；逾時不寫 `lock_timeout` ⇒ AT-BK-09-3-3 轉紅；鎖檔開不了時中止 ⇒ AT-BK-09-3-4 轉紅；狀態檔寫入失敗時 `exit 1` ⇒ AT-BK-09-3-5 轉紅；改 fd 形 `exec 9>`／`flock 9` ⇒ AT-BK-09-3-E-1、AT-BK-09-5-5 轉紅；終態寫入移到 `flock` 行程之外 ⇒ AT-BK-09-3-7 轉紅 | 09-3 |
| R-BK-49 | 一 | crontab 四條備份與驗證工作改經 `job-run.sh <job> scheduled`（保留 `>> /var/log/pgbackrest/cron.log 2>&1` 與原 cron 時間欄）；expire 與 WAL 清理兩列不動；`backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`verify-backup.sh` 等腳本本體零修改；`.last_backup_status` 的寫入與 `pgbackrest_backup_last_status` 的語意與值不變（包裝不碰該檔）；rc、stdout、stderr 原樣透傳 | `crontab`：漏掉 `>> cron.log` ⇒ AT-BK-09-4-1 轉紅；某工作仍直接呼叫腳本 ⇒ AT-BK-09-4-1 轉紅；`backup-incr.sh` 被順手修改 ⇒ AT-BK-09-4-2 轉紅；`job-run.sh` 吞掉 rc（一律回 0）⇒ AT-BK-09-4-3、AT-BK-09-3-4、AT-BK-09-3-5 轉紅；stdout 與 stderr 合併 ⇒ AT-BK-09-4-3 轉紅；`pgbackrest-metrics.sh` 改了既有指標行 ⇒ AT-BK-09-4-E-1 轉紅 | 09-4 |
| R-BK-50 | 一 | 匯出（`backup-ctl-export.sh`，runner 每 `BACKUP_CTL_EXPORT_SECONDS`＝60 秒與每次工作結束後以 `timeout 120` 啟動；前一個未結束就略過，不重疊、不共用 `.tmp`）：每輪先清掃 interrupted；原子寫 `export/info.json`（`{schema_rev:1, generated_at, ok, info(原輸出), retention, repos}`；失敗＝`{schema_rev,generated_at,ok:false}`）；`export/logical.json`（至多每 300 秒；`mc` 失敗＝`ok:false`、不寫部分清單、不保留舊清單）；`schedule` 子命令由 crontab 產生 `export/schedule.json`（啟動 root 階段一次）；所有檔 0644、目錄 0755 | `backup-ctl-export.sh`：直接 `>` 寫目的檔（非 `.tmp` 後改名）⇒ AT-BK-09-5-1（inode 不變、`jq -e` 讀到半個檔）轉紅；不做重疊防護 ⇒ AT-BK-09-5-3 轉紅；`mc` 失敗仍寫舊清單 ⇒ AT-BK-09-5-2 轉紅；logical 不節流 ⇒ AT-BK-09-5-2 轉紅；info 失敗仍寫 `ok:true` ⇒ AT-BK-09-5-E-1 轉紅；schedule 少辨識 wal_clean ⇒ AT-BK-09-5-4 轉紅；檔案模式 0640 ⇒ AT-BK-09-6-4 轉紅 | 09-5、09-6 |
| R-BK-51 | 一 | 心跳：runner 每輪迴圈（≤ `BACKUP_CTL_POLL_SECONDS`）原子更新 `export/heartbeat`＝`{schema_rev:1, ts（ISO Z）, lock_held}`；`lock_held` 只由 `/proc/locks` 比對鎖檔 dev:ino 得出（不以取鎖探測、不干擾持有者）；迴圈**永不等待**子行程（工作、匯出皆背景，匯出受 `timeout` 約束），故長工作與匯出逾時都不使心跳中斷（相鄰 `ts` 間隔 ≤3 秒於縮短參數下） | `backup-ctl-runner.sh`：以 `flock -n` 取鎖探測 `lock_held` ⇒ AT-BK-09-5-5（`flock.log` 有呼叫）、AT-BK-09-5-E-2 轉紅；心跳少寫 `schema_rev` ⇒ AT-BK-09-5-5 轉紅；匯出改前景同步 ⇒ AT-BK-09-8-2 轉紅；工作改前景同步 ⇒ AT-BK-09-8-1 轉紅；心跳只在有請求時更新 ⇒ AT-BK-09-8-1 轉紅；runner 迴圈被暫停時心跳不中斷（量測失效）⇒ AT-BK-09-8-E-1 轉紅 | 09-5、09-8 |
| R-BK-52 | 一 | 狀態持久與權限：`export/jobs/*.json` 住具名卷 `backup_out`（跨容器重建、重啟仍在）；啟動清掃把「進行中但鎖未持有」改記 `interrupted`（含對應 results）；目錄權限由**寫入端映像**定義（sidecar 映像建 `/backup-out`、`/run/backup-ctl` 屬 postgres 0755，entrypoint root 階段另 `install -d -m 0755` 建 `export`、`export/jobs`、`results`；階二 backend 映像建 `/backup-req` 屬 spring 0755）；讀取端一律 `:ro,nocopy`、寫入端不帶 `nocopy`；compose 旗標鎖（PyYAML）驗證 | `docker-compose.yml`：backend 的 `backup_out` 改為可寫或少 `nocopy` ⇒ AT-BK-09-6-1 轉紅（鎖函式本身被改鬆則 AT-BK-09-6-E-1 轉紅）；pgbackrest 的 `backup_req` 少 `ro` ⇒ AT-BK-09-6-1 轉紅；sidecar Dockerfile 的 0755 改 0750 ⇒ AT-BK-09-6-2 轉紅；清掃不看鎖持有者 ⇒ AT-BK-09-6-3 轉紅 | 09-6 |
| R-BK-53 | 一 | metrics：`pgbackrest-metrics.sh` 於 `.last_backup_status` 區塊之後追加 `aisdlc_backup_job_last_status{backup_job}`（0 成功、1 失敗）、`aisdlc_backup_job_last_finished_timestamp_seconds{backup_job}`、`aisdlc_backup_ctl_heartbeat_timestamp_seconds`（各帶 HELP／TYPE gauge；無狀態檔的 job 不產生序列）；標籤名用 `backup_job`（不用 `job`：與抓取目標標籤 `job="pgbackrest"` 相撞，曝光值被改名 `exported_job`，`prometheus.yml:30-33` 無 `honor_labels`）；既有 14 個指標名稱與語意不變 | `pgbackrest-metrics.sh`：失敗時輸出 0 ⇒ AT-BK-09-7-1 轉紅；少了心跳指標 ⇒ AT-BK-09-7-1 轉紅；改動既有 `pgbackrest_backup_last_status` 行 ⇒ AT-BK-09-4-E-1 轉紅；無狀態檔的 job 輸出 0 ⇒ AT-BK-09-7-1 轉紅；標籤名改回 `job` ⇒ AT-BK-09-7-1、AT-BK-09-7-R-1 轉紅 | 09-7 |
| R-BK-54 | 一 | Prometheus 規則：`alerts.yml` 的 `aisdlc-backup` 群組末尾新增 `PgBackRestJobFailed`（`aisdlc_backup_job_last_status{backup_job=~"dump\|verify"} != 0`、`for: 1m`、`critical`）與 `PgBackRestControlHeartbeatStale`（`time() - aisdlc_backup_ctl_heartbeat_timestamp_seconds > 120`、`for: 1m`、`warning`），總數 12→14；規則檔被 Prometheus 載入（`rule_files` 與 compose 掛載）；新增規則名都在 `docker/prometheus/tests/backup_alerts_test.yml`；`promtool check rules`、`promtool test rules` 皆綠（本機限定，CI 無 promtool 步驟為已知缺口）；`docker/README.md` 〈7〉「共 12 條」→「共 14 條」 | `alerts.yml`：`backup_job=~"dump\|verify"` 改 `backup_job=~".+"` ⇒ AT-BK-09-7-2（expr 逐字）、AT-BK-09-7-3（full=1 不得 firing）轉紅；`> 120` 改 `> 300` ⇒ AT-BK-09-7-2、AT-BK-09-7-3（121 秒列）轉紅；掛載行被刪 ⇒ AT-BK-09-7-2、AT-BK-09-7-E-1(b) 轉紅；`backup_alerts_test.yml` 缺其中一條 ⇒ AT-BK-09-7-E-1(a) 轉紅；README 〈7〉仍寫「共 12 條」⇒ AT-BK-09-7-2 轉紅；規則標籤改回 `job` ⇒ AT-BK-09-7-2、AT-BK-09-7-R-1 轉紅 | 09-7 |

#### J 資料、稽核與安全（PRD §5 FR-BK-10）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-55 | 二 | Flyway `V15__backup_jobs.sql` 建 `console.backup_jobs`（欄位、CHECK、預設值逐項如 PRD §8.1；部分唯一索引 `ux_backup_jobs_one_active ON ((1)) WHERE status IN ('QUEUED','RUNNING')`；`idx_backup_jobs_requested_at`），既有表零變動；寫入者唯一＝console-api（Bridge、sidecar 不讀不寫）；JDBC 配接器、無 JPA 實體；`backup_jobs` 只被 `BackupJobAdapter` 一個類別觸及；寫入敘述只有 INSERT 與條件式 UPDATE | `V15__backup_jobs.sql`：`type` 的 CHECK 多放 `'incr'` ⇒ AT-BK-10-1-1 轉紅；`detail` 少 `NOT NULL DEFAULT ''` ⇒ AT-BK-10-1-1 轉紅；順手改了既有表 ⇒ AT-BK-10-1-1（欄位快照）轉紅；新增 `@Entity` ⇒ AT-BK-10-1-E-1 轉紅；遷移檔版號寫成 V16（跳號）⇒ AT-BK-10-1-2 轉紅；四個既有 migration IT 未補 "15" ⇒ AT-BK-10-1-3（與四個 IT 自身）轉紅；第二個類別查 `backup_jobs` ⇒ AT-BK-10-1-E-1 與 AT-BK-06-8-E-1 轉紅 | 10-1 |
| R-BK-56 | 二 | 審計：POST 成功留 `method=POST`、`entity_type=backup`、`entity_id=<job id>`、`http_status=202`（用例以 `AuditTrail.note("backup.trigger","backup",id)` 標註）；終態對帳另有 `AuditTrail.system("backup.finished","backup",id,…)` 恰一列（`subject=system`、`method=SYSTEM`、`path=system:backup.finished`、`http_status=200`）；被拒的 POST（401、403、409、422）同樣由 `AuditLoggingFilter` 留列；GET 不留列 | `BackupJobService`：未呼叫 `note` ⇒ AT-BK-10-2-1（entity_type／entity_id）轉紅；對帳補兩次審計 ⇒ AT-BK-10-2-1、AT-BK-06-8-2 轉紅；`AuditTrail.system("backup.finished",…)` 的 details 帶入 results 的 `detail_tail`（含植入機密）⇒ AT-BK-10-4-1（日誌事件掃描）轉紅；對 GET 也寫審計 ⇒ AT-BK-10-2-E-1 轉紅；`AuditLoggingFilter` 排到授權之後（被拒的 POST 不留列）⇒ AT-BK-10-2-2 轉紅 | 10-2 |
| R-BK-57 | 二 | `SecurityConfig` 在通用 `/api/v1/**` 規則**之前**加 `requestMatchers(HttpMethod.POST, "/api/v1/sysadmin/**").hasRole("ADMIN")`（先中者定案）；所有 GET 為 VIEWER 以上；其他方法（PUT、PATCH、DELETE）沒有對映（404／405，VIEWER 403）；說明註解 `SecurityConfig.java:41-53` 同步 | `SecurityConfig`：把新規則放在通用規則之後 ⇒ AT-BK-10-3-2（順序掃描）、AT-BK-10-3-1（OPERATOR 得 202）轉紅；改成 `hasAnyRole("OPERATOR","ADMIN")` ⇒ AT-BK-10-3-1 轉紅 | 10-3 |
| R-BK-58 | 一 | 不洩漏機密：console-api 環境沒有 MinIO 金鑰與 cipher 密碼（compose 的 backend 環境無 `PGBACKREST_*`、`AWS_*`、`OFFSITE_S3_*`、`MC_HOST*`；不掛 `pg_data`、`pg_backup`；無 docker socket）；任何回應本文、日誌行、審計列、控制面檔案不含 DB 密碼、加密金鑰與植入的機密值；console-api 對 sidecar 只有檔案 I/O（無行程啟動、無網路呼叫） | `BackupQueryService`：把例外 `toString()` 回給用戶端（含連線字串）⇒ AT-BK-10-4-1 轉紅；洩漏掃描器改成只掃回應本文 ⇒ AT-BK-10-4-E-1（防反空轉語料筆數）轉紅；compose 的 backend 加 `AWS_SECRET_ACCESS_KEY` ⇒ AT-BK-10-4-2 轉紅；backup 類別呼叫 `ProcessBuilder` ⇒ AT-BK-10-4-3 轉紅 | 10-4 |
| R-BK-59 | 一 | OpenAPI：階一 75 路徑／86 操作（加 `GET /api/v1/sysadmin/backups`，`operationId=getBackupOverview`）；階二 77／89（加 `jobs` 的 get、post 與 `jobs/{id}` 的 get；`getBackupJobs`、`getBackupJob`、`postBackupJob`）；tag「系統管理（資料庫備份）」；sysadmin 路徑無 put、patch、delete；`schema.d.ts` 隨階段重產入庫；`endpoints.ts` 匯出函式 83→84→87 | `BackupController`：operationId 命名成 `getBackups` ⇒ AT-BK-10-5-1 轉紅；少宣告 tag ⇒ AT-BK-10-5-1 轉紅；`schema.d.ts` 未重產 ⇒ AT-BK-10-5-3 轉紅；端點多一個路徑 ⇒ AT-BK-10-5-1／AT-BK-10-5-2 轉紅 | 10-5 |
| R-BK-60 | 二 | reason 雙向鎖：契約檔 `API_Contract_SysAdminBackup.md` 的〈backup 類 reason 表〉（欄序 `reason｜狀態碼｜details｜中文訊息｜意義`）與 `ErrorReasons` 的 `BACKUP_` 前綴常數（五個有狀態碼的 API reason）、後端工作理由列舉（八個，狀態碼欄為「—」）、前端 `BACKUP_REASONS`（十三個鍵與中文訊息）三方鍵集合與訊息逐字相同；`BACKUP_REASONS` 不入 `reasons.ts`；`invalid_request` 以區域常數持有、不入表 | `BACKUP_REASONS`：`busy` 的訊息差一字 ⇒ AT-BK-06-5-3 轉紅；`ErrorReasons` 多一個 `BACKUP_X` 而契約表無 ⇒ AT-BK-06-5-4 轉紅；`BackupJobReason` 少一個工作理由 ⇒ AT-BK-06-5-4、AT-BK-06-8-1（reason 值域）轉紅；前端 `BACKUP_REASONS` 缺一個工作理由 ⇒ AT-BK-06-5-5、AT-BK-07-1-3 轉紅；解析器把第二張表也納入 ⇒ AT-BK-06-5-E-2 轉紅 | 06-5、06-8、07-1 |

#### K 跨切面（PRD §6、§9.5）

| R | 階 | 條文 | 突變（轉紅） | AT |
|---|---|---|---|---|
| R-BK-61 | 一 | 既有鎖只做可見的釘值上修、不刪斷言（§5.7 同步鎖逐檔逐行；基準 `000a217b` 重核）；`reasons.ts`、`API_Contract_P3-6.md`、新函式不以 `Si` 起頭；本功能改動只在 `AgentConsole/**` 與 PRD／TCS 文件（根層 `tools/`、`.claude/`、`.github/`、引擎、Bridge 零變動）；新類別守既有分層鎖（`ArchitectureRulesTest.java:23-28、32、52` 的 A1／A2／A5 與 `SiReadOnlyArchTest.java:124-134` 對全部類別再驗一次，**不放寬**）：Spring 相依的 `BackupCron`、`BackupOverdue` 在 `application/service`，設定經 `application/port/out/BackupSettings` 與 `infrastructure/config/BackupSettingsAdapter`，時間經專屬 `BackupClock` | 任一同步鎖被刪斷言 ⇒ G-C5 人工核對失敗（AT-BK-01-1-3）；順手動 `.github/workflows` 或根層 `tools/` ⇒ G-C1 的路徑差分失敗（AT-BK-09-4-E-2）；`BackupCron` 搬進 `domain/model/backup` 或服務類直接依賴 `BackupProperties` ⇒ 既有 A1／A2／A5 轉紅（G-K1；AT-BK-04-3-E-2 的掃描範圍同步）；放寬 `ArchitectureRulesTest` ⇒ G-C3 的 `git diff --exit-code` 失敗 | 01-1、09-4 |
| R-BK-62 | 一 | sidecar 新腳本品質：`job-run.sh`、`backup-ctl-export.sh`、`backup-ctl-runner.sh` 通過 `bash -n` 與 shellcheck 全嚴重度（`python tools/run_shellcheck.py` rc 0、`_BASELINE` 不新增鍵）；LF 行尾；僅在 Linux 容器執行 | 任一新腳本含 `SC2086`（未引號變數）⇒ AT-BK-09-3-E-2（G-S1 shellcheck）轉紅；CRLF 行尾 ⇒ AT-BK-09-3-E-2（`bash -n`）轉紅 | 09-3、09-5 |

### 契約節（可直接抄進 `AgentConsole/docs/02_architecture/API_Contract_SysAdminBackup.md`；本節為真相，契約檔不得與它不同）

#### C0 共通約定

| 項目 | 約定 |
|---|---|
| 命名 | 對外 API 一律 camelCase；控制面檔案（§C1）與 sidecar 輸出一律 snake_case；兩者對映規則：控制面檔案鍵 snake_case → API 鍵 camelCase（例 `last_success_at`→`lastSuccessAt`、`detail_tail`→`detailTail`、`endpoint_host`→`endpointHost`），值一律不動 |
| 封包 | 成功沿既有 `ApiResult<T>`：`{code:200, message:'success', data, timestamp, traceId}`；失敗沿 `ApiError`：`{code, message, reason?, errors[{field,message}], details?, timestamp, traceId}`；任何失敗沒有 `data` |
| 時間 | 所有時間戳為 ISO-8601 UTC 帶 `Z`（控制面檔案與 API 皆然）；排程時區（`schedule.json.tz`，預設 `Asia/Taipei`）只用於計算 `nextRunAt`、`lastDueAt` 與前端「排程時區」註記 |
| 缺鍵與 null | `null`＝量不到或不適用於該資料；非 ADMIN 的 `detailTail`、`requestedBy`、`detail` 為 `null`（或鍵缺席，兩者等價，測試兩者皆接受）；資料區塊 `null`＝該區塊因 `control.reason` 或來源失敗而不提供，**不得**以空陣列或 0 代替 |
| 角色 | 所有 GET：VIEWER 以上；`POST /api/v1/sysadmin/**`：僅 ADMIN；其他方法沒有對映 |
| 單位 | 大小＝位元組；耗時＝秒（整數）；`exportAgeSeconds`、`heartbeatAgeSeconds` 為相對 console-api 時鐘（`Clock`）的整數秒（無條件捨去） |

#### C1 控制面檔案協定 v1（兩個具名卷；寫入一律「寫 `.tmp` → 同目錄改名」；檔 0644、目錄 0755；內容絕不含機密）

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

#### C2 sidecar 指令（皆在 `AgentConsole/docker/pgbackrest/scripts/`、映像內 `/usr/local/bin/`；測試縫環境變數見 D-BK-T16）

| 指令 | 行為與輸出 |
|---|---|
| `job-run.sh <job> <scheduled｜manual> [<uuid>]` | `<job>`∈{full,diff,dump,verify} 對映 `backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`verify-backup.sh`；以命令形 `flock -o`（`--close`）包裝；排程等鎖至 `JOB_LOCK_WAIT_SECONDS`、手動不等待；取得鎖後寫 `jobs/<job>.json`（`running`）→ 執行腳本（stdout、stderr 原樣透傳並各自同步擷取）→ **持鎖期間**寫終態（遮罩、取最後 2000 字元；有 `<uuid>` 時一併寫 `results/<uuid>.json`），之後才釋放鎖；結束碼＝腳本 rc，唯手動 busy 與排程 lock_timeout 為 75；鎖檔開不了／狀態檔寫不了皆 fail-open（WARN；前者記 `note=locking:unavailable`）；**不碰** `.last_backup_status` |
| `backup-ctl-runner.sh [--once]` | 迴圈（`--once`＝只做一輪）：每輪先清掃 interrupted、原子更新 `heartbeat`、必要時以 `timeout $BACKUP_CTL_EXPORT_TIMEOUT_SECONDS` 背景啟動匯出子行程（前一個未結束則略過）、掃請求目錄（階段二）：撿最舊且 `results/<id>.json` 尚不存在的合法請求 → 先寫 `results`（`running`，`started_at`＝撿起時刻）→ 背景子行程跑 `job-run.sh <type> manual <id>`（終態由 `job-run.sh` 持鎖時寫入，R-BK-48；子行程僅在 rc 75 時補寫 `rejected`／`busy`）；**永不等待子行程**；非法請求依 R-BK-47 處理 |
| `backup-ctl-export.sh` | 一輪匯出（受單一實例鎖 `export.lock`〔非維護鎖〕保護，重疊則立即結束碼 0）：清掃 interrupted → 原子寫 `info.json` → （距上次 ≥300 秒才）寫 `logical.json`；失敗只寫 `ok:false`、結束碼 0 |
| `backup-ctl-export.sh schedule` | 由 `BACKUP_CTL_CRONTAB` 與 `TZ` 產生 `export/schedule.json`（啟動 root 階段呼叫一次）；無法辨識的列略過並記 WARN |
| `pgbackrest-metrics.sh <輸出檔>` | 既有 14 個指標不變；追加 §C6 的三個指標 |

#### C3 console-api 端點（`/api/v1/sysadmin`；operationId 與 tag「系統管理（資料庫備份）」）

**C3.1 `GET /backups`（`getBackupOverview`；VIEWER 以上；階一）** `data` 物件（鍵序固定，以保序 Map 輸出）：

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

**C3.2 `GET /backups/jobs?limit=&before=`（`getBackupJobs`；VIEWER 以上；階二）** `data`＝`{items:[{id, type, status, requestedAt, startedAt, finishedAt, durationSeconds, exitCode, reason, requestedBy, detail}], nextBefore:ISO｜null}`；`status`∈{QUEUED,RUNNING,SUCCEEDED,FAILED,REJECTED,EXPIRED}；`requestedBy`、`detail` 僅 ADMIN；參數規則見 D-BK-T14。

**C3.3 `GET /backups/jobs/{id}`（`getBackupJob`；VIEWER 以上；階二）** `data`＝單筆同 `items[]` 形；查無或 id 非 UUID ⇒ 404 `backup_job_not_found`。

**C3.4 `POST /backups/jobs`（`postBackupJob`；僅 ADMIN；階二）** body `{type:"full｜diff｜verify", confirm:true}`；成功 202，`data`＝`{id, type, status:"QUEUED", requestedAt}`；驗證序與狀態碼（D-BK-T13）：

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

**C3.5 設定（`application.yml` 的 `console.backup.*`；未設＝停用，沿 `docker-compose.yml:149-157` 的空預設寫法；服務層只經 `application/port/out/BackupSettings` 讀取，`BackupProperties` 只作綁定）**：`export-dir`（`CONSOLE_BACKUP_OUT_DIR`）、`request-dir`（`CONSOLE_BACKUP_REQ_DIR`）、`request-ttl-seconds` 120、`job-max-seconds` 21600、`reconcile-interval-ms` 5000、`overdue-grace-minutes` 30、`min-full-interval-seconds` 86400、`min-diff-interval-seconds` 3600；GET 只依 `export-dir`，POST 另依 `request-dir`；compose 的 backend 環境把兩個目錄變數設成字面常數 `/backup-req`、`/backup-out`（階二），不含機密。

#### C4 backup 類 reason 表

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

#### C5 資料所有權（V15；階二）

`console.backup_jobs` 的 DDL 逐字同 PRD §8.1（含 `ux_backup_jobs_one_active ON console.backup_jobs ((1)) WHERE status IN ('QUEUED','RUNNING')` 與 `idx_backup_jobs_requested_at`）；`BackupJobMigrationIT` 驗證部分唯一索引可建。寫入者唯一＝console-api 的 `BackupJobAdapter`（JDBC）；敘述種類恆為：INSERT（QUEUED）、條件式 UPDATE（`markRunningIfQueued`：`WHERE id=? AND status='QUEUED'`；`markTerminalIfActive`：`WHERE id=? AND status IN ('QUEUED','RUNNING')`；`markExpiredIfQueued`：`WHERE id=? AND status='QUEUED'`）與唯讀 SELECT；沒有 DELETE、TRUNCATE。`console.audit_log` 的寫入不變（由 `AuditLoggingFilter` 與 `AuditTrail` 產生）。

#### C6 Prometheus 指標與規則

| 項目 | 規格 |
|---|---|
| 新指標（`pgbackrest-metrics.sh`，gauge） | `aisdlc_backup_job_last_status{backup_job="full｜diff｜dump｜verify"}`（0 成功、1 失敗；`interrupted` 視為 1）；`aisdlc_backup_job_last_finished_timestamp_seconds{backup_job}`（`last.finished_at` 的 epoch 秒；`running` 中不輸出）；`aisdlc_backup_ctl_heartbeat_timestamp_seconds`（`heartbeat.ts` 的 epoch 秒）；無資料來源者不輸出序列。**標籤名不用 `job`**：抓取目標標籤 `job="pgbackrest"`（`prometheus.yml:30-33`，未設 `honor_labels`）會把曝光的 `job` 改名為 `exported_job`，規則的 `{job=~"dump\|verify"}` 永不匹配 |
| 既有 14 個指標 | 名稱與語意不變（`pgbackrest_exporter_info_ok`、`pgbackrest_exporter_scrape_timestamp_seconds`、`pgbackrest_stanza_status`、`pgbackrest_repo_status`、`pgbackrest_backup_count`、`pgbackrest_backup_since_last_full_seconds`、`pgbackrest_backup_since_last_backup_seconds`、`pgbackrest_backup_last_duration_seconds`、`pgbackrest_backup_last_database_size_bytes`、`pgbackrest_backup_last_repo_size_bytes`、`pgbackrest_backup_last_status`、`pgbackrest_backup_last_run_timestamp_seconds`、`aisdlc_storage_bytes`、`aisdlc_storage_used_ratio`） |
| 新規則（`alerts.yml`，群組 `aisdlc-backup` 末尾） | `PgBackRestJobFailed`：`expr: aisdlc_backup_job_last_status{backup_job=~"dump\|verify"} != 0`、`for: 1m`、`severity: critical`；`PgBackRestControlHeartbeatStale`：`expr: time() - aisdlc_backup_ctl_heartbeat_timestamp_seconds > 120`、`for: 1m`、`severity: warning`（`annotations.summary`／`description` 為中文，內容不鎖；`labels` 只鎖 `severity`） |
| promtool 測試 | `docker/prometheus/tests/backup_alerts_test.yml`（`rule_files: ["../alerts.yml"]`）；跑法同 `docker/README.md` 〈可用性 SLO〉的三條指令形（把測試檔換成 `backup_alerts_test.yml`） |
| README | `docker/README.md`：〈1.2〉卷表加 `backup_out`（階二另加 `backup_req`）、〈4.6 控制面〉（新增）、〈7〉「共 12 條」→「共 14 條」、〈9〉加 #35、〈10〉加「從未執行＝沒有序列＝規則不會亮」仍適用於新規則 |

## 1. AC → AT 映射表

PRD 的 53 條 AC 加 1 條 TCS 增量 AC（`AC-BK-04-6`）逐條映射；每條至少一個 AT（`AT-BK-<FR>-<AC>-<n>`），需要負控、邊界或錯誤路徑者另有反向 AT（`AT-BK-<FR>-<AC>-E-<n>`），真機項為 `AT-BK-<FR>-<AC>-R-<n>`。「階」欄為階段（一＝看、二＝控、一＋二＝跨階，以 AT 的階為準）；「載具」欄為 §3.1 的載具代碼。審查核對型（AT-BK-01-1-3、AT-BK-07-3-4、AT-BK-09-3-E-2、AT-BK-09-4-2、AT-BK-09-4-E-2、AT-BK-10-1-3、AT-BK-10-5-3）走 G 編號審查閘；真機型（`RM`、`ES`）見 §3.2 與 PRD §11 的 V 系列。

#### FR-BK-01　導覽與頁面骨架 — 3 條 AC、US-BK-01

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-01-1 | 一 | 導覽九項、末尾新增 | AT-BK-01-1-1、AT-BK-01-1-2、AT-BK-01-1-3 | AT-BK-01-1-E-1 | — | FN、GT |
| AC-BK-01-2 | 一 | 入口卡與導覽 active | AT-BK-01-2-1、AT-BK-01-2-2、AT-BK-01-2-3、AT-BK-01-2-4 | AT-BK-01-2-E-1、AT-BK-01-2-E-2 | — | FN、FH、FP、E2 |
| AC-BK-01-3 | 一 | 行動版 Tab 不顯示 | AT-BK-01-3-1 | AT-BK-01-3-E-1 | — | FN、FT |

#### FR-BK-02　備份清單 — 6 條 AC、US-BK-02

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-02-1 | 一 | 清單新到舊十欄 | AT-BK-02-1-1、AT-BK-02-1-2 | AT-BK-02-1-E-1 | AT-BK-02-1-R-1 | FV、ES、BQ |
| AC-BK-02-2 | 一 | 校驗錯誤警示色 | AT-BK-02-2-1、AT-BK-02-2-2 | AT-BK-02-2-E-1 | — | FV、BQ |
| AC-BK-02-3 | 一 | 格式化沿用既有函式 | AT-BK-02-3-1、AT-BK-02-3-2 | AT-BK-02-3-E-1 | — | FV、FS |
| AC-BK-02-4 | 一 | repo 異常不當成空 | AT-BK-02-4-1、AT-BK-02-4-2 | AT-BK-02-4-E-1 | — | FV、FL、BQ |
| AC-BK-02-5 | 一 | 空狀態不顯示 0 | AT-BK-02-5-1、AT-BK-02-5-2 | AT-BK-02-5-E-1 | — | FV、BQ |
| AC-BK-02-6 | 一 | 本機 MinIO 標同碟 | AT-BK-02-6-1、AT-BK-02-6-2 | AT-BK-02-6-E-1 | — | FV、BQ、BS |

#### FR-BK-03　排程與保留策略（唯讀） — 4 條 AC、US-BK-03

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-03-1 | 一 | 六條 cron 白話列 | AT-BK-03-1-1、AT-BK-03-1-2 | AT-BK-03-1-E-1 | — | FV、FL |
| AC-BK-03-2 | 一 | 不認得原樣退回 | AT-BK-03-2-1 | AT-BK-03-2-E-1 | — | FV、FL |
| AC-BK-03-3 | 一 | nextRunAt 以時區算 | AT-BK-03-3-1、AT-BK-03-3-2 | AT-BK-03-3-E-1 | — | BQ、BV |
| AC-BK-03-4 | 一 | 保留唯讀、null 入警告 | AT-BK-03-4-1、AT-BK-03-4-2、AT-BK-03-4-3 | AT-BK-03-4-E-1、AT-BK-03-4-E-2 | — | FV、BQ、BS |

#### FR-BK-04　最近狀態卡（全備、增備、離站 pg_dump、驗證） — 6 條 AC、US-BK-04

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-04-1 | 一 | 四張卡與最近備份 | AT-BK-04-1-1、AT-BK-04-1-2 | AT-BK-04-1-E-1、AT-BK-04-1-E-2 | AT-BK-04-1-R-1 | FV、FS、BQ、RM |
| AC-BK-04-2 | 一 | 失敗色與最近成功 | AT-BK-04-2-1、AT-BK-04-2-2 | AT-BK-04-2-E-1 | — | FV、BQ |
| AC-BK-04-3 | 一 | lastDueAt 與逾期 | AT-BK-04-3-1、AT-BK-04-3-2、AT-BK-04-3-3 | AT-BK-04-3-E-1、AT-BK-04-3-E-2 | — | FS、BQ、BV、BA |
| AC-BK-04-4 | 一 | 中斷判定 | AT-BK-04-4-1、AT-BK-04-4-2 | AT-BK-04-4-E-1 | — | BQ、BS |
| AC-BK-04-5 | 一＋二 | 非 ADMIN 無尾段 | AT-BK-04-5-1、AT-BK-04-5-2、AT-BK-04-5-3 | AT-BK-04-5-E-1 | — | BQ |
| AC-BK-04-6（TCS 增量） | 一 | WAL 歸檔一行 | AT-BK-04-6-1、AT-BK-04-6-2、AT-BK-04-6-3 | AT-BK-04-6-E-1 | — | FV、BQ、BV、BA |

#### FR-BK-05　控制面健康與資料新鮮度（fail-loud） — 5 條 AC、US-BK-05

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-05-1 | 一＋二 | 未設定整頁說明 | AT-BK-05-1-1、AT-BK-05-1-2、AT-BK-05-1-3 | AT-BK-05-1-E-1、AT-BK-05-1-E-2 | — | FV、BU、BV |
| AC-BK-05-2 | 一＋二 | 心跳離線橫幅 | AT-BK-05-2-1、AT-BK-05-2-2、AT-BK-05-2-3 | AT-BK-05-2-E-1 | AT-BK-05-2-R-1 | FV、ES、BQ |
| AC-BK-05-3 | 一 | 壞檔顯示原因 | AT-BK-05-3-1、AT-BK-05-3-2 | AT-BK-05-3-E-1、AT-BK-05-3-E-2 | — | FV、BQ |
| AC-BK-05-4 | 一 | 資料已過期標記 | AT-BK-05-4-1、AT-BK-05-4-2 | AT-BK-05-4-E-1 | — | FV、BQ |
| AC-BK-05-5 | 二 | DB 失敗降級 | AT-BK-05-5-1 | AT-BK-05-5-E-1 | — | BQ、BV |

#### FR-BK-06　手動觸發（全備、增備、驗證；僅 ADMIN） — 11 條 AC、US-BK-06

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-06-1 | 二 | 確認與保留名額 | AT-BK-06-1-1、AT-BK-06-1-2、AT-BK-06-1-3 | AT-BK-06-1-E-1 | — | FD、FL |
| AC-BK-06-2 | 二 | body 驗證 | AT-BK-06-2-1 | AT-BK-06-2-E-1 | — | BQ |
| AC-BK-06-3 | 二 | 先插列後寫檔 202 | AT-BK-06-3-1、AT-BK-06-3-2、AT-BK-06-3-3、AT-BK-06-3-4 | AT-BK-06-3-E-1 | AT-BK-06-3-R-1 | FV、ES、BQ、BV |
| AC-BK-06-4 | 二 | 單工與併發 | AT-BK-06-4-1、AT-BK-06-4-2、AT-BK-06-4-3 | AT-BK-06-4-E-1 | AT-BK-06-4-R-1 | ES、BQ、BV、BM |
| AC-BK-06-5 | 二 | 排程持鎖 busy | AT-BK-06-5-1、AT-BK-06-5-2、AT-BK-06-5-3、AT-BK-06-5-4、AT-BK-06-5-5 | AT-BK-06-5-E-1、AT-BK-06-5-E-2 | — | FV、FL、BQ、BC、BS |
| AC-BK-06-6 | 二 | 請求 TTL 與兜底 | AT-BK-06-6-1、AT-BK-06-6-2、AT-BK-06-6-3、AT-BK-06-6-4、AT-BK-06-6-5 | AT-BK-06-6-E-1 | — | BQ、BV、BS |
| AC-BK-06-7 | 二 | 僅 ADMIN 可觸發 | AT-BK-06-7-1、AT-BK-06-7-2、AT-BK-06-7-3 | AT-BK-06-7-E-1 | AT-BK-06-7-R-1 | FV、ES、BQ |
| AC-BK-06-8 | 二 | 終態對帳與審計 | AT-BK-06-8-1、AT-BK-06-8-2、AT-BK-06-8-3、AT-BK-06-8-4 | AT-BK-06-8-E-1 | — | BQ、BV、BA |
| AC-BK-06-9 | 二 | 寫檔失敗補償 | AT-BK-06-9-1、AT-BK-06-9-2 | AT-BK-06-9-E-1 | — | BQ、BF、BV |
| AC-BK-06-10 | 二 | 頻率上限 | AT-BK-06-10-1、AT-BK-06-10-2 | AT-BK-06-10-E-1 | — | BQ、BV |
| AC-BK-06-11 | 二 | 輪詢預算 | AT-BK-06-11-1、AT-BK-06-11-2、AT-BK-06-11-3 | AT-BK-06-11-E-1 | — | FV、FL |

#### FR-BK-07　工作紀錄（Console 發起的動作） — 3 條 AC、US-BK-07

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-07-1 | 二 | 工作紀錄分頁 | AT-BK-07-1-1、AT-BK-07-1-2、AT-BK-07-1-3 | AT-BK-07-1-E-1、AT-BK-07-1-E-2 | — | FV、BQ |
| AC-BK-07-2 | 二 | 尾段僅 ADMIN | AT-BK-07-2-1、AT-BK-07-2-2 | AT-BK-07-2-E-1 | — | FV、BQ |
| AC-BK-07-3 | 二 | 兩道遮罩 | AT-BK-07-3-1、AT-BK-07-3-2、AT-BK-07-3-3、AT-BK-07-3-4 | AT-BK-07-3-E-1 | — | BQ、BD、BS、GT |

#### FR-BK-08　說明區：還原與涵蓋範圍（只有說明，沒有按鈕） — 3 條 AC、US-BK-08

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-08-1 | 一 | 還原三步與核對 | AT-BK-08-1-1、AT-BK-08-1-2 | AT-BK-08-1-E-1、AT-BK-08-1-E-2 | — | FV、FK |
| AC-BK-08-2 | 一 | 涵蓋範圍表 | AT-BK-08-2-1 | AT-BK-08-2-E-1 | — | FV、FL |
| AC-BK-08-3 | 一 | 涵蓋表對卷集合 | AT-BK-08-3-1、AT-BK-08-3-2 | AT-BK-08-3-E-1 | — | FK、PY |

#### FR-BK-09　sidecar 控制面（runner、export、包裝） — 8 條 AC、US-BK-09

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-09-1 | 二 | runner 至多一次 | AT-BK-09-1-1、AT-BK-09-1-2、AT-BK-09-1-3 | AT-BK-09-1-E-1 | — | BS |
| AC-BK-09-2 | 二 | 非法請求防禦 | AT-BK-09-2-1、AT-BK-09-2-2、AT-BK-09-2-3 | AT-BK-09-2-E-1、AT-BK-09-2-E-2 | — | BS |
| AC-BK-09-3 | 一 | 共用維護鎖 | AT-BK-09-3-1、AT-BK-09-3-2、AT-BK-09-3-3、AT-BK-09-3-4、AT-BK-09-3-5、AT-BK-09-3-6、AT-BK-09-3-7 | AT-BK-09-3-E-1、AT-BK-09-3-E-2 | — | BS、PY、GT |
| AC-BK-09-4 | 一 | crontab 包裝 | AT-BK-09-4-1、AT-BK-09-4-2、AT-BK-09-4-3 | AT-BK-09-4-E-1、AT-BK-09-4-E-2 | AT-BK-09-4-R-1 | BS、PY、GT、RM |
| AC-BK-09-5 | 一 | 匯出與心跳 | AT-BK-09-5-1、AT-BK-09-5-2、AT-BK-09-5-3、AT-BK-09-5-4、AT-BK-09-5-5 | AT-BK-09-5-E-1、AT-BK-09-5-E-2 | — | BS、PY |
| AC-BK-09-6 | 一＋二 | 狀態持久與權限 | AT-BK-09-6-1、AT-BK-09-6-2、AT-BK-09-6-3、AT-BK-09-6-4、AT-BK-09-6-5 | AT-BK-09-6-E-1 | AT-BK-09-6-R-1 | BS、PY、RM |
| AC-BK-09-7 | 一 | 指標與告警規則 | AT-BK-09-7-1、AT-BK-09-7-2、AT-BK-09-7-3 | AT-BK-09-7-E-1 | AT-BK-09-7-R-1 | BS、PY、PT、RM |
| AC-BK-09-8 | 一＋二 | 不阻塞迴圈 | AT-BK-09-8-1、AT-BK-09-8-2、AT-BK-09-8-3 | AT-BK-09-8-E-1 | AT-BK-09-8-R-1 | BQ、BS、RM |

#### FR-BK-10　資料、稽核與安全 — 5 條 AC、US-BK-10

| AC | 階 | 重點 | 正向 AT | 反向 AT | 真機 AT | 載具 |
|---|---|---|---|---|---|---|
| AC-BK-10-1 | 二 | V15 資料表 | AT-BK-10-1-1、AT-BK-10-1-2、AT-BK-10-1-3 | AT-BK-10-1-E-1 | — | BM、BA、GT |
| AC-BK-10-2 | 二 | 稽核兩列 | AT-BK-10-2-1、AT-BK-10-2-2 | AT-BK-10-2-E-1 | — | BQ |
| AC-BK-10-3 | 二 | RBAC 規則 | AT-BK-10-3-1、AT-BK-10-3-2 | AT-BK-10-3-E-1、AT-BK-10-3-E-2 | — | BQ、BA |
| AC-BK-10-4 | 一 | 不洩漏機密 | AT-BK-10-4-1、AT-BK-10-4-2、AT-BK-10-4-3 | AT-BK-10-4-E-1 | — | BQ、BA、PY |
| AC-BK-10-5 | 一＋二 | OpenAPI 計數 | AT-BK-10-5-1、AT-BK-10-5-2、AT-BK-10-5-3 | AT-BK-10-5-E-1 | — | BQ、GT |

## 2. 可自動化 AT 格式規範

**編號與命名**：AT 編號 `AT-BK-<FR>-<AC>-<n>`（正向）、`AT-BK-<FR>-<AC>-E-<n>`（反向：負控、邊界、錯誤路徑）、`AT-BK-<FR>-<AC>-R-<n>`（真機）；`<FR>`、`<AC>` 取 AC 編號的兩段（`AC-BK-06-10`→`AT-BK-06-10-1`）；`n` 為 1～9。測試函式或標題一律以 AT 編號的底線形開頭：

| 載具 | 命名 | 例 |
|---|---|---|
| backend JUnit 5（含 sidecar 契約測試） | `AT_BK_<FR>_<AC>_<n>_<camelSlug>`、`AT_BK_<FR>_<AC>_E_<n>_<camelSlug>`（沿 `AT_IC_09_3_1_…` 先例） | `AT_BK_06_2_1_invalidBodiesAreRejectedWithoutSideEffects` |
| Bridge 目錄 pytest | `test_AT_BK_<FR>_<AC>_<n>_<slug>`（slug 為 ASCII 蛇形；不得以 `test_AT_2`、`test_AT_3` 起頭） | `test_AT_BK_09_6_1_compose_mount_flags` |
| frontend vitest | `it('AT_BK_<FR>_<AC>_<n> <中文描述>', …)`（標題以底線形開頭） | `it('AT_BK_01_1_1 登記表恰九項…', …)` |
| Playwright | `test('AT_BK_<FR>_<AC>_<n> <描述>', …)` | `test('AT_BK_01_2_E_2 …', …)` |
| promtool | 測試檔內每個 `name:` 以 `AT_BK_09_7_3 ` 起頭；判定＝promtool 結束碼 | `- name: AT_BK_09_7_3 dump 失敗經 for 後響` |

**判定指令樣板**（`<id>` 為 AT 編號的底線形，例 `AT_BK_06_2_1`；一律在該載具的工作目錄執行；rc 先存變數再讀，見 SCG-4 通過標準）：

- backend（工作目錄 `AgentConsole\backend`）：`.\gradlew.bat test --tests "*<類別>.<id>_*"`（IT 與 `BackupSidecarContractIT` 需 Docker daemon 在線）
- Bridge 目錄 pytest（工作目錄 `AgentConsole\engine-bridge`，**同一呼叫內先啟根 venv**）：`python -m pytest tests/test_backup_ctl_deploy_config.py -k <id>_ -q -p no:xdist -o addopts=`
- frontend（工作目錄 `AgentConsole\frontend`）：`npx vitest run <檔> -t "<id>"`；Playwright：`npx playwright test <檔> -g "<id>" --output=<各自目錄>`（共用 `test-results` 會被清空；`E2E_ROOT` 要短）
- promtool（工作目錄＝monorepo 根）：`docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/backup_alerts_test.yml`

**零測試視為失敗**：`No tests found`（Gradle）、`no tests ran`、`No test files found`、`-k` 無命中一律 FAIL（＝該 AT 未實作）；**跳過（skip）不算通過**：Docker 不在線時 IT 與 sidecar 契約測試應回報「工具缺席」而非綠燈（根 CLAUDE.md 規則 12）。

**AT 區塊樣式（Gherkin 壓縮成表列；三項後設資料由載具代碼與樣板推得）**

```
# AT-BK-06-4-2                          # 對應 AC: AC-BK-06-4（PRD §5；R-BK-32）
# 測試類型: Integration                 # 自動化工具: JUnit 5 + Testcontainers PostgreSQL + MockMvc
# 判定指令: .\gradlew.bat test --tests "*BackupApiIT.AT_BK_06_4_2_*"
Given 假 runner 暫停（工作停在 QUEUED）；兩個執行緒以 CyclicBarrier 同時對 ADMIN 送 POST（20 輪）
Then  每輪結果集合恰為 {202, 409}；backup_jobs 恰 1 列 QUEUED；請求目錄恰 1 檔且 id 等於 202 回應的 id
```

**測試檔規則**

1. 本案測試**不在 `tools/tests`**（根層零新模組，PRD §9.4）：根層 `tools/tests` 檔數、行數棘輪與 `MIN_TESTS` 零相依餘裕不受影響（新增收集數增量＝0）；根層 CI 與 compat-ci 的 `paths` 不動。
2. 基線站點鎖：本檔與 RTM 回填檔不得有同一行同時含 `passed`／`skipped` 字樣與 4 位數字；寫「通過」。
3. 機密紀律：所有夾具的金鑰、密碼、DSN 用假值，且值含 `example` 或 `fake` 佔位詞（pre-commit 的 `tools/lib/secret_scan.py` 才不擋）；AWS 存取金鑰 id 形用官方範例 `AKIAIOSFODNN7EXAMPLE`；真值只存在 `.env`（`make_env.ps1` 產生）。
4. 假 DEF／OBS 編號：測試碼不得出現未登記的 `DEF-`／`OBS-SI-` 接數字的片段；本案測試不引用缺陷帳本編號。
5. frontend 新檔須遵守 `tests/design-rules.test.ts`（無 shadow、無漸層、無寫死色碼、圖示只用 Lucide、無 `outline-none`、無 dark 變體）；backend 新檔須通過 Checkstyle 與 JaCoCo ≥80%（`gradlew clean build`）；sidecar 新腳本通過 shellcheck 全嚴重度與 `bash -n`、LF 行尾。
6. 時間與非決定性：backend 純函式與服務一律取 `BackupClock`（AT-BK-04-3-E-2 以掃描鎖住；IT 由 `support/BackupSeam` 換入可變專屬時鐘，不換全域 `Clock`）；sidecar 測試以縮短參數（輪詢 1 秒、睡 15 秒）取代真實長度，並以 D-BK-T16 的環境變數注入。

**突變規格**：每個 R 條文在 R 條文表的「突變」欄有至少一個會使所列 AT 轉紅的最小改動（格式：位置 ⇒ 轉紅的 AT）。QA 在 `git archive <HEAD>` 匯出的暫存副本上逐一套用（**不在工作樹套用**、不用 `git checkout --` 還原），各跑所列 AT 的判定指令，須見轉紅（rc≠0 且至少一個 AT 失敗）；回報「突變 R-BK-nn：killed／survived」。倖存者＝該 R 條文缺鑑別力，須補 AT（補在 §3 並勘誤）。重放注意：(a) 規格有整檔逐條的 `MUTATIONS`（`mutate.py`）與批次的 `BATCHES`（`mutate_seq.py`，基線感知）兩種格式，同名突變在不同模組要列全；(b) 副本缺 `AISDLC_SDD` 要單補 `scripts`，frontend `node_modules` 以 junction 指回工作樹，backend 的 Gradle 快取與 Testcontainers 需 Docker；(c) 無 `.git` 會使讀 git 的測試恆紅，要先量基線再判（本案測試無讀 git 者）；(d) 生產碼尚未存在時，位置以「檔案或類別＋構件」表示，開發棒完成後由 QA 補成可重放的 spec。

## 3. AT 完整清單

### 3.1 載具代碼與判定指令（每個 AT 的「載具」欄；判定指令樣板見 §2）

判定指令一律依 §2 樣板（`<類別>`＝下表「檔案」的類別名，`{id}`＝AT 編號底線形）；載具 ES 另加 `-c tests/e2e/docker.config.ts` 並須先依該設定啟全棧；GT、RM 見該 AT 的 Given。

| 代碼 | 載具 | 檔案 | 持有面 | AT 數 |
|---|---|---|---|---|
| FN | frontend vitest | `lib/nav/sysadmin-nav.test.ts`（新） | F 包 | 5 |
| FT | frontend vitest | `components/layout/ToolsRegion.test.tsx`（既有，擴充） | F 包 | 1 |
| FH | frontend vitest | `components/domain/sysadmin/SysAdminHome.test.tsx`（新） | F 包 | 3 |
| FV | frontend vitest | `components/domain/sysadmin/BackupView.test.tsx`（新） | F 包 | 36 |
| FD | frontend vitest | `components/domain/sysadmin/BackupTriggerDialog.test.tsx`（新） | F 包 | 3 |
| FL | frontend vitest（純函式） | `lib/domain/sysadminBackup.test.ts`（新） | F 包 | 7 |
| FK | frontend vitest（文件鎖） | `components/domain/sysadmin/backup-docs.test.ts`（新） | F 包 | 4 |
| FS | frontend vitest（靜態） | `components/domain/sysadmin/sysadmin.static.test.ts`（新） | F 包 | 3 |
| FP | frontend vitest（條件列：每頁說明案先落地才適用） | 每頁說明案的 `lib/help/*.test.ts`（既有或其實作棒新增）；判定指令 `npx vitest run lib/help` | F 包 | 1 |
| E2 | Playwright（mock API） | `tests/e2e/sysadmin-backup.mock.spec.ts`（新） | F 包 | 1 |
| ES | Playwright（Docker 全棧；真機證據，非每 commit 閘） | `tests/e2e/sysadmin-backup-docker.stack.ts`（新） | F 包 | 5 |
| BQ | backend JUnit 5（IT；真 PostgreSQL＋假 runner＋可變專屬時鐘） | `adapter/in/web/BackupApiIT.java`（新） | K 包 | 62 |
| BU | backend JUnit 5（IT；未設定情境，共用預設 context） | `adapter/in/web/BackupApiUnconfiguredIT.java`（新） | K 包 | 2 |
| BF | backend JUnit 5（`@TempDir`） | `adapter/out/control/FileBackupControlAdapterTest.java`（新） | K 包 | 1 |
| BD | backend JUnit 5（純函式；`BackupMasker`，無 Spring） | `domain/model/backup/BackupDomainTest.java`（新） | K 包 | 2 |
| BV | backend JUnit 5（服務層＋假埠，含 `BackupCron`、`BackupOverdue`；可變專屬時鐘） | `application/service/BackupServiceTest.java`（新） | K 包 | 15 |
| BM | backend JUnit 5（IT；Flyway） | `infrastructure/persistence/BackupJobMigrationIT.java`（新） | K 包 | 3 |
| BA | backend JUnit 5（ArchUnit＋原始碼掃描） | `architecture/BackupArchTest.java`（新） | K 包 | 7 |
| BC | backend JUnit 5（契約表雙向鎖） | `architecture/BackupReasonsContractTest.java`（新） | K 包 | 2 |
| BS | backend JUnit 5（IT；Testcontainers Linux 容器＋stub，sidecar 契約測試） | `sidecar/BackupSidecarContractIT.java`（新；S 包寫在 backend 測試樹） | S 包 | 40 |
| PY | Bridge 目錄 pytest（PyYAML 靜態鎖） | `AgentConsole/engine-bridge/tests/test_backup_ctl_deploy_config.py`（新） | S 包 | 10 |
| PT | promtool（本機 Docker） | `AgentConsole/docker/prometheus/tests/backup_alerts_test.yml`（新） | S 包 | 1 |
| GT | 審查閘（指令型 AT，不入單元測試） | SCG-4 通過標準的 G 編號指令 | 共同 | 7 |
| RM | 真機手動（掌舵者或主控；Windows＋Docker Desktop 全棧） | —（步驟見該 AT；PRD §11 的 V 系列） | 共同 | 5 |

### 3.2 AT 清單（依 FR；每列＝一個 AT）

Given（夾具）與 Then（判定）；R 條文對應見 R 條文表的 AT 欄與 §6 RTM。夾具名詞（`INFO_2REPO`、`OVERDUE_CASES`、`QUOTA_CASES`、mask 探針、假 runner、stub）定義於 §5。「階」欄為階段（一＝看、二＝控）。

#### FR-BK-01 的 AT　導覽與頁面骨架

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-01-1-1 | 一 | FN | `NAV_REGISTRY`（`lib/nav/registry.ts`）與 lucide-react 的 `Database`、`DatabaseBackup` 兩個圖示 | 長度恰 9；id 依陣列序為 dashboard、projects、import、execute、monitor、settings、self-improving、issues、sysadmin；`NAV_REGISTRY[6].id`＝self-improving、`[7].id`＝issues、`[8]` 即 sysadmin；sysadmin 各欄逐值：label「系統管理」、href `/sysadmin`、order 65、enabled true、mobile false、roles 缺（`undefined`）、`icon === Database`（不是 `DatabaseBackup`）；對 ADMIN、OPERATOR、VIEWER、`undefined` 四種角色的顯示序（`visibleNavEntries`）皆為 dashboard、projects、import、execute、monitor、issues、settings、sysadmin、self-improving；九個 `order` 唯一（`Set` 大小 9）、九個 `icon` 互異（`Set` 大小 9） |
| AT-BK-01-1-2 | 一 | FN | 既有導覽測試已依 §5.7 同步（`issues-nav.test.ts`、`registry.test.ts`、`ToolsRegion.test.tsx` 三檔） | 三檔全綠（零測試＝失敗）：`npx vitest run lib/nav components/layout/ToolsRegion.test.tsx`；`AT_950_10_E_1` 的標題改述為「原八列不變，另加系統管理」；`issues-nav.test.ts` 的 `NAV_REGISTRY[7]` 斷言仍在、且 `:19` 的 id 清單與 `:27` 的顯示序已含 sysadmin |
| AT-BK-01-1-3 | 一 | GT | G-C5：既有測試檔的 diff（`git diff -U0 <base> --` §5.7 前端同步鎖列所列檔） | 每個 hunk 只動釘值或預期清單（長度 8→9、id 清單、顯示序、order 與 icon 集合大小、href 清單、`links` 索引）；被刪的 `expect`、`assert` 行＝0；`registry.ts` 的檔頭註解「八項」→「九項」 |
| AT-BK-01-1-E-1 | 一 | FN | 原八列的逐欄快照（沿 `issues-nav.test.ts:36-70` 的 `snapshot`：id、label、order、enabled、mobile、roles、無專案與有專案兩種 href）與代表路徑探針 | `NAV_REGISTRY.slice(0,8)` 逐欄等於快照（含 issues 的 order 55、self-improving 的 order 70、mobile false）；match 探針：`/sysadmin`、`/sysadmin/backup`、`/sysadmin/x` 的 active 為 sysadmin；`/sysadmin-x`、`/system`、`/sysadmin_backup` 為 null；`/issues`、`/self-improving` 仍各自 active、不被 sysadmin 吃掉；沒有任何路徑被兩項同時命中 |
| AT-BK-01-2-1 | 一 | FH | `SysAdminHome`（`/sysadmin` 的入口頁）；`GET /api/v1/sysadmin/backups` 的 mock 回應：`cards[0]`（全備）為 succeeded、`finishedAt` 為固定時間；分別以 ADMIN、OPERATOR、VIEWER 登入 | 三種角色皆渲染 `data-testid=sysadmin-card-backup`：標題「資料庫備份」、一句說明（非空）、「最近全備」摘要＝狀態文字「成功」與 `formatDateTime(finishedAt)`；卡片是連結，href 為 `/sysadmin/backup`；入口頁只有這一張卡 |
| AT-BK-01-2-2 | 一 | FN | `visibleNavEntries(NAV_REGISTRY, role)` 與 `activeNavEntry`，角色取 ADMIN、OPERATOR、VIEWER | 三種角色的可見項皆含 sysadmin（label「系統管理」）；`activeNavEntry(visible, "/sysadmin")`、`(visible, "/sysadmin/backup")` 的 id 皆為 sysadmin（其餘八項皆不 active） |
| AT-BK-01-2-3 | 一 | FH | 入口卡的最近全備摘要：`cards[0].status` 分別為 failed、no_run（從未執行）、`control.reason=export_unreadable`（`cards` 為 null）；另 `GET` 失敗（網路錯誤） | failed→摘要文字為「失敗」（`data-tone=danger`）；no_run→「從未執行」；`cards` 為 null 或請求失敗→摘要文字為「—」並帶原因文字；任何情況都不顯示「成功」或數字 0 |
| AT-BK-01-2-4 | 一 | FP | **條件列（PRD §9.4 條件列、D-BK-10 (i)）：僅當實作基底已存在 `AgentConsole/frontend/lib/help/registry.ts`（每頁說明案先落地）時適用**；實作棒開工先以 `Test-Path` 判定，不存在即本 AT 不適用（改由每頁說明案實作時納入，以其 TCS 為準）。判定指令：`npx vitest run lib/help`（工作目錄 `AgentConsole\frontend`）。`lib/help/sysadmin.ts`、`lib/help/sysadmin-backup.ts` 兩個說明項（id 等於檔名，內容依每頁說明案的 AC-PH-03-5 結構）與 `HELP_ROUTES` 的兩個鍵 `/sysadmin`、`/sysadmin/backup` | 每頁說明案的三條鎖保持綠：AC-PH-03-1（`app/**/page.tsx` 路由集合＝`HELP_ROUTES` 鍵，`Console_PageHelp_PRD.md:89`；其 AT 為 `TCS-PageHelp-20261027.md` 的 AT-PH-03-1-1）、AC-PH-03-2（`enabled` 導覽項的 `href` 皆解析到說明項，`:90`）、AC-PH-03-4（頁檔 id 集合＝`HELP_PAGES`∪`PENDING_HELP_PAGES`，`:92`；AT-PH-03-4-1）；`helpForPath("/sysadmin")` 與 `helpForPath("/sysadmin/backup")` 各解析到恰一個說明 id；內容可先入 `PENDING_HELP_PAGES`，此時須**同 commit 上修** `lib/help/registry.test.ts` 檔頂的 `PENDING_CEILING`（每頁說明案 D-PH-14：上修只准姊妹案重填、並於 PR 說明 WHY；AT-PH-03-6-1） |
| AT-BK-01-2-E-1 | 一 | FH | `useAuth()` 的 status 為 `anon`（值域 `loading`｜`authed`｜`anon`，`lib/auth/AuthProvider.tsx:19`；`loading` 另跑一次）；以 `msw` 或 fetch 替身記錄所有請求 | `SysAdminHome` 與 `BackupView` 皆不渲染 `sysadmin-card-backup`、不渲染任何備份資料；對 `/api/v1/sysadmin/` 的請求數＝0（`useEnabled` 閘；沿 `queries.ts` 既有 hook 慣例）；登入閘的導向仍由 `AuthProvider` 負責（本檔不新增第二套） |
| AT-BK-01-2-E-2 | 一 | E2 | Playwright mock：以 VIEWER 登入，route mock `GET /api/v1/sysadmin/backups` | 左列有「系統管理」且點擊後網址為 `/sysadmin`；再點入口卡進 `/sysadmin/backup`；左列 active 為「系統管理」（`aria-current`）；頁面無任何寫入請求（沒有 POST、PUT、DELETE） |
| AT-BK-01-3-1 | 一 | FT | `ToolsRegion.test.tsx`（既有檔，新增一個 `it`）：以真實登記表渲染 Tools 區 | 九個連結皆在 DOM；帶 `max-md:hidden` 的恰為「自我進化」「議題中心」「系統管理」三項，其餘六項不帶；每個連結的 `aria-label` 與 `title` 恆等於其 label；`ToolsRegion.tsx` 本身零差異（G-C3） |
| AT-BK-01-3-E-1 | 一 | FN | `NAV_REGISTRY.filter(e => e.mobile)` | 長度恰 6、id 依序為 dashboard、projects、import、execute、monitor、settings；sysadmin 的 `mobile === false` |

#### FR-BK-02 的 AT　備份清單

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-02-1-1 | 一 | BQ | export 夾具：`info.json`＝§5.1 的 `INFO_2REPO`（F-03：repo1、repo2 各一份全備與一份差異，共 4 份，差異的 `prior` 為同 repo 全備）；`logical.json` 兩個物件（`aisdlc-20261025-183000.dump`、`aisdlc-20261026-183000.dump`）；ADMIN 呼叫 `GET /api/v1/sysadmin/backups` | `data.backups` 恰 6 筆，依 `finishedAt` 嚴格新到舊；每筆鍵齊（kind、label、location、startedAt、finishedAt、durationSeconds、databaseSizeBytes、repoSizeBytes、baseLabel、result）；差異備份 `baseLabel` 等於夾具 `prior`、其餘為 null；`location` 依 `database.repo-key` 為 repo1／repo2、邏輯備份為 logical；`durationSeconds`＝`timestamp.stop − timestamp.start`；`databaseSizeBytes`＝`info.size`、`repoSizeBytes`＝`info.repository.size`；邏輯備份的 `startedAt`、`durationSeconds`、`databaseSizeBytes`、`baseLabel` 為 null、`finishedAt`＝`modified`、`repoSizeBytes`＝`size`；所有時間為帶 `Z` 的 ISO-8601 |
| AT-BK-02-1-2 | 一 | FV | `BackupView` 取 API 回應（`backups` 為 AT-BK-02-1-1 同形的 6 筆，另加一筆 kind=incr） | 「備份清單」分頁表頭依序為 類型｜標籤｜儲存位置｜開始｜結束｜耗時｜資料庫｜備份｜基準｜結果；類型文字：full→全備、diff→增備（差異）、incr→增量、logical→邏輯備份；儲存位置：repo1→本地 repo1、repo2→離站 repo2、logical→離站邏輯；非差異的「基準」欄文字為「—」；列序與 API 回應序完全相同（前端不另排序） |
| AT-BK-02-1-E-1 | 一 | BQ | 同 AT-BK-02-1-1，但夾具列的檔案順序故意打亂（info.json 備份陣列依標籤字母序、logical.json 依大小序）；另一夾具兩份備份的 `timestamp.stop` 相同 | 輸出仍依 `finishedAt` 新到舊；`stop` 相同者依 `label` 字典序降冪穩定排列（同一輸入兩次呼叫結果逐位元相同）；kind 為 `incr` 的夾具列輸出 kind＝incr（不被歸成 diff） |
| AT-BK-02-1-R-1 | 一 | ES | 真機 V2：同一次全棧；Playwright（stack 載具）取頁面「備份清單」列，並以 `docker compose exec -T pgbackrest pgbackrest --stanza=aisdlc --output=json --log-level-console=off info`（唯讀）取真值 | 清單列的標籤集合、類型、結束時間、大小與 `info` 逐份相符（4 份＋離站邏輯備份物件數與 `mc ls`／MinIO 資料目錄一致） |
| AT-BK-02-2-1 | 一 | BQ | `INFO_2REPO` 的 repo1 差異備份加 `error:true`，其餘 `error:false`；另一份夾具完全沒有 `error` 鍵 | `error:true` 那筆 `result`＝`ok_with_errors`，其餘 `ok`；缺 `error` 鍵者視為 `ok`；`backups` 不含任何失敗狀態項（結果值域只有 ok、ok_with_errors） |
| AT-BK-02-2-2 | 一 | FV | 兩筆資料：一筆 `ok_with_errors`、一筆 `ok` | 前者 `bk-result-<label>` 文字為「成功，但有校驗錯誤」且 `data-tone=warn`；後者文字恰為「成功」且 `data-tone=ok`；`bk-list-note` 的文字含「失敗的工作看狀態卡與工作紀錄」 |
| AT-BK-02-2-E-1 | 一 | FV | 只有 `ok` 的資料 | 畫面任何處都不出現「校驗錯誤」；`bk-list-note` 仍在（說明恆在，不因無錯誤而隱藏） |
| AT-BK-02-3-1 | 一 | FV | 一筆備份：`startedAt`、`finishedAt`、`durationSeconds`、`databaseSizeBytes`、`repoSizeBytes` 皆有值；`timezone`＝`Asia/Taipei` | 「開始」「結束」儲存格文字逐字等於 `formatDateTime(iso)`（`lib/format.ts`）的回傳；耗時等於 `formatDuration(sec)`（`lib/domain/metrics.ts`）；兩個大小欄等於 `formatBytes(n)`；分頁標題旁有文字含 `Asia/Taipei`（排程時區註記） |
| AT-BK-02-3-2 | 一 | FS | 靜態掃描 `components/domain/sysadmin/**` 與 `lib/domain/sysadminBackup.ts`（略過 `tests` 目錄與 `*.test.ts(x)`） | 沒有定義名為 `formatBytes`、`formatDuration`、`formatDateTime`、`formatClock` 的函式或常數（`function X`、`const X =`、`export { X }` 皆掃）；三者皆由 `@/lib/format` 或 `@/lib/domain/metrics` 匯入；掃描器自帶負控（對含 `function formatBytes` 的合成原始碼回非空） |
| AT-BK-02-3-E-1 | 一 | FV | 一筆資料的 `databaseSizeBytes`、`durationSeconds`、`startedAt` 為 null（邏輯備份形） | 對應儲存格文字恰為「—」；不出現「0 B」「0s」「Invalid Date」或空白 |
| AT-BK-02-4-1 | 一 | BQ | `INFO_2REPO` 改為：repo2 的 `status.code`＝99、`status.message`＝other（離站不可達）、repo2 沒有任何備份；repo1 正常 | `data.repos` 兩筆；repo2 的 `statusCode`＝99、`statusMessage`＝other；repo1 的 `statusCode`＝0；`data.backups` 只含 repo1 的備份（repo2 無項、不補佔位列）；HTTP 200、`control.reason` 為 null |
| AT-BK-02-4-2 | 一 | FV | 兩個 repo 區塊：repo1 正常（2 列）、repo2 的 `statusCode`＝99、`statusMessage`＝other | `bk-repo-status-2` 顯示「狀態碼 99」與中文說明（取 `REPO_STATUS_ZH[99]`）；repo1 區塊照常列出 2 列；整頁不出現「沒有備份」「尚無備份」字樣；repo2 區塊不顯示成空表 |
| AT-BK-02-4-E-1 | 一 | FL | `REPO_STATUS_ZH`（`lib/domain/sysadminBackup.ts`）與函式 `repoStatusText(code, message)` | 鍵集合恰為 {0,1,2,3,4,5,6,99}，每個值非空中文；code 77 或 -1 或 `NaN` 回含該數字的「其他」兜底文字、不丟例外；code 0 回「正常」（不顯示成狀態碼警示） |
| AT-BK-02-5-1 | 一 | BQ | `info.json` 為 stanza 存在但 `backup:[]`；`logical.json` 為 `ok:true`、`objects:[]`；沒有任何 `jobs/*.json` | `backups`＝`[]`；`cards` 四張皆 `status=no_run`、`never=true`、`overdue=false`、`latestBackup` 為 null；HTTP 200；`control.reason` 為 null（空備份是合法狀態，不是錯誤） |
| AT-BK-02-5-2 | 一 | FV | API 回應為 AT-BK-02-5-1 的形狀 | `bk-list-empty` 的文字恰為「尚無備份：首次部署後請立刻做第一份全備」；四張卡的徽章文字皆為「從未執行」；畫面不出現「0 B」「0 份」「0s」 |
| AT-BK-02-5-E-1 | 一 | BQ | `info.json` 的 `info` 為空陣列 `[]`（pgBackRest 尚無 stanza）而 `ok:true` | HTTP 200；`backups`＝`[]`、`repos`＝`[]`；`schedule.retention` 為 null 並帶 `control.warnings` 含 `retention_unavailable`（沒有 stanza 就沒有自報值，不填預設值） |
| AT-BK-02-6-1 | 一 | BS | 匯出 `info.json` 的 `repos` 由環境變數決定：`OFFSITE_S3_ENDPOINT` 依序為 `minio:9000`、`localhost:9000`、`127.0.0.1:9000`、`[::1]:9000`、`host.docker.internal:9000`、`s3.amazonaws.com`、`s3.ap-northeast-1.amazonaws.com:443`、`minio.example.internal:9000`；repo1 為 posix | repo1 固定 `{repo:1,type:"posix",endpoint_host:null,local:true}`；repo2 的 `endpoint_host` 為去掉埠號的主機名；`local` 依序為 true×5（`minio`、`localhost`、`127.0.0.1`、`[::1]`、`host.docker.internal`；後三者為 TCS 加嚴的回送位址，`[::1]` 的 `endpoint_host` 為去掉括號與埠的 `::1`）、false×3（`minio.example.internal` 含 `.` ⇒ false，即使它在內網） |
| AT-BK-02-6-2 | 一 | FV | 兩組 `repos` 夾具：A＝repo2 `{endpointHost:"minio", local:true}`；B＝repo2 `{endpointHost:"s3.amazonaws.com", local:false}`；每組各渲染一次，另帶「離站 pg_dump」卡（status=succeeded） | A：`bk-repo-badge-2` 文字含「本機 MinIO・與主機同碟，主機損毀時一併消失」；B：文字為「外部 S3」且不含「與主機同碟」；A 與 B 的徽章文字不同；A 的畫面任何處（含 dump 卡）不含「已安全」「離站已備」字樣，且 dump 卡同樣帶「與主機同碟」標示；repo1 固定顯示「本地」無 S3 徽章 |
| AT-BK-02-6-E-1 | 一 | BQ | BQ 夾具 `repos` 的 `local` 值直接來自匯出檔（`true`／`false`）；另一夾具 `local` 缺鍵 | API `repos[].local` 與匯出檔逐值相同（console-api 不重算）；`local` 缺鍵或非布林 ⇒ 視為 `schema_mismatch`（`control.reason`、全區塊 null；見 R-BK-25），不預設成 false（避免把本機 MinIO 呈現成外部） |

#### FR-BK-03 的 AT　排程與保留策略（唯讀）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-03-1-1 | 一 | FV | `schedule.json` 夾具六條：full `0 2 * * 0`、diff `0 2 * * 1-6`、dump `30 2 * * *`、verify `0 4 * * 3`、expire `0 3 * * *`、wal_clean `30 3 * * *`；`tz`＝`Asia/Taipei` | `bk-sched-<job>` 六列文字依序為：「每週日 02:00・全備」「每週一至週六 02:00・增備（差異）」「每日 02:30・離站 pg_dump」「每週三 04:00・驗證」「每日 03:00・清理過期備份（維護工作）」「每日 03:30・清理 WAL 複本（維護工作）」；每列另顯示原 cron 字串與 `Asia/Taipei`；另有固定列 `bk-sched-fixed-wal`：「WAL 持續歸檔（有寫入時約每 60 秒一段）」；expire 與 wal_clean 兩列帶「維護工作」，另四列不帶 |
| AT-BK-03-1-2 | 一 | FL | 純函式 `humanizeCron(cron)`（`lib/domain/sysadminBackup.ts`）的表驅動 | `0 2 * * 0`→「每週日 02:00」；`0 2 * * 1-6`→「每週一至週六 02:00」；`30 2 * * *`→「每日 02:30」；`0 4 * * 3`→「每週三 04:00」；`5 14 * * 6`→「每週六 14:05」；`0 0 * * *`→「每日 00:00」；星期對照 0 日、1 一、2 二、3 三、4 四、5 五、6 六；時與分一律補零到兩位 |
| AT-BK-03-1-E-1 | 一 | FV | `schedule.json` 只有四條工作列（缺 expire、wal_clean） | 只渲染四列加固定 WAL 列，不補出缺的兩列、不丟例外；`schedule` 為 null（匯出缺）時整個「排程與保留」分頁顯示原因文字（由 `control.reason` 決定），不顯示空表 |
| AT-BK-03-2-1 | 一 | FL | `humanizeCron` 的不認得形狀：`*/5 * * * *`、`0 2 1 * *`、`0 2 * 1 *`、`0 2 * * 1,3`、`0 2 * * MON`、`@daily`、空字串、`0 2 * * 1-6/2`、`60 2 * * *`、`0 24 * * *`、`0 2 * * 8`、`0 2 * * 6-1`（反向範圍）、`0 2 * *`（四欄）、`0 2 * * * *`（六欄）、`0 2 * * 7` | 每個輸入都回傳與輸入逐字相同的原字串（不 trim、不改大小寫），沒有任何一個丟例外、回 `undefined` 或回猜測的白話；`0 2 * * 7`（星期欄 7）同屬不認得（本版只認 0～6） |
| AT-BK-03-2-E-1 | 一 | FV | `schedule.json` 含一條 cron 為 `*/7 * * * *` 的 `dump` 列；以 `console.error` 間諜監看 | 該列文字顯示原表達式 `*/7 * * * *`（不含「每」字白話）；頁面其餘列照常；`console.error` 呼叫數＝0 |
| AT-BK-03-3-1 | 一 | BV | `BackupCron.next(cron, zone, now)`（`application/service/`：它用 Spring `CronExpression`，不得進 domain，ArchUnit A1）以 `Clock.fixed`：`now`＝2026-10-27T10:00:00+08:00（星期二），zone＝`Asia/Taipei`；六條 cron 同 AT-BK-03-1-1 | 回傳（UTC `Z`）：full→2026-10-31T18:00:00Z（星期日 11-01 02:00+08）、diff→2026-10-27T18:00:00Z、dump→2026-10-27T18:30:00Z、verify→2026-10-27T20:00:00Z（星期三 04:00+08）、expire→2026-10-27T19:00:00Z、wal_clean→2026-10-27T19:30:00Z；星期欄 0 夾具：`now`＝2026-10-31T10:00:00+08:00（星期六）→ full 為 2026-10-31T18:00:00Z；`now`＝2026-11-01T01:59:59+08:00 → 同日 02:00+08；`now`＝2026-11-01T02:00:00+08:00（恰為觸發時刻）→ 下一個為 2026-11-07T18:00:00Z（嚴格晚於 now） |
| AT-BK-03-3-2 | 一 | BQ | `BackupApiIT` 以可變專屬時鐘 `BackupClock`（§5.2；不換全域 `Clock`）設為 2026-10-27T10:00:00+08:00；`schedule.json` 的 `tz`＝`Asia/Taipei`；JVM 預設時區在 `@BeforeEach` 改為 `America/Los_Angeles`（`@AfterEach` 還原） | `data.schedule.entries[].nextRunAt` 六值同 AT-BK-03-3-1（ISO-8601 帶 `Z`）；JVM 預設時區改為 `Asia/Tokyo` 後再呼叫，六值不變（不隨 JVM 或瀏覽器時區改變）；`data.timezone`＝`Asia/Taipei`；全域 `Clock` 沒被換掉：`getBeansOfType(Clock.class)` 只有系統時鐘一個（不是 `MutableClock`），且專屬時鐘撥到 2026-11-02 後，以 `AbstractApiIT` 既有的 admin token 呼叫 `GET /backups` 仍 200（JWT、限流與審計吃全域 `Clock`；`SiWriteSeam.java:26-28` 先例） |
| AT-BK-03-3-E-1 | 一 | BQ | 三個夾具：(a) `tz` 改為 `UTC`；(b) 某條 cron 為 Spring 解析不了的 `0 2 * * 1-6/0`；(c) `tz` 為 `Mars/Base` | (a) diff 的 `nextRunAt`＝2026-10-28T02:00:00Z（以該時區計算，不沿用 `Asia/Taipei`）；(b) 該條 `nextRunAt` 為 null、其餘五條照常、`control.warnings` 含 `cron_unparsable:diff`、對應卡 `lastDueAt`＝null 且 `overdue=false`、HTTP 200；(c) `control.reason`＝`schema_mismatch`（時區不合法屬匯出檔內容不合），依 D-BK-T5 所有資料區塊（含 `timezone`、`schedule`）為 null，HTTP 200、不丟 500 |
| AT-BK-03-4-1 | 一 | BS | stub `pgbackrest help expire repo-retention-full` 與 `…-diff` 的輸出，三種形態（夾具取自 PRD F-07 的現查描述，**實作棒開工先唯讀實查真輸出並以真輸出校正夾具，差異走勘誤**）：(a) full 單值 `current: 4`、diff 逐 repo `current:` 之下 `repo1: 7`；(b) 兩者皆為逐 repo 列（repo1、repo2 各一）；(c) diff 輸出沒有 repo2 列；`LOGICAL_BACKUP_RETENTION_DAYS=28` | 匯出 `info.json.retention`：(a) `{repo1:{full:4,diff:7},repo2:{full:4,diff:null},logical_days:28}`；(b) 兩 repo 各取自己的值；(c) repo2.diff 為 null（未設）；單值形態套用到所有 repo；環境變數優先於 conf 的語意由「取 pgBackRest 自報值、不自行讀 conf」達成：夾具把 `pgbackrest.conf` 換成不同值時匯出值不變 |
| AT-BK-03-4-2 | 一 | BS | stub 輸出為不可解析：空輸出、非數字（`current: abc`）、`pgbackrest` 非零結束、輸出含多個互相矛盾的 `current:` | `retention` 為 JSON `null`（不是物件、不填預設值 4／7）；其餘匯出內容（備份清單、repos）照常寫出；匯出行程結束碼 0 |
| AT-BK-03-4-3 | 一 | FV | `schedule.retention`＝`{repo1:{full:4,diff:7},repo2:{full:4,diff:null},logicalDays:28}` | `bk-retention` 文字恰為「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」；repo1.diff 為 null 時該段顯示「差異 未設」；`logicalDays` 為 null 時顯示「邏輯備份 —」 |
| AT-BK-03-4-E-1 | 一 | BQ | `info.json.retention` 為 null；另一夾具 `retention` 缺鍵 | `data.schedule.retention` 為 null（缺鍵亦然），`control.warnings` 含 `retention_unavailable`；`schedule.entries` 不受影響；HTTP 200；FV：`bk-retention` 文字為「—」，不出現數字 4、7、28 |
| AT-BK-03-4-E-2 | 一 | FV | 「排程與保留」分頁的整個 DOM 子樹，ADMIN 登入 | 子樹內沒有 `input`、`textarea`、`select`、可編輯元素（`contenteditable`），沒有名稱含「編輯」「儲存」「修改」「套用」的按鈕；沒有任何 PUT、PATCH、DELETE 請求被發出（fetch 替身記錄）；即使 ADMIN 亦然（保留與排程唯讀，R7） |

#### FR-BK-04 的 AT　最近狀態卡（全備、增備、離站 pg_dump、驗證）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-04-1-1 | 一 | BQ | export 夾具：`INFO_2REPO`；`jobs/full.json`（last：trigger=scheduled、status=succeeded、rc=0、started_at＝2026-10-26T18:00:00Z、finished_at＝2026-10-26T18:10:00Z；last_success_at＝同 finished_at）、`jobs/diff.json`（成功）、`jobs/dump.json`（成功）、沒有 `jobs/verify.json`；ADMIN 呼叫 | `data.cards` 恰 4 筆且依序為 job＝full、diff、dump、verify；前三筆 `status=succeeded`、`trigger=scheduled`、`startedAt`、`finishedAt`、`durationSeconds`（＝600）、`lastSuccessAt` 逐值對得上夾具；verify 為 `status=no_run`、`trigger` 與時間欄為 null、`never=true`；`latestBackup` 只在 full 與 diff 卡為物件（`{label, finishedAt, source:"pgbackrest"}`，full 取全備、diff 取差異或全備中最近者），dump 與 verify 卡該鍵缺席或為 null（不得為物件） |
| AT-BK-04-1-2 | 一 | FV | `cards` 表驅動五種狀態：succeeded、failed、running、interrupted、no_run（各一張卡） | `bk-badge-<job>` 文字依序為「成功」「失敗」「進行中」「中斷」「從未執行」，`data-status` 為對應值；每個徽章內含一個 `svg`（Lucide 圖示，`aria-hidden`）——文字加圖示，不得只有顏色；每張卡顯示最近一次執行的觸發（排程／手動）、開始時間（`formatDateTime`）、耗時（`formatDuration`）與「最近一次成功」 |
| AT-BK-04-1-E-1 | 一 | BQ | F-04 形：`jobs/full.json` 缺席（job-run.sh 尚未跑過全備），但 `INFO_2REPO` 有 `20261026-020000F`（repo1 停於 2026-10-25T18:10:00Z、repo2 停於 2026-10-25T18:12:00Z） | `cards[0]`：`status=no_run`、`trigger` 為 null、`never=false`（成功時間取自清單）、`lastSuccessAt`＝2026-10-25T18:10:00Z（各 repo 最近全備的**最舊者**，D-BK-T10）、`latestBackup.label`＝`20261026-020002F`、`latestBackup.finishedAt`＝2026-10-25T18:12:00Z、`latestBackup.source`＝`pgbackrest`（「最近一份」＝各 repo 最近者中 `stop` 最大者，與 `lastSuccessAt` 的「最舊者」語意不同，D-BK-T9）；FV：卡片徽章「從未執行」，同時顯示「最近一份備份：20261026-020002F」與「來源：pgBackRest 清單」——不得只顯示「從未執行」 |
| AT-BK-04-1-E-2 | 一 | FS | 靜態掃描 `components/domain/sysadmin/**`（略過 tests、`*.test.tsx`） | 沒有 `dangerouslySetInnerHTML`、沒有 Markdown 渲染器匯入（`react-markdown`、`marked`、`remark`）；輸出尾段與 reason 文字只以文字節點渲染；掃描器自帶負控 |
| AT-BK-04-1-R-1 | 一 | RM | 真機 V1：全棧運轉、sidecar 已跑過至少一次備份；掌舵者以 ADMIN 開 `/sysadmin/backup` | 不開終端機、不看英文，答得出四題：昨晚備份成功了嗎、最近一份全備是何時、離站有沒有備到、備份真的還原得起來嗎（驗證卡）；本機 MinIO 的離站標示「與主機同碟」 |
| AT-BK-04-2-1 | 一 | BQ | `jobs/dump.json`：last＝{trigger:scheduled, status:failed, rc:1, reason:script_failed, started_at＝2026-10-27T18:30:00Z, finished_at＝2026-10-27T18:30:40Z}、`last_success_at`＝2026-10-26T18:30:30Z；ADMIN 呼叫 | `cards[2]`：`status=failed`、`reason=script_failed`、`lastSuccessAt`＝2026-10-26T18:30:30Z（失敗不覆蓋較早的成功）、`finishedAt`＝2026-10-27T18:30:40Z |
| AT-BK-04-2-2 | 一 | FV | dump 卡為 failed 且 `lastSuccessAt` 有值，`detailTail`＝"line1\nline2"；分別以 ADMIN、OPERATOR 渲染 | 兩者皆：徽章 `data-tone=danger`、`bk-last-success-dump` 文字為「最近一次成功：」加 `formatDateTime(lastSuccessAt)`；ADMIN 另有 `bk-tail-dump` 顯示輸出尾段文字；OPERATOR 的 DOM 內沒有 `bk-tail-dump` |
| AT-BK-04-2-E-1 | 一 | FV | dump 卡為 failed 且 `lastSuccessAt` 為 null（從未成功） | `bk-last-success-dump` 文字為「最近一次成功：從未成功」；徽章仍為失敗色；不出現任何時間字串 |
| AT-BK-04-3-1 | 一 | BV | `BackupOverdue.evaluate(job, cron, zone, now, grace=30 分, stateSuccess, repoLatest[], running)`（純函式；`repoLatest[]`＝各已設定 repo 的最近符合備份 `stop`、缺席者為 null；`now` 取自 `Clock.fixed`；cron 同 AT-BK-03-1-1）；§5.5 的 `OVERDUE_CASES` 全部列（每列含 now、job、stateSuccess、各 repo 清單時間、running 與期望的 `lastDueAt`、`overdue`、`never`） | 每一列的 `lastDueAt`、`overdue`、`never` 逐列等於表中期望值；其中必含的邊界：週六 04:00（增備週六 02:00 成功）不逾期、週日 04:00（增備無週日時段，全備週日 02:00 成功）不逾期、週一 02:15 不逾期、週一 02:31 增備逾期、週日 02:31 全備逾期、寬限邊界 `now = lastDueAt + 30 分整` 為 false、`+30 分 1 秒` 為 true、`now = lastDueAt` 為 `lastDueAt = now` 且 false、`running=true` 為 false、無任何成功為 `never=true` 且 `overdue=false`、清單端取「各 repo 最近一份的最舊者」（兩 repo 一新一舊時取舊；某 repo 完全沒有符合的備份時清單端缺席） |
| AT-BK-04-3-2 | 一 | BQ | `BackupApiIT` 可變專屬時鐘＝2026-11-02T02:31:00+08:00（週一）；export 夾具同 `OVERDUE_CASES` 的 O5（diff、狀態檔成功停在週六、清單最新差異為週六） | `cards[1]`（diff）：`overdue=true`、`lastDueAt`＝2026-11-01T18:00:00Z、`never=false`；把 Clock 改為 02:15 後 `overdue=false`；把 diff 的 `jobs/diff.json` 改為 running 且心跳 `lock_held=true` 後 `overdue=false`、`status=running`；整個 `cards` 的 `lastDueAt` 皆為 UTC `Z` |
| AT-BK-04-3-3 | 一 | FS | 靜態掃描 `components/domain/sysadmin/**` 與 `lib/domain/sysadminBackup.ts` | 沒有 cron 解析函式庫的匯入（`cron-parser`、`croner`、`cronstrue`、`node-cron`）、沒有識別字含 `grace`（不分大小寫）、沒有以 `lastDueAt` 做算術或比較（`overdue` 只作為 `card.overdue` 讀取並顯示；沒有寫入 `overdue` 的指派）；掃描器自帶負控 |
| AT-BK-04-3-E-1 | 一 | BQ | 同 AT-BK-04-3-2 的 export，但 `schedule.json` 的 diff cron 為 Spring 解析不了的形狀 | `cards[1].lastDueAt` 為 null、`overdue=false`、`control.warnings` 含 `cron_unparsable:diff`；不丟 500、不把「算不出」當成逾期（算不出＝量不到，不是 true） |
| AT-BK-04-3-E-2 | 一 | BA | `BackupArchTest`：掃描 `application/service/Backup*`（含 `BackupCron`、`BackupOverdue`）與 `domain/model/backup/**` 的原始碼（去註解） | 沒有 `Instant.now()`、`LocalDateTime.now()`、`ZonedDateTime.now()`、`OffsetDateTime.now()`、`System.currentTimeMillis()`、`Clock.systemUTC()`、`Clock.systemDefaultZone()`、`ZoneId.systemDefault()`、`TimeZone.getDefault()`（時間一律取自注入的 `BackupClock`、時區一律取自 `schedule.json.tz`）；掃描函式自帶負控（對含 `Instant.now()` 的合成樣本回非空） |
| AT-BK-04-4-1 | 一 | BS | `export/jobs/full.json` 的 `last.status` 為 `running`、`finished_at` 為 null；沒有任何行程持有維護鎖檔（無活的 `flock` 持有者）；執行 `backup-ctl-export.sh`（每輪匯出前先掃一次狀態檔） | 該檔改寫為 `last.status="interrupted"`、`last.reason="interrupted"`、`last.finished_at` 為非 null 的 ISO-8601 `Z`；`last_success_at` 保持不變；寫入為原子（`.tmp` 後改名） |
| AT-BK-04-4-2 | 一 | BQ | `jobs/full.json` 為 `running`（`started_at` 為 clock−60 秒）；心跳 `lock_held=false` 且 `ts` 新鮮（age 5 秒，晚於 `started_at`） | `cards[0].status=interrupted`（console-api 防禦性導出）；`activeJob` 為 null（中斷的工作不算進行中，`overdue` 的「進行中豁免」不適用，照一般規則判定） |
| AT-BK-04-4-E-1 | 一 | BQ | 四個夾具：(a) `running` 且 `lock_held=true` 且心跳新鮮；(b) `running` 且心跳過期（age 100 秒）；(c) `succeeded` 且 `lock_held=false`；(d) `running`（`started_at`＝clock−2 秒）、心跳 `ts`＝clock−4 秒（早於 `started_at`）且 `lock_held=false` | (a) 保持 `status=running`、`activeJob.status=RUNNING`；(b) 保持 `running`（鎖資訊過期、不能斷言中斷），`control.reason=runner_offline`；(c) 不變為 interrupted；(d) 保持 `running`（心跳早於工作開始＝鎖資訊過時，不能斷言中斷） |
| AT-BK-04-5-1 | 一 | BQ | `jobs/dump.json` 的 last 含 `detail_tail`＝"CANARY-TAIL-7f3a failed"；分別以 VIEWER、OPERATOR token 呼叫 `GET /backups` | 遞迴掃描整個回應 JSON：所有名為 `detailTail`、`requestedBy` 的鍵，其值皆為 null 或鍵不存在；整段回應文字不含 `CANARY-TAIL-7f3a`；HTTP 200；`cards` 其餘欄位（狀態、時間、`lastDueAt`、`overdue`）與 ADMIN 回應逐值相同 |
| AT-BK-04-5-2 | 一 | BQ | 夾具改為 `detail_tail` 2500 字元（前段以 `PAD-HEAD` 填充、末尾含 `CANARY-TAIL-7f3a`）；ADMIN 呼叫 | `cards[2].detailTail` 恰為遮罩後文字的**最後** 2000 字元：含 `CANARY-TAIL-7f3a`、不含 `PAD-HEAD`、長度恰 2000 |
| AT-BK-04-5-3 | 二 | BQ | 以 JDBC 直接插入一列 RUNNING 的 `console.backup_jobs`（`requested_by`＝"CANARY-REQ-9c1e"、`detail`＝"CANARY-DET-4b2d"）；心跳新鮮、`lock_held=true`；VIEWER、OPERATOR、ADMIN 各呼叫 `GET /backups` | VIEWER、OPERATOR：`activeJob` 的 `requestedBy` 為 null 或缺席，整段回應文字不含 `CANARY-REQ-9c1e`、`CANARY-DET-4b2d`；ADMIN：`activeJob.requestedBy`＝`CANARY-REQ-9c1e` |
| AT-BK-04-5-E-1 | 二 | BQ | 同上 DB 列；非 ADMIN 對 `GET /backups/jobs` 與 `GET /backups/jobs/{id}` | `items[].requestedBy`、`items[].detail`、單筆的同名欄位皆為 null 或缺席（與 07-2 同規則）；回應文字不含兩個 canary |
| AT-BK-04-6-1 | 一 | BQ | `BackupApiIT` 對真 PostgreSQL（Testcontainers）：`WalArchiveStatsAdapter` 以應用連線讀 `pg_stat_archiver`；全新容器 `failed_count=0`、`last_archived_time`／`last_failed_time` 為 NULL | `data.walArchive`＝`{failedCount:0, lastArchivedAt:null, lastFailedAt:null}`（真實的零，不是「查不到」）；`control.warnings` 不含 `db_unavailable`；SQL 只有一條唯讀 SELECT（由 AT-BK-04-6-E-1 鎖住） |
| AT-BK-04-6-2 | 一 | BV | `BackupServiceTest`：**真實的** `WalArchiveStatsAdapter` 接「`JdbcTemplate` 替身」（覆寫查詢，依序：回 `{failed:0, lastArchived: T, lastFailed: null}`、回 `{failed:3, lastArchived: T, lastFailed: T+5min}`、丟 `DataAccessResourceFailureException`、丟 `IllegalStateException`）；其餘埠為假實作；心跳新鮮、有一個 `running` 工作且 `lock_held=true` | 前兩個依序映射為 `walArchive` 物件且欄位逐值相同；後兩個 `walArchive` 為 null（不是 0 計數的物件；adapter 吞例外回零物件即紅）、`control.warnings` 含 `db_unavailable`、其餘區塊（cards、backups、schedule、repos）完整、不丟例外；**僅 walArchive 失敗時** `control.canTrigger` 與 `activeJob` 與第一案逐值相同（不受影響） |
| AT-BK-04-6-3 | 一 | FV | `walArchive` 三形：(a) `{lastArchivedAt:T, failedCount:0, lastFailedAt:null}`；(b) `{lastArchivedAt:T, failedCount:3, lastFailedAt:T+5 分}`；(c) null | `bk-wal-line`：(a) 文字為「WAL 歸檔：最近 <formatDateTime(T)>・失敗 0 次」、`data-tone=ok`；(b) 含「失敗 3 次」與最近失敗時間、`data-tone=danger`；(c) 文字恰為「WAL 歸檔：—」，不出現「失敗 0 次」；三者皆為單行唯讀（沒有按鈕、輸入） |
| AT-BK-04-6-E-1 | 一 | BA | `BackupArchTest`：掃描 `WalArchiveStatsAdapter` 原始碼（去註解） | SQL 敘述恰一條、為 `SELECT … FROM pg_stat_archiver`、不含 INSERT／UPDATE／DELETE／TRUNCATE／`pg_` 其他系統函式呼叫；`pg_stat_archiver` 只出現在該一個類別；掃描函式自帶負控（對含第二條敘述或 UPDATE 的合成樣本回非空） |

#### FR-BK-05 的 AT　控制面健康與資料新鮮度（fail-loud）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-05-1-1 | 一 | BU | `BackupApiUnconfiguredIT`（共用預設 Spring context：沒有任何 `console.backup.*` 設定）；VIEWER、OPERATOR、ADMIN 各呼叫 `GET /api/v1/sysadmin/backups` | 三者 HTTP 200；`data.control`＝`{available:false, canTrigger:false, reason:"not_configured", heartbeatAgeSeconds:null, exportAgeSeconds:null, exportGeneratedAt:null, warnings:[]}`；`cards`、`backups`、`schedule`、`repos`、`walArchive`、`activeJob`、`timezone` 全為 null（不是 `[]` 或 0） |
| AT-BK-05-1-2 | 二 | BU | 同 context；ADMIN 對 `POST /api/v1/sysadmin/backups/jobs` 送 `{type:"full",confirm:true}` | HTTP 503、`reason=backup_control_unavailable`、無 `data`；`console.backup_jobs` 零列（階段二表存在時）；沒有檔案被寫出 |
| AT-BK-05-1-3 | 一 | FV | API 回應 `control.available=false`、`reason=not_configured`、其餘區塊 null | 整頁只顯示 `bk-reason-panel`：文字「備份控制面未設定（不在 Docker 全棧）」；沒有 `bk-cards`、`bk-list`、分頁內容；沒有任何數字 0、「0 份」或空表；手動操作按鈕（階段二）皆 `disabled` |
| AT-BK-05-1-E-1 | 二 | BV | `BackupServiceTest`：`BackupSettings` 假實作（`exportDir=@TempDir`、`requestDir=null`；服務層只認 `application/port/out/BackupSettings` 埠、不碰 `infrastructure` 的 `BackupProperties`，ArchUnit A2、A5）與一份新鮮的匯出夾具、新鮮心跳、DB 可用 | 概覽照常（`control.available=true`、cards 與 backups 非 null）；`control.canTrigger=false`；`BackupJobService.trigger` 丟「控制面不可用」領域例外（對應 503 `backup_control_unavailable`），不建列、不寫檔；`requestDir` 有設但 `exportDir` 未設時概覽為 `not_configured`、POST 亦 503（GET 只依 export-dir，POST 另依 request-dir） |
| AT-BK-05-1-E-2 | 一 | BV | `BackupServiceTest`：`BackupSettings.exportDir=null`；假 `BackupControlPort` 的讀取會回「`schema_rev=2` 加截斷 JSON」的壞快照，並記錄讀取次數 | `control.reason=not_configured`、全部資料區塊為 null；假埠讀取次數＝0（優先序 `not_configured`＞`schema_mismatch`＞`export_unreadable`＞`runner_offline`，D-BK-T5） |
| AT-BK-05-2-1 | 一 | BQ | `BackupApiIT` 可變專屬時鐘 固定；export 檔齊全；心跳 `ts` 分別為 clock−30 秒、clock−31 秒、檔案缺席 | age 30：`control.reason` 為 null、`heartbeatAgeSeconds=30`；age 31：`reason=runner_offline`、`heartbeatAgeSeconds=31`、`canTrigger=false`、HTTP 200、`backups`／`cards` 等區塊仍為已知資料（非 null）；缺席：`reason=runner_offline`、`heartbeatAgeSeconds` 為 null；三者 `activeJob` 規則不變 |
| AT-BK-05-2-2 | 一 | FV | `control.reason=runner_offline`、`heartbeatAgeSeconds=95`；另一組 `heartbeatAgeSeconds=null` | 出現 `bk-banner-offline`（`role="alert"`）：文字「備份控制面無回應（上次心跳 95 秒前）」；null 時為「備份控制面無回應（尚未收到心跳）」；資料區有 `bk-stale-mark` 文字「可能已過期」；階段二：三顆手動按鈕皆 `disabled` |
| AT-BK-05-2-3 | 二 | BQ | 心跳過期（age 31 秒）；ADMIN 對 POST 送合法 body | HTTP 503、`reason=backup_control_unavailable`；零列、零檔案 |
| AT-BK-05-2-E-1 | 一 | BQ | 心跳新鮮（age 3 秒）、`lock_held=true`、`jobs/full.json` 為 running（工作進行中） | `control.reason` 為 null（進行中的工作不是離線的藉口，也不會讓心跳變舊）；同夾具心跳 age 31 秒時仍為 `runner_offline`（進行中不豁免） |
| AT-BK-05-2-R-1 | 一 | ES | 真機 V5 之二：`docker compose stop pgbackrest` 後開備份頁（階段二：按鈕亦停用）；再 `docker compose start pgbackrest` | 停止後 ≤60 秒出現紅橫幅（`role=alert`）且資料標示可能已過期；啟動後橫幅消失、資料恢復；停止期間 GET 仍 200（回已知資料） |
| AT-BK-05-3-1 | 一 | BQ | 表驅動損毀夾具（逐項各一次、單一故障）：info.json 的 `schema_rev` 為 2；`schema_rev` 為字串 "1"；缺 `schema_rev` 鍵；info.json 內容為被截斷的 JSON；logical.json 的 `schema_rev` 為 2；schedule.json 為空檔案；`jobs/dump.json` 內容為 `[]`（頂層型別不對）；heartbeat 內容為非 JSON；heartbeat 的 `schema_rev` 為 2 | schema 類（第一～三、五、七、九項）：`control.reason=schema_mismatch`；損毀類（第四、六、八項）：`control.reason=export_unreadable`；每一項皆 HTTP 200，且 `cards`、`backups`、`schedule`、`repos`、`walArchive`、`activeJob` 全為 null（不顯示部分資料）；`control.canTrigger=false`；兩類並存與優先序見 AT-BK-05-3-E-2 |
| AT-BK-05-3-2 | 一 | FV | `control.reason` 分別為 schema_mismatch、export_unreadable，區塊皆為 null | `bk-reason-panel` 文字分別含「匯出檔格式版本不符」「匯出檔無法讀取」；不渲染任何表格、卡片；不出現「尚無備份」、不出現數字 0（避免被讀成「沒有備份」） |
| AT-BK-05-3-E-1 | 一 | BQ | `info.json` 與 `logical.json` 的 `ok:false` 兩種夾具（匯出行程回報失敗，檔案本身合法） | info `ok:false`：`control.warnings` 含 `info_unavailable`、`repos` 為 null、`backups` 只含邏輯備份項、各卡 `latestBackup` 為 null、`schedule.retention` 為 null；logical `ok:false`：`warnings` 含 `logical_unavailable`、`backups` 只含 pgBackRest 項；兩者 `control.reason` 為 null；FV 以提示條說明缺的來源（不靜默只顯示一半） |
| AT-BK-05-3-E-2 | 一 | BQ | 合併損毀夾具（各一次）：(a) info.json 的 `schema_rev`＝2 且 logical.json 為截斷 JSON；(a2) 反序：info.json 為截斷 JSON 且 logical.json 的 `schema_rev`＝2；(b) info.json 為截斷 JSON 且心跳 age 100 秒；(c) schedule.json 的 `schema_rev`＝2 且心跳檔缺席 | (a)(a2) `schema_mismatch`（兩類並存，與讀檔先後無關，schema 優先）；(b) `export_unreadable`（不是 `runner_offline`：資料損毀先於心跳）；(c) `schema_mismatch`（不是 `runner_offline`）；各案皆 HTTP 200、全部資料區塊為 null、`canTrigger=false` |
| AT-BK-05-4-1 | 一 | BQ | `info.json.generated_at`＝clock−180 秒、clock−181 秒；心跳新鮮 | `control.exportAgeSeconds` 分別為 180、181；`control.exportGeneratedAt` 為該 `generated_at`（ISO `Z`）；`control.reason` 皆為 null（匯出舊不改變 reason） |
| AT-BK-05-4-2 | 一 | FV | `exportAgeSeconds` 為 180、181；`exportGeneratedAt`＝2026-10-27T06:39:08Z（以本機時區顯示） | 兩者皆顯示「資料更新於 <formatClock(exportGeneratedAt)>」；181 者另有「已過期」標記（`bk-stale-mark`），180 者沒有 |
| AT-BK-05-4-E-1 | 一 | FV | `exportAgeSeconds` 為 null 但 `reason` 為 null（防禦：不應發生） | 不顯示「已過期」、不丟例外；時間文字為「資料更新於 —」 |
| AT-BK-05-5-1 | 二 | BQ | `BackupApiIT`：以資料庫層故障注入讓 `console.backup_jobs` 暫時不存在（`alter table … rename`，`finally` 與 `@AfterEach` 皆還原；沿 `IssueApiIT` 作法）；export 檔齊全且心跳新鮮、`jobs/full.json` 為 running 且 `lock_held=true` | GET HTTP 200；`control.warnings` 含 `db_unavailable`；`cards`、`backups`、`schedule`、`repos` 為檔案面資料（非 null）；`activeJob` 只取自匯出鎖狀態（`{type:"full", status:"RUNNING", trigger:"scheduled", id:null}`），不含 DB 欄位；`control.canTrigger=false`；POST 回 503 `backup_control_unavailable` |
| AT-BK-05-5-E-1 | 二 | BV | `BackupServiceTest`：`BackupJobRepository` 假實作的 `findActive()` 丟 `DataAccessException`；`WalArchiveStatsPort` 正常 | 概覽不丟例外；`warnings` 含 `db_unavailable`；`activeJob` 只由匯出鎖狀態導出；`walArchive` 仍為物件（兩個 DB 讀取獨立降級，互不連坐） |

#### FR-BK-06 的 AT　手動觸發（全備、增備、驗證；僅 ADMIN）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-06-1-1 | 二 | FL | 純函式 `retentionQuota(type, repoBackups, retention)`（`lib/domain/sysadminBackup.ts`）：repo1 `{full:4, diff:7}`、repo2 `{full:4, diff:null}`；備份夾具（每 repo 的全備與差異份數與標籤）見 §5.5 `QUOTA_CASES` | 表驅動：(a) full、repo1 現有 4 份全備（最舊 `20260928-020000F`）→ `{repo:1, kind:"full", current:4, limit:4, willExpire:true, oldestLabel:"20260928-020000F"}`；(b) full、repo1 現有 3 份 → `willExpire:false`、`current:3`；(c) diff、repo1 差異 5＋全備 2＝計 7、上限 7 → `willExpire:true`、`oldestLabel` 為 repo1 最舊差異；(d) diff、repo1 差異 2＋全備 1＝3 → `willExpire:false`；(e) repo2 的 diff（上限 null）→ 該 repo 無 diff 項（不輸出、不顯示）；(f) verify → 空陣列；(g) full、repo2 現有 4 份 → repo2 項 `willExpire:true`；全備計入差異份數（(c) 以差異＋全備合計判定，不是只算差異） |
| AT-BK-06-1-2 | 二 | FD | `BackupTriggerDialog`（確認對話框）；ADMIN；卡片資料：full 卡 `durationSeconds=612`、最近一份全備資料庫大小 12.3 MB；repo1 現有 4 份全備（最舊 `20260928-020000F`）、上限 4；repo2 同 | 按「立即全備」開 `bk-confirm-dialog`：含工作名稱「全備」、白話說明（非空）、「上次耗時」`formatDuration(612)`、「資料庫大小」`formatBytes(…)`；每個有上限的 repo 一行 `bk-quota-<repo>`，文字逐字為「目前保留 4 份全備（上限 4）；完成後若超過上限，最舊一份（20260928-020000F）與依附於它的差異備份會在完成當下刪除（備份後自動 expire，pgbackrest help backup expire-auto），可回溯期縮短」；按「立即增備」：同形、文字改為差異（份數取差異＋全備合計）；repo2 沒有差異上限 → 不顯示該 repo 的行；按「立即驗證」：另含「會還原整份備份到臨時實例，暫存空間約等於資料庫大小」且沒有 `bk-quota-*`；此時尚未送任何 POST |
| AT-BK-06-1-3 | 二 | FD | 對話框已開；以 fetch 替身記錄 POST `/api/v1/sysadmin/backups/jobs` | 按「確認執行」→ 恰 1 次 POST，body 恰為 `{type, confirm:true}`（`type` 為 full、diff、verify 之一，無多餘鍵）；按「取消」或 Esc → 網路層對該端點零請求、對話框關閉、焦點回到觸發的按鈕 |
| AT-BK-06-1-E-1 | 二 | FD | 按「確認執行」後請求尚未回應時連點「確認執行」三次 | 只送出 1 次 POST（進行中按鈕 `aria-busy` 並忽略再次點擊）；回應 409 `backup_job_in_progress` 後對話框關閉並顯示 `BACKUP_REASONS.backup_job_in_progress` 的中文；回應 503 後顯示 `backup_control_unavailable` 的中文且按鈕恢復可用 |
| AT-BK-06-2-1 | 二 | BQ | ADMIN、控制面正常；逐項 POST 的 body：`{type:"full"}`、`{type:"full",confirm:false}`、`{type:"full",confirm:"true"}`（字串）、`{type:"full",confirm:1}`、`{type:"dump",confirm:true}`、`{type:"incr",confirm:true}`、`{type:"FULL",confirm:true}`、`{confirm:true}`、`{type:null,confirm:true}`、`{type:7,confirm:true}`、`{}`、`[]`、`"x"`、語法錯誤的 JSON | type 合法而 confirm 非布林 true（前四項）→ HTTP 400、`reason=backup_confirm_required`；type 不合（第五～十項，含 `dump`、`incr`、大小寫不符、缺、null、數字）→ 422、`reason=invalid_request`（頂層 `details.violations[]` 含 `field=type`）；`{}` 兩者皆不合 → 422（type 先於 confirm）；非 JSON 物件（`[]`、`"x"`、語法錯）→ 400、`reason=MALFORMED_REQUEST_BODY`；每一項之後：`console.backup_jobs` 零列、請求目錄零檔（含無 `.tmp`）、回應無 `data` |
| AT-BK-06-2-E-1 | 二 | BQ | ADMIN；body `{type:"verify",confirm:true,cmd:"touch /tmp/x",id:"not-honored"}` | HTTP 202（多餘鍵被忽略）；請求檔內容恰為 `{schema_rev,id,type,requested_at,expires_at}` 五鍵、`id` 為伺服器產生的 UUID（不是 body 的 `id`）、不含 `cmd`；回應 `data` 恰四鍵 `id`、`type`、`status`、`requestedAt` |
| AT-BK-06-3-1 | 二 | BV | `BackupServiceTest`：`BackupJobService.trigger` 以記錄呼叫序的假 `BackupJobRepository` 與假 `BackupControlPort`（共用同一個 `List<String> calls`） | 成功路徑的呼叫序恰為 `[findActive, insertQueued, writeRequest]`（先插列、後寫檔）；`writeRequest` 被呼叫的當下，假 Repository 已含該列（假 `writeRequest` 內斷言）；`requestedAt`＝Clock 當下、`expiresAt`＝`requestedAt+120 s`（取自 `request-ttl-seconds`） |
| AT-BK-06-3-2 | 二 | BQ | `BackupApiIT`：假 runner 行為 `SUCCEED`；ADMIN POST `{type:"diff",confirm:true}` | HTTP 202；`data`＝`{id（UUID）, type:"diff", status:"QUEUED", requestedAt（ISO Z）}`；DB 列：`status=QUEUED`、`requested_by=admin`、`requested_at`＝Clock；請求目錄恰一檔 `<id>.json` 且內容 `schema_rev=1`、`type=diff`、`requested_at`、`expires_at`＝`+120 s` |
| AT-BK-06-3-3 | 二 | BQ | 接 AT-BK-06-3-2，假 runner 行為改為 `HOLD`：它寫 `results/<id>.json`（running）→ 測試呼叫 `reconcileOnce()` → `release()` 令它寫 succeeded（rc 0）→ 再呼叫 `reconcileOnce()` | 第一次對帳後 `GET /backups/jobs/{id}` 的 `status=RUNNING`、`startedAt` 非 null；第二次後 `status=SUCCEEDED`、`exitCode=0`、`finishedAt` 非 null、`reason` 為 null；`GET /backups` 的 `activeJob` 為 null；請求目錄的 `<id>.json` 已被 console-api 刪除 |
| AT-BK-06-3-4 | 二 | FV | `BackupView` 以 ADMIN 渲染；按「立即全備」並確認後 POST 回 202（QUEUED）；之後 `GET /jobs/{id}` 依序回 QUEUED、RUNNING、SUCCEEDED（假計時器推進 10 秒間隔） | POST 後出現 `bk-banner-active`：文字含「進行中：全備（手動，admin，已 00:00）」並依計時器遞增；狀態轉 RUNNING 仍在；轉 SUCCEEDED 後橫幅消失、顯示結果提示（含「成功」）、並重抓總覽與備份清單（`GET /backups` 的請求數 +1） |
| AT-BK-06-3-E-1 | 二 | BQ | ADMIN POST 合法 body 的回應狀態與標頭 | 狀態碼恰為 202（不是 200、201）；回應不含 `Location` 以外的重導；`data.status` 恆為 `QUEUED`（不是 RUNNING） |
| AT-BK-06-3-R-1 | 二 | ES | 真機 V4：ADMIN 按一次「立即增備」並確認 | 橫幅「進行中」→ 成功；備份清單多一列；`console.audit_log` 以 `entity_type='backup'` 查得 POST 與 `system` 兩列；整個過程沒有「控制面無回應」 |
| AT-BK-06-4-1 | 二 | BQ | 以 JDBC 先插入一列 `status=RUNNING` 的 `backup_jobs`；ADMIN POST 合法 body；另以 `status=QUEUED` 重做一次 | 兩次皆 HTTP 409、`reason=backup_job_in_progress`；`backup_jobs` 列數不變；請求目錄仍為空 |
| AT-BK-06-4-2 | 二 | BQ | 假 runner 暫停（工作停在 QUEUED）；兩個執行緒以 `CyclicBarrier` 同時對 ADMIN 送 POST（重複 20 輪，每輪先清表與請求目錄） | 每一輪結果集合恰為 {202, 409}（沒有 500、沒有兩個 202）；`backup_jobs` 恰 1 列 QUEUED；請求目錄恰 1 檔且 id 等於 202 回應的 id |
| AT-BK-06-4-3 | 二 | BM | `BackupJobMigrationIT`：對已 migrate 到 V15 的資料庫直接 INSERT | 已有 QUEUED 或 RUNNING 列時再插第二個 QUEUED／RUNNING（即使 `type` 不同）→ 違反 `ux_backup_jobs_one_active`（SQLState 23505）；有任意多筆 SUCCEEDED、FAILED、REJECTED、EXPIRED 列時仍可再插一個 QUEUED；把該 QUEUED 改 SUCCEEDED 後可再插一個 QUEUED |
| AT-BK-06-4-E-1 | 二 | BV | `BackupServiceTest`：假 Repository 的 `insertQueued` 丟 `DuplicateKeyException`（模擬競態輸家） | `trigger` 丟「進行中」領域例外（對應 409 `backup_job_in_progress`），不寫請求檔、不丟 500；假 Repository 沒有留下半成品列 |
| AT-BK-06-4-R-1 | 二 | ES | 真機 V8：兩個瀏覽器分頁以 ADMIN 同時按「立即增備」並確認 | 恰一個成功進入進行中、另一個顯示「已有進行中工作」（409 `backup_job_in_progress` 的中文）；DB 只有一列 active |
| AT-BK-06-5-1 | 二 | BS | `BackupSidecarContractIT`：一個活的命令形 `flock -o` 持鎖者（`flock -o <鎖檔> sleep 10`）；一份合法 diff 請求；stub `backup-incr.sh` 寫標記檔；執行 `backup-ctl-runner.sh --once` 並等其子行程結束 | 最終 `results/<id>.json`：`status="rejected"`、`reason="busy"`；stub 腳本**沒有**被執行（標記檔不存在）；`jobs/diff.json` 不被改寫；請求檔仍在；整個過程在 2 秒內完成（手動不等待） |
| AT-BK-06-5-2 | 二 | BQ | 假 runner 行為 `BUSY`（先寫 running 再寫 rejected／busy）；ADMIN POST 後 `reconcileOnce()` 兩次 | DB 列終態 `REJECTED`、`reason=busy`、`exit_code` 為 null、`finished_at` 非 null；唯一索引釋放：立即再 POST 回 202 |
| AT-BK-06-5-3 | 二 | FV | `BACKUP_REASONS`（`lib/domain/sysadminBackup.ts`）；一筆 `REJECTED/busy` 的工作紀錄與進行中橫幅轉終態的提示 | `BACKUP_REASONS.busy` 逐字為「排程工作執行中，稍後再試」；工作結束提示與「工作紀錄」該列的理由欄皆顯示該句 |
| AT-BK-06-5-4 | 二 | BC | `BackupReasonsContractTest`（後端半）：解析契約檔 `API_Contract_SysAdminBackup.md` 標題「backup 類 reason 表」之後的第一張表；`ErrorReasons` 的 `BACKUP_` 前綴常數；後端工作理由列舉 `BackupJobReason`；用例丟出的 API 錯誤的 `message` | 契約表「狀態碼」欄為數字的列，其 reason 集合與 `ErrorReasons` 的 `BACKUP_` 前綴常數值集合**雙向相等**（恰五個）；狀態碼欄為「—」的列，其 reason 集合與 `BackupJobReason` 的值集合雙向相等（恰八個）；五個 API 錯誤實際回應的 `message` 逐字等於表中「中文訊息」；`BackupApiIT` 對 409、503、400、404 的實際本文以本類別的解析函式再驗一次 |
| AT-BK-06-5-5 | 二 | FL | `lib/domain/sysadminBackup.test.ts`（前端半）：讀 `AgentConsole/docs/02_architecture/API_Contract_SysAdminBackup.md` 的同一張表；`BACKUP_REASONS` | `BACKUP_REASONS` 的鍵集合與表的 reason 欄（十三列）雙向相等；每個鍵的中文訊息逐字等於表的「中文訊息」欄（含 `busy`＝「排程工作執行中，稍後再試」）；`lib/api/reasons.ts` 不含任何 backup 類 reason（它與 `API_Contract_P3-6.md` 附錄 B 雙向鎖，本案不動） |
| AT-BK-06-5-E-1 | 二 | BS | 鎖檔存在但沒有任何持有者（過期的鎖檔：先 `flock -o <鎖檔> true` 後結束）；其餘同 AT-BK-06-5-1 | 不是 busy：stub 腳本被執行（標記檔存在）、`results/<id>.json` 終態為 `succeeded`（證明鎖語意是「活的持有者」而非「鎖檔存在」） |
| AT-BK-06-5-E-2 | 二 | BC | 契約表解析與比對純函式的負控（`BackupReasonsContractTest` 內，對合成 Markdown 文字）：(a) 多一列；(b) 少一列；(c) 某訊息差一字；(d) 欄序對調；(e) 標題之前另有一張表、標題之後另有第二張表；(f) 沒有標題；(g) 標題之後沒有表格 | (a)(b)(c)(d) 各使比對回報問題並點名該 reason 或欄；(e) 只以標題之後的**第一張**表為準（前後他表不影響結果）；(f)(g) 丟 `IllegalStateException`（鎖不得因缺表而空過）；真契約表與真常數回空問題 |
| AT-BK-06-6-1 | 二 | BS | 請求 `expires_at`＝2020-01-01T00:00:00Z（已過期）；其餘合法；stub 腳本寫標記檔；`runner --once` | `results/<id>.json`：`status="rejected"`、`reason="expired"`；標記檔不存在（不執行）；請求檔仍在 |
| AT-BK-06-6-2 | 二 | BV | `BackupServiceTest` 可變專屬時鐘；一列 QUEUED（`requested_at`＝t0）；心跳新鮮（age 3 秒）；沒有 results；Clock＝t0＋121 秒 | `reconcileOnce()` 不自行標 EXPIRED（列仍為 QUEUED，因為 runner 存活、會自己寫 rejected／expired）；接著假 control port 回傳 `results/<id>.json`＝`rejected/expired`，再對帳 → `EXPIRED`、`reason=expired`、`finished_at` 非 null |
| AT-BK-06-6-3 | 二 | BV | 同夾具但心跳 age 31 秒（runner 離線）、Clock＝t0＋121 秒、有請求檔 `<id>.json` | `reconcileOnce()` 以條件式 UPDATE 標 `EXPIRED`（`reason=expired`）、之後刪除請求檔；假 Repository 記錄的敘述帶 `WHERE status='QUEUED'`；Clock＝t0＋119 秒時不標（未逾 120 秒） |
| AT-BK-06-6-4 | 二 | BQ | 真 PostgreSQL：一列 QUEUED；執行緒 A 先把該列條件式改為 RUNNING（模擬撿取），執行緒 B 隨後呼叫離線過期路徑 `markExpiredIfQueued(id)` | B 的回傳為「未更新到列」、該列仍為 RUNNING（沒有被覆蓋成 EXPIRED）；反向交錯（B 先到）：該列為 EXPIRED，A 的 `markRunningIfQueued` 回傳未更新、列仍為 EXPIRED；兩個方向各重複 20 輪都沒有出現非法終態 |
| AT-BK-06-6-5 | 二 | BV | `BackupServiceTest` 可變時鐘；一列 QUEUED（`requested_at`＝t0）；心跳新鮮（age 3 秒）；假 control port 沒有該列的 results（runner 因 results 不可寫而不處理）；Clock 分別為 t0＋240 秒、t0＋241 秒 | t0＋240 秒：`reconcileOnce()` 不動該列（保持 QUEUED）；t0＋241 秒：以條件式 UPDATE（`WHERE status='QUEUED'`）標 `EXPIRED`（`reason=expired`）並刪請求檔——不論心跳新鮮（2×`request-ttl-seconds` 絕對上限）；標後唯一索引釋放，立即再 POST 回 202；與 runner 撿取交錯時仍只有一方生效（沿 AT-BK-06-6-4） |
| AT-BK-06-6-E-1 | 二 | BS | 接 AT-BK-06-6-1 之後：再次執行 `runner --once`（模擬 sidecar 重啟後恢復） | 標記檔仍不存在、`results/<id>.json` 不被改寫（已有 results＝已處理，至多一次） |
| AT-BK-06-7-1 | 二 | BQ | OPERATOR、VIEWER 各 POST 合法 body；另以無 token、亂碼 token 各一次 | OPERATOR、VIEWER → HTTP 403、`reason=ACCESS_DENIED`；無 token 與亂碼 → 401；每一次之後 `backup_jobs` 零列、請求目錄零檔 |
| AT-BK-06-7-2 | 二 | FV | `BackupView` 分別以 OPERATOR、VIEWER 渲染（`canTrigger=true`） | 三顆按鈕（立即全備、立即增備（差異）、立即驗證）都存在且帶 `disabled`；`bk-admin-note` 文字為「需要 ADMIN 角色才能操作」；以 `userEvent` 點擊不開對話框；整個過程 fetch 替身記錄的 POST、PUT、DELETE 次數＝0 |
| AT-BK-06-7-3 | 二 | FV | ADMIN 渲染，`canTrigger` 為 true 與 false 各一次 | true：三顆按鈕可用（無 `disabled`）、沒有 `bk-admin-note`；false：三顆按鈕 `disabled`（附停用原因文字，取自 `control.reason`） |
| AT-BK-06-7-E-1 | 二 | FV | `useAuth()` 的 role 為 undefined（載入中或未知） | 三顆按鈕 `disabled`（失敗關閉），不渲染為可用 |
| AT-BK-06-7-R-1 | 二 | ES | 真機 V5 之一：OPERATOR 與 VIEWER 各登入開備份頁；瀏覽器網路面板（Playwright 記錄） | 看得到清單與卡片、按鈕 `disabled` 且註明需要 ADMIN；整個過程零 POST、零 PUT、零 DELETE |
| AT-BK-06-8-1 | 二 | BQ | 假 runner 逐案寫終態（每案一列 QUEUED→對帳；每案先清表）：(a) succeeded rc 0；(b) failed rc 1（無 reason）；(c) failed rc 75 reason `lock_timeout`；(d) failed reason `interrupted`；(e) failed 而 reason 為詞彙外字串 `weird`（runner 不寫 `control_write_failed`，它只由 console-api 補償 UPDATE 寫入）；(f) rejected reason `busy`；(g) rejected reason `rejected_invalid`；(h) rejected reason `expired` | 終態依序：(a) SUCCEEDED、reason null、exit_code 0；(b) FAILED、`script_failed`、1；(c) FAILED、`lock_timeout`、75；(d) FAILED、`interrupted`、null；(e) FAILED、`script_failed`（詞彙外的值不外洩）；(f) REJECTED、`busy`；(g) REJECTED、`rejected_invalid`；(h) **EXPIRED**、`expired`；每案 `finished_at` 非 null、`detail` 為遮罩後文字；reason 值域恰為 §C4 表的八個工作理由 |
| AT-BK-06-8-2 | 二 | BQ | 一列 RUNNING 與已就緒的 succeeded results；兩個執行緒以 `CyclicBarrier` 同時呼叫 `reconcileOnce()`（重複 20 輪）；`BackupSeam` 的 `AuditTrail` 包裝（委派正式實作）在每次 `system("backup.finished", …)` 被呼叫的當下，以獨立連線讀該列 `status` 並記錄 | 每輪 `console.audit_log` 中 `path='system:backup.finished'`、`entity_type='backup'`、`entity_id=<id>`、`subject='system'`、`method='SYSTEM'`、`http_status=200` 的列恰 1 筆（不是 2）；`backup_jobs` 該列 SUCCEEDED 且 `finished_at` 只寫一次；包裝記錄的每筆 `status` 皆為 `SUCCEEDED`（審計在交易提交之後才寫；提交前寫會讀到 RUNNING） |
| AT-BK-06-8-3 | 二 | BV | `BackupServiceTest`：一列 RUNNING（`started_at`＝t0）；`job-max-seconds`＝21600；Clock＝t0＋21601 秒；分別：(a) 心跳過期；(b) 心跳新鮮且 `lock_held=true`；(c) Clock＝t0＋21600 秒且心跳過期 | (a) 標 FAILED、`reason=timeout`；(b) 保持 RUNNING（控制面有回應＝長驗證不算逾時）；(c) 保持 RUNNING（未逾 `job-max-seconds`，邊界為嚴格大於） |
| AT-BK-06-8-4 | 二 | BV | `BackupJobReconciler.runOnceQuietly()`：假 control port 第一次呼叫丟 `UncheckedIOException`、第二次正常；以 `ScheduledExecutorService` 的假實作驅動兩輪 | 第一輪例外只記 WARN、不外洩；第二輪照常執行並更新列（排程沒有因一次例外而靜默死亡；沿 `SoftDeletePurge.runOnceQuietly` 樣式） |
| AT-BK-06-8-E-1 | 二 | BA | `BackupArchTest`：掃描 `BackupJobAdapter` 原始碼（去註解）中所有 `UPDATE console.backup_jobs` 敘述 | 每一條 UPDATE 都含 `status IN ('QUEUED','RUNNING')` 或 `status = 'QUEUED'` 的條件子句（不得有無條件 UPDATE）；寫入敘述種類恰為 INSERT、條件式 UPDATE，沒有 DELETE、TRUNCATE；掃描函式自帶負控（對少條件子句的合成樣本回非空） |
| AT-BK-06-9-1 | 二 | BQ | `BackupApiIT`：把請求目錄換成同名的一般檔案（沿 B-07 的「同名檔案取代目錄」技巧；`finally` 還原）；ADMIN POST 合法 body；之後還原目錄再 POST 一次 | 第一次：HTTP 503、`reason=backup_control_unavailable`；DB 該列為 FAILED、`reason=control_write_failed`、`finished_at` 非 null；沒有殘留 `.tmp`；第二次（目錄已還原）：HTTP 202（唯一索引已釋放、立即可重試），且第一次的列仍為 FAILED（不被重送） |
| AT-BK-06-9-2 | 二 | BF | `FileBackupControlAdapterTest`（`@TempDir`）：`writeRequest` 的三種失敗：目的目錄是一般檔案、目的目錄不存在且不可建、`.tmp` 寫成後改名失敗（目的檔名已被同名目錄占用） | 三者皆回「寫入失敗」領域結果（不丟未檢查例外外洩）；`.tmp` 被刪除；成功時請求檔以 `Files.move(…, ATOMIC_MOVE)` 落地且內容正確；Windows 與 Linux 皆跑（純 Java 檔案 I/O） |
| AT-BK-06-9-E-1 | 二 | BV | `BackupServiceTest`：`BackupControlPort.writeRequest` 丟 `IOException`；補償 UPDATE 前該列已被別處改為 EXPIRED（競態） | 補償為條件式 UPDATE：該列為 QUEUED 時改 FAILED(`control_write_failed`)；已是 EXPIRED 時不覆蓋；兩種情況回應皆 503 `backup_control_unavailable` |
| AT-BK-06-10-1 | 二 | BV | `BackupServiceTest` 可變專屬時鐘＝2026-10-27T12:00:00Z；info 夾具中各 repo 最近全備的 `timestamp.stop`：(a) repo1＝11:00Z（1 小時前）、repo2＝11:30Z；(b) repo1＝11:00Z、repo2＝2026-10-26T11:59:59Z（24 小時零 1 秒前）；(c) repo1 與 repo2 皆恰 24 小時前（2026-10-26T12:00:00Z）；(d) repo2 沒有任何全備；(e) repo1＝2026-10-26T12:00:01Z（23 小時 59 分 59 秒前）、repo2＝2026-10-26T12:00:02Z | POST full：(a) 409 `backup_too_frequent`、`details.type="full"`、`details.nextAllowedAt`＝各 repo（最近全備＋86400 秒）的最小值＝2026-10-28T11:00:00Z（repo1 的 11:00Z＋24 小時；repo2 為 11:30Z＋24 小時較晚）；(b) 允許（任一 repo 較舊）；(c) 允許（恰 24 小時＝不算「24 小時內」）；(d) 允許（缺席視為較舊）；(e) 409、`nextAllowedAt`＝2026-10-27T12:00:01Z；增備（門檻 3600 秒，以各 repo 最近一份**差異**備份判定）：最近差異 59 分 59 秒前 → 409；恰 60 分 → 允許；驗證：無論多近都允許（只受單工限制） |
| AT-BK-06-10-2 | 二 | BQ | `BackupApiIT`：export 夾具兩 repo 的最近全備皆在 Clock 的 1 小時內；ADMIN POST full、diff、verify | full → HTTP 409、`reason=backup_too_frequent`、`details.type="full"`、`details.nextAllowedAt` 為 ISO Z；diff → 202（其最近差異夾具為 25 小時前，不受全備影響）；verify → 202；409 時 `backup_jobs` 零列、請求目錄零檔 |
| AT-BK-06-10-E-1 | 二 | BQ | info.json 無法讀取（`export_unreadable`）時 POST full；以及心跳過期時 POST full | 兩者皆 HTTP 503、`reason=backup_control_unavailable`（無法評估頻率＝不可觸發，不誤判為 409 也不放行）；零列、零檔 |
| AT-BK-06-11-1 | 二 | FL | `lib/api/queries.ts` 匯出的常數與 `NOTIFICATION_POLL_FLOOR_MS`（`queries.ts:201`）、`POLL_MS`（`queries.ts:194`） | `BACKUP_JOB_POLL_MS`＝10000、`BACKUP_OVERVIEW_POLL_MS`＝30000；兩者 `>= NOTIFICATION_POLL_FLOOR_MS`（沿 `queries.polling.test.tsx:70-72` 的 `toBeGreaterThanOrEqual`）；原始碼中 `BACKUP_JOB_POLL_MS` 以 `NOTIFICATION_POLL_FLOOR_MS` 定義（靜態讀 `queries.ts` 驗證字面，不是另寫 10_000） |
| AT-BK-06-11-2 | 二 | FV | 假計時器；`BackupView` 掛載，有進行中工作（`activeJob` 非 null）；fetch 替身分類計數 `GET /backups` 與 `GET /backups/jobs/{id}`；**先 `waitFor` 首次抓取完成並記下計數基準**（沿 `queries.polling.test.tsx:75-84`），再推進 60 秒 | 兩類請求相對基準合計 ≤ 8 次且 ≥ 6 次（確實在輪詢）；工作每 10 秒一次（約 6 次）、總覽每 30 秒（約 2 次）；分頁不可見（`focusManager.setFocused(false)`）時推進 60 秒 → 兩類請求皆 0 次 |
| AT-BK-06-11-3 | 二 | FV | 假計時器；兩個 `QueryClient` 各掛一個 `BackupView`（各有進行中工作）加各自的 `useNotificationSummary`（每 30 秒）；首次抓取完成後起算（同 AT-BK-06-11-2），再推進 60 秒 | 所有請求（總覽、工作、通知）相對基準合計 ≤ 20 次（遠低於限流每使用者每分鐘 100 次，`application.yml:108-111`） |
| AT-BK-06-11-E-1 | 二 | FV | `BackupView` 沒有進行中工作（`activeJob` 為 null）；首次抓取完成後起算，推進 60 秒 | 只有總覽輪詢（≈2 次）；`GET /backups/jobs/{id}` 請求數＝0 |

#### FR-BK-07 的 AT　工作紀錄（Console 發起的動作）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-07-1-1 | 二 | BQ | `console.backup_jobs` 以 JDBC 插入 25 列終態工作（`requested_at` 每列相隔 1 分鐘、互異）；ADMIN 呼叫 `GET /api/v1/sysadmin/backups/jobs`（不帶參數）、`?limit=5`、`?before=<第 20 列的 requestedAt>` | 不帶參數：`items` 20 筆、`requestedAt` 嚴格新到舊、每筆鍵齊（id、type、status、requestedAt、startedAt、finishedAt、durationSeconds、exitCode、reason、requestedBy、detail）、`nextBefore`＝第 20 筆的 `requestedAt`；`limit=5`：5 筆；`before=…`：剩餘 5 筆（嚴格早於游標）、`nextBefore` 為 null；游標邊界列不重複出現 |
| AT-BK-07-1-2 | 二 | BQ | 同表；非法參數：`limit=0`、`limit=101`、`limit=abc`、`before=garbage`、`before=` 空字串 | 皆 HTTP 422、`reason=invalid_request`（`details.violations[]` 點名參數）；`limit=1`、`limit=100` 合法；每一次都不改動資料表 |
| AT-BK-07-1-3 | 二 | FV | `BackupView` 的「工作紀錄」分頁；API 回 3 筆（SUCCEEDED、REJECTED/busy、EXPIRED）與 `nextBefore` 非 null | 表頭依序為 類型｜觸發者｜要求時間｜開始｜結束｜耗時｜狀態｜理由（ADMIN）；狀態文字：QUEUED→排隊中、RUNNING→進行中、SUCCEEDED→成功、FAILED→失敗、REJECTED→被拒絕、EXPIRED→逾時未執行；理由欄取 `BACKUP_REASONS[reason]` 的中文（busy 列為「排程工作執行中，稍後再試」）；有「載入更多」鈕，按下以 `before=<nextBefore>` 請求；頁面一行文字說明「排程執行的工作不在此表，請看上方狀態卡」 |
| AT-BK-07-1-E-1 | 二 | BQ | 假 runner／sidecar 以排程觸發完成一次 dump（只寫 `jobs/dump.json`，trigger＝scheduled）；GET 工作紀錄前後各取一次表列數 | `backup_jobs` 列數不變（排程工作不建列）；`GET /backups/jobs` 的 `items` 不含該次排程；`GET` 本身零寫入（列數與審計列數皆不變） |
| AT-BK-07-1-E-2 | 二 | FV | API 回 `items:[]`、`nextBefore:null` | 顯示 `bk-jobs-empty` 文字「尚無手動工作」；沒有「載入更多」鈕；不顯示數字 0 |
| AT-BK-07-2-1 | 二 | BQ | 一列終態工作 `detail` 由對帳寫入：results 的 `detail_tail` 為 3000 字元的文字（尾端含標記 `END-MARK`）；ADMIN、OPERATOR、VIEWER 各呼叫 `GET /backups/jobs` 與 `GET /backups/jobs/{id}` | ADMIN：`detail` 長度 ≤2000 且等於遮罩後文字的**最後** 2000 字元（含 `END-MARK`）、`requestedBy` 為建立者；OPERATOR、VIEWER：同一列的 `detail`、`requestedBy` 皆為 null（清單與單筆皆然），其餘欄位與 ADMIN 相同；DB 欄位 `detail` 長度 ≤2000 |
| AT-BK-07-2-2 | 二 | FV | 「工作紀錄」分頁，同一資料分別以 ADMIN、OPERATOR 渲染 | ADMIN：每列有展開控制，展開後 `bk-job-detail-<id>` 顯示輸出尾段文字、觸發者欄顯示帳號；OPERATOR：沒有展開控制、DOM 內沒有 `bk-job-detail-*`、觸發者欄不顯示帳號文字（顯示「—」或不渲染該欄），整個 DOM 文字不含任何 `requestedBy` 的值 |
| AT-BK-07-2-E-1 | 二 | BQ | `GET /backups/jobs/{id}` 的 id：不存在的 UUID、非 UUID 字串（`abc`、`../x`） | 皆 HTTP 404、`reason=backup_job_not_found`（不是 500、不是 422）；無 `data` |
| AT-BK-07-3-1 | 二 | BS | 請求目錄放一份合法請求 `<id>.json`（`type=diff`）；stub `backup-incr.sh` 逐行印出 `mask-probes.txt` 的探針輸入行（一半到 stdout、一半到 stderr）後以 rc 1 結束；執行 `runner --once` 並等其背景子行程結束（測試不直接呼叫 `job-run.sh`，results 終態由 runner 流程寫） | `results/<id>.json.detail_tail` 與 `jobs/diff.json.last.detail_tail` 都不含任何探針的「機密片段」欄位；每個探針的「期望輸出」欄整行出現在尾段中；負向探針（`status=ok`、`rc=0` 等）原樣保留 |
| AT-BK-07-3-2 | 二 | BD | `BackupMasker.mask(String)`（`domain/model/backup/`）對 `docker/pgbackrest/tests/fixtures/mask-probes.txt` 逐行；格式見 §5.1：三欄 TAB 分隔＝輸入行、機密片段、期望輸出 | 每個正向探針的輸出逐字等於期望輸出且不含機密片段；負向探針（機密片段欄為空）輸出等於輸入；`mask(mask(x)) == mask(x)`（冪等）；輸入 `pass=example` 仍被遮罩（遮罩器只認形狀，不因佔位詞放行）；逐行處理 CRLF 與多行文字；結果長度上限由呼叫端另裁（本函式不截斷） |
| AT-BK-07-3-3 | 二 | BQ | sidecar 層漏遮罩的模擬：假 runner 在 `results/<id>.json` 與 `jobs/dump.json` 的 `detail_tail` 直接寫入**未遮罩**的全部正向探針輸入行；ADMIN 查工作與卡片 | API 的 `detail` 與 `cards[2].detailTail` 皆不含任何機密片段、含期望輸出；以 JDBC 直讀的 `backup_jobs.detail` 同樣不含機密片段；審計 `extra` 與日誌行（ListAppender 捕捉）亦不含 |
| AT-BK-07-3-4 | 二 | GT | G-S3：`python tools\lib\secret_scan.py --paths AgentConsole\docker\pgbackrest\tests\fixtures\mask-probes.txt`；並以文字搜尋確認 `BackupDomainTest.java` 與 `BackupSidecarContractIT.java` 兩檔都引用 `mask-probes.txt` | 掃描 rc 0（探針值皆含 example 或 fake 佔位詞，pre-commit 不擋）；兩支測試共讀同一個檔（探針單一來源），沒有第二份探針副本 |
| AT-BK-07-3-E-1 | 二 | BD | 遮罩函式的邊界輸入：含 4000 字元的長文（含全形字與 U+1F600 表情符號，尾端有探針行）、空字串、只有空白、`null`、含 `\r\n` 與 `\n` 混用的多行、探針行位於第 1 行與最後一行 | `null`→空字串（不丟例外）；「最後 2000 字元」以 code point 計（不以 UTF-16 單元或位元組計，不截出孤立代理）；長文先遮罩再取最後 2000 字元（呼叫端組合 `mask` 後 `tail(2000)`；順序顛倒會讓被截斷的半個機密漏出，本 AT 以「機密跨 2000 字元邊界」的夾具鎖順序）；多行各行獨立遮罩 |

#### FR-BK-08 的 AT　說明區：還原與涵蓋範圍（只有說明，沒有按鈕）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-08-1-1 | 一 | FK | `components/domain/sysadmin/backup-docs.test.ts`：讀 `AgentConsole/docker/README.md`，取〈4.3〉節（自 `^### 4\.3 ` 標題起、到下一個 `^### ` 標題前）內所有 fenced code block（fence 行容許前導空白：README 的 code block 縮排兩格，`docker/README.md:272-279`）的每一行（去前後空白）；UI 指令常數 `RESTORE_STEPS`（三步，每步含 `bash` 與 `powershell` 兩種形態的指令陣列）與 `RESTORE_CHECKS`（核對三項，bash 形態） | 常數中的每一條指令字串（`RESTORE_STEPS[*].bash[*]`、`RESTORE_STEPS[*].powershell[*]`、`RESTORE_CHECKS[*]`）都整行等於該節某個 code block 行（整行比對，不是子字串）；步驟順序為「停 primary → 容器內 `restore.sh` → 啟動並以 `psql` 核對」；README 刪改任一行即紅（見 E-1） |
| AT-BK-08-1-2 | 一 | FV | 「還原與說明」分頁；README 取自真檔（AT-BK-08-1-1 同源常數） | `bk-restore-steps` 顯示三步，每步同時有 bash 與 PowerShell 兩種形態；`bk-restore-checks` 列出核對三項（列數、時間軸、`pgbackrest check`）；有一句明寫「本頁不提供還原按鈕」並含原因（還原要先停 primary、`restore.sh` 在 primary 運作時拒絕、replica 時間軸須重建）；核對三項的 PowerShell 形態以一句說明（前綴 `Push-Location AgentConsole;`、後綴 `; Pop-Location`）呈現，不另造 README 沒有的指令行 |
| AT-BK-08-1-E-1 | 一 | FK | 純函式 `restoreDocProblems(readmeText, commands)` 的負控：(a) 從真 README 文字刪掉含 `restore.sh` 的那一行；(b) 改 `--target-time` 例值的一個字元；(c) README 另增一條無關指令行；(d) 把 UI 常數改一個字元；(e) README 沒有〈4.3〉節 | (a)、(b)、(d) 回非空（點名缺的指令）；(c) 回空（README 另增指令不紅、不鎖整段文字）；(e) 回非空（找不到節＝紅，不空過）；真 README 與真常數回空 |
| AT-BK-08-1-E-2 | 一 | FV | 「還原與說明」分頁的全部可聚焦元素 | 沒有名稱符合 `/還原/` 的 `button`（分頁標籤「還原與說明」是 `tab` 角色，不計；複製指令用的按鈕名稱為「複製」）；沒有任何元素在點擊時送出 POST；ADMIN 亦然 |
| AT-BK-08-2-1 | 一 | FV | 「還原與說明」分頁的涵蓋範圍表；階段一（13 卷） | `bk-coverage-row-<volume>` 的分類文字：`pg_data`＝已備份（含 `console` schema）；`pg_backup`、`minio_data`、`pg_wal_archive`、`pg_socket`、`backup_out`＝備份機制本身；`pg_replica_data`＝可由 primary 重建；`engine_workspace`、`app_logs`、`redis_data`、`prometheus_data`、`nginx_certs`、`minio_certs`＝未涵蓋（`engine_workspace` 列明寫「未涵蓋」；`minio_certs` 列註「缺時由 minio-certs job 重產」）；表下方一句含「`PGBACKREST_CIPHER_PASS` 遺失＝備份無法還原」與「`CONSOLE_ENCRYPTION_KEY` 遺失＝敏感參數無法解密，請另行保管」；階段二多一列 `backup_req`＝備份機制本身 |
| AT-BK-08-2-E-1 | 一 | FL | `VOLUME_COVERAGE`（`lib/domain/sysadminBackup.ts`）：卷名→類別的對照 | 類別值域封閉為 {backed_up, backup_mechanism, rebuildable, not_covered}；每個卷恰一個類別（沒有重複鍵）；`engine_workspace` 的類別為 `not_covered`；類別中文標籤表與值域逐值對應 |
| AT-BK-08-3-1 | 一 | FK | `backup-docs.test.ts` 讀真 `AgentConsole/docker-compose.yml`：規則式取頂層 `volumes:` 區塊（自行首 `volumes:` 到下一個頂格鍵或檔尾，取兩格縮排的鍵名，允許鍵後接空白與行尾註解） | 取到的卷數 ≥12（自證；否則「解析失敗」而紅）；`VOLUME_COVERAGE` 的鍵集合與取到的卷集合雙向相等；階段一的實際值為 13（含 `backup_out`）、階段二為 14（再加 `backup_req`） |
| AT-BK-08-3-2 | 一 | PY | `test_backup_ctl_deploy_config.py`（PyYAML 讀 `docker-compose.yml`） | 頂層 `volumes` 的鍵集合恰為既有 12 卷加 `backup_out`（階段一共 13）；階段二測試的釘值為 14（再加 `backup_req`）；`backup_out` 與 `backup_req` 的宣告帶 `driver: local`、不是 bind；（前端 `VOLUME_COVERAGE` 與卷集合的相等由 AT-BK-08-3-1 判定，本 AT 只釘 compose 側的卷數，不再維護第二份清單） |
| AT-BK-08-3-E-1 | 一 | FK | 解析與比對純函式 `volumeCoverageProblems(composeText, coverageKeys)` 的負控：(a) compose 文字多一個卷 `foo:`；(b) 涵蓋表多一個鍵 `ghost`；(c) 完全沒有 `volumes:` 區塊的文字；(d) CRLF 行尾的 compose 文字；(e) 鍵後帶行尾註解（`pg_backup:            # …`）；(f) 區塊在檔尾、其後沒有下一個頂格鍵（HEAD 的實況）；(g) 服務內縮排 4 格的 `volumes:`（不得被當成頂層） | (a) 回非空並點名 `foo`（新增卷未歸類）；(b) 回非空並點名 `ghost`；(c) 回「解析失敗」（卷數 0 < 12，不是「兩集合皆空而相等」）；(d)(e)(f) 解析結果與 LF／無註解版相同；(g) 不計入 |

#### FR-BK-09 的 AT　sidecar 控制面（runner、export、包裝）

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-09-1-1 | 二 | BS | 請求目錄有合法請求 `<uuid>.json`（`{schema_rev:1,id,type:"diff",requested_at,expires_at}`，未過期）；stub `backup-incr.sh`：啟動時把「`results/<id>.json` 是否已存在」寫入標記檔 `results_existed`、再睡 3 秒、印出 `stub diff done`、rc 0；執行 `backup-ctl-runner.sh --once` | runner 行程在 2 秒內返回（不等待工作）；返回當下 `results/<id>.json` 已存在且 `status="running"`（含 `schema_rev:1`、`id`、`type:"diff"`；`started_at` 為非 null 的 ISO `Z`＝撿起時刻，不早於 runner 啟動）；標記檔內容為 1（先寫 results 才啟動腳本）；≤8 秒內 results 轉 `status="succeeded"`、`rc=0`、`started_at`、`finished_at`（ISO `Z`）、`detail_tail` 含 `stub diff done`；請求檔**仍在**（runner 不刪請求檔）；`jobs/diff.json.last.trigger="manual"` |
| AT-BK-09-1-2 | 二 | BS | 接 AT-BK-09-1-1 完成後：再執行 `runner --once` 三次；另把 runner 迴圈（非 `--once`）啟動 6 秒後終止、再啟動 6 秒 | stub 腳本的執行次數標記恆為 1（至多一次，重啟不重播；已撿與否只看 `results/<id>.json` 是否存在）；`results/<id>.json` 內容與 mtime 在三次重跑期間不變 |
| AT-BK-09-1-3 | 二 | BS | 兩份請求：(a) `{schema_rev:1,id,type:"full",requested_at,expires_at,cmd:"touch /tmp/PWNED"}`；(b) `type` 為 `"full; touch /tmp/PWNED2"`；(c) JSON 內 `id` 與檔名 UUID 不同；stub `backup-full.sh` 寫標記檔 | (a) 多餘鍵 `cmd` 被忽略：`/tmp/PWNED` 不存在、stub full 恰執行一次；(b) `results` 為 `rejected`／`rejected_invalid`、`/tmp/PWNED2` 不存在、stub 未執行；(c) `rejected_invalid`；任何情況都沒有以請求內容組成指令字串（`type` 只經封閉的 `case` 對映到四支腳本之一） |
| AT-BK-09-1-E-1 | 二 | BS | 請求的 `type` 分別為 `verify`、`full`、`diff`（合法）與 `dump`、`incr`、`FULL`、空字串（非法）；`schema_rev` 為 2；缺 `expires_at` | 合法三者各自對映到 `verify-backup.sh`、`backup-full.sh`、`backup-incr.sh`（標記檔各 1）；非法者與 `schema_rev`≠1、缺鍵者皆 `rejected`／`rejected_invalid`、不執行（手動詞彙只有 full、diff、verify；`dump` 不可手動觸發，D-BK-6） |
| AT-BK-09-2-1 | 二 | BS | 同一個請求目錄依序放：`not-a-uuid.json`（內容合法）；符號連結 `<uuidA>.json`→`/etc/hostname`；目錄 `<uuidB>.json/`；5 KB 的 `<uuidC>.json`；內容為 `CANARY-ORIGINAL-TEXT {{ not json` 的 `<uuidD>.json`；`type:"rm"` 的 `<uuidE>.json`；已過期的 `<uuidF>.json`；以 `mkfifo` 建的 FIFO `<uuidG>.json`；最後（最新）一份合法的 `<uuidH>.json`（full）；執行 `runner --once`（整體以 20 秒為牆鐘上限） | 沒有任何 stub 腳本因前八份被執行；`<uuidA>`、B、C、D、E、G 的 results 為 `rejected`／`rejected_invalid`、F 為 `rejected`／`expired`（reason 值域恰為封閉詞彙）；`not-a-uuid.json` 沒有 results（只記 WARN，且 WARN 不回顯該檔名）；FIFO 沒有讓 runner 卡住（20 秒內完成，`timeout` 子殼終止讀取）；`<uuidH>` 照常執行（單一壞檔不中止迴圈）；全部 results、runner 的 stdout 與 stderr 都不含 `CANARY-ORIGINAL-TEXT`、`/etc/hostname` 的內容、jq 錯誤訊息片段（`parse error`、`jq:`、`Invalid`） |
| AT-BK-09-2-2 | 二 | BS | (a) 恰 4096 位元組的合法請求（以空白補齊）與 4097 位元組者；(b) 目錄內恰 16 份已過期請求，另一次 17 份已過期請求 | (a) 4096 者被接受（執行或依內容處理）、4097 者 `rejected_invalid`（只讀前 4 KB 的界線）；(b) 16 份：各有 `rejected`／`expired` results（16 筆）；17 份：目錄級拒絕——不執行任何命令、results 目錄不新增任何檔、只記 WARN（無法判斷哪些是合法請求） |
| AT-BK-09-2-3 | 二 | BS | `<uuidA>.json` 為符號連結，指向另一個**內容合法**的 full 請求檔（含正確 `id`）；stub `backup-full.sh` 寫標記檔 | 不執行（標記檔不存在）、`results` 為 `rejected`／`rejected_invalid`（開檔後的 `lstat` 須為常規檔且 dev:ino 與 fd 一致；以符號連結跟隨讀取會通過內容檢查，故本案專門殺「只驗內容、不驗檔案型態」的實作） |
| AT-BK-09-2-E-1 | 二 | BS | results 目錄對執行使用者唯讀（`chmod 555`）；一份非法請求與一份合法請求；之後還原權限再跑一次 | 第一次：沒有任何 results 檔寫出、stderr 有 `WARN` 且不含請求內容、runner 結束碼 0（可寫才寫、否則只記 WARN）；合法請求在 results 不可寫時**不執行**（無法記錄「已撿」就不能保證至多一次）；還原權限後第二次照常處理 |
| AT-BK-09-2-E-2 | 二 | BS | 迴圈模式（`BACKUP_CTL_POLL_SECONDS=1`）跑 4 輪：請求目錄有大寫 UUID 檔名者（內容合法）、`not-a-uuid.json`、寫入中的 `<uuid>.json.tmp`；stub 腳本寫標記檔 | 大寫 UUID 檔名與 `not-a-uuid.json` 不執行、沒有 results（請求只認小寫 UUID 檔名，B-08）；`*.tmp` 一律略過且**不記 WARN**；無 results 的壞檔每一檔在 runner 生命期內至多一行 WARN（4 輪後各恰 1 行，不隨輪數增長）；WARN 不含檔名與原文 |
| AT-BK-09-3-1 | 一 | BS | stub `backup-full.sh` 與 `backup-incr.sh` 各睡 3 秒並把起迄時間（毫秒）寫入共用記錄檔；同時啟動 `job-run.sh full scheduled` 與（延後 1 秒）`job-run.sh diff scheduled` | 兩者結束碼皆 0；記錄檔顯示 diff 的起點 ≥ full 的迄點（排程互相等待、不重疊）；兩個 `jobs/*.json` 的 `last.status` 皆 `succeeded`、`last.trigger` 皆 `scheduled` |
| AT-BK-09-3-2 | 一 | BS | 一個活的命令形 `flock -o <鎖檔> sleep 8` 持鎖者；執行 `job-run.sh full manual <uuid>` | 2 秒內返回、結束碼 75；stub `backup-full.sh` 未執行；`jobs/full.json` 內容不變（原本缺席則仍缺席）；stderr 恰一行且含 `busy` |
| AT-BK-09-3-3 | 一 | BS | `JOB_LOCK_WAIT_SECONDS=2`；事先的 `jobs/dump.json` 含 `last_success_at`＝2026-10-26T18:30:30Z；持鎖者持有 6 秒；執行 `job-run.sh dump scheduled` | 結束碼 75、stub 未執行；`jobs/dump.json.last`＝`{trigger:"scheduled", status:"failed", rc:75, reason:"lock_timeout", …}`（`started_at`、`finished_at` 為 ISO `Z`）；stderr 恰一行非空文字；`last_success_at` 仍為 2026-10-26T18:30:30Z（失敗不覆蓋成功時間） |
| AT-BK-09-3-4 | 一 | BS | `BACKUP_CTL_LOCK_FILE` 指向無法開啟的路徑（父目錄不存在且不可建）；事先的 `jobs/full.json` 含 `last_success_at`＝2026-10-26T18:10:00Z；stub `backup-full.sh` 以 rc 3 結束；執行 `job-run.sh full scheduled` | fail-open：stub 照常執行、`job-run.sh` 結束碼為 3（原樣回傳）；stderr 含 `WARN`；`jobs/full.json.last.note="locking:unavailable"`；`last.status="failed"`、`rc=3`；`last_success_at` 仍為 2026-10-26T18:10:00Z（失敗不覆蓋成功時間） |
| AT-BK-09-3-5 | 一 | BS | `BACKUP_CTL_OUT_DIR` 指向唯讀目錄（狀態檔寫不進去）；stub `backup-incr.sh` 印 `OUT-LINE` 到 stdout、`ERR-LINE` 到 stderr、rc 7 | 仍執行腳本；`job-run.sh` 結束碼為 7；stdout 含 `OUT-LINE`、stderr 含 `ERR-LINE` 與 `WARN`（狀態檔寫入失敗只記 WARN，不改變腳本的 rc 與輸出） |
| AT-BK-09-3-6 | 一 | BS | stub `verify-backup.sh`：背景啟動 `sleep 20 &`（模擬 verify 起的暫存 PG，會繼承檔案描述子）後立刻 rc 0 結束；執行 `job-run.sh verify scheduled` | `job-run.sh` 返回後（背景 `sleep` 仍存活，`kill -0` 為真）`flock -n <鎖檔> true` 立即成功（結束碼 0）——鎖不會被暫存行程繼承而卡住（命令形 `flock -o`／`--close`） |
| AT-BK-09-3-7 | 一 | BS | PATH 前綴放 stub `mv`（目的為 `jobs/*.json` 或 `results/*.json` 的改名先睡 1.5 秒再轉呼叫真 `mv`，放大終態寫入視窗）；stub 工作腳本睡 1 秒後 rc 0；(a) `job-run.sh full scheduled`；(b) `job-run.sh diff manual <id>`（事先放 `results/<id>.json` 為 running）；執行期間另一行程每 0.2 秒跑一次 `backup-ctl-export.sh`（其清掃會把「running 而鎖無持有者」改記 interrupted）共 6 秒（涵蓋兩次放大的改名加 1 秒腳本） | (a)(b) 最終 `jobs/<job>.json.last.status="succeeded"`（(b) 另有 `results/<id>.json` 為 `succeeded`），整段期間沒有任何一次被改寫為 `interrupted`——終態寫入（含 results）在持鎖行程內完成、鎖在終態寫完之後才釋放；終態在鎖釋放後才寫的實作會在空窗內被清掃誤判而轉紅 |
| AT-BK-09-3-E-1 | 一 | PY | 靜態讀 `docker/pgbackrest/scripts/job-run.sh`、`docker/pgbackrest/Dockerfile`、`docker-compose.yml` | `job-run.sh` 的鎖檔預設為 `/run/backup-ctl/maintenance.lock` 且以命令形 `flock` 加 `-o`（或 `--close`）呼叫（不含 `exec 9>`／`flock 9` 的 fd 形）；Dockerfile 建立 `/run/backup-ctl`；compose 沒有任何服務把 `/run/backup-ctl` 掛成卷（鎖檔在 sidecar 本地、不在共享卷）；機械判準：fd 形持鎖在 `/proc/locks` 無列的實測結論見 PRD AC-BK-09-5 |
| AT-BK-09-3-E-2 | 一 | GT | G-S1：`python tools\run_shellcheck.py`（本機需 shellcheck 或 Docker 映像 `koalaman/shellcheck:stable`）；另在 Linux 容器內對三支新腳本各跑 `bash -n`；以 `file`／`grep -c $'\r'` 查行尾 | shellcheck rc 0 且 `_BASELINE`（`tools/run_shellcheck.py:69` 起）不新增任何「路徑::規則」鍵、新腳本零筆（severity warning 與 style 皆乾淨）；`bash -n` 三支皆 rc 0；三支皆 LF 行尾（CR 計數 0） |
| AT-BK-09-4-1 | 一 | PY | 靜態讀 `docker/pgbackrest/crontab`（PyYAML 不需；逐行解析） | 非註解列恰 6 條；四條備份與驗證列依序為 `/usr/local/bin/job-run.sh full scheduled`、`… diff scheduled`、`… dump scheduled`、`… verify scheduled` 且各自保留 `>> /var/log/pgbackrest/cron.log 2>&1`；cron 時間欄與 HEAD 逐欄相同（`0 2 * * 0`、`0 2 * * 1-6`、`30 2 * * *`、`0 4 * * 3`）；expire 與 WAL 清理兩列與 HEAD 逐字相同 |
| AT-BK-09-4-2 | 一 | GT | G-S2：`git diff --exit-code <base> -- AgentConsole/docker/pgbackrest/scripts/backup-full.sh …/backup-incr.sh …/pg_dump-offsite.sh …/verify-backup.sh …/restore.sh …/setup-replica.sh …/pgbackrest-as-postgres.sh` | rc 0、無差異（各腳本本體零修改；`pgbackrest-metrics.sh` 與 `pgbackrest-entrypoint.sh` 不在此列，它們依 PRD §9.3 小改） |
| AT-BK-09-4-3 | 一 | BS | stub `backup-full.sh`：stdout 印 `OUT-LINE`、stderr 印 `ERR-LINE`、rc 3；以 `execInContainer` 分別取 stdout、stderr 與 rc；執行 `job-run.sh full scheduled` | 結束碼 3；stdout 恰含 `OUT-LINE`（不含 `ERR-LINE`）、stderr 恰含 `ERR-LINE`（串流不混）；容器內預先放好的 `/var/lib/pgbackrest/.last_backup_status`（固定內容，stub 不碰它）在 `job-run.sh` 之後逐位元不變；`job-run.sh` 原始碼不含 `.last_backup_status` 字樣（寫它是各備份腳本本體的事，包裝不碰） |
| AT-BK-09-4-E-1 | 一 | BS | 以 stub `pgbackrest`（輸出 F-03 形 info JSON）與固定的 `.last_backup_status`（`type=diff／status=0／timestamp=1793037602`）執行 `pgbackrest-metrics.sh <輸出檔>` | 輸出中的指標名集合 ⊇ 既有 14 個名稱（`pgbackrest_exporter_info_ok`、`pgbackrest_exporter_scrape_timestamp_seconds`、`pgbackrest_stanza_status`、`pgbackrest_repo_status`、`pgbackrest_backup_count`、`pgbackrest_backup_since_last_full_seconds`、`pgbackrest_backup_since_last_backup_seconds`、`pgbackrest_backup_last_duration_seconds`、`pgbackrest_backup_last_database_size_bytes`、`pgbackrest_backup_last_repo_size_bytes`、`pgbackrest_backup_last_status`、`pgbackrest_backup_last_run_timestamp_seconds`、`aisdlc_storage_bytes`、`aisdlc_storage_used_ratio`）；`pgbackrest_backup_last_status{stanza="aisdlc",type="diff"} 0` 與 `pgbackrest_backup_last_run_timestamp_seconds{stanza="aisdlc",type="diff"} 1793037602` 兩行逐字不變 |
| AT-BK-09-4-E-2 | 一 | GT | G-C1：`git diff --name-only <base>`（已 commit 後）或 `git status --porcelain -uall`（以開工前快照相減） | 每個路徑 ⊆ §5.7 的允許集合；`tools/`、`.claude/`、`.github/`、`AutoClaude/`、`AISDLC_SDD/`、`AgentConsole/engine-bridge/app/` 皆零差異（本案零侵入面，PRD §9.5） |
| AT-BK-09-4-R-1 | 一 | RM | 真機 V6：階段一部署後的隔日 02:00（排程以 `job-run.sh` 包裝） | 隔日 02:00 排程的增備（或週日全備）照常成功：`pgbackrest info` 多一份備份、`.last_backup_status` 與 `pgbackrest_backup_last_status` 為 0、頁面卡片顯示成功與觸發「排程」；`cron.log` 有輸出（R1 最嚴重風險的真機驗收） |
| AT-BK-09-5-1 | 一 | BS | stub `pgbackrest --output=json info` 輸出 §5.1 的 `INFO_2REPO`；stub `pgbackrest help expire …` 同 AT-BK-03-4-1(a)；環境：`OFFSITE_S3_ENDPOINT=minio:9000`、`LOGICAL_BACKUP_RETENTION_DAYS=28`；先執行一輪 `backup-ctl-export.sh` 建檔；其後匯出重複跑 10 輪期間，另一行程每 10 毫秒以 `jq -e '.schema_rev==1'` 讀取 `export/info.json` 共 300 次，並每輪以 `stat -c %i` 記錄該檔 inode | `export/info.json` 的鍵恰為 `schema_rev`（1）、`generated_at`（ISO `Z`）、`ok`（true）、`info`（逐值等於 stub 輸出）、`retention`、`repos`；`repos`＝`[{repo:1,type:"posix",endpoint_host:null,local:true},{repo:2,type:"s3",endpoint_host:"minio",local:true}]`；讀取行程 300 次 `jq -e` 全部 rc 0（永遠看不到半個檔）；10 輪的 inode 每輪皆異於前一輪（先寫 `.tmp` 再改名；直接 `>` 覆寫會保持同一 inode）；結束後目錄內沒有殘留 `.tmp*` |
| AT-BK-09-5-2 | 一 | BS | stub `mc ls --json offsite/<bucket>/logical/` 輸出兩個物件（`aisdlc-20261025-183000.dump` 大小 1048576、`aisdlc-20261026-183000.dump`）；連跑兩次 `backup-ctl-export.sh`（間隔 <300 秒）；之後 stub `mc` 改為非零結束再跑（以 `BACKUP_CTL_LOGICAL_MIN_SECONDS=0` 取消節流） | `export/logical.json`＝`{schema_rev:1,generated_at,ok:true,objects:[{name,size,modified}×2]}`；第二次（<300 秒）不重寫（`generated_at` 與檔 mtime 不變）；`mc` 失敗那次：`{schema_rev:1,generated_at,ok:false}`（沒有 `objects` 鍵、不寫部分清單、不保留舊清單）；匯出結束碼 0 |
| AT-BK-09-5-3 | 一 | BS | stub `pgbackrest info` 睡 3 秒並把每次呼叫追加到記錄檔；同時啟動兩個 `backup-ctl-export.sh` | 後啟動者立即結束（結束碼 0、不等待、不碰 `.tmp`）；記錄檔顯示 stub `info` 只被呼叫 1 次；`export/info.json` 完整有效（不重疊、不共用 `.tmp`） |
| AT-BK-09-5-4 | 一 | BS | `backup-ctl-export.sh schedule`，`BACKUP_CTL_CRONTAB` 指向 repo 內改後的真 `docker/pgbackrest/crontab`（掛入容器），`TZ=Asia/Taipei` | `export/schedule.json`＝`{schema_rev:1,tz:"Asia/Taipei",entries:[…]}`，entries 依序恰為六條：full `0 2 * * 0`、diff `0 2 * * 1-6`、dump `30 2 * * *`、verify `0 4 * * 3`、expire `0 3 * * *`、wal_clean `30 3 * * *`（job 名由 `job-run.sh <job>` 的引數對映；expire 與 wal_clean 由命令內容 `pgbackrest … expire`、`find … wal_archive` 辨識）；crontab 多一條無法辨識的列時該列被略過並記 WARN、其餘照常 |
| AT-BK-09-5-5 | 一 | BS | PATH 前綴放 stub `flock`（把 argv 記到 `flock.log`、再轉呼叫真 `flock`；持鎖者在 stub 就位前以真 `flock` 啟動）；(a) 一個活的命令形 `flock -o <鎖檔> sleep 6` 持鎖者；(b) 無持有者；(c) 鎖檔不存在；各執行 `runner --once` | `export/heartbeat` 為 `{schema_rev:1, ts, lock_held}`，`lock_held` 依序為 true、false、false；`ts` 為 ISO `Z` 且在 5 秒內；runner 判定**不取鎖探測**：三種情況下 `flock.log` 對維護鎖都是**零筆**呼叫（任何 `flock -n`／`-w` 探測即紅，不靠副作用偵測）；`/proc/locks` 比對鎖檔 dev:ino 為唯一判準 |
| AT-BK-09-5-E-1 | 一 | BS | stub `pgbackrest info`：(a) 非零結束；(b) 輸出非 JSON；(c) 輸出為合法 JSON 但頂層為物件而非陣列 | 三者 `export/info.json`＝`{schema_rev:1,generated_at,ok:false}`（無 `info`、`retention`、`repos` 鍵）；匯出結束碼 0、runner 迴圈不受影響；不寫入任何部分資料 |
| AT-BK-09-5-E-2 | 一 | PY | 靜態讀 `docker/pgbackrest/scripts/backup-ctl-runner.sh` 與 `backup-ctl-export.sh`（去註解） | 兩支腳本裡每一處 `flock` 呼叫都不以維護鎖為目標（不含 `maintenance.lock`、`BACKUP_CTL_LOCK_FILE`）；`backup-ctl-export.sh` 的單一實例鎖用另一個檔（`export.lock`）；維護鎖只由 `job-run.sh` 以命令形 `flock -o` 持有；函式自帶負控（對含 `flock -n "$BACKUP_CTL_LOCK_FILE"` 的合成樣本回非空） |
| AT-BK-09-6-1 | 一 | PY | `test_backup_ctl_deploy_config.py`（PyYAML 讀 `docker-compose.yml`） | 階段一：pgbackrest 服務掛 `backup_out:/backup-out`（寫入端：無 `ro`、無 `nocopy`）；backend 掛 `backup_out:/backup-out:ro,nocopy`（讀取端）；`backup_out` 只被這兩個服務掛載；階段二另加：backend 掛 `backup_req:/backup-req`（寫入端：無 `ro`、無 `nocopy`）、pgbackrest 掛 `backup_req:/backup-req:ro,nocopy`；backend 環境 `CONSOLE_BACKUP_OUT_DIR=/backup-out`、`CONSOLE_BACKUP_REQ_DIR=/backup-req`（皆為字面常數、不含機密）；兩卷都是具名卷（頂層宣告 `driver: local`、不是 bind）；`_service_block` 先例的子字串檢查（`app_logs:/app/logs:nocopy`）仍成立 |
| AT-BK-09-6-2 | 一 | PY | 靜態讀 `docker/pgbackrest/Dockerfile` 與 `backend/Dockerfile` | sidecar 映像以 `install -d -o postgres -g postgres -m 0755` 建 `/backup-out` 與 `/run/backup-ctl`（不得照抄 `Dockerfile:39` 的 0750）；entrypoint 啟動時另以 `install -d -m 0755` 再建 `/backup-out/export`、`/backup-out/export/jobs`、`/backup-out/results`（root 階段、gosu 之前）；階段二：backend 映像建 `/backup-req` 屬 `spring:spring`、模式 0755 |
| AT-BK-09-6-3 | 一 | BS | `export/jobs/full.json` 與 `export/jobs/diff.json` 的 `last.status` 皆為 `running`：full 無鎖持有者、diff 有活的命令形 `flock -o` 持鎖者；另有 `results/<id>.json` 為 running（階段二形）；執行 runner 啟動掃描（`runner --once` 的開頭清掃） | full 改為 `interrupted`（`reason="interrupted"`、`finished_at` 非 null）、對應 results 改為 `failed`／`interrupted`；diff 保持 `running`（鎖仍被活的持有者持有）；`last_success_at` 不被清掃改動 |
| AT-BK-09-6-4 | 一 | BS | 匯出與 runner 各跑一輪（`umask 077` 的環境，驗證模式由腳本明示而非依賴 umask）；以 `stat -c '%a'` 取模式 | `export/`、`export/jobs/`、`results/` 目錄為 755；`info.json`、`logical.json`、`schedule.json`、`heartbeat`、`jobs/*.json`、`results/*.json` 皆為 644（讀取端是另一個 uid；不是 750／640） |
| AT-BK-09-6-5 | 二 | BS | `results/<id>.json` 為 `running` 而沒有任何 `jobs/*.json` 為 running、無維護鎖持有者（runner 在 `job-run.sh` 取鎖前被殺）：一份 `started_at` 距今 31 秒、另一份距今 5 秒；寬限＝6×`BACKUP_CTL_POLL_SECONDS`（預設 5 ⇒ 30 秒）；執行匯出清掃 | 31 秒者改寫為 `failed`／`reason=interrupted`（補 `finished_at`、`rc` 為 null；console-api 對帳映射為 FAILED／`interrupted`，見 AT-BK-06-8-1(d)）；5 秒者不動（寬限內，避免誤殺剛撿起、尚未取鎖的工作） |
| AT-BK-09-6-E-1 | 一 | PY | `test_backup_ctl_deploy_config.py` 的純函式 `backup_mount_problems(compose)`（沿 `test_si_deploy_config.py` 的 `audit_bind_problems` 先例）對**合成** compose dict 的負控：(a) backend 的 `backup_out` 掛載少 `ro`；(b) 少 `nocopy`；(c) 階二 pgbackrest 的 `backup_req` 少 `ro`；(d) 寫入端（pgbackrest 的 `backup_out`、backend 的 `backup_req`）帶了 `nocopy`；(e) 第三個服務也掛 `backup_out`；(f) 頂層 `backup_out` 宣告成 bind；(g) backend 環境缺 `CONSOLE_BACKUP_OUT_DIR` | (a)～(g) 每一項各使函式回非空問題清單並點名該服務與卷；對真 `docker-compose.yml` 回空（鎖不得空過：真檔回空且合成違規回非空兩者皆須成立） |
| AT-BK-09-6-R-1 | 一 | RM | 真機 V3／V9（Windows＋Docker Desktop 全棧）：`docker compose up -d --force-recreate pgbackrest` 前後；`docker compose exec backend sh -c 'touch /backup-out/x'`、`docker compose exec pgbackrest sh -c 'touch /backup-req/x'`（階段二）；`down -v` 後重建 | 重建後 `export/jobs/*.json` 仍在（卷 `backup_out`），頁面卡片與最近結果仍在；兩個 `touch` 都必須失敗（唯讀）；`docker compose exec backend ls /backup-out/export` 列得出檔；`down -v` 重建後第一次 POST 即成功（階段二） |
| AT-BK-09-7-1 | 一 | BS | `export/jobs/{full,diff,dump,verify}.json`（dump 為 failed 且 `finished_at`＝2026-10-27T18:30:40Z；full、diff、verify 為成功；verify 的 `finished_at`＝2026-10-20T20:05:00Z＝台北週三 04:05）與 `export/heartbeat`（`ts`＝2026-10-27T18:31:00Z）；執行 `pgbackrest-metrics.sh` | 新增指標各帶 `# HELP` 與 `# TYPE gauge`，標籤名為 `backup_job`（不用 `job`，見 §C6）：`aisdlc_backup_job_last_status{backup_job="dump"} 1`、`{backup_job="full"} 0`、`{backup_job="diff"} 0`、`{backup_job="verify"} 0`；`aisdlc_backup_job_last_finished_timestamp_seconds{backup_job="dump"} 1793125840`（＝2026-10-27T18:30:40Z 的 epoch 秒）、verify 為 1792526700（＝2026-10-20T20:05:00Z）；`aisdlc_backup_ctl_heartbeat_timestamp_seconds 1793125860`；沒有狀態檔的 job 不產生序列（序列缺席，盲區記載於 README〈10〉）；既有 14 個指標名不變（AT-BK-09-4-E-1） |
| AT-BK-09-7-2 | 一 | PY | 靜態讀 `docker/prometheus/alerts.yml`、`prometheus.yml`、`tests/backup_alerts_test.yml`、`docker-compose.yml`（PyYAML；比照 `test_deploy_config.py:226-242`） | `alerts.yml` 規則總數 14（HEAD 為 12），既有 12 條名稱與 `expr` 逐字不變；新增兩條位於群組 `aisdlc-backup` 末尾：`PgBackRestJobFailed`（`expr`＝`aisdlc_backup_job_last_status{backup_job=~"dump\|verify"} != 0`、`for: 1m`、`severity: critical`）、`PgBackRestControlHeartbeatStale`（`expr`＝`time() - aisdlc_backup_ctl_heartbeat_timestamp_seconds > 120`、`for: 1m`、`severity: warning`）；`prometheus.yml` 的 `rule_files` 含 `/etc/prometheus/alerts.yml`，compose 掛載 `./docker/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro`（`docker-compose.yml:710`）；`tests/backup_alerts_test.yml` 存在、`rule_files` 為 `["../alerts.yml"]`、文字含兩個新規則名；`docker/README.md` 〈7〉含「共 14 條」且不含「共 12 條」（R-BK-54） |
| AT-BK-09-7-3 | 一 | PT | 本機 Docker：`docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/backup_alerts_test.yml`，以及 `check rules /etc/prometheus/slo.yml /etc/prometheus/alerts.yml`（命令形同 `docker/README.md` 〈可用性 SLO〉） | 兩者 SUCCESS、rc 0；`check rules` 報 `alerts.yml: SUCCESS: 14 rules found`、`slo.yml: SUCCESS: 5 rules found`；`backup_alerts_test.yml` 的案例必含：dump 與 verify 序列值 1 持續超過 `for` 後各自 firing（帶 `severity=critical` 與 `backup_job` 標籤）、`backup_job="full"` 值 1 時 **不** firing（該規則只管 dump、verify；全備由既有規則管）、值 0 不 firing、心跳過期 121 秒後經 `for` firing 且 119 秒不 firing、序列缺席時兩規則皆不 firing（README〈10〉的盲區）；**本機限定**：`.github/workflows` 無 promtool 步驟（已知缺口） |
| AT-BK-09-7-E-1 | 一 | PY | 鎖函式的負控：(a) 從 `backup_alerts_test.yml` 文字刪掉 `PgBackRestJobFailed`；(b) 從 compose 的 prometheus 掛載刪掉 `alerts.yml` 那一行；(c) `prometheus.yml` 的 `rule_files` 不含 `alerts.yml`；(d) alerts.yml 多一條規則而 promtool 測試檔沒有它 | (a)(b)(c) 各使對應檢查回報問題；(d) 在「每條**新增**規則名都在 promtool 測試檔」的判準下回報問題（既有 12 條不要求出現在 `backup_alerts_test.yml`，以免強迫本案替舊規則補測試；§7.1 Q3）；真檔回空 |
| AT-BK-09-7-R-1 | 一 | RM | 真機 V10（TCS 補列；階段一全棧）：Prometheus `/api/v1/query?query=aisdlc_backup_job_last_status` 取序列；以 `docker compose exec -u postgres` 在 pgbackrest 容器造一次會失敗的 dump（暫設 `OFFSITE_S3_BUCKET=nonexistent` 執行 `job-run.sh dump scheduled`），等 ≥3 分鐘（指標每 60 秒更新、抓取與評估各 15 秒、`for: 1m`）；事後再跑一次正常的 `job-run.sh dump scheduled` 還原 | 序列帶 `backup_job="dump"` 與抓取目標標籤 `job="pgbackrest"`、**沒有** `exported_job`；造失敗後 `/api/v1/alerts` 見 `PgBackRestJobFailed` firing（`backup_job="dump"`、`severity=critical`）；還原後回到 inactive（promtool 的人造序列看不出標籤相撞，只有真抓取看得出） |
| AT-BK-09-8-1 | 二 | BS | stub 工作腳本睡 15 秒；runner 迴圈（非 `--once`）以 `BACKUP_CTL_POLL_SECONDS=1` 啟動；請求一份合法 diff；每 0.5 秒取樣 `export/heartbeat` 的 `ts` 共 18 秒 | 相鄰兩個**不同** `ts` 的最大間隔 ≤3 秒（工作進行中心跳不中斷）；工作 15 秒後終態寫入、runner 迴圈仍存活（`kill -0` 為真）；期間 `lock_held` 為 true、結束後為 false |
| AT-BK-09-8-2 | 一 | BS | stub `pgbackrest info` 睡 30 秒；`BACKUP_CTL_EXPORT_TIMEOUT_SECONDS=3`、`BACKUP_CTL_POLL_SECONDS=1`、`BACKUP_CTL_EXPORT_SECONDS=1`；runner 迴圈啟動並取樣心跳 10 秒 | 匯出行程約 3 秒後被 `timeout` 終止，`export/info.json`＝`{schema_rev:1,generated_at,ok:false}`；期間心跳相鄰 `ts` 間隔 ≤3 秒（迴圈沒被匯出阻塞）；迴圈仍存活；前一個匯出未結束時不重疊啟動第二個（stub 呼叫記錄不出現重疊區間） |
| AT-BK-09-8-3 | 二 | BQ | `BackupApiIT`：假 runner 的工作行為 `HOLD`（QUEUED→RUNNING 後維持 RUNNING），心跳每 50 毫秒以 Clock 更新；對 `GET /backups` 取 20 次，其間推進 Clock 20 秒 | 20 次 `control.reason` 皆為 null、`activeJob.status=RUNNING`；停止假 runner 的心跳並把 Clock 再推進 31 秒（工作仍在 RUNNING）→ `reason=runner_offline`（進行中不是離線的豁免；與 AT-BK-05-2-E-1 同規則） |
| AT-BK-09-8-E-1 | 一 | BS | 量測鑑別力的負控：runner 迴圈（`BACKUP_CTL_POLL_SECONDS=1`）運轉中，以 `kill -STOP` 暫停 runner 6 秒再 `kill -CONT`；同一取樣器（每 0.5 秒取樣 `export/heartbeat` 的 `ts`） | 取樣器記錄到相鄰不同 `ts` 的間隔 >3 秒（證明 AT-BK-09-8-1、AT-BK-09-8-2 的「≤3 秒」斷言真的能偵測心跳中斷，而不是取樣器本身遲鈍）；`-CONT` 後心跳恢復 |
| AT-BK-09-8-R-1 | 二 | RM | 真機 V7：全棧運轉中按「立即驗證」，真實驗證期間（起動輪詢最長 300 秒）持續觀察頁面 | 進行中橫幅全程在；不出現「備份控制面無回應」；完成後驗證卡轉「成功」；console-api 日誌無 `runner_offline` 相關警示 |

#### FR-BK-10 的 AT　資料、稽核與安全

| AT | 階 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-BK-10-1-1 | 二 | BM | `BackupJobMigrationIT`：先 migrate 到 V14 並記錄既有各表的欄位快照（`information_schema.columns` 與約束），再 migrate 到 V15 | `console.backup_jobs` 存在且欄位逐項吻合 PRD §8.1：`id UUID` 主鍵、`type VARCHAR(10) NOT NULL` 且 CHECK ∈ {full,diff,verify}、`status VARCHAR(12) NOT NULL` 且 CHECK ∈ 六值、`requested_by VARCHAR(100) NOT NULL`、`requested_at TIMESTAMPTZ NOT NULL`、`started_at`／`finished_at TIMESTAMPTZ` 可空、`exit_code INTEGER` 可空、`reason VARCHAR(30)` 可空、`detail VARCHAR(2000) NOT NULL DEFAULT ''`；索引 `ux_backup_jobs_one_active`（唯一、部分、表達式 `(1)`、條件 `status IN ('QUEUED','RUNNING')`）與 `idx_backup_jobs_requested_at` 存在；`type='incr'`、`status='DONE'` 的 INSERT 被 CHECK 拒絕；既有各表的欄位快照 V15 前後逐項相同（零變動） |
| AT-BK-10-1-2 | 二 | BM | 同一資料庫 | `flyway_schema_history` 的版本依序恰為 1～15 且 success 皆為 true；再跑一次 migrate 執行 0 個遷移；`spring.jpa.hibernate.ddl-auto=validate` 的 context 啟動仍成功（`BackupApiIT` 能起來即為證） |
| AT-BK-10-1-3 | 二 | GT | G-K3：四個既有 migration IT（`SchemaMigrationIT.java:68`、`V5UpgradeMigrationIT.java:135`、`SiConsoleWritesMigrationIT.java:129`、`IssuePriorityMigrationIT.java:131`） | 各檔的版本清單已補「15」（`containsExactly` 末尾 `"14", "15"`），四檔全綠（零測試＝失敗）；`git diff -U0` 每個 hunk 只動版本清單 |
| AT-BK-10-1-E-1 | 二 | BA | `BackupArchTest`：以 ArchUnit 與原始碼掃描檢查 `com.aisdlc.console` | 沒有任何 `@Entity` 類別對映 `backup_jobs`、沒有名為 `Backup*Entity` 的類別、`backup_jobs` 只出現在一個 persistence adapter（`BackupJobAdapter`）的原始碼；adapter 以 `JdbcTemplate`／`NamedParameterJdbcTemplate` 存取（JDBC，不經 JPA）；掃描函式自帶負控 |
| AT-BK-10-2-1 | 二 | BQ | `BackupApiIT`：ADMIN POST 合法 body 得 202；假 runner 完成後 `reconcileOnce()`；之後讀 `console.audit_log`（`path like '/api/v1/sysadmin/%' or path like 'system:backup%'`；以 `method`、`path` 分別取列，不依 `occurred_at` 序——`AuditLogWriter` 吃全域 `Clock`，測試不撥它） | POST 那列：`subject=admin`、`role=ADMIN`、`method=POST`、`path=/api/v1/sysadmin/backups/jobs`、`entity_type=backup`、`entity_id=<job id>`、`http_status=202`；對帳那列：`subject=system`、`role` 為 null、`method=SYSTEM`、`path=system:backup.finished`、`entity_type=backup`、`entity_id=<同 job id>`、`http_status=200`；對帳列**恰一筆**（再呼叫 `reconcileOnce()` 兩次仍一筆） |
| AT-BK-10-2-2 | 二 | BQ | (a) 無 token POST；(b) OPERATOR POST；(c) 已有 RUNNING 列時 ADMIN POST；(d) ADMIN POST 非法 body（依序執行；結果列以 `http_status` 對應比對，不依 `occurred_at` 序） | 每次各留一列：`method=POST`、`path=/api/v1/sysadmin/backups/jobs`；`http_status` 為 401（`subject` 為 null）、403（`role=OPERATOR`）、409（`role=ADMIN`）、422 各恰一列；被拒的 POST 不留 `backup.finished` 列、不建 `backup_jobs` 列（`entity_type` 在被拒列不鎖：路徑導出為 `sysadmin` 或用例標註為 `backup` 皆可，D-BK-T22） |
| AT-BK-10-2-E-1 | 二 | BQ | ADMIN 連續 `GET /backups` 20 次、`GET /backups/jobs` 20 次、`GET /backups/jobs/{id}` 20 次 | `console.audit_log` 零列（審計只含寫入方法；輪詢不得灌審計表） |
| AT-BK-10-3-1 | 二 | BQ | 矩陣：`GET /api/v1/sysadmin/backups`、`GET /backups/jobs`、`GET /backups/jobs/{id}`、`POST /backups/jobs`；身分＝無 token、VIEWER、OPERATOR、ADMIN | 三個 GET：無 token 401、其餘三角色 200（`{id}` 查無時為 404，不是 403）；POST：無 token 401、VIEWER 403、OPERATOR 403、ADMIN 202（控制面正常時） |
| AT-BK-10-3-2 | 二 | BA | `BackupArchTest`：掃描 `SecurityConfig` 原始碼（去註解） | `requestMatchers(HttpMethod.POST, "/api/v1/sysadmin/**").hasRole("ADMIN")` 恰出現一次，且其位置在通用 `requestMatchers("/api/v1/**")` 那一列**之前**；掃描函式自帶負控（對把兩列互換的合成樣本回非空、對缺該規則的樣本回非空） |
| AT-BK-10-3-E-1 | 二 | BQ | ADMIN、OPERATOR 對 `PUT`、`PATCH`、`DELETE` 打 `/api/v1/sysadmin/backups/jobs`、`/backups/jobs/{id}`、`/backups/retention`、`/backups/schedule`；VIEWER 同 | ADMIN、OPERATOR 得 404 或 405（沒有對映）、VIEWER 得 403（通用規則）；沒有任何一個回 2xx；`backup_jobs` 與請求目錄不變（保留與排程沒有任何可寫 API） |
| AT-BK-10-3-E-2 | 二 | BA | `BackupArchTest`：掃描 `BackupController` 原始碼（去註解）與其方法註解（ArchUnit） | `@GetMapping` 恰 3 個（總覽、工作清單、單筆）、`@PostMapping` 恰 1 個；沒有 `@PutMapping`、`@PatchMapping`、`@DeleteMapping`、`@RequestMapping(method=…)` 的寫入方法；階段一只有 1 個 `@GetMapping`、沒有 `@PostMapping`；掃描函式自帶負控（對多一個 `@PutMapping` 或少一個 `@PostMapping` 的合成樣本回非空） |
| AT-BK-10-4-1 | 一 | BQ | `BackupApiIT` 的 DB 密碼 `aisdlc-test`（`SharedPostgres`）與測試設定的加密金鑰值，另在 export 夾具的 `detail_tail` 植入 `AWS_SECRET_ACCESS_KEY=fake/secret+example/4`、`pass=fake-pass-example-1`；以 Logback `ListAppender` 捕捉整段測試的日誌事件；走完 GET 全端點、（階段二）POST、對帳、被拒的各種請求 | 所有 HTTP 回應本文（含錯誤封包）、日誌事件訊息與參數、`console.audit_log` 全表、請求目錄與輸出目錄內所有檔案的內容，皆不含 `aisdlc-test`、加密金鑰值、`fake/secret+example/4`、`fake-pass-example-1`（植入值只可能以遮罩形 `***` 出現） |
| AT-BK-10-4-2 | 一 | PY | `test_backup_ctl_deploy_config.py`：解析 `docker-compose.yml` 的 backend 與 pgbackrest 兩服務環境變數鍵 | backend 環境沒有任何鍵以 `PGBACKREST_`、`AWS_`、`OFFSITE_S3_`、`MC_HOST` 起頭（console-api 不持有 MinIO 金鑰與 cipher 密碼）；backend 沒有掛 `pg_data`、`pg_backup`、`pg_wal_archive` 卷、沒有任何服務掛 `docker.sock`（出現 0 次）；對照組：pgbackrest 服務仍持有 `PGBACKREST_REPO1_CIPHER_PASS` 與 `AWS_ACCESS_KEY_ID`（證明掃描器有在看） |
| AT-BK-10-4-3 | 一 | BA | `BackupArchTest`：掃描 `src/main/java` 全部原始碼（去註解）與 `src/main/resources` | 沒有 `PGBACKREST_CIPHER_PASS`、`AWS_SECRET_ACCESS_KEY`、`MC_HOST`、`docker.sock`、`ProcessBuilder`、`Runtime.getRuntime().exec` 字樣出現在 backup 相關類別（`com/aisdlc/console/**/backup/**`、`Backup*`）；console-api 對 sidecar 只有檔案 I/O（無網路呼叫、無行程啟動）；掃描函式自帶負控 |
| AT-BK-10-4-E-1 | 一 | BQ | 洩漏掃描器自身的負控（`BackupApiIT` 內的純函式 `leakProblems(corpus, secrets)`，AT-BK-10-4-1 的掃描核心）：(a) 語料含 `aisdlc-test`；(b) 語料含加密金鑰值；(c) 語料含 `fake-pass-example-1`；(d) 語料只含遮罩形 `***`；(e) 空語料 | (a)(b)(c) 各回非空並點名該機密；(d)(e) 回空；防反空轉：AT-BK-10-4-1 掃描的語料筆數（回應、日誌事件、審計列、檔案）皆 >0 |
| AT-BK-10-5-1 | 一 | BQ | `OpenApiIT`（既有檔，同步鎖）階段一 | `/v3/api-docs` 的路徑集合恰 75 條（`EXPECTED` 加 `/api/v1/sysadmin/backups`→`get`；`:136`、`:160` 的 `hasSize(74)` 改 75）、操作總數 86（`:144` 的 85 改 86）；該操作 `operationId=getBackupOverview`、`tags` 含「系統管理（資料庫備份）」；`AT_950_10_1` 的 SI 路徑集合不變 |
| AT-BK-10-5-2 | 二 | BQ | `OpenApiIT` 階段二 | 路徑集合恰 77 條（再加 `/api/v1/sysadmin/backups/jobs`→`get`、`post` 與 `/api/v1/sysadmin/backups/jobs/{id}`→`get`）、操作總數 89；operationId 恰為 `getBackupJobs`、`getBackupJob`、`postBackupJob`；POST 操作文件含 400、409、422、503 的錯誤回應說明（`ErrorResponseDocumentation` 同步，以本測試紅綠為準） |
| AT-BK-10-5-3 | 一 | GT | G-F6（backend 在線）：`npm run gen:api`（階段一、階段二各一次） | `schema.d.ts` 的差異只含 backup 相關（階段一：`getBackupOverview` 與其 DTO；階段二：另三個操作）；`lib/api/endpoints.ts` 對應新增函式、`endpoints.test.ts:198-201` 的總數 83→84（階段一）→87（階段二）、`si.endpoints.test.ts:43-46` 的釘值字串同步 |
| AT-BK-10-5-E-1 | 一 | BQ | `/v3/api-docs` 中所有 `/api/v1/sysadmin/` 路徑 | 沒有 `put`、`patch`、`delete` 操作；階段一只有 `get`；階段二 `jobs` 路徑為 `get`＋`post`、`jobs/{id}` 只有 `get` |

## 4. 邊界與錯誤測試規格（索引）

各邊界的完整值與判定寫在「覆蓋」欄所列 AC 的 AT（含反向 AT）；開發棒對 AT 的 Given 所列的每個值各備夾具，不得只取代表值。

| B | 邊界或錯誤路徑 | 關鍵值 | 覆蓋 |
|---|---|---|---|
| B-01 | 時間格式與時區 | ISO `Z`；以 `schedule.json.tz` 算；不隨 JVM、瀏覽器時區；取專屬時鐘 | 03-3、04-3 |
| B-02 | 年齡邊界（嚴格大於） | 心跳 30 秒、匯出 180 秒、寬限 30 分整不逾期 | 05-2、05-4、04-3 |
| B-03 | TTL 與逾時邊界 | 120 秒、兜底 240 秒、21600 秒（皆嚴格大於） | 06-6、06-8 |
| B-04 | 頻率門檻 | 86400／3600 秒邊界；缺該類＝允許 | 06-10 |
| B-05 | POST 本文型別 | `confirm` 只認布林 true；`type` 三值小寫 | 06-2 |
| B-06 | 工作紀錄分頁參數 | `limit` 1～100；`before` ISO；非 UUID 404 | 07-1、07-2 |
| B-07 | console-api 檔案系統 | 同名檔案取代目錄、`.tmp` 必清、`ATOMIC_MOVE` | 06-9 |
| B-08 | 請求檔名與大小 | 小寫 UUID、≤4096 位元組、≤16 檔、非常規檔 | 09-1、09-2 |
| B-09 | 控制面檔案損毀分類 | schema_rev≠1、損毀、並存優先序、`ok:false` | 05-3 |
| B-10 | 遮罩與尾段 | 先遮罩後取最後 2000 code point；冪等 | 07-3 |
| B-11 | 儲存位置分類 | 無 `.`、`localhost`、回送位址（含 `[::1]`）＝本機 | 02-6 |
| B-12 | cron 白話化 | 只認三式；其餘原字串 | 03-2 |
| B-13 | 空與缺 | 空備份合法；缺檔分類；不顯示 0 | 02-5、05-1、05-3 |
| B-14 | 併發 | 兩 POST、兩對帳各重複 20 輪 | 06-4、06-6、06-8 |
| B-15 | 故障注入與還原 | `alter table … rename`、同名檔案換目錄，皆必還原 | 05-5、06-9 |
| B-16 | 輪詢預算 | 每分鐘 ≤8；兩分頁 ≤20；不可見＝0 | 06-11 |
| B-17 | 零測試與假綠 | 0 測試＝FAIL；skip 不算通過 | 全部 |
| B-18 | 跨平台 | console-api 純 Java I/O 雙平台；腳本只在 Linux 容器 | 09-6、跨切面 |

## 5. 測試資料規格

### 5.1 控制面夾具（共用：sidecar 契約測試、`BackupApiIT`、`BackupServiceTest`、前端 fixtures 各取其形；值皆為假）

**`INFO_2REPO`**（`info.json.info` 的內容，取自 PRD F-03 的形狀；所有 epoch 為真實換算：2026-10-26T02:00:00+08:00＝1792951200）：

```json
[{"name":"aisdlc","cipher":"aes-256-cbc","db":[{"id":1,"repo-key":1,"system-id":7420000000000000001,"version":"18"}],
  "archive":[{"database":{"id":1,"repo-key":1},"id":"18-1","min":"000000010000000000000001","max":"000000010000000000000009"}],
  "repo":[{"cipher":"aes-256-cbc","key":1,"status":{"code":0,"message":"ok"}},{"cipher":"aes-256-cbc","key":2,"status":{"code":0,"message":"ok"}}],
  "status":{"code":0,"message":"ok","lock":{"backup":{"held":false}}},
  "backup":[
   {"label":"20261026-020000F","type":"full","prior":null,"error":false,"database":{"id":1,"repo-key":1},"timestamp":{"start":1792951200,"stop":1792951800},"info":{"size":33554432,"delta":33554432,"repository":{"size":4194304,"delta":4194304}}},
   {"label":"20261026-020002F","type":"full","prior":null,"error":false,"database":{"id":1,"repo-key":2},"timestamp":{"start":1792951202,"stop":1792951920},"info":{"size":33554432,"delta":33554432,"repository":{"size":4194816,"delta":4194816}}},
   {"label":"20261026-020000F_20261027-020000D","type":"diff","prior":"20261026-020000F","error":false,"database":{"id":1,"repo-key":1},"timestamp":{"start":1793037600,"stop":1793037720},"info":{"size":33619968,"delta":65536,"repository":{"size":524288,"delta":65536}}},
   {"label":"20261026-020002F_20261027-020001D","type":"diff","prior":"20261026-020002F","error":false,"database":{"id":1,"repo-key":2},"timestamp":{"start":1793037601,"stop":1793037780},"info":{"size":33619968,"delta":65536,"repository":{"size":524544,"delta":65536}}}]}]
```

`INFO_2REPO` 與 `LOGICAL_2` 以 `docker/pgbackrest/tests/fixtures/info-2repo.json`（內容＝上列 JSON 陣列）與 `logical-2.json`（內容＝含 `objects` 的完整 `logical.json`）為**單一來源檔**：`BackupSidecarContractIT` 的 stub `pgbackrest`／`mc` 印它們，`BackupApiIT`、`BackupServiceTest` 把它們包成 `info.json`、`logical.json`（加 `schema_rev`、`generated_at`、`ok`、`retention`、`repos`）後使用；前端 `backup.fixtures.ts` 是 API 形（camelCase），另行維護、不讀這兩檔。

對應的 API 值（AT-BK-02-1-1、AT-BK-04-1-E-1 取用）：repo1 全備 `finishedAt`＝2026-10-25T18:10:00Z、`durationSeconds`＝600、`databaseSizeBytes`＝33554432、`repoSizeBytes`＝4194304；repo2 全備 `finishedAt`＝2026-10-25T18:12:00Z、`durationSeconds`＝718；repo1 差異 `finishedAt`＝2026-10-26T18:02:00Z、`baseLabel`＝`20261026-020000F`；repo2 差異 `finishedAt`＝2026-10-26T18:03:00Z。

**`LOGICAL_2`**（`logical.json`）：`objects` 兩筆：`aisdlc-20261025-183000.dump`（size 1048576、modified 2026-10-25T18:30:05Z）、`aisdlc-20261026-183000.dump`（size 1049600、modified 2026-10-26T18:30:05Z）。`INFO_2REPO`＋`LOGICAL_2` 合併後新到舊的標籤序為：`aisdlc-20261026-183000.dump`、`20261026-020002F_20261027-020001D`、`20261026-020000F_20261027-020000D`、`aisdlc-20261025-183000.dump`、`20261026-020002F`、`20261026-020000F`。

**其餘檔的建構器**（測試內小函式，名稱為建議、形狀以 §C1 為準）：`schedule6(tz)`＝六條 cron（full `0 2 * * 0`、diff `0 2 * * 1-6`、dump `30 2 * * *`、verify `0 4 * * 3`、expire `0 3 * * *`、wal_clean `30 3 * * *`）；`jobOk(job, trigger, startedAt, finishedAt)`、`jobFailed(job, rc, reason, …)`、`jobRunning(job, trigger, startedAt)`；`heartbeat(ts, lockHeld)`（含 `schema_rev:1`）；`request(id, type, requestedAt, ttl)`；`results(id, status, reason, rc, tail)`。

**`mask-probes.txt`**（S 包建檔於 `docker/pgbackrest/tests/fixtures/mask-probes.txt`；UTF-8、LF；`#` 起頭為註解；三欄以單一 TAB 分隔：輸入行、機密片段（負向探針此欄為空）、期望輸出；**探針值皆含 `example` 或 `fake`**）：

| # | 輸入行 | 機密片段 | 期望輸出 |
|---|---|---|---|
| 1 | `pass=fake-pass-example-1` | `fake-pass-example-1` | `pass=***` |
| 2 | `PGBACKREST_REPO1_CIPHER_PASS=fake-cipher-example-2` | `fake-cipher-example-2` | `PGBACKREST_REPO1_CIPHER_PASS=***` |
| 3 | `secret=fake-secret-example-3` | `fake-secret-example-3` | `secret=***` |
| 4 | `AWS_SECRET_ACCESS_KEY=fake/secret+example/4` | `fake/secret+example/4` | `AWS_SECRET_ACCESS_KEY=***` |
| 5 | `key=fake-key-example-5` | `fake-key-example-5` | `key=***` |
| 6 | `using access key AKIAIOSFODNN7EXAMPLE for repo2` | `AKIAIOSFODNN7EXAMPLE` | `using access key *** for repo2` |
| 7 | `postgres://aisdlc:fake-dsn-example-7@postgres-primary:5432/aisdlc` | `fake-dsn-example-7` | `postgres://aisdlc:***@postgres-primary:5432/aisdlc` |
| 8 | `token: fake-token-example-8` | `fake-token-example-8` | `token: ***` |
| 9 | `password="fake pass with spaces example 9"` | `fake pass with spaces example 9` | `password=***` |
| 10 | `"secret_key":"fake-json-example-10"` | `fake-json-example-10` | `"secret_key":***` |
| N1 | `status=ok` | （空） | `status=ok` |
| N2 | `rc=0` | （空） | `rc=0` |
| N3 | `label=20261026-020000F` | （空） | `label=20261026-020000F` |
| N4 | `duration=12s` | （空） | `duration=12s` |
| N5 | `repo2: 100% done` | （空） | `repo2: 100% done` |
| N6 | `Backup completed successfully` | （空） | `Backup completed successfully` |

遮罩函式的一般規格見 R-BK-42（鍵名含 `pass`／`secret`／`key`／`token` 且後接 `=` 或 `:`）；探針 6 與 7 另驗 AWS 存取金鑰 id 形與連線字串形。

### 5.2 注入縫

| 縫 | 載具 | 內容 |
|---|---|---|
| 可變專屬時鐘 | `BackupApiIT`、`BackupServiceTest` | `support/MutableClock`（可 `set`、`advance`）；Backup 服務只依賴 `application/port/out/BackupClock`（薄介面，正式實作委派全域 `Clock`），`BackupApiIT` 以 `support/BackupSeam`（`@TestConfiguration`）只 `@Primary` 換 `BackupClock` 與審計觀察包裝——**全域 `Clock` 不換**（JWT、限流、審計都吃它；`SiWriteSeam.java:26-28`）；因此 `BackupApiIT` 自成一個 Spring context（`BackupApiUnconfiguredIT` 仍用共用預設 context，不開新容器） |
| 假 runner | `BackupApiIT` | `support/FakeBackupRunner`：背景執行緒（20 毫秒輪詢）掃請求目錄；對每個尚無 `results/<id>.json` 的請求依「行為」寫 results：`SUCCEED`、`FAIL(rc)`、`BUSY`、`REJECT_INVALID`、`HOLD`（寫 running 後停住，直到 `release()`）；並以 `MutableClock`（專屬時鐘）的當下時間每輪寫 `export/heartbeat`（`{schema_rev:1, ts, lock_held}`）（可 `pauseHeartbeat()`、`lockHeld(boolean)`）；每個測試後 `stop()` 並清空兩個目錄 |
| DB 故障注入 | `BackupApiIT` | `alter table console.backup_jobs rename to backup_jobs_off`（`finally` 與 `@AfterEach` 皆還原；沿 `IssueApiIT`）；walArchive 的故障以 `BackupServiceTest` 的 `JdbcTemplate` 替身（經真實 `WalArchiveStatsAdapter`）為之 |
| 請求目錄故障 | `BackupApiIT`、`FileBackupControlAdapterTest` | 以「同名一般檔案取代目錄」構造寫檔失敗；必還原 |
| Logback 捕捉 | `BackupApiIT`（AT-BK-10-4-1） | `ListAppender` 掛在 root logger，測試後移除 |
| sidecar stub | `BackupSidecarContractIT` | 見 §5.4 |
| 前端 | vitest／Playwright | fetch 替身（沿 `queries.polling.test.tsx`）；`vi.useFakeTimers({shouldAdvanceTime:true})`；`focusManager.setFocused`；Playwright 於 spec 內自帶 `/api/v1/sysadmin/**` 路由（不改 `mockApi.ts`） |

### 5.3 前端與跨端共用詞表、測試鉤

**詞表（住 `lib/domain/sysadminBackup.ts`，測試引用單一份）**：卡片狀態文字（succeeded→成功、failed→失敗、running→進行中、interrupted→中斷、no_run→從未執行）；備份種類文字（full→全備、diff→增備（差異）、incr→增量、logical→邏輯備份）；儲存位置文字（repo1→本地 repo1、repo2→離站 repo2、logical→離站邏輯）；工作狀態文字（QUEUED→排隊中、RUNNING→進行中、SUCCEEDED→成功、FAILED→失敗、REJECTED→被拒絕、EXPIRED→逾時未執行）；`REPO_STATUS_ZH`（鍵 0、1、2、3、4、5、6、99；0 正常、1 缺 stanza 路徑、2 尚無有效備份、3 缺 stanza 資料、4 repo 之間不一致、5 資料庫不符、6 找不到備份、99 其他）；`BACKUP_REASONS`（十三個鍵，見 §C4）；`SCHEDULE_JOB_LABELS`（D-BK-T8）；`VOLUME_COVERAGE`、`RESTORE_STEPS`、`RESTORE_CHECKS`（R-BK-43、R-BK-44）；常數 `BACKUP_JOB_POLL_MS`、`BACKUP_OVERVIEW_POLL_MS`（放 `lib/api/queries.ts`）。

**前端測試鉤**：以 `getByRole`（`tab`、`dialog`、`button`、`alert`）與文字為主；下列 `data-testid` 為輔，名稱逐字固定。

| testid | 元素 |
|---|---|
| `sysadmin-home`、`sysadmin-card-backup` | `/sysadmin` 入口頁；「資料庫備份」入口卡 |
| `bk-page`、`bk-reason-panel`、`bk-banner-offline`（`role="alert"`）、`bk-banner-active`、`bk-stale-mark`、`bk-wal-line` | 備份頁根；整區原因面板；紅色離線橫幅；黃色進行中橫幅；「可能已過期」／「已過期」標記；WAL 歸檔單行 |
| `bk-cards`、`bk-card-<job>`、`bk-badge-<job>`（帶 `data-status`、`data-tone`）、`bk-last-success-<job>`、`bk-latest-<job>`、`bk-overdue-<job>`、`bk-tail-<job>` | 狀態卡區、單卡、徽章、最近一次成功、最近一份備份（來源標示）、逾期標記、輸出尾段（僅 ADMIN）；`<job>`∈full、diff、dump、verify |
| `bk-trigger-full`、`bk-trigger-diff`、`bk-trigger-verify`、`bk-admin-note` | 三顆手動按鈕；「需要 ADMIN 角色才能操作」 |
| `bk-list`、`bk-list-note`、`bk-list-empty`、`bk-row-<label>`、`bk-result-<label>`（帶 `data-tone`＝ok｜warn）、`bk-repo-<n>`、`bk-repo-status-<n>`、`bk-repo-badge-<n>` | 備份清單分頁 |
| `bk-sched-<job>`、`bk-sched-fixed-wal`、`bk-retention` | 排程與保留分頁（`<job>`∈六個排程工作） |
| `bk-jobs`、`bk-job-<id>`、`bk-job-detail-<id>`、`bk-jobs-more`、`bk-jobs-empty` | 工作紀錄分頁 |
| `bk-restore-steps`、`bk-restore-checks`、`bk-no-restore-note`、`bk-coverage`、`bk-coverage-row-<volume>` | 還原與說明分頁 |
| `bk-confirm-dialog`、`bk-confirm-ok`、`bk-confirm-cancel`、`bk-quota-<repo>` | 確認對話框 |

### 5.4 sidecar 測試容器與替身（`BackupSidecarContractIT`）

- 容器：Linux（建議 `debian:bookworm-slim` 加 `bash`、`jq`、`util-linux`〔`flock`〕、`coreutils`、`procps`；以 `ImageFromDockerfile` 預建並快取，**同類別共用一個容器**〔靜態 `@Container`，各測試用各自的 `/tmp/ctl/<測試名>` 目錄；全類別估 3～5 分鐘〕），**以非 root 使用者執行**（略過腳本內的 `gosu`）；掛入三支新腳本與四支 stub 工作腳本（唯讀）；`PATH` 前綴 stub 目錄。
- stub `pgbackrest`：`--output=json … info` 印夾具 `INFO_2REPO`（或依環境變數印失敗／非 JSON／睡眠 N 秒並追加呼叫記錄）；`help expire repo-retention-full`／`-diff` 印 §AT-BK-03-4-1 的三種形態；其餘子命令回 0。stub `mc`：`ls --json` 印 `LOGICAL_2` 對應的行（或非零結束）。
- stub 工作腳本（`backup-full.sh`、`backup-incr.sh`、`pg_dump-offsite.sh`、`verify-backup.sh`）：由環境變數決定行為——睡眠秒數、rc、印 `OUT-LINE`／`ERR-LINE`、寫標記檔（含「啟動時 results 是否已存在」）、背景 `sleep &`、印探針行。
- PATH 前綴 stub：`flock`（記錄 argv 到 `flock.log` 再轉呼叫真 `flock`；AT-BK-09-5-5）、`mv`（對 `jobs/*.json`、`results/*.json` 的改名先睡再轉呼叫真 `mv`；AT-BK-09-3-7）；腳本內改名必須經 `mv`、鎖必須經 `flock` 命令名（才攔得到）。
- 請求與輸出目錄、鎖檔一律建在**容器內本地檔案系統**（例 `/tmp/ctl`，不是 Windows bind mount），才支援 FIFO、符號連結、`chmod` 與 `/proc/locks` 比對。
- 輔助：以 `execInContainer` 取 stdout／stderr／rc 分開；`waitFor(path, timeout)`；持鎖者以 `flock -o <鎖檔> sleep N` 在背景啟動（命令形）。

### 5.5 `OVERDUE_CASES` 與 `QUOTA_CASES`

**`OVERDUE_CASES`**（AT-BK-04-3-1 的表驅動；時區 `Asia/Taipei`；cron：full `0 2 * * 0`、diff `0 2 * * 1-6`、dump `30 2 * * *`、verify `0 4 * * 3`；寬限 30 分；「清單」欄＝各 repo 最近一份符合者的 `stop`〔repo1／repo2〕，`—` 表示該 repo 沒有符合的備份，「無」表示清單端不提供；期望值由本檔作者的參考實作算出並已對照下表人工預期逐列核對）：

| 列 | 工作（cron） | now（+08:00） | 狀態檔成功 | 清單（repo1／repo2） | 進行中 | 期望 `lastDueAt`（UTC） | 期望 `overdue` | 期望 `never` | 說明 |
|---|---|---|---|---|---|---|---|---|---|
| O1 | diff（`0 2 * * 1-6`） | 2026-10-31 04:00 | 2026-10-31 02:00:30 | 無 | 否 | 2026-10-30T18:00:00Z | false | false | 週六 04:00，增備週六 02:00 成功 |
| O2 | diff（`0 2 * * 1-6`） | 2026-11-01 04:00 | 2026-10-31 02:00:30 | 無 | 否 | 2026-10-30T18:00:00Z | false | false | 週日 04:00，增備無週日時段（`lastDueAt` 為週六 02:00） |
| O3 | full（`0 2 * * 0`） | 2026-11-01 04:00 | 2026-11-01 02:00:30 | 無 | 否 | 2026-10-31T18:00:00Z | false | false | 週日 04:00，全備週日 02:00 成功 |
| O4 | diff（`0 2 * * 1-6`） | 2026-11-02 02:15 | 2026-10-31 02:00:30 | 無 | 否 | 2026-11-01T18:00:00Z | false | false | 週一 02:15，寬限內 |
| O5 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 2026-10-31 02:00:30 | 無 | 否 | 2026-11-01T18:00:00Z | true | false | 週一 02:31，增備未成功 ⇒ 逾期 |
| O6 | full（`0 2 * * 0`） | 2026-11-01 02:31 | 2026-10-25 02:00:30 | 無 | 否 | 2026-10-31T18:00:00Z | true | false | 週日 02:31，全備未成功 ⇒ 逾期 |
| O7 | diff（`0 2 * * 1-6`） | 2026-11-02 02:30:00 | 2026-10-31 02:00:30 | 無 | 否 | 2026-11-01T18:00:00Z | false | false | 寬限邊界：`lastDueAt＋30 分整`（嚴格大於） |
| O8 | diff（`0 2 * * 1-6`） | 2026-11-02 02:30:01 | 2026-10-31 02:00:30 | 無 | 否 | 2026-11-01T18:00:00Z | true | false | 寬限邊界：`＋30 分 1 秒` |
| O9 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 2026-10-31 02:00:30 | 無 | 是 | 2026-11-01T18:00:00Z | false | false | 進行中不逾期 |
| O10 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 無 | 無 | 否 | 2026-11-01T18:00:00Z | false | true | 無任何成功 ⇒ `never`、不稱逾期 |
| O11 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 2026-10-31 02:00:30 | 11-02 02:02:00／11-02 02:03:00 | 否 | 2026-11-01T18:00:00Z | false | false | 清單端較新（兩 repo 皆於週一完成） |
| O12 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 2026-10-31 02:00:30 | 11-02 02:02:00／10-31 02:03:00 | 否 | 2026-11-01T18:00:00Z | true | false | 清單端取各 repo 最近者的**最舊者**（repo2 停在週六） |
| O13 | diff（`0 2 * * 1-6`） | 2026-11-02 02:31 | 2026-10-31 02:00:30 | 11-02 02:02:00／— | 否 | 2026-11-01T18:00:00Z | true | false | 某 repo 沒有符合的備份 ⇒ 清單端缺席，只剩狀態檔 |
| O14 | full（`0 2 * * 0`） | 2026-10-27 10:00 | 無 | 10-26 02:10:00／10-26 02:12:00 | 否 | 2026-10-24T18:00:00Z | false | false | F-04：無狀態檔但清單有全備（週一由差異升格） |
| O15 | dump（`30 2 * * *`） | 2026-10-28 03:01 | 2026-10-27 02:31:00 | 無 | 否 | 2026-10-27T18:30:00Z | true | false | 每日工作逾期（`lastDueAt` 為當日 02:30） |
| O16 | verify（`0 4 * * 3`） | 2026-10-28 04:31 | 2026-10-21 04:05:00 | 無 | 否 | 2026-10-27T20:00:00Z | true | false | 每週三 04:00 的驗證逾期 |
| O17 | verify（`0 4 * * 3`） | 2026-10-28 04:29 | 2026-10-21 04:05:00 | 無 | 否 | 2026-10-27T20:00:00Z | false | false | 驗證在寬限內 |
| O18 | full（`0 2 * * 0`） | 2026-11-01 02:00:00 | 2026-10-25 02:00:30 | 無 | 否 | 2026-10-31T18:00:00Z | false | false | `now` 恰為觸發時刻：`lastDueAt` 等於 `now`、未過寬限 |
| O19 | verify（`0 4 * * 3`） | 2026-10-28 04:31 | 無 | 無 | 否 | 2026-10-27T20:00:00Z | false | true | 驗證從未成功 ⇒ `never`、不稱逾期 |
| O20 | verify（`0 4 * * 3`） | 2026-10-29 10:00 | 2026-10-28 04:05:00 | 無 | 否 | 2026-10-27T20:00:00Z | false | false | 距 `lastDueAt` 已逾一天（30 小時）仍須以週三 04:00 為 `lastDueAt`（殺過短的回溯窗） |

**`QUOTA_CASES`**（AT-BK-06-1-1；`retention`＝repo1 `{full:4,diff:7}`、repo2 `{full:4,diff:null}`）：

| 列 | type | repo | 現有備份（舊→新） | 期望 |
|---|---|---|---|---|
| Q1 | full | 1 | 全備 4：`20260928-020000F`、`20261005-020000F`、`20261012-020000F`、`20261019-020000F` | `{repo:1,kind:"full",current:4,limit:4,willExpire:true,oldestLabel:"20260928-020000F"}` |
| Q2 | full | 1 | 全備 3：`20261005-020000F`、`20261012-020000F`、`20261019-020000F` | `current:3`、`willExpire:false` |
| Q3 | diff | 1 | 全備 2（`20261012-020000F`、`20261019-020000F`）＋差異 5（`20261012-020000F_20261013-020000D`、`…_20261014-020000D`、`…_20261015-020000D`、`20261019-020000F_20261020-020000D`、`…_20261021-020000D`） | `{repo:1,kind:"diff",current:7,limit:7,willExpire:true,oldestLabel:"20261012-020000F_20261013-020000D"}` |
| Q4 | diff | 1 | 全備 1（`20261019-020000F`）＋差異 2 | `current:3`、`willExpire:false` |
| Q5 | diff | 2 | repo2 任意備份 | repo2 的 diff 上限為 null ⇒ 該 repo 不輸出任何項 |
| Q6 | verify | 1、2 | 任意 | 回空陣列（無保留名額） |
| Q7 | full | 2 | 全備 4：`20260928-020002F`、`20261005-020002F`、`20261012-020002F`、`20261019-020002F` | `{repo:2,kind:"full",current:4,limit:4,willExpire:true,oldestLabel:"20260928-020002F"}` |

### 5.6 backend 與前端夾具細節

| 載具 | 夾具與輔助 |
|---|---|
| `BackupApiIT` | 沿 `AbstractApiIT`（`jdbc`；每測試 `TRUNCATE console.audit_log`）；`@BeforeEach` 另 `TRUNCATE console.backup_jobs` 並清空 `@TempDir` 出的兩個目錄（由 `@DynamicPropertySource` 注入 `console.backup.export-dir`、`console.backup.request-dir`，並把 `console.backup.reconcile-interval-ms` 設成很大的值，使排程輪詢不與測試的明確呼叫賽跑）；`support/BackupSeam`＋`support/FakeBackupRunner`（§5.2）；測試直接呼叫 `BackupJobReconciler.reconcileOnce()` 取得確定性。**時鐘（必讀）**：只撥專屬 `BackupClock`；全域 `Clock` 不動，所以 `AbstractApiIT` 的 JVM 靜態 token（`:29,36-45`）照常使用、不必重鑄，也不會因本類別先跑而讓同 fork 的其餘 IT 全部 401；`MutableClock` 須為執行緒安全（假 runner 與對帳執行緒同讀）。**審計列**：`audit_log.occurred_at` 取自全域 `Clock`（`AuditLogWriter`），測試不撥它，所以對審計列一律以 `method`、`path`、`http_status` 篩選比對，不依時間序 |
| `BackupApiUnconfiguredIT` | 沿 `AbstractApiIT`，不設任何 `console.backup.*`（＝未設定情境，共用預設 context） |
| `FileBackupControlAdapterTest` | `@TempDir`；純 Java 檔案 I/O；Windows 與 Linux 皆跑 |
| `BackupDomainTest` | 無 Spring；只測 `BackupMasker`；讀 `docker/pgbackrest/tests/fixtures/mask-probes.txt`（相對 backend 專案目錄 `..\docker\pgbackrest\tests\fixtures\mask-probes.txt`） |
| `BackupServiceTest` | 無 Spring；假 `BackupJobRepository`（記憶體實作，記錄呼叫序與敘述）、假 `BackupControlPort`（記憶體或 `@TempDir`）、假 `WalArchiveStatsPort`（AT-BK-04-6-2 改用真實 `WalArchiveStatsAdapter` 接 `JdbcTemplate` 替身）、假 `BackupSettings`；`MutableClock` 即專屬時鐘 |
| `BackupJobMigrationIT` | 沿 `IssuePriorityMigrationIT` 的 `flyway(database, null)` 作法（先 migrate 到 14、再到 15）；映像沿 `SharedPostgres.java:14`（`pgvector/pgvector:pg18`） |
| `BackupArchTest`、`BackupReasonsContractTest` | 沿 `IssuePriorityArchTest`（純函式掃描＋自帶負控）與 `IssueReasonsContractTest`（契約表解析）；契約檔路徑 `..\docs\02_architecture\API_Contract_SysAdminBackup.md` |
| frontend | 元件測試沿 `IssuesView.test.tsx` 的 API mock 與角色切換作法；夾具檔 `components/domain/sysadmin/tests/backup.fixtures.ts`（置於 `tests/` 子目錄；內容＝§5.1 的 JSON 形與各狀態的卡片、`repos`、`walArchive`）；Playwright 沿 `issues.mock.spec.ts` 作法在 spec 內自帶路由；`sysadmin-backup-docker.stack.ts` 走 `docker.config.ts`（stack 載具，需全棧） |

### 5.7 允許變更的檔案集合（`git diff --name-only <base>` 必須 ⊆ 本節；「同步鎖」＝PRD §9.4〈需同步改的既有鎖〉逐檔逐行，於基準 `000a217b` 重核，皆為同 commit 的可見上修、不刪斷言；路徑除標明者外相對 `AgentConsole/`）

**S 包（sidecar＋compose＋Prometheus＋README）**

| 路徑 | 類別 | 內容 |
|---|---|---|
| `docker/pgbackrest/scripts/job-run.sh`、`backup-ctl-export.sh`、`backup-ctl-runner.sh` | 新增 | §C2；LF、0755、shellcheck 全嚴重度乾淨 |
| `docker/pgbackrest/tests/**` | 新增 | `stubs/`（`pgbackrest`、`mc`、`flock`、`mv`、四支 stub 工作腳本）、`fixtures/mask-probes.txt`（R-BK-42 單一來源）、`fixtures/info-2repo.json`、`fixtures/logical-2.json` |
| `docker/pgbackrest/crontab` | 修改 | `:6,9,12,15`（HEAD 依序為 backup-full、backup-incr、pg_dump-offsite、verify-backup 四列）改經 `job-run.sh <job> scheduled`；`:18`（expire）、`:21`（WAL 清理）不動 |
| `docker/pgbackrest/scripts/pgbackrest-entrypoint.sh` | 修改 | `:56-67`（指標目錄、背景指標迴圈、httpd、crond）前後：root 階段 `install -d`、`backup-ctl-export.sh schedule`、背景啟 runner |
| `docker/pgbackrest/scripts/pgbackrest-metrics.sh` | 修改 | `:93-105`（`.last_backup_status` 區塊）之後追加三指標；`:3-22` 檔頭註解同步 |
| `docker/pgbackrest/Dockerfile` | 修改 | `:36-43`：`install -d -o postgres -g postgres -m 0755 /backup-out /run/backup-ctl`（不得沿 `:39` 的 0750） |
| `docker-compose.yml` | 修改 | 頂層 `volumes:`（`:796-818`）階一加 `backup_out`、階二加 `backup_req`；pgbackrest（`:559-564`）掛 `backup_out:/backup-out`、階二 `backup_req:/backup-req:ro,nocopy`；backend（`:170-175`）掛 `backup_out:/backup-out:ro,nocopy`、階二 `backup_req:/backup-req`，並設 `CONSOLE_BACKUP_OUT_DIR=/backup-out`、`CONSOLE_BACKUP_REQ_DIR=/backup-req` |
| `.env.example` | 修改（選填） | 不得新增機密；兩個目錄變數為 compose 字面常數，預設不需新增 |
| `backend/Dockerfile` | 修改（階二） | `:32` 之後建 `/backup-req`（屬 `spring:spring`、0755） |
| `docker/prometheus/alerts.yml` | 修改 | 末尾（HEAD `:118` 之後）`aisdlc-backup` 群組加兩條規則 |
| `docker/prometheus/tests/backup_alerts_test.yml` | 新增 | promtool 單元測試（比照 `tests/slo_test.yml`） |
| `docker/README.md` | 文件連動 | `:60-69` 卷表加兩卷；`:384`「共 12 條」→「共 14 條」；新增〈4.6 控制面〉；〈9〉加 #35；〈10〉補新規則的盲區；**〈4.3〉不改**（本案只讀；帳本案若改它，AC-BK-08-1 只鎖指令，不紅） |
| `engine-bridge/tests/test_backup_ctl_deploy_config.py` | 新增 | PyYAML 旗標鎖：掛載旗標、卷數 13／14、Dockerfile、crontab、alerts 載入與規則名、backend 無機密環境 |
| `backend/src/test/java/com/aisdlc/console/sidecar/BackupSidecarContractIT.java` | 新增（S 包寫在 backend 測試樹） | Testcontainers 契約測試；與 K 包無檔案重疊 |
| `engine-bridge/tests/test_deploy_config.py`、`test_si_deploy_config.py` | **已複核不改** | `test_deploy_config.py:99-108`（backend 區塊子字串檢查）、`:226-242`；`test_si_deploy_config.py:232-281,428-448`（只驗 engine-bridge 掛載與 backend SI 變數）不受新增掛載影響；G-S4 實跑 |

**K 包（console-api）**

| 路徑 | 類別 | 內容 |
|---|---|---|
| `backend/src/main/java/com/aisdlc/console/` 下：`adapter/in/web/BackupController.java`＋`dto/Backup*`；`application/port/in/*`、`application/port/out/{BackupControlPort,BackupJobRepository,WalArchiveStatsPort,BackupSettings,BackupClock}`；`application/service/{BackupQueryService,BackupJobService,BackupJobReconciler,BackupCron,BackupOverdue}`；`domain/model/backup/{BackupMasker,BackupJobReason}`；`adapter/out/persistence/{BackupJobAdapter,WalArchiveStatsAdapter}`；`adapter/out/control/FileBackupControlAdapter`；`infrastructure/config/{BackupProperties,BackupSettingsAdapter,BackupClockConfig}`；`db/migration/V15__backup_jobs.sql`（階二；在 `src/main/resources/`） | 新增 | PRD §9.4；名稱不符 `Si*Controller`，不受 `SiReadOnlyArchTest.java:72,91-92` 計數鎖；`WalArchiveStats*`、`BackupJobReason`、`BackupCron`、`BackupOverdue`、`BackupMasker`、`BackupSettings`、`BackupClock` 為本檔命名（D-BK-T3、T20）；**落點（勘誤 1-4）**：`ArchitectureRulesTest.java:23-28、32、52` 與 `SiReadOnlyArchTest.java:124-134` 已複核、**不放寬**——Spring 相依者（`BackupCron`、`BackupOverdue`）不進 domain，設定與時間經 port.out（先例 `RuntimeSettings`、`SiWriteSettings`、`SoftDeletePurge.java:43-50`） |
| `backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java` | 修改（階二） | `:41-53` 說明加一條；`:84-92` 於通用規則**之前**加 `POST /api/v1/sysadmin/**`＝ADMIN |
| `backend/src/main/java/com/aisdlc/console/domain/exception/ErrorReasons.java` | 修改（階二） | `:144`（`ISSUE_NOT_RANKABLE`）之後加五個 `BACKUP_` 前綴常數 |
| `backend/src/main/resources/application.yml` | 修改 | `:136-142`（`console.si`）旁加 `console.backup.*`（全預設空＝停用；依 `${CONSOLE_BACKUP_OUT_DIR:}` 形） |
| `backend/src/main/java/com/aisdlc/console/adapter/in/web/ErrorResponseDocumentation.java` | 條件修改 | 以 `OpenApiIT` 紅綠為準（先例議題中心 D-C14）：`CONFLICT_ENDPOINTS` 加 `POST /api/v1/sysadmin/backups/jobs`、`EXTRA` 加 400／422／503 說明、`NOT_FOUND_DESCRIPTION` 加單筆工作 |
| `backend/src/test/java/com/aisdlc/console/` 下：`adapter/in/web/{BackupApiIT,BackupApiUnconfiguredIT}.java`、`adapter/out/control/FileBackupControlAdapterTest.java`、`domain/model/backup/BackupDomainTest.java`、`application/service/BackupServiceTest.java`、`infrastructure/persistence/BackupJobMigrationIT.java`、`architecture/{BackupArchTest,BackupReasonsContractTest}.java`、`support/{MutableClock,FakeBackupRunner,BackupSeam}.java` | 新增 | §3.1 載具表；`BackupReasonsContractTest` 映像沿 `SharedPostgres.java:14` |
| `backend/src/test/java/com/aisdlc/console/infrastructure/config/OpenApiIT.java` | 同步鎖 | `:136、:160`（`hasSize(74)`→75→77）、`:144`（85→86→89）、`EXPECTED` `:38` 起加三路徑；`:28-35` 檔頭說明加一段 |
| `backend/src/test/java/com/aisdlc/console/infrastructure/persistence/{SchemaMigrationIT,V5UpgradeMigrationIT,SiConsoleWritesMigrationIT,IssuePriorityMigrationIT}.java` | 同步鎖（階二） | `:68`、`:135`、`:129`、`:131`（版本清單補 "15"） |
| `docs/02_architecture/API_Contract_SysAdminBackup.md` | 新增 | 依 §C 逐表抄成（TCS 為真相）；〈backup 類 reason 表〉與 `ErrorReasons`、`BACKUP_REASONS` 雙向鎖 |
| `docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md` | 新增（本檔） | 規格文件；凍結後只准追加〈勘誤〉節與檔頭 digest 更新 |
| `docs/02_architecture/Architecture.md` | 文件連動 | §2.5 `:169-186`（卷 12→13→14）、§5.1 `:300-331`（路由樹加 `/sysadmin`）、§7.2 `:612-634`（`backup_jobs` 所有權列；PRD 引 `:614-618`）、§8.2 `:658-676`（RBAC）、§9.4 `:854-870`（環境變數）、§11.1 `:960-983`（端點與 reason） |
| `docs/06_quality/RTM.md` | 收尾（主控） | 新增子表；開發棒交 rtm_backfill 檔、不直接改 |

**F 包（前端）**

| 路徑 | 類別 | 內容 |
|---|---|---|
| `frontend/app/sysadmin/page.tsx`、`app/sysadmin/backup/page.tsx` | 新增 | 只殼；title 各為「系統管理」「資料庫備份」 |
| `frontend/components/domain/sysadmin/`：`SysAdminHome`、`BackupView`、`BackupStatusCards`、`BackupList`、`BackupSchedule`、`BackupJobsLog`、`BackupHelp`、`BackupTriggerDialog`、`WalArchiveLine`（`.tsx`）；`tests/backup.fixtures.ts`；`SysAdminHome.test.tsx`、`BackupView.test.tsx`、`BackupTriggerDialog.test.tsx`、`sysadmin.static.test.ts`、`backup-docs.test.ts` | 新增 | 元件拆分可調整，但測試檔名與 `data-testid`（§5.3）固定；新函式不以 `Si` 起頭 |
| `frontend/lib/domain/sysadminBackup.ts`、`lib/domain/sysadminBackup.test.ts` | 新增 | 純函式與詞表（§5.3） |
| `frontend/lib/nav/sysadmin-nav.test.ts` | 新增 | 九項登記表與 match |
| `frontend/tests/e2e/sysadmin-backup.mock.spec.ts`、`tests/e2e/sysadmin-backup-docker.stack.ts` | 新增 | mock 版進 CI；stack 版為真機證據（非每 commit 閘） |
| `frontend/lib/api/{endpoints,queries,types}.ts`、`lib/api/schema.d.ts` | 修改 | 階一 `getBackupOverview`＋型別；階二另三函式；`BACKUP_JOB_POLL_MS`、`BACKUP_OVERVIEW_POLL_MS`；`schema.d.ts` 由 `npm run gen:api`（backend 在線）重產入庫 |
| `frontend/lib/nav/registry.ts` | 修改 | `:11` 註解「八項」→「九項」；`:36-95` 末尾（`:94` 之後）加 `sysadmin` 一列（`Database`） |
| `frontend/vitest.config.mts` | 修改 | `coverage.include`（`:71` 旁）加 `lib/domain/sysadminBackup.ts`（先例 `lib/domain/issues.ts`）；門檻（lines 70、statements 70、functions 70、branches 60）不動 |
| `frontend/lib/nav/issues-nav.test.ts` | 同步鎖 | `:17-34`：`:18` 長度 8→9、`:19` id 清單末尾加 `"sysadmin"`、`:27` 顯示序加 `"sysadmin"` 於 settings 與 self-improving 之間、`:32-33` order 唯一與 icon 互異 8→9；`:23` 的 `NAV_REGISTRY[7]` 斷言保留 |
| `frontend/lib/nav/registry.test.ts` | 同步鎖 | `:16-42`（`PATHS` 補 `/sysadmin`、`/sysadmin/backup`、`/sysadmin-x`）、`:100-109`（`AT_932_6_1` 長度、id、label、order〔補 65〕、mobile〔補 false〕、集合大小 8→9）、`:122`（icon 互異 8→9）、`:138`（字串 href 清單補 `/sysadmin`）、`:350-361`（`AT_950_10_E_1` 改述「原八列不變，另加系統管理」並補第九列） |
| `frontend/components/layout/ToolsRegion.test.tsx` | 同步鎖＋擴充 | `:76-95`（`AT_932_6_5`：預期序與 `others` 清單補「系統管理」；示範項 order 56 仍介於議題中心與系統設定之間）、`:115`（`original` 補「系統管理」）、`:121`（標題的「八項」）、`:147`（8→9）、`:154-161`（9 個連結；`max-md:hidden` 判準加「系統管理」）；另加 AT-BK-01-3-1 一個 `it` |
| `frontend/lib/api/endpoints.test.ts`、`lib/api/si.endpoints.test.ts` | 同步鎖 | `endpoints.test.ts:198-201`（83→84→87，`EXPECTED` 加對應列）；元鎖 `si.endpoints.test.ts:43-46`（釘值字串同步） |

**條件列（只在條件成立時才改；開工先查）**

| 條件 | 路徑 | 內容 |
|---|---|---|
| 每頁說明案先落地（`frontend/lib/help/registry.ts` 已存在） | `frontend/lib/help/sysadmin.ts`、`lib/help/sysadmin-backup.ts`、`lib/help/registry.ts`；若內容先入 `PENDING_HELP_PAGES` 則另含 `lib/help/registry.test.ts`（僅 `PENDING_CEILING` 一個常數，同 commit 上修） | 補兩個說明項並登記 `HELP_ROUTES` 兩個鍵（`/sysadmin`、`/sysadmin/backup`），使 AC-PH-03-1／03-2／03-4（HEAD `Console_PageHelp_PRD.md:89／:90／:92`；姊妹 TCS 的 AT-PH-03-1-1、AT-PH-03-4-1、AT-PH-03-6-1）保持綠；內容可先入 `PENDING_HELP_PAGES`（AC-PH-03-6）；AT-BK-01-2-4。本案先落地則由每頁說明案實作時納入（其 TCS D-PH-14 已載明） |
| 帳本改 DB 案若採專屬 PG 容器而新增具名卷 | `docker-compose.yml`、`frontend/components/domain/sysadmin/` 的 `VOLUME_COVERAGE`、`docker/README.md` 卷表 | 同 commit 補分類（AC-BK-08-3 的雙向相等會紅）；不得只改一邊 |

**已複核不需改**：`frontend/components/layout/ToolsRegion.tsx`（登記表驅動）、`si-login-gate.test.tsx:65-67`、`layout.test.tsx:135-137`、E2E 的導覽斷言（`tests/e2e/shells-and-layout.spec.ts:26-41`、`p9-w7-ui.spec.ts:180-206`；逐名點選、不計項數，G-F5 以真跑複核）。**不得變更**：`frontend/lib/api/reasons.ts`、`docs/02_architecture/API_Contract_P3-6.md`、`docker/pgbackrest/scripts/{backup-full,backup-incr,pg_dump-offsite,verify-backup,restore,setup-replica,pgbackrest-as-postgres}.sh`、`docker/pgbackrest/pgbackrest.conf`、`engine-bridge/app/**`、`ArchitectureRulesTest.java`、`SiReadOnlyArchTest.java`（分層鎖不放寬）、既有 `Si*`、`Issue*` 檔（除上列同步鎖）、根層 `tools/`、`.claude/`、`.github/`、`AutoClaude/`、`AISDLC_SDD/`、PRD（凍結檔，只准追加〈勘誤〉節）。

## 6. RTM 連結確認

### 6.1 US → FR → AC → AT（數字由 §1、§3 機械計算；AC 54／54）

| FR | US | AC 數 | 正向 AT | 反向 AT | 真機 AT | 載具 | R 條文 |
|---|---|---|---|---|---|---|---|
| FR-BK-01 | US-BK-01 | 3 | 8 | 4 | 0 | FN、FT、FH、FP、E2、GT | R-BK-01～03、R-BK-61 |
| FR-BK-02 | US-BK-02 | 6 | 12 | 6 | 1 | FV、FL、FS、ES、BQ、BS | R-BK-04～09 |
| FR-BK-03 | US-BK-03 | 4 | 8 | 5 | 0 | FV、FL、BQ、BV、BS | R-BK-10～14 |
| FR-BK-04 | US-BK-04 | 6 | 15 | 8 | 1 | FV、FS、BQ、BV、BA、BS、RM | R-BK-15～22 |
| FR-BK-05 | US-BK-05 | 5 | 11 | 7 | 1 | FV、ES、BQ、BU、BV | R-BK-22～28 |
| FR-BK-06 | US-BK-06 | 11 | 35 | 12 | 3 | FV、FD、FL、ES、BQ、BF、BV、BM、BA、BC、BS | R-BK-29～39、R-BK-60 |
| FR-BK-07 | US-BK-07 | 3 | 9 | 4 | 0 | FV、BQ、BD、BS、GT | R-BK-21、R-BK-40～42、R-BK-60 |
| FR-BK-08 | US-BK-08 | 3 | 5 | 4 | 0 | FV、FL、FK、PY | R-BK-43～45 |
| FR-BK-09 | US-BK-09 | 8 | 32 | 12 | 4 | BQ、BS、PY、PT、GT、RM | R-BK-20、R-BK-33、R-BK-46～54、R-BK-61、R-BK-62 |
| FR-BK-10 | US-BK-10 | 5 | 13 | 6 | 0 | BQ、BM、BA、PY、GT | R-BK-14、R-BK-35、R-BK-55～59 |
| 合計 | 10 | 54 | 148 | 68 | 10 | | R-BK-01～R-BK-62（62 條） |

### 6.2 行為規則與非功能（PRD §6）→ AT（R→AT 見 R 條文表的 AT 欄；下表為 NFR→AT）

| NFR | 條文 | 覆蓋 AT（AC 簡碼） |
|---|---|---|
| 安全（STRIDE 精簡） | 偽造身分→JWT＋ADMIN 規則；竄改→兩卷 mount 方向、請求只認封閉詞彙；否認→兩列審計；外洩→兩道遮罩、非 ADMIN 不見尾段；阻斷→單工、TTL、檔數與頻率上限；提權→無 docker socket、console-api 無 cipher 與 S3 金鑰 | 04-5、06-2、06-4、06-6、06-7、06-10、07-2、07-3、09-2、09-6、10-2、10-3、10-4 |
| 效能 | `GET /backups` 每請求讀 8 個小檔、不快取、本機目標 ≤500 ms；觸發到 DB 轉 RUNNING ≤10 秒 | 05-4（不快取：每次重讀）、06-3、06-11（以輪詢預算判定；≤500 ms 列真機 V1 觀察，不寫成會因機器慢而紅的單元斷言） |
| 並發與逾時 | 同時只允許一個進行中工作（DB 與 sidecar 兩層）；逾時值見 §C3.5 | 06-4、06-6、06-8、09-3 |
| 無障礙 | 沿用 `PillTabs`、`Dialog`、`Button`；徽章文字加圖示；橫幅 `role="alert"` | 04-1、05-2、06-1 |
| 跨平台 | console-api 純 Java 檔案 I/O（Windows 以 `@TempDir`）；sidecar 只在 Linux 容器（shellcheck、`bash -n`）；具名卷；時間戳帶 `Z` | 06-9、09-3、09-4（G-S1） |
| 零侵入面 | 改動只在 `AgentConsole/**`；備份腳本本體零修改 | 09-4（G-S2、G-C1） |
| fail-loud | 量不到顯示原因、絕不顯示成 0 | 02-5、04-6、05-1、05-3、08-3 |

## 7. 已結裁決與 PRD〈勘誤〉草稿（掌舵者可隨時以 T1 推翻；推翻走本檔修訂）

### 7.1 已結裁決（Q1～Q10 全數由主控代決結案，一審後）

| # | 問題 | 裁決（出處） |
|---|---|---|
| Q1 | Q7 的 WAL 歸檔一行，PRD 沒有 AC | 採：留 `AC-BK-04-6`、`walArchive` 欄（D-BK-T20）；PRD 補條走勘誤 1-1 |
| Q2 | 回送位址（`127.0.0.1`、`::1`、`host.docker.internal`）視為本機 | 採（D-BK-T21）；PRD AC-BK-02-6 字面走勘誤 1-5 |
| Q3 | 既有 12 條規則補 promtool | 否：只測新增兩條（D-BK-T19） |
| Q4 | `ok:false` 的處置 | 採來源級降級（D-BK-T5）；PRD 走勘誤 1-9 |
| Q5 | 增備頻率基準 | 採最近差異備份、嚴格小於門檻（D-BK-T12） |
| Q6 | `BackupSidecarContractIT` 進 CI backend job | 採；估 3～5 分鐘，同類別共用一個容器（靜態 `@Container`，映像預建快取）；本機無 Docker 回報工具缺席、不得綠 |
| Q7 | 清單端成功時間「任一 repo 缺席＝缺席」 | 採（D-BK-T10） |
| Q8 | results 不可寫時不執行請求 | 採（R-BK-47）；兜底：QUEUED 逾 2×TTL 不論心跳由 console-api 標 EXPIRED（R-BK-34；勘誤 1-10） |
| Q9 | 請求檔名限小寫 UUID | 採（AT-BK-09-2-E-2） |
| Q10 | README〈4.3〉補核對三項 PowerShell 指令行 | 否（D-BK-T23；PRD 勘誤 1-7） |

其餘預設裁決見檔頭 D-BK-T1～T24。

### 7.2 開放問題

無（Q1～Q10 已於 §7.1 結案）。

### 7.3 PRD〈勘誤〉草稿（PRD 已凍結、本檔不改它；PRD 現止於 §14、沒有〈勘誤〉節；座標為 2026-10-27 的 PRD 行號）

貼上方式：PRD 檔尾新建 `## 勘誤`（標題與用語沿議題中心 PRD 先例）與 `### 勘誤一（日期）`，內容為下表五欄（條、位置、原文、訂正、理由）；本檔勘誤與 PRD 勘誤引同一條號（〈凍結後修訂路由〉第 2 點）。

| 條 | 位置 | 原文 | 訂正 | 理由（WHY） |
|---|---|---|---|---|
| 1-1 | §5 FR-BK-04 表尾（`:87` 之後）、§8.3 `GET /backups` 列（`:200`） | （無對應 AC；§13 Q7 欄寫「只多一個 AC」`:298`） | 新增 `AC-BK-04-6`：Given 任一角色開頁 When 顯示 Then 一行唯讀「WAL 歸檔：最近 <時間>・失敗 N 次」（console-api 以一條唯讀 SELECT 讀 `pg_stat_archiver`；`GET /backups` 新增 `walArchive:{lastArchivedAt, failedCount, lastFailedAt}`）；`failedCount>0` 且最近失敗晚於最近歸檔＝警示色；查不到顯示「WAL 歸檔：—」、不當 0，且不影響 `canTrigger`、`activeJob` 與其他區塊。§8.3 該列補 `walArchive` | 掌舵者 Q7 裁決（`:301`）已採，§5 與 §8.3 漏列 |
| 1-2 | AC-BK-09-7（`:121`） | 「追加 `aisdlc_backup_job_last_status{job}`、`aisdlc_backup_job_last_finished_timestamp_seconds{job}`、`aisdlc_backup_ctl_heartbeat_timestamp_seconds`」…「且每條規則名都出現在 promtool 測試檔」 | 標籤改 `backup_job`（規則 expr 同改 `backup_job=~"dump\|verify"`）；「每條**新增**規則名」（既有 12 條不要求） | Prometheus 目標標籤 `job="pgbackrest"`（`prometheus.yml:30-33`，未設 `honor_labels`）與曝光的 `job` 相撞，曝光值被改名 `exported_job`，`{job=~…}` 永不匹配；既有 12 條沒有 promtool 測試 |
| 1-3 | §8.2 heartbeat 列（`:193`） | `{ts, lock_held}` | `{schema_rev:1, ts, lock_held}` | AC-BK-05-3 以 `schema_rev` 判必讀檔；heartbeat 是必讀檔之一（§6 `:133`），無版本欄就無判準 |
| 1-4 | §9.4 console-api 新增列（`:235`） | 「`application/{port/{in,out}/Backup*,service/{BackupQueryService,BackupJobService,BackupJobReconciler}}`」…「`domain/model/backup/`（cron 前後時刻、逾期、遮罩純函式）」…「`infrastructure/config/BackupProperties`」 | `application/port/out/` 加 `BackupSettings`、`BackupClock`；`application/service/` 加 `BackupCron`、`BackupOverdue`；`domain/model/backup/` 只留遮罩函式與工作理由列舉；`infrastructure/config/` 加 `BackupSettingsAdapter`（`BackupProperties` 只作綁定） | `ArchitectureRulesTest.java:23-28`（A1）禁 domain 依賴 `org.springframework..`，而 `BackupCron` 用 Spring `CronExpression`（AC-BK-03-3）；`:32`、`:52`（A2、A5）禁 application、domain 依賴 infrastructure，設定須經 port.out（先例 `RuntimeSettings`、`SiWriteSettings`） |
| 1-5 | AC-BK-02-6（`:76`） | 『端點主機名不含 `.`（compose 服務名，例 `minio`）或為 `localhost` 者標「本機 MinIO・與主機同碟，主機損毀時一併消失」』 | 並含回送位址（`127.0.0.0/8`、`::1`）與 `host.docker.internal` | 這些位址只可能指向同一台主機；不加嚴會把本機儲存顯示成「外部 S3」，與 Q8 裁決（`:299`）的目的相反 |
| 1-6 | AC-BK-04-3（`:85`） | 「…最近成功時間缺席或早於 `lastDueAt`…；從未成功＝`never:true`、不稱逾期」 | 「…最近成功時間早於 `lastDueAt`（缺席＝從未成功＝`never:true`、`overdue:false`）…；寬限比較嚴格大於（恰 30 分整不逾期）」 | 兩句字面互斥（缺席即逾期 vs 從未成功不稱逾期）；寬限邊界未寫 |
| 1-7 | AC-BK-08-1（`:111`） | 「bash 與 PowerShell 雙形態」；「UI 的每條指令都須逐字出現在該節 code block」 | 雙形態限還原三步；核對三項只有 bash 形態、UI 另以一句話說明 PowerShell 前後綴；比對時 code block 每行去前後空白 | README 核對三項的 PowerShell 形態只是一句說明（`docker/README.md:270`），沒有指令行；code block 縮排兩格（`:272-279`） |
| 1-8 | AC-BK-08-3（`:113`） | 「自 `^volumes:$` 到下一個頂格鍵」 | 「到下一個頂格鍵或檔尾」 | `volumes:` 是 compose 最後一個頂層鍵（`docker-compose.yml:795`），其後只有檔尾 |
| 1-9 | AC-BK-05-3（`:91`） | 「`schema_rev` 不是 1 或 JSON 損毀」 | 另加：匯出行程自報失敗（`ok:false`，檔案合法）＝該來源的衍生區塊缺席並加 `info_unavailable`／`logical_unavailable`、`reason` 仍 null、其餘照常；兩類損毀並存 `schema_mismatch` 優先；`not_configured` 優先於一切 | 處置未寫；MinIO 掛掉時最需要看狀態卡 |
| 1-10 | AC-BK-06-6（`:100`） | 「runner 離線（心跳過期）時才由 console-api 標 EXPIRED」 | 另加兜底：QUEUED 逾 2×`request-ttl-seconds` 且仍無 results 時，不論心跳 console-api 條件式標 EXPIRED | results 不可寫時 runner 不執行請求（R-BK-47）而心跳照常，列會永遠 QUEUED，部分唯一索引使其後的觸發全部 409 |
| 1-11 | AC-BK-09-6（`:120`） | 『「進行中但鎖未持有」者改記 `interrupted`』 | 含 `results/<id>.json` 為 running 且鎖無持有者（距撿起逾 6×輪詢間隔＝30 秒） | runner 寫 results 後、`job-run.sh` 取鎖並寫狀態檔前被殺，列會永遠 RUNNING（心跳新鮮，`timeout` 不成立） |
| 1-12 | §8.2 各列內容欄（`:188-194`） | （摘錄）`retention:{…}`、`repos:[…]`、results 的 reason、schedule 的 job 名等未寫死 | 以 TCS §C1 欄位表為準（含 `retention` 內 null 兩種語意、results reason 詞彙、job 值域） | 欄型與詞彙 PRD 未寫死，TCS 已定案 |
| 1-13 | §9.4 條件列（`:239`） | 『AC-PH-03-1（撰寫時 `:90` 路由集合＝`HELP_ROUTES` 鍵）、AC-PH-03-2（`:91` enabled 導覽項皆有說明）、AC-PH-03-4（`:93` 頁檔 id＝`HELP_PAGES`∪`PENDING_HELP_PAGES`）』 | `:89`／`:90`／`:92`（2026-10-27 重核） | 行號隨稿漂移（PRD 已自述） |
| 1-14 | §11 階段一出口與真機 V 系列（`:262`、`:271-274`） | 階段一：「真機 V1、V2、V3、V6」 | 加 V10：Prometheus `/api/v1/query` 取得的 `aisdlc_backup_job_last_status{backup_job="dump"}` 帶目標標籤 `job="pgbackrest"`、無 `exported_job`；人造一次 dump 失敗後 `PgBackRestJobFailed` firing | promtool 的人造序列看不出抓取層的標籤相撞，只有真抓取驗得出（勘誤 1-2） |
| 1-15 | AC-BK-09-2（`:116`） | 「非法請求（檔名非 UUID、非常規檔或符號連結、>4 KB、非 JSON、未知 type、已過期、目錄內檔數 >16）When 掃描 Then 不執行任何命令；可寫時寫 `rejected` 結果（封閉詞彙理由），否則只記 WARN」 | 於該句後加：「目錄內檔數 >16 者為目錄級拒絕：不執行任何請求、不寫任何 results、只記 WARN；被漏處理的合法請求由 AC-BK-06-6 的 2×`request-ttl-seconds` 兜底標 EXPIRED（勘誤 1-10）」 | 檔數超限時無從判斷哪一份是合法請求，沒有單一請求可對應一份 `rejected` results；也不該把擠爆目錄放大成十六份以上的寫入 |

## SCG-4 通過標準

**通過條件**（全部成立才算過；審查報告逐字貼各 G 指令的 rc 與輸出尾段）：

1. **AC 54／54**：每個 AT 的判定指令 rc 0 且收集 ≥1 個測試（§2 零測試規則）；審查閘型 AT 以所指 G 編號指令的輸出為證；真機 AT（`RM`、`ES`）依 PRD §11 出口分階段由掌舵者或主控留證。
2. **三包閘門全綠**：S 包 G-S1～G-S7、K 包 G-K1～G-K3、F 包 G-F1～G-F6、共同 G-C1～G-C5（真機 G-V 另依階段出口）。
3. **突變**：R 條文表的 R-BK-01～R-BK-62 每條至少一個突變轉紅（killed）；倖存者補 AT 並勘誤。
4. **兩道契約對拍**：控制面協定兩端（`FakeBackupRunner`＋`BackupApiIT` 對 `BackupSidecarContractIT`）以 §C1 為準互相印證——兩端各自的夾具逐欄等於 §C1 的範例形；`mask-probes.txt` 兩端共讀同一檔。
5. **出口判準（PRD §11）**：階段一＝階一 AT 與 M 項全綠＋真機 V1、V2、V3、V6、V10；階段二＝全部 AT 全綠＋M1～M6＋真機 V4、V5、V7、V8、V9。
6. 無 P1、P2 未結；凍結與放行依根 CLAUDE.md〈凍結常態規則〉與 BRIDGE §8。

**閘門指令**（`<repo>`＝monorepo 根，現查 `git rev-parse --show-toplevel`；`<base>`＝開發棒開工時的 HEAD、`<snap>`＝同一時刻 `git status --porcelain -uall` 的輸出檔，皆由主控在任務書寫明；每條在「目錄」欄執行；PowerShell 形態、rc 先存變數再讀、不得裸 `cd`、shell 狀態不跨呼叫（Python 閘門的 venv 啟動須與指令在同一呼叫內））：

```powershell
# Python 閘門（Bridge 目錄 pytest）：同一呼叫內先啟根 venv
Push-Location <repo>\<目錄>; & <repo>\.venv\Scripts\Activate.ps1; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# backend、frontend、docker、git 閘門：不需 venv
Push-Location <repo>\<目錄>; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# git status 閘門（G-C1～G-C4）：輸出逐行去掉 <snap> 已有的行，剩下的才判定（既有髒檔不計，例 AutoClaude/.perf_baseline.toml）
$snap = Get-Content -LiteralPath <snap 檔> -Encoding utf8; $o = git -C <repo> status --porcelain -uall; $rc = $LASTEXITCODE; "rc=$rc"; $o | Where-Object { $snap -notcontains $_ }
```

| G | 目錄 | 指令 | 期望 |
|---|---|---|---|
| G-K1 | `<repo>\AgentConsole\backend` | `.\gradlew.bat clean build` | BUILD SUCCESSFUL（含 Checkstyle、ArchUnit〔`ArchitectureRulesTest` A1～A6 與 `SiReadOnlyArchTest` 對新類別全綠、不放寬〕、Flyway＋validate、JaCoCo ≥80%、全部新測試與 `OpenApiIT`；需 Docker） |
| G-K2 | 同上 | `.\gradlew.bat test --tests "*Backup*"` | rc 0、每個新類別 ≥1 測試 |
| G-K3 | 同上 | `.\gradlew.bat test --tests "*SchemaMigrationIT" --tests "*V5UpgradeMigrationIT" --tests "*SiConsoleWritesMigrationIT" --tests "*IssuePriorityMigrationIT"` | rc 0（階二；版本清單含 "15"） |
| G-S1 | `<repo>` | `python tools\run_shellcheck.py` | rc 0、`_BASELINE` 不新增鍵（本機需 shellcheck 或 Docker 映像）；三支新腳本另在 Linux 容器 `bash -n` rc 0、LF |
| G-S2 | `<repo>` | `git diff --exit-code <base> -- AgentConsole/docker/pgbackrest/scripts/backup-full.sh AgentConsole/docker/pgbackrest/scripts/backup-incr.sh AgentConsole/docker/pgbackrest/scripts/pg_dump-offsite.sh AgentConsole/docker/pgbackrest/scripts/verify-backup.sh AgentConsole/docker/pgbackrest/scripts/restore.sh AgentConsole/docker/pgbackrest/scripts/setup-replica.sh AgentConsole/docker/pgbackrest/scripts/pgbackrest-as-postgres.sh AgentConsole/docker/pgbackrest/pgbackrest.conf` | rc 0、無差異 |
| G-S3 | `<repo>` | `python tools\lib\secret_scan.py --paths AgentConsole\docker\pgbackrest\tests\fixtures\mask-probes.txt` | rc 0 |
| G-S4 | `<repo>\AgentConsole\engine-bridge`（先啟根 venv） | `python -m pytest -q tests/test_deploy_config.py tests/test_si_deploy_config.py tests/test_backup_ctl_deploy_config.py`；同目錄 `ruff check .`（規則集 `pyproject.toml:38-44`）與 `<repo>` 視角 `ruff check AgentConsole\engine-bridge`；`<repo>\tools\tests` 內 `python -m unittest test_platform_neutral_paths.TestTextIoDeclaresEncoding -v`（新 Python 的文字 I/O 須帶 `encoding="utf-8"`，`:2136` 棘輪不得上升） | 各條 rc 0、pytest ≥1 測試 |
| G-S5 | `<repo>\AgentConsole\backend` | `.\gradlew.bat test --tests "*BackupSidecarContractIT"` | rc 0、≥1 測試（需 Docker） |
| G-S6 | `<repo>` | `docker run --rm -v "${PWD}\AgentConsole\docker\prometheus:/etc/prometheus" --entrypoint promtool prom/prometheus:v3.15.0 test rules /etc/prometheus/tests/backup_alerts_test.yml`；再跑 `… check rules /etc/prometheus/slo.yml /etc/prometheus/alerts.yml` 與 `… check config /etc/prometheus/prometheus.yml` | 三條皆 SUCCESS、rc 0；`alerts.yml: SUCCESS: 14 rules found`；**本機限定**（CI 無 promtool 步驟，已知缺口） |
| G-S7 | `<repo>\AgentConsole` | `docker compose --profile db --profile app --profile full config --volumes`（唯讀；需 `.env`） | rc 0；卷清單階一 13 個、階二 14 個 |
| G-F1 | `<repo>\AgentConsole\frontend` | `npm run lint` | rc 0 |
| G-F2 | 同上 | `npx tsc --noEmit` | rc 0 |
| G-F3 | 同上 | `npm run test:cov` | rc 0；覆蓋率文字表含 `lib/domain` 目錄段下的 `sysadminBackup.ts` 列；門檻 lines 70、statements 70、functions 70、branches 60 |
| G-F4 | 同上 | `npm run build` | rc 0 |
| G-F5 | 同上 | `npx playwright test tests/e2e/sysadmin-backup.mock.spec.ts tests/e2e/shells-and-layout.spec.ts --output=test-results-mock` | rc 0（導覽斷言複核） |
| G-F6 | 同上（backend 在線） | `npm run gen:api` | `schema.d.ts` 差異只含 backup 相關（階一、階二各一次） |
| G-C1 | `<repo>` | `git status --porcelain -uall`（已 commit 後改 `git diff --name-only <base>..HEAD`） | 以開工前快照相減；每個路徑 ⊆ §5.7；既有髒檔（`AutoClaude/.perf_baseline.toml`）不計 |
| G-C2 | `<repo>` | `git diff --exit-code <base> -- docs/01_requirements/Console_SysAdmin_Backup_PRD.md` | rc 0（PRD 凍結檔，只准追加〈勘誤〉節） |
| G-C3 | `<repo>` | `git diff --exit-code <base> -- AgentConsole/frontend/lib/api/reasons.ts AgentConsole/docs/02_architecture/API_Contract_P3-6.md AgentConsole/frontend/components/layout/ToolsRegion.tsx AgentConsole/backend/src/test/java/com/aisdlc/console/architecture/ArchitectureRulesTest.java AgentConsole/backend/src/test/java/com/aisdlc/console/architecture/SiReadOnlyArchTest.java` | rc 0 |
| G-C4 | `<repo>` | `git diff --name-only <base>..HEAD` 篩 `^(tools\|\.claude\|\.github\|AutoClaude\|AISDLC_SDD)/` 與 `^AgentConsole/engine-bridge/app/` | 無輸出（零侵入面；AT-BK-09-4-E-2） |
| G-C5 | `<repo>` | `git diff -U0 <base> --` 既有測試檔（§5.7 各「同步鎖」列所列檔） | 人工核對：每 hunk 只動釘值或預期清單；被刪 assert、expect、assertThat 行＝0（AT-BK-01-1-3） |
| G-V | 掌舵者或主控（Windows＋Docker Desktop 全棧） | 先 `Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build; Pop-Location`，sidecar 已跑過至少一次備份；依 §3.2 各真機 AT 的步驟 | 見各真機 AT；階段一 V1、V2、V3、V6、V10；階段二 V4、V5、V7、V8、V9 |

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（凍結前留空；凍結後依〈凍結後修訂路由〉由 `agentconsole-sysadmin-backup` `spec-refreeze`，並於此逐條附新 digest；原文座標以 Stage-2 凍結版的行號為準，本節只追加、不改正文。）
