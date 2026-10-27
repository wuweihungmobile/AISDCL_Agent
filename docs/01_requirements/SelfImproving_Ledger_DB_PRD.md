# 自我進化帳本廢除：改由 DB＋議題中心承載（SelfImproving Ledger → PostgreSQL）需求規格 v0.3（計畫型）

**狀態**：Draft v0.3（SA 依獨立審查一審〔P2×7、P3×12、P4×1〕、二審〔P2×1、P3×6、P4×4〕就地修訂，待主控審閱與 SCG-0；未凍結）。**性質**：計畫型 PRD——上位規格，拆 P0～P4（P3 分 P3a／P3b）六段，每段各開 SDD 鍵、TCS 與出口。**範圍**：自我進化三類帳本（§3.1）；**五問輪帳本與 `skip_id_ledger.json` 另案**（§3.2、OQ-5）。
**立案**：掌舵者 2026-10-27，原話「請全力消除所有帳本！」；主控說明架構級風險後，掌舵者選定「**廢除帳本機制，改由 DB＋議題中心承載**」（座標 SA 無從查證，見 D-1）。10-26 同一句話已被執行為「open 觀察列歸零」（commit `93276120`、`1c1f2b4e`），本次改選更強的讀法：**不再以檔案當帳本**。衝突列於 §3.3；數字皆 HEAD `c92f8bed`（2026-10-27）實測（與任務書差異：缺陷主檔 271 列〔任務書 266〕、議題總數 605〔604〕），指令與輸出見附錄 C（`[C-n]`），凍結日須重算。

---

## 1. 目標與範圍

> 把自我進化三類帳本的**真相源**，由 git 內的 Markdown／JSONL 檔改為 Docker PostgreSQL 18 的 `si` schema；根層 CLI 仍是唯一寫入者、議題中心是唯一人機介面；切換後舊檔凍結。

**成功的樣子（症狀型）**：(1) 掌舵者不必開任何帳本檔，看議題中心、按按鈕就夠；(2) 議題中心件數與切換前一致（以凍結日 `si issues --json` 的 `summary.total` 為準，撰寫時 605＝OBS 332＋DEF 271＋PROP 2 `[C-3]`）；(3) 資料庫停了，畫面與指令明說原因，絕不顯示「0 件」、也不悄悄讀舊檔；(4) 任一階段可退回上一階段，不丟任何資料列；(5) 「誰、何時、把什麼改成什麼」在 DB 查得到，非超級權限者事後竄改會紅（FR-LD-05、§6）。

**名詞**：**真相源**＝讀寫都以它為準的那一份（今天＝git 內的檔，P3b 起＝DB）；**影子**＝檔案仍是真相、DB 由匯入器依檔重建並對帳（P1～P3a）；**讀模型**＝Python 算好、存進 DB 供 console-api 唯讀的值；**快照**＝同格式匯出檔，**凍結檔**＝切換後不再寫入的舊檔；**Store**＝根層 CLI 的儲存層介面（Mem、File、Pg 後端）。

## 2. 使用者與場景（掌舵者視角）

| 場景 | 今天 | 切換後 |
|---|---|---|
| 看現況 | 開議題中心（Bridge 起子行程讀檔）；細查要開 332 列、178KB 的 Markdown 表 | 開議題中心（console-api 直讀 DB）；不需開檔 |
| 記一件事（觀察、缺陷） | 主控 Edit 手寫 Markdown 列（每列 ≤700 bytes、自己查號、commit）；缺陷、結構債列沒有 CLI 動詞；`obs-add`／`obs-close` 只收 Console 載體 | P3b 起用 CLI 動詞：`obs-add`／`obs-close`（新增 `--carrier operator`，**擴大寫入面、待掌舵者核准，OQ-3**）、新動詞 `def-add`／`def-update`／`debt-add`／`debt-update`；系統配號、當下入帳 |
| 在 Console 按「決定」 | 簽章→Bridge 落稽核檔→主機 CLI 入帳 | 簽章→寫 Console 稽核表→主機 CLI 自表驗簽入帳；資格與 K=1 不變 |
| 查「誰何時改了什麼」 | `git log -p`（commit 粒度） | `si.audit` 逐筆（含改前改後的值）＋雜湊鏈，`si check` 驗鏈與狀態重放 |
| 換機器／重灌 | `git clone` 即得全部帳本 | 需還原 DB（備份或快照匯入）——**本計畫最大代價**，見 R-1、R-2、OQ-1、OQ-2 |

## 3. 範圍與不做什麼

**3.1 納入**（三類；逐本欄位與讀寫者見附錄 A）：①觀察帳本（含附註檔：15 行、3 列以 `orig=@…` 參照）②缺陷帳本家族（主檔＋68 個歸檔檔、外部阻塞軌、結構債軌）③事件帳本與提案內容檔（`rN.md`／`rN.patch`／`verifyK.json`）。**只遷資料列**；非列文字見 §3.4。

**3.2 不納入**（OQ-5 請掌舵者確認）：**五問輪帳本** `FiveQuestion_Round_Ledger.jsonl`（16 筆、38,974 B）——綁協定雜湊與跨機輪次，以 git 為跨機同步；**`skip_id_ledger.json`**（四個鍵、23,705 B）——每台機器、每次 CI 都要讀（`skip_group_policy.py:1237`），依賴 DB 會打破「無 PG 也能跑」；**協定設定檔**（`params.json`、`research_sources.json`、`metrics.md`）；**引擎執行期 ledger**（SDD 各版 `*_ledger`、AutoClaude `pg_goal_progress_ledger.py`、`tools/lib/quota_ledger.py`）。

**3.3 與既有規格的衝突（Rule 7：浮出、不平均；本檔不改它們，由主控另案勘誤，為 P0 出口）**：

| # | 衝突點 | 座標 | 處置（時點） |
|---|---|---|---|
| 1 | 儲存原則「入 git…單一真相＝git」「不用 PG」、ADR-SI-01（觀察儲存選 git）；ADR-SI-02（載體 JSONL＋PROP 內容檔）；ADR-SI-10（事件檔案鎖）；ADR-SI-12（Console 讀模型選 Bridge 子行程；PG 讀模型「第二個真相源」；Bridge 不開帳本檔、不 import `tools/lib`，AST 鎖） | `docs/01_requirements/SelfImproving_PRD.md:791,793`、`:987-988`、`:997`、`:999`、`:811` | 勘誤改述為 §9.2 模式矩陣；ADR-SIDB-01、-04（P2）、-05（P3a）取代；P3b 起 JSONL／內容檔降為匯出格式；Bridge 仍只經 CLI 子行程取數（AC-LD-08-4） |
| 2 | ADR-SI-03′ Console 載體＝稽核檔、`audit_sha256`＝稽核檔位元組 sha256；已否決選項 E（CLI 讀 PG） | `:990`、`:792` | P3a：載荷落 DB 並**保存原始位元組**（FR-LD-09）；E 的「第二真相」因 DB 成唯一真相而失效，「第三方驅動」見第 5 列 |
| 3 | 「本 PRD 不新增非 Console 的 `obs-add`，主控的手寫入帳照舊」；`obs-add`／`obs-close` 屬需人工動詞、`--carrier` 只收 `console` | `:491`、`:904-905`；`tools/selfimproving.py:364-365` | **衝突**：P3b 後沒有檔可手寫。P3a 新增 `--carrier operator`（**擴大 CLI 寫入面，須掌舵者核准，OQ-3**）；不核准則 P3b 不得進（§8.1 H4） |
| 4 | 議題中心「不快取：每請求重算，帳本是唯一真相源」「帳本…一個字不動」 | `Issue_Center_PRD.md:415`、`:4` | 勘誤：讀模型是寫入時刷新、帶 `ledger_head` 的衍生值，過期由 `READ-MODEL-STALE` 偵測；退路＝ADR-SIDB-04 選項 C |
| 5 | NFR-SI-02-4 外聯只在 `fetch.py`；能力登記「第三方 import 紅」「只掃套件根層」 | `SelfImproving_PRD.md:527`；`tools/tests/test_selfimproving_capability.py:85,182,195-201` | 勘誤：增列「DB 連線只在 `dal_pg_conn.py`」；能力測試明列該檔為唯一可 import `psycopg` 者（延遲 import 也被 `ast.walk` 抓到，`:139-146`），新增 `dbr`／`dbw` 類 |
| 6 | AC-SI-22-2、AC-SI-30-6：`params.json` 或協定目錄任一檔改動必改 `params.fingerprint()` | `SelfImproving_PRD.md:370`、`:422`；`tools/lib/selfimproving/params.py:15,128-141` | **以設計避開**：不新增 params 鍵、不改協定目錄任何檔（§9.2）；P4 的容量鍵留置不刪 |
| 7 | 議題中心游標：缺陷＝主檔資料列行號；`schema_rev` 維持 1 | `Issue_Center_PRD.md:204`、`:419` | D-10：P3b 游標改插入序、`schema_rev` 升 2；勘誤＋Bridge／backend／黃金檔／前端同批 |
| 8 | 根層軌道表以缺陷帳本未結列為 R 系列驅動器 | 根 `CLAUDE.md:44`、`:48` | P4（OQ-4） |
| 9 | 任務書稱 hook 治理檔禁寫面要「改指 DB 權限」 | `.claude/hooks/block_destructive_git.py:1445-1464` | **無需改**：`_GOV_EXACT` 不含任何帳本檔 `[C-8]`；不可進化保護來自 `params.json:32-34` 的 `non_evolvable_globs`；`:1459` 已列入 `test_adr_xplat001_c1c2_lock.py`，重釘只能在互動 session（§8.3） |

**3.4 保留與不做**：保留根層 `issues` 動詞當 CLI 視圖、輸出契約不變。不改任何判準語意（九欄、處置首詞、PROP 狀態機、`dec` 驗證、議題中心對照表）、K=1 人工閘、HMAC 載體、`AUTOSDD_UNATTENDED` 語意；不新增守衛碼（`.claude/**`、settings、守衛面清單、`session_brief.py` 不動；凍結檔也不加入 `_GOV_EXACT`）；不做 SQLite（D-4）、DB 編輯 UI；不動 `params.json` 與協定目錄（AC-LD-02-6）。**舊檔位元組不變**：凍結宣告與逐檔雜湊住新檔 `docs/05_development/SelfImproving_Frozen_Manifest.md`（§9.2），唯一例外＝`si db unflip` 的顯式回退 commit（AC-LD-10-3）。**非列文字不進 DB**：觀察帳本表頭說明、結構債軌〈複查記錄〉、歸檔 `_INDEX.md`（79,098 B）隨凍結檔留在 git；複查改由 `debt-update --reviewed`＋`si.audit` 承載，`_INDEX.md` 隨歸檔輪替於 P4 退役。

**SA 加碼（可刪，非原話所必要）**：三角色（§9.3）、彩排（§8 P3a）、快照入 git 與專屬容器變體 B′（OQ-1、ADR-SIDB-01）、Console 資料來源提示（§7，只在異常態顯示）；不做 `si db provision`（SOP 附 psql 範本）。

## 4. 現況盤點（摘要；細節見附錄 A；數字 `[C-n]`）

| 帳本（`docs/06_quality/`） | 規模 | 寫入者 | 去向 |
|---|---|---|---|
| `SelfImproving_Observation_Ledger.md` | 332 列、178,372 B；列長最大 699 B、93 列 >600 B `[C-5]` | 主控手編（無動詞）；`obs-add`／`obs-close` 只收 Console 載體 | → `si.observations` |
| `AutoSDD_Defect_Log.md`（主檔） | 271 列、202,277 B；證據欄最長 806 B、狀態欄最長 1,117 B；族 01／100／101／200；最大 DEF-200-570 `[C-4]` | **只有手寫**；機器寫入者只有歸檔輪替 | → `si.defects`（`home='main'`） |
| `AutoSDD_Defect_Log_archive_01～68.md`＋`_INDEX.md` | 68 檔、1,415 列、2,348,531 B；證據欄最長 5,629 B、狀態欄最長 6,710 B；14 列欄數不符、6 組重複 ID、3 列被判 open `[C-4]` | `archive_defect_log.py`（輪替） | → `si.defects`（`home='archive_NN'`）＋`si.legacy_rows` |
| `AutoSDD_External_Blocked_Log.md`／`AutoSDD_Structural_Debt_Log.md` | 各 0 列 `[C-6]` | 手寫 | → `si.debt_tracks` |
| `SelfImproving_Event_Ledger.jsonl` | 34 事件、12,157 B、21 種 kind 中 15 種出現過 | CLI 17 個寫入動詞（`evwrite.append_event`，檔案鎖） | → `si.events`（追加專用） |
| `SelfImproving_Proposals/PROP-SI-NNN/` | 2 個 PROP、5 個檔 | `propfiles.py` | → `si.artifacts`（`bytea`） |

