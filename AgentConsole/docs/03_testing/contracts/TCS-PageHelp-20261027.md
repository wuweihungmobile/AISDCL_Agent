# Test Contract Specification — Console 每頁說明（Page Help）：頂列單一「本頁說明」鈕、每頁說明項與全站共通、狀態詞登記表與鍵鎖、白話檢查、路由與導覽三道鎖
# 測試契約規格文件（新功能；FRD-lite 併入檔頭；一份 TCS 涵蓋一把 SDD 鍵 `agentconsole-page-help`）

> **上位 PRD digest**：`sha256:cf1e97a9e5b666daef3024b13bc15a6903a6097f63a8dd8a24051813c899e3d0`（`docs/01_requirements/Console_PageHelp_PRD.md` v0.3＋〈勘誤一〉1-1～1-12＋〈勘誤二〉2-1；LF-only，62,607 bytes；2026-10-28 SCG-4 二審 PASS 後依〈凍結後修訂路由〉第 4 點同步更新；Stage-2 原值 `sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f`（62,015 bytes，含〈勘誤一〉）；Stage-1 凍結值為 `sha256:76768d1bf8d4a34deb22acb79e30b548acf6ffed6e03e69fc43b5389641a7a77`（56,565 bytes，commit `000a217b`）；FSM 狀態檔不由本檔作者直讀〔R-9.6〕）。本檔不改 PRD 正文；PRD 的問題一律寫 §7.3（已寫成可貼進 PRD 檔尾〈勘誤〉節的條文），凍結後走 PRD〈勘誤〉。
> **範圍**：PRD 的 8 個 FR、43 條 AC 全覆蓋；零 API、後端、Bridge、契約檔與 ADR；唯一新增的網路請求是議題中心詞表的唯讀 `GET /api/v1/issues?limit=1`（AC-PH-06-3）。**不含**登入頁（`/login`）說明、即時數字、50 個系統參數逐鍵說明、FSM 原始狀態全表（PRD §3）。
> **與姊妹案的關係**：`Console_SysAdmin_Backup_PRD.md`（鍵 `agentconsole-sysadmin-backup`）會加導覽項 `sysadmin` 與兩條路由；先落地者占號、後落地者補說明項與欄位列（PRD D-12、備份案 D-BK-10 (i)）。**本檔所有 AT 的斷言一律由登記表、路由表、導覽登記表推導，不寫死件數**；唯一的釘值是 §5.3 的必備子集（只准增不准減）與 PRD 明寫的白名單、六類資料來源、四個議題狀態詞門檻，兩案落地先後都綠。

## 文件資訊

| 項目 | 內容 |
|---|---|
| 檔案 | `AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md`（新；SDD Stage-2 契約。路徑依 PRD §5 檔頭、§9 文件列與 BRIDGE §8.1〈`agentconsole` 專案文件根＝`AgentConsole/docs/`〉，先例 `TCS-FsmTrail-20261018.md` 同目錄） |
| 版本與狀態 | v0.3 草案（2026-10-28；一審 FAIL〔P2 3、P3 11、P4 1〕與抽驗 FAIL〔#2、#3 各殘一個 P2〕後修訂，皆已修畢）；待 Stage-2 凍結（單鍵）；2026-10-27 起草；作者角色＝QA Engineer（Sonnet 5.5，依主控任務書）；〈勘誤〉節凍結前留空 |
| 上位規格 | `docs/01_requirements/Console_PageHelp_PRD.md` v0.3（digest 見檔頭）；先例 TCS：`docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（節體例、前端詞表與測試鉤、檔案集合）、`AgentConsole/docs/03_testing/contracts/TCS-FsmTrail-20261018.md`（Console 單半先例） |
| SDD 鍵（BRIDGE §8，一功能一鍵） | `agentconsole-page-help`（Console 單半；徑②：TypeScript 標的，session 內自跑 `vitest run`、`playwright test`、`tsc` 並逐字貼證據，BRIDGE §8.6 第 4 點） |
| 規模 | R 條文 37 條；AT 118 個（正向 77、反向 41）；AC 43／43 全覆蓋（§1、§6）；新增測試檔 8 個（vitest 7＋Playwright 1，PRD §9 的檔案集合，不多不少）、另改既有 1 個（`si.static.test.ts`，D-PH-18）；新增 vitest 約 97 個測試案例、Playwright 10 個；閘門指令一組（SCG-4 通過標準） |
| 載具與判定指令 | vitest（`npx vitest run <檔> -t "<AT 底線形>"`）；型別鎖（`npx tsc --noEmit`，tsc 含測試檔）；Playwright route mock（`npx playwright test tests/e2e/page-help.mock.spec.ts -g "<AT 底線形>" --output <各自目錄>`，CI 以 standalone 產物跑）；審查閘（G 編號指令）。細節見 §2、§3.1 |
| 讀法 | 開發棒分四棒串行（PRD §11 的輪 1 在本檔切成 1a、1b；§6.4）：輪 1a＝`lib/help` 框架、全部狀態表、先導三頁（`issues`、`projects`、`settings`）、`stateSources`、`si.ts` 匯出與 `si.static.test.ts` 同步鎖；輪 1b＝元件、`TopRegion` 接入與 e2e（八個測試檔於 1a、1b 建好，斷言皆由登記表推導，後兩輪只加頁檔與登記）；輪 2＝專案家族、匯入與儀表板；輪 3＝執行、監控、自我進化與全站驗收。每個 AT 的「輪」欄＝該 AT 自哪一棒起必須綠且非空轉 |

### 凍結後修訂路由（單鍵；先例 `TCS-IssueCenter-20261027.md` 同名節縮為一鍵）

1. 本檔（TCS）的勘誤：落本檔〈勘誤〉節並附新 digest，由 `agentconsole-page-help` `spec-refreeze`（依根 CLAUDE.md〈凍結常態規則〉：審查 PASS 且主控親驗無 P1、P2 才代執行）。
2. 上位 PRD 的修訂（PRD 已凍結、不可原地改）：依 PRD §13.2.1 只走 PRD〈勘誤〉節（§7.3 已備好條文，由主控貼入），並同步更新本檔檔頭 digest、再 refreeze。
3. 與姊妹案同批的共用規則（D-12）：姊妹案先落地時，後落地者（本案）rebase 後只補 `lib/help/sysadmin*.ts` 與兩條路由樣板、必要時重填 `PENDING_HELP_PAGES` 並**同 commit 上修 `PENDING_CEILING`**（見 D-PH-14）；姊妹案若動到 `lib/nav/registry.test.ts` 的「恰八項」釘值，那是姊妹案自己的同步鎖，不屬本檔的變更集合。
4. 開發棒不得自行改本檔；AT 與生產碼對不上時，開發棒回報主控，由 QA 走勘誤（談判閘 `negotiate-enter`，BRIDGE §8.6 第 2 點）。

## 增量變更專用：FRD-lite 與〈增量追溯表〉

### FRD-lite

**Before／After（現值皆於 HEAD `000a217b` 實查）**

| 面 | Before | After |
|---|---|---|
| 頂列右側群組（`TopRegion.tsx:145-157`） | 兩個動作：通知鈴（`button`，`bell-trigger`）、待審批佇列（`Link`，52px 圓鈕） | 末端多第三個：`<PageHelpButton />`（`button`，`data-testid="page-help-open"`，文字「本頁說明」，圖示 `BookOpen`）；只在 `showTools` 分支內渲染（`TopRegion.tsx:38、113`），以 `next/dynamic` 載入（D-PH-17） |
| 說明入口 | 公告列靜態「幫助中心」（不可點，契約 G-G5，`TopRegion.tsx:68-71`）；議題中心「狀態說明」鈕（`IssuesView.tsx:362-364`，`IssueLegend` 對話框） | 另有全站一顆「本頁說明」；議題中心既有「狀態說明」鈕與其測試不變（Q4），兩處共用同一份 API `legend` |
| `AgentConsole/frontend/lib/help/` | 不存在 | 框架檔 5 支（`types`、`states`、`common`、`registry`、`lint`）＋每頁一檔 `<id>.ts`（撰寫時 16 檔；件數由登記表推導） |
| `components/domain/help/` | 不存在 | 4 支：`stateSources.ts`、`PageHelpButton.tsx`、`PageHelpDialog.tsx`、`IssuesLegendGroups.tsx`（`components/layout` 維持恰四個元件檔，`layout.test.tsx:71-74` 不受影響） |
| 路由與說明的對應 | 路由樣板只被 `lib/nav/registry.test.ts:46-68` 的 walker 用來驗導覽 `href` | 新增三道雙向鎖：`app/**/page.tsx`↔`HELP_ROUTES`（減 `/login`）、導覽登記表→`helpForPath`、頁檔目錄↔`HELP_PAGES`∪`PENDING_HELP_PAGES` |
| 狀態詞白話釋義 | 畫面只有中文標籤（`lib/domain/status.ts` 等既有常數表），沒有白話釋義；議題中心有 API `legend` | `STATE_HELP`（每張表全站一份，只有 `meaning`、`next`）＋`STATE_SOURCES`（鍵與名稱現讀既有常數）；撰寫時 18 張、104 列（快照，不入斷言） |
| `lib/domain/si.ts` | `PROP_STATUS_BY_STATE`（`:179-191`）未匯出 | 新增一行匯出 `PROP_STATE_KEYS`（`:191` 後；無行為變更） |
| `vitest.config.mts` | `coverage.include`（`:26-72`）無 help 檔；門檻 `:73` | 加 `lib/help/registry.ts`、`lib/help/lint.ts`、`components/domain/help/stateSources.ts` 三行；門檻（lines 70、statements 70、functions 70、branches 60）不動 |
| frontend vitest 基線 | 88 個測試檔、1509 個測試，rc 0（本檔作者於 HEAD 實跑）；`npx tsc --noEmit` rc 0 | 新增 7 個 vitest 檔；既有 88 個檔只改 1 個（`si.static.test.ts` 同步鎖，D-PH-18），其餘零修改（§5.7） |
| Playwright mock spec | `tests/e2e/*.mock.spec.ts` 由 CI 以 `playwright test mock.spec`（standalone 產物）全數執行（`agentconsole-ci.yml:143-148`） | 新增 `page-help.mock.spec.ts`，被同一個過濾字串自動帶進 CI |

**使用者故事（US，一 FR 一則；AC 對應見 §1、§6）**

| US | 身為掌舵者，我要… | 以便… | FR |
|---|---|---|---|
| US-PH-01 | 在每個有說明的頁面，頂列都有同一顆「本頁說明」鈕，三種角色都開得了 | 不必到處找說明入口 | FR-PH-01 |
| US-PH-02 | 開啟後看到這頁做什麼、怎麼用、每個欄位與狀態的白話，且一律是純文字 | 不看英文也懂；說明不會執行任何內容 | FR-PH-02 |
| US-PH-03 | 路由、導覽與說明三方互相鎖住 | 新增頁面忘了寫說明時，測試就轉紅 | FR-PH-03 |
| US-PH-04 | 每個狀態詞的意思與畫面上的狀態表同步、不另抄一份；議題中心的詞表取自 API | 改了狀態而說明沒跟，測試會抓到 | FR-PH-04 |
| US-PH-05 | 說明用淺顯中文：句子短、英文少、沒有符號雜訊，欄位名真的在畫面上 | 讀得懂、對得上 | FR-PH-05 |
| US-PH-06 | 這個功能不動 API、後端、帳本與既有畫面行為，首屏不變慢 | 風險只在一層靜態說明 | FR-PH-06 |
| US-PH-07 | 鍵盤可用、手機看得到讀得完、無障礙零違規 | 每個人都用得了 | FR-PH-07 |
| US-PH-08 | 新增頁面時被規範要求必帶說明 | 說明不會隨時間腐爛 | FR-PH-08 |

**User Story INVEST 自檢（SCG-0；本檔作者自檢，凍結審查可推翻）**：八則 US 皆通過 N（可協商處＝說明文字本身，鎖的是結構、詞彙集合與機械面，白話由掌舵者真機判）、V、E、T（AC 與 AT 數見 §1、§3）；S 為「否」者是 FR 級故事（FR-PH-02、03、04、05，各 6～7 條 AC），以 AC 為最小可測單位、以持有面（見下表）為最小派工單位；I 的依賴即派工順序：US-PH-03 最先（輪 1a），US-PH-04、05、08 依 03，US-PH-01、02 依 03、04，US-PH-07 依 01、02，US-PH-06 跨切面（輪 1a 起）。

**持有面、鎖的住所與提交順序（鐵律七：一道鎖的常數、史料、消費端若不在同一持有面，不得派並行包）**

| 鎖或件 | 常數（真相） | 史料與消費端 | 持有面與順序 |
|---|---|---|---|
| 登記表、狀態釋義、lint | `lib/help/registry.ts`、`states.ts`、`lint.ts` | 各頁檔、`registry.test.ts`、`content.test.ts`、`lint.test.ts`、`stateKeys.test.ts`、`PageHelpDialog` | 單一持有面：輪 1a、1b、2、3 一律串行，前一棒經主控親驗才派下一棒；輪 1a 建立三檔，1b、2、3 只加頁檔與 `registry.ts` 的登記列，不再動 `states.ts`、`lint.ts` |
| 狀態名稱來源 | `components/domain/help/stateSources.ts`（`STATE_SOURCES`） | `stateKeys.test.ts`、`PageHelpDialog.tsx` | 輪 1a 一次寫完全部狀態表（`Record<StateTableId, …>` 不放寬成 Partial，PRD D-11） |
| 路由與導覽鎖 | `registry.ts` 的 `HELP_ROUTES`、`app/**/page.tsx`、`lib/nav/registry.ts` | `registry.test.ts`、姊妹案（備份）的兩條路由與第九個導覽項 | 輪 1a 起全程生效；姊妹案後落地者補列（D-12） |
| 分輪棘輪 | `registry.test.ts` 的 `PENDING_CEILING` | `registry.ts` 的 `PENDING_HELP_PAGES` | 每棒同 commit 下修；輪 3 出口為 0（G-F8）；姊妹案重填時同 commit 上修並於 PR 說明 WHY |
| 覆蓋率 include | `vitest.config.mts` | 三個新檔 | 輪 1a 同 commit（`npm run test:cov` 不得因新檔覆蓋不足而紅） |
| `si.ts` 匯出 | `lib/domain/si.ts` 的 `PROP_STATE_KEYS` | `stateKeys.test.ts` | 輪 1a；一行加法，不動 `si.test.ts` |
| 既有鎖同步 | `components/domain/si/si.static.test.ts` 的 `bridgeLeaks.checkText` | `lib/help/self-improving.ts` 的 `sourceFiles`（輪 3 才寫，故輪 1a 先改鎖） | 輪 1a；本案唯一准改的既有測試（D-PH-18） |
| 頂列接入 | `components/layout/TopRegion.tsx` | `layout.test.tsx`、`si-login-gate.test.tsx`、`DashboardView.test.tsx`（PRD §9 真跑清單）、`design-rules.test.ts:68-69` | 輪 1b（`next/dynamic` 載入，D-PH-17）；真跑三檔並貼輸出（AT-PH-06-2-2） |
| 文件連動（`Architecture.md` §3、§5.2、§5.4；ADR-002 §4 一列；RTM 新子表；SCG-4 審查報告） | 本功能落地事實 | 主控發布階段 | 主控單人收尾，開發棒不碰（PRD §9、AC-PH-08-3、F-16）；另含 PRD D-8 的 OBS 入帳一列（`docs/06_quality/SelfImproving_Observation_Ledger.md`，§6.5） |

**D 表：本檔（Stage-2）的定案；開發棒照做，不得另取他法（PRD 未定處由本表補，不與 PRD 相違；要改走勘誤）**

| D | 定案 |
|---|---|
| D-PH-1 | 本檔路徑與 PRD §9 一致：`AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md`；SDD 鍵 `agentconsole-page-help`；`spec-frozen --root` 取 monorepo 根（Stage-1 含根層 PRD，BRIDGE §8.1），`--doc` 寫相對根的路徑 |
| D-PH-2 | `helpForPath(pathname: string)` 回 `HelpId` 或 `null`：**只做路由→說明 id 的解析**（靜態段優先於動態段、去尾斜線；大小寫敏感；與 `PENDING_HELP_PAGES` 無關，所以輪 1a 起 `/` 就回 `dashboard`，AC-PH-03-3 在所有輪次成立）；「這頁有沒有已寫的說明」由按鈕以 `HELP_PAGES[id]` 判（缺＝不渲染，AC-PH-03-6）。`HELP_PAGES` 的鍵＝已寫頁 id（不含 pending），`HELP_ROUTES`＝路由樣板→id（含 pending 頁的路由，才能讓路由鎖在所有輪次成立） |
| D-PH-3 | `PageHelpDialog` 的公共面：`({ page, open, onOpenChange, content }: { page: PageHelp; open: boolean; onOpenChange: (open: boolean) => void; content?: HelpContent })`；`HelpContent = { common: CommonHelp; states: Readonly<Record<StateTableId, Readonly<Record<string, StateRow>>>>; sources: Readonly<Record<StateTableId, StateSource>> }`，`StateSource = { title: string; keys: readonly string[]; labelOf?: (key: string) => string }`（＝`STATE_SOURCES` 的值型別）；`content` 缺省取真登記（`HELP_COMMON`、`STATE_HELP`、`STATE_SOURCES`，以模組常數作預設值、不在每次渲染重建）。**這是測試唯一的注入縫**：合成頁、哨兵內容、`raw` 模式與跨輪次的內容測試都只經此縫，不用 `vi.mock` 換模組 |
| D-PH-4 | `PageHelpButton` 無 props：`usePathname()`→`helpForPath`→`HELP_PAGES[id]`，缺＝回 `null`。**行為規格**：路由變更即關閉、重繪不關閉（開在 A、走到 B、再回 A，仍是關閉）。**實作定案**：外層取 `pathname`，以 `key={pathname}` 重掛載內層元件（內含 `useState(false)` 與 `<PageHelpDialog page open onOpenChange />`），路由一變內層整個重建、開關回到關閉；**禁止**在 effect 內同步 `setState`（repo 的 ESLint `react-hooks/set-state-in-effect` 為 error：`eslint-config-next` 16.4.3、`eslint-plugin-react-hooks` 7.1.1；已實測 effect 寫法使 ESLint rc 1（§5.8），旁證 `components/charts/tremor/AreaChart.tsx:5-7` 為此停用該規則；`npm run lint` 是 G-F4 與 CI 第一步），也**不用**「`openFor === pathname`」衍生寫法（A→B→A 會誤重開）。鈕為 `<button type="button" data-testid="page-help-open">`，內含 `BookOpen`（`aria-hidden`）與文字節點「本頁說明」（`max-md:sr-only`）；名稱來自文字節點，不另設 `aria-label`；不另開 `Link` |
| D-PH-5 | 對話框 DOM 契約＝C4（逐項；測試鉤清單也在 C4）。要點：全對話框 `h3` 恰四個、小標題一律 `h4`、`steps` 用 `ol > li`（不手寫序號）、每個 `td` 帶 `data-label` |
| D-PH-6 | 固定文字（對話框內除登記內容外唯一允許的字，AC-PH-02-4 的白名單）：清單與判法見 §5.3 `FIXED_TEXT`（單一出處） |
| D-PH-7 | 議題詞表群 DOM＝C4「議題詞表群」列（沿 `IssueLegend.tsx` 的 `dl` 結構）；`page-help-legend-loading`、`page-help-legend-error` 兩個 testid 為本檔補充（PRD §7 清單的加法，不改既有 id） |
| D-PH-8 | 詞表失敗句：「狀態詞表暫時取不到：」後接 `siErrorParts(error)` 的 `reason`、`detail`、`cause`（存在者逐字，順序與分隔不拘）；三者皆空（網路失敗、無詳情）時改接 `describeError(error)`；`200` 但回應沒有 `legend` 物件或四群之一缺席＝同樣走失敗句，原因寫「回應沒有詞表」（fail-loud，不顯示空表；PRD AC-PH-04-5「不顯示空表」的延伸） |
| D-PH-9 | `lib/help/lint.ts` 公共面（測試只用這些）：`ENGLISH_WHITELIST: readonly string[]`（PRD §8.3 的 31 詞，原樣大小寫）、`splitSentences(text: string): string[]`（以「。！？；」與換行切、去前後空白、丟空段）、`codePointLength(text: string): number`、`unlistedEnglishWords(text: string): string[]`（先剔除 ID 形態再取連續 ASCII 字母、長度 ≥ 2、不在白名單者；底線與連字號當分隔、整詞比對不分大小寫）、`forbiddenFindings(text: string): string[]`（emoji、`#`＋≥3 位十六進位、`**`、反引號、`](`、HTML 標籤、`://`、磁碟機或家目錄路徑、≥3 位連續半形數字；**先剔除 ID 形態**）、`lintText(text: string, opts?: { maxSentences?: number }): string[]`（綜合：每句 ≤ 60 code point、可選句數上限、上列兩項；空陣列＝合規）。**訊息關鍵字契約**：`lintText` 回傳的每筆訊息必含其類別關鍵字——句長違規含「句長」、句數違規（`maxSentences`）含「句數」、英文詞違規含「英文」並列出該詞、字元違規含「字元」並列出命中形態（AT-PH-05-6-1 只斷言關鍵字，不釘全文；`#abc123` 會同時觸發英文與字元兩類）；`unlistedEnglishWords`、`forbiddenFindings` 回原始命中值，不受此約束 |
| D-PH-10 | ID 形態（D-PH-9 先剔除者，AC-PH-05-2 原文）：`OBS-SI-<數字>`、`PROP-SI-<數字>`、`DEF-<數字>-<數字>`。**AC-PH-05-3 的「連續 ≥ 3 位半形數字」同樣在剔除 ID 形態之後判**（否則 `OBS-SI-001` 本身就違規，剔除便失去意義；本檔的預設裁決，勘誤 1-4）；測試碼的 DEF 樣本一律在執行期組字串（`"DEF-" + "1-2"`），不把 DEF 編號字面寫進 repo（缺陷帳本引用完整性鎖） |
| D-PH-11 | 頁檔與 `SHARED`：`lib/help/<id>.ts` 每檔恰匯出一個 `PageHelp`（匯出名稱不拘，測試以「值帶 `id` 欄」取用）；`SHARED: Record<string, HelpField>`（每個值是一個可被頁檔放進 `fields` 的欄位釋義，例 `SHARED.autonomy`）；`HELP_COMMON: CommonHelp`；`STATE_HELP` 的每張表鍵順序＝顯示列序 |
| D-PH-12 | 靜態掃描器、表單欄位掃描器、出處鎖掃描器都**住測試檔內**（`help.static.test.ts`），不進生產碼；以既有 devDependency `typescript` 的 AST 實作，沿 `issues.static.test.ts` 的 `walk`、`parse`、`walkAst`、`literalTexts`（本檔另加 JSX 文字節點）；每個掃描器是純函式並各有負控樣本；掃描範圍有防反空轉斷言 |
| D-PH-13 | Playwright mock spec 的請求計數用**新穎性規則**：「新增請求」＝點擊之後出現、且鍵在點擊之前**沒出現過**的請求；鍵＝(方法, 路徑)，**唯一例外**是路徑 `/api/v1/issues`，其鍵再含排序後的查詢串（否則議題中心頁自己的清單請求會把詞表請求「吃掉」）。頁面自己的輪詢（監控頁的輪詢間隔由使用者設定，不靠間隔長短）與頂列輪詢（`GET /api/v1/notifications/summary`、`GET /api/v1/projects`）因路徑在點擊前已出現過而自然排除；議題中心頁自身的清單請求帶 `limit=100`（`SI_PAGE_LIMIT`），詞表請求帶 `limit=1` 且無其他參數，兩者鍵不同。點擊前的基線＝頁面載入、`page-help-open` 可見後固定再等 1,000 毫秒（**不用** `networkidle`，§5.8 實測多數路由到不了），點擊後的觀察窗＝對話框出現後再等 500 毫秒 |
| D-PH-14 | 分輪棘輪：`PENDING_CEILING`（常數，`registry.test.ts` 檔頂，附「第幾輪」註解）；`PENDING_HELP_PAGES.length <= PENDING_CEILING`；初值＝PRD 十六頁中尚未寫的頁數＋姊妹案暫列的 pending 頁數；只准下修，上修只有姊妹案重填且同 commit 於 PR 說明 WHY；輪 3 出口（G-F8）常數為 0 |
| D-PH-15 | 頁→狀態表矩陣（§5.3 `PAGE_STATES`）是 PRD §4「該頁要列的狀態表」的逐頁釘值：每個**已寫的 PRD 十六頁**之 `states` 表 id 集合與名稱模式（`label`／`raw`）必須與矩陣相等；矩陣只含 PRD 的十六頁，姊妹案新頁不受集合相等鎖（仍受通用鎖）。這是 PRD 未寫成 AC、但 §4 欄位標題明定的內容（「該頁要列的狀態表 id」），列入 AC-PH-03-5 的 AT（TCS 補強，勘誤 1-3） |
| D-PH-16 | 測試用 `QueryClient` 一律取**app 預設**（`components/providers/Providers.tsx:15-27` 的 `staleTime: 5_000`、4xx 不重試、其餘重試一次、`refetchOnWindowFocus: false`），**不用** `tests/helpers/api.tsx` 的 `makeClient()`（它的 `retry:false`、`staleTime:0` 會把「詞表查詢漏掉 `SI_QUERY_OPTIONS`」的缺陷整個遮蔽）。議題中心詞表的測試直接重用既有的 `renderIssues`／`newStub`／`unavailable`／`LEGEND`／`clone`（`components/domain/issues/tests/issues.fixtures.ts`；`newStub({ legend, overrides })` 供哨兵詞表與各種失敗回應，`stub.calls` 記錄請求）；經 `RootLayout` 渲染者自然取到真 `Providers`。輪 3 之後（`PENDING_HELP_PAGES` 為空）AT 內的 pending 分支（路由無鈕、內容豁免）只在姊妹案重填 pending 時才咬；其間以全函數式斷言（每條路由的鈕數＝已寫？1：0，AT-PH-01-2-E-1）保持有效 |
| D-PH-17 | 頂列接入形態：`TopRegion.tsx` 以 `next/dynamic` 載入 `PageHelpButton`（寫法見 §5.7 TopRegion 列；識別字仍叫 `PageHelpButton`，JSX 仍是 `<PageHelpButton />` 一處，AT-PH-01-1-E-2 的 JSX 掃描照樣成立；`ssr` 等選項由開發棒依 G-F5 量測定）。**成因訂正**（v0.1 預警說反了一半）：`si.ts`、`status.ts` 早已在每條路由的 root chunk（`queries.ts:13-14`←`TopRegion.tsx:20`），首屏真正的新增量是說明文字本體（16 頁加約 104 列釋義，一審估 90～120KB）、`sdd.ts` 鏈與 Radix Dialog；靜態 import 會全帶進每條路由，單憑 100,000 位元組預算守不住，所以輪 1b 起動態載入。測試寫法見 §5.1〈非同步慣例〉；AT-PH-06-4-1 自輪 1b 出口起為閘 |
| D-PH-18 | 本案唯一准改的既有測試：`components/domain/si/si.static.test.ts`（AT_932_4_3，`:249-276`）。該鎖掃 `app`、`components`、`lib`、`hooks` 全部非測試原始碼，`checkText` 第二分支（`:232`）把任何含 `/si/` 路徑段且不以 `/api/v1/si/` 起頭的字串字面值判紅；`self-improving` 頁的 `sourceFiles` 必含 `components/domain/si/**`（AC-PH-05-5），該字面值含 `/si/` 而使整檔 rc 1（審查鏡於 `git archive` 副本實測）。**定案（B 式）**：第二分支限縮為 URL 形——只判 (i) 以 `/` 或 `scheme://` 起頭的字串，與 (ii) **樣板運算式之後的每個片段（一律視為 URL 形，不論是否以 `/` 起頭）**；凡含 `/si/` 且不以 `/api/v1/si/` 起頭者判紅；相對檔案路徑形（`components/domain/si/**`）不判。**不得**用「`/si/` 在字串開頭或緊接樣板運算式後才判」（A 式）：等於刪掉第二分支（審查鏡突變實測 0／7 殺）；只做 (i) 者 5／7，漏 `http://${h}:9000/si/x` 與相對 `api/si/x`，加 (ii) 補回。第一分支（`/si/` 起頭）與 8081、BRIDGE 環境變數兩條不動；負控見 AT-PH-06-2-3、E-2。PRD AC-PH-06-1、06-2 的「既有測試不改」於此檔列例外（勘誤 1-1、1-2）；輪 1a 一併改，輪 3 寫 `self-improving` 頁時才不撞牆 |

**公共面（D-PH-2、3、9、11 的簽章清單；測試依此呼叫，改名須勘誤）**

