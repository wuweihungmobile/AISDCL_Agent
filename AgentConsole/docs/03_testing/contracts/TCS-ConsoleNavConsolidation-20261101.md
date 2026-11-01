# Test Contract Specification — Console 側欄導覽整併（停用匯入入口、專案管理頁按鈕改名、顯示序重排）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole 前端導覽登記表；上位文件含 Console PRD §0.7、Architecture §5.4 與三份既有 TCS）的單一 Feature；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ConsoleNavConsolidation-20261101.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD 與根層 TCS）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-904 |
| **Feature 名稱** | Console 側欄導覽整併——`import` 列停用（側欄不顯示、頁面保留）、專案管理頁按鈕「匯入」改名「BRD/PRD 匯入」、顯示序改為 儀表板→專案管理→執行中心→監控中心→議題中心→自我進化→系統管理→系統設定 |
| **User Story** | US-918（主控已對 `AgentConsole/docs/06_quality/RTM.md` 與全 repo `docs/` 以 Grep 確認 F-904、US-918、AC-952 皆未被使用，不撞號） |
| **建立日期** | 2026-11-01 |
| **輸入快照** | HEAD＝`6dd910f03ee231e800adbbd74d6810030863b74e`；上位檔 digest 見〈增量追溯表〉（主控以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算；Console PRD §0.7、Architecture 三處訂正、IssueCenter TCS 勘誤 1-14、SysAdmin TCS 勘誤 1-36 已在工作樹，與本檔同一 commit 進） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝主控，實作者＝鍵 `agentconsole-nav-consolidation` 的開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-nav-consolidation`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug nav-consolidation`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature（上位文件＝根層 `docs/01_requirements/Agent_ConsoleUI_PRD.md`（v1.1.0＋§0.7 校正）、AgentConsole 的 Architecture（§5.1、§5.2 Tools 列、§5.4）、ADR-001、`TCS-SelfImprovingMirror-P1b-20261021.md`（R20～R22 登記表）、`TCS-IssueCenter-20261027.md`（R-IC-62；勘誤 1-14）、`TCS-SysAdminBackup-20261027.md`（R-BK-01；勘誤 1-36））。**凍結檔不得再改**：上位 TCS 的訂正只寫在各自〈勘誤〉表，走 refreeze；本檔為使其可測而補定義者，標「本檔類推」並列入 §7。**本鍵零 backend 改動、零 Bridge 改動、零根層碼改動。**

### FRD-lite

**背景（掌舵者 2026-11-01 指令，sid `655d9777-cfd0-4478-b2b3-b8245313b24c`）**：原文「UI優化整併, 請將左邊 Tools Bar的BRD/PRD匯入移除, 保留"專案管理/匯入", 將"匯入"改成"BRD/PRD匯入"」「UI Tools Bar 順序調整：1.儀錶板 2.專案管理 3.執行中心 4.監控中心 5.議題中心 6.自我進化 7.系統管理 8.系統設定」；主控以互動選項提問、掌舵者裁決：「執行中心」與「監控中心」功能不同（操作面 vs 觀察面）**兩者都保留**；側欄匯入入口移除、`/import` 頁保留並由專案管理頁按鈕進入。裁決全文與架構面見 Console PRD §0.7。

**現況與變更（Before／After；brownfield）**