**規模（現查）**：SI 套件 51 檔 10,804 行、入口 412 行（24 動詞、17 個寫入）`[C-9]`；SI 測試 23 檔 24,896 行（`splitlines` 計）；缺陷帳本閘門族的測試 4 檔 8,458 行；Console 側（Bridge／backend／前端含測試）25,707 行（`[C-10]`）。**引用面**見 A.3、`[C-7]`、`[C-8]`。

**四個決定工作量的觀察**：
1. **讀取介面窄**：`LEDGER_REL`／`PROPOSALS_REL` 在 `tools/` 的 `*.py` 共 65 處／28 檔——SI 套件 20 檔 45 處、入口 2、量測探針 `tools/probe/selfimproving_measure.py:48` 1、測試 6 檔 17 `[C-7b]`；載入呼叫在 SI 套件 22 檔 57 處。Store 縫可行，不必重寫判準。
2. **寫入面一部分是手寫**：事件走 `evwrite.py:97-136`（鎖→讀末行→配號→追加）；`obs-add`／`obs-close` 只收 Console 載體（`tools/selfimproving.py:359-373`）；**缺陷、結構債列沒有任何動詞**，新增觀察、處置、更正全靠手寫——切換前必須先有動詞（P3a），否則人會繼續手改凍結檔。
3. **多數綁定是「檔案形態」不是「資料語意」**：容量閘（`check_defect_log_crossref.py:1152-1153`、`params.json:7-8`）、歸檔輪替、700 B 列長、git 歷史比對。DB 化後可退役（P4 候選、逐支審：歸檔輪替族 6 檔 3,118 行〔`archive_defect_log.py` 1,507、`lib/defect_ledger_index.py` 823、`lib/ledger_rotation.py` 488、`check_archive_required.py` 195、`archive_apply_locked.py` 67、`lib/ledger_staleness.py` 38〕及其測試 4,228 行〔`test_archive_defect_log.py` 4,068＋`test_check_archive_required.py` 160〕；`check_defect_log_crossref.py`、`check_handoff_carriers.py` 保留並改讀 `export`；`lib/ledger_closing_guards.py` 改義〔AC-LD-13-2〕）；代價有帳為證——`docs/04_planning/R124_Row_Slimming_Plan.md:1-24`。
4. **內容閘也藏在單元測試裡**：至少 10 支根層測試與 2 支 AutoClaude 測試讀**真實**帳本內容（附錄 A.4）；P3b 後新缺陷只在 DB，不先處置會對「引用新 DEF 的 commit」或「無 PG 的 CI」變紅（AC-LD-13-5）。

## 5. 功能需求（FR 與 AC）

一條 AC 一列、Given／When／Then；「差分」＝同輸入、兩後端（或兩路徑）輸出逐值相等。AC 編號 `AC-LD-<FR>-<n>`。