| 檔 | 匯出 | 說明 |
|---|---|---|
| `lib/help/types.ts` | `HelpId`、`StateTableId`（字面值聯集）、`FieldSource`、`HelpField`、`StateRow`、`HelpStateGroup`、`PageHelp`、`CommonHelp` | PRD §8.1 逐字；純型別，不 import 元件 |
| `lib/help/states.ts` | `STATE_HELP` | 物件字面值，**逐表以 `satisfies` 宣告**（例 `projectStatus: { … } satisfies Record<ProjectStatus, StateRow>`，外層 `satisfies Record<StateTableId, Readonly<Record<string, StateRow>>>`）；**不得**以 `: Record<StateTableId, Record<string, StateRow>>` 型別註記宣告（註記會抹掉各表的字面鍵，`keyof typeof STATE_HELP.projectStatus` 退成 `string`，AT-PH-04-2-2 的型別等式即無法成立）；十張有後端 enum 的表以 `Record<該 enum, StateRow>` 為準（AC-PH-04-2），`serviceState` 為字面值聯集 |
| `lib/help/common.ts` | `SHARED`、`HELP_COMMON` | D-PH-11 |
| `lib/help/registry.ts` | `HELP_PAGES`、`HELP_ROUTES`、`PENDING_HELP_PAGES`、`NO_STATE_PAGES`、`helpForPath` | D-PH-2；路由樣板鍵為 Next 資料夾名（`[projectId]`、`[goalId]`、`[taskId]`），根路由為 `/` |
| `lib/help/lint.ts` | `ENGLISH_WHITELIST`、`splitSentences`、`codePointLength`、`unlistedEnglishWords`、`forbiddenFindings`、`lintText` | D-PH-9 |
| `components/domain/help/stateSources.ts` | `STATE_SOURCES`（`Record<StateTableId, StateSource>`） | 只 import 既有常數表；`keys` 於載入時由既有常數現讀（`sddFsmState` 例外，PRD §8.2 備註 2） |
| `components/domain/help/PageHelpButton.tsx`、`PageHelpDialog.tsx`、`IssuesLegendGroups.tsx` | `PageHelpButton`、`PageHelpDialog`（與型別 `HelpContent`、`StateSource`）、`IssuesLegendGroups` | D-PH-3～8；`IssuesLegendGroups` 以 `useQuery`（query key `["help","issuesLegend"]`、`getIssues({ limit: 1 })`、`...SI_QUERY_OPTIONS`）取詞表，不 import `useIssues` |
| `lib/domain/si.ts` | `PROP_STATE_KEYS` | `Object.keys(PROP_STATUS_BY_STATE)` |

**追溯矩陣**：F-PH ← PRD FR-PH-01～08（§5 的 43 條 AC）、§4、§7～§11、§13；US-PH-01～08 → AC-PH-01-1～08-3（PRD §5）→ AT（§1）；R-PH-01～R-PH-37 → AC（R 條文表的 AT 欄）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；Console 單半，單鍵 `agentconsole-page-help`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.3 全文（§13.2.1 掌舵者 2026-10-27 裁決 Q1、Q2、Q4～Q7 全採建議值；Stage-1 依常態規則於 HEAD `000a217b` 凍結，三份姊妹 PRD 同批） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-PH＝FR-PH-01～08（PRD §5）；本檔 FRD-lite 的 US-PH-01～08 與 §1 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-0／NFR 已量化定義 | PRD §6（安全、效能、跨平台、零侵入）與 AC-PH-06-4（首屏 ≤ 100,000 位元組）、AC-PH-07-1～07-5；≤ 100 ms、≤ 2 秒兩項 PRD 自承無自動化量測（§6、F-18）→ 真機 V1；本檔 §6.2 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-0／User Story 已完成 INVEST 檢查 | US-PH-01～08（本檔〈User Story INVEST 自檢〉段） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-0／利害關係人已確認簽核 | PRD §13.2.1（掌舵者 2026-10-27 本窗互動選項裁決）、§13.1 主控代決 D-1～D-13；凍結依常態規則由主控執行，掌舵者可隨時以 T1 推翻 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6；`AgentConsole/docs/06_quality/RTM.md` 新子表（編號由主控依落地序定，PRD §9）於發布階段回填 | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（功能級增量；設計載於 PRD §4～§9） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-1／API Spec 草稿完成 | 不適用：零 API、後端、Bridge、契約檔（PRD 檔頭、§6）；唯一請求為既有端點 `GET /api/v1/issues`（`IC契約:138`，VIEWER 以上唯讀）；前端內部契約＝本檔〈契約節〉 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-1／資料模型設計完成 | PRD §8.1（型別）、§8.2（18 張狀態表、鍵來源與名稱來源）；本檔 R-PH-01、R-PH-08～R-PH-14、D-PH-3、D-PH-11、§5.3 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-1／NFR 設計對應完成 | PRD §6 對應本檔 R-PH-22（唯一新請求）、R-PH-23（首屏增量）、R-PH-26～R-PH-29（鍵盤、窄螢幕、axe、設計規則）、R-PH-31（純文字）、R-PH-20（零侵入） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-1／整合架構說明完整 | 無第三方服務；依賴＝既有前端件（`DialogContent`、`SI_QUERY_OPTIONS`、`getIssues`、`siErrorParts`、`SERVICE_LABEL`、既有狀態常數表、`NAV_REGISTRY`）；依賴方向 `lib/help/**`（純文字）← `components/domain/help/**` ← `components/layout/TopRegion.tsx`（PRD §9） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-2／C4 Context 圖完成 | PRD §1、§4（既有畫面→靜態說明層）；不新增系統邊界 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-2／C4 Container 圖完成 | PRD §9 模組落點表（`AgentConsole/frontend/` 下 `lib/help/`、`components/domain/help/`、`tests/e2e/`；根層零新檔）；本檔 §5.7 檔案集合 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-2／所有架構決策有對應 ADR | 本增量無新架構決策（PRD 檔頭：決策短編於 §9、§13.1，不另立 ADR）；ADR-002 §4 的「與設計稿的已知差異」登記由主控發布階段補一列（F-16） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-2／Trust Boundary Map 完成 | 不適用（brownfield）；要點：說明一律純文字節點、無新端點與寫入、詞表請求沿既有 JWT 與 VIEWER 以上授權、說明不得含機密與絕對路徑（PRD §6）；本檔 R-PH-15、R-PH-31 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈Before／After〉；PRD §9 模組落點表 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-3／OpenAPI 3.1 規格完整 | 不適用（零 API）；既有 `GET /api/v1/issues` 不變（`openapi-p3-6.yaml`、`schema*.d.ts` 不在變更集合，G-C1 機械核對） | （本檔〈契約節〉；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／Request／Response Schema 定義完整 | 本檔〈契約節〉：型別、公共面、DOM 契約、測試鉤、詞表（前端內部契約） | （本檔〈契約節〉；隨 Stage-2 凍結，自引、非上位文件） | n/a（自引） |
| SCG-3／錯誤碼定義 | 不適用（無新 reason）；詞表請求失敗的使用者可見句見 D-PH-8、AC-PH-04-5 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-3／Consumer Contract 完成 | 消費者＝掌舵者（SCG-5 真機 V1～V4）、既有 `layout.test.tsx` 等三個會渲染頂列的測試（真跑清單）、姊妹案的路由與導覽項（D-12） | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-3／API ID 與 RTM 已對應 | 不適用（零 API）；AT 到 RTM 見本檔 §1 與 §6 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（`SCG4-REVIEW-PageHelp-<日期>.md`）；本檔凍結前先經 Stage-2 的 SCG 審查 | docs/01_requirements/Console_PageHelp_PRD.md | sha256:945d79176ce13c98e9b2d07618c444fddaab01b4208bc06b76b8331ba521b46f |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是 Stage-1 凍結的 digest；本檔作者於 2026-10-27 以 SHA-256 對工作樹現況重算一致（LF-only，56,565 bytes），HEAD `000a217b8b35095976d04b031254a4fe133f6675`。凍結後的實際 digest 以該鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準，與本表不符時以 `show` 為準並更正本表。

### R 條文（把 PRD §2～§8 逐條化；每條可判定）

「突變」欄＝會使對應 AT 轉紅的最小改動；**每條都標明套用面**，讓 QA 能機械重放（QA 在 `git archive <HEAD>` 匯出的暫存副本上逐一套用，**不在工作樹套用**、不用 `git checkout --` 還原；frontend 副本以 junction 把 `node_modules` 指回工作樹）：

- **［上游］**＝改 HEAD 上**已存在**的檔，與實作無關，本檔凍結後即可對任何實作重放；
- **［實作］**＝改開發棒將新增的檔（路徑依 PRD §9），語意以「哪個檔的哪個結構」描述，開發棒完成後由 QA 逐一重放；
- **［閘］**＝審查閘型（G 編號指令），以其自證負控 AT 代為證明鑑別力（無法在單元測試重放者）。

AT 欄為 AC 簡碼（例 `01-1`＝`AT-PH-01-1-*` 全部）。倖存者（突變後 AT 仍綠）＝該 R 條文缺鑑別力，須補 AT 並勘誤。凡突變只在特定輪次起才咬（例：表單頁、`execute` 頁於其寫完的輪次起），該條已註明；重放程序與兩個［上游］前提已於本檔作者端預跑（§5.8）。

#### A 型別、登記表與路由（PRD §8.1、§9；`types.ts`、`registry.ts`、`app/**/page.tsx`、`NAV_REGISTRY`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-01 | `types.ts` 是純文字型別：`StateRow` 只有 `meaning`、`next`（沒有 `label`、`name`）；`FieldSource` 恰六類；`HelpStateGroup` 兩形（`{ table, name? }`、`{ legend: "issues" }`）；不 import 任何元件 | ［實作］給 `StateRow` 加一個 `label: string` 欄（tsc 紅）；`FieldSource` 加第七類（05-4 的型別等式紅） | 04-2、05-4 |
| R-PH-02 | 路由鎖：`HELP_ROUTES` 的鍵集合＝`app/**/page.tsx` 路由樣板（括號群組不進網址）減排除名單 `["/login"]`；缺（新頁沒說明）與多都紅，訊息含修法「在 `lib/help/<id>.ts` 新增並於 `registry.ts` 登記」 | ［上游］在 `app/` 新增 `app/zzz/page.tsx`（只殼，`export default function Page() { return null; }`）；［實作］自 `HELP_ROUTES` 刪一鍵、或加一個沒有頁面的鍵 | 03-1、08-1 |
| R-PH-03 | 導覽鎖：`NAV_REGISTRY` 每個 `enabled` 項、其 `href` 的兩種解析（`currentProjectId` 為 `null` 與 `"p1"`）都經 `helpForPath` 得到說明 id | ［上游］在 `NAV_REGISTRY` 末尾加 `{ id: "zz", label: "測試", icon: Settings, href: "/login", match: () => false, order: 99, enabled: true, mobile: false }`；［實作］自 `HELP_ROUTES` 刪 `/import` | 03-2、08-2 |
| R-PH-04 | `helpForPath`：靜態段優先於動態段、去尾斜線、大小寫敏感、每路徑恰一個 id；`""`、未知路徑、前綴相似（`/projects-x`）、`/login` 回 `null`；與 `PENDING_HELP_PAGES` 無關（D-PH-2） | ［實作］比對序改成動態段先（`/projects/new` 回 `project-detail`）；不去尾斜線；對 pending 頁回 `null`（此項於輪 1a、1b、2 重放：輪 3 已無 pending 頁） | 03-3 |
| R-PH-05 | 頁檔鎖：`lib/help/` 扣掉保留名（`types`、`states`、`registry`、`lint`、`common`）與測試檔後，頁檔 id 集合＝`HELP_PAGES` 的鍵∪`PENDING_HELP_PAGES`（兩者互斥）；每檔 `id` 欄等於檔名 | ［上游］在 `lib/help/` 新增 `zzz.ts`；［實作］改一個頁檔的 `id` 欄、或把同一 id 同時放進兩個集合 | 03-4 |
| R-PH-06 | 已寫頁的結構界線：`purpose` 以 `splitSentences` 切句後合計 1～3 句（每項非空）、`steps` 2～8 項、`fields` ≥ 1、`sourceFiles` ≥ 1 且路徑存在；`states` 為空者必在 `NO_STATE_PAGES`（且 `NO_STATE_PAGES` 內者必為空）；PRD 十六頁各頁的 `states` 表 id 集合與名稱模式＝§5.3 矩陣（D-PH-15） | ［實作］某頁 `steps` 砍成 1 步；`sourceFiles` 填不存在的路徑；`dashboard` 少登 `projectStatus`；`monitor` 的 `stepStatus` 寫成 `raw` | 03-5 |
| R-PH-07 | 分輪棘輪：`PENDING_HELP_PAGES.length <= PENDING_CEILING`，輪 3 出口為空；pending 頁的路由不渲染鈕、頁內容類檢查豁免到它移出 pending；`PENDING_HELP_PAGES` 為空時全部路由都渲染鈕 | ［實作］多填一個 pending 而不上修天花板；pending 頁的路由仍渲染鈕；輪 3 出口 `PENDING_CEILING` 仍非 0（G-F8）（前兩項於輪 1a、1b、2 重放：輪 3 已無 pending 頁，只剩第三項可重放） | 03-6、01-2 |

#### B 狀態詞：不自持、鍵雙向鎖、名稱只取自既有常數（PRD §8.2、FR-PH-04；`states.ts`、`stateSources.ts`、`IssuesLegendGroups.tsx`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-08 | 鍵雙向鎖：`STATE_SOURCES[id].keys` 於載入時現讀既有常數（對照表見 §5.3），與 `STATE_HELP[id]` 的鍵集合雙向相等；`sddFsmState` 例外＝五個鍵各須以子字串出現在 `lib/domain/sdd.ts` 與 `components/domain/sdd/**` 非測試檔的字串字面值、樣板片段或 JSX 文字（不含註解）；`STATE_HELP` 與 `STATE_SOURCES` 的表 id 集合相等且 ⊇ §5.3 的必備 18 個 | ［上游］`lib/domain/status.ts` 的 `PROJECT_STATUS` 加一鍵 `HOLD: { label: "暫停", color: MUTED }`；`lib/domain/si.ts` 的 `PROP_STATUS_BY_STATE` 加一鍵 `zzz: "done"`；［實作］`STATE_HELP.taskStatus` 刪 `PAUSED` 列；`sddFsmState` 的某鍵改成程式碼裡不存在的字串 | 04-1 |
| R-PH-09 | 型別鎖：十張有後端 enum 的表（專案、目標、任務、匯入、批次、審核種類、審核決定、步驟、告警規則、有界閘）逐表以 `satisfies Record<該 enum, StateRow>` 宣告（不用整體型別註記，見〈公共面〉表），鍵集合型別等式；`serviceState` 以字面值聯集宣告且型別等式＝`ServiceState`；`@ts-expect-error` 樣本證明型別真的擋（加 `label` 欄、缺一鍵、enum 多一值） | ［實作］`states.ts` 把 `projectStatus` 的宣告放寬成 `Record<string, StateRow>`；`serviceState` 的聯集少一個字面值；`StateRow` 加 `label?: string` | 04-2 |
| R-PH-10 | 名稱模式：`label`（預設）＝`STATE_SOURCES[id].labelOf(key)`、`raw`＝鍵本身；無 `labelOf` 的表只准 `raw`；每張有 `labelOf` 的表，`labelOf(key)` 等於上游常數同鍵的標籤（§5.3 對照）；畫面上「狀態」欄逐列等於該頁名稱模式，`raw` 表欄標題為「畫面上的原值」 | ［實作］`stateSources.ts` 的 `goalStatus.labelOf` 誤接 `PROJECT_STATUS`；`propState` 在頁檔登記成 label 模式；`task-detail` 的 `stepStatus` 登記成 label | 04-3 |
| R-PH-11 | 議題中心詞表群：狀態、結果、來源、嚴重度四群與 `updatedAtNote` 逐字取自 `GET /api/v1/issues?limit=1` 的 `legend`（順序＝陣列序）；`updatedAtNote` 缺席或空字串不渲染；對話框內沒有第二份詞表文字；靜態鎖只掃 `lib/help/issues.ts` 與 `components/domain/help/**` 非測試檔：每檔含不到 4 個不同的議題狀態名（現讀黃金檔） | ［實作］`IssuesLegendGroups.tsx` 把「結果」群改成寫死陣列；`updatedAtNote` 缺席時仍顯示寫死句；`lib/help/issues.ts` 的 `steps` 逐一點名四個狀態名 | 04-4 |
| R-PH-12 | 詞表載入與失敗：載入中顯示「狀態詞表載入中…」；503、504、網路失敗、回應沒有詞表＝前三段照常、狀態段顯示「狀態詞表暫時取不到：<原因>」，不顯示空表與過期資料；每次開啟都重取、失敗不重試、不留快取（沿 `SI_QUERY_OPTIONS`）；query key `["help","issuesLegend"]`，不掛 `["issues"]` 家族、不 import `useIssues` | ［實作］`IssuesLegendGroups.tsx` 拿掉 `...SI_QUERY_OPTIONS`（失敗多重試一次、5 秒內重開不重取）；失敗時渲染空表；query key 改成 `["issues","legend"]` | 04-5 |
| R-PH-13 | 自我進化的名稱模式：`propState` 名稱為畫面原值、鍵集合＝`PROP_STATE_KEYS`（⊇ 根層十個狀態並含 `retired`）；`obsClass`、`propClass` 名稱取自 `OBS_STATUS_OPTIONS`、`PROPOSAL_STATUS_OPTIONS` 去掉 `id===""` 的標籤；`propState.retired.meaning` 寫明「根層目前不會產生這個狀態，畫面為日後預留」（PRD D-8） | ［上游］`si.ts` 的 `OBS_STATUS_OPTIONS` 末尾加一項 `{ id: "zz", label: "測試" }`（`obsClass` 多一鍵而說明沒補，04-1 紅）；［實作］`retired.meaning` 刪去該句；`PROP_STATE_KEYS` 改取 `Object.values`。**對照（應存活，不是缺陷）**：把「未結」的 `label` 改字不應轉紅——名稱一律現讀常數，這正是 PRD 的設計 | 04-6、04-1 |
| R-PH-14 | `reviewDecision` 與後果表的一致性：每個決定鍵對 `REVIEW_KIND` 每個種類呼叫 `reviewConsequence`，至少在一個種類回傳非預設句；該表每列 `next` 為「依審核項種類而定」類固定句，後果文字只住 `execute/reviewHelp.ts`、不抄第二份 | ［上游］刪 `reviewHelp.ts` 的 `TASK_CONFIRM.APPROVE`、`GOAL_CONFIRM.APPROVE`、`GOAL_COMPLETED.APPROVE` 三個條目（`APPROVE` 在所有種類都落到預設句）；［實作］`reviewDecision.APPROVE.next` 抄入「批次會恢復執行，開始下一個任務。」 | 04-7 |

#### C 白話與內容品質（PRD §8.3、FR-PH-05；`lint.ts`、各頁檔、`states.ts`、`common.ts`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-15 | lint 純函式（D-PH-9、D-PH-10）：切句（「。！？；」與換行）、每句 ≤ 60 個 code point（不是 UTF-16 單元）、英文詞白名單（31 詞，整詞不分大小寫；ID 形態先剔除）、禁字元（emoji、`#`＋≥3 位十六進位、`**`、反引號、`](`、HTML 標籤、`://`、磁碟機或家目錄路徑、≥3 位連續數字）；每種違規各有負控、合規樣本回空；白名單與 PRD §8.3 逐字相同 | ［實作］`lint.ts` 句長上限 60→61；`ENGLISH_WHITELIST` 加 `Foo`；連續數字門檻 3→4；句長改用 `String.length` | 05-1、05-2、05-3、05-6 |
| R-PH-16 | 內容審：全部說明文字（各已寫頁的 `purpose`、`steps`、欄位 `meaning`、`sourceNote`；`STATE_HELP` 每列 `meaning`、`next`；`HELP_COMMON`；`SHARED`）逐筆過 lint；句數界線＝`purpose` 合計 ≤ 3 句、`steps` 每步 1 句、欄位與狀態 `meaning` ≤ 2 句、`next` 1 句；欄位名與狀態名（畫面字樣）不受英文詞限制 | ［實作］某頁 `purpose` 寫一個 61 字的句子；某狀態 `meaning` 含 `Foo`；某 `next` 寫兩句 | 05-1、05-2、05-3 |
| R-PH-17 | 欄位 `source` 屬六類（您填寫或選擇、系統自動產生、執行引擎回報、自我進化帳本、系統參數、其他頁面帶入）之一；`sourceNote` 選填且 ≤ 30 個 code point | ［實作］某欄位 `source` 寫「手動」；`sourceNote` 寫 31 字 | 05-4 |
| R-PH-18 | 出處鎖：每個欄位名（≥ 3 個 code point、同頁互異；更短者免掃）須出現在該頁 `sourceFiles` 展開後非測試檔的字串字面值、樣板字串片段或 JSX 文字（不含註解）；`sourceFiles` 條目為相對 `AgentConsole/frontend/` 的檔案或 `dir/**`，每頁展開後 ≤ 30 個、拒絕頂層萬用（`components/**`、`lib/**`、`app/**`、`hooks/**`）、檔須存在 | ［上游］挑一個欄位名在該頁 `sourceFiles` 內**只出現一處**的 UI 字面值（QA 以 `Select-String` 現查）把它改名；［實作］某頁 `sourceFiles` 填 `components/**`；欄位名寫成畫面上不存在的字 | 05-5 |
| R-PH-19 | 表單欄位清單鎖：`entity/EntityForms.tsx` 的 `ProjectForm`、`GoalForm`（含 `DependsOnField`）、`TaskForm` 內 `<Field>`、`<MarkdownField>` 的 `label` 字串屬性，須都在對應說明項（`project-form`、`goal-form`、`task-form`）的欄位名集合內 | ［上游］在 `EntityForms.tsx` 的 `ProjectForm` 加 `<Field label="新欄位" error={undefined}><Input /></Field>`；［實作］`goal-form` 的欄位少列「前置依賴」 | 05-7 |

#### D 零侵入與單一真相（PRD §6、FR-PH-06）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-20 | 變更清單只含 §5.7 路徑；不含 `AgentConsole/backend/**`、`AgentConsole/engine-bridge/**`、`lib/api/` 的 `endpoints`／`queries`／`reasons`／`schema*.d.ts`、`openapi-p3-6.yaml`、`API_Contract_*.md`、`lib/nav/registry.ts`、`.github/**`、`tools/**`、`.claude/**`；既有測試檔零差異（唯一例外 `si.static.test.ts`，R-PH-37）；`Architecture.md` 只准主控在發布階段改 §3、§5.2、§5.4 | ［閘］G-C1 的篩選函式餵合成路徑逐一判違規（AT-PH-06-1-E-1）；［上游］`lib/api/endpoints.ts` 末尾加一個空白行 | 06-1、06-2 |
| R-PH-21 | 既有 vitest 原樣通過；PRD §9 真跑清單三檔（`layout.test.tsx`、`si-login-gate.test.tsx`、`DashboardView.test.tsx`）逐檔通過；覆蓋率門檻不降 | ［實作］`PageHelpButton` 改用 `useParams()`（`DashboardView.test.tsx` 的 `next/navigation` 替身只提供 `useRouter`、`usePathname`、`useSearchParams`，單獨渲染 `<TopRegion />` 即丟錯，真跑清單紅）；`PageHelpButton` 呼叫 `useRouter().refresh()`（同一替身無此方法） | 06-2 |
| R-PH-22 | 唯一新請求：議題中心的說明開啟時恰一個唯讀 `GET /api/v1/issues?limit=1`，其餘路由零個；每次開啟各一個；新增請求全程無非 GET、無 `/si/` 路徑 | ［實作］`PageHelpButton` 在 render 階段預取詞表（所有路由多一個請求）；`IssuesLegendGroups` 常駐掛載（開關不增請求） | 06-3 |
| R-PH-23 | 首屏 JS 增量：Stage-2 凍結 commit 與完成後各 build 一次，`.next/diagnostics/route-bundle-stats.json` 每條路由的 `firstLoadUncompressedJsBytes` 增量 ≤ 100,000 位元組（載入方式與成因訂正見 D-PH-17） | ［實作］`PageHelpDialog.tsx` 靜態 `import "recharts"`（增量遠超上限）；［閘］比較腳本自證（AT-PH-06-4-E-1） | 06-4 |

#### E 按鈕、鍵盤與響應式（PRD §7、FR-PH-01、FR-PH-07；`PageHelpButton.tsx`、`PageHelpDialog.tsx`、`TopRegion.tsx`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-24 | 按鈕：全站一顆、同一元件、`data-testid="page-help-open"`，在 `[data-region="top"]` 右側群組末端（通知鈴與待審批佇列之後），內容區沒有；`/login`、未登入、無對應說明項、pending 頁不渲染；VIEWER、OPERATOR、ADMIN 皆可見可開且內容相同；路由變更即關閉（不殘留舊頁內容）、重繪不關閉；`PageHelpButton` 只在 `TopRegion.tsx` 被使用 | ［實作］把 `<PageHelpButton />` 移出 `showTools` 分支（`/login` 出現鈕）；對 VIEWER 不渲染；拿掉 `key={pathname}` 重掛載（路由變更後對話框仍開）；改成 `openFor === pathname` 衍生寫法（A→B→A 誤重開）；每次重繪都重設開關；在 `ContentRegion` 也渲染一顆；［閘］用 `useEffect(() => setOpen(false), [pathname])` 實作 → `npm run lint` rc 1（`react-hooks/set-state-in-effect`，G-F4） | 01-1、01-2、01-3、01-4 |
| R-PH-25 | 可存取名稱含可見文字「本頁說明」（Label in Name）；<768 文字為 `max-md:sr-only`、名稱不變；與公告列靜態「幫助中心」區別：圖示用 `BookOpen`（不用 `CircleHelp`）、鈕名不同 | ［實作］鈕改成只有圖示、無文字節點；改用 `CircleHelp`；`aria-label="說明"`（不含可見文字） | 01-5、07-5 |
| R-PH-26 | 對話框建於 `DialogContent`，不自刻、不傳 `onCloseAutoFocus`；Enter 或空白鍵開啟且焦點進入對話框，Esc 與右上「關閉」鈕各關一次且焦點回到該鈕；內容可捲、寬度沿用 `max-w-[calc(100%-48px)]` | ［實作］加 `onCloseAutoFocus={(e) => e.preventDefault()}`；改用自刻 `<div role="dialog">`；覆寫 `className` 去掉 `max-h-[88vh]` | 07-1、07-2 |
| R-PH-27 | 窄螢幕（390×844）：鈕可見可點、頂列不造成橫向捲動、對話框不超出視窗且 `scrollWidth ≤ clientWidth`、兩張表逐列堆疊（每格一行、同左緣、以 `data-label` 作小標）；≥768 表格並排；<768 文字隱藏、≥768 文字可見 | ［實作］表格不改堆疊；`sr-only` 的斷點由 `max-md` 改 `max-lg`；對話框寫死寬度 `w-[640px] max-w-none`（只寫 `w-[640px]` 會被 `DialogContent` 的 `max-w-[calc(100%-48px)]` 夾住而存活，故須連 `max-w-none`） | 07-3 |
| R-PH-28 | axe（WCAG 2.0／2.1 A／AA）零違規，三個狀態各掃：關閉態（鈕在頂列）、開啟態、展開「全站共通」後；含 `color-contrast`、`label-content-name-mismatch`；路由 `/issues`、`/projects/p1`、`/settings`，視窗 1440×900 與 390×844 | ［實作］鈕改成半透明底白字（`bg-white/[0.14] text-white`，約 3.5:1）；說明文字改用 `text-wg-disabled-text` | 07-4 |
| R-PH-29 | 新檔遵守 `design-rules.test.ts`（只用 token、Lucide、無陰影漸層、無 `outline-none`、文字無 emoji 與色碼）；按鈕不得用半透明底白字 | ［實作］某說明句含 emoji 或 `#abc123`；鈕的 `className` 含 `outline-none` | 07-5、05-3 |

#### F 對話框內容與純文字（PRD §7、§8、FR-PH-02；`PageHelpDialog.tsx`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-30 | 骨架：標題「<固定頁名>・本頁說明」；四個 `h3` 依序「這頁做什麼」「怎麼用」「欄位說明」「狀態說明」；其後一個預設收合的 `details[data-testid="page-help-common"]`（摘要「全站共通」）；`states` 為空的頁顯示固定句；`steps` 以 `ol` 渲染；欄位表三欄、狀態表三欄，列數與順序＝登記內容，每表 `aria-label`、`th scope="col"`、`td[data-label]`；標題不含專案名等動態名稱 | ［實作］對調「怎麼用」與「欄位說明」；`details` 預設 `open`；表頭缺 `scope="col"`；把 `execute` 的 `title` 改成含樣板佔位（如 `"專案執行：${name}"`，AT-PH-03-5-1 紅） | 02-1、02-2、03-5 |
| R-PH-31 | 純文字：說明一律以 React 文字節點渲染；`lib/help/**`、`components/domain/help/**` 非測試檔無 `dangerouslySetInnerHTML` 與 Markdown 渲染器 import（react-markdown、rehype*、remark*、`@uiw/react-md-editor`、本專案 `components/markdown/*`）；`<script>`、`**`、反引號以字面文字顯示 | ［實作］以 `dangerouslySetInnerHTML` 渲染 `purpose`；import `react-markdown` | 02-3 |
| R-PH-32 | 無第二份說明：對話框文字只由登記內容（頁、狀態、全站共通、狀態名稱來源）與 D-PH-6 的固定文字組成；把每段登記文字與名稱來源換成哨兵後不得剩下任何其他字 | ［實作］狀態段多寫一句寫死的「請參閱各頁面」；欄位表加一列寫死的備註 | 02-4 |
| R-PH-33 | 多張狀態表：每表一個 `h4` 小標題（取自 `STATE_SOURCES[id].title`）與自己的表，順序＝該頁 `states` 的登記順序；議題中心頁的狀態段為四群詞表而非表 | ［實作］兩張表的渲染順序對調；小標題改寫死；同一頁的兩張表共用一個 `table` | 02-5 |
| R-PH-34 | 全站共通：`HELP_COMMON.fields` 涵蓋 PRD §4 末列各項（§5.3 `COMMON_ANCHORS`）、`HELP_COMMON.states` 為 `serviceState`（名稱取自 `SERVICE_LABEL`）、`sourceFiles` 為 `components/layout/**` 與 `hooks/useServiceStatus.ts`；任兩頁展開後該段文字相同（只寫一份）；沒有任何頁的 `states` 登記 `serviceState`；「幫助中心」列寫明公告列字樣目前不能點（PRD §7、R-5） | ［實作］刪 `HELP_COMMON.states`；把共通文字複製一份進某頁的 `fields`；`serviceState` 的名稱改寫死；把「幫助中心」列的 `meaning` 改成「點進去可看說明」 | 02-6 |

