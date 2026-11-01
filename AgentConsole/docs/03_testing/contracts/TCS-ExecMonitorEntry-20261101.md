# Test Contract Specification — 執行中心／監控中心的無專案入口頁（`/execute`、`/monitor`）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole 前端導覽登記表、執行頁、監控頁、每頁說明；上位文件含 Console PRD §0.8、Architecture §5.1／§5.4、ADR-002 D3、P1b TCS R20～R22）的單一 Feature；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ExecMonitorEntry-20261101.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-905 |
| **Feature 名稱** | 執行中心／監控中心的無專案入口頁——側欄兩入口在沒有目的專案時退回 `/execute`／`/monitor`（說明＋專案選擇清單＋「新建專案」「BRD/PRD 匯入」動作），不再退回 `/projects` |
| **User Story** | US-919（主控已對 `AgentConsole/docs/06_quality/RTM.md` 與全 repo `docs/` 以 Grep 確認 F-905、US-919、AC-953 皆未被使用，不撞號） |
| **建立日期** | 2026-11-01 |
| **輸入快照** | HEAD＝`d09c251dcc3094027d4b9842768014c83689dfaa`；上位檔 digest 見〈增量追溯表〉（主控以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算；Console PRD §0.8＋§8.1 註、Architecture §5.1／§5.4、ADR-002 D3 訂正、P1b TCS 勘誤 26 已在工作樹，與本檔同一 commit 進） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝主控，實作者＝鍵 `agentconsole-exec-monitor-entry` 的開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-exec-monitor-entry`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug exec-monitor-entry`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature（上位文件＝根層 `docs/01_requirements/Agent_ConsoleUI_PRD.md`（v1.1.0＋§0.7、§0.8 校正）、AgentConsole 的 Architecture（§5.1 路由樹、§5.4 登記表形狀）、ADR-002（D3 訂正）、`TCS-SelfImprovingMirror-P1b-20261021.md`（R20～R22 登記表；勘誤 26））。**凍結檔不得再改**：上位 TCS 的訂正只寫在各自〈勘誤〉表，走 refreeze；本檔為使其可測而補定義者，標「本檔類推」並列入 §7。**本鍵零 backend 改動、零 Bridge 改動、零根層碼改動。**

### FRD-lite

**背景（掌舵者 2026-11-01 真機回報，sid `655d9777-cfd0-4478-b2b3-b8245313b24c`）**：原文「監控中心與執行中心UI無法執行? 請查看哪裡出錯並解決」。主控診斷（唯讀 Playwright 探針對 nginx 入口 `http://localhost`、nginx access log、資料庫查詢）：資料庫 `console.projects` 只有三筆且全為 `ARCHIVED`（E2E／QA 殘留），專案列表 API 回 0 筆 ⇒ `useCurrentProjectId()` 三層（網址 → 最近造訪 → 列表第一筆）皆空 ⇒ 側欄「執行中心」「監控中心」的 `href` 解析為 `/projects` ⇒ 點擊只落到專案管理頁的空狀態「還沒有任何專案」，網址／標題／active 項都是專案管理；兩個中心頁零請求、零錯誤、零 console 錯誤。nginx 記錄掌舵者 23:17～23:20 自儀表板多次落到 `/projects`。根因＝**設計上的靜默退回**（ADR-002 D3「都沒有退回 `/projects`」），不是程式錯誤；裁決全文見 Console PRD §0.8。

**現況與變更（Before／After；brownfield）**