| AC | 內容 |
|---|---|
| **FR-LD-01** | **資料庫契約：schema、遷移、角色、憑證** |
| `AC-LD-01-1` | Given 空的 PG18 與擁有者 DSN When `si db migrate` Then 建出 `si` schema 與 §9.3 全部表並記每版 SQL 檔 sha256；再跑一次 rc 0 且零變更 |
| `AC-LD-01-2` | Given 已套用版本的 SQL 檔被改一位元組 When `db migrate`／`db status` Then `MIGRATION-CHECKSUM`、不套用後續版本；庫版本低於程式要求＝`SCHEMA-BEHIND`、rc≠0 並指路 `si db migrate` |
| `AC-LD-01-3` | Given 唯讀角色 DSN When 對任一 `si.*` 表寫入 Then permission denied；寫入角色對 `events`、`audit`、`artifacts`、`legacy_rows` 的 UPDATE／DELETE 被觸發器拒絕，且寫入角色非表擁有者、不能停用觸發器（負控：`ALTER TABLE … DISABLE TRIGGER` 被拒） |
| `AC-LD-01-4` | Given 以哨兵字串當密碼的 DSN When 任一動詞以任何結果結束 Then stdout、stderr、`si.audit` 各欄、日誌皆不含該字串；tracked 檔無 DSN／密碼字面（`<YOUR_…>` 除外） |
| **FR-LD-02** | **儲存層（Store）與模式解析** |
| `AC-LD-02-1` | Given 同一契約基類與同一組種子 When 對 MemStore、FileStore（`tools/tests`）、PgStore（`tools/tests_pg`，有 `SI_TEST_PG_DSN` 才跑）各跑一次 Then 讀回的觀察列、缺陷列、事件、提案內容逐值相同，三處斷言數相等 |
| `AC-LD-02-2` | Given 啟動任一動詞 When 解析模式 Then 依序：①程式碼常數 `LEDGER_TRUTH`（預設 `file`，只在 P3b 切換 commit 改 `db`）②`SI_DB_DSN` 有設**且 `--repo` 即 CLI 自身所在的 checkout 根**，才把 `file` 升為 `shadow`（暫存夾具 repo 不升）③`SI_LEDGER_STORE`（僅測試與彩排；`--repo` 非 checkout 根時靜默生效，否則 stderr 橫幅）；**不讀 `params.json`**；`db` 而 DSN 缺或連不上＝rc≠0 且**不讀任何帳本檔**（負控：改凍結檔內容，輸出不變）；夾具 `SiTestCase.setUp`（`_selfimproving_fixtures.py:1206-1215` 的 `mock.patch.dict(os.environ…)`＋`_STRIP :36`，現成的環境隔離點；`:110` 的 `setup` 只建暫存目錄、不碰環境；TCS 核實每支跑 CLI 的 SI 測試皆經此 patch 或等價物，含唯一不呼叫 `setup` 的 `test_selfimproving_issuemap.py`）自 P1 起清 `SI_DB_DSN`、設 `SI_LEDGER_STORE=file`，開發機有 DSN 也不寫真影子庫 |
| `AC-LD-02-3` | Given 解析模式與庫內 `si.meta.truth` 不一致（覆寫 `db` 而庫為 `file`；覆寫 `file`／`shadow` 而可達的庫為 `db`；舊分支 `LEDGER_TRUTH=file` 寫 `truth=db` 的庫）When 任一寫入動詞 Then `MODE-MISMATCH`、零寫入、記 `si.audit`（`op='reject'`）；DSN 缺的 `file` 覆寫屬測試用法（凍結檔被改由 `si db frozen --check` 擋） |
| `AC-LD-02-4` | Given 唯讀動詞（`check`、`status`、`scan`、`card`、`export`、`issues`、`capacity`、`obs-add --dry-run`）When 執行 Then import 閉包 ⊆ `ro`∪`dbr`、DB 連線用唯讀交易（負控：INSERT 被 PG 拒）；能力登記新增 `dbr`、`dbw` 並有紅綠自證 |
| `AC-LD-02-5` | Given P2 出口 When Grep `LEDGER_REL`、`PROPOSALS_REL` Then 非測試碼只在 `dal_file_*`、匯入器、快照匯出與凍結檢查（其餘皆已改走 Store）；測試碼 17 處依附錄 A.4 |
| `AC-LD-02-6` | Given P1～P4 每個出口 When 比對 Then `SelfImproving_Protocol/` 全目錄位元組與 P0 基準相同、`params.fingerprint()` 等於 P0 基準（含 `CHECK_RULES_REV`＝4，`params.py:13,139`）；**file 模式 `si check` 位元組同 P0（items=33）**——P1 起新增項只在 `shadow`／`db` 輸出（`db` 規則集另設版本常數、不進指紋），`items=33` 與 `CHECK_RULES_REV` 的既有釘（`[C-20]`）因此原樣成立；負控：暫改 `params.json` 任一鍵使指紋變動，還原後相等 |
| **FR-LD-03** | **匯入與對帳（`si ledger-sync`；P1）** |
| `AC-LD-03-1` | Given 現行檔案帳本 When `si ledger-sync` Then 每本「檔內實體資料列數＝DB 正規表列數＋`legacy_rows` 列數」恆等式成立（缺陷：主檔 271＋歸檔 1,415＝1,686；凍結日重算），報告逐帳本列三數與差；差≠0＝rc 1 |
| `AC-LD-03-2` | Given 匯入的每一列 When 驗 Then `raw_line` 位元組等於檔內該行、`row_sha256` 等於正規化欄位雜湊（全部列、不抽樣）；連跑兩次，第二次 inserted=0、updated=0、`si.audit` 不增列 |
| `AC-LD-03-3` | Given 已知髒資料（14 列欄數不符、6 組重複 ID、3 列判 open）When 匯入 Then 原樣保存（`legacy_rows` 碼 `ARITY`／`DUP-ID` 或正規表）、不修正不丟棄；議題中心口徑（不讀歸檔）件數不變 |
| `AC-LD-03-4` | Given 檔內某 OBS 列於 DB 已存在、除處置欄 `open`→終值外另有欄位不同 When 匯入 Then `CONFLICT`（rc 1）不套用；僅處置 `open`→終值為合法更新並寫 `si.audit`；DEF 狀態、證據欄變動為例行更新，同樣寫 `si.audit`（含改前改後完整列影像） |
| `AC-LD-03-5` | Given 事件帳本與提案檔 When 匯入 Then `seq` 原值保留；既有事件被改寫＝`CONFLICT`、DB 多於檔＝`DB-AHEAD`（資訊）；`si.artifacts.content` 的 sha256 等於檔案 sha256，`prop` 事件的 `patch_sha256`、`body_sha256` 重算相符 |
| **FR-LD-04** | **影子寫與一致性檢查（P1）** |
| `AC-LD-04-1` | Given `shadow` 且 DB 可用 When 寫入動詞成功落檔 Then 同一次呼叫內增量同步；`si check`（`shadow`）新項 `db.consistency` PASS（每列 digest 相等） |
| `AC-LD-04-2` | Given `shadow` 且 DB 不可用 When 寫入動詞 Then 照常成功（檔案為真相）、stderr 印 `SHADOW-SYNC-FAILED`、rc 不變；`db.consistency` 回 NE，**不得印成 PASS**；`SI_SHADOW_STRICT=1` 改為 rc≠0 |
| `AC-LD-04-3` | Given 帳本檔被手改而未同步 When `si check`（`shadow`）Then `db.consistency` 報 `DRIFT` 與列 ID 清單；`ledger-sync` 後轉 PASS；`git commit` 時 pre-commit（非守衛面）觸發 `ledger-sync`（best-effort：DB 不可用只出聲不擋；`SI_SHADOW_STRICT=1` 時擋） |
| **FR-LD-05** | **列規則、追加專用、完整性（取代 git 的完整性保證）** |
| `AC-LD-05-1` | Given 結構性規則（分類 5 值、嚴重度 4 值、處置首詞 8 種、事件 kind 21 種、ID 形態、事件行長）When 以 SQL 插入違規列 Then PG CHECK 拒絕，且 DB 枚舉與 Python 常數雙向相等；語意性規則（座標九形態、標記值域、`fixed@` 可解析、DEF 引用存在、PROP 狀態轉移）與 `si check` 用同一份函式，同批壞列在 file／db 兩模式 findings 逐筆相同 |
| `AC-LD-05-2` | Given `si.events`、`audit`、`artifacts`、`legacy_rows` When 任何角色 UPDATE／DELETE Then 觸發器拒絕（`integrity_constraint_violation`，沿 `V13__si_console_writes.sql:28-51`）；`si.observations` 只准處置欄 `open`→終值一次 |
| `AC-LD-05-3` | Given `si.audit` When 驗 Then `row_hash＝sha256(prev_hash ‖ canonical(整列))`（含 seq、txid、at、actor、tbl、row_id、op、before、after、reason）；可變表存改前改後**完整列影像**、追加專用表存 `after_sha`；PG 內 `audit_chain_guard` 只驗 `seq` 連續、`prev_hash` 銜接與 `txid`、**不重算 `row_hash`**（canonical JSON 只由 Python 定義）；`si check` 新項 `chain.intact` 全鏈重算相等；超級使用者竄改任一歷史列後轉紅並指出最早不符 `seq`（劃界：超級權限者可整鏈重寫，偵測靠錨點，OQ-1） |
| `AC-LD-05-4` | Given 任一 `si` 資料表（`audit` 本身與讀模型除外）When 以 psql 直接 INSERT／UPDATE（不經動詞、無同交易 audit 列）Then COMMIT 失敗：延遲約束觸發器要求同交易（`txid`）有同 `tbl`、`row_id` 的 audit 列，其 `after_sha` 對可變表須等於 `NEW.row_sha256`、對追加專用表須等於 PG 核心 `sha256()` 重算值 `[C-19]`（負控：同一變更經動詞成功）；首次遷移的自舉順序（`audit` 與觸發器先於任何受約束表的首筆寫入；`schema_migrations`／`meta`／`import_runs` 的例外）由 TCS 逐表列明 |
| `AC-LD-05-5` | Given 以超級權限停用觸發器竄改某資料表的列或讀模型 When `si check`（`shadow`／`db`）Then 新項 `state.replay` 紅並指出（`tbl`、`row_id`）：每張資料表的每一列皆有 audit（追加專用表恰一筆 INSERT；缺＝旁路寫入）、可變列正規化雜湊＝`row_sha256`＝最新 audit 的 `after_sha`、並可由 audit 影像逐 `seq` 重放出現值；新項 `readmodel.fresh` 重算讀模型並逐值比對；負控另含「改 audit 影像」→`chain.intact` 紅 |
| `AC-LD-05-6` | Given 任一寫入動詞 When 交易中途失敗（注入）或 N≥8 行程×M 筆併發 `obs-add`／事件追加 Then 失敗時領域表、audit、讀模型全回滾、零殘列；號碼（OBS、DEF、`audit.seq`）一律於 advisory lock 內取 `max+1`（不用 identity／sequence），回滾不留洞、併發下無重複無缺漏、`seq` 連續、鏈無分叉（確定性交錯＋壓力兩種負控，沿 ADR-SI-10） |
| **FR-LD-06** | **寫入路徑：單一寫入者與新動詞（P3a）** |
| `AC-LD-06-1` | Given `db` 模式 When 任一寫入動詞（現 17 個，另 `card --issue`）Then 只寫 DB、不寫帳本檔、不取檔案鎖；`git status --porcelain -- docs/06_quality/` 對帳本檔零變更 |
| `AC-LD-06-2` | Given 表下〈手寫能力對照〉When 逐列比對 Then 每項皆有動詞且**不擴大**能力（不能改既有 DEF 的 ID、不能刪列、觀察處置只能 `open`→終值一次）；`--carrier operator` 不帶 `audit_ref`、不寫 `obs.*` 事件、列標記同今天手寫列（出處記 `si.audit.actor`）；更新類必帶 `--reason`；新動詞於 `file`／`shadow` 模式 rc 3 並指路「手改檔案如今天」（D-15） |
| `AC-LD-06-3` | Given DEF 編號規則 When `def-add` Then 取家族 200 下一號（＝帳本現最大號 +1；撰寫時最大號 DEF-200-570，本檔不寫未登記的編號——`test_defect_id_reference_integrity` 會紅）、滿 998 開下一族、不落入保留帶 102～199 與 999（`AutoSDD_Defect_Log.md:11-30`） |
| `AC-LD-06-4` | Given `AUTOSDD_UNATTENDED` 有設 When 各動詞 Then 以「今天主控手寫在該姿態下的實際行為」為判準（`_GOV_EXACT` 不含帳本檔、手寫不被擋 `[C-8]`）逐動詞釘於 TCS「動詞×姿態」表：`def-*`、`debt-*`、`--carrier operator` 與手寫同級；Console 載體動詞與既有九個需人工動詞維持 rc 1；新增 `db flip`、`db unflip`、`db import` 為需人工 |
| `AC-LD-06-5` | Given 能力登記 When 掃 `tools/lib/selfimproving/*.py`（只掃本層、非遞迴，`test_selfimproving_capability.py:182`）Then 每個新 `dal_*.py` 皆登記；`ro` 檔不相對 import 非 `ro` 檔（`:216-219`）；`psycopg` 只在 `dal_pg_conn.py`（明列例外，`:195-201`）；DAL 無 `time.sleep`／`while True` 等禁字樣（`:91-106`；取鎖逾時用 DB 端 `lock_timeout`） |
| **FR-LD-07** | **讀取路徑與 fail-loud** |
| `AC-LD-07-1` | Given `db` 模式（或 `--source db`）且 DB 不可達 When 任一讀取動詞 Then rc≠0、stderr 一行 `si-db-unavailable: <cause>`，stdout 無成功樣貌的「0 件」（連線逾時預設 3 秒）；寫入動詞＝rc 1 `DB-UNAVAILABLE`、零寫入並印可貼入的 OBS 草稿列；本機 pre-push 的內容類閘門印 NE 與一行紅字、不擋 push（D-17）、絕不印成通過 |
| `AC-LD-07-2` | Given DB 不可達或過慢 When SessionStart 簡報呼叫 `si_status_line` Then `status` 取 DB 連線逾時 ≤0.4 s、查詢 ≤0.3 s，超時收成「量不到（…）」、不拋出、不擋 SessionStart；DB 可達時 `si_status_line` 實測 p95 ≤0.5 s（n=20；根 `CLAUDE.md:79` 預算）。`session_brief.py:599-649` 不改——逾時值由 `status.py` 取 Store 時自帶 |
| **FR-LD-08** | **讀模型與 Console 直讀（P2）** |
| `AC-LD-08-1` | Given 同步或寫入完成 When 比對 Then `si.issues`、`si.export_items`、`si.export_meta` 與同時刻 `si issues --json`、`si export --json` 對應值逐值相同（排除 `generated_at`，`issues.py:253`；沿 `si_golden` A／B 兩態黃金檔） |
| `AC-LD-08-2` | Given `console.si.read-source=db` When 呼叫 `GET /api/v1/issues`、`/issues/{id}`、`/api/v1/si/*` Then 假 Bridge 零請求，回應與 `=bridge` 時逐值相同（含 `legend`、`summary`、`problems`、`ne`、`nextSince`、`truncated`） |
| `AC-LD-08-3` | Given `si.audit` 鏈頭大於讀模型的 `ledger_head` When console-api 回應 Then `ne` 含 `READ-MODEL-STALE`，前端明說「資料比帳本舊」 |
| `AC-LD-08-4` | Given 影子期帳本檔在最後一次 `ledger-sync` 後被手改 When Console 讀 DB Then console-api 比對 DB 的 `si.meta.synced_digest` 與 Bridge 經既有 CLI 子行程取得的 `export --kind ledger-digest`（唯讀、不連 DB；檔案集合與摘要函式同 `ledger-sync`；新 kind 入 `si_cli.py:54` 的 `SI_KINDS` 並新增逐 kind GET 路由（`routers/si.py:82-123` 現為逐 kind 路由；`tests/test_si_readonly_lock.py` 路由釘同步）；Bridge 不開帳本檔，ADR-SI-12 的 AST 鎖不動；Bridge 不可達時略過、不影響讀取；比對結果以 TTL ≥30 s 快取、逾期後非同步刷新不阻塞請求，AC-LD-08-5 的 p95 比較不含此呼叫），使 `ne` 含 `FILE-DRIFT`，前端以**資訊級**呈現（影子期手改是常態；`ledger-sync` 後消失；負控：改一位元組→出現）。今天 Bridge 每次讀工作樹現況（`si_cli.py:84-96`），本 AC 是 P2 不比今天更盲的條件 |
| `AC-LD-08-5` | Given 真資料（605 件）When `GET /issues?status=待處理&limit=500` 同機同請求各 50 次 Then `read-source=db` p95 ≤ `=bridge` p95（絕對值於 TCS 實測校準）；`si export --kind issues` 單次 ≤2 s（沿 `Issue_Center_PRD.md:416`） |
| `AC-LD-08-6` | Given console-api 的 `si` 讀取 When 檢查 Then 只經一個 adapter、只有 SELECT（ArchUnit），連線角色為唯讀角色；DB 不可達時端點回 503 `si_unavailable`（cause＝`db_unreachable`），前端顯示原因、摘要列「—」，絕不顯示 0 件 |
| **FR-LD-09** | **Console 寫入載體落 DB（P3a）** |
| `AC-LD-09-1` | Given 決定／新增觀察／關閉觀察 When 簽章 Then 載荷落點由旗標 `console.si.write-carrier` 決定：`file`（現況：Bridge 落稽核檔，V13 表照寫）、`dual`（兩者並存，表列含原始位元組欄）、`db`（只寫表列，Bridge 不再落檔）；預設 `file`；主機 `decide`／`obs-add`／`obs-close --carrier console --audit-ref` 在 `dual`／`db` 自表驗簽入帳；同一 `audit_ref` 跨載體只入帳一次；**回退＝旗標改回前一值**；切換前 `console_pending`（`si status`）必為 0，否則拒切 |
| `AC-LD-09-2` | Given 載荷外層 JSON 原始位元組 When 入帳 Then `audit_sha256＝sha256(原始位元組)`（語意同今天），位元組存 `console.si_console_writes` 新增欄 `raw`（Flyway 新版本）或 `si.console_requests.raw`；歷史稽核檔（repo 內 0 檔、帶 `audit_sha256` 的事件 4 筆、`carrier=console` 的 OBS 列 2 列 `[C-14]`）由 `si db import --audit-dir <AUTOSDD_SI_DIR>/console_audit` 匯入 `si.console_audit_files`；雜湊相符可回查，找不到檔者維持今天的 NE |
| `AC-LD-09-3` | Given 載體≠寫入者不變式 When 檢查 Then console-api 對 `si.*` 除請求表 INSERT 外零寫入（ArchUnit＋角色權限）；Bridge 不再被任何路徑呼叫 SI 寫入端點（P4 移除） |
| `AC-LD-09-4` | Given 既有 AC-SI-33、AC-SI-35 When 在 `db` 模式重跑 Then 與載體無關者（資格、K=1、HMAC 驗簽、列規則、二次入帳拒收）逐條沿用且綠；載體綁定者（`console_audit/` 檔、檔名安全等）於 TCS 對映表標「取代」並給等價 AC；漏列任一條＝文件鎖紅 |
| **FR-LD-10** | **真相源切換、凍結與回退（P3b）** |
| `AC-LD-10-1` | Given 切換前提 When `si db flip --check` Then 逐項輸出並以 rc 表示：**M 類（機器自驗）**＝§8.1 M1～M7；**H 類（人工）**＝§8.1 H1～H5，只驗**證據檔在場且欄位完整**（指令、rc、日期、引用鏈頭或 commit），不判真偽；簽核走人工閘 `--approver`（`AUTOSDD_UNATTENDED` 下不可執行）。任一不成立不得切換 |
| `AC-LD-10-2` | Given 切換 commit When 檢查 Then 同一 commit 內：`LEDGER_TRUTH` 由 `file` 改 `db`、新檔 `docs/05_development/SelfImproving_Frozen_Manifest.md` 逐檔記 `sha256`、DB `si.meta.truth=db`；**舊帳本檔與 `params.json` 位元組不變**；其後任一凍結檔位元組變動＝`si db frozen --check` 紅（獨立檢查、非 `si check` 項，免動 items=33 與 `CHECK_RULES_REV` 的釘），pre-commit 與 CI 皆跑（不新增守衛碼）；既有 23 檔 SI 測試原樣綠（AC-LD-02-2） |
| `AC-LD-10-3` | Given 切換後已有新寫入 When `si db unflip` Then 以凍結檔為底稿、只替換／追加切換後有變動的資料列並匯出回檔案（非列文字原封不動），`LEDGER_TRUTH` 改回 `file`、manifest 標註解除；`parse(匯出)` 與 DB 逐列相等、`file` 模式 `si check` 全綠（舊檔唯一被改寫的路徑，且是顯式 commit） |
| **FR-LD-11** | **離線、CI 與測試替身** |
| `AC-LD-11-1` | Given 無 `SI_TEST_PG_DSN` 的 Windows／macOS／Linux When 跑 `tools/run_root_unittests.py` Then 全套綠、skip 摘要同 P0 基準：PG 專屬測試住 `tools/tests_pg/`（不在 runner 的 discover 根內），故**不進 M6「全世界沒跑過」判準**（`skip_runtime_report.py:311-318`；M6 只在 `start_dir` 為 `tools/tests` 時評，`run_root_unittests.py:333-336`），`skip_id_ledger.json` 落款與上限表（`skip_group_policy.py:575,622,701`）**不需變動**；Mem／File 契約測試在 `tools/tests`、不 skip |
| `AC-LD-11-2` | Given CI 新工作 `si-pg-contract`（ubuntu、`pgvector/pgvector:pg18` 服務容器，先例 `agentconsole-ci.yml:63-101`）When 跑 `tools/tests_pg` Then `SI_TEST_PG_REQUIRED=1` 時缺 DSN＝失敗而非略過；每個測試類用拋棄式資料庫；自帶收集數下限（裸 `unittest discover` 對 0 個測試回 rc=0，`root-infra-ci.yml:66`）；**多 CPU**：印 `[cpu_budget] xdist workers=N`（`tools/lib/cpu_budget.py --legs 1`，先例 `agentconsole-ci.yml:98-99`），PG 在場一律 `--dist loadgroup`；要序列須先在 workflow 註解寫 WHY 並登缺陷帳本（根 `CLAUDE.md` 多 CPU 節） |
| `AC-LD-11-3` | Given windows／macos compat CI When 檢查 Then 不加服務容器、不裝 DB 驅動；`_THIRD_PARTY_PREREQS` 與 `CiPrereqInstallLockTest`（`test_run_root_unittests.py:2800-2823`）**不動**——`si-pg-contract` 自行安裝驅動、不經該 runner；本機開發相依 `psycopg` 登 `ONBOARDING.md`／bootstrap（`[C-11]`） |
| `AC-LD-11-4` | Given P0 出口 When 檢查 Then Root_Layout §2 已先修（含 WHY）：新增「PG 專屬契約測試 `tools/tests_pg/`」「套件內 SQL 遷移資料目錄 `sql/`」兩格（根 `CLAUDE.md`〈根層模組落點〉）；並逐一核對以 `tools/tests` 為根的掃描器（Grep `tools/tests` 於 `tools/lib`、`tools/tests`），結果入 TCS，且明寫：`tools/tests_pg/*.py` **受 LOC 分級管轄**（只有名為 `tests` 的目錄豁免，`AutoClaude/tools/check_loc_budget.py:296`；落 `guardrail_cli`，單檔 ≤750 斷言行，`:279-282,318-340`），故 PG 測試拆成每檔 ≤750 的多檔，**每階段 ≤4 檔、不計入 `tools/tests` 的每階段 ≤3 檔**（該上限立論＝重釘稅，`tools/tests_pg/` 不被行數棘輪計入）；**不受**行數棘輪（只數 `tools/tests/*.py`，`test_adr_xplat001_c1c2_lock.py:554,595`）、M6、skip 政策管轄 |
| **FR-LD-12** | **快照匯出與還原** |
| `AC-LD-12-1` | Given `si db snapshot --out <dir>`（獨立於唯讀動詞 `export`：快照寫檔、閉包含 `dal_snapshot.py` `rw`，不得掛在 `CLOSURE_ONLY_RO` 登記的 `export` 下）When 對尚未被改動的匯入列 Then 該列的**資料列行**與凍結檔對應行位元組逐列相同；非列文字（標頭、說明、〈複查記錄〉）不在保證內；原生新列依規範格式渲染；另含 `audit.jsonl` 與鏈頭 |
| `AC-LD-12-2` | Given 快照目錄 When `si db import --from-snapshot` 到空庫 Then `si check` 全綠、對帳恆等式、`chain.intact`、`state.replay` 成立（鏈與影像由快照內 audit 重建並驗）；`FileStore` 可直接讀快照目錄（CI 內容閘輸入） |
| `AC-LD-12-3` | Given 離機備份 When 演練 `pg_dump -n si`（或 pgBackRest 還原）到拋棄式庫 Then `si check` 全綠；指令與 rc 入證據檔。（OQ-1 選 b 時另加快照閘：DB 可達且快照鏈頭落後、或匯出失敗〔rc≠0〕＝pre-commit 擋並印匯出指令；DB 不可達只出聲不擋；逃生口＝環境變數 `AUTOSDD_SNAPSHOT_GATE_OFF=1`，commit 前設、訊息寫明理由，不接受 `--no-verify`，比照 `AUTOSDD_NET_RATCHET_OFF`〔`ledger_closing_guards.py:42-55`〕） |
| **FR-LD-13** | **閘門、驅動器與文件連動（P3a 起、P4 收尾）** |
| `AC-LD-13-1` | Given `check_defect_log_crossref.py --unresolved-count` When `db`、`file` 兩模式 Then 輸出契約（行數、欄、warn／fail 數、判準行）逐位元相同（差分）；R 系列驅動器指令字面不變；CI 無 DB 時來源＝快照（OQ-4）。此指令口徑＝主檔狀態欄判準（`[C-6]`），與議題中心「待處理」不同，P4 改驅動器前須定案（OQ-4） |
| `AC-LD-13-2` | Given 淨額棘輪 When 改以 `si.audit` 自 HEAD 提交時刻起算新增未結與結案列 Then 與 `file` 模式同樣本判定相同；逃生口 `AUTOSDD_NET_RATCHET_OFF` 不變（`ledger_closing_guards.py:55`） |
| `AC-LD-13-3` | Given `db` 模式 When 容量類閘（`_LEDGER_*_BYTES`、歸檔強制觸發、`ledger.volume`）Then 不再作用於 DB（不產生假紅）；對凍結檔改為「體積與雜湊不得變動」 |
| `AC-LD-13-4` | Given P4 出口 When 現查引用 Then 附錄 A.3 標「改寫」的規範性清單逐檔 Grep 帳本檔名命中 0（歷史證據檔不在清單）；連動面（SelfImproving_PRD 勘誤、ADR、Architecture §7.2／§9.4〔`si.*` 所有權與 `SI_DB_DSN` 等變數〕、Root_Layout §3、根 `CLAUDE.md` 軌道表、SOP、compat-ci `paths`）同一 commit 收齊；`git diff --name-only` 不含 `.claude/**`、`settings*.json`、守衛面清單檔 |
| `AC-LD-13-5` | Given 附錄 A.4 When P0 出口 Then 每支「讀真實帳本內容」的測試皆有處置（維持／改讀 export 或快照／隨被測碼退役），並以該表的 Grep 重跑普查無遺漏；P3a 出口處置已落地，P3b 前後同一組測試皆綠（含無 PG 的 CI） |
| `AC-LD-13-6` | Given 量測探針 `tools/probe/selfimproving_measure.py:48` 與 M1～M5 的兩個 measuring 窗 When P3b 切換前後各跑 `--json` Then `success`、`info`、`fingerprint`、`ne` 逐值相同（排除 `head_sha`）；窗序與窗規則不變、不重置 |
| `AC-LD-13-7` | Given 護欄層棘輪 When P0 出口 Then 以 `repin_growth_problems()` 對各階段預估增量序列做唯讀預演，預演表入 TCS（§8.3）；需入名冊的階段與名冊上限上修量已標出 |

