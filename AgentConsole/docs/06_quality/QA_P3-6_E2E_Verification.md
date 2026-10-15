# QA 報告：Phase 3～6 獨立零信任驗證（W4-QA）

| 項目 | 內容 |
|------|------|
| 版本 | v1.0（W4-QA 產出；供主控收斂與 W5 修復使用） |
| 日期 | 2026-10-15 |
| 驗證者 | 獨立 QA（零信任：四位開發者的交卷只當「宣稱」，每一列親跑才設 `✅ 已驗證`） |
| 被驗 commit | HEAD `c3250dd7` |
| 依據 | 任務書 `docs/04_planning/agent_briefs/W4_QA_E2E.md`（含兩節〈主控裁決補充〉）、契約 `docs/02_architecture/API_Contract_P3-6.md`（§5 為最低驗證矩陣）、[RTM.md](RTM.md)、`Implementation_Plan.md` §2 W4 出口閘門 |
| 相關文件 | [RTM.md](RTM.md)（E2E 驗證欄的節號都指向本檔）、`frontend/tests/e2e/README.md`（真 Bridge specs 與 Docker 全棧的跑法） |

## 1. 摘要

**結論**：Phase 3～6 的主線——匯入（三條路徑）→ signoff 硬閘 → 執行（自治等級 1～5、暫停／恢復／取消／還原、審核閘）→ 監控（KPI、圖表、六條告警規則、報表）→ 設定（Token Guard、敏感鍵、測試連線、匯出入）——在「真後端＋真 Bridge＋mock claude」與「Docker 全棧經 nginx」兩種環境下都能走通。登記 **10 筆缺陷（P1 一筆、P2 三筆、P3 六筆）**與 21 筆觀察（§11）。最該優先處理的四件事：

1. **DEF-AC-003（P1）Bridge 映像缺 git**：Docker 全棧下任何批次一律 FAILED。本機（有 git）、mock 測試、Bridge 的 pytest 全綠，只有全棧真跑才現形。
2. **DEF-AC-007（P2）**：前端把 backend 暫時性 502 當成登入失效而登出（經 nginx 重啟 backend 時重現，mock 與本機直連都看不到）。
3. **DEF-AC-001（P2）**：匯入頁節點編輯對話框把 `maxRetries: null` 顯示成字面「null」並卡住「確定」（前端 mock 夾具沒有 `null` 欄位，所以先前測不到）。
4. **DEF-AC-009（P2）**：總覽頁單一分頁閒置時穩態每分鐘約 31 次請求（每 60 秒一輪 `task-trend` 扇出），專案數 ≥ 30 後一次快速導覽就會出現「無法載入儀表板資料：請求過於頻繁」；最終整套跑到後段的 `signoff` 親見。

**本回合實跑的數字**（逐條證據見 §3）：

- 後端 `gradlew clean build`：1,337 個測試全數成功、JaCoCo 指令 96％／分支 84％；前端 `lint`／`tsc`／`build` 皆 rc=0、`vitest` 44 個檔 585 個測試全數通過（Statements 95.43％）；Bridge `ruff` 乾淨、pytest 269 個通過（Windows 無 symlink 權限略過 4 個）。
- 本機整套 Playwright（真後端＋真 Bridge＋mock claude，乾淨資料庫）：108 支全數通過（33.8 分鐘，單一 worker；第 3 次整套，見 §4.7）：其中 DEF-AC-001（`p3`）與 DEF-AC-002（`p6`）兩支是 `test.fail` 預期失敗，其餘 106 支正向通過；0 略過；Docker 全棧（經 nginx）23 支全數通過（含兩支 `test.fail` 釘住 DEF-AC-007／008 的預期失敗）。
- 矩陣 A～J 全部實跑；契約 §5 的 E2E-01～12 逐一落成真後端 spec。除 spec 外另有 QA 腳本的 API 補測（§15）：告警六條規則、狀態機取樣、Token 單一任務／目標上限、Bridge 直連、NFR 量測、axe 無障礙掃描、備份還原計時演練。
- RTM 361 列：`✅ 已驗證` **331**、`🟡 部分` 17、`❌ 缺陷` 7、`✅ 實作+測試` 5、`⬜ 未開始` 1（§9）。

**本輪新增或修改的驗證資產**（皆在 `frontend/tests/e2e/`）：`realBackend.ts`（共用工具）、`p3-import`／`p4-execute`／`p4b-execute-more`／`p5-monitor`／`p6-settings`／`p7-cors-ratelimit` 六支真後端 spec、`markdown-editor.spec.ts`（UI-MD-01～08 的真瀏覽器實操）、`p8-docker-stack.stack.ts`＋`docker.config.ts`（Docker 全棧）、`support/fake_brain_bridge.py`（路徑 C 的假 Brain 版 Bridge）、README 兩節、以及 44 張新截圖。已登記但尚未修復的缺陷用 `test.fail` 釘住：缺陷還在時整支「預期失敗」＝綠燈，修好後會「意外通過」而變紅，提醒移除該行。

**主控請知悉**：（a）`e6d266f5` 動了 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`，字面上違反 `AgentConsole/CLAUDE.md` 鐵律 7（§15.3）；（b）Docker 全棧預設帶開發帳號與預設密碼，正式部署必須更換（O-06）；（c）本輪 `p3-import.spec.ts` 暴露一個我方的錯誤（缺 `bootstrapSettings`，乾淨資料庫上單獨跑會失敗），已修（§4.7）；（d）整套最終跑的第 2 次又暴露兩類我方 spec 的問題（Bridge 直寫資料庫的終態先於 Console 建審核項的時序、`signoff` 的限流額度被前一支 spec 用光），已修並以第 3 次整套 108 支全數通過確認（§4.7）；限流那一類同時是 DEF-AC-009 改判 P2 的新證據。

## 2. 環境與啟動

### 2.1 版本與主機

| 項目 | 值 |
|------|----|
| 作業系統 | Windows 11 專業版 10.0.26300（20 個邏輯核心、127.7GB 記憶體）；所有指令用 PowerShell 工具執行（Windows 上禁用 Bash 工具） |
| 被驗 commit | HEAD `c3250dd7`（四位開發者的 commit：`460bafb`、`c339e66d`、`8a7a09d3`、`6c213f20`） |
| 工具鏈 | Node v22.23.3／npm 10.9.9、OpenJDK 21.0.10、Python 3.11.9（根層 `.venv`）、Gradle 9.8.1、Next.js 16.4.0、Playwright 1.64.1（Chromium）、Docker 29.5.3／Compose 5.1.4 |
| 資料庫 | PostgreSQL 18.4（`pgvector/pgvector:pg18`；本機 e2e 用單一容器，Docker 全棧用 primary＋replica） |

### 2.2 本機 e2e 環境（矩陣 A、B、C、E、J）

埠：PostgreSQL 25433（這台機器的 5433 被原生 PG 佔用，5432 的 `autoclaude_pg` 不動）、backend 18080、Engine Bridge 18081、前端 3000（`npm run build` 後 standalone，`NEXT_PUBLIC_API_URL=http://localhost:18080` 於 build 時內嵌）。啟動順序**必須是 backend → Bridge → 重啟 backend**：Bridge 的 DB 模式要等 backend 的 Flyway 建好 `console` schema；backend 的連線探測環要在 Bridge 起來之後才看得到它（否則 `agentAvailability` 不是 100）。完整步驟見 `frontend/tests/e2e/README.md` 〈真 Bridge specs〉；以下是本輪實際使用的形態（`<…>` 換成自己的值，密碼與金鑰一律用環境變數，不寫進檔案）：

```bash
export E2E_ROOT=<ABS_PATH_TO_EMPTY_DIR>; mkdir -p "$E2E_ROOT"/{projects,workspace,quota-cache}
docker run -d --rm --name qa-pg -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -p 25433:5432 pgvector/pgvector:pg18
(cd AgentConsole/backend && SPRING_PROFILES_ACTIVE=e2e SERVER_PORT=18080 JWT_SECRET='<YOUR_JWT_SECRET_MIN_32_CHARS>' CONSOLE_ENCRYPTION_KEY='<YOUR_CONSOLE_ENCRYPTION_KEY>' \
  SPRING_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:25433/aisdlc SPRING_DATASOURCE_USERNAME=aisdlc SPRING_DATASOURCE_PASSWORD='<YOUR_PASSWORD>' \
  ENGINE_BRIDGE_URL=http://127.0.0.1:18081 CONSOLE_CORS_ALLOWED_ORIGINS=http://localhost:3000 \
  java -jar build/libs/console-0.0.1-SNAPSHOT.jar "--console.execution.mock-env[MOCK_CLAUDE_TRACE]=$E2E_ROOT/mock-trace.jsonl")
# Bridge 啟動前清掉 AUTOSDD_*／AUTOCLAUDE_*／MINIMAX_*／MOCK_CLAUDE_*，PATH 前置 .venv/bin（契約 §5.0.1）
(cd AgentConsole/engine-bridge && PATH="$PWD/../../.venv/bin:$PATH" AUTOSDD_QUOTA_CACHE_DIR="$E2E_ROOT/quota-cache" ENGINE_WORKSPACE="$E2E_ROOT/workspace" \
  BRIDGE_ALLOWED_PATH_ROOTS="$E2E_ROOT/projects:$E2E_ROOT/workspace" BRIDGE_DB_DSN='postgresql://aisdlc:<YOUR_PASSWORD>@127.0.0.1:25433/aisdlc' BRIDGE_DB_SCHEMA=console \
  BRIDGE_OUTBOUND_ALLOWLIST=127.0.0.1,localhost BRIDGE_STOP_GRACE_SECONDS=5 BRIDGE_INSTANCE=e2e-bridge \
  ../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 18081 --workers 1)
(cd AgentConsole/frontend && E2E_API_URL=http://localhost:18080 E2E_MODE=standalone E2E_FAKE_BRAIN=1 npx playwright test)
```

```powershell
$env:E2E_ROOT = "<ABS_PATH_TO_EMPTY_DIR>"; "projects", "workspace", "quota-cache" | ForEach-Object { New-Item -ItemType Directory -Force "$env:E2E_ROOT\$_" | Out-Null }
docker run -d --rm --name qa-pg -e POSTGRES_USER=aisdlc -e POSTGRES_DB=aisdlc -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -p 25433:5432 pgvector/pgvector:pg18
$env:SPRING_PROFILES_ACTIVE = "e2e"; $env:SERVER_PORT = "18080"; $env:JWT_SECRET = "<YOUR_JWT_SECRET_MIN_32_CHARS>"; $env:CONSOLE_ENCRYPTION_KEY = "<YOUR_CONSOLE_ENCRYPTION_KEY>"
$env:SPRING_DATASOURCE_URL = "jdbc:postgresql://127.0.0.1:25433/aisdlc"; $env:SPRING_DATASOURCE_USERNAME = "aisdlc"; $env:SPRING_DATASOURCE_PASSWORD = "<YOUR_PASSWORD>"
$env:ENGINE_BRIDGE_URL = "http://127.0.0.1:18081"; $env:CONSOLE_CORS_ALLOWED_ORIGINS = "http://localhost:3000"
Push-Location AgentConsole\backend; java -jar build\libs\console-0.0.1-SNAPSHOT.jar "--console.execution.mock-env[MOCK_CLAUDE_TRACE]=$env:E2E_ROOT\mock-trace.jsonl"; Pop-Location
# 另開終端（Bridge）：先清環境變數，再照 README 設 BRIDGE_*、PATH 前置 .venv\Scripts
Get-ChildItem Env: | Where-Object Name -match "^(AUTOSDD_|AUTOCLAUDE_|MINIMAX_|MOCK_CLAUDE_)" | ForEach-Object { Remove-Item "Env:$($_.Name)" }
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 18081 --workers 1; Pop-Location
Push-Location AgentConsole\frontend; $env:E2E_API_URL = "http://localhost:18080"; $env:E2E_MODE = "standalone"; $env:E2E_FAKE_BRAIN = "1"; npx playwright test; Pop-Location
```

本輪與 README 預設的差異：（a）最終整套用**假 Brain 版 Bridge**（`support/fake_brain_bridge.py`）搭配 `E2E_FAKE_BRAIN=1`，路徑 C 的 test 才不會略過；（b）設 `E2E_JWT_SECRET`（backend 的 `JWT_SECRET`，用來偽造過期 token）與 `E2E_RESTART_BACKEND`（停止並重啟 backend 的腳本，「重啟 backend 看 SSE 重連」那支才不會略過）；（c）假 LLM 伺服器由 `p3`／`p6` 自起（`realBackend.ts` 的 `FakeLlm`，綁 127.0.0.1，固定回三層 JSON 與 usage，另有 25 個任務的版本驗 422）。

### 2.3 Docker 全棧

啟動、情境與收尾見 §7.2。`.env` 由 `.env.example` 複製、填隨機測試值（`CONSOLE_ENCRYPTION_KEY` 以 `openssl rand -base64 32` 或等效指令產生），驗完刪除；全棧結束一律 `docker compose … down -v`。

### 2.4 收尾狀態

本輪起的 backend、Bridge、前端、PostgreSQL 容器、Docker 全棧在交卷前全部收掉；`.env` 已刪；證據見交卷附的行程與容器清單。

## 3. 閘門與重跑結果（Implementation_Plan §2 W4 出口閘門；本回合自跑）