#### G 接入規範（PRD FR-PH-08、§9）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-35 | 新增 `app/**/page.tsx` 而沒登記、或新增 `NAV_REGISTRY` 項而其 `href` 無說明，跑 `npx vitest run` 即紅並指出修法 | ［上游］同 R-PH-02、R-PH-03 的兩個上游突變；本條另以合成目錄樹（不動工作樹）自證 | 08-1、08-2 |
| R-PH-36 | `Architecture.md` §5.4 接入檢查表增一格「說明登記表一列」，與 §3 目錄表兩列（`frontend/lib/help/`、`frontend/components/domain/help/`）、§5.2 Top 列（補「本頁說明鈕」）同一個 commit 由主控收齊 | ［閘］G-D1 的檢查腳本對合成文字自證（AT-PH-08-3-E-1） | 08-3 |

#### H 既有鎖同步（D-PH-18；PRD 勘誤 1-1、1-2）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-PH-37 | 本案唯一准改的既有測試 `components/domain/si/si.static.test.ts`：`bridgeLeaks` 的 `checkText` 第二分支只判 URL 形（B 式，D-PH-18：(i) 以 `/` 或 `scheme://` 起頭的字串，(ii) 樣板運算式之後的每個片段一律視為 URL 形），相對檔案路徑形（`components/domain/si/**`）回空；URL 形（`/si/x`、`/v1/si/x`、`https://x.example/si/status`、`${base}/si/x`、`${base}/v1/si/x`、`http://${h}:9000/si/x`）與 8081、BRIDGE 環境變數仍判紅；改動只在該分支與新增的兩個 `it`，不刪既有斷言 | ［實作］把第二分支還原成原式（含 `/si/` 路徑段即判，不論形態）→ AT-PH-06-2-3 紅；**第二分支整個拿掉**（只留第一分支與 8081 判準），或改成 A 式（`/si/` 在字串開頭或緊接樣板運算式後才判，行為等同拿掉）→ AT-PH-06-2-E-2 紅（只靠第二分支才紅的三個樣本回空）；只做 (i)、拿掉 (ii) → E-2 紅（兩個樣板片段樣本回空）；［閘］改了該檔別處的斷言 → G-C2 逐 hunk 核對紅 | 06-2 |

### 契約節（前端內部契約；本功能零 HTTP 契約，本節為真相——型別、公共面、DOM 與詞表以本節為準，PRD §8.1、§7 的示意與本節不同時以本節為準並於 §7.3 登記）

#### C0 共通約定

1. **純文字、零新端點**：說明內容全在程式碼庫（`lib/help/**`），經 PR 修改；渲染一律 React 文字節點；唯一的網路請求＝既有 `GET /api/v1/issues`（`limit=1`，唯讀，VIEWER 以上，`IC契約:138`），僅在議題中心說明開啟時送出（C6）。
2. **名稱不自持**：狀態名稱只取自既有常數表（`STATE_SOURCES[id].labelOf` 或鍵本身）；`StateRow` 刻意沒有 `label`／`name`（PRD §8.1）。
3. **件數不入斷言**：說明 id、路由、狀態表、列數一律由登記表推導；唯一的釘值是 §5.3 的必備子集（只准增不准減）、白名單 31 詞、六類資料來源、四個議題狀態詞門檻、60 code point 等 PRD 明寫的門檻。

#### C1 型別（`lib/help/types.ts`；PRD §8.1 逐字，加上兩個字面值聯集）

```ts
export type HelpId = "dashboard" | "projects" | "project-detail" | "goals" | "goal-detail" | "tasks" | "task-detail" | "project-form" | "goal-form" | "task-form" | "execute" | "monitor" | "import" | "settings" | "self-improving" | "issues";   // 姊妹案日後加成員（D-12）
export type StateTableId = "projectStatus" | "goalStatus" | "taskStatus" | "stepStatus" | "importStatus" | "runStatus" | "runTransition" | "reviewKind" | "reviewDecision" | "alertSeverity" | "alertRule" | "gateName" | "sddPhase" | "sddFsmState" | "serviceState" | "obsClass" | "propClass" | "propState";
export type FieldSource = "您填寫或選擇" | "系統自動產生" | "執行引擎回報" | "自我進化帳本" | "系統參數" | "其他頁面帶入";
export type HelpField = { name: string; meaning: string; source: FieldSource; sourceNote?: string };
export type StateRow = { meaning: string; next: string };        // 刻意沒有 label／name：名稱只取自既有常數表
export type HelpStateGroup = { table: StateTableId; name?: "label" | "raw" } | { legend: "issues" };   // name 預設 "label"
export type PageHelp = { id: HelpId; title: string; purpose: readonly string[]; steps: readonly string[]; fields: readonly HelpField[]; states: readonly HelpStateGroup[]; sourceFiles: readonly string[] };
export type CommonHelp = Pick<PageHelp, "fields" | "states" | "sourceFiles">;
```

`HelpId` 與 `StateTableId` 是 PRD 撰寫時的 16 與 18 個成員（§4、§8.2 的 id 逐字）；`PageHelp.id` 與 `PageHelp.title` 的關係：`title`＝固定頁名（不含專案名等動態名稱，PRD §8.1），對話框標題恆為「`<title>`・本頁說明」。

#### C2 登記表（`lib/help/registry.ts`）

| 匯出 | 型別 | 語意 |
|---|---|---|
| `HELP_PAGES` | `Readonly<Partial<Record<HelpId, PageHelp>>>` | 已寫頁（不含 `PENDING_HELP_PAGES`）；鍵＝`PageHelp.id` |
| `HELP_ROUTES` | `Readonly<Record<string, HelpId>>` | 路由樣板→說明 id；樣板為 Next 資料夾名（`/`、`/projects/[projectId]/goals/[goalId]` 等）；含 pending 頁的路由；不含 `/login` |
| `PENDING_HELP_PAGES` | `readonly HelpId[]` | 尚未寫的頁；每輪只准縮小；輪 3 為空 |
| `NO_STATE_PAGES` | `readonly HelpId[]` | `states` 為空的頁（撰寫時 `project-form`、`task-form`、`settings`） |
| `helpForPath(pathname)` | 簽章 `(pathname: string)`，回 `HelpId` 或 `null` | D-PH-2：靜態段優先、去尾斜線、大小寫敏感；與 pending 無關 |

#### C3 狀態表（`lib/help/states.ts`、`components/domain/help/stateSources.ts`）

`STATE_HELP[id][key]＝{ meaning, next }`（每張表全站一份；物件字面值逐表 `satisfies` 宣告，見〈公共面〉表）；`STATE_SOURCES[id]＝{ title, keys, labelOf? }`（`keys` 於載入時現讀既有常數；`labelOf` 缺＝只准 `raw`）。下表為 PRD §8.2 於 HEAD `000a217b` 的逐項複核（座標與列數皆吻合，列數僅作快照、不入斷言）：

| 表 id | 鍵來源（`AgentConsole/frontend/` 下） | 名稱來源（`labelOf`） | 列數 | 型別鎖（AC-PH-04-2） |
|---|---|---|---|---|
| `projectStatus` | `PROJECT_STATUS`（`lib/domain/status.ts:43`） | `.label` | 6 | `Record<ProjectStatus, StateRow>` |
| `goalStatus` | `GOAL_STATUS`（`:52`） | `.label` | 5 | `Record<GoalStatus, StateRow>` |
| `taskStatus` | `TASK_STATUS`（`:60`） | `.label` | 11 | `Record<TaskStatus, StateRow>` |
| `stepStatus` | `STEP_STATUS`（`:134`） | `.label`；`task-detail` 用 `raw` | 4 | `Record<ExecutionStepStatus, StateRow>` |
| `importStatus` | `IMPORT_STATUS`（`:78`） | `.label` | 6 | `Record<ImportStatus, StateRow>` |
| `runStatus` | `RUN_STATUS`（`:92`） | `.label` | 6 | `Record<RunStatus, StateRow>` |
| `runTransition` | `BRIDGE_TRANSITION`（`:102`，`Partial`，鍵 `PAUSING`、`CANCELLING`） | `.label` | 2 | （非完整 enum，不入十張） |
| `reviewKind` | `REVIEW_KIND`（`:115`） | `.label` | 4 | `Record<ReviewKind, StateRow>` |
| `reviewDecision` | `REVIEW_DECISION_LABEL`（`:123`） | 值 | 4 | `Record<ReviewDecision, StateRow>` |
| `alertSeverity` | `ALERT_SEVERITY`（`:142`，含 `INFO`） | `.label` | 3 | （含 `INFO`，非後端 enum，不入十張） |
| `alertRule` | `ALERT_RULE_LABEL`（`:160`） | 值 | 8 | `Record<AlertRule, StateRow>` |
| `gateName` | `GATE_LABEL`（`components/domain/import/gateErrors.ts:26`） | 值 | 6 | `Record<GateName, StateRow>` |
| `sddPhase` | `SDD_PHASE_LABEL`（`lib/domain/sdd.ts:162`） | 值 | 12 | `Record<string, …>`（鍵於執行期展開） |
| `sddFsmState` | 無單一常數：五個鍵（`HUMAN_PENDING`、`SPEC_FROZEN`、`ESCALATION`、`ESCALATION_FINAL`、`AUTOCLAUDE_DELEGATED`），子字串弱鎖（PRD §8.2 備註 2） | 鍵本身（`raw`） | 5 | 字面值聯集 |
| `serviceState` | `SERVICE_LABEL`（`hooks/useServiceStatus.ts:58`） | 值 | 5 | 字面值聯集，型別等式＝`ServiceState` |
| `obsClass` | `OBS_STATUS_OPTIONS` 去掉 `id===""`（`lib/domain/si.ts:206`） | `.label` | 3 | 字面值聯集 |
| `propClass` | `PROPOSAL_STATUS_OPTIONS` 去掉 `id===""`（`si.ts:212`） | `.label` | 3 | 字面值聯集 |
| `propState` | `PROP_STATE_KEYS`（新匯出，`si.ts:191` 後；＝`PROP_STATUS_BY_STATE` 的鍵，`:179-191`） | 鍵本身（`raw`） | 11 | 字串鍵（`retired` 只在 Console 表，PRD D-8） |

#### C4 對話框與按鈕的 DOM 契約（測試鉤；D-PH-4～7）

| 元素 | 契約 |
|---|---|
| 說明鈕 | `<button type="button" data-testid="page-help-open">`；文字節點「本頁說明」（`max-md:sr-only`）＋`BookOpen` 圖示（`aria-hidden`）；位於 `[data-region="top"]` 的右側群組末端；只在 `showTools` 分支內渲染；`TopRegion` 以 `next/dynamic` 載入（D-PH-17） |
| 對話框 | 建於 `DialogContent`（`components/ui/dialog.tsx`）；標題「`<title>`・本頁說明」；`role="dialog"` 元素帶 `data-testid="page-help-dialog"` |
| 段落 | `data-testid`＝`page-help-purpose`／`page-help-steps`／`page-help-fields`／`page-help-states`；各含一個 `h3`（全對話框 `h3` 恰四個，依序「這頁做什麼」「怎麼用」「欄位說明」「狀態說明」）；`steps` 為 `<ol><li>` |
| 表格 | 欄位表與每張狀態表為 `<table aria-label>`；`<thead>` 的 `th` 皆 `scope="col"`；每個 `td` 帶 `data-label`＝對應欄標題；欄標題：欄位表「欄位」「意思」「資料來源」，狀態表「狀態」「意思」「通常的下一步」（`raw` 表首欄「畫面上的原值」） |
| 多表 | 狀態段內每個群一個 `h4`（`STATE_SOURCES[id].title`）與一個 `data-testid="page-help-states-<表 id>"` 容器（內含該表） |
| 議題詞表群 | `data-testid="page-help-legend-statuses｜results｜sources｜severities"` 的 `<section aria-label>`，內 `h4` 群名＋`dl`（`dt` 名稱、`dd` 說明）；`page-help-legend-note`（`<p>`，缺席不渲染）；`page-help-legend-loading`（`role="status"`）；`page-help-legend-error`（`role="alert"`） |
| 全站共通 | `<details data-testid="page-help-common"><summary>全站共通</summary>…</details>`，接在四個段落之後、預設收合；內含欄位表（`HELP_COMMON.fields`）與 `serviceState` 狀態表 |

#### C5 lint 契約（`lib/help/lint.ts`）

D-PH-9 的六個匯出；白名單 31 詞（PRD §8.3）；ID 形態＝`OBS-SI-<數字>`、`PROP-SI-<數字>`、`DEF-<數字>-<數字>`（D-PH-10）；`FieldSource` 六類（C1）。判準細節與樣本見 §5.4、§5.5。

#### C6 詞表請求（唯一的新網路請求）

| 項 | 契約 |
|---|---|
| 端點 | `GET /api/v1/issues?limit=1`（`getIssues({ limit: 1 })`，`lib/api/endpoints.ts:603-608`；不改 `endpoints.ts`） |
| 取數 | `useQuery`，query key `["help","issuesLegend"]`，`...SI_QUERY_OPTIONS`（`lib/api/queries.ts:998`：`retry:false`、`staleTime:0`、`gcTime:0`、`refetchInterval:false`、`refetchOnWindowFocus:false`）；只在議題中心說明的對話框開啟時掛載（每次開啟重取、關閉即回收） |
| 使用的回應欄位 | `legend.statuses[].name／meaning`、`legend.results[]`、`legend.sources[]`、`legend.severities[].name／meaning`、`legend.updatedAtNote`（型別 `IssueLegend`，`lib/api/types.ts:422-431`） |
| 失敗 | 503、504、網路失敗、回應無詞表：D-PH-8 的失敗句；不重試、不顯示空表與過期資料 |
| 授權 | 沿既有 JWT 與 VIEWER 以上唯讀（`IC契約:138`）；前端不以角色擋 |

#### C7 資料所有權

說明內容（文字）所有權＝程式碼庫 `lib/help/**`，經 PR 與 SCG-4 審查修改；議題詞表所有權＝根層帳本與 `issuemap.py`（經 Bridge、console-api 傳遞，本功能唯讀）；本功能不新增任何資料表、Flyway 版本、Bridge 路由或契約檔。

## 1. AC → AT 映射表

PRD 的 43 條 AC 逐條映射；每條至少一個 AT（`AT-PH-<FR>-<AC>-<n>`），多數另有反向 AT（`AT-PH-<FR>-<AC>-E-<n>`；負控、邊界或錯誤路徑）。「載具」欄為 §3.1 的載具代碼；「輪」欄為該 AC 各 AT 的首輪綁定（各 AT 不同輪時列出全部）。審查核對型（AC-PH-06-1、08-3）與審查閘型（AC-PH-06-2 的真跑部分、06-4、03-6 的出口、07-5 的既有檔真跑）走 G 編號審查閘（載具 `GT`）；掌舵者真機 V1～V4（PRD §11）不計入自動 AT，對應見 §6.2。

#### FR-PH-01　說明鈕：全站一顆、同一元件、同一 testid — 5 條 AC、US-PH-01

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-01-1 | AT-PH-01-1-1 | AT-PH-01-1-E-1、AT-PH-01-1-E-2 | HB、HS | 1b |
| AC-PH-01-2 | AT-PH-01-2-1 | AT-PH-01-2-E-1 | HB | 1b |
| AC-PH-01-3 | AT-PH-01-3-1 | AT-PH-01-3-E-1 | HB | 1b |
| AC-PH-01-4 | AT-PH-01-4-1 | AT-PH-01-4-E-1 | HB | 1b |
| AC-PH-01-5 | AT-PH-01-5-1 | AT-PH-01-5-E-1 | HB | 1b |

#### FR-PH-02　對話框內容與純文字渲染 — 6 條 AC、US-PH-02

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-02-1 | AT-PH-02-1-1 | AT-PH-02-1-E-1 | HD | 1b |
| AC-PH-02-2 | AT-PH-02-2-1、AT-PH-02-2-2 | — | HD | 1b |
| AC-PH-02-3 | AT-PH-02-3-1、AT-PH-02-3-2 | AT-PH-02-3-E-1 | HD、HS | 1b |
| AC-PH-02-4 | AT-PH-02-4-1 | AT-PH-02-4-E-1 | HD | 1b |
| AC-PH-02-5 | AT-PH-02-5-1 | — | HD | 1b |
| AC-PH-02-6 | AT-PH-02-6-1 | AT-PH-02-6-E-1 | HD | 1b |

#### FR-PH-03　登記表與路由對應 — 6 條 AC、US-PH-03

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-03-1 | AT-PH-03-1-1 | AT-PH-03-1-E-1 | HR | 1a |
| AC-PH-03-2 | AT-PH-03-2-1 | AT-PH-03-2-E-1 | HR | 1a |
| AC-PH-03-3 | AT-PH-03-3-1、AT-PH-03-3-2 | AT-PH-03-3-E-1 | HR | 1a |
| AC-PH-03-4 | AT-PH-03-4-1 | AT-PH-03-4-E-1 | HR | 1a |
| AC-PH-03-5 | AT-PH-03-5-1、AT-PH-03-5-2 | AT-PH-03-5-E-1 | HL | 1a |
| AC-PH-03-6 | AT-PH-03-6-1、AT-PH-03-6-2、AT-PH-03-6-3 | — | HR、GT | 1a、3 |

#### FR-PH-04　狀態詞不自持；鍵集合雙向鎖 — 7 條 AC、US-PH-04

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-04-1 | AT-PH-04-1-1、AT-PH-04-1-2、AT-PH-04-1-3 | AT-PH-04-1-E-1、AT-PH-04-1-E-2 | HK | 1a |
| AC-PH-04-2 | AT-PH-04-2-1、AT-PH-04-2-2、AT-PH-04-2-3 | AT-PH-04-2-E-1 | HK＋TC | 1a |
| AC-PH-04-3 | AT-PH-04-3-1、AT-PH-04-3-2、AT-PH-04-3-3 | AT-PH-04-3-E-1 | HK、HD | 1a、1b |
| AC-PH-04-4 | AT-PH-04-4-1、AT-PH-04-4-2、AT-PH-04-4-3 | AT-PH-04-4-E-1 | HD、HS | 1b |
| AC-PH-04-5 | AT-PH-04-5-1、AT-PH-04-5-2、AT-PH-04-5-3、AT-PH-04-5-4 | AT-PH-04-5-E-1、AT-PH-04-5-E-2、AT-PH-04-5-E-3 | HD、HS | 1b |
| AC-PH-04-6 | AT-PH-04-6-1、AT-PH-04-6-2、AT-PH-04-6-3 | — | HK、HD | 1a、3 |
| AC-PH-04-7 | AT-PH-04-7-1、AT-PH-04-7-2 | AT-PH-04-7-E-1 | HK | 1a |

#### FR-PH-05　白話與內容品質（機械可驗的部分） — 7 條 AC、US-PH-05

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-05-1 | AT-PH-05-1-1 | AT-PH-05-1-E-1 | HL、HN | 1a |
| AC-PH-05-2 | AT-PH-05-2-1、AT-PH-05-2-2 | AT-PH-05-2-E-1 | HL、HN | 1a |
| AC-PH-05-3 | AT-PH-05-3-1、AT-PH-05-3-2 | — | HL、HN | 1a |
| AC-PH-05-4 | AT-PH-05-4-1 | AT-PH-05-4-E-1 | HL＋TC、HL | 1a |
| AC-PH-05-5 | AT-PH-05-5-1、AT-PH-05-5-2、AT-PH-05-5-3 | AT-PH-05-5-E-1 | HS | 1a |
| AC-PH-05-6 | AT-PH-05-6-1 | AT-PH-05-6-E-1 | HN | 1a |
| AC-PH-05-7 | AT-PH-05-7-1、AT-PH-05-7-2 | — | HS | 1a、2 |

#### FR-PH-06　零侵入與單一真相 — 4 條 AC、US-PH-06

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-06-1 | AT-PH-06-1-1 | AT-PH-06-1-E-1 | GT | 1a |
| AC-PH-06-2 | AT-PH-06-2-1、AT-PH-06-2-2、AT-PH-06-2-3 | AT-PH-06-2-E-1、AT-PH-06-2-E-2 | GT、HX | 1a、1b |
| AC-PH-06-3 | AT-PH-06-3-1、AT-PH-06-3-2 | AT-PH-06-3-E-1 | E2 | 1b |
| AC-PH-06-4 | AT-PH-06-4-1 | AT-PH-06-4-E-1 | GT | 1b |

#### FR-PH-07　無障礙與響應式 — 5 條 AC、US-PH-07

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-07-1 | AT-PH-07-1-1、AT-PH-07-1-2 | AT-PH-07-1-E-1 | HB、E2 | 1b |
| AC-PH-07-2 | AT-PH-07-2-1、AT-PH-07-2-2 | AT-PH-07-2-E-1 | HS、HD | 1b |
| AC-PH-07-3 | AT-PH-07-3-1、AT-PH-07-3-2 | AT-PH-07-3-E-1 | E2 | 1b |
| AC-PH-07-4 | AT-PH-07-4-1、AT-PH-07-4-2、AT-PH-07-4-3 | — | E2 | 1b |
| AC-PH-07-5 | AT-PH-07-5-1、AT-PH-07-5-2 | AT-PH-07-5-E-1 | HS、GT | 1a、1b |

#### FR-PH-08　接入規範：新頁面必帶說明 — 3 條 AC、US-PH-08

| AC | 正向 AT | 反向 AT | 載具 | 輪 |
|---|---|---|---|---|
| AC-PH-08-1 | AT-PH-08-1-1 | AT-PH-08-1-E-1 | HR | 1a |
| AC-PH-08-2 | AT-PH-08-2-1 | AT-PH-08-2-E-1 | HR | 1a |
| AC-PH-08-3 | AT-PH-08-3-1 | AT-PH-08-3-E-1 | GT | 3 |

## 2. 可自動化 AT 格式規範

**編號與命名**：AT 編號 `AT-PH-<FR>-<AC>-<n>`（正向）、`AT-PH-<FR>-<AC>-E-<n>`（反向），`<FR>`、`<AC>` 取 PRD AC 編號的兩段（`AC-PH-04-5`→`AT-PH-04-5-1`）；`n` 為 1～9。測試標題一律以 AT 編號的底線形開頭：

| 載具 | 命名 | 例 |
|---|---|---|
| vitest（HL、HR、HN、HK、HB、HD、HS） | `it("AT_PH_<FR>_<AC>_<n> <中文描述>", …)`、`it("AT_PH_<FR>_<AC>_E_<n> <中文描述>", …)`（沿 `AT_932_6_1 …`、`AT_IC_08_2_1 …` 先例；`-t` 以子字串比對，`n` 只用 1～9 故無前綴相撞） | `it("AT_PH_04_5_E_1 詞表失敗不重試：恰一個請求", …)` |
| 型別鎖（標 TC） | 同 vitest 命名；判定另加 `npx tsc --noEmit`（`tsconfig.json` 的 `include` 含 `**/*.ts`、`**/*.tsx`，tsc 會檢查測試檔，`@ts-expect-error` 生效） | `it("AT_PH_04_2_2 十張表的鍵集合型別等式", () => { expectTypeOf<…>().toEqualTypeOf<…>(); })` |
| Playwright | `test("AT_PH_<FR>_<AC>_<n> <描述>", …)`；`-g` 比對 | `test("AT_PH_07_3_1 390 寬對話框不超出視窗", …)` |
| 審查閘（GT） | 無測試函式；判定＝SCG-4 通過標準的 G 編號指令輸出 | AT-PH-06-1-1 → G-C1 |

**判定指令樣板**（`<id>` 為 AT 編號的底線形，例 `AT_PH_01_1_1`；rc 先存變數再讀，不接管線；不裸 `cd`）：

```powershell
# vitest
Push-Location <repo>\AgentConsole\frontend; $o = & npx vitest run <檔> -t "<id>" 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# 型別鎖（TC）
Push-Location <repo>\AgentConsole\frontend; $o = & npx tsc --noEmit 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# Playwright（mock；CI 以 standalone 產物跑：先 npm run build，再設 E2E_MODE=standalone）
Push-Location <repo>\AgentConsole\frontend; $o = & npx playwright test tests/e2e/page-help.mock.spec.ts -g "<id>" --output <各自暫存目錄> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
```

Playwright 一律帶各自的 `--output` 目錄（共用 `test-results` 會被並行的 Playwright 行程清空，`tests/e2e/README.md:29`）；`E2E_MODE=standalone` 時須先以同一個環境 `npm run build`；本檔的 mock spec 不需後端與資料庫，不需 `E2E_ROOT`（那是真 Bridge specs 的變數，Windows 上也不適用，README 第 137 行）。

**零測試視為失敗**：vitest `No test files found`／`no tests`、Playwright `No tests found` 一律 FAIL（`-t`、`-g` 無命中＝該 AT 未實作）；新檔不得含 `it.skip`、`it.todo`、`test.skip`、`test.fixme`、`.only`（G-F9 以 `Select-String` 查，命中即紅；跳過不算通過，根 CLAUDE.md 規則 12）。

**AT 區塊樣式（由載具代碼與樣板推得其餘後設資料）**

```
// AT-PH-04-5-E-1                         // 對應 AC: AC-PH-04-5（PRD §5；R-PH-12）
// 測試類型: Component                    // 自動化工具: vitest＋@testing-library/react＋fetch 替身（APP_QC）
// 判定指令: npx vitest run components/domain/help/PageHelpDialog.test.tsx -t "AT_PH_04_5_E_1"
Given 議題詞表請求回 503（details.cause 等三項齊全），app 預設的 QueryClient（對 5xx 重試一次）
When  開啟議題中心說明並等到錯誤句
Then  詞表請求恰 1 個；等 1,500 毫秒仍為 1 個（SI_QUERY_OPTIONS 的 retry:false 真的套用）
```

**測試檔規則**（八個新測試檔：vitest 七支＋Playwright 一支）：

1. 路徑與檔名與 PRD §9 逐一相同，**不多不少**（`lib/help/{content,registry,lint}.test.ts`、`components/domain/help/{stateKeys.test.ts,PageHelpButton.test.tsx,PageHelpDialog.test.tsx,help.static.test.ts}`、`tests/e2e/page-help.mock.spec.ts`），另唯一准改的既有測試是 `components/domain/si/si.static.test.ts`（D-PH-18）；不另建輔助檔（PRD §9 的檔案集合與 AC-PH-06-1 不容許）：夾具與掃描器住各自的測試檔內，共用的假後端與登入輔助沿用既有檔（只讀取用、不修改）：`components/domain/issues/tests/issues.fixtures.ts` 的 `renderIssues`、`newStub`、`stubIssuesApi`、`unavailable`、`signInAs`、`LEGEND`、`clone`（`renderIssues` 以真 `Providers` 渲染，議題詞表測試的主力夾具）與 `tests/helpers/api.tsx` 的 `stubApi`、`envelope`、`failure`、`signIn`（不用其 `makeClient()`，D-PH-16）。
2. 檔頭 JSDoc 註解寫明：TCS 編號、涵蓋的 AC 與 R、判定指令（沿既有測試檔風格）。
3. 注入縫只有 D-PH-3 的 `content` 參數與 `vi.mock("next/navigation")`、`vi.mock("next/link")`、`vi.stubGlobal("fetch")`（`tests/helpers/api.tsx` 的 `stubApi`）；**不得** `vi.mock` 換掉 `@/lib/help/*` 或 `stateSources`（那會讓「登記內容」與「渲染」脫鉤而測不到真登記）。
4. 檔案路徑一律 `path.join`；測試以 `process.cwd()`（＝`AgentConsole/frontend`）為根，沿 `issues.static.test.ts` 的 `ROOT`、`rel`、`walk`、`SKIP_DIRS`；LF、UTF-8。
5. Prettier（`.prettierrc`：`printWidth: 200`、雙引號、尾逗號、LF）與 ESLint（`eslint-config-next`）：新檔過 `npm run lint`（含 `format:check`）；`npx tsc --noEmit` 含測試檔；每個 `@ts-expect-error` 必帶說明文字（`@typescript-eslint/ban-ts-comment` 為 error，要 ≥ 3 字）；不在 effect 內同步 `setState`（`react-hooks/set-state-in-effect` 為 error，D-PH-4）；二者皆已實測，§5.8。
6. 測試碼不得出現 `OBS-SI-` 接數字的片段（只准 PRD 與本檔已引的真 ID：`OBS-SI-001`、`PROP-SI-004`）；DEF 編號一律在執行期組字串（`"DEF-" + "1-2"`）；任何「測試摘要字樣＋4 位數字」不得同行（基線站點鎖；寫「通過」）。
7. 不新增守衛碼、不改 `.claude/**`、`settings*.json`、`tools/**`、`.github/**`。

