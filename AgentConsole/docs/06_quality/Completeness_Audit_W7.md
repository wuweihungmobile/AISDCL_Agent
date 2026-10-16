# W7-ARCH：PRD 完備性獨立審查

| 項目 | 內容 |
|------|------|
| 審查者 | W7-ARCH（獨立 Architect 審查鏡；唯讀、量不挖；沒有改任何程式、契約或 RTM，也沒有起任何服務或容器） |
| 審查日期 | 2026-10-16 |
| 基準 | HEAD `ac9272da`；本檔所有「檔案:行號」以該版為準（契約、Architecture、ADR、`docker-compose.yml`、`docker/README.md` 在本輪被他棒修改，工作樹行號會位移，已逐一對 `git show HEAD:` 的內容核對） |
| 回答的問題 | ① PRD 全部功能是否已規劃、實作並逐項 E2E 驗證；② UI 是否依設計稿；③ AutoClaude、AISDLC_SDD、AgentConsole 三模組是否緊密結合 |
| 權威順序 | PRD（§0 權威）＞設計稿 README（視覺唯一真相源，ADR-001 D11）＞契約、Architecture、ADR |
| 數字守則 | 本檔數字全部來自本輪工具輸出；只能由程式推得、未實跑者一律標「待驗」 |

## 0. 一頁摘要

**結論先行**：三個問題的答案都是「有條件」。功能面幾乎沒有「PRD 要、RTM 沒列、程式沒做」的硬缺口；缺口集中在三處：

1. **證據口徑**：RTM 的「已驗證」在三個地方比字面弱——63 列 INF 只有開發者自述（沒有 QA 標記，也沒有指向 log 或輸出檔的路徑）；`NFR-OBS-01` 驗的不是 PRD 寫的四源；前端覆蓋率「70%」只量四分之一的原始檔。
2. **PRD wireframe 與設計稿之間被默默拿掉、沒有登記的小元素**：DAG 卡「全螢幕」、專案詳情「匯出」、任務詳情第三張指標卡「執行時長」、公告列五個靜態字樣。
3. **AISDLC_SDD 只接上一個點**（凍結規格編譯）：Bridge 的 `/sdd/version`、`/sdd/fsm/{project}` 在 Console 後端與前端沒有任何消費者，PRD 把 FSM 狀態列為 Console 對 SDD 的遙測來源。

另有一個前後端口徑問題：儀表板的「待審批草案數」與頂列徽章（含任務與匯入草案）和「待人工審批」清單（只有專案與目標）不是同一個集合，點得到的入口比數字少。

**發現總數：27 筆**——缺列 4、證據失效 12、設計稿差異 4、整合缺口 7；建議處置：本波可修 11、登缺陷 6、裁決保留 10。不重複計入的已知項：五列「部分」（`API-AUT-06`、`US-M-10`、`NFR-9.1-05`、`NFR-9.3-01`、`INF-VOL-07`）都已有掌舵者裁決 D-11～D-15 與 W7 負責棒次。

RTM 現查（Grep count）：全表列數 364（`^\| (US|API|BR|NFR|INF|UI)-`）；狀態欄為「已驗證」者 359、為「部分」者 5（RTM.md:123、:215、:261、:270、:307）。

## 1. 怎麼查（方法與指令）

### 1.1 從 PRD 重新推導需求清單

不看 RTM，先通讀 PRD §0、§2～§5、§7～§12 與附錄 B，抽出可驗收的原子條目：58 條使用者故事、17 條頁面路由（§4.2）、§5.1.4 的八項、§5.3.2 的六列自治等級、§5.3.3 狀態機、§5.4.2 的八張 KPI 與五張圖、§5.4.4 的六條告警、§5.5 的 41 個參數鍵（加 §0.6 補的 9 個＝50）、§6.2 的十張表與索引、§7.1 的 55 個端點、§7.2 的三種封包、§8 全域佈局與設計系統、§9 的 22 條 NFR、§0.5 的 6 條 NFR、§11 的服務／網路／卷／映像／nginx／環境變數、§12 的備援與維運清單；再逐條對 RTM。

### 1.2 RTM 全量機械掃描（不只抽樣）

做法：用根層 `.venv` 的 Python（`-X utf8 -I`）把 RTM 表格按九欄切開，逐列核對。腳本是本 session 的暫存檔、不入庫；邏輯如下，QA 可照做：

- 以 `^\| (US|API|BR|NFR|INF|UI)-` 取列，按 ` | ` 切成九欄；結果：364 列、無重複 ID、前綴計數 US 58／API 93／BR 26／NFR 32／INF 103／UI 52，與 RTM 檔頭一致。
- 「實作檔」欄：以 `、` 切開（括號內不切），去掉尾端說明，凡含 `/` 或副檔名者轉成相對 `AgentConsole/` 的路徑 Glob。結果：1,235 個路徑；1,173 個直接命中；62 個是 RTM 的寫法（同目錄的裸檔名、`＋` 連寫、`docker/README.md〈n〉` 章節記號），逐一人工確認都存在（含字型檔 `NotoSansTC-Regular.ttf`、`OFL.txt` 與 README 的 `〈2〉〈3〉〈4.3〉〈6〉〈8〉` 章節）。**缺檔 0 個。**
- 「自動測試」欄：Java 以 `void 方法名(`、Python 以 `def 方法名(`、TypeScript／Playwright 以標題字串核對。結果：Java 九百四十六項中九百四十五項命中；Python 八十一項全命中；TypeScript 與 Playwright 二百九十四項全命中。**失配一項（V-01）。**
- 「E2E 驗證」欄：`QA_*.md §n` 引用全數指到存在的章節（兩份報告標題索引共一百零五個章節編號）；`*.spec.ts`、`*.stack.ts` 檔名引用全數存在（唯一例外是 US-M-08 的 `*.mock.spec.ts` 通配寫法）。
- 另外掃：狀態為「已驗證」的列中，實作或測試欄為「待填」者、欄位內殘留「待 W3」「未做」等待辦字樣者（V-02、V-03）。

### 1.3 抽樣 44 列的 Glob／Grep 實查（涵蓋每個分類）