- Before：(1) 導覽登記表 `frontend/lib/nav/registry.ts` 九列全部 `enabled: true`，`order` 為 dashboard 10、projects 20、import 30、execute 40、monitor 50、issues 55、settings 60、sysadmin 65、self-improving 70 ⇒ 側欄九項、序為 儀表板、專案管理、BRD/PRD 匯入、執行中心、監控中心、議題中心、系統設定、系統管理、自我進化；mobile 為 true 六項。(2) 專案管理頁右上的匯入連結文字為「匯入」（`ProjectsView.tsx`，`href="/import"`）。(3) 四個導覽測試檔共用快照 `tests/helpers/navDelivered.ts`（append-only；改既有列即紅，須同步）。
- After：(1) `import` 列 `enabled: false`（列、索引 2、`label`、`icon`、`href`、`match`、`order` 30、`mobile` 皆不變）；`settings` order 80、`sysadmin` order 75，其餘列各欄與索引不變 ⇒ 側欄八項、序為 儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定；mobile 為 true 的可見項五項（儀表板、專案管理、執行中心、監控中心、系統設定）。(2) 專案管理頁按鈕文字「BRD/PRD 匯入」，`href` 與圖示不變；空狀態文案「…或從「BRD/PRD 匯入」讓 AI 拆解」已與按鈕同名。(3) 快照與四個導覽測試檔、兩支 E2E spec 同步（只改預期值，不刪斷言）。
- **非目標**：不刪 `import` 列、不改 `/import` 頁與其頁面說明（`lib/help/import.ts`）、不改儀表板主按鈕「匯入 BRD / PRD」、不改 `ToolsRegion.tsx`／`layout.tsx`、不合併執行與監控兩頁、不補底部 Tab 第六項、不動 backend／Bridge／根層 `tools/`。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：本檔自增 AC 自 `AC-952-1` 起（dedupe 用到 `AC-951-6`，不撞號），共 4 個：952-1 登記表與側欄顯示序、952-2 專案管理頁按鈕、952-3 既有釘選與 E2E 同步、952-4 文件連動（V 系列）。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-952-1-1`→`AT_952_1_1`）。
4. **計數**：AC 4 個、AT 10 個（正控 7、負控 3）。

**本增量交付物**（D1～D5；路徑相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | 登記表改值 | `AgentConsole/frontend/lib/nav/registry.ts`（`import.enabled` false；`settings.order` 80；`sysadmin.order` 75；檔頭註解補「導覽整併 2026-11-01」與 WHY；其餘一字不動） | 開發 agent | AC-952-1 |
| D2 | 專案管理頁按鈕 | `AgentConsole/frontend/components/domain/views/ProjectsView.tsx`（連結文字「匯入」→「BRD/PRD 匯入」） | 開發 agent | AC-952-2 |
| D3 | 新 AT 檔 | `AgentConsole/frontend/lib/nav/nav-consolidation.test.ts`（AT-952-1-1～1-E-2）、`AgentConsole/frontend/components/domain/views/ProjectsView.nav.test.tsx`（AT-952-2-1、2-E-1；若 `ProjectsView` 已有測試檔則併入該檔） | 開發 agent | AC-952-1、952-2 |
| D4 | 既有釘選同步（只改預期值、不刪斷言；逐項見 §4） | §4 所列 7 筆 | 開發 agent | AC-952-3 |
| D5 | 文件連動（主控） | Console PRD §0.7 與 §8.1 註（已在工作樹）、Architecture §5.1／§5.2／§5.4（已在工作樹）、IssueCenter TCS 勘誤 1-14 與 SysAdmin TCS 勘誤 1-36（已在工作樹）、RTM 子表 `AgentConsole/docs/06_quality/RTM-ConsoleNav-20261101.md` 與 `RTM.md` §2.8 存根、SCG-4 報告 | 主控 | AC-952-4（V 系列） |

**提交順序與責任**

- D1 → D3（登記表 AT）→ D2 → D3（按鈕 AT）→ D4；每支完成即 `npx vitest run <檔>`，最後全套 `npx vitest run`、`npx tsc --noEmit`、`npm run lint` 三者皆 rc 0；E2E 兩支 spec 由主控於 Docker 全棧跑（§6.2 V2）。
- 開發 agent **不 commit／push**、不動 §5.7 集合以外的檔（鐵律 7）、不改 `ToolsRegion.tsx`；凍結檔與既有 TCS 不動。
- 真帳本、真 `~/.autosdd/` 一律唯讀。

**〈增量行為規則〉**（W-N1～W-N4；各 AT 以 W-N 編號引用。實查依據：`frontend/lib/nav/registry.ts`、`components/layout/ToolsRegion.tsx`、`components/domain/views/ProjectsView.tsx`、`tests/helpers/navDelivered.ts`、`lib/nav/{registry,issues-nav,sysadmin-nav}.test.ts`、`components/layout/ToolsRegion.test.tsx`、`tests/e2e/{shells-and-layout,p9-w7-ui}.spec.ts`）

- **W-N1 登記表**：`NAV_REGISTRY` 仍九列、陣列位置不變（`[2]` import、`[5]` settings、`[6]` self-improving、`[7]` issues、`[8]` sysadmin）；`import` 列 `enabled: false`，其餘欄位逐字不變（`label`「BRD/PRD 匯入」、`href` `/import`、`match` 以 `/import` 起頭、`order` 30、`mobile` true、`icon` Upload）；`settings.order` 80、`sysadmin.order` 75；其他七列各欄不變。`id`／`order` 唯一、`icon` 互異、`mobile: true` 總數 ≤ 6 的既有判準照舊。
- **W-N2 可見項與顯示序**：`visibleNavEntries(NAV_REGISTRY, role)` 對 ADMIN、OPERATOR、VIEWER 與 `undefined` 四種角色皆回八項，id 序恰為 `dashboard, projects, execute, monitor, issues, self-improving, sysadmin, settings`；不含 `import`。`activeNavEntry(visible, "/import")` 回 `null`（側欄無 active 項）；登記表層級 `import.match("/import")` 仍為真且只有它命中（`ownPathProblems` 空，互斥不變）。`ToolsRegion` 以真登記表渲染：主導覽恰八個連結、`aria-label` 序同上、無 name「BRD/PRD 匯入」的連結；`max-md:hidden` 恰在 議題中心、自我進化、系統管理 三項上。
- **W-N3 專案管理頁**：右上連結 `name`「BRD/PRD 匯入」、`href="/import"`、仍帶 Upload 圖示；頁內不存在 `name` 恰為「匯入」的連結；三種角色都看得到該連結（匯入頁的權限不在本鍵範圍）；空狀態文案含「BRD/PRD 匯入」。
- **W-N4 同步只增不減**：§4 所列既有測試的 diff 每個 hunk 只動預期值、標籤清單或快照列；被刪的 `expect` 行＝0；AT 標題與 id 不變。E2E：`shells-and-layout.spec.ts` 的導覽案例不再點側欄「BRD/PRD 匯入」，改為自 `/projects` 點按鈕「BRD/PRD 匯入」到 `/import`；`p9-w7-ui.spec.ts` 的側欄錨點改為八項（去掉「導航：BRD/PRD 匯入」）且專案管理頁右側錨點改為「BRD/PRD 匯入」。

### 增量追溯表（上位凍結檔；digest＝主控於工作樹現算，Stage-1 凍結由 CLI 重算為準）

| 上位檔 | 路徑（相對 monorepo 根） | sha256（本檔落檔時） |
|--------|--------------------------|---------------------|
| Console PRD v1.1.0＋§0.7 | `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `5d7b12c1431827e3b41af421110a04e96e2e12d881b09b18d34235177e5ee446` |
| Architecture（§5.1／§5.2／§5.4 訂正） | `AgentConsole/docs/02_architecture/Architecture.md` | `3dac8e2ad488d068646ba00e413c8b9b721346812af39719ced00f56992308c3` |
| ADR-001 | `AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md` | `ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38` |
| P1b TCS（R20～R22） | `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingMirror-P1b-20261021.md` | `0c8b854b287860f155ad0f30cfe08cf71aa74df90c768ced83476a2a8b224fd2` |
| IssueCenter TCS（勘誤 1-14） | `docs/03_testing/contracts/TCS-IssueCenter-20261027.md` | `50d41337de5d374b0568be1a09bf8c1adee35603f82ba9528ff0f80a2c296c30` |
| SysAdmin TCS（勘誤 1-36） | `AgentConsole/docs/03_testing/contracts/TCS-SysAdminBackup-20261027.md` | `1fc2f46bd4fc44bfe2e058b8a743c51507bbfe8280bdd135989ff25732260d2b` |

