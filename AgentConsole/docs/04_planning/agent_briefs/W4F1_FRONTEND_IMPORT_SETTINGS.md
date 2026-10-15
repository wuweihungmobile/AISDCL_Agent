# 任務書 W4-F1：前端第一棒（Next.js 16；Phase 3 匯入頁 ＋ Phase 6 設定頁 ＋ 通知徽章）

> 先讀 `COMMON_CONTEXT.md`（頂部〈本輪環境覆寫〉凌駕其後）、`AgentConsole/CLAUDE.md`、`W3_FRONTEND.md`（W3-A 的決策與慣例：四區塊版面、API client、status.ts、表單驗證、設計系統），然後讀**契約 SSOT**：`AgentConsole/docs/02_architecture/API_Contract_P3-6.md`（§1 端點、§4 頁面↔端點矩陣、§5 情境）＋ `openapi-p3-6.yaml`，再讀本檔。
> 後端 Phase 3／6 由 W3-B1 **同時**在做，你不能等它；型別從契約 YAML 產生，頁面以 route mock 驗證；真後端對接由 QA 波做，契約漂移由主控裁決。

## 必讀
1. 設計稿（像素級定稿）：`docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md` 的畫面 6（Import）、畫面 9（Settings）、〈全域覆蓋層〉、〈Motion〉、〈Focus〉；`screenshots/06-import.png`、`09-settings.png`（Read 看圖）。
2. PRD：§5.2.3（706～719）、§5.2.5（773～817）、§5.5.3（1283～1294）、§5.5.4（1296～1338）、§7.1.4（1726～1746）、§7.1.8（1791～1807）。
3. 既有程式：`frontend/lib/api/{client,endpoints,queries,types}.ts`、`frontend/components/layout/TopRegion.tsx`、`frontend/components/domain/entity/*`（表單／對話框慣例）、`frontend/app/import/page.tsx` 與 `frontend/app/settings/page.tsx`（目前是路由殼）、`frontend/tests/e2e/*.spec.ts`（Playwright 慣例與登入 helper）。

## 已拍板決策
- **型別**：`Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx openapi-typescript ..\docs\02_architecture\openapi-p3-6.yaml -o lib\api\schema-p3-6.d.ts; Pop-Location`，產物入庫；`lib/api/endpoints.ts` 每個契約端點一個函式（命名與 PRD §7.1 一一對應，延續既有風格）；`lib/api/queries.ts` 加 TanStack Query hooks。檔案上傳用 `FormData`（client 要能不設 `Content-Type`）；報表／匯出下載用 Blob。
- **`/import`（畫面 6）**：`max-width 960px`；步驟 1 卡：來源 tab（檔案上傳／貼上文字／歷史記錄）、拖放區（`2px dashed`、`upload-cloud` 40px、格式與 10MB 說明、點擊選檔、拖曳 hover 態）、自治等級 select（1～10，預設 3）、執行路徑 input（等寬；提示本機／Docker 兩種寫法，Architecture L-8）、補充說明 textarea、「開始解析」（`sparkles`，44px）。解析中：spinner ＋「AI 解析中…（套用有界閘：步驟 ≤24 / Kahn 無環 / prompt 非空）」。步驟 2 卡：樹狀預覽（`folder`/`target`/`file-text` 圖示、縮排、可展開看說明與通過標準）＋ **編輯**（新增／刪除／改名／改說明與通過標準／拖曳調整目標與任務順序 → `PUT /import/{id}/result`）；有界閘 422 時把 `errors[]` 的 gate／detail／location **完整列出不截斷**，並讓使用者修改後重試；signoff 警示橫幅（含 `signed_off=false` code 字樣）＋「signoff 審批」（approver 對話框，預設帶目前使用者）→ 成功顯示綠勾「已 signoff」；底部「放棄」（→ REJECTED）＋「確認匯入」（未 signoff 時禁用；成功導到 `/projects/[id]`）。歷史記錄 tab：列表（時間、來源檔名、狀態中文標籤、產生的專案連結、aiModel／tokenUsed），分頁。
- **`/settings`（畫面 9）**：標題列＋「匯出設定」「匯入設定」ghost；六個分類 tab（模型／Agent／執行／監控／AutoClaude／SDD，各帶圖示）；參數卡每列 grid（220px label＋desc／1fr 控制項），控制項依 `valueType`：STRING／INTEGER／LONG／FLOAT → input（44px、圓角 8px；數值用 `inputMode`）、ENUM → select、BOOLEAN → 自訂 toggle（46×26）、ENCRYPTED → password input ＋ 顯示／隱藏（顯示＝呼叫 `?reveal=true`，非 ADMIN 時按鈕禁用並提示）；每列尾端「重置」IconButton（`rotate-ccw`）；驗證錯誤紅字（後端 400 的 reason／errors 對應到該列）；`impactNote` 以 ℹ️ 行顯示（US-S-08）；敏感鍵（ENCRYPTED 或契約標敏感）儲存前二次確認對話框（送 `confirm=true`）；token_guard 兩鍵在執行 tab 以同一張「Token Guard」小卡成對編輯，送 `PUT /settings/execution/token-guard`，400 時顯示 reason；模型 tab 有「測試連線」（`plug`）→ 測試中 spinner → 成功綠勾「連線成功（延遲 NNNms）」／失敗紅字 reason；修改歷史卡（等寬字體列 `時間 / 參數 / 舊值 → 新值 / @使用者`，分頁）；底部「儲存變更」（逐鍵送有變動的 PUT，全部成功才 toast；任一失敗停在該鍵並顯示錯誤）＋「全部重置為預設值」（確認對話框 → 逐鍵 reset）。匯出＝下載 JSON；匯入＝選檔上傳 → 顯示 `applied/skipped/errors[]`。
- **通知徽章**：`TopRegion` 的鈴鐺與 signoff 佇列鈕接 `GET /api/v1/notifications/summary`（每 30 秒 refetch；`pendingSignoffs` 進 signoff 鈕 badge、`pendingReviews + unacknowledgedAlerts` 進鈴鐺 badge；點鈴鐺開一個小面板列三個數字與連結）。Dashboard 的「待審批草案數」KPI 改用此端點。
- **狀態標籤**：`lib/domain/status.ts` 增加 ImportStatus（UPLOADED／PARSING／PARSED／REVIEWING／IMPORTED／REJECTED）中文標籤與顏色，仍是唯一出處。
- 設計系統規範不變：扁平無陰影、8pt grid、Lucide、強制焦點環、hover 只改顏色；四區塊只在 `app/layout.tsx` 組裝（grep 閘門必須空）。