**手寫能力對照（AC-LD-06-2 的母表；P3a 交付，僅 `db` 模式）**：新增觀察列（含更正列＝帶 `rel` 標記的新列）／觀察處置 `open`→終值＝`obs-add`／`obs-close --carrier operator`；新增缺陷列／更新狀態欄、證據欄、歸屬 `home`＝`def-add`／`def-update`；新增／更新結構債、外部阻塞列與〈複查記錄〉＝`debt-add`／`debt-update`（含 `--reviewed`）；歸檔輪替＝不需要（`home` 是欄位值，輪替於 P4 退役，AC-LD-13-3）。

## 6. 非功能需求

- **安全**：DSN 只走 `SI_DB_DSN`＋libpq `PGPASSFILE`（不讀 `AgentConsole/.env`，D-5）；非 loopback 須 `sslmode` ≥ `require`、loopback 可 `prefer`（AutoClaude 一律強制 TLS，`factory.py:85-100`）；角色見 §9.3、無 DELETE；HMAC 金鑰不入庫；SQL 參數化（沿 `engine-bridge/app/db.py:9-10`）；任何輸出面不含密碼（AC-LD-01-4）。
- **誠實劃界**：(a) 觸發器、延遲約束、鏈與重放抓得到**非超級權限者**的事後竄改與旁路寫入；持超級權限者（或表擁有者）可停用觸發器並整鏈重寫，偵測只靠外部錨點（快照內鏈頭，OQ-1）。(b) 持 `si_writer` 憑證的 CLI 可寫出自洽的 audit——與今天「能寫 git 的人能寫帳本」同級。(c) **單份、無遠端副本**：git 今天兼任版本史、跨機同步與離機備份；切換後 DB 是唯一一份，持久性取決於備份（OQ-1、R-2）。
- **效能與可用性**：寫入動詞單次 ≤1 s（含讀模型刷新）；`ledger-sync` 全量（含 1,415 列歸檔）≤60 s（初值）；讀取見 AC-LD-07-2、08-5；fail-loud（FR-LD-07）。
- **跨平台、無障礙**：Windows（PowerShell、禁裸 `cd`）／macOS／Linux；根層庫原則純標準庫，驅動只准 `dal_pg_conn.py` 延遲 import（`psycopg` 3 已在根 `.venv` `[C-11]`）；快照 UTF-8 無 BOM、LF；時間 `timestamptz` 並保留原字串 `time_raw`；前端只新增異常態提示條（沿用既有元件，顏色之外必有文字）。
- **零侵入、可逆、相容**：不動項見 §3.4（`.claude/**`、settings、守衛面清單、`params.json`、兩引擎；不新增 hook 碼）；AgentConsole 鐵律 7（不動根層 `tools/`）→ 根層與 Console 分鍵。舊檔永不刪（P4 只退役寫入它們的程式）；`schema_rev` P2 維持 1、P3b 升 2（D-10）；Console 既有 API 形狀不變；每段回退點見 §8。

## 7. 畫面（文字線框；數字為示意、以實跑為準）

**(a) `python tools/selfimproving.py db status`**
```
mode=shadow (LEDGER_TRUTH=file, SI_DB_DSN 已設)   truth=file   schema=v003 (3/3 已套用，checksum 相符)
db=127.0.0.1:<port>/aisdlc  role=si_writer  tls=prefer(loopback)  latency=4ms
ledger_head=#1287  chain=intact(1287/1287)  replay=ok  last_sync=2026-10-27T14:40:24+08:00  drift=0
```
**(b) 議題中心頂部——只在異常態多一條「資料來源」提示；正常態版面與今天相同**
```
資料來源：資料庫 ✕ 連不上（db_unreachable：connection refused）    待處理 —・待您決定 —・已完成 —
資料來源：資料庫 ▲ 資料比帳本舊（READ-MODEL-STALE）
資料來源：資料庫 ⓘ 帳本檔在最後同步後被改過（FILE-DRIFT；資訊級，非警告）
```

## 8. 分階段計畫（每段一把 SDD 鍵；先換讀、再換寫、最後換真相）

**三條原則**：(1) 順序＝P1 影子→P2 讀→P3a 寫→P3b 切換→P4 清理，真相源只在 P3b 那一個 commit 換手；(2) **先換介面、後換儲存**：所有讀寫都經 Store 之後，切換只剩常數與凍結；(3) 鍵格式依 BRIDGE §8.0（`<sub>-<slug>`、一功能一鍵、三件組、一律從 monorepo 根啟動）；根層與 Console 分鍵（AgentConsole 鐵律 7）。

| 階段 | SDD 鍵 | 交付 | 回退點（安全停靠） | 估工；風險 |
|---|---|---|---|---|
| **P0** 規格 | `monorepo-si-ledgerdb-p0` | 本 PRD、ADR-SIDB-01～08、Architecture 草稿、§3.3 勘誤案、Root_Layout §2 修訂、A.4 普查定稿、棘輪預演 | 丟棄文件 | 5 棒／0.5 輪 |
| **P1** 影子 | `monorepo-si-ledgerdb-p1` | `si` schema 遷移、DAL（`dal_*.py`）、`db`／`ledger-sync`、`si check` 新項（`db.schema`、`db.consistency`、`chain.intact`、`state.replay`；只在 `shadow`／`db` 輸出）、`dbr`／`dbw`、`tools/tests_pg/`＋CI `si-pg-contract`；**不改既有寫入語意**（只加寫後同步鉤） | `LEDGER_TRUTH=file` 且不設 DSN＝與今天相同；DB 可丟可重建 | 10 棒／2 輪；R-5、R-6、R-8 |
| **P2** 讀 | `monorepo-si-ledgerdb-p2` ＋ `agentconsole-si-ledgerdb-p2` | 讀取動詞經 Store、讀模型、console-api 直讀（`console.si.read-source`）、`FILE-DRIFT`（Bridge 經既有 `export` 取 `ledger-digest`）、`readmodel.fresh`、前端異常態提示、差分測試 | `read-source=bridge` 一步切回。**建議長期停靠點（OQ-6）** | 11 棒／2 輪；R-3、R-7 |
| **P3a** 寫 | `monorepo-si-ledgerdb-p3a` ＋ `agentconsole-si-ledgerdb-p3a` | 寫入動詞經 Store、`def-*`／`debt-*`／`--carrier operator`（僅 `db` 模式）、Console 載體旗標與原始位元組、閘門與非 SI 消費者改讀 `export`／快照、快照匯出／匯入、生命週期隔離與離機備份演練、**彩排**（拋棄式庫走一般 flip 流程）、A.4 處置落地 | 不翻 `LEDGER_TRUTH`＝仍是影子 | 16 棒／3 輪；R-2、R-4、R-6、R-7 |
| **P3b** 切換 | `monorepo-si-ledgerdb-p3b` ＋ `agentconsole-si-ledgerdb-p3b` | 切換 commit、`si db frozen --check`、CI 內容閘模式、SOP 改寫、`schema_rev` 2、穩定期 | `si db unflip` | 5 棒／1 輪＋穩定期；R-1、R-2、R-3 |
| **P4** 清理 | `monorepo-si-ledgerdb-p4` ＋ `agentconsole-si-ledgerdb-p4` | 退役候選（逐支審）、移除 Bridge 的 SI 讀寫路由與 `si_audit.py`、引用處置、文件連動、驅動器改讀（OQ-4） | 逐 commit `git revert` | 8 棒／1.5 輪；R-3、R-6 |

