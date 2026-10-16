# E2E（Playwright，對真後端）

驗證前端對真實 console-api（含 PostgreSQL）的完整流程：登入 → 專案／目標／任務 CRUD → 依賴與成環錯誤 → 拖曳排序 → signoff 硬閘 → 刪除；
另含響應式（1440／1024／390px）、路由導覽與四區塊版面、圖表回歸守衛、Markdown 編輯器八項功能（`markdown-editor.spec.ts`：即時預覽、原始碼著色、工具列、GFM 表格、程式碼高亮、Checklist、匯入／匯出 .md），以及 FAILED 任務重試（該情境後端目前無入口，用 route mock）。
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

## 真 Bridge specs（`p3-import`／`p4-execute`／`p4b-execute-more`／`p5-monitor`／`p6-settings`／`p7-cors-ratelimit`）

對真後端（e2e profile）＋真 Engine Bridge＋`aisdlc-mock-claude`，驗契約 `API_Contract_P3-6.md` §5 的 E2E-01～12；**沒設 `E2E_ROOT` 時整批略過**（一般開發機沒有真 Bridge）。
環境依契約 §5.0（完整 Bridge 與 backend 環境變數見 [engine-bridge/README.md](../../../engine-bridge/README.md)、[backend/README.md](../../../backend/README.md)）：

1. `E2E_ROOT`＝一個空目錄（絕對路徑），底下建 `projects`、`workspace`、`quota-cache` 三個子目錄；專案的 `executionPath` 一律建在 `projects` 之下。
2. PostgreSQL 18：`docker run -d --rm --name qa-pg -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -p 25433:5432 pgvector/pgvector:pg18`（5433 常被本機原生 PG 佔用，所以用 25433）。
3. **啟動順序：backend → Bridge → 重啟 backend**。Bridge 的 DB 模式要等 backend 的 Flyway 建好 `console` schema；backend 的連線探測環要在 Bridge 起來之後才看得到它（否則 `agentAvailability` 不是 100）。
4. backend 以 `e2e` profile 啟動（才有 `console.security.allow-loopback` 與 `console.execution.mock-env`）；Bridge 啟動前清掉 `AUTOSDD_*`／`AUTOCLAUDE_*`／`MINIMAX_*`／`MOCK_CLAUDE_*` 環境變數，`PATH` 前置根層 `.venv` 的 `Scripts`（POSIX：`bin`），`AUTOSDD_QUOTA_CACHE_DIR` 指向 `<E2E_ROOT>/quota-cache`。
5. 前端要用 `npm run build`（`NEXT_PUBLIC_API_URL` 於 build 時內嵌）後以 `E2E_MODE=standalone` 跑：`next dev` 偶爾在頁面載入後被 HMR 全頁重載（見上節），長情境會被它打斷。

```bash
# bash（相對於 monorepo 根；〈…〉換成自己的值，密碼與金鑰一律用環境變數、不寫進檔案）
export E2E_ROOT=<ABS_PATH_TO_EMPTY_DIR>; mkdir -p "$E2E_ROOT"/{projects,workspace,quota-cache}
(cd AgentConsole/backend && SPRING_PROFILES_ACTIVE=e2e SERVER_PORT=18080 JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' \
  SPRING_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:25433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_PASSWORD>' \
  ENGINE_BRIDGE_URL=http://127.0.0.1:18081 CONSOLE_CORS_ALLOWED_ORIGINS=http://localhost:3000 \
  java -jar build/libs/console-0.0.1-SNAPSHOT.jar "--console.execution.mock-env[MOCK_CLAUDE_TRACE]=$E2E_ROOT/mock-trace.jsonl")
unset ${!AUTOSDD_*} ${!AUTOCLAUDE_*} ${!MINIMAX_*} ${!MOCK_CLAUDE_*}   # 契約 §5.0.1：Bridge 啟動前先清掉
(cd AgentConsole/engine-bridge && PATH="$PWD/../../.venv/bin:$PATH" AUTOSDD_QUOTA_CACHE_DIR="$E2E_ROOT/quota-cache" ENGINE_WORKSPACE="$E2E_ROOT/workspace" \
  BRIDGE_ALLOWED_PATH_ROOTS="$E2E_ROOT/projects:$E2E_ROOT/workspace" BRIDGE_DB_DSN='postgresql://aisdlc:<YOUR_PASSWORD>@127.0.0.1:25433/aisdlc' BRIDGE_DB_SCHEMA=console \
  BRIDGE_OUTBOUND_ALLOWLIST=127.0.0.1,localhost BRIDGE_STOP_GRACE_SECONDS=5 BRIDGE_INSTANCE=e2e-bridge \
  ../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18081 --workers 1)
(cd AgentConsole/frontend && E2E_API_URL=http://localhost:18080 E2E_WEB_PORT=3000 E2E_MODE=standalone npx playwright test tests/e2e/p3-import.spec.ts tests/e2e/p4-execute.spec.ts tests/e2e/p4b-execute-more.spec.ts tests/e2e/p5-monitor.spec.ts tests/e2e/p6-settings.spec.ts tests/e2e/p7-cors-ratelimit.spec.ts)
```