| 閘門 | 指令 | rc | 關鍵輸出 |
|------|------|----|---------|
| 後端建置與測試 | `Push-Location AgentConsole\backend; .\gradlew.bat clean build --console=plain; Pop-Location` | 0 | `BUILD SUCCESSFUL in 1m 20s`；1,337 個測試全數成功（0 失敗、0 略過）；`checkstyleMain`／`checkstyleTest` 通過；`jacocoTestCoverageVerification` 通過 |
| 後端覆蓋率 | `jacocoTestReport` 的 `<tfoot>` | — | 指令覆蓋 96％（未涵蓋 1,658／46,560）、分支覆蓋 84％（未涵蓋 604／3,792）；門檻 80％ |
| 資料庫遷移 | 後端啟動時 Flyway | — | V1～V7 全 `success`（`init`、`seed system configs`、`review requests`、`monitor alerts`、`seed engine configs`、`audit log`、`console event anchors and token samples`）；JPA `ddl-auto=validate` 通過 |
| 前端 lint | `npm run lint` | 0 | 無輸出 |
| 前端型別 | `npx tsc --noEmit` | 0 | 無輸出 |
| 前端建置 | `npm run build`（`NEXT_PUBLIC_API_URL=http://localhost:18080`） | 0 | Next.js 16.4.0（Turbopack）編譯成功；20 條路由（含 §5.1 全部頁面與 `/api/health`） |
| 前端單元測試與覆蓋率 | `npx vitest run --coverage` | 0 | 44 個測試檔、585 個測試全數通過；Statements 95.43％（1,588／1,664）、Branches 88.92％（1,252／1,408）、Functions 97.56％（441／452）、Lines 96.95％（1,307／1,348）；門檻 70％ |
| 四區塊只在 `app/layout.tsx` 組裝 | `Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx \| Where-Object { $_.FullName -notlike '*\app\layout.tsx' } \| Select-String -Pattern 'TopRegion\|ToolsRegion\|BottomRegion'` | 0 | **無任何輸出**（另有 vitest 的靜態守衛 `四區塊共用版面只住 app/layout.tsx（UI-LAY-05）`） |
| Bridge lint | `ruff check AgentConsole\engine-bridge`（本目錄與 monorepo 根視角各一次） | 0 | `All checks passed!`（兩次） |
| Bridge 測試 | `python -m pytest -q`（`BRIDGE_TEST_DSN` 指向 PostgreSQL 容器，DB 整合測試實跑） | 0 | 269 個通過、4 個略過（Windows 無 symlink 權限：見 §12）；蒐集 273 個 |
| Bridge 健康 | `GET /health` | — | `status:ok`、引擎版本、SDD LATEST、`db.ok`（§15.1） |
| 根層檔案鎖 | `python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v`（在 `tools\tests`） | 0 | 7 個測試 OK |
| 全鏈 Playwright | `npx playwright test`（本機 e2e 環境、乾淨資料庫、假 Brain 版 Bridge；§2.2） | 0 | 108 支全數通過（33.8 分鐘，單一 worker；第 3 次整套，見 §4.7）：其中 DEF-AC-001（`p3`）與 DEF-AC-002（`p6`）兩支是 `test.fail` 預期失敗，其餘 106 支正向通過；0 略過 |
| Docker 全棧 Playwright | `npx playwright test -c tests/e2e/docker.config.ts`（§7.2） | 0 | 23 支全數通過（5.3 分鐘）：`p8` 7 支（其中重啟 backend 與 nginx error log 兩支是 `test.fail` 釘住 DEF-AC-007／008 的預期失敗）＋既有真後端 specs 16 支 |
| 6 支 mock specs | 含在上方整套內；稍早也單獨跑過一次（`npx playwright test`＋該 6 個檔） | 0 | 44 支全數通過（整套內同樣包含 44 支） |
| 消毒字元集 parity | 矩陣 C（§6） | — | 三處集合相等 |
| RTM 計數與文件鎖 | §9、§3 末段 | — | 根層基線站點鎖 `tools/check_pytest_baseline_sites.py` 在 RTM 套用與本報告寫入後 rc=0（114 支未納管存量檔不變）；`AgentConsole/CLAUDE.md` 164 行（上限 200）、`README.md` 78 行（上限 80）；`RTM.md` 361 列、`⬜ 未開始` 1 列、`✅ 已驗證` 331 列（§9.2 的兩條指令現查） |

## 4. 矩陣 A：契約 §5 全部情境（Playwright 真後端 specs）

### 4.0 契約情境與 spec 對照

| 契約情境 | 驗證檔（`frontend/tests/e2e/`） | 補充 |
|----------|-------------------------------|------|
| E2E-01 匯入貼文字（路徑 B）→ 編輯 → signoff → confirm | `p3-import.spec.ts` | 另驗路徑 A（真 `/sdd/compile`）、路徑 C（真 Bridge＋假 Brain）、PDF／DOCX 真檔、歷史重開、唯讀角色 |
| E2E-02 execute 未 signoff → 409 | `p4-execute.spec.ts`（E2E-02）、`p4b-execute-more.spec.ts`（前置檢查） | §5.1 的 API 矩陣 |
| E2E-03 execute 成功 → SSE → COMPLETED → metrics 對得上 | `p4-execute.spec.ts`（Level 4）、`p5-monitor.spec.ts`（M1） | §8 SSE 延遲 |
| E2E-04 自治閘 Level 1／2／3 | `p4-execute.spec.ts`（Level 1、Level 3）、`p4b-execute-more.spec.ts`（等級 2） | — |
| E2E-05 ESCALATED → RETRY → 再失敗 → SKIP（含變體 V1～V4） | `p4-execute.spec.ts`（ESCALATED）、`p4b-execute-more.spec.ts`（REJECT、變體 V1／V3／V4） | §15.4 |
| E2E-06 cancel | `p4-execute.spec.ts`（取消） | §10.2 |
| E2E-07 restore | `p4-execute.spec.ts`（restore；含 PAUSED 批次，AR-01 已修） | — |
| E2E-08 Token 預算告警 | `p4-execute.spec.ts`（Token 預算告警） | §15.4（單一任務／目標上限） |
| E2E-09 系統參數 | `p6-settings.spec.ts` | — |
| E2E-10 test-connection 的 SSRF 拒絕 | `p6-settings.spec.ts`（測試連線） | — |
| E2E-11 限流 | `p7-cors-ratelimit.spec.ts` | §5.3、§7.3 |
| E2E-12 SSE 認證、重播、終態語意 | `p4-execute.spec.ts`（E2E-12 SSE；斷線重連；重新整理終態批次） | §5.2、§10.1 |

所有執行類情境一律用 **Level 4 一路跑完**（主控裁決），spec 內每個 run 的任務數 ≤ 5；只有 §15.4 的告警腳本（QA 腳本，不是 spec）為了造出夠長的批次用過 25 個任務的夾具。`realBackend.ts` 提供共用工具：REST 呼叫、`ensureQuota()`（情境前確認限流餘額）、夾具（PRJ-A／PRJ-B）、`FakeLlm`（假 OpenAI 相容伺服器）、SSE 解析。

### 4.1 `p3-import.spec.ts`（匯入，8 支）

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | 貼文字 → 路徑 B → 有界閘 422 三條 → 修正重試 → 編輯 → signoff → confirm → 專案全部 signedOff | UI 全鏈：文件帶 `GATE_UI3` 標記讓假模型回「三道閘都違規」的樹→三條錯誤全列、不截斷（`prompt 不可為空`／`步驟上限（≤ 24）`／`依賴成環（Kahn 無環）`，位置 `goals[0].tasks[1].description`／`goals[0].tasks`／`goals[0].dependsOn`）；記錄仍 `UPLOADED`、`lastParseErrors` 3 筆、`parsedResult` 為 null；修正後樹狀預覽、編輯（改名、新增、刪除、儲存撤銷 signoff）、signoff 對話框（審批者預設帶 operator）、confirm 前的 409「草案尚未 signoff」、confirm 後專案／目標／任務全部 `signedOff` |
| 2 | 上傳 .md 檔（multipart）→ 解析；副檔名不符當場擋下；歷史記錄重開並還原；放棄 | UI 上傳、副檔名檢查、歷史列表重開後由 `lastParseErrors` 還原同一份錯誤清單 |
| 3 | E2E-01 API 序列 | 有界閘八種變體（422、`lastParseErrors`、重試後清空）、消毒變體（禁用字元 400、regex 無法編譯 400）、`signoff`／`confirm` 序列與狀態機（`UPLOADED→PARSED→REVIEWING→IMPORTED`／`REJECTED`，終態對 `parse`／`editResult`／`signoff`／`confirm`／`reject` 一律 409）、上傳變體（413／415／422／400） |
| 4 | 路徑 A（凍結 SDD 規格，真 Bridge 的 `/sdd/compile`） | 探測 `executionPath` 與明示 `specDir` 皆 `path=SDD`、不呼叫模型（`FakeLlm` 零次）、30 個合約切成 24＋6 兩個目標（名稱「brownfield（第 1 批）」「（第 2 批）」、`g2.dependsOn=[g1]`）、規格存在但未凍結→422「SDD 規格檢查未通過」（`details.bridgeReason=spec_not_frozen`，記錄仍 `UPLOADED`）、signoff→confirm |
| 5 | 上傳 PDF 與 DOCX（本檔獨立產生的真檔） | 擷取文字（PDF 含括號、DOCX 含 `&` 與 `<>`）、`sourceType`、擷取結果進入路徑 B 的提示詞；不用後端測試的 PDFBox／POI 夾具 |
| 6 | 路徑 C（高階目標拆解，真 Bridge＋假 Brain；`E2E_FAKE_BRAIN=1`） | 四種有界閘皆 422（`max_steps`／`cycle`／`empty_prompt`／`brain_failed`）；decompose 成功（3 步驟、`warnings` 含 `passcriteria_placeholder`×2、`aiModel`／`tokenUsed` 為 null）；signoff 時 Console 才呼叫 Bridge `approve`（草案檔 `signed_off=true`＋`approver`）；confirm（1 目標 3 任務）；專案可被引擎執行並 COMPLETED（3,720 token） |
| 7 | DEF-AC-001（`test.fail`） | AI 解析結果的 `null` 欄位在節點編輯對話框不得顯示成字面「null」——目前是已知缺陷（§11） |
| 8 | 唯讀角色（VIEWER） | 看得到頁面與歷史，拖放區、欄位、開始解析全部停用；後端對 viewer 寫入 403 |

截圖入庫：`p3-import-dropzone`、`-step1`、`-parsing`、`-gate-errors`、`-step2`、`-signoff-dialog`、`-signed-off`、`-imported-project`、`-history`、`-viewer`。

### 4.2 `p4-execute.spec.ts`（執行，12 支）

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | Level 4 一路跑完（E2E-03） | SSE 即時日誌與進度、Token 帳（3,720）、DAG 節點隨批次變綠、終態收工、`steps` 6 列（`STARTED`／`COMPLETED` 成對、`stepNumber` 嚴格遞增、`tokensUsed` 1,240） |
| 2 | Level 3（E2E-04） | 目標邊界 PAUSED → `GOAL_COMPLETED` 待審核（通過／重試／拒絕、無跳過）→ 通過 → 跑完 |
| 3 | Level 1（E2E-04） | 第一步後 PAUSED＋`TASK_CONFIRM`→ 通過 → 第二次暫停 → 通過 → 跑完 |
| 4 | ESCALATED（`[FAIL_ME]`；E2E-05；矩陣 I） | 終態後待審核卡仍出現（RETRY／SKIP／REJECT 可按、通過停用）→ `APPROVE` 直打 409「此審核項不允許該決定」→ RETRY 同批次還原重跑再失敗（第二個審核項）→ SKIP 另開 Run #2 跑完（1 / 1 任務完成、Token 1,240、任務二成為跳過狀態、專案 `COMPLETED`）；日誌有嚴重等級的引擎告警行 |
| 5 | restore（E2E-07） | 終態批次從 `after-G1-T1` 還原續跑（Token 累計跨 restore、checkpoints 只增不改）；PAUSED 批次 restore（AR-01 已修）並自動拒絕舊審核項 |
| 6 | 取消（E2E-06） | PAUSED 時取消（確認對話框）→ 即時 `CANCELLED`、待決審核項自動拒絕、專案回 `READY`、可重新執行 |
| 7 | Token 預算告警（E2E-08） | 預算 1,500：超出後自動暫停且不建審核項；告警恰兩筆（`TOKEN_BUDGET_WARNING` 訊息含「1240 / 1500」、`TOKEN_BUDGET_EXCEEDED`）；恢復後跑完（6,200）且不再被暫停（去重） |
| 8 | SSE 斷線重連（真 `SseEmitter`；矩陣 I） | 重啟 backend 切斷串流→前端顯示重連中→連回後帶 `Last-Event-ID`、已有事件不重複、後續事件照常到（需 `E2E_RESTART_BACKEND`） |
| 9 | 重新整理終態批次（矩陣 I） | 頁面還原狀態，不為終態連線無限重連（終態 204） |
| 10 | 跨 Phase | 匯入（假 LLM）→ signoff → confirm → 專案頁 → 執行頁 Level 3 啟動 → 一路跑完（匯入專案可被引擎執行）；匯入等級＝執行頁預設 |
| 11 | E2E-02 | execute 未 signoff → 409（`details` 分層列出）、無副作用；逐步 signoff（專案、目標、任務）後才放行；角色（viewer 403）、不存在 404、`autonomyLevel:11`→400、`maxRetries:25`→400；執行中再 execute→409「專案正在執行中」 |
| 12 | E2E-12 SSE | 認證（401 JSON：`UNAUTHENTICATED`／`TOKEN_INVALID`／`TOKEN_EXPIRED`）、標頭優先、404、重播（`Last-Event-ID`）、終態 204、`/metrics` 三則快照 id（`<S>.1`／`.2`／`.3`）、PAUSED 的 keep-alive、預檢（需 `E2E_JWT_SECRET`） |

### 4.3 `p4b-execute-more.spec.ts`（補充情境，9 支）

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | 執行範圍（US-E-02） | 只勾目標 1→只跑 G1 的兩個任務（`G1-T1`、`G1-T2` 各成對）、專案回 `READY`、G2 仍 `PENDING`；重新整理後以預設範圍跑完剩下的 |
| 2 | 手動暫停／恢復（US-E-04／05） | RUNNING 時按暫停→在步驟邊界 `PAUSED`（沒有懸空的 `STARTED`）→暫停期間不前進→恢復後跑完，每步恰一次、Token 6,200 |
| 3 | 等級 2（API-AUT-02） | G1 最後一步之後 PAUSED＋`GOAL_CONFIRM`（只有通過／拒絕）→通過→跑完 |
| 4 | 審核 REJECT（契約 §3.5.3） | 等級 1 的 `TASK_CONFIRM`→run `CANCELLED`；等級 3 的 `GOAL_COMPLETED`→run `CANCELLED` 且被審目標 `FAILED`（人類判定優先） |
| 5 | 審核 REJECT（ESCALATED） | 只關閉審核項：run 維持 `FAILED`、任務維持失敗、不呼叫 Bridge |
| 6 | E2E-05 變體 | V1 第一步失敗的 RETRY（沒有還原點→後續批次）、V3 新批次取代舊審核項（`decided_by=system`、`comment` 含「已由第 2 批次取代」）、V4 等級 5 與等級 4 同樣建 ESCALATED 審核項（API-AUT-05） |
| 7 | execute 前置檢查補充 | `#7b` 依賴未選未完成→409「所選目標依賴未完成的前置目標」（`details.missingGoalIds`）；`#10` 併發兩個 execute 只放行一個（輸家 409：專案正在執行中，或同專案同路徑鎖）、批次列補償刪除（只剩 1 筆）；`#3` 執行中再啟動→409；`#7c` 全部跑完再啟動→409「沒有可執行的任務」 |
| 8 | 路徑 A 匯入的專案被引擎執行 | 凍結規格→signoff→confirm→Level 4→`COMPLETED`（3/3、3,720 token），evaluator（`pytest tests -k AT_00n_1_1`）真的在專案目錄跑了（留下 `.pytest_cache`） |
| 9 | 連續失敗告警（API-ALR-03） | 本輪新增：`scope.taskIds` 逐批各失敗一個任務，第 3 個觸發 `CONSECUTIVE_FAILURES`（§15.4） |

### 4.4 `p5-monitor.spec.ts`（監控，4 支）

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | M1 指標卡與圖表 | UI 數字＝API 回的值；契約 E2E-03 步驟 9 的固定數字（完成率／成功率 100、Token 總消耗 3,720、預算使用率 3.7％、Agent 可用率 100、平均重試 0.00）；任務趨勢堆疊面積圖、Token 趨勢折線（`aria-label` 含最新累計與預算）、狀態分佈柱、執行時間分佈 3 柱、重試次數分佈 6 柱 |
| 2 | M2 批次比較／日誌／事件時間軸／Agent | Run #1 失敗（成功率 50.0％）、Run #2 完成；選批次改查該批次；ERROR／關鍵字篩選、由新到舊；事件時間軸 ≥ 5 項（T1 開始／完成、T2 開始／重試／失敗）；Agent 連線狀態、可用率、目前任務 |
| 3 | 告警 | 升級告警未確認→確認（樂觀更新後以伺服器為準）；viewer 看得到但不能確認；去重；M3 兩筆預算告警（預算使用率 413.3％） |
| 4 | 匯出報表 | CSV 下載（檔名取自 `Content-Disposition`＝CORS 暴露）、BOM、四段內容；PDF 回 501 顯示「尚未提供」 |