- Before：(1) `frontend/lib/nav/registry.ts` 的 `execute`／`monitor` 兩列 `href(ctx)` 在 `currentProjectId` 為 null 時回 `/projects`；`match` 只認 `/projects/<id>/execute`、`/projects/<id>/monitor`。(2) 沒有 `/execute`、`/monitor` 路由。(3) 每頁說明登記表 `lib/help/registry.ts` 的 `HELP_ROUTES` 無這兩條路由（路由鎖＝`app/**/page.tsx` 全集，加頁不登記即紅）。(4) 三個導覽測試檔釘 `hrefNoProject` 為 `/projects`（`registry.test.ts` AT_932_6_1、`issues-nav.test.ts` AT_IC_11_1_E_1、`sysadmin-nav.test.ts` AT_BK_01_1_E_1）。
- After：(1) 兩列 `href(ctx)` 無專案時回 `/execute`／`/monitor`（有專案時不變）；`match` 加認精確路徑 `/execute`／`/monitor`（不認子路徑）；列數、索引、`order`、`mobile`、`enabled`、`label`、`icon` 皆不變。(2) 新路由 `app/execute/page.tsx`、`app/monitor/page.tsx`（只殼）組共用領域元件 `components/domain/entry/CenterEntryView.tsx`（`kind: "execute" | "monitor"`）。(3) 每頁說明新增 `execute-entry`、`monitor-entry` 兩條（頁檔、`HELP_PAGES`、`HELP_ROUTES`、`NO_STATE_PAGES`、`HelpId`）。(4) 三個導覽測試檔只改預期值；E2E `shells-and-layout.spec.ts` 加入口頁案例。
- **非目標**：不改 `ExecuteView`／`MonitorView`／`useCurrentProjectId`（三層解析不變）、不改 `ToolsRegion.tsx`／`layout.tsx`、入口頁**不自動跳轉**到任何專案、不做跨專案彙總、不動 backend／Bridge／根層 `tools/`。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：本檔自增 AC 自 `AC-953-1` 起（導覽整併用到 `AC-952-4`，不撞號），共 5 個：953-1 登記表退回與認領、953-2 入口頁、953-3 每頁說明接入、953-4 既有釘選與 E2E 同步、953-5 文件連動（V 系列）。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-953-1-1`→`AT_953_1_1`）。
4. **計數**：AC 5 個、AT 10 個（正控 8、負控 2）。

**本增量交付物**（D1～D6；路徑相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | 登記表退回與認領 | `AgentConsole/frontend/lib/nav/registry.ts`（`execute`／`monitor` 的 `href` 無專案分支改 `/execute`／`/monitor`；`match` 加 `pathname === "/execute"`／`"/monitor"`；檔頭規則第 4 點與兩列行內註解改為現值；其餘列一字不動） | 開發 agent | AC-953-1 |
| D2 | 入口頁 | `AgentConsole/frontend/app/execute/page.tsx`、`app/monitor/page.tsx`（只殼；`metadata.title` 分別「執行中心」「監控中心」）、`components/domain/entry/CenterEntryView.tsx`（新；W-E1） | 開發 agent | AC-953-2 |
| D3 | 每頁說明接入 | `AgentConsole/frontend/lib/help/types.ts`（`HelpId` 加 `"execute-entry"`、`"monitor-entry"`）、`lib/help/execute-entry.ts`、`lib/help/monitor-entry.ts`（新）、`lib/help/registry.ts`（`HELP_PAGES` 加兩鍵、`HELP_ROUTES` 加 `"/execute"`、`"/monitor"`、`NO_STATE_PAGES` 加兩 id） | 開發 agent | AC-953-3 |
| D4 | 新 AT 檔 | `AgentConsole/frontend/lib/nav/exec-monitor-entry.test.ts`（AT-953-1-1、1-2、1-E-1、3-1）、`AgentConsole/frontend/components/domain/entry/CenterEntryView.test.tsx`（AT-953-2-1、2-2、2-3、2-E-1） | 開發 agent | AC-953-1～3 |
| D5 | 既有釘選同步（只改預期值、不刪斷言；逐項見 §4） | §4 所列 6 筆 | 開發 agent | AC-953-4 |
| D6 | 文件連動（主控） | Console PRD §0.8 與 §8.1 註、Architecture §5.1／§5.4、ADR-002 D3 訂正、P1b TCS 勘誤 26（皆已在工作樹）、RTM 子表 `AgentConsole/docs/06_quality/RTM-ExecMonitorEntry-20261101.md` 與 `RTM.md` §2.9 存根、SCG-4 報告、五個上位鍵 refreeze | 主控 | AC-953-5（V 系列） |

**提交順序與責任**

- D1 → D4（登記表 AT）→ D2 → D4（元件 AT）→ D3 → D4（說明 AT）→ D5；每支完成即 `npx vitest run <檔>`，最後全套 `npx vitest run`、`npx tsc --noEmit`、`npm run lint` 三者皆 rc 0；E2E 由主控於 Docker 全棧跑（§6.2 V2）。
- 開發 agent **不 commit／push**、不動 §5.7 集合以外的檔（鐵律 7）、不改 `ToolsRegion.tsx`、`ExecuteView.tsx`、`MonitorView.tsx`、`useCurrentProjectId.ts`；凍結檔與既有 TCS 不動。
- 真帳本、真 `~/.autosdd/` 一律唯讀。

**〈增量行為規則〉**（W-E1～W-E5；各 AT 以 W-E 編號引用。實查依據：`frontend/lib/nav/registry.ts`、`hooks/useCurrentProjectId.ts`、`components/layout/ToolsRegion.tsx`、`components/domain/views/ProjectsView.tsx`（動作按鈕與空狀態體例）、`components/ui/states.tsx`（`EmptyState`／`ErrorState`／`PageSkeleton`）、`lib/api/queries.ts`（`useAllProjects`）、`lib/help/{registry,types}.ts`、`lib/help/registry.test.ts`、`tests/e2e/shells-and-layout.spec.ts`）

- **W-E1 入口頁**：`CenterEntryView({ kind })` 渲染 `<div data-testid="center-entry-view" data-kind={kind}>`：(a) `PageTitle`：icon `Play`（execute）／`Activity`（monitor），title「執行中心」／「監控中心」，subtitle「以專案為單位 · 選擇專案進入它的執行頁」／「以專案為單位 · 選擇專案進入它的監控頁」；`actions`＝兩顆動作：「BRD/PRD 匯入」（`Button asChild variant="ghost" iconLeft={Upload}` 包 `<Link href="/import">`；三種角色皆顯示）與「新建專案」（`canWrite` 時 `Button asChild iconLeft={Plus}` 包 `<Link href="/projects/new">`；否則同文字的 `Button` `disabled` 且 `title="權限不足（唯讀角色）"`，不渲染連結）。(b) 一段說明 `<p data-testid="entry-intro">`：execute＝「執行中心以專案為單位：每個專案有自己的執行頁（啟動、暫停、恢復、取消批次與審核）。請從下面選擇一個專案進入；還沒有專案時，先新建專案或從 BRD/PRD 匯入。」monitor＝「監控中心以專案為單位：每個專案有自己的監控頁（指標、趨勢、日誌、告警）。請從下面選擇一個專案進入；還沒有專案時，先新建專案或從 BRD/PRD 匯入。」(c) 資料來源＝`useAllProjects()`（與側欄 rail、儀表板同一份快取；最多 100 筆、更新時間新到舊；不另加端點）。`isPending && !data` → `PageSkeleton`；`isError && !data` → `ErrorState title="無法載入專案列表"`（重試呼叫 `refetch`）；`data.content` 為空 → `EmptyState title="還沒有任何專案"`、description＝「執行中心需要一個專案。先按「新建專案」，或從「BRD/PRD 匯入」讓 AI 拆解，建立後再回到這裡選擇它進入。」（monitor 把「執行中心」換成「監控中心」）；非空 → `<ul role="list" aria-label="選擇專案" data-testid="entry-project-list">`，每筆 `<li>` 內一個 `<Link href={`/projects/${p.id}/${kind}`} aria-label={p.name}>`，內容＝`StatusDot`（`projectStatus(p.status).color`）＋專案名＋狀態標籤（`projectStatus(p.status).label`，置於 `aria-hidden` 容器內，使連結可及名稱恰為專案名），順序同 API。(d) 入口頁**不**呼叫任何 mutation、**不**自動 `router.push`、不記住專案（記住由專案頁的 `useCurrentProjectId` 負責）。(e) 頁面殼 `app/execute/page.tsx`／`app/monitor/page.tsx` 只 `export const metadata` 與 `export default function` 回傳 `<CenterEntryView kind="…" />`（Architecture §5.4 檢查表第 1 項：不 import 四區塊元件）。
- **W-E2 登記表**：`execute.href(ctx)`＝`ctx.currentProjectId ? "/projects/<id>/execute" : "/execute"`；`monitor` 同理為 `/monitor`。`execute.match(p)`＝`EXECUTE.test(p) || p === "/execute"`；`monitor.match(p)`＝`MONITOR.test(p) || p === "/monitor"`；`/execute/x`、`/executes`、`/monitoring` 都不認；`projects.match` 不變（本就不以 `/execute` 起頭）。登記表仍九列、索引不變、`order`／`mobile`／`enabled`／`label`／`icon` 不變（`DELIVERED_NAV_ROWS` 快照不變）。既有 `ownPathProblems` 判準（每項自己的頁面恰被該項認領）仍為空，且入口路徑 `/execute`／`/monitor` 各恰被一項認領。
- **W-E3 每頁說明**：`HelpId` 加 `"execute-entry"`、`"monitor-entry"`；兩個頁檔 `title` 分別「執行中心」「監控中心」（固定頁名）、`purpose` 二～三句、`steps` 三句、`fields` 三項（名稱逐字＝畫面字樣「新建專案」「BRD/PRD 匯入」「選擇專案」，`sourceFiles` 含 `components/domain/entry/CenterEntryView.tsx`）、`states` 為空並列入 `NO_STATE_PAGES`；`HELP_PAGES` 加兩鍵；`HELP_ROUTES` 加 `"/execute": "execute-entry"`、`"/monitor": "monitor-entry"`；`PENDING_HELP_PAGES` 維持空、`PENDING_CEILING` 維持 0（直接寫實，不走 pending）。`lib/help/registry.test.ts` 與 `help.static.test.ts` 的三道雙向鎖與靜態規則全綠。
- **W-E4 同步只增不減**：§4 所列既有測試的 diff 每個 hunk 只動預期值、探針列或註解；被刪的 `expect` 行＝0；AT 標題與 id 不變。E2E：`shells-and-layout.spec.ts` 第一個測試加入口頁案例（深連結 `/execute`、`/monitor`：標題、`center-entry-view`、清單含該測試專案名稱的連結、點擊到 `/projects/<id>/execute`／`/monitor`、側欄該中心 `aria-current="page"`）；既有「從專案進入」案例不變。
- **W-E5 不變量**：`useCurrentProjectId` 三層解析不變，所以有專案時側欄兩入口仍直達該專案頁，入口頁只在深連結或零專案時出現；`ExecuteView`／`MonitorView` 零差異。

### 增量追溯表（上位凍結檔；digest＝主控於工作樹現算，Stage-1 凍結由 CLI 重算為準）

| 上位檔 | 路徑（相對 monorepo 根） | sha256（本檔落檔時） |
|--------|--------------------------|---------------------|
| Console PRD v1.1.0＋§0.7、§0.8 | `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `29807d7f5f7c4439a33a665214caa016524753a9ebd678e7ce496f0a80802988` |
| Architecture（§5.1 路由樹、§5.4 href 註） | `AgentConsole/docs/02_architecture/Architecture.md` | `696bd3fb578b0f65a11d5f3fdc110bea1763d40e0b4e81a661e9c2aadb014287` |
| ADR-002（D3 訂正） | `AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md` | `b0897c536bdbce19efc21bf0762240f22e054fc4ff03882276fa0ed59da6066d` |
| P1b TCS（R20～R22；勘誤 26） | `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingMirror-P1b-20261021.md` | `7482fa275c452f82634edc9f508d2b550a9c7ceb5e0ab5535dfefa299c1a5777` |