**突變規格**：每個 R 條文的突變欄標明套用面（［上游］／［實作］／［閘］，見〈R 條文〉節頭）；QA 在 `git archive <HEAD>` 匯出的暫存副本上重放（**不在工作樹套用**、不用 `git checkout --` 還原；frontend 副本以 junction 把 `node_modules` 指回工作樹；無 `.git` 的副本會讓讀 git 的測試恆紅，要先量基線再判），各跑所列 AT 的判定指令，須見轉紅；回報「突變 R-PH-nn：killed／survived」，倖存者須補 AT 並勘誤。本功能無既有突變 spec，QA 自備，同名突變列全。

## 3. AT 完整清單

### 3.1 載具代碼與判定指令（每個 AT 的「載具」欄；判定指令樣板見 §2）

| 代碼 | 載具 | 檔案 | 判定指令樣板（`<id>`＝AT 編號底線形，§2） | 持有面與時機 | AT 數 |
|---|---|---|---|---|---|
| HL | vitest（部分另以 tsc 判定，標 TC） | `lib/help/content.test.ts`（新） | `npx vitest run <本列檔案> -t "<id>"`；TC 者另跑 `npx tsc --noEmit` | 輪 1a 建 | 8（其中 TC 1 個） |
| HR | vitest | `lib/help/registry.test.ts`（新） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1a 建；每棒下修 `PENDING_CEILING` | 15 |
| HN | vitest | `lib/help/lint.test.ts`（新） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1a 建 | 6 |
| HK | vitest（部分另以 tsc 判定，標 TC） | `components/domain/help/stateKeys.test.ts`（新） | `npx vitest run <本列檔案> -t "<id>"`；TC 者另跑 `npx tsc --noEmit` | 輪 1a 建 | 17（其中 TC 4 個） |
| HB | vitest（RL） | `components/domain/help/PageHelpButton.test.tsx`（新） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1b 建 | 12 |
| HD | vitest（PD） | `components/domain/help/PageHelpDialog.test.tsx`（新） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1b 建 | 21 |
| HS | vitest（靜態） | `components/domain/help/help.static.test.ts`（新） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1a 起建（出處鎖、表單抽取器）、輪 1b 補（元件靜態鎖） | 16 |
| HX | vitest（既有檔的同步鎖） | `components/domain/si/si.static.test.ts`（既有，**改**；本案唯一准改的既有測試，D-PH-18） | `npx vitest run <本列檔案> -t "<id>"` | 輪 1a 改 | 2 |
| E2 | Playwright（mock API） | `tests/e2e/page-help.mock.spec.ts`（新） | `npx playwright test <本列檔案> -g "<id>" --output <各自目錄>` | 輪 1b 建、輪 3 完整 | 10 |
| GT | 審查閘（指令型 AT，不入單元測試） | SCG-4 通過標準的 G 編號指令 | 見該 AT 的 Given 欄所指 G 編號 | 共同（主控／QA） | 11 |
| 合計 | | | | | 118（vitest 97、Playwright 10、審查閘 11） |

### 3.2 AT 清單（依 FR；每列＝一個 AT）

「輪」欄＝該 AT 自哪一棒起必須綠且非空轉（§6.4；輪 1 切 1a、1b 兩半：1a＝資料層，1b＝元件、接入與 e2e）；對「已寫頁」逐頁迴圈的 AT 標 1a 或 1b，並**逐輪綁定**——頁從 `PENDING_HELP_PAGES` 移進 `HELP_PAGES` 的那一輪起自動納入迴圈（pending 頁由 AT-PH-03-4、03-6 保證不會被靜默漏掉）。夾具名詞（RL、PD、錨點頁、登記頁、FIXED_TEXT、PAGE_STATES、ROUTE_TABLE、APP_QC、哨兵）定義於 §5。`-E-` 為反向 AT（負控、邊界或錯誤路徑）。

#### FR-PH-01 的 AT　說明鈕：全站一顆、同一元件、同一 testid

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-01-1-1 | HB | 1b | RL（OPERATOR 已登入、`pathname="/projects"` 錨點頁）渲染 | `[data-region="top"]` 內 `[data-testid="page-help-open"]` 恰 1 個、`tagName` 為 BUTTON、可見文字含「本頁說明」；它與 `bell-trigger`、待審批佇列連結（`getByRole("link", { name: /^待審批佇列/ })`）同一個父節點（右側群組）且在文件順序上位於兩者之後；`[data-region="content"]` 內該 testid 為 0 個 |
| AT-PH-01-1-E-1 | HB | 1b | 同上，再依序把 `pathname` 改成 `/settings`、`/issues` 並 `rerender` | 每次整頁 `page-help-open` 仍恰 1 個（不因路由變更重複渲染）；`tools`、`bottom`、`content` 三區內各 0 個 |
| AT-PH-01-1-E-2 | HS | 1b | 掃 `components/**`、`app/**` 非測試檔（`walk` 規則），以 AST 找 `<PageHelpButton` 的 JSX 使用處（`TopRegion` 以 `next/dynamic` 載入時，識別字仍須叫 `PageHelpButton`，D-PH-17；比對 JSX 標籤名，不看 import 形態） | 使用處恰 1 個且在 `components/layout/TopRegion.tsx`；該元素位於 `showTools` 為真的條件分支內（祖先含 `ConditionalExpression`，條件為識別字 `showTools`，元素在 `whenTrue` 側）；合成樣本：寫在分支外、寫在 `app/` 某頁、寫兩處者各回非空，合規樣本回空 |
| AT-PH-01-2-1 | HB | 1b | 四組情境各用 RL 渲染：(a) 已登入且 `pathname="/login"`；(b) 未登入（無 session）於 `/projects`；(c) 已登入於 `/unknown`；(d) 已登入於 `/projects-x`；另一組對照 (e) 已登入於 `/projects` | (a)～(d) 的 `page-help-open` 皆為 0 個；(e) 恰 1 個（防空轉） |
| AT-PH-01-2-E-1 | HB | 1b | 對 `HELP_ROUTES` 的每個樣板取具體路徑（`[projectId]`→`p1`、`[goalId]`→`g1`、`[taskId]`→`t1`）設 `pathname`，RL 渲染（OPERATOR） | 每條路由的鈕數＝（其 id 在 `HELP_PAGES` 內 ? 1 : 0）：pending 頁的路由 0 個、已寫頁的路由 1 個；至少一條為 1（防空轉）；`PENDING_HELP_PAGES` 為空時全部為 1 |
| AT-PH-01-3-1 | HB | 1b | 對 VIEWER、OPERATOR、ADMIN 各 `signIn` 後 RL 渲染（`pathname="/projects"`），`userEvent.click` 該鈕，取對話框 | 三種角色皆：鈕存在且 `toBeEnabled()`、`getByRole("dialog", { name: "<該頁 title>・本頁說明" })` 出現；三份對話框的 `textContent`（空白正規化）逐字相同（內容不隨角色而變） |
| AT-PH-01-3-E-1 | HB | 1b | VIEWER、`pathname="/issues"`（詞表以 fetch 替身供給），點鈕 | 對話框可開；鈕無 `disabled`、無 `aria-disabled`；詞表請求仍送出一次（VIEWER 以上可讀，前端不以角色擋）；對話框內無任何寫入類控制項（無 `input`、`textarea`、`select`、送出鈕） |
| AT-PH-01-4-1 | HB | 1b | RL（`pathname="/projects"`）依序：(1) 按鈕開啟對話框；(2) `pathname` 改成 `/settings` 後 `rerender`；(3) **不按任何鈕**，`pathname` 直接改回 `/projects` 後 `rerender`；(4) 再改成 `/settings` 後 `rerender`，按鈕 | (2) `queryByRole("dialog")` 為 null（已關閉）；(3) 仍為 null（A→B→A 不得重開：D-PH-4 禁用的 `openFor === pathname` 衍生寫法在此會讓對話框重現，所以 (3) 前不得在 B 按鈕——按了會把 `openFor` 覆寫成 B 而掩蓋缺陷）；(4) 對話框名稱為「<settings 的 title>・本頁說明」，且文件內找不到 `projects` 說明項 `purpose[0]` 的文字（不殘留舊頁內容） |
| AT-PH-01-4-E-1 | HB | 1b | 對話框開啟中且 `pathname` 不變：(a) `rerender` 同一棵樹；(b) 對頂列搜尋框做 `fireEvent.change`（讓 `TopRegion` 自身狀態變動而重繪） | 兩種情況對話框都仍開啟、內容不變（只有路由變更才關閉；不得每次重繪就關或重設） |
| AT-PH-01-5-1 | HB | 1b | RL（`/projects`），`getAllByRole("button", { name: /本頁說明/ })` | 恰 1 個；可見文字節點含「本頁說明」且該文字所在元素的 `className` 含 `max-md:sr-only`；圖示 `svg` 帶 `aria-hidden="true"`；按鈕沒有 `aria-label` 屬性（`getAttribute("aria-label")` 為 null：名稱來自文字節點，D-PH-4；Label in Name 沿 `layout.test.tsx:173-198`）；沒有只靠 `title` 取名 |
| AT-PH-01-5-E-1 | HB | 1b | 同上，取可存取名稱（`getByRole` 的 `name` 同源計算） | 名稱恰為「本頁說明」（不因 `sr-only` 而變）；名稱不含「幫助中心」「說明文件」（與公告列靜態字樣區別，R-5）；公告列「幫助中心」仍是不可點的 `span`（`getByText("幫助中心", { exact: true })` 的元素 `tagName` 非 BUTTON、非 A） |

#### FR-PH-02 的 AT　對話框內容與純文字渲染

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-02-1-1 | HD | 1b | PD 逐頁渲染：登記頁每一頁（`Object.values(HELP_PAGES)`）加一個合成的 `states: []` 頁（防空轉：至少含一個有狀態表的頁與一個無狀態的頁）；fetch 替身供議題詞表 | 逐頁：`dialog` 名稱＝「`<title>`・本頁說明」；`h3`（`level 3`）恰四個、文字依序為「這頁做什麼」「怎麼用」「欄位說明」「狀態說明」；其後（文件順序）有且僅有一個 `details[data-testid="page-help-common"]`、無 `open` 屬性、`summary` 文字「全站共通」；`purpose` 段含該頁全部 `purpose` 項文字；`steps` 以 `ol > li` 渲染、`li` 數＝`steps.length`；`states` 為空者「狀態說明」段文字恰為「這一頁沒有會變動的狀態。」且段內無 `table`、`dl`、`h4` |
| AT-PH-02-1-E-1 | HD | 1b | 合成頁（三個狀態群）：(a) 點 `summary`；(b) 關閉對話框後重新開啟 | (a) `details` 變為 `open`；(b) 重新開啟後 `details` 又是收合（預設收合：`details` 隨對話框內容卸載重掛）；兩種狀態下 `h3` 都恰四個（小標題與群組標題一律 `h4`，不增加 `h3`） |
| AT-PH-02-2-1 | HD | 1b | PD 逐頁（登記頁）取 `fields` 段的表 | 表有非空 `aria-label`；`columnheader` 文字依序為「欄位」「意思」「資料來源」，每個 `th` 帶 `scope="col"`；資料列數與順序＝該頁 `fields`；每列三格依序＝`name`、`meaning`、含 `source`（有 `sourceNote` 者同格也含它）；每個 `td` 帶 `data-label`＝對應欄標題 |
| AT-PH-02-2-2 | HD | 1b | PD 合成頁：`states: [{ table: "projectStatus" }, { table: "stepStatus", name: "raw" }]` | 兩張狀態表各有非空 `aria-label`、`th scope="col"`、`td[data-label]`；欄標題＝「狀態」「意思」「通常的下一步」，**只有** `raw` 那張首欄標題是「畫面上的原值」；列數與順序＝`Object.keys(STATE_HELP[表 id])`；每列「意思」「通常的下一步」格逐字＝該列的 `meaning`、`next` |
| AT-PH-02-3-1 | HD | 1b | PD 合成頁：每個文字欄（`title`、`purpose`、`steps`、欄位 `name`／`meaning`／`sourceNote`、狀態 `meaning`／`next`、全站共通欄位）都換成 §5.4 的逸出樣本（`<script>alert(1)</script>`、`**粗體**`、帶反引號的 `` `§反引號§` ``、`[連結](https://example.test)`、`<img src=x onerror=alert(1)>`、`&amp;`） | 對話框 `textContent` 逐字含各樣本（含 `**`、反引號、`](` 等記號本身）；對話框 DOM 內沒有 `script`、`img`、`a[href]` 元素；沒有任何元素的 `textContent` 恰等於「粗體」「§反引號§」「連結」（Markdown 若被渲染，記號會消失並長出獨立的 `strong`、`code`、`a` 元素；不以標籤名判，因為設計上可能用 `code` 呈現原值狀態名）；`&amp;` 顯示為「&amp;」五個字元（不被解成「&」）；`window.alert` 未被呼叫 |
| AT-PH-02-3-2 | HS | 1b | 掃 `lib/help/**` 與 `components/domain/help/**` 的非測試檔（略過 `tests` 目錄、`*.test.ts(x)`、`*.d.ts`、`*.fixtures.ts`） | 無 `dangerouslySetInnerHTML`；無任何 Markdown／HTML 渲染器 import（`react-markdown`、`rehype*`、`remark*`、`@uiw/react-md-editor`、本專案 `components/markdown/*` 含相對路徑與動態 `import()`）；防反空轉：掃描檔數 ≥ 8，且含 `lib/help/registry.ts` 與 `components/domain/help/PageHelpDialog.tsx` |
| AT-PH-02-3-E-1 | HS | 1b | 掃描器負控（合成原始碼，沿 `issues.static.test.ts:164-191` 的樣本） | `dangerouslySetInnerHTML`、`react-markdown`、`rehype-raw`、`remark-gfm`、`@uiw/react-md-editor`、`@/components/markdown/…`、相對路徑 `../../markdown/…`、動態 `import("react-markdown")` 逐一回非空；`@/components/ui/button`、`const html = '<b>字面文字</b>'`、`./markdownLike` 回空 |
| AT-PH-02-4-1 | HD | 1b | PD 搭 `content` 縫＋哨兵內容（§5.1 哨兵）：合成頁的 `title`、`purpose`、`steps`、欄位 `name`／`meaning`／`sourceNote`、`HelpContent.common`（欄位與 `sourceNote`）、`states` 的 `meaning`／`next`、`sources` 的 `title`／`labelOf` 輸出／`keys` 全換成互不相同的哨兵字串；頁含：一張 label 表、一張 `raw` 表、有欄位與 `sourceNote`、非空 `steps` | `dialog.textContent` 扣掉全部哨兵（`§…§` 形）、D-PH-6 的固定文字（§5.3 `FIXED_TEXT`）、標點與空白後為空字串；哨兵個數＝內容中哨兵總數（每個都出現、互不相同、無遺漏）；原真實內容的任何一句都不在對話框內 |
| AT-PH-02-4-E-1 | HD | 1b | 偵測函式 `strayText(textContent, sentinels, fixed)` 的負控（測試內純函式） | 對「哨兵齊全＋多一句寫死的『請參閱各頁面』」回非空；對「哨兵齊全且只有固定文字」回空；對「少一個哨兵」回缺漏；哨兵產生器產出的字串互不相同 |
| AT-PH-02-5-1 | HD | 1b | PD 合成頁：`states` 三個群 `[projectStatus, stepStatus(raw), alertRule]`；另對登記頁逐頁 | 狀態段內 `h4` 數＝群數、文字依序＝`STATE_SOURCES[id].title`；每群各有一個 `[data-testid="page-help-states-<表 id>"]` 內含自己的 `table`；順序＝`states` 登記順序；登記頁逐頁同樣成立，**但 `issues` 頁排除**：它的狀態段是 API 詞表四群（四個 `h4`＝狀態、結果、來源、嚴重度，見 04-4-1），不適用「`h4` 數＝群數」，對它只斷言沒有 `table` 且 `h4` 恰為那四個群標題 |
| AT-PH-02-6-1 | HD | 1b | PD 對登記頁中任兩頁（至少含 `issues`、`projects`），各自展開 `page-help-common` | 兩頁 `page-help-common` 的 `textContent` 逐字相同；其內欄位表的欄位名每個 `COMMON_ANCHORS` 錨點都至少被一個欄位名包含；狀態表為 `serviceState`：首欄逐列＝`Object.keys(STATE_HELP.serviceState).map((k) => SERVICE_LABEL[k])`（名稱取自 `SERVICE_LABEL`，現讀 `hooks/useServiceStatus.ts`）；其內 `td[data-label]` 齊全；`HELP_COMMON.fields` 中名稱含「幫助中心」的列，其 `meaning` 含「不能點」或「不可點」（PRD §7、R-5：全站共通段寫明公告列「幫助中心」字樣目前不能點，與本鈕區別） |
| AT-PH-02-6-E-1 | HD | 1b | 掃登記表 | 沒有任何頁的 `states` 登記 `serviceState`（只寫一份）；`page-help-common` 位於四個 `h3` 段之後且不在任何段內；全站共通的文字不出現在頁的 `purpose`、`steps`、`fields` 之中（`HELP_COMMON.fields` 的每個 `meaning` 不是任何頁 `fields[].meaning` 的子字串） |

#### FR-PH-03 的 AT　登記表與路由對應

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-03-1-1 | HR | 1a | 沿 `lib/nav/registry.test.ts:46-68` 的 walker 取 `app/**/page.tsx` 路由樣板（根路由為 `/`，括號群組不進網址，動態段保留方括號名），減排除名單 `["/login"]` | 集合與 `Object.keys(HELP_ROUTES)` 相等；防反空轉：路由數 > 10；`/login` 不在 `HELP_ROUTES` 鍵中；每個鍵的值都在 `HelpId` 集合內（`HELP_PAGES` 鍵∪`PENDING_HELP_PAGES`） |
| AT-PH-03-1-E-1 | HR | 1a | 純函式 `routeProblems(templates, helpKeys, exclude)` 與合成目錄樹（tmp 目錄，含 `(app)/x/page.tsx` 路由群組、`[id]/page.tsx`、根 `page.tsx`） | walker 把 `(app)/x/page.tsx` 解成 `/x`、`[id]` 保留為 `/[id]`、根為 `/`；缺一個鍵、多一個鍵各回非空；`/login` 在排除名單內不算缺；訊息逐字含「在 `lib/help/<id>.ts` 新增並於 `registry.ts` 登記」 |
| AT-PH-03-2-1 | HR | 1a | 對 `NAV_REGISTRY` 每個 `enabled` 項，取其 `href` 的兩種解析（字串直取；函式型以 `{ currentProjectId: null }` 與 `{ currentProjectId: "p1" }` 呼叫），去掉 `?`、`#` 後的路徑 | 每個解析結果經 `helpForPath` 皆非 null；防反空轉：檢查的解析數 ≥ 登記表 `enabled` 項數；`enabled: false` 項不納入 |
| AT-PH-03-2-E-1 | HR | 1a | 純函式 `navProblems(registry, resolve)` 餵合成登記表：(a) 一項 `href: "/login"`；(b) 函式型 `href` 的一個分支指向 `/unknown`；(c) `enabled: false` 且 `href: "/unknown"` | (a)(b) 各回非空並含該項 `id`；(c) 回空（停用項豁免）；合規登記表回空 |
| AT-PH-03-3-1 | HR | 1a | PRD AC-PH-03-3 的代表路徑逐字 | `/`→`dashboard`、`/projects/new`→`project-form`、`/projects/p1`→`project-detail`、`/projects/p1/edit`→`project-form`、`/projects/p1/goals/g1/tasks/t1/edit`→`task-form`、`/projects/p1/`→`project-detail`；`""`、`/unknown`、`/projects-x`、`/login`→`null` |
| AT-PH-03-3-2 | HR | 1a | §5.3 `ROUTE_TABLE`（PRD §4 的 19 條路由→id，動態段代入 `p1`／`g1`／`t1`），並以測試內獨立比對器（逐段比對：靜態段相等或動態段非空，取靜態段最多者）重算 | 19 條具體路徑逐一＝表中 id；`Object.keys(HELP_ROUTES)` ⊇ 表中 19 個樣板且各自的 id 相同（姊妹案新增者不在表內也不影響）；每條具體路徑「最具體的符合樣板」唯一（不存在兩個同樣具體的樣板）；`helpForPath` 的結果＝獨立比對器的結果 |
| AT-PH-03-3-E-1 | HR | 1a | 邊界路徑 | `/projects/%E4%B8%AD/goals`（URL 編碼的非 ASCII id）與 `/projects/中文/goals`→`goals`；`/Projects`→`null`（大小寫敏感）；`/projects/p1/goals/g1/tasks/t1/edit/x`（多一段）→`null`；`/issues/x`→`null`（導覽 `match` 用前綴、路由表沒有）；`/projects/new` 與 `/projects/p1/goals/new`、`/projects/p1/goals/g1/tasks/new` 取靜態段（`project-form`、`goal-form`、`task-form`）；pending 頁的路由仍回其 id（與 `PENDING_HELP_PAGES` 無關） |
| AT-PH-03-4-1 | HR | 1a | `readdirSync` 列 `lib/help/`：扣掉 `types`、`states`、`registry`、`lint`、`common` 與測試檔，餘為頁檔；以動態 ``await import(`./${name}`)`` 取各頁檔模組（不用 `import.meta.glob`：tsc 缺 `vite/client` 型別會使 G-F4 紅；審查鏡實測 Vite 對此動態寫法印 `vite:dynamic-import-vars` 警告，屬已知、rc 不受影響，不得為消除警告改用 `import.meta.glob`，可加 `/* @vite-ignore */`） | 頁檔 id 集合（檔名去 `.ts`）＝`Object.keys(HELP_PAGES)`∪`PENDING_HELP_PAGES`；兩者互斥；每個頁檔模組恰匯出一個帶 `id` 的 `PageHelp`，其 `id` 等於檔名；pending 頁的頁檔存在（可為佔位）；防反空轉：頁檔數 ≥ 3（輪 1 的先導頁） |
| AT-PH-03-4-E-1 | HR | 1a | 純函式 `pageFileProblems(fileNames, helpKeys, pending, ids)` 餵合成輸入 | 多一個頁檔、少一個頁檔、檔內 `id` 與檔名不符、同一 id 同在 `HELP_PAGES` 與 `PENDING` 四種各回非空；合規輸入回空 |
| AT-PH-03-5-1 | HL | 1a | 對 `Object.values(HELP_PAGES)`（已寫頁；pending 頁豁免）逐頁 | `purpose` 每項非空，且以 `lint.ts` 的 `splitSentences` 對全部 `purpose` 項切句後合計 1～3 句（與 AT-PH-05-1-1 的「每頁 `purpose` 合計 ≤ 3 句」同一判準，勘誤 1-5）；`steps.length` 2～8；`fields.length ≥ 1`；`sourceFiles.length ≥ 1` 且每條路徑存在（檔案存在，或 `dir/**` 的 `dir` 存在且展開後 ≥ 1 個檔）；`states.length === 0` ⇔ `NO_STATE_PAGES` 含該 id（雙向）；`title` 為非空字串常數（固定頁名）：不含「・」、不含 `${`、`{`、`}`（不是樣板，不帶專案名等動態名稱，PRD §8.1） |
| AT-PH-03-5-2 | HL | 1a | §5.3 `PAGE_STATES` 矩陣（PRD §4 十六頁各頁的狀態表 id 與名稱模式）；已寫頁中屬於矩陣者逐頁 | 該頁 `states` 的表 id 集合與矩陣相等（`issues` 為 `{ legend: "issues" }` 一群）；每個表群的名稱模式（`label` 預設／`raw`）與矩陣相等；`execute` 不含 `stepStatus`；`monitor` 的 `stepStatus` 為 `label`、`task-detail` 的為 `raw`；矩陣外的頁（姊妹案）不受此鎖 |
| AT-PH-03-5-E-1 | HL | 1a | 純函式 `pageShapeProblems(page, noStatePages)` 餵合成頁 | `purpose` 合計 4 句（4 項各 1 句，或 1 項含 4 句）、`purpose` 空、`steps` 1 項、`steps` 9 項、`fields` 空、`sourceFiles` 含不存在路徑、`states` 空而不在 `NO_STATE_PAGES`、在 `NO_STATE_PAGES` 卻有 `states` 八種各回非空；邊界合規頁（`purpose` 1 項 1 句、`purpose` 1 項含 3 句、`steps` 2 項、`steps` 8 項）回空 |
| AT-PH-03-6-1 | HR | 1a | `PENDING_CEILING`（檔頂常數，附輪次註解）與 `PENDING_HELP_PAGES` | `PENDING_HELP_PAGES.length <= PENDING_CEILING`；`PENDING_HELP_PAGES` 無重複且全部屬於頁檔 id 集合；`HELP_PAGES` 與 `PENDING_HELP_PAGES` 互斥；`PENDING_CEILING` 為非負整數 |
| AT-PH-03-6-2 | HR | 1a | 依 D-PH-2 在輪次間的行為 | pending 頁的 id 仍出現在 `HELP_ROUTES` 的值中（路由鎖在所有輪次成立）；`HELP_PAGES` 不含 pending id；內容類測試（`content.test.ts`、`PageHelpDialog.test.tsx`）的語料來源只取 `HELP_PAGES`（pending 豁免，且豁免是明列的：測試檔印出被豁免的 id 清單，不是靜默略過） |
| AT-PH-03-6-3 | GT | 3 | 輪 3 出口閘 G-F8：`Select-String` 查 `lib/help/registry.test.ts` 的 `PENDING_CEILING` 定義，並跑 `npx vitest run lib/help/registry.test.ts -t "AT_PH_03_6_1"` | 輪 3 起：`PENDING_CEILING` 為 0（AT-PH-03-6-1 因而斷言 `PENDING_HELP_PAGES.length` 為 0，即清空）；輪 1a、1b、2 此閘不要求，但天花板逐棒不得高於前一棒（審查者以 `git log -p` 逐輪核對只降不升；姊妹案重填除外並須同 commit 說明 WHY） |

