# Test Contract Specification — SelfImproving 決定重送去重與對帳取代標示（backend 重送閘與 dkind、對帳 supersededBy、frontend 面板分群與對話框停用）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件含 P2b 的 TCS 與後繼契約）的單一 Feature（SelfImproving P2b 之後的增量）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecideDedupe-20261031.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-903 |
| **Feature 名稱** | SelfImproving 決定重送去重與對帳取代標示——backend 重送閘（409 `si_decision_duplicate`）與 `dkind` 讀取、對帳 `items[]` 加 `dkind` 與 `supersededBy`、frontend 對帳面板的「已被取代」群組與決定對話框的動詞停用 |
| **User Story** | US-917（SA 已對 `AgentConsole/docs/06_quality/RTM.md` 與全 repo `docs/` 以 Grep 確認 F-903、US-917、AC-951 皆未被使用，不撞號） |
| **建立日期** | 2026-10-31 |
| **輸入快照** | HEAD＝`2da0205fb657c44ca665d8826d09af631434c51d`（`git rev-parse HEAD` 於落檔時現查；HEAD 會隨主控的 commit 前進，凍結前由主控重查）；上位檔 digest 見〈增量追溯表〉，SA 已以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算（Architecture 與 P2b TCS 取工作樹現值）；事故證據＝觀察帳本 OBS-SI-348 |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝鍵 `agentconsole-si-decide-dedupe` 的開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-si-decide-dedupe`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-decide-dedupe`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature（上位文件＝根層 `docs/01_requirements/SelfImproving_PRD.md`（v0.12）、AgentConsole 的 Architecture、ADR-001、後繼契約 `API_Contract_SelfImproving_P2b.md` 與上位 TCS `TCS-SelfImprovingDecide-P2b-20261024.md`）。**凍結檔不得再改**（本檔隨交的契約增補 §8 是檔尾追加、前文一字不改）：發現需修訂處一律寫在 §7 的 ⚖ 清單，走掌舵者 T1／SPEC_REGRESSION_CHECK；凡上位文件未定、本檔為使其可測而補定義者，標「本檔類推」並列入 §7.1。**本鍵零根層碼改動、零 Bridge 改動、零 Flyway 改動。**

### FRD-lite

**背景（真機事故，觀察帳本 OBS-SI-348）**：掌舵者於 2026-10-31 18:19～18:21（+08:00；日誌 10:19:51～10:21:26Z）在 Console「自我進化／提案」對 PROP-SI-006 的決定對話框送了四次「晉升（未驗採納）」：四次 `POST /api/v1/si/proposals/PROP-SI-006/decide` 皆 201，落四份稽核檔（auditRef 前 8 碼 e550a510、a2c9903f、ea60faf6、f5e78bb3，帳號 admin）。主機端以 `--carrier console` 只能入帳一份（e550a510，DEC-SI-006），其餘三份在對帳面板永遠顯示「待入帳」。掌舵者裁示：**多送的不得再顯示為待入帳（會造成誤解），且來源要堵住**；稽核紀錄本身不刪（稽核軌跡）。

**現況與變更（Before／After；brownfield）**