| 分類 | 列 | 實查方式與結果 |
|------|----|----------------|
| US（8） | US-P-05、US-G-06、US-T-05、US-I-08、US-E-10、US-M-08、US-S-06、US-E-11 | Glob 後端主程式與 dto 檔全在；Grep 方法名全在：`ProjectApiIT.java:267、:289`、`GoalApiIT.java:161、:176`、`TaskApiIT.java:144`、`ImportPathsApiIT.java:434`、`ExecuteProjectApiIT.java:348`、`ExecutionAlertsApiIT.java:60`、`SettingsExportImportApiIT.java:74`、`ExecutionLifecycleApiIT.java:535`；前端 `monitorLayout.test.ts:27`、`monitor.mock.spec.ts:363`、`crud-flow.spec.ts:166`、`task-retry.spec.ts:36` 全在 |
| API（10） | API-PRJ-06、API-IMP-09、API-EXE-12、API-MON-07、API-NTF-01、API-SET-04、API-ALR-04、API-AUTH-02、API-DAG-02、API-HLT-02 | Glob 控制器、服務、領域類別共三十四個檔全在；Grep：`ProjectRestoreApiIT.java:85`、`ImportFlowApiIT.java:80`、`ExecuteProjectApiIT.java:70`、`MonitorApiIT.java:591`、`NotificationSummaryApiIT.java:68`、`SettingsWriteApiIT.java:83、:98`、`AlertRulesTest.java:72`、`AuthApiIT.java:65`、`DagServiceTest.java:81`、`ActuatorIT.java:29` 全在 |
| BR（6） | BR-02、BR-11、BR-14、BR-17、BR-19、BR-26 | Glob Bridge 的 `routers/autoclaude.py`、`routers/sdd.py`、`runner.py`、`decompose.py`、`procutil.py`、`health.py`、`main.py`、`Dockerfile` 與九個測試檔全在；Grep：`test_api_validation.py:125`、`test_decompose.py:84`、`test_e2e_lifecycle.py:15`、`test_sdd.py:102`、`test_procutil.py:66`、`test_reconcile.py:42` 全在；`test_health_deep.py` 有十三支，與 RTM 寫的「十三支」一致 |
| NFR（5） | NFR-SEC-03、NFR-9.2-02、NFR-9.2-06、NFR-9.4-02、NFR-XPL-04 | Glob 全在（含 `gradlew`、`gradlew.bat`）；Grep：`PassCriteriaSanitizerTest.java:19`、`RbacIT.java:80`、`RateLimiterTest.java:47`；`build.gradle.kts:121–128` 的 JaCoCo 門檻為 0.80、`vitest.config.mts:62` 的前端門檻為 70 |
| INF（8） | INF-SVC-04、INF-NGX-01、INF-DB-14、INF-DR-10、INF-DR-28、INF-OPS-04、INF-DKR-04、INF-VOL-08 | Glob：`docker/nginx/conf.d/default.conf`、`pg_dump-offsite.sh`、`crontab`、`pgbackrest-metrics.sh`、`alerts.yml`、`docker/README.md`、`V3__review_requests.sql` 全在；`SchemaMigrationIT.java:49、:62`、`test_deploy_config.py` 在；compose 有 `engine_workspace` 卷（:728）；README 的 `〈8〉`＝「日常維運檢查清單」（docker/README.md:391） |
| UI（7） | UI-SCR-07、UI-LAY-05、UI-MD-07、UI-OVL-02、UI-KPI-06、UI-CHT-03、UI-DS-03 | Glob 路由與元件全在；Grep：`layout.test.tsx:42`、`markdown.test.tsx:191`、`ui.test.tsx:22`、`design-rules.test.ts:35`、`shells-and-layout.spec.ts:26`、`design-system.spec.ts:38` 全在 |

44 列全數通過；全量掃描額外揪出的失配只有 V-01 一筆。指令形態（三例；其餘同型，皆在本輪的工具輸出裡）：

```text
Glob  pattern: {ProjectApiIT,GoalApiIT,TaskApiIT,ImportPathsApiIT,ImportParserTest,ExecuteProjectApiIT,…,SchemaMigrationIT}.java
      path:    AgentConsole\backend\src\test\java
      結果:    二十三個測試類別全在
Grep  pattern: void (deleteIsSoftAndCascadesToGoalsAndTasks|executingProjectCannotBeDeleted)\(
      path:    …\adapter\in\web\ProjectApiIT.java
      結果:    :267、:289
Grep  pattern: def (test_lifecycle_three_steps_complete_and_stream_is_finite|test_a_duplicate_run_id_is_409|…)\(
      path:    AgentConsole\engine-bridge\tests
      結果:    六筆，test_api_validation.py:125、test_decompose.py:84、test_e2e_lifecycle.py:15 等
```

### 1.4 其他實查

- PRD §4.2 的 17 條頁面路由：Glob `frontend/app` 下 17 個 `page.tsx` 全在，且皆 import 對應的 domain 元件（見 §4）。
- PRD §6.2 的 DDL 與 `V1__init.sql`：逐段比對，十張表、十一個索引與 CHECK 約束字面相同（檔頭自述「逐字採用」，兩邊 Read 比對屬實）。
- compose 的資源限制：十一個 PRD 服務的 CPU／記憶體上限與 PRD §11.2 逐項相同。
- PRD §12.6.2 的九個告警閾值：`docker/prometheus/alerts.yml` 的規則逐一對上（含 `> 30`、`> 50`、`691200` 秒、`!= 0`）。
- 前端 `lib/api/endpoints.ts` 對 PRD §7.1 的 55 個端點：每個都有函式；兩條 SSE（`/logs`、`/metrics`）都有消費（`sse.ts:26–30`、`useRunStream.ts:146`）。
- 後端對 `resume`、`restore` 的 signoff 二次校驗：`ExecutionControlService.java:113、:144`。
- 測試被停用的掃描：沒有 `test.fixme`、`test.fail`、`@Disabled`；真後端 spec 有十一個檔以 `test.skip(!E2E_ROOT, …)` 做環境閘（需要完整本機環境才會跑）；Bridge 有四條 symlink 權限略過（`test_security.py:132`、`test_sdd.py:137`、`test_e2e_edge_cases.py:151`、`test_api_validation.py:75`）與三處條件略過（沒有 git、沒有 DSN、不在 monorepo 內）。

## 2. 發現清單

分類：缺列＝PRD 有而 RTM 沒有列；證據失效＝RTM 欄位與實況不符、或「已驗證」的證據比字面弱；設計稿差異＝設計稿或 PRD wireframe 與實作不同且未登記；整合缺口＝三模組或前後端之間該接而沒接、或接了但口徑不一。嚴重度沿用 QA 的 P 級（P3＝該排進下一輪、P4＝觀察）。

### 2.1 缺列（4）

| 編號 | 類別 | PRD 位置 | RTM 列或檔案 | 證據（檔案:行號） | 建議處置 |
|------|------|----------|--------------|-------------------|----------|
| L-01 | 缺列 | §11.2 服務清單（PRD:2163–2177）、§11.3 卷（PRD:2537–2553） | INF-SVC 十五列、INF-VOL 八列；`minio-certs` 只在 INF-SVC-12 的實作欄附帶一句（RTM.md:294） | `docker-compose.yml:371`（服務 minio-certs）、`:720`（卷 pg_socket）、`:730`（卷 minio_data）、`:732`（卷 minio_certs）；`Architecture.md:117、:183` 已承認這四項；compose 共十六個服務、十一個卷 | 本波可修（P4）：W7-QA 合併 RTM 時補 INF-SVC-16、INF-VOL-09～11 |
| L-02 | 缺列 | §5.5.1.1～§5.5.1.6 參數表（PRD:1186–1263），尤其 `:1239–1240` 的 Email 通知 | 無逐鍵列；US-S-01～08 全為「已驗證」（RTM.md:124–131）；INF-DB-13／17 只管種子 | `ConfigCatalog.java:70–127` 與契約附錄 C（契約:2512–2596）一致：50 鍵＝引擎生效 15、Console 內部 15、只儲存 15、未驗 5；只儲存者含 `monitor.enableEmailNotification`／`notificationEmail`（後端沒有任何郵件發送程式）、`agent.maxConcurrentTasks`、`execution.maxParallelGoals`、`execution.enableRollback`（Architecture.md:1028、:1036）；UI 以 effect 標籤誠實呈現（契約:1764） | 裁決保留（P4）：功能面已誠實登記；建議 RTM 新增一列把「二十把只儲存／未驗」放進可追溯面；D-11 完成後未驗者由五把降為三把 |
| L-03 | 缺列 | §3.1 後端列「Java 21，Virtual Threads」（PRD:216）；ADR-001 D1（ADR-001:50） | 無對應列 | 只有 `StreamConnection.java:64`、`RunConsumers.java:90` 兩處明確 `Thread.ofVirtual()`；`backend/src/main/resources` 搜尋 `virtual`、`threads:` 無命中，即沒有 `spring.threads.virtual.enabled`（Spring Boot 4.1 的預設值待驗） | 裁決保留（P4）：ADR-001 D1 補一句「虛擬執行緒只用於 SSE 寫出與 run 消費者」，或登缺陷改為全域啟用 |
| L-04 | 缺列 | §3.1 架構模式、§4.1 後端目錄樹（PRD:263–312：`adapter/in/sse`、`adapter/out/messaging`、`domain/event`） | 無列；RTM 全文沒有 ArchitectureRulesTest 或 ArchUnit 字樣 | `ArchitectureRulesTest.java:22–69` 有八條 `@ArchTest` 守四層分離，但沒有任何 RTM 列引用；實際套件只有 `adapter/in/web`（SSE 在 `StreamController`）、`adapter/out/{bridge,document,http,llm,persistence}`，沒有 messaging 與 event 目錄；Architecture.md 對這三個目錄無任何說明 | 裁決保留（P4）：RTM 補一列 Clean Architecture 分層鎖；Architecture.md 補「與 PRD §4.1 目錄樹的差異」一段 |