---

## 1. AC → AT 映射表

| AC | 說明 | 正控 AT | 負控／邊界 AT | 規則 |
|----|------|---------|---------------|------|
| AC-953-1 | 登記表：無專案退回入口頁、入口路徑認領 | AT-953-1-1、AT-953-1-2 | AT-953-1-E-1 | W-E2 |
| AC-953-2 | 入口頁三態（空／有專案／載入與錯誤）與動作 | AT-953-2-1、AT-953-2-2、AT-953-2-3 | AT-953-2-E-1 | W-E1 |
| AC-953-3 | 每頁說明接入 | AT-953-3-1 | — | W-E3 |
| AC-953-4 | 既有釘選與 E2E 同步（只增不減） | AT-953-4-1、AT-953-4-2 | — | W-E4 |
| AC-953-5 | 文件連動 | V 系列（§6.2） | — | PRD §0.8 |

**Given／When／Then**

- **AT-953-1-1**（FN，`lib/nav/exec-monitor-entry.test.ts`）Given 真 `NAV_REGISTRY` When `navHref(execute, { currentProjectId: null })`／`navHref(monitor, …)` Then 分別為 `/execute`、`/monitor`；`{ currentProjectId: "p1" }` 時分別為 `/projects/p1/execute`、`/projects/p1/monitor`（不變）。
- **AT-953-1-2**（FN）Given OPERATOR 可見項 When `activeNavEntry(visible, "/execute")`／`"/monitor"` Then id 分別為 `execute`、`monitor`；登記表層級以 `/execute` 計算 match 的命中集合恰為 `["execute"]`、`/monitor` 恰為 `["monitor"]`；`/execute/x`、`/executes`、`/monitoring` 的命中集合為空（`activeNavEntry` 回 null）；沿 `registry.test.ts` 的 `ownPathProblems` 判準對真登記表為空。
- **AT-953-1-E-1**（FN）Given 真登記表 When 逐列比對 `DELIVERED_NAV_ROWS` 前綴（id、label、order、mobile、enabled、roles）Then 相等（本鍵不改任何快照欄）；`projects.match("/execute")`、`projects.match("/monitor")` 為 false；`/projects/p1/execute` 的命中集合仍恰為 `["execute"]`。
- **AT-953-2-1**（FT，`components/domain/entry/CenterEntryView.test.tsx`；兩個 kind 各跑一次）Given OPERATOR、專案列表 API 回空頁 When 渲染 `CenterEntryView` Then `data-testid="center-entry-view"` 的 `data-kind` 為該 kind；標題「執行中心」／「監控中心」；`entry-intro` 文字含「以專案為單位」；`EmptyState` 標題「還沒有任何專案」且描述含「新建專案」與「BRD/PRD 匯入」；連結「新建專案」`href` `/projects/new`、連結「BRD/PRD 匯入」`href` `/import`；`queryByRole("list")` 為 null。
- **AT-953-2-2**（FT；兩個 kind）Given OPERATOR、API 回兩個專案（名稱 Alpha、Beta，狀態各異）When 渲染 Then `getByRole("list", { name: "選擇專案" })` 內恰兩個連結，可及名稱依序 Alpha、Beta，`href` 分別為 `/projects/<idA>/<kind>`、`/projects/<idB>/<kind>`；每個 `<li>` 內有狀態標籤文字（`projectStatus(status).label`）；不渲染 `EmptyState`。
- **AT-953-2-3**（FT）Given API 永不回應 When 渲染 Then 顯示 `PageSkeleton`、無清單、無空狀態；Given API 回 500 When 渲染 Then `ErrorState` 標題「無法載入專案列表」，按「重試」後再呼叫一次列表 API（請求計數 1→2）。
- **AT-953-2-E-1**（FT）Given VIEWER、API 回空頁 When 渲染 Then 「新建專案」為停用按鈕（`disabled`，`title` 含「權限不足」）且頁內無 `href` 為 `/projects/new` 的連結；「BRD/PRD 匯入」連結仍存在；空狀態照常。
- **AT-953-3-1**（FN，`exec-monitor-entry.test.ts`）Given `lib/help/registry.ts` When 讀 `HELP_ROUTES`／`HELP_PAGES`／`NO_STATE_PAGES` Then `HELP_ROUTES["/execute"]` 為 `execute-entry`、`["/monitor"]` 為 `monitor-entry`；`helpForPath("/execute").id` 與 `helpForPath("/monitor").id` 同上；兩 id 皆在 `HELP_PAGES` 且 `title` 分別「執行中心」「監控中心」、`states` 為空、皆在 `NO_STATE_PAGES`；`PENDING_HELP_PAGES` 為空。
- **AT-953-4-1**（GT）Given `git diff -U0 <base> -- <§4 所列檔>` When 逐 hunk 檢視 Then 只動預期值、探針列、快照列與註解；被刪的 `expect`／`it` 行＝0；AT 標題與 id 不變；`ToolsRegion.tsx`、`layout.tsx`、`ExecuteView.tsx`、`MonitorView.tsx`、`useCurrentProjectId.ts` 零差異。
- **AT-953-4-2**（E2E，Docker 全棧，`shells-and-layout.spec.ts`）Given 已登入、該測試已建立專案 `name` When `page.goto("/execute")` Then 標題「執行中心」可見、`center-entry-view` 可見、側欄「執行中心」`aria-current="page"`、清單中名為 `name` 的連結存在，點擊後 URL 為 `/projects/<id>/execute` 且 `execute-view` 可見；`/monitor` 同理到 `/projects/<id>/monitor` 且 `monitor-view` 可見；四區塊各一份；既有「從專案進入」案例不變。