---

## 1. AC → AT 映射表

| AC | 說明 | 正控 AT | 負控／邊界 AT | 規則 |
|----|------|---------|---------------|------|
| AC-952-1 | 登記表改值與側欄顯示序 | AT-952-1-1、AT-952-1-2、AT-952-1-3 | AT-952-1-E-1、AT-952-1-E-2 | W-N1、W-N2 |
| AC-952-2 | 專案管理頁按鈕改名 | AT-952-2-1 | AT-952-2-E-1 | W-N3 |
| AC-952-3 | 既有釘選與 E2E 同步（只增不減） | AT-952-3-1、AT-952-3-2、AT-952-3-3 | — | W-N4 |
| AC-952-4 | 文件連動 | V 系列（§6.2） | — | PRD §0.7 |

**Given／When／Then**

- **AT-952-1-1**（FN，`lib/nav/nav-consolidation.test.ts`）Given 真 `NAV_REGISTRY` When 逐列讀欄位 Then `[2]` 為 import 且 `enabled` 為 false、其餘欄（label、href、order 30、mobile true）逐字同 W-N1；`settings.order` 80、`sysadmin.order` 75；dashboard 10、projects 20、execute 40、monitor 50、issues 55、self-improving 70；九列 id 依陣列序 dashboard、projects、import、execute、monitor、settings、self-improving、issues、sysadmin；id／order 唯一、icon 互異。
- **AT-952-1-2**（FN）Given 四種角色（ADMIN、OPERATOR、VIEWER、undefined）When `visibleNavEntries` Then 八項、id 序 `dashboard, projects, execute, monitor, issues, self-improving, sysadmin, settings`，不含 import；`DELIVERED_DISPLAY_IDS` 經過濾 enabled 後與之相等。
- **AT-952-1-3**（FT，`ToolsRegion.test.tsx` 新增 `it`）Given 真登記表、OPERATOR When 渲染 `ToolsRegion` Then 主導覽恰八個連結、`aria-label` 序為 儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定；`queryByRole("link", { name: "BRD/PRD 匯入" })` 為 null；`max-md:hidden` 恰在 議題中心、自我進化、系統管理；`ToolsRegion.tsx` 原始碼零差異（G-C3）。
- **AT-952-1-E-1**（FN）Given 可見項（OPERATOR）When `activeNavEntry(visible, "/import")` Then `null`；登記表層級以 `/import` 計算 match 的命中集合恰為 `["import"]`；`ownPathProblems`（沿 registry.test.ts 的判準）為空。
- **AT-952-1-E-2**（FN）Given `DELIVERED_NAV_ROWS` When 與 `NAV_REGISTRY` 前綴逐欄比對（id、label、order、mobile、enabled、roles）Then 相等；快照第 3 列 `enabled` 為 false、settings 80、sysadmin 75；mobile 為 true 的可見項恰五項（儀表板、專案管理、執行中心、監控中心、系統設定）。
- **AT-952-2-1**（FT，`ProjectsView` 測試）Given OPERATOR、空專案列表 When 渲染專案管理頁 Then 右上連結 `name`「BRD/PRD 匯入」、`href` `/import`、內含 svg；`queryByRole("link", { name: "匯入" })` 為 null；空狀態描述含「BRD/PRD 匯入」。
- **AT-952-2-E-1**（FT）Given VIEWER When 渲染 Then 該連結仍存在（文字與 href 同上）、「新建專案」按鈕為停用（既有行為不變）。
- **AT-952-3-1**（GT）Given `git diff -U0 <base> -- <§4 所列檔>` When 逐 hunk 檢視 Then 只動預期值、標籤清單、快照列與註解；被刪的 `expect`／`it` 行＝0；AT 標題與 id 不變；`ToolsRegion.tsx`、`layout.tsx`、`lib/help/**` 零差異。
- **AT-952-3-2**（E2E，Docker 全棧，`shells-and-layout.spec.ts`）Given 已登入 When 依序點側欄 系統設定、專案管理、儀表板，再自 `/projects` 點按鈕「BRD/PRD 匯入」Then 各到對應 URL 與標題（`/import` 標題「BRD / PRD 智能匯入」），四區塊各一份；側欄不存在「BRD/PRD 匯入」連結；執行中心／監控中心從專案進入的既有案例不變。
- **AT-952-3-3**（E2E，Docker 全棧，`p9-w7-ui.spec.ts`）Given 已登入 When 錨點檢查 Then 側欄錨點為八項且順序同 W-N2、無「導航：BRD/PRD 匯入」；專案管理頁右側錨點「BRD/PRD 匯入」存在、「匯入」（exact）不存在。

