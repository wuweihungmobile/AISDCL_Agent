# SCG-4 實作審查報告：自我進化核准流程全程可見（Console 半，第一波）

**鍵**: `agentconsole-si-flow-visibility`（F-911／US-931／AC-966-1～17）
**審查對象**: 實作 commit `0adfc535`（只含 `AgentConsole/` 下 68 個檔）
**規格（oracle）**: `AgentConsole/docs/03_testing/contracts/TCS-SiFlowVisibility-20261111.md`（含實作期勘誤 E-1～E-18）；根層 `docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md` §2、附錄 A
**審查者**: 獨立 QA（未參與規格與實作；測試與突變皆自己實跑，不採信交卷檔）
**審查日期**: 2026-11-11
**審查位置**: 主 repo 外的 git worktree（停在 `0adfc535`；根層黃金樣本已複製進副本；`frontend/node_modules` 在 E2E 階段由連結改為實體複本，見 §2 備註）

## 結論

**CONDITIONAL（有條件通過；有 1 個 P2，修復並重審該項後方可 PASS）**

- 實跑全綠（Bridge、backend、前端、mock E2E），新 SI 測試零略過；113 條 AT 中 109 條有對應測試，其餘 4 條（AT-966-17-1／17-2／17-3／17-E-1，Docker 全棧 E2E）依任務書預期尚未實作，不算缺陷。
- 突變測試 48 個，46 個被殺，**2 個存活**，指向同一個缺口（Q-01）：真實的 `useMinuteTick`（讓「上次心跳」與過時警示隨時間前進的唯一實作）在所有測試中都被替身取代，從未被執行過。這是規格點名「掌舵者最在意的『畫面不能說謊』情境」的承重零件，存活於關鍵斷言，依嚴重度定義為 P2。
- 無 P1：治理不變量全數成立（見 §7）。

## 1. 範圍與方法

1. 對照 TCS §4.1 與 §5.7 的差分範圍（§5）。
2. 113 條 AT 逐條對應測試（名稱帶 AT 編號；§3）；深讀 54 條（§3.2），含 22 條 `E` 負向 AT 中的 17 條。
3. 全部測試在副本實跑（§2）。
4. 48 個突變，每個突變後只跑相關測試，還原後以 `git status --porcelain` 確認（§4）。
5. 治理、契約、畫面文案、文件逐項檢查（§6、§7、§8）。

## 2. 實跑結果

| 項目 | 指令（在副本內） | rc | 摘要行 |
|------|------------------|----|--------|
| Bridge 全套 | `python -m pytest -q`（`engine-bridge/`） | 0 | 摘要行為 2583 項通過、524 項略過、1 則警告，耗時 805.34 秒（略過歸屬見下） |
| Bridge 新增與受影響 SI 測試 | `pytest -q -rs tests/test_si_patrol_route.py tests/test_si_proposal_detail.py tests/test_si_deploy_config.py tests/test_si_readonly_lock.py tests/test_si_cli.py` | 0 | `163 passed`，零略過、零 xfail |
| Bridge ruff（本目錄） | `ruff check .` | 0 | `All checks passed!` |
| Bridge ruff（monorepo 根視角） | `ruff check AgentConsole/engine-bridge` | 0 | `All checks passed!` |
| backend | `.\gradlew.bat clean build` | 0 | 測試結果 SUCCESS（2583 項測試、2583 項成功、0 項失敗、0 項略過）；`BUILD SUCCESSFUL in 4m 51s`（含 checkstyle、`jacocoTestCoverageVerification`） |
| 前端 vitest | `npx vitest run` | 0 | 測試檔 169 個全數通過（共 169）；測試案例 3034 個全數通過（共 3034） |
| 前端 lint | `npm run lint`（eslint 與 prettier `--check`） | 0 | `All matched files use Prettier code style!` |
| 前端型別 | `npx tsc --noEmit` | 0 | 無輸出 |
| 前端 build | `npm run build`（Turbopack；`NEXT_PUBLIC_API_URL=http://localhost:8080`） | 0 | 建置完成（E2E 用） |
| mock E2E | `E2E_MODE=standalone`、`npx playwright test` 對 `self-improving-flow.mock.spec.ts`、`a11y.mock.spec.ts`、`research-deliver.mock.spec.ts`、`self-improving-schedule.mock.spec.ts` | 0 | `20 passed (55.7s)`（新 spec 四條：AT-966-16-1、16-2、16-3、16-E-1 皆在其中） |
| 根層 SI 帳本檢查 | `python tools/selfimproving.py check`（副本根） | 0 | `PASS ref.obs`、`PASS ref.def`、`overall=PASS rc=0`（測試夾具無形似帳本編號而查無的字面） |
| 黃金樣本位元組 | `Get-FileHash`（根層 vs 各側複本） | — | `patrol`：Bridge、前端複本與根層相同；`detail`：Bridge、前端、backend 複本與根層相同 |

