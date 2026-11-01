# SCG-4 審查報告 — 執行中心／監控中心的無專案入口頁（鍵 `agentconsole-exec-monitor-entry`）

**TCS**：`AgentConsole/docs/03_testing/contracts/TCS-ExecMonitorEntry-20261101.md`（Stage-2 凍結 `sha256:7987c06dbb3a557fcd976c6331284597c38fd605866cc1e4424a7b5f80d43c73`；RELEASE_READY refreeze 後含勘誤 1～9）
**規格 commit** `57daa703`（Console PRD §0.8＋§8.1 註、Architecture §5.1／§5.4、ADR-002 D3 訂正、P1b TCS 勘誤 26、本 TCS）；**實作 commit** `b8c29146`（Sonnet 開發棒；主控親驗）；RELEASE commit＝本報告所在 commit。
**審查者**：QA 鏡（Sonnet，獨立 worktree `@b8c29146`，全程唯讀、不採信任何宣稱）；主控（Fable）親驗與真機。

## A. 判定

**一審 PASS**（2026-11-02 00:1x；P1 0／P2 0／P3 3／P4 4）。理由：8 個 vitest AT 單跑全綠、AT-953-4-1 以 diff 人讀過、AT-953-4-2 文字核對過；全區 vitest／tsc／lint rc 皆 0；範圍外改動 0；§4 六筆同步零刪斷言；23 個突變殺 20。三個存活突變（頁殼 kind、有舊資料時重抓失敗、進入頁記住專案）都是「該條文沒有 vitest 層 AT」而非既有 AT 判準不足，主控於一審後補 AT-953-2-4 與兩個 Then（勘誤 3、4），同時套用三個突變重放：恰 4 個對應測試轉紅（AT_953_2_2×2、AT_953_2_3 第三個 it、AT_953_2_4 execute），改回後子檔 11 測試綠、全套綠。

## B. 發現表（QA 一審）

| 編號 | 嚴重度 | 座標 | 事實 | 處置 |
|------|--------|------|------|------|
| F-01 | P3 | `app/execute/page.tsx:8`、`app/monitor/page.tsx:8` | 突變 m12（execute 頁殼改 `kind="monitor"`）全套 rc 0 存活：沒有任何 vitest 載入頁殼，只有 E2E AT-953-4-2 承擔 | 主控補 AT-953-2-4（兩個 kind；`data-kind`、標題、`metadata.title`）；勘誤 4 |
| F-02 | P3 | `CenterEntryView.tsx:86-91` | 突變 x10（條件改 `projects === undefined \|\| all.isError`）存活：W-E1 (c)「只有根本沒有資料才換錯誤畫面」無 AT | 主控補 AT-953-2-3 第三個 it（第一次 200、重抓 500 → 清單仍在、無錯誤卡）；勘誤 3 |
| F-03 | P3 | `CenterEntryView.tsx:56-58` | 突變 x11（有專案時 `rememberProjectId`）存活：W-E1 (d)「不記住專案」無 AT | 主控於 AT_953_2_2 加 `getLastProjectId()` 為 null 與 sessionStorage 無鍵；勘誤 3 |
| F-04 | P4 | `registry.test.ts:159`、`:357` | 兩個 it 標題仍寫「無專案時回 /projects」「與舊 hrefFor 完全相同」，與現行斷言相反 | 刻意保留（AT 標題與 id 不變；與導覽整併勘誤 6 同口徑）；勘誤 6 |
| F-05 | P4 | `exec-monitor-entry.test.ts:23` | `ownPathProblems` 是 `registry.test.ts` 判準的複本（有 broken 負控） | 事實登記；勘誤 7 |
| F-06 | P4 | 兩個 `page.tsx` | `metadata.title` 無任何斷言 | 併入 AT-953-2-4 |
| F-07 | P4 | RTM 子表 | 狀態欄與實作 commit 待回填 | RELEASE 回填（本 commit） |

## C. 突變（QA 在 worktree；每個跑全套 vitest，基線 1771 測試全綠）

m1 execute.href 無專案→/projects（紅 AT_953_1_1 另 4 筆既有）、m2 monitor.match 拿掉精確 /monitor（AT_953_1_2 另 2）、m3 清單連結 kind 寫死 execute（僅 AT_953_2_2 monitor 變體紅——證明兩 kind 都要跑）、m4 空狀態標題（AT_953_2_1×2、2_E_1×2）、m5 HELP_ROUTES 拿掉 /monitor（AT_953_3_1 另 6 筆說明鎖）、m6 VIEWER 停用拿掉（2_E_1×2）、m7 說明句拿掉「以專案為單位」（2_1）、m8 清單 aria-label（2_2×2）、m9 新建專案 href（2_1×2）、m10 錯誤標題（2_3 重試變體）、m11 projects.match 也認 /execute（1_2、1_E_1 另 5）、x1 match 改 startsWith（1_2）、x2 停用鈕拿掉 title（2_E_1×2）、x3 NO_STATE_PAGES 拿掉 monitor-entry（3_1、AT_PH_03_5_1）、x4 重試 no-op（2_3）、x5 狀態標籤一律 READY（2_2×2）、x6 匯入 href（2_1×2、2_E_1×2）、x7 有專案時 router.push（2_2×2）、x8 PageSkeleton→null（2_3 永不回應變體）、x9 說明 title（3_1）；**存活** m12、x10、x11 → 主控補 AT 後重放皆紅（§A）。

