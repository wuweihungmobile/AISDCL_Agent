# Test Contract Specification — 自我進化核准流程全程可見（Console 半，第一波：Bridge 巡邏快照讀取端點與唯讀掛載、backend 巡邏端點、單筆提案詳情透傳、提案詳情對話框〔diff、提案本文、評估集與驗證、時間線〕、巡邏狀態卡與推送狀態、待入帳寫入面板的入帳結果、自我進化頁說明、E2E 與無障礙）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層半另有 `docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md`）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件含 Console PRD §0.11、SelfImproving 鏡像／決定／排程三代的契約與 TCS）的單一 Feature（核准流程可見的 Console 半）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SiFlowVisibility-20261111.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-911 |
| **Feature 名稱** | 自我進化核准流程全程可見（Console 半，第一波）——Bridge `GET /si/patrol`（唯讀讀取主機寫的 `patrol.json`；`app/si_report.py` 新）、compose 新增唯讀 bind `/si-report` 與環境變數 `BRIDGE_SI_REPORT_DIR`、console-api `GET /api/v1/si/patrol`（API-SI-16）、單筆提案端點對根層 `detail` 物件的透傳（API-SI-05 擴充）、前端提案詳情對話框（`SiProposalDetail.tsx`、`SiDiffView.tsx`）、巡邏狀態卡（`SiPatrolCard.tsx`）、待入帳面板的入帳結果、純函式庫 `lib/domain/siFlow.ts`、自我進化頁說明、mock 與 Docker 全棧 E2E 與無障礙 |
| **User Story** | US-931（Console PRD §0.12；本檔 FRD-lite 沿用 US-931 對映） |
| **建立日期** | 2026-11-11 |
| **輸入快照** | HEAD＝`e1ad0ac0`（`git rev-parse HEAD` 現查）；上位檔 digest 見〈增量追溯表〉，**由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 重算**（本欄值未預填，避免快照過期） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝鍵 `agentconsole-si-flow-visibility` 的三個開發 agent〔PKG-BR、PKG-BE、PKG-FE〕，三方不同） |
| **FSM 功能鍵** | `agentconsole-si-flow-visibility`（**依賴根層鍵 `monorepo-si-p7-flow-visibility` 的規格已凍結**〔`detail` 八欄、`patrol.json` schema_rev 1、原因碼與白話字表、黃金樣本的位元組權威；已凍結於根層 TCS-P7 §2、附錄 A〕；真全棧 E2E 與真入帳 V 項須待根層實作完成。一律從 monorepo 根啟動：`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-flow-visibility`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature。**凍結檔不得再改**：發現需修訂處一律寫在 §7 的清單，走掌舵者 T1／SPEC_REGRESSION_CHECK。**與根層 TCS 的接縫**：`detail` 的八個欄位語意、`patrol.json` 的欄位與原因碼白話字、`nextstep.of` 的判準，**一律引根層 PRD v0.16 與根層 TCS（`TCS-SelfImproving-P7-20261111.md` §2、附錄 A）的條文編號、不在本檔複寫判準**；本檔只釘 Console 側（HTTP 形狀、欄名對映、前端呈現與保底、Bridge 讀檔、部署、角色、無障礙）。介面契約（本檔 §0.2 C-1～C-6）是 Console 側的唯一定稿處，**不改**既有契約檔（`API_Contract_SelfImproving_P1b／P2b／P2c.md` 為凍結檔；Architecture §10.5 只留簡表）。

### FRD-lite

**現況與變更（Before／After；brownfield；現況於撰寫時現查，每項附座標）**