---

## 2. 可自動化 AT 格式規範

- frontend vitest：`it("AT_952_<AC>_<n> <中文描述>", …)`；FT 以 `@testing-library/react` 真渲染（沿 `ToolsRegion.test.tsx` 的 `Providers`＋`stubApi` 體例）；FN 直接 import `@/lib/nav/registry` 與 `@/tests/helpers/navDelivered`。
- E2E：Playwright 真後端 spec（`shells-and-layout.spec.ts`、`p9-w7-ui.spec.ts`）沿既有 `loginViaStorage`／`signIn` 與 `expectAnchors` 體例；mock spec 不受影響。
- GT：主控以 `git diff -U0` 對 §4 檔逐 hunk 人讀（SCG-4 報告附 hunk 清單）。

## 3. AT 完整清單

### 3.1 Unit／Component（vitest）
AT-952-1-1、AT-952-1-2、AT-952-1-E-1、AT-952-1-E-2（`lib/nav/nav-consolidation.test.ts`）；AT-952-1-3（`components/layout/ToolsRegion.test.tsx`）；AT-952-2-1、AT-952-2-E-1（`ProjectsView` 測試）。

### 3.2 Gate／靜態
AT-952-3-1（git diff 人讀；SCG-4 報告 §B）。

### 3.3 E2E
AT-952-3-2、AT-952-3-3（Docker 全棧；主控跑，結果寫 RTM E2E 欄）。

