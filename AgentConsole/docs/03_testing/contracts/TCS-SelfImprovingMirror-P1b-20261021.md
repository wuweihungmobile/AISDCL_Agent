# Test Contract Specification — SelfImproving Mirror P1b（Console 唯讀鏡像：Bridge `/si/*`、backend `/api/v1/si/**`、frontend `/self-improving`、導覽登記表化）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件已於 Stage-1 採納凍結）的單一 Feature（SelfImproving P1b 階段）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-SelfImprovingMirror-P1b-20261021.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因 Stage-1 含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-901 |
| **Feature 名稱** | SelfImproving P1b：Console 唯讀鏡像——Bridge `GET /si/*`（子行程呼叫根層 `si export`）、backend `GET /api/v1/si/**` 代理、frontend 新頁 `/self-improving`（狀態橫幅、觀察／提案／事件三分頁），加導覽登記表化（`ToolsRegion.tsx` 改讀 `lib/nav/registry.ts`），加部署前置（compose 唯讀掛載、CI `paths`），加順帶兩項（匯入頁節點編輯對話框的執行路徑說明；RTM FsmTrail 區塊以真後端 E2E 升格） |
| **User Story** | US-901～US-907 |
| **建立日期** | 2026-10-21 |
| **輸入快照** | HEAD＝`5593d0bb4c6c1d0df9fdcb7863ad192604aa314f`；Stage-1 六份凍結檔的 digest 於本檔〈增量追溯表〉，SA 已以 `Get-FileHash -Algorithm SHA256` 對工作樹現況逐檔重算、與任務書所列相同 |
| **QA 負責人** | SelfImproving P1b 的 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SA 棒，實作者＝鍵 `agentconsole-si-mirror` 的 hooks-ON 開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-si-mirror`（AgentConsole 子專案 SDD 流程；一律從 monorepo 根啟動 session；啟動 `python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug si-mirror`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（AgentConsole；上位文件＝`docs/01_requirements/SelfImproving_PRD.md` v0.10 與 AgentConsole 的 Architecture、ADR-001、ADR-002、`API_Contract_P3-6.md`、`openapi-p3-6.yaml`，均已於 Stage-1 凍結）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。**凍結檔不得再改**：本檔發現上位文件需修訂之處，一律寫在 §7 的 ⚖ 清單與交卷單，走掌舵者 T1／SPEC_REGRESSION_CHECK；本檔不自行改任何凍結檔，凡上位文件未定、本檔為使其可測而補定義者，一律標「本檔類推」並列入 §7.1。

### FRD-lite

**現況與變更（Before／After；brownfield）**

- Before：(1) Bridge（`AgentConsole/engine-bridge/app/`）只有 `routers/autoclaude.py` 與 `routers/sdd.py`，沒有 SelfImproving 路由、沒有呼叫根層 `tools/selfimproving.py` 的子行程模組、`settings.py` 沒有 `SI_ROOT`；(2) backend 沒有 `/api/v1/si/**`，`AgentBridge` 埠沒有 `siExport`，`BridgeHttpAdapter.handle` 只把 4xx 與 503 `sdd_write_disabled` 視為明確拒絕（其餘 5xx 一律 `UpstreamException.Failure`），`ErrorReasons` 沒有 SI 常數；(3) frontend 沒有 `/self-improving` 頁，`components/layout/ToolsRegion.tsx` 持有硬編 `NAV` 常數（六項）加 `activeNav`／`hrefFor` 分支，`activeNav` 對未知路徑 fallback 成「專案管理」，`layout.test.tsx` 寫死六個標籤；(4) `AgentConsole/docker-compose.yml` 的 engine-bridge 服務只掛 `../AISDLC_SDD:/sdd:ro`、`engine_workspace`、`app_logs`，Bridge 映像無 `tools/`、無 `.git`；`.github/workflows/agentconsole-ci.yml` 的 `paths` 不含根層 SI 檔；(5) `NodeEditDialog.tsx` 的專案節點編輯「執行路徑」欄沒有兩模式說明（同一欄在 `EntityForms.tsx` 已重用 `EXECUTION_PATH_HINT`，OBS-SI-230 把它列為 P1b 順帶項）；(6) `AgentConsole/docs/06_quality/RTM.md` 的 FsmTrail 本地編號子表 14 列停在「✅ 實作+測試」，備註要求 QA 升格而無承接輪次（OBS-SI-202 已決議由 P1b 鍵的 QA 承接）。
- After：Bridge 新增 `app/si_cli.py`（子行程、白名單環境、逾時、輸出判定）、`app/routers/si.py`（六個 GET）、`settings.py` 的 `si_root`（環境變數 `SI_ROOT`），`main.py` 掛路由；backend 新增 `SiController` 與其四層檔案（檔名依 PRD §9.1〈C18 檔名表〉），`BridgeHttpAdapter` 把 503 `si_unavailable` 與 404 `si_not_found` 轉明確拒絕；frontend 新增 `app/self-improving/page.tsx`、`components/domain/si/*`、`lib/api` 的 SI 條目與重產入庫的 `schema.d.ts`、`lib/domain/si.ts`、`lib/nav/registry.ts`（七項）並使 `ToolsRegion.tsx` 只消費登記表；compose 以長語法唯讀掛載 repo 的必要子集並設 `SI_ROOT`，`agentconsole-ci.yml` 的 `paths` 補齊 Bridge 子行程會執行的根層檔；`NodeEditDialog.tsx` 的執行路徑欄重用 `EXECUTION_PATH_HINT`；新增契約後繼檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`（D12，承接 PRD C18 的「契約新版」，凍結的 `API_Contract_P3-6.md` 與 `openapi-p3-6.yaml` 不動）；RTM FsmTrail 區塊由 QA 以真後端 E2E 驗證並交文字證據，主控依該證據升格或寫再開症狀（V6）。**P1b 全程零寫入端點**：Console 是顯示面，不是資料來源，頁面資料＝`si export` 的輸出。

**AC 編號規則**（本節回答「PRD 的 AC 與本檔的 AC 怎麼對應」，並記錄與任務書字面不同之處）：

1. **編譯文法**：ADR-XPLAT-016 §8.1 規定 AC 文法為 `AC-[\d\-]+`、AT 文法為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC。PRD 的 `AC-SI-NN-Y`、PRD §5〈編號注意〉的階段前綴形（本階段為 `AC-P1b-032-1` 一類）與任務書舉例的 `AC-132b-1` 都含字母，照寫則 §1 映射列不被 `sdd_compile` 收、AT 列入 `unmapped_at_ids`（rc 6）。**本檔採雙名**：§1、§2 等機器可讀位置一律用合文法的數字 id；人讀處（FRD-lite 表的 AC 欄、§6）一律同時寫出 PRD 全名。
2. **對映規則**：**百位 `9`＝AgentConsole 側**（根層 P1 TCS 用百位 `1`、根層 P2 TCS 另編，三者不撞號）。PRD 的 AC：`AC-SI-32-Y`＝本檔 `AC-932-Y`（P1b 範圍為 Y＝1、2、3、4、6；`AC-SI-32-5` 是根層 `export` 半、由根層 P1 TCS 承接，不在本檔）。本檔自增 AC：FR 號位自 40 起編，名為 `AC-940-1` 起（其階段前綴形為 `AC-P1b-040-1`），FRD-lite 表逐條標示來源（PRD 明文者標座標；PRD 只給機制未給編號者標「本檔自增」；PRD 未定、本檔為使其可測而補定義者標「本檔類推」）。
3. **與任務書的差異**：任務書寫「AC 編號百位 `1`＋`b` 後綴（例 `AC-132b-1`），與文法不合時改用 `AC-932-1`（九百位＝AgentConsole 側）並在本節寫明」；`b` 後綴不合文法，故採 `AC-932-1`（§7.1 ⚖ 1）。
4. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控／邊界 `AT-<AC 數字 id>-E-<序>`；測試函式名含其底線形（`AT-932-3-2`→`AT_932_3_2`；Java 方法名以底線形開頭，後接駝峰敘述，例 `AT_932_3_5_bridgeUnavailableIsRelayedVerbatim`，Checkstyle 規則集無方法命名規則，已實查）。每個 AC 內數字序與 E 序各不超過 9，使 `-k`／`-t`／`--tests` 的子字串比對不會誤收其他 AT。
5. **AC 數**：PRD 的 AC 5 個加本檔自增 9 個，合計 14 個（見 §1 覆蓋率統計）。

**P1b 交付物**（D1～D13；路徑一律相對 monorepo 根）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | Bridge 子行程層：`run_export`、常數、白名單環境、輸出判定、失敗碼 | `AgentConsole/engine-bridge/app/si_cli.py`（新；整個 `app/` 只有此檔出現字面 `selfimproving.py`） | 開發 agent | AC-932-3、AC-940-2 系列 AT |
| D2 | Bridge 路由與設定：六個 GET、`si_root`／`SI_ROOT`、掛路由、README | `AgentConsole/engine-bridge/app/routers/si.py`（新）、`app/settings.py`（改）、`app/main.py`（改一行 `include_router`）、`AgentConsole/engine-bridge/README.md`（改：端點與環境變數） | 開發 agent | AC-932-1／932-2／940-1／940-9 系列 AT |
| D3 | Bridge 測試與夾具 | `AgentConsole/engine-bridge/tests/{test_si_cli,test_si_routes,test_si_export_differential,test_si_readonly_lock,test_si_deploy_config}.py`、`fake_si.py`、`si_repo_support.py`、`si_golden_regen.py`（新）；`tests/fixtures/si_repo/**`、`tests/fixtures/si_golden/**`（新；§5） | 開發 agent | 各 AT 自身；AC-940-7 |
| D4 | backend 代理：控制器、DTO、用例埠、服務、`AgentBridge.siExport`、領域物件、介面卡與 `handle()` 改動、端點基底、reason 常數 | 依 PRD §9.1〈C18 檔名表〉backend 列（`SiController`、`SiExportResponse`＋`SiObservationDto`／`SiProposalDto`／`SiRunDto`／`SiStatusDto`、`SiMirrorUseCase`、`SiMirrorQueryService`＋`SiBridgeErrors`、`SiExport`、`BridgeHttpAdapter`、`BridgeEndpoints.siBase()`、`ErrorReasons`），加本檔類推的 `SiKeyNames`（§7.1 ⚖ 19）；`NotFoundException` 的類別 Javadoc、`ErrorResponseDocumentation`（程式註解與 OpenAPI 說明字串）與 `ErrorReasons` 的 `RTM_NOT_FOUND` Javadoc 中的「唯一例外」字樣隨之改寫（R26；§7.1 ⚖ 11） | 開發 agent | AC-932-1／932-2／932-3／932-4 的 backend 側 AT |
| D5 | backend 測試與夾具 | `SiMirrorApiIT`、`SiKeyNamesTest`、`BridgeHttpAdapterSiTest`、`SiReadOnlyArchTest`；`MiniBridge`／`MiniBridgeController` 的 SI 擴充；`backend/src/test/resources/si/golden-*.json`（新或改；§5）；**既有 `OpenApiIT`**（`EXPECTED` 加六筆 SI 路徑、路徑數 `hasSize(61)` 改 67、操作總數 70 改 76、Javadoc 補一句；只增不減，§4） | 開發 agent | 各 AT 自身；`OpenApiIT` 本身續綠 |
| D6 | frontend 頁與元件 | `AgentConsole/frontend/app/self-improving/page.tsx`、`components/domain/si/SiView.tsx` 及子元件（狀態橫幅、三分頁、卡面逐字區、篩選列）；測試與夾具：`components/domain/si/SiView.test.tsx`、`components/domain/si/si.static.test.ts`、`tests/helpers/si.tsx`（測試輔助，沿既有 `tests/helpers/` 先例：不被 vitest 收集、不在 `design-rules` 掃描面、不屬三個靜態掃描的「非測試原始碼」）、`components/layout/si-login-gate.test.tsx`、`tests/fixtures/si/**`（黃金檔副本，§5.4） | 開發 agent | AC-932-1／932-2／932-3／932-4 的 frontend 側 AT |
| D7 | frontend API 層與純函式 | `lib/api/endpoints.ts`／`queries.ts`／`types.ts`（改）、`lib/api/schema.d.ts`（由 `openapi-typescript` 重產入庫）、`lib/domain/si.ts`（新）；`lib/api/reasons.ts`（**只改** `RTM_NOT_FOUND` 的註解、不動任何常數，R26）；測試：`lib/domain/si.test.ts`、`lib/api/si.endpoints.test.ts`；**既有 `lib/api/endpoints.test.ts`**（`EXPECTED` 加六列 `getSi*`、數量 `toHaveLength(68)` 改 74；只增不減，§4） | 開發 agent | AC-932-1／940-5／940-8 的 frontend 側 AT；`endpoints.test.ts` 本身續綠 |
| D8 | 導覽登記表化 | `lib/nav/registry.ts`（新）、`registry.test.ts`（新）、`components/layout/ToolsRegion.tsx`（改為只消費）、`ToolsRegion.test.tsx`（新）、`components/layout/layout.test.tsx`（導覽斷言改由登記表驅動） | 開發 agent | AC-932-6 系列 AT |
| D9 | 順帶：匯入頁節點編輯對話框的執行路徑說明 | `components/domain/import/NodeEditDialog.tsx`（改一處）、`NodeEditDialog.test.tsx`（新） | 開發 agent | AC-940-6 的 AT |
| D10 | 部署前置 | `AgentConsole/docker-compose.yml`（改：`SI_ROOT`、唯讀掛載） | 開發 agent | AC-940-3 的 AT；實查 V3 |
| D11 | CI 觸發範圍 | `.github/workflows/agentconsole-ci.yml`（改 `paths`；**屬根層，開發 agent 回報、由主控同一 commit 代改**，`AgentConsole/CLAUDE.md` 鐵律 7） | 主控 | AC-940-4 的 AT |
| D12 | 文件連動：契約後繼檔、RTM、SCG-4 報告，以及 RELEASE 之後的 Architecture 修訂 | (a) **契約後繼檔（新檔）**`AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`（承接 PRD §9.1 C18 的「契約新版」；內容與來源見 R26；§7.1 ⚖ 12）；(b) `AgentConsole/docs/06_quality/RTM.md` 的本地編號子表（FsmTrail 區塊升格依 V6）；(c) **根層 RTM** 的 FR-SI-32 列（`docs/06_quality/RTM-SelfImproving-<Phase>-<日期>.md`，檔名依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2；PRD 指定的 FR-SI 追溯主載體）；(d) `AgentConsole/docs/06_quality/` 的 SCG-4 報告；(e) **RELEASE 之後另以純文件 commit**：`Architecture.md`（Stage-1 凍結檔，不在實作 commit 內改）去除〔P1b 規劃〕註記並回寫 §12.1 L-14、§12.2 V-12 結論與 `cause` 補句（R26） | (a) 主控（SCG-5，與實作同一個 commit；開發 agent 於交卷以純文字附後繼檔全文草稿——其在 IMPLEMENTATION 態寫不進 `docs/02_architecture/`，R26）；(b)(c)(d) 主控（SCG-5）；(e) 主控（RELEASE 之後） | (a) V8 的存在性核對；其餘 §6 與 V 系列 |
| D13 | 實查（V 系列，非 AT） | 真後端全棧差分、真瀏覽器、真容器、冷啟動量測、FsmTrail E2E 驗證（RTM 升格由主控依 QA 文字證據改）、掌舵者真機瀏覽 | QA、掌舵者 | §6.2 的 V1～V10 |

**提交順序與責任**

- 依賴序為 D1／D2（Bridge）→ D4（backend 介面卡→服務→控制器）→ D7（API 層與純函式）→ D6（頁面）→ D8（登記表與消費端）→ D9 → D10；D3、D5 與各自受測碼同步完成；D12 (a) 的契約後繼檔全文草稿由開發 agent 在 D2、D4 完成後依實作如實起草、於交卷以純文字附上（主控落檔，R26）。**D7 的 `schema.d.ts` 重產需要後端在線**：`npm run gen:api`（`scripts/gen-api.mjs`）預設自 `http://localhost:8080/v3/api-docs` 取得 OpenAPI，所以必須在 D4 已含六個 SI 路徑、且 backend 已啟動（`bootRun`；環境變數見 `AgentConsole/CLAUDE.md`）之後執行，重產結果入庫。每支程式完成立即編譯並跑該區 AT（`AgentConsole/CLAUDE.md` 鐵律 11），不累積。
- 開發 agent **不准 commit／push**；`.github/` 與根層 `tools/` 一律不動（鐵律 7）：需要根層改動者回報主控。與實作**同一個 commit** 收齊者：D11（主控代改）、D12 的 (a) 契約後繼檔（主控落檔）、R26 (1) 列的註解字樣連動與 README（根 `CLAUDE.md` 第 5 條「修復不留後遺症」）；D12 的 (b)(c)(d) 由主控於 SCG-5 收齊；**D12 的 (e) Architecture 修訂屬 Stage-1 凍結檔，不在實作 commit 內改，於本鍵 RELEASE 之後另以純文件 commit 做**（內容清單見 R26，不留未登記的尾巴）。
- **AC-940-4 的 AT 依賴主控的 D11**：開發 agent 不得動 `.github/`，所以該 AC 的 AT 在主控補上 `agentconsole-ci.yml` 的 `paths` 之前為**預期紅**；開發 agent 於交卷時逐行列出需要新增的 `paths` 項（`CLI_CLOSURE` 與 `PARAMS_SRC` 的每一項，`pull_request` 與 `push` 兩處），主控於同一個 commit 補上後轉綠（該 AT 的紅燈是連動面未收齊的偵測，不得以改弱測試處理）。
- 真帳本、真事件帳本、真 `SelfImproving_Proposals/` 一律唯讀：AT 只用 `tests/fixtures/si_repo/` 的凍結複本與 tmp 目錄的合成 repo；P1b 出口 (e)（掌舵者真機瀏覽 `/self-improving`）與 V 系列由 QA／掌舵者執行，不由 AT 充當。
- 依賴：本鍵依賴根層 `export`、`status`、`card`（P1 已落地於 HEAD，實查：`tools/lib/selfimproving/export.py` 存在）；`export` 的 `buckets[]`（模組桶）屬根層 P2 鍵，**P1b 不等它**——前端於該欄缺席時降級（R17），欄位出現後零改動即可顯示（AC-932-1 的負控釘住）。

**〈P1b 行為規則〉**（R1～R29；各 AT 以 R 編號引用；三個服務各自的規則分節，跨服務的契約只定義一次、其餘引用。實查依據：`AgentConsole/engine-bridge/app/{sdd_cli,settings,errors,main}.py` 與 `routers/sdd.py`、`backend` 的 `BridgeHttpAdapter`／`SddBridgeErrors`／`GlobalExceptionHandler`／`SecurityConfig`、`frontend` 的 `ToolsRegion.tsx`／`layout.test.tsx`／`lib/api/reasons.test.ts`／`ContentRegion.tsx`、根層 `tools/lib/selfimproving/export.py` 與 `status.py`，以及 SA 棒在 scratchpad 對真 CLI 的唯讀探針）

*A. Bridge（`AgentConsole/engine-bridge/app/`）*

- **R1 `SI_ROOT` 設定**：`Settings` 新增欄位 `si_root: Path | None = None`（置於既有欄位之後、帶預設值；既有 `Settings(...)` 呼叫皆為關鍵字，不受影響）。`load_settings`：環境變數 `SI_ROOT` 去空白後非空 → `Path(raw).resolve()`，並過 `_anchor_guard(path, "SI_ROOT")`（解析結果為檔案系統根或磁碟機根 → `SettingsError`，啟動即失敗）；不檢查存在性與內容（存在性在請求時判，R4）。空白或未設 → `_looks_like_monorepo(REPO_ROOT)` 為真取 `REPO_ROOT.resolve()`，否則 `None`。`si_root` 不併入 `allowed_path_roots`（那是引擎 `execution_path` 的閘，NFR-SEC-03）。`settings.py` 檔頭環境變數一覽與 `engine-bridge/README.md` 的環境變數表各加 `SI_ROOT` 一列。
- **R2 `si_cli.py` 常數與入口**：`SI_CLI_TIMEOUT_SECONDS = 15.0`（呼叫時才讀，測試可改）、`SI_EXPORT_SCHEMA_REV = 1`、`SI_STDOUT_MAX_BYTES = 8 * 1024 * 1024`、`SI_STDERR_TAIL_CHARS = 1000`、`SI_KINDS = ("observations", "events", "proposals", "runs", "status")`（封閉集合，路由只能傳這五值）。入口 `run_export(si_root, kind, *, since=None, limit=None, ident=None) -> dict`：成功回傳解析後的 export 物件；失敗一律拋 `ApiError(503, "si_unavailable", cause=<碼>, detail=<字串>)`；不寫任何檔、不快取；失敗時 `logger.warning` 一行（不含環境值）。
- **R3 子行程**：argv 恰為 `[sys.executable, <si_root>/tools/selfimproving.py, "export", "--json", "--kind", <kind>]` 之後依序可接 `--since <n>`、`--limit <n>`、`--id <id>`；**不帶 `--repo`**（預設值＝腳本所在 repo＝`si_root`；少一個可被誤用的旗標，§7.1 ⚖ 7）；**不帶 `-I`／`-P`**（3.11 起 `-I` 蘊含 `-P`，腳本目錄不進 `sys.path`，`import _stdio_utf8` 與 `from lib…` 會失敗；PRD §9.2 鐵律三自問表）。cwd＝`si_root`；`stdin` 為 `DEVNULL`；`stdout`、`stderr` 為管道；平台旗標走 `procutil.popen_platform_kwargs()`；逾時以行程樹終止（`procutil.begin_terminate`／`force_kill`，不直接 `os.kill`；Windows 行為＝新行程組、無視窗、`taskkill` 不用）。環境＝白名單加固定鍵：白名單名稱 `PATH`、`SYSTEMROOT`、`TEMP`、`TMP`、`HOME`、`USERPROFILE`、`LANG`、`LC_ALL`（名稱不分大小寫比對，值取自 Bridge 自己的環境，缺者不補）；固定鍵 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`、`GIT_CONFIG_COUNT=1`、`GIT_CONFIG_KEY_0=safe.directory`、`GIT_CONFIG_VALUE_0=<str(si_root)>`（只放行該路徑，不用 `*`）。**其餘任何變數一律不繼承**（含 `BRIDGE_*`、`MINIMAX_API_KEY`、`AUTOSDD_*`、`SDD_*`、`PYTHONPATH`、`CLAUDE*`）。環境建構為純函式（輸入來源映射、輸出 dict），供單測。
- **R4 失敗判定**（依序，先中者定案；`cause` 取值與順序固定）：

| 順序 | `cause` | 條件 |
|------|---------|------|
| 1 | `si_root_unset` | `si_root` 為 `None` |
| 2 | `si_script_missing` | `si_root` 不是目錄，或 `<si_root>/tools/selfimproving.py` 不是檔案 |
| 3 | `spawn_failed` | 啟動子行程拋 `OSError` |
| 4 | `timeout` | 超過 `SI_CLI_TIMEOUT_SECONDS` 仍未結束（行程樹已終止） |
| 5 | `stdout_too_large` | stdout 位元組數超過 `SI_STDOUT_MAX_BYTES`（行程已終止，不等它自然結束） |
| 6 | `nonzero_rc` | rc 非 0 |
| 7 | `bad_json` | stdout（UTF-8 解碼、去尾端空白）不是恰好一份 JSON 文件，或解出來不是物件 |
| 8 | `schema_rev_mismatch` | 物件缺 `schema_rev`、不是整數，或不等於 `SI_EXPORT_SCHEMA_REV` |
| 9 | `bad_shape` | 物件的 `kind` 不等於請求的 kind，或 `items` 不是陣列 |

  失敗本文恆為 `{"code": 503, "reason": "si_unavailable", "cause": <碼>, "detail": <字串>}`（`cause` 為本檔類推，§7.1 ⚖ 4）。`detail` 格式恆為 `rc=<n 或 none>; stderr=<尾段>`：`<n>` 為離開碼（未啟動，或被 Bridge 終止〔逾時、超量〕而沒有離開碼＝`none`）；`<尾段>` 為 stderr 以 UTF-8（`errors=replace`）解碼後的**最後 `SI_STDERR_TAIL_CHARS` 個字元**。順序 1～3 沒有行程：`stderr=` 之後改填 Bridge 自寫的固定說明（含字樣 `SI_ROOT`；順序 3 另含例外類名）。**合法輸出不是錯誤**：rc 0、stdout 為合法 export 物件即原樣回傳，即使 `items` 為空、`ne`／`problems` 非空、stderr 有雜訊、物件含未知的額外鍵（空表只在 SI 真的回空時合法；PRD AC-SI-32-3）。
- **R5 路由**（`routers/si.py`；`router = APIRouter(prefix="/si", tags=["si"])`；`main.py` 加一行 `app.include_router(si.router)`）：六個 GET——`/si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs`。清單類（observations、events、proposals、runs）收 `since`（整數 ≥0）與 `limit`（整數 ≥1）；`/si/status` 與 `/si/proposals/{id}` 不收任何查詢參數。任何其他查詢參數名（含這兩個端點上的 `since`、`limit`）＝422 `invalid_request`（`violations[]` 一筆，`field` 為參數名、`rule` 為 `unknown_parameter`；§7.1 ⚖ 5）；型別或範圍不合（`since=abc`、`since=-1`、`limit=0`）＝422 `invalid_request`（沿 Bridge 既有 `RequestValidationError` 處理器）。`{id}` 須符 `^PROP-SI-\d{3,}$`，不符＝422 `invalid_request`（會被路由器擋在路徑層而回 404 的形態除外；兩者皆**不得啟動子行程**）；符合而 `export --id` 回 `items: []`＝404 `si_not_found`（本文 `{"code": 404, "reason": "si_not_found", "id": <id>}`）；符合且有資料＝200，本文為完整 export 物件（`items` 恰一筆）。`limit` 的上限不在 Bridge 複製（`export_limit_max` 住 `params.json`）：超過上限時 CLI 回 rc 3，Bridge 依 R4 回 503 `nonzero_rc`（§7.1 ⚖ 6）。200 時本文為子行程輸出**解析後的 export 物件逐值透傳**（含 `generated_at`、`head_sha`、`ne`、`problems`；鍵序保留、非 ASCII 不跳脫；Bridge 不增刪改任何鍵）。非 GET 一律 405（FastAPI 預設）；未定義的 `/si/…` 路徑 404。Bridge 對 SI 不加快取：每個請求恰一次子行程。SI 不可用**不影響** `/health` 與 `/health/deep`（SI 與 SDD 同為選用面，不進健康判準）。
- **R6 唯讀不變量與 AST 鎖**（`tests/test_si_readonly_lock.py`；邊界型 M，誠實劃界見 §4）：鎖的判準為純函式（輸入為原始碼文字或 `app/` 樹，輸出違規清單），對真原始碼須回空、對各違規樣本須逐一回非空。① **寫入形態呼叫**：`si_cli.py`、`routers/si.py` 與原始碼含 `selfimproving`（不分大小寫）字樣的其他 `app/` 模組，零個寫入形態呼叫（掃描器自 `tests/test_sdd_integration_parity.py` 的 `write_shaped_calls` import，不複製）；② **`app/` 全樹**：不得有 `import lib…`／`from lib…`／`import tools…`／`from tools…`（含 `importlib` 對這兩名的字面呼叫），不得有任何對 `sys.path` 的變更（`insert`、`append`、`extend`、賦值、增量賦值）；③ 字面 `selfimproving.py` 在 `app/` 只出現在 `si_cli.py`；④ **argv 動詞形態**：`si_cli.py` 中組 argv 的函式恰一個，其唯一 `return` 為列表字面值、索引 2 的元素為字串常數 `export`；`si_cli.py` 的 `Popen` 呼叫恰一處且其 argv 引數來自該函式；動詞白名單常數（住在鎖的測試檔內）為 `{("export",), ("obs-add", "--dry-run")}`（後者為 P2b 預留，P1b 的 `si_cli.py` 不得組出它；§7.1 ⚖ 25）；⑤ **動態對照**：對五個 kind 與全部旗標組合呼叫該函式，argv 的動詞位置恆為 `export` 且不含 `--repo`。

*B. backend（`AgentConsole/backend/`）*

- **R7 端點、參數與權限**（`SiController`；`@RequestMapping("/api/v1/si")`）：六個 GET——`/status`、`/observations`、`/events`、`/proposals`、`/proposals/{id}`、`/runs`；清單類收 `since`（整數 ≥0）與 `limit`（整數 ≥1），型別或範圍不合沿既有驗證處理（400）；**未知查詢參數不轉發**：送往 Bridge 的 URL 只由 kind 與上述參數組成。`{id}` 原樣（嚴格 percent-encode 為單一路徑段；整段恰為 `.` 或 `..` 時，點字元亦編為 `%2E`，避免被 HTTP 堆疊當作路徑穿越）交給 Bridge，backend 不另驗格式（單一真相在 Bridge；§7.1 ⚖ 29）。含編碼斜線、編碼百分號、分號、反斜線或未正規化路徑段的網址，會在進入控制器之前被 Spring Security 預設的 `StrictHttpFirewall` 以 400 拒絕（本專案未調整防火牆設定；實查 `backend/src` 無相關設定），所以這類 id 形態只能在介面卡層驗證編碼（AT-932-3-4），不經 HTTP 送入 backend。權限：`SecurityConfig` 零改動、既有規則涵蓋——無有效 JWT＝401；VIEWER／OPERATOR／ADMIN 的 GET＝可讀；非 GET 對 VIEWER＝403（被 `SecurityConfig` 擋下）、對 OPERATOR／ADMIN＝405（沒有任何非 GET 對映）；未定義的 `/api/v1/si/…` 路徑＝404。`SiController` 與所有 `Si*Controller` 不得有 `@PostMapping`、`@PutMapping`、`@PatchMapping`、`@DeleteMapping`，`@RequestMapping` 不得帶 `method`。
- **R8 失敗對映**（Bridge→backend）：`BridgeHttpAdapter.handle` 把 503 `si_unavailable` 與 404 `si_not_found` 視為明確拒絕（沿 `sdd_write_disabled` 的處理）並轉 `BridgeRejectedException`；`SiBridgeErrors` 依下表對映，其餘 `BridgeRejectedException` 一律當作上游故障。

| Bridge 回應 | backend HTTP | `reason` | `details` |
|-------------|--------------|----------|-----------|
| 200 且本文為合法 JSON 物件 | 200（`ApiResult.ok`） | — | — |
| 503 `si_unavailable` | 503（`ServiceUnavailableException`） | `si_unavailable` | `detail`＝Bridge 的 `detail` 逐字；`cause`＝Bridge 的 `cause` 逐字（有才帶） |
| 404 `si_not_found` | 404（`NotFoundException` 的帶 reason 形態） | `si_not_found` | `id`＝Bridge 本文的 `id`（有才帶） |
| 422 `invalid_request` | 422（`UnprocessableException`） | `ErrorReasons.BRIDGE_REJECTED` | `bridgeReason`＝`invalid_request`、`violations` 逐項原樣（沿 `BridgeErrors.rejected()` 與 `SddBridgeErrors` 的既有同形處理） |
| 其他 4xx 與 5xx | 502（`UpstreamException.Failure`） | `ErrorReasons.BRIDGE_ERROR` | `bridgeStatus` |
| 連線失敗 | 502（`UpstreamException.Unavailable`） | `ErrorReasons.BRIDGE_UNREACHABLE` | — |
| 讀取逾時 | 504（`UpstreamException.TimedOut`） | `ErrorReasons.BRIDGE_TIMEOUT` | — |
| 200 但本文不是 JSON 物件 | 502（`UpstreamException.Failure`） | `ErrorReasons.BRIDGE_ERROR` | `bridgeStatus`＝200 |

  連線逾時 2 秒、讀取逾時 20 秒、**不重試**（每個 backend 請求最多一次 Bridge 呼叫）；任何失敗的回應都**沒有 `data`**——不回空表、不回部分資料、不回上一次的結果。`si_not_found` 是「404 的 reason 省略」慣例的第二個例外（第一個是 `rtm_not_found`；§7.1 ⚖ 11）。`invalid_request`（422）是 **Bridge 層**的 reason：backend 回應的頂層 `reason` 為 `ErrorReasons.BRIDGE_REJECTED`，`invalid_request` 只經 `details.bridgeReason` 帶出，所以前端不為它建 reason 常數（R19）。
- **R9 欄名對映與透傳**（AC-SI-32-1 所稱「snake_case↔camelCase 對映」的唯一定義；§7.1 ⚖ 2）：對映函式 `camel(key)`——鍵若符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$`，依 `_` 切段、首段不動、其後各段首字元轉大寫（數字不變）、串接（`http_status`→`httpStatus`、`touched_sha256`→`touchedSha256`、`marks_kv`→`marksKv`、`schema_rev`→`schemaRev`）；**其餘鍵恆等**（`digest8`、`PROP-SI-004`、`quota-band`、中文鍵、已含大寫的鍵、單字鍵、`a__b`、`_x`、`x_`）。套用範圍：回應 `data` 內**所有層級的所有物件鍵**；值（字串、數字、布林、`null`、陣列元素的個數與順序）一律不動；`null` 必須保留（`head_sha`、`next_since`、`cooldown`、`reviewer` 等的 `null` 有語意）；`card` 字串逐位元組不動（含 `\n` 與全形字元）。**透傳**：Bridge 回的任何鍵（含 backend 尚不認得者，例如日後根層 P2 加的 `buckets`、`console_pending`）都必須出現在回應，鍵經 `camel` 對映、值不動；具型別的 DTO 須帶未知鍵的兜底（`@JsonAnyGetter` 或等價），不得靜默丟棄。backend **不重算**：不折疊事件、不算 digest、不判 NE、不補 `generated_at`（回應的 `generatedAt` 是子行程的值，不是 backend 的時鐘）、不快取（每個請求恰一次 Bridge 呼叫）。測試入口：公開靜態方法 `SiKeyNames.camel(String)`（`com.aisdlc.console.adapter.in.web.dto`；§7.1 ⚖ 19）。
- **R10 契約面**：springdoc 的 `/v3/api-docs` 含六個 `/api/v1/si/…` 路徑、各只有 `get`；operationId 依既有慣例為 `getSiStatus`、`getSiObservations`、`getSiEvents`、`getSiProposals`、`getSiProposal`、`getSiRuns`；`ErrorReasons` 新增 `SI_UNAVAILABLE = "si_unavailable"` 與 `SI_NOT_FOUND = "si_not_found"`；`BridgeEndpoints.siBase()` 的解析規則同 `sddBase()`（設定 `sdd.engineUrl` 優先，否則 `ENGINE_BRIDGE_URL`，去尾端斜線；SI 沒有自己的 engineUrl 設定鍵；§7.1 ⚖ 14）；`AgentBridge` 埠上名稱以 `si` 起頭的方法恰為 `SiExport siExport(String kind, Integer since, Integer limit, String id)`；領域物件 `SiExport` 以 `Map<String, Object> raw()` 持有 Bridge 的原樣 JSON（snake_case 鍵、值未動；§7.1 ⚖ 19）。

*C. frontend（`AgentConsole/frontend/`）*

- **R11 API 層**：`lib/api/endpoints.ts` 新增且只新增六個函式——`getSiStatus()`、`getSiObservations(opts?)`、`getSiEvents(opts?)`、`getSiProposals(opts?)`、`getSiProposal(id)`、`getSiRuns(opts?)`（`opts` 為 `{ since?, limit? }`，`undefined` 不進網址）：全部 `GET`、經 `apiRequest`、路徑為 `/api/v1/si/…`、`id` 以 `encodeURIComponent` 編碼；匯出名稱中凡符合 `^(post|put|patch|delete)Si` 者為零。`lib/api/queries.ts` 的 SI 查詢一律 `retry: false`、`staleTime: 0`、`gcTime: 0`（覆寫 `Providers` 的預設：不留過期快取、5xx 也不重試）。`lib/api/types.ts` 的 SI 型別欄名為 R9 對映後的 camelCase。`lib/api/schema.d.ts` 以 `npm run gen:api` 重產入庫，含六個 `/api/v1/si/…` 路徑且各只有 `get`。前端原始碼（測試除外）不得出現 Bridge 路徑字面（以 `/si/` 起頭、且不屬 `/api/v1/si/` 的字串）——瀏覽器不直連 Bridge（Architecture §10.1）。
- **R12 頁面骨架與三態**：`app/self-improving/page.tsx` 是只殼（`export const metadata = { title: "自我進化" }` 加 `export default` 渲染 `<SiView />`），全文不得出現 `TopRegion|ToolsRegion|ContentRegion|BottomRegion` 字樣（含註解；`layout.test.tsx` 既有掃描）。`SiView` 為 `"use client"`；`data-testid="si-view"`；`h1` 文字 `自我進化`；頁首有按鈕 `重新整理`（`data-testid="si-refresh"`），點擊對目前顯示的所有面板 `refetch`。**每個資料面板各自獨立取數、各自有 loading／error／ok 三態**（狀態橫幅一個查詢、目前分頁的清單一個查詢、事件分頁另有運轉查詢）：loading＝`role="status"` 且文字含 `載入中`；error（`isError` 為真）＝只顯示錯誤態，含 `ErrorState`（標題 `自我進化資料無法取得`）、`data-testid="si-error-summary"`（一句摘要，內容見 R19）、`si-error-reason`（`ApiError.reason` 逐字）、`si-error-detail`（`details.detail` 逐字，有才顯示）、`si-error-cause`（`details.cause`，有才顯示）、按鈕 `重試`（`data-testid="si-retry"`，觸發該查詢 `refetch`）——**不渲染 `data`**（即使快取殘留上一次成功的資料）；ok＝渲染內容。任何面板的 error 不得被渲染成空表、零筆、「無事件」或「通過」。
- **R13 狀態橫幅**（`data-testid="si-status-banner"`；資料＝`status` 的 `items[0]`，欄名為 R9 對映後）：`si-head-sha` 顯示 `headSha` 前 8 碼（完整值在 `title`），`headSha` 為 `null`＝顯示 `量不到（NOT-EVALUABLE）`並於 `si-ne-list` 列出對應的 `ne` 項；`si-generated-at` 顯示 `generatedAt` 原字串。事件：`eventsDetected` 非空＝逐筆列出（`trigger`、`subject`、`detail`；`si-events-detected`）；為空＝`si-no-event`，文字為 `無事件`（`unavailable` 為空）或 `無事件（尚有 <k> 項量不到）`（`unavailable` 長度 k>0），且 `unavailable` 逐項列於 `si-unavailable`（`trigger` 與 `reason`）。另顯示 `openRuns`（`si-open-runs`）、`pendingProps`（`si-pending-props`：`id`、`rev`、`state`、`route`、`digest8`）、`suspended`（`si-suspended`：`null`＝`無`，物件＝緊湊 JSON 純文字）、`cooldowns`（`si-cooldowns`）、`skipReasons`（`si-skip-reasons`：`鍵：值` 逐項）、`capacity`（`si-capacity`）、`frictionReconcile`（`si-friction`）。橫幅**每個**頂層鍵至少有一個可見呈現；不認得的鍵（如日後的 `consolePending`）以 `鍵：緊湊 JSON` 純文字列在 `si-status-extra`，不丟欄位。export 層級的 `ne[]` 逐項列為 `<field>：<reason>`（`si-ne-list`）、`problems[]` 逐項列為 `<subject> <code> <detail>`（`si-problems-list`）；兩者為空時不顯示該區（不顯示「0 項」）。
- **R14 三分頁與詳情**（`role="tablist"`、`aria-label="自我進化資料"`；分頁名 `觀察`、`提案`、`事件`，預設 `觀察`；分頁標籤帶已載入筆數，`truncated` 為真時筆數後加 `+`）：**觀察**（`si-panel-observations`）每筆一列（`si-obs-row-<ID>`），欄為 `ID`、`時間`、`分類`、`嚴重度`、`處置`、`症狀`（DOM 文字為完整字串，截斷只准用 CSS）；列可展開（`<button aria-expanded>`，名稱 `展開 <ID>`），展開後 `si-obs-fields-<ID>` 逐欄顯示九欄原文——欄標籤逐字取自帳本表頭：`ID`、`時間`、`情境`、`症狀`、`證據座標`、`分類`、`嚴重度`、`處置`、`標記`——另顯示 `marksKv`（`鍵：值` 逐項）、`line`、`buckets`（有才顯示）。`valid` 為 `false` 的列（無法解析）永遠顯示為 `si-obs-invalid-<line>`：文字 `無法解析的列（第 <line> 行）` 加 `raw` 原文（`<pre>`），**不受任何篩選影響**。**提案**（`si-panel-proposals`）每筆一列（`si-prop-row-<ID>`），欄為 `ID`、`狀態`（`state`）、`類別`（`cls`）、`route`、`rev`、`digest`（前 8 碼）、`verdict`、`cooldown`；`state` 為 `proposed` 或 `verified` 的**待決提案預設展開**、其他可展開；展開區 `<pre data-testid="si-card-<ID>">` 的 `textContent` **逐位元組等於**該筆 `card` 字串（含換行、全形字元與結尾換行；前端不渲染、不重排行、不裁切、不加前後綴）；`card` 為 `null` 時顯示 `卡面量不到（NOT-EVALUABLE）`並指向對應 `ne` 項。**事件**（`si-panel-events`）上半「運轉」表（資料來自 `/si/runs`：`id`、`trigger`、`openedSeq`、`closedSeq`、`outcome`、`propIds`、`research`；`si-runs-table`；§7.1 ⚖ 10），下半「事件帳本」列表（`seq`、`t`、`kind`、`by`；`si-events-table`）；事件詳情 `si-event-json-<seq>` 顯示該事件物件（R9 對映後的 camelCase 鍵、值不動）的 `JSON.stringify(obj, null, 2)` 純文字（§7.1 ⚖ 3）。`truncated` 為真時顯示 `si-filter-scope-note`（`篩選只作用於已載入的 <n> 筆，尚有更多未載入`）。每個分頁面板的頂端同樣以 `si-ne-list` 與 `si-problems-list`（各在該面板容器內）列出**該面板回應**的 `ne[]` 與 `problems[]`（為空時不顯示），使壞列的 `ROW-ARITY`、事件載體缺席、卡面量不到等原因都看得見。
- **R15 分頁與游標**：清單查詢的 `limit` 取常數 `SI_PAGE_LIMIT`（`lib/domain/si.ts` 匯出，初值 100；§7.1 ⚖ 24）；`truncated` 為真時顯示按鈕 `載入更多`，點擊以 `since=<nextSince>` 與同一 `limit` 取下一頁，結果以 `lib/domain/si.ts` 的純函式 `mergePages` 併入——依序串接、依身分鍵去重（`id`、`seq`、`line`，保留先到者）、不丟任何一筆；末頁（`truncated` 為假）按鈕消失。`status` 不分頁。
- **R16 NE 與量不到的呈現**（NFR-SI-09-1；PRD AC-SI-32-3 末句）：凡 `{status: "NOT-EVALUABLE"}` 形態的物件、`headSha: null`、`card: null`、`ne[]` 的項、`unavailable[]` 的項，一律以文字 `NOT-EVALUABLE`（或 `量不到`）加原因呈現；不得顯示為 0、空字串、「無」、「通過」、「正常」。`items` 為空而 `ne` 含 `field` 為 `events`、`reason` 為 `carrier-not-established` 的項時，事件分頁顯示該 NE 說明，不得只顯示「沒有事件」。
- **R17 篩選**（`lib/domain/si.ts` 純函式加控制項；控制項為原生 `<select>`，`aria-label` 即欄名，預設選項 `全部`）：**觀察**有 `分類`（`category`）、`嚴重度`（`severity`）、`處置`（依 `dispositionKey`：處置字串自頭起、到第一個 `：`、`；`、`;`、`:`、`@` 或空白為止的首詞；首詞以 `DEF-` 起頭者併為 `DEF-*`；§7.1 ⚖ 20）、`模組桶`（`buckets`）、`時間窗`（`全部`、`今天`、`近 7 天`、`近 30 天`）。選項一律**取自已載入資料的相異值**（不寫死列舉；僅「模組桶」的顯示次序用顯示用常數 `BUCKET_DISPLAY_ORDER`＝`SelfImproving`、`AutoClaude`、`AISDLC_SDD`、`AgentConsole`、`根層`、`未分類`，其餘值依出現序附後；比對恆用資料自帶的 `buckets` 成員關係，不用該常數）。**模組桶不重算**：任何一筆觀察都沒有 `buckets` 欄（根層 P2 尚未交付）時，`模組桶` 控制項為 `disabled`，旁顯示 `si-bucket-note`：`此版本的 export 尚無模組桶欄（待根層 P2 交付）`；前端不得自證據座標文字推算模組桶（§7.1 ⚖ 8）。有 `buckets` 時，一筆符合＝其 `buckets` 含所選值。**時間窗**：錨點為該回應 `generatedAt` 的日期部分（依其自帶 offset 取字面日期，不用瀏覽器時鐘）；以日曆日字串比對（`今天`＝日期等於錨點日；`近 N 天`＝日期介於錨點日往前 N−1 日與錨點日之間，含兩端）；觀察以 `time` 的前 10 字元、事件以 `t` 的前 10 字元為日期；日期無法解析者**不被時間窗篩除**並標 `時間無法解析`；不做時區換算（觀察時間欄無 offset、檔頭 `tz=` 不在 export 內；±1 日邊界為已知邊界，§7.1 ⚖ 9）。**提案**有 `狀態`、`類別`（無時間窗）；**事件**有 `種類`（`kind`）、`時間窗`（§7.1 ⚖ 21）。多個控制項為「且」；`valid` 為 `false` 的列不受篩選影響；篩選只對**已取得的頁**做（先分頁、後篩選）。`lib/domain/si.ts` 匯出的純函式名稱以 AC-932-1 的純函式 AT 為準（`mergePages`、`dispositionKey`、`inDateWindow`、`filterObservations`、`bucketOptions`；§7.1 ⚖ 22）。
- **R18 純文字渲染**（AC-SI-32-1 末句）：`components/domain/si/**` 與 `app/self-improving/**` 不得出現 `dangerouslySetInnerHTML`，不得 import `react-markdown`、`rehype*`、`remark*`、`@uiw/react-md-editor` 或本專案 `components/markdown/*`；所有來自帳本的字串（九欄、`marks`、`marksKv` 的值、`card`、事件 JSON、`ne`／`problems` 的 `detail`、`details.detail`）都以 React 文字節點渲染。執行期負控：含 `<script>`、`<img … onerror=…>`、Markdown 粗體與連結語法、HTML 實體字樣（如 `&lt;`）的欄位原樣顯示為字面文字（不執行、不轉格式、不二次解碼）。
- **R19 reason 常數與錯誤顯示**：`lib/domain/si.ts` 匯出 `SI_REASONS = { UNAVAILABLE: "si_unavailable", NOT_FOUND: "si_not_found" }`，其值與凍結 `Architecture.md` §11.1〈SelfImproving 相關的 `reason`〉表逐字一致（`lib/domain/si.test.ts` 解析該表比對，體例同 `reasons.test.ts`；**比對範圍＝表中 `reason` 以 `si_` 起頭、且「何時」欄含 `P1b` 者**，恰為這兩值；只標 P2b 的 `si_write_*`、`si_audit_exists` 不需要常數；表中的 `invalid_request`〔422〕是 Bridge 層的 reason，只經 backend 回應的 `details.bridgeReason` 帶出〔R8〕，不屬 `SI_REASONS`）；`REASONS`（`lib/api/reasons.ts`）不得含這兩值，該檔的註解也不寫它們的字面值（該表與凍結契約附錄 B 雙向鎖：多一個前端常數＝`reasons.test.ts` 紅，§7.1 ⚖ 11）。錯誤態的摘要 `si-error-summary`：`status` 為 503 且 `reason` 為 `SI_REASONS.UNAVAILABLE` 時為 `SI 資料面不可用`，404 且 `reason` 為 `SI_REASONS.NOT_FOUND` 時為 `查無此筆`，其餘錯誤沿 `describeError`。

*D. 導覽登記表*

- **R20 登記表**（`lib/nav/registry.ts`；形狀以凍結 `Architecture.md` §5.4 為準）：匯出 `NavCtx`、`NavEntry`（欄位 `id`、`label`、`icon`、`href`〔字串或 `(ctx: NavCtx) => string`〕、`match(pathname)`、`order`、`roles?`、`enabled`、`mobile`）與 `NAV_REGISTRY: ReadonlyArray<NavEntry>`，**七項**（`id`／`label`／`order`／`mobile`／`href`）：`dashboard`／`儀表板`／10／`true`／`/`；`projects`／`專案管理`／20／`true`／`/projects`；`import`／`BRD/PRD 匯入`／30／`true`／`/import`；`execute`／`執行中心`／40／`true`／有目前專案＝`/projects/<id>/execute`、否則 `/projects`；`monitor`／`監控中心`／50／`true`／有目前專案＝`/projects/<id>/monitor`、否則 `/projects`；`settings`／`系統設定`／60／`true`／`/settings`；`self-improving`／`自我進化`／70／**`false`**／`/self-improving`（`roles` 缺＝所有已登入角色、`enabled` 為 `true`、`icon` 取自 `lucide-react` 且與其他項不同）。`match` 逐項（舊 `activeNav` 對「其餘一律 `projects`」用 fallback 兜底、沒有 `projects` 自己的判斷式，登記表化後 fallback 取消，故 `projects` 必須明寫）：`dashboard`＝`pathname === "/"`；`projects`＝`(pathname === "/projects" || pathname.startsWith("/projects/")) && !/^\/projects\/[^/]+\/(execute|monitor)/.test(pathname)`（以 `/projects` 或 `/projects/` 起頭，且不屬 `/projects/<id>/execute` 與 `/projects/<id>/monitor`；排除是為了讓 `execute`、`monitor` 在 R21 的「第一個命中者」規則下不被 `projects` 吃掉，`/projects-x` 不命中）；`import`＝`pathname.startsWith("/import")`；`execute`＝`/^\/projects\/[^/]+\/execute/.test(pathname)`；`monitor`＝`/^\/projects\/[^/]+\/monitor/.test(pathname)`；`settings`＝`pathname.startsWith("/settings")`（其中 `dashboard`、`import`、`execute`、`monitor`、`settings` 五項的判斷與 `href` 逐字搬自舊 `activeNav`／`hrefFor`）；第七項 `match` 為 `pathname === "/self-improving" || pathname.startsWith("/self-improving/")`。`id` 與 `order` 各自唯一；`mobile` 為 `true` 的項數 ≤ 6。
- **R21 純函式與消費規則**（登記表檔內另匯出**以登記表為參數**的純函式，使測試可注入自訂登記表；名稱不鎖，§7.1 ⚖ 22）：**可見項**＝`enabled` 為真，且（`roles` 缺，或 `roles` 含目前角色）；角色未知（`undefined`）時帶 `roles` 的項不可見；可見項依 `order` 升冪（同序依登記表原序）。**active**＝在可見項中依序第一個 `match(pathname)` 為真者；無則**沒有任何項 active**（PRD AC-SI-32-6 (f) 明定：舊行為「未知路徑 fallback 成專案管理」就此改變，列於 §4）。**href**：字串直取；函式以 `{ currentProjectId }` 呼叫。**mobile**：每個可見項的 `<a>` 一律在 DOM 內（三種響應式形態共用同一個 `<nav aria-label="主導覽">`）；`mobile` 為 `false` 的項其 `<a>` 帶類別 `max-md:hidden`（<768 底部 Tab 不顯示），為 `true` 者不帶（§7.1 ⚖ 23）；`aria-label` 與 `title` 皆為 `label`；active 者 `aria-current="page"`。`ToolsRegion.tsx` 只消費：全文不得含 `const NAV`、`function activeNav`、`hrefFor`；以登記表參數化函式處理 `NAV_REGISTRY`、目前角色（`useAuth().role`）、`pathname` 與 `useCurrentProjectId()`；新增導覽項只加登記表一列、不改任何元件。
- **R22 `layout.test.tsx` 由登記表驅動**：導覽斷言改為對「目前角色可見的登記表項」逐項斷言標籤與 href，增刪一列即增刪斷言；原有的專案頁斷言（`/projects/p2/goals` 時「執行中心」指向網址中的專案、「專案管理」為 active）保留；不再寫死六個標籤的清單。

*E. 連動面*

- **R23 compose**（`AgentConsole/docker-compose.yml`；`engine-bridge` 服務）：環境變數 `SI_ROOT: /repo`；以**長語法**唯讀掛載下列兩種具名設計之一（§7.1 ⚖ 13；兩者擇一，由 V3 真容器結果決定，AT 只接受恰好其中之一）。**設計 A（預設）**：六條 bind，皆 `read_only: true`、`bind.create_host_path: false`，來源（相對 compose 檔）→目標：`../tools`→`/repo/tools`、`../docs/06_quality`→`/repo/docs/06_quality`、`../.git/HEAD`→`/repo/.git/HEAD`、`../.git/refs`→`/repo/.git/refs`、`../.git/objects`→`/repo/.git/objects`、`../.git/packed-refs`→`/repo/.git/packed-refs`。**設計 B（備案：單檔 bind 在 git 換檔後容器保留舊 inode，或 `packed-refs` 缺檔使容器起不來時採用）**：`../.git`→`/repo/.git`（`read_only: true`）加一個空檔覆蓋 `/repo/.git/config`（`read_only: true`；空檔入庫路徑 `AgentConsole/docker/si/git-config.empty`）。兩設計共同：不掛 repo 根、不掛真的 `.git/config`、所有 SI 相關 bind 皆唯讀、`engine-bridge` 服務沒有 `ports` 發布（Architecture §12.1 L-6）。
- **R24 CI**（`.github/workflows/agentconsole-ci.yml`）：`on.pull_request.paths` 與 `on.push.paths` **兩處**都須涵蓋 Bridge 差分測試的根層輸入（`tests/si_repo_support.py` 的常數 `CLI_CLOSURE` 與 `PARAMS_SRC`）：`tools/selfimproving.py`、`tools/_stdio_utf8.py`、`tools/lib/platform_utils.py`、`tools/lib/selfimproving/**`、`docs/06_quality/SelfImproving_Protocol/params.json`；`CLI_CLOSURE` 日後變動時，測試與 `paths` 同一個 commit 收齊。根層 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 須續綠（V7 現查）。
- **R25 夾具與真 CLI 閉包**（細節見 §5）：差分測試用的「真 CLI」＝把 `CLI_CLOSURE`（四個路徑，現查為 `tools/selfimproving.py`、`tools/_stdio_utf8.py`、`tools/lib/platform_utils.py`、`tools/lib/selfimproving/`，排除 `__pycache__`）自 monorepo 複製進 tmp 倉，加 `tests/fixtures/si_repo/` 的帳本複本與取自真 repo 的 `params.json`，`git init` 並以固定作者與日期提交一次＝狀態 A；追加一筆觀察列與一筆事件並再提交一次＝狀態 B。閉包不完備（CLI 的 `import` 失敗）時，建構器須以清楚訊息直接失敗，不得退回假 CLI。
- **R26 文件與帳本連動**（非 AT；QA 以 V 系列與 §6 核對。分三批：**(1) 與實作同一個 commit（開發 agent）**、**(2) SCG-5（主控；其中契約後繼檔與實作同一個 commit 落檔）**、**(3) RELEASE 之後的純文件 commit（主控）**）：**(1) 與實作同一個 commit（開發 agent）**——① `engine-bridge/README.md` 加端點與 `SI_ROOT`；② 「404 的 reason 省略」慣例的「唯一例外」字樣的連動面：`NotFoundException.java` 的類別 Javadoc、`ErrorResponseDocumentation.java` 的程式註解與 OpenAPI 說明字串、`ErrorReasons.java` 的 `RTM_NOT_FOUND` Javadoc、`frontend/lib/api/reasons.ts` 的 `RTM_NOT_FOUND` 註解，一律改述為「例外之一」（`rtm_not_found` 與 `si_not_found`）；`reasons.ts` **只改註解、不動任何常數**（`reasons.test.ts` 的雙向鎖不受影響），註解不寫 SI reason 的字面值、只指向 `lib/domain/si.ts` 的 `SI_REASONS`。**(2) SCG-5（主控）**——① **契約後繼檔**（PRD §9.1 C18 的「契約新版」；§7.1 ⚖ 12）：新檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`，由**主控落檔、與實作同一個 commit**；開發 agent 於交卷以**純文字附後繼檔全文草稿**（依實作如實撰寫）。WHY：在 SDD hooks-ON 的 session 裡，開發 agent 於 IMPLEMENTATION 態寫不進 `docs/02_architecture/`——SDD FSM runtime（`fsm_runtime.py`）的 `_SPEC_TARGET_PREFIXES` 含 `docs/02_architecture/`（路徑子字串比對，`AgentConsole/docs/02_architecture/` 一併命中），`_STATES_ALLOWING_SPEC_WRITE` 不含 IMPLEMENTATION，`AISDLC_SDD/CLAUDE.md` Rule 9 絕對禁令 #3 明文禁止 IMPLEMENTATION 期間 Write／Edit `docs/01～03` 規格文件；所以由主控代寫（與 D11 同型）。後繼檔內容為六個 backend GET（`/api/v1/si/**`）與六個 Bridge GET（`/si/**`）各自的路徑、查詢參數（`since`、`limit`、`{id}` 規則）、回應形狀的指向（`export` 物件經 R9 對映），以及狀態碼與 `reason` 的對映表——200、401、403、404（`si_not_found`，帶 `id`）、405、422（`invalid_request`，Bridge 層 reason，經 `details.bridgeReason` 帶出）、502、503（`si_unavailable`，帶 `cause` 與 `detail`）、504；來源＝PRD §9.3、Architecture §10.3 與 §11.1、本檔 R5、R7、R8；該檔並載明「404 的 reason 省略」慣例多一個例外（`si_not_found`；第一個是 `rtm_not_found`）；凍結的 `API_Contract_P3-6.md`（含 §0.3 第 8 點的「唯一例外」字樣）與 `openapi-p3-6.yaml` 一律不改。② `AgentConsole/docs/06_quality/RTM.md` 加本檔的本地編號子表（先例 FsmTrail 子表：ID 欄加反引號、不計入總列數、不往計數列加列；`F-901`、`US-901`～`US-907`、14 個 AC 與全部 AT；§7.1 ⚖ 27）；③ **根層 RTM 的 FR-SI-32 列**（PRD 指定的 FR-SI 追溯主載體，`docs/06_quality/RTM-SelfImproving-<Phase>-<日期>.md`，檔名依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2）填 AC-SI-32-1～32-4、32-6 對應的 AT 與 V 項座標（AC-SI-32-5 由根層 P1 TCS 承接，不在此）；④ SCG-4 報告。**(3) RELEASE 之後另以純文件 commit（主控）**——`Architecture.md` 是 Stage-1 凍結檔，實作 commit 內不改：去除〔P1b 規劃〕註記，回寫 §12.1 L-14 與 §12.2 V-12 的 V3、V4 結論，§10.3 簡表補 `cause` 欄一句（§7.2 #3）。

*F. 順帶*

- **R27 `NodeEditDialog.tsx` 的專案節點編輯**：「執行路徑」欄下方加 `<p id=…>` 顯示 `EXECUTION_PATH_HINT`（自 `components/domain/import/sourceRules.ts` import，不複製字串），輸入框以 `aria-describedby` 連到它；欄位標籤維持精確 `執行路徑`（`getByLabelText("執行路徑")` 仍取得輸入框）；形態比照 `EntityForms.tsx`（說明放在 `Field` 外、不進可及名稱；OBS-SI-230）。
- **R28 RTM FsmTrail 升格**（OBS-SI-202；V 系列，非 AC）：QA 以 Console 真後端 E2E 驗「委派失敗的 FSM 狀態檔→監控頁最近決策顯示 `AUTOCLAUDE_DELEGATED → ESCALATION`」，並以**文字證據**（指令輸出與 E2E 座標）交卷——QA 全程唯讀、不改 RTM；通過者由**主控依該證據**把 RTM 的 FsmTrail 子表 14 列（`F-001`、`US-001`、`AC-001-1`～`AC-001-5`、七個 AT 列）由「✅ 實作+測試」改為「✅ 已驗證」並附 E2E 座標；未通過或未做者由主控保留現狀並寫一句再開症狀（§7.1 ⚖ 28）。
- **R29 範圍**：開發 agent 只准新增或修改 §5.6 的允許集合；根層 `tools/`、`.claude/`、`.github/`、根 `CLAUDE.md`、`AutoClaude/`、`AISDLC_SDD/`、本檔的六份凍結上位文件與既有 TCS 一律不動。

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-901 | 作為掌舵者，我要在 Console 以只讀頁面看到 SelfImproving 帳本的鏡像（狀態橫幅、觀察／提案／事件三分頁），且頁面每個資料欄都與 `si export` 一致，以便不開終端機就能審提案卡面 | AC-932-1 | （PRD AC-SI-32-1；R5、R6、R9、R11、R13～R18）Given 任一時刻的帳本與事件帳本 When 開 `/self-improving` 或呼叫 `GET /si/*`、`GET /api/v1/si/**` Then 頁面與回應的每個資料欄，與同一時刻 `export --json --kind <k>` 輸出的對應欄逐欄相同（欄名只經 R9 的對映，`generated_at` 不參與比對）；待決 PROP 的卡面逐字＝`si card`；Bridge、backend、frontend 不重算判準；frontend 以純文字渲染外部衍生與卡面（含 `<script>` 與 Markdown 的負控）；差分＝正控（一致）加負控（追加一筆帳本列與一筆事件後頁面隨之改變且仍與 CLI 一致） |
| US-901 | 同上 | AC-940-7 | （本檔自增，PRD 階段前綴形 `AC-P1b-040-7`；R25）Given 差分夾具 When 以真 CLI 閉包建狀態 A 與 B Then 閉包完備（CLI 不因缺檔失敗）、夾具具備反空轉前提（卡面非 `null`、含壞列與 CJK 與標記字元、事件與運轉非空），閉包缺檔時建構器以清楚訊息失敗而不退回假 CLI |
| US-901 | 同上 | AC-940-8 | （本檔自增，`AC-P1b-040-8`；R10、R11）Given backend 與 frontend 的契約面 When 檢查 `/v3/api-docs`、`schema.d.ts`、`siBase()` Then 六個 SI 路徑各只有 `get`、`schema.d.ts` 重產入庫且含六路徑、`siBase()` 解析規則同 `sddBase()` |
| US-902 | 作為維護者，我要 Console 對 SelfImproving 帳本零寫入（沒有任何非 GET 方法、子行程只呼叫 `export`），以便鏡像不會成為第二個寫入者 | AC-932-2 | （PRD AC-SI-32-2；R5、R6、R7、R11）Given 任意 Console 操作序列（含全部分頁、篩選、重新整理與直接呼叫端點） When 結束 Then 正式面 `git status --porcelain` 與 HEAD 前後逐字相同、家目錄無新增檔；`/si/**` 與 `/api/v1/si/**` 沒有任何非 GET 方法（Admin 與 Operator 回 405，Viewer 先被擋成 403）；Bridge 原始碼不含以寫入形態開啟 SI 路徑、不 import 根層 `tools/lib`、argv 動詞只有 `export`（AST 鎖加負控） |
| US-902 | 同上 | AC-940-2 | （本檔自增，`AC-P1b-040-2`；R3）Given Bridge 以子行程呼叫根層 CLI When 檢查 argv、cwd、環境 Then argv 與旗標序固定且不帶 `--repo`、`-I`、`-P`，環境只含白名單與固定鍵（機密與 `BRIDGE_*` 一律不洩入），名稱比對不分大小寫 |
| US-902 | 同上 | AC-940-9 | （本檔自增，`AC-P1b-040-9`；R5）Given Bridge 的六個端點 When 帶各種查詢參數與 `{id}` Then 只收 `since`、`limit` 與合格的 `{id}`，其餘 422 `invalid_request`；`si_not_found`（404）與 `si_unavailable`（503）語意分離，不合規輸入不啟動子行程 |
| US-903 | 作為掌舵者，我要 SelfImproving 資料面不可用時看到明確的錯誤與原因，而不是空表或過期快取，以便不被假象誤導 | AC-932-3 | （PRD AC-SI-32-3；R4、R5、R8、R12、R13、R16、R19）Given SI 不可用（`SI_ROOT` 未設或不含 CLI、子行程逾時或 rc 非 0、輸出非合法 JSON、`schema_rev` 不符等十餘種形態） When 請求任一 `/si/*` Then Bridge 回 503 `si_unavailable`（`detail` 帶 rc 與 stderr 末 1,000 字元），backend 逐字轉出（Bridge 不可達與逾時沿 502／504），frontend 顯示錯誤態與原因；不得渲染空表、零筆或過期快取當作正常；環境缺件使某欄量不到時，該欄回 NOT-EVALUABLE 並顯示、不省略欄位 |
| US-903 | 同上 | AC-940-1 | （本檔自增，`AC-P1b-040-1`；R1）Given 環境變數 `SI_ROOT` When 載入 Bridge 設定 Then 非空者解析為絕對路徑並拒檔案系統根，空白時本機直跑取 monorepo 根、其餘為 `None`，且不併入 `allowed_path_roots`；README 與設定檔頭註解皆已列 |
| US-904 | 作為安全審查者，我要 SelfImproving 端點需登入、Bridge 不對 host 發布，以便帳本內容不外洩 | AC-932-4 | （PRD AC-SI-32-4；R7、R11、R23）Given 未帶有效 JWT When `GET /api/v1/si/**` Then 401（且不呼叫 Bridge）；Viewer 以上可讀；`/self-improving` 頁在未登入時導向登入且不發任何 SI 請求；瀏覽器不直連 Bridge（前端原始碼零 Bridge 路徑字面）；邊界型 M＋P：Bridge 無認證、只准 backend-net（Architecture §12.1 L-6）以 compose 靜態檢查（無 `ports` 發布）補一個機械物 |
| US-905 | 作為前端維護者，我要導覽入口來自單一登記表、後續功能只加一列，以便新功能接入不改元件、不靜默吞路由 | AC-932-6 | （PRD AC-SI-32-6；R20～R22）Given Console 導覽的 Tools 區 When 檢視入口的來源 Then 全部入口皆取自登記表，`ToolsRegion.tsx` 不再持有入口常數：(a) 加一列即多一個入口、不改任何元件；(b) `enabled` 為假或角色不在 `roles` 內者不渲染；(c) 依 `order` 排序；(d) 每列 `href`（字串或函式型 `href` 的解析結果）須對應存在的 `app/**/page.tsx`，缺＝紅；(e) <768 底部 Tab 只渲染 `mobile: true` 的項且其項數 ≤ 6；(f) 未知路徑不亮任何項（不 fallback 成專案管理） |
| US-906 | 作為維護者，我要 P1b 的部署前置、CI 觸發範圍與常數落點在同一個 commit 收齊並可機械驗證，以便不留幽靈依賴與靜默失效 | AC-940-3 | （本檔自增，`AC-P1b-040-3`；R23）Given `docker-compose.yml` When 解析 engine-bridge 服務 Then 設 `SI_ROOT=/repo`，以長語法唯讀掛載設計 A（六條，`create_host_path: false`）或設計 B（整個 `.git` 唯讀加空檔覆蓋 config）恰其一，不掛 repo 根與真 `.git/config`，且無 `ports` 發布 |
| US-906 | 同上 | AC-940-4 | （本檔自增，`AC-P1b-040-4`；R24）Given Bridge 差分測試的根層輸入清單 When 對照 `agentconsole-ci.yml` Then 每一項都被 `pull_request` 與 `push` 兩處的 `paths` 涵蓋 |
| US-906 | 同上 | AC-940-5 | （本檔自增，`AC-P1b-040-5`；R8、R10、R19）Given SI 的 reason 常數 When 對照前後端 Then 前端常數住 `lib/domain/si.ts` 並與 Architecture §11.1 逐字一致、`REASONS` 不含它們（`reasons.test.ts` 續綠）；後端 `ErrorReasons` 有兩常數，`si_not_found` 的 404 帶 `reason` |
| US-907 | 作為匯入頁的使用者，我要節點編輯對話框的「執行路徑」欄也有本機與 Docker 全棧兩種寫法的說明，以便不會在全棧下填錯路徑 | AC-940-6 | （本檔自增，`AC-P1b-040-6`；R27；OBS-SI-230）Given 匯入頁編輯專案節點的對話框 When 檢視「執行路徑」欄 Then 欄下顯示重用自 `sourceRules.ts` 的 `EXECUTION_PATH_HINT`、輸入框以 `aria-describedby` 連到它、欄位標籤仍為精確的 `執行路徑`，說明文字不複製字串 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。本檔除 §1 外沒有任何第一欄以 AC 起頭的表格；AT ID 於 §1 與 §2 的宣告位置之外，只出現在說明性文字與表格的非第一欄。

**INVEST 自檢**：獨立（只依賴 HEAD 上已存在的根層 `export`／`status`／`card`、既有 Bridge／backend／frontend 的慣例與測試基礎設施；`buckets[]` 缺席時前端降級）、可協商（欄名對映深度、`cause` 欄、時間窗粒度、篩選集合、掛載設計 A／B 由本檔定義並列入 §7.1，掌舵者可裁決）、有價值（P1b 出口 (a)～(d)、(f) 可由 AT 判定，(e) 真機瀏覽由掌舵者回報、不由 AT 充當）、可估計（Bridge 2 支新模組加 5 個測試檔與夾具、backend 約 10 個新類別加 4 個測試類別、frontend 約 12 個新檔加 6 個測試檔、2 個既有檔改動、compose 與 CI 各一處）、小（P1b 零寫入端點、不含 P2b 的決定載體與帳本寫入）、可測（AT 數見 §1 覆蓋率統計；Bridge 與 frontend 的 AT 不需外部服務，backend 的整合測試沿既有 Testcontainers 與迷你 Bridge，真 CLI 差分只用 tmp 目錄與本機子行程，不連外網）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-P1b-1 | 唯讀與純度：R6 的 AST 鎖（五項判準）對真原始碼回空、對違規樣本回非空；Bridge 對 SI 的子行程只呼叫 `export`；Console 對 SI 零寫入端點（R5、R7、R11） | AC-932-2 系列 AT；SCG-4 程式碼審查 |
| NFR-P1b-2 | 逾時層級：Bridge 子行程 15 秒（`SI_CLI_TIMEOUT_SECONDS`）小於 backend 讀取逾時 20 秒（兩者不得同值、前者必須較小，否則 Bridge 的 503 會被 backend 的 504 蓋掉）；stdout 上限 8MB；`export --kind status` 冷啟動三次中位數記錄於 V4，超過 7.5 秒即再開 ADR-SI-12 的症狀（§7.1 ⚖ 17） | AC-940-2 與 AC-932-3 的 AT（常數、逾時與上限）；實查 V4 |
| NFR-P1b-3 | 跨平台（根 `CLAUDE.md` 鐵律三；`AgentConsole/CLAUDE.md` 跨平台鐵律）：子行程旗標走 `procutil`、逾時終止行程樹（不直接 `os.kill`、不用 `signal.SIGTERM` 名稱於 Windows）；路徑一律 `Path`／`os.path`；stdout 以位元組讀取後 UTF-8 解碼；測試字面值不含磁碟機代號開頭的路徑；新 Python 的 `open`／`read_text`／`write_text` 帶 `encoding="utf-8"`、時間戳帶 tz；容器內 `git` 以環境變數式 `safe.directory`（不寫 `.gitconfig`）；Windows 與 Linux（CI）皆須全綠，macOS 未實跑項在 SCG-4 報告標「未驗」 | 既有 `tests/test_cross_platform_guard.py` 與根層 `TestDirEntryPrimitivesAreAccountedFor` 續綠；SCG-4 審查；V10 |
| NFR-P1b-4 | 前端品質：`npm run lint`、`npx tsc --noEmit`、`npm run build` 全過；vitest 全套綠且覆蓋率 ≥70%（`AgentConsole/CLAUDE.md` 閘門表）；SI 新檔另以覆蓋率報告列出（資訊，不閘）；四區塊只在 `app/layout.tsx` 組裝（掃描無輸出）；`grep 'const NAV' components/layout/ToolsRegion.tsx` 無輸出；既有 Playwright route mock spec 全綠（CI 的 mock spec 步驟） | V7 實跑 |
| NFR-P1b-5 | 後端品質：`gradlew clean build` 為 BUILD SUCCESSFUL（含 Checkstyle 零警告、JaCoCo 指令覆蓋 ≥80%、`ArchitectureRulesTest` 的 A1～A6 與兩條落點規則全綠）；Flyway 不增版本（P1b 無 DB 變更）；整合測試需 Docker（Testcontainers PG18，與既有 IT 同） | V7 實跑 |
| NFR-P1b-6 | Bridge 品質：`ruff check` 對新增與改動的每個 `.py` 為 0 錯，本專案視角與 monorepo 根視角各跑一次；`GET /health` 與 `/health/deep` 行為不變（SI 不可用不影響健康）；全套 pytest 無失敗、無新增略過 | V7 實跑；AC-932-3 的 AT（健康不受影響） |
| NFR-P1b-7 | 零退化：既有測試全綠且不被改弱——`reasons.test.ts`（前端常數與凍結契約雙向鎖）、`layout.test.tsx`（四區塊鎖，其導覽斷言改由登記表驅動但原專案頁斷言保留）、`test_sdd_integration_parity.py`（FSM 寫入面 AST 鎖）、`EnginesApiIT`、`ArchitectureRulesTest`；`OpenApiIT` 與 `endpoints.test.ts` 的精確數量釘選隨新增的六個 SI 端點同步（只增不減：`EXPECTED` 各加六筆或六列，61→67、70→76、68→74；§4） | V7 實跑 |
| NFR-P1b-8 | 範圍守衛：實作者只新增或修改 §5.6 允許集合內的檔案；`git diff --name-only` 不得出現根層 `tools/`、`.claude/`、`.github/`（D11 由主控代改）、根 `CLAUDE.md`、`AutoClaude/`、`AISDLC_SDD/`、六份凍結上位文件、既有 TCS | V8（`git diff --name-only` 機械核對） |
| NFR-P1b-9 | 文件連動不留尾巴（R26，分三批）：與實作同一個 commit（開發 agent）＝README、`NotFoundException`／`ErrorResponseDocumentation`／`ErrorReasons`／`reasons.ts` 的四處註解字樣；SCG-5（主控）＝契約後繼檔（與實作同一個 commit 落檔，開發 agent 交卷附全文草稿）、RTM 本地子表、根層 RTM 的 FR-SI-32 列、SCG-4 報告；RELEASE 之後另以純文件 commit＝Architecture 去註與 V-12 結論回寫；文件指令雙形態（bash 與 PowerShell 並列；PowerShell 不用裸 `cd`）；新文件不得有測試摘要字樣加 4 位以上數字同行（根層 `check_pytest_baseline_sites` 的判準） | SCG-5 核對表；根層文件鎖 |
| NFR-P1b-10 | **開發 agent 交卷前閘門清單（缺一不得交卷；輸出逐字貼入交卷）**：(1) 本檔各 AT 逐一單跑並貼輸出——Bridge：`Push-Location AgentConsole\engine-bridge; python -m pytest tests/<檔> -k <AT 底線形> -q; Pop-Location`；backend：`Push-Location AgentConsole\backend; .\gradlew.bat test --tests "<類別全名>.<AT 底線形>*"; Pop-Location`；frontend：`Push-Location AgentConsole\frontend; npx vitest run <檔> -t <AT 底線形>; Pop-Location`（bash 形態見 §2 開頭）；(2) Bridge 全套 pytest 與 `ruff check`（兩視角）；(3) `gradlew clean build`；(4) 前端 `npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`；(5) 讀 rc 先存變數再讀、不接管線；(6) 每支程式完成立即編譯與跑該區 AT、不累積；(7) 不 commit、不 push、不碰根層與凍結檔；(8) 交卷含「流程摩擦」節；(9) 文件引用子專案檔案一律寫 monorepo 根起算路徑；(10) 夾具與測試中的 `OBS-SI-`、`DEF-` 編號只准用真帳本已存在者（根層 `test_defect_id_reference_integrity.py` 的 `git grep` 掃整個 repo）；(11) 測試與夾具不得含真機密或 `sk-` 形態字串（pre-commit 機密掃描）；(12) 交卷附兩份純文字：契約後繼檔全文草稿（D12 (a)；開發 agent 在 IMPLEMENTATION 態寫不進 `docs/02_architecture/`，由主控落檔，R26）與需新增的 `agentconsole-ci.yml` `paths` 逐行清單（D11） | SCG-4 實跑檢核 V7、V8 |
| NFR-P1b-11 | 失效可偵測（NFR-SI-09）對稱：任何一層任何失敗，在畫面上都不得呈現為空表、零筆、「無事件」、「通過」或舊資料；量不到＝NOT-EVALUABLE 加原因（R12、R13、R16） | AC-932-3 的 AT |
| NFR-P1b-12 | 安全：子行程環境為白名單（機密不洩入）；`{id}` 嚴格 percent-encode 為單一路徑段；所有帳本字串以文字節點渲染；`export` 不讀不印 `~/.autosdd/`（根層 P1 已以哨兵測試釘住，P1b 以家目錄零新增檔補一道）；Bridge 無認證、只准 backend-net（P 型，另以 compose 靜態檢查補機械物） | AC-932-2、AC-932-1、AC-932-4 系列 AT |

**追溯矩陣**：F-901 ← PRD FR-SI-32 的 AC-SI-32-1、32-2、32-3、32-4、32-6（FR-SI-32 補述）、§9.1〈C18 檔名表〉AgentConsole 半與〈C20〉、§9.3〈Bridge／Console〉段、§9.4〈Console 面〉、§9.5 的 ADR-SI-12 與 ADR-SI-13、§9.6 P1b 列、§9.7 FC-a～FC-d、FC-g，與 §8.1 P1b 出口 (a)～(f)；Architecture §3、§5.1、§5.2（硬規則 2、5）、§5.4、§10.3、§11.1、§12.1 L-14、§12.2 V-12；OBS-SI-202（V 系列）與 OBS-SI-230（順帶項）；US-901～US-907 → AC-932-1～AC-940-9（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | SelfImproving PRD v0.10 全文（§8.1 P1b、§9.6 P1b）；Stage-1 凍結＝掌舵者常態規則由主控代執行（2026-10-21 `spec-frozen`） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-901（本檔 FRD-lite）；FR-SI-32 的 AC-SI-32-1～32-4、32-6 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／NFR 已量化定義 | NFR-P1b-1～12（本檔）；最近依據 PRD NFR-SI-02、06（NFR-SI-06-6）、09 與 Architecture §8、§10.1 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-901～US-907（本檔 INVEST 自檢） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／利害關係人已確認簽核 | PRD 附錄 C.2（#12：AC-SI-32-5 由根層鍵交付、AC-SI-32-1～32-4 在 AgentConsole 鍵）；掌舵者 T1 2026-10-19、2026-10-20 問題 1c（sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13）；凍結常態規則（根 `CLAUDE.md`〈派工模型與凍結常態規則〉） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC→AT 映射與 R→AT 映射）；AgentConsole RTM 的本地編號子表與根層 RTM 的 FR-SI-32 列於 SCG-5 階段回填（R26） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | 不適用（功能級增量；設計載於 PRD §9 與 Architecture）；最近依據 Architecture §3、§5.1、§5.2、§5.4、§10、§11.1 | AgentConsole/docs/02_architecture/Architecture.md | sha256:8110feff5eb5c258edfd2c78e42ff1ec8b2bf619ce7f5b161318bc83cb8410ce |
| SCG-1／API Spec 草稿完成（所有端點清單） | Architecture §10.3 簡表與 PRD §9.3〈Bridge／Console〉：Bridge 六個 `GET /si/*`、backend 六個 `GET /api/v1/si/**`（本檔 R5、R7）；P2b 的四個 POST 不在本檔 | AgentConsole/docs/02_architecture/Architecture.md | sha256:8110feff5eb5c258edfd2c78e42ff1ec8b2bf619ce7f5b161318bc83cb8410ce |
| SCG-1／資料模型設計完成 | PRD §9.2〈`export --json` 輸出〉（`schema_rev`、`kind`、`generated_at`、`head_sha`、`items`、`next_since`、`truncated`、`ne`、`problems` 與各 kind 的 items 形狀）；本檔 R9（欄名對映）、R13～R14（頁面資料形態）；P1b 無 DB 變更 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-P1b-1～12 對應 R6（唯讀鎖）、R3～R4（逾時與白名單）、R8（失敗對映）、R16（NE 呈現）、ADR-SI-12（無快取、逾時 15／20 秒） | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；Bridge 以子行程呼叫根層 CLI（ADR-SI-12 選項 A）；依 Docker 唯讀掛載與容器內 `git`（Architecture §12.1 L-14、§12.2 V-12）；技術棧沿 ADR-001 D22（引擎唯讀接入）的體例 | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | Architecture §1（C4 L1）；P1b 不改系統邊界（Console 是顯示面、不是資料來源） | AgentConsole/docs/02_architecture/Architecture.md | sha256:8110feff5eb5c258edfd2c78e42ff1ec8b2bf619ce7f5b161318bc83cb8410ce |
| SCG-2／C4 Container 圖完成（主要組件識別） | Architecture §2（C4 L2）與 §3 目錄地圖：engine-bridge 容器加 `routers/si.py`、`si_cli.py`；frontend 加 `lib/nav/registry.ts` 與 `components/domain/si/`；compose 的 engine-bridge 加唯讀掛載 | AgentConsole/docs/02_architecture/Architecture.md | sha256:8110feff5eb5c258edfd2c78e42ff1ec8b2bf619ce7f5b161318bc83cb8410ce |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | PRD §9.5 的 ADR-SI-12（Console 唯讀讀模型）與 ADR-SI-13（導覽登記表與功能接入規範）；本增量無新架構決策，ADR 不新開 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；信任邊界要點：Bridge 無認證、只准 backend-net（Architecture §12.1 L-6）；帳本字串是資料不是指令（純文字渲染，R18）；子行程環境白名單（R3）；`{id}` 單一路徑段（R5、R7）；最近依據 Architecture §8 | AgentConsole/docs/02_architecture/Architecture.md | sha256:8110feff5eb5c258edfd2c78e42ff1ec8b2bf619ce7f5b161318bc83cb8410ce |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉；前端設計系統決策（ADR-002）不受影響：新頁沿既有 token 與元件，登記表只改導覽資料來源 | AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md | sha256:d67e450b48f9ace170ec5873c81bca74d915ac1bd15ab496cbbfdea8efffbf36 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 後端 springdoc 由碼產生（本檔 R10：六路徑各只有 `get`、operationId 固定）；凍結的 `openapi-p3-6.yaml` 不含 SI 端點（凍結檔、不改）；SI 端點的契約文件＝D12 的契約後繼檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`（承接 PRD §9.1 C18 的「契約新版」；§7.1 ⚖ 12），形狀來源＝PRD §9.3、Architecture §10.3 與 §11.1、本檔 R5、R7、R8；機器可讀形狀由 springdoc 的 `/v3/api-docs` 與入庫的 `schema.d.ts` 承擔（AT-940-8-1、AT-940-8-2） | AgentConsole/docs/02_architecture/openapi-p3-6.yaml | sha256:956539977c70fe6527c7d41162cc49a6d6138c5a49d35d7a43c4852a6bf87823 |
| SCG-3／Request／Response Schema 定義完整 | 回應＝export 物件經 R9 欄名對映；失敗封包＝R4（Bridge）與 R8（backend）；PRD §9.2〈`export --json` 輸出〉 | docs/01_requirements/SelfImproving_PRD.md | sha256:1d26dbf8b34900d1d7bbef0e564e60a5b5ae6db0d72872612785fb4740cb8406 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | 401、403（`SecurityConfig` 既有）、404 `si_not_found`、405、422 `invalid_request`、502／504、503 `si_unavailable`（Architecture §11.1〈SelfImproving 相關的 reason〉表）；契約 §0.3 的「404 的 reason 省略」慣例多一個例外（§7.1 ⚖ 11；凍結的契約不改，由契約後繼檔載明） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:14097a21263dbfd8fbe72e9630aa58c0cddf8cfc31bd88fac6927a756e02c6af |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝console-api（唯一消費 Bridge `/si/*`）與 `/self-improving` 頁（消費 `GET /api/v1/si/**`）；契約 §3.1 呼叫總表的逾時與重試慣例（連線 2 秒、讀取依呼叫、GET 不重試）沿用，SI 讀取取 20 秒 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:14097a21263dbfd8fbe72e9630aa58c0cddf8cfc31bd88fac6927a756e02c6af |
| SCG-3／API ID 與 RTM 已對應 | 無新 API ID（P1b 的端點以本檔 AC 為追溯單位）；AT 到 RTM 見本檔 §1 與 §6，RTM 本地編號子表屬 SCG-5（R26） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:14097a21263dbfd8fbe72e9630aa58c0cddf8cfc31bd88fac6927a756e02c6af |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:14097a21263dbfd8fbe72e9630aa58c0cddf8cfc31bd88fac6927a756e02c6af |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。上表六個值取自 2026-10-21 Stage-1 `spec-frozen` 的真實輸出（任務書逐字列出），SA 以 `Get-FileHash -Algorithm SHA256` 對工作樹現況逐檔重算、六檔全部相同；凍結後的實際 digest 以該鍵 `show` 的輸出為準，與本表不符時以 `show` 為準並更正本表。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC（見〈AC 編號規則〉）；邊界、錯誤與負控 AT 以 `AT-<NNN>-<Y>-E-<n>` 命名並列於本表。測試類型為 Unit／Integration／Contract；本 Feature 沒有 E2E 類 AT（真後端與真瀏覽器屬 §6.2 的 V 系列）。各 AT 的判定指令與測試檔見 §2 各 AT 標頭。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-1 | （Bridge）狀態 A 的六個端點回應與同時刻直接跑真 `export` 的輸出逐值相等，卡面逐位元組相同，且等於 `si card` 的 stdout | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-2 | （Bridge）`since`／`limit`／`next_since`／`truncated` 對映真 CLI 的游標分頁，頁串接等於不分頁輸出 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-3 | （backend）迷你 Bridge 回放 snake_case 黃金檔時，六個端點的 `data` 逐值等於 camelCase 黃金檔（含 `null`、`card` 字串、`generatedAt` 透傳） | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-4 | （backend）`SiKeyNames.camel` 對映表：符合規則者轉 camelCase，其餘鍵恆等 | ✅ | Unit | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-5 | （frontend）渲染 `SiView`：橫幅、觀察九欄、壞列、運轉與事件的文字逐欄等於 camelCase 黃金檔，且請求網址集合恰為所需 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-6 | （frontend）待決提案的卡面區 `textContent` 逐位元組等於 `card` 字串（含全形字元、box 字元、空行與結尾換行），`null` 卡面顯示量不到 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-7 | （frontend）`mergePages`、`dispositionKey`、`inDateWindow`、`filterObservations`、`bucketOptions` 的表驅動單測 | ✅ | Unit | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-8 | （frontend）`載入更多` 以 `since=<nextSince>` 取下一頁並合併：不漏、不重、末頁按鈕消失，重送的身分只顯示一次 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-1 | （Bridge）把倉推進到狀態 B 後，回應隨之改變、仍與真 CLI 一致，且每個請求各啟動一次子行程（無快取） | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-2 | （Bridge）黃金檔是真 CLI 輸出的子集（容忍根層日後加欄位），camelCase 版等於參考轉換，backend 與 frontend 的副本逐位元組相同，且黃金檔不含任何由 commit sha 衍生的值 | ✅ | Contract | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-3 | （backend）未知頂層鍵、未知項內鍵、帳本不可能有的值都原樣透傳；`items` 為空仍為 200 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-4 | （backend）兩次請求之間 Bridge 資料改變，回應隨之改變；`generatedAt` 是 Bridge 的值而非 backend 時鐘；每請求一次 Bridge 呼叫 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-5 | （frontend）含 `<script>`、`<img onerror>`、Markdown 語法、HTML 實體字樣的欄位與卡面原樣顯示為字面文字（不執行、不轉格式、不二次解碼） | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-6 | （frontend）五種篩選的選項與結果正確；壞列不受篩選影響；`buckets` 缺席時模組桶停用並說明、前端不自證據文字歸桶；有 `buckets` 時可篩 | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-7 | （frontend）把替身從狀態 A 切到狀態 B 並重新整理，畫面恰多出對應項目、共同項不變，且仍逐欄等於黃金檔 B | ✅ | Integration | □ |
| AC-932-1 | 差分：頁面與回應逐欄等於同一時刻的 `si export`（PRD AC-SI-32-1） | AT-932-1-E-8 | （frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含 `dangerouslySetInnerHTML` 與任何 Markdown／HTML 渲染器 import；掃描器有負控且範圍非空 | ✅ | Unit | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-1 | （Bridge）`app/` 全樹通過 R6 的五項判準：無寫入形態、無 lib／tools import 與 sys.path 變更、字面位置、argv 動詞形態與動態對照 | ✅ | Contract | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-E-1 | （Bridge）鎖的判準函式對各類違規樣本逐一回非空並指出判準編號，對良性樣本回空 | ✅ | Unit | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-2 | （Bridge）任意讀取操作序列（含併發、被擋下的請求）前後，`git status --porcelain`、HEAD、檔案雜湊表、`.git/HEAD` 與 `refs` 內容、家目錄皆逐字相同 | ✅ | Integration | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-3 | （Bridge）六路徑乘四種非 GET 方法皆 405，未定義的 `/si/…` 路徑 404，且全部不啟動子行程 | ✅ | Integration | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-4 | （backend）六路徑乘 POST／PUT／PATCH／DELETE 乘三種角色：Viewer 403、Operator 與 Admin 405、無 token 401；未定義路徑 404；全程不觸及 Bridge | ✅ | Integration | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-5 | （backend）`Si*Controller` 沒有任何非 GET 映射、`AgentBridge` 上 `si` 起頭的方法恰為 `siExport`，加入 SI 類別後既有 ArchUnit 規則仍全綠 | ✅ | Unit | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-6 | （frontend）完整操作序列（分頁、篩選、展開、載入更多、重新整理、錯誤重試）中，每個請求都是不帶本文的 GET；畫面沒有表單與寫入型按鈕 | ✅ | Integration | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-7 | （frontend）`lib/api/endpoints.ts` 匯出名稱以 get、post、put、patch 或 delete 加 `Si` 起頭者恰為六個 `getSi*`；各函式的方法、網址、查詢與編碼正確 | ✅ | Unit | □ |
| AC-932-2 | 唯讀：零寫入、無非 GET 方法、AST 鎖（PRD AC-SI-32-2） | AT-932-2-8 | （frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含表單、mutation hook、非 GET 方法字樣；掃描器有負控且範圍非空 | ✅ | Unit | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-1 | （Bridge）`run_export` 對十數種失敗形態各拋 503 `si_unavailable`，`cause` 與 `detail` 格式符合 R4 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-2 | （Bridge）六個端點乘六種失敗形態：503、本文鍵集合固定、`detail` 取 stderr 末 1,000 字元、不回空表、`/health` 不受影響 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-3 | （Bridge）狀態 A 倉移除 `.git` 且子行程無家目錄時，真 CLI 對缺件回 NOT-EVALUABLE：200、`head_sha` 為 `null`、`ne` 逐欄列出、鍵集合不變 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-4 | （backend）`siExport` 的請求形態（網址、標頭、逾時 2 秒與 20 秒）與十種 Bridge 回應各自拋出的例外型別，且每種失敗只送一次請求；惡意 `{id}` 形態被編碼為單一路徑段 | ✅ | Unit | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-5 | （backend）Bridge 的 503 `si_unavailable`、404 `si_not_found`、422、500、非 JSON 與陣列本文，各依 R8 對映為 503／404／422／502；連線被拒對映為 502、讀取逾時對映為 504；原因逐字、失敗回應無 `data` | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-6 | （frontend）後端回 503 `si_unavailable` 時，橫幅與目前分頁各自顯示錯誤態：reason、detail、cause 逐字，沒有空表或零筆字樣；重試可恢復 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-7 | （frontend）SI 查詢 `retry` 為假、`staleTime` 與 `gcTime` 為 0：失敗只呼叫一次，卸載重掛不顯示上一次的資料 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-1 | （Bridge）合法輸出不是錯誤：空 `items`、非空 `ne` 與 `problems`、stderr 雜訊、未知頂層鍵、`null` 欄位皆原樣成功回傳 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-2 | （Bridge）逾時時整棵行程樹（含孫行程）被終止、呼叫在有界時間內返回、無孤兒，且之後的正常呼叫成功 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-3 | （Bridge）子行程持續輸出時，超過 `SI_STDOUT_MAX_BYTES` 即終止並回 503，Bridge 不隨輸出無限吃記憶體 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-4 | （frontend）先成功顯示資料、重新整理失敗後，舊資料全部從 DOM 消失只剩錯誤態；改回成功並重試後內容恢復 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-5 | （frontend）`status` 失敗時橫幅顯示錯誤而非「無事件」；清單失敗時該分頁顯示錯誤而非空表；其他面板不受影響 | ✅ | Integration | □ |
| AC-932-3 | fail-loud：SI 不可用回 503 `si_unavailable` 並顯示原因、不渲染空表或過期資料（PRD AC-SI-32-3） | AT-932-3-E-6 | （frontend）`NOT-EVALUABLE` 物件、`headSha` 為 `null`、`card` 為 `null`、`ne`、`unavailable` 與空事件加 carrier NE，一律以量不到加原因呈現，不顯示為 0、無、通過或正常 | ✅ | Integration | □ |
| AC-932-4 | 需登入：JWT 與角色、瀏覽器不直連 Bridge（PRD AC-SI-32-4） | AT-932-4-1 | （backend）六個 GET：無 token 與亂碼 token 為 401（不觸及 Bridge），VIEWER／OPERATOR／ADMIN 皆 200 | ✅ | Integration | □ |
| AC-932-4 | 需登入：JWT 與角色、瀏覽器不直連 Bridge（PRD AC-SI-32-4） | AT-932-4-2 | （frontend）未登入開 `/self-improving`：導向 `/login?next=…`、`SiView` 不渲染、沒有任何 SI 請求；已登入對照組正常 | ✅ | Integration | □ |
| AC-932-4 | 需登入：JWT 與角色、瀏覽器不直連 Bridge（PRD AC-SI-32-4） | AT-932-4-3 | （frontend）前端非測試原始碼的字串字面值沒有以 `/si/` 起頭者、沒有 8081 與 BRIDGE 字樣；掃描器有負控且範圍含 `lib/api/endpoints.ts` | ✅ | Unit | □ |
| AC-932-4 | 需登入：JWT 與角色、瀏覽器不直連 Bridge（PRD AC-SI-32-4） | AT-932-4-4 | （Bridge／compose）`docker-compose.yml` 的 engine-bridge 服務沒有 `ports` 發布，網路只有 `backend-net` 與 `db-net`；檢查函式有負控 | ✅ | Contract | □ |
| AC-932-4 | 需登入：JWT 與角色、瀏覽器不直連 Bridge（PRD AC-SI-32-4） | AT-932-4-E-1 | （backend）三種角色對單筆提案的讀取結果一致；不存在的 id 為 404 `si_not_found`；含空白、中文、問號、井號與超長的 id 經 HTTP 送入時被編碼為單一路徑段，回應收斂為 404 或 422 | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-1 | （frontend）`NAV_REGISTRY` 恰七項，`id`／`label`／`order`／`mobile`／`href` 逐項符合 R20，唯一性與型別正確 | ✅ | Unit | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-2 | （frontend）登記表每一項的 `href`（字串，或函式型的各解析結果）都對應存在的 `app/**/page.tsx`；檢查函式對自造壞登記表回報 | ✅ | Unit | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-3 | （frontend）對代表路徑表，七項的 `match` 恰好命中期望的單一項或無項，互斥成立，邊界路徑不誤命中 | ✅ | Unit | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-4 | （frontend）`ToolsRegion.tsx` 不含 `const NAV`、`activeNav`、`hrefFor` 與入口標籤字面，含自登記表的 import；檢查函式有負控 | ✅ | Unit | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-5 | （frontend）以替身把登記表換成「真登記表加一列」：`ToolsRegion` 多出該入口、位置依 `order`、其餘入口不變，且元件原始碼不被修改 | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-6 | （frontend）`enabled` 為假、`roles` 不含目前角色的項不渲染（不在 DOM）；符合者渲染；`roles` 缺者三種角色皆可見 | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-7 | （frontend）登記表以亂序提供時，主導覽的 DOM 順序仍依 `order` 升冪；同 `order` 者保持登記表原序 | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-8 | （frontend）七個連結皆在 DOM（768 以上兩種形態顯示全部）；只有 `mobile` 為 `false` 的入口帶 `max-md:hidden`；`aria-label` 與 `title` 不隨 `mobile` 改變 | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-9 | （frontend）對代表路徑表，`aria-current` 恰在期望項上；未知路徑主導覽內沒有任何 `aria-current`（尤其不是專案管理） | ✅ | Integration | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-E-1 | （frontend）登記表檢查函式（唯一性、`mobile` 項數、路由存在、`match` 互斥）對六種自造違規各自回報恰對應的違規，真登記表回空 | ✅ | Unit | □ |
| AC-932-6 | 導覽登記表：入口取自單一來源（PRD AC-SI-32-6） | AT-932-6-E-2 | （frontend）以舊 `activeNav`／`hrefFor` 的行為表對照新登記表：六項的 active 與 href 全部相同，唯一差異是未知路徑由 `projects` 改為無 active | ✅ | Unit | □ |
| AC-940-1 | `SI_ROOT` 設定解析（本檔自增） | AT-940-1-1 | （Bridge）`load_settings` 對 `SI_ROOT` 七種輸入的解析結果，拒檔案系統根，不檢查存在性，不併入 `allowed_path_roots`，既有欄位不變 | ✅ | Unit | □ |
| AC-940-1 | `SI_ROOT` 設定解析（本檔自增） | AT-940-1-E-1 | （Bridge／文件）`engine-bridge/README.md` 與 `app/settings.py` 檔頭註解都含 `SI_ROOT`，README 含六個端點路徑與兩個 reason；檢查函式有負控 | ✅ | Contract | □ |
| AC-940-2 | 子行程 argv、cwd 與環境白名單（本檔自增） | AT-940-2-1 | （Bridge）對五個 kind 與旗標組合，假 CLI 記錄的 argv、cwd、環境符合 R3：旗標序固定、不帶 `--repo`／`-I`／`-P`、環境只有白名單與固定鍵、哨兵機密不洩入；`si_cli` 預設常數符合 R2 | ✅ | Integration | □ |
| AC-940-2 | 子行程 argv、cwd 與環境白名單（本檔自增） | AT-940-2-E-1 | （Bridge）環境建構純函式：白名單名稱不分大小寫比對並保留原鍵與值，其餘一律丟棄，來源中的 `GIT_CONFIG_COUNT` 被固定值覆寫，缺席的白名單鍵不補空值 | ✅ | Unit | □ |
| AC-940-3 | compose 唯讀掛載與 `SI_ROOT`（本檔自增） | AT-940-3-1 | （compose）`engine-bridge` 服務設 `SI_ROOT=/repo`，SI 相關 bind 皆為長語法唯讀，整組恰符合設計 A 或設計 B 其中之一，不掛 repo 根與真 `.git/config`，既有掛載保留 | ✅ | Contract | □ |
| AC-940-3 | compose 唯讀掛載與 `SI_ROOT`（本檔自增） | AT-940-3-E-1 | （compose）檢查函式對九種壞變體（缺唯讀、短語法、`create_host_path` 為真、掛 repo 根、掛真 config、少 `packed-refs`、多掛一條、`SI_ROOT` 錯、A 與 B 混用）各自回報 | ✅ | Unit | □ |
| AC-940-4 | CI `paths` 涵蓋根層輸入（本檔自增） | AT-940-4-1 | （CI）`CLI_CLOSURE` 與 `PARAMS_SRC` 的每個輸入都被 `agentconsole-ci.yml` 的 `on.pull_request.paths` 與 `on.push.paths` 兩處涵蓋（D11 由主控代改，補上之前本 AT 為預期紅） | ✅ | Contract | □ |
| AC-940-4 | CI `paths` 涵蓋根層輸入（本檔自增） | AT-940-4-E-1 | （CI）涵蓋檢查函式對「缺目錄 glob、缺檔案、只有一個觸發器缺、glob 只涵蓋單層」各變體回報缺哪一項與哪一個觸發器 | ✅ | Unit | □ |
| AC-940-5 | SI reason 常數的落點與帶 reason 的 404（本檔自增） | AT-940-5-1 | （frontend）`SI_REASONS` 與凍結 `Architecture.md` §11.1 的 SelfImproving reason 表逐字一致（比對範圍＝`reason` 以 `si_` 起頭且標 P1b 者；`invalid_request` 是 Bridge 層 reason、不進 `SI_REASONS`）；`REASONS` 不含這兩值；`reasons.ts` 的註解不再稱 `rtm_not_found` 為唯一例外；`reasons.test.ts` 的雙向鎖續綠；錯誤文案對照正確 | ✅ | Unit | □ |
| AC-940-5 | SI reason 常數的落點與帶 reason 的 404（本檔自增） | AT-940-5-2 | （backend）`ErrorReasons` 兩常數值正確；`si_not_found` 的 404 帶 `reason` 而一般 404 不帶；`NotFoundException`、`ErrorResponseDocumentation` 與 `ErrorReasons` 三檔的 `唯一例外` 字樣已改述 | ✅ | Integration | □ |
| AC-940-6 | 節點編輯對話框的執行路徑說明（本檔自增；OBS-SI-230） | AT-940-6-1 | （frontend）專案節點編輯對話框的「執行路徑」欄下顯示 `EXECUTION_PATH_HINT`，輸入框以 `aria-describedby` 連到它，欄位標籤仍為精確的 `執行路徑`；目標與任務節點沒有此欄 | ✅ | Integration | □ |
| AC-940-6 | 節點編輯對話框的執行路徑說明（本檔自增；OBS-SI-230） | AT-940-6-E-1 | （frontend）`NodeEditDialog.tsx` 自 `sourceRules` import `EXECUTION_PATH_HINT`、不複製其字串；三處使用者引用同一個匯出；`EntityForms.test.tsx` 既有斷言續綠 | ✅ | Unit | □ |
| AC-940-7 | 夾具與真 CLI 閉包的反空轉（本檔自增） | AT-940-7-1 | （Bridge）`make_si_repo` 建出的狀態 A 與 B：CLI 閉包完備、五個 kind 的真 `export` 皆 rc 0、夾具含壞列與特殊字元與非空卡面等反空轉前提，B 相對 A 恰多一筆觀察與一筆事件 | ✅ | Integration | □ |
| AC-940-7 | 夾具與真 CLI 閉包的反空轉（本檔自增） | AT-940-7-E-1 | （Bridge）從閉包清單移除任一必要檔後，建構器拋出清楚的例外（含 `CLI_CLOSURE` 與缺失的檔名或 import 名稱），不退回假 CLI；完整清單時成功 | ✅ | Unit | □ |
| AC-940-8 | 契約面：OpenAPI、`schema.d.ts`、`siBase()`（本檔自增） | AT-940-8-1 | （backend）`/v3/api-docs` 內 `/api/v1/si/` 起頭的路徑恰六個、各只有 `get`、operationId 固定、參數型別正確 | ✅ | Contract | □ |
| AC-940-8 | 契約面：OpenAPI、`schema.d.ts`、`siBase()`（本檔自增） | AT-940-8-2 | （frontend）`lib/api/schema.d.ts` 含六個 `/api/v1/si/` 路徑與六個 operationId、各路徑只有 `get`；`gen:api` 指令存在 | ✅ | Contract | □ |
| AC-940-8 | 契約面：OpenAPI、`schema.d.ts`、`siBase()`（本檔自增） | AT-940-8-3 | （backend）`BridgeEndpoints.siBase()` 的解析規則與 `sddBase()` 相同（自訂 `sdd.engineUrl` 優先、否則 `ENGINE_BRIDGE_URL`、去尾斜線），每次呼叫重新解析 | ✅ | Unit | □ |
| AC-940-9 | Bridge 路由輸入驗證與 404／503 語意分離（本檔自增） | AT-940-9-1 | （Bridge）未知參數、型別或範圍錯誤、不該帶參數的端點、不合格的 `{id}` 皆被擋下（422 或路徑層 404）且不啟動子行程；合法請求各啟動恰一次 | ✅ | Integration | □ |
| AC-940-9 | Bridge 路由輸入驗證與 404／503 語意分離（本檔自增） | AT-940-9-E-1 | （Bridge）合法但不存在的 id 為 404 `si_not_found`（帶 `id`）；`limit` 超過上限（CLI rc 3）與逾時為 503（帶 `cause`）；404 本文無 `cause`、503 本文無 `id`；真 CLI 對 `limit` 上限與上限加一的對照 | ✅ | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 14（PRD 的 5 個加本檔自增 9 個）
- 已映射 AT 數: 73（其中負控與邊界 E 類 25 個）
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（形態：方括號內為 `AT_OK_` 接 AT 底線形去掉 `AT_` 前綴後的部分；E 類的 `E` 同樣保留），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，引號字元用文字描述（全形引號 `「」` 同樣不得出現在 Then、And 行：編譯器的引號字面抽取〔`sdd_to_playbook_adapter.py` 的 `_QUOTED_LITERAL`〕把 `「…」` 也當成引號，會把被框住的字誤收為期望輸出的必要片段；強調一律改用反引號）。本 Feature 走 SDD session-only 路徑（backend 與 frontend；Bridge 可走委派迴圈）：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-932-3-E-1` 的底線形是 `AT_932_3_E_1`）；每個 AT 的測試函式（Java 為方法）名稱須含其底線形（例 `test_AT_932_3_1_failure_forms`、`AT_932_3_5_bridgeUnavailableIsRelayedVerbatim`、vitest 的 `it` 標題以底線形開頭）。每個 AC 內數字序與 E 序各不超過 9，使 `-k`、`-t`、`--tests` 的子字串比對不會誤收其他 AT。**同一 AT 的子情境**（以 (a)(b)… 列舉者）一律以參數化或 `subTest` 實作並保留 AT 底線形，任一子情境失敗時，失敗訊息須指出是哪個情境。**AT 內不引用其他 AT 的 ID**（只有 §1、§3、§6 的表格引用 AT ID）。**不得新增 skip、xfail 或 `it.skip`／`describe.skip`**：git 或 loopback 埠缺席視為環境壞、直接失敗。
>
> **判定指令的三種形態**（各 AT 標頭只列「引數部分」；cwd 與啟用的環境如下，PowerShell 不用裸 `cd`、讀 rc 先存變數再讀）：
>
> - **Bridge（pytest；已啟用根 `.venv`）**：`python -m pytest tests/<檔> -k <AT 底線形> -q`
> - **backend（Gradle；整合測試需 Docker）**：`gradlew test --tests "<類別全名>.<AT 底線形>*"`
> - **frontend（vitest）**：`npx vitest run <檔> -t <AT 底線形>`

```powershell
Push-Location AgentConsole\engine-bridge; python -m pytest tests/test_si_cli.py -k AT_932_3_1 -q; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_3_5*"; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_5; Pop-Location
```

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && python -m pytest tests/test_si_cli.py -k AT_932_3_1 -q)
(cd AgentConsole/backend && ./gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_3_5*")
(cd AgentConsole/frontend && npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_5)
```

> **斷言簡寫**（本節各 AT 共用；實作與設施細節見 §5）：
>
> - **Bridge 側**：`R`＝`make_si_repo(tmp_path, state)`（真 CLI 閉包＋夾具帳本＋一次提交；`state` 取 `A` 或 `B`，§5.1）或 `make_fake_si(tmp_path)`（假 CLI 樹，§5.2）回傳的 tmp 倉；`L`／活 Bridge＝`make_bridge(replace(settings, si_root=R))` 起的真 uvicorn（沿 `tests/conftest.py`，用 httpx 真 HTTP）；`CLI(R, kind, …)`＝直接以 `sys.executable` 跑 `R/tools/selfimproving.py export --json --kind <kind> …` 並解析 stdout 的 JSON（差分基準）；`FK`＝假 CLI 樹與其 `set_control`／`read_calls`；「紀錄器」＝包住 `subprocess.Popen` 的測試替身（呼叫真的 `Popen` 並記下 argv）。「逐值相等」＝解析後的 JSON 物件深度相等（鍵集合、值、陣列順序；`null` 與缺鍵不同）。
> - **backend 側**：`MINI.si`＝迷你 Bridge 的 SI 夾具（§5.3，預設回放狀態 A 的 snake_case 黃金檔）；`api.get(token, path)`、`viewer()`／`operator()`／`admin()` 沿既有 `AbstractExecutionIT`／`ApiClient`；JSON 路徑以既有 `Resp.read("$.…")`。
> - **frontend 側**：`renderSi(opts)`＝測試輔助（§5.4：包真 `Providers`、以 `saveSession` 設角色、以 `vi.stubGlobal("fetch", …)` 依網址回放 `ApiResult` 封包）；`GA`／`GB`＝狀態 A／B 的 camelCase 黃金檔；測試 id 以 `data-testid` 取元素。
> - **黃金檔**（§5.1）：狀態 A 與 B 各有 snake_case 與 camelCase 兩版；snake 版是真 CLI 輸出（各回應頂層的 `generated_at` 與 `head_sha` 置固定占位值；**黃金檔不得含任何由 commit sha 衍生的值**，§5.1），camelCase 版是 R9 轉換結果；backend 與 frontend 各持逐位元組相同的副本（AT 鎖住）。

```gherkin
# AT-932-1-1
# 對應 AC: AC-932-1（PRD AC-SI-32-1；差分的 Bridge 層；R5、R6、R9）（Bridge）狀態 A 的六個端點回應與同時刻直接跑真 `export` 的輸出逐值相等，卡面逐位元組相同，且等於 `si card` 的 stdout
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_1_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: Bridge 六端點對拍真 CLI

Scenario: 狀態 A：六個回應與直接執行真 CLI 的輸出逐值相等
  Given 依 §5.1 以 `make_si_repo` 建出狀態 A 的 tmp 倉 `R`（真 CLI 閉包、`tests/fixtures/si_repo/` 複本、真 `params.json`、一次固定日期的提交），並以 `make_bridge(replace(settings, si_root=R))` 起活 Bridge `L`
  When 對六個端點各發一次 GET：`/si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/PROP-SI-004`、`/si/runs`；同時對 `R` 直接以 `CLI` 跑對應的 `export --json --kind <k>`（單筆提案加 `--id PROP-SI-004`）取得基準
  Then 六個回應的狀態碼皆為 200；各回應的 JSON 物件與對應基準逐值相等（鍵集合、值、`items` 順序與個數皆同；`generated_at` 以外不得有任何差異，`head_sha` 因同倉亦相等）
  And 基準的 `items` 個數依序為：`status` 恰 1、`observations` 恰 12、`events` 恰 6、`proposals` 恰 1、單筆提案恰 1、`runs` 恰 1；`proposals` 的 `card` 為非空字串，回應中與基準逐位元組相同；`observations` 含一筆 `valid` 為 `false` 的壞列，且回應的 `problems` 與基準相同且非空
  And 卡面獨立對照（不經 export）：對 `R` 直接跑 `python tools/selfimproving.py card PROP-SI-004`（cwd 為 `R`、環境同 §5.5），其 stdout（UTF-8 解碼、不經 `strip`）逐位元組等於 `/si/proposals` 回應的 `items[0].card`，也等於 `/si/proposals/PROP-SI-004` 回應的 `items[0].card`（精確相等，含全形字元、box 字元、空行與結尾換行；兩個回應的 `items[0].id` 皆為 `PROP-SI-004`）
  And 回應本文的原始文字中，中文與全形標點以原字元出現、不以 `\u` 跳脫（以回應的原始位元組解碼後檢查不含反斜線加 `u` 的序列）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_1]"
```

```gherkin
# AT-932-1-2
# 對應 AC: AC-932-1（PRD AC-SI-32-1；游標分頁的 Bridge 層；R2、R3、R5）（Bridge）`since`／`limit`／`next_since`／`truncated` 對映真 CLI 的游標分頁，頁串接等於不分頁輸出
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_1_2 -q（cwd＝AgentConsole/engine-bridge）

Feature: Bridge 的 since 與 limit 對映真 CLI 的分頁

Scenario: 三頁串接等於不分頁；next_since 與 truncated 逐值透傳
  Given 狀態 A 的 `R` 與活 Bridge `L`，並以包住 `subprocess.Popen` 的紀錄器記下每次子行程的 argv（紀錄器呼叫真的 `Popen`）
  When 依序請求 `/si/observations?limit=5`，再以回應的 `next_since` 請求 `/si/observations?since=<n>&limit=5`，直到 `truncated` 為 `false`；`/si/events?limit=4` 同法取完；另請求 `/si/runs?limit=1` 與 `/si/proposals?limit=1`
  Then 觀察三頁的 `items` 個數依序為 5、5、2；前兩頁 `truncated` 為 `true` 且 `next_since` 為整數，末頁 `truncated` 為 `false` 且 `next_since` 為 `null`；每一頁與對應的 `CLI(R, observations, --since <n> --limit 5)` 基準逐值相等
  And 三頁 `items` 串接後與無分頁的 `CLI(R, observations)` 的 `items` 逐值相等（不漏不重、順序相同）；事件兩頁（4 加 2）同法成立；`runs` 與 `proposals` 各只有一頁且 `truncated` 為 `false`
  And 紀錄器顯示每個請求恰啟動一次子行程，argv 依序為 `export`、`--json`、`--kind`、<kind>，之後旗標順序為 `--since`、`--limit`，且值與請求參數相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_2]"
```

```gherkin
# AT-932-1-3
# 對應 AC: AC-932-1（PRD AC-SI-32-1；差分的 backend 層；R7、R9、R8）（backend）迷你 Bridge 回放 snake_case 黃金檔時，六個端點的 `data` 逐值等於 camelCase 黃金檔（含 `null`、`card` 字串、`generatedAt` 透傳）
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_1_3*"（cwd＝AgentConsole/backend）

Feature: backend 對黃金檔的欄名對映逐值相等

Scenario: 六端點的 data 等於 camelCase 黃金檔
  Given `MINI.si` 設為回放狀態 A 的 snake_case 黃金檔（五個 kind 與單筆提案），身分為 VIEWER
  When 對六個 `GET /api/v1/si/…` 各請求一次
  Then 六個回應皆為 200，`$.data` 與 camelCase 黃金檔的對應回應逐值相等（以 JSON 樹比對：鍵集合、值、`null` 皆須相同，鍵序不比）；`$.data.generatedAt` 等於黃金檔中的 `generated_at` 值（backend 沒有自己改寫）
  And `proposals` 的 `card` 字串與黃金檔逐位元組相同；`items` 的順序與個數相同；`ne`、`problems`、`nextSince`、`truncated` 皆原樣
  And `MINI.requests()` 恰為六個 `GET /si/…`（每個 backend 請求恰一次 Bridge 呼叫），路徑與查詢字串與期望相同
  And 另對 `/api/v1/si/observations` 以 `since=abc`、`limit=0` 各請求一次：回 400（既有驗證格式）且沒有任何 Bridge 請求；以 `foo=1&since=2` 請求一次：回 200 且 Bridge 收到的查詢字串恰為 `since=2`（未知參數不轉發）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_3]"
```

```gherkin
# AT-932-1-4
# 對應 AC: AC-932-1（PRD AC-SI-32-1；欄名對映（本檔類推）；R9）（backend）`SiKeyNames.camel` 對映表：符合規則者轉 camelCase，其餘鍵恆等
# 測試類型: Unit
# 自動化工具: JUnit 5（純單元）
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.dto.SiKeyNamesTest.AT_932_1_4*"（cwd＝AgentConsole/backend）

Feature: 欄名對映函式 camel

Scenario: 對映表逐項相符，其餘鍵恆等
  Given 公開靜態方法 `SiKeyNames.camel(String)`
  When 對下列鍵各呼叫一次：`http_status`、`touched_sha256`、`marks_kv`、`schema_rev`、`next_since`、`opened_seq`、`digest8`、`PROP-SI-004`、`quota-band`、`來源`、`a__b`、`_x`、`x_`、`Http_status`、`sha_256`、`id`、空字串
  Then 回傳依序為 `httpStatus`、`touchedSha256`、`marksKv`、`schemaRev`、`nextSince`、`openedSeq`、`digest8`、`PROP-SI-004`、`quota-band`、`來源`、`a__b`、`_x`、`x_`、`Http_status`、`sha256`、`id`、空字串
  And 方法對同一輸入恆回同一輸出（無狀態），對 `null` 輸入拋出明確的例外或回傳 `null`（二者擇一並由實作固定；不得回傳亂值）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_4]"
```

```gherkin
# AT-932-1-5
# 對應 AC: AC-932-1（PRD AC-SI-32-1；差分的 frontend 層；R12、R13、R14）（frontend）渲染 `SiView`：橫幅、觀察九欄、壞列、運轉與事件的文字逐欄等於 camelCase 黃金檔，且請求網址集合恰為所需
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_5（cwd＝AgentConsole/frontend）

Feature: 頁面逐欄顯示黃金檔資料

Scenario: 橫幅、觀察九欄、運轉與事件逐欄等於黃金檔
  Given 測試輔助 `renderSi` 以 OPERATOR 登入，`fetch` 替身依網址回放 camelCase 黃金檔狀態 A 的各端點（包在 `ApiResult` 封包內）
  When 渲染 `SiView`，等待橫幅與觀察分頁就緒，再切到事件分頁
  Then 橫幅 `si-status-banner` 的 `si-head-sha` 為黃金檔 `headSha` 的前 8 碼、`si-generated-at` 為 `generatedAt` 原字串；`si-pending-props` 含 `PROP-SI-004` 且其 `digest8` 與黃金檔相同；`si-unavailable` 列出黃金檔 `unavailable` 的每一項（`trigger` 與 `reason`）；`si-friction` 含 `NOT-EVALUABLE` 與黃金檔的 `reason`；橫幅頂層的每個鍵都至少有一個可見呈現
  And 觀察分頁有 12 個項目（11 個 `si-obs-row-<ID>` 與 1 個 `si-obs-invalid-<line>`）；對 11 筆有效列逐筆展開，`si-obs-fields-<ID>` 內九欄的文字逐欄等於黃金檔該筆的 `id`、`time`、`context`、`symptom`、`evidence`、`category`、`severity`、`disposition`、`marks`（精確字串比對，不做正規化），壞列的 `raw` 逐字顯示，且該面板頂端的 `si-problems-list` 列出黃金檔 `problems` 的每一項
  And 事件分頁的 `si-runs-table` 之列等於黃金檔 `runs` 的 `items`（`id`、`trigger`、`openedSeq`、`closedSeq`、`outcome`、`propIds`）；`si-events-table` 有 6 列，`seq`、`t`、`kind`、`by` 逐欄相同；展開事件 `seq` 為 5 者後，`si-event-json-5` 的文字等於該事件物件的 `JSON.stringify(obj, null, 2)`
  And 全程 `fetch` 的網址恰為 `/api/v1/si/status`（無查詢參數）、`/api/v1/si/observations?limit=<L>`、`/api/v1/si/events?limit=<L>`、`/api/v1/si/runs?limit=<L>`（`<L>` 為 `SI_PAGE_LIMIT` 的值）；未打開的提案分頁不發請求
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_5]"
```

```gherkin
# AT-932-1-6
# 對應 AC: AC-932-1（PRD AC-SI-32-1；待決卡面逐字＝`si card`；R14）（frontend）待決提案的卡面區 `textContent` 逐位元組等於 `card` 字串（含全形字元、box 字元、空行與結尾換行），`null` 卡面顯示量不到
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_6（cwd＝AgentConsole/frontend）

Feature: 提案卡面逐位元組顯示

Scenario: 待決提案預設展開，卡面 textContent 等於 card
  Given `renderSi` 與黃金檔狀態 A（`PROP-SI-004` 的 `state` 為 `proposed`）；另在測試內加兩個合成提案：`state` 為 `verified` 者，其 `card` 含中文全形標點、半形與全形的直線 box 字元、縮排空白、連續空行與結尾換行；`state` 為 `rejected` 者；再加一個 `card` 為 `null` 且 `ne` 有對應項的提案
  When 渲染 `SiView` 並切到提案分頁
  Then 兩個待決提案（`proposed` 與 `verified`）的卡面區 `si-card-<ID>` 預設已展開，其 `textContent` 逐位元組等於各自的 `card` 字串（精確相等；含全部換行、空白與結尾換行，不經 `trim`）
  And `rejected` 的提案預設不展開，點擊展開後 `si-card-<ID>` 的 `textContent` 同樣逐位元組等於其 `card`；卡面區的元素為 `<pre>`，內容為單一文字節點（無子元素、無 `<br>`、無 `<code>`、無額外前後綴文字）
  And `card` 為 `null` 的提案顯示 `卡面量不到（NOT-EVALUABLE）` 並指向對應的 `ne` 項，不渲染空的 `si-card-<ID>`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_6]"
```

```gherkin
# AT-932-1-7
# 對應 AC: AC-932-1（PRD AC-SI-32-1；前端純函式（本 AT 釘住匯出名稱）；R15、R17）（frontend）`mergePages`、`dispositionKey`、`inDateWindow`、`filterObservations`、`bucketOptions` 的表驅動單測
# 測試類型: Unit
# 自動化工具: vitest（純函式表驅動，不渲染元件、無網路）
# 判定指令: npx vitest run lib/domain/si.test.ts -t AT_932_1_7（cwd＝AgentConsole/frontend）

Feature: lib/domain/si.ts 的純函式表驅動

Scenario: 合併、處置鍵、日期窗、篩選與桶選項各表逐項相符
  Given `lib/domain/si.ts` 匯出 `mergePages(pages, keyOf)`、`dispositionKey(text)`、`inDateWindow(dateText, anchorIso, win)`（`win` 取 `all`、`today`、`7d`、`30d`；回傳 `in`、`out` 或 `unparsable`）、`filterObservations(items, filters, anchorIso)`、`bucketOptions(items)` 與常數 `BUCKET_DISPLAY_ORDER`、`SI_PAGE_LIMIT`（本 AT 釘住這些名稱與語意；§7.1 ⚖ 22）
  When 依表呼叫：`mergePages` 取三組頁（含重複身分鍵、空頁、單頁）；`dispositionKey` 取 `open`、`decided：寫成某檔`、`deferred；再開症狀：x`、`retired：座標`、`fixed@abc1234`、`DEF-AC-003`、`DEF-AC-023`、`merged@OBS-SI-010`、`proposed@PROP-SI-004`、`decided: x`、`decided x`、空字串；`inDateWindow` 取錨點 `2026-10-21T09:30:00+08:00` 與日期 `2026-10-21 08:00`、`2026-10-20 23:59`、`2026-10-15 00:00`、`2026-10-14 23:00`、`2026-09-22`、`2026-09-21`、`2026-10-18 21:20～22:05`、`約一週前`、`null`；另取跨年錨點 `2027-01-02T00:30:00+00:00` 與閏年錨點 `2028-03-01T10:00:00+08:00`
  Then `mergePages` 依序串接、依身分鍵去重且保留先到者、不丟任何一筆（空頁與單頁不出錯）；`dispositionKey` 依序為 `open`、`decided`、`deferred`、`retired`、`fixed`、`DEF-*`、`DEF-*`、`merged`、`proposed`、`decided`、`decided`、空字串
  And 對錨點 `2026-10-21` 的 `today`：`2026-10-21 08:00` 為 `in`、`2026-10-20 23:59` 為 `out`；`7d`（窗起點 `2026-10-15`）：`2026-10-15 00:00` 為 `in`、`2026-10-14 23:00` 為 `out`；`30d`（窗起點 `2026-09-22`）：`2026-09-22` 為 `in`、`2026-09-21` 為 `out`；`all` 恆為 `in`；區間寫法 `2026-10-18 21:20～22:05` 取前 10 字元；`約一週前` 與 `null` 在 `today`、`7d`、`30d` 為 `unparsable`、在 `all` 為 `in`；跨年錨點的 `7d` 起點為 `2026-12-27`；閏年錨點的 `30d` 起點為 `2028-02-01`
  And `filterObservations` 對分類、嚴重度、處置鍵、模組桶、時間窗取交集（全部條件同時成立才保留）；`valid` 為 `false` 的壞列在任何篩選下都保留；無 `buckets` 欄的項不符合任何選定的模組桶；`bucketOptions` 對輸入桶 `未分類`、`AutoClaude`、`SelfImproving`、`Foo` 回傳 `SelfImproving`、`AutoClaude`、`未分類`、`Foo`（依 `BUCKET_DISPLAY_ORDER`，未知值依出現序附後）；`SI_PAGE_LIMIT` 為 100
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_7]"
```

```gherkin
# AT-932-1-8
# 對應 AC: AC-932-1（PRD AC-SI-32-1；游標合併（frontend）；R15）（frontend）`載入更多` 以 `since=<nextSince>` 取下一頁並合併：不漏、不重、末頁按鈕消失，重送的身分只顯示一次
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_8（cwd＝AgentConsole/frontend）

Feature: 載入更多以 since 游標併頁

Scenario: 三頁合併不漏不重，按鈕於末頁消失
  Given `SI_PAGE_LIMIT` 以 `vi.mock` 局部覆寫為 5；`fetch` 替身依 `since`、`limit` 對黃金檔狀態 A 的 12 筆觀察切頁（`since` 為嚴格大於的游標，取該頁最後一筆 ID 的數字部分；回應帶 `truncated` 與 `nextSince`）
  When 渲染 `SiView`，點兩次 `載入更多`
  Then 分頁標籤依序為 `觀察 (5+)`、`觀察 (10+)`、`觀察 (12)`（壞列算一筆）；按鈕在第三頁後消失；三次請求的查詢字串依序為只有 `limit=5`、`since` 等於上一頁 `nextSince` 且 `limit=5`、同前（`since` 取自上一頁回應）
  And 最終 DOM 的列順序與黃金檔 12 筆完全相同（不漏、不重複）；`si-filter-scope-note` 在前兩頁顯示 `篩選只作用於已載入的 5 筆，尚有更多未載入` 與 10 筆的版本，末頁消失
  And 把第二頁的回應刻意改為重送一筆已出現的 ID（替身故障注入）時，該筆只顯示一次且保留先到者的內容
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_8]"
```

```gherkin
# AT-932-1-E-1
# 對應 AC: AC-932-1（PRD AC-SI-32-1 負控：追加一筆後頁面隨之改變且仍與 CLI 一致；R5、R6）（Bridge）把倉推進到狀態 B 後，回應隨之改變、仍與真 CLI 一致，且每個請求各啟動一次子行程（無快取）
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_1_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 差分負控：追加帳本列與事件後回應隨之改變

Scenario: after 等於新基準且不同於 before，無快取
  Given 狀態 A 的 `R` 與活 Bridge `L`；先對 `/si/observations`、`/si/events`、`/si/runs`、`/si/status` 各請求一次得 `before`（並以紀錄器計子行程數）
  When 依 §5.1 把 `R` 推進到狀態 B（追加一筆觀察列與一筆 `run.open` 事件並再提交），再對同四個端點各請求一次得 `after`，並對 `R` 直接跑 `CLI` 得新基準
  Then `after` 與新基準逐值相等（`generated_at` 除外）；且 `after` 與 `before` 不同：`observations` 的 `items` 恰多 1 筆（新列 `id` 為 `OBS-SI-013`）、`events` 恰多 1 筆（`seq` 為 7）、`runs` 恰多 1 筆（`RUN-SI-002`，`closed_seq` 為 `null`）、`status` 的 `open_runs` 含 `RUN-SI-002`，各回應頂層的 `head_sha` 與 `before` 不同（此處只指頂層；`seq` 為 7 的事件與 `RUN-SI-002` 的運轉列所帶的 `head_sha` 是 §5.1 的固定字面 `73ff8e3cdefeb993f9d4213ef88e3c184055a60a`，本 AT 不斷言它們等於 A 的 HEAD）
  And 兩批請求之間 Bridge 沒有任何快取：紀錄器顯示 8 個請求共啟動 8 次子行程
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_1]"
```

```gherkin
# AT-932-1-E-2
# 對應 AC: AC-932-1（PRD AC-SI-32-1；黃金檔鏈（Bridge、backend、frontend 三份副本）；R9、R25）（Bridge）黃金檔是真 CLI 輸出的子集（容忍根層日後加欄位），camelCase 版等於參考轉換，backend 與 frontend 的副本逐位元組相同，且黃金檔不含任何由 commit sha 衍生的值
# 測試類型: Contract
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_1_E_2 -q（cwd＝AgentConsole/engine-bridge）

Feature: 黃金檔鏈：真輸出、camelCase 與三份副本互相鎖住

Scenario: 黃金檔為真輸出子集、camelCase 版等於參考轉換、三份副本位元組相同
  Given `tests/fixtures/si_golden/` 內狀態 A 與 B 的 snake_case 黃金檔（每個狀態一份 JSON，含五個 kind 與單筆提案的回應）與其 camelCase 對應檔，以及 backend 與 frontend 各自的副本（`AgentConsole/backend/src/test/resources/si/`、`AgentConsole/frontend/tests/fixtures/si/`）
  When 以 `make_si_repo` 建狀態 A 與 B 並以真 CLI 取得各端點輸出；對黃金檔做下列四項比對
  Then 一、snake_case 黃金檔是真輸出的子集：比對前先在雙方（黃金檔與真輸出）的全部深度把鍵名為 `head_sha` 的值以占位 `<HEAD>` 取代，並移除各回應頂層的 `generated_at`；其後黃金檔的每個鍵與值在真輸出的同一位置存在且相等、陣列個數與順序相同；真輸出可有黃金檔沒有的額外鍵（使根層日後加欄位不致誤紅），真輸出缺黃金檔有的鍵或值不同即為紅
  And 二、camelCase 版逐值等於以測試內的 Python 參考實作 `camel_keys`（R9 規則）對 snake_case 版全層級轉換的結果；`camel_keys` 對自帶邊界鍵表（`http_status`、`digest8`、`PROP-SI-004`、`quota-band`、中文鍵、`a__b`、`_x`、`x_`）回傳 R9 規定的結果
  And 三、backend 與 frontend 的副本與 `tests/fixtures/si_golden/` 對應檔逐位元組相同；缺檔或內容不同即為紅，失敗訊息指出是哪一份漂移與重產指令
  And 四、黃金檔不含任何由 commit sha 衍生的值：`make_si_repo` 當次建出的狀態 A 與 B 兩個倉的 HEAD（各 40 碼小寫 hex）都不出現在任何黃金檔的文字中（snake_case 與 camelCase、含兩份副本）；頂層 `head_sha` 為 40 個 `0`，狀態 B 的 seq 7 事件與 `RUN-SI-002` 運轉列的 `head_sha` 為 §5.1 的固定字面 `73ff8e3cdefeb993f9d4213ef88e3c184055a60a`；可重現性負控：測試於提交前對 tmp 倉內的閉包複本（不是 monorepo 的真檔）任一檔追加一行註解後重建狀態 B，建倉所得 HEAD 與先前不同，但該倉對黃金檔的比對結果仍相同
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_2]"
```

```gherkin
# AT-932-1-E-3
# 對應 AC: AC-932-1（PRD AC-SI-32-1 負控：backend 不重算、不丟欄；R9）（backend）未知頂層鍵、未知項內鍵、帳本不可能有的值都原樣透傳；`items` 為空仍為 200
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_1_E_3*"（cwd＝AgentConsole/backend）

Feature: backend 透傳未知鍵與怪值，不重算

Scenario: 未知鍵與怪值原樣出現，空結果不被當錯誤
  Given `MINI.si` 的 `observations` 回應在黃金檔狀態 A 之上做三處改動：第一筆多一個 backend 不認得的鍵 `buckets`（值為字串陣列，內容為 `AutoClaude` 與 `未分類`）與一個含底線鍵的巢狀物件 `x_meta`（內含 `inner_key` 與一個 `null` 值）；第二筆的 `severity` 設為 `P9`、`category` 設為 `weird-category`；頂層多一個 `console_pending`（值為空陣列）
  When VIEWER 請求 `GET /api/v1/si/observations`
  Then 回應 200；`$.data.items[0].buckets` 逐值等於該字串陣列，`$.data.items[0].xMeta.innerKey` 存在且 `xMeta` 內的 `null` 值仍為 `null`；`$.data.consolePending` 為空陣列
  And `$.data.items[1].severity` 為 `P9`、`category` 為 `weird-category`（backend 不驗枚舉、不補值、不改值）；整個 `items` 的個數與順序不變
  And 把 `MINI.si` 改為回 `items` 為空陣列且 `ne` 含兩項時，回應為 200、`$.data.items` 為空陣列、`$.data.ne` 與輸入逐值相同（backend 不把空當錯誤，也不補內容）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_3]"
```

```gherkin
# AT-932-1-E-4
# 對應 AC: AC-932-1（PRD AC-SI-32-1 負控：backend 不快取、不改寫 generatedAt；R9）（backend）兩次請求之間 Bridge 資料改變，回應隨之改變；`generatedAt` 是 Bridge 的值而非 backend 時鐘；每請求一次 Bridge 呼叫
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_1_E_4*"（cwd＝AgentConsole/backend）

Feature: backend 無快取且 generatedAt 為 Bridge 的值

Scenario: 兩次回應各等於當時的 Bridge 輸出
  Given `MINI.si` 回放狀態 A 的 `observations`
  When VIEWER 連續請求 `GET /api/v1/si/observations` 兩次，兩次之間把 `MINI.si` 改為回放狀態 B 的 `observations`
  Then 第一次回應等於狀態 A 的 camelCase 黃金檔、第二次等於狀態 B 的（`items` 多一筆）；兩次的 `$.data.generatedAt` 各等於當次 Bridge 回的 `generated_at`（兩值不同），封包的 `$.timestamp` 是 backend 自己的時間且未被拿來充當 `generatedAt`
  And `MINI.requests()` 中 `GET /si/observations` 恰兩次；兩次回應的 `X-Trace-Id` 不同，且各自出現在對應的 Bridge 請求（沿既有 `EnginesApiIT` 的同形斷言）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_4]"
```

```gherkin
# AT-932-1-E-5
# 對應 AC: AC-932-1（PRD AC-SI-32-1 負控：含 script 與 Markdown 的候選列原樣顯示；R18）（frontend）含 `<script>`、`<img onerror>`、Markdown 語法、HTML 實體字樣的欄位與卡面原樣顯示為字面文字（不執行、不轉格式、不二次解碼）
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_E_5（cwd＝AgentConsole/frontend）

Feature: 純文字渲染的執行期負控

Scenario: script、Markdown、HTML 實體皆以字面文字顯示
  Given 黃金檔狀態 A 之上由測試改寫三筆觀察與一筆提案：第一筆 `symptom` 為 `<script>window.__si_xss=1</script>`；第二筆 `symptom` 含 Markdown 粗體（兩個星號包住）、連結語法（方括號加圓括號的網址）、行內程式碼語法（反引號包住）與 `&lt;b&gt;x&lt;/b&gt;` 字樣；第三筆 `context` 為 `<img src=x onerror=window.__si_xss=1>`；提案的 `card` 含一行 `<b>卡面</b>` 與兩個星號包住的字樣
  When 渲染 `SiView`，展開這三筆觀察並切到提案分頁
  Then `document.querySelectorAll` 取 `script` 的個數與渲染前相同，`window.__si_xss` 為 `undefined`；DOM 內沒有出自這些字串的 `<img>`、`<b>`、`<strong>`、`<em>`、`<a>`、`<code>` 元素
  And 各欄位的 `textContent` 逐字等於原字串（`&lt;b&gt;` 仍是這七個字元、不被二次解碼成 `<b>`）；卡面 `<pre>` 的 `textContent` 逐字等於含 `<b>卡面</b>` 的整段原文
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_5]"
```

```gherkin
# AT-932-1-E-6
# 對應 AC: AC-932-1（PRD AC-SI-32-1 補述；篩選與模組桶不重算；R17）（frontend）五種篩選的選項與結果正確；壞列不受篩選影響；`buckets` 缺席時模組桶停用並說明、前端不自證據文字歸桶；有 `buckets` 時可篩
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_E_6（cwd＝AgentConsole/frontend）

Feature: 篩選控制項與模組桶降級

Scenario: 選項取自資料、壞列不被篩除、桶缺席時停用且不推算
  Given 黃金檔狀態 A 的觀察（含不同的 `category`、`severity`、處置首詞，日期橫跨多日）；錨點為該回應的 `generatedAt`
  When 依序操作 `分類`、`嚴重度`、`處置`、`時間窗` 四個 `<select>`（`userEvent.selectOptions`）
  Then 各 select 的選項集合等於已載入資料的相異值集合加 `全部`（`處置` 的選項為各筆 `dispositionKey` 的相異值，`DEF-` 起頭者併為 `DEF-*`）；選 `嚴重度` 為 `P3` 後只剩 `severity` 為 `P3` 的有效列，壞列 `si-obs-invalid-<line>` 仍顯示；疊加 `分類` 後為兩者交集；選 `時間窗` 為 `今天` 時只剩日期等於錨點日的列；全部清回 `全部` 後 12 項全數回來
  And `模組桶` 控制項在狀態 A（無 `buckets` 欄）為 `disabled`，`si-bucket-note` 的文字為 `此版本的 export 尚無模組桶欄（待根層 P2 交付）`；一筆 `evidence` 含 `AutoClaude/` 路徑的觀察不會被前端歸桶（沒有任何列因路徑文字而出現在以桶名篩選的結果中）
  And 改用每筆都帶 `buckets` 的資料（測試內把 `buckets` 加進黃金檔觀察：有的為 `AutoClaude`、有的為 `SelfImproving` 與 `AgentConsole`、有的為 `未分類`）重新渲染：`模組桶` 啟用，選項依 `BUCKET_DISPLAY_ORDER` 排列，選 `AgentConsole` 只剩 `buckets` 含 `AgentConsole` 的列；事件分頁的 `種類` 選項取自事件 `kind` 的相異值、`時間窗` 以 `t` 的日期比對；提案分頁沒有 `時間窗` 控制項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_6]"
```

```gherkin
# AT-932-1-E-7
# 對應 AC: AC-932-1（PRD AC-SI-32-1 負控：帳本推進後頁面隨之改變；R12、R14）（frontend）把替身從狀態 A 切到狀態 B 並重新整理，畫面恰多出對應項目、共同項不變，且仍逐欄等於黃金檔 B
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_1_E_7（cwd＝AgentConsole/frontend）

Feature: 黃金檔 A 換成 B 後頁面隨之改變

Scenario: 多一筆觀察與一筆運轉，其餘項逐項不變
  Given `fetch` 替身回放狀態 A，渲染 `SiView` 到橫幅與 12 項觀察就緒
  When 把替身切換為狀態 B，並點頁首的 `重新整理` 按鈕（`si-refresh`）
  Then 觀察分頁由 12 項變為 13 項，多出的一項為 `OBS-SI-013`，其九欄逐欄等於狀態 B 黃金檔；橫幅 `si-open-runs` 多出 `RUN-SI-002`、`si-head-sha` 變為狀態 B 的前 8 碼
  And 事件分頁多一列 `seq` 為 7 的事件與一筆 `RUN-SI-002` 運轉；A 與 B 的共同項目逐項文字相同、順序不變（無重排）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_7]"
```

```gherkin
# AT-932-1-E-8
# 對應 AC: AC-932-1（PRD AC-SI-32-1；純文字渲染的靜態判準；R18）（frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含 `dangerouslySetInnerHTML` 與任何 Markdown／HTML 渲染器 import；掃描器有負控且範圍非空
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_932_1_E_8（cwd＝AgentConsole/frontend）

Feature: 純文字渲染的靜態掃描

Scenario: SI 原始碼無 dangerouslySetInnerHTML 與 Markdown 渲染器
  Given `components/domain/si/**` 與 `app/self-improving/**` 的全部非測試原始碼
  When 以讀檔掃描
  Then 不含 `dangerouslySetInnerHTML`，不含 import 自 `react-markdown`、`rehype`、`remark`、`@uiw/react-md-editor` 或 `@/components/markdown` 的敘述；`app/self-improving/page.tsx` 全文不含 `TopRegion`、`ToolsRegion`、`ContentRegion`、`BottomRegion`
  And 掃描器自帶負控：對一組違規樣本字串（涵蓋上述各類）逐一回非空，對良性樣本回空；掃描範圍非空（`components/domain/si/` 存在且含 `SiView.tsx`，防反空轉）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_1_E_8]"
```

```gherkin
# AT-932-2-1
# 對應 AC: AC-932-2（PRD AC-SI-32-2；AST 鎖（真原始碼）；R6）（Bridge）`app/` 全樹通過 R6 的五項判準：無寫入形態、無 lib／tools import 與 sys.path 變更、字面位置、argv 動詞形態與動態對照
# 測試類型: Contract
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_readonly_lock.py -k AT_932_2_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: Bridge 原始碼通過五項唯讀判準

Scenario: 違規清單為空且標的非空
  Given `AgentConsole/engine-bridge/app/` 全樹的真實原始碼
  When 以 R6 的五項判準掃描
  Then 回傳的違規清單為空；且掃描標的非空（含 `si_cli.py` 與 `routers/si.py`，檔案不存在即為紅）
  And 判準 4 取到的 argv 組裝函式恰一個，其返回的列表字面值索引 2 的元素為 `export`；判準 5 的動態對照對五個 kind 與旗標組合（無旗標、僅 `--since`、僅 `--limit`、兩者、`--id`）共十五個以上的組合，argv 的動詞位置恆為 `export` 且不含 `--repo`
  And `sys.path` 變更的掃描對 `app/` 全樹的結果為空（現況基線，鎖住日後新增者）；真檔不含 `obs-add` 字樣（P2b 預留的白名單配對在 P1b 不得被組出）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_1]"
```

```gherkin
# AT-932-2-E-1
# 對應 AC: AC-932-2（PRD AC-SI-32-2；AST 鎖的負控；R6）（Bridge）鎖的判準函式對各類違規樣本逐一回非空並指出判準編號，對良性樣本回空
# 測試類型: Unit
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_readonly_lock.py -k AT_932_2_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 唯讀鎖的違規樣本與良性樣本

Scenario: 每個違規樣本各自回非空，良性樣本回空
  Given R6 的判準函式（輸入為原始碼文字）與一組樣本
  When 對每個樣本各呼叫一次
  Then 下列違規樣本各自回非空且指出所違反的判準編號：判準 1 的寫入形態（含 `selfimproving` 字樣的模組中的 `open` 以寫入模式、`Path.write_text`、`os.replace`、`json.dump` 至檔案）；判準 2 的 `import lib`、`from lib.selfimproving import x`、`from tools import y`、`sys.path.insert`、`sys.path.append`、`sys.path` 增量賦值、以 `importlib.import_module` 字面載入 `lib` 或 `tools`；判準 3 的第二個模組含字面 `selfimproving.py`
  And 判準 4 的違規樣本為把 `export` 換成 `check`、`decide`、`obs-add`（無 `--dry-run`）、`run-open`、`promote` 的 `si_cli.py` 變體，有兩處 `Popen` 呼叫的變體，argv 來自另一個函式的變體；判準 5 的違規樣本為動態對照下 argv 含 `--repo` 的變體
  And 良性樣本（讀取形態的 `open(p)`、`open(p, rb)`、`Path.read_text`、`json.dumps`、`si_cli.py` 內動詞為 `export` 的單一 `Popen`）回空；白名單內 `obs-add` 加 `--dry-run` 的配對對判準 4 合法（P2b 預留）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_E_1]"
```

```gherkin
# AT-932-2-2
# 對應 AC: AC-932-2（PRD AC-SI-32-2；操作序列前後的正式面與家目錄；R3、R5）（Bridge）任意讀取操作序列（含併發、被擋下的請求）前後，`git status --porcelain`、HEAD、檔案雜湊表、`.git/HEAD` 與 `refs` 內容、家目錄皆逐字相同
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_2_2 -q（cwd＝AgentConsole/engine-bridge）

Feature: 任意操作序列後 repo 與家目錄零變動

Scenario: git status、HEAD、檔案雜湊表、refs 與家目錄前後相同
  Given 狀態 A 的 `R` 與活 Bridge `L`；測試前記下：`git status --porcelain` 輸出、`git rev-parse HEAD`、`R` 內 `.git/` 之外全部檔案的〔相對路徑到位元組 sha256〕表、`.git/HEAD` 與 `.git/refs/**` 全部檔案內容；家目錄替身（Bridge 的 `HOME` 與 `USERPROFILE` 指向 tmp 內一個空目錄 `H`）的全部項目
  When 依序做：六個端點各請求三次、清單端點帶各種 `since` 與 `limit` 組合各一次、`/si/proposals/PROP-SI-004` 請求十次、八條執行緒同時各打六個端點各兩次、最後各打一次會被 422 與 404 擋下的請求
  Then 測試後 `git status --porcelain` 輸出、HEAD、檔案雜湊表、`.git/HEAD` 與 `.git/refs/**` 內容與測試前逐字相同；`H` 內沒有任何新項目；`R` 內沒有 `__pycache__` 目錄
  And 所有回應中，成功者皆為 200，被擋下者為預期的 404 或 422，沒有任何 5xx
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_2]"
```

```gherkin
# AT-932-2-3
# 對應 AC: AC-932-2（PRD AC-SI-32-2；Bridge 無非 GET 方法；R5）（Bridge）六路徑乘四種非 GET 方法皆 405，未定義的 `/si/…` 路徑 404，且全部不啟動子行程
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_routes.py -k AT_932_2_3 -q（cwd＝AgentConsole/engine-bridge）

Feature: Bridge 非 GET 一律 405，未定義路徑 404

Scenario: 24 個 405、4 個 404，且不啟動子行程
  Given 活 Bridge `L`，`si_root` 為 `FK` 假 CLI 樹 `R`（記錄每次呼叫）
  When 對六個定義的路徑各以 `POST`、`PUT`、`PATCH`、`DELETE` 發請求（帶空 JSON 本文）；另對未定義路徑 `/si/nothing`、`/si/proposals/PROP-SI-004/extra`、`/si/status/x`、`/si/observations/OBS-SI-001` 各發 GET
  Then 六路徑乘四方法共 24 個回應的狀態碼皆為 405；四個未定義路徑的 GET 皆為 404
  And 假 CLI 的呼叫紀錄為空（`read_calls(R)` 無任何項目），證明非 GET 與未定義路徑都不啟動子行程
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_3]"
```

```gherkin
# AT-932-2-4
# 對應 AC: AC-932-2（PRD AC-SI-32-2；Admin 405、Viewer 403 的角色乘方法矩陣；R7）（backend）六路徑乘 POST／PUT／PATCH／DELETE 乘三種角色：Viewer 403、Operator 與 Admin 405、無 token 401；未定義路徑 404；全程不觸及 Bridge
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_2_4*"（cwd＝AgentConsole/backend）

Feature: backend 的角色乘方法矩陣

Scenario: Viewer 403、Operator 與 Admin 405、無 token 401，且不觸及 Bridge
  Given `MINI.si` 回放黃金檔；身分為 VIEWER、OPERATOR、ADMIN 與無 token
  When 對六個定義的路徑（`/status`、`/observations`、`/events`、`/proposals`、`/proposals/PROP-SI-004`、`/runs`，皆加前綴 `/api/v1/si`）各以 `POST`、`PUT`、`PATCH`、`DELETE` 發請求（三個身分共 72 個組合，另加 6 個無 token 的 POST）
  Then VIEWER 的 24 個回應皆為 403；OPERATOR 與 ADMIN 的 48 個回應皆為 405；無 token 者皆為 401；另對未定義路徑 `/api/v1/si/nothing` 以三個角色發 GET，皆為 404
  And 上述所有請求之後 `MINI.requests()` 為空（沒有任何請求觸及 Bridge）；ADMIN 的 GET 對六個路徑仍皆為 200（對照組：路徑本身可用）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_4]"
```

```gherkin
# AT-932-2-5
# 對應 AC: AC-932-2（PRD AC-SI-32-2；控制器只有 GET、埠上只有 siExport；R7、R10）（backend）`Si*Controller` 沒有任何非 GET 映射、`AgentBridge` 上 `si` 起頭的方法恰為 `siExport`，加入 SI 類別後既有 ArchUnit 規則仍全綠
# 測試類型: Unit
# 自動化工具: JUnit 5 + ArchUnit
# 判定指令: gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest.AT_932_2_5*"（cwd＝AgentConsole/backend）

Feature: backend 結構鎖：控制器唯讀、AgentBridge 只有 siExport

Scenario: 無寫入映射註解，埠方法恰一個，既有 ArchUnit 規則續綠
  Given backend 編譯後的類別（ArchUnit 的 `ClassFileImporter`）與 `AgentBridge` 介面
  When 檢查 `adapter.in.web` 套件內名稱符合 `Si*Controller` 的類別與 `AgentBridge`
  Then 這些控制器沒有任何方法標註 `@PostMapping`、`@PutMapping`、`@PatchMapping`、`@DeleteMapping`，`@RequestMapping` 不帶 `method` 屬性；至少存在一個 `SiController`（防反空轉）
  And `AgentBridge` 上名稱以 `si` 接大寫字母起頭的方法恰為 `siExport`，參數型別依序為 `String`、`Integer`、`Integer`、`String`，回傳型別為 `SiExport`
  And 既有 `ArchitectureRulesTest` 的 A1 至 A6 與兩條落點規則在加入 SI 類別後仍全綠（以同一次 Gradle 呼叫一併執行該類別）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_5]"
```

```gherkin
# AT-932-2-6
# 對應 AC: AC-932-2（PRD AC-SI-32-2；前端零寫入（執行期）；R11、R12）（frontend）完整操作序列（分頁、篩選、展開、載入更多、重新整理、錯誤重試）中，每個請求都是不帶本文的 GET；畫面沒有表單與寫入型按鈕
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_2_6（cwd＝AgentConsole/frontend）

Feature: 完整操作序列只產生 GET 請求

Scenario: 每個 fetch 為 GET、無本文、無寫入型控制項
  Given `renderSi` 與記錄方法與網址的 `fetch` 替身，黃金檔狀態 A
  When 渲染 `SiView` 並做完整操作序列：切換三個分頁、操作每個篩選控制項、展開全部觀察與提案、點 `載入更多`、點 `重新整理`、在錯誤態點 `重試`（以替身令一次請求失敗）
  Then `fetch` 的每一次呼叫其方法為 `GET`（或未指定）、網址路徑以 `/api/v1/si/` 起頭，且沒有任何請求帶本文
  And `SiView` 的渲染結果內沒有 `<form>` 元素、沒有 `type` 為 `submit` 的按鈕、沒有 `type` 為 `file` 的輸入；所有 `<button>` 的名稱都不含 `新增`、`刪除`、`核准`、`否決`、`決定`、`儲存`、`送出`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_6]"
```

```gherkin
# AT-932-2-7
# 對應 AC: AC-932-2（PRD AC-SI-32-2；端點函式只有六個 GET；R11）（frontend）`lib/api/endpoints.ts` 匯出名稱以 get、post、put、patch 或 delete 加 `Si` 起頭者恰為六個 `getSi*`；各函式的方法、網址、查詢與編碼正確
# 測試類型: Unit
# 自動化工具: vitest + fetch 替身（不渲染元件）
# 判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_932_2_7（cwd＝AgentConsole/frontend）

Feature: endpoints.ts 的 SI 匯出恰為六個 GET 函式

Scenario: 名稱、方法、網址與編碼逐項相符
  Given `lib/api/endpoints.ts` 的匯出與 `fetch` 替身
  When 列舉名稱符合 `^(get|post|put|patch|delete)Si` 的匯出，並逐一呼叫六個函式（`getSiProposal` 另以含 `/`、空白、中文的 id 各呼叫一次）
  Then 匯出恰為 `getSiStatus`、`getSiObservations`、`getSiEvents`、`getSiProposals`、`getSiProposal`、`getSiRuns`，沒有任何 `postSi`、`putSi`、`patchSi`、`deleteSi` 開頭者
  And 呼叫的方法皆為 `GET`、網址依序為 `/api/v1/si/status`、`/api/v1/si/observations?since=7&limit=100`、`/api/v1/si/events?limit=100`、`/api/v1/si/proposals`、`/api/v1/si/proposals/PROP-SI-004`、`/api/v1/si/runs?since=3`；值為 `undefined` 的選項不進網址；`getSiProposal` 對含 `/`、空白或中文的 id 以 `encodeURIComponent` 編碼（結果為單一路徑段）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_7]"
```

```gherkin
# AT-932-2-8
# 對應 AC: AC-932-2（PRD AC-SI-32-2；前端零寫入（靜態）；R11、R18）（frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含表單、mutation hook、非 GET 方法字樣；掃描器有負控且範圍非空
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_932_2_8（cwd＝AgentConsole/frontend）

Feature: SI 前端原始碼無寫入形態的靜態掃描

Scenario: 無表單、無 mutation hook、無非 GET 方法字樣
  Given `components/domain/si/**` 與 `app/self-improving/**` 的非測試原始碼
  When 以讀檔掃描
  Then 不含 `<form`、`type` 為 `submit` 的字串形態、`useMutation`、`useWrite`、以 `method:` 指定 `POST`、`PUT`、`PATCH` 或 `DELETE` 的字樣，也不 import `lib/api/queries` 中名稱符合 `^use(Create|Update|Delete|Post|Put|Patch|Retry|Approve|Signoff|Execute)` 者
  And 掃描器自帶負控樣本（各一個違規字串）皆回非空、良性樣本回空；掃描範圍非空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_2_8]"
```

```gherkin
# AT-932-3-1
# 對應 AC: AC-932-3（PRD AC-SI-32-3；各失敗形態負控（子行程層）；R2、R4）（Bridge）`run_export` 對十數種失敗形態各拋 503 `si_unavailable`，`cause` 與 `detail` 格式符合 R4
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_932_3_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: si_cli 各失敗形態對映 cause 與 detail

Scenario: 每個子情境拋 503 si_unavailable，cause 與 detail 符合 R4
  Given `FK` 假 CLI 樹與 `si_cli.run_export`；以 `set_control` 逐一造下列子情境，各以 `subTest` 或參數化實作並在失敗訊息指出名稱：(a) `si_root` 為 `None`；(b) `si_root` 為不存在的目錄；(c) 目錄存在但無 `tools/selfimproving.py`；(d) `Popen` 以 monkeypatch 拋 `PermissionError`；(e) 假 CLI 睡過逾時（`SI_CLI_TIMEOUT_SECONDS` 以 monkeypatch 設 0.5 秒）；(f) 假 CLI 印出超過 `SI_STDOUT_MAX_BYTES`（以 monkeypatch 設 2048）；(g) rc 為 2 並寫 stderr；(h) rc 0 但 stdout 為垃圾文字；(i) rc 0 但 stdout 為兩份 JSON 文件相連；(j) rc 0 但 stdout 為 JSON 陣列；(k) rc 0 但 stdout 為空；(l) `schema_rev` 為 2、另一個子情境缺 `schema_rev`、再一個為字串 `1`；(m) `kind` 與請求不同、另一個子情境 `items` 不是陣列
  When 對每個子情境呼叫 `run_export(R, observations)`
  Then 每次都拋 `ApiError`，其 `status_code` 為 503、`body[reason]` 為 `si_unavailable`，`body[cause]` 依序為 `si_root_unset`、`si_script_missing`、`si_script_missing`、`spawn_failed`、`timeout`、`stdout_too_large`、`nonzero_rc`、`bad_json`、`bad_json`、`bad_json`、`bad_json`、`schema_rev_mismatch`（三個）、`bad_shape`（兩個）
  And 每個 `body[detail]` 以 `rc=` 起頭並符合 `rc=<整數或 none>; stderr=<尾段>`：(g) 為 `rc=2` 且尾段等於假 CLI 寫的 stderr；(a) 至 (f) 為 `rc=none`；(h) 至 (m) 為 `rc=0`；(a)(b)(c) 的 `stderr=` 之後含字樣 `SI_ROOT`，(d) 含例外類名 `PermissionError`
  And 每個失敗各有一筆 `logger.warning`（以 `caplog` 取得），且訊息與 `body` 都不含任何環境變數的值（先在 Bridge 行程環境放一個哨兵機密值，斷言它不在任何日誌與 `body` 內）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_1]"
```

```gherkin
# AT-932-3-2
# 對應 AC: AC-932-3（PRD AC-SI-32-3；各失敗形態負控（HTTP 層）；R4、R5）（Bridge）六個端點乘六種失敗形態：503、本文鍵集合固定、`detail` 取 stderr 末 1,000 字元、不回空表、`/health` 不受影響
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_routes.py -k AT_932_3_2 -q（cwd＝AgentConsole/engine-bridge）

Feature: 六個端點在各種失敗下回 503 本文固定

Scenario: 36 個請求全 503，鍵集合與 cause 相符，stderr 尾 1000，健康不受影響
  Given 活 Bridge，`si_root` 為 `FK` 假 CLI 樹，依序切換六種失敗：`si_root` 未設、缺腳本、逾時、rc 為 3 並寫 5000 字元的 stderr（開頭含 `HEAD-MARK`、結尾含 `TAIL-MARK`）、垃圾 stdout、`schema_rev` 為 2
  When 每種失敗下對六個端點各發一次 GET（共 36 個請求；單筆端點用 `PROP-SI-004`）
  Then 全部回 503；本文鍵集合恰為 `code`、`reason`、`cause`、`detail`；`reason` 為 `si_unavailable`，`cause` 依序為 `si_root_unset`、`si_script_missing`、`timeout`、`nonzero_rc`、`bad_json`、`schema_rev_mismatch`
  And rc 為 3 的情境，`detail` 為 `rc=3; stderr=` 加 stderr 的最後 1000 個字元（總長恰為前綴 `rc=3; stderr=` 的長度加 1000），含 `TAIL-MARK`、不含 `HEAD-MARK`
  And 每種失敗下同一活 Bridge 的 `GET /health` 與 `GET /health/deep` 仍為 200（SI 不可用不影響健康）；失敗回應本文沒有 `items` 鍵（不回空表）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_2]"
```

```gherkin
# AT-932-3-3
# 對應 AC: AC-932-3（PRD AC-SI-32-3 末句；環境缺件時該欄回 NOT-EVALUABLE、不省略欄位；R4、R16）（Bridge）狀態 A 倉移除 `.git` 且子行程無家目錄時，真 CLI 對缺件回 NOT-EVALUABLE：200、`head_sha` 為 `null`、`ne` 逐欄列出、鍵集合不變
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_932_3_3 -q（cwd＝AgentConsole/engine-bridge）

Feature: 容器內缺件（無 .git、無家目錄）時真 CLI 回 NE 而非失敗

Scenario: 200、head_sha 為 null、ne 列出、欄位不省略
  Given 以 `make_si_repo` 建狀態 A 的 tmp 倉後**移除 `.git` 目錄**（模擬容器內無 `.git`），並令 Bridge 的 `HOME` 與 `USERPROFILE` 指向不存在的路徑（模擬無家目錄）
  When 對六個端點各請求一次
  Then 六個回應皆為 200（真 CLI 對缺件走 NOT-EVALUABLE、不是失敗）；每個回應的 `head_sha` 為 `null` 且 `ne` 含 `field` 為 `head_sha`、`reason` 為 `git-unavailable` 的一項；`observations` 的 `items` 仍為 12 筆，與狀態 A 的基準逐值相等（除 `head_sha`、`ne`、`generated_at`）
  And `status` 的 `items[0].friction_reconcile` 為 `status` 是 `NOT-EVALUABLE`、`reason` 是 `transcript-unavailable` 的物件（真 CLI 對無逐字稿目錄的答案）；`status.unavailable` 含 `trigger` 為 `c`、`reason` 為 `ledger-missing` 的一項（夾具倉無缺陷帳本）
  And 回應的頂層鍵集合與有 `.git` 時相同（不省略欄位），`proposals` 的 `card` 仍為字串（M 類提案的卡面不需 git）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_3]"
```

```gherkin
# AT-932-3-4
# 對應 AC: AC-932-3（PRD AC-SI-32-3；介面卡的明確拒絕、逾時與不重試；`{id}` 的路徑編碼；R7、R8、R10）（backend）`siExport` 的請求形態（網址、標頭、逾時 2 秒與 20 秒）與十種 Bridge 回應各自拋出的例外型別，且每種失敗只送一次請求；惡意 `{id}` 形態被編碼為單一路徑段
# 測試類型: Unit
# 自動化工具: JUnit 5 + MockRestServiceServer
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.out.bridge.BridgeHttpAdapterSiTest.AT_932_3_4*"（cwd＝AgentConsole/backend）

Feature: BridgeHttpAdapter 的 SI 呼叫與失敗對映

Scenario: 網址、逾時 2／20 秒、例外型別與不重試逐項相符
  Given `MockRestServiceServer` 綁定的 `BridgeHttpAdapter`（沿 `BridgeHttpAdapterSddTest` 的 `Rig`，捕捉連線與讀取逾時）
  When 呼叫 `siExport(observations, 5, 10, null)` 與 `siExport(proposals, null, null, PROP-SI-004)`，並對各次呼叫讓伺服器依序回：200 合法物件；200 非 JSON；200 JSON 陣列；503 且本文含 `reason` 為 `si_unavailable`、`cause`、`detail`；404 且本文含 `reason` 為 `si_not_found`、`id`；422 且本文含 `reason` 為 `invalid_request`、`violations`；500；403；連線例外；讀取逾時例外
  Then 請求網址依序為 `<基底>/si/observations?since=5&limit=10` 與 `<基底>/si/proposals/PROP-SI-004`（單筆不帶 `since` 與 `limit`），方法皆為 GET、帶 `X-Trace-Id`、不帶 `X-Bridge-Token`；捕捉的逾時皆為連線 2 秒、讀取 20 秒
  And 成功回傳的 `SiExport.raw()` 逐值等於伺服器本文（snake_case 鍵未動）；200 非 JSON 與陣列拋 `UpstreamException.Failure`；503 `si_unavailable`、404 `si_not_found`、422 與 403 拋 `BridgeRejectedException`（`status()`、`reason()` 與 `detailObject()` 取得原樣的 `cause`、`detail`、`id`）；500 拋 `UpstreamException.Failure`；連線例外為 `UpstreamException.Unavailable`、讀取逾時為 `UpstreamException.TimedOut`
  And 每種失敗各只送出一次請求（`MockRestServiceServer` 的期望次數為 1，不重試）
  And `{id}` 的編碼（路徑穿越防線；含編碼斜線等形態的網址無法經 HTTP 進入 backend，R7，故在此層斷言）：另對 `siExport(proposals, null, null, <id>)` 取 id 為 `a/b`、`..`、`.`、`%2F`、`a b`、`專案`、`a?b`、`a#b`、`a;b`、`a\b`、`a%b` 與 1000 字元長字串各呼叫一次（各由伺服器回 200 合法物件）：`MockRestServiceServer` 收到的請求網址路徑恰為 `<基底>/si/proposals/` 加該 id 的嚴格百分比編碼單一段——`/` 為 `%2F`、`%` 為 `%25`、空白為 `%20`、`?` 為 `%3F`、`#` 為 `%23`、`;` 為 `%3B`（`a;b` 期望 `a%3Bb`）、反斜線為 `%5C`（`a\b` 期望 `a%5Cb`）、中文為 UTF-8 百分比編碼，整段恰為 `.` 或 `..` 時各點字元編為 `%2E`；網址不含查詢字串與錨點，路徑只比 `<基底>/si/proposals/` 多一段；任一子情境失敗時，失敗訊息指出是哪個 id
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_4]"
```

```gherkin
# AT-932-3-5
# 對應 AC: AC-932-3（PRD AC-SI-32-3；backend 逐字轉出原因，失敗無 data；R8）（backend）Bridge 的 503 `si_unavailable`、404 `si_not_found`、422、500、非 JSON 與陣列本文，各依 R8 對映為 503／404／422／502；連線被拒對映為 502、讀取逾時對映為 504；原因逐字、失敗回應無 `data`
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_3_5*"（cwd＝AgentConsole/backend）

Feature: backend 失敗對映表逐列成立

Scenario: 503、404、422、502、504 各自的 reason 與 details 相符，皆無 data
  Given `MINI.si` 依序切換下列行為（每個測試後 `MINI.reset()`）：503 `si_unavailable`（帶 `cause` 與含全形字元及換行的 `detail`）；404 `si_not_found`（帶 `id`）；422 `invalid_request`（帶 `violations`）；500；200 但本文為純文字；200 但本文為 JSON 陣列；另兩個 Bridge 層的情境：連線被拒（以測試輔助 `setting` 把 `sdd.engineUrl` 指向無人監聽的 `http://127.0.0.1:1`，沿 `ExecuteProjectApiIT` 與 `EnginesApiIT` 的做法）與讀取逾時（`MINI.si.delayMillis` 設為 21000，大於 SI 讀取逾時 20 秒）
  When VIEWER 依序請求對應端點（404 用 `/proposals/PROP-SI-004`，其餘用 `/status` 與 `/observations`；連線被拒與讀取逾時兩情境各請求 `/observations` 一次）
  Then 503 情境：HTTP 503、`$.reason` 為 `si_unavailable`、`$.details.detail` 與 Bridge 的 `detail` 逐字相同（含全形與換行）、`$.details.cause` 與 Bridge 的 `cause` 相同；404 情境：HTTP 404、`$.reason` 為 `si_not_found`、`$.details.id` 存在；422 情境：HTTP 422、`$.reason` 為 `ErrorReasons.BRIDGE_REJECTED` 的值、`$.details.bridgeReason` 為 `invalid_request`
  And 500、純文字、陣列三個情境：HTTP 502、`$.reason` 為 `ErrorReasons.BRIDGE_ERROR` 的值；所有失敗回應都**沒有** `$.data`（不回空表、不回部分資料）
  And 連線被拒情境：HTTP 502、`$.reason` 為 `ErrorReasons.BRIDGE_UNREACHABLE` 的值；讀取逾時情境：HTTP 504、`$.reason` 為 `ErrorReasons.BRIDGE_TIMEOUT` 的值，耗時介於 19 秒與 40 秒之間（讀取逾時 20 秒、不重試——若重試會超過 40 秒），且 `MINI.countRequests` 對 `GET /si/observations` 恰為 1；兩情境的失敗回應同樣沒有 `$.data`；讀取逾時情境耗時約 20 秒，是本 AT 已知的成本
  And 失敗之後立即以相同身分重請求一次成功情境（先還原 `sdd.engineUrl` 並 `MINI.reset()`，`MINI.si` 改回黃金檔），回應為 200 且為當次資料（沒有殘留的錯誤或上一次結果）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_5]"
```

```gherkin
# AT-932-3-6
# 對應 AC: AC-932-3（PRD AC-SI-32-3；frontend 顯示錯誤態與原因；R12、R19）（frontend）後端回 503 `si_unavailable` 時，橫幅與目前分頁各自顯示錯誤態：reason、detail、cause 逐字，沒有空表或零筆字樣；重試可恢復
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_3_6（cwd＝AgentConsole/frontend）

Feature: SI 全面失敗時各面板顯示錯誤態與原因

Scenario: reason、detail、cause 逐字顯示，無空表字樣，可重試
  Given `renderSi`，`fetch` 替身對全部 SI 端點回 503，本文為後端錯誤封包形態：`reason` 為 `si_unavailable`，`details` 含 `cause` 為 `nonzero_rc`、`detail` 為 `rc=2; stderr=boom 全形字元`
  When 渲染 `SiView`
  Then 狀態橫幅與觀察分頁各自顯示錯誤態：`si-error-reason` 的文字為 `si_unavailable`、`si-error-detail` 的文字逐字為 `rc=2; stderr=boom 全形字元`、`si-error-cause` 為 `nonzero_rc`；錯誤態標題為 `自我進化資料無法取得`、`si-error-summary` 的文字為 `SI 資料面不可用`
  And 畫面上沒有 `si-no-event`、沒有任何 `si-obs-row-`開頭的項目、沒有 `0 筆`、`無事件`、`沒有資料` 字樣；分頁標籤不帶筆數
  And 點 `重試` 後該面板的請求再發一次（替身改回成功時，面板轉為 ok 態並顯示資料）；對單筆 404 `si_not_found` 的情境，`si-error-summary` 的文字為 `查無此筆`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_6]"
```

```gherkin
# AT-932-3-7
# 對應 AC: AC-932-3（PRD AC-SI-32-3；retry false 與 staleTime、gcTime 為 0；R11、R12）（frontend）SI 查詢 `retry` 為假、`staleTime` 與 `gcTime` 為 0：失敗只呼叫一次，卸載重掛不顯示上一次的資料
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_3_7（cwd＝AgentConsole/frontend）

Feature: SI 查詢不重試、不留快取

Scenario: 失敗端點恰呼叫一次，重掛不顯示舊資料
  Given `fetch` 替身對 `/api/v1/si/status` 與 `/api/v1/si/observations` 回 503 並計數；渲染於預設 `Providers` 的 QueryClient 之下（該預設對 5xx 重試一次）
  When 渲染 `SiView`，等待兩個錯誤態出現，再以 fake timers 推進 5 秒
  Then 兩個端點各被呼叫恰一次（SI 查詢覆寫了預設的重試）
  And 另一組情境：先回成功並顯示資料，卸載後重新掛載（替身此時延遲回應）：重掛後先顯示載入中、不先顯示舊資料，且重新發出新請求（`gcTime` 與 `staleTime` 皆為 0）
  And `lib/api/queries.ts` 的 SI 查詢設定（以匯出的查詢選項或 hook 的實際行為取得）為 `retry` 假值、`staleTime` 為 0、`gcTime` 為 0
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_7]"
```

```gherkin
# AT-932-3-E-1
# 對應 AC: AC-932-3（PRD AC-SI-32-3 的非錯誤對照組（空表只在 SI 真的回空時合法）；R4）（Bridge）合法輸出不是錯誤：空 `items`、非空 `ne` 與 `problems`、stderr 雜訊、未知頂層鍵、`null` 欄位皆原樣成功回傳
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_932_3_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 合法輸出不是錯誤

Scenario: 空 items、雜訊 stderr、未知鍵、null 欄位皆原樣回傳為 200
  Given `FK` 假 CLI 樹與活 Bridge
  When 依序令假 CLI：(a) 輸出合法 export 物件，`items` 為空、`ne` 含一項、`problems` 含一項；(b) rc 為 0、stderr 有 200 字元雜訊、stdout 為合法物件；(c) 合法物件多一個未知的頂層鍵 `future_key`；(d) `next_since` 為 `null`、`truncated` 為 `false`、`head_sha` 為 `null`
  Then 四個子情境 `run_export` 皆回傳解析後的物件而不拋例外，物件逐值等於假 CLI 的輸出（含 `ne`、`problems`、`future_key`、`null`）
  And 透過活 Bridge 請求 `/si/observations`：(a) 回 200 且 `items` 為空陣列、`ne` 與 `problems` 原樣（空是 SI 真的回空時的合法答案，不是 503）；(b)(c)(d) 皆 200
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_1]"
```

```gherkin
# AT-932-3-E-2
# 對應 AC: AC-932-3（PRD AC-SI-32-3；逾時殺行程樹、無孤兒；R3、R4）（Bridge）逾時時整棵行程樹（含孫行程）被終止、呼叫在有界時間內返回、無孤兒，且之後的正常呼叫成功
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_932_3_E_2 -q（cwd＝AgentConsole/engine-bridge）

Feature: 逾時終止整棵行程樹

Scenario: 拋 timeout、耗時有界、假 CLI 與孫行程皆消失
  Given 假 CLI 啟動一個孫行程（與自己各睡 30 秒，兩個 pid 寫入檔案），`SI_CLI_TIMEOUT_SECONDS` 以 monkeypatch 設為 0.5
  When 呼叫 `run_export`
  Then 在 10 秒內拋 `ApiError`，`cause` 為 `timeout`、`detail` 以 `rc=none; stderr=` 起頭；整個呼叫耗時小於 10 秒（遠小於假 CLI 的 30 秒睡眠）
  And 以 `psutil` 檢查假 CLI 行程與其孫行程的 pid 在呼叫返回後 3 秒內皆已不存在（沒有孤兒）
  And 逾時後立即對正常的假 CLI 再呼叫一次成功（Bridge 本身未被拖垮）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_2]"
```

```gherkin
# AT-932-3-E-3
# 對應 AC: AC-932-3（PRD AC-SI-32-3；stdout 上限；R3、R4）（Bridge）子行程持續輸出時，超過 `SI_STDOUT_MAX_BYTES` 即終止並回 503，Bridge 不隨輸出無限吃記憶體
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_932_3_E_3 -q（cwd＝AgentConsole/engine-bridge）

Feature: stdout 超過上限即終止行程並失敗

Scenario: cause 為 stdout_too_large，行程被殺，寫出量有界
  Given 假 CLI 持續印出無換行的資料（迴圈寫出，並把累計寫出位元組數記入檔案），`SI_STDOUT_MAX_BYTES` 以 monkeypatch 設為 4096
  When 呼叫 `run_export`
  Then 在 10 秒內拋 `ApiError`，`cause` 為 `stdout_too_large`；假 CLI 行程已被終止（`psutil` 檢查 pid 不存在）
  And 假 CLI 被殺時累計寫出的位元組數不超過 1 MiB（寬鬆上界：上限加管道緩衝的倍數），證明 Bridge 是邊讀邊判、不是讀完才判
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_3]"
```

```gherkin
# AT-932-3-E-4
# 對應 AC: AC-932-3（PRD AC-SI-32-3；不得渲染過期資料（成功轉失敗）；R12）（frontend）先成功顯示資料、重新整理失敗後，舊資料全部從 DOM 消失只剩錯誤態；改回成功並重試後內容恢復
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_3_E_4（cwd＝AgentConsole/frontend）

Feature: 成功後轉失敗時舊資料消失

Scenario: 錯誤態出現，舊列與橫幅內容全部移除，恢復後回到正確內容
  Given `fetch` 替身先回成功（黃金檔狀態 A），渲染 `SiView` 至橫幅與 12 項觀察就緒
  When 把替身改為對所有 SI 端點回 503，並點 `重新整理`
  Then 橫幅與觀察分頁轉為錯誤態：先前的 `si-obs-row-` 開頭項目、`si-head-sha`、`si-pending-props` 全部從 DOM 消失，沒有上一次成功的資料殘留（`isError` 時不渲染 `data`）
  And 替身再改回成功並點 `重試`，內容恢復為狀態 A 的內容
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_4]"
```

```gherkin
# AT-932-3-E-5
# 對應 AC: AC-932-3（PRD AC-SI-32-3；各面板失敗互相獨立且不渲染成空；R12、R13）（frontend）`status` 失敗時橫幅顯示錯誤而非「無事件」；清單失敗時該分頁顯示錯誤而非空表；其他面板不受影響
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_3_E_5（cwd＝AgentConsole/frontend）

Feature: 部分面板失敗不被渲染成空或無事件

Scenario: status 失敗不顯示無事件，清單失敗不顯示空表，其他面板照常
  Given `fetch` 替身：`/api/v1/si/status` 回 503，其餘端點回成功（黃金檔狀態 A）
  When 渲染 `SiView`
  Then 橫幅顯示錯誤態，**沒有** `si-no-event`、沒有 `si-pending-props`；觀察分頁仍正常顯示 12 項
  And 反向情境（`/api/v1/si/observations` 回 503、其餘成功）：橫幅正常顯示，觀察分頁顯示錯誤態而非空表；切到提案分頁（成功）可正常顯示，錯誤只限於失敗的面板
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_5]"
```

```gherkin
# AT-932-3-E-6
# 對應 AC: AC-932-3（PRD AC-SI-32-3 末句；量不到不得顯示為零或通過；R13、R16）（frontend）`NOT-EVALUABLE` 物件、`headSha` 為 `null`、`card` 為 `null`、`ne`、`unavailable` 與空事件加 carrier NE，一律以量不到加原因呈現，不顯示為 0、無、通過或正常
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/si/SiView.test.tsx -t AT_932_3_E_6（cwd＝AgentConsole/frontend）

Feature: NOT-EVALUABLE 與量不到的呈現規則

Scenario: NE 物件、null、ne 與 unavailable 項皆以量不到加原因呈現
  Given 黃金檔狀態 A 之上由測試改寫回應：`status.capacity` 為 `status` 是 `NOT-EVALUABLE`、`reason` 是 `capacity-verb-not-established` 的物件；`headSha` 為 `null` 且 `ne` 含 `field` 為 `head_sha`、`reason` 為 `git-unavailable` 的一項；`status.unavailable` 非空且 `eventsDetected` 為空；另一份 `events` 回應 `items` 為空、`ne` 含 `field` 為 `events`、`reason` 為 `carrier-not-established` 的一項；一筆提案 `card` 為 `null` 且 `ne` 含對應的 `card` 項
  When 渲染 `SiView` 並切到事件與提案分頁
  Then `si-capacity` 的文字含 `NOT-EVALUABLE` 與 `capacity-verb-not-established`，不含 `通過`、`正常`，且其值不顯示為 `0`；`si-head-sha` 顯示 `量不到（NOT-EVALUABLE）`；`si-ne-list` 含 `head_sha：git-unavailable`；`si-no-event` 的文字為 `無事件（尚有 1 項量不到）`（不是純 `無事件`）
  And 事件分頁顯示 `events：carrier-not-established` 的說明，不得只顯示 `沒有事件`；提案列顯示 `卡面量不到（NOT-EVALUABLE）`
  And `problems` 非空時 `si-problems-list` 逐項顯示 `<subject> <code> <detail>`；`ne` 與 `problems` 皆為空時兩個區塊都不渲染
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_3_E_6]"
```

```gherkin
# AT-932-4-1
# 對應 AC: AC-932-4（PRD AC-SI-32-4；backend 的 JWT 與角色；R7）（backend）六個 GET：無 token 與亂碼 token 為 401（不觸及 Bridge），VIEWER／OPERATOR／ADMIN 皆 200
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_4_1*"（cwd＝AgentConsole/backend）

Feature: 無 JWT 回 401、三種角色可讀

Scenario: 401 不觸及 Bridge，三角色 200
  Given `MINI.si` 回放黃金檔；三個角色的 token、無 token、亂碼 token（`Bearer garbage`）
  When 對六個 `GET /api/v1/si/…` 各以各身分請求
  Then 無 token 與亂碼 token 皆為 401（回應沒有 `$.data`）；VIEWER、OPERATOR、ADMIN 皆為 200 且 `$.data` 非空
  And 全部 401 請求之後 `MINI.requests()` 仍為空（401 不觸及 Bridge）；成功請求每個恰一次 Bridge 呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_4_1]"
```

```gherkin
# AT-932-4-2
# 對應 AC: AC-932-4（PRD AC-SI-32-4；未登入導向登入且不發 SI 請求；R12）（frontend）未登入開 `/self-improving`：導向 `/login?next=…`、`SiView` 不渲染、沒有任何 SI 請求；已登入對照組正常
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/si-login-gate.test.tsx -t AT_932_4_2（cwd＝AgentConsole/frontend）

Feature: 未登入時 /self-improving 導向登入且不發 SI 請求

Scenario: router.replace 帶 next，SiView 未渲染，無 SI fetch
  Given 沿 `layout.test.tsx` 的方式渲染 `RootLayout`（`next/navigation` 與 `next/link` 替身），`usePathname` 為 `/self-improving`、`window.history.pushState` 把網址設為 `/self-improving`、沒有 session、`fetch` 為計數替身；children 為真正的 `SiView`
  When 等待水合與 effect
  Then `router.replace` 被呼叫恰一次，參數為 `/login?next=` 加 `encodeURIComponent` 套用於 `/self-improving` 的結果
  And `SiView` 沒有被渲染（`si-view` 不存在，內容區為載入中指示）；`fetch` 沒有任何對 `/api/v1/si/` 的呼叫
  And 對照組：改以 OPERATOR 的 session 渲染時，`si-view` 存在且 `fetch` 對 `/api/v1/si/status` 有呼叫
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_4_2]"
```

```gherkin
# AT-932-4-3
# 對應 AC: AC-932-4（PRD AC-SI-32-4；瀏覽器不直連 Bridge；R11）（frontend）前端非測試原始碼的字串字面值沒有以 `/si/` 起頭者、沒有 8081 與 BRIDGE 字樣；掃描器有負控且範圍含 `lib/api/endpoints.ts`
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run components/domain/si/si.static.test.ts -t AT_932_4_3（cwd＝AgentConsole/frontend）

Feature: 前端原始碼不含 Bridge 路徑字面

Scenario: SI 路徑字面一律以 /api/v1/si/ 起頭，無 8081 與 BRIDGE 字樣
  Given `AgentConsole/frontend/` 內 `app/`、`components/`、`lib/`、`hooks/` 的非測試原始碼
  When 讀檔掃描字串字面值（以各種引號與反引號包住者）
  Then 沒有任何字面值以 `/si/` 起頭（Bridge 路徑）；所有含 `si/` 路徑段的字面值皆以 `/api/v1/si/` 起頭；沒有 `8081` 字面、沒有 `BRIDGE` 字樣的環境變數讀取（`NEXT_PUBLIC_*` 不指向 Bridge）
  And 掃描器自帶負控（違規字面值 `/si/status` 與一個指向 `engine-bridge:8081` 的 `/si/runs` 網址回非空；`/api/v1/si/status` 回空）；掃描範圍非空且含 `lib/api/endpoints.ts`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_4_3]"
```

```gherkin
# AT-932-4-4
# 對應 AC: AC-932-4（PRD AC-SI-32-4 的 P 型劃界補機械物（Architecture §12.1 L-6）；R23）（Bridge／compose）`docker-compose.yml` 的 engine-bridge 服務沒有 `ports` 發布，網路只有 `backend-net` 與 `db-net`；檢查函式有負控
# 測試類型: Contract
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_932_4_4 -q（cwd＝AgentConsole/engine-bridge）

Feature: compose 的 engine-bridge 沒有對 host 發布任何埠

Scenario: 無 ports、網路為 backend-net 與 db-net，負控觸發
  Given `AgentConsole/docker-compose.yml`（`yaml.safe_load`）
  When 取 `services` 下的 `engine-bridge`
  Then 沒有 `ports` 鍵（沒有對 host 發布任何埠）；`networks` 只含 `backend-net` 與 `db-net`；`environment` 中沒有把 8081 綁到 `0.0.0.0` 或 host 的發布設定
  And `8081` 作為埠值的出現位置只限於下列三個鍵路徑：對 `yaml.safe_load` 的結果遞迴走訪所有純量字串（註解不在解析結果內，故不計；也不斷言出現次數），含 `8081` 者的鍵路徑必為 `services.backend.environment.ENGINE_BRIDGE_URL`（容器網路位址）、`services.engine-bridge.environment.BRIDGE_PORT`（容器內監聽埠）或 `services.engine-bridge.healthcheck.test`（容器內位址）之一；任何 `ports` 項、任何其他鍵路徑含 `8081` 即為紅
  And 檢查函式自帶負控：對加了一條把 `8081` 對映到 host 的 `ports` 的服務片段、以及在白名單以外的鍵路徑（例如 `services.frontend.environment`）含 `8081` 的片段，皆回非空；對只在 YAML 註解裡寫 `8081` 的片段回空（註解不計）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_4_4]"
```

```gherkin
# AT-932-4-E-1
# 對應 AC: AC-932-4（PRD AC-SI-32-4；Viewer 以上可讀單筆，id 嚴格編碼；R7、R8）（backend）三種角色對單筆提案的讀取結果一致；不存在的 id 為 404 `si_not_found`；含空白、中文、問號、井號與超長的 id 經 HTTP 送入時被編碼為單一路徑段，回應收斂為 404 或 422
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_932_4_E_1*"（cwd＝AgentConsole/backend）

Feature: 三種角色讀單筆提案一致，id 編碼為單一路徑段

Scenario: 真 id 200 卡面相同、不存在 id 404、惡意 id 不改變 Bridge 路徑
  Given `MINI.si` 回放黃金檔（含單筆 `PROP-SI-004`），對一個不存在的 id 回 404 `si_not_found`，並記錄每個 Bridge 請求的原始 URI
  When VIEWER、OPERATOR、ADMIN 各請求 `GET /api/v1/si/proposals/PROP-SI-004`，以及把 `PROP-SI-004` 的序號改為 998 的不存在 id
  Then 三個角色對真 id 皆 200、`$.data.items` 恰一筆且 `card` 逐位元組等於黃金檔；對不存在的 id 皆 404、`$.reason` 為 `si_not_found`（各角色一致）
  And 另以含空白、中文、`?`、`#` 與 1000 字元長字串的 id 各請求一次（測試客戶端把 id 編為單一路徑段後送入；含編碼斜線、編碼百分號、分號、反斜線與 `..` 的形態會被 `StrictHttpFirewall` 在控制器之前以 400 拒絕，不經 HTTP 送入，其編碼改由介面卡層的單元 AT 斷言，R7）：Bridge 收到的原始 URI 路徑恰為 `/si/proposals/` 加編碼後的單一段，不出現多一層路徑（沒有路徑穿越）
  And 上述每個 id 各以兩種 Bridge 回應對照：令 `si.notFoundIds` 含該 id 時回應恰為 404 且 `$.reason` 為 `si_not_found`；改令 `si.invalid` 時回應恰為 422 且 `$.details.bridgeReason` 為 `invalid_request`；任一情境都不為 400、不為 5xx
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_4_E_1]"
```

```gherkin
# AT-932-6-1
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (a)(e)；登記表形狀與七項內容；R20）（frontend）`NAV_REGISTRY` 恰七項，`id`／`label`／`order`／`mobile`／`href` 逐項符合 R20，唯一性與型別正確
# 測試類型: Unit
# 自動化工具: vitest（純函式表驅動，不渲染元件、無網路）
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_1（cwd＝AgentConsole/frontend）

Feature: 登記表恰七項且欄位值符合 R20

Scenario: id、label、order、mobile、href 逐項相符，mobile 為真的項數不超過 6
  Given `lib/nav/registry.ts` 的 `NAV_REGISTRY`
  When 檢查每一項
  Then 共 7 項；`id` 依序為 `dashboard`、`projects`、`import`、`execute`、`monitor`、`settings`、`self-improving`；`label` 依序為 `儀表板`、`專案管理`、`BRD/PRD 匯入`、`執行中心`、`監控中心`、`系統設定`、`自我進化`；`order` 依序為 10、20、30、40、50、60、70；`id` 與 `order` 各自唯一
  And `mobile` 依序為 `true`、`true`、`true`、`true`、`true`、`true`、`false`；`mobile` 為 `true` 的項數不超過 6；每項 `enabled` 為布林、`roles` 缺或為只含 `ADMIN`、`OPERATOR`、`VIEWER` 的陣列、`match` 為函式、`href` 為字串或函式、`icon` 為 React 元件（函式或帶 `$$typeof` 的物件）
  And 第七項 `href` 為 `/self-improving`、`roles` 缺、`enabled` 為 `true`、`icon` 與其他六項皆不同；`execute` 與 `monitor` 的 `href(ctx)` 對 `currentProjectId` 為 `null` 回 `/projects`，對 `p1` 分別回 `/projects/p1/execute` 與 `/projects/p1/monitor`；其餘五項的 `href` 依序為字串 `/`、`/projects`、`/import`、`/settings`、`/self-improving`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_1]"
```

```gherkin
# AT-932-6-2
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (d)；每列 href 對應存在的路由頁；R20）（frontend）登記表每一項的 `href`（字串，或函式型的各解析結果）都對應存在的 `app/**/page.tsx`；檢查函式對自造壞登記表回報
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_2（cwd＝AgentConsole/frontend）

Feature: 每列 href 都對應存在的 app/**/page.tsx

Scenario: 字串與函式型 href 的各分支皆指向真路由，檢查函式有負控
  Given `app/` 目錄下全部 `page.tsx` 的相對路徑（測試以 `readdirSync` 遞迴取得）轉成路由樣式（方括號段為單段萬用）
  When 對登記表每一項的 `href`（字串直取；函式以 `currentProjectId` 為 `null` 與 `p1` 各解析一次）取路徑部分（去查詢與雜湊）逐段比對
  Then 每個解析結果都至少對應一個存在的路由樣式（`/` 對 `app/page.tsx`、`/projects` 對 `app/projects/page.tsx`、`/projects/p1/execute` 對 `app/projects/[projectId]/execute/page.tsx`、`/self-improving` 對 `app/self-improving/page.tsx`）；路由表非空且含上述四個樣式
  And 測試內的檢查函式對自造登記表回報：指向不存在路由（例如 `/nope`）者、函式型 `href` 的任一分支指向不存在路由者、空字串 `href`；對真登記表回空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_2]"
```

```gherkin
# AT-932-6-3
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (f)；match 對代表路徑互斥；R20、R21）（frontend）對代表路徑表，七項的 `match` 恰好命中期望的單一項或無項，互斥成立，邊界路徑不誤命中
# 測試類型: Unit
# 自動化工具: vitest（純函式表驅動，不渲染元件、無網路）
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_3（cwd＝AgentConsole/frontend）

Feature: 代表路徑表：恰一項命中或無項命中

Scenario: 互斥成立，execute 路徑不被專案管理吃掉，邊界路徑不命中
  Given 代表路徑表（路徑對期望命中項，無者為 none）：`/`對 dashboard；`/projects`、`/projects/new`、`/projects/p1`、`/projects/p1/edit`、`/projects/p1/goals`、`/projects/p1/goals/g1/tasks/t1/edit` 對 projects；`/projects/p1/execute` 對 execute；`/projects/p1/monitor` 對 monitor；`/import` 對 import；`/settings`、`/settings/x` 對 settings；`/self-improving`、`/self-improving/x` 對 self-improving；`/self-improving-x`、`/projects-x`、`/unknown`、`/login`、`/api/health`、空字串對 none（`/projects-x` 釘住 R20 對 `projects` 的邊界：以 `/projects` 全等或 `/projects/` 起頭才命中）
  When 對每個路徑計算七項 `match` 為真的項集合
  Then 每個路徑的命中集合恰為期望（單一項或空集合），沒有任何路徑被兩項同時命中；`/projects/p1/execute` 只命中 `execute`（`projects` 的 `match` 對它為假）
  And `/self-improving-x` 不命中任何項（第七項的邊界判斷以全等或帶斜線的前綴為準）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_3]"
```

```gherkin
# AT-932-6-4
# 對應 AC: AC-932-6（PRD AC-SI-32-6；Architecture §5.2 硬規則 5 的機械檢查；R21）（frontend）`ToolsRegion.tsx` 不含 `const NAV`、`activeNav`、`hrefFor` 與入口標籤字面，含自登記表的 import；檢查函式有負控
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_4（cwd＝AgentConsole/frontend）

Feature: ToolsRegion.tsx 不再持有入口常數與路徑分支

Scenario: 無 const NAV、activeNav、hrefFor，無標籤字面，檢查函式有負控
  Given `components/layout/ToolsRegion.tsx` 的原始碼
  When 以讀檔斷言檢查
  Then 不含 `const NAV`、`function activeNav`、`hrefFor`，且含自 `@/lib/nav/registry` 的 import；以登記表參數化函式取得可見項與 active
  And 不含任何入口標籤字面 `儀表板`、`專案管理`、`BRD/PRD 匯入`、`執行中心`、`監控中心`、`系統設定`、`自我進化`（標籤只住登記表）；不含以 `pathname.startsWith` 接路徑字面值決定 active 或 href 的敘述
  And 對自造的違規原始碼（含 `const NAV` 開頭的常數、含 `pathname.startsWith` 接路徑字面值）檢查函式回非空（負控）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_4]"
```

```gherkin
# AT-932-6-5
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (a)；加一列即多一個入口、不改元件；R21）（frontend）以替身把登記表換成「真登記表加一列」：`ToolsRegion` 多出該入口、位置依 `order`、其餘入口不變，且元件原始碼不被修改
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/ToolsRegion.test.tsx -t AT_932_6_5（cwd＝AgentConsole/frontend）

Feature: 登記表加一列即出現入口，元件原始碼不變

Scenario: 多一個連結且位置依 order，元件檔雜湊前後相同
  Given 以 `vi.mock` 把 `@/lib/nav/registry` 的 `NAV_REGISTRY` 換成真登記表加一列：`id` 為 `demo`、`label` 為 `示範功能`、`href` 為 `/demo`、`order` 為 55、`enabled` 為 `true`、`mobile` 為 `false`、`match` 命中 `/demo`；OPERATOR 已登入並渲染 `ToolsRegion`
  When 檢視主導覽
  Then 多出一個名稱為 `示範功能`、`href` 為 `/demo` 的連結，位置在 `監控中心` 與 `系統設定` 之間；其餘七個連結不變
  And 當路徑為 `/demo` 時該連結的 `aria-current` 為 `page`（`match` 取自登記表那一列）；以讀檔斷言 `ToolsRegion.tsx` 不含字串 `demo`（元件沒有任何針對新入口的程式碼，加一列確實不需改元件）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_5]"
```

```gherkin
# AT-932-6-6
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (b)；enabled 與 roles 的可見性；R21）（frontend）`enabled` 為假、`roles` 不含目前角色的項不渲染（不在 DOM）；符合者渲染；`roles` 缺者三種角色皆可見
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/ToolsRegion.test.tsx -t AT_932_6_6（cwd＝AgentConsole/frontend）

Feature: enabled 為假或角色不符的項目不渲染

Scenario: 各角色可見集合相符，隱藏者不在 DOM
  Given 替身登記表加三個額外項：`enabled` 為 `false` 者、`roles` 為只含 `ADMIN` 者、`roles` 含 `OPERATOR` 與 `ADMIN` 者（`id` 各異）
  When 分別以 VIEWER、OPERATOR、ADMIN 渲染
  Then VIEWER 看不到這三個額外項；OPERATOR 看得到第三者、看不到 `roles` 只含 `ADMIN` 者與 `enabled` 為 `false` 者；ADMIN 看得到後兩者、看不到 `enabled` 為 `false` 者
  And 被隱藏的項目不存在於 DOM（以名稱查詢連結得到 `null`），不是以 CSS 隱藏；`roles` 缺的既有項目三種角色都看得到
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_6]"
```

```gherkin
# AT-932-6-7
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (c)；依 order 升冪；R21）（frontend）登記表以亂序提供時，主導覽的 DOM 順序仍依 `order` 升冪；同 `order` 者保持登記表原序
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/ToolsRegion.test.tsx -t AT_932_6_7（cwd＝AgentConsole/frontend）

Feature: 入口依 order 升冪，同序依登記表原序

Scenario: DOM 順序依 order，改 order 即移動
  Given 替身登記表以亂序提供（陣列順序打亂，`order` 值不變），另加兩個 `order` 相同（皆為 35）的項
  When 渲染 `ToolsRegion`
  Then 主導覽內連結的 DOM 順序為 `order` 升冪；`order` 相同的兩項保持登記表原序
  And 把某一項的 `order` 改成最小值後它移到最前（證明排序依 `order` 而非陣列位置）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_7]"
```

```gherkin
# AT-932-6-8
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (e)；mobile 為假的入口在 <768 不顯示；R21）（frontend）七個連結皆在 DOM（768 以上兩種形態顯示全部）；只有 `mobile` 為 `false` 的入口帶 `max-md:hidden`；`aria-label` 與 `title` 不隨 `mobile` 改變
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/ToolsRegion.test.tsx -t AT_932_6_8（cwd＝AgentConsole/frontend）

Feature: mobile 旗標以 max-md:hidden 類別落實

Scenario: 七個連結都在 DOM，僅 mobile 為假者帶 max-md:hidden
  Given 真登記表，OPERATOR 渲染 `ToolsRegion`
  When 檢查七個連結的 `className`
  Then 七個連結都在 DOM 內；`mobile` 為 `false` 的 `自我進化` 連結的類別含 `max-md:hidden`，其餘六個連結的類別不含它
  And 以替身登記表把 `自我進化` 的 `mobile` 改為 `true` 後，該連結不再含 `max-md:hidden`；把任一既有項改為 `false` 後它含 `max-md:hidden`；`aria-label` 與 `title` 恆等於 `label`（不隨 `mobile` 改變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_8]"
```

```gherkin
# AT-932-6-9
# 對應 AC: AC-932-6（PRD AC-SI-32-6 (f)；active 為第一個命中的可見項，未知路徑無 active；R21）（frontend）對代表路徑表，`aria-current` 恰在期望項上；未知路徑主導覽內沒有任何 `aria-current`（尤其不是專案管理）
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/layout/ToolsRegion.test.tsx -t AT_932_6_9（cwd＝AgentConsole/frontend）

Feature: active 依序第一個命中，未知路徑不亮任何項

Scenario: 代表路徑的 aria-current 與期望一致
  Given 真登記表，`usePathname` 替身可改，OPERATOR 渲染 `ToolsRegion`
  When 對代表路徑表（與登記表測試相同的表）逐一渲染
  Then 每個路徑下 `aria-current` 為 `page` 的元素恰為期望的項；期望為 none 的路徑（`/unknown`、`/self-improving-x`、`/api/health`）主導覽內**沒有任何** `aria-current` 元素，尤其不是 `專案管理`；`/login` 時沒有 `主導覽`
  And `/projects/p2/goals` 時 `專案管理` 為 active、`執行中心` 的 `href` 為 `/projects/p2/execute`（網址中的專案，沿舊測試語意）；`/self-improving` 時 `自我進化` 為 active 且其餘皆否
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_9]"
```

```gherkin
# AT-932-6-E-1
# 對應 AC: AC-932-6（PRD AC-SI-32-6 負控；登記表檢查函式的違規樣本；R20、R21）（frontend）登記表檢查函式（唯一性、`mobile` 項數、路由存在、`match` 互斥）對六種自造違規各自回報恰對應的違規，真登記表回空
# 測試類型: Unit
# 自動化工具: vitest（純函式表驅動，不渲染元件、無網路）
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_E_1（cwd＝AgentConsole/frontend）

Feature: 登記表檢查函式的違規樣本各自觸發

Scenario: 重複 id、重複 order、七項皆 mobile、壞 href、match 重疊、order 非數字
  Given 測試內的登記表檢查函式與一組自造登記表
  When 逐一餵入：重複 `id`、重複 `order`、七項 `mobile` 皆為 `true`、`href` 指向不存在路由、兩項 `match` 同時命中同一代表路徑、`order` 非數字
  Then 每個自造登記表都被檢查函式回報恰對應的違規；真登記表回空
  And 各違規各由一個獨立樣本觸發（一個樣本只含一種違規，彼此不互相掩蓋）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_E_1]"
```

```gherkin
# AT-932-6-E-2
# 對應 AC: AC-932-6（PRD AC-SI-32-6；既有六項行為相容（唯一差異為未知路徑）；R20、R21、R22）（frontend）以舊 `activeNav`／`hrefFor` 的行為表對照新登記表：六項的 active 與 href 全部相同，唯一差異是未知路徑由 `projects` 改為無 active
# 測試類型: Unit
# 自動化工具: vitest（純函式表驅動，不渲染元件、無網路）
# 判定指令: npx vitest run lib/nav/registry.test.ts -t AT_932_6_E_2（cwd＝AgentConsole/frontend）

Feature: 舊六項的 active 與 href 行為不變，唯一差異明列

Scenario: 新舊對照表逐項相同，未知路徑由 projects 改為無 active
  Given 舊行為表（取自改動前的 `ToolsRegion.tsx` 與 `layout.test.tsx`）：`/`對 dashboard、`/import` 對 import、`/settings` 對 settings、`/projects/<id>/execute` 對 execute、`/projects/<id>/monitor` 對 monitor、其餘以 `/projects` 起頭者對 projects；href 為 `/`、`/projects`、`/import`、`/settings`，有專案時 `/projects/<id>/execute` 與 `/projects/<id>/monitor`，無專案時 `/projects`
  When 以新登記表對相同輸入計算 active 與 href
  Then 六項的 active 判定與 href 全部相同；**唯一差異**是舊行為下不屬於任何已知前綴的路徑（`/unknown`、`/foo/bar`）原 fallback 為 `projects`，新行為為無 active（本 AT 明列此差異並釘住新行為）
  And `layout.test.tsx` 既有的專案頁斷言（`/projects/p2/goals` 時 `執行中心` 指向 `/projects/p2/execute`、`專案管理` 為 active）在登記表化後仍通過（同檔單跑該測試為證）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_932_6_E_2]"
```

```gherkin
# AT-940-1-1
# 對應 AC: AC-940-1（本檔自增（`AC-P1b-040-1`）；`SI_ROOT` 設定解析；R1）（Bridge）`load_settings` 對 `SI_ROOT` 七種輸入的解析結果，拒檔案系統根，不檢查存在性，不併入 `allowed_path_roots`，既有欄位不變
# 測試類型: Unit
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_940_1_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: SI_ROOT 設定的七種輸入

Scenario: 解析結果、拒絕根目錄、不併入 allowed_path_roots
  Given `load_settings` 與以 monkeypatch 指向 tmp 內兩種目錄的 `REPO_ROOT`：一個內容像 monorepo 的目錄與一個內容不像的目錄
  When 依序以環境映射呼叫：(a) 未設 `SI_ROOT` 且 `REPO_ROOT` 像 monorepo；(b) 未設且 `REPO_ROOT` 不像（如容器內）；(c) `SI_ROOT` 為全空白；(d) `SI_ROOT` 為含 `..` 段的相對路徑；(e) `SI_ROOT` 為 tmp 內一個存在的絕對目錄；(f) `SI_ROOT` 為不存在的絕對路徑；(g) `SI_ROOT` 為檔案系統根（依平台取 `Path(...).anchor`）
  Then (a) `si_root` 等於 `REPO_ROOT.resolve()`；(b) 為 `None`；(c) 與 (a) 或 (b) 相同（依 `REPO_ROOT` 而定）；(d)(e)(f) 皆等於 `Path(raw).resolve()`（不檢查存在性，(f) 不拋例外）；(g) 拋 `SettingsError` 且訊息含 `SI_ROOT`
  And 各子情境的 `allowed_path_roots` 都不含 `si_root`（除非 `BRIDGE_ALLOWED_PATH_ROOTS` 另外明列）；`Settings` 的 `repr` 不洩露任何機密（沒有新增權杖欄位）；既有欄位的預設值與解析不變（對既有環境映射的結果與改動前快照逐欄相同）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_1_1]"
```

```gherkin
# AT-940-1-E-1
# 對應 AC: AC-940-1（本檔自增；README 與設定檔頭註解不漂移；R1）（Bridge／文件）`engine-bridge/README.md` 與 `app/settings.py` 檔頭註解都含 `SI_ROOT`，README 含六個端點路徑與兩個 reason；檢查函式有負控
# 測試類型: Contract
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_940_1_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: README 與 settings 檔頭註解已列 SI_ROOT 與端點

Scenario: 兩處皆含 SI_ROOT，README 含六端點與兩個 reason，負控觸發
  Given `AgentConsole/engine-bridge/README.md` 與 `app/settings.py` 檔頭註解的文字
  When 以讀檔斷言檢查
  Then 兩者都含 `SI_ROOT`；README 含六個端點路徑字串 `/si/status`、`/si/observations`、`/si/events`、`/si/proposals`、`/si/proposals/{id}`、`/si/runs` 與 `si_unavailable`、`si_not_found`
  And 檢查函式對缺 `SI_ROOT` 或缺任一端點字串的文字回非空（負控）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_1_E_1]"
```

```gherkin
# AT-940-2-1
# 對應 AC: AC-940-2（本檔自增（`AC-P1b-040-2`）；argv、cwd、環境與預設常數；R2、R3）（Bridge）對五個 kind 與旗標組合，假 CLI 記錄的 argv、cwd、環境符合 R3：旗標序固定、不帶 `--repo`／`-I`／`-P`、環境只有白名單與固定鍵、哨兵機密不洩入；`si_cli` 預設常數符合 R2
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_940_2_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 子行程 argv、cwd 與環境白名單

Scenario: argv 固定、無 --repo、無 -I、環境只含白名單與固定鍵，機密不洩入，預設常數相符
  Given `FK` 假 CLI 樹，Bridge 行程環境事先放入哨兵：`BRIDGE_DB_DSN`、`MINIMAX_API_KEY`、`AUTOSDD_SI_DIR`、`PYTHONPATH`、`SDD_ROOT`、`CLAUDE_CONFIG_DIR`，並確認 `PATH`、`HOME`、`USERPROFILE`、`LANG` 在場
  When 對五個 kind 與旗標組合各呼叫 `run_export`
  Then 假 CLI 記錄的 argv 依序為直譯器（`sys.executable`）、`<R>/tools/selfimproving.py`、`export`、`--json`、`--kind`、<kind>，其後的旗標只可能是 `--since`、`--limit`、`--id` 且依此序；不含 `--repo`、`-I`、`-P`；假 CLI 自記的 `sys.flags.safe_path` 為假（子行程沒有以 `-I` 或 `-P` 啟動）
  And cwd 正規化後等於 `R`；假 CLI 讀自己的標準輸入立即得到 EOF（子行程的 `stdin` 為 `DEVNULL`）；環境紀錄中除白名單鍵與固定鍵外沒有任何其他變數（以假 CLI 記錄的全部環境名稱集合比對，Windows 以大寫比對）；`PYTHONUTF8` 與 `PYTHONDONTWRITEBYTECODE` 為 `1`；`GIT_CONFIG_COUNT` 為 `1`、`GIT_CONFIG_KEY_0` 為 `safe.directory`、`GIT_CONFIG_VALUE_0` 等於 `str(R)`
  And 哨兵機密值不出現在假 CLI 記錄的任何環境值中；`PATH` 與 `HOME`（或 `USERPROFILE`）的值與 Bridge 自己的相同
  And `si_cli` 的預設常數（未被 monkeypatch 時）：`SI_CLI_TIMEOUT_SECONDS` 為 15.0、`SI_EXPORT_SCHEMA_REV` 為 1、`SI_STDOUT_MAX_BYTES` 為 8 MiB（8388608）、`SI_STDERR_TAIL_CHARS` 為 1000、`SI_KINDS` 恰為 `observations`、`events`、`proposals`、`runs`、`status` 五個；且 `SI_CLI_TIMEOUT_SECONDS` 小於 20（backend 的讀取逾時，NFR-P1b-2）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_2_1]"
```

```gherkin
# AT-940-2-E-1
# 對應 AC: AC-940-2（本檔自增；環境建構純函式（名稱不分大小寫）；R3）（Bridge）環境建構純函式：白名單名稱不分大小寫比對並保留原鍵與值，其餘一律丟棄，來源中的 `GIT_CONFIG_COUNT` 被固定值覆寫，缺席的白名單鍵不補空值
# 測試類型: Unit
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_cli.py -k AT_940_2_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 環境建構純函式對混合大小寫輸入

Scenario: 白名單保留、其餘丟棄、固定鍵覆寫、缺席不補
  Given 環境建構純函式與輸入映射：混合大小寫的 `Path`、`userprofile`、`Lc_All`、`BRIDGE_X`、`bridge_y`、`MINIMAX_API_KEY`、`Autosdd_Anything`、`pythonpath`、`SDD_ROOT`、`GIT_DIR`、`GIT_CONFIG_COUNT`（來源裡已有，應被覆寫）、`KEEP_ME`
  When 以該映射呼叫環境建構純函式
  Then 輸出只含白名單三個（`Path`、`userprofile`、`Lc_All`，鍵的大小寫與值原樣保留）加五個固定鍵；`BRIDGE_X`、`bridge_y`、`MINIMAX_API_KEY`、`Autosdd_Anything`、`pythonpath`、`SDD_ROOT`、`GIT_DIR`、`KEEP_ME` 皆不在輸出；來源中已有的 `GIT_CONFIG_COUNT` 被固定值 `1` 覆寫
  And 白名單中來源沒有的名稱不補空值（例如來源無 `SYSTEMROOT` 則輸出無此鍵）；對空映射輸入，輸出恰為五個固定鍵
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_2_E_1]"
```

```gherkin
# AT-940-3-1
# 對應 AC: AC-940-3（本檔自增（`AC-P1b-040-3`）；唯讀掛載與 SI_ROOT；R23）（compose）`engine-bridge` 服務設 `SI_ROOT=/repo`，SI 相關 bind 皆為長語法唯讀，整組恰符合設計 A 或設計 B 其中之一，不掛 repo 根與真 `.git/config`，既有掛載保留
# 測試類型: Contract
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_940_3_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: compose 的唯讀掛載符合設計 A 或 B 恰其一

Scenario: SI_ROOT 為 /repo，長語法唯讀，不掛 repo 根與真 config
  Given `AgentConsole/docker-compose.yml`（`yaml.safe_load`）
  When 解析 `services` 下的 `engine-bridge`
  Then `environment` 含 `SI_ROOT` 且值為 `/repo`；`volumes` 中目標以 `/repo` 起頭者全為長語法（映射）、`type` 為 `bind`、`read_only` 為 `true`；整組恰符合設計 A（六條，來源與目標逐一相同，`bind.create_host_path` 皆為 `false`）或設計 B（`../.git` 對 `/repo/.git`，加空檔對 `/repo/.git/config`）其中之一，且不同時符合兩者
  And 沒有任何 bind 的來源為 repo 根（`..` 或 `../`）；沒有任何 bind 以真 `../.git/config` 為來源；既有三條掛載（`../AISDLC_SDD:/sdd:ro`、`engine_workspace`、`app_logs`）原樣保留
  And 若為設計 B，空檔 `AgentConsole/docker/si/git-config.empty` 存在且位元組長度為 0
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_3_1]"
```

```gherkin
# AT-940-3-E-1
# 對應 AC: AC-940-3（本檔自增；compose 檢查函式的負控；R23）（compose）檢查函式對九種壞變體（缺唯讀、短語法、`create_host_path` 為真、掛 repo 根、掛真 config、少 `packed-refs`、多掛一條、`SI_ROOT` 錯、A 與 B 混用）各自回報
# 測試類型: Unit
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_940_3_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: compose 檢查函式對壞變體各自回報

Scenario: 九種變體皆回非空並指出問題，真檔回空
  Given compose 檢查函式（輸入為 YAML 文字或解析結果）
  When 餵入下列變體：缺 `read_only`、短語法字串、`create_host_path` 為 `true`、掛 repo 根、掛真 `.git/config`、少 `packed-refs` 那一條、多一條 `../docs` 的掛載、`SI_ROOT` 為 `/srv`、設計 A 與 B 混用
  Then 每個變體都回非空並指出具體問題；真檔回空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_3_E_1]"
```

```gherkin
# AT-940-4-1
# 對應 AC: AC-940-4（本檔自增（`AC-P1b-040-4`）；CI paths 涵蓋 Bridge 差分測試的根層輸入；R24）（CI）`CLI_CLOSURE` 與 `PARAMS_SRC` 的每個輸入都被 `agentconsole-ci.yml` 的 `on.pull_request.paths` 與 `on.push.paths` 兩處涵蓋（D11 由主控代改，補上之前本 AT 為預期紅）
# 測試類型: Contract
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_940_4_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: agentconsole-ci 的 paths 兩處都涵蓋根層輸入（主控補上 paths 之前為預期紅）

Scenario: 每個輸入被 pull_request 與 push 兩處涵蓋
  Given `tests/si_repo_support.py` 的常數 `CLI_CLOSURE` 與 `PARAMS_SRC`，與 `.github/workflows/agentconsole-ci.yml`（`yaml.safe_load`）
  When 對 `on.pull_request.paths` 與 `on.push.paths` 兩處，檢查每個輸入是否被某個 glob 涵蓋（`**` 比對零至多段、`*` 比對單段內任意字元；目錄型輸入以 `<目錄>/**` 涵蓋）
  Then 兩處都涵蓋每一個輸入；兩處的 `paths` 仍含 `AgentConsole/**` 與 `.github/workflows/agentconsole-ci.yml`；`CLI_CLOSURE` 非空，且每個項目在 monorepo 內真實存在（檔案或目錄）
  And `PARAMS_SRC` 恰為 `docs/06_quality/SelfImproving_Protocol/params.json` 且被涵蓋
  And 預期紅註記：開發 agent 不得動 `.github/`，所以本 AT 在主控於同一個 commit 補上 `agentconsole-ci.yml` 的 `paths`（D11）之前為預期紅；這是連動面未收齊的偵測，不得以改弱測試、放寬涵蓋判準或跳過處理，補上之後才轉綠；開發 agent 於交卷時逐行列出需新增的 `paths` 項
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_4_1]"
```

```gherkin
# AT-940-4-E-1
# 對應 AC: AC-940-4（本檔自增；paths 涵蓋檢查函式的負控；R24）（CI）涵蓋檢查函式對「缺目錄 glob、缺檔案、只有一個觸發器缺、glob 只涵蓋單層」各變體回報缺哪一項與哪一個觸發器
# 測試類型: Unit
# 自動化工具: pytest + AST／檔案掃描（純讀取）
# 判定指令: python -m pytest tests/test_si_deploy_config.py -k AT_940_4_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: paths 涵蓋檢查函式對缺項變體回報

Scenario: 缺項、只缺一個觸發器、glob 太窄皆被指出
  Given 路徑涵蓋檢查函式
  When 餵入缺 `tools/lib/selfimproving/**` 的變體、缺 `tools/selfimproving.py` 的變體、只在 `pull_request` 有而 `push` 缺的變體、glob 寫成 `tools/lib/selfimproving/*`（只涵蓋單層）的變體
  Then 各變體皆回非空並指出缺哪一項與哪一個觸發器；真檔回空
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_4_E_1]"
```

```gherkin
# AT-940-5-1
# 對應 AC: AC-940-5（本檔自增（`AC-P1b-040-5`）；前端 reason 常數與 Architecture 逐字一致、不進 REASONS；R19）（frontend）`SI_REASONS` 與凍結 `Architecture.md` §11.1 的 SelfImproving reason 表逐字一致（比對範圍＝`reason` 以 `si_` 起頭且標 P1b 者；`invalid_request` 是 Bridge 層 reason、不進 `SI_REASONS`）；`REASONS` 不含這兩值；`reasons.ts` 的註解不再稱 `rtm_not_found` 為唯一例外；`reasons.test.ts` 的雙向鎖續綠；錯誤文案對照正確
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run lib/domain/si.test.ts -t AT_940_5_1（cwd＝AgentConsole/frontend）

Feature: 前端 SI reason 常數與凍結表對拍且不進 REASONS

Scenario: 兩常數出現在 Architecture 表，REASONS 不含，註解已改述，reasons.test.ts 續綠
  Given 凍結的 `AgentConsole/docs/02_architecture/Architecture.md` §11.1〈SelfImproving 相關的 reason〉表（測試以 `readFileSync` 取該表，體例同 `reasons.test.ts`）、`lib/domain/si.ts` 的 `SI_REASONS`，以及 `lib/api/reasons.ts` 的 `REASONS` 與原始碼文字
  When 讀取該表並與兩個匯出物件逐項比對，並讀取 `lib/api/reasons.ts` 的原始碼文字
  Then `SI_REASONS.UNAVAILABLE` 為 `si_unavailable`、`SI_REASONS.NOT_FOUND` 為 `si_not_found`，`Object.keys(SI_REASONS)` 恰為這兩個鍵，且兩值都出現在該表的 reason 欄；該表中 `reason` 以 `si_` 起頭且階段標示含 P1b 者（恰為 `si_unavailable` 與 `si_not_found`）全數有對應的 `SI_REASONS` 常數，其餘以 `si_` 起頭而只標 P2b 者不需要；表中的 `invalid_request`（422）是 Bridge 層的 reason（backend 以 `details.bridgeReason` 帶出，回應的頂層 `reason` 為 `ErrorReasons.BRIDGE_REJECTED`），不要求也不得有對應的 `SI_REASONS` 常數
  And `Object.values(REASONS)` 不含這兩值；`reasons.test.ts` 的雙向鎖（契約附錄 B 與 `REASONS` 逐字一致）在本改動後仍通過（同檔單跑為證）；`lib/api/reasons.ts` 的原始碼不含字串 `唯一例外`（`RTM_NOT_FOUND` 的註解已改述為例外之一），也不含 `si_unavailable` 與 `si_not_found` 字樣（註解只指向 `SI_REASONS`），且 `REASONS.RTM_NOT_FOUND` 仍為 `rtm_not_found`（本改動只動註解）
  And 錯誤態文案純函式：狀態 503 加 `si_unavailable` 對 `SI 資料面不可用`、狀態 404 加 `si_not_found` 對 `查無此筆`、其餘沿 `describeError`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_5_1]"
```

```gherkin
# AT-940-5-2
# 對應 AC: AC-940-5（本檔自增；backend 常數與帶 reason 的第二個 404；R8、R10）（backend）`ErrorReasons` 兩常數值正確；`si_not_found` 的 404 帶 `reason` 而一般 404 不帶；`NotFoundException`、`ErrorResponseDocumentation` 與 `ErrorReasons` 三檔的 `唯一例外` 字樣已改述
# 測試類型: Integration
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_940_5_2*"（cwd＝AgentConsole/backend）

Feature: backend 的 SI 常數與 si_not_found 的 404 帶 reason

Scenario: 常數值相符、404 帶 reason 而一般 404 不帶、文件字樣已改述
  Given `ErrorReasons`、`MINI.si` 回 404 `si_not_found`，以及 `NotFoundException`、`ErrorResponseDocumentation` 與 `ErrorReasons` 的原始碼
  When 以反射取兩個常數，並由 VIEWER 請求單筆提案端點
  Then `ErrorReasons.SI_UNAVAILABLE` 為 `si_unavailable`、`ErrorReasons.SI_NOT_FOUND` 為 `si_not_found`
  And VIEWER 請求 `GET /api/v1/si/proposals/PROP-SI-004` 的 404 回應 `$.reason` 為 `si_not_found`；對照：一般 404（`GET /api/v1/projects/` 加隨機 UUID）沒有 `$.reason`（證明這是帶 reason 的第二個例外，不是 404 一律帶 reason）
  And `NotFoundException`、`ErrorResponseDocumentation` 與 `ErrorReasons` 三檔原始碼不再含以 `rtm_not_found` 為唯一者的敘述（不含字串 `唯一帶 reason` 與 `唯一例外`），且 `NotFoundException` 與 `ErrorResponseDocumentation` 各含 `si_not_found`、`ErrorReasons` 含 `SI_NOT_FOUND` 的宣告（讀檔斷言）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_5_2]"
```

```gherkin
# AT-940-6-1
# 對應 AC: AC-940-6（本檔自增（`AC-P1b-040-6`）；OBS-SI-230 順帶項；R27）（frontend）專案節點編輯對話框的「執行路徑」欄下顯示 `EXECUTION_PATH_HINT`，輸入框以 `aria-describedby` 連到它，欄位標籤仍為精確的 `執行路徑`；目標與任務節點沒有此欄
# 測試類型: Integration
# 自動化工具: vitest + @testing-library/react + fetch 替身（jsdom）
# 判定指令: npx vitest run components/domain/import/NodeEditDialog.test.tsx -t AT_940_6_1（cwd＝AgentConsole/frontend）

Feature: 節點編輯對話框的執行路徑欄有兩模式說明

Scenario: 說明在欄下、輸入框以 aria-describedby 連到它、標籤精確
  Given `NodeEditDialog` 的 `target` 為專案節點、`tree` 由 `toTree` 建立、`dispatch` 為 `vi.fn()`，外包 `ToastProvider`
  When 渲染
  Then 以 `EXECUTION_PATH_HINT` 的值查文字存在，且含 `本機開發填主機路徑`、`Docker 全棧填 Bridge 容器內的路徑`、`/workspace/`、`BRIDGE_ALLOWED_PATH_ROOTS`
  And 以標籤文字 `執行路徑` 查詢取得輸入框（標籤仍為精確字串、不含說明文字），且該輸入框的可及描述等於 `EXECUTION_PATH_HINT`（`toHaveAccessibleDescription`）
  And 對目標節點與任務節點的對話框渲染時沒有 `EXECUTION_PATH_HINT`（這兩種節點沒有執行路徑欄）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_6_1]"
```

```gherkin
# AT-940-6-E-1
# 對應 AC: AC-940-6（本檔自增；單一來源，不複製字串；R27）（frontend）`NodeEditDialog.tsx` 自 `sourceRules` import `EXECUTION_PATH_HINT`、不複製其字串；三處使用者引用同一個匯出；`EntityForms.test.tsx` 既有斷言續綠
# 測試類型: Unit
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run components/domain/import/NodeEditDialog.test.tsx -t AT_940_6_E_1（cwd＝AgentConsole/frontend）

Feature: 執行路徑說明三處同源、不複製字串

Scenario: NodeEditDialog 自 sourceRules import，無長子串複製，三處同一常數
  Given `NodeEditDialog.tsx`、`EntityForms.tsx`、`SourceCard.tsx` 的原始碼與 `sourceRules.ts` 的 `EXECUTION_PATH_HINT` 常數
  When 以讀檔掃描三個原始碼與常數定義
  Then `NodeEditDialog.tsx` 含自 `./sourceRules` 或 `@/components/domain/import/sourceRules` import `EXECUTION_PATH_HINT` 的敘述；其原始碼不含該常數字串的任何連續 10 字元以上的子串（沒有複製字串）
  And 三處使用者（`SourceCard.tsx`、`EntityForms.tsx`、`NodeEditDialog.tsx`）引用的是同一個檔案匯出的同一個常數；`sourceRules.ts` 的常數值與改動前相同，`EntityForms.test.tsx` 的既有斷言單跑仍通過
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_6_E_1]"
```

```gherkin
# AT-940-7-1
# 對應 AC: AC-940-7（本檔自增（`AC-P1b-040-7`）；真 CLI 閉包完備與夾具反空轉前提；R25）（Bridge）`make_si_repo` 建出的狀態 A 與 B：CLI 閉包完備、五個 kind 的真 `export` 皆 rc 0、夾具含壞列與特殊字元與非空卡面等反空轉前提，B 相對 A 恰多一筆觀察與一筆事件
# 測試類型: Integration
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_940_7_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 夾具建構器產出可用的狀態 A 與 B

Scenario: 閉包四路徑齊備、五 kind rc 0、夾具具備反空轉前提、B 相對 A 的差異精確
  Given `si_repo_support.make_si_repo`
  When 建狀態 A 與 B
  Then `CLI_CLOSURE` 的四個路徑自 monorepo 複製進 tmp 倉（`tools/selfimproving.py`、`tools/_stdio_utf8.py`、`tools/lib/platform_utils.py`、`tools/lib/selfimproving/` 且無 `__pycache__`）；真 CLI 對五個 kind 的 `export` 皆 rc 0 並印合法 JSON；狀態 A 的 `head_sha` 為 40 碼小寫 hex、`git status --porcelain` 為空
  And 反空轉前提：觀察 12 筆（11 有效、1 壞列）；至少一筆含全形字元、一筆含反引號與雙引號、一筆 `symptom` 含 `<script>`、一筆含 Markdown 粗體與連結語法、一筆含 HTML 實體字樣、一筆 `marks` 含 `carrier=console;audit_ref=` 形態；事件恰 6 行（取自真事件帳本的複本）；`proposals` 恰 1 筆且 `card` 為非空字串、`state` 為 `proposed`；`runs` 恰 1 筆；`status.pending_props` 含該提案
  And 狀態 B 相對 A：觀察多 `OBS-SI-013`、事件多 `seq` 為 7 的 `run.open`（`RUN-SI-002`）、各回應頂層的 `head_sha` 不同、`runs` 多一筆；其餘既有項目逐值不變；`seq` 為 7 的事件與 `RUN-SI-002` 運轉列所帶的 `head_sha` 是 §5.1 的固定字面 `73ff8e3cdefeb993f9d4213ef88e3c184055a60a`（不取自建倉的 HEAD，本 AT 不斷言它等於 A 的 HEAD）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_7_1]"
```

```gherkin
# AT-940-7-E-1
# 對應 AC: AC-940-7（本檔自增；閉包缺檔時大聲失敗，不退回假 CLI；R25）（Bridge）從閉包清單移除任一必要檔後，建構器拋出清楚的例外（含 `CLI_CLOSURE` 與缺失的檔名或 import 名稱），不退回假 CLI；完整清單時成功
# 測試類型: Unit
# 自動化工具: pytest + 真 CLI 子行程 + tmp 目錄真 git + 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_export_differential.py -k AT_940_7_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 閉包缺檔時夾具建構器大聲失敗

Scenario: 拋清楚的例外並指出缺檔，完整清單時成功
  Given 建構器的內部函式可注入要複製的閉包清單
  When 從清單移除 `tools/lib/platform_utils.py`（另一個子情境移除 `tools/_stdio_utf8.py`）後建倉並要求跑 `export`
  Then 建構器丟出清楚的例外，訊息含 `CLI_CLOSURE` 與缺失的檔名或 import 名稱（來自 CLI 的 stderr），而不是退回任何假 CLI 或回傳空結果
  And 完整清單時同一入口成功（對照組）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_7_E_1]"
```

```gherkin
# AT-940-8-1
# 對應 AC: AC-940-8（本檔自增（`AC-P1b-040-8`）；springdoc 的六個 SI 路徑只有 get；R10）（backend）`/v3/api-docs` 內 `/api/v1/si/` 起頭的路徑恰六個、各只有 `get`、operationId 固定、參數型別正確
# 測試類型: Contract
# 自動化工具: JUnit 5 + Spring Boot RANDOM_PORT + Testcontainers PG18 + 迷你 Bridge
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.in.web.SiMirrorApiIT.AT_940_8_1*"（cwd＝AgentConsole/backend）

Feature: OpenAPI 文件含六個 SI 路徑且各只有 get

Scenario: 路徑集合、方法集合、operationId 與參數相符
  Given 啟動中的 backend（整合測試 context）
  When 請求 `GET /v3/api-docs`
  Then `paths` 內以 `/api/v1/si/` 起頭的鍵恰為六個（`/status`、`/observations`、`/events`、`/proposals`、`/proposals/{id}`、`/runs` 各加前綴）；每個路徑物件的方法鍵集合恰為 `get`；`operationId` 依序為 `getSiStatus`、`getSiObservations`、`getSiEvents`、`getSiProposals`、`getSiProposal`、`getSiRuns`
  And 清單類的 `since` 與 `limit` 為整數型 query 參數；`{id}` 為 path 參數；各路徑的回應含 200 與適用的 503、404 說明
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_8_1]"
```

```gherkin
# AT-940-8-2
# 對應 AC: AC-940-8（本檔自增；schema.d.ts 重產入庫且含六路徑；R11）（frontend）`lib/api/schema.d.ts` 含六個 `/api/v1/si/` 路徑與六個 operationId、各路徑只有 `get`；`gen:api` 指令存在
# 測試類型: Contract
# 自動化工具: vitest + 讀檔掃描
# 判定指令: npx vitest run lib/api/si.endpoints.test.ts -t AT_940_8_2（cwd＝AgentConsole/frontend）

Feature: 已入庫的 schema.d.ts 含六個 SI 路徑且各只有 get

Scenario: 路徑與 operationId 在檔內、無寫入方法、gen:api 指令存在
  Given `lib/api/schema.d.ts` 的原文與 `package.json`
  When 以讀檔與字串搜尋檢查
  Then 以字串搜尋找到六個 `/api/v1/si/` 路徑鍵，各自的區塊內有 `get` 而沒有 `post`、`put`、`patch`、`delete`；含六個 operationId（`getSiStatus` 等）
  And `package.json` 的 `scripts` 含 `gen:api`；重產（`npm run gen:api`）後 `schema.d.ts` 無差異由 V7 現查（本 AT 只驗已入庫的檔案內容）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_8_2]"
```

```gherkin
# AT-940-8-3
# 對應 AC: AC-940-8（本檔自增；siBase 解析規則同 sddBase；R10）（backend）`BridgeEndpoints.siBase()` 的解析規則與 `sddBase()` 相同（自訂 `sdd.engineUrl` 優先、否則 `ENGINE_BRIDGE_URL`、去尾斜線），每次呼叫重新解析
# 測試類型: Unit
# 自動化工具: JUnit 5 + MockRestServiceServer
# 判定指令: gradlew test --tests "com.aisdlc.console.adapter.out.bridge.BridgeHttpAdapterSiTest.AT_940_8_3*"（cwd＝AgentConsole/backend）

Feature: siBase 解析規則同 sddBase 且每次重新解析

Scenario: 三種設定組合下兩者相等、去尾斜線、改設定即生效
  Given `BridgeEndpoints` 與假的 `SettingValues`
  When 分別設定：(a) 只有 `ENGINE_BRIDGE_URL`（`BridgeProperties.url`）；(b) `sdd.engineUrl` 為自訂值；(c) 兩者都有且結尾帶多個斜線
  Then `siBase()` 在 (a) 為 `ENGINE_BRIDGE_URL`（去尾斜線）、(b) 為自訂值（去尾斜線）、(c) 為自訂值（去尾斜線）；且在每個情形下都等於 `sddBase()` 的回傳
  And 每次呼叫重新解析：設定改變後下一次的 `siBase()` 即為新值
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_8_3]"
```

```gherkin
# AT-940-9-1
# 對應 AC: AC-940-9（本檔自增（`AC-P1b-040-9`）；查詢參數與 id 的驗證；R5）（Bridge）未知參數、型別或範圍錯誤、不該帶參數的端點、不合格的 `{id}` 皆被擋下（422 或路徑層 404）且不啟動子行程；合法請求各啟動恰一次
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_routes.py -k AT_940_9_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 只收 since、limit 與合格的 id，其餘 422 且不啟動子行程

Scenario: 各壞輸入 422 或路徑層 404，假 CLI 無呼叫，合法對照組各啟動一次
  Given 活 Bridge，`si_root` 為 `FK` 假 CLI 樹（記錄呼叫），假 CLI 在 `--id` 為 `PROP-SI-004` 時回單筆、其餘回空
  When 依序請求：`/si/observations` 帶 `since=abc`、`since=-1`、`limit=0`、`limit=abc`、`foo=1`、`since=1&bar=2`；`/si/status` 帶 `since=1`、`limit=5`、`x=1`；`/si/proposals/PROP-SI-004` 帶 `since=1`；單筆端點的 id 取 `prop-si-004`、`PROP-SI-04`、`PROP-SI-004x`、`PROP-SI-`、含空白者、含中文者、含 `..` 者、含 `%2F` 者
  Then 帶壞參數的請求（前六個、三個 status 請求與單筆帶參請求）皆為 422，本文 `reason` 為 `invalid_request`、`violations` 非空：未知參數者 `violations[0].rule` 為 `unknown_parameter` 且 `field` 為該參數名，型別與範圍錯誤者 `field` 為 `since` 或 `limit`
  And 不合格式的 id 回 422，或在被路由器擋成 404 的形態回 404；**所有**上述被擋下的請求都沒有啟動子行程（假 CLI 的呼叫紀錄為空）
  And 合法請求的對照組：`/si/observations` 帶 `since=3&limit=2`、`/si/runs`、`/si/proposals/PROP-SI-004` 皆為 200，且子行程各啟動恰一次
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_9_1]"
```

```gherkin
# AT-940-9-E-1
# 對應 AC: AC-940-9（本檔自增；404 與 503 語意分離，limit 超限對映；R4、R5）（Bridge）合法但不存在的 id 為 404 `si_not_found`（帶 `id`）；`limit` 超過上限（CLI rc 3）與逾時為 503（帶 `cause`）；404 本文無 `cause`、503 本文無 `id`；真 CLI 對 `limit` 上限與上限加一的對照
# 測試類型: Integration
# 自動化工具: pytest + 假 CLI 樹（fake_si）+ 活 Bridge（hermetic）
# 判定指令: python -m pytest tests/test_si_routes.py -k AT_940_9_E_1 -q（cwd＝AgentConsole/engine-bridge）

Feature: 404 與 503 語意分離，limit 超限為 503 nonzero_rc

Scenario: 不存在 id 為 404 帶 id，超限與逾時為 503 帶 cause，真 CLI 對照
  Given 同上的活 Bridge 與假 CLI，以及狀態 A 的真 CLI 倉（另一個活 Bridge）
  When 請求：合法形態但不存在的 id（把 `PROP-SI-004` 的序號改為 998）；令假 CLI 回 rc 3 與 stderr 後請求 `/si/observations?limit=501`；令假 CLI 逾時後請求 `/si/runs`；對真 CLI 倉讀取 `params.json` 的 `export_limit_max`，請求 `limit` 為該值與該值加一
  Then 不存在的 id：404，本文鍵集合為 `code`、`reason`、`id`，`reason` 為 `si_not_found`，子行程啟動恰一次並帶 `--id`；假 CLI 的 rc 3：503、`cause` 為 `nonzero_rc`、`detail` 以 `rc=3; stderr=` 起頭（§7.1 ⚖ 6）；逾時：503、`cause` 為 `timeout`
  And 真 CLI 倉：`limit` 等於 `export_limit_max` 時 200，等於 `export_limit_max` 加一時 503、`cause` 為 `nonzero_rc`、`detail` 含真 CLI 的 stderr 字樣 `--limit 介於 1 與上限`
  And 404 與 503 的語意不混：`si_not_found` 的本文沒有 `cause`，`si_unavailable` 的本文沒有 `id`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_940_9_E_1]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-932-1-4 | AC-932-1 | （backend）`SiKeyNames.camel` 對映表：符合規則者轉 camelCase，其餘鍵恆等 | SiKeyNamesTest.AT_932_1_4_* | 每個輸入得到 R9 規定的輸出 |
| AT-932-1-7 | AC-932-1 | （frontend）`mergePages`、`dispositionKey`、`inDateWindow`、`filterObservations`、`bucketOptions` 的表驅動單測 | lib/domain/si.test.ts（it 標題 AT_932_1_7…） | 每張表逐項相符 |
| AT-932-1-E-8 | AC-932-1 | （frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含 `dangerouslySetInnerHTML` 與任何 Markdown／HTML 渲染器 import；掃描器有負控且範圍非空 | components/domain/si/si.static.test.ts（it 標題 AT_932_1_E_8…） | 掃描回空；負控樣本皆回非空 |
| AT-932-2-E-1 | AC-932-2 | （Bridge）鎖的判準函式對各類違規樣本逐一回非空並指出判準編號，對良性樣本回空 | tests/test_si_readonly_lock.py::test_AT_932_2_E_1_* | 違規各自觸發、良性回空 |
| AT-932-2-5 | AC-932-2 | （backend）`Si*Controller` 沒有任何非 GET 映射、`AgentBridge` 上 `si` 起頭的方法恰為 `siExport`，加入 SI 類別後既有 ArchUnit 規則仍全綠 | SiReadOnlyArchTest.AT_932_2_5_* | 規則全綠，防反空轉成立 |
| AT-932-2-7 | AC-932-2 | （frontend）`lib/api/endpoints.ts` 匯出名稱以 get、post、put、patch 或 delete 加 `Si` 起頭者恰為六個 `getSi*`；各函式的方法、網址、查詢與編碼正確 | lib/api/si.endpoints.test.ts（it 標題 AT_932_2_7…） | 六個函式與網址表全等 |
| AT-932-2-8 | AC-932-2 | （frontend）`components/domain/si/**` 與 `app/self-improving/**` 不含表單、mutation hook、非 GET 方法字樣；掃描器有負控且範圍非空 | components/domain/si/si.static.test.ts（it 標題 AT_932_2_8…） | 掃描回空；負控皆回非空 |
| AT-932-3-4 | AC-932-3 | （backend）`siExport` 的請求形態（網址、標頭、逾時 2 秒與 20 秒）與十種 Bridge 回應各自拋出的例外型別，且每種失敗只送一次請求；惡意 `{id}` 形態被編碼為單一路徑段 | BridgeHttpAdapterSiTest.AT_932_3_4_* | 例外型別與捕捉的逾時相符，期望次數為 1，id 編碼逐形態相符 |
| AT-932-4-3 | AC-932-4 | （frontend）前端非測試原始碼的字串字面值沒有以 `/si/` 起頭者、沒有 8081 與 BRIDGE 字樣；掃描器有負控且範圍含 `lib/api/endpoints.ts` | components/domain/si/si.static.test.ts（it 標題 AT_932_4_3…） | 掃描回空，負控回非空 |
| AT-932-6-1 | AC-932-6 | （frontend）`NAV_REGISTRY` 恰七項，`id`／`label`／`order`／`mobile`／`href` 逐項符合 R20，唯一性與型別正確 | lib/nav/registry.test.ts（it 標題 AT_932_6_1…） | 七項逐欄相符 |
| AT-932-6-2 | AC-932-6 | （frontend）登記表每一項的 `href`（字串，或函式型的各解析結果）都對應存在的 `app/**/page.tsx`；檢查函式對自造壞登記表回報 | lib/nav/registry.test.ts（it 標題 AT_932_6_2…） | 真登記表回空，壞登記表各自被指出 |
| AT-932-6-3 | AC-932-6 | （frontend）對代表路徑表，七項的 `match` 恰好命中期望的單一項或無項，互斥成立，邊界路徑不誤命中 | lib/nav/registry.test.ts（it 標題 AT_932_6_3…） | 每條路徑命中集合與期望相同 |
| AT-932-6-4 | AC-932-6 | （frontend）`ToolsRegion.tsx` 不含 `const NAV`、`activeNav`、`hrefFor` 與入口標籤字面，含自登記表的 import；檢查函式有負控 | lib/nav/registry.test.ts（it 標題 AT_932_6_4…） | 讀檔斷言全過，負控回非空 |
| AT-932-6-E-1 | AC-932-6 | （frontend）登記表檢查函式（唯一性、`mobile` 項數、路由存在、`match` 互斥）對六種自造違規各自回報恰對應的違規，真登記表回空 | lib/nav/registry.test.ts（it 標題 AT_932_6_E_1…） | 違規各自被指出，互不掩蓋 |
| AT-932-6-E-2 | AC-932-6 | （frontend）以舊 `activeNav`／`hrefFor` 的行為表對照新登記表：六項的 active 與 href 全部相同，唯一差異是未知路徑由 `projects` 改為無 active | lib/nav/registry.test.ts（it 標題 AT_932_6_E_2…） | 對照表逐項相符，差異被釘住 |
| AT-940-1-1 | AC-940-1 | （Bridge）`load_settings` 對 `SI_ROOT` 七種輸入的解析結果，拒檔案系統根，不檢查存在性，不併入 `allowed_path_roots`，既有欄位不變 | tests/test_si_cli.py::test_AT_940_1_1_* | 各輸入得 R1 規定的結果 |
| AT-940-2-E-1 | AC-940-2 | （Bridge）環境建構純函式：白名單名稱不分大小寫比對並保留原鍵與值，其餘一律丟棄，來源中的 `GIT_CONFIG_COUNT` 被固定值覆寫，缺席的白名單鍵不補空值 | tests/test_si_cli.py::test_AT_940_2_E_1_* | 輸出集合與期望相同 |
| AT-940-3-E-1 | AC-940-3 | （compose）檢查函式對九種壞變體（缺唯讀、短語法、`create_host_path` 為真、掛 repo 根、掛真 config、少 `packed-refs`、多掛一條、`SI_ROOT` 錯、A 與 B 混用）各自回報 | tests/test_si_deploy_config.py::test_AT_940_3_E_1_* | 壞變體各被指出，真檔回空 |
| AT-940-4-E-1 | AC-940-4 | （CI）涵蓋檢查函式對「缺目錄 glob、缺檔案、只有一個觸發器缺、glob 只涵蓋單層」各變體回報缺哪一項與哪一個觸發器 | tests/test_si_deploy_config.py::test_AT_940_4_E_1_* | 各變體被指出，真檔回空 |
| AT-940-5-1 | AC-940-5 | （frontend）`SI_REASONS` 與凍結 `Architecture.md` §11.1 的 SelfImproving reason 表逐字一致（比對範圍＝`reason` 以 `si_` 起頭且標 P1b 者；`invalid_request` 是 Bridge 層 reason、不進 `SI_REASONS`）；`REASONS` 不含這兩值；`reasons.ts` 的註解不再稱 `rtm_not_found` 為唯一例外；`reasons.test.ts` 的雙向鎖續綠；錯誤文案對照正確 | lib/domain/si.test.ts（it 標題 AT_940_5_1…） | 常數對拍、REASONS 乾淨、註解已改述、文案相符 |
| AT-940-6-E-1 | AC-940-6 | （frontend）`NodeEditDialog.tsx` 自 `sourceRules` import `EXECUTION_PATH_HINT`、不複製其字串；三處使用者引用同一個匯出；`EntityForms.test.tsx` 既有斷言續綠 | components/domain/import/NodeEditDialog.test.tsx（it 標題 AT_940_6_E_1…） | 讀檔斷言全過 |
| AT-940-7-E-1 | AC-940-7 | （Bridge）從閉包清單移除任一必要檔後，建構器拋出清楚的例外（含 `CLI_CLOSURE` 與缺失的檔名或 import 名稱），不退回假 CLI；完整清單時成功 | tests/test_si_export_differential.py::test_AT_940_7_E_1_* | 缺檔拋例外、完整成功 |
| AT-940-8-3 | AC-940-8 | （backend）`BridgeEndpoints.siBase()` 的解析規則與 `sddBase()` 相同（自訂 `sdd.engineUrl` 優先、否則 `ENGINE_BRIDGE_URL`、去尾斜線），每次呼叫重新解析 | BridgeHttpAdapterSiTest.AT_940_8_3_* | 三種組合結果相同 |

### 3.2 Integration Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-932-1-1 | AC-932-1 | （Bridge）狀態 A 的六個端點回應與同時刻直接跑真 `export` 的輸出逐值相等，卡面逐位元組相同，且等於 `si card` 的 stdout | tests/test_si_export_differential.py::test_AT_932_1_1_* | 六回應皆 200 且與基準逐值相等（僅 `generated_at` 可不同），卡面等於 `si card` 的輸出 |
| AT-932-1-2 | AC-932-1 | （Bridge）`since`／`limit`／`next_since`／`truncated` 對映真 CLI 的游標分頁，頁串接等於不分頁輸出 | tests/test_si_export_differential.py::test_AT_932_1_2_* | 分頁各頁與基準相等、串接不漏不重 |
| AT-932-1-3 | AC-932-1 | （backend）迷你 Bridge 回放 snake_case 黃金檔時，六個端點的 `data` 逐值等於 camelCase 黃金檔（含 `null`、`card` 字串、`generatedAt` 透傳） | SiMirrorApiIT.AT_932_1_3_* | 六回應 data 與黃金檔 JSON 樹相等 |
| AT-932-1-5 | AC-932-1 | （frontend）渲染 `SiView`：橫幅、觀察九欄、壞列、運轉與事件的文字逐欄等於 camelCase 黃金檔，且請求網址集合恰為所需 | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_5…） | DOM 文字與黃金檔逐欄相等 |
| AT-932-1-6 | AC-932-1 | （frontend）待決提案的卡面區 `textContent` 逐位元組等於 `card` 字串（含全形字元、box 字元、空行與結尾換行），`null` 卡面顯示量不到 | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_6…） | 每個 card 與 textContent 全等 |
| AT-932-1-8 | AC-932-1 | （frontend）`載入更多` 以 `since=<nextSince>` 取下一頁並合併：不漏、不重、末頁按鈕消失，重送的身分只顯示一次 | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_8…） | 合併後 12 項與黃金檔順序相同 |
| AT-932-1-E-1 | AC-932-1 | （Bridge）把倉推進到狀態 B 後，回應隨之改變、仍與真 CLI 一致，且每個請求各啟動一次子行程（無快取） | tests/test_si_export_differential.py::test_AT_932_1_E_1_* | after 與基準相等、與 before 不同 |
| AT-932-1-E-3 | AC-932-1 | （backend）未知頂層鍵、未知項內鍵、帳本不可能有的值都原樣透傳；`items` 為空仍為 200 | SiMirrorApiIT.AT_932_1_E_3_* | 透傳逐值相等，空表原樣 |
| AT-932-1-E-4 | AC-932-1 | （backend）兩次請求之間 Bridge 資料改變，回應隨之改變；`generatedAt` 是 Bridge 的值而非 backend 時鐘；每請求一次 Bridge 呼叫 | SiMirrorApiIT.AT_932_1_E_4_* | 回應 A 後 B，Bridge 請求恰兩次 |
| AT-932-1-E-5 | AC-932-1 | （frontend）含 `<script>`、`<img onerror>`、Markdown 語法、HTML 實體字樣的欄位與卡面原樣顯示為字面文字（不執行、不轉格式、不二次解碼） | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_E_5…） | 無腳本執行、無格式元素、textContent 逐字 |
| AT-932-1-E-6 | AC-932-1 | （frontend）五種篩選的選項與結果正確；壞列不受篩選影響；`buckets` 缺席時模組桶停用並說明、前端不自證據文字歸桶；有 `buckets` 時可篩 | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_E_6…） | 篩選結果與選項集合逐項相符 |
| AT-932-1-E-7 | AC-932-1 | （frontend）把替身從狀態 A 切到狀態 B 並重新整理，畫面恰多出對應項目、共同項不變，且仍逐欄等於黃金檔 B | components/domain/si/SiView.test.tsx（it 標題 AT_932_1_E_7…） | 13 項觀察、新運轉出現、共同項相等 |
| AT-932-2-2 | AC-932-2 | （Bridge）任意讀取操作序列（含併發、被擋下的請求）前後，`git status --porcelain`、HEAD、檔案雜湊表、`.git/HEAD` 與 `refs` 內容、家目錄皆逐字相同 | tests/test_si_export_differential.py::test_AT_932_2_2_* | 前後快照全等，無 pycache，無 5xx |
| AT-932-2-3 | AC-932-2 | （Bridge）六路徑乘四種非 GET 方法皆 405，未定義的 `/si/…` 路徑 404，且全部不啟動子行程 | tests/test_si_routes.py::test_AT_932_2_3_* | 24 個 405 加 4 個 404，假 CLI 無呼叫 |
| AT-932-2-4 | AC-932-2 | （backend）六路徑乘 POST／PUT／PATCH／DELETE 乘三種角色：Viewer 403、Operator 與 Admin 405、無 token 401；未定義路徑 404；全程不觸及 Bridge | SiMirrorApiIT.AT_932_2_4_* | 72 加 6 個請求各得預期狀態碼 |
| AT-932-2-6 | AC-932-2 | （frontend）完整操作序列（分頁、篩選、展開、載入更多、重新整理、錯誤重試）中，每個請求都是不帶本文的 GET；畫面沒有表單與寫入型按鈕 | components/domain/si/SiView.test.tsx（it 標題 AT_932_2_6…） | 所有 fetch 為 GET 且網址以 /api/v1/si/ 起頭 |
| AT-932-3-1 | AC-932-3 | （Bridge）`run_export` 對十數種失敗形態各拋 503 `si_unavailable`，`cause` 與 `detail` 格式符合 R4 | tests/test_si_cli.py::test_AT_932_3_1_* | 各子情境 cause 依序相符，detail 以 rc= 起頭 |
| AT-932-3-2 | AC-932-3 | （Bridge）六個端點乘六種失敗形態：503、本文鍵集合固定、`detail` 取 stderr 末 1,000 字元、不回空表、`/health` 不受影響 | tests/test_si_routes.py::test_AT_932_3_2_* | 36 個 503，本文與 detail 長度相符 |
| AT-932-3-3 | AC-932-3 | （Bridge）狀態 A 倉移除 `.git` 且子行程無家目錄時，真 CLI 對缺件回 NOT-EVALUABLE：200、`head_sha` 為 `null`、`ne` 逐欄列出、鍵集合不變 | tests/test_si_export_differential.py::test_AT_932_3_3_* | 六回應皆 200 且 NE 欄位齊全 |
| AT-932-3-5 | AC-932-3 | （backend）Bridge 的 503 `si_unavailable`、404 `si_not_found`、422、500、非 JSON 與陣列本文，各依 R8 對映為 503／404／422／502；連線被拒對映為 502、讀取逾時對映為 504；原因逐字、失敗回應無 `data` | SiMirrorApiIT.AT_932_3_5_* | 各情境狀態碼、reason、details 相符 |
| AT-932-3-6 | AC-932-3 | （frontend）後端回 503 `si_unavailable` 時，橫幅與目前分頁各自顯示錯誤態：reason、detail、cause 逐字，沒有空表或零筆字樣；重試可恢復 | components/domain/si/SiView.test.tsx（it 標題 AT_932_3_6…） | 錯誤態文字逐字，無資料殘影 |
| AT-932-3-7 | AC-932-3 | （frontend）SI 查詢 `retry` 為假、`staleTime` 與 `gcTime` 為 0：失敗只呼叫一次，卸載重掛不顯示上一次的資料 | components/domain/si/SiView.test.tsx（it 標題 AT_932_3_7…） | 失敗端點各一次呼叫，重掛先見載入中 |
| AT-932-3-E-1 | AC-932-3 | （Bridge）合法輸出不是錯誤：空 `items`、非空 `ne` 與 `problems`、stderr 雜訊、未知頂層鍵、`null` 欄位皆原樣成功回傳 | tests/test_si_cli.py::test_AT_932_3_E_1_* | 四個子情境不拋例外且逐值相等 |
| AT-932-3-E-2 | AC-932-3 | （Bridge）逾時時整棵行程樹（含孫行程）被終止、呼叫在有界時間內返回、無孤兒，且之後的正常呼叫成功 | tests/test_si_cli.py::test_AT_932_3_E_2_* | cause 為 timeout，pid 全消失 |
| AT-932-3-E-3 | AC-932-3 | （Bridge）子行程持續輸出時，超過 `SI_STDOUT_MAX_BYTES` 即終止並回 503，Bridge 不隨輸出無限吃記憶體 | tests/test_si_cli.py::test_AT_932_3_E_3_* | cause 為 stdout_too_large 且行程已終止 |
| AT-932-3-E-4 | AC-932-3 | （frontend）先成功顯示資料、重新整理失敗後，舊資料全部從 DOM 消失只剩錯誤態；改回成功並重試後內容恢復 | components/domain/si/SiView.test.tsx（it 標題 AT_932_3_E_4…） | isError 時不渲染 data |
| AT-932-3-E-5 | AC-932-3 | （frontend）`status` 失敗時橫幅顯示錯誤而非「無事件」；清單失敗時該分頁顯示錯誤而非空表；其他面板不受影響 | components/domain/si/SiView.test.tsx（it 標題 AT_932_3_E_5…） | 錯誤只限失敗面板 |
| AT-932-3-E-6 | AC-932-3 | （frontend）`NOT-EVALUABLE` 物件、`headSha` 為 `null`、`card` 為 `null`、`ne`、`unavailable` 與空事件加 carrier NE，一律以量不到加原因呈現，不顯示為 0、無、通過或正常 | components/domain/si/SiView.test.tsx（it 標題 AT_932_3_E_6…） | 各 NE 呈現且不含禁用字樣 |
| AT-932-4-1 | AC-932-4 | （backend）六個 GET：無 token 與亂碼 token 為 401（不觸及 Bridge），VIEWER／OPERATOR／ADMIN 皆 200 | SiMirrorApiIT.AT_932_4_1_* | 401 與 200 的矩陣相符 |
| AT-932-4-2 | AC-932-4 | （frontend）未登入開 `/self-improving`：導向 `/login?next=…`、`SiView` 不渲染、沒有任何 SI 請求；已登入對照組正常 | components/layout/si-login-gate.test.tsx（it 標題 AT_932_4_2…） | replace 一次，無 SI 請求 |
| AT-932-4-E-1 | AC-932-4 | （backend）三種角色對單筆提案的讀取結果一致；不存在的 id 為 404 `si_not_found`；含空白、中文、問號、井號與超長的 id 經 HTTP 送入時被編碼為單一路徑段，回應收斂為 404 或 422 | SiMirrorApiIT.AT_932_4_E_1_* | 角色一致，路徑穿越不成立，惡意 id 的回應為 404 或 422 |
| AT-932-6-5 | AC-932-6 | （frontend）以替身把登記表換成「真登記表加一列」：`ToolsRegion` 多出該入口、位置依 `order`、其餘入口不變，且元件原始碼不被修改 | components/layout/ToolsRegion.test.tsx（it 標題 AT_932_6_5…） | 多一個連結且位置正確 |
| AT-932-6-6 | AC-932-6 | （frontend）`enabled` 為假、`roles` 不含目前角色的項不渲染（不在 DOM）；符合者渲染；`roles` 缺者三種角色皆可見 | components/layout/ToolsRegion.test.tsx（it 標題 AT_932_6_6…） | 三種角色的可見集合相符 |
| AT-932-6-7 | AC-932-6 | （frontend）登記表以亂序提供時，主導覽的 DOM 順序仍依 `order` 升冪；同 `order` 者保持登記表原序 | components/layout/ToolsRegion.test.tsx（it 標題 AT_932_6_7…） | DOM 順序等於 order 排序 |
| AT-932-6-8 | AC-932-6 | （frontend）七個連結皆在 DOM（768 以上兩種形態顯示全部）；只有 `mobile` 為 `false` 的入口帶 `max-md:hidden`；`aria-label` 與 `title` 不隨 `mobile` 改變 | components/layout/ToolsRegion.test.tsx（it 標題 AT_932_6_8…） | 類別與旗標逐項對應 |
| AT-932-6-9 | AC-932-6 | （frontend）對代表路徑表，`aria-current` 恰在期望項上；未知路徑主導覽內沒有任何 `aria-current`（尤其不是專案管理） | components/layout/ToolsRegion.test.tsx（it 標題 AT_932_6_9…） | 每條路徑 active 與期望相同 |
| AT-940-2-1 | AC-940-2 | （Bridge）對五個 kind 與旗標組合，假 CLI 記錄的 argv、cwd、環境符合 R3：旗標序固定、不帶 `--repo`／`-I`／`-P`、環境只有白名單與固定鍵、哨兵機密不洩入；`si_cli` 預設常數符合 R2 | tests/test_si_cli.py::test_AT_940_2_1_* | argv、cwd、環境集合逐項相符 |
| AT-940-5-2 | AC-940-5 | （backend）`ErrorReasons` 兩常數值正確；`si_not_found` 的 404 帶 `reason` 而一般 404 不帶；`NotFoundException`、`ErrorResponseDocumentation` 與 `ErrorReasons` 三檔的 `唯一例外` 字樣已改述 | SiMirrorApiIT.AT_940_5_2_* | 常數、404 對照與文字檢查全過 |
| AT-940-6-1 | AC-940-6 | （frontend）專案節點編輯對話框的「執行路徑」欄下顯示 `EXECUTION_PATH_HINT`，輸入框以 `aria-describedby` 連到它，欄位標籤仍為精確的 `執行路徑`；目標與任務節點沒有此欄 | components/domain/import/NodeEditDialog.test.tsx（it 標題 AT_940_6_1…） | 說明存在且可及描述相符 |
| AT-940-7-1 | AC-940-7 | （Bridge）`make_si_repo` 建出的狀態 A 與 B：CLI 閉包完備、五個 kind 的真 `export` 皆 rc 0、夾具含壞列與特殊字元與非空卡面等反空轉前提，B 相對 A 恰多一筆觀察與一筆事件 | tests/test_si_export_differential.py::test_AT_940_7_1_* | 反空轉前提逐項成立 |
| AT-940-9-1 | AC-940-9 | （Bridge）未知參數、型別或範圍錯誤、不該帶參數的端點、不合格的 `{id}` 皆被擋下（422 或路徑層 404）且不啟動子行程；合法請求各啟動恰一次 | tests/test_si_routes.py::test_AT_940_9_1_* | 壞輸入全擋下，對照組成功 |
| AT-940-9-E-1 | AC-940-9 | （Bridge）合法但不存在的 id 為 404 `si_not_found`（帶 `id`）；`limit` 超過上限（CLI rc 3）與逾時為 503（帶 `cause`）；404 本文無 `cause`、503 本文無 `id`；真 CLI 對 `limit` 上限與上限加一的對照 | tests/test_si_routes.py::test_AT_940_9_E_1_* | 404、503 本文鍵集合與 cause 相符 |

### 3.3 Contract Tests（靜態與契約面檢查）

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-932-1-E-2 | AC-932-1 | （Bridge）黃金檔是真 CLI 輸出的子集（容忍根層日後加欄位），camelCase 版等於參考轉換，backend 與 frontend 的副本逐位元組相同，且黃金檔不含任何由 commit sha 衍生的值 | tests/test_si_export_differential.py::test_AT_932_1_E_2_* | 四項比對全過，漂移時指出哪一份 |
| AT-932-2-1 | AC-932-2 | （Bridge）`app/` 全樹通過 R6 的五項判準：無寫入形態、無 lib／tools import 與 sys.path 變更、字面位置、argv 動詞形態與動態對照 | tests/test_si_readonly_lock.py::test_AT_932_2_1_* | 違規清單為空 |
| AT-932-4-4 | AC-932-4 | （Bridge／compose）`docker-compose.yml` 的 engine-bridge 服務沒有 `ports` 發布，網路只有 `backend-net` 與 `db-net`；檢查函式有負控 | tests/test_si_deploy_config.py::test_AT_932_4_4_* | 無 ports，負控回非空 |
| AT-940-1-E-1 | AC-940-1 | （Bridge／文件）`engine-bridge/README.md` 與 `app/settings.py` 檔頭註解都含 `SI_ROOT`，README 含六個端點路徑與兩個 reason；檢查函式有負控 | tests/test_si_deploy_config.py::test_AT_940_1_E_1_* | 兩處文字檢查全過 |
| AT-940-3-1 | AC-940-3 | （compose）`engine-bridge` 服務設 `SI_ROOT=/repo`，SI 相關 bind 皆為長語法唯讀，整組恰符合設計 A 或設計 B 其中之一，不掛 repo 根與真 `.git/config`，既有掛載保留 | tests/test_si_deploy_config.py::test_AT_940_3_1_* | 恰符合一個具名設計 |
| AT-940-4-1 | AC-940-4 | （CI）`CLI_CLOSURE` 與 `PARAMS_SRC` 的每個輸入都被 `agentconsole-ci.yml` 的 `on.pull_request.paths` 與 `on.push.paths` 兩處涵蓋（D11 由主控代改，補上之前本 AT 為預期紅） | tests/test_si_deploy_config.py::test_AT_940_4_1_* | 兩處涵蓋全過（D11 補上後） |
| AT-940-8-1 | AC-940-8 | （backend）`/v3/api-docs` 內 `/api/v1/si/` 起頭的路徑恰六個、各只有 `get`、operationId 固定、參數型別正確 | SiMirrorApiIT.AT_940_8_1_* | 六路徑與 operationId 相符 |
| AT-940-8-2 | AC-940-8 | （frontend）`lib/api/schema.d.ts` 含六個 `/api/v1/si/` 路徑與六個 operationId、各路徑只有 `get`；`gen:api` 指令存在 | lib/api/si.endpoints.test.ts（it 標題 AT_940_8_2…） | 字串搜尋結果相符 |

### 3.4 E2E Tests

（無 AT；真後端全棧、真瀏覽器、真容器與掌舵者真機瀏覽屬 §6.2 的 V 系列，結果寫進 SCG-4 報告。）

---

## 4. 邊界與錯誤測試規格

容錯與邊界情境已併入各 AC 的 E 類 AT 與帶負控的 AT（以 `AT-<NNN>-<Y>-E-<n>` 命名，列於 §1）；本節依場景分類登記，並登記刻意不做、已知邊界與需同步的既有測試。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 非法輸入（查詢參數） | AT-940-9-1 | 未知參數、型別與範圍錯誤、不該帶參數的端點 | `since=abc`、`since=-1`、`limit=0`、`foo=1`、`/si/status?since=1` | 422 `invalid_request`，不啟動子行程 |
| 非法輸入（id） | AT-940-9-1、AT-932-3-4、AT-932-4-E-1 | 格式不合與路徑穿越形態（Bridge 層、介面卡編碼層、backend HTTP 層各自斷言） | `prop-si-004`、`PROP-SI-04`、`..`、`%2F`、空白、中文、超長 | Bridge：422 或路徑層 404；介面卡：單一路徑段編碼；backend：404 或 422，不改變 Bridge 路徑 |
| 失敗形態（子行程） | AT-932-3-1、AT-932-3-2 | 未設、缺腳本、spawn 失敗、逾時、超量、rc 非 0、垃圾、多文件、陣列、空輸出、`schema_rev`、`kind`、`items` | 十餘種子情境 | 503 `si_unavailable`＋固定 `cause`＋`rc=…; stderr=…` |
| 邊界值（stderr 尾段） | AT-932-3-2 | stderr 5000 字元 | 頭尾各有標記 | `detail` 恰取最後 1000 字元 |
| 邊界值（stdout 上限） | AT-932-3-E-3 | 無限輸出的子行程 | 上限縮小為 4096 | 即時終止、寫出量有界、`stdout_too_large` |
| 逾時 | AT-932-3-E-2 | 子行程與孫行程皆睡 30 秒 | 逾時縮小為 0.5 秒 | 整棵行程樹被終止、無孤兒 |
| 非錯誤對照 | AT-932-3-E-1 | 空 `items`、雜訊 stderr、未知頂層鍵、`null` 欄位 | 合法 export 物件 | 200 原樣（空表只在 SI 真的回空時合法） |
| 環境缺件 | AT-932-3-3 | 無 `.git`、無家目錄 | 移除 `.git`、`HOME` 指向不存在路徑 | 200、`head_sha` 為 `null`、`ne` 逐欄列出、鍵集合不變 |
| 負控（差分） | AT-932-1-E-1、AT-932-1-E-7 | 帳本推進後回應與畫面隨之改變 | 狀態 A 推進到 B | 回應與畫面多一筆觀察與一筆運轉，且仍與 CLI 一致 |
| 負控（不重算） | AT-932-1-E-3、AT-932-1-E-4 | backend 透傳未知鍵與怪值、不快取、`generatedAt` 為 Bridge 的值 | `buckets`、`console_pending`、`P9` | 原樣出現；每請求一次 Bridge 呼叫 |
| 負控（純文字） | AT-932-1-E-5、AT-932-1-E-8 | `<script>`、`<img onerror>`、Markdown、HTML 實體 | 改寫的觀察與卡面 | 字面顯示、無腳本執行、無格式元素；原始碼無渲染器 |
| 負控（過期資料） | AT-932-3-E-4、AT-932-3-7 | 成功轉失敗、卸載重掛 | 替身序列 | 不渲染舊資料；重掛先見載入中 |
| 負控（部分失敗） | AT-932-3-E-5 | 只有 `status` 或只有清單失敗 | 503 | 錯誤只限失敗面板，不顯示「無事件」或空表 |
| 邊界值（日期窗） | AT-932-1-7 | 跨年、閏年、區間寫法、無法解析 | 錨點 `2027-01-02`、`2028-03-01` | 依 R17；無法解析者不被篩除 |
| 邊界值（鍵對映） | AT-932-1-4、AT-932-1-E-2 | `a__b`、`_x`、`x_`、`sha_256`、已含大寫 | 鍵表 | 依 R9 |
| 邊界值（分頁） | AT-932-1-2、AT-932-1-8 | 末頁、重送身分 | `limit` 為 5 | 不漏不重；末頁按鈕消失 |
| 邊界值（limit 上限） | AT-940-9-E-1 | `export_limit_max` 與其加一 | 真 CLI | 200 與 503 `nonzero_rc` |
| 權限矩陣 | AT-932-2-4、AT-932-4-1、AT-932-4-E-1 | 角色乘方法乘路徑 | VIEWER／OPERATOR／ADMIN／無 token | 403、405、401、200、404 如 R7 |
| 登記表邊界 | AT-932-6-3、AT-932-6-E-1、AT-932-6-E-2 | 路徑邊界與壞登記表、舊行為相容 | `/self-improving-x`、重複 order | 互斥、各違規被指出、唯一差異被釘住 |
| 靜態鎖負控 | AT-932-2-E-1、AT-940-3-E-1、AT-940-4-E-1 | 違規樣本 | 見各 AT | 各自回非空，真檔回空 |
| 夾具負控 | AT-940-7-E-1 | 閉包缺檔 | 移除 `platform_utils.py` | 大聲失敗、不退回假 CLI |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| 寫入端點與決定載體（`POST /si/**`、`si_console_writes`） | 屬 P2b（鍵 `agentconsole-si-decide`），依賴根層 P2 動詞；P1b 零寫入是 AC-932-2 的前提 | 掌舵者要求在 Console 內決定提案或新增觀察 |
| 在 backend 或 frontend 重算判準（折疊、digest、NE、歸桶） | AC-932-1 禁止；差分只證明頁面＝`export` 輸出 | 差分出現歧異（附 `kind` 與欄位座標） |
| HTTP 層 `Cache-Control` | PRD 未要求；無快取靠不快取的實作（Bridge 無快取、backend 無快取、前端 `gcTime` 與 `staleTime` 為 0），且既有 nginx 設定已有單一 `Cache-Control` 的鎖 | 掌舵者回報畫面資料過期而查得是 HTTP 層快取（附回應標頭） |
| 前端自行歸模組桶 | 違反「不重算判準」；欄位缺席時降級（R17） | 根層 P2 長期未交付 `buckets[]` 而掌舵者仍要求桶篩選 |
| 時區換算與小時級時間窗 | 觀察時間欄無 offset、檔頭 `tz=` 不在 `export` 內（§7.1 ⚖ 9） | 時間窗的 ±1 日邊界造成篩選結果被回報錯誤（附列座標） |
| Bridge 認證 | Bridge 只准 backend-net（Architecture §12.1 L-6）；以 compose 靜態檢查補機械物（無 `ports` 發布） | L-6 被實際違反（Bridge 埠出現在 host） |
| 列表虛擬捲動 | 單頁預設 100 筆、分頁載入；Rule 2 | 掌舵者回報載入多頁後互動遲滯（附筆數與瀏覽器） |
| 以自動化截圖充當 P1b 出口 (e) | PRD §8.1 明文：構造情境或自動化截圖不能充當 | — |
| 驗證 `export` 的折疊與卡面正確性 | 屬根層 P1 TCS（`status`、`card`、`check` 的測試）；差分只證明頁面＝`export` 輸出 | 根層 `export` 與 `status` 對同一帳本給出矛盾答案 |

**已知邊界（誠實登記）**

1. **AST 鎖是形態判準**：`getattr`、動態拼接、`importlib` 以變數載入看不到（R6）；唯讀的「行為面」另由 AC-932-2 的 AT（操作序列前後零變動）覆蓋，但只涵蓋測試所用的操作序列。
2. **差分只證明頁面＝`export` 輸出**，不證明 `export` 的折疊邏輯正確（PRD AC-SI-32-1 誠實劃界）；「同一時刻」在實務上是兩次相鄰的呼叫，帳本在兩次之間被另一視窗改動的短暫不一致不在偵測範圍，回應帶 `headSha` 與 `generatedAt` 供人對照（PRD AC-SI-32-3 誠實劃界）。
3. **黃金檔是子集比較**：容忍根層日後加欄位（`buckets[]`、`console_pending[]` 等，使跨鍵變動不致誤紅），但偵測不到「鍵不變、語意改變」的根層變動——那一類由 `schema_rev` 與根層 TCS 承擔（§7.1 ⚖ 30）。
4. **容器掛載有兩個未實測風險**：單檔 bind（`HEAD`、`packed-refs`）在 git 以 lock 加 rename 換檔後，容器可能保留舊 inode 使 `head_sha` 靜默過期；`packed-refs` 於主機不存在時 `create_host_path: false` 使容器起不來。AT 只做靜態檢查並接受設計 A 或 B；真容器行為由 V3 決定採哪一個（Architecture §12.1 L-14、§12.2 V-12 未實測）。
5. **`safe.directory` 的環境變數式放行與 git ≥2.31** 未在真容器驗證（V3）；Windows 本機直跑與 macOS 不涉及。
6. **jsdom 不評估 CSS**：`max-md:hidden` 類別存在不等於 <768 時真的隱藏；真視窗行為由 V2 的 Playwright 視窗實測承擔。
7. **`limit` 超過 `export_limit_max` 時回 503**（CLI rc 3 依 R4 對映）：語意上是使用者輸入錯誤而被標為「SI 不可用」，是 PRD「rc 非 0 即 503」字面的後果；前端永不送超限值（§7.1 ⚖ 6）。
8. **行為變更（PRD AC-SI-32-6 (f) 明定）**：未知路徑不再亮「專案管理」；`/projects/…` 仍是專案管理 active（AT-932-6-E-2 釘住）。
9. **前端時間窗以日曆日字串比對、不換算時區**：容器內 `generatedAt` 多為 UTC 而帳本為 +08:00，窗邊界可能差一日（§7.1 ⚖ 9）。
10. **macOS 全部未驗**（NFR-SI-06-5）：本檔的 AT 與 V 系列只在 Windows 與 Linux（CI）實跑。
11. **迷你 Bridge 的 SI 夾具與真 Bridge 的錯誤本文同形**只由介面卡單測（AT-932-3-4）與差分間接保證（形態判準）；真 Bridge 對真 backend 的整合由 V1 承擔。

**需同步的既有測試**（新增的六個 SI 端點與第七個導覽項會讓下列既有測試的精確釘選變紅；開發 agent 須同步修改，且**只增不減**〔NFR-P1b-7〕；這些檔已列入 §5.6 與 D5、D7）：

1. `AgentConsole/frontend/components/layout/layout.test.tsx`：導覽斷言（第 132 至 140 行的六標籤斷言）改由登記表驅動（R22）；專案頁斷言（第 239 至 247 行）保留。實查 `AgentConsole/frontend/tests/e2e` 與 `engine-bridge/tests`、`backend/src/test`：沒有其他測試斷言導覽恰為六項或依賴「未知路徑 fallback 成專案管理」（e2e 以連結名稱查詢，第七項不影響）。
2. `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/config/OpenApiIT.java`（OpenAPI 端點清單必須恰好等於已交付範圍）：`EXPECTED` 加六筆——`/api/v1/si/status`、`/api/v1/si/observations`、`/api/v1/si/events`、`/api/v1/si/proposals`、`/api/v1/si/proposals/{id}`、`/api/v1/si/runs`，皆為 `List.of("get")`；路徑數的釘選（現為第 113 行）`hasSize(61)` 改為 `hasSize(67)`；操作總數的釘選（現為第 121 行）`isEqualTo(70)` 改為 `isEqualTo(76)`；類別 Javadoc 補一句「P1b 再加六個 SI GET（路徑 61→67、操作 70→76）」。
3. `AgentConsole/frontend/lib/api/endpoints.test.ts`（每個後端端點一個函式；現為第 147 至 152 行）：`EXPECTED` 加六列 `getSi*`（方法 `GET`，網址同 R11 與 AT-932-2-7 的六個：`/api/v1/si/status`、`/api/v1/si/observations?since=7&limit=100`、`/api/v1/si/events?limit=100`、`/api/v1/si/proposals`、`/api/v1/si/proposals/PROP-SI-004`、`/api/v1/si/runs?since=3`）；測試標題的數量與 `toHaveLength(68)` 改為 74（標題補一句「再加 P1b 的六個 `getSi*`」）。
4. 不需改、但對新檔自動生效：`reasons.test.ts` 不需改（SI 常數不進 `REASONS`，R19），`lib/api/reasons.ts` 只改 `RTM_NOT_FOUND` 的一則註解（R26）；`test_sdd_integration_parity.py` 不需改（SI 鎖是新檔，不改既有鎖）；`AgentConsole/frontend/tests/design-rules.test.ts` 掃描 `app`、`components`、`lib`、`hooks` 的全部自家原始碼（無陰影與漸層、無寫死色碼、只用 Lucide 且無 emoji、無 `outline-none`、無 `dark:`），新檔必須通過。

漏改第 2、3 項者，V7 的全套測試會紅；它們與 NFR-P1b-7 的零退化是同一條約束（只增不減，不得為了讓測試變綠而改弱既有斷言）。

---

## 5. 測試資料規格

### 5.1 夾具倉、狀態 A 與 B、黃金檔（Bridge 側；`AgentConsole/engine-bridge/tests/`）

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| `CLI_CLOSURE`、`PARAMS_SRC` | 常數（`si_repo_support.py`） | `CLI_CLOSURE`＝`tools/selfimproving.py`、`tools/_stdio_utf8.py`、`tools/lib/platform_utils.py`、`tools/lib/selfimproving/`（現查：`export` 的 import 閉包，SA 以真 CLI 在複本倉實跑五個 kind 皆 rc 0、無 `__pycache__` 產生、家目錄無新增檔）；`PARAMS_SRC`＝`docs/06_quality/SelfImproving_Protocol/params.json`（建倉時自真 repo 複製，使 `params.json` 的結構演進會讓 Bridge 測試誠實變紅；§7.1 ⚖ 15、⚖ 16） | R24、R25 |
| 夾具帳本 | 凍結複本（入庫） | `tests/fixtures/si_repo/docs/06_quality/SelfImproving_Observation_Ledger.md`：檔頭與表頭逐字取自真帳本（含 `<!-- si-ledger: tz=+08:00 -->`），12 列資料：`OBS-SI-001`～`OBS-SI-004` 為真帳本前四列的逐字複本（含反引號、`orig=` 的雙引號、全形字元）；`OBS-SI-005` 的 `symptom` 含 `<script>window.__si_xss=1</script>`；`OBS-SI-006` 含 Markdown 粗體、連結語法、行內程式碼與 `&lt;b&gt;` 字樣；`OBS-SI-007` 為外部衍生列（`回報者=研究者`、`外部衍生=是`、`src=anthropic-engineering`）；`OBS-SI-008` 嚴重度 `P1`、分類 `decision`；`OBS-SI-009` 的 `marks` 含 `carrier=console;audit_ref=<UUID>`、`evidence` 含 `AutoClaude/` 路徑（供模組桶不重算的負控）；`OBS-SI-010` 處置為 `deferred；再開症狀：…`；`OBS-SI-011` 處置為 `merged@OBS-SI-001`；`OBS-SI-012` 為欄數不足的壞列（8 欄）。各列 ≤700 bytes；日期橫跨至少三個不同日，且至少一列的日期等於黃金檔錨點日 `2026-10-21`（使 `今天` 窗非空）、至少兩列早於錨點日 7 天以上（使 `近 7 天` 與 `近 30 天` 有區別）；ID 只用真帳本已存在者（根層 `git grep` 的編號完整性鎖）；**不得含 `DEF-101-`／`DEF-200-` 編號** | R25 |
| 夾具事件與提案 | 凍結複本（入庫） | `SelfImproving_Event_Ledger.jsonl`＝真事件帳本現有 6 行的逐位元組複本；`SelfImproving_Proposals/PROP-SI-004/r1.md` 與 `r1.patch`＝真檔逐位元組複本（M 類提案，卡面不需 git 歷史；SA 實跑確認 `card` 為字串、以換行結尾、`state` 為 `proposed`） | R25 |
| 狀態 A | 動態生成（`make_si_repo(tmp_path, "A")`） | 複製閉包、夾具、真 `params.json` 進 tmp 倉；`git init` 後以固定作者（`si-fixture`、`si-fixture@example.invalid`）、固定日期（`GIT_AUTHOR_DATE` 與 `GIT_COMMITTER_DATE` 為 `2026-10-21T00:00:00+08:00`）、`-c core.autocrlf=false -c commit.gpgsign=false` 提交一次；建倉所得的 HEAD（40 碼小寫 hex）隨複製進倉的閉包與夾具內容而變（樹內容進雜湊：閉包檔日後任何一行改動都會改變它），所以**不被當作常數斷言，也不得寫進黃金檔** | AT-932-1 系列、AT-940-7 |
| 狀態 B | 動態生成（`make_si_repo(tmp_path, "B")` 或對 A 的倉推進） | 在 A 之上追加一列 `OBS-SI-013`（一般 bug、`P3`、`open`）與一行事件 `seq` 為 7 的 `run.open`（`RUN-SI-002`、`trigger` 為 `a`、`coords` 一筆、`head_sha` 為**固定字面** `73ff8e3cdefeb993f9d4213ef88e3c184055a60a`，不取自建倉所得的 HEAD；`runs` 中 `RUN-SI-002` 的 `head_sha` 由該事件帶出、同為此字面），再以日期 `2026-10-21T00:10:00+08:00` 提交；`export` 對 B 的輸出相對 A：`observations` 多一筆、`events` 多一筆、`runs` 多一筆（`closed_seq` 為 `null`）、`status.open_runs` 含 `RUN-SI-002`、`head_sha` 不同 | AT-932-1-E-1、AT-932-1-E-7 |
| 黃金檔 | 入庫（`tests/fixtures/si_golden/{A,B}.snake.json` 與 `{A,B}.camel.json`） | 每個檔含鍵 `observations`、`events`、`proposals`、`proposal_one`（單筆 `PROP-SI-004`）、`runs`、`status`，值為該端點的完整回應物件；snake 版為真 CLI 輸出（各回應頂層的 `generated_at` 置占位 `2026-10-21T00:00:00+08:00`、頂層 `head_sha` 置 40 個 `0`；其餘鍵值一律保留真輸出）；**黃金檔不得含任何由 commit sha 衍生的值**——建倉所得的 HEAD 一律不進黃金檔，事件與運轉內的 `head_sha` 皆為夾具寫死的固定字面（狀態 A 的六行事件是真事件帳本的逐位元組複本，其 `head_sha` 本就固定；狀態 B 的 seq 7 事件用上列固定字面），AT-932-1-E-2 以「雙方全部深度的 `head_sha` 值占位化後比對」加「黃金檔文字不含建倉 HEAD」兩道釘住；camel 版為 R9 轉換；B 版只需涵蓋會變的 kind（`observations`、`events`、`runs`、`status`）加不變的 `proposals`。backend 副本在 `backend/src/test/resources/si/`、frontend 副本在 `frontend/tests/fixtures/si/`（檔名同）。重產指令：`python tests/si_golden_regen.py`（Bridge 側的測試支援腳本，列印差異並寫四個黃金檔與兩份副本；不是測試） | AT-932-1-E-2 |

### 5.2 假 CLI 樹（`tests/fake_si.py`）

`make_fake_si(tmp_path) -> Path`：在 `<R>/tools/selfimproving.py` 放一支只用標準庫的替身腳本；每次呼叫把 `argv`（`sys.argv[1:]`）、`cwd`、`sys.executable`、`sys.flags.safe_path`、`pid` 與**全部環境變數的名稱與值**追加進 `<R>/fake_calls.jsonl`（`read_calls(R)` 取回）。`set_control(R, **旋鈕)` 寫 `<R>/fake_control.json`：`rc`（離開碼）、`stderr`（要寫的文字）、`sleep`（秒）、`raw_stdout`（原樣輸出的字串）、`huge`（持續寫出無換行資料並把累計位元組數寫進 `<R>/fake_written.txt`）、`grandchild`（啟動一個睡 30 秒的孫行程並把兩個 pid 寫進檔案）、`export`（要輸出的物件；預設為對請求 kind 合法的最小 export 物件，`schema_rev` 為 1、`items` 為空）、`schema_rev`、`kind`、`items`、`by_id`（`--id` 對輸出的對映）。替身腳本本身不是測試（檔名不以 `test_` 起頭）。

### 5.3 迷你 Bridge 的 SI 夾具（backend 測試支援；`com.aisdlc.minibridge`）

`MiniBridge` 新增 `public final Si si`，`MiniBridgeController` 新增六個 `GET /si/**` 處理方法（形態仿其既有 `/sdd/*`）：`si.payloads`（`observations`、`events`、`proposals`、`runs`、`status`、`proposal:<id>` 到回應物件的對映，預設為 `src/test/resources/si/A.snake.json` 的內容）、`si.unavailable`（`cause` 與 `detail`，非空時回 503 `si_unavailable`）、`si.notFoundIds`（對這些 id 回 404 `si_not_found` 並帶 `id`）、`si.invalid`（回 422 `invalid_request` 並帶 `violations`）、`si.status500`、`si.garbage`（回 200 但本文為這個字串）、`si.arrayBody`（回 200 但本文為 JSON 陣列）、`si.delayMillis`（先睡再回；AT-932-3-5 以大於讀取逾時 20 秒的值造 504）、`si.seen`（每個請求的**原始 URI** 與查詢字串，供 id 編碼與參數轉發的斷言）；`MINI.requests()` 照既有體例記 `GET /si/<路徑>`；`reset()` 回到預設（回放狀態 A）。

### 5.4 frontend 夾具與輔助

`tests/fixtures/si/{A,B}.camel.json`（黃金檔副本）；`tests/helpers/si.tsx`（測試輔助，沿 `tests/helpers/api.tsx`／`sddFixtures.ts` 先例：不被 vitest 收集、不在 `design-rules` 掃描面）：`renderSi({ role, fixture, overrides })` 以真 `Providers`（含 `AuthProvider`、預設 `QueryClient`）渲染 `SiView`，以 `saveSession` 設定角色，以 `vi.stubGlobal("fetch", …)` 依網址回放黃金檔（`since`／`limit` 語意與 CLI 相同：`since` 為嚴格大於的 ID 數字游標），可逐端點覆寫為錯誤或改寫資料，並記錄每次呼叫的方法與網址；`GA`／`GB` 為兩份黃金檔的載入結果。

### 5.5 hermetic 環境

全部 AT 只用 tmp 目錄內的合成倉與假 CLI、loopback 上的 uvicorn、Testcontainers 內的 PG、`MockRestServiceServer`、jsdom 與 `fetch` 替身；不連外網、不寫真帳本、不寫真事件帳本、不寫真 `SelfImproving_Proposals/`；唯讀存取 monorepo 內的 CLI 閉包、`params.json`、`.github/workflows/agentconsole-ci.yml`、`AgentConsole/docker-compose.yml`、`Architecture.md`；子行程的 `HOME`／`USERPROFILE` 一律指向 tmp 內的目錄（或不存在的路徑）。測試結束必關活 Bridge 與回收子行程。

### 5.6 允許變更的檔案集合（開發 agent；與 D1～D10 逐項一致）

| 區 | 允許新增或修改的路徑（相對 monorepo 根） |
|----|------------------------------------------|
| Bridge | `AgentConsole/engine-bridge/app/si_cli.py`、`app/routers/si.py`、`app/settings.py`、`app/main.py`、`README.md`；`tests/test_si_cli.py`、`test_si_routes.py`、`test_si_export_differential.py`、`test_si_readonly_lock.py`、`test_si_deploy_config.py`、`fake_si.py`、`si_repo_support.py`、`si_golden_regen.py`；`tests/fixtures/si_repo/**`、`tests/fixtures/si_golden/**` |
| backend | `AgentConsole/backend/src/main/java/com/aisdlc/console/` 下依 PRD §9.1〈C18 檔名表〉backend 列與本檔 D4 的新增與修改檔（含 `SiKeyNames`；`NotFoundException` 的 Javadoc、`ErrorResponseDocumentation` 的註解與說明字串、`ErrorReasons` 的 `RTM_NOT_FOUND` Javadoc 中的字樣改述，R26）；`backend/src/test/java/com/aisdlc/` 下的 `SiMirrorApiIT`、`SiKeyNamesTest`、`BridgeHttpAdapterSiTest`、`SiReadOnlyArchTest`、`MiniBridge`／`MiniBridgeController` 的 SI 擴充、既有 `OpenApiIT` 的 `EXPECTED` 與數量釘選（61→67、70→76，只增不減，§4）（另可加不使 AT 失效的補充單元測試，供 JaCoCo）；`backend/src/test/resources/si/**` |
| frontend | `AgentConsole/frontend/app/self-improving/page.tsx`；`components/domain/si/**`；`lib/api/endpoints.ts`、`queries.ts`、`types.ts`、`schema.d.ts`、`si.endpoints.test.ts`、既有 `endpoints.test.ts` 的 `EXPECTED` 與數量釘選（68→74，只增不減，§4）；`lib/api/reasons.ts`（**只改** `RTM_NOT_FOUND` 的註解，不動任何常數，R26）；`lib/domain/si.ts`、`si.test.ts`；`lib/nav/registry.ts`、`registry.test.ts`；`components/layout/ToolsRegion.tsx`、`ToolsRegion.test.tsx`、`layout.test.tsx`、`si-login-gate.test.tsx`；`components/domain/import/NodeEditDialog.tsx`、`NodeEditDialog.test.tsx`；`tests/fixtures/si/**` |
| 部署 | `AgentConsole/docker-compose.yml`；（設計 B 時）`AgentConsole/docker/si/git-config.empty` |
| 不屬開發 agent（主控代做） | `.github/workflows/agentconsole-ci.yml`；`AgentConsole/docs/**`——含契約後繼檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`（**新檔**，D12 (a)；開發 agent 在 IMPLEMENTATION 態寫不進 `docs/02_architecture/`，由主控落檔、與實作同一個 commit，開發 agent 於交卷以純文字附全文草稿，R26）、RTM 子表、SCG-4 報告；根層 RTM 的 FR-SI-32 列；RELEASE 之後才做的 `Architecture.md` 修訂（凍結檔）；其餘一律不動（R29） |

---

## 6. RTM 連結確認

### 6.1 追溯

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| PRD FR-SI-32 的 AC-SI-32-1、32-2、32-3、32-4、32-6 → F-901 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-901 → US-901～US-907 | ☑ 已映射 |
| US-901～US-907 → 本檔 14 個 AC（PRD 的 5 個加本檔自增 9 個） | ☑ 已映射（FRD-lite） |
| PRD 的 5 個 P1b AC → 本檔 `AC-932-1`、`AC-932-2`、`AC-932-3`、`AC-932-4`、`AC-932-6` | ☑ 已映射（編號規則見 FRD-lite 與 §7.1 ⚖ 1） |
| 14 個 AC → 本檔全部 AT（§1；數量見覆蓋率統計） | ☑ 已映射（本文件 §1） |
| PRD §8.1 P1b 出口 (a) 差分、(b) 唯讀、(c) fail-loud、(d) 需登入、(f) 導覽登記表化 → 對應 AC 的 AT | ☑ 已映射；出口 (e) 真機瀏覽由 V5 承擔（不由 AT 充當） |
| OBS-SI-230（順帶項）→ AC-940-6 | ☑ 已映射 |
| OBS-SI-202（FsmTrail 升格）→ V6（非 AC） | ☑ 已登記（R28；QA 交文字證據、主控改 RTM） |
| PRD §9.1 C18 的「契約新版」（`API_Contract_P3-6.md` 後繼）→ D12 (a) 的契約後繼檔 `API_Contract_SelfImproving_P1b.md` | ☑ 已映射（R26；主控於 SCG-5 落檔、與實作同一個 commit，開發 agent 交卷附全文草稿；存在性與內容範圍由 V8 核對；§7.1 ⚖ 12） |
| PRD 指定的 FR-SI 追溯主載體＝根層 RTM → 根層 RTM 的 FR-SI-32 列 | ☑ 已登記（D12 (c)、R26；由主控於 SCG-5 填，檔名依 Root_Layout SSOT §2） |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由雲端 agentconsole-ci 的三個 job 一併執行；`paths` 連動見 AC-940-4） |

**行為規則 → AT 對映**（各 R 至少被一個 AT 釘住；R26、R28、R29 為文件與流程規則，由 §6.2 與 SCG-5 核對表承擔）

| 規則 | 內容 | 釘住它的 AT |
|------|------|-------------|
| R1 | `SI_ROOT` 設定 | AT-940-1-1、AT-940-1-E-1 |
| R2 | `si_cli.py` 常數與入口 | AT-932-1-2、AT-932-3-1、AT-940-2-1 |
| R3 | 子行程 argv、cwd、環境 | AT-932-1-2、AT-932-2-2、AT-932-3-E-2、AT-932-3-E-3、AT-940-2-1、AT-940-2-E-1 |
| R4 | 失敗判定與 `detail` | AT-932-3-1、AT-932-3-2、AT-932-3-3、AT-932-3-E-1、AT-932-3-E-2、AT-932-3-E-3、AT-940-9-E-1 |
| R5 | Bridge 路由與輸入驗證 | AT-932-1-1、AT-932-1-2、AT-932-1-E-1、AT-932-2-2、AT-932-2-3、AT-932-3-2、AT-940-9-1、AT-940-9-E-1 |
| R6 | 唯讀不變量與 AST 鎖 | AT-932-1-1、AT-932-1-E-1、AT-932-2-1、AT-932-2-E-1 |
| R7 | backend 端點、參數與權限 | AT-932-1-3、AT-932-2-4、AT-932-2-5、AT-932-3-4、AT-932-4-1、AT-932-4-E-1 |
| R8 | backend 失敗對映 | AT-932-1-3、AT-932-3-4、AT-932-3-5、AT-932-4-E-1、AT-940-5-2 |
| R9 | 欄名對映與透傳 | AT-932-1-1、AT-932-1-3、AT-932-1-4、AT-932-1-E-2、AT-932-1-E-3、AT-932-1-E-4 |
| R10 | 契約面 | AT-932-2-5、AT-932-3-4、AT-940-5-2、AT-940-8-1、AT-940-8-3 |
| R11 | frontend API 層 | AT-932-2-6、AT-932-2-7、AT-932-2-8、AT-932-3-7、AT-932-4-3、AT-940-8-2 |
| R12 | 頁面骨架與三態 | AT-932-1-5、AT-932-1-E-7、AT-932-2-6、AT-932-3-6、AT-932-3-7、AT-932-3-E-4、AT-932-3-E-5、AT-932-4-2 |
| R13 | 狀態橫幅 | AT-932-1-5、AT-932-3-E-5、AT-932-3-E-6 |
| R14 | 三分頁與詳情 | AT-932-1-5、AT-932-1-6、AT-932-1-E-7 |
| R15 | 分頁與游標 | AT-932-1-7、AT-932-1-8 |
| R16 | NE 與量不到的呈現 | AT-932-3-3、AT-932-3-E-6 |
| R17 | 篩選 | AT-932-1-7、AT-932-1-E-6 |
| R18 | 純文字渲染 | AT-932-1-E-5、AT-932-1-E-8、AT-932-2-8 |
| R19 | reason 常數與錯誤顯示 | AT-932-3-6、AT-940-5-1 |
| R20 | 導覽登記表 | AT-932-6-1、AT-932-6-2、AT-932-6-3、AT-932-6-E-1、AT-932-6-E-2 |
| R21 | 純函式與消費規則 | AT-932-6-3、AT-932-6-4、AT-932-6-5、AT-932-6-6、AT-932-6-7、AT-932-6-8、AT-932-6-9、AT-932-6-E-1、AT-932-6-E-2 |
| R22 | `layout.test.tsx` 由登記表驅動 | AT-932-6-E-2 |
| R23 | compose | AT-932-4-4、AT-940-3-1、AT-940-3-E-1 |
| R24 | CI `paths` | AT-940-4-1、AT-940-4-E-1 |
| R25 | 夾具與真 CLI 閉包 | AT-932-1-E-2、AT-940-7-1、AT-940-7-E-1 |
| R26 | 文件與帳本連動（實作同 commit／SCG-5／RELEASE 後） | （文件／流程規則，見 §6.2 與 SCG-5 核對表） |
| R27 | `NodeEditDialog.tsx` 說明 | AT-940-6-1、AT-940-6-E-1 |
| R28 | RTM FsmTrail 升格（V6） | （文件／流程規則，見 §6.2 與 SCG-5 核對表） |
| R29 | 範圍 | （文件／流程規則，見 §6.2 與 SCG-5 核對表） |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註）

| 編號 | 實查項 | 步驟與指令要點 | 通過判準與證據 | 再開症狀 |
|------|--------|----------------|----------------|----------|
| V1 | 全棧 API 差分（真 PG、真 backend、真 Bridge、真 CLI） | 沿 `frontend/tests/e2e/README.md` 的真後端前置起全棧，Bridge 的 `SI_ROOT` 指向以 `make_si_repo` 建出的 tmp 倉（狀態 A）；以 admin 與 viewer 登入取 JWT；對六個 `GET /api/v1/si/**` 各請求，並對該倉直接跑真 `export` 以 R9 參考轉換比對；推進到狀態 B 再比一次；另測 Bridge 停止與 `SI_ROOT` 指向空目錄 | 六端點 `data` 與 `camel(export)` 逐值相等（`generatedAt` 除外）；A 到 B 隨之改變；Bridge 停止時 502；空目錄時 503 且 `details.cause` 為 `si_script_missing`；證據＝命令輸出與差異報告 | 差分出現歧異（附 kind 與欄位座標） |
| V2 | 真瀏覽器 DOM 差分與響應式（Playwright 真後端版 `tests/e2e/p11-si-mirror.spec.ts`） | 設 `E2E_ROOT` 起全棧（standalone 建置）；視窗 1440、1024、375 各跑一輪；每個 spec 以 `--output` 指向自己的暫存目錄 | DOM 與真 `export` 逐欄相同（12 筆觀察的九欄、提案卡面 `textContent`）；≥768 七個導覽項全可見、<768 只有六個可見且 `自我進化` 不可見；直接輸入 `/self-improving` 網址可進入；未登入導向登入；移除 `SI_ROOT` 重啟 Bridge 後錯誤態顯示 `si_unavailable` 與 detail、不顯示空表；跑完 `git status --porcelain` 確認沒有已追蹤截圖被改動 | `max-md:hidden` 與實際視窗行為不符 |
| V3 | 真容器：掛載設計、`safe.directory`、唯讀、無 config | `docker compose --profile db --profile app up -d --build` 後於 engine-bridge 容器內驗：(1) 帶三個 `GIT_CONFIG_*` 環境變數時 `git -C /repo rev-parse HEAD` 等於主機 HEAD；(2) 經 backend 的 `GET /api/v1/si/status` 之 `headSha` 為非 `null` 且等於主機 HEAD；(3) 主機端 `git commit --allow-empty` 後再查，`headSha` 隨之更新（單檔 bind 的 inode 過期測試）；(4) 於容器內嘗試寫入 `/repo/docs/06_quality` 與 `/repo/tools` 失敗（唯讀）；(5) `/repo/.git/config` 在設計 A 不存在、在設計 B 為空檔；(6) `docker compose config` 顯示 engine-bridge 無 `ports` | 設計 A 全過則採 A；(3) 失敗或 `packed-refs` 缺檔使容器起不來則改採 B 並再驗；兩者皆失敗登缺陷並回報掌舵者；結論寫進 SCG-4 報告，並於 RELEASE 之後的純文件 commit 回寫 Architecture §12.1 L-14 與 §12.2 V-12（凍結檔，R26）；證據＝指令輸出 | `headSha` 為 `null` 且 `ne` 含 `git`（附 stderr 的 `dubious ownership` 字樣）；或 `headSha` 與主機 HEAD 不符 |
| V4 | `export --kind status` 冷啟動量測（ADR-SI-12 要求） | 本機直接執行與經 Bridge 的 `/si/status` 各三次、容器內經 Bridge 三次，取中位數 | 記錄三個中位數（QA 以文字回報，由主控於本檔〈勘誤〉節記錄這三個數字與量測環境）；任一超過 7.5 秒（`SI_CLI_TIMEOUT_SECONDS` 的一半）即再開 ADR-SI-12 的症狀並回報；結果寫入 SCG-4 報告，並於 RELEASE 之後的純文件 commit 回寫 Architecture §12.2 V-12 結論列 | 單次 `export` 逼近 15 秒逾時 |
| V5 | **掌舵者真機瀏覽 `/self-improving`**（PRD §8.1 P1b 出口 (e)） | 掌舵者在真機（真 repo、真帳本）開 `/self-improving`，看狀態橫幅、三分頁、待決提案卡面，並回報 | 掌舵者回覆（附 sid 與 line）；構造情境、自動化截圖與 AT 不能充當 | 掌舵者回報畫面與 `si card` 輸出不一致或出現空表 |
| V6 | RTM FsmTrail 區塊升格（OBS-SI-202；R28） | QA 以 Console 真後端 E2E 驗「委派失敗的 FSM 狀態檔→監控頁最近決策顯示 `AUTOCLAUDE_DELEGATED → ESCALATION`」（種一份 `trigger` 為 `autoclaude_delegated_exit` 的 FSM 檔與符合的 provenance；可擴充既有 `p9-w7-sdd.spec.ts` 或新檔） | QA 以文字證據交卷（指令輸出與 E2E 座標；QA 全程唯讀、不改 RTM）；通過者：**主控依該證據**把 RTM 的 FsmTrail 子表 14 列改為「✅ 已驗證」並附 E2E 座標；未通過或未做：主控保留現狀並寫一句再開症狀 | 監控頁顯示 `ESCALATION → ESCALATION` |
| V7 | 閘門全綠（各服務） | Bridge：`ruff check`（`AgentConsole/engine-bridge` 與 monorepo 根視角各一次）、全套 pytest、`GET /health`、根層 `tools/tests` 的 `TestDirEntryPrimitivesAreAccountedFor`；backend：`gradlew clean build`（Checkstyle、JaCoCo 80%、ArchUnit）；frontend：`npm run lint`、`npx tsc --noEmit`、`npm run build`、`npx vitest run`（覆蓋率 70%）、四區塊 grep 無輸出、`grep 'const NAV'` 無輸出、`layout.test.tsx` 不含寫死的六標籤陣列（以 `Select-String` 找同一個陣列字面內同時含 `執行中心` 與 `監控中心`，期望無輸出）、`npm run gen:api` 後 `schema.d.ts` 無差異；根層：`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`、`python tools/selfimproving.py check` 的 rc 不變；Playwright route mock spec（`mock.spec`）全綠 | 各指令 rc 為 0（讀 rc 先存變數再讀）；輸出逐字貼入 SCG-4 報告 | 任一閘門紅 |
| V8 | 範圍守衛與契約後繼檔存在性 | (1) `git diff --name-only` 與 `git status --porcelain`（含未追蹤檔）對照 §5.6；(2) 核對契約後繼檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md` 存在，內含六個 backend GET 與六個 Bridge GET 的路徑、查詢參數（`since`、`limit`、`{id}` 規則）、狀態碼與 `reason` 對映表（200、401、403、404、405、422、502、503、504），其路徑集合與 springdoc `/v3/api-docs` 的六個 `/api/v1/si/…` 路徑一致，並載明 `si_not_found` 是「404 的 reason 省略」慣例的第二個例外 | (1) 只出現允許集合；零根層 `tools/`、`.claude/`、`.github/`（D11 除外且由主控）、凍結檔、既有 TCS；主控落檔的契約後繼檔（D12 (a)）不屬開發 agent 的變更、不計入違規；(2) 該檔存在且內容範圍相符（缺檔或缺列即紅） | 出現允許集合外的檔；或契約後繼檔缺檔、缺端點列、缺 `reason` 表 |
| V9 | 雲端 CI | push 後 `agentconsole-ci` 的 engine-bridge、backend、frontend 三個 job 皆綠；差分測試的根層輸入變動會觸發該 workflow（AC-940-4 的實際效果） | `gh run list` 現查的 run 與結論 | 雲端紅而本機綠（平台差異） |
| V10 | 平台 | Windows 實跑全部 AT 與 V1～V4；macOS 於 SCG-4 報告標「未驗」（NFR-SI-06-5）；Linux 由 CI 承擔 | 報告載明各平台狀態 | Windows 與 CI 結果不一致 |

V3 與 V4 的關鍵指令（bash 與 PowerShell 同形；容器內只有 Linux）：

```bash
(cd AgentConsole && docker compose exec -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo engine-bridge git -C /repo rev-parse HEAD)
(cd AgentConsole && docker compose exec engine-bridge sh -c 'touch /repo/docs/06_quality/x 2>&1; ls -la /repo/.git/config 2>&1')
```

```powershell
Push-Location AgentConsole; docker compose exec -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo engine-bridge git -C /repo rev-parse HEAD; Pop-Location
Push-Location AgentConsole; docker compose exec engine-bridge sh -c 'touch /repo/docs/06_quality/x 2>&1; ls -la /repo/.git/config 2>&1'; Pop-Location
```

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 開放問題與預設（⚖ 1～⚖ 30）

| 編號 | 問題（上位文件內部矛盾、未定或不可測處） | 本檔已採用的預設 | 替代與再開症狀 |
|------|----------------------------------------|------------------|----------------|
| ⚖ 1 | AC 編號：PRD 的 `AC-SI-NN-Y`、階段前綴形與任務書舉例的 `AC-132b-1` 皆含字母，不合 ADR-XPLAT-016 §8.1 的 `AC-[\d\-]+` | 百位 `9`＝AgentConsole 側：`AC-SI-32-Y`＝`AC-932-Y`；自增 AC 自 `AC-940-1` 起 | 替代：編譯前置轉換（框架改動）。再開症狀：`sdd_compile` 對本檔回報 `unmapped_at_ids` 非空，或 RTM 對不上 PRD AC |
| ⚖ 2 | 欄名對映：PRD 只說「欄名只經 snake_case↔camelCase 對映」「events 原樣轉 camelCase」，未定規則與遞迴深度 | R9：`^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 才轉，全深度所有物件鍵，值不動，未知鍵透傳 | 替代：只轉頂層（SDD 先例：巢狀內容保留 snake_case）。再開症狀：前端需要巢狀物件的原始鍵而對映造成混淆，或日後根層鍵含大寫而撞鍵 |
| ⚖ 3 | PRD:472 的「事件 JSON 逐字」與 PRD:764（§9.1 C18 backend 列：`events` 為 `Map<String,Object>`、多型事件鍵依 `kind`、**原樣轉 camelCase**）並讀有張力（轉換後的鍵不再逐字） | 依 PRD:764（Architect 棒定的實作座標）：詳情顯示收到的物件（camelCase 鍵、值不動）的縮排 JSON；「逐字」解讀為值逐字、不補不減 | 替代：前端把鍵轉回 snake_case 再顯示。再開症狀：掌舵者要把事件 JSON 貼回 CLI 對照而嫌鍵名不同 |
| ⚖ 4 | Bridge 503 本文：PRD 只定 `detail`＝`rc=<n>; stderr=<末 1,000 字元>`；無行程的失敗形態與可機器判別的碼未定 | 本文加 `cause`（九值，R4 表）；無行程時 `stderr=` 位置填 Bridge 自寫說明 | 替代：只用 `reason` 與 `detail`。再開症狀：測試或 Console 需要區分失敗形態而無法由 `detail` 文字穩定判斷 |
| ⚖ 5 | 「查詢參數只有 `since` 與 `limit`，其餘一律不收」的「不收」是拒絕還是忽略 | 拒絕：未知參數 422 `invalid_request`；`/si/status` 與 `/si/proposals/{id}` 不收 `since`／`limit`（CLI 對 status 併用 `--since` 本就 rc 3） | 替代：靜默忽略。再開症狀：前端或第三方拼錯參數得到全量頁而誤讀 |
| ⚖ 6 | `limit` 超過 `export_limit_max`：PRD 規定 rc 非 0 即 503，但這是使用者輸入錯誤 | 不在 Bridge 複製上限；CLI rc 3 依 R4 回 503 `nonzero_rc`；前端永不送超限值 | 替代：Bridge 把 rc 3 且 stderr 為旗標錯誤者對映成 422。再開症狀：非前端的呼叫者因超限被誤報成「SI 不可用」 |
| ⚖ 7 | `--repo` 旗標：PRD 說預設＝腳本所在 repo，Bridge 是否明示未定 | 不帶（少一個可被誤用的旗標；`si_root` 即腳本所在 repo） | 替代：明示 `--repo <si_root>`。再開症狀：腳本被複製到別處執行，`si_root` 與腳本所在 repo 不一致 |
| ⚖ 8 | 模組桶：PRD 把 `buckets[]` 歸根層 P2 鍵，而 FR-SI-32 補述的篩選含模組桶，P1b 與 P2 的次序不保證 | P1b 不等它：欄缺席時控制項 `disabled` 加說明、前端不重算；欄出現時零改動即可篩（AT 以兩種資料釘住） | 替代：P1b 不提供桶篩選。再開症狀：P1b 出口驗收時掌舵者要求桶篩選可用而根層 P2 尚未交付 |
| ⚖ 9 | 時間窗：PRD 只說「時間窗」，粒度、錨點與時區未定；OBS 時間欄無 offset、檔頭 `tz=` 不在 export 內 | 日曆日字串比對、錨點為回應 `generatedAt` 的日期、四個預設（全部、今天、近 7 天、近 30 天）、不換算時區 | 替代：自訂區間與時區換算。再開症狀：篩選結果邊界差一日被回報 |
| ⚖ 10 | 頁面範圍未列「運轉」，但 `/si/runs` 與 `getSiRuns` 要有消費者 | 事件分頁上半「運轉」表、下半「事件帳本」列表 | 替代：獨立分頁，或省略（則 `getSiRuns` 成死碼）。再開症狀：掌舵者要求運轉獨立成頁 |
| ⚖ 11 | reason 常數落點：前端 `reasons.test.ts` 把 `REASONS` 與**凍結**契約附錄 B 雙向鎖，加 SI 常數必紅；`si_not_found` 又打破契約 §0.3 第 8 點「404 的 reason 省略」（唯一例外是 `rtm_not_found`） | 前端常數住 `lib/domain/si.ts` 的 `SI_REASONS`，以凍結 Architecture §11.1 的表對拍（比對範圍＝`reason` 以 `si_` 起頭且標 P1b 者；`invalid_request` 是 Bridge 層 reason、不進常數）；「唯一例外」字樣的可編輯處——`NotFoundException`、`ErrorResponseDocumentation`、`ErrorReasons` 與 `frontend/lib/api/reasons.ts` 的註解——由開發 agent 於實作 commit 改述（`reasons.ts` 只改註解）；凍結的契約 §0.3 第 8 點不改，由契約後繼檔載明第二個例外（⚖ 12） | 替代：修改契約附錄 B（凍結檔，不可）。再開症狀：前端需要把 SI reason 與其他 reason 放在同一張表查詢 |
| ⚖ 12 | 契約後繼檔的檔名與範圍：PRD §9.1 C18 的「文件與 CI 連動」列要求「契約新版（`API_Contract_P3-6.md` 後繼）」，但該檔與 `openapi-p3-6.yaml` 是本鍵凍結檔、不可改；PRD 未定後繼檔的檔名與範圍 | 預設＝新檔 `AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P1b.md`（D12 (a)；主控於 SCG-5 落檔、與實作同一個 commit，開發 agent 於交卷以純文字附全文草稿——hooks-ON 的 IMPLEMENTATION 態寫不進 `docs/02_architecture/`，R26）；範圍＝六個 backend GET 與六個 Bridge GET 的路徑、查詢參數、狀態碼（200、401、403、404、405、422、502、503、504）與 `reason` 對映表，來源＝PRD §9.3、Architecture §10.3 與 §11.1、本檔 R5、R7、R8；凍結的契約與 openapi 不動 | 替代：修訂凍結的 `API_Contract_P3-6.md` 與 `openapi-p3-6.yaml`（走 T1；凍結檔不可原地改）。再開症狀：第二個消費者出現而後繼檔不敷使用，或後繼檔與 `/v3/api-docs` 漂移 |
| ⚖ 13 | 容器掛載：Architecture §12.1 L-14 的兩個未實測風險（單檔 bind 的 inode、`packed-refs` 缺檔），PRD 要求「P1b 以真容器二擇一」 | AT 接受兩個具名設計恰其一（設計 A 六條、設計 B 整個 `.git` 唯讀加空檔覆蓋 config），由 V3 決定；設計 B 需入庫一個空檔 | 替代：整個 repo 唯讀掛載（PRD FC-b 已否決：暴露被忽略的 `.env`）。再開症狀：V3 兩個設計皆失敗 |
| ⚖ 14 | `BridgeEndpoints.siBase()` 的解析來源 PRD 只列名 | 同 `sddBase()`：自訂 `sdd.engineUrl` 優先、否則 `ENGINE_BRIDGE_URL`、去尾斜線 | 替代：新增 `si.engineUrl` 設定鍵（新設定面，Rule 2 否）。再開症狀：SI 與 SDD 需指向不同 Bridge |
| ⚖ 15 | 差分夾具的來源：用真 repo（併發下不穩、且 AC-932-2 的前後比對會被主控的並行編輯擾動）、假 CLI（失去差分意義）、還是複本 | 真 CLI 閉包複製進 tmp 倉＋入庫的凍結帳本複本（取自真帳本與真事件帳本）＋建倉時自真 repo 複製的 `params.json` | 替代：整個倉複製（龐大）。再開症狀：複本與真帳本格式漂移使差分變成「對自己」 |
| ⚖ 16 | CLI 閉包的範圍 | 現查四路徑（R25）；`export` 的 import 閉包日後變動時，測試與 CI `paths` 同一個 commit 收齊（AT 鎖住） | 替代：複製整個 `tools/`（57 MB、8 千餘檔）。再開症狀：閉包不完備使建倉失敗 |
| ⚖ 17 | ADR-SI-12 的再開症狀「逼近逾時」未量化 | 冷啟動三次中位數超過 7.5 秒（逾時 15 秒的一半）即再開 | 替代：其他比例。再開症狀：實測逼近或超過 |
| ⚖ 18 | HTTP 層快取 | 不加 `Cache-Control`（Bridge、backend、前端三層皆不快取） | 替代：nginx 或 backend 對 `/api/v1/si/**` 加 `Cache-Control: no-store`（backend 以回應標頭、或 nginx 以 `add_header`；既有 nginx 設定有單一 `Cache-Control` 的鎖，須同步，見 §4 刻意不做）。再開症狀：畫面資料過期而查得是 HTTP 層 |
| ⚖ 19 | PRD §9.1 C18 未列的檔名與簽名，以及與 C18 列示不同的簽名：`SiKeyNames`、`AgentBridge.siExport(String, Integer, Integer, String)`、`SiExport.raw()`、`si_repo_support.py`、`si_golden_regen.py`、`MiniBridge.Si`；`run_export` 的簽名 | 本檔釘住（測試需要穩定入口）；C18 表依其「檔名可微調並回寫本表」的約定由主控回寫。`run_export(si_root, kind, *, since=None, limit=None, ident=None)` 與 C18 的 `run_export(kind, since, limit, id)` 的差異與 WHY：(一) 多首位 `si_root`——函式不讀全域設定，與 `sdd_cli.run_verb` 以 `sdd_root` 為參數同體例，使測試可注入 tmp 倉；(二) `since`、`limit`、`ident` 為關鍵字限定——兩個整數參數不致位置誤置；(三) `ident` 而非 `id`——不遮蔽內建 `id` | 替代：完全照 C18 的簽名（`si_root` 改由模組層設定取得，測試須以 monkeypatch 注入）。再開症狀：實作者以 ArchUnit 或 ruff 為由改名，或其他消費者依 C18 的簽名呼叫 `run_export` |
| ⚖ 20 | 處置篩選的粒度 | 處置首詞，`DEF-` 起頭併為 `DEF-*`（R17） | 替代：完整字串。再開症狀：處置枚舉新增而首詞規則切錯 |
| ⚖ 21 | 提案與事件分頁的篩選集合（PRD 只列觀察欄位） | 提案：`狀態`、`類別`；事件：`種類`、`時間窗` | 替代：不提供。再開症狀：掌舵者要求更多篩選 |
| ⚖ 22 | 登記表輔助函式名稱與 icon | 輔助函式名稱不鎖（測試以匯出者為準）；`AT-932-1-7` 釘住 `lib/domain/si.ts` 的五個匯出名稱；icon 只驗存在與互異 | 替代：全部釘名。再開症狀：實作者與測試對名稱理解不一致 |
| ⚖ 23 | `mobile` 為 `false` 的入口如何在 <768 不顯示（單一 nav 服務三形態） | DOM 內全在、以類別 `max-md:hidden` 隱藏；jsdom 可驗類別、真視窗由 V2 驗 | 替代：條件渲染（需 JS 視窗判斷，破壞 SSR 一致）。再開症狀：V2 實測 <768 仍可見 |
| ⚖ 24 | `SI_PAGE_LIMIT` 初值 | 100（無先例、未校準；`export_limit_max` 為 500） | 替代：500。再開症狀：載入次數過多或首屏過慢 |
| ⚖ 25 | argv 白名單常數含 `obs-add --dry-run`（PRD §9.4 文字如此，屬 P2b） | 常數含兩個配對，但 P1b 真檔不得組出後者 | 替代：P1b 只含 `export`、P2b 再擴。再開症狀：P2b 鍵啟動時須同步改鎖 |
| ⚖ 26 | AT 命名（Java 方法底線形開頭）與判定指令形態 | 底線形開頭加駝峰敘述；Checkstyle 規則集無方法命名規則（SA 已實查 `config/checkstyle/checkstyle.xml`） | 替代：`@DisplayName`。再開症狀：Checkstyle 日後加方法命名規則 |
| ⚖ 27 | RTM 本地子表範圍 | `F-901`、`US-901`～`US-907`、14 個 AC 與全部 AT 逐列（先例 FsmTrail 子表） | 替代：只列 AC。再開症狀：子表過長難維護 |
| ⚖ 28 | OBS-SI-202 的升格範圍 | V6（真後端 E2E；非 AC）；失敗或未做則保留現狀並寫再開症狀（OBS-SI-202 的處置文字） | 替代：列為 AC。再開症狀：升格再度無人承接 |
| ⚖ 29 | `{id}` 格式由誰驗 | 只在 Bridge 驗（單一真相）；backend 嚴格編碼後原樣轉發（嚴格編碼＝RFC 3986 非保留字元以外全部百分比編碼；整段恰為 `.` 或 `..` 時，點字元亦編為 `%2E`，這是本檔類推，避免被 HTTP 堆疊正規化成路徑穿越，R7），Bridge 的 422 對映為 backend 422 | 替代：兩處各驗。再開症狀：Bridge 的 422 訊息洩漏內部資訊 |
| ⚖ 30 | 黃金檔與真輸出的比較方式（根層日後加欄位如何不致誤紅） | 子集比較（比對前於雙方全部深度把鍵名為 `head_sha` 的值以占位取代、移除各回應頂層的 `generated_at`；黃金檔的每個鍵值在真輸出同位置存在且相等；真輸出可多鍵）；黃金檔不含任何由 commit sha 衍生的值（§5.1） | 替代：精確相等（根層任何加欄位即紅，跨鍵耦合）。再開症狀：子集比較漏掉「鍵不變語意變」的根層改動 |

### 7.2 SA 對凍結上位文件的發現（供主控處理；本檔未改任何凍結檔）

1. **契約 §0.3 第 8 點**（凍結 `API_Contract_P3-6.md`）與 `NotFoundException`、`ErrorResponseDocumentation`、`ErrorReasons`、`frontend/lib/api/reasons.ts` 的註解皆稱 `rtm_not_found` 是 404 帶 reason 的唯一例外；本鍵使 `si_not_found` 成為第二個（⚖ 11）。可編輯的四處由開發 agent 於實作 commit 改述（R26）；凍結的契約與 openapi 不改，由 D12 (a) 的契約後繼檔載明第二個例外；凍結檔上的字樣由主控登 OBS 處理。
2. **PRD §9.1 C18「契約新版」**以 D12 (a) 的新檔 `API_Contract_SelfImproving_P1b.md` 承接（主控落檔，開發 agent 交卷附全文草稿；R26），凍結的 `API_Contract_P3-6.md` 與 `openapi-p3-6.yaml` 不動（⚖ 12）。
3. **Architecture §10.3 簡表**的 Bridge 失敗列只有 `reason`；本檔另定 `cause` 欄（⚖ 4），主控於 RELEASE 之後的純文件 commit 去註時一併補一句（R26）。
4. **PRD §8.1 P1b 與 §9.6 P2 的先後**：P1b 的模組桶篩選依賴 P2 才交付的 `buckets[]`（⚖ 8）；屬排程備註，不需要修訂凍結檔。

（已移除的原項：事件 JSON 逐字與欄名對映的張力，已由 PRD:764 解決，見 ⚖ 3；`reasons.test.ts` 雙向鎖與 C18 的前端 SI 條目，已由 ⚖ 11 的 `SI_REASONS` 落點解決。兩項皆不需要主控處理。）

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC（14 個 AC 皆至少一個 AT） | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式；每個 AT 可單跑（Bridge `-k`、backend `--tests`、frontend `-t`） | □ |
| 負向測試覆蓋 | 每個 AC 至少一個負向或負控 AT（AC-940-5 的負控內含於其兩個 AT 的對照斷言；AC-940-8 為契約面靜態檢查，負向由 AC-932-2 承擔） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試（鍵對映、日期窗、分頁、`limit` 上限、`stderr` 尾段、`stdout` 上限、路徑邊界） | □ |
| 測試資料規格完整 | 資料來源明確定義（§5）；夾具與黃金檔可重現 | □ |
| 出口 (e) 與 V 系列 | V1～V10 有結果與證據；V5 為掌舵者真機回報 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| # | 日期 | 位置 | 原文（摘） | 訂正 | 依據 |
|---|------|------|-----------|------|------|
| 1 | 2026-10-22 | D4 檔名表（PRD §9.1 C18） | `SiObservationDto`／`SiProposalDto`／`SiRunDto`／`SiStatusDto` 四個具型別 DTO | 未建；改以單一 `SiExportResponse`（`@JsonValue` 無型別樹，`additionalProperties: true`）＋`SiKeyNames` 深層欄名對映取代。理由：保住「缺鍵≠null」語意與未知鍵透傳（R9）；具型別 DTO 會把兩者都變 null、等於替 Bridge 補話 | ⚖-A（主控追認，SCG-4 §A AC-932-1）；PRD 凍結檔走〈修訂建議〉 |
| 2 | 2026-10-22 | AT-940-1-1 (a) | 「各子情境的 `allowed_path_roots` 都不含 `si_root`」 | 改述為「有無 `SI_ROOT` 都不改變 `allowed_path_roots`；明列 `BRIDGE_ALLOWED_PATH_ROOTS` 時 `si_root` 不會溜進去」——(a) 未設 `SI_ROOT` 且 REPO_ROOT 像 monorepo 時既有預設白名單本就含 REPO_ROOT，而此時 `si_root` 即該根，原字面自相矛盾 | ⚖-B |
| 3 | 2026-10-22 | AT-932-3-E-2；§4「逾時」列 | 逾時縮小為 0.5 秒 | 2.0 秒（孫行程未出生時改 6.0 秒重試並斷言孫行程 pid 檔存在）；0.5 秒在慢機器上會在孫行程出生前就殺掉假 CLI，鑑別力歸零；仍遠小於假 CLI 的 30 秒睡眠 | ⚖-C |
| 4 | 2026-10-22 | AT-932-3-4 | `detailObject()` | 既有 `BridgeRejectedException` 的實際存取器為 `body()`／`detail()`／`violations()`；`SiBridgeErrors` 以 `body().get("cause")`／`get("id")` 取值 | ⚖-F |
| 5 | 2026-10-22 | AT-932-2-5（ArchUnit） | 類名判準 `Si*Controller` | `Si(?![a-z]).*Controller`（避開既有 `SignoffController`） | ⚖-G |
| 6 | 2026-10-22 | D5；§5.1 | 黃金檔 `golden-*.json` 字樣 | 定為 `{A,B}.{snake,camel}.json`（Bridge `tests/fixtures/si_golden/` 四檔、backend `src/test/resources/si/` 四檔、frontend `tests/fixtures/si/` 兩檔 camel） | ⚖-E |
| 7 | 2026-10-22 | R23／AC-940-3 設計 A／B | 設計 B 的空檔 `AgentConsole/docker/si/git-config.empty` | 採設計 A，空檔未建；設計 B 解讀為「設計 A 的 tools 與 docs/06_quality 兩條 bind＋整個 `../.git` 唯讀＋空檔覆蓋 `/repo/.git/config`」；V3 真容器結果決定是否轉 B | ⚖-D；Architecture §12.1 L-14 |
| 8 | 2026-10-22 | AT-940-4-1；檔頭「補前預期紅」 | 主控補 D11 前預期紅 | 事實記錄：D11（`agentconsole-ci.yml` push／pull_request 各五行）由主控於 2026-10-21 補上後轉綠；QA 2026-10-22 重跑為綠 | SCG-4 §A AC-940-4 |
| 9 | 2026-10-22 | V4 冷啟動三個中位數 | 待量 | 尚未量測；量到後記於此（本輪 V1～V10 皆未驗，見 SCG-4 報告〈未驗〉） | SCG-4 §E |
| 10 | 2026-10-22 | 其餘登記（不改規格） | — | OBS-SI-259（⚖-H `PageTitle` h2 債）、OBS-SI-260（P3-6 契約「唯一例外」字樣）、OBS（根層 `export` 的 `touched` null 無 `ne` 項，SCG-4 P3-1）、OBS（`schema.d.ts` 無路徑集合對拍鎖，SCG-4 P4-3）；P3-1 前端側已於修復棒二改為 NE 顯示並補 vitest（掛 AC-932-3 之下，不另編 AT） | SCG-4 判決檔 §三 |
| 11 | 2026-10-25 | AT-932-2-1、AT-932-2-E-1（Bridge AST 鎖） | 「無寫入形態、argv 動詞只准 `export`」（零寫入前提） | P2b 起寫入形態只准出現在 `app/si_audit.py` 且路徑源自 `settings.si_audit_dir`；argv 動詞白名單擴為 `export` 與 `obs-add --dry-run` 兩個配對；測試改寫並改名為 P2b TCS 的 AT-933-1-6、AT-933-1-E-3（P1b 的兩條 AT 退役） | P2b TCS §4 第 1 項、⚖19；PRD AC-SI-33-1、35-1 ② |
| 12 | 2026-10-25 | AT-932-2-3（Bridge 405 矩陣） | 「六路徑乘四種非 GET 方法皆 405」 | `POST /si/observations` 自 P2b 起為寫入端點：改為 PUT／PATCH／DELETE 乘六個讀路徑皆 405、POST 乘其餘五個讀路徑皆 405；九個 `/si/` 路徑的三方法矩陣由 AT-935-3-E-2 承擔；原名保留、原地改寫 | P2b TCS §4 第 2 項 |
| 13 | 2026-10-25 | AT-932-2-4（backend 角色×方法矩陣） | 「六路徑乘 POST／PUT／PATCH／DELETE 乘三種角色：Operator 與 Admin 405」 | `SecurityConfig` 對 `POST /api/v1/si/**` 要求 ADMIN：POST 組移出；PUT／PATCH／DELETE 乘六路徑維持；POST 乘五個無 POST 映射的讀路徑另測（無 token 401、Viewer 與 Operator 403、Admin 405）；原名保留 | P2b TCS §4 第 9 項 |
| 14 | 2026-10-25 | AT-932-2-5（ArchUnit） | 「`Si*Controller` 沒有任何非 GET 映射、`AgentBridge` 上 `si` 起頭的方法恰為 `siExport`」 | 改寫並取代為 AT-935-3-1：`@GetMapping` 6→7、`@PostMapping` 0→4、無 Put／Patch／Delete；`AgentBridge` 的 `si[A-Z]` 方法 1→5；新增「寫入只經 `SiConsoleWriteService`」 | P2b TCS §4 第 8 項 |
| 15 | 2026-10-25 | AT-932-2-7、AT-940-8-2（frontend 端點／schema 釘選） | 「get 加 `Si` 恰六個」「`schema.d.ts` 六路徑各只有 get」 | 取代為 AT-950-9-E-1、AT-950-10-2（P2b 加五個函式與四條路徑） | P2b TCS §4 第 14 項 |
| 16 | 2026-10-25 | AT-932-2-8（frontend 靜態掃描） | 「`components/domain/si/**` 不含表單、mutation hook、非 GET 方法字樣」 | 取代為 AT-950-9-E-2（P2b 的三個對話框是合法表單與 mutation；掃描改為白名單形態） | P2b TCS §4 第 15 項 |
| 17 | 2026-10-25 | AT-940-3-1、AT-940-3-E-1（compose 掛載） | 「SI 相關 bind 皆為長語法唯讀」 | 改為「設計 A 或 B 的唯讀 SI bind 加恰一條可寫稽核 bind（`BRIDGE_SI_AUDIT_DIR`）」；九種壞變體保留；原名保留 | P2b TCS §4 第 3 項；Architecture §12.1 L-14 |
| 18 | 2026-10-25 | AT-940-4-1、AT-940-4-E-1（CI paths） | `SI_INPUTS`＝`CLI_CLOSURE`＋`PARAMS_SRC` | `SI_INPUTS` 改取 `WRITE_CLOSURE`＋`PARAMS_SRC`；`FULL_PATHS` 補 `tools/lib/apply_lock.py`、`tools/lib/sdd_latest.py`；原名保留 | P2b TCS §4 第 3 項、D10 |
| 19 | 2026-10-25 | AT-940-5-1（`SI_REASONS` 對拍） | 比對範圍＝標 P1b 的 `si_` reason（2 值） | 改為 `reason` 以 `si_` 起頭的全部列（5 值），與 AT-950-9-2 合併斷言；原名保留 | P2b TCS §4 第 17 項 |
| 20 | 2026-10-25 | AT-940-8-1（OpenAPI 恰六路徑各只 get） | 六路徑、只有 get | 取代為 AT-950-10-1（SI 路徑 10 條、`/api/v1/si/observations` 有 get 與 post） | P2b TCS §4 第 10 項 |
| 21 | 2026-10-25 | §6.1 追溯（RTM §2.2 子表） | 子表 AT 欄指向上列原名 | RTM §2.2 子表的對應列改指新 AT 名（主控同 commit）；取代者在子表以「→ AT-9xx-y（P2b）」標示、不刪列 | ⚖19 再開症狀 |
| 22 | 2026-10-25 | AT-932-1-E-6（模組桶缺席時停用）；§5.1 黃金檔 | 「狀態 A 沒有 buckets 欄」（以 2026-10-22 黃金檔為前提） | 真 CLI 自根層 P2 起每列都帶 `buckets`；黃金檔於 2026-10-25 依根層 P3 的 `status`／`export` 增量重產（`tests/si_golden_regen.py`；三份副本逐位元組相同），降級路徑改以去掉 `buckets` 欄的狀態 A 複本驗（`SiView.test.tsx` 該 it 的 `renderSi({ fixture })`）；斷言不變、原名保留 | 根層 P3 TCS R130；黃金檔重產規則（§5.1） |
