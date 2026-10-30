# SelfImproving 帳本改 DB P0：上位規格勘誤案（備案；D5）

- 性質：備案證據檔。P0 **不套用**、不 `spec-refreeze`；`docs/01_requirements/SelfImproving_PRD.md` 與 `docs/01_requirements/Issue_Center_PRD.md` 在 P0 位元組不變。
- 來源：`docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §3.3 九列（#1～#5、#7 拆為 E-1～E-7；#6、#8、#9 見〈不勘誤〉）；契約＝`docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md` 契約節 C4、§5.1.3。
- 路由：各條於「套用階段」由該階段的鍵套用並 `spec-refreeze`；凍結後修訂路由見 TCS〈凍結後修訂路由〉。`monorepo-selfimproving` 不入路由：該鍵為 `SPEC_FROZEN`，且其 PRD 摘要與現檔本就不符（既有狀態，與本案無關）。
- 格式：每條 `### E-<n>` 之下緊接七個欄位行（`- <欄位>：<內容>`，單行、無空行）；`原文` 取自目前版本目標文件該行的逐字子字串，座標以檔:行表示。

### E-1
- 目標文件：`docs/01_requirements/SelfImproving_PRD.md`
- 原文座標：`:791`（「入 git…單一真相＝git」）、`:793`（「不用 PG」）
- 原文：跨機器可稽核、可 diff；單一真相＝git）
- 訂正文：改述為模式矩陣（帳本改 DB PRD §9.2）：`LEDGER_TRUTH` 是程式碼常數（預設 `file`，只在 P3b 切換 commit 改為 `db`，隨 git 走、可審；AC-LD-02-2），`file`、`shadow`、`db` 是執行期依該常數、`SI_DB_DSN` 與 `--repo`、`SI_LEDGER_STORE` 解析出的模式，不放 `params.json`；「單一真相＝git」自 P3b 切換 commit 起不成立（`db` 模式以 PG 為真相源，舊檔凍結並保留）；`:793` 的「不用 PG」改為「P1 起為影子、P3b 起為真相源」；仍不用 `build/`；引 `ADR-SIDB-001`（真相源與 DB 位置）。
- 生效階段：P1（影子）；P3b（真相）
- 套用階段：P1
- 理由：兩處原文寫死 git 為單一真相與不用 PG，與帳本改 DB 的模式矩陣（PRD §9.2）及 OQ-2 裁決（單一主力機為真相）不相容；P1 起 DB 以影子身分出現，原文須先改為可含模式的述句，免得 `db` 模式上線時規格與現況相反。

### E-2
- 目標文件：`docs/01_requirements/SelfImproving_PRD.md`
- 原文座標：`:811`（ADR-SI-10 多寫入者與配號）、`:987`（ADR-SI-01）、`:988`（ADR-SI-02）、`:997`（ADR-SI-10）、`:999`（ADR-SI-12）
- 原文：多寫入者與配號（SCG-0 一審 F-11；ADR-SI-10）
- 訂正文：逐項加「被取代關係」：ADR-SI-01 由 `ADR-SIDB-001` 取代（P3b 起 DB 為真相源）；ADR-SI-02 的 JSONL 與提案內容檔於 P3b 起降為匯出格式；ADR-SI-10 的寫入鎖與配號由 `ADR-SIDB-005` 取代（P3a 起，`pg_advisory_xact_lock` 加單交易配號，取代 `evwrite.py` 的鎖內配號）；ADR-SI-12 的 Console 唯讀讀模型由 `ADR-SIDB-004` 取代（P2 起，僅 `console.si.read-source=db` 時；預設 `bridge` 不變；Bridge 仍只經 CLI 子行程取數，AC-LD-08-4）。
- 生效階段：P2、P3a、P3b（依各項被取代時點）
- 套用階段：P2
- 理由：五處 ADR 表列各自假設檔案為真相與檔鎖為序列化機制；DB 切換後這些決定部分失效，須在原表列留下指向新 ADR 的單向指標，避免讀者採信已被取代的決定。

### E-3
- 目標文件：`docs/01_requirements/SelfImproving_PRD.md`
- 原文座標：`:990`（ADR-SI-03′ Console 載體＝稽核檔、`audit_sha256`）、`:792`（家目錄表 `console_audit/`「不可丟棄」）
- 原文：**不可丟棄**——它是 `carrier=console` 之 `dec` 與 OBS 列的回查憑證
- 訂正文：加註：P3a 起載荷落 DB 並保存原始位元組（`raw`）；旗標 `console.si.write-carrier` 為 `file`、`dual`、`db`；稽核檔「不可丟棄」的性質改由 DB 備份承擔；原選項 E 所慮的「第二個真相」因 DB 成為唯一真相而失效；引 `ADR-SIDB-006`。
- 生效階段：P3a
- 套用階段：P3a
- 理由：稽核檔的不可丟棄性是因為它是回查憑證；載荷改落 DB 後，憑證的持久性改由 DB 與其備份提供，原文若不更新會誤導家目錄清理與備份範圍判斷。