## 4. 需同步的既有測試（只改預期值，不刪斷言；每筆寫明「為何現值變了」）

| # | 檔 | 現釘值 | 改為 | 原因 |
|---|----|--------|------|------|
| 1 | `tests/helpers/navDelivered.ts` | import `enabled` true；settings 60；sysadmin 65 | import `enabled` false；settings 80；sysadmin 75（列序與其他欄不變） | W-N1；快照是四檔共用的唯一副本 |
| 2 | `lib/nav/sysadmin-nav.test.ts` | `[settings, sysadmin, self-improving].order` 為 `[60, 65, 70]`；逐欄快照 import enabled true、settings 60；「系統設定之後、自我進化之前」 | `[self-improving, sysadmin, settings].order` 為 `[70, 75, 80]`；快照同 #1；敘述改「自我進化之後、系統設定之前」 | SysAdmin TCS 勘誤 1-36 |
| 3 | `lib/nav/issues-nav.test.ts` | 顯示序「議題中心在監控中心之後、系統設定之前；系統管理在系統設定之後；自我進化最後」；快照 | 顯示序 議題中心→自我進化→系統管理→系統設定；快照同 #1 | IssueCenter TCS 勘誤 1-14 |
| 4 | `lib/nav/registry.test.ts` | `PATHS` 的 `/import` 期望 `import`（登記表層級 match，不受 enabled 影響）；AT_932_6_1 第七項斷言 | 不須改（若 `ids(delivered)` 類斷言因快照改動而紅，只改快照）；若新增斷言一律放新檔 | W-N2（match 互斥不變） |
| 5 | `components/layout/ToolsRegion.test.tsx` | AT_932_6_5 示範項註解「議題中心（55）之後、系統設定（60）之前」；AT_932_6_7 預期標籤序含「BRD/PRD 匯入」且系統設定在自我進化前；AT_932_6_8 以「BRD/PRD 匯入」當 mobile 改 false 的樣本 | 示範項位置改「議題中心之後、自我進化之前」（斷言改比 自我進化 的索引）；AT_932_6_7 標籤序去掉「BRD/PRD 匯入」並依新 order 排（儀表板、專案管理、同序後者、同序前者、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定 中屬該測試登記表者）；AT_932_6_8 的樣本改用「專案管理」 | W-N1、W-N2 |
| 6 | `tests/e2e/shells-and-layout.spec.ts` | 案例表含 `["BRD/PRD 匯入", /\/import$/, …]` 由側欄點 | 側欄案例改三項；`/import` 改自 `/projects` 點按鈕「BRD/PRD 匯入」 | W-N4 |
| 7 | `tests/e2e/p9-w7-ui.spec.ts` | 側欄錨點六項含「導航：BRD/PRD 匯入」；專案管理頁「右側：匯入」 | 側欄錨點八項（含議題中心、自我進化、系統管理；無匯入）依新序；「右側：BRD/PRD 匯入」 | W-N3、W-N4 |

