# SCG-4 PR Review 報告 — 系統管理／資料庫備份 階一（PRD FR-BK-01～10 之階一；鍵 `agentconsole-sysadmin-backup`）

- 規格：TCS `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md`（Stage-2 digest `sha256:14e4e2ffe1bc11f7fd18c7775c008dcde78aada6a9f6f29892dc30c472ed5795`）；PRD `docs/01_requirements/Console_SysAdmin_Backup_PRD.md`（`sha256:848c2acfae30d3034205d647effd5000189c776f29db743629d4a4bdb1d0800a`，含〈勘誤一〉1-1～1-15）；契約 `AgentConsole/docs/02_architecture/API_Contract_SysAdminBackup.md`。審查者於工作樹與副本皆 `Get-FileHash` 相符。
- 受審 commit（本功能自己的六個）：S 包階一 `f150e35a`、契約檔 `6667b68f`、K 包 `08249781`（K 載具含階二者全做）、F 包階一 `297dab7d`、Architecture 連動 `5607835f`、`7088f355`；審查時 HEAD＝`7088f355`。實作期主控代決與實作棒揭露＝scratchpad `backup_impl_decisions.md` 第 1～20 點（本報告 §G 逐條裁定）。
- 審查者：Sonnet QA 鏡（未參與起草與實作）；全程唯讀、一切作業在 `git archive HEAD` 副本（frontend `node_modules` 實體複製；backend Gradle 與 Testcontainers 在副本內跑）；證據 scratchpad `qa_bk_notes.md` 與逐批輸出。本檔由主控依審查者純文字交卷落檔；數字一律審查者本場自跑。

### 審查歷程

| 審次 | 日期 | 結論 | 摘要 |
|------|------|------|------|
| 一審 | 2026-10-31 01:0x～02:3x | **FAIL** | P1 0、P2 4（F1～F4，皆「補斷言／勘誤、不動實作」可解；F1 另含一個待驗的 schedule 缺席 NPE 推論）、P3 5、P4 1；階一 AT 131 個中 125 個自動化證據全綠、0 紅、6 個真機未跑；階一 33 條 AC 每條 ≥1 綠 AT；突變 122 個 killed 111／survived 11；安全面（POST 僅 ADMIN 且置通用規則前、sidecar 對 `/backup-req` 唯讀、遮罩、機密、零侵入）查無缺口 |
| 二審 | 2026-10-31 12:08～12:58 | **PASS** | 新鏡 r2（一審鏡屬舊 session 不可達）對副本 `git archive d4aeab5b` 重放受審 `e205c0f5`＋`3784f88c`：十個倖存突變（U2、U2b、U11、J7、U3、U6、U7、U9、U12、U13）全數轉紅、F11 負控（三 tsx 退回）轉紅且逐檔精準、八處 DB 日誌遮罩逐處還原皆 killed、另 21 個額外突變 killed 19（倖存 U7b／U7c → R2-02）；新 AT 15 個全綠（backend 11、vitest 3、e2e 1；以 XML／JSON 測試名逐一比對，零跳過）；閘門 G-K1 `clean build` 2216／0 失敗／0 跳過、G-K2 148、G-K3 42、G-S5 36、G-F1～F5 rc 0（vitest 101 檔 1713）、G-C1～C5 合規；F1／F4 事實核對成立；P1 0、P2 0、P3 2（R2-01、R2-02）、P4 5（R2-03～R2-07）；P3 由修復棒同批補並由主控親驗（§H） |

### A. 一審站得住的部分（審查者數字）