```powershell
# PowerShell（不用裸 cd；〈…〉換成自己的值）
$env:E2E_ROOT = "<ABS_PATH_TO_EMPTY_DIR>"; "projects", "workspace", "quota-cache" | ForEach-Object { New-Item -ItemType Directory -Force "$env:E2E_ROOT\$_" | Out-Null }
# backend（e2e profile）；另開終端，Bridge 同理
$env:SPRING_PROFILES_ACTIVE = "e2e"; $env:SERVER_PORT = "18080"; $env:JWT_SECRET = "<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:CONSOLE_ENCRYPTION_KEY = "<YOUR_CONSOLE_ENCRYPTION_KEY>"
$env:SPRING_DATASOURCE_URL = "jdbc:postgresql://127.0.0.1:25433/aisdlc"; $env:SPRING_DATASOURCE_USERNAME = "aisdlc"; $env:SPRING_DATASOURCE_PASSWORD = "<YOUR_PASSWORD>"
$env:ENGINE_BRIDGE_URL = "http://127.0.0.1:18081"; $env:CONSOLE_CORS_ALLOWED_ORIGINS = "http://localhost:3000"
Push-Location AgentConsole\backend; java -jar build\libs\console-0.0.1-SNAPSHOT.jar "--console.execution.mock-env[MOCK_CLAUDE_TRACE]=$env:E2E_ROOT\mock-trace.jsonl"; Pop-Location
# Bridge
Get-ChildItem Env: | Where-Object Name -match "^(AUTOSDD_|AUTOCLAUDE_|MINIMAX_|MOCK_CLAUDE_)" | ForEach-Object { Remove-Item "Env:$($_.Name)" }
$env:PATH = "$((Resolve-Path .venv\Scripts).Path);$env:PATH"; $env:AUTOSDD_QUOTA_CACHE_DIR = "$env:E2E_ROOT\quota-cache"; $env:ENGINE_WORKSPACE = "$env:E2E_ROOT\workspace"
$env:BRIDGE_ALLOWED_PATH_ROOTS = "$env:E2E_ROOT\projects;$env:E2E_ROOT\workspace"; $env:BRIDGE_DB_DSN = "postgresql://aisdlc:<YOUR_PASSWORD>@127.0.0.1:25433/aisdlc"; $env:BRIDGE_DB_SCHEMA = "console"
$env:BRIDGE_OUTBOUND_ALLOWLIST = "127.0.0.1,localhost"; $env:BRIDGE_STOP_GRACE_SECONDS = "5"; $env:BRIDGE_INSTANCE = "e2e-bridge"
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 18081 --workers 1; Pop-Location
# Playwright
$env:E2E_API_URL = "http://localhost:18080"; $env:E2E_WEB_PORT = "3000"; $env:E2E_MODE = "standalone"
Push-Location AgentConsole\frontend; npx playwright test tests/e2e/p3-import.spec.ts tests/e2e/p4-execute.spec.ts tests/e2e/p4b-execute-more.spec.ts tests/e2e/p5-monitor.spec.ts tests/e2e/p6-settings.spec.ts tests/e2e/p7-cors-ratelimit.spec.ts; Pop-Location
```

