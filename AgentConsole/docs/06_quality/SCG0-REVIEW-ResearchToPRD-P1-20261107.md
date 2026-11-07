# TCS-ResearchToPRD-P1 覆蓋審報告（含第五版四審；唯讀）

## 四審（只核 §4 第 34 列 TCS:1731、AT-961-1-1 :1222、AT-961-1-8 :1254 三處的一致性與對 `ResearchSchemaMigrationIT.java` 的可施工性）

**最終判定：PASS（P1 0、P2 0、P3 0、P4 0）。**

逐句核對（對原始碼）：
- 第 34 列：兩個 P0 常數 `RESEARCH_TABLES`（:64）與 `CONTROLLED_TABLES`（:62）不動；新增 `V19_TABLES`（五）、`V19_CONTROLLED_TABLES`（四）。`:495` 釘 `databaseAt("18")` 對 P0 十三張、V19 增量另以 `databaseAt("19")` 對 `V19_TABLES`——與 `:463-464` 現行結構相容，`added` 為十三張。`:518` 的守衛表集合（共用資料庫、全部 `research_` 觸發器）＝P0 十三加 V19 五（deliveries 掛 append-only 守衛，故五表皆有守衛）＝十八，期望值「P0∪V19」正確。`:1385-1389` 的通用守衛引用表＝P0 五加 V19 四（K.4：route_decisions、route_steps、scr、decompositions 掛 `research_controlled_update_guard`）＝九，期望值「P0∪V19」正確。`:1377` 迴圈不動，仍只對 P0 五表（`rowIds` 與 `CONTROLLED_UPDATE_COLUMNS` 只含這五表），不會 NPE。
- AT-961-1-1（:1222）的敘述與第 34 列逐項一致（P0 常數不變、V19 另立、`:518`／`:1385-1389` 為 P0 加 V19、指向第 34 列）。
- AT-961-1-8（:1254）自備列定位（三表 `id`、`research_route_steps` 以 `(route_id, step_no)`）、不使用 `rowIds`／`CONTROLLED_UPDATE_COLUMNS`，與第 34 列「V19 四表由 AT-961-1-8 另驗」一致。
- 實跑：自檢腳本 `checks=49 fail=0`、rc=0。

三處一致、對現行測試原始碼不產生 NPE 或新紅燈（推論：依原始碼逐行判讀，未跑 gradle）。前三輪的 N-01～N-07 全數關閉。

---
# TCS-ResearchToPRD-P1 覆蓋審報告（含第四版三審；唯讀）

## 三審（第四版：AT 209、RTM 238；範圍只核 N-01～N-06）

**三審判定：FAIL（P1 0、P2 1、P3 0、P4 0）。** N-02～N-06 全數落實；N-01 只做了一半——AT-961-1-1 與 AT-961-1-8 改對了，但 §4 第 34 列（TCS:1731）本身仍是舊的、會製造紅燈的文字，與 AT-961-1-1 直接矛盾。

### 實跑（本回合真跑）
- 自檢腳本：`checks=49 fail=0`、rc=0。守門掃描：TCS、RTM 皆 0 站點。
- AT-961-24-1 一行式：PowerShell `Select-String` 與 Git Bash `grep -c` 各跑一遍（路徑指 scratchpad 檔），兩種殼皆為 AC 25、AT 209、RTM 238、passed／skipped 加四位數同行 0，與 TCS 寫死的期望值一致。

### N-01～N-06 狀態
| ID | 狀態 | 現查 |
|---|---|---|
| N-01 | **未完全落實（仍 P2）** | AT-961-1-1（:1222）已改對：`:495` 改釘 `databaseAt("18")` 對 P0 十三張、`CONTROLLED_TABLES`／`RESEARCH_TABLES` 維持 P0 值、V19 另立 `V19_TABLES`（五）與 `V19_CONTROLLED_TABLES`（四）、`:518` 與 `:1385-1389` 期望集合為 P0 加 V19、`:1377` 迴圈不動——對照 `ResearchSchemaMigrationIT.java:1377`、`:1398` 後這套安排不會 NPE。AT-961-1-8（:1254-1258）自備列定位、複合主鍵表以 `(route_id, step_no)`、明言不使用 `rowIds` 與 `CONTROLLED_UPDATE_COLUMNS`：正確。**但 §4 第 34 列（TCS:1731）完全沒改**：仍寫「`RESEARCH_TABLES` 改十八張、`CONTROLLED_TABLES` 改九張」「`:463-464` 釘 `databaseAt("18")`」。開發棒照 §4 施工會得到 NPE（`:1377` 迴圈對 V19 四表）與 `:495` 兩邊不等的新紅燈；而 AT-961-1-1 又寫「見 §4 第 34 列」，兩處互相矛盾。（SD 回報「第 34 列改寫 :1731」與檔內實況不符。） |
| N-02 | 已落實 | E1（:1739）改 `adopt.adopt_baseline` |
| N-03 | 已落實 | AT-961-7-7（:871-873）末句改「正負控放在既有 `test_research_fsm_ops.py` 末尾」 |
| N-04 | 已落實 | AT-961-20-E-2（:1602）改純函式判讀（不渲染，`hasDrift`／`pendingCorrection`）；新 AT-961-20-E-4（:1607）載具為 `BuildFrontPanel.test.tsx`（屬 PKG-FE-D2 §5.7）、`stubApi` 三夾具、Then 可機械判定（待校正說明、重新對帳鈕、無漂移橫幅），判定指令帶 `-t AT_961_20_E_4` 且該檔本期新增測試，可執行 |
| N-05 | 已落實 | AT-961-11-2（:1284）改「憑證 subject 為空字串回 400」，並加本文帶 `approver:"mallory"` 不被採用；Given 句殘留「缺 approver 的請求」字樣但 When 已具體，不影響判定 |
| N-06 | 已落實 | AT-961-11-4（:1294）只驗 409 與透傳形狀，STALE 寫入明歸 AT-961-10-5 |

