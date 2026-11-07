# SCG-4 獨立審查報告 — ResearchToPRD P0（鍵 agentconsole-research-to-prd-p0）

> 審查者：SCG-4 獨立審查 QA 鏡（Sonnet；全程唯讀）｜日期 2026-11-03｜審查基準 origin/main `0b678757`（審查期間 HEAD 前進到 `04884296`＝主控 compose 接線，僅動 docker-compose.yml／.env.example，不影響九包程式）｜Oracle：凍結 TCS-ResearchToPRD-P0-20261102（AT 210）＋ PRD／API 契約／ADR-003／ADR-XPLAT-017｜裁決 D-67～D-75 以主控裁決為準並標「裁決偏離」

## A　摘要與判定

**判定：FAIL（一審；P1 0／P2 4／P3 5／P4 5）**——判定規則 P1 0 且 P2 0 ⇒ PASS；四個 P2 中三個是**測試鑑別力缺口**（F-01 地板邊界、F-03 常數與邊界、F-04 D-71′ 事件載體），一個（F-02）是前端與 Bridge 的「授權待查」判準分歧（含測試缺口）；**無實作缺陷被證實會讓 P0 功能失效**（Gate 0、審查判定、抓取安全、RBAC、SSE、DDL 守衛的核心突變皆被擊殺）；九包在 120 個單點突變下 103 個被擊殺。

- **AT 結果**（TCS §3 共 210 條）：自動化 193 條全 PASS（pytest 108／JUnit 39／vitest 45／Playwright 1〔AT-960-17-1：打字 P95 17.2／13.7／13.6 ms〈門檻 100〉、Diff 中位 2 ms〈門檻 1,000〉、預覽首次渲染中位 114 ms／冷啟 364.6 ms〈門檻 2,000〉；機器 i5-14600K 20 核／127.7 GB／Chromium 156〉）；指令核對 12 條：PASS 11、部分 1（24-1：RTM 未回填＝主控步驟）；NOT-EVALUABLE 5 條（Docker／Playwright 的 22-2～22-5 與 22-E-1，檔案尚未交付）。
- **基線真跑**（工作樹 0b678757；rc 全 0）：Bridge 研究 21 檔 877 通過／0 略過（`SDD_ROOT`＋`BRIDGE_TEST_DSN` 皆在）；sdd 三檔 382 通過／2 略過（既有 symlink）；Gradle 9 類 108 tests／0 fail／0 skip／BUILD SUCCESSFUL；5 個遷移 IT 37 tests；vitest 全套 2,191 通過；ruff 兩視角 rc 0；`tsc --noEmit` rc 0；`npm run lint` rc 0；`check_pytest_baseline_sites` rc 0；`check_loc_budget` rc 0；`TestDirEntryPrimitivesAreAccountedFor` 7 OK；Playwright 11 案（見 G）。
- **突變**（`git archive` 副本）：9 包各 ≥5（見 D 表）；存活 15（逐一判讀後列為 F-01／F-02／F-03／F-04 的 P2、F-06／F-08 的 P3、F-12 的 P4），等價 2（FB-2、DB-4）；BRA-7 在 ALL 階段曾被負載下不相關的 orchestrator 測試「擊殺」，不採信，改以靜態佐證（tests 內無 limit>500 請求）判存活。存活者另做**全套複驗**（G）：Java 三者（API-9／API-10／DB-15）同時套用跑全 backend＝2,324 tests／0 failures／0 略過；Bridge 七者（BRC-2／13／14／20／22、BRB-11、BRA-7）同時套用跑全 engine-bridge 套件＝紅／錯 53 筆，與無突變基線的 53 筆逐筆相同（皆副本缺 monorepo 根的環境相依、研究測試零紅）⇒ 全部確認存活。
- **接縫**：型別／鍵集／路徑／事件型別／approve 鍵全對得上；唯二偏差＝approve 摘要不符錯誤碼（F-05）、授權待查判準（F-02）。
- **裁決偏離**：D-68～D-75 逐條核實屬實（F.1）；D-72 的錯誤碼未同步三端（F-05）。
- **待主控**：RTM 回填、Docker E2E、V 系列、勘誤批次與 refreeze（F-14，非缺陷）。

## B　發現表（F-nn）

| 編號 | 級別 | 標題 | 座標／證據 | 建議處置 |
|---|---|---|---|---|
| F-01 | P2 | AT-960-12-2 缺「最低維度恰 60 ⇒ PASS」正例（地板邊界未釘；突變 BRC-2 存活） | TCS AT-960-12-2 When 首組＝「預檢過、W100 8,500、最低維度 60、未結 P1 0」應 PASS；`tests/test_research_gates.py:573-589` 的 PASS 案例用 scores(90,90,90,90)／(85,85,85,85)，地板只有負例 59。`gates/aggregate.py:94` `lowest >= DIMENSION_FLOOR` 改成 `>`：Bridge 研究套件（含全套）全綠 | 於 AT-960-12-2 表驅動加一組四維含恰 60 且 W100≥8,500（例 ARCHITECTURE=100、PRODUCT=100、QA=60、SECURITY=75 ⇒ W100 8,500；或 100／100／60／100）⇒ verdict PASS、`all_dimensions_ge_floor` 真；同組對 `ResearchSchemaMigrationIT` 的 `通過` CHECK 寫入成功（SQL 端 `>=` 同邊界） |
| F-02 | P2 | 前端「授權待查」判準與 Bridge 不一致：不認 UNKNOWN、認複合表達式內的 GPL；LGPL／UNKNOWN／複合式皆無測試（突變 FB-5 存活） | `frontend/lib/domain/research.ts:1114-1118` `isLicensePending`＝空字串／「未見」／`/\bA?GPL/i`；Bridge `gates/evidence.py:518-523` 認 None／空／`UNKNOWN`／「未見」＋前綴 GPL／AGPL（`startswith(p+"-")`）；`export.py:255` 只在渲染 matrix.md 時把 UNKNOWN 轉「未見」，DB 的 `research_sources.license_spdx` 仍存 `UNKNOWN`（`gates/ingest.py:21` 原樣入庫）。TCS AT-960-9-6 Given 含 `UNKNOWN` 且計入待查 4 筆；前端 `EvidenceMatrixTable.test.tsx:168,188` 只測 GPL-3.0-only 與 MIT | 前端 `isLicensePending` 對齊 Bridge：UNKNOWN 視同未見；比對改前綴式（大寫後 `==GPL`／`startsWith('GPL-')`／AGPL 同；LGPL 與 `MIT OR GPL…` 的處置明寫）；補 vitest：UNKNOWN、null、LGPL-3.0、`GPL-2.0-or-later`、`Apache-2.0 OR GPL-2.0`、小寫 `gpl-3.0-only` 各一列，並與 Bridge 同表對拍（可共用 fixtures） |
| F-03 | P2 | TCS 明定的常數與邊界只釘單側或完全未釘（突變 BRC-13、BRC-14、BRC-22、BRC-23、API-9、API-10、DB-15 存活） | BR-C `gates/evidence.py:481` 儲存格 600 的 `>`→`>=`；`:38` `MIN_EVIDENCE_ROWS` 3→2；`gates/review_card.py:148` 「18 分以上 note 必含 §」的 `>= 18`→`>= 19`、`:49` 錨點章範圍 `1[0-4]`→`1[0-5]`（第 15 章也通過）；console-api `ResearchInputGates.java:59` slug `{0,29}`→`{0,30}`、`:205` PRD 1 MiB `>`→`>=`；DB `V16__research_core.sql:11` `rp_no ~ '^RP-[0-9]{4,}$'`→`{3,}`：各自在其套件（含全研究套件／全 Java 研究類）全綠 | BR-C：AT-960-9-1 變體加「恰 600 字元」正例；新增證據閘 3／2 列邊界案例（恰 3 列 ready、2 列不 ready）；AT-960-12-3（審查者輸出驗證）加「score 恰 18 而 note 無 § ⇒ V3 違規」與「score 17 無 § ⇒ 通過」、`prd_anchor` 的 §14 通過／§15 與 §0 拒絕。API：AT-960-4-1 加 30 字／31 字 slug 與 1 MiB／1 MiB+1 位元組 PRD 的邊界組。DB：AT-960-1-5 加 `RP-123`（3 位數）拒絕、`RP-1234` 通過 |
| F-04 | P2 | AT-960-8-E-3 的「skipped:over_limit 落在事件 payload」（D-71′：`research.alert` kind=FETCH_SKIPPED_OVER_LIMIT）沒有任何測試釘住（突變 BRC-20 存活） | `app/research/orchestrator.py:697` 發 `research.alert`（`kind="FETCH_SKIPPED_OVER_LIMIT"`、`detail`＝JSON）；`tests/test_research_fetch_security.py:973-975` 只驗 `plan.skipped[*].to_payload()` 形狀，沒有任何 orchestrator／DB 層測試斷言該事件被寫入或 kind 字串；把 kind 改成 `FETCH_SKIPPED` 全套綠 | 於 AT-960-8-E-3（或 7-x 的 RESEARCH 階段整合案例）加：候選數超過 per_layer／total 上界的 RESEARCH stage ⇒ `research_events` 恰有對應筆數的 `research.alert`、`payload.kind=='FETCH_SKIPPED_OVER_LIMIT'`、`detail` JSON 含 reason／layer／kind／url／limit，且 `research_fetches` 無這些 URL 的列、`research.step` payload 仍四鍵 |
| F-05 | P3 | Gate 0 摘要不符的錯誤碼三端不一致：Bridge 422 `digest_mismatch`／`missing_digests`（D-72），console-api／前端／OpenAPI／MiniBridge 仍是 409 `spec_digest_changed` | Bridge `routers/research.py:698-700`、`orchestrator.py:1149-1165`；console-api `ErrorReasons.RESEARCH_SPEC_DIGEST_CHANGED`、`ResearchBridgeErrors.java:55-57`（422 原樣轉出 reason）；前端 `lib/domain/research.ts:721,745`（只有 spec_digest_changed 文案）；`MiniResearchController`；OpenAPI 回應說明 `spec_digest_changed`；Bridge 測試檔頭自述 `test_research_approve.py:8-12` | 勘誤批次同步：契約 §0.2／§1.4／API-RP-12、TCS AT-960-14-2／14-3／14-E-2、`ErrorReasons`＋`ResearchErrorDocs` 加 `digest_mismatch`／`missing_digests`（或 Bridge 改回 409 spec_digest_changed 並保留 details.files）、前端 `REASON_TEXT` 兩條文案 |
| F-06 | P3 | Bridge `GET …/events` 的 `limit` 上限 500 無任何測試釘（突變 BRA-7 在靶向套件存活） | `routers/research.py:76,866` `EVENTS_MAX_LIMIT = 500`／`min(limit, EVENTS_MAX_LIMIT)`；tests 只用 `limit=500` 取資料，無 501／1,000 案例；console-api 端另有上限 500（`ResearchQueryService.java:49,101`） | `test_research_events.py`／`test_research_router.py` 加 `limit=501` 回 ≤500 筆且 `truncated` 為真的案例 |
| F-07 | P3 | AT-960-22-E-1 無測試檔／無 AT 標記；Docker 全棧 E2E（22-2～22-5）尚未交付（任務書字面「無測試的 AT＝P2」；此五條屬 §5.7「整合 P0」主控交付、尚未到期，故降為 P3——主控若要依字面算可升回 P2） | `tests/e2e/research.mock.spec.ts`、`research-docker.stack.ts` 皆不存在；語意由 `a11y.mock.spec.ts:239-293`（研究三情境、axe 零違規×1,440／1,000／600）與 `research-studio-perf.mock.spec.ts:678-679`（橫向溢出）分散涵蓋，彈窗焦點陷阱由 vitest 元件測試涵蓋 | 主控整合 P0 步驟：寫 `research-docker.stack.ts`；22-E-1 要嘛補 `research.mock.spec.ts` 並以 AT_960_22_E_1 標記，要嘛以勘誤把 AT 指向 a11y.mock.spec.ts 的三情境 |
| F-08 | P3 | 前端 `ResearchListView` 三個徽章（active／frozen／delivered）的對比度修法（D-73）只有 Playwright a11y 守，vitest 層無斷言（突變 FD-2／FD-3／FD-4 存活） | `components/domain/research/ResearchListView.tsx:204-206` 三列 `"bg-wg-base text-wg-primary-strong"` 任一改 `text-wg-primary`：vitest 全套綠；僅 `a11y.mock.spec.ts:239` 的清單情境會在瀏覽器紅（未對突變重跑 Playwright） | 仿 `FlowStepper.test.tsx:131` 的 `textClass`／token 對比斷言，補 ResearchListView 三個徽章列（active／frozen／delivered）的 class 斷言 |
| F-09 | P3 | 三處 reason 清單差異：Bridge 21／ErrorReasons 21／前端 RESEARCH_REASONS 18／契約 18（已知勘誤 ③） | `ErrorReasons` 多 `allowlist_exists`／`init_failed`／`not_implemented`（`ResearchReasonsTest.PENDING_ERRATUM` 明載）；前端 `lib/domain/research.ts:711-730` 無此三條文案；Bridge 另有 `compile_failed`／`fsm_state_unreadable`／`sdd_cli_failed`／`invalid_request`（不在 ErrorReasons，其中 invalid_request 為區域常數） | 勘誤批次補列後清空 `PENDING_ERRATUM`（測試會強制）；前端補三條文案（`allowlist_exists` 是 ADMIN 新增重複網域時使用者會遇到的 409） |
| F-10 | P4 | AT-960-23-1 全範圍子句字面不成立：base..HEAD 另含 4 個主控無關維護 commit（非包 commit；逐包子句 PASS） | `AutoClaude/.perf_baseline.toml`（a1d120c7 chore perf）、`tools/tests/_selfimproving_fixtures.py`＋`docs/06_quality/AutoSDD_Defect_Log.md`（263d4d16／8d858d76 DEF-200-579）、`env.shared`（bf866da0 停機線 95）；`.claude/` 差異為空 | 勘誤：23-1／23-2／23-4 的「整體 diff」子句限定為各包 commit 與本鍵 W0 連動檔，另列「主控無關維護 commit」例外清單 |
| F-11 | P4 | §5.7 包外檔案（皆有任務書或主控授權但 TCS 未列） | BR-B：`routers/research.py`（import 一行）、`tests/test_research_router.py`；BR-C：`engine-bridge/README.md`、`app/main.py`、`app/settings.py`、`tests/research_stage_support.py`（新）、`test_research_{capability,db,events,router,settings}.py`、`test_health_settings.py`；FE-B：`lib/api/types.ts`、`endpoints.test.ts`、`tests/fixtures/research/events.ts`（D-69）；FE-C：兩個 `page.tsx`、`lib/help/research-workspace.ts`（波次二接線）；FE-A：`lib/api/client.ts`（加 PATCH）；FE-D：整包無 §5.7 列（D-73）；API：`BridgeProperties.java`、`MiniBridgeApp.java` | §5.7 勘誤補列（或各包交卷列為授權擴充）；`client.ts` 加 PATCH 與 `BridgeProperties` 研究權杖屬性無 D-n 紀錄，補一句裁決 |
| F-12 | P4 | BR-B：Content-Length 恰等於上限時的處置未被測試釘（突變 BRB-11 存活）；規格只寫「超界」 | `fetch/http.py:548` `int(declared) > self._max_bytes` 改 `>=` 全套綠；TCS AT-960-8-5 只寫「超界＝TOO_LARGE」 | AT-960-8-5 補「恰 5242880 位元組通過、5242881 為 TOO_LARGE」兩列 |
| F-13 | P4 | 文字面小項：AT-960-14-8 測試檔名與 TCS 不同；AT-960-20-4 掃描字面自我命中；TCS §5.1 的 STEP_TIMEOUT 1,200 與 D-75 的 600 | AT-960-14-8 spec `test_sdd_freeze.py`、實際在 `test_research_approve.py`；`ResearchFlowHeader.test.tsx:123` 的反向斷言含四區塊名；`test_research_settings.py` 預期 600（D-75）而 AT-960-2-E-1 寫 1,200 | 勘誤批次逐條改字 |
| F-14 | P4 | 待主控收尾（非實作包缺陷）：RTM-P0 回填（474 處「待實作」）、Docker 全棧 E2E、V 系列（V-R2／V-R6／V-R7／V-B1／V-C1／V-D1／V-H1／V-H2）、ADR-003 §D9 回寫、勘誤批次與 refreeze | `RTM-ResearchToPRD-P0-20261102.md` 狀態欄；`tests/e2e/` 無 docker stack 檔；TCS SCG-4 通過標準 #1／#5／#6 | 依 RESTART_POINT 下一步序列 |

### B.1　P1／P2 逐條

**F-01（P2）AT-960-12-2 缺「最低維度恰 60 ⇒ PASS」正例（地板邊界未釘；突變 BRC-2 存活）**

**證據**：TCS §3.1 AT-960-12-2 的 When 逐字寫了首組輸入（預檢過、W100 為 8,500、最低維度 60、未結 P1 為 0）且 Then 為「僅第一組為 PASS」。實測 `tests/test_research_gates.py::test_AT_960_12_2_the_four_conditions_each_veto_a_pass_on_their_own`（:573-589）的 PASS 組是 scores(90,90,90,90) 與 scores(85,85,85,85)（最低維度 90／85），地板側只有 59 的負例，沒有「恰 60」的正例。突變 BRC-2（`app/research/gates/aggregate.py` `"all_dimensions_ge_floor": lowest >= DIMENSION_FLOOR` → `>`）在副本跑 Bridge 研究套件（BR-C 五檔靶向＋orchestrator＋全研究套件 21 檔，排除副本環境相依的 test_health_settings）全綠＝SURVIVED。**影響**：D-14／D-42 的「任一維度不低於地板 60」邊界沒有測試守，日後有人把比較改成 `>` 會把「最低維度恰 60」的合格輪判為 REVISE（耗審查預算，真實研究輪常見 60 分整數）。**這是測試鑑別力缺口、非實作缺陷**（實作現況正確）。**該補的 AT**：AT-960-12-2（見建議處置）；順帶 AT-960-12-E-3 的第二組亦可改成含 60 的組。

