# 任務書 W5-FE：前端修復棒（Next.js 16／React 19／TypeScript strict）

> 先讀 `W5_OVERVIEW.md`。持有面：`frontend/**`（含 `tests/e2e/*.mock.spec.ts`、單元測試、截圖基準）與 `docs/06_quality/rtm_backfill_W5FE.md`。**不改** `tests/e2e/` 的真後端 spec（p3～p8、signoff、crud-flow、design-system、chart、shells-and-layout、task-retry、helpers.ts、realBackend.ts）——那些由 W5-QA 在真後端驗過後改。契約 v1.2 已由 SA 定稿；型別從 `docs/02_architecture/openapi-p3-6.yaml` 重產（找現有產生指令：在 `frontend/` 內 grep `openapi-typescript`）。

## 必讀

契約 v1.2 §1.1.9／§1.2.2／§1.3（task-totals、report）／§2.8／§6.5；QA 報告 §11 的 DEF-AC-001、004、005、007、009、§13、觀察 O-02／O-04／O-17；`frontend/lib/api/client.ts`（第 179～275 行）、`frontend/lib/api/sse.ts`（重連處）、`frontend/lib/api/queries.ts`（第 888～945 行）、`frontend/components/domain/import/{NodeEditDialog.tsx,tree.ts,TreeEditor.tsx}`、`frontend/styles/tokens.css`。

## 範圍（依優先序；每條做完立即 lint＋tsc＋vitest 對應檔，不累積）

1. **DEF-AC-001**：`NodeEditDialog.tsx:278`、`tree.ts:127`、`TreeEditor.tsx:132` 判空改 `== null`／`!= null`（型別允許 `null` 就把型別也改對）；補元件測試餵 `maxRetries: null`（對話框欄位為空字串、預覽不印「null」、可按確定）。
2. **C-5 DEF-AC-007**：`client.ts` 的 `doRefresh` 回三態（`renewed`／`invalid`／`unavailable`）；`renewSession` 只在 `invalid` 清 session；`sendWithRenewal` 401＋`unavailable` → 丟 `ApiError{status:503, reason:"upstream_unavailable"}` 不登出；`getFreshAccessToken({force})` 在 `unavailable` 時現有 token 未過期就沿用、否則回 null 不登出；`sse.ts` 對 null token／連線失敗做 1→2→4→…→30 秒退避並維持「重新連線中」；更新 `client.test.ts`（第 244～253 行等）與 `sse.test.ts`：502、網路錯誤不清 session，401 才清。
3. **C-1 DEF-AC-009**：`queries.ts` 的 `useWeekCompletedTasks` 改打 `GET /monitor/task-totals`（from＝本週一 00:00 本機時區轉 ISO、to＝現在）一次；拿掉 `WEEK_COMPLETED_MAX_PROJECTS` 與 `projectsForWeeklyCompleted`；輪詢維持 60 秒、分頁隱藏不輪詢（React Query 預設）；儀表板的 partial 語意改為 loading／error；更新單元測試與 `dashboard`／`monitor` 的 `*.mock.spec.ts` 路由 mock（mock 夾具加 task-totals）。
4. **C-18 DEF-AC-004／005**：`tokens.css` 主色底小字 `#ffffff`、`wg-muted` 加深到 ≥4.5:1（QA 建議 `#6b7766`，以 axe／手算對比驗）；頂列 logo aria-label 含可見文字；Markdown 工具列 svg `aria-hidden="true"`；監控頁 Agent 狀態晶片 list 結構改正；`design-system.mock`／vitest 的色值斷言與截圖基準同步更新（截圖只更新 mock spec 產生的）。
5. **C-10**：匯入記錄重開時顯示 `warnings[]` 黃色提示並還原 `parseOptions`（mock spec 補情境）。
6. **C-11**：批次列表顯示 `bridgeStatus`（PAUSING／CANCELLING 晶片）。
7. **C-3**：專案列表「已刪除」篩選（`deleted=true`，OPERATOR 以上可見）與「復原」按鈕、toast、三種錯誤原因顯示（mock spec）。
8. **C-4**：報表匯出 PDF 選項啟用（下載走既有 `apiDownload`，檔名取 `Content-Disposition`）。
9. **C-8／C-9**：刪除目標／任務遇 409 `project_executing` 顯示原因；手動重試 toast 文案改「手動重試第 N 次（不計入自動重試上限 M）」。
10. **C-19**：Prettier（`.prettierrc` 與現行風格一致：雙引號、分號、trailing comma、printWidth 對齊現有程式；`npm run format:check`；`lint` 腳本串起來）——若 `prettier --check` 對現有檔有差異，只在 `frontend/**` 內套用且**排除** `tests/e2e/` 的真後端 spec；Markdown 預覽去抖（`useDeferredValue`），用 QA 的量法（真瀏覽器 20KB 文件 7 次中位數）量一次附數字。
11. **RTM 回填** `docs/06_quality/rtm_backfill_W5FE.md`：US-I-04、UI-SCR-06、UI-A11Y-01／03、UI-SCR-01、NFR-9.4-01、NFR-9.1-05、API-SSE-03／NFR-9.2-01（附註 DEF-AC-007）、US-M-07 前端側、NFR-9.3-04 前端側、UI-KPI-01／02（引用 ADR-001 G-20）。

## 契約 v1.2 定稿後的補充（SA 交卷，主控已採納；與上文衝突時以契約為準）

- `lib/api/reasons.ts`：新增 `project_executing`、`project_not_deleted`、`restore_window_expired`、`upstream_unavailable` 四個常數（英文識別字，契約 §0.3 第 5 點、附錄 B.2；`upstream_unavailable` 只由前端合成），移除 `PDF 報表尚未提供（W5）`；否則 `reasons.test.ts` 的雙向比對會紅。
- 重產型別後 `ImportRecordDetailResponse.warnings` 為 required、`parseOptions` nullable；`ExecutionRunSummaryResponse.bridgeStatus`；`ProjectSummaryResponse.deletedAt`；`TaskTotalsResponse`——既有夾具與 mock 要補齊。
- task-totals 的 400 reason 是 `時間範圍不合法`（`errors[].field=to`）；PDF 報表現在回 200（監控頁若有 501 的處理分支一併拿掉）。
- 換新三態與 SSE 退避的精確規則在契約 §2.8 第 7～9 點（未列狀態碼一律視為 `unavailable`，寧可保留 session）。

## 閘門（全部 rc=0，貼逐字關鍵行）

`npm run lint`、`npx tsc --noEmit`、`npm run build`（20 路由）、`npx vitest run --coverage`（≥70%，現值 Statements 95.43%，不得明顯下降）、`npx playwright test tests/e2e/*.mock.spec.ts`（dev 模式；起跑前刪 `frontend\.next\dev`；對真後端的 spec 不在本棒閘門）、四區塊只在 `app/layout.tsx` 組裝的掃描無輸出。所有指令 `Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\frontend; …; Pop-Location`，輸出導檔後讀 rc。

## 交卷

依 `W5_OVERVIEW.md` §5；〈給 QA 的提醒〉列：p3 的 DEF-AC-001 `test.fail`、p8 的 DEF-AC-007 `test.fail` 可移除；儀表板 mock 夾具的 task-totals 形狀；哪些截圖基準改了與原因。
