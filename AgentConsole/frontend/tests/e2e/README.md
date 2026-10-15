# E2E（Playwright，對真後端）

驗證前端對真實 console-api（含 PostgreSQL）的完整流程：登入 → 專案／目標／任務 CRUD → 依賴與成環錯誤 → 拖曳排序 → signoff 硬閘 → 刪除；
另含響應式（1440／1024／390px）、路由導覽與四區塊版面、圖表回歸守衛，以及 FAILED 任務重試（該情境後端目前無入口，用 route mock）。
每個重點畫面存一張截圖到 `tests/e2e/__screenshots__/`。測試資料一律帶每次執行唯一的後綴，並在結束時刪除；`workers: 1` 序列執行。

## route mock 版（`*.mock.spec.ts`；不需要後端、不需要資料庫）

匯入頁（畫面 6）、設定頁（畫面 9）、通知徽章（Phase 3／6）、執行頁（畫面 7）、監控頁（畫面 8）與總覽儀表板（畫面 1）的 specs 以 `page.route` 攔 `**/api/v1/**`，
回契約 v1.1（`docs/02_architecture/API_Contract_P3-6.md`）形狀的假資料，驗「前端對契約形狀的行為」；真後端對接與契約漂移由 QA 波另驗。共用工具與夾具：

- `mockApi.ts`：`installApiMock`（攔截、CORS 放行、記錄每次請求與標頭供斷言；回應可帶標頭、204、或 `proxyTo` 轉給另一台真的伺服器）、
  `signInAs`（直接寫 sessionStorage，不需要 login 端點）、`snap`（截圖）、`collectConsoleErrors`（收主控台 error，收尾時應為空）。
- `settingsFixture.ts`：附錄 C 的 50 個鍵與記憶體內的設定假後端（ADMIN 專屬寫入、加密參數須 confirm、token_guard 跨鍵校驗、歷史）。
- `execFixture.ts`：**假引擎**（`Engine`）——記憶體內的 console-api 執行端點（execute／pause／resume／cancel／restore／review／steps／dag／checkpoints，
  自治等級 1～4 的審核閘、ESCALATED 的 RETRY／SKIP 與 `X-Follow-Up-Run-Id`、`/auth/refresh`），再加一台**真的 `node:http` SSE 伺服器**（`engine.listen()`，隨機埠）：
  `page.route` 的 fulfill 做不到「連線一直開著、事件陸續送達」，而連線狀態點、斷線重連、401 換 token 都依賴持續連線，所以 mock 對 `/api/v1/stream/**` 只做 `route.continue` 改網址轉過來。
  框架格式、`id` 規則（`41`、`41.1`）、`Last-Event-ID` 重放、`/metrics` 的收斂快照（`<S>.1/.2/.3`）、終態先送完衍生事件再關連線、重連已終態批次回 204、
  access token 驗證（401）都照契約 §2。時間由測試掌控：`startNext()`／`finishCurrent()`／`failCurrent()` 推進一步，事件立刻推給已連線的訂閱者；
  `dropStreams()`（切線）、`refuseStreams(n)`（503）、`expireTokens()`（401）模擬網路與認證故障；`sseConnections` 記下每次連線的 `Last-Event-ID`、token 與結果。
- `monitorFixture.ts`：假監控後端（`MonitorWorld`）——指標、Token／任務趨勢、告警（確認可延遲或失敗以驗樂觀更新與還原）、45 筆日誌的篩選與分頁、CSV／PDF 報表；
  批次與步驟事件借用 `Engine`。
- 新增的三支：`execute.mock.spec.ts`（15 個情境）、`monitor.mock.spec.ts`（9 個）、`dashboard.mock.spec.ts`（3 個）。

```bash
(cd AgentConsole/frontend && npx playwright test tests/e2e/execute.mock.spec.ts tests/e2e/monitor.mock.spec.ts tests/e2e/dashboard.mock.spec.ts)
(cd AgentConsole/frontend && npx playwright test tests/e2e/import.mock.spec.ts tests/e2e/settings.mock.spec.ts tests/e2e/notifications.mock.spec.ts)
```