**F-02（P2）前端「授權待查」判準與 Bridge 不一致：不認 UNKNOWN、認複合表達式內的 GPL；LGPL／UNKNOWN／複合式皆無測試（突變 FB-5 存活）**

**證據**：同一份資料兩處各自計「授權待查」——Bridge 寫進 `00_research/evidence_matrix.md` 檔頭統計行與資安審查輸入（AT-960-9-6：六列 MIT／Apache-2.0／GPL-3.0-only／AGPL-3.0-or-later／null／UNKNOWN ⇒ 4），前端 `EvidenceMatrixTable`（`license-pending-count`）自 `licensePendingCount(items, sources)` 計。Bridge 規則（`gates/evidence.py:518-523`）：None／空／`UNKNOWN`／「未見」或大寫後等於或以 `GPL-`／`AGPL-` 起頭；前端規則（`lib/domain/research.ts:1114-1118`）：空字串／「未見」／`/\bA?GPL/i`。**分歧**：(a) `UNKNOWN`——agent 依模板「查不到寫 UNKNOWN」寫入的來源在 DB 就是字串 `UNKNOWN`（`ingest.py` 原樣入庫；只有 `export.py:255` 渲染檔案時轉成「未見」），console-api 不轉換（grep 無 UNKNOWN 處理），前端判為**非**待查，Bridge 判為待查 ⇒ 同一專案 UI 計數少於 matrix.md 頁頂與資安輸入；(b) 複合 SPDX 表達式 `MIT OR GPL-2.0`：前端命中、Bridge 不命中。PRD AC-R2P-05-5／NFR-R2P-13-1 寫「GPL／AGPL 系或『未見』」，而 D-70 明定 UNKNOWN 與「未見」渲染同為未見。**本回合實跑探針**（`qa_probe.test.ts` 在副本以 vitest 跑 `isLicensePending`；`be_probe.py` 以 `python -I` 唯讀匯入 Bridge `is_license_pending`；同一組輸入）：前端 `"UNKNOWN"=false；"MIT OR GPL-2.0"=true`，Bridge `"UNKNOWN"=true；"MIT OR GPL-2.0"=false`；其餘（LGPL-3.0 假、gpl-3.0-only／GPL-3.0-only／AGPL-3.0-or-later 真、MIT／Apache-2.0 假、null／空字串／未見 真）兩端一致。**突變**：FB-5（regex 去掉 `\b`，使 LGPL 也命中）在 vitest 全套 2,191 全綠＝SURVIVED，證明 LGPL 不算待查的實作決定沒有測試釘。**該補的 AT**：AT-960-10-6（前端；加 UNKNOWN、LGPL、複合式、大小寫四列）與 AT-960-9-6（對拍：同一組列，Bridge 與前端結果相等）。

**F-03（P2）TCS 明定的常數與邊界只釘單側或完全未釘（突變 BRC-13、BRC-14、BRC-22、BRC-23、API-9、API-10、DB-15 存活）**

**證據**：TCS §5.1 值域常數表逐項要求「測試與產品碼共用同一份常數；初值標未校準者以常數登記並以測試釘住」，並寫明儲存格 600、證據列下限 3、slug 1 至 30 字、PRD ≤1 MiB。實測：(a) BRC-13：`tests/test_research_gates.py:136` 只有 `"長" * 601` 的負例，沒有恰 600 的正例；(b) BRC-14：`MIN_EVIDENCE_ROWS` 改成 2，BR-C 五檔、orchestrator、全研究套件全綠，且 `tests/test_research_*.py` 無任何檔引用該常數或以「恰 2／3 列」斷言證據閘（模板／PRD §5.1.1 的下限沒有被測試釘）；(b2) BRC-22／BRC-23：`tests/test_research_*.py` 沒有任何案例斷言「score≥18 須含 § 錨點」與「`prd_anchor` 章號 1～14」的邊界，兩個突變各自在全研究套件全綠；(c) API-9：`ResearchApiIT.java:128,160` 與補充類 `ResearchEndpointsIT.java:188` 的 slug 違規案例都只有 `Bad_Slug`，console-api 輸入閘的長度上界在 console-api 側無 30／31 字測試（Bridge 側 AT-960-3-2 有長度案例、BRA-10 被殺）；(d) API-10：`ResearchEndpointsIT.java:395` 只有 `"字".repeat(400_000)`（約 1.2 MB，遠超上限），無 1 MiB／1 MiB+1 位元組的邊界組（Bridge 側 BRA-8 被殺）；(e) DB-15：`ResearchSchemaMigrationIT` 對 `rp_no` 只驗序列產生的合法值，未驗 3 位數被拒。**影響**：五處皆是「日後改動比較符號或常數不會有測試變紅」。**測試鑑別力缺口、非實作缺陷**。

**F-04（P2）AT-960-8-E-3 的「skipped:over_limit 落在事件 payload」（D-71′：`research.alert` kind=FETCH_SKIPPED_OVER_LIMIT）沒有任何測試釘住（突變 BRC-20 存活）**

**證據**：TCS AT-960-8-E-3 Then：「超出的候選不抓取、不截斷，各留一筆 `skipped:over_limit` 紀錄（落在事件 payload，不佔 `research_fetches` 的 outcome 列舉）」。D-71′ 把載體定為 `research.alert`。實測 BR-B 的 `plan_fetches` 單元層有釘（`test_research_fetch_security.py:973-975`），但「orchestrator 真的把它寫成事件」這一半只存在於 `orchestrator.py:697`，BR-C 的測試沒有任何一處引用 `FETCH_SKIPPED_OVER_LIMIT` 或斷言 skipped 事件。突變 BRC-20（`kind` 改名）在 BR-C 靶向、orchestrator、全研究套件皆綠＝SURVIVED。**影響**：AT 的 Then 子句（事件落地）無證據；D-71′ 的決定本身沒有回歸保護。**測試鑑別力缺口、非實作缺陷**（程式碼讀起來正確）。

## C　AT 逐條表（TCS §3 共 210 條）

### C.0　實作定位表（AC-960-n → 實作檔與已讀行號；C 表的 I-n 指此表）

