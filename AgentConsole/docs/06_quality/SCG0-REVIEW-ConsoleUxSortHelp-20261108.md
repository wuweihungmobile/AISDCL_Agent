# SCG-0～3 規格獨立審查 — Console 資料列表排序與每頁說明文案改寫（鍵 `agentconsole-console-ux-sort-help`）

> 審查者：QA 鏡（Sonnet 子代理，與規格棒、開發棒皆為不同代理）；全程唯讀、未跑測試或編譯。審查對象＝工作樹上的 Console PRD §0.10、`Architecture.md` §5.5 與 §12.1、`TCS-ConsoleUxSortHelp-20261108.md`（Stage-1／Stage-2 凍結前）。本檔由主控依審查者純文字交卷落檔（鐵律 9）；逐字稿座標 sid `3d200496-a6dd-47e0-9921-b3904cf412ac`。

## 一審（2026-11-08 23:3x）：FAIL（P1 0／P2 3／P3 11／P4 3）

主控點名的「最可能 P1」（`<th>` 內加 `<button>` 會改變 `columnheader` 可及名稱而紅）**不成立**：議題八欄鎖 `IssuesView.test.tsx:134-138`、備份十欄鎖 `BackupView.test.tsx:94-98`、追溯表鎖 `TraceabilityTable.test.tsx:84-88` 都以 `getAllByRole("columnheader").map(h => h.textContent)` 斷言，不用 role name；全 repo 的 `columnheader, { name }` 只在 `markdown.test.tsx:225,569`。

| # | 級 | 位置 | 問題 | 改法（已由主控套入；對應 TCS 行內標「QA Fn」） |
|---|----|------|------|------|
| F1 | P2 | W-UX1(h)、W-UX2、AT-963-1-4；Arch §5.5 | `nextSort(null, key)` 恆回升冪，但預設欄已顯示 `aria-sort=ascending`：第一次點預設欄畫面不變、後端表多打一次相同請求 | `nextSort(state, key, defaultSort?)`，有效狀態＝`state ?? defaultSort`；新增 AT-963-1-5；AT-963-3-5／3-14 補「首次點預設欄即反向」；Arch §5.5 同步 |
| F2 | P2 | §2.1 T3／T4、W-UX1、§5.1 | SI 觀察表壞列（`SiInvalidRow`，無 id）在預設序與使用者排序時的落點未定；黃金檔斷言含壞列位置 | W-UX3：壞列不參與排序、恆在有效列之後、依 `line` 升冪；T3、AT-963-3-5、§5.1 同步 |
| F3 | P2 | §2.1 T7 vs W-UX1(f)、AT-963-1-3 | 備份 tie-break 一處寫標籤降冪、一處規定識別欄升冪，互相矛盾 | `SortColumn.tieDir`（預設升冪、不隨升降冪翻轉；備份標籤 `desc`）；AT-963-1-3、3-9 補例 |
| F4 | P3 | R-UX-H3 | 「含任一動作詞」的子字串比對比「以動作開頭」弱 | 加註機械近似、真正把關靠 V3 人讀 |
| F5 | P3 | AT-963-6-E-1 | 「看看清單」未給期望值 | 三個例子補期望值 |
| F6 | P3 | R-UX-H5 | 未定義比對方式與引號內是否算出現 | ASCII 詞以非英文字母為界；「」內也算 |
| F7 | P3 | AT-963-3-E-1 | 檔級掃描做不到「同檔內某張表不在集合」；十一張表住九個檔 | 改為九檔集合逐名列出；優缺點矩陣改由 AT-963-3-13 釘 |
| F8 | P3 | W-UX6、AT-963-5-1／5-2 | `status` 依列舉名排、`projectId` 為 UUID、PG collation 與前端 collator 不同、Java 與 PG 的 uuid 序不同 | W-UX6 登記已知差異、Arch §12.1 新增 L-UX-2；IT 以小寫十六進位字串比 id、夾具限 ASCII |
| F9 | P3 | §7.1、§5.2 | `lib/domain/research.test.ts`、`si.test.ts`、`crud-flow.spec.ts`、`issues.mock.spec.ts`、`a11y.mock.spec.ts`、`p9-w5-a11y.spec.ts` 未指明歸屬 | 前兩者入 PKG-FE-SORT、後四者入 PKG-E2E（實際紅才改） |
| F10 | P3 | AT-963-8-2～8-5 | 既有 spec 的夾具是檔內函式不可重用；專案 mock 未要求依 `sort` 排序 | PKG-E2E 自帶夾具、可新增 `sortFixtures.ts`、不改 `mockApi.ts`、專案 mock 依 `sort` 排序 |
| F11 | P3 | AT-963-3-14、4-1 | 既有斷言比的是編碼字串 `createdAt%2Cdesc` | 以 `URLSearchParams` 解碼後比對 |
| F12 | P3 | W-UX8、AT-963-8-1 | 「被刪 expect 行＝0」在改預期值時不可能成立 | 改為 `expect(`／`it(` 呼叫數新 ≥ 舊 |
| F13 | P3 | PRD D-UX-1 | 例舉「來源編號」「交付／PRD 版本」無對應表 | 改為證據編號、擷取編號、追溯表 AC 編號 |
| F14 | P3 | D-UX-2 | 未提醒既有 AT_PH_05_1_1（meaning ≤ 2 句等） | §3.1 末加註既有鎖同時有效 |
| F15 | P3 | AT-963-7-4 | 議題頁「排序」與「優先順序」欄的「排序」鈕同詞 | 排序教學句必含「欄位標題」；優先序用「排列順位」 |
| F16 | P4 | §5.1 | `listImport` 的 `sort` 型別本就是字串 | 改為同步 `types.ts:86` 過時註解 |
| F17 | P4 | PRD D-UX-2 | 「全形計」與 TCS「code point」量法不同 | PRD 改 code point |
| F18 | P4 | §2.1 T3 | SI 時間欄非 ISO，`iso` 退路未釘 | AT-963-3-5 加「字串序＝時刻序」 |