### 新發現
| ID | 嚴重度 | 座標 | 問題 | 修法 | 指名 |
|---|---|---|---|---|---|
| N-07（即 N-01 殘留） | P2 | §4 第 34 列（TCS:1731） | 同上：列內「現值／改後值」仍是會製造紅燈的舊內容，與 AT-961-1-1（:1222）、AT-961-1-8（:1255）矛盾 | 第 34 列「改後值」改寫為：`CONTROLLED_TABLES`、`RESEARCH_TABLES` 維持 P0 值不動；新增 `V19_TABLES`、`V19_CONTROLLED_TABLES`；`:495` 釘 `databaseAt("18")` 對 P0 十三張並另立 V19 增量斷言；`:518`、`:1385-1389` 期望集合為 P0 集合∪V19 集合；`:1377` 迴圈不動；訊息字樣為 V16～V19 | SD；落實歸 PKG-DB-P1 |

### 三審誠實劃界
- 唯讀、未跑 gradle／vitest／pytest；N-01 判讀依 `ResearchSchemaMigrationIT.java` 原始碼（:495、:518、:1377、:1385-1389、:1398）。
- 依指示不擴大抽讀；僅核 N 項與新增 AT-961-20-E-4。

---
# TCS-ResearchToPRD-P1 覆蓋審報告（含第三版二審；唯讀）

## 二審（第三版：1905 行、AC-961 25、AT 208＝正控 166＋負控 42、RTM 237 列、§4 硬釘 36 筆、§7 39 列）

**二審判定：FAIL（P1 0、P2 1、P3 5、P4 0）。** 一審七個 P2 與八個 P3／P4 全數落實；剩一個 P2 是 SD 為 F-01 寫的修法本身會讓既有測試新增紅燈（N-01）。

### 實跑結果（本回合真跑）
- 自檢腳本 `_aux\selfcheck.py`：`checks=49 fail=0`、rc=0。
- 守門掃描（`passed|skipped` 同行含四位以上數字或 `NNNN/NN` 式樣）：TCS、RTM 皆 0 站點。
- AT-961-24-1 的 shell 一行式，我自己對第三版跑（PowerShell 的 `Select-String` 與 Git Bash 的 `grep -c` 各一套，路徑改指 scratchpad 檔）：AC 定義列 25、AT 定義列 208、RTM 列 237、passed／skipped 加四位數同行 0；兩種殼結果相同，期望值與 TCS 寫死值一致。
- 我的獨立解析：AT 208、四行齊全缺 0、不可判字眼 0、載具分佈 pytest 121／gradlew 49／vitest 33／指令核對 5；§1.2 與 §3 各 AT 標題的 PRD 引用逐條一致。

### F-01～F-15 狀態表（座標為第三版現行行號，與 SD 回報逐一對上）
| ID | 狀態 | 現查座標與說明 |
|---|---|---|
| F-01 | **部分落實，修法有誤→N-01** | §4 第 34 列（TCS:1725）已補，但內容會製造新紅燈 |
| F-02 | 已落實 | AT-961-1-E-1（:1263）改「十八張（P0 十三張加 V19 五張）」 |
| F-03 | 已落實 | §4 第 5 列（:1684）補 `:452-463` 八改九；AT-961-15-6（:1398）Then 同步 |
| F-04 | 已落實 | 第 14 列（:1698）C2 白名單加 `research/adopt.py`、限內環鍵與 Stage-1、紅綠夾具；⚖P1-38（:1883）；§5.7 PKG-BR-D1 含 `adopt.py`；全文 `adopt.adopt_baseline`（殘留一處見 N-02） |
| F-05 | 已落實 | AT-961-19-3（:1576）、19-6（:1591）、19-2（:1571）判定改不帶 `-t` 整檔，並寫明理由 |
| F-06 | 已落實 | 新 AT-961-4-E-2（:740，299／300／301 秒且設定 299、301 使界線隨設定移動）、4-E-3（:745）；AT-961-2-E-1 補 `COMPENSATE_REASON_MAX`（1、500 過；0、501 違規）；4-9 補界值；14-8 補 30／31／330／331 |
| F-07 | 已落實 | AT-961-24-1（:1654）Then 25／208／237，判定為入庫 shell 一行式，不引用 scratchpad |
| F-08 | 已落實 | ⚖P1-24（:1871）定案；全檔 Grep「暫名」「以實作實際值」0 命中 |
| F-09 | 已落實 | 「落點待定」0 命中 |
| F-10 | 已落實 | AT-961-14-2 改「§4 第 6 列」 |
| F-11 | 已落實 | AT-961-4-E-1（:735）oracle 引 P0 原文（行為句逐字寫入 Given，不依賴 scratchpad）；D-128 |
| F-12 | 已落實 | 第 35、36 列（:1726-1727）、E2b（:1735）、AT-961-20-E-2、20-E-3 |
| F-13 | 已落實 | AT-961-3-3（:662-663）、8-4（:903）、§5.1 gitops 環境列（:1769）皆含 `GIT_OPTIONAL_LOCKS=0` |
| F-14 | 已落實 | AT-961-22-E-2 改比 HEAD、`status --porcelain`、`for-each-ref` 摘要 |
| F-15 | 已落實 | AT-961-7-7（:870）移到 BR-D2 的 `test_research_fsm_ops.py`，註明第一波不驗 |