#### FR-PH-04 的 AT　狀態詞不自持；鍵集合雙向鎖

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-04-1-1 | HK | 1a | §5.3 `UPSTREAM`（表 id→上游常數的鍵取法，**測試內獨立直接 import 既有常數**，不經 `STATE_SOURCES`）；對除 `sddFsmState` 外每張表 | `STATE_SOURCES[id].keys` 的集合＝`UPSTREAM[id].keys()` 的集合；`Object.keys(STATE_HELP[id])` 的集合＝同一集合（雙向相等：常數新增狀態而說明沒補、說明多出不存在的狀態都紅）；防反空轉：檢查的表數 ≥ 17 |
| AT-PH-04-1-2 | HK | 1a | `sddFsmState`：五個鍵 `HUMAN_PENDING`、`SPEC_FROZEN`、`ESCALATION`、`ESCALATION_FINAL`、`AUTOCLAUDE_DELEGATED`；掃 `lib/domain/sdd.ts` 與 `components/domain/sdd/**` 的非測試檔，取字串字面值、樣板字串片段與 JSX 文字（不含註解） | `Object.keys(STATE_HELP.sddFsmState)` 的集合＝這五個鍵；每個鍵都以**子字串**出現在上述某處（`SPEC_FROZEN` 只在句中出現也算，不用等號）；`STATE_SOURCES.sddFsmState.labelOf` 缺席（只准 `raw`）；掃描檔數 ≥ 2（防反空轉） |
| AT-PH-04-1-3 | HK | 1a | 表登記總覽 | `Object.keys(STATE_HELP)` 的集合＝`Object.keys(STATE_SOURCES)` 的集合 ⊇ §5.3 `REQUIRED_TABLE_IDS`（18 個必備）；每張表至少一列、每列 `meaning`、`next` 為非空字串；每個 `STATE_SOURCES[id]` 的 `title` 為非空字串、`keys` 為非空陣列 |
| AT-PH-04-1-E-1 | HK | 1a | 純函式 `keyProblems(upstreamKeys, helpKeys)` 餵合成輸入 | 說明缺一鍵回「說明缺：<鍵>」、說明多一鍵回「說明多出：<鍵>」、兩者並存各一筆；相等回空；順序不同不算差異 |
| AT-PH-04-1-E-2 | HK | 1a | 弱鎖掃描器 `weakLockProblems(keys, sources)` 的負控（合成原始碼） | 鍵只出現在註解中→回該鍵；鍵完全不出現→回該鍵；鍵為某字串字面值的子字串（例 `"核准後 FSM 進入 SPEC_FROZEN，…"`）→不回；鍵出現在樣板字串片段或 JSX 文字→不回；五個鍵俱在→回空 |
| AT-PH-04-2-1 | HK＋TC | 1a | `expectTypeOf<StateRow>().toEqualTypeOf<{ meaning: string; next: string }>()`；兩行 `// @ts-expect-error 多餘欄位 label`、`// @ts-expect-error 多餘欄位 name`（**說明文字必填**：`@typescript-eslint/ban-ts-comment` 為 error，要 ≥ 3 字說明，G-F4 判，§5.8）分別接 `const a: StateRow = { meaning: "x", next: "y", label: "z" }`、`const b: StateRow = { meaning: "x", next: "y", name: "z" }`；以 `npx tsc --noEmit` 判定 | tsc rc 0；若 `StateRow` 被加了 `label` 或 `name` 欄，兩個 `@ts-expect-error` 之一會變成「未使用的指令」而使 tsc 紅（型別真的擋）；vitest 側 `-t "AT_PH_04_2_1"` 收集 ≥ 1 個且通過 |
| AT-PH-04-2-2 | HK＋TC | 1a | 十張表→enum 對照：`projectStatus`→`ProjectStatus`、`goalStatus`→`GoalStatus`、`taskStatus`→`TaskStatus`、`importStatus`→`ImportStatus`、`runStatus`→`RunStatus`、`reviewKind`→`ReviewKind`、`reviewDecision`→`ReviewDecision`、`stepStatus`→`ExecutionStepStatus`、`alertRule`→`AlertRule`、`gateName`→`GateName`（型別取自 `@/lib/api/types`）；對每張 `expectTypeOf<keyof typeof STATE_HELP.<表>>().toEqualTypeOf<該 enum>()` | tsc rc 0；執行期側：十張表的 `Object.keys(STATE_HELP[表])` 皆非空；enum 經 `schema*.d.ts` 重產而新增值時，這十行即編譯紅（第一道鎖，04-1 為第二道） |
| AT-PH-04-2-3 | HK＋TC | 1a | `expectTypeOf<keyof typeof STATE_HELP.serviceState>().toEqualTypeOf<ServiceState>()`（`ServiceState` 取自 `@/hooks/useServiceStatus`，type import） | tsc rc 0；`lib/help/**` 沒有 import `hooks/**`（掃描：`lib/help/**` 非測試檔的模組位址不含 `@/hooks/`、`@/components/`） |
| AT-PH-04-2-E-1 | HK＋TC | 1a | 合成：`type Widened = keyof (Record<ProjectStatus, 0> & { HOLD: 0 })`（＝`ProjectStatus` 加字面值 `"HOLD"`）；`// @ts-expect-error 缺 HOLD`：`const t: Record<Widened, StateRow> = STATE_HELP.projectStatus`；另一行 `// @ts-expect-error 少一鍵` 把 `STATE_HELP.taskStatus` 指派給少一鍵的型別（兩個指令都帶說明文字） | tsc rc 0（證明「enum 多一值」與「表少一鍵」型別都真的紅；若 `projectStatus` 被放寬成 `Record<string, StateRow>`，第一個指令變成未使用而 tsc 紅） |
| AT-PH-04-3-1 | HK | 1a | §5.3 `UPSTREAM`（表 id→上游標籤取法）；對每張有 `labelOf` 的表的每個鍵 | `STATE_SOURCES[id].labelOf(key)`＝上游常數同鍵的標籤（`PROJECT_STATUS.DRAFT.label`、`REVIEW_DECISION_LABEL.APPROVE`、`SERVICE_LABEL.online`、`GATE_LABEL.cycle`、`SDD_PHASE_LABEL.INTAKE`、`OBS_STATUS_OPTIONS` 去「全部」後 `open`→「未結」等）；每個標籤為非空字串；`sddFsmState`、`propState` 無 `labelOf` |
| AT-PH-04-3-2 | HD | 1b | PD 合成頁：`projectStatus`（label 模式）、`stepStatus`（`raw`）、`propState`（`raw`）各一群 | 「狀態」欄逐列：label 表＝`labelOf(key)`；`raw` 表＝鍵本身（例 `STARTED`）；`raw` 表欄標題「畫面上的原值」、label 表欄標題「狀態」；同一個 `stepStatus` 以 label 模式再渲染一次時首欄變成中文標籤（兩種模式同表可並存） |
| AT-PH-04-3-3 | HK | 1a | 對 `Object.values(HELP_PAGES)` 每個頁的每個 `{ table, name }` 群 | 無 `labelOf` 的表（`sddFsmState`、`propState`）只准 `name: "raw"`；`name` 缺省＝label 模式；`name` 值只能是 `"label"`、`"raw"`；`{ legend: "issues" }` 只出現在 `issues` 頁；每個 `table` 都在 `STATE_SOURCES` 內 |
| AT-PH-04-3-E-1 | HK | 1a | 純函式 `nameModeProblems(group, source)` 負控 | `{ table: "propState" }`（缺省 label，但無 `labelOf`）回非空；`{ table: "propState", name: "raw" }` 回空；`{ table: "projectStatus", name: "raw" }` 回空（有 `labelOf` 的表可選 raw）；`name: "foo"` 回非空；表 id 不在來源表回非空 |
| AT-PH-04-4-1 | HD | 1b | PD 渲染 `issues` 頁；fetch 替身回黃金檔 `LEGEND`（`components/domain/issues/tests/issues.fixtures.ts` 的 `LEGEND`，取自 `tests/fixtures/si/A.camel.json`）；APP_QC | 恰一個請求 `GET /api/v1/issues`，查詢串恰 `limit=1`；對話框內 `page-help-legend-statuses`／`results`／`sources`／`severities` 四群：`dt`、`dd` 依序逐字＝`LEGEND` 對應陣列的 `name`、`meaning`；`page-help-legend-note` 文字＝`LEGEND.updatedAtNote`；四個群標題（`h4`）依序「狀態」「結果」「來源」「嚴重度」；狀態段沒有 `table` |
| AT-PH-04-4-2 | HD | 1b | 同上，但 `LEGEND` 每個 `meaning` 換成哨兵、`updatedAtNote` 缺席（鍵不在）；另一輪 `updatedAtNote` 為空字串 | 對話框詞表群只顯示哨兵（沒有第二份說明文字：扣掉哨兵、群標題、名稱後狀態段為空）；兩種缺席下 `page-help-legend-note` 都不存在，且文字不含「最後已知動靜」（不寫死） |
| AT-PH-04-4-3 | HS | 1b | 現讀黃金檔 `tests/fixtures/si/A.camel.json` 的 `issues.legend.statuses[].name`（七個：候選、待您決定、待解、進行中、觀察中、延後、已完成）；**只掃** `lib/help/issues.ts` 與 `components/domain/help/**` 的非測試檔，含註解、子字串比對（語意同 `issues.static.test.ts:88-92`） | 每個被掃檔含不到 4 個**不同**的議題狀態名（同一個詞重複幾次只算一個）；防反空轉：被掃檔含 `lib/help/issues.ts`、`PageHelpDialog.tsx`、`IssuesLegendGroups.tsx`；**不掃** `lib/help/states.ts` 與其他頁檔（「進行中」「已完成」「延後」是一般詞，會誤紅）；詞表現讀黃金檔、不另抄，且恰 7 個 |
| AT-PH-04-4-E-1 | HS | 1b | 掃描器 `stateKeyViolations(file, source, words)` 負控；tmp 目錄依 repo 形狀擺三個內容相同（含七個狀態詞）的檔：`lib/help/states.ts`、`lib/help/issues.statusWords.sample.ts`、`components/domain/help/X.sample.ts` | 含 4 個不同詞者回非空、含 3 個者回空、同一詞重複 4 次者回空；範圍規則：`states.ts` 不被掃進、`issues.*` 與 `components/domain/help/**` 的樣本被掃進；預跑結果見 §5.8（自擬 `issues` 說明草稿含 2 個狀態名） |
| AT-PH-04-5-1 | HD | 1b | PD 渲染 `issues` 頁，APP_QC；fetch 替身對詞表回 503：`{ reason: "si_unavailable", details: { cause: "nonzero_rc", detail: "rc=2; stderr=boom 全形字元" } }` | 「這頁做什麼」「怎麼用」「欄位說明」三段照常（內容＝`issues` 頁登記）；狀態段含「狀態詞表暫時取不到：」並逐字含 `si_unavailable`、`nonzero_rc`、`rc=2; stderr=boom 全形字元`（取 `siErrorParts`）；`page-help-legend-error` 存在、`role="alert"`；沒有任何詞表群、沒有 `table`、沒有「載入中」句；無 `dd` 殘留 |
| AT-PH-04-5-2 | HD | 1b | 三種失敗各渲染一次：(a) 504；(b) fetch 以 `TypeError("Failed to fetch")` 拒絕（網路失敗）；(c) `200` 但 `data` 沒有 `legend`（或 `statuses` 缺） | 三者皆顯示「狀態詞表暫時取不到：」且冒號後非空（(b) 取 `describeError`；(c) 為「回應沒有詞表」，D-PH-8）；前三段照常；不顯示空表與詞表群 |
| AT-PH-04-5-3 | HD | 1b | 詞表請求以可控 Promise 擋住 | 擋住期間：「狀態詞表載入中…」存在（`page-help-legend-loading`、`role="status"`），前三段已顯示，沒有詞表群、沒有空表；放行後：載入句消失、四群出現 |
| AT-PH-04-5-4 | HD | 1b | APP_QC（`staleTime: 5_000`）；開啟（回 `LEGEND` 甲）→關閉→改 fetch 替身回哨兵版 `LEGEND` 乙→再開啟 | 共 2 個詞表請求（每次開啟都重取，不被 5 秒 `staleTime` 擋掉）；第二次開啟先顯示載入句（不先顯示甲的過期資料），之後顯示乙；全程不出現甲的任何 `meaning` 與乙並存 |
| AT-PH-04-5-E-1 | HD | 1b | APP_QC（`renderIssues` 的真 `Providers`：對 5xx 重試一次、`staleTime: 5_000`）；`stub.overrides.list` 回 `unavailable()`（503）；開啟一次並等待錯誤句出現 | 詞表請求恰 1 個（失敗不重試：沿 `SI_QUERY_OPTIONS` 的 `retry: false`；若漏掉此選項，app 預設會重試一次而得 2 個請求）；再等 1,500 毫秒（React Query 預設重試延遲 1,000 毫秒）仍為 1 個 |
| AT-PH-04-5-E-2 | HD | 1b | 開啟 `issues` 說明並取得詞表後，取該測試 `Providers` 內的 `QueryClient` 的 `getQueryCache()`（`renderIssues` 不回傳 client：測試內自帶探針子元件，與被測元件同樹渲染，於 `useEffect` 內把 `useQueryClient()` 的值存到測試作用域物件；不在 render 階段寫外部變數，免觸 `react-hooks/globals`） | 有 query key 為 `["help","issuesLegend"]` 的查詢；沒有任何以 `["issues"]` 起頭的查詢（不污染議題中心的快取家族）；關閉對話框後該查詢被回收（`gcTime: 0`，不留快取；以 `waitFor` 等待回收） |
| AT-PH-04-5-E-3 | HS | 1b | 掃 `components/domain/help/IssuesLegendGroups.tsx` 的 import 與字面值 | 自 `@/lib/api/endpoints` import `getIssues`、自 `@/lib/api/queries` import `SI_QUERY_OPTIONS`；**不** import `useIssues`、`useIssue`、`useIssueLookups`、`qk`；字面值含 `"help"` 與 `"issuesLegend"`；負控：import `useIssues` 者、query key 為 `["issues", …]` 者各回非空 |
| AT-PH-04-6-1 | HK | 1a | `PROP_STATE_KEYS`（`lib/domain/si.ts` 新匯出）、`propStatusClass`、`OBS_STATUS_OPTIONS`、`PROPOSAL_STATUS_OPTIONS` | `PROP_STATE_KEYS` 每個鍵 `propStatusClass(key) !== "unknown"`；⊇ 根層十個提案狀態（`proposed、approved、rejected、returned、handed-off、sandboxed、verified、promoted、measuring、closed`，抄自 `si.test.ts:395`）且含 `retired`；`STATE_SOURCES.propState.keys` 與 `Object.keys(STATE_HELP.propState)` 皆等於 `PROP_STATE_KEYS`；`obsClass`、`propClass` 的 `keys` 各＝其 OPTIONS 去掉 `id === ""` 的 `id`，`labelOf(id)`＝該 OPTIONS 的 `label` |
| AT-PH-04-6-2 | HD | 3 | PD 渲染 `self-improving` 頁（輪 3 才寫；輪 1a～2 該頁在 `PENDING_HELP_PAGES`，本 AT 先斷言「它在 pending 內」） | 三張表依 PAGE_STATES：`obsClass` 首欄＝「未結」「延後」「已完成」、`propClass` 首欄＝「待決」「進行中」「已完成」、`propState` 首欄＝`PROP_STATE_KEYS` 原值（例 `proposed`、`handed-off`）且欄標題「畫面上的原值」；`propState` 的列鍵集合＝`PROP_STATE_KEYS` |
| AT-PH-04-6-3 | HK | 1a | `STATE_HELP.propState.retired.meaning` | 含逐字「根層目前不會產生這個狀態，畫面為日後預留」（PRD D-8、§8.2 備註 4） |
| AT-PH-04-7-1 | HK | 1a | 對 `Object.keys(REVIEW_DECISION_LABEL)` 每個決定，對 `Object.keys(REVIEW_KIND)` 每個種類呼叫 `reviewConsequence`（`components/domain/execute/reviewHelp.ts:28`） | 每個決定至少在一個種類回傳非預設句（預設句＝「依後端規則處理。」，`:29`）；`Object.keys(STATE_HELP.reviewDecision)` 的集合＝`Object.keys(REVIEW_DECISION_LABEL)`；決定新增而後果表沒補＝紅 |
| AT-PH-04-7-2 | HK | 1a | 收集全部「種類×決定」的非預設後果句；檢視 `STATE_HELP.reviewDecision` 的每列 | 每列 `next` 含「依審核項種類而定」；任一列的 `meaning`、`next` 都不含任何一句後果文字（不抄第二份，後果只住 `reviewHelp.ts`） |
| AT-PH-04-7-E-1 | HK | 1a | 純函式 `decisionCoverageProblems(decisions, kinds, consequence)` 餵合成輸入 | 決定 `FOO`（所有種類都回預設句）→回「FOO」；每個決定至少一個種類有非預設句→回空；`consequence` 對全部輸入回預設句→回全部決定 |


#### FR-PH-05 的 AT　白話與內容品質（機械可驗的部分）

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-05-1-1 | HL | 1a | 語料 `allHelpTexts()`（測試內）：已寫頁的 `purpose`／`steps`／欄位 `meaning`／`sourceNote`、`STATE_HELP` 每列 `meaning`／`next`、`HELP_COMMON.fields`、`SHARED` 的每個欄位釋義；依 D-PH-9 用 `splitSentences`、`codePointLength` | 每句 ≤ 60 code point；每頁 `purpose` 合計 ≤ 3 句；`steps` 每項恰 1 句；欄位與狀態 `meaning` ≤ 2 句；`next` 恰 1 句；`sourceNote` ≤ 1 句；防反空轉：語料中 `STATE_HELP` 列數 ≥ `REQUIRED_TABLE_IDS.length`、語料含至少一個已寫頁；pending 頁不在語料內 |
| AT-PH-05-1-E-1 | HN | 1a | `splitSentences`、`codePointLength` 邊界 | 60 個「字」的句子通過、61 個不通過；60 個 U+20BB7（代理對，UTF-16 長度 120）的句子通過（用 code point 不用 `.length`）；「甲。乙！丙？丁；戊」切成 5 句；`\r\n`、連續分隔「。。」、結尾分隔、全空白段不產生空句；「；」也是切句點（「A；B」算 2 句） |
| AT-PH-05-2-1 | HL | 1a | 同上語料，對每筆用 `unlistedEnglishWords`（欄位名欄與狀態名欄是畫面字樣的逐字引用，不在語料內） | 每筆回空陣列；失敗訊息列出頁／表、位置與非白名單詞 |
| AT-PH-05-2-2 | HN | 1a | `ENGLISH_WHITELIST` 與 `unlistedEnglishWords` | 白名單集合與 PRD §8.3 的 31 詞逐字相同（`ID、API、URL、AI、Token、Agent、PRD、BRD、SDD、FSM、AISDLC、AutoClaude、Console、Engine、Bridge、Playbook、Markdown、PDF、DOCX、CSV、JSON、SSE、DAG、Regex、CPU、ADMIN、OPERATOR、VIEWER、signoff、Run、Level`；增詞必須改本 AT，即走複審）；整詞、不分大小寫（`autoclaude`、`SIGNOFF` 通過）；連字號與底線當分隔（`console-api` 通過、`auto-claude` 回 `auto`、`claude`）；數字相接取字母段（`Level2` 通過）；單一字母不算（`第 A 步`）；ID 形態先剔除（`OBS-SI-001`、`PROP-SI-004`、執行期以 `"DEF-" + "<數字>-<數字>"` 組出的 DEF 形態字串都不回詞） |
| AT-PH-05-2-E-1 | HN | 1a | 負控 | `Foo`、`GitHub`、`Review & Approve`（回 `Review`、`Approve`）、`https`、`Users` 各回非空；「由 Foo 啟動」回 `["Foo"]` |
| AT-PH-05-3-1 | HL | 1a | 同上語料，對每筆用 `forbiddenFindings` | 每筆回空陣列（無 emoji、`#`＋≥3 位十六進位、`**`、反引號、`](`、HTML 標籤、`://`、磁碟機或家目錄路徑、≥3 位連續半形數字；ID 形態先剔除，D-PH-10） |
| AT-PH-05-3-2 | HN | 1a | `forbiddenFindings` 各類與邊界（§5.5 樣本表） | emoji（`😀`、`✅`、`↔`、`™`）回非空，`→` 與全形標點回空；`#abc123`、`#abc`、`#123` 回非空，`#12` 回空；`**粗**`、`` `x` ``、`[a](b)` 各回非空；`<b>粗</b>` 回非空；`a://b` 回非空；`C:\Users\x`、`/Users/x`、`/home/x` 各回非空；`1234`、`123` 回非空、`12` 回空；`OBS-SI-001`、`PROP-SI-004`、`DEF-` 接兩個數字組成的 ID 形態（執行期組字串）回空（先剔除）；判準取 AC-PH-05-3 的「≥ 3 位」，AC-PH-05-6 的「4 位數字」樣本是其子集（勘誤 1-4） |
| AT-PH-05-4-1 | HL＋TC | 1a | 已寫頁每個欄位列、`HELP_COMMON.fields`、`SHARED` 值 | `source` 屬六類之一（§5.4 `FIELD_SOURCES`）；`sourceNote` 缺或 ≤ 30 個 code point；型別等式 `expectTypeOf<FieldSource>().toEqualTypeOf<(typeof FIELD_SOURCES)[number]>()`（tsc 判定；六類逐字） |
| AT-PH-05-4-E-1 | HL | 1a | 純函式 `fieldProblems(field)` 負控 | `source: "手動"` 回非空；`sourceNote` 恰 30 字回空、31 字回非空；`sourceNote: undefined` 回空；六類各一個合規欄位回空 |
| AT-PH-05-5-1 | HS | 1a | 對 `Object.values(HELP_PAGES)` 逐頁與 `HELP_COMMON`：展開 `sourceFiles`（`dir/**` 與檔案；扣測試檔、`*.d.ts`、`*.fixtures.ts`、`tests/` 子目錄），以 TypeScript AST 取字串字面值、樣板字串片段與 JSX 文字（不含註解） | 每個欄位名（≥ 3 個 code point）至少被一處文字含有；同頁欄位名互異；每頁展開後 ≤ 30 個檔；每個展開檔存在；`HELP_COMMON.sourceFiles` 含 `components/layout/**` 與 `hooks/useServiceStatus.ts`；防反空轉：至少檢查 3 頁、每頁至少 1 個欄位名通過掃描 |
| AT-PH-05-5-2 | HS | 1a | 純函式 `expandSourceFiles(entries, root)` 對真目錄樹與合成輸入 | `components/**`、`lib/**`、`app/**`、`hooks/**`（單段目錄的萬用）各被拒；`components/layout/**` 通過；含 `..` 的路徑被拒；不存在的檔被拒；`components/domain/**` 在真樹展開 87 個檔（本檔作者 2026-10-27 實測）> 30 而被拒（上限 30＝PRD 值；實測單一目錄最大 `components/domain/execute/**` 12 個，見 §5.8）；`.test.tsx`、`*.d.ts`、`*.fixtures.ts`、`tests/` 下的檔不被展開進去 |
| AT-PH-05-5-3 | HS | 1a | 文字抽取器 `collectTexts(source)` 的負控（合成 TSX） | 名稱只出現在 `//`、`/* */` 註解→找不到；出現在字串字面值（含 JSX 屬性值）、樣板字串片段、JSX 文字→找得到；出現在 `import` 位址→不算；名稱被拆在兩個字面值之間→找不到 |
| AT-PH-05-5-E-1 | HS | 1a | 模擬「改名」：合成 `sourceFiles` 內容裡把某欄位名所在字面值改名後重跑檢查函式 `sourceLockProblems(page, texts)` | 改名後回「欄位『X』在 sourceFiles 找不到」；同頁重複欄位名回非空；名稱 2 個 code point 者免掃（回空）；名稱剛好 3 個 code point 者要掃 |
| AT-PH-05-6-1 | HN | 1a | PRD AC-PH-05-6 的負控樣本逐一餵 `lintText` | 61 字的句子、白名單外英文詞（`Foo`）、emoji、`#abc123`、Markdown 記號（`**`、反引號、`](`）、`://`、4 位數字、3 位數字各回非空，2 位數字回空（勘誤 1-4，與 AT-PH-05-3-2 同界線）；每個樣本至少回一筆含對應類別關鍵字的訊息（句長→「句長」、英文詞→「英文」、其餘→「字元」；`#abc123` 會同時觸發英文與字元，不要求單一類） |
| AT-PH-05-6-E-1 | HN | 1a | 合規樣本與選項 | 合規樣本（含白名單英文、ID 形態、全形標點、`Level 3`、`OBS-SI-001`）回空；恰 60 字句子回空；`lintText(text, { maxSentences: 2 })` 對 3 句回非空、對 2 句回空；空字串回空 |
| AT-PH-05-7-1 | HS | 2 | 掃 `components/domain/entity/EntityForms.tsx`：`ProjectForm`、`GoalForm`（含 `DependsOnField`）、`TaskForm` 三個函式體內 `<Field>`、`<MarkdownField>` 的 `label` 字串屬性；三個表單頁 `project-form`、`goal-form`、`task-form`（輪 2 才寫；輪 1 該三頁在 pending 內，本 AT 先斷言它們在 pending 且抽取結果非空） | 對已寫的表單頁：其 `fields` 的名稱集合 ⊇ 對應函式抽出的 `label` 集合（撰寫時 5／4／6 個：`ProjectForm`＝專案名稱、執行路徑、說明描述、通過標準、自治等級；`GoalForm`＝目標名稱、說明描述、通過標準、前置依賴；`TaskForm`＝任務名稱、說明描述、通過標準、最大重試次數、驗證命令、期望輸出 Regex）；表單新增欄位而說明沒補＝紅 |
| AT-PH-05-7-2 | HS | 1a | 抽取器 `formLabels(source, fnNames)` 的負控（合成 TSX）與對真檔的防反空轉 | 抽到 `<Field label="X">` 與 `<MarkdownField … label="Y" />`；`label={x}`（運算式）不抽；只抽指定函式體內的元素（其他函式內的 `<Field>` 不算）；`GoalForm` 內呼叫的 `DependsOnField` 其標籤計入 `GoalForm`；對真檔 `EntityForms.tsx`：三組結果各 ⊇ §5.4 `FORM_LABELS` 的快照清單（新增欄位不影響此斷言） |

#### FR-PH-06 的 AT　零侵入與單一真相

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-06-1-1 | GT | 1a | G-C1：`<base>`＝輪開工 HEAD；本功能 commit 範圍的 `git diff --name-only`（含未追蹤檔以 `git status --porcelain -uall` 與開工快照相減）；共用分支上姊妹案的 commit 夾在中間者，以本功能自己的 commit 範圍判定（由主控在任務書寫明） | 每個路徑 ⊆ §5.7 允許集合；與禁改集合（`AgentConsole/backend/**`、`AgentConsole/engine-bridge/**`、`lib/api/endpoints.ts`、`queries.ts`、`reasons.ts`、`schema*.d.ts`、`openapi-p3-6.yaml`、`API_Contract_*.md`、`lib/nav/registry.ts`、`.github/**`、`tools/**`、`.claude/**`、既有 `*.test.ts(x)`／`*.spec.ts`，唯 `si.static.test.ts` 除外，D-PH-18）交集為空；`Architecture.md` 只在主控發布階段的 commit 出現 |
| AT-PH-06-1-E-1 | GT | 1a | G-C1 的篩選函式（SCG-4 通過標準內的 PowerShell 片段）餵合成路徑清單 | `AgentConsole/backend/x.java`、`AgentConsole/frontend/lib/api/endpoints.ts`、`AgentConsole/frontend/lib/nav/registry.ts`、`.github/workflows/x.yml`、`tools/x.py`、`.claude/x`、`AgentConsole/docs/02_architecture/Architecture.md`（開發棒階段）、既有 `components/layout/layout.test.tsx` 逐一被判違規；§5.7 內的每個路徑被判允許 |
| AT-PH-06-2-1 | GT | 1a | G-F1：`npx vitest run`（全套） | rc 0；測試檔數與測試數不少於基線（HEAD：88 個檔、1509 個測試）加本功能新增者；任一既有檔的測試數不減 |
| AT-PH-06-2-2 | GT | 1b | G-F2：PRD §9 真跑清單三檔逐檔各跑一次：`npx vitest run components/layout/layout.test.tsx`、`components/layout/si-login-gate.test.tsx`、`components/domain/views/DashboardView.test.tsx`，輸出逐檔貼證據檔 | 逐檔 rc 0；三檔合跑的基線（HEAD `000a217b`，本檔作者實測）為 3 個檔、32 個測試皆通過，完成後不少於此；`layout.test.tsx:71-74`（`components/layout` 恰四個元件檔）、`:263-272`（`/login` 無動作）仍成立 |
| AT-PH-06-2-E-1 | GT | 1a | G-C2：`git diff -U0 <base> --` 既有 `*.test.ts(x)` 與 `tests/e2e/*.spec.ts` | 空，**唯一例外** `components/domain/si/si.static.test.ts`（D-PH-18）：其 diff 只准出現在 `bridgeLeaks` 的 `checkText` 第二分支與新增的 `AT_PH_06_2_3`、`AT_PH_06_2_E_2` 兩個 `it`，逐 hunk 核對、不刪既有斷言（PRD §9「需同步改的既有鎖」其餘逐檔核對皆為「不受影響／不動」） |
| AT-PH-06-2-3 | HX | 1a | 既有檔 `components/domain/si/si.static.test.ts`（本案唯一准改的既有測試，D-PH-18）新增 `it("AT_PH_06_2_3 …")`：對純函式 `bridgeLeaks` 餵相對檔案路徑形字面——`export const sourceFiles = ["components/domain/si/**", "components/domain/si/SiView.tsx", "lib/domain/si.ts"];`；並整檔重跑 | 該樣本回空（`/si/` 出現在相對檔案路徑中不是 Bridge 路徑字面）；整檔 rc 0（既有 AT_932_4_3 的真樹掃描與原負控原樣通過；輪 3 `lib/help/self-improving.ts` 的 `sourceFiles` 含 `components/domain/si/**` 後仍綠） |
| AT-PH-06-2-E-2 | HX | 1a | 同檔新增 `it("AT_PH_06_2_E_2 …")`：URL 形樣本逐一餵 `bridgeLeaks` | 既有負控保留：``const u = "/si/status";``、``const u = `/si/runs?limit=${n}`;``、``const u = `${base}/si/x`;`` 回非空；**只靠第二分支才紅**：``const u = "https://x.example/si/status";``、``const u = "/v1/si/x";``、``const u = `${base}/v1/si/x`;``；**只有 (ii)「樣板片段一律視為 URL 形」才紅**：``const u = `http://${h}:9000/si/x`;``、``const u = `${base}api/si/x`;``，以上皆回非空；``const u = "/api/v1/si/status";`` 與模組位址 ``import { SiView } from "@/components/domain/si/SiView";`` 回空 |
| AT-PH-06-3-1 | E2 | 1b | spec 內自帶 mock：`compose(shellHandler(), 議題詞表處理器, 404 後備)`；OPERATOR；`Object.keys(HELP_ROUTES)` 每個樣板代入 `p1`／`g1`／`t1` 為網址；每條路由載入、等 `page-help-open` 可見後**固定再等 1,000 毫秒**（不用 `networkidle`：實測 2026-10-27 於 404 後備 mock 下 19 條路由有 18 條在 30 秒內到不了網路靜止，§5.8）記下 `calls`，按「本頁說明」，等對話框出現再等 500 毫秒；請求計數依 D-PH-13 的新穎性規則；測試內**明寫 `test.setTimeout(180_000)`**（19 條路由各約數秒，遠超 Playwright 預設 30 秒；先例 `issues.mock.spec.ts:121`） | 逐路由：pending 頁的路由無鈕（與 AT-PH-01-2-E-1 一致）；已寫頁的路由：議題中心（`/issues`）恰一個新增請求 `GET /api/v1/issues`（查詢串恰 `limit=1`），其餘每條路由新增請求為 0 個；對話框名稱＝「`<title>`・本頁說明」（`title` 取自登記表）；點擊到對話框出現期間無 `pageerror` |
| AT-PH-06-3-2 | E2 | 1b | `/issues`，VIEWER；開啟→Esc 關閉→開啟→關閉→開啟（三次開啟） | 詞表請求共 3 個（每次開啟各一個，查詢串皆恰 `limit=1`）；VIEWER 的詞表請求不被前端擋；每次開啟後四群詞表皆出現 |
| AT-PH-06-3-E-1 | E2 | 1b | 上兩個 AT 全程累積的**新增請求**（D-PH-13：點擊後才出現的新鍵；不含頁面載入時自己發的請求，例如 `/self-improving` 頁載入時本來就會 GET `/api/v1/si/*`） | 新增請求中沒有任何非 GET（POST、PUT、DELETE）；沒有路徑含 `/si/` 者（說明不碰自我進化端點）；除議題詞表請求外沒有其他新增請求 |
| AT-PH-06-4-1 | GT | 1b | G-F5：Stage-2 凍結 commit（`<base>`，**輪 1a 開工前**）與各棒出口各 `npm run build` 一次（`Push-Location AgentConsole\frontend`；每次 build 後把 `.next\diagnostics\route-bundle-stats.json` 複製到各自的暫存檔），以 SCG-4 通過標準的 `Compare-RouteBundle` 逐路由比對 `firstLoadUncompressedJsBytes` | 每條路由（含 `/login` 與 `/_not-found`；HEAD 的檔案有 21 列）增量 ≤ 100,000 位元組；兩份檔的路由集合相同（多一條或少一條路由＝紅；姊妹案的 `/sysadmin` 等路由若在兩次 build 之間落地，基線須在「含姊妹案、不含本功能」的樹上重取）；**自輪 1b 出口起每個出口（1b、2、3）都是閘**（D-PH-17 已採 `next/dynamic`；若仍超過，再把 `PageHelpDialog`、`states.ts`、頁檔、`stateSources.ts` 一律改成按下鈕才 `import()`，PRD AC-PH-06-4） |
| AT-PH-06-4-E-1 | GT | 1b | 比較腳本自證（合成 JSON 兩份） | 增量恰 100,000 通過、100,001 紅；缺一條路由紅；多一條路由紅；欄位缺 `firstLoadUncompressedJsBytes` 紅；兩份完全相同回 rc 0 |