截圖入庫：`p5-monitor-*.png`。

### 4.5 `p6-settings.spec.ts`（設定，8 支）

| # | 情境 | 驗證重點 |
|---|------|---------|
| 1 | 六個分類 tab | 參數列數 9／11／10／10／6／4＝50 鍵、標題、控制項型別、影響提示與誠實標示；加密鍵一律遮罩（`••••••••`＋`hasValue`） |
| 2 | 改一個數值並儲存 | 只送有變動的鍵→歷史多一列→重置；本地驗證紅字不送請求 |
| 3 | Token Guard | 前端鏡射 `halt>compact`（不送請求）；成對套用一次 PUT；後端跨鍵 400 的原因逐字（`errors[].field＝haltThresholdPct`） |
| 4 | 敏感鍵（API Key） | 二次確認才送 `confirm=true`、歷史只記遮罩、ADMIN 才能顯示明文（`reveal=true`，operator／viewer 403） |
| 5 | 測試連線 | 對假 server 成功（金鑰只走 `Authorization`、不回顯）；對 `http://10.0.0.1` 被 SSRF 規則拒絕且沒有任何連線 |
| 6 | 匯出入 | 匯出（50 鍵、加密鍵為 `<encrypted>`）→改一個值匯入（`applied=1`）→異常檔 400／413／415；全部重置 |
| 7 | DEF-AC-002（`test.fail`） | 匯出後原樣匯入（一個值都沒改）不得出現 errors——目前是已知缺陷（§11） |
| 8 | 角色 | operator／viewer 看得到參數與歷史，輸入、重置、儲存、匯出入、測試連線全部停用；後端對寫入 403 |

截圖入庫：`p6-settings-*.png`。

### 4.6 `p7-cors-ratelimit.spec.ts`（跨來源標頭與限流，1 支）

真瀏覽器 `fetch`（origin 3000→18080）把 viewer 的額度打滿：第 N 次得 429，`Retry-After` 在瀏覽器內可讀（1～60）、`X-Trace-Id` 可讀且等於錯誤封包的 `traceId`、body 為 `{code:429, reason:"超過每分鐘 100 次請求上限", details.retryAfterSeconds}`；超限者做寫入先得 429（早於授權的 403）；伺服器端看到 `X-RateLimit-Limit=100`、`Remaining=0`；operator 不受影響、`/actuator/health` 仍 200；等 `Retry-After` 秒後 viewer 恢復。`X-RateLimit-*` 在瀏覽器內讀不到（O-01，契約只要求暴露 `Retry-After` 等三個）。

### 4.7 既有 specs、mock specs 與新增的 Markdown 編輯器 spec

- **既有真後端 specs**（`chart`、`crud-flow`、`design-system`、`shells-and-layout`、`signoff`，共 16 支）：本機與 Docker 全棧各跑一次。Docker 乾淨庫經 nginx 全數通過；本機資料庫有 2,050 個專案時會被限流擋下（DEF-AC-009，§8），最終整套是在乾淨資料庫上跑。`crud-flow.spec.ts` 第 30 行（`kpi-week-done` 改驗整數）是 F2 改的、先前未對真後端驗過，本輪驗過。
- **mock specs**（`*.mock.spec.ts`，不需後端，共 44 支）：本輪重跑全數通過。這批 spec 會重寫自己名稱的已追蹤截圖（`06-`、`07-`、`08-`、`09-`、`00-notification`、`01-dashboard-*`），QA 每次跑完都以 HEAD 版本寫回，不留差異。
- **整套 108 支的組成**（第 3 次整套的逐檔計數）：本輪新寫的 7 個檔共 47 支（`p3` 8、`p4` 12、`p4b` 9、`p5` 4、`p6` 8、`p7` 1、`markdown-editor` 5）、`*.mock.spec.ts` 6 個檔共 44 支、既有真後端 specs 5 個檔共 16 支、`task-retry.spec.ts` 1 支（route mock，只有登入走真後端）。
- **`markdown-editor.spec.ts`（QA 新增，5 支）**：真瀏覽器在「新建專案」Dialog 的說明欄逐項實操 UI-MD-01～08——即時預覽（左原始碼右預覽）、GFM 表格（兩欄表頭）、程式碼區塊語言高亮（`code.language-ts` 帶 `hljs` class，內容為 prism 的 `token` span）、Checklist（已勾／未勾）、原始碼著色（`token title`／`bold`／`code`／`table`）、工具列十一個語法按鈕（粗體、核取清單、表格按下去會寫入語法）、匯入 .md（讀入並覆蓋、`.pdf` 與超過 1MB 被擋下並提示、欄位不變）、匯出 .md（空白時停用、下載內容與欄位逐字相同）。截圖：`30-markdown-editor.png`。
- **`p4b` 第 9 支與 `markdown-editor.spec.ts` 都是本輪新增**；`p3-import.spec.ts` 在最終整套第一次跑時暴露一個我方的錯誤：它的 `beforeEach` 只設 `model.apiUrl` 與 `model.apiKey`，`model.name` 要靠其他 spec 的 `bootstrapSettings` 先設，在乾淨資料庫上單獨跑會得 `Expected "e2e-model" Received "MiniMax-M2.7"`；已改為 `beforeAll` 自己呼叫 `bootstrapSettings`。
- **整套最終跑共跑了三次；前兩次暴露的都是我方 spec 的時序或額度問題，沒有改動任何被測程式**：
  - 第 2 次（乾淨資料庫）：102 支通過、3 支失敗、3 支未執行。其一是 `p4b` 的 ALR-03：Bridge 直接寫資料庫的終態比 Console 消費事件建審核項早一步（契約 §2.4），`GET run` 看到 `FAILED` 時 `pendingReviews` 還是空的。其二是 `signoff.spec.ts`：前一支 `shells-and-layout` 六支合計約 4.3 秒就把 operator 每分鐘 100 次的額度用光（總覽頁每次載入就要 30 次上下，DEF-AC-009），`signoff` 的總覽頁出現「無法載入儀表板資料：請求過於頻繁」，第二個情境的 `beforeAll` 在 `POST /projects` 也得 429，其後三支因 `beforeAll` 失敗而未執行。
  - 修正：新增 `waitForQuota`（`helpers.ts`），`signoff.spec.ts` 每個情境前先確認額度餘額；`p4b`（V1／V3／V4、ALR-03）、`p5` 的 `beforeAll`、`p4` 的 RST1 暫停改成輪詢到審核項出現才取（同型時序）。針對性複驗：先把 operator 的額度打到只剩 2，再一起跑 ALR-03 與 `signoff` 5 支，6 支全數通過（2.3 分鐘；ALR-03 排在前面跑了 1.2 分鐘，視窗已回滿，`signoff` 第 3 支另在 `beforeEach` 等了約 1 分鐘）。
  - 第 3 次（重置成乾淨資料庫後重跑整套）：**108 支全數通過、`rc=0`（33.8 分鐘）**，其中 `signoff` 第 4 支在 `beforeEach` 等了約 1 分鐘讓視窗回滿，守衛在整套內確實起了作用。

## 5. 矩陣 B：後端 API 層（不經前端）

QA 腳本（PowerShell＋`curl.exe`，暫存不入庫）對本機 backend（18080）直接打；輪詢一律用 viewer、寫入用 operator、設定用 admin（限流以 JWT subject 計）。

### 5.1 execute 未 signoff → 409（E2E-02）

```
POST /api/v1/projects/{id}/execute {}
HTTP 409 {"code":409,"message":"草案未經人工審批，禁止執行","reason":"未經人工審批的草案不可執行","errors":[],"details":{"unsignedTaskIds":[…3 個…],"unsignedProjectId":"…","unsignedGoalIds":[…2 個…]}}
executions totalElements=0（無副作用）；project status=DRAFT
（只 signoff 專案後）409 details＝2 個目標＋3 個任務未簽
（再 signoff 兩個目標與兩個任務後）409 details＝只剩第三個任務
viewer → 403 reason=ACCESS_DENIED；不存在的專案 → 404；autonomyLevel:11 → 400 errors=[autonomyLevel 必須介於 1 到 10]；scope.mode=ALL 又帶 goalIds → 400；PUT /tasks/{id} {maxRetries:25} → 400 errors=[maxRetries 不可超過 20]
```

被擋下的啟動沒有副作用（批次列補償刪除、專案維持 `DRAFT`）。`details` 的 `unsignedProjectId` 等可為 null 的欄位，「缺席」與 `null` 等價（任務書裁決）。

### 5.2 兩條 SSE 端點、`Last-Event-ID` 重播、認證

```powershell
curl.exe -N -s -D headers -o logs.txt "http://127.0.0.1:18080/api/v1/stream/executions/<runId>/logs?access_token=<operator access token>"
```

`/logs` 前 5 行與標頭：

```
HTTP/1.1 200
Content-Type: text/event-stream;charset=UTF-8
Cache-Control: no-cache, no-store
X-Accel-Buffering: no
X-RateLimit-Limit: 100

retry:3000

id:1
event:status-change
data:{"seq":1,"ts":"2026-10-15T11:19:17.956387+00:00","runStatus":"INITIALIZING","bridgeStatus":"INITIALIZING","reason":"run 已建立，準備啟動引擎"}
```

`/metrics` 前 5 行：`retry:3000`、`id:2.1`、`event:progress-update`、`data:{"seq":2,…,"completedSteps":0,"totalSteps":3,"progressPct":0.0}`。

| 項目 | 結果（逐字或節錄） |
|------|-------------------|
| `/logs` 全部 id | `1 2 3 … 15 17 18 … 22 24 … 28 30 31 32 33`（嚴格遞增；缺號 16、23、29 是 token 事件，只送 `/metrics`，下一列的序列裡有 `16`／`16.1`、`23`／`23.1`、`29`／`29.1`） |
| `/metrics` 全部 id | `2.1 2.2 2.3 14 16 16.1 20 20.1 21 23 23.1 26 26.1 27 29 29.1 32 32.1 33 33.1`（以 `(seq, n)` 比較嚴格遞增、無重複） |
| `Last-Event-ID: 5` | 重播 id `6 7 8 … 33`＝原序列中 id>5 的後綴，各一次：`True` |
| 終態後重連 | `/logs` 帶 `Last-Event-ID: 33`→**204**；`/metrics` 帶 `33.3`→**204**；帶 `33.1`→仍送終態快照 `33.1`／`33.2`／`33.3` 後關閉 |
| `Last-Event-ID: garbage` | 視為未帶，重播最後 `tail` 則（本例 30 則框架） |
| `?tail=0`（無 `Last-Event-ID`） | 重播集合為空且已終態→204 |
| 認證 | 無 token→401 `UNAUTHENTICATED`；`access_token=garbage`→401 `TOKEN_INVALID`；已過期的 access token→401 `TOKEN_EXPIRED`（「請使用 refresh token 續期」）；refresh token 放進 `access_token`→401 `TOKEN_INVALID`；標頭 token 有效而查詢參數無效→200（標頭優先）；不存在的 runId→404 |
| 角色 | viewer 的 `execute`／`cancel`→403 `ACCESS_DENIED`；無 token 的 `GET /projects`→401 |

### 5.3 限流 101 次→429（E2E-11）

```
共 101 次；前 100 次狀態分佈=200x100；最後一次=429
X-RateLimit-Remaining 前 3 個值=99,98,97；第 100 個=0
429 標頭: Retry-After=60 X-RateLimit-Limit=100 X-RateLimit-Remaining=0
429 body: {"code":429,"message":"請求過於頻繁：每分鐘最多 100 次，請 60 秒後再試","reason":"超過每分鐘 100 次請求上限","errors":[],"details":{"retryAfterSeconds":60,"limit":100,"windowSeconds":60},…}
被限流的 viewer 打 /actuator/health → HTTP 200（不計入）；同一時間 operator GET /projects → HTTP 200（桶以使用者隔離）
等 61 秒後 viewer 再請求 → 200
未認證（XFF=203.0.113.77）：前 100 次=401、第 101 次=429；換 XFF=203.0.113.78 → 401（IP 桶隔離）；未認證請求不吃 operator 額度
```

固定視窗每 60 秒 100 次；UI 與 REST 共用同一個桶，所以真後端 specs 一律以 `ensureQuota()` 在情境前確認餘額。經 nginx 的同項量測與 `X-Forwarded-For` 可繞過的觀察見 §7.3。

### 5.4 CORS（跨來源 3000→18080）

| 請求 | 結果 |
|------|------|
| `OPTIONS …/stream/executions/{id}/logs`，`Origin: http://localhost:3000`、`Access-Control-Request-Headers: last-event-id,authorization` | 200，`Access-Control-Allow-Origin: http://localhost:3000`、`Allow-Methods: GET,POST,PUT,PATCH,DELETE,OPTIONS`、`Allow-Headers: last-event-id, authorization`、`Max-Age: 3600` |
| `GET /executions/{id}`（帶 `Origin`） | `Access-Control-Expose-Headers: X-Trace-Id, X-Follow-Up-Run-Id, Retry-After, Content-Disposition` |
| `GET /monitor/projects/{id}/report?format=csv` | `Content-Disposition: attachment; filename="monitor-report-e783327a-20261015-1119.csv"`（暴露給瀏覽器）、`Content-Type: text/csv;charset=UTF-8` |
| SSE 回應 | 同樣帶 `Access-Control-Allow-Origin` 與 `Expose-Headers`；`X-Accel-Buffering: no` |
| 瀏覽器內的可讀性（spec） | `p7-cors-ratelimit.spec.ts`：429 的 `Retry-After` 與 `X-Trace-Id` 在 JS 內可讀；`p4-execute.spec.ts`（SKIP 後前端切到後續批次）讀到 `X-Follow-Up-Run-Id`；`p5-monitor.spec.ts`（匯出報表）讀到 CSV 檔名（O-01：`X-RateLimit-*` 未暴露） |

`X-Follow-Up-Run-Id`、`Content-Disposition`、`Retry-After` 三個都在 Expose-Headers 內，任務書要求的「缺任一登缺陷」**未觸發**。

### 5.5 Bridge 關掉時 `GET /executions/{runId}` 仍 200 且 `bridge.connected=false`

```
準備：已完成批次 R1；PAUSED 批次 R2（Level 1）；尚未執行的專案 P3
Bridge 開著：GET run(R1) → 200 bridge={"connected":true,"instance":"e2e-bridge","status":"COMPLETED","runKnown":true,…}
殺掉 Bridge（18081 監聽數 0）
GET /executions/{R1}      → HTTP 200 status=COMPLETED completedSteps=3/3 bridge={"connected":false,…}
GET /executions/{R2}      → HTTP 200 status=PAUSED bridge.connected=False pendingReviews=1（來自 DB）
POST /projects/{P3}/execute → HTTP 502 reason=引擎橋接服務無法連線；executions totalElements=0（補償刪除）；project status=DRAFT
POST /executions/{R2}/cancel → HTTP 502 reason=引擎橋接服務無法連線
SSE /logs（R2）：retry:3000；event:alert data:{…"origin":"CONSOLE","code":"BRIDGE_UNREACHABLE","severity":"WARNING","message":"Engine Bridge 暫時無法連線，將自動重試"}（無 id 行）；其後持續 :keep-alive
等 35 秒（探測環 30 秒一次）：notifications/summary bridgeConnected=False
重啟 Bridge：GET run(R2) → bridge.connected=True status=PAUSED runKnown=True；SSE 重播 22 個框架（皆帶 id：log×17、review-request×1、status-change×4）；新專案 execute → 201 → COMPLETED；摘要 bridgeConnected=True
```