### 新發現
| ID | 嚴重度 | 座標 | 問題 | 修法 | 指名 |
|---|---|---|---|---|---|
| N-01 | **P2** | §4 第 34 列（TCS:1725）；`ResearchSchemaMigrationIT.java:1362-1377`、`:1397-1399`、`:1389`、`:463-464`、`:495` | 第 34 列要把 `CONTROLLED_TABLES` 改九張、`RESEARCH_TABLES` 改十八張。(a) `:1377` 迴圈對 `CONTROLLED_TABLES` 每表呼叫 `checkControlledTable(…, rowIds.get(table), …)`，`rowIds` 只放了 P0 五表（`:1369-1375`），`CONTROLLED_UPDATE_COLUMNS.get(table)`（`:1398`）對 V19 四表為 null，會 NPE；`research_route_steps` 另是複合主鍵、沒有 `id` 欄，`where id = ?` 不成立。(b) 第 34 列同時把 `:463-464` 釘在 `databaseAt("18")`（`added` 只會是十三張），又把 `RESEARCH_TABLES` 改十八張，`:495` 的 `containsExactlyInAnyOrderElementsOf(RESEARCH_TABLES)` 兩邊對不上。照列施工必有新紅燈（推論：我沒跑，依程式碼逐行判讀）。 | 第 34 列改寫：`CONTROLLED_TABLES` 與 `RESEARCH_TABLES` 維持 P0 值不動；新增 `V19_TABLES`（五表）與 `V19_CONTROLLED_TABLES`（四表）；`:495` 以 `databaseAt("18")` 對 `RESEARCH_TABLES`、另立斷言驗 V19 增量等於 `V19_TABLES`；`:518` 與 `:1389` 的期望集合改為 P0 集合∪V19 集合；`:1377` 迴圈不動（V19 受控表的更新規則由 AT-961-1-8 另驗）。 | SD；落實歸 PKG-DB-P1 |
| N-02 | P3 | §4.4 E1（:1733） | 仍寫 `route.adopt_baseline`，與 D-126、⚖P1-38 的 `adopt.adopt_baseline` 不一致 | 改名 | SD |
| N-03 | P3 | AT-961-7-7 Then（:870 內）末句 | 仍寫「新正負控放在新檔」，但同 AT Given 已改為既有 `test_research_fsm_ops.py` 末尾 | 改為「放在該檔末尾的新增測試」 | SD |
| N-04 | P3 | AT-961-20-E-2（:1601）判定 | 載具為 `lib/domain/research.test.ts`（純 `.ts` 單元檔），Then 卻要「渲染對帳區塊」；渲染需 `.tsx` 元件測試 | 拆成判讀函式單元測試（本檔）與元件渲染測試（`GatekeeperPanel` 或對帳元件的 `.test.tsx`），各帶 `AT_961_20_E_2` 標題 | SD |
| N-05 | P3 | AT-961-11-2（:1283） | 「缺 approver（空字串與缺鍵）400」與同 AT「approver 取 JWT subject、本文帶 approver 鍵被忽略」互相拉扯：approver 不由本文取，「缺」只能指 JWT 無 subject | 寫明「缺＝憑證無 subject 的情形（夾具造一個無 sub 的 JWT）」，並刪「空字串與缺鍵」 | SD |
| N-06 | P3 | AT-961-11-4（:1293）Then | 要求「舊列 `status` 為 `STALE`（由 Bridge 寫入）」，但本 AT 是 console-api JUnit、迷你 Bridge 不寫庫，驗不到 | 改為只驗 console-api 以讀取時比對判 409，STALE 寫入歸 AT-961-10-5 | SD |

### 二審抽讀（一審未細讀者共 48 個 AT；每個都對照 Given 前置、Then 可判、hermetic、與 PRD／FSM／現碼）
Bridge scr：12-2、12-3、12-5、12-6、12-7、13-2、13-4、13-5、13-6、13-7、13-8、13-9、13-E-1、13-E-3（內環邊 `IMPLEMENTATION／EXECUTION_EVALUATION／ADVERSARIAL_EVALUATION／PR_REVIEW→SPEC_AUDIT`、`SPEC_AUDIT→PR_REVIEW`、`PR_REVIEW→IMPLEMENTATION` 我對 `transition_rules.py:46-77` 逐條核對皆為合法邊）；decompose：10-2、10-3、10-4、10-5、10-7、10-8；tcs_draft：9-2、9-3、9-6、9-7；backend：11-1、11-2、11-4、11-5、11-6、14-3、14-4、14-5、14-6、14-7、15-4、15-6、15-8、15-9；新增：4-E-2、4-E-3、20-E-2、20-E-3、4-E-1、7-7。除 N-03～N-06 外皆通過。

### 二審誠實劃界
- 全程唯讀、未跑 gradle／vitest／pytest；N-01 為依 `ResearchSchemaMigrationIT` 原始碼逐行判讀的推論，凍結前請 SD 照我的座標自行覆核。
- 二審抽讀四十八個，加一審七十餘個，累計約佔 208 個 AT 的六成；其餘僅結構機械掃描。
- 沒有重審 §4 其他 33 筆硬釘的現值（一審已逐項核對，這次只核第 5、14、34～36 列與 F 項座標）。

---

# 一審原報告（保留，編號沿用）
# TCS-ResearchToPRD-P1（第二版）覆蓋審報告（QA 獨立、唯讀；輕量 SCG-0 增量審）