### 2.2 證據失效（12）

| 編號 | 類別 | PRD 位置 | RTM 列或檔案 | 證據（檔案:行號） | 建議處置 |
|------|------|----------|--------------|-------------------|----------|
| V-01 | 證據失效 | §5.2.3 US-I-06 | US-I-06（RTM.md:98）自動測試欄 | 引用 `ImportRecordMapperTest::theListProjectionCarriesNeitherTheSourceNorTheParseResult`，實際方法已更名為 `…NorTheWarningsAndOptions`（`ImportRecordMapperTest.java:107`）；舊名還留在 `rtm_backfill_W3B1.md:30`、`rtm_backfill_W5BE.md:27`。另：UI-SCR-07（RTM.md:392）寫「十五個情境」，`execute.mock.spec.ts` 現有十六個 `test(`（Grep 計數） | 本波可修（P4）：W7-QA 合併時改名並更新數量 |
| V-02 | 證據失效 | §9、§0.5、§0.6；ADR-001 D15（跨平台補充） | 實作欄「待填」十三列（十二列是已驗證，另一列是 NFR-9.3-01 的部分）：NFR-REL-03、NFR-COMPAT-01、NFR-9.1-01～04、06、NFR-9.3-01、NFR-9.3-02、NFR-XPL-01～03、INF-DB-17；測試欄「待填」十四列（十三列是已驗證）：同上再加 NFR-9.3-03（RTM.md:255–260、:262、:270–272、:279–281、:341） | RTM §1.5 第 1 點要求回填四格；INF-DB-17 明明有檔：`V5__seed_engine_configs.sql`，測試可引 `SchemaMigrationIT.java:62`；其餘多為量測型 NFR，可改寫成量測腳本名或明寫「量測型，無實作檔」 | 本波可修（P4）：W7-QA 合併時一併補 |
| V-03 | 證據失效 | 多條 | 八列「已驗證」的實作欄殘留過期待辦：US-P-04（RTM.md:77「後端沒有把專案轉成 EXECUTING 的入口」）、NFR-9.2-01（:263「前端…待 W3」）、NFR-9.3-04（:273「restore 機制未做」）、NFR-9.4-01（:274「前端 ESLint／Prettier 待 W3」）、NFR-9.4-02（:275「前端 70% 待 W3／W4」）、NFR-9.4-04（:277「Bridge 端待 W1-B 回填」）、NFR-XPL-04（:282「待主控…D-2 裁決」）、UI-A11Y-01（:403「尚未跑全站 axe 稽核」） | 這些事後都做完了：Phase 4 可產生 EXECUTING 專案；`ADR-001 D19` 與契約 §1.6 有 restore；Prettier 在 `package.json`；Implementation_Plan.md:459 已裁 D-2；E2E 欄記載 axe 掃描已跑。讀者只看實作欄會以為還有未做的事 | 本波可修（P4）：W7-QA 合併時清掉 |
| V-04 | 證據失效 | §5.1.1 US-P-04「EXECUTING 狀態下限制可編輯範圍」 | US-P-04（RTM.md:77）E2E 欄 | 鎖定表單的 UI（`EntityForms.tsx:154、:178` 的橫幅「專案執行中：只能修改名稱與說明」、`EntityEditor.tsx:90`）沒有任何元件測試或 E2E：Grep 該橫幅字串只命中程式本身；`schemas.test.ts:74` 只驗請求轉換；QA 的 E2E 欄是 API 層 PUT 回 409（QA_P3-6 §15.4）。RTM 自己的註記說「無法用真資料驗證 UI 行為」，現在 Phase 4 已能產生 EXECUTING 專案，理由已過期 | 本波可修（P4）：W7-QA 補一支真後端 spec（長批次執行中開編輯頁，斷言橫幅與欄位停用） |
| V-05 | 證據失效 | §11、§12 全部 INF 列 | 六十三列 INF「已驗證」的 E2E 欄沒有 QA 標記或報告章節：INF-SVC-07～15、INF-NET-01～03、INF-VOL-01～05／08、INF-DKR-01～03／05、INF-CMD-01～02、INF-DEV-01、INF-DR-01～07／09／10／12／15／17／19～35、INF-OPS-01～09 | 這些列的證據是帶日期的口述（例：INF-DR-21 的「min(pg_up) 為 1」，RTM.md:362），沒有指向 log 或輸出檔的路徑，也沒有 QA 章節；QA_P3-6_E2E_Verification.md:710 自承「其餘 INF 列沿用 W2-B 的實跑證據、QA 未逐列重跑」；兩份 QA 報告對 INF-DR 只提到 12、13、16、18，INF-DR-20～35 與 INF-OPS-01～09 完全沒有 QA 紀錄（Grep 全部 `INF-DR-`、`INF-OPS` 命中）；RTM §1.4（RTM.md:58）允許 INF 列由 W2-B 直接設定，所以不違規，但「逐項 E2E 驗證」對這六十三列只有自述 | 本波可修（P3）：W7-QA 起全棧做 D-14／D-15 時順手跑一輪唯讀探查（Prometheus targets、rules、Grafana search、pg_stat_replication、pgbackrest info），逐列留證 |
| V-06 | 證據失效 | §0.5 NFR-OBS-01（PRD:111）「四源真相一致：FSM-STATE yaml／引擎執行邏輯／Console 渲染／PG 持久化」 | NFR-OBS-01（RTM.md:254）E2E 欄 | QA 比對的四源是 console-api `GET run`、Bridge `GET run`、PG `execution_runs`、SSE `/logs` 最後一框（QA_P3-6 §15.2）：沒有 FSM-STATE，「Console 渲染」也只比到 API 層，沒有比到頁面 DOM；Console 後端與前端全碼沒有任何讀 FSM 的路徑（Grep `fsm`、`FSM-STATE`、`sdd/fsm` 在 `backend/src` 無命中，前端只出現在 e2e 夾具 `p3-import.spec.ts:35`、`p4b-execute-more.spec.ts:310`、`p8-docker-stack.stack.ts:47`） | 登缺陷（P3）：主控二擇一——把 NFR-OBS-01 改寫成實際驗的口徑；或接上 FSM 讀取（見 I-01）後補比對 |
| V-07 | 證據失效 | §9.4「測試覆蓋率 後端 ≥ 80%，前端 ≥ 70%」（PRD:1981） | NFR-9.4-02（RTM.md:275） | `vitest.config.mts:26–61` 的 `coverage.include` 只列三十六個檔（`app`、`components`、`lib`、`hooks` 下的非測試原始檔共一百四十三個，約四分之一）；`components/domain/**` 中沒被列入的五十四個頁面視圖與卡片檔、`app/**` 路由、`components/ui` 與 `components/charts` 的其餘檔，共一百零七個檔不計入，檔頭 `:4–9` 自承「整頁視圖由 E2E 驗證，不計入這個門檻」；分支門檻只有 60（`:62`）。QA 報告的前端覆蓋率數字就是這個子集的數字；ADR-001、ADR-002、契約與 Architecture 都沒有登記這項口徑（Grep `覆蓋率`、`coverage` 於 `docs/02_architecture` 無命中；只有 W4-F2 任務書 `W4F2_FRONTEND_EXECUTE_MONITOR.md:23` 提到「受測範圍」） | 裁決保留（P3）：在 ADR-001 §4 補登口徑；或本波以全量範圍量一次並回報（全量數字待驗，本審查未跑覆蓋率） |
| V-08 | 證據失效 | §8、設計稿九畫面（UI-SCR 列來源為設計稿 README） | UI-SCR-01～09（RTM.md:386–394） | E2E 欄是功能流程的 spec（crud-flow、p4、p5、p6…），UI-SCR-02／03／04／05 與另外二十九列共用同一句「Docker 全棧…重跑既有真後端 specs 16 支全數通過」（腳本統計共三十三列，如 US-P-01、UI-RSP-01～03、UI-OVL-01）；沒有任何一列記載與 `Design_ConsoleUI/screenshots/*.png` 的逐畫面比對；W3 任務書只要求「列出與設計稿截圖的差異（文字描述即可）」（W3_FRONTEND.md:48）。所以「已驗證」證明的是「流程跑得動」，不證明「版面依設計稿」 | 本波可修（P3）：W7-QA 做一次九畫面×設計稿截圖的對照（至少 DOM 結構斷言加人眼比對），結果寫進 UI-SCR 列的 E2E 欄 |
| V-09 | 證據失效 | §10.2 Phase 6「系統設定 + 完整整合測試」（PRD:2043） | 359 列「已驗證」的 E2E 欄 | `agentconsole-ci.yml:11–12` 自述 Playwright E2E 不在 CI，「Windows 輪手動／nightly 跑」；`.github` 全域 Grep `playwright` 只命中這兩行，沒有任何 AgentConsole 的 nightly 工作流程。E2E 證據是一次性的人工 QA，之後任何改動都沒有機械重跑 | 登缺陷（P3）：登「E2E 無持續重跑」，由主控決定是否補 nightly（`.github` 不在本專案可改範圍） |
| V-10 | 證據失效 | — | RTM.md:9 檔頭與 §3.2（RTM.md:471–479） | 檔頭寫 364 列（API 93、BR 26）；§3.2 的類別×Phase 表加總 361（API 91、BR 25），是建表快照，W5 新增的三列沒進去；§1.5 第 5 點說快照不手改，但讀者會拿它對帳 | 本波可修（P4）：§3.2 表頭加「W5 前快照」字樣，或改現查數字 |
| V-11 | 證據失效 | §5.5.1.5、§5.3.6、§5.3.4 | Architecture.md、契約、程式註解 | ① `Architecture.md:1041` 把 `autoclaude.dalBackend` 標為生效並寫對映，但同節 `:1015`、`ConfigCatalog.java:114`（STORED_ONLY）、契約:2578 都說不生效；② `Architecture.md:441、:494` 仍寫位移與探測環存 Redis，實作是位移存 DB（V7 的 `console_last_seq`）、環形緩衝在記憶體（`BridgeHealthMonitor.java:17`）；③ 契約:1715 仍寫 DAG「全螢幕」、契約:1788 寫「任務層級列入 W4 增強」，實作早已有任務層級選取（`ScopeTree.tsx:27`、`ExecuteView.tsx:107`、`rtm_backfill_W4F2.md:70`）；④ `AgentBridge.java:201` 註解稱 ReviewService 使用 `listCheckpoints`，實際 `ReviewService.java:240–241` 用 `CheckpointRepository` | 本波可修（P4）：①②③歸 W7-SA（Architecture §10／§11 本來就要改）；④歸 W7-BE（連同 I-07 的死碼） |
| V-12 | 證據失效 | §0.6、§5.5 設定物化為引擎參數 | API-SET-10（RTM.md:195）E2E 欄 | E2E 欄實證的只有三把鍵真的改變引擎行為（`autoclaude.claudeCommand`、`agent.maxRetries`、`execution.autoResume`）；契約附錄 C 與 `ConfigCatalog.java:70–127` 標為引擎生效的共十五把，其餘十二把（含 `execution.compactThresholdPct`、`haltThresholdPct`、`agent.taskTimeout`、`model.timeout`、`model.enableKernelBrain`、`autoclaude.claudeExtraArgs` 等）只有 Console 側產出內容的單元測試（`ConfigMaterializerTest.java:73、:88、:96、:110、:120、:132、:142`）與 Bridge 對覆寫值的驗證；`frontend/tests/e2e` 沒有任何一支去讀引擎設定檔或對這些鍵做行為斷言（Grep `token_guard`、`step_timeout`、`enable_kernel_brain` 只命中跨鍵校驗與前置設定） | 本波可修（P4）：W7-QA 為 D-11 做「磁碟上的引擎設定檔斷言」時，把同一支 spec 擴到其餘生效鍵（只讀設定檔、不需新增引擎行為） |