## 測試要求
- vitest：樹狀編輯器的 reducer／轉換（新增、刪除、重排、序列化成 `parsedResult`）；有界閘錯誤呈現（給 3 條 errors 全部顯示、不截斷）；settings 控制項依 valueType 渲染（7 種各一）；敏感鍵確認流程；token-guard 卡的 400 顯示；status.ts ImportStatus 表完整；endpoints 每個新端點一個函式（延續既有 `endpoints.test.ts` 的寫法）。
- Playwright（**route mock**，不需後端；新檔 `tests/e2e/import.mock.spec.ts`、`tests/e2e/settings.mock.spec.ts`，用 `page.route` 攔 `**/api/v1/**` 回契約形狀的假資料）：匯入貼文字 → 解析 → 顯示三層樹 → 編輯一個任務名 → 422 情境顯示三條 gate → signoff → 確認匯入 → 導向專案頁；設定頁六個 tab 切換、改一個數值儲存、敏感鍵二次確認、token-guard 400、測試連線成功、匯出下載。每頁截圖存 `tests/e2e/__screenshots__/`，交卷列與設計稿的差異。既有真後端 specs 不動（QA 會跑）。
- `npm run lint`、`npx tsc --noEmit`、`npm run build` 皆 0 錯。

## 閘門（自己跑、逐字貼）
```powershell
Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npm run lint; "lint rc=$LASTEXITCODE"; npx tsc --noEmit; "tsc rc=$LASTEXITCODE"; npm run build > "<scratchpad>\build.log" 2>&1; "build rc=$LASTEXITCODE"; Pop-Location
Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx vitest run > "<scratchpad>\vitest.log" 2>&1; "vitest rc=$LASTEXITCODE"; Pop-Location; Get-Content "<scratchpad>\vitest.log" -Tail 8
Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; npx playwright test tests/e2e/import.mock.spec.ts tests/e2e/settings.mock.spec.ts > "<scratchpad>\pw.log" 2>&1; "pw rc=$LASTEXITCODE"; Pop-Location; Get-Content "<scratchpad>\pw.log" -Tail 15
Get-ChildItem D:\CursorProject\AISDCL_Agent\AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
```
（Playwright 瀏覽器不在就先 `npx playwright install chromium`；被網路擋下就寫明並貼嘗試輸出。）交卷前 `git status --porcelain` 全部落在 `AgentConsole/frontend/**` 與你的 RTM 回填檔；`Get-Process node -ErrorAction SilentlyContinue` 無你留下的 dev server。

## RTM 回填
寫到 `AgentConsole/docs/06_quality/rtm_backfill_W4F1.md`（ID｜實作檔｜自動測試｜狀態），涵蓋 US-I-01～10（FE 側）、US-S-01～08（FE 側）、UI-SCR-06／09、UI-OVL-*（新對話框）、UI-KPI 待審批卡、契約 §4 列到的 FE 項。不要直接改 RTM.md。

## 交卷
照 COMMON_CONTEXT〈交卷格式〉，另加〈契約漂移／缺口〉（你實作時發現契約欄位不夠用或矛盾的地方）與〈給 W4-F2 的提醒〉（共用元件、SSE 尚未碰、queries 慣例）。不准 commit／push、不派子 agent、不留背景行程。

## 主控裁決補充（2026-10-15，依獨立 Architect 審查；與本檔上文衝突時以本節與契約 v1.1 為準）
- `reason` 常數＝契約附錄 B 的中文逐字常數，集中在 `lib/api/reasons.ts`，不要自己造英文代碼。
- 輪詢地板：通知摘要與任何輪詢間隔 ≥ 10 秒（限流鍵是 JWT subject，同一使用者所有頁面共用每分鐘 100 次）。
- 設定頁「全部重置為預設值」＝對六個分類各呼叫一次 `POST /settings/{category}/reset`（契約 §1.5.6 分類級 reset；單鍵 reset 另有 §1.5.5）；`model.apiUrl` 的表單提示寫「完整的 chat-completions 端點 URL」；`monitor.refreshIntervalMs` 最小 10000。
- 匯入詳情：`parsedResult` 解析前為 null、`parsePath`／`lastParseErrors` 來自契約 v1.1 的 `ImportRecordResponse`；有界閘錯誤顯示 `lastParseErrors[]`。
- 事件時間軸不在你這棒；`task-trend` 沒有 `events[]`（F2 用 steps 端點）。
