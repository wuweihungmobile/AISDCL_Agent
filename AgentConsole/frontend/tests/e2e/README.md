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
- `monitorFixture.ts`：假監控後端（`MonitorWorld`）——指標、Token／任務趨勢、告警（確認可延遲或失敗以驗樂觀更新與還原）、45 筆日誌的篩選與分頁、CSV／PDF 報表、
  AISDLC_SDD 引擎（`world.sdd`：以「FSM 狀態檔」的原樣內容依契約 §1.7.1 映射成 `GET /engines/sdd`，可切引擎不可用的三種原因、改檔案與壞檔）；批次與步驟事件借用 `Engine`。
- 新增的三支：`execute.mock.spec.ts`（21 個情境）、`monitor.mock.spec.ts`（15 個）、`dashboard.mock.spec.ts`（8 個，含頂列登出 2 個）；情境數會隨波次增加，一律以 `npx playwright test <檔> --list` 現查為準。
- `markdown-preview.mock.spec.ts`（3 個）：Markdown 編輯器預覽不渲染內嵌 HTML（DEF-AC-013，P2 資安）——新建專案對話框貼入各種載體、儲存式（管理者開編輯頁）、不合格網址的連結沒有 href；
  一定要對 **production 建置**跑（`E2E_MODE=standalone`）：修法靠 rehype-raw 的函式身分比對，jsdom 看不出 bundler 讓身分對不上的情形。真後端版是 QA 的 `p9-w7-html.spec.ts`。

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
- 選配環境變數：`E2E_JWT_SECRET`（backend 的 `JWT_SECRET`，用來偽造過期 token，E2E-12 步驟 1）、`E2E_RESTART_BACKEND`（停止並重新啟動 backend、等到 `/actuator/health` 才返回的腳本路徑；沒設就略過「重啟 backend 看 SSE 重連」的情境）、`E2E_DEFECTS_FIXED=1`（關掉 `test.fail` 釘住的已登記缺陷，看真實失敗訊息；缺陷清單見 `docs/06_quality/QA_P3-6_E2E_Verification.md` 與 `docs/06_quality/QA_W5_Reverification.md`，W6 修掉 DEF-AC-011 後曾有一段時間沒有任何 spec 用它釘住；W7-QA 登記 DEF-AC-013（Markdown 預覽 `<iframe srcdoc>` 腳本執行，`QA_W7_Closure.md` §10.1）後，`p9-w7-html.spec.ts` 的兩個情境再度用它釘住）。
- 路徑 C（高階目標拆解）要真 Brain，E2E 環境沒有；`support/fake_brain_bridge.py` 以假 Brain 啟動同一個 Bridge（`uvicorn --app-dir AgentConsole/frontend/tests/e2e/support fake_brain_bridge:app --host 127.0.0.1 --port 18081`，環境同上），再設 `E2E_FAKE_BRAIN=1` 跑 `p3-import.spec.ts` 即多跑一支路徑 C 情境（後端 → 真 Bridge 的 decompose 與草案 approve 都是真的，只有「拆解出什麼」是假的）。

## W5 複驗（契約 v1.2 §5 E2E-13；`p9-w5-*.spec.ts`）

W5 修復波（task-totals、專案復原、PDF 報表、Bridge 深度探針、traceId、手動重試文案…）的真後端複驗，環境同上節（本機 e2e 環境＋假 Brain 版 Bridge）：