**判定**：全部符合契約 §1.2.3、§2.8：Bridge 死時讀取類端點照常、寫入類端點 502 並補償、SSE 不關閉且暫態告警不帶 `id:`、恢復後自動補齊。

## 6. 矩陣 C：消毒字元集 parity（Architecture §8.3）

**方法**：QA 腳本（暫存、不入庫）做兩件事。靜態：載入 AutoClaude 的 `BASE_DENY_CHARS`（SSOT）、Bridge 的 `app.security.DENY_CHARS`／`CONTROL_CHARS`、解析後端 `PassCriteriaSanitizer` 的常數，比對集合。動態：對每個字元，分別打後端（建任務帶 `evaluatorCommand`）與 Bridge（`POST /autoclaude/runs` 的 `evaluator_command`），比對「擋或放行」是否一致。

**輸出節錄**（逐字）：

```
AutoClaude SSOT BASE_DENY_CHARS : !$&;<>`~ (8)
Bridge app.security.DENY_CHARS  : !$&;<>`~ (8)
後端 PassCriteriaSanitizer.DENY : !$&;<>`~ (8)
三者集合相等: True
Bridge CONTROL_CHARS: ['0x0', '0xa', '0xd'] ；後端以 Character.isISOControl 擋控制字元: True
Bridge 的控制字元 ⊂ 後端的 isISOControl（後端不比 Bridge 鬆）: True
後端擋、Bridge 放行（後端比 Bridge 嚴，安全方向）: []
Bridge 擋、後端放行（會讓 execute 才在 Bridge 被 422，違反雙層一致）: []
```

動態表：`! $ & ; < > ` ~` 與 `\n`、`\r`、`\x00` 共 11 個字元，後端與 Bridge **皆擋**；`| ( ) { } * ? [ ] # % ^ : , . ' " / - _ = 空白` 後端**放行**（與 SSOT 相同，這些不在黑名單）。`\t` 後端擋（`isISOControl`）、Bridge 不在 `CONTROL_CHARS`，屬「後端比 Bridge 嚴」的安全方向，不是缺陷。

**判定**：三處常數集合相等，雙層行為一致；後端不比 Bridge 鬆。矩陣 C 通過（影響列：NFR-SEC-03、BR-02）。

## 7. 矩陣 D／H：Docker 全棧（經 nginx）

全棧不載入 e2e profile（沒有 `allow-loopback`、沒有 `mock-env`），所以匯入走路徑 A（凍結規格放進 Bridge 容器的 `/workspace`）、執行用映像內建的 `aisdlc-mock-claude`；`p3`～`p7` 那批（假 LLM 伺服器綁 127.0.0.1）不在這裡跑。

### 7.1 矩陣 H：`CONSOLE_ENCRYPTION_KEY` 缺值（DEF-AC-006）

做法：`.env` 由 `.env.example` 複製，其餘變數填隨機測試值，**刻意整行不放** `CONSOLE_ENCRYPTION_KEY`（QA 腳本 `d_env`，驗完刪除）。

| 步驟 | 結果（逐字或節錄） |
|------|-------------------|
| `docker compose … config` | rc=0，輸出 `CONSOLE_ENCRYPTION_KEY: ""`（對照：缺 `POSTGRES_PASSWORD` 時 rc=1：`required variable POSTGRES_PASSWORD is missing a value: POSTGRES_PASSWORD is required`） |
| `docker compose … up -d --build` | rc=1，耗時 155 秒：`dependency failed to start: container aisdlc-backend is unhealthy`；backend 容器 `Restarting (1)`（重啟次數 8）、nginx 停在 `Created` |
| backend 容器日誌 | `APPLICATION FAILED TO START` ／ `Property: console.encryption.key` ／ `Value: ""` ／ `Origin: System Environment Property "CONSOLE_ENCRYPTION_KEY"` ／ `Reason: 環境變數 CONSOLE_ENCRYPTION_KEY 必填（base64 編碼的 32 bytes，可用 openssl rand -base64 32 產生）` |
| 補上金鑰後 `up -d --wait` | 映像已建好時 18～50 秒內 14 個長駐服務全 healthy（`minio-certs`、`minio-init` 是一次性 job，Exited 0） |

**判定**：應用層 fail-closed 正確（缺金鑰拒絕啟動、訊息可讀）。但 compose 層放行空值，要等 155 秒、只看到「container is unhealthy」才知道失敗，且一路上 backend 無限重啟。登 **DEF-AC-006（P3）**，建議把 compose 改成 `${CONSOLE_ENCRYPTION_KEY:?請設定}`，與 `POSTGRES_PASSWORD` 一樣在 `config` 階段就失敗。

### 7.2 全棧情境（矩陣 D、I）

啟動與收尾（bash／PowerShell 並列；`.env` 的值一律自填，不入庫）：

```bash
(cd AgentConsole && cp .env.example .env)   # 之後把 <YOUR_...> 佔位符換成測試值；CONSOLE_ENCRYPTION_KEY 以 openssl rand -base64 32 產生
(cd AgentConsole && docker compose --profile db --profile app --profile full up -d --build --wait)
(cd AgentConsole/frontend && E2E_API_URL=http://localhost npx playwright test -c tests/e2e/docker.config.ts)
(cd AgentConsole && docker compose --profile db --profile app --profile full down -v && rm -f .env)
```

```powershell
Push-Location AgentConsole; Copy-Item .env.example .env; Pop-Location   # 之後把 <YOUR_...> 佔位符換成測試值
Push-Location AgentConsole; docker compose --profile db --profile app --profile full up -d --build --wait; Pop-Location
Push-Location AgentConsole\frontend; $env:E2E_API_URL = "http://localhost"; npx playwright test -c tests/e2e/docker.config.ts; Pop-Location
Push-Location AgentConsole; docker compose --profile db --profile app --profile full down -v; Remove-Item .env; Pop-Location
```

| 項目 | 結果 |
|------|------|
| 服務與 profile | 不帶 profile 0 個服務、`--profile db` 12 個、`db`＋`app`＋`full` 16 個；補金鑰後 14 個長駐服務皆 healthy |
| 入口 | 首頁 200、`/nginx-health` 200、`/actuator/health` 403（nginx `location /actuator/ { deny all; }`）、無 token 的 `/api/v1/projects` 401、預設開發帳號登入 200 |
| **Bridge 映像缺 git（DEF-AC-003，P1）** | 任何批次一律 FAILED：`引擎異常結束 exit=1`，Bridge 容器內 traceback 止於 `boot_self_check.py:215` 的 `subprocess.run(["git", "-C", …, "diff", "HEAD", "--binary"])`：`FileNotFoundError: [Errno 2] No such file or directory: 'git'`（映像基底 `python:3.11-slim` 沒有 git；引擎內共 11 處 subprocess 呼叫 git）。這是本機（Windows 有 git）與 mock 測試都看不到、只有全棧真跑才現形的缺陷 |
| 驗證用暫行手段 | `docker exec -u root aisdlc-engine-bridge apt-get install -y git`（容器內臨時安裝，非 repo 修改，`down -v` 後消失）；之後的全棧情境都在此條件下進行 |
| 路徑 A 全鏈（UI，經 nginx） | 凍結規格→規格驅動解析→signoff→confirm→執行 Level 4→進度逐步前進→COMPLETED，21 秒（`p8-docker-stack.stack.ts`） |
| SSE 經 nginx | 暫停中的批次：連線後 22 毫秒內重播的 21 個框架全部到齊，連線仍開著（沒有被緩衝到結束才吐出）；`nginx -T` 確認 `/api/v1/stream/` 區塊 `proxy_buffering off`、`proxy_read_timeout 3600s` |
| 重啟 backend（矩陣 I） | 容器重啟約 15～40 秒；前端串流斷線後重連，但 `POST /auth/refresh` 在 backend 尚未就緒時回 502，前端把它當成登入失效而清除 session、導向 `/login`——**DEF-AC-007（P2）**，詳見 §11 |
| 上傳大小經 nginx | 剛好 10MB→201；10MB＋1 位元組（封裝後仍小於 nginx 的 11MB）→後端 413「檔案超過 10MB 上限」；12MB→nginx 自己的 413 HTML |
| nginx access log | SSE 請求只留 `?***`，整份日誌 0 個 token 值（`p8` 該 test 通過） |
| nginx error log | 上游被切斷時印出完整請求行，含 `?access_token=<JWT>`：81 行 `[error]` 中 16 行含 token 值——**DEF-AC-008（P3）**（契約 §0.7 第 4 點的殘留風險成真） |
| 既有真後端 specs（乾淨庫） | `chart`、`crud-flow`、`design-system`、`shells-and-layout`、`signoff` 共 16 支，經 nginx 同源全數通過；同樣的 specs 在本機 2,000 多個專案的資料庫下會被限流擋下（DEF-AC-009）；`signoff` 在這次執行時還是加 `waitForQuota` 之前的版本，其後只加了額度守衛（§4.7），情境本身沒變 |

`p8-docker-stack.stack.ts` 對 DEF-AC-007／008 以 `test.fail(DEFECTS_OPEN, …)` 釘住：缺陷還在時整支「預期失敗」＝綠燈，修好後會「意外通過」而變紅，提醒移除該行；設 `E2E_DEFECTS_FIXED=1` 可看真實失敗訊息。

### 7.3 nginx 與限流（經 nginx）

| 項目 | 結果 |
|------|------|
| 靜態資源快取 | `/_next/static/…` 回 `Cache-Control: public, max-age=31536000, immutable`，**同一標頭出現兩次**（nginx 與 Next 各加一次，P4 觀察） |
| `client_max_body_size` | 匯入上傳 11m、設定檔匯入 2m（`nginx -T`）；`proxy_read_timeout` 匯入 180s、串流 3600s |
| `/api/health` | `location /api/` 把它反代到後端，經 nginx 打 `/api/health` 得 401（前端容器自己的 healthcheck 走 `127.0.0.1:3000`，不受影響；對外存活探測要用 `/nginx-health`）——P4 觀察 |
| 未認證限流（依來源位址） | 連打 101 次：401 共 100 次、第 101 次 429，`Retry-After: 60`、`X-RateLimit-Limit: 100`；緊接再打仍 429 |
| 認證限流（依 JWT subject） | viewer 連打 101 次：200 共 100 次、第 101 次 429；同時 operator 照常 200（桶以使用者隔離） |
| **偽造 `X-Forwarded-For`** | 同一視窗內改 `X-Forwarded-For: 203.0.113.77`、`203.0.113.78` 即各換一個新桶（回 401 不是 429）＝未認證限流可被繞過。成因：主機請求在 Docker 下來自閘道私網位址，Tomcat `RemoteIpValve` 預設信任私網代理；公網客戶端經 nginx 時 nginx 以 `$proxy_add_x_forwarded_for` 附加、不會被偽造值取代，內網客戶端則可偽造。列 P3 觀察（§11），建議縮小 `internalProxies` 只信 nginx 容器 |
| CORS 預檢 | `OPTIONS` 帶 `Origin: http://localhost`→200；`Origin: http://evil.example`→403 |
| 資源限額 | `docker stats` 的 MEM LIMIT 與 compose 一致（backend 1GiB、Bridge 1GiB、frontend 512MiB、nginx 256MiB、primary 2GiB、replica 1GiB…）；backend 實用 928MiB／1GiB、pgAdmin 242MiB／256MiB 偏緊（P4 觀察） |
| 日誌 | backend 容器日誌為 JSON 且含 `traceId`；Bridge 日誌沒有 `traceId`（NFR-9.4-04 維持 🟡） |
| 機密掃描 | `python tools/lib/secret_scan.py --paths AgentConsole/.env.example` rc=0 |

### 7.4 Linux 容器內的 BR-19（SIGTERM 逾時升 SIGKILL）

Windows 沒有 SIGTERM 語意（終止即 `TerminateProcess`），所以改在 Linux 容器內實測：對 Bridge 容器內起一個 run，其 mock claude 設 `MOCK_CLAUDE_IGNORE_TERM=1`（忽略 SIGTERM），再 `stop`。

```
stop -> 202 {'status': 'CANCELLING'}
終態 CANCELLED，從 stop 起 30.3 秒；reason=使用者取消
mock claude 行程（終態後）: []
```

預設寬限 30 秒（`BRIDGE_STOP_GRACE_SECONDS` 未設）後 SIGKILL，終態後沒有殘留行程。Bridge 映像不含 `tests/` 目錄，無法在容器內跑 Bridge 的 pytest（列〈未覆蓋〉）。

### 7.5 備份、還原與 RPO／RTO 計時演練（NFR-9.3-03、INF-DR-16／18）

**備份**（Docker 全棧）：`pgbackrest check` 兩個 repo 的 WAL 皆 `successfully archived`；`backup-full.sh` 各 repo 一份全備成功（資料庫 32.3MB、離站 repo2 的備份集 3.5MB）；`pgbackrest info`：`cipher: aes-256-cbc`、`status: ok`。

**計時演練**（QA 腳本 `d_rto`；Docker 全棧經 nginx，資料庫 31.2MB、30 個演練專案）：

| 步驟 | 結果 |
|------|------|
| 全備 | `backup-full.sh` rc=0，5.3 秒 |
| RPO（a）：串流複製 | 經 nginx 寫入標記專案後，replica 於 0.4 秒內重播到該筆交易的 LSN |
| RPO（b）：WAL 歸檔 | 該筆交易所在 WAL 段於寫入後 61.7 秒歸檔到 repo1（`archive_timeout=60`；含 2 秒輪詢誤差） |
| 宣告災難 | `docker compose stop postgres-primary`（0.3 秒）→ 清空 primary 資料目錄內容（模擬資料遺失，保留 `pgdata` 目錄本身） |
| 還原 | `docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes`（還原到最新）rc=0，1.8 秒 |
| 啟動 | `docker compose start postgres-primary`；primary healthy 等待 6.2 秒 |
| 服務恢復 | 經 nginx 以 viewer 登入並讀專案列表成功；**RTO＝宣告災難到 API 讀回還原後資料共 9 秒**（目標 15 分鐘） |
| 資料核對 | 還原後專案總數 31＝演練前 30＋標記 1；標記專案在庫內；primary 時間軸 2；`pgbackrest check` 成功 |

**判定**：RTO 與 RPO 都落在設計目標內（NFR-9.3-03、INF-DR-18 升 `✅ 已驗證`）。侷限：資料量只有 31.2MB，不代表正式資料量下的還原時間；RPO 的歸檔路徑受 `archive_timeout=60` 支配，實測 61.7 秒含量測誤差。

**DEF-AC-010（P3）**：同一場演練的第一輪，QA 把整個 `pgdata` 目錄刪掉（模擬「換新磁碟／新卷」），`restore.sh` 於 Step 1 失敗：

```
[Step 1/2] Cleaning data directory...
find: ‘/var/lib/postgresql/data/pgdata’: No such file or directory
```

