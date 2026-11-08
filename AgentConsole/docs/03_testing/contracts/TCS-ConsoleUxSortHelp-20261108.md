# Test Contract Specification — Console 資料列表排序與每頁說明文案改寫
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole 前端各列表元件、每頁說明登記表、後端專案與匯入列表端點；上位文件含 Console PRD §0.10、Architecture §5.5 與 §12.1 L-UX-1、API_Contract_P3-6、TCS-PageHelp、TCS-IssueCenter、TCS-SysAdminBackup）的單一 Feature；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ConsoleUxSortHelp-20261108.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-909 |
| **Feature 名稱** | Console 資料列表預設依識別欄排序、表頭可點排序；每頁「本頁說明」改為國高中程度的導覽文案，並以機械鎖守住可讀性 |
| **User Story** | US-929（規格棒已對 `AgentConsole/docs/06_quality/RTM.md` 與全 repo `*.md` 以 Grep 確認 F-909、US-929、AC-963 皆未被使用，不撞號） |
| **PRD 對應節** | `docs/01_requirements/Agent_ConsoleUI_PRD.md` §0.10（FR-UX-01、FR-UX-02；D-UX-1、D-UX-2） |
| **建立日期** | 2026-11-08 |
| **輸入快照** | HEAD＝`ca9a23f1bfe90152c9db2f312459a614aeb1ca8a`；上位檔 digest 見〈增量追溯表〉（規格棒以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算；Console PRD §0.10 與 Architecture §5.5／§12.1 L-UX-1 已在工作樹，與本檔同一 commit 進） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝Architect＋SA 合一規格棒，實作者＝四個派工包的開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-console-ux-sort-help`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug console-ux-sort-help`） |
| **AT 總數** | 56（正控 47、負控與邊界 9；AC 9 個，其中 AC-963-9 為 V 系列，無 AT；AT-963-1-5 為 SCG-0～3 審查 F1 新增） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉。**凍結檔不得再改**：上位 TCS／契約的訂正只寫在各自〈勘誤〉表，走 refreeze；本檔為使其可測而補定義者，標「本檔類推」並列入 §9。**本鍵零 Bridge 改動、零根層碼改動；backend 只動兩支列表端點的 `sort` 白名單。**

### FRD-lite

**背景（掌舵者 2026-11-08 兩項指令，sid `3d200496-a6dd-47e0-9921-b3904cf412ac`）**：(1)「Console UI 中所有資料列表的每個欄位，預設依 ID 排序，使用者也可以按欄位標題排序」；(2)「所有 UI 的『本頁說明』改成國高中等級、詳細清楚又言簡意賅的文案，使用者一看就知道功能怎麼用，尤其專案管理／研發工作流」。掌舵者已裁決排序政策為方案 A（D-UX-1，原文住 PRD §0.10）；說明文案標準由主控預決（D-UX-2，同處）。現況盤點（唯讀事實）：frontend 沒有任何共用排序元件，所有表格手寫 `<table>`、沒有 `aria-sort`；唯一的排序控制是專案列表的下拉；三個後端列表端點有 `sort`（專案、匯入、批次），其餘寫死 `ORDER BY`；每頁說明 22 頁各一檔，現有 lint 只管句長 60、英文白名單與禁字元，沒有步驟品質與術語解釋的檢查，且研發工作流清單頁說明含已過時的「目前開放前兩步」句。

**現況與變更（Before／After；brownfield）**