#### FR-PH-07 的 AT　無障礙與響應式

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-07-1-1 | HB | 1b | RL（`/projects`）；`userEvent.setup()`；`button.focus()` 後 `keyboard("{Enter}")` | 對話框開啟；`document.activeElement` 在 `dialog` 之內；`keyboard("{Escape}")` 後對話框關閉且 `document.activeElement` 為 `page-help-open`；以滑鼠點開（`userEvent.click`）再按 Esc 同樣焦點回到該鈕 |
| AT-PH-07-1-2 | E2 | 1b | 真瀏覽器（mock）：`/projects`（或首個已寫頁）；Tab 逐次前進（沿 `issues.mock.spec.ts` 的 `tabUntil` 寫法，上限 80 次）直到焦點在 `page-help-open` | Enter 開啟後焦點進入對話框；Esc 關閉後焦點回到該鈕（`toBeFocused()`）；再以空白鍵開、右上「關閉」鈕關，焦點同樣回到該鈕；`:focus-visible` 焦點環可見（鈕的 `outline-style` 非 none） |
| AT-PH-07-1-E-1 | HB | 1b | RL；以空白鍵（`keyboard(" ")`）開啟；以 `getByRole("button", { name: "關閉" })` 點關閉 | 空白鍵可開；關閉鈕可關；兩種關法焦點都回到 `page-help-open`；連開連關三次後仍恰一個對話框、鈕仍恰一個（無重複掛載） |
| AT-PH-07-2-1 | HS | 1b | 掃 `components/domain/help/PageHelpDialog.tsx` 原始碼（AST） | 自 `@/components/ui/dialog` import `DialogContent`（含 `Dialog` 或 `DialogBody` 之一）並以 `<DialogContent` 渲染；**不含** `onCloseAutoFocus`、`preventDefault`；不直接 import `radix-ui` 或 `@radix-ui/*`；不含字面 `role="dialog"`；不傳 `className` 去覆寫 `max-h-`、`max-w-`、`overflow-` 類 |
| AT-PH-07-2-2 | HD | 1b | PD 渲染任一已寫頁，取 `role=dialog` 元素 | `className` 含 `max-h-[88vh]`、`max-w-[calc(100%-48px)]`、`overflow-y-auto`（沿用 `components/ui/dialog.tsx:60`）；`data-testid="page-help-dialog"` 在該元素上；內容超高時可捲（`overflow-y-auto` 在對話框根元素） |
| AT-PH-07-2-E-1 | HS | 1b | 掃描器負控（合成原始碼） | 含 `onCloseAutoFocus={(e) => e.preventDefault()}`、自刻 `<div role="dialog">`、`import { Dialog } from "radix-ui"` 者各回非空；只用 `DialogContent` 者回空 |
| AT-PH-07-3-1 | E2 | 1b | 視窗 390×844；`/issues` 與 `/projects` 兩個已寫頁（再加 `/settings`）；mock 同 06-3；`signInAs(OPERATOR)` | 鈕可見可點（`click()` 通過可操作性檢查，不被覆蓋）；開啟後對話框 `boundingBox` 完全在視窗內（`x ≥ 0`、`x + width ≤ 390`、`y ≥ 0`、`y + height ≤ 844`）；對話框根元素與 `documentElement` 皆 `scrollWidth ≤ clientWidth`；展開「全站共通」後仍成立 |
| AT-PH-07-3-2 | E2 | 1b | 視窗 390×844 與 768×900、767×900 | 390 時頂列（`[data-region="top"]`）與 `documentElement` 無橫向捲動（`scrollWidth ≤ clientWidth`；R-4）；767 時鈕的可見文字節點不可見（`sr-only` 剪裁，`boundingBox` 寬高 ≤ 1 或被剪裁）、鈕本身可見；768 時文字節點可見（寬 > 1）；兩種寬度下 `getByRole("button", { name: "本頁說明" })` 皆找得到 |
| AT-PH-07-3-E-1 | E2 | 1b | `/projects`（有欄位表與狀態表）；對話框內**兩張表**（欄位表、第一張狀態表）各取第一個資料列（至少 3 格）；視窗 1440×900 與 390×844 各量一次 | 1440：兩張表的三格 `boundingBox().y` 差 < 2（並排）；390：三格 `y` 嚴格遞增、`x` 相同（逐列堆疊、同左緣）；390 時每格可見「欄名」小標（`data-label` 屬性值＝該欄標題，且以 `getComputedStyle(cell, "::before").content` 或可見子節點呈現其中之一） |
| AT-PH-07-4-1 | E2 | 1b | `/issues`、`/projects/p1`、`/settings` × 視窗 1440×900 與 390×844（`/projects/p1` 於輪 2 起納入；pending 的路由跳過並斷言其無鈕）；**關閉態**，用既有 `expectNoA11yViolations(page, 標籤)`（`tests/e2e/a11y.ts:94-97`） | 零違規（含 `color-contrast`、`label-content-name-mismatch`：新鈕與其圖示、主色底上的對比） |
| AT-PH-07-4-2 | E2 | 1b | 同上六種組合，**開啟態**（對話框顯示、「全站共通」收合） | 零違規 |
| AT-PH-07-4-3 | E2 | 1b | 同上六種組合，開啟並**展開「全站共通」**後 | 零違規（收合內容在展開前不被 axe 掃到，所以另掃一次） |
| AT-PH-07-5-1 | HS | 1b | 掃 `components/domain/help/PageHelpButton.tsx` | 自 `lucide-react` import `BookOpen`、**不** import `CircleHelp`；`className` 字面值含 `bg-white`、`text-wg-primary`、`font-medium`、`rounded-full`，且不含 `outline-none`／`outline-hidden`、且**不同時**含 `bg-white/` 接數字或方括號的半透明底與 `text-white`（半透明底白字約 3.5:1，PRD §7；判的是同一個 `className` 字面值內的組合，單獨出現的 `text-white`，例如 hover 態換深色底，不算）；執行期：`import { BookOpen } from "lucide-react"` 取得非 undefined（安裝版 1.57.0，`lucide-react.d.ts:2772`） |
| AT-PH-07-5-2 | GT | 1a | G-F6：既有 `tests/design-rules.test.ts` 真跑（`npx vitest run tests/design-rules.test.ts`） | rc 0（新檔 `lib/help/**`、`components/domain/help/**` 的說明文字無 emoji 與色碼、只用 token、Lucide、無陰影漸層、無 `outline-none`；`TopRegion.tsx:124` 的 `focus-visible:outline-offset-[-2px]` 保留，`design-rules.test.ts:68-69` 仍成立） |
| AT-PH-07-5-E-1 | HS | 1b | 掃描器負控（合成原始碼） | import `CircleHelp` 者、`className="bg-white/[0.14] text-white"` 者、含 `outline-none` 者各回非空；`BookOpen`＋`bg-white text-wg-primary` 者回空；`className="bg-white text-wg-primary hover:bg-wg-primary hover:text-white"`（單獨出現的 `text-white`）回空 |

#### FR-PH-08 的 AT　接入規範

| AT | 載具 | 輪 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-PH-08-1-1 | HR | 1a | 把真 `app/` 樹複製到 tmp 目錄（`fs.cpSync`），再加 `app/zzz/page.tsx`；對複本跑 AT-PH-03-1 的 `routeProblems`（不動工作樹） | 回非空，訊息含「/zzz」與逐字「在 `lib/help/<id>.ts` 新增並於 `registry.ts` 登記」；對未加檔的複本回空（對照組，證明紅是新頁造成的） |
| AT-PH-08-1-E-1 | HR | 1a | 同一複本，改為從 `HELP_ROUTES` 鍵集合拿掉一個鍵（合成輸入） | 回非空並指出缺的路由；不影響其他路由的判定 |
| AT-PH-08-2-1 | HR | 1a | 純函式 `navProblems` 餵「真 `NAV_REGISTRY` 加一項 `enabled: true`、`href: "/login"`」的合成登記表 | 回非空並含該項 `id`；真登記表回空（對照組） |
| AT-PH-08-2-E-1 | HR | 1a | 合成登記表：新項 `enabled: false`；新項 `href` 為函式且兩種解析都有說明 | 兩者皆回空（停用項豁免；函式型 `href` 兩種解析都經 `helpForPath`） |
| AT-PH-08-3-1 | GT | 3 | G-D1（主控發布階段）：讀 `AgentConsole/docs/02_architecture/Architecture.md` | §5.4 檢查表含「說明登記表一列」一格；§3 目錄表含 `frontend/lib/help/` 與 `frontend/components/domain/help/` 兩列；§5.2 Top 列含「本頁說明」；三處在同一個 commit（`git log -1 --format=%h -- <檔>` 與 `git diff --stat <該 commit>^ <該 commit> --` 只含 §5.7 的主控文件列）；`API_Contract_P3-6.md` 未改（G-C1 禁改集合涵蓋） |
| AT-PH-08-3-E-1 | GT | 3 | G-D1 檢查函式餵合成 Markdown（缺一格、缺目錄列、缺 Top 列各一份） | 逐一回非空；齊全者回空 |

## 4. 邊界與錯誤測試規格

下列邊界各自由所列 AC 的 AT（含反向 AT）覆蓋；開發棒不得因「看起來不會發生」而省略夾具。「覆蓋」欄為 AC 簡碼；對應 AT 的 Given 含該 B 列的全部值（每個值至少出現在一個 AT 的 Given）。

| B | 邊界或錯誤路徑 | 規格（可判定） | 覆蓋 |
|---|---|---|---|
| B-01 | code point 與 UTF-16 | 句長（≤ 60）、`sourceNote`（≤ 30）、欄位名（≥ 3 才掃）一律以 code point 計（`[...s].length`）：全形字、U+20BB7 之類代理對各算 1；組合附加符號各算 1（不做字素叢集）；這三處不得用 `String.length` | 05-1、05-4、05-5 |
| B-02 | 切句 | 切分字元「。！？；」與換行；`\r\n` 視為換行；連續分隔、前後空白、全空白段一律丟棄；英文句點、逗號、冒號、頓號、`・` 不是切分點（全形「；」是） | 05-1 |
| B-03 | 英文詞 | 連續 ASCII 字母、長度 ≥ 2；底線、連字號、數字當分隔；整詞比對不分大小寫；單一字母不算；ID 形態先剔除；全形字母（Ａ）與中文不算 ASCII | 05-2 |
| B-04 | 數字與色碼 | 連續半形數字 ≥ 3 位命中（剔除 ID 形態後），2 位不命中；全形數字不算；`#` 後 ≥ 3 位十六進位命中（`#abcg` 的 `#abc` 即命中），`#12`、`#1` 不命中 | 05-3 |
| B-05 | `Extended_Pictographic` | `😀`、`✅`、`↔`、`™` 命中；`→`、`←`、`↑`、`↓`、全形標點、`・` 不命中（實測 2026-10-27，§5.8） | 05-3 |
| B-06 | 路徑解析 | `""`、`/`、尾斜線、非 ASCII 與 URL 編碼的動態段、大小寫（`/Projects`）、前綴相似（`/projects-x`、`/self-improving-x`）、多一段、`/issues/x`、`/login`；`/projects/new` 對 `[projectId]` 取靜態段 | 03-3 |
| B-07 | 角色與登入狀態 | VIEWER、OPERATOR、ADMIN 皆渲染且內容相同；未登入（anon，非 `/login`）不渲染；已登入於 `/login` 不渲染（`TopRegion.tsx:36-38`：`showTools = !isLogin && status !== "anon"`）；hydration 前的 `loading` 狀態不在測試範圍（單元測試的 client 渲染一律已水合） | 01-1、01-2、01-3 |
| B-08 | 對話框開關 | 連開連關三次無重複掛載；開著時路由變更→關閉；開著時重繪（含頂列搜尋框狀態變動）→不關；Enter、空白鍵開；Esc、關閉鈕關；滑鼠開再 Esc 關焦點同樣回鈕（`RememberOpener` 讀 `document.activeElement`：`userEvent.click` 會先聚焦，`fireEvent.click` 不會，測試一律用 `userEvent`） | 01-4、07-1 |
| B-09 | 詞表失敗型別 | 503（含 `details.cause`、`details.detail`、`reason`）、504、網路失敗（`TypeError`）、`200` 但無 `legend`、`legend` 缺 `statuses`；401 不在範圍（`apiRequest` 的未授權處理器導向登入，非本功能） | 04-5 |
| B-10 | 詞表重取與快取 | 每次開啟重取（`staleTime:0`，不被 app 預設 5 秒擋）；失敗不重試（等 1,500 毫秒仍 1 個，React Query 預設重試延遲 1,000 毫秒）；`["help","issuesLegend"]` 不污染 `["issues"]`；關閉即回收（`gcTime:0`） | 04-5、06-3 |
| B-11 | `updatedAtNote` 三態 | 缺鍵、空字串、非空 | 04-4 |
| B-12 | `sourceFiles` 展開 | 檔案；`dir/**`；不存在的檔；含 `..`；單段萬用（`components/**`、`lib/**`、`app/**`、`hooks/**`）；展開 > 30（`components/domain/**` 實測 87）；展開結果排除 `*.test.ts(x)`、`*.d.ts`、`*.fixtures.ts`、`tests/` 子目錄 | 05-5、03-5 |
| B-13 | AST 文字抽取 | 字串字面值（含 JSX 屬性值）、樣板字串片段、JSX 文字算；註解不算；`import`／`export from` 位址不算；名稱被拆在兩個字面值之間不算；沿 `issues.static.test.ts:202-220` 的 `literalTexts`，**另加 `ts.isJsxText`**（該函式原本沒有 JSX 文字） | 05-5、05-7 |
| B-14 | pending 與已寫的交界 | pending 頁：路由無鈕但仍有 id、頁檔存在（可為佔位）、內容類 AT 豁免且被豁免的 id 清單印出；`PENDING_HELP_PAGES` 為空時全部路由有鈕；頁從 pending 移出的同一 commit，內容類 AT 自動納入 | 03-6、01-2 |
| B-15 | 姊妹案落地先後 | 先後兩序皆綠：新增路由與導覽項而說明未補→路由鎖與導覽鎖紅且訊息指出修法；補完（或暫列 pending 並同 commit 上修天花板）→綠；所有 AT 不寫死件數。**最小必要回歸**＝備份案 TCS（已凍結）AT-BK-01-2-4 的判定指令 `npx vitest run lib/help`，所涵蓋的路由鎖、導覽鎖、頁檔鎖與天花板（AT-PH-03-1-1、03-2-1、03-4-1、03-6-1，皆在 `lib/help/registry.test.ts`）；**建議回歸**＝`npx vitest run lib/help components/domain/help`（兩個目錄：每頁內容與出處鎖在 `content.test.ts`、`help.static.test.ts`，逐路由渲染鈕在 `PageHelpButton.test.tsx`，也會因新路由而動）；兩者是「最小」與「建議」的關係，不矛盾，由主控在姊妹案實作任務書寫明 | 03-1、03-2、08-1、08-2 |
| B-16 | 斷點與窄螢幕 | 390×844、767×900、768×900、1440×900；`max-md`＝<768；表格堆疊以幾何判準（y 遞增、x 相同）不以 CSS 字串 | 07-3 |
| B-17 | axe 範圍 | 關閉態、開啟態、展開共通；沿 `a11y.ts:38-54`（`reducedMotion`、滑鼠移開、等動畫跑完、視窗拉高避免 `outsideViewport`）；Next dev 浮標（`nextjs-portal`）已排除 | 07-4 |
| B-18 | 請求計數 | 新穎性規則（D-PH-13）；`/api/v1/issues` 以查詢串區分；頂列輪詢排除；點擊後再觀察 500 毫秒；`/issues` 頁自身清單請求（`limit=100`）不與詞表請求（`limit=1`）混淆 | 06-3 |
| B-19 | 零測試與假綠 | `-t`、`-g` 無命中＝FAIL；`.skip`、`.todo`、`.only`、`test.fixme` 零容忍（G-F9）；每個迴圈類 AT 有最低迭代數（防反空轉） | 全部 |
| B-20 | 格式與 lint | 新檔過 `npm run lint`（ESLint＋Prettier `format:check`：printWidth 200、雙引號、尾逗號、LF）與 `npx tsc --noEmit` | 全部 |

## 5. 測試資料規格

### 5.1 vitest 夾具與慣例

| 名詞 | 定義 |
|---|---|
| **RL** | `RootLayout`（`app/layout.tsx`）取 body 內的組裝結果（`layoutBody`，沿 `components/layout/layout.test.tsx:77-81`）渲染；`vi.mock("next/navigation")`（可變 `pathname`；`useRouter` 為 `{ push, replace, back }` 的 `vi.fn()`；`useSearchParams`、`useParams` 同 `layout.test.tsx:13-18`）與 `vi.mock("next/link")`（同 `:19-25`）；`beforeEach` 重設 `pathname`、`resetSessionCache()`、`clearSession()`；`signIn(role)`（`tests/helpers/api.tsx:81`）寫 session；fetch 替身以 `stubApi` 或 `stubIssuesApi` 提供：`GET /api/v1/projects?…` 回空分頁、`GET /api/v1/notifications/summary` 回 `{ pendingSignoffs: 0, pendingReviews: 0, unacknowledgedAlerts: 0, bridgeConnected: null, bridgeCheckedAt: null }`、`GET /api/v1/issues` 回黃金檔議題頁（含 `legend`），其餘回 404（頂列對 4xx 不重試，不影響說明鈕） |
| **PD** | `renderIssues(<PageHelpDialog page={…} open onOpenChange={…} content={…} />, { role })`（真 `Providers`；`next/navigation` 須 `vi.mock`，因 `AuthProvider` 用 `useRouter`） |
| **APP_QC** | 真 `components/providers/Providers.tsx` 提供的 `QueryClient`（D-PH-16）：經 RL 或 `renderIssues` 取得，**不自建、不用 `makeClient()`** |
| **錨點頁** | 輪 1a 即已寫的三頁：`/issues`（`issues`，議題詞表）、`/projects`（`projects`，常數狀態表）、`/settings`（`settings`，無狀態表）；組件層測試以錨點頁為預設路徑 |
| **登記頁** | `Object.values(HELP_PAGES)`（已寫頁，不含 pending） |
| **哨兵** | 產生器 `sentinel(kind)` 回 `§<kind><序號>§`（序號遞增、全程唯一，例 `§h12§`）；`sentinelContent(page, base)` 深拷貝 `HelpContent` 與頁並把每個登記文字（`title`、`purpose`、`steps`、欄位 `name`／`meaning`／`sourceNote`、`common.fields`、`states` 的 `meaning`／`next`、`sources` 的 `title`、`labelOf` 輸出、`keys`）換成哨兵；表 id 保留真值（只當 testid 與型別鍵用，不顯示） |
| **合成頁** | 測試內自造的 `PageHelp`（例：`states: []`、`states: [projectStatus, stepStatus(raw), alertRule]`、逸出樣本頁）；經 D-PH-3 的 `page` 參數注入，不需要登記 |
| **非同步慣例** | `TopRegion` 以 `next/dynamic` 載入 `PageHelpButton`（D-PH-17），`PageHelpDialog` 也可能按下鈕才載入。所以 HB 的測試：(a)「出現」類斷言一律 `await screen.findBy…`／`waitFor`，**不用**同步 `getBy…`；(b)「不渲染」類斷言（AT-PH-01-1-E-1、01-2-1 的 (a)～(d)、01-2-E-1 的 pending 路由）必須先 `await settle()` 再斷言，否則動態載入尚未完成時的「0 個」是空洞的真——`settle = () => act(async () => { await new Promise((r) => setTimeout(r, 50)); })`；每個此類 AT 內另須有一個同形態的對照組（有鈕的路由）先 `findBy` 到鈕，證明載入機制本身已完成（防空轉）。PD 直接渲染 `PageHelpDialog` 者不受影響。AT 的斷言內容不因同步或延遲載入而不同 |

### 5.2 注入縫（僅此三種；D-PH-3、D-PH-16）

1. `PageHelpDialog` 的 `content` 參數（`HelpContent`）與 `page` 參數——合成頁、哨兵內容、`raw` 模式、無狀態頁都經此。
2. `vi.mock("next/navigation")`、`vi.mock("next/link")`——路由與連結替身（沿既有版面測試）。
3. fetch 替身——`stubApi`／`stubIssuesApi`（`stub.overrides.list` 回 `unavailable()`、延遲 Promise 或丟 `TypeError`；`newStub({ legend })` 供哨兵詞表）。

**不允許**：`vi.mock` 換掉 `@/lib/help/*`、`stateSources`；`vi.spyOn` 改生產常數；改 `lib/domain/status.ts` 等既有常數。上游突變（R 條文表的［上游］）只在 QA 的 `git archive` 副本上做，不在測試碼裡做。

### 5.3 必備子集與矩陣（釘值只增不減；PRD §4、§8.2 為出處）

**`ANCHOR_PAGES`**：`["/issues", "/projects", "/settings"]`（輪 1a 即已寫）。

**`REQUIRED_PAGE_IDS`（16）**：`dashboard`、`projects`、`project-detail`、`goals`、`goal-detail`、`tasks`、`task-detail`、`project-form`、`goal-form`、`task-form`、`execute`、`monitor`、`import`、`settings`、`self-improving`、`issues`；`HELP_PAGES` 鍵∪`PENDING_HELP_PAGES` ⊇ 此集合。

**`REQUIRED_TABLE_IDS`（18）**：`projectStatus`、`goalStatus`、`taskStatus`、`stepStatus`、`importStatus`、`runStatus`、`runTransition`、`reviewKind`、`reviewDecision`、`alertSeverity`、`alertRule`、`gateName`、`sddPhase`、`sddFsmState`、`serviceState`、`obsClass`、`propClass`、`propState`。

**`ROUTE_TABLE`（19 條；PRD §4，於 HEAD 以 `git ls-files 'AgentConsole/frontend/app/**/page.tsx'` 複核：20 個 `page.tsx` 扣 `/login`）**

| 樣板（`HELP_ROUTES` 的鍵；具體路徑把 `[projectId]`→`p1`、`[goalId]`→`g1`、`[taskId]`→`t1`） | 說明 id |
|---|---|
| `/` | `dashboard` |
| `/projects` | `projects` |
| `/projects/[projectId]` | `project-detail` |
| `/projects/[projectId]/goals` | `goals` |
| `/projects/[projectId]/goals/[goalId]` | `goal-detail` |
| `/projects/[projectId]/goals/[goalId]/tasks` | `tasks` |
| `/projects/[projectId]/goals/[goalId]/tasks/[taskId]` | `task-detail` |
| `/projects/new` | `project-form` |
| `/projects/[projectId]/edit` | `project-form` |
| `/projects/[projectId]/goals/new` | `goal-form` |
| `/projects/[projectId]/goals/[goalId]/edit` | `goal-form` |
| `/projects/[projectId]/goals/[goalId]/tasks/new` | `task-form` |
| `/projects/[projectId]/goals/[goalId]/tasks/[taskId]/edit` | `task-form` |
| `/projects/[projectId]/execute` | `execute` |
| `/projects/[projectId]/monitor` | `monitor` |
| `/import` | `import` |
| `/settings` | `settings` |
| `/self-improving` | `self-improving` |
| `/issues` | `issues` |

**`PAGE_STATES`（PRD §4 的「狀態表」欄逐頁釘值；表群順序不鎖、集合與模式要等；`raw`＝畫面印原值，其餘為 label 模式）**

| 說明 id | 狀態表群 |
|---|---|
| `dashboard` | `projectStatus` |
| `projects` | `projectStatus` |
| `project-detail` | `projectStatus`、`goalStatus`、`sddPhase`、`sddFsmState`（raw） |
| `goals` | `goalStatus` |
| `goal-detail` | `goalStatus`、`taskStatus` |
| `tasks` | `taskStatus` |
| `task-detail` | `taskStatus`、`stepStatus`（**raw**，執行歷史印原值 `STARTED` 等，`TaskDetailView.tsx:150`） |
| `project-form` | （無；在 `NO_STATE_PAGES`） |
| `goal-form` | `goalStatus`（前置依賴挑選器每列帶目標狀態，`EntityForms.tsx:236`） |
| `task-form` | （無；在 `NO_STATE_PAGES`） |
| `execute` | `runStatus`、`runTransition`、`reviewKind`、`reviewDecision`、`taskStatus`（**不含** `stepStatus`） |
| `monitor` | `runStatus`、`runTransition`、`stepStatus`（label，中文事件時間軸）、`alertSeverity`、`alertRule`、`sddPhase`、`sddFsmState`（raw） |
| `import` | `importStatus`、`gateName` |
| `settings` | （無；在 `NO_STATE_PAGES`） |
| `self-improving` | `obsClass`、`propClass`、`propState`（**raw**，畫面印英文原值，`SiProposalsPanel.tsx:190`） |
| `issues` | `{ legend: "issues" }`（取自 API，不入狀態表） |

**`UPSTREAM`（AC-PH-04-1、04-3 的獨立對照；測試內**直接 import** 既有常數，不經 `STATE_SOURCES`）**

| 表 id | 鍵（`UPSTREAM[id].keys()`） | 標籤（`UPSTREAM[id].label(k)`；無＝只准 `raw`） |
|---|---|---|
| `projectStatus` | `Object.keys(PROJECT_STATUS)` | `PROJECT_STATUS[k].label` |
| `goalStatus` | `Object.keys(GOAL_STATUS)` | `GOAL_STATUS[k].label` |
| `taskStatus` | `Object.keys(TASK_STATUS)` | `TASK_STATUS[k].label` |
| `stepStatus` | `Object.keys(STEP_STATUS)` | `STEP_STATUS[k].label` |
| `importStatus` | `Object.keys(IMPORT_STATUS)` | `IMPORT_STATUS[k].label` |
| `runStatus` | `Object.keys(RUN_STATUS)` | `RUN_STATUS[k].label` |
| `runTransition` | `Object.keys(BRIDGE_TRANSITION)` | `BRIDGE_TRANSITION[k]?.label` |
| `reviewKind` | `Object.keys(REVIEW_KIND)` | `REVIEW_KIND[k].label` |
| `reviewDecision` | `Object.keys(REVIEW_DECISION_LABEL)` | `REVIEW_DECISION_LABEL[k]` |
| `alertSeverity` | `Object.keys(ALERT_SEVERITY)` | `ALERT_SEVERITY[k].label` |
| `alertRule` | `Object.keys(ALERT_RULE_LABEL)` | `ALERT_RULE_LABEL[k]` |
| `gateName` | `Object.keys(GATE_LABEL)` | `GATE_LABEL[k]` |
| `sddPhase` | `Object.keys(SDD_PHASE_LABEL)` | `SDD_PHASE_LABEL[k]` |
| `serviceState` | `Object.keys(SERVICE_LABEL)` | `SERVICE_LABEL[k]` |
| `obsClass` | `OBS_STATUS_OPTIONS.filter((o) => o.id !== "").map((o) => o.id)` | 同列 `.label` |
| `propClass` | `PROPOSAL_STATUS_OPTIONS.filter((o) => o.id !== "").map((o) => o.id)` | 同列 `.label` |
| `propState` | `PROP_STATE_KEYS` | （無；raw） |
| `sddFsmState` | 弱鎖（AT-PH-04-1-2）：五個鍵＝`HUMAN_PENDING`、`SPEC_FROZEN`、`ESCALATION`、`ESCALATION_FINAL`、`AUTOCLAUDE_DELEGATED` | （無；raw） |

**`COMMON_ANCHORS`（13；AC-PH-02-6 的「涵蓋 §4 末列各項」，子字串錨點，每個至少被一個 `HELP_COMMON.fields[].name` 包含；已以 AST 對 `components/layout/**` 與 `hooks/useServiceStatus.ts` 預跑，13 個全數命中，但必須含 JSX 文字——不含則漏 8 個，B-13）**：`說明文件`、`下載 CLI`、`GitHub`（公告列，`TopRegion.tsx:53-57`）、`Engine Bridge`（`:59`、`BottomRegion.tsx:39`）、`通知總覽`、`幫助中心`、`繁體中文`（`:65、70、75`）、`搜尋`（`:123` 的 `aria-label`）、`最近專案`（`:135`）、`通知`（`NotificationBell` 的名稱；子字串含於「通知總覽」亦可）、`待審批佇列`（`:151`）、`console-api`（`BottomRegion.tsx:38`）、`我的專案`（`ToolsRegion.tsx:83`）。

