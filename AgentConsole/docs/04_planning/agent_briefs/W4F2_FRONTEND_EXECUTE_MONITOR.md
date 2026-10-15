# 任務書 W4-F2：前端第二棒（Next.js 16；Phase 4 執行頁 ＋ Phase 5 監控頁與儀表板真指標）

> 先讀 `COMMON_CONTEXT.md`（頂部〈本輪環境覆寫〉凌駕其後）、`AgentConsole/CLAUDE.md`、`W3_FRONTEND.md`、**W4-F1 的交卷（主控會貼給你）**，然後讀**契約 SSOT**：`AgentConsole/docs/02_architecture/API_Contract_P3-6.md`（§1、§2 SSE、§4 頁面矩陣、§5 情境）＋ `openapi-p3-6.yaml`，再讀本檔。
> 你在 W4-F1 交卷後的同一棵 frontend 樹上續做；後端 Phase 4／5 由 W3-B2 **同時**在做，你不能等它；SSE 與端點以契約為準、route mock 驗證；真後端對接由 QA 波做。

## 必讀
1. 設計稿：README 畫面 7（Execute）、畫面 8（Monitor）、畫面 1（Dashboard 的四張 KPI 與「進行中的執行」卡）；`screenshots/07-execute.png`、`08-monitor.png`、`01-dashboard.png`。
2. PRD：§5.3.2（871～880）、§5.3.4（907～921）、§5.3.6（968～1026）、§5.4.2～§5.4.5（1066～1174）、§7.1.5～§7.1.7（1748～1790）、附錄 B（2068～2108）。
3. 既有程式：`frontend/lib/api/*`、`frontend/components/charts/*`（W3-A 的圖表 spike：Tremor Raw AreaChart＋recharts）、`frontend/components/domain/LogPanel.tsx`、`frontend/app/page.tsx`（Dashboard）、`frontend/app/projects/[projectId]/{execute,monitor}/page.tsx`（路由殼）、`frontend/components/layout/BottomRegion.tsx`。

## 已拍板決策
- **SSE client**：`lib/api/sse.ts`——用原生 `EventSource`（URL 帶 `?access_token=<accessToken>`，契約 §2），監聽具名事件；`lastEventId` 記錄；斷線時先 `GET /executions/{runId}/steps?afterSeq=<lastId>` 分頁回補，再以 `Last-Event-ID`（EventSource 自動帶）續接；401 時換 token 後重建；頁面離開時 `close()`。寫成可測試的純函式＋hook（`useRunStream(runId)`）。
- **`/projects/[projectId]/execute`（畫面 7）**：返回連結、標題「專案執行：{名稱}」（`play`）、副標；專案 `signedOff=false` 時「執行鎖定」橫幅（`lock`；「啟動回 409 Conflict」；「前往審批」開 signoff 對話框）。上半兩欄：左「執行控制」卡（自治等級 select 1～10、Token 預算 input（等寬 20px/700，預設取 settings `execution.globalTokenBudget`）、執行範圍 checkbox 樹（全部／各目標／展開任務；對映 `scope{mode, goalIds, taskIds}`）、按鈕列依 run 狀態切換：無 run 或終態→「啟動執行」；RUNNING→「暫停」「取消」；PAUSED→「恢復」「取消」「從斷點恢復」（開 checkpoint 選擇對話框，列 `GET checkpoints`，選一筆 → `POST restore/{checkpointId}`））；右上「執行進度」卡（Run #n、狀態中文＋`wg-blink` 閃點、任務進度條 `completedSteps/totalSteps`、Token 進度條 `totalTokensUsed/tokenBudget`（≥80% 變 warning 色、超限 error 色）、耗時）；右下「DAG 依賴視覺化」卡（`GET dag`：目標節點橫向排列 `G1 ─── G2 ─── G3`，完成＝主色實底、進行中＝tertiary 底主色邊、待處理＝灰底，各目標下方列任務節點小方塊顏色依狀態；可橫向捲動；狀態隨 SSE `progress-update` 更新）。「即時日誌」卡（深色終端 `#1c241a`、高 240px、自動捲動開關、搜尋過濾；`log` 事件逐行、`status-change` 以強調色插一行）。「待審核項目」卡（來源 `GET /executions/{runId}` 的 `pendingReviews[]` ＋ SSE `review-request`；每列 `alert-triangle`＋kind 中文＋reason＋四按鈕 通過(solid)／重試／跳過／拒絕 → `POST review/{reviewId}` 帶 decision 與可選 comment，成功後移除並 toast）。執行批次選擇：頁首 select 列 `GET /projects/{id}/executions`，預設最新；切換 run 重訂閱。
- **`/projects/[projectId]/monitor`（畫面 8）**：返回、標題「專案監控：{名稱}」（`activity`）、右側時間範圍 select（1h／24h／7d／30d → `from`／`to`）與執行批次 select（`runId`）；四張指標卡（完成率、任務成功率、重試率、Token 消耗；數值 30px/700；delta 行用契約給的比較值，沒有就不顯示 delta）；「Token 使用趨勢」卡＝recharts／Tremor AreaChart（主色折線、`opacity .08` 填充、虛線預算線 `#DCE3D6`、軸標籤 11px）；兩欄：「任務狀態分佈」水平 bar（完成 `#498428`／執行中 `#80B155`／失敗 `#D35B58`／待處理 `#A6B0A1`）與「執行時間分佈」垂直柱（最高用主色其餘 secondary）；「事件時間軸」（`task-trend` 的 events：啟動／完成／失敗／重試點，水平時間軸）；「執行日誌查詢」卡（level select 全部／INFO／WARN／ERROR、關鍵字、任務 id，分頁；等寬列：時間 muted＋level 著色寬 48px＋訊息）；「告警」卡（`#fef7ea` 底、`alert-triangle` `#F5A623`、時間、訊息、「確認」ghost → acknowledge；已確認顯示「已確認」）；底部「匯出報表」（CSV 下載；PDF 若後端 501 顯示「尚未提供」）；批次比較表（US-M-06：選 2 個 run 橫向對比 Token／時長／成功率，用 `metrics?runId=` 各取一次）；Agent 即時狀態（US-M-10：`metrics` 的 agentAvailability／最近探測結果，顯示狀態指示燈）。
- **Dashboard（畫面 1）**：四張 KPI 全接真資料（活躍專案數、待審批草案數＝notifications summary、本週完成任務數＝`metrics`（from＝本週一）、執行中 run 數＝各專案 executions 聚合或契約提供的全域端點）；「進行中的執行」卡列 status=EXECUTING 專案 ＋ 其最新 run 的進度條（`completedSteps/totalSteps`）。
- **BottomRegion**：Engine Bridge 連線狀態點＝輪詢契約指定的健康來源（每 30 秒；連線＝綠點「已連線」、否則紅點「未連線」）。
- 自訂儀表板拖曳（US-M-08）：**本波做最小版**——監控頁各卡可用 `@dnd-kit` 拖曳重排，順序存 `localStorage`（鍵 `console.monitor.layout`）；沒時間就標 🟡 並寫明。
- 設計系統規範同 W3-A；四區塊只在 `app/layout.tsx` 組裝。