**略過或 xfail 歸屬**：新增與受影響的 SI 測試檔（Bridge 5 檔、backend、前端、E2E）零略過、零 `@Disabled`、零 `it.skip`、零 xfail（以 `-rs` 實跑與靜態 grep 雙證）。Bridge 全套的 524 個略過皆來自本鍵未動的既有測試檔（見 §2.1）。

### 2.1 Bridge 全套 524 個略過的歸屬

以 `pytest -q -rs` 全套重跑一次（2583 項通過、524 項略過，與第一次相同）逐筆取得略過原因，依原因歸類，**屬於 `test_si_*` 的略過為 0 筆**：

| 略過數 | 原因（pytest 的 skip 文字） | 所在檔 | 與本鍵的關係 |
|--------|------------------------------|--------|--------------|
| 515 | 未設定 `BRIDGE_TEST_DSN`／`TOOL-ABSENCE: BRIDGE_TEST_DSN 不存在`（沒有指向 PostgreSQL 的連線字串，只在有 PG 時跑） | `research_pg_support.py`、`test_db_integration.py`、`test_research_adopt.py`、`test_research_approve.py`、`test_research_capabilities_p1.py`、`test_research_db.py` 等研究工作區與 DB 整合測試 | 無（本鍵不碰 DB 模式；backend 側的 PG 測試走 Testcontainers 且全綠） |
| 7 | 此環境無法建立 symlink（Windows 需開發人員模式或系統管理員） | `test_api_validation.py`、`test_e2e_edge_cases.py`、`test_sdd_freeze.py`、`test_sdd_fsm.py`、`test_sdd.py`、`test_security.py` | 無（既有的 symlink 逃逸測試）。注意：本鍵 AT-966-1-7 的符號連結逃逸判準以純函式注入解析器驗證，因此在本環境不受此限制 |
| 1 | `AISDLC_SDD` 的 `build/reports/fsm` 下沒有 `FSM-STATE-*.yaml` | `test_sdd_fsm.py` | 無 |
| 1 | `TOOL-ABSENCE`：缺 `E2E_LOCAL_BRIDGE=1`、`E2E_STACK=1` 等 | `test_research_int_p2.py` | 無 |

合計 524（364 個略過位置）。皆為環境條件缺件（無 PG、無 symlink 權限、無全棧），不是被停用的測試；這些條件在 CI（Linux、有 PG）會成立，本機 Windows 不成立，屬既有狀態。

### 2.2 備註（環境，非產品缺陷）

- 副本的 `node_modules` 原是指向主 repo 的連結：Turbopack 拒絕解析連結（`Could not find the Next.js package`），改用 `--webpack` 建置則因 Tailwind 4 掃不到來源而**沒有任何工具類別 CSS**（`.overflow-x-auto`、`.sr-only` 皆不在產出內），造成 5 個假失敗（4 個既有 spec 與 AT-966-16-2、16-E-1 因樣式缺失而違規）。已刪除連結本身（非遞迴；主 repo 的 `node_modules` 經 `Test-Path` 確認完好）、改成實體複本後用 Turbopack 重建，E2E 全綠（上表）。**此為審查載具問題，未改動任何受審檔案。** 建議 `tests/e2e/README.md` 補一句：E2E 的 standalone 建置要在有實體 `node_modules` 的目錄做，連結式 `node_modules` 會得到沒有樣式的假紅。
- 副本已刪除建置產物以外的所有暫存；Gradle daemon 已停；未留任何常駐行程。

## 3. AT 覆蓋稽核

### 3.1 對應結果

以 TCS §1 表抽出 AT ID 113 條，逐條在 `AgentConsole/` 下的 `.py`／`.java`／`.ts`／`.tsx` 搜尋底線形或連字號形。

- **109 條有對應測試**，分佈：Bridge（`test_si_patrol_route.py`、`test_si_proposal_detail.py`、`test_si_deploy_config.py`、`test_si_readonly_lock.py`）、backend（`SiPatrolApiIT`、`SiProposalDetailApiIT`、`SiReadOnlyArchTest`、`OpenApiIT`）、前端（`siFlow.test.ts`、`siFlow.golden.test.ts`、`SiProposalDetail.test.tsx`、`SiDiffView.test.tsx`、`SiPatrolCard.test.tsx`、`SiWritesPanel.test.tsx`、`SiFlowRoles.test.tsx`、`content.test.ts`）、mock E2E（`self-improving-flow.mock.spec.ts`）。
- **4 條無對應**：AT-966-17-1（新鮮、過時、缺席三畫面）、AT-966-17-2（真提案詳情冒煙）、AT-966-17-3（hermetic 掛載斷言）、AT-966-17-E-1（未掛載部署的畫面）。皆為需 Docker 全棧的真全棧 E2E，且 `self-improving-flow-docker.stack.ts`（D6）不存在；依任務書預期，**列出、不算缺陷**。V1～V3、V7（長駐棧升級序列、真機入帳、axe 真棧目視）同屬主控／掌舵者待辦，本審未驗。