rc=1（`set -euo pipefail` 下 `find "$PGDATA_DIR" -mindepth 1 -delete` 對不存在的目錄失敗）。更危險的是之後照 README 〈4.3〉第三步 `docker compose start postgres-primary`：PG 映像的入口程序發現資料目錄為空，會 `initdb` 出一個**全新的空叢集**，約 10 秒後顯示 healthy——只看 healthy 的人會以為還原成功。建議 `restore.sh` 在 Step 1 之前 `mkdir -p` 並設好擁有者與 0700，README 〈4.3〉補「全新空卷」註記，並把「還原後核對資料列數」列為必做步驟。第二輪改為只清目錄內容後，上表全數通過。

## 8. 矩陣 E：NFR-9.1-01～06 量測

環境：Windows 11、本機 production 建置（`next build` 後 standalone）、backend e2e profile、PostgreSQL 18.4（Docker 本機）、真 Bridge；資料庫內有 2,050 個以上的專案（QA 為量測列表效能而灌入，名稱 `QA-seed-…`）。量測值是本機單機的值，不代表正式環境。

| NFR | 方法 | 實測 | 目標 | 判定 |
|-----|------|------|------|------|
| 9.1-01 首頁 LCP | Playwright（Chromium）以 `PerformanceObserver` 取 `largest-contentful-paint`，每頁載入 3 次取中位數 | 總覽 180ms、專案列表 200ms、專案詳情 228ms、執行頁 228ms、監控頁 284ms、設定頁 208ms、匯入頁 192ms（p95 皆 ≤ 300ms） | < 2 秒 | 通過 |
| 9.1-02 API p95 | PowerShell `Measure-Command` 迴圈，循序 50 次 | `GET /projects?size=10`（viewer）p50 4.7ms／p95 5.3ms／max 5.6ms；`GET /settings`（admin，22.5KB）p50 2.0ms／p95 2.8ms／max 13.1ms；`GET /executions/{runId}`（含 Bridge 往返）p50 7.4ms／p95 10.0ms／max 16.1ms | < 200ms | 通過 |
| 9.1-03 SSE 延遲 | Node `fetch` 串流同時讀 `/logs` 與 `/metrics`，延遲＝收到時間減事件的 `ts`（同一主機，無時鐘偏差）；只算連線後才產生的即時框架 | n=68：p50 15ms／p95 30ms／max 32ms（`/logs` n=38：p50 15ms／p95 30ms；`/metrics` n=30：p50 17ms／p95 30ms） | < 500ms | 通過 |
| 9.1-04 列表查詢 | 同 9.1-02，資料庫 2,050 個專案 | `GET /projects?size=100&sort=updatedAt`（30.4KB）p50 5.4ms／p95 7.3ms／max 22.0ms；`GET /projects?q=QA&size=50` p95 6.3ms；`GET /import?size=50` p95 1.9ms | < 500ms | 通過 |
| 9.1-05 Markdown 渲染 | 真瀏覽器在編輯器輸入後量測預覽更新時間，每種大小 7 次取中位數 | 1KB 12ms（max 34ms）、5KB 29ms（max 39ms）、**20KB 112ms**（max 123ms） | < 100ms | **部分**：說明文字常見大小（至 5KB）達標；20KB 略超 12% |
| 9.1-06 並發 | PowerShell 同時啟動 N 個使用者，各自「登入＋列表」 | 10 個：全成功，登入 p95 60.8ms、總耗時 p50 66.4ms／p95 86.4ms；50 個：全成功，登入 p95 79.9ms、總耗時 p50 70.7ms／p95 91.3ms／max 116ms | ≥ 50 | 通過 |

**頁面載入請求數與閒置輪詢**（同一批 Playwright，影響限流額度——每使用者每 60 秒 100 次，UI 與 REST 共用）：

| 頁面 | 載入時請求數 | 閒置 35 秒內再發 |
|------|-------------|-----------------|
| 總覽 `/` | **31**（29 次 `task-trend`＋1 次 `projects`＋1 次 `notifications/summary`） | 2 |
| 專案列表 | 3 | 2 |
| 專案詳情 | 3 | 2 |
| 執行頁 | 16 | 3 |
| 監控頁 | 12 | 16 |
| 設定頁 | 4 | 2 |
| 匯入頁 | 3 | 2 |

總覽頁每次載入對最近專案各打一次 `task-trend`（最多 30 個專案）＝單次載入就吃掉 31% 的限流額度（**DEF-AC-009**，F2-3 已知的近似做法）；監控頁閒置時每 35 秒再發 16 次請求，開著監控頁 1 分鐘約 27 次。這兩點在資料庫專案數 ≥ 30 時會讓同一使用者的其他操作更早撞上 429。

上表的閒置欄只觀察 35 秒，涵蓋不到總覽頁 60 秒一輪的聚合輪詢，所以另做一次**總覽頁閒置 135 秒**的補量測（QA 腳本，production build、資料庫 37 個專案、Chromium 逐一記錄 `/api/v1` 回應的時間與端點）：

| 時間（秒） | 0～10 | 30～40 | 60～70 | 90～100 | 120～130 | 合計 |
|-----------|-------|--------|--------|---------|----------|------|
| 請求數 | 30 | 2 | 29 | 2 | 29 | 92 |

依端點：81 次 `task-trend`（27 個專案 × 3 輪）、各 5 次 `projects` 與 `notifications/summary`、1 次 `goals`。也就是**總覽頁什麼都不做，穩態就是每分鐘約 31 次請求**（每 60 秒一輪 27～29 次 `task-trend`，加上每 30 秒一次 `projects`＋`summary`）；資料庫專案數達 30 時是每分鐘約 33 次，佔每使用者每分鐘 100 次額度的三成以上。以單分頁的實測值推算（未實測多分頁），同一使用者開兩個總覽分頁約六成、三個約九成。

## 9. 矩陣 F：RTM 逐列核對與統計

### 9.1 做法

- 把四份開發者回填檔（`rtm_backfill_W3B1.md`、`W3B2.md`、`W4F1.md`、`W4F2.md`）合併進 `RTM.md`；**只改每列的「實作檔、自動測試、E2E 驗證、狀態」四格**，不刪列、不改號、不合併列。QA 以腳本逐列比對 HEAD 驗證：361 列、`ID／來源／摘要／層／Phase` 五格逐字不變、非表格行逐字不變、儲存格內沒有混入管線字元、每個 `✅ 已驗證` 列的 E2E 驗證欄都有內容。
- 開發者宣稱 `✅ 實作+測試` 的列：整批重跑其自動測試一次（後端 `gradlew clean build`、前端 `vitest`，結果見 §3），再依真後端／真 Bridge 的跨層證據決定升 `✅ 已驗證`、留原狀或降 `❌ 缺陷`。`INF-*` 列依 RTM §1.4，W2-B 的真機實跑可直接設 `✅ 已驗證`，本輪只對 18 列做全棧補充驗證（§12）。
- `⬜ 未開始` 的列逐條判定：只有主控裁決可引用——`API-AUT-06` 與 `US-M-10` 的「資源使用情況」→ 🟡、`US-I-05` 的「瀏覽按鈕」→ ⛔（該列其餘部分已驗證，故狀態仍 `✅ 已驗證`，裁決註記在 E2E 欄）；沒有裁決可引用而又無法驗證的列（`NFR-9.3-01`）留 `⬜` 並列入 §12。
- `UI-SCR-07`、`UI-SCR-08` 原指向已刪的 `ProjectShellPage.tsx`，合併時改為 F2 回填的實作檔與測試；`UI-SCR-06`、`UI-SCR-09` 另有已刪的 `PlaceholderCard.tsx` 過期引用，一併移除。
- QA 另做兩項存在性查核：實作檔欄的 1,324 個路徑與自動測試欄的 1,112 個測試引用，逐一對回 repo。查出並就地更正 4 個過期的後端測試名（`SchemaMigrationIT` 三個、`OpenApiIT` 一個：W3-B 改名或擴充後，W2-A 先前回填的名稱沒跟上，涉及 `INF-DB-01`～`16` 與 `NFR-9.4-03`）；其餘引用全數存在。
- 本輪**沒有新增列**，總列數維持 361。E2E 驗證欄的 `QA_P3-6_E2E_Verification.md §n` 都指向本檔對應節號。

### 9.2 現查計數（Implementation_Plan W4 閘門的兩條指令）

```bash
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$' AgentConsole/docs/06_quality/RTM.md
```

```powershell
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*✅ 已驗證 \|$').Count
```

本回合在 RTM 合併完成後實跑的輸出：`⬜ 未開始`＝**1**、`✅ 已驗證`＝**331**。W4 閘門要求 `⬜` 為 0；剩下的 1 列是 `NFR-9.3-01`（可用性 99.5% 需要長期監測，單次 QA 無法判定，也沒有主控裁決可改 `⛔`），已列入 §12。

### 9.3 狀態分佈（361 列）

| 前綴 | 列數 | ✅ 已驗證 | ✅ 實作+測試 | 🟡 部分 | ❌ 缺陷 | ⬜ 未開始 |
|------|------|------|------|------|------|------|
| `US-` | 58 | 53 | 0 | 3 | 2 | 0 |
| `API-` | 91 | 88 | 0 | 2 | 1 | 0 |
| `BR-` | 25 | 25 | 0 | 0 | 0 | 0 |
| `NFR-` | 32 | 27 | 0 | 4 | 0 | 1 |
| `INF-` | 103 | 98 | 0 | 3 | 2 | 0 |
| `UI-` | 52 | 40 | 5 | 5 | 2 | 0 |
| 合計 | 361 | 331 | 5 | 17 | 7 | 1 |

### 9.4 降為 `❌ 缺陷` 的 7 列（轉 W5）

| 列 | 摘要 | 缺陷 |
|----|------|------|
| `US-I-04` | 匯入前編輯三層結構 | DEF-AC-001（P2） |
| `UI-SCR-06` | BRD/PRD 智能匯入 | DEF-AC-001（P2） |
| `US-S-06` | 匯出／匯入系統設定 | DEF-AC-002（P3） |
| `API-SET-09` | 匯入設定 | DEF-AC-002（P3） |
| `INF-SVC-04` | engine-bridge 旁車 | DEF-AC-003（P1） |
| `INF-DKR-04` | bridge Dockerfile | DEF-AC-003（P1） |
| `UI-A11Y-03` | 對比度符合 WCAG 2.1 AA | DEF-AC-004（P3） |

### 9.5 仍為 `🟡 部分` 的 17 列

| 列 | 原因 |
|----|------|
| `US-M-07`、`API-MON-07` | PDF 報表依契約回 501（W5）；CSV 已驗 |
| `US-M-09` | 設計稿與契約都沒有獨立的追蹤鏈視圖；以批次下拉＋事件時間軸＋日誌查詢涵蓋 |
| `US-M-10` | 「資源使用情況」Bridge 無來源（主控裁決） |
| `API-AUT-06` | 等級 6～10 不送引擎設定（主控裁決、契約標 UNVERIFIED） |
| `NFR-9.1-05` | Markdown 預覽 20KB 為 112ms（目標 100ms；5KB 以內達標） |
| `NFR-9.3-04` | 軟刪除已做，30 天內復原的 restore 機制未做 |
| `NFR-9.4-01` | 前端未設 Prettier |
| `NFR-9.4-04` | Bridge 日誌沒有 `traceId` |
| `INF-VOL-06`、`INF-VOL-07`、`INF-DR-13` | W2-B 標註的缺口（卷內為空、憑證與 HTTPS 區塊未放、WAL 7 天本地複本清理未做時間驗證） |
| `UI-SCR-01` | 總覽頁請求扇出（DEF-AC-009） |
| `UI-A11Y-01` | 無障礙結構（DEF-AC-005） |
| `UI-A11Y-02` | 全站鍵盤操作未逐頁驗 |
| `UI-KPI-01`、`UI-KPI-02` | PRD 寫「環形」，設計稿與實作是數值卡（§13） |

### 9.6 仍為 `✅ 實作+測試` 的 5 列

`UI-DS-04`（僅用 Lucide 線性圖示）、`UI-DS-06`（動效規範）、`UI-DS-07`（狀態中文標籤與顏色）、`UI-OVL-02`（Toast）、`UI-OVL-03`（載入 Skeleton／spinner）：自動測試本回合重跑全綠，但沒有真瀏覽器逐項證據，所以不升 `✅ 已驗證`（E2E 欄已註明原因）。

## 10. 矩陣 I／J

### 10.1 矩陣 I：真 SSE 對前端的回歸

F2 的 SSE 前端全在 mock（`node:http` 伺服器）下驗；以下在真後端（Spring `SseEmitter`）與經 nginx 的真入口重做：

| 情境 | 本機真後端 | Docker 經 nginx（`proxy_buffering off`） |
|------|-----------|----------------------------------------|
| 斷線重連 | `p4-execute.spec.ts`：真的把 backend 行程殺掉再起（`context.setOffline` 切不斷已建立的 EventSource，實測 30 秒後仍 open）；前端顯示重連中→連回後以 `Last-Event-ID` 續接、已有事件不重複、後續事件照常到。backend 停機超過 3 秒時瀏覽器原生重連也失敗，前端依設計改以 `tail=1000` 重建連線 | `p8`：同情境；**登入被清除**（DEF-AC-007），詳見 §11 |
| 終態 204 | `E2E-12`：已終態批次帶 `Last-Event-ID` 等於最後 id→204（EventSource 不再重連）；`/metrics` 帶 `<S>.3`→204、帶 `<S>.1`→仍送終態快照後關閉 | 同上，路徑相同 |
| `/metrics` 子序號去重 | `E2E-12`：三則快照 id 為 `<S>.1`／`<S>.2`／`<S>.3`，互異且嚴格遞增；`b2_sse`：整條序列 `2.1 2.2 2.3 14 16 16.1 20 20.1 21 23 …` 嚴格遞增、無重複 | — |
| 串流不緩衝 | — | 暫停中的批次，連線後 22 毫秒內 21 個重播框架全部到齊，連線仍開著 |
| keep-alive | `E2E-12`：PAUSED 的批次閒置時，每 ≤ 2 秒（e2e 設定）收到 keep-alive 註解 | — |
| 終態順序 | `p4`（ESCALATED）：run 終態（FAILED）後待審核卡仍出現（RETRY／SKIP／REJECT 可按、通過停用）；RETRY 再失敗→出現第二個 ESCALATED 審核項；SKIP→另開後續批次並跑完。沒有「前端在 S.1 到達前關線而審核卡消失」的情形 | — |

**判定**：只在 mock 綠、真後端紅的情形，唯一一條是 DEF-AC-007（真後端／真重啟才有 refresh 502 這件事，mock 伺服器永遠不會回 502）。其餘情境真後端與 mock 一致。

### 10.2 矩陣 J：殭屍視窗（cancel 後 5 秒內狀態）

做法：對 PRJ-B（5 個任務）Level 4 啟動，約 1.2 秒後 `POST /executions/{runId}/cancel`，每 0.1～0.5 秒同時讀 Console 的 `GET /executions/{runId}` 與 Bridge 直連的 run 狀態，並檢查行程殘留；連做 5 次。

```
POST cancel -> HTTP 200 status=RUNNING bridgeStatus=CANCELLING
t+ 0.1s Console: status=RUNNING bridgeStatus=CANCELLING bridge.connected=True completedSteps=0 | Bridge直連: status=CANCELLING pid=31868
t+ 0.6s Console: status=CANCELLED bridgeStatus=CANCELLED bridge.connected=True completedSteps=0 | Bridge直連: status=CANCELLED pid=
--- cancel 之後的相關行程（預期無殘留）---（無）
專案 status=READY（預期 READY）
…（第 2～5 次同形）
==== 結論：5 次中卡住（7 秒內未進 CANCELLED）的次數 = 0 ====
```

