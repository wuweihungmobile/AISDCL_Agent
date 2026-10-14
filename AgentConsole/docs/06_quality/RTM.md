# AgentConsole 需求追溯矩陣（RTM）

| 項目 | 內容 |
|------|------|
| 版本 | v1.0（W1 由 Architect 建表；初始狀態一律 `⬜ 未開始`） |
| 建立日期 | 2026-10-14 |
| 唯一真相源 | PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md`（§0 權威）、設計稿 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md`、[Architecture.md](../02_architecture/Architecture.md)（§10 Bridge 契約）、[ADR-001](../02_architecture/ADR-001-TechStack-Lock.md) |
| 維護責任 | Architect 建表；各開發 agent 回填「實作檔／自動測試／狀態」；QA 回填「E2E 驗證」並逐列核對；主控於 Implementation_Plan 進度帳彙總 |
| 總列數 | **361**（US 58／API 91／BR 25／NFR 32／INF 103／UI 52；現查指令見 §3.4） |

## 1. 使用說明

### 1.1 欄位定義

| 欄位 | 說明 |
|------|------|
| ID | 本表唯一鍵；PRD 使用者故事沿用原編號，其餘依 §1.2 前綴規則；**不得改號、不得刪列、不得合併列** |
| 來源 | PRD／設計稿／Architecture／ADR 的章節（API 列同列出方法與路徑） |
| 摘要 | 不超過 20 字的需求摘要（建表時已逐列檢查字數；新增列同樣遵守） |
| 層 | `FE`／`BE`／`Bridge`／`Infra`；複合以 `+` 連接（例 `FE+BE+Bridge`） |
| Phase | PRD §10 的 1～6（歸屬規則見 §1.3；是 PRD 里程碑歸屬，不是施工波次，波次見 Implementation_Plan.md） |
| 實作檔 | 相對 `AgentConsole/` 的路徑，多個以 `、` 分隔；初值 `待填` |
| 自動測試 | `測試檔::測試名`（或 vitest／pytest／JUnit 的具名測試）；初值 `待填` |
| E2E 驗證 | 跨層實跑的指令或腳本名＋日期；由 QA 填；初值 `待填` |
| 狀態 | 見 §1.4；初值一律 `⬜ 未開始` |

### 1.2 ID 前綴

| 前綴 | 範圍 | 列數 |
|------|------|------|
| `US-` | PRD 使用者故事（沿用 PRD 原編號 US-P／G／T／I／E／M／S-nn） | 58 |
| `API-` | console-api（後端）端點與後端業務規則（含認證、健康檢查、回應格式、告警、自治等級、狀態機、DAG、匯入細節） | 91 |
| `BR-` | Engine Bridge 端點與行為（Architecture §10 契約逐條＋PRD §0.2.2 行為） | 25 |
| `NFR-` | 非功能需求（PRD §0.5、§9.1～§9.4；NFR-XPL＝跨平台補充） | 32 |
| `INF-` | 部署與資料庫（INF-SVC 服務／NET 網路／VOL 卷／DKR 映像／NGX nginx／ENV／CMD／DEV／PRF／HLT／RES／DB 資料表與遷移／DR 災難復原與監控／OPS 維運檢查） | 103 |
| `UI-` | 介面（UI-SCR 九畫面／LAY 四區塊／RSP 響應式／A11Y 可及性／DS 設計系統／MD Markdown 編輯器／OVL 覆蓋層／KPI 指標卡／CHT 圖表） | 52 |

> 本表所有需求列的行首一律為 `| <前綴>-`（前綴限上列六種），故 `grep -c '^| US-\|^| API-\|^| BR-\|^| NFR-\|^| INF-\|^| UI-'` 即總列數；說明用表格的 ID 欄一律加反引號，避免被誤計。

### 1.3 Phase 歸屬規則

| Phase | PRD §10.2 交付物 | 本表歸入的需求 |
|-------|------------------|----------------|
| 1 | 專案骨架、DB Schema、認證機制 | 骨架、四區塊版面與設計系統、認證、健康檢查、回應格式、資料表與遷移、compose 服務／網路／映像、Bridge `/health`、工程基線 NFR、跨平台基線 |
| 2 | 專案／目標／任務 CRUD | US-P／G／T、對應 API、專案／目標／任務 signoff、狀態機、Markdown 編輯器、對話框與 Toast、輸入驗證與審計 |
| 3 | BRD/PRD 匯入解析 | US-I、匯入 API 與 import signoff、Bridge decompose／sdd 端點、外呼 allowlist |
| 4 | 專案執行引擎 | US-E、執行 API 與 SSE、自治等級、DAG、Bridge runs 全系列與行為、review_requests 表 |
| 5 | 專案監控儀表板 | US-M、監控 API、告警規則、KPI 與圖表、alerts 表、總覽儀表板 |
| 6 | 系統設定＋完整整合測試 | US-S、設定 API、效能／安全／可靠性 NFR、§12 備援／備份／監控（INF-DR、INF-OPS）、可及性驗收 |

### 1.4 狀態圖例與回填權限

| 狀態 | 意義 | 誰可設 |
|------|------|--------|
| `⬜ 未開始` | 尚未施工 | 初值 |
| `🟡 部分` | 已做一部分，或僅做語法驗證（須在實作檔欄註明缺什麼） | 開發者 |
| `✅ 實作+測試` | 程式已完成且「自動測試」欄列出的測試實跑為綠（須附指令輸出） | 開發者 |
| `✅ 已驗證` | 已在「E2E 驗證」欄的指令實跑通過（跨層列須含真後端／真 Bridge） | QA；`INF-*` 列的驗證本身就是真機實跑，W2-B 實跑通過可直接設定 |
| `❌ 缺陷` | QA 實跑不符；於 Implementation_Plan 進度帳登缺陷並進 W5 修復 | QA |
| `⛔ 範圍外` | 掌舵者裁決不做（須附裁決日期與理由） | 主控 |

### 1.5 回填規則（機械可查）

1. 只改該列的「實作檔／自動測試／E2E 驗證／狀態」四格；ID、來源、摘要、層、Phase 變動須先在 ADR 或 Implementation_Plan 登記。
2. 新增需求＝新增一列（沿用前綴與遞增編號），不得塞進既有列。
3. 狀態升為 `✅` 必須附當回合真跑的輸出（指令＋關鍵行）；貼不出來就維持 `🟡`。
4. 儲存格內不得出現管線字元 `|`；路徑與測試名用 `、` 分隔。
5. 統計（§3）為建表時快照；回填後以 §3.4 指令現查，不手改數字。

## 2. 需求追溯總表