### 3.2 深讀（54 條；斷言是否逐字落實 Given／When／Then）

| 層 | 深讀的 AT | 判讀 |
|----|-----------|------|
| Bridge | 1-1、1-2、1-3、1-4、1-5、1-6、1-7、1-E-1（讀其斷言骨架）、4-1、4-2、4-6、4-E-1 | 落實。1-2 以 `os.stat`／`open` 偵測零檔案系統存取；1-3 十三個壞檔逐一斷言且附對照組與 NaN；1-4 同時斷言實讀位元組不超過上限加一；4-6 含 10 種金絲雀、形狀不符、snake_case、`sourceObs` 缺列形態與整份位元組比對。無弱化 |
| backend | 3-1、3-2、3-3、3-4、3-E-1 | 落實。3-1 含無 token、壞 token、三角色與四種非 GET 方法；3-2 以獨立算出的預期樹比對；3-3 含 21 秒真逾時並斷言「不重試」；3-4 斷言資料庫列內容不變與 Bridge 請求逐筆形態 |
| 前端純函式 | 5-1、5-2、5-3、5-5、5-6、5-7、5-9（未逐字深讀，由 §4 突變 F1～F3、F8～F14、F16、F19、F20、F27、F29、F30 驗證其斷言有咬合） | 落實（間接證據，不計入深讀數） |
| 前端元件 | 6-5、6-6、6-7、6-E-1、7-E-2、8-E-1、9-1、9-2、9-E-1、10-E-1、11-1、11-2、11-3、11-4、11-5、11-6、11-7、11-E-1、11-E-2、12-E-1、12-E-2、13-1～13-6、13-E-1、13-E-2、14-1、14-2、14-3、14-E-1、15-E-1 | 落實。例：11-3 同時釘 35:00 無警示、35:01 有警示、週期 60 限度 125、放著不動 32→33 分鐘自動轉警示且請求數不變；9-2 金絲雀掃整個對話框五分頁的文字與 `outerHTML`；14-1 以「請求集合」與「寫入控件選擇器」雙重斷言零寫入；15-E-1 以固定種子 966 產生 50 組垃圾輸入。E-16 的三項屬性斷言已補在 7-E-2 |
| E2E | 16-2、16-3、16-E-1 | 落實。16-2 取 `RESEARCH_WIDTHS` 同源常數並先斷言其值；16-3 以 Tab／Shift+Tab 各 60 次斷言焦點不逃出且繞圈，並以 `closest('[aria-hidden]')` 判背景隱藏（E-15） |

22 條 `E` 負向 AT：已深讀 17 條（1-E-1、3-E-1、4-E-1、6-E-1、7-E-2、8-E-1、9-E-1、10-E-1、11-E-1、11-E-2、12-E-1、12-E-2、13-E-1、13-E-2、14-E-1、15-E-1、16-E-1）；2-E-1（`docker compose config`，已讀其測試碼）與 1-E-2、5-E-1、7-E-1 只以突變與實跑間接驗證，**未逐字深讀**；17-E-1 未實作（見上）。

**弱化或恆真的 AT：未發現。** 唯一的覆蓋缺口是 §4 的 Q-01（AT-966-11-1／11-2／11-3／11-E-1(d) 的「時間前進」Then 只驗到替身時鐘，沒驗到真實計時機制）。

## 4. 突變測試

方法：每個突變一次改一處、只跑相關測試、立刻還原；結束後 `git status --porcelain` 除黃金樣本目錄外零差異。