5 次的 `CANCELLING→CANCELLED` 皆在 0.5～0.6 秒內完成、`bridge.connected` 全程 True、cancel 後沒有殘留的 `claude`／`aisdlc-mock-claude` 行程、專案回 `READY` 可再執行。沒有「行程已死但狀態卡 CANCELLING」。Linux 容器內的強殺路徑見 §7.4。

## 11. 缺陷清單

嚴重度：**P1**＝阻斷主要功能、無合理繞過；**P2**＝功能錯誤或可用性缺陷、影響一般使用者、有繞過；**P3**＝次要缺陷、防禦縱深或設定／文件缺口；**P4**＝觀察（不立缺陷，供 W5 評估）。編號與 `frontend/tests/e2e/` 內的 `test.fail` 註解一致，勿改號。

| 編號 | 嚴重度 | 摘要 | 影響的 RTM 列 | 釘住的測試 |
|------|--------|------|---------------|-----------|
| DEF-AC-001 | P2 | 匯入頁節點編輯對話框：AI 解析任務的 `maxRetries: null` 顯示成字面「null」並卡住「確定」 | US-I-04、UI-SCR-06（降為缺陷） | `p3-import.spec.ts`（`test.fail`） |
| DEF-AC-002 | P3 | 設定匯入對「值未變」的項目仍驗 SSRF／allowlist，匯出後原樣匯入出現 errors | US-S-06、API-SET-09（降為缺陷） | `p6-settings.spec.ts`（`test.fail`） |
| DEF-AC-003 | **P1** | Bridge 映像沒有 git，Docker 全棧下任何批次一律 FAILED | INF-SVC-04、INF-DKR-04（降為缺陷）；全棧下的 US-E／API-EXE | `p8`（以暫裝 git 繞過後才能跑） |
| DEF-AC-004 | P3 | 色彩對比不足（WCAG AA）：257 個節點 | UI-A11Y-03（降為缺陷） | axe 掃描（QA 腳本） |
| DEF-AC-005 | P3 | 無障礙結構：名稱與可見文字不符 31、svg 缺替代文字 18、list／listitem 結構錯誤 | UI-A11Y-01（維持部分） | axe 掃描 |
| DEF-AC-006 | P3 | `docker-compose.yml` 的 `CONSOLE_ENCRYPTION_KEY` 預設空，compose 層不擋 | INF-SVC-03、INF-HLT-01（附註） | 矩陣 H（§7.1） |
| DEF-AC-007 | P2 | backend 暫時不可用（nginx 502）時，前端把 refresh 失敗當登入失效而登出 | API-SSE-03、NFR-9.2-01（附註） | `p8`（`test.fail`） |
| DEF-AC-008 | P3 | nginx `error_log` 在上游被切斷時印出含 `?access_token=<JWT>` 的完整請求行 | INF-NGX-04（附註） | `p8`（`test.fail`） |
| DEF-AC-009 | P2 | 總覽頁每次載入打 30 次上下請求（27～29 次 `task-trend`），閒置時每 60 秒再打一輪：單一分頁穩態每分鐘約 31 次，佔每使用者 100 次額度的三成；專案數 ≥ 30 後，快速導覽即出現「無法載入儀表板資料：請求過於頻繁」 | UI-SCR-01（維持部分） | 無（以 `waitForQuota` 規避；證據見下） |
| DEF-AC-010 | P3 | `restore.sh` 在資料目錄不存在（全新空卷）時失敗，其後 start 會 initdb 出空叢集並顯示 healthy | INF-DR-16（附註）、NFR-9.3-03（附註） | 矩陣 D（§7.5） |

### DEF-AC-001（P2）匯入頁節點編輯對話框無法確定

- **症狀**：真後端對 AI 解析出的任務，`maxRetries` 回 `null`（契約 §0.2：client 視 `null` 與缺席等價）。開「編輯任務」對話框時「最大重試次數」欄顯示成字面「null」，zod 驗證（0～20 的整數）擋住「確定」，使用者必須手動清空該欄才能儲存；樹狀預覽同型，會顯示「最大重試次數：null」。
- **根因（待驗假設，已讀碼對照）**：`frontend/components/domain/import/NodeEditDialog.tsx` 第 278 行 `existing?.maxRetries === undefined ? "" : String(existing.maxRetries)`，`null` 不等於 `undefined` 而被 `String(null)` 轉成「null」（同檔 `evaluatorCommand`、`expectedOutputRegex` 已用 `?? ""`，沒有此問題）；`components/domain/import/tree.ts` 第 127 行（`!== undefined`）與 `TreeEditor.tsx` 第 132 行同型。前端 mock 夾具沒有 `null` 欄位，所以 vitest 與 mock specs 都沒測到。
- **重現**：`p3-import.spec.ts` 的對應 test（`E2E_DEFECTS_FIXED=1` 看真實訊息：`Expected "" Received "null"`）；手動：貼一段文字走路徑 B 解析，結構預覽按任一任務「編輯」。
- **建議修法**：三處判空改 `== null`（或在 API 邊界把 `null` 正規化成預設值）；補一支餵 `maxRetries: null` 的元件測試。

### DEF-AC-002（P3）設定匯入對值未變的項目仍驗 allowlist

- **症狀**：`POST /settings/export` 之後把檔案原樣 `POST /settings/import`，得 `{"applied":0,"skipped":49,"errors":[model.apiUrl …]}`。契約 §1.5.10 要求「值相同者計 skipped」，不應有 errors；UI 因此顯示匯入失敗。
- **重現**：e2e profile（`console.security.outbound-allowlist` 不含預設的 `model.apiUrl` 主機）；`p6-settings.spec.ts` 的對應 test，或 curl 兩步。
- **影響**：只要管理員的 allowlist 不含預設 URL，「匯出→匯入」的回環操作就失敗。
- **建議修法**：匯入時先比對值，相同者直接計 skipped、不做 SSRF 驗證。

### DEF-AC-003（P1）Bridge 映像缺 git

- **症狀／證據**：見 §7.2。Docker 全棧下 execute 後 run FAILED（`引擎異常結束 exit=1`），Bridge 容器內 traceback：`FileNotFoundError: [Errno 2] No such file or directory: 'git'`（`autoclaude/execution/boot_self_check.py` 第 215 行的 `git -C … diff HEAD --binary`；引擎內共 11 處 subprocess 呼叫 git）。
- **為何先前沒被發現**：本機（Windows 有 git）、mock claude、Bridge 的 pytest 都不經過這條路；compose 的 healthcheck 只打 `/health`（不跑引擎開機自檢），容器永遠 healthy。
- **影響**：全棧下沒有任何批次能跑完（US-E 全部、API-EXE 全部在 Docker 下不可用）。
- **驗證用暫行手段**：容器內臨時 `apt-get install -y git`（非 repo 修改）；之後 `p8` 路徑 A 全鏈 21 秒 COMPLETED。
- **建議修法**：`engine-bridge/Dockerfile` 的 apt 步驟加裝 `git`，build 後加 `git --version` 冒煙；Bridge 的 `/health` 另提供深度探針（跑一次引擎開機自檢）供 compose healthcheck 使用。

### DEF-AC-004（P3）色彩對比不足

- **症狀**：axe-core 4.14.0（WCAG 2.0／2.1 A／AA 規則）掃 11 頁，`color-contrast` 共 257 個節點違規：主色 `#498428` 底上的 `#edf3e9`（12px 文字）4.03:1、`#e4eddf`（11px）3.79:1；`wg-muted` `#7a8775` 在白底 12～14px 文字 3.78:1；標準 4.5:1。
- **重現**：QA 的 axe 掃描腳本（暫存）；任一頁的頂列副標、登入頁的「AGENT CONTROL PANEL」、狀態晶片。
- **建議修法**：主色底上的小字改純白（`#ffffff` 在 `#498428` 為 4.55:1）；`wg-muted` 加深到 `#6b7766` 以下（在白底 4.71:1）。這是設計 token 層級的改動，要與設計稿確認。

### DEF-AC-005（P3）無障礙結構

- `label-content-name-mismatch` 31 個節點：頂列 logo `a[aria-label="AISDLC Console 首頁"]` 的 aria-label 不含可見文字（WCAG 2.5.3）。
- `svg-img-alt` 18 個節點：Markdown 編輯器工具列的 `<svg role="img">` 沒有替代文字（按鈕本身有 aria-label，svg 應 `aria-hidden`）。
- `list`／`listitem`：監控頁 Agent 狀態晶片的 `<ol>` 直接含 `<div>`、`<li>` 不在 `<ul>`／`<ol>` 內。
- **建議修法**：aria-label 納入可見文字或移除；工具列 svg 加 `aria-hidden="true"`；晶片容器改 `<ul>` 或把 `<li>` 換成 `<div>`。

### DEF-AC-006（P3）`CONSOLE_ENCRYPTION_KEY` 預設空

見 §7.1。**建議**：`docker-compose.yml` 改 `${CONSOLE_ENCRYPTION_KEY:?請設定}`。

### DEF-AC-007（P2）暫時性 502 被當成登入失效

- **症狀**：Docker 全棧下，開著執行頁（SSE 串流 open）時重啟 backend 容器，約 10 秒後前端被導到 `/login`、session 被清除，backend 恢復後仍停在 `/login`。
- **時序（逐字節錄，QA 的瀏覽器請求追蹤）**：

```
   2.8s --- 已暫停、串流 open：重啟 backend ---
   4.3s GET /api/v1/executions/<id> → 502   （nginx 在上游不可用時立即回 502）
   4.3s FAILED GET /api/v1/stream/executions/<id>/logs (net::ERR_INCOMPLETE_CHUNKED_ENCODING)
   6.8s GET /api/v1/stream/executions/<id>/logs → 502
   9.9s POST /api/v1/auth/refresh → 502
   9.9s NAVIGATED /login
  14.5s backend healthy；再觀察 25 秒
  39.5s 最後停在 /login；session=false
```

- **根因（待驗假設，已讀碼對照）**：`frontend/lib/api/client.ts` 的 `doRefresh()` 以 `try/catch` 把任何失敗（含 502、網路錯誤）都當成回 `false`；`renewSession()`（第 257～261 行）據此呼叫 `handleUnauthorized()` 清 session 並導向登入。SSE 重連走的 `getFreshAccessToken({ force: true })` 會進這條路；一般 REST 的 `sendWithRenewal()`（401 後換新）同樣沒有區分「refresh token 無效（401／400）」與「伺服器暫時不可用（5xx、網路錯誤）」。
- **為何只在 Docker**：本機直連時 backend 重啟約 10 秒，EventSource 的重連先成功，沒踩到 refresh；經 nginx 時上游不可用會**立即**回 502，重連路徑因而觸發 refresh。mock 伺服器永遠不會回 502，所以 F2 的 mock 驗證看不到。
- **建議修法**：refresh 只在 401／400 時登出；5xx 與網路錯誤保留 session、退避重試（例如 1→2→4 秒，上限 30 秒）；SSE 重連遇到 502 或網路錯誤時不要強制 refresh。
- **測試**：`p8-docker-stack.stack.ts` 的「重啟 backend → 前端串流重連、session 不得被清除、不重複」以 `test.fail` 釘住。

### DEF-AC-008（P3）nginx error_log 洩漏 access_token

- **症狀**：EventSource 無法帶標頭，token 放在查詢字串。nginx 的 `access_log` 已遮罩（`?***`，QA 驗證 0 個 token 值），但 `error_log` 在上游被切斷時印出完整請求行：重啟 backend 的演練中，81 行 `[error]` 有 16 行含 `?access_token=<JWT>`。
- **證據樣本（token 已遮蔽）**：`upstream prematurely closed connection while reading upstream, client: …, request: "GET /api/v1/stream/executions/<id>/metrics?access_token=<已遮蔽> HTTP/1.1"`。
- **建議修法**：（a）把 nginx `error_log` 降到 `crit` 以上；（b）前端改用 fetch 串流並帶 `Authorization` 標頭（契約 §2.8 已把它列為優先做法）；（c）縮短 SSE 專用 token 的壽命。
- **測試**：`p8` 的「nginx error log」以 `test.fail` 釘住。

### DEF-AC-009（P2）總覽頁請求扇出

- **嚴重度的調整**：初判 P3（既有 specs 在 2,050 個專案的資料庫下被 429 擋下）。最終整套 Playwright 第 2 次在乾淨資料庫（跑到後段已累積 ≥ 30 個專案）上，`signoff.spec.ts` 的總覽頁出現使用者可見的紅色錯誤區塊，連一般導覽都會撞上，故改判 **P2**（可用性缺陷、影響一般使用者、有繞過：等視窗回滿或按「重試」）。
- **症狀**：總覽頁每次載入打 30 次上下的請求（27～29 次 `GET /monitor/projects/{id}/task-trend`＋`projects`＋`notifications/summary`＋1 次 `goals`），之後每 60 秒再打一輪、每 30 秒另打 `projects` 與 `summary`（`useWeekCompletedTasks`，`frontend/lib/api/queries.ts`：`WEEK_COMPLETED_MAX_PROJECTS=30`、`DASHBOARD_AGG_POLL_MS=60_000`）。實測（§8：QA 腳本，閒置 135 秒、資料庫 37 個專案）：共 92 次，依時間為 30／2／29／2／29（0、30、60、90、120 秒附近），即**單一總覽分頁穩態每分鐘約 31 次**；限流是每使用者每分鐘 100 次、UI 與 REST 共用，所以總覽頁開著就持續佔掉三成以上額度。
- **使用者可見的失敗（本回合親見）**：整套第 2 次最終跑，`shells-and-layout` 六支（合計約 4.3 秒）之後緊接著 `signoff` 載入總覽頁，主內容區換成紅色錯誤區塊，文字逐字是「無法載入儀表板資料」「請求過於頻繁：每分鐘最多 100 次，請 56 秒後再試：超過每分鐘 100 次請求上限」並附 traceId 與「重試」按鈕，左側「我的專案」顯示「尚無專案」。視窗剩 56 秒，與「前面那六支合計約 4 秒就把額度用光」吻合（推論，沒有逐請求計數）；隨後第二個情境的 beforeAll 在 `POST /projects` 同樣得到 HTTP 429（請 40 秒後再試）。另外，本機資料庫有 2,050 個專案時，`crud-flow`、`design-system`（扁平）、`signoff` 三個既有 specs 也被 429 擋下（畫面逐字：「無法載入目標：請求過於頻繁：每分鐘最多 100 次…」）；Docker 乾淨資料庫（< 30 個專案）全過。
- **為何仍是「專案數 ≥ 30」才現形**：fan-out 的上限是 30 個專案，專案少時請求數就少；正式使用一個月後專案數很容易超過 30。
- **背景**：這是 F2-3 已知、主控裁決的近似做法（契約 §4.6 G-G3：沒有全域端點）。本缺陷登記的是它與限流額度的交互，不是推翻該裁決。
- **我方的處理**：`signoff.spec.ts` 加 `waitForQuota`（`helpers.ts`）在每個情境前確認餘額；該 spec 在針對性複驗與第 3 次整套中都通過，兩次守衛都實際等過一個視窗（§4.7）。這只是測試端的規避，缺陷本身沒修。
- **建議修法**：W5 做全域聚合端點（一次回全部專案的本週完成數）；在那之前可調高讀取類端點的限流額度，或把總覽頁的聚合輪詢降頻（例如改 5 分鐘、分頁隱藏時暫停）。