- Before：(1) 提案分頁每筆只有九欄與卡面 `<pre>`，展開區 `ProposalDetail`（`SiProposalsPanel.tsx`）無 diff、本文、評估集、沙盒、驗證證據；`getSiProposal`（`lib/api/endpoints.ts`）已匯出但頁面未使用；(2) Bridge `routers/si.py` 有六個 export 型 GET、兩個議題 GET、五個寫入 POST、一個預檢 POST；compose 的 engine-bridge 有六條 SI 唯讀 bind（設計 A）與一條可寫稽核 bind（`/si-audit`，`docker-compose.yml`「唯一一條可寫的 SI bind」註解）；(3) `SiWritesPanel.tsx` 只列待入帳，入帳被拒時 backend 說明文字自承「稽核列原地不動、持續顯示待入帳」；(4) SI 查詢一律 `SI_QUERY_OPTIONS`（不重試、不留快取、不輪詢，`queries.ts`）；(5) 非 ADMIN 零 `console-writes` 請求（`useSiConsoleWrites`）；(6) `GET /api/v1/si/console-writes` 的 `items[]` 恰十一鍵（`SiConsoleWritesResponse.Item`；`TCS-SelfImprovingDecideDedupe` 與 `SiConsoleWritesReadApiIT` 逐字釘住）。
- After：(1) 提案列新增「詳情」鈕，開啟對話框後才取數（只有一個請求 `GET /api/v1/si/proposals/{id}`，時間線與來源觀察皆取自回應的 `detail.timeline`、`detail.sourceObs`，不再打議題端點）；(2) Bridge 新增 `GET /si/patrol`（只讀 `BRIDGE_SI_REPORT_DIR/patrol.json`）；compose 新增第七條 SI 相關 bind，**唯讀**；(3) console-api 新增 `GET /api/v1/si/patrol`（VIEWER 以上）；(4) 巡邏狀態卡掛在自我進化頁（所有角色）；(5) 待入帳面板以**前端結合**方式顯示入帳結果：用稽核編號對照巡邏快照的 `ingest[]`；**不改** `console-writes` 回應形狀（理由見 §7.1 第 3 項）；(6) 單筆提案端點的回應多一個根層帶來的 `detail` 物件，Bridge 只放行契約列出的鍵、其餘丟棄（新純函式 `filter_detail`，W-F4），backend 只做鍵名轉換（snake_case→camelCase，程式零邏輯改動、只加測試與文件）。
- **非目標**：不新增任何寫入端點、DB 表、Flyway 版本、稽核 kind；不改 `si_cli.py` 的 argv 動詞白名單；不改 `console-writes` 與既有 Bridge 路由的行為；不做「按鈕推送」「取消待入帳」「觀察送去提案」「退回後自動修訂」「缺評估集自動凍結」「取消運轉」（第二波，鍵 `agentconsole-si-flow-crud`）；不輪詢；不在 Console 持有任何白話原因字表（白話字表的單一家在根層，Console 只持有**少數固定列舉的標籤**〔運轉目的三值、驗證結果三值、入帳狀態兩值〕與**未知值保底句**，§0.2 C-5；推送狀態、原因碼、等待對象一律顯示根層給的白話欄或中文值）；不顯示評估集內容。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：AC 取 `AC-966-1`～`AC-966-17`，與 Console PRD §0.12 的 AC 清單逐號對映；`AC-965-*` 已被研究來源單一化占用，不得使用。本檔不自增 AC。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-966-6-3`→`AT_966_6_3`；Java 方法名以底線形開頭加駝峰敘述）。每個 AC 內數字序與 E 序各不超過 9，使 `-t`、`--tests`、`-k`、`-g` 的子字串比對不會誤收其他 AT。
4. **計數**：AC 17 個、AT 113 個（編號含 `E` 的負控與邊界 22 個；分佈見 §3 末）。

**FRD-lite 表**（第一欄為 US ID；AC 的完整 Given／When／Then 住各 AT，本表給摘要）

| US ID | User Story | AC ID | AC（Given／When／Then 摘要） |
|-------|------------|-------|-----------------------|
| US-931 | 身為掌舵者，我想在 Console 看得到每個自我進化提案的完整內容、「現在卡在哪、等誰」、巡邏器有沒有在跑、我送出的決定有沒有被主機接受，以便不必開命令列就能核准與追進度 | AC-966-1 | Given 主機寫了 `patrol.json` When Bridge 被問 `GET /si/patrol` Then 只讀、驗形狀與大小、缺席與壞檔各有原因碼 |
| US-931 | 同上 | AC-966-2 | Given compose 與環境變數 When 檢視部署 Then 唯讀 bind 條件齊備、未掛載時行為明確且不影響其他 SI 功能 |
| US-931 | 同上 | AC-966-3 | Given console-api When 三種角色取巡邏狀態 Then VIEWER 以上可讀、欄名對映、Bridge 錯誤逐字透傳 |
| US-931 | 同上 | AC-966-4 | Given 根層 export 回 `detail` When 取單筆提案 Then backend 原樣透傳、Bridge 只放行契約列出的鍵（含超大 patch、缺欄、主機多帶的鍵被丟棄） |
| US-931 | 同上 | AC-966-5 | Given 任一快照或詳情資料 When 純函式判讀 Then 新鮮度、下一步來源、標籤保底、diff 解析與結合規則確定 |
| US-931 | 同上 | AC-966-6 | Given 提案列 When 開詳情 Then 懶取數、五分頁、載入／錯誤／缺欄三態與頂端「下一步」 |
| US-931 | 同上 | AC-966-7 | Given patch 文字 When 渲染 Then 顏色以外的標示、截斷、視窗化、下載與缺席皆符規格 |
| US-931 | 同上 | AC-966-8 | Given 提案本文與來源 When 檢視 Then 純文字、來源觀察可跳轉、缺席有說明 |
| US-931 | 同上 | AC-966-9 | Given 評估集與沙盒與驗證資料 When 檢視 Then 不洩漏評估集內容、三步證據與原因白話、未知值保底 |
| US-931 | 同上 | AC-966-10 | Given 提案事件 When 切到時間線 Then 才取數、依 seq 升冪、失敗不影響其他分頁 |
| US-931 | 同上 | AC-966-11 | Given 快照新舊與缺席情境 When 開自我進化頁 Then 新鮮度警示與三種缺席畫面各自明確 |
| US-931 | 同上 | AC-966-12 | Given 快照內容 When 檢視巡邏狀態卡 Then 提案卡住原因、為什麼沒有啟動運轉、進行中運轉、步驟、推送狀態白話呈現且無推送按鈕 |
| US-931 | 同上 | AC-966-13 | Given 待入帳列與快照 When 檢視寫入面板 Then 拒收原因、延後、量不到、最近已入帳各有呈現 |
| US-931 | 同上 | AC-966-14 | Given VIEWER／OPERATOR／ADMIN When 走完整旅程 Then 零寫入、零多餘請求、無 PII 以外的角色差異 |
| US-931 | 同上 | AC-966-15 | Given 說明頁與新字串 When 機械鎖檢查 Then 四段說明、可讀性、保底句與垃圾輸入不洩漏 `null`／`undefined` |
| US-931 | 同上 | AC-966-16 | Given 三寬度 mock When 走流程與無障礙檢查 Then axe 零違規、無橫向溢出、鍵盤可用 |
| US-931 | 同上 | AC-966-17 | Given 真全棧與拋棄式快照目錄 When 改快照 Then 新鮮、過時、缺席三畫面與真提案詳情皆成立 |

**本增量交付物**（D1～D9；路徑相對 monorepo 根；三個開發包的持有面見〈提交順序與責任〉）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | Bridge：`app/si_report.py`（新；讀檔、驗形狀、常數 `PATROL_REPORT_MAX_BYTES`）、`app/si_detail.py`（新；`filter_detail` 白名單，W-F4）、`routers/si.py` 加 `GET /patrol` 並讓單筆提案路由對 `items[0].detail` 套 `filter_detail`、`settings.py` 加 `si_report_dir` 與環境變數 `BRIDGE_SI_REPORT_DIR`；測試 `tests/test_si_patrol_route.py`、`tests/test_si_proposal_detail.py`、`tests/test_si_deploy_config.py`（加案）、`tests/fake_si.py`（加 `detail` 夾具）、`tests/test_si_readonly_lock.py`（只改預期值） | `AgentConsole/engine-bridge/` | PKG-BR | AC-966-1、2、4 |
| D2 | 部署：`docker-compose.yml` 唯讀 bind 與環境變數、`.env.example` 一段、`docker/README.md`〈巡邏回報目錄〉一節（**長駐棧升級序列**：預建目錄→重建映像→啟動→驗證→失敗表徵→退回，內容見 §6.2 V1；預建指令雙 shell） | `AgentConsole/docker-compose.yml`、`AgentConsole/.env.example`、`AgentConsole/docker/README.md` | PKG-BR | AC-966-2 |
| D3 | backend：`SiController.patrol()`（`getSiPatrol`）、`SiMirrorUseCase.patrol()`、`SiMirrorQueryService`、`AgentBridge.siPatrol()`、`BridgeHttpAdapter` 實作、`ErrorResponseDocumentation` 補四個 cause、OpenAPI 說明；測試 `SiPatrolApiIT`、`SiProposalDetailApiIT`、`AbstractApiIT` 迷你 Bridge 加 `MINI.patrol(...)` 與 `MINI.proposalDetail(...)` | `AgentConsole/backend/` | PKG-BE | AC-966-3、4 |
| D4 | frontend 純函式、型別、端點：`lib/domain/siFlow.ts`（新）、`lib/api/{endpoints,queries,types}.ts`（`getSiPatrol`、`useSiPatrol`、`useSiProposalDetail`、`qk.siPatrol`）、`schema.d.ts` 重產；**不新增** `useSiProposalTimeline`（時間線取自 `detail.timeline`） | `AgentConsole/frontend/lib/` | PKG-FE | AC-966-5 |
| D5 | frontend 元件：`SiProposalDetail.tsx`、`SiDiffView.tsx`、`SiPatrolCard.tsx`（皆新）、`SiProposalsPanel`（加「詳情」鈕）、`SiWritesPanel`（加入帳結果）、`SiView`（掛卡與對話框、來源觀察跳轉狀態）、`SiObservationsPanel`（加 `highlightId`）、`lib/help/self-improving.ts`；另新增 `useMinuteTick`（每分鐘重繪、不發請求，供新鮮度與相對時間隨時間前進，W-F5） | `AgentConsole/frontend/components/domain/si/`、`lib/help/` | PKG-FE | AC-966-6～15 |
| D6 | E2E：`self-improving-flow.mock.spec.ts`（新）、`self-improving-flow-docker.stack.ts`（新）、既有 SI mock spec 補路由 | `AgentConsole/frontend/tests/e2e/` | PKG-FE | AC-966-16、17 |
| D7 | 夾具：夾具以**建構函式**提供，不做 JSON 檔：vitest 用 `frontend/tests/helpers/siFlow.tsx`（`PATROL(over)`、`DETAIL(over)`、`renderFlow`、`camelKeys`）與 `tests/helpers/siClock.ts`（可控時鐘替身），Playwright 用 `frontend/tests/e2e/siFlowFixtures.ts`（Playwright 不能引用含 testing-library 與 `@` 別名的 vitest 輔助，且新鮮度須依真時鐘計算；`patch-big` 本就由測試產生）；兩者皆 **camelCase 形態**（`generatedAt`、`heartbeatMinutes`⋯，即前端實際收到的鍵名）；入庫的檔只有 `frontend/tests/fixtures/si/flow/patch-mixed.diff`；另 `patrol.golden.json`、`detail.golden.json` 為根層黃金樣本複本，見 §5.1）、`tests/helpers/si.tsx` 加 `patrol` 端點、`engine-bridge/tests/fixtures/si_report/*.json` | 同上 | PKG-FE／PKG-BR | 各 AC |
| D8 | 既有釘選測試同步（只改預期值；逐項見 §4.1） | §4.1 | 三包各自持有面 | NFR-FV-5 |
| D9 | 出口實查（V 系列，非 AT） | §6.2 的 V1～V8 | QA、主控、掌舵者 | PRD §0.12 |

**提交順序與責任**

- 依賴序：根層實作輪先產出黃金樣本 `tools/tests/fixtures/selfimproving/p7/patrol.golden.json` 與 `detail.golden.json`（根層 TCS-P7 §3、AT-790-5-1／5-E-1 鎖；LF、無 BOM、結尾一個 LF）→ 主控原樣複製到 `AgentConsole/engine-bridge/tests/fixtures/si_report/`、`AgentConsole/backend/src/test/resources/si/p7/`、`AgentConsole/frontend/tests/fixtures/si/flow/`（複本檔名同）。**位元組一致性由測試機械判定**：各側有一個先行測試，以 repo 根相對路徑讀根層檔與本地複本，斷言逐位元組相等（任一方改動即紅；複製時主控另以 `Get-FileHash -Algorithm SHA256 <根層檔>,<複本>` 目視核對）→ PKG-BR（Bridge、compose）→ PKG-BE（backend；需 PKG-BR 的路由契約，但以迷你 Bridge 自足，可並行）→ PKG-FE（純函式與元件可與 PKG-BE 並行開工；`schema.d.ts` 須待 PKG-BE 完成後以拋棄式 IT 倒 `/v3/api-docs` 餵 `scripts/gen-api.mjs` 重產入庫，沿 P2b 勘誤 9 作法）。每支程式完成即編譯並跑該區 AT，不累積（`AgentConsole/CLAUDE.md` 鐵律 11）。
- **三包持有面互不重疊、可並行**（根鐵律七）：PKG-BR＝`AgentConsole/engine-bridge/**` 與 `AgentConsole/docker-compose.yml`、`.env.example`、`docker/README.md`；PKG-BE＝`AgentConsole/backend/**`；PKG-FE＝`AgentConsole/frontend/**`。共用物只有黃金樣本複本（主控複製）；三包不得互改對方目錄。
- 開發 agent **不 commit／push**、不動根層 `tools/`、`.github/`、`.claude/`、凍結檔與既有 TCS（鐵律 7）。`Architecture.md` 與 Console PRD 本鍵已由 SA 棒改好（凍結前一併進 refreeze）；RTM 本地子表與 SCG-4 報告由主控代做；`lib/help/*` 的頁面說明由前端開發者實作（與 UI 同 commit，文案由 SCG-4 人讀把關）。
- 真 SI 家目錄 `~/.autosdd/`、真帳本、真事件帳本、真 `patrol.json` 一律唯讀且**不得被任何 AT 寫入**：AT 只用暫存目錄、迷你 Bridge、jsdom、fetch 替身與 Playwright 路由替身；Docker 全棧 E2E 的 `BRIDGE_SI_REPORT_DIR` 對應的 bind 來源必須是全棧自帶的拋棄式目錄（不得掛真 SI 家目錄；AT-966-17-3 斷言之）。

**〈增量行為規則〉**（W-F0～W-F12；各 AT 以 W-F 編號引用。實查依據：`routers/si.py`、`si_cli.py`（stdout 上限 8 MiB、逾時 15 秒）、`settings.py`（`si_audit_dir` 與 `_anchor_guard`）、`docker-compose.yml`、`SiController.java`、`SiConsoleWritesResponse.java`、`SiReadOnlyArchTest`、`OpenApiIT`、`SiProposalsPanel.tsx`、`SiWritesPanel.tsx`、`SiView.tsx`、`SiStatusBanner.tsx`、`queries.ts`〔`SI_QUERY_OPTIONS`〕、`tests/helpers/si.tsx`、`dialog.tsx`、`pill-tabs.tsx`）

- **W-F0 零退步與只看不寫**：本鍵不新增任何非 GET 請求、DB 表、稽核 kind；既有 SI AT 的預期值只因「Bridge 路由數」「backend GET／OpenAPI 計數」「`SI_READ_FUNCTIONS`」「提案列多一個唯讀按鈕」「SI 頁多一個 `patrol` 請求」五類原因改動（§4.1 逐項）。
- **W-F1 Bridge 讀快照**：固定檔名 `patrol.json`；每個請求恰讀一次、不快取、不寫任何檔、不啟動子行程；回應 `{schema_rev:1, kind:"patrol", read_at, report}`，`report` 是檔案解析後的物件**逐值透傳**（鍵序保留、非 ASCII 不跳脫）；只驗形狀（頂層為物件、`schema_rev` 為整數 1、`generated_at` 為帶 offset 的 ISO 字串）與大小（≤ `PATROL_REPORT_MAX_BYTES`＝1048576 位元組，Bridge 唯一定義處）；原因碼四個（`report_dir_unset`、`report_missing`、`report_unreadable`、`report_invalid`），一律 503 `si_unavailable` 加 `cause`；任何查詢參數 422。
- **W-F2 部署**：新 bind 為長語法、`read_only: true`、`create_host_path: false`、來源以 `console_report` 結尾且不寫死磁碟路徑、與稽核 bind 不同目錄；engine-bridge 仍只有**一條**可寫 bind。
- **W-F3 backend 巡邏端點**：`GET /api/v1/si/patrol`（API-SI-16，operationId `getSiPatrol`），VIEWER 以上；每請求恰一次 Bridge 呼叫（連線 2 秒、讀取 20 秒、不重試）；欄名對映同 `SiKeyNames`（snake→camel，其餘恆等）；失敗沒有 `data`；零 DB 寫入。
- **W-F4 詳情透傳與 Bridge 白名單**：`items[0].detail` 由根層產生；backend 不增刪改任何鍵與值（只改欄名風格）；**Bridge 只放行契約（C-3）列出的鍵，其餘一律丟棄**（純函式 `app/si_detail.py::filter_detail`，只作用於 `items[0].detail`；頂層八欄、各區塊與 `sourceObs[]`、`verify.reasons[]`、`timeline[]` 項目內的鍵皆以白名單過濾，值逐值不動、鍵序保留）——這是 Console 側「評估集內容與其他未列欄位永不外送」的真防線（主機端多帶 `cases` 之類的鍵時，Bridge 就擋下，AT-966-4-6 可被造成紅燈）；`detail` 不是物件時視為缺席（移除該鍵）；**形狀不符一律丟棄（fail-closed）**：白名單內的純量鍵若值是物件或陣列、區塊（`patch`、`heldout` 等）型別不符、陣列（`sourceObs`、`reasons`、`timeline`）內的非物件元素，皆丟棄；白名單**只認 camelCase 鍵**（與根層 TCS-P7 §2.1 一致：根層以 camelCase 輸出 `detail`，如 `touchedOk`、`belowMin`、`probesN`，其測試 `test_selfimproving_p7_report.py` 逐鍵斷言；snake_case 鍵到達 Bridge 時視為未列鍵而丟棄，backend 的 snake_case 轉換只在 backend 測試構造）；清單端點不含 `detail`；`detail` 缺席（舊根層）時原樣缺席。
- **W-F5 新鮮度與「隨時間前進」**：`stale ⇔ ageMinutes > 2×heartbeatMinutes + 5`（嚴格大於）；`ageMinutes = (readAt − generatedAt) ＋ (現在 − 資料抵達瀏覽器的時刻)`——前一項以 Bridge 讀取時間為準（避免瀏覽器與主機時鐘偏移），後一項只用瀏覽器自己的兩個時刻相減（單調、與偏移無關；資料抵達時刻取查詢的 `dataUpdatedAt`）；`readAt` 缺席或無法解析時退用「現在 − generatedAt」並在畫面標明「（用瀏覽器時間估算）」。畫面上的相對時間（「上次心跳：N 分鐘前」）與過時警示**每分鐘重算一次**（`useMinuteTick`：只重繪、**不發任何網路請求**），所以頁面放著不動，原本新鮮的快照在跨過門檻的那一分鐘會自動轉成過時警示、相對時間也不會停在讀取當時的數字（這是掌舵者最在意的「畫面不能說謊」情境；仍沿 `SI_QUERY_OPTIONS` 不輪詢）；畫面另標「資料讀取於 <readAt>」，並在過時時提示「按『重新整理』取得最新回報」。`heartbeatMinutes` 非正整數＝無法判斷（不算過時也不算新鮮）；`generatedAt` 比 `readAt` 晚超過 5 分鐘＝時鐘異常。常數 `STALE_FACTOR=2`、`STALE_GRACE_MINUTES=5` 只住 `lib/domain/siFlow.ts`。
- **W-F6 下一步的來源序**：(1) 快照可用（有效、未過時〔含 W-F5 的時間前進〕、`ledgerSeq ≥ 該提案 lastSeq`）且 `props[]` 有該提案 ⇒ 用快照那筆；(2) 否則用單筆詳情的 `next`；(3) 兩者皆無 ⇒「量不到」；快照過時且等待對象為「巡邏器」時，加一行「巡邏可能沒在跑，這一步可能不會自動進行」。
- **W-F7 原因碼與列舉的保底（單一真相源在根層，Console 不另寫白話）**：凡根層帶出的原因碼一律同帶白話欄——`ingest[].text`、`props[].text`、`push.text`、`schedule.current.text`、`schedule.last_skip.text`、`runs.waiting[].text`、`detail.next.text`、`detail.verify.reasons[].text`、`detail.sandbox.failText`、`detail.heldout.neNote`、`ne[].text`（新碼項）——Console **逐字顯示**；白話欄缺席、空字串或非字串時用保底句（含原因碼原文：「主機沒有提供白話說明（原因碼 X）。」）；碼也缺席用「主機沒有提供原因。」。Console **不持有任何原因碼→白話對照表**，也不持有推送狀態的對照表（`push.state` 只用來決定樣式與是否為已知值，顯示的句子是 `push.text`）。Console 持有的列舉標籤**只有**（皆為根層未提供白話欄的固定小集合）：運轉目的第一波三值（`scheduled`→「排程啟動」、`console`→「從畫面按『立即啟動』」、`manual`→「手動啟動」）、驗證結果三值（`PASS`→「通過」、`FAIL`→「未通過」、`NE`→「無法評估」）、入帳狀態兩值（`rejected`→「被拒收」、`deferred`→「延後」）；等待對象五值本身就是中文，原樣顯示、只驗是否屬於該五值。**第二波才有的值（運轉目的 `freeze`／`revise`／`propose`、`runs.queued[]` 元素）不得當成已知值**：目的當未知值顯示、`queued` 不渲染。未知值一律顯示「未知值『X』」＋原文，不套用成功樣式。**Console 不列舉任何原因碼集合**：根層之後新增的碼（例如 `push.code` 的 `PUSH-NOT-RECORDED`、`PUSH-RECORD-MISMATCH`、`PUSH-LEDGER-RULE`，皆 `blocked`、`retry` 為 null；`props[].code` 的 `COMMIT-LEFTOVER`、`COMMIT-RECORD-FAILED`）一律只靠白話欄顯示，不需要 Console 認得，AT 夾具不得以碼集合斷言畫面。
- **W-F8 diff 呈現**：每行保留原文（含行首符號）；種類＝`add`（`+` 起頭且非 `+++ `）、`del`（`-` 起頭且非 `--- `）、`hunk`（`@@`）、`file`（`+++ `／`--- `／`diff `／`index `）、`meta`（`\`）、`ctx`（其餘）；顏色以外的標示＝行首符號＋左邊框（add 實線、del 虛線）＋讀屏前綴；預設視窗 400 行（`DIFF_WINDOW_LINES`）；下載內容＝畫面已取得的全文。
- **W-F9 評估集隱私與低於下限提示**：只顯示 `frozen`、`seq`、`n`、`min`、`belowMin`、`frozenBy`、`neNote` 七個欄位，**不顯示 `digest8`**（理由：它是評估集內容的指紋，對決定無用、且「評估集零外露」寧嚴勿鬆）；其他任何鍵（含未知鍵）一律不渲染；畫面不出現評估集的案例、探針、突變檔與 digest。`belowMin===true` 時顯示 `neNote`（逐字，根層白話）；`neNote` 缺席或空字串時才用 Console 的保底句「案例數低於下限，驗證結果只能是『無法評估』」（保底句只在根層未給白話時出現）。評估集尚未凍結時的說明句為「評估集要由人在主機上凍結，巡邏器不會自己建立；凍結前這個提案不會進行驗證」——**不得暗示會自動凍結**（自動凍結屬第二波）。
- **W-F10 入帳結果的結合**：前端以 `auditRef` 對照快照 `ingest[].auditRef`（前端收到的是 backend 轉過的 camelCase；Bridge 層原名 `audit_ref`）；只對 `ingested === false` 的列結合；同一 `auditRef` 有多筆取第一筆；快照缺席或不可用時，面板層級顯示一次「拒收原因量不到：<原因>」，各列維持「待入帳」；`permanent===true`＝需要人處理（並明說目前畫面沒有取消功能）、`false`＝條件解除後會自動入帳、其他＝是否會自動入帳不明。
- **W-F11 角色**：詳情與巡邏狀態對所有可讀 SI 頁的角色（VIEWER 以上）一視同仁、不因角色遮蔽欄位；非 ADMIN 仍零 `console-writes` 請求、零寫入控件；本鍵新增元件不引用任何寫入 hook。
- **W-F12 更新頻率**：新查詢沿用 `SI_QUERY_OPTIONS`（不重試、不留快取、不輪詢網路）；頁首「重新整理」使 `patrol` 查詢一併重抓；詳情對話框關閉即丟棄資料，重開重取；畫面時間每分鐘由 `useMinuteTick` 本地重算（W-F5），不是輪詢。
- **W-F13 「為什麼沒有啟動運轉」與「為什麼沒推進」都屬第一波的「卡在哪」**：快照的 `schedule`（`enabled`、`current{code,text}`、`last_skip{seq,t,code,text,auditRef}`；OFF 時為 null）與 `runs.waiting[]{run,code,text}` 在巡邏卡有專屬區塊（AT-966-12-7）；`last_skip.auditRef` 非 null ＝「你從畫面按的『立即啟動』被略過了」要明說；全部文字取根層的 `text`，Console 不自寫。`runs.live[].purpose` 第一波值域為 `scheduled｜console｜manual`；`runs.queued` 恆空、Console 不渲染也不依賴；快照頂層 `truncated===true` 時顯示「這份回報太長，被截短了，清單可能不完整」。
- **W-F14 根層欄位採用表**（逐欄；不採用者附理由）：`detail.patch`、`body`（採用）；`detail.sourceObs`（採用：在「提案本文」顯示來源觀察摘要，免去逐筆跳轉才看得到內容，也消除「來源不在已載入頁」的降級體驗）；`detail.heldout` 八鍵中除 `digest8` 外七鍵採用（`digest8` 不採用，理由見 W-F9）；`detail.sandbox` 七鍵全採用（含 `failText`）；`detail.verify` 全採用（`carrierProof` 為 bool｜null）；`detail.next` 採用；`detail.timeline` 採用（取代 `GET /api/v1/issues/{id}`：少一個請求、一個失敗面；`kind` 欄不顯示——`action` 已是中文，不採用理由＝重複資訊）；`ne[]` 新碼項的 `text` 採用；快照 `schema_rev`、`generated_at`、`off`、`heartbeat_minutes`、`ledger_seq`、`truncated`、`steps[]`、`schedule`、`ingest[]`、`props[]`、`runs.live[]`、`runs.waiting[]`、`push` 採用；`runs.queued` 不採用（第一波恆空，W2 才有元素，W1 Console 不得依賴）；`push.retry` 不採用（理由：`push.text` 已含「稍後自動重試」「請由人推送」等語意，Console 不另加句子，與 AT-966-5-9 一致）；`push.tick_at` 不採用（理由：`pending` 與 `waiting-login` 的區分已由根層判定並寫進 `push.state`／`push.text`，Console 不自行重判）；`push.sha`、`push.ahead`、`push.attempts`、`push.finished_at` 採用（顯示於推送區的補充資訊）；`ingest[].kind` 不採用（待入帳列已有自己的種類標籤）。

**非功能需求（NFR-FV）**

| NFR | 敘述 | 驗證 AT |
|-----|------|---------|
| NFR-FV-1 | **只讀零副作用**：Bridge 讀快照前後目錄與檔案位元組、mtime 不變、不啟動子行程；backend 巡邏端點零 DB 寫入；前端旅程零非 GET 請求 | AT-966-1-6、AT-966-3-4、AT-966-14-1 |
| NFR-FV-2 | **讀到的永遠是完整檔**：主機以「寫新檔→replace」更新時，Bridge 不會讀到半個檔 | AT-966-1-E-1 |
| NFR-FV-3 | **量不到不顯示成正常或零**：缺檔、壞檔、缺欄、`null`、空陣列各有不同呈現；絕不把「讀不到」畫成「沒有事」 | AT-966-5-E-1、AT-966-11-5、AT-966-12-E-1、AT-966-13-4 |
| NFR-FV-4 | **評估集內容不外洩**：Bridge 只放行契約列出的鍵（主機多帶的鍵丟棄），前端不渲染未知鍵；畫面與 DOM 不含評估集內容 | AT-966-4-6、AT-966-9-2 |
| NFR-FV-5 | **零退步與範圍**：既有 AT 在其角色下仍綠，釘選數字只改預期值（§4.1）；只動 §5.7 允許集合 | AT-966-3-6、AT-966-14-2、V4 |
| NFR-FV-6 | **無障礙**：三寬度（1440／1000／600，取自既有無障礙 E2E 的 `RESEARCH_WIDTHS`，不另立數字）axe 零 serious／critical、無橫向溢出；diff 與狀態的意義不只靠顏色；對話框焦點管理沿 `dialog.tsx` | AT-966-7-2、AT-966-16-2 |
| NFR-FV-7 | **跨平台**（根鐵律三）：新程式與測試不引入平台專屬假設（路徑分隔符、換行、檔案鎖、`os.replace` 需 `try/except OSError`）；Windows 與 Linux（CI）皆須全綠；macOS 未驗 | V6 |
| NFR-FV-8 | **開發 agent 交卷前閘門**（輸出逐字貼入）：(1) 本檔各 AT 逐一單跑；(2) `gradlew clean build`；(3) 前端 lint、`tsc --noEmit`、build、vitest；(4) Bridge `pytest`、`ruff check`（本目錄與 monorepo 根視角各一次）；(5) 讀 rc 先存變數再讀；(6) 不 commit、不碰根層 `tools/`、`.claude/`、凍結檔；(7) 夾具與測試中不得出現不存在於真帳本的編號字面（見 §5.1「給所有實作者的規定」：用真實存在的編號，或在執行期拼出；`si check` 的 `ref.obs` 掃全 repo）；(8) 不得有 `sk-` 形態字串與真機密；(9) 契約與實作不符處以純文字回報；(10) 交卷含流程摩擦節 | SCG-4 實跑檢核 |
| NFR-FV-9 | **hermetic**：AT 不得寫真 SI 家目錄；全棧 E2E 的快照目錄為拋棄式目錄；E2E 寫入的 `patrol.json` 僅在該目錄 | AT-966-17-3 |

**追溯矩陣**：F-911 ← Console PRD §0.12、§8.1；根層 SelfImproving PRD v0.16 的 FR-SI-47～49（detail、巡邏快照、M 類與推送的顯示面）與根層 TCS 的接縫條文；P1b 的唯讀鏡像（R5～R19）、P2b 的對帳面板（W14～W21）、P4 的排程面板與 `SI_QUERY_OPTIONS` 慣例；US-931 → AC-966-1～17（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3；「已凍結上位文件」相對 `spec-frozen --root`＝monorepo 根；**凍結摘要一律由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 重算並與各鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 對照，不符以 `show` 為準**；本表不預填摘要）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定、FRD 覆蓋、利害關係人已簽核 | US-931、AC-966-1～17；授權＝掌舵者 2026-11-11 要求（本輪任務書）；凍結常態規則（根 CLAUDE.md） | docs/01_requirements/Agent_ConsoleUI_PRD.md（§0.12 本增量新增） | 主控凍結前重算 |
| SCG-0／根層 PRD（SI 側契約的唯一定稿處） | SelfImproving PRD v0.16 的 FR-SI-47～49（根層棒；本檔引用不複寫） | docs/01_requirements/SelfImproving_PRD.md | 主控於根層棒完成後重算 |
| SCG-0／NFR 已量化、User Story INVEST、RTM 初版 | NFR-FV-1～9；US-931；本檔 §1 與 §6（RTM 本地子表 §2.16 於 SCG-5 回填） | （本檔；隨 Stage 凍結，非上位文件） | n/a（自引） |
| SCG-1／整合架構、NFR 對應 | Architecture §5.7（本增量新增）、§10.5（新增）、§12.1 L-SI-3（新增）；§5.4 新功能接入檢查表 | AgentConsole/docs/02_architecture/Architecture.md | 主控凍結前重算 |
| SCG-1／技術選型與偏離清單 | ADR-001（Spring Boot 4.1、JDBC adapter 體例）；設計 A 唯讀 bind（Architecture §12.1 L-14、§12.2 V-12） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | 主控重算 |
| SCG-3／前代契約（唯讀鏡像與回應形狀） | `API_Contract_SelfImproving_P1b.md` §0.2（欄名對映）、§1.5（單筆提案）、§2.3（503 cause）；P2b §4（對帳）；P2c | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md；…_P2b.md；…_P2c.md | 主控重算（本鍵不改這些檔） |
| SCG-3／上位 TCS | `TCS-SelfImprovingMirror-P1b-20261021.md`（AT-935 系列、單筆提案端點）；`TCS-SelfImprovingDecide-P2b-20261024.md`（對帳面板 W14～W21）；`TCS-SelfImprovingDecideDedupe-20261031.md`（`items[]` 十一鍵）；`TCS-SelfImprovingSchedule-20261109.md`（SI 頁掛載點、`SI_QUERY_OPTIONS`）；`TCS-ResearchRegistry-20261110.md`（Bridge 路由與 OpenAPI 計數的現值累加） | AgentConsole/docs/03_testing/contracts/ 下同名檔 | 主控重算 |
| SCG-3／根層 TCS（接縫） | 根層 TCS §2.1（`detail` 八欄）、§2.2（`patrol.json`）、附錄 A（原因碼與白話字表）與黃金樣本（`tools/tests/fixtures/selfimproving/p7/patrol.golden.json`、`detail.golden.json`）（本檔引用不複寫） | docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md | 主控凍結前重算（與根層鍵凍結值對照） |

---

## 0.2 介面契約（Console 側唯一定稿處；欄名依根層設計稿 §2，**本檔不自創、不改名**）

**C-1　Bridge `GET /si/patrol`**：無路徑與查詢參數；200 本文 `{"schema_rev":1,"kind":"patrol","read_at":"<ISO+offset>","report":{…}}`（Bridge 層一律 snake_case，與 Bridge 其他回應同慣例）。`read_at` 為 Bridge 讀檔當下的時間（帶 offset）；backend 轉成 `readAt`，前端收到 `readAt`。`report` 為 `patrol.json` 解析後物件，**欄名、型別、可空性、值域一律以根層 TCS-P7 §2.2 為準**（本檔不複寫，只列用到的）：`generated_at`（str，非空）、`off`（bool）、`heartbeat_minutes`（int）、`ledger_seq`（int）、`truncated`（bool）、`steps[]{step,result}`、`schedule`（object｜null；OFF 時 null）＝`{enabled, current:{code,text}｜null, last_skip:{seq,t,code,text,audit_ref}｜null}`、`ingest[]{audit_ref,kind,status∈{rejected,deferred},code,text,permanent}`、`props[]{id,state,code,who,text}`（皆非空 str）、`runs.live[]{run,purpose∈{scheduled,console,manual},started_at,wall_due_at}`、`runs.waiting[]{run,code,text}`、`runs.queued`（W1 恆 `[]`，Console 不依賴）、`push{enabled,state∈{off,idle,pending,waiting-login,running,ok,failed,blocked},code,text,retry,sha,ahead,attempts,finished_at,tick_at}`（`state`／`code`／`text` 恆非空）；**其他鍵一律透傳、前端忽略**。失敗：503 `si_unavailable` 加 `cause`∈{`report_dir_unset`,`report_missing`,`report_unreadable`,`report_invalid`}；422 `invalid_request`（任何查詢參數）。Bridge 的大小上限（1048576）大於根層寫入端的 `REPORT_MAX_BYTES`（524288），兩者各自獨立：根層限制寫、Bridge 限制讀，讀端寬於寫端不會誤拒合法快照。

**C-2　console-api `GET /api/v1/si/patrol`（API-SI-16）**：VIEWER 以上；回應 `ApiResult<SiExportResponse>` 形（無型別樹）；`data` 為 C-1 本文經 `SiKeyNames` 對映後的樹（snake_case→camelCase，其餘恆等：`read_at`→`readAt`、`report.generatedAt`、`heartbeatMinutes`、`ledgerSeq`、`lastSkip`、`auditRef`、`startedAt`、`wallDueAt`、`finishedAt`、`tickAt`、`schemaRev`）。**前端一律以這組 camelCase 鍵讀取**；snake_case 只出現在 Bridge 層與 backend 層的測試。失敗沿 §10.3 的 503 `si_unavailable`（`details.cause` 逐字）、502、504；沒有 `data`。backend 不需改動（`SiKeyNames.camelKeys` 已深層對映整棵樹），只補測試。

**C-3　單筆提案 `GET /api/v1/si/proposals/{id}`（API-SI-05 擴充）**：`data.items[0].detail`（根層 TCS-P7 §2.1；清單端點不含；**八欄全列，採用與否見 W-F14**）：`patch`／`body`＝`{rel,bytes,text,truncated}`｜null；`sourceObs`＝`[{id,context,symptom,severity,disposition}]`，缺列者為 `{id,missing:true}`（**正式契約句：缺列形態只有 `id` 與 `missing` 兩鍵，`filter_detail` 的 `sourceObs[]` 白名單＝`id`、`context`、`symptom`、`severity`、`disposition`、`missing`**）；`heldout`＝`{frozen,seq,n,min,belowMin,frozenBy,digest8,neNote}`（`digest8` 不顯示）；`sandbox`＝`{seq,id,applied,touchedOk,rollbackOk,failCode,failText}`｜null；`verify`＝`{seq,id,verdict,baselineRed,patchedGreen,mutatedRed,probesN,carrierProof,reasons:[{code,text}]}`｜null（`baselineRed`、`patchedGreen`、`mutatedRed`、`carrierProof` 為 bool｜null）；`next`＝`{code,who,text}`（`who`∈{掌舵者,巡邏器,無人運轉,主機管理者,無}）；`timeline`＝`[{seq,t,by,kind,action}]`（升冪，至多最後 500 筆）。`ne[]` 既有形狀 `{field,reason}` 不變，根層新碼項（`PATCH-UNREADABLE`、`BODY-UNREADABLE`、`OBS-LEDGER-UNREADABLE`、`HELDOUT-MIN-UNKNOWN`、`TIMELINE-TRUNCATED`）多一鍵 `text`（白話）。根層以 camelCase 輸出 `detail` 內鍵；若某鍵以 snake_case 到達，backend 的 `SiKeyNames` 轉成同一組 camelCase（AT-966-4-3 兩種輸入各驗）。

**C-4　時間線與來源觀察**：兩者皆取自 C-3 的 `detail.timeline`、`detail.sourceObs`（根層 TCS-P7 §2.1 註明時間線不必再打議題端點）；本鍵**不呼叫** `GET /api/v1/issues/{id}`，也不改該端點。

**C-5　Console 持有的常數與表**（全部只住 `lib/domain/siFlow.ts`，不複製到元件）：`STALE_FACTOR=2`、`STALE_GRACE_MINUTES=5`、`DIFF_WINDOW_LINES=400`、`RECENT_INGESTED_SHOWN=5`；列舉標籤只有 W-F7 列的三組（運轉目的第一波三值、驗證結果三值、入帳狀態兩值）；等待對象五值只驗屬於該集合；推送狀態八值只用來決定樣式與是否已知，**不建標籤表**（顯示的句子是 `push.text`）；保底句模板（W-F7）。

**C-6　Bridge 常數**：`PATROL_REPORT_MAX_BYTES=1048576`（`app/si_report.py` 唯一定義處）；固定檔名 `patrol.json`；環境變數 `BRIDGE_SI_REPORT_DIR`（compose 設 `/si-report`）。

---

## 1. AC → AT 映射表

> 每個 AC 對應至少一個可自動化 AT；AT ID 前兩段數字＝所屬 AC。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-966-1 | Bridge 巡邏快照讀取 | AT-966-1-1 | 成功回應形狀、逐值透傳與黃金樣本 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-2 | 目錄未設／缺檔／不可讀三種原因碼 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-3 | 壞檔十三子情境皆 report_invalid | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-4 | 大小邊界 1048576／1048577 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-5 | 任何查詢參數 422 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-6 | 零寫入、零子行程、目錄不變 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-7 | 路徑含於目錄（逃逸判準純函式） | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-8 | 唯讀鎖普查與路由數 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-E-1 | 寫入端 replace 交替時讀端永遠讀到完整檔 | ✅ | Unit | □ |
| AC-966-1 | | AT-966-1-E-2 | 殘留 `.tmp` 與其他檔名不被讀 | ✅ | Unit | □ |
| AC-966-2 | 部署 | AT-966-2-1 | compose 唯讀 bind 與環境變數齊備 | ✅ | Unit | □ |
| AC-966-2 | | AT-966-2-2 | Settings 解析與錨定守衛 | ✅ | Unit | □ |
| AC-966-2 | | AT-966-2-3 | 檢查器突變變體全被指出 | ✅ | Unit | □ |
| AC-966-2 | | AT-966-2-4 | `.env.example`、docker README、Architecture §9.4 文字 | ✅ | Unit | □ |
| AC-966-2 | | AT-966-2-5 | 未設環境變數只影響 `/si/patrol` | ✅ | Unit | □ |
| AC-966-2 | | AT-966-2-E-1 | `docker compose config` 展開結果 | ✅ | Integration | □ |
| AC-966-3 | backend 巡邏端點 | AT-966-3-1 | 角色矩陣與非 GET 方法 | ✅ | Integration | □ |
| AC-966-3 | | AT-966-3-2 | 欄名深層對映 | ✅ | Integration | □ |
| AC-966-3 | | AT-966-3-3 | Bridge 錯誤逐字透傳與 502／504 | ✅ | Integration | □ |
| AC-966-3 | | AT-966-3-4 | 恰一次 Bridge 呼叫、零 DB 寫入 | ✅ | Integration | □ |
| AC-966-3 | | AT-966-3-5 | OpenAPI 條目與計數 | ✅ | Integration | □ |
| AC-966-3 | | AT-966-3-6 | ArchUnit 結構鎖計數 | ✅ | Unit | □ |
| AC-966-3 | | AT-966-3-E-1 | 未知鍵、非 ASCII、1 MiB 本文與腳本字樣原樣 | ✅ | Integration | □ |
| AC-966-4 | 詳情透傳 | AT-966-4-1 | Bridge：detail 位元組級透傳 | ✅ | Unit | □ |
| AC-966-4 | | AT-966-4-2 | Bridge：清單不含 detail、argv 不變 | ✅ | Unit | □ |
| AC-966-4 | | AT-966-4-3 | backend：兩種欄名風格對映與未知鍵透傳 | ✅ | Integration | □ |
| AC-966-4 | | AT-966-4-4 | backend：null 與缺席區分 | ✅ | Integration | □ |
| AC-966-4 | | AT-966-4-5 | backend：256 KiB patch 往返 | ✅ | Integration | □ |
| AC-966-4 | | AT-966-4-6 | Bridge：detail 只放行契約列出的鍵 | ✅ | Unit | □ |
| AC-966-4 | | AT-966-4-E-1 | Bridge：256 KiB patch 加本文仍在 8 MiB 上限內；404／422／503 不變 | ✅ | Unit | □ |
| AC-966-5 | 前端純函式 | AT-966-5-1 | 新鮮度邊界表 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-2 | 下一步來源序 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-3 | 列舉已知判定與未知值、第二波值保底 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-4 | 原因保底句與憑證遮罩 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-5 | diff 解析與計數 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-6 | diff 視窗與下載描述 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-7 | 入帳結果結合 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-8 | 評估集與驗證檢視模型 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-9 | 推送、排程、等待檢視模型與相對時間 | ✅ | Unit | □ |
| AC-966-5 | | AT-966-5-E-1 | 缺席、null、空陣列三者區分 | ✅ | Unit | □ |
| AC-966-6 | 詳情對話框骨架 | AT-966-6-1 | 每列「詳情」鈕、開關與焦點歸還 | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-2 | 五分頁順序與鍵盤 | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-3 | 懶取數與請求次數（不打議題端點） | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-4 | 載入、503、404 三態 | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-5 | 「下一步」三種來源 | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-6 | 過時快照加巡邏器警示行 | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-7 | 純文字渲染與靜態無 innerHTML | ✅ | Unit | □ |
| AC-966-6 | | AT-966-6-E-1 | 舊根層無 `detail`、卡面為 null | ✅ | Unit | □ |
| AC-966-7 | diff 分頁 | AT-966-7-1 | 逐行原文、種類與計數句 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-2 | 顏色以外的標示 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-3 | 截斷提示與下載 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-4 | 400 行視窗與展開 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-5 | patch 為 null、空字串 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-E-1 | 256 KiB 夾具視窗化 | ✅ | Unit | □ |
| AC-966-7 | | AT-966-7-E-2 | 單行超長 | ✅ | Unit | □ |
| AC-966-8 | 本文與來源觀察 | AT-966-8-1 | 提案本文純文字與截斷 | ✅ | Unit | □ |
| AC-966-8 | | AT-966-8-2 | 本文為 null | ✅ | Unit | □ |
| AC-966-8 | | AT-966-8-3 | 來源觀察跳轉與高亮 | ✅ | Unit | □ |
| AC-966-8 | | AT-966-8-4 | 跳轉目標不在已載入頁、非 OBS 來源、無來源 | ✅ | Unit | □ |
| AC-966-8 | | AT-966-8-5 | 來源觀察摘要與缺列 | ✅ | Unit | □ |
| AC-966-8 | | AT-966-8-E-1 | 大量與重複來源 | ✅ | Unit | □ |
| AC-966-9 | 評估集、沙盒、驗證 | AT-966-9-1 | 評估集四種狀態與 neNote 提示 | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-2 | 評估集內容不外洩（金絲雀） | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-3 | 隔離試跑（沙盒）結果與 failText | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-4 | 驗證三步證據與結果 | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-5 | 原因清單與保底 | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-6 | 缺席的三種情形 | ✅ | Unit | □ |
| AC-966-9 | | AT-966-9-E-1 | 未知驗證結果 | ✅ | Unit | □ |
| AC-966-10 | 時間線 | AT-966-10-1 | 時間線取自 detail、依 seq 升冪 | ✅ | Unit | □ |
| AC-966-10 | | AT-966-10-2 | 空與缺席 | ✅ | Unit | □ |
| AC-966-10 | | AT-966-10-3 | 時間線被截短的說明 | ✅ | Unit | □ |
| AC-966-10 | | AT-966-10-E-1 | 無法解析的時間與重複 seq | ✅ | Unit | □ |
| AC-966-11 | 巡邏狀態卡：新鮮度與缺席 | AT-966-11-1 | 掛載位置、角色、請求次數 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-2 | 新鮮呈現 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-3 | 過時警示邊界 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-4 | 環境變數暫停 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-5 | 快照缺席畫面 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-6 | 未掛載畫面 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-7 | 壞檔與其他失敗 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-E-1 | 缺週期與時鐘異常 | ✅ | Unit | □ |
| AC-966-11 | | AT-966-11-E-2 | 惡意字串純文字 | ✅ | Unit | □ |
| AC-966-12 | 巡邏狀態卡：內容與推送 | AT-966-12-1 | 提案卡住原因清單 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-2 | 未知等待對象與未知碼保底 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-3 | 進行中運轉與第二波值不當成已知 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-4 | 步驟與入帳摘要 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-5 | 推送八態與未知態 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-6 | 無推送按鈕與憑證遮罩 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-7 | 為什麼沒有啟動運轉：排程狀態與等待中的運轉 | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-E-1 | 段落缺席＝量不到與 truncated | ✅ | Unit | □ |
| AC-966-12 | | AT-966-12-E-2 | 兩百個提案的捲動區 | ✅ | Unit | □ |
| AC-966-13 | 待入帳面板入帳結果 | AT-966-13-1 | 永久拒收 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-2 | 暫時延後、重複送出與不明 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-3 | 無對應項與快照過時 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-4 | 回報量不到的四種原因 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-5 | 最近已入帳 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-6 | 只結合未入帳列 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-E-1 | 重複稽核編號與缺原因碼 | ✅ | Unit | □ |
| AC-966-13 | | AT-966-13-E-2 | 對帳量不到與既有行為回歸 | ✅ | Unit | □ |
| AC-966-14 | 角色與零寫入 | AT-966-14-1 | VIEWER 與 OPERATOR 完整旅程 | ✅ | Unit | □ |
| AC-966-14 | | AT-966-14-2 | ADMIN 既有流程回歸 | ✅ | Unit | □ |
| AC-966-14 | | AT-966-14-3 | 新元件靜態無寫入引用 | ✅ | Unit | □ |
| AC-966-14 | | AT-966-14-E-1 | 角色一視同仁與 401 | ✅ | Unit | □ |
| AC-966-15 | 文案與說明 | AT-966-15-1 | 四段說明與三道雙向鎖 | ✅ | Unit | □ |
| AC-966-15 | | AT-966-15-2 | 新字串可讀性鎖 | ✅ | Unit | □ |
| AC-966-15 | | AT-966-15-E-1 | 垃圾輸入不洩漏技術字樣 | ✅ | Unit | □ |
| AC-966-16 | mock E2E 與無障礙 | AT-966-16-1 | 旅程與無主控台錯誤 | ✅ | E2E | □ |
| AC-966-16 | | AT-966-16-2 | 三寬度（同源常數）axe 與溢出 | ✅ | E2E | □ |
| AC-966-16 | | AT-966-16-3 | 對話框鍵盤與焦點 | ✅ | E2E | □ |
| AC-966-16 | | AT-966-16-E-1 | 超大 patch 全部展開 | ✅ | E2E | □ |
| AC-966-17 | 全棧 E2E | AT-966-17-1 | 新鮮、過時、缺席三畫面 | ✅ | E2E | □ |
| AC-966-17 | | AT-966-17-2 | 真提案詳情冒煙檢查 | ✅ | E2E | □ |
| AC-966-17 | | AT-966-17-3 | hermetic 掛載斷言 | ✅ | E2E | □ |
| AC-966-17 | | AT-966-17-E-1 | 未掛載部署的畫面 | ✅ | E2E | □ |

**覆蓋率統計**：總 AC 數 17；已映射 AT 數 113；映射覆蓋率 100%。

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的「判定」行給判定指令；每個 AT 的最後一行「驗收字樣」帶一個以方括號包住的字樣（形態：`AT_OK_` 接 AT 底線形去掉 `AT_` 前綴的部分；E 類的 `E` 保留）。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-966-6-3` 的底線形是 `AT_966_6_3`）；每個 AT 的測試函式（Java 為方法、pytest 為函式、vitest 為 `it` 名稱、Playwright 為 `test` 名稱）須含其底線形。**同一 AT 的子情境**一律以參數化或 `subTest`／`it.each`／`@ParameterizedTest` 實作並保留底線形，任一子情境失敗時失敗訊息須指出是哪一個。**不得新增 skip 或 `it.skip`／`describe.skip`／`test.skip`／`@Disabled`**：Docker 缺席視為環境壞、直接失敗。AT 內不引用其他 AT 的 ID。
>
> **判定指令的四種形態**（PowerShell 不用裸 `cd`，用 `Push-Location … Pop-Location` 同行成對，讀 rc 先存變數再讀）：backend `gradlew test --tests "<類別全名>.<AT 底線形>*"`（cwd＝`AgentConsole/backend`；整合測試需 Docker）；Bridge `python -m pytest <檔> -k <AT 底線形> -q`（cwd＝`AgentConsole/engine-bridge`，根層 `.venv`）；frontend `npx vitest run <檔> -t <AT 底線形>`（cwd＝`AgentConsole/frontend`）；Playwright `npx playwright test <檔> -g <AT 底線形>`（cwd＝`AgentConsole/frontend`；mock 情境 `E2E_MODE=standalone`、先 `npm run build`，真棧 `E2E_STACK=1` 並帶 `E2E_ADMIN_*` 與拋棄式棧的環境變數）。
>
> **斷言簡寫**（資料與設施細節見 §5）：**Bridge**：`LB`（本機 Bridge 測試夾具，沿 `test_si_routes.py`）、`RD`（暫存的快照目錄，設為 `BRIDGE_SI_REPORT_DIR`）、`PR(over)`（C-1 的 `report` 夾具，逐鍵覆寫；基準＝§5.1）、`FAKE_CLI`（`tests/fake_si.py` 替身 export 行程）；**backend**：`ADMIN`／`OPERATOR`／`VIEWER`（沿 `AbstractApiIT` 帳號）、`MINI`（迷你 Bridge；本鍵加 `MINI.patrol(status, body)` 設定 `GET /si/patrol` 的回應、`MINI.proposalDetail(id, item)` 設定 `GET /si/proposals/{id}`、`MINI.requests()` 記錄收到的請求）、`rows()`（`si_console_writes` 逐列）；**frontend**：`renderSi`、`stubSiApi`、`ADMIN_UI`／`VIEWER_UI`／`OPERATOR_UI`（沿 `tests/helpers/si.tsx`；本鍵加 `patrol` 端點與 `proposalDetail`、`issue` 路由）、`NOW`＝`2026-11-11T14:00:00+08:00`（固定 `readAt`）、`PATROL(over)`（C-2 的 `data` 夾具，基準＝§5.1）、`DETAIL(over)`（C-3 的 `detail` 夾具）、`P901`＝提案 `PROP-SI-901`（狀態 `verified`、rev 2、`lastSeq` 120、`sources:["OBS-SI-<901>"]`）。

**A. Bridge（pytest；`tests/test_si_patrol_route.py`、`tests/test_si_deploy_config.py`、`tests/test_si_proposal_detail.py`、`tests/test_si_readonly_lock.py`）**

- **AT-966-1-1**（pytest｜`test_si_patrol_route.py`｜Unit｜AC-966-1、W-F1）成功回應形狀與逐值透傳。
  - Given `RD` 內有 `patrol.json`（內容＝`PR()` 以 `json.dumps(ensure_ascii=False)` 寫出，含中文與鍵序 `generated_at` 在 `schema_rev` 之後）；`BRIDGE_SI_REPORT_DIR=RD`
  - When `GET /si/patrol`
  - Then 200；本文頂層鍵恰 `schema_rev`、`kind`、`read_at`、`report`（鍵序同此）；`schema_rev` 為整數 1、`kind` 為 `"patrol"`；`read_at` 可被 `datetime.fromisoformat` 解析且帶 offset；`report` 逐值等於檔案解析結果且**鍵序同檔**（比對 `list(report.keys())`）；中文字串未被跳脫（回應原始位元組含該 UTF-8 序列、不含 `\u`）；`Content-Type` 為 `application/json`；**參數化第二列＝黃金樣本複本** `tests/fixtures/si_report/patrol.golden.json`：測試先斷言該複本的位元組逐位元組等於根層檔 `tools/tests/fixtures/selfimproving/p7/patrol.golden.json`（以 repo 根相對路徑讀取；不等即紅），再以同一組斷言驗回應
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_1 -q`；預期突變：改鍵序、把 `read_at` 換成不帶 offset、寫成 `readAt`、`ensure_ascii` 改 true、丟掉未知鍵，皆紅
  - 驗收字樣：[AT_OK_966_1_1]
- **AT-966-1-2**（pytest｜同檔｜Unit｜AC-966-1、W-F1）目錄未設、缺檔、不可讀三種原因碼。
  - Given 三種設定：(a) 不設 `BRIDGE_SI_REPORT_DIR`；(b) 目錄存在但無 `patrol.json`；(c) `patrol.json` 是一個**目錄**（跨平台可造的不可讀）
  - When 各自 `GET /si/patrol`
  - Then 一律 503，本文 `{"code":503,"reason":"si_unavailable","cause":<c>,…}`，`cause` 依序為 `report_dir_unset`、`report_missing`、`report_unreadable`；(a) 時以監視替身證明**零檔案系統存取**（`open`／`os.stat` 次數為 0）；三者皆沒有 `report` 鍵
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_2 -q`；預期突變：缺檔誤回 `report_invalid`、未設時仍去讀預設路徑、不可讀誤回 `report_missing`，皆紅
  - 驗收字樣：[AT_OK_966_1_2]
- **AT-966-1-3**（pytest｜同檔｜Unit｜AC-966-1、W-F1）壞檔十三個子情境皆 `report_invalid`。
  - Given 逐一寫入：空檔、非 JSON 文字、JSON 陣列、JSON 純量 `1`、UTF-8 BOM 開頭的合法 JSON、非 UTF-8 位元組（`b"\xff\xfe{}"`）、`{}`、`schema_rev` 為 2、為字串 `"1"`、為布林 `true`、缺 `generated_at`、`generated_at` 為 `"2026-11-11T14:00:00"`（無 offset）、`generated_at` 為 `"not a date"`
  - When 各自 `GET /si/patrol`
  - Then 一律 503 `si_unavailable`、`cause=report_invalid`，失敗訊息指出是哪一個子情境；**不**回傳部分內容；對照組：`schema_rev:1`＋合法 `generated_at`＋其餘鍵缺席（`{"schema_rev":1,"generated_at":"2026-11-11T14:00:00+08:00"}`）回 200（Bridge 不要求其他鍵）
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_3 -q`；預期突變：放行 BOM、把布林當整數 1、不驗 offset，皆紅
  - 驗收字樣：[AT_OK_966_1_3]
- **AT-966-1-4**（pytest｜同檔｜Unit｜AC-966-1、W-F1、C-6）大小邊界。
  - Given 兩份合法 JSON 檔，位元組數恰為 `PATROL_REPORT_MAX_BYTES`（1048576）與其加 1（以長字串欄位填充）；以監視替身記錄讀取量
  - When 各自 `GET /si/patrol`
  - Then 前者 200；後者 503 `report_invalid`；任一情況實際讀入位元組數不超過 `PATROL_REPORT_MAX_BYTES + 1`；測試以 `from app.si_report import PATROL_REPORT_MAX_BYTES` 取常數並斷言其值為 1048576（常數唯一定義處）
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_4 -q`；預期突變：上限改 1048577、改成讀完全檔才判，皆紅
  - 驗收字樣：[AT_OK_966_1_4]
- **AT-966-1-5**（pytest｜同檔｜Unit｜AC-966-1、W-F1）任何查詢參數 422。
  - Given 合法快照
  - When `GET /si/patrol?x=1`、`?since=1`、`?limit=1`、`?read_at=x`
  - Then 一律 422 `invalid_request`，`violations[]` 每個未知參數一筆 `{field,rule:"unknown_parameter",message}`；零檔案系統存取
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_5 -q`；預期突變：忽略未知參數，紅
  - 驗收字樣：[AT_OK_966_1_5]
- **AT-966-1-6**（pytest｜同檔｜Unit｜AC-966-1、NFR-FV-1）零寫入、零子行程、目錄不變。
  - Given `RD` 內有 `patrol.json` 與一個無關檔；監視 `subprocess.Popen`、`os.open`（寫旗標）、`open`（寫模式）；記錄目錄清單、兩檔位元組 sha256 與 mtime
  - When 連續 `GET /si/patrol` 二十次
  - Then `Popen` 呼叫 0 次、任何寫旗標開檔 0 次；目錄清單、位元組與 mtime 全不變；二十次回應的 `report` 皆相同
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_6 -q`；預期突變：讀取時順手 `touch`、讀取時啟動 `si_cli`，皆紅
  - 驗收字樣：[AT_OK_966_1_6]
- **AT-966-1-7**（pytest｜同檔｜Unit｜AC-966-1、W-F1）路徑含於目錄（逃逸判準純函式 `resolve_report_path(report_dir, resolver)`）。
  - Given 注入的假解析器，回傳：目錄內的 `patrol.json`、目錄外的路徑（符號連結逃逸）、目錄本身、含 `..` 的路徑
  - When 呼叫判準
  - Then 只有第一個通過；其餘回報問題（路由層轉成 503 `report_invalid`）；Windows 路徑大小寫與分隔符以 `os.path.normcase` 比對（以假解析器餵大小寫不同的同一路徑，仍通過）
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_7 -q`；預期突變：只比字串前綴（`/si-report-evil` 誤判含於 `/si-report`），紅
  - 驗收字樣：[AT_OK_966_1_7]
- **AT-966-1-8**（pytest｜`test_si_readonly_lock.py`｜Unit｜AC-966-1、NFR-FV-5）唯讀鎖普查納入新模組與新路由。
  - Given 現行五判準與路由普查（`test_AT_964_8_4…` 的 `routes` 計數）
  - When 重跑
  - Then `app/si_report.py` 與 `app/si_detail.py` 皆被普查為 SI 相關模組且五判準（寫入形態只在 `si_audit`、禁用 import、單一 script 字面、argv 白名單、動態 argv）全數通過；`si_cli.py` 的 argv 白名單與 `export`／`obs-add --dry-run` 兩形態**逐字不變**；路由數等於修改前現值加一，每條路由恰一個方法；`GET /si/patrol` 對應的處理函式不呼叫 `si_cli`
  - 判定：`python -m pytest tests/test_si_readonly_lock.py -k "AT_933_1_6 or AT_964_8_4 or AT_966_1_8" -q`；預期突變：讓 `si_report.py` 以寫模式開檔、讓 `si_detail.py` 開檔或呼叫子行程（它必須是純函式）、讓路由處理函式呼叫 `run_export`，皆紅
  - 驗收字樣：[AT_OK_966_1_8]
- **AT-966-1-E-1**（pytest｜`test_si_patrol_route.py`｜Unit｜AC-966-1、NFR-FV-2）寫入端 replace 交替時，讀端永遠讀到完整檔。
  - Given 兩份合法快照 X、Y（`generated_at` 不同）；寫入執行緒以「寫 `patrol.json.tmp`→（`try/except OSError`，Windows 被占用時重試）`os.replace`」交替 X、Y 三百次；讀端同時 `GET /si/patrol` 三百次
  - When 兩者並行
  - Then 每個讀端回應皆 200 且 `report` 等於 X 或 Y 之一（逐值）；**零個** 503；寫入端遇 `OSError` 的重試次數記錄於測試輸出（不影響判定）
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_E_1 -q`；預期突變：讀端改成先判存在再開檔（TOCTOU）、讀端改讀 `.tmp`，皆至少偶發紅（測試迴圈次數足以穩定重現）
  - 驗收字樣：[AT_OK_966_1_E_1]
- **AT-966-1-E-2**（pytest｜同檔｜Unit｜AC-966-1、W-F1）殘留 `.tmp` 與其他檔名不被讀。
  - Given `RD` 內只有 `patrol.json.tmp`（內容合法）與 `patrol.json.bak`
  - When `GET /si/patrol`
  - Then 503 `report_missing`；再放入合法 `patrol.json` 後 200 且 `report` 等於 `patrol.json` 的內容（不是 `.tmp` 的）
  - 判定：`python -m pytest tests/test_si_patrol_route.py -k AT_966_1_E_2 -q`；預期突變：以 glob `patrol*` 取最新檔，紅
  - 驗收字樣：[AT_OK_966_1_E_2]
- **AT-966-2-1**（pytest｜`test_si_deploy_config.py`｜Unit｜AC-966-2、W-F2）compose 唯讀 bind 與環境變數齊備。
  - Given 現行 `AgentConsole/docker-compose.yml` 以 YAML 解析
  - When 新函式 `report_bind_problems(compose)` 檢查 engine-bridge
  - Then 無問題：環境變數 `BRIDGE_SI_REPORT_DIR` 等於 `/si-report` 且不在 `/repo` 之下、不等於 `BRIDGE_SI_AUDIT_DIR`；恰一條 target 為 `/si-report` 的 volume，長語法、`type: bind`、`read_only: true`、`bind.create_host_path: false`、`source` 以 `console_report` 結尾、不符合寫死磁碟路徑正規式（沿檔內 `HARD_CODED_DISK`）、且與稽核 bind 的 `source` 使用同一個 `${AUTOSDD_SI_DIR:-…}` 前綴運算式；`audit_bind_problems` 仍為空（engine-bridge 唯一可寫 bind 仍是稽核目錄）；`si_mount_problems` 仍為空（既有六條 `/repo` 唯讀 bind 與設計 A 逐條不變）
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_1 -q`；預期突變：見 AT-966-2-3
  - 驗收字樣：[AT_OK_966_2_1]
- **AT-966-2-2**（pytest｜同檔｜Unit｜AC-966-2）Settings 解析與錨定守衛。
  - Given 環境字典：未設／`/si-report`／`relative/path`／`/`／與 `BRIDGE_SI_AUDIT_DIR` 相同／空白字串
  - When `load_settings`
  - Then 未設與空白＝`si_report_dir is None`；`/si-report`＝該 `Path`；**相對路徑（`Path(raw).anchor` 為空字串）拋 `SettingsError`**——新變數刻意比 `BRIDGE_SI_AUDIT_DIR` 嚴（後者既有行為是 resolve 成絕對路徑、不拋，本鍵**不改它**）：compose 一律給絕對路徑 `/si-report`，相對路徑必是部署寫錯，應在啟動時第一時間看出來；Windows 的 `/si-report`（有根無磁碟代號）anchor 非空，仍合法；`/`（檔案系統根）沿 `_anchor_guard` 既有規則拋 `SettingsError`；與稽核目錄相同拋 `SettingsError`（兩個目錄不得是同一個）；既有 `si_audit_dir` 與 `si_write_enabled` 行為不變
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_2 -q`；預期突變：允許兩目錄相同、相對路徑被悄悄 resolve（不拋）、不走錨定守衛，皆紅
  - 驗收字樣：[AT_OK_966_2_2]
- **AT-966-2-3**（pytest｜同檔｜Unit｜AC-966-2）檢查器突變變體全被指出。
  - Given 以真 compose 深複製後各改一處的九個變體：`report-writable`（`read_only` 拿掉）、`create-host-path-true`、`short-syntax`、`under-repo`（target 改 `/repo/si-report`）、`missing-env`、`wrong-source-suffix`（改 `console_audit`）、`hard-coded-disk`、`same-as-audit`（source 與稽核相同）、`second-writable-bind`
  - When 各自過 `report_bind_problems`
  - Then 每個變體都至少回報一個問題且訊息含對應關鍵字；變體個數 `len(variants)==9`；真 compose 回報 0 個
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_3 -q`；預期突變：檢查器漏判任一變體，紅
  - 驗收字樣：[AT_OK_966_2_3]
- **AT-966-2-4**（pytest｜同檔｜Unit｜AC-966-2）文件文字。
  - Given `AgentConsole/.env.example`、`AgentConsole/docker/README.md`、`AgentConsole/docs/02_architecture/Architecture.md` §9.4 環境變數表
  - When 讀文字
  - Then `.env.example` 有一段說明 `console_report` 目錄須在 `docker compose up` 前存在（雙 shell 預建指令各一條：PowerShell 的 `New-Item -ItemType Directory -Force` 與 POSIX 的 `mkdir -p`，皆使用 `AUTOSDD_SI_DIR` 預設運算式的展開寫法、不寫死磁碟路徑）且**只含 `<YOUR_...>` 佔位符、無真機密**；README 有〈巡邏回報目錄〉小節，內含 §6.2 V1 的升級序列：「建目錄→重建 engine-bridge、backend、frontend 三個映像→啟動→驗證（`/api/v1/si/patrol` 先回 503 `report_missing`、第一個心跳後有快照）」四步的指令各一條且**依此順序出現**、「失敗表徵」一段（含目錄未建時 compose 拒絕啟動的訊息、漏重建某映像的症狀）、「退回」一段，並說明未掛載時的畫面；Architecture §9.4 表含 `BRIDGE_SI_REPORT_DIR` 一列；三處皆不含「第二條可寫 bind」字樣
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_4 -q`；預期突變：刪掉任一段，紅
  - 驗收字樣：[AT_OK_966_2_4]
- **AT-966-2-5**（pytest｜同檔｜Unit｜AC-966-2、W-F1）未設環境變數只影響 `/si/patrol`。
  - Given Bridge 以舊部署設定（無 `BRIDGE_SI_REPORT_DIR`）啟動，`FAKE_CLI` 就緒
  - When 依序 `GET /si/status`、`/si/proposals`、`/health`、`/health/deep`、`/si/patrol`
  - Then 前四者行為與修改前相同（200）；`/si/patrol` 為 503 `report_dir_unset`；`/health/deep` 的項目集合不增不減（SI 巡邏回報目錄不進深度探針）
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_5 -q`；預期突變：深度探針加一項、缺目錄時 Bridge 啟動失敗，皆紅
  - 驗收字樣：[AT_OK_966_2_5]
- **AT-966-2-E-1**（pytest｜同檔｜Integration｜AC-966-2、NFR-FV-7）`docker compose config` 展開結果。
  - Given 暫存目錄 T；環境 `AUTOSDD_SI_DIR=T`（POSIX 與 Windows 皆以該變數，不依賴 `HOME`／`USERPROFILE`）；其餘必填變數以測試哨兵值補齊（沿 `test_si_deploy_config.py` 既有 `docker compose config` 案例的做法）
  - When 執行 `docker compose -f AgentConsole/docker-compose.yml config --format json`（讀 rc 先存變數）
  - Then rc 0；engine-bridge 的 `/si-report` volume 展開為 `type=bind`、`read_only=true`、`source` 等於 `T/console_report`（正規化比對）、`bind.create_host_path=false`；`/si-audit` volume 仍 `read_only=false` 且來源 `T/console_audit`
  - 判定：`python -m pytest tests/test_si_deploy_config.py -k AT_966_2_E_1 -q`；預期突變：來源忘了接 `AUTOSDD_SI_DIR`（展開為家目錄預設），紅
  - 驗收字樣：[AT_OK_966_2_E_1]
- **AT-966-4-1**（pytest｜`test_si_proposal_detail.py`｜Unit｜AC-966-4、W-F4）Bridge 對 `detail` 位元組級透傳。
  - Given `FAKE_CLI` 對 `export --kind proposals --id PROP-SI-901` 輸出一個物件，`items[0].detail` 取 `DETAIL(full)`（C-3 八欄俱全，含 `sourceObs`、`timeline`、`heldout` 八鍵、`sandbox.failText`；`patch.text` 含 `\r\n`、Tab、U+2028、emoji、中文、一行字面 `+++ b/x`、結尾無換行；`reasons[].text` 含中文）
  - When `GET /si/proposals/PROP-SI-901`
  - Then 200；`items[0].detail` 逐值等於 `FAKE_CLI` 輸出（`==` 比對解析後物件，另比 `patch.text` 的 UTF-8 位元組）；鍵序與 `FAKE_CLI` 輸出一致；`items` 恰一筆；其餘頂層鍵（`schema_rev`、`kind`、`generated_at`、`head_sha`、`next_since`、`truncated`、`ne`、`problems`）不增不減；`ne[]` 含根層新碼項（`PATCH-UNREADABLE` 等，帶 `text` 鍵）時逐項原樣；**參數化第二列＝黃金樣本複本** `detail.golden.json`（**其內容是整個 `items[0]`**，`FAKE_CLI` 以它整個作為 `items[0]` 輸出；先斷言複本位元組等於根層 `tools/tests/fixtures/selfimproving/p7/detail.golden.json`）
  - 判定：`python -m pytest tests/test_si_proposal_detail.py -k AT_966_4_1 -q`；預期突變：Bridge 對 `detail` 做 `strip()`、重新編碼或刪鍵，紅
  - 驗收字樣：[AT_OK_966_4_1]
- **AT-966-4-2**（pytest｜同檔｜Unit｜AC-966-4、W-F4）清單端點不含 `detail`、argv 不變。
  - Given `FAKE_CLI` 記錄收到的 argv；清單輸出不含 `detail`
  - When `GET /si/proposals?limit=5` 與 `GET /si/proposals/PROP-SI-901`
  - Then 清單項目鍵集合不含 `detail`；單筆 argv 恰為 `export --kind proposals --id PROP-SI-901 --json`（與修改前逐字相同；沿 `si_cli.build_argv` 現行形態）；`si_cli.py` 的 argv 白名單常數與修改前相同
  - 判定：`python -m pytest tests/test_si_proposal_detail.py -k AT_966_4_2 -q`；預期突變：Bridge 自行加 `--detail` 旗標，紅
  - 驗收字樣：[AT_OK_966_4_2]
- **AT-966-4-6**（pytest｜`test_si_proposal_detail.py`｜Unit｜AC-966-4、W-F4、NFR-FV-4）Bridge 對 `detail` 只放行契約列出的鍵。
  - Given `FAKE_CLI` 對單筆提案輸出的 `items[0]` 內，`detail` 多帶合成的未列鍵與形狀不符者（`heldout.n` 為物件、`verify.reasons` 內夾一個字串元素、snake_case 的 `touched_ok`）：`detail.evalset:"CANARY-TOP"`、`detail.heldout.cases:["CANARY-CASE"]`、`heldout.probes`、`heldout.files`、`patch.raw:"CANARY-RAW"`、`sandbox.log`、`verify.secret`、`verify.reasons[0].trace`、`sourceObs[0].internal`、`timeline[0].pid`；另備 `detail` 為字串、為陣列、為 null 三份；以及只含契約鍵的黃金樣本複本（整個 `items[0]`，非只 `detail`）
  - When `GET /si/proposals/PROP-SI-901`
  - Then 形狀不符者與 snake_case 鍵被丟棄（回應中不存在）；多帶的鍵**在回應任何位置都不存在**（回應原始文字不含任何 `CANARY`）；契約列出的鍵與值逐值不變且鍵序保留（`heldout` 八鍵含 `digest8`、`neNote`）；`detail` 為字串、陣列、null 時回應的 `items[0]` 沒有 `detail` 鍵；黃金樣本列與未過濾時逐位元組相同（白名單不誤傷契約鍵）；`items[0]` 的其他鍵（`id`、`state`、`card` 等）、`ne`、`problems` 不受影響
  - 判定：`python -m pytest tests/test_si_proposal_detail.py -k AT_966_4_6 -q`；預期突變：拿掉白名單（直接透傳）即紅（哨兵出現）；白名單漏列 `neNote`、`digest8`、`kind`，或漏列 `sourceObs` 缺列形態的 `missing` 鍵（`{id,missing:true}` 被削成 `{id}`），亦紅；Given 另含一份 `sourceObs:[{id:"OBS-SI-<902>",missing:true}]` 並斷言原樣保留
  - 驗收字樣：[AT_OK_966_4_6]
- **AT-966-4-E-1**（pytest｜同檔｜Unit｜AC-966-4）上限內的大 patch 與錯誤路徑不變。
  - Given `FAKE_CLI` 輸出 256 KiB（262144 位元組）的 `patch.text` 加 256 KiB 的 `body.text`（皆 `truncated:true`），總輸出小於 8 MiB；另備輸出 8 MiB 加 1 位元組的替身
  - When 各自 `GET /si/proposals/PROP-SI-901`；另 `GET /si/proposals/PROP-SI-999`（`FAKE_CLI` 回 `items:[]`）、`GET /si/proposals/bad-id`
  - Then 第一個 200 且兩段文字位元組不變；超量者 503 `cause=stdout_too_large`（既有行為）；查無 404 `si_not_found`；格式不符 422 `invalid_request`（`rule=invalid_format`）
  - 判定：`python -m pytest tests/test_si_proposal_detail.py -k AT_966_4_E_1 -q`；預期突變：把 stdout 上限降到 256 KiB，紅
  - 驗收字樣：[AT_OK_966_4_E_1]

**B. backend（JUnit；`SiPatrolApiIT`、`SiProposalDetailApiIT`，皆在 `com.aisdlc.console.adapter.in.web`，`AbstractApiIT` 體例；`OpenApiIT` 在 `…infrastructure.config`；`SiReadOnlyArchTest` 在 `…architecture`）**

- **AT-966-3-1**（JUnit｜`SiPatrolApiIT`｜Integration｜AC-966-3、W-F3、W-F11）角色矩陣與非 GET 方法。
  - Given `MINI.patrol(200, <C-1 本文>)`
  - When `GET /api/v1/si/patrol` 依序以無 token、`VIEWER`、`OPERATOR`、`ADMIN`；再以 `ADMIN` 對同路徑 `POST`、`PUT`、`PATCH`、`DELETE`
  - Then 無 token＝401；三種角色皆 200 且回應相同；非 GET 四種方法在 `ADMIN` 下皆為 405（與既有 `/api/v1/si/status` 的非 GET 預期逐項相同，以 `SiMirrorApiIT` 現行斷言為準）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiPatrolApiIT.AT_966_3_1*"`；預期突變：加 `@PreAuthorize("hasRole('ADMIN')")`、放行 POST，皆紅
  - 驗收字樣：[AT_OK_966_3_1]
- **AT-966-3-2**（JUnit｜`SiPatrolApiIT`｜Integration｜AC-966-3、W-F3）欄名深層對映。
  - Given `MINI.patrol` 本文取 `PR()` 的完整 snake_case 夾具（含 `read_at`、`truncated`、`steps`、`schedule`〔含 `current`、`last_skip`、`audit_ref`〕、`ingest`、`props`、`runs.live`、`runs.waiting`、`runs.queued`、`push`〔含 `retry`、`finished_at`、`tick_at`〕）
  - When `GET /api/v1/si/patrol`
  - Then `data.schemaRev`、`data.kind`、`data.readAt`（由 `read_at` 轉來）存在；`data.report.generatedAt`、`heartbeatMinutes`、`ledgerSeq`、`truncated`、`off` 存在；`schedule.lastSkip.auditRef`、`ingest[0].auditRef`、`runs.live[0].startedAt`、`wallDueAt`、`runs.waiting[0].code`、`push.finishedAt`、`push.tickAt`、`push.retry`、`props[0].id` 存在；**所有值與輸入逐值相等**；原 snake_case 鍵（`generated_at` 等）**不存在**；已是 camelCase 或單字的鍵（`runs`、`push`、`schedule`）恆等；`read_at` 與 `readAt` 並存者依「不變的鍵先保有名字」規則（本 AT 不構造此情形）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiPatrolApiIT.AT_966_3_2*"`；預期突變：只轉第一層、不把 `read_at` 轉成 `readAt`，皆紅
  - 驗收字樣：[AT_OK_966_3_2]
- **AT-966-3-3**（JUnit｜`SiPatrolApiIT`｜Integration｜AC-966-3、W-F3）Bridge 錯誤逐字透傳。
  - Given `MINI.patrol(503, {reason:"si_unavailable",cause:<c>,detail:"…"})`，`<c>` 依序為四個 cause；另 `MINI` 不可達、`MINI` 延遲超過讀取逾時（backend 的連線 2 秒、讀取 20 秒是常數、沒有可縮短的屬性，沿 `SiMirrorApiIT` 既有做法讓迷你 Bridge 真等待約 21 秒，該案單獨設較長的測試逾時；不為本 AT 新增屬性）
  - When `GET /api/v1/si/patrol`
  - Then 四個 cause 皆 503、`reason=si_unavailable`、`details.cause` 與 `details.detail` 逐字、**無 `data`**；不可達＝502；逾時＝504；任一情況只打一次 Bridge（不重試）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiPatrolApiIT.AT_966_3_3*"`；預期突變：把 `report_*` cause 白名單化丟掉未知 cause、加重試，皆紅
  - 驗收字樣：[AT_OK_966_3_3]
- **AT-966-3-4**（JUnit｜`SiPatrolApiIT`｜Integration｜AC-966-3、NFR-FV-1）恰一次 Bridge 呼叫、零 DB 寫入。
  - Given 測試前後各取 `si_console_writes` 與 `audit_log` 的列數與內容 hash；`MINI.requests()` 清空
  - When 連續呼叫五次（含一次 Bridge 503）
  - Then `MINI.requests()` 恰五筆且皆為 `GET /si/patrol`（無本文、不帶 `X-Bridge-Token` 以外的寫入標頭）；兩表列數與 hash 不變；該端點的 `audit_log` 不新增 `entity_type='si_patrol'` 之類列
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiPatrolApiIT.AT_966_3_4*"`；預期突變：每次呼叫寫稽核列、先打 `GET /si/status` 再打 patrol，皆紅
  - 驗收字樣：[AT_OK_966_3_4]
- **AT-966-3-5**（JUnit｜`OpenApiIT` 新案 `AT_966_3_5…`｜Integration｜AC-966-3、NFR-FV-5）OpenAPI 條目與計數。
  - Given `/v3/api-docs`
  - When 讀 `getSiPatrol`
  - Then 路徑 `/api/v1/si/patrol` 恰一個操作（GET）、operationId `getSiPatrol`、tag 為「自我進化（SelfImproving）」、description 提到「唯讀」「巡邏快照」與四個 cause；文件化狀態碼含 200／401／502／503／504；路徑總數與操作總數各等於**本鍵實作前現值加一**（現值取 `OpenApiIT` 現行 `AT_964_7_7*` 的常數，不硬寫絕對值於本 AT）
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_966_3_5*"`；預期突變：漏 operationId、多註冊第二個操作，皆紅
  - 驗收字樣：[AT_OK_966_3_5]
- **AT-966-3-6**（JUnit｜`SiReadOnlyArchTest` 新案 `AT_966_3_6…`｜Unit｜AC-966-3、NFR-FV-5）結構鎖計數與寫入埠隔離。
  - Given 主程式 class 檔
  - When ArchUnit 檢查
  - Then `Si*Controller` 的 `@GetMapping` 恰九個（原八個加 `patrol`）、`@PostMapping` 仍恰七個；`AgentBridge` 上 `si` 接大寫字母起頭的方法恰九個（加 `siPatrol`）；寫入埠與 `si_console_writes` 表的存取者集合不變（`patrol` 路徑不觸及 `SiConsoleWriteService`）
  - 判定：`gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest"`；預期突變：patrol 處理函式注入 `SiConsoleWriteRepository`，紅
  - 驗收字樣：[AT_OK_966_3_6]
- **AT-966-3-E-1**（JUnit｜`SiPatrolApiIT`｜Integration｜AC-966-3）未知鍵、非 ASCII、1 MiB 本文與腳本字樣原樣。
  - Given `MINI.patrol` 本文含未知頂層鍵與 `report` 內未知鍵（`future_key`、`futureKey`）、`props[0].text` 為 `<script>alert(1)</script>**粗體**` 加全形與 emoji、`report` 總大小 1,048,000 位元組
  - When `GET /api/v1/si/patrol`
  - Then 200；未知鍵依對映規則出現（`future_key`→`futureKey`；已 camelCase 者恆等；兩源轉同名時「不變的先保有名字」）；字串值逐位元組相等（不轉義、不截斷）；回應完整可解析
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiPatrolApiIT.AT_966_3_E_1*"`；預期突變：對字串值做 HTML 轉義、對本文設 256 KiB 上限，皆紅
  - 驗收字樣：[AT_OK_966_3_E_1]
- **AT-966-4-3**（JUnit｜`SiProposalDetailApiIT`｜Integration｜AC-966-4、W-F4）兩種欄名風格對映與未知鍵透傳。
  - Given `MINI.proposalDetail("PROP-SI-901", item)`，`item.detail` 兩個版本：(a) 全 camelCase（C-3 原樣）；(b) 全 snake_case（`below_min`、`frozen_by`、`touched_ok`、`rollback_ok`、`fail_code`、`baseline_red`、`patched_green`、`mutated_red`、`probes_n`、`carrier_proof`）；各另含未知鍵 `detail.futureThing`、`detail.heldout.extra_key`
  - When `GET /api/v1/si/proposals/PROP-SI-901`
  - Then 兩版皆回 `items[0].detail` 且鍵為同一組 camelCase（(b) 被轉成與 (a) 相同的鍵名）；`verify.reasons[].code`／`text` 值不變；`sandbox.failText`、`heldout.neNote`、`sourceObs[]`、`timeline[]` 與 `ne[].text` 逐值不變；另一列以黃金樣本複本 `src/test/resources/si/p7/detail.golden.json`（整個 `items[0]`）餵 `MINI.proposalDetail`（先斷言複本位元組等於根層檔 `tools/tests/fixtures/selfimproving/p7/detail.golden.json`）；未知鍵依規則透傳（`extra_key`→`extraKey`）；`patch.text` 與 `body.text` 位元組相等；`items` 恰一筆
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiProposalDetailApiIT.AT_966_4_3*"`；預期突變：丟掉未知鍵、對 `reasons[]` 陣列內物件不轉鍵，皆紅
  - 驗收字樣：[AT_OK_966_4_3]
- **AT-966-4-4**（JUnit｜`SiProposalDetailApiIT`｜Integration｜AC-966-4、W-F4）null 與缺席區分。
  - Given 三份 `item`：(a) `detail.patch=null`、`body=null`、`sandbox=null`、`verify=null`、`heldout.seq=null`、`heldout.n=null`；(b) 完全沒有 `detail` 鍵；(c) `detail.verify.reasons=[]`
  - When `GET /api/v1/si/proposals/PROP-SI-901`
  - Then (a) 上述鍵**存在且值為 JSON null**；(b) `items[0]` **沒有** `detail` 鍵（不補 null、不補 `{}`）；(c) `reasons` 為空陣列（不是 null、不是缺席）；`ne[]` 逐項透傳
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiProposalDetailApiIT.AT_966_4_4*"`；預期突變：序列化設定 `NON_NULL` 丟掉 null，紅
  - 驗收字樣：[AT_OK_966_4_4]
- **AT-966-4-5**（JUnit｜`SiProposalDetailApiIT`｜Integration｜AC-966-4）256 KiB patch 往返。
  - Given `MINI.proposalDetail` 的 `patch.text` 為 262144 位元組（混合 ASCII、中文、`\r\n`），`truncated:true`、`bytes:262144`；`body.text` 同大
  - When `GET /api/v1/si/proposals/PROP-SI-901`
  - Then 200；兩段文字逐位元組相等；`patch.truncated` 為 true；backend 讀取 Bridge 本文無截斷（8 MiB 內）；單次請求在測試逾時內完成
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiProposalDetailApiIT.AT_966_4_5*"`；預期突變：`BridgeHttpAdapter` 的本文上限降為 128 KiB，紅
  - 驗收字樣：[AT_OK_966_4_5]

**C. frontend 純函式（vitest；`lib/domain/siFlow.test.ts`；函式皆住 `lib/domain/siFlow.ts`，純函式、不讀時鐘、不讀 DOM）**

- **AT-966-5-1**（vitest｜`lib/domain/siFlow.test.ts`｜Unit｜AC-966-5、W-F5）`patrolFreshness(report, readAt, receivedAtMs, nowMs)` 邊界表與隨時間前進。
  - Given `heartbeatMinutes=15`（限度 35 分鐘）、`readAt=NOW`、`receivedAtMs=T0`；`generatedAt` 分別比 `NOW` 早 0、34 分 59 秒、35 分 00 秒、35 分 01 秒、10 小時；比 `NOW` 晚 4 分 59 秒、5 分 01 秒；`heartbeatMinutes` 為 5（限度 15）、60（限度 125）；另一組：`generatedAt` 比 `NOW` 早 3 分鐘，`nowMs` 依序為 `T0`、`T0`＋31 分 59 秒、`T0`＋32 分 00 秒、`T0`＋32 分 01 秒
  - When 呼叫
  - Then 回傳 `{state, ageMinutes, limitMinutes}`：0／34:59／35:00＝`fresh`（**嚴格大於才過時**）；35:01／10 小時＝`stale`；晚 4:59＝`fresh`（ageMinutes 為負值取 0）、晚 5:01＝`clock-skew`；`limitMinutes` 依 `2×hb+5` 為 35／15／125；另一組：3 分鐘加經過 31:59＝34:59 `fresh`、加 32:00＝35:00 `fresh`、加 32:01＝35:01 `stale`（**頁面放著不動，跨過門檻就轉過時，與是否重新抓取無關**）；`readAt` 缺席或無法解析時改用 `nowMs` 並回 `usedClientClock:true`
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_1`；預期突變：`>` 改 `>=`、常數 2 改 3、grace 改 10、晚 5 分判成過時、忽略經過時間，皆紅
  - 驗收字樣：[AT_OK_966_5_1]
- **AT-966-5-2**（vitest｜同檔｜Unit｜AC-966-5、W-F6）`resolveNextStep` 來源序。
  - Given `P901.lastSeq=120`；快照 `ledgerSeq`、新鮮度、`props[]` 是否含 `PROP-SI-901`、詳情 `next` 是否存在，組成八個情境（逐列：可用且有／可用但無該提案／過時／`ledgerSeq=119`／快照缺席／快照無效／詳情缺席／兩者皆無）
  - When 呼叫
  - Then 可用且有＝`{source:"snapshot", …該筆}`；可用但無該提案＝改用詳情 `next`（`source:"detail"`）；過時＝詳情 `next`；`ledgerSeq<lastSeq`＝詳情 `next`；快照缺席或無效且有詳情＝詳情；兩者皆無＝`{source:"none", text:"量不到"}`；`ledgerSeq===lastSeq` 視為可用（`≥`）；當 `source==="detail"`、`who==="巡邏器"` 且快照過時時 `warnPatrolMayBeDown:true`，其餘情境為 false
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_2`；預期突變：`≥` 改 `>`、過時仍用快照，皆紅
  - 驗收字樣：[AT_OK_966_5_2]
- **AT-966-5-3**（vitest｜同檔｜Unit｜AC-966-5、W-F7、C-5）列舉值的已知判定與未知值保底。
  - Given 已知集合：等待對象五值（掌舵者、巡邏器、無人運轉、主機管理者、無）、運轉目的第一波三值（`scheduled`、`console`、`manual`）、驗證結果三值、入帳狀態兩值、推送狀態八值（`off`、`idle`、`pending`、`waiting-login`、`running`、`ok`、`failed`、`blocked`）；加上未知值 `"zzz"`、空字串、`null`、`undefined`、數字 `7`、物件，以及**第二波才有的值**：運轉目的 `freeze`、`revise`、`propose`，推送狀態 `skipped`
  - When 各 `labelOf…`／`isKnown…` 函式
  - Then 已知值：運轉目的為「排程啟動」「從畫面按『立即啟動』」「手動啟動」；驗證結果「通過」「未通過」「無法評估」；入帳狀態「被拒收」「延後」；等待對象原樣；推送狀態只回 `known:true` 與樣式類別（`ok`→成功、`failed`／`blocked`→警示、其餘中性），**不回任何標籤句**；未知與第二波值（`freeze`、`revise`、`propose`、`skipped`、`zzz`）一律 `known:false`，字串為「未知值『X』」；空字串／null／undefined 為「量不到」；數字與物件得「未知值」加其 `String()`（物件為 `[物件]`，**不得出現 `[object Object]`**）；`known:false` 使呼叫端不套成功樣式
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_3`；預期突變：把 `freeze` 當已知、`skipped` 當已知、推送狀態自建標籤、`String(obj)` 漏出，皆紅
  - 驗收字樣：[AT_OK_966_5_3]
- **AT-966-5-4**（vitest｜同檔｜Unit｜AC-966-5、W-F7）`reasonText(code, text)` 保底句與 `maskCredentials`。
  - Given (`"STALE-CARD"`, `"卡面已過期"`)、(`"X-1"`, `""`)、(`"X-1"`, `undefined`)、(`"X-1"`, `42`)、(`undefined`, `"只有說明"`)、(`undefined`, `undefined`)；字串三組（凡「網址內嵌帳密」的夾具一律由測試在執行期拼出，規格與測試檔都不落完整字面，以免被機密掃描閘擋下）：`"push "`＋內嵌帳密的 https 網址（`https://`＋`<帳號>`＋`:`＋`<密碼>`＋`@github.com/x.git`，帳號取 user、密碼取 p%40ss）＋`" failed"`；`"git@github.com:a/b.git"`；內嵌帳密的 http 網址（`http://`＋`<帳號>`＋`:`＋`<密碼>`＋`@c/d`，帳號取 a、密碼取 b）＋一個空白＋`https://e@f/g`
  - When 呼叫
  - Then 有合法 `text` 者逐字回 `text`（不二次加工）；`text` 缺席／空／非字串者回「主機沒有提供白話說明（原因碼 X-1）。」；兩者皆無回「主機沒有提供原因。」；`maskCredentials` 把 `scheme://userinfo@` 換成 `scheme://***@`（兩個 URL 皆遮罩、`git@github.com:a/b.git` 不動）；遮罩後字串不含原 userinfo；函式不丟例外
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_4`；預期突變：保底句漏原因碼、遮罩只處理第一個 URL，皆紅
  - 驗收字樣：[AT_OK_966_5_4]
- **AT-966-5-5**（vitest｜同檔｜Unit｜AC-966-5、W-F8）`parseDiff(text)` 解析與計數。
  - Given 夾具 `patch-mixed.diff`（含 `diff --git`、`index`、`--- a/f`、`+++ b/f`、兩個 `@@`、新增行、刪除行、上下文行、`\ No newline at end of file`、一行內容本身以 `++` 起頭的新增行 `+++x`、一個 CRLF 行、空行）；另 `""`、`"\n"`、無結尾換行
  - When 呼叫
  - Then 每行種類依 W-F8（`+++ b/f` 與 `--- a/f` 為 `file`，`+++x` 為 `add`，`\ No newline…` 為 `meta`，空行與其他為 `ctx`）；`lines[i].text` 逐字等於原行（含行首符號，**CRLF 的 `\r` 保留於 text 但不計入顯示行數的額外一行**）；`addCount`／`delCount` 不含 `file` 行；`lines.map(l=>l.text).join("\n")` 等於輸入（結尾換行規則：輸入以 `\n` 結尾時最後一個空元素不算一行）；`""`→零行、`"\n"`→零行
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_5`；預期突變：把 `+++x` 當檔頭、`\r` 當成新行，皆紅
  - 驗收字樣：[AT_OK_966_5_5]
- **AT-966-5-6**（vitest｜同檔｜Unit｜AC-966-5、W-F8）`diffWindow`、`downloadSpec`。
  - Given 399、400、401、1000 行的 `parseDiff` 結果；`patch={rel:"docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch",bytes:…,text,truncated:false|true}`；`patch.rel` 缺席時以 `proposal.rev=2`
  - When `diffWindow(lines, expanded)` 與 `downloadSpec(propId, rev, patch)`
  - Then 399／400＝全顯示且 `canExpand:false`；401／1000＝未展開時顯示前 400、`hiddenCount` 為 1／600、`canExpand:true`；展開後全顯示；`downloadSpec` 檔名 `PROP-SI-901-r2.patch`（`truncated` 時 `PROP-SI-901-r2.truncated.patch`）、內容＝`patch.text`、MIME `text/plain;charset=utf-8`；檔名不含路徑分隔符與控制字元（`rel` 含 `..` 或反斜線時仍只取安全字元）
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_6`；預期突變：視窗改 401、檔名用 `rel` 全路徑，皆紅
  - 驗收字樣：[AT_OK_966_5_6]
- **AT-966-5-7**（vitest｜同檔｜Unit｜AC-966-5、W-F10）`joinHostRejections(items, report)`（前端收到的鍵名形態，camelCase）。
  - Given 對帳 `items`（`ingested` 為 false／true／null 各數筆，`auditRef` 各異）與 `PATROL({ingest:[…]}).report.ingest[]`（鍵 `auditRef`、`kind`、`status`、`code`、`text`、`permanent`；含對應項、無對應項、重複 `auditRef`、`permanent` 為 true／false／缺席／字串）
  - When 呼叫
  - Then 回傳每個 `ingested===false` 的列對應的 `{status, code, text, permanent, mode}`，`mode`∈{`human`（permanent true）、`auto`（false）、`unknown`（其他）}；`ingested===true` 與 `null` 的列一律不結合；重複 `auditRef` 取第一筆；沒有對應項者回 `null`；`report` 為 null 時全部回 `null`；輸入不被修改（凍結物件不丟例外）；**以 snake_case 鍵（`audit_ref`）餵入的物件一律視為無對應項**（鎖定前端只認 camelCase，防止兩種寫法並存）
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_7`；預期突變：對已入帳列也結合、重複取最後一筆、同時接受兩種鍵名，皆紅
  - 驗收字樣：[AT_OK_966_5_7]
- **AT-966-5-8**（vitest｜同檔｜Unit｜AC-966-5、W-F9）`heldoutView`、`verifyView`、`sandboxView` 檢視模型。
  - Given `heldout`（八鍵：`frozen`、`seq`、`n`、`min`、`belowMin`、`frozenBy`、`digest8`、`neNote`）：`{frozen:false,…}`、`{frozen:true,n:7,min:5,belowMin:false}`、`{frozen:true,n:5,min:5,belowMin:false}`、`{frozen:true,n:4,min:5,belowMin:true,neNote:"案例數 4 低於下限 5，驗證結果只能是 NE"}`、`belowMin:true` 而 `neNote` 為 null／空字串／缺席、`{frozen:true,n:null}`、`null`，另帶額外鍵 `cases`、`probes`、`digest`；`verify`：PASS／FAIL／NE、三步布林含 null、`carrierProof` 為 true／false／null、`reasons` 空與非空與缺席、未知 `verdict:"WEIRD"`；`sandbox`：成功、`applied:false`＋`failCode`＋`failText`、`applied:false`＋`failCode` 而 `failText` 為 null／空字串／缺席、`null`
  - When 呼叫
  - Then 評估集：`n=5,min=5` 不警示；`belowMin:true` 時警示字串**逐字等於 `neNote`**；`neNote` 為 null／空字串／缺席時改用保底句「案例數低於下限，驗證結果只能是『無法評估』」；`n` 為 null 且已凍結＝「案例數量不明」；輸出物件**不含 `digest8`**，且序列化後不含 `cases`、`probes`、`digest` 字樣；驗證：結果標籤依 C-5、三步各為「是／否／量不到」、`carrierProof` 為「通過／沒通過／量不到」、未知 `verdict` 得 `known:false`；隔離試跑（沙盒）：`failText` 非空時**逐字使用**，缺席或空字串時才用保底句「隔離試跑沒有通過：<碼>（主機沒有提供白話說明）」
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_8`；預期突變：`n<=min` 當低於、前端自寫低於下限句而忽略 `neNote`、忽略 `failText`、額外鍵漏入輸出，皆紅
  - 驗收字樣：[AT_OK_966_5_8]
- **AT-966-5-9**（vitest｜同檔｜Unit｜AC-966-5、W-F7、W-F13）`pushView(push)`、`scheduleView(schedule)`、`waitingView(waiting)`、`relativeMinutesText`。
  - Given `push` 八態各一份，內容取自根層 TCS-P7 附錄 A.4／A.4b 的固定句：`off`＋`PUSH-OFF`「自動推送已關閉」；`idle`＋`PUSH-NOT-AHEAD`「沒有待推送的提交」；`pending`＋`PUSH-PENDING`「等推送任務下一次執行（每個心跳一次）」；`waiting-login`＋`PUSH-WAITING-LOGIN`「等使用者登入後自動推送」；`running`＋`PUSH-RUNNING`；`ok`＋`PUSH-OK`＋`sha`＋`finishedAt`；`failed`＋`PUSH-FAILED`＋`retry:"wait"`＋`attempts:2`；`blocked`＋`PUSH-DIRTY-TREE`；另 `blocked`＋`PUSH-FOREIGN-COMMITS` 的 `text` 含 `{detail}` 已填的 sha 前 8 碼；`blocked`＋`PUSH-NOT-RECORDED`、`PUSH-RECORD-MISMATCH`、`PUSH-LEDGER-RULE`（`retry:null`，根層附錄 A.4 的固定句）各一份——三者與其他 `blocked` 碼走同一條路徑、不需特例；未知 `state:"（已廢止的設計稿第五態名）"`＋有 `text`、`state:"zzz"`＋無 `text`；`text` 缺席或空字串的已知態；`null`；`enabled` 缺席。`schedule`：`null`、`{enabled:false,current:{code:"SCHED-DISABLED",text:"…"},lastSkip:null}`、`current:null`、`lastSkip:{seq:99,t:"…",code:"SKIP-RUN-OPEN",text:"…",auditRef:null}`、`lastSkip.auditRef` 為 UUID。`waiting`：`[{run:"RUN-SI-902",code:"SKIP-OTHER-DRIVER",text:"…"}]`、`[]`、缺席。分鐘數 0、0.5、1、59、61、125、1500、負數、NaN
  - When 呼叫
  - Then `pushView`：顯示句**逐字等於 `push.text`**（`{detail}` 已由根層填入，Console 不二次處理），並依 `state` 決定樣式：`ok` 成功樣式、`failed`／`blocked` 警示樣式、其餘中性；`ok` 補「（提交 <sha 前 8 碼>）」與完成時間；`failed` 補「已嘗試 N 次」；`retry` 不另加句子（句子已含「稍後自動重試」等語意）；`text` 缺席或空字串＝保底句「主機沒有提供白話說明（原因碼 <code>）。」；未知 `state`（含 （已廢止的設計稿第五態名））＝「未知的推送狀態『X』」並附 `text`（若有）、不套成功樣式；`null`＝「量不到」；所有輸出經 `maskCredentials`。`scheduleView(schedule, off)`：`schedule` 為 null 且 `off:true`＝「巡邏已暫停，沒有排程資訊」；`schedule` 為 null 而 `off` 不是 true（含缺席）＝「這份回報沒有排程資訊」（不說成暫停、也不說成排程停用）；`enabled:false`＝取 `current.text`；`current:null`＝「目前這一格的排程狀態量不到」；`lastSkip` 非 null 時回「最近一次略過：<時間> <text>」，`auditRef` 非 null 時另加「這次略過的是你從畫面按的『立即啟動』（稽核編號 <auditRef>）」；`waitingView`：每筆「<run> 等待中：<text>」；空陣列＝「目前沒有在等待啟動的運轉」；缺席＝「等待中的運轉量不到」。`relativeMinutesText`：0 與小於 1＝「剛剛」、1＝「1 分鐘前」、59＝「59 分鐘前」、61＝「1 小時 1 分鐘前」、125＝「2 小時 5 分鐘前」、1500＝「1 天 1 小時前」、負數與 NaN＝「時間量不到」
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_9`；預期突變：自建推送狀態對照句、對 `PUSH-NOT-RECORDED` 等新碼寫特例、把 `skipped` 當已知、`text` 缺席時回空字串、`auditRef` 非 null 時不加註、未遮罩 text，皆紅
  - 驗收字樣：[AT_OK_966_5_9]
- **AT-966-5-E-1**（vitest｜同檔｜Unit｜AC-966-5、NFR-FV-3）缺席、`null`、空陣列三者區分。
  - Given `report` 夾具：`props` 缺席／為 `null`／為 `[]`／為字串；`runs` 缺席／`{}`／`{live:[],queued:[]}`／`{live:null}`；`steps`、`ingest` 同理；`push` 缺席／`null`／`{}`
  - When `sectionState(value)` 與各檢視模型
  - Then 缺席、`null`、錯型別＝`unknown`（畫面「量不到」）；空陣列＝`empty`（畫面「無」類文案，各段文案不同）；非空＝`items`；**任何輸入不得得到 `empty`，除非它是真的陣列且長度為 0**；`runs.live` 缺席而 `runs.queued` 為空陣列時兩段各自判定
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_5_E_1`；預期突變：`?? []` 把缺席當空陣列，紅
  - 驗收字樣：[AT_OK_966_5_E_1]

**D. frontend 元件（vitest；檔名與渲染輔助見 §5.6；一律 `renderSi`，網路為 `stubSiApi` 的 fetch 替身，時間取 `NOW`）**

- **AT-966-6-1**（vitest｜`SiProposalDetail.test.tsx`｜Unit｜AC-966-6、W-F11）每列「詳情」鈕、開關與焦點歸還。
  - Given 提案分頁有三列（含 `P901`），以 `VIEWER_UI`、`OPERATOR_UI`、`ADMIN_UI` 各渲染
  - When 點 `P901` 的「詳情」鈕（`data-testid="si-detail-open-PROP-SI-901"`、`aria-label="詳情 PROP-SI-901"`）；按 Esc
  - Then 三種角色皆有三個「詳情」鈕；開啟後出現 `role="dialog"`、`aria-modal="true"`（Radix 預設不帶，元件須顯式設定）、名稱為「提案詳情 PROP-SI-901」；Esc 關閉；焦點回到該鈕（沿 `dialog.tsx` 的歸還行為）；ADMIN 另有的「決定」鈕不受影響
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_1`；預期突變：只對 ADMIN 顯示、關閉後焦點落到 `<body>`，皆紅
  - 驗收字樣：[AT_OK_966_6_1]
- **AT-966-6-2**（vitest｜同檔｜Unit｜AC-966-6）五分頁順序與鍵盤。
  - Given 開啟 `P901` 詳情
  - When 檢視 tablist；按 →、←、End、Home
  - Then `aria-label` 為「提案詳情分頁」，分頁依序為「卡面」「變更內容」「提案本文」「評估集與驗證」「時間線」（沿 `PillTabs`）；預設選「卡面」；方向鍵與 Home／End 切換並移動焦點；每個 tabpanel 以 `aria-labelledby` 關聯
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_2`；預期突變：順序對調、預設選「變更內容」，皆紅
  - 驗收字樣：[AT_OK_966_6_2]
- **AT-966-6-3**（vitest｜同檔｜Unit｜AC-966-6、W-F12）懶取數與請求次數。
  - Given `stubSiApi` 記錄請求；渲染提案分頁
  - When (a) 只渲染不點；(b) 點「詳情」；(c) 逐一切到五個分頁（含「時間線」）；(d) 關閉再重開
  - Then (a) 對 `/api/v1/si/proposals/` 的請求 0 次；(b) 恰 1 次 `GET /api/v1/si/proposals/PROP-SI-901`（路徑段 percent-encode 後的單一段）；(c) 仍是 1 次，且**全程對 `/api/v1/issues/` 的請求 0 次**（時間線取自 `detail.timeline`）；(d) 關閉後資料丟棄（`gcTime: 0`）、重開再取一次提案詳情（共 2 次）；全程無非 GET 請求
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_3`；預期突變：清單載入即預取詳情、切到時間線時另打議題端點，皆紅
  - 驗收字樣：[AT_OK_966_6_3]
- **AT-966-6-4**（vitest｜同檔｜Unit｜AC-966-6、NFR-FV-3）載入、503、404 三態。
  - Given 詳情端點依序回：延遲中、503 `si_unavailable`（`cause=nonzero_rc`）、404 `si_not_found`、502
  - When 開啟詳情
  - Then 延遲中顯示「載入中」且五分頁內容區不顯示任何「沒有」字樣；503 顯示原因（`si_unavailable`、cause、detail 逐字）與「重試」鈕，按下恰多 1 次請求；404 顯示「查無這個提案」；502 顯示通用錯誤與原因；**任何錯誤態都不渲染空的 diff、空的評估集、「沒有變更」「未凍結」等字樣**
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_4`；預期突變：錯誤時渲染空資料頁籤，紅
  - 驗收字樣：[AT_OK_966_6_4]
- **AT-966-6-5**（vitest｜同檔｜Unit｜AC-966-6、W-F6）頂端「下一步」三種來源。
  - Given (a) 快照可用且 `props[]` 有 `P901`（`who:"掌舵者"`、`text:"等你決定要不要晉升"`）；(b) 快照過時、詳情 `next={who:"巡邏器",text:"巡邏器會自動跑驗證"}`；(c) 快照端點 503 且詳情無 `next`
  - When 開啟詳情
  - Then (a) 對話框最上方（分頁之上）有 `data-testid="si-next-step"`，文字為「下一步：等掌舵者｜等你決定要不要晉升」且來源註記「依巡邏回報」；(b) 文字取詳情、註記「依帳本判斷」；(c) 文字「下一步：量不到」；`who` 為「無」時文字改為「目前不需要任何人動作：<text>」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_5`；預期突變：永遠用詳情、`who` 為「無」仍寫「等無」，皆紅
  - 驗收字樣：[AT_OK_966_6_5]
- **AT-966-6-6**（vitest｜同檔｜Unit｜AC-966-6、W-F6）過時快照加巡邏器警示行。
  - Given 快照過時（`generatedAt` 早於 `NOW` 40 分、週期 15）；詳情 `next.who="巡邏器"`；另一情境 `who="掌舵者"`
  - When 開啟詳情
  - Then 前者在「下一步」下多一行「巡邏可能沒在跑，這一步可能不會自動進行」（`data-testid="si-next-warning"`）；後者沒有該行
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_6`；預期突變：對所有 who 都加警示、快照新鮮也加，皆紅
  - 驗收字樣：[AT_OK_966_6_6]
- **AT-966-6-7**（vitest｜同檔｜Unit｜AC-966-6、NFR-FV-4）純文字渲染與靜態無 innerHTML。
  - Given 詳情夾具 `DETAIL(hostile)`：`patch.text`、`body.text`、`next.text`、`reasons[].text`、`heldout.frozenBy`、`heldout.neNote`、`sandbox.failCode`、`sandbox.failText`、`sourceObs[].symptom`、`timeline[].action`、`card` 皆含 `<img src=x onerror=alert(1)>`、`<script>window.__x=1</script>`、`**粗體**`、`[x](javascript:alert(1))`、`&lt;`
  - When 開啟詳情並逐一切換五分頁
  - Then DOM 內沒有任何由這些字串產生的 `img`、`script`、`a[href^=javascript]` 元素；字串以字面文字出現（`textContent` 含原字串）；`window.__x` 為 undefined；另靜態斷言：`SiProposalDetail.tsx`、`SiDiffView.tsx`、`SiPatrolCard.tsx`、`siFlow.ts` 的原始碼不含 `dangerouslySetInnerHTML`、`innerHTML`、`insertAdjacentHTML`、`document.write`
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_7`；預期突變：以 `dangerouslySetInnerHTML` 渲染本文，紅
  - 驗收字樣：[AT_OK_966_6_7]
- **AT-966-6-E-1**（vitest｜同檔｜Unit｜AC-966-6、W-F4）舊根層無 `detail`、卡面為 null。
  - Given (a) 詳情回應的 `items[0]` 沒有 `detail` 鍵；(b) `P901.card===null` 且 `ne` 有 `proposals.PROP-SI-901.card`
  - When 開啟詳情
  - Then (a) 四個依賴 `detail` 的分頁顯示「這個根層版本還沒提供詳情（量不到）」，「卡面」分頁仍逐字顯示清單列的 `card`，「下一步」依快照或「量不到」；(b) 「卡面」分頁顯示「卡面量不到」與對應 `ne` 項，其餘分頁照常
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_6_E_1`；預期突變：缺 `detail` 時渲染成「沒有變更」，紅
  - 驗收字樣：[AT_OK_966_6_E_1]
- **AT-966-7-1**（vitest｜`SiDiffView.test.tsx`｜Unit｜AC-966-7、W-F8）逐行原文、種類與計數句。
  - Given `patch.text` 為 `patch-mixed.diff`（見 AT-966-5-5）
  - When 渲染「變更內容」分頁
  - Then 每行一個 `data-diff-kind` 屬性值∈{add,del,hunk,file,meta,ctx} 的元素；各行 `.diff-text` 的 `textContent` 以 `\n` 連接逐字等於輸入；計數句 `data-testid="si-diff-summary"` 為「新增 N 行、刪除 M 行」（N、M 取 `parseDiff` 的 `addCount`／`delCount`）；顯示 `patch.rel` 與位元組數
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_1`；預期突變：行首符號被吃掉、計數含檔頭，皆紅
  - 驗收字樣：[AT_OK_966_7_1]
- **AT-966-7-2**（vitest｜同檔｜Unit｜AC-966-7、NFR-FV-6）顏色以外的標示。
  - Given 含 add、del、hunk、ctx 各一的小 patch
  - When 渲染
  - Then add 行：行首 `+` 在文字節點內、左邊框 class 為實線（`border-solid`）、含 sr-only 前綴「新增：」；del 行：行首 `-`、`border-dashed`、sr-only「刪除：」；hunk 行：以 `@@` 起頭、粗體、sr-only「區段：」；ctx 行無前綴；**單靠移除全部顏色 class 仍可由符號、邊框形狀與 sr-only 文字區分四類**（測試移除含 `bg-`、`text-wg-` 的 class 後以符號與 `border-*` 形狀重新分類，結果與原分類全等）；`.diff-text` 不含 sr-only 前綴（避免污染原文比對）
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_2`；預期突變：del 與 add 都用實線、拿掉 sr-only 前綴，皆紅
  - 驗收字樣：[AT_OK_966_7_2]
- **AT-966-7-3**（vitest｜同檔｜Unit｜AC-966-7）截斷提示與下載。
  - Given (a) `truncated:false`；(b) `truncated:true`、`rel` 為 `docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch`；`URL.createObjectURL`／`revokeObjectURL` 與 `<a>.click` 以替身記錄
  - When 檢視；按「下載 patch 檔」
  - Then (a) 無截斷提示；(b) 有 `data-testid="si-diff-truncated"`「內容過長已截斷，完整檔在 docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch」；下載鈕在 (a) 產生檔名 `PROP-SI-901-r2.patch`、Blob 內容逐字等於 `patch.text`、類型 `text/plain;charset=utf-8`；(b) 檔名 `PROP-SI-901-r2.truncated.patch` 且鈕旁文字註明「這是截斷後的內容」；點擊後 `revokeObjectURL` 被呼叫一次；下載動作零網路請求
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_3`；預期突變：下載時重新打 API、不 revoke，皆紅
  - 驗收字樣：[AT_OK_966_7_3]
- **AT-966-7-4**（vitest｜同檔｜Unit｜AC-966-7、W-F8）400 行視窗與展開。
  - Given 1000 行 patch；另 400 行與 401 行
  - When 渲染；按「展開全部（1000 行）」；再按「只看前 400 行」
  - Then 初始 400 個 `data-diff-kind` 元素並有該展開鈕；展開後 1000 個；再收合回 400；400 行 patch 無展開鈕；401 行顯示「展開全部（401 行）」；展開鈕有 `aria-expanded` 且與狀態一致
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_4`；預期突變：視窗常數改 200、展開後仍 400，皆紅
  - 驗收字樣：[AT_OK_966_7_4]
- **AT-966-7-5**（vitest｜同檔｜Unit｜AC-966-7、NFR-FV-3）patch 為 null、空字串。
  - Given (a) `patch=null` 且 `ne` 有 `proposals.PROP-SI-901.detail.patch`；(b) `patch={text:"",bytes:0,truncated:false,rel:"…"}`；(c) `patch=null` 且 `ne` 無對應項
  - When 渲染
  - Then (a) 顯示「變更內容量不到」與該 `ne` 項（`PATCH-UNREADABLE` 以 `reasonText` 呈現，無 text 時用保底句）；(b) 顯示「這個提案沒有變更內容」；(c) 顯示「變更內容量不到」（無對應 `ne` 也不改說「沒有變更」）；(a)(c) 沒有下載鈕與計數句
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_5`；預期突變：null 與空字串用同一句，紅
  - 驗收字樣：[AT_OK_966_7_5]
- **AT-966-7-E-1**（vitest｜同檔｜Unit｜AC-966-7）256 KiB 夾具視窗化。
  - Given 夾具 `patch-big.diff`（262144 位元組、約 6000 行）
  - When 渲染；展開
  - Then 初始 `data-diff-kind` 元素數恰 400；展開後等於 `parseDiff` 行數；元件整體 DOM 節點數初始小於 `5000`（防止全量渲染）；展開不丟例外
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_E_1`；預期突變：初始就渲染全部，紅
  - 驗收字樣：[AT_OK_966_7_E_1]
- **AT-966-7-E-2**（vitest｜同檔｜Unit｜AC-966-7）單行超長。
  - Given `patch.text` 為 `"+" + "x".repeat(200000)`（單行）
  - When 渲染
  - Then 恰 1 個 `data-diff-kind="add"` 元素；其容器 class 含 `overflow-x-auto` 與 `whitespace-pre`；`.diff-text` 完整含 200001 字元（不截斷於元件層；超過主機上限者由 `truncated` 表示）；**可橫向捲動的 diff 行容器必須可用鍵盤聚焦**：該容器為 `role="region"`、`tabIndex=0`、帶 `aria-label`（文案取自 `SI_FLOW_TEXTS.diffScroll`，現為「變更內容的每一行（可捲動）」），否則 axe `scrollable-region-focusable` 違規（由 AT-966-16-2 與 16-E-1 的 axe 在 E2E 層、本 AT 在單元層雙重守住）；不丟例外
  - 判定：`npx vitest run components/domain/si/SiDiffView.test.tsx -t AT_966_7_E_2`；預期突變：元件層截斷長行、容器拿掉 `tabIndex` 或 `role="region"` 或 `aria-label`，皆紅
  - 驗收字樣：[AT_OK_966_7_E_2]
- **AT-966-8-1**（vitest｜`SiProposalDetail.test.tsx`｜Unit｜AC-966-8）提案本文純文字與截斷。
  - Given `body={rel:"…/r2.md",bytes:48,text:"# 標題\n\n- 項目 <b>x</b>\n",truncated:false}`；另 `truncated:true`
  - When 切到「提案本文」
  - Then 本文在單一 `<pre>`（`whitespace-pre-wrap`、`break-words`）內逐字顯示，`#`、`-`、`<b>` 皆為字面；顯示 `body.rel`；`truncated:true` 時有「內容過長已截斷，完整檔在 <rel>」；不渲染成標題或清單元素
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_1`；預期突變：以 Markdown 渲染，紅
  - 驗收字樣：[AT_OK_966_8_1]
- **AT-966-8-2**（vitest｜同檔｜Unit｜AC-966-8、NFR-FV-3）本文為 null。
  - Given `body=null`；另 `body.text=""`
  - When 切到「提案本文」
  - Then null＝「提案本文量不到」；空字串＝「這個提案沒有本文」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_2`；預期突變：兩者同句，紅
  - 驗收字樣：[AT_OK_966_8_2]
- **AT-966-8-3**（vitest｜同檔｜Unit｜AC-966-8）來源觀察跳轉與高亮。
  - Given `DETAIL({sourceObs:[{id:"OBS-SI-<901>",context:"…",symptom:"…",severity:"P2",disposition:"proposed"}]})`；觀察分頁已載入含 `OBS-SI-<901>` 的列（`si-obs-row-OBS-SI-<901>`）；整個 `SiView` 渲染
  - When 開詳情→「提案本文」分頁→按「看觀察 OBS-SI-<901>」
  - Then 對話框關閉；分頁切到「觀察」；該列有 `data-highlight="true"` 並取得焦點（`tabIndex=-1`＋`focus()`），其餘列沒有；再切離並回到觀察分頁後高亮消失（一次性）；跳轉全程**不新增**詳情（`/api/v1/si/proposals/{id}`）、巡邏（`/api/v1/si/patrol`）與議題（`/api/v1/issues/`）請求，觀察清單（`/api/v1/si/observations`）**至多重取一次**（觀察分頁在提案分頁時是卸載的，SI 查詢 `gcTime: 0`，重掛必然重取；不得重取兩次以上）
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_3`；預期突變：只切分頁不高亮、高亮永久殘留，皆紅
  - 驗收字樣：[AT_OK_966_8_3]
- **AT-966-8-4**（vitest｜同檔｜Unit｜AC-966-8）跳轉目標不在已載入頁、非 OBS 來源、無來源。
  - Given 三個提案：`sourceObs=[{id:"OBS-SI-<777>",…}]`（該觀察不在已載入的觀察頁）、`sources=["DEF-200-575","手寫說明"]` 且 `sourceObs` 缺席、`sources=[]` 且 `sourceObs=[]`
  - When 分別看來源區並對第一個按跳轉鈕
  - Then 第一個跳到觀察分頁後顯示一條說明「找不到 OBS-SI-<777>（可能在更舊的頁，請按『載入更多』）」，無例外；第二個 `DEF-…` 與手寫文字以純文字顯示、**沒有**跳轉鈕（只有符合 `OBS-SI-\d{3,}` 者有鈕）；第三個顯示「這個提案沒有登記來源觀察」；`sources` 與 `sourceObs` 皆缺席＝「來源量不到」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_4`；預期突變：對任何字串都出鈕、找不到時丟例外，皆紅
  - 驗收字樣：[AT_OK_966_8_4]
- **AT-966-8-5**（vitest｜同檔｜Unit｜AC-966-8、W-F14）來源觀察摘要與缺列。
  - Given `sourceObs=[{id:"OBS-SI-<901>",context:"巡邏日誌",symptom:"提案卡了三天沒人處理 <b>x</b>",severity:"P2",disposition:"open"},{id:"OBS-SI-<902>",missing:true}]`；另一情境 `ne` 含 `OBS-LEDGER-UNREADABLE`（帶 `text`）而 `sourceObs` 為空陣列
  - When 切到「提案本文」
  - Then 每筆來源顯示編號、嚴重度、處置、情境與症狀（純文字原文、不截斷）；`missing:true` 者顯示「找不到這筆觀察 OBS-SI-<902>（觀察帳本裡沒有）」；`ne` 的 `OBS-LEDGER-UNREADABLE` 項顯示其 `text`（根層白話），不顯示成「沒有來源」；整段不發任何請求
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_5`；預期突變：缺列者顯示成空白、讀不到帳本時顯示「沒有登記來源觀察」，皆紅
  - 驗收字樣：[AT_OK_966_8_5]
- **AT-966-8-E-1**（vitest｜同檔｜Unit｜AC-966-8）大量與重複來源。
  - Given `sources` 為 30 個 OBS（其中 5 個重複）
  - When 檢視
  - Then 顯示 25 個不重複的鈕（依首次出現序）、區域有最大高度與 `overflow-y-auto`；全部可鍵盤聚焦
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_8_E_1`；預期突變：不去重，紅
  - 驗收字樣：[AT_OK_966_8_E_1]
- **AT-966-9-1**（vitest｜同檔｜Unit｜AC-966-9、W-F9）評估集四種狀態與低於下限提示。
  - Given `heldout`：(a) `frozen:false`；(b) `{frozen:true,seq:60,n:7,min:5,belowMin:false,frozenBy:"凍結者甲",neNote:null}`；(c) `{frozen:true,n:4,min:5,belowMin:true,frozenBy:"凍結者甲",neNote:"案例數 4 低於下限 5，驗證結果只能是 NE"}`；(c2) 同 (c) 但 `neNote:null`；(d) `{frozen:true,n:null,min:5,belowMin:null}`
  - When 切到「評估集與驗證」
  - Then (a)「還沒有凍結評估集」與說明「評估集要由人在主機上凍結，巡邏器不會自己建立；凍結前這個提案不會進行驗證」（**全頁不得出現「自動凍結」「會自動」字樣**）；(b)「已凍結：7 筆案例（下限 5），凍結者：凍結者甲」且無警示；(c) 另有 `data-testid="si-heldout-warning"`，內容**逐字等於 `neNote`**，並接一句「這不會擋住凍結，只表示驗證結果不能當成通過」；(c2) 警示改用保底句「案例數低於下限，驗證結果只能是『無法評估』」；(d)「已凍結，案例數量不明」且無低於下限警示；各情境的標題為「評估集（用來驗證的考題）」，且**不顯示 `digest8`**
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_1`；預期突變：`n=min` 判成低於、(c) 不用 `neNote`、(a) 暗示自動凍結，皆紅
  - 驗收字樣：[AT_OK_966_9_1]
- **AT-966-9-2**（vitest｜同檔｜Unit｜AC-966-9、NFR-FV-4）評估集內容不外洩（金絲雀）。
  - Given `heldout` 物件另含合成的哨兵字串：`cases:["CANARY-CASE-7f3a"]`、`probes:"CANARY-PROBE"`、`digest:"sha256:CANARY"`、`digest8:"CANARY08"`、`files:{a:"CANARY-FILE"}`、`items:[…]`（皆為測試內合成字串，**不讀任何真實 SI 家目錄**）；`detail` 其他位置不含哨兵
  - When 切到每個分頁並取整個對話框 `textContent` 與 `outerHTML`
  - Then 兩者皆不含任何 `CANARY`（含 `digest8` 的哨兵）；評估集區塊只出現 W-F9 的七個欄位的呈現；網路請求只有 AT-966-6-3 規定的那一條；**此 AT 能變紅**：把元件改成 `Object.entries(heldout)` 全列即會出現哨兵
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_2`；預期突變：以 `Object.entries(heldout)` 全部列出、顯示 `digest8`，皆紅
  - 驗收字樣：[AT_OK_966_9_2]
- **AT-966-9-3**（vitest｜同檔｜Unit｜AC-966-9、W-F7）隔離試跑（沙盒）結果呈現。
  - Given `sandbox`：(a) `{applied:true,touchedOk:true,rollbackOk:true,failCode:null,failText:null}`；(b) `{applied:false,touchedOk:false,rollbackOk:true,failCode:"SANDBOX-NOT-APPLIED",failText:"修補套不上去，請退回或修訂提案"}`；(b2) 同 (b) 但 `failText` 為 null；(c) `null`
  - When 切到「評估集與驗證」
  - Then 區塊標題「隔離試跑（沙盒）」；(a)「已套用修補、只動到允許的檔案、回滾正常」；(b)「沒有通過：SANDBOX-NOT-APPLIED」並**逐字顯示 `failText`**；(b2)「沒有通過：SANDBOX-NOT-APPLIED（主機沒有提供白話說明）」；(b)(b2) 分項顯示三個布林為「是／否」；(c)「還沒有做隔離試跑」；`failCode` 以等寬字顯示
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_3`；預期突變：有 `failText` 仍顯示保底句、(c) 顯示成失敗，皆紅
  - 驗收字樣：[AT_OK_966_9_3]
- **AT-966-9-4**（vitest｜同檔｜Unit｜AC-966-9）驗證三步證據與結果。
  - Given `verify={verdict:"PASS",baselineRed:true,patchedGreen:true,mutatedRed:true,probesN:6,carrierProof:true,reasons:[]}`；另 FAIL（`patchedGreen:false`）、NE、`carrierProof:false`、`carrierProof:null`
  - When 檢視
  - Then 結果標籤文字為「通過」「未通過」「無法評估」（文字本身表達，不只靠顏色；前綴「結果：」）；三步逐項白話：「修補前確實重現症狀：是」「修補後症狀消失：是」「故意弄壞修補後症狀又出現：是」；「檢查項目數（探針）：6」；「驗證用的測量工具自我檢查：通過／沒通過／量不到」（`carrierProof` 為 true／false／null；**不顯示 `true`／`false` 原字**）；FAIL 時第二步為「否」且該行標示「這一步沒過」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_4`；預期突變：三步標籤與欄位錯位、結果只用顏色、顯示 `true`／`false` 原字，皆紅
  - 驗收字樣：[AT_OK_966_9_4]
- **AT-966-9-5**（vitest｜同檔｜Unit｜AC-966-9、W-F7）原因清單與保底。
  - Given `verify.reasons`：(a) `[{code:"HELDOUT-TOO-SMALL",text:"評估集案例數低於下限"}]`；(b) `[{code:"UNK-9"}]`、`[{code:"UNK-9",text:""}]`；(c) 空陣列且 `verdict:"PASS"`；(d) 空陣列且 `verdict:"NE"`；(e) 缺席
  - When 檢視
  - Then (a) 顯示碼（等寬）與 text；(b) 顯示「主機沒有提供白話說明（原因碼 UNK-9）。」；(c)「沒有任何保留原因」；(d)「主機沒有回報原因」；(e)「原因量不到」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_5`；預期突變：(d)(e) 同句、(b) 顯示空白，皆紅
  - 驗收字樣：[AT_OK_966_9_5]
- **AT-966-9-6**（vitest｜同檔｜Unit｜AC-966-9、NFR-FV-3）缺席的三種情形。
  - Given (a) `verify=null`；(b) `verify` 內 `baselineRed:null`、`patchedGreen` 缺席；(c) `heldout` 整個缺席
  - When 檢視
  - Then (a)「還沒有驗證結果」並接一句依「下一步」判斷的提示（沿 W-F6 來源序；無來源時不加提示）；(b) 該步顯示「量不到」（不是「否」）；(c) 評估集區塊顯示「評估集狀態量不到」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_6`；預期突變：null 布林顯示成「否」，紅
  - 驗收字樣：[AT_OK_966_9_6]
- **AT-966-9-E-1**（vitest｜同檔｜Unit｜AC-966-9）未知驗證結果。
  - Given `verify.verdict="WEIRD"`、`""`、缺席
  - When 檢視
  - Then 顯示「未知結果『WEIRD』」「量不到」；結果標籤元素**不含**成功樣式 class（`text-wg-success*`、`bg-wg-success*`）也不含失敗樣式 class；仍顯示三步證據
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_9_E_1`；預期突變：未知值落入預設成功樣式，紅
  - 驗收字樣：[AT_OK_966_9_E_1]
- **AT-966-10-1**（vitest｜同檔｜Unit｜AC-966-10）時間線取自 `detail.timeline`、依 `seq` 升冪、不另打請求。
  - Given `detail.timeline=[{seq:30,t:"2026-11-10T09:00:00+08:00",by:"掌舵者",kind:"dec",action:"核准"},{seq:12,t:"…",by:"巡邏器",kind:"prop",action:"提出提案"},{seq:21,…}]`
  - When 開詳情並切「時間線」
  - Then 列依 `seq` 升冪（12、21、30）顯示 `seq`、時間、`by`、`action` 四欄（`kind` 不顯示）；欄標題「序號」「時間」「誰」「做了什麼」；表格有 `<caption class="sr-only">提案事件時間線</caption>`；全程對 `/api/v1/issues/` 零請求
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_10_1`；預期突變：依輸入序顯示、改打議題端點，皆紅
  - 驗收字樣：[AT_OK_966_10_1]
- **AT-966-10-2**（vitest｜同檔｜Unit｜AC-966-10、NFR-FV-3）空與缺席。
  - Given `timeline=[]`；`timeline` 鍵缺席；`timeline=null`
  - When 切「時間線」
  - Then 空陣列＝「這個提案還沒有事件」；缺席與 null＝「時間線量不到」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_10_2`；預期突變：缺席顯示成「還沒有事件」，紅
  - 驗收字樣：[AT_OK_966_10_2]
- **AT-966-10-3**（vitest｜同檔｜Unit｜AC-966-10、W-F7）時間線被截短的說明。
  - Given `ne` 含 `{field:"proposals.PROP-SI-901.detail.timeline",reason:"TIMELINE-TRUNCATED",text:"事件太多，時間線只顯示最後 500 筆"}`；時間線 500 筆
  - When 切「時間線」
  - Then 表格上方顯示該 `ne` 項的 `text`（逐字）；500 列皆渲染；`ne` 項缺 `text` 時用保底句「主機沒有提供白話說明（原因碼 TIMELINE-TRUNCATED）。」
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_10_3`；預期突變：不顯示截短說明、自寫句子，皆紅
  - 驗收字樣：[AT_OK_966_10_3]
- **AT-966-10-E-1**（vitest｜同檔｜Unit｜AC-966-10）無法解析的時間與重複 `seq`。
  - Given `timeline` 含 `t:"昨天"`、`t:null`、兩筆 `seq:12`
  - When 切「時間線」
  - Then `t` 無法解析者原字串顯示（null 顯示「時間量不到」）；兩筆 `seq:12` 都顯示且保持輸入相對序（穩定排序）；不丟例外
  - 判定：`npx vitest run components/domain/si/SiProposalDetail.test.tsx -t AT_966_10_E_1`；預期突變：以 `seq` 去重，紅
  - 驗收字樣：[AT_OK_966_10_E_1]
- **AT-966-11-1**（vitest｜`SiPatrolCard.test.tsx`｜Unit｜AC-966-11、W-F11、W-F12）掛載位置、角色、請求次數。
  - Given 整個 `SiView` 以 `VIEWER_UI`、`OPERATOR_UI`、`ADMIN_UI` 各渲染；`patrol` 端點回 `PATROL()`
  - When 載入；按頁首「重新整理」；以可控時鐘替身（見 §5.6）前進 60 分鐘
  - Then 三種角色皆有 `data-testid="si-patrol-card"` 區塊，位置在狀態橫幅之後、「研究來源」說明列之前（DOM 順序）；載入時 `GET /api/v1/si/patrol` 恰 1 次；按「重新整理」後累計 2 次；**前進 60 分鐘網路請求仍為 2 次**（無輪詢；畫面時間由本地每分鐘重算，不發請求）；另以靜態斷言 `SI_QUERY_OPTIONS.refetchInterval === false` 且 `patrol` 查詢沿用它（「不輪詢」＝靜態斷言加請求數不變，兩者並用）；視窗聚焦不重抓；區塊標題「巡邏狀態」；區塊內無 `button`（除「這一輪做了什麼」展開切換，其 `aria-expanded` 存在）
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_1`；預期突變：只對 ADMIN 渲染、加 `refetchInterval`，皆紅
  - 驗收字樣：[AT_OK_966_11_1]
- **AT-966-11-2**（vitest｜同檔｜Unit｜AC-966-11、W-F5）新鮮呈現與時間前進。
  - Given `generatedAt` 比 `readAt`（＝`NOW`）早 3 分鐘、`heartbeatMinutes:15`、`off:false`；可控時鐘替身（`tests/helpers/siClock.ts`，見 §5.6）
  - When 檢視；再把時間前進 10 分鐘（不重抓）
  - Then 初始顯示「上次心跳：3 分鐘前」、一個 `<time dateTime=generatedAt>`、「巡邏每 15 分鐘一次」、「資料讀取於 <readAt>」；**無**警示區；狀態標籤為「巡邏正常」（文字）；前進 10 分鐘後相對時間變為「13 分鐘前」（**不得停在 3 分鐘前**），仍無警示、網路請求次數不變
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_2`；預期突變：相對時間固定為讀取當時的值，紅
  - 驗收字樣：[AT_OK_966_11_2]
- **AT-966-11-3**（vitest｜同檔｜Unit｜AC-966-11、W-F5）過時警示邊界與自動轉警示。
  - Given 週期 15；`generatedAt` 比 `NOW` 早 35 分 00 秒、35 分 01 秒；週期 60 且早 125 分 01 秒；另一情境：早 3 分鐘、載入後以可控時鐘替身前進到抵達後第 32 分 00 秒再前進 1 分鐘（不重抓）
  - When 檢視
  - Then 35:00 無警示；35:01 出現 `data-testid="si-patrol-stale"`（`role="status"`）文字「巡邏可能沒在跑：已超過 35 分鐘沒有新的回報（巡邏每 15 分鐘一次）。可能原因：電腦睡眠、排程任務被移除、巡邏被環境變數暫停。請按『重新整理』取得最新回報。」；週期 60 的情境限度顯示 125；警示與狀態標籤「巡邏可能沒在跑」並存（文字，不只靠顏色）；仍顯示快照內容並註明「以下是 X 分鐘前的回報」；另一情境在 32:00 無警示、再過 1 分鐘（35:01 起算）**自動出現警示**，網路請求次數不變
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_3`；預期突變：邊界改 `>=`、過時時隱藏快照內容、不隨時間重算，皆紅
  - 驗收字樣：[AT_OK_966_11_3]
- **AT-966-11-4**（vitest｜同檔｜Unit｜AC-966-11）環境變數暫停。
  - Given `off:true`，`props`、`runs`、`ingest` 皆為空陣列
  - When 檢視
  - Then 顯示「巡邏已暫停（環境變數 AUTOSDD_SI_PATROL_OFF 有設定）」，**不**顯示「目前沒有需要巡邏推進的提案」（空陣列在暫停時不代表沒事）；上次心跳與新鮮度判定仍照常；`off` 缺席視為 false，`off` 為字串或其他型別視為「量不到暫停狀態」並顯示該字樣
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_4`；預期突變：暫停時照常顯示「沒有提案」，紅
  - 驗收字樣：[AT_OK_966_11_4]
- **AT-966-11-5**（vitest｜同檔｜Unit｜AC-966-11、NFR-FV-3）快照缺席畫面。
  - Given 端點回 503 `si_unavailable`、`cause=report_missing`
  - When 檢視
  - Then 顯示標題「還沒有收到巡邏回報」與三個白話可能原因（巡邏任務還沒安裝、巡邏還沒跑過第一次、主機的回報目錄是空的）與「按『重新整理』再看一次」；**不**用錯誤樣式（無 `role="alert"`）、**不**顯示重試鈕以外的操作；整頁其他區塊不受影響；也**不**顯示任何「沒有提案」「沒有運轉」字樣
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_5`；預期突變：缺席時渲染空卡片、渲染通用錯誤，皆紅
  - 驗收字樣：[AT_OK_966_11_5]
- **AT-966-11-6**（vitest｜同檔｜Unit｜AC-966-11）未掛載畫面。
  - Given 端點回 503 `cause=report_dir_unset`
  - When 檢視
  - Then 顯示「這個部署沒有掛載巡邏回報目錄」與一句說明「看不到巡邏狀態，其他自我進化功能照常；要看請照部署說明加上回報目錄」；與 AT-966-11-5 的標題與說明**不同**（兩種缺席不混為一談）；沒有重試鈕（重試無意義）
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_6`；預期突變：兩種缺席同一畫面，紅
  - 驗收字樣：[AT_OK_966_11_6]
- **AT-966-11-7**（vitest｜同檔｜Unit｜AC-966-11）壞檔與其他失敗。
  - Given 端點依序回：503 `report_invalid`（detail 含檔名）、503 `report_unreadable`、503 `nonzero_rc`、502、504、網路錯誤
  - When 檢視
  - Then 前兩者顯示標題「巡邏回報檔有問題」並逐字顯示 `cause` 與 `detail`（等寬）、「重試」鈕；其餘走既有 `SiError`（原因逐字）；任何失敗都不顯示舊快照資料（`gcTime: 0`）；重試按一次恰多 1 次請求
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_7`；預期突變：壞檔時顯示上次快取內容，紅
  - 驗收字樣：[AT_OK_966_11_7]
- **AT-966-11-E-1**（vitest｜同檔｜Unit｜AC-966-11、W-F5）缺週期與時鐘異常。
  - Given (a) `heartbeatMinutes` 缺席／0／-5／`"15"`／NaN；(b) `generatedAt` 比 `readAt` 晚 6 分鐘；(c) `generatedAt` 無法解析（`"昨天"`）；(d) `readAt` 缺席
  - When 檢視
  - Then (a)「無法判斷是否過時：快照沒有巡邏週期」且**不顯示**「巡邏正常」也不顯示過時警示；(b)「快照時間在未來，電腦時鐘可能不同步」；(c)「上次心跳時間量不到」；(d) 以瀏覽器時間計算並註明「（用瀏覽器時間估算）」
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_E_1`；預期突變：缺週期時當成新鮮，紅
  - 驗收字樣：[AT_OK_966_11_E_1]
- **AT-966-11-E-2**（vitest｜同檔｜Unit｜AC-966-11、NFR-FV-4）惡意字串純文字。
  - Given `PATROL()` 中 `report.props[0].text`、`report.steps[0].result`、`report.push.text`、`report.runs.waiting[0].text`、`report.schedule.lastSkip.text`、`report.ingest[0].text`、`report.generatedAt`（非法字串）含 `<script>`、`<img onerror>`、Markdown、`javascript:` 連結
  - When 檢視
  - Then 全為字面文字；DOM 無注入元素；`window` 無副作用
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_11_E_2`；預期突變：用 `dangerouslySetInnerHTML`，紅
  - 驗收字樣：[AT_OK_966_11_E_2]
- **AT-966-12-1**（vitest｜同檔｜Unit｜AC-966-12、W-F7）提案卡住原因清單。
  - Given `PATROL({props:[{id:"PROP-SI-901",state:"approved",code:"NO-HELDOUT",who:"主機管理者",text:"尚未凍結評估集；需有人用 heldout-freeze，巡邏器不會自己湊"},{id:"PROP-SI-902",state:"verified",code:"WAIT-PROMOTE-DECISION",who:"掌舵者",text:"驗證通過，等你決定是否晉升"}]})`
  - When 檢視
  - Then 區塊「每個提案現在卡在哪」依輸入序列出兩列：提案編號（等寬）、狀態、「等：主機管理者」「等：掌舵者」標籤（文字）、`text` 逐字、原因碼（小字等寬）；**不出現任何暗示會自動凍結的句子**（`NO-HELDOUT` 列的「該誰處理」就是主機管理者）；`props=[]`（且未暫停）顯示「目前沒有需要巡邏推進的提案」；提案編號可點，點擊開啟該提案詳情對話框（若該提案在已載入提案清單中；否則為純文字）
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_1`；預期突變：改變順序、空陣列顯示成「量不到」、把 `NO-HELDOUT` 寫成等無人運轉，皆紅
  - 驗收字樣：[AT_OK_966_12_1]
- **AT-966-12-2**（vitest｜同檔｜Unit｜AC-966-12、W-F7）未知等待對象與未知碼保底。
  - Given `props` 含 `who:"外星人"`、`who` 缺席、`text` 缺席、`code` 缺席、`state` 缺席，以及根層後加的碼 `COMMIT-LEFTOVER`、`COMMIT-RECORD-FAILED`（`who:"主機管理者"`、`text` 為根層白話；Console 不認得這些碼也必須逐字顯示該 `text`）
  - When 檢視
  - Then 「等：未知值『外星人』」「等：量不到」；`text` 缺席時顯示「主機沒有提供白話說明（原因碼 <code>）。」；`code` 與 `text` 皆缺席顯示「主機沒有提供原因。」；`state` 缺席顯示「狀態量不到」；任何情況不顯示成功樣式、不丟例外；`COMMIT-LEFTOVER`、`COMMIT-RECORD-FAILED` 兩列只顯示碼與 `text`，無任何特例分支
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_2`；預期突變：缺 `who` 顯示成「無」，紅
  - 驗收字樣：[AT_OK_966_12_2]
- **AT-966-12-3**（vitest｜同檔｜Unit｜AC-966-12、W-F7）進行中的運轉與第二波值不當成已知。
  - Given `runs.live=[{run:"RUN-SI-901",purpose:"scheduled",startedAt:<NOW 前 12 分>,wallDueAt:<NOW 後 48 分>},{run:"RUN-SI-902",purpose:"console",…},{run:"RUN-SI-903",purpose:"manual",…}]`；另情境：`live=[]`；`purpose:"freeze"`、`"zzz"`；`live` 缺席；`runs.queued=[{purpose:"revise",target:"PROP-SI-902",why:"x"}]`（W1 不應出現的元素）
  - When 檢視
  - Then 顯示兩個短句「進行中：RUN-SI-901（排程啟動）。」「12 分鐘前開始，預計最晚 48 分鐘後結束。」（每句不超過可讀性鎖的 40 字）；`console`＝「從畫面按『立即啟動』」、`manual`＝「手動啟動」；`freeze`、`zzz` 一律「未知值『…』」；`live=[]`（且 `waiting` 也空）＝「目前沒有進行中的運轉」；`live` 缺席＝「進行中的運轉量不到」；`runs.queued` 的內容**完全不渲染**（畫面不出現「revise」「PROP-SI-902」「排隊」字樣）
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_3`；預期突變：把 `freeze` 當已知標籤、渲染 `queued`，皆紅
  - 驗收字樣：[AT_OK_966_12_3]
- **AT-966-12-4**（vitest｜同檔｜Unit｜AC-966-12）步驟與入帳摘要。
  - Given `steps=[{step:"入帳",result:"入帳 1、拒收 0"},{step:"推進",result:"PROP-SI-901 跳過：NO-HELDOUT"}]`；`ingest` 有 2 筆（1 筆 `rejected` 永久、1 筆 `deferred`）
  - When 檢視；按「這一輪做了什麼」展開
  - Then 預設收合（`aria-expanded=false`）；展開後依序列出兩步與結果逐字；入帳摘要顯示「有 2 筆稽核檔被拒收或延後」；`ADMIN_UI` 下另有按鈕「看待入帳清單」（捲動到並聚焦 `data-testid="si-writes-panel"`）；`VIEWER_UI`／`OPERATOR_UI` 只有摘要文字、無該按鈕（因待入帳面板只對 ADMIN 存在）；`ingest=[]`＝「這一輪沒有被拒收的稽核檔」；`steps` 缺席＝「這一輪的步驟量不到」
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_4`；預期突變：非 ADMIN 也出按鈕、預設展開，皆紅
  - 驗收字樣：[AT_OK_966_12_4]
- **AT-966-12-5**（vitest｜同檔｜Unit｜AC-966-12、W-F7）推送八態與未知態。
  - Given 九份 `push`：根層八態（見 AT-966-5-9 的夾具，內容取自根層 TCS-P7 附錄 A.4）加未知 `state:"skipped"`；另 `enabled:false` 並 `state:"off"`
  - When 檢視「自動推送」區
  - Then 每份的顯示句與 `pushView` 逐字相同（元件不自行組句、不自建狀態對照）；`ok` 另顯示 `<time>`；`failed` 顯示嘗試次數；`blocked` 與 `failed` 使用警示樣式並帶文字前綴（「需要處理：」），`ok` 帶「完成：」，不只靠顏色；`waiting-login` 顯示根層句「等使用者登入後自動推送」；未知態顯示「未知的推送狀態『skipped』」；標題「自動推送」並有一句固定說明「推送由主機自動執行，這裡只顯示狀態」
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_5`；預期突變：元件另寫一套文案、把 `skipped` 當已知、少一種狀態，皆紅
  - 驗收字樣：[AT_OK_966_12_5]
- **AT-966-12-7**（vitest｜同檔｜Unit｜AC-966-12、W-F13）為什麼沒有啟動運轉：排程狀態與等待中的運轉。
  - Given `PATROL({schedule:…,runs:{waiting:…}})`：(a) `schedule={enabled:true,current:{code:"SKIP-RUN-OPEN",text:"已有未關運轉（RUN-SI-901），排程與立即啟動都會等它關閉"},lastSkip:{seq:99,t:"2026-11-11T13:45:00+08:00",code:"SKIP-RUN-OPEN",text:"已有未關運轉（RUN-SI-901）…",auditRef:null}}`；(b) 同 (a) 但 `lastSkip.auditRef="a1000000-0000-4000-8000-000000000001"`；(c) `enabled:false`＋`current.text:"自動演化排程目前停用（立即啟動仍可用）"`；(d) `schedule:null` 且 `off:true`；(e) `current:null`；(f) `runs.waiting=[{run:"RUN-SI-902",code:"SKIP-OTHER-DRIVER",text:"近期有人在互動視窗工作，巡邏器先不開運轉"}]`；(g) `waiting=[]`；(h) `waiting` 缺席
  - When 檢視「為什麼沒有啟動運轉」區（標題固定）
  - Then (a) 顯示「排程：啟用中」「目前狀態：<current.text>」「最近一次略過：<t> <lastSkip.text>」，文字逐字取自根層；(b) 另有一句「這次略過的是你從畫面按的『立即啟動』（稽核編號 a1000000-…）」；(c) 顯示停用句；(d) 顯示「巡邏已暫停，沒有排程資訊」（不顯示成「排程停用」）；(i) `schedule:null` 而 `off:false` 顯示「這份回報沒有排程資訊」（不說成暫停）；(e)「目前這一格的排程狀態量不到」；(f) 顯示「RUN-SI-902 等待中：近期有人在互動視窗工作，巡邏器先不開運轉」；(g)「目前沒有在等待啟動的運轉」；(h)「等待中的運轉量不到」；`code` 以小字等寬附於各句；`text` 缺席時用保底句；**全區零按鈕**（第二波才有取消）；`SKIP-RUN-OPEN` 句尾若根層帶「第二波起可由 Console 處理」字樣，Console 逐字顯示、不另加承諾
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_7`；預期突變：`auditRef` 非 null 時不加註、把 `schedule:null` 顯示成停用、渲染按鈕，皆紅
  - 驗收字樣：[AT_OK_966_12_7]
- **AT-966-12-6**（vitest｜同檔｜Unit｜AC-966-12、W-F11）無推送按鈕與憑證遮罩。
  - Given `push.text` 為 `"push "`＋內嵌帳密的 https 網址（執行期拼出：`https://`＋`<帳號>`＋`:`＋`<密碼>`＋`@github.com/o/r.git`，帳號取 user、密碼取 token123）＋`" failed"`；`props[0].text` 含另一個內嵌帳密的網址（執行期拼出：`https://`＋`<帳號>`＋`:`＋`<密碼>`＋`@c/d`，帳號取 a、密碼取 b）
  - When 檢視；掃描卡片內所有 `button`、`a`、`[role=button]`
  - Then 沒有任何可存取名稱含「推送」「推」「push」（不分大小寫）的互動元素（「自動推送」只出現在標題與說明文字）；`token123`、`user:` 不出現在 DOM；顯示為 `https://***@github.com/o/r.git`；靜態：`SiPatrolCard.tsx` 不 import 任何 `usePost*`、`useWrite`、`postSi*`
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_6`；預期突變：加「立即推送」鈕、不遮罩，皆紅
  - 驗收字樣：[AT_OK_966_12_6]
- **AT-966-12-E-1**（vitest｜同檔｜Unit｜AC-966-12、NFR-FV-3）段落缺席＝量不到，與 `truncated`。
  - Given `report` 只有 `{schemaRev:1,generatedAt:…}`（其餘全缺）；另一情境 `truncated:true` 的完整快照
  - When 檢視
  - Then 「每個提案現在卡在哪」「進行中的運轉」「為什麼沒有啟動運轉」「這一輪做了什麼」「自動推送」五區各顯示對應的「…量不到」；**各區內文**（斷言範圍＝各區去掉固定區塊標題與標題旁固定說明後的文字；區塊標題「為什麼沒有啟動運轉」本身含「沒有」，不納入比對）不含「沒有」「無」字樣；上次心跳區仍正常；`truncated:true` 時卡片頂端顯示「這份回報太長，被截短了，清單可能不完整」，`false` 或缺席時不顯示
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_E_1`；預期突變：缺席當空陣列、忽略 `truncated`，皆紅
  - 驗收字樣：[AT_OK_966_12_E_1]
- **AT-966-12-E-2**（vitest｜同檔｜Unit｜AC-966-12）兩百個提案的捲動區。
  - Given `props` 200 筆
  - When 檢視
  - Then 200 列全部渲染；清單容器含 `max-h-` 與 `overflow-y-auto` class 且可鍵盤聚焦（`tabIndex=0`、有 `aria-label`）；頁面其他區塊位置不被推走（卡片本身高度受限）
  - 判定：`npx vitest run components/domain/si/SiPatrolCard.test.tsx -t AT_966_12_E_2`；預期突變：無捲動容器，紅
  - 驗收字樣：[AT_OK_966_12_E_2]
- **AT-966-13-1**（vitest｜`SiWritesPanel.test.tsx`（新）｜Unit｜AC-966-13、W-F10）永久拒收。
  - Given `ADMIN_UI`；對帳 `items` 有一筆待入帳（`auditRef=A1`、`kind:"decide"`、`dkind:"promote"`、`ingested:false`）；`PATROL({ingest:[{auditRef:"A1",kind:"decide",status:"rejected",code:"STALE-CARD",text:"提案卡面已更新，你按的是舊卡面；請看新卡面重新決定",permanent:true}]})`（新鮮）
  - When 檢視待入帳列
  - Then 該列除「待入帳」外另有「被拒收」標籤（文字）、原因碼 `STALE-CARD`（等寬）、`text` 逐字、「需要人處理：這筆不會自動入帳。請看最新卡面後重新送出決定；目前畫面沒有取消功能，這筆會留在清單。」；列仍保有「入帳指令」鈕與原有欄位
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_1`；預期突變：不顯示碼、說會自動入帳，皆紅
  - 驗收字樣：[AT_OK_966_13_1]
- **AT-966-13-2**（vitest｜同檔｜Unit｜AC-966-13、W-F10）暫時延後、重複送出與不明。
  - Given 五筆待入帳與對應的 `ingest` 項：`status:"deferred"`＋`permanent:false`＋`code:"AUDIT-KEY-MISSING"`；`status:"rejected"`＋`permanent:false`；`status:"rejected"`＋`permanent` 缺席；`permanent` 為字串 `"yes"`；`status:"rejected"`＋`code:"AUDIT-REF-REUSED"`＋`permanent:true`（根層定稿：重複送出已入帳的編號，不會再入帳）
  - When 檢視
  - Then 第一筆「延後」＋「條件解除後下一次心跳會自動入帳」；第二筆「被拒收」＋同上自動入帳句；第三筆與字串者「是否會自動入帳不明」；第五筆「被拒收」＋「需要人處理」句（與永久拒收相同）並逐字顯示根層 `text`；`status` 為未知值者標籤為「未知狀態『X』」
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_2`；預期突變：`permanent` 缺席當 true、`AUDIT-REF-REUSED` 當自動入帳，皆紅
  - 驗收字樣：[AT_OK_966_13_2]
- **AT-966-13-3**（vitest｜同檔｜Unit｜AC-966-13）無對應項與快照過時。
  - Given 待入帳 A2 在 `ingest[]` 無對應項；(a) 快照新鮮；(b) 快照過時（早於 `NOW` 40 分）
  - When 檢視
  - Then (a) A2 列只有「待入帳」與一句「主機還沒處理這筆」；(b) 另在面板層級顯示「巡邏回報已過時（40 分鐘前）：下面的原因可能已經改變」，且過時時 A1 的拒收原因仍顯示
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_3`；預期突變：過時時隱藏拒收原因，紅
  - 驗收字樣：[AT_OK_966_13_3]
- **AT-966-13-4**（vitest｜同檔｜Unit｜AC-966-13、NFR-FV-3）回報量不到的四種原因。
  - Given 快照端點依序回 503 `report_dir_unset`、`report_missing`、`report_invalid`、502（不可達）
  - When 檢視面板
  - Then 面板層級各顯示一次「拒收原因量不到：這個部署沒有掛載巡邏回報目錄」「…：還沒有收到巡邏回報」「…：巡邏回報檔有問題」「…：連不上後端服務」；各待入帳列維持「待入帳」（不顯示「被拒收」也不顯示「主機還沒處理」）；既有待入帳功能（入帳指令展開）不受影響
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_4`；預期突變：量不到時各列顯示「主機還沒處理這筆」、出現「Bridge」字樣，皆紅
  - 驗收字樣：[AT_OK_966_13_4]
- **AT-966-13-5**（vitest｜同檔｜Unit｜AC-966-13、W-F10）最近已入帳（常駐顯示、**不加展開鈕**）。
  - Given 對帳 `items` 有 8 筆 `ingested:true`（時間各異）與 2 筆待入帳；另情境 `ingested:null`（量不到）；另情境 `ingested:true` 為 0 筆
  - When 檢視面板（不需任何操作）
  - Then 待入帳清單之下有一段 `data-testid="si-recent-ingested"`，標題「最近已入帳（8）」並註明「只列最近 5 筆」，內容直接顯示（**沒有展開／收合按鈕**，面板內按鈕集合與本鍵實作前相同——這是刻意的設計，避免動到既有 AT-935-3-2、AT-951-4-1 的面板按鈕清點），只列時間最新的 5 筆（`RECENT_INGESTED_SHOWN`），每列有「已入帳」標籤、種類標籤、對象、時間、稽核編號；`ingested:null` 時整段不出現（沿既有「量不到」訊息）；0 筆時整段不出現；已入帳列不出現入帳指令鈕；整段內無任何 `button`
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_5`；預期突變：列出全部、`null` 當已入帳、加上展開鈕，皆紅
  - 驗收字樣：[AT_OK_966_13_5]
- **AT-966-13-6**（vitest｜同檔｜Unit｜AC-966-13、W-F10）只結合未入帳列。
  - Given 一筆 `ingested:true` 的列 A3，快照 `ingest[]` 仍含 A3 的舊拒收項（快照比帳本舊）
  - When 檢視
  - Then A3 只顯示在「最近已入帳」且**沒有**任何拒收標籤；待入帳清單不含 A3
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_6`；預期突變：對所有列結合，紅
  - 驗收字樣：[AT_OK_966_13_6]
- **AT-966-13-E-1**（vitest｜同檔｜Unit｜AC-966-13）重複稽核編號與缺原因碼。
  - Given `ingest` 有兩筆同 `auditRef` 的項（第一筆 `STALE-CARD`、第二筆 `DIGEST-MISMATCH`）；另一筆項無 `code` 無 `text`
  - When 檢視
  - Then 取第一筆（`STALE-CARD`）；無 `code`／`text` 者顯示「主機沒有提供原因。」與狀態標籤；不丟例外
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_E_1`；預期突變：取最後一筆，紅
  - 驗收字樣：[AT_OK_966_13_E_1]
- **AT-966-13-E-2**（vitest｜同檔｜Unit｜AC-966-13、W-F0）對帳量不到與既有行為回歸。
  - Given (a) `reconcile.status="NOT-EVALUABLE"`（`ingested` 皆 null）；(b) 既有 `AT_935` 系列的待入帳、被取代群組、orphan 警示夾具
  - When 檢視
  - Then (a) 沿既有訊息「對帳量不到…」且**不結合**拒收原因、無「最近已入帳」；(b) 待入帳列、「入帳指令」展開、「另有 N 筆已被取代」切換、對帳警示 `si-write-alerts` 的 `data-testid` 與文字逐字不變
  - 判定：`npx vitest run components/domain/si/SiWritesPanel.test.tsx -t AT_966_13_E_2`；預期突變：改動既有 testid、(a) 仍列已入帳，皆紅
  - 驗收字樣：[AT_OK_966_13_E_2]
- **AT-966-14-1**（vitest｜`SiFlowRoles.test.tsx`（新）｜Unit｜AC-966-14、NFR-FV-1、W-F11）VIEWER 與 OPERATOR 完整旅程。
  - Given 以 `VIEWER_UI` 與 `OPERATOR_UI` 各渲染 `SiView`
  - When 載入→開 `P901` 詳情→逐一切五分頁→展開 diff→按下載→點來源觀察跳轉→切到時間線→關閉→按「重新整理」
  - Then 全程網路請求集合 ⊆ {`GET status`、`observations`、`proposals`、`proposals/{id}`、`patrol`}（逐條斷言路徑；**不含 `issues`**）；**零個非 GET**；**零個** `console-writes`；整個畫面無任何寫入控件（沿 `AT_935_3_2` 的唯讀按鈕白名單，並加入 `si-detail-open-*` 與詳情內顯示切換鈕）；巡邏卡可見
  - 判定：`npx vitest run components/domain/si/SiFlowRoles.test.tsx -t AT_966_14_1`；預期突變：非 ADMIN 也打 `console-writes`、詳情內出現決定鈕、改打議題端點，皆紅
  - 驗收字樣：[AT_OK_966_14_1]
- **AT-966-14-2**（vitest｜同檔｜Unit｜AC-966-14、NFR-FV-5）ADMIN 既有流程回歸。
  - Given 以 `ADMIN_UI` 渲染
  - When 走既有決定流程（對 `P901` 開決定對話框、送 `promote`）、排程面板、立即啟動、觀察新增，再開詳情對話框並關閉
  - Then 既有對話框行為與收據文案逐字不變；詳情對話框內**沒有**決定、核准、晉升等寫入鈕；寫入成功後使全部 SI 查詢失效重取時，`patrol` 查詢也被重取一次（屬 `qk.siAll` 家族）
  - 判定：`npx vitest run components/domain/si/SiFlowRoles.test.tsx -t AT_966_14_2`；預期突變：`qk.siPatrol` 不在 `siAll` 家族，紅
  - 驗收字樣：[AT_OK_966_14_2]
- **AT-966-14-3**（vitest｜同檔｜Unit｜AC-966-14、W-F11）新元件靜態無寫入引用。
  - Given 原始碼 `SiProposalDetail.tsx`、`SiDiffView.tsx`、`SiPatrolCard.tsx`、`lib/domain/siFlow.ts`
  - When 掃描 import 與 JSX
  - Then 不 import `usePost*`、`useWrite`、`postSi*`、`fetch`、`XMLHttpRequest`；不含 `<form`、`<input`、`<textarea`、`type="submit"`；`siFlow.ts` 不 import React 與任何 `lib/api/*`（純函式）
  - 判定：`npx vitest run components/domain/si/SiFlowRoles.test.tsx -t AT_966_14_3`；預期突變：元件 import `usePostSiDecide`，紅
  - 驗收字樣：[AT_OK_966_14_3]
- **AT-966-14-E-1**（vitest｜同檔｜Unit｜AC-966-14、W-F11）角色一視同仁與 401。
  - Given 同一份 `DETAIL(full)` 與 `PATROL()`；三種角色各渲染；另 `patrol` 與詳情端點回 401
  - When 比對三角色看到的詳情與巡邏卡文字；觸發 401
  - Then 三角色的詳情對話框與巡邏卡（不含 ADMIN 專屬的「看待入帳清單」鈕）`textContent` 逐字相同（無角色遮蔽）；401 走既有全域處理（`AuthProvider` 的登出導向），元件不自訂處理也不顯示技術字樣
  - 判定：`npx vitest run components/domain/si/SiFlowRoles.test.tsx -t AT_966_14_E_1`；預期突變：對 VIEWER 隱藏 patch，紅
  - 驗收字樣：[AT_OK_966_14_E_1]
- **AT-966-15-1**（vitest｜`lib/help/content.test.ts`、`lib/help/pageFacts.test.ts`、`lib/help/readability` 既有測試｜Unit｜AC-966-15）說明頁含四段與五個名詞的白話釋義，且落在既有說明頁結構內（`PageHelp` 只有 `purpose`／`steps`／`fields`／`states`／`sourceFiles`，**不新增名詞表結構**）。
  - Given `lib/help/self-improving.ts`（本鍵修改後；由前端開發者實作）
  - When 跑既有三道鎖（`content.test.ts` 的欄位雙向、`pageFacts.test.ts` 的 `sourceFiles` 與事實雙向、可讀性鎖），並以 `HELP_PAGES["self-improving"]` 讀取
  - Then (a) `fields[].name` 含四段標題「提案詳情」「下一步」「巡邏狀態」「自動推送」，以及「詳情」「變更內容」「提案本文」「評估集與驗證」「時間線」「上次心跳」「巡邏可能沒在跑」「為什麼沒有啟動運轉」，皆逐字取自畫面字樣（本鍵新增欄位共 12 個）；(b) 五個名詞的白話釋義各落在既有結構內，以字串片段機械判定（比對 `purpose`、`steps`、`fields[].meaning` 串接後的文字）：「評估集（用來驗證的考題）」、「隔離試跑（沙盒）」、「檢查項目（探針）」、「巡邏快照」（出現在「巡邏狀態」欄位的釋義內，並附半句白話，例如「巡邏器每個心跳留下的回報檔」）、「下一步」（出現在欄位名，且其釋義說明「現在輪到誰做什麼」）；沙盒與探針只准以括號形態出現；(c) `sourceFiles` 含 `SiProposalDetail.tsx`、`SiDiffView.tsx`、`SiPatrolCard.tsx`；(d) 全段不得出現「自動凍結」「會自動修訂」「按鈕推送」「立即推送」等第二波或不存在的功能字樣；(e) 三道鎖全綠且既有 SI 說明字樣不退步
  - 判定：`npx vitest run lib/help -t AT_966_15_1`（測試檔內新案含此底線形；另整目錄 `npx vitest run lib/help` 全綠）；預期突變：少一段、欄位名與畫面不一致、說明暗示自動凍結、拿掉「檢查項目（探針）」或「巡邏快照」片段，皆紅
  - 驗收字樣：[AT_OK_966_15_1]
- **AT-966-15-2**（vitest｜`lib/domain/siFlow.test.ts`｜Unit｜AC-966-15）新字串可讀性鎖與禁用技術詞。
  - Given `siFlow.ts` 匯出 `SI_FLOW_TEXTS`（所有固定句、標籤、保底句模板的物件常數）；元件內的固定句一律取自此物件（元件原始碼不含寫死的中文句子，掃描判定）
  - When 逐句過 `lib/help/readability.ts` 現行規則（句長、禁用詞、國高中程度；以該檔匯出的檢查函式為準，不另寫規則），並另外檢查禁用詞表
  - Then 全部通過（**鎖只管 Console 自己寫的固定句與保底句模板**；根層在執行期提供的白話——`text`、`neNote`、`failText`、`ne[].text`、`push.text` 等——Console 逐字顯示、不得改寫，因此**明確豁免**，不進 `SI_FLOW_TEXTS`；Console 組合句〔如運轉列、相對時間句〕必須拆成每句不超過 40 字，含佔位值代入後仍成立，代入值取實際可能的最長形態，例如完整的運轉編號）；每個值為非空字串；不含「null」「undefined」「NaN」「object」字樣；**不含未經說明的技術詞**：`Bridge`、`carrierProof`、`probe`、`sandbox`、`digest`、`schema`、`payload`、`HMAC`（「沙盒」「探針」只准以「隔離試跑（沙盒）」「檢查項目（探針）」的括號形態出現）；含 `{…}` 佔位者以測試值代入後再檢查
  - 判定：`npx vitest run lib/domain/siFlow.test.ts -t AT_966_15_2`；預期突變：塞進一句超長艱澀句、保底句出現「Bridge」，皆紅
  - 驗收字樣：[AT_OK_966_15_2]
- **AT-966-15-E-1**（vitest｜`SiFlowRoles.test.tsx`｜Unit｜AC-966-15）垃圾輸入不洩漏技術字樣。
  - Given 以固定種子（`seed=966`）產生 50 組垃圾 `PATROL`／`DETAIL`（隨機把任一欄位換成 null、undefined、數字、布林、物件、陣列、超長字串、`NaN`）；渲染詳情對話框五分頁與巡邏卡
  - When 檢視全部可見文字
  - Then 每組皆不丟例外；可見文字不含 `null`、`undefined`、`NaN`、`[object Object]`、`Invalid Date`；每個不確定處都顯示「量不到」類字樣
  - 判定：`npx vitest run components/domain/si/SiFlowRoles.test.tsx -t AT_966_15_E_1`；預期突變：直接 `{value}` 渲染未驗型別的欄位，紅
  - 驗收字樣：[AT_OK_966_15_E_1]
- **AT-966-16-1**（Playwright｜`self-improving-flow.mock.spec.ts`｜E2E｜AC-966-16）旅程與無主控台錯誤。
  - Given `E2E_MODE=standalone`（production 建置）；spec 內自帶 `/api/v1/si/**` 路由替身（本鍵不打議題端點）（唯讀資料取既有 SI 黃金檔，巡邏與詳情夾具取 `tests/e2e/siFlowFixtures.ts` 的建構函式）；ADMIN 登入
  - When 開 `/self-improving`→看巡邏卡→開 `P901` 詳情→切五分頁→在變更內容按「展開全部」→按「下載 patch 檔」（攔截下載事件）→跳轉來源觀察→關閉
  - Then 全程 `collectConsoleErrors` 為空；巡邏卡顯示「上次心跳：N 分鐘前」；下載檔名 `PROP-SI-901-r2.patch` 且內容等於夾具；跳轉後觀察列高亮；請求記錄中**無非 GET 的 `/api/v1/si/**`**
  - 判定：`npx playwright test tests/e2e/self-improving-flow.mock.spec.ts -g AT_966_16_1`（先 `npm run build`，`E2E_MODE=standalone`）；預期突變：任一元件拋例外、下載檔名錯，皆紅
  - 驗收字樣：[AT_OK_966_16_1]
- **AT-966-16-2**（Playwright｜同檔｜E2E｜AC-966-16、NFR-FV-6）三寬度 axe 與溢出。
  - Given 寬度**取自既有無障礙 E2E 的同一常數 `RESEARCH_WIDTHS`**（現值 1440／1000／600；若該常數尚未匯出，實作者把它搬到 `tests/e2e/a11y.ts` 匯出並讓 `a11y.mock.spec.ts` 與本 spec 同源引用，**不在本 spec 另立數字**）；情境：巡邏卡新鮮、過時、缺席（`report_missing`）、未掛載（`report_dir_unset`）、含「為什麼沒有啟動運轉」與推送八態中的 `blocked`；詳情對話框的「變更內容」（含 400 行視窗與展開）、「評估集與驗證」（低於下限警示）、「時間線」；ADMIN 寫入面板含拒收原因列
  - When 逐情境 `expectNoA11yViolations`（serious／critical 為零；沿 `a11y.ts`）並量測 `document.documentElement.scrollWidth <= clientWidth`，且對話框與巡邏卡自身 `scrollWidth <= clientWidth`（diff 長行的捲動限於其內部容器）
  - Then 全部零違規、零橫向溢出；對比度達標（過時警示與「被拒收」標籤的文字對比 ≥ 4.5）
  - 判定：`npx playwright test tests/e2e/self-improving-flow.mock.spec.ts -g AT_966_16_2`；預期突變：警示用低對比色、diff 容器不捲動導致頁面溢出、本 spec 另寫寬度數字，皆紅（最後一項由 QA 以原始碼比對）
  - 驗收字樣：[AT_OK_966_16_2]
- **AT-966-16-3**（Playwright｜同檔｜E2E｜AC-966-16）對話框鍵盤與焦點。
  - Given 詳情對話框已開
  - When 以 Tab 與 Shift+Tab 循環、方向鍵切分頁、Esc
  - Then 焦點被限制在對話框內（Tab 走完最後一個元素回到第一個）；分頁方向鍵切換；Esc 關閉且焦點回到觸發的「詳情」鈕；對話框開啟時背景不可聚焦——判定方式（Playwright 的 `toBeHidden` 不看 `aria-hidden`，故不用它）：(i) Tab 與 Shift+Tab 各連按 60 次，每次 `document.activeElement` 皆在對話框內且會繞圈；(ii) 對話框外的背景根元素以 `closest("[aria-hidden=true]")` 判定為被隱藏
  - 判定：`npx playwright test tests/e2e/self-improving-flow.mock.spec.ts -g AT_966_16_3`；預期突變：焦點逃出對話框，紅
  - 驗收字樣：[AT_OK_966_16_3]
- **AT-966-16-E-1**（Playwright｜同檔｜E2E｜AC-966-16）超大 patch 全部展開。
  - Given 詳情夾具 `patch-big.diff`（約 6000 行、256 KiB）
  - When 開對話框→變更內容→「展開全部」
  - Then 展開在 5 秒內完成並可捲動；展開後 axe 零違規；對話框仍可用 Esc 關閉；頁面無無回應（以 `page.evaluate` 在展開後立即執行簡單運算於 1 秒內回傳為判準）
  - 判定：`npx playwright test tests/e2e/self-improving-flow.mock.spec.ts -g AT_966_16_E_1`；預期突變：展開時同步渲染造成長任務，紅
  - 驗收字樣：[AT_OK_966_16_E_1]
- **AT-966-17-1**（Playwright｜`self-improving-flow-docker.stack.ts`｜E2E｜AC-966-17）新鮮、過時、缺席三畫面。
  - Given 拋棄式全棧（沿 `research-docker.stack.spec.ts` 的拋棄式棧作法）；棧的 `console_report` 目錄為測試自建的暫存目錄（環境 `E2E_SI_REPORT_DIR`），內有測試以根層黃金樣本為底、把 `generated_at` 改成「現在」寫入的 `patrol.json`；ADMIN 登入
  - When (a) 開 `/self-improving`；(b) 把 `patrol.json` 改成 `generated_at`＝現在減 40 分鐘（以「寫新檔→rename」覆寫）後按「重新整理」；(c) 刪除 `patrol.json` 後按「重新整理」
  - Then (a) 顯示「上次心跳：N 分鐘前」且無警示；(b) 出現「巡邏可能沒在跑」警示；(c) 出現「還沒有收到巡邏回報」畫面；全程對該目錄只讀（Bridge 容器內 `touch /si-report/x` 失敗）；測試收尾刪除自建目錄
  - 判定：`E2E_STACK=1 npx playwright test tests/e2e/self-improving-flow-docker.stack.ts -g AT_966_17_1`（帶拋棄式棧環境變數）；預期突變：Bridge 快取快照（改檔後畫面不變）、掛載可寫，皆紅
  - 驗收字樣：[AT_OK_966_17_1]
- **AT-966-17-2**（Playwright｜同檔｜E2E｜AC-966-17、NFR-FV-9）真提案詳情冒煙檢查（含合成哨兵）。
  - Given 拋棄式全棧（Bridge 唯讀掛載本 repo 的 `tools/` 與 `docs/06_quality/`，經真根層 CLI `export --kind proposals --id`）；已有至少一個真提案（取 `GET /api/v1/si/proposals` 第一筆）；根層鍵實作已落地；在全棧自帶的拋棄式 `AUTOSDD_SI_DIR` 內預先放一份合成評估集目錄（內含唯一哨兵字串 `CANARY-<隨機>`；**不讀、不掛、不碰真實 `~/.autosdd`**）
  - When 開 `/self-improving`→提案分頁→對該提案按「詳情」→逐一切五分頁
  - Then 「變更內容」顯示該提案 `rN.patch` 的內容（與 repo 內追蹤檔 `docs/06_quality/SelfImproving_Proposals/<id>/rN.patch` 讀檔結果逐行相同，測試以檔案系統讀取比對）；頂端「下一步」非空（不是「量不到」）；`GET /api/v1/si/proposals/<id>` 的回應本文與整個 DOM 的 `textContent` 皆不含哨兵；全程零非 GET。**誠實劃界：本 AT 在全棧層是冒煙檢查，不宣稱可被造成紅燈**——容器讀不到拋棄式 held-out 目錄（compose 不掛載它），所以哨兵不含於回應是必然的；評估集零外洩的真保證在根層 AT-747-4-E-2（`propdetail` 禁讀評估集）、Bridge 的白名單 AT-966-4-6（主機多帶的鍵會被丟棄）與前端 AT-966-9-2（不渲染未知鍵）
  - 判定：`E2E_STACK=1 npx playwright test tests/e2e/self-improving-flow-docker.stack.ts -g AT_966_17_2`；本 AT 的鑑別力僅限「真提案的 patch 與下一步在真棧上端到端可見」：預期突變＝Bridge 對單筆提案的過濾誤傷契約鍵（`patch` 被丟）、根層 `detail` 缺 `next`，皆紅
  - 驗收字樣：[AT_OK_966_17_2]
- **AT-966-17-3**（Playwright｜同檔｜E2E｜AC-966-17、NFR-FV-9）hermetic 掛載斷言。
  - Given 拋棄式棧起來後
  - When `docker inspect` engine-bridge 容器的 Mounts
  - Then `/si-report` 的 `Source` 位於測試暫存目錄之下（不在使用者家目錄的 `.autosdd` 下）、`RW` 為 false；`/si-audit` 的 `Source` 亦為拋棄式目錄（不是真 SI 家目錄）；`BRIDGE_SI_REPORT_DIR` 環境值為 `/si-report`
  - 判定：`E2E_STACK=1 npx playwright test tests/e2e/self-improving-flow-docker.stack.ts -g AT_966_17_3`；預期突變：掛真 `~/.autosdd`，紅
  - 驗收字樣：[AT_OK_966_17_3]
- **AT-966-17-E-1**（Playwright｜同檔｜E2E｜AC-966-17）未掛載部署的畫面。
  - Given 以一份 compose override 起第二套拋棄式棧，其 engine-bridge 不設 `BRIDGE_SI_REPORT_DIR`（模擬舊部署）
  - When ADMIN 開 `/self-improving`
  - Then 巡邏卡顯示「這個部署沒有掛載巡邏回報目錄」；狀態橫幅、提案分頁、對帳面板皆正常；詳情對話框仍可開啟（下一步取詳情 `next`）；待入帳面板層級顯示「拒收原因量不到：這個部署沒有掛載巡邏回報目錄」
  - 判定：`E2E_STACK=1 npx playwright test tests/e2e/self-improving-flow-docker.stack.ts -g AT_966_17_E_1`；預期突變：未設環境變數時整頁報錯，紅
  - 驗收字樣：[AT_OK_966_17_E_1]

---

## 3. AT 完整清單

依「測試住在哪一側」分類：

- **3.1 Bridge（pytest）**：AT-966-1-1～1-8、1-E-1、1-E-2（10）；AT-966-2-1～2-5、2-E-1（6）；AT-966-4-1、4-2、4-6、4-E-1（4）；合計 20 個。
- **3.2 backend（JUnit）**：AT-966-3-1～3-6、3-E-1（7）；AT-966-4-3～4-5（3）；合計 10 個。
- **3.3 frontend（vitest）**：AT-966-5-1～5-9、5-E-1（10）；AT-966-6-1～6-7、6-E-1（8）；AT-966-7-1～7-5、7-E-1、7-E-2（7）；AT-966-8-1～8-5、8-E-1（6）；AT-966-9-1～9-6、9-E-1（7）；AT-966-10-1～10-3、10-E-1（4）；AT-966-11-1～11-7、11-E-1、11-E-2（9）；AT-966-12-1～12-7、12-E-1、12-E-2（9）；AT-966-13-1～13-6、13-E-1、13-E-2（8）；AT-966-14-1～14-3、14-E-1（4）；AT-966-15-1、15-2、15-E-1（3）；合計 75 個。
- **3.4 Playwright**：AT-966-16-1～16-3、16-E-1（4）；AT-966-17-1～17-3、17-E-1（4）；合計 8 個。

**計數核對**：20＋10＋75＋8＝113；亦等於各 AC 分項加總：AC-966-1（10）＋2（6）＋3（7）＋4（7）＋5（10）＋6（8）＋7（7）＋8（6）＋9（7）＋10（4）＋11（9）＋12（9）＋13（8）＋14（4）＋15（3）＋16（4）＋17（4）＝113。編號含 `E` 者 22 個：1-E-1、1-E-2、2-E-1、3-E-1、4-E-1、5-E-1、6-E-1、7-E-1、7-E-2、8-E-1、9-E-1、10-E-1、11-E-1、11-E-2、12-E-1、12-E-2、13-E-1、13-E-2、14-E-1、15-E-1、16-E-1、17-E-1。

---

## 4. 邊界與錯誤測試規格，與需同步的既有測試

| 類別 | 情境 | 預期 |
|------|------|------|
| 邊界 | `patrol.json` 1048576／1048577 位元組；patch 399／400／401 行；`generated_at` 與 `readAt` 差 35:00／35:01、晚 4:59／5:01；最近已入帳 5／6 筆 | 前者通過、後者被拒或切換（依各 AT） |
| 邊界 | patch 256 KiB（262144 位元組）、單行 200000 字元、`props` 200 筆、來源觀察 30 個 | 視窗化或捲動，不崩潰、不截斷於元件層 |
| 錯誤 | 快照目錄未設、缺檔、不可讀、壞檔（十三子情境）、Bridge 不可達、逾時、401 | 依 AT-966-1-2、1-3、3-3、11-5～11-7、14-E-1 |
| 競態 | 主機寫入快照時 Bridge 同時讀取 | AT-966-1-E-1：永遠完整檔；Docker Desktop 的目錄 bind 是否即時看見 `os.replace` 後的新檔屬 V3 實測 |
| 競態 | 快照比帳本舊（`ledger_seq < lastSeq`）或過時 | AT-966-5-2、6-5、6-6：改用帳本判斷並加警示 |
| 安全 | 惡意字串、憑證形態 URL、評估集內容金絲雀 | AT-966-6-7、11-E-2、12-6、9-2 |

### 4.1 需同步的既有測試（只改預期值；不弱化斷言；本表外既有函式因本鍵而紅者，開發 agent 以純文字回報、由主控裁決後補入本表）

| 既有測試（檔；撰寫時現查，行號開發時再查） | 現況 | 改為 | 原因 |
|---|---|---|---|
| Bridge `tests/test_si_readonly_lock.py`（`test_AT_964_8_4…` 的路由普查，`len(si_router.router.routes)`） | 現值（含研究來源同步路由後） | 現值加 1 | `GET /si/patrol` |
| Bridge `tests/test_si_routes.py`（若有路由或方法清單釘選；開發 agent 先跑、以紅燈為準回報） | 現清單 | 加 `GET /si/patrol` | 新路由 |
| Bridge `tests/test_settings*.py`（若以位置參數建 `Settings` 或釘欄位集合；以紅燈為準回報） | 現欄位集合 | 加 `si_report_dir` | 新設定 |
| backend `SiReadOnlyArchTest`（`AT_935_3_1…`：`@GetMapping` 恰八個、`AgentBridge` 上 `si[A-Z]` 方法恰八個） | 8／8 | 9／9（訊息文字加 `patrol`）；「鏡像呼叫集合」（`AgentBridge` 上被 SI 讀取端使用的 `si` 方法集合）由 `siExport` 一個增為 `siExport`、`siPatrol` 兩個 | `SiController.patrol`、`AgentBridge.siPatrol` |
| backend `IssueBridgeArchTest`（TCS-IssueCenter-20261027 的 AT-IC-07-6-1／6-E-1；`AgentBridge` 的 `si` 方法與 GET 計數） | 8／8 | 9／9 | 同上；議題中心對 `AgentBridge` 的結構鎖以「現值」釘 `si` 方法數 |
| Bridge `tests/test_si_cli.py`（`Settings` 欄位尾端的位置參數／欄位集合） | 現欄位集合 | 尾端加 `si_report_dir` | 新設定欄位；既有 `si_cli` 行為與 argv 白名單不變 |
| frontend `lib/api/si.endpoints.test.ts` 的 describe／it **標題**（寫死「十二個 SI 路徑」「十二個路徑、十三個操作」等數字，早已因研究來源單一化與本鍵過時） | 標題含數字 | **改成不寫死數字的措辭**（例如「已入庫的 schema.d.ts 的 SI 路徑集合與規劃相符」）；`it.each`／清單內容與斷言不動；AT 底線形（`AT_950_10_2`、`AT_951_6_2`）保留 | 標題數字每增一個端點就過時，改為不寫死以免再次漂移 |
| backend `OpenApiIT`（`AT_964_7_7*` 的路徑與操作總數；`AT_950_10_1` 的 SI 路徑清單） | 現值 | 現值各加 1；SI 路徑清單加 `/api/v1/si/patrol` | 新端點 |
| backend `ErrorResponseDocumentation`／`SiScheduleWriteApiIT` 內列舉 `cause` 的釘選（若有） | 九個 cause | 加四個 `report_*` | 新 cause（只在 Bridge 新路由出現） |
| backend `AbstractApiIT` 迷你 Bridge | 無 `/si/patrol` | 加路由與 `MINI.patrol(...)`、`MINI.proposalDetail(...)` | 測試設施（只增不改） |
| frontend `lib/api/si.endpoints.test.ts`（`SI_READ_FUNCTIONS`、`PATHS`、`AT_951_6_2` 的路徑與 operationId 清單） | 七個函式；PATHS 不含 `/api/v1/si/patrol` | 加 `getSiPatrol`（八個）；PATHS 與 `AT_951_6_2` 清單各加 `/api/v1/si/patrol`（`getSiPatrol`）；`endpoints.test.ts` 表加一列 `GET /api/v1/si/patrol` | 新讀取函式 |
| frontend `lib/api/schema.d.ts`（入庫快照） | 無 `getSiPatrol` | 重產 | 新 operationId |
| frontend `SiView.test.tsx`（`AT_935_3_2` 的唯讀按鈕白名單與各案例的請求集合／次數斷言）、`SiStatusFilter.test.tsx`、`SiSchedulePanel.test.tsx`、`SiStatusBanner.test.tsx` 中對 `SiView` 整體請求次數的斷言 | 不含 `patrol`、不含「詳情」鈕 | 請求集合加 `GET /api/v1/si/patrol`（所有角色）；測試內部的唯讀按鈕 testid 白名單加三個封閉項：`si-detail-open-<ID>`、`si-patrol-steps-toggle`、`si-patrol-open-writes`（皆唯讀、非寫入控件；沿該白名單「封閉集合逐個列名」的既有做法）；**對帳面板內不新增任何按鈕**（AT-966-13-5 已改為常駐顯示、無展開鈕），故 `AT_935_3_2` 的面板按鈕名稱清單與 `AT_951_4_1` 的面板按鈕數**維持原預期值、不改**；`stubSiApi` 的預設 `patrol` 回 503 `report_missing` 以免舊案例收到未處理請求 | SI 頁多一個唯讀請求與一個唯讀按鈕 |
| frontend `tests/helpers/si.tsx` | 無 `patrol`、`proposalDetail` 端點 | 加 `patrol`、`proposalDetail` 兩條可覆寫路由（預設值如上；**不加 `issue` 端點**，本鍵不打議題端點） | 測試設施（只增不改） |
| frontend `tests/e2e/a11y.ts`、`tests/e2e/a11y.mock.spec.ts`（`:177` 附近）、`tests/e2e/research-deliver.mock.spec.ts`（`:20` 附近） | `RESEARCH_WIDTHS` 在後兩支各自宣告、皆未匯出 | 在 `a11y.ts` 新增匯出 `RESEARCH_WIDTHS`（值 1440／1000／600 不變），兩支既有 spec 改為 import 它——**只動常數宣告，不動任何斷言與情境，既有 spec 行為不變**（AT-966-16-2 因此與既有無障礙 E2E 同源，不另立數字） | AT-966-16-2 的同源要求（C-16） |
| frontend `tests/e2e/self-improving-schedule.mock.spec.ts`、`a11y.mock.spec.ts`（若掃自我進化頁）等凡 mock `/api/v1/si/**` 的 spec | 無 `patrol` 路由 | 補 `/api/v1/si/patrol`（回 503 `report_missing`，預設）；斷言語意不變 | 頁面新增請求 |
| frontend `lib/help/self-improving.ts` 與 `content.test.ts`／`pageFacts.test.ts` 的釘選（欄位列數、`sourceFiles`、說明字樣） | 無本鍵段落 | 加四段（本鍵新增 12 個欄位）、五個名詞的白話片段（評估集、沙盒、探針、巡邏快照、下一步，落在既有 `fields[].meaning`）、`sourceFiles` 加三個元件與 `lib/domain/siFlow.ts`；不新增名詞表結構 | 每頁說明同步（AT-966-15-1） |
| frontend `SiProposalsPanel` 既有測試（欄數、`colSpan`） | 9（ADMIN 10）欄 | **不變**：「詳情」鈕放在既有第一欄（與展開鈕同格），不新增欄 | 避免連動排序與欄寬釘選 |

**本鍵沒有找到因本增量而必然失效的既有 AT**：`console-writes` 的 `items[]` 十一鍵與頂層鍵集合不變（前端結合，§7.1 第 3 項）；`si_cli.py` argv 白名單不變；既有 Bridge 路由行為不變；失效面只來自上表五類「計數、清單、請求集合、白名單」預期值。

**既有 TCS 勘誤稿**：無（本鍵不修改任何已凍結 TCS 或契約的語意；Architecture 與 Console PRD 為追加，非改寫）。**需要 `spec-refreeze` 的鍵**（一審審查者逐把比對「各鍵最後一筆凍結摘要」與 HEAD 檔的 SHA-256 後的核對結果；判準＝**只有最後一筆摘要仍等於 HEAD 檔者才需要重凍**，其餘鍵的摘要早在本鍵之前就已不等於 HEAD，重凍它們只是蓋新章、並非因本鍵而失效）：
- `docs/01_requirements/Agent_ConsoleUI_PRD.md`（本鍵新增 §0.12）：`agentconsole-console-ux-sort-help`、`agentconsole-exec-monitor-entry`、`agentconsole-fsm-trail`、`agentconsole-nav-consolidation`、`agentconsole-research-to-prd-p0`、`agentconsole-research-to-prd-p1`、`agentconsole-research-to-prd-p2`、`agentconsole-si-schedule`（**共 8 把**）。
- `AgentConsole/docs/02_architecture/Architecture.md`（本鍵新增 §5.7、§10.5、§12.1 L-SI-3、§9.4 一列）：**只有 `agentconsole-si-schedule`**（1 把；與上列 PRD 同一次指令併記兩個 `--doc`）。其餘持有者（`console-ux-sort-help`、`exec-monitor-entry`、`fsm-trail`、`nav-consolidation`、`research-to-prd-p0／p1／p2`、`si-decide`、`si-decide-dedupe`、`si-mirror`）的 Architecture 摘要本來就不等於 HEAD，不需也不應因本鍵重凍。
- 不需重凍：`API_Contract_SelfImproving_P1b／P2b／P2c.md`（未修改）、`Implementation_Plan.md`、`RTM.md`（無任何鍵持有）、`agentconsole-research-registry`／`page-help`／`issue-center`／`sysadmin-backup`（不持有這兩檔）；根層鍵不持有 Console PRD／Architecture。
- 凍結前仍由主控以各鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 與 `Get-FileHash -Algorithm SHA256` 現查確認；本鍵自身依常規流程凍結 Stage-1（PRD、Architecture）與 Stage-2（本 TCS）。
---

## 5. 測試資料規格

### 5.1 常數與資料

- 測試提案編號一律 `PROP-SI-901`、`PROP-SI-902`、觀察 `OBS-SI-<901>`、運轉 `RUN-SI-901`、稽核編號 `A1`～`A3` 以固定 UUID 形（`a1000000-0000-4000-8000-00000000000N`）；皆**不存在於真帳本**（NFR-FV-8 第 7 項）。**給所有實作者的規定**：測試資料與原始碼（含測試檔、夾具、註解）不得寫出形似帳本編號而帳本裡查無的字面（觀察編號 `OBS-SI-` 接數字最危險：根層 `si check` 的 `ref.obs` 會掃全 repo，查無即 `OBS-REF-DANGLING` 紅；其他前綴〔`PROP-SI-`、`RUN-SI-`、`DEF-`〕若根層對應檢查同樣掃到，處理方式相同）；要用帳本裡真實存在的編號，或在執行期拼出（例如 `["OBS-SI", 901].join("-")`，前綴與數字不相鄰寫成字面）。本檔以 `OBS-SI-<901>` 的形式書寫觀察範例編號（數字不緊接前綴）。
- `PATROL(over)` 基準（C-2 形，**前端實際收到的 camelCase 鍵名**，全檔前端 AT 的 Given 一律用此形態；Bridge／backend 層的 `PR(over)` 為同內容 snake_case）：`{schemaRev:1, kind:"patrol", readAt:NOW, report:{generatedAt:<NOW 前 3 分>, off:false, heartbeatMinutes:15, ledgerSeq:130, truncated:false, steps:[<恆 5 項：巡視、入帳、到期、運轉、推進>], schedule:{enabled:true, current:{code:"SCHED-CELL-RAN",text:"本期已經跑過一次，等下一期"}, lastSkip:null}, ingest:[], props:[{id:"PROP-SI-901",state:"verified",code:"WAIT-PROMOTE-DECISION",who:"掌舵者",text:"驗證通過，等你決定是否晉升"}], runs:{live:[],waiting:[],queued:[]}, push:{enabled:true,state:"idle",code:"PUSH-NOT-AHEAD",text:"沒有待推送的提交",retry:null,sha:null,ahead:0,attempts:0,finishedAt:null,tickAt:null}}}`；`ingest[]` 項為 `{auditRef,kind,status,code,text,permanent}`，`runs.live[]` 項為 `{run,purpose,startedAt,wallDueAt}`，`lastSkip` 為 `{seq,t,code,text,auditRef}`。白話字句取自根層 TCS-P7 附錄 A 的固定句或其語意。
- `DETAIL(over)` 基準（C-3 形；根層 §2.1 八欄俱全）：`patch={rel:"docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch",bytes:<實長>,text:<patch-mixed.diff>,truncated:false}`、`body={rel:"…/r2.md",bytes:…,text:"# 提案 901\n\n症狀…\n",truncated:false}`、`sourceObs=[{id:"OBS-SI-<901>",context:"巡邏日誌",symptom:"提案卡了三天沒人處理",severity:"P2",disposition:"proposed"}]`、`heldout={frozen:true,seq:60,n:7,min:5,belowMin:false,frozenBy:"凍結者甲",digest8:"0a1b2c3d",neNote:null}`、`sandbox={seq:61,id:"APP-SI-901",applied:true,touchedOk:true,rollbackOk:true,failCode:null,failText:null}`、`verify={seq:62,id:"APP-SI-901",verdict:"PASS",baselineRed:true,patchedGreen:true,mutatedRed:true,probesN:6,carrierProof:true,reasons:[]}`、`next={code:"WAIT-PROMOTE-DECISION",who:"掌舵者",text:"驗證通過，等你決定是否晉升"}`、`timeline=[{seq:12,t:"2026-11-10T09:00:00+08:00",by:"巡邏器",kind:"prop",action:"提出提案"},…]`。- 夾具檔：`frontend/tests/fixtures/si/flow/`：`patrol-fresh.json`、`patrol-stale.json`（`generated_at` 早 40 分）、`patrol-off.json`、`patrol-minimal.json`、`detail-full.json`、`detail-minimal.json`（無 `detail` 鍵）、`detail-hostile.json`、`patch-mixed.diff`（見 AT-966-5-5 描述）、`patch-big.diff`（262144 位元組、約 6000 行；由測試以固定種子**產生並寫入暫存**，不入庫大檔；僅 `patch-mixed.diff` 入庫）；Bridge：`engine-bridge/tests/fixtures/si_report/`：`valid.json`、`invalid-*.json`（以測試內字串產生為主）。**黃金樣本——複本責任、同步與硬斷言**（根層樣本已存在：`tools/tests/fixtures/selfimproving/p7/{patrol,detail}.golden.json`；下段為本鍵唯一規則）：**主控**負責把兩個樣本原樣複製到三側，路徑固定——前端 `AgentConsole/frontend/tests/fixtures/si/flow/{patrol,detail}.golden.json`（`siFlow.golden.test.ts` 與 AT-966-12-1、12-7、9-1、9-4 的黃金列）、Bridge `AgentConsole/engine-bridge/tests/fixtures/si_report/{patrol,detail}.golden.json`（AT-966-1-1、4-1、4-6 的黃金列）、backend `AgentConsole/backend/src/test/resources/si/p7/detail.golden.json`（AT-966-4-3 的黃金列；backend 只需 detail）。**樣本更新時的同步**：根層樣本改動的同一個 commit，主控重新複製三側全部複本並以 `Get-FileHash -Algorithm SHA256` 核對；各側先行測試（逐位元組比對根層檔）是機械保險，漏複製即紅。**待根層樣本的暫態處理必須移除**：各包先前以 `xfail`（Bridge）、`Assumptions` 跳過（backend）、「前端複本不得先行存在」斷言（前端）標示「待根層樣本」，複本到位後這些暫態分支一律刪除，下列 AT 的黃金列轉為**硬斷言**：AT-966-1-1、4-1、4-6（Bridge）、4-3（backend）、12-1、12-7、9-1、9-4（前端）；不得留任何 skip。CI：`agentconsole-ci.yml` 的 `paths` 須涵蓋 `tools/tests/fixtures/selfimproving/p7/**`（Bridge、backend、前端測試會讀根層檔；屬主控／根層持有面，不在三包內）。以下為樣本格式說明（裁決 11；根層 TCS-P7 §3 定義，路徑固定 `tools/tests/fixtures/selfimproving/p7/patrol.golden.json`、`tools/tests/fixtures/selfimproving/p7/detail.golden.json`；LF、無 BOM、結尾一個 LF）：主控複製到 `engine-bridge/tests/fixtures/si_report/`、`backend/src/test/resources/si/p7/`、`frontend/tests/fixtures/si/flow/`（檔名同）；**每一側有先行測試**以 repo 根相對路徑讀根層檔與本地複本，斷言逐位元組相等（不相等即紅）；AT-966-1-1、4-1、4-3 另以黃金樣本再跑一次（`it.each`／`parametrize` 的第二列），前端 AT-966-12-1、12-7、9-1、9-4 的 `PATROL`／`DETAIL` 夾具亦各有一列取黃金樣本：黃金樣本複本是 snake_case（根層原樣），由 PKG-FE 在 `tests/helpers/siFlow.tsx` 實作轉換輔助函式 `camelKeys`（規則逐字等同 backend `SiKeyNames.camel`：鍵符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 才依 `_` 切段轉駝峰、其餘鍵恆等，遞迴整棵樹），並以黃金樣本的轉換結果與 `PATROL()`／`DETAIL()` 基準的鍵集合相等作為該輔助函式的自檢（包在 AT-966-12-1 的黃金列內）；黃金 `detail` 樣本是整個 `items[0]`（含 `detail`），前端取其 `detail`。
- 常數單一定義處：`PATROL_REPORT_MAX_BYTES`（`app/si_report.py`）；`STALE_FACTOR`、`STALE_GRACE_MINUTES`、`DIFF_WINDOW_LINES`、`RECENT_INGESTED_SHOWN`（`lib/domain/siFlow.ts`）。測試以 import 取值並另斷言其值（防被悄悄改動）。

### 5.5 backend 測試設施（沿 P2b TCS §5.4、P4 TCS §5.5；只增不改）

`AbstractApiIT` 迷你 Bridge 加路由 `GET /si/patrol`（`MINI.patrol(status, body)`）；`GET /si/proposals/{id}`（`MINI.proposalDetail(id, item)`，沿現有單筆路由的設定方式）；`MINI.requests()` 回傳按序記錄的請求（方法、路徑、標頭、本文）。新增 `SiPatrolApiIT`、`SiProposalDetailApiIT` 沿 `SiMirrorApiIT` 的體例（`AbstractApiIT` 帳號、`MockMvc`／測試 HTTP 客戶端）。

### 5.6 frontend 與 Playwright 測試設施

`tests/helpers/si.tsx` 加 `patrol`、`proposalDetail` 兩個 `SiEndpoint` 與 `renderSi` 的 `overrides`（不加議題端點）；`PATROL`、`DETAIL` 夾具建構函式放 `tests/helpers/siFlow.tsx`（新檔）；jsdom 下 `URL.createObjectURL`、`URL.revokeObjectURL` 以替身；固定時間以 `readAt` 夾具而非假時鐘（不依賴 `Date.now`，例外只有需要「時間前進」的 AT-966-11-1（「無輪詢」）、11-2、11-3 與 11-E-1 (d)，它們一律使用**可控時鐘替身** `tests/helpers/siClock.ts`（以測試可手動前進分鐘的時間來源取代 `useMinuteTick` 的內部時鐘與 `Date.now`，**不使用假計時器**：假計時器會讓 Testing Library 的 `waitFor` 停擺））；Playwright mock spec 沿 `self-improving-schedule.mock.spec.ts`；真棧 spec 沿 `research-docker.stack.spec.ts` 的拋棄式棧與登入輔助，快照目錄 `E2E_SI_REPORT_DIR` 由 spec 以暫存目錄建立並於收尾刪除。

### 5.7 hermetic 環境與允許變更的檔案集合

- **允許變更**（三包持有面）：D1～D7 所列路徑，加 §4.1 所列既有測試檔的預期值與 mock 路由；Architecture §5.7／§10.5／§9.4 一列／§12.1 L-SI-3、Console PRD §0.12、Implementation_Plan 與 RTM 子表由 SA 棒與主控處理。另含 Bridge 新模組 `app/si_detail.py` 與其測試、§4.1 新增列的 `IssueBridgeArchTest`、`test_si_cli.py`、`si.endpoints.test.ts`、前端夾具 `tests/e2e/siFlowFixtures.ts` 與 `tests/helpers/{siFlow.tsx,siClock.ts}`、`SiDiffView.tsx` 的可聚焦區域，以及 §4.1 的 `tests/e2e/a11y.ts`、`a11y.mock.spec.ts`、`research-deliver.mock.spec.ts`（只動 `RESEARCH_WIDTHS` 宣告）。本鍵**不得**動：根層 `tools/`、`.claude/`、`.github/`、根 `CLAUDE.md`、既有 Flyway 檔（本鍵無新遷移）、既有 TCS 與契約原文、`si_cli.py`、`consoleaudit` 相關黃金檔。
- AT 不連外網、不寫真 SI 家目錄、不讀真帳本、不讀真 `patrol.json`；Testcontainers PG、迷你 Bridge、jsdom、fetch 替身、Playwright 路由替身與拋棄式全棧為唯一外部依賴；AT-966-17-2 讀的 `docs/06_quality/SelfImproving_Proposals/` 為 repo 內追蹤檔（唯讀）。

---

## 6. RTM 連結確認

### 6.1 追溯

| 需求 | AC（PRD §0.12）｜AC（本檔） | AT |
|------|---------------------------|-----|
| 校正 1：提案詳情對話框 | AC-966-6、6 | AT-966-6-1～6-7、6-E-1；AT-966-10-1～10-3、10-E-1 |
| 校正 2：diff | AC-966-7 | AT-966-7-1～7-5、7-E-1、7-E-2 |
| 校正 1（本文與來源） | AC-966-8 | AT-966-8-1～8-5、8-E-1 |
| 校正 3：評估集與驗證 | AC-966-9 | AT-966-9-1～9-6、9-E-1 |
| 校正 4：巡邏狀態卡 | AC-966-11、12 | AT-966-11-1～11-7、11-E-1、11-E-2；AT-966-12-1～12-7、12-E-1、12-E-2 |
| 校正 5：入帳結果 | AC-966-13 | AT-966-13-1～13-6、13-E-1、13-E-2 |
| 校正 6：資料來源與信任、更新頻率 | AC-966-1、3、4、5 | AT-966-1-1～1-8、1-E-1、1-E-2；AT-966-3-1～3-6、3-E-1；AT-966-4-1～4-6、4-E-1；AT-966-5-1～5-9、5-E-1 |
| 校正 8：部署 | AC-966-2 | AT-966-2-1～2-5、2-E-1 |
| 校正 7、9：角色、說明 | AC-966-14、15 | AT-966-14-1～14-3、14-E-1；AT-966-15-1、15-2、15-E-1 |
| E2E 與無障礙 | AC-966-16、17 | AT-966-16-1～16-3、16-E-1；AT-966-17-1～17-3、17-E-1 |
| NFR-FV-1～9 | — | 見 NFR 表「驗證 AT」欄 |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註；未驗者如實標「未驗」，構造情境不得充當）

- **V1（主控，真機；長駐棧升級序列，順序不可換）**：(1) 在主機建立回報目錄——PowerShell：`New-Item -ItemType Directory -Force -Path (Join-Path $(if ($env:AUTOSDD_SI_DIR) { $env:AUTOSDD_SI_DIR } else { Join-Path $env:USERPROFILE '.autosdd\selfimproving' }) 'console_report')`；POSIX：`mkdir -p "${AUTOSDD_SI_DIR:-$HOME/.autosdd/selfimproving}/console_report"`（**必須先於 `docker compose up`**：bind 設了 `create_host_path: false`；根層巡邏第一次心跳才會寫入快照檔，所以此時目錄是空的）；(2) 重建三個映像並啟動——`docker compose --profile db --profile app --profile full build engine-bridge backend frontend` 後 `docker compose --profile db --profile app --profile full up -d`（engine-bridge 有新模組、backend 有新端點、frontend 有新畫面，三者缺一則畫面或 API 對不上；nginx 與資料庫映像不動、不需重建）；(3) 驗證——以 ADMIN 登入後 `GET /api/v1/si/patrol`：快照尚未寫出時應回 503 `si_unavailable`（`cause=report_missing`），自我進化頁顯示「還沒有收到巡邏回報」；等根層巡邏的第一個心跳寫出快照（最多一個心跳週期）後重新整理，應顯示「上次心跳：N 分鐘前」；(4) **失敗表徵**：目錄沒建就 `up` ⇒ compose 以「bind source path does not exist」類訊息拒絕啟動 engine-bridge（明確失敗，不是靜默）；只重建 engine-bridge 而漏了 backend ⇒ `GET /api/v1/si/patrol` 回 404；漏了 frontend ⇒ 畫面沒有巡邏卡與「詳情」鈕；映像都新但環境變數 `BRIDGE_SI_REPORT_DIR` 沒進容器 ⇒ 卡片顯示「這個部署沒有掛載巡邏回報目錄」；(5) **退回**：還原 `docker-compose.yml` 到升級前版本（移除 `/si-report` bind 與環境變數）並 `up -d`，舊畫面不受影響（Bridge 對未設環境變數降級為 503 `report_dir_unset`，其他自我進化功能照常）。以上序列同寫入 `AgentConsole/docker/README.md`〈巡邏回報目錄〉（AT-966-2-4 機械檢查：三個指令各自存在且順序為「建目錄→重建映像→啟動→驗證」，並含失敗表徵與退回各一段）。升級後目視：巡邏卡顯示真心跳、對一個真提案開詳情對話框五分頁；巡邏卡與主機 `patrol.json` 的 `generated_at`、`props[]` 逐項對照。- **V2（主控）**：在主機製造一筆被拒收的稽核檔（例：對舊卡面送 `promote`），等巡邏一個心跳，目視待入帳列顯示「被拒收」與主機給的白話；其後以 CLI 手動處置並確認該列轉入「最近已入帳」或仍待入帳。
- **V3（主控，Docker Desktop）**：主機以「寫新檔→rename」連續覆寫 `patrol.json` 二十次（每次 `generated_at` 遞增），同時由 `GET /api/v1/si/patrol` 輪詢，確認 Bridge 在 1 秒內看見新值、無舊 inode 殘留；失敗則回報架構（改為每次重新 open 且不快取）。
- **V4（QA）**：既有 SI AT 全套（`SiMirrorApiIT`、`SiConsoleWriteApiIT`、`SiConsoleWritesReadApiIT`、`SiScheduleWriteApiIT`、`SiReadOnlyArchTest`、Bridge `test_si_*`、前端 SI 元件與 `lib/domain/si` 測試）逐檔重跑，列出預期值改動恰等於 §4.1。
- **V5（主控）**：全套 `gradlew clean build`、Bridge `pytest` 與 `ruff check`（兩視角）、前端 `lint`／`tsc --noEmit`／`build`／`vitest`；根層 `si check` 不因本鍵變紅（本鍵不動根層）。
- **V6（QA）**：Linux（CI）與 Windows 各跑一次本鍵新增 AT；macOS 未驗（如實標）。
- **V7（掌舵者，目視；或改由代理截圖代驗，沿研究來源單一化勘誤 E-12 做法）**：長駐棧以 ADMIN 唯讀開啟詳情對話框與巡邏卡（不下任何決定），1440／1000／600（與 AT-966-16-2 同源）三寬截圖並跑 axe，**另加手機寬 375 作補充目視（非 AT，數字不入 AT 常數）**；逐段對照文案是否國高中白話、與規格用語一致；diff 在 375 寬可捲動可讀。
- **V8（QA）**：拿一個真實的大提案（patch 接近 256 KiB）開詳情，量首次展開到可互動的時間，並確認截斷提示與下載檔皆如規格。

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 裁決與預設

1. **編號**：AC 取 `AC-966-1～17`（`AC-965` 已被研究來源單一化占用，架構設計稿原擬的 AC-965／966 作廢，第二波取 AC-967 起）；F-911、US-931；API 編號 `API-SI-16`（`API-SI-14／15` 已占用）；RTM 子表 §2.16；Console PRD §0.12。
2. **契約放本檔 §0.2，不改既有契約檔**：`API_Contract_SelfImproving_P1b／P2b／P2c.md` 為凍結檔，本鍵只加讀取端點與一個透傳物件，寫在 TCS §0.2 與 Architecture §10.5 即足；避免連動重凍其持有者。
3. **入帳結果用前端結合，不改 `console-writes`**：設計稿原案「console-writes 對帳併入 `hostRejection`」會使 `items[]` 變十二鍵，而「恰十一鍵」被 `TCS-SelfImprovingDecideDedupe` 與 `SiConsoleWritesReadApiIT`（AT-951 系列）逐字釘住，併入需勘誤並重凍多鍵；前端以 `auditRef` 對 `ingest[]` 結合在功能上等價（兩份資料本來就都送到前端），且零 backend 改動、零既有 AT 失效。代價：ADMIN 面板多一個 `patrol` 請求（與巡邏卡共用同一查詢鍵，實際只打一次）。
4. **新鮮度以 `readAt` 為基準**：避免瀏覽器與主機時鐘偏移；`readAt` 缺席才退用瀏覽器時間並標明。
5. **詳情用既有對話框元件（`dialog.tsx`）而非抽屜**：專案沒有 Sheet 元件；對話框已有焦點捕捉與歸還（DEF-AC-011 修復）且 axe 已驗；設計稿的「抽屜」是意象，行為（懶取數、五分頁、可關閉）等價。
6. **懶取數與單一請求**：清單載入時零詳情請求（pending 提案預設展開，若隨展開預取會一次打 N 個子行程與最多 N×256 KiB）；「下一步」在對話框外的展開列不顯示，只在對話框頂端與巡邏卡顯示。時間線與來源觀察採用根層 `detail.timeline`、`detail.sourceObs`（W-F14）：少打一個議題請求與一個失敗面，且消除「來源不在已載入頁」的降級體驗；代價是時間線上限 500 筆（根層以 `TIMELINE-TRUNCATED` 的 `ne.text` 說明）。
7. **角色**：詳情（含 diff 與本文）與巡邏卡對所有可讀 SI 頁的角色（VIEWER 以上）開放。理由：(a) SI 頁整個唯讀鏡像（含事件帳本全文）本來就對 VIEWER 以上開放；(b) patch 與本文是 repo 追蹤檔 `docs/06_quality/SelfImproving_Proposals/` 的內容，Console 使用者本就可經版本庫讀到；(c) 只有 ADMIN 能下決定，閱讀不產生權力。風險：M 類（記憶）提案的 patch 可能含個人記憶內容。若掌舵者要收緊，推翻路徑＝backend 對非 ADMIN 把 `detail.patch.text`／`detail.body.text` 以 null 取代並在前端顯示「只有管理員可看內容」（需 PRD §0.12 第 1 點與 AT-966-14-E-1、4-3 連動修訂）。
8. **來源觀察跳轉**：議題中心沒有深連結，採「關閉對話框＋切到觀察分頁＋高亮該列」；不新增路由。
9. **compose 用 `create_host_path: false`**：與稽核 bind 一致，避免 Docker 在 Linux 主機以 root 建出主機端使用者寫不進的目錄；代價是首次升級需先建目錄（`.env.example` 與 README 給雙 shell 指令）；未建目錄時 `docker compose up` 明確失敗（不靜默）。
10. **Console 不持有原因碼→白話表，也不持有推送狀態對照**：白話字表單一家在根層（`nextstep`／快照 `text`／`failText`／`neNote`）；Console 只持有三組小列舉標籤（運轉目的第一波三值、驗證結果、入帳狀態）與未知值保底句，避免兩處漂移；第二波才有的值不當成已知；代價是主機沒給白話欄時畫面較不友善（保底句帶原因碼）。
11. **推送**：Console 只顯示主機給的 `push` 狀態與 `text`；本鍵沒有任何推送按鈕（AT-966-12-6 機械鎖）。
12. **「最近已入帳」限 ADMIN 面板、最新 5 筆**：沿既有「對帳面板只對 ADMIN」規則；5 為 `RECENT_INGESTED_SHOWN`。
13. **憑證遮罩為縱深防禦**：主機端依設計稿已遮罩 URL 內憑證；Console 再遮一次 `scheme://userinfo@`，不依賴單一側。
14. **不輪詢**：沿 `SI_QUERY_OPTIONS`；畫面標明資料更新時間，並在過時時提示重新整理。

### 7.2 對上位文件與現況的發現（本檔未改任何凍結檔）

1. **編號衝突已化解**：設計稿的 AC-965／AC-966、API-SI-14／15、RTM §2.15 與現況衝突（皆被研究來源單一化占用），本鍵改用 AC-966、API-SI-16、RTM §2.16；第二波取 AC-967 起。
2. **與根層契約已對齊**（以根層 TCS-P7 §2、附錄 A 為準，逐欄採用與否見 W-F14）：`detail` 八欄、`sandbox.failText`、`carrierProof` 為 bool｜null、`ne` 新碼項帶 `text`、快照 `schedule`／`runs.waiting[]`／`truncated`、`push` 八態與恆非空的 `code`／`text`、`ingest[]` 的 `AUDIT-REF-REUSED` 為 permanent:true、黃金樣本路徑 `tools/tests/fixtures/selfimproving/p7/{patrol,detail}.golden.json`。**對根層契約沒有未決疑義**；僅有兩個提醒（不阻塞）：(a) `readAt` 命名已定案：Bridge 層回 `read_at`、backend 轉 `readAt`、前端收到 `readAt`，全檔不留例外；(b) 根層快照寫入上限 `REPORT_MAX_BYTES`＝524288、Bridge 讀取上限 `PATROL_REPORT_MAX_BYTES`＝1048576，讀端寬於寫端，兩常數各自獨立（C-1）。
3. **持有面**：`SiProposalsPanel.tsx`、`SiWritesPanel.tsx`、`SiView.tsx`、`SiObservationsPanel.tsx`、`lib/api/*`、`tests/helpers/si.tsx` 同為 PKG-FE 一包持有；PKG-FE 內部串行（元件互相引用），不拆多個前端並行包。
4. **審查紀錄**：規格階段獨立審查（一審、二審）的逐筆發現與處置見 `AgentConsole/docs/06_quality/SCG0-REVIEW-SiFlowVisibility-20261111.md`。
### 7.3 已知邊界（不是待修缺陷）

- **根層新增 `detail` 欄位時須同步改白名單**：Bridge 的 `filter_detail` 只放行 C-3 列出的鍵，根層日後在 `detail`（含 `heldout`、`sandbox`、`verify`、`sourceObs[]`、`timeline[]` 等內層）新增鍵時，Console 端必須同步修訂 C-3、W-F4、`filter_detail` 與 AT-966-4-6（走勘誤列）；在那之前新鍵不會顯示，這是刻意的（安全側失敗）。
- Console 看不到主機 OS 任務是否存在；「巡邏有沒有在跑」只能由快照新鮮度推算（Architecture L-SI-1、L-SI-3）；機器睡眠、關機、登出都會使快照過時，與「任務壞了」無法區分，文案只說「巡邏可能沒在跑」。
- 快照是每個心跳的重新量測，不是事件串流；兩次心跳之間發生的拒收要等下一個心跳才出現。
- 前端結合入帳結果時，若快照比稽核檔舊（稽核檔在快照之後才落地），該列顯示「主機還沒處理這筆」是正確的；不為此判斷時序。
- 「下載 patch 檔」只含畫面已取得的全文；主機端截斷（超過 256 KiB）者，下載的是截斷版並明寫，完整檔在主機路徑。
- 第二波（取消待入帳、取消運轉、請求凍結／修訂、觀察送去提案）的畫面入口不在本鍵；永久拒收的文案已明說「目前畫面沒有取消功能」，第二波落地時一併改為提供取消（屆時更新該 AT 預期值走勘誤）。

---

## 📋 SCG-4 通過標準

- [ ] 113 個 AT 全數通過，輸出逐字貼入證據；本檔 §4.1 預期值改動恰等於實際改動（QA 以 `git diff` 核對，不多不少）
- [ ] 既有 SI AT 零弱化（V4）；`console-writes` 十一鍵 AT 零改動仍綠
- [ ] 黃金樣本複本（`patrol.golden.json`、`detail.golden.json`）sha256 與根層樣本相符，AT-966-1-1、4-1、4-3 的黃金樣本列綠
- [ ] `gradlew clean build`、Bridge `pytest` 與 `ruff check`（兩視角）、前端 lint／`tsc`／build／vitest 全綠（V5）
- [ ] 零 skip；零 `@Disabled`；零 `it.skip`
- [ ] 新元件靜態鎖（無 `dangerouslySetInnerHTML`、無寫入 hook）綠；唯讀鎖與 compose 部署鎖（唯一可寫 bind 仍是稽核目錄）綠
- [ ] RTM 本地子表回填（`AgentConsole/docs/06_quality/RTM-SiFlowVisibility-20261111.md`，主控於 SCG-5 做）；`AgentConsole/docs/06_quality/RTM.md` §2.16 回填
- [ ] Architecture §5.7、§10.5、§12.1 L-SI-3 與實作逐項校對；V1～V8 結果如實回寫（未驗者標「未驗」）

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| E-1 | 11-11 | 範例編號與狀態名措辭（文件文字，非語意；測試與程式不動） | 原文：範例觀察編號寫成 OBS-SI-<901>、OBS-SI-<902>、OBS-SI-<777>（共 13 處）；第 526、528 行「未知 state」例以舊設計稿第五態的英文字面命名 | 訂正：範例編號改為 OBS-SI-<901>／<902>／<777>（數字不緊接前綴）；兩行改稱「已廢止的設計稿第五態名」。測試夾具中的實際字串不變 | si check 的 ref.obs 會掃全 repo 內形似帳本編號的字串，範例編號不在帳本即 OBS-REF-DANGLING（紅，根層 test_AT_IC_06_4_1、test_AT_437_5_2 連帶紅）；check_pytest_baseline_sites 以「狀態字樣＋四位數字」判基線宣稱，兩行誤中而使未納管站點由 114 增為 115。屬既有機械鎖，改文字不改鎖 |
| E-2 | 11-12 | AT-966-15-1（含 §4.1 說明列） | 「名詞表新增『巡邏快照』『評估集』『下一步』『沙盒』『探針』五列」；「名詞表列數」 | 改為「五個名詞的白話釋義落在既有 `fields[].meaning`／欄位名內（字串片段機械判定），不新增名詞表結構」，並列出五個必含片段；說明檔由前端開發者實作（§提交順序原寫「由主控代做」，同步訂正） | `PageHelp` 只有 `purpose`／`steps`／`fields`／`states`／`sourceFiles`，沒有名詞表結構（`lib/help/types.ts`、`self-improving.ts`）；前端交卷偏離 3、4。前端需補：「評估集與驗證」釋義加「檢查項目（探針）」、「巡邏狀態」釋義加「巡邏快照」及半句白話 |
| E-3 | 11-12 | AT-966-13-5（§1 映射、§4 邊界不變） | 「展開『最近已入帳（8）』；預設收合；展開後只列最新 5 筆」 | 改為「常駐顯示、不加展開鈕；待入帳清單之下直接列最新 5 筆；段內無 button」 | 展開鈕使對帳面板按鈕數由 3 變 4，牽動已發布的 AT-951-4-1（TCS-SelfImprovingDecideDedupe）與 AT-935-3-2（TCS-SelfImprovingDecide-P2b）的面板按鈕清點；常駐顯示最多 5 列、不損害可用性，且不需為既有 AT 另寫勘誤、不增加重凍鍵。前端需移除 `si-recent-ingested-toggle`，把清單常駐，並把 `AT_951_4_1` 面板按鈕數與 `AT_935_3_2` 面板按鈕名稱清單還原為原預期值 |
| E-4 | 11-12 | §4.1 `SiView.test.tsx` 列 | 「白名單加 `si-detail-open-<ID>`」 | 補列 `si-patrol-steps-toggle`、`si-patrol-open-writes` 兩個唯讀按鈕 testid；明寫此白名單為測試內部封閉集合，既有 AT-935-3-2／AT-951-4-1 的規格文字（Then：名稱與 testid 不含刪除類字樣、寫入類 testid 前綴恰為五個、面板內無刪除類控件）不變，故不修訂已發布 TCS | 已發布 TCS 的 Then 未列舉唯讀按鈕清單，新增唯讀鈕不改其語意；先例＝狀態快篩 pill 與 `si-superseded-toggle` 以同法加入白名單 |
| E-5 | 11-12 | AT-966-8-3 | 「跳轉零新增請求」 | 「不新增詳情、巡邏、議題請求；觀察清單至多重取一次」 | 觀察分頁在提案分頁時卸載（SI 查詢 `gcTime: 0`），跳轉重掛必然重取一次觀察清單 |
| E-6 | 11-12 | AT-966-12-3、AT-966-15-2 | 12-3 的「進行中：RUN-…（排程啟動），12 分鐘前開始，預計最晚 48 分鐘後結束」為單句超過 40 字；15-2 以短值代入檢查 | 12-3 拆成兩個短句；15-2 明寫鎖只管 Console 自寫的固定句與保底句模板，根層執行期提供的白話（`text`、`neNote`、`failText`、`ne[].text`、`push.text`）逐字顯示、不得改寫而明確豁免；Console 組合句代入最長形態仍須每句 ≤ 40 字 | 根層給的白話句 Console 不能改（裁決 8）；Console 自寫句才受可讀性鎖。前端需把運轉列句子拆成兩句並以完整運轉編號代入檢查 |
| E-7 | 11-12 | AT-966-12-E-1 | 「各區不顯示任何『沒有』『無』字樣」 | 斷言範圍限各區內文，不含固定區塊標題與標題旁固定說明 | 區塊標題「為什麼沒有啟動運轉」本身含「沒有」 |
| E-8 | 11-12 | AT-966-11-1／11-2／11-3／11-E-1 (d)、§5.6、AT-966-6-1（確認登記） | 「以假計時器前進」；「固定時間不依賴 Date.now，例外用假計時器」；對話框 `aria-modal="true"` | 改為「可控時鐘替身 `tests/helpers/siClock.ts`（不用假計時器，因其使 `waitFor` 停擺）」；「不輪詢」＝靜態斷言 `SI_QUERY_OPTIONS.refetchInterval === false` 加前進 60 分鐘請求數不變；`aria-modal="true"` 本就是 6-1 的 Then，補註「Radix 預設不帶，須顯式設定」（登記型，語意不變） | 前端交卷偏離 2、5；兩項實作與規格意圖一致，只是測試手法與註記的措辭需明文 |
| E-9 | 11-12 | §5.1、NFR-FV-8 (7) | 「夾具與測試中不得出現不存在於真帳本的字面…（夾具一律用 `PROP-SI-901` 起的測試號）」 | 改為「不得寫出形似帳本編號而帳本查無的字面；用真實存在的編號，或在執行期拼出（前綴與數字不相鄰）；`si check` 的 `ref.obs` 掃全 repo」 | 兩句互相矛盾（901 不在帳本）；根層 `si check` 對查無編號紅燈（見勘誤 E-1 的機械鎖說明） |
| E-10 | 11-12 | AT-966-2-2 | 「相對路徑、`/`（磁碟根）沿 `_anchor_guard` 的既有規則拋 `SettingsError`」 | 「相對路徑（`Path(raw).anchor` 為空）拋 `SettingsError`——新變數刻意比 `BRIDGE_SI_AUDIT_DIR` 嚴；`/` 沿 `_anchor_guard` 既有規則」 | 原句自相矛盾：既有 `BRIDGE_SI_AUDIT_DIR` 對相對路徑是 resolve 成絕對、不拋。裁定新變數嚴格：compose 只給絕對路徑，相對路徑必是部署寫錯，啟動即拋才能第一時間看出；不改既有變數以免動既有行為 |
| E-11 | 11-12 | AT-966-3-3 | 「測試以縮短的 `read-timeout` 屬性」 | 「backend 逾時為常數、無屬性；沿 `SiMirrorApiIT` 讓迷你 Bridge 真等約 21 秒，該案單獨設較長測試逾時」 | 實作現況：連線 2 秒、讀取 20 秒為常數；不為測試新增屬性（最小侵入） |
| E-12 | 11-12 | W-F4、AT-966-4-6 | 「Bridge 只放行契約列出的鍵、其餘丟棄」 | 補「形狀不符一律丟棄（fail-closed）」與「白名單只認 camelCase 鍵」，並以 AT-966-4-6 的 Given 加形狀不符與 snake_case 案例 | 與根層 TCS-P7 §2.1 一致（根層以 camelCase 輸出 `detail`，其測試逐鍵斷言）；更嚴的保守行為不損及契約鍵 |
| E-13 | 11-12 | §4.1 | 同步清單未列 `IssueBridgeArchTest`、`test_si_cli.py`，且 `SiReadOnlyArchTest` 未提鏡像呼叫集合 | 補列：`IssueBridgeArchTest`（`si` 方法與 GET 8→9）、`SiReadOnlyArchTest`（另含鏡像呼叫集合加 `siPatrol`）、`test_si_cli.py`（`Settings` 欄位加 `si_report_dir`）、`test_si_readonly_lock.py`（路由數現值加一）、`OpenApiIT`（計數與 si 路徑）；皆只改預期值、既有行為不變。**不對已發布 TCS（IssueCenter、DecideP2b、Schedule 等）加勘誤、不增加重凍鍵**：這些釘選本就以「現值」計數，先例＝TCS-ResearchRegistry E-5 的登記型處理 | 實作為建置通過而同步的預期值；已發布 TCS 的 Then 未以不可變常數寫死這些數字（歷次增量皆以「現值加 N」更新測試而不勘誤上位 TCS） |
| E-14 | 11-12 | §1 D7、§5.1 夾具檔、AT-966-16-1 Given | 「夾具檔 `patrol-fresh.json`、`patrol-stale.json`、`patrol-off.json`、`detail-full.json`、`detail-minimal.json`⋯」「唯讀資料取入庫黃金檔與 `tests/fixtures/si/flow/`」 | 改為建構函式：vitest 用 `tests/helpers/{siFlow.tsx,siClock.ts}`，Playwright 用 `tests/e2e/siFlowFixtures.ts`；入庫的檔只有 `patch-mixed.diff` 與黃金樣本複本 | Playwright 不能引用 vitest 輔助（testing-library、`@` 別名），且新鮮度須依真時鐘計算；前端實作亦以建構函式為準（HB_FE 偏離 3） |
| E-15 | 11-12 | AT-966-16-3 | 「對話框開啟時背景不可聚焦」 | 明寫判定方式：Tab／Shift+Tab 各 60 次焦點不逃出且繞圈，加背景根元素 `aria-hidden` 以 `closest` 判定 | Playwright 的 `toBeHidden` 不看 `aria-hidden`；實作的判定方式與規格意圖一致 |
| E-16 | 11-12 | AT-966-7-E-2（並由 16-2、16-E-1 的 axe 守住） | 「其容器 class 含 `overflow-x-auto` 與 `whitespace-pre`」 | 補「該容器為 `role="region"`、`tabIndex=0`、帶 `aria-label`（`SI_FLOW_TEXTS.diffScroll`）」 | E2E 的 axe 抓到真缺陷 `scrollable-region-focusable`（可捲動容器無法鍵盤聚焦），已於結構層修正；單元層 `SiDiffView.test.tsx` 目前**沒有**對應斷言，前端須在 AT_966_7_E_2 補上 role、tabIndex、aria-label 三項斷言 |
| E-17 | 11-12 | §4.1 `si.endpoints.test.ts` | 「`SI_READ_FUNCTIONS` 加 `getSiPatrol`」 | 另列 PATHS、AT_951_6_2 清單加 `/api/v1/si/patrol`，並要求 describe／it 標題不再寫死路徑與操作數量（`AT_950_10_2`、`AT_951_6_2` 等底線形保留，斷言不動） | 標題中的「十二個」早已過時，每次增端點都漂移 |
| E-18 | 11-12 | §5.1 黃金樣本段 | 「主控複製，複本 sha256 先驗」「待根層樣本」暫態 | 寫成明確的一段：誰複製、三側固定路徑、更新同步（同一 commit 重新複製並核對雜湊）、暫態（xfail／Assumptions／「複本不得先行存在」）必須移除、轉為硬斷言的 AT 清單、CI paths 須涵蓋根層樣本目錄 | 根層樣本已出現（2326／2951 位元組）；各包以暫態分支標示待樣本，需明文規定到位後的轉換 |