| 檔案 | 內容 |
|------|------|
| `p9-w5-api.spec.ts` | E2E-13 列 1（task-totals 與各專案 task-trend 加總逐欄相等）、2～3（復原與錯誤路徑）、4（PDF 抽字）、7（升級告警跨批次）、8（執行中刪除 409）、9（手動重試）、11（列表 bridgeStatus）、12（traceId 貫穿 Bridge） |
| `p9-w5-bridge.spec.ts` | 列 13 的本機半邊：`/health/deep` 200，與「PATH 沒有 git」「工作區被刪」兩種 503（自起第二個 Bridge 在埠 18082） |
| `p9-w5-ui.spec.ts` | 專案列表「已刪除」與「復原」、執行中刪除的白話原因、手動重試 toast、執行頁暫停中晶片、重開匯入記錄還原警告與選項（路徑 C）、儀表板在 ≥31 個專案下的請求量與「本週完成」 |
| `p9-w5-a11y.spec.ts` | axe 掃 16 個頁面狀態（WCAG 2.0／2.1 A／AA 零違規）與鍵盤走查（Tab／Enter／Esc、拖曳的鍵盤替代、分頁籤方向鍵）；對話框關閉後焦點歸還觸發鈕（DEF-AC-011，W6 修於共用層 `components/ui/dialog.tsx`）為正向斷言 |
| `p9-w5-ui-evidence.spec.ts` | UI-DS-04／06／07、UI-OVL-02／03 的真瀏覽器逐項證據，另量 Markdown 預覽更新時間（NFR-9.1-05；W7 起 20KB 的上限由 400ms 收緊為 100ms，達到 PRD 要求的 100ms 內） |

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

## W7 複驗（契約 v1.3 E2E-14、v1.4 E2E-15／E2E-16；`p9-w7-*.spec.ts`）

W7 波（等級 6～10 傳遞引擎旋鈕 D-11、資源取樣 D-12、AISDLC_SDD 狀態端點 D-16、探測改打深度探針 D-17、待簽核清單 D-18、登出與 refresh 撤銷 D-19、DAG 全螢幕 D-01）的真後端複驗，環境同〈W5 複驗〉（本機 e2e 環境＋假 Brain 版 Bridge）。共用工具在 `w7.ts`：假模型伺服器（`FakeModelServer`，依請求內容把引擎對 Brain 的呼叫分成校正、演化提案、目標驗證，計數用）、
經根層 `.venv` 的 PyYAML 讀寫 YAML（磁碟上的引擎設定檔一律用 YAML 解析器讀，不比對文字）、變體 Bridge（`startBridge`：另起 18082～18086，純檔案模式、各自的工作區，不碰共用的 18081）、目錄 mtime 快照（`dirSnapshot`）、長批次夾具（`createLongFixture`）。