### DEF-AC-010（P3）`restore.sh` 對不存在的資料目錄失敗

見 §7.5。**建議**：`restore.sh` Step 1 之前 `mkdir -p "$PGDATA_DIR"` 並設擁有者與 0700；README 〈4.3〉補「全新空卷」註記；還原後核對資料列數列為必做步驟。

### 觀察（P4，不立缺陷）

| 編號 | 觀察 | 出處 |
|------|------|------|
| O-01 | `X-RateLimit-*` 標頭沒有列入 `Access-Control-Expose-Headers`，瀏覽器內讀不到剩餘額度（契約只要求 `Retry-After`、`X-Follow-Up-Run-Id`、`Content-Disposition`，皆已暴露） | §5.4 |
| O-02 | Token 趨勢圖在單一時間桶（短批次）時只剩點、沒有線 | `p5` |
| O-03 | 契約 E2E-01 步驟 12 對**清單**端點寫 `signedOffBy` 過寬（只有詳情帶） | `p3` |
| O-04 | 手動重試不受 `maxRetries` 限制：ESCALATED 任務按「重試」後 toast 顯示「重試 3 / 1」 | §15.4 |
| O-05 | `EXECUTING` 中仍可刪除「尚未開始」的目標（204），批次照樣跑完 | §15.4 |
| O-06 | Docker 全棧預設帶開發帳號與文件載明的預設密碼；正式部署必須更換，部署指引要寫明 | §7.2 |
| O-07 | 任務詳情的執行日誌行會帶出主機路徑（例：`path=C:\Users\…`），viewer 角色看得到 | §15.4 |
| O-08 | `/api/health`（前端健康路由）經 nginx 被 `/api/` 反代到後端而回 401 | §7.3 |
| O-09 | 靜態資源 `Cache-Control` 標頭重複兩次 | §7.3 |
| O-10 | W3B1、W4F1 兩份任務書只有 PowerShell 形態的指令（違反雙形態要求） | §15.3 |
| O-11 | Bridge 日誌沒有 `traceId`（NFR-9.4-04 維持部分） | §7.3 |
| O-12 | PAUSED 批次 `restore` 後，舊審核項以 `decided_by=system`、`comment=執行已還原` 關閉，只有查資料庫看得到 | §4.2 |
| O-13 | `ENGINE_ESCALATION` 告警訊息本身就是失敗原因（含 `[G1-T1]` 這種每批次重新編號的 stepId），沒有任務名 | §4.2 |
| O-14 | `ENGINE_ESCALATION` 的去重鍵是 `step:<stepId>`，而 stepId 每批次重新編號：不同批次、不同任務的升級會被先前未確認的那則吞掉（逐批失敗的情境，第 2、3 批沒有新告警列，SSE 仍轉發）。契約 §3.7 如此規定，但後果是漏看 | §15.4 |
| O-15 | `CONSECUTIVE_FAILURES` 在 UI 操作路徑下幾乎不可達：引擎遇到第一個升級就結束批次；SKIP 讓任務變 SKIPPED 而自序列消失；REJECT 後重跑 `ALL` 又卡在同一個任務；只有 `scope.mode=SELECTED` ＋ `taskIds` 逐批各選一個任務才會累計 | §4.3、§15.4 |
| O-16 | `GET /actuator/prometheus` 不需 token（`ActuatorIT` 明載）：直連後端埠時任何人可讀，防護全靠網路隔離（Docker 由 nginx `deny all`、後端埠不發布） | §15.4 |
| O-17 | Markdown 預覽端同時裝了套件預設的 `rehype-prism-plus` 與專案加的 `rehype-highlight`，實際著色由 prism token 負責（`hljs` 只留 class）；兩套並存多一份轉換成本 | §4.7 |
| O-18 | 契約 §6.2 #20：Docker 全棧沒有 e2e profile，路徑 B／C 在該環境沒有模型可用；以路徑 A 與 Phase 2 REST 夾具替代 | §7.2 |
| O-19 | 主機資源：backend 實用 928MiB／1GiB、pgAdmin 242MiB／256MiB 貼近限額 | §7.3 |
| O-20 | 未認證限流可被 `X-Forwarded-For` 繞過（內網客戶端；見 §7.3），建議縮小 Tomcat `RemoteIpValve` 的 `internalProxies` | §7.3 |
| O-21 | `aisdlc-mock-claude` 只有 `MOCK_CLAUDE_DELAY`／`FAIL_REGEX`／`TRACE`／`IGNORE_TERM` 四個旋鈕：沒有「首次失敗、重試成功」與「慢步驟」，時間型與重試率告警只能靠繞法驗證（§15.4） | §14 |

## 12. 未覆蓋（誠實清單）

| 項目 | 原因 | 影響的 RTM 列／備註 |
|------|------|--------------------|
| NFR-9.3-01 可用性 99.5% | 需要長期監測，單次 QA 無法驗證；沒有主控裁決可改 `⛔` | 維持 `⬜ 未開始`（RTM 中唯一的 `⬜`） |
| 真 MiniMax Brain（路徑 C 的真模型拆解） | 環境沒有金鑰與外網模型；以「假 Brain 伺服器＋真 Bridge」代替（`support/fake_brain_bridge.py`、`E2E_FAKE_BRAIN=1`）；一般 Bridge 無金鑰一律 fail-closed 422 `brain_unsupported`（已驗） | API-IMP-03、BR-11 的「真模型」部分 |
| 真實 `claude` CLI | 全程使用 `aisdlc-mock-claude`；真 CLI 的 token usage、context% 等欄位未驗 | US-E 全系列的「真 Agent」語意 |
| 正式資料量的還原時間 | 計時演練只有 31.2MB（RTO 9 秒）；正式資料量下的還原時間未量 | NFR-9.3-03、INF-DR-18 |
| `verify-backup.sh`（週期性還原演練） | 本輪未重跑，沿用 W2-B；本輪另做了 `restore.sh` 的計時演練（§7.5） | INF-DR-12 沿用 W2-B |
| W2-B 已設 `✅ 已驗證` 的 INF 列 | RTM §1.4 規定 `INF-*` 列的真機實跑可由 W2-B 直接設定；QA 只對 18 列做了全棧補充驗證（含兩列降為缺陷），其餘 INF 列沿用 W2-B 的實跑證據、QA 未逐列重跑 | INF-* |
| Bridge 的 4 支 pytest（Windows 略過） | Windows 無 symlink 權限：`test_security.py:132`、`test_api_validation.py:75`、`test_sdd.py:137`、`test_e2e_edge_cases.py:151`；Bridge 映像不含 `tests/`，無法在 Linux 容器內補跑。建議在 Linux CI 確認這 4 支確實執行 | BR-02、BR-13 的 symlink 防護 |
| 「單純長步驟、探測正常」不告警的負向情境 | `aisdlc-mock-claude` 沒有慢步驟旋鈕；只有單元測試（`AlertRulesTest`）覆蓋 | API-ALR-04 |
| PDF 報表 | 契約裁決回 501「尚未提供」（W5）；CSV 已驗 | US-M-07、API-MON-07（維持 🟡） |
| 觸控拖曳 | 只驗指標與鍵盤，未在觸控裝置驗證 | US-M-08、US-G-06 |
| Docker 下 `RemoteIpValve` 對公網客戶端 | 主機端的請求都來自 Docker 閘道私網位址；公網客戶端行為只能由 nginx 設定與 Tomcat 預設值推論 | O-20 |
| DNS rebinding 對真外網 | 只有測試用的解析覆寫（`rebind.e2e.test`→私網位址） | NFR-SEC-04 |
| Firefox／WebKit、非 Windows 主機 | Playwright 只跑 Chromium；本機是 Windows 11（Linux 只有容器內的 Bridge 與全棧服務） | NFR-XPL-0x |
| 超過 50 的並發、長時間浸泡 | 並發只量到 10 與 50 | NFR-9.1-06 |
| 兩項主控裁決 | `API-AUT-06`（等級 6～10 不送引擎設定）、`US-M-10` 的「資源使用情況」（Bridge 無來源）依裁決維持 🟡；`US-I-05` 的「瀏覽按鈕」依裁決範圍外 | 見 §9 |

## 13. 與設計稿／PRD 的差異

| 項目 | 設計稿／PRD | 實作／量測 | 處置 |
|------|-------------|-----------|------|
| KPI「專案完成率」「目標達成率」 | PRD 寫「環形」 | 設計稿畫面 8 只有數值卡與 delta，實作依設計稿畫的是數值卡 | UI-KPI-01／02 維持 🟡；由主控裁決以哪份為準 |
| Markdown 渲染時間 | PRD §9.1：小於 100ms | 20KB 112ms（≤5KB 達標） | NFR-9.1-05 維持 🟡 |
| Markdown 程式碼區塊高亮 | 單元測試與註解描述為 rehype-highlight（`hljs-*` class） | 真瀏覽器 DOM 是 `code.hljs.language-ts.code-highlight` 加 prism 的 `token` span：套件預設的 `rehype-prism-plus` 與專案加的 `rehype-highlight` 並存，實際著色由 prism 負責（O-17） | 功能正確，只是文件與實作描述不一致；W5 擇一保留 |
| PDF 報表 | PRD §5.4：匯出 PDF／CSV | PDF 依契約回 501 | W5 |
| 圖表時區 | — | F2-1：DAY 桶標籤用瀏覽器本機時區，桶起點仍為 UTC；跨日邊界附近標籤與伺服器的日界不同 | 已知漂移（不登缺陷），W5 擇一 |
| 色彩 token | 設計稿 `water_green` 配色 | 主色底上的小字與 `wg-muted` 不達 WCAG AA（DEF-AC-004） | 需設計確認 token |
| Token 趨勢圖 | 折線 | 單一時間桶（短批次）只剩點（O-02） | 觀察 |
| 總覽「本週完成」 | 全域聚合 | F2-3：前 30 個專案的近似聚合（DEF-AC-009 的來源，P2） | W5 做全域端點 |
| 頂列 Bridge 連線燈 | 設計稿有 | 以 `notifications/summary` 的 `bridgeConnected` 實作（D-44），30 秒探測環；實測 Bridge 關掉→false、恢復→true | 符合 |
| 契約 E2E-01 步驟 12 | 清單端點含 `signedOffBy` | 只有詳情端點帶（O-03） | 契約措辭差異 |

## 14. 給 W5 的修復建議（依優先序）

1. **DEF-AC-003（P1）**：`engine-bridge/Dockerfile` 加裝 `git`；Bridge `/health` 提供深度探針（跑一次引擎開機自檢）供 compose healthcheck 使用。並建議把「`compose up` 後跑一個批次」的全棧冒煙納入 CI（`docker.config.ts` 的 `p8` 已可直接用）——這條缺陷在本機、mock、Bridge pytest 全綠的情況下只有全棧真跑才現形。
2. **DEF-AC-007（P2）**：前端 refresh 只在 401／400 才登出，5xx 與網路錯誤保留 session 並退避重試；SSE 重連不強制 refresh。修好後移除 `p8` 對應 test 的 `test.fail`。
3. **DEF-AC-001（P2）**：`NodeEditDialog.tsx`／`tree.ts`／`TreeEditor.tsx` 判空改 `== null`；補一支餵 `null` 欄位的元件測試。修好後移除 `p3` 的 `test.fail`。
4. **DEF-AC-009（P2）**：全域聚合端點取代 27～29 次 `task-trend` 扇出；在那之前把總覽頁聚合輪詢降頻（例如 5 分鐘、分頁隱藏時暫停）或調高讀取類端點的限流額度。這是 W5 之後所有 E2E 的穩定性前提：專案數 ≥ 30 後，連續載入幾次總覽頁就會把 operator 的額度用光。
5. **DEF-AC-002**：設定匯入對值相同者直接計 skipped、不驗 allowlist。
6. **DEF-AC-006／010**：`compose` 的金鑰改 `:?` 必填；`restore.sh` 補 `mkdir -p`，README 〈4.3〉補空卷註記與「還原後核對資料」步驟。
7. **DEF-AC-008**：nginx `error_log` 降級或前端改 fetch 串流帶標頭。
8. **DEF-AC-004／005**：與設計確認 token 後一併修對比與結構；`aria-hidden` 之類的修法成本很低。
9. **契約 v1.2 回寫**：B1-1～B1-9、F1-1～F1-6、F2-1～F2-6 的漂移裁決（任務書〈契約漂移裁決〉）一次寫回契約；另補 O-14（ENGINE_ESCALATION 的去重鍵）與 O-15（`CONSECUTIVE_FAILURES` 的累計路徑）的明文。
10. **測試替身與 CI**：`aisdlc-mock-claude` 加「慢步驟」與「首次失敗、重試成功」兩個旋鈕（例：`MOCK_CLAUDE_SLOW_REGEX`／`MOCK_CLAUDE_FLAKY_REGEX`），時間型與重試率告警才能不靠繞法驗證；在 Linux CI 確認 Bridge 那 4 支 Windows 略過的 pytest 確實執行。
11. **小項**：O-04（手動重試受 `maxRetries` 限制或明示）、O-05（執行中禁刪未開始目標或明示）、O-07（日誌行遮罩主機絕對路徑）、O-08／O-09（`/api/health` 與快取標頭）、O-16／O-20（`/actuator/prometheus` 與 `internalProxies` 的網路隔離說明）、O-06（部署指引寫明預設帳密必須更換）。
12. **RTM**：每修好一條缺陷，把對應 `❌ 缺陷` 列重跑對應 spec 後改回 `✅ 已驗證`，並刪除該 spec 的 `test.fail`（`E2E_DEFECTS_FIXED=1` 可預覽修復後的真實結果）。

## 15. 補充證據

證據檔（QA 暫存目錄，不入庫）以名稱引用；關鍵輸出已節錄在本節。

### 15.1 Bridge 直連（`br_direct`、`br_orphan`）

Bridge 以 DB 模式在 18081 上，QA 腳本直接打 Bridge（不經 backend），逐條對 RTM 的 `BR-*` 列：

