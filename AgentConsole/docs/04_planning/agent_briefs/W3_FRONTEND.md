# 任務書 W3-A：前端開發者（Next.js 16，PRD Phase 1 + Phase 2 ＋ 四區塊共用版面）

> 先讀 `COMMON_CONTEXT.md`，再讀 `AgentConsole/docs/02_architecture/Architecture.md` §5／§11 與 `ADR-001`，再讀本檔。後端（console-api）已完成 Phase 1+2 並可在本機 8080 跑起來；它的 OpenAPI 在 `http://localhost:8080/v3/api-docs`。

## 你的角色
你是 console-web（前端）的唯一開發者。本波做：專案骨架、設計系統落地、**四區塊共用版面**、登入、Dashboard（部分）、專案／目標／任務三層所有頁面與對話框、Markdown 編輯器。匯入／執行／監控／設定四個頁面本波只放路由殼（顯示「Phase 3～5 待實作」），下一波填。

## 必讀
1. UI 設計稿（**像素級定稿，視覺以它為準**）：`docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md` 全文；`_ds/water-green-design-system-*/tokens/*.css`（token 原文，逐字搬進 `frontend/styles/tokens.css`）；`screenshots/01～09.png`（用 Read 工具看圖）；`Agent Console.dc.html` 可用瀏覽器開來對照互動（不可移植其程式碼）。
2. PRD：§4.2 路由樹（314～347）、§5.1 全部（353～646，含 §5.1.4 Markdown 編輯器八項功能）、§8（1856～1940；**§8.2 色彩方案與設計稿衝突時以設計稿為準**，見下方偏離）、§7.2 回應格式、§9.1 效能。
3. 後端 OpenAPI：`curl -s localhost:8080/v3/api-docs`（型別用 `openapi-typescript` 產生，見下）。

## 已拍板決策
- **設計系統**：採設計稿的 water_green（淺色、扁平、綠色主調、Inter + Noto Sans TC、Lucide 線性圖示、8pt grid、無陰影、強制焦點環）。PRD §8.2 的 Slate/Indigo 深色方案**被設計稿取代**（設計稿是後交付的像素級定稿）；深色模式本波不做。把這條寫進 `AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md`。
- **路由**：照 PRD §4.2 巢狀路由（`/projects/[projectId]/goals/[goalId]/tasks/[taskId]`），不用設計稿 README 建議的扁平路由。
- **四區塊共用版面**（掌舵者要求，改一處全站生效）：`components/layout/TopRegion.tsx`（＝設計稿 Topbar 公告列 + Masthead 主導覽列：logo、搜尋列、通知鈴、signoff 佇列鈕）、`components/layout/ToolsRegion.tsx`（＝左側 240px：導航六項 + 「我的專案」rail）、`components/layout/ContentRegion.tsx`（路由內容容器，負責捲動與 max-width 1440）、`components/layout/BottomRegion.tsx`（底部列：Engine Bridge 連線狀態點、版本、Toast 宿主）。`app/layout.tsx` 只組裝這四個；任何頁面不得自帶這四區塊的內容。響應式照 PRD §8.3（<768 底部 Tab、768～1279 收合成圖示）。
- **資料存取**：全部 client-side——`lib/api/client.ts` 典型 fetch 包裝（自動帶 Bearer、401 時用 refresh token 換新、失敗跳登入、解 PRD §7.2 封包、帶 `X-Trace-Id` 進錯誤訊息）＋ TanStack Query；token 存 `sessionStorage`（`lib/auth/store.ts`）。頁面用 `"use client"`；Server Components 只做靜態殼。
- **型別**：`npx openapi-typescript http://localhost:8080/v3/api-docs -o lib/api/schema.d.ts`，**把產物 commit 進 repo**（建置不依賴後端在線）；再寫 `lib/api/endpoints.ts` 封裝每個端點（函式名與 PRD §7.1 一一對應）。
- **Markdown**：`@uiw/react-md-editor`（Split View、工具列、GFM 表格、checklist、程式碼區塊高亮）＋ 匯入 `.md`（`<input type=file>` 讀入）／匯出 `.md`（Blob 下載）；渲染用 `react-markdown` + `remark-gfm` + `rehype-highlight`。PRD §5.1.4 八項逐項對照寫進 RTM。
- **圖表 spike**（本波就做，只做一張）：先試 Tremor Raw 的 AreaChart 在 Tailwind 4 下能否 build＋render；30 分鐘內不成就改 shadcn `chart`（Recharts）。結果（成／敗、採用哪個、版本）寫進 ADR-002。Dashboard 放這張圖（資料先用專案狀態分佈，真指標下一波接監控 API）。
- **狀態 enum 中文標籤與顏色**：照設計稿 README〈狀態 enum〉表，放 `lib/domain/status.ts` 單一出處。
- **表單驗證**：react-hook-form + zod；錯誤訊息繁中；後端 400 的 `errors[]` 要對應到欄位顯示。