### 2.3 設計稿差異（4）

| 編號 | 類別 | PRD 位置 | RTM 列或檔案 | 證據（檔案:行號） | 建議處置 |
|------|------|----------|--------------|-------------------|----------|
| D-01 | 設計稿差異 | §5.3.6 執行頁 wireframe：DAG 卡 `[展開/收合] [全螢幕]`（PRD:997）；US-E-09 | US-E-09（RTM.md:111）已驗證；契約:1715 仍列「全螢幕」 | `DagCard.tsx:58` 只有「展開任務／收合任務」；`rtm_backfill_W4F2.md:78` 開發者自承「全螢幕未做」；RTM.md、ADR-001 §4、ADR-002 §4、契約 §4.6 都沒有登記；前端元件中的「全螢幕」只出現在 Markdown 編輯器的註解（`MarkdownEditorImpl.tsx:5`） | 本波可修（P3）：前端加一個全螢幕切換（小工），或裁決保留並補登 ADR-002 §4 |
| D-02 | 設計稿差異 | §5.1.1 專案詳情 wireframe：`[編輯專案] [執行專案] [查看監控] [匯出] [刪除]`（PRD:463） | UI-SCR-03（RTM.md:388）、ADR-002 §4 | `ProjectDetailView.tsx:100–111` 底部行動只有執行專案、查看監控、編輯專案、刪除專案；PRD 沒有為「匯出」定義任何 US 或端點，設計稿也沒畫；ADR-002 §4 第 4 項只登記了「多了刪除」 | 裁決保留（P4）：補登 ADR-002 §4（PRD 未定義匯出內容；若要做需先定義） |
| D-03 | 設計稿差異 | §5.1.3 任務詳情 wireframe：三張指標卡「開始時間／Token／執行時長」（PRD:600–603）、按鈕含 `[暫停] [取消]`（PRD:622） | UI-SCR-05（RTM.md:390）、ADR-002 §4 第 4 項 | 設計稿 README:111 的三張卡是「開始時間／Token 消耗／重試次數」，實作照設計稿（`TaskDetailView.tsx:107–109`），「執行時長」被拿掉且沒有登記；ADR-002 第 4 項（`ADR-002:126`）說暫停／取消「屬 Phase 4 執行控制」，Phase 4 完成後任務頁仍沒有、PRD §7.1.3 也沒有單任務暫停端點，理由已過期 | 裁決保留（P4）：補登「第三張卡取設計稿」，並把暫停／取消的理由改為「執行控制只有批次層級」 |
| D-04 | 設計稿差異 | 設計稿 README:57 公告列：說明文件／下載 CLI／GitHub／通知總覽／幫助中心／繁體中文 | 契約 §4.6 G-G2（契約:1797）只涵蓋「通知總覽」 | `TopRegion.tsx:53、:55、:57、:65、:70、:75`：六項都是不可點、無行為的 `<span>`；設計稿 README 只描述文字，沒說連到哪 | 裁決保留（P4）：契約 §4.6 補登五項為靜態標示；或讓它們連到實際文件 |