## 測試要求
- vitest：SSE client（假 EventSource：事件分派、lastEventId、斷線回補順序、401 重建、close）；DAG 節點佈局與狀態色對映；執行控制按鈕狀態機（每個 run 狀態顯示哪些按鈕）；審核動作送出的 body；KPI 計算／格式化；告警確認後的樂觀更新；status.ts 的 RunStatus／ReviewKind 標籤。
- Playwright（route mock ＋ 用 `page.route` 回假 SSE：以 `text/event-stream` body 一次給多則事件即可）：`tests/e2e/execute.mock.spec.ts`（鎖定橫幅、啟動 → 進度與日誌更新、待審核四按鈕、暫停／恢復／取消、checkpoint 對話框）、`tests/e2e/monitor.mock.spec.ts`（四卡、圖表渲染、日誌篩選、告警確認、CSV 下載）、`tests/e2e/dashboard.mock.spec.ts`（四張 KPI 真值）。每頁截圖入庫並列與設計稿差異。
- `npm run lint`、`npx tsc --noEmit`、`npm run build` 皆 0 錯；vitest 覆蓋率（`npx vitest run --coverage`）貼總表，受測範圍 ≥ 70%。

## 閘門
同 W4-F1 的指令（Playwright 改跑你的三支 mock spec）；四區塊 grep 閘門空；`git status --porcelain` 全部落在 `AgentConsole/frontend/**` 與 `rtm_backfill_W4F2.md`；無殘留 node 行程。

## RTM 回填
寫到 `AgentConsole/docs/06_quality/rtm_backfill_W4F2.md`，涵蓋 US-E-01～11（FE 側）、US-M-01～10（FE 側）、UI-SCR-01／07／08、UI-KPI-*、UI-CHT-*、契約 §4 列到的 FE 項。不要直接改 RTM.md。

## 交卷
照 COMMON_CONTEXT〈交卷格式〉，另加〈契約漂移／缺口〉與〈給 QA 的提醒〉（哪些行為只在 mock 下驗過、真後端對接時最可能漂移的點）。不准 commit／push、不派子 agent、不留背景行程。

## 主控裁決補充（2026-10-15，依獨立 Architect 審查；與本檔上文衝突時以本節與契約 v1.1 為準）
- mock spec 裡「啟動後一路跑到 COMPLETED」用自治等級 4；等級 3 的多目標專案會在目標邊界 PAUSED 並出現 GOAL_COMPLETED 待審核項（另寫一條 spec 驗「通過 → 續跑」）。
- 事件時間軸來源＝`GET /executions/{runId}/steps`（`task-trend` 沒有 `events[]`）。
- `/metrics` 串流的事件 id 互異且嚴格遞增（`<S>.1` progress-update／`<S>.2` token-update／`<S>.3` metric-update），去重用 id 即可；`/logs` 與 `/metrics` 各自獨立記 lastEventId。
- 斷線回補順序照契約 §2.3／§2.8：先讓 EventSource 以 `Last-Event-ID` 自動重連，連續失敗兩次以上才改走 `GET /executions/{runId}/steps?afterSeq=` 回補再續接（本檔上文的「先 REST 回補」作廢）。
- SSE 框架的冒號後空白不保證（後端用 Spring SseEmitter），解析用 EventSource 即可，不要自己用字串比對框架。
- 儀表板「本週完成任務數」＝各專案 `task-trend`（from＝本週一）的 completed 加總；「執行中 run 數」＝各 EXECUTING 專案最新 run 的計數。
- BottomRegion 的 Engine Bridge 連線狀態點＝`GET /notifications/summary` 的 `bridgeConnected`／`bridgeCheckedAt`（B1 階段可能為 null → 顯示「未知」灰點）。
- 自治等級 6～10 不傳引擎（契約標 UNVERIFIED），UI 照常可選、說明文字註明。