---

## 2. 可自動化 AT 格式規範

- frontend vitest：`it("AT_953_<AC>_<n> <中文描述>", …)`；FT 以 `@testing-library/react` 真渲染（沿 `ProjectsView.test.tsx`／`ToolsRegion.test.tsx` 的 `Providers`＋`stubApi` 體例，`useAuth` 以既有測試助手注入角色）；FN 直接 import `@/lib/nav/registry`、`@/lib/help/registry`、`@/tests/helpers/navDelivered`。
- E2E：Playwright 真後端 spec（`shells-and-layout.spec.ts`）沿既有 `loginViaStorage` 體例；mock spec 不受影響。
- GT：主控以 `git diff -U0` 對 §4 檔逐 hunk 人讀（SCG-4 報告附 hunk 清單）。

## 3. AT 完整清單

### 3.1 Unit／Component（vitest）
AT-953-1-1、AT-953-1-2、AT-953-1-E-1、AT-953-3-1（`lib/nav/exec-monitor-entry.test.ts`）；AT-953-2-1、AT-953-2-2、AT-953-2-3、AT-953-2-E-1（`components/domain/entry/CenterEntryView.test.tsx`）。

### 3.2 Gate／靜態
AT-953-4-1（git diff 人讀；SCG-4 報告 §B）。