- 階一 AT：前端 FN 5／5、FT 1／1、FH 3／3、FV 25／25、FL 4／4、FK 4／4、FS 3／3、FP 1／1（`npx vitest run lib/help` 3 檔 39 測）、E2 1／1（axe 無違規）；後端 BQ 30／30、BU 1／1、BV 4／4、BA 3／3、BS 24／24；靜態 PY 10／10、PT 1／1；審查閘 GT 5／5（01-1-3、09-3-E-2〔見 F2〕、09-4-2、09-4-E-2、10-5-3 等價重產）；真機未跑 ES×2、RM×4（主控另派真機棒）。階二（K 載具已全做，皆綠）：BQ 32、BU 1、BV 11、BA 4、BC 2、BD 2、BF 1、BM 3、FL 3、BS 09-6-5；實作棒補的四個 AT（04-5-S-1、07-3-S-1、06-3-S-1、09-2-S-1）全綠。階二未做（不算紅）：BS 15、FD 3、FV 11、ES 3、RM 1、GT 2；純階二 AC 中僅 AC-BK-09-1、09-2 暫無綠 AT（預期）；未見把階二誤宣稱為可用（唯 F5）。
- 突變 122：前端 35／35 killed；Java 48 killed 39／survived 9（U2、U2b→F1；U11→F3；U3、U6、U7、U9、U12、U13→F6）；sidecar shell 27 批 killed 26／survived 1（J7→F4）；靜態 PY／PT 11／11 killed；G-S1 SC2086 注入 1 survived（F2）。R 條文表階一條文 R-BK-01～26、28、43～45、48～54、58、59、61、62 皆重放至少一突變；階二僅抽樣。
- 安全與零侵入：POST `/api/v1/sysadmin/**` 僅 ADMIN 且置於通用規則前（突變 killed）；sidecar 對 `/backup-req` 為 `ro,nocopy`；`BackupMasker` 與 mask-probes 對 R-BK-42 在 API 道有鎖（AT-07-3-3 綠）；機密零入庫；不得變更清單零差異。

### B. 發現清單（一審；P2＝規格明文未被斷言／突變倖存／契約不一致；P3＝措辭、偵測力、數字；P4＝備註）

