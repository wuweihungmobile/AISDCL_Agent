# SCG-4 審查報告 — Console 側欄導覽整併（鍵 `agentconsole-nav-consolidation`）

**TCS**：`AgentConsole/docs/03_testing/contracts/TCS-ConsoleNavConsolidation-20261101.md`（Stage-2 凍結 `sha256:5216df65f25653b516c4128c20ccd202ab319d6664edbc0a2fe16f700066c18e`；RELEASE_READY refreeze 後含勘誤 1～9）
**規格 commit** `a45a9d60`（Console PRD §0.7、Architecture 三處、IssueCenter TCS 勘誤 1-14、SysAdmin TCS 勘誤 1-36、本 TCS）；**實作 commit** `1a742bd7`（Sonnet 開發棒；主控親驗）；RELEASE commit＝本報告所在 commit。
**審查者**：QA 鏡（Sonnet，獨立 worktree `@1a742bd7`，全程唯讀、不採信任何宣稱）；主控（Fable）親驗與真機。

## A. 判定

**一審 PASS**（2026-11-01 17:xx；P1 0／P2 0／P3 3／P4 4）。理由：7 個 vitest AT 單跑全綠；任務書 m1～m10 突變全被殺（另加 m11～m15 亦被殺）；全區 vitest／tsc／lint rc 皆 0；範圍外零改動；§4 七筆同步零刪斷言。唯一存活突變 m16（Upload→Plus 圖示互換）屬 TCS 內 W-N3 與 AT-952-2-1 的強度落差（P3），主控於實作 commit 後補斷言（勘誤 4）。

## B. 發現表（QA 一審）

| 編號 | 嚴重度 | 座標 | 事實 | 處置 |
|------|--------|------|------|------|
| F-01 | P3 | `registry.ts` issues／sysadmin 兩列行內註解 | 仍寫舊 order 比較（55 介於 50 與 60；65 介於 60 與 70），與現值相反；D1「其餘一字不動」使開發棒只在檔頭免責 | 主控改寫兩段註解為現值、刪檔頭免責句（勘誤 5） |
| F-02 | P3 | `ProjectsView.tsx:100`、`ProjectsView.test.tsx` AT_952_2_1 | W-N3「仍帶 Upload 圖示」只驗「內含 svg」：`iconLeft={Upload}` 換 `{Plus}` 全套仍綠（m16 存活）；ADMIN 未測 | 主控補斷言 svg 類別含 `lucide-upload`（本 commit；子集重跑 7 檔 54 測試綠）；ADMIN 不另立 AT（勘誤 4） |
| F-03 | P3 | TCS §4 #4、#5、§6.1 | 「不須改」實改一行；§4 #5 漏列四處連動；§6.1 列數寫法不準 | 勘誤 1～3 |
| F-04 | P4 | 既有 it 標題（九個連結／九項／六項） | 依 W-N4 保留舊計數字樣，檔頭註明現值 | 勘誤 6（刻意保留） |
| F-05 | P4 | 四個測試檔各自濾停用列、`ownPathProblems` 複製一份 | 皆由快照衍生、非第二份真相 | 勘誤 2 登記根因；日後在 `navDelivered.ts` 一次 export |
| F-06 | P4 | `tests/e2e/__screenshots__/20-responsive-tablet.png`、`21-responsive-mobile.png` | 主控跑 `shells-and-layout.spec.ts` 的副產物（已追蹤截圖隨側欄少一項而變） | 隨 V2 證據提交（本 commit） |
| F-07 | P4 | 兩支 E2E spec | 改法與 W-N4 一致，無 strict-mode 風險；其餘 spec 進 `/import` 皆 `page.goto` | 主控 V2 實跑見 §E |

## C. 突變（QA 在 worktree；每個先跑全套，基線 1759 測試全綠）

m1 import.enabled→true（15 紅）、m2 settings.order→60（12）、m3 sysadmin.order→65（9）、m4 settings.order→76（7；只有逐值斷言殺它）、m5 import.href→/imports（10）、m6 import.match 永假（5）、m7 連結文字→「匯入」（2）、m8 連結 href→/projects/import（2）、m9 快照第 3 列 enabled→true（11）、m10 issues.order→72（11）、m11 拿掉 iconLeft（1）、m12 空狀態文案→「匯入」（1）、m13 VIEWER 隱藏連結（1）、m14 import.mobile→false（8）、m15 projects.match 吃掉 /import（11）；**存活 m16** iconLeft Upload→Plus → 主控補斷言後由 AT_952_2_1 殺。

## D. AT 單跑與全區