- **限流**：e2e profile 每個使用者（JWT subject）每 60 秒 100 次，UI 與 REST 共用同一個桶，所以輪詢一律用 viewer、UI 用 operator、設定用 admin；`realBackend.ts` 的 `ensureQuota()` 在情境開始前確認餘額，不夠就等視窗過去（多步驟 UI 情境中途撞 429 會被誤判成功能缺陷）；不需要 `E2E_ROOT` 的既有 spec（例如 `signoff.spec.ts`）用 `helpers.ts` 的 `waitForQuota()`。總覽頁每次載入就要 30 次上下請求（QA 報告 DEF-AC-009），整套連續跑時，前一支 spec 可能已把這個使用者的額度用光。
- 選配環境變數：`E2E_JWT_SECRET`（backend 的 `JWT_SECRET`，用來偽造過期 token，E2E-12 步驟 1）、`E2E_RESTART_BACKEND`（停止並重新啟動 backend、等到 `/actuator/health` 才返回的腳本路徑；沒設就略過「重啟 backend 看 SSE 重連」的情境）、`E2E_DEFECTS_FIXED=1`（關掉 `test.fail` 釘住的已登記缺陷，看真實失敗訊息；缺陷清單見 `docs/06_quality/QA_P3-6_E2E_Verification.md` 與 `docs/06_quality/QA_W5_Reverification.md`，W6 修掉 DEF-AC-011 後已沒有任何 spec 用它釘住，旗標保留給日後登記的缺陷）。
- 路徑 C（高階目標拆解）要真 Brain，E2E 環境沒有；`support/fake_brain_bridge.py` 以假 Brain 啟動同一個 Bridge（`uvicorn --app-dir AgentConsole/frontend/tests/e2e/support fake_brain_bridge:app --host 127.0.0.1 --port 18081`，環境同上），再設 `E2E_FAKE_BRAIN=1` 跑 `p3-import.spec.ts` 即多跑一支路徑 C 情境（後端 → 真 Bridge 的 decompose 與草案 approve 都是真的，只有「拆解出什麼」是假的）。

## W5 複驗（契約 v1.2 §5 E2E-13；`p9-w5-*.spec.ts`）

W5 修復波（task-totals、專案復原、PDF 報表、Bridge 深度探針、traceId、手動重試文案…）的真後端複驗，環境同上節（本機 e2e 環境＋假 Brain 版 Bridge）：

| 檔案 | 內容 |
|------|------|
| `p9-w5-api.spec.ts` | E2E-13 列 1（task-totals 與各專案 task-trend 加總逐欄相等）、2～3（復原與錯誤路徑）、4（PDF 抽字）、7（升級告警跨批次）、8（執行中刪除 409）、9（手動重試）、11（列表 bridgeStatus）、12（traceId 貫穿 Bridge） |
| `p9-w5-bridge.spec.ts` | 列 13 的本機半邊：`/health/deep` 200，與「PATH 沒有 git」「工作區被刪」兩種 503（自起第二個 Bridge 在埠 18082） |
| `p9-w5-ui.spec.ts` | 專案列表「已刪除」與「復原」、執行中刪除的白話原因、手動重試 toast、執行頁暫停中晶片、重開匯入記錄還原警告與選項（路徑 C）、儀表板在 ≥31 個專案下的請求量與「本週完成」 |
| `p9-w5-a11y.spec.ts` | axe 掃 16 個頁面狀態（WCAG 2.0／2.1 A／AA 零違規）與鍵盤走查（Tab／Enter／Esc、拖曳的鍵盤替代、分頁籤方向鍵）；對話框關閉後焦點歸還觸發鈕（DEF-AC-011，W6 修於共用層 `components/ui/dialog.tsx`）為正向斷言 |
| `p9-w5-ui-evidence.spec.ts` | UI-DS-04／06／07、UI-OVL-02／03 的真瀏覽器逐項證據，另量 Markdown 預覽更新時間（NFR-9.1-05） |

- 選配環境變數：`E2E_BRIDGE_URL`（預設 `http://127.0.0.1:18081`，直連 Bridge）、`E2E_BRIDGE_LOG`（Bridge 以 `BRIDGE_LOG_DIR` 啟動時的 `bridge.log` 絕對路徑；沒設就略過「日誌每一行有 trace_id」那支）、`E2E_PG_CONTAINER`（本機 e2e 的 PostgreSQL 容器名，例 `qa-pg`；「復原逾保留期」要把 `deleted_at` 撥到 31 天前，沒設就略過）。
- 🔴 **Windows 的 `E2E_ROOT` 要短**：Bridge 的工作區檔案路徑是 `<ENGINE_WORKSPACE>\<run uuid>\engine\checkpoints\playbook.checkpoint.<pid>.<uuid>.tmp`，比根目錄多約 130 字元；根目錄超過約 130 字元時，審核 `RETRY`（restore）會在 Bridge 內因 Windows 的 260 字元路徑上限（`LongPathsEnabled=0`）得到 `FileNotFoundError`，console-api 回 502。`E2E_ROOT` 請放在磁碟根目錄底下、名稱 8 個字元以內的短資料夾（不要放進 session 暫存目錄或使用者家目錄深處）。
- `pdfText.ts`：不依賴任何套件的 PDF 文字抽取（PDFBox 內嵌字型的 ToUnicode CMap），報表 PDF 的中文與四個區段靠它驗。
- 跑法（bash／PowerShell 並列；其餘環境變數同上節）：