| # | 層 | 突變 | 相關測試 | 結果 |
|---|----|------|----------|------|
| B1 | Bridge | `filter_detail` 純量鍵放行物件或陣列（fail-closed 破功） | `test_si_*` 5 檔 | 殺：`test_AT_966_4_6_detail_is_whitelisted_to_the_contract_keys` |
| B2 | Bridge | 白名單接受 snake_case 鍵 `touched_ok` | 同上 | 殺：AT-966-4-6 |
| B3 | Bridge | `filter_detail` 放行頂層未列鍵 | 同上 | 殺：AT-966-4-6 |
| B4 | Bridge | 大小邊界 `>` 改 `>=`（1048576 位元組被誤拒） | 同上 | 殺：`test_AT_966_1_4_size_boundary_at_one_mebibyte` |
| B5 | Bridge | `schema_rev` 接受布林 `true` | 同上 | 殺：AT-966-1-3 |
| B6 | Bridge | 路徑含於目錄的父目錄檢查拿掉 | 同上 | 殺：AT-966-1-7 |
| B7 | Bridge | 巡邏路由不拒查詢參數 | 同上 | 殺：AT-966-1-5 |
| B8 | Bridge | JSON 接受 NaN | 同上 | 殺：AT-966-1-3 |
| B9 | Bridge／部署 | compose 的 `/si-report` bind 改可寫 | 同上 | 殺：`test_AT_940_3_1_si_mounts_match_exactly_one_named_design`（既有唯讀鎖） |
| B10 | Bridge | 設定不擋「回報目錄＝稽核目錄」 | 同上 | 殺：AT-966-2-2 |
| B11 | Bridge | `generated_at` 缺 offset 也放行 | 同上 | 殺：AT-966-1-3 |
| G1 | backend | 巡邏 service 呼叫 Bridge 兩次 | `SiPatrolApiIT`、`SiKeyNames*`、`SiReadOnlyArchTest`、`OpenApiIT` | 殺：AT-966-3-1、3-4（2 failed） |
| G2 | backend | 巡邏端點只准 ADMIN | 同上 | 殺：AT-966-3-1、3-2、3-3、3-4、3-E-1（5 failed） |
| G3 | backend | 轉發時多帶查詢參數 | 同上 | 殺：AT-966-3-4（1 failed） |
| G4 | backend | 巡邏讀取改為重試一次 | 同上 | 殺：AT-966-3-3（1 failed） |
| G5 | backend | 欄名轉換不遞迴陣列 | 同上 | 殺：AT-966-3-2，另 `SiKeyNamesTest` 兩案（3 failed） |
| G6 | backend | 巡邏端點移除 `operationId` | 同上 | 殺：`OpenApiIT.AT_966_3_5_…`（1 failed） |
| F1 | 前端 | 過時門檻 `>` 改 `>=` | `siFlow*.test.ts`、`SiPatrolCard.test.tsx`、`SiFlowRoles.test.tsx` | 殺：邊界表（4 failed） |
| F2 | 前端 | 寬限分鐘 5 改 6 | 同上 | 殺（13 failed） |
| F3 | 前端 | `reasonText` 忽略主機白話欄 | 加 `SiProposalDetail.test.tsx` | 殺（5 failed） |
| F4 | 前端 | diff 容器去掉 `tabIndex` | `SiDiffView.test.tsx` | 殺：AT-966-7-E-2 |
| F5 | 前端 | diff 容器去掉 `role="region"` | 同上 | 殺：AT-966-7-E-2 |
| F6 | 前端 | 刪除行去掉虛線邊框 | 同上 | 殺：AT-966-7-2（非顏色標示） |
| F7 | 前端 | 低於下限警示忽略主機 `neNote` | 純函式與詳情測試 | 殺：AT-966-9-1（含黃金列） |
| F8 | 前端 | 運轉目的把第二波 `freeze` 當已知 | 純函式與卡測試 | 殺：AT-966-5-3、12-3 |
| F9 | 前端 | 入帳結合不只限 `ingested===false` | 純函式與寫入面板測試 | 殺：AT-966-5-7 |
| F10 | 前端 | 下一步不驗 `ledgerSeq >= lastSeq` | 純函式與詳情測試 | 殺：AT-966-5-2 |
| F11 | 前端 | `+++ ` 檔頭不當 file 行 | 純函式與 diff 測試 | 殺：AT-966-5-5 |
| F12 | 前端 | 推送文字不遮憑證 | 純函式與卡測試 | 殺：AT-966-5-9、12-6 |
| F13 | 前端 | diff 視窗 400 改 401 | 同上 | 殺：AT-966-5-6（3 failed） |
| F14 | 前端 | 新鮮度不加「資料抵達後經過時間」 | 同上 | 殺：AT-966-5-1、11-2、11-3 |
| F15 | 前端 | `truncated` 提示永不顯示 | `SiPatrolCard.test.tsx` | 殺：AT-966-12-E-1 |
| F16 | 前端 | 等待對象任何字串都當已知 | 純函式與卡測試 | 殺：AT-966-5-3、12-2 |
| F17 | 前端 | 「看待入帳清單」鈕對非 ADMIN 也顯示 | `SiPatrolCard.test.tsx` | 殺：AT-966-12-4 |
| F18 | 前端 | 寫入面板對所有角色顯示（VIEWER 可見性） | `SiView.test.tsx`、`SiFlowRoles.test.tsx` | 殺：AT-966-14-1（VIEWER、OPERATOR）、AT-935-4-E-3 |
| F19 | 前端 | 過時快照下一步不降級 | 純函式與詳情測試 | 殺：AT-966-5-2、6-5、6-6 |
| F20 | 前端 | 推送未知狀態當已知 | 同上 | 殺：AT-966-5-3、12-5 |
| F21 | 前端 | diff 讀屏前綴（新增：／刪除：）拿掉 | `SiDiffView.test.tsx` | 殺：AT-966-7-2 |
| F22 | 前端 | 評估集 `digest8` 外露到畫面 | 純函式與詳情測試 | 殺：AT-966-9-1、9-2 |
| F23 | 前端 | 提案本文改用 `dangerouslySetInnerHTML` | `SiProposalDetail.test.tsx` | 殺：AT-966-6-7（3 failed） |
| F24 | 前端 | 待入帳面板不顯示入帳結果 | `SiWritesPanel.test.tsx`、`SiFlowRoles.test.tsx` | 殺：AT-966-13-1～（5 failed） |
| **F25** | 前端 | **`useMinuteTick` 重繪週期由 60 秒改為 1 小時** | `SiPatrolCard.test.tsx`、`SiProposalDetail.test.tsx`、`SiView.test.tsx`、`SiWritesPanel.test.tsx` 等 | **存活**（`Tests 101 passed`） |
| F26 | 前端 | 過時警示去掉 `role="status"` | `SiPatrolCard.test.tsx` | 殺：AT-966-11-3 |
| F27 | 前端 | 下一步「無」不改寫 | 純函式與詳情測試 | 殺：AT-966-6-5 |
| F28 | 前端 | 來源觀察跳轉不設高亮 | 詳情與 `SiView` 測試 | 殺：AT-966-8-3（2 failed） |
| F29 | 前端 | `permanent` 的人工／自動判斷反向 | 純函式與寫入面板測試 | 殺：`siFlow.test.ts`（AT-966-5-7 等，3 failed） |
| F30 | 前端 | 時鐘異常（快照時間在未來）不判斷 | 純函式與卡測試 | 殺：`siFlow.test.ts`（AT-966-5-1，1 failed） |
| **F31** | 前端 | **`useMinuteTick` 拿掉 `setInterval`（永不重繪）** | 同 F25（178 個測試） | **存活**（`Tests 178 passed`） |