| 檔案 | 內容 |
|------|------|
| `p9-w7-engine.spec.ts` | E2E-14 列 1～7（等級 7＋金鑰、Brain 真的被呼叫與失敗升級、等級 3 對照、沒有金鑰、旗標全 false、旗標單獨生效、凍結與缺席；每列都讀磁碟上的 `config.yaml`／`playbook.yaml`／`run.json` 並在整個 run 目錄搜金鑰值）；V-12（附錄 C 標為 ENGINE 的其餘鍵逐鍵對磁碟設定，並斷言 `GET /settings` 的生效標籤目錄：ENGINE 十六把、UNVERIFIED 三把） |
| `p9-w7-resources.spec.ts` | E2E-14 列 8～9：`bridge.resources` 四欄位型別與範圍、`sampledAt` 前進、沒有 pid、卡片「資源使用」格式；終態與 PAUSED 的「—」；Bridge 停掉後的連線燈（會真的結束共用的 Bridge 再重啟，沒設 `E2E_STOP_BRIDGE`／`E2E_START_BRIDGE` 就略過那一支） |
| `p9-w7-sdd.spec.ts` | E2E-15 列 1～12：夾具目錄 `<E2E_ROOT>/sdd-fixture/AISDLC_SDD_v9.99`（不依賴被 git 忽略的真實 FSM 檔）的清單、單一專案、待人工、找不到／壞檔／非法名、檔案 ↔ API ↔ 畫面逐值比對、檔案改寫後輪詢跟上、Bridge 不可達、SDD 目錄無效、乾淨 clone 等價、權限、只讀；列 12 選跑真實檔 |
| `p9-w7-signoffs.spec.ts` | E2E-16 列 1～9：探測預設值與深度探針（git 不在 PATH 製造 503）；待簽核清單與計數同源、`limit` 與權限、儀表板「待人工審批」卡與通知鈴連結；refresh 輪替、登出撤銷、前端登出流程 |
| `p9-w7-ui.spec.ts` | DAG 全螢幕（契約 E-22）、US-P-04 專案執行中的編輯鎖定、設計稿九畫面的 DOM 結構斷言與截圖（`__screenshots__/p9-w7-screen-*`，供人眼對照 monorepo 根的 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/screenshots/`） |
| `p9-w7-purefile.spec.ts` | 審查 I-07／Architecture L-12：同一份夾具各跑一次——共用的 DB 模式 Bridge 對照另起（18086）的純檔案模式 Bridge，比對 Console 的步驟時間軸與斷點清單（只量不裁決；會把 `autoclaude.engineUrl` 指過去，結束後還原） |
| `p9-w7-html.spec.ts` | FE 回填〈九〉第 3 點：編輯器預覽走 rehype-raw、內嵌 HTML 會變成真元素——①img onerror、script、javascript: 連結三種載體不執行（正向斷言）；②③DEF-AC-013（P2）`<iframe srcdoc>` 內的腳本會在編輯器預覽執行（新建專案的預覽、已儲存內容的「編輯專案」頁），用 `test.fail(DEFECTS_OPEN)` 釘住，修好後會意外通過、請移除該行；④同一份已儲存內容在唯讀的專案詳情頁不執行（對照）。腳本只寫旗標與讀 sessionStorage 的鍵名，不讀值、不外送 |

- 選配環境變數：`E2E_MOCK_DELAY`（秒；backend 以 `--console.execution.mock-env[MOCK_CLAUDE_DELAY]=<秒>` 啟動時設成同值，`p9-w7-resources.spec.ts` 走契約形態「五個任務、延遲 ≥ 3 秒」；沒設則為預設 0.6 秒，改用 40 個任務的單一目標把批次撐長）、
  `E2E_STOP_BRIDGE`／`E2E_START_BRIDGE`（結束／重啟共用 Bridge 的 PowerShell 腳本路徑，以 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` 執行；**只有 Windows**，其他平台不要設，那一支會略過）。其餘同〈W5 複驗〉（`E2E_BRIDGE_LOG`、`E2E_PG_CONTAINER`、`E2E_FAKE_BRAIN`、`E2E_RESTART_BACKEND`）。
- 🔴 這批 spec 起額外的行程與埠：變體 Bridge 18082～18086、假模型伺服器（隨機埠）；`p9-w7-engine.spec.ts` 的列 5（等級 3 的目標邊界審核）一支就要一分多鐘，各檔單獨跑約二至四分鐘（視機器而定）。與別的真後端 spec 一樣 `workers: 1`，不可與 mock spec 同機同時跑（共用的 Bridge 與限流額度）。
- 檔名 `p9-w7-*` 刻意排在 `p5-monitor.spec.ts` 之後：列 2（git 不在 PATH 的 Bridge 回 503）與列 9（Bridge 停掉）會故意讓探測失敗，把 `agentAvailability` 拉到 100 以下；可用率環在 backend 記憶體裡、要約一天才滾出去，只有重啟 backend 會清空，而 `p5-monitor.spec.ts` 斷言它為 100。單獨重跑 p5 之前先重啟 backend。
- 跑法（bash／PowerShell 並列；其餘環境變數同前面各節）：

```bash
(cd AgentConsole/frontend && E2E_BRIDGE_LOG="$E2E_ROOT/bridge-logs/bridge.log" E2E_PG_CONTAINER=qa-pg E2E_FAKE_BRAIN=1 npx playwright test tests/e2e/p9-w7-engine.spec.ts tests/e2e/p9-w7-sdd.spec.ts tests/e2e/p9-w7-signoffs.spec.ts tests/e2e/p9-w7-ui.spec.ts tests/e2e/p9-w7-purefile.spec.ts tests/e2e/p9-w7-html.spec.ts tests/e2e/p9-w7-resources.spec.ts)
```

```powershell
Push-Location AgentConsole\frontend; $env:E2E_BRIDGE_LOG = "$env:E2E_ROOT\bridge-logs\bridge.log"; $env:E2E_PG_CONTAINER = "qa-pg"; $env:E2E_FAKE_BRAIN = "1"; npx playwright test tests/e2e/p9-w7-engine.spec.ts tests/e2e/p9-w7-sdd.spec.ts tests/e2e/p9-w7-signoffs.spec.ts tests/e2e/p9-w7-ui.spec.ts tests/e2e/p9-w7-purefile.spec.ts tests/e2e/p9-w7-html.spec.ts tests/e2e/p9-w7-resources.spec.ts; Pop-Location
```