## 5. 測試資料規格

### 5.1 常數
新 order 值：settings 80、sysadmin 75；可見序 `dashboard, projects, execute, monitor, issues, self-improving, sysadmin, settings`；mobile 可見五項。

### 5.7 hermetic 環境與允許變更的檔案集合（開發 agent 只准動這些檔）

- `AgentConsole/frontend/lib/nav/registry.ts`
- `AgentConsole/frontend/components/domain/views/ProjectsView.tsx`
- `AgentConsole/frontend/tests/helpers/navDelivered.ts`
- `AgentConsole/frontend/lib/nav/nav-consolidation.test.ts`（新）
- `AgentConsole/frontend/components/domain/views/ProjectsView.nav.test.tsx`（新；或併入既有 `ProjectsView` 測試檔）
- `AgentConsole/frontend/lib/nav/registry.test.ts`、`issues-nav.test.ts`、`sysadmin-nav.test.ts`
- `AgentConsole/frontend/components/layout/ToolsRegion.test.tsx`、`layout.test.tsx`（僅在因快照連動而紅時）
- `AgentConsole/frontend/tests/e2e/shells-and-layout.spec.ts`、`p9-w7-ui.spec.ts`
- 禁動：`ToolsRegion.tsx`、`layout.tsx`、`lib/help/**`（出處鎖以畫面字樣為準，本鍵的字樣變更不在任何說明欄位名內；若 `help.static.test.ts` 因此紅，回報主控、不自行改說明）、backend、engine-bridge、根層 `tools/`、`.claude/`、docs。

## 6. RTM 連結確認

### 6.1 追溯
RTM 子表 `AgentConsole/docs/06_quality/RTM-ConsoleNav-20261101.md`（10 列 AT＋V 系列）；`RTM.md` §2.8 存根連到它。

### 6.2 V 系列：實查檢核（主控、掌舵者；**不是 AT**）
- V1 真機：Docker 全棧重建 frontend 後，登入看側欄八項與順序、`/projects` 右上按鈕文字、`/import` 可達（主控 Playwright 探針或掌舵者目視）。
- V2 真機 E2E：`shells-and-layout.spec.ts`、`p9-w7-ui.spec.ts` 對 Docker 全棧跑綠。
- V3 文件：PRD §0.7、Architecture 三處、兩份 TCS 勘誤、RTM 子表與 §2.8 存根、三個上位鍵 refreeze（fsm-trail、issue-center、sysadmin-backup）皆已落地。

## 7. 本檔採用的預設裁決（主控依掌舵者授權裁決；掌舵者可推翻）

| ⚖ | 裁決 | WHY |
|----|------|-----|
| ⚖1 | `import` 列以 `enabled: false` 停用、不刪列 | 三份凍結 TCS 的「恰 N 項」與索引陳述全部維持真；`/import` 路由、match 認領與頁面說明不動；Architecture §5.4 本就預留此旗標 |
| ⚖2 | 只動 `settings`（60→80）與 `sysadmin`（65→75）兩個 order | 最小勘誤面即可得到掌舵者指定的序；其餘七列 order 不動 |
| ⚖3 | 底部 Tab 停用匯入後只剩五項，不補第六項 | 掌舵者未指示；補項是另一個產品決定 |
| ⚖4 | 儀表板主按鈕「匯入 BRD / PRD」不動 | 不在指令範圍；它與專案管理頁按鈕是 `/import` 的兩個入口 |
| ⚖5 | 停用列的 `mobile` 欄保留 true | 不渲染的列其 `mobile` 無效果；少動一欄即少一處快照差異 |