### 2.4 整合缺口（7）

| 編號 | 類別 | PRD 位置 | RTM 列或檔案 | 證據（檔案:行號） | 建議處置 |
|------|------|----------|--------------|-------------------|----------|
| I-01 | 整合缺口 | §0.2（PRD:63）Bridge 責任含 `GET /fsm/{project}`；§0.3 對映表（PRD:92–93）：Run＝FSM-STATE session、監控遙測＝FSM decision_trace／retry_history／RTM；NFR-OBS-01（PRD:111） | BR-13、BR-14（RTM.md:237–238）已驗證，但只驗到 Bridge 直連 | Bridge 有 `GET /sdd/version`（`sdd.py:30`）與 `GET /sdd/fsm/{project}`（`sdd.py:36`），Console 後端 `BridgeHttpAdapter.java` 與前端都沒有消費者（Grep `sdd/version`、`sdd/fsm`、`FSM-STATE`、`fsmState` 於 `backend/src` 與 `frontend` 非測試碼無命中）；真實檔 `AISDLC_SDD_v0.30/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml` 存在，Bridge 讀得到卻沒人讀 | 登缺陷（P3）：主控裁決——接上（最小範圍：監控頁 Agent 卡顯示 SDD 版本與專案 FSM 當前狀態）或把 BR-13／14 與 PRD 對映改寫成「Bridge 層能力、Console 不消費」 |
| I-02 | 整合缺口 | §0.2（PRD:63）SSE「推 log＋ExecutionObservation＋FSM 狀態」、`POST /decompose`「呼叫 GoalDecomposer／SDD skill」；§0.4／US-I-09（PRD:101、:718）signoff「對應 SDD HUMAN_PENDING」 | BR-07（SSE）、BR-11、US-I-09 全為已驗證 | Bridge 事件型別只有六種（`events.py:26`：log、status、step、token、review-request、alert），沒有 FSM 或 observation；`/sdd/fsm` 只回六個欄位加尾五筆 decision_trace（`sdd.py:53–62`），沒有 RTM coverage、`retry_history`、`human_pending_tracking`（真實 FSM 檔 `FSM-STATE-AISDLC_SDD.yaml:8、:47` 都有這兩個鍵）；decompose 只用 GoalDecomposer（`decompose.py:23`），沒有 SDD skill；Console 的 signoff 只寫 Console 自己的表與 GoalDecomposer 的 `:approve`（`ImportService.java:386`），不與 SDD 的 HUMAN_PENDING 同步 | 登缺陷（P3）：與 I-01 一併裁決；PRD 這幾句要嘛實作、要嘛 ADR 登記為偏離 |
| I-03 | 整合缺口 | §5.4.2「Agent 可用率」、US-M-10 | US-M-10（RTM.md:123）、UI-KPI-08 | Console 的探測環打淺層 `/health`（`BridgeEndpoints.java:15、:35–39`；`BridgeHttpAdapter.java:146–157` 只看 HTTP 2xx），而 Bridge 的 `/health` 不論引擎是否可用都回 `status:"ok"`（`main.py:117–138`，`engines.autoclaude.ok`、`engines.sdd.ok` 可為 false）；只有 `/health/deep` 會回 503，但它只給容器 healthcheck 用（`docker-compose.yml:218`、`Dockerfile:55`；`Architecture.md:847` 寫明探測環仍打 `/health`），而且它只檢查 git、autoclaude、workspace、db 四項（`health.py:87–90`），沒有 SDD。所以 AutoClaude 匯入失敗時，頂列仍顯示「已連線」、Agent 可用率不降；`SDD_ROOT` 找不到時兩條探針都看不出來，只會在匯入路徑 A 才以 503 `sdd_unavailable` 現形（`sdd.py:22–27`） | 登缺陷（P3）：探測環改打 `/health/deep`（設定鍵 `autoclaude.healthCheckPath` 的驗證規則已允許該路徑，改預設值即可）並在 deep 加一項 SDD 檢查；或把 `/health` 的 `status` 隨引擎狀態降級 |
| I-04 | 整合缺口 | 根層規則：SDD LATEST 以 `AISDLC_SDD/scripts/sdd_version.py` 為唯一來源 | BR-13（RTM.md:237） | Bridge 自己實作「數字最大的 `AISDLC_SDD_v*` 目錄」（`settings.py:71–81`），沒有引用 SSOT（`tools/lib/sdd_latest.py:59–89`，內部以 `git ls-files` 判定）；Bridge 測試比對的也是自己寫的 `_numeric_latest`（`test_sdd.py:57、:88`），FSM 測試用合成夾具（`test_sdd.py:65–71`）；`agentconsole-ci.yml:19–24` 的路徑過濾不含 `AISDLC_SDD/**`，SDD 側改格式不會觸發 Console 的 CI。兩者在「有未入庫的版本目錄」時是否分歧：待驗 | 裁決保留（P4）：至少在 `settings.py` 註明與 SSOT 的差異理由；CI 路徑過濾評估是否加 `AISDLC_SDD/scripts/**` 與 FSM 範本 |
| I-05 | 整合缺口 | §5.3.4 US-E-07「通知＋Badge」、§8.1 頂列徽章；設計稿 README:84 的「待人工審批」卡 | US-E-07、UI-SCR-01（RTM.md:386） | 後端 `pendingSignoffs` 是四種草案的總數：專案、目標、任務、PARSED／REVIEWING 的匯入記錄（`NotificationCountsAdapter.java:14–27`），頂列徽章與儀表板 KPI 用它（`DashboardView.tsx:115`、`TopRegion.tsx:150`）；但「待人工審批」卡的清單與卡上徽章來自另一條路：只列「未簽專案」與其底下未簽目標，沒有任務、沒有匯入記錄、也沒有「已簽專案底下的草案」（`queries.ts:240–279`；`DashboardView.tsx:63` 自承「清單仍由專案／目標 API 組」、`:182` 徽章用 `queue.count`）。通知鈴的「待審核」「未確認告警」是全域數字，連結卻只導向「目前專案」的執行／監控頁（`NotificationBell.tsx:25–31`），目標專案不是目前專案時點進去是空的。契約 G-06（契約:1776）只更正了 KPI，清單與落點沒有登記 | 登缺陷（P3）：後端補一個列出待簽清單與待審核清單（含 projectId）的端點，前端清單與鈴的連結改用它；或至少在契約 §4.6 登記為已知限制 |
| I-06 | 整合缺口 | §11.2 服務 `redis`「快取／Session 儲存」（PRD:2173）；ADR-001 D16 | INF-SVC-07（RTM.md:289）已驗證，但只驗容器健康 | 後端沒有任何 Redis 依賴或程式（`build.gradle.kts` 無 redis；`backend/src/main` 只有兩處註解提到 Redis，一說選配、一說本輪不做：`RateLimitFilter.java:44`、`BridgeHealthMonitor.java:17`），但 compose 仍把 `SPRING_DATA_REDIS_HOST／PORT` 傳給 backend（`docker-compose.yml:131–132`）並要求 redis healthy 才啟動 backend（`:166`）；ADR-001 D16（:194）列的三個用途（refresh token 輪替與撤銷名單、限流計數、SSE 位移）全部沒做，也就沒有 D16 承諾的「Redis 不在線仍可用」降級測試；登出只清瀏覽器 session，後端沒有撤銷名單（`AuthUseCase.java:18` 只說換新一組 token）；`Architecture.md:441、:494` 仍寫存 Redis（V-11） | 裁決保留（P3）：功能面——ADR-001 D16 改寫為「Redis 目前未使用」，並移除 compose 的死設定與啟動相依；refresh token 撤銷若列為需求再另案 |
| I-07 | 整合缺口 | §0.2.1 checkpoint 列舉 | BR-09（RTM.md:233）、API-EXE-08 | Bridge 的 `GET …/checkpoints` 與 `AgentBridge.listCheckpoints` 在 `backend/src/main/java` 沒有呼叫者（Grep 只命中宣告 `AgentBridge.java:202` 與實作 `BridgeHttpAdapter.java:231`，只有 adapter 單元測試呼叫）；Console 的斷點列表與審核 RETRY 還原改走資料庫（`ExecutionQueryService.java:303–309`、`ReviewService.java:240–241`），而資料庫的 `checkpoints`、`execution_steps` 完全由 Bridge 寫入（`db.py:6`）。Bridge 若以純檔案模式啟動（無 `BRIDGE_DB_DSN`，AgentConsole/CLAUDE.md 所載模式），Console 的斷點清單與步驟時間軸會是空的；compose 與 e2e README 都有設 DSN，所以標準部署不受影響（純檔案模式的實際表現：待驗） | 裁決保留（P4）：README 與 CLAUDE.md 註明「Console 需要 Bridge 的 DB 模式」；`listCheckpoints` 死碼刪除或補用途（連同 V-11 ④） |