## 頁面規格（本波必做；每頁對照設計稿該張截圖做到像素級，標題／按鈕／卡片結構一致）
1. `/login`：帳密表單（不在設計稿，風格照 token）；成功導回 `/`。
2. `/`（Dashboard，設計稿 1）：四張 KPI 卡（活躍專案數／待審批草案數／本週完成任務數／執行中 run 數——前兩張用專案／目標 API 算，後兩張先顯示「—」並標 Phase 5）；「進行中的執行」卡（本波列 status=EXECUTING 的專案）；「待人工審批」卡（signedOff=false 的專案＋目標，按「審批」開 signoff 對話框）；右上「匯入 BRD / PRD」按鈕導到 `/import`。
3. `/projects`（設計稿 2）：Toolbar（狀態 tab 群 全部/草稿/就緒/執行中/完成/失敗、排序 select、mini 分頁器）、搜尋（Top 區搜尋列 Enter 後導到 `/projects?q=`）、專案卡清單（圖示方塊、名稱、狀態點、「未審批」紅標、meta 行：Lv.N 自治／目標 N／任務 done/total／更新日期／等寬路徑；四個 ghost 按鈕 查看／編輯／執行／監控）、底部分頁器；「新建專案」開對話框。
4. `/projects/[projectId]`（設計稿 3）：返回鏈結、標題列、meta、**Signoff 警示橫幅**（signedOff=false 時）、兩欄卡（基本資訊：執行路徑等寬框＋通過標準 Markdown 渲染／專案說明 Markdown 渲染）、目標清單卡（狀態點、名稱、進度條、done/total、查看；「新增目標」；拖曳排序→PUT reorder）、底部行動（執行專案→`/execute`、查看監控→`/monitor`、編輯、刪除確認）。
5. `/projects/[projectId]/goals/[goalId]`（設計稿 4）：返回、標題、meta（所屬專案／進度／前置依賴 chips）、草案橫幅、兩欄卡（目標說明／通過標準 checklist 渲染）、任務清單卡（狀態點、名稱、狀態、重試 x/y、詳情）、「新增任務」、底部編輯／刪除；編輯對話框含「前置依賴」多選（成環時顯示後端 400 原因）。
6. `/projects/[projectId]/goals/[goalId]/tasks/[taskId]`（設計稿 5）：返回、標題、meta（麵包屑／重試／Agent）、三張指標卡（開始時間／Token 消耗／重試次數，等寬字體）、兩欄卡（任務說明／通過標準）、執行日誌卡（深色終端面板 `#1c241a`，`executionLog` 內容，搜尋框過濾）、底部 重試（FAILED/ESCALATED 才啟用）／編輯／刪除。
7. 建立／編輯 Dialog（設計稿〈全域覆蓋層〉）：560px 白卡、名稱、（專案）執行路徑、說明 Markdown 編輯器、通過標準 Markdown 編輯器、（專案）自治等級、（任務）最大重試／evaluatorCommand／expectedOutputRegex；取消／儲存；名稱空→行內錯誤。
8. Signoff 對話框：approver 輸入（預設帶目前使用者名）、確認 → POST signoff → toast「已 signoff」。
9. `/import`、`/projects/[id]/execute`、`/projects/[id]/monitor`、`/settings`：路由殼＋設計稿標題列＋「本頁於 Phase 3～5 實作」佔位卡（**導航項要能點**）。
10. Toast（底部置中深色）、載入 Skeleton、空狀態、錯誤狀態（顯示 traceId）。

## 專案骨架
```
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole
npx --yes create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir=false --import-alias "@/*" --use-npm --yes
cd frontend && npx --yes shadcn@latest init -d && npx shadcn@latest add button card dialog input textarea select badge tabs table progress skeleton toast dropdown-menu checkbox separator sheet tooltip
npm i @tanstack/react-query lucide-react react-hook-form zod @hookform/resolvers @uiw/react-md-editor react-markdown remark-gfm rehype-highlight @dnd-kit/core @dnd-kit/sortable
npm i -D openapi-typescript vitest @testing-library/react @testing-library/jest-dom jsdom @playwright/test
```
`next.config.ts`：`output: "standalone"`（Dockerfile 需要）；`app/api/health/route.ts` 回 `{status:"ok"}`。`.env.example`（原寫 .env.local.example，根層鎖只准 `.env.example` 範本名入庫）：`NEXT_PUBLIC_API_URL=http://localhost:8080`。Dockerfile 照 PRD §11.4.1 逐字（build context＝`AgentConsole/frontend`）。