- Before：(1) 各表列序＝API 回應序或元件內零散 `.sort`；表頭純文字。(2) 專案卡片的排序下拉只有「最近更新／名稱／最近建立」三項；匯入歷史寫死 `createdAt,desc`；研究專案列沒有排序。(3) 後端專案白名單 `name｜status｜createdAt｜updatedAt`、匯入白名單 `createdAt｜status`。(4) 說明文字 `steps` 2～8 步、每句 ≤ 60 字，沒有術語與動作詞檢查。
- After：(1) 新增 `lib/domain/sorting.ts`、`components/domain/common/SortableHeader.tsx`、`SortBar.tsx`；十一張資料表的表頭可點排序（§2.1），預設序依 §2.1。(2) 專案卡片與研究專案列以排序控制列提供同等能力（§2.2）；專案卡片與匯入歷史前端明確送 `createdAt,asc`。(3) 後端專案白名單加 `autonomyLevel`、匯入白名單加 `sourceFileName｜aiModel｜tokenUsed｜projectId`；API 預設值不變。(4) 新增 `lib/help/readability.ts`＋`.test.ts`（§3 規則 R-UX-H1～H9）；22 頁說明依 D-UX-2 改寫，研發工作流清單與工作區、專案管理為重點。
- **非目標**：不改 API 預設排序、不改回應序契約、不改 Bridge、不為 SI 帳本新增 `sort` 參數（Architecture §12.1 L-UX-1）、不為 `goalsCount`／`tasksCount` 開放排序、不動目標與任務清單、不把排序狀態放進網址或持久化、不改 `lint.ts` 的任何常數、不動議題詳情與詞表。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：本檔自增 AC 自 `AC-963-1` 起（ResearchToPRD P2 用到 `AC-962-*`，不撞號），共 9 個，見 §1。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-963-1-1`→`AT_963_1_1`）。
4. **計數**：AC 9 個、AT 56 個（見檔頭；§4 逐條列出，正文 AT 條數以 §1 的 Given／When／Then 條目為準）。

**本增量交付物**（D1～D8；路徑相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | 排序工具 | `AgentConsole/frontend/lib/domain/sorting.ts`＋`sorting.test.ts` | PKG-FE-SORT | AC-963-1 |
| D2 | 表頭元件與排序控制列 | `AgentConsole/frontend/components/domain/common/SortableHeader.tsx`、`SortBar.tsx`（各含 `.test.tsx`） | PKG-FE-SORT | AC-963-2、4 |
| D3 | 十一張表接入與兩處控制列 | §7.1 PKG-FE-SORT 持有檔案面所列元件 | PKG-FE-SORT | AC-963-3、4 |
| D4 | 後端白名單擴充 | §7.1 PKG-BE-SORT 持有檔案面 | PKG-BE-SORT | AC-963-5 |
| D5 | 可讀性鎖與文案改寫 | `AgentConsole/frontend/lib/help/readability.ts`＋`readability.test.ts`；`lib/help/*.ts` 各頁檔 | PKG-FE-HELP | AC-963-6、7 |
| D6 | 既有測試同步與 Playwright | §5 所列檔；新 `tests/e2e/console-sort.mock.spec.ts` | 各包＋PKG-E2E | AC-963-8 |
| D7 | 文件連動（主控） | Console PRD §0.10、Architecture §5.5／§12.1 L-UX-1（皆已在工作樹）、§6 勘誤與 refreeze、API_Contract_P3-6 與 openapi-p3-6 白名單條文、RTM 子表 `AgentConsole/docs/06_quality/RTM-ConsoleUxSortHelp-20261108.md` 與 `RTM.md` 存根、SCG-4 報告 | 主控 | AC-963-9（V 系列） |
| D8 | 本檔 | 本檔 | 規格棒 | — |

**提交順序與責任**

- 三包可並行（持有檔案面不重疊，§7.1）：PKG-BE-SORT、PKG-FE-SORT、PKG-FE-HELP；三包皆收工且主控親驗後才派 PKG-E2E（它要看到真的排序介面與新說明文案）。
- 每包內：先純函式與其單測、再元件、最後既有測試同步；每支完成即跑該支測試，最後該包全套驗證指令（§7.2）皆 rc 0。
- 開發 agent **不 commit／push**、不動各包持有面以外的檔（鐵律 7）、不改凍結 TCS 與契約檔、不改 `ToolsRegion.tsx`、`TopRegion.tsx`、`layout.tsx`。
- 真帳本、真 `~/.autosdd/` 一律唯讀。

**〈增量行為規則〉**（W-UX1～W-UX8；各 AT 以 W-UX 編號引用。實查依據：盤點紀錄、`IssueTable.tsx`、`issues.ts`、`BackupList.tsx`、`HistoryPanel.tsx`、`ProjectsView.tsx`、`ResearchListView.tsx`、`lib/help/{lint,types,registry,content.test}.ts`、後端 `ProjectController`、`ImportController`、`ProjectRepositoryAdapter`、`ImportRecordRepositoryAdapter`）

- **W-UX1 排序工具**：`sorting.ts` 匯出 `SortKind`（`id`｜`text`｜`number`｜`iso`｜`rank`）、`SortColumn<T>`（`{ key: string; kind: SortKind; get: (row: T) => string | number | null | undefined; rank?: (v: string) => number | null; tieDir?: "asc" | "desc" }`）、`SortState`（`{ key: string; dir: "asc" | "desc" } | null`，`null`＝預設序）、`sortRows(rows, columns, state, defaultCompare?)`、`nextSort(state, key, defaultSort?)`、`compareId`。語意：(a) `id` 與 `text` 都用 `Intl.Collator("zh-Hant", { numeric: true })`（`RP-0009` < `RP-0010`、`ID-99` < `ID-100`；範例一律不用真實帳本 id 樣式，見勘誤 E-1）；(b) `number` 數值比較；(c) `iso` 轉毫秒，無法解析者退回 `text` 比較、不丟例外；(d) `rank` 呼叫端提供序位函式，序位 `null` 視同空值；(e) 空值（`null`／`undefined`／空字串）**不論升降冪一律排最後**；(f) 主比較相等時一律再比識別欄（`columns` 中第一個 `kind: "id"` 的欄；全表無識別欄時用呼叫端給的 `tieBreak` 欄），方向由該欄的 `tieDir` 決定、預設升冪，且**不隨使用者的升降冪翻轉**（備份清單「標籤」欄設 `desc`，與後端同口徑；QA F3）；(g) 回傳新陣列、不改輸入；`state === null` 時回 `defaultCompare` 排序後的新陣列（未給＝原順序複本）；`state.key` 不在 `columns` 內＝當 `null`；(h) `nextSort(state, key, defaultSort?)`：有效狀態＝`state ?? defaultSort ?? null`；有效狀態為 `null` 或目前欄不同 → `{ key, dir: "asc" }`；目前欄相同 → 升冪變降冪、降冪變升冪（預設序對應某欄時，第一次點該欄就反向，不會出現「點了沒變、後端表多打一次相同請求」；QA F1）。
- **W-UX2 表頭元件**：`SortableHeader({ column, label, state, onSort, children? })` 渲染 `<th scope="col" aria-sort="ascending｜descending｜none">`，內含 `<button type="button">`，按鈕文字＝欄名、圖示（`ArrowUp`／`ArrowDown`／`ArrowUpDown`，lucide）帶 `aria-hidden`；🔴 `<th>` 的 `textContent` 必須嚴格等於欄名（不得有 sr-only 補字或 `aria-label`）。目前欄 `aria-sort` 為 `ascending`／`descending`，其餘欄為 `none`；預設序若對應某個欄（識別欄升冪、備份「結束」降冪）則該欄起始 `aria-sort` 即為該方向（`state` 為 `null` 時由 `defaultSort` prop 決定顯示，不需使用者先點），第一次點該欄即依 W-UX1(h) 反向。不可排欄不使用此元件，保持既有純 `<th>`。一欄含兩個排序鍵（匯入歷史「AI 模型 · Token」）時渲染兩個按鈕（文字各為「AI 模型」「Token」，中間文字節點為「 · 」），`<th>` 的 `textContent` 仍嚴格等於「AI 模型 · Token」，`aria-sort` 反映兩鍵中目前啟用者。
- **W-UX3 各表預設序與可排欄**：以 §2.1 矩陣為準（唯一出處）。表頭點擊只改畫面順序，不改任何件數、不改選取與展開狀態（SI 與議題的展開列以識別鍵記，排序後仍展開同一列）。SI 觀察表的壞列（`SiInvalidRow`，`valid===false`、無 ID；`lib/api/types.ts`）不參與欄排序：一律排在全部有效列之後、彼此依 `line` 升冪，升降冪相同（QA F2）。
- **W-UX4 議題表特則**：(a) 「待處理」「待您決定」分頁預設序＝R-IC-33 第一條（佇列）；(b) 「已完成」「全部」分頁預設序＝R-IC-33 第二條（最後更新降冪→編號升冪；**不改**，D-UX-18：顯示序兩條是根層 CLI `tools/lib/selfimproving/issues.py` 與前端 `lib/domain/issues.ts`「同表兩端驗」的鎖，本鍵不動根層也不動 `issues.ts`）；四分頁預設皆非任一欄，起始 `aria-sort` 全為 `none`；(c) 「全部」分頁置頂列（狀態屬待您決定者）使用者排序時**仍留在頂端**，其內依佇列序，排序只作用於其下清單；(d) 切換分頁時排序狀態重置為 `null`；(e) 例外表（議題表四分頁、備份清單）在使用者排序後顯示文字按鈕「還原預設排序」（`data-testid="sort-reset"`），按下回 `null`；其餘表無此按鈕；(f) 八欄表頭字樣與順序不變（R-IC-65）；「下一步」欄（含決定按鈕）不可排。
- **W-UX5 排序控制列**：`SortBar({ options, state, onChange, label })` 渲染 `<div role="group" aria-label={label}>`：一個 `<Select aria-label="排序">`（選項即欄位）加一顆方向按鈕（`aria-label`「目前由小到大，按一下改由大到小」／「目前由大到小，按一下改由小到大」，兩句擇一，依 `state.dir`）。專案卡片選項依序：建立順序（`createdAt`，預設，升冪）、名稱（`name`）、狀態（`status`）、最近更新（`updatedAt`）、自治等級（`autonomyLevel`）；無「任務數」「目標數」選項（W-UX6 理由）。研究專案列選項依序：編號（`rpNo`，預設，升冪）、標題、狀態、步驟、最近更新。換排序（欄位或方向）時專案卡片回第 1 頁（沿現有行為）；已刪除模式與一般模式共用同一組控制列。
- **W-UX6 後端白名單**：專案 `sort` 白名單加 `autonomyLevel`（欄位名不分大小寫，沿現有解析）；匯入歷史加 `sourceFileName`、`aiModel`、`tokenUsed`、`projectId`；非法值仍 400，訊息列出完整新白名單；API 預設值不變（專案 `updatedAt,desc`、匯入 `createdAt,desc`）；後端一律再加 `id` 升冪 tie-break（專案現狀已有；匯入現狀已有）；可為空的欄（匯入的四個新欄）升冪與降冪都 `NULLS LAST`；方向非 `asc`／`desc` 仍 400。`goalsCount`／`tasksCount` 不入白名單（Architecture §5.5 理由）。前端專案卡片與匯入歷史明確送 `createdAt,asc`。已知差異（登記 Architecture §12.1 L-UX-2；QA F8）：`status` 排序依列舉常數的英文名、不是畫面標籤；`projectId` 排序是 UUID 字串序（對使用者意義有限，為「每欄可排」的完整性保留）；PG 字串排序依資料庫 collation，與前端 `zh-Hant` collator 不同；IT 比對 `id` tie-break 一律用小寫十六進位字串比較（Java `UUID.compareTo` 與 PG `uuid` 序不同），夾具的 `sourceFileName`／`aiModel` 限 ASCII。
- **W-UX7 說明文案**：標準與機械規則見 §3（R-UX-H1～H9）；`lint.ts` 與其凍結規則不動，`readability.ts` 疊加；同一份語料（各頁 `purpose`、`steps`、欄位 `meaning` 與 `sourceNote`、`STATE_HELP` 每列、`HELP_COMMON`、`SHARED`）逐筆過兩道。欄位名與狀態名（畫面字樣）不受英文詞與術語規則限制。
- **W-UX8 同步只增不減**：§5 所列既有測試的 diff 每個 hunk 只動預期值、探針列、fixture 或註解；`expect(` 與 `it(`／`test(` 的呼叫數新檔 ≥ 舊檔（改預期值在 diff 是一刪一增，不以「刪除行＝0」計；QA F12）；AT 標題與 id 不變（與 TCS-ExecMonitorEntry 勘誤 6 同口徑）。

### 增量追溯表（上位凍結檔；digest＝規格棒於工作樹現算，Stage-1 凍結由 CLI 重算為準）

| 上位檔 | 路徑（相對 monorepo 根） | sha256（本檔落檔時） |
|--------|--------------------------|---------------------|
| Console PRD（含 §0.10） | `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `e62c6ccf7cd137081cf778d8f9ac2442626f23df4014dda58f1c1c04d97161de` |
| Architecture（含 §5.5、§12.1 L-UX-1） | `AgentConsole/docs/02_architecture/Architecture.md` | `1edf242418b6409cad051fa4a5b90b498b606ffa451369a1a3242d77548b7064` |
| TCS-PageHelp（R-PH-06 步數界線；勘誤 PH-1） | `AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md` | `c58035bb00e63978b8693a5f192d8a57ef7a7a930702db000fa9e5bea8a67b6e` |
| Console_PageHelp_PRD（AC-PH-03-5；勘誤 PH-2） | `docs/01_requirements/Console_PageHelp_PRD.md` | `cf1e97a9e5b666daef3024b13bc15a6903a6097f63a8dd8a24051813c899e3d0` |
| TCS-IssueCenter（R-IC-33、R-IC-66；勘誤 IC-1、IC-2） | `docs/03_testing/contracts/TCS-IssueCenter-20261027.md` | `50d41337de5d374b0568be1a09bf8c1adee35603f82ba9528ff0f80a2c296c30` |
| TCS-SysAdminBackup（AT-BK-02-1-2；勘誤 BK-1） | `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md` | `1fc2f46bd4fc44bfe2e058b8a743c51507bbfe8280bdd135989ff25732260d2b` |
| API_Contract_P3-6（sort 白名單；勘誤 API-1） | `AgentConsole/docs/02_architecture/API_Contract_P3-6.md` | `0ada38cf4fe438c4fd572a89cc3af089711361339c62e01653ef2438cefe2300` |
| API_Contract_ResearchToPRD（API-RP-02；勘誤 RP-1） | `AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` | `909b1afefecf1ba93886049b4b93a63729882387ca28ae9069b7a57855fc171f` |
| TCS-ExecMonitorEntry（W-E3；勘誤 EM-1） | `AgentConsole/docs/03_testing/contracts/TCS-ExecMonitorEntry-20261101.md` | `986e19417b7493d74961243de144483127a2c887ff44b290f4f04ccb91b8ecbf` |

---

## 1. AC → AT 映射表

| AC | 說明 | 正控 AT | 負控／邊界 AT | 規則 |
|----|------|---------|---------------|------|
| AC-963-1 | 排序工具與狀態機 | AT-963-1-1、1-2、1-3、1-4、1-5 | AT-963-1-E-1 | W-UX1 |
| AC-963-2 | 表頭元件與無障礙 | AT-963-2-1、2-2、2-3、2-4 | AT-963-2-E-1 | W-UX2 |
| AC-963-3 | 十一張表的預設序與表頭排序 | AT-963-3-1～3-14 | AT-963-3-E-1、3-E-2 | W-UX3、W-UX4 |
| AC-963-4 | 專案卡片與研究專案列的排序控制列 | AT-963-4-1、4-2、4-3、4-4 | AT-963-4-E-1 | W-UX5 |
| AC-963-5 | 後端 sort 白名單擴充 | AT-963-5-1、5-2、5-3 | AT-963-5-E-1、5-E-2 | W-UX6 |
| AC-963-6 | 說明文案可讀性機械鎖 | AT-963-6-1～6-6 | AT-963-6-E-1 | W-UX7、§3 |
| AC-963-7 | 各頁說明的內容事實 | AT-963-7-1～7-5 | AT-963-7-E-1 | W-UX7、§3.4 |
| AC-963-8 | 既有鎖連動與 E2E | AT-963-8-1～8-6 | — | W-UX8 |
| AC-963-9 | 文件連動 | V 系列（§8.2） | — | PRD §0.10 |

**Given／When／Then**（載具：FN＝vitest 純函式；FT＝vitest 元件；IT＝gradle 整合測試；E2E＝Playwright mock spec；GT＝閘門／靜態；H＝vitest 內容測試）

### AC-963-1（`lib/domain/sorting.test.ts`，FN）

- **AT-963-1-1** Given 列 `[RP-0010, RP-0009, RP-0100]`（`id` 欄）與 `[ID-100, ID-99]`、文字欄 `["丙","甲","乙"]`、數字欄 `[10, 9, 100]`、ISO 欄 `["2026-11-02T00:00:00+08:00","2026-11-01T23:00:00Z"]` When 各自 `sortRows` 升冪 Then 依序為 `RP-0009、RP-0010、RP-0100`；`ID-99、ID-100`；中文欄依 zh-Hant collator 序（與 `Intl.Collator("zh-Hant")` 逐元素比對結果相同）；`9、10、100`；ISO 欄依實際時刻（兩列時刻相差一小時，`+08:00` 者較早）；降冪為各自的反序。
- **AT-963-1-2** Given 欄值含 `null`、`undefined`、空字串各一與正常值 When 升冪與降冪各排一次 Then 兩個方向空值都在最後；ISO 欄含無法解析的字串 When 排序 Then 不丟例外、該列依文字比較落位。
- **AT-963-1-3** Given 兩列主欄值相等、識別欄不同 When 升冪與降冪 Then 兩個方向都由識別欄升冪決定先後（決定性）；識別欄設 `tieDir: "desc"` 時，兩個方向都由識別欄降冪決定先後（QA F3）；輸入陣列與其元素未被改動（`Object.freeze` 的輸入不丟例外、回傳為新陣列）；`state=null` 且給 `defaultCompare` ⇒ 結果等於以它排序的複本，未給 ⇒ 原順序複本。
- **AT-963-1-4** Given `nextSort` When 狀態 `null` 點 `a`、再點 `a`、再點 `a`、再點 `b` Then 依序為 `{a,asc}`、`{a,desc}`、`{a,asc}`、`{b,asc}`。
- **AT-963-1-5** Given `defaultSort={key:"id",dir:"asc"}`、`state=null` When `nextSort(null, "id", defaultSort)` Then 得 `{id,desc}`；`nextSort(null, "text", defaultSort)` 得 `{text,asc}`；`defaultSort={key:"finishedAt",dir:"desc"}` 時 `nextSort(null, "finishedAt", defaultSort)` 得 `{finishedAt,asc}`；不帶 `defaultSort` 時行為同 AT-963-1-4（QA F1）。
- **AT-963-1-E-1** Given `state.key` 不在 `columns` 內、空陣列、單筆、`rank` 函式對某值回 `null` When `sortRows` Then 不丟例外；不明欄＝視同 `null`（原順序複本）；空陣列回空、單筆回同筆；`rank` 回 `null` 的列排最後。

### AC-963-2（`components/domain/common/SortableHeader.test.tsx`，FT）

- **AT-963-2-1** Given 三欄表頭（A、B、C）、`state={key:"B",dir:"asc"}` When 渲染 Then 三個 `columnheader` 的 `aria-sort` 依序為 `none`、`ascending`、`none`；`state={key:"B",dir:"desc"}` ⇒ `descending`；`state=null` 且 `defaultSort={key:"A",dir:"asc"}` ⇒ A 為 `ascending`、其餘 `none`。
- **AT-963-2-2** Given 同上 When 對 B 的按鈕以 `userEvent.keyboard("{Enter}")` 與 `" "`（Space）各觸發一次 Then `onSort("B")` 各被呼叫一次（原生按鈕鍵盤操作可用）；按鈕 `type="button"`。
- **AT-963-2-3** Given 渲染 Then 每個 `<th>` 的 `textContent` 嚴格等於欄名；每個圖示 `svg` 帶 `aria-hidden="true"`；`<th>` 內沒有 `aria-label`；兩鍵欄（「AI 模型 · Token」）渲染兩個按鈕、`<th>` `textContent` 為「AI 模型 · Token」。
- **AT-963-2-4** Given 一個不可排欄（用純 `<th>`，如「操作」）混在表頭 When 渲染 Then 該欄沒有 `button`、沒有 `aria-sort` 屬性。
- **AT-963-2-E-1** Given 受控元件接 `nextSort` When 連點同一欄、再點另一欄 Then 前者 `ascending`→`descending`→`ascending`；點另一欄後前者回 `none`、後者 `ascending`（同一時刻最多一欄非 `none`）。

### AC-963-3（十一張表；各元件測試檔，FT；H＝逐表欄位矩陣以 §2.1 為準）

- **AT-963-3-1**（`IssuesView.test.tsx`）Given 「待處理」與「待您決定」分頁資料依序亂排 When 渲染 Then 列序＝R-IC-33 第一條（順位升冪→嚴重度→最後更新升冪→編號升冪），與改動前逐列相同；沒有任何 `columnheader` 帶非 `none` 的 `aria-sort`（預設序不是欄位）。
- **AT-963-3-2**（同檔）Given 「已完成」與「全部」分頁資料依序亂排 When 渲染 Then 預設列序＝R-IC-33 第二條（最後更新降冪、空值最後→編號升冪），與改動前逐列相同；沒有任何 `columnheader` 帶非 `none` 的 `aria-sort`；「全部」分頁置頂列（待您決定狀態）仍在頂端（`issue-top-pinned` 恰在前段），其內依佇列序（D-UX-18）。
- **AT-963-3-3**（同檔）Given 任一分頁 When 依序點「最後更新」「嚴重度」「優先順序」「來源」「標題」「狀態」各一次 Then 各欄按該欄語意排序（最後更新依 ISO 時刻；嚴重度依 `severityRank`；優先順序依有效順位、無順位排最後，兩個方向都是）；「下一步」欄沒有按鈕；八個 `columnheader` 的 `textContent` 依序為 編號、來源、標題、嚴重度、狀態、優先順序、最後更新、下一步（R-IC-65 字樣不變）；「全部」分頁排序後置頂列仍在頂端。
- **AT-963-3-4**（同檔）Given 「待處理」分頁已點「標題」排序 When 按「還原預設排序」 Then 列序回佇列序、按鈕消失；Given 該狀態下切到「已完成」再切回 Then 排序狀態已重置（`aria-sort` 全 `none`、無還原鈕）；「已完成」分頁排序後同樣出現還原鈕、按下回 R-IC-33 第二條序（四分頁預設序都不是任一欄）。
- **AT-963-3-5**（`SiView.test.tsx`；SI 觀察表）Given 觀察資料列序亂排 When 渲染 Then 預設＝ID 自然序升冪（ID 欄 `aria-sort="ascending"`）；點「時間」「分類」「嚴重度」「處置」「症狀」各依該欄排；操作欄與寫入操作欄無按鈕；展開某列後排序，展開的仍是同一列（以 ID 記）；第一次點「ID」（預設欄）即變降冪（QA F1）；壞列（`si-obs-invalid-<line>`）在預設與任何排序下都在有效列之後、依 line 升冪（QA F2）；「時間」欄值為 `YYYY-MM-DD HH:mm` 字串，`iso` 解析失敗退回文字比較後的順序等於時刻順序（夾具含跨月、跨年各一對；QA F18）。
- **AT-963-3-6**（`SiStatusFilter.test.tsx` 或 `SiView.test.tsx`；SI 提案表）Given 提案資料 When 渲染與點欄 Then 預設 ID 升冪；「rev」依數字排、`digest`、`verdict`、`cooldown`、「狀態」「類別」「route」依文字排；操作欄與決定欄無按鈕。
- **AT-963-3-7**（同上；SI 事件表）Given 事件資料 When 渲染 Then 預設 `seq` 數值升冪（9 在 10 前）；點 `t` 依 ISO 時刻、`kind`、`by` 依文字；操作欄無按鈕。
- **AT-963-3-8**（同上；SI 運轉表）Given 運轉資料 When 渲染 Then 預設 ID 升冪；`openedSeq`、`closedSeq` 依數字排、`closedSeq` 為空的列兩個方向都在最後；`trigger`、`outcome`、`propIds`、`research` 依文字排。
- **AT-963-3-9**（`BackupView.test.tsx`；備份清單）Given AT-BK-02-1-1 同形的 6 筆加一筆增量 When 渲染 Then 預設列序與表頭序與改動前完全相同（結束時間新到舊；十欄字樣與順序不變；「結束」欄 `aria-sort="descending"`）；點「標籤」「開始」「耗時」「備份」「結果」等欄依該欄排（耗時、資料庫、備份依數值，空值「—」排最後）；結束時間相同的兩列，預設序與升降冪都依「標籤」降冪（`tieDir: "desc"`；QA F3）；排序後出現「還原預設排序」，按下回新到舊。
- **AT-963-3-10**（`AllowlistDialog.test.tsx`；允許清單）Given 清單資料 When 渲染 Then 預設「主機」自然序升冪；「最小間隔」依數字排；「動作」欄無按鈕；八個 `columnheader` 的 `textContent` 依序為 主機、清單、層、用途、來源、最小間隔、狀態、動作。
- **AT-963-3-11**（`TraceabilityTable.test.tsx`；追溯表）Given 驗收條件列 When 渲染 Then 預設「AC」自然序升冪；「使用者故事」「Gherkin 摘要」「單元狀態」「端對端狀態」「來源」依文字、「最近執行」依 ISO 時刻排；列首 `<th scope="row">` 維持。
- **AT-963-3-12**（`EvidenceMatrixTable.test.tsx`；抓取紀錄）Given 抓取紀錄 When 渲染 Then 預設「編號」自然序升冪；「狀態碼」「位元組」依數字、「時間」依 ISO、「方法」「觀測者」「主機」「結果」「原文 sha256」依文字。
- **AT-963-3-13**（同檔；證據表）Given 證據列 When 渲染 Then 預設「編號」自然序升冪；「層級」「強度」依文字（序位函式留給實作，必須使 V0～V3 型態標籤依字面升冪）；「標記」欄不可排（複合徽章無單一值）；七欄 `textContent` 依序不變；同檔的優缺點矩陣（`proscons-matrix`）`thead` 內無 `aria-sort`、無按鈕（範圍外；QA F7）。
- **AT-963-3-14**（`HistoryPanel.test.tsx`；匯入歷史，後端排序）Given 空 localStorage、API 替身記錄請求 When 渲染 Then 第一個請求帶 `sort=createdAt,asc`；點「來源」⇒ 下一個請求 `sort=sourceFileName,asc` 且 `page=0`；再點「來源」⇒ `sourceFileName,desc`；點「狀態」`status,asc`；點「專案」`projectId,asc`；點「AI 模型」`aiModel,asc`、點「Token」`tokenUsed,asc`；「匯入時間」欄起始 `aria-sort="ascending"`，第一次點它即送 `createdAt,desc`（QA F1）；操作欄無按鈕；`sort` 值一律以 `URLSearchParams` 解碼後比對（既有 `:65` 斷言的是編碼字串 `createdAt%2Cdesc`，改預期時同樣解碼；QA F11）。
- **AT-963-3-E-1**（`lib/domain/sortScope.static.test.ts`，GT 靜態）Given 掃 `components/domain/**` 非測試檔 When 找出 import `SortableHeader` 的檔 Then 檔集合恰為九個：`issues/IssueTable.tsx`、`si/SiObservationsPanel.tsx`、`si/SiProposalsPanel.tsx`、`si/SiEventsPanel.tsx`、`sysadmin/BackupList.tsx`、`research/AllowlistDialog.tsx`、`research/TraceabilityTable.tsx`、`research/EvidenceMatrixTable.tsx`、`import/HistoryPanel.tsx`（§2.1 十一張表住九個檔）；`CompareCard`、`GatekeeperPanel`（雷達等效表）、`CoverageList`、`RouteDrawer`、`PageHelpDialog`、`BackupHelp`、`BackupList` 之外的備份子元件都不在集合內（範圍外表不得被悄悄加排序；優缺點矩陣的檔內例外由 AT-963-3-13 釘；QA F7）。
- **AT-963-3-E-2**（`SiView.test.tsx`）Given SI 觀察表已載入 100 筆、按「載入更多」又來 20 筆（ID 全部較大）且使用者已點「時間」降冪 When 新列併入 Then 全部 120 列依目前排序重排（新列不會永遠接在尾端）；預設序下新列自然接尾（ID 升冪與游標序一致）。

### AC-963-4（`ProjectsView.test.tsx`、`ResearchListView.test.tsx`、`SortBar.test.tsx`，FT）

- **AT-963-4-1**（`ProjectsView.test.tsx`）Given 專案列表 API 替身記錄請求 When 渲染 Then 第一個請求 `sort=createdAt,asc`；排序下拉選項依序為 建立順序、名稱、狀態、最近更新、自治等級，沒有「任務數」「目標數」；選「自治等級」⇒ 下一個請求 `sort=autonomyLevel,asc` 且 `page=0`；按方向鈕 ⇒ `autonomyLevel,desc`（`sort` 值以 `URLSearchParams` 解碼後比對；QA F11）。
- **AT-963-4-2**（同檔）Given 切到「已刪除」模式 When 渲染 Then 同一組排序控制列仍在、預設仍 `createdAt,asc`；方向鈕 `aria-label` 隨方向在兩句之間切換。
- **AT-963-4-3**（`ResearchListView.test.tsx`）Given 三個研究專案（RP-0010、RP-0009、RP-0100，更新時間各異）When 渲染 Then 預設列序依編號自然序升冪（RP-0009、RP-0010、RP-0100）；選「標題」依文字、「最近更新」依 ISO 時刻、「狀態」依徽章文字、「步驟」依步驟順序；方向鈕切換後整列反序。
- **AT-963-4-4**（同檔）Given 已選「標題」降冪 When 切到「已封存」篩選再切回 Then 排序保持（排序狀態與篩選狀態各自獨立）；搜尋關鍵字縮小清單後，結果仍依目前排序。
- **AT-963-4-E-1**（`SortBar.test.tsx`）Given 清單為空或只有一筆 When 渲染與切換 Then 不丟例外、控制列照常渲染；`options` 為空陣列時不渲染下拉（不產生空 `<select>`）。

### AC-963-5（backend，IT；沿 `ProjectApiIT`、`ImportFlowApiIT` 的真 PG／測試容器體例）

- **AT-963-5-1**（`ProjectApiIT`，IT）Given 三個專案 `autonomyLevel` 各為 5、2、5（後者建立較晚）When `GET /api/v1/projects?sort=autonomyLevel,asc` 與 `,desc` Then 200；asc 序為 2 者在前，兩個 5 者以 `id` 升冪決定先後；desc 序為兩個 5 者在前（仍以 `id` 升冪決定其間先後）、2 者在後；`sort=AUTONOMYLEVEL,asc`（大小寫不同）同樣 200；`id` 序一律以小寫十六進位字串比較（QA F8）。
- **AT-963-5-2**（`ImportFlowApiIT`，IT）Given 四筆匯入紀錄（`sourceFileName`、`aiModel`、`tokenUsed`、`projectId` 各異，部分為 null） When 各以 `sort=<欄>,asc` 與 `,desc` 查詢 Then 200；序依該欄（`tokenUsed` 數值序；null 在升降冪兩個方向都排最後）；同值以 `id` 升冪（小寫十六進位字串比較）；夾具的 `sourceFileName`、`aiModel` 限 ASCII；`createdAt`、`status` 既有排序行為不變（QA F8）。
- **AT-963-5-3**（`ProjectApiIT`、`ImportFlowApiIT`，IT）Given 不帶 `sort` When 查專案與匯入列表 Then 專案預設 `updatedAt,desc`、匯入預設 `createdAt,desc`（與改動前逐筆相同）；`ResponseEnvelopeIT` 的封包形狀不變。
- **AT-963-5-E-1**（兩個 IT 檔）Given `sort=goalsCount,asc`、`sort=tasksCount,asc`、`sort=executionPath,asc`（專案）與 `sort=foo,asc`（匯入）When 查詢 Then 400，訊息列出完整新白名單（專案：name、status、createdAt、updatedAt、autonomyLevel；匯入：createdAt、status、sourceFileName、aiModel、tokenUsed、projectId）。
- **AT-963-5-E-2**（兩個 IT 檔）Given `sort=name,up`、`sort=aiModel,` When 查詢 Then 400（方向非 `asc`／`desc` 仍拒收）。

### AC-963-6（`lib/help/readability.test.ts`，H；語料＝全部已登記頁的 `purpose`、`steps`、欄位 `meaning` 與 `sourceNote`、`STATE_HELP` 每列 `meaning` 與 `next`、`HELP_COMMON`、`SHARED`；欄位名與狀態名不入語料）

- **AT-963-6-1** Given 全語料 When 以 `splitSentences` 切句 Then 每句 code point 數 ≤ 40（R-UX-H1）；失敗訊息列出頁、位置與該句。
- **AT-963-6-2** Given 每頁 When 計數 Then `purpose` 合計 2～3 句、`steps` 5～10 項且每項恰 1 句（R-UX-H2）。
- **AT-963-6-3** Given 每頁每個 step When 判定 Then 不以「這」「此」「系統」開頭、且含 `ACTION_WORDS` 至少一個詞（R-UX-H3）。
- **AT-963-6-4** Given 每頁每個欄位與 `HELP_COMMON`、`SHARED` 的每個欄位 When 判定 Then `meaning` 去空白後 ≥ 10 個 code point（R-UX-H4）。
- **AT-963-6-5** Given 每頁（`HELP_COMMON` 與 `SHARED` 各自當一個語料）依畫面順序串接（purpose → steps → 欄位 meaning 與 sourceNote → 狀態列 meaning 與 next） When 掃 `MUST_EXPLAIN` 詞 Then 每個詞在該語料的第一次出現後面緊接「（」且括號內 ≥ 2 個字，否則紅（R-UX-H5）。
- **AT-963-6-6** Given 全語料 When 掃 `JARGON_BANNED`、`IMPLEMENTATION_WORDS` 與 `STALE_PHRASES` Then 命中為 0；`lib/help/research.ts` 不含「目前開放前兩步」、全語料不含「本步驟於後續階段提供」（R-UX-H6～H8）。
- **AT-963-6-E-1**（負控）Given 合成輸入 When 餵給 `readability.ts` 的判定函式 Then 41 個 code point 的句子回非空、40 個回空；purpose 1 句與 4 句回非空、2 句與 3 句回空；steps 4 項與 11 項回非空、5 項與 10 項回空；step「這個按鈕可以按」回非空（開頭）、「系統會自動儲存」回非空（開頭）、「看看清單」回空（含詞表內的「看」）、「等待結果出現」回空（含「等」）、「結果會出現在右邊」回非空（無動作詞；QA F5）；`meaning` 9 字回非空、10 字回空；「FSM 會跑」（首次出現無括號）回非空、「FSM（流程狀態機，記錄做到哪一步）」回空、括號只有 1 字回非空、第二次出現不需括號回空；含「游標」、含「JDBC」、含「本步驟於後續階段提供」各回非空。

### AC-963-7（`lib/help/pageFacts.test.ts`，H；「事實」以關鍵詞組判定，詞組見 §3.4）

- **AT-963-7-1**（專案管理 `projects`）Given 該頁全文 When 檢 §3.4 的 P1～P6 Then 全部命中（草案審批前不能執行、唯讀角色不能新建、已刪除可復原、排序可選建立順序與名稱、匯入入口、「完整走一遍」步驟依 新建或匯入→目標→任務→審批→執行→監控 的次序各出現）。
- **AT-963-7-2**（研發工作流清單 `research`）Given 該頁全文 When 檢 R1～R6 Then 全部命中，且不含「目前開放前兩步」。
- **AT-963-7-3**（研發工作流工作區 `research-workspace`）Given 該頁全文 When 檢 W1～W5 Then 全部命中（規格由 ADMIN 核准後凍結、分流只有 ADMIN 能確認、五步依序出現、退回修改、卡住時的去處）。
- **AT-963-7-4**（有可排序表的頁）Given `SORTABLE_HELP_PAGES`（import、issues、self-improving、sysadmin-backup、research-workspace 與兩個控制列頁 projects、research） When 檢 Then 表頁（前五者）的 `steps` 內至少一步同一句含「欄位標題」與「排序」；控制列頁（後二者）的 `steps` 內至少一步含「排序」；議題頁的排序教學句必須含「欄位標題」，且全頁文案描述「優先順序」欄的「排序」鈕時改用「排列順位」，使「排序」一詞只指表頭排序（QA F15）。
- **AT-963-7-5**（入口頁）Given `execute-entry`、`monitor-entry` When 檢 Then 兩頁 `steps` 各 5～10 步（由勘誤 EM-1 放寬），且每步通過 AT-963-6-3。
- **AT-963-7-E-1**（負控）Given 缺 P1 關鍵詞的合成專案管理頁、缺 W2 的合成工作區頁、`steps` 次序顛倒的合成頁 When 餵 `factProblems` Then 各回非空；完整合成頁回空。

### AC-963-8（既有鎖連動與 E2E）

- **AT-963-8-1**（GT）Given `git diff -U0 <base> -- <§5 所列檔>` When 逐 hunk 檢視 Then 只動預期值、探針列、fixture 與註解；每檔 `expect(` 與 `it(`／`test(` 的呼叫數新 ≥ 舊（QA F12）；AT 標題與 id 不變；§5 標「不受影響」的檔零差異；各包持有面以外零差異（`git diff --name-only` 核對）。
- **AT-963-8-2**（E2E，`tests/e2e/console-sort.mock.spec.ts`，專案管理）Given mock 三個專案 When 進 `/projects` Then 卡片順序為建立順序；選排序「名稱」、按方向鈕 ⇒ 卡片順序隨之改變且請求帶對應 `sort`；沒有「任務數」選項。
- **AT-963-8-3**（E2E，議題中心）Given mock 議題 When 進 `/issues` Then 「待處理」佇列序不變；切「全部」點「編號」表頭 ⇒ `aria-sort` 反向且列序反轉、置頂列仍在頂端；鍵盤 Tab 到表頭按鈕按 Enter 同樣有效。
- **AT-963-8-4**（E2E，研發工作流清單）Given mock 研究專案三筆 When 進 `/research` Then 預設編號升冪；選「標題」排序列序改變；開「本頁說明」看到步驟 ≥ 5 且不含「目前開放前兩步」。
- **AT-963-8-5**（E2E，備份）Given mock 備份清單 When 進 `/sysadmin/backup` 的清單分頁 Then 預設新到舊；點「標籤」表頭列序改變且出現「還原預設排序」；按它回新到舊。
- **AT-963-8-6**（E2E，`page-help.mock.spec.ts` 擴一案，專案管理）Given 進 `/projects` When 開「本頁說明」 Then 對話框「怎麼用」為編號步驟 ≥ 5 項；「狀態說明」第一張表列序仍＝`projectStatus` 鍵序（`tbody tr` 第一列不變）。

---

## 2. 列表×欄位矩陣

### 2.1 有表頭的資料表（`SortableHeader`；十一張，母體＝盤點 A 的 A7、A9、A10～A13、A15、A30、A31 中的「有表頭資料表」）

層：前端＝前端對已載入全部列排序；後端＝送 `sort` 給後端（跨頁正確）。kind 見 W-UX1。「空值」一律最後。

| # | 表（testid／元件） | 層 | 預設序（起始 `aria-sort`） | 可排欄（kind） | 不可排欄與理由 | tie-break |
|---|---|---|---|---|---|---|
| T1 | 匯入歷史（`import-history`／`HistoryPanel`） | 後端 | 建立順序升冪＝`createdAt,asc`（匯入時間欄 ascending；D-UX-1：UUID 無業務序，以建立順序當 ID 序） | 匯入時間→`createdAt`、來源→`sourceFileName`、狀態→`status`、專案→`projectId`、AI 模型→`aiModel`、Token→`tokenUsed`（「AI 模型 · Token」一欄兩鍵） | 操作欄（按鈕） | 後端 `id` 升冪 |
| T2 | 議題表（`issues-table`／`IssueTable`） | 前端 | 四分頁皆＝R-IC-33（例外；待處理與待您決定＝第一條佇列、已完成與全部＝第二條 最後更新降冪→編號升冪；無欄 active，起始 `aria-sort` 全 `none`；D-UX-18） | 編號（id）、來源（text）、標題（text）、嚴重度（rank：`severityRank`）、狀態（text）、優先順序（number，無順位為空值）、最後更新（iso） | 下一步（含決定按鈕，動作欄） | 編號升冪（自然序）；全部分頁置頂列留頂 |
| T3 | SI 觀察表（`si-obs-table`／`SiObservationsPanel`） | 前端（已載入列） | ID 自然序升冪（ID ascending）；壞列恆在有效列之後、依 line 升冪（W-UX3） | ID（id）、時間（iso）、分類（text）、嚴重度（text）、處置（text）、症狀（text） | 操作（展開鈕）、寫入操作（按鈕）：sr-only 動作欄 | ID |
| T4 | SI 提案表（`si-prop-table`／`SiProposalsPanel`） | 前端（已載入列） | ID 自然序升冪 | ID（id）、狀態、類別、route、digest、verdict、cooldown（text）、rev（number） | 操作（展開鈕）、決定（決定鈕欄，僅 Admin 有） | ID |
| T5 | SI 事件表（`si-events-table`／`SiEventsPanel`） | 前端（已載入列） | seq 數值升冪（seq ascending） | seq（number，視為識別欄）、t（iso）、kind（text）、by（text） | 操作（展開鈕） | seq |
| T6 | SI 運轉表（`si-runs-table`／`SiEventsPanel`） | 前端（已載入列） | ID 自然序升冪 | ID（id）、trigger、outcome、propIds、research（text）、openedSeq、closedSeq（number；closedSeq 空值最後） | 無 | ID |
| T7 | 備份清單（`bk-table`／`BackupList`） | 前端 | 結束時間新到舊（例外；結束 descending；凍結 AT-BK-02-1-2） | 類型、儲存位置、基準、結果（text）、標籤（id，`tieDir: "desc"`）、開始、結束（iso）、耗時、資料庫、備份（number；空值「—」最後） | 無 | 標籤降冪（`tieDir`，與後端同口徑；W-UX1(f)） |
| T8 | 允許清單（`allowlist-table`／`AllowlistDialog`） | 前端 | 主機自然序升冪（主機 ascending；清單條目無編號，主機是條目的唯一鍵，見 §9 D-UX-5） | 主機（id）、清單、層、用途、來源、狀態（text）、最小間隔（number） | 動作（按鈕欄） | 主機 |
| T9 | 追溯表（`TraceabilityTable`，`<table>` 無 testid，以 `aria-label` 取） | 前端 | AC 自然序升冪（AC ascending；與 Bridge `sorted(frozen.acs)` 同序） | AC（id）、使用者故事、Gherkin 摘要、單元狀態、端對端狀態、來源（text）、最近執行（iso） | 無 | AC |
| T10 | 抓取紀錄（`fetch-records`／`EvidenceMatrixTable`） | 前端 | 編號（fetchNo）升冪 | 編號（id）、方法、觀測者、主機、結果、原文 sha256（text）、狀態碼、位元組（number）、時間（iso） | 無 | 編號 |
| T11 | 證據表（`evidence-table`／`EvidenceMatrixTable`） | 前端 | 編號（evidenceNo）自然序升冪 | 編號（id）、候選技術、論點、來源、層級、強度（text） | 標記（複合徽章，無單一值） | 編號 |

### 2.2 沒有表頭的列表（`SortBar` 控制列）

| # | 列表 | 層 | 預設序 | 選項（欄位→排序鍵） | 不提供的欄與理由 |
|---|---|---|---|---|---|
| L1 | 專案卡片列表（`ProjectsView`；一般與已刪除兩模式） | 後端 | 建立順序升冪＝`createdAt,asc` | 建立順序→`createdAt`、名稱→`name`、狀態→`status`、最近更新→`updatedAt`、自治等級→`autonomyLevel` | 目標數、任務數：衍生聚合值，非資料表欄位（Architecture §5.5）；路徑：不是使用者找專案的依據；已刪除模式的刪除時間：不新增（保持白名單最小） |
| L2 | 研究專案列（`ResearchListView`） | 前端（API 不分頁） | 編號（`rpNo`）自然序升冪 | 編號、標題、狀態（徽章文字）、步驟（`deriveSteps` 目前步驟序）、最近更新（`updatedAt`） | 封存與繼續是動作 |

### 2.3 排除與保留預設（不加欄位排序）

| 列表 | 為何排除（W-UX3 的範圍界定） |
|------|------|
| 批次比較表（`compare-table`）、雷達等效文字表（`radar-table`）、優缺點矩陣（`proscons-matrix`）、覆蓋矩陣（`coverage-matrix`）、路由評分表（`route-eval-table`） | 固定指標列或矩陣，列的次序本身是語意 |
| 說明對話框的欄位表與狀態表（`PageHelpDialog`）、備份說明表（`BackupHelp`） | 靜態說明表；狀態表鍵序為凍結鎖（TCS-PageHelp D-PH-11） |
| 日誌（`log-row`）、告警（`alert-row`）、設定修改歷史、事件時間軸、寫入對帳、SDD 決策列、執行日誌（即時） | 無表頭的事件序清單，語意是時間序；日誌端點已有 `order` 參數（不變） |
| 目標清單、任務清單、匯入結果樹、拆解樹、範圍樹、DAG | 拖曳序或樹狀；順序即資料 |
| 批次下拉（RunSelect）、還原點清單 | `<option>` 清單 |
| 待人工審批清單（儀表板卡）、全部專案 rail、通知摘要、待審核項（ReviewCard）、看板欄位 | 儀表板與導覽類摘要或工作佇列，非資料列表 |

---

## 3. 說明文案標準與機械可讀性規則

### 3.1 標準條文（R-UX-H；與 PRD §0.10 D-UX-2 同義，此處為可測定義）

| 編號 | 規則 | 判定位置 | 對應 AT |
|------|------|----------|---------|
| R-UX-H1 | 句長：以 `lint.ts` 的 `splitSentences` 切句，每句 code point 數 ≤ 40（`lint.ts` 的 60 仍在，是外層界線） | `readability.ts`：`longSentences(text)` | AT-963-6-1、6-E-1 |
| R-UX-H2 | 結構：`purpose` 合計 2～3 句；`steps` 5～10 項，每項恰 1 句 | `shapeProblems(page)` | AT-963-6-2、6-E-1 |
| R-UX-H3 | 步驟：不以「這」「此」「系統」開頭；含至少一個 `ACTION_WORDS` 詞（子字串比對；這是 D-UX-2「步驟以動作開頭」的機械近似，真正把關靠 §8.2 V3 人讀；QA F4） | `stepProblems(step)` | AT-963-6-3、6-E-1 |
| R-UX-H4 | 欄位：`meaning` 去空白後 ≥ 10 code point（`HELP_COMMON`、`SHARED` 同） | `fieldProblems(field)` | AT-963-6-4、6-E-1 |
| R-UX-H5 | 術語首次解釋：依畫面順序串接的語料中，`MUST_EXPLAIN` 詞第一次出現後緊接「（」且括號內 ≥ 2 個字；之後出現免括號。比對：ASCII 詞以前後非英文字母為界（`Token` 不配 `Tokens`），「」引號內出現也算出現（QA F6） | `unexplainedTerms(corpus)` | AT-963-6-5、6-E-1 |
| R-UX-H6 | 不得出現 `JARGON_BANNED`（中文行話） | `bannedFindings(text)` | AT-963-6-6、6-E-1 |
| R-UX-H7 | 不得出現 `IMPLEMENTATION_WORDS`（內部實作語彙） | 同上 | AT-963-6-6、6-E-1 |
| R-UX-H8 | 不得出現 `STALE_PHRASES`（占位與過時句；含「本步驟於後續階段提供」「目前開放前兩步」） | 同上 | AT-963-6-6、7-2 |
| R-UX-H9 | 有可排序表的頁（`SORTABLE_HELP_PAGES`）的 `steps` 必須教排序：表頁含一句同時有「欄位標題」與「排序」；控制列頁含「排序」 | `pageFacts.test.ts` | AT-963-7-4 |

> 既有鎖仍全部有效、改寫須同時滿足：`lib/help/content.test.ts` AT_PH_05_1_1（欄位 `meaning` ≤ 2 句、狀態 `next` 恰 1 句、`sourceNote` 恰 1 句且 ≤ 30 字）、`lint.ts` 全部規則（每句 ≤ 60、英文白名單、禁字元）與三道登記鎖（QA F14）。

### 3.2 詞表（`readability.ts` 持有；增減詞要同改本表與 `readability.test.ts` 的對照）

- **ACTION_WORDS**（動作詞）：按、點、選、輸入、填、勾、打開、開啟、進入、查看、看、切換、確認、核准、退回、拖、搜尋、篩選、回到、返回、重試、建立、新建、封存、復原、刪除、上傳、貼上、等、檢查、比對、複製、下載、儲存、送出、啟動、暫停、恢復、取消、展開、收合、改、換、找、讀、留意、設定、開始、審批、簽核、匯入、排序、移到、繼續、登入、離開、重新整理。
- **MUST_EXPLAIN**（首次出現要括號白話解釋）：FSM、SSE、PRD、BRD、SDD、Token、signoff、Bridge、Playbook、DAG、Regex、API、Agent、Engine、AISDLC、AutoClaude。（這些詞在既有英文白名單內，所以不被 `lint.ts` 擋，由 R-UX-H5 要求解釋；白名單外的縮寫如 SCR、RTM、JDBC、Gate 已被 `lint.ts` 的英文規則擋在說明文字之外，只准出現在欄位名與狀態名這類畫面字樣，故不需重複列入。）
- **JARGON_BANNED**：端點、游標、雜湊、冪等、序列化、非同步、輪詢、反向代理、資料表、連線池、快取、握手、封包、行程、執行緒、白名單、黑名單。
- **IMPLEMENTATION_WORDS**：JDBC、Spring、Flyway、Controller、endpoint、schema、SQL、唯讀連線、API 路徑、`/api/`（字串）。
- **STALE_PHRASES**：本步驟於後續階段提供、目前開放前兩步、後續階段、之後的版本、敬請期待、待補、TODO。

### 3.3 `readability.ts` 介面（供開發棒照做；純函式、不碰 React）

`longSentences(text): string[]`、`shapeProblems(page): string[]`、`stepProblems(step): string[]`、`fieldProblems(field): string[]`、`unexplainedTerms(corpus: string): string[]`、`bannedFindings(text): string[]`、`pageCorpus(page): string`（依畫面順序串接，狀態列由 `STATE_HELP` 取）、`factProblems(page, facts): string[]`；回傳空陣列＝合規；訊息含關鍵字「句長」「結構」「動作」「釋義」「術語」「行話」「過時」「事實」供測試斷言（沿 `lint.ts` 的關鍵字契約體例）。

### 3.4 必須提到的事實（`pageFacts.test.ts`；各事實以關鍵詞組判定：同一事實的每個詞組都要在該頁全文出現，除標「同句」者必須在同一句內）

**專案管理（`projects`）**

| 事實 | 關鍵詞組 |
|------|----------|
| P1 草案審批前不能執行 | 「未審批」、「審批」、「不能執行」或「無法執行」或「才能執行」 |
| P2 唯讀角色不能新建 | 同句：「唯讀」、「新建專案」、「不能」 |
| P3 已刪除專案保留期限內可復原 | 「已刪除」、「復原」、「保留」 |
| P4 排序可選建立順序與名稱 | 同句：「排序」、「建立順序」；另「名稱」 |
| P5 匯入入口 | 「匯入」 |
| P6 完整走一遍 | `steps` 依序出現：（「新建專案」或「匯入」）→「目標」→「任務」→（「審批」或「簽核」）→「執行」→「監控」，各自第一次出現的位置遞增 |

**研發工作流清單（`research`）**

| 事實 | 關鍵詞組 |
|------|----------|
| R1 命題必填 | 同句：「研究命題」、「必填」 |
| R2 五步名稱 | 「研究」、「規格工作室」、「分流」、「拆解與執行」、「交付」 |
| R3 封存可復原 | 「封存」、「復原」 |
| R4 初始化失敗要重試 | 「初始化失敗」、「重試初始化」 |
| R5 排序 | 「排序」、「編號」 |
| R6 唯讀不能新建 | 同句：「唯讀」、「不能」 |

**研發工作流工作區（`research-workspace`）**

| 事實 | 關鍵詞組 |
|------|----------|
| W1 規格由 ADMIN 核准後凍結 | 同句：「ADMIN」、「核准」、「凍結」（「Gate 0」只准出現在欄位名，說明句改用「規格核准」白話） |
| W2 分流只有 ADMIN 能確認 | 同句：「分流」、「ADMIN」、「確認」 |
| W3 五步依序 | `steps` 依序出現：「研究」→「規格工作室」→「分流」→「拆解與執行」→「交付」 |
| W4 可退回修改 | 「退回」 |
| W5 卡住時的去處 | 「卡住」或「出錯」或「找不到」之一，且同句含「對帳」或「本頁說明」或「重試」之一 |

---

## 4. AT 完整清單與載具

### 4.1 Unit／Component（vitest）
- `lib/domain/sorting.test.ts`：AT-963-1-1、1-2、1-3、1-4、1-5、1-E-1
- `components/domain/common/SortableHeader.test.tsx`：AT-963-2-1、2-2、2-3、2-4、2-E-1
- `components/domain/issues/IssuesView.test.tsx`：AT-963-3-1、3-2、3-3、3-4
- `components/domain/si/SiView.test.tsx`、`SiStatusFilter.test.tsx`：AT-963-3-5、3-6、3-7、3-8、3-E-2
- `components/domain/sysadmin/BackupView.test.tsx`：AT-963-3-9
- `components/domain/research/AllowlistDialog.test.tsx`：AT-963-3-10；`TraceabilityTable.test.tsx`：AT-963-3-11；`EvidenceMatrixTable.test.tsx`：AT-963-3-12、3-13
- `components/domain/import/HistoryPanel.test.tsx`：AT-963-3-14
- `lib/domain/sortScope.static.test.ts`：AT-963-3-E-1
- `components/domain/views/ProjectsView.test.tsx`：AT-963-4-1、4-2；`research/ResearchListView.test.tsx`：AT-963-4-3、4-4；`common/SortBar.test.tsx`：AT-963-4-E-1
- `lib/help/readability.test.ts`：AT-963-6-1～6-6、6-E-1；`lib/help/pageFacts.test.ts`：AT-963-7-1～7-5、7-E-1

### 4.2 Integration（gradle）
AT-963-5-1、5-2、5-3、5-E-1、5-E-2（`ProjectApiIT`、`ImportFlowApiIT`）。

### 4.3 Gate／靜態
AT-963-8-1（git diff 人讀；SCG-4 報告 §B）。

### 4.4 E2E（Playwright mock spec）
AT-963-8-2～8-6（`tests/e2e/console-sort.mock.spec.ts` 與 `page-help.mock.spec.ts`；mock 層，不需 Docker 全棧）。

---

## 5. 需同步的既有測試（只改預期值，不刪斷言；「改預期」＝列出的斷言因預設序、sort 預設值或說明結構改變而改；開發棒只在實際轉紅時動，逐 hunk 寫明原因）

### 5.1 vitest（前端）

| 檔（盤點 §E-1 座標） | 處置 | 理由 |
|----|------|------|
| `IssuesView.test.tsx`（47-69、100、126、174…821 各列序斷言） | 不受影響（四分頁預設序皆不變；只增 AT-963-3-1～3-4） | D-UX-18；`:131-138` 八欄表頭字樣斷言不受影響（W-UX2 保 `textContent`） |
| `IssuePriorityDialog.test.tsx`（53…140） | 不受影響 | 預設序不變 |
| `issues.test.ts`（76-137） | 不受影響 | 顯示序兩條不改（D-UX-18）；`lib/domain/issues.ts` 不在本鍵任何持有面 |
| `issues.static.test.ts` | 不受影響 | 靜態規則與排序無關；若新增 `SortableHeader` 的 import 觸及其「元件 import 白名單」判準才改，改法只加成員 |
| `HistoryPanel.test.tsx`（51-65） | 改預期 | 預設請求改為 `sort=createdAt,asc`（AT-963-3-14 同檔擴充） |
| `ProjectsView.test.tsx`（97、107、139、155、168、184、189） | 改預期 | 預設 `sort` 由 `updatedAt,desc` 改 `createdAt,asc`、選項集合與下拉標籤改變、卡片序依建立順序（fixture 的 `[0]`、`[1]` 取用順序改取新順序） |
| `client.test.ts`（61-62）、`endpoints.test.ts`（36、103、433-436） | 不受影響 | 端點函式簽名與 URL 組裝不變（`sort` 由元件傳入；`lib/api/types.ts:63,92` 的 `sort?: string` 本就是字串）；只同步 `types.ts:86` 的註解（限 createdAt／status 的說法過時；QA F16） |
| `DashboardView.test.tsx`（276、321、369） | 不受影響 | 待審批清單為排除項（§2.3） |
| `MonitorView.test.tsx`（308、319-325、371-376） | 不受影響 | 時間軸、日誌、告警為排除項 |
| `BackupView.test.tsx`（87-99、88） | 不受影響（預設序與表頭序不變；`:99` 仍成立） | 例外表保留預設；`textContent` 不變 |
| `SiView.test.tsx`（125、238、948）、`SiStatusFilter.test.tsx`（107、140） | 不受影響；若黃金檔的壞列（`si-obs-invalid-<line>`）原位不在末端、或 fixture 帳本序與 ID 序不一致而紅 ⇒ 只改預期（W-UX3 壞列規則；QA F2） | 預設 ID 升冪與游標序在實際帳本一致 |
| `lib/domain/research.test.ts`（1457）、`lib/domain/si.test.ts`（1030-1048） | 不受影響；實際紅才改預期（PKG-FE-SORT 持有） | `research.test.ts:1457` 的 `filterProjects` 輸出序由「排序在元件層做、`filterProjects` 不排序」保證不變；寫入對帳為排除項（QA F9） |
| `ExecuteView.test.tsx`（359）、`SddEngineCard.test.tsx`（106、134）、`sdd.test.ts`（101） | 不受影響 | 排除項（還原點、SDD 決策列） |
| `ResearchListView.test.tsx`（222-224、438） | 改預期 | 預設列序由更新時間新到舊改為編號升冪 |
| `GatekeeperPanel.test.tsx`（426）、`HealingMonitor.test.tsx`（43-47）、`EvidenceTimeline.test.tsx`（253-259） | 不受影響 | 缺陷卡、Healing、時間軸為排除項 |
| `lib/help/content.test.ts`（:166 步數 2～8；AT_PH_03_5_1、AT_PH_03_5_E_1 的 9 項負控） | 改預期 | 勘誤 PH-1：上限 8→10；負控「9 項回非空」改為「11 項回非空、10 項回空」 |
| `lib/help/research-workspace.test.ts`（:37 `steps ≤ 8`；:124 占位欄位否定釘） | 改預期（:37 改 ≤ 10）；:124 不受影響 | 同上 |
| `lib/nav/research-nav.test.ts`（:196 ≥ 5、:216-218 的 2～8 與逐步 `lintText(maxSentences:1)`） | 改預期（:217 改 ≤ 10） | 同上；逐步單句規則不變 |
| `lib/help/registry.test.ts`、`components/domain/help/*.test.tsx`（`PageHelpDialog.test.tsx` 254-294） | 不受影響；若 fixture 頁的步數落在新界線外而紅，只改 fixture | 說明表 `th` 與狀態表鍵序不動 |
| `BackupView.test.tsx`（:623 `toHaveLength(3)`） | 不受影響 | 為備份還原步驟，非說明頁步驟 |

### 5.2 Playwright

| 檔（盤點 §E-2 座標） | 處置 | 理由 |
|----|------|------|
| `p4-execute.spec.ts`（276-277）、`execute.mock.spec.ts`、`monitor.mock.spec.ts`、`p5-monitor.spec.ts`、`p9-w7-sdd.spec.ts`、`settings.mock.spec.ts`、`p6-settings.spec.ts`、`dashboard.mock.spec.ts`、`notifications.mock.spec.ts` | 不受影響 | 目標、任務、監控、執行、設定、儀表板皆排除項；`crud-flow.spec.ts`（168-181 拖曳序不受影響；62、146 若用 `.first()` 取專案卡而紅 ⇒ 改為依專案名稱取）與 `p9-w5-a11y.spec.ts` 見下方「實際紅才改」列 |
| `p9-w5-ui-evidence.spec.ts`（255、416-425） | 改預期（255 的專案卡 `.first()` 改依名稱定位；416-425 任務序不受影響） | 專案卡預設序改為建立順序 |
| `import.mock.spec.ts`（339-341、470-482） | 改預期 | 歷史預設請求 `sort=createdAt,asc`、列序依建立順序 |
| `sysadmin-backup-docker.stack.ts`（67、78-79）、`sysadmin-backup.mock.spec.ts` | 不受影響 | 備份預設序不變 |
| `page-help.mock.spec.ts`（336-337） | 不受影響（另擴一案 AT-963-8-6） | 狀態表鍵序不變 |
| `crud-flow.spec.ts`（62、146）、`issues.mock.spec.ts`（`tabUntil` 走訪序）、`a11y.mock.spec.ts`、`p9-w5-a11y.spec.ts`（`import-history` axe 掃描） | 實際紅才改（只改定位方式或預期：表頭多了按鈕會改變 Tab 走訪序與 axe 母體） | PKG-E2E 持有（QA F9） |
| `research-docker.stack.spec.ts`（158）、`research-studio-perf.mock.spec.ts`（641-675） | 改預期（僅研究專案清單列序、證據表列序若有斷言）；其餘不受影響 | 研究專案列預設編號升冪、證據表預設編號升冪 |

### 5.3 後端 IT（盤點 §E-3）

| 檔 | 處置 | 理由 |
|----|------|------|
| `ProjectApiIT.java`（118-151 排序測試、187-188 非法 `sort`） | 不受影響（API 預設值與既有欄位語意不變）；187-188 若斷言錯誤訊息全文 ⇒ 改預期為新白名單訊息 | W-UX6 |
| `ProjectRestoreApiIT.java`（309、312） | 不受影響 | 還原不涉排序參數 |
| `ImportFlowApiIT.java`（251、558-565、585-591） | 不受影響；非法 `sort` 訊息全文若被斷言 ⇒ 改預期 | 預設 `createdAt,desc` 不變 |
| `ExecutionLifecycleApiIT.java`（323-331）、`ResponseEnvelopeIT.java`（55） | 不受影響 | 批次排序白名單不動；封包形狀不變 |

---

## 6. 凍結文件勘誤清單與 refreeze

> 勘誤文字由主控在 SCG-4 通過後寫入各凍結檔的〈勘誤〉表（本檔只是來源）；寫入後依下表 refreeze 對應的 FSM 鍵（`AgentConsole/build/reports/fsm/FSM-STATE-agentconsole-*.yaml` 現查：哪一把鍵的 `spec_frozen` 記錄含該檔）。🔴 **本輪 PRD §0.10 與 Architecture §5.5／§12.1 已進工作樹**，所以引用這兩檔的所有鍵都要 refreeze：PRD 被 exec-monitor-entry、fsm-trail、nav-consolidation、research-to-prd-p0／p1／p2 引用；Architecture 另加 si-decide-dedupe、si-decide、si-mirror。

| 編號 | 位置（盤點 §D 座標） | 勘誤文字 | 要 refreeze 的鍵（現查結果） |
|------|------------------------|----------|------------------------------|
| PH-1 | `TCS-PageHelp-20261027.md` R-PH-06（:161）與 AT-PH-03-5-1（:521）的 `steps` 2～8 | 「`steps` 2～8 項」改為「`steps` 2～10 項（鍵 `agentconsole-console-ux-sort-help` 起放寬，使專案管理與研發工作流能寫完整導覽；更嚴的 5～10 步與其他規則由 `readability.ts` 另守，`lint.ts` 規則不變）」；AT-PH-03-5-E-1 的 steps 負控「9 項」改為「11 項」 | page-help |
| PH-2 | `Console_PageHelp_PRD.md` AC-PH-03-5（:93）與對話框描述（:142）的「2～8 步」 | 同 PH-1 文字（改 2～10 步） | page-help |
| PH-3 | `TCS-PageHelp-20261027.md` D-PH-11（:89）`STATE_HELP` 每張表鍵順序＝顯示列序、R-PH-11（:171）詞表群順序 | **不改**；於勘誤表加註「本鍵改寫說明文案但不動鍵序與詞表群序；說明對話框內的表不加排序（排除項）」，使鎖與排序的界線可追溯 | page-help（與 PH-1 同次 refreeze） |
| IC-1 | `TCS-IssueCenter-20261027.md` R-IC-33（:235）顯示序兩條 | **不改**（D-UX-18）：四分頁預設序維持 R-IC-33 兩條；表頭排序是使用者動作、不改預設；根層 CLI `tools/lib/selfimproving/issues.py:281` 與前端 `lib/domain/issues.ts` 的「同表兩端驗」對拍鎖（`tools/tests/test_selfimproving_issues.py` AT-IC-05-1-1、前端 `issues.test.ts`）不動；於勘誤表只加註「表頭可點排序後畫面序暫離兩條規則，『還原預設排序』回到規則序」 | issue-center、nav-consolidation（僅因加註與 PRD／Architecture 變動） |
| IC-2 | `TCS-IssueCenter-20261027.md` R-IC-65（:292）八欄、R-IC-66（:293）置頂 | **不改字樣**；加註「八欄表頭 `textContent` 與順序不變（`SortableHeader` 保 `textContent`）；表頭另帶 `aria-sort` 與按鈕；全部分頁使用者排序時置頂列仍在頂端（W-UX4）」 | issue-center、nav-consolidation |
| BK-1 | `TCS-SysAdminBackup-20261027.md` AT-BK-02-1-2（:596）「列序與 API 回應序完全相同（前端不另排序）」；R-BK 的清單序條文（:176、:328） | 在「前端不另排序」前加「預設時」：「**預設時**列序與 API 回應序完全相同（前端不另排序；使用者按表頭後才改變畫面順序，且可按『還原預設排序』回到回應序）」；`BackupList.tsx` 檔頭「不另排序」註解同步改 | sysadmin-backup、nav-consolidation |
| API-1 | `API_Contract_P3-6.md` 專案列表 `sort` 白名單（:87、:653）、匯入歷史白名單（:729）；`openapi-p3-6.yaml`（:116、:610、:1123、:1905、:1925 對應列）；`ADR-002-Frontend-Design-System.md` :125「任務數排序因白名單不支援被『最近建立』取代」 | 專案白名單加 `autonomyLevel`；匯入白名單加 `sourceFileName｜aiModel｜tokenUsed｜projectId`；兩端點的預設值不變；非法值 400 訊息改列新白名單；ADR-002 :125 加註「排序控制列選項為 建立順序／名稱／狀態／最近更新／自治等級，任務數與目標數因衍生聚合值仍不開放」 | fsm-trail、research-to-prd-p0／p1／p2、si-decide、si-mirror（P3-6 與 openapi）；exec-monitor-entry、fsm-trail、research-to-prd-p0／p1／p2、si-decide、si-mirror（ADR-002） |
| RP-1 | `API_Contract_ResearchToPRD.md` API-RP-02（:282、:447）「清單不分頁、依更新時間新到舊」；`TCS-ResearchToPRD-P2-20261107.md` 的清單序條文（:403、:863、:1464） | 加註「**API 回應序不變**（更新時間新到舊）；UI 預設序改由前端依 `rpNo` 升冪排（D-UX-1）；使用者可由排序控制列改回『最近更新』」；P2 TCS 條文若斷言畫面列序＝回應序，加「預設時」限定（現查為準） | research-to-prd-p0、p1、p2 |
| EM-1 | `TCS-ExecMonitorEntry-20261101.md` W-E3（:70）「`steps` 三句」與 AT-953-3-1 的相關斷言 | 「steps 三句」改為「steps 5～10 步（鍵 `agentconsole-console-ux-sort-help` 起，D-UX-2）」；兩頁 `fields` 三項不變 | exec-monitor-entry |
| SI-1 | `API_Contract_SelfImproving_P1b.md`:53（游標序）、`TCS-SelfImprovingDecideDedupe`（:329 寫入對帳序）等 | **不改**：SI 四表 API 序不變、對帳清單為排除項；`Architecture §12.1 L-UX-1` 已記排序只作用於已載入列 | —（僅因 Architecture 變動被帶入 refreeze：si-decide-dedupe、si-decide、si-mirror） |
| NAV-1 | `TCS-ConsoleNavConsolidation-20261101.md`、`TCS-SelfImprovingMirror-P1b-20261021.md` 的導覽 order 條文 | 不改（本鍵不動導覽登記表）；僅因引用 PRD／Architecture 被帶入 refreeze | nav-consolidation、si-mirror |

**refreeze 範圍彙整**：以上合計涵蓋 `AgentConsole/build/reports/fsm/` 下**全部 12 把鍵**：exec-monitor-entry、fsm-trail、issue-center、nav-consolidation、page-help、research-to-prd-p0、research-to-prd-p1、research-to-prd-p2、si-decide、si-decide-dedupe、si-mirror、sysadmin-backup。另 `TCS-ResearchToPRD-P0／P1／P2` 與根 `ResearchToPRD_PRD.md` 是否釘住每頁說明字樣：**主控現查（2026-11-08）＝未釘住任何句子**（三份 TCS 只釘說明登記表的三道鎖與計數不變、「寫實內容」：AT-961-19-2、AT-962-25-1；根 PRD 與三份 TCS 皆無「目前開放前兩步」字樣），不需勘誤；research-to-prd 三鍵仍因 PRD／Architecture 變動進 refreeze。

---

## 7. 測試資料規格、派工包與持有檔案面

### 7.0 常數
排序預設值：專案與匯入 `createdAt,asc`；方向按鈕兩句 `aria-label`（W-UX5）；還原鈕文字「還原預設排序」與 `data-testid="sort-reset"`；詞表名稱 `ACTION_WORDS`、`MUST_EXPLAIN`、`JARGON_BANNED`、`IMPLEMENTATION_WORDS`、`STALE_PHRASES`、`SORTABLE_HELP_PAGES`。

### 7.1 派工包與持有檔案面（路徑相對 `AgentConsole/`；**四包持有面兩兩不重疊**，鐵律七）

**PKG-BE-SORT**（backend，Java；與前端兩包無檔案交集）
- 持有：`backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java`、`ImportController.java`（`sort` 解析與訊息、`SortField` 列舉所在檔）、`adapter/out/persistence/ProjectRepositoryAdapter.java`、`ImportRecordRepositoryAdapter.java`、兩者查詢埠的 `SortField` 列舉定義檔（現查 `grep SortField`）、`backend/src/test/java/**` 中的 `ProjectApiIT.java`、`ImportFlowApiIT.java`（AT-963-5-1～5-E-2 與 §5.3 同步）。
- 禁動：`ResponseEnvelopeIT`、`ExecutionLifecycleApiIT`、`ProjectRestoreApiIT`（不受影響）、Flyway 遷移（`autonomyLevel`、`sourceFileName`、`aiModel`、`tokenUsed`、`projectId` 皆既有欄位；若發現需要新欄，停下回報）、`frontend/**`、`engine-bridge/**`、docs。
- 驗證指令：
  ```powershell
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\backend; .\gradlew.bat test --tests '*ProjectApiIT' --tests '*ImportFlowApiIT'; Pop-Location
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\backend; .\gradlew.bat clean build; Pop-Location
  ```
  （IT 需本機 Docker／測試容器可用；起不來要在交卷明說，不得宣稱已驗證。）

**PKG-FE-SORT**（frontend 排序）
- 新檔：`frontend/lib/domain/sorting.ts`、`sorting.test.ts`、`lib/domain/sortScope.static.test.ts`、`components/domain/common/SortableHeader.tsx`、`SortableHeader.test.tsx`、`SortBar.tsx`、`SortBar.test.tsx`。
- 改檔（排序接入）：`components/domain/issues/IssueTable.tsx`、`IssuesView.tsx`（排序欄位定義放元件內；`lib/domain/issues.ts` 的 `sortIssues`／`displayOrder`／`compareHistory` 一字不動，D-UX-18）；`components/domain/si/SiObservationsPanel.tsx`、`SiProposalsPanel.tsx`、`SiEventsPanel.tsx`；`components/domain/sysadmin/BackupList.tsx`；`components/domain/research/AllowlistDialog.tsx`、`TraceabilityTable.tsx`、`EvidenceMatrixTable.tsx`、`ResearchListView.tsx`；`components/domain/import/HistoryPanel.tsx`；`components/domain/views/ProjectsView.tsx`；`lib/api/endpoints.ts`、`lib/api/queries.ts`、`lib/api/types.ts`（只放寬 `sort` 參數型別與預設傳入值）。
- 改檔（既有測試同步，§5.1 標「改預期」者的元件測試）：`IssuesView.test.tsx`（只增 AT）、`HistoryPanel.test.tsx`、`ProjectsView.test.tsx`、`ResearchListView.test.tsx`，以及 AT-963-3-5～3-13 所在的 `SiView.test.tsx`、`SiStatusFilter.test.tsx`、`BackupView.test.tsx`、`AllowlistDialog.test.tsx`、`TraceabilityTable.test.tsx`、`EvidenceMatrixTable.test.tsx`（只增 AT、不刪斷言）；`lib/domain/research.test.ts`、`lib/domain/si.test.ts` 與 `lib/api/types.ts:86` 註解（實際紅或過時才改；QA F9、F16）。
- 禁動：`lib/help/**`、`lib/nav/**`、`components/domain/help/**`、`tests/e2e/**`、backend、`ToolsRegion.tsx`、`TopRegion.tsx`、`layout.tsx`、`lib/domain/research.ts`（排序欄位定義放元件內，`filterProjects` 不排序）、`lib/domain/issues.ts`（D-UX-18）、根層 `tools/**`。
- 驗證指令：
  ```powershell
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx vitest run lib/domain/sorting.test.ts components/domain/common; Pop-Location
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx vitest run; Pop-Location
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx tsc --noEmit; npm run lint; Pop-Location
  ```
  （`tsc` 與 `lint` 的 rc 各自讀，不接管線。）

**PKG-FE-HELP**（frontend 說明文案）
- 新檔：`frontend/lib/help/readability.ts`、`readability.test.ts`、`pageFacts.test.ts`。
- 改檔：`lib/help/*.ts` 二十二頁檔與 `common.ts`、`states.ts`（文案改寫；`id`、`title`、欄位名與 `sourceFiles`、狀態表鍵序不動，欄位名仍須在 `sourceFiles` 內出現）；`lib/help/content.test.ts`（步數界線與負控，§5.1）、`lib/help/research-workspace.test.ts`（:37）、`lib/nav/research-nav.test.ts`（:217 一行界線）；`components/domain/help/*.test.tsx` 只在 fixture 因新界線而紅時改 fixture。
- 約束：不新增以「建立順序」「排序控制列」等新字樣為名的欄位（那些字樣由 PKG-FE-SORT 同期落地；排序教學只寫在 `steps` 與既有欄位 `meaning`，避免出處鎖互相等待）；不改 `lint.ts`、`types.ts`、`registry.ts`（頁數與 id 不變）；不動 `components/domain/help/*.tsx` 非測試檔；`research.ts` 必須移除「目前開放前兩步」。
- 禁動：`lib/domain/**`、其他 `components/**` 非測試檔、`tests/e2e/**`、backend。
- 驗證指令：
  ```powershell
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx vitest run lib/help lib/nav components/domain/help; Pop-Location
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx vitest run; Pop-Location
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx tsc --noEmit; npm run lint; Pop-Location
  ```
- 交卷額外附：每頁一行摘要（步數、purpose 句數、是否通過 `readability`）與 `research`、`research-workspace`、`projects` 三頁全文（供 SCG-4 人讀把關「看／填它時要注意什麼」這一面）。

**PKG-E2E**（Playwright；三包收工且主控親驗後才派）
- 新檔：`frontend/tests/e2e/console-sort.mock.spec.ts`（AT-963-8-2～8-5）；新 spec 自帶夾具（議題、備份、專案、研究清單四組，既有 spec 的夾具是各檔內部函式、不可重用），專案 mock 必須依請求的 `sort` 參數排序（AT-963-8-2 要看到順序真的改變）；可新增 `tests/e2e/sortFixtures.ts`；只重用 `mockApi.ts` 的 `installApiMock`／`compose`／`shellHandler`／`signInAs`，**不改 `mockApi.ts`**（QA F10）。
- 改檔：`tests/e2e/page-help.mock.spec.ts`（擴 AT-963-8-6）、§5.2 標「改預期」的 `p9-w5-ui-evidence.spec.ts`、`import.mock.spec.ts`、`research-docker.stack.spec.ts`、`research-studio-perf.mock.spec.ts`（只改預期值）；`crud-flow.spec.ts`、`issues.mock.spec.ts`、`a11y.mock.spec.ts`、`p9-w5-a11y.spec.ts` 實際紅才改（只改定位方式或預期；QA F9）。
- 禁動：`frontend/**` 非 e2e 檔、backend、docs。
- 驗證指令（設定檔與 script 名以 `package.json` 為準，先 `npm run` 現查；並行必帶各自 `--output` 目錄，避免共用 `test-results` 被清空）：
  ```powershell
  Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx playwright test tests/e2e/console-sort.mock.spec.ts tests/e2e/page-help.mock.spec.ts --output <暫存目錄>\pw-out; Pop-Location
  ```
  Docker 全棧型 spec（`*.stack.spec.ts`）由主控於 §8.2 V2 跑，開發棒只改預期。

### 7.2 交卷格式（四包共同；純文字，不寫報告檔，鐵律 9）
1. 改了哪些檔（路徑；新增或修改；行數）；是否全在持有面內（附 `git diff --name-only` 逐字輸出）。
2. 逐 AT：測試名、指令、rc、輸出尾段逐字（附當回合真跑的輸出，不得轉述）；未跑的明說。
3. §5 連動：逐檔「改了／沒改」與每個 hunk 的原因；每檔 `expect(` 與 `it(`／`test(` 呼叫數新 ≥ 舊（附兩個數字）。
4. 勘誤候選（規格與現碼不符處）、〈Windows 接續注意〉、未結事項。
5. 不 commit、不 push、不派子代理、不自架背景等待。

---

## 8. RTM 連結確認

### 8.1 追溯
RTM 子表 `AgentConsole/docs/06_quality/RTM-ConsoleUxSortHelp-20261108.md`（F 1、US 1、AC 9、AT 56，共 67 列；由主控依 RTM 子表體例建，`RTM.md` 存根連到它，ID 加反引號故不計入總列數）。

### 8.2 V 系列：實查檢核（主控、掌舵者；**不是 AT**）
- V1 真機：Docker 全棧重建 frontend 後，在 `/projects`、`/issues`、`/import`、`/research`、`/sysadmin/backup` 各點一次排序，確認預設序與表頭／控制列行為與 §2 相符（主控 Playwright 探針或掌舵者目視；截圖不入庫）。
- V2 真機 E2E：`console-sort.mock.spec.ts`、`page-help.mock.spec.ts` 綠；Docker 全棧型 spec（`research-docker.stack.spec.ts`、`sysadmin-backup-docker.stack.ts`）對全棧跑綠。
- V3 說明文案人讀：掌舵者或主控讀 `projects`、`research`、`research-workspace` 三頁說明，確認「國高中看得懂、照著做能走完一遍」；`readability` 只能守可測的面（句長、術語、結構），「看／填它時要注意什麼」是否寫得到位只有人讀能判。
- V4 文件：PRD §0.10、Architecture §5.5 與 §12.1 L-UX-1、本檔 §6 全部勘誤、RTM 子表與存根、`API_Contract_P3-6` 與 `openapi-p3-6.yaml` 白名單條文、12 把鍵 refreeze 皆已落地。
- V5 容器卷與暫存清理：真機跑完後依 repo 慣例清理用完的測試暫存（QA 副本、閒置行程、`suite_tmp_*`）。

---

## 9. 裁決表與〈待主控裁決〉

### 9.1 裁決表

| ⚖ | 裁決 | WHY |
|----|------|------|
| D-UX-1 | **排序政策＝方案 A**（掌舵者已裁；全文見 PRD §0.10） | 掌舵者原文裁決 |
| D-UX-2 | **說明文案標準**（主控預決；全文見 PRD §0.10；機械規則 R-UX-H1～H9） | 掌舵者要求可讀性可驗，可驗才不會下輪又退化 |
| D-UX-3 | 範圍＝有表頭 `<table>` 加專案卡片與研究專案列；日誌、告警、時間軸、修改歷史、寫入對帳視為「事件序清單」排除 | 它們沒有表頭、語意是時間序；日誌端點已有 `order` 參數；硬加欄位排序會與既有 `order` 參數並存兩套語意 |
| D-UX-4 | 排序狀態只在記憶體，不入網址、不持久化；議題切分頁即重置 | 網址目前不承載列表狀態，加參數就多一份要對齊凍結契約的面；分頁預設序不同，沿用上一分頁的排序會讓預設序說不清 |
| D-UX-5 | 允許清單（無編號欄）以「主機」當識別欄，預設主機自然序升冪 | 主機是條目的唯一鍵，使用者找條目也靠主機；保持 API 序則無法回答「預設依什麼排」 |
| D-UX-6 | 排序鍵循環＝升冪↔降冪兩態；例外表另設「還原預設排序」文字鈕，不做第三態 | 三態循環（升→降→預設）讓 `aria-sort` 語意與使用者預期脫節；例外表才有「預設不是任何一欄」的問題，所以只在它們出現還原鈕 |
| D-UX-7 | 空值一律排最後（不論升降冪）；tie-break 一律識別欄升冪 | 沿議題表既有規則（`nullsLast`、`id` 升冪）一致化；降冪時把空值翻到最前會讓最有資訊的列被擠下去 |
| D-UX-8 | `Intl.Collator("zh-Hant", { numeric: true })` 同時服務 `id` 與 `text` | 編號如 `RP-0009`、`ID-99` 要自然序；中文欄要依注音序，兩者同一 collator 最少規則 |
| D-UX-9 | 後端白名單只加現有欄位：專案 `autonomyLevel`、匯入 `sourceFileName｜aiModel｜tokenUsed｜projectId`；不加 `goalsCount`／`tasksCount`／`executionPath`／已刪除模式的刪除時間 | 衍生聚合欄排序要改查詢形狀、拖慢每次列表；路徑與刪除時間不是找專案的依據；白名單越小，契約與測試面越小 |
| D-UX-10 | 專案卡片與匯入歷史的「建立順序」預設由前端明確送 `createdAt,asc`；API 預設值不變 | 改 API 預設會連動契約、openapi、IT、凍結 TCS 多處；前端明確送值只動一層 |
| D-UX-11 | `th` 的 `textContent` 不變（不加 sr-only、不加 `aria-label`），排序狀態只用 `aria-sort` 傳達 | 議題八欄、備份十欄的表頭字樣鎖是凍結條文；`aria-sort` 就是標準的可及性表達 |
| D-UX-12 | 說明新規則疊加於 `lint.ts`，不改 `lint.ts` 常數；唯一勘誤＝`steps` 上限 2～8 放寬為 2～10 | 動 `lint.ts` 會連動 PRD §8.3 白名單與 `lint.test.ts` 對照；專案管理與研發工作流要完整導覽，8 步不夠 |
| D-UX-13 | 句長以 code point ≤ 40 計（半形字也算 1） | 與 `lint.ts` 同一量法，只收緊上限，不引入第二種字寬算法 |
| D-UX-14 | 「Gate」等白名單外英文不進說明句，只留在欄位名；說明句改用「規格核准」等白話 | `lint.ts` 英文白名單是凍結規則；白話本來也符合國高中讀者 |
| D-UX-15 | 排序教學放在 `steps` 與既有欄位 `meaning`，不新增以排序新字樣為名的欄位 | 欄位名須在 `sourceFiles` 出現（出處鎖）；文案包與排序包並行時會互相等待 |
| D-UX-16 | 全部分頁置頂列在使用者排序時仍留頂端 | 置頂是「待您決定」的注意力區（R-IC-66），被排序沖走會讓需要人決定的事看不見 |
| D-UX-17 | SI 四表不新增後端 `sort`，排序只作用於已載入列（Architecture L-UX-1） | 改 Bridge 契約超出本鍵；預設序與游標序一致，預設畫面無落差 |
| D-UX-18（主控 2026-11-08） | **議題表四分頁預設序全部維持 R-IC-33 兩條**（已完成／全部仍為最後更新降冪→編號升冪），整張表列為例外：只加表頭排序與「還原預設排序」，不改 `lib/domain/issues.ts`、不勘誤 R-IC-33 第二條 | 顯示序兩條住根層 CLI `tools/lib/selfimproving/issues.py:281` 與前端 `issues.ts`，以同一張範例表在兩端驗（`tools/tests/test_selfimproving_issues.py` AT-IC-05-1-1、前端 `issues.test.ts`）；只改前端半邊會破對拍、改根層則動到護欄層與 SI 不可演化面，都超出本鍵 |
| D-UX-19（主控 2026-11-08） | 專案卡片與匯入歷史預設＝建立順序**升冪**（最新在最後），照掌舵者 D-UX-1 原文；V1 目視若掌舵者改口，只改一個常數與 AT-963-4-1／3-14 預期值 | 「依 ID 預設排序」字面即升冪；不替掌舵者猜偏好 |
| D-UX-20（主控 2026-11-08） | 允許清單以「主機」為識別欄（同意 D-UX-5） | 條目唯一鍵即主機 |
| D-UX-21（主控 2026-11-08） | `steps` 上限 2～10 的勘誤落點照 §5.1／§6（PH-1、PH-2、EM-1 與兩個釘 8 步的測試），不另開 PRD 增補 | §0.10 已載明唯一勘誤即步數上限 |
| D-UX-22（主控 2026-11-08） | 接受 12 把鍵 refreeze（§6 彙整），維持 §0.10 住 PRD §0、§5.5 住 Architecture 的體例 | refreeze 是 CLI 一次操作；把規格搬到旁檔只為省 refreeze 會讓 PRD §0 凌駕體例出現第一個例外 |

### 9.2 待主控裁決（≤ 5 題；規格棒已給預設，可推翻）

1. **專案卡片「建立順序升冪」會把最新專案放到最後面**（D-UX-1 方案 A 的直接後果；現在預設是最近更新在前）。預設保持升冪（照掌舵者裁決）？或預設 `createdAt,desc` 並仍標示為「建立順序」？規格棒預設：照裁決升冪，並在 V1 請掌舵者目視確認；若不喜歡，改一個常數即可（`createdAt,desc`），規格連動只有 §2.2 L1 與 AT-963-4-1／3-14 的預期值。
2. **匯入歷史的預設同樣改為建立順序升冪**（現為新到舊）。同上；預設照裁決。
3. **允許清單以「主機」為識別欄**（D-UX-5）是否同意？替代＝保留 API 序為預設並在例外表登記。
4. **steps 上限 2～10 的勘誤落點**：除 TCS-PageHelp、Console_PageHelp_PRD 外，`research-nav.test.ts:217`、`research-workspace.test.ts:37` 也釘 8 步；規格棒已列入 §5.1，請確認不另開 PRD 增補。
5. **12 把鍵全部 refreeze 的成本**：因 PRD §0.10 與 Architecture §5.5 已進工作樹而無法避免；若希望縮小，可改把 §0.10 與 §5.5 搬到不被任何鍵凍結的新檔（例如 `docs/01_requirements/ConsoleUxSortHelp_Addendum.md`），但與 §0.7～§0.9 的「PRD §0 凌駕後文」體例不一致。規格棒預設：維持現狀、接受 12 鍵 refreeze。

**主控裁決（2026-11-08，見 §9.1 D-UX-18～D-UX-22）**：1、2 照升冪（D-UX-19）；3 同意（D-UX-20）；4 同意、不另開增補（D-UX-21）；5 接受 12 鍵 refreeze（D-UX-22）；另加 D-UX-18：議題表四分頁預設序全部不改、整張表列為例外（W-UX4、§2.1 T2、AT-963-3-2／3-4、§5.1、§6 IC-1 已同步改寫）。

---

## 📋 SCG-4 通過標準

1. §4 全部 AT 綠：vitest 全套、`tsc`、`lint` 皆 rc 0；後端 `gradlew clean build` rc 0 且兩個 IT 綠；Playwright mock spec 綠；E2E 全棧型 spec 對 Docker 全棧綠（§8.2 V2）。
2. §5 同步只改預期值、零刪斷言（AT-963-8-1）；各包持有面以外零差異（`git diff --name-only` 核對）。
3. §6 勘誤與 12 把鍵 refreeze 全部落地（§8.2 V4）。
4. §8.2 V1、V3 由主控與掌舵者實查完成。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| 編號 | 位置 | 原文 | 改為 | 依據 |
|------|------|------|------|------|
| E-1 | W-UX1(a)、AT-963-1-1、D-UX-8（Architecture §5.5 同句同步） | 自然序範例用了觀察帳本 id 的樣式（`OBS-SI-` 後接 99 與 100） | `ID-99` < `ID-100` | 2026-11-08 規格 commit 8e7cbabe 推送被 pre-push 擋：根層 `si check` 的 `ref.obs` 把該範例判為 OBS-REF-DANGLING（帳本無此 id；規格、勘誤表與測試碼一律不得寫真實帳本 id 樣式的範例，連本列原文欄也不能逐字引）；凍結後訂正，於 RELEASE_READY 連同 §6 勘誤批次 refreeze |