審查對象：`S\sd\TCS-ResearchToPRD-P1-20261107.md`（1862 行、AC-961 二十五、AT 二百零四＝正控 166＋負控 38）、`RTM-ResearchToPRD-P1-20261107.md`（233 列）、`_aux\`。S＝`C:\Users\wuwei\AppData\Local\Temp\claude\480c0aec144051b3\40b4052a-6070-494a-89db-ce4045862af8\scratchpad\r2p1`。工作樹 HEAD＝`9c628f0f`（本審以 Grep／Read 現查，未改任何檔）。

## A 判定與計數

**判定：FAIL（P2 未清零；P1 為 0）**

| 嚴重度 | 件數 |
|---|---|
| P1 | 0 |
| P2 | 7（F-01～F-07） |
| P3 | 6（F-08～F-13） |
| P4 | 2（F-14、F-15） |

要點：覆蓋面完整（PRD 的 P1 AC 三十七條＋增量十條全數落入 §1.2，P2 二十三條全數列於 §1.3；自檢腳本實跑 rc=0、四十九項通過）。FAIL 的原因全在「既有測試連動」與「AT 可執行性」：V19 與 SCR 端點落地後會轉紅卻沒列入 §4 的既有測試（F-01、F-03、F-04，P0 一審 F-01 同型）、一個數字錯誤使 AT 對正確實作也會紅（F-02）、判定指令跑不到所述斷言（F-05）、新常數缺界內界外 AT（F-06）、一個 AT 的 Then 數字與判定載具不成立（F-07）。

## B 發現表

| ID | 嚴重度 | TCS 座標 | PRD／契約／現碼座標 | 問題 | 修法建議 | 指名哪一棒修 |
|---|---|---|---|---|---|---|
| F-01 | P2 | §4.1 第 1 列（TCS:1642 附近）、AT-961-1-1（:1204） | `backend/src/test/java/com/aisdlc/console/infrastructure/persistence/ResearchSchemaMigrationIT.java:463-464`（`newDatabase()` 遷到最新、`databaseAt("15")`）、`:495`（`added` 須等於 `RESEARCH_TABLES`＝十三張，訊息「V16～V18 在 console 內恰多出 13 張表」）、`:518`（`guardsByTable.keySet()` 須等於 `RESEARCH_TABLES`）、`:1385-1389`（引用 `research_controlled_update_guard` 的表須等於 `CONTROLLED_TABLES`＝五張，訊息「恰為五張」）；Architecture K.4：V19 的 `research_route_decisions`／`research_route_steps`／`research_scr`／`research_decompositions` 四表掛 `research_controlled_update_guard`、`research_deliveries` 掛 append-only | V19 落地後這三處既有斷言對正確實作必紅（`added` 變十八張、守衛表集合多五張、通用守衛引用表由五張變九張）。§4.1 第 1 列只列版本清單 `:490,493`，AT-961-1-1 只寫新表斷言，沒有任何列處理這三處（HARDPIN_SCAN 與 TCS 內 `RESEARCH_TABLES`、`newDatabase`、`guardsByTable`、`:495` 皆 0 命中，推論：掃描只抓版本字串）。 | §4.1 加一列（標「例外：不只改預期值」）：`:463-464` 的比較基準改成「V19 範圍＝遷到最新 vs 遷到 18」另立斷言，或把 V16～V18 斷言的資料庫釘在 `databaseAt("18")`；`:518`、`:1385-1389` 的期望集合加 V19 五表（或限縮至 P0 表集合並由 AT-961-1-E-1 另驗 V19）；訊息字樣同步改為 V16～V19、十八張。 | SD（改 TCS §4.1 與 AT-961-1-1 Then）；落實歸 PKG-DB-P1 |
| F-02 | P2 | AT-961-1-E-1（:1249-1252）；RTM-P1:47 同字樣 | `ResearchSchemaMigrationIT.java:64-67`（`RESEARCH_TABLES` 十三張）；AT-960-1-1 標題「13 張新表」；P0 RTM:37 | AT 寫「所有 23 張 research_ 表（P0 十八張加 V19 五張）」、Then「表清單恰 23 張」。P0 實為十三張，V19 五張，合計十八張；對正確實作此 AT 必紅（不可執行）。 | 全文改為十八張（P0 十三張＋V19 五張）；Given 的「P0 十八張沿既有夾具」同改；RTM:47 同步。 | SD |
| F-03 | P2 | §4.1 第 5 列（RbacIT）、第 6 列（SecurityConfig） | `backend/src/test/java/com/aisdlc/console/infrastructure/security/RbacIT.java:452-463`（`research` 規則 matcher 清單 `containsExactly` 恰八條）、`:464-465`、`:481`（研究規則夾在 sysadmin 與 settings 之間）；`SecurityConfig.java:103-110` | 第 6 列要新增 `POST …/scr/*/apply` ADMIN 規則，現有 `containsExactly` 八條立即轉紅；第 5 列只列 `:342-345、:374-379、:404、:486-495`，沒有這一處。第 6 列還稱「`route` 規則 `:105` 已預置」，與此鎖的八條清單一致，所以只有新增那條會破。 | 第 5 列補 `:452-463`：預期清單加第九條 `HttpMethod.POST, "/api/v1/research/projects/*/scr/*/apply"`，位置在 `delivery/pr` 之後與 `allowlist` 之前或依實際行序；保留「夾在 sysadmin 與 settings 之間」斷言；AT-961-15-6 的 Then 補「規則清單恰九條」。 | SD；落實歸 PKG-API-P1 |
| F-04 | P2 | §4.2 第 14 列（:1662）、AT-961-7-1（:826-830）、§5.7 PKG-BR-D1（:1770） | `engine-bridge/tests/test_research_ast_locks.py:131-136`（C2 規則：`spec_frozen`／`approve_baseline` 呼叫只准在 `routers/research.py` 的 HTTP 處理函式內，或 `research/fsm_ops.py` 內的 `spec_frozen`）、`:257`（`test_AT_960_13_7_the_whole_app_tree_satisfies_every_rule`）；`app/research/fsm_ops.py:314`；IFACE:183-190 的採納序列含 `spec-frozen --stage Stage-1` | 基線採納要在內環鍵呼叫 `fsm_ops.spec_frozen`（Stage-1），呼叫點在 `adopt`／`route` 模組而非 `routers/research.py`，全樹 AST 鎖 C2 對正確實作必紅；§4.2 第 14 列只改 `create_key` 呼叫者集合與 `EXEC_MODULES`，沒處理 C2。另：採納函式的家不一致——AT-961-7-x 寫 `adopt.adopt_baseline`（測試檔 `test_research_adopt.py`）、第 14 列寫 `route.adopt_baseline`、§5.7 PKG-BR-D1 只列 `{route,scaffold,gitops}.py`，沒有 `adopt.py`。 | §4.2 第 14 列補「例外（改規則）」：C2 的 `spec_frozen` 白名單加採納模組檔（例如 `research/adopt.py`，並要求位於 HTTP 處理函式或 `route.execute` 的呼叫鏈、僅限內環 `Stage-1`）；統一函式名與檔案；§5.7 PKG-BR-D1 加該檔；紅綠自證夾具（`test_research_ast_locks.py:193-217`）補一正一負。 | SD；落實歸 PKG-BR-D1 |
| F-05 | P2 | AT-961-19-3（:1557-1561）、AT-961-19-6（:1572-1576）；另 AT-961-19-2（:1552）的既有三道鎖部分 | `frontend/components/domain/help/stateKeys.test.ts:100`（既有、本檔宣稱零改動）；`frontend/tests/design-rules.test.ts`（既有、零改動）；P0 命名規則（TCS:45：vitest 的 `it` 標題以 `AT_961_n_m` 起頭） | 這兩個 AT 的 Then 是「既有檔零改動仍綠」，判定卻是 `npx vitest run <既有檔> -t AT_961_19_3`／`-t AT_961_19_6`；零改動的檔裡沒有任何標題含此字樣，`-t` 會把全部測試篩掉而不跑斷言（推論：vitest 對全數被名稱篩掉的檔回 rc 0），AT 永遠無法轉紅。 | 判定改為不帶 `-t` 跑完整檔（`stateKeys.test.ts`；`design-rules.test.ts`、`layout.test.tsx`、`si.static.test.ts`、`sysadminBackup.test.ts`、`registry.test.ts`、`content.test.ts`），或在新增的 P1 測試檔內加標題含 `AT_961_19_3`／`19_6` 的包裝測試去呼叫同一判準；AT-961-19-2 同查（`lib/help/research-workspace.test.ts` 現不存在，須註明為新檔）。 | SD |
| F-06 | P2 | §5.1「分流執行」「理由上限」列（:1721、:1726）；AT-961-14-8（:1344-1347）；AT-961-4-9（:726-730）；AT-961-2-E-1（:641-645） | D-105（`BRIDGE_ROUTE_TIMEOUT_SECONDS`＝300、讀逾時 330 s）；P0 一審 F-03 同型 | 新常數缺恰在界內與界外各一的 AT：(a) `BRIDGE_ROUTE_TIMEOUT_SECONDS`＝300 沒有任何 AT 以假時鐘驗 299／300／301 秒的行為（牆鐘逾時回 502 `route_step_failed`、路由列 `FAILED`、`failure_step`、後續副作用為零；§5.3 只說「以假時鐘注入驗證」，AT 內無此案例）；(b) `COMPENSATE_REASON_MAX`（500）不在 AT-961-2-E-1 的常數清單內，AT-961-4-9 只有「空或超 500 字」，界內 1／500 未明寫；(c) 讀逾時只測 31 秒與 331 秒，缺 30／330 秒界內。 | 在 `test_research_route_exec.py` 增一個 AT（假時鐘：299 秒仍在跑、300 秒觸發逾時、301 秒不再接受後續步驟）與其負控；AT-961-2-E-1 的 Given 補 `COMPENSATE_REASON_MAX`；AT-961-14-8 補 30／31 與 330／331 兩對。 | SD |
| F-07 | P2 | AT-961-24-1（:1630-1634） | TCS 檔頭與 RTM：AC-961 共 25、RTM 233 列＝1＋3＋25＋204 | Then 寫「RTM-P1 列數等於 F 1、US 3、AC 24 加 AT 總數」：AC 應為 25，照字面核對會得 232≠233。判定欄引用 `_aux/selfcheck.py`——住在 scratchpad、不入庫，他機與本輪之後無法重現（違反修復不留後遺症三問之一）。 | 改為 AC 25；判定改為入庫可跑的指令（`git grep -c` 計列＋ pre-commit 摘要字樣掃描），或明寫「自檢腳本隨 RTM-P1 落入 `docs/06_quality/` 並版本化」。 | SD |
| F-08 | P3 | AT-961-15-3（:1372）、AT-961-19-5（:1570）、⚖P1-24（:1830） | D-118「operationId 定案」九個名稱 | D-118 已把九個 operationId 定案，TCS 仍寫「暫名」「以實作實際值為準並同步本列」，使名稱型斷言可被任意改名繞過。 | 刪「暫名／以實際為準」字樣，⚖P1-24 改為定案列。 | SD |
| F-09 | P3 | §1.4 第 344 列 | D-123 | 「⚖P1-26：落點待定」殘留；D-123 已定歸 API-P1。 | 改為「API-P1（D-123）」。 | SD |
| F-10 | P3 | AT-961-14-2（:1317） | §4 第 6 列 | 「§4 第 17 列註明不需改」：第 17 列是 Bridge 對帳；SecurityConfig 是第 6 列。 | 改交叉參照。 | SD |
| F-11 | P3 | AT-961-4-E-1（:731-734）、⚖P1-21（:1827） | D-118 ⚖P1-21 | AT 自陳「P0 未結項原文未讀」，oracle 由 SD 依原則自擬；與 D-118「細節由 BR-D2 依 P0 報告原文落實」可能不一致，鑑別力無法保證。 | 開工前由 SD 讀 P0 INT 與一審報告原文後校正 Then；或明寫 BR-D2 開工前須對該段原文並回報差異。 | SD |
| F-12 | P3 | AT-961-20-3（:1136-1139）、§4 第 32 列 | `ReconcileResultDto.java:29`（Schema「ok｜drift｜NOT_EVALUABLE」）、`frontend/lib/domain/research.ts:525-534`（只認 `drift`） | 對帳新增第三態 `pending_correction` 後，console-api DTO 說明、OpenAPI、前端顯示與契約 E2 勘誤皆未涵蓋；前端會把未知狀態當「非漂移」（行為可接受，但文件與型別未對）。 | §4 加一列：DTO Schema 說明與契約勘誤補第三態；前端 `research.ts` 加一個測試釘「`pending_correction` 不算漂移」。 | SD（落實 PKG-API-P1、FE-D2） |
| F-13 | P3 | AT-961-3-3（:656-660） | — | 要求 `.git/index` 位元組雜湊前後不變，但記錄動作本身跑 `git status --porcelain`（可能順手刷新 index）。 | 記錄用的 git 呼叫加 `GIT_OPTIONAL_LOCKS=0`／唯讀管道，並於 Then 寫明。 | SD |
| F-14 | P4 | AT-961-22-E-2（:1176-1180） | — | 「真 repo `.git` 位元組整個測試前後不變」在多視窗並行工作時有偶發失敗風險（推論）。 | 改比 `HEAD`、`status`、`refs` 摘要。 | SD（可延後） |
| F-15 | P4 | AT-961-7-7（:856-860）、§5.7 | BR-D1 測試檔 `test_research_adopt.py`、產品 `sdd_cli.py` 在 BR-D2 | 7-7 的測試住 BR-D1 的檔，被測的 `tcs gate` 前綴在 BR-D2 才落地，第一波 BR-D1 單獨驗收時 7-7 必紅。 | 把 7-7 歸 BR-D2 的新測試檔或註明波次依賴。 | SD（可延後） |

## C 覆蓋對照表（P1 的 AC-R2P 全表 → AC-961 → AT；自 TCS §1.2 機械展開，並以我自己的腳本與 PRD 現查交叉核對）

現查結果：PRD 共 171 條 AC-R2P；FR-11（8）、12（6）、13（8）、14（7）、19（8）＝37 條全數出現在 §1.2，缺 0；增量十條（02-4、02-5、02-7、02-8、04-11、21-2、21-5、21-6、23-1、23-4）全數在 §1.2 且皆屬 P0 的部分列或已覆蓋列的 P1 半。P0 TCS 標「部分」的 01-5、02-4、02-5：02-4／02-5 的 P1 半已承接、01-5 的尾巴（ResearchBackLink）依 TCS-P0 ⚖2 屬 P2，已寫入 §1.2 標題說明與 §1.3 說明，判定正確。§1.3 恰二十三條 P2（15-1～15-6、16-1～16-5、17-1～17-4、18-2、18-3、20-1～20-6），與 PRD 差集 0；§1.2 與 §3 各 AT 標題的 PRD 引用逐條對拍一致（我自寫腳本 qa\chk2.py：不一致 0）。AC-961 一至二十五皆有 AT；每 AC 正負控序各不超過九；RTM 的 AT 集合與 TCS 完全相等。

| AC-R2P | AC-961 | AT 數 | 首 AT … 末 AT | 判定 |
|---|---|---|---|---|
| AC-R2P-11-1 | AC-961-2、AC-961-15、AC-961-17 | 4 | AT-961-2-7 … AT-961-17-2 | 有 |
| AC-R2P-11-2 | AC-961-3、AC-961-14、AC-961-17、AC-961-22 | 8 | AT-961-3-1 … AT-961-22-2 | 有 |
| AC-R2P-11-3 | AC-961-4、AC-961-7、AC-961-14、AC-961-17 | 14 | AT-961-4-1 … AT-961-17-7 | 有 |
| AC-R2P-11-4 | AC-961-2、AC-961-14、AC-961-15、AC-961-17 | 7 | AT-961-2-4 … AT-961-17-E-2 | 有 |
| AC-R2P-11-5 | AC-961-2、AC-961-8、AC-961-17 | 5 | AT-961-2-1 … AT-961-17-E-2 | 有 |
| AC-R2P-11-6 | AC-961-3、AC-961-14、AC-961-16、AC-961-17、AC-961-22 | 7 | AT-961-3-5 … AT-961-22-5 | 有 |
| AC-R2P-11-7 | AC-961-7、AC-961-8、AC-961-22 | 11 | AT-961-7-1 … AT-961-22-3 | 有 |
| AC-R2P-11-8 | AC-961-4、AC-961-14 | 5 | AT-961-4-9 … AT-961-14-5 | 有 |
| AC-R2P-12-1 | AC-961-3、AC-961-5、AC-961-22 | 8 | AT-961-3-1 … AT-961-22-E-2 | 有 |
| AC-R2P-12-2 | AC-961-5 | 1 | AT-961-5-3 … AT-961-5-3 | 有 |
| AC-R2P-12-3 | AC-961-2、AC-961-17 | 2 | AT-961-2-3 … AT-961-17-3 | 有 |
| AC-R2P-12-4 | AC-961-5、AC-961-14 | 3 | AT-961-5-5 … AT-961-14-7 | 有 |
| AC-R2P-12-5 | AC-961-4、AC-961-5 | 4 | AT-961-4-2 … AT-961-5-E-1 | 有 |
| AC-R2P-12-6 | AC-961-5 | 1 | AT-961-5-4 … AT-961-5-4 | 有 |
| AC-R2P-13-1 | AC-961-3 | 3 | AT-961-3-2 … AT-961-3-5 | 有 |
| AC-R2P-13-2 | AC-961-6 | 4 | AT-961-6-4 … AT-961-6-E-1 | 有 |
| AC-R2P-13-3 | AC-961-2、AC-961-17 | 6 | AT-961-2-1 … AT-961-17-E-2 | 有 |
| AC-R2P-13-4 | AC-961-4、AC-961-6、AC-961-8、AC-961-14、AC-961-22 | 17 | AT-961-4-3 … AT-961-22-E-1 | 有 |
| AC-R2P-13-5 | AC-961-6 | 1 | AT-961-6-5 … AT-961-6-5 | 有 |
| AC-R2P-13-6 | AC-961-3 | 1 | AT-961-3-6 … AT-961-3-6 | 有 |
| AC-R2P-13-7 | AC-961-2、AC-961-16、AC-961-17 | 6 | AT-961-2-5 … AT-961-17-4 | 有 |
| AC-R2P-13-8 | AC-961-6 | 4 | AT-961-6-1 … AT-961-6-9 | 有 |
| AC-R2P-14-1 | AC-961-10、AC-961-11、AC-961-15、AC-961-18 | 15 | AT-961-10-1 … AT-961-18-7 | 有 |
| AC-R2P-14-2 | AC-961-10、AC-961-11、AC-961-18 | 6 | AT-961-10-3 … AT-961-18-E-1 | 有 |
| AC-R2P-14-3 | AC-961-11、AC-961-18 | 5 | AT-961-11-1 … AT-961-18-5 | 有 |
| AC-R2P-14-4 | AC-961-11 | 3 | AT-961-11-3 … AT-961-11-E-2 | 有 |
| AC-R2P-14-5 | AC-961-10、AC-961-11、AC-961-15、AC-961-18 | 7 | AT-961-10-5 … AT-961-18-5 | 有 |
| AC-R2P-14-6 | AC-961-10 | 1 | AT-961-10-6 … AT-961-10-6 | 有 |
| AC-R2P-14-7 | AC-961-7、AC-961-9、AC-961-11、AC-961-18、AC-961-22、AC-961-25 | 18 | AT-961-7-7 … AT-961-25-E-1 | 有 |
| AC-R2P-19-1 | AC-961-12、AC-961-15 | 9 | AT-961-12-1 … AT-961-15-E-1 | 有 |
| AC-R2P-19-2 | AC-961-13 | 3 | AT-961-13-1 … AT-961-13-E-1 | 有 |
| AC-R2P-19-3 | AC-961-12 | 2 | AT-961-12-3 … AT-961-12-7 | 有 |
| AC-R2P-19-4 | AC-961-12、AC-961-13 | 2 | AT-961-12-5 … AT-961-13-7 | 有 |
| AC-R2P-19-5 | AC-961-12、AC-961-15 | 2 | AT-961-12-2 … AT-961-15-1 | 有 |
| AC-R2P-19-6 | AC-961-12、AC-961-15 | 2 | AT-961-12-4 … AT-961-15-4 | 有 |
| AC-R2P-19-7 | AC-961-12 | 1 | AT-961-12-6 … AT-961-12-6 | 有 |
| AC-R2P-19-8 | AC-961-13、AC-961-22 | 10 | AT-961-13-1 … AT-961-22-4 | 有 |
| AC-R2P-02-4 | AC-961-21 | 1 | AT-961-21-1 … AT-961-21-1 | 有 |
| AC-R2P-02-5 | AC-961-21 | 2 | AT-961-21-2 … AT-961-21-E-1 | 有 |
| AC-R2P-02-7 | AC-961-1、AC-961-23 | 18 | AT-961-1-1 … AT-961-23-E-1 | 有 |
| AC-R2P-02-8 | AC-961-1 | 1 | AT-961-1-1 … AT-961-1-1 | 有 |
| AC-R2P-04-11 | AC-961-16 | 6 | AT-961-16-1 … AT-961-16-E-2 | 有 |
| AC-R2P-21-2 | AC-961-15、AC-961-19 | 4 | AT-961-15-E-2 … AT-961-19-E-1 | 有 |
| AC-R2P-21-5 | AC-961-19、AC-961-22 | 8 | AT-961-19-1 … AT-961-22-8 | 有 |
| AC-R2P-21-6 | AC-961-24 | 1 | AT-961-24-1 … AT-961-24-1 | 有 |
| AC-R2P-23-1 | AC-961-20、AC-961-25 | 6 | AT-961-20-1 … AT-961-25-E-1 | 有 |
| AC-R2P-23-4 | AC-961-20 | 1 | AT-961-20-4 … AT-961-20-4 | 有 |
## D 抽查 AT 表（共檢視 76 個；每個 AC-961 至少一個；負控 24 個）

判準：載具與指令可跑／Given 前置在 P1 落地後存在／Then 可機械判定／hermetic。「通過」＝四項皆成立。

| AC-961 | 檢視的 AT | 結論 |
|---|---|---|
| 1 | 1-1、1-E-1、1-E-2（讀 TCS 內文） | 1-E-1 數字錯（F-02）；1-1 缺 F-01 的既有斷言連動；1-E-2 通過 |
| 2 | 2-1、2-E-1（負控） | 通過（欄位表與界內外齊；COMPENSATE 缺，見 F-06） |
| 3 | 3-3、3-4、3-5 | 3-3 有 F-13（P3）；3-4、3-5 通過（零副作用的 DB、目錄樹、假 gh 紀錄皆可機械比） |
| 4 | 4-1、4-9、4-E-1（負控） | 4-1、4-9 通過；4-E-1 oracle 未對原文（F-11） |
| 5 | 5-1、5-6（負控型壓力） | 通過（`git worktree list`、HEAD、index 雜湊可判；真 git 僅在拋棄式 clone） |
| 6 | 6-4、6-7、6-E-2（負控） | 通過（掃描器自帶負控與非空範圍；token 脫敏邊界齊） |
| 7 | 7-1、7-7、7-E-1、7-E-2（負控 ×2） | 7-1 的 C2 連動缺（F-04）；7-7 波次依賴（F-15）；7-E-1、7-E-2 通過 |
| 8 | 8-1、8-4、8-7、8-E-1（負控） | 通過（argv 白名單表驅動；環境白名單與設定隔離明確） |
| 9 | 9-1、9-4、9-5、9-E-2（負控） | 通過（FSM 轉態 `SPEC_FROZEN→SPEC_DRAFTING` 在 `transition_rules.py:35` 合法；`:freeze` 走既有端點） |
| 10 | 10-1、10-6、10-E-1（負控） | 通過（`covers_ac` 由程式賦值、夾具刻意帶錯值；`signed_off` AST 判準） |
| 11 | 11-3、11-E-2（負控） | 通過（非研究專案零影響以請求數 0 判定） |
| 12 | 12-1、12-4、12-E-1 | 通過（`scr_limit` 2／3 界內外齊） |
| 13 | 13-1、13-3、13-E-2（負控） | 通過（人工等價序列夾具逐筆比對 decision_trace；任一步非 0 即停以 k=1..5 參數化） |
| 14 | 14-1、14-2、14-8、14-E-1（負控） | 14-1、14-E-1 通過；14-2 交叉參照錯（F-10）；14-8 界值不全（F-06） |
| 15 | 15-1、15-2、15-3、15-5 | 通過（15-3 自算法 101＋6＝107、115＋9＝124 我獨立核算相符；暫名字樣見 F-08） |
| 16 | 16-1、16-3、16-E-1（負控） | 通過（十三鍵不變、值取真） |
| 17 | 17-1、17-6、17-E-1（負控） | 通過（確認名完全相等含零寬字元） |
| 18 | 18-1、18-4、18-E-1（負控） | 通過（18-E-1 的 200 毫秒標「未校準」並入證據，可接受） |
| 19 | 19-1、19-2、19-3、19-4、19-5、19-6、19-E-1 | 19-3、19-6 判定不可跑到斷言（F-05）；19-2 檔案為新檔須註明；19-1、19-4、19-5、19-E-1 通過 |
| 20 | 20-1、20-4、20-E-1（負控） | 通過（三態 `pending_correction` 見 F-12） |
| 21 | 21-1、21-E-1（負控） | 通過（R7／R8／R10／R11／R12 口徑與 D-118 一致） |
| 22 | 22-1、22-2、22-E-2（負控） | 通過（假 gh 為夾具；22-E-2 見 F-14） |
| 23 | 23-1、23-2、23-E-1（負控） | 通過（指令核對型；`<基準>` 取自 RTM-P1 檔頭） |
| 24 | 24-1 | 不通過（F-07） |
| 25 | 25-1、25-2、25-3、25-4、25-E-1（負控） | 通過（D-125 三段機制皆有 AT；`stage2Frozen` 只由 `frozen_stages` 導出；校正冪等與未凍結負控齊） |

另機械掃描全部 204 個 AT：每個都有 Given／When／Then／判定四行（缺 0）；Then 含「正確顯示、正常運作、適當、合理」等不可判字眼的 AT 為 0；判定載具分佈 pytest 119、gradlew 48、vitest 32、指令核對 5。

## E 硬釘重掃表（我以 Grep 現查；對照 TCS §4 與 `_aux\HARDPIN_SCAN.txt`）

| 釘住的事實 | 現值（我的現查座標） | TCS 是否列入 | 判定 |
|---|---|---|---|
| 六處 Flyway 版本清單 | `SchemaMigrationIT:69`、`V5UpgradeMigrationIT:136`、`IssuePriorityMigrationIT:131`、`BackupJobMigrationIT:168`、`SiConsoleWritesMigrationIT:129`、`ResearchSchemaMigrationIT:490,493`（皆到 "18"） | 是（§4.1 第 1 列） | 相符 |
| Bridge 夾具版本 | `research_pg_support.py` `LAST_VERSION`＝18 | 是 | 相符 |
| ResearchSchemaMigrationIT 的表集合與守衛集合 | `:495`、`:518`、`:1385-1389` | 否 | 漏列＝F-01 |
| `OpenApiIT` | `:163`＝101、`:164`＝115 | 是（第 3 列；自算 107／124） | 相符 |
| `ResearchReasonsTest` | `:112` `hasSize(22)` | 是（第 4 列） | 相符 |
| `RbacIT` 清單與 `:486-495` 探針 | 探針以空本文打 ADMIN 路徑，P1 後回 400 仍非 401／403 | 是（第 5 列） | 探針相符；規則清單 `:452-463` 漏列＝F-03 |
| `SecurityConfig` | `:103-110` 八條研究規則，`route` 已預置 | 是（第 6 列） | 相符（但連動 F-03） |
| `BackupJobMigrationIT` 排除條件 | `:85`（欄位查詢排除 `backup_jobs` 與 `research_` 起頭）；視圖 `v_research_healing_attempts` 不以 `research_` 起頭 | 是（第 2 列） | 相符 |
| `test_sdd_cli.py` 動詞表與 `HUMAN_PENDING` 前綴 | `sdd_cli.py:358-366,478-482`；測試 `:495-499` 只用 `baseline adoption` | 是（第 18 列） | 相符（`INNER_FREEZE_STAGES={"Stage-1"}` 已排除內環 Stage-2，與 D-125 一致） |
| `CAPABILITY`／`EXEC_MODULES` | `test_research_capability.py:43,295`、`test_research_ast_locks.py:30` | 是（第 13、14 列） | 相符 |
| AST 鎖 C2（`spec_frozen` 呼叫點） | `test_research_ast_locks.py:131-136`、`:257` | 否 | 漏列＝F-04 |
| 游標 UPDATE 只在 `research/` 且同函式有 `append_event` | `test_research_ast_locks.py:352-373` | 否（校正走既有 `set_cursor`，推論不破） | 通過（BR-D2 實作須沿用 `db.set_cursor`） |
| `endpoints.test.ts:288`＝109 與元鎖 `si.endpoints.test.ts:46` | 現查相符 | 是（第 24 列） | 相符 |
| `HELP_PAGES`／`HELP_ROUTES`／`StateTableId`／`registry.test.ts` | P1 無新路由與導覽列 | 是（第 30 列） | 相符 |
| `stateKeys.test.ts:100` 的 `researchFlow` 鍵＝兩常數鍵 | `FLOW_STATUS_LABEL`＋`FLOW_PHASE_LABEL` | 是（第 27 列） | 相符 |
| `schema.d.ts` 重產、真棧 spec | FE-W 單棒 | 是 | 相符 |
| 守門（passed／skipped＋四位數字同行） | TCS、RTM 皆 0 站點（以 `tools/check_pytest_baseline_sites.py` 的關鍵字與數字式樣自跑） | — | 通過 |

## F 誠實劃界

- 全程唯讀：只讀 repo 與 scratchpad，未改任何檔（除本報告、`qa\progress_qa.md` 與我在 `S\qa\` 下的小腳本 `cov.py`、`ats.py`、`show.py`、`z.py`、`chk2.py`、`mkC.py`、`ats.json`、`_C.txt`）；未跑任何 gradle、vitest、pytest（所以 F-05 的「rc 0」是對 vitest 行為的推論，標推論）。
- 自檢腳本 `_aux\selfcheck.py` 實跑一次：`checks=49 fail=0`、rc=0；但它只證明結構（編號、計數、文法、撞號、有無 AT），不證明 §4 的連動是否完整，這正是 F-01、F-03、F-04 漏掉的面。
- AT 抽查為七十六個（全部二百零四個的三成七）；其餘 AT 我只做了結構機械掃描（四行齊全、不可判字眼 0、載具分佈），沒有逐個讀 Given／When／Then，可能還有同型缺陷。
- 硬釘重掃的方法是「讀現行 IT 與鎖的原始碼找出對 V19、SCR 規則、採納呼叫點敏感的斷言」，不是跑測試；沒有掃到的類型：Docker／nginx／compose 側、`.github` 的 paths 覆蓋（TCS 把它歸主控收尾，未審）。
- 對 D-94～D-125 的一致性只對「TCS 內有無落點與是否矛盾」做了字串與抽樣核對，沒有重做 ARCH 定稿與 PRD 的全面對拍；D-118～D-125 的八條皆找到落點（D-118 的 ⚖ 列無殘留「待裁決」，但 ⚖P1-24 文字未跟上定案，見 F-08；D-119、D-120、D-121、D-122、D-123、D-124、D-125 各有 AT 或 ⚖ 列）。
- F-05 的嚴重度判定依「AT 無法轉紅＝不可執行」；若主控要求在凍結前不驗證 vitest 行為，可先以 F-05 改判定欄為不帶 `-t` 的整檔執行，成本最小。