```powershell
Push-Location AgentConsole\frontend; npx playwright test tests/e2e/execute.mock.spec.ts tests/e2e/monitor.mock.spec.ts tests/e2e/dashboard.mock.spec.ts; Pop-Location
Push-Location AgentConsole\frontend; npx playwright test tests/e2e/import.mock.spec.ts tests/e2e/settings.mock.spec.ts tests/e2e/notifications.mock.spec.ts; Pop-Location
```

寫 mock spec 的陷阱：Playwright 的 `getByLabel` 預設是**子字串**比對，而每列參數另有「重置：○○」「顯示：○○」按鈕，查輸入框要加 `{ exact: true }`；
文字區的 accessible name 會含它自己的內容，測試資料不要寫出和其他欄位標籤相同的詞（例如需求文字裡寫「補充說明」）；
EventSource 對非 200 的串流回應（204／401／503）會在主控台印一行 error，`collectConsoleErrors` 已把這幾種預期內的訊息濾掉，故意切線的測試另帶 `dropsConnections` 容許網路層那行。

**頁面載入時一直重新整理（`next dev` 的 Turbopack 快取）**：偶爾（W4-F2 開發期間在 Windows 上重現過數次）新啟動的 dev server 在頁面載入後會立刻被 HMR 全頁重載、
斷言一個接一個逾時（成因未完全查明，疑為上一次 dev server 被強制結束後留下不一致的快取；實測刪除快取後恢復正常。徵兆：`.next/dev/logs/next-development.log` 裡連續出現 `Compiled in 1ms`，HMR 訊息為 `reloadPage: HMR hash mismatch`）。
**刪掉 `frontend/.next/dev` 再重跑即可**（它只是快取，下次啟動重建；不影響 `npm run build` 的產物）。

寫 mock spec 的兩個陷阱：Playwright 的 `getByLabel` 預設是**子字串**比對，而每列參數另有「重置：○○」「顯示：○○」按鈕，查輸入框要加 `{ exact: true }`；
文字區的 accessible name 會含它自己的內容，測試資料不要寫出和其他欄位標籤相同的詞（例如需求文字裡寫「補充說明」）。

## 前置條件（真後端 specs）

1. PostgreSQL 與後端在線（`/actuator/health` 回 UP），且後端的 `CONSOLE_CORS_ALLOWED_ORIGINS` 包含前端來源（預設 `http://localhost:3000`）。
   啟動方式見 [backend/README.md](../../../backend/README.md)；開發預設帳號 operator／viewer 也在該檔。
2. 安裝瀏覽器（一次性）：`npx playwright install chromium`。

## 執行（工作目錄＝monorepo 根）

```bash
(cd AgentConsole/frontend && npx playwright install chromium)
(cd AgentConsole/frontend && npx playwright test)
# 非預設埠：後端 18080、前端 3100（後端的 CORS 要放行 http://localhost:3100）
(cd AgentConsole/frontend && E2E_API_URL=http://localhost:18080 E2E_WEB_PORT=3100 npx playwright test)
```

```powershell
Push-Location AgentConsole\frontend; npx playwright install chromium; Pop-Location
Push-Location AgentConsole\frontend; npx playwright test; Pop-Location
Push-Location AgentConsole\frontend; $env:E2E_API_URL="http://localhost:18080"; $env:E2E_WEB_PORT="3100"; npx playwright test; Pop-Location
```

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `E2E_API_URL` | `http://localhost:8080` | 後端 origin |
| `E2E_WEB_PORT` | `3000` | 前端埠 |
| `E2E_MODE` | `dev` | `dev`＝由 Playwright 起 `next dev`（`NEXT_PUBLIC_API_URL` 於啟動時決定）；`standalone`＝用已建置產物（`node scripts/start-standalone.mjs`），此時 `NEXT_PUBLIC_API_URL` 已在 `npm run build` 時內嵌，須以同一個後端位址先 build |
| `E2E_USER`／`E2E_PASSWORD` | operator／開發預設 | 登入帳密 |
| `E2E_VIEWER_PASSWORD` | viewer 開發預設 | 唯讀角色測試用 |

前端埠上已有服務且 `/api/health` 可達時（例如先以 `docker run -p` 起了前端映像），Playwright 會直接沿用、不另起伺服器。

## 收尾

測試不留資料；若中途被中斷，殘留的專案名稱帶「E2E」前綴，可在專案列表搜尋後刪除。報告與 trace 在 `playwright-report/`、`test-results/`（皆已 gitignore）。