## 3. PRD 推導清單 ↔ RTM 對帳

| PRD 區段 | 推導出的條目 | RTM 對應 | 結果 |
|----------|--------------|----------|------|
| §5.1.1～§5.5.3 使用者故事 | 58（P6、G7、T6、I10、E11、M10、S8） | US-* 58 列；RTM §3.1 與 PRD 逐表一致 | 全對應 |
| §4.2 頁面路由 | 17 條（`/` 到 `/settings`，含巢狀） | 無逐路由列；US-P-04 的 E2E 欄引用 `shells-and-layout.spec.ts:56`「PRD §4.2 的 new／edit／goals／tasks 路由都存在且可深連結」 | 17／17 存在（Glob）；以故事列涵蓋，可接受 |
| §5.1.4 Markdown | 8 項 | UI-MD-01～08 | 全對應 |
| §5.2 解析、有界閘、雙路徑 | 格式判斷、規格凍結偵測、三層 JSON、狀態機 | API-IMP-07～10、BR-11、BR-12、BR-15 | 全對應 |
| §5.3.2／§5.3.3 | 6 個等級列、狀態機 3 張 | API-AUT-01～06、API-STM-01～03 | 全對應（AUT-06 為部分，D-11） |
| §5.4.2 KPI／圖 | 8 張卡、5 張圖 | UI-KPI-01～08、UI-CHT-01～05 | 全對應 |
| §5.4.4 告警 | 6 條 | API-ALR-01～06 | 全對應 |
| §5.5 設定鍵 | PRD 41＋§0.6 補 9＝50 | 無逐鍵列（L-02）；契約附錄 C、`ConfigCatalog`、`labels.ts` 都是 50 鍵 | 鍵集合一致 |
| §6.2 DDL | 10 張表、索引 | INF-DB-01～11、V1 逐字相同 | 全對應 |
| §7.1 端點 | 55（REST 53＋SSE 2） | API-PRJ／GOL／TSK／IMP／SGN／EXE／MON／SSE／SET 共 55 列；前端 `endpoints.ts` 每個都有函式 | 全對應 |
| §7.2 封包 | 3 種 | API-FMT-01～03 | 全對應 |
| §8 全域佈局、設計系統、響應式、可及性（設計稿 README 另補設計系統細則與覆蓋層） | §8.1 佈局與六個導覽項、§8.2 色彩／字型／動畫、§8.3 三個斷點、§8.4 四條可及性 | UI-LAY-01～05、UI-DS-01～07、UI-RSP-01～03、UI-A11Y-01～04、UI-OVL-01～03 | 全對應；§8.2 動畫表已由 ADR-001 D11（:139）降為參考 |
| §9 NFR | 22 | NFR-9.1-01～9.4-05 | 全對應（V-07 口徑） |
| §0.5 NFR | 6 | NFR-SEC-03～05、OBS-01、REL-03、COMPAT-01 | 全對應（V-06 口徑） |
| §11 服務、網路、卷、映像、nginx、環境、指令、資源 | 服務 11、網路 3、卷 8、映像 3、nginx 3 | INF-SVC／NET／VOL／DKR／NGX／ENV／CMD／RES | 全對應；實作多 1 服務 3 卷（L-01） |
| §12 備援、備份、監控、維運 | 各子節＋九個指標＋六個面板＋九項檢查 | INF-DR-01～35、INF-OPS-01～09 | 全對應；§12.2.7 自動 failover 依 PRD 自述為選配、預設不啟用，不要求列 |
| §0.2／§0.3 Bridge 責任 | 七個端點責任、互斥、孤兒回收 | BR-01～26 | 對應；FSM 面見 I-01、I-02 |

## 4. 設計稿畫面 ↔ 路由／元件