### 3.3 E2E
AT-953-4-2（Docker 全棧；主控跑，結果寫 RTM E2E 欄）。

## 4. 需同步的既有測試（只改預期值，不刪斷言；每筆寫明「為何現值變了」）

| # | 檔 | 現釘值 | 改為 | 原因 |
|---|----|--------|------|------|
| 1 | `lib/nav/registry.test.ts` | AT_932_6_1 `navHref(entry, { currentProjectId: null })` 為 `/projects`；AT_932_6_3 代表路徑探針表無 `/execute`、`/monitor`；`ownPath` 註解「無專案時退回 /projects 是別項的頁面」 | 預期改為 `/${id}`（`/execute`／`/monitor`）；探針表加 `["/execute", "execute"]`、`["/monitor", "monitor"]`（互斥判準自動涵蓋）；註解改為現值 | W-E2；P1b TCS 勘誤 26 |
| 2 | `lib/nav/issues-nav.test.ts` | AT_IC_11_1_E_1 快照 execute／monitor 的 `hrefNoProject: "/projects"`；探針表 | `hrefNoProject` 改 `/execute`／`/monitor`；探針表加 `["/execute", "execute"]`、`["/monitor", "monitor"]` | 同上 |
| 3 | `lib/nav/sysadmin-nav.test.ts` | AT_BK_01_1_E_1 快照同 #2 | 同 #2 | 同上 |
| 4 | `lib/help/registry.test.ts` | 路由鎖母體＝`app/**/page.tsx`；頁數相關斷言（若有「十八頁」字樣或計數） | 預期不需改（`HELP_ROUTES` 加兩鍵即綠）；若有頁數釘值改為二十；`PENDING_CEILING` 維持 0 | W-E3 |
| 5 | `components/layout/ToolsRegion.test.tsx`、`layout.test.tsx` | 以 `navHref` 推導預期 | 預期不需改；紅了只改預期值 | W-E2 |
| 6 | `tests/e2e/shells-and-layout.spec.ts` | 第一個測試無入口頁案例 | 加入口頁案例（AT-953-4-2）；既有案例不動 | W-E4 |