**合計**：約 55 棒、10 把 SDD 鍵（根層 6＋Console 4）、約 10 輪、折合約 17～24 個工作日（**不含**額度帶與掌舵者決定的等待）。校準（皆單一連續視窗）：議題中心 `1e82dd18`→`c92f8bed` 約 12.6 小時、SelfImproving P2b＋P3 `0a358919`→`67e75d9c` 約 7 小時；P3a 面遠大於它們，TCS 後重估；棒＝一個 Sonnet 子代理工作包（含審查與修復）。

**8.1 進入 P3b 的閘（缺一不得切換；機器可驗者由 `si db flip --check` 判，AC-LD-10-1）**：**M 類**——M1 對帳恆等式（彩排庫與真庫）；M2 `si check` 全綠（含 `db.consistency`、`chain.intact`、`state.replay`、`readmodel.fresh`）；M3 `console_pending=0` 且載體旗標為 `db`；M4 快照在場且鏈頭等於 DB 鏈頭（OQ-1 選 a／b／c 時）；M5 `params.fingerprint()` 等於 P0 基準；M6 `docs/06_quality/` 無未提交的帳本編輯；M7 寫入動詞與閘門在彩排庫以 `db` 模式全綠（證據＝`si-pg-contract` 綠＋彩排報告摘要雜湊）。**H 類**（人工項，證據檔＋簽核；用 H 避免與階段 P1～P4 混淆）——H1 離機備份演練已做（AC-LD-12-2、12-3）；H2 DB 生命週期隔離（對 Console 專案做 `docker compose down -v` 後 `si` 資料仍在，或有機械式清場前快照）；H3 拓撲決議（OQ-2）與他機匯入快照演練（他機 SessionStart 的「量不到」屬預期）；H4 `--carrier operator` 決議（OQ-3）；H5 掌舵者真機簽核。**穩定期**：切換後 `si db flip --check --post`（唯讀）於期末判一次——距切換 ≥7 日曆日、期間 `si.audit` 寫入 ≥20 筆（初值）、`MODE-MISMATCH` 拒收 0 筆、`si check` 全綠、未 `unflip`；SI 套件禁排程字樣（`test_selfimproving_capability.py:91-106`），故不設常駐驗鏈。

**8.2 DB 在哪、怎麼連（今天的事實，決定 §8.1 H2）**：Console 全棧在跑，`aisdlc-pg-primary` 只有 `5432/tcp`、**未發布到主機**；主機 5432 被獨立容器 `autoclaude_pg` 占用 `[C-12]`；db-net 是 internal，主機連線須疊加 dev 檔（`127.0.0.1:${POSTGRES_PORT:-5432}`；`Architecture.md:148,167`、`docker-compose.dev.yml:9-11,27-31`），本機要改埠。**備份面**：WAL 歸檔約每 60 秒一段、每日 02:30 `pg_dump -Fc`（`docker/README.md:216-226`），但離站 repo 是本機單碟 MinIO（`:491`）——同機、不是離機；整庫還原須先停 primary（`:245-267`）、核對只數 `console` 表（`:274`），故 P1 以邏輯匯出或快照演練。`down -v` 是文件化清場手段（17 檔 41 處 `[C-13]`），`si` 與 Console 同卷則一次清場＝治理資料全失，故 ADR-SIDB-01 把「隔離」列為 P3 進場條件；P2 的 console-api 直讀要求 `si` 網路可達。

**8.3 棘輪稅預算（R-6 量化；AC-LD-13-7）**：行數棘輪數的是 **`tools/tests/*.py`（非遞迴）的測試行**（`test_adr_xplat001_c1c2_lock.py:554,595`），不是 `tools/lib` 程式碼（那歸每檔 LOC 分級，`AutoClaude/tools/check_loc_budget.py:276-283`）；重釘受三道鎖——單輪淨額上限 515（`:2872`）、連兩輪上升後第三輪須 ≤0（`:2856,2877`）、一次性例外名冊上限 6 且現有 6 列＝**已滿**（`:2888`、`:2979`，`[C-16]`；鎖檔屬 `_GOV_EXACT`，無人值守不可改，§3.3 #9）。**預算以新增／修改的測試行估**（量級、無實測；先例＝`:2957` +3,793、`:2966` +2,336，皆為新鎖檔）：P1 約 +1,500～2,500（PG 測試在 `tools/tests_pg/`，不計）；P2、P3b 各 ≤ +515；P3a 約 +1,500～3,000；**P4 淨減＝測試行 −4,228**（§4 觀察 3；棘輪不計退役的程式碼行）。**規則**：P0 以 `repin_growth_problems()` 唯讀預演、預演表入 TCS；預期入名冊者（P1、P3a）各一列：輪號仍為 R214 時以同標籤續列、不佔名冊上限（先例 `:2946-2970` 已續用 8 次），輪號前進後才須由 6 上修（可見決定，掌舵者可推翻）；不得出現三個連續上升輪而無名冊例外或淨減輪（P2 超過 +515 則插一輪純淨減並登缺陷帳本）；每階段新增 `tools/tests` 測試檔 ≤3（只計 `tools/tests`；`tools/tests_pg/` 不計入，另受 AC-LD-11-4 的每階段 ≤4 檔），重釘由收尾單人窗口做（鐵律七）；兄弟目錄的取捨見 ADR-SIDB-02。

## 9. 技術選型與模組落點

**9.1 選型**：引擎＝既有 PG18；驅動＝`psycopg` 3（Bridge 先例 `engine-bridge/app/db.py:24-27`）；遷移＝根層自有 `V<NNN>__*.sql`＋Python 執行器（Flyway 只管 `console`：`application.yml:25-29`；AutoClaude 的 alembic 在 `public`：`01-init-db.sql:2`）；寫入序列化＝`pg_advisory_xact_lock`；雜湊＝sha256＋canonical JSON；Console 讀＝JDBC 唯讀 DataSource。

**9.2 模式矩陣與解析**（先例：AutoClaude `yaml_only`／`both`／`db_only`，`factory.py:267-294`、`dual_state_repository.py:102-134`）：

| 模式（執行期解析，**非** params 鍵） | 真相源 | DB | 讀 | 寫 | 用於 |
|---|---|---|---|---|---|
| `file` | 檔 | 無 | 檔 | 檔 | 今天；未設 `SI_DB_DSN` 即此 |
| `shadow` | 檔 | 影子 | 檔（`--source db` 供差分） | 檔＋寫後同步 | P1～P3a；DB 不可用不擋 |
| `db` | DB | 真相 | DB | DB | P3b 起；舊檔只供匯入、匯出、凍結檢查；DB 不可用＝fail-loud |

解析規則見 AC-LD-02-2、02-3（`LEDGER_TRUTH` 住 `dal_types.py`，隨 git 走、可審、只在 P3b 切換 commit 改）。**不放 `params.json` 的理由**：`params.fingerprint()` 雜湊協定目錄下除 `research_sources.json` 外的所有檔（`params.py:15,128-141`），多一個鍵＝指紋改變＝M1～M5 量測窗的判準版本改變（議題中心同理，`Issue_Center_PRD.md:409`）。**凍結宣告**住新檔 `docs/05_development/SelfImproving_Frozen_Manifest.md`（宣告文字＋逐檔 sha256；在協定目錄之外、不進指紋，且屬 `non_evolvable_globs`〔`params.json:30`〕；放 `docs/06_quality/` 須加 glob＝改 `params.json`＝指紋變動，故不採；落點由 TCS 依 Root_Layout §2 確認），`si db frozen --check` 讀它。

**9.3 資料模型（`si` schema；欄位於 TCS 定稿）**

| 表 | 關鍵欄 | 約束與可變性 |
|---|---|---|
| `si.schema_migrations`、`si.meta` | version／sha256；`truth`、`flipped_at`、`ledger_head`、`synced_digest` | 追加；`meta` 僅 `si_owner` 與 `db flip` 可改 |
| `si.observations` | id、num、`time_raw`、`occurred_at`、情境／症狀／座標、`category`、`severity`、`disposition`、`marks jsonb`、`raw_line`、`src_file`、`src_line`、`row_sha256` | CHECK 枚舉、ID、處置首詞；只准處置欄 `open`→終值一次；變更須同交易有 audit 列 |
| `si.defects` | id、family、seq、`found_on`、情境、證據、`severity_raw`／`severity_rank`、`route`、`status_raw`、`status_class`、`home`（`main`／`archive_NN`）、`cursor`、`raw_line`、`row_sha256` | `status_class`∈五類或 NULL（沿 `defs.classify_status`）；證據、狀態欄 `text`（不設長度）；可更新、同交易寫 audit（含影像） |
| `si.debt_tracks` | kind（external／structural）、`def_id`、`source_name`、`since`、`unlock_condition`、`last_reviewed`、`row_sha256` | 具名阻塞源枚舉 CHECK；成長上限沿 `ledger_closing_guards`；延遲約束同上 |
| `si.events`、`si.artifacts` | `seq`、`t`、`kind`（21 值）、`by`、`body jsonb`、`line_bytes`、`raw_line`；`prop`、`name`（限 `rN.md`／`rN.patch`／`verifyK.json`）、`content bytea`、`sha256` | 追加專用；`line_bytes ≤ 4096` |
| `si.audit` | `seq`（鎖內 `max+1`）、`txid`、`at`、`actor`（動詞＠角色＠主機）、`tbl`、`row_id`、`op`、`before jsonb`、`after jsonb`、`before_sha`、`after_sha`、`reason`、`prev_hash`、`row_hash` | 追加專用＋鏈；可變表存完整列影像、追加專用表存 `after_sha` |
| `si.legacy_rows`、`si.import_runs`、`si.console_audit_files` | 原行、來源檔／行、原因碼；匯入批次與報告；`audit_ref`、`raw bytea`、`sha256` | 追加專用 |
| 讀模型 `si.issues`、`si.export_items`、`si.export_meta` | 議題欄＋`payload`；`kind`＋游標；`ne`／`problems`／`legend`／`summary`／`ledger_head` | 只准 `si_writer` 於同一交易刷新；P1／P2 由 `ledger-sync` 重建；不逐列 audit，由 `readmodel.fresh` 重算比對 |
| `console.si_console_writes`（V13；P3a 加 `raw` 欄）；專屬容器時另有 `si.console_requests` | 簽章載荷列（`audit_ref`、`kind`、`body`、`key_id`、`mac`、`raw`…；V13 現況 `V13__si_console_writes.sql:13-24`） | `si_writer` 只 SELECT；請求表只准 console-api INSERT |

任務書建議的 `proposals`、`decisions` 表**不另立**（PROP 狀態與 DEC 是事件的折疊結果，`fold.py`，另存會成第二個真相）；外部阻塞與結構債兩軌合為 `si.debt_tracks`。追加專用觸發器與**全表**「同交易必有 audit 列」的延遲約束觸發器（`audit_chain_guard` 只驗 `seq` 連續、`prev_hash` 銜接與 `txid`；追加專用表的 `after_sha` 用 PG 核心 `sha256()` 重算 `[C-19]`），SQL 草稿於 P0 隨 ADR-SIDB-03 附上（沿 `V13__si_console_writes.sql:28-51`；驗收＝AC-LD-05-2～05-5）。角色（§3.4）：`si_owner`（遷移、`flip`；表與觸發器擁有者，平時不用）、`si_writer`（非擁有者，不能停用觸發器；`observations`／`defects`／`debt_tracks`／讀模型可 UPDATE，其餘只 INSERT）、`si_reader`（SELECT；console-api 與 `ro` 動詞用）；密碼不入 SQL 檔，SOP 附 psql 範本。