**統計：48 個突變，46 個被殺，2 個存活（F25、F31，同一根因＝Q-01）。**
還原確認：`git -C <副本> status --porcelain` 只剩黃金樣本目錄 `tools/tests/fixtures/selfimproving/p7/`（審查前就存在）。

## 5. 差分範圍（TCS §4.1 與 §5.7）

`git show --stat --name-only 0adfc535` 共 68 個檔，**全部在 `AgentConsole/` 之下**；未動根層 `tools/`、`.claude/`、`.github/`、根 `CLAUDE.md`、既有 Flyway、`si_cli.py`、既有 TCS 與凍結契約。逐一對照：

- D1（Bridge）：`app/si_report.py`、`app/si_detail.py`、`routers/si.py`、`settings.py`；測試 `test_si_patrol_route.py`、`test_si_proposal_detail.py`、`test_si_deploy_config.py`、`fake_si.py`、`test_si_readonly_lock.py`、`test_si_cli.py`，夾具 `tests/fixtures/si_report/*.golden.json`；另有 `engine-bridge/README.md`（說明檔，位於 D1 目錄內，清單未點名，無害）。
- D2（部署）：`docker-compose.yml`、`.env.example`、`docker/README.md`。
- D3（backend）：`SiController`、`SiMirrorUseCase`、`SiMirrorQueryService`、`AgentBridge`、`BridgeHttpAdapter`、`ErrorResponseDocumentation`；測試 `SiPatrolApiIT`、`SiProposalDetailApiIT`、`MiniBridge*`（迷你 Bridge）、`OpenApiIT`、`SiReadOnlyArchTest`、`IssueBridgeArchTest`、`detail.golden.json`。均在 §4.1／§5.7 清單。
- D4～D7（前端）：`lib/domain/siFlow.ts`、`lib/api/{endpoints,queries,types,schema.d.ts}`、`lib/help/self-improving.ts`、`content.test.ts`、六個 `components/domain/si/` 元件與 `useMinuteTick`／`usePatrolView`、`tests/helpers/{si,siFlow,siClock}`、`tests/e2e/{self-improving-flow.mock.spec.ts,siFlowFixtures.ts,a11y.ts,a11y.mock.spec.ts,research-deliver.mock.spec.ts,self-improving-schedule.mock.spec.ts}`、`si.endpoints.test.ts`、`endpoints.test.ts`。`SiFlowRoles.test.tsx`、`siFlow.golden.test.ts`、`SiWritesPanel.test.tsx` 為清單目錄內的測試檔。
- §4.1 列為「需同步」但本 commit 未改的檔：`SiStatusFilter.test.tsx`、`SiSchedulePanel.test.tsx`、`SiStatusBanner.test.tsx`、`pageFacts.test.ts`——實跑全綠，表示預設 `stubSiApi` 的 `patrol` 503 保底已涵蓋，屬清單的「若」條款，不算越界。

**清單外的檔：無。**

## 6. 治理與契約

