# E2E（Playwright，對真後端）

驗證前端對真實 console-api（含 PostgreSQL）的完整流程：登入 → 專案／目標／任務 CRUD → 依賴與成環錯誤 → 拖曳排序 → signoff 硬閘 → 刪除；
另含響應式（1440／1024／390px）、路由殼、圖表回歸守衛，以及 FAILED 任務重試（該情境後端目前無入口，用 route mock）。
每個重點畫面存一張截圖到 `tests/e2e/__screenshots__/`。測試資料一律帶每次執行唯一的後綴，並在結束時刪除；`workers: 1` 序列執行。

## route mock 版（`*.mock.spec.ts`；不需要後端、不需要資料庫）

匯入頁（畫面 6）、設定頁（畫面 9）與通知徽章（Phase 3／6）的 specs 以 `page.route` 攔 `**/api/v1/**`，回契約 v1.1（`docs/02_architecture/API_Contract_P3-6.md`）形狀的假資料，
驗「前端對契約形狀的行為」；真後端對接與契約漂移由 QA 波另驗。共用工具與夾具：

- `mockApi.ts`：`installApiMock`（攔截、CORS 放行、記錄每次請求供斷言）、`signInAs`（直接寫 sessionStorage，不需要 login 端點）、`snap`（截圖）。
- `settingsFixture.ts`：附錄 C 的 50 個鍵與記憶體內的設定假後端（ADMIN 專屬寫入、加密參數須 confirm、token_guard 跨鍵校驗、歷史）。

```bash
(cd AgentConsole/frontend && npx playwright test tests/e2e/import.mock.spec.ts tests/e2e/settings.mock.spec.ts tests/e2e/notifications.mock.spec.ts)
```

```powershell
Push-Location AgentConsole\frontend; npx playwright test tests/e2e/import.mock.spec.ts tests/e2e/settings.mock.spec.ts tests/e2e/notifications.mock.spec.ts; Pop-Location
```

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