| # | 級別 | 座標 | 問題與證據 | 建議修法 |
|---|------|------|------------|----------|
| F1 | **P2** | TCS D-BK-T6／R-BK-25；`BackupQueryService.ExportReader.read()` | 「info／logical／schedule 缺席 ⇒ `export_unreadable`」沒有任何 AT：突變 U2（去 logical 缺席）、U2b（三檔缺席全去）在 BackupApiIT／BackupApiUnconfiguredIT／BackupServiceTest 共 91 測試全綠倖存；副本探針 IT（逐一刪 info／logical／schedule，期望 200＋export_unreadable）原碼綠、U2b 紅；**schedule 缺席依碼可能 `ZoneId.of(null)` NPE（推論，探針在 info 即停）**；sidecar 首次啟動窗口真會遇到缺席 | AT-BK-05-3-1 的 faults 表補三列缺席（⇒export_unreadable）、心跳缺席⇒runner_offline、jobs 缺席⇒no_run；修復棒先驗 schedule 缺席是否 NPE，是則修實作（消除成因）；勘誤 R-BK-25 補〈缺席〉並指向 D-BK-T6 |
| F2 | **P2** | TCS R-BK-62／AT-BK-09-3-E-2／G-S1 | `tools/run_shellcheck.py` 的 `_SEVERITY="warning"`：對 `job-run.sh` 注入未引號變數（info 級）經真 gate 實測 rc 0；只有 `-S style` 才紅；TCS「注入 SC2086 ⇒ G-S1 轉紅」不成立（現況三支新腳本 `-S style` rc 0） | G-S1 補一條 `docker run koalaman/shellcheck -S style` 專驗三支新腳本（不改根層工具，守零侵入）；勘誤 R-BK-62 突變欄 |
| F3 | **P2** | TCS R-BK-58／AT-BK-10-4-1 | 突變「把例外 `toString()` 回給用戶端」植入 `BackupQueryService.dbUnavailable()`（`GET /jobs`、`/jobs/{id}` 的 503 路徑）後 91 測試全綠倖存（U11）：洩漏掃描只涵蓋總覽降級路徑 | AT-BK-10-4-1 補：假 repo 丟含 `jdbc:…password=<假值>` 的 DataAccessException，對 `GET /jobs`、`GET /jobs/{id}`、POST 三個 503 路徑斷言回應本文與日誌不含該字串 |
| F4 | **P2** | TCS R-BK-42／R-BK-48（遮罩階一已上線） | `job-run.sh` 的 `mask_output`（perl）階一零 AT：突變 J7（`| mask_output` 改 `| cat`）使 BackupSidecarContractIT 26 測試全綠（cleanTest 重跑同）；對應 AT-BK-07-3-1 屬階二 BS 未做；API 端第二道 `BackupMasker` 有鎖（不外洩），但第一道無鎖 | mask-probes 對拍（容器內灌 probes 逐行比 `job-run.sh` 輸出，不需 runner）提前為階一 AT（如 09-3-S-2）；勘誤 R-BK-42 階欄拆「一（sidecar 道）／二（runner 道）」 |
| F5 | P3 | TCS C3.1 `canTrigger`、C3.5；決策 2／14 | S 包 compose 階一就設了 `CONSOLE_BACKUP_REQ_DIR`；K 的 `canTrigger`＝requestDir≠null∧reason=null∧DB 正常，階一部署即為 true，TCS 寫「階一恆 false」「REQ_DIR（階二）」；階一前端不讀它；POST 因 `/backup-req` 卷根屬 root 實機必 503 並補償該列 FAILED，無卡死 | 勘誤明寫 `canTrigger` 階一語意與 REQ_DIR 階一已設；決策 2 補「REQ_DIR 亦已設」 |
| F6 | P3 | 獵殺突變倖存（TCS 未列） | U3 incr 列 `baseLabel` 應 null 卻給 prior（AT-02-1-E-1 無帶 prior 的 incr 夾具）；U6 `cards[].requestedBy` 對非進行中 job 也給（決策 19 無反例）；U7 `Reconciler.start()` 不註冊輪詢排程（R-BK-36 無 AT）；U9 啟動不呼叫 `cleanStaleRequests()`（決策 8 啟動接線無 AT）；U12 `ATOMIC_MOVE` 換 `REPLACE_EXISTING` 全綠；U13 移除 0644（Windows 無 posix） | 各補一條斷言（U13 在 Linux 容器側斷言） |
| F7 | P3 | TCS §5.7／R-BK-61／G-C1／G-C4 | 六 commit 聯集 111 列有 3 路徑不在 §5.7：`frontend/lib/help/types.ts`（HelpId 兩鍵）、`components/domain/sysadmin/tone.ts`、`…/tests/withProviders.tsx`；G-C4 字面（`f150e35a^..HEAD`）3 命中皆非本功能 commit（`bb67692d` compat-ci paths、`39accaa3` 名冊 +1 行＝S 包 stubs 觸發的根層登記，必要且最小）；六 commit 自身 G-C4 命中 0 | 勘誤 §5.7 條件列與 R-BK-61 例外，註明 `39accaa3` 的 WHY |
| F8 | P3 | TCS §2「零測試視為失敗」 | Gradle per-AT 指令對不存在的 AT 仍 rc 0（`--tests "*AT_BK_99_9_9_*"` ⇒ 8 個 ArchitectureRulesTest 照跑）；vitest `-t` 無匹配 rc 0；只有 pytest `-k` 無匹配 rc 5 | §2 改為「以測試名清單比對 ≥1 個以 AT 編號起頭者」（本審查即以 XML／JSON 逐 AT 名比對） |
| F9 | P3 | TCS R-BK-59／FRD-lite（階一 75／86） | K 載具全做：階一 OpenAPI 已 77 路徑／89 操作，`schema.d.ts` 已含三個階二函式型別（`endpoints.ts` 仍 84）；等價重產（OpenApiIT 取 api-docs 經 gen-api.mjs）與入庫 `schema.d.ts` 位元組相同 | 勘誤階一數字 |
| F11 | **P2** | 真機（06:3x）：`BackupStatusCards.tsx:88`（`pre.bk-tail-*`，`max-h-48 overflow-auto`）、`BackupList.tsx:50`、`BackupHelp.tsx:69`（`div.overflow-x-auto`） | 備份頁本身 axe `scrollable-region-focusable`［serious］：ADMIN 1440 三節點（三分頁皆有）、ADMIN 390 另加表格容器、VIEWER 390 一節點；說明對話框 0 違規；repo 的 mock E2 只掃 VIEWER 1440 短資料故掃不到；Chromium 實測 Tab 可聚焦捲動容器（功能可用），但專案規則集判違規 | F 包小修：捲動容器加 `tabIndex={0}`＋`role="region"`＋`aria-label`；mock e2e 補 ADMIN 1440／390 長資料的 axe（二審重放） |
| F10 | P4 | 備註 | 決策 2「目錄不存在⇒not_configured」與碼不符（實為 export_unreadable）；`vitest.config.mts` reporter 加 `skipFull:false` 超出 §5.7 字面但為 G-F3 所需；ok／info 色階同為 primary-strong（靠文字與圖示分）；`BackupOverviewResponse` 為開放 schema，前端手寫型別與夾具和後端無自動漂移鎖；vitest 5 秒預設逾時在高負載下誤紅（重放需 `--testTimeout`） | 登記；決策 2 改寫入勘誤 |