**9.4 模組落點表**（依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2：新檔進既有 SelfImproving 套件，**扁平＋`dal_` 前綴**——能力登記只掃套件根層（`test_selfimproving_capability.py:182,332`），子套件會成鎖的盲區；`dbr`＝可 import 驅動、只開唯讀交易；`dbw`＝`dbr`＋寫入交易；唯讀動詞 import 閉包 ⊆ `ro`∪`dbr`。落點對不上 §2 的兩處〔`tools/tests_pg/`、套件內 `sql/`〕見 AC-LD-11-4）

| 件 | 落點（`tools/lib/selfimproving/`）與能力類 | 測試（新增；`tools/tests` 每階段 ≤3 檔、`tools/tests_pg/` ≤4 檔） | 需同步改的既有鎖（HEAD `c92f8bed`，TCS 重核） |
|---|---|---|---|
| Store 與模式解析 | `dal_types.py` `ro`（Protocol、資料類、錯誤碼、`LEDGER_TRUTH`、`resolve_mode()`）、`dal_resolve_ro.py` `dbr`、`dal_resolve_rw.py` `dbw`；函式簽名 `(repo)` 不變、內部自行解析（`session_brief.py:599-608` 不必改） | `tools/tests/test_selfimproving_dal_contract.py`＋基類 `_selfimproving_dal_contract.py` | `test_selfimproving_capability.py:4,83-85,176-225,333-334,413,650-651`（新類；登記鍵數 51＝39 `ro`／8 `rw`／2 `net`／2 `exec`）；`test_selfimproving_p3_meta.py`、`p2_meta.py` 的動詞數／`CAPABILITY` 計數；`Root_Layout…:52`＋落點鎖 `tools/tests/test_root_module_layout.py` |
| File／Mem 後端 | `dal_file_read.py` `ro`（包既有 `ledger`／`rows`／`defs`／`events.load_*`；可讀快照目錄）、`dal_render.py` `ro`、`dal_file_write.py` `rw`（包既有 `obswrite`／`evwrite`／`propfiles`）、`dal_snapshot.py` `rw`、`dal_mem.py` `rw`（記憶體寫入）；讀寫分檔使 `ro` 不 import 非 `ro`（`:216-219`） | 同上 | — |
| PG 後端 | `dal_pg_conn.py` `dbr`（唯一 `import psycopg`，延遲）、`dal_pg_read.py` `dbr`、`dal_pg_write.py`／`dal_migrate.py`／`dal_sync.py`／`dal_readmodel.py` `dbw`；遷移檔 `sql/V001__si_init.sql`…（資料目錄，不被 `*.py` 掃描） | `tools/tests_pg/test_selfimproving_dal_pg_*.py`（拆成每檔 ≤750 斷言行，含同步測試；CI 必跑、自帶收集數下限） | `test_selfimproving_capability.py:195-201`（明列例外）；Root_Layout §2 兩新格；`tools/selfimproving.py:7,30,391`（動詞 24→+6：`db`、`ledger-sync`、`def-*`、`debt-*`）；**不動** `run_root_unittests.py:85-90`、skip 棘輪、`skip_id_ledger.json` |
| SI 既有 20 檔 | 清單見 A.3（45 處 `[C-7b]`）；另入口 `tools/selfimproving.py`（2）、探針 `tools/probe/selfimproving_measure.py:48`；`evwrite.py:97-136`、`mea.py` 以路徑參數讀寫，隨同改接 | 既有 SI 測試 24,896 行原樣綠（夾具自 P1 起設 file，AC-LD-02-2；例外＝上列動詞數／能力登記釘的重釘） | `check.py:26,136,153-157`（新項只在 `shadow`／`db` 輸出；容量項改義）；**不改** `params.py`／`params.json`；`items=33` 的 10 處釘與 `CHECK_RULES_REV`＝4 的釘在 file 模式原樣成立（座標 `[C-20]`） |
| 非 SI 消費者 | 只經 `python tools/selfimproving.py export --json --kind <k>`（新 kind：`defects`、`debt_tracks`、`ledger-digest`；`events` 已在 `export.KINDS`（`export.py:27`）、`--kind` choices 取自它（`selfimproving.py:79`），CLI 與 Bridge `SI_KINDS` 兩處同加；快照是 `db snapshot` 動詞、不是 export kind，AC-LD-12-1），不跨套件 import：`check_defect_log_crossref`、`check_handoff_carriers`、`archive_defect_log`、`check_archive_required`、`integration_gate_core`、`baseline_origin`、`defect_ledger_index`、`sdd_latest`、三支探針 | 既有測試 8,458 行做差分；A.4 | `pre-commit:479-505`、`pre-push:485-505`、`root-infra-ci.yml:519-535` |
| CI | `root-infra-ci.yml` 新工作 `si-pg-contract`（先例 `agentconsole-ci.yml:63-101`；自帶收集數下限，數字由 TCS 定） | `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` | compat-ci `paths` 兩支共 24 條（`windows-compat-ci.yml:241-249,729-737`、`macos-compat-ci.yml:104-112,600-608` 等）：新碼已被 `tools/lib/selfimproving/**` 涵蓋；`tools/tests_pg/**` 入不入由 TCS 核；P4 才移除歸檔 glob |
| Console（分鍵） | backend：`SiReadAdapter.java`（JDBC、唯讀 DataSource）、`IssueQueryService.java:76`、`SiMirrorQueryService`、`SiReconcileService` 依 `console.si.read-source` 切源、Flyway 新版本（`raw` 欄）；frontend：`IssuesView`、`SiStatusBanner` 異常態提示；Bridge：P2 新增逐 kind GET 路由 `ledger-digest`（`routers/si.py:82-123` 現為逐 kind 路由；`si_cli.py:54` 的 `SI_KINDS` 增一值；`tests/test_si_readonly_lock.py` 路由釘同步）、P4 移除 `routers/si.py`、`si_cli.py`、`si_audit.py` | `IssueApiIT`、`SiMirrorApiIT` 加 `db` 源 | `IssueBridgeArchTest`、`SiReadOnlyArchTest`；`si_cli.py:49-54,84-103`（argv AST 鎖）；`test_si_*`；`SiObservationsPanel.tsx:98,231-233`；黃金檔 `si_golden` |
| 文件 | 本檔；`docs/02_architecture/ADR-SIDB-NNN-*.md`；`docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P<n>-<YYYYMMDD>.md`；SOP 新節；證據檔 `docs/06_quality/SelfImproving_LedgerDb_*`；`docs/05_development/SelfImproving_Frozen_Manifest.md` | — | Architecture `:612-618,854-870,944-956`；根 `CLAUDE.md` 第 5 條（連動面同 commit）；B 方案另含 `AgentConsole/docker/README.md` 〈4.3〉還原核對清單加 `si` |

**9.5 ADR 候選**（P0 轉正式 ADR 檔，各含選項與代價；「再開症狀」皆為可觀測事件）：
- **SIDB-01 真相源與 DB 位置**（A 維持檔／B Console PG 加 `si` schema／C 專屬 PG 容器／D 用 `autoclaude_pg`）：影子期任何可達的 PG18 皆可；P3 進場須滿足 §8.1 H2／H3，**建議 C**，B 在同樣隔離下可接受。再開：`down -v` 清掉 `si`、埠衝突。
- **SIDB-02 DAL 與模式**（A 只做 Pg／B Mem＋File＋Pg＋影子／C 另加 SQLite）：**B**（AutoClaude 先例），C 否（雙方言、保真度差）。**PG 測試放兄弟目錄 `tools/tests_pg/`＝稅的緩解，記為可見決定**（行數棘輪視 `tools/tests` 子目錄為繞道，`test_adr_xplat001_c1c2_lock.py:4491-4496`；兄弟目錄同型，仍受 LOC 分級）。再開：PG 契約測試在 CI 長期跑不起來；棘輪收緊到涵蓋兄弟目錄。
- **SIDB-03 完整性**（A 無／B 追加專用＋全表延遲約束＋鏈＋重放／C B＋外部錨點）：**B 為底線**，錨點＝快照內鏈頭（OQ-1）。再開：出現超級權限竄改的暴露證據。
- **SIDB-04 讀模型**（A Java 重實作 fold 與對照表／B Python 算、DB 存、Java 只讀／C 保留 Bridge 子行程讀 DB）：**B**（兩語言兩份判準是本 repo 反覆在治的複本型缺陷），C 為 P2 退路。再開：刷新使寫入 >1 s 或鏈頭常落後。
- **SIDB-05 寫入序列化、07 憑證、08 快照與離機備份**：05＝`pg_advisory_xact_lock`＋單交易配號，取代 `evwrite.py:97-136`（再開：取鎖逾時成常態）；07＝只認 `SI_DB_DSN`＋`PGPASSFILE`，D-5（再開：無人值守窗口缺 env 成常態）；08＝依 OQ-1（再開：快照與 DB 長期不同步）。
- **SIDB-06 Console 載體**（A 稽核檔＋Bridge／B 載荷列放 `console.si_console_writes`〔加 `raw`〕／B′ 專屬容器時 `si.console_requests`）：**B** 或 **B′**，附旗標與 drain（FR-LD-09），與 SIDB-01 連動；代價＝稽核檔「不可丟棄」性質改由 DB 備份承擔。再開：Console 表被清而尚有未入帳列。

## 10. 風險

| # | 風險 | 證據 | 緩解／回退 |
|---|---|---|---|
| R-1 | **跨機器同步斷裂**：git 即今天的同步機制，DB 不隨 clone 走 | 根 `CLAUDE.md:11`；`CrossPlatform_R201_FiveQuestion_MacRound_Q4Darwin_Evidence.md`；`[C-15]` | 影子期各機自建影子、git 仍為真相；P3 前定拓撲（OQ-2）；`unflip`；他機唯讀 |
| R-2 | **單點持久性、無遠端副本**：切換後 DB 是唯一一份；離站備份只是本機 MinIO；`down -v` 是文件化清場手段 | `docker/README.md:491`；`[C-13]` | §8.1 H1／H2；快照入 git（OQ-1）；專屬容器 |
| R-3 | **CI 內容閘失去輸入**：跨文件狀態一致、交接承接、歸檔保全，及讀真實帳本的單元測試 | `root-infra-ci.yml:519-535`；A.4 | 程式閘用 Mem／Pg 契約；內容閘輸入＝快照（OQ-1）或 NE（D-17）；A.4 逐支處置（AC-LD-13-5） |
| R-4 | **手改習慣**：缺陷列無動詞、凍結檔仍在工作樹；習慣切換集中在 P3b 當日（D-15） | §4 觀察 2 | 彩排與 SOP 預演；`si db frozen --check`＋pre-commit；`FILE-DRIFT`（P2 起） |
| R-5 | **遷移失真**：髒資料 14／6／3、93 列 >600 B、`orig=@` 附註 3 列 | `[C-4]`、`[C-5]` | `raw_line` 位元組保全、`legacy_rows`、恆等式、往返測試 |
| R-6 | **工作量與棘輪稅**：45 處／20 檔改 Store；SI 測試 24,896 行須原樣綠；行數棘輪（數 `tools/tests` 測試行；名冊已滿）、`tools/tests` 檔數下限 | §8.3；`Issue_Center_PRD.md:410` | §8.3 預算與預演；PG 測試獨立目錄（仍受 LOC 分級）；重釘由收尾單人窗口 |
| R-7 | **環境與延遲**：PG 對主機不可達、埠被占；SessionStart 延遲、無人值守缺 env | §8.2、`[C-12]`；`session_brief.py:624-649`；根 `CLAUDE.md:79` | DSN 可改埠；AC-LD-07-2；缺 DSN＝「量不到」 |
| R-8 | **能力登記／純度鎖與 DB 驅動** | `test_selfimproving_capability.py:139-146,182,195-201` | 扁平 `dal_*`、單一例外、`dbr`／`dbw` |
| R-9 | **中途停擺、並行派工互踩、意圖漂移**（同句話 10-26 已被滿足） | 根 `CLAUDE.md:280-287`、鐵律七；commit `93276120` | 各階段回退點；P2 為建議停靠點（OQ-6）；兩鍵分派、鎖持有面只由收尾單人窗口動 |
| R-10 | **M1～M5 量測中斷**：量測讀事件帳本與 git，切換後換源 | `tools/probe/selfimproving_measure.py:48`；`mea.py:189-192` | AC-LD-13-6；指紋不變（AC-LD-02-6） |