## D. AT 單跑與全區

| AT | 結果 |
|----|------|
| AT-953-1-1／1-2／1-E-1／3-1（`exec-monitor-entry.test.ts`） | 各 rc 0；1-2 的 `ownPathProblems` 對真登記表計算、附 broken 負控 |
| AT-953-2-1／2-2／2-E-1（`CenterEntryView.test.tsx`，兩個 kind） | 各 rc 0（2 passed） |
| AT-953-2-3 | rc 0（永不回應→骨架；500→錯誤卡→重試請求計數 1→2；一審後加第三個 it：重抓失敗清單照常） |
| AT-953-2-4（一審後新增） | rc 0（兩個 kind） |
| AT-953-4-1（git diff 人讀） | 16 檔皆在 §5.7 允許集合（含主控 RTM 兩檔）；`registry.test.ts` it 20→20、expect 74→74；`issues-nav` 3→3／22→22；`sysadmin-nav` 5→5／52→52；被刪 expect 只有 2 行且皆原位改預期值；E2E spec +16／−0、expect 33→39；禁動檔差異 0 |
| AT-953-4-2 | 見 §E V2 |
| 全區（QA worktree @b8c29146） | vitest 104 檔／1771 測試 rc 0；tsc rc 0；lint rc 0 |
| 全區（主控，主 repo，補 AT 後） | vitest 104 檔／1774 測試 rc 0；tsc rc 0；lint rc 0 |

## E. V 系列（真機；非 AT）

- **V1 探針**（主控，2026-11-01 23:5x；Docker 全棧重建 frontend 後，拋棄式 Playwright 對 nginx 入口 `http://localhost`，operator 登入，資料庫零未封存專案＝掌舵者回報時的狀態，瀏覽器端攔下所有非 GET）：(a) 點側欄「執行中心」→ `/execute`，`center-entry-view` `data-kind=execute`、標題「執行中心」、說明含「以專案為單位」、空狀態「還沒有任何專案」、「新建專案」→`/projects/new`、「BRD/PRD 匯入」→`/import`、側欄該項 `aria-current=page`、無清單 ✅；(b) 「監控中心」→ `/monitor` 同組檢核 ✅；(c) 390px 底部 Tab 仍五項且點執行中心到 `/execute` ✅；零 API ≥400、零 console／page 錯誤；截圖 1440×2、390×1（scratchpad，不入庫）。
- **V2 真機 E2E**：`shells-and-layout.spec.ts` 對 Docker 全棧（`E2E_WEB_PORT=80`、`E2E_API_URL=http://localhost`）6 測試全過 rc 0（第一個測試含新加的 `/execute`、`/monitor` 深連結案例：標題、`center-entry-view`、側欄 `aria-current`、清單連結到 `/projects/<id>/execute`／`/monitor`）。副產物：兩張已追蹤響應式截圖被重寫，差異只是動態內容，以 `git show HEAD:<path>` 還原、不入庫（勘誤 9）。
- **V3 文件**：Console PRD §0.8 與 §8.1 註、Architecture §5.1／§5.4、ADR-002 D3 訂正、P1b TCS 勘誤 26、本 TCS 勘誤 1～9、RTM 子表 18 列回填、`RTM.md` §2.9 存根；上位五鍵（`agentconsole-fsm-trail`、`agentconsole-nav-consolidation`、`agentconsole-si-mirror`、`agentconsole-si-decide`、`agentconsole-si-decide-dedupe`）與本鍵 refreeze。

## F. FSM 收尾

PR_REVIEW gate PASS → RTM_VERIFY gate PASS → RELEASE_READY → 本鍵 spec-refreeze（PRD、Architecture、ADR-002、P1b TCS、本 TCS 含勘誤 1～9）→ 上位五鍵 spec-refreeze → RELEASE。各動詞 rc 皆 0（主控親跑；rc 逐字見 RELEASE commit 訊息）。

## G. 掌舵者問題對照

掌舵者 2026-11-01 23:2x：「監控中心與執行中心UI無法執行? 請查看哪裡出錯並解決」。
- **哪裡出錯**：不是程式錯誤，是設計上的靜默退回。資料庫只有三個已封存的測試專案（E2E／QA 殘留），專案列表為空 ⇒ 側欄兩入口找不到目的專案 ⇒ 依 ADR-002 D3 退回 `/projects`，畫面只剩專案管理的空狀態、網址與 active 項都是專案管理（nginx 記錄 23:17～23:20 多次自儀表板落到 `/projects`，兩中心頁零請求、零錯誤）。
- **怎麼解決**：零專案時側欄兩入口改落到各自的入口頁 `/execute`、`/monitor`，頁上說明「以專案為單位」、給「新建專案」「BRD/PRD 匯入」兩個去處；有專案後入口頁會列出專案供選擇，而側欄入口會直接進入目前專案的執行／監控頁（原行為不變）。真機 V1／V2 已驗。