| ID | 來源 | 摘要（≤20 字） | 層 | Phase | 實作檔 | 自動測試 | E2E 驗證 | 狀態 |
|----|------|----------------|----|-------|--------|----------|----------|------|
| US-P-01 | PRD §5.1.1 | 建立專案（初始 DRAFT） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateProjectRequest.java、frontend/components/domain/entity/EntityForms.tsx、frontend/components/domain/entity/EntityEditor.tsx、frontend/components/domain/entity/EntityDialog.tsx、frontend/components/domain/entity/schemas.ts、frontend/components/domain/entity/EntityFormPage.tsx、frontend/app/projects/new/page.tsx（後端＋前端 W3-A 完成） | ProjectApiIT::manualCreateReturns201WithDraftStatusSignedOffTrueAndDefaults、ProjectApiIT::draftTrueCreatesAnUnsignedProjectAndCustomAutonomyIsKept、ProjectApiIT::invalidCreateInputIsRejectedWithFieldErrors、ProjectTest::manuallyCreatedProjectStartsAsDraftAlreadySignedOffWithDefaultAutonomy、ProjectTest::creationCollectsEveryViolationAtOnce、frontend/components/domain/entity/schemas.test.ts::表單驗證（繁中訊息；後端仍是權威）、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-P-02 | PRD §5.1.1 | 專案列表含搜尋與排序 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/adapter/out/persistence/ProjectRepositoryAdapter.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectSummaryResponse.java、frontend/components/domain/views/ProjectsView.tsx、frontend/components/domain/ProjectCard.tsx、frontend/app/projects/page.tsx、frontend/components/layout/TopRegion.tsx（後端＋前端 W3-A 完成） | ProjectApiIT::listPaginatesAndReportsTotals、ProjectApiIT::defaultSortIsUpdatedAtDescendingAndNameSortsBothWays、ProjectApiIT::nameSearchIsCaseInsensitiveAndTreatsWildcardCharactersLiterally、ProjectApiIT::statusFilterAndInvalidQueryParametersAreHandled、ProjectApiIT::listShowsOnlyLiveGoalAndTaskCounts、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/shells-and-layout.spec.ts::搜尋列 Enter → /projects?q=，列表只留符合者並可清除 | 待填 | ✅ 實作+測試 |
| US-P-03 | PRD §5.1.1 | 專案詳情含 Markdown 渲染 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectDetailResponse.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、frontend/components/domain/views/ProjectDetailView.tsx、frontend/components/markdown/MarkdownView.tsx、frontend/app/projects/[projectId]/page.tsx（後端＋前端 W3-A 完成） | ProjectApiIT::detailIncludesGoalsWithTaskCountsInSortOrder、frontend/components/markdown/markdown.test.tsx::UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-P-04 | PRD §5.1.1 | 編輯專案（EXECUTING 受限） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateProjectRequest.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、frontend/components/domain/entity/EntityEditor.tsx、frontend/components/domain/entity/EntityForms.tsx、frontend/app/projects/[projectId]/edit/page.tsx（後端＋前端 W3-A 完成；EXECUTING 受限的欄位鎖定只有請求轉換的單元測試：後端沒有把專案轉成 EXECUTING 的入口，無法用真資料驗證 UI 行為） | ProjectApiIT::putUpdatesOnlyProvidedFieldsAndClearsDescriptionWithBlank、ProjectApiIT::whileExecutingOnlyNameAndDescriptionCanChangeAndOtherChangesAre409WithReason、ProjectTest::whileExecutingChangingOtherFieldsIsConflictWithReasonAndFieldList、ProjectTest::whileExecutingOnlyNameAndDescriptionMayChange、frontend/components/domain/entity/schemas.test.ts::請求轉換、frontend/tests/e2e/shells-and-layout.spec.ts::PRD §4.2 的 new／edit／goals／tasks 路由都存在且可深連結 | 待填 | 🟡 部分 |
| US-P-05 | PRD §5.1.1 | 軟刪除專案（執行中禁止） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、frontend/components/domain/views/ProjectDetailView.tsx、frontend/components/domain/ConfirmDialog.tsx（後端＋前端 W3-A 完成；EXECUTING 禁刪的 409 由後端把關，前端把訊息（含 traceId）顯示在確認對話框內） | ProjectApiIT::deleteIsSoftAndCascadesToGoalsAndTasks、ProjectApiIT::executingProjectCannotBeDeleted、ProjectTest::executingProjectCannotBeDeleted、ProjectTest::softDeleteArchivesAndMarksDeleted、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-P-06 | PRD §5.1.1 | 詳情頁目標標題與任務數 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectDetailResponse.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/GoalBrief.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、frontend/components/domain/GoalListCard.tsx、frontend/components/domain/views/ProjectDetailView.tsx（後端＋前端 W3-A 完成） | ProjectApiIT::detailIncludesGoalsWithTaskCountsInSortOrder、ProjectGoalTaskFlowIT::projectGoalTaskLifecycleEndToEnd、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-G-01 | PRD §5.1.2 | 在專案下建立目標 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateGoalRequest.java、frontend/components/domain/entity/EntityForms.tsx、frontend/components/domain/GoalListCard.tsx、frontend/app/projects/[projectId]/goals/new/page.tsx（後端＋前端 W3-A 完成） | GoalApiIT::createReturns201AssignsSortOrderAtTheEndAndStartsPendingSignedOff、GoalApiIT::draftGoalIsNotSignedOffAndInvalidInputIs400、GoalApiIT::createUnderAMissingOrDeletedProjectIs404、GoalTest::createStartsPendingWithGivenSortOrderAndManualGoalIsSignedOff、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/shells-and-layout.spec.ts::PRD §4.2 的 new／edit／goals／tasks 路由都存在且可深連結 | 待填 | ✅ 實作+測試 |
| US-G-02 | PRD §5.1.2 | 目標列表含任務數與比例 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/GoalSummaryResponse.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、frontend/components/domain/GoalListCard.tsx、frontend/components/domain/views/ListPages.tsx、frontend/app/projects/[projectId]/goals/page.tsx（後端＋前端 W3-A 完成） | GoalApiIT::listShowsTaskCountsAndCompletionRatioInSortOrder、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/shells-and-layout.spec.ts::PRD §4.2 的 new／edit／goals／tasks 路由都存在且可深連結 | 待填 | ✅ 實作+測試 |
| US-G-03 | PRD §5.1.2 | 目標詳情含說明與任務清單 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/GoalDetailResponse.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、frontend/components/domain/views/GoalDetailView.tsx、frontend/components/domain/TaskListCard.tsx、frontend/components/markdown/MarkdownView.tsx（後端＋前端 W3-A 完成） | GoalApiIT::detailListsTaskTitlesAndDependencies、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-G-04 | PRD §5.1.2 | 編輯目標（含排序） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateGoalRequest.java、frontend/components/domain/entity/EntityEditor.tsx、frontend/app/projects/[projectId]/goals/[goalId]/edit/page.tsx（後端＋前端 W3-A 完成） | GoalApiIT::updateChangesOnlyProvidedFields、GoalTest::updateChangesProvidedFieldsOnlyAndTouchesUpdatedAtOnlyWhenChanged、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/components/domain/entity/apiErrors.test.ts::後端錯誤 → 表單欄位 | 待填 | ✅ 實作+測試 |
| US-G-05 | PRD §5.1.2 | 軟刪除目標並連帶任務 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、frontend/components/domain/views/GoalDetailView.tsx、frontend/components/domain/ConfirmDialog.tsx（後端＋前端 W3-A 完成） | GoalApiIT::deleteIsSoftAndTakesItsTasksWithIt、GoalApiIT::aGoalWithARunningTaskCannotBeDeleted、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-G-06 | PRD §5.1.2 | 拖曳調整目標順序 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ReorderRequest.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、frontend/components/domain/GoalListCard.tsx、frontend/lib/api/queries.ts（後端＋前端 W3-A 完成；指標拖曳（@dnd-kit）與重新整理後順序保持由 E2E 驗證，鍵盤拖曳為套件內建行為、未另測） | GoalApiIT::reorderRewritesSortOrderToMatchTheGivenSequence、GoalApiIT::reorderRejectsIncompleteUnknownDuplicateAndForeignIds、GoalTest::moveToChangesSortOrderOnly、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/lib/api/endpoints.test.ts::endpoints：每個後端端點一個函式 | 待填 | ✅ 實作+測試 |
| US-G-07 | PRD §5.1.2 | 設定目標間依賴關係 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/service/DagService.java、backend/src/main/java/com/aisdlc/console/adapter/out/persistence/GoalRepositoryAdapter.java、frontend/components/domain/entity/EntityForms.tsx、frontend/components/domain/views/GoalDetailView.tsx（後端＋前端 W3-A 完成；已做前置依賴多選、成環原因顯示與詳情 chips，「依賴拓撲」視覺化（DAG）屬 W4 執行頁） | GoalApiIT::dependenciesKeepTheOrderGivenAndUpdateReplacesTheWholeSet、GoalApiIT::aDiamondShapedGraphIsAccepted、GoalApiIT::aTwoGoalCycleIsRejectedWithTheCyclePathAndNothingIsPersisted、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/components/domain/entity/apiErrors.test.ts::後端錯誤 → 表單欄位 | 待填 | 🟡 部分 |
| US-T-01 | PRD §5.1.3 | 在目標下建立任務 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateTaskRequest.java、frontend/components/domain/entity/EntityForms.tsx、frontend/components/domain/TaskListCard.tsx、frontend/app/projects/[projectId]/goals/[goalId]/tasks/new/page.tsx（後端＋前端 W3-A 完成） | TaskApiIT::createReturns201WithDocumentedDefaults、TaskApiIT::createAcceptsTheMachineReadablePassCriteriaAndStoresTheSpecAsAJsonbObject、TaskApiIT::draftTaskIsNotSignedOffAndInvalidInputIs400、TaskApiIT::createUnderAMissingGoalIs404、TaskTest::createStartsPendingWithDefaultsAndManualTaskIsSignedOff、frontend/components/domain/entity/schemas.test.ts::表單驗證（繁中訊息；後端仍是權威）、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-T-02 | PRD §5.1.3 | 任務詳情含 Markdown 與歷史 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/TaskDetailResponse.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ExecutionStepBrief.java、frontend/components/domain/views/TaskDetailView.tsx、frontend/components/markdown/MarkdownView.tsx（後端＋前端 W3-A 完成；後端備註：executionHistory 目前恆為空清單，Phase 4 起由 execution_steps 衍生；執行歷史清單已實作，但後端 Phase 2 恆回空清單，未用非空資料驗證） | TaskApiIT::detailCarriesTheExecutionLogAndAnEmptyExecutionHistory、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/task-retry.spec.ts::FAILED 任務可重試：送出 POST /retry，toast 顯示重試 1 / 3；日誌可搜尋 | 待填 | 🟡 部分 |
| US-T-03 | PRD §5.1.3 | 編輯任務（含最大重試） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateTaskRequest.java、frontend/components/domain/entity/EntityEditor.tsx、frontend/app/projects/[projectId]/goals/[goalId]/tasks/[taskId]/edit/page.tsx（後端＋前端 W3-A 完成） | TaskApiIT::updateChangesProvidedFieldsAndBlankClearsOptionalOnes、TaskTest::updateChangesOnlyProvidedFieldsAndBlankClearsOptionalOnes、TaskTest::updateAppliesSanitizationJustLikeCreate、frontend/components/domain/entity/schemas.test.ts::表單驗證（繁中訊息；後端仍是權威）、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-T-04 | PRD §5.1.3 | 軟刪除任務（RUNNING 禁止） | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、frontend/components/domain/views/TaskDetailView.tsx、frontend/components/domain/ConfirmDialog.tsx（後端＋前端 W3-A 完成；RUNNING 禁刪的 409 由後端把關） | TaskApiIT::aRunningTaskCannotBeDeletedButAnyOtherCanBe、TaskTest::runningTaskCannotBeDeleted、TaskTest::anyNonRunningTaskCanBeSoftDeleted、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除 | 待填 | ✅ 實作+測試 |
| US-T-05 | PRD §5.1.3 | 查看任務執行日誌並搜尋 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/TaskDetailResponse.java、frontend/components/domain/LogPanel.tsx、frontend/components/domain/views/TaskDetailView.tsx（後端＋前端 W3-A 完成；後端備註：詳情回傳 executionLog，內容由 Phase 4 執行事件寫入；搜尋／篩選以 route mock 提供的日誌驗證，真實日誌內容由 Phase 4 執行事件寫入） | TaskApiIT::detailCarriesTheExecutionLogAndAnEmptyExecutionHistory、frontend/tests/e2e/task-retry.spec.ts::FAILED 任務可重試：送出 POST /retry，toast 顯示重試 1 / 3；日誌可搜尋 | 待填 | ✅ 實作+測試 |
| US-T-06 | PRD §5.1.3 | 手動重試失敗任務 | FE+BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、frontend/components/domain/views/TaskDetailView.tsx、frontend/lib/domain/status.ts（後端＋前端 W3-A 完成；FAILED／ESCALATED 才啟用；後端無法產生 FAILED 任務，該情境以 route mock 驗證） | TaskApiIT::retryFromFailedOrEscalatedIncrementsRetryCountAndRequeues、TaskApiIT::retryFromAnyOtherStatusIsConflictAndChangesNothing、TaskTest::retryIsAllowedOnlyFromFailedOrEscalated、TaskTest::retryFromAnyOtherStatusIsConflictAndChangesNothing、frontend/tests/e2e/task-retry.spec.ts::FAILED 任務可重試：送出 POST /retry，toast 顯示重試 1 / 3；日誌可搜尋、frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/lib/domain/status.test.ts::狀態 enum 對照表（lib/domain/status.ts 是唯一出處） | 待填 | ✅ 實作+測試 |
| US-I-01 | PRD §5.2.3 | 上傳 BRD/PRD（≤10MB） | FE+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-02 | PRD §5.2.3 | 貼上純文字需求 | FE+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-03 | PRD §5.2.3 | 三層結構樹狀預覽 | FE+BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-04 | PRD §5.2.3 | 匯入前編輯三層結構 | FE+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-05 | PRD §5.2.3 | 設定匯入執行路徑 | FE+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-06 | PRD §5.2.3 | 查看歷史匯入記錄 | FE+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-07 | PRD §5.2.3 | 解析前選擇自治等級 | FE+BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-08 | PRD §5.2.3 | 解析前提供額外提示 | FE+BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-09 | PRD §5.2.3 | signoff 後才落為正式項目 | FE+BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-I-10 | PRD §5.2.3 | 逾界拆解顯示明確原因 | FE+BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-01 | PRD §5.3.4 | 啟動執行（signoff 校驗） | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-02 | PRD §5.3.4 | 選擇執行範圍 | FE+BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-03 | PRD §5.3.4 | SSE 即時執行日誌 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-04 | PRD §5.3.4 | 暫停執行 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-05 | PRD §5.3.4 | 恢復暫停的執行 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-06 | PRD §5.3.4 | 取消執行 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-07 | PRD §5.3.4 | 審核請求通知與 Badge | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-08 | PRD §5.3.4 | 審核結果（通過/拒絕/重試） | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-09 | PRD §5.3.4 | DAG 依賴圖與進度 | FE+BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-10 | PRD §5.3.4 | 設定 Token 上限 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-E-11 | PRD §5.3.4 | 從 Checkpoint 恢復 | FE+BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-01 | PRD §5.4.3 | 儀表板整體健康度 KPI | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-02 | PRD §5.4.3 | Token 使用趨勢含預算線 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-03 | PRD §5.4.3 | 任務執行時間軸 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-04 | PRD §5.4.3 | 搜尋篩選執行日誌 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-05 | PRD §5.4.3 | 異常告警通知 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-06 | PRD §5.4.3 | 比較執行批次效能 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-07 | PRD §5.4.3 | 匯出 PDF／CSV 報表 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-08 | PRD §5.4.3 | 自訂儀表板（拖曳） | FE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-09 | PRD §5.4.3 | 執行批次完整追蹤鏈 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-M-10 | PRD §5.4.3 | Agent 即時狀態 | FE+BE+Bridge | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-01 | PRD §5.5.3 | 依分類查看系統參數 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-02 | PRD §5.5.3 | 修改參數（敏感二次確認） | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-03 | PRD §5.5.3 | 重置參數為預設值 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-04 | PRD §5.5.3 | 敏感參數遮罩顯示 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-05 | PRD §5.5.3 | 測試模型連線 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-06 | PRD §5.5.3 | 匯出／匯入系統設定 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-07 | PRD §5.5.3 | 查看參數修改歷史 | FE+BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| US-S-08 | PRD §5.5.3 | 關鍵參數影響範圍提示 | FE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-PRJ-01 | PRD §7.1.1 · POST /api/v1/projects | 建立專案（201） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateProjectRequest.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectResponse.java | ProjectApiIT::manualCreateReturns201WithDraftStatusSignedOffTrueAndDefaults、ProjectApiIT::draftTrueCreatesAnUnsignedProjectAndCustomAutonomyIsKept、ProjectApiIT::invalidCreateInputIsRejectedWithFieldErrors、ProjectApiIT::windowsAndUncAbsolutePathsAreAccepted、ProjectApiIT::malformedJsonBodyIsFourHundredNotFiveHundred | 待填 | ✅ 實作+測試 |
| API-PRJ-02 | PRD §7.1.1 · GET /api/v1/projects | 專案列表（分頁） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/adapter/out/persistence/ProjectRepositoryAdapter.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectSummaryResponse.java | ProjectApiIT::listPaginatesAndReportsTotals、ProjectApiIT::defaultSortIsUpdatedAtDescendingAndNameSortsBothWays、ProjectApiIT::nameSearchIsCaseInsensitiveAndTreatsWildcardCharactersLiterally、ProjectApiIT::statusFilterAndInvalidQueryParametersAreHandled、ProjectApiIT::listShowsOnlyLiveGoalAndTaskCounts | 待填 | ✅ 實作+測試 |
| API-PRJ-03 | PRD §7.1.1 · GET /api/v1/projects/{id} | 專案詳情 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ProjectDetailResponse.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java | ProjectApiIT::detailIncludesGoalsWithTaskCountsInSortOrder、ProjectApiIT::unknownIdsAre404AndMalformedIdsAre400 | 待填 | ✅ 實作+測試 |
| API-PRJ-04 | PRD §7.1.1 · PUT /api/v1/projects/{id} | 更新專案 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateProjectRequest.java | ProjectApiIT::putUpdatesOnlyProvidedFieldsAndClearsDescriptionWithBlank、ProjectApiIT::whileExecutingOnlyNameAndDescriptionCanChangeAndOtherChangesAre409WithReason、ProjectApiIT::manualStatusChangeIsLimitedToDraftAndReadyAndFollowsTheStateMachine、ProjectTest::illegalStatusChangeLeavesTheOtherFieldsUntouched | 待填 | ✅ 實作+測試 |
| API-PRJ-05 | PRD §7.1.1 · DELETE /api/v1/projects/{id} | 軟刪除專案（204） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java | ProjectApiIT::deleteIsSoftAndCascadesToGoalsAndTasks、ProjectApiIT::executingProjectCannotBeDeleted、ProjectGoalTaskFlowIT::projectGoalTaskLifecycleEndToEnd | 待填 | ✅ 實作+測試 |
| API-GOL-01 | PRD §7.1.2 · POST /api/v1/projects/{projectId}/goals | 建立目標（201） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateGoalRequest.java | GoalApiIT::createReturns201AssignsSortOrderAtTheEndAndStartsPendingSignedOff、GoalApiIT::draftGoalIsNotSignedOffAndInvalidInputIs400、GoalApiIT::createUnderAMissingOrDeletedProjectIs404 | 待填 | ✅ 實作+測試 |
| API-GOL-02 | PRD §7.1.2 · GET /api/v1/projects/{projectId}/goals | 目標列表 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/GoalSummaryResponse.java | GoalApiIT::listShowsTaskCountsAndCompletionRatioInSortOrder | 待填 | ✅ 實作+測試 |
| API-GOL-03 | PRD §7.1.2 · GET /api/v1/goals/{id} | 目標詳情 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/GoalDetailResponse.java | GoalApiIT::detailListsTaskTitlesAndDependencies | 待填 | ✅ 實作+測試 |
| API-GOL-04 | PRD §7.1.2 · PUT /api/v1/goals/{id} | 更新目標 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateGoalRequest.java | GoalApiIT::updateChangesOnlyProvidedFields、GoalApiIT::dependenciesKeepTheOrderGivenAndUpdateReplacesTheWholeSet | 待填 | ✅ 實作+測試 |
| API-GOL-05 | PRD §7.1.2 · DELETE /api/v1/goals/{id} | 軟刪除目標（204） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java | GoalApiIT::deleteIsSoftAndTakesItsTasksWithIt、GoalApiIT::aGoalWithARunningTaskCannotBeDeleted | 待填 | ✅ 實作+測試 |
| API-GOL-06 | PRD §7.1.2 · PUT /api/v1/goals/reorder | 調整目標順序（204） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ReorderRequest.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java | GoalApiIT::reorderRewritesSortOrderToMatchTheGivenSequence、GoalApiIT::reorderRejectsIncompleteUnknownDuplicateAndForeignIds、ResponseEnvelopeIT::deleteAndReorderReturnNoContentWithAnEmptyBody | 待填 | ✅ 實作+測試 |
| API-TSK-01 | PRD §7.1.3 · POST /api/v1/goals/{goalId}/tasks | 建立任務（201） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateTaskRequest.java | TaskApiIT::createReturns201WithDocumentedDefaults、TaskApiIT::createAcceptsTheMachineReadablePassCriteriaAndStoresTheSpecAsAJsonbObject、TaskApiIT::draftTaskIsNotSignedOffAndInvalidInputIs400、TaskApiIT::createUnderAMissingGoalIs404 | 待填 | ✅ 實作+測試 |
| API-TSK-02 | PRD §7.1.3 · GET /api/v1/goals/{goalId}/tasks | 任務列表 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/TaskSummaryResponse.java | TaskApiIT::listIsOrderedAndHidesDeletedTasks | 待填 | ✅ 實作+測試 |
| API-TSK-03 | PRD §7.1.3 · GET /api/v1/tasks/{id} | 任務詳情 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/TaskDetailResponse.java | TaskApiIT::detailCarriesTheExecutionLogAndAnEmptyExecutionHistory | 待填 | ✅ 實作+測試 |
| API-TSK-04 | PRD §7.1.3 · PUT /api/v1/tasks/{id} | 更新任務 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/UpdateTaskRequest.java | TaskApiIT::updateChangesProvidedFieldsAndBlankClearsOptionalOnes、TaskApiIT::everyBlacklistedCharacterIsRejectedOnCreateAndUpdateAndNamedInTheResponse、TaskTest::updateAppliesSanitizationJustLikeCreate | 待填 | ✅ 實作+測試 |
| API-TSK-05 | PRD §7.1.3 · DELETE /api/v1/tasks/{id} | 軟刪除任務（204） | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java | TaskApiIT::aRunningTaskCannotBeDeletedButAnyOtherCanBe、TaskTest::runningTaskCannotBeDeleted | 待填 | ✅ 實作+測試 |
| API-TSK-06 | PRD §7.1.3 · POST /api/v1/tasks/{id}/retry | 重試任務 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java | TaskApiIT::retryFromFailedOrEscalatedIncrementsRetryCountAndRequeues、TaskApiIT::retryFromAnyOtherStatusIsConflictAndChangesNothing、TaskApiIT::retryOfAnUnknownTaskIs404、TaskTest::retryIsAllowedOnlyFromFailedOrEscalated | 待填 | ✅ 實作+測試 |
| API-IMP-01 | PRD §7.1.4 · POST /api/v1/import/upload | 上傳檔案（201） | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-02 | PRD §7.1.4 · POST /api/v1/import/text | 貼上純文字（201） | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-03 | PRD §7.1.4 · POST /api/v1/import/{id}/parse | 觸發 AI 解析 | BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-04 | PRD §7.1.4 · PUT /api/v1/import/{id}/result | 編輯解析結果 | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-05 | PRD §7.1.4 · POST /api/v1/import/{id}/confirm | 確認匯入並建專案（201） | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-06 | PRD §7.1.4 · GET /api/v1/import | 查詢匯入歷史 | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SGN-01 | PRD §7.1.4.1 · POST /api/v1/import/{id}/signoff | 審批匯入草案 | BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SGN-02 | PRD §7.1.4.1 · POST /api/v1/projects/{id}/signoff | 審批專案草案 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/ProjectController.java、backend/src/main/java/com/aisdlc/console/application/service/ProjectService.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/SignoffRequest.java | ProjectApiIT::signoffOnADraftRecordsApproverAndUtcTime、ProjectApiIT::signoffWithoutAnApproverIsFourHundred、ProjectApiIT::signingOffTwiceIsConflictAndKeepsTheFirstApprover、ProjectTest::signoffRecordsApproverAndTimeOnADraft | 待填 | ✅ 實作+測試 |
| API-SGN-03 | PRD §7.1.4.1 · POST /api/v1/goals/{id}/signoff | 審批目標草案 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/GoalController.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/SignoffRequest.java | GoalApiIT::goalSignoffFollowsTheSameRulesAsProjects、GoalTest::signoffRulesMatchTheProjectOnes | 待填 | ✅ 實作+測試 |
| API-SGN-04 | PRD §7.1.4.1 · POST /api/v1/tasks/{id}/signoff | 審批任務草案 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/TaskController.java、backend/src/main/java/com/aisdlc/console/application/service/TaskService.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/SignoffRequest.java | TaskApiIT::taskSignoffFollowsTheSameRulesAsProjectsAndGoals、TaskTest::signoffRulesMatchTheProjectOnes | 待填 | ✅ 實作+測試 |
| API-EXE-01 | PRD §7.1.5 · POST /api/v1/projects/{projectId}/execute | 啟動專案執行（201） | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-02 | PRD §7.1.5 · POST /api/v1/executions/{runId}/pause | 暫停執行 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-03 | PRD §7.1.5 · POST /api/v1/executions/{runId}/resume | 恢復執行 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-04 | PRD §7.1.5 · POST /api/v1/executions/{runId}/cancel | 取消執行 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-05 | PRD §7.1.5 · GET /api/v1/executions/{runId} | 查詢執行狀態 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-06 | PRD §7.1.5 · GET /api/v1/executions/{runId}/steps | 分頁查詢執行步驟 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-07 | PRD §7.1.5 · GET /api/v1/executions/{runId}/dag | 查詢 DAG 圖 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-08 | PRD §7.1.5 · GET /api/v1/executions/{runId}/checkpoints | 查詢斷點列表 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-09 | PRD §7.1.5 · POST /api/v1/executions/{runId}/restore/{checkpointId} | 從歷史斷點還原 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-10 | PRD §7.1.5 · POST /api/v1/executions/{runId}/review/{stepId} | 審核執行結果（204） | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-11 | PRD §7.1.5 前置硬校驗 · §0.4 | 未 signoff 啟動回 409 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-12 | PRD §7.1.5 並發互斥 · §0.2.2 | 並發互斥回 409 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-13 | PRD §0.3 · Arch §6(c) | 任務物化為 Playbook | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-EXE-14 | Arch §11.1 補充 · GET /api/v1/projects/{projectId}/executions | 列出專案執行批次（補） | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-01 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/metrics | 查詢專案指標 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-02 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/token-trend | Token 使用趨勢 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-03 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/task-trend | 任務執行趨勢 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-04 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/alerts | 查詢告警 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-05 | PRD §7.1.6 · POST /api/v1/monitor/alerts/{alertId}/acknowledge | 確認告警（204） | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-06 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/logs | 查詢結構化日誌 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-MON-07 | PRD §7.1.6 · GET /api/v1/monitor/projects/{projectId}/report | 匯出報表（PDF/CSV） | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-NTF-01 | Arch §11.1 補充 · GET /api/v1/notifications/summary | 通知與待審批計數（補） | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SSE-01 | PRD §7.1.7 · GET /api/v1/stream/executions/{runId}/logs | 即時日誌 SSE | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SSE-02 | PRD §7.1.7 · GET /api/v1/stream/executions/{runId}/metrics | 即時指標 SSE | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SSE-03 | PRD §7.1.7 斷線重播 | Last-Event-ID 斷線重播 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-01 | PRD §7.1.8 · GET /api/v1/settings | 查詢全部參數 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-02 | PRD §7.1.8 · GET /api/v1/settings/{category} | 查詢分類參數 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-03 | PRD §7.1.8 · PUT /api/v1/settings/{category}/{key} | 更新單鍵參數 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-04 | PRD §7.1.8 · PUT /api/v1/settings/execution/token-guard | 原子更新 token_guard | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-05 | PRD §7.1.8 · POST /api/v1/settings/{category}/{key}/reset | 重置為預設值 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-06 | PRD §7.1.8 · POST /api/v1/settings/test-connection | 測試模型連線 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-07 | PRD §7.1.8 · GET /api/v1/settings/history | 查詢修改歷史 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-08 | PRD §7.1.8 · POST /api/v1/settings/export | 匯出設定 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-09 | PRD §7.1.8 · POST /api/v1/settings/import | 匯入設定 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-SET-10 | PRD §0.6 · §5.5.1 | 設定物化為引擎參數 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUTH-01 | ADR-001 D4 · POST /api/v1/auth/login | 登入取得 JWT | BE | 1 | backend/src/main/java/com/aisdlc/console/adapter/in/web/AuthController.java、backend/src/main/java/com/aisdlc/console/application/service/AuthService.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/JwtTokenService.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/ConsoleAuthProperties.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/ConfiguredUserDirectory.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/BcryptPasswordVerifier.java、backend/src/main/resources/application.yml | AuthApiIT::eachConfiguredUserLogsInAndReceivesTheirRoleAndAThirtyMinuteToken、AuthApiIT::wrongPasswordAndUnknownUserGetTheSameFourZeroOneSoAccountsCannotBeEnumerated、AuthApiIT::missingFieldsAreRejectedWithFieldLevelErrors、ConsoleAuthPropertiesTest::aMissingSecretFailsStartupAndNamesTheEnvironmentVariable、BcryptPasswordVerifierTest::theHtpasswdStyleVariantPrefixesAreAccepted | 待填 | ✅ 實作+測試 |
| API-AUTH-02 | ADR-001 D4 · POST /api/v1/auth/refresh | 以 refresh 換新 token | BE | 1 | backend/src/main/java/com/aisdlc/console/adapter/in/web/AuthController.java、backend/src/main/java/com/aisdlc/console/application/service/AuthService.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/JwtTokenService.java | AuthApiIT::refreshTokenIssuesAFreshWorkingPair、AuthApiIT::anAccessTokenCannotBeUsedAsARefreshTokenAndViceVersa、AuthApiIT::anExpiredAccessTokenIsToldApartFromAnInvalidOne、AuthApiIT::tamperedWrongKeyAndAlgNoneTokensAreAllRejected、JwtTokenServiceTest::validAccessAndRefreshTokensVerifyForTheirOwnUseOnly | 待填 | ✅ 實作+測試 |
| API-HLT-01 | PRD §11.3 · GET /actuator/health | 後端健康檢查 | BE | 1 | backend/src/main/resources/application.yml、backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java | ActuatorIT::healthIsUpWithoutATokenAndHidesComponentDetails、ActuatorIT::livenessAndReadinessProbesAreExposed、RbacIT::publicEndpointsNeedNoToken | 待填 | ✅ 實作+測試 |
| API-HLT-02 | PRD §12.6.1 · GET /actuator/prometheus | Prometheus 指標端點 | BE | 1 | backend/build.gradle.kts、backend/src/main/resources/application.yml、backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java | ActuatorIT::prometheusExposesJvmDatabasePoolAndHttpMetricsWithoutAToken、RbacIT::publicEndpointsNeedNoToken | 待填 | ✅ 實作+測試 |
| API-HLT-03 | PRD §11.3 · GET /api/health（前端） | 前端健康檢查 | FE | 1 | frontend/app/api/health/route.ts、frontend/Dockerfile | frontend/app/api/health/route.test.ts::前端健康檢查（API-HLT-03） | 待填 | ✅ 實作+測試 |
| API-FMT-01 | PRD §7.2 | 統一回應封包 | BE | 1 | backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ApiResult.java、backend/src/main/java/com/aisdlc/console/infrastructure/config/TraceIdFilter.java、backend/src/main/java/com/aisdlc/console/infrastructure/config/WebConfig.java | ResponseEnvelopeIT::successEnvelopeHasExactlyTheDocumentedKeys、ResponseEnvelopeIT::traceIdIsAFreshUuidPerRequestAndMatchesTheResponseHeader、ResponseEnvelopeIT::aClientSuppliedTraceIdIsIgnored、ResponseEnvelopeIT::deleteAndReorderReturnNoContentWithAnEmptyBody | 待填 | ✅ 實作+測試 |
| API-FMT-02 | PRD §7.2 | 分頁回應格式 | BE | 1 | backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/PageData.java、backend/src/main/java/com/aisdlc/console/application/port/in/PageResult.java | ResponseEnvelopeIT::paginationEnvelopeCarriesContentPageSizeTotalElementsAndTotalPages、ProjectApiIT::listPaginatesAndReportsTotals | 待填 | ✅ 實作+測試 |
| API-FMT-03 | PRD §7.2 | 錯誤回應含欄位明細 | BE | 1 | backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/ApiError.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/GlobalExceptionHandler.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/RestSecurityHandlers.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/ErrorResponseDocumentation.java | ResponseEnvelopeIT::validationErrorEnvelopeListsEveryFieldProblem、ResponseEnvelopeIT::everyKindOfErrorUsesTheSameEnvelope、GlobalExceptionHandlerTest::eachDomainExceptionMapsToItsHttpStatus、GlobalExceptionHandlerTest::anUnexpectedExceptionIsAGenericFiveHundredThatLeaksNothing、OpenApiIT::theErrorEnvelopeIsDocumentedSoClientsCanTypeIt | 待填 | ✅ 實作+測試 |
| API-ALR-01 | PRD §5.4.4 | Token 達預算 80% 警告 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-ALR-02 | PRD §5.4.4 | Token 超預算自動暫停 | BE+Bridge | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-ALR-03 | PRD §5.4.4 | 連續 3 失敗暫停目標 | BE+Bridge | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-ALR-04 | PRD §5.4.4 | Agent 逾 5 分鐘無回應 | BE+Bridge | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-ALR-05 | PRD §5.4.4 | 任務逾時 200% 警告 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-ALR-06 | PRD §5.4.4 | 目標重試率逾 50% 警告 | BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-01 | PRD §5.3.2 | Level 1 每任務前確認 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-02 | PRD §5.3.2 | Level 2 每目標前確認 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-03 | PRD §5.3.2 | Level 3 目標完成與失敗審核 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-04 | PRD §5.3.2 | Level 4 僅升級時介入 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-05 | PRD §5.3.2 | Level 5 全自動含重試 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-AUT-06 | PRD §5.3.2 | Level 6-10 等級傳遞引擎 | BE+Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-STM-01 | PRD 附錄 B.1 | 專案狀態機轉移 | BE | 2 | backend/src/main/java/com/aisdlc/console/domain/service/StateMachines.java、backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java | StateMachinesTest::projectTransitionsFollowAppendixB1、ProjectTest::manualStatusChangeFollowsTheStateMachine、ProjectApiIT::manualStatusChangeIsLimitedToDraftAndReadyAndFollowsTheStateMachine | 待填 | ✅ 實作+測試 |
| API-STM-02 | PRD 附錄 B.2 | 目標狀態機轉移 | BE | 2 | backend/src/main/java/com/aisdlc/console/domain/service/StateMachines.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java | StateMachinesTest::goalTransitionsFollowAppendixB2、GoalTest::statusTransitionsFollowAppendixB2 | 待填 | ✅ 實作+測試 |
| API-STM-03 | PRD 附錄 B.3 · §5.3.3 | 任務狀態機轉移 | BE | 2 | backend/src/main/java/com/aisdlc/console/domain/service/StateMachines.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java | StateMachinesTest::taskTransitionsFollowAppendixB3、TaskTest::transitionToFollowsAppendixB3、TaskApiIT::retryFromAnyOtherStatusIsConflictAndChangesNothing | 待填 | ✅ 實作+測試 |
| API-DAG-01 | PRD §5.3.0 · §5.3.1 | DAG 建立與拓撲排序 | BE | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-DAG-02 | PRD §5.1.2 · §6.2 | 目標依賴 Kahn 防環 | BE | 2 | backend/src/main/java/com/aisdlc/console/domain/service/DagService.java、backend/src/main/java/com/aisdlc/console/application/service/GoalService.java、backend/src/main/java/com/aisdlc/console/adapter/out/persistence/GoalRepositoryAdapter.java | DagServiceTest::twoNodeCycleIsDetected、DagServiceTest::cycleExtractionIgnoresNodesDownstreamOfTheCycle、DagServiceTest::veryLongChainIsHandledIterativelyWithoutStackOverflow、GoalApiIT::aTwoGoalCycleIsRejectedWithTheCyclePathAndNothingIsPersisted、GoalApiIT::aThreeGoalCycleThroughATransitiveChainIsRejected、GoalApiIT::aGoalCannotDependOnItself、GoalApiIT::crossProjectAndMissingAndDeletedDependenciesAreRejected、GoalDependencyConcurrencyIT::concurrentOppositeDependenciesNeverBothSucceed | 待填 | ✅ 實作+測試 |
| API-IMP-07 | PRD §5.2.1 | 格式判斷與文字擷取 | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-08 | PRD §5.2.1 · §0.4 | 規格凍結偵測雙路徑 | BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-09 | PRD §5.2.4 | 解析輸出三層 JSON | BE+Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| API-IMP-10 | PRD §5.2.2 | 匯入記錄狀態機 | BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-01 | Arch §10 · GET /health | 健康檢查含引擎版本 | Bridge | 1 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-02 | Arch §10 · POST /autoclaude/runs | 建立執行（201/409/422） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-03 | Arch §10 · POST /autoclaude/runs/{run_id}:pause | 暫停（202 PAUSING） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-04 | Arch §10 · POST /autoclaude/runs/{run_id}:resume | 恢復（202 RUNNING） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-05 | Arch §10 · POST /autoclaude/runs/{run_id}:stop | 停止（202 CANCELLING） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-06 | Arch §10 · GET /autoclaude/runs/{run_id} | 查詢執行狀態 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-07 | Arch §10 · GET /autoclaude/runs/{run_id}/stream | SSE 串流（可重播） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-08 | Arch §10 · GET /autoclaude/runs/{run_id}/events | REST 事件重播 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-09 | Arch §10 · GET /autoclaude/runs/{run_id}/checkpoints | 列出歷史斷點 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-10 | Arch §10 · POST /autoclaude/runs/{run_id}/restore | 從斷點還原（202） | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-11 | Arch §10 · POST /autoclaude/decompose | 目標拆解（三道有界閘） | Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-12 | Arch §10 · POST /autoclaude/decompose/{draft_id}:approve | 草案 signoff（approver） | Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-13 | Arch §10 · GET /sdd/version | 回報 SDD LATEST 版 | Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-14 | Arch §10 · GET /sdd/fsm/{project} | 讀 FSM 狀態或 404 | Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-15 | Arch §10 · POST /sdd/compile | 規格編譯為任務或 422 | Bridge | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-16 | PRD §0.2.2 | 同專案同路徑互斥 409 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-17 | PRD §0.2.2 | 孤兒回收標 FAILED | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-18 | ADR-001 D8 | 暫停於步驟邊界生效 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-19 | PRD §0.2.2 · ADR-001 D8 | SIGTERM 逾時升 SIGKILL | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-20 | ADR-001 D8 | 恢復自 checkpoint 續跑 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-21 | ADR-001 D8 | 還原複製歷史 checkpoint | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-22 | Arch §7 · §10 | 寫 PG 僅用 PRD 六態 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-23 | PRD §0.2.2 · Arch §7 | execution_runs 寫入分工 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-24 | PRD §0.2.2 · Arch §7 | 步驟與斷點由 Bridge 寫 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| BR-25 | Arch §10 | SSE 事件格式與 seq | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-SEC-03 | PRD §0.5 | UI 輸入三層消毒 | BE+Bridge | 2 | backend/src/main/java/com/aisdlc/console/domain/service/PassCriteriaSanitizer.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/PassCriteriaSpecRules.java（後端第 1 層完成；Bridge 入口與兩端字元集 parity 腳本由 W4 QA 核對） | PassCriteriaSanitizerTest::denyCharsAreExactlyTheSsotSetOfEightCharacters、PassCriteriaSanitizerTest::everyDenyCharIsRejectedAndNamedInTheError、TaskApiIT::everyBlacklistedCharacterIsRejectedOnCreateAndUpdateAndNamedInTheResponse、TaskApiIT::theSameRulesApplyInsideTheStructuredPassCriteriaSpec、TaskApiIT::anUncompilableRegexOrTooLongFieldsAreRejected | 待填 | 🟡 部分 |
| NFR-SEC-04 | PRD §0.5 | 外呼預設 deny＋allowlist | Bridge+BE | 3 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-SEC-05 | PRD §0.5 · token_guard halt > compact | halt 須大於 compact | BE+FE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-OBS-01 | PRD §0.5 | 四源狀態一致 | BE+Bridge | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-REL-03 | PRD §0.5 | 備份以 §12 為準含離站 | Infra | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-COMPAT-01 | PRD §0.5 | 零侵入引擎核心 | Bridge | 1 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-01 | PRD §9.1 | 首頁 LCP 小於 2 秒 | FE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-02 | PRD §9.1 | API P95 小於 200ms | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-03 | PRD §9.1 | SSE 延遲小於 500ms | BE+Bridge | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-04 | PRD §9.1 | 列表查詢小於 500ms | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-05 | PRD §9.1 | Markdown 渲染小於 100ms | FE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.1-06 | PRD §9.1 | 並發使用者至少 50 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.2-01 | PRD §9.2 | JWT 30 分鐘＋Refresh | BE+FE | 1 | backend/src/main/java/com/aisdlc/console/infrastructure/security/JwtTokenService.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/JwtAuthenticationFilter.java（後端完成；前端 sessionStorage 與 401→refresh 流程待 W3） | JwtTokenServiceTest::issuedTokensCarryTheDocumentedLifetimesAndExpiresInSeconds、JwtTokenServiceTest::accessTokenExpiresExactlyAfterThirtyMinutesButRefreshStillLives、AuthApiIT::refreshTokenIssuesAFreshWorkingPair | 待填 | 🟡 部分 |
| NFR-9.2-02 | PRD §9.2 | RBAC 三角色授權 | BE | 1 | backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/RestSecurityHandlers.java | RbacIT::viewerCanReadEverythingButEveryWriteEndpointIs403AndChangesNothing、RbacIT::everyWriteEndpointRequiresAuthenticationWith401、RbacIT::operatorAndAdminMayWrite、RbacIT::otherActuatorEndpointsAreAdminOnly、RbacIT::roleIsTakenFromTheTokenNotFromAnythingTheClientSends | 待填 | ✅ 實作+測試 |
| NFR-9.2-03 | PRD §9.2 | 敏感資料 AES-256 加密 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.2-04 | PRD §9.2 | 輸入驗證與防 SQL 注入 | BE | 2 | backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/CreateProjectRequest.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/GlobalExceptionHandler.java、backend/src/main/java/com/aisdlc/console/adapter/out/persistence/ProjectRepositoryAdapter.java | ProjectApiIT::invalidCreateInputIsRejectedWithFieldErrors、ProjectApiIT::sqlMetaCharactersInSearchTextAndNamesAreNeverInterpretedAsSql、ProjectApiIT::nameSearchIsCaseInsensitiveAndTreatsWildcardCharactersLiterally、ProjectApiIT::malformedJsonBodyIsFourHundredNotFiveHundred | 待填 | ✅ 實作+測試 |
| NFR-9.2-05 | PRD §9.2 | CORS 限指定 Origin | BE | 1 | backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/ConsoleCorsProperties.java | RbacIT::corsAllowsOnlyTheConfiguredOrigin | 待填 | ✅ 實作+測試 |
| NFR-9.2-06 | PRD §9.2 | Rate Limit 每分鐘 100 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.2-07 | PRD §9.2 | 寫入操作審計日誌 | BE | 2 | backend/src/main/java/com/aisdlc/console/infrastructure/security/AuditLoggingFilter.java | AuditLogIT::aWriteProducesOneJsonAuditLineWithSubjectMethodPathTargetStatusAndTraceId、AuditLogIT::readsAreNotAudited、AuditLogIT::rejectedWritesAreAuditedToo、AuditLogIT::requestBodiesNeverReachTheAuditLog | 待填 | ✅ 實作+測試 |
| NFR-9.3-01 | PRD §9.3 | 可用性目標 99.5% | Infra | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.3-02 | PRD §9.3 | 備份以 §12 為準 | Infra | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.3-03 | PRD §9.3 | RTO 15 分／RPO 1 分 | Infra | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-9.3-04 | PRD §9.3 | 軟刪除 30 天內可復原 | BE | 2 | backend/src/main/java/com/aisdlc/console/domain/model/project/Project.java、backend/src/main/java/com/aisdlc/console/domain/model/goal/Goal.java、backend/src/main/java/com/aisdlc/console/domain/model/task/Task.java（軟刪除保留資料列已完成；30 天內復原的 restore 機制未做） | ProjectApiIT::deleteIsSoftAndCascadesToGoalsAndTasks、GoalApiIT::deleteIsSoftAndTakesItsTasksWithIt、TaskApiIT::aRunningTaskCannotBeDeletedButAnyOtherCanBe | 待填 | 🟡 部分 |
| NFR-9.4-01 | PRD §9.4 | 前後端程式碼規範檢查 | FE+BE | 1 | backend/config/checkstyle/checkstyle.xml、backend/build.gradle.kts（後端 Checkstyle 完成；前端 ESLint／Prettier 待 W3） | gradlew checkstyleMain checkstyleTest（隨 gradlew build 執行，違規即建置失敗） | 待填 | 🟡 部分 |
| NFR-9.4-02 | PRD §9.4 | 覆蓋率 後端80／前端70 | FE+BE | 6 | backend/build.gradle.kts（後端 JaCoCo 門檻完成；前端 70% 待 W3／W4） | gradlew build 內的 jacocoTestCoverageVerification（後端指令覆蓋率門檻 80%，低於即建置失敗） | 待填 | 🟡 部分 |
| NFR-9.4-03 | PRD §9.4 | OpenAPI 文件自動產生 | BE | 1 | backend/src/main/java/com/aisdlc/console/infrastructure/config/OpenApiConfig.java、backend/src/main/java/com/aisdlc/console/adapter/in/web/ErrorResponseDocumentation.java、backend/src/main/resources/application.yml | OpenApiIT::theDocumentListsExactlyTheEndpointsOfPhaseOneAndTwo、OpenApiIT::creatingResourcesDocuments201AndDeletesDocument204、OpenApiIT::theBearerSchemeIsGlobalButLoginAndRefreshAreMarkedPublic、OpenApiIT::responseEnvelopeSchemasAreDocumentedWithTheirRequiredFields、OpenApiIT::theErrorEnvelopeIsDocumentedSoClientsCanTypeIt | 待填 | ✅ 實作+測試 |
| NFR-9.4-04 | PRD §9.4 | JSON 日誌含 traceId | BE+Bridge | 1 | backend/src/main/java/com/aisdlc/console/infrastructure/config/TraceIdFilter.java、backend/src/main/java/com/aisdlc/console/infrastructure/config/WebConfig.java、backend/src/main/java/com/aisdlc/console/infrastructure/security/AuditLoggingFilter.java、backend/src/main/resources/application.yml、backend/Dockerfile（後端完成：日誌含 traceId，容器內 LOGGING_STRUCTURED_FORMAT_CONSOLE=logstash 輸出 JSON；Bridge 端待 W1-B 回填） | ResponseEnvelopeIT::traceIdIsAFreshUuidPerRequestAndMatchesTheResponseHeader、AuditLogIT::aWriteProducesOneJsonAuditLineWithSubjectMethodPathTargetStatusAndTraceId | 待填 | 🟡 部分 |
| NFR-9.4-05 | PRD §9.4 | 配置外部化 | FE+BE+Bridge+Infra | 1 | backend/src/main/resources/application.yml、backend/README.md（後端完成：環境相關設定皆可由環境變數覆寫；前端、Bridge、Infra 各自回填） | ConsoleAuthPropertiesTest::aMissingSecretFailsStartupAndNamesTheEnvironmentVariable、ConsoleAuthPropertiesTest::defaultsAreThirtyMinutesAndSevenDays | 待填 | 🟡 部分 |
| NFR-XPL-01 | ADR-001 D15 · 跨平台補充 1 | 文件指令雙形態 | FE+BE+Bridge+Infra | 1 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-XPL-02 | ADR-001 D15 · 跨平台補充 2 | Bridge 可於 Windows 運行 | Bridge | 4 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-XPL-03 | ADR-001 D15 · 跨平台補充 3 | 主機側不依賴 .sh | Infra | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| NFR-XPL-04 | ADR-001 D15 · 跨平台補充 4 | gradlew 與 .bat 皆入庫 | BE | 1 | backend/gradlew、backend/gradlew.bat、backend/.gitattributes（檔案已就位；入庫與 gradlew 索引模式待主控 commit 時依 D-2 裁決） | 無自動測試（git ls-files --eol 現查：gradlew 為 w/lf、gradlew.bat 為 w/crlf） | 待填 | 🟡 部分 |
| INF-SVC-01 | PRD §11.2 · nginx | nginx 反向代理 | Infra | 1 | docker-compose.yml（nginx 段）、docker/nginx/nginx.conf、docker/nginx/conf.d/default.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 以假上游（拓撲與正式 compose 相同）實跑正式 nginx 設定：根路徑回前端、/api/v1/projects 回後端、nginx -t 通過；另與真實 frontend／backend 一起跑（profile full）：GET / 回 200 與 Next.js 頁面、/nginx-health 回 ok、/actuator/health 經 nginx 回 403、/api/v1/projects 無 token 回 401、登入後建立與列出專案皆成功、_next/static 回 Cache-Control: public, max-age=31536000, immutable（2026-10-15） | ✅ 已驗證 |
| INF-SVC-02 | PRD §11.2 · frontend | frontend（Next.js） | Infra | 1 | docker-compose.yml（frontend 段，profile app） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 以 W3-A 建好的映像 aisdlc-frontend:dev 經 up -d --no-build --wait 啟動，compose 定義的 healthcheck 判 healthy，經 nginx 回 200 與 Next.js 頁面（2026-10-15）；註：compose 的 build: 區段本輪未實際執行（避免與 W3-A 的建置互踩）；frontend/Dockerfile 本身屬 INF-DKR 列（他人負責） | ✅ 已驗證 |
| INF-SVC-03 | PRD §11.2 · backend | backend（Spring Boot） | Infra | 1 | docker-compose.yml（backend 段，profile app） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 以 W2-A 建好的映像 aisdlc-backend:dev 經 up -d --no-build --wait 啟動：Flyway 4 個版本成功、console schema 13 張表、compose 定義的 healthcheck 判 healthy；登入與建立專案／目標／任務經 nginx 成功並串流到 replica；Prometheus 的 spring-boot target 為 up；failover 後以 POSTGRES_HOST=postgres-replica 重建，連線字串改指升格節點並可寫入（2026-10-15）；註：compose 的 build: 區段本輪未實際執行 | ✅ 已驗證 |
| INF-SVC-04 | PRD §11.2 · engine-bridge | engine-bridge 旁車 | Infra | 1 | docker-compose.yml（engine-bridge 段，profile app） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | up -d --no-deps engine-bridge 後 healthy；/health 回 sdd.latest=AISDLC_SDD_v0.30、db.ok=true；uid 10001 可寫 /workspace、/sdd 唯讀；POSTGRES_HOST 改指 postgres-replica 後 db.ok=true（2026-10-15） | ✅ 已驗證 |
| INF-SVC-05 | PRD §11.2 · postgres-primary | postgres-primary | Infra | 1 | docker-compose.yml、docker/postgres/primary/Dockerfile、docker/postgres/primary/postgresql.conf、docker/postgres/primary/pg_hba.conf、docker/postgres/primary/init/01-init-db.sql、docker/postgres/primary/init/02-replication.sh、docker/postgres/primary/pgbackrest-archive-wal.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | up -d --build 後 healthy；寫入成功；pgvector／pg_stat_statements 延伸與 console schema 已建；postmaster 非預期退出後自動重啟且資料不丟（2026-10-15） | ✅ 已驗證 |
| INF-SVC-06 | PRD §11.2 · postgres-replica | postgres-replica | Infra | 1 | docker-compose.yml、docker/postgres/replica/postgresql.conf、docker/postgres/replica/entrypoint.sh、docker/pgbackrest/scripts/setup-replica.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_stat_replication 1 列 streaming／async；replica 讀到 primary 寫入的列；pg_is_in_recovery=t（2026-10-15） | ✅ 已驗證 |
| INF-SVC-07 | PRD §11.2 · redis | redis 快取 | Infra | 1 | docker-compose.yml、docker/redis/redis.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；SET 後 restart 再 GET 仍為原值（AOF 開）；經 dev 疊加檔發布的 6379 以 redis-cli ping 回 PONG（2026-10-15） | ✅ 已驗證 |
| INF-SVC-08 | PRD §11.2 · pgadmin | pgadmin 管理介面 | Infra | 1 | docker-compose.yml、docker/pgadmin/servers.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；日誌 Added 1 Server Group(s) and 2 Server(s)；dump-servers 列出 Primary 與 Replica；主機 5050 可連（2026-10-15） | ✅ 已驗證 |
| INF-SVC-09 | PRD §11.2 · pgbackrest | pgbackrest 備份服務 | Infra | 1 | docker-compose.yml、docker/pgbackrest/Dockerfile、docker/pgbackrest/pgbackrest.conf、docker/pgbackrest/crontab、docker/pgbackrest/scripts/ | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；啟動時自動 stanza-create；check、全備、差備、info、離站、演練皆成功；crond 探針以 postgres 身分觸發（2026-10-15） | ✅ 已驗證 |
| INF-SVC-10 | PRD §11.2 · prometheus | prometheus 指標收集 | Infra | 1 | docker-compose.yml、docker/prometheus/prometheus.yml、docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；/api/v1/targets：postgres-primary、postgres-replica、pgbackrest、prometheus 為 up，spring-boot 為 down（db profile 下 backend 未起，預期；app profile 下真實 backend 起來後為 up）；/api/v1/rules 12 條規則 health 皆 ok（2026-10-15） | ✅ 已驗證 |
| INF-SVC-11 | PRD §11.2 · grafana | grafana 儀表板 | Infra | 1 | docker-compose.yml、docker/grafana/provisioning/、docker/grafana/dashboards/ | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；/api/search 回 Application Overview 與 PostgreSQL Overview；資料來源 health 為 OK（2026-10-15） | ✅ 已驗證 |
| INF-SVC-12 | ADR-001 D14 · minio | minio 離站儲存 | Infra | 1 | docker-compose.yml（minio、minio-certs 段）、docker/minio/gen-cert.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy（自簽 TLS）；pgBackRest repo2 與 mc 皆可連線；官方 minio/minio 映像已下架，改用 pgsty/minio（docker/README.md〈9〉#5）（2026-10-15） | ✅ 已驗證 |
| INF-SVC-13 | ADR-001 D14 · minio-init | minio-init 建立 bucket | Infra | 1 | docker-compose.yml（minio-init 段）、docker/minio/init-bucket.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Exited (0)；建立 bucket aisdlc-db-backup 與專用帳號，並以該帳號實際寫入、讀取、刪除探針物件（2026-10-15） | ✅ 已驗證 |
| INF-SVC-14 | ADR-001 D14 · postgres-exporter-primary | exporter-primary | Infra | 1 | docker-compose.yml（postgres-exporter-primary 段） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；Prometheus 目標 postgres-primary 為 up；pg_up、pg_stat_activity_count、pg_stat_statements_* 皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-SVC-15 | ADR-001 D14 · postgres-exporter-replica | exporter-replica | Infra | 1 | docker-compose.yml（postgres-exporter-replica 段） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | healthy；Prometheus 目標 postgres-replica 為 up；pg_replication_lag_seconds 有資料（2026-10-15） | ✅ 已驗證 |
| INF-NET-01 | PRD §11.3 · networks | frontend-net 網路 | Infra | 1 | docker-compose.yml（networks） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | config 通過；與真實 frontend 一起跑：nginx 經 frontend-net 連到 frontend 並回 200（2026-10-15） | ✅ 已驗證 |
| INF-NET-02 | PRD §11.3 · networks | backend-net 網路 | Infra | 1 | docker-compose.yml（networks） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | grafana、prometheus、pgadmin 掛此網路，主機 3001、9090、5050 皆可連（2026-10-15） | ✅ 已驗證 |
| INF-NET-03 | PRD §11.3 · networks | db-net 內部網路 | Infra | 1 | docker-compose.yml（networks：internal: true） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 正式模式主機連 5432／5433 被拒；E-5 玩具實驗：只掛 internal 網路的容器 ports 發布無效、加掛非 internal 網路後可達（2026-10-15） | ✅ 已驗證 |
| INF-VOL-01 | PRD §11.1 · §11.3 · pg_data | 卷 pg_data | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | primary 資料持久；PITR 還原與 failover 流程後資料正確（2026-10-15） | ✅ 已驗證 |
| INF-VOL-02 | PRD §11.1 · §11.3 · pg_replica_data | 卷 pg_replica_data | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | replica 資料卷：首次自動 basebackup、重建流程皆驗證（2026-10-15） | ✅ 已驗證 |
| INF-VOL-03 | PRD §11.1 · §11.3 · pg_wal_archive | 卷 pg_wal_archive | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 本地 WAL 複本（gzip）寫入；replica 的 restore_command 讀取並重播驗證（2026-10-15） | ✅ 已驗證 |
| INF-VOL-04 | PRD §11.1 · §11.3 · pg_backup | 卷 pg_backup | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pgBackRest repo1 備份與歸檔寫入；primary 與 sidecar 共用（2026-10-15） | ✅ 已驗證 |
| INF-VOL-05 | PRD §11.1 · §11.3 · redis_data | 卷 redis_data | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | SET 後 restart 再 GET 仍為原值（2026-10-15） | ✅ 已驗證 |
| INF-VOL-06 | PRD §11.1 · §11.3 · app_logs | 卷 app_logs | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | engine-bridge 與 backend 皆掛載 /app/logs 成功，backend 的 /app/logs 屬主為 spring（可寫）；backend 日誌只走 stdout 的結構化 JSON，卷內為空（2026-10-15）；缺：要檔案日誌需後端另設 file appender | 🟡 部分 |
| INF-VOL-07 | PRD §11.1 · §11.3 · nginx_certs | 卷 nginx_certs | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | config 通過、唯讀掛載設定（2026-10-15）；缺：憑證實際放入與 HTTPS 區塊（default.conf 僅有註解範例） | 🟡 部分 |
| INF-VOL-08 | PRD §11.3 · engine_workspace | 卷 engine_workspace | Infra | 1 | docker-compose.yml（volumes） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | engine-bridge 以 uid 10001 可寫 /workspace（2026-10-15） | ✅ 已驗證 |
| INF-DKR-01 | PRD §11.4.1 | frontend Dockerfile | Infra | 1 | frontend/Dockerfile、frontend/.dockerignore（PRD §11.4.1 三階段；兩處必要修正見 ADR-002 §D10） | —（以容器實跑驗證，見 E2E 驗證欄） | `docker build -t aisdlc-frontend:dev AgentConsole/frontend` rc=0；`docker run` 後 uid 1001、`GET /api/health`＝`{"status":"ok"}`、`docker inspect` Health.Status＝`healthy`；另以同一份 Dockerfile 建出帶測試後端位址的映像，Playwright 全套 E2E 對該容器實跑（W3-A，2026-10-15） | ✅ 已驗證 |
| INF-DKR-02 | PRD §11.4.2 | backend Dockerfile | Infra | 1 | backend/Dockerfile、backend/.dockerignore、backend/build.gradle.kts | 無自動測試（docker build 與 docker run 實跑，輸出見 W2-A 交卷） | docker build -t aisdlc-backend:dev AgentConsole/backend 成功；docker run 指向本機 PG 後 /actuator/health 回 UP 且容器 healthy（W2-A，2026-10-14） | ✅ 已驗證 |
| INF-DKR-03 | PRD §11.4.3 · ADR-001 D14 | pgbackrest 映像（apt） | Infra | 1 | docker/pgbackrest/Dockerfile | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | build 成功；pgBackRest 2.59.3（apt，支援 PG18）；基底為 Debian 12 bookworm（ADR-001 E-4）（2026-10-15） | ✅ 已驗證 |
| INF-DKR-04 | PRD §11.8 · ADR-001 D7 · engine-bridge/Dockerfile | bridge Dockerfile | Infra | 1 | docker-compose.yml（engine-bridge 段：build context 為 monorepo 根） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose --profile db --profile app build engine-bridge 成功並實際啟動 healthy（Dockerfile 由 Bridge 開發者提供）（2026-10-15） | ✅ 已驗證 |
| INF-DKR-05 | ADR-001 D14 | 主節點映像含 pgBackRest | Infra | 1 | docker/postgres/primary/Dockerfile | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | build 成功；primary 內 pgbackrest archive-push 實際歸檔到 repo1 與 repo2（2026-10-15） | ✅ 已驗證 |
| INF-NGX-01 | PRD §11.5 | SSE 反代不緩衝 | Infra | 1 | docker/nginx/conf.d/default.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 以假上游實跑：SSE 事件逐秒到達（t+0～4 秒各一則），nginx 未緩衝（2026-10-15）；真後端 SSE 待 W4 整合 | ✅ 已驗證 |
| INF-NGX-02 | PRD §11.5 | 封鎖 /actuator/ 對外 | Infra | 1 | docker/nginx/conf.d/default.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | curl /actuator/health 回 HTTP 403（2026-10-15） | ✅ 已驗證 |
| INF-NGX-03 | PRD §11.5 | 靜態資源長快取 | Infra | 1 | docker/nginx/conf.d/default.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | curl -I /_next/static/app.js 含 Cache-Control: public, max-age=31536000, immutable（2026-10-15） | ✅ 已驗證 |
| INF-NGX-04 | ADR-001 D14 | nginx 可達 backend | Infra | 1 | docker-compose.yml（nginx 同掛 backend-net）、docker/nginx/conf.d/default.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 反證：nginx 只掛 frontend-net 時 nginx -t 報 host not found in upstream backend:8080；正證：同掛 backend-net 後 /api/v1/projects 回後端內容（2026-10-15） | ✅ 已驗證 |
| INF-ENV-01 | PRD §11.6 | .env.example 無真實機密 | Infra | 1 | .env.example | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | python tools/lib/secret_scan.py --paths（含 .env.example 與 docker/ 全部檔案）rc=0；內容只有 <YOUR_...> 佔位符與非機密預設值（2026-10-15） | ✅ 已驗證 |
| INF-CMD-01 | PRD §11.7 | 首次部署流程 | Infra | 1 | docker/README.md〈2〉〈3〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | cp .env.example 後填值 → docker compose --profile db up -d --build → ps 全部 healthy；PRD 的手動 Flyway 步驟依 ADR-001 D14-11 刪除（2026-10-15） | ✅ 已驗證 |
| INF-CMD-02 | PRD §11.7 | 日常操作指令 | Infra | 1 | docker/README.md〈2〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | ps、logs、stop、down、down -v 與單一服務重建（up -d --build pgbackrest）皆實跑（2026-10-15） | ✅ 已驗證 |
| INF-DEV-01 | ADR-001 D14 · docker-compose.dev.yml | 本機開發 compose 檔 | Infra | 1 | docker-compose.dev.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 獨立模式只起 postgres-primary 與 redis；疊加模式發布 5432／5433／6379；主機端以 psql 實連兩個節點並查詢成功（2026-10-15） | ✅ 已驗證 |
| INF-PRF-01 | ADR-001 D14 | compose profiles 分層 | Infra | 1 | docker-compose.yml（profiles） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | config --services：不帶 profile 為空、db 為 12 個、db＋app＋full 為 16 個；單獨 --profile app 報 depends on undefined service（README 已註明）（2026-10-15） | ✅ 已驗證 |
| INF-HLT-01 | PRD §11.3 | healthcheck 與依賴順序 | Infra | 1 | docker-compose.yml（healthcheck、depends_on） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | db 層 10 個長駐服務皆 healthy，依賴順序 minio-certs→minio→minio-init→pgbackrest 正確；加上 app、full 層共 14 個長駐服務（含 frontend、backend、engine-bridge、nginx）皆以各自 healthcheck 判 healthy，postgres-primary／redis／engine-bridge 先於 backend、frontend／backend 先於 nginx（2026-10-15） | ✅ 已驗證 |
| INF-RES-01 | PRD §11.2 | 各服務資源限制 | Infra | 1 | docker-compose.yml（deploy.resources.limits） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker stats 的 MEM LIMIT 與設定一致（primary 2GiB、replica 1GiB、grafana／pgadmin／redis 256MiB…）；pgAdmin 閒置即用 221.7MiB／256MiB（風險見 docker/README.md〈10〉）（2026-10-15） | ✅ 已驗證 |
| INF-DB-01 | PRD §6.2 · projects | 專案表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/ProjectEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-02 | PRD §6.2 · goals | 目標表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/GoalEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-03 | PRD §6.2 · goal_dependencies | 目標依賴表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/GoalDependencyEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates、SchemaMigrationIT::databaseItselfRejectsSelfDependencyDuplicateEdgeAndUnknownStatus | 待填 | ✅ 實作+測試 |
| INF-DB-04 | PRD §6.2 · tasks | 任務表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/TaskEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-05 | PRD §6.2 · execution_runs | 執行批次表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/ExecutionRunEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates、ExecutionRunOwnershipIT::consoleCreatesTheRowWithoutTouchingBridgeColumns、ExecutionRunOwnershipIT::bridgeWritesAreVisibleToConsoleAndNeverOverwrittenByConsoleFlushes | 待填 | ✅ 實作+測試 |
| INF-DB-06 | PRD §6.2 · execution_steps | 執行步驟表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/ExecutionStepEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-07 | PRD §6.2 · checkpoints | 斷點表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/CheckpointEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-08 | PRD §6.2 · import_records | 匯入記錄表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/ImportRecordEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-09 | PRD §6.2 · system_configs | 系統參數表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/SystemConfigEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates、SchemaMigrationIT::seedHasAllSixCategoriesWithTheDocumentedParameterCounts | 待填 | ✅ 實作+測試 |
| INF-DB-10 | PRD §6.2 · system_config_history | 參數歷史表 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/SystemConfigHistoryEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-11 | PRD §6.2 索引 | 索引（含 partial index） | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql | SchemaMigrationIT::listIndexesAreSoftDeleteAwarePartialIndexes | 待填 | ✅ 實作+測試 |
| INF-DB-12 | ADR-001 D5 · Flyway V1 + ddl-auto=validate | V1 遷移＋JPA 驗證 | BE | 1 | backend/src/main/resources/db/migration/V1__init.sql、backend/src/main/resources/application.yml | SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates、ConsoleApplicationTests::contextLoads、SchemaMigrationIT::flywayAppliedVersionsOneToFourSuccessfully | 待填 | ✅ 實作+測試 |
| INF-DB-13 | PRD §5.5.1 · ADR-001 D5 | V2 六類參數預設種子 | BE | 1 | backend/src/main/resources/db/migration/V2__seed_system_configs.sql | SchemaMigrationIT::seedHasAllSixCategoriesWithTheDocumentedParameterCounts、SchemaMigrationIT::dalBackendDefaultsToFileNotPostgresqlPerAdr001D13、SchemaMigrationIT::onlyTheApiKeyIsEncryptedAndItsValueIsEmpty、SchemaMigrationIT::tokenGuardSeedKeepsHaltAboveCompact | 待填 | ✅ 實作+測試 |
| INF-DB-14 | ADR-001 D5 · Arch §11 | V3 review_requests 表 | BE | 4 | backend/src/main/resources/db/migration/V3__review_requests.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/ReviewRequestEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::flywayAppliedVersionsOneToFourSuccessfully | 待填 | ✅ 實作+測試 |
| INF-DB-15 | ADR-001 D5 · Arch §11 | V4 alerts 表 | BE | 5 | backend/src/main/resources/db/migration/V4__monitor_alerts.sql、backend/src/main/java/com/aisdlc/console/infrastructure/persistence/entity/AlertEntity.java | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::flywayAppliedVersionsOneToFourSuccessfully | 待填 | ✅ 實作+測試 |
| INF-DB-16 | ADR-001 D5 | console schema 隔離 | BE | 1 | backend/src/main/resources/application.yml、backend/src/main/resources/db/migration/V1__init.sql | SchemaMigrationIT::allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic、SchemaMigrationIT::ddlIsOwnedByFlywayAndJpaOnlyValidates | 待填 | ✅ 實作+測試 |
| INF-DB-17 | PRD §0.6 · ADR-001 D5 | V5 §0.6 補充參數種子 | BE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| INF-DR-01 | PRD §12.2.1 | 串流複製 standby | Infra | 6 | docker-compose.yml、docker/postgres/replica/postgresql.conf、docker/postgres/replica/entrypoint.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_stat_replication 1 列 streaming；寫主讀副成功；replica 為唯讀 standby（2026-10-15） | ✅ 已驗證 |
| INF-DR-02 | PRD §12.2.2 | Primary WAL／歸檔設定 | Infra | 6 | docker/postgres/primary/postgresql.conf、docker/postgres/primary/pgbackrest-archive-wal.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pgbackrest check：WAL 成功歸檔到 repo1 與 repo2；pg_stat_archiver 的失敗次數維持 0（2026-10-15） | ✅ 已驗證 |
| INF-DR-03 | PRD §12.2.3 | Primary pg_hba.conf | Infra | 6 | docker/postgres/primary/pg_hba.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 應用網段 scram、replication、loopback 皆依檔案放行（hba_file 已明確設定，PRD 漏設）（2026-10-15） | ✅ 已驗證 |
| INF-DR-04 | PRD §12.2.4 | Replica 設定檔 | Infra | 6 | docker/postgres/replica/postgresql.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | replica 以此設定啟動為 hot standby；WAL／複製參數與 primary 對稱（failover 切回流程驗證）（2026-10-15） | ✅ 已驗證 |
| INF-DR-05 | PRD §12.2.5 | Replication 帳號與 slot | Infra | 6 | docker/postgres/primary/init/02-replication.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | replicator 角色與 replica_slot_1 建立；pg_basebackup 與串流皆以該帳號成功（2026-10-15） | ✅ 已驗證 |
| INF-DR-06 | PRD §12.2.6 · ADR-001 D14 | Replica 建立與重建 | Infra | 6 | docker/postgres/replica/entrypoint.sh、docker/pgbackrest/scripts/setup-replica.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 首次啟動自動 basebackup；PITR 後與 failover 後以 setup-replica.sh --force 重建，slot 不存在時自動建立（2026-10-15） | ✅ 已驗證 |
| INF-DR-07 | PRD §12.3.1 · §12.4 | WAL 連續歸檔（60 秒） | Infra | 6 | docker/postgres/primary/postgresql.conf、docker/postgres/primary/pgbackrest-archive-wal.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | archive_timeout=60（SHOW 回 1min）：有持續寫入時 6 分鐘內 pg_stat_archiver 的 last_archived_time 為 18:10:15、18:11:15、18:12:15、18:13:15、18:14:15、18:15:15（UTC），逐分鐘各歸檔一段、歸檔失敗次數維持 0；完全閒置時不再換段（最後一次寫入後多換 1 段，其後經過兩個 checkpoint 週期約 10 分鐘，沒有新段也沒有新的 checkpoint）（驗證日 10-15） | ✅ 已驗證 |
| INF-DR-08 | PRD §12.3.3 · §12.4 | pgBackRest 全備（週日） | Infra | 6 | docker/pgbackrest/scripts/backup-full.sh、docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | repo1 與 repo2 各一份全備；crond 觸發機制以探針驗證（以 postgres 身分、帶 PGBACKREST_* 環境變數）；週日 02:00 的實際觸發未等待（2026-10-15） | ✅ 已驗證 |
| INF-DR-09 | PRD §12.3.3 · §12.4 | pgBackRest 差備（週一至六） | Infra | 6 | docker/pgbackrest/scripts/backup-incr.sh、docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | repo1 與 repo2 各一份差異備份；crond 觸發機制同 INF-DR-08；週一至週六 02:00 的實際觸發未等待（2026-10-15） | ✅ 已驗證 |
| INF-DR-10 | PRD §12.3.3 · §12.3.4 | pg_dump 離站備份（每日） | Infra | 6 | docker/pgbackrest/scripts/pg_dump-offsite.sh、docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | MinIO 的 logical/ 出現 aisdlc-<時間>.dump；pg_restore --list 可讀（TOC 14 筆）（2026-10-15） | ✅ 已驗證 |
| INF-DR-11 | PRD §12.3.2 · §12.7.2 | 離站 repo2 預設啟用 | Infra | 6 | docker/pgbackrest/pgbackrest.conf、docker-compose.yml、docker/minio/ | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | repo2 為 MinIO（S3，自簽 TLS）；info 顯示全備與差備各有 repo1 與 repo2（2026-10-15） | ✅ 已驗證 |
| INF-DR-12 | PRD §12.3.3 · §12.3.4 | 備份驗證與 restore 演練 | Infra | 6 | docker/pgbackrest/scripts/verify-backup.sh、docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | verify-backup.sh：repo1 與 repo2 各一次真實還原演練，console.drill_demo 250 列、console.repl_probe 1 列，臨時實例停止並清除，rc=0（2026-10-15） | ✅ 已驗證 |
| INF-DR-13 | PRD §12.1 · §12.3.2 | 備份與 WAL 保留政策 | Infra | 6 | docker/pgbackrest/pgbackrest.conf、docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | repo1-retention-full=4：連做 5 份全備後 repo1 只留 4 份，最舊者被 expire（2026-10-15）；缺：WAL 7 天的本地複本清理 cron 未做時間驗證 | 🟡 部分 |
| INF-DR-14 | PRD §12.3.2 | 備份加密 aes-256-cbc | Infra | 6 | docker/pgbackrest/pgbackrest.conf | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | info 顯示 cipher: aes-256-cbc；兩個 repo 同一把密碼；還原演練能解密（2026-10-15） | ✅ 已驗證 |
| INF-DR-15 | PRD §12.3.3 | 過期備份清理（每日） | Infra | 6 | docker/pgbackrest/crontab | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 與 cron 相同的指令 pgbackrest --stanza=aisdlc expire 實跑 rc=0；備份後的自動 expire 日誌可見 expire full backup／remove expired backup（2026-10-15） | ✅ 已驗證 |
| INF-DR-16 | PRD §12.3.4 | restore 與 PITR 還原 | Infra | 6 | docker/pgbackrest/scripts/restore.sh、docker/README.md〈4.3〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | primary 在跑時 restore.sh 拒絕（rc=1）；stop → run --rm --no-deps restore.sh --target-time → start：timeline 2，誤刪的 drill_demo（260 列）回來、誤刪後的插入列不在（2026-10-15） | ✅ 已驗證 |
| INF-DR-17 | PRD §12.5.2 | 手動 failover 程序 | Infra | 6 | docker/README.md〈6〉、docker/pgbackrest/scripts/setup-replica.sh、docker-compose.yml（POSTGRES_HOST） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose 指令序列實跑：停 primary → pg_promote → 可寫；POSTGRES_HOST 改指 replica 後 Bridge db.ok=true；原 primary 重建為 standby → 計畫性切回 → 新全備與演練皆成功（2026-10-15） | ✅ 已驗證 |
| INF-DR-18 | PRD §12.1 | RPO／RTO 設計目標 | Infra | 6 | docker/postgres/primary/postgresql.conf、docker/README.md〈6〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | RPO：非同步串流（replay_lsn 與 sent_lsn 相同）、archive_timeout=60；RTO：failover 指令序列實跑可在數十秒內完成提升與應用改連（人工時間另計）；含真實 backend：promote 後以 --no-deps 重建 backend，約 15 秒 healthy，failover 後經 nginx 寫入的專案在切回後的 primary／replica／還原演練都在（2026-10-15）；缺：正式計時演練 | 🟡 部分 |
| INF-DR-19 | PRD §12.5.1 | 容器崩潰自動重啟 | Infra | 6 | docker-compose.yml（restart: unless-stopped） | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | postmaster 非預期退出後容器自動重啟（restart_count 0→1）、crash recovery 完成、資料不丟、replica 自動接回；docker kill 被 Docker 視為手動停止而不重啟（已記入證據）（2026-10-15） | ✅ 已驗證 |
| INF-DR-20 | PRD §12.6.1 | Prometheus 抓取目標 | Infra | 6 | docker/prometheus/prometheus.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | /api/v1/targets：postgres-primary、postgres-replica、pgbackrest、prometheus 為 up；spring-boot 為 down（db profile 下 backend 未起）、app profile 下真實 backend 起來後為 up（2026-10-15） | ✅ 已驗證 |
| INF-DR-21 | PRD §12.6.2 · pg_up | pg_up 在線狀態 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | min(pg_up) 為 1；PostgresDown 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-22 | PRD §12.6.2 · pg_replication_lag_seconds | 副本延遲秒數 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_replication_lag_seconds{job=postgres-replica} 為 0；PostgresReplicationLagHigh 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-23 | PRD §12.6.2 · pg_stat_activity_count | 活躍連線數 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | sum(pg_stat_activity_count) 有值（3）；PostgresConnectionsHigh 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-24 | PRD §12.6.2 · pg_database_size_bytes | 資料庫大小 | Infra | 6 | docker/prometheus/alerts.yml、docker/pgbackrest/scripts/pgbackrest-metrics.sh | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_database_size_bytes{datname=aisdlc} 有值；aisdlc_storage_used_ratio（磁碟 80% 判準）有值；PostgresDiskUsageHigh 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-25 | PRD §12.6.2 · pg_stat_bgwriter_buffers_alloc | bgwriter 緩衝分配率 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 實際指標名為 pg_stat_bgwriter_buffers_alloc_total，rate 有值；PostgresBufferAllocSpike 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-26 | PRD §12.6.2 · pg_locks_count | 鎖等待數量 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | sum(pg_locks_count) 有值；PostgresLocksHigh 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-27 | PRD §12.6.2 · pg_stat_statements_mean_time | 查詢平均執行時間 | Infra | 6 | docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 以 rate(pg_stat_statements_seconds_total)／rate(pg_stat_statements_calls_total) 取平均耗時，有值；PostgresSlowQueries 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-28 | PRD §12.6.2 · pgbackrest_backup_since_last_full_seconds | 距上次完整備份秒數 | Infra | 6 | docker/pgbackrest/scripts/pgbackrest-metrics.sh、docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pgbackrest_backup_since_last_full_seconds 有值（備份後 48 秒）；PgBackRestNoRecentFullBackup 規則 health ok（2026-10-15） | ✅ 已驗證 |
| INF-DR-29 | PRD §12.6.2 · pgbackrest_backup_last_status | 最近備份狀態 | Infra | 6 | docker/pgbackrest/scripts/pgbackrest-metrics.sh、docker/pgbackrest/scripts/backup-full.sh、docker/prometheus/alerts.yml | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | 成功為 0；模擬失敗（BACKUP_REPOS=3）腳本 rc=1、指標轉 1；PgBackRestLastBackupFailed 規則 health ok（驗證日 10-15） | ✅ 已驗證 |
| INF-DR-30 | PRD §12.6.3 · PostgreSQL Overview | 面板：PG 總覽 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | PostgreSQL Overview 列：Primary／Replica 狀態、連線數、連線使用率、資料庫大小、快取命中率、TPS 皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-DR-31 | PRD §12.6.3 · Replication Status | 面板：複製狀態 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Replication Status 列：Replica 延遲、streaming 數、slot、WAL 落後、LSN 位置皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-DR-32 | PRD §12.6.3 · Query Performance | 面板：查詢效能 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Query Performance 列：Top 10 慢查詢（10 列）、calls/s、平均耗時皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-DR-33 | PRD §12.6.3 · Backup Status | 面板：備份狀態 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Backup Status 列：距上次全備、最近備份結果、stanza／repo 狀態、備份份數、大小、耗時皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-DR-34 | PRD §12.6.3 · Lock & Wait | 面板：鎖與等待 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Lock & Wait 列：鎖數量、死鎖、長交易、最長交易時間皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-DR-35 | PRD §12.6.3 · Storage | 面板：儲存空間 | Infra | 6 | docker/grafana/dashboards/postgres-overview.json | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | Storage 列：磁碟使用率、備份 repo／WAL 歸檔用量、資料庫大小、pg_wal 大小、表大小 Top 10 皆有資料（2026-10-15） | ✅ 已驗證 |
| INF-OPS-01 | PRD §12.8 每日 | 每日：Primary 健康 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose exec postgres-primary pg_isready -U aisdlc 回 accepting connections（2026-10-15） | ✅ 已驗證 |
| INF-OPS-02 | PRD §12.8 每日 | 每日：Replica 健康 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose exec postgres-replica pg_isready -U aisdlc 回 accepting connections（2026-10-15） | ✅ 已驗證 |
| INF-OPS-03 | PRD §12.8 每日 | 每日：Replication 延遲 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_stat_replication 查詢：sent_lsn、write_lsn、flush_lsn、replay_lsn 皆為 0/1B000060（落差為 0）（2026-10-15） | ✅ 已驗證 |
| INF-OPS-04 | PRD §12.8 每日 | 每日：最近備份狀態 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose exec pgbackrest pgbackrest --stanza=aisdlc info：最近備份為當日，repo1 與 repo2 皆有（2026-10-15） | ✅ 已驗證 |
| INF-OPS-05 | PRD §12.8 每日 | 每日：磁碟使用率 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker system df 可執行並回報各類用量（2026-10-15） | ✅ 已驗證 |
| INF-OPS-06 | PRD §12.8 每週 | 每週：備份驗證 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose exec pgbackrest pgbackrest --stanza=aisdlc verify：verify command end completed successfully（2026-10-15） | ✅ 已驗證 |
| INF-OPS-07 | PRD §12.8 每週 | 每週：慢查詢分析 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_stat_statements 慢查詢 Top 查詢可執行，列出平均耗時與次數（2026-10-15） | ✅ 已驗證 |
| INF-OPS-08 | PRD §12.8 每週 | 每週：表膨脹檢查 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | pg_stat_user_tables 表膨脹查詢可執行（0 列）（2026-10-15） | ✅ 已驗證 |
| INF-OPS-09 | PRD §12.8 每週 | 每週：WAL 歸檔空間 | Infra | 6 | docker/README.md〈8〉 | 無獨立測試檔（以 docker compose 指令實跑驗證，見 E2E 驗證欄） | docker compose exec postgres-primary du -sh /var/lib/postgresql/wal_archive/ 回 2.2M（gzip 複本）（2026-10-15） | ✅ 已驗證 |
| UI-SCR-01 | 設計稿 README §Screens-1 | 總覽儀表板 | FE | 5 | frontend/components/domain/views/DashboardView.tsx、frontend/components/charts/ProjectStatusChart.tsx、frontend/components/charts/tremor/AreaChart.tsx、frontend/app/page.tsx（本波：KPI 前兩張＋進行中的執行＋待人工審批＋狀態分佈圖；後兩張 KPI 待 Phase 5 監控 API） | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除（Dashboard 步驟）、frontend/tests/e2e/signoff.spec.ts::signoff 流程、frontend/tests/e2e/chart.spec.ts::Dashboard 專案狀態分佈圖：面積線用主色、座標軸有刻度、附文字替代說明 | 待填 | 🟡 部分 |
| UI-SCR-02 | 設計稿 README §Screens-2 | 專案管理（清單） | FE | 2 | frontend/components/domain/views/ProjectsView.tsx、frontend/components/domain/ProjectCard.tsx、frontend/components/ui/pagination.tsx、frontend/app/projects/page.tsx | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/shells-and-layout.spec.ts::搜尋列 Enter → /projects?q=，列表只留符合者並可清除、frontend/components/ui/ui.test.tsx::Pagination（超大扁平分頁器） | 待填 | ✅ 實作+測試 |
| UI-SCR-03 | 設計稿 README §Screens-3 | 專案詳情 | FE | 2 | frontend/components/domain/views/ProjectDetailView.tsx、frontend/components/domain/GoalListCard.tsx、frontend/components/domain/SignoffBanner.tsx、frontend/app/projects/[projectId]/page.tsx | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/signoff.spec.ts::signoff 流程 | 待填 | ✅ 實作+測試 |
| UI-SCR-04 | 設計稿 README §Screens-4 | 目標詳情 | FE | 2 | frontend/components/domain/views/GoalDetailView.tsx、frontend/components/domain/TaskListCard.tsx、frontend/app/projects/[projectId]/goals/[goalId]/page.tsx | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/signoff.spec.ts::signoff 流程 | 待填 | ✅ 實作+測試 |
| UI-SCR-05 | 設計稿 README §Screens-5 | 任務詳情（含日誌） | FE | 2 | frontend/components/domain/views/TaskDetailView.tsx、frontend/components/domain/LogPanel.tsx、frontend/app/projects/[projectId]/goals/[goalId]/tasks/[taskId]/page.tsx | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/task-retry.spec.ts::FAILED 任務可重試：送出 POST /retry，toast 顯示重試 1 / 3；日誌可搜尋 | 待填 | ✅ 實作+測試 |
| UI-SCR-06 | 設計稿 README §Screens-6 | BRD/PRD 智能匯入 | FE | 3 | frontend/app/import/page.tsx、frontend/components/domain/PlaceholderCard.tsx（路由殼：標題列＋占位卡；內容於 Phase 3 實作） | frontend/tests/e2e/shells-and-layout.spec.ts::導覽六項都能點到對應頁面，每頁四區塊各一份 | 待填 | 🟡 部分 |
| UI-SCR-07 | 設計稿 README §Screens-7 | 專案執行控制台 | FE | 4 | frontend/app/projects/[projectId]/execute/page.tsx、frontend/components/domain/ProjectShellPage.tsx（路由殼；內容於 Phase 4 實作） | frontend/tests/e2e/shells-and-layout.spec.ts::導覽六項都能點到對應頁面，每頁四區塊各一份 | 待填 | 🟡 部分 |
| UI-SCR-08 | 設計稿 README §Screens-8 | 專案監控儀表板 | FE | 5 | frontend/app/projects/[projectId]/monitor/page.tsx、frontend/components/domain/ProjectShellPage.tsx（路由殼；內容於 Phase 5 實作） | frontend/tests/e2e/shells-and-layout.spec.ts::導覽六項都能點到對應頁面，每頁四區塊各一份 | 待填 | 🟡 部分 |
| UI-SCR-09 | 設計稿 README §Screens-9 | 系統參數設定 | FE | 6 | frontend/app/settings/page.tsx、frontend/components/domain/PlaceholderCard.tsx（路由殼；內容於 Phase 6 實作） | frontend/tests/e2e/shells-and-layout.spec.ts::導覽六項都能點到對應頁面，每頁四區塊各一份 | 待填 | 🟡 部分 |
| UI-LAY-01 | Arch §5 · 設計稿 Topbar+Masthead | Top 區（公告列＋主導覽） | FE | 1 | frontend/components/layout/TopRegion.tsx | frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/components/layout/layout.test.tsx::四區塊共用版面只住 app/layout.tsx（UI-LAY-05） | 待填 | ✅ 實作+測試 |
| UI-LAY-02 | Arch §5 · 設計稿 Sidebar | Tools 區（導航＋我的專案） | FE | 1 | frontend/components/layout/ToolsRegion.tsx | frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/components/layout/layout.test.tsx::四區塊共用版面只住 app/layout.tsx（UI-LAY-05） | 待填 | ✅ 實作+測試 |
| UI-LAY-03 | Arch §5 · 設計稿 Main | Content 區（路由內容） | FE | 1 | frontend/components/layout/ContentRegion.tsx | frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/components/layout/layout.test.tsx::四區塊共用版面只住 app/layout.tsx（UI-LAY-05） | 待填 | ✅ 實作+測試 |
| UI-LAY-04 | Arch §5 | Bottom 區（底部列） | FE | 1 | frontend/components/layout/BottomRegion.tsx、frontend/components/ui/toast.tsx、frontend/hooks/useServiceStatus.ts | frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/components/ui/ui.test.tsx::Toast（底部置中、一次一則、自動消失） | 待填 | ✅ 實作+測試 |
| UI-LAY-05 | Arch §5 | 共用區塊各僅一個元件檔 | FE | 1 | frontend/app/layout.tsx、frontend/components/layout/TopRegion.tsx、frontend/components/layout/ToolsRegion.tsx、frontend/components/layout/ContentRegion.tsx、frontend/components/layout/BottomRegion.tsx | frontend/components/layout/layout.test.tsx::四區塊共用版面只住 app/layout.tsx（UI-LAY-05）、frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份、frontend/tests/e2e/shells-and-layout.spec.ts::導覽六項都能點到對應頁面，每頁四區塊各一份 | 待填 | ✅ 實作+測試 |
| UI-RSP-01 | PRD §8.3 | Desktop ≥1280 完整側欄 | FE | 1 | frontend/components/layout/ToolsRegion.tsx、frontend/app/layout.tsx | frontend/tests/e2e/shells-and-layout.spec.ts::響應式（PRD §8.3） › 桌面 1440px：240px 完整側欄與『我的專案』rail | 待填 | ✅ 實作+測試 |
| UI-RSP-02 | PRD §8.3 | Tablet 側欄收合為圖示 | FE | 1 | frontend/components/layout/ToolsRegion.tsx | frontend/tests/e2e/shells-and-layout.spec.ts::響應式（PRD §8.3） › 平板 1024px：側欄收合成圖示（標籤隱藏、aria-label 保留） | 待填 | ✅ 實作+測試 |
| UI-RSP-03 | PRD §8.3 | Mobile 底部 Tab 導航 | FE | 1 | frontend/components/layout/ToolsRegion.tsx、frontend/app/layout.tsx | frontend/tests/e2e/shells-and-layout.spec.ts::響應式（PRD §8.3） › 手機 390px：側欄變成底部 Tab 導航（位於內容下方） | 待填 | ✅ 實作+測試 |
| UI-A11Y-01 | PRD §8.4 | 互動元素具 aria-label | FE | 6 | frontend/components/layout/TopRegion.tsx、frontend/components/layout/ToolsRegion.tsx、frontend/components/ui/icon-button.tsx、frontend/components/ui/pagination.tsx（互動元素皆帶 aria-label／可及名稱；尚未跑全站 axe 稽核，歸 Phase 6） | frontend/components/layout/layout.test.tsx::RootLayout 渲染：四區塊各一份 | 待填 | 🟡 部分 |
| UI-A11Y-02 | PRD §8.4 | 鍵盤導航 Tab/Enter/Esc | FE | 6 | frontend/styles/tokens.css、frontend/components/domain/GoalListCard.tsx（Tab 焦點環與 Esc 關閉 Dialog 由 Radix 提供；拖曳排序有鍵盤 sensor；完整鍵盤走查歸 Phase 6） | frontend/tests/e2e/design-system.spec.ts::焦點環：鍵盤依序 Tab 過頂列的每個停駐點，皆為 2px 實線主色外框（搜尋框改畫在內側） | 待填 | 🟡 部分 |
| UI-A11Y-03 | PRD §8.4 | 對比度符合 WCAG 2.1 AA | FE | 6 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-A11Y-04 | PRD §8.4 | 圖表提供文字替代說明 | FE | 6 | frontend/components/charts/ProjectStatusChart.tsx（Dashboard 狀態分佈圖：role="img"＋aria-label＋螢幕閱讀器專用清單；其餘圖表屬 Phase 5） | frontend/tests/e2e/chart.spec.ts::Dashboard 專案狀態分佈圖：面積線用主色、座標軸有刻度、附文字替代說明 | 待填 | 🟡 部分 |
| UI-DS-01 | 設計稿 README §Design Tokens | water_green 色彩 token | FE | 1 | frontend/styles/tokens.css、frontend/styles/tokens.console.css、frontend/app/globals.css | frontend/lib/domain/status.test.ts::狀態 enum 對照表（lib/domain/status.ts 是唯一出處）、frontend/tests/design-rules.test.ts::設計系統硬規則（靜態守衛）（只用 token、無寫死色碼） | 待填 | ✅ 實作+測試 |
| UI-DS-02 | 設計稿 README §Typography | Inter＋Noto 字型 | FE | 1 | frontend/styles/fonts.css、frontend/app/layout.tsx | frontend/tests/e2e/design-system.spec.ts::字型：內文用 Inter Variable＋Noto Sans TC Variable，且自託管（沒有對 Google Fonts 的請求） | 待填 | ✅ 實作+測試 |
| UI-DS-03 | 設計稿 README §Elevation | 扁平無陰影 | FE | 1 | frontend/app/globals.css、frontend/components/ui/card.tsx、frontend/styles/markdown.css | frontend/tests/design-rules.test.ts::設計系統硬規則（靜態守衛）（無 shadow／漸層）、frontend/tests/e2e/design-system.spec.ts::扁平：頁面、開著的建立 Dialog 與 Markdown 編輯器裡沒有任何元素帶 box-shadow | 待填 | ✅ 實作+測試 |
| UI-DS-04 | 設計稿 README §Iconography | 僅用 Lucide 線性圖示 | FE | 1 | frontend/components/ui/button.tsx、frontend/components/ui/icon-button.tsx（lucide-react 1.57.0；stroke 1.5 於 app/globals.css） | frontend/tests/design-rules.test.ts::設計系統硬規則（靜態守衛）（只用 Lucide、無手寫 svg、無 emoji） | 待填 | ✅ 實作+測試 |
| UI-DS-05 | 設計稿 README §Focus | 強制鍵盤焦點環 | FE | 1 | frontend/styles/tokens.css、frontend/components/ui/input.tsx、frontend/components/layout/TopRegion.tsx | frontend/tests/design-rules.test.ts::設計系統硬規則（靜態守衛）（不得 outline-none）、frontend/tests/e2e/design-system.spec.ts::焦點環：鍵盤依序 Tab 過頂列的每個停駐點，皆為 2px 實線主色外框（搜尋框改畫在內側） | 待填 | ✅ 實作+測試 |
| UI-DS-06 | 設計稿 README §Motion | 動效規範（僅色彩透明度） | FE | 1 | frontend/app/globals.css、frontend/components/ui/button.tsx | frontend/tests/design-rules.test.ts::設計系統硬規則（靜態守衛）（hover 無位移／縮放） | 待填 | ✅ 實作+測試 |
| UI-DS-07 | 設計稿 README §狀態 enum | 狀態中文標籤與顏色 | FE | 1 | frontend/lib/domain/status.ts、frontend/components/ui/status-dot.tsx | frontend/lib/domain/status.test.ts::狀態 enum 對照表（lib/domain/status.ts 是唯一出處） | 待填 | ✅ 實作+測試 |
| UI-MD-01 | PRD §5.1.4 | 即時預覽（Split View） | FE | 2 | frontend/components/markdown/MarkdownEditorImpl.tsx、frontend/components/markdown/MarkdownEditor.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-01 即時預覽（Split View） | 待填 | ✅ 實作+測試 |
| UI-MD-02 | PRD §5.1.4 | Markdown 語法高亮 | FE | 2 | frontend/components/markdown/MarkdownEditorImpl.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-02 語法高亮（編輯區原始碼著色） | 待填 | ✅ 實作+測試 |
| UI-MD-03 | PRD §5.1.4 | 常用語法工具列 | FE | 2 | frontend/components/markdown/MarkdownEditorImpl.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-03 常用語法工具列 | 待填 | ✅ 實作+測試 |
| UI-MD-04 | PRD §5.1.4 | GFM 表格支援 | FE | 2 | frontend/components/markdown/MarkdownView.tsx、frontend/styles/markdown.css | frontend/components/markdown/markdown.test.tsx::UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist | 待填 | ✅ 實作+測試 |
| UI-MD-05 | PRD §5.1.4 | 程式碼區塊與語言高亮 | FE | 2 | frontend/components/markdown/MarkdownView.tsx、frontend/styles/markdown.css | frontend/components/markdown/markdown.test.tsx::UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist | 待填 | ✅ 實作+測試 |
| UI-MD-06 | PRD §5.1.4 | Checklist 核取方塊 | FE | 2 | frontend/components/markdown/MarkdownView.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-04／05／06 渲染端：GFM 表格、程式碼區塊語言高亮、Checklist | 待填 | ✅ 實作+測試 |
| UI-MD-07 | PRD §5.1.4 | 匯入 .md 檔案 | FE | 2 | frontend/components/markdown/MarkdownEditorImpl.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-07 匯入 .md 檔案 | 待填 | ✅ 實作+測試 |
| UI-MD-08 | PRD §5.1.4 | 匯出 .md 檔案 | FE | 2 | frontend/components/markdown/MarkdownEditorImpl.tsx | frontend/components/markdown/markdown.test.tsx::UI-MD-08 匯出 .md 檔案 | 待填 | ✅ 實作+測試 |
| UI-OVL-01 | 設計稿 README §全域覆蓋層 | 建立／編輯 Dialog | FE | 2 | frontend/components/ui/dialog.tsx、frontend/components/domain/entity/EntityDialog.tsx、frontend/components/domain/SignoffDialog.tsx、frontend/components/domain/ConfirmDialog.tsx | frontend/tests/e2e/crud-flow.spec.ts::登入 → 專案／目標／任務完整流程 → 刪除、frontend/tests/e2e/signoff.spec.ts::signoff 流程 | 待填 | ✅ 實作+測試 |
| UI-OVL-02 | 設計稿 README §全域覆蓋層 | Toast 提示 | FE | 2 | frontend/components/ui/toast.tsx | frontend/components/ui/ui.test.tsx::Toast（底部置中、一次一則、自動消失） | 待填 | ✅ 實作+測試 |
| UI-OVL-03 | 設計稿 README §全域覆蓋層 | 載入 Skeleton／spinner | FE | 2 | frontend/components/ui/skeleton.tsx、frontend/components/ui/spinner.tsx、frontend/components/ui/states.tsx | frontend/components/ui/ui.test.tsx::載入狀態（UI-OVL-03） | 待填 | ✅ 實作+測試 |
| UI-KPI-01 | PRD §5.4.2 | KPI 專案完成率（環形） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-02 | PRD §5.4.2 | KPI 目標達成率（環形） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-03 | PRD §5.4.2 | KPI 任務成功率 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-04 | PRD §5.4.2 | KPI 平均重試次數 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-05 | PRD §5.4.2 | KPI Token 總消耗 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-06 | PRD §5.4.2 | KPI Token 預算使用率 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-07 | PRD §5.4.2 | KPI 平均任務執行時間 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-KPI-08 | PRD §5.4.2 | KPI Agent 可用率 | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-CHT-01 | PRD §5.4.2 | 圖 任務執行趨勢（堆疊面積） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-CHT-02 | PRD §5.4.2 | 圖 Token 使用趨勢（折線） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-CHT-03 | PRD §5.4.2 | 圖 成功失敗比率（堆疊柱） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-CHT-04 | PRD §5.4.2 | 圖 執行時間分佈（柱狀） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |
| UI-CHT-05 | PRD §5.4.2 | 圖 重試次數分佈（柱狀） | FE+BE | 5 | 待填 | 待填 | 待填 | ⬜ 未開始 |