### C. ⚖ 裁決（審查者對證據；主控採納）

- 修復棒範圍：F1（補 AT＋先驗 schedule 缺席 NPE、是則修實作）、F3、F4、F6 補斷言／新 AT；F2 走勘誤＋G-S1 補 `-S style` 指令（不改根層工具）；F5、F7、F8、F9、F10 由主控寫入 TCS〈勘誤〉；決策檔第 2 點改寫（目錄不存在⇒export_unreadable、REQ_DIR 階一已設）。
- 階二落地前不得宣稱真機 POST 可用（決策 14；F5 的 `canTrigger` 為 true 但 POST 會 503＋補償）。

### D. 一審閘門 rc（審查者於副本自跑；rc 皆先存變數再讀）

| 閘 | rc | 數字 |
|----|----|------|
| G-K1 `gradlew clean build` | 0 | 2205 測試、0 失敗、0 跳過（3m38s；含 Checkstyle／ArchUnit／JaCoCo） |
| G-K2 `--tests "*Backup*"` | 0 | 137 |
| G-K3 四支 migration IT | 0 | 42 |
| G-S5 BackupSidecarContractIT | 0 | 34（26 sidecar＋8 arch）；全部突變還原後 G-K2 137、前端 289 測全綠＝無殘留 |
| G-F1 lint／G-F2 tsc | 0／0 | — |
| G-F3 test:cov | 0 | 101 檔 1710 測；`sysadminBackup.ts` 100% 列在 lib/domain 段 |
| G-F4 build | 0 | ○ /sysadmin、○ /sysadmin/backup |
| G-F5 | — | sysadmin-backup.mock.spec 1 條通過；shells-and-layout.spec 需真後端（ECONNREFUSED :8080，未跑） |
| G-F6 schema 等價重產 | — | 位元組相同 |
| G-S1 run_shellcheck | 0 | 11／11 基線（scratch git repo 內 HEAD 54 支 shell）＋三支新腳本 `-S style` rc 0＋`bash -n` 五支 OK、CR 0 |
| G-S2／G-S3 | 0／0 | 另全掃 110 個變更檔 rc 0 |
| G-S4 | 0 | pytest 38 條通過、ruff 雙視角 rc 0、TestTextIoDeclaresEncoding 7 OK |
| G-S6 promtool | — | test SUCCESS、check rules 14 條、check config rc 0 |
| G-S7 `compose config --volumes` | 0 | 14 卷 |
| G-C1 | — | 六 commit 聯集 ⊆ §5.7，除 F7 三檔 |
| G-C2／G-C3 | 0／0 | `f150e35a^..HEAD` |
| G-C4 | — | 六 commit 0 命中（字面 3 命中見 F7） |
| G-C5 | — | 12 個同步鎖檔被刪斷言行 ≤ 新增（無淨減） |