`tests/helpers/navDelivered.ts`（無 href 欄）、`tests/e2e/p9-w7-ui.spec.ts`（錨點不變）不改。

## 5. 測試資料規格

### 5.1 常數
入口路徑 `/execute`、`/monitor`；說明 id `execute-entry`、`monitor-entry`；清單 `aria-label`「選擇專案」；空狀態標題「還沒有任何專案」；錯誤標題「無法載入專案列表」；唯讀停用提示「權限不足（唯讀角色）」。

### 5.7 hermetic 環境與允許變更的檔案集合（開發 agent 只准動這些檔）

- `AgentConsole/frontend/lib/nav/registry.ts`
- `AgentConsole/frontend/app/execute/page.tsx`、`app/monitor/page.tsx`（新）
- `AgentConsole/frontend/components/domain/entry/CenterEntryView.tsx`（新）、`CenterEntryView.test.tsx`（新）
- `AgentConsole/frontend/lib/nav/exec-monitor-entry.test.ts`（新）
- `AgentConsole/frontend/lib/help/types.ts`、`lib/help/registry.ts`、`lib/help/execute-entry.ts`（新）、`lib/help/monitor-entry.ts`（新）
- `AgentConsole/frontend/lib/nav/registry.test.ts`、`issues-nav.test.ts`、`sysadmin-nav.test.ts`
- `AgentConsole/frontend/lib/help/registry.test.ts`、`components/layout/ToolsRegion.test.tsx`、`layout.test.tsx`（僅在因連動而紅時）
- `AgentConsole/frontend/tests/e2e/shells-and-layout.spec.ts`
- 禁動：`ToolsRegion.tsx`、`layout.tsx`、`ExecuteView.tsx`、`MonitorView.tsx`、`hooks/useCurrentProjectId.ts`、`lib/nav/lastProject.ts`、`lib/api/**`、backend、engine-bridge、根層 `tools/`、`.claude/`、docs。