## 3. 統計（建表時快照）

### 3.1 PRD 使用者故事對帳（58 條一條不漏）

| 類別 | PRD 條數 | 本表列數 | 來源章節 | 對帳 |
|------|----------|----------|----------|------|
| `US-P` | 6 | 6 | PRD §5.1.1 | 一致 |
| `US-G` | 7 | 7 | PRD §5.1.2 | 一致 |
| `US-T` | 6 | 6 | PRD §5.1.3 | 一致 |
| `US-I` | 10 | 10 | PRD §5.2.3 | 一致 |
| `US-E` | 11 | 11 | PRD §5.3.4 | 一致 |
| `US-M` | 10 | 10 | PRD §5.4.3 | 一致 |
| `US-S` | 8 | 8 | PRD §5.5.3 | 一致 |
| 合計 | 58 | 58 | — | 一致 |

**PRD §7.1 端點對帳（55 條：REST 53＋SSE 2；每條一列，補充端點與規則列另計）**

| PRD 章節 | PRD 條數 | 本表對應列（`API-<碼>-01～nn`） | 列數 | 對帳 |
|----------|----------|--------------------------------|------|------|
| §7.1.1 專案管理 | 5 | `API-PRJ-01～05` | 5 | 一致 |
| §7.1.2 目標管理 | 6 | `API-GOL-01～06` | 6 | 一致 |
| §7.1.3 任務管理 | 6 | `API-TSK-01～06` | 6 | 一致 |
| §7.1.4 匯入 | 6 | `API-IMP-01～06` | 6 | 一致 |
| §7.1.4.1 signoff | 4 | `API-SGN-01～04` | 4 | 一致 |
| §7.1.5 執行 | 10 | `API-EXE-01～10` | 10 | 一致 |
| §7.1.6 監控 | 7 | `API-MON-01～07` | 7 | 一致 |
| §7.1.7 SSE | 2 | `API-SSE-01～02` | 2 | 一致 |
| §7.1.8 系統參數 | 9 | `API-SET-01～09` | 9 | 一致 |
| 合計 | 55 | — | 55 | 一致 |