| 檢查 | 結果 |
|------|------|
| Console 無任何寫入主機 SI 目錄的程式碼 | 通過。`si_report.py` 以 `open(path, "rb")` 唯讀；AT-966-1-6 攔截 `os.open` 寫入旗標、`Popen` 與目錄 mtime；compose bind `read_only: true` 且突變 B9 被既有唯讀鎖殺掉 |
| 本波沒有新增任何決定或寫入動作 | 通過。差分中無新增非 GET 端點、DB 遷移、稽核 kind；AT-966-14-1 斷言旅程零非 GET；AT-966-14-3 靜態鎖禁止寫入 hook、`fetch`、表單控件 |
| Console 不自建原因碼或推送狀態對照表 | 通過（有 P4 附註 Q-04）。白話一律取主機 `text`；列舉標籤僅 W-F7 允許的三組小集合；`pushStateInfo` 只回「已知／樣式」；F3、F8、F16、F20 皆被殺 |
| `filter_detail` 鍵集合與根層 TCS §2.1 相同 | 通過。`DETAIL_SPEC` 八欄與子鍵逐項對照 C-3；AT-966-4-6 以黃金樣本與 10 種金絲雀雙向釘住；B1～B3 被殺 |
| 評估集內容不出現在任何回應或畫面 | 通過（Bridge 白名單擋 `cases`／`probes`／`files` 等；前端 `heldoutView` 只取七欄；AT-966-9-2 掃對話框全文與 `outerHTML`；F22 被殺） |
| 測試資料無形似帳本編號而查無的字面 | 通過。`OBS-SI-001／002／011／050` 皆在 `SelfImproving_Observation_Ledger.md`；根層 `si check` `ref.obs`、`ref.def` 皆 PASS；`PROP-SI-901～905`、`RUN-SI-901～905`、`APP-SI-901` 為 TCS §5.1 明定的測試號（`ref.*` 未對它們報告） |
| 無完整寫出的合成帳密字串 | 通過。對 68 檔新增行掃 `sk-…`、`AKIA…`、`password=…`、`scheme://user:pass@`，零命中 |
| 角色可見性 | 通過。VIEWER／OPERATOR／ADMIN 的詳情與巡邏卡文字逐字相同（14-E-1）；寫入面板仍只限 ADMIN（F18 被殺） |

## 7. 畫面與文案

- **白話**：新增 12 個說明欄位以括號就近解釋「評估集（用來驗證的考題）」「隔離試跑（沙盒）」「檢查項目（探針）」「巡邏快照（巡邏器每個心跳留下的回報檔）」；固定句有 `AT-966-15-2` 可讀性鎖（單句 ≤ 40 字，根層白話逐字顯示豁免，E-6）。
- **未知值保底**：實測（15-E-1 的 50 組垃圾輸入、`unknownValueText`、第二波值 `freeze`／`queued`）不洩漏 `null`／`undefined`／`NaN`／`[object Object]`。
- **超大 patch**：400 行視窗、展開、下載截斷註記、單行 200001 字元皆有測試；mock E2E 的 6000 行（256 KiB）展開在 5 秒內完成且 axe 零違規。
- **快照缺席與過時**：缺席、未掛載、壞檔、過時各是不同畫面且互不冒充（11-5～11-7、11-E-1）。
- **三寬度與 axe**：mock E2E 的 16-2（1440／1000／600；巡邏卡五情境、詳情四情境、ADMIN 寫入面板）全綠；唯一在審查期間出現的違規是載具問題（§2.2）。
- **鍵盤**：Tab／Shift+Tab 循環不逃出、方向鍵切分頁、Esc 關閉且焦點回到「詳情」鈕（16-3 全綠）；diff 與提案清單的可捲動區均為 `tabIndex=0` 加 `aria-label`。
- **未驗**：V7 的 375 寬補充目視與真機畫面、V8（接近 256 KiB 的真提案的互動時間，僅有 mock 的 6000 行近似）、V6 的 Linux 一側（本審只在 Windows 跑）。

## 8. 文件一致性

- **RTM §2.16**（`AgentConsole/docs/06_quality/RTM.md` 第 512～513 行）：仍寫「現況（2026-11-11 規格階段）：全部 ⬜ 未開始」，且 `RTM-SiFlowVisibility-20261111.md` 尚不存在——尚未回填四格（Q-02）。
- **Implementation_Plan** 第 454 行：該列仍是「🟡 規格階段…未 commit」，與已落地的 `0adfc535` 不一致（Q-02）。
- **TCS 勘誤 E-1～E-18 與實作**：逐條核對一致——E-3（最近已入帳常駐、無展開鈕；`SiWritesPanel` 的 `RecentIngested` 無 button，13-5 斷言）、E-5（8-3 請求數措辭）、E-8（`siClock` 替身；`SI_QUERY_OPTIONS.refetchInterval === false` 靜態斷言）、E-10（相對路徑拋 `SettingsError`，AT-966-2-2）、E-12（fail-closed 與只認 camelCase，AT-966-4-6）、E-14（夾具為建構函式）、E-15（`aria-hidden` 判準）、E-16（role／tabIndex／aria-label 三項斷言已補）、E-17（`si.endpoints.test.ts` 標題不寫死數字）。