**`FIXED_TEXT`（D-PH-6；AC-PH-02-4 的哨兵檢查扣掉的固定字）**：`・本頁說明`、`這頁做什麼`、`怎麼用`、`欄位說明`、`狀態說明`、`全站共通`、`欄位`、`意思`、`資料來源`、`狀態`、`通常的下一步`、`畫面上的原值`、`這一頁沒有會變動的狀態。`、`結果`、`來源`、`嚴重度`、`狀態詞表載入中…`、`狀態詞表暫時取不到：`，加六類 `FIELD_SOURCES` 的值；比對前先去除標點、空白與全形括號。

### 5.4 詞表、測試鉤與逸出樣本

**英文詞白名單 `ENGLISH_WHITELIST`**：31 詞，逐字見 AT-PH-05-2-2（PRD §8.3；單一出處）。

**`FIELD_SOURCES`（6）**：`您填寫或選擇`、`系統自動產生`、`執行引擎回報`、`自我進化帳本`、`系統參數`、`其他頁面帶入`。


**黃金檔詞表 `LEGEND`**：`tests/fixtures/si/A.camel.json` 的 `issues.legend`（四群 7／8／4／4、`unmappedLabel`＝`未歸類`、`updatedAtNote`＝`已完成議題的日期是帳本上的「最後已知動靜」，不是結案日（帳本沒有記結案時間）`，v0.2 對照該檔 `:1005` 逐字）；測試改字一律 `clone` 後改。

**逸出樣本 `ESCAPE_SAMPLES`**：見 AT-PH-02-3-1 的 Given（判定不靠標籤名，而靠「記號仍在文字裡、且沒有元素的文字恰等於記號內的字」）。

**表單欄位快照 `FORM_LABELS`**（AT-PH-05-7-2 的防反空轉）：清單逐項見 AT-PH-05-7-1（2026-10-27 於 HEAD 複核：`EntityForms.tsx:147、215、248、302` 的 `ProjectForm` 5、`GoalForm` 3 加 `DependsOnField` 1、`TaskForm` 6）。

**前端測試鉤（`data-testid`）**：清單見 C4（PRD §7 的清單，加 D-PH-7 的 `page-help-legend-loading`、`page-help-legend-error` 兩個補充；單一出處）。

### 5.5 lint 樣本表（AT-PH-05-1-E-1、05-2-2、05-2-E-1、05-3-2、05-6-1、05-6-E-1；於 scratchpad 以等價實作預跑，結果見 §5.8）

| 樣本 | 預期 |
|---|---|
| 「字」×60 一句 | `lintText` 回空；×61 回非空（句長） |
| 「字」×60 的 U+20BB7 | 回空（以 code point 計；UTF-16 長度 120） |
| 「甲。乙！丙？丁；戊」 | `splitSentences` 得 5 句 |
| 「這裡有 Foo 這個詞」 | `unlistedEnglishWords` 回 `["Foo"]` |
| 「由 AutoClaude 啟動」「由 autoclaude 啟動 與 SIGNOFF」 | 回空（整詞、不分大小寫） |
| 「console-api 與 well_known」 | `console-api` 回空；`well_known` 回 `["well","known"]` |
| 「Level2 等級」 | 回空（數字相接取字母段 `Level`） |
| 「見 `OBS-SI-001` 與 `PROP-SI-004`」 | 英文與數字檢查皆回空（ID 形態先剔除，D-PH-10） |
| 「Level 3 · Review & Approve」 | 回 `["Review","Approve"]` |
| 「完成 😀」「完成 ✅」「往返 ↔ 兩端」「產品™」 | `forbiddenFindings` 回非空（emoji） |
| 「按 → 前往」 | 回空（`→` 不是 `Extended_Pictographic`） |
| 「顏色 #abc123」「顏色 #abc」「第 #123 項」 | 回非空（色碼）；「第 #12 項」回空 |
| 「這是 **粗體**」「這是 `code`」「連結 [a](b)」 | 各回非空（Markdown 記號） |
| 「請看 <b>粗</b>」 | 回非空（HTML 標籤） |
| 「網址 https://x.y」「a://b」 | 回非空（`://`） |
| 「路徑 C:\Users\x」「路徑 /Users/x」「路徑 /home/x」 | 各回非空（磁碟機或家目錄路徑） |
| 「共 1234 筆」「共 123 筆」「共 12 筆」 | 前兩者回非空（≥3 位）、後者回空 |
| 「把 Token 與 Agent 用在 Console 的 Run 與 Level」 | `lintText` 回空（全為白名單詞） |
| 「第 A 步與 I 型」 | 回空（單一字母不算） |

### 5.6 e2e 夾具（`tests/e2e/page-help.mock.spec.ts`；不改 `mockApi.ts`、不改既有 spec）

| 項 | 內容 |
|---|---|
| 載入與登入 | `signInAs(page, "OPERATOR")`（`mockApi.ts:141`；VIEWER 另一個測試）；`installApiMock(page, compose(shellHandler(), issuesLegend, notFoundFallback))`；`collectConsoleErrors(page)`（只斷言點擊之後的新增錯誤，隔離既有頁面載入雜訊） |
| `issuesLegend` | `GET /api/v1/issues`（任何查詢串）回黃金檔議題頁形狀：`schemaRev: 1`、`kind: "issues"`、`items: []`、`legend: <黃金檔 issues.legend>`、`summary` 全 0（黃金檔以 `readFileSync(path.join(process.cwd(), "tests", "fixtures", "si", "A.camel.json"))` 讀，沿 `issues.mock.spec.ts:16-18`） |
| `notFoundFallback` | 其餘 `/api/v1/**` 沿 `installApiMock` 預設回 404（頁面顯示各自的錯誤或空狀態；既有頁面載入時對 4xx 不導向：`router.replace` 只出現在登入閘、刪除後返回與匯入頁的使用者操作，已用 `Grep` 查過 `components/**`、`app/**`） |
| 路由→網址 | `Object.keys(HELP_ROUTES)` 每個樣板代入 `p1`／`g1`／`t1`（`import { HELP_ROUTES, PENDING_HELP_PAGES, HELP_PAGES } from "../../lib/help/registry"`，相對路徑或 `@/` 別名，兩者 Playwright 的 TS 載入器皆可解析；`lib/help/**` 只含純文字與型別，無 DOM 相依） |
| 新增請求 | 點擊前 `before = new Set(calls.map(noveltyKey))`；點擊、等對話框、再等 500 毫秒；`added = calls.slice(n).filter((c) => !before.has(noveltyKey(c)))`，`noveltyKey` 見 D-PH-13 |
| axe | `expectNoA11yViolations(page, 標籤)`（`a11y.ts:94-97`）；開啟態另掃展開「全站共通」後；視窗 `page.setViewportSize` 於 `goto` 之前設定 |
| 鍵盤 | `tabUntil(page, selector)`（上限 80 次；寫法沿 `issues.mock.spec.ts:112-118`，在 spec 內自備，不 import 既有 spec） |
| 輸出目錄與 CI | CI 以 `E2E_MODE=standalone npx playwright test mock.spec --output=test-results-mock` 自動帶入本 spec（`agentconsole-ci.yml:143-148`）；本機重跑一律另帶 `--output <各自目錄>` |

### 5.7 允許變更的檔案集合（`git diff --name-only <base>` 必須 ⊆ 本節；「同步鎖」＝PRD §9 的〈需同步改的既有鎖〉逐檔逐行，2026-10-27 於 HEAD `000a217b` 重核行號與值全數吻合）

路徑省略前綴者相對 `AgentConsole/frontend/`。

| 路徑 | 類別 | 內容 |
|---|---|---|
| `lib/help/types.ts`、`states.ts`、`common.ts`、`registry.ts`、`lint.ts` | 新增 | 框架檔（輪 1a） |
| `lib/help/<id>.ts`（每頁一檔；撰寫時 16 檔：`dashboard`、`projects`、`project-detail`、`goals`、`goal-detail`、`tasks`、`task-detail`、`project-form`、`goal-form`、`task-form`、`execute`、`monitor`、`import`、`settings`、`self-improving`、`issues`） | 新增 | 輪 1a 先寫 `issues`、`projects`、`settings`，其餘於輪 1a 建佔位並列 pending、輪 2、3 補實；姊妹案日後加 `sysadmin*.ts` |
| `lib/help/content.test.ts`、`registry.test.ts`、`lint.test.ts` | 新增 | 三支測試檔（輪 1a） |
| `components/domain/help/stateSources.ts`、`PageHelpButton.tsx`、`PageHelpDialog.tsx`、`IssuesLegendGroups.tsx` | 新增 | 元件與名稱解析（`stateSources.ts` 輪 1a，三個元件輪 1b） |
| `components/domain/help/stateKeys.test.ts`、`PageHelpButton.test.tsx`、`PageHelpDialog.test.tsx`、`help.static.test.ts` | 新增 | 四支測試檔（`stateKeys.test.ts` 輪 1a；`help.static.test.ts` 輪 1a 起建、1b 補；兩個元件測試輪 1b） |
| `tests/e2e/page-help.mock.spec.ts` | 新增 | Playwright mock spec（唯一的 e2e 檔；不新增 `*.stack.ts`，§7.1 Q4） |
| `components/layout/TopRegion.tsx` | 修改（加法）＋同步鎖 | （輪 1b）`:17` 旁加 `import dynamic from "next/dynamic";` 與 `const PageHelpButton = dynamic(() => import("@/components/domain/help/PageHelpButton").then((m) => m.PageHelpButton));`（D-PH-17）；`:145-157` 右側群組在待審批佇列 `</Link>`（`:156`）之後加 `<PageHelpButton />`；`layout.test.tsx:71-74`（`components/layout` 恰四個元件檔）不受影響（不新增 layout 檔）；`:263-272`（`/login` 無動作）仍成立；`tests/design-rules.test.ts:68-69` 讀 `TopRegion.tsx` 原文斷言 `focus-visible:outline-offset-[-2px]`（`:124`），保留該行 |
| `lib/domain/si.ts` | 修改（加法） | `:191`（`PROP_STATUS_BY_STATE` 的 `};`）之後加 `export const PROP_STATE_KEYS = Object.keys(PROP_STATUS_BY_STATE);`；無行為變更；`lib/domain/si.test.ts:393-398` 釘根層十個提案狀態的歸類、不釘匯出清單，不受影響（PRD F-18 (2) 已於本檔複核） |
| `vitest.config.mts` | 修改（加法） | `coverage.include`（`:26-72`）加 `lib/help/registry.ts`、`lib/help/lint.ts`、`components/domain/help/stateSources.ts` 三行；`thresholds`（`:73`）不動 |
| `components/domain/si/si.static.test.ts` | 修改（同步鎖；**本案唯一准改的既有測試**） | `:230-234` 的 `checkText` 第二分支限縮為 URL 形；新增 `AT_PH_06_2_3`、`AT_PH_06_2_E_2` 兩個 `it`（含負控）；其餘斷言原樣、不刪（D-PH-18；PRD 勘誤 1-1、1-2；輪 1a） |
| `AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027.md` | 新增（本檔） | Stage-2 契約 |
| `AgentConsole/docs/06_quality/SCG4-REVIEW-PageHelp-<日期>.md`、`AgentConsole/docs/06_quality/RTM.md`（新子表，編號由主控依落地序定；RTM 計數列不動，ID 加反引號） | 收尾（主控） | 審查報告與追溯；開發棒交 rtm_backfill 檔、不直接改 |
| `AgentConsole/docs/02_architecture/Architecture.md`（§3 目錄表加兩列、§5.2 Top 列補「本頁說明鈕」、§5.4 檢查表加一格）、`AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md`（§4「與設計稿的已知差異」表補一列，F-16） | 收尾（主控，發布階段，同一個 commit） | AC-PH-08-3；開發棒不碰 |
| `docs/06_quality/SelfImproving_Observation_Ledger.md`（根層；一列 OBS，PRD D-8） | 收尾（主控，發布階段） | 處置 `deferred；再開症狀：根層 PROP_STATES 新增 retired，或 Console 的表刪掉它`（格式見該檔 `:5`）；開發棒不碰帳本 |
| `.github/workflows/windows-compat-ci.yml`、`macos-compat-ci.yml`（是否把 PRD 補入 `paths`） | 收尾（主控定奪） | PRD §9：先例 `Issue_Center_PRD.md` 已列入；`.github/**` 開發棒不准改（`AgentConsole/CLAUDE.md:141`）；`tools/tests/test_root_module_layout.py:140-146` 讀全部 `*_PRD.md` 要求含「模組落點表」者引用 SSOT，PRD 已引，現況不紅 |

**已複核不需改**：`components/layout/si-login-gate.test.tsx:43、60`（`/self-improving` 於輪 3 前無鈕、之後多一顆鈕，不影響其斷言）、`components/domain/views/DashboardView.test.tsx:355`（單獨渲染 `<TopRegion />`，`dashboard` 於輪 2 起多一顆鈕；以 `getByRole("dialog", { name: "審批 signoff：專案" })` 找對話框，不受影響）、`tests/e2e/p9-w7-ui.spec.ts:180-206`（`getByText("幫助中心", { exact: true })` 不受影響）、`components/domain/si/si.static.test.ts:83`（只掃 `app/self-improving/page.tsx`；但 `:249-276` 需同步改，見上列與 D-PH-18）、`playwright.config.ts:19`（`testMatch` 已涵蓋新 spec）、`lib/nav/registry.ts`（姊妹案才加第九項）。**不得變更**：`AgentConsole/backend/**`、`AgentConsole/engine-bridge/**`、`lib/api/endpoints.ts`、`queries.ts`、`reasons.ts`、`schema*.d.ts`、`openapi-p3-6.yaml`、`API_Contract_*.md`、`lib/nav/registry.ts`、既有 `*.test.ts(x)`（`si.static.test.ts` 除外）、`tests/e2e/*.spec.ts`、`.github/**`（開發棒）、`tools/**`、`.claude/**`、根層 `CLAUDE.md`、`AgentConsole/CLAUDE.md`、`package.json`（不新增依賴）。

### 5.8 預跑與基線（本檔作者 2026-10-27 於 HEAD `000a217b` 實測；v0.2 於 2026-10-28 補跑者標「v0.2」；只留結論）

| 項 | 結論 |
|---|---|
| vitest 全套、tsc、頂列三檔基線 | 全套 rc 0（88 個測試檔、1509 個測試皆通過）；`npx tsc --noEmit` rc 0；`layout.test.tsx`、`si-login-gate.test.tsx`、`DashboardView.test.tsx` 三檔 rc 0（3 個檔、32 個測試皆通過；AT-PH-06-2-2 要求完成後不少於此） |
| `sourceFiles` 展開 | 單一目錄最大 `components/domain/execute/**` 12 個；頂層萬用 `components/domain/**` 87、`components/**` 125、`lib/**` 28、`app/**` 22、`hooks/**` 5；上限 30＝PRD 值；`lib/**`、`app/**`、`hooks/**` 低於 30，故「單段萬用一律拒」須獨立於上限（AT-PH-05-5-2） |
| 首屏基線（讀 `.next/diagnostics/route-bundle-stats.json`；本機舊建置 10:23，**非 HEAD 重建**） | 21 列；首屏 685,448～1,305,485 位元組，預算 100,000 約為最大者的 7.7%；`si.ts`、`status.ts` 已在每條路由的 root chunk（`queries.ts:13-14`←`TopRegion.tsx:20`），新增量主要是說明文字本體、`sdd.ts` 鏈與 Radix Dialog（D-PH-17）；正式基線由輪 1a 開工前 `npm run build` 取得 |
| e2e 路由與 axe（HEAD、`next dev -p 3111`、最小 mock） | 19 條路由皆渲染頂列、無導向、無 `pageerror`；`networkidle` 18 條到不了（冷啟編譯），故固定等待（D-PH-13）；點擊前 3 秒後無新路徑；axe 六組合（`/issues`、`/projects/p1`、`/settings` × 1440×900、390×844）在尚無本鈕的 HEAD 皆 0 違規 |
| 突變重放程序（`git archive` 副本＋`node_modules` junction） | 副本基線 rc 0（2 檔、30 個測試皆通過）；刪 `reviewHelp.ts` 三個 `APPROVE` 條目、`PROJECT_STATUS` 加 `HOLD` 皆使既有測試轉紅（R-PH-14、R-PH-08 的［上游］前提成立）；清理先 `[IO.Directory]::Delete` 刪 junction |
| 型別鎖機制（同上副本＋`tsc`） | 通過版 rc 0；突變 A（`StateRow` 加 `label?`）rc 2、`TS2578`（指令未使用）；突變 B（表放寬成 `Record<string, StateRow>`）rc 2、`TS2344` 加 `TS2578`；tsc 含測試檔，`@ts-expect-error` 生效；`STATE_HELP` 宣告形態（v0.2 同程序）：逐表 `satisfies` 加外層 `satisfies` 時 rc 0（`keyof` 與列舉相等、缺鍵與多一值都被擋、可指派給 `HelpContent.states`）；整體型別註記時 rc 2（兩處 `TS2344`，`keyof` 退成 `string`；另有 `TS2578`） |
| `next/dynamic` 原型（v0.2；副本） | 假 `PageHelpButton` 以 `next/dynamic` 掛進 `TopRegion`：三檔既有測試 5 次皆 rc 0（32 個測試皆通過、無未處理錯誤）；首屏位元組未量（副本 build 跑不起來），由 G-F5 量 |
| `checkText` 變體模擬（v0.3；與 `bridgeLeaks` 同構的 TypeScript AST 實作） | 八個應紅樣本（E-2 的八型）與三個應空樣本（`/api/v1/si/status`、`components/domain/si/**`、模組位址）：原式把 `components/domain/si/**` 判紅（即缺陷本身）；「第二分支拿掉」與 A 式**行為完全相同**，五個應紅樣本回空；只做 (i) 的 B 式漏 `http://${h}:9000/si/x`、`${base}api/si/x`；(i)＋(ii) 八紅三空全對 |
| ESLint 等級與寫法（v0.2；`npx eslint --print-config` 與 `--stdin --stdin-filename`，不落檔） | `react-hooks/set-state-in-effect`、`@typescript-eslint/ban-ts-comment` 皆 error（`eslint-config-next` 16.4.3、`eslint-plugin-react-hooks` 7.1.1）；effect 內同步 `setOpen(false)` rc 1、`key={pathname}` 重掛載 rc 0；`@ts-expect-error` 無說明 rc 1（要 ≥ 3 字）、有說明無報錯；旁證 `components/charts/tremor/AreaChart.tsx:5-7` 為此停用一條 → D-PH-4、§2 |
| 閘門片段自測（`pwsh -NoProfile -File`，合成輸入；v0.2 重跑） | `Compare-RouteBundle` 六情境（相同、+100,000、+100,001、缺、多、欄位缺）皆符合；`Get-PageHelpViolations -Dev`：§5.7 外 8 個合成路徑 8／8 判違規、§5.7 內 11 個零違規，收尾階段放行主控文件列；G-C1 餵料整行直接餵＝全部誤判，`Substring(3)` 加改名行拆兩條後，在合成 git repo（改名、未追蹤、快照內髒檔）上原樣執行 SCG-4 區塊，只報出改名的舊路徑與 `backend` 檔；G-F9 舊式寫法（表格跳脫形貼進 PowerShell 變字面直線）對 7 個正例 0 命中（恆綠），新寫法 7／7、乾淨檔 0，檔數低於下限自判 rc 1（v0.3 已實跑） |
| lint 原型與 AC-PH-04-4 預跑 | 60 字句通過、61 字句不通過；`→` 不是 `Extended_Pictographic`，`↔`、`™`、`✅`、`😀` 是；`#12` 不命中、`#123` 命中；`OBS-SI-001` 含三位數字（→ D-PH-10）。自擬 `issues` 說明草稿含 2 個不同狀態名（小於 4，門檻可行），壓力樣本點名四個而轉紅；寫作提示：`issues` 頁的 `steps`、`fields` 不要逐一列舉狀態詞 |
## 6. RTM 連結確認

### 6.1 US → FR → AC → AT（數字由 §1、§3 機械計算；AC 43／43）

US-PH-nn 與 FR-PH-nn 一對一（FRD-lite 的 US 表）；FR→AC→AT 逐條見 §1 映射表。各 FR 的 AT 數（正向／反向）：FR-PH-01 5／6；FR-PH-02 8／4；FR-PH-03 10／5；FR-PH-04 21／9；FR-PH-05 12／5；FR-PH-06 7／5；FR-PH-07 11／4；FR-PH-08 3／3；合計 77／41（AT 118 個、AC 43／43、R 37 條）。

### 6.2 行為規則、非功能與出口條件（PRD §6、§11）→ AT 與證據

| 項目 | 條文 | 覆蓋 AT（AC 簡碼）與證據 |
|---|---|---|
| 零侵入與相容 | 只加前端檔、既有檔只有三處加法；不改 API、後端、Bridge、契約、導覽登記表；既有測試原樣通過（唯一例外 `si.static.test.ts` 同步鎖，D-PH-18） | 06-1、06-2（G-C1、G-C2、G-F1、G-F2） |
| 安全 | 純文字節點、無新端點與寫入、詞表請求沿 JWT 與 VIEWER 以上、說明不含機密與絕對路徑 | 02-3、05-3、06-3、01-3 |
| 效能（首屏） | 每路由 `firstLoadUncompressedJsBytes` 增量 ≤ 100,000 位元組 | 06-4（G-F5）；輪 1a 開工前取基線，輪 1b、2、3 出口各量一次，皆為閘（D-PH-17） |
| 效能（開啟 ≤ 100 ms、詞表請求 ≤ 2 秒） | PRD §6 與 F-18 (1) 自承**無自動化量測**（jsdom 計時不可靠；Playwright 計時受 CI 機器影響會偽陽性） | 不入 AT；掌舵者真機 V1 目測（§7.1 Q10） |
| 無障礙 | 鍵盤、焦點歸還、`DialogContent`、axe、設計規則 | 07-1～07-5 |
| 響應式 | <768 文字隱藏、對話框不超出視窗、表格堆疊、頂列不橫向捲動 | 07-3（Playwright 真瀏覽器；jsdom 不評估 CSS，沿 `API_Contract_SelfImproving_P1b.md:270`） |
| 跨平台 | 測試以 `path.join`、LF、UTF-8；CI 的 frontend job 只在 `ubuntu-latest`，Windows 無 CI 證據 | G-F1、G-F4 於 Windows 開發機自跑並貼輸出（PRD §11 (a)）；mock spec 本機 Windows 與 CI Linux 皆跑 |
| 掌舵者真機 V1～V4 | V1 逐頁開說明、不看英文說出用途，任指 3 頁各 2 個狀態說出意思與下一步；V2 390 寬視窗看得到鈕、讀得完、不橫向捲動；V3 議題中心說明狀態段與頁面一致；V4 只用鍵盤 Tab→Enter→Esc，焦點回鈕 | 機械面（必要非充分，PRD R-2）：V1＝05-1～05-4、05-6、02-x；V2＝07-3；V3＝04-4（mock 版對拍黃金檔，真後端補證由 V3 目視）；V4＝07-1；SCG-5 由掌舵者簽 |
| `next` 欄與釋義的**內容正確性** | PRD §8.2「每列 `next` 的依據」：專案、目標、任務取 PRD 附錄 B「可轉移至」（`PRD:2070-2105`）、批次與審核取契約附錄 A（`契約:3873-3891`）、匯入取契約 §1.1、連線狀態取 `useServiceStatus.ts` 檔頭與契約 §4.5 G-03、FSM 原始狀態取 BRIDGE §8 | **無機械判準**（內容是否與出處一致無法由程式判定）；SCG-4 由 QA 逐表人讀對照出處並在審查報告列對照結果；機械面只守形式（結構、句長、英文詞、字元、鍵集合） |
| PRD R-1（內容漂移的已知缺口） | 畫面私有字樣（SSE 串流點、能力晶片、自治等級、Agent 燈、階段進度）、`sddFsmState` 新增、非表單頁新增欄位、語意改變，鎖擋不到 | 由真機與 SCG-4 QA 人讀補位；本檔不假裝機械可驗（`sddFsmState` 只有弱鎖，AT-PH-04-1-2、E-2 自證其強度） |

### 6.3 R→AC 與 AC→R 連結

R 條文表每條 R 的 AT 欄皆指向存在且有 AT 的 AC；PRD 的 43 條 AC 每條至少被一條 R 引用（組裝腳本於本檔產生時檢查，缺漏＝組裝失敗；本次結果：R 37 條皆有效；AC 43／43 皆被至少一條 R 引用；每條 R 的突變欄皆標明套用面）。RTM 回填見 §6.5 (a)。

### 6.4 分輪與 AT 切分（PRD §11、D-11；鐵律七：四棒——輪 1a、1b、2、3——同一持有面〔`registry.ts`、`states.ts`、`lint.ts`〕一律串行，前一棒經主控親驗才派下一棒）

**切分原則**：八個測試檔的斷言**全部由登記表推導**，所以輪 1（1a、1b）把八個測試檔建好，輪 2、3 只加頁檔與登記（外加 `PENDING_CEILING` 下修），不改測試邏輯。輪 1 最重（約 104 列釋義、框架、八個測試檔、元件與接入），故切兩半、同持有面、串行：1a＝`lib/help` 資料層與其測試，1b＝元件、頂列接入與 e2e。頁從 `PENDING_HELP_PAGES` 移進 `HELP_PAGES` 的那一棒起，內容類 AT 自動把它納入迴圈。每棒出口 CI 全綠的最小 AT 集合＝「輪」欄排序在該棒之前或相同者全部，另須 `npx vitest run` 全套、`npx tsc --noEmit`、`npm run lint`、G-F9、G-C1、G-C2 皆通過（1b 起加 G-F2、G-F3、G-F5、G-F6、G-F7）。

| 輪 | 本棒新綁定的 AT | 累計（該棒出口 CI 全綠的最小 AT 集合） | 清單 |
|---|---|---|---|
| 1a | 58 | 58 | 按載具：HL 8、HR 15、HN 6、HK 17、HS 5、HX 2、GT 5；審查閘＝AT-PH-06-1-1、AT-PH-06-1-E-1、AT-PH-06-2-1、AT-PH-06-2-E-1、AT-PH-07-5-2 |
| 1b | 55 | 113 | 按載具：HB 12、HD 20、HS 10、E2 10、GT 3；審查閘＝AT-PH-06-2-2、AT-PH-06-4-1、AT-PH-06-4-E-1 |
| 2 | 1 | 114 | AT-PH-05-7-1 |
| 3 | 4 | 118 | AT-PH-03-6-3、AT-PH-04-6-2、AT-PH-08-3-1、AT-PH-08-3-E-1 |

**輪 1a（資料層與先導三頁）**：交付＝`lib/help/{types,states,common,registry,lint}.ts`（`states.ts` **一次寫完全部狀態表**，逐表 `satisfies`，不放寬）、16 個頁檔（`issues`、`projects`、`settings` 三頁寫完，其餘 13 個佔位並列 `PENDING_HELP_PAGES`，`PENDING_CEILING`＝13）、`components/domain/help/stateSources.ts`、`lib/domain/si.ts` 匯出、`vitest.config.mts` 三行、**`si.static.test.ts` 同步鎖（D-PH-18）**、測試檔 `content.test.ts`、`registry.test.ts`、`lint.test.ts`、`stateKeys.test.ts` 與 `help.static.test.ts` 的出處鎖半邊；**開工前先取 G-F5 基線**（`npm run build`）。

**輪 1b（元件、頂列接入與 e2e）**：交付＝`PageHelpButton.tsx`、`PageHelpDialog.tsx`、`IssuesLegendGroups.tsx`、`TopRegion.tsx` 以 `next/dynamic` 接入（D-PH-17）、`PageHelpButton.test.tsx`、`PageHelpDialog.test.tsx`、`help.static.test.ts` 其餘 AT、`page-help.mock.spec.ts`；出口加 G-F2（頂列三檔真跑）、G-F3、G-F5（首屏增量；自此每個出口都是閘）、G-F6、G-F7。

**輪 2（專案家族、匯入與儀表板）**：交付＝`dashboard`、`project-detail`、`goals`、`goal-detail`、`tasks`、`task-detail`、`project-form`、`goal-form`、`task-form`、`import` 十個頁檔寫完（只改頁檔與 `registry.ts` 登記，**不再動 `states.ts`**）；`PENDING_CEILING` 13→3；新綁定的 AT＝AT-PH-05-7-1（表單欄位清單鎖開始咬三個表單頁）；另 AT-PH-07-4-x 的 `/projects/p1` 組合自本輪起才被咬到（AT 輪 1b 已綁，`project-detail` 寫完才納入；之前走「pending 跳過並斷言無鈕」）。

**輪 3（執行、監控、自我進化與全站驗收）**：交付＝`execute`、`monitor`、`self-improving` 三個頁檔；`PENDING_HELP_PAGES` 清空、`PENDING_CEILING` 3→0（G-F8）；新綁定的 AT＝AT-PH-04-6-2（自我進化三張表）、AT-PH-03-6-3（出口）、AT-PH-08-3-1／E-1（主控的文件連動）；完整 e2e、SCG-4 獨立審查、RTM 回填、真機 V1～V4。

### 6.5 預估（實作棒數、新增測試檔、收集數增量）與主控待辦

