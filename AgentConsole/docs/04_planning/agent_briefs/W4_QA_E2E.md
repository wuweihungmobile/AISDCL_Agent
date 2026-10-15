# 任務書 W4-QA：獨立驗證（全鏈 E2E、RTM 逐列核對、NFR 量測、缺陷登記）

> 你是獨立審查者，**零信任**：四位開發者（W3-B1／B2、W4-F1／F2）的交卷只是「宣稱」，每一條 RTM 列都要你親跑才能設 `✅ 已驗證`。先讀 `COMMON_CONTEXT.md`（頂部〈本輪環境覆寫〉凌駕其後）、`AgentConsole/CLAUDE.md`、`Implementation_Plan.md` §2 W4 出口閘門、契約 `API_Contract_P3-6.md`（§5 情境是你的最低驗證矩陣）、`RTM.md` §1（回填規則與狀態權限）、四份 `docs/06_quality/rtm_backfill_*.md`，再讀本檔。
> **你不改任何程式碼**（`backend/src/main`、`frontend/app|components|lib`、`engine-bridge/app` 一律唯讀）；你只能新增／修改 `frontend/tests/e2e/**`（真後端 E2E spec）、`docs/06_quality/**`（RTM、QA 報告、缺陷清單）、以及驗證用腳本（放 scratchpad）。發現缺陷＝登記，不是修。

## 環境（本機模式，Architecture §9.2；全部用 `run_in_background: true` 起，交卷前全部收掉）
1. PG：`docker run -d --name qa-pg -e POSTGRES_PASSWORD=aisdlc -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -p 5433:5432 pgvector/pgvector:pg18`。
2. Bridge：`Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\engine-bridge; $env:BRIDGE_DB_DSN='postgresql://aisdlc:aisdlc@127.0.0.1:5433/aisdlc'; $env:BRIDGE_DB_SCHEMA='console'; $env:BRIDGE_ALLOWED_PATH_ROOTS='<你的 scratchpad 測試專案目錄>'; $env:BRIDGE_OUTBOUND_ALLOWLIST='localhost,127.0.0.1'; D:\CursorProject\AISDCL_Agent\.venv\Scripts\uvicorn.exe app.main:app --port 8081; Pop-Location`（**backend 先跑 Flyway 建好 console schema 之後**再起 Bridge，或 Bridge 純檔案模式先起、backend 起好後重啟 Bridge）。
3. backend：照 `backend/README.md`，另加 `ENGINE_BRIDGE_URL=http://127.0.0.1:8081`、`CONSOLE_ENCRYPTION_KEY`、`CONSOLE_SECURITY_OUTBOUND_ALLOWLIST=localhost,127.0.0.1`、`CONSOLE_CORS_ALLOWED_ORIGINS=http://localhost:3000`、mock-cli 旗標（看 W3-B2 交卷）。
4. 假 chat-completions server（匯入 LLM 路徑用）：scratchpad 放一支 Python `http.server`，固定回三層 JSON（含 usage）；另一組回 25 個任務（驗 422）。
5. frontend：Playwright 的 webServer 會自己起 `next dev`（`playwright.config.ts`）。

## 驗證矩陣（最低；每條都要貼指令與關鍵輸出）
A. 契約 §5 全部情境，以 Playwright **真後端** spec 落檔（`tests/e2e/p3-import.spec.ts`、`p4-execute.spec.ts`、`p5-monitor.spec.ts`、`p6-settings.spec.ts`），登入 → 匯入貼文字（假 LLM）→ 422 有界閘顯示三條 → 修正 → signoff → confirm → 專案頁全 signedOff → 執行頁 Level 3 啟動（mock claude）→ SSE 日誌出現 step 事件 → 進度條到 100% → COMPLETED → 監控頁 KPI／趨勢／日誌／告警 → 設定頁 token-guard 400、敏感鍵二次確認、測試連線（對假 server 成功、對 `http://10.0.0.1` 被拒）。另跑 Level 1（第一步後 PAUSED＋待審核卡 → 通過 → 跑完）、ESCALATED（`MOCK_CLAUDE_FAIL_REGEX`）→ 重試／跳過、取消、從 checkpoint 恢復、token 預算告警（小預算）。每頁截圖入庫。
B. 後端 API 層（不經前端）：`curl.exe -N` 讀兩條 SSE 端點貼前 5 行各一；`Last-Event-ID` 重播（斷後再連，貼 id 連續）；execute 未 signoff 409 body；rate limit 101 次 429；viewer 寫入 403；無 token 401；Bridge 關掉時 `GET /executions/{runId}` 200 且 `bridge.connected=false`。
C. 消毒字元集 parity：比對 Bridge `engine-bridge/app/security.py` 的黑名單常數與後端 `PassCriteriaSanitizer`（或 W3-B 新增的常數）集合相等，貼腳本輸出（Architecture §8.3）。
D. Docker 全棧（`docker compose --profile db --profile app --profile full up -d --build`，`.env` 由 `.env.example` 複製填測試值、驗完刪除）：經 nginx `http://localhost/` 200、`/api/v1/projects` 無 token 401、登入後走一次「匯入貼文字 → signoff → confirm → 執行（映像內建 mock claude）→ COMPLETED」；`docker compose ps` 全 healthy；收尾 `down -v`。Windows 上 compose 若有平台問題，貼錯誤並登缺陷，不要繞。
E. NFR-9.1-01～06 量測：頁面首屏（Playwright `performance.timing`）、API p95（用 `Measure-Command` 迴圈 50 次對 `GET /api/v1/projects`）、SSE 延遲（事件 timestamp 與收到時間差）、並發（10 個同時登入 ＋ 列表）；方法與數值寫進報告。
F. RTM 逐列核對：把四份 `rtm_backfill_*.md` 合併進 `RTM.md`（只改四格；開發者宣稱 `✅ 實作+測試` 的列，你實跑其自動測試一次（可整批跑 `gradlew test`／`vitest`）再決定留 `✅ 實作+測試` 或升 `✅ 已驗證`／降 `❌ 缺陷`）；`⬜ 未開始` 的列每一條判定：已驗證／缺陷／`⛔ 範圍外`（只准引用主控裁決，沒有就留 `⬜` 並列入報告〈未覆蓋〉）。用 Implementation_Plan W4 閘門的兩條 Select-String 現查計數貼報告。
G. 文件鎖：`D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe D:\CursorProject\AISDCL_Agent\tools\check_pytest_baseline_sites.py` rc=0；RTM 列數仍 361＋你新增的列（新增列要在報告列出）；`AgentConsole/CLAUDE.md` ≤ 200 行。