| I-n | 實作定位 |
|---|---|
| I-1 | backend/src/main/resources/db/migration/V16__research_core.sql、V17__research_evidence.sql、V18__research_prd_review_gate.sql（V18:31-70 輪表 CHECK、V18:118-134 缺陷守衛、V17:24-43、V16:40-93） |
| I-2 | engine-bridge/app/routers/research.py:150-177（權杖→DB 關）、app/research/db.py（ResearchDb fail-loud）、app/research/outbox.py:226-240（BLOCKED_DB）、app/research/settings.py |
| I-3 | app/research/layout.py:30-52、app/routers/research.py:314-480（建立／重試初始化）、app/research/db.py:408-420、.gitignore:74 |
| I-4 | backend …/application/service/ResearchQueryService.java（events 上限 :49,:101）、domain/service/ResearchFlowPolicy.java:72-119、adapter/in/web/ResearchController.java |
| I-5 | …/infrastructure/config/SecurityConfig.java:99-110、application/service/ResearchCommandService.java:104-165、domain/exception/ErrorReasons.java（RESEARCH_*）、adapter/in/web/ResearchErrorDocs.java |
| I-6 | app/routers/research.py:493-535（PUT prd）、567-607（stages start／並行上限）、861-900（events） |
| I-7 | app/research/compile/playbooks.py:115-128,281-310、app/research/orchestrator.py:475-623（stage 鏈／看門狗）、compile/personas.py、compile/prompts.py |
| I-8 | app/research/fetch/allowlist.py:137-162、fetch/http.py:85-103,450-570、fetch/__init__.py:90-161、fetch/{arxiv,github,semantic_scholar,stackexchange}.py |
| I-9 | app/research/gates/evidence.py:37-38,103-147,474-483、gates/ingest.py、gates/schemas.py |
| I-10 | backend …/application/service/ResearchStreamService.java:72-160；frontend components/domain/research/EvidenceTimeline.tsx、lib/domain/research.ts:818-893 |
| I-11 | app/research/gates/prd_schema.py、orchestrator.py（_draft） |
| I-12 | app/research/gates/aggregate.py:63-119、gates/review_card.py、orchestrator.py:829-850（_review） |
| I-13 | app/research/fsm_ops.py:188-330、app/sdd_cli.py:333-376,432-562 |
| I-14 | app/routers/research.py:660-748（approve）、orchestrator.py:1149-1165（digest_problems）、app/research/export.py |
| I-15 | app/routers/research.py:387-480（reinit）、610-660（escalation 閘）、749-792（return）；backend ResearchCommandService.java:144-165；frontend GatekeeperPanel.tsx:159-164,488,683-790 |
| I-16 | frontend StudioPanel.tsx（RICH_EDIT_MAX_BYTES:54）、PrdOutline.tsx、PrdDiffView.tsx、MermaidBlock.tsx:23-32、lib/domain/research.ts:379-503 |
| I-17 | frontend StudioPanel.tsx（next/dynamic:21）、tests/e2e/research-studio-perf.mock.spec.ts、package.json |
| I-18 | frontend lib/nav/registry.ts:123-132、lib/help/{types,registry,states,research,research-workspace}.ts |
| I-19 | frontend ResearchListView.tsx、ResearchWorkspaceView.tsx、FlowStepper.tsx:25-30、lib/domain/research.ts:80-109,305-350 |
| I-20 | frontend components/layout/*（零差異）、FlowStepper.tsx／ResearchFlowHeader.tsx |
| I-21 | app/research/gates/reconcile.py、app/routers/research.py:793-808 |
| I-22 | app/mock_claude.py（研究劇本模式:154-170）、tests/fixtures/research/scripts/*.json |
| I-23 | （指令核對） |
| I-24 | （指令核對） |

### C.1　逐條表

欄位：AT｜層｜實作（I-n）｜自動測試定位（檔:行::測試名；括號為同 AT 測試案例數）｜單跑結果｜突變（擊殺該 AT 測試的 mutant）｜判定。「單跑結果」＝該 AT 底線形選到的 junit 案例在本回合分檔批跑（Bridge 21＋3 檔 -n 8、Gradle 9 類、vitest 全套）的各自結果；批跑指令與 rc 見 G。

| AT | 層 | 實作 | 自動測試定位 | 單跑結果 | 突變 | 判定 |
|---|---|---|---|---|---|---|
| AT-960-2-1 | pytest／Integration | I-2 | test_research_router.py:218::test_AT_960_2_1_without_a_dsn_every_research_endpoint_but_the_probe… (1) | 1/1 PASS | — | PASS |
| AT-960-2-2 | pytest／Integration | I-2 | test_research_router.py:257::test_AT_960_2_2_the_token_gate_comes_first_and_the_audit_never_hold… (1) | 1/1 PASS | BRA-5 | PASS |
| AT-960-2-3 | pytest／Unit | I-2 | test_research_settings.py:38::test_AT_960_2_3_the_write_token_is_checked_at_startup_like_the_si_t… (1) | 1/1 PASS | — | PASS |
| AT-960-2-4 | pytest／Integration | I-2 | test_research_db.py:194::test_AT_960_2_4_a_failed_connection_makes_every_write_method_raise (5) | 43/43 PASS | — | PASS |
| AT-960-2-5 | pytest／Integration | I-2 | test_research_db.py:474::test_AT_960_2_5_a_db_outage_blocks_the_stage_run_and_replay_loses_a… (3) | 4/4 PASS | — | PASS |
| AT-960-2-6 | pytest／Integration | I-2 | test_research_db.py:561::test_AT_960_2_6_the_call_order_is_file_then_outbox_then_db_then_done (4) | 12/12 PASS | — | PASS |
| AT-960-2-7 | pytest／Integration | I-2 | test_research_router.py:287::test_AT_960_2_7_capabilities_and_health_deep_share_a_fixed_info_shape (1) | 1/1 PASS | — | PASS |
| AT-960-2-E-1 | pytest／Unit | I-2 | test_research_settings.py:57::test_AT_960_2_E_1_the_defaults_are_the_documented_values (10) | 26/26 PASS | BRC-21 | PASS |
| AT-960-2-E-2 | pytest／Contract | I-2 | test_research_deploy_config.py:119::test_AT_960_2_E_2_the_real_deployment_files_pass_every_check (8) | 30/30 PASS | — | PASS |
| AT-960-3-1 | pytest／Integration | I-3 | test_research_router.py:315::test_AT_960_3_1_a_valid_request_creates_row_event_files_and_the_out… (2) | 4/4 PASS | BRA-10 | PASS |
| AT-960-3-2 | pytest／Unit | I-3 | test_research_layout.py:65::test_AT_960_3_2_a_bad_slug_is_a_422_sanitization_failure_and_adds_n… (3) | 13/13 PASS | BRA-10 | PASS |
| AT-960-3-3 | pytest／Integration | I-3 | test_research_router.py:380::test_AT_960_3_3_a_second_create_with_the_same_slug_is_409_and_touch… (1) | 2/2 PASS | — | PASS |
| AT-960-3-4 | pytest／Integration | I-3 | test_research_router.py:395::test_AT_960_3_4_a_failed_init_is_marked_and_only_retry_init_in_that… (2) | 4/4 PASS | — | PASS |
| AT-960-3-5 | pytest／Integration | I-3 | test_research_settings.py:193::test_AT_960_3_5_the_three_defaults_are_outside_the_monorepo_and_doc… (2) | 2/2 PASS | — | PASS |
| AT-960-3-E-1 | pytest／Unit | I-3 | test_research_layout.py:252::test_AT_960_3_E_1_rendering_the_same_row_twice_gives_identical_bytes (3) | 3/3 PASS | — | PASS |
| AT-960-6-1 | pytest／Integration | I-6 | test_research_router.py:481::test_AT_960_6_1_the_cursor_lives_in_the_db_and_survives_a_bridge_re… (1) | 1/1 PASS | — | PASS |
| AT-960-6-2 | pytest／Contract | I-6 | test_research_ast_locks.py:331::test_AT_960_6_2_no_advance_endpoint_exists_on_the_bridge (2) | 2/2 PASS | — | PASS |
| AT-960-6-3 | pytest／Integration | I-6 | test_research_router.py:505::test_AT_960_6_3_an_unmet_precondition_is_409_with_the_unmet_rules_a… (2) | 4/4 PASS | BRA-9 | PASS |
| AT-960-6-4 | pytest／Integration | I-6 | test_research_router.py:540::test_AT_960_6_4_a_second_start_on_one_project_is_409_and_seq_stays_… (4) | 8/8 PASS | BRA-6,BRA-9 | PASS |
| AT-960-6-5 | pytest／Integration | I-6 | test_research_router.py:618::test_AT_960_6_5_after_gate_0_every_write_action_is_409_spec_frozen (1) | 2/2 PASS | — | PASS |
| AT-960-6-6 | pytest／Integration | I-6 | test_research_router.py:637::test_AT_960_6_6_two_concurrent_puts_on_the_same_base_one_wins_and_o… (2) | 4/4 PASS | BRA-8 | PASS |
| AT-960-6-7 | pytest／Contract | I-6 | test_research_db.py:276::test_AT_960_6_7_every_update_sets_only_controlled_columns_of_a_cont… (7) | 7/7 PASS | — | PASS |
| AT-960-6-E-1 | pytest／Unit | I-6 | test_research_events.py:54::test_AT_960_6_E_1_eight_threads_writing_200_events_get_contiguous_u… (3) | 3/3 PASS | — | PASS |
| AT-960-7-1 | pytest／Unit | I-7 | test_research_compile.py:95::test_AT_960_7_1_each_role_gets_its_minimal_allowed_tools (3) | 5/5 PASS | BRC-18,BRC-19 | PASS |
| AT-960-7-2 | pytest／Unit | I-7 | test_research_compile.py:140::test_AT_960_7_2_manifest_matches_the_prompt_files_and_yaml_bytes (2) | 4/4 PASS | — | PASS |
| AT-960-7-3 | pytest／Unit | I-7 | test_research_compile.py:177::test_AT_960_7_3_every_step_is_bounded_and_self_contained (3) | 8/8 PASS | BRC-11 | PASS |
| AT-960-7-4 | pytest／Integration | I-7 | test_research_orchestrator.py:218::test_AT_960_7_4_research_run_row_snapshot_and_no_execution_tables_t… (1) | 2/2 PASS | — | PASS |
| AT-960-7-5 | pytest／Integration | I-7 | test_research_orchestrator.py:302::test_AT_960_7_5_a_bounded_stage_fails_with_its_exit_reason_and_keep… (2) | 5/5 PASS | BRC-8 | PASS |
| AT-960-7-6 | pytest／Integration | I-7 | test_research_router.py:983::test_AT_960_7_6_mock_only_mode_still_accepts_the_research_stage (1) | 2/2 PASS | — | PASS |
| AT-960-7-7 | pytest／Unit | I-7 | test_research_orchestrator.py:343::test_AT_960_7_7_flow_status_is_derived_from_runs_and_fsm_state_only (2) | 3/3 PASS | — | PASS |
| AT-960-7-E-1 | pytest／Integration | I-7 | test_research_orchestrator.py:380::test_AT_960_7_E_1_injected_source_text_never_reaches_a_prompt_or_pe… (1) | 1/1 PASS | — | PASS |
| AT-960-7-E-2 | pytest／Integration | I-7 | test_research_orchestrator.py:408::test_AT_960_7_E_2_bridge_secrets_never_reach_the_fake_claude_enviro… (1) | 2/2 PASS | — | PASS |
| AT-960-8-1 | pytest／Integration | I-8 | test_research_fetch_security.py:146::test_AT_960_8_1_only_normalised_arxiv_and_github_https_forms_pass (7) | 33/33 PASS | BRB-1,BRB-2,BRB-3,BRB-7,BRB-8 | PASS |
| AT-960-8-2 | pytest／Unit | I-8 | test_research_fetch_security.py:260::test_AT_960_8_2_a_host_that_resolves_to_a_non_public_address_is_den… (7) | 35/35 PASS | BRB-12,BRB-4,BRB-5 | PASS |
| AT-960-8-3 | pytest／Integration | I-8 | test_research_fetch_security.py:327::test_AT_960_8_3_the_connection_goes_only_to_the_first_validated_add… (5) | 5/5 PASS | — | PASS |
| AT-960-8-4 | pytest／Integration | I-8 | test_research_fetch_security.py:398::test_AT_960_8_4_allowed_hops_each_leave_a_record_and_the_terminal_r… (7) | 7/7 PASS | BRB-1,BRB-10,BRB-12,BRB-2,BRB-3 | PASS |
| AT-960-8-5 | pytest／Integration | I-8 | test_research_fetch_security.py:479::test_AT_960_8_5_each_failure_kind_is_recorded_on_its_own_and_nothin… (10) | 11/11 PASS | BRB-10,BRB-12 | PASS |
| AT-960-8-6 | pytest／Unit | I-8 | test_research_fetch_parsers.py:91::test_AT_960_8_6_the_golden_response_matches_the_golden_json_field_b… (16) | 55/55 PASS | BRB-14,BRB-15,BRB-20 | PASS |
| AT-960-8-7 | pytest／Integration | I-8 | test_research_fetch_security.py:648::test_AT_960_8_7_default_effective_intervals_equal_the_v_r9_values (13) | 13/13 PASS | BRB-13,BRB-6,BRB-9 | PASS |
| AT-960-8-8 | pytest／Contract | I-8 | test_research_capability.py:261::test_AT_960_8_8_the_real_tree_is_registered_one_to_one_and_has_no_p… (7) | 47/47 PASS | — | PASS |
| AT-960-8-9 | pytest／Integration | I-8 | test_research_router.py:695::test_AT_960_8_9_the_allowlist_is_env_base_plus_enabled_admin_entries (4) | 7/7 PASS | — | PASS |
| AT-960-8-E-1 | pytest／Integration | I-8 | test_research_fetch_security.py:894::test_AT_960_8_E_1_the_token_goes_out_only_as_an_authorization_heade… (2) | 2/2 PASS | — | PASS |
| AT-960-8-E-2 | pytest／Integration | I-8 | test_research_orchestrator.py:850::test_AT_960_8_E_2_the_stage_revalidates_the_web_layer_and_only_indu… (2) | 4/4 PASS | — | PASS |
| AT-960-8-E-3 | pytest／Unit | I-8 | test_research_fetch_security.py:966::test_AT_960_8_E_3_each_depth_level_caps_sources_per_layer_and_fetch… (4) | 6/6 PASS | BRB-16,BRB-17,BRB-18,BRB-19 | PASS |
| AT-960-9-1 | pytest／Unit | I-9 | test_research_gates.py:66::test_AT_960_9_1_the_golden_evidence_file_passes_every_rule (5) | 27/27 PASS | — | PASS |
| AT-960-9-2 | pytest／Unit | I-9 | test_research_gates.py:338::test_AT_960_9_2_the_matrix_layout_is_deterministic_and_follows_the_… (2) | 2/2 PASS | — | PASS |
| AT-960-9-3 | pytest／Unit | I-9 | test_research_gates.py:411::test_AT_960_9_3_citation_codes_equal_the_template_table_and_each_on… (1) | 1/1 PASS | — | PASS |
| AT-960-9-4 | pytest／Unit | I-9 | test_research_gates.py:211::test_AT_960_9_4_numbers_are_anchored_literally_or_after_normalisation (2) | 2/2 PASS | — | PASS |
| AT-960-9-5 | pytest／Integration | I-9 | test_research_gates.py:242::test_AT_960_9_5_a_second_research_run_adds_a_matrix_version_and_kee… (1) | 2/2 PASS | — | PASS |
| AT-960-9-6 | pytest／Unit | I-9 | test_research_gates.py:270::test_AT_960_9_6_license_pending_counts_gpl_family_and_unknown_licen… (1) | 1/1 PASS | — | PASS |
| AT-960-9-7 | pytest／Unit | I-9 | test_research_gates.py:282::test_AT_960_9_7_locators_are_normalised_and_duplicates_keep_a_refer… (1) | 1/1 PASS | — | PASS |
| AT-960-9-8 | pytest／Unit | I-9 | test_research_gates.py:205::test_AT_960_9_8_strength_follows_the_template_table (1) | 20/20 PASS | BRC-15,BRC-16,BRC-17 | PASS |
| AT-960-9-E-1 | pytest／Integration | I-9 | test_research_db.py:678::test_AT_960_9_E_1_ingested_rows_are_complete_and_equal_the_files (1) | 2/2 PASS | — | PASS |
| AT-960-9-E-2 | pytest／Unit | I-9 | test_research_gates.py:378::test_AT_960_9_E_2_each_matrix_row_equals_the_ingest_rows_cell_for_c… (1) | 1/1 PASS | — | PASS |
| AT-960-9-E-3 | pytest／Unit | I-9 | test_research_gates.py:300::test_AT_960_9_E_3_a_supplement_must_keep_every_previous_row_bit_for… (1) | 1/1 PASS | — | PASS |
| AT-960-10-3 | pytest／Integration | I-10 | test_research_events.py:184::test_AT_960_10_3_rest_and_stream_replay_equal_the_db_rows_and_the_p… (3) | 3/3 PASS | — | PASS |
| AT-960-11-1 | pytest／Integration | I-11 | test_research_orchestrator.py:254::test_AT_960_11_1_draft_run_saves_prd_and_adr_and_moves_the_cursor_t… (1) | 2/2 PASS | — | PASS |
| AT-960-11-2 | pytest／Unit | I-11 | test_research_gates.py:436::test_AT_960_11_2_the_fixture_prd_passes_and_each_structural_defect_… (3) | 3/3 PASS | — | PASS |
| AT-960-11-3 | pytest／Unit | I-11 | test_research_gates.py:461::test_AT_960_11_3_citations_must_exist_in_the_matrix_and_the_researc… (1) | 1/1 PASS | — | PASS |
| AT-960-11-4 | pytest／Unit | I-11 | test_research_gates.py:472::test_AT_960_11_4_every_feature_has_boundaries_and_every_us_and_ac_i… (1) | 1/1 PASS | — | PASS |
| AT-960-11-5 | pytest／Integration | I-11 | test_research_orchestrator.py:430::test_AT_960_11_5_a_failed_draft_keeps_the_cursor_on_topic_and_store… (1) | 1/1 PASS | — | PASS |
| AT-960-11-E-1 | pytest／Unit | I-11 | test_research_compile.py:220::test_AT_960_11_E_1_draft_inputs_carry_no_review_material_or_scoring… (2) | 4/4 PASS | — | PASS |
| AT-960-11-E-2 | pytest／Unit | I-11 | test_research_gates.py:489::test_AT_960_11_E_2_ids_are_rule_7_numeric_without_r2p_prefixes_or_d… (1) | 1/1 PASS | — | PASS |
| AT-960-12-1 | pytest／Unit | I-12 | test_research_gates.py:522::test_AT_960_12_1_w100_and_the_exact_two_decimal_display (3) | 11/11 PASS | BRC-5 | PASS |
| AT-960-12-2 | pytest／Unit | I-12 | test_research_gates.py:573::test_AT_960_12_2_the_four_conditions_each_veto_a_pass_on_their_own (2) | 2/2 PASS | BRC-1,BRC-3,BRC-4 | **P2（F-01）**：測試綠，但缺「最低維度恰 60 ⇒ PASS」正例；突變 BRC-2 存活 |
| AT-960-12-3 | pytest／Integration | I-12 | test_research_orchestrator.py:526::test_AT_960_12_3_invalid_reviewer_output_writes_no_round_and_keeps_… (1) | 2/2 PASS | BRC-24 | PASS |
| AT-960-12-4 | pytest／Integration | I-12 | test_research_orchestrator.py:762::test_AT_960_12_4_reviewers_are_four_independent_steps_with_a_clean_… (1) | 2/2 PASS | — | PASS |
| AT-960-12-5 | pytest／Integration | I-12 | test_research_db.py:781::test_AT_960_12_5_defect_status_moves_only_along_the_one_way_table (2) | 3/3 PASS | BRC-25 | PASS |
| AT-960-12-6 | pytest／Integration | I-12 | test_research_orchestrator.py:465::test_AT_960_12_6_a_precheck_veto_skips_the_reviewers_and_counts_aga… (1) | 2/2 PASS | — | PASS |
| AT-960-12-7 | pytest／Integration | I-12 | test_research_orchestrator.py:689::test_AT_960_12_7_a_human_save_makes_the_old_pass_stale_and_review_b… (1) | 2/2 PASS | BRC-12 | PASS |
| AT-960-12-8 | pytest／Integration | I-12 | test_research_orchestrator.py:597::test_AT_960_12_8_cancel_quota_and_restart_leave_no_round_and_keep_t… (2) | 4/4 PASS | BRC-24 | PASS |
| AT-960-12-9 | pytest／Integration | I-12 | test_research_db.py:940::test_AT_960_12_9_the_round_result_is_on_disk_before_gate_and_one_tr… (4) | 8/8 PASS | — | PASS |
| AT-960-12-E-1 | pytest／Contract | I-12 | test_research_schema_parity.py:78::test_AT_960_12_E_1_exactly_nine_marked_json_blocks_exist (4) | 8/8 PASS | — | PASS |
| AT-960-12-E-2 | pytest／Integration | I-12 | test_research_orchestrator.py:791::test_AT_960_12_E_2_fail3_script_escalates_on_the_third_round (2) | 4/4 PASS | — | PASS |
| AT-960-12-E-3 | pytest／Integration | I-12 | test_research_gates.py:613::test_AT_960_12_E_3_the_negative_control_84_95_fails_and_85_00_passes (2) | 2/2 PASS | BRC-1 | PASS |
| AT-960-12-E-4 | pytest／Integration | I-12 | test_research_orchestrator.py:722::test_AT_960_12_E_4_review_in_human_pending_only_records_to_the_db (1) | 2/2 PASS | BRC-12 | PASS |
| AT-960-12-E-5 | pytest／Integration | I-12 | test_research_orchestrator.py:957::test_AT_960_12_E_5_revise_after_a_human_resume_runs_one_round_and_a… (2) | 4/4 PASS | BRC-7 | PASS |
| AT-960-13-1 | pytest／Unit | I-13 | test_sdd_cli.py:387::test_AT_960_13_1_the_five_existing_verbs_stay_and_the_research_tabl… (4) | 16/16 PASS | — | PASS |
| AT-960-13-2 | pytest／Unit | I-13 | test_sdd_cli.py:588::test_AT_960_13_2_the_flag_and_value_matrix_cell (3) | 206／206 PASS | BRA-3,BRA-4 | PASS |
| AT-960-13-3 | pytest／Integration | I-13 | test_research_ast_locks.py:315::test_AT_960_13_3_only_one_helper_builds_a_show_without_must_exist (7) | 23/23 PASS | BRA-2 | PASS |
| AT-960-13-4 | pytest／Contract | I-13 | test_research_fsm_ops.py:267::test_AT_960_13_4_every_mirror_edge_is_a_happy_path_edge (5) | 8/8 PASS | — | PASS |
| AT-960-13-5 | pytest／Integration | I-13 | test_research_fsm_ops.py:352::test_AT_960_13_5_the_child_environment_is_fixed_and_only_the_outer_… (2) | 2/2 PASS | BRA-1 | PASS |
| AT-960-13-6 | pytest／Integration | I-13 | test_research_fsm_ops.py:414::test_AT_960_13_6_three_fails_end_in_escalation_never_in_auto_recovery (3) | 6/6 PASS | — | PASS |
| AT-960-13-7 | pytest／Contract | I-13 | test_research_ast_locks.py:257::test_AT_960_13_7_the_whole_app_tree_satisfies_every_rule (5) | 5/5 PASS | — | PASS |
| AT-960-13-8 | pytest／Integration | I-13 | test_research_fsm_ops.py:460::test_AT_960_13_8_after_a_human_resume_the_budget_is_not_reset (1) | 4/4 PASS | BRA-1 | PASS |
| AT-960-13-9 | pytest／Integration | I-13 | test_research_fsm_view.py:107::test_AT_960_13_9_the_projection_adds_retry_gates_and_leaves_retry_h… (4) | 12/12 PASS | — | PASS |
| AT-960-13-E-1 | pytest／Unit | I-13 | test_research_ast_locks.py:238::test_AT_960_13_E_1_each_synthetic_violation_is_reported_with_its_rule (3) | 21/21 PASS | — | PASS |
| AT-960-13-E-2 | pytest／Unit | I-13 | test_research_fsm_ops.py:524::test_AT_960_13_E_2_a_malformed_or_contradictory_gate_output_is_502_… (4) | 25/25 PASS | — | PASS |
| AT-960-13-E-3 | pytest／Integration | I-13 | test_research_fsm_ops.py:601::test_AT_960_13_E_3_a_pass_in_human_pending_fails_and_fails_only_mov… (1) | 2/2 PASS | — | PASS |
| AT-960-14-1 | pytest／Integration | I-14 | test_research_approve.py:159::test_AT_960_14_1_approval_freezes_four_docs_and_the_record_equals_s… (1) | 2/2 PASS | — | PASS |
| AT-960-14-2 | pytest／Integration | I-14 | test_research_approve.py:252::test_AT_960_14_2_the_first_unmet_check_wins_and_nothing_is_written (1) | 2/2 PASS | BRC-9 | PASS |
| AT-960-14-3 | pytest／Unit | I-14 | test_research_approve.py:301::test_AT_960_14_3_approver_names_and_reserved_words (3) | 3/3 PASS | BRC-10,BRC-9 | PASS |
| AT-960-14-5 | pytest／Integration | I-14 | test_research_approve.py:343::test_AT_960_14_5_returns_share_the_three_try_budget_and_the_third_e… (2) | 4/4 PASS | — | PASS |
| AT-960-14-6 | pytest／Integration | I-14 | test_research_approve.py:401::test_AT_960_14_6_two_concurrent_approvals_one_wins_and_the_other_is… (1) | 2/2 PASS | — | PASS |
| AT-960-14-7 | pytest／Integration | I-14 | test_research_approve.py:429::test_AT_960_14_7_the_regression_check_state_is_visited_only_when_sh… (1) | 2/2 PASS | — | PASS |
| AT-960-14-8 | pytest／Integration | I-14 | test_research_approve.py:513::test_AT_960_14_8_gate_0_never_goes_through_the_freeze_router (1) | 1/1 PASS | — | PASS |
| AT-960-14-9 | pytest／Integration | I-14 | test_research_approve.py:463::test_AT_960_14_9_after_gate_0_writes_are_409_and_reconcile_shows_ex… (1) | 2/2 PASS | — | PASS |
| AT-960-14-E-2 | pytest／Integration | I-14 | test_research_approve.py:489::test_AT_960_14_E_2_gate_0_runs_one_automatic_reconcile_and_a_prior_… (1) | 2/2 PASS | — | PASS |
| AT-960-15-5 | pytest／Integration | I-15 | test_research_router.py:598::test_AT_960_15_5_after_escalation_only_reads_the_fsm_and_never_writ… (1) | 2/2 PASS | — | PASS |
| AT-960-15-6 | pytest／Integration | I-15 | test_research_router.py:581::test_AT_960_15_6_in_escalation_new_reviews_and_automatic_revisions_… (1) | 2/2 PASS | BRA-1 | PASS |
| AT-960-15-8 | pytest／Integration | I-15 | test_research_router.py:779::test_AT_960_15_8_generation_next_abandons_the_old_key_in_one_transa… (1) | 2/2 PASS | BRA-1 | PASS |
| AT-960-15-E-1 | pytest／Integration | I-15 | test_research_router.py:849::test_AT_960_15_E_1_a_failed_new_key_leaves_the_db_ahead_and_retry_i… (1) | 2/2 PASS | — | PASS |
| AT-960-21-1 | pytest／Integration | I-21 | test_research_reconcile.py:87::test_AT_960_21_1_six_checks_report_drift_with_both_digests_and_fix_… (1) | 2/2 PASS | — | PASS |
| AT-960-21-2 | pytest／Unit | I-21 | test_research_reconcile.py:147::test_AT_960_21_2_legal_rows_are_true (3) | 24/24 PASS | — | PASS |
| AT-960-21-3 | pytest／Integration | I-21 | test_research_reconcile.py:176::test_AT_960_21_3_an_unreadable_state_file_is_not_evaluable_and_neve… (1) | 4/4 PASS | — | PASS |
| AT-960-21-4 | pytest／Integration | I-21 | test_research_reconcile.py:195::test_AT_960_21_4_gate_0_runs_exactly_one_reconcile_and_p95_stays_un… (2) | 3/3 PASS | — | PASS |
| AT-960-21-5 | pytest／Contract | I-21 | test_research_reconcile.py:263::test_AT_960_21_5_the_scanner_reports_read_samples_and_its_scope_is_… (3) | 4/4 PASS | — | PASS |
| AT-960-22-1 | pytest／Unit | I-22 | test_mock_claude_research.py:55::test_AT_960_22_1_default_mode_output_is_byte_identical_to_the_golden (8) | 17/17 PASS | — | PASS |
| AT-960-1-1 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:457::AT_960_1_1_flywayHistoryObjectsAndGuardWiring (1) | 1/1 PASS | DB-11,DB-3,DB-9 | PASS |
| AT-960-1-2 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:537::AT_960_1_2_appendOnlyTablesRejectUpdateAndDelete (1) | 1/1 PASS | DB-3 | PASS |
| AT-960-1-3 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:595::AT_960_1_3_sourcesChecksAndVerificationUpgrade (1) | 1/1 PASS | DB-10,DB-7 | PASS |
| AT-960-1-4 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:672::AT_960_1_4_allowlistImmutableColumnsAndChecks (1) | 1/1 PASS | DB-8 | PASS |
| AT-960-1-5 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:743::AT_960_1_5_projectsSequenceSlugAndUniqueness (1) | 1/1 PASS | DB-9 | PASS |
| AT-960-1-6 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:833::AT_960_1_6_reviewRoundsExactNumericsAndPassedCheck (1) | 1/1 PASS | DB-1,DB-2 | PASS |
| AT-960-1-7 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:926::AT_960_1_7_scoresDefectsDecisionsAndPrdVersions (1) | 1/1 PASS | — | PASS |
| AT-960-1-8 | JUnit／Contract | I-1 | ResearchSchemaMigrationIT.java:1044::AT_960_1_8_everyTimeColumnHasTimeZone (1) | 1/1 PASS | — | PASS |
| AT-960-1-9 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1075::AT_960_1_9_stageRunsArtifactsAndTheActiveRunIndex (1) | 1/1 PASS | DB-11 | PASS |
| AT-960-1-E-3 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1158::AT_960_1_E_3_fetchesAndEvidenceItemsChecks (1) | 1/1 PASS | — | PASS |
| AT-960-1-E-4 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1245::AT_960_1_E_4_defectStatusIsOneWay (1) | 1/1 PASS | DB-13,DB-14 | PASS |
| AT-960-1-E-5 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1307::AT_960_1_E_5_sourceVerificationOnlyGoesUp (1) | 1/1 PASS | DB-12 | PASS |
| AT-960-1-E-6 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1353::AT_960_1_E_6_controlledUpdateGuardMatrix (1) | 1/1 PASS | DB-3 | PASS |
| AT-960-1-E-7 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1474::AT_960_1_E_7_reviewRoundCheckGroup (1) | 1/1 PASS | DB-5,DB-6 | PASS |
| AT-960-1-E-8 | JUnit／Integration | I-1 | ResearchSchemaMigrationIT.java:1560::AT_960_1_E_8_fetchNumberingAndWebSearchMutualExclusion (1) | 1/1 PASS | — | PASS |
| AT-960-4-1 | JUnit／Integration | I-4 | ResearchApiIT.java:107::AT_960_4_1_theCreateGateRejectsEveryViolationWith400AndTouchesNeith… (2) | 2/2 PASS | API-8 | PASS |
| AT-960-4-2 | JUnit／Integration | I-4 | ResearchApiIT.java:174::AT_960_4_2_theFlowHasFiveFixedStepsAndTheCursorComesFromTheDatabase… (1) | 1/1 PASS | — | PASS |
| AT-960-4-3 | JUnit／Integration | I-4 | ResearchApiIT.java:208::AT_960_4_3_recordsAuditReturnsR1ToR14WithCountsAndTheMissingClasses… (1) | 1/1 PASS | — | PASS |
| AT-960-4-4 | JUnit／Integration | I-4 | ResearchApiIT.java:243::AT_960_4_4_unmetPreconditionsAreAConflictWithTheBridgeReasonAndDeta… (1) | 1/1 PASS | — | PASS |
| AT-960-4-5 | JUnit／Integration | I-4 | ResearchApiIT.java:272::AT_960_4_5_theSecondConcurrentStageStartIs409StageConflictAndConsol… (1) | 1/1 PASS | — | PASS |
| AT-960-4-6 | JUnit／Integration | I-4 | ResearchApiIT.java:310::AT_960_4_6_cancelReconcileArchiveAndRestoreAreOperatorWritesWithOne… (1) | 1/1 PASS | — | PASS |
| AT-960-4-7 | JUnit／Integration | I-4 | ResearchApiIT.java:347::AT_960_4_7_reviewRoundsDescribeOnlyCompletedRoundsWithoutStatusAndW… (2) | 2/2 PASS | — | PASS |
| AT-960-4-8 | JUnit／Integration | I-4 | ResearchApiIT.java:438::AT_960_4_8_theFsmViewKeepsTheExistingRetryHistoryAddsThreeGatesAndC… (1) | 1/1 PASS | — | PASS |
| AT-960-4-E-1 | JUnit／Contract | I-4 | ResearchArchTest.java:72::AT_960_4_E_1_thePersistenceResearchPackageHasZeroWriteStatementsAnd… (5) | 5/5 PASS | — | PASS |
| AT-960-4-E-2 | JUnit／Unit | I-4 | ResearchFlowPolicyTest.java:87::AT_960_4_E_2_effectiveIsTableDrivenAndNeverDerivesASecondTruthForTh… (6) | 6/6 PASS | API-1,API-2,API-3,API-4,API-5 | PASS |
| AT-960-5-1 | JUnit／Integration | I-5 | RbacIT.java:339::AT_960_5_1_adminOnlyResearchEndpointsAre401ForAnonymousAnd403ForVie… (1) | 1/1 PASS | API-6,API-7 | PASS |
| AT-960-5-2 | JUnit／Integration | I-5 | RbacIT.java:370::AT_960_5_2_generalResearchWritesNeedOperatorAndEveryResearchGetIsOp… (1) | 1/1 PASS | — | PASS |
| AT-960-5-3 | JUnit／Contract | I-5 | RbacIT.java:448::AT_960_5_3_everyResearchAdminRuleSitsBeforeTheGenericRuleAndTheExis… (1) | 1/1 PASS | API-6,API-7 | PASS |
| AT-960-5-4 | JUnit／Integration | I-5 | ResearchApiIT.java:491::AT_960_5_4_theAllowlistApiLetsOnlyAdminAddAndDisableAndEveryWriteLe… (1) | 1/1 PASS | API-7 | PASS |
| AT-960-5-5 | JUnit／Contract | I-5 | OpenApiIT.java:939::AT_960_5_5_theResearchPathsHaveExactlyTheContractOperationsAndOpera… (2) | 2/2 PASS | — | PASS |
| AT-960-5-6 | JUnit／Contract | I-5 | ResearchReasonsTest.java:109::AT_960_5_6_theBackendConstantsAreTheEighteenP0ReasonsPlusTheThreeKn… (6) | 6/6 PASS | — | PASS |
| AT-960-5-E-1 | JUnit／Unit | I-5 | BridgeHttpAdapterResearchTest.java:102::AT_960_5_E_1_everyWriteCarriesTheTokenAndTheTraceHeaderAndPostsTheB… (7) | 7/7 PASS | — | PASS |
| AT-960-10-1 | JUnit／Integration | I-10 | ResearchStreamIT.java:78::AT_960_10_1_theStreamCarriesEveryPushedEventInStrictlyIncreasingSeq… (2) | 2/2 PASS | API-14 | PASS |
| AT-960-10-2 | JUnit／Integration | I-10 | ResearchStreamIT.java:158::AT_960_10_2_reconnectingInsideTheBufferReplaysTheMissedEventsExactl… (6) | 6/6 PASS | API-13,API-14,API-15 | PASS |
| AT-960-14-4 | JUnit／Integration | I-14 | ResearchApiIT.java:563::AT_960_14_4_theApproverIsAlwaysTheJwtSubjectAndAForgedApproverInThe… (1) | 1/1 PASS | API-12,API-6 | PASS |
| AT-960-14-E-1 | JUnit／Integration | I-14 | ResearchApiIT.java:600::AT_960_14_E_1_everyBridgeFailureIsRelayedWithItsStatusAndReasonVerb… (2) | 2/2 PASS | API-6 | PASS |
| AT-960-15-7 | JUnit／Integration | I-15 | ResearchApiIT.java:676::AT_960_15_7_getFsmRelaysTheBridgeSddFsmStateGoldenFileInSddFsmState… (1) | 1/1 PASS | — | PASS |
| AT-960-15-9 | JUnit／Integration | I-15 | RbacIT.java:501::AT_960_15_9_reinitWithGenerationNextIsAdminOnlyInTheServiceLayerWhi… (1) | 1/1 PASS | API-11 | PASS |
| AT-960-15-E-2 | JUnit／Integration | I-15 | ResearchApiIT.java:698::AT_960_15_E_2_reinitNextRequiresAReasonUsesOnlyTheJwtSubjectAsDecid… (1) | 1/1 PASS | — | PASS |
| AT-960-10-4 | vitest／Integration | I-10 | EvidenceTimeline.test.tsx:173::AT_960_10_4 動態欄對外部文字原樣純文字顯示 (5) | 4/4 PASS | — | PASS |
| AT-960-10-5 | vitest／Integration | I-10 | EvidenceTimeline.test.tsx:247::AT_960_10_5 頁面重開由 REST 重建；SSE 重連首筆 id 不連續即全量重抓並去重合併 (15) | 13/13 PASS | FB-3,FB-4 | PASS |
| AT-960-10-6 | vitest／Integration | I-10 | EvidenceMatrixTable.test.tsx:62::AT_960_10_6 技術優缺點矩陣：只列有證據列的候選，每格帶 [E-NNN] 連結且目標列存在 (15) | 13/13 PASS | FB-8 | PASS |
| AT-960-10-7 | vitest／Unit | I-10 | EvidenceTimeline.test.tsx:478::AT_960_10_7 事件自 emitted_at 到 rendered_at 的延遲量測函式 (6) | 5/5 PASS | — | PASS |
| AT-960-10-8 | vitest／Integration | I-10 | EvidenceTimeline.test.tsx:588::AT_960_10_8 收到 research.replay_gap 訊號即全量重抓並與後續 SSE 去重合併，訊號本身不顯示為事件 (4) | 3/3 PASS | FB-1,FB-4 | PASS |
| AT-960-15-1 | vitest／Integration | I-15 | GatekeeperPanel.test.tsx:172::AT_960_15_1 ESCALATION 區塊內容與沒有任何恢復動詞按鈕 (2) | 3/3 PASS | — | PASS |
| AT-960-15-2 | vitest／Integration | I-15 | GatekeeperPanel.test.tsx:216::AT_960_15_2 SSE 重播造成重複事件時同一待處理項只有一個彈窗 (3) | 2/2 PASS | — | PASS |
| AT-960-15-3 | vitest／Integration | I-15 | GatekeeperPanel.test.tsx:259::AT_960_15_3 VIEWER 可讀 ESCALATION 內容但所有決定按鈕停用 (2) | 1/1 PASS | — | PASS |
| AT-960-15-4 | vitest／Integration | I-15 | GatekeeperPanel.test.tsx:275::AT_960_15_4 ESCALATION 區塊兩個動作 (4) | 3/3 PASS | FC-4 | PASS |
| AT-960-16-1 | vitest／Integration | I-16 | PrdOutline.test.tsx:46::AT_960_16_1 目錄由標題與 r2p:section 錨點導出 (37) | 29/29 PASS | — | PASS |
| AT-960-16-2 | vitest／Integration | I-16 | PrdDiffView.test.tsx:69::AT_960_16_2 Diff 行級、A→B 與 B→A 互為反向、與確定性比對相同，凍結版可比對不可編輯 (15) | 13/13 PASS | FC-8 | PASS |
| AT-960-16-3 | vitest／Integration | I-16 | MermaidBlock.test.tsx:40::AT_960_16_3 Mermaid 嚴格模式渲染、錯誤退回原始碼、逾時退回原始碼 (11) | 9/9 PASS | FC-2,FC-3 | PASS |
| AT-960-16-4 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:398::AT_960_16_4 雷達圖四軸等於 DB 分數並附等效文字表，缺陷卡排序與定位 (4) | 3/3 PASS | — | PASS |
| AT-960-16-5 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:470::AT_960_16_5 動作區矩陣：未通過、通過、非 ADMIN、escalated、人工恢復後的按鈕啟停與說明 (9) | 8/8 PASS | FC-4 | PASS |
| AT-960-16-6 | vitest／Integration | I-16 | StudioPanel.test.tsx:435::AT_960_16_6 儲存產生新 HUMAN 版本、舊審查標過期、離開有未儲存提示 (9) | 8/8 PASS | — | PASS |
| AT-960-16-7 | vitest／Integration | I-16 | StudioPanel.test.tsx:648::AT_960_16_7 凍結版與 VIEWER 的編輯器唯讀，儲存、迭代、核准皆停用 (4) | 3/3 PASS | — | PASS |
| AT-960-16-8 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:553::AT_960_16_8 Gate 0 確認對話框內容、退回需理由、焦點陷阱與歸還 (8) | 7/7 PASS | FC-6 | PASS |
| AT-960-16-9 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:671::AT_960_16_9 Gate 0 等待中顯示已等待小時數，滿 72 小時顯示提醒橫幅（純前端、假時鐘、零寫入） (2) | 5/5 PASS | — | PASS |
| AT-960-16-E-1 | vitest／Integration | I-16 | StudioPanel.test.tsx:730::AT_960_16_E_1 PRD 預覽不渲染原始 HTML，外部連結帶 noopener noreferrer (5) | 4/4 PASS | — | PASS |
| AT-960-16-E-2 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:728::AT_960_16_E_2 審查狀態只由 stage run 與事件決定：進行中聽 research.run，輪完成才顯示分數與判定，… (6) | 5/5 PASS | — | PASS |
| AT-960-16-E-3 | vitest／Integration | I-16 | GatekeeperPanel.test.tsx:824::AT_960_16_E_3 「第 n 輪」取自輪表列數，並以 FSM 重試史筆數對照「目前世代的未通過輪數加 humanReturnC… (4) | 8/8 PASS | FC-5 | PASS |
| AT-960-16-E-4 | vitest／Unit | I-16 | research.test.ts:394::AT_960_16_E_4 剩餘審查預算＝max(0, 3 − currentCount)，來源只取 FSM 視圖的 currentC… (4) | 3/3 PASS | FA-3 | PASS |
| AT-960-17-2 | vitest／Integration | I-17 | StudioPanel.test.tsx:806::AT_960_17_2 超過 200KB 降級為純文字預覽並說明原因，畫面不凍結 (6) | 5/5 PASS | FC-1 | PASS |
| AT-960-17-3 | vitest／Contract | I-17 | MermaidBlock.test.tsx:292::AT_960_17_3 mermaid 只經動態載入、不進首屏 chunk；diff 只在 Diff 模式載入 (4) | 3/3 PASS | — | PASS |
| AT-960-17-E-1 | vitest／Unit | I-17 | research.test.ts:497::AT_960_17_E_1 diffLines：確定性、反向對稱與 200KB 計算時間（無瀏覽器全域） (4) | 5/5 PASS | — | PASS |
| AT-960-18-1 | vitest／Unit | I-18 | research-nav.test.ts:107::AT_960_18_1 登記表恰多一列 research（欄位逐值、唯一性、icon 互異、href 對應真路由、match 互斥） (4) | 3/3 PASS | FA-9 | PASS |
| AT-960-18-2 | vitest／Unit | I-18 | research-nav.test.ts:167::AT_960_18_2 說明三道鎖：HELP_ROUTES、HELP_PAGES、頁檔雙向一致，PENDING 仍空，說明文字過 lint (5) | 4/4 PASS | — | PASS |
| AT-960-18-3 | vitest／Unit | I-18 | research-nav.test.ts:236::AT_960_18_3 狀態詞表 researchFlow：說明鍵、來源鍵與 flow_status／flow_phase 詞彙常數的… (4) | 3/3 PASS | — | PASS |
| AT-960-18-4 | vitest／Integration | I-18 | ToolsRegion.test.tsx:305::AT_960_18_4 研發工作流入口（底部 Tab 不含、側欄含） (1) | 9/9 PASS | FA-8,FA-9 | PASS |
| AT-960-18-5 | vitest／Unit | I-18 | nav-consolidation.test.ts:155::AT_960_18_5 既有導覽整併測試只改預期值：登記表十列、側欄九項（研發工作流在專案管理之後、執行中心之前）；對照組啟用 imp… (1) | 1/1 PASS | — | PASS |
| AT-960-18-E-1 | vitest／Unit | I-18 | research-nav.test.ts:148::AT_960_18_E_1 登記表檢查函式對違規樣本回報 (2) | 1/1 PASS | — | PASS |
| AT-960-19-1 | vitest／Integration | I-19 | ResearchListView.test.tsx:57::AT_960_19_1 清單：空狀態、新建入口、VIEWER 停用、每列內容、三態 (22) | 18/18 PASS | — | PASS |
| AT-960-19-2 | vitest／Integration | I-19 | ResearchListView.test.tsx:362::AT_960_19_2 新建對話框：zod 驗證逐欄顯示且不送出、代號自動產生可改、檢索深度三值、Web 層停用 (14) | 22/22 PASS | FA-11 | PASS |
| AT-960-19-3 | vitest／Unit | I-19 | FlowStepper.test.tsx:33::AT_960_19_3 FlowStepper 恆五項，狀態與可及名稱含狀態文字 (12) | 19/19 PASS | FD-1,FD-5,FD-7 | PASS |
| AT-960-19-4 | vitest／Integration | I-19 | ResearchWorkspaceView.test.tsx:125::AT_960_19_4 網址 step 超前導回游標所在步；已完成步驟為唯讀檢視 (10) | 16/16 PASS | — | PASS |
| AT-960-19-5 | vitest／Integration | I-19 | ResearchWorkspaceView.test.tsx:209::AT_960_19_5 P0 步驟 3 至 5 為占位面板：說明、唯讀、無寫入、回游標步連結，不假裝有執行中心連結 (4) | 8/8 PASS | — | PASS |
| AT-960-19-6 | vitest／Integration | I-19 | ResearchWorkspaceView.test.tsx:265::AT_960_19_6 VIEWER 於每個步驟都可讀，所有寫入與推進動作停用且 title 為權限不足 (3) | 7/7 PASS | — | PASS |
| AT-960-19-7 | vitest／Integration | I-19 | TopicPanel.test.tsx:80::AT_960_19_7 議題面板：環境閘（mock-only、Web 層、探針） (22) | 18/18 PASS | FB-7,FB-8 | PASS |
| AT-960-19-8 | vitest／Integration | I-19 | AllowlistDialog.test.tsx:103::AT_960_19_8 研究來源設定：僅 ADMIN 看得到入口 (17) | 12/12 PASS | FB-6,FC-7 | PASS |
| AT-960-19-E-1 | vitest／Unit | I-19 | research.test.ts:100::AT_960_19_E_1 五步列與可達性（表驅動；純函式） (4) | 3/3 PASS | FA-1,FA-10,FA-2 | PASS |
| AT-960-19-E-2 | vitest／Integration | I-19 | ResearchWorkspaceView.test.tsx:320::AT_960_19_E_2 離開再回來：游標取自 API 而非瀏覽器儲存，已存產物完整 (3) | 4/4 PASS | — | PASS |
| AT-960-20-1 | vitest／Integration | I-20 | ResearchFlowHeader.test.tsx:56::AT_960_20_1 頁首列三個區塊：切換下拉、狀態燈、Token 速率與預算 (14) | 22/22 PASS | — | PASS |
| AT-960-20-2 | vitest／Unit | I-20 | research.test.ts:225::AT_960_20_2 狀態燈窮舉表（優先序 Escalated＞Healing＞Running＞Paused＞Idle） (3) | 3/3 PASS | — | PASS |
| AT-960-20-3 | vitest／Unit | I-20 | research.test.ts:294::AT_960_20_3 Token 速率（近五分鐘增量除以五）與預算警示 (4) | 3/3 PASS | — | PASS |
| AT-960-21-6 | vitest／Integration | I-21 | ResearchWorkspaceView.test.tsx:370::AT_960_21_6 漂移橫幅：以資料庫為準、紅色提示檔名、不送出任何寫入請求 (7) | 6/6 PASS | — | PASS |
| AT-960-1-E-1 | 指令核對／Gate | I-1 | —（無測試案例） | — | — | PASS（指令核對：gradlew 5 類 37 tests rc 0；diff 僅版本清單＋BackupJobMigrationIT 兩個查詢條件） |
| AT-960-1-E-2 | 指令核對／Gate | I-1 | —（無測試案例） | — | — | PASS（指令核對：`git diff --name-status 25c66981 0b678757 -- db/migration` 恰 3 行 A＝V16／V17／V18，無 V19） |
| AT-960-3-6 | 指令核對／Gate | I-3 | —（無測試案例） | — | — | PASS（指令核對：check-ignore rc 0 命中 `.gitignore:74 /my-project/`；`AgentConsole/my-project-x/a.txt` rc 1） |
| AT-960-5-7 | 指令核對／Gate | I-5 | —（無測試案例） | — | — | PASS（指令核對：endpoints.test.ts＋si.endpoints.test.ts 在 vitest 全套 2,191 全綠；兩檔 diff 只動預期值與釘值字串 -2/+2） |
| AT-960-17-1 | Playwright／E2E | I-17 | StudioPanel.lazy.test.tsx:246::AT_960_17_1 首屏補強：Markdown 渲染管線不在頁殼的靜態 import 圖裡（只經 StudioPanel 的動態 … (10) | 6/6 PASS | FD-6 | PASS（Playwright `research-studio-perf.mock.spec.ts -g AT_960_17_1` 與 a11y＋perf 共 11 案 passed；量測值見 A；vitest 側 StudioPanel 同名測試亦綠） |
| AT-960-17-4 | 指令核對／Gate | I-17 | —（無測試案例） | — | — | PASS（指令核對：package.json 恰加 diff 8.0.4＋mermaid 12.2.0；lock 根依賴同；僅 891d3d8b 動兩檔；`npm ci --dry-run` rc 0；無第二個 md 編輯器） |
| AT-960-20-4 | 指令核對／Gate | I-20 | —（無測試案例） | — | — | PASS（指令核對：layout diff 僅 ToolsRegion.test.tsx；字樣掃描只命中 ResearchFlowHeader.test.tsx:123 的反向斷言 regex＝TCS 掃描字面自我命中，P4 F-13） |
| AT-960-22-2 | Playwright／E2E | I-22 | —（無測試案例） | — | — | NOT-EVALUABLE：`tests/e2e/research-docker.stack.ts` 不存在（§5.7「整合 P0」＝主控 Docker 步驟，非九包） |
| AT-960-22-3 | Playwright／E2E | I-22 | —（無測試案例） | — | — | NOT-EVALUABLE：同 22-2（Docker 全棧 E2E 尚未交付） |
| AT-960-22-4 | Playwright／E2E | I-22 | —（無測試案例） | — | — | NOT-EVALUABLE：同 22-2 |
| AT-960-22-5 | Playwright／E2E | I-22 | —（無測試案例） | — | — | NOT-EVALUABLE：同 22-2 |
| AT-960-22-E-1 | Playwright／E2E | I-22 | —（無測試案例） | — | — | NOT-EVALUABLE（F-07）：`research.mock.spec.ts` 不存在、無 AT 標記；語意由 a11y.mock.spec.ts 研究三情境（axe 零違規×1440／1000／600）＋research-studio-perf.mock.spec.ts:678-679（橫向溢出）分散涵蓋 |
| AT-960-23-1 | 指令核對／Gate | I-23 | —（無測試案例） | — | — | PASS（逐包）；全範圍子句字面不成立（F-10：4 個主控無關維護 commit）；包外檔案見 F-11 |
| AT-960-23-2 | 指令核對／Gate | I-23 | —（無測試案例） | — | — | PASS（指令核對：TestDirEntryPrimitivesAreAccountedFor 7 OK；app/research 4 處文字命中皆 docstring） |
| AT-960-23-3 | 指令核對／Gate | I-23 | —（無測試案例） | — | — | PASS（大部分獨立驗證）：ruff 兩視角 rc 0；`tsc --noEmit` rc 0；`npm run lint` rc 0；vitest 2,191 通過＋覆蓋率 97.54／93.15／98.86／98.45%（門檻 70／60／70／70）rc 0；**pristine 副本 `gradlew clean build`：2,324 tests／0 fail／0 skip／BUILD SUCCESSFUL 4m14s、JaCoCo instruction 96.41%／line 96.27%、Checkstyle main＋test、jacocoTestCoverageVerification 通過**；Bridge 研究子集 877 通過／0 略過（SDD_ROOT＋BRIDGE_TEST_DSN 在場）。未獨立跑：`npm run build`（重用主控 03:27 建置）、docker build、Bridge 全套 2,346 的真 repo 樹基線（引用主控 2,339 通過／7 略過；我在真樹只跑 21 研究檔＋3 sdd 檔共 1,261 案例，副本全套另跑一次，見 G） |
| AT-960-23-4 | 指令核對／Gate | I-23 | —（無測試案例） | — | — | PASS（指令核對：check_loc_budget rc 0、零 AgentConsole 檔、`.claude` diff 空） |
| AT-960-23-5 | 指令核對／Gate | I-23 | —（無測試案例） | — | — | PASS（指令核對：276 檔零 CR；53 個 py AST 掃描零違規） |
| AT-960-24-1 | 指令核對／Gate | I-24 | —（無測試案例） | — | — | 部分：基線站點鎖 rc 0、CLAUDE.md 167／README.md 78、ID 家族只在本鍵檔案；**RTM-P0 仍有 474 處「待實作」＝主控收尾回填（F-14）** |

## D　突變表（`git archive` 副本；每包至少 5 個單點突變）

KILLED＝套件在突變下紅且擊殺測試對應被突變程式；SURVIVED＝全套仍綠；EQUIVALENT＝人工判等價（不計存活）；SUSPECT＝只被不相關／環境相依測試擊殺，改以人工判讀。

| ID | 包 | 檔 | 突變 | 結果 | 擊殺階段／測試 |
|---|---|---|---|---|---|
| DB-1 | DB | V18__research_prd_review_gate.sql | 輪表 passed CHECK 去掉「最低維度≥地板」子句 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_6_reviewRoundsExactNumericsAndPassedCheck() FAILED ／ > Task :test FAILED |
| DB-2 | DB | V18__research_prd_review_gate.sql | passed CHECK 的 open_p1_count=0 改 >=0 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_6_reviewRoundsExactNumericsAndPassedCheck() FAILED ／ > Task :test FAILED |
| DB-3 | DB | V18__research_prd_review_gate.sql | 移除輪表 append-only 觸發器 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_1_flywayHistoryObjectsAndGuardWiring() FAILED ／ ResearchSchemaMigrationIT > AT_960_1_E_6_controlledUpdateGuardMatrix() FAILED ／ Resea |
| DB-4 | DB | V18__research_prd_review_gate.sql | precheck 不過 CHECK 去掉 `AND passed IS NOT TRUE`（被 passed CHECK 蘊含＝冗餘） | **EQUIVALENT** |   |
| DB-5 | DB | V18__research_prd_review_gate.sql | floor_score CHECK 50..100 改 0..100（D-65(2)） | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_E_7_reviewRoundCheckGroup() FAILED ／ > Task :test FAILED |
| DB-6 | DB | V18__research_prd_review_gate.sql | 移除 `verdict='PASS' ⇔ passed` CHECK（D-61） | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_E_7_reviewRoundCheckGroup() FAILED ／ > Task :test FAILED |
| DB-7 | DB | V17__research_evidence.sql | 移除 T3 必為線索 CHECK | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_3_sourcesChecksAndVerificationUpgrade() FAILED ／ > Task :test FAILED |
| DB-8 | DB | V17__research_evidence.sql | Reddit 條款確認 CHECK 恆真 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_4_allowlistImmutableColumnsAndChecks() FAILED ／ > Task :test FAILED |
| DB-9 | DB | V16__research_core.sql | 專案 slug 唯一索引不限未封存 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_1_flywayHistoryObjectsAndGuardWiring() FAILED ／ ResearchSchemaMigrationIT > AT_960_1_5_projectsSequenceSlugAndUniqueness() FAILED ／ > |
| DB-10 | DB | V17__research_evidence.sql | COMMIT 錨點 40 碼放寬成 39–40 碼 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_3_sourcesChecksAndVerificationUpgrade() FAILED ／ > Task :test FAILED |
| DB-11 | DB | V16__research_core.sql | stage run 單一進行中索引只涵蓋 QUEUED（D-61） | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_1_flywayHistoryObjectsAndGuardWiring() FAILED ／ ResearchSchemaMigrationIT > AT_960_1_9_stageRunsArtifactsAndTheActiveRunIndex() FAILE |
| DB-12 | DB | V17__research_evidence.sql | verification 只升不降守衛 `<` 改 `<=` | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_E_5_sourceVerificationOnlyGoesUp() FAILED ／ > Task :test FAILED |
| DB-13 | DB | V18__research_prd_review_gate.sql | 缺陷 FIXED→OPEN 也放行 | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_E_4_defectStatusIsOneWay() FAILED ／ > Task :test FAILED |
| DB-14 | DB | V18__research_prd_review_gate.sql | 缺陷 REGRESSED→OPEN 也放行（D-63） | **KILLED** | targeted:SchemaIT ResearchSchemaMigrationIT > AT_960_1_E_4_defectStatusIsOneWay() FAILED ／ > Task :test FAILED |
| DB-15 | DB | V16__research_core.sql | rp_no CHECK 4 位數放寬成 3 位數 | **SURVIVED** |   |
| BRA-1 | BR-A | sdd_cli.py | 外環鍵 SDD_ENABLE_AUTO_RECOVERY 0 改 1（D-26） | **KILLED** | targeted:BR-A suite FAILED tests/test_research_fsm_ops.py::test_AT_960_13_8_after_a_human_resume_the_budget_is_not_reset[fake-pass] ／ FAILED tests/test_research_fsm_ops.py::test_AT_960_13_5_ |
| BRA-2 | BR-A | sdd_cli.py | 建檔動詞放寬到內環鍵 | **KILLED** | targeted:BR-A suite FAILED tests/test_research_fsm_ops.py::test_AT_960_13_3_creation_is_only_for_show_on_an_outer_key |
| BRA-3 | BR-A | sdd_cli.py | gate 動詞放行 --trigger 旗標 | **KILLED** | targeted:BR-A suite FAILED tests/test_sdd_cli.py::test_AT_960_13_2_the_flag_and_value_matrix_cell[outer:gate:--trigger is not a gate flag] |
| BRA-4 | BR-A | sdd_cli.py | 旗標值 NUL 檢查失效 | **KILLED** | targeted:BR-A suite FAILED tests/test_sdd_cli.py::test_AT_960_13_2_the_flag_and_value_matrix_cell[outer:transition:NUL in value] |
| BRA-5 | BR-A | research.py | 權杖錯誤 403 改 401 | **KILLED** | targeted:BR-A suite FAILED tests/test_research_router.py::test_AT_960_2_2_the_token_gate_comes_first_and_the_audit_never_holds_the_token |
| BRA-6 | BR-A | research.py | 並行上限 `>=` 改 `>`（D-67） | **KILLED** | targeted:BR-A suite FAILED tests/test_research_router.py::test_AT_960_6_4_two_projects_really_run_in_parallel_when_the_cap_is_two_and_conflicts_hold[fake] ／ FAILED tests/test_research_router |
| BRA-7 | BR-A | research.py | Bridge events 上限 500 改 1,000（ALL 階段被不相關 orchestrator 測試擊殺＝負載 flaky，不採信；tests 無 limit>500 請求＝存活） | **SURVIVED** | all-bridge-research(minus health_settings) FAILED tests/test_research_orchestrator.py::test_AT_960_12_7_a_human_save_makes_the_old_pass_stale_and_review_becomes_post_human[real] ／ FAILED tests/test_re |
| BRA-8 | BR-A | research.py | PRD 上限 1 MiB 加 1 | **KILLED** | targeted:BR-A suite FAILED tests/test_research_router.py::test_AT_960_6_6_bad_prd_content_is_422_and_adds_no_version[fake] |
| BRA-9 | BR-A | research.py | 同專案進行中 stage 互斥移除 | **KILLED** | targeted:BR-A suite FAILED tests/test_research_router.py::test_AT_960_6_4_two_projects_really_run_in_parallel_when_the_cap_is_two_and_conflicts_hold[fake] ／ FAILED tests/test_research_router |
| BRA-10 | BR-A | layout.py | slug 長度上限 30 改 31 | **KILLED** | targeted:BR-A suite FAILED tests/test_research_router.py::test_AT_960_3_1_bad_fields_are_422_and_leave_nothing_behind[fake] ／ FAILED tests/test_research_layout.py::test_AT_960_3_2_a_bad_slug |
| BRA-11 | BR-A | db.py | slug 唯一性不排除已封存專案 | **KILLED** | targeted:BR-A suite+db FAILED tests/test_research_router.py::test_cancel_archive_and_restore[real] ／ FAILED tests/test_research_router.py::test_cancel_archive_and_restore[fake] |
| BRB-1 | BR-B | allowlist.py | 允許 http（僅 https 失效） | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_1_only_normalised_arxiv_and_github_https_forms_pass[form01] ／ FAILED tests/test_research_fetch_security.py::te |
| BRB-2 | BR-B | allowlist.py | 不檢查埠 443 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_1_the_wrapper_differs_from_the_wrapped_function_only_on_three_forms[form05] ／ FAILED tests/test_research_fetch |
| BRB-3 | BR-B | allowlist.py | 不檢查尾點 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_1_the_wrapper_differs_from_the_wrapped_function_only_on_three_forms[form07] ／ FAILED tests/test_research_fetch |
| BRB-4 | BR-B | allowlist.py | 混合 DNS 答案只在全私網時才拒（rebinding） | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_2_one_non_public_answer_among_public_ones_denies_the_whole_host |
| BRB-5 | BR-B | allowlist.py | 多播位址不再擋 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_2_every_other_non_global_range_is_denied_too[ff02::1] ／ FAILED tests/test_research_fetch_security.py::test_AT_ |
| BRB-6 | BR-B | allowlist.py | GitHub 搜尋端點未帶權杖下限 6 改 2 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_7_default_effective_intervals_equal_the_v_r9_values ／ FAILED tests/test_research_fetch_security.py::test_AT_96 |
| BRB-7 | BR-B | allowlist.py | 被拒 URL 留存 500 改 5,000（D-66） | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_1_unsafe_characters_in_a_denied_url_cannot_break_the_database_write ／ FAILED tests/test_research_fetch_securit |
| BRB-8 | BR-B | allowlist.py | 保留字 `(unparsed)` 改字（D-66） | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_1_the_reserved_host_is_what_makes_the_database_accept_an_unparsed_call |
| BRB-9 | BR-B | allowlist.py | ADMIN 條目可低於內建下限 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_7_an_admin_entry_can_only_lengthen_the_interval |
| BRB-10 | BR-B | http.py | 重導跳數 3 改 4 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_4_more_than_three_hops_is_an_http_error_with_an_explanation ／ FAILED tests/test_research_fetch_security.py::te |
| BRB-11 | BR-B | http.py | Content-Length 邊界 `>` 改 `>=` | **SURVIVED** |   |
| BRB-12 | BR-B | http.py | 文字類 content-type 移除 application/json | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_2_addresses_just_outside_the_private_ranges_are_not_over_blocked[93.184.216.34] ／ FAILED tests/test_research_f |
| BRB-13 | BR-B | http.py | 429 退避不取 DEFAULT_BACKOFF | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_7_a_429_is_rate_limited_retried_once_after_backing_off_and_never_stormed |
| BRB-14 | BR-B | arxiv.py | arXiv anchor_kind 恆 DOI | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_parsers.py::test_AT_960_8_6_missing_fields_read_as_unseen_not_empty_and_not_omitted[arxiv] ／ FAILED tests/test_research_fetch_parsers.py: |
| BRB-15 | BR-B | github.py | GitHub NOASSERTION 視為授權 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_parsers.py::test_AT_960_8_6_the_golden_response_matches_the_golden_json_field_by_field[github] ／ FAILED tests/test_research_fetch_parsers |
| BRB-16 | BR-B | __init__.py | STANDARD 全 run 抓取上限 30 改 31 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_E_3_each_depth_level_caps_sources_per_layer_and_fetches_per_run[STANDARD-10-30] |
| BRB-17 | BR-B | __init__.py | 每層上限 `>=` 改 `>` | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_E_3_each_depth_level_caps_sources_per_layer_and_fetches_per_run[QUICK-5-15] ／ FAILED tests/test_research_fetch |
| BRB-18 | BR-B | __init__.py | 全 run 上限 `>=` 改 `>` | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_E_3_the_run_wide_cap_binds_when_more_layers_compete ／ FAILED tests/test_research_fetch_security.py::test_AT_96 |
| BRB-19 | BR-B | __init__.py | UI 請求值可超過硬上限 | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_security.py::test_AT_960_8_E_3_a_request_can_only_lower_the_limits_never_raise_them |
| BRB-20 | BR-B | http.py | 「未見」不轉 NULL（D-70） | **KILLED** | targeted:BR-B suite FAILED tests/test_research_fetch_parsers.py::test_AT_960_8_6_nullable_columns_turn_unseen_into_null_and_text_columns_keep_it ／ FAILED tests/test_research_fetch_parsers.py |
| BRC-1 | BR-C | aggregate.py | 通過門檻 W100 `>=` 改 `>` | **KILLED** | targeted:research_gates+research_orchestrator+research_approve+research_compile+research_reconcile FAILED tests/test_research_gates.py::test_AT_960_12_E_3_the_negative_control_84_95_fails_and_85_00_pa |
| BRC-2 | BR-C | aggregate.py | 最低維度地板 `>=` 改 `>` | **SURVIVED** |   |
| BRC-3 | BR-C | aggregate.py | POST_HUMAN 通過輪也呼叫 gate PASS（D-50） | **KILLED** | targeted:research_gates+research_orchestrator+research_approve+research_compile+research_reconcile FAILED tests/test_research_gates.py::test_AT_960_12_2_verdict_follows_the_fsm_reply_and_post_human_ne |
| BRC-4 | BR-C | aggregate.py | 升級計數 `>=` 改 `>` | **KILLED** | targeted:research_gates+research_orchestrator+research_approve+research_compile+research_reconcile FAILED tests/test_research_gates.py::test_AT_960_12_2_verdict_follows_the_fsm_reply_and_post_human_ne |
| BRC-5 | BR-C | schemas.py | 權重 ARCHITECTURE／PRODUCT 對調 | **KILLED** | targeted:research_gates+research_orchestrator+research_approve+research_compile+research_reconcile FAILED tests/test_research_gates.py::test_AT_960_12_1_w100_and_the_exact_two_decimal_display[given6-8 |
| BRC-6 | BR-C | orchestrator.py | POST_HUMAN 輪也推進到 SCG_VALIDATION | **KILLED** | BR-C orchestrator ERROR    bridge.research.orchestrator:orchestrator.py:491 研究 e9c2fd7f-e47a-44bf-a4f8-1e084fa6d8c2 的 stage 鏈崩潰 ／ ERROR    bridge.research.orchestrator:orchestrator.py:495  |
| BRC-7 | BR-C | orchestrator.py | 恢復後 revise→review 鏈不續（D-60） | **KILLED** | BR-C orchestrator FAILED tests/test_research_orchestrator.py::test_AT_960_12_E_5_revise_after_a_human_resume_runs_one_round_and_a_new_failure_escalates[fake] ／ FAILED tests/test_research_o |
| BRC-8 | BR-C | orchestrator.py | stage attempt 加 2 | **KILLED** | BR-C orchestrator FAILED tests/test_research_orchestrator.py::test_AT_960_7_5_a_stage_run_left_over_by_a_restart_is_reaped_as_orphaned[real] ／ FAILED tests/test_research_orchestrator.py::t |
| BRC-9 | BR-C | orchestrator.py | 核准摘要值比對移除（D-72） | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_approve.py::test_AT_960_14_3_digest_problems_compares_only_the_keys_that_were_sent ／ FAILED tests/test_research_approve.py::test_A |
| BRC-10 | BR-C | orchestrator.py | 零鍵摘要不擋（D-72） | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_approve.py::test_AT_960_14_3_digest_problems_compares_only_the_keys_that_were_sent ／ FAILED tests/test_research_approve.py::test_D |
| BRC-11 | BR-C | playbooks.py | BG_WAIT 上限毫秒改秒 | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_compile.py::test_AT_960_7_3_every_step_is_bounded_and_self_contained[fixture-1200] ／ FAILED tests/test_research_compile.py::test_A |
| BRC-12 | BR-C | orchestrator.py | FSM 為 HUMAN_PENDING 時不判 POST_HUMAN | **KILLED** | BR-C orchestrator FAILED tests/test_research_orchestrator.py::test_AT_960_12_7_a_human_save_makes_the_old_pass_stale_and_review_becomes_post_human[fake] ／ FAILED tests/test_research_orches |
| BRC-13 | BR-C | evidence.py | 證據格上限 600 的邊界 `>` 改 `>=` | **SURVIVED** |   |
| BRC-14 | BR-C | evidence.py | MIN_EVIDENCE_ROWS 3 改 2 | **SURVIVED** |   |
| BRC-15 | BR-C | evidence.py | T2／V3 強度 MEDIUM 改 STRONG | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_gates.py::test_AT_960_9_8_strength_follows_the_template_table[T2-V3-f411-LIMIT-MEDIUM] |
| BRC-16 | BR-C | evidence.py | WEAKEN 反證不降級 | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_gates.py::test_AT_960_9_8_strength_follows_the_template_table[T1-V2-f410-WEAKEN-WEAK] ／ FAILED tests/test_research_gates.py::test_ |
| BRC-17 | BR-C | evidence.py | 風險標籤封頂失效 | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_gates.py::test_AT_960_9_8_strength_follows_the_template_table[T1-V3-f45-LIMIT-MEDIUM] |
| BRC-18 | BR-C | playbooks.py | REVIEW 角色 Edit 範圍放寬到整個工作區（D-74） | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_compile.py::test_AT_960_7_1_each_role_gets_its_minimal_allowed_tools[fixture] |
| BRC-19 | BR-C | playbooks.py | Web 工具無條件加入 | **KILLED** | BR-C fast(gates+approve+compile+reconcile) FAILED tests/test_research_compile.py::test_AT_960_7_1_each_role_gets_its_minimal_allowed_tools[fixture] |
| BRC-20 | BR-C | orchestrator.py | skipped 告警 kind 改名（D-71′） | **SURVIVED** |   |
| BRC-21 | BR-C | settings.py | 步驟逾時預設 600 改 1,200（D-75） | **KILLED** | all-bridge-research(minus health_settings) FAILED tests/test_research_settings.py::test_AT_960_2_E_1_the_defaults_are_the_documented_values |
| BRC-22 | BR-C | review_card.py | 審查卡 V3「score≥18 須含 § 錨點」門檻 18 改 19（存活；併入 F-03） | **SURVIVED** |   |
| BRC-23 | BR-C | review_card.py | prd_anchor 章號上界 §14 改 §15，第 15 章也通過（存活；併入 F-03） | **SURVIVED** |   |
| BRC-24 | BR-C | review_card.py | QA 手動 SLV 檢查「ac_testable<ac_total 須有 P1 或 P2 缺陷」改只認 P1 | **KILLED** | BR-C orchestrator FAILED tests/test_research_orchestrator.py::test_AT_960_12_3_invalid_reviewer_output_writes_no_round_and_keeps_the_round_number[fake] ／ FAILED tests/test_research_orchest |
| BRC-25 | BR-C | review_card.py | WAIVED 轉移不要求非空 waiver_reason（只看 waived_by；只在 ALL 階段被 test_research_db 的 AT-960-12-5 擊殺） | **KILLED** | all-bridge-research(minus health_settings) FAILED tests/test_research_db.py::test_AT_960_12_5_defect_status_moves_only_along_the_one_way_table |
| API-1 | API | ResearchFlowPolicy.java | ESCALATION 前綴判斷改精確比對 | **KILLED** | targeted:FlowPolicyTest ResearchFlowPolicyTest > AT_960_4_E_2_effectiveIsTableDrivenAndNeverDerivesASecondTruthForTheCursorSteps() FAILED ／ > Task :test FAILED |
| API-2 | API | ResearchFlowPolicy.java | BUILD_READY 不要求已談判 | **KILLED** | targeted:FlowPolicyTest ResearchFlowPolicyTest > AT_960_4_E_2_effectiveIsTableDrivenAndNeverDerivesASecondTruthForTheCursorSteps() FAILED ／ > Task :test FAILED |
| API-3 | API | ResearchFlowPolicy.java | HEALING 恆算 BUILDING | **KILLED** | targeted:FlowPolicyTest ResearchFlowPolicyTest > AT_960_4_E_2_effectiveIsTableDrivenAndNeverDerivesASecondTruthForTheCursorSteps() FAILED ／ > Task :test FAILED |
| API-4 | API | ResearchFlowPolicy.java | 步驟 DONE 邊界 `<` 改 `<=` | **KILLED** | targeted:FlowPolicyTest ResearchFlowPolicyTest > AT_960_4_E_2_theFurthestStepIsTheLaterOfTheCursorAndTheDerivedPosition() FAILED ／ ResearchFlowPolicyTest > AT_960_4_E_2_aBlockingStatusMarksTheCu |
| API-5 | API | ResearchFlowPolicy.java | furthestStep 恆取游標 | **KILLED** | targeted:FlowPolicyTest ResearchFlowPolicyTest > AT_960_4_E_2_theFurthestStepIsTheLaterOfTheCursorAndTheDerivedPosition() FAILED ／ > Task :test FAILED |
| API-6 | API | SecurityConfig.java | approve 規則 ADMIN 改 OPERATOR | **KILLED** | targeted:RbacIT+ApiIT ResearchApiIT > AT_960_14_4_theApproverIsAlwaysTheJwtSubjectAndAForgedApproverInTheBodyIsIgnored() FAILED ／ ResearchApiIT > AT_960_14_E_1_everyBridgeFailureIsRelayedWithI |
| API-7 | API | SecurityConfig.java | allowlist PATCH 規則 ADMIN 改 OPERATOR | **KILLED** | targeted:RbacIT+ApiIT ResearchApiIT > AT_960_5_4_theAllowlistApiLetsOnlyAdminAddAndDisableAndEveryWriteLeavesOneAuditRowWithoutTouchingTheEventLedger(CapturedOutput) FAILED ／ RbacIT > AT_960_5 |
| API-8 | API | ResearchInputGates.java | applicabilityAxes 項數上限 6 改 7 | **KILLED** | targeted:ApiIT ResearchApiIT > AT_960_4_1_theCreateGateRejectsEveryViolationWith400AndTouchesNeitherTheBridgeNorTheDatabase() FAILED ／ > Task :test FAILED |
| API-9 | API | ResearchInputGates.java | slug 長度上限 30 改 31 | **SURVIVED** |   |
| API-10 | API | ResearchInputGates.java | PRD 1 MiB 邊界 `>` 改 `>=` | **SURVIVED** |   |
| API-11 | API | ResearchCommandService.java | 移除 reinit 換世代的服務層 ADMIN 檢查（D-64） | **KILLED** | targeted:RbacIT+ApiIT RbacIT > AT_960_15_9_reinitWithGenerationNextIsAdminOnlyInTheServiceLayerWhileTheRetryInitModeStaysOperator() FAILED ／ > Task :test FAILED |
| API-12 | API | ResearchCommandService.java | approve 的 approver 不取 JWT subject | **KILLED** | targeted:ApiIT+RbacIT ResearchApiIT > AT_960_14_4_theApproverIsAlwaysTheJwtSubjectAndAForgedApproverInTheBodyIsIgnored() FAILED ／ > Task :test FAILED |
| API-13 | API | ResearchQueryService.java | events 上限 500 改 1,000 | **KILLED** | all-research-java+migration-ITs ResearchStreamIT > AT_960_10_2_restBackfillReturnsTheWholeTailAndAnOversizedLimitIsClampedTo500WithTheContinuationCursor() FAILED ／ > Task :test FAILED |
| API-14 | API | ResearchStreamService.java | replay_gap 的 toSeq 差一 | **KILLED** | targeted:StreamIT ResearchStreamIT > AT_960_10_1_aConnectionWithoutLastEventIdOnlyGetsEventsWrittenAfterItAndAGapOfTheLedgerIsAnnouncedBeforeTheNextEvent() FAILED ／ ResearchStreamIT > AT_9 |
| API-15 | API | ResearchStreamService.java | Last-Event-ID 0 視為未帶 | **KILLED** | targeted:StreamIT+ApiIT ResearchStreamIT > AT_960_10_2_authenticationAndRolesAreTheSameAsRestGetAndAnUnknownProjectIsA404WithTheResearchReason() FAILED ／ > Task :test FAILED |
| FA-1 | FE-A | research.ts | 步驟 DONE 邊界 `<` 改 `<=` | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > AT_960_19_E_1 五步列與可達性（表驅動；純函式） > AT_960_19_E_1 deriveSteps：游標 k 為 1 至 5、九種 flow_status 全部組合，恆五項、序號與名稱固定；小於 k 已完成、等 ／ FAIL  lib/domain/ |
| FA-2 | FE-A | research.ts | stepReachable `<=` 改 `<` | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > AT_960_19_E_1 五步列與可達性（表驅動；純函式） > AT_960_19_E_1 stepReachable：25 個 (step, furthest) 組合，僅在 step 不超前於 furthest 時為真；re |
| FA-3 | FE-A | research.ts | 剩餘預算不夾 0 | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > AT_960_16_E_4 剩餘審查預算＝max(0, 3 − currentCount)，來源只取 FSM 視圖的 currentCount > AT_960_16_E_4 表驅動 0、1、2、3、4 依序得 3、2、1、0、 |
| FA-4 | FE-A | research.ts | 72 小時橫幅 `>=` 改 `>` | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > Gate 0 等待時數（D-48(3)；AC-R2P-09-10） > gate0WaitView：FSM 現態不是 HUMAN_PENDING 不顯示；滿 72 小時 overdue；較新的 POST_HUMAN 通過輪不改變 |
| FA-5 | FE-A | research.ts | 等待小時 floor 改 round | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > Gate 0 等待時數（D-48(3)；AC-R2P-09-10） > gateWaitedHours：向下取整（5 小時、71 小時 59 分、72 小時、100 小時）；起點解不出回 null；時鐘偏差的負值夾到 0；入參為 ／ FAIL  lib/domain/ |
| FA-6 | FE-A | research.ts | Gate 0 等待不限 HUMAN_PENDING | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > Gate 0 等待時數（D-48(3)；AC-R2P-09-10） > gate0WaitView：FSM 現態不是 HUMAN_PENDING 不顯示；滿 72 小時 overdue；較新的 POST_HUMAN 通過輪不改變 |
| FA-7 | FE-A | research.ts | 前端 slug 上限 30 改 31 | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > 新建研究專案：代號、摘要、驗證、請求本文 > createResearchErrors：topic 空與 501 字、slug 不合規、四層全關各回對應欄位的錯誤；合法輸入回空物件 |
| FA-8 | FE-A | registry.ts | 導覽 mobile:false 改 true | **KILLED** | targeted:nav tests FAIL  components/layout/ToolsRegion.test.tsx > AT_932_6_8 mobile 旗標以 max-md:hidden 落實 > AT_BK_01_3_1 真登記表渲染 Tools 區：九個連結皆在 DOM；帶 max-md:hidden 的恰為自我進化 ／ FAIL  components/ |
| FA-9 | FE-A | registry.ts | 導覽 match 放寬成 /research* | **KILLED** | targeted:nav tests FAIL  components/layout/ToolsRegion.test.tsx > AT_960_18_4 研發工作流入口（底部 Tab 不含、側欄含） > AT_960_18_4 路徑 /researchx：aria-current 恰在 [] ／ FAIL  components/layout/ToolsRegion.tes |
| FA-10 | FE-A | research.ts | resolveViewStep 不夾 furthest≥current | **KILLED** | targeted:research.test FAIL  lib/domain/research.test.ts > AT_960_19_E_1 五步列與可達性（表驅動；純函式） > AT_960_19_E_1 stepReachable：25 個 (step, furthest) 組合，僅在 step 不超前於 furthest 時為真；re |
| FA-11 | FE-A | research.ts | TOPIC_MAX 500 改 501 | **KILLED** | targeted:research.test+ListView FAIL  lib/domain/research.test.ts > 新建研究專案：代號、摘要、驗證、請求本文 > createResearchErrors：topic 空與 501 字、slug 不合規、四層全關各回對應欄位的錯誤；合法輸入回空物件 ／ FAIL  components/domain/research/Resear |
| FB-1 | FE-B | research.ts | 重複事件判斷 `<=` 改 `<` | **KILLED** | targeted:research.test+Timeline FAIL  components/domain/research/EvidenceTimeline.test.tsx > AT_960_10_8 收到 research.replay_gap 訊號即全量重抓並與後續 SSE 去重合併，訊號本身不顯示為事件 > AT_960_10_8 畫面已有 1 至 |
| FB-2 | FE-B | research.ts | contiguousPrefix 的 break 改 continue（輸入已升冪＝等價） | **EQUIVALENT** |   |
| FB-3 | FE-B | research.ts | 事件合併優先序對調（串流優先於 REST） | **KILLED** | targeted:research.test+Timeline FAIL  components/domain/research/EvidenceTimeline.test.tsx > AT_960_10_5 時間軸合併純函式：依 seq 去重、自 1 起連續的前綴、障壁 > AT_960_10_5 mergeEventsBySeq：升冪聯集、同 seq 只留一 |
| FB-4 | FE-B | research.ts | 重抓障壁 `<=` 改 `<` | **KILLED** | targeted:research.test+Timeline FAIL  components/domain/research/EvidenceTimeline.test.tsx > AT_960_10_5 頁面重開由 REST 重建；SSE 重連首筆 id 不連續即全量重抓並去重合併 > AT_960_10_5 重連後首筆 id 為 52（不是 46；沒有  ／ FAIL  component |
| FB-5 | FE-B | research.ts | GPL regex 去 `\b`（LGPL 也命中） | **SURVIVED** |   |
| FB-6 | FE-B | research.ts | isRedditHost 去 redd.it | **KILLED** | targeted:research.test+Allowlist FAIL  components/domain/research/AllowlistDialog.test.tsx > AT_960_19_8 Reddit 條款確認 > AT_960_19_8 Reddit 網域判斷（純函式）：reddit.com、子網域、redd.it 是；長得像的別人網域不是 |
| FB-7 | FE-B | research.ts | 證據閘 `>=` 改 `>` | **KILLED** | targeted:research.test+Topic FAIL  components/domain/research/TopicPanel.test.tsx > AT_960_19_7 議題面板：證據閘與「生成 PRD 初稿」 > AT_960_19_7 研究完成且證據閘過（3 列合格）：「生成 PRD 初稿」啟用；點了 POST stages/dr ／ FAIL  components/ |
| FB-8 | FE-B | research.ts | 合格列不排除 unanchored | **KILLED** | targeted:research.test+Topic+Matrix FAIL  components/domain/research/EvidenceMatrixTable.test.tsx > AT_960_10_6 證據矩陣表：標記計數、七欄展開、抓取紀錄、純文字與安全連結、版本、空狀態 > AT_960_10_6 頁頂：版本、列數、合格列數（V2 以上且非 U ／ FAIL  compo |
| FC-7 | FE-B | AllowlistDialog.tsx | Reddit 條款未勾仍可送出（AllowlistDialog，屬 FE-B） | **KILLED** | targeted:AllowlistDialog.test FAIL  components/domain/research/AllowlistDialog.test.tsx > AT_960_19_8 Reddit 條款確認 > AT_960_19_8 填 reddit.com：出現條款勾選與提示、「新增」停用；Enter 也送不出去；勾選後啟用，送出本文 |
| FC-1 | FE-C | StudioPanel.tsx | RICH_EDIT_MAX_BYTES 30KB 改 31KB | **KILLED** | targeted:StudioPanel.test FAIL  components/domain/research/StudioPanel.test.tsx > AT_960_17_2 超過 200KB 降級為純文字預覽並說明原因，畫面不凍結 > AT_960_17_2 200KB 走完整預覽：分批渲染（閒置排程呼叫次數大於 1）、首批只渲染一部分 |
| FC-2 | FE-C | MermaidBlock.tsx | Mermaid securityLevel strict 改 loose | **KILLED** | targeted:MermaidBlock.test FAIL  components/domain/research/MermaidBlock.test.tsx > AT_960_16_3 Mermaid 嚴格模式渲染、錯誤退回原始碼、逾時退回原始碼 > AT_960_16_3 initialize 的設定固定 securityLevel: stri |
| FC-3 | FE-C | MermaidBlock.tsx | Mermaid htmlLabels false 改 true | **KILLED** | targeted:MermaidBlock.test FAIL  components/domain/research/MermaidBlock.test.tsx > AT_960_16_3 Mermaid 嚴格模式渲染、錯誤退回原始碼、逾時退回原始碼 > AT_960_16_3 initialize 的設定固定 securityLevel: stri |
| FC-4 | FE-C | GatekeeperPanel.tsx | isAdmin 由 ADMIN 改非 VIEWER | **KILLED** | targeted:GatekeeperPanel.test FAIL  components/domain/research/GatekeeperPanel.test.tsx > AT_960_15_4 ESCALATION 區塊兩個動作 > AT_960_15_4 「換世代」鈕僅 ADMIN 啟用：OPERATOR 的 title 說明權限不足、VIEWE ／ FAIL  components/ |
| FC-5 | FE-C | GatekeeperPanel.tsx | retry_history 對照不加人工退回數 | **KILLED** | targeted:GatekeeperPanel.test FAIL  components/domain/research/GatekeeperPanel.test.tsx > AT_960_16_E_3 「第 n 輪」取自輪表列數，並以 FSM 重試史筆數對照「目前世代的未通過輪數加 humanReturnCount」，不一致顯示警示、不自建第二套計數  ／ FAIL  components/ |
| FC-6 | FE-C | GatekeeperPanel.tsx | 退回修改可無理由送出 | **KILLED** | targeted:GatekeeperPanel.test FAIL  components/domain/research/GatekeeperPanel.test.tsx > AT_960_16_8 Gate 0 確認對話框內容、退回需理由、焦點陷阱與歸還 > AT_960_16_8 按「核准 PRD」：對話框顯示 PRD 版本、sha256 前 8 碼 ／ FAIL  components/ |
| FC-8 | FE-C | research.ts | DIFF_MAX_EDITS 2,000 改 20000 | **KILLED** | targeted:PrdDiffView.test+research.test FAIL  components/domain/research/PrdDiffView.test.tsx > AT_960_16_2 比對函式：函式庫的結果與確定性比對一致、超過編輯上限退回確定性比對 > AT_960_16_2 編輯距離超過上限：函式庫放棄、退回確定性比對（整段刪除加整段新增）， |
| FD-1 | FE-D | FlowStepper.tsx | FlowStepper DONE 字色 primary-strong 改 primary（對比度回歸） | **KILLED** | targeted:FlowStepper.test FAIL  components/domain/research/FlowStepper.test.tsx > AT_960_19_3 FlowStepper 恆五項，狀態與可及名稱含狀態文字 > AT_960_19_3 DONE 的 chip：字色 class 是 text-wg-primary- |
| FD-2 | FE-D | ResearchListView.tsx | ListView active 徽章字色回歸 | **SURVIVED** |   |
| FD-3 | FE-D | ResearchListView.tsx | ListView frozen 徽章字色回歸 | **SURVIVED** |   |
| FD-4 | FE-D | ResearchListView.tsx | ListView delivered 徽章字色回歸 | **SURVIVED** |   |
| FD-5 | FE-D | FlowStepper.tsx | FlowStepper TODO 字色改 text-wg-line | **KILLED** | targeted:FlowStepper.test FAIL  components/domain/research/FlowStepper.test.tsx > AT_960_19_3 FlowStepper 恆五項，狀態與可及名稱含狀態文字 > AT_960_19_3 TODO 的 chip：字色 class 是 text-wg-muted，對它 |
| FD-6 | FE-D | StudioPanel.tsx | StudioPanel 靜態 import MarkdownView（破壞延遲載入） | **KILLED** | targeted:StudioPanel.lazy+test FAIL  components/domain/research/StudioPanel.lazy.test.tsx > AT_960_17_1 首屏補強：Markdown 渲染管線不在頁殼的靜態 import 圖裡（只經 StudioPanel 的動態 import 載入） > AT_960_17 ／ FAIL  components |
| FD-7 | FE-D | FlowStepper.tsx | FlowStepper CURRENT 字色改 primary（綠底綠字） | **KILLED** | targeted:FlowStepper.test FAIL  components/domain/research/FlowStepper.test.tsx > AT_960_19_3 FlowStepper 恆五項，狀態與可及名稱含狀態文字 > AT_960_19_3 CURRENT 的 chip：字色 class 是 text-white，對它 |

各包突變數與結果：

| 包 | 突變數 | KILLED | SURVIVED | EQUIVALENT／SUSPECT |
|---|---|---|---|---|
| DB | 15 | 13 | 1 | 1 |
| BR-A | 11 | 10 | 1 | 0 |
| BR-B | 20 | 19 | 1 | 0 |
| BR-C | 25 | 19 | 6 | 0 |
| API | 15 | 13 | 2 | 0 |
| FE-A | 11 | 11 | 0 | 0 |
| FE-B | 9 | 7 | 1 | 1 |
| FE-C | 7 | 7 | 0 | 0 |
| FE-D | 7 | 4 | 3 | 0 |

## E　跨包接縫

| # | 接縫 | 方法 | 結果 |
|---|------|------|------|
| E1 | 前端手寫 Research* 型別 ↔ `schema.d.ts`（OpenAPI 生成） | Python 解析兩檔的物件型別頂層鍵（brace 配對），32 對 DTO 逐對比鍵集與可選性（`seam_keys.py`） | 32 對頂層鍵集全等（`ResearchProjectDetail`／`ResearchFsmView` 為 `& {…}` 交集型：15＋10＝25、15＋2＝17 吻合）；唯一可選性差異＝`ResearchAllowlistRequest` 四欄 schema 可選、前端必填（前端較嚴，無害）。**限制**：只比頂層鍵與可選性，不比巢狀欄位與值域（tsc 單向可指派檢查被生成型別的可選性淹沒，不採信） |
| E2 | console-api 研究 DTO ↔ Bridge 回應（迷你 Bridge 與真 Bridge 形狀對拍） | 讀 `MiniResearchController.java` 的 snake_case 成功本文與 `routers/research.py` 各 `return {…}`（:351,437,481,522,740,789,820,828,841,873,922,956）逐鍵比 | create／stage start／put prd／approve／return／cancel／archive／restore／reinit／allowlist 的鍵集與 `flow{step,phase,status,detail}` 全吻合（Mini 的 approve 另帶 `audit_trace_id`，無害）；console-api→Bridge 請求鍵（`ResearchCommandService.java` 的 `body.put`）與 Bridge 九個 Pydantic 請求模型逐鍵吻合；路徑（`BridgeHttpAdapter.java:477-554`）與 Bridge 路由吻合。**唯一偏差**＝approve 摘要不符的錯誤碼（見 F-05）。capabilities：真 Bridge 回 8 鍵（`INFO_KEYS`），`CapabilitiesDto.java:44-50` 以 `research_root`→`root` 回退並對缺鍵給預設，容錯；`fetch_hosts`／`repo_writable`／`scaffold_root` 在真 Bridge 恆缺（DTO 回空／預設，勘誤 ⑥） |
| E3 | Bridge 事件型別 ↔ 前端事件描述表 ↔ 契約 §3 | 抽 `db.py:54-70` `EVENT_PAYLOAD_KEYS`、`describeResearchEvent`（`lib/domain/research.ts:929-1055`）讀取的 payload 鍵、契約 §3 | 契約 §3＝前端描述表＝15 型別；Bridge P0 實發 11 型別（缺 delivery／route／scr 屬 P1／P2，replay_gap 僅傳輸層）；各事件 payload 鍵（flowStep…tokensUsed…weightedScore…）前端讀取鍵逐一落在 Bridge 鍵集內；`weightedScore` Bridge 寫 float（`db.py:669`），前端 `payloadNumber` 接得住；DDL 無 `event_type` 列舉 CHECK（型別由寫入器 `EVENT_PAYLOAD_KEYS` 守） |
| E4 | reason 清單三處（契約／ErrorReasons／RESEARCH_REASONS）＋Bridge | 抽 Bridge `ApiError(code,"reason")` 字面、`ErrorReasons.RESEARCH_*`、前端常數、契約 §0.2 | 見 F-09：Bridge 21、ErrorReasons 21（18＋3 待補）、前端 18、契約 18；`spec_digest_changed` 在 ErrorReasons／前端存在但 Bridge 從不發（見 F-05） |
| E5 | approve 三端一致（D-72） | 讀前端 `GatekeeperPanel.tsx:75-76,169-174,612`、console-api `ResearchInputGates.java:226-238`＋`ResearchCommandService.java:104-118`、Bridge `routers/research.py:660-741`＋`orchestrator.py:1115-1165` | **鍵與摘要格式一致**：前端送 `01_specs/PRD-v1.0.0.md`＋`00_research/evidence_matrix.md` 兩鍵、值 `sha256:<hex>`；console-api 只驗非空／相對 POSIX 路徑／`sha256:` 64 hex、不要求四鍵；Bridge 只比對送來的鍵、其餘由 `spec-frozen --digest` 計入凍結記錄。**錯誤碼不一致**（F-05）。`approver`＝JWT subject（突變 API-12 驗） |
| E6 | 授權待查判準（前端 ↔ Bridge） | 讀 `lib/domain/research.ts:1114-1118` 與 `gates/evidence.py:518-523`、`export.py:255` | 分歧，見 F-02（P2） |
| E7 | 契約 §2.2／TCS 與實作的欄位：Bridge `ApproveIn.prd_version`＝整數、前端 `prdVersion: number`、console-api `ApproveInput.prdVersion`＝整數 | grep | 一致（勘誤 ⑩ 成立：契約文字寫字串版號的地方須改） |
| E10 | 前端 `endpoints.ts` 研究函式的 URL×方法 ↔ `ResearchController` 映射 | 解析 `endpoints.ts:660-900` 的 `apiRequest` 模板與控制器 `@XxxMapping`（`fe_be_paths.py`） | 25 個前端函式（24 個由腳本解析、`getResearchProject` 以 `researchProject(id)` 輔助函式手讀確認）的 URL×方法與後端 25 個映射一一相等；`archived` 查詢參數兩端同名；SSE 用既有 `?access_token=` 慣例（`lib/api/sse.ts:5,92`） |

### E.8　V-C1：Architecture §5.4 接入檢查表逐項人讀對照（TCS §6.2；AT-960-24-1 的第 5 子項）

| # | 檢查項（Architecture.md:463-473） | 對照結果 |
|---|------|------|
| 1 | 路由頁只殼 | ✅ `app/research/page.tsx`（11 行）、`app/research/[researchId]/page.tsx`（19 行），不 import 四區塊（AT-960-20-4 掃描通過） |
| 2 | 領域元件 | ✅ `components/domain/research/{ResearchListView,ResearchWorkspaceView,FlowStepper,ResearchFlowHeader,TopicPanel,EvidenceTimeline,EvidenceMatrixTable,AllowlistDialog,StudioPanel,PrdOutline,PrdDiffView,MermaidBlock,GatekeeperPanel}.tsx` |
| 3 | API 條目 | ✅ `lib/api/endpoints.ts` 25 個新函式（總數 84→109，`endpoints.test.ts`＋`si.endpoints.test.ts` 元鎖同步）、`queries.ts`、`types.ts`、`schema.d.ts` 重產入庫（10,422→13,911 行，純增量） |
| 4 | 純函式與測試 | ✅ `lib/domain/research.ts`（1,293 行）＋`research.test.ts`（突變 FA／FB 系列 19 個：17 被殺、FB-2 等價、FB-5 存活＝F-02） |
| 5 | 導覽登記表一列 | ✅ `lib/nav/registry.ts:123-132`（order 35、mobile:false、FlaskConical）；`ToolsRegion.tsx` 零差異（AT-960-20-4）；`registry.test.ts` 綠 |
| 6 | 說明登記表（兩條） | ✅ `lib/help/registry.ts` 有 `research`、`research-workspace`（`HELP_ROUTES` `/research`、`/research/[researchId]`）、狀態表 `researchFlow`；`PENDING_HELP_PAGES` 仍空 |
| 7 | `layout.test.tsx` | ✅ 導覽斷言由登記表驅動；`ToolsRegion.test.tsx` 只改預期值（9 連結；`max-md:hidden` 為研發工作流／議題中心／自我進化／系統管理；AT-960-18-4 綠） |
| 8 | RTM | ❌ 子表 `RTM-ResearchToPRD-P0-20261102.md` 仍有 474 處「待實作」（主控 QA 後回填；F-14） |
| 9 | 本文同步 | ✅ W0 已增補 Architecture §2.2／§3／§5.1／§5.4／…（檔頭 :14）；實作期的 §12 已知限制（L-R9／L-R12 等）本審查未重驗 |
| 10 | CI paths | ✅ `.github/workflows/agentconsole-ci.yml:29,31,49,51` 加 `AISDLC_SDD/*/agent/**` 與 `…/workflow/sdd-research-to-prd/**`（W0 主控） |
| 11 | 契約 | ✅ `API_Contract_ResearchToPRD.md`；`engine-bridge/README.md` +55 行（93b5ca94）；契約與實作的偏差見 F-05／F-09 與 F.2 |

結論：十一項中十項有對應交付，RTM 一項待主控回填（依 TCS「缺一項＝本期未完成」，此項在 RTM 回填前尚不成立）。

### E.9　SCG-4 通過標準 #4：TCS §1.2 的 111 條 P0 AC-R2P 覆蓋核對（`ac_coverage.py`：解析 §1.2 表，逐條比對 §3 的 AT 與本回合 junit 結果）

- 111 條中 **107 條**至少有 1 個本回合 PASS 的自動化 AT（且不依賴 Docker／Playwright 的 22-x）；§1.2 引用的 AT 編號全數存在於 §3（無斷鏈）。
- 其餘 4 條只靠指令核對或 V：AC-R2P-03-8（AT-960-3-6 指令核對 PASS）、AC-R2P-22-4（AT-960-20-4 指令核對 PASS）、AC-R2P-21-6（AT-960-24-1 部分＋V-C1 本報告 E.8 已做）、**AC-R2P-03-9（只有 V-R2 負向驗證＝真機項，本審查未驗）**。
- §1.3 的 60 條 P1／P2 AC 未被算入已覆蓋（本審查未見反例）。

## F　裁決偏離清單與勘誤核實

### F.1　依 D-67～D-75 偏離 TCS 字面者（供勘誤批次；列「TCS 位置／字面／實作／裁決」）

| 裁決 | TCS 位置與字面 | 實作（已讀座標） | 核實 |
|---|---|---|---|
| D-67 | AT-960-6-4「不同專案的第二個 stage 排隊或 409」 | `routers/research.py:598-607` `_check_concurrency_cap`：`active >= limit` ⇒ 409 `stage_conflict`（`details.cause=max_concurrent_runs`） | **非偏離**（TCS 允許二擇一）；突變 BRA-6（`>=`→`>`）、BRA-9（同專案互斥移除）KILLED |
| D-68 | §5.7 PKG-BR-A 列漏列 `app/health.py`、`tests/test_health_deep.py` | commit 93b5ca94 動兩檔（`health.py` +9／−2 加 `research` 資訊欄；`test_health_deep.py` 把整表斷言改為先 pop `research` 鍵集再比其餘，語意不減） | 屬實；§5.7 勘誤補列 |
| D-69 | §5.7 PKG-FE-B 集合外連動：`tests/fixtures/research/events.ts`、`lib/api/endpoints.test.ts` | eb4fe413：兩檔各 −2／+2（nextSeq 語意；prdVersion 字串→整數 3）；另授權 `lib/api/types.ts` 四處 | 屬實；只改預期值（已刪斷言掃描無違規） |
| D-70 | AT-960-8-6／PRD AC-R2P-04-6「未見」；模板 `EVIDENCE-MATRIX-TEMPLATE.md:128` 寫 UNKNOWN | 解析器輸出「未見」；`fetch/http.py:215-222` `to_db_source_row` 對 doi／git_commit／published_at／license_spdx 轉 NULL；`gates/evidence.py:258,520` 驗證與待查判準兩者皆收；`export.py:255` 渲染兩者皆顯示「未見」 | 屬實；**但前端 `isLicensePending` 未跟上 UNKNOWN（F-02）** |
| D-71′ | AT-960-8-?（skipped 載體）／V17 事件型別集合鎖死 | `orchestrator.py:697` `research.alert` `kind="FETCH_SKIPPED_OVER_LIMIT"`、`detail`＝JSON；`research.step` payload 仍四鍵 | 屬實；**但事件載體沒有任何測試釘（突變 BRC-20 存活，F-04）** |
| D-72 | AT-960-14-2「不符 409 `spec_digest_changed`（details.pair=expected_vs_file）」、14-3「expectedDigests 須涵蓋四檔，缺一鍵 422」、14-E-2；契約 L101／L319 | `routers/research.py:667-700`、`orchestrator.py:1149-1165`：只比對送來的鍵；零鍵 422 `missing_digests`；有鍵不符 422 `digest_mismatch`（details.files 列鍵／送來的值／現值）；`approve_input_violations` 不要求四鍵 | 屬實；Bridge 測試 `test_D_72_*`（:206,222）釘住；**錯誤碼未同步到 console-api／前端／OpenAPI（F-05）**；突變 BRC-9／BRC-10 KILLED |
| D-73 | FE-D 無 §5.7 列；任務書 (a)「在 ResearchWorkspaceView 動態載入面板」 | 9917f28b：`StudioPanel.tsx` 預覽管線 `next/dynamic`（:21）＋`StudioPanel.lazy.test.tsx`（6 測）＋`FlowStepper.test.tsx` +4 案；`ResearchListView.tsx:204-206` 三個徽章 `text-wg-primary-strong` | 屬實；Playwright 17-1 實測首屏 JS 見 §A；徽章修法無 vitest 守（F-08） |
| D-74 | AT-960-7-1「RESEARCH／DRAFT／REVISE＝Read、Write、Edit、Glob、Grep；REVIEW＝Read、Glob、Grep＋`Write(<工作區>/02_governance/reviews/round-<k>/**)`」；PRD／ADR-003 同 | `compile/playbooks.py:115-128`：RESEARCH／DRAFT／REVISE＝`READ_TOOLS`＋`Edit(//<小寫磁碟機無冒號路徑>/**)`；REVIEW＝`READ_TOOLS`＋`Edit(…/02_governance/reviews/round-<k>/**)`；無裸 Write | 屬實；突變 BRC-18（REVIEW 範圍放寬到整個工作區）、BRC-19（Web 工具無條件加入）KILLED（`test_AT_960_7_1_each_role_gets_its_minimal_allowed_tools`） |
| D-75 | §5.1「Bridge 環境 `BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS` 1,200」、AT-960-2-E-1「STEP_TIMEOUT_SECONDS 1,200」 | `app/settings.py:119` `RESEARCH_DEFAULT_STEP_TIMEOUT_SECONDS = 600`；`test_research_settings.py`／`test_health_settings.py` 預期值已同步 | 屬實；突變 BRC-21（600→1200）KILLED（`test_AT_960_2_E_1_the_defaults_are_the_documented_values`） |

### F.2　各包交卷勘誤候選核實（60 條；僅列我獨立查證者，餘者「引用交卷、未獨立驗」）

| 包 | 候選 | 核實 |
|---|------|------|
| API ③ | 契約 §0.2／§3 與前端 RESEARCH_REASONS 補 `allowlist_exists`／`init_failed`／`not_implemented` | 成立（F-09；`ResearchReasonsTest.PENDING_ERRATUM` 明載） |
| API ⑥／BR-A ⑤ | capabilities 鍵 `root` vs `research_root`；契約 §2.1 八鍵 | 成立（`INFO_KEYS` 8 鍵；DTO 回退容錯，E2） |
| API ⑩／FE-A | `prdVersion` 整數 | 成立（Bridge `ApproveIn.prd_version: int`；前端／console-api 皆整數） |
| BR-A ⑤ | 契約 §2.2 body 欄漏 `added_by`／`disabled_by`／`decided_by` | 成立（`AllowlistIn`／`AllowlistPatchIn`／`ReinitIn` 有；契約 §2.2 表無） |
| BR-A ⑥ | 契約 reason 補列 allowlist_exists／init_failed／not_implemented／stage_conflict details… | 成立（同 API ③） |
| BR-A ⑦ | PRD 草稿檔名 `v0.<n>.0-draft` | 成立（`db.py:168-169`） |
| FE-A（archived 參數） | 契約總表未寫查詢參數名；前端取 `?archived=true` | 成立（`endpoints.ts:674-679`；後端 `ResearchController.java:103` `archived` 布林；一致） |
| FE-A（client.ts PATCH） | `lib/api/client.ts` method 聯集加 PATCH | 成立（b1f308f6 `client.ts` +1／−1；§5.7 未列，F-11） |
| FE-B f | GPL 判定不含 LGPL | 成立於實作（regex `\b`）；**但無測試且與 Bridge 規則分歧（F-02）** |
| BR-C（逾時） | D-75 | 成立（600；Kernel 路徑固定 600 之說未獨立驗引擎） |
| BR-C（NOT_EVALUABLE 拼法） | TCS 同時用 `NOT-EVALUABLE`（health／capabilities）與 `NOT_EVALUABLE`（reconcile 項 status） | 成立（`settings.py:53` 連字號；TCS :749 vs :649,1239 底線） |
| BR-C（D-72 對 TCS 14-2／14-3／14-E-2、Architecture:1096、契約 :101／:319） | 見 F.1 | 成立；另須加「錯誤碼同步」（F-05） |
| BR-B ①～⑧、BR-A ①～④⑥⑧⑨、API ①②④⑤⑦～⑨、FE-A 其餘、FE-B a～e g h、FE-C E1～E5、FE-D、BR-C 其餘 | 見各包交卷 | 引用交卷、未逐條獨立驗（它們是 TCS／契約字面與實作現況的差異記錄；本審查的 AT 逐條與突變未發現與其矛盾之處） |


## G　誠實劃界

- **「單跑 rc」**：未對 193 個自動化 AT 各起一個行程；改為分檔批跑並讀 junit XML 的逐案例結果（Bridge 研究 21 檔 877 通過／0 略過、`test_sdd_cli／freeze／fsm` 382 通過／2 略過〔既有 symlink〕；Gradle 9 類 108 tests；vitest 全套 2,191 通過）；AT 與測試案例的對應＝測試名含 AT 底線形（等價於 `-k`／`--tests`／`-t` 的選取，另以 `at_results.json` 核對每個 AT 至少選到 1 案例、無 rc=5 空選）。
- **實作定位**：給到 AC 級檔案與已讀行號區間，不是每個 AT 一個行號（210 條）；行號是我實際讀過的區段。
- **突變**：全部在 `git archive 0b678757` 匯出的副本（`D:\qa_p0`／`qa_p1`／`qa_p2`，經 `subst` 對應 Q:／R:／S:；Windows 長路徑未啟用，副本放 scratchpad 會讓 `Path.resolve()` 後的 `shutil.copytree` 超 260 字元而基線即紅——第一批 BRC 結果因此作廢並重跑，作廢檔 `mut_results_INVALID_baseline_failed_in_subst_copy.jsonl` 留存）；副本基線：BR-C 五檔 221 通過、Bridge 全研究套件在副本唯 `test_health_settings.py` 3 測因副本無 monorepo 根而紅（環境相依，已自 ALL 階段排除並不採信其「擊殺」）、frontend 副本以 junction 共用 `node_modules`（收尾先以 .NET 非遞迴 Delete 移除連結，確認 repo 的 node_modules 未動）。ALL 階段在並行 job 的負載下出現過「被不相關 orchestrator 測試擊殺」（BRA-7；擊殺測試 `test_AT_960_12_7_…` 與被突變的 events 上限無關），不採信、改判 SURVIVED（D 表以人工覆寫標示；七突變全套同時套用的實驗亦未見任何研究測試紅，見下）。結果檔的載入順序＝首輪檔在前、重跑檔在後（同 id 後者為準；BRB-11 首輪被環境相依測試「擊殺」、重跑改判存活，BRC-2 同型）；全部 120 個突變各取最後一筆，且已逐筆核對：沒有任何一筆最終 KILLED 的「首個擊殺測試」是 `test_health_settings` 那 3 個環境相依測試（掃每筆結果的 fails 欄；升級到 ALL 階段才被擊殺者除 BRA-7 外還有 BRC-21、BRC-25（Bridge）與 API-13（Java 全研究類），擊殺測試分別是 `test_research_settings` 的 AT-960-2-E-1、`test_research_db` 的 AT-960-12-5、`ResearchStreamIT` 的 AT_960_10_2（events 上限夾到 500），皆與被突變程式語意對應）。每個 mutant 先跑靶向測試、存活才升級到全套。
- **背景工作**：突變與 Playwright 的單次執行超過 10 分鐘工具上限，改以工具的背景模式執行（同一副本不並行起第二個），全部在交卷前結束；未留常駐行程、未動 repo 檔、未碰 80／8080／8081 埠。
- **Playwright**：重用主控 03:27:46 的 standalone 建置（BUILD_ID 時間晚於所有非測試前端原始檔的最新修改 03:26:51，故視為對應 HEAD；我未重建），`E2E_MODE=standalone E2E_WEB_PORT=3209 --output=<自己目錄>`，跑 `research-studio-perf.mock.spec.ts`＋`a11y.mock.spec.ts`（共 11 案）。未對突變重跑 Playwright。
- **突變工具事故（已處置、不影響 repo）**：FD-6 首版突變（在 StudioPanel 加靜態 import `MarkdownView`）使 `StudioPanel.lazy.test.tsx` 的閘門式模組替身（工廠函式 top-level await）讓 vitest 掛住 14 分鐘以上；以 TaskStop 終止該 job（mut.py 因此未能自行還原，改由 `git show 0b678757:…` 的 blob 覆寫副本 S 的檔案並以 sha256 比對確認一致）；一支閒置的 node（vitest，pid 52736，CPU 0.6 秒、110 MB）因 `Stop-Process` 被權限分類器拒絕而留在原地——它只讀 `D:\qa_p2` 副本、不占 CPU，主控可自行結束；FD-6 改用「靜態 import `react-markdown`」重做，KILLED。
- **Java 套件範圍**：除 AT 標記的 9 個類，backend 另有未帶 AT 標記的 `ResearchEndpointsIT`（547 行；讀取投影、輸入閘、寫入轉發的補充測試）。
- **存活者全套複驗（防「只在靶向套件存活」的假象）**：(1) Java——API-9（slug 上限 30→31）、API-10（PRD 1 MiB `>`→`>=`）、DB-15（`rp_no` 4 位數放寬成 3 位數）三者**同時**套用於 `git archive` 副本，跑全 backend `gradlew.bat test --console=plain`（含未帶 AT 標記的 `ResearchEndpointsIT`）：`Test result: SUCCESS (2,324 tests, 2,324 successes, 0 failures, 0 略過)`、`BUILD SUCCESSFUL in 4m 27s`（日誌 `runs\multi_java_full.log`）⇒ 三者確認存活。(2) Bridge——BRC-2、BRC-13、BRC-14、BRC-20、BRC-22、BRB-11、BRA-7 七個存活者**同時**套用於副本 R:，跑全 engine-bridge 套件（`pytest tests -n 12`，另 `--deselect` 副本環境相依的 `test_health_settings.py` 3 測）：`40 failed, 2,280 通過, 10 略過, 13 warnings, 13 errors in 384.09s`（日誌 `runs\multi_bridge_full_R.log`）。53 個紅／錯**全部**落在需要 monorepo 根的 8 個檔（`test_si_console_ingest` 19、`test_sdd_integration_parity` 11 ERROR＋1 FAILED、`test_si_export_differential` 9、`test_si_issues` 6、`test_sdd_dogfood_fixture` 2 ERROR、`test_sdd` 2、`test_si_deploy_config` 2、`test_si_routes` 1），錯誤訊息為「找不到真的 AISDLC_SDD 樹」「CLI_CLOSURE 的項目在 monorepo 內不存在：tools/selfimproving.py」「sdd_unavailable」（副本只含 `git archive` 的 `AgentConsole/` 子樹）；**`test_research_*`、`test_mock_claude_research` 零紅**。為排除「這 53 個其實是突變造成」，我在**還原後逐檔與 tar 完全一致**的副本 R: 對同 8 檔跑無突變基線：`40 failed, 135 通過, 2 略過, 9 warnings, 13 errors in 15.62s`，紅／錯的測試 id 集合與上述 53 個**逐筆相等**（雙向差集皆空；日誌 `runs\baseline_R_envdep8.log`）⇒ 七個 Bridge 存活者對整個 engine-bridge 套件無任何額外紅燈，確認存活（BRA-7 先前在 ALL 階段的「擊殺」確為負載下不相關測試的 flaky）。
- **突變工具事故 2（已處置、不影響結論）**：`mut_multi.py` 的還原迴圈依套用順序回寫各檔原位元組，同一檔有兩個突變時（evidence.py：BRC-13、BRC-14）最後寫回的是「已套 BRC-13」的中間態，導致 multi-run 結束後副本 R: 的 `evidence.py` 殘留 BRC-13；multi-run 本身有效（兩個突變是累加套用，執行時 BRC-13＋BRC-14 同在）。發現方式＝收尾前對副本 Q:／R: 做**全樹 sha256 對 `arc0b.tar`**（`verify_tree.py`；engine-bridge 217 檔）：Q: 217／217 一致、R: 216／217（唯 evidence.py 不同）；從 tar 覆寫該檔後 R: 217／217 一致，之後才跑上述基線。Java 的 S: 副本（API-9／API-10 同檔）有同型順序，該副本已整個丟棄。副本只是 scratch，repo 工作樹全程 `git status` 乾淨。
- **skip 普查（Rule 12 fail loud）**：本回合保留的全部 junit XML（Gradle 9 類、Bridge 研究 21 檔、sdd 三檔、vitest 全套；共 3,560 個 testcase）只有 **2 個 略過**，皆為既有的 `test_sdd_freeze::test_a_symlink_that_escapes_root_is_outside_root`、`test_sdd_fsm::test_a_symlinked_state_file_that_points_outside_is_an_error_not_a_listing`（訊息「此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）」＝工具缺席型 skip，不屬任何 AT-960 條目）；AT-960 對應案例零 skip（`at_results.json`：210 條 AT 中 193 條有測試案例，這 193 條的 skip 合計 0、fail 合計 0；其餘 17 條無測試案例，見 C 表）。（掃描指令 `skip_scan.py`，輸出末行 `TOTAL {'tests': 3,560, '略過': 2, 'failures': 0, 'errors': 0}`。）
- **已獨立驗（非引用）的全量項**：`gradlew clean build`——在與 tar 逐檔一致的副本 R: 跑（`runs\backend_cleanbuild_R.log`：`checkstyleMain`／`checkstyleTest`／`Test result: SUCCESS (2,324 tests, 2,324 successes, 0 failures, 0 略過)`／`jacocoTestCoverageVerification` 通過／`BUILD SUCCESSFUL in 4m 14s`）；JaCoCo 由該副本的 `jacocoTestReport.xml` 自行加總（`jacoco_total.py`）：instruction 96.41%（75261／78064）、line 96.27%（11810／12267）、branch 85.48%。
- **未評估／未獨立驗**：Docker 全棧 E2E（22-2～22-5；主控並行建置中，且檔案不存在）、V 系列（V-R2／V-R6／V-R7／V-B1／V-D1／V-H1／V-H2＝人或真機；V-C1 我另做了人讀對照，見 E.8）、macOS／Linux、`npm run build` 與 docker build（Playwright 重用主控建置）；Bridge 全套 2,346 案例在**真 repo 樹**我只跑了 21 個研究檔＋3 個 sdd 檔（877 通過＋382 通過＋2 略過＝1,261 案例），其餘案例的真樹基線引用主控 [他包回報] 2,339 通過／7 略過；副本上另跑過全套一次（見〈存活者全套複驗〉：2,343 案例＝2,346 扣 3 個 deselect；副本缺 monorepo 根，故有 53 筆環境相依紅／錯、與無突變基線逐筆相同）。
- **接縫比對**限於靜態：鍵集、路徑、常數表與型別；未把真 Bridge 的實際回應餵進 console-api 解析（需另起整合棒）。
- 自己的推論：F-02 的實際影響取決於 agent 是否真寫 `UNKNOWN`（模板指示如此，AT-960-9-6 的 Given 也含此值），我未在真研究輪觀察到。