### E. 契約一致性（Code vs Contract vs TCS §C）

TCS §C（C0 8 列、C1 9、C2 7、C3 21、C4 15、C6 7）對契約檔逐列相同、0 差異（契約檔只多附錄 A／B 與標題形式）；`BACKUP_REASONS`（13 鍵）↔ `ErrorReasons.BACKUP_*`（5）＋`BackupJobReason`（8）↔ 契約〈backup 類 reason 表〉三方逐字相同（BackupReasonsContractTest 綠）；OpenAPI 三路徑／四 operationId 與 §C3 相符（77 路徑／89 操作）；C1 檔案協定：sidecar IT 斷言鍵序與型別等於 §C1，後端 `FileBackupControlAdapter`＋`ExportReader` 與 `FakeBackupRunner` 同形，`info-2repo.json` 與 `mask-probes.txt` 兩端共讀同一檔；尚無「真 pgbackrest 輸出對真解析端」串接（屬真機 V1～V3）。偏離點：F5、F9、決策 2 的目錄不存在語意。

### F. 內容品質抽讀（審查者）

狀態詞（成功／失敗／進行中／中斷／從未執行）＋圖示、逾期只讀 `card.overdue` 不重算、失敗卡同列「最近一次成功」；降級提示：整頁原因面板文字不含「尚無備份」與數字、`runner_offline` 紅橫幅 `role=alert` 加「可能已過期」、匯出 >180 秒「已過期」；repo 狀態碼 0～6／99 對 pgBackRest 語意相符；還原三步與核對三項逐行等於 README〈4.3〉；「本頁不提供還原按鈕」與原因寫明；涵蓋表 14 卷四分類與 compose 頂層卷（G-S7）及 README〈1.2〉一致；ADMIN 才有的尾段後端非 ADMIN 為 null、前端再擋一層、純文字節點渲染。小處（P4）：cards 為 null 時「原因見上方提示」需 HintBar 同時存在才成立。

### G. 決策檔 1～20 裁定（審查者）

1 成立｜2 改寫成立（兩卷階一皆掛；補 REQ_DIR 亦已設；目錄不存在⇒export_unreadable）｜3 成立，由 8 取代｜4 成立｜5 成立｜6 成立（PRD 勘誤待補 1-16）｜7 成立｜8 成立（啟動接線無 AT＝F6）｜9 成立｜10 成立｜11 成立｜12 成立｜13 成立（14 卷；勘誤 R-BK-44／45、FRD-lite、AT-08-2-1／08-3-1／08-3-2）｜14 成立｜15 成立（§5.7 註記持有面）｜16 成立（四補 AT 編入 §3.2）｜17 成立｜18 成立（06-8-4 輪詢註冊無鎖＝F6 U7）｜19 成立但驗證不足（requestedBy 反例缺＝F6 U6）｜20 成立（GitHub runner 未驗）。另建議 TCS §2〈突變規格〉補一句：sidecar 腳本不是 Gradle test 任務輸入，重放須 `cleanTest`。

### H. 二審、真機與凍結紀錄