## 產出
- `AgentConsole/docs/06_quality/QA_P3-6_E2E_Verification.md`：環境、每條情境的指令與證據、NFR 表、RTM 統計（現查指令輸出）、〈缺陷清單〉（編號 DEF-AC-NNN；嚴重度 P1～P4；重現步驟；影響的 RTM 列；建議修法）、〈未覆蓋〉、〈與設計稿差異〉。
- `RTM.md` 更新（只改四格、不刪列不改號）。
- `frontend/tests/e2e/*.spec.ts` 真後端 spec ＋截圖。

## 交卷
照 COMMON_CONTEXT〈交卷格式〉；〈驗證證據〉逐條對應驗證矩陣 A～G；`Get-Process java,node,python -ErrorAction SilentlyContinue` 與 `docker ps` 證明環境已收；`git status --porcelain` 只落在允許路徑。不准 commit／push、不派子 agent、不改程式碼。

## 主控裁決補充（2026-10-15，依獨立 Architect 審查；與本檔上文衝突時以本節與契約 v1.1 為準）
- 情境 A 的「Level 3 啟動 → 跑到 COMPLETED」改為：一路跑完用 **Level 4**（契約 E2E-03）；Level 3 另驗「目標邊界 PAUSED → GOAL_COMPLETED 待審核 → 通過 → 跑完」；Level 1 驗第一步後 PAUSED。
- 環境照契約 v1.1 §5.0：Bridge 啟動前 PATH 前置 `D:\CursorProject\AISDCL_Agent\.venv\Scripts`、`autoclaude.claudeCommand` 設為 `D:\CursorProject\AISDCL_Agent\.venv\Scripts\aisdlc-mock-claude.exe` 絕對路徑、`AUTOSDD_QUOTA_CACHE_DIR=<E2E_ROOT>\quota-cache`、清掉 `AUTOSDD_*`／`AUTOCLAUDE_*`／`MINIMAX_*`；E2E 專案每個 run 的任務數 ≤ 5。
- SSE 斷言用解析後的欄位（事件名、id、data JSON），不比對框架位元組；`/metrics` 的 id 含子序號 `<S>.1`／`<S>.2`／`<S>.3`。
- 本機環境要以 e2e profile 啟動 backend（才有 `console.security.allow-loopback=true` 與 `console.execution.mock-env`，契約 §5.0.1）；Docker 全棧（矩陣 D）不載入 e2e profile，匯入步驟改走路徑 A（凍結規格）或 Phase 2 REST 建專案，10MB 上傳（nginx 11m）與 `access_token` 不入 nginx 日誌仍須驗。
- Bridge P1（AR-01）已由主控派人修復並親驗（PAUSED 可 restore）；若 E2E-07 步驟 6 仍 409，登記為 Bridge 缺陷附 Bridge 日誌。
- 經 nginx 的驗證要包含 10MB 上傳（nginx `client_max_body_size` 由 B1 補）與 `?access_token=` 不出現在 nginx access log（由 B2 補遮罩）。
- 限流鍵是 JWT subject：驗 429 時用同一使用者打 101 次；不同情境用不同使用者或等 60 秒。
- RTM 裁決（引用本節即可）：`API-AUT-06`（自治等級傳遞引擎）→ 🟡（契約標 UNVERIFIED，等級 6～10 不送引擎設定）；`US-M-10` 的「資源使用情況」→ 🟡（Bridge 無來源；連線狀態與當前任務有）；`US-I-05` 的「瀏覽按鈕」→ ⛔（Web 不瀏覽伺服器檔案系統，路徑輸入欄即為交付）。
- 斷言 `details.unsignedProjectId` 這類可為 null 的欄位時，「缺席」與 `null` 等價（契約 §0.2）。