## 測試要求
- vitest：四區塊版面各渲染一次且只在 `app/layout.tsx` 被組裝（用 grep 測試斷言其他 `app/**/page.tsx` 不 import layout 區塊）；status.ts 對照表完整（11 個任務狀態、5 個目標狀態、6 個專案狀態都有中文標籤）；API client 的封包解析與 401→refresh 流程（mock fetch）；Markdown 編輯器八項功能各一個行為測試（至少匯入／匯出／checklist 渲染可自動化）。
- Playwright E2E（對真後端：先 `docker compose -f ../docker-compose.dev.yml up -d` 起 PG，再 `cd ../backend && ./gradlew bootRun` 背景起後端——**用 `run_in_background` 啟動並在交卷前自己關掉**，不要留孤兒行程）：登入 → 新建專案 → 進詳情 → 新增兩個目標並設依賴 → 新增任務 → 專案列表顯示目標 2／任務 1 → signoff 流程（先用 API 把 signedOff 改 false 或建立時由後端提供測試旗標——若後端無法產生草案，E2E 只驗橫幅在 signedOff=false 資料下會出現，可用 route mock）→ 刪除任務／目標／專案 → 列表消失。每頁截一張圖存 `frontend/tests/e2e/__screenshots__/`，交卷列出與設計稿截圖的差異（文字描述即可）。
- `npm run lint`、`npx tsc --noEmit`、`npm run build` 皆 0 錯。

## 閘門（自己跑，逐字貼）
```
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole/frontend
npm run lint && npx tsc --noEmit && npm run build         # 貼 build 的 Route 表
npx vitest run                                            # 貼 N passed
npx playwright test                                       # 貼 N passed（需後端在線；若無法起後端寫明原因並貼嘗試輸出）
docker build -t aisdlc-frontend:dev .                     # 在 frontend/ 跑；貼最後 3 行；docker run -p 3000:3000 … curl localhost:3000/api/health
grep -rn "TopRegion\|ToolsRegion\|BottomRegion" app --include=*.tsx | grep -v "app/layout.tsx"   # 期望空（共用區塊只住 layout）
```
- 回填 RTM 的 UI-／US-P／US-G／US-T 列（實作檔、測試、狀態）。
- 交卷附：Next.js／Tailwind／shadcn／MD editor 實際版本、圖表 spike 結果、與設計稿的已知差異清單。

## 追加（後端 W2-A 交卷後，2026-10-15；優先於上文衝突處）
### 後端接線事實（已由主控驗證）
- 啟動後端（本機）：先起 PG：`docker run -d --name console-pg -e POSTGRES_PASSWORD=aisdlc -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18`；再 `cd AgentConsole/backend && JWT_SECRET=dev-secret-please-change-me-at-least-32-chars SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD=aisdlc sh gradlew bootRun`（用 `run_in_background`，交卷前 `sh gradlew --stop` 並 `docker rm -f console-pg`）。細節見 `AgentConsole/backend/README.md`。
- 開發帳密：admin／`Admin#Dev2026`、operator／`Operator#Dev2026`、viewer／`Viewer#Dev2026`。登入 `POST /api/v1/auth/login {username,password}` → `{code,message,data:{accessToken,refreshToken,expiresIn:1800,role}}`；`POST /api/v1/auth/refresh {refreshToken}`。
- 封包：成功 `{code,message:"success",data,timestamp,traceId}`；錯誤 `{code,message,errors[{field,message}],timestamp,traceId,reason?,details?}`；分頁 `data={content,page,size,totalElements,totalPages}`；每回應 header `X-Trace-Id`。列表參數 `page,size,q,status,sort=欄位,asc|desc`。CORS 只放行 `http://localhost:3000`。
- 建立 Request 可帶 `draft:true` → `signedOff=false`（用這個做 signoff E2E，不必 mock）。已 signoff 再簽回 409。專案列表每列有 `goalsCount/tasksCount/tasksDone`。目標 PUT 可帶 `dependsOn[]`，成環回 400 `reason:"依賴成環"`＋`details.cycle[]`。任務 `evaluatorCommand` 含禁用字元回 400 `details.violations[]`。
- OpenAPI：`http://localhost:8080/v3/api-docs`（13 路徑／22 操作，含 ApiError schema）→ `npx openapi-typescript` 產型別。

### 分階段與停損（額度有限，寧可少做但每階段都可建置）
- **M1**（必做）：骨架、tokens.css、四區塊共用版面、`/login`、API client（封包／401 refresh）、`lib/domain/status.ts`、路由殼（九個路由都能點、各有標題列）、`npm run build` 綠。
- **M2**（必做）：Dashboard（KPI 前兩張＋待審批卡＋進行中卡）、`/projects` 列表（toolbar／分頁／搜尋）、專案詳情、目標詳情、任務詳情（含日誌面板）、建立／編輯對話框（說明與通過標準先用 textarea，Markdown **渲染**用 react-markdown）、刪除確認、signoff 對話框、retry 按鈕。
- **M3**（必做）：Markdown 編輯器（@uiw/react-md-editor 八項功能）、目標拖曳排序、依賴多選、vitest（版面唯一性／status 表／API client）。
- **M4**（時間允許才做）：圖表 spike、Playwright E2E、Dockerfile。做不到就在〈沒做〉寫清楚，並留 `frontend/tests/e2e/README.md` 說明怎麼跑。
- 每個 M 完成時 `npm run lint && npx tsc --noEmit && npm run build` 必須綠才進下一個；交卷時樹必須可建置。不要讀整份 PRD（只讀 §4.2、§5.1、§8），省 token。