## 11. 出口條件

| 階段 | 機械可驗（指令＋判準） | 掌舵者真機 |
|---|---|---|
| P0 | SCG-0 PASS、Stage-1 凍結；ADR-SIDB-01～08 成檔；§3.3 勘誤案與 Architecture 草稿備妥；Root_Layout §2 已修（AC-LD-11-4）；A.4 普查定稿與棘輪預演表入 TCS | 答覆 OQ-1、OQ-2、OQ-3、OQ-6（至少） |
| P1 | AC-LD-01～05 綠；`db migrate` 第二次零變更；對帳恆等式成立；`si-pg-contract` 綠（`SI_TEST_PG_REQUIRED=1`）；無 PG 的全套根層測試綠且 skip 摘要同 P0 基準；**差分**：夾具 repo 上 P1 前後 `si issues --json`、`si export --json` 去 `generated_at` 後逐位元相同（P0 基準取自 `git archive` 匯出的 P0 commit）；file 模式 `si check` 位元組同 P0（items=33）`[C-2]`、`shadow` 下含新項全綠；`params.fingerprint()` 等於 P0 基準；`git diff --name-only` 不含守衛面 | 看一次對帳報告（`ledger-sync --dry-run`：每本帳本檔內列數＝正規表＋`legacy_rows`、CONFLICT=0）；關掉 DB 容器後 `si status` 明說「量不到」而日常動詞照常 |
| P2 | AC-LD-07、08 綠；黃金檔 A／B 差分；`read-source=bridge` 回應與今天一致；`FILE-DRIFT` 負控綠；db 路徑 p95 ≤ bridge 路徑 p95 | 議題中心件數與清單與今天相同（凍結日 `summary.total`）；停 Bridge 仍可看；停 DB 顯示原因而非 0 件 |
| P3a | AC-LD-06、09、12、13-1～13-6 綠；A.4 處置落地；彩排庫全套寫入＋閘門＋Console 載體綠；`down -v` 後 `si` 資料仍在；還原演練 rc 0 | 在 Console 按一次「決定」與「新增觀察」，經彩排庫入帳成功、議題中心即時更新 |
| P3b | AC-LD-10 綠（`flip --check` M 類全過、H 類證據檔齊）；`git status` 對帳本檔零變更；`si check` 全綠；`flip --check --post` PASS；AC-LD-13-6 差分綠 | 件數與切換前相同；用 `def-add` 記一件新事立即出現；關 DB 容器看到明確原因 |
| P4 | AC-LD-13-4（規範性清單 Grep 0）；全套綠；退役清單逐支審查報告；`params.fingerprint()` 仍等於 P0 基準 | 確認不再需要開任何帳本檔 |

## 12. 與既有系統的整合點（檔案:行號；HEAD `c92f8bed`）

整合點（檔案:行號）分列於 §3.3（上位規格）、§9.4（落點與需同步改的鎖）、附錄 A.3／A.4（引用處置與測試普查）；讀取縫與寫入縫＝`LEDGER_REL`／`PROPOSALS_REL` 的 45 處使用（`[C-7b]` 輸出逐行列出；另含 `evwrite.py:97-136`、`tools/selfimproving.py:359-373`），全改走 `Store`；`line` 欄在 `db` 模式的語意見 D-10。

## 13. 主控代決清單與開放問題

**13.1 主控代決（我拿不準、但給預設值；掌舵者可隨時推翻）**

| # | 決定 | 預設 |
|---|---|---|
| D-1 | 掌舵者 2026-10-27 裁決的對話座標 | 主控凍結時補 sid／line（SA 無從查證） |
| D-2 | 階段與鍵 | P0～P4，P3 拆 P3a／P3b；根層與 Console 分鍵（共 10 把）；TCS 每階段一份、兩鍵共用 |
| D-4 | 後端 | Mem＋File＋Pg，**不做 SQLite**（雙 SQL 方言、`timestamptz`／`jsonb`／觸發器／advisory lock 保真度差；Mem 已滿足「無 PG 也能跑」，PG 契約由 CI 服務容器把關） |
| D-5 | 憑證與 TLS | 只認 `SI_DB_DSN`＋libpq `PGPASSFILE`，**根層 CLI 不讀 `AgentConsole/.env`**（不耦合 AgentConsole 設定與其餘機密；代價：每台機器自設一次，缺＝fail-loud）；loopback `prefer`、其餘 `require` 以上 |
| D-9 | 列規則 | 700 B 列長、座標九形態等 P3 前不動；P4 以資料決定是否解除（解除會讓快照往返失真，須同步改判準） |
| D-10 | `schema_rev` | P2 維持 1；P3b 升 2（`origin`、游標改插入序；`line` 僅匯入列有值），Bridge 常數、backend、黃金檔、前端 `line` 顯示（`SiObservationsPanel.tsx:98`）同批改 |
| D-15 | `def-*`／`debt-*`／`--carrier operator` 在 file／shadow 模式 | **只在 `db` 模式提供**（rc 3 指路手改）；備選＝由 FileStore 改寫 Markdown（多一支寫入器、P4 退役，約多 400 行與往返驗證）。代價：習慣切換集中在 P3b 當日（R-4） |
| D-16 | 68 個缺陷歸檔檔進 DB | **要**；議題中心口徑仍不讀歸檔（`Issue_Center_PRD.md:29`）。理由：不遷就仍有一批可被手改的檔案帳本，「消除」不徹底 |
| D-17 | pre-push 在 DB 不可達時 | **不擋**，印 NE 與紅字：Docker 沒開不該讓 push 全卡；CI 把關程式面，快照（OQ-1）把關內容面 |
| D-18 | PG 測試落點 | `tools/tests_pg/`（P0 先改 Root_Layout §2）：避開 M6 與第三方相依鎖（AC-LD-11-1、11-3）；LOC 分級與棘輪的適用見 AC-LD-11-4，兄弟目錄的稅取捨見 ADR-SIDB-02；備選＝新增 `tools/tests@linux+pg` 剖面（落款＋兩張上限表＋CI 工作，稅更高） |

（D-3、D-6～D-8、D-11～D-14、D-19 於 v0.2 併入 §3.4、§8.3、§9.1～§9.5、AC-LD-06-2 等他節，編號保留不補；v0.1 的 OQ-3、OQ-6、OQ-7、OQ-9 已移入 D-4、D-5、D-16、D-17。）

**13.2 開放問題（只有掌舵者能答；各附建議與理由）**

| # | 問題 | 建議與理由 |
|---|---|---|
| **OQ-1** | 切換後要保留快照嗎？快照多久一次、何時觸發（RPO）？ | **舊檔永遠保留；另採 (b)**：快照放**固定一處** `docs/06_quality/SelfImproving_Snapshots/`（覆寫；舊版在 git 歷史；標頭宣告衍生物、含鏈頭），pre-commit 於 DB 可達且 DB 鏈頭≠快照鏈頭、或匯出失敗時擋 commit 並印匯出指令（逃生口 `AUTOSDD_SNAPSHOT_GATE_OFF`，AC-LD-12-3），再加 (c) 每日 `pg_dump -n si`。事實：寫入有尖峰（OBS 10-19 單日 144 列、近 7 日 142 列；DEF 近 14 日 40 列 `[C-15]`），一天不匯出可能丟數十至百餘列；**git 成本實測可忽略** `[C-18]`（首份 1,123 KiB、其後每份約 1.6 KiB），但須固定單一目錄覆寫（日期目錄使工作樹每份 +2.9 MB）。選項：(a) 輪收尾手動匯出（RPO＝數日）；(b) 如上（RPO＝最近一次 commit）；(c)＝(b)＋每日 `pg_dump`；(d) 不要快照（DR 只剩 pgBackRest＋真 S3、CI 內容閘改 NE、鏈無外部錨點、M4 略）。理由：git 是今天唯一的離機備份與 CI 輸入，(b) 以最小代價延續；代價：commit 多一道匯出閘 |
| **OQ-2** | DB 部署拓撲與換機器：近期還會在 Mac 上寫帳本嗎？ | 事實 `[C-15]`：git 不記錄寫入機器；自 2026-09-27 起 132 個 commit 觸及三本帳，標明 Mac 輪的最近一筆是 `9b9228fd`（2026-10-07，R206），其後 20 日無標示 Mac 的寫帳提交——**無證據顯示近期有 Mac 寫入，但不能排除**。建議：P1～P2 各機自建影子；P3 前定案，預設 **A 單一主力機為真相、他機唯讀**（匯入快照到本機拋棄式庫；H3 證據含「他機匯入快照演練」）；B 共用遠端 PG 成本高、暫不建議；C 各機本機庫加快照同步不建議。若仍要在 Mac 寫帳：改走 B，或限定 Mac 輪的寫入經主力機動詞 |
| **OQ-3** | 主控的非 Console 寫入路徑：可否新增 `obs-add`／`obs-close --carrier operator`，以及 `def-*`、`debt-*`？ | 事實：上位規格明文「本 PRD 不新增非 Console 的 `obs-add`，主控的手寫入帳照舊」（`SelfImproving_PRD.md:491`、`:904-905`）；P3b 後沒有檔可手寫。建議：**核准**，採 AC-LD-06-2／06-4 的邊界（能力等價、`AUTOSDD_UNATTENDED` 與手寫同級〔請一併確認〕、不寫事件、出處記 `si.audit.actor`）。若不核准：P3b 不得進（§8.1 H4），替代＝主控改走 Console 表單記觀察（需掌舵者帳號在場，自動化流程無法記） |
| **OQ-4** | R 系列驅動器（缺陷帳本未結列）怎麼改讀 DB？ | P3a 起以 `--unresolved-count` 同輸出契約過渡（AC-LD-13-1）；P4 改以議題中心清單件數（`issues --source 系統缺陷 --status 待解,進行中 --json`）為驅動器，並更新根 `CLAUDE.md:44,48` 與範本。**兩點請掌舵者定**：①語意差異——`--unresolved-count` 是主檔狀態欄判準（現值 0／全部 271 列，warn=86 fail=98），議題中心「待處理」是狀態對照（現值 2 `[C-3]`），改驅動器會改變「何時開 R 輪」；②CI 無 DB 時來源＝快照（OQ-1 (b)）或 NE。**建議 P4 前兩個口徑並行跑一輪**再定 |
| **OQ-5** | 範圍：五問輪帳本與 `skip_id_ledger.json` 納入嗎？ | **不納入**（§3.2）；本案＝自我進化三類帳本 |
| **OQ-6** | 哪一階段可以先停？ | **P2（含 `FILE-DRIFT` 偵測；條件＝其負控綠）是第一個長期停靠點**：Console 直讀 DB、檔案仍為真相、零不可逆動作、手改造成的落後 Console 會明說（AC-LD-08-4）；P3a 之後停也安全，但新動詞僅 `db` 模式（D-15），習慣沒換、價值有限；**P3b 是不易回頭的點（單份、無遠端副本）**，進場須過 §8.1 與您簽核 |

## 附錄 A　盤點細表

**A.1 帳本欄位格式**：觀察九欄＋檔頭 `tz`、標記鍵 13 種（`ledger.py:12`、`rows.py:52`）`[C-5]`；缺陷七欄（`AutoSDD_Defect_Log.md:8-11`），主檔與歸檔共 1,680 個相異 ID、62 個族、無重疊 ID `[C-4]`；外部阻塞／結構債五欄＋〈複查記錄〉（`AutoSDD_External_Blocked_Log.md:9-22`、`AutoSDD_Structural_Debt_Log.md:11-27`）；事件 21 種 kind（`events.py:32-37`）；其餘欄位與列規則以 `SelfImproving_PRD.md` §5.1.1／§9.2 為準。

**A.2 P4 退役候選**：見 §4 觀察 3。

**A.3 引用處置（現查 `[C-7]`、`[C-7b]`、`[C-8]`）**