## 📋 SCG-4 通過標準

1. §3 全部 AT 綠（vitest 全套、tsc、lint rc 0；E2E 兩支對 Docker 全棧綠）。
2. §4 七筆同步只改預期值、零刪斷言（AT-952-3-1）。
3. §5.7 集合外零差異（`git diff --name-only` 核對）。
4. 文件連動全部落地（§6.2 V3）。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| 編號 | 位置 | 原文 | 改為 | 依據 |
|------|------|------|------|------|
| 1 | §4 #4 | 「預期不需改」 | `registry.test.ts` 的 AT_932_6_E_2 已知前綴迴圈：`/import` 及子路徑新期望 `null`（import 停用、不在可見項），其餘路徑仍等於舊 activeNav；改一行預期值 | 開發棒勘誤候選 1；QA 一審 F-03 |
| 2 | §4 #5 | 只列 AT_932_6_5／6_7／6_8 | 另列 AT_932_6_6（改比濾停用列的快照）、AT_932_6_8 前一個 it（同）、AT_932_6_9（`/import` 期望 none）、AT_BK_01_3_1（`DELIVERED_MOBILE_LABELS` 先濾停用列）；`issues-nav` AT_IC_11_1_E_1 的 `/import` 探針、`sysadmin-nav` AT_BK_01_1_1 的 order 75 屬 §4 #2／#3 的連動。根因＝`navDelivered.ts` 衍生常數不看 enabled，各消費檔以局部常數濾 enabled | 開發棒勘誤候選 2；QA F-03、F-05 |
| 3 | §6.1 | 「10 列 AT＋V 系列」 | 子表 16 列（F 1、US 1、AC 4、AT 10）；V1～V3 不入列 | QA F-03 |
| 4 | W-N3／AT-952-2-1、AT-952-2-E-1 | 「內含 svg」；「三種角色都看得到」 | AT-952-2-1 Then 加「svg 類別含 `lucide-upload`」（突變 Upload→Plus 須轉紅；主控已於實作 commit 後補斷言）；「三種角色」以 OPERATOR（2-1）與 VIEWER（2-E-1）釘住，ADMIN 走同一無條件渲染、不另立 AT | QA F-02（突變 m16 存活） |
| 5 | D1「其餘一字不動」 | issues／sysadmin 兩列行內註解仍寫舊 order 比較 | 允許同步這兩段註解為現值（主控已改），檔頭免責句刪除 | 開發棒勘誤候選 5；QA F-01 |
| 6 | W-N4「AT 標題與 id 不變」 | 既有 it 標題含「九個連結／九項／六項」等舊計數 | 刻意保留（與 OBS-SI-321 勘誤「AT 標題與 id 不變」同口徑；AT id 前綴是判定鍵）；現值由各檔檔頭註解與本 TCS W-N1／W-N2 給出 | QA F-04（P4） |
| 7 | AT-952-1-1／1-2／1-3 | 釘「恰九列／恰八項／恰八連結」 | 保留：本鍵的事實就是項數變動；日後登記表末尾加列時這三個 AT 隨之改（`nav-consolidation.test.ts` 檔頭已註明） | 開發棒勘誤候選 4 |
| 8 | IssueCenter TCS 勘誤 1-14、SysAdmin TCS 勘誤 1-36 的讀法 | 「mobile 為 true 的可見項 5」 | 欄位層級 mobile 為 true 仍 6（停用的 import 保留 mobile true，⚖5）；AT_IC_11_1_1／AT_BK_01_3_E_1 的「≤6」斷言不變 | QA 勘誤候選 5 |
| 9 | AT-952-3-3 | `p9-w7-ui.spec.ts` 對 Docker 全棧跑 | 該 spec 以 `test.skip(!E2E_ROOT)` 整檔閘住（需 Bridge 側 `E2E_ROOT` 全環境），本輪以拋棄式 Playwright 探針對 nginx 入口代驗同一組錨點（側欄八項序、無匯入入口、專案管理頁按鈕、`/import` 可達、390px 底部 Tab 五項）；spec 文字改法由 QA 靜態審閱 | V2 實跑限制（§6.2） |