審查者抽讀 22 條 AT（每個 AC 至少一條）、核對 F-909／US-929／AC-963 未撞號、AT-963-6-E-1 數字門檻與 R-UX-H 一致、§2.1 五張以上表的 testid／欄名、`lint.ts` 英文白名單含 `MUST_EXPLAIN` 全部 16 詞、釘 8 步的三個測試行號、後端 `SortField` 列舉與實體欄位、R-IC-33 兩端驗鎖在 D-UX-18 下不受影響、Playwright mock 機制。誠實劃界：未跑測試；後端 `NULLS LAST` 可行性只憑讀碼。

## 二審（2026-11-08 23:5x）：PASS（P1 0／P2 0／P3 0／P4 3）

- F1、F2、F3 消除（逐行核對 W-UX1(h)、AT-963-1-5、W-UX2、AT-963-3-5／3-14、Arch §5.5；W-UX3、T3、§5.1；`tieDir`、T7、AT-963-1-3／3-9）。
- 未引入新矛盾：`tieDir` 預設 asc 與 AT-963-1-3 原文並存；九檔集合與 §2.1 T1～T11 逐一對上；AT 總數重點數＝正控 47＋負控 9＝56，檔頭、FRD、§1、§4.1、§8.1 一致；§7.1 持有面無重疊；L-UX-2 與 W-UX6 一致。
- 剩餘 P4 三項（N1 匯出清單簽章、N2／N3 §5 兩處重複列）由主控於凍結前改掉。

## 主控處置

- 一審 18 項與二審 3 項全部套入工作樹（TCS 行內標「QA Fn」；N1～N3 已改）；主控裁決 D-UX-18～D-UX-22 住 TCS §9.1。
- 依凍結常態規則（根 CLAUDE.md；審查 PASS＋主控親驗：三檔零 CR／零 BOM、AT 定義 56 條無重複）由主控代執行 Stage-1（Console PRD、Architecture）與 Stage-2（本 TCS）凍結；FSM 鍵 `agentconsole-console-ux-sort-help`。