| 類 | 數量 | 處置 |
|---|---|---|
| `tools/` 四個主帳本名 | 174 處／45 檔＝SI 套件 8、其他 lib 3、腳本 5、探針 3、測試 26 | SI 套件→Store；其他 lib、腳本、探針→改讀 `export`（P3a）或退役（P4）；測試隨被測碼 |
| `LEDGER_REL`／`PROPOSALS_REL`（`tools/*.py`） | 65 處／28 檔＝SI 套件 20 檔 45 處（`card`、`check`、`decverify`、`decwrite`、`evcheck`、`events`、`export`、`issues`、`issues_items`、`meawrite`、`obswrite`、`propfiles`、`promote`、`sandbox`、`writeverbs`、`research`、`verify`、`refs`、`status`、`scan`）＋入口 2＋探針 1＋測試 6 檔 17 | SI 套件、入口、探針→Store（AC-LD-02-5）；測試依 A.4 |
| `.github/workflows` | 30 處／4 檔＝compat-ci `paths` 條目 24＋註解 6 | `paths` 不增；P4 移除歸檔 glob；root-infra-ci 三個 step 改義 |
| `docs/` | 776 處／256 檔 | **P4 Grep 0 的規範性清單**：SOP 5、SelfImproving_PRD 31、四份 TCS（P0 16、P1 35、P2 17、P3 3）、Issue_Center_PRD 7、TCS-IssueCenter 10、迭代範本 6、Root_Layout 2、五問協定 README 1、TechDebt 兩份 3；其餘為歷史證據檔，不動 |
| AgentConsole／AutoClaude | 204／20；8／7 | 黃金檔與夾具重產（`si_golden`、`tests/fixtures/si`、`backend/src/test/resources/si`）；契約檔 `API_Contract_IssueCenter.md`、`TCS-SelfImprovingMirror-P1b-20261021.md`；AutoClaude 兩支測試見 A.4 |

**A.4 讀「真實」帳本內容的測試普查（P0 出口，AC-LD-13-5；P0 以 `[C-17]` 重跑、不得遺漏）**

| 測試（座標） | 讀什麼 → P3b 後 | 處置 |
|---|---|---|
| `tools/tests/test_defect_id_reference_integrity.py:171-186` | 真實缺陷帳本家族；全 repo 的 `DEF-…` 引用必須存在 → 新 DEF 只在 DB，引用新 DEF 的 commit 紅 | ID 全集改取「凍結檔∪最新快照」；快照不入 git（OQ-1 選 d）則 CI 內 NE、本機以 DB 驗 |
| `test_adr_xplat001_c1c2_lock.py:102,314-321,458-464` | 讀主檔＋歸檔取輪次落款 → 凍結檔不再長新輪次，「最新輪」判準失去輸入 | P0 查明判準語意；候選＝讀快照；屬 `_GOV_EXACT`，只能互動 session 改 |
| `test_check_defect_log_crossref.py:380,388,544` | 真實主檔做跨文件狀態一致 → 同上 | 改餵 `si export --kind defects` 或快照；差分（AC-LD-13-1） |
| `test_archive_defect_log.py`（真實家族讀取多處）、`test_check_archive_required.py` | 歸檔輪替與強制觸發 → 輪替退役 | 隨被測碼於 P4 退役（4,228 行） |
| `test_selfimproving_issuemap.py:21,145`、`test_selfimproving_measure_probe.py:450` | 真實缺陷主檔 → 凍結檔仍在，斷言與「現行」無關者維持 | 維持；斷言「最大 ID」類現行值者改讀 export（TCS 逐斷言判） |
| `test_selfimproving_events.py:1696`、`test_selfimproving_issues.py:1859-1860,1923`、`test_selfimproving_events_p2.py:1124` | 對真實 repo 根跑 `check`／`export`（含 ≤2 s 計時） → `db` 模式無 PG 即 fail-loud | 夾具設 `SI_LEDGER_STORE=file` 指向快照或凍結檔，或標 PG 專屬移 `tools/tests_pg/`；計時 AC 改相對判準 |
| `AutoClaude/tests/contract/test_ac_matrix_scaffolding.py:433-438`、`AutoClaude/tests/test_conftest_windows_native_skip_report.py:136-143` | 「缺陷帳本檔存在」＋`crossref.current_round()` → 檔仍在即可 | 凍結檔不得刪、`current_round` 不得退役 |

非測試的內容閘（`pre-commit:479-505`、`pre-push:485-505`、`root-infra-ci.yml:519-535`）見 R-3。

## 附錄 B　`si check` 33 項的去向（SA 初判，TCS 逐項定案）

- **`si check` 33 項在 file 模式全數不動**（AC-LD-02-6）；`db` 模式：**A 邏輯不變、改餵 DB 讀取器 22 項**（`row.*`、`ref.*`、`params.*`、`events.*` 除下列、`research.sources`）；**B 證據來源換成 DB 2 項**（`events.dec_console`、`obs.console_audit`）；**C 與檔案形態綁定 9 項，改寫或退役**（`ledger.structure`→`db.schema`、`ledger.time_tz`、`row.bytes`〔沿 D-9〕、`ledger.volume`、`ledger.vacuity`、`ref.orig_notes`、`history.migration`、`history.row_mutated`、`events.mutated`）。只在 `shadow`／`db` 新增：`db.schema`、`db.consistency`、`chain.intact`、`state.replay`、`readmodel.fresh`。

## 附錄 C　現查指令與輸出（HEAD `c92f8bed`；PowerShell，`$root`＝repo 根、`$py`＝`$root\.venv\Scripts\python.exe`；表內 `｜` 代替正則的 `|`；行數＝`len(read_text().splitlines())`，Grep 計數＝符合的**行**數；數字帳本天天在長，凍結日重算）

| # | 指令 | 輸出（2026-10-27 實測） |
|---|---|---|
| C-2 | `& $py tools\selfimproving.py check` | `si-check rows=332 items=33` … `overall=PASS rc=0`（file 模式） |
| C-3 | `& $py tools\selfimproving.py issues --json --limit 500`（以 `next_since` 取完） | `summary.total=605`（OBS 332／DEF 271／PROP 2）、`problems=0`、`ne=0`；候選 1、觀察中 2、延後 51、已完成 551 |
| C-4 | `defs.load_rows`（主檔與 `AutoSDD_Defect_Log_archive_[0-9][0-9].md`）、`ledger.parse_ledger`、事件帳本非空行數、`DefRow.evidence`／`status_text` 的 UTF-8 位元組最大值（`python -I`，於 repo 根，`sys.path` 加 `tools`） | `271 1415 14 6`（主檔列、歸檔列、欄數不符列、重複 ID 組）、`332 699`（觀察列、最大列 B）、事件 34；證據／狀態欄最長：主檔 806／1,117 B、歸檔 5,629／6,710 B |
| C-5 | `lib.selfimproving.ledger.parse_ledger`、`rows.parse_marks` 逐列統計 | 332 列、最大 699 B、93 列 >600 B、0 列 >700 B；附註檔 15 行 |
| C-6 | `& $py tools\check_defect_log_crossref.py --unresolved-count` | 外部阻塞 0、結構債 0、`未結列數＝0／全部 271 列｜warn=86 fail=98` |
| C-7 | Grep `SelfImproving_Observation_Ledger｜AutoSDD_Defect_Log｜SelfImproving_Event_Ledger｜SelfImproving_Proposals`（路徑 `tools`，不限副檔名，計數） | `174 total occurrences across 45 files` |
| C-7b | Grep `LEDGER_REL｜PROPOSALS_REL`（路徑 `tools`，glob `*.py`，計數） | `65 total occurrences across 28 files` |
| C-8 | C-7 加 `External_Blocked`、`Structural_Debt`、`Round_Ledger`、`skip_id_ledger`；`tools` 用 glob `*.py`，其餘目錄不限副檔名 | tools 217／52；docs（排除歸檔 glob）776／256；`.github` 30／4；AgentConsole 204／20；AutoClaude 8／7；`.claude` 0；LATEST `governance/` 0 |
| C-9 | `tools/lib/selfimproving/*.py` 行數合計；`& $py tools\selfimproving.py --help` | 51 檔 10,804 行；入口 412 行；24 個動詞 |
| C-10 | 逐集合 `len(read_text().splitlines())` 加總：SI 測試＝`tools/tests/` 的 `*selfimproving*.py`；缺陷族 4 檔＝`test_archive_defect_log`、`test_check_archive_required`、`test_check_defect_log_crossref`、`test_defect_id_reference_integrity`；Console 側＝`AgentConsole/` 下 Bridge／backend／frontend 中 si／issues 相關檔（排除 build、node_modules） | SI 測試 23 檔 24,896；缺陷族 4 檔 8,458；Bridge app 3 檔 726、測試 16 檔 4,832；backend 主碼 43 檔 2,879、測試 19 檔 6,282；frontend 35 檔 10,988（合計 25,707）；`tools/tests/test_*.py` 共 112 檔 |
| C-11 | `importlib.util.find_spec`（根 `.venv`） | `psycopg`、`psycopg_binary` 皆可匯入 |
| C-12 | `docker ps --format '{{.Names}}｜{{.Image}}｜{{.Ports}}'` | `aisdlc-pg-primary｜…｜5432/tcp`（未發布）；`autoclaude_pg｜pgvector/pgvector:pg18｜0.0.0.0:5432->5432/tcp` |
| C-13 | Grep `down -v｜down --volumes`（`AgentConsole`，排除 build 類目錄） | `41 total occurrences across 17 files` |
| C-14 | Glob `**/console_audit/*.json`（repo 根）；Grep `audit_sha256`（事件帳本，計數）；Grep `carrier=console`（觀察帳本，`-o`） | `No files found`；`4`；第 317、318 行各一 |
| C-15 | `git log --since='2026-09-27 00:00' --format=%h｜%aI｜%s -- <三本帳>`（主旨正則 `Mac｜macOS｜darwin`、不分大小寫；`--since` 不帶時刻會隨當下時刻漂移，須釘 `00:00`）；OBS／DEF 列日期欄分佈；六類帳本檔位元組總和 | 132 個 commit（`2026-10-13 00:00` 起 80）；主旨含 Mac 字樣 29 個，最近的標明 Mac 輪＝`9b9228fd`（2026-10-07）；OBS 近 7 日新增 142 列、10-19 單日 144 列；DEF 近 7／14／30 日新增 11／40／164 列；位元組總和 2,863,713 |
| C-16 | 讀 `test_adr_xplat001_c1c2_lock.py:554,595,2856-2881,2888-2979,4491-4496,7126-7132`；`AutoClaude/tools/check_loc_budget.py:276-283,296,318-340` | 行數棘輪只數 `tools/tests/*.py`；單輪上限表末列 `(214, 515)`；連續上升上限 2；名冊 R101、R129、R145、R171、R213、R214 共 6 列（上限 6），R214 列內 +3793、+2336；`guardrail_lib` 400、`guardrail_cli` 750，只有名為 `tests` 的目錄豁免 |
| C-17 | Grep `ledger_primary_ids｜_LEDGER\b｜read_text.*Defect_Log｜Defect_Log.*read_text｜REAL_DEFECT_LOG｜REAL_LEDGER｜Observation_Ledger.*read_｜LEDGER_REL`（`tools/tests`，計數）；Grep 帳本檔名與 `current_round\(`（`AutoClaude/tests`，計數）；另 `fx.ROOT`／`.parents[` 型真實根讀取 | `156 total occurrences across 9 files`；`9 total occurrences across 2 files` |
| C-18 | 暫存 repo（scratchpad）：對 `git log --since='2026-10-13 00:00'` 觸及三本帳的 80 個 commit，各取當時六類帳本檔成一份快照目錄並 commit；`git gc --aggressive`、`git count-objects -v` | 首份 1,123 KiB；80 份合計 1,251 KiB（其後 79 份增 128 KiB，≈1.6 KiB／份）；每日一份（11 份）1,218 KiB |
| C-19 | `docker exec autoclaude_pg psql -U autoclaude -d postgres -tAc "select encode(sha256('abc'::bytea),'hex'), current_setting('server_version')"`（唯讀） | `ba7816bf…15ad`（標準 SHA-256 向量）、`18.4`；rc 0 |
| C-20 | Grep `items=33｜all_33_items｜\b33\b.{0,30}items｜items.{0,30}\b33\b`（`tools/tests`，`*selfimproving*.py`）；Grep `CHECK_RULES_REV`（`tools`，`*.py`） | `items=33` 釘 10 處＝Grep 10 行扣 `test_selfimproving_issues.py:1859`（測試名）、加 `test_selfimproving_check.py:722`（`(ITEMS21, 33)`），分布於 `check`／`events`／`issues`／`measure_verb`／`capability`／`events_p2` 六支 `test_selfimproving_*.py`；`CHECK_RULES_REV`＝4 釘於 `test_selfimproving_p3_meta.py:292`（`params.py:13,139`） |