## 6. RTM 連結確認

### 6.1 追溯
RTM 子表 `AgentConsole/docs/06_quality/RTM-ExecMonitorEntry-20261101.md`（17 列：F 1、US 1、AC 5、AT 10）；`RTM.md` §2.9 存根連到它。

### 6.2 V 系列：實查檢核（主控、掌舵者；**不是 AT**）
- V1 真機：Docker 全棧重建 frontend 後，以掌舵者的零專案資料庫狀態登入，點側欄「執行中心」「監控中心」各落到 `/execute`、`/monitor`，看到標題、說明、空狀態與兩顆動作，側欄該中心為 active（主控 Playwright 探針或掌舵者目視）。
- V2 真機 E2E：`shells-and-layout.spec.ts` 對 Docker 全棧跑綠（含新案例）。
- V3 文件：PRD §0.8 與 §8.1 註、Architecture §5.1／§5.4、ADR-002 D3 訂正、P1b TCS 勘誤 26、RTM 子表與 §2.9 存根、五個上位鍵 refreeze（fsm-trail、nav-consolidation、si-mirror、si-decide、si-decide-dedupe）皆已落地。

## 7. 本檔採用的預設裁決（主控依掌舵者授權裁決；掌舵者可推翻）

| ⚖ | 裁決 | WHY |
|----|------|-----|
| ⚖1 | 無專案時退回**入口頁**，不是在 `/projects` 加提示橫幅 | 網址、標題、側欄 active 都指向該中心，使用者一眼知道自己在哪、為何要先選專案；橫幅留在專案管理頁仍會讓人以為「執行中心」只是跳到專案列表 |
| ⚖2 | 入口頁**不自動跳轉**到第一個專案 | 有專案時側欄已由 `useCurrentProjectId` 直達該專案頁，入口頁只在深連結或零專案時出現；自動跳轉使「選擇」消失、也難以測試與解釋 |
| ⚖3 | 單一共用元件 `CenterEntryView(kind)` | 兩頁只差標題、圖示、目的路徑與一句說明；兩份元件＝兩份要同步的真相 |
| ⚖4 | 每頁說明新增 `execute-entry`／`monitor-entry`，不沿用 `execute`／`monitor` | 既有兩條說明描述專案頁的欄位與狀態，入口頁沒有那些欄位；沿用會讓「本頁說明」講錯頁 |
| ⚖5 | VIEWER 的「新建專案」停用不隱藏；「BRD/PRD 匯入」三角色皆顯示 | 與專案管理頁一致（`ProjectsView` 的按鈕體例；導覽整併 TCS W-N3 同口徑：匯入頁自管權限） |
| ⚖6 | `match` 只認精確 `/execute`／`/monitor`，不認子路徑 | 入口頁沒有子頁；精確比對避免 `/executeX` 之類誤認，也讓互斥判準最簡單 |
| ⚖7 | 清單沿用 `useAllProjects` 的 100 筆上限、不分頁、不搜尋 | 與側欄 rail 同一份快取、零新端點；超過 100 個專案時從專案管理頁搜尋後由專案頁進入（說明頁 steps 寫明） |

## 📋 SCG-4 通過標準

1. §3 全部 AT 綠（vitest 全套、tsc、lint rc 0；E2E 對 Docker 全棧綠）。
2. §4 六筆同步只改預期值、零刪斷言（AT-953-4-1）。
3. §5.7 集合外零差異（`git diff --name-only` 核對）。
4. 文件連動全部落地（§6.2 V3）。

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| 編號 | 位置 | 原文 | 改為 | 依據 |
|------|------|------|------|------|