| 項 | 預估 |
|---|---|
| 實作棒 | 4 棒串行（輪 1a 最重：約 104 列釋義、框架、四個測試檔；1b：元件與接入；2、3：頁檔與登記）；另預留 1～2 支修復棒（SCG-4 一審常見＝AT 鑑別力與內容審查） |
| 測試檔 | 新增 8 個（vitest 7＋Playwright 1），改既有 1 個（`si.static.test.ts`）；根層 `tools/tests` 零新增，`MIN_TESTS` 零相依餘裕與基線站點鎖不受影響 |
| 收集數 | vitest 增量 97 個以 AT 為單位的測試案例（含 `si.static.test.ts` 新增者；迴圈類 AT 在案例內迭代，不展開）；全套由 88 個檔、1509 個測試增至 95 個檔、約 1606 個測試以上；Playwright 增量 10 個 `test`（一支 spec；本機約 60～120 秒，19 條路由各載入一次） |
| 主控待辦（發布階段） | (a) RTM 新子表回填；(b) `Architecture.md` §3、§5.2、§5.4 與 ADR-002 §4 一列，同一個 commit；(c) PRD D-8 的 OBS 入帳一列（§5.7 OBS 列；開發棒不碰帳本）；(d) 把 §7.3 的勘誤貼進 PRD 檔尾〈勘誤〉節並更新本檔檔頭 digest；(e) 通知掌舵者排 V1～V4（§7.1 Q9）；(f) 是否把 PRD 補入 compat-ci `paths`（§5.7 末列）；重釘無 |

## 7. 主控代決與已結案問題（2026-10-28；掌舵者可隨時以 T1 推翻）

### 7.1 開放問題結案與預設裁決索引

Q1～Q10 全部結案（主控代決，一審後）：皆採本檔預設；Q4 不加全棧 e2e；Q9 改為「通知掌舵者排 V1～V4」。

| # | 事項 | 結案（出處） |
|---|---|---|
| Q1 | `helpForPath` 回 id 或回 `PageHelp` | 回 `HelpId` 或 `null`（D-PH-2） |
| Q2 | 測試縫用 `content` 參數或 `vi.mock` | `content` 參數（D-PH-3） |
| Q3 | AC-PH-05-3 的數字規則先不先剔除 ID 形態 | 先剔除（D-PH-10；勘誤 1-4） |
| Q4 | 是否為 SCG-5 另加全棧 e2e | **不加**：PRD §9 檔案集合與 AC-PH-06-1 不容新增 `*.stack.ts`；全棧證據＝真機 V3 |
| Q5 | axe 掃整頁遇到既有頁面的無關違規 | 預跑已答 0 違規（§5.8）；日後長出就補 spec 內最小夾具並另立缺陷，不縮範圍、不排除節點 |
| Q6 | 輪 1a 是否建好 16 個頁檔 | 是（13 個佔位並列 pending；AT-PH-03-4 的頁檔鎖要求全數存在） |
| Q7 | 是否釘 16 個固定頁名 | 不釘（只釘非空、不含「・」、不含樣板；AT-PH-03-5-1） |
| Q8 | `SHARED` 的型別 | `Record<string, HelpField>`（D-PH-11） |
| Q9 | 真機 V1～V4 何時排 | **通知掌舵者排**：輪 3 完成且 SCG-4 PASS 後由主控通知，掌舵者逐項簽（PRD §11）；V1、V3 需全棧 |
| Q10 | 是否加開啟 ≤ 100 ms、詞表 ≤ 2 秒的自動計時 | 不加（jsdom 與 CI 計時偽陽性；PRD F-18 已列真機目測） |
| 其他 | 已定案的預設裁決 | 見 AT-PH-02-1-E-1（重開後全站共通收合）、AT-PH-03-5-1（`NO_STATE_PAGES` 雙向）、D-PH-15、AT-PH-05-5-2、AT-PH-07-4-1～3、D-PH-13 |

### 7.2 寫作提示（給 SA 與開發棒；非缺陷）

白名單不含 `GitHub`、`CLI`、自治等級英文名（`Manual Confirm`、`Goal Confirm`、`Review & Approve`、`Exception Only`、`Full Autonomy`，`lib/domain/status.ts:172-178`）；這些畫面字樣只能出現在**欄位名欄與狀態名欄**，`meaning`、`next`、`purpose`、`steps` 一律用中文描述，否則 AC-PH-05-2 轉紅；要在說明文字逐字引用須增詞並走複審（PRD §8.3）。`serviceState.idle`（未登入）只在 `/login` 出現而該頁無鈕，列仍須保留以維持鍵鎖，`meaning` 不可空（PRD §8.2 備註 5）。

### 7.3 PRD 勘誤草案（可直接貼進 PRD 檔尾〈勘誤〉節；PRD 已凍結，本檔不改 PRD；貼入後由主控更新本檔檔頭 digest）

**勘誤一**（Stage-2 起草與一審所得；座標＝`docs/01_requirements/Console_PageHelp_PRD.md` v0.3 的行號）

| 條 | PRD 座標 | 原文 | 改文 | 理由 |
|---|---|---|---|---|
| 1-1 | AC-PH-06-1、AC-PH-06-2（L112、L113） | 06-2：「既有測試檔的 diff 只含 §9 所列檔、不刪斷言」；06-1：「只含 §9 表列路徑」 | 兩條各加：「唯一例外：`AgentConsole/frontend/components/domain/si/si.static.test.ts`——其 `bridgeLeaks` 的 `checkText` 第二分支限縮為 URL 形：只判以 `/` 或 `scheme://` 起頭的字串，以及樣板運算式之後的每個片段（一律視為 URL 形）；相對檔案路徑形（如 `components/domain/si/**`）不判；並補負控（`components/domain/si/**` 回空、`${base}/si/x` 回非空，另三個只靠第二分支才紅的樣本）；§9 表加此檔一列」 | 既有鎖 AT_932_4_3 把全樹非測試原始碼中含 `/si/` 路徑段的字串字面值一律判紅；`self-improving` 頁的 `sourceFiles` 必含 `components/domain/si/**`（AC-PH-05-5），副本實測整檔 rc 1；「只在字串開頭或樣板運算式後判」等於刪掉第二分支，不可 |
| 1-2 | §9 後的「已複核不需改」（L219） | 「`components/domain/si/si.static.test.ts:83`（只掃 `app/self-improving/page.tsx`）」 | 補「；`:249-276`（AT_932_4_3：掃 `app`、`components`、`lib`、`hooks` 全部非測試原始碼）**需同步改**，見 AC-PH-06-2 的例外」 | PRD 只複核了 `:83`，漏了 `:249-276` |
| 1-3 | §4 定義「狀態表」的說明句（L34；表頭在 L36）、AC-PH-03-5（L93） | 「『狀態表』＝該頁要列的狀態表 id（§8.2）」；AC-PH-03-5 沒有鎖「頁登記了該頁該列的表」 | AC-PH-03-5 補一句：「每個已寫的 PRD 十六頁，其 `states` 的表 id 集合與名稱模式（`label`／`raw`）須等於 §4 的『狀態表』欄」 | 欄位標題明定是逐頁必列的出處，卻沒有 AC 鎖它；開發棒漏列一張表沒有任何測試紅（TCS D-PH-15、AT-PH-03-5-2） |
| 1-4 | AC-PH-05-3（L106）、AC-PH-05-2（L105）、AC-PH-05-6（L109） | 05-3：「連續 ≥ 3 位半形數字」（未說先剔除 ID 形態）；05-6：「4 位數字」 | 05-3 加「（先剔除 `OBS-SI-NNN`、`PROP-SI-NNN`、`DEF-N-N` 形態，再判英文詞與數字）」；05-6 的「4 位數字」改「3 位數字（2 位不命中）」 | `OBS-SI-001` 本身含三位數字，不先剔除則說明文字連引用一個真編號都違規；05-2 的剔除只寫在英文詞規則；兩條門檻對齊並補邊界（TCS D-PH-10） |
| 1-5 | AC-PH-03-5（L93） | 「`purpose` 1～3 句」 | 加「（以 `lint.ts` 的 `splitSentences` 對全部 `purpose` 項切句，合計 1～3 句）」 | `purpose` 是陣列，「句」與「項」不同；與 AC-PH-05-1「每頁 `purpose` 合計 ≤ 3 句」同一判準（TCS AT-PH-03-5-1） |
| 1-6 | AC-PH-04-5（L100） | 「取 `siErrorParts`」 | 加「；三項皆空（網路失敗、無詳情）時改接 `describeError`；`200` 但回應沒有 `legend` 或四群缺席同樣走失敗句，原因寫『回應沒有詞表』」 | 網路失敗時 `siErrorParts` 三項皆空，句子會斷在冒號；空表不是成功（TCS D-PH-8） |
| 1-7 | AC-PH-03-5（L93） | 「`states` 為空者必在 `NO_STATE_PAGES`」 | 改雙向：「`states` 為空者必在 `NO_STATE_PAGES`，且 `NO_STATE_PAGES` 內者必為空」 | 單向則名單可無限陳舊（TCS AT-PH-03-5-1） |
| 1-8 | AC-PH-02-1（L82）、AC-PH-02-5（L86） | 02-1：「四個 `h3`」；02-5：「每表有小標題」 | 02-5 加「小標題與詞表群標題一律 `h4`」 | 小標題若用 `h3` 會違反「恰四個 `h3`」（TCS D-PH-5） |
| 1-9 | AC-PH-06-3（L114） | 「頁面自身的輪詢以網址白名單排除，細節由 TCS 定」 | 改「以新穎性規則排除：點擊後才出現、且（方法, 路徑）在點擊前沒出現過的請求才算新增；`/api/v1/issues` 另含查詢串」 | 逐頁列舉輪詢網址脆弱易漏（TCS D-PH-13） |
| 1-10 | AC-PH-06-1（L112） | 「`git diff --name-only <Stage-2 凍結 commit>..HEAD`」 | 改「以本功能自己的 commit 範圍（`<base>..<本功能最後 commit>`）；共用分支上姊妹案 commit 交錯者不計」 | 範圍在共用分支上不明（TCS G-C1） |
| 1-11 | §8.1（L149 起） | （描述）型別小節只列型別，未定公共面簽章 | 加一句「`helpForPath` 回 `HelpId` 或 `null`、`PageHelpDialog` 的 props、`STATE_SOURCES` 欄名（`title`、`keys`、`labelOf`）、`lint.ts` 匯出名、`SHARED` 型別、`HelpId`／`StateTableId` 聯集，以 TCS 的 D 表與〈契約節〉為準」 | PRD 未定的公共面由 TCS 補齊，避免兩處各寫一份 |
| 1-12 | §7 測試 id 清單（L145） | 「議題詞表群 `page-help-legend-statuses｜results｜sources｜severities｜note`。」 | 補「；詞表載入中 `page-help-legend-loading`（`role="status"`）、詞表失敗 `page-help-legend-error`（`role="alert"`）」 | AC-PH-04-5 要求載入中與失敗各一句固定文字，需要測試鉤而清單沒列；加法、不改既有 id（TCS D-PH-7、C4） |


## SCG-4 通過標準

**通過條件**（全部成立才算過；審查報告逐字貼各 G 指令的 rc 與輸出尾段；徑②：實作棒在 session 內自跑並貼證據，BRIDGE §8.6 第 4 點）：

1. **AC 43／43**：每個 AT 的判定指令 rc 0 且收集 ≥ 1 個測試（§2 零測試規則）；審查閘型 AT 以所指 G 編號指令的輸出為證。
2. **閘門全綠**：frontend G-F1～G-F9、共同 G-C1、G-C2；發布階段另跑 G-D1（主控）。
3. **突變**：R 條文表的 R-PH-01～R-PH-37 每條至少一個突變轉紅（killed）；［上游］突變可於凍結後立即對任何實作重放，［實作］突變待實作完成後重放；倖存者補 AT 並勘誤。
4. **型別鎖**：`npx tsc --noEmit` rc 0，且 AT-PH-04-2-x 的每個 `@ts-expect-error` 都生效（若指令變成「未使用」，tsc 即紅）。
5. **出口判準（PRD §11）**：(a) `npx vitest run` 全綠含新增測試、`npx tsc --noEmit`、`npm run lint`、`npm run build` 皆 rc 0，**並於 Windows 開發機自跑 vitest 與 tsc 貼輸出**；(b) `npx playwright test tests/e2e/page-help.mock.spec.ts` 全綠（standalone 產物，`--output` 各自目錄）；(c) 零侵入（G-C1、G-C2）、`PENDING_HELP_PAGES` 為空（G-F8，輪 3）、覆蓋率門檻不降（G-F3）、首屏 JS 增量（G-F5；自輪 1b 出口起每個出口都量，D-PH-17）。
6. **SCG-5 真機（掌舵者）**：V1～V4（PRD §11；§6.2 對應）；V1、V3 在全棧（`docker compose --profile db --profile app --profile full up -d --build`）上看。
7. 無 P1、P2 未結；凍結與放行依根 CLAUDE.md〈凍結常態規則〉與 BRIDGE §8。

**閘門指令**（`<repo>`＝monorepo 根，現查 `git rev-parse --show-toplevel`；`<base>`＝開發棒開工時的 HEAD，由主控在任務書寫明；`<snap>`＝同一時刻 `git status --porcelain -uall` 的輸出檔，由主控存檔並在任務書寫明路徑；PowerShell 形態、rc 先存變數再讀、不裸 `cd`；frontend 與 git 閘門不需 venv）：

```powershell
# frontend 閘門（G-F1～G-F7）
Push-Location <repo>\AgentConsole\frontend; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
# git status 閘門（G-C1 開發階段）：輸出逐行去掉 <snap> 已有的行（既有髒檔例 AutoClaude/.perf_baseline.toml 在 <snap> 內，不計）；每行是「2 字元狀態＋空白＋路徑」，改名、複製行是「舊 -> 新」，所以要去前綴、拆開，兩個路徑都餵進篩選函式（整行直接餵會全部誤判）
$snap = Get-Content -LiteralPath <snap 檔> -Encoding utf8; $o = git -C <repo> -c core.quotepath=false status --porcelain -uall; $rc = $LASTEXITCODE; "rc=$rc"
$paths = $o | Where-Object { $snap -notcontains $_ } | ForEach-Object { $_.Substring(3) -split ' -> ' }
Get-PageHelpViolations $paths -Dev
```

G-C1 的篩選函式（AT-PH-06-1-1、AT-PH-06-1-E-1；路徑一律以 `/` 與 repo 相對形態餵入；`-Dev` 時排除主控收尾列）：

```powershell
$allowedDev = @(
  '^AgentConsole/frontend/lib/help/[^/]+\.ts$',
  '^AgentConsole/frontend/components/domain/help/[^/]+\.tsx?$',
  '^AgentConsole/frontend/tests/e2e/page-help\.mock\.spec\.ts$',
  '^AgentConsole/frontend/components/layout/TopRegion\.tsx$',
  '^AgentConsole/frontend/lib/domain/si\.ts$',
  '^AgentConsole/frontend/vitest\.config\.mts$',
  '^AgentConsole/frontend/components/domain/si/si\.static\.test\.ts$',
  '^AgentConsole/docs/03_testing/contracts/TCS-PageHelp-20261027\.md$'
)
$allowedClose = $allowedDev + @(
  '^AgentConsole/docs/06_quality/(SCG4-REVIEW-PageHelp-[^/]+\.md|RTM\.md)$',
  '^AgentConsole/docs/02_architecture/(Architecture|ADR-002-Frontend-Design-System)\.md$',
  '^docs/06_quality/SelfImproving_Observation_Ledger\.md$'
)
function Get-PageHelpViolations([string[]]$paths, [switch]$Dev) {
  $ok = if ($Dev) { $allowedDev } else { $allowedClose }
  $paths | Where-Object { $p = $_; -not ($ok | Where-Object { $p -match $_ }) }
}
```

| G | 目錄 | 指令 | 期望 |
|---|---|---|---|
| G-F1 | `<repo>\AgentConsole\frontend` | `npx vitest run` | rc 0；測試檔 ≥ 93（1a 出口）／≥ 95（1b 起）、案例數不少於基線（88 個檔、1509 個測試）加該棒新綁定者 |
| G-F2 | 同上 | 三檔逐檔各跑一次：`npx vitest run components/layout/layout.test.tsx`、`… components/layout/si-login-gate.test.tsx`、`… components/domain/views/DashboardView.test.tsx`（輸出逐檔貼證據檔；PRD §9 真跑清單） | 逐檔 rc 0；三檔合計不少於基線 32 個測試 |
| G-F3 | 同上 | `npm run test:cov` | rc 0；覆蓋率文字表含 `lib/help/registry.ts`、`lib/help/lint.ts`、`components/domain/help/stateSources.ts` 三列；`vitest.config.mts` 門檻 lines 70、statements 70、functions 70、branches 60 未動 |
| G-F4 | 同上 | `npm run lint`；再 `npx tsc --noEmit`（各一次呼叫） | 兩者 rc 0（ESLint＋Prettier `format:check`；tsc 含測試檔） |
| G-F5 | 同上 | 基線：**輪 1a 開工前**在 Stage-2 凍結 commit（`<base>`，工作樹乾淨）`npm run build`，把 `.next\diagnostics\route-bundle-stats.json` 複製到存檔（例 scratchpad 的 `route-bundle-stats.base.json`）；**輪 1b、2、3 出口各**再 `npm run build` 並複製一份；每份與基線餵下方 `Compare-RouteBundle` | 每個出口每條路由增量 ≤ 100,000 位元組、路由集合相同；各次 build 皆 rc 0（輪 1b 起皆為閘，D-PH-17） |
| G-F6 | 同上 | `npx vitest run tests/design-rules.test.ts` | rc 0（AT-PH-07-5-2） |
| G-F7 | 同上 | `$env:E2E_MODE="standalone"; npm run build; npx playwright test tests/e2e/page-help.mock.spec.ts --output <各自目錄>`；再跑 CI 形態 `npx playwright test mock.spec --output <各自目錄>`（全部 mock spec，確認新 spec 不破壞既有） | 兩次皆 rc 0；`<各自目錄>` 與 `E2E_WEB_PORT` 與其他並行行程不重疊 |
| G-F8 | `<repo>` | 輪 3 出口：`Select-String -Path AgentConsole\frontend\lib\help\registry.test.ts -Pattern 'PENDING_CEILING\s*=\s*0\b'`；並以 `npx vitest run lib/help/registry.test.ts -t "AT_PH_03_6_1"` 確認 `PENDING_HELP_PAGES.length` 為 0（AT-PH-03-6-1 在天花板為 0 時即等於此斷言） | 輪 3 起命中且 rc 0；輪 1a、1b、2 不要求，但天花板逐棒只降不升（`git log -p` 核對） |
| G-F9 | `<repo>` | 下方〈G-F9〉程式碼區塊（正規式含「或」符號，不放表格：表格內的跳脫形貼進 PowerShell 變字面直線，閘恆綠） | 無命中（零跳過，B-19）；檔數低於下限（1a 出口 6、1b 起 9）區塊自判 rc 1（閘空轉算紅） |
| G-C1 | `<repo>` | 開發階段：上方 git status 閘門算出的 `$paths` 餵 `Get-PageHelpViolations -Dev`；已 commit 後改 `git diff --name-only <base>..<本功能最後 commit>` 餵 `Get-PageHelpViolations`（共用分支上姊妹案 commit 夾在中間者，以本功能自己的 commit 範圍判定，勘誤 1-10） | 無輸出；自證負控見 AT-PH-06-1-E-1（8 個合成違規路徑 8／8 判違規；§5.7 內路徑回空） |
| G-C2 | `<repo>` | `git diff -U0 <base> -- AgentConsole/frontend/**/*.test.ts AgentConsole/frontend/**/*.test.tsx AgentConsole/frontend/tests/e2e/*.spec.ts`（排除本功能新增的八個檔） | 空；**唯一例外** `components/domain/si/si.static.test.ts`（D-PH-18）：其 hunk 只准在 `bridgeLeaks` 的 `checkText` 第二分支與新增的 `AT_PH_06_2_3`、`AT_PH_06_2_E_2`，逐 hunk 核對、不刪既有斷言 |
| G-D1 | `<repo>` | 主控發布階段：`Select-String -Path AgentConsole\docs\02_architecture\Architecture.md -Pattern '說明登記表一列','frontend/lib/help/','frontend/components/domain/help/','本頁說明'`；`git log -1 --format=%h -- AgentConsole/docs/02_architecture/Architecture.md` 與 `git show --stat <該 commit>` | 四個字樣皆命中且三處在同一個 commit；`API_Contract_P3-6.md` 未改（AT-PH-08-3-1） |

G-F9（零跳過）：

```powershell
Push-Location <repo>; $fe = 'AgentConsole\frontend'
$files = @(Get-ChildItem -Path "$fe\lib\help", "$fe\components\domain\help" -Filter '*.test.ts*' -File) + @(Get-Item -ErrorAction SilentlyContinue "$fe\tests\e2e\page-help.mock.spec.ts", "$fe\components\domain\si\si.static.test.ts")
$hits = $files | Select-String -Pattern '\.(skip|skipIf|only|todo|fixme)\b|\b(xit|xtest|xdescribe)\('; Pop-Location
"掃 $($files.Count) 個檔；命中 $(@($hits).Count) 筆"; $hits
if ($files.Count -lt <N>) { 'rc 1：檔數低於下限'; exit 1 }   # <N>＝1a 出口填 6、1b 起填 9
```

自證與空轉防護（§5.8）：七個正例命中 7 筆、乾淨檔 0 筆；用 `Get-ChildItem` 列檔並自判檔數，因為 `Select-String -Path` 對全錯的路徑會安靜地得 0 筆。

`Compare-RouteBundle`（G-F5；AT-PH-06-4-1、E-1）：

```powershell
function Compare-RouteBundle([string]$before, [string]$after, [int]$limit = 100000) {
  $b = @(Get-Content -Raw -Encoding utf8 $before | ConvertFrom-Json); $a = @(Get-Content -Raw -Encoding utf8 $after | ConvertFrom-Json)
  $bad = @()
  foreach ($r in $b.route) { if ($a.route -notcontains $r) { $bad += "缺：$r" } }
  foreach ($row in $a) {
    $old = $b | Where-Object { $_.route -eq $row.route }
    if ($null -eq $old) { $bad += "多：$($row.route)"; continue }
    if ($null -eq $row.firstLoadUncompressedJsBytes -or $null -eq $old.firstLoadUncompressedJsBytes) { $bad += "欄位缺：$($row.route)"; continue }
    $d = $row.firstLoadUncompressedJsBytes - $old.firstLoadUncompressedJsBytes
    if ($d -gt $limit) { $bad += "超過：$($row.route) +$d" }
  }
  $bad
}
```

自證（AT-PH-06-4-E-1，以兩份合成 JSON 在 scratchpad 跑）：增量恰 100,000→無輸出；100,001→`超過`；缺一條路由→`缺`；多一條→`多`；欄位缺→`欄位缺`；兩份相同→無輸出。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

### 勘誤一（2026-10-28；SCG-4 獨立審查一審 FAIL→修復棒→二審 PASS；報告 `AgentConsole/docs/06_quality/SCG4-REVIEW-PageHelp-20261028.md`；主控依凍結常態規則於 RELEASE_READY 以 `spec-refreeze` 記新 digest）

| 條 | TCS 座標 | 原文 | 改文 | 理由 |
|---|---|---|---|---|
| 1-1 | §3.2 AT-PH-04-5-2 (c) | 「或 statuses 缺」 | 「或 statuses／results／sources／severities 任一缺或非陣列」 | F-01：D-PH-8／PRD 勘誤 1-6 要求四群之一缺席＝失敗句；一審突變 X29（去 severities 檢查）、X30（去 results、sources 檢查）倖存，修復棒補四例後殺 |
| 1-2 | G-C2、R-PH-37、AT-PH-06-2-E-1 | 既有檔 `si.static.test.ts` 的 hunk 只准在 `checkText` 第二分支與兩個新 it | 補「`checkText` 簽章與註解（:230-233）、樣板片段呼叫處（:243）」 | B 式 (ii) 的必要連動；一審 G-C2 裁決准許 |
| 1-3 | R-PH-21 突變欄 | 「`useParams`…」 | 改「`PageHelpButton` 改用 `useRouter().refresh()` 之類會在 layout 重掛載的寫法；殺手＝`layout.test`」 | `next/dynamic` 後 `DashboardView.test` 不渲染該鈕，原突變 M21a 不重現 |
| 1-4 | R-PH-23 突變欄 | 「`PageHelpDialog` 靜態 import recharts」 | 改「`TopRegion` 改回靜態 import `PageHelpButton`」 | 原突變 B23a 落在動態 chunk 內、Compare-RouteBundle 0 違規；B23b 21／21 路由超標（+102,746～+123,152 B） |
| 1-5 | R-PH-13 對照句 | 「對照（應存活）：…」 | 改寫為「輪 3 起由 AT-PH-04-6-2 殺（M13d 改「未結」label 即紅）」 | 輪 3 綁定後對照失效 |
| 1-6 | R-PH-09 突變欄 | 「放寬成 `Record<string,…>`」 | 改「改回型別註記（拿掉 `satisfies`）」 | `satisfies` 形態下原突變是等價突變（M09a、M09e 倖存）；M09d 由 tsc TS2344＋TS2578 殺 |
| 1-7 | R-PH-24 突變欄 | 「（`/login` 出現鈕）」 | 改「未登入於 `/projects` 出現鈕（殺手 AT-PH-01-2-1 (b)）」 | `helpForPath('/login')`＝null，原突變不重現 |
| 1-8 | §3.2 AT-PH-04-2-E-1 | 第二個 `@ts-expect-error` 字面 | 以 `Omit` 在合成型別上演示，實際鎖是 `keyof` 等式 | 實作揭露（輪 1a） |
| 1-9 | D-PH-3 | `StateSource` 住 `PageHelpDialog.tsx` | `StateSource` 定義在 `stateSources.ts`、由 `PageHelpDialog.tsx` re-export | 實作揭露（輪 1a／1b） |
| 1-10 | D-PH-17 | `ssr` 設定 | `ssr` 保持 `next/dynamic` 預設 true；hydration 無警告（AT-PH-07-1-2 主控台零錯誤） | 實作揭露（輪 1b） |
| 1-11 | G-F3 判準 | 「文字表含三列」 | 改用 `json-summary`（`lint.ts`、`stateSources.ts`、`registry.ts` 皆在 include） | text reporter 不列 100% 檔（F-10） |
| 1-12 | G-D1 判準 | `Select-String '本頁說明'` | 錨定「\| Top \|」列再判 | §3 目錄列也命中（F-09） |
| 1-13 | §3.2／§6.4 AT-PH-05-7-1 | 輪 2 綁定 | 註記「輪 1a 已建、輪 2 三個表單頁寫完才咬」 | 提早無害 |
| 1-14 | §2（:144）、§3.2 突變規格（:451） | 「frontend 副本以 junction 把 `node_modules` 指回工作樹」 | 補「junction 只夠 vitest／tsc；Playwright（dev）與 build 類突變須實體複製 `node_modules`」 | Turbopack 在 junction 副本 ENOENT build-manifest（OBS-SI-337） |
| 1-15 | §6.4 輪 3 | 綁定 AT 清單 | 補「AT-PH-04-6-2 由輪 3 在 `PageHelpDialog.test.tsx` 補 it（1b 交 HD 20 個，§3.1 預期 21）」 | 輪 3 偏離，一審裁決准許 |
| 1-16 | D-PH-8（:86）、§3.2 AT-PH-04-5-2 (c)（:550） | 「四群之一缺席」／「或 statuses 缺」 | 補「或任一群不是陣列、或 legend 不是物件」，並寫明例數：缺席四例、非陣列四例、legend 為 null 一例 | 二審 e-2：非陣列只給一例時其餘三群把 `Array.isArray` 放寬成 `!== undefined` 仍綠（Y01～Y03、Y05 倖存）；主控補例後 Y01 轉紅 |
| 1-17 | D-PH-13（:91）、§3.2 AT-PH-06-3-1／06-3-E-1 | 請求計數只寫新穎性規則 | 加註「詞表請求另以每路由自進路由起的全程計數判（含頁面載入；議題中心恰一、其餘零；VIEWER 每次開啟各一），不套新穎性規則」；反空轉改「clicked＋pending＝HELP_ROUTES 數、clicked＝已寫路由數；E-1 visited＝已寫路由數」 | 一審 F-05：單靠新穎性規則，非 issues 路由載入時預取只在排最後的 /issues 間接現形；二審 P22b 第一條路由即紅、Pskip3s／3e 證明新門檻嚴於 ≥3 |
| 1-18 | R-PH-18、R-PH-34、AT-PH-05-5-E-1 | 名稱 2 個 code point 免掃 | 明定「全站共通的名詞定義列（如「唯讀」＝VIEWER）可無逐字出處、取兩字名免掃是有意設計；此類列 `source` 寫「系統自動產生」並在 `common.ts` 檔頭寫 WHY；不得用來繞過有畫面字樣的欄位名」 | 二審 e-4／N04：該列的綠完全靠免鎖，需明文以免日後複製此手法繞過出處鎖 |
| 1-19 | §3.2 AC-PH-06-3（:383） | 載具只列 E2 | 註記「vitest 層無 AT、M22b（非 issues 路由 render 時預取）在 vitest 倖存為設計，由 e2e 的 P22b／P22e 殺」 | 二審 e-3；可選補 AT-PH-01-2-E-1「非 issues 路由 fetch 計數 0」另案 |