## Docker 全棧（`*.stack.ts`，經 nginx 同源）

`docker compose --profile db --profile app --profile full up -d` 之後，用 `docker.config.ts` 跑 `p8-docker-stack.stack.ts`：入口（首頁／`/actuator/` 被封／401）、路徑 A 匯入全鏈（凍結規格放進 Bridge 容器的 `/workspace`，因為全棧不載入 e2e profile、沒有 allow-loopback）、SSE 經 nginx（`proxy_buffering off`）與重啟 backend 後重連（W5 起不再 `test.fail`：換新失敗不登出）、10MB 上傳、nginx access／error 日誌都不含 `access_token` 的值，以及 W5 新增的全棧情境：`/api/health` 與 `/_next/static` 的 Cache-Control 恰好一份、Bridge 深度探針（移走容器內的 git → 503 → 容器轉 unhealthy → 還原後回 healthy）、`X-Trace-Id` 貫穿 Bridge 與 backend 卷內日誌、偽造 `X-Forwarded-For` 仍會被限流（含兩段各 62 秒的等待）。
W7 起另有 `p9-w7-docker.stack.ts`（契約 v1.3／v1.4 的全棧側）：全新資料庫的 `healthCheckPath` 預設與 Bridge 容器 healthcheck 打深度探針（E2E-16 列 1）、Linux 容器內引擎行程樹的資源取樣與終態的「—」（E2E-14 列 8～9）、`/engines/sdd` 與主機上真實 FSM 檔逐值一致（E2E-15 列 9 全棧半邊）、同一個 Bridge 映像另起容器驗乾淨 clone 等價與 `SDD_ROOT` 不存在（列 8～9）、停掉 redis 後登入／換新／登出的撤銷仍有效且 backend 維持 healthy、日誌恰一筆 WARN、恢復後一筆 INFO（E2E-16 列 10）。
它用 `docker` CLI 指名容器：預設為 compose 的 `container_name`（`aisdlc-engine-bridge`、`aisdlc-backend`、`aisdlc-redis`），映像 `aisdlc-engine-bridge:dev`；以 `E2E_BRIDGE_CONTAINER`／`E2E_BACKEND_CONTAINER`／`E2E_REDIS_CONTAINER`／`E2E_BRIDGE_IMAGE` 覆寫。**起全棧前要先 `up -d --build`**：舊的 Bridge 映像沒有 `resources`、`/sdd/fsm`、`checks.sdd`。
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
| `E2E_BRIDGE_URL`／`E2E_BRIDGE_LOG`／`E2E_PG_CONTAINER` | `http://127.0.0.1:18081`／（空）／（空） | W5、W7 複驗用：直連 Bridge 的位址、`bridge.log` 絕對路徑、本機 e2e 的 PostgreSQL 容器名（見〈W5 複驗〉） |
| `E2E_MOCK_DELAY`／`E2E_STOP_BRIDGE`／`E2E_START_BRIDGE` | `0.6`／（空）／（空） | W7 複驗用（見〈W7 複驗〉）；後兩者只有 Windows |
| `E2E_BRIDGE_CONTAINER`／`E2E_BACKEND_CONTAINER`／`E2E_REDIS_CONTAINER`／`E2E_BRIDGE_IMAGE` | compose 的 `container_name`／`aisdlc-engine-bridge:dev` | `p9-w7-docker.stack.ts` 用（見〈Docker 全棧〉） |

前端埠上已有服務且 `/api/health` 可達時（例如先以 `docker run -p` 起了前端映像），Playwright 會直接沿用、不另起伺服器。

## 收尾

測試不留資料；若中途被中斷，殘留的專案名稱帶「E2E」前綴，可在專案列表搜尋後刪除。報告與 trace 在 `playwright-report/`、`test-results/`（皆已 gitignore）。