| 設計稿畫面 | 路由 | 主要元件 | 差異登記狀況 |
|------------|------|----------|--------------|
| 全域：公告列＋主導覽 | `app/layout.tsx` 組裝 | `layout/TopRegion.tsx` | ADR-002 §4 第 1、6、9 項；D-04 未登記 |
| 全域：側欄、我的專案 | 同上 | `layout/ToolsRegion.tsx`（導覽六項、rail 取前六個專案） | 與設計稿一致；PRD §8.3 響應式三形態（ADR-002 D3） |
| 1 總覽儀表板 | `/` | `views/DashboardView.tsx`、`charts/ProjectStatusChart.tsx` | ADR-002 §4 第 2 項；I-05 口徑問題 |
| 2 專案管理 | `/projects` | `views/ProjectsView.tsx`、`ProjectCard.tsx`、`ui/pagination.tsx` | ADR-002 §4 第 3 項（排序第三項） |
| 3 專案詳情 | `/projects/[projectId]` | `views/ProjectDetailView.tsx`、`GoalListCard.tsx`、`SignoffBanner.tsx` | D-02 未登記 |
| 4 目標詳情 | `…/goals/[goalId]` | `views/GoalDetailView.tsx`、`TaskListCard.tsx` | 與設計稿一致 |
| 5 任務詳情 | `…/tasks/[taskId]` | `views/TaskDetailView.tsx`、`LogPanel.tsx` | D-03 未登記 |
| 6 匯入 | `/import` | `import/ImportView.tsx`、`SourceCard`、`StructureCard`、`TreeEditor`、`HistoryPanel`、`NodeEditDialog`、`parts` | 契約 §4.1、§4.6 G-I1～G-I3 已登記 |
| 7 執行 | `/projects/[projectId]/execute` | `execute/ExecuteView.tsx`、`ControlCard`、`ScopeTree`、`ProgressCard`、`DagCard`、`LiveLogCard`、`ReviewCard`、`CheckpointDialog` | 契約 §4.2、§4.6 G-E1～G-E3 已登記；D-01 未登記 |
| 8 監控 | `/projects/[projectId]/monitor` | `monitor/MonitorView.tsx`、`KpiCards`、`ChartCards`、`TimelineCard`、`LogQueryCard`、`AlertsCard`、`CompareCard`、`AgentCard`、`ExportBar` | 契約 §4.3、§4.6 G-M1～G-M3 已登記 |
| 9 設定 | `/settings` | `settings/SettingsView.tsx`、`SettingRow`、`SettingControl`、`TokenGuardCard`、`ConnectionTest`、`HistoryCard`、`ImportSettingsDialog`、`ResetAllDialog` | 契約 §4.4 已登記（含儲存方式差異 S-09） |
| 全域覆蓋層 | 各頁 | `ui/dialog.tsx`、`domain/entity/EntityDialog.tsx`、`ConfirmDialog.tsx`、`SignoffDialog.tsx`、`ui/toast.tsx`、`ui/skeleton.tsx`、`ui/spinner.tsx` | 與設計稿一致 |

PRD §4.2 的其餘路由（目標列表、任務列表、新建、編輯）由 `EntityFormPage`／`ListPages` 承接，皆存在。

## 5. 三模組整合

### 5.1 Bridge 端點（十六個）↔ 消費者

Bridge 共十四條業務路由（`autoclaude.py` 十一條、`sdd.py` 三條）加兩條健康探針（`main.py:104、:108`）；瀏覽器不直連 Bridge（Architecture.md:838），所以「前端消費者」指經 Console API 的入口。

| # | Bridge 端點 | RTM | Console 後端呼叫點 | 前端入口（經 Console API） | 狀態 |
|---|-------------|-----|--------------------|-----------------------------|------|
| 1 | `POST /autoclaude/runs` | BR-02 | `BridgeHttpAdapter.java:171` ← `RunLauncher.java:109` | 啟動執行（`endpoints.ts:324`） | 有 |
| 2 | `POST …:pause` | BR-03 | `:179` ← `ExecutionControlService.java:104`、`RunConsumers.java:215`（審核閘點） | 暫停（`endpoints.ts:342`） | 有 |
| 3 | `POST …:resume` | BR-04 | `:186` ← `ExecutionControlService.java:114`、`ReviewService.java:176` | 恢復、審核通過（`:347`、`:382`） | 有 |
| 4 | `POST …:stop` | BR-05 | `:192` ← `ExecutionControlService.java:124`、`ReviewService.java:184` | 取消、審核拒絕（`:352`、`:382`） | 有 |
| 5 | `GET …/runs/{id}` | BR-06 | `:208` ← `ExecutionQueryService.java:108`、`MonitorTicker.java:148` | 執行頁與監控頁的 `bridge.*`（`:337`） | 有 |
| 6 | `GET …/events` | BR-08 | `:219` ← `StreamService.java:169`、`RunConsumers.java:182` | 間接（SSE 回補） | 有 |
| 7 | `GET …/checkpoints` | BR-09 | `:231`，無呼叫者 | 斷點對話框走資料庫的 `GET /executions/{id}/checkpoints`（`:369`） | **無生產消費者**（I-07） |
| 8 | `POST …/restore` | BR-10 | `:203` ← `ExecutionControlService.java:154` | 斷點對話框（`:374`） | 有 |
| 9 | `GET …/stream` | BR-07 | `:244` ← `RunConsumers.java:135` | 間接：Console SSE（`sse.ts:94`） | 有 |
| 10 | `POST /autoclaude/decompose` | BR-11 | `:114` ← `ImportParser.java:257` | 匯入路徑 C（`:218`） | 有 |
| 11 | `POST …/decompose/{id}:approve` | BR-12 | `:127` ← `ImportService.java:386` | 匯入 signoff（`:228`） | 有 |
| 12 | `GET /sdd/version` | BR-13 | 無 | 無 | **無消費者**（I-01） |
| 13 | `GET /sdd/fsm/{project}` | BR-14 | 無 | 無 | **無消費者**（I-01） |
| 14 | `POST /sdd/compile` | BR-15 | `:133` ← `ImportParser.java:139、:152` | 匯入路徑 A | 有 |
| 15 | `GET /health` | BR-01 | `:150` ← `BridgeHealthMonitor.java:39` | 頂列、底列連線燈（`notifications/summary`，`:243`） | 有（只看 HTTP 碼，I-03） |
| 16 | `GET /health/deep` | BR-26 | 無 | 無 | 僅容器探針（`docker-compose.yml:218`；設計如此，I-03 建議改用） |

十六個中十二個有生產消費者、四個沒有。

### 5.2 PRD 提到的引擎能力

| 引擎能力 | PRD | Bridge | Console | 判定 |
|----------|-----|--------|---------|------|
| 凍結規格編譯（SddToPlaybookAdapter） | §0.1、§0.4、§5.2.1 | `/sdd/compile` | 匯入路徑 A（`ImportParser.java:139`） | 已接；實際讀規格的是 AutoClaude 的 adapter（`sdd.py:72`），不是 AISDLC_SDD 的 runtime |
| 高階目標拆解與有界閘 | §0.4、§5.2.1 | `/decompose`（`decompose.py:23`） | 匯入路徑 C | 已接 |
| 人工 signoff（`GoalDecomposer.approve`） | §0.4、§7.1.4.1 | `:approve` | `ImportService.java:386` | 已接；與 SDD 的 HUMAN_PENDING 不同步（I-02） |
| 執行、config 物化、互斥、孤兒回收 | §0.2、§0.2.2 | runs 系列 | `RunLauncher`、`ConfigMaterializer`（十五把引擎生效鍵） | 已接 |
| pause／resume／stop／checkpoint／restore | §0.2.1、US-E-04～06、11 | 對應端點 | `ExecutionControlService` | 已接（列舉走資料庫，I-07） |
| 即時日誌與指標 | §7.1.7 | `/stream` | `RunConsumers`→`StreamService`→前端 `useRunStream` | 已接 |
| 自動突變與自演化（Level 6～10） | §5.3.2 | 引擎旋鈕存在 | `ConfigMaterializer.java:73` 只送 `enable_kernel_brain`（取自設定鍵，與等級無關） | 未接（D-11 承接） |
| 資源使用情況 | US-M-10 | 無 | 無 | PRD 有、Bridge 沒有（D-12 承接） |
| FSM 狀態、版本、RTM coverage | §0.2、§0.3、NFR-OBS-01 | 只有 FSM 與版本，沒有 RTM coverage | 無 | 只存在於 Bridge（I-01、I-02） |
| SSE 推 FSM 狀態與 ExecutionObservation | §0.2（PRD:63） | 無（`events.py:26`） | — | PRD 有、Bridge 沒有（I-02） |
| decompose 呼叫 SDD skill | §0.2 | 無 | — | PRD 有、Bridge 沒有（I-02） |