- **真機 ES（2026-10-31 06:1x，真機棒；全棧映像 01:47 含 K1／F1）**：先 `docker compose exec -u postgres pgbackrest job-run.sh full manual` rc 0（兩份全備 `20261031-061458F`／`061500F`，repo1／repo2 各 3.5MB；匯出 `jobs/full.json` last＝manual／succeeded、heartbeat 刷新）；`npx playwright test -c tests/e2e/docker.config.ts -g "AT_BK_"` rc 0：AT-BK-02-1-R-1 ✓（pgBackRest 14 份、離站邏輯備份 6 個，清單與真值逐份相符）、AT-BK-05-2-R-1 ✓（停 sidecar 約 30 秒內出現離線橫幅、GET 200＋runner_offline、啟回後恢復；sidecar 結尾 Up、RestartCount 0）。備份頁人讀代驗（ADMIN／VIEWER×1440／390，problems 0）：四張卡對 `jobs/*.json`＋`pgbackrest info`、WAL 單行對 `pg_stat_archiver`、「資料更新於」＝`exportGeneratedAt`、清單 20 列＝14＋6、排程六列與下次時間對 crontab 與 `schedule.json`、保留一行對 `pgbackrest help expire`＋`LOGICAL_BACKUP_RETENTION_DAYS`、涵蓋表 14 卷＝`compose config --volumes`、ADMIN 三個輸出尾段／VIEWER 零且 API 無 `detailTail`。新發現 F11（axe，P2）見 §B。證據 scratchpad `qa-real\`。
- **二審（2026-10-31 12:08～12:58，新鏡 r2，副本 `git archive d4aeab5b`）**：PASS（無 P1／P2）。發現：R2-01 P3 十處非 DB 例外日誌仍直出 `e.toString()`／`getMessage()`（`BackupJobService:118`；`BackupJobReconciler:124／261／275`；`BackupQueryService:663／673`；`FileBackupControlAdapter:110／124／145／149`；判型皆 JDK 檔案 I/O、自寫 SchemaProblem、Jackson 解析，無 DB 密碼／金鑰流入路徑，故 P3）；R2-02 P3 `AT_BK_06_8_4_startRegisters…` 只斷言 20 ms 下 10 秒 ≥3 次，interval 改常數 1000／2500 倖存；R2-03 P4 U12 字面鎖 WHY 不精確（`REPLACE_EXISTING`＝先 unlink 再 rename 的空窗）且掃整檔含註解；R2-04 P4 AT_BK_06_9_3 的 POSIX 半在 Windows 靜默不跑、勘誤 1-21 字面要改；R2-05 P4 E2 只掃 ADMIN（VIEWER 390 探針 0 違規、等價覆蓋）；R2-06 P4 S 系列命名不在 §2、06_9_3 對應改掛 C1、AT_BK_08_2_2 比 08-1-E-2 更嚴；R2-07 P4 BackupSeam 新縫補 §5.2。G-C1 對 e205c0f5 三支 service 八處遮罩的判定：R-BK-58「日誌行」條款下的正當消除成因修法，在 §5.7 K 包內。摩擦：harness 拒寫報告檔（本節由主控落檔）、Playwright 預設埠會 reuse 在線容器（改 3917／3918）、fe_m 副本 AT_BK_01_2_E_2 不穩（tree 全樹 3／3 綠，不作判據）。
- **二審後 P3 修復（主控派 Sonnet 修復棒，backend 只動 K 包）**：R2-01 十處同形改經 `BackupMasker.mask`＋新增靜態掃描 AT（backup 類別所有把例外寫進 LOG 的站點須經遮罩；紅綠自證）；R2-02 `AT_BK_06_8_4` 加第二情境（`reconcileMs=600_000`、3.5 秒、輪詢零次）；R2-03 WHY 改寫＋只掃程式碼行。結果（修復棒交卷＋主控親驗，2026-10-31 14:0x）：production 改動 `git diff --stat` 4 檔 +11／−10（一個 import＋十行日誌，行為零變更）；新 AT `BackupArchTest.AT_BK_10_4_S_1_everyBackupLogCallThatCarriesAnExceptionMasksItWithBackupMaskerFirst`（編號取 `_S_n` 先例，AT-BK-10-4-2 已是 PY 載具）——主控紅燈探針：把 `BackupJobReconciler:275` 還原成 `e.toString()` 跑 `cleanTest test --tests "*BackupArchTest*"` rc 1、XML 8 個測試／1 失敗、失敗者恰該 AT；改回後 `cleanTest test --tests "*Backup*"` rc 0、XML 10 檔 149 個測試／0 失敗／0 錯誤／0 跳過（含 `AT_BK_06_8_4_startRegisters…` 第二情境與新 AT）；修復棒 `clean build` rc 0（2217 個測試／0 失敗／0 錯誤／0 跳過；二審基線 2216＋1）、checkstyle／JaCoCo 過、secret_scan 7 檔 rc 0。修復棒另驗：十處未遮時 AT 恰點名 10 筆、R2-02 三個間隔突變情境二皆紅、R2-03 註解含字樣不再誤紅。
- 勘誤套用（主控，路由第 4 點；`apply_backup_errata.py`，PRD Stage-2 digest 核對通過）：TCS 檔尾〈勘誤一〉1-1～1-31（含二審 R2-01～R2-07 的 1-21／1-27～1-30 訂正、RTM 文件棒發現的 AT-BK-05-2-R-1 時限語意 1-31）、PRD 檔尾〈勘誤二〉2-1～2-3；TCS 檔頭 PRD digest 同步、§1 增量追溯表保留 Stage-2 快照（原值字樣餘 2 處屬快照）。新 digest 由 `spec-refreeze` 記入（下一行）。
- FSM 鍵 `agentconsole-sysadmin-backup`（主控依凍結常態規則執行）：IMPLEMENTATION → `transition --to PR_REVIEW` → `gate PR_REVIEW PASS`（→ RTM_VERIFY，fsm rc 0，2026-10-31 14:0x）→ RTM §2.6 子表（文件棒；F 1／US 10／AC 54／AT 239，§3.4 計數前後不變）→ `gate RTM_VERIFY PASS`（→ RELEASE_READY，fsm rc 0）→ `spec-refreeze --doc PRD --doc TCS` rc 0（2026-10-31 14:2x）：`refrozen: true`、`stage: Stage-2`、`supersedes: 2026-10-27T16:30:22+00:00`；記入 PRD `sha256:1eeb770758738b7f260ee4656243d5b46e71cbf59fb985b10ad9aec356632841`（69,073 bytes，含〈勘誤二〉2-1～2-3）、TCS `sha256:5e8236d44fbaa9d191498827bd8fb5b152fe4b19b042f346836638870b34a9a5`（含〈勘誤一〉1-1～1-31；Stage-2 原值 `sha256:14e4e2ff…5795`）。鍵狀態 RELEASE_READY；RELEASE 轉移待掌舵者裁示（階一 RM×4 真機未跑，見 §H 首段）。另：RTM.md 逼近 `secret_scan` 1 MiB 上限（§2.6 已改精簡版；帳本 DEF-200-576 closed-by-decision，再開症狀＝下一個子表動工或 RTM.md 超 1 MiB，屆時每功能一檔拆檔）。

### I. 流程摩擦（審查者；主控處置）

1. Gradle test 任務不把 sidecar 腳本當輸入：倖存突變後下一批判 UP-TO-DATE 形成假存活，以 `cleanTest` 重跑 17 批 → TCS 勘誤 §2。
2. vitest 預設 5 秒逾時在機器負載下造成假 killed；改 `--testTimeout=120000`。
3. PostToolUse hook 把 `.ps1` 轉 CRLF，含多行字面字串的突變腳本與 LF 原始碼比對失敗（改用 `n）。
4. 副本無 `.git`：`run_shellcheck` 與 `TestTextIoDeclaresEncoding` 需另建 scratch repo／全匯出。
5. 收尾：副本、scratch repo、拋棄式容器與 `C:\t` 已刪；工作樹零改動。