| BR | 指令與結果（節錄） |
|----|-------------------|
| 01 | `GET /health`→200，`engines.autoclaude.version=0.1.0`、`engines.sdd.latest`、`db.ok` |
| 02 | `POST /autoclaude/runs`→201（4 步驟）；同 `run_id` 再送→409 `run_exists`；`execution_path` 在 allowlist 外／`evaluator_command` 含 `;`／regex 無法編譯→422 `sanitization_failed`（`violations[]` 逐項帶 `field`／`rule`） |
| 03、18 | `:pause`→202 `PAUSING`，在步驟邊界到達 `PAUSED`：`reason=在步驟邊界暫停（已完成 1 步，續跑點：S2）`；對 `PAUSED` 再 pause→409 `invalid_state` |
| 04、20 | `:resume`→202 `RUNNING`，跑完 `COMPLETED`（`completed_steps=4/4`、`tokens_used=4960`、`last_event_seq=59`） |
| 05 | `:stop`→202 `CANCELLING`→`CANCELLED`（`pid` 空）；再 stop→409 `invalid_state` |
| 06 | `GET /autoclaude/runs/{id}`：`status`／`completed_steps`／`tokens_used`／`last_event_seq` 與 Console、PG、SSE 一致（§15.2） |
| 07、25 | `GET …/stream`：`after=0` 的前 14 行（`retry: 3000`、`id: 1`、`event: status`、`data: {"seq":1,…}`）；`Last-Event-ID: 8` 只送 `seq>8`；標頭 `cache-control: no-cache`、`x-accel-buffering: no` |
| 08 | `GET …/events?after=3&limit=3`→seq 4～6 |
| 09、10、21 | `GET …/checkpoints`→`after-S1`（`step_idx=1`、`is_automatic=true`）；對終態 run `:restore`→202→重跑完成（`completed_steps=4`） |
| 11、12 | 假 Brain 版 Bridge：`POST /autoclaude/decompose`→200（`draft_id`、`goal_hash`、`reasoning`、`playbook`）；一般 Bridge 無金鑰→422 `brain_unsupported`；`:approve` 缺 `approver`→400 `approver_required`、未知草案→404 `draft_not_found` |
| 13、14 | `GET /sdd/version`（`SDD_ROOT` 指向假樹時 `latest=AISDLC_SDD_v9.99`；repo 的 `sdd_version.py` 回報 LATEST 為 `AISDLC_SDD_v0.30`，兩者語意相同、來源不同）；`GET /sdd/fsm/demo`→200（最後五筆 `decision_trace`）；不存在或惡意名稱→404 `fsm_not_found` |
| 16 | 同專案同路徑第二個 run→409 `advisory_lock_held`（含 `holder_run_id`）；不同專案同路徑→201（不互斥） |
| 17 | RUNNING 中（已完成 4 步）殺掉 Bridge 行程樹→重啟後該 run 標 `FAILED`：`orphaned：Bridge 重啟時子程序已不存在`；鎖釋放，同專案同路徑可重新啟動（201） |
| 19 | Linux 容器內強殺：§7.4 |
| 22～24 | PG：`execution_runs.status` 的 CHECK 只允許 `INITIALIZING／RUNNING／PAUSED／COMPLETED／FAILED／CANCELLED`；81 個批次實際出現 `CANCELLED 17／COMPLETED 46／FAILED 12／PAUSED 6`；`execution_steps` 393 列（`STARTED 193／COMPLETED 172／FAILED 14／RETRYING 14`）、`checkpoints` 172 列（69 個批次有斷點）；`execution_runs` 同一列由兩邊寫（Console：`run_number`、`autonomy_level`、`scope`、`token_budget`、`dag`、`started_at`；Bridge：`status`、`total_tokens_used`、`bridge_instance`、`subprocess_pid`、`console_last_seq`） |

### 15.2 NFR 抽驗與資料庫事實

| 項目 | 證據（節錄） |
|------|-------------|
| NFR-9.2-01 JWT | 登入 `expiresIn=1800`、access 的 `exp-iat=1800`、refresh `604800`（7 天）；refresh 換新可用；refresh 當 Bearer→401 `TOKEN_INVALID`、access 當 refresh→401 `INVALID_REFRESH_TOKEN`、亂字串→401；錯誤密碼→401 `INVALID_CREDENTIALS`。真瀏覽器：access 過期→只打一次 `/auth/refresh`→列表載入、token 換新；refresh 也無效→導向 `/login?next=%2Fprojects`、session 清除 |
| NFR-9.2-03 AES-256 | `PUT model.apiKey`→200，回應與 `GET /settings/model` 皆為 `••••••••`（`hasValue:true`）；PG 的 `system_configs.value` 為密文 `v1:…`（76 字元、不含明文）；歷史只記遮罩；ADMIN `reveal=true` 才回明文且寫審計 |
| NFR-9.2-04 輸入驗證 | 搜尋字串與專案名稱含 SQL 元字元→200／201 逐字存取，`console.projects` 仍在；空名稱＋相對路徑＋空標準→400，`errors[]` 逐欄列出；壞掉的 JSON→400 |
| NFR-9.2-07 審計 | PG `audit_log`（`subject`／`role`／`method`／`path`／`entity_type`／`entity_id`／`http_status`／`trace_id`，不含請求本文）2,091 列，被拒的寫入（400／403）也有紀錄；後端日誌同步輸出 audit JSON 行含 `traceId` |
| NFR-9.4-03 OpenAPI | `/v3/api-docs`→200（OpenAPI 3.1.0、53 個 paths、109 個 schemas）；`/v3/api-docs.yaml`、`/swagger-ui/index.html` 皆 200 |
| NFR-OBS-01 四源一致 | 同一個已完成批次：console-api `GET run`（`COMPLETED`、3/3、`totalTokensUsed=3720`、`lastEventSeq=33`）、Bridge `GET run`（同）、PG `execution_runs`（`total_tokens_used=3720`、`console_last_seq=33`、`execution_steps` 3 列 `COMPLETED`）、SSE `/logs` 最後框架的 seq＝33 |
| 資料庫 | PostgreSQL 18.4；Flyway V1～V7 全 `success`；`console` schema 14 張應用表加 `flyway_schema_history`；3 個 partial index（含 `uq_alerts_open_rule_subject`＝告警去重兜底）、共 36 個索引；`system_configs` 50 列（`agent 9／autoclaude 11／execution 10／model 10／monitor 6／sdd 4`） |

### 15.3 無障礙、跨平台、相容性

- **axe-core 4.14.0**（WCAG 2.0／2.1 A／AA 規則）掃 11 頁（登入、總覽、專案列表、新建專案表單、專案詳情、目標詳情、任務詳情、執行頁、監控頁、設定頁、匯入頁）：違規節點 310 個＝`color-contrast` 257、`label-content-name-mismatch` 31、`svg-img-alt` 18、`list` 1、`listitem` 3。顏色分組：`#edf3e9` 於 `#498428`（12px）4.03:1 共 30 個樣本節點、`#e4eddf` 於 `#498428`（11px）3.79:1 共 11 個、`#7a8775` 於白底 3.78:1。詳見 DEF-AC-004／005。
- **鍵盤焦點**：`design-system.spec.ts` 的焦點環測試——鍵盤依序 Tab 過頂列每個停駐點，皆為 2px 實線主色外框；全站鍵盤操作（Esc 關閉對話框、拖曳的鍵盤替代）未逐頁驗（UI-A11Y-02 維持 🟡）。
- **雙形態文件（NFR-XPL-01）**：AgentConsole 下 33 份 md，10 份含指令區塊者 bash 與 PowerShell 區塊數逐檔相等；只有 `W3B1_BACKEND_IMPORT_SETTINGS.md`、`W4F1_FRONTEND_IMPORT_SETTINGS.md` 兩份任務書只有 PowerShell（O-10）。
- **行尾與索引模式（NFR-XPL-04）**：`git ls-files --eol`：`gradlew`（index lf／worktree lf）、`gradlew.bat`（index lf／worktree crlf，`.gitattributes` 設 `eol=crlf`）皆入庫；Windows 以 `gradlew.bat clean build` 實跑 rc=0。
- **零侵入（NFR-COMPAT-01）**：14 個觸及 `AgentConsole/` 的 commit 中，沒有任何一個改 AutoClaude 的 `autoclaude/` 或 AISDLC_SDD 的框架 runtime；唯一的引擎區變動是 `e6d266f5` 在 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 的 CI 掃描豁免前綴加一項 `AgentConsole/`（CI 登記，非引擎行為；但字面上動了 `AgentConsole/CLAUDE.md` 鐵律 7 禁止的 `AISDLC_SDD/` 目錄，請主控知悉）。

### 15.4 API 補測（QA 腳本，本機真後端）

| 項目 | 指令與結果（節錄） |
|------|-------------------|
| 健康與指標（API-HLT-01～03） | `GET /actuator/health`（無 token）→200 `{"groups":["liveness","readiness"],"status":"UP"}`；`GET /actuator/prometheus`（無 token、operator、admin）→200，657 行指標含 `http_server_requests`／`jvm_`／`hikaricp_`；前端 `GET /api/health`→200 `{"status":"ok"}` |
| 專案手動狀態轉移（API-STM-01） | `PUT /projects/{id}` 的 `status`：`READY`→200、`DRAFT`→200、`READY`→200；`EXECUTING`→409「不可手動轉移至該狀態」；`COMPLETED`→409；`ARCHIVED`→409；viewer→403。PENDING 任務 `POST /tasks/{id}/retry`→409「目前狀態不可重試」 |
| 狀態機實際走過的狀態（API-STM-01～03，`stm_sample`） | 批次進行中每 0.35 秒取樣專案／目標／任務：`P=DRAFT`→`EXECUTING`（0.0 秒，任務 QUEUED）→ 1.5 秒 `G1=IN_PROGRESS`、任務一 `RUNNING` → 2.3 秒任務一 `COMPLETED`、任務二 `RUNNING` → 3.0 秒 `G1=COMPLETED`、`G2=IN_PROGRESS`、任務三 `RUNNING` → 3.8 秒 `P=COMPLETED`、全部 `COMPLETED`。失敗情境（任務二帶 `[FAIL_ME]`）：`P=FAILED`、`G1=FAILED`、`G2=PENDING`；任務一 `COMPLETED`、任務二 `ESCALATED`（`retryCount=1`）、任務三由 `QUEUED` 被系統重設回 `PENDING`（契約 E2E-05 步驟 3）。`VALIDATING` 過短未取到 |
| Token 單一任務／目標上限（US-E-10，`exe_limits`） | `scope.limits.taskTokens=1000`：批次 `PAUSED`（已完成 2/3、不建審核項），告警 `TOKEN_BUDGET_EXCEEDED`／`CRITICAL`／`task:<id>`／「任務「設定」Token 用量 1240 超過上限 1000，已要求暫停執行」（任務「初始化」另一則同形）；`resume`→200→跑完 `COMPLETED`（3,720）。`scope.limits.goalTokens=2000`：告警「目標「基礎」Token 用量 2480 超過上限 2000，已要求暫停執行」（`goal:<id>`），同樣暫停、可恢復。`limits.taskTokens=0`→400 `scope.limits.taskTokens`「單一任務 Token 上限必須 ≥ 1」 |
| 執行中的限制（`exec_lock`） | `EXECUTING` 專案：`PUT` 通過標準→409（`details.fields=["passCriteria"]`）、只改名稱與說明→200、`DELETE` 專案→409「EXECUTING 狀態的專案不可刪除」；`DELETE` RUNNING 任務→409；`DELETE` 尚未開始的目標→**204**（批次仍跑完，O-05）；跑完後 `PUT` 通過標準→200、`DELETE` 專案→204（軟刪除） |
| 步驟分頁與 DAG（API-EXE-06／07） | `steps?page=0&size=2&sort=stepNumber,asc`→`content=2`、`totalElements=6`、`totalPages=3`；`size=200`→6 列（`G1-T1:STARTED`、`COMPLETED`、`G1-T2:…`、`G2-T1:…`）；`size=0`→400；`/dag`→200（5 個節點：2 目標＋3 任務、4 條邊）；不存在的 runId→404、格式錯誤→400 |
| 設定（API-SET-01／07） | `GET /settings?reveal=abc`→400；viewer `reveal=true`→403「僅 ADMIN 可揭露敏感參數」；ADMIN→200；歷史 `size=2`→`totalElements=158`、`totalPages=79`；`category=model&key=apiKey` 的 `newValue` 全為遮罩 |
| 任務詳情與手動重試（US-T-02／05／06） | 已完成任務詳情頁含執行歷史（STARTED／COMPLETED、`tokensUsed` 1,240）與執行日誌面板（含「搜尋執行日誌」）；ESCALATED 任務的「重試」按鈕→`POST /retry` 200，toast「已重新排入佇列（重試 3 / 1）」，DB 為 `QUEUED`、`retry_count=3`（O-04）；日誌行含 `path=C:\Users\…`（O-07） |
| **告警 `CONSECUTIVE_FAILURES`（API-ALR-03）** | 夾具 PRJ-B（任務一～三全帶 `[FAIL_ME]`，Level 4）。**路徑 1（`SKIP`）**：每批失敗後 SKIP→後續批次，三批後專案只有 1 則 `ENGINE_ESCALATION`，沒有 `CONSECUTIVE_FAILURES`（SKIP 使任務成為 SKIPPED，自序列消失）。**路徑 2（`REJECT` 後重跑 `ALL`）**：四次重跑都卡在任務一（`ESCALATED`），任務二、三維持 `PENDING`。**路徑 3（`scope.mode=SELECTED`＋`taskIds` 逐批各選一個）**：第 1 批 `FAILED`／`ESCALATED`、`REJECT`→第 2 批→第 3 批：第 3 批的審核項 reason 為「任務「任務三」重試 1 次仍失敗，需要人類介入：…（連續 3 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）」，告警 `CONSECUTIVE_FAILURES`／`CRITICAL`／`goal:<id>`／「目標「基礎」連續 3 個任務失敗」；三個任務皆 `ESCALATED`。第 2 批沒有新的 `ENGINE_ESCALATION` 列（O-14）。已落成 `p4b-execute-more.spec.ts` 的測試 |
| **告警 `AGENT_UNRESPONSIVE`（API-ALR-04）** | `PUT /settings/monitor/alertAgentTimeoutSec` 試 `10`→400「需為整數（30～86400）」；調到 `30`；25 個任務的批次進行中（已完成 2 步）殺掉 Bridge→殺後 47 秒出現告警：`AGENT_UNRESPONSIVE`／`CRITICAL`／`run:<id>`／「Agent 已超過 30 秒無回應」；此時 `GET run` 為 `RUNNING`、`bridge.connected=false`；重啟 Bridge→run 標 `FAILED`（BR-17）；門檻 `reset` 回 300 |
| **告警 `TASK_DURATION_EXCEEDED`（API-ALR-05）** | 把 `agent.taskTimeout` 調到下限 10、`monitor.alertTaskDurationMultiplier` 調到 1.0；同樣殺掉 Bridge→殺後 22 秒：`TASK_DURATION_EXCEEDED`／`WARNING`／`task:<id>`／「任務「任務4」已執行 20 秒，超過門檻 10 秒（1 倍）」；三個門檻 `reset` 回 600／2.0 |
| **告警 `HIGH_RETRY_RATE`（API-ALR-06）** | backend 以 `--console.execution.mock-env[MOCK_CLAUDE_FAIL_REGEX]=^[^#]` 重啟（引擎的首次嘗試 prompt 以 `===` 或 `[總目標` 開頭、重試 prompt 以 `## 任務` 開頭，此 regex 只讓首次嘗試失敗）：5 個任務皆 `STARTED→RETRYING→COMPLETED`、`retryCount=1`；兩個目標各出現 `HIGH_RETRY_RATE`／`WARNING`／`goal:<id>`／「目標「基礎」重試率 100%，超過 50%」；還原預設參數後，無重試的對照批次告警 0 筆 |
| **審核 RETRY 的 `RESTORE` 告警（F2-2）** | Level 4、任務二帶 `[FAIL_ME]`：ESCALATED 審核項 `RETRY`→204、無 `X-Follow-Up-Run-Id`（同一批次內部 restore）；SSE `/logs` 出現 1 則 `alert`：`origin=ENGINE`、`code=RESTORE`、`severity=INFO`、「從 checkpoint「after-G1-T1」（step_idx=1）還原並續跑」；任務二再度失敗的第二則 `ESCALATION` 告警被去重擋下，SSE 仍轉發（不帶 `alertId`） |