### 3.2 ID 類別 × Phase（加總＝總列數）

| 類別 | P1 | P2 | P3 | P4 | P5 | P6 | 合計 |
|------|----|----|----|----|----|----|------|
| US | 0 | 19 | 10 | 11 | 10 | 8 | 58 |
| API | 8 | 24 | 11 | 25 | 14 | 9 | 91 |
| BR | 1 | 0 | 5 | 19 | 0 | 0 | 25 |
| NFR | 10 | 4 | 1 | 1 | 0 | 16 | 32 |
| INF | 56 | 0 | 0 | 1 | 1 | 45 | 103 |
| UI | 15 | 15 | 1 | 1 | 15 | 5 | 52 |
| 合計 | 90 | 62 | 28 | 58 | 40 | 83 | 361 |

### 3.3 層 × Phase（複合層計入每個涉及的層，故加總大於總列數）

| 層 | P1 | P2 | P3 | P4 | P5 | P6 | 合計 |
|----|----|----|----|----|----|----|------|
| FE | 20 | 34 | 11 | 12 | 25 | 17 | 119 |
| BE | 30 | 47 | 22 | 37 | 37 | 26 | 199 |
| Bridge | 5 | 1 | 15 | 46 | 4 | 2 | 73 |
| Infra | 44 | 0 | 0 | 0 | 0 | 49 | 93 |