- Before：(1) backend 的 `POST /api/v1/si/proposals/{id}/decide` 不查既有列，同一張卡的同一決定每送一次就多一份稽核檔與一列 `si_console_writes`（201）；對話框成功後只收起表單，關閉再開同一張卡仍可再送。(2) `GET /api/v1/si/console-writes` 的 `items[]` 為九鍵；「待入帳」＝帳本沒有同 `auditRef` 的事件或觀察列標記，所以同一決定的第二份起（主機只能入帳一份）永遠 `ingested=false`；契約 §4 的 `orphans` 只涵蓋反向（帳本有、表內無）。(3) 對帳面板把所有 `ingested=false` 的列列為待入帳；決定對話框不知道已有待入帳的同一決定。(4) 寫入埠 `SiConsoleWriteRepository` 只有 `insert`、`deleteByAuditRef`；`SiConsoleWriteSummary` 沒有 `dkind`。
- After：(1) decide 在輸入閘之後、取 `auditRef` 之前查表，已有同 subject＋digest＋dkind 的 decide 列＝409 `si_decision_duplicate`、零副作用（W-D1；只管帶 digest 的六個動詞，rollback、unblock、resume 不受此閘，主控裁決 ⚖1）；(2) `dkind` 取自稽核列 `body`（不改 Flyway），寫入埠與對帳讀埠各補一個查詢（W-D2）；(3) `items[]` 十一鍵，被同一決定的已入帳列取代的待入帳列帶 `supersededBy`，`ingested` 仍如實為 false（W-D3；同樣只管帶 digest 的動詞）；(4) 面板把被取代列移到預設收合的群組，待入帳列與群組列都顯示 `dkind`（W-D4）；(5) 對話框只讀既有的對帳快取、對已有待入帳列的動詞停用，並在 409 時說明（W-D5；不發新請求，議題中心零改動）；(6) 契約面與既有釘選同步（W-D6）。三份既有的多餘稽核檔不刪，由 W-D3 自然判為被取代。
- **非目標**：不改 Flyway 與觸發器；不做任何刪除 UI 或刪列 API；Bridge 與稽核檔不動；根層 `tools/` 不動；不改 `console-writes` 的分頁與 scan 上限；不改 obs-add、obs-close、validate 的任何行為；不改議題中心（`IssuesView`）及其測試與夾具（決定對話框只讀快取、不發新請求）；不防 rollback、unblock、resume 的連送（⚖1）。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：本檔不新增 PRD 的 `AC-SI-NN-Y`（本增量延伸 AC-SI-33-2 與 AC-SI-35-5 的對帳語意）；本檔自增 AC 自 `AC-951-1` 起（P2b 用到 `AC-950-11`，不撞號），共 6 個：951-1 決定重送閘、951-2 dkind 的來源與兩個埠、951-3 對帳取代判定、951-4 對帳面板、951-5 決定對話框、951-6 契約面與釘選同步。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-951-1-1`→`AT_951_1_1`；Java 方法名以底線形開頭加駝峰敘述）。每個 AC 內數字序與 E 序各不超過 9。
4. **計數**：AC 6 個、AT 25 個（正控 11、負控 14；分佈見 §1 末）。

**本增量交付物**（D1～D7；路徑相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | backend 重送閘與寫入埠 | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下：`application/service/SiConsoleWriteService.java`（改）、`application/port/out/SiConsoleWriteRepository.java`（加 `findDecideAuditRefs`）、`adapter/out/persistence/SiConsoleWriteAdapter.java`（加查詢）、`domain/exception/ErrorReasons.java`（加 `SI_DECISION_DUPLICATE`）、`adapter/in/web/ErrorResponseDocumentation.java`（decide 的 409 說明）、`adapter/in/web/SiController.java`（僅說明文字）、`application/port/in/SiWriteUseCase.java` 與 `application/port/out/SiAuditRefSource.java`（兩者僅 Javadoc：「閘門序…→執行」「重送一律新 auditRef」「一個請求恰取一次、重送一律新 ref」三處敘述過時） | 開發 agent | AC-951-1、951-2 |
| D2 | backend 對帳讀面 | 同上根目錄下：`domain/model/si/SiConsoleWriteSummary.java`（加 `dkind`）、`application/port/out/SiConsoleWriteQueries.java`（加 `findDecideRows`）、`adapter/out/persistence/SiConsoleWriteAdapter.java`（`findRecent` 的 dkind 表達式）、`application/port/in/SiReconcileUseCase.java`（`Item` 加二欄）、`application/service/SiReconcileService.java`（取代判定）、`adapter/in/web/dto/SiConsoleWritesResponse.java`（`Item` 加二欄） | 開發 agent | AC-951-2、951-3 |
| D3 | frontend 純函式與型別 | `AgentConsole/frontend/lib/domain/si.ts`、`lib/api/schema.d.ts`（重產）、`lib/api/types.ts`（若需要）、`lib/api/queries.ts`（僅在需要新增唯讀的快取 hook 時；`useSiConsoleWrites` 的行為不變） | 開發 agent | AC-951-4、951-5、951-6 |
| D4 | frontend 元件 | `AgentConsole/frontend/components/domain/si/SiWritesPanel.tsx`、`SiDecideDialog.tsx`（只讀既有快取，不發新請求）、`siParts.tsx`（若需要） | 開發 agent | AC-951-4、951-5 |
| D5 | 既有釘選測試同步（只增不減；逐項見 §4） | §4〈需同步的既有測試〉12 筆 | 開發 agent | AC-951-6；NFR-DD-5 |
| D6 | 文件連動 | `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md` §8（SA 已隨本檔落檔）；主控代做：`Architecture.md` §11.1 新列（已在工作樹，與實作同一 commit 進）、RTM 本地子表（依 DEF-200-576 體例另立新檔 `AgentConsole/docs/06_quality/RTM-SelfImprovingDecideDedupe-20261031.md`，並於 `RTM.md` 補一節存根連到它）、SCG-4 報告、`AgentConsole/frontend/lib/help/self-improving.ts`（對帳面板的被取代群組、決定對話框的動詞停用與重送 409 的頁面說明；欄位名須逐字引用畫面字樣、出處鎖到 `sourceFiles` 找，故與 UI 實作同 commit）、凍結上位的勘誤（§7.2 第 8 項） | SA、主控 | V5 |
| D7 | 出口實查（V 系列，非 AT） | §6.2 的 V1～V6 | QA、主控、掌舵者 | OBS-SI-348 的再開症狀 |

**提交順序與責任**

- 依賴序 backend（D1→D2）→ frontend（D3 的 `schema.d.ts` 須在 backend 完成後重產：沿 P2b 勘誤 9 的作法，以拋棄式 IT 倒 `/v3/api-docs` 餵 `scripts/gen-api.mjs`，結果入庫）→ D3 純函式 → D4 元件 → D5；測試與受測碼同步完成。每支程式完成即編譯並跑該區 AT，不累積（`AgentConsole/CLAUDE.md` 鐵律 11）。
- 開發 agent **不 commit／push**、不動 `engine-bridge/`、根層 `tools/`、`.github/`、`.claude/`、Flyway `db/migration/`、凍結檔與既有 TCS（鐵律 7）。D6 的 `Architecture.md` §11.1 新列（主控已加在工作樹）須與實作**同一 commit** 進、不得先單獨 commit（單獨 commit 會讓已提交的 HEAD 上 `lib/domain/si.test.ts` 的 AT_940_5_1 變紅）；開發期間工作樹已有該列而 `SI_REASONS` 尚無第六鍵時，該 AT 為預期紅，加上第六鍵後轉綠，不得改弱該測試（⚖2）。
- 真帳本、真事件帳本、真 `~/.autosdd/` 一律唯讀：AT 只用 Testcontainers PG、迷你 Bridge 與 jsdom；V1、V2 屬真機檢核，由掌舵者與 QA 做、不由 AT 充當。
- 依賴：本鍵依賴 P2b 已落地的 backend 寫入載體與對帳讀面（HEAD 上 `SiConsoleWriteService`、`SiReconcileService`、`SiWritesPanel`、`SiDecideDialog` 皆在），不依賴根層任何新碼。

**〈增量行為規則〉**（W-D1～W-D6；各 AT 以 W-D 編號引用。實查依據：backend 的 `SiConsoleWriteService`、`SiReconcileService`、`SiReconcileUseCase`、`SiConsoleWriteAdapter`、`SiConsoleWriteRepository`、`SiConsoleWriteQueries`、`SiConsoleWriteSummary`、`SiConsoleWritesResponse`、`SiController`、`SiBridgeErrors`、`ErrorReasons`、`ErrorResponseDocumentation`、`GlobalExceptionHandler`、`DomainException`；frontend 的 `components/domain/si/{SiWritesPanel,SiDecideDialog,siParts,SiView}.tsx`、`components/domain/issues/IssuesView.tsx`、`lib/domain/si.ts`、`lib/api/{queries,types,schema.d}.ts`；現行測試 `SiConsoleWriteApiIT`、`SiConsoleWritesReadApiIT`、`SiReadOnlyArchTest`、`OpenApiIT`、`AbstractSiWriteIT`、`si.test.ts`、`SiView.test.tsx`、`SiDecideDialog.test.tsx`、`IssuesView.test.tsx`；根層 `tools/lib/selfimproving/fold.py` 的 resume 與 suspended 折疊；凍結契約 `API_Contract_P3-6.md` §0.2 的 details 慣例）

- **W-D1 重送閘**（`SiConsoleWriteService.decide`；**只管帶 digest 的六個動詞**——approve、reject、return、promote、decline-promote、ack-handoff，即表 M-D 實際有 digest 者；rollback、unblock、resume 沒有卡面 digest 可綁，**不受此閘**，其重送的合法性由主機端 decide 的前提態判〔主控裁決，⚖1〕；obs-add、obs-close、validate 亦不經此關）：在授權（W10 序 2～3）、停用檢查（序 4）、輸入閘（序 5）**之後**、取 `auditRef`、簽章、INSERT、Bridge **之前**，以命令的 `digest` 是否非 null 判定受閘動詞，並以寫入埠 `findDecideAuditRefs(subject, digest, dkind)` 查 `si_console_writes` 是否已有 `kind='decide'` 且三者相同的列：`subject`＝命令的 `subject`（PROP 號，即列的 `subject_id`）、`digest`＝命令的 `digest`（非 null）、`dkind`＝命令的 `dkind`（逐字、區分大小寫）。**有任一列**（不論該列是否已入帳、不論哪個帳號送的、不論 `reason` 是否相同）＝回 **409**，頂層 `reason` 為 `si_decision_duplicate`（`ErrorReasons.SI_DECISION_DUPLICATE`），`details`＝`existingAuditRef`（回傳清單的第一個＝`time` 最早、同刻 `audit_ref` 最小者；同刻比較規則見 W-D2 (e)）、`dkind`、`subject`、`digest8`（digest 去掉 `sha256:` 前綴後的前 8 碼；受閘動詞的 digest 恆非 null，故四鍵恆在；防禦性規格：若 digest 為 null 則省略 `digest8`、不輸出 null，避免 `DomainException.details` 的 `Map.copyOf` 遇 null 而 NPE，⚖3），`message` 含 `請以對帳面板為準`。**零副作用**：不取 ref（`SiAuditRefSource` 取用次數不變）、不簽章、不寫 DB、不呼叫 Bridge（含 GET）。同 subject＋digest 但 dkind 不同＝照常受理（入帳前改變主意是合法的，由主機端決定吃哪一份）。補償刪除（W11）後列已不存在＝可重送；結果不明而保留的列＝仍擋（已知邊界 1；補救＝主機端 DBA 依 PRD §9.3 補償刪列）。`SiBridgeErrors` 不動（這不是 Bridge 的錯）；`ErrorResponseDocumentation` 對 `POST /api/v1/si/proposals/{id}/decide` 的 409 說明載明本 reason，其餘兩個寫入 POST 的 409 說明不變。
- **W-D2 dkind 的來源與兩個埠**：不改 Flyway、不加欄。`dkind` 由稽核列 `body`（TEXT；`SiAuditSigner` 自己產生的合法 JSON）以 SQL 表達式 `(body::jsonb)->>'dkind'` 取出，且只對 `kind='decide'` 的列取（以 `case when kind = 'decide' then … end` 保護：非 decide 列恆為 null；body 內沒有 `dkind` 鍵的 decide 列也為 null）。(a) 寫入埠 `SiConsoleWriteRepository` 加 `List<UUID> findDecideAuditRefs(String subject, String digest, String dkind)`：只回 `kind='decide'` 且 `subject_id`、`digest`、dkind 皆等於參數的列，依 `time` 升冪、同刻 `audit_ref` 升冪；`digest` 或 `dkind` 參數為 null 回空清單（無 digest 的動詞不受重送閘，所以不提供 null 比對）。(b) 對帳讀埠：`SiConsoleWriteSummary` 加元件 `dkind`（非 decide 列為 null），`findRecent` 以同一表達式選出；另加 `List<SiConsoleWriteSummary> findDecideRows()`（全部 decide 列，同一投影，`time` 升冪、同刻 `audit_ref` 升冪；供 W-D3 的取代判定，⚖4）。(c) **仍不選整欄 `body` 與 `mac`**：契約與各 Javadoc 的「查詢一律不選 body 與 mac」改寫為「不選整欄 body 與 mac；只以表達式取 body 內的 dkind」。(d) ArchUnit「唯一存取該表的類別」鎖與 DML 三條的鎖不變（新增的兩個查詢是 SELECT）。(e) **同刻 tie-break**：全文所有「同刻 `audit_ref` 升冪」一律指小寫正規 UUID 字串的字典序（等同 PostgreSQL uuid 的位元組序與 `String.compareTo`）；Java 端不得用 `UUID.compareTo`（它以有號 long 比較，首位元組 0x80 以上者會排到 0x7f 以下者之前），也不得對 SQL 已排序的結果重排（AT 以 §5.1 的 UT1、UT2 鎖住）。
- **W-D3 對帳的取代判定**：`GET /api/v1/si/console-writes` 的 `items[]` 鍵集合改為**恰** `auditRef`、`kind`、`dkind`、`user`、`role`、`time`、`subjectId`、`digest`、`keyId`、`ingested`、`supersededBy`（十一鍵，鍵恆在、值可為 null；仍無 `body`、`mac`）。`dkind`＝W-D2 的值。`supersededBy`＝對 `kind=decide` 且 `ingested=false` 且 `dkind`、`subjectId`、`digest` 皆非 null 的列 r（即帶 digest 的六個動詞；**無 digest 的動詞 rollback、unblock、resume 一律 null**——同一 RUN 再度暫停後第二次合法的 resume，不得被先前已入帳的 resume 誤判為被取代而從待入帳消失，⚖1、⚖10）：在**整張表的 decide 列**（`findDecideRows()`，與 `limit` 無關）中找「另一列」d——`d.auditRef` 不等於 `r.auditRef`、`d.auditRef` 屬於同一次 `scan()` 的 `ingested` 集合、`d.subjectId` 等於 `r.subjectId`、`d.dkind` 等於 `r.dkind`、`d.digest` 等於 `r.digest`——取這些 d 中 `time` 最早者（同刻取 `auditRef` 升冪第一個，比較規則見 W-D2 (e)）的 `auditRef`；沒有 d 則 null。其餘列（kind 非 decide、已入帳、`dkind`、`subjectId` 或 `digest` 為 null）一律 null。`reconcile.status` 為 NOT-EVALUABLE 時，`supersededBy` 與 `ingested` 一樣整欄為 null。**被取代列的 `ingested` 仍如實為 false**（不冒充已入帳）；取代者必須是本表的列（帳本有 carrier 為 console 而表內沒有的項是 orphan，不充當取代者）；兩列都未入帳時互不取代。
- **W-D4 對帳面板**（`SiWritesPanel.tsx`、`lib/domain/si.ts`）：(a) `pendingWrites(items)` 改為只回 `ingested` 為 false 且 `supersededBy` 為 null、缺席或空字串的列（排序規則不變）；(b) 新增純函式 `supersededWrites(items)`：回 `ingested` 為 false 且 `supersededBy` 為非空字串的列，依 `time` 升冪、同刻依 `auditRef`；兩函式不改動輸入；(c) 面板於**待入帳清單之後**渲染預設收合的群組 `si-superseded-list`（僅當對帳 ok 且被取代列數 N 至少 1；NOT-EVALUABLE 時不渲染），群組內有展開鈕 `si-superseded-toggle`（`aria-expanded`、`aria-controls`；標題列文字恰為 `另有 N 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`，N 為半形數字），展開後依序列出 `si-superseded-<auditRef>` 列：`si-dkind-<auditRef>`、`對象：<subjectId>`、time、auditRef、`si-superseded-by-<auditRef>`（文字 `取代者：<supersededBy>`），**沒有入帳指令鈕**；(d)「無待入帳」（`si-writes-empty`）的判定只看待入帳清單與 orphans，被取代筆數不影響；(e) 待入帳列與被取代列都以 `si-dkind-<auditRef>` 顯示 `dkind`（決定動詞中文標籤加原文，例 `核准 approve`；`dkind` 為 null 的列不渲染此元素），中文標籤由新純函式 `decideKindLabel(dkind)` 提供（九個動詞對照見 §5.1；未知值原樣回傳、null 與 undefined 回空字串）。群組的展開鈕是面板在入帳指令鈕之外新增的唯一按鈕，名稱不含刪除、移除、清除字樣。
- **W-D5 決定對話框**（`SiDecideDialog.tsx`、`lib/domain/si.ts`）：(a) 對話框**只讀**既有的對帳查詢快取（面板與 `useSiConsoleWrites` 所用的同一個查詢鍵），**不發任何新的 GET**（主控裁決，⚖5）；實作形態不鎖（`useQueryClient().getQueryData`，或 `useQuery` 以 `enabled: false` 讀快取）。僅當快取有資料且 `reconcile.status` 為 ok 時才停用動詞；快取缺席（沒有面板的頁面〔議題中心〕、面板的查詢尚在載入或已失敗）與 NOT-EVALUABLE 一律不停用（寧可讓 backend 的 409 擋）；議題中心及其測試與夾具零改動、零額外請求；(b) 新純函式 `pendingDecision(items, { subject, digest, dkind })`：`digest` 為 null（無 digest 的動詞）一律回 null；否則回第一個（`time` 最早、同刻 `auditRef` 最小）符合下列全部條件的列，否則 null——`kind` 為 decide、`subjectId` 等於 subject、列的 `digest` 等於 digest、列的 `dkind` 為非 null 且等於 dkind、`ingested` 為 false、`supersededBy` 為 null、缺席或空字串（與 W-D4 (a) 一致）；(c) 對每個動詞選項呼叫 `pendingDecision`（subject 為提案編號，恢復為運轉編號；digest 在 `DECIDE_FIELDS` 該動詞需要 digest 時取開啟當下綁定的卡面值，否則為 null，因此 rollback、unblock、resume 永不停用，⚖10），命中者的 `<option>` 為 disabled，並在送出鈕旁以 `si-decide-dup` 顯示 `已送出待入帳（稽核編號 <auditRef>）`（前面可帶該動詞的標籤；多個動詞命中則各一則，以 `getAllByTestId` 取）；(d) backend 回 409 且 `reason` 為 `si_decision_duplicate` 時：toast 文字由 `siWriteErrorText` 產生——以 `同一張卡的同一決定已送出（稽核編號 <existingAuditRef>），待主機入帳，不需重送` 起首（`details.existingAuditRef` 不是字串時省略括號段），其後以全形分號接 `describeError` 的原文（含 reason 與 traceId）；對話框不關、表單不收起、送出鈕恢復；(e) `SI_REASONS` 加鍵 `DECISION_DUPLICATE`（值 `si_decision_duplicate`；五鍵→六鍵，原五鍵與順序不變）；既有釘選「恰五鍵」的測試只增不減（§4）。
- **W-D6 契約面與釘選同步**：(a) `OpenApiIT`：既有釘選（路徑與操作總數、各 SI 路徑的方法與狀態碼集合）不改；新增 `SiConsoleWriteItem` 的鍵集合與必填集合釘選，以及 decide 的 409 與 operation 說明含新 reason、其餘兩個寫入 POST 的 409 說明不含它；(b) `schema.d.ts` 依 P2b 勘誤 9 的作法重產；(c) `SiReadOnlyArchTest`：兩個埠的方法集合釘選同步（§4 第 1 項），並新增 `findRecent` 的 SQL 形狀與 `SiConsoleWriteSummary` 元件的釘選；(d) 前端釘選：`SI_REASONS` 六鍵、`writeItem` 夾具（議題中心的測試與夾具零改動）；(e) 文件：`API_Contract_SelfImproving_P2b.md` §8（SA 已寫）、`Architecture.md` §11.1 一列（主控，⚖2；與實作同一 commit 進）、RTM 本地子表（新檔 `AgentConsole/docs/06_quality/RTM-SelfImprovingDecideDedupe-20261031.md`，DEF-200-576 體例）的 F-903、US-917、AC-951-1～6 與各 AT 列（主控）、`frontend/lib/help/self-improving.ts` 的頁面說明（主控，D6）；`SiController`、`ErrorResponseDocumentation`、`ErrorReasons` 與各 Javadoc 的說明文字同步，不留過時敘述（例：`SiConsoleWritesResponse` 的「鍵集合恰九鍵」、`SiConsoleWriteRepository` 的「只有兩個動作」、`SiController` 的閘門序敘述、`SiWriteUseCase` 的「閘門序…→執行」與「重送一律新 auditRef」、`SiAuditRefSource` 的「一個請求恰取一次、重送一律新 ref」）。(f) **實作陷阱**（開發 agent 須知）：① `ErrorResponseDocumentation` 的 409 說明目前是單一泛用字串，須新增端點專屬覆寫表（比照 `NOT_FOUND_DESCRIPTION`）；② `SiMirrorApiIT.AT_940_5_2` 會讀 `ErrorResponseDocumentation.java`、`ErrorReasons.java`、`NotFoundException.java` 的原始碼：新增的說明文字不得含「唯一帶 reason」「唯一例外」字樣，`SI_NOT_FOUND`、`SI_UNAVAILABLE` 的常數字面格式不得改動，`ErrorResponseDocumentation` 仍須含 `si_not_found`（覆寫表不得取代既有的 404 說明）；③ `si.static.test.ts` 的 `WRITE_HOOK` 以名稱前綴判寫入型 hook（`useCreate`、`useUpdate`、`useDelete`、`usePost`、`usePut`、`usePatch`、`useRetry`、`useApprove`、`useSignoff`、`useExecute`、`useSiDecide`、`useSiAddObservation`、`useSiCloseObservation`、`useSiValidateObservation`），並斷言 `SiDecideDialog.tsx` import 的寫入 hook 恰為 `useSiDecide`：新增的唯讀快取 hook 不得以這些字樣起頭（例：命名為 `useSiConsoleWritesCache`）；該檔的全樹掃描另禁止直接 `fetch(` 與 PUT、PATCH、DELETE 字樣。

**主控先行裁決（已裁，不再開 ⚖；掌舵者可推翻）**：(1)～(6) 即 W-D1～W-D6 的設計方向（任務書逐條裁定，本檔只補成可測規則）；(7) 稽核紀錄不刪，多餘的三份由取代標示處理；(8) 同 subject＋digest 但不同 dkind 照常受理；(9) 文件最小化（本檔 AT 恰 25 個、每個 AT 區塊 8 行）；(10) 本檔不寫測試摘要字樣與 4 位數字同行（`AgentConsole/CLAUDE.md` 文件閘）；(11) 主控 2026-10-31 對 ⚖1～⚖5 的裁決（⚖1 採替代案的一半、⚖2～⚖4 採預設、⚖5 採替代案）已併入本檔，結果見 §7.1。

**User Story 與 AC 對映**

| US ID | User Story | AC ID | 摘要（PRD 座標；規則） |
|-------|------------|-------|-------------------------|
| US-917 | 作為掌舵者，我要同一張卡的同一決定只能送出一次、重複的稽核檔不再被當成待入帳，以免對帳面板誤導我，也不必再人工分辨哪一份才是有效的 | AC-951-1、951-2、951-3、951-4、951-5、951-6 | PRD AC-SI-33-2、AC-SI-35-5 的增量；W-D1～W-D6：重送閘、dkind、取代判定、面板分群、對話框停用、契約面同步 |

> 編譯相容提醒：本表第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把第一欄形如 AC 的表格列當成 AC→AT 映射列掃描）；除 §1 外沒有任何第一欄以 AC 起頭的表格。**§1 表格列的描述格不含豎線字元**（編譯器以豎線切欄）。

**INVEST 自檢**：獨立（只依賴 HEAD 上已存在的 P2b 寫入載體與對帳讀面）、可協商（⚖ 清單列出可裁決的預設）、有價值（直接消除 OBS-SI-348 的誤導與來源；V1、V2 由真機判定）、可估計（backend 約 10 個類別小幅修改加 2 個測試類別補測、frontend 2 個元件與 1 個純函式模組、4 個既有測試檔補測）、小（零 Bridge、零根層碼、零 Flyway、零新路徑）、可測（全部 AT 只用 Testcontainers PG、迷你 Bridge、jsdom 與 fetch 替身，不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-DD-1 | **重送被擋時零副作用**：409 前後，表內列數、迷你 Bridge 收到的請求數（含 GET）、ref 來源取用次數三者的變動量皆為 0 | AC-951-1 |
| NFR-DD-2 | **不冒充已入帳**：被取代列的 `ingested` 恆為 false；`supersededBy` 非 null 的列必有一個已入帳的同伴列 | AC-951-3 |
| NFR-DD-3 | **失效可偵測**（NFR-SI-09 對稱）：對帳量不到時 `supersededBy` 與 `ingested` 皆為 null、面板不顯示被取代群組也不顯示無待入帳 | AC-951-3、951-4 |
| NFR-DD-4 | **判定與分頁無關**：同一時刻、不同 `limit` 下，同一列的 `supersededBy` 相同 | AC-951-3 |
| NFR-DD-5 | **零退化與範圍**：既有 AT 在其角色下仍綠，釘選數字只增不減（§4）；只動 §5.7 允許集合 | V4、V5 |
| NFR-DD-6 | **開發 agent 交卷前閘門**（輸出逐字貼入）：(1) 本檔各 AT 逐一單跑；(2) `gradlew clean build`；(3) 前端 lint、tsc、build、vitest；(4) 讀 rc 先存變數；(5) 不 commit、不碰 Bridge、根層、Flyway 與凍結檔；(6) 夾具與測試中的 DEF、OBS、PROP、RUN 編號只准用真帳本已存在者；(7) 不得有 `sk-` 形態字串；(8) 契約 §8 與實作不符處以純文字回報；(9) 交卷含流程摩擦節 | SCG-4 實跑檢核 V4、V5 |
| NFR-DD-7 | **跨平台**（根鐵律三）：新程式與測試不引入平台專屬假設；Windows 與 Linux（CI）皆須全綠；macOS 未驗 | V6 |

**追溯矩陣**：F-903 ← PRD FR-SI-33 的 AC-SI-33-2（稽核列與對帳）、FR-SI-35 的 AC-SI-35-5（對帳：已送出而尚無帳本列＝待入帳）、§9.3 寫入端點；觀察帳本 OBS-SI-348；Architecture §10.3、§11.1；P2b TCS 的 W10、W11、W14、W15、W17、W21；P2b 契約 §0.3、§1.4、§4、§6；US-917 → AC（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3；「已凍結上位文件」相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定、FRD 覆蓋、利害關係人已簽核 | PRD v0.12 的 FR-SI-33（AC-SI-33-2）、FR-SI-35（AC-SI-35-5）、§9.3；F-903；OBS-SI-348；掌舵者 2026-10-31 對 OBS-SI-348 的裁示（由主控任務書轉述，座標由主控補記）；凍結常態規則（根 CLAUDE.md） | docs/01_requirements/SelfImproving_PRD.md | sha256:4dd95528d935d92f6c80815dd2697c9288072484ccfdf048250e102d6169b7a4 |
| SCG-0／NFR 已量化、User Story INVEST、RTM 初版 | NFR-DD-1～7；US-917；本檔 §1 與 §6（RTM 本地子表於 SCG-5 回填） | （本檔；隨 Stage 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD、整合架構、NFR 對應 | Architecture §10.3、§11.1（工作樹已含本增量的新列 `si_decision_duplicate`，與實作同一 commit 進）、§12.1 L-14；P2b 的 W10、W11、W14、W15 | AgentConsole/docs/02_architecture/Architecture.md | sha256:c156549f339560acf5399f6477a54d725cf8a3ce54ac486f19b0c2858cc57b5b |
| SCG-1／技術選型與偏離清單 | ADR-001（Spring Boot 4.1、JDBC adapter 體例、PG18、不改 Flyway） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38 |
| SCG-3／API Spec、錯誤碼、Consumer Contract（本檔隨交 §8 增補；凍結值取含 §8 的工作樹現值） | 後繼契約 §0.3、§1.4、§4、§6、§8 | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md | sha256:32e60de75fda6171a452d28449567aa19e5ade8825e3fcc27e35edd795b92841（增補前 HEAD 值 sha256:9baaa069ca170486a5d147947568d1256c418d1ecef92ec0ccfa6854292e0f2d） |
| SCG-3／上位 TCS（W10、W11、W14、W15、W17、W21 的來源與其 AT） | TCS-SelfImprovingDecide-P2b：W10、W11、W14、W15、W17、W21 與 AT-935-5-*、AT-950-6-*、AT-933-1-*（現值，含勘誤 17） | AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingDecide-P2b-20261024.md | sha256:6acfe309f01d321f577201d5e53dcac7192ce60c493dd2d134e1582ac3d22b47 |

> 凍結摘要＝SA 以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算（原始位元組），並以 `git show HEAD:<路徑>` 另算一次對照：PRD、ADR-001 與 P2b TCS 的工作樹值與 HEAD 相同；API 契約取增補前的值（工作樹的 §8 增補不在內）；**`Architecture.md` 取工作樹現值**，它與 HEAD（`sha256:67cf0788acf19f7bd6cf1616b0657f2e8304feb7ca57aed7fee3b15aa09e4528`）不同，差在尚未 commit 的兩類修訂：§11.1 的表前說明句與新列 `si_decision_duplicate`（本增量；**須與實作同一 commit 進、不得先單獨 commit**，⚖2），以及 OBS-SI-321 的文件漂移訂正（目錄樹補一行、Tools 列的導覽項數）。PRD 已是 v0.12 且已 commit；P2b TCS 自 P2b 凍結後已有勘誤 1～17；PRD、Architecture 與 P2b TCS 因此與 P2b TCS 的〈增量追溯表〉所列 Stage-1 值不同，以本表（現值）為準。`spec-frozen` 前主控須重算，與該鍵 `show` 的輸出不符時以 `show` 為準並更正本表（`Architecture.md` 在實作 commit 前仍可能被編修，此格會漂移）。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（見〈AC 編號規則〉）；邊界、錯誤與負控 AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。測試類型為 Unit／Integration／Contract；本 Feature 沒有 E2E 類 AT（真全棧、真瀏覽器與掌舵者真機屬 §6.2 的 V 系列）。各 AT 的判定指令與測試檔見 §2 各 AT 標頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-1 | （backend）重送同一決定得 409 `si_decision_duplicate`：六個帶 digest 的動詞皆然，details 恰四鍵，零副作用 | ✅ | Integration | □ |
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-2 | （backend）不論先前那一列是否已入帳都擋，且重送閘不呼叫 Bridge | ✅ | Integration | □ |
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-E-1 | （backend）負控：不該被擋的請求照常受理——不同 dkind、不同 digest、不同 subject、obs-add、obs-close、validate | ✅ | Integration | □ |
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-E-2 | （backend）負控：補償刪列後同一決定可重送，結果不明而保留的列則擋住重送（已知邊界） | ✅ | Integration | □ |
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-E-3 | （backend）負控：重送閘排在授權、停用與輸入閘之後，不搶先回 409 | ✅ | Integration | □ |
| AC-951-1 | 決定重送閘：同一張卡的同一決定只能送出一次（W-D1） | AT-951-1-E-4 | （backend）負控：無 digest 的動詞不受重送閘——同一 RUN 的 `resume` 連送兩次皆 201，rollback 與 unblock 亦然 | ✅ | Integration | □ |
| AC-951-2 | dkind 的來源與兩個埠（W-D2） | AT-951-2-1 | （backend）九個決定動詞寫入後，對帳讀面每個 decide 項的 `dkind` 等於寫入的動詞，非 decide 項為 null | ✅ | Integration | □ |
| AC-951-2 | dkind 的來源與兩個埠（W-D2） | AT-951-2-E-1 | （backend）邊界：`findDecideAuditRefs` 依時間升冪、digest 為 null 一律不命中、dkind 區分大小寫，且不回非 decide 列 | ✅ | Integration | □ |
| AC-951-2 | dkind 的來源與兩個埠（W-D2） | AT-951-2-E-2 | （backend）負控：看不出 dkind 的列與非 decide 列一律為 null，不拖垮對帳讀面也不被重送閘誤認 | ✅ | Integration | □ |
| AC-951-3 | 對帳的取代判定（W-D3） | AT-951-3-1 | （backend）事故形狀：同一決定的四份稽核檔只有一份已入帳時，其餘三份的 `supersededBy` 指向它，`ingested` 仍為 false，鍵集合為十一鍵 | ✅ | Integration | □ |
| AC-951-3 | 對帳的取代判定（W-D3） | AT-951-3-E-1 | （backend）邊界：多個已入帳同伴取最早者、同刻取 auditRef 較小者，且判定不受 `limit` 限制 | ✅ | Integration | □ |
| AC-951-3 | 對帳的取代判定（W-D3） | AT-951-3-E-2 | （backend）負控：量不到時 `supersededBy` 與 `ingested` 一樣整欄為 null，不誤標被取代 | ✅ | Integration | □ |
| AC-951-3 | 對帳的取代判定（W-D3） | AT-951-3-E-3 | （backend）負控：不同 dkind、不同 digest、不同對象、皆未入帳、非 decide、無 digest 的動詞、dkind 為 null、取代者不在表內，一律不取代 | ✅ | Integration | □ |
| AC-951-4 | 對帳面板：被取代的稽核檔不再顯示為待入帳（W-D4） | AT-951-4-1 | （frontend）對帳面板：待入帳清單排除被取代列，被取代列進預設收合的群組，兩處都顯示 dkind，群組列沒有入帳指令鈕，面板內沒有刪除類控件 | ✅ | Integration | □ |
| AC-951-4 | 對帳面板：被取代的稽核檔不再顯示為待入帳（W-D4） | AT-951-4-2 | （frontend）純函式：`pendingWrites` 排除被取代列、`supersededWrites` 的篩選與排序、`decideKindLabel` 的對照 | ✅ | Unit | □ |
| AC-951-4 | 對帳面板：被取代的稽核檔不再顯示為待入帳（W-D4） | AT-951-4-E-1 | （frontend）負控：對帳量不到時不渲染被取代群組，也不顯示無待入帳 | ✅ | Integration | □ |
| AC-951-4 | 對帳面板：被取代的稽核檔不再顯示為待入帳（W-D4） | AT-951-4-E-2 | （frontend）負控：被取代筆數不影響無待入帳的判定，orphans 與一般待入帳仍各自生效 | ✅ | Integration | □ |
| AC-951-5 | 決定對話框：已送出待入帳的動詞停用，409 的原因明確（W-D5） | AT-951-5-1 | （frontend）決定對話框：已送出待入帳的同一決定使該動詞選項停用並顯示 `si-decide-dup`，且不發新的對帳請求 | ✅ | Integration | □ |
| AC-951-5 | 決定對話框：已送出待入帳的動詞停用，409 的原因明確（W-D5） | AT-951-5-2 | （frontend）後端回 409 `si_decision_duplicate` 時 toast 顯示既有稽核編號，對話框不關、連點只送一次 | ✅ | Integration | □ |
| AC-951-5 | 決定對話框：已送出待入帳的動詞停用，409 的原因明確（W-D5） | AT-951-5-3 | （frontend）純函式：`pendingDecision` 的比對規則、`siWriteErrorText` 的重送文案與 `SI_REASONS` 的六個鍵 | ✅ | Unit | □ |
| AC-951-5 | 決定對話框：已送出待入帳的動詞停用，409 的原因明確（W-D5） | AT-951-5-E-1 | （frontend）負控：無對帳快取或對帳量不到時不停用任何動詞，且對話框不發出任何新的 console-writes 請求 | ✅ | Integration | □ |
| AC-951-5 | 決定對話框：已送出待入帳的動詞停用，409 的原因明確（W-D5） | AT-951-5-E-2 | （frontend）負控：dkind、digest、對象、入帳狀態、取代狀態或 kind 不相符的列，以及無 digest 的動詞的待入帳列，都不使動詞停用 | ✅ | Integration | □ |
| AC-951-6 | 契約面與既有釘選同步（W-D6） | AT-951-6-1 | （backend）OpenAPI：`SiConsoleWriteItem` 恰十一鍵且必填集合不變，決定端點的 409 與說明載明新 reason，路徑與操作總數不變 | ✅ | Contract | □ |
| AC-951-6 | 契約面與既有釘選同步（W-D6） | AT-951-6-2 | （frontend）`schema.d.ts`：`SiConsoleWriteItem` 恰十一鍵，兩個新鍵選填且可為 null，SI 路徑與 operationId 不變 | ✅ | Contract | □ |
| AC-951-6 | 契約面與既有釘選同步（W-D6） | AT-951-6-E-1 | （backend）結構鎖：表仍只由一個配接器存取且 DML 仍三條，兩個埠的方法集合與 `findRecent` 的投影形狀同步 | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 6（本檔自增；PRD 的 AC-SI-33-2、AC-SI-35-5 為本增量所延伸的上位 AC，不新增）
- 已映射 AT 數: 25（正控 11、負控與邊界 E 類 14；負控不少於正控）
- 層別分佈: backend 15（正控 5、負控 10）；frontend 10（正控 6、負控 4）
- 映射覆蓋率: 100% （目標: 100%）

---
## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（形態：方括號內為 `AT_OK_` 接 AT 底線形去掉 `AT_` 前綴的部分；E 類的 `E` 保留）；Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，引號、撇號與全形引號 `「」` 一律不得出現在 Then、And 行（編譯器的引號字面抽取〔`sdd_to_playbook_adapter.py` 的 `_QUOTED_LITERAL`〕會把被框住的字誤收為期望輸出片段）；本檔的 Given、When 行同樣不用雙引號（JSON 以不帶引號的簡寫表示）。本 Feature 走 SDD session-only 路徑（backend 與 frontend；Bridge 與根層不動）：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-951-1-E-3` 的底線形是 `AT_951_1_E_3`）；每個 AT 的測試函式（Java 為方法）名稱須含其底線形；每個 AC 內數字序與 E 序各不超過 9，使 `-t`、`--tests` 的子字串比對不會誤收其他 AT。**同一 AT 的子情境**（Given 列舉者）一律以參數化或 `subTest` 實作並保留底線形，任一子情境失敗時，失敗訊息須指出是哪一個。**AT 內不引用其他 AT 的 ID**。**不得新增 skip 或 `it.skip`／`describe.skip`**：Docker 缺席視為環境壞、直接失敗。
>
> **每個 AT 區塊 8 行**：三行 `#` 標頭（AT ID；對應 AC、W-D 規則與 PRD 座標；測試類型、自動化工具、判定指令）、`Scenario:`（＝§1 的 AT 描述）、`Given`、`When`、`Then`、帶驗收字樣的 `And`。
>
> **判定指令的兩種形態**（標頭只列引數部分；PowerShell 不用裸 `cd`、讀 rc 先存變數再讀）：backend（Gradle；整合測試需 Docker）`gradlew test --tests "<類別全名>.<AT 底線形>*"`；frontend（vitest）`npx vitest run <檔> -t <AT 底線形>`。

```powershell
Push-Location AgentConsole\backend; .\gradlew.bat test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_1*"; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_1; Pop-Location
```

```bash
(cd AgentConsole/backend && ./gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_1*")
(cd AgentConsole/frontend && npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_1)
```

> **斷言簡寫**（本節各 AT 共用；資料與設施細節見 §5）：
>
> - **backend 側**：`SEAM`、`MINI`、`ADMIN` 沿 P2b TCS §5.4（`AbstractSiWriteIT`、`SiWriteSeam`、迷你 Bridge；`ADMIN`＝帳號 `admin`，在名單內、金鑰與權杖已設）；`D0`、`D1`、`UT1`、`UT2` 見 §5.1；`refs` 取用次數＝`refs.taken()`；`insertDecide`、`insertAudit` 見 §5.5；Viewer、Operator 與名單外 Admin 沿 `AbstractApiIT` 與 `adminAs`；表內列快照＝`writeRows()` 的逐列內容（含 body 位元組）。
> - **frontend 側**：`renderSi`、fetch 替身、`overrides` 沿 P2b TCS §5.5；`writeItem` 的擴充見 §5.6；ADMIN 開對話框的輔助沿 `SiDecideDialog.test.tsx` 既有的 `openProposalDecide`；PROP-SI-004 預設為 proposed／loop（動詞為核准、否決、退回，卡面 digest＝`D0`）。

```gherkin
# AT-951-1-1
# 對應 AC: AC-951-1（W-D1；PRD AC-SI-33-2 的增量）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）重送同一決定得 409 `si_decision_duplicate`：六個帶 digest 的動詞皆然，details 恰四鍵，零副作用
  Given `ADMIN` 在名單內、金鑰與權杖已設，`SEAM` 排入足量 ref；先各送一次六個帶 digest 的動詞（approve、reject、return、promote、decline-promote、ack-handoff；皆 `PROP-SI-004`、`D0`，表 M-D 的有效請求），六個皆 201；記下六列逐位元組快照、`MINI.si.writes` 筆數、`MINI.requests()` 筆數與 `refs` 取用次數
  When 對這六個動詞各以同一 subject、同一 digest 重送；reject、return、decline-promote 的 `reason` 與 `reasonClass` 改為不同的值
  Then 六個皆 409 且頂層 `reason` 為 `si_decision_duplicate`；`details.existingAuditRef` 等於各自首次收據的 `auditRef`；`details` 鍵集合恰為 `existingAuditRef`、`dkind`、`subject`、`digest8`，`digest8` 為 `d21ae6f5`、`dkind` 與 `subject` 等於請求；`message` 含 `請以對帳面板為準`；重送後六列快照逐位元組不變、`MINI.si.writes` 與 `MINI.requests()` 筆數不變、`refs` 取用次數不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_1]"
```
```gherkin
# AT-951-1-2
# 對應 AC: AC-951-1（W-D1）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）不論先前那一列是否已入帳都擋，且重送閘不呼叫 Bridge
  Given 先送一次 approve 得 201（列 R1）；`MINI` 的 events 夾具含 R1 的 `dec`（carrier 為 console，R1 已入帳）、observations 夾具為空；記下 `MINI.requests()` 與 `MINI.si.writes` 筆數、`refs` 取用次數與表內列數
  When 重送同一個 approve
  Then 409 且 `reason` 為 `si_decision_duplicate`、`details.existingAuditRef` 為 R1；表內仍恰一列；重送前後 `MINI.requests()` 完全相同（沒有任何 GET events、GET observations 或 POST）；`refs` 取用次數不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_2]"
```
```gherkin
# AT-951-1-E-1
# 對應 AC: AC-951-1（W-D1）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：不該被擋的請求照常受理——不同 dkind、不同 digest、不同 subject、obs-add、obs-close、validate
  Given 先送一次 approve（`PROP-SI-004`、`D0`）得 201
  When 依序送：(a) reject（同 subject、`D0`）；(b) approve（同 subject、`D1`）；(c) approve（subject 為 `PROP-SI-005`、`D0`）；(d) 同一本文的 obs-add 連送兩次；(e) 同一本文的 obs-close（`OBS-SI-005`）連送兩次；(f) validate 連送兩次
  Then (a) 到 (e) 共七個請求皆 201、(f) 兩個皆 200，沒有任何 409；表內列數為 8（含起手的 approve）；`MINI.si.writes` 恰 8 筆；失敗訊息須指出是哪一個子情境
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_E_1]"
```
```gherkin
# AT-951-1-E-2
# 對應 AC: AC-951-1（W-D1；W11 的補償與結果不明）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：補償刪列後同一決定可重送，結果不明而保留的列則擋住重送（已知邊界）
  Given 迷你 Bridge 對寫入先回 503 `si_unavailable`（確定未落檔）
  When 送 approve 得 503；把回覆還原後重送同一個 approve；另設讀取逾時（讀取上限縮到 1 秒、Bridge 延遲 3 秒）送 promote（`PROP-SI-004`、`D0`）；還原後重送同一個 promote
  Then 第一個 approve 得 503 且表內零列（補償刪列）；重送的 approve 得 201、表內恰一列且為第二次取的 ref；promote 的首次回應為 504 且 `details.outcomeUnknown` 為 true、列被保留（表內共二列）；promote 的重送得 409 `si_decision_duplicate`，`details.existingAuditRef` 為保留列的 ref，表內仍二列、`MINI.si.writes` 筆數與重送前相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_E_2]"
```
```gherkin
# AT-951-1-E-3
# 對應 AC: AC-951-1（W-D1；W10 的閘門序）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：重送閘排在授權、停用與輸入閘之後，不搶先回 409
  Given 表內已有一列 approve（`PROP-SI-004`、`D0`；先以 `ADMIN` 送出得 201）；記下表內列數與 `refs` 取用次數
  When 對同一決定再送，但分別以：(a) 名單外的 Admin；(b) Viewer；(c) Operator；(d) 無 token；(e) 把金鑰環設為空後的 `ADMIN`；(f) 把 Bridge 權杖設為空後的 `ADMIN`；(g) `ADMIN` 且本文多帶 `reason`
  Then 依序為 403 `si_write_forbidden`、403 `ACCESS_DENIED`、403 `ACCESS_DENIED`、401、503 `si_write_disabled`（`details.cause` 為 `audit_key_unset`）、503 `si_write_disabled`（`details.cause` 為 `bridge_token_unset`）、422 `invalid_request`（`violations[].field` 含 `reason`）；全程沒有 409；表內列數與 `refs` 取用次數不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_E_3]"
```
```gherkin
# AT-951-1-E-4
# 對應 AC: AC-951-1（W-D1；主控裁決 ⚖1）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_1_E_4*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：無 digest 的動詞不受重送閘——同一 RUN 的 `resume` 連送兩次皆 201，rollback 與 unblock 亦然
  Given `ADMIN`、`SEAM` 排入足量 ref；迷你 Bridge 對寫入回預設的 201
  When 依序送：(a) resume（`RUN-SI-001`）連送兩次，第二次的 `reason` 不同；(b) rollback（`PROP-SI-004`）連送兩次；(c) unblock（`PROP-SI-004`）連送兩次
  Then 六個請求皆 201，沒有任何 409；表內列數為 6、每次都取新 ref 且各自落檔（`MINI.si.writes` 恰 6 筆）；兩次 resume 的 `auditRef` 不同；失敗訊息須指出是哪一個子情境
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_1_E_4]"
```
```gherkin
# AT-951-2-1
# 對應 AC: AC-951-2（W-D2、W-D3 的 dkind 欄）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_2_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）九個決定動詞寫入後，對帳讀面每個 decide 項的 `dkind` 等於寫入的動詞，非 decide 項為 null
  Given `ADMIN`、`SEAM` 排入十一個 ref；迷你 Bridge 的 events 與 observations 夾具為空
  When 以 ADMIN 送九個動詞（表 M-D 的有效請求；resume 綁 `RUN-SI-001`、其餘綁 `PROP-SI-004`）各一次，另送一個 obs-add 與一個 obs-close，皆 201；再以 Viewer 呼叫 `GET /api/v1/si/console-writes`
  Then 回應 `items` 十一筆；九個 decide 項的 `dkind` 逐一等於該請求的 dkind（以 `auditRef` 對應收據）；帶 digest 的六種動詞 `digest` 為 `D0`、其餘三種為 null；obs-add 與 obs-close 兩項的 `dkind` 為 null 且鍵仍在；`body` 與 `mac` 兩個鍵不出現在回應任何位置
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_2_1]"
```
```gherkin
# AT-951-2-E-1
# 對應 AC: AC-951-2（W-D2；W-D1 所用的查詢語意）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_2_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）邊界：`findDecideAuditRefs` 依時間升冪、digest 為 null 一律不命中、dkind 區分大小寫，且不回非 decide 列
  Given 以 `insertDecide` 直接植入：同為 `PROP-SI-004`、`D0`、promote 的三列 X1（最早）、X2（auditRef 為 `UT1`）、X3（與 X2 同時刻、auditRef 為 `UT2`），插入次序為 X3、X1、X2；干擾列 Y1（同 subject、`D0`、approve）、Y2（同 subject、promote、`D1`）、Y3（`PROP-SI-005`、`D0`、promote）、以 `insertAudit` 植入的 Y4（kind 為 obs-add，body 內含 dkind 為 promote）；digest 為 null 的 rollback 兩列 Z1、Z2
  When 呼叫寫入埠 `findDecideAuditRefs`：(a) subject 為 `PROP-SI-004`、digest 為 `D0`、dkind 為 promote；(b) subject 為 `PROP-SI-004`、digest 為 null、dkind 為 rollback；(c) 同 (a) 但 dkind 為 reject；(d) 同 (a) 但 dkind 為 PROMOTE
  Then (a) 回 X1、X2、X3 三個 auditRef（依 time 升冪；X2 與 X3 同刻，依小寫 UUID 字串字典序 `UT1` 在前、`UT2` 在後，不是 `UUID.compareTo` 的順序）；(b) 回空清單（即使表內有 digest 為 null 的 rollback 列 Z1、Z2，無 digest 的動詞不提供比對）；(c) 與 (d) 回空清單；任何結果都不含 Y1 到 Y4 與 Z1、Z2
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_2_E_1]"
```
```gherkin
# AT-951-2-E-2
# 對應 AC: AC-951-2（W-D2）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWriteApiIT.AT_951_2_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：看不出 dkind 的列與非 decide 列一律為 null，不拖垮對帳讀面也不被重送閘誤認
  Given 植入四列：W1（以既有 `insertWrite` 植入的 decide；body 為只含 `fixture` 鍵的合法 JSON、沒有 dkind；subject `PROP-SI-004`、digest `D0`）、W2（以 `insertAudit` 植入的 obs-add；body 含 dkind 且值為 approve）、W3（以 `insertWrite` 植入的 obs-close）、W4（以 `insertDecide` 植入的 decide；subject 與 digest 同 W1；body 含 dkind 為 approve）；迷你 Bridge 的 events 與 observations 夾具為空
  When 以 Viewer 呼叫 `GET /api/v1/si/console-writes`；再呼叫寫入埠 `findDecideAuditRefs`（`PROP-SI-004`、`D0`、approve）
  Then 讀面 200 且 `reconcile.status` 為 ok；四列皆在 `items`；W1、W2、W3 的 `dkind` 為 null（W2 因 kind 非 decide 而為 null，不因 body 含鍵就取值）、W4 的 `dkind` 為 approve；`findDecideAuditRefs` 只回 W4（W1 沒有 dkind 而不命中）；`body` 與 `mac` 兩個鍵不出現在回應任何位置
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_2_E_2]"
```
```gherkin
# AT-951-3-1
# 對應 AC: AC-951-3（W-D3；PRD AC-SI-35-5 的增量）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_951_3_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）事故形狀：同一決定的四份稽核檔只有一份已入帳時，其餘三份的 `supersededBy` 指向它，`ingested` 仍為 false，鍵集合為十一鍵
  Given 以 `insertDecide` 植入同為 `PROP-SI-004`、`D0`、promote 的四列 R1（最早）、R2、R3、R4；迷你 Bridge 的 events 夾具含 R1 的 `dec`（carrier 為 console）、observations 夾具為空
  When 以 Viewer 呼叫 `GET /api/v1/si/console-writes`
  Then `reconcile.status` 為 ok；R2、R3、R4 的 `ingested` 皆為 false 且 `supersededBy` 皆等於 R1 的 auditRef；R1 的 `ingested` 為 true 且 `supersededBy` 為 null；每個 `items` 元素的鍵集合恰為 `auditRef`、`kind`、`dkind`、`user`、`role`、`time`、`subjectId`、`digest`、`keyId`、`ingested`、`supersededBy`；`orphans` 為空陣列；`body` 與 `mac` 兩個鍵不出現在回應任何位置
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_3_1]"
```
```gherkin
# AT-951-3-E-1
# 對應 AC: AC-951-3（W-D3；NFR-DD-4）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_951_3_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）邊界：多個已入帳同伴取最早者、同刻取 auditRef 較小者，且判定不受 `limit` 限制
  Given 植入三組：組 A 為已入帳的 A1（09:00:00Z）與 A2（10:00:00Z）和待入帳的 P1（11:00:00Z），皆為 `PROP-SI-004`、`D0`、approve；組 B 為同刻（09:00:00Z）已入帳的 B1（auditRef 為 `UT1`）、B2（auditRef 為 `UT2`；插入次序 B2 先）和待入帳的 P2（10:30:00Z），皆為 `PROP-SI-005`、`D0`、approve；events 夾具含 A1、A2、B1、B2 的 `dec`
  When 以 Viewer 呼叫預設的 `GET /api/v1/si/console-writes` 與 `GET /api/v1/si/console-writes?limit=1`
  Then 預設回應中 P1 的 `supersededBy` 為 A1（time 最早者，不是 A2）、P2 的 `supersededBy` 為 B1（同刻取字串序較小的 `UT1`，不是 `UUID.compareTo` 判較小的 `UT2`）；`?limit=1` 的回應只含 P1、`truncated` 為 true，且 P1 的 `supersededBy` 仍為 A1（判定不受 `limit` 影響）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_3_E_1]"
```
```gherkin
# AT-951-3-E-2
# 對應 AC: AC-951-3（W-D3；NFR-DD-3）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_951_3_E_2*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：量不到時 `supersededBy` 與 `ingested` 一樣整欄為 null，不誤標被取代
  Given 植入同為 `PROP-SI-004`、`D0`、promote 的四列 R1 到 R4（若對帳量得到，R1 會是已入帳、R2 到 R4 會是被取代者）
  When 分別讓迷你 Bridge 回 503 `si_unavailable`、讓連線被拒（設定的引擎位址指向無人監聽的埠）、讓讀取逾時（讀取上限縮到 1 秒、延遲 3 秒），各以 Viewer 呼叫一次讀面
  Then 三次皆 200 且 `reconcile.status` 為 NOT-EVALUABLE，`reconcile.reason` 依序為 `si_unavailable`、`bridge_unreachable`、`bridge_timeout`；每次 `items` 仍含四列，且每列的 `ingested` 與 `supersededBy` 皆為 null（鍵仍在，不是 false，也不是空）；`orphans` 為 null；表內各列逐位元組不變
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_3_E_2]"
```
```gherkin
# AT-951-3-E-3
# 對應 AC: AC-951-3（W-D3）
# 測試類型: Integration；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG + MiniBridge（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_951_3_E_3*"（cwd＝AgentConsole/backend）
Scenario: （backend）負控：不同 dkind、不同 digest、不同對象、皆未入帳、非 decide、無 digest 的動詞、dkind 為 null、取代者不在表內，一律不取代
  Given 對帳量得到；植入並以 events 夾具標示入帳狀態（編號皆取自真帳本已有者）：(a) 已入帳的 approve（`PROP-SI-004`、`D0`）與其下三列待入帳者：reject（同 subject、`D0`）、approve（同 subject、`D1`）、approve（`PROP-SI-005`、`D0`）；(b) 兩列皆未入帳的 approve（`PROP-SI-006`、`D0`）；(c) 一列待入帳的 obs-close（`OBS-SI-005`）與另一列已入帳的 obs-close（同對象）；(d) 兩列只含 `fixture` 鍵、沒有 dkind 的 decide（`PROP-SI-006`、`D1`），其中一列已入帳、一列待入帳；(e) 一列待入帳的 return（`PROP-SI-005`、`D0`），而帳本 events 有同 prop、同 digest、dkind 為 return 且 carrier 為 console 的 `dec`，其 `audit_ref` 不在表內；(f) 無 digest 的動詞各一組：resume（`RUN-SI-001`）與 rollback（`PROP-SI-004`）都是先一列已入帳、其後一列待入帳（同 subject、同 dkind、digest 皆為 null）
  When 以 Viewer 呼叫 `GET /api/v1/si/console-writes`
  Then 上列每一個待入帳列的 `ingested` 為 false 且 `supersededBy` 為 null（含 (f) 第二次合法的 resume 與 rollback）；每一個已入帳列的 `supersededBy` 為 null；全部 `items` 沒有任何一列的 `supersededBy` 非 null；(e) 那一筆帳本項出現在 `orphans`（不充當取代者）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_3_E_3]"
```
```gherkin
# AT-951-4-1
# 對應 AC: AC-951-4（W-D4；PRD AC-SI-35-5 的增量）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_951_4_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）對帳面板：待入帳清單排除被取代列，被取代列進預設收合的群組，兩處都顯示 dkind，群組列沒有入帳指令鈕，面板內沒有刪除類控件
  Given ADMIN 開 `/self-improving`；`console-writes` 替身回 ok，items 為：P1（decide、approve、`PROP-SI-004`、`ingested` 為 false、`supersededBy` 為 null）、P2（obs-add、`ingested` 為 false）、E1（decide、promote、`PROP-SI-006`、`ingested` 為 true）、S1 與 S2（decide、promote、`PROP-SI-006`、`ingested` 為 false、`supersededBy` 皆為 E1 的 auditRef，time 不同）
  When 開頁後先不操作，檢視對帳面板；再點 `si-superseded-toggle`
  Then `si-pending-list` 恰含 P1 與 P2 兩列且不含 S1、S2；P1 列的 `si-dkind-<auditRef>` 文字含 `核准` 與 `approve`、P2 列沒有 `si-dkind-<auditRef>`；`si-superseded-list` 存在且在 DOM 順序上位於 `si-pending-list` 之後，展開前 `si-superseded-toggle` 的 `aria-expanded` 為 false 且沒有任何 `si-superseded-<auditRef>` 列，標題文字為 `另有 2 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`；展開後 S1、S2 依 time 升冪出現，各列含 `si-dkind-<auditRef>`（`晉升 promote`）、`對象：PROP-SI-006`、time、auditRef 與 `取代者：<E1 的 auditRef>`，且列內沒有入帳指令鈕；對帳面板內（含展開後的群組）所有按鈕與連結的名稱與 `data-testid` 都不含 `刪除`、`移除`、`清除`、`delete`、`remove` 字樣（不分大小寫）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_4_1]"
```
```gherkin
# AT-951-4-2
# 對應 AC: AC-951-4（W-D4）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_951_4_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）純函式：`pendingWrites` 排除被取代列、`supersededWrites` 的篩選與排序、`decideKindLabel` 的對照
  Given 一組 `SiConsoleWrite` 樣本：待入帳者（`ingested` 為 false，`supersededBy` 為 null 或缺席）；被取代者（`ingested` 為 false，`supersededBy` 為字串）若干，time 亂序且含同刻；`ingested` 為 true 或 null 而 `supersededBy` 為字串者；`supersededBy` 為空字串者
  When 呼叫 `pendingWrites`、`supersededWrites`，並對九個 dkind、一個未知值與 null、undefined 呼叫 `decideKindLabel`
  Then `pendingWrites` 只回 `ingested` 為 false 且 `supersededBy` 為 null、缺席或空字串者，依 time 升冪、同刻依 auditRef；`supersededWrites` 只回 `ingested` 為 false 且 `supersededBy` 為非空字串者，排序規則同；`ingested` 為 true 或 null 的列兩者皆不回；兩函式皆不改動輸入、空清單回空；`decideKindLabel` 對 approve、reject、return、promote、decline-promote、rollback、unblock、resume、ack-handoff 依序回 `核准`、`否決`、`退回`、`晉升`、`不晉升`、`回滾`、`解除`、`恢復`、`轉交`，對未知值原樣回該值，對 null 與 undefined 回空字串
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_4_2]"
```
```gherkin
# AT-951-4-E-1
# 對應 AC: AC-951-4（W-D4；NFR-DD-3）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_951_4_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）負控：對帳量不到時不渲染被取代群組，也不顯示無待入帳
  Given ADMIN 開頁；`console-writes` 替身回 `reconcile.status` 為 NOT-EVALUABLE（reason 為 `bridge_timeout`）、`orphans` 為 null，items 含兩列：一列 decide（`ingested` 與 `supersededBy` 皆為 null）、一列刻意帶 `supersededBy` 為字串（契約外輸入，證明群組由對帳狀態而非資料控制）
  When 開頁並等待面板渲染完成
  Then 顯示 `si-reconcile-ne` 且文字含 `bridge_timeout`；沒有 `si-superseded-list`、沒有 `si-pending-list`、沒有 `si-writes-empty`；整頁文字不含 `已被取代`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_4_E_1]"
```
```gherkin
# AT-951-4-E-2
# 對應 AC: AC-951-4（W-D4）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_951_4_E_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）負控：被取代筆數不影響無待入帳的判定，orphans 與一般待入帳仍各自生效
  Given ADMIN 開頁；`console-writes` 替身回 ok，依情境：(a) items 只有三列被取代的待入帳列、orphans 為空；(b) 同 (a) 但 orphans 有一筆；(c) items 為一列一般待入帳加兩列被取代的待入帳列、orphans 為空
  When 各情境開頁並等待面板渲染完成
  Then (a) 有 `si-writes-empty`（文字含 `無待入帳`）、沒有 `si-pending-list`，群組標題為 `另有 3 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`；(b) 沒有 `si-writes-empty`、有 `si-write-alerts`，群組仍在；(c) `si-pending-list` 恰一列、沒有 `si-writes-empty`，群組標題為 `另有 2 筆已被取代（同一張卡的同一決定已由其他稽核檔入帳）`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_4_E_2]"
```
```gherkin
# AT-951-5-1
# 對應 AC: AC-951-5（W-D5）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）決定對話框：已送出待入帳的同一決定使該動詞選項停用並顯示 `si-decide-dup`，且不發新的對帳請求
  Given ADMIN 以 `renderSi` 開頁並切到提案分頁，兩個情境各做一次：(1) PROP-SI-004 為 proposed／loop，`console-writes` 替身有一列待入帳 decide（auditRef 為 X，subjectId `PROP-SI-004`、digest `D0`、dkind approve、`ingested` 為 false、`supersededBy` 為 null）；(2) PROP-SI-004 為 verified 且 verdict 為 NE（動詞為晉升（未驗採納）與不晉升），待入帳列為 promote（其餘同 (1)，auditRef 為 Y）；等對帳面板列出該列、並記下 `console-writes` 的請求次數之後才開對話框
  When 開啟決定對話框；情境 (1) 另選 reject、填理由與理由類別後送出
  Then 情境 (1) 的 approve 選項為 disabled、reject 與 return 不為 disabled；情境 (2) 的 promote 選項為 disabled、decline-promote 不為 disabled；`si-decide-dup` 存在且文字含 `已送出待入帳（稽核編號 X）`（情境 (2) 為 Y）；開啟對話框後、送出之前，`console-writes` 的請求次數與記下的相同（對話框沒有自己發讀取）；情境 (1) 的 reject 送出恰一個 POST 且本文 `dkind` 為 reject
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_5_1]"
```
```gherkin
# AT-951-5-2
# 對應 AC: AC-951-5（W-D5）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）後端回 409 `si_decision_duplicate` 時 toast 顯示既有稽核編號，對話框不關、連點只送一次
  Given ADMIN 開 PROP-SI-004（proposed／loop）的決定對話框並選 approve；`decide` 替身回 409，頂層 `reason` 為 `si_decision_duplicate`，`details` 為 `existingAuditRef`＝Y、`dkind` 為 approve、`subject` 為 `PROP-SI-004`、`digest8` 為 `d21ae6f5`
  When 連點送出鈕兩下
  Then 恰一個 POST；toast 文字含 `同一張卡的同一決定已送出（稽核編號 Y），待主機入帳，不需重送` 與 `si_decision_duplicate`；對話框仍開啟、表單未收起（沒有 `si-decide-result`）；送出鈕在請求結束後恢復可用
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_5_2]"
```
```gherkin
# AT-951-5-3
# 對應 AC: AC-951-5（W-D5；W-D6 的 reason 常數）
# 測試類型: Unit；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/domain/si.test.ts -t AT_951_5_3（cwd＝AgentConsole/frontend）
Scenario: （frontend）純函式：`pendingDecision` 的比對規則、`siWriteErrorText` 的重送文案與 `SI_REASONS` 的六個鍵
  Given `pendingDecision` 的表驅動樣本：命中者（kind 為 decide，subjectId、digest、dkind 皆相符且 digest 非 null，`ingested` 為 false，`supersededBy` 為 null、缺席、空字串各一個樣本），以及逐一破壞單一條件的樣本——kind 為 obs-add、subjectId 不同、digest 不同（字串對字串、字串對 null）、dkind 不同、列的 dkind 為 null 或缺席、`ingested` 為 true、`ingested` 為 null、`supersededBy` 為非空字串；另有目標 digest 為 null 的樣本（列的 digest 也為 null、其餘條件全符）、兩列同時命中且 time 不同的樣本；`siWriteErrorText` 的 409 樣本與其他錯誤樣本；`SI_REASONS`
  When 呼叫 `pendingDecision(items, { subject, digest, dkind })`、`siWriteErrorText` 並讀取 `SI_REASONS`
  Then 命中樣本回該列（含 `supersededBy` 為空字串者）；兩列同時命中回 time 最早者（同刻回 auditRef 較小者）；目標 digest 為 null 一律回 null（無 digest 的動詞不受重複判定）；每個被破壞單一條件的樣本回 null；`siWriteErrorText` 對 409 且 reason 為 `si_decision_duplicate`、`details.existingAuditRef` 為字串者，文字含 `同一張卡的同一決定已送出（稽核編號 <ref>），待主機入帳，不需重送` 與 reason 逐字；缺 `existingAuditRef` 時不含括號段、仍含 `同一張卡的同一決定已送出` 與 reason；409 `si_audit_exists` 的文字與既有行為逐字相同；`SI_REASONS` 的鍵依序恰為 `UNAVAILABLE`、`NOT_FOUND`、`WRITE_DISABLED`、`WRITE_FORBIDDEN`、`AUDIT_EXISTS`、`DECISION_DUPLICATE`，六個值都在 Architecture §11.1 的 SI reason 表內，且表中 `si_` 起頭的列恰為這六個
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_5_3]"
```
```gherkin
# AT-951-5-E-1
# 對應 AC: AC-951-5（W-D5；主控裁決 ⚖5；NFR-DD-3）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_E_1（cwd＝AgentConsole/frontend）
Scenario: （frontend）負控：無對帳快取或對帳量不到時不停用任何動詞，且對話框不發出任何新的 console-writes 請求
  Given ADMIN 開 PROP-SI-004（proposed／loop）的頁面；`console-writes` 替身依情境：(a) 回 503 `si_unavailable`（快取沒有資料）；(b) 延遲到斷言之後才回（快取沒有資料）；(c) 回 `reconcile.status` 為 NOT-EVALUABLE、`orphans` 為 null，items 含一列 decide（approve、`ingested` 為 null、`supersededBy` 為 null）；`decide` 替身回 409 `si_decision_duplicate`
  When 各情境先記下全部請求的序列，再開啟決定對話框、選 approve 並送出
  Then 三個情境皆：沒有任何動詞選項為 disabled、沒有 `si-decide-dup`；開啟對話框到送出完成之間，請求序列只多一個決定 POST（`console-writes` 的次數不變，對話框不發讀取）；approve 可被選取且送出得到恰一個 POST（以後端 409 為準），toast 顯示 409 的文字；對話框不關閉
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_5_E_1]"
```
```gherkin
# AT-951-5-E-2
# 對應 AC: AC-951-5（W-D5；主控裁決 ⚖1）
# 測試類型: Integration；自動化工具: vitest + Testing Library（jsdom）+ fetch 替身（hermetic）；判定指令: npx vitest run components/domain/si/SiDecideDialog.test.tsx -t AT_951_5_E_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）負控：dkind、digest、對象、入帳狀態、取代狀態或 kind 不相符的列，以及無 digest 的動詞的待入帳列，都不使動詞停用
  Given ADMIN 開決定對話框，三個情境各做一次：(1) PROP-SI-004（proposed／loop，卡面 digest 為 `D0`），`console-writes` 替身回 ok、items 為七列都不該命中的列——promote 列（dkind 與本卡三個動詞皆不同，待入帳）、approve 列但 digest 為 `D1`、approve 列但 subjectId 為 `PROP-SI-005`、approve 列且 `ingested` 為 true、approve 列且 `supersededBy` 為非空字串、obs-add 列、dkind 為 null 的 decide 列（subject 與 digest 相同）；(2) PROP-SI-004 為 promoted，待入帳列為 rollback（digest 為 null、dkind 為 rollback、`ingested` 為 false、`supersededBy` 為 null）；(3) 狀態橫幅暫停 `RUN-SI-001`，待入帳列為 resume（subjectId 為 `RUN-SI-001`、digest 為 null、`ingested` 為 false）
  When 等對帳面板渲染完成後開啟對話框
  Then 情境 (1) 的 approve、reject、return 三個選項皆不為 disabled；情境 (2) 的 rollback 與情境 (3) 的 resume 選項不為 disabled；三個情境都沒有 `si-decide-dup`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_5_E_2]"
```
```gherkin
# AT-951-6-1
# 對應 AC: AC-951-6（W-D6）
# 測試類型: Contract；自動化工具: JUnit 5 + Spring Boot Test + Testcontainers PG（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_951_6_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）OpenAPI：`SiConsoleWriteItem` 恰十一鍵且必填集合不變，決定端點的 409 與說明載明新 reason，路徑與操作總數不變
  Given 啟動中的 backend 提供的 `/v3/api-docs`
  When 讀 `components.schemas.SiConsoleWriteItem`、三個寫入 POST 的 409 回應說明，以及 `postSiDecide` 的 operation 說明
  Then `SiConsoleWriteItem.properties` 的鍵集合恰為 `auditRef`、`kind`、`dkind`、`user`、`role`、`time`、`subjectId`、`digest`、`keyId`、`ingested`、`supersededBy`；`required` 恰為 `auditRef`、`kind`、`user`、`role`、`time`、`keyId`（`dkind` 與 `supersededBy` 非必填）；decide 的 409 說明與 operation 說明都含 `si_decision_duplicate`，`post /api/v1/si/observations` 與 `post /api/v1/si/observations/{id}/close` 的 409 說明不含它；既有的路徑總數與操作總數釘選不變（本鍵不新增路徑）、decide 的回應狀態碼集合與既有相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_6_1]"
```
```gherkin
# AT-951-6-2
# 對應 AC: AC-951-6（W-D6）
# 測試類型: Contract；自動化工具: vitest（jsdom；hermetic）；判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_951_6_2（cwd＝AgentConsole/frontend）
Scenario: （frontend）`schema.d.ts`：`SiConsoleWriteItem` 恰十一鍵，兩個新鍵選填且可為 null，SI 路徑與 operationId 不變
  Given 已入庫的 `lib/api/schema.d.ts`
  When 取出 `SiConsoleWriteItem` 型別區塊（以 `SiConsoleWriteItem: {` 起、下一個同縮排的結尾止）
  Then 區塊內的鍵恰為十一個且與 backend 契約同名；`dkind` 與 `supersededBy` 皆為選填且型別為字串或 null；`auditRef`、`kind`、`user`、`role`、`time`、`keyId` 仍為必填；`schema.d.ts` 中以 `/api/v1/si/` 起頭的路徑鍵與其 operationId 與重產前相同；`SiConsoleWrite` 型別帶兩個新鍵的物件字面值由 `tsc --noEmit` 檢查成立（V4 承擔）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_6_2]"
```
```gherkin
# AT-951-6-E-1
# 對應 AC: AC-951-6（W-D2、W-D6）
# 測試類型: Unit；自動化工具: JUnit 5 + ArchUnit 與原始碼掃描（hermetic）；判定指令: gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest.AT_951_6_E_1*"（cwd＝AgentConsole/backend）
Scenario: （backend）結構鎖：表仍只由一個配接器存取且 DML 仍三條，兩個埠的方法集合與 `findRecent` 的投影形狀同步
  Given 主程式原始碼（去除註解後）、`SiConsoleWriteRepository` 與 `SiConsoleWriteQueries` 兩個埠、`SiConsoleWriteSummary`
  When 跑結構鎖
  Then 提及 `si_console_writes` 的非註解原始碼仍只有 `SiConsoleWriteAdapter`；該配接器的 DML 敘述總數仍為三（INSERT 一、UPDATE 一且只設 `subject_id`、DELETE 一且依 `audit_ref`），新增的兩個查詢都是 SELECT；寫入埠的方法集合恰為 `insert`、`deleteByAuditRef`、`findDecideAuditRefs`；對帳讀埠的方法集合恰為 `findRecent`、`findExistingAuditRefs`、`findObsAddRefsWithoutSubject`、`fillSubjectId`、`findDecideRows`；`findRecent` 的 SQL 不含 `select *`，select 清單除 dkind 的表達式外恰為既有八欄（`audit_ref`、`kind`、`user`、`role`、`time`、`subject_id`、`digest`、`key_id`）；`SiConsoleWriteSummary` 的記錄元件含 `dkind`、不含 `body` 與 `mac`；寫入埠仍只有 `SiConsoleWriteService` 使用、讀埠仍只有 `SiReconcileService` 使用；防反空轉：掃描確實讀到 `SiConsoleWriteAdapter.java` 與兩個埠的原始碼（皆非空）、確實看得到三條 DML 與 `findRecent`、`findDecideAuditRefs`、`findDecideRows` 的 SQL 字串（各非空），且 `findDecideAuditRefs`、`findDecideRows` 兩個方法名確實同時出現在埠介面與配接器
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_951_6_E_1]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-951-4-2 | AC-951-4 | frontend | lib/domain/si.test.ts（it 標題 AT_951_4_2…） |
| AT-951-5-3 | AC-951-5 | frontend | lib/domain/si.test.ts（it 標題 AT_951_5_3…） |
| AT-951-6-E-1 | AC-951-6 | backend | SiReadOnlyArchTest.AT_951_6_E_1_* |

### 3.2 Integration Tests

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-951-1-1 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_1_* |
| AT-951-1-2 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_2_* |
| AT-951-1-E-1 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_E_1_* |
| AT-951-1-E-2 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_E_2_* |
| AT-951-1-E-3 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_E_3_* |
| AT-951-1-E-4 | AC-951-1 | backend | SiConsoleWriteApiIT.AT_951_1_E_4_* |
| AT-951-2-1 | AC-951-2 | backend | SiConsoleWriteApiIT.AT_951_2_1_* |
| AT-951-2-E-1 | AC-951-2 | backend | SiConsoleWriteApiIT.AT_951_2_E_1_* |
| AT-951-2-E-2 | AC-951-2 | backend | SiConsoleWriteApiIT.AT_951_2_E_2_* |
| AT-951-3-1 | AC-951-3 | backend | SiConsoleWritesReadApiIT.AT_951_3_1_* |
| AT-951-3-E-1 | AC-951-3 | backend | SiConsoleWritesReadApiIT.AT_951_3_E_1_* |
| AT-951-3-E-2 | AC-951-3 | backend | SiConsoleWritesReadApiIT.AT_951_3_E_2_* |
| AT-951-3-E-3 | AC-951-3 | backend | SiConsoleWritesReadApiIT.AT_951_3_E_3_* |
| AT-951-4-1 | AC-951-4 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_951_4_1…） |
| AT-951-4-E-1 | AC-951-4 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_951_4_E_1…） |
| AT-951-4-E-2 | AC-951-4 | frontend | components/domain/si/SiView.test.tsx（it 標題 AT_951_4_E_2…） |
| AT-951-5-1 | AC-951-5 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_951_5_1…） |
| AT-951-5-2 | AC-951-5 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_951_5_2…） |
| AT-951-5-E-1 | AC-951-5 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_951_5_E_1…） |
| AT-951-5-E-2 | AC-951-5 | frontend | components/domain/si/SiDecideDialog.test.tsx（it 標題 AT_951_5_E_2…） |

> 對帳面板的 AT 沿 P2b 的先例住在既有的 `SiView.test.tsx`（`SiWritesPanel.test.tsx` 不存在；開發 agent 若另開該檔屬允許的新增，AT 底線形與判定指令照改）。

### 3.3 Contract Tests（靜態與契約面檢查）

| AT ID | 對應 AC | 層 | 測試方法 |
|-------|---------|----|---------|
| AT-951-6-1 | AC-951-6 | backend | OpenApiIT.AT_951_6_1_* |
| AT-951-6-2 | AC-951-6 | frontend | lib/api/si.endpoints.test.ts（it 標題 AT_951_6_2…） |

### 3.4 E2E Tests

（無 AT；真全棧、真瀏覽器與掌舵者真機屬 §6.2 的 V 系列，結果寫進 SCG-4 報告。）

---

## 4. 邊界與錯誤測試規格

容錯與邊界情境已併入各 AC 的 E 類 AT 與帶負控的 AT（`AT-<NNN>-<Y>-E-<n>`，列於 §1）；本節依場景分類登記，並登記刻意不做、已知邊界與需同步的既有測試。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 重送閘（帶 digest 的六個動詞） | AT-951-1-1 | 同一決定重送得 409，details 恰四鍵，零副作用 | 六個帶 digest 的動詞各送兩次（重送時 reason 與 reasonClass 改變） | 409 `si_decision_duplicate`；details 四鍵；列、Bridge 請求、ref 取用皆不變 |
| 入帳與否 | AT-951-1-2 | 先前列已入帳仍擋，閘不掃描 Bridge | events 夾具含首次的 `dec` | 409；Bridge 零新增請求 |
| 不該擋的請求 | AT-951-1-E-1 | 不同 dkind、digest、subject、obs-add、obs-close、validate | 七個請求加兩個 validate | 全 201 或 200，表內 8 列 |
| 無 digest 的動詞 | AT-951-1-E-4 | resume、rollback、unblock 不受重送閘（主控裁決 ⚖1） | 各連送兩次 | 全 201、表內 6 列、無 409 |
| 補償與結果不明 | AT-951-1-E-2 | 補償刪列後可重送；結果不明保留列擋住重送 | Bridge 503；讀取逾時 | 重送 201；重送 409 且 Bridge 不增請求 |
| 閘門序 | AT-951-1-E-3 | 重送閘在授權、停用、輸入閘之後 | 名單外 Admin、Viewer、Operator、無 token、金鑰空、權杖空、本文違規 | 403、403、403、401、503、503、422；無 409 |
| dkind 的暴露 | AT-951-2-1 | 九個動詞經 API 寫入後讀面的 dkind 逐一相符 | 九個動詞加 obs-add、obs-close | decide 項 dkind 相符；非 decide 項為 null |
| 查詢語意 | AT-951-2-E-1 | 升冪、同刻（字串序）、digest 為 null 不命中、大小寫、非 decide 列 | 三列同決定加干擾列與 rollback 列 | 回清單順序固定；null 一律空清單；PROMOTE 不命中 |
| 看不出 dkind | AT-951-2-E-2 | 無 dkind 的 decide 列、body 含 dkind 的非 decide 列 | 只含 `fixture` 鍵的 body | dkind 為 null、不 500、不被閘誤認 |
| 取代判定 | AT-951-3-1 | 事故形狀 | 四列同決定、一列已入帳 | 其餘列 `supersededBy` 指向已入帳者；十一鍵；ingested 仍 false |
| 取代者選取與分頁 | AT-951-3-E-1 | 最早者、同刻取 auditRef 字串序較小者（UT1 與 UT2 跨 0x7f 與 0x80，不是 Java 的 UUID 比較序）、與 `limit` 無關 | 兩組已入帳同伴加待入帳列；`limit=1` | 取 A1、B1；`limit=1` 結果相同 |
| 量不到 | AT-951-3-E-2、AT-951-4-E-1 | NOT-EVALUABLE 時整欄 null、面板不渲染群組 | Bridge 503、連線被拒、逾時 | `supersededBy` 與 `ingested` 皆 null；無群組、無無待入帳 |
| 不取代 | AT-951-3-E-3 | 八種不該取代的情形 | 不同 dkind、digest、對象；皆未入帳；非 decide；dkind 為 null；orphan；無 digest 的動詞 | 全部 `supersededBy` 為 null |
| 面板分群 | AT-951-4-1、AT-951-4-2 | 待入帳與被取代分流、dkind 顯示、群組內無刪除類控件、純函式篩選與排序 | 五列樣本；亂序與同刻樣本 | 清單排除被取代列；群組預設收合、標題與列內容固定、群組內無刪除類控件 |
| 無待入帳判定 | AT-951-4-E-2 | 被取代筆數不影響判定 | 三種情境 | 無待入帳顯示與否只看待入帳與 orphans |
| 對話框停用 | AT-951-5-1、AT-951-5-E-2 | 命中則停用；不相符的列與無 digest 的動詞不停用 | 兩個命中情境；七列不命中加兩個無 digest 情境 | 命中動詞 disabled 並顯示 `si-decide-dup`；其餘不受影響；請求次數不變 |
| 409 的呈現 | AT-951-5-2、AT-951-5-3 | toast 文案、連點只送一次、純函式 | 409 加 details | 文案含既有稽核編號與 reason；對話框不關 |
| 快取不可用 | AT-951-5-E-1 | 無對帳快取或量不到都不停用，且不發新請求 | 三個情境 | 不停用；請求序列只多一個決定 POST；仍可送出由後端把關 |
| 契約面 | AT-951-6-1、AT-951-6-2、AT-951-6-E-1 | OpenAPI、schema.d.ts、結構鎖 | `/v3/api-docs`、入庫檔、原始碼 | 十一鍵；新 reason 載明；方法集合同步 |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| 刪除 UI 或刪稽核列、稽核檔的 API | 稽核紀錄本身不刪（稽核軌跡；PRD AC-SI-35-3 無刪除能力）；多餘的三份由 W-D3 判為被取代 | 掌舵者要求清理稽核目錄或對帳表 |
| 以資料庫唯一約束或鎖使重送閘原子化 | 需 Flyway（本鍵不改 Flyway 與觸發器）；殘餘由 W-D3 事後標示承接 | 閘上線後對帳頁仍出現同一決定的 2 筆以上待入帳且皆未被取代 |
| 讓重送閘看帳本入帳與否（掃描 Bridge） | 閘須零 Bridge 呼叫；與「不論是否已入帳都擋」（帶 digest 的動詞）一致 | 帶 digest 的決定因先前列已入帳而被擋的合法重送出現 |
| 為無 digest 的動詞（rollback、unblock、resume）加重送防護 | 沒有卡面 digest 可綁；`resume` 可因新的壞窗對同一 RUN 再度暫停；重送合法性由主機端 decide 的前提態判（主控裁決 ⚖1） | 掌舵者對這三個動詞連送後，對帳頁出現 2 筆以上待入帳（OBS-SI-348 同型） |
| Bridge、稽核檔與根層 CLI 的任何改動 | Bridge 不解 `body`、只落檔（P2b W3）；入帳面歸根層 | 稽核目錄檔數影響主機端 `status` 耗時 |
| 改 `console-writes` 的分頁與 scan 上限 | 不是本事故的成因 | 沿 P2b 已知邊界 4 的再開症狀 |
| 把被取代列的 `ingested` 改成 true 或另造第三種狀態 | 不冒充已入帳：入帳以帳本列為憑 | 面板需要依 `ingested` 以外的欄位篩選 |
| 對 `body` 非合法 JSON 的 decide 列做容錯（例如 PG 的 `pg_input_is_valid`） | backend 只寫合法 JSON，人為植入屬資料毀損；加容錯會讓壞資料靜默變成不擋、不被取代 | 出現 body 非 JSON 的 decide 列而使對帳讀面或重送閘回 500 |

**已知邊界（誠實登記）**

1. **結果不明與補償失敗的保留列也擋重送**（P2b 已知邊界 3、13 的延伸；僅限帶 digest 的動詞）：讀取逾時、送出後連線重設、2xx 本文無法解析而保留的列，以及補償刪除失敗留下的幽靈列，都會讓同一決定被 409 擋下；P2b 原有的補救（掌舵者重送新 ref）對這六個動詞自本鍵起不再成立，補救改為主機端 DBA 依 PRD §9.3 補償刪列。API 訊息提示請以對帳面板為準（主控裁決 ⚖1）。
2. **無 digest 的動詞不受重送閘、不參與取代判定、對話框也不停用**（主控裁決 ⚖1；後兩者為 SA 延伸，⚖10）：rollback、unblock、resume 沒有卡面 digest 可綁，重送合法性由主機端 decide 的前提態判；連送會各落一份稽核檔，主機入帳一份後其餘在對帳面板仍顯示為待入帳（OBS-SI-348 同型症狀對這三個動詞仍可能發生）；換得的是同一 RUN 再度暫停後第二次合法的 resume 不會被擋、被隱藏或被停用（根層 `fold.py` 的 suspended 判定只看 resume 事件序號之後是否又有連續壞窗）。
3. **重送閘非原子**（檢查後才 INSERT，且不改 Flyway 故無唯一約束）：兩個並行請求可各落一列；前端以 ref 同步擋連點，殘餘由 W-D3 事後標示承接（其中一份入帳後另一份判為被取代）。
4. **閘不看帳號**：另一位名單內的 Admin 也被擋（K=1 的現況無影響）。
5. **取代者必須是本表的列**：帳本有 carrier 為 console 而表內沒有的項（orphan）不充當取代者；兩列都未入帳時互不取代，直到其中一份入帳。
6. **被取代的稽核檔仍在稽核目錄**：主機端若手動入帳被取代的那一份，根層 CLI 以前提不符等碼拒收；Console 不防（入帳在主機端、pull 模式）。
7. **dkind 取自 body 的 JSON**：看不出 dkind 的 decide 列（歷史或夾具列）視為不可比（不擋、不被取代，⚖6）；body 非合法 JSON 的 decide 列會使讀面與閘的查詢出錯（刻意不做 7）。
8. **對話框只讀既有的對帳快取**：快取缺席（議題中心沒有對帳面板；面板的查詢載入中或失敗）或對帳量不到時不停用，只靠 backend 409 擋；快取可能略舊，同樣以 409 為準；議題中心因此零改動、零額外請求（主控裁決 ⚖5）。
9. **被取代群組只涵蓋回應 `items`**（最新 `limit` 筆）內的列；`truncated` 為 true 時沿 P2b 勘誤 16 的說明。
10. **macOS 全部未驗**：AT 與 V 系列只在 Windows 與 Linux（CI）實跑。
11. **promote 的兩個後式同鍵、digest 不含 verdict**：一般晉升與晉升後式（`unverifiedAck`，verdict 為 NE）都是 dkind 為 promote、同一 digest，視為同一決定——先送其一再送另一個會被擋；且卡面 digest 只由卡面內容算出（根層 `props.py` 的 `compute_digest`，15 個鍵，不含 verdict），故 verdict 改變（例：NE 重驗為 PASS）而 digest 不變時，先前未入帳的 promote 仍擋住新的 promote（補救同已知邊界 1）。

**需同步的既有測試**（本鍵使下列既有測試的前提或精確釘選改變；開發 agent 須同步修改，只增不減，不得為使其變綠而改弱斷言）：

1. `backend/.../architecture/SiReadOnlyArchTest.AT_950_8_2_*`：`repositoryMethods` 釘選由恰 `insert`、`deleteByAuditRef` 改為再加 `findDecideAuditRefs`；`queryMethods` 釘選再加 `findDecideRows`；「兩個埠的方法只有 insert、deleteByAuditRef、fillSubjectId 與 find 起頭者」「DML 敘述總數 3」「唯一提及表名者」三條不變；類別 Javadoc 補一句。
2. `backend/.../web/SiConsoleWriteApiIT.AT_935_4_1_*`：`admin` 與 `ops_admin` 兩個帳號對同一 subject、digest、dkind 各送 approve，第二個帳號會被新閘擋（閘不看帳號）；改為兩個帳號送不同動詞（或不同 digest），「名單內 Admin 皆放行」與表內 6 列的前提不變，Admin 大小寫那一例不得改弱。
3. `backend/.../web/SiConsoleWriteApiIT.AT_950_5_E_2_*`：四次 `approve()` 依序為成功、Bridge 403、Bridge 503、逾時；成功與逾時各保留一列，成功之後的三次都會被新閘擋在 Bridge 之前（403 與 503 是補償刪列的失敗，補償後本可重送，但它們排在成功之後）；改法二擇一，使每次都到達 Bridge：(i) 先送兩次補償刪列的失敗、再送成功，逾時改用不同動詞或不同 digest；(ii) 四次改為互不相同的動詞。`MINI.si.writes` 恰 4 筆與權杖標頭的斷言不減。
4. `backend/.../web/SiConsoleWritesReadApiIT.AT_935_5_1_*`：`items` 元素鍵集合由九鍵改十一鍵（加 `dkind`、`supersededBy`）；其餘斷言不變。該 AT 的 decIn 與 decOut 同 subject、同 digest 且 body 無 dkind，依 ⚖6 其 `supersededBy` 必須為 null（鎖住 null 對 null 的誤判）。
5. `backend/.../web/SiConsoleWritesReadApiIT.AT_935_5_E_2_*`：五個量不到情境的逐列斷言，在 `ingested` 為 null 之外加 `supersededBy` 為 null（只增）。
6. `backend/.../support/AbstractSiWriteIT`：新增通用的 `insertAudit(auditRef, kind, subjectId, digest, bodyJson, timeIso)` 與 decide 的便捷包裝 `insertDecide(auditRef, subjectId, digest, dkind, timeIso)`（§5.5）；`insertWrite` 與其他助手不變。
7. `backend/.../config/OpenApiIT`：新增 AT-951-6-1 的測試方法；`AT_950_10_1_*` 的路徑、操作、狀態碼集合釘選一個不改（本鍵不新增路徑、decide 的狀態碼集合原已含 409）；類別 Javadoc 補一句。
8. `frontend/lib/domain/si.test.ts::AT_932_1_7`：「SI_REASONS 恰五個鍵」改為六個鍵（依序加 `DECISION_DUPLICATE`；原五鍵與順序不變）。
9. `frontend/lib/domain/si.test.ts::AT_940_5_1`：第一個 it 的「恰為五個鍵」與 `Object.keys(SI_REASONS).sort()` 加 `DECISION_DUPLICATE`；與 Architecture §11.1 表的對拍：新列由主控加在工作樹，並與實作同一 commit 進、不得先單獨 commit（⚖2）；開發期間該 AT 在第六鍵加上之前為預期紅、加上之後轉綠，不得改弱；其餘各 it 不變。
10. `frontend/lib/domain/si.test.ts::AT_950_9_2` 的 `pendingWrites` 子測：既有斷言一個不改，另加「被取代列被排除」的斷言（只增）。
11. `frontend/tests/helpers/si.tsx`：`writeItem` 增選填的 `dkind`、`digest`、`supersededBy`（預設 null，既有呼叫的行為不變）。
12. `frontend/components/domain/si/SiView.test.tsx` 的「沒有刪除 UI」AT（`AT_935_3_2`）：`READ_ONLY_TESTIDS` 封閉集合加入 `si-superseded-toggle`（群組展開鈕是 `si-` 前綴的按鈕，未列名會落入「未列名的 si- 按鈕」判準而紅）；`FORBIDDEN_NAME`（刪除、移除、清除、delete、remove）的掃描不放寬，並對群組展開鈕的名稱與 testid 生效；終段「對帳面板只有入帳指令展開鈕」的斷言只在該測試的資料沒有被取代列時成立，夾具若擴充含被取代列，須同步改為含群組展開鈕（只增不減）。

**已逐一核對、不需改（續綠）**：backend 的 `SiConsoleWriteApiIT` 其餘各 AT（九個不同 dkind 的端對端、單次決定、obs-add 與 obs-close 的端對端、DELETE／PUT／PATCH 矩陣、資格拒收矩陣、閘門序、回應形態、補償矩陣——每次都補償刪列，補償後可重送，故同一請求連送六次不受閘；結果不明與重送新 ref 兩個 AT 只送 obs-add）；`SiConsoleWritesReadApiIT` 的 `AT_933_2_E_1`、`AT_935_5_2`、`AT_935_5_E_1`、`AT_935_5_E_3`（夾具列 body 為只含 `fixture` 鍵的合法 JSON，dkind 為 null）；`SiConsoleWritesMigrationIT`、`SchemaMigrationIT`、`V5UpgradeMigrationIT`（表結構與版本不變）。frontend 的 `SiView.test.tsx` 其餘 AT（`AT_935_5_3`、`AT_935_5_E_4` 等，其資料沒有被取代列；「沒有刪除 UI」那一個見需同步第 12 項）、`SiDecideDialog.test.tsx` 既有各 AT（對話框只讀快取、不發新請求，其請求序列不變）、`si.static.test.ts`（對話框若新增讀取型 hook 的 import，不在 `WRITE_HOOK` 判準內，命名見 W-D6 (f) ③）、`lib/api/endpoints.test.ts`、`lib/nav/registry.test.ts`；議題中心的 `IssuesView.test.tsx`（含 `AT_IC_10_1_1` 的精確請求序列）、`components/domain/issues/tests/issues.fixtures.ts`、`issues.static.test.ts` 因對話框不發新請求而零改動、續綠（此即主控 ⚖5 裁決的回歸鎖）。

不需改、但對新碼自動生效的機械鎖：`ArchitectureRulesTest` 的 A1～A6 與 JPA、WEB 規則（新增的埠方法住 application 層，不依賴 adapter 或 infrastructure）、`frontend/tests/design-rules.test.ts`（新 UI 無陰影與漸層、無寫死色碼、只用 Lucide 且無 emoji、無 `outline-none`、無 `dark:`）、`AgentConsole/CLAUDE.md` 的文件閘（新文件不得有測試摘要字樣與 4 位數字同行）。

---

## 5. 測試資料規格

### 5.1 事故資料與常數

- `D0`＝`sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c`（P2b TCS §5.3；狀態 A 的 PROP-SI-004 卡面 digest），`digest8(D0)`＝`d21ae6f5`；`D1`＝`sha256:` 接 64 個小寫 `b`，`digest8(D1)`＝`bbbbbbbb`。
- 同刻 tie-break 用的 UUID 字面（跨首位元組 0x7f 與 0x80，鎖住 Java `UUID.compareTo` 以有號 long 比較的陷阱）：`UT1`＝`7fffffff-0000-4000-8000-000000000001`（字串序與 PostgreSQL uuid 序較小）、`UT2`＝`80000000-0000-4000-8000-000000000002`（較大；`UUID.compareTo` 卻判它較小）。AT-951-2-E-1 的 X2、X3 與 AT-951-3-E-1 的 B1、B2 各以 UT1、UT2 充當。
- 測試資料的 PROP、RUN、OBS 編號一律取自真帳本已有者：`PROP-SI-004`、`PROP-SI-005`、`PROP-SI-006`、`RUN-SI-001`、`OBS-SI-005`（NFR-DD-6 (6) 不開例外；不得另造未存在的編號）。
- 事故（真機；只供 V1 比對，AT 不得依賴真資料）：PROP-SI-006 的 promote（晉升，未驗採納），稽核檔 auditRef 前 8 碼 e550a510（已入帳為 DEC-SI-006）、a2c9903f、ea60faf6、f5e78bb3，帳號 admin。
- `decideKindLabel` 對照（canonical，不分卡面情境）：approve＝核准、reject＝否決、return＝退回、promote＝晉升、decline-promote＝不晉升、rollback＝回滾、unblock＝解除、resume＝恢復、ack-handoff＝轉交；未知值原樣回傳。

### 5.2 表 M-G：重送閘的比對矩陣（W-D1）

| 情境 | subject | digest | dkind | 先前列的狀態 | 結果 |
|------|---------|--------|-------|--------------|------|
| 1 完全相同 | `PROP-SI-004` | `D0` | approve | 未入帳 | 409 |
| 2 完全相同 | 同上 | 同上 | 同上 | 已入帳 | 409 |
| 3 完全相同 | 同上 | 同上 | 同上 | 結果不明而保留 | 409 |
| 4 完全相同 | 同上 | 同上 | 同上 | 已補償刪除 | 201 |
| 5 dkind 不同 | 同上 | `D0` | reject | 任何 | 201 |
| 6 digest 不同 | 同上 | `D1` | approve | 任何 | 201 |
| 7 subject 不同 | `PROP-SI-005` | `D0` | approve | 任何 | 201 |
| 8 無 digest 的動詞 | `PROP-SI-004`（resume 為 `RUN-SI-001`） | null | rollback、unblock、resume | 任何（先前列同 subject、同 dkind） | **201（不受此閘；主控裁決 ⚖1）** |
| 9 帳號不同 | 同情境 1 | 同上 | 同上 | 另一帳號送出 | 409（閘不看帳號） |
| 10 非 decide | 任意 | 無 | obs-add、obs-close、validate | 同本文先前列 | 201 或 200（不經此閘） |

受閘者只有帶 digest 的六個動詞（approve、reject、return、promote、decline-promote、ack-handoff；表 M-D 實際有 digest 者）；其餘三個 decide 動詞與 obs-add、obs-close、validate 不經此閘。

### 5.3 表 M-R：`items[]` 的十一個鍵（W-D3）

| 鍵 | 型別 | 值與規則 |
|----|------|----------|
| `auditRef` | string（uuid） | 稽核編號 |
| `kind` | string | decide、obs-add、obs-close |
| `dkind` | string 或 null | decide 列＝動詞（九個之一，原樣透傳不設 enum）；其餘與看不出者＝null |
| `user`、`role`、`time` | string | 沿既有（`time` 以 UTC 表示） |
| `subjectId` | string 或 null | 沿既有 |
| `digest` | string 或 null | 只有六種決定動詞有 |
| `keyId` | string | 金鑰 sha256 前 8 碼 |
| `ingested` | boolean 或 null | 量不到＝null |
| `supersededBy` | string（uuid）或 null | W-D3；量不到、非 decide、已入帳、無同伴＝null |

十一鍵恆在，不含 `body`、`mac`；比對不看鍵序。

### 5.4 表 M-S：取代判定真值表（W-D3）

| 列的 kind | ingested | dkind、subjectId、digest | 同伴（另一列、已入帳、同 subject、同 dkind、同 digest） | `supersededBy` |
|-----------|----------|--------------------|------------------------------------------------------------|----------------|
| decide | false | 皆非 null | 有一個 | 該同伴的 auditRef |
| decide | false | 皆非 null | 有多個 | time 最早者的 auditRef（同刻取 auditRef 較小者） |
| decide | false | 皆非 null | 沒有（含：同伴不在表內的 orphan、同伴也未入帳、同伴 dkind 或 digest 或 subject 不同） | null |
| decide | false | 任一為 null（含無 digest 的 rollback、unblock、resume） | 任何 | null |
| decide | true | 任何 | 任何 | null |
| decide | null（量不到） | 任何 | 任何 | null |
| obs-add、obs-close | 任何 | 任何 | 任何 | null |

### 5.5 backend 測試設施（沿 P2b TCS §5.4；只增不改）

- `AbstractSiWriteIT` 新增兩個助手：通用的 `insertAudit(auditRef, kind, subjectId, digest, bodyJson, timeIso)`（欄位沿 `insertWrite`：user 為 `admin`、role 為 `ADMIN`、key_id 為 `f076edf0`、mac 為 64 個 0，差別是 `kind` 與 `body` 由呼叫端給，供 obs-add 的 body 含 dkind 這類樣本），以及 decide 的便捷包裝 `insertDecide(auditRef, subjectId, digest, dkind, timeIso)`（kind 為 decide、body 為含 `dkind` 的合法 JSON 物件，只含 dkind 一鍵即可）。`insertWrite` 的 body 仍為只含 `fixture` 鍵的合法 JSON（dkind 為 null 的列由它植入）。
- events 夾具：`event(...)` 回傳的 Map 再以 `put` 加 `digest`、`dkind` 鍵，供 AT-951-3-E-3 的 orphan 取代者案例；其餘沿既有。
- 每個測試開始前清表與重設夾具的既有 `@BeforeEach` 不變。

### 5.6 frontend 測試設施（沿 P2b TCS §5.5；只增不改）

`tests/helpers/si.tsx` 的 `writeItem({ auditRef, kind, subjectId?, ingested?, time?, dkind?, digest?, supersededBy? })`：新增的三個選填鍵預設為 null（`digest` 沿既有預設 null）；其餘預設值不變，既有呼叫的結果逐位元組相同。`console-writes` 的預設回應不變（已對帳、無待入帳）。議題中心的測試與夾具零改動（對話框不發新請求，§4）。

### 5.7 hermetic 環境與允許變更的檔案集合

全部 AT 只用 Testcontainers 的 PG18、迷你 Bridge、jsdom 與 `fetch` 替身；不連外網、不寫真帳本、不碰真 `~/.autosdd/`。測試結束必關迷你 Bridge 與回收資源。

| 區 | 允許新增或修改的路徑（相對 monorepo 根；與 D1～D6 逐項一致） |
|----|--------------------------------------------------------------|
| backend 主程式 | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下：`application/service/SiConsoleWriteService.java`、`application/service/SiReconcileService.java`、`adapter/out/persistence/SiConsoleWriteAdapter.java`、`application/port/out/SiConsoleWriteRepository.java`、`application/port/out/SiConsoleWriteQueries.java`、`domain/model/si/SiConsoleWriteSummary.java`、`application/port/in/SiReconcileUseCase.java`、`adapter/in/web/dto/SiConsoleWritesResponse.java`、`domain/exception/ErrorReasons.java`、`adapter/in/web/ErrorResponseDocumentation.java`、`adapter/in/web/SiController.java`（僅註解與 `@Operation` 說明文字，⚖8）、`application/port/in/SiWriteUseCase.java`、`application/port/out/SiAuditRefSource.java`（兩者僅 Javadoc：「閘門序…→執行」「重送一律新 auditRef」「一個請求恰取一次」已過時） |
| backend 測試 | `AgentConsole/backend/src/test/java/com/aisdlc/console/` 下：`adapter/in/web/SiConsoleWriteApiIT.java`、`adapter/in/web/SiConsoleWritesReadApiIT.java`、`architecture/SiReadOnlyArchTest.java`、`infrastructure/config/OpenApiIT.java`、`support/AbstractSiWriteIT.java` |
| frontend 主程式 | `AgentConsole/frontend/components/domain/si/SiWritesPanel.tsx`、`components/domain/si/SiDecideDialog.tsx`、`components/domain/si/siParts.tsx`（若需要）；`lib/domain/si.ts`；`lib/api/schema.d.ts`（重產）；`lib/api/types.ts`（若需要；`SiConsoleWrite` 為 `schema.d.ts` 的別名，通常不需改）；`lib/api/queries.ts`（僅在需要新增唯讀的快取 hook 時；`useSiConsoleWrites` 的行為不變） |
| frontend 測試 | `AgentConsole/frontend/components/domain/si/SiView.test.tsx`、`components/domain/si/SiDecideDialog.test.tsx`、`lib/domain/si.test.ts`、`lib/api/si.endpoints.test.ts`、`tests/helpers/si.tsx`（議題中心的測試與夾具不在允許集合內，零改動） |
| 不屬開發 agent（主控代做） | `AgentConsole/docs/02_architecture/Architecture.md` §11.1 一列（⚖2；凍結檔的純文件修訂，**與實作同一 commit 進、不得先單獨 commit**）；RTM 本地子表（依 DEF-200-576 體例另立新檔 `AgentConsole/docs/06_quality/RTM-SelfImprovingDecideDedupe-20261031.md`，並於 `RTM.md` 補一節存根；F-903、US-917、AC-951-1～6 與各 AT 列）；SCG-4 報告；`AgentConsole/frontend/lib/help/self-improving.ts`（對帳面板與決定對話框的頁面說明，與 UI 實作同 commit）；凍結上位的勘誤（P2b TCS、P1b TCS；§7.2 第 8 項，並 refreeze `agentconsole-si-decide`、`agentconsole-si-mirror`）；契約 `API_Contract_SelfImproving_P2b.md` §8 已由 SA 棒隨本檔落檔（實作與其不符處，開發 agent 以純文字回報差異，由主控改檔）；其餘一律不動：`AgentConsole/engine-bridge/`、根層 `tools/`、`AgentConsole/docker-compose*.yml`、`.github/`、`.claude/`、Flyway `db/migration/`、凍結檔與既有 TCS（上列勘誤除外） |

---

## 6. RTM 連結確認

### 6.1 追溯

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD AC-SI-33-2、AC-SI-35-5（本增量延伸其對帳語意）→ F-903 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-903 → US-917 | ☑ 已映射 |
| US-917 → 本檔 6 個 AC | ☑ 已映射（FRD-lite） |
| 6 個 AC → 本檔全部 25 個 AT | ☑ 已映射（本文件 §1） |
| OBS-SI-348 的再開症狀（對帳頁同一卡同一決定出現 2 筆以上待入帳稽核檔）→ V1、V2 與 AT-951-1-*、AT-951-3-* | ☑ 已映射；真機操作不由 AT 充當 |
| 契約增補（`API_Contract_SelfImproving_P2b.md` §8） | ☑ 已由 SA 棒隨本檔落檔（主控於 SCG-5 與實作同 commit 收齊；存在與範圍由 V5 核對） |
| `Architecture.md` §11.1 的新 reason 列（⚖2） | □ 主控已加在工作樹；與實作同一 commit 進，不得先單獨 commit |
| 頁面說明 `frontend/lib/help/self-improving.ts`（對帳面板與決定對話框） | □ 主控代做，與 UI 實作同 commit |
| 凍結上位的字面勘誤（§7.2 第 8 項） | □ 主控於實作 commit 寫勘誤並 refreeze `agentconsole-si-decide`、`agentconsole-si-mirror` |
| RTM 本地子表（新檔 `RTM-SelfImprovingDecideDedupe-20261031.md`，DEF-200-576 體例；`RTM.md` 補一節存根）的 F-903、US-917、AC-951-1～6 與各 AT 列 | □ 主控於 SCG-5 回填（本地子表，不計入 §2 總列數） |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由雲端 agentconsole-ci 的 backend 與 frontend job 一併執行；Bridge 與根層未動，`paths` 無需變更） |

**行為規則 → AT 對映**（W-D1～W-D6 各至少被一個正控與一個負控 AT 釘住）

| 規則 | 內容 | 釘住它的 AT |
|------|------|-------------|
| W-D1 | 重送閘（位置、比對、409、零副作用、補償互動、閘門序、無 digest 動詞的豁免） | AT-951-1-1、AT-951-1-2、AT-951-1-E-1、AT-951-1-E-2、AT-951-1-E-3、AT-951-1-E-4、AT-951-2-E-1 |
| W-D2 | dkind 的來源與兩個埠 | AT-951-2-1、AT-951-2-E-1、AT-951-2-E-2、AT-951-6-E-1 |
| W-D3 | 對帳取代判定 | AT-951-3-1、AT-951-3-E-1、AT-951-3-E-2、AT-951-3-E-3 |
| W-D4 | 對帳面板 | AT-951-4-1、AT-951-4-2、AT-951-4-E-1、AT-951-4-E-2 |
| W-D5 | 決定對話框與 reason 常數 | AT-951-5-1、AT-951-5-2、AT-951-5-3、AT-951-5-E-1、AT-951-5-E-2 |
| W-D6 | 契約面與既有釘選同步 | AT-951-6-1、AT-951-6-2、AT-951-6-E-1、AT-951-5-3 |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註；未驗者如實標「未驗」，構造情境不得充當）

| 編號 | 實查項 | 步驟與指令要點 | 通過判準與證據 | 再開症狀 |
|------|--------|----------------|----------------|----------|
| V1 | 真機對帳頁：事故三筆進「已被取代」群組（掌舵者真機） | 以含本鍵的 build 重啟 backend（DB 無 migration）；admin 開 `/self-improving` 的對帳面板，並以 admin token 呼叫 `GET /api/v1/si/console-writes?limit=100` | auditRef 前 8 碼 a2c9903f、ea60faf6、f5e78bb3 三列的 `ingested` 為 false 且 `supersededBy` 為 e550a510 該列的完整 auditRef；e550a510 該列 `ingested` 為 true；待入帳清單不含這三筆；群組標題為 `另有 3 筆已被取代…` 且預設收合，展開後三列各有 `取代者：<e550a510 的完整編號>`；API 輸出逐字貼入加掌舵者截圖或 sid 與 line | 三筆仍在待入帳、`supersededBy` 指向錯誤的列，或被取代列的 `ingested` 被改成 true |
| V2 | 真機重送閘與對話框（掌舵者真機；不得構造） | 在真後端以 admin 找一張當下真的可下決定的待決卡（帶 digest 的動詞；resume、rollback、unblock 不受閘，不在此驗），下一個決定後重開對話框；另以 API 直呼同一請求（同 digest） | 該動詞選項停用並顯示 `已送出待入帳（稽核編號 …）`；API 直呼得 409 `si_decision_duplicate`、`details.existingAuditRef` 等於該次收據、表內列數與稽核目錄檔數前後相同；**若當下沒有可下決定的卡，如實標「未驗」，不得為了驗收新建 PROP 或偽造卡** | 選項仍可選，或 409 之後仍落了新稽核檔 |
| V3 | `schema.d.ts` 重產可重現 | backend 完成後依 P2b 勘誤 9 的作法重產（拋棄式 IT 倒 `/v3/api-docs`，餵 `node scripts/gen-api.mjs`），與入庫檔比對；`OpenApiIT` 親跑 | 重產結果與入庫檔逐位元組相同；`OpenApiIT` 的 rc 為 0（讀 rc 先存變數再讀） | 重產後有差異（入庫檔與後端漂移） |
| V4 | 閘門全綠 | backend：`gradlew clean build`（Checkstyle、JaCoCo 80%、ArchUnit）；frontend：`npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`（覆蓋率 70%）含 `design-rules.test.ts` | 各指令 rc 為 0；輸出逐字貼入 SCG-4 報告 | 任一閘門紅 |
| V5 | 範圍守衛與文件連動 | `git diff --name-only` 與 `git status --porcelain`（含未追蹤檔）對照 §5.7；`git diff` 對 `API_Contract_SelfImproving_P2b.md` 只有檔尾追加；契約 §8 含 §1.4 新 409 列、`items[]` 十一鍵、`dkind` 來源、`supersededBy` 判定；`Architecture.md` §11.1、RTM 本地子表、`lib/help/self-improving.ts` 與凍結上位勘誤的主控項 | 只出現允許集合；零 Bridge、零根層 `tools/`、零 Flyway、零 `.claude/`；契約前文無任何刪除行；缺列即紅 | 出現允許集合外的檔；或契約缺項、Architecture 缺列 |
| V6 | 平台與雲端 CI | Windows 實跑全部 AT 與 V1～V3；push 後 `agentconsole-ci` 的 backend 與 frontend job；macOS 標「未驗」 | `gh run list` 現查的 run 與結論；報告載明各平台狀態 | 雲端紅而本機綠（平台差異） |

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 10；主控先行裁決 1～11 已裁，不在此列。⚖1～⚖5 已由主控於 2026-10-31 裁決，下列保留其結果與再開症狀；⚖6～⚖10 為本檔類推或 SA 延伸，已採預設；⚖10 由主控於 2026-10-31 QA 二審後確認採納）

| 編號 | 問題（上位文件未定、內部矛盾或不可測處） | 本檔已採用的預設 | 替代與再開症狀 |
|------|----------------------------------------|------------------|----------------|
| ⚖ 1 | W-D1 原稿「不論是否已入帳都擋」會永久擋下無 digest 的動詞（`resume` 可因新的壞窗對同一 RUN 再度暫停）與結果不明而保留的列 | **主控裁決（採替代案的一半）**：rollback、unblock、resume 不受重送閘（沒有卡面 digest 可綁，合法性由主機端前提態判），閘只管帶 digest 的六個動詞；結果不明而保留的列照擋（補救＝DBA 依 PRD §9.3 補償刪列；409 訊息提示看對帳面板）；AT-951-1-E-4 釘住 resume 連送兩次皆 201、AT-951-1-E-2 釘住保留列擋重送；同一豁免一併用於取代判定與對話框見 ⚖10 | 再開症狀：掌舵者對這三個動詞連送後對帳頁出現 2 筆以上待入帳；或結果不明的保留列使帶 digest 的決定無法重送 |
| ⚖ 2 | `SI_REASONS` 加第六鍵與凍結檔 `Architecture.md` §11.1 的對拍：`lib/domain/si.test.ts` 的 AT_940_5_1 解析該表並要求 `si_` 起頭的列恰等於 `SI_REASONS` 的值；Architecture 是凍結檔，且該表標題寫「Bridge 產生」而本 reason 由 backend 產生 | **主控裁決（採預設）**：主控已把 §11.1 新列（`si_decision_duplicate`，來源寫 backend，標題隨之訂正）加在工作樹，並將於實作 commit 同時 refreeze 相關鍵；**新列與實作同一 commit 進，不得先單獨 commit**（單獨 commit 會讓已提交的 HEAD 上 AT_940_5_1 變紅）；開發期間工作樹已有新列而 `SI_REASONS` 尚無第六鍵時，該 AT 為預期紅（§4 第 9 項），加上第六鍵後轉綠；§5.7 列為不屬開發 agent | 再開症狀：AT_940_5_1 紅 |
| ⚖ 3 | `details.digest8` 在 digest 為 null 時任務書寫「為 null」，與凍結契約 P3-6 §0.2（`details` 不輸出 null；`Map.copyOf` 遇 null 會 NPE）衝突 | **主控裁決（採預設）**：digest8 為 null 時缺席、不輸出 null。因 ⚖1 的豁免，受閘動詞的 digest 恆非 null，此情形不可由 API 觸及，故只作防禦性規格（W-D1）；AT-951-1-1 釘住四鍵恆在 | 再開症狀：前端或文件期待 `digest8` 為 null |
| ⚖ 4 | 取代判定的範圍：任務書未說取自回應 `items` 還是整張表 | **主控裁決（採預設）**：取整張表的 decide 列、與 `limit` 無關；`SiConsoleWriteQueries` 多一個唯讀方法 `findDecideRows()`，ArchUnit 方法集合同步（AT-951-6-E-1、§4 第 1 項） | 再開症狀：`limit` 改變時 `supersededBy` 跟著變 |
| ⚖ 5 | 決定對話框在議題中心也掛載；原稿以 `useSiConsoleWrites()` 取資料會讓議題中心開對話框時多一個 GET，並使 `IssuesView.test` 的精確請求序列斷言變紅 | **主控裁決（採替代案）**：對話框只讀既有的對帳快取、不發新 GET；快取缺席或對帳量不到＝不停用、交給 backend 409；議題中心的測試與夾具不動（零改動續綠即回歸鎖）；AT-951-5-E-1 釘住無快取時不停用且請求序列不變 | 再開症狀：掌舵者在議題中心重送同一決定而未被 UI 擋下（只靠 409 與 toast） |
| ⚖ 6 | dkind 為 null 的 decide 列（body 無 dkind 的歷史或夾具列）是否參與重送閘與取代判定：若 null 等於 null，既有夾具（AT_935_5_1 的 decIn 與 decOut 同 subject 同 digest）會被誤判為同一決定 | 不參與：閘的 dkind 參數非 null 故永不命中這類列；取代判定要求 `dkind` 與 `subjectId` 皆非 null（寧可不擋、不隱藏）；AT-951-2-E-2、AT-951-3-E-3 釘住 | 替代：null 對 null 視為相同（會誤隱藏）。再開症狀：待入帳列被誤判為已被取代 |
| ⚖ 7 | 重送閘非原子：不改 Flyway 就沒有唯一約束，檢查與 INSERT 之間有競爭窗口 | 接受（已知邊界 3）；前端以 ref 同步擋連點，殘餘由 W-D3 事後標示承接 | 替代：交易內取諮詢鎖或加部分唯一索引（需 Flyway，與任務書的範圍裁決衝突）。再開症狀：閘上線後仍出現同一決定的 2 筆以上待入帳 |
| ⚖ 8 | 本檔補定的名稱與範圍（測試需要穩定入口）：`findDecideRows`、`decideKindLabel`、`pendingDecision`、`supersededWrites`、`si-dkind-<auditRef>`、`si-superseded-toggle`、`si-superseded-<auditRef>`、`si-superseded-by-<auditRef>`；`SiController.java`、`SiWriteUseCase.java` 與 `SiAuditRefSource.java` 於 §5.7 比任務書多列（僅註解、Javadoc 與 `@Operation` 說明文字，避免閘門序與重送敘述過時） | 本檔釘住；`ErrorResponseDocumentation` 另載明 decide 的 409 | 替代：完全照任務書清單。再開症狀：實作者改名使 AT 對不上 |
| ⚖ 9 | 409 文案：backend message 中性（先前列可能已入帳），前端 toast 依任務書逐字（待主機入帳，不需重送）並接 `describeError` 的原文以保留 reason 與 traceId | 如左；AT-951-5-2、AT-951-5-3 釘住 | 替代：toast 只留任務書那句。再開症狀：掌舵者覺得 toast 太長，或在已入帳情形下被誤導（同 ⚖1） |
| ⚖ 10 | **SA 延伸，主控已於 2026-10-31 確認採納**：⚖1 的裁決只明說「重送閘」。無 digest 的動詞若仍參與取代判定，第二次合法的 resume 會被先前已入帳的 resume 誤判為被取代而從待入帳消失；若對話框仍對它們停用，一列從未入帳的待入帳列會讓 UI 永久擋住該動詞 | 同一豁免一併用於 W-D3（`supersededBy` 恆為 null）與 W-D5（`pendingDecision` 對 digest 為 null 的目標一律回 null）；AT-951-3-E-3 與 AT-951-5-E-2 釘住；代價見已知邊界 2 | 替代：取代判定與對話框仍涵蓋無 digest 的動詞（UX 較防呆，但有前述兩個風險）。再開症狀：待入帳的合法 resume 被標為已被取代，或對話框永久停用某個無 digest 的動詞 |

### 7.2 SA 對上位文件與既有碼的發現（供主控處理；本檔未改任何凍結檔）

1. **PRD AC-SI-35-5 的字面**：「已送出而尚無帳本列＝待入帳」。本增量下，被取代列仍是 `ingested=false`、仍在 `items`，只是面板改列入已被取代群組；PRD 文字不改（凍結），建議下次 PRD 修訂時補一句「同一決定已由其他稽核檔入帳者標為被取代」（走 T1）。
2. **P2b 已知邊界 3 的補救（重送新 ref）自本鍵起對六個帶 digest 的 decide 不再成立**（見 ⚖1）；對 rollback、unblock、resume（不受重送閘）、obs-add 與 obs-close 仍成立；逐處字面見本節第 8 項。
3. **既有 backend IT 的前提衝突**：`AT_935_4_1` 與 `AT_950_5_E_2` 以同一決定連送多次為前提，與新閘衝突（§4 第 2、3 項）。
4. **議題中心嵌入 `SiDecideDialog`**（`IssuesView.tsx`）：依主控 ⚖5 裁決，對話框只讀快取、不發新請求，議題中心的測試與夾具零改動；代價是議題中心重送同一決定時 UI 不會先擋（只靠 backend 409 與 toast，已知邊界 8）。
5. **`OpenApiIT` 現值**：路徑與操作總數的釘選現為 77 與 89（P2b 當時為 71 與 81，其後由其他鍵演進）；本鍵不新增路徑，故不改這兩個數；`SiConsoleWriteItem` 的 schema 鍵集合目前沒有任何釘選，本檔新增（AT-951-6-1）。
6. **`SiConsoleWriteRepository` 的 Javadoc**（「只有兩個動作」）與 `SiReadOnlyArchTest.AT_950_8_2`（「寫入埠恰兩個方法」）的前提隨 W-D2 改變；把唯讀查詢放在寫入埠是主控裁決，結構鎖以方法名前綴 `find` 保護它只讀。
7. **事故三份稽核檔是真實資料**：不刪、不改，由 W-D3 自然判定（V1 驗收）。
8. **凍結上位文件的字面需勘誤**（本檔不改凍結檔；由主控在實作 commit 寫勘誤並 refreeze `agentconsole-si-decide`、`agentconsole-si-mirror`）：(a) P2b TCS 的 W14 與 AT-935-5-1：`items[]` 鍵集合恰為九個鍵 → 十一鍵（加 `dkind`、`supersededBy`）；(b) P2b TCS 的 AT-950-9-2：`SI_REASONS` 恰含該表五個 reason → 六個；(c) P1b TCS 的 AT-940-5-1（勘誤 19：`si_` 起頭的全部列〔5 值〕）→ 6 值；(d) SA 另補：P2b TCS 的 W11（重送一律新 `auditRef`）、已知邊界 3（補救是掌舵者重送，新 audit_ref）與 ⚖7（每次新 ref），以及 P2b 契約 §0.2、§0.4 第 3 點的同類敘述，對六個帶 digest 的決定動詞自本鍵起不再成立（重送在取 ref 之前即被 409 擋下；對 rollback、unblock、resume、obs-add、obs-close 仍成立），契約側已由本契約 §8.2 補述。

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC（6 個 AC 皆至少一個 AT） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 可單跑（backend `--tests`、frontend `-t`）；每個 AT 的驗收字樣逐字出現在最終回覆 | □ |
| 負向測試覆蓋 | 每個 AC 至少一個負向或負控 AT；負控數不少於正控數（14 對 11）；每條 W-D 規則皆有正控與負控 | □ |
| 邊界值測試 | 無 digest 的動詞不受閘、同刻取 auditRef 字串序較小者（跨 0x7f 與 0x80）、`limit=1`、dkind 區分大小寫、空 dkind、量不到、無對帳快取、重送閘的閘門序、補償刪列與結果不明保留列皆有對照 | □ |
| 零副作用與不冒充 | 409 前後列數、Bridge 請求數、ref 取用數不變；被取代列的 `ingested` 仍為 false | □ |
| 測試資料規格完整 | 資料來源明確（§5）；夾具可重現；ID 引用只用真帳本已存在者 | □ |
| 出口與 V 系列 | V1～V6 有結果與證據；V1、V2 為掌舵者真機；未驗者如實標記 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| # | 日期 | 位置 | 原文（摘） | 訂正 | 依據 |
|---|------|------|-----------|------|------|
| 1 | 2026-10-31 | AT-951-1-E-1 | 「`MINI.si.writes` 恰 8 筆」 | 迷你 Bridge 的 `writes` 也記錄預檢（含 `:validate`）：(a)～(e) 七個寫入後恰 8 筆（含起手的 approve）、(f) 兩次預檢後為 10 筆；訂正為「不含預檢恰 8 筆（含預檢為 10）」，斷言依此釘兩個值 | Developer 交卷勘誤候選 1 |
| 2 | 2026-10-31 | §5.6 `writeItem` | 「既有呼叫的結果逐位元組相同」 | `writeItem` 現恆輸出 `dkind`、`supersededBy` 兩個 null 鍵（與十一鍵契約一致），JSON 不再逐位元組相同；訂正為「既有呼叫的斷言結果不變」 | Developer 交卷勘誤候選 2 |
| 3 | 2026-10-31 | W-D1（`digest8` 省略句）；W-D3（`d.auditRef` 不等於 `r.auditRef`） | 兩條防禦性條文 | 事實記錄：digest 為 null 的動詞在閘前即放行，`digest8` 省略句無可達路徑；r 待入帳而 d 已入帳，兩者必為不同列，該條件恆成立；兩者皆不改碼、字面保留 | Developer 交卷勘誤候選 3 |
| 4 | 2026-10-31 | §5.7 frontend 測試列；§3.2 註記 | §3.2 允許開發 agent 另開 `SiWritesPanel.test.tsx`，§5.7 允許集合未列該檔 | §5.7 frontend 測試列補「`components/domain/si/SiWritesPanel.test.tsx`（若新增）」，使 V5 的範圍守衛與 §3.2 一致；本輪未新增該檔，對帳面板的 AT 仍住 `SiView.test.tsx` | RTM 棒疑義一 |
