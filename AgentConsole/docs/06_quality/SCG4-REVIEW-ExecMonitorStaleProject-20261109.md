# SCG-4 一審：DEF-AC-035 修復（commit 69a25b89，BASE 521c47f4）

## A 摘要與判定
判定：PASS（P1 0／P2 0／P3 1／P4 2）。突變 11 個：KILLED 10、SURVIVED 1（M10，等價於暫態，列 P3）。

## B 發現表
- F-01 P3：純函式 `resolveCurrentProjectId` 的「stale 時退列表第一筆」未被獨立斷言（M10：stale 時回 null 而非 first，全部測試仍綠）。最終畫面等價（遺忘後重算即得 first，只差一個 render 的暫態）。建議補一條純函式斷言：`last:"b"`、page 非空且不含 b ⇒ `{id:<first>, stale:true}`。
- F-02 P4：任務書計數（AT 22／30 列／RTM 12 列）與落檔（AT 21／29 列／RTM 11 列）不符；任務書把 AT 編號多算一個（6-1～6-9＋6-E-1＝10 個編號，非 11），落檔內部一致（TCS 勘誤 15、RTM 11 列皆 🟡）。裁決偏離，非缺陷。
- F-03 P4：三處開發棒偏離（W-E8 落在 ProjectDetailView、D-P1-4 不加文案、純函式留在 lastProject.ts）核實屬實，已寫入勘誤 11／12。

## C AT 逐條（單跑形態 `npx vitest run <檔> -t 953_6`，副本 HEAD，rc=0，14 passed）
| AT | 實作 | 測試 | 判定 |
|---|---|---|---|
| 6-1 | lib/nav/lastProject.ts resolveCurrentProjectId＋hooks/useCurrentProjectId.ts 遺忘 effect | hooks/useCurrentProjectId.test.tsx::AT_953_6_1 | PASS（M1／M8 殺） |
| 6-2 | 同上 | ::AT_953_6_2 | PASS |
| 6-3 | 同上 | ::AT_953_6_3 | PASS（M2 殺） |
| 6-4 | 同上 | ::AT_953_6_4（fetch 永不回應） | PASS |
| 6-5 | ExecuteView.tsx 404 分支＋ProjectGoneState.tsx | ExecuteView.test.tsx::AT_953_6_5 | PASS（M3／M4a／M6／M9） |
| 6-6 | MonitorView.tsx 404 分支 | MonitorView.test.tsx::AT_953_6_6 | PASS |
| 6-7 | 既有 ErrorState 未動 | 兩檔各 AT_953_6_7（500） | PASS（M4a／M4b 殺） |
| 6-8 | ProjectDetailView.tsx forgetProjectId | ProjectDetailView.forget.test.tsx::AT_953_6_8 | PASS，裁決偏離（落點由 ProjectsView 改詳情頁；刪除入口確在詳情頁，推論依 diff 與測試能點「刪除專案」） |
| 6-E-1 | ProjectGoneState.tsx | ProjectGoneState.test.tsx（含 VIEWER／OPERATOR） | PASS（M6／M7／M9） |
| 6-9 | — | tests/e2e/shells-and-layout.spec.ts 新增案例；apiDelete／apiPost／loginViaStorage／token 皆已存在 | 靜態正確，真機由主控跑（NOT-EVALUABLE 於本鏡） |

## D 突變（HEAD 副本，各自跑 5 個相關測試檔，每次還原）
M1 存在性判斷拿掉 KILLED；M2 不完整列表也遺忘 KILLED；M3 gone 漏 forget KILLED；M4a Execute 任何 ApiError 都 gone KILLED；M4b Monitor 同 KILLED；M5 刪除成功不遺忘 KILLED；M6 gone 多重試鈕 KILLED；M7 forget 不判相等 KILLED；M8 hook 不執行遺忘 KILLED；M9 入口連結固定 /execute KILLED；M10 stale 不退第一筆 SURVIVED（F-01）。

## E 接縫
- `git diff --name-only 521c47f4..69a25b89` 對 components/layout（ToolsRegion）、lib/nav/registry.ts、app（layout.tsx）零輸出；lib/help 零 diff。
- MonitorView 既有 `if (project.isError)` 條件未改，僅其內插入 404 前置判斷；ExecuteView 同（`isError && !data` 內）。
- expect／it 數：ExecuteView.test 183→193／41→43；MonitorView.test 178→188／39→41。
- 15 個修復檔 CR 計數全為 0（LF）。

## F 文件對照
TCS 勘誤 11～15 落檔且與實作一致（含上述偏離說明）；PRD §0.8 第 4 點落檔；RTM 子表追加 11 列，皆 🟡（AC-953-6＋10 AT）。

## G 誠實劃界
未跑全套 vitest／tsc／lint（主控已跑）；未跑真後端 E2E；未驗證效應順序競態（側欄 remember effect 與 gone 元件 forget effect 的先後）——推論：即使 remember 後到，側欄在列表完整時由 W-E6 再遺忘，影響僅限列表不完整（>100 筆）時多一次補救畫面，屬設計內。副本已刪除，工作樹未動。

## 主控補記（2026-11-09 11:4x +08:00；一審 PASS 後的收尾，主控親跑）

- **F-01（P3）已補**：`hooks/useCurrentProjectId.test.tsx` 純函式 describe 新增 it「AT_953_6_1 純函式：最近造訪不在已載入且完整的列表內時，退到列表第一筆並標 stale」（含列表不完整時 `{id:"b",stale:false}` 的對照）。突變 M10 重放（`lastProject.ts` 的 stale 分支改回傳 `last`）：該檔 `Tests 2 failed | 4 passed`（新 it 與既有純函式 it 同時轉紅）；逐字還原後 `6 passed`。
- **AT-953-6-9 入口頁斷言收緊**：`toHaveURL(/\/monitor$/)` 改 `/^https?:\/\/[^/]+\/monitor$/`（`/projects/<id>/monitor` 尾段同為 `/monitor`）；TCS 勘誤 16 登記。
- **真機（Docker 全棧、frontend 映像重建後經 nginx 80）**：V2 `npx playwright test tests/e2e/shells-and-layout.spec.ts -g AT-953-6-9`（`E2E_WEB_PORT=80`、`E2E_API_URL=http://localhost`）1 通過（rc 0）；V1 探針 `scratchpad\p1\probe_gone.cjs`（記住已刪除專案 `af0cdcc1-8c41-41dc-a545-49b929136d76` 後）：側欄兩入口 href `/execute`／`/monitor`、最近造訪鍵被遺忘、直連執行頁與監控頁皆見 `project-gone-state`（標題、無重試）、點「選擇其他專案」到入口頁且 `center-entry-view` 可見、零 pageerror／5xx，15 項全 OK（log `scratchpad\p1\probe_gone.log`）。
- 補強後本機親跑：該測試檔 6 passed、`prettier --check` 兩檔 rc 0、`tsc --noEmit` rc 0；全套 vitest 於 commit 前再跑一次（結果見 commit 訊息）。