## 9. 發現表

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 |
|------|--------|------|------|----------|
| Q-01 | **P2** | `AgentConsole/frontend/components/domain/si/useMinuteTick.ts:10-18`；替身 `frontend/tests/helpers/siClock.ts:14-15`；以 `vi.mock("@/components/domain/si/useMinuteTick", …)` 取代它的測試，例如 `SiPatrolCard.test.tsx:19` | AT-966-11-1／11-2／11-3／11-E-1(d) 與 W-F5 要求「畫面放著不動，相對時間與過時警示每分鐘自動前進」。這條路徑的實際零件 `useMinuteTick`（`setInterval(…, 60_000)`）在所有測試都被換成替身，從未被執行：突變 F25（週期改 1 小時）與 F31（整段 `setInterval` 拿掉＝永不重繪）全部存活（101 與 178 個測試皆綠）。真實環境裡若這個 hook 壞掉，「巡邏可能沒在跑」的警示就不會自動出現——正是規格最在意的「畫面不能說謊」情境，現有測試完全抓不到 | 補一個不經替身的 hook 單元測試（`renderHook` 加 `vi.useFakeTimers()`，此檔不用 `waitFor`，不牴觸 E-8）：(a) 斷言 `MINUTE_TICK_MS === 60_000`；(b) `advanceTimersByTime(60_000)` 後回傳值改變、未滿 60 秒不變；(c) unmount 後 `clearInterval` 被呼叫、`vi.getTimerCount()` 為 0。亦可在 mock E2E 以 `page.clock` 加速 35 分鐘，斷言警示自動出現。補完後 F25、F31 須被殺 |
| Q-02 | P3 | `AgentConsole/docs/06_quality/RTM.md:512-513`；`AgentConsole/docs/04_planning/Implementation_Plan.md:454` | RTM §2.16 仍為「規格階段、全部 ⬜」，`RTM-SiFlowVisibility-20261111.md` 尚未建立；Implementation_Plan 的鍵列仍是「規格階段、未 commit」。與已落地的實作不一致（TCS 標明此為主控於 SCG-5 回填，故非實作缺陷，但 RELEASE 前必須收齊，否則 RTM 的「回填四格」鐵律 12 不成立） | SCG-5 回填：建立本地子表（F 1、US 1、AC 17、AT 113 共 132 列；AT-966-17-* 四列標「未實作」，V1～V8 標「未驗」）、改 §2.16 現況句、改 Implementation_Plan 該列狀態與 commit |
| Q-03 | P4 | `AgentConsole/engine-bridge/app/si_detail.py:35`（`heldout` 含 `digest8`）；TCS W-F9、C-3 | W-F9 說明「寧嚴勿鬆」不顯示 `digest8`（評估集內容的指紋），但 Bridge 白名單依 C-3 放行它，所以它仍會經 backend 傳到瀏覽器的網路回應（UI 不渲染，F22 被殺）。與規格一致，但是「零外露」目標與 AT-966-4-1 位元組級透傳之間的張力 | 下一次規格修訂時評估：Bridge 丟棄 `digest8`（需根層黃金樣本與 AT-966-4-1 的比對改為「去掉 digest8 後相等」，走勘誤）；本波不必動 |
| Q-04 | P4 | `AgentConsole/frontend/components/domain/si/SiProposalDetail.tsx:64,250` | W-F7 寫「Console 不列舉任何原因碼集合」，但兩處以字面 `OBS-LEDGER-UNREADABLE`、`TIMELINE-TRUNCATED` 當分支鍵（白話仍取主機 `text`）。C-3 有明列這兩個 `ne` 新碼，屬規格許可的版面分支，但算第二個要與根層同步的地方 | 在 TCS §7.3「已知邊界」補一句這兩個碼是 Console 的版面分支鍵（與 `filter_detail` 同步修訂），避免日後有人把它當成「違反 W-F7」 |
| Q-05 | P4 | `AgentConsole/frontend/lib/domain/siFlow.ts:365` | `who: who.known ? who.text : who.text` 兩個分支相同，是冗餘寫法 | 簡化為 `who: who.text` |
| Q-06 | P4 | `AgentConsole/frontend/tests/e2e/README.md`（建議） | standalone E2E 在連結式 `node_modules` 下 Turbopack 無法建置、`--webpack` 建置沒有 Tailwind 工具類別，產生 5 個看似產品缺陷的假紅（§2.2） | 在 README 註明建置須在實體 `node_modules` 目錄進行 |

## 10. 通過條件核對（TCS「SCG-4 通過標準」）

| 條件 | 狀態 |
|------|------|
| 113 個 AT 全數通過 | 109 條已實作且全綠；4 條 AT-966-17-* 需 Docker 全棧，未實作（依任務書預期） |
| §4.1 預期值改動恰等於實際改動 | 通過（§5） |
| 既有 SI AT 零弱化、`console-writes` 十一鍵零改動仍綠 | 通過（Bridge 5 檔、backend 全套、前端全套皆綠；`SiConsoleWritesReadApiIT` 在 2583 個全綠內） |
| 黃金樣本複本與根層相符且黃金列為硬斷言 | 通過（雜湊逐一相同；各側先行測試逐位元組比對） |
| `gradlew clean build`、Bridge pytest 與 ruff（兩視角）、前端 lint／tsc／build／vitest 全綠 | 通過 |
| 零 skip、零 `@Disabled`、零 `it.skip`（本鍵新增與受影響檔） | 通過 |
| 新元件靜態鎖與唯讀鎖綠 | 通過 |
| RTM 本地子表回填 | 未完成（Q-02，SCG-5 由主控做） |
| Architecture §5.7、§10.5、§12.1 L-SI-3 與實作逐項校對；V1～V8 結果回寫 | 實作面與 §5.7／§10.5 敘述相符；V1～V3、V7 未驗（待主控、掌舵者）；V4（既有 SI 測試重跑）與 V5 已由本審實跑；V6 僅 Windows；V8 僅有 mock 近似 |