### 3.4 現查指令（回填後以此重算，兩種 shell 擇一）

```bash
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| US-[PGTIEMS]-' AgentConsole/docs/06_quality/RTM.md
grep -c -E '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$' AgentConsole/docs/06_quality/RTM.md
```

```powershell
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| US-[PGTIEMS]-').Count
(Select-String -Path AgentConsole\docs\06_quality\RTM.md -Pattern '^\| (US|API|BR|NFR|INF|UI)-.*⬜ 未開始 \|$').Count
```

## 4. 範圍外與選配（不入列數；若日後要做，須新增列並更新 ADR）

| 項目 | 來源 | 處置 |
|------|------|------|
| 自動 failover（Patroni／pg_auto_failover／etcd／pgbouncer／HAProxy） | PRD §12.2.7 | 選配、預設未啟用；全文不宣稱 HA，另立 ADR |
| 離站替代方案 NFS／rsync／Rclone | PRD §12.7.2 | 非預設；預設為 S3／MinIO（見 INF-DR-11） |
| WebSocket 雙向通訊 | PRD §3.2 | 標示可選；本輪以 REST＋SSE 達成所有故事 |
| Next.js `app/api/` BFF 層 | PRD §4.2 | 標示可選；僅保留 `/api/health`（API-HLT-03） |
| eventBusType 的 KAFKA／RABBITMQ | PRD §5.5.1.5 | 只儲存為設定值，不實作對應後端 |
| Email 通知（monitor.enableEmailNotification） | PRD §5.5.1.4 | 只儲存設定值，不寄信 |
| 並行任務／並行目標（agent.maxConcurrentTasks、execution.maxParallelGoals） | PRD §5.5.1.2／§5.5.1.3 | 只儲存設定值；AutoClaude Playbook 為序列執行，見 Architecture §12 L-1 |
| Replica 唯讀查詢分流 | PRD §12.3.1 | 後端僅連 primary；replica 專供 DR，見 Architecture §12 L-3 |