## 6. 查了但沒有發現的項目

| 項目 | 怎麼查 | 結果 |
|------|--------|------|
| RTM 列數、前綴計數、重複 ID | 全量解析（§1.2） | 364／58／93／26／32／103／52，無重複 |
| PRD 使用者故事與端點對帳 | 逐表對 RTM；Grep 計數 | 58／58、55／55 |
| 實作檔路徑存在 | 全量 Glob（§1.2）＋抽樣 44 列 | 缺檔 0 |
| `QA_*.md §n` 章節引用、`*.spec.ts` 檔名引用 | 兩份 QA 報告標題索引、`frontend/tests/e2e` 目錄 | 失效 0 |
| PRD §6.2 DDL ↔ `V1__init.sql` | 逐段 Read 比對 | 相同 |
| compose 資源限制 ↔ PRD §11.2 | Grep `cpus`、`memory` | 十一項相同 |
| PRD §11.6 的十九個環境變數 ↔ `.env.example` | Grep 變數名 | 十九個全在（`.env.example:15–71`） |
| §12.6.2 告警閾值 ↔ `alerts.yml` | Grep `alert`、`expr` | 九項全有 |
| 前端對 PRD §7.1 的 55 端點與兩條 SSE | Grep `/api/v1/` | 全有函式 |
| signoff 對 execute／resume／restore 的二次校驗 | Grep `requireSignedOff` | 三條路徑都有 |
| 設定鍵集合：PRD 41＋9 ↔ 契約附錄 C ↔ `ConfigCatalog` | Grep `specs.add(spec(` | 一致，皆 50 |
| 任務層級執行範圍（US-E-02「特定任務」） | Grep `taskIds` | 已實作（`scope.ts:7`），契約 §4.6 G-E1 文字過期（V-11） |
| 已登記的差異是否真的登記、且與程式不矛盾 | 逐項對 ADR-001 §4／D11、ADR-002 §4、契約 §4.6、Architecture §12 | 十八項都找得到登記，見 §7；其中回頭比對程式字面者：動畫表（`toast.tsx:90` 底部置中）、排序第三項（`ProjectsView.tsx:31`）、全域搜尋（`TopRegion.tsx:41–45`）、通知總覽靜態（`TopRegion.tsx:65`）、review 路徑參數（`endpoints.ts:382`）、backend 只連 primary（`backend/src/main/resources` 無 replica 字樣）、SDD 版本（BR-13）皆相符；其餘只核對到文件登記，未回頭驗程式 |
| 被停用的測試 | Grep `test.fixme`、`test.fail`、`@Disabled`、`pytest.skip` | 無 fixme、fail、Disabled；略過皆為環境條件 |

## 7. 已登記、不重複計的差異（抽查）

下列差異在文件中找得到登記，本審查不列為發現（驗證深度見 §6 倒數第二列）：Dark Mode 改淺色（ADR-001 §4:207、D11）；PRD §8.2 動畫表降為參考（ADR-001:139）；Tremor 改 Tremor Raw（§4:205、ADR-002 D6）；KPI 環形改數值卡（§4:214、G-20）；色票對比覆寫（§4:215）；US-I-05 瀏覽按鈕（§4:213、G-15）；PRD 八張 KPI 對設計稿四張（G-13）；儀表板 KPI 與公告列高度（ADR-002 §4 第 2、9 項）；排序第三項（ADR-002 §4 第 3 項）；頂列 Bridge 連線燈（契約 G-03；QA_P3-6 §13 記載實測符合）；全域搜尋只搜專案（契約:1796 G-G1）；通知總覽頁不做（契約:1797 G-G2）；執行批次下拉、事件時間軸、追蹤鏈（契約 §4.6 G-M1、G-M2、M-12）；「查看結果／查看日誌」只做任務連結（契約 E-18 F2-5）；修改後儲存方式（契約 S-09）；review 路徑參數語意（契約:223）；backend 只連 primary、不分流讀取（Architecture.md:1067 L-3）；SDD 版本 v0.14 對現況（ADR-001 §4:209）。

W7 已承接、不重複計：`API-AUT-06`（D-11）、`US-M-10` 的資源使用情況（D-12）、`NFR-9.1-05`（D-13）、`NFR-9.3-01`（D-14）、`INF-VOL-07`（D-15）。W7 完成後仍留下的：五把未驗鍵中的三把（`sdd.specFormat`、`workflowEngine`、`validationLevel`）與十五把只儲存鍵（L-02）。

## 8. 結論

1. **PRD 全部功能是否已規劃、實作並逐項 E2E 驗證——有條件**：規劃與實作已涵蓋（RTM 364 列對上 PRD 的 58 條故事、55 個端點、28 條 NFR 與 §11、§12 全部，實作檔路徑零缺漏，具名測試一千三百二十一項只有一項過期），359 列有 E2E 紀錄且其中 296 列有 QA 獨立證據；條件是 63 列 INF 的「已驗證」只有開發者自述、`NFR-OBS-01` 與前端覆蓋率兩列的證據口徑比 PRD 原文弱、PRD wireframe 另有 DAG 全螢幕與專案匯出兩個元素未做且未登記、二十把設定鍵只儲存或未驗、E2E 證據沒有任何持續重跑機制。
2. **UI 是否依設計稿——有條件**：九個畫面與四個全域區塊都有對應的路由與元件，色票、字級、間距與動效由 token 與靜態守衛釘住，已登記的差異與程式相符；條件是「依設計稿」的證據是功能流程而不是逐畫面比對，且有四項設計稿／PRD 差異（D-01～D-04）與一項待審批清單口徑不一致（I-05）未登記。
3. **三模組是否緊密結合——有條件**：AutoClaude 與 Console 緊密（Bridge 直接 import 引擎的 GoalDecomposer、AppConfig、檢查點儲存庫，十六個 Bridge 端點中十二個有生產消費者）；AISDLC_SDD 只在「凍結規格編譯」一點接上，FSM 狀態、版本、HUMAN_PENDING 與 RTM 覆蓋在 Console 側沒有任何消費者，三個 `sdd.*` 設定鍵也沒有作用，且 Console 使用的淺層健康探針看不到引擎層失敗。

## 9. 〈沒做〉與限制

- 沒有起任何服務、容器、瀏覽器，也沒有跑任何測試或覆蓋率；所有「存在」「命中」都是靜態檔案與程式推得。凡需要實跑才能確認者標「待驗」（L-03 的預設值、V-07 的全量覆蓋率、I-04 的 SSOT 分歧、I-07 的純檔案模式表現）。
- 沒有做像素級或截圖比對（V-08 正是這件事的缺口）；UI 對照只做結構與文字層級（路由、元件、按鈕、指標卡、色票與尺寸字面）。
- 沒有逐列重跑 E2E；對 E2E 欄的判斷只看證據是否可追溯（有無 spec 名、QA 章節、指令與輸出），不判斷輸出本身真假。
- 沒有檢查 `docker/README.md` 各節內容是否與 INF 列逐字相符，只核對章節記號存在。
- 沒有審查 W7 各棒的進行中工作（契約 v1.3、D-11～D-15 的實作）；其產出不在本審查範圍。
- 本審查的暫存腳本與中間輸出放在 session 暫存目錄、不入庫；邏輯已寫在 §1.2，可重現。