```bash
(cd AgentConsole/frontend && E2E_BRIDGE_LOG="$E2E_ROOT/bridge-logs/bridge.log" E2E_PG_CONTAINER=qa-pg E2E_FAKE_BRAIN=1 npx playwright test tests/e2e/p9-w5-api.spec.ts tests/e2e/p9-w5-bridge.spec.ts tests/e2e/p9-w5-ui.spec.ts tests/e2e/p9-w5-a11y.spec.ts tests/e2e/p9-w5-ui-evidence.spec.ts)
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_BRIDGE_LOG = "$env:E2E_ROOT\bridge-logs\bridge.log"; $env:E2E_PG_CONTAINER = "qa-pg"; $env:E2E_FAKE_BRAIN = "1"; npx playwright test tests/e2e/p9-w5-api.spec.ts tests/e2e/p9-w5-bridge.spec.ts tests/e2e/p9-w5-ui.spec.ts tests/e2e/p9-w5-a11y.spec.ts tests/e2e/p9-w5-ui-evidence.spec.ts; Pop-Location
```

## Docker 全棧（`*.stack.ts`，經 nginx 同源）

`docker compose --profile db --profile app --profile full up -d` 之後，用 `docker.config.ts` 跑 `p8-docker-stack.stack.ts`：入口（首頁／`/actuator/` 被封／401）、路徑 A 匯入全鏈（凍結規格放進 Bridge 容器的 `/workspace`，因為全棧不載入 e2e profile、沒有 allow-loopback）、SSE 經 nginx（`proxy_buffering off`）與重啟 backend 後重連（W5 起不再 `test.fail`：換新失敗不登出）、10MB 上傳、nginx access／error 日誌都不含 `access_token` 的值，以及 W5 新增的全棧情境：`/api/health` 與 `/_next/static` 的 Cache-Control 恰好一份、Bridge 深度探針（移走容器內的 git → 503 → 容器轉 unhealthy → 還原後回 healthy）、`X-Trace-Id` 貫穿 Bridge 與 backend 卷內日誌、偽造 `X-Forwarded-For` 仍會被限流（含兩段各 62 秒的等待）。
同一份設定也會跑不依賴 e2e profile 的既有真後端 specs（`crud-flow`／`signoff`／`design-system`／`chart`／`shells-and-layout`）：全棧是乾淨的資料庫、經 nginx 同源。需要 docker CLI；`E2E_API_URL` 必須是 nginx 入口（預設 `http://localhost`）。
全棧的 backend 沒有 `allow-loopback`，所以 `p3`～`p7` 那批（假 LLM 伺服器綁 127.0.0.1）不能在這裡跑。

```bash
(cd AgentConsole/frontend && E2E_API_URL=http://localhost npx playwright test -c tests/e2e/docker.config.ts)
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts; Pop-Location
```

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `E2E_API_URL` | `http://localhost:8080` | 後端 origin |
| `E2E_WEB_PORT` | `3000` | 前端埠 |
| `E2E_MODE` | `dev` | `dev`＝由 Playwright 起 `next dev`（`NEXT_PUBLIC_API_URL` 於啟動時決定）；`standalone`＝用已建置產物（`node scripts/start-standalone.mjs`），此時 `NEXT_PUBLIC_API_URL` 已在 `npm run build` 時內嵌，須以同一個後端位址先 build |
| `E2E_USER`／`E2E_PASSWORD` | operator／開發預設 | 登入帳密 |
| `E2E_VIEWER_PASSWORD` | viewer 開發預設 | 唯讀角色測試用 |
| `E2E_ROOT` | （空） | 真 Bridge specs 的根目錄；沒設就略過那批 specs（見〈真 Bridge specs〉） |
| `E2E_JWT_SECRET`／`E2E_RESTART_BACKEND`／`E2E_DEFECTS_FIXED`／`E2E_FAKE_BRAIN` | （空） | 真 Bridge specs 的選配項（同上節） |

前端埠上已有服務且 `/api/health` 可達時（例如先以 `docker run -p` 起了前端映像），Playwright 會直接沿用、不另起伺服器。

## 收尾

測試不留資料；若中途被中斷，殘留的專案名稱帶「E2E」前綴，可在專案列表搜尋後刪除。報告與 trace 在 `playwright-report/`、`test-results/`（皆已 gitignore）。