### E-4
- 目標文件：`docs/01_requirements/SelfImproving_PRD.md`
- 原文座標：`:491`（AC-SI-35-1 ③）、`:904`、`:905`（`obs-add`、`obs-close` 列）
- 原文：`--carrier` 目前只收 `console`，本 PRD 不新增非 Console 的 `obs-add`，主控的手寫入帳照舊
- 訂正文：加「掌舵者 2026-10-27 核准（OQ-3，核准座標 sid c61e3847-c8bf-4694-962f-93a657a7bf35 line 4437）：P3a 起於 `db` 模式新增 `--carrier operator`，以及 `def-*`、`debt-*` 動詞；`AUTOSDD_UNATTENDED` 下與手寫同級處理；若不核准，P3b 不得進入（H4）」；生效前沿用原文。
- 生效階段：P3a
- 套用階段：P3a
- 理由：缺陷與債務帳本改入 DB 後沒有「手改檔案」這條路，必須有等價的 CLI 載體；原文把非 Console 載體明文排除，須經掌舵者核准後才可放寬，核准座標欄用於回查該核准。

### E-5
- 目標文件：`docs/01_requirements/SelfImproving_PRD.md`
- 原文座標：`:527`（NFR-SI-02-4）
- 原文：外聯只在 `fetch.py` 一個模組、對象限來源表
- 訂正文：增列「DB 連線只在 `dal_pg_conn.py` 一個模組（唯一可 import `psycopg` 者），連線目標限 `SI_DB_DSN`」；能力登記測試明列該檔為唯一例外；新增 `dbr`、`dbw` 兩個能力類（唯讀交易與寫入交易）。
- 生效階段：P1
- 套用階段：P1
- 理由：NFR 原文把「外聯」限定在單一模組；DB 連線是新的外部相依，若不增列，能力登記的判準會把 `dal_pg_conn.py` 誤判為違規，或讓其他模組有理由自行連線。

### E-6
- 目標文件：`docs/01_requirements/Issue_Center_PRD.md`
- 原文座標：`:415`（「不快取」）、`:4`（「帳本…一個字不動」）
- 原文：**不快取**：Bridge 與 backend 每請求重算，帳本是唯一真相源。
- 訂正文：加「`console.si.read-source=db`（P2 起；非預設）時，讀模型是寫入時刷新、帶 `ledger_head` 的衍生值，過期由 `READ-MODEL-STALE` 偵測，退路為 `ADR-SIDB-004` 的選項 C；預設 `bridge` 仍每請求重算」。`:4` 的「一個字不動」同步註明指的是帳本內容語意。
- 生效階段：P2
- 套用階段：P2
- 理由：P2 起 console-api 可直讀 DB 讀模型，「不快取、每請求重算」不再對所有模式成立；原文須分模式敘述，否則讀模型的合法過期偵測會被視為違反規格。

### E-7
- 目標文件：`docs/01_requirements/Issue_Center_PRD.md`
- 原文座標：`:204`（游標：缺陷＝主檔資料列行號）、`:419`（`schema_rev` 維持 1）
- 原文：缺陷＝主檔資料列行號〔`DefRow.lineno`；DEF 號的族與序不單調，不能當游標〕
- 訂正文：加「P3b：缺陷游標改為 DB 插入序，`schema_rev` 升為 2（帳本改 DB PRD D-10）；Bridge 常數、backend、黃金檔與前端須同一批更新」。
- 生效階段：P3b
- 套用階段：P3b
- 理由：缺陷真相源搬進 DB 後，檔案行號不再存在（輪替歸檔也會重排它）；游標必須改用單調的插入序，這是對外契約變更，須升 `schema_rev` 並同批更新所有消費者。

## 不勘誤

- #6（`docs/01_requirements/SelfImproving_PRD.md:370,422` 的 `params` 指紋判準）：以設計避開——本案不新增任何 `params` 鍵、不改協定目錄任何檔，模式改由執行期解析；由 AT-LD-02-6-1、AT-LD-02-6-E-1 持續守護，故無需勘誤。
- #8（根 `CLAUDE.md:44,48` 的軌道敘述）：屬 P4 的連動面（OQ-4），在 P4 隨文件連動收齊，不在本案備案。
- #9（`.claude/hooks/block_destructive_git.py:1445-1464` 的 `_GOV_EXACT`）：無需改；該清單不含任何帳本檔（帳本改 DB PRD `[C-8]`），守衛面零變動。