## 11. 結論重述

**CONDITIONAL**：1 個 P2（Q-01，真實的每分鐘重繪機制沒有任何測試，兩個突變存活）。修復只需補測試（不改產品碼），補完後只需重跑相關測試與 F25、F31 兩個突變即可轉 PASS。P3 一筆（Q-02，SCG-5 文件回填），P4 三筆。無 P1。

## 12. 二審（範圍：Q-01、Q-04、Q-05、Q-06；Q-02、Q-03 由主控在發布前處理，不計入）

**審查位置**：副本停在修正後的 `c6472463`（相對 `0adfc535` 只多 4 個前端檔：`useMinuteTick.test.ts`（新）、`siFlow.ts`、`siFlow.test.ts`、`tests/e2e/README.md`）。`node_modules` 為一審留下的實體複本。

| 項 | 結果 | 證據 |
|----|------|------|
| Q-01 | **已解** | 新測試 `useMinuteTick.test.ts`（不經替身；`renderHook` 加假計時器，只偽造 `setInterval`／`clearInterval`／`Date`，不影響 `waitFor`）三案：週期常數 60_000、59_999 ms 不變且 60_000 ms 前進並可再前進、unmount 後 `vi.getTimerCount()` 為 0。突變重做：F25（週期改 1 小時）**殺**（2 failed：常數、前進）；F31（拿掉 `setInterval`）**殺**（2 failed）；另加 F32（不清除計時器）**殺**（1 failed）。還原後該檔 3 案全綠。替身範圍：對 `useMinuteTick` 的 `vi.mock` 仍只在 `SiPatrolCard.test.tsx` 一處，替身 helper 與其他測試檔在 `c6472463` 無任何改動，未擴大 |
| Q-05 | **已解** | `siFlow.ts:365` 改為 `{ who: who.text, text: step.text }`。`siFlow.test.ts` 新增 `nextStepLine` 案例，四種輸出逐字斷言：未知對象 `下一步：等未知值『外星人』｜說明`、已知 `下一步：等掌舵者｜說明`、缺席 `下一步：等量不到｜說明`、「無」`目前不需要任何人動作：說明`。突變 Q05（改成 `String(step.who)`）**殺**（1 failed）；還原後綠 |
| Q-06 | **已解** | `tests/e2e/README.md` 新增一條：standalone 的 production 建置須在實體 `node_modules` 目錄進行，連結目錄時 Turbopack 無法解析、`--webpack` 缺 Tailwind 工具類別而假紅，並給出處置（確認不是 symlink／junction，必要時乾淨目錄 `npm ci` 再 `npm run build`）。與一審 §2.2 的實測一致 |
| Q-04 | **處置可接受（不計未結；留一條 P4 條件）** | 開發者維持現狀的理由成立：根層契約 §2.1 沒有結構欄位表達「帳本讀不到」與「時間線被截短」，只剩 `ne` 的原因碼；Console 兩處只拿碼來決定版面（顯示哪一塊、是否多一行），顯示的句子仍逐字取主機 `text`，沒有「碼→白話」的對照表，故沒有自建對照表的實質風險。殘餘風險只有一個：根層若改名這兩個碼，Console 會靜默不再出現「時間線被截短」提示（落到沒有提示的一般時間線），而不是出錯——屬「畫面不能說謊」面的退化。建議（不阻擋）：SA 登記這兩碼為 Console 唯一允許的版面分支鍵時，同步加一個機械鎖，讀根層 TCS 附錄 A 斷言兩個碼字面存在，改名即紅 |

**二審全前端實跑**（副本，`c6472463`）：

| 項目 | 指令 | rc | 摘要行 |
|------|------|----|--------|
| vitest | `npx vitest run` | 0 | 測試檔 170 個全數通過（共 170）；測試案例 3038 個全數通過（共 3038）（一審 169／3034，差額即新測試檔與 4 個新案） |
| lint | `npm run lint` | 0 | `All matched files use Prettier code style!` |
| 型別 | `npx tsc --noEmit` | 0 | 無輸出 |

**二審結論：PASS。** 一審的 Q-01（P2）已修且突變咬合；Q-05、Q-06 已解；Q-04 處置可接受。仍未結的發現：無（Q-02、Q-03 依指示由主控在發布前處理）。還原確認：突變後 `git status --porcelain` 只剩黃金樣本目錄。