| AT | 結果 |
|----|------|
| AT-952-1-1／1-2／1-E-1／1-E-2（`nav-consolidation.test.ts`） | rc 0，Then 逐條有斷言 |
| AT-952-1-3（`ToolsRegion.test.tsx`） | rc 0；「原始碼零差異」以字樣掃描替代，git 零差異由 QA 與主控各核一次 |
| AT-952-2-1／2-E-1（`ProjectsView.test.tsx`） | rc 0（補斷言後子集重跑 7 檔 54 測試綠） |
| AT-952-3-1（git diff 人讀） | 7 檔 55 hunk；被刪 it／describe 0；被刪斷言 15 行皆一對一改值；expect 數不減（sysadmin 52→52、issues 22→22、registry 74→74、ToolsRegion 43→51、ProjectsView 35→45、shells 27→33、p9 63→65）；新增 skip／only／eslint-disable 0 |
| AT-952-3-2／3-3 | 見 §E V2 |
| 全區（QA worktree） | vitest 102 檔／1759 測試 rc 0；tsc rc 0；lint rc 0 |
| 全區（主控，主 repo @1a742bd7） | vitest 102 檔／1759 測試 rc 0；tsc rc 0；lint rc 0 |

G-C1：`git diff --name-only a45a9d60..1a742bd7` 13 檔＝11 個 frontend 檔（皆在 §5.7 集合）＋ 2 個主控 docs（RTM 子表、RTM.md 存根）；`ToolsRegion.tsx`、`layout.tsx`、`lib/help/**`、`lib/api/**`、backend、engine-bridge、根層 `tools/`、`.claude/` 零差異。

## E. V 系列（真機；非 AT）

- **V1 探針**（主控，2026-11-01 16:2x；Docker 全棧重建 frontend 後，拋棄式 Playwright 對 nginx 入口 `http://localhost`，operator 登入，瀏覽器端攔下所有非 GET）：(a) 側欄八個連結序＝儀表板、專案管理、執行中心、監控中心、議題中心、自我進化、系統管理、系統設定 ✅；(b) 側欄無「BRD/PRD 匯入」✅；(c) `/projects` 右上連結「BRD/PRD 匯入」href `/import`、無名稱恰為「匯入」的連結 ✅；(d) 點該連結到 `/import`、標題「BRD / PRD 智能匯入」、側欄仍無匯入入口 ✅；(e) 390px 底部 Tab 五項（儀表板、專案管理、執行中心、監控中心、系統設定）✅；截圖 1440／1024／390 各一張（scratchpad，不入庫）。
- **V2 真機 E2E**：`shells-and-layout.spec.ts` 對 Docker 全棧（`E2E_WEB_PORT=80`、`E2E_API_URL=http://localhost`）6 測試全過 rc 0（含改寫的導覽案例：側欄三項、`/projects` 按鈕到 `/import`、側欄無匯入入口；響應式三寬度）；`p9-w7-ui.spec.ts` 因 `test.skip(!E2E_ROOT)` 整檔略過（需 Bridge 側 `E2E_ROOT` 全環境），其錨點由 V1 探針代驗（勘誤 9）。副產物：兩張已追蹤響應式截圖更新（F-06），隨本 commit 提交。
- **V3 文件**：Console PRD §0.7 與 §8.1 註、Architecture §5.1／§5.2／§5.4、IssueCenter TCS 勘誤 1-14、SysAdmin TCS 勘誤 1-36、本 TCS 勘誤 1～9、RTM 子表 16 列回填、`RTM.md` §2.8 存根；上位三鍵（`agentconsole-fsm-trail`、`agentconsole-issue-center`、`agentconsole-sysadmin-backup`）與本鍵 refreeze。

## F. FSM 收尾

PR_REVIEW gate PASS → RTM_VERIFY gate PASS → RELEASE_READY → 本鍵 spec-refreeze（PRD、Architecture、ADR-001、P1b TCS、IssueCenter TCS、SysAdmin TCS、本 TCS 含勘誤 1～9）→ 上位三鍵 spec-refreeze → RELEASE。各動詞 rc 皆 0（主控親跑；rc 逐字見 RELEASE commit 訊息）。

## G. 掌舵者問題對照

四項指令的處置：① 側欄移除 BRD/PRD 匯入、專案管理頁按鈕改名 ✅（本鍵）；② 執行中心＝操作面、監控中心＝觀察面，功能不同、兩者都留（掌舵者互動選項裁決）；③ 順序依指令 ✅；④ PROP-SI-004／005／006 的量測窗：到 5／5 且 `si measure` 關窗（結果 clean）後議題中心歸「已完成（已採納）」；窗內復發則提早關窗轉「待您決定（回滾）」；沒有新的同型機會列時會一直停在「觀察中」（設計如此，見 SelfImproving PRD §1.3 與 Issue Center PRD §4.2）。
